"""
tests/test_pp_v3_1_0_ansi_utilities_dialog.py — v3.1.0 Track B-3.

ANSI Utilities Dialog (3 utilities) — Mis-coord / Conversion / TX Tap.
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


class TestAnsiUtilitiesDialog:

    def test_dialog_imports(self):
        from app.gui.ansi_utilities_dialog import (
            AnsiUtilitiesDialog, run_ansi_utilities_dialog,
        )
        assert AnsiUtilitiesDialog is not None

    def test_dialog_has_3_tabs(self, qapp):
        from app.gui.ansi_utilities_dialog import AnsiUtilitiesDialog
        from PySide6.QtWidgets import QTabWidget
        dlg = AnsiUtilitiesDialog()
        tabs = dlg.findChildren(QTabWidget)
        assert tabs[0].count() == 3


class TestMisCoordTab:

    def test_default_threshold_0_80(self, qapp):
        from app.gui.ansi_utilities_dialog import AnsiUtilitiesDialog
        dlg = AnsiUtilitiesDialog()
        assert dlg.mc_threshold.value() == pytest.approx(0.80)

    def test_default_levels_3(self, qapp):
        from app.gui.ansi_utilities_dialog import AnsiUtilitiesDialog
        dlg = AnsiUtilitiesDialog()
        assert dlg.mc_levels.value() == 3

    def test_check_coordinated_pair(self, qapp):
        """t_main < t_backup → COORDINATED."""
        from app.gui.ansi_utilities_dialog import AnsiUtilitiesDialog
        dlg = AnsiUtilitiesDialog()
        dlg.t_main.setValue(0.05)
        dlg.t_backup.setValue(0.20)
        dlg._mc_check()
        result = dlg.mc_result.toPlainText()
        assert "COORDINATED" in result

    def test_check_mis_coordination(self, qapp):
        """t_backup < t_main → MIS-COORDINATION."""
        from app.gui.ansi_utilities_dialog import AnsiUtilitiesDialog
        dlg = AnsiUtilitiesDialog()
        dlg.t_main.setValue(0.30)
        dlg.t_backup.setValue(0.10)
        dlg._mc_check()
        result = dlg.mc_result.toPlainText()
        assert "MIS-COORDINATION" in result


class TestConversionTab:

    def test_xr_from_complex_z(self, qapp):
        """X/R = X / R for E/Z method."""
        from app.gui.ansi_utilities_dialog import AnsiUtilitiesDialog
        dlg = AnsiUtilitiesDialog()
        dlg.r_input.setValue(0.065)
        dlg.x_input.setValue(0.922)
        dlg._compute_xr()
        result = dlg.xr_result.text()
        # 0.922 / 0.065 = 14.18
        assert "14.18" in result

    def test_total_to_symmetrical_conversion(self, qapp):
        """16 kA / 1.6 = 10 kA."""
        from app.gui.ansi_utilities_dialog import AnsiUtilitiesDialog
        dlg = AnsiUtilitiesDialog()
        dlg.conv_direction.setCurrentIndex(0)  # Total → Symm
        dlg.conv_input.setValue(16.0)
        dlg.conv_factor.setValue(1.6)
        dlg._convert_standard()
        result = dlg.conv_result.text()
        assert "10.0" in result

    def test_symmetrical_to_total_conversion(self, qapp):
        """10 kA × 1.6 = 16 kA."""
        from app.gui.ansi_utilities_dialog import AnsiUtilitiesDialog
        dlg = AnsiUtilitiesDialog()
        dlg.conv_direction.setCurrentIndex(1)  # Symm → Total
        dlg.conv_input.setValue(10.0)
        dlg.conv_factor.setValue(1.6)
        dlg._convert_standard()
        result = dlg.conv_result.text()
        assert "16.0" in result


class TestTransformerTapTab:

    def test_tap_minus_2_5_yields_1_0256(self, qapp):
        """Tap -2.5% (NEMA -1) → V_sec = 1.0256 (§1.4.2 Case manual)."""
        from app.gui.ansi_utilities_dialog import AnsiUtilitiesDialog
        dlg = AnsiUtilitiesDialog()
        dlg.tap_combo.setCurrentIndex(1)  # -2.5%
        dlg.tap_v_pri.setValue(1.0)
        dlg._compute_tap()
        result = dlg.tap_result.text()
        assert "1.0256" in result

    def test_slg_ratio_z0_z1_0_85(self, qapp):
        """Z0/Z1 = 0.85 → SLG/3φ = 3/(2+0.85) = 1.0526."""
        from app.gui.ansi_utilities_dialog import AnsiUtilitiesDialog
        dlg = AnsiUtilitiesDialog()
        dlg.slg_z0_z1.setValue(0.85)
        dlg._compute_slg()
        result = dlg.slg_result.text()
        assert "1.0526" in result


class TestSeventhGuaranteeAccessibility:

    def test_main_window_handler_exists(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "_on_show_ansi_utilities" in content

    def test_main_window_menu_action_exists(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "ANSI Utilities" in content
