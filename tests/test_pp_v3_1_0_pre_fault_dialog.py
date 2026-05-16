"""
tests/test_pp_v3_1_0_pre_fault_dialog.py — v3.1.0 Track B-2.

Pre-Fault Voltage Settings Dialog — testa instanciação, defaults,
combined worst-case calculator, get_settings() consumível pelo caller.
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


class TestPreFaultDialogInstantiation:

    def test_dialog_imports(self):
        from app.gui.pre_fault_voltage_dialog import (
            PreFaultVoltageDialog, run_pre_fault_voltage_dialog,
        )
        assert PreFaultVoltageDialog is not None
        assert callable(run_pre_fault_voltage_dialog)

    def test_dialog_creates(self, qapp):
        from app.gui.pre_fault_voltage_dialog import PreFaultVoltageDialog
        dlg = PreFaultVoltageDialog()
        assert "Pre-Fault" in dlg.windowTitle()


class TestPreFaultDialogDefaults:

    def test_default_mode_pu_all(self, qapp):
        """Default mode = PU_ALL (index 0)."""
        from app.gui.pre_fault_voltage_dialog import PreFaultVoltageDialog
        dlg = PreFaultVoltageDialog()
        assert dlg.mode_combo.currentIndex() == 0

    def test_tolerance_table_3_rows(self, qapp):
        """Util / Cable / TX rows."""
        from app.gui.pre_fault_voltage_dialog import PreFaultVoltageDialog
        dlg = PreFaultVoltageDialog()
        assert dlg.tol_table.rowCount() == 3

    def test_tolerance_defaults_match_module(self, qapp):
        """Tolerance values match `app.postprocessor.pre_fault_voltage` defaults."""
        from app.gui.pre_fault_voltage_dialog import PreFaultVoltageDialog
        dlg = PreFaultVoltageDialog()
        # Utility row: 0.95, 1.00, 1.05
        assert float(dlg.tol_table.item(0, 1).text()) == pytest.approx(0.95)
        assert float(dlg.tol_table.item(0, 3).text()) == pytest.approx(1.05)
        # Transformer row: 0.975, 1.00, 1.025
        assert float(dlg.tol_table.item(2, 1).text()) == pytest.approx(0.975)
        assert float(dlg.tol_table.item(2, 3).text()) == pytest.approx(1.025)


class TestPreFaultCombinedCalculator:

    def test_max_scenario_yields_product_of_maxes(self, qapp):
        """V_combined max = 1.05 × 1.00 × 1.025 = 1.07625"""
        from app.gui.pre_fault_voltage_dialog import PreFaultVoltageDialog
        dlg = PreFaultVoltageDialog()
        dlg.scenario_combo.setCurrentIndex(0)  # max
        dlg._update_combined_voltage()
        text = dlg.combined_label.text()
        assert "1.0763" in text or "1.0762" in text  # rounding tolerance

    def test_min_scenario_yields_product_of_mins(self, qapp):
        """V_combined min = 0.95 × 1.00 × 0.975 = 0.92625"""
        from app.gui.pre_fault_voltage_dialog import PreFaultVoltageDialog
        dlg = PreFaultVoltageDialog()
        dlg.scenario_combo.setCurrentIndex(2)  # min
        dlg._update_combined_voltage()
        text = dlg.combined_label.text()
        assert "0.9263" in text or "0.9262" in text


class TestPreFaultGetSettings:

    def test_get_settings_returns_dict(self, qapp):
        from app.gui.pre_fault_voltage_dialog import PreFaultVoltageDialog
        dlg = PreFaultVoltageDialog()
        settings = dlg.get_settings()
        assert "mode" in settings
        assert "default_voltage_pu" in settings
        assert "utility_tolerance" in settings


class TestSeventhGuaranteeAccessibility:

    def test_main_window_handler_exists(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "_on_show_pre_fault_voltage_dialog" in content

    def test_main_window_menu_action_exists(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "Pre-Fault Voltage Settings" in content
