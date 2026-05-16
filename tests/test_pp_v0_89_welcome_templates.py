"""
tests/test_pp_v0_89_welcome_templates.py — v0.89: templates
de onboarding no welcome dialog.

Cobertura
---------

* Templates module: 3 builders retornam PpProject válido.
* Cada template tem ao menos 1 BUS, 1 Vac, 1 GND.
* Wires conectam endpoints alinhados com pinos (snap-aware).
* Round-trip: serialize → parse devolve o mesmo (componentes
  + wires preservados).
* Registry: get_template_builder, build_template, TEMPLATES.
* Welcome dialog: _TemplateCard widget, template_requested signal.
* MainWindow handler: _on_pp_new_from_template carrega projeto.
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Templates module
# ---------------------------------------------------------------------------


class TestTemplateBuilders:

    def test_simple_13_8kV(self):
        from app.preprocessor.templates import build_simple_13_8kV
        proj = build_simple_13_8kV()
        # v0.91.12: Vac + BUS + R_LOAD + GND = 4 (era 3, mas
        # adicionada carga R para tornar runnable em ATP).
        assert len(proj.components) == 4
        types = [c.type for c in proj.components]
        assert "Vac" in types
        assert "BUS" in types
        assert "R" in types     # v0.91.12: R_LOAD
        assert "GND" in types
        # Pelo menos 1 wire
        assert len(proj.wires) >= 1

    def test_industrial_480V(self):
        from app.preprocessor.templates import build_industrial_480V
        proj = build_industrial_480V()
        # v0.91.3: Vac + BUS-MV + R_FEED + L_FEED + BUS-LV + GND = 6
        # (substituiu Tr por R+L para topologia 1-line vertical)
        assert len(proj.components) == 6
        types = [c.type for c in proj.components]
        assert types.count("BUS") == 2
        assert "R" in types          # R_FEED
        assert "L" in types          # L_FEED
        assert "Vac" in types
        assert "GND" in types
        # Verifica que existem 2 níveis de tensão
        bus_voltages = [
            float(c.get(1)) for c in proj.components if c.type == "BUS"
        ]
        assert max(bus_voltages) > 1.0
        assert min(bus_voltages) < 1.0

    def test_dual_bus_substation(self):
        from app.preprocessor.templates import build_dual_bus_substation
        proj = build_dual_bus_substation()
        # 2 Vac + 2 BUS + 2 GND = 6
        assert len(proj.components) == 6
        types = [c.type for c in proj.components]
        assert types.count("Vac") == 2
        assert types.count("BUS") == 2
        assert types.count("GND") == 2
        # Wire de tie tem label "TIE"
        labels = [w.label for w in proj.wires]
        assert "TIE" in labels

    def test_all_templates_grid_aligned(self):
        """Coordenadas em múltiplos de 10 (grid v0.85)."""
        from app.preprocessor.templates import (
            build_dual_bus_substation,
            build_industrial_480V,
            build_simple_13_8kV,
        )
        for builder in (
            build_simple_13_8kV,
            build_industrial_480V,
            build_dual_bus_substation,
        ):
            proj = builder()
            for c in proj.components:
                assert c.x % 10 == 0, (
                    f"{builder.__name__} {c.type} x={c.x} not aligned"
                )
                assert c.y % 10 == 0, (
                    f"{builder.__name__} {c.type} y={c.y} not aligned"
                )
            for w in proj.wires:
                assert w.x1 % 10 == 0
                assert w.y1 % 10 == 0
                assert w.x2 % 10 == 0
                assert w.y2 % 10 == 0


# ---------------------------------------------------------------------------
# Bus props alinhadas com .ocomp (v0.85 BusInfoDialog convention)
# ---------------------------------------------------------------------------


class TestBusProperties:

    def test_simple_template_bus_has_correct_props(self):
        from app.preprocessor.templates import build_simple_13_8kV
        proj = build_simple_13_8kV()
        bus = next(c for c in proj.components if c.type == "BUS")
        # bus_id (prop 0)
        assert bus.get(0) == "BUS-MAIN-13.8"
        # rated_voltage_kV (prop 1)
        assert float(bus.get(1)) == 13.8
        # n_phases (prop 2)
        assert bus.get(2) == "3"
        # panel_type (prop 3)
        assert bus.get(3) == "swgr_15kv"
        # is_lineside (prop 4)
        assert bus.get(4) == "1"

    def test_industrial_lv_bus_is_loadside(self):
        from app.preprocessor.templates import build_industrial_480V
        proj = build_industrial_480V()
        lv_bus = next(
            c for c in proj.components
            if c.type == "BUS" and float(c.get(1)) < 1.0
        )
        assert lv_bus.get(4) == "0"   # is_lineside = 0 (loadside)
        assert lv_bus.get(3) == "lv_swgr"


# ---------------------------------------------------------------------------
# Registry API
# ---------------------------------------------------------------------------


class TestRegistry:

    def test_get_template_builder_returns_callable(self):
        from app.preprocessor.templates import get_template_builder
        assert callable(get_template_builder("simple_13_8kV"))
        assert callable(get_template_builder("industrial_480V"))
        assert callable(get_template_builder("dual_bus_substation"))

    def test_get_template_builder_unknown_returns_none(self):
        from app.preprocessor.templates import get_template_builder
        assert get_template_builder("__not_a_template__") is None

    def test_build_template_unknown_raises(self):
        from app.preprocessor.templates import build_template
        with pytest.raises(KeyError):
            build_template("__not_a_template__")

    def test_TEMPLATES_has_3_entries(self):
        from app.preprocessor.templates import TEMPLATES
        assert len(TEMPLATES) == 3
        # Cada entry: (id, label, desc, builder)
        for entry in TEMPLATES:
            assert len(entry) == 4
            tid, label, desc, builder = entry
            assert isinstance(tid, str) and tid
            assert isinstance(label, str) and label
            assert isinstance(desc, str) and desc
            assert callable(builder)


# ---------------------------------------------------------------------------
# Round-trip serialization
# ---------------------------------------------------------------------------


class TestRoundtrip:

    def test_simple_template_round_trip_via_sch_text(self, tmp_path):
        """
        Build → serialize → parse → result equivalente.

        Garante que os templates produzem .sch válido (estrutura
        compatível com Qucs format).
        """
        from app.preprocessor.templates import build_simple_13_8kV
        from app.preprocessor.qucs_sch_parser import parse_sch_file
        from app.preprocessor.qucs_sch_serializer import serialize_sch_file

        proj = build_simple_13_8kV()
        path = tmp_path / "tpl.sch"
        serialize_sch_file(proj, str(path))
        assert path.is_file()

        re_parsed = parse_sch_file(str(path))
        assert len(re_parsed.components) == len(proj.components)
        assert len(re_parsed.wires) == len(proj.wires)
        # Tipos preservados
        types_orig = sorted(c.type for c in proj.components)
        types_re = sorted(c.type for c in re_parsed.components)
        assert types_orig == types_re

    def test_industrial_template_round_trip(self, tmp_path):
        from app.preprocessor.templates import build_industrial_480V
        from app.preprocessor.qucs_sch_parser import parse_sch_file
        from app.preprocessor.qucs_sch_serializer import serialize_sch_file

        proj = build_industrial_480V()
        path = tmp_path / "tpl.sch"
        serialize_sch_file(proj, str(path))
        re_parsed = parse_sch_file(str(path))
        # v0.91.3: 6 componentes (Vac + 2 BUS + R + L + GND)
        assert len(re_parsed.components) == 6

    def test_dual_bus_template_preserves_tie_label(self, tmp_path):
        from app.preprocessor.templates import build_dual_bus_substation
        from app.preprocessor.qucs_sch_parser import parse_sch_file
        from app.preprocessor.qucs_sch_serializer import serialize_sch_file

        proj = build_dual_bus_substation()
        path = tmp_path / "tpl.sch"
        serialize_sch_file(proj, str(path))
        re_parsed = parse_sch_file(str(path))
        labels = [w.label for w in re_parsed.wires]
        assert "TIE" in labels


# ---------------------------------------------------------------------------
# Welcome dialog: _TemplateCard + template_requested
# ---------------------------------------------------------------------------


class TestWelcomeDialogTemplates:

    def test_dialog_has_template_section(self, qapp):
        from app.gui.welcome_dialog import WelcomeDialog
        dlg = WelcomeDialog()
        # template_requested signal exposto
        assert hasattr(dlg, "template_requested")

    def test_template_card_emits_id(self, qapp):
        from app.gui.welcome_dialog import _TemplateCard
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QEvent
        card = _TemplateCard(
            template_id="my-tpl",
            title="MyTemplate",
            description="Test",
        )
        captured: list[str] = []
        card.clicked.connect(captured.append)
        # Simula click esquerdo
        ev = QMouseEvent(
            QEvent.MouseButtonPress,
            QPointF(0, 0), Qt.LeftButton, Qt.LeftButton,
            Qt.NoModifier,
        )
        card.mousePressEvent(ev)
        assert captured == ["my-tpl"]

    def test_template_card_template_id_property(self, qapp):
        from app.gui.welcome_dialog import _TemplateCard
        card = _TemplateCard("xyz", "Title", "Desc")
        assert card.template_id == "xyz"

    def test_dialog_template_section_has_3_cards(self, qapp):
        """Welcome dialog mostra 3 _TemplateCard (1 por template
        no registry)."""
        from app.gui.welcome_dialog import WelcomeDialog, _TemplateCard
        dlg = WelcomeDialog()
        cards = dlg.findChildren(_TemplateCard)
        assert len(cards) == 3


# ---------------------------------------------------------------------------
# MainWindow handler
# ---------------------------------------------------------------------------


class TestMainWindowHandler:

    def test_handler_loads_simple_template(self, qapp):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            mw._on_pp_new_from_template("simple_13_8kV")
            scene = mw.schematic_pp.scene
            # v0.91.12: 4 componentes (Vac + BUS + R_LOAD + GND)
            assert len(scene.component_items()) == 4
        finally:
            mw.close()

    def test_handler_loads_industrial_template(self, qapp):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            mw._on_pp_new_from_template("industrial_480V")
            scene = mw.schematic_pp.scene
            # v0.91.3: 6 componentes (Vac + 2 BUS + R + L + GND)
            assert len(scene.component_items()) == 6
        finally:
            mw.close()

    def test_handler_unknown_template_warns_no_crash(
        self, qapp, monkeypatch,
    ):
        """Template inexistente → QMessageBox.warning, não crash."""
        from app.gui.main_window import MainWindow
        from PySide6.QtWidgets import QMessageBox
        mw = MainWindow()
        try:
            captured = []
            monkeypatch.setattr(
                QMessageBox, "warning",
                lambda *a, **kw: captured.append(a),
            )
            mw._on_pp_new_from_template("__nonsense__")
            assert len(captured) == 1
        finally:
            mw.close()

    def test_handler_switches_to_pp_tab(self, qapp):
        """Após carregar template, foca a aba do PpEditor."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            mw._on_pp_new_from_template("simple_13_8kV")
            assert mw.tabs.currentWidget() is mw.schematic_pp
        finally:
            mw.close()
