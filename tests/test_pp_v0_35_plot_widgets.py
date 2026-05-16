"""
tests/test_pp_v0_35_plot_widgets.py — v0.35: plot widgets
matplotlib dockable.
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
matplotlib = pytest.importorskip("matplotlib")

from PySide6.QtWidgets import QApplication, QDockWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# 1. PowerFlowVoltageProfileDock
# ---------------------------------------------------------------------------


class TestPowerFlowVoltageProfile:

    def test_instantiates(self, qapp):
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        w = PowerFlowVoltageProfileDock()
        assert isinstance(w, QDockWidget)

    def test_set_data_renders(self, qapp):
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        w = PowerFlowVoltageProfileDock()
        w.set_data(["B1", "B2", "B3"], [1.05, 0.97, 0.85])
        # Verifica que figura tem 1 axes (subplot)
        assert len(w._figure.axes) >= 1

    def test_empty_data_shows_message(self, qapp):
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        w = PowerFlowVoltageProfileDock()
        w.set_data([], [])
        # Sem dados: ainda renderiza axes com texto
        assert len(w._figure.axes) >= 1

    def test_apply_theme_dark(self, qapp):
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        w = PowerFlowVoltageProfileDock()
        w.set_data(["B1"], [1.0])
        w.apply_theme(is_dark=True)
        assert w._is_dark is True

    def test_save_png(self, qapp, tmp_path):
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        w = PowerFlowVoltageProfileDock()
        w.set_data(["B1", "B2"], [1.05, 1.0])
        out = tmp_path / "profile.png"
        w.save_png(str(out))
        assert out.is_file()
        assert out.stat().st_size > 1000


# ---------------------------------------------------------------------------
# 2. ScContributionPieDock
# ---------------------------------------------------------------------------


class TestScContributionPie:

    def test_instantiates(self, qapp):
        from app.gui.plot_widgets import ScContributionPieDock
        w = ScContributionPieDock()
        assert isinstance(w, QDockWidget)

    def test_set_data_renders(self, qapp):
        from app.gui.plot_widgets import ScContributionPieDock
        w = ScContributionPieDock()
        w.set_data({"UTIL": 0.7, "GEN1": 0.25, "MOTOR": 0.05})
        assert len(w._figure.axes) >= 1

    def test_empty_dict_handled(self, qapp):
        from app.gui.plot_widgets import ScContributionPieDock
        w = ScContributionPieDock()
        w.set_data({})


# ---------------------------------------------------------------------------
# 3. TccCurveOverlayDock
# ---------------------------------------------------------------------------


class TestTccCurveOverlay:

    def test_instantiates(self, qapp):
        from app.gui.plot_widgets import TccCurveOverlayDock
        w = TccCurveOverlayDock()
        assert isinstance(w, QDockWidget)

    def test_set_data_with_curves(self, qapp):
        from app.gui.plot_widgets import TccCurveOverlayDock
        w = TccCurveOverlayDock()
        w.set_data([
            {
                "name": "Relay UP",
                "currents_A": [100, 500, 1000, 5000],
                "times_s": [5.0, 1.5, 0.8, 0.3],
            },
            {
                "name": "Relay DN",
                "currents_A": [100, 500, 1000, 5000],
                "times_s": [3.0, 0.8, 0.4, 0.15],
                "color": "red",
            },
        ])
        assert len(w._figure.axes) >= 1

    def test_with_fault_current_marker(self, qapp):
        from app.gui.plot_widgets import TccCurveOverlayDock
        w = TccCurveOverlayDock()
        w.set_data(
            [{
                "name": "R1",
                "currents_A": [100, 10000],
                "times_s": [10, 0.1],
            }],
            fault_current_kA=15.0,
        )

    def test_empty_curves_handled(self, qapp):
        from app.gui.plot_widgets import TccCurveOverlayDock
        w = TccCurveOverlayDock()
        w.set_data([])


# ---------------------------------------------------------------------------
# 4. MonteCarloHistogramDock
# ---------------------------------------------------------------------------


class TestMonteCarloHistogram:

    def test_instantiates(self, qapp):
        from app.gui.plot_widgets import MonteCarloHistogramDock
        w = MonteCarloHistogramDock()
        assert isinstance(w, QDockWidget)

    def test_set_data_renders(self, qapp):
        from app.gui.plot_widgets import MonteCarloHistogramDock
        w = MonteCarloHistogramDock()
        samples = [10 + i * 0.5 for i in range(100)]
        w.set_data(samples, P50=30.0, P95=50.0, P99=55.0)
        assert len(w._figure.axes) >= 1

    def test_empty_samples_handled(self, qapp):
        from app.gui.plot_widgets import MonteCarloHistogramDock
        w = MonteCarloHistogramDock()
        w.set_data([], P50=0, P95=0, P99=0)


# ---------------------------------------------------------------------------
# Integration: Monte Carlo result → plot
# ---------------------------------------------------------------------------


class TestMonteCarloIntegration:

    def test_mc_result_to_plot(self, qapp):
        """Resultado de run_monte_carlo flui pra MonteCarloHistogramDock."""
        from app.gui.plot_widgets import MonteCarloHistogramDock
        from app.postprocessor.arc_flash import ArcFlashCase
        from app.postprocessor.arc_flash_monte_carlo import (
            ArcFlashUncertainty, run_monte_carlo,
        )
        from app.standards.nbr17227 import (
            ElectrodeConfig, EquipmentClass,
        )

        case = ArcFlashCase(
            bus_name="X", rated_voltage_kV=13.8,
            bolted_fault_current_kA=18.0,
            arc_clearing_time_ms=200.0,
            equipment_class=EquipmentClass.SWITCHGEAR_15KV,
            electrode_config=ElectrodeConfig.VCB,
        )
        result = run_monte_carlo(
            case, ArcFlashUncertainty(),
            n_samples=200, random_seed=42,
        )
        w = MonteCarloHistogramDock()
        w.set_data(
            list(result.samples_E_J_per_cm2),
            P50=result.P50_J_per_cm2,
            P95=result.P95_J_per_cm2,
            P99=result.P99_J_per_cm2,
        )
        assert len(w._figure.axes) >= 1
