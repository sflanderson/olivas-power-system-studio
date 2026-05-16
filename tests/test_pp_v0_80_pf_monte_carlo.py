"""
tests/test_pp_v0_80_pf_monte_carlo.py — v0.80 Monte Carlo
PF sensitivity.
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")   # PF needs numpy

from app.postprocessor.power_flow import PowerFlowSystem
from app.postprocessor.power_flow_monte_carlo import (
    PfMonteCarloResult, PfUncertainty, run_pf_monte_carlo,
)


def _build_sys():
    sys = PowerFlowSystem()
    sys.add_slack(id="SL", V_pu=1.0)
    sys.add_pq(id="L1", P_pu=-0.4, Q_pu=-0.1)
    sys.add_pq(id="L2", P_pu=-0.3, Q_pu=-0.05)
    sys.add_branch("SL", "L1", R_pu=0.01, X_pu=0.05)
    sys.add_branch("L1", "L2", R_pu=0.01, X_pu=0.05)
    return sys


class TestPfUncertainty:

    def test_defaults(self):
        u = PfUncertainty()
        assert u.load_P_cv_pct == 20.0
        assert u.load_Q_cv_pct == 30.0
        assert u.voltage_setpoint_cv_pct == 1.0


class TestRunPfMonteCarlo:

    def test_returns_result(self):
        sys = _build_sys()
        result = run_pf_monte_carlo(
            sys, PfUncertainty(),
            n_samples=100, random_seed=42,
        )
        assert isinstance(result, PfMonteCarloResult)
        assert result.n_samples > 0

    def test_zero_uncertainty_deterministic(self):
        """CV=0 → todas amostras dão mesmo resultado."""
        sys = _build_sys()
        u = PfUncertainty(
            load_P_cv_pct=0, load_Q_cv_pct=0,
            voltage_setpoint_cv_pct=0,
        )
        result = run_pf_monte_carlo(
            sys, u, n_samples=50, random_seed=42,
        )
        # Variância nula
        v_mins = list(result.voltages_min_pu)
        assert len(v_mins) > 0
        assert max(v_mins) - min(v_mins) < 1e-6

    def test_higher_cv_higher_spread(self):
        sys = _build_sys()
        r_low = run_pf_monte_carlo(
            sys, PfUncertainty(load_P_cv_pct=5, load_Q_cv_pct=5),
            n_samples=200, random_seed=42,
        )
        r_high = run_pf_monte_carlo(
            sys, PfUncertainty(load_P_cv_pct=40, load_Q_cv_pct=50),
            n_samples=200, random_seed=42,
        )
        # Maior incerteza → maior dispersão de V_min
        spread_low = max(r_low.voltages_min_pu) - min(r_low.voltages_min_pu)
        spread_high = max(r_high.voltages_min_pu) - min(r_high.voltages_min_pu)
        assert spread_high > spread_low

    def test_seed_reproducibility(self):
        sys = _build_sys()
        u = PfUncertainty()
        r1 = run_pf_monte_carlo(sys, u, n_samples=100, random_seed=123)
        r2 = run_pf_monte_carlo(sys, u, n_samples=100, random_seed=123)
        assert r1.P50_V_min == r2.P50_V_min

    def test_no_side_effects(self):
        """run_pf_monte_carlo restaura cargas originais."""
        sys = _build_sys()
        original_P = sys.buses[1].P_pu_set
        original_Q = sys.buses[1].Q_pu_set
        run_pf_monte_carlo(
            sys, PfUncertainty(load_P_cv_pct=30, load_Q_cv_pct=50),
            n_samples=50, random_seed=42,
        )
        assert sys.buses[1].P_pu_set == original_P
        assert sys.buses[1].Q_pu_set == original_Q

    def test_violation_probabilities_in_range(self):
        sys = _build_sys()
        result = run_pf_monte_carlo(
            sys, PfUncertainty(),
            n_samples=200, random_seed=42,
        )
        assert 0 <= result.violation_prob_under_voltage <= 1
        assert 0 <= result.violation_prob_over_voltage <= 1

    def test_summary_format(self):
        sys = _build_sys()
        result = run_pf_monte_carlo(
            sys, PfUncertainty(),
            n_samples=100, random_seed=42,
        )
        text = result.summary()
        assert "P50 V_min" in text
        assert "P5  V_min" in text
        assert "violation" in text.lower() or "P(V_min" in text


class TestPercentiles:

    def test_p50_between_p5_and_p95(self):
        sys = _build_sys()
        result = run_pf_monte_carlo(
            sys, PfUncertainty(),
            n_samples=200, random_seed=42,
        )
        assert result.P5_V_min <= result.P50_V_min
        assert result.P95_V_max >= result.P50_V_min
