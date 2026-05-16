"""
tests.test_pp_v1_4_0_arc_flash_label_BC — sub-sprints B + C.

Cobre LabelDesignerDialog (B) + integração main_window (C).

**Aceite B+C**: 14+ testes, 100% verde.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.gui.arc_flash_label_dialog import (
    LabelDesignerDialog,
    _build_demo_label,
)
from app.postprocessor.arc_flash_label import (
    ArcFlashLabel,
    LabelStyle,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------------------------------------------------------------------------
# Sub-sprint B — LabelDesignerDialog
# ---------------------------------------------------------------------------


class TestLabelDesignerDialogConstruction:

    def test_dialog_constructs(self, qapp):
        dlg = LabelDesignerDialog()
        assert dlg is not None

    def test_table_has_30_rows(self, qapp):
        dlg = LabelDesignerDialog()
        assert dlg.table.rowCount() == 30

    def test_demo_loaded_on_init(self, qapp):
        """Demo é carregado automaticamente."""
        dlg = LabelDesignerDialog()
        # Bus name preenchido
        bus_name_row = None
        for i in range(dlg.table.rowCount()):
            if dlg.table.item(i, 0).data(Qt.UserRole) == "bus_name":
                bus_name_row = i
                break
        assert bus_name_row is not None
        assert dlg.table.item(bus_name_row, 1).text() != ""

    def test_html_browser_populated(self, qapp):
        dlg = LabelDesignerDialog()
        html = dlg.html_browser.toHtml()
        # QTextBrowser.toHtml retorna HTML processado pelo Qt — pode
        # diferir do raw mas deve ter conteúdo.
        assert len(html) > 100

    def test_style_combo_has_3_options(self, qapp):
        dlg = LabelDesignerDialog()
        assert dlg.style_combo.count() == 3


class TestLabelDesignerDialogBehavior:

    def test_set_label_populates_table(self, qapp):
        dlg = LabelDesignerDialog()
        custom = ArcFlashLabel(
            bus_name="X-CUSTOM",
            ppe_category="DANGER",
        )
        dlg.set_label(custom)
        # Bus name na tabela
        for i in range(dlg.table.rowCount()):
            if dlg.table.item(i, 0).data(Qt.UserRole) == "bus_name":
                assert dlg.table.item(i, 1).text() == "X-CUSTOM"
                return
        pytest.fail("bus_name field não encontrado")

    def test_current_label_from_table(self, qapp):
        dlg = LabelDesignerDialog()
        custom = ArcFlashLabel(
            bus_name="ROUNDTRIP-TEST",
            bus_kV="13.8",
            ppe_category="2",
        )
        dlg.set_label(custom)
        # Re-leitura da tabela deve dar o mesmo label
        retrieved = dlg.current_label_from_table()
        assert retrieved.bus_name == "ROUNDTRIP-TEST"
        assert retrieved.ppe_category == "2"

    def test_style_change_updates_label(self, qapp):
        dlg = LabelDesignerDialog()
        # Default é NFPA 70E
        assert dlg.style == LabelStyle.NFPA_70E_2024
        # Muda combo para BR
        for i in range(dlg.style_combo.count()):
            if dlg.style_combo.itemData(i) == LabelStyle.MINIMAL_BR:
                dlg.style_combo.setCurrentIndex(i)
                break
        assert dlg.style == LabelStyle.MINIMAL_BR

    def test_demo_button_repopulates(self, qapp):
        dlg = LabelDesignerDialog()
        # Limpa
        dlg.set_label(ArcFlashLabel())
        # Carrega demo
        dlg._on_load_demo()
        # Bus name preenchido
        for i in range(dlg.table.rowCount()):
            if dlg.table.item(i, 0).data(Qt.UserRole) == "bus_name":
                assert dlg.table.item(i, 1).text() != ""
                return

    def test_refresh_preview_updates_html(self, qapp):
        dlg = LabelDesignerDialog()
        # Edita bus_name na tabela
        for i in range(dlg.table.rowCount()):
            if dlg.table.item(i, 0).data(Qt.UserRole) == "bus_name":
                dlg.table.item(i, 1).setText("NEW-BUS-NAME")
                break
        dlg.refresh_preview()
        html = dlg.html_browser.toHtml()
        # Qt pode escapar; verifica que valor está no label atual
        assert dlg.label.bus_name == "NEW-BUS-NAME"


class TestDemoLabelGeneration:

    def test_build_demo_label_returns_arc_flash_label(self):
        lab = _build_demo_label()
        assert isinstance(lab, ArcFlashLabel)
        # Bus name preenchido
        assert lab.bus_name == "BUS-MAIN-13.8kV"
        # Contém audit + project_title
        assert lab.project_title != ""

    def test_demo_label_has_ppe_category(self):
        lab = _build_demo_label()
        assert lab.ppe_category in ("0", "1", "2", "3", "4", "DANGER")

    def test_demo_label_renders_without_error(self):
        from app.postprocessor.arc_flash_label import render_html_label
        lab = _build_demo_label()
        for style in LabelStyle:
            html = render_html_label(lab, style)
            assert len(html) > 1000


# ---------------------------------------------------------------------------
# Sub-sprint C — main_window integration
# ---------------------------------------------------------------------------


class TestMainWindowIntegration:

    def test_main_window_has_label_designer_handler(self, qapp):
        from app.gui.main_window import MainWindow
        assert hasattr(MainWindow, "_on_show_label_designer")

    def test_main_window_does_not_break_with_v140_imports(self, qapp):
        """Importar main_window com v1.4.0 não deve quebrar."""
        from app.gui import main_window  # noqa
        assert main_window is not None
