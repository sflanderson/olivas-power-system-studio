"""
tests/test_gui_v1_7_0_plots_integration.py — v1.7.0 Sprint C.

Cobre a integração de plot docks com StudyCache:

* Dock abre vazio (empty state)
* Cache populado → dock mostra plot ao invés de empty state
* Cache vazio + abertura: empty state mantido
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestPopulateFromCache:

    def test_pf_dock_has_populate_method(self, qapp):
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        dock = PowerFlowVoltageProfileDock()
        assert hasattr(dock, "populate_from_cache")

    def test_sc_dock_has_populate_method(self, qapp):
        from app.gui.plot_widgets import ScContributionPieDock
        dock = ScContributionPieDock()
        assert hasattr(dock, "populate_from_cache")

    def test_tcc_dock_has_populate_method(self, qapp):
        from app.gui.plot_widgets import TccCurveOverlayDock
        dock = TccCurveOverlayDock()
        assert hasattr(dock, "populate_from_cache")

    def test_mc_dock_has_populate_method(self, qapp):
        from app.gui.plot_widgets import MonteCarloHistogramDock
        dock = MonteCarloHistogramDock()
        assert hasattr(dock, "populate_from_cache")


class TestPFDockPopulation:

    def test_empty_cache_keeps_empty_state(self, qapp):
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        from app.postprocessor.study_cache import StudyCache

        cache = StudyCache()
        dock = PowerFlowVoltageProfileDock()
        dock.populate_from_cache(cache)
        # Dock continua em empty state (cache vazio)
        assert dock.is_empty() is True

    def test_pf_cache_populates_plot(self, qapp):
        """Cache com PF result → dock mostra plot."""
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        from app.postprocessor.study_cache import StudyCache

        # Mock PF result
        mock_pf = MagicMock()
        mock_pf.bus_voltages_pu = {
            "BUS-1": complex(1.0, 0.0),
            "BUS-2": complex(0.98, -0.01),
            "BUS-3": complex(1.02, 0.005),
        }

        cache = StudyCache()
        cache.set_pf(mock_pf, input_hash="test_hash")

        dock = PowerFlowVoltageProfileDock()
        dock.populate_from_cache(cache)
        # Dock mudou para plot (não-vazio)
        assert dock.is_empty() is False


class TestSCDockPopulation:

    def test_empty_cache_keeps_empty_state(self, qapp):
        from app.gui.plot_widgets import ScContributionPieDock
        from app.postprocessor.study_cache import StudyCache

        cache = StudyCache()
        dock = ScContributionPieDock()
        dock.populate_from_cache(cache)
        assert dock.is_empty() is True
