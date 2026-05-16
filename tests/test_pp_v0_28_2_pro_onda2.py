"""
tests/test_pp_v0_28_2_pro_onda2.py — v0.28.2-PRO Onda 2:
GUI foundation tests.

Cobre:

* 2.1: Menu Análise existe com 5+ entries.
* 2.2: Toolbar primária com 6+ actions.
* 2.3: WelcomeDialog instanciável.
* 2.4: Recent files persistem em QSettings.
* 2.5: Modified-state indicator atualiza window title.
"""

from __future__ import annotations

import pytest

# PySide6 pode não estar disponível em CI minimalista
PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QDialog, QMainWindow, QMenu, QToolBar,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def main_window(qapp):
    from app.gui.main_window import MainWindow
    mw = MainWindow()
    yield mw
    mw.close()


# ---------------------------------------------------------------------------
# Onda 2.1 — Menu Análise
# ---------------------------------------------------------------------------


class TestAnalysisMenu:

    def test_analysis_menu_exists(self, main_window):
        menus = main_window.menuBar().findChildren(QMenu)
        titles = [m.title() for m in menus]
        # Deve haver um menu com "Análise"
        assert any("Análise" in t for t in titles)

    def test_analysis_menu_has_5_entries(self, main_window):
        menus = main_window.menuBar().findChildren(QMenu)
        analysis = next(
            (m for m in menus if "Análise" in m.title()), None,
        )
        assert analysis is not None
        # 5 ações + 2 separadores
        actions = [a for a in analysis.actions() if a.text()]
        assert len(actions) >= 5

    def test_analysis_menu_has_postprocessor_keywords(
        self, main_window,
    ):
        menus = main_window.menuBar().findChildren(QMenu)
        analysis = next(
            (m for m in menus if "Análise" in m.title()), None,
        )
        all_text = " ".join(a.text() for a in analysis.actions())
        # v0.92: Verifica os 5 estudos expostos. Em v0.92 o item
        # "Partida de motor" foi reclassificado como
        # "Balanço de carga / partida de motor (IEEE 141)" — o
        # match é case-insensitive em "partida de motor".
        assert "Curto-circuito" in all_text
        assert "Fluxo de potência" in all_text
        assert "partida de motor" in all_text.lower()
        assert "Arc-flash" in all_text
        assert "barramento" in all_text


# ---------------------------------------------------------------------------
# Onda 2.2 — Toolbar primária
# ---------------------------------------------------------------------------


class TestPrimaryToolbar:

    def test_toolbar_exists(self, main_window):
        # _main_toolbar é o atributo que adicionamos
        assert hasattr(main_window, "_main_toolbar")
        assert isinstance(main_window._main_toolbar, QToolBar)

    def test_toolbar_has_actions(self, main_window):
        actions = main_window._main_toolbar.actions()
        # Open, Save, Validate, Diff, Run, Pipeline, SC + separadores
        assert len(actions) >= 7

    def test_toolbar_run_atp_shortcut(self, main_window):
        """v0.92.1: F5 reaproveitado para 'Estudo do barramento'.
        ATP run button foi REMOVIDO da toolbar (integração ATP
        desvinculada da UI principal)."""
        actions = main_window._main_toolbar.actions()
        # Não deve mais existir 'Run ATP'
        run_atp = next(
            (a for a in actions if "Run ATP" in a.text()), None,
        )
        assert run_atp is None, (
            "v0.92.1: 'Run ATP' foi removido da toolbar"
        )
        # F5 agora é Estudo do barramento
        f5_action = next(
            (a for a in actions if a.shortcut().toString() == "F5"),
            None,
        )
        assert f5_action is not None, (
            "F5 deve estar atribuído a alguma action da toolbar"
        )
        assert "Estudo" in f5_action.text(), (
            f"F5 deve ser 'Estudo do barramento', got {f5_action.text()!r}"
        )

    def test_toolbar_pipeline_shortcut(self, main_window):
        actions = main_window._main_toolbar.actions()
        pipeline_action = next(
            (a for a in actions if "Estudo" in a.text()), None,
        )
        assert pipeline_action is not None


# ---------------------------------------------------------------------------
# Onda 2.3 — Welcome dialog
# ---------------------------------------------------------------------------


