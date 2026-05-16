"""
app/postprocessor/fault_decay.py — Fault current decay over time.

Implements PTW Tutorial §Part 5 p. 136-138:

* Generator/Sync Motor decay step (subtransient → transient → steady)
* Induction Motor exclude after N cycles + hp threshold
* Recalculate Trip Time using time-decayed current

Reference
---------
PTW Tutorial §Part 5 p. 136-138 (Reduce Generator/Sync Motor Fault
Contribution + Induction Motor Fault Contribution).
A_Fault §1.2.5 p. 1-8 (machine multipliers tabela).
IEEE Std 141 (Red Book) §4.6 (machine fault current decay).
"""

from __future__ import annotations

import math
from typing import Callable


def gen_sync_decay_step(
    i_subtransient_pct: float,
    i_steady_pct: float,
    decay_time_constant_cycles: float,
    current_cycle: float,
) -> float:
    """Generator / synchronous motor fault current at time t (cycles).

    Per PTW Tutorial §Part 5 p. 136-137 (Reduce Generator/Sync Motor
    Fault Contribution): a generator's fault current decays from
    subtransient (Xd") to steady-state (Xd) following an exponential
    envelope:

    .. math::
        I(t) = I_{steady} + (I_{subtrans} - I_{steady}) \\cdot e^{-t/\\tau}

    where ``τ`` is the decay time constant in cycles (typically 5-15 for
    industrial generators).

    Common example: 1000% subtransient → 300% steady-state with
    τ = 10 cycles.

    Parameters
    ----------
    i_subtransient_pct
        Initial fault contribution as % of rated (e.g., 1000.0 = 10×).
    i_steady_pct
        Steady-state fault contribution as % of rated (e.g., 300.0 = 3×).
    decay_time_constant_cycles
        Exponential decay time constant τ in cycles. Must be > 0.
    current_cycle
        Time t at which to evaluate, in cycles. Must be ≥ 0.

    Returns
    -------
    float
        Fault current at time t, in % of rated.

    References
    ----------
    PTW Tutorial §Part 5 p. 136-137.
    IEEE Std 141 §4.6.
    """
    if decay_time_constant_cycles <= 0:
        raise ValueError(
            f"decay_time_constant_cycles must be > 0; "
            f"got {decay_time_constant_cycles!r}"
        )
    if current_cycle < 0:
        raise ValueError(
            f"current_cycle must be ≥ 0; got {current_cycle!r}"
        )
    return i_steady_pct + (i_subtransient_pct - i_steady_pct) * math.exp(
        -current_cycle / decay_time_constant_cycles
    )


def induction_motor_excluded(
    hp: float,
    cycles_after_fault: float,
    *,
    hp_threshold: float = 50.0,
    cycles_threshold_large: float = 30.0,
    cycles_threshold_small: float = 1.0,
) -> bool:
    """Determine if an induction motor's contribution is excluded.

    Per PTW Tutorial §Part 5 p. 138 + A_Fault §1.2.5 p. 1-8:

    * Motors **< 50 hp** → excluded for first-cycle calculations
      (multiplier = ∞ in A_FAULT machine table).
    * Motors **≥ 50 hp** → included for first-cycle, excluded after
      ~30 cycles (steady-state, ~0.5 s @ 60 Hz) since induction
      motors lose flux without external excitation.

    Parameters
    ----------
    hp
        Motor horsepower rating.
    cycles_after_fault
        Time elapsed since fault, in cycles.
    hp_threshold
        Motor hp threshold below which to exclude immediately (default 50).
    cycles_threshold_large
        For large motors (≥ hp_threshold), excluded after this many cycles.
    cycles_threshold_small
        For small motors (< hp_threshold), excluded after this many cycles.

    Returns
    -------
    bool
        True if motor contribution should be excluded; False otherwise.

    References
    ----------
    PTW Tutorial §Part 5 p. 138.
    A_Fault §1.2.5 p. 1-8 (Tab Machine Multipliers).
    """
    if hp < 0:
        raise ValueError(f"hp must be ≥ 0; got {hp!r}")
    if cycles_after_fault < 0:
        raise ValueError(
            f"cycles_after_fault must be ≥ 0; got {cycles_after_fault!r}"
        )

    if hp < hp_threshold:
        # Small motor — exclude after 1 cycle (essentially no contribution)
        return cycles_after_fault >= cycles_threshold_small
    # Large motor — exclude after 30 cycles (steady-state)
    return cycles_after_fault >= cycles_threshold_large


def recalculate_trip_time(
    curve: Callable[[float], float],
    i_per_pickup: float,
) -> float:
    """Recalculate trip time using a time-current curve and reduced current.

    Per PTW Tutorial §Part 5 p. 137 (Recalculate Trip Time): when the
    fault current decreases over time (e.g., generator decay), the
    relay/breaker may take **longer** to trip because it integrates
    the curve at a lower I/Ipickup ratio. This impacts arc-flash
    incident energy (longer arcing time = more energy).

    Parameters
    ----------
    curve
        Time-current curve callable: ``curve(i_per_pickup) -> trip_time_s``.
        Must return ``inf`` for currents below pickup.
    i_per_pickup
        Current at the device as a multiple of pickup setting.

    Returns
    -------
    float
        Trip time in seconds. ``math.inf`` if below pickup.

    References
    ----------
    PTW Tutorial §Part 5 p. 137.
    IEEE C37.112-1996 (inverse-time relay curves).
    """
    if i_per_pickup < 0:
        raise ValueError(
            f"i_per_pickup must be ≥ 0; got {i_per_pickup!r}"
        )
    return curve(i_per_pickup)


__all__ = [
    "gen_sync_decay_step",
    "induction_motor_excluded",
    "recalculate_trip_time",
]
