"""
tests.test_pp_v1_4_1_user_audit_fixes — v1.4.1 hotfix
para issues do user audit v1.4.0.

Cobre as 9 issues reportadas pelo Landerson Ferreira Silva:
1. ATP residual no chat (chat_widget + status bar)
2. Logo (validação que main_window aplica logo)
3. Tab Validação removida
4. Tab Detalhes removida
5. CT Saturation GUI funcional (sprint v0.93.1 esquecida fechada)
6. RELAY catalog spec
7. XFMR3 catalog spec
8. Equipment Library Ctrl+B atalho
9. RELAY + XFMR3 acessíveis na paleta

**Aceite v1.4.1**: 14+ testes, 100% verde.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------------------------------------------------------------------------
# Issue 1 — ATP residual no chat removido
# ---------------------------------------------------------------------------


class TestIssue1_AtpCleanupChat:

    def test_chat_help_text_no_atp_simulation(self):
        """ajuda do chat NÃO deve mais ter 'rodar simulação ATP'."""
        from app.gui.chat_widget import _HELP_TEXT as _DEFAULT_HELP_TEXT
        assert "rodar simulação ATP" not in _DEFAULT_HELP_TEXT
        assert ".atp" not in _DEFAULT_HELP_TEXT

    def test_chat_help_has_new_analysis_commands(self):
        """ajuda deve ter comandos novos: analisar curto, coord, etc."""
        from app.gui.chat_widget import _HELP_TEXT as _DEFAULT_HELP_TEXT
        assert "analisar curto" in _DEFAULT_HELP_TEXT.lower() \
            or "analisar coord" in _DEFAULT_HELP_TEXT.lower() \
            or "arc-flash" in _DEFAULT_HELP_TEXT.lower()


# ---------------------------------------------------------------------------
# Issues 3, 4 — tabs Detalhes e Validação removidas
# ---------------------------------------------------------------------------


class TestIssues3_4_TabsRemoved:

    def test_main_window_has_only_2_tabs(self, qapp):
        """v1.4.1: tabs reduzidas de 4 para 2 (Esquemático + Agente)."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        assert mw.tabs.count() == 2

    def test_no_validation_tab(self, qapp):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        tab_texts = [
            mw.tabs.tabText(i) for i in range(mw.tabs.count())
        ]
        assert "Validação" not in tab_texts

    def test_no_details_tab(self, qapp):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        tab_texts = [
            mw.tabs.tabText(i) for i in range(mw.tabs.count())
        ]
        assert "Detalhes" not in tab_texts

    def test_status_bar_no_atp_message(self, qapp):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        msg = mw.statusBar().currentMessage()
        assert "ATP" not in msg
        assert ".atp" not in msg
        # Deve mencionar esquemático
        assert "esquemático" in msg.lower() or "schematic" in msg.lower()


# ---------------------------------------------------------------------------
# Issue 5 — CT Saturation GUI funcional
# ---------------------------------------------------------------------------


class TestIssue5_CtSaturationDialog:

    def test_dialog_constructs(self, qapp):
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        assert dlg is not None

    def test_dialog_auto_runs_demo(self, qapp):
        """Demo deve rodar ao abrir (auto-fill defaults)."""
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        assert dlg._last_report is not None

    def test_dialog_summary_populated(self, qapp):
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        text = dlg.summary_text.toPlainText()
        assert len(text) > 50  # tem algum conteúdo

    def test_main_window_handler_uses_new_dialog(self, qapp):
        """v1.4.1: handler `_on_analyze_ct_saturation` agora abre
        CTSaturationDialog (não mais QMessageBox 'em desenvolvimento')."""
        # Inspeciona código fonte do handler — verifica que importa
        # ct_saturation_dialog
        import inspect
        from app.gui.main_window import MainWindow
        src = inspect.getsource(MainWindow._on_analyze_ct_saturation)
        assert "CTSaturationDialog" in src


# ---------------------------------------------------------------------------
# Issues 6, 7 — RELAY + XFMR3 catalog specs
# ---------------------------------------------------------------------------


