"""
tests/test_pp_v3_1_0_decay_balanced_dialogs.py — v3.1.0 Tracks B-4 + B-5.

* B-4: Fault Decay temporal dialog
* B-5: Balanced System Studies orchestrator
"""

from __future__ import annotations

import os
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys
    return QApplication.instance() or QApplication(sys.argv)


# ===========================================================================
# B-4 Fault Decay
# ===========================================================================


class TestFaultDecayDialog:

    def test_dialog_imports(self):
        from app.gui.fault_decay_dialog import (
            FaultDecayDialog, run_fault_decay_dialog,
        )
        assert FaultDecayDialog is not None

    def test_dialog_creates(self, qapp):
        from app.gui.fault_decay_dialog import FaultDecayDialog
        dlg = FaultDecayDialog()
        assert "Decay" in dlg.windowTitle()

    def test_default_generator_decay(self, qapp):
        """Default = generator com 1000% sub, 300% steady, τ=10."""
        from app.gui.fault_decay_dialog import FaultDecayDialog
        dlg = FaultDecayDialog()
        assert dlg.i_subtransient.value() == 1000.0
        assert dlg.i_steady.value() == 300.0
        assert dlg.tau_cycles.value() == 10.0

    def test_decay_table_populated_for_generator(self, qapp):
        """Default mode = generator → decay table preenchida."""
        from app.gui.fault_decay_dialog import FaultDecayDialog
        dlg = FaultDecayDialog()
        # _generate_table is called in __init__
        assert dlg.decay_table.rowCount() > 0
        # First row: t=0, I = subtransient
        first_t = dlg.decay_table.item(0, 0).text()
        first_i = dlg.decay_table.item(0, 1).text()
        assert "0.0" in first_t
        assert "1000" in first_i

    def test_switch_to_induction_changes_table(self, qapp):
        """Switch to induction → table shows pass/fail per cycle mark."""
        from app.gui.fault_decay_dialog import FaultDecayDialog
        dlg = FaultDecayDialog()
        dlg.source_combo.setCurrentIndex(2)  # induction
        # Tabela regenerada
        rows = dlg.decay_table.rowCount()
        assert rows > 0
        # Check at least one row has "EXCLUDED" or "Active" in note column
        note = dlg.decay_table.item(0, 2).text()
        assert "EXCLUDED" in note or "Active" in note


class TestFaultDecayAccessibility:

    def test_main_window_handler_exists(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "_on_show_fault_decay_dialog" in content

    def test_main_window_menu_action_exists(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "Fault Current Decay" in content


# ===========================================================================
# B-5 Balanced System Studies
# ===========================================================================


class TestBalancedSystemStudiesDialog:

    def test_dialog_imports(self):
        from app.gui.balanced_system_studies_dialog import (
            BalancedSystemStudiesDialog, run_balanced_system_studies,
        )
        assert BalancedSystemStudiesDialog is not None

    def test_dialog_creates(self, qapp):
        from app.gui.balanced_system_studies_dialog import (
            BalancedSystemStudiesDialog,
        )
        dlg = BalancedSystemStudiesDialog()
        assert "Balanced System Studies" in dlg.windowTitle()

    def test_default_3_studies_checked(self, qapp):
        """DAPPER + LF + ANSI SC checked; IEC SC unchecked by default."""
        from app.gui.balanced_system_studies_dialog import (
            BalancedSystemStudiesDialog,
        )
        dlg = BalancedSystemStudiesDialog()
        assert dlg.cb_dapper.isChecked()
        assert dlg.cb_lf.isChecked()
        assert dlg.cb_ansi_sc.isChecked()
        assert not dlg.cb_iec_sc.isChecked()

    def test_run_studies_logs_progress(self, qapp):
        """_run_studies populates the log with status lines."""
        from app.gui.balanced_system_studies_dialog import (
            BalancedSystemStudiesDialog,
        )
        dlg = BalancedSystemStudiesDialog()
        dlg._run_studies()
        log = dlg.log_text.toPlainText()
        assert "Balanced System Studies" in log
        assert "DAPPER" in log
        assert "ANSI" in log


class TestBalancedSystemStudiesAccessibility:

    def test_main_window_handler_exists(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "_on_show_balanced_system_studies" in content

    def test_main_window_menu_action_exists(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "Balanced System Studies" in content
