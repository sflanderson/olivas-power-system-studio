"""
tests.test_pp_v1_4_3_breaker_component — Sprint D.

Cobre BREAKER.ocomp (disjuntor genérico controlado por relé):
* spec loadable (15 properties, 3 pins)
* renderer = CircuitBreakerSymbol (PTW-style)
* paleta tem BREAKER
* Library apply BreakerModel → BREAKER funciona
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


class TestBreakerSpec:

    def test_BREAKER_spec_loadable(self):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("BREAKER")
        assert spec is not None
        assert spec.code == "BREAKER"
        assert spec.label_pt.startswith("Disjuntor")

    def test_BREAKER_has_3_pins(self):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("BREAKER")
        pin_names = {p.name for p in spec.pins}
        assert pin_names == {"T1", "T2", "Trip_in"}

    def test_BREAKER_has_essential_properties(self):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("BREAKER")
        prop_names = {p.name for p in spec.properties}
        # Ratings essenciais
        assert "tag" in prop_names
        assert "vendor_model" in prop_names
        assert "rated_voltage_kV" in prop_names
        assert "rated_current_A" in prop_names
        assert "breaking_capacity_kA" in prop_names
        assert "mechanism" in prop_names
        assert "relay_link_tag" in prop_names

    def test_mechanism_choices(self):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("BREAKER")
        m_prop = next(
            p for p in spec.properties if p.name == "mechanism"
        )
        assert "vacuum" in m_prop.choices
        assert "SF6" in m_prop.choices
        assert "MCB" in m_prop.choices

    def test_BREAKER_atp_supported_false(self):
        """BREAKER é orientado a análise NBR/IEEE — não ATP."""
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("BREAKER")
        assert spec.atp_supported is False


class TestBreakerSymbol:

    def test_BREAKER_renderer_is_circuit_breaker(self, qapp):
        from app.preprocessor.symbols import get_renderer
        r = get_renderer("BREAKER")
        # PTW override mapeia para CircuitBreakerSymbol (quadrado+cruz)
        assert type(r).__name__ == "CircuitBreakerSymbol"

    def test_BREAKER_paint_does_not_crash(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage, QPainter
        from app.preprocessor.symbols import get_renderer

        r = get_renderer("BREAKER")
        img = QImage(200, 200, QImage.Format_ARGB32)
        img.fill(Qt.white)
        p = QPainter(img)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            p.translate(100, 100)
            r.paint(p)
        finally:
            p.end()


class TestBreakerInPalette:

    def test_BREAKER_in_palette(self, qapp):
        from PySide6.QtCore import Qt
        from app.gui.schematic_pp.editor import PpPalette
        p = PpPalette()
        codes = []
        for i in range(p.count()):
            d = p.item(i).data(Qt.UserRole)
            if d:
                codes.append(str(d))
        assert "BREAKER" in codes


class TestBreakerLibraryApply:

    def test_apply_BreakerModel_to_BREAKER_component(self, qapp):
        """Library Apply BreakerModel → BREAKER popula vendor_model."""
        from app.gui.equipment_library_dialog import EquipmentLibraryDialog
        from app.preprocessor.models import PpComponent, PpProperty
        from app.preprocessor.spec import get_default_registry

        dlg = EquipmentLibraryDialog()
        # Tab 3 = Disjuntores
        dlg.tabs.setCurrentIndex(3)
        dlg.breakers_list.setCurrentRow(0)
        model = dlg.selected_model()
        assert type(model).__name__ == "BreakerModel"

        # Cria BREAKER component
        spec = get_default_registry().get("BREAKER")
        props = [
            PpProperty(value=str(p.default or ""), visible=p.visible)
            for p in spec.properties
        ]
        comp = PpComponent(
            type="BREAKER", name="Q1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=props,
        )
        ok, msg = dlg.apply_model_to_component(model, comp)
        assert ok
        # vendor_model deve estar populated
        for idx, p in enumerate(spec.properties):
            if p.name == "vendor_model":
                assert len(comp.properties[idx].value) > 0
                return
