"""
tests/test_gui_v1_5_0_marketplace_dialog.py — v1.5.0 Sprint D.

Cobre o dialog ``app.gui.plugin_marketplace_dialog``:

* 3 tabs (Instalados / Disponíveis / Configurações)
* Lista de plugins com source label, version, ações
* Empty states alinhados com PTW patterns (paridade lição v1.4.5)
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


class TestMarketplaceDialog:

    def test_dialog_loadable(self, qapp):
        from app.gui.plugin_marketplace_dialog import (
            PluginMarketplaceDialog,
        )
        dlg = PluginMarketplaceDialog()
        assert dlg is not None

    def test_dialog_has_three_tabs(self, qapp):
        """Tab 1: Instalados, Tab 2: Disponíveis, Tab 3: Configurações."""
        from app.gui.plugin_marketplace_dialog import (
            PluginMarketplaceDialog,
        )
        dlg = PluginMarketplaceDialog()
        assert dlg.tabs.count() == 3
        labels = [
            dlg.tabs.tabText(i) for i in range(dlg.tabs.count())
        ]
        joined = " ".join(labels).lower()
        # palavras-chave de cada tab
        assert "instal" in joined or "installed" in joined
        assert "dispon" in joined or "available" in joined
        assert "config" in joined or "setting" in joined

    def test_installed_tab_shows_builtin_plugins(self, qapp):
        """3 plugins builtin (solar/nbr/csv) devem aparecer."""
        from app.gui.plugin_marketplace_dialog import (
            PluginMarketplaceDialog,
        )
        dlg = PluginMarketplaceDialog()
        # Lista de instalados popula com builtin discovered
        list_w = dlg.installed_list
        # Pelo menos 3 items (3 builtin)
        assert list_w.count() >= 3
        texts = [
            list_w.item(i).text() for i in range(list_w.count())
        ]
        joined = " ".join(texts).lower()
        assert "solar_pv_yield" in joined
        assert "nbr_5410_validator" in joined
        assert "csv_exporter" in joined

    def test_dialog_has_action_buttons(self, qapp):
        from app.gui.plugin_marketplace_dialog import (
            PluginMarketplaceDialog,
        )
        dlg = PluginMarketplaceDialog()
        # Botões de ação (refresh, close, eventualmente install/disable)
        assert hasattr(dlg, "btn_refresh")
        assert hasattr(dlg, "btn_close")

    def test_settings_tab_shows_plugin_dirs(self, qapp):
        """Tab 3 deve mostrar caminhos: builtin_dir e user_dir."""
        from PySide6.QtWidgets import QLabel
        from app.gui.plugin_marketplace_dialog import (
            PluginMarketplaceDialog,
        )
        dlg = PluginMarketplaceDialog()
        # Switch to settings tab
        dlg.tabs.setCurrentIndex(2)
        labels = dlg.findChildren(QLabel)
        joined = " ".join(lb.text() for lb in labels).lower()
        assert ".olivas" in joined or "plugins" in joined

    def test_refresh_does_not_crash(self, qapp):
        from app.gui.plugin_marketplace_dialog import (
            PluginMarketplaceDialog,
        )
        dlg = PluginMarketplaceDialog()
        # Click refresh — deve repopular sem crash
        dlg._on_refresh()
        # Continua tendo plugins
        assert dlg.installed_list.count() >= 1
