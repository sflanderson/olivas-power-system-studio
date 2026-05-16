"""
tests/test_pp_v0_91_polish_wave2.py — v0.91: polish UX onda 2.

Cobertura
---------

* PpPalette.filter_text:
  - texto vazio mostra tudo
  - filtro case-insensitive
  - filtro match em código (R, BUS) ou label_pt
  - headers de categoria escondidos quando seção vazia
* Editor: search box atualiza filtro automaticamente.
* MainWindow.window_title:
  - mostra "*" quando .sch dirty
  - "(untitled)*" quando dirty sem path
  - clean state remove "*"
  - cleanChanged signal dispara update
* ShortcutsDialog:
  - instancia
  - tem ao menos 5 categorias
  - menu Ajuda → "Atalhos do teclado (?)"
* v0.91.1 hotfix splash layout:
  - SPLASH_HEIGHT comporta o conteúdo sem clipping
  - VERSION refletindo a sprint atual
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Palette filter
# ---------------------------------------------------------------------------


class TestPaletteFilter:

    def test_empty_filter_shows_all(self, qapp):
        from app.gui.schematic_pp.editor import PpPalette
        from PySide6.QtCore import Qt
        p = PpPalette()
        # Conta componentes (não headers — header tem UserRole=None)
        total = sum(
            1 for i in range(p.count())
            if p.item(i).data(Qt.UserRole) is not None
        )
        n_visible = p.filter_text("")
        assert n_visible == total

    def test_filter_by_code(self, qapp):
        from app.gui.schematic_pp.editor import PpPalette
        p = PpPalette()
        # Filtra por "BUS" — só BUS deve sobrar
        n = p.filter_text("BUS")
        assert n >= 1
        # E BUS NÃO está escondido
        from PySide6.QtCore import Qt
        for i in range(p.count()):
            it = p.item(i)
            if it.data(Qt.UserRole) == "BUS":
                assert not it.isHidden()
                break
        else:
            pytest.fail("BUS item não encontrado na paleta")

    def test_filter_case_insensitive(self, qapp):
        from app.gui.schematic_pp.editor import PpPalette
        p = PpPalette()
        n_lower = p.filter_text("bus")
        n_upper = p.filter_text("BUS")
        assert n_lower == n_upper

    def test_filter_no_match_hides_all(self, qapp):
        from app.gui.schematic_pp.editor import PpPalette
        p = PpPalette()
        n = p.filter_text("__zzz_no_match__")
        assert n == 0

    def test_filter_hides_empty_category_header(self, qapp):
        """Quando filtro elimina todos os items de uma seção,
        o header da seção também some."""
        from app.gui.schematic_pp.editor import PpPalette
        from PySide6.QtCore import Qt
        p = PpPalette()
        p.filter_text("__no_match__")
        # Todos os headers devem estar hidden (já que nenhum item bate)
        for i in range(p.count()):
            it = p.item(i)
            if it.data(Qt.UserRole) is None:    # header
                assert it.isHidden()

    def test_filter_restores_on_empty(self, qapp):
        """Filtro com texto, depois vazio → volta ao estado original."""
        from app.gui.schematic_pp.editor import PpPalette
        from PySide6.QtCore import Qt
        p = PpPalette()
        # Aplica filtro "BUS"
        p.filter_text("BUS")
        # Vários items hidden agora
        # Limpa
        n_after_clear = p.filter_text("")
        # Conta total de componentes
        total = sum(
            1 for i in range(p.count())
            if p.item(i).data(Qt.UserRole) is not None
        )
        assert n_after_clear == total
        # Nenhum item de componente está hidden
        for i in range(p.count()):
            it = p.item(i)
            if it.data(Qt.UserRole) is not None:
                assert not it.isHidden()


# ---------------------------------------------------------------------------
# Editor search box
# ---------------------------------------------------------------------------


class TestEditorSearchBox:

    def test_editor_has_palette_search(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        assert hasattr(ed, "palette_search")

    def test_search_text_filters_palette(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        ed.palette_search.setText("BUS")
        # Apenas o(s) item(s) BUS devem aparecer não-hidden.
        from PySide6.QtCore import Qt
        n_visible = sum(
            1 for i in range(ed.palette.count())
            if (
                ed.palette.item(i).data(Qt.UserRole) is not None
                and not ed.palette.item(i).isHidden()
            )
        )
        assert n_visible >= 1


# ---------------------------------------------------------------------------
# Title bar dirty indicator
# ---------------------------------------------------------------------------


class TestTitleBarDirty:

    def test_clean_state_no_asterisk(self, qapp):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            # Estado limpo (recém-criado)
            mw._update_window_title()
            title = mw.windowTitle()
            assert "*" not in title
        finally:
            mw.close()

    def test_dirty_untitled_shows_asterisk(self, qapp):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            # Modifica o esquemático para virar dirty
            mw.schematic_pp.add_component_by_type("R")
            mw._update_window_title()
            title = mw.windowTitle()
            # Untitled dirty
            assert "*" in title
            assert "untitled" in title.lower()
        finally:
            mw.close()

    def test_dirty_with_path_shows_filename_and_asterisk(
        self, qapp, tmp_path,
    ):
        from app.gui.main_window import MainWindow
        from app.preprocessor.templates import build_simple_13_8kV
        from app.preprocessor.qucs_sch_serializer import (
            serialize_sch_file,
        )
        sch = tmp_path / "myproject.sch"
        serialize_sch_file(build_simple_13_8kV(), str(sch))

        mw = MainWindow()
        try:
            mw.schematic_pp.load_from_sch(str(sch))
            mw._update_window_title()
            title = mw.windowTitle()
            assert "myproject.sch" in title
            assert "*" not in title.split("—")[0]
            # Modifica
            mw.schematic_pp.add_component_by_type("R")
            mw._update_window_title()
            assert "*" in mw.windowTitle()
        finally:
            mw.close()

    def test_clean_changed_signal_triggers_update(self, qapp):
        """undo_stack.cleanChanged conectado ao _update_window_title.

        Não força o signal — verifica que após mudança real
        o título reflete o estado.
        """
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            initial = mw.windowTitle()
            mw.schematic_pp.add_component_by_type("R")
            # cleanChanged dispara via signal/slot (sync no Qt)
            assert mw.windowTitle() != initial
            assert "*" in mw.windowTitle()
        finally:
            mw.close()


# ---------------------------------------------------------------------------
# ShortcutsDialog
# ---------------------------------------------------------------------------


class TestShortcutsDialog:

    def test_dialog_instantiates(self, qapp):
        from app.gui.shortcuts_dialog import ShortcutsDialog
        dlg = ShortcutsDialog()
        assert isinstance(dlg, QDialog)
        assert "Atalhos" in dlg.windowTitle()

    def test_has_categories(self, qapp):
        from app.gui.shortcuts_dialog import _SHORTCUTS
        # Pelo menos 5 categorias
        assert len(_SHORTCUTS) >= 5
        # Cada categoria tem ao menos 1 atalho
        for cat, shortcuts in _SHORTCUTS.items():
            assert len(shortcuts) > 0

    def test_includes_canvas_shortcuts(self, qapp):
        from app.gui.shortcuts_dialog import _SHORTCUTS
        joined = "\n".join(
            key for shortcuts in _SHORTCUTS.values()
            for key, _desc in shortcuts
        )
        # Atalhos canônicos devem estar presentes
        assert "R" in joined  # rotacionar
        assert "E" in joined  # espelhar
        assert "W" in joined  # wire
        assert "Esc" in joined
        assert "F1" in joined


# ---------------------------------------------------------------------------
# MainWindow integration
# ---------------------------------------------------------------------------


class TestMainWindowShortcuts:

    def test_help_menu_has_shortcuts_action(self, qapp):
        from app.gui.main_window import MainWindow
        from PySide6.QtWidgets import QMenu
        mw = MainWindow()
        try:
            help_menu = next(
                (m for m in mw.menuBar().findChildren(QMenu)
                 if m.title() == "Ajuda"), None,
            )
            assert help_menu is not None
            actions = [a.text() for a in help_menu.actions()]
            assert any("Atalhos" in a for a in actions)
        finally:
            mw.close()

    def test_on_show_shortcuts_opens_dialog(self, qapp, monkeypatch):
        """Mock exec do ShortcutsDialog para verificar
        que é chamado sem crash."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            called = []
            from app.gui import shortcuts_dialog as sd
            real_exec = sd.ShortcutsDialog.exec
            monkeypatch.setattr(
                sd.ShortcutsDialog, "exec",
                lambda self: (called.append(True), QDialog.Rejected)[1],
            )
            mw._on_show_shortcuts()
            assert called == [True]
        finally:
            mw.close()


