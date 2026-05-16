"""v3.6.0 — Reliability indices module tests (IEEE 1366-2012).

Tests cobrem:
* InterruptionEvent validation
* ComponentReliability properties (λ, q, A)
* SAIFI/SAIDI/CAIDI/ASAI fórmulas (golden values IEEE 1366 §4.2-4.5)
* Series/parallel system reliability (IEEE 493 Gold Book)
* GUI dialog smoke (offscreen)
"""

from __future__ import annotations

import math
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.postprocessor.reliability import (
    HOURS_PER_YEAR,
    ComponentReliability,
    InterruptionEvent,
    ReliabilityIndices,
    calculate_asai,
    calculate_caidi,
    calculate_indices,
    calculate_saidi,
    calculate_saifi,
    parallel_unavailability,
    system_failure_rate_series,
    system_unavailability_series,
)


# ---------------------------------------------------------------------------
# Data class validation
# ---------------------------------------------------------------------------


class TestInterruptionEvent:
    def test_valid_event(self) -> None:
        e = InterruptionEvent(customers_interrupted=100, duration_hours=2.5)
        assert e.customers_interrupted == 100
        assert e.duration_hours == 2.5

    def test_negative_customers_raises(self) -> None:
        with pytest.raises(ValueError, match="customers_interrupted"):
            InterruptionEvent(customers_interrupted=-1, duration_hours=1.0)

    def test_zero_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="duration_hours"):
            InterruptionEvent(customers_interrupted=10, duration_hours=0.0)

    def test_negative_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="duration_hours"):
            InterruptionEvent(customers_interrupted=10, duration_hours=-1.0)


class TestComponentReliability:
    def test_failure_rate_year(self) -> None:
        # MTBF = 8760 → λ = 1 failure/year
        c = ComponentReliability("X", mtbf_hours=8760.0, mttr_hours=10.0)
        assert math.isclose(c.failure_rate_per_year, 1.0)

    def test_failure_rate_high_reliability(self) -> None:
        # MTBF = 87600 → λ = 0.1 failure/year
        c = ComponentReliability("X", mtbf_hours=87600.0, mttr_hours=10.0)
        assert math.isclose(c.failure_rate_per_year, 0.1)

    def test_forced_outage_rate(self) -> None:
        # MTBF=99h MTTR=1h → q = 1/100 = 0.01
        c = ComponentReliability("X", mtbf_hours=99.0, mttr_hours=1.0)
        assert math.isclose(c.forced_outage_rate, 0.01)

    def test_availability(self) -> None:
        # MTBF=99 MTTR=1 → A = 99/100 = 0.99
        c = ComponentReliability("X", mtbf_hours=99.0, mttr_hours=1.0)
        assert math.isclose(c.availability, 0.99)

    def test_availability_plus_q_equals_one(self) -> None:
        c = ComponentReliability("X", mtbf_hours=8000.0, mttr_hours=24.0)
        assert math.isclose(c.availability + c.forced_outage_rate, 1.0)

    def test_zero_mtbf_raises(self) -> None:
        with pytest.raises(ValueError, match="mtbf_hours"):
            ComponentReliability("X", mtbf_hours=0.0, mttr_hours=1.0)

    def test_zero_mttr_raises(self) -> None:
        with pytest.raises(ValueError, match="mttr_hours"):
            ComponentReliability("X", mtbf_hours=1.0, mttr_hours=0.0)


# ---------------------------------------------------------------------------
# IEEE 1366 indices (golden values)
# ---------------------------------------------------------------------------


class TestSAIFI:
    """SAIFI = Σ N_i / N_T."""

    def test_simple_one_event(self) -> None:
        # 100 customers interrupted, 1000 total → SAIFI = 0.1
        events = [InterruptionEvent(100, 1.0)]
        assert math.isclose(calculate_saifi(events, 1000), 0.1)

    def test_multiple_events(self) -> None:
        # (50 + 75 + 25) / 1000 = 0.15
        events = [
            InterruptionEvent(50, 2.0),
            InterruptionEvent(75, 1.5),
            InterruptionEvent(25, 0.5),
        ]
        assert math.isclose(calculate_saifi(events, 1000), 0.15)

    def test_no_events_zero(self) -> None:
        assert calculate_saifi([], 1000) == 0.0

    def test_zero_customers_raises(self) -> None:
        with pytest.raises(ValueError, match="total_customers"):
            calculate_saifi([], 0)


class TestSAIDI:
    """SAIDI = Σ (r_i × N_i) / N_T."""

    def test_simple_one_event(self) -> None:
        # 100 cust × 2.5h / 1000 = 0.25 hours/cust/year
        events = [InterruptionEvent(100, 2.5)]
        assert math.isclose(calculate_saidi(events, 1000), 0.25)

    def test_multiple_events(self) -> None:
        # (100×1 + 200×0.5 + 50×4) / 1000 = (100 + 100 + 200) / 1000 = 0.4
        events = [
            InterruptionEvent(100, 1.0),
            InterruptionEvent(200, 0.5),
            InterruptionEvent(50, 4.0),
        ]
        assert math.isclose(calculate_saidi(events, 1000), 0.4)

    def test_zero_customers_raises(self) -> None:
        with pytest.raises(ValueError):
            calculate_saidi([], 0)


class TestCAIDI:
    def test_caidi_equals_saidi_div_saifi(self) -> None:
        assert math.isclose(calculate_caidi(0.5, 1.0), 2.0)

    def test_caidi_zero_when_saifi_zero(self) -> None:
        # No interruptions → CAIDI undefined; convention return 0
        assert calculate_caidi(0.0, 0.0) == 0.0

    def test_caidi_realistic_us_distribution(self) -> None:
        # IEEE 1366 typical US distribution: SAIFI≈1.2, SAIDI≈2.4
        # CAIDI ≈ 2 hours
        caidi = calculate_caidi(saifi=1.2, saidi=2.4)
        assert math.isclose(caidi, 2.0)


