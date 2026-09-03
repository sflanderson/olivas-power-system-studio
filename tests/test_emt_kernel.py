"""
tests/test_emt_kernel.py — verificação do kernel EMT dedicado
(``app.simulation.emt``): montagem MNA, modelos companheiros de Dommel,
linha de Bergeron, amortecimento crítico (CDA) e cache de fatoração.

Todo valor de referência é (a) conferido à mão sobre a formulação nodal,
(b) solução analítica fechada da equação diferencial do circuito, ou
(c) [CÁLCULO PRÓPRIO] medido nesta sessão e documentado no comentário.

Referências das soluções analíticas: qualquer texto de circuitos —
adotou-se a notação de [LITERATURA: A. Greenwood, *Electrical Transients
in Power Systems*, 2. ed., Wiley, 1991, cap. 2-5].
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.simulation.emt import (
    MODE_BACKWARD_EULER_HALF,
    MODE_TRAPEZOIDAL,
    BergeronLine,
    BranchCurrentProbe,
    BranchVoltageProbe,
    Capacitor,
    Circuit,
    CoupledRL,
    DifferentialVoltageProbe,
    Inductor,
    NodeVoltageProbe,
    Resistor,
    SingularSystemError,
    Solver,
    Switch,
    TimedSwitchController,
    VoltageSource,
    lu_factor,
    lu_solve,
    surge_impedance,
    three_phase_voltage_sources,
    travel_time,
)
from app.simulation.emt import KNOWN_LIMITATIONS
from app.simulation.emt import __all__ as EMT_ALL
from app.simulation.emt.probes import to_kV, to_stress_profile
from app.simulation.emt.components import GROUND_INDEX as GROUND_INDEX_LOCAL


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


def _dc_source(name: str, node_p: str, node_n: str, volts: float) -> VoltageSource:
    """Fonte de tensão contínua (amplitude senoidal nula, offset = ``volts``)."""
    return VoltageSource(
        name, node_p, node_n, amplitude_V=0.0, frequency_Hz=0.0, dc_offset_V=volts
    )


def _value_at(probe, t_query: float) -> float:
    """Valor da sonda na primeira amostra com ``t >= t_query``."""
    idx = int(np.searchsorted(probe.time_s, t_query))
    idx = min(idx, probe.n_samples - 1)
    return float(probe.values[idx])


# ---------------------------------------------------------------------------
# 1. Montagem da matriz MNA — conferida à mão
# ---------------------------------------------------------------------------


class TestMontagemMatriz:
    def test_resistor_unico_matriz_1x1(self):
        """R entre o nó 1 e a terra: A = [[1/R]] (KCL do único nó)."""
        ckt = Circuit("r")
        ckt.add(Resistor("R", "1", "gnd", 1000.0))
        assert ckt.build() == 1
        A = ckt.assemble_matrix()
        assert A.shape == (1, 1)
        assert A[0, 0] == pytest.approx(1.0e-3)

    def test_dois_resistores_serie_matriz_2x2(self):
        """R1(1-2) e R2(2-terra): A = [[G1, -G1], [-G1, G1+G2]]."""
        ckt = Circuit("serie")
        ckt.add(Resistor("R1", "1", "2", 100.0))
        ckt.add(Resistor("R2", "2", "gnd", 400.0))
        assert ckt.build() == 2
        A = ckt.assemble_matrix()
        g1, g2 = 1.0 / 100.0, 1.0 / 400.0
        esperado = np.array([[g1, -g1], [-g1, g1 + g2]])
        assert np.allclose(A, esperado)

    def test_fonte_ideal_matriz_aumentada(self):
        """MNA da fonte ideal: linha/coluna de incidência e restrição v = e(t).

        Com E(1-terra) e R(1-terra), x = [v1, i_E] e
        A = [[G, +1], [+1, 0]]; b = [0, e(t)].
        """
        ckt = Circuit("fonte")
        ckt.add(_dc_source("E", "1", "gnd", 12.0))
        ckt.add(Resistor("R", "1", "gnd", 4.0))
        assert ckt.build() == 2
        A = ckt.assemble_matrix()
        assert np.allclose(A, np.array([[0.25, 1.0], [1.0, 0.0]]))
        b = ckt.assemble_rhs(0.0, MODE_TRAPEZOIDAL)
        assert np.allclose(b, np.array([0.0, 12.0]))
        x = np.linalg.solve(A, b)
        # v1 = 12 V; a corrente da fonte SAI do nó 1, logo i_E = -3 A.
        assert x[0] == pytest.approx(12.0)
        assert x[1] == pytest.approx(-3.0)

    def test_chave_fechada_e_aberta_mesma_dimensao(self):
        """A dimensão do sistema é invariante ao estado da chave."""
        ckt = Circuit("chave")
        ckt.add(Resistor("R", "1", "gnd", 10.0))
        sw = ckt.add(Switch("SW", "1", "gnd", closed=True))
        assert ckt.build() == 2
        a_fechada = ckt.assemble_matrix()
        assert np.allclose(a_fechada, np.array([[0.1, 1.0], [1.0, 0.0]]))
        sw.open()
        a_aberta = ckt.assemble_matrix()
        assert np.allclose(a_aberta, np.array([[0.1, 1.0], [0.0, 1.0]]))
        assert a_aberta.shape == a_fechada.shape

    def test_assinatura_topologia_reflete_estado_das_chaves(self):
        ckt = Circuit("assin")
        ckt.add(Resistor("R", "1", "gnd", 10.0))
        sw = ckt.add(Switch("SW", "1", "gnd", closed=False))
        ckt.build()
        assert ckt.topology_signature() == (("SW", False),)
        assert sw.close() is True
        assert ckt.topology_signature() == (("SW", True),)
        assert sw.close() is False  # já estava fechada

    def test_condutancias_companheiras_de_dommel(self):
        """G_L = Δt/(2L) e G_C = 2C/Δt (Dommel 1969, eqs. 5 e 8)."""
        dt = 2.0e-6
        ind = Inductor("L", "1", "gnd", 1.0e-3)
        cap = Capacitor("C", "2", "gnd", 5.0e-9)
        ind.prepare(dt)
        cap.prepare(dt)
        assert ind.conductance_S == pytest.approx(dt / (2.0 * 1.0e-3))
        assert cap.conductance_S == pytest.approx(2.0 * 5.0e-9 / dt)

    def test_matriz_invariante_ao_modo_de_integracao(self):
        """Euler regressivo com h = Δt/2 dá a MESMA condutância do trapézio.

        É a propriedade que dispensa refatorar a matriz durante o CDA
        (Marti & Lin 1989).
        """
        dt = 1.0e-6
        ckt = Circuit("modo")
        ckt.add(_dc_source("E", "1", "gnd", 1.0))
        ckt.add(Resistor("R", "1", "2", 1.0))
        ckt.add(Inductor("L", "2", "3", 1.0e-3))
        ckt.add(Capacitor("C", "3", "gnd", 1.0e-9))
        ckt.build()
        ckt.prepare(dt)
        a_ref = ckt.assemble_matrix()
        # O modo só afeta o vetor independente, nunca a matriz.
        b_trap = ckt.assemble_rhs(dt, MODE_TRAPEZOIDAL)
        b_be = ckt.assemble_rhs(dt, MODE_BACKWARD_EULER_HALF)
        assert np.allclose(ckt.assemble_matrix(), a_ref)
        assert b_trap.shape == b_be.shape


# ---------------------------------------------------------------------------
# 2. Soluções em corrente contínua
# ---------------------------------------------------------------------------


class TestRegimeContinuo:
    def test_divisor_resistivo_dois_ramos(self):
        """v2 = V·R2/(R1+R2) = 10·3000/4000 = 7,5 V."""
        ckt = Circuit("divisor")
        ckt.add(_dc_source("E", "1", "gnd", 10.0))
        ckt.add(Resistor("R1", "1", "2", 1000.0))
        ckt.add(Resistor("R2", "2", "gnd", 3000.0))
        solver = Solver(ckt, dt=1.0e-6)
        v2 = solver.add_probe(NodeVoltageProbe("v2", "2"))
        solver.run(1.0e-5)
        assert v2.values[-1] == pytest.approx(7.5, rel=1e-12)

    def test_divisor_com_paralelo(self):
        """R2//R3 = 3000//6000 = 2000 Ω ⇒ v2 = 10·2000/3000 = 6,6667 V."""
        ckt = Circuit("paralelo")
        ckt.add(_dc_source("E", "1", "gnd", 10.0))
        ckt.add(Resistor("R1", "1", "2", 1000.0))
        ckt.add(Resistor("R2", "2", "gnd", 3000.0))
        ckt.add(Resistor("R3", "2", "gnd", 6000.0))
        solver = Solver(ckt, dt=1.0e-6)
        v2 = solver.add_probe(NodeVoltageProbe("v2", "2"))
        i_r1 = solver.add_probe(BranchCurrentProbe("i_R1", ckt.get("R1")))
        solver.run(1.0e-5)
        assert v2.values[-1] == pytest.approx(20.0 / 3.0, rel=1e-12)
        assert i_r1.values[-1] == pytest.approx((10.0 - 20.0 / 3.0) / 1000.0, rel=1e-12)

    def test_chave_aberta_interrompe_a_corrente(self):
        ckt = Circuit("aberta")
        ckt.add(_dc_source("E", "1", "gnd", 10.0))
        r = ckt.add(Resistor("R", "1", "2", 10.0))
        ckt.add(Switch("SW", "2", "gnd", closed=False))
        ckt.add(Resistor("Rp", "2", "gnd", 1.0e6))
        solver = Solver(ckt, dt=1.0e-6)
        i_r = solver.add_probe(BranchCurrentProbe("i_R", r))
        solver.run(1.0e-5)
        # Corrente limitada por Rp: 10/(10+1e6) ≈ 1e-5 A.
        assert i_r.values[-1] == pytest.approx(10.0 / (10.0 + 1.0e6), rel=1e-9)
        ckt.get("SW").close()
        solver.run(1.0e-5)
        assert i_r.values[-1] == pytest.approx(1.0, rel=1e-6)


