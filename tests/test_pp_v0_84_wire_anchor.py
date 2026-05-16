"""
tests/test_pp_v0_84_wire_anchor.py — v0.84:

UX: wires connected to component pins are *anchored* — they
follow the component on drag/rotate/mirror, and the only way
to disconnect is to delete the wire.

Cobertura
---------

* Drag: mover componente arrasta endpoints de fios fixados.
* Endpoints não-fixados (wire que não toca nenhum pino) não
  são afetados.
* Rotate/Mirror: pinos mudam de posição → endpoints seguem.
* Múltiplos fios fixados ao mesmo componente.
* Um fio com AMBOS endpoints fixados (a → componente, b →
  outro componente) — só o endpoint do componente movido
  segue.
* Undo/Redo do drag preserva endpoints (componente E fios
  voltam ao estado original).
* MoveComponentCommand não faz merge quando wire_anchors
  presente.
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import QPointF
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication

from app.gui.schematic_pp.commands import (
    MirrorComponentCommand,
    MoveComponentCommand,
    RotateComponentCommand,
)
from app.gui.schematic_pp.items import ComponentItem, WireItem
from app.gui.schematic_pp.scene import PpScene
from app.preprocessor.models import (
    PpComponent, PpProperty, PpProject, PpWire,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_resistor(name: str = "R1", x: int = 100, y: int = 100,
                   rotation: int = 0, mirror: int = 0) -> PpComponent:
    """Resistor com 2 pinos em (0,-30) e (0,30) coords locais."""
    return PpComponent(
        type="R", name=name, visible=True,
        x=x, y=y,
        label_dx=0, label_dy=0,
        mirror=mirror, rotation=rotation,
        properties=[PpProperty("1k")],
    )


def _make_wire(x1: int, y1: int, x2: int, y2: int) -> PpWire:
    return PpWire(x1=x1, y1=y1, x2=x2, y2=y2, label="")


# ---------------------------------------------------------------------------
# Anchor capture
# ---------------------------------------------------------------------------


class TestAnchorCapture:

    def test_no_wires_no_anchors(self, qapp):
        scene = PpScene()
        scene.add_component(_make_resistor())
        item = scene.component_items()[0]
        anchors = item._capture_attached_anchors()
        assert anchors == []

    def test_wire_at_top_pin_captured(self, qapp):
        """R1 em (100,100); pinos em (100,70) e (100,130).
        Wire de (100,70)→(50,70) deve ancorar no pino 0 (top)."""
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_wire(_make_wire(100, 70, 50, 70))
        item = scene.component_items()[0]
        anchors = item._capture_attached_anchors()
        assert len(anchors) == 1
        wire_item, endpoint, pin_idx = anchors[0]
        assert isinstance(wire_item, WireItem)
        assert endpoint == 1  # x1,y1 = (100,70) é o pino top.
        assert pin_idx == 0

    def test_wire_at_both_pins(self, qapp):
        """Wire de (100,70) → (100,130) toca AMBOS os pinos."""
        scene = PpScene()
        scene.add_component(_make_resistor())
        scene.add_wire(_make_wire(100, 70, 100, 130))
        item = scene.component_items()[0]
        anchors = item._capture_attached_anchors()
        # Mesmo wire aparece duas vezes (uma por endpoint).
        assert len(anchors) == 2
        endpoints = {a[1] for a in anchors}
        pins = {a[2] for a in anchors}
        assert endpoints == {1, 2}
        assert pins == {0, 1}

    def test_wire_far_from_pins_not_captured(self, qapp):
        scene = PpScene()
        scene.add_component(_make_resistor())
        scene.add_wire(_make_wire(200, 200, 300, 300))
        item = scene.component_items()[0]
        anchors = item._capture_attached_anchors()
        assert anchors == []


# ---------------------------------------------------------------------------
# Drag follow (sync via itemChange)
# ---------------------------------------------------------------------------


class TestDragFollow:

    def test_dragging_component_translates_attached_wire(self, qapp):
        """
        Move componente de (100,100) para (200,100).
        Wire ancorado no pino top deve mover (100,70) → (200,70).
        """
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_wire(_make_wire(100, 70, 50, 70))
        item = scene.component_items()[0]
        wire_item = scene.wire_items()[0]

        # Simula mousePress (captura anchors)
        item._anchor_snapshot = item._capture_attached_anchors()
        item._anchor_before_endpoints = [
            (
                wi, idx,
                wi.wire.x1 if idx == 1 else wi.wire.x2,
                wi.wire.y1 if idx == 1 else wi.wire.y2,
            )
            for (wi, idx, _pin_idx) in item._anchor_snapshot
        ]
        # Move: setPos triggers itemChange → _sync_anchored_wires.
        item.setPos(QPointF(200, 100))
        # Endpoint do wire (era 100,70) agora deve ser (200,70).
        assert wire_item.wire.x1 == 200
        assert wire_item.wire.y1 == 70
        # Outro endpoint inalterado.
        assert wire_item.wire.x2 == 50
        assert wire_item.wire.y2 == 70

    def test_unanchored_wire_not_affected(self, qapp):
        """Wire que NÃO toca nenhum pino: drag não muda nada."""
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        # Wire longe dos pinos
        scene.add_wire(_make_wire(300, 300, 400, 400))
        item = scene.component_items()[0]
        wire_item = scene.wire_items()[0]

        item._anchor_snapshot = item._capture_attached_anchors()
        assert item._anchor_snapshot == []

        item.setPos(QPointF(200, 100))
        # Wire intacto.
        assert (
            wire_item.wire.x1, wire_item.wire.y1,
            wire_item.wire.x2, wire_item.wire.y2,
        ) == (300, 300, 400, 400)

    def test_two_wires_both_follow(self, qapp):
        """Dois wires fixados ao mesmo componente seguem juntos."""
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        # Wire 1 no pino top, wire 2 no pino bottom.
        scene.add_wire(_make_wire(100, 70, 50, 70))
        scene.add_wire(_make_wire(100, 130, 150, 130))
        item = scene.component_items()[0]
        wires = scene.wire_items()

        item._anchor_snapshot = item._capture_attached_anchors()
        # 2 anchors (1 por wire).
        assert len(item._anchor_snapshot) == 2

        item.setPos(QPointF(120, 100))
        # Top wire endpoint: (100,70) → (120,70)
        assert (wires[0].wire.x1, wires[0].wire.y1) == (120, 70)
        assert (wires[0].wire.x2, wires[0].wire.y2) == (50, 70)  # outro endpoint
        # Bottom wire endpoint: (100,130) → (120,130)
        assert (wires[1].wire.x1, wires[1].wire.y1) == (120, 130)
        assert (wires[1].wire.x2, wires[1].wire.y2) == (150, 130)

    def test_wire_between_two_components_only_moves_attached_endpoint(self, qapp):
        """
        Wire conecta R1 (pino bottom) → R2 (pino top). Só R1 move
        → só endpoint x1,y1 (em R1) move; (x2,y2) em R2 fica.
        """
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_component(_make_resistor("R2", 200, 200))
        # Wire de R1 bottom (100,130) → R2 top (200,170)
        scene.add_wire(_make_wire(100, 130, 200, 170))
        items = scene.component_items()
        r1 = items[0] if items[0].component.name == "R1" else items[1]
        wire_item = scene.wire_items()[0]

        r1._anchor_snapshot = r1._capture_attached_anchors()
        # R1 só ancora x1,y1 (bottom pin idx=1)
        assert len(r1._anchor_snapshot) == 1
        assert r1._anchor_snapshot[0][1] == 1  # endpoint_idx

        r1.setPos(QPointF(110, 100))
        # x1,y1: (100,130) → (110,130)
        assert (wire_item.wire.x1, wire_item.wire.y1) == (110, 130)
        # x2,y2 inalterado.
        assert (wire_item.wire.x2, wire_item.wire.y2) == (200, 170)


# ---------------------------------------------------------------------------
# Rotate / Mirror via método direto (rotate_cw/rotate_ccw/mirror_x)
# ---------------------------------------------------------------------------


class TestRotateMirrorFollow:

    def test_rotate_ccw_moves_pin_and_wire_follows(self, qapp):
        """
        R1 em (100,100), rot=0 → pinos (100,70) e (100,130).
        Wire em (100,70). Rotate CCW (rotation = 1 → 90° CCW) →
        pino top vai para (-30, 0) local → mapToScene = (100+30, 100+0)
        = (130, 100). Wire endpoint deve ir para (130, 100).
        """
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100, rotation=0))
        scene.add_wire(_make_wire(100, 70, 50, 70))
        item = scene.component_items()[0]
        wire_item = scene.wire_items()[0]

        # Antes: wire endpoint coincide com pino top (100,70)
        assert (wire_item.wire.x1, wire_item.wire.y1) == (100, 70)

        item.rotate_ccw()
        # Após rot CCW (rotation = 1, ângulo +90°), pino que era
        # (0,-30) em local agora aplica setRotation(90) → mapToScene
        # roda anti-horário. Em Qt, setRotation com valor positivo
        # roda *horário* na visualização default (eixo Y para
        # baixo). Em vez de mexer com transformações analiticamente,
        # validamos que o endpoint do wire COINCIDE com o novo
        # pino[0].
        new_pin_top = item.pin_positions_scene()[0]
        nx = int(round(new_pin_top.x()))
        ny = int(round(new_pin_top.y()))
        assert (wire_item.wire.x1, wire_item.wire.y1) == (nx, ny)
        # Outro endpoint do wire (não fixado) inalterado.
        assert (wire_item.wire.x2, wire_item.wire.y2) == (50, 70)

    def test_mirror_x_keeps_wire_anchored(self, qapp):
        """Mirror X: pinos (0,-30)/(0,30) mantêm posição (eixo Y).
        Wire fixado no top permanece colado."""
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_wire(_make_wire(100, 70, 50, 70))
        item = scene.component_items()[0]
        wire_item = scene.wire_items()[0]

        item.mirror_x()
        new_pin_top = item.pin_positions_scene()[0]
        nx = int(round(new_pin_top.x()))
        ny = int(round(new_pin_top.y()))
        assert (wire_item.wire.x1, wire_item.wire.y1) == (nx, ny)

    def test_rotate_command_via_undo_stack(self, qapp):
        """RotateComponentCommand undoable: rotação + undo
        retorna wire ao estado original."""
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_wire(_make_wire(100, 70, 50, 70))
        comp = scene.project.components[0]
        wire = scene.project.wires[0]

        before = (wire.x1, wire.y1, wire.x2, wire.y2)
        cmd = RotateComponentCommand(scene, comp, direction=+1)
        stack.push(cmd)
        # Wire moveu para nova posição do pino
        item = scene.find_component_item(comp)
        new_pin = item.pin_positions_scene()[0]
        assert (wire.x1, wire.y1) == (
            int(round(new_pin.x())), int(round(new_pin.y())),
        )

        stack.undo()
        # Wire voltou ao original
        assert (wire.x1, wire.y1, wire.x2, wire.y2) == before

    def test_mirror_command_via_undo_stack(self, qapp):
        """MirrorComponentCommand undoable: undo restaura wire."""
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_wire(_make_wire(100, 70, 50, 70))
        comp = scene.project.components[0]
        wire = scene.project.wires[0]

        before = (wire.x1, wire.y1, wire.x2, wire.y2)
        cmd = MirrorComponentCommand(scene, comp)
        stack.push(cmd)
        stack.undo()
        assert (wire.x1, wire.y1, wire.x2, wire.y2) == before


# ---------------------------------------------------------------------------
# Undo / redo do MoveComponentCommand com wire_anchors
# ---------------------------------------------------------------------------


class TestMoveComponentCommandWithWires:

    def test_redo_applies_new_positions(self, qapp):
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_wire(_make_wire(100, 70, 50, 70))
        comp = scene.project.components[0]
        wire = scene.project.wires[0]

        cmd = MoveComponentCommand(
            scene, comp,
            old_x=100, old_y=100,
            new_x=200, new_y=100,
            wire_anchors=[(wire, 1, 100, 70, 200, 70)],
        )
        cmd.redo()
        assert (comp.x, comp.y) == (200, 100)
        assert (wire.x1, wire.y1) == (200, 70)
        assert (wire.x2, wire.y2) == (50, 70)  # outro endpoint inalterado

    def test_undo_restores_old_positions(self, qapp):
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_wire(_make_wire(100, 70, 50, 70))
        comp = scene.project.components[0]
        wire = scene.project.wires[0]

        cmd = MoveComponentCommand(
            scene, comp,
            old_x=100, old_y=100,
            new_x=200, new_y=100,
            wire_anchors=[(wire, 1, 100, 70, 200, 70)],
        )
        cmd.redo()
        cmd.undo()
        assert (comp.x, comp.y) == (100, 100)
        assert (wire.x1, wire.y1) == (100, 70)

    def test_redo_undo_redo_idempotent(self, qapp):
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_wire(_make_wire(100, 70, 50, 70))
        comp = scene.project.components[0]
        wire = scene.project.wires[0]

        cmd = MoveComponentCommand(
            scene, comp,
            old_x=100, old_y=100,
            new_x=200, new_y=100,
            wire_anchors=[(wire, 1, 100, 70, 200, 70)],
        )
        cmd.redo()
        cmd.undo()
        cmd.redo()
        assert (comp.x, comp.y) == (200, 100)
        assert (wire.x1, wire.y1) == (200, 70)

    def test_no_merge_when_wire_anchors_present(self, qapp):
        """Comandos com wire_anchors não fazem merge — cada drag
        é uma operação atômica de undo."""
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_wire(_make_wire(100, 70, 50, 70))
        comp = scene.project.components[0]
        wire = scene.project.wires[0]

        c1 = MoveComponentCommand(
            scene, comp, 100, 100, 150, 100,
            wire_anchors=[(wire, 1, 100, 70, 150, 70)],
        )
        c2 = MoveComponentCommand(
            scene, comp, 150, 100, 200, 100,
            wire_anchors=[(wire, 1, 150, 70, 200, 70)],
        )
        assert c1.mergeWith(c2) is False

    def test_merge_still_works_without_anchors(self, qapp):
        """Sem wire_anchors mantém comportamento legacy: merge OK."""
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        comp = scene.project.components[0]

        c1 = MoveComponentCommand(scene, comp, 100, 100, 150, 100)
        c2 = MoveComponentCommand(scene, comp, 150, 100, 200, 100)
        assert c1.mergeWith(c2) is True
        assert c1._new == (200, 100)


# ---------------------------------------------------------------------------
# Integração end-to-end via QUndoStack
# ---------------------------------------------------------------------------


class TestEndToEndUndoRedo:

    def test_drag_then_undo_restores_wire(self, qapp):
        """
        Simula drag completo (sem QMouseEvent — usamos os mesmos
        passos que ``mousePressEvent`` / ``mouseReleaseEvent`` fariam,
        mais ``setPos`` para disparar o ``itemChange``).
        Validamos undo/redo via QUndoStack real.
        """
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        scene.add_component(_make_resistor("R1", 100, 100))
        scene.add_wire(_make_wire(100, 70, 50, 70))
        item = scene.component_items()[0]
        wire_item = scene.wire_items()[0]

        # mousePress equivalente: captura state inicial + anchors.
        item._press_pos = (item.component.x, item.component.y)
        item._anchor_snapshot = item._capture_attached_anchors()
        item._anchor_before_endpoints = [
            (
                wi, idx,
                wi.wire.x1 if idx == 1 else wi.wire.x2,
                wi.wire.y1 if idx == 1 else wi.wire.y2,
            )
            for (wi, idx, _pin_idx) in item._anchor_snapshot
        ]
        assert len(item._anchor_snapshot) == 1

        # Simula movimento: setPos dispara itemChange →
        # _sync_anchored_wires move o endpoint do wire.
        item.setPos(QPointF(200, 100))
        assert (wire_item.wire.x1, wire_item.wire.y1) == (200, 70)

        # mouseRelease equivalente: empilha o command com snapshots.
        old_x, old_y = item._press_pos
        new_x, new_y = item.component.x, item.component.y
        wire_after = [
            (
                wi, idx,
                wi.wire.x1 if idx == 1 else wi.wire.x2,
                wi.wire.y1 if idx == 1 else wi.wire.y2,
            )
            for (wi, idx, _pin_idx) in item._anchor_snapshot
        ]
        wire_before = item._anchor_before_endpoints
        # Rebobina (igual a mouseReleaseEvent)
        item.component.x = old_x
        item.component.y = old_y
        for (wi, idx, ox, oy) in wire_before:
            if idx == 1:
                wi.wire.x1 = ox
                wi.wire.y1 = oy
            else:
                wi.wire.x2 = ox
                wi.wire.y2 = oy
            wi.sync_from_model()
        item.sync_from_model()
        wire_anchors = [
            (
                wi.wire, idx, ox, oy,
                wire_after[i][2], wire_after[i][3],
            )
            for i, (wi, idx, ox, oy) in enumerate(wire_before)
        ]
        cmd = MoveComponentCommand(
            scene, item.component,
            old_x, old_y, new_x, new_y,
            wire_anchors=wire_anchors,
        )
        stack.push(cmd)

        # Stack tem 1 comando.
        assert stack.count() == 1
        # Componente em (200,100), wire em (200,70).
        assert (item.component.x, item.component.y) == (200, 100)
        assert (wire_item.wire.x1, wire_item.wire.y1) == (200, 70)

        # Undo
        stack.undo()
        assert (item.component.x, item.component.y) == (100, 100)
        assert (wire_item.wire.x1, wire_item.wire.y1) == (100, 70)

        # Redo
        stack.redo()
        assert (item.component.x, item.component.y) == (200, 100)
        assert (wire_item.wire.x1, wire_item.wire.y1) == (200, 70)
