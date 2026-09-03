"""
tests/test_emt_steady_state.py — verificação da INICIALIZAÇÃO EM REGIME
PERMANENTE SENOIDAL do kernel EMT (``app.simulation.emt.steady_state``)
e do critério de comutação por margem de corrente ``Imar``.

Os valores de referência vêm de três origens, sempre identificadas no
docstring de cada teste:

* [LISTA: 02] — os dois circuitos da Lista 02 do autor (EEE873, UFMG),
  cuja rotina própria em MATLAB foi validada contra o ATP com desvio de
  4,27e−4 V em tensão e 4,83e−7 A em corrente (Tabela 3). São, portanto,
  referência de terceiro nível: analítica → MATLAB → ATP.
* [CÁLCULO PRÓPRIO] — solução fasorial fechada calculada no próprio
  teste, independente do código sob teste.
* medições desta sessão, sempre com a ordem de grandeza justificada.

Reproduções dígito a dígito obtidas aqui (marcha sem CDA, como na rotina
do autor), contra [LISTA: 02, Tabelas 3 e 4]:

======  ===============  ===============
Δt      pico da TRV      Lista 02
======  ===============  ===============
4 µs    501,37 V         501,37 V
2 µs    503,29 V         503,29 V
1 µs    504,292 V        504,292 V
0,5 µs  505,62 V         505,62 V
0,25 µs 505,84 V         505,84 V
======  ===============  ===============
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.simulation.emt import (
    INIT_MODES,
    INIT_STEADY_STATE,
    INIT_ZERO,
    BergeronLine,
    BranchCurrentProbe,
    Capacitor,
    Circuit,
    Component,
    CoupledRL,
    Inductor,
    MultipleFrequenciesError,
    NodeVoltageProbe,
    PhasorSolution,
    Resistor,
    Solver,
    SteadyStateError,
    Switch,
    TimedSwitchController,
    UnsupportedComponentError,
    VoltageSource,
    assemble_phasor_system,
    initialize_steady_state,
    instantaneous,
    solve_phasor,
    source_frequency,
    source_phasor,
    three_phase_voltage_sources,
)
from app.simulation.emt import KNOWN_LIMITATIONS
from app.simulation.emt.steady_state import _line_admittance


# ---------------------------------------------------------------------------
# Dados dos circuitos de referência [LISTA: 02]
# ---------------------------------------------------------------------------

#: ω = 377 rad/s das duas questões; a frequência correspondente não é
#: exatamente 60 Hz — é a mesma que o autor declarou no cartão ACSOURCE
#: do ATP, 60,001414 Hz [LISTA: 02, §2.5].
OMEGA: float = 377.0
FREQ: float = OMEGA / (2.0 * math.pi)

#: Questão 1: vs = 100 cos(377 t) V, R1 = 0,5 Ω, L = 25 mH, R2 = 20 Ω.
Q1_R1, Q1_L, Q1_R2 = 0.5, 25.0e-3, 20.0

#: Questão 2: acrescenta o reator R2–L2 com capacitância parasita C.
Q2_R1, Q2_L1, Q2_R2, Q2_L2, Q2_C = 0.5, 5.0e-3, 5.0, 50.0e-3, 50.0e-9
#: Comando de abertura e margem de corrente do disjuntor [LISTA: 02, §3.1].
Q2_T_OPEN, Q2_IMAR = 30.0e-3, 0.5


def _fonte(name: str = "VS", node: str = "1") -> VoltageSource:
    """Fonte ``100·cos(377 t)`` V — a das duas questões [LISTA: 02]."""
    return VoltageSource(
        name,
        node,
        "gnd",
        amplitude_V=100.0,
        frequency_Hz=FREQ,
        phase_reference="cos",
    )


def _circuito_q1(*, chave_fechada: bool = False) -> Circuit:
    """Questão 1 — RL série com chave em paralelo com a carga R2."""
    ckt = Circuit("q1")
    ckt.add(_fonte())
    ckt.add(Resistor("R1", "1", "2", Q1_R1))
    ckt.add(Inductor("L", "2", "3", Q1_L))
    ckt.add(Resistor("R2", "3", "gnd", Q1_R2))
    ckt.add(Switch("SW", "3", "gnd", closed=chave_fechada))
    return ckt


def _circuito_q2(*, imar_no_cartao: bool = False) -> Circuit:
    """Questão 2 — disjuntor a vácuo alimentando um reator com C parasita."""
    ckt = Circuit("q2")
    ckt.add(_fonte())
    ckt.add(Resistor("R1", "1", "2", Q2_R1))
    ckt.add(Inductor("L1", "2", "3", Q2_L1))
    ckt.add(
        Switch(
            "SW",
            "3",
            "4",
            closed=True,
            current_margin_A=Q2_IMAR if imar_no_cartao else None,
        )
    )
    ckt.add(Capacitor("C", "4", "gnd", Q2_C))
    ckt.add(Resistor("R2", "4", "5", Q2_R2))
    ckt.add(Inductor("L2", "5", "gnd", Q2_L2))
    return ckt


def _desvio_do_regime(
    solver: Solver, probe, tempos: np.ndarray, node: str, ate_s: float | None = None
) -> float:
    """Desvio máximo da série da sonda em relação ao fasor semeado [V]."""
    sol = solver.steady_state_solution
    assert sol is not None
    mascara = np.ones_like(tempos, dtype=bool) if ate_s is None else tempos < ate_s
    ref = np.array([sol.node_value_at(node, t) for t in tempos[mascara]])
    return float(np.max(np.abs(np.asarray(probe.values)[mascara] - ref)))


# ---------------------------------------------------------------------------
# 1. Solução fasorial
# ---------------------------------------------------------------------------


class TestSolucaoFasorial:
    """A solução complexa em ω, conferida contra a Lista 02 e à mão."""

    def test_rl_serie_confere_com_a_solucao_fasorial_analitica(self):
        """[LISTA: 02, §2.3, eqs. (12)-(14)] — chave aberta, malha única.

        ``Z = R1 + jωL + R2 = 22,562815∠24,6909° Ω`` e
        ``Î = 4,432071∠−24,6909° A``; em ``t = 0``,
        ``i_L(0) = 4,026867 A``, ``v2(0) = 97,986566 V``,
        ``v3(0) = 80,537341 V`` e ``v_L(0) = 17,449225 V``. O ATP imprime
        ``4,4320710624∠−24,6908953°`` e ``i(0) = 4,02686705 A``.
        """
        ckt = _circuito_q1(chave_fechada=False)
        sol = solve_phasor(ckt)

        z = Q1_R1 + 1j * OMEGA * Q1_L + Q1_R2
        i_hat = 100.0 / z
        assert abs(i_hat) == pytest.approx(4.432071, abs=1e-6)
        assert math.degrees(np.angle(i_hat)) == pytest.approx(-24.6909, abs=1e-4)

        v_l, i_l = sol.branch_phasor("L")
        assert abs(i_l) == pytest.approx(4.432071, abs=1e-6)
        assert math.degrees(np.angle(i_l)) == pytest.approx(-24.6909, abs=1e-4)

        assert instantaneous(i_l, OMEGA, 0.0) == pytest.approx(4.026867, abs=1e-6)
        assert sol.node_value_at("2", 0.0) == pytest.approx(97.986566, abs=1e-6)
        assert sol.node_value_at("3", 0.0) == pytest.approx(80.537341, abs=1e-6)
        assert instantaneous(v_l, OMEGA, 0.0) == pytest.approx(17.449225, abs=1e-6)

    def test_chave_inicialmente_fechada_muda_a_impedancia_vista(self):
        """[LISTA: 02, §2.4] — fechada, ``Z = R1 + jωL = 9,438253∠86,9633° Ω``.

        A corrente forçada é ``10,595181∠−86,9633° A``. É o teste de que a
        solução fasorial usa a topologia CORRENTE das chaves, e não uma
        topologia fixa.
        """
        sol = solve_phasor(_circuito_q1(chave_fechada=True))
        _, i_l = sol.branch_phasor("L")
        assert abs(i_l) == pytest.approx(10.595181, abs=1e-6)
        assert math.degrees(np.angle(i_l)) == pytest.approx(-86.9633, abs=1e-4)
        # Com a chave fechada o nó 3 está aterrado.
        assert abs(sol.node_phasor("3")) == pytest.approx(0.0, abs=1e-12)

    def test_reator_com_capacitancia_parasita(self):
        """[LISTA: 02, §3.3, eqs. (19)-(23)] — disjuntor fechado.

        ``i_s = 4,660054∠−75,1394° A``, ``v = 90,912028∠−0,0005° V`` e
        ``i = 4,661711∠−75,1448° A``. A capacitância parasita conduz
        apenas 1,71 mA em 60 Hz, mas define todo o transitório posterior.
        """
        sol = solve_phasor(_circuito_q2())
        _, i_s = sol.branch_phasor("L1")
        _, i_r = sol.branch_phasor("L2")
        _, i_c = sol.branch_phasor("C")
        v4 = sol.node_phasor("4")

        assert abs(i_s) == pytest.approx(4.660054, abs=1e-6)
        assert math.degrees(np.angle(i_s)) == pytest.approx(-75.1394, abs=1e-4)
        assert abs(v4) == pytest.approx(90.912028, abs=1e-6)
        assert math.degrees(np.angle(v4)) == pytest.approx(-0.0005, abs=1e-4)
        assert abs(i_r) == pytest.approx(4.661711, abs=1e-6)
        assert math.degrees(np.angle(i_r)) == pytest.approx(-75.1448, abs=1e-4)
        assert abs(i_c) == pytest.approx(1.71e-3, rel=5e-3)

    def test_rlc_serie_confere_com_a_impedancia_fechada(self):
        """RLC série a 60 Hz [CÁLCULO PRÓPRIO].

        ``Z = R + jωL + 1/(jωC)``; a tensão do capacitor é
        ``V̂·(1/jωC)/Z``. Confere-se módulo, fase e a defasagem de 90°
        entre corrente e tensão do capacitor.
        """
        f, r_ohm, l_h, c_f = 60.0, 5.0, 10.0e-3, 100.0e-6
        w = 2.0 * math.pi * f
        ckt = Circuit("rlc")
        ckt.add(
            VoltageSource(
                "VS", "1", "gnd", amplitude_V=100.0, frequency_Hz=f,
                phase_reference="cos",
            )
        )
        ckt.add(Resistor("R", "1", "2", r_ohm))
        ckt.add(Inductor("L", "2", "3", l_h))
        ckt.add(Capacitor("C", "3", "gnd", c_f))
        sol = solve_phasor(ckt)

        z = r_ohm + 1j * w * l_h + 1.0 / (1j * w * c_f)
        v_c = 100.0 * (1.0 / (1j * w * c_f)) / z
        assert sol.node_phasor("3") == pytest.approx(v_c, abs=1e-9)

        v_cap, i_cap = sol.branch_phasor("C")
        assert i_cap == pytest.approx(100.0 / z, abs=1e-9)
        defasagem = math.degrees(np.angle(i_cap / v_cap))
        assert defasagem == pytest.approx(90.0, abs=1e-9)

    def test_fonte_trifasica_defasada_e_aceita(self):
        """Três fontes na MESMA frequência com defasagem de 120° passam.

        A restrição declarada é de FREQUÊNCIA única, não de fase única:
        o sistema trifásico equilibrado é caso de uso do estudo de
        manobra. Confere-se a soma nula das três tensões de fase.
        """
        ckt = Circuit("3f")
        ckt.extend(
            three_phase_voltage_sources(
                "VS", ("a", "b", "c"), "gnd", amplitude_V=100.0,
                frequency_Hz=60.0, phase_reference="cos",
            )
        )
        for fase in ("a", "b", "c"):
            ckt.add(Resistor(f"R_{fase}", fase, f"n_{fase}", 1.0))
            ckt.add(Inductor(f"L_{fase}", f"n_{fase}", "gnd", 10.0e-3))
        sol = solve_phasor(ckt)
        soma = sum(sol.node_phasor(f) for f in ("a", "b", "c"))
        assert abs(soma) == pytest.approx(0.0, abs=1e-9)
        modulos = [abs(sol.node_phasor(f"n_{f}")) for f in ("a", "b", "c")]
        assert modulos[0] == pytest.approx(modulos[1], rel=1e-12)
        assert modulos[1] == pytest.approx(modulos[2], rel=1e-12)

    def test_referencia_seno_equivale_a_cosseno_defasado(self):
        """``sen(θ) = cos(θ − 90°)`` [LISTA: 02, §1.4].

        O fasor de uma fonte declarada em seno é o mesmo de uma fonte
        declarada em cosseno com 90° a menos — e a semeadura resultante
        deve ser idêntica.
        """
        seno = VoltageSource(
            "A", "1", "gnd", amplitude_V=100.0, frequency_Hz=60.0,
            phase_deg=30.0, phase_reference="sin",
        )
        cosseno = VoltageSource(
            "B", "1", "gnd", amplitude_V=100.0, frequency_Hz=60.0,
            phase_deg=-60.0, phase_reference="cos",
        )
        assert source_phasor(seno) == pytest.approx(source_phasor(cosseno), abs=1e-12)
        # e o valor instantâneo em t = 0 confere com value_at.
        assert instantaneous(source_phasor(seno), 2 * math.pi * 60.0, 0.0) == (
            pytest.approx(seno.value_at(0.0), abs=1e-12)
        )

    def test_sistema_complexo_tem_a_mesma_dimensao_do_real(self):
        """A numeração MNA complexa é a de ``Circuit.build()``.

        É o que torna ``PhasorSolution.state_at(0)`` diretamente
        utilizável como vetor de estado inicial do solver.
        """
        ckt = _circuito_q2()
        ckt.build()
        A, b = assemble_phasor_system(ckt, OMEGA)
        assert A.shape == (ckt.dimension, ckt.dimension)
        assert b.shape == (ckt.dimension,)
        assert A.dtype == complex
        # 5 nós + fonte + chave = 7, exatamente a eq. (17) da Lista 02.
        assert ckt.dimension == 7


# ---------------------------------------------------------------------------
# 2. Erros declarados
# ---------------------------------------------------------------------------


class TestErrosDeclarados:
    """A recusa explícita é preferível à semeadura silenciosamente errada."""

    def test_erro_para_multiplas_frequencias(self):
        """Duas fontes ativas em frequências distintas ⇒ erro claro."""
        ckt = Circuit("2f")
        ckt.add(
            VoltageSource("V60", "1", "gnd", amplitude_V=100.0, frequency_Hz=60.0)
        )
        ckt.add(Resistor("R1", "1", "2", 1.0))
        ckt.add(Inductor("L", "2", "gnd", 1.0e-3))
        ckt.add(
            VoltageSource("V180", "3", "gnd", amplitude_V=10.0, frequency_Hz=180.0)
        )
        ckt.add(Resistor("R3", "3", "gnd", 5.0))
        with pytest.raises(MultipleFrequenciesError) as exc:
            solve_phasor(ckt)
        texto = str(exc.value)
        assert "única frequência" in texto
        assert "60" in texto and "180" in texto

    def test_erro_para_componente_continua(self):
        """``dc_offset_V`` não nulo acrescenta a frequência zero ⇒ erro."""
        ckt = Circuit("dc")
        ckt.add(
            VoltageSource(
                "VS", "1", "gnd", amplitude_V=100.0, frequency_Hz=60.0,
                dc_offset_V=10.0,
            )
        )
        ckt.add(Resistor("R", "1", "2", 1.0))
        ckt.add(Inductor("L", "2", "gnd", 1.0e-3))
        with pytest.raises(MultipleFrequenciesError, match="dc_offset_V"):
            solve_phasor(ckt)

    def test_erro_para_fonte_continua_pura(self):
        """Amplitude não nula com ``frequency_Hz = 0`` é fonte contínua."""
        ckt = Circuit("cc")
        ckt.add(
            VoltageSource("VS", "1", "gnd", amplitude_V=100.0, frequency_Hz=0.0)
        )
        ckt.add(Resistor("R", "1", "gnd", 1.0))
        with pytest.raises(MultipleFrequenciesError, match="corrente contínua"):
            solve_phasor(ckt)

    def test_erro_quando_nenhuma_fonte_define_omega(self):
        """Sem fonte senoidal ativa não há ω; exige ``frequency_Hz``."""
        ckt = Circuit("morto")
        ckt.add(VoltageSource("VS", "1", "gnd", amplitude_V=0.0, frequency_Hz=0.0))
        ckt.add(Resistor("R", "1", "2", 1.0))
        ckt.add(Inductor("L", "2", "gnd", 1.0e-3))
        with pytest.raises(MultipleFrequenciesError, match="defina ω"):
            solve_phasor(ckt)
        # Com ω imposto a solução existe e é o repouso.
        sol = solve_phasor(ckt, frequency_Hz=60.0)
        assert abs(sol.node_phasor("2")) == pytest.approx(0.0, abs=1e-15)

    def test_erro_para_frequencia_imposta_divergente(self):
        """``frequency_Hz`` incompatível com as fontes ⇒ erro, não silêncio."""
        ckt = _circuito_q1()
        with pytest.raises(MultipleFrequenciesError, match="diverge"):
            solve_phasor(ckt, frequency_Hz=50.0)
        # A frequência correta é aceita.
        assert source_frequency(ckt, frequency_Hz=FREQ) == pytest.approx(FREQ)

    def test_componente_sem_equivalente_fasorial_levanta_erro(self):
        """Ramo desconhecido ⇒ :class:`UnsupportedComponentError`."""

        class RamoExotico(Component):
            """Ramo de teste sem estampagem fasorial."""

            def stamp_matrix(self, A):
                self._stamp_conductance(A, self._idx[0], self._idx[1], 1.0)

        ckt = Circuit("exotico")
        ckt.add(_fonte())
        ckt.add(RamoExotico("X", ("1", "gnd")))
        with pytest.raises(UnsupportedComponentError, match="RamoExotico"):
            solve_phasor(ckt)

    def test_gancho_stamp_phasor_permite_estender_o_modulo(self):
        """Um ramo que implemente ``stamp_phasor`` é aceito.

        É o ponto de extensão declarado: quem acrescentar um modelo ao
        kernel acrescenta junto o seu equivalente fasorial, em vez de
        alterar este módulo.
        """

        class RamoComFasor(Component):
            """Resistência de 2 Ω com estampagem fasorial própria."""

            def stamp_matrix(self, A):
                self._stamp_conductance(A, self._idx[0], self._idx[1], 0.5)

            def stamp_phasor(self, A, b, omega):
                p, n = self._idx[0], self._idx[1]
                if p != -1:
                    A[p, p] += 0.5
                if n != -1:
                    A[n, n] += 0.5

            def branch_voltage(self, index: int = 0) -> float:
                return 0.0

            def branch_current(self, index: int = 0) -> float:
                return 0.0

        ckt = Circuit("extensivel")
        ckt.add(_fonte())
        ckt.add(Resistor("R", "1", "2", 2.0))
        ckt.add(RamoComFasor("X", ("2", "gnd")))
        ckt.build()
        A, _ = assemble_phasor_system(ckt, OMEGA)
        idx = ckt.node_index["2"]
        assert A[idx, idx] == pytest.approx(0.5 + 0.5)

    def test_linha_em_meia_onda_sem_perdas_levanta_erro(self):
        """``ωτ`` múltiplo de π torna o sistema fasorial singular.

        Não é falha numérica: sem perdas, a linha em meia onda não tem
        regime permanente único. O módulo recusa em vez de devolver lixo.
        """
        f = 60.0
        ckt = Circuit("meia_onda")
        ckt.add(
            VoltageSource("VS", "1", "gnd", amplitude_V=100.0, frequency_Hz=f)
        )
        ckt.add(
            BergeronLine(
                "LN", "1", "2", surge_impedance_ohm=400.0,
                travel_time_s=1.0 / (2.0 * f),
            )
        )
        ckt.add(Resistor("RL", "2", "gnd", 400.0))
        with pytest.raises(SteadyStateError, match="meia onda"):
            solve_phasor(ckt)


# ---------------------------------------------------------------------------
# 3. Ausência de transitório de energização
# ---------------------------------------------------------------------------


class TestPartidaSemTransitorio:
    """A marcha no tempo reproduz o regime desde o primeiro passo."""

    def test_rl_serie_em_regime_sem_transitorio(self):
        """RL série, 4 ciclos: desvio bem abaixo de 1e-5 da amplitude.

        [CÁLCULO PRÓPRIO — medição desta sessão: 1,36e−7 A sobre 4,43 A
        de amplitude, com Δt = 1 µs.] O resíduo é o da diferença entre a
        impedância contínua ``jωL`` e a da recursão trapezoidal
        ``j(2L/Δt)·tg(ωΔt/2)``, de ordem ``(ωΔt)²/12``.
        """
        ckt = Circuit("rl")
        ckt.add(_fonte())
        ckt.add(Resistor("R1", "1", "2", Q1_R1))
        ckt.add(Inductor("L", "2", "gnd", Q1_L))
        solver = Solver(ckt, dt=1.0e-6, init=INIT_STEADY_STATE)
        p = solver.add_probe(BranchCurrentProbe("i", ckt.get("L")))
        res = solver.run(4.0 / FREQ)

        sol = solver.steady_state_solution
        assert sol is not None
        _, i_hat = sol.branch_phasor("L")
        ref = np.array(
            [instantaneous(i_hat, sol.omega_rad_s, t) for t in res.time_s]
        )
        desvio = float(np.max(np.abs(np.asarray(p.values) - ref)))
        assert desvio < 1.0e-6
        # a amplitude de regime é a fasorial, sem componente contínua.
        assert float(np.max(p.values)) == pytest.approx(abs(i_hat), rel=1e-7)
        assert float(np.min(p.values)) == pytest.approx(-abs(i_hat), rel=1e-7)

    def test_partida_do_repouso_tem_transitorio_de_energizacao(self):
        """Contraste: com ``init='zero'`` o desvio é da ordem da amplitude.

        É a demonstração de que o teste anterior mede alguma coisa: o
        mesmo circuito, partindo do repouso, carrega a componente contínua
        de energização ``−i_f(0) = −0,5613 A``, que decai com
        ``τ = L/R = 50 ms`` e ainda vale 93 % ao fim de 4 ciclos. São
        seis ordens de grandeza acima do resíduo da partida semeada.
        """
        ckt = Circuit("rl_repouso")
        ckt.add(_fonte())
        ckt.add(Resistor("R1", "1", "2", Q1_R1))
        ckt.add(Inductor("L", "2", "gnd", Q1_L))
        solver = Solver(ckt, dt=1.0e-6, init=INIT_ZERO)
        p = solver.add_probe(BranchCurrentProbe("i", ckt.get("L")))
        res = solver.run(4.0 / FREQ)

        # regime da malha R1–L (sem R2): Z = R1 + jωL.
        z = Q1_R1 + 1j * OMEGA * Q1_L
        i_hat = 100.0 / z
        ref = np.array([instantaneous(i_hat, OMEGA, t) for t in res.time_s])
        desvio = float(np.max(np.abs(np.asarray(p.values) - ref)))
        assert desvio == pytest.approx(abs(instantaneous(i_hat, OMEGA, 0.0)), rel=0.1)
        assert desvio > 1.0e5 * 1.0e-6

    def test_residuo_converge_com_o_quadrado_do_passo(self):
        """O resíduo cai por ~4 a cada divisão de ``Δt`` por 2.

        Prova que o que resta é o erro de discretização da regra
        trapezoidal — ordem 2 —, e não um transitório mal semeado, que
        seria insensível ao passo.
        """
        def residuo(dt: float) -> float:
            ckt = Circuit("rl")
            ckt.add(_fonte())
            ckt.add(Resistor("R1", "1", "2", Q1_R1))
            ckt.add(Inductor("L", "2", "gnd", Q1_L))
            solver = Solver(ckt, dt=dt, init=INIT_STEADY_STATE)
            p = solver.add_probe(BranchCurrentProbe("i", ckt.get("L")))
            res = solver.run(2.0 / FREQ)
            sol = solver.steady_state_solution
            _, i_hat = sol.branch_phasor("L")
            ref = np.array(
                [instantaneous(i_hat, sol.omega_rad_s, t) for t in res.time_s]
            )
            return float(np.max(np.abs(np.asarray(p.values) - ref)))

        r1, r2 = residuo(4.0e-6), residuo(2.0e-6)
        assert r1 / r2 == pytest.approx(4.0, rel=0.05)

    def test_questao2_reproduz_o_desvio_de_1e_10_da_tabela3(self):
        """[LISTA: 02, Tabela 3] — regime × fasorial: 1,39e−10 V.

        É o teste-bandeira do módulo: o circuito da Questão 2, com
        ``Δt = 1 µs``, antes do comando de abertura em ``t0 = 30 ms``.
        O autor mede 1,39e−10 V na rotina própria validada contra o ATP;
        aqui mede-se 1,392e−10 V. O patamar excepcionalmente baixo vem de
        a tensão do reator ser quase estacionária em ω
        (``90,912 V∠−0,0005°``).
        """
        ckt = _circuito_q2()
        solver = Solver(ckt, dt=1.0e-6, init=INIT_STEADY_STATE)
        p = solver.add_probe(NodeVoltageProbe("v4", "4"))
        res = solver.run(Q2_T_OPEN)
        desvio = _desvio_do_regime(solver, p, res.time_s, "4")
        assert desvio < 1.0e-9
        assert desvio == pytest.approx(1.39e-10, rel=0.05)

    def test_estado_em_t_zero_ja_e_o_regime_permanente(self):
        """Os controladores leem o regime ANTES do primeiro passo.

        É o que permite ao critério ``Imar`` decidir corretamente já em
        ``t = 0`` — e o que distingue esta implementação de uma que
        apenas semeasse os históricos.
        """
        ckt = _circuito_q2()
        solver = Solver(ckt, dt=1.0e-6, init=INIT_STEADY_STATE)
        lidos: list[tuple[float, float, float]] = []

        def espiao(t: float, s: Solver) -> None:
            if not lidos:
                lidos.append(
                    (t, s.node_voltage("4"), float(ckt.get("SW").branch_current(0)))
                )

        solver.run(10.0e-6, controllers=[espiao])
        t0, v4, i_sw = lidos[0]
        assert t0 == 0.0
        assert v4 == pytest.approx(90.912028, abs=1e-5)
        # a corrente da chave em t = 0 é a da fonte, i_s(0) = 4,660054·cos(−75,1394°)
        assert abs(i_sw) == pytest.approx(
            abs(4.660054 * math.cos(math.radians(-75.1394))), rel=1e-4
        )

    def test_meios_passos_de_partida_desligados_no_regime_permanente(self):
        """``init='steady_state'`` desliga o paliativo de partida.

        [LISTA: 02, §1.4]: não há descontinuidade em ``t = 0`` quando a
        partida é o regime, e os dois meios-passos de Euler regressivo
        amorteceriam o que acabou de ser semeado. O CDA das MANOBRAS é
        outra coisa e permanece ligado — ver o teste seguinte.
        """
        ckt = _circuito_q2()
        solver = Solver(ckt, dt=1.0e-6, init=INIT_STEADY_STATE)
        assert solver.cda_at_start is False
        res = solver.run(50.0e-6)
        assert res.cda_events == 0

        ckt2 = _circuito_q2()
        repouso = Solver(ckt2, dt=1.0e-6, init=INIT_ZERO)
        assert repouso.cda_at_start is True
        assert repouso.run(50.0e-6).cda_events == 1

    def test_cda_de_manobra_permanece_ativo_no_regime_permanente(self):
        """A manobra continua disparando o par de meios-passos.

        Confere-se também que o nó da fonte NÃO oscila em ``2Δt`` após a
        interrupção — o artefato de [LISTA: 02, §3.8], que o CDA suprime.
        """
        ckt = _circuito_q2()
        solver = Solver(ckt, dt=1.0e-6, init=INIT_STEADY_STATE)
        v3 = solver.add_probe(NodeVoltageProbe("v3", "3"))
        res = solver.run(
            40.0e-3,
            controllers=[
                TimedSwitchController(
                    ckt.get("SW"), open_time_s=Q2_T_OPEN, current_margin_A=Q2_IMAR
                )
            ],
        )
        assert res.cda_events == 1
        assert res.topology_changes == 1
        # sem CDA a oscilação chegaria a ±5 kV [LISTA: 02, eq. (29)].
        pos = res.time_s > 35.0e-3
        assert float(np.max(np.abs(np.asarray(v3.values)[pos]))) < 200.0


# ---------------------------------------------------------------------------
# 4. Comutação por margem de corrente (Imar)
# ---------------------------------------------------------------------------


class TestMargemDeCorrente:
    """Campo ``Imar`` do cartão de chave do ATP [LISTA: 02, §1.3 e §3.6]."""

    def test_abertura_so_ocorre_quando_a_corrente_cai_abaixo_de_imar(self):
        """[LISTA: 02, §3.4] — comando em 30 ms, corte em 32,36 ms.

        Em ``t0 = 30 ms`` a corrente vale −3,9137 A, muito acima de
        ``I_mar = 0,5 A``; a interrupção só se efetiva quando
        ``|i_s| <= 0,5 A``. O instante exato é ``t_c = 32,359422 ms`` e o
        ATP registra "Open switch after 3.23600000E-02 sec" — o mesmo
        passo obtido aqui.
        """
        ckt = _circuito_q2()
        sw = ckt.get("SW")
        solver = Solver(ckt, dt=1.0e-6, init=INIT_STEADY_STATE)
        ctrl = TimedSwitchController(
            sw, open_time_s=Q2_T_OPEN, current_margin_A=Q2_IMAR
        )
        correntes: list[tuple[float, float]] = []
        solver.run(
            35.0e-3,
            controllers=[
                ctrl,
                lambda t, s: correntes.append((t, float(sw.branch_current(0)))),
            ],
        )
        assert ctrl.effective_open_time_s == pytest.approx(32.360e-3, abs=1.0e-9)
        # a corrente no instante do corte está dentro da margem…
        no_corte = [i for t, i in correntes if abs(t - 32.360e-3) < 1.0e-9][0]
        assert abs(no_corte) <= Q2_IMAR
        # …e no passo anterior ainda a excedia.
        anterior = [i for t, i in correntes if abs(t - 32.359e-3) < 1.0e-9][0]
        assert abs(anterior) > Q2_IMAR
        # em t0 a corrente é a de [LISTA: 02, §3.4]: −3,9137 A.
        em_t0 = [i for t, i in correntes if abs(t - Q2_T_OPEN) < 1.0e-9][0]
        assert em_t0 == pytest.approx(-3.9137, abs=1e-3)

    def test_imar_do_cartao_da_chave_e_usado_quando_o_controlador_omite(self):
        """``Switch(current_margin_A=…)`` é o campo do cartão.

        O controlador sem margem própria recai sobre o campo da chave —
        e o resultado tem de ser idêntico ao do teste anterior.
        """
        ckt = _circuito_q2(imar_no_cartao=True)
        sw = ckt.get("SW")
        assert sw.current_margin_A == Q2_IMAR
        solver = Solver(ckt, dt=1.0e-6, init=INIT_STEADY_STATE)
        ctrl = TimedSwitchController(sw, open_time_s=Q2_T_OPEN)
        assert ctrl.margin_in_force_A == Q2_IMAR
        solver.run(35.0e-3, controllers=[ctrl])
        assert ctrl.effective_open_time_s == pytest.approx(32.360e-3, abs=1.0e-9)

    def test_sem_imar_a_abertura_e_forcada_no_instante_comandado(self):
        """``Imar = None`` nos dois lugares ⇒ abertura forçada em ``t0``.

        É o interruptor ideal comandado do ensaio numérico. Sem o campo,
        "o ATP esperaria um zero natural de corrente e a sobretensão
        praticamente desapareceria" [LISTA: 02, §3.6] — aqui o efeito é
        o oposto, a abertura é imediata, e o contraste com o caso
        anterior é o que se verifica.
        """
        ckt = _circuito_q2()
        sw = ckt.get("SW")
        assert sw.current_margin_A is None
        solver = Solver(ckt, dt=1.0e-6, init=INIT_STEADY_STATE)
        ctrl = TimedSwitchController(sw, open_time_s=Q2_T_OPEN)
        assert ctrl.margin_in_force_A is None
        solver.run(32.0e-3, controllers=[ctrl])
        assert ctrl.effective_open_time_s == pytest.approx(Q2_T_OPEN, abs=1.0e-9)

    def test_criterio_imar_na_propria_chave(self):
        """:meth:`Switch.may_interrupt` e :meth:`open_within_margin`."""
        sw = Switch("SW", "a", "b", closed=True, current_margin_A=0.5)
        assert sw.may_interrupt(0.4) is True
        assert sw.may_interrupt(-0.5) is True
        assert sw.may_interrupt(0.6) is False
        assert sw.open_within_margin(3.0) is False
        assert sw.closed is True
        assert sw.open_within_margin(0.25) is True
        assert sw.closed is False
        # sem margem declarada não há critério: abertura forçada.
        livre = Switch("SW2", "a", "b", closed=True)
        assert livre.may_interrupt(1.0e6) is True
        assert livre.open_within_margin(1.0e6) is True
        assert livre.closed is False

    def test_margem_negativa_e_rejeitada(self):
        """``Imar`` é um módulo de corrente: negativo é erro de dado."""
        with pytest.raises(ValueError, match="current_margin_A"):
            Switch("SW", "a", "b", current_margin_A=-1.0)

    @pytest.mark.parametrize(
        "dt, pico",
        [
            (4.0e-6, 501.37),
            (2.0e-6, 503.29),
            (1.0e-6, 504.292),
            (0.5e-6, 505.62),
            (0.25e-6, 505.84),
        ],
    )
    def test_pico_da_trv_reproduz_a_tabela4_da_lista02(self, dt, pico):
        """[LISTA: 02, Tabelas 3 e 4] — pico da TRV em função do passo.

        Reprodução dígito a dígito da rotina própria do autor, que por
        sua vez concorda com o ATP em 4,27e−4 V. A marcha é feita SEM
        CDA porque é assim que a rotina de referência opera — e é
        justamente por isso que [LISTA: 02, §3.8] observa a oscilação
        numérica de ``2Δt`` no nó da fonte. O pico converge
        monotonicamente para o valor analítico de 506,170 V, cujo desvio
        residual decorre de o corte só poder cair sobre um ponto da
        malha de tempo (limitação ``emt_switching_quantized_to_step``).
        """
        ckt = _circuito_q2()
        solver = Solver(
            ckt, dt=dt, init=INIT_STEADY_STATE, cda_enabled=False
        )
        p = solver.add_probe(NodeVoltageProbe("v4", "4"))
        solver.run(
            40.0e-3,
            controllers=[
                TimedSwitchController(
                    ckt.get("SW"), open_time_s=Q2_T_OPEN, current_margin_A=Q2_IMAR
                )
            ],
        )
        assert float(np.max(np.abs(p.values))) == pytest.approx(pico, abs=5.0e-3)


# ---------------------------------------------------------------------------
# 5. Linha de Bergeron e ramo acoplado
# ---------------------------------------------------------------------------


class TestLinhaEAcoplamento:
    """Semeadura dos ramos com memória distribuída e matricial."""

    def test_linha_sem_perdas_reduz_a_admitancia_classica(self):
        """``Y₁₁ = 1/(jZ_c·tg ωτ)`` e ``Y₁₂ = −1/(jZ_c·sen ωτ)``.

        A admitância usada na semeadura é a do MODELO IMPLEMENTADO
        (operador de atraso, fator ζ, perdas concentradas); sem perdas
        ela tem de recair na da linha ideal de parâmetros distribuídos —
        que é o teste de que a álgebra do modelo está correta.
        """
        z_c, tau, w = 400.0, 50.0e-6, 2.0 * math.pi * 60.0
        linha = BergeronLine(
            "LN", "k", "m", surge_impedance_ohm=z_c, travel_time_s=tau
        )
        y11, y12 = _line_admittance(linha, w)
        assert y11 == pytest.approx(1.0 / (1j * z_c * math.tan(w * tau)), rel=1e-12)
        assert y12 == pytest.approx(-1.0 / (1j * z_c * math.sin(w * tau)), rel=1e-12)

    @pytest.mark.parametrize("r_linha", [0.0, 20.0])
    def test_linha_semeada_nao_produz_degrau_de_partida(self, r_linha):
        """O buffer de trânsito entra carregado com a onda de regime.

        Sem a semeadura os primeiros ``τ/Δt`` passos veriam histórico
        nulo e a linha injetaria um degrau da ordem da própria tensão de
        regime — o que se verifica no contraste com ``init='zero'``.
        Com ``τ`` múltiplo inteiro de ``Δt`` não há erro de interpolação
        e o desvio cai ao patamar de arredondamento.
        """
        f, dt, z_c, tau = 60.0, 1.0e-6, 400.0, 50.0e-6

        def monta() -> Circuit:
            ckt = Circuit("linha")
            ckt.add(
                VoltageSource(
                    "VS", "1", "gnd", amplitude_V=1000.0, frequency_Hz=f,
                    phase_reference="cos",
                )
            )
            ckt.add(Resistor("Rs", "1", "k", 1.0))
            ckt.add(
                BergeronLine(
                    "LN", "k", "m", surge_impedance_ohm=z_c,
                    travel_time_s=tau, resistance_ohm=r_linha,
                )
            )
            ckt.add(Resistor("RL", "m", "gnd", z_c))
            return ckt

        ckt = monta()
        solver = Solver(ckt, dt=dt, init=INIT_STEADY_STATE)
        p = solver.add_probe(NodeVoltageProbe("vm", "m"))
        res = solver.run(10.0e-3)
        desvio = _desvio_do_regime(solver, p, res.time_s, "m")
        assert desvio < 1.0e-9

        ckt2 = monta()
        repouso = Solver(ckt2, dt=dt, init=INIT_ZERO)
        p2 = repouso.add_probe(NodeVoltageProbe("vm", "m"))
        res2 = repouso.run(10.0e-3)
        sol = solver.steady_state_solution
        ref = np.array([sol.node_value_at("m", t) for t in res2.time_s])
        assert float(np.max(np.abs(np.asarray(p2.values) - ref))) > 100.0

    def test_semente_da_linha_sobrevive_ao_reset(self):
        """Reexecutar o solver reinicia sempre do MESMO regime.

        A semente é condição inicial do ramo, como ``initial_current_A``
        no indutor — e por isso :meth:`BergeronLine.reset` a reaplica.
        """
        f, dt = 60.0, 1.0e-6
        ckt = Circuit("linha")
        ckt.add(
            VoltageSource(
                "VS", "1", "gnd", amplitude_V=1000.0, frequency_Hz=f,
                phase_reference="cos",
            )
        )
        ckt.add(Resistor("Rs", "1", "k", 1.0))
        ckt.add(
            BergeronLine(
                "LN", "k", "m", surge_impedance_ohm=400.0, travel_time_s=50.0e-6
            )
        )
        ckt.add(Resistor("RL", "m", "gnd", 400.0))
        solver = Solver(ckt, dt=dt, init=INIT_STEADY_STATE)
        p = solver.add_probe(NodeVoltageProbe("vm", "m"))
        solver.run(2.0e-3)
        primeira = np.asarray(p.values).copy()
        solver.run(2.0e-3)
        assert np.array_equal(primeira, np.asarray(p.values))

        linha = ckt.get("LN")
        linha.clear_steady_state_seed()
        linha.reset()
        assert linha.branch_voltage(0) == 0.0

    def test_ramo_rl_acoplado_parte_do_regime(self):
        """``CoupledRL`` recebe ``i(0)`` e ``v(0)`` vetoriais.

        A condição inicial de um ramo acoplado exige os dois vetores,
        pelo mesmo motivo do indutor escalar: o histórico trapezoidal é
        ``G·[v(0) + (2L/Δt − R)·i(0)]``. O resíduo aqui é maior que o do
        indutor puro porque a resistência entra DENTRO da recursão, mas
        continua sendo ``O((ωΔt)²)`` — 1,5e−6 V sobre 72 V com
        ``Δt = 2 µs`` [CÁLCULO PRÓPRIO].
        """
        ckt = Circuit("trafo")
        ckt.add(
            VoltageSource(
                "VS", "1", "gnd", amplitude_V=100.0, frequency_Hz=60.0,
                phase_reference="cos",
            )
        )
        ckt.add(Resistor("R1", "1", "2", 1.0))
        L = np.array([[10.0e-3, 8.0e-3], [8.0e-3, 10.0e-3]])
        ckt.add(
            CoupledRL(
                "T", [("2", "gnd"), ("3", "gnd")], L, resistance_ohm=[0.5, 0.5]
            )
        )
        ckt.add(Resistor("Rb", "3", "gnd", 50.0))
        solver = Solver(ckt, dt=2.0e-6, init=INIT_STEADY_STATE)
        p = solver.add_probe(NodeVoltageProbe("v3", "3"))
        res = solver.run(3.0 / 60.0)
        desvio = _desvio_do_regime(solver, p, res.time_s, "3")
        assert desvio < 1.0e-4

        # contraste com a partida do repouso, que oscila em torno do regime
        ckt2 = Circuit("trafo0")
        ckt2.add(
            VoltageSource(
                "VS", "1", "gnd", amplitude_V=100.0, frequency_Hz=60.0,
                phase_reference="cos",
            )
        )
        ckt2.add(Resistor("R1", "1", "2", 1.0))
        ckt2.add(
            CoupledRL(
                "T", [("2", "gnd"), ("3", "gnd")], L, resistance_ohm=[0.5, 0.5]
            )
        )
        ckt2.add(Resistor("Rb", "3", "gnd", 50.0))
        repouso = Solver(ckt2, dt=2.0e-6, init=INIT_ZERO)
        p2 = repouso.add_probe(NodeVoltageProbe("v3", "3"))
        res2 = repouso.run(3.0 / 60.0)
        sol = solver.steady_state_solution
        ref = np.array([sol.node_value_at("3", t) for t in res2.time_s])
        assert float(np.max(np.abs(np.asarray(p2.values) - ref))) > 1.0

    def test_condicao_inicial_vetorial_valida_o_tamanho(self):
        """``set_initial_state`` recusa vetor de dimensão errada."""
        L = np.array([[10.0e-3, 8.0e-3], [8.0e-3, 10.0e-3]])
        ramo = CoupledRL("T", [("2", "gnd"), ("3", "gnd")], L)
        with pytest.raises(ValueError, match="initial_current_A"):
            ramo.set_initial_state(current_A=[1.0, 2.0, 3.0])
        ramo.set_initial_state(current_A=[1.0, 2.0], voltage_V=[3.0, 4.0])
        ramo.reset()
        assert ramo.branch_current(0) == pytest.approx(1.0)
        assert ramo.branch_voltage(1) == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# 6. API e auditoria
# ---------------------------------------------------------------------------


class TestApiEAuditoria:
    """Contrato público e limitações declaradas."""

    def test_modos_de_partida_e_validacao(self):
        """``init`` aceita apenas os modos declarados."""
        assert INIT_MODES == (INIT_ZERO, INIT_STEADY_STATE)
        ckt = _circuito_q1()
        with pytest.raises(ValueError, match="init deve ser"):
            Solver(ckt, dt=1.0e-6, init="fasorial")
        with pytest.raises(ValueError, match="init_frequency_Hz"):
            Solver(ckt, dt=1.0e-6, init=INIT_STEADY_STATE, init_frequency_Hz=-1.0)

    def test_solucao_fasorial_fica_disponivel_para_auditoria(self):
        """``Solver.steady_state_solution`` expõe o fasor que semeou."""
        ckt = _circuito_q2()
        solver = Solver(ckt, dt=1.0e-6, init=INIT_STEADY_STATE)
        assert solver.steady_state_solution is None
        solver.run(20.0e-6)
        sol = solver.steady_state_solution
        assert isinstance(sol, PhasorSolution)
        assert sol.frequency_Hz == pytest.approx(FREQ)
        assert sol.omega_rad_s == pytest.approx(OMEGA)
        assert sol.x.shape == (ckt.dimension,)
        assert sol.condition_estimate > 0.0
        with pytest.raises(SteadyStateError, match="não existe"):
            sol.node_phasor("inexistente")
        with pytest.raises(SteadyStateError, match="ausente"):
            sol.branch_phasor("inexistente")

        # partida do repouso não produz solução fasorial
        repouso = Solver(_circuito_q2(), dt=1.0e-6)
        repouso.run(20.0e-6)
        assert repouso.steady_state_solution is None

    def test_initialize_steady_state_e_idempotente(self):
        """Chamar a inicialização duas vezes dá o mesmo estado.

        A semeadura escreve nos parâmetros de condição inicial dos ramos,
        de onde ``reset()`` a reproduz — por isso a reexecução do solver
        é determinística.
        """
        ckt = _circuito_q2()
        s1 = initialize_steady_state(ckt, 1.0e-6)
        i1 = ckt.get("L2").initial_current_A
        s2 = initialize_steady_state(ckt, 1.0e-6)
        i2 = ckt.get("L2").initial_current_A
        assert i1 == pytest.approx(i2, abs=1e-15)
        assert np.allclose(s1.x, s2.x, atol=1e-15)

    def test_semeadura_realiza_a_equacao_6_da_lista02(self):
        """``I_L(0) = i_L(0) + G_L·v_L(0)`` e ``I_C(0) = −[G_C·v_C(0) + i_C(0)]``.

        Confere-se o termo histórico efetivamente devolvido pelos ramos
        contra a eq. (6) calculada à mão a partir da solução fasorial.
        """
        dt = 1.0e-6
        ckt = _circuito_q2()
        sol = initialize_steady_state(ckt, dt)

        ind = ckt.get("L2")
        v_l, i_l = sol.branch_phasor("L2")
        g_l = dt / (2.0 * Q2_L2)
        esperado = instantaneous(i_l, OMEGA, 0.0) + g_l * instantaneous(
            v_l, OMEGA, 0.0
        )
        assert ind.history_current_A() == pytest.approx(esperado, rel=1e-12)
        assert ind.conductance_S == pytest.approx(g_l, rel=1e-15)

        cap = ckt.get("C")
        v_c, i_c = sol.branch_phasor("C")
        g_c = 2.0 * Q2_C / dt
        esperado_c = -(
            g_c * instantaneous(v_c, OMEGA, 0.0) + instantaneous(i_c, OMEGA, 0.0)
        )
        assert cap.history_current_A() == pytest.approx(esperado_c, rel=1e-12)
        assert cap.conductance_S == pytest.approx(g_c, rel=1e-15)

    def test_limitacoes_do_regime_permanente_declaradas(self):
        """As três chaves novas entram no catálogo de auditoria."""
        for chave in (
            "emt_steady_state_single_frequency",
            "emt_steady_state_residual_deviation",
            "emt_steady_state_line_interpolation",
        ):
            assert chave in KNOWN_LIMITATIONS
            assert len(KNOWN_LIMITATIONS[chave]) > 200
        # a limitação que este módulo eliminou não pode continuar declarada
        assert "emt_no_steady_state_init" not in KNOWN_LIMITATIONS
        assert "UMA ÚNICA frequência" in KNOWN_LIMITATIONS[
            "emt_steady_state_single_frequency"
        ]
