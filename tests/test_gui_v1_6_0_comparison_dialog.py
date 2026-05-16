"""
tests/test_gui_v1_6_0_comparison_dialog.py — v1.6.0 Sprint F.

Cobre o dialog ``app.gui.arc_flash_comparison_dialog``:

* Inputs (V, Ibf, t, D, DC checkbox)
* Tabela de resultados
* Botão Comparar + Salvar TXT
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


class TestComparisonDialog:

    def test_dialog_loadable(self, qapp):
        from app.gui.arc_flash_comparison_dialog import (
            ArcFlashComparisonDialog,
        )
        dlg = ArcFlashComparisonDialog()
        assert dlg is not None

    def test_dialog_has_input_fields(self, qapp):
        from app.gui.arc_flash_comparison_dialog import (
            ArcFlashComparisonDialog,
        )
        dlg = ArcFlashComparisonDialog()
        # Inputs essenciais
        assert hasattr(dlg, "voltage_kV")
        assert hasattr(dlg, "Ibf_kA")
        assert hasattr(dlg, "clearing_time_ms")
        assert hasattr(dlg, "working_distance_mm")
        assert hasattr(dlg, "dc_checkbox")

    def test_dialog_has_action_buttons(self, qapp):
        from app.gui.arc_flash_comparison_dialog import (
            ArcFlashComparisonDialog,
        )
        dlg = ArcFlashComparisonDialog()
        assert hasattr(dlg, "btn_compare")
        assert hasattr(dlg, "btn_save_txt")

    def test_dialog_auto_runs_comparison(self, qapp):
        """Defaults didáticos populam a tabela na inicialização."""
        from app.gui.arc_flash_comparison_dialog import (
            ArcFlashComparisonDialog,
        )
        dlg = ArcFlashComparisonDialog()
        # Tabela deve ter pelo menos 5 linhas após auto-run
        assert dlg.results_table.rowCount() >= 5

    def test_compare_lv_panel_runs_without_crash(self, qapp):
        from app.gui.arc_flash_comparison_dialog import (
            ArcFlashComparisonDialog,
        )
        dlg = ArcFlashComparisonDialog()
        dlg.voltage_kV.setValue(0.480)
        dlg.Ibf_kA.setValue(25.0)
        dlg.clearing_time_ms.setValue(200)
        dlg.working_distance_mm.setValue(455)
        dlg.dc_checkbox.setChecked(False)
        dlg._on_compare()
        assert dlg._last_comparison is not None
        applicable = [
            r for r in dlg._last_comparison.results if r.applicable
        ]
        assert len(applicable) >= 5

    def test_dc_mode_excludes_ac_standards(self, qapp):
        from app.gui.arc_flash_comparison_dialog import (
            ArcFlashComparisonDialog,
        )
        dlg = ArcFlashComparisonDialog()
        dlg.dc_checkbox.setChecked(True)
        dlg.voltage_kV.setValue(0.125)
        dlg.Ibf_kA.setValue(2.5)
        dlg._on_compare()
        # IEEE 1584 deve estar não-aplicável em DC
        ieee_results = [
            r for r in dlg._last_comparison.results
            if "IEEE 1584" in r.standard_name
        ]
        for r in ieee_results:
            assert r.applicable is False
