"""
Testes do método de compensação e da característica por trechos.

O que se valida aqui, em ordem:

1. A característica ``v-i``: monotonicidade exigida, simetria ímpar,
   busca de trecho e extrapolação declarada.
2. A álgebra da compensação contra soluções ANALÍTICAS — é o único jeito
   de saber que ``z_T`` e a superposição estão certas, e não apenas
   autoconsistentes.
3. O acoplamento entre ramos compensados, que é o que a formulação de
   ``M`` ramos de Dommel acrescenta ao caso de um ramo só.
4. A invalidação de ``z_T`` na mudança de topologia — a condição que a
   própria fonte impõe.

Fonte do método: DOMMEL, H. W. Nonlinear and time-varying elements in
digital simulation of electromagnetic transients. *IEEE Transactions on
Power Apparatus and Systems*, v. PAS-90, n. 6, p. 2561-2567, 1971, §V.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.simulation.emt.circuit import Circuit, Solver
from app.simulation.emt.components import Resistor, Switch, VoltageSource
from app.simulation.emt.nonlinear import (
    KNOWN_LIMITATIONS,
    CompensatedBranch,
    CompensationNetwork,
    PiecewiseLinearVI,
    collect_compensated,
)


def _fonte_cc(name: str, node_p: str, node_n: str, valor_V: float) -> VoltageSource:
    """Fonte de valor constante ``valor_V`` (seno com φ = 90° e f = 0)."""
    return VoltageSource(
        name,
        node_p,
        node_n,
        amplitude_V=float(valor_V),
        frequency_Hz=0.0,
        phase_deg=90.0,
    )


#: Característica LINEAR disfarçada de não linear: ``i = v/20`` em todo o
#: domínio. Serve para confrontar a compensação com o divisor resistivo
#: analítico, cujo resultado é conhecido exatamente.
LINEAR_20_OHM = PiecewiseLinearVI(
    voltage_V=(20.0, 200.0), current_A=(1.0, 10.0), name="linear20"
)


# ---------------------------------------------------------------------------
# 1. A característica
# ---------------------------------------------------------------------------


class TestCaracteristicaPorTrechos:
    def test_pontos_geram_trecho_central_mais_um_por_par(self):
        c = PiecewiseLinearVI(voltage_V=(10.0, 20.0, 40.0), current_A=(1.0, 5.0, 50.0))
        assert c.n_segments == 3  # central + 2 pares
        assert c.knee_voltage_V == pytest.approx(10.0)
        assert c.max_point == (40.0, 50.0)

    def test_trecho_central_passa_pela_origem(self):
        c = PiecewiseLinearVI(voltage_V=(10.0, 20.0), current_A=(2.0, 8.0))
        g, b, lo, hi = c.segment(0)
        assert b == pytest.approx(0.0)
        assert g == pytest.approx(0.2)
        assert (lo, hi) == (-10.0, 10.0)
        assert c.current_A_at(0.0) == pytest.approx(0.0)

    def test_caracteristica_e_impar(self):
        c = PiecewiseLinearVI(voltage_V=(10.0, 20.0), current_A=(2.0, 8.0))
        for v in (0.5, 5.0, 10.0, 15.0, 20.0, 60.0):
            assert c.current_A_at(-v) == pytest.approx(-c.current_A_at(v), rel=1e-12)

    def test_pontos_informados_sao_reproduzidos_exatamente(self):
        v = (10.0, 20.0, 40.0)
        i = (1.0, 5.0, 50.0)
        c = PiecewiseLinearVI(voltage_V=v, current_A=i)
        for vk, ik in zip(v, i):
            assert c.current_A_at(vk) == pytest.approx(ik, rel=1e-12)

    def test_extrapola_com_a_inclinacao_do_ultimo_trecho(self):
        c = PiecewiseLinearVI(voltage_V=(10.0, 20.0), current_A=(2.0, 8.0))
        g, b, _lo, _hi = c.segment(1)
        assert c.current_A_at(100.0) == pytest.approx(g * 100.0 + b, rel=1e-12)

    def test_busca_de_trecho_cobre_o_dominio(self):
        c = PiecewiseLinearVI(voltage_V=(10.0, 20.0, 40.0), current_A=(1.0, 5.0, 50.0))
        assert c.segment_index(5.0) == 0
        assert c.segment_index(-5.0) == 0
        assert c.segment_index(15.0) == 1
        assert c.segment_index(30.0) == 2
        assert c.segment_index(4000.0) == 2  # extrapolação fica no último

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"voltage_V": (10.0,), "current_A": (1.0,)},
            {"voltage_V": (10.0, 20.0), "current_A": (1.0,)},
            {"voltage_V": (0.0, 20.0), "current_A": (1.0, 5.0)},
            {"voltage_V": (-10.0, 20.0), "current_A": (1.0, 5.0)},
            {"voltage_V": (20.0, 10.0), "current_A": (1.0, 5.0)},
            {"voltage_V": (10.0, 20.0), "current_A": (5.0, 1.0)},
            {"voltage_V": (10.0, float("nan")), "current_A": (1.0, 5.0)},
        ],
    )
    def test_caracteristica_invalida_levanta(self, kwargs):
        with pytest.raises(ValueError):
            PiecewiseLinearVI(**kwargs)

    def test_trecho_fora_da_faixa_levanta(self):
        c = PiecewiseLinearVI(voltage_V=(10.0, 20.0), current_A=(2.0, 8.0))
        with pytest.raises(IndexError):
            c.segment(9)


# ---------------------------------------------------------------------------
# 2. A álgebra, contra solução analítica
# ---------------------------------------------------------------------------


class TestCompensacaoContraSolucaoAnalitica:
    """``z_T`` e a superposição verificados em circuitos de solução fechada."""

    @staticmethod
    def _divisor(r_serie: float, caracteristica: PiecewiseLinearVI, fonte_V: float):
        ckt = Circuit("divisor")
        ckt.extend(
            [
                _fonte_cc("e", "s", "gnd", fonte_V),
                Resistor("r1", "s", "n", r_serie),
                # Caminho linear de altíssima impedância: mantém o nó 'n'
                # definido quando o ramo compensado é retirado de [Y], que é
                # a condição que Dommel impõe ("no open circuit exists").
                Resistor("rfuga", "n", "gnd", 1.0e12),
                CompensatedBranch("nl", "n", "gnd", caracteristica),
            ]
        )
        solver = Solver(ckt, dt=1.0e-5, init="zero", cda_at_start=False)
        solver.run(t_end=5.0e-5)
        ramo = next(c for c in ckt.components if c.name == "nl")
        return solver, ramo

    def test_thevenin_e_a_resistencia_serie(self):
        solver, _ramo = self._divisor(10.0, LINEAR_20_OHM, 100.0)
        zt = solver._compensation.thevenin_ohm  # noqa: SLF001
        assert zt.shape == (1, 1)
        assert zt[0, 0] == pytest.approx(10.0, rel=1e-9)

    def test_ponto_de_operacao_e_o_do_divisor(self):
        """``v = E·R_nl/(R1 + R_nl)`` com ``R_nl = 20 Ω``."""
        _solver, ramo = self._divisor(10.0, LINEAR_20_OHM, 100.0)
        v_esperado = 100.0 * 20.0 / 30.0
        assert ramo.branch_voltage() == pytest.approx(v_esperado, rel=1e-7)
        assert ramo.branch_current() == pytest.approx(v_esperado / 20.0, rel=1e-7)

    def test_polaridade_invertida_da_o_simetrico(self):
        _solver, ramo = self._divisor(10.0, LINEAR_20_OHM, -100.0)
        assert ramo.branch_voltage() == pytest.approx(-100.0 * 20.0 / 30.0, rel=1e-7)

    def test_troca_de_trecho_e_resolvida_no_mesmo_passo(self):
        """Característica com joelho: o ponto cai no trecho de alta corrente.

        ``i = v/100`` até 10 V; acima, ``i = 0,1 + (v−10)/1`` — resistência
        de 1 Ω. Com fonte de 100 V e série de 10 Ω o ponto exato é
        ``v = (100 − 10·(0,1 − 10)) / (1 + 10) = 18,0 V``.
        """
        c = PiecewiseLinearVI(voltage_V=(10.0, 110.0), current_A=(0.1, 100.1))
        _solver, ramo = self._divisor(10.0, c, 100.0)
        # trecho ativo: g = 1, b = 0,1 − 10 = −9,9 ; v = (100 + 10·9,9)/11
        v_exato = (100.0 + 10.0 * 9.9) / 11.0
        assert ramo.branch_voltage() == pytest.approx(v_exato, rel=1e-7)
        assert ramo.branch_current() == pytest.approx(v_exato - 9.9, rel=1e-6)

    def test_extrapolacao_e_sinalizada(self, caplog):
        c = PiecewiseLinearVI(voltage_V=(1.0, 2.0), current_A=(0.05, 0.1))
        with caplog.at_level("WARNING"):
            _solver, ramo = self._divisor(10.0, c, 100.0)
        assert ramo.extrapolated is True
        assert any("EXTRAPOLADA" in r.message for r in caplog.records)

    def test_ramo_dentro_da_faixa_nao_sinaliza(self):
        _solver, ramo = self._divisor(10.0, LINEAR_20_OHM, 100.0)
        assert ramo.extrapolated is False


# ---------------------------------------------------------------------------
# 3. Vários ramos: o acoplamento
# ---------------------------------------------------------------------------


class TestVariosRamosCompensados:
    """A formulação de ``M`` ramos acopla os ramos pela rede."""

    @staticmethod
    def _dois_ramos(r_comum: float, r_a: float, r_b: float):
        """Dois ramos não lineares pendurados no MESMO nó por resistores.

        ``E ─R_comum─ n ─R_a─ a ─NL_a─ gnd``
        ``                └──R_b─ b ─NL_b─ gnd``

        O acoplamento é real: a corrente de um ramo muda a tensão do outro
        através de ``R_comum``.
        """
        ckt = Circuit("dois")
        ckt.extend(
            [
                _fonte_cc("e", "s", "gnd", 100.0),
                Resistor("rc", "s", "n", r_comum),
                Resistor("ra", "n", "a", r_a),
                Resistor("rb", "n", "b", r_b),
                Resistor("fa", "a", "gnd", 1.0e12),
                Resistor("fb", "b", "gnd", 1.0e12),
                CompensatedBranch("nl_a", "a", "gnd", LINEAR_20_OHM),
                CompensatedBranch("nl_b", "b", "gnd", LINEAR_20_OHM),
            ]
        )
        solver = Solver(ckt, dt=1.0e-5, init="zero", cda_at_start=False)
        solver.run(t_end=5.0e-5)
        ra = next(c for c in ckt.components if c.name == "nl_a")
        rb = next(c for c in ckt.components if c.name == "nl_b")
        return solver, ra, rb

    def test_matriz_de_thevenin_tem_termos_cruzados(self):
        solver, _a, _b = self._dois_ramos(5.0, 10.0, 10.0)
        zt = solver._compensation.thevenin_ohm  # noqa: SLF001
        assert zt.shape == (2, 2)
        # Os ramos compensados estão FORA de [Y]: a impedância vista de 'a'
        # é R_a em série com R_comum, porque o caminho por R_b termina no
        # resistor de fuga de 1 TΩ. Logo 10 + 5 = 15 Ω.
        assert zt[0, 0] == pytest.approx(15.0, rel=1e-6)
        assert zt[1, 1] == pytest.approx(15.0, rel=1e-6)
        # Cruzado: 1 A saindo de 'b' atravessa R_comum e eleva 'n' — e com
        # ele 'a', que não conduz — em 5 V. A matriz é simétrica.
        assert zt[0, 1] == pytest.approx(5.0, rel=1e-6)
        assert zt[0, 1] == pytest.approx(zt[1, 0], rel=1e-9)

    def test_solucao_bate_com_o_circuito_resistivo_equivalente(self):
        """Todos os ramos na região linear: resolve-se por associação."""
        _solver, ra, rb = self._dois_ramos(5.0, 10.0, 10.0)
        # Dois ramos de 30 Ω em paralelo = 15 Ω, em série com 5 Ω:
        v_n = 100.0 * 15.0 / 20.0
        v_nl = v_n * 20.0 / 30.0
        assert ra.branch_voltage() == pytest.approx(v_nl, rel=1e-6)
        assert rb.branch_voltage() == pytest.approx(v_nl, rel=1e-6)

    def test_ramos_assimetricos_dao_pontos_distintos(self):
        _solver, ra, rb = self._dois_ramos(5.0, 10.0, 40.0)
        assert ra.branch_voltage() > rb.branch_voltage()


# ---------------------------------------------------------------------------
# 4. Topologia e ciclo de vida
# ---------------------------------------------------------------------------


class TestTopologiaECicloDeVida:
    def test_thevenin_e_recomputada_quando_a_topologia_muda(self):
        """"the slope z_T remains unchanged as long as no switchings take place"."""
        ckt = Circuit("chaveado")
        chave = Switch("sw", "s", "n", closed=True)
        ckt.extend(
            [
                _fonte_cc("e", "s", "gnd", 100.0),
                chave,
                Resistor("r1", "n", "m", 10.0),
                Resistor("rfuga", "m", "gnd", 1.0e12),
                CompensatedBranch("nl", "m", "gnd", LINEAR_20_OHM),
            ]
        )
        solver = Solver(ckt, dt=1.0e-5, init="zero", cda_at_start=False)
        solver.run(t_end=2.0e-5)
        zt_fechada = solver._compensation.thevenin_ohm[0, 0]  # noqa: SLF001

        def abre(t, s):
            if t >= 3.0e-5:
                chave.open()

        solver.run(t_end=8.0e-5, controllers=[abre], reset=False)
        zt_aberta = solver._compensation.thevenin_ohm[0, 0]  # noqa: SLF001
        assert zt_fechada == pytest.approx(10.0, rel=1e-6)
        # Com a chave aberta o ramo enxerga o caminho de fuga: z_T explode.
        assert zt_aberta > 1.0e6

    def test_ramo_compensado_nao_estampa_a_matriz(self):
        ckt = Circuit("estampa")
        ckt.extend(
            [
                _fonte_cc("e", "s", "gnd", 100.0),
                Resistor("r1", "s", "n", 10.0),
                Resistor("rfuga", "n", "gnd", 1.0e12),
                CompensatedBranch("nl", "n", "gnd", LINEAR_20_OHM),
            ]
        )
        ckt.build()
        ckt.prepare(1.0e-5)
        A = ckt.assemble_matrix()
        sem = Circuit("sem")
        sem.extend(
            [
                _fonte_cc("e", "s", "gnd", 100.0),
                Resistor("r1", "s", "n", 10.0),
                Resistor("rfuga", "n", "gnd", 1.0e12),
            ]
        )
        sem.build()
        sem.prepare(1.0e-5)
        assert np.allclose(A, sem.assemble_matrix())

    def test_mudanca_de_trecho_nao_muda_a_assinatura_de_topologia(self):
        """É a vantagem central da compensação: sem refatoração por trecho."""
        ramo = CompensatedBranch("nl", "n", "gnd", LINEAR_20_OHM)
        antes = ramo.topology_signature()
        ramo.set_active_segment(1, -1.0)
        assert ramo.topology_signature() == antes

    def test_reset_zera_o_estado_acumulado(self):
        ramo = CompensatedBranch("nl", "n", "gnd", LINEAR_20_OHM)
        ramo.set_solution(50.0, 2.5, 1.0e-3)
        ramo.set_solution(60.0, 3.0, 2.0e-3)
        assert ramo.energy_J > 0.0
        ramo.reset()
        assert ramo.energy_J == 0.0
        assert ramo.peak_voltage_V == 0.0
        assert ramo.peak_current_A == 0.0

    def test_energia_e_a_integral_trapezoidal_da_potencia(self):
        ramo = CompensatedBranch("nl", "n", "gnd", LINEAR_20_OHM)
        ramo.set_solution(0.0, 0.0, 0.0)
        ramo.set_solution(100.0, 5.0, 1.0e-3)
        # trapézio de (0·0) a (100·5) em 1 ms = 0,5·500·1e-3
        assert ramo.energy_J == pytest.approx(0.25, rel=1e-12)

    def test_terminais_iguais_levantam(self):
        with pytest.raises(ValueError, match="curto-circuitado"):
            CompensatedBranch("nl", "n", "n", LINEAR_20_OHM)

    def test_caracteristica_de_tipo_errado_levanta(self):
        with pytest.raises(TypeError, match="PiecewiseLinearVI"):
            CompensatedBranch("nl", "n", "gnd", object())  # type: ignore[arg-type]

    def test_nos_antes_de_build_levantam(self):
        ramo = CompensatedBranch("nl", "n", "gnd", LINEAR_20_OHM)
        with pytest.raises(ValueError, match="não foi ligado"):
            ramo.compensation_nodes()

    def test_coleta_reconhece_apenas_ramos_compensados(self):
        ramo = CompensatedBranch("nl", "n", "gnd", LINEAR_20_OHM)
        r = Resistor("r", "n", "gnd", 10.0)
        assert collect_compensated([r, ramo]) == (ramo,)

    def test_rede_vazia_e_transparente(self):
        rede = CompensationNetwork(())
        assert len(rede) == 0
        x = np.array([1.0, 2.0, 3.0])
        assert np.allclose(rede.correct(x, 0.0), x)

    def test_correct_antes_de_prepare_levanta(self):
        ramo = CompensatedBranch("nl", "n", "gnd", LINEAR_20_OHM)
        rede = CompensationNetwork((ramo,))
        with pytest.raises(ValueError, match="prepare"):
            rede.correct(np.zeros(3), 0.0)

    def test_thevenin_antes_de_prepare_levanta(self):
        rede = CompensationNetwork((CompensatedBranch("nl", "n", "gnd", LINEAR_20_OHM),))
        with pytest.raises(ValueError, match="prepare"):
            _ = rede.thevenin_ohm


# ---------------------------------------------------------------------------
# 5. Regime permanente
# ---------------------------------------------------------------------------


class TestRegimePermanente:
    def test_estampa_a_condutancia_do_trecho_central(self):
        """Abaixo do joelho a linearização é EXATA, não aproximada."""
        ckt = Circuit("regime")
        ckt.extend(
            [
                VoltageSource(
                    "e", "s", "gnd", amplitude_V=100.0, frequency_Hz=60.0,
                    phase_reference="cos",
                ),
                Resistor("r1", "s", "n", 1.0),
                Resistor("rfuga", "n", "gnd", 1.0e12),
                CompensatedBranch("nl", "n", "gnd", LINEAR_20_OHM),
            ]
        )
        solver = Solver(ckt, dt=1.0e-5, init="steady_state", cda_at_start=False)
        solver.run(t_end=1.0e-3)
        ramo = next(c for c in ckt.components if c.name == "nl")
        # Divisor 1 Ω / 20 Ω: pico de 100·20/21 = 95,238 V
        assert abs(ramo.peak_voltage_V) == pytest.approx(100.0 * 20.0 / 21.0, rel=1e-3)

    def test_ponto_de_regime_acima_do_joelho_e_registrado(self, caplog):
        ramo = CompensatedBranch("nl", "n", "gnd", LINEAR_20_OHM)
        with caplog.at_level("WARNING"):
            assert ramo.check_phasor_operating_point(complex(100.0, 0.0)) is False
        assert any("joelho" in r.message for r in caplog.records)
        assert ramo.check_phasor_operating_point(complex(5.0, 0.0)) is True


# ---------------------------------------------------------------------------
# 6. Limitações declaradas
# ---------------------------------------------------------------------------


def test_limitacoes_declaradas_e_sem_colisao_com_o_kernel():
    from app.simulation.emt import KNOWN_LIMITATIONS as KERNEL

    assert "emt_nonlinear_absent_from_phasor_solution" in KNOWN_LIMITATIONS
    assert "emt_nonlinear_odd_symmetry_assumed" in KNOWN_LIMITATIONS
    assert "emt_nonlinear_extrapolates_beyond_last_point" in KNOWN_LIMITATIONS
    assert not set(KNOWN_LIMITATIONS) & set(KERNEL)
    for chave, texto in KNOWN_LIMITATIONS.items():
        assert chave.startswith("emt_")
        assert len(texto) > 80
