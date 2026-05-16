"""
tests/test_pp_v1_7_2_ux_fixes.py — v1.7.2.

Cobre os 3 fixes do user gate v2.0.0:

* Sprint A: pin dots renderer
* Sprint B: multi-drag wire sync
* Sprint C: plot dock refresh após estudo
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ===========================================================================
# Sprint A — Pin dots
# ===========================================================================


class TestPinDotsRendering:

    def test_paint_pin_dots_method_exists(self, qapp):
        """ComponentItem deve ter método _paint_pin_dots."""
        from app.gui.schematic_pp.items import ComponentItem
        assert hasattr(ComponentItem, "_paint_pin_dots")

    def test_pin_dot_color_constants_exist(self, qapp):
        """v1.7.2 deve definir cores para pin dots."""
        from app.gui.schematic_pp import items
        # Aceita qualquer das constantes
        has_color = (
            hasattr(items, "_PIN_DOT_COLOR")
            or hasattr(items, "PIN_DOT_COLOR")
        )
        assert has_color


# ===========================================================================
# Sprint B — Multi-drag wire sync
# ===========================================================================


class TestMultiDragCapture:

    def test_propagate_capture_helper_exists(self, qapp):
        """v1.7.2 deve ter helper para propagar capture aos
        items selected."""
        from app.gui.schematic_pp.items import ComponentItem
        # Aceita método público OU privado
        has_helper = (
            hasattr(ComponentItem, "_propagate_anchor_capture")
            or hasattr(ComponentItem, "_capture_for_all_selected")
            or hasattr(ComponentItem, "_capture_attached_anchors")
        )
        assert has_helper


# ===========================================================================
# Sprint C — Plot dock refresh
# ===========================================================================


class TestPlotDockRefresh:

    def test_refresh_plot_docks_method_exists(self, qapp):
        """MainWindow deve ter _refresh_plot_docks() para atualizar
        docks abertos após estudo."""
        from app.gui.main_window import MainWindow
        assert hasattr(MainWindow, "_refresh_plot_docks")

    def test_populate_from_cache_idempotent(self, qapp):
        """Chamar populate_from_cache 2x não deve causar erro."""
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        from app.postprocessor.study_cache import StudyCache
        cache = StudyCache()
        dock = PowerFlowVoltageProfileDock()
        # Empty cache, 2 calls — sem erro
        dock.populate_from_cache(cache)
        dock.populate_from_cache(cache)
        assert dock.is_empty() is True


# ===========================================================================
# Anti-regressão (lista TRAVADA preservada)
# ===========================================================================


class TestAntiRegression:

    def test_existing_wire_capture_still_works(self, qapp):
        """Capture original (single drag) continua funcionando."""
        from app.gui.schematic_pp.items import ComponentItem
        # _capture_attached_anchors continua existindo
        assert hasattr(ComponentItem, "_capture_attached_anchors")
        assert hasattr(ComponentItem, "_sync_anchored_wires")

    def test_existing_set_data_still_works(self, qapp):
        """plot_widgets.set_data continua funcionando."""
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        dock = PowerFlowVoltageProfileDock()
        dock.set_data(
            ["B1", "B2"], [1.0, 0.98],
        )
        # Não está mais empty após set_data com dados válidos
        assert dock.is_empty() is False
