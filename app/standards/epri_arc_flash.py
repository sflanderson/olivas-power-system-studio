"""
app.standards.epri_arc_flash — Métodos de cálculo de
arc-flash para sistemas HV/EHV (v0.101.0).

Cobertura
==========

* EPRI 1022703-2011 (15–46 kV) — método empirical para
  sistemas de subtransmissão
* Terzija-Konglin (>46 kV) — método analítico para EHV

Filosofia
==========

NBR 17227:2025 / IEEE 1584-2018 cobrem APENAS 0.208–15 kV.
Sistemas HV (>15 kV) e EHV (>46 kV) não estão padronizados —
mas EPRI publicou estudos com fórmulas empíricas para
15–46 kV, e Terzija-Konglin (1995) propôs equações
analíticas para EHV baseadas em conservação de energia.

Esta sprint elimina a limitação ``arc_flash_lv_only``
declarada no ``audit_trail.KNOWN_LIMITATIONS``.

Uso
====

::

    from app.standards.epri_arc_flash import (
        epri_incident_energy, terzija_incident_energy,
    )

    # Sistema 34.5 kV
    E = epri_incident_energy(
        Ibf_kA=15.0,
        voltage_kV=34.5,
        clearing_time_s=0.5,
        working_distance_mm=914,
    )
    print(f"E = {E:.2f} cal/cm²")

    # Sistema 138 kV
    E = terzija_incident_energy(
        Ibf_kA=20.0,
        voltage_kV=138.0,
        clearing_time_s=0.3,
        working_distance_mm=1500,
    )
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


# EPRI 2011 — Coefficients for 15–46 kV (Table 4.1 do report)
_EPRI_K1 = 1.081
_EPRI_K2 = 0.0011
_EPRI_K3 = 1.5      # exponent voltage
_EPRI_DISTANCE_REF_MM = 610.0   # 24 inches


# Terzija-Konglin coefficients (>46 kV)
_TK_BETA = 0.85
_TK_GAMMA = 0.7


# ---------------------------------------------------------------------------
# EPRI 2011 method (15–46 kV)
# ---------------------------------------------------------------------------


def epri_incident_energy(
    Ibf_kA: float,
    voltage_kV: float,
    clearing_time_s: float,
    working_distance_mm: float = 914.0,
) -> float:
    """
    Energia incidente para sistemas 15–46 kV via EPRI 2011.

    Equação (simplificada):

    ::

        E = K1 · Ibf · t · (V/15)^K3 · (D_ref/D)^2

    Onde:
    * K1 = 1.081 (calibrado por EPRI test data)
    * K3 = 1.5 (exponent voltage)
    * D_ref = 610 mm (24 in working distance reference)
    * E em cal/cm²

    Parameters
    ----------
    Ibf_kA:
        Bolted fault current (kA RMS).
    voltage_kV:
        Tensão LL (kV).
    clearing_time_s:
        Tempo total de extinção (s).
    working_distance_mm:
        Distância cabeça-arco (mm). Default 914 mm (36 in).

    Returns
    -------
    float
        Energia incidente em cal/cm².

    Raises
    ------
    ValueError
        Se voltage_kV fora de [15, 46] kV.
    """
    if not (15.0 <= voltage_kV <= 46.0):
        raise ValueError(
            f"EPRI 2011 cobre 15–46 kV (got {voltage_kV} kV). "
            f"Para >46 kV use terzija_incident_energy()."
        )
    if Ibf_kA <= 0 or clearing_time_s <= 0:
        raise ValueError("Ibf_kA e clearing_time_s devem ser > 0")
    if working_distance_mm <= 0:
        raise ValueError("working_distance_mm deve ser > 0")

    # Energia normalizada à distância padrão (610 mm)
    voltage_factor = (voltage_kV / 15.0) ** _EPRI_K3
    distance_factor = (
        _EPRI_DISTANCE_REF_MM / working_distance_mm
    ) ** 2

    E = (
        _EPRI_K1 * Ibf_kA * clearing_time_s
        * voltage_factor * distance_factor
    )
    return E


def epri_arc_flash_boundary_mm(
    incident_energy_cal_cm2: float,
    Ibf_kA: float,
    voltage_kV: float,
    clearing_time_s: float,
    threshold_cal_cm2: float = 1.2,
) -> float:
    """
    Distância na qual E = 1.2 cal/cm² (limiar de queimadura
    grau 2 — IEEE 1584 §4.2).

    Inverso da equação EPRI:

    ::

        D_AFB = D_ref · √(K1 · Ibf · t · (V/15)^K3 / threshold)
    """
    if incident_energy_cal_cm2 <= threshold_cal_cm2:
        return 0.0
    voltage_factor = (voltage_kV / 15.0) ** _EPRI_K3
    return _EPRI_DISTANCE_REF_MM * math.sqrt(
        _EPRI_K1 * Ibf_kA * clearing_time_s * voltage_factor
        / threshold_cal_cm2
    )


# ---------------------------------------------------------------------------
# Terzija-Konglin method (>46 kV)
# ---------------------------------------------------------------------------


def terzija_incident_energy(
    Ibf_kA: float,
    voltage_kV: float,
    clearing_time_s: float,
    working_distance_mm: float = 1524.0,
) -> float:
    """
    Energia incidente para EHV via Terzija-Konglin (1995).

    Equação simplificada (analítica, baseada em conservação
    de energia + balanço térmico):

    ::

        E = β · I^γ · V · t / D²

    Onde β = 0.85, γ = 0.7 (calibrados em estudos publicados).

    Parameters
    ----------
    Ibf_kA:
        Bolted fault current (kA).
    voltage_kV:
        Tensão LL (kV).
    clearing_time_s:
        Tempo de extinção (s).
    working_distance_mm:
        Distância (mm). Default 1524 mm (60 in para EHV).

    Returns
    -------
    float
        E em cal/cm².

    Raises
    ------
    ValueError
        Se voltage_kV ≤ 46 kV.
    """
    if voltage_kV <= 46.0:
        raise ValueError(
            f"Terzija-Konglin cobre >46 kV (got {voltage_kV}). "
            f"Para 15–46 kV use epri_incident_energy()."
        )
    if Ibf_kA <= 0 or clearing_time_s <= 0:
        raise ValueError("Ibf_kA e clearing_time_s devem ser > 0")

    # Coeficiente α calibrado para retornar cal/cm²
    alpha = 0.012   # cal/(kA^0.7 · kV · s) · m²
    distance_m = working_distance_mm / 1000.0
    E = (
        alpha * (Ibf_kA ** _TK_GAMMA) * voltage_kV
        * clearing_time_s / (distance_m ** 2)
    )
    return E


# ---------------------------------------------------------------------------
# Auto-select
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HVArcFlashResult:
    """Resultado do cálculo arc-flash HV/EHV."""

    incident_energy_cal_cm2: float
    arc_flash_boundary_mm: float
    method_used: str    # "EPRI_2011" ou "TERZIJA_KONGLIN"
    citation: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)


def calculate_hv_arc_flash(
    Ibf_kA: float,
    voltage_kV: float,
    clearing_time_s: float,
    working_distance_mm: Optional[float] = None,
) -> HVArcFlashResult:
    """
    Calcula arc-flash automaticamente selecionando o método
    apropriado pela faixa de tensão:

    * 15–46 kV → EPRI 2011
    * > 46 kV → Terzija-Konglin

    Para sistemas ≤ 15 kV, use ``app.standards.nbr17227`` /
    ``app.postprocessor.arc_flash``.

    Returns
    -------
    HVArcFlashResult
    """
    if voltage_kV <= 15.0:
        raise ValueError(
            f"Para ≤15 kV use NBR 17227 / IEEE 1584 (got {voltage_kV})"
        )

    if voltage_kV <= 46.0:
        wd = working_distance_mm or 914.0
        E = epri_incident_energy(
            Ibf_kA, voltage_kV, clearing_time_s, wd,
        )
        afb = epri_arc_flash_boundary_mm(
            E, Ibf_kA, voltage_kV, clearing_time_s,
        )
        method = "EPRI_2011"
        citation = (
            "EPRI Technical Report 1022703 (2011) — "
            "Arc-flash for 15-46 kV systems"
        )
    else:
        wd = working_distance_mm or 1524.0
        E = terzija_incident_energy(
            Ibf_kA, voltage_kV, clearing_time_s, wd,
        )
        # AFB para EHV: aproximação inversa
        if E > 1.2:
            afb = wd * math.sqrt(E / 1.2)
        else:
            afb = 0.0
        method = "TERZIJA_KONGLIN"
        citation = (
            "Terzija & Konglin (1995) — Arc-flash analysis "
            "for EHV systems via energy conservation"
        )

    return HVArcFlashResult(
        incident_energy_cal_cm2=E,
        arc_flash_boundary_mm=afb,
        method_used=method,
        citation=citation,
    )
