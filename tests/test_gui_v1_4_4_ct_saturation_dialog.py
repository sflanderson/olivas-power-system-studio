"""
tests.test_gui_v1_4_4_ct_saturation_dialog — v1.4.4 Sprint G.

Cobre integração GUI:

* Dialog cria 4 tabs (Sumário + Nível 1 + Nível 2 + Nível 3)
* Botões "Carregar JSON" / "Salvar TXT" / "Salvar XLSX" presentes
* Workflow refinamento (botão "Re-dimensionar para próxima classe")
* Auto-run com defaults didáticos
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


class TestCTSaturationDialog:

    def test_dialog_loads(self, qapp):
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        assert dlg is not None

    def test_dialog_has_4_tabs(self, qapp):
        """Sumário + 3 plots Nível 1/2/3."""
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        assert hasattr(dlg, "results_tabs")
        assert dlg.results_tabs.count() == 4
        labels = [
            dlg.results_tabs.tabText(i)
            for i in range(dlg.results_tabs.count())
        ]
        # Tab labels (com emojis ou sem) — checa keywords
        joined = " ".join(labels).lower()
        assert "sum" in joined or "rio" in joined  # Sumário
        # 3 níveis
        assert "1" in joined
        assert "2" in joined
        assert "3" in joined

    def test_dialog_has_save_buttons(self, qapp):
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        # Atributos de botões de salvar
        assert hasattr(dlg, "btn_save_txt")
        assert hasattr(dlg, "btn_save_xlsx")

    def test_dialog_has_load_json_button(self, qapp):
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        assert hasattr(dlg, "btn_load_json")

    def test_dialog_has_redimension_button(self, qapp):
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        assert hasattr(dlg, "btn_redimension")

    def test_dialog_auto_runs_analysis(self, qapp):
        """Após __init__, _last_report deve estar populado."""
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        assert dlg._last_report is not None

    def test_redimension_increases_class(self, qapp):
        """Click em redimensionar deve aumentar CT_Rating_C."""
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        # Setup falha: classe baixa para forçar
        dlg.CT_Rating_C.setValue(100.0)
        dlg.I_fault.setValue(28.0)
        dlg._on_analyze()
        before = dlg.CT_Rating_C.value()
        dlg._on_redimension()
        after = dlg.CT_Rating_C.value()
        assert after > before, (
            f"Esperava aumento da classe; before={before} after={after}"
        )
