"""v3.8.0 — Monte Carlo Reliability simulation (extends v3.6.0 Reliability).

Estende :mod:`reliability` com:

* **Library presets** IEEE 493-2007 (Gold Book) Tab 3-1 — typical MTBF/MTTR
  para componentes industriais comuns
* **Monte Carlo time-series** — simula ``n_years`` de operação,
  amostrando failures via distribuição exponencial (rate λ por componente)
  e durations via distribuição lognormal (MTTR ± σ)
* **Confidence intervals** — 5%/50%/95% para SAIFI/SAIDI/CAIDI/ASAI

Reference
---------
* IEEE Std 493-2007 (Gold Book) Tab 3-1 — Equipment reliability data
* IEEE Std 1366-2012 §4 — Indices definitions
* Tan, Sun, Goel (2005) "MC reliability assessment of distribution systems"

Anti-alucinação
---------------
* Apenas usa ``random`` stdlib (não numpy) para garantir reprodutibilidade
  via seed
* Limitations: assume independent failures (no common-mode); deferred
  multi-state Markov.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Iterable

from app.commercial.feature_gates import Feature, requires_feature
from app.postprocessor.reliability import (
    HOURS_PER_YEAR,
    ComponentReliability,
    InterruptionEvent,
    ReliabilityIndices,
    calculate_indices,
)


# ---------------------------------------------------------------------------
# IEEE 493-2007 Gold Book Tab 3-1 — typical equipment reliability data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _IEEE493Preset:
    """Frozen preset row from IEEE 493-2007 Tab 3-1."""
    equipment_type: str
    mtbf_hours: float
    mttr_hours: float
    description: str = ""


IEEE493_PRESETS: tuple[_IEEE493Preset, ...] = (
    _IEEE493Preset(
        "transformer_liquid_filled",
        mtbf_hours=350_400.0,    # λ ≈ 0.025/year
        mttr_hours=342.0,        # ~14 days
        description="Liquid-filled transformer >600V, indoor/outdoor",
    ),
    _IEEE493Preset(
        "transformer_dry_type",
        mtbf_hours=438_000.0,    # λ ≈ 0.020/year
        mttr_hours=192.0,        # ~8 days
        description="Dry-type transformer (cast resin / VPI)",
    ),
    _IEEE493Preset(
        "circuit_breaker_metalclad",
        mtbf_hours=146_000.0,    # λ ≈ 0.060/year
        mttr_hours=90.0,
        description="Metal-clad medium-voltage breaker (5-15kV)",
    ),
    _IEEE493Preset(
        "circuit_breaker_lv",
        mtbf_hours=87_600.0,     # λ ≈ 0.10/year
        mttr_hours=4.5,
        description="Low-voltage molded-case / power breaker",
    ),
    _IEEE493Preset(
        "cable_underground_lv",
        mtbf_hours=219_000.0,    # λ ≈ 0.04/year per 1000ft
        mttr_hours=24.0,
        description="Underground cable LV, per 1000 ft",
    ),
    _IEEE493Preset(
        "cable_aerial_mv",
        mtbf_hours=87_600.0,     # λ ≈ 0.10/year per mile
        mttr_hours=8.0,
        description="Aerial cable MV (5-15kV), per mile",
    ),
    _IEEE493Preset(
        "induction_motor_400hp",
        mtbf_hours=43_800.0,     # λ ≈ 0.20/year
        mttr_hours=144.0,        # 6 days
        description="Induction motor 100-1000HP, 600V-15kV",
    ),
    _IEEE493Preset(
        "switchgear_lv",
        mtbf_hours=2_190_000.0,  # λ ≈ 0.004/year
        mttr_hours=72.0,
        description="Low-voltage switchgear assembly",
    ),
    _IEEE493Preset(
        "ups_battery",
        mtbf_hours=43_800.0,     # λ ≈ 0.20/year
        mttr_hours=8.0,
        description="UPS battery system (string)",
    ),
    _IEEE493Preset(
        "generator_diesel",
        mtbf_hours=3650.0,       # ~5000 starts MTBF
        mttr_hours=48.0,
        description="Diesel emergency generator",
    ),
)


def get_preset(equipment_type: str) -> _IEEE493Preset:
    """Return preset by equipment_type. Raises KeyError if not found."""
    for p in IEEE493_PRESETS:
        if p.equipment_type == equipment_type:
            return p
    raise KeyError(
        f"No IEEE 493 preset for {equipment_type!r}. "
        f"Available: {[p.equipment_type for p in IEEE493_PRESETS]}"
    )


def list_preset_types() -> list[str]:
    """Return list of available preset equipment_types."""
    return [p.equipment_type for p in IEEE493_PRESETS]


def make_component_from_preset(
    name: str,
    equipment_type: str,
) -> ComponentReliability:
    """Build a ComponentReliability from an IEEE 493 preset."""
    preset = get_preset(equipment_type)
    return ComponentReliability(
        name=name,
        mtbf_hours=preset.mtbf_hours,
        mttr_hours=preset.mttr_hours,
    )


# ---------------------------------------------------------------------------
# Monte Carlo simulation
# ---------------------------------------------------------------------------


@dataclass
class MCResult:
    """Monte Carlo simulation result.

    Attributes
    ----------
    n_simulations:
        Number of independent Monte Carlo runs.
    n_years_per_run:
        Number of operational years simulated per run.
    saifi_distribution:
        Sorted list of SAIFI values (one per run).
    saidi_distribution:
        Sorted list of SAIDI values (one per run).
    caidi_distribution:
        Sorted list of CAIDI values (one per run).
    asai_distribution:
        Sorted list of ASAI values (one per run).
    """
    n_simulations: int
    n_years_per_run: int
    saifi_distribution: list[float] = field(default_factory=list)
    saidi_distribution: list[float] = field(default_factory=list)
    caidi_distribution: list[float] = field(default_factory=list)
    asai_distribution: list[float] = field(default_factory=list)

    def percentile(self, dist_name: str, p: float) -> float:
        """Return percentile p (0..1) of the given distribution.

        Uses simple linear interpolation between sorted samples.
        """
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"p must be in [0, 1], got {p}")
        dist = getattr(self, f"{dist_name}_distribution", None)
        if not dist:
            return 0.0
        sorted_dist = sorted(dist)
        n = len(sorted_dist)
        if n == 1:
            return sorted_dist[0]
        idx_f = p * (n - 1)
        lo = int(math.floor(idx_f))
        hi = int(math.ceil(idx_f))
        frac = idx_f - lo
        return sorted_dist[lo] + frac * (sorted_dist[hi] - sorted_dist[lo])

    def confidence_interval(
        self, dist_name: str, alpha: float = 0.10,
    ) -> tuple[float, float]:
        """Return (low, high) bounds for confidence ``1 - alpha``."""
        return (
            self.percentile(dist_name, alpha / 2),
            self.percentile(dist_name, 1 - alpha / 2),
        )

    def median(self, dist_name: str) -> float:
        return self.percentile(dist_name, 0.5)

    def mean(self, dist_name: str) -> float:
        dist = getattr(self, f"{dist_name}_distribution", None)
        if not dist:
            return 0.0
        return sum(dist) / len(dist)

    def as_text_report(self) -> str:
        """Format MC summary report with mean ± 90% CI."""
        lines = [
            "=== Monte Carlo Reliability ===",
            f"Simulations : {self.n_simulations}",
            f"Years/run   : {self.n_years_per_run}",
            "",
            f"SAIFI mean = {self.mean('saifi'):.4f}, "
            f"90% CI = [{self.percentile('saifi', 0.05):.4f}, "
            f"{self.percentile('saifi', 0.95):.4f}]",
            f"SAIDI mean = {self.mean('saidi'):.4f}, "
            f"90% CI = [{self.percentile('saidi', 0.05):.4f}, "
            f"{self.percentile('saidi', 0.95):.4f}]",
            f"CAIDI mean = {self.mean('caidi'):.4f}, "
            f"90% CI = [{self.percentile('caidi', 0.05):.4f}, "
            f"{self.percentile('caidi', 0.95):.4f}]",
            f"ASAI mean  = {self.mean('asai'):.6f}, "
            f"90% CI = [{self.percentile('asai', 0.05):.6f}, "
            f"{self.percentile('asai', 0.95):.6f}]",
        ]
        return "\n".join(lines)


@requires_feature(Feature.RELIABILITY_MC)
def run_monte_carlo(
    components: Iterable[ComponentReliability],
    *,
    customers_per_component: int = 100,
    total_customers: int = 1000,
    n_years: int = 10,
    n_simulations: int = 100,
    mttr_lognormal_sigma: float = 0.5,
    seed: int | None = 42,
) -> MCResult:
    """Run Monte Carlo time-series reliability simulation.

    For each simulation:
    1. For each component, sample failure times via exponential
       distribution with rate λ = 1/MTBF (in failures/hour).
    2. For each failure event, sample duration via lognormal
       distribution with mean = MTTR and shape = ``mttr_lognormal_sigma``.
    3. Compute SAIFI/SAIDI/CAIDI/ASAI for the simulated horizon.

    Parameters
    ----------
    components:
        Iterable of :class:`ComponentReliability` (each contributes failures).
    customers_per_component:
        Customers affected when this component fails.
    total_customers:
        Denominator for SAIFI/SAIDI calculations.
    n_years:
        Operational horizon per simulation.
    n_simulations:
        Number of independent MC runs.
    mttr_lognormal_sigma:
        Shape parameter (σ) for lognormal MTTR distribution.
    seed:
        RNG seed for reproducibility (None = nondeterministic).

    Returns
    -------
    MCResult
    """
    if total_customers <= 0:
        raise ValueError("total_customers must be > 0")
    if n_simulations <= 0:
        raise ValueError("n_simulations must be > 0")
    if n_years <= 0:
        raise ValueError("n_years must be > 0")

    rng = random.Random(seed)
    components_list = list(components)
    horizon_hours = n_years * HOURS_PER_YEAR

    saifis: list[float] = []
    saidis: list[float] = []
    caidis: list[float] = []
    asais: list[float] = []

    for _sim in range(n_simulations):
        events: list[InterruptionEvent] = []
        for c in components_list:
            # Exponential failures: λ_per_hour = 1/MTBF
            lambda_per_hour = 1.0 / c.mtbf_hours
            t = 0.0
            while t < horizon_hours:
                # Inverse-CDF sampling: -ln(U)/λ
                u = rng.random()
                if u <= 0:
                    u = 1e-12
                interarrival = -math.log(u) / lambda_per_hour
                t += interarrival
                if t >= horizon_hours:
                    break
                # Sample duration from lognormal
                # μ = ln(MTTR) - σ²/2 so E[X] = MTTR
                mu = math.log(c.mttr_hours) - mttr_lognormal_sigma ** 2 / 2.0
                duration = rng.lognormvariate(mu, mttr_lognormal_sigma)
                duration = max(duration, 0.01)  # min 0.01h = 36s
                events.append(InterruptionEvent(
                    customers_interrupted=customers_per_component,
                    duration_hours=duration,
                    description=f"{c.name}@{t:.1f}h",
                ))

        # Convert to per-year averages (divide by n_years)
        if events:
            indices = calculate_indices(events, total_customers)
            saifis.append(indices.saifi / n_years)
            saidis.append(indices.saidi / n_years)
            caidis.append(indices.caidi)  # CAIDI is hours/event, no per-year
            asais.append((HOURS_PER_YEAR - indices.saidi / n_years)
                         / HOURS_PER_YEAR)
        else:
            saifis.append(0.0)
            saidis.append(0.0)
            caidis.append(0.0)
            asais.append(1.0)

    return MCResult(
        n_simulations=n_simulations,
        n_years_per_run=n_years,
        saifi_distribution=saifis,
        saidi_distribution=saidis,
        caidi_distribution=caidis,
        asai_distribution=asais,
    )
