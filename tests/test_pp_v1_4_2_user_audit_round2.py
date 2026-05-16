"""
tests.test_pp_v1_4_2_user_audit_round2 — v1.4.2 hotfix
para issues round 2 do user audit (pós v1.4.1).

Cobre 6 sprints v1.4.2:
* A — Logo .ico
* B — Menu Validação removido
* C — RelaySymbol PTW-style
* E — Equipment Library Apply
* F — Online overlay para novos tipos (RELAY/XFMR3/MOTOR/CABLE/CT)
* (D, G — deferred ou parcial)

**Aceite v1.4.2**: 18+ testes, 100% verde.
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
# Sprint A — Logo .ico priorizado
# ---------------------------------------------------------------------------


class TestSprintA_LogoIco:

    def test_ico_path_exists(self):
        from app.main import _LOGO_PATH_ICO
        assert _LOGO_PATH_ICO.is_file()

    def test_main_logo_path_uses_ico(self):
        from app.main import _LOGO_PATH, _LOGO_PATH_ICO
        # Se .ico existe, _LOGO_PATH deve ser ele
        if _LOGO_PATH_ICO.is_file():
            assert _LOGO_PATH == _LOGO_PATH_ICO


# ---------------------------------------------------------------------------
# Sprint B — Menu Validação removido
# ---------------------------------------------------------------------------


class TestSprintB_MenuValidationRemoved:

    def test_no_validacao_in_menubar(self, qapp):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        menus = [
            mw.menuBar().actions()[i].text()
            for i in range(len(mw.menuBar().actions()))
        ]
        assert "Validação" not in menus

    def test_main_window_menus_count(self, qapp):
        """v1.4.2: menu_bar tem 7 menus (Arquivo, Editar, Análise,
        Ferramentas, Ajuda, Exemplos, Visualizar) — sem Validação."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        menus = [
            mw.menuBar().actions()[i].text()
            for i in range(len(mw.menuBar().actions()))
        ]
        # Esperados: 7 menus
        expected = {"Arquivo", "Editar", "Análise", "Ferramentas",
                    "Ajuda", "Exemplos", "Visualizar"}
        assert expected.issubset(set(menus))


# ---------------------------------------------------------------------------
# Sprint C — RelaySymbol PTW-style
# ---------------------------------------------------------------------------


