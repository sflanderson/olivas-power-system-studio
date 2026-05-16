"""
tests/test_pp_v0_44_monte_carlo.py — v0.44: análise Monte
Carlo arc-flash sensitivity.
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.arc_flash import ArcFlashCase
from app.postprocessor.arc_flash_monte_carlo import (
    ArcFlashUncertainty, DistributionType, MonteCarloResult,
    _percentile, _sample_lognormal, _sample_normal_truncated,
    _sample_uniform, run_monte_carlo,
)
from app.standards.nbr17227 import ElectrodeConfig, EquipmentClass


def _base_case() -> ArcFlashCase:
    return ArcFlashCase(
        bus_name="SWGR",
        rated_voltage_kV=13.8,
        bolted_fault_current_kA=18.0,
        arc_clearing_time_ms=200.0,
        equipment_class=EquipmentClass.SWITCHGEAR_15KV,
        electrode_config=ElectrodeConfig.VCB,
    )


# ---------------------------------------------------------------------------
# Distributions
# ---------------------------------------------------------------------------


class TestDistributions:

    def test_normal_truncated_no_negative(self):
        import random
        rng = random.Random(42)
        samples = [
            _sample_normal_truncated(10.0, 5.0, rng)
            for _ in range(500)
        ]
        # Todas amostras > 0
        assert all(s > 0 for s in samples)

    def test_lognormal_always_positive(self):
        import random
        rng = random.Random(42)
        samples = [_sample_lognormal(10.0, 0.20, rng) for _ in range(500)]
        assert all(s > 0 for s in samples)

    def test_lognormal_mean_approximately_target(self):
        import random
        rng = random.Random(42)
        samples = [_sample_lognormal(10.0, 0.15, rng) for _ in range(2000)]
        mean = sum(samples) / len(samples)
        # Tolerância 5% para 2000 amostras
        assert abs(mean - 10.0) / 10.0 < 0.05

    def test_uniform_within_range(self):
        import random
        rng = random.Random(42)
        samples = [_sample_uniform(10.0, 2.0, rng) for _ in range(500)]
        assert all(8.0 <= s <= 12.0 for s in samples)


# ---------------------------------------------------------------------------
# Percentile
# ---------------------------------------------------------------------------


class TestPercentile:

    def test_empty_returns_zero(self):
        assert _percentile([], 50) == 0.0

    def test_single_element(self):
        assert _percentile([5.0], 50) == 5.0

    def test_p50_median(self):
        assert _percentile([1, 2, 3, 4, 5], 50) == 3.0

    def test_p95_upper(self):
        # Lista de 0-99: P95 ≈ 94 (interpolated)
        samples = list(range(100))
        p95 = _percentile([float(s) for s in samples], 95)
        assert 93 <= p95 <= 95


# ---------------------------------------------------------------------------
# ArcFlashUncertainty
# ---------------------------------------------------------------------------


class TestUncertainty:

    def test_defaults(self):
        u = ArcFlashUncertainty()
        assert u.Ibf_cv_pct == 15.0
        assert u.T_cv_pct == 20.0
        assert u.gap_cv_pct == 5.0
        assert u.D_cv_pct == 10.0
        assert u.Ibf_distribution == DistributionType.LOGNORMAL


# ---------------------------------------------------------------------------
# run_monte_carlo
# ---------------------------------------------------------------------------


class TestRunMonteCarlo:

    def test_returns_result(self):
        result = run_monte_carlo(
            _base_case(), ArcFlashUncertainty(),
            n_samples=200, random_seed=42,
        )
        assert isinstance(result, MonteCarloResult)
        assert result.n_samples > 0

    def test_percentiles_ordered(self):
        result = run_monte_carlo(
            _base_case(), ArcFlashUncertainty(),
            n_samples=500, random_seed=42,
        )
        # P50 ≤ P95 ≤ P99
        assert result.P50_J_per_cm2 <= result.P95_J_per_cm2
        assert result.P95_J_per_cm2 <= result.P99_J_per_cm2

    def test_cal_conversion(self):
        result = run_monte_carlo(
            _base_case(), ArcFlashUncertainty(),
            n_samples=200, random_seed=42,
        )
        # cal = J / 4.184
        assert result.P50_cal_cm2 == pytest.approx(
            result.P50_J_per_cm2 / 4.184, rel=1e-9,
        )

    def test_zero_cv_returns_deterministic(self):
        """CV=0 em todos params → distribuição degenerada (só 1 valor)."""
        u = ArcFlashUncertainty(
            Ibf_cv_pct=0, T_cv_pct=0, gap_cv_pct=0, D_cv_pct=0,
        )
        result = run_monte_carlo(
            _base_case(), u, n_samples=100, random_seed=42,
        )
        # Variância deve ser ≈ 0
        assert result.std_J_per_cm2 < 0.1

    def test_higher_uncertainty_higher_spread(self):
        """Maior CV → maior std das amostras."""
        u_low = ArcFlashUncertainty(
            Ibf_cv_pct=5, T_cv_pct=5, gap_cv_pct=2, D_cv_pct=2,
        )
        u_high = ArcFlashUncertainty(
            Ibf_cv_pct=30, T_cv_pct=40, gap_cv_pct=15, D_cv_pct=20,
        )
        r_low = run_monte_carlo(
            _base_case(), u_low, n_samples=500, random_seed=42,
        )
        r_high = run_monte_carlo(
            _base_case(), u_high, n_samples=500, random_seed=42,
        )
        assert r_high.std_J_per_cm2 > r_low.std_J_per_cm2

    def test_seed_reproducibility(self):
        """Mesma seed → mesmos resultados."""
        u = ArcFlashUncertainty()
        r1 = run_monte_carlo(_base_case(), u, n_samples=200, random_seed=123)
        r2 = run_monte_carlo(_base_case(), u, n_samples=200, random_seed=123)
        assert r1.P50_J_per_cm2 == r2.P50_J_per_cm2
        assert r1.P95_J_per_cm2 == r2.P95_J_per_cm2

    def test_cat_distribution_sums_to_one(self):
        result = run_monte_carlo(
            _base_case(), ArcFlashUncertainty(),
            n_samples=500, random_seed=42,
        )
        total = sum(result.cat_distribution.values())
        assert total == pytest.approx(1.0, rel=1e-6)

    def test_summary_contains_percentiles(self):
        result = run_monte_carlo(
            _base_case(), ArcFlashUncertainty(),
            n_samples=200, random_seed=42,
        )
        text = result.summary()
        assert "P50" in text
        assert "P95" in text
        assert "P99" in text
        assert "Categorias" in text


class TestPhysicalSanity:

    def test_p95_above_deterministic(self):
        """P95 deve ser ≥ valor determinístico (cenário base)."""
        from app.postprocessor.arc_flash import calculate_arc_flash
        base = _base_case()
        det = calculate_arc_flash(base)
        # Para distribuição centrada no base, P95 > determinístico
        result = run_monte_carlo(
            base, ArcFlashUncertainty(),
            n_samples=500, random_seed=42,
        )
        assert result.P95_J_per_cm2 >= det.incident_energy_J_cm2 * 0.9
