"""
tests/test_pp_v1_7_0_window_state.py — v1.7.0 Sprint A.

Cobre o módulo ``app.gui.window_state_mixin``.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestEnableWindowControls:

    def test_module_loadable(self):
        from app.gui import window_state_mixin  # noqa: F401

    def test_adds_maximize_hint(self, qapp):
        from PySide6.QtCore import Qt
        from app.gui.window_state_mixin import enable_window_controls
        dlg = QDialog()
        enable_window_controls(dlg)
        flags = dlg.windowFlags()
        assert bool(flags & Qt.WindowMaximizeButtonHint)

    def test_adds_minimize_hint(self, qapp):
        from PySide6.QtCore import Qt
        from app.gui.window_state_mixin import enable_window_controls
        dlg = QDialog()
        enable_window_controls(dlg)
        flags = dlg.windowFlags()
        assert bool(flags & Qt.WindowMinimizeButtonHint)

    def test_keeps_close_hint(self, qapp):
        from PySide6.QtCore import Qt
        from app.gui.window_state_mixin import enable_window_controls
        dlg = QDialog()
        enable_window_controls(dlg)
        flags = dlg.windowFlags()
        assert bool(flags & Qt.WindowCloseButtonHint)

    def test_with_settings_key_does_not_crash(self, qapp):
        """Mesmo com settings vazio/inexistente, não deve crashar."""
        from app.gui.window_state_mixin import enable_window_controls
        dlg = QDialog()
        enable_window_controls(dlg, settings_key="test_dialog_xyz")
        # Just verify no exception


class TestDialogIntegration:
    """Verifica que dialogs existentes ficam com window controls."""

    def test_ct_saturation_dialog_has_maximize(self, qapp):
        from PySide6.QtCore import Qt
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        assert bool(dlg.windowFlags() & Qt.WindowMaximizeButtonHint)

    def test_demand_load_dialog_has_maximize(self, qapp):
        from PySide6.QtCore import Qt
        from app.gui.demand_load_dialog import DemandLoadDialog
        dlg = DemandLoadDialog()
        assert bool(dlg.windowFlags() & Qt.WindowMaximizeButtonHint)

    def test_plugin_marketplace_dialog_has_maximize(self, qapp):
        from PySide6.QtCore import Qt
        from app.gui.plugin_marketplace_dialog import (
            PluginMarketplaceDialog,
        )
        dlg = PluginMarketplaceDialog()
        assert bool(dlg.windowFlags() & Qt.WindowMaximizeButtonHint)

    def test_arc_flash_comparison_dialog_has_maximize(self, qapp):
        from PySide6.QtCore import Qt
        from app.gui.arc_flash_comparison_dialog import (
            ArcFlashComparisonDialog,
        )
        dlg = ArcFlashComparisonDialog()
        assert bool(dlg.windowFlags() & Qt.WindowMaximizeButtonHint)