# ---------------------------------------------------------------------------
# 3. Confronto com soluções analíticas
# ---------------------------------------------------------------------------


class TestSolucoesAnaliticas:
    def test_carga_de_rc_contra_exponencial(self):
        """v_C(t) = V(1 − e^(−t/RC)); erro máximo < 1e-4 V em 100 V."""
        R, C = 1000.0, 1.0e-6
        ckt = Circuit("rc")
        ckt.add(_dc_source("E", "1", "gnd", 100.0))
        ckt.add(Resistor("R", "1", "2", R))
        ckt.add(Capacitor("C", "2", "gnd", C))
        solver = Solver(ckt, dt=1.0e-7)
        vc = solver.add_probe(NodeVoltageProbe("vc", "2"))
        solver.run(5.0e-3)
        t = vc.time_s
        analitico = 100.0 * (1.0 - np.exp(-t / (R * C)))
        erro = float(np.max(np.abs(vc.values - analitico)))
        assert erro < 1.0e-4, f"erro máximo {erro:.3e} V"
        assert vc.values[-1] == pytest.approx(100.0 * (1 - math.exp(-5.0)), abs=1e-4)

    def test_descarga_de_rc_com_condicao_inicial(self):
        """v_C(t) = V0·e^(−t/RC) com o capacitor pré-carregado."""
        R, C, V0 = 500.0, 2.0e-6, 50.0
        ckt = Circuit("descarga")
        ckt.add(Resistor("R", "1", "gnd", R))
        ckt.add(Capacitor("C", "1", "gnd", C, initial_voltage_V=V0))
        solver = Solver(ckt, dt=1.0e-7)
        vc = solver.add_probe(NodeVoltageProbe("vc", "1"))
        solver.run(3.0e-3)
        t = vc.time_s
        analitico = V0 * np.exp(-t / (R * C))
        assert float(np.max(np.abs(vc.values - analitico))) < 1.0e-4

    def test_energizacao_de_rl_contra_exponencial(self):
        """i_L(t) = (V/R)(1 − e^(−tR/L)); erro máximo < 1e-6 A em 1 A."""
        R, L, V = 10.0, 1.0e-3, 10.0
        ckt = Circuit("rl")
        ckt.add(_dc_source("E", "1", "gnd", V))
        ckt.add(Resistor("R", "1", "2", R))
        ind = ckt.add(Inductor("L", "2", "gnd", L))
        solver = Solver(ckt, dt=1.0e-8)
        i_l = solver.add_probe(BranchCurrentProbe("iL", ind))
        v_l = solver.add_probe(BranchVoltageProbe("vL", ind))
        solver.run(1.0e-3)
        t = i_l.time_s
        analitico = (V / R) * (1.0 - np.exp(-t * R / L))
        assert float(np.max(np.abs(i_l.values - analitico))) < 1.0e-6
        # v_L = V·e^(−tR/L) — consistência entre as duas sondas.
        assert float(np.max(np.abs(v_l.values - V * np.exp(-t * R / L)))) < 1.0e-4

    def test_rlc_serie_subamortecido_amplitude_do_primeiro_pico(self):
        """v_C(t) = V[1 − e^(−αt)(cos ω_d t + (α/ω_d) sin ω_d t)].

        Primeiro máximo em t = π/ω_d, valor V(1 + e^(−απ/ω_d)).
        """
        R, L, C, V = 10.0, 1.0e-3, 1.0e-6, 1.0
        alpha = R / (2.0 * L)
        wd = math.sqrt(1.0 / (L * C) - alpha * alpha)
        ckt = Circuit("rlc")
        ckt.add(_dc_source("E", "1", "gnd", V))
        ckt.add(Resistor("R", "1", "2", R))
        ckt.add(Inductor("L", "2", "3", L))
        ckt.add(Capacitor("C", "3", "gnd", C))
        solver = Solver(ckt, dt=1.0e-8)
        vc = solver.add_probe(NodeVoltageProbe("vc", "3"))
        solver.run(8.0e-4)
        pico_teorico = V * (1.0 + math.exp(-alpha * math.pi / wd))
        assert float(np.max(vc.values)) == pytest.approx(pico_teorico, rel=1e-4)

    def test_rlc_serie_subamortecido_frequencia_amortecida(self):
        """f_d = ω_d/2π medida por cruzamentos ascendentes de v_C − V."""
        R, L, C, V = 10.0, 1.0e-3, 1.0e-6, 1.0
        alpha = R / (2.0 * L)
        wd = math.sqrt(1.0 / (L * C) - alpha * alpha)
        ckt = Circuit("rlc_f")
        ckt.add(_dc_source("E", "1", "gnd", V))
        ckt.add(Resistor("R", "1", "2", R))
        ckt.add(Inductor("L", "2", "3", L))
        ckt.add(Capacitor("C", "3", "gnd", C))
        solver = Solver(ckt, dt=1.0e-8)
        vc = solver.add_probe(NodeVoltageProbe("vc", "3"))
        solver.run(8.0e-4)
        t, y = vc.time_s, vc.values - V
        cruz = [
            t[i] + (t[i + 1] - t[i]) * (-y[i]) / (y[i + 1] - y[i])
            for i in range(len(y) - 1)
            if y[i] < 0.0 <= y[i + 1]
        ]
        assert len(cruz) >= 3
        periodo = float(np.mean(np.diff(cruz)))
        assert 1.0 / periodo == pytest.approx(wd / (2.0 * math.pi), rel=1e-3)

    def test_rlc_serie_subamortecido_decremento_logaritmico(self):
        """δ = ln(A_k/A_{k+1}) = α·T_d, com T_d = 2π/ω_d."""
        R, L, C, V = 10.0, 1.0e-3, 1.0e-6, 1.0
        alpha = R / (2.0 * L)
        wd = math.sqrt(1.0 / (L * C) - alpha * alpha)
        ckt = Circuit("rlc_d")
        ckt.add(_dc_source("E", "1", "gnd", V))
        ckt.add(Resistor("R", "1", "2", R))
        ckt.add(Inductor("L", "2", "3", L))
        ckt.add(Capacitor("C", "3", "gnd", C))
        solver = Solver(ckt, dt=1.0e-8)
        vc = solver.add_probe(NodeVoltageProbe("vc", "3"))
        solver.run(8.0e-4)
        y = vc.values - V
        picos = [
            float(y[i])
            for i in range(1, len(y) - 1)
            if y[i] > y[i - 1] and y[i] >= y[i + 1] and y[i] > 0.0
        ]
        assert len(picos) >= 3
        delta = float(np.mean(np.log(np.asarray(picos[:-1]) / np.asarray(picos[1:]))))
        assert delta == pytest.approx(alpha * 2.0 * math.pi / wd, rel=1e-3)

    def test_conservacao_de_energia_em_tanque_lc(self):
        """LC sem perdas: E = ½Li² + ½Cv² constante (trapézio é conservativo)."""
        L, C, I0 = 1.0e-3, 1.0e-6, 1.0
        ckt = Circuit("lc")
        ind = ckt.add(Inductor("L", "1", "gnd", L, initial_current_A=I0))
        ckt.add(Capacitor("C", "1", "gnd", C))
        solver = Solver(ckt, dt=1.0e-8)
        i_l = solver.add_probe(BranchCurrentProbe("iL", ind))
        v_c = solver.add_probe(NodeVoltageProbe("vc", "1"))
        solver.run(1.0e-3)
        energia = 0.5 * L * i_l.values**2 + 0.5 * C * v_c.values**2
        e0 = 0.5 * L * I0**2
        desvio = float(np.max(np.abs(energia - e0))) / e0
        assert desvio < 1.0e-4, f"desvio relativo de energia {desvio:.3e}"

    def test_frequencia_do_tanque_lc(self):
        """f0 = 1/(2π√(LC)) = 5032,92 Hz para L = 1 mH e C = 1 µF."""
        L, C, I0 = 1.0e-3, 1.0e-6, 1.0
        ckt = Circuit("lc_f")
        ckt.add(Inductor("L", "1", "gnd", L, initial_current_A=I0))
        ckt.add(Capacitor("C", "1", "gnd", C))
        solver = Solver(ckt, dt=1.0e-8)
        v_c = solver.add_probe(NodeVoltageProbe("vc", "1"))
        solver.run(6.0e-4)
        t, y = v_c.time_s, v_c.values
        cruz = [
            t[i] + (t[i + 1] - t[i]) * (-y[i]) / (y[i + 1] - y[i])
            for i in range(len(y) - 1)
            if y[i] < 0.0 <= y[i + 1]
        ]
        periodo = float(np.mean(np.diff(cruz)))
        assert 1.0 / periodo == pytest.approx(
            1.0 / (2.0 * math.pi * math.sqrt(L * C)), rel=1e-4
        )


# ---------------------------------------------------------------------------
# 4. Linha de Bergeron
# ---------------------------------------------------------------------------


