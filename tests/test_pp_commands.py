"""
Tests for ``app.gui.schematic_pp.commands`` — QUndoCommand subclasses.

Cobertura
---------

* Redo/undo de cada comando individual mantém o PpProject
  consistente.
* ``MoveComponentCommand.mergeWith`` coalesce moves consecutivos.
* ``EditPropertyCommand.mergeWith`` coalesce edits no mesmo campo.
* ``EditNameCommand.mergeWith`` coalesce renames.
* ``RemoveSelectionCommand`` remove e restaura múltiplos itens.
* Sequências de undo/redo mantêm o estado estável (idempotência).
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication

from app.gui.schematic_pp import (
    AddComponentCommand,
    AddWireCommand,
    EditNameCommand,
    EditPropertyCommand,
    MirrorComponentCommand,
    MoveComponentCommand,
    PpScene,
    RemoveComponentCommand,
    RemoveSelectionCommand,
    RemoveWireCommand,
    RotateComponentCommand,
)
from app.preprocessor.models import (
    PpComponent,
    PpProject,
    PpProperty,
    PpWire,
)


# ---------------------------------------------------------------------------
# QApplication fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_R(name: str = "R1", x: int = 100, y: int = 100) -> PpComponent:
    return PpComponent(
        type="R", name=name, visible=True,
        x=x, y=y, label_dx=15, label_dy=-26, mirror=0, rotation=0,
        properties=[
            PpProperty(value="1k",    visible=True),
            PpProperty(value="26.85", visible=False),
            PpProperty(value="european", visible=False),
        ],
    )


def _make_wire(x1=100, y1=100, x2=200, y2=100) -> PpWire:
    return PpWire(x1=x1, y1=y1, x2=x2, y2=y2, label="")


# ---------------------------------------------------------------------------
# AddComponentCommand
# ---------------------------------------------------------------------------


class TestAddComponentCommand:

    def test_redo_adds_component(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        comp = _make_R("R1")
        stack.push(AddComponentCommand(scene, comp))
        assert len(scene.component_items()) == 1
        assert scene.component_items()[0].component is comp

    def test_undo_removes_component(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        comp = _make_R("R1")
        stack.push(AddComponentCommand(scene, comp))
        stack.undo()
        assert len(scene.component_items()) == 0

    def test_redo_after_undo_re_adds(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        comp = _make_R("R1")
        stack.push(AddComponentCommand(scene, comp))
        stack.undo()
        stack.redo()
        assert len(scene.component_items()) == 1

    def test_name_preserved_across_redo(self, qapp):
        """O nome auto-gerado deve ser estável após undo/redo."""
        scene = PpScene()
        # Adiciona 1 R primeiro para reservar "R1".
        scene.add_component(_make_R("R1"))
        stack = QUndoStack()
        newcomp = PpComponent(
            type="R", name="", visible=True, x=200, y=100,
            label_dx=15, label_dy=-26, mirror=0, rotation=0, properties=[],
        )
        stack.push(AddComponentCommand(scene, newcomp))
        first_name = newcomp.name  # autogerado (R2)
        assert first_name != ""
        stack.undo()
        stack.redo()
        assert newcomp.name == first_name

    def test_text_includes_type_before_resolution(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        c = AddComponentCommand(scene, comp)
        assert "R" in c.text()


# ---------------------------------------------------------------------------
# RemoveComponentCommand
# ---------------------------------------------------------------------------


class TestRemoveComponentCommand:

    def test_redo_removes(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(RemoveComponentCommand(scene, comp))
        assert len(scene.component_items()) == 0

    def test_undo_restores_same_object(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(RemoveComponentCommand(scene, comp))
        stack.undo()
        items = scene.component_items()
        assert len(items) == 1
        assert items[0].component is comp


# ---------------------------------------------------------------------------
# AddWireCommand / RemoveWireCommand
# ---------------------------------------------------------------------------


class TestWireCommands:

    def test_add_wire(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        w = _make_wire()
        stack.push(AddWireCommand(scene, w))
        assert len(scene.wire_items()) == 1
        stack.undo()
        assert len(scene.wire_items()) == 0
        stack.redo()
        assert len(scene.wire_items()) == 1

    def test_remove_wire(self, qapp):
        scene = PpScene()
        w = _make_wire()
        scene.add_wire(w)
        stack = QUndoStack()
        stack.push(RemoveWireCommand(scene, w))
        assert len(scene.wire_items()) == 0
        stack.undo()
        assert len(scene.wire_items()) == 1


# ---------------------------------------------------------------------------
# MoveComponentCommand
# ---------------------------------------------------------------------------


class TestMoveComponentCommand:

    def test_move_changes_coords(self, qapp):
        scene = PpScene()
        comp = _make_R("R1", x=100, y=100)
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(MoveComponentCommand(scene, comp, 100, 100, 200, 150))
        assert comp.x == 200
        assert comp.y == 150

    def test_undo_restores_old_coords(self, qapp):
        scene = PpScene()
        comp = _make_R("R1", x=100, y=100)
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(MoveComponentCommand(scene, comp, 100, 100, 200, 150))
        stack.undo()
        assert comp.x == 100
        assert comp.y == 100

    def test_merge_coalesces_consecutive_moves(self, qapp):
        scene = PpScene()
        comp = _make_R("R1", x=100, y=100)
        scene.add_component(comp)
        stack = QUndoStack()

        stack.push(MoveComponentCommand(scene, comp, 100, 100, 110, 100))
        stack.push(MoveComponentCommand(scene, comp, 110, 100, 120, 100))
        stack.push(MoveComponentCommand(scene, comp, 120, 100, 130, 100))

        # Após merge, deve haver uma única entrada no histórico.
        assert stack.count() == 1
        assert comp.x == 130

        # Undo precisa voltar ao ponto inicial (100), não ao último intermediário.
        stack.undo()
        assert comp.x == 100

    def test_merge_refuses_different_component(self, qapp):
        scene = PpScene()
        c1 = _make_R("R1", x=100, y=100)
        c2 = _make_R("R2", x=200, y=200)
        scene.add_component(c1)
        scene.add_component(c2)
        stack = QUndoStack()

        stack.push(MoveComponentCommand(scene, c1, 100, 100, 150, 100))
        stack.push(MoveComponentCommand(scene, c2, 200, 200, 250, 200))
        assert stack.count() == 2


# ---------------------------------------------------------------------------
# RotateComponentCommand / MirrorComponentCommand
# ---------------------------------------------------------------------------


class TestRotateMirror:

    def test_rotate_ccw(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(RotateComponentCommand(scene, comp, -1))
        assert comp.rotation == 3  # (0 - 1) % 4
        stack.undo()
        assert comp.rotation == 0

    def test_rotate_cw(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(RotateComponentCommand(scene, comp, +1))
        assert comp.rotation == 1
        stack.undo()
        assert comp.rotation == 0

    def test_four_rotations_return_to_zero(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        stack = QUndoStack()
        for _ in range(4):
            stack.push(RotateComponentCommand(scene, comp, +1))
        assert comp.rotation == 0

    def test_mirror_toggles(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(MirrorComponentCommand(scene, comp))
        assert comp.mirror == 1
        stack.push(MirrorComponentCommand(scene, comp))
        assert comp.mirror == 0

    def test_mirror_undo_is_symmetric(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(MirrorComponentCommand(scene, comp))
        stack.undo()
        assert comp.mirror == 0


# ---------------------------------------------------------------------------
# EditPropertyCommand / EditNameCommand
# ---------------------------------------------------------------------------


class TestEditProperty:

    def test_edit_value(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(EditPropertyCommand(scene, comp, 0, "4.7k"))
        assert comp.properties[0].value == "4.7k"
        stack.undo()
        assert comp.properties[0].value == "1k"

    def test_merge_coalesces_same_field(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(EditPropertyCommand(scene, comp, 0, "2k"))
        stack.push(EditPropertyCommand(scene, comp, 0, "5k"))
        stack.push(EditPropertyCommand(scene, comp, 0, "10k"))
        assert stack.count() == 1
        assert comp.properties[0].value == "10k"
        stack.undo()
        assert comp.properties[0].value == "1k"  # ponto de partida

    def test_merge_refuses_different_field(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(EditPropertyCommand(scene, comp, 0, "2k"))
        stack.push(EditPropertyCommand(scene, comp, 1, "30"))
        assert stack.count() == 2

    def test_index_out_of_range_raises(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        with pytest.raises(IndexError):
            EditPropertyCommand(scene, comp, 999, "x")


class TestEditName:

    def test_rename(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(EditNameCommand(scene, comp, "RA"))
        assert comp.name == "RA"
        stack.undo()
        assert comp.name == "R1"

    def test_merge_coalesces_renames(self, qapp):
        scene = PpScene()
        comp = _make_R("R1")
        scene.add_component(comp)
        stack = QUndoStack()
        stack.push(EditNameCommand(scene, comp, "R_A"))
        stack.push(EditNameCommand(scene, comp, "R_B"))
        stack.push(EditNameCommand(scene, comp, "R_C"))
        assert stack.count() == 1
        stack.undo()
        assert comp.name == "R1"


# ---------------------------------------------------------------------------
# RemoveSelectionCommand
# ---------------------------------------------------------------------------


class TestRemoveSelectionCommand:

    def test_removes_components_and_wires(self, qapp):
        scene = PpScene()
        c1 = _make_R("R1", x=100, y=100)
        c2 = _make_R("R2", x=200, y=100)
        w = _make_wire()
        scene.add_component(c1)
        scene.add_component(c2)
        scene.add_wire(w)

        stack = QUndoStack()
        stack.push(RemoveSelectionCommand(scene, [c1, c2], [w]))

        assert len(scene.component_items()) == 0
        assert len(scene.wire_items()) == 0

        stack.undo()
        assert len(scene.component_items()) == 2
        assert len(scene.wire_items()) == 1

    def test_empty_selection_is_noop(self, qapp):
        scene = PpScene()
        scene.add_component(_make_R("R1"))
        stack = QUndoStack()
        stack.push(RemoveSelectionCommand(scene, [], []))
        assert len(scene.component_items()) == 1

    def test_text_contains_count(self, qapp):
        scene = PpScene()
        c1 = _make_R("R1")
        c2 = _make_R("R2")
        w = _make_wire()
        cmd = RemoveSelectionCommand(scene, [c1, c2], [w])
        assert "3" in cmd.text()


# ---------------------------------------------------------------------------
# Stacked operations (integration)
# ---------------------------------------------------------------------------


class TestStackedOperations:
    """Encadeamento: adiciona → move → edita → remove, e desfaz tudo."""

    def test_full_stack_undo_restores_empty(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        comp = _make_R("R1")

        stack.push(AddComponentCommand(scene, comp))
        stack.push(MoveComponentCommand(scene, comp, 100, 100, 200, 100))
        stack.push(EditPropertyCommand(scene, comp, 0, "4.7k"))
        stack.push(RotateComponentCommand(scene, comp, +1))

        # Faz undo até vazio (não conta quantos merges aconteceram, só o efeito).
        while stack.canUndo():
            stack.undo()

        assert len(scene.component_items()) == 0

    def test_mixed_add_remove_preserves_identity(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        comp = _make_R("R1")

        stack.push(AddComponentCommand(scene, comp))
        stack.push(RemoveComponentCommand(scene, comp))
        stack.undo()  # desfaz remove → deve ter o mesmo comp de volta
        stack.undo()  # desfaz add → vazio

        items = scene.component_items()
        assert len(items) == 0

        stack.redo()
        items = scene.component_items()
        assert len(items) == 1
        assert items[0].component is comp
