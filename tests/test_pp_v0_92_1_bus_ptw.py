"""
tests/test_pp_v0_92_1_bus_ptw.py — v0.92.1:

Bus PTW — barramento como linha grossa contínua, multi-conexão
em qualquer ponto, redimensionável por drag (estilo PTW
Power*Tools).

Cobertura:

* ``BusSymbol`` é stateful (length por instância).
* ``set_length()`` aplica clamp [60, 4000] e snap a 10 px.
* ``pin_positions()`` retorna pinos sintéticos a cada 10 px
  ao longo da barra (multi-conexão).
* ``endpoint_positions()`` retorna left/right endpoints
  sincronizados com length.
* ``update_from_component()`` lê propriedade ``"length"`` do
  PpComponent e aplica.
* ``ComponentItem`` instala 2 ``BusResizeHandle`` (left/right)
  para componentes BUS; ocultos por padrão, visíveis quando
  selecionado.
* Catálogo BUS.ocomp contém propriedade ``length``.
* Pinos antigos hardcoded (T1_A..T4_C com 12 pinos) foram
  substituídos por pinos sintéticos.
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# BusSymbol unitário
# ---------------------------------------------------------------------------


class TestBusSymbol:

    def test_default_length(self, qapp):
        from app.preprocessor.symbols import BusSymbol
        bs = BusSymbol()
        assert bs.length == BusSymbol.DEFAULT_LENGTH == 200

    def test_set_length_within_range(self, qapp):
        from app.preprocessor.symbols import BusSymbol
        bs = BusSymbol()
        bs.set_length(400)
        assert bs.length == 400
        bs.set_length(80)
        assert bs.length == 80

    def test_set_length_clamps_min(self, qapp):
        from app.preprocessor.symbols import BusSymbol
        bs = BusSymbol()
        bs.set_length(50)   # abaixo do MIN
        assert bs.length == BusSymbol.MIN_LENGTH

    def test_set_length_clamps_max(self, qapp):
        from app.preprocessor.symbols import BusSymbol
        bs = BusSymbol()
        bs.set_length(99999)
        assert bs.length == BusSymbol.MAX_LENGTH

    def test_set_length_snaps_to_grid(self, qapp):
        from app.preprocessor.symbols import BusSymbol
        bs = BusSymbol()
        bs.set_length(237)   # não múltiplo de 10
        assert bs.length % 10 == 0
        # 237 // 10 * 10 = 230
        assert bs.length == 230

    def test_set_length_handles_garbage(self, qapp):
        from app.preprocessor.symbols import BusSymbol
        bs = BusSymbol()
        bs.set_length("abc")
        # Default fallback (também clamped a MIN se < MIN)
        assert bs.length == BusSymbol.DEFAULT_LENGTH or bs.length >= 60

    def test_pin_positions_synthetic_every_grid_step(self, qapp):
        """v0.92.1: pin_positions retorna ponto a cada 10 px."""
        from app.preprocessor.symbols import BusSymbol
        bs = BusSymbol()
        bs.set_length(200)
        pins = bs.pin_positions()
        # length=200, half=100, pinos de -100 a +100 step 10 = 21
        assert len(pins) == 21
        # Todos com y=0
        assert all(p[1] == 0 for p in pins)
        # X cobre o range completo
        xs = [p[0] for p in pins]
        assert min(xs) == -100 and max(xs) == 100
        # Spacing = 10
        diffs = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
        assert all(d == 10 for d in diffs)

    def test_pin_positions_scales_with_length(self, qapp):
        """v0.92.1: aumentar length aumenta o número de pinos."""
        from app.preprocessor.symbols import BusSymbol
        bs = BusSymbol()
        bs.set_length(400)
        pins = bs.pin_positions()
        # length=400, half=200, pinos de -200 a +200 step 10 = 41
        assert len(pins) == 41

    def test_endpoint_positions(self, qapp):
        from app.preprocessor.symbols import BusSymbol
        bs = BusSymbol()
        bs.set_length(300)
        left, right = bs.endpoint_positions()
        assert left == (-150, 0)
        assert right == (150, 0)

    def test_bounding_rect_scales(self, qapp):
        from app.preprocessor.symbols import BusSymbol
        bs = BusSymbol()
        bs.set_length(200)
        r1 = bs.bounding_rect()
        bs.set_length(600)
        r2 = bs.bounding_rect()
        # Bounding rect cresce com length
        assert r2.width() > r1.width()


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------


class TestBusCatalog:

    def test_bus_spec_has_length_property(self, qapp):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("BUS")
        assert spec is not None
        prop_names = [p.name for p in spec.properties]
        assert "length" in prop_names, (
            f"BUS catalog não tem 'length' property: {prop_names}"
        )

    def test_bus_spec_no_more_12_pin_taps(self, qapp):
        """v0.92.1: pinos T1_A..T4_C foram substituídos por
        pinos sintéticos. O spec mantém apenas referências
        compactas (T_CENTER, T_LEFT, T_RIGHT)."""
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("BUS")
        pin_names = [p.name for p in spec.pins]
        # Pinos antigos (T1_A, T2_B, etc.) foram retirados
        old_pins = [
            n for n in pin_names if n.startswith("T") and "_" in n
            and n.split("_")[0] in ("T1", "T2", "T3", "T4")
        ]
        assert not old_pins, (
            f"Pinos antigos ainda no catálogo: {old_pins}"
        )

    def test_bus_length_default_is_200(self, qapp):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("BUS")
        for p in spec.properties:
            if p.name == "length":
                assert p.default in ("200", 200, "200.0")
                return
        pytest.fail("length property ausente")


# ---------------------------------------------------------------------------
# ComponentItem + BusResizeHandle integration
# ---------------------------------------------------------------------------


class TestBusItemIntegration:

    def _make_bus_component(self):
        from app.preprocessor.spec import get_default_registry
        from app.preprocessor.models import PpComponent, PpProperty
        spec = get_default_registry().get("BUS")
        props = [
            PpProperty(p.default, p.visible) for p in spec.properties
        ]
        return PpComponent(
            type="BUS", name="BUS-1", visible=True,
            x=200, y=200, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=props,
        )

    def test_bus_item_installs_2_handles(self, qapp):
        """v0.92.1: ComponentItem instala left+right handles para BUS."""
        from app.gui.schematic_pp.items import (
            ComponentItem, BusResizeHandle,
        )
        comp = self._make_bus_component()
        item = ComponentItem(comp)
        handles = [
            c for c in item.childItems()
            if isinstance(c, BusResizeHandle)
        ]
        assert len(handles) == 2
        sides = sorted(h.side for h in handles)
        assert sides == ["left", "right"]

    def test_bus_handles_initially_hidden(self, qapp):
        """v0.92.1: handles começam ocultos (só aparecem quando
        item está selecionado)."""
        from app.gui.schematic_pp.items import (
            ComponentItem, BusResizeHandle,
        )
        comp = self._make_bus_component()
        item = ComponentItem(comp)
        handles = [
            c for c in item.childItems()
            if isinstance(c, BusResizeHandle)
        ]
        assert all(not h.isVisible() for h in handles)

    def test_bus_handles_visible_when_selected(self, qapp):
        """v0.92.1: selecionar o bus mostra os handles."""
        from PySide6.QtWidgets import QGraphicsScene
        from app.gui.schematic_pp.items import (
            ComponentItem, BusResizeHandle,
        )
        scene = QGraphicsScene()
        comp = self._make_bus_component()
        item = ComponentItem(comp)
        scene.addItem(item)
        item.setSelected(True)
        handles = [
            c for c in item.childItems()
            if isinstance(c, BusResizeHandle)
        ]
        assert all(h.isVisible() for h in handles)

    def test_non_bus_components_have_no_handles(self, qapp):
        """v0.92.1: somente BUS recebe handles (R, L, C, etc. não)."""
        from app.preprocessor.models import PpComponent, PpProperty
        from app.gui.schematic_pp.items import (
            ComponentItem, BusResizeHandle,
        )
        comp = PpComponent(
            type="R", name="R1", visible=True,
            x=100, y=100, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100", True)],
        )
        item = ComponentItem(comp)
        handles = [
            c for c in item.childItems()
            if isinstance(c, BusResizeHandle)
        ]
        assert len(handles) == 0

    def test_renderer_length_synced_from_property(self, qapp):
        """v0.92.1: ComponentItem.sync_from_model lê 'length' do
        PpComponent.properties e aplica ao renderer."""
        from app.gui.schematic_pp.items import ComponentItem
        from app.preprocessor.spec import get_default_registry

        comp = self._make_bus_component()
        # Encontra índice de length
        spec = get_default_registry().get("BUS")
        length_idx = next(
            i for i, p in enumerate(spec.properties)
            if p.name == "length"
        )
        comp.properties[length_idx].value = "350"

        item = ComponentItem(comp)
        # sync_from_model é chamado em __init__
        # 350 não é múltiplo de 10 — deve snap para 350 (já é)
        assert item.renderer.length == 350

    def test_handle_drag_updates_length(self, qapp):
        """v0.92.2: simular drag do handle direito atualiza length
        e persiste em PpComponent.properties.

        Como v0.92.2 mudou a semântica para resize ASSIMÉTRICO
        (preserva endpoint oposto), o length resultante é metade
        do que era em v0.92.1: ``new_length = mouse_x − anchor_x``
        em vez de ``2 × |x_parent|``.
        """
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtWidgets import QGraphicsScene
        from app.gui.schematic_pp.items import (
            ComponentItem, BusResizeHandle,
        )
        from app.preprocessor.spec import get_default_registry

        scene = QGraphicsScene()
        comp = self._make_bus_component()
        item = ComponentItem(comp)
        scene.addItem(item)
        item.setSelected(True)

        right_handle = next(
            c for c in item.childItems()
            if isinstance(c, BusResizeHandle) and c.side == "right"
        )

        # Componente em (200, 200), length=200 → endpoint esquerdo
        # scene = (100, 200). Drag right para scene_x=550 →
        # new_length = 550 − 100 = 450. new_center = 100 + 225 = 325.
        assert item.renderer.length == 200

        class _StubEvent:
            def __init__(self, sp):
                self._sp = sp
            def scenePos(self):
                return self._sp
            def buttons(self):
                return Qt.LeftButton
            def accept(self):
                pass

        new_scene_pos = QPointF(550, 200)
        right_handle.mouseMoveEvent(_StubEvent(new_scene_pos))

        # v0.92.2: length assimétrico = mouse - anchor
        assert item.renderer.length == 450
        assert comp.x == 325
        # PpComponent.properties também
        spec = get_default_registry().get("BUS")
        length_idx = next(
            i for i, p in enumerate(spec.properties)
            if p.name == "length"
        )
        assert comp.properties[length_idx].value == "450"


# ---------------------------------------------------------------------------
# Painter (smoke — não há assert pixel-perfect, só verifica não-crash)
# ---------------------------------------------------------------------------


class TestPaintSmoke:

    def test_paint_does_not_crash(self, qapp):
        """v0.92.1: BusSymbol.paint() roda sem erro em diferentes
        comprimentos."""
        from PySide6.QtGui import QImage, QPainter
        from app.preprocessor.symbols import BusSymbol
        bs = BusSymbol()
        for length in [60, 100, 200, 500, 1000, 4000]:
            bs.set_length(length)
            img = QImage(2 * length + 100, 100, QImage.Format_ARGB32)
            painter = QPainter(img)
            painter.translate(img.width() / 2, img.height() / 2)
            bs.paint(painter)
            painter.end()
            # Imagem não vazia
            assert not img.isNull()


# ---------------------------------------------------------------------------
# v0.92.2: resize assimétrico, undo, wire-clamping
# ---------------------------------------------------------------------------


class _StubMouseEvent:
    """Stub mínimo de QMouseEvent para alimentar handle.mouse{Press,Move,Release}Event."""

    def __init__(self, scene_x, scene_y):
        from PySide6.QtCore import QPointF, Qt
        self._sp = QPointF(scene_x, scene_y)
        self._lb = Qt.LeftButton

    def scenePos(self):
        return self._sp

    def buttons(self):
        return self._lb

    def button(self):
        return self._lb

    def accept(self):
        pass


def _make_bus(x=200, y=200):
    from app.preprocessor.spec import get_default_registry
    from app.preprocessor.models import PpComponent, PpProperty
    spec = get_default_registry().get("BUS")
    props = [PpProperty(p.default, p.visible) for p in spec.properties]
    return PpComponent(
        type="BUS", name="BUS-1", visible=True,
        x=x, y=y, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=props,
    )


def _right_handle(item):
    from app.gui.schematic_pp.items import BusResizeHandle
    return next(
        c for c in item.childItems()
        if isinstance(c, BusResizeHandle) and c.side == "right"
    )


def _left_handle(item):
    from app.gui.schematic_pp.items import BusResizeHandle
    return next(
        c for c in item.childItems()
        if isinstance(c, BusResizeHandle) and c.side == "left"
    )


def _patch_scene_lookups(scene, items, wires=()):
    """QGraphicsScene padrão não tem find_component_item / find_wire_item;
    PpScene sim. Patches para ResizeBusCommand operar."""
    scene.find_component_item = lambda c: next(
        (it for it in items if it.component is c), None,
    )
    scene.find_wire_item = lambda w: next(
        (wi for wi in wires if wi.wire is w), None,
    )


class TestBusResizeAsymmetric:
    """v0.92.2: handles left/right preservam o endpoint oposto."""

    def test_drag_right_handle_preserves_left_endpoint(self, qapp):
        from PySide6.QtCore import QPointF
        from PySide6.QtWidgets import QGraphicsScene
        from app.gui.schematic_pp.items import ComponentItem
        scene = QGraphicsScene()
        comp = _make_bus(x=200, y=200)
        item = ComponentItem(comp)
        scene.addItem(item)
        item.setSelected(True)

        rh = _right_handle(item)
        # length=200, half=100, endpoint esq scene = 100. Drag para
        # scene_x=550 → new_length = 550 - 100 = 450, x = 100 + 225 = 325.
        rh.mousePressEvent(_StubMouseEvent(300, 200))
        rh.mouseMoveEvent(_StubMouseEvent(550, 200))

        assert item.renderer.length == 450
        assert comp.x == 325
        # Endpoint esquerdo permanece em scene_x=100
        (lx, _ly), _r = item.renderer.endpoint_positions()
        left_scene = item.mapToScene(QPointF(lx, 0))
        assert int(round(left_scene.x())) == 100

    def test_drag_left_handle_preserves_right_endpoint(self, qapp):
        from PySide6.QtCore import QPointF
        from PySide6.QtWidgets import QGraphicsScene
        from app.gui.schematic_pp.items import ComponentItem
        scene = QGraphicsScene()
        comp = _make_bus(x=200, y=200)
        item = ComponentItem(comp)
        scene.addItem(item)
        item.setSelected(True)

        lh = _left_handle(item)
        # endpoint dir scene = 300. Drag left para scene_x=50 →
        # new_length = 300 - 50 = 250, x = 300 - 125 = 175.
        lh.mousePressEvent(_StubMouseEvent(100, 200))
        lh.mouseMoveEvent(_StubMouseEvent(50, 200))

        assert item.renderer.length == 250
        assert comp.x == 175
        # Endpoint direito permanece em scene_x=300
        _l, (rx, _ry) = item.renderer.endpoint_positions()
        right_scene = item.mapToScene(QPointF(rx, 0))
        assert int(round(right_scene.x())) == 300

    def test_shrink_via_right_handle_preserves_left(self, qapp):
        """v0.92.2: encolher pelo handle direito também preserva
        o endpoint esquerdo."""
        from PySide6.QtCore import QPointF
        from PySide6.QtWidgets import QGraphicsScene
        from app.gui.schematic_pp.items import ComponentItem
        scene = QGraphicsScene()
        comp = _make_bus(x=200, y=200)
        item = ComponentItem(comp)
        scene.addItem(item)
        item.setSelected(True)

        rh = _right_handle(item)
        # encolhe: drag right de 300 → 250.
        # new_length = 250 - 100 = 150, x = 100 + 75 = 175.
        rh.mousePressEvent(_StubMouseEvent(300, 200))
        rh.mouseMoveEvent(_StubMouseEvent(250, 200))

        assert item.renderer.length == 150
        assert comp.x == 175
        (lx, _), _ = item.renderer.endpoint_positions()
        left_scene = item.mapToScene(QPointF(lx, 0))
        assert int(round(left_scene.x())) == 100

    def test_resize_clamped_to_min_length(self, qapp):
        """v0.92.2: drag muito agressivo é clamped a MIN_LENGTH=60."""
        from PySide6.QtWidgets import QGraphicsScene
        from app.gui.schematic_pp.items import ComponentItem
        scene = QGraphicsScene()
        comp = _make_bus(x=200, y=200)
        item = ComponentItem(comp)
        scene.addItem(item)
        item.setSelected(True)

        rh = _right_handle(item)
        # Tentar encolher abaixo do MIN: drag right para scene_x=110
        # (anchor=100, raw_length=10) — clamp para 60.
        rh.mousePressEvent(_StubMouseEvent(300, 200))
        rh.mouseMoveEvent(_StubMouseEvent(110, 200))

        assert item.renderer.length == 60


class TestBusResizeUndo:
    """v0.92.2: ResizeBusCommand empilha no QUndoStack e suporta undo/redo."""

    def test_release_pushes_resize_bus_command(self, qapp):
        from PySide6.QtGui import QUndoStack
        from PySide6.QtWidgets import QGraphicsScene
        from app.gui.schematic_pp.items import ComponentItem
        scene = QGraphicsScene()
        scene.undo_stack = QUndoStack()
        comp = _make_bus(x=200, y=200)
        item = ComponentItem(comp)
        scene.addItem(item)
        _patch_scene_lookups(scene, [item])
        item.setSelected(True)

        rh = _right_handle(item)
        rh.mousePressEvent(_StubMouseEvent(300, 200))
        rh.mouseMoveEvent(_StubMouseEvent(550, 200))
        assert scene.undo_stack.count() == 0
        rh.mouseReleaseEvent(_StubMouseEvent(550, 200))
        assert scene.undo_stack.count() == 1
        # Command é do tipo correto
        # (QUndoStack não expõe acesso direto ao comando topo, mas
        # o text() é único.)
        assert "Redimensionar" in scene.undo_stack.command(0).text()

    def test_undo_restores_length_and_x(self, qapp):
        from PySide6.QtGui import QUndoStack
        from PySide6.QtWidgets import QGraphicsScene
        from app.gui.schematic_pp.items import ComponentItem
        scene = QGraphicsScene()
        scene.undo_stack = QUndoStack()
        comp = _make_bus(x=200, y=200)
        item = ComponentItem(comp)
        scene.addItem(item)
        _patch_scene_lookups(scene, [item])
        item.setSelected(True)

        rh = _right_handle(item)
        rh.mousePressEvent(_StubMouseEvent(300, 200))
        rh.mouseMoveEvent(_StubMouseEvent(550, 200))
        rh.mouseReleaseEvent(_StubMouseEvent(550, 200))

        # Estado novo
        assert item.renderer.length == 450
        assert comp.x == 325

        # Undo: rebobina para pré-drag
        scene.undo_stack.undo()
        assert item.renderer.length == 200
        assert comp.x == 200

        # Redo: re-aplica novo
        scene.undo_stack.redo()
        assert item.renderer.length == 450
        assert comp.x == 325

    def test_no_change_no_command_pushed(self, qapp):
        """Press + release sem drag não empilha command."""
        from PySide6.QtGui import QUndoStack
        from PySide6.QtWidgets import QGraphicsScene
        from app.gui.schematic_pp.items import ComponentItem
        scene = QGraphicsScene()
        scene.undo_stack = QUndoStack()
        comp = _make_bus(x=200, y=200)
        item = ComponentItem(comp)
        scene.addItem(item)
        _patch_scene_lookups(scene, [item])
        item.setSelected(True)

        rh = _right_handle(item)
        rh.mousePressEvent(_StubMouseEvent(300, 200))
        # Sem move
        rh.mouseReleaseEvent(_StubMouseEvent(300, 200))
        assert scene.undo_stack.count() == 0


class TestBusResizeWireClamp:
    """v0.92.2: wires conectados são clampados ao novo range do bus."""

    def test_wire_endpoint_clamped_when_shrinking(self, qapp):
        from PySide6.QtWidgets import QGraphicsScene
        from app.preprocessor.models import PpWire
        from app.gui.schematic_pp.items import ComponentItem, WireItem
        scene = QGraphicsScene()
        # PpScene mantém a lista de wires; QGraphicsScene padrão não
        # tem o atributo. Adicionamos manualmente para o
        # _capture_attached_anchors do componente enxergar.
        scene._wires = []
        comp = _make_bus(x=200, y=200)
        item = ComponentItem(comp)
        scene.addItem(item)

        # Wire conectado em scene (290, 200) — pino do bus em x=290
        # (pinos sintéticos a cada 10 px de 100 a 300).
        wire = PpWire(
            x1=290, y1=200, x2=290, y2=400,
            label="", label_x=0, label_y=0,
        )
        wire_item = WireItem(wire)
        scene.addItem(wire_item)
        scene._wires.append(wire_item)

        item.setSelected(True)
        rh = _right_handle(item)
        # encolhe: drag right de 300 → 250.
        # range scene novo: [100, 250]. wire em x=290 → clamp 250.
        rh.mousePressEvent(_StubMouseEvent(300, 200))
        rh.mouseMoveEvent(_StubMouseEvent(250, 200))

        assert wire.x1 == 250
        assert wire.y1 == 200

    def test_wire_endpoint_unchanged_if_inside_new_range(self, qapp):
        """Wire dentro do novo range NÃO é movido (a barra ainda
        passa por ele)."""
        from PySide6.QtWidgets import QGraphicsScene
        from app.preprocessor.models import PpWire
        from app.gui.schematic_pp.items import ComponentItem, WireItem
        scene = QGraphicsScene()
        scene._wires = []
        comp = _make_bus(x=200, y=200)
        item = ComponentItem(comp)
        scene.addItem(item)

        # Wire conectado em scene (150, 200) — bem no meio do bus
        wire = PpWire(
            x1=150, y1=200, x2=150, y2=400,
            label="", label_x=0, label_y=0,
        )
        wire_item = WireItem(wire)
        scene.addItem(wire_item)
        scene._wires.append(wire_item)

        item.setSelected(True)
        rh = _right_handle(item)
        # Estende: drag right de 300 → 500. range novo [100, 500].
        # Wire x=150 já está dentro — não deve mover.
        rh.mousePressEvent(_StubMouseEvent(300, 200))
        rh.mouseMoveEvent(_StubMouseEvent(500, 200))

        assert wire.x1 == 150
        assert wire.y1 == 200

    def test_undo_restores_wire_endpoint(self, qapp):
        from PySide6.QtGui import QUndoStack
        from PySide6.QtWidgets import QGraphicsScene
        from app.preprocessor.models import PpWire
        from app.gui.schematic_pp.items import ComponentItem, WireItem
        scene = QGraphicsScene()
        scene.undo_stack = QUndoStack()
        scene._wires = []
        comp = _make_bus(x=200, y=200)
        item = ComponentItem(comp)
        scene.addItem(item)

        wire = PpWire(
            x1=290, y1=200, x2=290, y2=400,
            label="", label_x=0, label_y=0,
        )
        wire_item = WireItem(wire)
        scene.addItem(wire_item)
        scene._wires.append(wire_item)

        _patch_scene_lookups(scene, [item], wires=[wire_item])

        item.setSelected(True)
        rh = _right_handle(item)
        rh.mousePressEvent(_StubMouseEvent(300, 200))
        rh.mouseMoveEvent(_StubMouseEvent(250, 200))
        rh.mouseReleaseEvent(_StubMouseEvent(250, 200))

        # Wire foi clampado a 250
        assert wire.x1 == 250

        # Undo restaura wire ao estado pré-drag (290)
        scene.undo_stack.undo()
        assert wire.x1 == 290


# ---------------------------------------------------------------------------
# Analyzer integration (node_coalescer enxerga pinos sintéticos)
# ---------------------------------------------------------------------------


class TestAnalyzerIntegration:

    def test_node_coalescer_returns_synthetic_pins(self, qapp):
        """v0.92.1: node_coalescer.pin_positions() para BUS retorna
        a mesma lista que BusSymbol.pin_positions() — analyzer
        e renderer compartilham a mesma topologia."""
        from app.preprocessor.spec import get_default_registry
        from app.preprocessor.models import PpComponent, PpProperty
        from app.preprocessor.node_coalescer import pin_positions

        spec = get_default_registry().get("BUS")
        props = [PpProperty(p.default, p.visible) for p in spec.properties]
        comp = PpComponent(
            type="BUS", name="BUS-1", visible=True,
            x=200, y=200, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=props,
        )
        pins = pin_positions(comp)
        # length=200 default → half=100 → 21 pinos (-100, -90, ..., +100)
        # Em coords absolutas, x vai de 100 a 300
        assert len(pins) == 21
        xs = [p[0] for p in pins]
        assert min(xs) == 100   # 200 + (-100)
        assert max(xs) == 300   # 200 + (+100)
        # Todos com y=200 (anchor + dy=0)
        assert all(p[1] == 200 for p in pins)

    def test_pipeline_finds_source_via_bus(self, qapp):
        """v0.92.1: end-to-end — Vac conectado ao BUS via wire em
        qualquer ponto da barra deve ser detectado pela
        find_neighbors_of_bus()."""
        from app.postprocessor.bus_pipeline import (
            find_neighbors_of_bus,
        )
        from app.preprocessor.templates import build_simple_13_8kV
        proj = build_simple_13_8kV()
        neighbors = find_neighbors_of_bus(proj, "BUS-MAIN-13.8")
        # Deve achar UTIL-1 (Vac) E R_LOAD (R) — 2 neighbors
        names = [n.component.name for n in neighbors]
        assert "UTIL-1" in names, (
            f"Vac (UTIL-1) deve ser detectado como vizinho do "
            f"BUS, got: {names}"
        )

    def test_synthetic_pins_respect_length(self, qapp):
        """v0.92.1: bus com length=400 expõe 41 pinos sintéticos
        ao node_coalescer."""
        from app.preprocessor.spec import get_default_registry
        from app.preprocessor.models import PpComponent, PpProperty
        from app.preprocessor.node_coalescer import pin_positions

        spec = get_default_registry().get("BUS")
        props = [PpProperty(p.default, p.visible) for p in spec.properties]
        # Encontra idx de length e seta para 400
        length_idx = next(
            i for i, p in enumerate(spec.properties)
            if p.name == "length"
        )
        props[length_idx].value = "400"
        comp = PpComponent(
            type="BUS", name="BUS-LARGE", visible=True,
            x=500, y=300, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=props,
        )
        pins = pin_positions(comp)
        # length=400, half=200, 41 pinos a cada 10 px
        assert len(pins) == 41
