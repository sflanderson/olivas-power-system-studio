"""
app.postprocessor.prognosis.damage_models — modelos de dano de isolamento
(D1–D7) e acumulador combinado (5.1)–(5.2).

Escopo
======

Funções puras de vida/dano de isolamento de estator de motor de indução
de média tensão, mais o acumulador combinado térmico + elétrico + sinergia.
Nenhum I/O, nenhum estado global, nenhuma dependência de GUI.

Equações implementadas (nomenclatura do estudo de RUL, Etapa 1 §5.4)
=====================================================================

* **D1 — Lei de potência inversa (IPL)**: ``L(V) = k V^-n``
  [LITERATURA: Feilat, IntechOpen 2018, eq. (21), DOI 10.5772/intechopen.72423;
  CIGRE WG D1.43, TB 703, p. 29, Fig. 31].
  Expoentes medidos (fio esmaltado / epóxi): ``n`` de **3,8 a 11,7**
  [LITERATURA: CIGRE TB 703, Figs. 24 e 33]. **Nenhum valor de n para
  mica-epóxi pré-formada de MT sob impulsos de VCB foi localizado**
  [INSERIR CITAÇÃO].
* **D2 — IPL com limiar**: ``L = C (E - E_0)^-m``, vida infinita abaixo
  do limiar [LITERATURA: Tommasini, CERN, arXiv:1104.0802;
  Choudhary et al., Energies 15:3408, 2022, eqs. (1), (4)]. Suporte
  empírico da existência de limiar: 1 000–8 000 surtos de 3,0–7,8 pu sem
  degradação mensurável em 2 de 3 estatores [LITERATURA: Gupta, Lloyd e
  Sharma, IEEE TEC 5(2):320-326, 1990]. Limiares físicos normativos
  correspondentes: PDIV/RPDIV [NORMA: IEC 60034-18-41:2014, 3.2, 3.9].
* **D3 — Correção de tempo de frente**: ``L ∝ (dv/dt)^-n'``, aqui na
  forma ``N ∝ (t_f / t_f0)^m`` [LITERATURA: Yang et al., High Voltage,
  2023, DOI 10.1049/hve2.12375].
* **D4 — Regra de Miner**: ``D = Σ_i n_i / N_i``, falha em ``D = 1``
  [LITERATURA: ReliaSoft HotWire 116; Theofanous et al., Energies
  18:6087, 2025, eqs. (17)-(19), (25)].
* **D5 — Multi-estresse de Simoni**:
  ``L(V,T) = t_0 (V/V_0)^-n exp(-B c_T)``, com **``c_T = 1/T_0 - 1/T``**
  [LITERATURA: Feilat 2018, eq. (26)]. **Convenção de sinal corrigida**
  (Etapa 1 §5.4, D5, nota de sinal): Feilat imprime ``1/T - 1/T_0``, o
  que faria a vida CRESCER com a temperatura.
* **D6 — Parcela térmica (Arrhenius-Dakin e Montsinger)**:
  ``L(θ) = L_0 exp[-B (1/θ_0 - 1/θ)]`` e ``L(θ) = L_0 2^((θ_0-θ)/HIC)``,
  com ``HIC`` de **8 a 15 °C** [LITERATURA: Theofanous et al., Energies
  18:6087, 2025, eqs. (5), (9)-(10), p. 11]. A NEMA adota k = 10 °C
  [NORMA: NEMA MG 1, Parte 31, 31.4.1.2].
* **D7 — Acumulador por evento**:

  ``N_j = N_0 [(a V_pk,j - V_th)/(V_ref - V_th)]^-n (t_f,j/t_f0)^m
  2^((θ_0-θ_j)/HIC)`` , com ``1/N_j = 0`` sempre que
  ``a V_pk,j <= V_th``.

  **Convenção de sinal do fator térmico** (Etapa 2 §3.1 e §5.1, correção
  aplicada em todo o estudo): o fator ``2^((θ_0-θ_j)/HIC)`` multiplica
  ``N_j``; equivalentemente ``1/N_j ∝ 2^((θ_j-θ_0)/HIC)`` — isto é,
  **o fator térmico multiplica o DANO**, e com HIC = 10 K uma
  sobretemperatura de +20 K multiplica a taxa de dano por 2^2 = 4,0.
  A forma impressa na Etapa 1 (``2^((θ_j-θ_0)/HIC)`` multiplicando
  ``N_j``) é inconsistente com D6 e **não** é a implementada.

* **(5.1)-(5.2) — acumulador combinado** (Etapa 2 §5.2):

  ``D(t) = D_th(t) + D_el(t) + D_sin(t)``, com
  ``D_th = ∫ dτ / L(θ(τ))`` e ``D_el = Σ_m Σ_j 1/N_j(U_w(θ,D))``.

  ``D_sin := D_exato - (D_th + D_el)`` (eq. 5.3) **não tem parâmetros
  medidos publicados** para mica-epóxi de MT; o padrão do módulo é
  ``D_sin = 0``, e nesse caso ``D`` é declarado **cota inferior de dano
  (cota superior de RUL)** — nunca estimativa central.

Estado de calibração
=====================

**Todos** os parâmetros de :class:`DamageModelParams` são
[HIPÓTESE de modelagem — não calibrados] (Etapa 1 §5.4, D7). Os defaults
existem apenas para tornar o módulo executável e testável; cada um traz
comentário com a origem da ordem de grandeza ou a marcação explícita de
"NÃO CALIBRADO".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

from app.core.logging_config import get_logger
from app.postprocessor.prognosis.stress_profile import (
    ABSOLUTE_ZERO_C,
    StressEvent,
    StressProfile,
)

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Faixas de literatura (para validação e para o laudo)
# ---------------------------------------------------------------------------

#: Faixa de expoentes de tensão n medidos em fio esmaltado / epóxi
#: [LITERATURA: CIGRE WG D1.43, TB 703, Figs. 24 e 33].
IPL_EXPONENT_LITERATURE_RANGE: tuple[float, float] = (3.8, 11.7)

#: Faixa de HIC (halving interval of the temperature) em °C
#: [LITERATURA: Theofanous et al., Energies 18:6087, 2025, p. 11].
HIC_LITERATURE_RANGE_C: tuple[float, float] = (8.0, 15.0)

#: Limite superior de expoente aceito nos argumentos de exp()/2**, para
#: evitar overflow. Puramente numérico.
_MAX_EXPONENT: float = 700.0


def _saturate_exponent(expo: float, where: str) -> float:
    """Satura o expoente em +/- :data:`_MAX_EXPONENT` e LOGA o clamp.

    Convenção do repositório: "fallbacks aplicados, limitações tocadas"
    são registrados em nível WARNING [REPO: app/core/logging_config.py:33-37;
    checklist de convencoes_auditoria_gui_docs.md, item 4.1.6].
    """
    if expo > _MAX_EXPONENT or expo < -_MAX_EXPONENT:
        log.warning(
            "%s: expoente %.6g saturado em +/-%.0f para evitar overflow "
            "numerico; o resultado NAO e o do modelo analitico e nao deve "
            "ser citado como valor de projeto.",
            where,
            expo,
            _MAX_EXPONENT,
        )
        return max(-_MAX_EXPONENT, min(_MAX_EXPONENT, expo))
    return expo


def _kelvin(theta_C: float) -> float:
    if not math.isfinite(theta_C) or theta_C <= ABSOLUTE_ZERO_C:
        raise ValueError(
            f"temperatura deve ser > {ABSOLUTE_ZERO_C} °C (zero absoluto), "
            f"obtida {theta_C}"
        )
    return theta_C - ABSOLUTE_ZERO_C


# ---------------------------------------------------------------------------
# D1 — Lei de potência inversa
# ---------------------------------------------------------------------------


def inverse_power_law_life(V: float, k: float, n: float) -> float:
    """**D1** — Vida por lei de potência inversa: ``L(V) = k V^-n``.

    [LITERATURA: Feilat, IntechOpen 2018, eq. (21); CIGRE TB 703, p. 29,
    Fig. 31 — "As the applied surge voltage increases, the life decreases
    following an inverse power law"].

    Parameters
    ----------
    V:
        Tensão (ou campo) aplicada, > 0, em unidade coerente com ``k``.
    k:
        Constante do material, > 0. Fixa a unidade de ``L``.
    n:
        Expoente de resistência à tensão (VEC), >= 0. Faixa de literatura
        para dielétricos: 3,8 a 11,7 (:data:`IPL_EXPONENT_LITERATURE_RANGE`).

    Returns
    -------
    float
        Vida em horas ou em número de impulsos, conforme a unidade de ``k``.

    Raises
    ------
    ValueError
        ``V <= 0``, ``k <= 0`` ou ``n < 0``.
    """
    if not math.isfinite(V) or V <= 0.0:
        raise ValueError(f"V deve ser > 0, obtido {V}")
    if not math.isfinite(k) or k <= 0.0:
        raise ValueError(f"k deve ser > 0, obtido {k}")
    if not math.isfinite(n) or n < 0.0:
        raise ValueError(f"n deve ser >= 0, obtido {n}")
    return k * V ** (-n)


def ipl_with_threshold(V: float, V_th: float, C: float, m: float) -> float:
    """**D2** — IPL com limiar: ``L = C (V - V_th)^-m``.

    Abaixo ou no limiar a vida é **infinita** (dano nulo): é a forma que
    reconcilia CIGRE/Ghassemi com Gupta, Lloyd e Sharma (1990), em que
    1 000 a 8 000 surtos de 3,0 a 7,8 pu não produziram degradação
    mensurável em 2 de 3 estatores (Etapa 1 §5.6).

    [LITERATURA: Tommasini, CERN, arXiv:1104.0802; Choudhary et al.,
    Energies 15:3408, 2022, eqs. (1), (4)]. Contraparte normativa do
    limiar: PDIV/RPDIV [NORMA: IEC 60034-18-41:2014, 3.2, 3.9].

    Raises
    ------
    ValueError
        ``V <= 0``, ``V_th < 0``, ``C <= 0`` ou ``m < 0``.
    """
    if not math.isfinite(V) or V <= 0.0:
        raise ValueError(f"V deve ser > 0, obtido {V}")
    if not math.isfinite(V_th) or V_th < 0.0:
        raise ValueError(f"V_th deve ser >= 0, obtido {V_th}")
    if not math.isfinite(C) or C <= 0.0:
        raise ValueError(f"C deve ser > 0, obtido {C}")
    if not math.isfinite(m) or m < 0.0:
        raise ValueError(f"m deve ser >= 0, obtido {m}")
    if V <= V_th:
        return math.inf
    return C * (V - V_th) ** (-m)


def front_time_correction(t_f: float, t_f0: float, m: float) -> float:
    """**D3** — Fator de correção de frente: ``(t_f / t_f0)^m``.

    Multiplica ``N_j`` em D7. Com ``m > 0``, frentes mais curtas que a
    referência REDUZEM o número de eventos suportáveis (penalizam),
    coerente com ``L ∝ (dv/dt)^-n'`` [LITERATURA: Yang et al., High
    Voltage, 2023, DOI 10.1049/hve2.12375] e com o suporte qualitativo
    "the shorter the rise time, the larger the PD magnitudes; thus, the
    shorter lifetime" [LITERATURA: Ghassemi, IEEE TDEI 2019 /
    arXiv:2007.03194, p. 2].

    ``t_f0`` de referência natural: 1,2 µs da onda normalizada
    [NORMA: IEC 60034-15:2009, §4.2].

    Raises
    ------
    ValueError
        ``t_f <= 0``, ``t_f0 <= 0`` ou ``m < 0``.
    """
    if not math.isfinite(t_f) or t_f <= 0.0:
        raise ValueError(f"t_f deve ser > 0, obtido {t_f}")
    if not math.isfinite(t_f0) or t_f0 <= 0.0:
        raise ValueError(f"t_f0 deve ser > 0, obtido {t_f0}")
    if not math.isfinite(m) or m < 0.0:
        raise ValueError(f"m deve ser >= 0, obtido {m}")
    return (t_f / t_f0) ** m


def miner_damage(events: Iterable[Sequence[float]]) -> float:
    """**D4** — Regra de Miner: ``D = Σ_i n_i / N_i``; falha em ``D = 1``.

    [LITERATURA: ReliaSoft HotWire 116; Theofanous et al., Energies
    18:6087, 2025, eqs. (17)-(19), (25)].

    Parameters
    ----------
    events:
        Iterável de pares ``(n_i, N_i)``: número de eventos aplicados no
        nível de estresse ``i`` e número suportável nesse nível.
        ``N_i = inf`` (nível abaixo do limiar) contribui com dano nulo.

    Limitações declaradas [LITERATURA: ReliaSoft]: usa apenas valores
    esperados, assume relação linear vida-estresse e **independência da
    ordem de aplicação**.

    Raises
    ------
    ValueError
        Par malformado, ``n_i < 0`` ou ``N_i <= 0``.
    """
    total = 0.0
    for idx, pair in enumerate(events):
        seq = tuple(pair)
        if len(seq) != 2:
            raise ValueError(
                f"events[{idx}] deve ser um par (n_i, N_i), obtido {seq!r}"
            )
        n_i, N_i = float(seq[0]), float(seq[1])
        if not math.isfinite(n_i) or n_i < 0.0:
            raise ValueError(f"n_i deve ser >= 0 em events[{idx}], obtido {n_i}")
        if N_i <= 0.0 or math.isnan(N_i):
            raise ValueError(f"N_i deve ser > 0 em events[{idx}], obtido {N_i}")
        if math.isinf(N_i):
            continue
        total += n_i / N_i
    return total


# ---------------------------------------------------------------------------
# D5 / D6 — parcela térmica e multi-estresse
# ---------------------------------------------------------------------------


def arrhenius_life(
    theta_C: float,
    *,
    L0_h: float,
    theta0_C: float,
    B_K: float,
) -> float:
    """**D6** — Arrhenius-Dakin: ``L(θ) = L_0 exp[-B (1/θ_0 - 1/θ)]``.

    Temperaturas convertidas para kelvin internamente. Com ``θ > θ_0`` e
    ``B > 0`` a vida DECRESCE, como exige a física.

    [LITERATURA: Theofanous et al., Energies 18:6087, 2025, eqs. (5),
    (9)-(10)]. ``B = E_a / k_B`` [K]; energias de ativação típicas:
    epóxi 110-170 kJ/mol, poliimida 180-240 kJ/mol [idem, Tabela 1].

    Raises
    ------
    ValueError
        Temperatura <= zero absoluto, ``L0_h <= 0`` ou ``B_K < 0``.
    """
    if not math.isfinite(L0_h) or L0_h <= 0.0:
        raise ValueError(f"L0_h deve ser > 0 [h], obtido {L0_h}")
    if not math.isfinite(B_K) or B_K < 0.0:
        raise ValueError(f"B_K deve ser >= 0 [K], obtido {B_K}")
    T = _kelvin(theta_C)
    T0 = _kelvin(theta0_C)
    c_T = 1.0 / T0 - 1.0 / T  # convenção de sinal da Etapa 1 §5.4, D5
    expo = _saturate_exponent(-B_K * c_T, "arrhenius_life (D6)")
    return L0_h * math.exp(expo)


def montsinger_life(
    theta_C: float,
    *,
    L0_h: float,
    theta0_C: float,
    HIC: float,
) -> float:
    """**D6** — Montsinger: ``L(θ) = L_0 2^((θ_0 - θ)/HIC)``.

    ``HIC`` (*halving interval of the temperature*) na faixa **8 a 15 °C**
    [LITERATURA: Theofanous et al., Energies 18:6087, 2025, eqs. (9)-(10),
    p. 11]; a NEMA adota k = 10 °C para expectativa de vida térmica
    relativa [NORMA: NEMA MG 1, Parte 31, 31.4.1.2].

    Raises
    ------
    ValueError
        Temperatura <= zero absoluto, ``L0_h <= 0`` ou ``HIC <= 0``.
    """
    if not math.isfinite(L0_h) or L0_h <= 0.0:
        raise ValueError(f"L0_h deve ser > 0 [h], obtido {L0_h}")
    if not math.isfinite(HIC) or HIC <= 0.0:
        raise ValueError(f"HIC deve ser > 0 [°C], obtido {HIC}")
    _kelvin(theta_C)
    _kelvin(theta0_C)
    expo = _saturate_exponent((theta0_C - theta_C) / HIC, "montsinger_life (D6)")
    return L0_h * (2.0 ** expo)


def simoni_life(
    V: float,
    theta_C: float,
    *,
    t0_h: float,
    V0: float,
    n: float,
    B_K: float,
    theta0_C: float,
) -> float:
    """**D5** — Simoni: ``L(V,T) = t_0 (V/V_0)^-n exp(-B c_T)``.

    com ``c_T = 1/T_0 - 1/T`` — **convenção de sinal corrigida**
    (Etapa 1 §5.4, D5, nota de sinal): a forma impressa por Feilat,
    ``Δ(1/T) = 1/T - 1/T_0``, faria a vida crescer com a temperatura.

    [LITERATURA: Feilat, IntechOpen 2018, eq. (26); INSERIR CITAÇÃO
    primária: Simoni 1981/1984; Montanari, Mazzanti e Simoni, IEEE TDEI
    9:730-745, 2002].

    Raises
    ------
    ValueError
        ``V <= 0``, ``V0 <= 0``, ``t0_h <= 0``, ``n < 0``, ``B_K < 0`` ou
        temperatura <= zero absoluto.
    """
    if not math.isfinite(V) or V <= 0.0:
        raise ValueError(f"V deve ser > 0, obtido {V}")
    if not math.isfinite(V0) or V0 <= 0.0:
        raise ValueError(f"V0 deve ser > 0, obtido {V0}")
    if not math.isfinite(t0_h) or t0_h <= 0.0:
        raise ValueError(f"t0_h deve ser > 0 [h], obtido {t0_h}")
    if not math.isfinite(n) or n < 0.0:
        raise ValueError(f"n deve ser >= 0, obtido {n}")
    if not math.isfinite(B_K) or B_K < 0.0:
        raise ValueError(f"B_K deve ser >= 0 [K], obtido {B_K}")
    T = _kelvin(theta_C)
    T0 = _kelvin(theta0_C)
    c_T = 1.0 / T0 - 1.0 / T
    expo = _saturate_exponent(-B_K * c_T, "simoni_life (D5)")
    return t0_h * (V / V0) ** (-n) * math.exp(expo)


# ---------------------------------------------------------------------------
# Parâmetros do modelo (todos NÃO CALIBRADOS)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DamageModelParams:
    """Parâmetros de D7 e do acumulador (5.1)-(5.2).

    **TODOS os defaults são [HIPÓTESE de modelagem — NÃO CALIBRADOS]**
    (Etapa 1 §5.4, D7). Existem para tornar o módulo executável; nenhum
    resultado numérico obtido com eles deve ser citado como valor fechado.
    """

    # Expoente de tensão (VEC) de D1. Default = 6,4 (50 Hz senoidal em ar,
    # fio esmaltado) [LITERATURA: CIGRE TB 703, Fig. 24]. NÃO CALIBRADO
    # para mica-epóxi pré-formada de MT [INSERIR CITAÇÃO].
    n_voltage: float = 6.4

    # Expoente de correção de frente de D3. Default 0,0 = correção
    # DESLIGADA (hipótese H3 da Etapa 1 §5.5, que isola o efeito de n).
    # NÃO CALIBRADO.
    m_front: float = 0.0

    # Limiar de dano V_th [kV] de D2/D7. Default 0,0 = SEM limiar
    # (hipótese H3, Etapa 1 §5.5). Um modelo sem limiar produz RUL
    # sistematicamente PESSIMISTA (Etapa 1 §5.6). NÃO CALIBRADO.
    V_th_kV: float = 0.0

    # Par de referência (V_ref, N_0) da curva de vida.
    # V_ref = 7,8 pu × 3,397 kV = 26,50 kV e N_0 = 1e4 eventos ancoram a
    # ORDEM DE GRANDEZA de Gupta, Lloyd e Sharma (1990): 1 000-8 000
    # surtos de 3,0-7,8 pu SEM degradação mensurável — referência
    # otimista, pois a fonte não observou falha [Etapa 1 §5.5, H2].
    V_ref_kV: float = 26.50
    N0_events: float = 1.0e4

    # Tempo de frente de referência [µs]: onda normalizada 1,2/50 µs
    # [NORMA: IEC 60034-15:2009, §4.2].
    t_f0_us: float = 1.2

    # HIC [°C] de D6/D7. Default 10,0 = valor central da faixa 8-15 °C
    # [LITERATURA: Theofanous et al., Energies 18:6087, 2025, p. 11] e
    # igual ao k = 10 °C da NEMA MG 1, Parte 31, 31.4.1.2.
    HIC_C: float = 10.0

    # Temperatura de referência θ_0 [°C] de D6/D7. Default 40,0 °C =
    # temperatura de referência de ensaio de IR [NORMA: ABNT NBR
    # 17094-3:2018, 6.8.2]. NÃO CALIBRADO como referência de vida.
    theta0_C: float = 40.0

    # Fração a(t_f) da tensão que recai sobre a primeira bobina.
    # Default 1,0 = hipótese H1 da Etapa 1 §5.5 (a se cancela na razão
    # V/V_ref). NÃO CALIBRADO — deve ser MEDIDO, não presumido
    # (Etapa 1 §5.5, contagem anual ilustrativa).
    a_first_coil: float = 1.0

    # Parcela térmica: vida de referência L_0 [h] e B [K] de Arrhenius.
    # L_0 = 175 200 h ≈ 20 anos é uma vida de projeto convencional
    # [HIPÓTESE — NÃO CALIBRADO]. B = 12 000 K corresponde a
    # E_a ≈ 99,8 kJ/mol, abaixo da faixa 110-170 kJ/mol de epóxi
    # [LITERATURA: Theofanous et al. 2025, Tab. 1] — NÃO CALIBRADO.
    L0_thermal_h: float = 175_200.0
    B_thermal_K: float = 12_000.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.n_voltage) or self.n_voltage < 0.0:
            raise ValueError(f"n_voltage deve ser >= 0, obtido {self.n_voltage}")
        if not math.isfinite(self.m_front) or self.m_front < 0.0:
            raise ValueError(f"m_front deve ser >= 0, obtido {self.m_front}")
        if not math.isfinite(self.V_th_kV) or self.V_th_kV < 0.0:
            raise ValueError(f"V_th_kV deve ser >= 0 [kV], obtido {self.V_th_kV}")
        if not math.isfinite(self.V_ref_kV) or self.V_ref_kV <= 0.0:
            raise ValueError(f"V_ref_kV deve ser > 0 [kV], obtido {self.V_ref_kV}")
        if self.V_ref_kV <= self.V_th_kV:
            raise ValueError(
                f"V_ref_kV ({self.V_ref_kV}) deve ser > V_th_kV ({self.V_th_kV}): "
                f"a normalização (V_ref - V_th) de D7 seria nula ou negativa"
            )
        if not math.isfinite(self.N0_events) or self.N0_events <= 0.0:
            raise ValueError(f"N0_events deve ser > 0, obtido {self.N0_events}")
        if not math.isfinite(self.t_f0_us) or self.t_f0_us <= 0.0:
            raise ValueError(f"t_f0_us deve ser > 0 [µs], obtido {self.t_f0_us}")
        if not math.isfinite(self.HIC_C) or self.HIC_C <= 0.0:
            raise ValueError(f"HIC_C deve ser > 0 [°C], obtido {self.HIC_C}")
        if not math.isfinite(self.theta0_C) or self.theta0_C <= ABSOLUTE_ZERO_C:
            raise ValueError(
                f"theta0_C deve ser > {ABSOLUTE_ZERO_C} °C, obtido {self.theta0_C}"
            )
        if not math.isfinite(self.a_first_coil) or self.a_first_coil <= 0.0:
            raise ValueError(
                f"a_first_coil deve ser > 0, obtido {self.a_first_coil}"
            )
        if not math.isfinite(self.L0_thermal_h) or self.L0_thermal_h <= 0.0:
            raise ValueError(
                f"L0_thermal_h deve ser > 0 [h], obtido {self.L0_thermal_h}"
            )
        if not math.isfinite(self.B_thermal_K) or self.B_thermal_K < 0.0:
            raise ValueError(
                f"B_thermal_K deve ser >= 0 [K], obtido {self.B_thermal_K}"
            )

    # -- auditoria ----------------------------------------------------------

    @property
    def n_within_literature_range(self) -> bool:
        """``n_voltage`` está na faixa 3,8-11,7 da literatura?"""
        lo, hi = IPL_EXPONENT_LITERATURE_RANGE
        return lo <= self.n_voltage <= hi

    @property
    def hic_within_literature_range(self) -> bool:
        """``HIC_C`` está na faixa 8-15 °C da literatura?"""
        lo, hi = HIC_LITERATURE_RANGE_C
        return lo <= self.HIC_C <= hi

    def calibration_warnings(self) -> list[str]:
        """Avisos obrigatórios de calibração para o laudo."""
        msgs = [
            "Parâmetros de D7 e do acumulador (5.1)-(5.2) NÃO CALIBRADOS "
            "para mica-epóxi pré-formada de MT: nenhum valor de n sob "
            "impulsos de VCB foi localizado na literatura acessada "
            "[Etapa 1 §5.4, D1; INSERIR CITAÇÃO].",
        ]
        if not self.n_within_literature_range:
            lo, hi = IPL_EXPONENT_LITERATURE_RANGE
            msgs.append(
                f"n_voltage = {self.n_voltage} está FORA da faixa de "
                f"literatura {lo}-{hi} [CIGRE TB 703, Figs. 24 e 33]."
            )
        if not self.hic_within_literature_range:
            lo, hi = HIC_LITERATURE_RANGE_C
            msgs.append(
                f"HIC_C = {self.HIC_C} °C está FORA da faixa de literatura "
                f"{lo}-{hi} °C [Theofanous et al., Energies 2025, p. 11]."
            )
        if self.V_th_kV == 0.0:
            msgs.append(
                "V_th_kV = 0 (sem limiar): o modelo produz RUL "
                "sistematicamente PESSIMISTA para manobras rotineiras "
                "[Etapa 1 §5.6]."
            )
        if self.m_front == 0.0:
            msgs.append(
                "m_front = 0 (correção de frente desligada): a severidade "
                "de frentes curtas NÃO é penalizada [Etapa 1 §5.4, D3]."
            )
        return msgs


# ---------------------------------------------------------------------------
# D7 — número suportável e dano por evento
# ---------------------------------------------------------------------------

#: Normalização do estresse em D7.
#: ``"threshold_shift"`` — forma impressa de D7: ``(aV - V_th)/(V_ref - V_th)``.
#: ``"residual_withstand"`` — forma preferida da Etapa 2 §5.2 (saída ii):
#: normaliza pela suportabilidade residual ``U_w(θ,D)``, tornando
#: ``∂F/∂D > 0`` ESTRUTURAL e evitando a monotonicidade perversa
#: demonstrada em Etapa 2 §5.2 para eventos com ``aV_pk > V_ref``.
NORMALIZATION_MODES: tuple[str, ...] = ("threshold_shift", "residual_withstand")


def supportable_events(
    event: StressEvent,
    params: DamageModelParams,
    *,
    U_w_kV: float | None = None,
    U_w0_kV: float | None = None,
    V_th_kV: float | None = None,
    normalization: str = "threshold_shift",
) -> float:
    """**D7** — número de eventos suportáveis ``N_j`` no nível do evento.

    ``N_j = N_0 [(a V_pk - V_th)/(V_ref - V_th)]^-n (t_f/t_f0)^m
    2^((θ_0 - θ_j)/HIC)``

    **Convenção de sinal térmico** (Etapa 2 §3.1): o fator
    ``2^((θ_0-θ_j)/HIC)`` multiplica ``N_j``, logo ``1/N_j`` cresce com a
    temperatura — o fator térmico multiplica o DANO.

    Retorna ``math.inf`` quando ``a V_pk <= V_th`` (dano nulo, D2).

    Parameters
    ----------
    event:
        Evento de estresse (fornece ``V_pk``, ``T1`` e ``θ_j``). O tempo
        de frente usado é ``T1_us`` (normativo), não ``V_pk/RRRV``.
    params:
        Parâmetros do modelo.
    U_w_kV, U_w0_kV:
        Suportabilidade residual e inicial [kV]. Obrigatórios no modo
        ``"residual_withstand"``; ignorados no modo ``"threshold_shift"``.
    V_th_kV:
        Limiar efetivo [kV]; ``None`` usa ``params.V_th_kV``. Permite ao
        acumulador aplicar ``V_th(U_w(θ,D))`` (Etapa 2 §5.1).
    normalization:
        Um de :data:`NORMALIZATION_MODES`.

    Raises
    ------
    ValueError
        ``normalization`` desconhecida; ``U_w`` ausente ou não positivo no
        modo ``residual_withstand``; ``V_th_kV`` >= ``V_ref_kV``.
    """
    if normalization not in NORMALIZATION_MODES:
        raise ValueError(
            f"normalization deve ser um de {NORMALIZATION_MODES}, "
            f"obtido {normalization!r}"
        )
    v_th = params.V_th_kV if V_th_kV is None else float(V_th_kV)
    if not math.isfinite(v_th) or v_th < 0.0:
        raise ValueError(f"V_th_kV deve ser >= 0 [kV], obtido {v_th}")

    stress_kV = params.a_first_coil * event.abs_V_pk_kV
    if stress_kV <= v_th:
        return math.inf  # 1/N_j = 0 (D2 / eq. 5.2)

    if normalization == "threshold_shift":
        if v_th >= params.V_ref_kV:
            raise ValueError(
                f"V_th_kV ({v_th}) deve ser < V_ref_kV ({params.V_ref_kV}) "
                f"no modo 'threshold_shift'"
            )
        ratio = (stress_kV - v_th) / (params.V_ref_kV - v_th)
    else:  # residual_withstand
        if U_w_kV is None or U_w0_kV is None:
            raise ValueError(
                "U_w_kV e U_w0_kV são obrigatórios no modo 'residual_withstand'"
            )
        if not math.isfinite(U_w_kV) or U_w_kV <= 0.0:
            raise ValueError(f"U_w_kV deve ser > 0 [kV], obtido {U_w_kV}")
        if not math.isfinite(U_w0_kV) or U_w0_kV <= 0.0:
            raise ValueError(f"U_w0_kV deve ser > 0 [kV], obtido {U_w0_kV}")
        # Normalizado de modo que (V = V_ref, U_w = U_w0) ⇒ ratio = 1.
        ratio = (stress_kV / U_w_kV) / (params.V_ref_kV / U_w0_kV)

    if ratio <= 0.0:
        return math.inf

    front = front_time_correction(event.T1_us, params.t_f0_us, params.m_front)
    thermal_expo = _saturate_exponent(
        (params.theta0_C - event.theta_C) / params.HIC_C,
        "supportable_events (D7, fator termico)",
    )
    thermal = 2.0 ** thermal_expo

    return params.N0_events * ratio ** (-params.n_voltage) * front * thermal


def event_damage(
    event: StressEvent,
    params: DamageModelParams,
    *,
    U_w_kV: float | None = None,
    U_w0_kV: float | None = None,
    V_th_kV: float | None = None,
    normalization: str = "threshold_shift",
) -> float:
    """``1/N_j`` — dano incremental de uma reignição (eq. 5.2).

    Vale exatamente 0,0 quando ``a V_pk <= V_th``.

    Saturação declarada [CÁLCULO PRÓPRIO — proteção numérica]: quando o
    produto ``ratio^-n · (t_f/t_f0)^m · 2^((θ_0-θ_j)/HIC)`` sofre
    *underflow* para 0,0 em ponto flutuante (estresse muitas ordens de
    grandeza acima da referência, ou θ_j muito acima de θ_0), ``N_j`` é
    0,0 e ``1/N_j`` não é representável. O incremento é então saturado em
    **1,0**, que é a falha convencionada ``D = 1`` da regra de Miner
    (Etapa 1 §5.4, D4) — um único evento consome todo o orçamento de
    vida. O clamp é registrado em WARNING; o valor NÃO é resultado do
    modelo analítico e não deve ser citado como número de projeto.
    """
    N_j = supportable_events(
        event,
        params,
        U_w_kV=U_w_kV,
        U_w0_kV=U_w0_kV,
        V_th_kV=V_th_kV,
        normalization=normalization,
    )
    if math.isinf(N_j):
        return 0.0
    if N_j <= 0.0:
        log.warning(
            "event_damage (D7): N_j sofreu underflow para %.6g com "
            "V_pk = %.6g kV, T1 = %.6g us e theta = %.6g C; incremento "
            "saturado em 1,0 (falha convencionada D = 1, D4). Reveja n, "
            "V_ref e HIC: o evento esta fora da faixa numerica do modelo.",
            N_j,
            event.abs_V_pk_kV,
            event.T1_us,
            event.theta_C,
        )
        return 1.0
    return 1.0 / N_j


# ---------------------------------------------------------------------------
# ψ(D) — suportabilidade residual
# ---------------------------------------------------------------------------


def psi_linear(D: float, *, psi_min: float = 0.5) -> float:
    """``ψ(D) = 1 - (1 - ψ_min) D`` — degradação linear da suportabilidade.

    Etapa 1 §6: ``U_w(t) = U_w0 ψ(D(t))``, com ``ψ(0) = 1`` e ``ψ' < 0``.
    A forma linear é **[HIPÓTESE]**: nenhuma fonte primária acessada
    fornece parâmetros medidos para ``ψ(·)`` em mica-epóxi de MT
    [Etapa 2 §5.2, "Ausência de parâmetros"; INSERIR CITAÇÃO].

    ``psi_min = 0,5`` é ancorado, em ORDEM DE GRANDEZA, na prática de
    reduzir o nível de ensaio a 75 % em máquinas em serviço
    [LITERATURA secundária: citando IEEE 522-2023 — HIPÓTESE a verificar
    no texto primário] e no nível de rotina de 40-80 % de U'_P para
    bobinas inseridas [NORMA: IEC 60034-15:2009, 5.1]. NÃO CALIBRADO.

    Raises
    ------
    ValueError
        ``D < 0`` ou ``psi_min`` fora de (0, 1].
    """
    if not math.isfinite(D) or D < 0.0:
        raise ValueError(f"D deve ser >= 0, obtido {D}")
    if not math.isfinite(psi_min) or not (0.0 < psi_min <= 1.0):
        raise ValueError(f"psi_min deve estar em (0, 1], obtido {psi_min}")
    if D > 1.0:
        log.warning(
            "psi_linear: D = %.6g > 1 (falha ja atingida, D4); psi saturado "
            "no valor de D = 1 (%.6g). A extrapolacao de suportabilidade "
            "residual alem da falha convencionada nao esta definida.",
            D,
            psi_min,
        )
    d = min(1.0, D)
    return 1.0 - (1.0 - psi_min) * d


# ---------------------------------------------------------------------------
# Acumulador combinado (5.1)-(5.2)
# ---------------------------------------------------------------------------


@dataclass
class ThermalInterval:
    """Trecho de trajetória térmica ``(θ, Δt)`` para ``D_th = ∫ dτ/L(θ)``."""

    theta_C: float
    duration_h: float
    label: str = ""

    def __post_init__(self) -> None:
        if not math.isfinite(self.theta_C) or self.theta_C <= ABSOLUTE_ZERO_C:
            raise ValueError(
                f"theta_C deve ser > {ABSOLUTE_ZERO_C} °C, obtido {self.theta_C}"
            )
        if not math.isfinite(self.duration_h) or self.duration_h < 0.0:
            raise ValueError(
                f"duration_h deve ser >= 0 [h], obtido {self.duration_h}"
            )


@dataclass
class CombinedDamageAccumulator:
    """Acumulador combinado ``D = D_th + D_el + D_sin`` (Etapa 2, eq. 5.1).

    Implementa (5.1)-(5.2) com limiar (D2), correção de frente (D3) e
    acoplamento térmico (D6/D7 com a convenção de sinal corrigida).

    Declaração obrigatória de leitura (Etapa 2 §5.2)
    -------------------------------------------------

    Com ``synergy_fn = None`` (padrão), ``D_sin = 0`` e o resultado é
    **cota inferior de dano — portanto cota superior de RUL**, sob a
    premissa de monotonicidade ``∂F/∂D > 0``. Essa premissa é
    ESTRUTURAL no modo ``normalization="residual_withstand"`` e
    CONDICIONAL (``a V_pk <= V_ref``, ou travessia de limiar) no modo
    ``"threshold_shift"`` — ver a monotonicidade perversa demonstrada em
    Etapa 2 §5.2.

    Parameters
    ----------
    params:
        Parâmetros de D7 (todos não calibrados).
    U_w0_kV, U_s_kV:
        Suportabilidade inicial e solicitação de projeto [kV], para a
        margem de coordenação ``γ = U_w/U_s`` (Etapa 1 §6). Opcionais.
    psi_min:
        Suportabilidade residual relativa em ``D = 1`` (ver
        :func:`psi_linear`).
    normalization:
        ``"threshold_shift"`` (D7 como impresso) ou
        ``"residual_withstand"`` (forma preferida, Etapa 2 §5.2).
    state_dependent_threshold:
        Se ``True``, o limiar acompanha a suportabilidade residual,
        ``V_th(D) = V_th0 ψ(D)`` (Etapa 2 §5.1: o envelhecimento térmico
        move o evento de volta para cima do limiar). [HIPÓTESE].
    synergy_fn:
        Função ``(D_th, D_el) -> D_sin``. ``None`` ⇒ ``D_sin = 0``.
    thermal_model:
        ``"montsinger"`` (padrão, D6 com HIC) ou ``"arrhenius"`` (D6 com B).
    """

    params: DamageModelParams = field(default_factory=DamageModelParams)
    U_w0_kV: float | None = None
    U_s_kV: float | None = None
    psi_min: float = 0.5
    normalization: str = "threshold_shift"
    state_dependent_threshold: bool = False
    synergy_fn: Callable[[float, float], float] | None = None
    thermal_model: str = "montsinger"

    _D_el: float = field(default=0.0, init=False, repr=False)
    _D_th: float = field(default=0.0, init=False, repr=False)
    _n_events: int = field(default=0, init=False, repr=False)
    _n_operations: int = field(default=0, init=False, repr=False)
    _n_below_threshold: int = field(default=0, init=False, repr=False)
    _hours: float = field(default=0.0, init=False, repr=False)

    _THERMAL_MODELS = ("montsinger", "arrhenius")

    def __post_init__(self) -> None:
        if not isinstance(self.params, DamageModelParams):
            raise ValueError(
                f"params deve ser DamageModelParams, obtido "
                f"{type(self.params).__name__}"
            )
        if self.normalization not in NORMALIZATION_MODES:
            raise ValueError(
                f"normalization deve ser um de {NORMALIZATION_MODES}, "
                f"obtido {self.normalization!r}"
            )
        if self.thermal_model not in self._THERMAL_MODELS:
            raise ValueError(
                f"thermal_model deve ser um de {self._THERMAL_MODELS}, "
                f"obtido {self.thermal_model!r}"
            )
        if not math.isfinite(self.psi_min) or not (0.0 < self.psi_min <= 1.0):
            raise ValueError(
                f"psi_min deve estar em (0, 1], obtido {self.psi_min}"
            )
        if self.normalization == "residual_withstand" and self.U_w0_kV is None:
            raise ValueError(
                "U_w0_kV é obrigatório quando normalization='residual_withstand'"
            )
        for name in ("U_w0_kV", "U_s_kV"):
            val = getattr(self, name)
            if val is not None and (not math.isfinite(val) or val <= 0.0):
                raise ValueError(f"{name} deve ser > 0 [kV] ou None, obtido {val}")

    # -- estado -------------------------------------------------------------

    @property
    def D_el(self) -> float:
        """Dano elétrico acumulado (Σ_m Σ_j 1/N_j)."""
        return self._D_el

    @property
    def D_th(self) -> float:
        """Dano térmico acumulado (∫ dτ/L(θ))."""
        return self._D_th

    @property
    def D_sin(self) -> float:
        """Termo de sinergia (eq. 5.3). 0,0 quando ``synergy_fn`` é None."""
        if self.synergy_fn is None:
            return 0.0
        value = float(self.synergy_fn(self._D_th, self._D_el))
        if not math.isfinite(value):
            raise ValueError(f"synergy_fn retornou valor não finito: {value}")
        return value

    @property
    def D_total(self) -> float:
        """``D = D_th + D_el + D_sin`` (eq. 5.1). Falha convencionada em D = 1."""
        return self._D_th + self._D_el + self.D_sin

    @property
    def remaining_fraction(self) -> float:
        """``1 - D``, saturado em 0 (fração de vida remanescente)."""
        return max(0.0, 1.0 - self.D_total)

    @property
    def is_lower_bound(self) -> bool:
        """True quando ``D_sin`` não é modelado: D é cota INFERIOR de dano."""
        return self.synergy_fn is None

    @property
    def n_events(self) -> int:
        """Número de reignições contabilizadas."""
        return self._n_events

    @property
    def n_operations(self) -> int:
        """Número de manobras contabilizadas via :meth:`add_profile`."""
        return self._n_operations

    @property
    def n_events_below_threshold(self) -> int:
        """Reignições que não causaram dano por estarem abaixo de V_th."""
        return self._n_below_threshold

    @property
    def thermal_hours(self) -> float:
        """Horas de trajetória térmica contabilizadas."""
        return self._hours

    # -- suportabilidade residual e margem ----------------------------------

    def psi(self) -> float:
        """``ψ(D)`` no estado corrente."""
        return psi_linear(self.D_total, psi_min=self.psi_min)

    def U_w_kV(self) -> float:
        """``U_w(t) = U_w0 ψ(D)`` [kV] (Etapa 1 §6).

        Raises
        ------
        ValueError
            Quando ``U_w0_kV`` não foi informado.
        """
        if self.U_w0_kV is None:
            raise ValueError(
                "U_w0_kV não informado: a suportabilidade residual U_w(t) "
                "não pode ser calculada"
            )
        return self.U_w0_kV * self.psi()

    def gamma(self) -> float:
        """Margem de coordenação ``γ(t) = U_w(t)/U_s`` (Etapa 1 §6).

        Critério de fim de vida por coordenação: ``γ → 1``. O BIL entra
        em ``U_w0`` como CONDIÇÃO INICIAL; ele não é a variável de estado
        (correção conceitual da Etapa 1 §6).

        Raises
        ------
        ValueError
            Quando ``U_w0_kV`` ou ``U_s_kV`` não foram informados.
        """
        if self.U_s_kV is None:
            raise ValueError(
                "U_s_kV não informado: a margem γ = U_w/U_s não pode ser "
                "calculada"
            )
        return self.U_w_kV() / self.U_s_kV

    def _effective_threshold_kV(self) -> float:
        if not self.state_dependent_threshold:
            return self.params.V_th_kV
        return self.params.V_th_kV * self.psi()

    # -- acumulação ---------------------------------------------------------

    def add_event(self, event: StressEvent) -> float:
        """Acumula uma reignição; retorna o incremento ``1/N_j``.

        Raises
        ------
        ValueError
            ``event`` não é :class:`StressEvent`.
        """
        if not isinstance(event, StressEvent):
            raise ValueError(
                f"event deve ser StressEvent, obtido {type(event).__name__}"
            )
        u_w = self.U_w_kV() if self.U_w0_kV is not None else None
        increment = event_damage(
            event,
            self.params,
            U_w_kV=u_w,
            U_w0_kV=self.U_w0_kV,
            V_th_kV=self._effective_threshold_kV(),
            normalization=self.normalization,
        )
        self._D_el += increment
        self._n_events += 1
        if increment == 0.0:
            self._n_below_threshold += 1
        return increment

    def add_events(self, events: Iterable[StressEvent]) -> float:
        """Acumula uma sequência de reignições; retorna o incremento total."""
        return sum(self.add_event(ev) for ev in events)

    def add_profile(self, profile: StressProfile) -> float:
        """Acumula um :class:`StressProfile` inteiro (uma ou mais manobras).

        Raises
        ------
        ValueError
            ``profile`` não é :class:`StressProfile`.
        """
        if not isinstance(profile, StressProfile):
            raise ValueError(
                f"profile deve ser StressProfile, obtido {type(profile).__name__}"
            )
        total = self.add_events(profile.events)
        self._n_operations += profile.n_operations
        return total

    def thermal_life_h(self, theta_C: float) -> float:
        """``L(θ)`` [h] pelo modelo térmico configurado (D6)."""
        if self.thermal_model == "montsinger":
            return montsinger_life(
                theta_C,
                L0_h=self.params.L0_thermal_h,
                theta0_C=self.params.theta0_C,
                HIC=self.params.HIC_C,
            )
        return arrhenius_life(
            theta_C,
            L0_h=self.params.L0_thermal_h,
            theta0_C=self.params.theta0_C,
            B_K=self.params.B_thermal_K,
        )

    def add_thermal_interval(self, theta_C: float, duration_h: float) -> float:
        """Acumula ``Δt / L(θ)`` (forma contínua de Miner, D4/D6).

        Retorna o incremento de ``D_th``.

        Raises
        ------
        ValueError
            Temperatura <= zero absoluto ou ``duration_h < 0``.
        """
        interval = ThermalInterval(theta_C=theta_C, duration_h=duration_h)
        life = self.thermal_life_h(interval.theta_C)
        increment = interval.duration_h / life
        self._D_th += increment
        self._hours += interval.duration_h
        return increment

    def add_thermal_profile(self, intervals: Iterable[ThermalInterval]) -> float:
        """Acumula uma trajetória térmica discretizada."""
        total = 0.0
        for it in intervals:
            if not isinstance(it, ThermalInterval):
                raise ValueError(
                    f"intervals deve conter ThermalInterval, obtido "
                    f"{type(it).__name__}"
                )
            total += self.add_thermal_interval(it.theta_C, it.duration_h)
        return total

    # -- projeções ----------------------------------------------------------

    @property
    def mean_damage_per_event(self) -> float:
        """``E[1/N_j]`` observado — 0,0 se nenhum evento foi acumulado."""
        if self._n_events == 0:
            return 0.0
        return self._D_el / self._n_events

    @property
    def mean_damage_per_operation(self) -> float:
        """``E[ΔD_m]`` observado por manobra — requer :meth:`add_profile`."""
        if self._n_operations == 0:
            return 0.0
        return self._D_el / self._n_operations

    def rul_operations(self) -> float:
        """``RUL_N = (1 - D)/E[ΔD_m]`` — manobras restantes (D7).

        Retorna ``math.inf`` quando ``E[ΔD_m] = 0`` (todos os eventos
        abaixo do limiar de dano).

        Raises
        ------
        ValueError
            Nenhuma manobra acumulada via :meth:`add_profile`.
        """
        if self._n_operations == 0:
            raise ValueError(
                "nenhuma manobra acumulada: use add_profile() para contabilizar "
                "manobras antes de estimar RUL em manobras"
            )
        rate = self.mean_damage_per_operation
        if rate <= 0.0:
            return math.inf
        return self.remaining_fraction / rate

    def rul_years(self, operations_per_year: float) -> float:
        """``RUL_t = RUL_N / λ_m`` — anos restantes (D7).

        Parameters
        ----------
        operations_per_year:
            ``λ_m`` [manobras severas/ano], > 0.

        Raises
        ------
        ValueError
            ``operations_per_year <= 0`` ou nenhuma manobra acumulada.
        """
        if not math.isfinite(operations_per_year) or operations_per_year <= 0.0:
            raise ValueError(
                f"operations_per_year (λ_m) deve ser > 0, "
                f"obtido {operations_per_year}"
            )
        return self.rul_operations() / operations_per_year

    def summary(self) -> str:
        """Resumo textual determinístico para laudo/console."""
        lines = [
            "Acumulador combinado D = D_th + D_el + D_sin (Etapa 2, eq. 5.1)",
            f"  D_el (elétrico, D7) ............ {self._D_el:.6g}",
            f"  D_th (térmico, D6) ............. {self._D_th:.6g}",
            f"  D_sin (sinergia, eq. 5.3) ...... {self.D_sin:.6g}",
            f"  D total ........................ {self.D_total:.6g}",
            f"  Fração remanescente (1 - D) .... {self.remaining_fraction:.6g}",
            f"  Reignições contabilizadas ...... {self._n_events} "
            f"({self._n_below_threshold} abaixo de V_th)",
            f"  Manobras contabilizadas ........ {self._n_operations}",
            f"  Horas de trajetória térmica .... {self._hours:.6g}",
            f"  Normalização de D7 ............. {self.normalization}",
        ]
        if self.is_lower_bound:
            lines.append(
                "  ATENÇÃO: D_sin não modelado ⇒ D é COTA INFERIOR de dano "
                "(cota superior de RUL) [Etapa 2 §5.2]."
            )
        lines.extend(f"  • {w}" for w in self.params.calibration_warnings())
        return "\n".join(lines)
