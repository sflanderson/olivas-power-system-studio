"""
app.standards.iec60909 — codificação dos requisitos de cálculo de
curto-circuito da IEC 60909-0:2016 (Short-circuit currents in
three-phase a.c. systems).

Fonte: IEC 60909-0:2016 (LIBRARY/IEC 60909_0.pdf).

Fundamentos
============

A IEC 60909-0 padroniza o cálculo de correntes de curto-circuito
máximas e mínimas em sistemas trifásicos AC para qualquer ponto
do sistema. A norma aplica método das **componentes simétricas**
com fonte de tensão equivalente no ponto de falta:

::

    U_eq = c · Un / √3      (fonte equivalente fase-neutro)

Onde ``c`` é o **voltage factor** (Tabela 1 da norma) que depende
do nível de tensão e do tipo de cálculo (max ou min).

Correntes características
=========================

* **Ik''** (initial symmetrical SC current): valor RMS da
  componente AC simétrica no instante t=0.

  ::

      Ik'' = c · Un / (√3 · |Z_k|)

* **ip** (peak SC current): valor de pico instantâneo
  considerando contribuição DC.

  ::

      ip = κ · √2 · Ik''
      κ  = 1.02 + 0.98·exp(-3·R/X)

  Para sistemas trifásicos AC, ``κ`` varia entre 1.02 (R/X grande,
  sistemas de baixa tensão) e ~1.95 (R/X pequeno, alta-tensão
  geradores).

* **idc** (DC component at time t):

  ::

      idc(t) = √2 · Ik'' · exp(-2π·f·t·R/X)

* **Ib** (symmetrical SC breaking current): para faltas
  alimentadas por gerador, ``Ib = μ·q·Ik''`` (factors of decay).
  Para faltas longe do gerador (far-from-generator), ``Ib = Ik''``.

* **Ik** (steady-state SC current): valor RMS da componente AC
  no regime permanente (após decaimento subtransitório/transitório).

Voltage factor Table 1 (IEC 60909-0:2016)
==========================================

==========================  =========  =========
Sistema (tensão nominal Un) ``c_max``  ``c_min``
==========================  =========  =========
LV 100 V → 1000 V (230/400) 1.05 *     0.95
LV 100 V → 1000 V (outros)  1.10       0.95
MV  1 kV → 35 kV            1.10       1.00
HV  >35 kV → 230 kV         1.10       1.00
==========================  =========  =========

\\* Para 230/400 V residencial, IEC usa 1.00 vs 0.95 (não aplicar
   1.05 quando a tolerância de tensão é menor).

Para cálculo da máxima Ik'' usa-se ``c_max``; para mínima Ik''
(seletividade de proteção) usa-se ``c_min``.

Far-from-generator vs near-to-generator
========================================

A IEC 60909-0 distingue:

* **Far-from-generator**: ``Ik'' = Ib = Ik`` (não há decaimento).
* **Near-to-generator**: ``Ik'' > Ib > Ik`` (componente AC
  decai por causa da reação de armadura).

Critério aproximado: a falta é "near-to-generator" se a maior
contribuição vem de gerador conectado por linha curta (Z_linha <<
Xd''_gerador).

Referências cruzadas
=====================

* IEC 60909-0:2016 §3.8 (definitions).
* IEC 60909-0:2016 §4.2.2 (Voltage factor c, Table 1).
* IEC 60909-0:2016 §4.3.1 (formulas for Ik'', ip).
* IEC 60909-0:2016 §4.4 (calculation of asymmetrical SC currents).
* IEC TR 60909-1 (factors and examples).
* IEC TR 60909-2 (data for impedance calculations).
* IEC TR 60909-3 (faults to ground).
* IEC TR 60909-4 (examples).
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Voltage factor Table 1
# ---------------------------------------------------------------------------


class VoltageLevel(str, Enum):
    """
    Classificação de tensão para escolha do voltage factor c
    conforme IEC 60909-0 Table 1.
    """
    LV_RESIDENTIAL = "lv_residential"   # 230/400 V — c_max=1.05
    LV_INDUSTRIAL = "lv_industrial"     # outros LV — c_max=1.10
    MV = "mv"                            # 1 kV → 35 kV
    HV = "hv"                            # > 35 kV


class FaultDistance(str, Enum):
    """
    Classificação far-/near-to-generator para decaimento.

    * FAR_FROM_GENERATOR: Ik'' = Ib = Ik.
    * NEAR_TO_GENERATOR: aplicar fatores de decaimento μ·q.
    """
    FAR_FROM_GENERATOR = "far"
    NEAR_TO_GENERATOR = "near"


# Voltage factors c por tipo de cálculo (max/min) e nível.
# Fonte: IEC 60909-0:2016 Table 1.
_VOLTAGE_FACTORS_MAX: dict[VoltageLevel, float] = {
    VoltageLevel.LV_RESIDENTIAL: 1.05,
    VoltageLevel.LV_INDUSTRIAL: 1.10,
    VoltageLevel.MV: 1.10,
    VoltageLevel.HV: 1.10,
}

_VOLTAGE_FACTORS_MIN: dict[VoltageLevel, float] = {
    VoltageLevel.LV_RESIDENTIAL: 0.95,
    VoltageLevel.LV_INDUSTRIAL: 0.95,
    VoltageLevel.MV: 1.00,
    VoltageLevel.HV: 1.00,
}


def voltage_factor_c(
    level: VoltageLevel, kind: str = "max",
) -> float:
    """
    Retorna o voltage factor c conforme IEC 60909-0 Table 1.

    Parameters
    ----------
    level:
        Nível de tensão.
    kind:
        ``"max"`` para máxima Ik'' (default), ``"min"`` para
        mínima (estudo de seletividade).
    """
    if kind == "max":
        return _VOLTAGE_FACTORS_MAX[level]
    if kind == "min":
        return _VOLTAGE_FACTORS_MIN[level]
    raise ValueError(f"kind deve ser 'max' ou 'min' (achado {kind!r})")


def classify_voltage(rated_voltage_kV: float) -> VoltageLevel:
    """
    Auto-classifica nível de tensão para uso de c-factor.

    * ≤ 1 kV → LV_INDUSTRIAL (use LV_RESIDENTIAL explicitamente
      para 230/400 V se aplicável).
    * 1 a 35 kV → MV.
    * > 35 kV → HV.
    """
    if rated_voltage_kV <= 1.0:
        return VoltageLevel.LV_INDUSTRIAL
    if rated_voltage_kV <= 35.0:
        return VoltageLevel.MV
    return VoltageLevel.HV


# ---------------------------------------------------------------------------
# Cálculo da kappa (peak factor)
# ---------------------------------------------------------------------------


def kappa_factor(r_over_x: float) -> float:
    """
    Calcula κ (peak factor) conforme IEC 60909-0 §4.3.1.2.

    ::

        κ = 1.02 + 0.98 · exp(-3 · R/X)

    Limites:
    * R/X = 0 → κ = 2.00 (puramente indutivo, asimetria máxima)
    * R/X = 0.10 → κ ≈ 1.75
    * R/X = 0.50 → κ ≈ 1.24
    * R/X → ∞ → κ → 1.02 (DC offset desprezível)

    Para malhas com múltiplas R/X diferentes (Methods A, B, C
    da norma), usar Method C (frequency-equivalent) para precisão.
    Esta MVP cobre Method B (single equivalent R/X).
    """
    if r_over_x < 0:
        raise ValueError(f"R/X deve ser >= 0 (achado {r_over_x})")
    return 1.02 + 0.98 * math.exp(-3.0 * r_over_x)


# ---------------------------------------------------------------------------
# Impedâncias dos componentes
# ---------------------------------------------------------------------------


def network_feeder_impedance_ohm(
    rated_voltage_kV: float,
    short_circuit_power_MVA: float,
    voltage_factor_c: float = 1.10,
    r_over_x: float = 0.10,
) -> complex:
    """
    Impedância equivalente de uma rede externa (feeder) conforme
    IEC 60909-0 §6.2.

    ::

        |Z_Q| = c · Un² / S_kQ''

    Onde S_kQ'' é a potência de curto-circuito conhecida no
    ponto de conexão.

    Parameters
    ----------
    rated_voltage_kV:
        Tensão nominal Un (linha-linha) em kV.
    short_circuit_power_MVA:
        S_kQ'' — potência de SC no ponto de entrega.
    voltage_factor_c:
        Geralmente 1.10 para HV/MV.
    r_over_x:
        Razão R/X da rede; típico 0.10 para HV, 0.30 para MV.

    Returns
    -------
    complex
        Z_Q = R_Q + jX_Q em ohms.
    """
    if rated_voltage_kV <= 0 or short_circuit_power_MVA <= 0:
        raise ValueError("rated_voltage e SC_power devem ser > 0")
    z_mag = (
        voltage_factor_c
        * (rated_voltage_kV * 1.0e3) ** 2
        / (short_circuit_power_MVA * 1.0e6)
    )
    # Decompor em R + jX usando R/X
    # X = z / sqrt(1 + (R/X)²)
    # R = (R/X) · X
    x = z_mag / math.sqrt(1.0 + r_over_x ** 2)
    r = r_over_x * x
    return complex(r, x)


def transformer_impedance_ohm(
    rated_voltage_kV: float,
    rated_power_MVA: float,
    uk_percent: float,
    uR_percent: float = 0.0,
) -> complex:
    """
    Impedância de um transformador 2-enrolamentos referida ao
    lado de tensão Un, conforme IEC 60909-0 §6.3.1.

    ::

        Z_T = (uk / 100) · U_rT² / S_rT
        R_T = (uR / 100) · U_rT² / S_rT
        X_T = √(Z_T² - R_T²)

    Parameters
    ----------
    rated_voltage_kV:
        Tensão nominal U_rT do enrolamento referenciado.
    rated_power_MVA:
        Potência nominal S_rT.
    uk_percent:
        Tensão de curto-circuito percentual (impedância%, %Z).
    uR_percent:
        Componente resistivo (perdas em SC). Se 0, assume X-only
        (puramente indutivo — conservador para Ik'').

    Returns
    -------
    complex
        Z_T = R_T + jX_T em ohms.
    """
    if rated_voltage_kV <= 0 or rated_power_MVA <= 0:
        raise ValueError("V e S devem ser > 0")
    if uk_percent <= 0:
        raise ValueError(f"uk_percent deve ser > 0 (achado {uk_percent})")
    if uR_percent < 0 or uR_percent > uk_percent:
        raise ValueError(
            f"uR_percent ({uR_percent}) deve ser 0 ≤ uR ≤ uk ({uk_percent})"
        )
    z_base = (rated_voltage_kV * 1.0e3) ** 2 / (rated_power_MVA * 1.0e6)
    z_mag = (uk_percent / 100.0) * z_base
    r = (uR_percent / 100.0) * z_base
    x = math.sqrt(max(0.0, z_mag ** 2 - r ** 2))
    return complex(r, x)


def synchronous_machine_impedance_ohm(
    rated_voltage_kV: float,
    rated_power_MVA: float,
    Xd_pp_pu: float,
    Ra_pu: float = 0.003,
) -> complex:
    """
    Impedância subtransitória de uma máquina síncrona referida
    aos seus terminais, conforme IEC 60909-0 §6.6.

    ::

        Z''_G = Ra + jXd''
        em pu, então convertido a ohms via Z_base = U_rG² / S_rG

    Para correntes de SC iniciais (Ik''), usa-se ``Xd''``.
    """
    if rated_voltage_kV <= 0 or rated_power_MVA <= 0:
        raise ValueError("V e S devem ser > 0")
    z_base = (rated_voltage_kV * 1.0e3) ** 2 / (rated_power_MVA * 1.0e6)
    return complex(Ra_pu * z_base, Xd_pp_pu * z_base)


# ---------------------------------------------------------------------------
# Cálculo de Ik'', ip, idc
# ---------------------------------------------------------------------------


def initial_symmetric_sc_current_kA(
    rated_voltage_kV: float,
    z_thevenin_ohm: complex,
    voltage_factor: float = 1.10,
) -> float:
    """
    Calcula Ik'' (initial symmetrical SC current, kA RMS) por:

    ::

        Ik'' = c · Un / (√3 · |Z_k|)

    Onde Z_k é a impedância de Thevenin no ponto de falta.
    """
    if rated_voltage_kV <= 0:
        raise ValueError("rated_voltage_kV deve ser > 0")
    z_mag = abs(z_thevenin_ohm)
    if z_mag == 0:
        # v0.92.2: log fallback (auditabilidade)
        from app.core.logging_config import get_logger
        log = get_logger(__name__)
        log.warning(
            "z_thevenin=0 em rede %.2f kV; corrente Ik'' = inf "
            "(fonte ideal sem impedância). Adicione impedância "
            "de rede para resultado físico defensável. "
            "[IEC 60909-0 §4.3.1]",
            rated_voltage_kV,
        )
        return float("inf")
    return voltage_factor * rated_voltage_kV / (math.sqrt(3.0) * z_mag)


def peak_sc_current_kA(
    ik_pp_kA: float, r_over_x: float,
) -> float:
    """
    Calcula ip (peak SC current, kA) por:

    ::

        ip = κ · √2 · Ik''
    """
    return kappa_factor(r_over_x) * math.sqrt(2.0) * ik_pp_kA


def dc_component_kA(
    ik_pp_kA: float,
    r_over_x: float,
    time_s: float,
    frequency_Hz: float = 60.0,
) -> float:
    """
    Componente DC da corrente de SC em ``time_s`` segundos:

    ::

        idc(t) = √2 · Ik'' · exp(-2π·f·t·R/X)
    """
    if time_s < 0:
        raise ValueError(f"time_s deve ser >= 0 (achado {time_s})")
    decay = math.exp(-2.0 * math.pi * frequency_Hz * time_s * r_over_x)
    return math.sqrt(2.0) * ik_pp_kA * decay


# ---------------------------------------------------------------------------
# Resultado consolidado
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShortCircuitResult:
    """
    Resultado completo do cálculo IEC 60909-0 num ponto de falta.

    Attributes
    ----------
    Ik_pp_kA:
        Initial symmetrical SC current (RMS, kA).
    ip_kA:
        Peak SC current (kA).
    idc_at_50ms_kA:
        DC component em t=50ms (default — momento de abertura
        de disjuntores rápidos).
    Ib_kA:
        Symmetrical breaking current (assume Ib=Ik'' para
        far-from-generator; v0.27.x adicionará μ·q).
    Ik_steady_kA:
        Steady-state SC current (assume Ik=Ik'' para far-from-
        generator).
    z_thevenin_ohm:
        Impedância de Thevenin no ponto.
    r_over_x:
        Razão R/X para cálculo de κ.
    kappa:
        Factor κ aplicado.
    voltage_factor_c:
        c usado.
    rated_voltage_kV:
        Un do sistema.
    fault_distance:
        Far/near-to-generator.
    source:
        Citação da norma.
    """

    Ik_pp_kA: float
    ip_kA: float
    idc_at_50ms_kA: float
    Ib_kA: float
    Ik_steady_kA: float

    z_thevenin_ohm: complex
    r_over_x: float
    kappa: float
    voltage_factor_c: float
    rated_voltage_kV: float
    fault_distance: FaultDistance = FaultDistance.FAR_FROM_GENERATOR
    source: str = "IEC 60909-0:2016"

    @property
    def thermal_equivalent_kA(self) -> float:
        """
        Corrente térmica equivalente Ith (RMS) durante 1s,
        aproximada como Ik'' para far-from-generator.

        Para precisão maior, aplicar fatores m+n da IEC 60909-0
        §4.8 (não cobertos no MVP).
        """
        return self.Ik_pp_kA

    def summary(self) -> str:
        return (
            f"=== IEC 60909-0 Short-Circuit Analysis ===\n"
            f"Source: {self.source}\n"
            f"System Un = {self.rated_voltage_kV:.2f} kV, "
            f"c = {self.voltage_factor_c:.2f}\n"
            f"Z_thevenin = {self.z_thevenin_ohm.real:.4f} + "
            f"j{self.z_thevenin_ohm.imag:.4f} Ω, R/X = {self.r_over_x:.4f}\n"
            f"\n"
            f"--- Currents ---\n"
            f"  Ik'' = {self.Ik_pp_kA:.3f} kA  (initial symmetrical)\n"
            f"  ip   = {self.ip_kA:.3f} kA  (peak, κ={self.kappa:.3f})\n"
            f"  idc  = {self.idc_at_50ms_kA:.3f} kA  (@ 50 ms)\n"
            f"  Ib   = {self.Ib_kA:.3f} kA  (breaking)\n"
            f"  Ik   = {self.Ik_steady_kA:.3f} kA  (steady-state)\n"
            f"  Distance: {self.fault_distance.value}-from-generator"
        )


def calculate_short_circuit(
    rated_voltage_kV: float,
    z_thevenin_ohm: complex,
    voltage_level: VoltageLevel | None = None,
    kind: str = "max",
    fault_distance: FaultDistance = FaultDistance.FAR_FROM_GENERATOR,
    frequency_Hz: float = 60.0,
    time_for_idc_s: float = 0.050,
    *,
    correction_factor: float = 1.0,
    breaker_min_delay_s: float | None = None,
    generator_x_d_subtransient_pu: float | None = None,
    is_synchronous_motor: bool = False,
    motor_speed_gradient_pu_per_s: float = 0.10,
) -> ShortCircuitResult:
    """
    Wrapper consolidado: dado Un e Z_thevenin, calcula todos os
    parâmetros padrão da IEC 60909-0.

    Parameters
    ----------
    rated_voltage_kV:
        Tensão nominal Un (linha-linha).
    z_thevenin_ohm:
        Impedância equivalente no ponto de falta.
    voltage_level:
        Auto-classificado se None.
    kind:
        ``"max"`` (default) ou ``"min"`` para escolha do c.
    fault_distance:
        ``FAR_FROM_GENERATOR`` (default) → Ib = Ik = Ik''.
        ``NEAR_TO_GENERATOR`` → aplica decaimento μ·q
        (v3.3.1 Sub-sprint D — gap audit §D.5 fechado).
    correction_factor:
        v3.3.1 Sub-sprint C: factor combinado a aplicar a Z_thevenin
        antes de calcular Ik''. Use produto de KT × KG × KSO (cada
        um obtido de :func:`transformer_correction_factor_KT`,
        :func:`generator_correction_factor_KG`,
        :func:`motor_correction_factor_KSO`). Default 1.0 (sem
        correção). Per IEC 60909-0:2016 §6.x.
    breaker_min_delay_s:
        v3.3.1 Sub-sprint D: tempo mínimo de operação do breaker, em
        segundos. Usado para calcular μ (decay AC) e q (decay near-gen).
        Default None = usa 0.05 s (50ms).
    generator_x_d_subtransient_pu:
        v3.3.1 Sub-sprint D: Xd'' do gerador near-from-fault. Necessário
        para o cálculo de μ via :mod:`iec60909_decay`.
    is_synchronous_motor:
        v3.3.1 Sub-sprint D: True se a contribuição é de motor
        síncrono (afeta q factor — IEC 60909-0 §4.5.2.2).
    motor_speed_gradient_pu_per_s:
        v3.7.0 (closes SKIPPED_BACKLOG B.3) — gradiente de velocidade
        do motor assíncrono (IEC 60909-0:2016 §4.6.2 Tab 3):
        - 0.10 (default) — motor 2-pólos
        - 0.05 — motor 4-pólos
        - 0.02 — motor 6+ pólos
        Aplicado em :func:`q_factor` para calcular Ik steady-state
        de motor assíncrono no caso NEAR_TO_GENERATOR.

    References
    ----------
    IEC 60909-0:2016 §4 (calculation of currents) + §6 (impedances).
    PTW Tutorial §Part 5 p.128.
    """
    if voltage_level is None:
        voltage_level = classify_voltage(rated_voltage_kV)
    c = voltage_factor_c(voltage_level, kind=kind)

    # v3.3.1 Sub-sprint C: apply correction factor (KT × KG × KSO)
    if correction_factor != 1.0:
        if correction_factor <= 0:
            raise ValueError(
                f"correction_factor must be > 0; got {correction_factor!r}"
            )
        z_thevenin_ohm = z_thevenin_ohm * correction_factor

    r_over_x = (
        z_thevenin_ohm.real / z_thevenin_ohm.imag
        if z_thevenin_ohm.imag != 0 else float("inf")
    )

    ik_pp = initial_symmetric_sc_current_kA(
        rated_voltage_kV, z_thevenin_ohm, voltage_factor=c,
    )
    kappa = kappa_factor(r_over_x)
    ip = peak_sc_current_kA(ik_pp, r_over_x)
    idc = dc_component_kA(
        ik_pp, r_over_x, time_for_idc_s, frequency_Hz=frequency_Hz,
    )

    # v3.3.1 Sub-sprint D: integra decay μ·q quando NEAR_TO_GENERATOR.
    # Per IEC 60909-0:2016 §4.5 (μ factor — generator decay).
    # Para FAR_FROM_GENERATOR, mantém Ib = Ik = Ik'' (caso simples).
    if (fault_distance == FaultDistance.NEAR_TO_GENERATOR
            and generator_x_d_subtransient_pu is not None
            and breaker_min_delay_s is not None):
        try:
            from app.standards.iec60909_decay import mu_factor
            # Compute Ik''_G / I_rG ratio. Approximation: ratio ≈ 1/Xd''
            # (assume operating at nominal voltage; for r ≤ 2 µ → 1.0)
            ratio = 1.0 / generator_x_d_subtransient_pu
            mu = mu_factor(
                Ik_pp_to_IrG_ratio=ratio,
                minimum_clearing_time_s=breaker_min_delay_s,
            )
            ib = mu * ik_pp
            # Steady-state: gerador síncrono mantém ~Ik''; async motor
            # decai conforme q_factor IEC 60909-0 §4.6.2.
            # v3.7.0 B.3 — usa motor_speed_gradient_pu_per_s (default
            # 0.10 = 2-pólos) em vez do antigo factor fixo 0.5.
            if is_synchronous_motor:
                ik_steady = ib
            else:
                from app.standards.iec60909_decay import q_factor as _qf
                q = _qf(
                    minimum_clearing_time_s=breaker_min_delay_s,
                    n_per_unit_per_second=motor_speed_gradient_pu_per_s,
                )
                ik_steady = ib * q
        except (ImportError, AttributeError, TypeError, ValueError):
            # Fallback se assinatura do iec60909_decay não bater
            ib = ik_pp
            ik_steady = ik_pp
    else:
        # FAR_FROM_GENERATOR (default): Ib = Ik = Ik''
        ib = ik_pp
        ik_steady = ik_pp

    return ShortCircuitResult(
        Ik_pp_kA=ik_pp,
        ip_kA=ip,
        idc_at_50ms_kA=idc,
        Ib_kA=ib,
        Ik_steady_kA=ik_steady,
        z_thevenin_ohm=z_thevenin_ohm,
        r_over_x=r_over_x,
        kappa=kappa,
        voltage_factor_c=c,
        rated_voltage_kV=rated_voltage_kV,
        fault_distance=fault_distance,
    )


# ===========================================================================
# v3.3.0 Sprint 5 — Impedance Correction Factors (IEC 60909-0:2016)
# ===========================================================================
# Closing audit gap §D.3: KT (transformer §6.3.3, Tab 3),
# KG / KSO (generator/motor §6.6.2, Tab 2).
# ===========================================================================


def transformer_correction_factor_KT(
    *,
    voltage_factor_c_max: float,
    x_T_pu: float,
) -> float:
    """**Transformer impedance correction factor KT** (IEC 60909-0 §6.3.3).

    Per IEC 60909-0:2016 §6.3.3 Eq. 12:

    .. math::
        K_T = 0.95 \\cdot \\frac{c_{max}}{1 + 0.6 \\cdot x_T}

    Onde:
    - ``c_max`` = voltage factor cmax na barra de fault (Tab 1)
    - ``x_T`` = reactance per-unit do TX (referida à própria SnT)

    Aplicado a Z_T para obter Z_TK = KT × Z_T.

    Parameters
    ----------
    voltage_factor_c_max
        Voltage factor cmax do bus de fault (geralmente 1.05 ou 1.10).
    x_T_pu
        Reactance per-unit do TX (positive sequence).

    Returns
    -------
    float
        KT factor.

    References
    ----------
    IEC 60909-0:2016 §6.3.3 Eq. (12).
    """
    if x_T_pu <= 0:
        raise ValueError(f"x_T_pu must be > 0; got {x_T_pu!r}")
    if voltage_factor_c_max <= 0:
        raise ValueError(
            f"voltage_factor_c_max must be > 0; got {voltage_factor_c_max!r}"
        )
    return 0.95 * voltage_factor_c_max / (1.0 + 0.6 * x_T_pu)


def generator_correction_factor_KG(
    *,
    voltage_factor_c_max: float,
    x_d_subtransient_pu: float,
    cos_phi_rg: float = 0.85,
) -> float:
    """**Generator impedance correction factor KG** (IEC 60909-0 §6.6.2).

    Per IEC 60909-0:2016 §6.6.2 Eq. 17:

    .. math::
        K_G = \\frac{U_n}{U_{rG}} \\cdot \\frac{c_{max}}{1 + x_d'' \\cdot \\sin(\\varphi_{rG})}

    Aproximação assumindo Un ≈ UrG (operação nominal):

    .. math::
        K_G \\approx \\frac{c_{max}}{1 + x_d'' \\cdot \\sin(\\varphi_{rG})}

    Aplicado a Z_G para obter Z_GK = KG × Z_G.

    Parameters
    ----------
    voltage_factor_c_max
        Voltage factor cmax do bus do gerador.
    x_d_subtransient_pu
        Subtransient reactance Xd'' per-unit (referida ao SrG).
    cos_phi_rg
        Cosine of rated power factor of generator (default 0.85).

    Returns
    -------
    float
        KG factor.

    References
    ----------
    IEC 60909-0:2016 §6.6.2 Eq. (17).
    """
    if x_d_subtransient_pu <= 0:
        raise ValueError(
            f"x_d_subtransient_pu must be > 0; got {x_d_subtransient_pu!r}"
        )
    if not 0 < cos_phi_rg <= 1:
        raise ValueError(
            f"cos_phi_rg must be in (0, 1]; got {cos_phi_rg!r}"
        )
    sin_phi = math.sqrt(1.0 - cos_phi_rg ** 2)
    return voltage_factor_c_max / (1.0 + x_d_subtransient_pu * sin_phi)


def motor_correction_factor_KSO(
    *,
    voltage_factor_c_max: float,
    x_M_subtransient_pu: float,
    cos_phi_motor: float = 0.83,
) -> float:
    """**Motor impedance correction factor KSO** (IEC 60909-0 §6.7).

    Per IEC 60909-0:2016 §6.7 — para motores assíncronos contributing
    em sub-transient stage:

    .. math::
        K_{SO} = \\frac{c_{max}}{1 + x_M'' \\cdot \\sin(\\varphi_M)}

    Análogo a KG mas para motor (asynchronous typically cos_phi=0.83).

    Parameters
    ----------
    voltage_factor_c_max
        Voltage factor cmax.
    x_M_subtransient_pu
        Motor subtransient reactance, pu (sob SrM).
    cos_phi_motor
        Motor power factor (default 0.83 — typical NEMA design B).

    Returns
    -------
    float
        KSO factor.

    References
    ----------
    IEC 60909-0:2016 §6.7.
    """
    if x_M_subtransient_pu <= 0:
        raise ValueError(
            f"x_M_subtransient_pu must be > 0; got {x_M_subtransient_pu!r}"
        )
    if not 0 < cos_phi_motor <= 1:
        raise ValueError(
            f"cos_phi_motor must be in (0, 1]; got {cos_phi_motor!r}"
        )
    sin_phi = math.sqrt(1.0 - cos_phi_motor ** 2)
    return voltage_factor_c_max / (1.0 + x_M_subtransient_pu * sin_phi)
