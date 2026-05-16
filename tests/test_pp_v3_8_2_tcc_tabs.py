"""v3.8.2 — D.3 TCC 3-tab pages tests.

Closes SKIPPED_BACKLOG D.3 — Categoria D 100% encerrada.
Reference: PTW Tutorial §Part 3 p.103-104.
"""

from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    return app


def _make_dialog(qapp):
    from app.gui.tcc_coordinogram import TCCCoordinogramDialog
    from app.postprocessor.tcc_curves import TCCCurve, CurveType
    curves = [
        TCCCurve("Relé F1", CurveType.IEC_VERY_INVERSE,
                 pickup_A=200, tms=0.5),
        TCCCurve("Relé F2", CurveType.IEC_STANDARD_INVERSE,
                 pickup_A=100, tms=0.3),
    ]
    dlg = TCCCoordinogramDialog(curves=curves, fault_current_A=5000)
    return dlg


# ---------------------------------------------------------------------------
# D.3 — 3-tab structure
# ---------------------------------------------------------------------------


class TestTCCDialogTabs:
    """v3.8.2 D.3 closure — 3-tab refactor."""

    def test_dialog_has_tabs_widget(self, qapp) -> None:
        dlg = _make_dialog(qapp)
        assert hasattr(dlg, "_tabs")
        from PySide6.QtWidgets import QTabWidget
        assert isinstance(dlg._tabs, QTabWidget)

    def test_dialog_has_3_tabs(self, qapp) -> None:
        dlg = _make_dialog(qapp)
        assert dlg._tabs.count() == 3

    def test_tab_titles_pt_br(self, qapp) -> None:
        dlg = _make_dialog(qapp)
        titles = [dlg._tabs.tabText(i) for i in range(dlg._tabs.count())]
        # Settings / Curves / Datablock
        assert any("Settings" in t for t in titles)
        assert any("Curves" in t for t in titles)
        assert any("Datablock" in t for t in titles)

    def test_default_tab_is_curves(self, qapp) -> None:
        """Open dialog → land on Curves tab (main view)."""
        dlg = _make_dialog(qapp)
        current = dlg._tabs.currentIndex()
        title = dlg._tabs.tabText(current)
        assert "Curves" in title

    def test_curves_tab_contains_coord_widget(self, qapp) -> None:
        from app.gui.tcc_coordinogram import TCCCoordinogramWidget
        dlg = _make_dialog(qapp)
        # The 'Curves' tab is the coord widget itself (per implementation)
        assert isinstance(dlg._tab_curves, TCCCoordinogramWidget)

    def test_settings_tab_has_fault_spinbox(self, qapp) -> None:
        from PySide6.QtWidgets import QDoubleSpinBox
        dlg = _make_dialog(qapp)
        assert hasattr(dlg, "_spin_fault_A")
        assert isinstance(dlg._spin_fault_A, QDoubleSpinBox)
        assert dlg._spin_fault_A.value() == 5000

    def test_datablock_tab_lists_curves(self, qapp) -> None:
        dlg = _make_dialog(qapp)
        assert hasattr(dlg, "_datablock_text")
        text = dlg._datablock_text.toPlainText()
        # Should mention 2 curves and their names
        assert "Total curves: 2" in text
        assert "F1" in text
        assert "F2" in text


class TestApplySettings:
    def test_apply_updates_fault_current(self, qapp) -> None:
        dlg = _make_dialog(qapp)
        # Change fault current via Settings tab
        dlg._spin_fault_A.setValue(8000)
        dlg._on_apply_settings()
        assert dlg._coord_widget._fault_current_A == 8000


# ---------------------------------------------------------------------------
# Anti-regressão — existing functionality preserved
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    """v3.8.2 D.3 must not break existing dialog APIs."""

    def test_curve_list_still_present(self, qapp) -> None:
        dlg = _make_dialog(qapp)
        assert hasattr(dlg, "_curve_list")
        assert dlg._curve_list.count() == 2

    def test_status_label_still_present(self, qapp) -> None:
        dlg = _make_dialog(qapp)
        assert hasattr(dlg, "_status_label")

    def test_c_lines_button_still_wired(self, qapp) -> None:
        dlg = _make_dialog(qapp)
        assert hasattr(dlg, "_btn_c_lines")
        assert dlg._btn_c_lines.isCheckable()

    def test_protection_filter_combo_still_present(self, qapp) -> None:
        dlg = _make_dialog(qapp)
        assert hasattr(dlg, "_cmb_protection_filter")
        # 3 modes: all / phase / ground
        assert dlg._cmb_protection_filter.count() == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
