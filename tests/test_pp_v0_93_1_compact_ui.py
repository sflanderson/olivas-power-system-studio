"""
tests/test_pp_v0_93_1_compact_ui.py — v0.93.1:

UI compactification (design-critique). Reduz chrome density
de 4 camadas → 2 camadas:

* Main_window icon toolbar OCULTA por default (Ctrl+Alt+T toggle)
* PpEditor toolbar reduzida 13 → 6 botões visíveis (≡ Mais
  hamburger para o resto)
* F11 "Tela cheia" REAL — oculta menu+tab+status bars +
  toolbar PpEditor + painéis (modo zen)

Cobre também os bug fixes:
* Window title rebrand para "Olivas Power System Studio"
  (era "Olivas ATP Studio" no f-string ao carregar projeto)
* Botão "Exportar ATP" removido da toolbar PpEditor
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QPushButton


@pytest.fixture(scope="module")
def qapp():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Phase 1: Main toolbar oculta por default
# ---------------------------------------------------------------------------


class TestMainToolbarHidden:

    def test_main_toolbar_hidden_by_default(self, qapp):
        """v0.93.1: barra de ícones do topo OCULTA por default
        (duplica menu Análise)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        mw.show()
        qapp.processEvents()
        assert mw._main_toolbar.isHidden(), (
            "Main toolbar deveria iniciar OCULTA em v0.93.1"
        )

    def test_toggle_action_in_view_menu(self, qapp):
        """v0.93.1: Visualizar → 'Mostrar barra de ferramentas'
        com shortcut Ctrl+Alt+T."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        # Mantém referência à action (não ao menu, evita PySide6 GC)
        action = None
        for a in mw.menuBar().actions():
            if a.text() == "Visualizar":
                action = a
                break
        assert action is not None
        view_menu = action.menu()
        items = [a.text() for a in view_menu.actions() if a.text()]
        joined = " ".join(items)
        assert (
            "barra de ferramentas" in joined.lower()
            or "toolbar" in joined.lower()
        ), f"Toggle ausente: {items}"

    def test_toggle_action_has_shortcut(self, qapp):
        """v0.93.1: Ctrl+Alt+T atalho do toggle."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        action = mw._toggle_main_toolbar_action
        assert action.shortcut().toString() == "Ctrl+Alt+T"

    def test_toggle_shows_toolbar(self, qapp):
        """v0.93.1: ativar o toggle mostra a toolbar."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        mw.show()
        qapp.processEvents()
        # Inicialmente oculta
        assert mw._main_toolbar.isHidden()
        # Aciona toggle
        mw._toggle_main_toolbar_action.setChecked(True)
        qapp.processEvents()
        assert not mw._main_toolbar.isHidden(), (
            "Toolbar deveria aparecer após toggle ON"
        )


# ---------------------------------------------------------------------------
# Phase 2: PpEditor toolbar compactada
# ---------------------------------------------------------------------------


class TestPpEditorToolbarCompact:
    """v0.93.1: PpEditor toolbar reduzida.
    v0.93.2: PpEditor toolbar OCULTA por completo (UM SÓ menu
    no topo da tela). Suas ações migraram para o menu bar
    do MainWindow + cornerWidget + atalhos."""

    def test_pp_toolbar_hidden_v0_93_2(self, qapp):
        """v0.93.2: PpEditor toolbar não é mais visível por
        default. Suas ações foram para o menu bar e cornerWidget."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        mw.show()
        qapp.processEvents()
        pp = mw.schematic_pp
        assert pp.toolbar.isHidden(), (
            "v0.93.2: PpEditor toolbar deve ser oculta por default. "
            "Apenas menu bar + tabs no topo."
        )

    def test_secondary_actions_still_exist_as_attrs(self, qapp):
        """v0.93.1+: ações continuam existindo como atributos
        (api preservada — tests legacy podem clicar via emit)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        pp = mw.schematic_pp
        for attr in (
            "act_new", "act_open", "act_save", "act_tool_select",
            "act_tool_wire", "act_undo", "act_redo", "act_zoom_reset",
            "act_refresh_datablocks", "act_run_analysis",
            "act_compact_mode",
        ):
            assert hasattr(pp, attr), (
                f"Ação {attr} deve continuar existir como atributo"
            )

    def test_more_menu_button_still_exists(self, qapp):
        """v0.93.1+: "≡ Mais" hamburger continua existindo
        (preservado como API mas oculto junto com toolbar)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        pp = mw.schematic_pp
        assert hasattr(pp, "act_more_menu")
        assert hasattr(pp, "_show_more_menu")
        assert callable(pp._show_more_menu)

    def test_run_button_in_menu_bar_corner(self, qapp):
        """v0.93.2: ▶ Executar Análise é cornerWidget do menu
        bar (canto direito). Visível sem ocupar linha extra."""
        from PySide6.QtCore import Qt
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        corner = mw.menuBar().cornerWidget(Qt.TopRightCorner)
        assert corner is not None, (
            "v0.93.2: cornerWidget do menu bar (right) deveria "
            "ser o botão ▶ Executar Análise"
        )
        assert "Executar" in corner.text()

    def test_visualizar_menu_has_panel_toggles(self, qapp):
        """v0.93.2: Visualizar menu tem toggles de Paleta/
        Propriedades/Tela cheia (migrados da PpEditor toolbar)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        action = next(
            (a for a in mw.menuBar().actions()
             if a.text() == "Visualizar"),
            None,
        )
        assert action is not None
        items = [a.text() for a in action.menu().actions() if a.text()]
        joined = " ".join(items)
        assert "Paleta" in joined, f"items: {items}"
        assert "Propriedades" in joined or "propriedades" in joined.lower()
        assert "Tela cheia" in joined or "compacto" in joined.lower()


# ---------------------------------------------------------------------------
# Phase 3: F11 Tela cheia REAL
# ---------------------------------------------------------------------------


class TestFullscreenZenMode:

    def test_compact_mode_signal_exists(self, qapp):
        """v0.93.1: PpEditor expõe signal compact_mode_changed."""
        from app.gui.schematic_pp.editor import PpEditor
        assert hasattr(PpEditor, "compact_mode_changed")

    def test_compact_mode_keeps_toolbar_hidden(self, qapp):
        """v0.93.1: ao entrar em compact mode, toolbar PpEditor
        é/permanece oculta. v0.93.2: já era oculta por default
        (UM SÓ menu no topo)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        mw.show()
        qapp.processEvents()
        pp = mw.schematic_pp
        # v0.93.2: toolbar oculta por default
        assert pp.toolbar.isHidden()
        pp.set_compact_mode(True)
        qapp.processEvents()
        # Continua oculta (compact mode é idempotente para a toolbar)
        assert pp.toolbar.isHidden(), (
            "PpEditor toolbar deve permanecer oculta em compact mode"
        )

    def test_compact_mode_hides_menu_bar(self, qapp):
        """v0.93.1: F11 oculta também menu bar do MainWindow."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        mw.show()
        qapp.processEvents()
        assert not mw.menuBar().isHidden()
        mw.schematic_pp.set_compact_mode(True)
        qapp.processEvents()
        assert mw.menuBar().isHidden()

    def test_compact_mode_hides_tab_bar(self, qapp):
        """v0.93.1: F11 oculta o tab bar (maximiza canvas)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        mw.show()
        qapp.processEvents()
        assert not mw.tabs.tabBar().isHidden()
        mw.schematic_pp.set_compact_mode(True)
        qapp.processEvents()
        assert mw.tabs.tabBar().isHidden()

    def test_compact_mode_hides_status_bar(self, qapp):
        """v0.93.1: F11 oculta status bar para máxima zen."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        mw.show()
        qapp.processEvents()
        if mw.statusBar() is not None:
            assert not mw.statusBar().isHidden()
            mw.schematic_pp.set_compact_mode(True)
            qapp.processEvents()
            assert mw.statusBar().isHidden()

    def test_compact_mode_off_restores_chrome(self, qapp):
        """v0.93.1: sair de compact mode restaura menu/tab bar.
        v0.93.2: PpEditor toolbar continua oculta sempre (UM SÓ
        menu no topo). Apenas menu bar + tab bar restauram."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        mw.show()
        qapp.processEvents()
        pp = mw.schematic_pp
        # Entra
        pp.set_compact_mode(True)
        qapp.processEvents()
        assert mw.menuBar().isHidden()
        # Sai
        pp.set_compact_mode(False)
        qapp.processEvents()
        assert not mw.menuBar().isHidden()
        assert not mw.tabs.tabBar().isHidden()
        # v0.93.2: toolbar PpEditor permanece oculta (UM SÓ menu)
        assert pp.toolbar.isHidden(), (
            "v0.93.2: PpEditor toolbar permanece oculta sempre"
        )


# ---------------------------------------------------------------------------
# Bug fixes
# ---------------------------------------------------------------------------


class TestBugFixes:

    def test_window_title_rebrand_default(self, qapp):
        """v0.93.1 bug fix: window title default é "Olivas Power
        System Studio" (era "Olivas ATP Studio" persistindo)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        title = mw.windowTitle()
        assert "ATP Studio" not in title, (
            f"Window title ainda contém 'ATP Studio': {title!r}"
        )
        assert "Power System Studio" in title, (
            f"Window title deveria ter 'Power System Studio': "
            f"{title!r}"
        )