class TestLinhaBergeron:
    def test_impedancia_de_surto_e_tempo_de_transito(self):
        """Z_c = √(L'/C') e τ = ℓ√(L'C')."""
        lp, cp, ell = 2.5e-7, 1.0e-10, 1000.0
        assert surge_impedance(lp, cp) == pytest.approx(50.0)
        assert travel_time(ell, lp, cp) == pytest.approx(ell * math.sqrt(lp * cp))
        linha = BergeronLine.from_distributed_parameters(
            "LN", "k", "m", length_m=ell, inductance_H_per_m=lp, capacitance_F_per_m=cp
        )
        assert linha.surge_impedance_ohm == pytest.approx(50.0)
        assert linha.travel_time_s == pytest.approx(5.0e-6)
        assert linha.attenuation_factor == pytest.approx(1.0)

    def test_terminacao_aberta_duplica_a_tensao_e_reflete_em_2tau(self):
        """Fonte 1 V com R_s = Z_c: onda incidente 0,5 V.

        Terminal aberto: v_m salta a 1,0 V em t = τ (duplicação); a
        reflexão volta ao emissor em t = 2τ, levando v_k de 0,5 a 1,0 V.
        """
        zc, tau = 100.0, 10.0e-6
        ckt = Circuit("aberta")
        ckt.add(_dc_source("E", "s", "gnd", 1.0))
        ckt.add(Resistor("Rs", "s", "k", zc))
        ckt.add(BergeronLine("LN", "k", "m", surge_impedance_ohm=zc, travel_time_s=tau))
        solver = Solver(ckt, dt=1.0e-7)
        vk = solver.add_probe(NodeVoltageProbe("vk", "k"))
        vm = solver.add_probe(NodeVoltageProbe("vm", "m"))
        solver.run(5.0 * tau)
        assert _value_at(vk, 0.5 * tau) == pytest.approx(0.5, rel=1e-9)
        assert _value_at(vm, 0.5 * tau) == pytest.approx(0.0, abs=1e-12)
        assert _value_at(vm, 1.5 * tau) == pytest.approx(1.0, rel=1e-9)
        assert _value_at(vk, 1.5 * tau) == pytest.approx(0.5, rel=1e-9)
        assert _value_at(vk, 2.5 * tau) == pytest.approx(1.0, rel=1e-9)

    def test_terminacao_casada_nao_reflete(self):
        """R_carga = Z_c: v_k permanece em 0,5 V indefinidamente."""
        zc, tau = 100.0, 10.0e-6
        ckt = Circuit("casada")
        ckt.add(_dc_source("E", "s", "gnd", 1.0))
        ckt.add(Resistor("Rs", "s", "k", zc))
        ckt.add(BergeronLine("LN", "k", "m", surge_impedance_ohm=zc, travel_time_s=tau))
        ckt.add(Resistor("RL", "m", "gnd", zc))
        solver = Solver(ckt, dt=1.0e-7)
        vk = solver.add_probe(NodeVoltageProbe("vk", "k"))
        vm = solver.add_probe(NodeVoltageProbe("vm", "m"))
        solver.run(6.0 * tau)
        depois = vk.values[2:]
        assert float(np.max(np.abs(depois - 0.5))) < 1.0e-12
        assert _value_at(vm, 1.5 * tau) == pytest.approx(0.5, rel=1e-9)

    @pytest.mark.parametrize("tau", [1.0e-6, 1.05e-6, 1.37e-6])
    def test_interpolacao_de_historico_com_tau_fracionario(self, tau):
        """Linha casada nas duas pontas: v_m(t) = ½·e(t − τ) EXATAMENTE.

        Com Δt = 0,1 µs, τ = 1,05 µs e τ = 1,37 µs NÃO são múltiplos
        inteiros do passo; o histórico em ``t − τ`` cai entre duas
        amostras e só a interpolação linear reproduz o atraso correto.
        O erro contra o atraso analítico permanece na ordem de Δt² da
        própria interpolação.
        """
        zc, dt, freq = 100.0, 1.0e-7, 1.0e5
        ckt = Circuit("interp")
        ckt.add(VoltageSource("E", "s", "gnd", amplitude_V=1.0, frequency_Hz=freq))
        ckt.add(Resistor("Rs", "s", "k", zc))
        ckt.add(BergeronLine("LN", "k", "m", surge_impedance_ohm=zc, travel_time_s=tau))
        ckt.add(Resistor("RL", "m", "gnd", zc))
        solver = Solver(ckt, dt=dt)
        vm = solver.add_probe(NodeVoltageProbe("vm", "m"))
        solver.run(3.0e-5)
        t = vm.time_s
        w = 2.0 * math.pi * freq
        exato = 0.5 * np.sin(w * (t - tau))
        mascara = t > 2.0 * tau
        erro = float(np.max(np.abs(vm.values[mascara] - exato[mascara])))
        assert erro < 2.0e-3, f"τ = {tau:.3g} s, erro máximo {erro:.3e}"

    def test_perdas_concentradas_exatas_em_corrente_continua(self):
        """R/4, R/2, R/4: em regime contínuo a linha vale exatamente R.

        Fonte 100 V, R_linha = 4 Ω, carga 96 Ω ⇒ I = 1,000 A.
        """
        ckt = Circuit("perdas")
        ckt.add(_dc_source("E", "s", "gnd", 100.0))
        linha = ckt.add(
            BergeronLine(
                "LN",
                "s",
                "m",
                surge_impedance_ohm=100.0,
                travel_time_s=1.0e-6,
                resistance_ohm=4.0,
            )
        )
        ckt.add(Resistor("RL", "m", "gnd", 96.0))
        solver = Solver(ckt, dt=1.0e-8)
        i_k = solver.add_probe(BranchCurrentProbe("ik", linha, terminal=0))
        i_m = solver.add_probe(BranchCurrentProbe("im", linha, terminal=1))
        solver.run(1.0e-4)
        assert i_k.values[-1] == pytest.approx(1.0, rel=1e-9)
        assert i_m.values[-1] == pytest.approx(-1.0, rel=1e-9)
        assert linha.attenuation_factor == pytest.approx((100.0 - 1.0) / (100.0 + 1.0))

    def test_validacao_de_parametros_da_linha(self):
        with pytest.raises(ValueError):
            BergeronLine("L1", "a", "b", surge_impedance_ohm=0.0, travel_time_s=1e-6)
        with pytest.raises(ValueError):
            BergeronLine("L2", "a", "b", surge_impedance_ohm=50.0, travel_time_s=0.0)
        with pytest.raises(ValueError):
            BergeronLine(
                "L3", "a", "b", surge_impedance_ohm=50.0, travel_time_s=1e-6,
                resistance_ohm=-1.0,
            )
        with pytest.raises(ValueError):
            # R/4 >= Z_c invalida a aproximação de perdas concentradas.
            BergeronLine(
                "L4", "a", "b", surge_impedance_ohm=10.0, travel_time_s=1e-6,
                resistance_ohm=40.0,
            )
        with pytest.raises(ValueError):
            BergeronLine("L5", "a", "a", surge_impedance_ohm=50.0, travel_time_s=1e-6)


# ---------------------------------------------------------------------------
# 5. Amortecimento crítico (CDA) — o requisito de validade do projeto
# ---------------------------------------------------------------------------


def _circuito_de_chopping(cda: bool, cda_full_steps: int = 1):
    """Interrupção de corrente indutiva por chave ideal.

    V = 100 V, R = 1 Ω, L = 1 mH (corrente de regime 100 A), chave em
    série aberta em t = 5 ms, com R_p = 100 kΩ em paralelo para dar
    caminho à corrente. Após a abertura, R_p·Δt/(2L) = 50 ⟹ o polo
    trapezoidal vale z = (1−50)/(1+50) = −0,9608: oscilação de período
    2Δt praticamente sem amortecimento — o artefato que o CDA suprime.
    """
    V, R, L, RP, DT = 100.0, 1.0, 1.0e-3, 1.0e5, 1.0e-6
    ckt = Circuit("chopping")
    ckt.add(_dc_source("E", "1", "gnd", V))
    ckt.add(Resistor("R", "1", "2", R))
    ind = ckt.add(Inductor("L", "2", "3", L))
    sw = ckt.add(Switch("SW", "3", "gnd", closed=True))
    ckt.add(Resistor("Rp", "3", "gnd", RP))
    solver = Solver(ckt, dt=DT, cda_enabled=cda, cda_full_steps=cda_full_steps)
    i_l = solver.add_probe(BranchCurrentProbe("iL", ind))
    v_sw = solver.add_probe(DifferentialVoltageProbe("v_sw", "3", "gnd"))
    resultado = solver.run(
        5.05e-3, controllers=[TimedSwitchController(sw, open_time_s=5.0e-3)]
    )
    k = int(np.searchsorted(i_l.time_s, 5.0e-3))
    janela = i_l.values[k + cda_full_steps + 2 : k + cda_full_steps + 42]
    sinais = np.sign(janela)
    alternancias = int(np.sum(sinais[1:] * sinais[:-1] < 0))
    return {
        "alternancias": alternancias,
        "amplitude": float(np.max(np.abs(janela))),
        "regime": V / (R + RP),
        "pico_v": float(np.max(np.abs(v_sw.values))),
        "stats": resultado,
        "solver": solver,
    }


