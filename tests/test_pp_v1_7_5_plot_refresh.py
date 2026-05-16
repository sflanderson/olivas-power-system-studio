"""
tests/test_pp_v1_7_5_plot_refresh.py — v1.7.5.

Cobre o helper ``refresh_open_plot_docks`` que atualiza docks
de Vis>Gráficos abertos após estudo rodar.
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


class TestRefreshHelper:

    def test_module_loadable(self):
        from app.gui import plot_dock_refresh  # noqa: F401

    def test_no_docks_returns_zero(self):
        """MainWindow sem docks abertos → 0 refreshes (no-op)."""
        from app.gui.plot_dock_refresh import refresh_open_plot_docks
        mw = MagicMock()
        mw._study_cache = MagicMock(return_value=MagicMock())
        # Nenhum atributo `_plot_dock_*` existe → todos None via
        # MagicMock auto-creation. Para forçar None real:
        for attr in (
            "_plot_dock_pf_voltage", "_plot_dock_sc_pie",
            "_plot_dock_tcc_overlay", "_plot_dock_mc_hist",
        ):
            setattr(mw, attr, None)
        n = refresh_open_plot_docks(mw)
        assert n == 0

    def test_refreshes_open_pf_dock(self, qapp):
        """Dock aberto com populate_from_cache → é refrescado."""
        from app.gui.plot_dock_refresh import refresh_open_plot_docks
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        from app.postprocessor.study_cache import StudyCache

        cache = StudyCache()
        # Mock PF result
        pf = MagicMock()
        pf.bus_voltages_pu = {"BUS1": complex(1.0, 0.0)}
        cache.set_pf(pf, input_hash="test")

        dock = PowerFlowVoltageProfileDock()
        # Force into "open" empty state
        assert dock.is_empty() is True

        mw = MagicMock()
        mw._study_cache = lambda: cache
        mw._plot_dock_pf_voltage = dock
        for attr in ("_plot_dock_sc_pie", "_plot_dock_tcc_overlay",
                     "_plot_dock_mc_hist"):
            setattr(mw, attr, None)

        n = refresh_open_plot_docks(mw)
        assert n == 1
        # Dock agora populado
        assert dock.is_empty() is False

    def test_anti_crash_with_broken_cache(self):
        """_study_cache lança → returns 0, não propaga."""
        from app.gui.plot_dock_refresh import refresh_open_plot_docks
        mw = MagicMock()
        mw._study_cache = MagicMock(side_effect=RuntimeError("oops"))
        n = refresh_open_plot_docks(mw)
        assert n == 0

    def test_anti_crash_with_broken_dock(self, qapp):
        """Dock cuja populate_from_cache lança → conta como skipped."""
        from app.gui.plot_dock_refresh import refresh_open_plot_docks
        from app.postprocessor.study_cache import StudyCache

        cache = StudyCache()
        bad_dock = MagicMock()
        bad_dock.populate_from_cache = MagicMock(
            side_effect=ValueError("broken")
        )

        mw = MagicMock()
        mw._study_cache = lambda: cache
        mw._plot_dock_pf_voltage = bad_dock
        for attr in ("_plot_dock_sc_pie", "_plot_dock_tcc_overlay",
                     "_plot_dock_mc_hist"):
            setattr(mw, attr, None)

        n = refresh_open_plot_docks(mw)
        # Dock falhou → não conta como sucesso
        assert n == 0
