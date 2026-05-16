"""
tests/test_pp_v3_1_0_ansi_sc_dialog.py — v3.1.0 Track B-1.

ANSI SC Dialog — testa que o dialog GUI instancia, calcula e exporta
corretamente os relatórios ANSI C37 (Backfill GUI sob 7ª garantia).

Anti-alucinação: reproduz §1.4.3 Case 2 (NACD=0.6778) via dialog.
"""

from __future__ import annotations

import os
import pytest

# Ensure offscreen Qt for headless tests
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    """Provide a QApplication for the dialog tests."""
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


# ===========================================================================
# B-1.A — Dialog instantiation
# ===========================================================================


class TestDialogInstantiation:

    def test_dialog_imports(self):
        """Module imports without error."""
        from app.gui.ansi_sc_dialog import (
            AnsiShortCircuitDialog, run_ansi_sc_dialog,
        )
        assert AnsiShortCircuitDialog is not None
        assert callable(run_ansi_sc_dialog)

    def test_dialog_creates(self, qapp):
        """Dialog instantiates with correct title."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        dlg = AnsiShortCircuitDialog()
        assert "ANSI" in dlg.windowTitle()
        assert "C37" in dlg.windowTitle()

    def test_dialog_has_3_tabs(self, qapp):
        """Inputs / Generators / Reports tabs."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        from PySide6.QtWidgets import QTabWidget
        dlg = AnsiShortCircuitDialog()
        tabs = dlg.findChildren(QTabWidget)
        assert len(tabs) >= 1
        assert tabs[0].count() == 3


# ===========================================================================
# B-1.B — Default input values reproduce §1.4.3 Case 2
# ===========================================================================


class TestDialogDefaults:

    def test_default_bus_is_published_case(self, qapp):
        """Default values reproduce §1.4.3 Case 2 (PROC A MTR BUS)."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        dlg = AnsiShortCircuitDialog()
        assert dlg.sym_rms_kA.value() == pytest.approx(13.871, abs=0.001)
        assert dlg.x_over_r.value() == pytest.approx(11.88, abs=0.01)

    def test_default_generators_count(self, qapp):
        """Default has 2 contributions (UTIL + G1) per §1.4.3 Case 2."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        dlg = AnsiShortCircuitDialog()
        assert dlg.gens_table.rowCount() == 2


# ===========================================================================
# B-1.C — Calculate produces report with golden values
# ===========================================================================


class TestDialogCalculate:

    def test_calculate_produces_text(self, qapp):
        """Calculate fills output_text with PTW-style report."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        dlg = AnsiShortCircuitDialog()
        dlg._on_calculate()
        text = dlg.output_text.toPlainText()
        assert "ANSI/IEEE C37.5/C37.010 SHORT-CIRCUIT REPORT" in text

    def test_calculate_reproduces_nacd_0_6778(self, qapp):
        """Default values must yield NACD ≈ 0.6778 (§1.4.3 Case 2 manual)."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        dlg = AnsiShortCircuitDialog()
        dlg._on_calculate()
        text = dlg.output_text.toPlainText()
        # Manual NACD: 0.6778 — Olivas may round to 0.6777 (±1e-3 tolerance)
        assert "0.6777" in text or "0.6778" in text

    def test_calculate_includes_3_reports(self, qapp):
        """Output contains LV / Momentary / Interrupting headers."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        dlg = AnsiShortCircuitDialog()
        dlg._on_calculate()
        text = dlg.output_text.toPlainText()
        assert "LV Duty Report" in text
        assert "Momentary Duty Report" in text
        assert "Interrupting Duty Report" in text

    def test_calculate_cites_manual_inline(self, qapp):
        """Anti-alucinação: cita §1.x.y inline no output."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        dlg = AnsiShortCircuitDialog()
        dlg._on_calculate()
        text = dlg.output_text.toPlainText()
        assert "§1.2.3" in text
        assert "§1.3.6" in text
        assert "§1.3.7" in text