class TestAmortecimentoCritico:
    def test_oscilacao_numerica_aparece_com_cda_desligado(self):
        """DEMONSTRAÇÃO do artefato: sem CDA a corrente alterna a cada Δt.

        [CÁLCULO PRÓPRIO] 39 inversões de sinal em 40 amostras e
        amplitude ~1,8 A contra corrente de regime de 1,0 mA — três
        ordens de grandeza de erro numérico puro.
        """
        r = _circuito_de_chopping(cda=False)
        assert r["alternancias"] >= 35, r["alternancias"]
        assert r["amplitude"] > 500.0 * r["regime"], r["amplitude"]

    def test_cda_suprime_a_oscilacao_numerica(self):
        """Um passo de CDA (padrão do ATP) reduz o artefato em ~50 vezes."""
        sem = _circuito_de_chopping(cda=False)
        com = _circuito_de_chopping(cda=True)
        assert com["amplitude"] < sem["amplitude"] / 20.0, (
            sem["amplitude"], com["amplitude"]
        )

    def test_dois_passos_de_cda_eliminam_a_oscilacao(self):
        """Com cda_full_steps=2 a corrente cai ao valor de regime, sem alternância.

        [CÁLCULO PRÓPRIO] amplitude/regime = 1,014 e zero inversões de
        sinal na janela pós-evento.
        """
        r = _circuito_de_chopping(cda=True, cda_full_steps=2)
        assert r["alternancias"] == 0
        assert r["amplitude"] < 1.1 * r["regime"]

    def test_cda_nao_amortece_o_transitorio_fisico_com_snubber(self):
        """Com capacitância de snubber o transitório é físico e resolvido.

        Interrompendo i₀ = 100 A num indutor de 1 mH descarregando em um
        capacitor de 10 nF, a TRV é uma senoide de amplitude
        ``i₀·√(L/C) = 100·316,2 = 31,62 kV`` e frequência
        ``1/(2π√(LC)) = 50,3 kHz``. Como não há ramo rígido, não existe
        artefato a suprimir: as soluções com e sem CDA coincidem e ambas
        reproduzem a amplitude analítica. Isso demonstra que o CDA NÃO é
        um amortecedor cego do fenômeno real.
        """
        V, R, L, CS = 100.0, 1.0, 1.0e-3, 1.0e-8
        picos = []
        for cda in (False, True):
            ckt = Circuit("snubber")
            ckt.add(_dc_source("E", "1", "gnd", V))
            ckt.add(Resistor("R", "1", "2", R))
            # Condição inicial de regime imposta (i₀ = V/R = 100 A): evita
            # simular a janela de acomodação de 5·L/R antes da manobra.
            ckt.add(Inductor("L", "2", "3", L, initial_current_A=V / R))
            sw = ckt.add(Switch("SW", "3", "gnd", closed=True))
            ckt.add(Capacitor("Cs", "3", "gnd", CS))
            solver = Solver(ckt, dt=1.0e-8, cda_enabled=cda)
            v_sw = solver.add_probe(DifferentialVoltageProbe("v_sw", "3", "gnd"))
            solver.run(4.0e-5, controllers=[TimedSwitchController(sw, open_time_s=1.0e-5)])
            picos.append(float(np.max(np.abs(v_sw.values))))
        analitico = (V / R) * math.sqrt(L / CS)
        assert picos[0] == pytest.approx(analitico, rel=0.02)
        assert picos[1] == pytest.approx(analitico, rel=0.02)
        assert picos[1] == pytest.approx(picos[0], rel=1e-3)

    def test_registro_de_meios_passos_preserva_o_pico_interno(self):
        """``record_half_steps=True`` expõe a amostra interna do par CDA.

        No circuito rígido sem snubber o maior valor calculado pelo
        solver ocorre no PRIMEIRO meio-passo; sem o registro opcional
        ele não aparece na série.
        """
        def pico(record: bool) -> float:
            ckt = Circuit("meio_passo")
            ckt.add(_dc_source("E", "1", "gnd", 100.0))
            ckt.add(Resistor("R", "1", "2", 1.0))
            ckt.add(Inductor("L", "2", "3", 1.0e-3))
            sw = ckt.add(Switch("SW", "3", "gnd", closed=True))
            ckt.add(Resistor("Rp", "3", "gnd", 1.0e5))
            solver = Solver(ckt, dt=1.0e-6, record_half_steps=record)
            v = solver.add_probe(DifferentialVoltageProbe("v_sw", "3", "gnd"))
            solver.run(5.01e-3, controllers=[TimedSwitchController(sw, open_time_s=5.0e-3)])
            return float(np.max(np.abs(v.values)))

        assert pico(True) > 10.0 * pico(False)

    def test_contagem_de_eventos_de_cda(self):
        """Um CDA na partida (histórico consistente) e um por manobra."""
        r = _circuito_de_chopping(cda=True)
        assert r["stats"].cda_events == 2
        assert r["stats"].topology_changes == 1
        sem = _circuito_de_chopping(cda=False)
        assert sem["stats"].cda_events == 0

    def test_modo_de_integracao_invalido_e_recusado(self):
        ckt = Circuit("modo_ruim")
        ckt.add(Resistor("R", "1", "gnd", 10.0))
        ckt.add(Capacitor("C", "1", "gnd", 1.0e-9))
        ckt.build()
        ckt.prepare(1.0e-6)
        with pytest.raises(ValueError):
            ckt.assemble_rhs(0.0, "regra_do_ponto_medio")


# ---------------------------------------------------------------------------
# 6. Fatoração LU e cache por assinatura de topologia
# ---------------------------------------------------------------------------


