"""v3.6.0 — Reliability indices module (Tier 1 PTW Tutorial §Part 10).

Implements **system reliability indices** per **IEEE Std 1366-2012**:

* **SAIFI** — System Average Interruption Frequency Index (events/customer/year)
* **SAIDI** — System Average Interruption Duration Index (hours/customer/year)
* **CAIDI** — Customer Average Interruption Duration Index (hours/event)
* **ASAI** — Average Service Availability Index (per-unit, 0..1)
* **MTBF** — Mean Time Between Failures (hours)
* **MTTR** — Mean Time To Repair (hours)
* **Forced outage rate** — q = MTTR / (MTBF + MTTR) (per-unit)

Reference
---------
* IEEE Std 1366-2012 — Guide for Electric Power Distribution Reliability Indices
* PTW Tutorial v8.0 §Part 10 — Reliability assessment workflow
* IEEE 493-2007 (Gold Book) §3.4 — Component reliability data

Anti-alucinação
---------------
Cita IEEE 1366-2012 §4.2-4.5 inline para cada índice. Fórmulas
documentadas com unidades. Limitações declaradas no docstring de cada
função.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

# ---------------------------------------------------------------------------
# Hours per year — assume non-leap year (8760 hours)
# ---------------------------------------------------------------------------

HOURS_PER_YEAR: float = 8760.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class InterruptionEvent:
    """Single interruption event affecting customers (IEEE 1366 §3.13).

    Attributes
    ----------
    customers_interrupted:
        Number of customers affected (must be ≥ 0).
    duration_hours:
        Duration of interruption in hours (must be > 0).
    description:
        Optional human-readable cause / location.
    """

    customers_interrupted: int
    duration_hours: float
    description: str = ""

    def __post_init__(self) -> None:
        if self.customers_interrupted < 0:
            raise ValueError(
                f"customers_interrupted must be >= 0, got "
                f"{self.customers_interrupted}"
            )
        if self.duration_hours <= 0:
            raise ValueError(
                f"duration_hours must be > 0, got {self.duration_hours}"
            )


@dataclass
class ComponentReliability:
    """Component-level MTBF / MTTR (IEEE 493-2007 Gold Book).

    Attributes
    ----------
    name:
        Component identifier (e.g. ``"BREAKER_Q1"``).
    mtbf_hours:
        Mean Time Between Failures (hours).
    mttr_hours:
        Mean Time To Repair (hours).
    """

    name: str
    mtbf_hours: float
    mttr_hours: float

    def __post_init__(self) -> None:
        if self.mtbf_hours <= 0:
            raise ValueError(
                f"mtbf_hours must be > 0 for {self.name!r}, "
                f"got {self.mtbf_hours}"
            )
        if self.mttr_hours <= 0:
            raise ValueError(
                f"mttr_hours must be > 0 for {self.name!r}, "
                f"got {self.mttr_hours}"
            )

    @property
    def failure_rate_per_year(self) -> float:
        """λ = HOURS_PER_YEAR / MTBF (failures per year)."""
        return HOURS_PER_YEAR / self.mtbf_hours

    @property
    def forced_outage_rate(self) -> float:
        """q = MTTR / (MTBF + MTTR) — per-unit forced outage rate
        (IEEE 493 §3.4.3, range 0..1).
        """
        return self.mttr_hours / (self.mtbf_hours + self.mttr_hours)

    @property
    def availability(self) -> float:
        """A = MTBF / (MTBF + MTTR) — per-unit availability."""
        return self.mtbf_hours / (self.mtbf_hours + self.mttr_hours)


@dataclass
class ReliabilityIndices:
    """Container for IEEE 1366-2012 system indices.

    Attributes
    ----------
    saifi:
        System Average Interruption Frequency Index (events/cust/year).
    saidi:
        System Average Interruption Duration Index (hours/cust/year).
    caidi:
        Customer Average Interruption Duration Index (hours/event).
    asai:
        Average Service Availability Index (per-unit, 0..1).
    total_customers:
        Total customers served (denominator for SAIFI/SAIDI).
    n_events:
        Number of interruption events analyzed.
    """

    saifi: float
    saidi: float
    caidi: float
    asai: float
    total_customers: int
    n_events: int = 0

    def as_text_report(self) -> str:
        """Format as multi-line text report."""
        return (
            f"=== Reliability Indices (IEEE 1366-2012) ===\n"
            f"SAIFI = {self.saifi:.4f} events/customer/year\n"
            f"SAIDI = {self.saidi:.4f} hours/customer/year\n"
            f"CAIDI = {self.caidi:.4f} hours/event\n"
            f"ASAI  = {self.asai:.6f} ({self.asai * 100:.4f}%)\n"
            f"Customers served : {self.total_customers}\n"
            f"Events analyzed  : {self.n_events}"
        )


# ---------------------------------------------------------------------------
# Index calculations
# ---------------------------------------------------------------------------


def calculate_saifi(
    events: Iterable[InterruptionEvent],
    total_customers: int,
) -> float:
    """SAIFI = Σ N_i / N_T (IEEE 1366-2012 §4.2).

    Where:
    * ``N_i`` = customers interrupted in event i
    * ``N_T`` = total customers served

    Returns events per customer per year.

    Raises
    ------
    ValueError
        If ``total_customers <= 0``.
    """
    if total_customers <= 0:
        raise ValueError(
            f"total_customers must be > 0, got {total_customers}"
        )
    sum_ni = sum(e.customers_interrupted for e in events)
    return sum_ni / total_customers


def calculate_saidi(
    events: Iterable[InterruptionEvent],
    total_customers: int,
) -> float:
    """SAIDI = Σ (r_i × N_i) / N_T (IEEE 1366-2012 §4.3).

    Where:
    * ``r_i`` = restoration time for event i (hours)
    * ``N_i`` = customers interrupted in event i
    * ``N_T`` = total customers served

    Returns customer-hours of interruption per customer per year.
    """
    if total_customers <= 0:
        raise ValueError(
            f"total_customers must be > 0, got {total_customers}"
        )
    sum_rini = sum(
        e.duration_hours * e.customers_interrupted for e in events
    )
    return sum_rini / total_customers


def calculate_caidi(saifi: float, saidi: float) -> float:
    """CAIDI = SAIDI / SAIFI (IEEE 1366-2012 §4.4).

    Returns hours/event. If SAIFI == 0 (no interruptions), returns 0.
    """
    if saifi == 0:
        return 0.0
    return saidi / saifi


def calculate_asai(saidi: float) -> float:
    """ASAI = (8760 - SAIDI) / 8760 (IEEE 1366-2012 §4.5).

    Returns per-unit availability (0..1). Clamps result to [0, 1] in
    case SAIDI > 8760 (full year of outages — unphysical but handled).
    """
    asai = (HOURS_PER_YEAR - saidi) / HOURS_PER_YEAR
    return max(0.0, min(1.0, asai))


def calculate_indices(
    events: Iterable[InterruptionEvent],
    total_customers: int,
) -> ReliabilityIndices:
    """One-shot calculation of all 4 IEEE 1366 indices."""
    events_list = list(events)
    saifi = calculate_saifi(events_list, total_customers)
    saidi = calculate_saidi(events_list, total_customers)
    caidi = calculate_caidi(saifi, saidi)
    asai = calculate_asai(saidi)
    return ReliabilityIndices(
        saifi=saifi,
        saidi=saidi,
        caidi=caidi,
        asai=asai,
        total_customers=total_customers,
        n_events=len(events_list),
    )


# ---------------------------------------------------------------------------
# Component-level helpers (IEEE 493 Gold Book)
# ---------------------------------------------------------------------------


def system_failure_rate_series(
    components: Iterable[ComponentReliability],
) -> float:
    """Series system failure rate = sum of component λ (IEEE 493 §3.4.4).

    For series topology (any one fails → system fails), system λ
    is approximately the sum of individual rates (failures/year).
    """
    return sum(c.failure_rate_per_year for c in components)


def system_unavailability_series(
    components: Iterable[ComponentReliability],
) -> float:
    """Series system unavailability ≈ Σ q_i (small-q approximation).

    For small q (q < 0.01), unavailability of series system is
    approximately the sum of individual unavailabilities. This is
    the standard IEEE 493 §3.4.5 first-order approximation.
    """
    return sum(c.forced_outage_rate for c in components)


def parallel_unavailability(
    components: Iterable[ComponentReliability],
) -> float:
    """Parallel system unavailability = Π q_i (IEEE 493 §3.4.6).

    For parallel topology (all must fail → system fails), product
    of individual q values. Returns per-unit (0..1).
    """
    q_product = 1.0
    has_any = False
    for c in components:
        q_product *= c.forced_outage_rate
        has_any = True
    return q_product if has_any else 0.0