class TestASAI:
    def test_asai_perfect_reliability(self) -> None:
        # No outages → ASAI = 1
        assert math.isclose(calculate_asai(0.0), 1.0)

    def test_asai_one_hour_outage_per_year(self) -> None:
        # SAIDI = 1 hour → ASAI = (8760-1)/8760 ≈ 0.99988584
        asai = calculate_asai(1.0)
        assert math.isclose(asai, (HOURS_PER_YEAR - 1.0) / HOURS_PER_YEAR)

    def test_asai_clamped_to_zero(self) -> None:
        # Pathological SAIDI > 8760 → clamped to 0
        assert calculate_asai(99999.0) == 0.0

    def test_asai_clamped_to_one(self) -> None:
        # Negative SAIDI (impossible) → clamped to 1
        assert calculate_asai(-1.0) == 1.0


class TestCalculateIndices:
    """One-shot calculation of all 4 indices."""

    def test_all_indices_consistent(self) -> None:
        events = [
            InterruptionEvent(100, 2.0),
            InterruptionEvent(200, 3.0),
        ]
        idx = calculate_indices(events, total_customers=10_000)
        # SAIFI = 300/10000 = 0.03
        assert math.isclose(idx.saifi, 0.03)
        # SAIDI = (100×2 + 200×3)/10000 = 800/10000 = 0.08
        assert math.isclose(idx.saidi, 0.08)
        # CAIDI = SAIDI/SAIFI = 0.08/0.03 ≈ 2.667
        assert math.isclose(idx.caidi, 0.08 / 0.03)
        # ASAI ≈ (8760 - 0.08)/8760
        assert math.isclose(idx.asai, (8760 - 0.08) / 8760)
        assert idx.total_customers == 10_000
        assert idx.n_events == 2

    def test_text_report_includes_all_indices(self) -> None:
        idx = ReliabilityIndices(
            saifi=1.2, saidi=2.4, caidi=2.0, asai=0.9997,
            total_customers=1000, n_events=5,
        )
        text = idx.as_text_report()
        assert "SAIFI" in text and "1.2000" in text
        assert "SAIDI" in text and "2.4000" in text
        assert "CAIDI" in text and "2.0000" in text
        assert "ASAI" in text
        assert "1000" in text


# ---------------------------------------------------------------------------
# IEEE 493 Gold Book — series/parallel
# ---------------------------------------------------------------------------


class TestSystemReliability:
    def test_series_failure_rate_sum(self) -> None:
        c1 = ComponentReliability("A", mtbf_hours=8760.0, mttr_hours=10.0)
        c2 = ComponentReliability("B", mtbf_hours=4380.0, mttr_hours=5.0)
        # λA = 1, λB = 2 → series = 3
        rate = system_failure_rate_series([c1, c2])
        assert math.isclose(rate, 3.0)

    def test_series_unavailability_approximation(self) -> None:
        # Two components, q = 0.01 each → series ≈ 0.02
        c1 = ComponentReliability("A", mtbf_hours=99.0, mttr_hours=1.0)
        c2 = ComponentReliability("B", mtbf_hours=99.0, mttr_hours=1.0)
        q_series = system_unavailability_series([c1, c2])
        assert math.isclose(q_series, 0.02)

    def test_parallel_unavailability_product(self) -> None:
        # Two parallel components q=0.1 each → 0.01
        c1 = ComponentReliability("A", mtbf_hours=9.0, mttr_hours=1.0)
        c2 = ComponentReliability("B", mtbf_hours=9.0, mttr_hours=1.0)
        q_par = parallel_unavailability([c1, c2])
        assert math.isclose(q_par, 0.01)

    def test_parallel_empty_returns_zero(self) -> None:
        assert parallel_unavailability([]) == 0.0


# ---------------------------------------------------------------------------
# GUI smoke
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    return app


class TestReliabilityDialog:
    def test_dialog_builds(self, qapp) -> None:
        from app.gui.reliability_dialog import ReliabilityDialog
        dlg = ReliabilityDialog(parent=None)
        # Dialog seeds with 1 sample row
        assert dlg._table.rowCount() >= 1
        assert dlg._total_customers_spin.value() == 1000

    def test_dialog_calculate_with_sample_data(self, qapp) -> None:
        from app.gui.reliability_dialog import ReliabilityDialog
        dlg = ReliabilityDialog(parent=None)
        # Default seeded row: 100 cust, 2.5h
        dlg._on_calculate()
        text = dlg._result.toPlainText()
        assert "SAIFI" in text
        assert "SAIDI" in text

    def test_dialog_clear(self, qapp) -> None:
        from app.gui.reliability_dialog import ReliabilityDialog
        dlg = ReliabilityDialog(parent=None)
        dlg._on_clear()
        assert dlg._table.rowCount() == 0


# ---------------------------------------------------------------------------
# Acessibilidade GUI (Master Protocol garantia 7ª)
# ---------------------------------------------------------------------------


def test_main_window_wires_reliability_action() -> None:
    """Verify Análise menu has Reliability action wired."""
    import inspect
    from app.gui import main_window

    src = inspect.getsource(main_window)
    assert "_on_show_reliability" in src, (
        "MainWindow must define _on_show_reliability handler"
    )
    assert "Reliability Indices" in src, (
        "Análise menu must list Reliability Indices action"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