def _circuito_com_manobras(dt: float):
    """Circuito cuja chave alterna a cada 10 passos (2 topologias)."""
    ckt = Circuit("manobras")
    ckt.add(_dc_source("E", "1", "gnd", 10.0))
    ckt.add(Resistor("R", "1", "2", 10.0))
    sw = ckt.add(Switch("SW", "2", "gnd", closed=True))
    ckt.add(Resistor("Rp", "2", "gnd", 1.0e3))
    ckt.add(Capacitor("C", "2", "gnd", 1.0e-9))

    def controlador(t: float, solver) -> None:
        n = int(round(t / dt))
        sw.set_state((n // 10) % 2 == 0)

    return ckt, controlador


class TestFatoracaoECache:
    def test_lu_reproduz_numpy_linalg_solve(self):
        rng = np.random.default_rng(20260903)
        A = rng.normal(size=(9, 9)) + 9.0 * np.eye(9)
        b = rng.normal(size=9)
        lu, piv = lu_factor(A)
        x = lu_solve(lu, piv, b)
        assert np.allclose(x, np.linalg.solve(A, b), rtol=1e-10, atol=1e-12)

    def test_lu_detecta_matriz_singular(self):
        A = np.array([[1.0, 2.0], [2.0, 4.0]])
        with pytest.raises(SingularSystemError):
            lu_factor(A)

    def test_lu_recusa_matriz_nao_quadrada(self):
        with pytest.raises(ValueError):
            lu_factor(np.zeros((2, 3)))

    def test_no_flutuante_produz_sistema_singular(self):
        ckt = Circuit("flutuante")
        ckt.add(Resistor("R1", "1", "gnd", 10.0))
        ckt.add(Switch("SW", "2", "3", closed=False))
        solver = Solver(ckt, dt=1.0e-6)
        with pytest.raises(SingularSystemError):
            solver.run(1.0e-5)

    def test_cache_devolve_o_mesmo_resultado(self):
        dt = 1.0e-6
        ckt1, ctrl1 = _circuito_com_manobras(dt)
        s1 = Solver(ckt1, dt=dt, use_cached_factorization=True)
        p1 = s1.add_probe(NodeVoltageProbe("v2", "2"))
        r1 = s1.run(1.0e-4, controllers=[ctrl1])

        ckt2, ctrl2 = _circuito_com_manobras(dt)
        s2 = Solver(ckt2, dt=dt, use_cached_factorization=False)
        p2 = s2.add_probe(NodeVoltageProbe("v2", "2"))
        r2 = s2.run(1.0e-4, controllers=[ctrl2])

        assert np.array_equal(p1.values, p2.values)
        assert np.array_equal(p1.time_s, p2.time_s)
        assert r1.topology_changes == r2.topology_changes

    def test_cache_reduz_o_numero_de_fatoracoes(self):
        """Duas topologias recorrentes ⇒ 2 fatorações com cache, 11 sem."""
        dt = 1.0e-6
        ckt1, ctrl1 = _circuito_com_manobras(dt)
        s1 = Solver(ckt1, dt=dt, use_cached_factorization=True)
        r1 = s1.run(1.0e-4, controllers=[ctrl1])
        ckt2, ctrl2 = _circuito_com_manobras(dt)
        s2 = Solver(ckt2, dt=dt, use_cached_factorization=False)
        r2 = s2.run(1.0e-4, controllers=[ctrl2])
        assert r1.factorizations == 2
        assert s1.cache_entries == 2
        assert r1.cache_hits == r1.topology_changes + 1 - r1.factorizations
        assert r2.factorizations > r1.factorizations
        assert r2.cache_hits == 0

    @pytest.mark.parametrize("estrategia", ["auto", "inverse", "lu"])
    def test_estrategias_de_solucao_coincidem(self, estrategia):
        """As três estratégias resolvem o mesmo sistema com a mesma resposta.

        [CÁLCULO PRÓPRIO] Erro relativo entre a aplicação por inversa
        cacheada e a substituição LU numa matriz MNA real (n = 7,
        κ₁ = 2,2·10²): 9,2·10⁻¹⁷ — irrelevante fisicamente.
        """
        R, C = 1000.0, 1.0e-6
        ckt = Circuit(f"estrat_{estrategia}")
        ckt.add(VoltageSource("E", "1", "gnd", amplitude_V=100.0, frequency_Hz=1000.0))
        ckt.add(Resistor("R", "1", "2", R))
        ckt.add(Capacitor("C", "2", "gnd", C))
        solver = Solver(ckt, dt=1.0e-7, solve_strategy=estrategia)
        vc = solver.add_probe(NodeVoltageProbe("vc", "2"))
        solver.run(2.0e-3)
        w = 2.0 * math.pi * 1000.0
        tau = R * C
        amp = 100.0 / (1.0 + (w * tau) ** 2)
        t = vc.time_s
        exato = amp * (np.sin(w * t) - w * tau * np.cos(w * t)) + amp * w * tau * np.exp(
            -t / tau
        )
        assert float(np.max(np.abs(vc.values - exato))) < 1.0e-5

    def test_fatoracao_escolhe_inversa_ou_lu_por_condicionamento(self):
        """κ₁ = 2,0·10¹² > 10¹⁰ ⇒ 'auto' abandona a inversa e usa LU."""
        from app.simulation.emt.circuit import INVERSE_CONDITION_LIMIT, _Factorization

        bem = np.array([[2.0, -1.0], [-1.0, 2.0]])
        mal = np.array([[1.0e3 + 1.0e-9, -1.0e3], [-1.0e3, 1.0e3 + 1.0e-9]])
        f_bem = _Factorization(bem, "auto")
        assert f_bem.use_inverse is True
        assert f_bem.condition_estimate < INVERSE_CONDITION_LIMIT
        f_mal = _Factorization(mal, "auto")
        assert f_mal.use_inverse is False
        assert f_mal.condition_estimate > INVERSE_CONDITION_LIMIT
        # Forçada, a inversa é usada mesmo mal condicionada.
        assert _Factorization(mal, "inverse").use_inverse is True
        # Em modo 'lu' a inversa sequer é calculada.
        f_lu = _Factorization(mal, "lu")
        assert f_lu.use_inverse is False and f_lu.inverse is None
        b = np.array([1.0, -1.0])
        assert np.allclose(f_bem.apply(b), np.linalg.solve(bem, b))

    def test_fallback_de_condicionamento_e_registrado_em_log(self, caplog):
        ckt = Circuit("mal_condicionado")
        ckt.add(Resistor("R1", "1", "gnd", 1.0e9))
        ckt.add(Resistor("R2", "1", "2", 1.0e-3))
        ckt.add(Resistor("R3", "2", "gnd", 1.0e9))
        solver = Solver(ckt, dt=1.0e-6)
        with caplog.at_level("WARNING", logger="app.simulation.emt.circuit"):
            solver.run(1.0e-5)
        assert any("condicionamento estimado" in r.message for r in caplog.records)

    def test_estrategia_de_solucao_invalida_e_recusada(self):
        ckt = Circuit("estrat_ruim")
        ckt.add(_dc_source("E", "1", "gnd", 1.0))
        ckt.add(Resistor("R", "1", "gnd", 1.0))
        with pytest.raises(ValueError):
            Solver(ckt, dt=1.0e-6, solve_strategy="gauss_seidel")

    def test_cache_com_capacidade_unitaria_ainda_converge(self):
        """Com cache_size=1 há descarte (log de WARNING) mas o resultado é o mesmo."""
        dt = 1.0e-6
        ckt1, ctrl1 = _circuito_com_manobras(dt)
        s1 = Solver(ckt1, dt=dt, use_cached_factorization=True)
        p1 = s1.add_probe(NodeVoltageProbe("v2", "2"))
        s1.run(1.0e-4, controllers=[ctrl1])
        ckt2, ctrl2 = _circuito_com_manobras(dt)
        s2 = Solver(ckt2, dt=dt, use_cached_factorization=True, cache_size=1)
        p2 = s2.add_probe(NodeVoltageProbe("v2", "2"))
        s2.run(1.0e-4, controllers=[ctrl2])
        assert np.array_equal(p1.values, p2.values)
        assert s2.cache_entries == 1


# ---------------------------------------------------------------------------
# 7. Convergência com refino do passo
# ---------------------------------------------------------------------------


def _erro_rc_senoidal(dt: float) -> float:
    """Erro máximo do RC excitado por senoide contra a solução fechada.

    Para e(t) = V sin(ωt) e condição inicial nula::

        v_C(t) = A[sin(ωt) − ωτ cos(ωt)] + A·ωτ·e^(−t/τ),
        A = V/(1 + (ωτ)²),  τ = RC
    """
    R, C, V, f = 1000.0, 1.0e-6, 100.0, 1000.0
    ckt = Circuit("rc_sen")
    ckt.add(VoltageSource("E", "1", "gnd", amplitude_V=V, frequency_Hz=f))
    ckt.add(Resistor("R", "1", "2", R))
    ckt.add(Capacitor("C", "2", "gnd", C))
    solver = Solver(ckt, dt=dt)
    vc = solver.add_probe(NodeVoltageProbe("vc", "2"))
    solver.run(2.0e-3)
    w = 2.0 * math.pi * f
    tau = R * C
    amp = V / (1.0 + (w * tau) ** 2)
    t = vc.time_s
    exato = amp * (np.sin(w * t) - w * tau * np.cos(w * t)) + amp * w * tau * np.exp(
        -t / tau
    )
    return float(np.max(np.abs(vc.values - exato)))


class TestConvergencia:
    def test_ordem_dois_com_excitacao_senoidal(self):
        """Regra trapezoidal: erro ∝ Δt². Razão medida ≈ 0,25 ao halvar Δt."""
        e1 = _erro_rc_senoidal(4.0e-7)
        e2 = _erro_rc_senoidal(2.0e-7)
        e3 = _erro_rc_senoidal(1.0e-7)
        assert e3 < e2 < e1
        assert e2 / e1 == pytest.approx(0.25, rel=0.05)
        assert e3 / e2 == pytest.approx(0.25, rel=0.05)

    def test_ordem_dois_no_degrau_continuo(self):
        """O CDA de partida preserva a ordem 2 mesmo com degrau em t = 0.

        Sem o par de meios-passos inicial, o histórico inconsistente do
        capacitor (i(0⁻) = 0 contra i(0⁺) = V/R) degrada o erro para
        O(Δt) [CÁLCULO PRÓPRIO desta sessão].
        """
        R, C = 1000.0, 1.0e-6
        alvo = 100.0 * (1.0 - math.exp(-1.0))

        def erro(dt: float) -> float:
            ckt = Circuit("rc_deg")
            ckt.add(_dc_source("E", "1", "gnd", 100.0))
            ckt.add(Resistor("R", "1", "2", R))
            ckt.add(Capacitor("C", "2", "gnd", C))
            solver = Solver(ckt, dt=dt)
            vc = solver.add_probe(NodeVoltageProbe("vc", "2"))
            solver.run(1.0e-3)
            return abs(float(vc.values[-1]) - alvo)

        e1, e2 = erro(4.0e-7), erro(2.0e-7)
        assert e2 / e1 == pytest.approx(0.25, rel=0.05)

    def test_convergencia_do_pico_de_rlc(self):
        """O pico do RLC converge para o valor analítico com o refino."""
        R, L, C, V = 10.0, 1.0e-3, 1.0e-6, 1.0
        alpha = R / (2.0 * L)
        wd = math.sqrt(1.0 / (L * C) - alpha * alpha)
        alvo = V * (1.0 + math.exp(-alpha * math.pi / wd))

        def pico(dt: float) -> float:
            ckt = Circuit("rlc_conv")
            ckt.add(_dc_source("E", "1", "gnd", V))
            ckt.add(Resistor("R", "1", "2", R))
            ckt.add(Inductor("L", "2", "3", L))
            ckt.add(Capacitor("C", "3", "gnd", C))
            solver = Solver(ckt, dt=dt)
            vc = solver.add_probe(NodeVoltageProbe("vc", "3"))
            solver.run(3.0e-4)
            return float(np.max(vc.values))

        assert abs(pico(2.0e-8) - alvo) < abs(pico(2.0e-7) - alvo)


# ---------------------------------------------------------------------------
# 8. Ramo RL acoplado e fontes trifásicas
# ---------------------------------------------------------------------------


class TestCoupledRLeTrifasico:
    def test_coupled_rl_sem_acoplamento_equivale_a_indutores_isolados(self):
        L = np.array([[1.0e-3, 0.0], [0.0, 2.0e-3]])
        ckt = Circuit("crl")
        ckt.add(_dc_source("E", "1", "gnd", 10.0))
        crl = ckt.add(CoupledRL("T", [("1", "2"), ("3", "gnd")], L))
        ckt.add(Resistor("R1", "2", "gnd", 10.0))
        ckt.add(Resistor("R2", "3", "gnd", 10.0))
        solver = Solver(ckt, dt=1.0e-8)
        i1 = solver.add_probe(BranchCurrentProbe("i1", crl, terminal=0))
        i2 = solver.add_probe(BranchCurrentProbe("i2", crl, terminal=1))
        solver.run(5.0e-4)
        analitico = 1.0 * (1.0 - np.exp(-i1.time_s * 10.0 / 1.0e-3))
        assert float(np.max(np.abs(i1.values - analitico))) < 1.0e-6
        assert float(np.max(np.abs(i2.values))) < 1.0e-12

    def test_coupled_rl_transfere_tensao_com_acoplamento_forte(self):
        """k = M/√(L₁L₂) = 0,999 e carga alta ⇒ v₂ ≈ v₁ (relação 1:1)."""
        m = 0.999e-3
        L = np.array([[1.0e-3, m], [m, 1.0e-3]])
        ckt = Circuit("trafo")
        ckt.add(VoltageSource("E", "1", "gnd", amplitude_V=1000.0, frequency_Hz=60.0))
        ckt.add(CoupledRL("T", [("1", "gnd"), ("2", "gnd")], L, resistance_ohm=0.01))
        ckt.add(Resistor("RL", "2", "gnd", 1000.0))
        solver = Solver(ckt, dt=1.0e-6)
        v2 = solver.add_probe(NodeVoltageProbe("v2", "2"))
        solver.run(0.05)
        pico = float(np.max(np.abs(v2.values[-8000:])))
        assert pico == pytest.approx(1000.0, rel=0.05)

    def test_coupled_rl_valida_matriz_de_indutancias(self):
        with pytest.raises(ValueError):
            CoupledRL("T1", [("1", "gnd")], np.array([[0.0]]))
        with pytest.raises(ValueError):
            CoupledRL("T2", [("1", "gnd"), ("2", "gnd")], np.array([[1e-3, 1.0], [0.0, 1e-3]]))
        with pytest.raises(ValueError):
            # Não definida positiva (k > 1 é fisicamente impossível).
            CoupledRL(
                "T3", [("1", "gnd"), ("2", "gnd")],
                np.array([[1e-3, 2e-3], [2e-3, 1e-3]]),
            )
        with pytest.raises(ValueError):
            CoupledRL("T4", [("1", "1")], np.array([[1e-3]]))

    def test_fontes_trifasicas_defasagem_e_soma_nula(self):
        fontes = three_phase_voltage_sources(
            "E", ["a", "b", "c"], "gnd", amplitude_V=100.0, frequency_Hz=60.0,
            phase_deg=17.0,
        )
        assert [f.phase_deg for f in fontes] == [17.0, -103.0, 137.0]
        for t in (0.0, 1.0e-3, 4.2e-3):
            assert sum(f.value_at(t) for f in fontes) == pytest.approx(0.0, abs=1e-9)
        inversa = three_phase_voltage_sources(
            "F", ["a", "b", "c"], "gnd", amplitude_V=1.0, sequence="acb"
        )
        assert [f.phase_deg for f in inversa] == [0.0, 120.0, -120.0]
        with pytest.raises(ValueError):
            three_phase_voltage_sources("G", ["a", "b"], "gnd", amplitude_V=1.0)
        with pytest.raises(ValueError):
            three_phase_voltage_sources(
                "H", ["a", "b", "c"], "gnd", amplitude_V=1.0, sequence="cba"
            )


# ---------------------------------------------------------------------------
# 9. Validação de entradas
# ---------------------------------------------------------------------------


class TestValidacao:
    @pytest.mark.parametrize(
        "fabrica",
        [
            lambda: Resistor("R", "1", "gnd", 0.0),
            lambda: Resistor("R", "1", "gnd", -5.0),
            lambda: Inductor("L", "1", "gnd", 0.0),
            lambda: Capacitor("C", "1", "gnd", -1.0e-9),
            lambda: Resistor("R", "1", "1", 10.0),
            lambda: Inductor("L", "1", "1", 1e-3),
            lambda: Capacitor("C", "1", "1", 1e-9),
            lambda: Switch("SW", "1", "1"),
            lambda: Resistor("", "1", "gnd", 10.0),
            lambda: Resistor("R", "1", "gnd", float("nan")),
        ],
    )
    def test_parametros_invalidos_levantam_value_error(self, fabrica):
        with pytest.raises(ValueError):
            fabrica()

    def test_circuito_sem_terra_e_recusado(self):
        ckt = Circuit("sem_terra")
        ckt.add(Resistor("R", "1", "2", 10.0))
        with pytest.raises(ValueError):
            ckt.build()

    def test_circuito_vazio_e_recusado(self):
        with pytest.raises(ValueError):
            Circuit("vazio").build()

    def test_nome_de_componente_duplicado_e_recusado(self):
        ckt = Circuit("dup")
        ckt.add(Resistor("R", "1", "gnd", 10.0))
        with pytest.raises(ValueError):
            ckt.add(Resistor("R", "2", "gnd", 20.0))

    def test_componente_de_tipo_errado_e_recusado(self):
        with pytest.raises(ValueError):
            Circuit("tipo").add("não é um componente")  # type: ignore[arg-type]

    def test_passo_e_horizonte_invalidos(self):
        ckt = Circuit("passo")
        ckt.add(_dc_source("E", "1", "gnd", 1.0))
        ckt.add(Resistor("R", "1", "gnd", 1.0))
        with pytest.raises(ValueError):
            Solver(ckt, dt=0.0)
        with pytest.raises(ValueError):
            Solver(ckt, dt=1.0e-6, cda_full_steps=0)
        with pytest.raises(ValueError):
            Solver(ckt, dt=1.0e-6, cache_size=0)
        solver = Solver(ckt, dt=1.0e-6)
        with pytest.raises(ValueError):
            solver.run(-1.0)
        with pytest.raises(ValueError):
            solver.run(1.0e-3, dt=-1.0)
        with pytest.raises(ValueError):
            # t_end menor que o passo.
            solver.run(1.0e-9)

    def test_controlador_nao_chamavel_e_recusado(self):
        ckt = Circuit("ctrl")
        ckt.add(_dc_source("E", "1", "gnd", 1.0))
        ckt.add(Resistor("R", "1", "gnd", 1.0))
        solver = Solver(ckt, dt=1.0e-6)
        with pytest.raises(ValueError):
            solver.run(1.0e-5, controllers=["não chamável"])  # type: ignore[list-item]

    def test_sonda_em_no_inexistente_e_recusada(self):
        ckt = Circuit("sonda")
        ckt.add(_dc_source("E", "1", "gnd", 1.0))
        ckt.add(Resistor("R", "1", "gnd", 1.0))
        solver = Solver(ckt, dt=1.0e-6)
        solver.add_probe(NodeVoltageProbe("vX", "42"))
        with pytest.raises(ValueError):
            solver.run(1.0e-5)

    def test_terminal_de_sonda_fora_da_faixa(self):
        r = Resistor("R", "1", "gnd", 10.0)
        with pytest.raises(ValueError):
            BranchCurrentProbe("i", r, terminal=1)
        with pytest.raises(ValueError):
            BranchVoltageProbe("v", r, terminal=-1)


# ---------------------------------------------------------------------------
# 10. Sondas, integração com o prognóstico e auditoria
# ---------------------------------------------------------------------------


class TestSondasEIntegracao:
    def test_sondas_sao_consistentes_entre_si(self):
        ckt = Circuit("sondas")
        ckt.add(_dc_source("E", "1", "gnd", 12.0))
        r1 = ckt.add(Resistor("R1", "1", "2", 2.0))
        ckt.add(Resistor("R2", "2", "gnd", 4.0))
        solver = Solver(ckt, dt=1.0e-6)
        v1 = solver.add_probe(NodeVoltageProbe("v1", "1"))
        v2 = solver.add_probe(NodeVoltageProbe("v2", "2"))
        vr1 = solver.add_probe(BranchVoltageProbe("vR1", r1))
        ir1 = solver.add_probe(BranchCurrentProbe("iR1", r1))
        dif = solver.add_probe(DifferentialVoltageProbe("d", "1", "2"))
        solver.run(1.0e-5)
        assert v1.values[-1] == pytest.approx(12.0)
        assert v2.values[-1] == pytest.approx(8.0)
        assert vr1.values[-1] == pytest.approx(4.0)
        assert dif.values[-1] == pytest.approx(4.0)
        assert ir1.values[-1] == pytest.approx(2.0)
        assert vr1.peak() == pytest.approx(4.0)

    def test_conversao_para_kv_e_recusa_de_sonda_de_corrente(self):
        ckt = Circuit("kv")
        ckt.add(_dc_source("E", "1", "gnd", 4160.0))
        r = ckt.add(Resistor("R", "1", "gnd", 10.0))
        solver = Solver(ckt, dt=1.0e-6)
        v1 = solver.add_probe(NodeVoltageProbe("v1", "1"))
        i1 = solver.add_probe(BranchCurrentProbe("i1", r))
        solver.run(1.0e-5)
        assert to_kV(v1)[-1] == pytest.approx(4.16)
        with pytest.raises(ValueError):
            to_kV(i1)

    def test_sonda_alimenta_extract_stress_events(self):
        """A série da sonda produz StressProfile válido no núcleo de RUL."""
        ckt = Circuit("estresse")
        ckt.add(VoltageSource("E", "1", "gnd", amplitude_V=5000.0, frequency_Hz=60.0))
        ckt.add(Resistor("R", "1", "2", 1.0))
        ckt.add(Capacitor("C", "2", "gnd", 1.0e-9))
        solver = Solver(ckt, dt=1.0e-6)
        v2 = solver.add_probe(NodeVoltageProbe("v2", "2"))
        solver.run(0.02)
        perfil = to_stress_profile(v2, threshold_kV=3.0, surge_impedance_ohm=50.0)
        assert len(perfil.events) >= 2
        assert perfil.sampling_step_s == pytest.approx(1.0e-6, rel=1e-6)
        evento = perfil.events[0]
        assert abs(evento.V_pk_kV) == pytest.approx(5.0, rel=1e-3)
        assert evento.T1_us > 0.0
        assert evento.energy_J > 0.0
        assert evento.source.startswith("emt:")

    def test_execucao_e_deterministica(self):
        """Duas execuções idênticas produzem séries bit a bit iguais."""

        def executa():
            ckt = Circuit("det")
            ckt.add(VoltageSource("E", "1", "gnd", amplitude_V=100.0, frequency_Hz=60.0))
            ckt.add(Resistor("R", "1", "2", 5.0))
            ind = ckt.add(Inductor("L", "2", "3", 1.0e-3))
            sw = ckt.add(Switch("SW", "3", "gnd", closed=True))
            ckt.add(Resistor("Rp", "3", "gnd", 1.0e5))
            solver = Solver(ckt, dt=1.0e-6)
            p = solver.add_probe(BranchCurrentProbe("iL", ind))
            solver.run(5.0e-3, controllers=[TimedSwitchController(sw, open_time_s=3.0e-3)])
            return p.values

        assert np.array_equal(executa(), executa())

    def test_callback_por_passo_recebe_todos_os_passos(self):
        ckt = Circuit("callback")
        ckt.add(_dc_source("E", "1", "gnd", 1.0))
        ckt.add(Resistor("R", "1", "gnd", 1.0))
        solver = Solver(ckt, dt=1.0e-6)
        instantes: list[float] = []
        resultado = solver.run(
            1.0e-5, on_step=lambda t, x, s: instantes.append(t)
        )
        assert resultado.steps == 10
        # Não há amostra fabricada em t = 0 (init="zero"):
        # a série começa no primeiro instante efetivamente resolvido.
        assert len(instantes) == 10
        assert instantes[0] == pytest.approx(1.0e-6)
        assert instantes[-1] == pytest.approx(1.0e-5)
        assert len(resultado.time_s) == 10

    def test_reexecucao_reinicia_o_estado(self):
        ckt = Circuit("reset")
        ckt.add(_dc_source("E", "1", "gnd", 100.0))
        ckt.add(Resistor("R", "1", "2", 1000.0))
        ckt.add(Capacitor("C", "2", "gnd", 1.0e-6))
        solver = Solver(ckt, dt=1.0e-7)
        vc = solver.add_probe(NodeVoltageProbe("vc", "2"))
        solver.run(1.0e-3)
        primeira = vc.values.copy()
        solver.run(1.0e-3)
        assert np.array_equal(primeira, vc.values)

    def test_api_publica_e_limitacoes_declaradas(self):
        """KNOWN_LIMITATIONS segue o padrão do projeto, com prefixo emt_."""
        assert isinstance(KNOWN_LIMITATIONS, dict)
        assert len(KNOWN_LIMITATIONS) >= 10
        assert all(k.startswith("emt_") for k in KNOWN_LIMITATIONS)
        assert all(isinstance(v, str) and len(v) > 60 for v in KNOWN_LIMITATIONS.values())
        for nome in (
            "Circuit", "Solver", "Resistor", "Inductor", "Capacitor",
            "VoltageSource", "Switch", "CoupledRL", "BergeronLine",
            "NodeVoltageProbe", "BranchVoltageProbe", "BranchCurrentProbe",
            "KNOWN_LIMITATIONS",
        ):
            assert nome in EMT_ALL
        import app.simulation.emt as pacote

        for nome in EMT_ALL:
            assert hasattr(pacote, nome), nome

    def test_runner_do_atp_continua_disponivel(self):
        """O motor dedicado não substitui nem quebra o runner do ATP."""
        from app.simulation.runner import AtpRunner

        assert AtpRunner(executable_path=None).is_configured() is False


# ---------------------------------------------------------------------------
# Reancoragem nas fontes primárias (auditoria equação a equação)
# ---------------------------------------------------------------------------


class TestFontesPrimarias:
    """Confronto direto com as equações publicadas e com o caso de referência.

    Cada teste cita a equação da fonte que verifica. Os valores de
    referência da Lista 02 foram medidos pelo autor contra o ATP.
    """

    def test_recursao_do_indutor_dommel_apendice_I(self):
        """``I_L(t) = 2·G_L·v_L(t) + I_L(t−Δt)``.

        [FONTE: Dommel 1969, Apêndice I, p. 395, sinal + para indutância];
        [LISTA: 02, eq. (3)].
        """
        L, dt = 25.0e-3, 10.0e-6
        ind = Inductor("L", "1", "2", L, initial_current_A=1.5, initial_voltage_V=7.0)
        ind.prepare(dt)
        ind.reset()
        g = ind.conductance_S
        assert g == pytest.approx(dt / (2.0 * L), rel=1e-15)
        # I(0) = i(0) + G·v(0) — semeadura de [LISTA: 02, eq. (6)].
        i_hist_0 = ind.history_current_A(MODE_TRAPEZOIDAL)
        assert i_hist_0 == pytest.approx(1.5 + g * 7.0, rel=1e-15)
        # Um passo com v(t) arbitrário deve satisfazer a recursão publicada.
        ind._idx = (0, GROUND_INDEX_LOCAL)
        v1 = -3.25
        ind.commit(np.array([v1]), dt, MODE_TRAPEZOIDAL)
        assert ind.history_current_A(MODE_TRAPEZOIDAL) == pytest.approx(
            2.0 * g * v1 + i_hist_0, rel=1e-14
        )

    def test_recursao_do_capacitor_alterna_de_sinal(self):
        """``I_C(t) = −2·G_C·v_C(t) − I_C(t−Δt)``.

        [FONTE: Dommel 1969, Apêndice I, p. 395, sinal − para capacitância];
        [LISTA: 02, eq. (3)]; [LISTA: 01, §2.1].
        """
        C, dt = 50.0e-9, 1.0e-6
        cap = Capacitor("C", "1", "2", C, initial_voltage_V=84.86, initial_current_A=0.0016)
        cap.prepare(dt)
        cap.reset()
        g = cap.conductance_S
        assert g == pytest.approx(2.0 * C / dt, rel=1e-15)
        # I_C(0) = −[G_C·v_C(0) + i_C(0)] — [LISTA: 02, eq. (6)].
        i_hist_0 = cap.history_current_A(MODE_TRAPEZOIDAL)
        assert i_hist_0 == pytest.approx(-(g * 84.86 + 0.0016), rel=1e-15)
        cap._idx = (0, GROUND_INDEX_LOCAL)
        v1 = 12.5
        cap.commit(np.array([v1]), dt, MODE_TRAPEZOIDAL)
        assert cap.history_current_A(MODE_TRAPEZOIDAL) == pytest.approx(
            -2.0 * g * v1 - i_hist_0, rel=1e-14
        )

    def test_euler_regressivo_meio_passo_lin_marti_eq4(self):
        """BE com Δt/2 dá a MESMA condutância e histórico só de corrente.

        [FONTE: Lin & Martí 1990, eqs. (2)-(4), p. 395]; [LISTA: 01, Tabela 1].
        """
        L, C, dt = 5.0e-3, 50.0e-9, 1.0e-6
        ind = Inductor("L", "1", "gnd", L, initial_current_A=2.0, initial_voltage_V=9.0)
        cap = Capacitor("C", "1", "gnd", C, initial_voltage_V=3.0, initial_current_A=0.5)
        for comp in (ind, cap):
            comp.prepare(dt)
            comp.reset()
        # Condutâncias idênticas nos dois modos: é o que dispensa refatoração.
        assert ind.conductance_S == pytest.approx((0.5 * dt) / L, rel=1e-15)
        assert cap.conductance_S == pytest.approx(C / (0.5 * dt), rel=1e-15)
        # Indutor: h(t) = i(t−Δt/2), SEM o termo de tensão — eq. (4).
        assert ind.history_current_A(MODE_BACKWARD_EULER_HALF) == pytest.approx(2.0)
        # Capacitor: h(t) = −G·v(t−Δt/2), SEM o termo de corrente.
        assert cap.history_current_A(MODE_BACKWARD_EULER_HALF) == pytest.approx(
            -cap.conductance_S * 3.0
        )

    def test_cda_executa_exatamente_dois_meios_passos(self):
        """Um par de meios-passos de Δt/2 por descontinuidade, e só um.

        [FONTE: Lin & Martí 1990, §2, p. 394, itens 4-5]: o segundo
        meio-passo cai em ``t₁ + Δt``, devolvendo a marcha à malha
        uniforme. A amostra intermediária não é registrada nem gera
        decisão de manobra.
        """
        ckt = Circuit("cda")
        ckt.add(_dc_source("E", "1", "gnd", 100.0))
        ckt.add(Resistor("R", "1", "2", 1.0))
        ckt.add(Inductor("L", "2", "3", 1.0e-3))
        sw = ckt.add(Switch("SW", "3", "gnd", closed=True))
        dt = 1.0e-6
        sol = Solver(ckt, dt=dt, cda_at_start=False)
        res = sol.run(
            20.0 * dt, controllers=[TimedSwitchController(sw, open_time_s=10.0 * dt)]
        )
        assert res.topology_changes == 1
        assert res.cda_events == 1          # UM par = DOIS meios-passos
        # A base de tempo permanece uniforme: nenhum ponto Δt/2 vazou.
        passos = np.diff(res.time_s)
        assert np.allclose(passos, dt, rtol=1e-9)

    def test_chave_mna_muda_uma_unica_linha(self):
        """Comutação altera UMA linha; dimensão e posto são invariantes.

        [LISTA: 02, §1.2, eqs. (5) e (18)]; [FONTE: Mahseredjian et al.
        2007, §2, p. 1516, "fixed rank system"].
        """
        ckt = Circuit("mna")
        ckt.add(_dc_source("E", "1", "gnd", 10.0))
        ckt.add(Resistor("R", "1", "2", 1.0))
        sw = ckt.add(Switch("SW", "2", "gnd", closed=False))
        ckt.add(Resistor("Rc", "2", "gnd", 20.0))
        sol = Solver(ckt, dt=1.0e-6)
        A_aberta = sol.matrix.copy()
        sw.close()
        A_fechada = sol.matrix.copy()
        assert A_aberta.shape == A_fechada.shape
        difere = ~np.isclose(A_aberta, A_fechada)
        linhas = sorted(set(np.nonzero(difere)[0].tolist()))
        assert len(linhas) == 1, f"a comutação alterou as linhas {linhas}"
        assert np.linalg.matrix_rank(A_aberta) == np.linalg.matrix_rank(A_fechada)

    def test_linha_sem_perdas_reproduz_dommel_eq7b(self):
        """``I_k(t−τ) = −(1/Z_c)·e_m(t−τ) − i_mk(t−τ)``.

        [FONTE: Dommel 1969, eq. (7b), p. 389]. Com ``R = 0`` a expressão
        implementada deve coincidir termo a termo.
        """
        lin = BergeronLine("T", "k", "m", surge_impedance_ohm=400.0, travel_time_s=5.0e-6)
        assert lin.attenuation_factor == pytest.approx(1.0)
        lin.prepare(1.0e-6)
        lin.reset()
        lin._history.append(1.0e-6, 120.0, 0.4, -30.0, -0.1)
        i_k, i_m = lin._history_sources(1.0e-6 + lin.travel_time_s)
        g = 1.0 / 400.0
        assert i_k == pytest.approx(-(-30.0) * g - (-0.1), rel=1e-14)
        assert i_m == pytest.approx(-120.0 * g - 0.4, rel=1e-14)


class TestCasoReferenciaLista02:
    """Questão 2 da Lista 02 — abertura de disjuntor a vácuo em reator.

    Circuito de [LISTA: 02, §3.1, Figura 6]: ``vs = 100·cos(377t)`` V,
    ``R1 = 0,5 Ω``, ``L1 = 5 mH``, ``R2 = 5 Ω``, ``L2 = 50 mH``,
    ``C = 50 nF``; comando de abertura em ``t0 = 30 ms``, corte quando
    ``|i_s| <= I_mar = 0,5 A``. Os valores de referência foram medidos
    pelo autor contra o ATP e constam das Tabelas 3 e 4.
    """

    W = 377.0
    R1, L1, R2, L2, C = 0.5, 5.0e-3, 5.0, 50.0e-3, 50.0e-9

    @classmethod
    def _fasores(cls):
        """Solução fasorial de regime com o disjuntor fechado.

        Referência: [LISTA: 02, §3.3, eqs. (19)-(23)].
        """
        w = cls.W
        z_c = 1.0 / (1j * w * cls.C)
        z_rl = cls.R2 + 1j * w * cls.L2
        z_reat = z_rl * z_c / (z_rl + z_c)
        z_tot = cls.R1 + 1j * w * cls.L1 + z_reat
        i_s = 100.0 / z_tot
        v_reat = i_s * z_reat
        return i_s, v_reat, v_reat / z_rl, v_reat / z_c, z_reat, z_tot

    @classmethod
    def _circuito(cls, *, semear_derivadas: bool = True):
        i_s, v_reat, i_r, i_c, _, _ = cls._fasores()
        w = cls.W
        ckt = Circuit("lista02_q2")
        ckt.add(
            VoltageSource(
                "E", "1", "gnd", amplitude_V=100.0,
                frequency_Hz=w / (2.0 * math.pi), phase_reference="cos",
            )
        )
        ckt.add(Resistor("R1", "1", "2", cls.R1))
        ckt.add(
            Inductor(
                "L1", "2", "3", cls.L1,
                initial_current_A=i_s.real,
                initial_voltage_V=(1j * w * cls.L1 * i_s).real if semear_derivadas else 0.0,
            )
        )
        sw = ckt.add(Switch("SW", "3", "4", closed=True))
        ckt.add(
            Capacitor(
                "C", "4", "gnd", cls.C,
                initial_voltage_V=v_reat.real,
                initial_current_A=i_c.real if semear_derivadas else 0.0,
            )
        )
        ckt.add(Resistor("R2", "4", "5", cls.R2))
        ckt.add(
            Inductor(
                "L2", "5", "gnd", cls.L2,
                initial_current_A=i_r.real,
                initial_voltage_V=(1j * w * cls.L2 * i_r).real if semear_derivadas else 0.0,
            )
        )
        return ckt, sw

    def test_solucao_fasorial_confere_com_a_lista(self):
        """[LISTA: 02, eqs. (19)-(23)], em acordo com as notas de aula."""
        i_s, v_reat, i_r, _, z_reat, z_tot = self._fasores()
        assert abs(z_reat) == pytest.approx(19.508791, abs=1e-6)
        assert math.degrees(np.angle(z_reat)) == pytest.approx(75.1389, abs=1e-4)
        assert abs(z_tot) == pytest.approx(21.458977, abs=1e-6)
        assert abs(i_s) == pytest.approx(4.660054, abs=1e-6)
        assert math.degrees(np.angle(i_s)) == pytest.approx(-75.1394, abs=1e-4)
        assert abs(v_reat) == pytest.approx(90.912028, abs=1e-6)
        assert abs(i_r) == pytest.approx(4.661711, abs=1e-6)

    def test_partida_em_regime_permanente_sem_transitorio_espurio(self):
        """Desvio contra a solução fasorial da ordem de 1e−10 V.

        Valor de referência do autor, medido contra o ATP: 1,39 × 10⁻¹⁰ V
        [LISTA: 02, §3.7 e Tabela 3]. Exige a semeadura completa
        ``I_L(0) = i_L(0) + G_L·v_L(0)`` e
        ``I_C(0) = −[G_C·v_C(0) + i_C(0)]`` [LISTA: 02, eq. (6)] e a
        ausência de CDA em ``t = 0`` (não há descontinuidade aí).
        """
        _, v_reat, _, _, _, _ = self._fasores()
        ckt, sw = self._circuito()
        sol = Solver(ckt, dt=1.0e-6, cda_at_start=False)
        desvio = [0.0]

        def _passo(t, x, s):
            exato = (v_reat * np.exp(1j * self.W * t)).real
            desvio[0] = max(desvio[0], abs(s.node_voltage("4") - exato))

        sol.run(
            0.029,
            controllers=[TimedSwitchController(sw, open_time_s=0.030, current_margin_A=0.5)],
            on_step=_passo,
        )
        assert desvio[0] < 1.0e-9, f"desvio de regime {desvio[0]:.3e} V"

    def test_semeadura_incompleta_degrada_a_partida(self):
        """Sem ``v_L(0)`` e ``i_C(0)`` o desvio sobe várias ordens.

        É a lacuna corrigida nesta auditoria: [FONTE: Dommel 1969,
        Apêndice I, p. 395] e [LISTA: 02, eq. (6)] exigem os DOIS termos.
        """
        _, v_reat, _, _, _, _ = self._fasores()
        ckt, sw = self._circuito(semear_derivadas=False)
        sol = Solver(ckt, dt=1.0e-6, cda_at_start=False)
        desvio = [0.0]

        def _passo(t, x, s):
            exato = (v_reat * np.exp(1j * self.W * t)).real
            desvio[0] = max(desvio[0], abs(s.node_voltage("4") - exato))

        sol.run(
            0.029,
            controllers=[TimedSwitchController(sw, open_time_s=0.030, current_margin_A=0.5)],
            on_step=_passo,
        )
        assert desvio[0] > 1.0e-6, f"desvio {desvio[0]:.3e} V — semeadura incompleta"

    @pytest.mark.parametrize(
        "dt_us, tc_ms",
        [(4.0, 32.364000), (2.0, 32.362000), (1.0, 32.361000), (0.5, 32.360000)],
    )
    def test_instante_de_corte_reproduz_a_tabela_4(self, dt_us, tc_ms):
        """Critério ``|i_s| <= I_mar`` reproduz a Tabela 4 dígito a dígito.

        [LISTA: 02, Tabela 4], medida pelo autor com a rotina própria e
        confirmada pelo ATP (``*** Open switch "N3" to "N4" after
        3.23600000E-02 sec.``, [LISTA: 02, §3.6]). O instante exato é
        ``t_c = 32,359422 ms``; o resto é a quantização em Δt.
        """
        ckt, sw = self._circuito()
        sol = Solver(ckt, dt=dt_us * 1.0e-6, cda_at_start=False)
        corte = [None]

        def _passo(t, x, s):
            if corte[0] is None and not sw.closed:
                corte[0] = t

        sol.run(
            0.040,
            controllers=[TimedSwitchController(sw, open_time_s=0.030, current_margin_A=0.5)],
            on_step=_passo,
        )
        assert corte[0] is not None, "o disjuntor não interrompeu a corrente"
        assert corte[0] * 1.0e3 == pytest.approx(tc_ms, abs=1.0e-6)

    def test_pico_da_trv_converge_para_o_analitico(self):
        """Pico da TRV entre 5,5 e 5,6 vezes o pico de regime, convergente.

        Referência analítica de [LISTA: 02, §3.4, eq. (26)]: 506,170 V com
        corte exato, isto é 5,57 vezes o pico de regime (90,912 V). O
        pico numérico é sempre inferior porque o corte só pode cair sobre
        um ponto da malha [LISTA: 02, Tabela 4], e cresce
        monotonicamente à medida que Δt diminui.
        """
        picos = []
        for dt in (4.0e-6, 2.0e-6, 1.0e-6, 5.0e-7):
            ckt, sw = self._circuito()
            sol = Solver(ckt, dt=dt, cda_at_start=False)
            pico = [0.0]

            def _passo(t, x, s, pico=pico):
                pico[0] = max(pico[0], abs(s.node_voltage("4")))

            sol.run(
                0.040,
                controllers=[
                    TimedSwitchController(sw, open_time_s=0.030, current_margin_A=0.5)
                ],
                on_step=_passo,
            )
            picos.append(pico[0])
        assert all(b >= a - 1.0e-9 for a, b in zip(picos, picos[1:])), picos
        assert picos[-1] == pytest.approx(506.170, rel=5.0e-3), picos
        assert picos[-1] / 90.912028 == pytest.approx(5.57, abs=0.05)

    def test_sem_margem_de_corrente_nao_ha_sobretensao(self):
        """Sem o campo ``I_mar`` a manobra deixa de representar o VCB.

        [LISTA: 02, §3.6]: "sem o campo Imar o ATP esperaria um zero
        natural de corrente e a sobretensão praticamente desapareceria".
        Aqui o efeito oposto é verificado: a abertura FORÇADA no comando
        (``current_margin_A=None``) corta 3,9 A e produz uma TRV muito
        maior que a do corte por margem — ou seja, o critério não é
        detalhe de implementação, é o modelo físico do disjuntor.
        """
        picos = {}
        for rotulo, margem in (("margem", 0.5), ("forcada", None)):
            ckt, sw = self._circuito()
            sol = Solver(ckt, dt=1.0e-6, cda_at_start=False)
            pico = [0.0]

            def _passo(t, x, s, pico=pico):
                pico[0] = max(pico[0], abs(s.node_voltage("4")))

            sol.run(
                0.040,
                controllers=[
                    TimedSwitchController(sw, open_time_s=0.030, current_margin_A=margem)
                ],
                on_step=_passo,
            )
            picos[rotulo] = pico[0]
        assert picos["forcada"] > 2.0 * picos["margem"], picos