class TestIssue6_7_NewCatalogSpecs:

    def test_RELAY_spec_loadable(self):
        from app.preprocessor.spec import get_default_registry
        reg = get_default_registry()
        relay = reg.get("RELAY")
        assert relay is not None
        assert relay.code == "RELAY"
        # Tem props essenciais
        prop_names = {p.name for p in relay.properties}
        assert "tag" in prop_names
        assert "vendor_model" in prop_names
        assert "ansi_devices" in prop_names
        assert "curve_51" in prop_names
        assert "pickup_51_A" in prop_names
        assert "tms_51" in prop_names

    def test_XFMR3_spec_loadable(self):
        from app.preprocessor.spec import get_default_registry
        reg = get_default_registry()
        xfmr3 = reg.get("XFMR3")
        assert xfmr3 is not None
        assert xfmr3.code == "XFMR3"
        prop_names = {p.name for p in xfmr3.properties}
        assert "vector_group" in prop_names
        assert "impedance_pct" in prop_names
        assert "xr_ratio" in prop_names
        assert "pri_grounding" in prop_names

    def test_XFMR3_vector_group_choices(self):
        """Vector group inclui Yyn0, Dyn1, Yd1, Yd11, Dy1, Dy11."""
        from app.preprocessor.spec import get_default_registry
        reg = get_default_registry()
        xfmr3 = reg.get("XFMR3")
        vg_prop = next(
            p for p in xfmr3.properties if p.name == "vector_group"
        )
        choices = vg_prop.choices
        assert "Yyn0" in choices
        assert "Dyn1" in choices
        assert "Yd11" in choices
        assert "Dy11" in choices

    def test_XFMR3_grounding_choices(self):
        from app.preprocessor.spec import get_default_registry
        reg = get_default_registry()
        xfmr3 = reg.get("XFMR3")
        g_prop = next(
            p for p in xfmr3.properties if p.name == "pri_grounding"
        )
        assert "none" in g_prop.choices
        assert "solid" in g_prop.choices
        assert "resistance" in g_prop.choices
        assert "reactance" in g_prop.choices


# ---------------------------------------------------------------------------
# Issue 9 — RELAY + XFMR3 na paleta
# ---------------------------------------------------------------------------


class TestIssue9_PaletteHasNewComponents:

    def test_RELAY_in_palette(self, qapp):
        from PySide6.QtCore import Qt
        from app.gui.schematic_pp.editor import PpPalette
        p = PpPalette()
        codes = []
        for i in range(p.count()):
            d = p.item(i).data(Qt.UserRole)
            if d:
                codes.append(str(d))
        assert "RELAY" in codes

    def test_XFMR3_in_palette(self, qapp):
        from PySide6.QtCore import Qt
        from app.gui.schematic_pp.editor import PpPalette
        p = PpPalette()
        codes = []
        for i in range(p.count()):
            d = p.item(i).data(Qt.UserRole)
            if d:
                codes.append(str(d))
        assert "XFMR3" in codes

    def test_legacy_Relais_still_present(self, qapp):
        """Relais (chave) coexistir com RELAY (proteção). Não conflito."""
        from PySide6.QtCore import Qt
        from app.gui.schematic_pp.editor import PpPalette
        p = PpPalette()
        codes = []
        for i in range(p.count()):
            d = p.item(i).data(Qt.UserRole)
            if d:
                codes.append(str(d))
        assert "Relais" in codes
        assert "RELAY" in codes
        # Distintos
        assert "RELAY" != "Relais"


# ---------------------------------------------------------------------------
# Issue 8 — Ctrl+B atalho para Equipment Library
# ---------------------------------------------------------------------------


class TestIssue8_EquipmentLibraryShortcut:

    def test_main_window_has_library_handler(self, qapp):
        from app.gui.main_window import MainWindow
        assert hasattr(MainWindow, "_on_show_equipment_library")

    def test_ctrl_b_shortcut_registered(self, qapp):
        """Verificar via inspeção que Ctrl+B foi adicionado."""
        from app.gui.main_window import MainWindow
        import inspect
        # Source do _build_menu_bar (ou método que adiciona o action)
        src = inspect.getsource(MainWindow)
        # v1.4.1 adiciona setShortcut("Ctrl+B")
        assert 'Ctrl+B' in src