# ---------------------------------------------------------------------------
# v0.91.1 hotfix: splash layout dimensions
# ---------------------------------------------------------------------------


class TestSplashLayoutHotfix:

    def test_splash_height_fits_content(self, qapp):
        """v0.91.1: splash height suficiente para evitar clipping
        do logo. Com layout: logo + tagline + progress + status +
        version + spacings + margins, mínimo ~520 px."""
        from app.gui.splash_screen import (
            LOGO_MAX_DIM, SPLASH_HEIGHT, SPLASH_WIDTH,
        )
        # Margins (40+40), spacings (4×16), tagline (~22), progress
        # (8), status (~22), version (~17). Total mínimo
        # = 80 + 64 + 22 + 8 + 22 + 17 + LOGO_MAX_DIM
        # = 213 + LOGO_MAX_DIM.
        min_required = 213 + LOGO_MAX_DIM
        assert SPLASH_HEIGHT >= min_required, (
            f"SPLASH_HEIGHT={SPLASH_HEIGHT} < {min_required} "
            f"(logo will clip)"
        )

    def test_splash_dimensions_reasonable(self, qapp):
        """Sanity: dimensões da splash dentro de range realista."""
        from app.gui.splash_screen import SPLASH_HEIGHT, SPLASH_WIDTH
        # Não excessivamente grande (não invade tela inteira)
        assert 400 <= SPLASH_WIDTH <= 800
        assert 400 <= SPLASH_HEIGHT <= 800

    def test_logo_max_dim_reasonable(self, qapp):
        """Logo tem espaço para respirar mas não micro."""
        from app.gui.splash_screen import LOGO_MAX_DIM
        assert 200 <= LOGO_MAX_DIM <= 400

    def test_version_is_current(self, qapp):
        """v0.91.1: VERSION reflete a sprint atual.

        Validação minima: VERSION > 0.50 (referência antiga)
        e tem 3 componentes semver.
        """
        from app.core.version import VERSION_TUPLE, parse_version
        assert len(VERSION_TUPLE) >= 3
        # Pelo menos 0.91 (referência v0.91.x)
        assert VERSION_TUPLE >= (0, 91, 0), (
            f"VERSION_TUPLE={VERSION_TUPLE} < (0, 91, 0)"
        )
