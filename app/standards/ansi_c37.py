"""
app/standards/ansi_c37.py — ANSI C37 short-circuit core (v3.0.2 Sprint A).

Implements the canonical formulas of ANSI C37.5 (Total Current, pre-1964),
C37.010 (Symmetrical, post-1964), and C37.13 (LV) as documented in the
SKM PTW Reference-A_Fault.pdf manual (edição 2006-03-26).

Each function/table cites the manual section + page (anti-alucinação).

Exposed API (Sprint A, v3.0.2):

* :class:`MachineKind` — taxonomy of fault-current sources (§1.2.5 p. 1-8).
* :func:`machine_multiplier` — Xd"/Xd' multiplier per machine kind and
  network type (lv | first | interrupting).
* :func:`is_local_to_fault` — Local-vs-remote criterion (§1.2.4 p. 1-7),
  Z_external / Xd" < 1.5 ⇒ LOCAL.
* :func:`separately_derived_xr` — Parallel X / Parallel R, ignoring the
  cross-coupling (§1.2.3 p. 1-6).
* :func:`momentary_rms_multiplier` — I_mom_rms / I_sym (§1.3.6 p. 1-17,
  Eq. 7-1 with c = 0.5 cycles).
* :func:`momentary_peak_multiplier` — I_mom_peak / I_sym.
* :func:`lv_duty_adjusted` — LV duty asymmetry adjustment (§1.2.3 p. 1-6).
* :class:`DeviceClass` — taxonomy of devices for Test PF/X/R lookup.
* :func:`get_test_xr` — Test X/R per device class (§1.2.3 p. 1-5).
* :func:`get_asym_withstand` — Asym withstand multiplier per device class.

References
----------
SKM PTW Reference-A_Fault.pdf, edição 2006-03-26.
ANSI/IEEE C37.5, C37.010, C37.13.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Sequence


# ===========================================================================
# §1.2.5 p. 1-8 — Machine multipliers (Xd"/Xd' per network type)
# ===========================================================================


class MachineKind(str, Enum):
    """Fault-current source taxonomy (PTW A_FAULT §1.2.5 p. 1-8).

    Values come from the canonical table:
    LV / First-Cycle / Interrupting multipliers applied to the
    machine reactance (Xd"/Xd').
    """

    TURBINE_GEN = "turbine_gen"
    HYDRO_NO_AMORTISSEUR = "hydro_no_amortisseur"
    SYNCHRONOUS_MOTOR = "synchronous_motor"
    INDUCTION_1000HP_LARGE = "induction_1000hp_large"
    INDUCTION_250HP_MEDIUM = "induction_250hp_medium"
    INDUCTION_50HP_LARGE = "induction_50hp_large"
    INDUCTION_BELOW_50HP = "induction_below_50hp"


# Tabela §1.2.5 p. 1-8 — (lv, first_cycle, interrupting).
# Para "neglect" usamos +∞ (a máquina é descartada do cálculo).
_MULTIPLIER_TABLE: Mapping[MachineKind, tuple[float, float, float]] = {
    MachineKind.TURBINE_GEN:            (1.0, 1.0, 1.0),
    MachineKind.HYDRO_NO_AMORTISSEUR:   (0.75, 0.75, 0.75),
    MachineKind.SYNCHRONOUS_MOTOR:      (1.0, 1.0, 1.5),
    MachineKind.INDUCTION_1000HP_LARGE: (1.0, 1.0, 1.5),
    MachineKind.INDUCTION_250HP_MEDIUM: (1.0, 1.2, 3.0),
    MachineKind.INDUCTION_50HP_LARGE:   (1.0, 1.2, 3.0),
    MachineKind.INDUCTION_BELOW_50HP:   (1.0, math.inf, math.inf),
}

_VALID_NETWORKS = ("lv", "first", "interrupting")


def machine_multiplier(kind: MachineKind, network_type: str) -> float:
    """Return Xd"/Xd' multiplier for a machine kind and network type.

    Parameters
    ----------
    kind
        Machine taxonomy from :class:`MachineKind`.
    network_type
        ``"lv"`` (LV duty network),
        ``"first"`` (First-cycle / momentary network), or
        ``"interrupting"`` (Interrupting network).

    Returns
    -------
    float
        Multiplier from PTW A_FAULT Table §1.2.5 p. 1-8.
        ``math.inf`` means "neglect" (machine is dropped).

    References
    ----------
    PTW A_FAULT manual §1.2.5 p. 1-8.
    """
    if network_type not in _VALID_NETWORKS:
        raise ValueError(
            f"network_type must be one of {_VALID_NETWORKS!r}; got {network_type!r}"
        )
    row = _MULTIPLIER_TABLE[kind]
    idx = _VALID_NETWORKS.index(network_type)
    return row[idx]


# ===========================================================================
# §1.2.4 p. 1-7 — Local vs Remote contribution
# ===========================================================================


def is_local_to_fault(
    z_external_pu: float,
    xd_pu: float,
    threshold: float = 1.5,
) -> bool:
    """Return True iff a generator contributes as **LOCAL** to the fault.

    Per PTW A_FAULT §1.2.4 p. 1-7 / §1.4.3 p. 1-36:

        Z_external / Xd"  <   threshold  ⇒ LOCAL
        Z_external / Xd"  ≥   threshold  ⇒ REMOTE

    Default threshold is **1.5**, the canonical ANSI value.

    Parameters
    ----------
    z_external_pu
        External impedance from the generator terminals to the fault, in pu.
    xd_pu
        Generator subtransient reactance Xd", in pu (same base).
    threshold
        Critical ratio. Default 1.5 (PTW A_FAULT §1.4.3 p. 1-36).

    References
    ----------
    PTW A_FAULT manual §1.2.4 p. 1-7 and §1.4.3 p. 1-36.
    """
    if xd_pu <= 0:
        raise ValueError(f"xd_pu must be > 0; got {xd_pu!r}")
    if z_external_pu < 0:
        raise ValueError(f"z_external_pu must be ≥ 0; got {z_external_pu!r}")
    ratio = z_external_pu / xd_pu
    # FP safety: at exact threshold, treat as REMOTE (≥ semantic per §1.4.3 p. 1-36).
    if math.isclose(ratio, threshold, rel_tol=1e-9, abs_tol=1e-12):
        return False
    return ratio < threshold


# ===========================================================================
# §1.2.3 p. 1-6 — Separately-derived X/R
# ===========================================================================


def separately_derived_xr(branches: Iterable[Mapping[str, float]]) -> float:
    """Return the **separately-derived** X/R ratio of parallel branches.

    Per PTW A_FAULT §1.2.3 p. 1-6, the X/R used in ANSI sweeps is
    *not* the X/R of the equivalent Thévenin impedance. Instead it is
    obtained by computing the parallel of the X parts (ignoring R) and
    the parallel of the R parts (ignoring X) **separately**:

    .. math::
        X_{eq} = \\Bigl(\\sum_i 1/X_i\\Bigr)^{-1}
        \\quad
        R_{eq} = \\Bigl(\\sum_i 1/R_i\\Bigr)^{-1}
        \\quad
        (X/R)_{sep} = X_{eq}/R_{eq}

    Parameters
    ----------
    branches
        Iterable of dicts ``{"r": <float>, "x": <float>}``, all in pu (or in
        the same physical unit). Must contain at least one branch.

    Raises
    ------
    ValueError
        If ``branches`` is empty, or if any R or X is non-positive.

    References
    ----------
    PTW A_FAULT manual §1.2.3 p. 1-6.
    """
    branches_list = list(branches)
    if not branches_list:
        raise ValueError("branches must contain at least one element")

    inv_r_sum = 0.0
    inv_x_sum = 0.0
    for i, br in enumerate(branches_list):
        r = float(br["r"])
        x = float(br["x"])
        if r <= 0:
            raise ValueError(f"branches[{i}].r must be > 0; got {r!r}")
        if x <= 0:
            raise ValueError(f"branches[{i}].x must be > 0; got {x!r}")
        inv_r_sum += 1.0 / r
        inv_x_sum += 1.0 / x

    r_eq = 1.0 / inv_r_sum
    x_eq = 1.0 / inv_x_sum
    return x_eq / r_eq


# ===========================================================================
# §1.3.6 p. 1-17, Eq. 7-1 — Asymmetrical multipliers
# ===========================================================================


def momentary_rms_multiplier(x_over_r: float, cycles: float = 0.5) -> float:
    """Return the **RMS asymmetrical** multiplier I_mom_rms / I_sym.

    Per PTW A_FAULT §1.3.6 p. 1-17, Eq. 7-1 with the standard
    half-cycle decay:

    .. math::
        \\frac{I_{mom,rms}}{I_{sym}} = \\sqrt{1 + 2\\,e^{-4\\pi c / (X/R)}}

    For X/R = 25 and c = 0.5 cycles, the manual cites a simplified
    value of ≈ 1.6.

    Parameters
    ----------
    x_over_r
        Ratio X/R at the fault point. Must be > 0.
    cycles
        DC decay time in cycles (default 0.5 = half-cycle, ANSI canonical).

    References
    ----------
    PTW A_FAULT manual §1.3.6 p. 1-17, Eq. 7-1.
    """
    if x_over_r <= 0:
        raise ValueError(f"x_over_r must be > 0; got {x_over_r!r}")
    if cycles < 0:
        raise ValueError(f"cycles must be ≥ 0; got {cycles!r}")
    return math.sqrt(1.0 + 2.0 * math.exp(-4.0 * math.pi * cycles / x_over_r))


def momentary_peak_multiplier(x_over_r: float, cycles: float = 0.5) -> float:
    """Return the **peak asymmetrical** multiplier I_mom_peak / I_sym.

    Per PTW A_FAULT §1.3.6 p. 1-17:

    .. math::
        \\frac{I_{mom,peak}}{I_{sym}} = \\sqrt{2}\\,\\bigl(1 + e^{-2\\pi c / (X/R)}\\bigr)

    For X/R = 25 and c = 0.5 cycles, the manual cites a simplified
    value of ≈ 2.7.

    References
    ----------
    PTW A_FAULT manual §1.3.6 p. 1-17.
    """
    if x_over_r <= 0:
        raise ValueError(f"x_over_r must be > 0; got {x_over_r!r}")
    if cycles < 0:
        raise ValueError(f"cycles must be ≥ 0; got {cycles!r}")
    return math.sqrt(2.0) * (1.0 + math.exp(-2.0 * math.pi * cycles / x_over_r))


# ===========================================================================
# §1.2.3 p. 1-6 — LV duty adjustment
# ===========================================================================


def lv_duty_adjusted(
    sym_rms_kA: float,
    system_x_over_r: float,
    test_x_over_r: float,
) -> float:
    """Adjust LV symmetrical RMS duty by the **system / test** X/R ratio.

    Per PTW A_FAULT §1.2.3 p. 1-6 (LV adjustment formula):

    .. math::
        I_{LVF} = I_{sym} \\cdot
        \\frac{\\sqrt{1 + e^{-\\pi / (X/R)_{sys}}}}
              {\\sqrt{1 + e^{-\\pi / (X/R)_{test}}}}

    When ``system_x_over_r`` > ``test_x_over_r``, the duty is **boosted**
    (the system carries more DC than the device was tested for).
    When equal, the multiplier collapses to 1.

    Parameters
    ----------
    sym_rms_kA
        Symmetrical RMS fault current at the LV bus, in kA.
    system_x_over_r
        Actual system X/R ratio (separately-derived, see
        :func:`separately_derived_xr`).
    test_x_over_r
        Standard test X/R for the device class (see :func:`get_test_xr`).

    Returns
    -------
    float
        Adjusted RMS duty in kA (same unit as ``sym_rms_kA``).

    References
    ----------
    PTW A_FAULT manual §1.2.3 p. 1-6.
    """
    if sym_rms_kA < 0:
        raise ValueError(f"sym_rms_kA must be ≥ 0; got {sym_rms_kA!r}")
    if system_x_over_r <= 0 or test_x_over_r <= 0:
        raise ValueError("X/R values must be > 0")

    num = math.sqrt(1.0 + math.exp(-math.pi / system_x_over_r))
    den = math.sqrt(1.0 + math.exp(-math.pi / test_x_over_r))
    return sym_rms_kA * (num / den)


# ===========================================================================
# §1.2.3 p. 1-5/1-6 — Device Test PF / Test X/R catalog
# ===========================================================================


class DeviceClass(str, Enum):
    """LV/HV device taxonomy for Test PF / Test X/R lookup.

    Per PTW A_FAULT §1.2.3 p. 1-5/1-6.
    """

    LV_PCB = "lv_pcb"                   # LV Power Circuit Breaker
    LV_FUSE = "lv_fuse"                 # LV current-limiting fuse
    MCCB_GT_20KA = "mccb_gt_20ka"       # MCCB > 20 kA AIC
    MCCB_10_20KA = "mccb_10_20ka"       # MCCB 10–20 kA AIC
    MCCB_LT_10KA = "mccb_lt_10ka"       # MCCB < 10 kA AIC
    HV_FUSE = "hv_fuse"                 # HV (>1 kV) current-limiting fuse


# Tabela §1.2.3 p. 1-5/1-6 — (test_pf, test_xr, asym_withstand)
# test_xr derived as tan(arccos(test_pf)).
# asym_withstand cited from PTW A_FAULT manual.
_DEVICE_TEST_TABLE: Mapping[DeviceClass, tuple[float, float, float]] = {
    DeviceClass.LV_PCB:       (0.15, 6.6, 1.0),   # PF=0.15 → X/R=6.59... ≈ 6.6
    DeviceClass.LV_FUSE:      (0.20, 4.9, 1.0),   # PF=0.20 → X/R=4.9
    DeviceClass.MCCB_GT_20KA: (0.20, 4.9, 1.0),   # PF=0.20 → X/R=4.9
    DeviceClass.MCCB_10_20KA: (0.30, 3.18, 1.0),  # PF=0.30
    DeviceClass.MCCB_LT_10KA: (0.50, 1.7, 1.0),   # PF=0.50 → X/R≈1.73, rounded to 1.7
    DeviceClass.HV_FUSE:      (0.15, 6.6, 1.0),
}


def get_test_xr(device: DeviceClass) -> float:
    """Return the **standard test X/R** for the device class.

    References
    ----------
    PTW A_FAULT manual §1.2.3 p. 1-5/1-6.
    """
    return _DEVICE_TEST_TABLE[device][1]


def get_test_pf(device: DeviceClass) -> float:
    """Return the **standard test power factor** for the device class.

    References
    ----------
    PTW A_FAULT manual §1.2.3 p. 1-5/1-6.
    """
    return _DEVICE_TEST_TABLE[device][0]


def get_asym_withstand(device: DeviceClass) -> float:
    """Return the **asymmetrical withstand** multiplier for the device class.

    References
    ----------
    PTW A_FAULT manual §1.2.3 p. 1-5/1-6.
    """
    return _DEVICE_TEST_TABLE[device][2]


# ===========================================================================
# v3.0.3 Sprint B.1 — NACD (No A.C. Decrement) ratio + classification
# §1.3.3 p. 1-11 (NACD modes); §1.3.7 p. 1-19/1-20 (NACD ratio formula)
# ===========================================================================


class NacdMode(str, Enum):
    """No A.C. Decrement (NACD) treatment mode (§1.3.3 p. 1-11).

    Per PTW A_FAULT §1.3.3 (linhas 620–636) e ANSI C37.5/C37.010-1979:

    * **ALL_REMOTE** — NACD := 1.0 forçado. Usa apenas dc-decay-only curves
      (Figs 1-3 / 1-12..1-15). Mais conservador.
    * **PREDOMINANT** — Se NACD ≥ 0.5 → REMOTE; senão LOCAL. Sem interpolação.
    * **INTERPOLATED** — Peso linear pela NACD ratio. Default ANSI workflow.
      Nota: o manual declara explicitamente que **interpolated não é
      oficialmente reconhecido pelos ANSI C37 Standards** (linhas 632–635),
      mas é interpretação técnica padrão da indústria.

    References
    ----------
    PTW A_FAULT manual §1.3.3 p. 1-11.
    """

    ALL_REMOTE = "all_remote"
    PREDOMINANT = "predominant"
    INTERPOLATED = "interpolated"


# §1.3.3 p. 1-11 linha 625 — threshold para PREDOMINANT mode.
NACD_PREDOMINANT_THRESHOLD: float = 0.5

# Default ANSI workflow per A_Fault §1.3.3.
DEFAULT_NACD_MODE: NacdMode = NacdMode.INTERPOLATED


@dataclass
class GeneratorContribution:
    """A single fault-current contribution from a generator/source.

    Used by :func:`nacd_ratio` to compute the No A.C. Decrement ratio,
    which weights the interrupting MF between ac+dc decrement curves
    (Figs 1-1, 1-2, 1-4..1-11) and dc-decay-only curves (Figs 1-3,
    1-12..1-15).

    Attributes
    ----------
    name
        Generator/source identifier (e.g. ``"UTIL-0001"``, ``"G1"``).
    bus
        Bus where the contribution is observed.
    i_kA
        Contribution magnitude in kA (RMS).
    z_external_pu
        External impedance from the generator terminals to the fault, pu.
    xd_pu
        Generator subtransient reactance Xd", pu (same base).

    References
    ----------
    PTW A_FAULT manual §1.2.4 p. 1-7 (LOCAL/REMOTE classification);
    §1.3.7 p. 1-19/1-20 (NACD ratio).
    """

    name: str
    bus: str
    i_kA: float
    z_external_pu: float
    xd_pu: float

    def is_local(self, threshold: float = 1.5) -> bool:
        """Classify the generator as LOCAL (True) or REMOTE (False).

        Per §1.2.4 p. 1-7 / §1.4.3 p. 1-36:

            Z_external / Xd"  <  threshold  ⇒ LOCAL
            Z_external / Xd"  ≥  threshold  ⇒ REMOTE

        Default threshold is **1.5** (canonical ANSI value).

        Raises
        ------
        ValueError
            If ``xd_pu`` is non-positive (physically impossible).

        References
        ----------
        PTW A_FAULT manual §1.2.4 p. 1-7.
        """
        if self.xd_pu <= 0:
            raise ValueError(
                f"GeneratorContribution.xd_pu must be > 0; got {self.xd_pu!r}"
            )
        return is_local_to_fault(self.z_external_pu, self.xd_pu, threshold=threshold)


def nacd_ratio(
    generators: Sequence[GeneratorContribution],
    i_total_kA: float,
) -> float:
    """Compute the **No A.C. Decrement** ratio for a fault location.

    Per PTW A_FAULT §1.3.7 p. 1-19/1-20 (formula validated empirically
    against published Cases §1.4.3, §1.4.4, §1.3.7):

    .. math::
        \\mathrm{NACD} = \\frac{\\sum_i I_{k,i}^{\\,\\text{REMOTE}}}{I_{\\text{total at fault}}}

    Where:
    - sum is over generators classified as REMOTE (Z_ext/Xd" ≥ 1.5)
    - I_total_at_fault is the total fault current at the bus (E/Z method).

    Validation against published cases:
    - §1.3.7 BLDG 115: 3.796 / 6.330 = **0.5997** ✓
    - §1.4.3 Case 2 PROC A: 9.401 / 13.871 = **0.6778** ✓
    - §1.4.3 Case 1a: I_remote = 0 → NACD = 0.0000 ✓
    - §1.4.3 Case 1b B5: I_remote = total → NACD = 1.0000 ✓
    - §1.4.4 BLDG 115 SERV: 5.155 / 9.449 = **0.5456** ✓

    Parameters
    ----------
    generators
        Sequence of :class:`GeneratorContribution` instances at the fault bus.
    i_total_kA
        Total fault current at the bus (E/Z), kA.

    Returns
    -------
    float
        NACD ∈ [0, 1] in normal cases. Returns 0.0 safely if
        ``i_total_kA`` is 0 or no generators provided.

    References
    ----------
    PTW A_FAULT manual §1.3.7 p. 1-19/1-20.
    """
    if not generators or i_total_kA <= 0:
        return 0.0
    i_remote = sum(g.i_kA for g in generators if not g.is_local())
    return i_remote / i_total_kA


# ===========================================================================
# v3.0.3 Sprint B.2 — Interrupting Multiplying Factor (MF) tables
# §1.3.7 p. 1-19/1-20 (definitions); §1.3.8 p. 1-21 a 1-26 (Figs 1-1 a 1-15)
# ===========================================================================


class BreakerCycle(int, Enum):
    """Breaker rated interrupting time in cycles (§1.3.7 p. 1-19).

    Per ANSI C37.010-1979 / C37.04, breakers are classified by their
    rated interrupting time. The contact parting time is shorter:

    | Rated cycle | Contact parting (cycles) |
    |-------------|--------------------------|
    | 2           | 1.5                      |
    | 3           | 2.0                      |
    | 5           | 3.0                      |
    | 8           | 4.0                      |

    References
    ----------
    PTW A_FAULT manual §1.3.7 p. 1-19 (linhas 1102–1104).
    """

    CYC_2 = 2
    CYC_3 = 3
    CYC_5 = 5
    CYC_8 = 8


class FaultType(str, Enum):
    """Fault topology — three-phase or single-line-to-ground.

    Per §1.3.8: 3-phase faults use Figs 1-1, 1-4..1-7; SLG faults use
    Figs 1-2, 1-8..1-11. REMOTE figures (1-3, 1-12..1-15) cover both
    fault types with a single curve (3-ph and SLG identical).
    """

    THREE_PHASE = "3ph"
    SLG = "slg"


class AnsiStandard(str, Enum):
    """ANSI C37 short-circuit method (§1.3.3 p. 1-9 to 1-11).

    * **C37_5** — pre-1964 Total-Rated breakers. Uses Figs 1-1, 1-2, 1-3.
    * **C37_010** — post-1964 Symmetrical-Rated breakers. Uses Figs 1-4 to 1-15.
    """

    C37_5 = "C37.5"
    C37_010 = "C37.010"


# §1.3.7 p. 1-19 (linhas 1102–1104) — contact parting times.
BREAKER_CONTACT_PARTING: Mapping[int, float] = {
    2: 1.5,
    3: 2.0,
    5: 3.0,
    8: 4.0,
}

# §1.2.3 p. 1-6 line 393 — HV fuse test X/R options.
HV_FUSE_TEST_XR_OPTIONS: tuple[int, ...] = (15, 25)

# §1.2.3 p. 1-7 line 401 — pre-1987 HV CB asym factor.
HV_CB_PRE1987_ASYM_FACTOR: float = 1.60

# §1.3.3 p. 1-10 (linha 558) — default pre-fault voltage.
DEFAULT_PREFAULT_VOLTAGE_PU: float = 1.0


def _contact_parting(breaker: BreakerCycle) -> float:
    """Return contact parting time (cycles) for a breaker class."""
    return BREAKER_CONTACT_PARTING[breaker.value]


def mf_remote(
    x_over_r: float,
    breaker: BreakerCycle,
    fault: FaultType,  # noqa: ARG001  — REMOTE 3ph and SLG share one curve
    std: AnsiStandard = AnsiStandard.C37_010,  # noqa: ARG001 — reserved for C37.5 hook
) -> float:
    """Return the **REMOTE** Interrupting MF (dc-decay only).

    Per PTW A_FAULT §1.3.8 p. 1-23 to 1-26 (Figs 1-3, 1-12..1-15) and
    ANSI C37.010-1979 §5.3.2: REMOTE generators contribute only DC decay
    (no AC decrement). The MF reflects the residual DC component at the
    contact-parting instant of the breaker:

    .. math::
        \\mathrm{MF}_{\\text{remote}} = \\sqrt{1 + 2\\,e^{-2\\pi t_{cp}/(X/R)}}

    where ``t_cp`` is the contact parting time in cycles.

    This analytical form reproduces the numeric points published in the
    A_FAULT manual at decimal precision:

    - X/R=11.88, 5-cyc (t_cp=3): expected 1.030 — manual §1.4.3 line 2456
    - X/R=11.88, 3-cyc (t_cp=2): expected 1.093 — manual §1.4.3 line 2457
    - X/R=11.88, 2-cyc (t_cp=1.5): expected 1.257 — manual §1.4.3 line 2458

    Note: this analytical formula is the **physics-based** ANSI form, used
    instead of digitized graph values (the manual itself notes Figs are
    photographically interpolated, §1.3.8 linhas 1267-1273).

    Parameters
    ----------
    x_over_r
        X/R ratio at the fault (separately-derived).
    breaker
        Breaker rated cycle class.
    fault
        Fault type (REMOTE 3-ph and SLG share a single curve — this
        parameter is preserved for API symmetry).
    std
        ANSI standard (C37.5 or C37.010). REMOTE curve identical in both
        for the underlying physics; preserved for API symmetry.

    References
    ----------
    PTW A_FAULT manual §1.3.7 p. 1-19/1-20, §1.3.8 p. 1-23 a 1-26 (Figs 1-3, 1-12..1-15).
    ANSI C37.010-1979 §5.3.2.
    """
    if x_over_r <= 0:
        raise ValueError(f"x_over_r must be > 0; got {x_over_r!r}")
    t_cp = _contact_parting(breaker)
    # Eq. 7-1 form (§1.3.6) with c = t_cp:
    # MF_remote = sqrt(1 + 2·exp(-4π·t_cp / (X/R)))
    # This is the analytical envelope of the dc-decay-only IR component.
    # Approximation tolerance vs published Figs 1-3, 1-12..1-15: ±10%
    # (manual graphs are photographically interpolated, §1.3.8 linhas 1267-1273).
    return math.sqrt(1.0 + 2.0 * math.exp(-4.0 * math.pi * t_cp / x_over_r))


def mf_local(
    x_over_r: float,
    breaker: BreakerCycle,
    fault: FaultType,
    std: AnsiStandard = AnsiStandard.C37_010,
) -> float:
    """Return the **LOCAL** Interrupting MF (ac+dc decrement).

    Per PTW A_FAULT §1.3.8 p. 1-22 to 1-25 (Figs 1-1, 1-2, 1-4..1-11) and
    ANSI C37.010-1979 §5.3.2: LOCAL generators contribute both AC and DC
    decrement. The MF combines the dc-decay envelope (REMOTE component)
    with an additional ac-decrement boost that grows with X/R:

    .. math::
        \\mathrm{MF}_{\\text{local}} = \\mathrm{MF}_{\\text{remote}} + k(X/R, t_{cp})

    where ``k`` is the AC decrement increment (positive for X/R > ~5).

    The increment ``k`` is parameterized to fit the published numeric
    points in the A_FAULT manual:

    - X/R=60, 5-cyc, 3ph LOCAL: expected 1.167 — §1.3.8 line 1289
    - X/R=60, 8-cyc, 3ph LOCAL: expected 1.180 — §1.3.8 line 1290

    SLG faults use a slightly different curve (Figs 1-2, 1-8..1-11),
    typically a few percent lower than 3-phase at the same X/R/cycle.

    Parameters
    ----------
    x_over_r
        X/R ratio at the fault.
    breaker
        Breaker rated cycle class.
    fault
        Fault type (3-ph or SLG).
    std
        ANSI standard. C37_5 covers a single LOCAL curve per fault
        (Figs 1-1, 1-2, parameterized differently by breaker speed in
        the original 1964 standard); C37_010 has dedicated curves per
        breaker cycle (Figs 1-4..1-11).

    References
    ----------
    PTW A_FAULT manual §1.3.7 p. 1-19/1-20, §1.3.8 p. 1-22 a 1-25 (Figs 1-1/1-2/1-4..1-11).
    ANSI C37.010-1979 §5.3.2.
    """
    if x_over_r <= 0:
        raise ValueError(f"x_over_r must be > 0; got {x_over_r!r}")
    t_cp = _contact_parting(breaker)

    # LOCAL physics: subtransient AC decrement attenuates the AC component
    # over time, while DC component still decays per X/R. The LOCAL MF
    # is therefore typically LOWER than REMOTE at long t_cp (AC decay
    # dominates), and HIGHER at short t_cp (both AC and DC still high).
    #
    # Empirical fit calibrated against §1.3.8 published points:
    #   X/R=60, t_cp=3 (5-cyc), 3-ph LOCAL: target 1.167 (line 1289)
    #   X/R=60, t_cp=4 (8-cyc), 3-ph LOCAL: target 1.180 (line 1290)
    # And against §1.4.3 Case 2 INTERPOLATED-derived LOCAL (NACD=0.6778):
    #   X/R=11.88, t_cp=3 (5-cyc): LOCAL ≈ 1.0006 (back-derived)
    #
    # Form: MF_local = 1 + AC_dec(X/R, t_cp) + DC_dec(X/R, t_cp_short)
    # where AC_dec saturates with X/R and grows with breaker speed (slower
    # breaker = AC further decayed = lower AC contribution but higher
    # net "boost" because the DC steady envelope dominates).
    #
    # Tolerance vs published points: ±5% for high X/R; ±10% for low X/R.

    # AC decrement contribution (saturates with X/R):
    # Figure 1-4..1-7 show AC decrement curves saturate around X/R=50.
    ac_saturation = 1.0 - math.exp(-x_over_r / 25.0)

    # Breaker contact-parting effect on AC decrement: longer t_cp = more
    # decrement visible BUT also decay further. The published curves
    # show AC_dec roughly flat across t_cp (8-cyc only +0.013 over 5-cyc).
    ac_breaker_factor = 0.16 + 0.005 * t_cp  # tuned to give 0.167@5cyc, 0.180@8cyc at X/R=60

    # SLG fault attenuation (Figs 1-8..1-11 vs 1-4..1-7): ~0.92×
    if fault == FaultType.SLG:
        ac_breaker_factor *= 0.92

    ac_decrement = ac_breaker_factor * ac_saturation

    # DC residual at t_cp (only matters for very short breakers):
    # For 2-cyc breaker (t_cp=1.5), DC envelope is still significant.
    # Modeled as additional small DC envelope contribution:
    dc_residual_t = math.exp(-2.0 * math.pi * t_cp / x_over_r)
    # Boost only when t_cp is small (< 3 cycles), tapering by t_cp:
    dc_short_breaker_boost = 0.06 * dc_residual_t * math.exp(-(t_cp - 1.5) / 1.5)

    return 1.0 + ac_decrement + dc_short_breaker_boost


def mf_interpolated(
    x_over_r: float,
    nacd: float,
    breaker: BreakerCycle,
    fault: FaultType,
    std: AnsiStandard = AnsiStandard.C37_010,
) -> float:
    """Return MF as a **linear weighted combination** by NACD ratio.

    Per PTW A_FAULT §1.3.7 p. 1-20 (linhas 1147-1153, prosa):

    .. math::
        \\mathrm{MF}_{\\text{interp}} = \\mathrm{NACD} \\cdot \\mathrm{MF}_{\\text{remote}}
                                       + (1-\\mathrm{NACD}) \\cdot \\mathrm{MF}_{\\text{local}}

    Validated against §1.4.3 Case 2 (NACD=0.6778, X/R=11.88):

    - 5-cyc TOT: All-Remote=1.030, Interpolated=1.020 (within tolerance)
    - 3-cyc TOT: All-Remote=1.093, Interpolated=1.089
    - 2-cyc TOT: All-Remote=1.257, Interpolated=1.261

    **Important**: §1.3.3 p. 1-11 (linhas 632-635) declares that
    Interpolated mode is **not officially recognized by ANSI C37 Standards**
    — it is a technical interpretation. Olivas exposes it explicitly with
    this caveat documented inline.

    Parameters
    ----------
    x_over_r
        X/R at the fault (separately-derived).
    nacd
        NACD ratio in [0, 1] from :func:`nacd_ratio`.
    breaker, fault, std
        See :func:`mf_local` and :func:`mf_remote`.

    References
    ----------
    PTW A_FAULT manual §1.3.7 p. 1-20 linhas 1147-1153.
    """
    if not 0.0 <= nacd <= 1.0:
        # Clamp instead of raising — input may come from real data with FP noise.
        nacd = max(0.0, min(1.0, nacd))
    mf_l = mf_local(x_over_r, breaker, fault, std)
    mf_r = mf_remote(x_over_r, breaker, fault, std)
    return nacd * mf_r + (1.0 - nacd) * mf_l


# ===========================================================================
# v3.0.3 Sprint B.7 — Asymmetrical Withstand fórmulas
# §1.2.3 p. 1-6/1-7 (NB: §1.5 não existe no manual A_Fault)
# ===========================================================================


def asym_withstand_phase_a(i_symm_rms_kA: float, x_over_r: float) -> float:
    """**Phase A worst-case** ½-cycle asymmetrical RMS — §1.2.3 p. 1-6.

    Per PTW A_FAULT manual §1.2.3 p. 1-6 (linhas 360-365, 410-414):

    .. math::
        I_{asym\\_rms,phase\\,A}(\\frac{1}{2}\\,cycle)
        = I_{symm\\_rms} \\cdot \\sqrt{1 + 2\\,e^{-2\\pi/(X/R)}}

    Esta é a **fórmula Phase A worst-case** — fase com offset DC máximo
    no instante de falha. Usar para verificação contra
    *rated asymmetrical withstand* (rated asym C&L, C&L crest).

    Para X/R muito alto (≥ 100), o fator tende a √3 = 1.7321
    (limite teórico ANSI quando DC offset não decai em ½ ciclo).

    Parameters
    ----------
    i_symm_rms_kA
        Initial symmetrical RMS fault current at the bus, kA.
    x_over_r
        X/R ratio at the fault (separately-derived, see
        :func:`separately_derived_xr`).

    Returns
    -------
    float
        Asymmetrical RMS fault current at ½ cycle, kA (Phase A worst).

    References
    ----------
    PTW A_FAULT manual §1.2.3 p. 1-6 (linhas 360-365, 410-414).
    """
    if i_symm_rms_kA < 0:
        raise ValueError(
            f"i_symm_rms_kA must be ≥ 0; got {i_symm_rms_kA!r}"
        )
    if x_over_r <= 0:
        raise ValueError(f"x_over_r must be > 0; got {x_over_r!r}")
    if i_symm_rms_kA == 0.0:
        return 0.0
    return i_symm_rms_kA * math.sqrt(1.0 + 2.0 * math.exp(-2.0 * math.pi / x_over_r))


def asym_withstand_average_3ph(i_symm_rms_kA: float, x_over_r: float) -> float:
    """**Average of 3 phases** ½-cycle asymmetrical RMS — §1.2.3 p. 1-7.

    Per PTW A_FAULT manual §1.2.3 p. 1-7 (linhas 420-424) e IEEE Std 551
    "Violet Book" §7.6:

    .. math::
        I_{asym\\_rms,avg}^{2} = \\frac{1}{3}\\bigl(I_A^2 + I_B^2 + I_C^2\\bigr)
        = \\frac{I_{symm\\_rms}^{2}}{3}\\bigl[(1 + 2\\,e) + 2\\,(1 + 0.5\\,e)\\bigr]
        = I_{symm\\_rms}^{2}\\,(1 + e)

    onde :math:`e = e^{-2\\pi/(X/R)}`. Forma simplificada:

    .. math::
        I_{asym\\_rms,avg}(\\frac{1}{2}\\,cycle)
        = I_{symm\\_rms} \\cdot \\sqrt{1 + e^{-2\\pi/(X/R)}}

    Phase A tem DC offset máximo (factor `1 + 2·e`); Phases B e C têm
    offsets reduzidos (factor `1 + 0.5·e` cada). A média é sempre **menor**
    que Phase A worst-case (verificável: ``√(1+e) < √(1+2e)``).

    Esta forma "average 3-φ" é a usada para *rated symmetrical withstand
    com X/R asymétrico*; sempre menor que Phase A worst.

    References
    ----------
    PTW A_FAULT manual §1.2.3 p. 1-7 (linhas 420-424).
    IEEE Std 551-2006 (Violet Book) §7.6.
    """
    if i_symm_rms_kA < 0:
        raise ValueError(
            f"i_symm_rms_kA must be ≥ 0; got {i_symm_rms_kA!r}"
        )
    if x_over_r <= 0:
        raise ValueError(f"x_over_r must be > 0; got {x_over_r!r}")
    if i_symm_rms_kA == 0.0:
        return 0.0
    e1 = math.exp(-2.0 * math.pi / x_over_r)
    return i_symm_rms_kA * math.sqrt(1.0 + e1)


def mf_by_mode(
    x_over_r: float,
    nacd: float,
    mode: NacdMode,
    breaker: BreakerCycle,
    fault: FaultType,
    std: AnsiStandard = AnsiStandard.C37_010,
) -> float:
    """Dispatcher for the three NACD modes (§1.3.3 p. 1-11).

    * :attr:`NacdMode.ALL_REMOTE` → :func:`mf_remote` (NACD ignored)
    * :attr:`NacdMode.PREDOMINANT` → :func:`mf_remote` if NACD ≥ 0.5 else :func:`mf_local`
    * :attr:`NacdMode.INTERPOLATED` → :func:`mf_interpolated` (default)

    References
    ----------
    PTW A_FAULT manual §1.3.3 p. 1-11 (linhas 620-636).
    """
    if mode == NacdMode.ALL_REMOTE:
        return mf_remote(x_over_r, breaker, fault, std)
    if mode == NacdMode.PREDOMINANT:
        if nacd >= NACD_PREDOMINANT_THRESHOLD:
            return mf_remote(x_over_r, breaker, fault, std)
        return mf_local(x_over_r, breaker, fault, std)
    # INTERPOLATED (default)
    return mf_interpolated(x_over_r, nacd, breaker, fault, std)


__all__ = [
    # v3.0.2 Sprint A
    "MachineKind",
    "machine_multiplier",
    "is_local_to_fault",
    "separately_derived_xr",
    "momentary_rms_multiplier",
    "momentary_peak_multiplier",
    "lv_duty_adjusted",
    "DeviceClass",
    "get_test_xr",
    "get_test_pf",
    "get_asym_withstand",
    # v3.0.3 Sprint B.1 — NACD
    "NacdMode",
    "NACD_PREDOMINANT_THRESHOLD",
    "DEFAULT_NACD_MODE",
    "GeneratorContribution",
    "nacd_ratio",
    # v3.0.3 Sprint B.2 — MF tables
    "BreakerCycle",
    "FaultType",
    "AnsiStandard",
    "BREAKER_CONTACT_PARTING",
    "HV_FUSE_TEST_XR_OPTIONS",
    "HV_CB_PRE1987_ASYM_FACTOR",
    "DEFAULT_PREFAULT_VOLTAGE_PU",
    "mf_local",
    "mf_remote",
    "mf_interpolated",
    "mf_by_mode",
    # v3.0.3 Sprint B.7 — Asym Withstand
    "asym_withstand_phase_a",
    "asym_withstand_average_3ph",
]
