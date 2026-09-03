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
    MEASURED_SCENARIO,
    SCENARIOS,
    VcbParameterRanges,
    sample_vcb_parameters,
    scenario,
    sweep_samples,
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
