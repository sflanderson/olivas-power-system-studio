"""
tests/test_emt_vcb_scenarios.py — parâmetros de disjuntor a vácuo como
faixas da literatura.

O que estes testes fixam
========================

1. **As faixas são as das fontes primárias**, e o cenário do caso de
   referência está declarado FORA delas nos três parâmetros.
2. **A amostragem é reprodutível** por semente e respeita os limites.
3. **A conversão de unidades da recuperação dielétrica é exata**:
   ``1 kV/ms = 1 V/µs``.
4. **A convenção de extinção é a física** (``interrupt_within``): o arco
   se extingue quando o ``di/dt`` está DENTRO da capacidade — o oposto do
   que o arquivo de referência executa.
5. **O caso ancorado honra as amostras**, substituindo os valores do
   arquivo por realização.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.simulation.emt.vcb import (
    DIDT_INTERRUPT_WITHIN,
    LinearRecovery,
    ParabolicRecovery,
)
from app.simulation.emt.vcb_scenarios import (
    DOC_A_SCENARIO,
    FIELD_PEAK_CEILING_PU,
    LITERATURE_CHOPPING_RANGE_A,
    LITERATURE_DIDT_RANGE_A_PER_US,
    LITERATURE_RRDS_RANGE_KV_PER_MS,
    LITERATURE_RRDS_WORST_KV_PER_MS,
    LITERATURE_SCENARIO,
    LITERATURE_WORST_ARC_TIME_S,
    MEASURED_SCENARIO,
    SCENARIOS,
    PoleCurrentZeros,
    VcbParameterRanges,
    sample_vcb_parameters,
    sample_vcb_parameters_by_arc_time,
    scenario,
    sweep_samples,
    sweep_three_pole_samples,
)

JANELA = (14.0e-3, 30.7e-3)


# ---------------------------------------------------------------------------
# 1. As faixas e sua procedência
# ---------------------------------------------------------------------------


def test_faixas_da_literatura_sao_as_das_fontes_primarias():
    """Valores conferidos no anexo de física de surtos da Etapa 1."""
    assert LITERATURE_CHOPPING_RANGE_A == (2.0, 10.0)      # Vollet 2007
    assert LITERATURE_DIDT_RANGE_A_PER_US == (100.0, 600.0)  # Wong 2003; Abdulahovic 2011
    assert LITERATURE_RRDS_RANGE_KV_PER_MS == (5.0, 50.0)  # Vollet; Wong; Abdulahovic
    assert LITERATURE_RRDS_WORST_KV_PER_MS == (20.0, 30.0)  # Wong 2003, escalada máxima
    assert FIELD_PEAK_CEILING_PU == pytest.approx(4.6)      # campanha EPRI, 33 motores


def test_cenario_do_caso_de_referencia_esta_fora_da_faixa_nos_tres_parametros():
    """É o achado que motiva este módulo: os três parâmetros agravam o caso.

    Recuperação 10 a 25 vezes mais lenta, extinção 7 a 120 vezes mais
    fácil e corte abaixo da faixa de contatos Cu/Cr — a combinação que
    maximiza reignições.
    """
    d, lit = DOC_A_SCENARIO, LITERATURE_SCENARIO
    assert d.within_literature is False
    assert lit.within_literature is True
    # Corte abaixo da faixa publicada: o máximo do caso apenas TOCA o
    # mínimo de Vollet (2 A), e o mínimo do caso é metade dele.
    assert d.chopping_A[1] <= lit.chopping_A[0]
    assert d.chopping_A[0] < lit.chopping_A[0]
    # Extinção muito mais fácil: o MÁXIMO do caso é uma fração do mínimo.
    assert d.didt_A_per_us[1] < 0.2 * lit.didt_A_per_us[0]
    # Recuperação muito mais lenta na origem.
    assert d.rrds_kV_per_ms[0] < 0.2 * lit.rrds_kV_per_ms[0]


def test_cenario_medido_esta_dentro_da_faixa_publicada():
    """Abdulahovic 2011: RRDS inicial 5,5 kV/ms, di/dt 250-350 A/µs."""
    m = MEASURED_SCENARIO
    assert m.within_literature
    assert LITERATURE_RRDS_RANGE_KV_PER_MS[0] <= m.rrds_kV_per_ms[0]
    assert m.rrds_kV_per_ms[1] <= LITERATURE_RRDS_RANGE_KV_PER_MS[1]
    assert LITERATURE_DIDT_RANGE_A_PER_US[0] <= m.didt_A_per_us[0]
    assert m.didt_A_per_us[1] <= LITERATURE_DIDT_RANGE_A_PER_US[1]


def test_selecao_por_nome_e_cenario_desconhecido_levanta():
    assert scenario("literatura") is LITERATURE_SCENARIO
    assert set(SCENARIOS) == {"literatura", "medido", "caso_de_referencia"}
    with pytest.raises(ValueError, match="cenário desconhecido"):
        scenario("inexistente")


def test_selecao_de_cenario_fora_da_faixa_emite_aviso(caplog):
    """Requisito de auditabilidade: o desvio precisa aparecer no log."""
    with caplog.at_level("WARNING"):
        scenario("caso_de_referencia")
    assert any("FORA da faixa publicada" in r.message for r in caplog.records)


def test_pior_caso_restringe_a_rrds_a_faixa_de_escalada_maxima():
    """Wong 2003: a escalada é máxima em RRDS intermediária, não na mínima."""
    pior = LITERATURE_SCENARIO.narrowed_to_worst_case()
    assert pior.rrds_kV_per_ms == LITERATURE_RRDS_WORST_KV_PER_MS
    assert pior.chopping_A == LITERATURE_SCENARIO.chopping_A
    assert pior.name.endswith("_pior_caso")


# ---------------------------------------------------------------------------
# 2. Validação de entradas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chopping_A": (0.0, 10.0)},        # limite inferior nulo
        {"didt_A_per_us": (600.0, 100.0)},  # invertida
        {"rrds_kV_per_ms": (5.0, float("inf"))},
        {"rrds_parabolic_kV_per_ms2": -1.0},
        {"name": "  "},
    ],
)
def test_faixas_invalidas_levantam(kwargs):
    base = {"name": "t"}
    base.update(kwargs)
    with pytest.raises(ValueError):
        VcbParameterRanges(**base)


def test_janela_de_separacao_invalida_levanta():
    rng = np.random.default_rng(0)
    for janela in ((-1.0e-3, 1.0e-3), (2.0e-3, 1.0e-3)):
        with pytest.raises(ValueError, match="separation_window_s"):
            sample_vcb_parameters(
                LITERATURE_SCENARIO, rng=rng, separation_window_s=janela
            )


def test_numero_de_amostras_invalido_levanta():
    with pytest.raises(ValueError, match="n deve ser > 0"):
        sweep_samples(LITERATURE_SCENARIO, n=0, separation_window_s=JANELA)


# ---------------------------------------------------------------------------
# 3. Amostragem
# ---------------------------------------------------------------------------


def test_amostragem_respeita_os_limites_e_a_janela():
    amostras = sweep_samples(
        LITERATURE_SCENARIO, n=200, separation_window_s=JANELA, seed=3
    )
    assert len(amostras) == 200
    for a in amostras:
        assert LITERATURE_CHOPPING_RANGE_A[0] <= a.chopping_current_A <= LITERATURE_CHOPPING_RANGE_A[1]
        assert (
            LITERATURE_DIDT_RANGE_A_PER_US[0]
            <= a.didt_capability_A_per_us
            <= LITERATURE_DIDT_RANGE_A_PER_US[1]
        )
        assert LITERATURE_RRDS_RANGE_KV_PER_MS[0] <= a.rrds_a_kV_per_ms <= LITERATURE_RRDS_RANGE_KV_PER_MS[1]
        assert JANELA[0] <= a.separation_time_s <= JANELA[1]
        assert a.scenario_name == "literatura"


def test_amostragem_cobre_a_janela_de_separacao():
    """A janela é um ciclo inteiro: sem cobertura não há varredura."""
    t = np.array(
        [a.separation_time_s for a in sweep_samples(
            LITERATURE_SCENARIO, n=400, separation_window_s=JANELA, seed=5
        )]
    )
    assert t.min() < JANELA[0] + 0.1 * (JANELA[1] - JANELA[0])
    assert t.max() > JANELA[1] - 0.1 * (JANELA[1] - JANELA[0])


def test_amostragem_e_reprodutivel_por_semente():
    a = sweep_samples(LITERATURE_SCENARIO, n=20, separation_window_s=JANELA, seed=11)
    b = sweep_samples(LITERATURE_SCENARIO, n=20, separation_window_s=JANELA, seed=11)
    c = sweep_samples(LITERATURE_SCENARIO, n=20, separation_window_s=JANELA, seed=12)
    assert a == b
    assert a != c


def test_faixa_degenerada_devolve_o_proprio_valor():
    """Cenário determinístico: mínimo igual ao máximo."""
    fixo = VcbParameterRanges(
        name="fixo", chopping_A=(3.0, 3.0), didt_A_per_us=(300.0, 300.0),
        rrds_kV_per_ms=(20.0, 20.0),
    )
    a = sweep_samples(fixo, n=5, separation_window_s=(0.01, 0.01), seed=1)
    for x in a:
        assert x.chopping_current_A == 3.0
        assert x.didt_capability_A_per_us == 300.0
        assert x.rrds_a_kV_per_ms == 20.0
        assert x.separation_time_s == 0.01


# ---------------------------------------------------------------------------
# 4. Recuperação dielétrica e convenção de extinção
# ---------------------------------------------------------------------------


def test_recuperacao_linear_com_identidade_de_unidades_exata():
    """``1 kV/ms = 1 V/µs`` [CÁLCULO PRÓPRIO] — sem fator de conversão."""
    a = sweep_samples(
        VcbParameterRanges(name="t", rrds_kV_per_ms=(20.0, 20.0)),
        n=1, separation_window_s=(0.01, 0.01),
    )[0]
    rec = a.recovery()
    assert isinstance(rec, LinearRecovery)
    assert rec.u0_V == 0.0
    # 20 kV/ms durante 1 ms = 20 kV.
    assert rec.withstand_V(1.0e-3) == pytest.approx(20_000.0)
    assert rec.withstand_V(0.0) == 0.0


def test_recuperacao_parabolica_apenas_quando_o_termo_quadratico_existe():
    a = sweep_samples(DOC_A_SCENARIO, n=1, separation_window_s=(0.01, 0.01))[0]
    rec = a.recovery()
    assert isinstance(rec, ParabolicRecovery)
    # 0,801·1 + 1,226·1² = 2,027 kV em 1 ms.
    assert rec.withstand_V(1.0e-3) == pytest.approx(2027.0, rel=1e-3)


def test_o_caso_de_referencia_recupera_uma_ordem_de_grandeza_mais_devagar():
    """2,03 kV contra 20 kV em 1 ms — é a raiz das reignições em excesso."""
    doc = sweep_samples(DOC_A_SCENARIO, n=1, separation_window_s=(0.01, 0.01))[0]
    lit = sweep_samples(
        VcbParameterRanges(name="t", rrds_kV_per_ms=(20.0, 20.0)),
        n=1, separation_window_s=(0.01, 0.01),
    )[0]
    razao = lit.recovery().withstand_V(1.0e-3) / doc.recovery().withstand_V(1.0e-3)
    assert razao > 9.0


def test_convencao_de_extincao_e_a_fisica():
    """Wong 2003: acima do limite de di/dt o arco PERSISTE."""
    a = sweep_samples(LITERATURE_SCENARIO, n=1, separation_window_s=JANELA)[0]
    kwargs = a.as_pole_kwargs()
    assert kwargs["didt_convention"] == DIDT_INTERRUPT_WITHIN
    assert set(kwargs) == {
        "separation_time_s",
        "chopping_current_A",
        "recovery",
        "didt_capability_A_per_us",
        "didt_convention",
    }


# ---------------------------------------------------------------------------
# 5. Integração com o caso ancorado
# ---------------------------------------------------------------------------


def test_caso_ancorado_honra_as_amostras_por_polo():
    from app.simulation.emt.cases.atp_reference import build_reference_model

    amostras = sweep_samples(
        LITERATURE_SCENARIO, n=3, separation_window_s=JANELA, seed=1
    )
    m = build_reference_model(
        with_snubber=False, vcb_samples=tuple(amostras), t_end_s=1.0e-3
    )
    for polo, a in zip(m.poles, amostras):
        assert polo.separation_time_s == pytest.approx(a.separation_time_s)
        assert polo.sampled_chopping_current_A == pytest.approx(a.chopping_current_A)
        assert polo.didt_capability_A_per_us == pytest.approx(a.didt_capability_A_per_us)
        assert polo.didt_convention == DIDT_INTERRUPT_WITHIN


def test_numero_errado_de_amostras_levanta():
    from app.simulation.emt.cases.atp_reference import build_reference_model

    amostras = sweep_samples(
        LITERATURE_SCENARIO, n=2, separation_window_s=JANELA, seed=1
    )
    with pytest.raises(ValueError, match="uma por fase"):
        build_reference_model(vcb_samples=tuple(amostras), t_end_s=1.0e-3)


def test_sem_amostras_o_caso_usa_os_valores_do_arquivo():
    from app.simulation.emt.cases.atp_reference import (
        VCB_CHOPPING_CURRENT_A,
        VCB_SEPARATION_TIME_S,
        build_reference_model,
    )

    m = build_reference_model(with_snubber=False, t_end_s=1.0e-3)
    for polo, t_sep, i_ch in zip(m.poles, VCB_SEPARATION_TIME_S, VCB_CHOPPING_CURRENT_A):
        assert polo.separation_time_s == pytest.approx(t_sep)
        assert polo.sampled_chopping_current_A == pytest.approx(i_ch)


# ---------------------------------------------------------------------------
# 6. Amostragem por tempo de arco
# ---------------------------------------------------------------------------


class TestZerosDeCorrenteDoPolo:
    """A geometria dos zeros, que é o que define o tempo de arco."""

    def test_zeros_espacados_de_meio_periodo(self):
        z = PoleCurrentZeros(phase_angle_rad=0.0, frequency_Hz=60.0)
        t1 = z.first_zero_after(0.0)
        t2 = z.first_zero_after(t1)
        assert t2 - t1 == pytest.approx(z.half_period_s, rel=1e-12)
        assert z.half_period_s == pytest.approx(1.0 / 120.0, rel=1e-12)

    def test_primeiro_zero_de_uma_cossenoide_com_fase_nula(self):
        """``cos(ωt) = 0`` em ``t = T/4``."""
        z = PoleCurrentZeros(phase_angle_rad=0.0, frequency_Hz=60.0)
        assert z.first_zero_after(0.0) == pytest.approx(1.0 / 240.0, rel=1e-12)

    def test_o_zero_devolvido_anula_a_corrente(self):
        z = PoleCurrentZeros(phase_angle_rad=0.7, frequency_Hz=60.0)
        tz = z.first_zero_after(0.021)
        assert np.cos(z.omega_rad_s * tz + z.phase_angle_rad) == pytest.approx(
            0.0, abs=1e-12
        )

    def test_busca_e_estritamente_posterior_mesmo_partindo_de_um_zero(self):
        z = PoleCurrentZeros(phase_angle_rad=-0.3, frequency_Hz=60.0)
        tz = z.first_zero_after(0.01)
        assert z.first_zero_after(tz) == pytest.approx(tz + z.half_period_s, rel=1e-12)

    def test_construcao_a_partir_do_fasor(self):
        z = PoleCurrentZeros.from_phasor(74.0 * np.exp(1j * 0.42), frequency_Hz=60.0)
        assert z.phase_angle_rad == pytest.approx(0.42, rel=1e-12)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"phase_angle_rad": float("nan")},
            {"phase_angle_rad": 0.0, "frequency_Hz": 0.0},
            {"phase_angle_rad": 0.0, "frequency_Hz": -60.0},
        ],
    )
    def test_parametros_invalidos_levantam(self, kwargs):
        with pytest.raises(ValueError):
            PoleCurrentZeros(**kwargs)

    def test_fasor_nulo_levanta(self):
        with pytest.raises(ValueError, match="nulo"):
            PoleCurrentZeros.from_phasor(0j)


class TestSeparacaoDerivadaDoTempoDeArco:
    """O recuo a partir do zero de corrente é exato e respeita o piso."""

    def test_o_tempo_de_arco_realizado_e_o_pedido(self):
        z = PoleCurrentZeros(phase_angle_rad=1.1, frequency_Hz=60.0)
        for tau in (0.0, 5.0e-6, 50.0e-6, 99.0e-6):
            t_sep = z.separation_for_arc_time(tau, earliest_separation_s=14.0e-3)
            assert z.arc_time_after(t_sep) == pytest.approx(tau, abs=1e-12)

    def test_separacao_nunca_fica_abaixo_do_piso(self):
        z = PoleCurrentZeros(phase_angle_rad=-2.0, frequency_Hz=60.0)
        piso = 14.0e-3
        for tau in np.linspace(0.0, 100.0e-6, 25):
            assert z.separation_for_arc_time(float(tau), earliest_separation_s=piso) >= piso

    def test_tempo_de_arco_acima_de_meio_periodo_levanta(self):
        z = PoleCurrentZeros(phase_angle_rad=0.0, frequency_Hz=60.0)
        with pytest.raises(ValueError, match="meio período"):
            z.separation_for_arc_time(z.half_period_s)

    @pytest.mark.parametrize("tau", [-1.0e-6, float("inf"), float("nan")])
    def test_tempo_de_arco_invalido_levanta(self, tau):
        z = PoleCurrentZeros(phase_angle_rad=0.0, frequency_Hz=60.0)
        with pytest.raises(ValueError):
            z.separation_for_arc_time(tau)

    def test_piso_invalido_levanta(self):
        z = PoleCurrentZeros(phase_angle_rad=0.0, frequency_Hz=60.0)
        with pytest.raises(ValueError, match="earliest_separation_s"):
            z.separation_for_arc_time(10.0e-6, earliest_separation_s=-1.0)


class TestAmostragemPorTempoDeArco:
    """A varredura passa a ter a janela de escalada como alvo, e não como sorte."""

    def test_janela_padrao_e_a_de_escalada_maxima_de_wong(self):
        assert LITERATURE_WORST_ARC_TIME_S == (0.0, 100.0e-6)

    def test_amostras_caem_na_janela_pedida(self):
        z = PoleCurrentZeros(phase_angle_rad=0.9, frequency_Hz=60.0)
        rng = np.random.default_rng(3)
        amostras = [
            sample_vcb_parameters_by_arc_time(
                LITERATURE_SCENARIO, rng=rng, zeros=z, earliest_separation_s=14.0e-3
            )
            for _ in range(200)
        ]
        taus = np.array([a.arc_time_s for a in amostras])
        assert taus.min() >= 0.0
        assert taus.max() <= 100.0e-6
        assert taus.max() - taus.min() > 80.0e-6  # cobre a janela
        for a in amostras:
            assert z.arc_time_after(a.separation_time_s) == pytest.approx(
                a.arc_time_s, abs=1e-12
            )

    def test_amostragem_uniforme_no_ciclo_quase_nunca_atinge_a_janela(self):
        """O motivo de existir esta parametrização.

        100 µs sobre os 8,333 ms entre zeros são 1,2 % do ciclo: a
        varredura uniforme cai na janela de escalada cerca de uma vez em
        cada 83 realizações [CÁLCULO PRÓPRIO].
        """
        z = PoleCurrentZeros(phase_angle_rad=0.9, frequency_Hz=60.0)
        uniformes = sweep_samples(
            LITERATURE_SCENARIO, n=500, separation_window_s=(14.0e-3, 30.7e-3), seed=1
        )
        na_janela = sum(
            1 for a in uniformes if z.arc_time_after(a.separation_time_s) <= 100.0e-6
        )
        assert na_janela / len(uniformes) < 0.05

        dirigidas = [
            sample_vcb_parameters_by_arc_time(
                LITERATURE_SCENARIO,
                rng=np.random.default_rng(k),
                zeros=z,
                earliest_separation_s=14.0e-3,
            )
            for k in range(50)
        ]
        assert all(a.arc_time_s <= 100.0e-6 for a in dirigidas)

    def test_parametros_do_disjuntor_continuam_nas_faixas(self):
        z = PoleCurrentZeros(phase_angle_rad=0.0, frequency_Hz=60.0)
        rng = np.random.default_rng(11)
        for _ in range(100):
            a = sample_vcb_parameters_by_arc_time(LITERATURE_SCENARIO, rng=rng, zeros=z)
            assert (
                LITERATURE_SCENARIO.chopping_A[0]
                <= a.chopping_current_A
                <= LITERATURE_SCENARIO.chopping_A[1]
            )
            assert (
                LITERATURE_SCENARIO.didt_A_per_us[0]
                <= a.didt_capability_A_per_us
                <= LITERATURE_SCENARIO.didt_A_per_us[1]
            )
            assert (
                LITERATURE_SCENARIO.rrds_kV_per_ms[0]
                <= a.rrds_a_kV_per_ms
                <= LITERATURE_SCENARIO.rrds_kV_per_ms[1]
            )

    @pytest.mark.parametrize("janela", [(-1.0e-6, 1.0e-6), (2.0e-6, 1.0e-6)])
    def test_janela_de_tempo_de_arco_invalida_levanta(self, janela):
        z = PoleCurrentZeros(phase_angle_rad=0.0, frequency_Hz=60.0)
        with pytest.raises(ValueError, match="arc_time_window_s"):
            sample_vcb_parameters_by_arc_time(
                LITERATURE_SCENARIO,
                rng=np.random.default_rng(0),
                zeros=z,
                arc_time_window_s=janela,
            )


class TestVarreduraTripolar:
    """Os três polos partilham o acionamento; só os zeros os separam."""

    ZEROS = (
        PoleCurrentZeros(phase_angle_rad=0.0, frequency_Hz=60.0),
        PoleCurrentZeros(phase_angle_rad=-2.0 * np.pi / 3.0, frequency_Hz=60.0),
        PoleCurrentZeros(phase_angle_rad=2.0 * np.pi / 3.0, frequency_Hz=60.0),
    )

    def test_separacao_e_comum_as_tres_fases(self):
        for tripla in sweep_three_pole_samples(
            LITERATURE_SCENARIO,
            n=25,
            zeros_abc=self.ZEROS,
            earliest_separation_s=14.0e-3,
            seed=7,
        ):
            t = tripla[0].separation_time_s
            assert all(p.separation_time_s == t for p in tripla)

    def test_tempos_de_arco_diferem_entre_as_fases_por_um_terco_de_meio_periodo(self):
        """Zeros defasados de 120° elétricos ficam a ``T/6`` um do outro."""
        tripla = sweep_three_pole_samples(
            LITERATURE_SCENARIO,
            n=1,
            zeros_abc=self.ZEROS,
            earliest_separation_s=14.0e-3,
            seed=5,
        )[0]
        taus = sorted(p.arc_time_s for p in tripla)
        passo = 1.0 / 360.0  # T/6 em 60 Hz
        assert taus[1] - taus[0] == pytest.approx(passo, abs=2.0e-4)
        assert taus[2] - taus[1] == pytest.approx(passo, abs=2.0e-4)

    def test_o_polo_condutor_e_o_que_cai_na_janela(self):
        for k in (0, 1, 2):
            tripla = sweep_three_pole_samples(
                LITERATURE_SCENARIO,
                n=20,
                zeros_abc=self.ZEROS,
                earliest_separation_s=14.0e-3,
                leading_pole=k,
                seed=2,
            )
            assert all(p[k].arc_time_s <= 100.0e-6 for p in tripla)

    def test_parametros_do_arco_sao_sorteados_por_polo(self):
        """Corte, di/dt e RRDS são do arco, não do acionamento."""
        triplas = sweep_three_pole_samples(
            LITERATURE_SCENARIO,
            n=30,
            zeros_abc=self.ZEROS,
            earliest_separation_s=14.0e-3,
            seed=13,
        )
        iguais = sum(
            1
            for t in triplas
            if len({round(p.chopping_current_A, 9) for p in t}) == 1
        )
        assert iguais == 0

    def test_reprodutibilidade_por_semente(self):
        kwargs = dict(
            n=10, zeros_abc=self.ZEROS, earliest_separation_s=14.0e-3, seed=99
        )
        a = sweep_three_pole_samples(LITERATURE_SCENARIO, **kwargs)
        b = sweep_three_pole_samples(LITERATURE_SCENARIO, **kwargs)
        assert a == b

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"n": 0},
            {"zeros_abc": ZEROS[:2]},
            {"leading_pole": 3},
        ],
    )
    def test_argumentos_invalidos_levantam(self, kwargs):
        base = dict(n=5, zeros_abc=self.ZEROS, earliest_separation_s=14.0e-3)
        base.update(kwargs)
        with pytest.raises(ValueError):
            sweep_three_pole_samples(LITERATURE_SCENARIO, **base)


# ---------------------------------------------------------------------------
# 7. Domínio de validade da cauda de escalada
# ---------------------------------------------------------------------------


class TestEscaladaComandadaPelaRampaDeRecuperacao:
    """Fixa o DEFEITO diagnosticado na varredura de 150 realizações.

    A escalada que o motor produz não é a publicada: em cada reignição a
    tensão do *gap* iguala a suportabilidade instantânea, de modo que o
    pico é ``RRDS·Δt`` — a rampa dielétrica define o pico em vez de
    limitá-lo. O diagnóstico completo, com as medições, está em
    ``docs/research/rul_isolamento/08_VARREDURA_ESTATISTICA_VCB.md``.

    Estes testes existem para que a correção — representar o caminho
    capacitivo nos terminais do disjuntor — seja DETECTÁVEL: quando ela
    entrar, eles falham e devem ser reescritos com o comportamento
    publicado (escalada máxima em RRDS de 20 a 30 kV/ms, pico abaixo de
    ``FIELD_PEAK_CEILING_PU``).
    """

    def test_limitacao_esta_declarada(self):
        from app.simulation.emt.vcb import KNOWN_LIMITATIONS

        chave = "emt_vcb_escalation_driven_by_recovery_ramp"
        assert chave in KNOWN_LIMITATIONS
        texto = KNOWN_LIMITATIONS[chave]
        assert "Wong" in texto and "Vollet" in texto
        assert "FIELD_PEAK_CEILING_PU" in texto

    def test_tensao_de_reignicao_acompanha_a_rampa_de_suportabilidade(self):
        """``|v_gap| ≈ RRDS·(t − t_sep)`` em cada evento — a assinatura do defeito."""
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase
        from app.simulation.emt.vcb_scenarios import VcbSample

        rrds = 44.3  # kV/ms — a da pior realização da varredura
        t_sep = 14.6865e-3
        amostras = tuple(
            VcbSample(
                scenario_name="literatura",
                chopping_current_A=corte,
                didt_capability_A_per_us=didt,
                rrds_a_kV_per_ms=rrds,
                rrds_b_kV_per_ms2=0.0,
                separation_time_s=t_sep,
                arc_time_s=None,
            )
            for corte, didt in ((2.71, 460.0), (2.84, 457.0), (5.41, 199.0))
        )
        modelo = AtpReferenceCase(with_snubber=False, vcb_samples=amostras).build()
        modelo.run()

        polo = modelo.poles[0]
        r = polo.result
        assert r.reignition_count > 10, "a realização precisa entrar em escalada"

        t = np.array(r.reignition_times_s)
        v = np.abs(np.array(r.reignition_voltages_V))
        w = np.array(r.reignition_withstand_V)

        # A suportabilidade registrada É a rampa, referenciada à separação.
        rampa = rrds * 1.0e3 * (t - t_sep) * 1.0e3  # kV/ms · ms → V
        assert np.allclose(w, rampa, rtol=1e-9, atol=1.0)

        # E a tensão de reignição a acompanha: nunca fica muito acima dela.
        assert np.all(v >= w)
        assert float(np.median(v / w)) < 1.5

        # Consequência: o pico escala com a rampa, e não com o teto de campo.
        assert v.max() > FIELD_PEAK_CEILING_PU * 3396.6

    def test_o_freio_de_didt_nunca_engata_na_escalada(self):
        """O ``di/dt`` no zero fica muito abaixo da capacidade sorteada.

        É por isso que o polo interrompe todas as vezes e a sequência não
        termina: o mecanismo publicado — o arco persistir quando o
        ``di/dt`` excede a capacidade — exige o caminho de alta frequência
        que o caso não representa.
        """
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase
        from app.simulation.emt.vcb_scenarios import VcbSample

        capacidade = 460.0
        amostras = tuple(
            VcbSample("literatura", 2.71, capacidade, 44.3, 0.0, 14.6865e-3, None)
            for _ in range(3)
        )
        modelo = AtpReferenceCase(with_snubber=False, vcb_samples=amostras).build()
        modelo.run()
        polo = modelo.poles[0]
        assert polo.result.reignition_count > 10
        assert polo.last_didt_A_per_us < 0.5 * capacidade
