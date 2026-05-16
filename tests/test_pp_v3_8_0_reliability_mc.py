"""v3.8.0 — Reliability Monte Carlo tests.

Reference:
* IEEE 493-2007 Tab 3-1 typical reliability data
* IEEE 1366-2012 indices
"""

from __future__ import annotations

import math
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    return app


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------


class TestPresets:
    def test_list_preset_types_includes_common_equipment(self) -> None:
        from app.postprocessor.reliability_monte_carlo import list_preset_types
        types = list_preset_types()
        assert "transformer_dry_type" in types
        assert "circuit_breaker_lv" in types
        assert "induction_motor_400hp" in types
        assert len(types) >= 8

    def test_get_preset_returns_data(self) -> None:
        from app.postprocessor.reliability_monte_carlo import get_preset
        p = get_preset("transformer_dry_type")
        assert p.equipment_type == "transformer_dry_type"
        assert p.mtbf_hours > 0
        assert p.mttr_hours > 0
        assert "transformer" in p.description.lower()

    def test_get_preset_unknown_raises(self) -> None:
        from app.postprocessor.reliability_monte_carlo import get_preset
        with pytest.raises(KeyError, match="No IEEE 493 preset"):
            get_preset("nonexistent_xyz")

    def test_make_component_from_preset(self) -> None:
        from app.postprocessor.reliability_monte_carlo import (
            make_component_from_preset,
        )
        c = make_component_from_preset("T1", "transformer_dry_type")
        assert c.name == "T1"
        assert c.mtbf_hours > 0
        # IEEE 493 dry-type ≈ 438000h MTBF, 192h MTTR
        assert math.isclose(c.mtbf_hours, 438_000.0, rel_tol=0.05)
        assert math.isclose(c.mttr_hours, 192.0, rel_tol=0.05)


# ---------------------------------------------------------------------------
# MCResult
# ---------------------------------------------------------------------------


class TestMCResult:
    def _make_dummy_result(self):
        from app.postprocessor.reliability_monte_carlo import MCResult
        return MCResult(
            n_simulations=5,
            n_years_per_run=10,
            saifi_distribution=[0.1, 0.2, 0.3, 0.4, 0.5],
            saidi_distribution=[1.0, 2.0, 3.0, 4.0, 5.0],
            caidi_distribution=[10.0, 10.0, 10.0, 10.0, 10.0],
            asai_distribution=[0.99, 0.995, 0.999, 0.9995, 0.9999],
        )

    def test_percentile_endpoints(self) -> None:
        r = self._make_dummy_result()
        assert r.percentile("saifi", 0.0) == 0.1
        assert r.percentile("saifi", 1.0) == 0.5

    def test_percentile_median(self) -> None:
        r = self._make_dummy_result()
        assert r.percentile("saifi", 0.5) == 0.3

    def test_percentile_invalid_raises(self) -> None:
        r = self._make_dummy_result()
        with pytest.raises(ValueError):
            r.percentile("saifi", 1.5)

    def test_confidence_interval_90pct(self) -> None:
        r = self._make_dummy_result()
        lo, hi = r.confidence_interval("saifi", alpha=0.10)
        assert lo < hi
        # 5th percentile of [0.1..0.5] = ~0.12; 95th = ~0.48
        assert math.isclose(lo, 0.12, abs_tol=0.05)
        assert math.isclose(hi, 0.48, abs_tol=0.05)

    def test_mean(self) -> None:
        r = self._make_dummy_result()
        assert math.isclose(r.mean("saifi"), 0.3)

    def test_text_report_includes_all_metrics(self) -> None:
        r = self._make_dummy_result()
        text = r.as_text_report()
        assert "SAIFI" in text and "SAIDI" in text
        assert "CAIDI" in text and "ASAI" in text
        assert "Monte Carlo" in text or "Simulations" in text


# ---------------------------------------------------------------------------
# Monte Carlo simulation
# ---------------------------------------------------------------------------