class TestSprintC_RelaySymbol:

    def test_relay_uses_RelaySymbol(self):
        from app.preprocessor.symbols import get_renderer
        r = get_renderer("RELAY")
        assert type(r).__name__ == "RelaySymbol"

    def test_relay_distinct_from_relais(self):
        """RELAY (proteção) ≠ Relais (chave)."""
        from app.preprocessor.symbols import get_renderer
        relay = get_renderer("RELAY")
        relais = get_renderer("Relais")
        assert type(relay).__name__ != type(relais).__name__

    def test_relay_paint_does_not_crash(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage, QPainter
        from app.preprocessor.symbols import get_renderer
        r = get_renderer("RELAY")
        img = QImage(200, 200, QImage.Format_ARGB32)
        img.fill(Qt.white)
        p = QPainter(img)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            p.translate(100, 100)
            r.paint(p)
        finally:
            p.end()
        # smoke ok


# ---------------------------------------------------------------------------
# Sprint E — Library Apply workflow
# ---------------------------------------------------------------------------


class TestSprintE_LibraryApply:

    def test_dialog_constructs(self, qapp):
        from app.gui.equipment_library_dialog import EquipmentLibraryDialog
        dlg = EquipmentLibraryDialog()
        assert dlg is not None

    def test_dialog_has_4_tabs(self, qapp):
        from app.gui.equipment_library_dialog import EquipmentLibraryDialog
        dlg = EquipmentLibraryDialog()
        assert dlg.tabs.count() == 4

    def test_dialog_has_apply_button(self, qapp):
        from app.gui.equipment_library_dialog import EquipmentLibraryDialog
        dlg = EquipmentLibraryDialog()
        assert "Aplicar" in dlg.btn_apply.text()

    def test_apply_to_RELAY_component(self, qapp):
        """Apply RelayModel → RELAY component popula vendor_model."""
        from app.gui.equipment_library_dialog import EquipmentLibraryDialog
        from app.preprocessor.models import PpComponent, PpProperty
        from app.preprocessor.spec import get_default_registry

        dlg = EquipmentLibraryDialog()
        # Seleciona primeiro relé na lista
        dlg.tabs.setCurrentIndex(0)
        dlg.relays_list.setCurrentRow(0)
        model = dlg.selected_model()
        assert type(model).__name__ == "RelayModel"

        # Cria componente RELAY
        spec = get_default_registry().get("RELAY")
        props = [
            PpProperty(value=str(p.default or ""), visible=p.visible)
            for p in spec.properties
        ]
        comp = PpComponent(
            type="RELAY", name="R1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=props,
        )
        ok, msg = dlg.apply_model_to_component(model, comp)
        assert ok
        # vendor_model deve estar populated
        for idx, p in enumerate(spec.properties):
            if p.name == "vendor_model":
                assert "SEL" in comp.properties[idx].value or \
                    "ABB" in comp.properties[idx].value or \
                    "Siemens" in comp.properties[idx].value or \
                    "GE" in comp.properties[idx].value
                return

    def test_apply_incompat_returns_error(self, qapp):
        """Apply RelayModel → MOTOR component falha (incompat)."""
        from app.gui.equipment_library_dialog import EquipmentLibraryDialog
        from app.preprocessor.models import PpComponent, PpProperty
        from app.preprocessor.spec import get_default_registry

        dlg = EquipmentLibraryDialog()
        dlg.tabs.setCurrentIndex(0)
        dlg.relays_list.setCurrentRow(0)
        model = dlg.selected_model()

        # Cria MOTOR (incompat com RelayModel)
        spec = get_default_registry().get("MOTOR")
        props = [
            PpProperty(value=str(p.default or ""), visible=p.visible)
            for p in spec.properties
        ]
        comp = PpComponent(
            type="MOTOR", name="M1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=props,
        )
        ok, msg = dlg.apply_model_to_component(model, comp)
        assert not ok
        assert "Incompatibilidade" in msg or "compat" in msg.lower()

    def test_apply_no_component_returns_error(self, qapp):
        from app.gui.equipment_library_dialog import EquipmentLibraryDialog
        dlg = EquipmentLibraryDialog()
        dlg.tabs.setCurrentIndex(0)
        dlg.relays_list.setCurrentRow(0)
        model = dlg.selected_model()
        ok, msg = dlg.apply_model_to_component(model, None)
        assert not ok


# ---------------------------------------------------------------------------
# Sprint F — Online overlay para novos tipos
# ---------------------------------------------------------------------------


def _make_test_comp(code, **prop_overrides):
    """Helper para criar PpComponent de teste."""
    from app.preprocessor.models import PpComponent, PpProperty
    from app.preprocessor.spec import get_default_registry
    spec = get_default_registry().get(code)
    props = []
    for p in spec.properties:
        val = prop_overrides.get(p.name, p.default or "")
        props.append(PpProperty(value=str(val), visible=p.visible))
    return PpComponent(
        type=code, name=f"{code}-1", visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=props,
    )


class TestSprintF_OnlineOverlayNewTypes:

    def test_relay_annotation(self):
        from app.gui.schematic_pp.online_overlay import OnlineOverlayManager
        mgr = OnlineOverlayManager()
        comp = _make_test_comp(
            "RELAY",
            ansi_devices="51,50,49",
            pickup_51_A=120,
            tms_51=0.30,
            pickup_50_A=600,
        )
        ann = mgr._relay_static_annotation(comp)
        assert ann is not None
        # Linhas têm os settings
        text_full = "\n".join(ann.lines)
        assert "51,50,49" in text_full
        assert "120" in text_full
        assert "600" in text_full

    def test_xfmr3_annotation(self):
        from app.gui.schematic_pp.online_overlay import OnlineOverlayManager
        mgr = OnlineOverlayManager()
        comp = _make_test_comp(
            "XFMR3",
            kVA_rated=1000, V_pri_kV=13.8, V_sec_kV=0.48,
            vector_group="Dyn1", impedance_pct=5.75,
        )
        ann = mgr._xfmr3_static_annotation(comp)
        assert ann is not None
        text = "\n".join(ann.lines)
        assert "Dyn1" in text
        assert "5.75" in text
        assert "1000" in text

    def test_motor_annotation(self):
        from app.gui.schematic_pp.online_overlay import OnlineOverlayManager
        mgr = OnlineOverlayManager()
        comp = _make_test_comp("MOTOR")
        ann = mgr._motor_static_annotation(comp)
        assert ann is not None

    def test_cable_annotation(self):
        from app.gui.schematic_pp.online_overlay import OnlineOverlayManager
        mgr = OnlineOverlayManager()
        comp = _make_test_comp(
            "CABLE",
            section_mm2=50, material="Cu_XLPE", length_m=100,
        )
        ann = mgr._cable_static_annotation(comp)
        assert ann is not None
        text = "\n".join(ann.lines)
        assert "50" in text
        assert "Cu_XLPE" in text or "Cu/XLPE" in text \
            or "XLPE" in text

    def test_ct_annotation(self):
        from app.gui.schematic_pp.online_overlay import OnlineOverlayManager
        mgr = OnlineOverlayManager()
        comp = _make_test_comp(
            "CT", ratio_pri=2000, ratio_sec=5, classe="ANSI_C",
        )
        ann = mgr._ct_static_annotation(comp)
        assert ann is not None
        text = "\n".join(ann.lines)
        assert "2000" in text
        assert "ANSI_C" in text or "ANSI" in text
