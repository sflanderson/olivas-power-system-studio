"""v3.7.1 — Branch impedance extraction (closes SKIPPED_BACKLOG B.1).

Extrai impedância (R_pu, X_pu, B_pu) de componentes Tr/sTr/Tr3/CABLE/TLIN
para uso em :func:`build_pf_system_from_project`. Substitui o
fallback default ``R=0.01, X=0.05`` por valores reais derivados das
properties do componente.

Reference
---------
* PTW Tutorial v8.0 §Part 1 p.54-58 (transformer / cable libraries)
* IEC 60076-1:2011 §10 (transformer impedance v_sc%)
* IEC 60364-5-52:2009 (cable resistance per cross-section)

Anti-alucinação
---------------
* Tr/sTr/Tr3: usa **fórmula fechada** Z_pu = (v_sc_pct/100) × (S_base/S_nom)
* CABLE: usa **resistividade tabelada IEC 60364** (Cu=1/56, Al=1/35)
* TLIN: usa params explícitos R_per_km / length

Limitações declaradas em §Anti-alucinação do handoff.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Resistivity (IEC 60364-5-52 typical values, 20°C)
RHO_CU_OHM_MM2_PER_M = 1.0 / 56.0  # Copper: 0.01786 Ω·mm²/m
RHO_AL_OHM_MM2_PER_M = 1.0 / 35.0  # Aluminum: 0.02857 Ω·mm²/m

# Typical reactance for LV cables in conduit (Ω/km)
DEFAULT_CABLE_X_PER_KM = 0.08

# Default fallback impedance (legacy v3.3.1 placeholder)
DEFAULT_BRANCH_R_PU = 0.01
DEFAULT_BRANCH_X_PU = 0.05


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BranchImpedance:
    """Branch impedance in per-unit on system base.

    Attributes
    ----------
    R_pu, X_pu, B_pu:
        Per-unit values on system MVA / kV base.
    source:
        Provenance: "transformer" / "cable" / "tline" / "default".
    """
    R_pu: float
    X_pu: float
    B_pu: float = 0.0
    source: str = "default"


# ---------------------------------------------------------------------------
# Property reading helpers
# ---------------------------------------------------------------------------


_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _parse_numeric(value: str | float | None, default: float = 0.0) -> float:
    """Parse first numeric token from a property string.

    Handles formats like:
    * "1.0"           → 1.0
    * "1.5 MVA"       → 1.5
    * "0.05 Ohm/km"   → 0.05
    * "1 mH"          → 1.0
    * "13.8 kV"       → 13.8
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return default
    m = _NUM_RE.search(s)
    if m is None:
        return default
    try:
        return float(m.group())
    except ValueError:
        return default


def _read_prop(component, name: str, default: str | float = 0.0) -> str | float:
    """Read named property value from a component, with default fallback."""
    for prop in getattr(component, "properties", []):
        if getattr(prop, "name", "") == name:
            val = getattr(prop, "value", None)
            return val if val not in (None, "") else default
    return default


# ---------------------------------------------------------------------------
# Transformer (Tr / sTr / Tr3)
# ---------------------------------------------------------------------------


def transformer_impedance_pu(
    component,
    *,
    base_MVA: float = 100.0,
) -> BranchImpedance:
    """Compute (R_pu, X_pu) from Tr/sTr/Tr3 properties.

    Per IEC 60076-1:2011 §10:
    * v_sc_pct = % short-circuit impedance on **transformer** base
    * Convert to system base: Z_pu_sys = Z_pu_xfmr × (S_base_sys / S_nom)
    * Split into R/X using p_sc_kW (load losses):
      R_pu_xfmr = p_sc_kW / (S_nom × 1000)
      X_pu_xfmr = sqrt(Z² - R²)

    Returns
    -------
    BranchImpedance
        With ``source="transformer"`` and ``B_pu=0``.

    Fallback
    --------
    If ``S_nom`` or ``v_sc_pct`` are missing/zero, returns default
    values (R=0.01, X=0.05) with ``source="default_tr_missing_data"``.
    """
    S_nom_MVA = _parse_numeric(_read_prop(component, "S_nom"))
    v_sc_pct = _parse_numeric(_read_prop(component, "v_sc_pct"))
    p_sc_kW = _parse_numeric(_read_prop(component, "p_sc_kW"))

    if S_nom_MVA <= 0 or v_sc_pct <= 0:
        return BranchImpedance(
            R_pu=DEFAULT_BRANCH_R_PU,
            X_pu=DEFAULT_BRANCH_X_PU,
            source="default_tr_missing_data",
        )

    # Z on transformer base
    Z_pu_xfmr = v_sc_pct / 100.0

    # R from copper losses (p_sc in kW; S_nom in MVA = 1000 kW)
    if p_sc_kW > 0:
        R_pu_xfmr = p_sc_kW / (S_nom_MVA * 1000.0)
    else:
        # Heuristic: typical X/R ratio ≈ 7 for power transformers
        R_pu_xfmr = Z_pu_xfmr / math.sqrt(1.0 + 49.0)
    R_pu_xfmr = min(R_pu_xfmr, Z_pu_xfmr)  # safety: R can't exceed Z
    X_pu_xfmr = math.sqrt(max(0.0, Z_pu_xfmr ** 2 - R_pu_xfmr ** 2))

    # Convert to system base
    base_ratio = base_MVA / S_nom_MVA
    R_pu = R_pu_xfmr * base_ratio
    X_pu = X_pu_xfmr * base_ratio

    return BranchImpedance(R_pu=R_pu, X_pu=X_pu, source="transformer")