class TestRunMonteCarlo:
    def test_basic_run_completes(self) -> None:
        from app.postprocessor.reliability_monte_carlo import (
            make_component_from_preset,
            run_monte_carlo,
        )
        components = [
            make_component_from_preset("T1", "transformer_dry_type"),
            make_component_from_preset("BR1", "circuit_breaker_lv"),
        ]
        result = run_monte_carlo(
            components,
            total_customers=1000,
            n_years=5,
            n_simulations=20,
            seed=42,
        )
        assert result.n_simulations == 20
        assert result.n_years_per_run == 5
        assert len(result.saifi_distribution) == 20

    def test_seed_reproducibility(self) -> None:
        """Same seed → same distribution."""
        from app.postprocessor.reliability_monte_carlo import (
            make_component_from_preset,
            run_monte_carlo,
        )
        comps = [make_component_from_preset("X", "circuit_breaker_lv")]
        r1 = run_monte_carlo(comps, n_years=2, n_simulations=10, seed=99)
        r2 = run_monte_carlo(comps, n_years=2, n_simulations=10, seed=99)
        assert r1.saifi_distribution == r2.saifi_distribution

    def test_different_seeds_yield_different_results(self) -> None:
        from app.postprocessor.reliability_monte_carlo import (
            make_component_from_preset,
            run_monte_carlo,
        )
        comps = [make_component_from_preset("X", "circuit_breaker_lv")]
        r1 = run_monte_carlo(comps, n_years=2, n_simulations=10, seed=1)
        r2 = run_monte_carlo(comps, n_years=2, n_simulations=10, seed=2)
        assert r1.saifi_distribution != r2.saifi_distribution

    def test_zero_total_customers_raises(self) -> None:
        from app.postprocessor.reliability_monte_carlo import (
            make_component_from_preset,
            run_monte_carlo,
        )
        with pytest.raises(ValueError, match="total_customers"):
            run_monte_carlo(
                [make_component_from_preset("X", "circuit_breaker_lv")],
                total_customers=0,
            )

    def test_zero_simulations_raises(self) -> None:
        from app.postprocessor.reliability_monte_carlo import (
            make_component_from_preset,
            run_monte_carlo,
        )
        with pytest.raises(ValueError, match="n_simulations"):
            run_monte_carlo(
                [make_component_from_preset("X", "circuit_breaker_lv")],
                n_simulations=0,
            )

    def test_high_reliability_yields_low_saifi(self) -> None:
        """Very reliable component (long MTBF) → low SAIFI."""
        from app.postprocessor.reliability import ComponentReliability
        from app.postprocessor.reliability_monte_carlo import run_monte_carlo
        # MTBF = 100 years (876000h); should rarely fail in 5 years
        c = ComponentReliability("X", mtbf_hours=876_000.0, mttr_hours=4.0)
        result = run_monte_carlo(
            [c], total_customers=10_000,
            customers_per_component=100,
            n_years=5, n_simulations=30, seed=42,
        )
        # Per-year SAIFI should be small
        assert result.mean("saifi") < 0.10


# ---------------------------------------------------------------------------
# GUI smoke
# ---------------------------------------------------------------------------


class TestReliabilityDialogMC:
    def test_mc_button_present(self, qapp) -> None:
        from app.gui.reliability_dialog import ReliabilityDialog
        dlg = ReliabilityDialog(parent=None)
        # Button text contains "Monte Carlo"
        from PySide6.QtWidgets import QPushButton
        btns = dlg.findChildren(QPushButton)
        labels = [b.text() for b in btns]
        assert any("Monte Carlo" in l for l in labels), (
            f"Reliability dialog must have Monte Carlo button. Got: {labels}"
        )

    def test_mc_handler_runs(self, qapp) -> None:
        """Trigger _on_run_monte_carlo directly; result text populated."""
        from app.gui.reliability_dialog import ReliabilityDialog
        dlg = ReliabilityDialog(parent=None)
        dlg._on_run_monte_carlo()
        text = dlg._result.toPlainText()
        # Should produce a Monte Carlo report (no error)
        assert "❌" not in text
        assert "SAIFI" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
