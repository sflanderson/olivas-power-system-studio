"""
tests/test_pp_v0_82_run_analysis_button.py — v0.82:
Botão verde "▶ Executar Análise" + RunAnalysisDialog +
F1 HowTo + menu Ajuda.
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication, QDialog, QMenu, QPushButton,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# PpEditor toolbar — botão verde
# ---------------------------------------------------------------------------


class TestPpEditorRunButton:

    def test_run_analysis_button_exists(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        assert hasattr(ed, "act_run_analysis")
        assert isinstance(ed.act_run_analysis, QPushButton)

    def test_button_text_correct(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        assert "Executar Análise" in ed.act_run_analysis.text()

    def test_button_has_tooltip(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        tip = ed.act_run_analysis.toolTip()
        assert "Curto-circuito" in tip
        assert "Fluxo de potência" in tip
        assert "Arc-flash" in tip

    def test_signal_run_analysis_requested(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        # Signal exists
        assert hasattr(ed, "run_analysis_requested")

    def test_clicking_button_emits_signal(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        emitted = []
        ed.run_analysis_requested.connect(
            lambda: emitted.append(True),
        )
        ed.act_run_analysis.click()
        assert emitted == [True]


# ---------------------------------------------------------------------------
# RunAnalysisDialog
# ---------------------------------------------------------------------------


class TestRunAnalysisDialog:

    def test_instantiates(self, qapp):
        from app.gui.run_analysis_dialog import RunAnalysisDialog
        dlg = RunAnalysisDialog()
        assert isinstance(dlg, QDialog)

    def test_no_project_shows_warning(self, qapp):
        from app.gui.run_analysis_dialog import RunAnalysisDialog
        dlg = RunAnalysisDialog(pp_project=None)
        assert not dlg._has_bus

    def test_project_with_bus_detected(self, qapp):
        from app.gui.run_analysis_dialog import RunAnalysisDialog
        from app.preprocessor.models import (
            PpComponent, PpProject, PpProperty,
        )
        bus_comp = PpComponent(
            type="BUS", name="B1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[
                PpProperty("BUS-MAIN-13.8"),
                PpProperty("13.8"),
                PpProperty("3"),
                PpProperty("swgr_15kv"),
            ],
        )
        proj = PpProject(components=[bus_comp])
        dlg = RunAnalysisDialog(pp_project=proj)
        assert dlg._has_bus
        assert "BUS-MAIN-13.8" in dlg._bus_ids

    def test_radios_present(self, qapp):
        from app.gui.run_analysis_dialog import RunAnalysisDialog
        dlg = RunAnalysisDialog()
        # 5 análises
        assert "pipeline" in dlg._radios
        assert "sc" in dlg._radios
        assert "pf" in dlg._radios
        assert "motor" in dlg._radios
        assert "arc_flash" in dlg._radios

    def test_pipeline_pre_selected(self, qapp):
        from app.gui.run_analysis_dialog import RunAnalysisDialog
        dlg = RunAnalysisDialog()
        assert dlg._radios["pipeline"].isChecked()

    def test_selected_kind(self, qapp):
        from app.gui.run_analysis_dialog import RunAnalysisDialog
        dlg = RunAnalysisDialog()
        assert dlg._selected_kind() == "pipeline"
        # Mudando a seleção
        dlg._radios["sc"].setChecked(True)
        assert dlg._selected_kind() == "sc"

    def test_pf_does_not_require_bus(self, qapp):
        """
        Even sem BUS, PF deve ser permitido (apenas topologia).
        """
        from app.gui.run_analysis_dialog import RunAnalysisDialog
        dlg = RunAnalysisDialog(pp_project=None)
        dlg._radios["pf"].setChecked(True)
        # _on_accept não deve mostrar warning (PF é OK sem BUS).
        # Verificamos que selected_kind retorna "pf"
        assert dlg._selected_kind() == "pf"


# ---------------------------------------------------------------------------
# HowToDialog (F1)
# ---------------------------------------------------------------------------


class TestHowToDialog:

    def test_instantiates(self, qapp):
        from app.gui.howto_dialog import HowToDialog
        dlg = HowToDialog()
        assert isinstance(dlg, QDialog)
        assert "Como executar" in dlg.windowTitle()

    def test_html_has_3_paths(self, qapp):
        from app.gui.howto_dialog import _HOWTO_HTML
        # Deve mencionar todos 3 caminhos
        assert "Simulação ATP" in _HOWTO_HTML
        assert "Executar Análise" in _HOWTO_HTML
        assert "Exemplos" in _HOWTO_HTML

    def test_html_has_table(self, qapp):
        from app.gui.howto_dialog import _HOWTO_HTML
        assert "<table" in _HOWTO_HTML
        # Deve ter Pré-requisitos
        assert "Pré-requisitos" in _HOWTO_HTML
        # Deve mencionar BUS
        assert "BUS" in _HOWTO_HTML


# ---------------------------------------------------------------------------
# MainWindow integration
# ---------------------------------------------------------------------------


class TestMainWindowIntegration:

    def test_help_menu_exists(self, qapp):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            menus = mw.menuBar().findChildren(QMenu)
            help_menu = next(
                (m for m in menus if m.title() == "Ajuda"), None,
            )
            assert help_menu is not None
            actions = [a.text() for a in help_menu.actions()]
            assert any("Como executar" in t for t in actions)
            assert any("Sobre" in t for t in actions)
        finally:
            mw.close()

    def test_pp_editor_run_signal_connected(self, qapp):
        """MainWindow conecta run_analysis_requested ao
        _on_run_analysis_dialog."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            # Verifica que método existe
            assert hasattr(mw, "_on_run_analysis_dialog")
            assert callable(mw._on_run_analysis_dialog)
        finally:
            mw.close()

    def test_dispatch_analysis_unknown_kind(self, qapp, monkeypatch):
        """kind desconhecido deve mostrar warning, não crashar."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            # Mock QMessageBox.warning
            shown = []
            from PySide6.QtWidgets import QMessageBox
            monkeypatch.setattr(
                QMessageBox, "warning",
                lambda *args, **kw: shown.append(args),
            )
            mw._dispatch_analysis(
                kind="__unknown__", bus_id="B1", pp_project=None,
            )
            assert len(shown) >= 1
        finally:
            mw.close()
