"""
app.standards.dc_arc_flash — DC arc-flash incident energy
via método de potência máxima (v1.6.0 Sprint C).

Fonte primária
==============

NFPA 70E:2024 *Annex D.5 — Maximum Power Method for DC Arc Flash
Hazard Calculations*. Reproduz o método originalmente proposto
por **Stokes & Oppenheim (1991)** e refinado por **Wilkins (2003)**.

Princípio físico
================

Maximum Power Transfer Theorem aplicado a um arco DC:

* O arco se estabelece em equilíbrio quando ``V_arc = V_sys / 2``
  (dissipa máxima potência).
* Corrente de arco: ``I_arc = V_sys / (2 · R_total)`` =
  ``I_sc / 2``, onde I_sc é o curto-circuito DC máximo.
* Potência máxima dissipada no arco:
  ``P_max = V_arc · I_arc = V_sys · I_sc / 4``.

Equação NFPA 70E §D.5 (energia incidente esférica)::

    E (J/cm²) = (P_max · t) / (4π · D² )

    E (cal/cm²) = E (J/cm²) / 4.184

Onde:
* ``P_max`` em watts = V_sys · I_sc / 4
* ``t`` em segundos
* ``D`` em **cm** (NFPA usa cm; convertemos do mm na API)

Limitações declaradas
=====================

* Modelo ESFÉRICO sem arc-in-box correction (NFPA não fornece
  fator universal; campo aplica fator empírico 2x ou 3x quando
  apropriado).
* Não cobre DC arc com choke (e.g. baterias EV/UPS modernas com
  resistência interna não-linear).
* Tempo de clearing assumido constant; sistemas com fuse DC têm
  curva I²t mais favorável (Wilkins 2003 propõe correção).

API
===

::

    from app.standards.dc_arc_flash import dc_arc_flash_max_power

    result = dc_arc_flash_max_power(
        V_system=125.0,            # 125 V battery bank
        I_short_circuit_A=2500.0,  # bolted DC short
        arc_clearing_time_s=0.5,   # fuse total clearing
        working_distance_mm=457.0, # 18 in
    )
    print(f"E = {result.incident_energy_cal_cm2:.2f} cal/cm²")
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.core.logging_config import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Conversão de unidades
# ---------------------------------------------------------------------------


_J_PER_CAL = 4.184


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DCArcFlashResult:
    """
    Resultado do cálculo DC arc-flash via max-power method.

    Attributes
    ----------
    incident_energy_cal_cm2:
        Energia incidente na working distance, em cal/cm².
    incident_energy_J_per_cm2:
        Mesma energia, em J/cm² (cal × 4.184).
    arc_flash_boundary_mm:
        Distance from arc onde E = 1.2 cal/cm² (boundary
        para skin burn de 2nd grau).
    arc_voltage_V:
        V_arc = V_sys / 2 (max power transfer).
    arc_current_A:
        I_arc = I_sc / 2.
    method:
        "NFPA 70E §D.5 max-power".
    """

    incident_energy_cal_cm2: float
    incident_energy_J_per_cm2: float
    arc_flash_boundary_mm: float
    arc_voltage_V: float
    arc_current_A: float
    method: str = "NFPA 70E §D.5 max-power"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_inputs(
    V_system: float,
    I_short_circuit_A: float,
    arc_clearing_time_s: float,
    working_distance_mm: float,
) -> None:
    if V_system < 0:
        raise ValueError(
            f"V_system deve ser >= 0 (got {V_system})"
        )
    if I_short_circuit_A < 0:
        raise ValueError(
            f"I_short_circuit_A deve ser >= 0 "
            f"(got {I_short_circuit_A})"
        )
    if arc_clearing_time_s < 0:
        raise ValueError(
            f"arc_clearing_time_s deve ser >= 0 "
            f"(got {arc_clearing_time_s})"
        )
    if working_distance_mm <= 0:
        raise ValueError(
            f"working_distance_mm deve ser > 0 "
            f"(got {working_distance_mm})"
        )


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------


def dc_arc_flash_max_power(
    V_system: float,
    I_short_circuit_A: float,
    arc_clearing_time_s: float,
    working_distance_mm: float = 457.0,
) -> DCArcFlashResult:
    """
    Energia incidente DC via método de potência máxima
    (NFPA 70E:2024 §D.5).

    Steps
    -----

    1. ``V_arc = V_sys / 2`` (max power transfer)
    2. ``I_arc = I_sc / 2``
    3. ``P_max = V_arc · I_arc = V_sys · I_sc / 4`` (W)
    4. ``E (J/cm²) = P_max · t / (4π · D_cm²)`` — esférica
    5. ``E (cal/cm²) = E (J/cm²) / 4.184``
    6. ``D_AFB`` (arc-flash boundary onde E = 1.2 cal/cm²) =
       ``√(P_max · t / (4π · 1.2 · 4.184))`` em cm

    Parameters
    ----------
    V_system:
        Tensão DC do sistema (V).
    I_short_circuit_A:
        Corrente máxima de curto-circuito DC (A).
    arc_clearing_time_s:
        Tempo de extinção do arco em segundos.
    working_distance_mm:
        Distância de trabalho em mm (default 457 mm = 18 in).

    Returns
    -------
    :class:`DCArcFlashResult`

    Raises
    ------
    ValueError
        Inputs negativos ou distância zero.
    """
    _validate_inputs(
        V_system, I_short_circuit_A,
        arc_clearing_time_s, working_distance_mm,
    )

    # 1-3. Max power
    V_arc = V_system / 2.0
    I_arc = I_short_circuit_A / 2.0
    P_max = V_arc * I_arc   # watts

    # 4. Incident energy spherical (J/cm²)
    D_cm = working_distance_mm / 10.0
    if D_cm <= 0 or arc_clearing_time_s == 0.0 or P_max == 0.0:
        E_J_cm2 = 0.0
    else:
        E_J_cm2 = (P_max * arc_clearing_time_s) / (
            4.0 * math.pi * D_cm * D_cm
        )

    # 5. Convert to cal/cm²
    E_cal_cm2 = E_J_cm2 / _J_PER_CAL

    # 6. AFB onde E = 1.2 cal/cm² (skin burn 2º grau)
    if P_max > 0 and arc_clearing_time_s > 0:
        # 1.2 cal/cm² = 1.2 × 4.184 J/cm² = 5.0208 J/cm²
        E_threshold_J = 1.2 * _J_PER_CAL
        D_afb_cm = math.sqrt(
            (P_max * arc_clearing_time_s)
            / (4.0 * math.pi * E_threshold_J)
        )
        AFB_mm = D_afb_cm * 10.0
    else:
        AFB_mm = 0.0

    log.info(
        "DC arc-flash NFPA 70E §D.5: V_sys=%.1f V, I_sc=%.0f A, "
        "t=%.2f s, D=%.0f mm → E=%.2f cal/cm², AFB=%.0f mm",
        V_system, I_short_circuit_A,
        arc_clearing_time_s, working_distance_mm,
        E_cal_cm2, AFB_mm,
    )

    return DCArcFlashResult(
        incident_energy_cal_cm2=E_cal_cm2,
        incident_energy_J_per_cm2=E_J_cm2,
        arc_flash_boundary_mm=AFB_mm,
        arc_voltage_V=V_arc,
        arc_current_A=I_arc,
    )
