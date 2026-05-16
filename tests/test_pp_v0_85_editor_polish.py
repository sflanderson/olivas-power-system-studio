"""
tests/test_pp_v0_85_editor_polish.py — v0.85: polimento do
editor visual (UX).

Cobertura
---------

* **Connection dots** (PpScene._paint_connection_dots): pontos
  pretos onde wire endpoint coincide com pino de componente.
* **Junction dots**: pontos onde 3+ endpoints de wires coincidem
  (sem componente).
* **Snap-to-pin no ghost wire** (PpView._snapped_scene_pos):
  cursor próximo a pino → ghost endpoint snapa exatamente no
  pino.
* **Cursor change sobre pino** (PpView.mouseMoveEvent +
  TOOL_WIRE): hover sobre pino → PointingHandCursor; fora,
  CrossCursor.
* **BUS auto-naming dialog** (BusInfoDialog + editor.
  _prompt_bus_info): adicionar BUS abre dialog rico; aceitar
  cria BUS com props preenchidas; cancelar não cria.
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_resistor(name: str = "R1", x: int = 100, y: int = 100):
    from app.preprocessor.models import PpComponent, PpProperty
    return PpComponent(
        type="R", name=name, visible=True,
        x=x, y=y,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty("1k")],
    )


def _make_wire(x1: int, y1: int, x2: int, y2: int):
    from app.preprocessor.models import PpWire
    return PpWire(x1=x1, y1=y1, x2=x2, y2=y2, label="")


# ---------------------------------------------------------------------------
# Connection dots (scene foreground)
# ---------------------------------------------------------------------------


class TestConnectionDots:

    def test_no_dots_when_no_wires(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        scene = PpScene()
        scene.add_component(_make_resistor())
        # Não crasha; lista de dots é vazia (cobertura de branch).
        # A forma mais direta: invocar _paint_connection_dots com um
        # painter de pixmap dummy.
        pixmap = QPixmap(200, 200)
        painter = QPainter(pixmap)
        try:
            scene._paint_connection_dots(painter)
        finally:
            painter.end()

    def test_pin_endpoint_match_produces_dot(self, qapp, monkeypatch):
        """
        R1 em (100,100) tem pinos em (100,70) e (100,130).
        Wire em (100,70)→(50,70) deve gerar dot no pino top.
        Verificamos via inspeção da lista interna calculada
        durante ``_paint_connection_dots``.
        """
        from app.gui.schematic_pp.scene import PpScene
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_wire(_make_wire(100, 70, 50, 70))

        # Captura os dot points via spy no drawEllipse
        captured: list[tuple[float, float]] = []

        class SpyPainter:
            def __init__(self):
                pass

            def save(self): pass
            def restore(self): pass
            def setRenderHint(self, *a, **kw): pass
            def setBrush(self, *a, **kw): pass
            def setPen(self, *a, **kw): pass

            def drawEllipse(self, center, rx, ry):
                captured.append((center.x(), center.y()))

        sp = SpyPainter()
        scene._paint_connection_dots(sp)
        # Pelo menos um dot na pos do pino top conectado.
        assert (100.0, 70.0) in captured

    def test_no_dot_when_wire_far_from_pins(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_wire(_make_wire(300, 300, 400, 300))

        captured: list[tuple[float, float]] = []

        class SpyPainter:
            def save(self): pass
            def restore(self): pass
            def setRenderHint(self, *a, **kw): pass
            def setBrush(self, *a, **kw): pass
            def setPen(self, *a, **kw): pass
            def drawEllipse(self, center, rx, ry):
                captured.append((center.x(), center.y()))

        scene._paint_connection_dots(SpyPainter())
        assert captured == []


# ---------------------------------------------------------------------------
# Junction dots
# ---------------------------------------------------------------------------


class TestJunctionDots:

    def test_three_wires_endpoint_at_same_point_creates_junction(self, qapp):
        """
        3 wires terminando em (50,50) sem componente nesse ponto →
        junction dot deve ser pintado.
        """
        from app.gui.schematic_pp.scene import PpScene
        scene = PpScene()
        scene.add_wire(_make_wire(50, 50, 50, 100))
        scene.add_wire(_make_wire(50, 50, 100, 50))
        scene.add_wire(_make_wire(50, 50, 0, 50))

        captured: list[tuple[float, float]] = []

        class SpyPainter:
            def save(self): pass
            def restore(self): pass
            def setRenderHint(self, *a, **kw): pass
            def setBrush(self, *a, **kw): pass
            def setPen(self, *a, **kw): pass
            def drawEllipse(self, center, rx, ry):
                captured.append((center.x(), center.y()))

        scene._paint_connection_dots(SpyPainter())
        assert (50.0, 50.0) in captured

    def test_two_wires_endpoint_no_junction(self, qapp):
        """2 endpoints num ponto SEM componente — não é junção."""
        from app.gui.schematic_pp.scene import PpScene
        scene = PpScene()
        # 2 wires colineares que se tocam em (50,50)
        scene.add_wire(_make_wire(50, 50, 50, 100))
        scene.add_wire(_make_wire(50, 50, 100, 50))

        captured: list[tuple[float, float]] = []

        class SpyPainter:
            def save(self): pass
            def restore(self): pass
            def setRenderHint(self, *a, **kw): pass
            def setBrush(self, *a, **kw): pass
            def setPen(self, *a, **kw): pass
            def drawEllipse(self, center, rx, ry):
                captured.append((center.x(), center.y()))

        scene._paint_connection_dots(SpyPainter())
        assert captured == []


# ---------------------------------------------------------------------------
# Snap-to-pin no ghost wire
# ---------------------------------------------------------------------------


class TestSnapToPin:

    def test_view_closest_pin_within_distance(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        view = PpView(scene)
        view.resize(600, 600)

        # Cursor a 3 px do pino top (100,70) → snap pega o pino.
        result = view._closest_pin(QPointF(103, 70), max_dist=8.0)
        assert result is not None
        assert (result.x(), result.y()) == (100.0, 70.0)

    def test_view_closest_pin_too_far_returns_none(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        view = PpView(scene)
        view.resize(600, 600)

        # Cursor a 50 px de qualquer pino → None.
        result = view._closest_pin(QPointF(200, 200), max_dist=8.0)
        assert result is None

    def test_snapped_scene_pos_prefers_pin_over_grid(self, qapp):
        """
        Pino em (100,70). Cursor view-pos próximo do pino: o snap
        deve retornar EXATAMENTE (100,70), não algum múltiplo de
        grid próximo. Isso garante conexão correta mesmo quando o
        usuário não acerta o grid.
        """
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        view = PpView(scene)
        view.resize(600, 600)

        # Calcula a view-pos correspondente ao ponto cena (102,72).
        scene_pt = QPointF(102, 72)
        view_pt = view.mapFromScene(scene_pt)

        snapped = view._snapped_scene_pos(QPointF(view_pt))
        # Esperado: snap para o pino (100,70).
        assert (snapped.x(), snapped.y()) == (100.0, 70.0)

    def test_snapped_scene_pos_fallback_to_grid(self, qapp):
        """
        Cursor longe de qualquer pino → fallback para grid.
        """
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        view = PpView(scene)
        view.resize(600, 600)

        scene_pt = QPointF(303, 307)
        view_pt = view.mapFromScene(scene_pt)
        snapped = view._snapped_scene_pos(QPointF(view_pt))
        # Esperado: snap ao grid 10 → (300,310).
        assert snapped.x() % 10 == 0
        assert snapped.y() % 10 == 0


# ---------------------------------------------------------------------------
# BUS auto-naming dialog
# ---------------------------------------------------------------------------


class TestBusInfoDialog:

    def test_dialog_instantiates(self, qapp):
        from app.gui.bus_info_dialog import BusInfoDialog
        dlg = BusInfoDialog()
        assert isinstance(dlg, QDialog)
        assert "Adicionar Barramento" in dlg.windowTitle()

    def test_default_values(self, qapp):
        from app.gui.bus_info_dialog import BusInfoDialog
        dlg = BusInfoDialog(suggested_id="BUS-7", default_voltage_kV=4.16)
        assert dlg.bus_id() == "BUS-7"
        assert dlg.rated_voltage_kV() == 4.16
        assert dlg.n_phases() == 3
        assert dlg.is_lineside() is True

    def test_validation_blocks_empty_id(self, qapp):
        from app.gui.bus_info_dialog import BusInfoDialog
        from PySide6.QtWidgets import QDialogButtonBox
        dlg = BusInfoDialog(suggested_id="")
        ok_btn = dlg._buttons.button(QDialogButtonBox.Ok)
        assert not ok_btn.isEnabled()

    def test_validation_blocks_duplicate_id(self, qapp):
        from app.gui.bus_info_dialog import BusInfoDialog
        from PySide6.QtWidgets import QDialogButtonBox
        dlg = BusInfoDialog(
            suggested_id="BUS-1",
            existing_ids={"BUS-1"},
        )
        ok_btn = dlg._buttons.button(QDialogButtonBox.Ok)
        assert not ok_btn.isEnabled()

    def test_to_property_values_returns_9(self, qapp):
        """BUS.ocomp tem 9 propriedades; o dialog produz 9 valores."""
        from app.gui.bus_info_dialog import BusInfoDialog
        dlg = BusInfoDialog(suggested_id="MCC-1")
        values = dlg.to_property_values()
        assert len(values) == 9
        assert values[0] == "MCC-1"
        # n_phases no idx 2; default 3
        assert values[2] == "3"
        # has_AFD default 0
        assert values[5] == "0"

    def test_panel_type_auto_suggest_low_voltage(self, qapp):
        """Mudar V para 0.48 kV → panel_type vira lv_panel_typical."""
        from app.gui.bus_info_dialog import BusInfoDialog
        dlg = BusInfoDialog()
        dlg._kv_spin.setValue(0.48)
        dlg._auto_suggest_panel_type(0.48)
        assert dlg.panel_type() == "lv_panel_typical"

    def test_panel_type_auto_suggest_medium_voltage(self, qapp):
        """V=4.16 kV → swgr_5kv."""
        from app.gui.bus_info_dialog import BusInfoDialog
        dlg = BusInfoDialog()
        dlg._auto_suggest_panel_type(4.16)
        assert dlg.panel_type() == "swgr_5kv"

    def test_panel_type_auto_suggest_high_voltage(self, qapp):
        """V=13.8 kV → swgr_15kv."""
        from app.gui.bus_info_dialog import BusInfoDialog
        dlg = BusInfoDialog()
        dlg._auto_suggest_panel_type(13.8)
        assert dlg.panel_type() == "swgr_15kv"


# ---------------------------------------------------------------------------
# Editor — integração BUS dialog
# ---------------------------------------------------------------------------


class TestEditorBusFlow:

    def test_add_bus_calls_dialog(self, qapp, monkeypatch):
        """add_component_by_type('BUS') deve chamar
        _prompt_bus_info."""
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        called = []
        ed._prompt_bus_info = lambda: (called.append(True), None)[1]
        result = ed.add_component_by_type("BUS")
        assert called == [True]
        # Cancelado → None retornado, nenhum componente criado.
        assert result is None
        assert len(ed.scene.component_items()) == 0

    def test_add_bus_accepted_creates_component(self, qapp, monkeypatch):
        """Dialog aceito → BUS criado com props do dialog."""
        from app.gui.schematic_pp.editor import PpEditor
        from app.preprocessor.models import PpProperty

        ed = PpEditor()
        # Mock: sempre aceita, retorna props fixas.
        fake_props = [
            PpProperty("BUS-FAKE", True),
            PpProperty("4.16", True),
            PpProperty("3", False),
            PpProperty("swgr_5kv", True),
            PpProperty("1", True),
            PpProperty("0", True),
            PpProperty("10", False),
            PpProperty("4", False),
            PpProperty("", False),
        ]
        ed._prompt_bus_info = lambda: (fake_props, "BUS-FAKE")
        item = ed.add_component_by_type("BUS")
        assert item is not None
        assert item.component.name == "BUS-FAKE"
        assert item.component.properties[0].value == "BUS-FAKE"
        assert item.component.properties[1].value == "4.16"

    def test_add_non_bus_skips_dialog(self, qapp):
        """add_component_by_type('R') NÃO chama BUS dialog."""
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        called = []
        ed._prompt_bus_info = lambda: (called.append(True), None)[1]
        item = ed.add_component_by_type("R")
        assert item is not None
        assert called == []

    def test_suggest_bus_id_returns_unique(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        # Sem BUSes existentes → BUS-1
        assert ed._suggest_bus_id(set()) == "BUS-1"
        # Com BUS-1 e BUS-2 → BUS-3
        assert ed._suggest_bus_id({"BUS-1", "BUS-2"}) == "BUS-3"