# ---------------------------------------------------------------------------
# Cable
# ---------------------------------------------------------------------------


def cable_impedance_pu(
    component,
    *,
    base_MVA: float = 100.0,
    voltage_base_kV: float = 0.480,
) -> BranchImpedance:
    """Compute (R_pu, X_pu) from CABLE properties.

    Per IEC 60364-5-52:2009 typical resistance values:
    * Copper @ 20°C: ρ = 1/56 Ω·mm²/m
    * Aluminum @ 20°C: ρ = 1/35 Ω·mm²/m

    Reactance is approximated as 0.08 Ω/km (typical for LV in conduit).
    For accurate X, use spaced installations or HV cables (deferred).

    Z_base = V²_LL / S_base = (kV)² / MVA
    R_pu = R_ohm / Z_base
    """
    section_mm2 = _parse_numeric(_read_prop(component, "section_mm2"), 35.0)
    length_m = _parse_numeric(_read_prop(component, "length_m"), 30.0)
    material = str(_read_prop(component, "material", "Cu")).strip().upper()

    if section_mm2 <= 0 or length_m <= 0:
        return BranchImpedance(
            R_pu=DEFAULT_BRANCH_R_PU,
            X_pu=DEFAULT_BRANCH_X_PU,
            source="default_cable_missing_data",
        )

    # Resistivity
    if material.startswith("AL"):
        rho = RHO_AL_OHM_MM2_PER_M
    else:
        rho = RHO_CU_OHM_MM2_PER_M  # Cu default

    R_ohm = rho * length_m / section_mm2
    X_ohm = DEFAULT_CABLE_X_PER_KM * (length_m / 1000.0)

    # Convert to per-unit
    Z_base = (voltage_base_kV ** 2) / base_MVA  # Ω
    if Z_base <= 0:
        return BranchImpedance(
            R_pu=DEFAULT_BRANCH_R_PU,
            X_pu=DEFAULT_BRANCH_X_PU,
            source="default_cable_zbase_invalid",
        )

    return BranchImpedance(
        R_pu=R_ohm / Z_base,
        X_pu=X_ohm / Z_base,
        source="cable",
    )


# ---------------------------------------------------------------------------
# Transmission Line (TLIN)
# ---------------------------------------------------------------------------


def tline_impedance_pu(
    component,
    *,
    base_MVA: float = 100.0,
    voltage_base_kV: float = 138.0,
) -> BranchImpedance:
    """Compute (R_pu, X_pu) from TLIN properties.

    TLIN.ocomp expõe R_per_km e length explicitamente; usa
    diretamente. X é parametrizado via geometria (x_a/y_a/...) que
    seria refinement v3.7.x (geometric mean radius). Por ora,
    assume X = 5 × R (típico para linhas aéreas).
    """
    R_per_km = _parse_numeric(_read_prop(component, "R_per_km"), 0.05)
    # length_km — schema usa "length" string como "100 km"
    length_km = _parse_numeric(_read_prop(component, "length"), 100.0)

    if R_per_km <= 0 or length_km <= 0:
        return BranchImpedance(
            R_pu=DEFAULT_BRANCH_R_PU,
            X_pu=DEFAULT_BRANCH_X_PU,
            source="default_tline_missing_data",
        )

    R_ohm = R_per_km * length_km
    # Typical aerial line X/R ≈ 5
    X_ohm = R_ohm * 5.0

    Z_base = (voltage_base_kV ** 2) / base_MVA
    if Z_base <= 0:
        return BranchImpedance(
            R_pu=DEFAULT_BRANCH_R_PU,
            X_pu=DEFAULT_BRANCH_X_PU,
            source="default_tline_zbase_invalid",
        )

    return BranchImpedance(
        R_pu=R_ohm / Z_base,
        X_pu=X_ohm / Z_base,
        source="tline",
    )


# ---------------------------------------------------------------------------
# Dispatch by component type
# ---------------------------------------------------------------------------


def extract_branch_impedance(
    component,
    *,
    base_MVA: float = 100.0,
    voltage_base_kV: float = 13.8,
) -> BranchImpedance:
    """Top-level dispatch: read component.type and route to specific extractor.

    Component types handled:
    * ``"Tr"``, ``"sTr"``, ``"Tr3"`` → :func:`transformer_impedance_pu`
    * ``"CABLE"`` → :func:`cable_impedance_pu`
    * ``"TLIN"`` → :func:`tline_impedance_pu`
    * Anything else → default fallback (R=0.01, X=0.05)
    """
    ctype = (getattr(component, "type", "") or "").strip()
    if ctype in ("Tr", "sTr", "Tr3"):
        return transformer_impedance_pu(component, base_MVA=base_MVA)
    if ctype == "CABLE":
        return cable_impedance_pu(
            component, base_MVA=base_MVA,
            voltage_base_kV=voltage_base_kV,
        )
    if ctype == "TLIN":
        return tline_impedance_pu(
            component, base_MVA=base_MVA,
            voltage_base_kV=voltage_base_kV,
        )
    return BranchImpedance(
        R_pu=DEFAULT_BRANCH_R_PU,
        X_pu=DEFAULT_BRANCH_X_PU,
        source="default_unknown_type",
    )
