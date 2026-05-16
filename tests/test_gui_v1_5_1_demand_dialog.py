"""
tests/test_gui_v1_5_1_demand_dialog.py — v1.5.1 Sprint D.

Cobre o dialog ``app.gui.demand_load_dialog``:

* Tabela de entries (input)
* Botão Calcular → popula sumário + tabs por categoria
* Salvar TXT / XLSX
* Empty state alinhado com PTW lessons (paridade v1.4.5/v1.5.0)
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


class TestDemandLoadDialog:

    def test_dialog_loadable(self, qapp):
        from app.gui.demand_load_dialog import DemandLoadDialog
        dlg = DemandLoadDialog()
        assert dlg is not None

    def test_dialog_has_tabs_for_results(self, qapp):
        """Tabs: Sumário, Por Categoria, Detalhe."""
        from app.gui.demand_load_dialog import DemandLoadDialog
        dlg = DemandLoadDialog()
        assert dlg.tabs.count() >= 2

    def test_dialog_has_action_buttons(self, qapp):
        from app.gui.demand_load_dialog import DemandLoadDialog
        dlg = DemandLoadDialog()
        assert hasattr(dlg, "btn_calculate")
        assert hasattr(dlg, "btn_add_entry")
        assert hasattr(dlg, "btn_save_txt")
        assert hasattr(dlg, "btn_save_xlsx")

    def test_add_entry_creates_row(self, qapp):
        from app.gui.demand_load_dialog import DemandLoadDialog
        dlg = DemandLoadDialog()
        before = dlg.entries_table.rowCount()
        dlg._on_add_entry()
        after = dlg.entries_table.rowCount()
        assert after == before + 1

    def test_calculate_with_demo_entries_runs(self, qapp):
        """Defaults didáticos populam ≥1 entry; Calcular deve funcionar."""
        from app.gui.demand_load_dialog import DemandLoadDialog
        dlg = DemandLoadDialog()
        # Construtor já adiciona entries didáticas
        assert dlg.entries_table.rowCount() >= 1
        # Calcular não deve crashar
        dlg._on_calculate()
        # _last_report é populado
        assert dlg._last_report is not None
        assert dlg._last_report.total_connected_kVA > 0

    def test_summary_tab_shows_totals_after_calculate(self, qapp):
        from app.gui.demand_load_dialog import DemandLoadDialog
        dlg = DemandLoadDialog()
        dlg._on_calculate()
        # Aba Sumário (índice 0) deve ter texto
        summary_text = dlg.summary_text.toPlainText()
        assert "Connected" in summary_text or "kVA" in summary_text

    def test_category_combobox_has_22_options(self, qapp):
        """ComboBox de categoria deve listar todas as 22 categorias."""
        from app.gui.demand_load_dialog import DemandLoadDialog
        dlg = DemandLoadDialog()
        # Adiciona uma row para garantir que combobox foi criado
        dlg._on_add_entry()
        # ComboBox da última row
        row = dlg.entries_table.rowCount() - 1
        combo = dlg.entries_table.cellWidget(row, 1)
        assert combo is not None
        # ≥22 categorias
        assert combo.count() >= 22
