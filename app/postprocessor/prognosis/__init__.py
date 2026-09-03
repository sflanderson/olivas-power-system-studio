"""
app.postprocessor.prognosis — núcleo computacional de prognóstico de
isolamento (RUL) de motores de indução de média tensão.

Escopo
======

Pacote **puro** (sem I/O, sem estado global, sem GUI) que converte
estresse dielétrico de manobra e trajetória térmica em dano acumulado,
vida útil remanescente (RUL) e índice de saúde do ativo (AHI), para
motores de indução de MT (2,3 a 13,8 kV) em plantas críticas.

Cadeia implementada::

    forma de onda ──▶ StressProfile (s_{m,j} = [V_pk, T1, dv/dt, E, n_r, θ])
                          │
                          ▼
                   CombinedDamageAccumulator   D = D_th + D_el + D_sin  (5.1)
                          │                    1/N_j por D7             (5.2)
                          ├──▶ rul_from_damage(D, dD/dt)   — determinístico
                          └──▶ AssetHealthIndex            — AHI 0-100

    série de indicador ──▶ EkfRulEstimator ──▶ RulPrediction (RUL + IC)

Módulos
========

* :mod:`~app.postprocessor.prognosis.stress_profile` — vetor de estresse
  por evento e extração a partir de forma de onda, com ``T1`` normativo
  [NORMA: IEC 60034-15:2009, §2.4].
* :mod:`~app.postprocessor.prognosis.damage_models` — D1 a D7 e o
  acumulador combinado (5.1)-(5.2).
* :mod:`~app.postprocessor.prognosis.rul_estimator` — EKF sobre tendência
  exponencial (padrão de Jensen, Strangas e Foster, 2018) e caminho
  determinístico.
* :mod:`~app.postprocessor.prognosis.health_index` — AHI 0-100 com
  decomposição explicável.

Cobertura normativa e de literatura citada no código
=====================================================

* **IEC 60034-15:2009** — §2.4 (``T1 = 1,67 (t90 - t30)``), §4.2 (onda
  1,2/50 µs e SFI 0,2 ± 0,1 µs), §5.1 (rotina 40-80 % de U'_P),
  §A.1 (frentes de serviço até 0,1 µs).
* **IEC 60034-18-41:2014** — 3.2 e 3.9 (PDIV/RPDIV como limiar físico);
  3.13 (``t_r = t90 - t10``, grandeza distinta de ``T1``).
* **IEC 60034-27-2:2023 / -27-3:2015 / -27-4:2018** — Introdução: as
  tendências de DP, tan δ e IR/PI **não** predizem tempo até a falha.
* **IEC 60071-1:2019** — 3.31 (fator de segurança ``K_s``) e 3.34
  (tensão suportável nominal como nível de ENSAIO, não propriedade que
  decai) — base da correção conceitual "BIL × suportabilidade residual".
* **ABNT NBR 17094-3:2018** — 6.8.2 Tab. 2 (IR mínimo) e 6.8.3 (PI).
* **NEMA MG 1, Parte 31, 31.4.1.2** — k = 10 °C para vida térmica
  relativa.
* **ISO 13381-1:2015** — 3.3 e 3.9: prognóstico com nível de confiança
  explícito.
* **CIGRE WG D1.43, TB 703** — expoentes ``n`` de 3,8 a 11,7; aquecimento
  dielétrico sob envelhecimento por pulsos.
* **Feilat, IntechOpen 2018** — eqs. (21), (26), (27), (29)
  (DOI 10.5772/intechopen.72423).
* **Theofanous et al., Energies 18:6087, 2025** — eqs. (5), (9)-(10),
  (17)-(19), (25); HIC 8-15 °C.
* **Jensen, Strangas e Foster, 2018** — eqs. (1)-(8) do EKF.
* **Gupta, Lloyd e Sharma, IEEE TEC 5(2):320-326, 1990** — evidência
  empírica de existência de limiar de dano.

Estado de maturidade
=====================

Este é o **núcleo computacional** (MVP). Ele NÃO está integrado à GUI,
não possui gate comercial próprio, não gera laudo HTML/PDF e não tem
strings de interface internacionalizadas — ver ``not done`` no handoff da
sessão. Todos os parâmetros dos modelos de dano são **não calibrados**
para mica-epóxi pré-formada de MT.
"""