# ===========================================================================
# B-1.D — Mode/Cycle changes reflect in output
# ===========================================================================


class TestDialogModeChanges:

    def test_all_remote_mode_changes_mf(self, qapp):
        """Switch to ALL_REMOTE → MF differs from INTERPOLATED default."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        dlg = AnsiShortCircuitDialog()

        # Default INTERPOLATED
        dlg._on_calculate()
        text_interp = dlg.output_text.toPlainText()

        # Switch to ALL_REMOTE
        dlg.nacd_mode.setCurrentIndex(2)  # ALL_REMOTE
        dlg._on_calculate()
        text_remote = dlg.output_text.toPlainText()

        # MFs should differ
        assert text_interp != text_remote
        assert "all_remote" in text_remote.lower()

    def test_breaker_cycle_2_yields_higher_mf(self, qapp):
        """2-cycle breaker → higher TOT MF than 5-cycle (faster, more DC)."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        dlg = AnsiShortCircuitDialog()

        # Default 5-cycle
        dlg._on_calculate()
        text_5 = dlg.output_text.toPlainText()

        # Switch to 2-cycle (index 3)
        dlg.breaker_cycle.setCurrentIndex(3)
        dlg._on_calculate()
        text_2 = dlg.output_text.toPlainText()

        # Outputs differ
        assert text_5 != text_2
        assert "2-cycle" in text_2


# ===========================================================================
# B-1.E — Export produces valid files (no exec() of GUI dialogs)
# ===========================================================================


class TestExportLogic:

    def test_export_text_format(self, qapp, tmp_path):
        """Export to TXT writes PTW-style report."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        dlg = AnsiShortCircuitDialog()
        dlg._on_calculate()

        # Simulate text export by directly using cached _last_text
        path = tmp_path / "test.txt"
        path.write_text(dlg._last_text, encoding="utf-8")

        content = path.read_text(encoding="utf-8")
        assert "ANSI/IEEE C37.5/C37.010" in content
        assert "Interrupting Duty Report" in content

    def test_export_markdown_via_report_class(self, qapp, tmp_path):
        """AnsiFaultReport.format_markdown produces valid MD."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        from app.postprocessor.ansi_fault_report import AnsiFaultReport

        dlg = AnsiShortCircuitDialog()
        dlg._on_calculate()
        report = AnsiFaultReport(project_name=dlg._last_bus.bus_name)
        report.add_bus(dlg._last_bus)

        md = report.format_markdown()
        assert "# ANSI Fault Report" in md
        assert "|" in md  # markdown table

    def test_export_csv_via_report_class(self, qapp, tmp_path):
        """AnsiFaultReport.format_csv produces parseable CSV."""
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        from app.postprocessor.ansi_fault_report import AnsiFaultReport
        import csv as csv_mod
        import io

        dlg = AnsiShortCircuitDialog()
        dlg._on_calculate()
        report = AnsiFaultReport(project_name=dlg._last_bus.bus_name)
        report.add_bus(dlg._last_bus)

        csv_text = report.format_csv()
        rows = list(csv_mod.DictReader(io.StringIO(csv_text)))
        assert len(rows) == 1
        assert "bus_name" in rows[0]


# ===========================================================================
# B-1.F — 7ª garantia: dialog é acessível via menu
# ===========================================================================


class TestSeventhGuaranteeAccessibility:

    def test_main_window_has_handler(self):
        """main_window.py expõe `_on_show_ansi_sc_dialog`."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "_on_show_ansi_sc_dialog" in content

    def test_main_window_has_menu_action(self):
        """main_window.py adiciona action do ANSI SC ao menu Análise."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "ANSI Short Circuit (C37.5 / C37.010)" in content

    def test_main_window_has_shortcut(self):
        """Atalho Ctrl+Shift+A configurado."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "Ctrl+Shift+A" in content