class TestWelcomeDialog:

    def test_dialog_instantiable(self, qapp):
        from app.gui.welcome_dialog import WelcomeDialog
        dlg = WelcomeDialog(parent=None, recent_files=None)
        # v0.92.2: rebrand para Olivas Power System Studio
        assert dlg.windowTitle() == "Bem-vindo ao Olivas Power System Studio"
        assert dlg.isModal()

    def test_dialog_with_recent_files(self, qapp):
        from app.gui.welcome_dialog import WelcomeDialog
        dlg = WelcomeDialog(
            parent=None,
            recent_files=["/path/file1.atp", "/path/file2.sch"],
        )
        assert dlg.recent_list is not None
        assert dlg.recent_list.count() == 2

    def test_should_show_welcome_default(self, tmp_path):
        from app.gui.welcome_dialog import should_show_welcome
        settings = QSettings(
            str(tmp_path / "test.ini"), QSettings.IniFormat,
        )
        # Default deve ser True
        assert should_show_welcome(settings) is True

    def test_remember_dont_show(self, tmp_path):
        from app.gui.welcome_dialog import (
            remember_dont_show, should_show_welcome,
        )
        settings = QSettings(
            str(tmp_path / "test.ini"), QSettings.IniFormat,
        )
        remember_dont_show(settings)
        assert should_show_welcome(settings) is False


# ---------------------------------------------------------------------------
# Onda 2.4 — Recent files
# ---------------------------------------------------------------------------


class TestRecentFiles:

    def test_load_recent_empty(self, main_window):
        # Pode haver lista de testes anteriores em QSettings; só
        # verifica que retorna lista
        recent = main_window._load_recent_files()
        assert isinstance(recent, list)

    def test_add_to_recent(self, main_window, tmp_path):
        f = tmp_path / "test.atp"
        f.write_text("BEGIN NEW DATA CASE\nC test\nBLANK")
        path = str(f)

        # Limpa primeiro
        main_window._save_recent_files([])
        main_window._add_to_recent(path)

        recent = main_window._load_recent_files()
        assert path in recent or any(
            str(f.resolve()) == p for p in recent
        )

    def test_recent_no_duplicates(self, main_window, tmp_path):
        f = tmp_path / "dup.atp"
        f.write_text("BEGIN")
        path = str(f.resolve())

        main_window._save_recent_files([])
        main_window._add_to_recent(path)
        main_window._add_to_recent(path)
        main_window._add_to_recent(path)

        recent = main_window._load_recent_files()
        # Path deve aparecer exatamente 1×
        assert recent.count(path) == 1

    def test_recent_max_limit(self, main_window, tmp_path):
        from app.gui.main_window import RECENT_FILES_MAX
        main_window._save_recent_files([])
        # Adiciona mais que RECENT_FILES_MAX
        for i in range(RECENT_FILES_MAX + 5):
            f = tmp_path / f"file{i}.atp"
            f.write_text("X")
            main_window._add_to_recent(str(f.resolve()))
        recent = main_window._load_recent_files()
        assert len(recent) <= RECENT_FILES_MAX


# ---------------------------------------------------------------------------
# Onda 2.5 — Modified state indicator
# ---------------------------------------------------------------------------


class TestModifiedState:

    def test_window_title_no_modification(self, main_window):
        main_window._active_case = None
        main_window._update_window_title()
        assert "Olivas" in main_window.windowTitle()
        assert "*" not in main_window.windowTitle()

    def test_mark_modified_adds_asterisk(self, main_window, tmp_path):
        f = tmp_path / "test.atp"
        main_window._active_case = str(f)
        main_window._mark_modified(str(f))
        assert "*" in main_window.windowTitle()

    def test_mark_clean_removes_asterisk(self, main_window, tmp_path):
        f = tmp_path / "test.atp"
        main_window._active_case = str(f)
        main_window._mark_modified(str(f))
        assert "*" in main_window.windowTitle()
        main_window._mark_clean(str(f))
        assert "*" not in main_window.windowTitle()

    def test_is_modified(self, main_window, tmp_path):
        f = tmp_path / "test.atp"
        path = str(f)
        assert main_window._is_modified(path) is False
        main_window._mark_modified(path)
        assert main_window._is_modified(path) is True