from __future__ import annotations

from app.postprocessor.prognosis.damage_models import (
    HIC_LITERATURE_RANGE_C,
    IPL_EXPONENT_LITERATURE_RANGE,
    NORMALIZATION_MODES,
    CombinedDamageAccumulator,
    DamageModelParams,
    ThermalInterval,
    arrhenius_life,
    event_damage,
    front_time_correction,
    inverse_power_law_life,
    ipl_with_threshold,
    miner_damage,
    montsinger_life,
    psi_linear,
    simoni_life,
    supportable_events,
)
from app.postprocessor.prognosis.health_index import (
    DEFAULT_BANDS,
    AssetHealthIndex,
    HealthContribution,
    HealthIndexThresholds,
    HealthIndexWeights,
)
from app.postprocessor.prognosis.rul_estimator import (
    DEFAULT_CONFIDENCE,
    DEFAULT_P0_DIAG,
    DEFAULT_Q_DIAG,
    DEFAULT_R,
    EkfRulEstimator,
    RulPrediction,
    rul_from_damage,
)
from app.postprocessor.prognosis.stress_profile import (
    IEC_60034_15_T1_FACTOR,
    StressEvent,
    StressProfile,
    extract_stress_events,
)

__all__ = [
    # stress_profile
    "StressEvent",
    "StressProfile",
    "extract_stress_events",
    "IEC_60034_15_T1_FACTOR",
    # damage_models
    "DamageModelParams",
    "CombinedDamageAccumulator",
    "ThermalInterval",
    "inverse_power_law_life",
    "ipl_with_threshold",
    "front_time_correction",
    "miner_damage",
    "arrhenius_life",
    "montsinger_life",
    "simoni_life",
    "supportable_events",
    "event_damage",
    "psi_linear",
    "IPL_EXPONENT_LITERATURE_RANGE",
    "HIC_LITERATURE_RANGE_C",
    "NORMALIZATION_MODES",
    # rul_estimator
    "EkfRulEstimator",
    "RulPrediction",
    "rul_from_damage",
    "DEFAULT_Q_DIAG",
    "DEFAULT_R",
    "DEFAULT_P0_DIAG",
    "DEFAULT_CONFIDENCE",
    # health_index
    "AssetHealthIndex",
    "HealthIndexWeights",
    "HealthIndexThresholds",
    "HealthContribution",
    "DEFAULT_BANDS",
    # auditoria
    "KNOWN_LIMITATIONS",
]


# ---------------------------------------------------------------------------
# Limitações conhecidas do módulo — padrão do projeto
# (cf. app/postprocessor/audit_trail.py:338-382). Chaves com prefixo
# ``rul_`` para evitar colisão no catálogo global do laudo.
# ---------------------------------------------------------------------------

