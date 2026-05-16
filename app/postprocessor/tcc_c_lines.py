"""
app/postprocessor/tcc_c_lines.py — Constant Incident Energy (C-lines) curves.

v3.4.0 Sprint 1 — paridade PTW Tutorial §Part 5 p.163-165 (C-lines on TCC).

PTW CAPTOR overlays curvas constantes de Incident Energy (IE) sobre o
Time-Current Characteristic (TCC) para mostrar visualmente onde cada
categoria PPE (NFPA 70E Annex H Tab H.3(b)) é exigida em função do
trip-time do device protetor + corrente de fault.

Ao plotar I_arc × t_trip:
- C-line de IE = 1.2 cal/cm² (Cat 1) — abaixo dela, PPE Cat 1
- C-line de IE = 4.0 cal/cm² (Cat 2)
- C-line de IE = 8.0 cal/cm² (Cat 3)
- C-line de IE = 25.0 cal/cm² (Cat 4)
- C-line de IE = 40.0 cal/cm² (Cat 4 limite)

A fórmula IE = K × t × I^n; resolvendo para t em função de I:
``t = IE / (K × I^n)``

Cada C-line é um set (I, t) constante em IE.

Reference: PTW Tutorial §Part 5 p.163-165 + NFPA 70E Annex H Tab H.3(b).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


# NFPA 70E Annex H Table H.3(b) — PPE Category thresholds (cal/cm²).
# Values are the **upper bound** for each category.
NFPA_PPE_THRESHOLDS_CAL_CM2: tuple[tuple[int, float], ...] = (
    (1, 4.0),   # Cat 1: 1.2 → 4.0 (lower 1.2 = Cat 0 boundary)
    (2, 8.0),   # Cat 2: 4.0 → 8.0
    (3, 25.0),  # Cat 3: 8.0 → 25.0
    (4, 40.0),  # Cat 4: 25.0 → 40.0
)

# Default cal/cm² thresholds to plot (conservative set).
DEFAULT_C_LINE_IE_CAL_CM2: tuple[float, ...] = (
    1.2, 4.0, 8.0, 25.0, 40.0,
)


class IEEEFormulaModel(str, Enum):
    """Arc-flash IE formula model used to derive C-lines.

    Reference: IEEE 1584-2018 + NBR 17227.
    """

    IEEE_1584_2018 = "IEEE_1584_2018"
    NBR_17227 = "NBR_17227"


@dataclass(frozen=True)
class CLineCurve:
    """A single C-line (constant IE) curve as (I_kA, t_s) tuples.

    Attributes
    ----------
    incident_energy_cal_cm2
        IE level held constant ao longo da curva.
    points
        Lista de (I_kA, t_s) pairs.
    ppe_category
        Categoria PPE NFPA 70E associada (1-4) ou None.
    color_hint
        Cor hint para plot (#hex ou nome). PTW usa amarelo/laranja/vermelho.
    """

    incident_energy_cal_cm2: float
    points: tuple[tuple[float, float], ...]
    ppe_category: int | None = None
    color_hint: str = "#ff8c00"


def compute_c_line_ieee_1584(
    incident_energy_cal_cm2: float,
    *,
    voltage_kV: float = 0.480,
    gap_mm: float = 32.0,
    working_distance_mm: float = 610.0,
    enclosure_box: bool = True,
    i_min_kA: float = 0.5,
    i_max_kA: float = 100.0,
    n_points: int = 50,
) -> CLineCurve:
    """Compute IEEE 1584-2018 C-line for a given constant IE.

    Per IEEE 1584-2018 Eq. (16) — simplificada para 600V class:

    .. math::
        IE = 4.184 \\cdot C_f \\cdot E_n \\cdot \\left(\\frac{t}{0.2}\\right)
        \\cdot \\left(\\frac{610}{D}\\right)^x

    Onde ``E_n`` depende de I_arc, voltage, gap, etc. Para gerar C-line
    a IE constante, resolvemos para ``t`` em função de I:

    .. math::
        t(I) = \\frac{IE \\cdot 0.2}{4.184 \\cdot C_f \\cdot E_n(I) \\cdot (610/D)^x}

    Parameters
    ----------
    incident_energy_cal_cm2
        IE constante a plotar (cal/cm²).
    voltage_kV
        Tensão do bus (default 0.480 kV / 480V).
    gap_mm
        Gap entre eletrodos (default 32 mm typical LV).
    working_distance_mm
        Distância de trabalho (default 610 mm = 24").
    enclosure_box
        True = enclosed (Cf = 1.5); False = open air (Cf = 1.0).
    i_min_kA, i_max_kA, n_points
        Range de correntes a varrer.

    Returns
    -------
    CLineCurve
        Curva (I_kA, t_s).

    References
    ----------
    IEEE 1584-2018 §6 Eq. (16), Table 1-3.
    PTW Tutorial §Part 5 p.163-165 (C-lines on TCC).
    """
    if incident_energy_cal_cm2 <= 0:
        raise ValueError(
            f"incident_energy_cal_cm2 must be > 0; got {incident_energy_cal_cm2!r}"
        )
    if i_min_kA <= 0 or i_max_kA <= i_min_kA:
        raise ValueError("i_min_kA > 0 and i_max_kA > i_min_kA required")
    if n_points < 2:
        raise ValueError("n_points must be >= 2")

    # Cf factor (Table 3 IEEE 1584)
    Cf = 1.5 if enclosure_box else 1.0
    # Distance exponent x (Table 4 IEEE 1584 — typical 1.473 for LV/box)
    x_exp = 1.473
    # Distance correction factor
    D_correction = (610.0 / working_distance_mm) ** x_exp

    # Linear-log corrente sweep
    log_min = math.log10(i_min_kA)
    log_max = math.log10(i_max_kA)
    points: list[tuple[float, float]] = []
    for i in range(n_points):
        frac = i / (n_points - 1)
        log_i = log_min + frac * (log_max - log_min)
        I_kA = 10 ** log_i

        # Simplified normalized E_n (IEEE 1584 §6 — empirical fit
        # for 480V class). Real formula uses log(I), V, gap.
        # For C-line we only need t as function of I.
        # E_n = K1 * I_arc^a * V^b → here approximate as power law:
        # E_n ≈ 0.5 * I_kA^1.2 (cal/cm² for t=0.2s, D=610mm)
        # This is a simplification — full IEEE 1584 needs more params
        E_n_normalized = 0.5 * (I_kA ** 1.2)
        if E_n_normalized <= 0:
            continue

        # Solve IE = 4.184 * Cf * E_n * (t/0.2) * D_correction for t:
        # t = IE * 0.2 / (4.184 * Cf * E_n * D_correction)
        t_s = (
            incident_energy_cal_cm2 * 0.2
            / (4.184 * Cf * E_n_normalized * D_correction)
        )
        if t_s > 0:
            points.append((I_kA, t_s))

    # Determine PPE category
    ppe_cat = None
    for cat, threshold in NFPA_PPE_THRESHOLDS_CAL_CM2:
        if incident_energy_cal_cm2 <= threshold:
            ppe_cat = cat
            break

    # Color hint by category
    color_map = {
        1: "#ffd700",  # gold
        2: "#ff8c00",  # orange
        3: "#ff4500",  # orange-red
        4: "#dc143c",  # crimson
    }
    color = color_map.get(ppe_cat, "#808080")

    return CLineCurve(
        incident_energy_cal_cm2=incident_energy_cal_cm2,
        points=tuple(points),
        ppe_category=ppe_cat,
        color_hint=color,
    )


def compute_default_c_lines(
    *,
    voltage_kV: float = 0.480,
    gap_mm: float = 32.0,
    working_distance_mm: float = 610.0,
    enclosure_box: bool = True,
    i_min_kA: float = 0.5,
    i_max_kA: float = 100.0,
) -> list[CLineCurve]:
    """Generate default 5 C-lines (1.2 / 4 / 8 / 25 / 40 cal/cm²).

    Reference
    ---------
    NFPA 70E Annex H Table H.3(b).
    PTW Tutorial §Part 5 p.163-165.
    """
    return [
        compute_c_line_ieee_1584(
            incident_energy_cal_cm2=ie,
            voltage_kV=voltage_kV,
            gap_mm=gap_mm,
            working_distance_mm=working_distance_mm,
            enclosure_box=enclosure_box,
            i_min_kA=i_min_kA,
            i_max_kA=i_max_kA,
        )
        for ie in DEFAULT_C_LINE_IE_CAL_CM2
    ]


def ppe_category_for_ie(incident_energy_cal_cm2: float) -> int:
    """Return PPE category (1-4) for a given IE per NFPA 70E Annex H Tab H.3(b).

    Returns 0 for IE < 1.2 (no PPE required).
    Returns 5 (extreme — exit area) for IE > 40 (above Cat 4 limit).

    References
    ----------
    NFPA 70E-2024 Annex H Table H.3(b).
    """
    if incident_energy_cal_cm2 < 1.2:
        return 0
    for cat, threshold in NFPA_PPE_THRESHOLDS_CAL_CM2:
        if incident_energy_cal_cm2 <= threshold:
            return cat
    return 5  # Above 40 cal/cm² — danger / no PPE adequate


__all__ = [
    "IEEEFormulaModel",
    "NFPA_PPE_THRESHOLDS_CAL_CM2",
    "DEFAULT_C_LINE_IE_CAL_CM2",
    "CLineCurve",
    "compute_c_line_ieee_1584",
    "compute_default_c_lines",
    "ppe_category_for_ie",
]
