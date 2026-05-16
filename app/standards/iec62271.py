"""
app.standards.iec62271 — codificação dos requisitos TRT (Transient
Recovery Voltage) das normas IEC 62271-100/-200/-203 para
disjuntores de alta-tensão.

Fonte: IEC 62271-200 (LIBRARY/62271-200.pdf, retornando à 62271-100
para os parâmetros de envelope) — A.C. metal-enclosed switchgear
and controlgear for rated voltages above 1 kV and up to 52 kV.

Fundamentos
============

A TRT (Transient Recovery Voltage) é a tensão que aparece nos
terminais do disjuntor imediatamente após a interrupção da
corrente. Sua **forma de onda** define se o arco re-acende ou
o circuito é efetivamente aberto.

A IEC 62271-100 especifica **envelopes** de referência que a TRT
real do circuito **não pode** exceder em nenhum ponto durante o
período crítico (até alguns ms pós-corte):

* **Two-parameter envelope** (sistemas até ~100 kV ou Voc < 36 kV
  por T100): definida por ``u_c`` (tensão de pico) e ``t_3``
  (tempo até o pico).
* **Four-parameter envelope** (sistemas ≥ 100 kV ou test duties
  T30/T60/T100s): definida por ``u_1``, ``t_1``, ``u_c``, ``t_2``
  — composta por um trecho íngreme até (u_1, t_1) seguido de
  rampa mais suave até (u_c, t_2).

**RRRV** (Rate of Rise of Recovery Voltage) é a derivada inicial:

::

    RRRV (kV/μs) = u_1 / t_1   (4-parâmetro)
    RRRV         = u_c / t_3   (2-parâmetro)

**Parâmetros característicos** (IEC 62271-100, Table 14):

* ``kpp`` — first-pole-to-clear factor:
    - 1.3 para sistemas **efetivamente aterrados** (k_e/k_r ≥ 0.7
      e impedância zero-sequência não-resistiva).
    - 1.5 para sistemas **não-efetivamente aterrados** (incluindo
      isolados ou compensados).

* ``kaf`` — amplitude factor (relação u_c / u_pico_freq_industrial).
  Tabela típica:

    ====  ========  =======
    Duty  kaf       RRRV (kV/μs)
    ====  ========  =======
    T100  1.40      ~2.0
    T60   1.50      ~3.0
    T30   1.54      ~5.0
    T10   1.76      ~7.0
    ====  ========  =======

  (ATP/ATPDraw usa estes valores como default; valores exatos
  variam com Voc — consultar IEC 62271-100 Tables 14-19.)

Test duties IEC 62271-100
==========================

* **T100s**: 100% rated SC current, simétrico.
* **T100a**: 100% asimétrico (componente DC máxima).
* **T60**: 60% Ik''.
* **T30**: 30% Ik''.
* **T10**: 10% Ik'' (faltas próximas — short-line faults).
* **OP1/OP2**: out-of-phase switching.

Esta MVP cobre T10/T30/T60/T100s para envelope check.

Referências cruzadas
====================

* IEC 62271-100:2021, Section 6.102.10 (Test duties)
* IEC 62271-100:2021, Tables 14-19 (TRT parameters by voltage)
* IEC 62271-200:2021, references back to -100 for TRT specs.
* CIGRE WG A3.28 — Reference TRT for high-voltage breakers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Enums e tipos
# ---------------------------------------------------------------------------


class TestDuty(str, Enum):
    """
    Test duties da IEC 62271-100 Section 6.102.10.

    Determinam fração de Ik'' e parâmetros de TRT esperados.
    """
    T100s = "T100s"   # 100% Isc symmetrical
    T100a = "T100a"   # 100% Isc asymmetrical (DC offset)
    T60 = "T60"       # 60% Isc
    T30 = "T30"       # 30% Isc
    T10 = "T10"       # 10% Isc — short-line faults
    OP1 = "OP1"       # out-of-phase 1
    OP2 = "OP2"       # out-of-phase 2


class GroundingType(str, Enum):
    """
    Tipo de aterramento do sistema — define ``kpp``.

    * ``EFFECTIVELY_GROUNDED``: kpp = 1.3 (X0/X1 ≤ 3 e R0/X1 ≤ 1).
    * ``NON_EFFECTIVELY_GROUNDED``: kpp = 1.5 (incluindo isolado,
      ressonante, alta-impedância).
    """
    EFFECTIVELY_GROUNDED = "effectively"
    NON_EFFECTIVELY_GROUNDED = "non_effectively"


# ---------------------------------------------------------------------------
# Tabelas IEC 62271-100
# ---------------------------------------------------------------------------


# Amplitude factor kaf por test duty.
# Fonte: IEC 62271-100:2021 Table 14, valores típicos para sistemas
# de média/alta tensão. Para precisão extrema, consultar tabelas
# específicas por Voc (146 kV: T10 RRRV=7 kV/μs; 245 kV: T10
# RRRV=9 kV/μs etc.).
_AMPLITUDE_FACTORS: dict[TestDuty, float] = {
    TestDuty.T100s: 1.40,
    TestDuty.T100a: 1.40,
    TestDuty.T60:   1.50,
    TestDuty.T30:   1.54,
    TestDuty.T10:   1.76,
    TestDuty.OP1:   2.00,   # out-of-phase mais severo
    TestDuty.OP2:   2.00,
}


# RRRV típicos (kV/μs) por test duty para sistemas até 100 kV.
# Fonte: IEC 62271-100:2021 Table 14 (valores conservadores
# representativos; a norma especifica curvas por Voc nas
# Tabelas 15-19).
_TYPICAL_RRRV: dict[TestDuty, float] = {
    TestDuty.T100s: 2.0,
    TestDuty.T100a: 2.0,
    TestDuty.T60:   3.0,
    TestDuty.T30:   5.0,
    TestDuty.T10:   7.0,
    TestDuty.OP1:   1.54,
    TestDuty.OP2:   1.54,
}


# Threshold de Voc (kV) acima do qual o envelope 4-parâmetro é
# obrigatório. Abaixo, o 2-parâmetro é suficiente.
# Fonte: IEC 62271-100:2021 §6.102.10.2 (T100s).
VOC_4PARAM_THRESHOLD_KV: float = 100.0


# ---------------------------------------------------------------------------
# Helpers de cálculo
# ---------------------------------------------------------------------------


def first_pole_factor_kpp(grounding: GroundingType) -> float:
    """
    Retorna o ``kpp`` (first-pole-to-clear factor) por tipo de
    aterramento, conforme IEC 62271-100 §3.7.151.

    * Effectively grounded → 1.3
    * Non-effectively grounded → 1.5
    """
    if grounding == GroundingType.EFFECTIVELY_GROUNDED:
        return 1.3
    if grounding == GroundingType.NON_EFFECTIVELY_GROUNDED:
        return 1.5
    raise ValueError(f"GroundingType inválido: {grounding!r}")


def amplitude_factor_kaf(duty: TestDuty) -> float:
    """Retorna ``kaf`` (amplitude factor) por test duty."""
    if duty not in _AMPLITUDE_FACTORS:
        raise ValueError(f"TestDuty {duty!r} sem kaf cadastrado")
    return _AMPLITUDE_FACTORS[duty]


def typical_rrrv_kV_per_us(duty: TestDuty) -> float:
    """Retorna RRRV típico (kV/μs) por test duty."""
    if duty not in _TYPICAL_RRRV:
        raise ValueError(f"TestDuty {duty!r} sem RRRV cadastrado")
    return _TYPICAL_RRRV[duty]


def peak_voltage_uc_kV(
    rated_voltage_kV: float,
    kpp: float,
    kaf: float,
) -> float:
    """
    Calcula ``u_c`` (tensão de pico TRT, kV) pela fórmula clássica:

    ::

        u_c = kpp · kaf · √2 · U_r / √3

    Onde ``U_r`` é a tensão nominal linha-linha (kV).

    Esta fórmula é válida para test duties simétricas (T10/T30/T60/
    T100s). Para T100a (asimétrico), aplicar fator adicional ~0.9.

    Parameters
    ----------
    rated_voltage_kV:
        Tensão nominal U_r linha-linha em kV (ex: 138, 245, 550).
    kpp:
        First-pole-to-clear factor (1.3 ou 1.5).
    kaf:
        Amplitude factor (1.40, 1.50, 1.54, 1.76).

    Returns
    -------
    float
        u_c em kV.
    """
    if rated_voltage_kV <= 0:
        raise ValueError(f"rated_voltage_kV deve > 0 (achado {rated_voltage_kV})")
    if kpp <= 0 or kaf <= 0:
        raise ValueError(f"kpp ({kpp}) e kaf ({kaf}) devem ser > 0")
    return kpp * kaf * math.sqrt(2.0) * rated_voltage_kV / math.sqrt(3.0)


# ---------------------------------------------------------------------------
# Envelopes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrtEnvelope2Param:
    """
    Envelope TRT 2-parâmetro (IEC 62271-100 §6.102.10.5).

    Definida por ``(u_c, t_3)`` mais ``(t_d, u_d)`` opcional para
    o atraso inicial (delay line):

    ::

        u(t) = 0                       , t < t_d
             = u_c · (t - t_d) / t_3   , t_d ≤ t ≤ t_d + t_3
             = u_c                      , t > t_d + t_3

    Attributes
    ----------
    u_c_kV:
        Tensão de pico (kV).
    t_3_us:
        Tempo até o pico (μs).
    t_d_us:
        Atraso inicial (μs). Default 0.
    duty:
        Test duty associado.
    rated_voltage_kV:
        Tensão nominal de referência.
    source:
        Citação da norma de origem.
    """

    u_c_kV: float
    t_3_us: float
    t_d_us: float
    duty: TestDuty
    rated_voltage_kV: float
    source: str = "IEC 62271-100:2021 §6.102.10.5"

    @property
    def rrrv_kV_per_us(self) -> float:
        """RRRV efetivo = u_c / t_3."""
        return self.u_c_kV / self.t_3_us if self.t_3_us > 0 else float("inf")

    def voltage_at(self, t_us: float) -> float:
        """Avalia o envelope no instante ``t`` (μs)."""
        if t_us < self.t_d_us:
            return 0.0
        rel = t_us - self.t_d_us
        if rel >= self.t_3_us:
            return self.u_c_kV
        return self.u_c_kV * rel / self.t_3_us


@dataclass(frozen=True)
class TrtEnvelope4Param:
    """
    Envelope TRT 4-parâmetro (IEC 62271-100 §6.102.10.4).

    Definida por ``(u_1, t_1, u_c, t_2)``: trecho íngreme até
    (u_1, t_1), depois rampa mais suave até (u_c, t_2):

    ::

        u(t) = 0                         , t < t_d
             = u_1 · (t-t_d) / t_1        , t_d ≤ t ≤ t_d + t_1
             = u_1 + (u_c-u_1)·(t-t_d-t_1)/(t_2-t_1)  , t_d+t_1 ≤ t ≤ t_d+t_2
             = u_c                        , t > t_d + t_2

    Mais conservadora para sistemas ≥ 100 kV onde a contribuição
    capacitiva da linha cria um TRT bi-segmentado característico.

    Attributes
    ----------
    u_1_kV, t_1_us:
        Primeiro segmento — ponto íngreme inicial.
    u_c_kV, t_2_us:
        Pico final (u_c) e tempo total (t_2).
    t_d_us:
        Atraso inicial (μs).
    duty, rated_voltage_kV, source:
        Metadata.
    """

    u_1_kV: float
    t_1_us: float
    u_c_kV: float
    t_2_us: float
    t_d_us: float
    duty: TestDuty
    rated_voltage_kV: float
    source: str = "IEC 62271-100:2021 §6.102.10.4"

    @property
    def rrrv_initial_kV_per_us(self) -> float:
        """RRRV do primeiro segmento (mais alto) = u_1 / t_1."""
        return self.u_1_kV / self.t_1_us if self.t_1_us > 0 else float("inf")

    @property
    def rrrv_average_kV_per_us(self) -> float:
        """RRRV médio até o pico = u_c / t_2."""
        return self.u_c_kV / self.t_2_us if self.t_2_us > 0 else float("inf")

    def voltage_at(self, t_us: float) -> float:
        """Avalia o envelope em ``t_us``."""
        if t_us < self.t_d_us:
            return 0.0
        rel = t_us - self.t_d_us
        if rel <= self.t_1_us:
            return self.u_1_kV * rel / self.t_1_us
        if rel <= self.t_2_us:
            slope = (self.u_c_kV - self.u_1_kV) / (self.t_2_us - self.t_1_us)
            return self.u_1_kV + slope * (rel - self.t_1_us)
        return self.u_c_kV


def trt_envelope_2param(
    rated_voltage_kV: float,
    grounding: GroundingType,
    duty: TestDuty,
    t_d_us: float = 0.0,
) -> TrtEnvelope2Param:
    """
    Constrói envelope 2-parâmetro para ``rated_voltage_kV`` (Voc) e
    test duty conforme IEC 62271-100 Tables 14-19.

    Aplica:

    ::

        u_c = kpp · kaf · √2 · U_r / √3
        t_3 = u_c / RRRV

    Onde RRRV é o típico do duty (vide ``_TYPICAL_RRRV``).
    """
    kpp = first_pole_factor_kpp(grounding)
    kaf = amplitude_factor_kaf(duty)
    u_c = peak_voltage_uc_kV(rated_voltage_kV, kpp, kaf)
    rrrv = typical_rrrv_kV_per_us(duty)
    t_3 = u_c / rrrv
    return TrtEnvelope2Param(
        u_c_kV=u_c,
        t_3_us=t_3,
        t_d_us=t_d_us,
        duty=duty,
        rated_voltage_kV=rated_voltage_kV,
    )


def trt_envelope_4param(
    rated_voltage_kV: float,
    grounding: GroundingType,
    duty: TestDuty,
    t_d_us: float = 2.0,
    u1_ratio: float = 0.75,
    t1_ratio: float = 0.50,
) -> TrtEnvelope4Param:
    """
    Constrói envelope 4-parâmetro para sistemas ≥ 100 kV (típicos
    para T30/T60/T100s em alta-tensão).

    Aplica:

    ::

        u_c = kpp · kaf · √2 · U_r / √3
        t_2 = u_c / RRRV_avg
        u_1 = u1_ratio · u_c    (default 0.75)
        t_1 = t1_ratio · t_2    (default 0.50, dá RRRV inicial = 1.5 · RRRV_avg)

    Estes ratios são valores típicos para envelope de teste.
    Para casos críticos, consultar Tables 16-19 da IEC 62271-100.
    """
    kpp = first_pole_factor_kpp(grounding)
    kaf = amplitude_factor_kaf(duty)
    u_c = peak_voltage_uc_kV(rated_voltage_kV, kpp, kaf)
    rrrv = typical_rrrv_kV_per_us(duty)
    t_2 = u_c / rrrv
    u_1 = u1_ratio * u_c
    t_1 = t1_ratio * t_2
    return TrtEnvelope4Param(
        u_1_kV=u_1, t_1_us=t_1,
        u_c_kV=u_c, t_2_us=t_2,
        t_d_us=t_d_us,
        duty=duty,
        rated_voltage_kV=rated_voltage_kV,
    )


def select_envelope_type(
    rated_voltage_kV: float, duty: TestDuty,
) -> str:
    """
    Sugere ``"2param"`` ou ``"4param"`` baseado em Voc e duty
    conforme IEC 62271-100:

    * ≥ 100 kV ou T30/T60/T100s → ``"4param"``.
    * < 100 kV e T10 ou T100a → ``"2param"``.
    """
    if (
        rated_voltage_kV >= VOC_4PARAM_THRESHOLD_KV
        or duty in (TestDuty.T30, TestDuty.T60, TestDuty.T100s)
    ):
        return "4param"
    return "2param"