KNOWN_LIMITATIONS: dict[str, str] = {
    "rul_params_not_calibrated": (
        "TODOS os parâmetros dos modelos de dano (n, m, V_th, V_ref, N_0, "
        "HIC, B, L_0, a) são NÃO CALIBRADOS para mica-epóxi pré-formada de "
        "MT. Nenhum valor de n sob impulsos de VCB foi localizado na "
        "literatura acessada; os expoentes de 3,8 a 11,7 da CIGRE TB 703 "
        "provêm de fio esmaltado e epóxi puro. A vida em manobras varia por "
        "fator de 6,6 ao mover n de 4 para 9 — a incerteza do expoente "
        "DOMINA a estimativa de RUL."
    ),
    "rul_synergy_lower_bound": (
        "Com D_sin = 0 (padrão), o dano D = D_th + D_el é COTA INFERIOR de "
        "dano e, portanto, COTA SUPERIOR de RUL — nunca estimativa central. "
        "A premissa de monotonicidade ∂F/∂D > 0 é estrutural apenas na "
        "normalização 'residual_withstand'; na normalização 'threshold_shift' "
        "ela vale somente para eventos com a·V_pk ≤ V_ref ou na travessia do "
        "limiar."
    ),
    "rul_miner_linear_order_independent": (
        "A regra de Miner usa apenas valores esperados, assume relação "
        "linear vida-estresse e INDEPENDÊNCIA DA ORDEM de aplicação dos "
        "eventos. Sequências de estresse com a mesma composição produzem o "
        "mesmo dano, o que não se verifica em dielétricos com histórico de "
        "treeing."
    ),
    "rul_front_time_sampling": (
        "T1 = 1,67 (t90 − t30) é medido sobre a forma de onda fornecida. Com "
        "passo de amostragem da ordem do tempo de frente (o caso do passo de "
        "1 µs), a derivada numérica é calculada sobre 1 a 3 amostras e os "
        "valores de dv/dt reportados são LIMITES INFERIORES do real. A IEC "
        "60034-15:2009 §A.1 admite frentes de serviço de até 0,1 µs."
    ),
    "rul_measurement_point": (
        "A tensão de entrada é a do ponto de medição informado pelo chamador. "
        "TRV no disjuntor NÃO é a tensão nos terminais do motor: o módulo não "
        "modela reflexões no cabo nem a fração a(t_f) que recai sobre a "
        "primeira bobina, que é entrada do usuário e deve ser MEDIDA, não "
        "presumida."
    ),
    "rul_reignition_count_user_premise": (
        "O número de reignições por manobra é ENTRADA do usuário ou resultado "
        "da detecção de excursões na forma de onda fornecida; não é premissa "
        "do módulo. Sob lei de potência inversa com n ≥ 4 o dano é dominado "
        "pela maior reignição — a prioridade de instrumentação é medir bem o "
        "pico e a frente, não contar reignições."
    ),
    "rul_thermal_state_not_derived": (
        "A temperatura de ponto quente θ_j no instante de cada evento é "
        "ENTRADA do chamador: não é extraível da forma de onda de tensão nem "
        "derivada de fluxo de potência. Com HIC = 10 K, um erro de +20 K em "
        "θ_j multiplica a taxa de dano por 4,0."
    ),
    "rul_ekf_thermal_aging_only": (
        "O EKF reproduz a arquitetura de Jensen, Strangas e Foster (2018), "
        "validada com envelhecimento TÉRMICO em estatores de baixa tensão de "
        "5 kW (n = 3), monitorando fase-terra. A transferência para dano "
        "espira-a-espira por impulso em MT é hipótese de trabalho não "
        "validada."
    ),
    "rul_interval_delta_method": (
        "O intervalo de RUL é obtido por propagação de covariância (método "
        "delta, linearização de primeira ordem) sobre (α, β) do EKF. NÃO é "
        "intervalo de cobertura exata nem distribuição B10/B50 de Weibull por "
        "Monte Carlo, exigida por ISO 13381-1:2015, 3.3 e 3.9 para uma saída "
        "de prognóstico completa."
    ),
    "rul_ahi_bands_not_normative": (
        "As faixas de classificação do índice de saúde (85/70/50) e os pesos "
        "de composição são convenção do módulo, NÃO NORMATIVOS e "
        "configuráveis. Além disso, IR/PI, tan δ e DP têm sensibilidade "
        "nula/baixa ou indireta ao dano espira-a-espira, e as próprias normas "
        "declaram que suas tendências não predizem tempo até a falha "
        "(IEC 60034-27-2:2023, -27-3:2015 e -27-4:2018, Introdução)."
    ),
    "rul_numerical_saturation": (
        "Saturações numéricas declaradas, todas registradas em WARNING no "
        "log: (i) expoentes de exp()/2** são limitados a ±700, e o valor "
        "retornado deixa de ser o do modelo analítico; (ii) quando N_j "
        "sofre underflow para 0, o incremento de dano por evento é "
        "saturado em 1,0 — a falha convencionada D = 1 da regra de Miner "
        "(Etapa 1 §5.4, D4) —, o que significa apenas que o evento saiu "
        "da faixa numérica do modelo, não que a magnitude do dano foi "
        "calculada; (iii) ψ(D) é congelado em D = 1 para D > 1, pois a "
        "suportabilidade residual além da falha convencionada não está "
        "definida. Nenhum desses valores é resultado do modelo e nenhum "
        "deve ir a laudo como número de projeto."
    ),
    "rul_energy_surge_impedance_proxy": (
        "A energia por evento é aproximada por E = ∫ v²/Z dt com impedância "
        "de surto informada pelo usuário (faixa reportada para cabos de MT: "
        "≈ 30 a 80 Ω). Não é energia absorvida medida, nem energia dissipada "
        "no dielétrico."
    ),
}
