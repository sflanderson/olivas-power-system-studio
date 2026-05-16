"""
tests/test_pp_visibility_command.py — v0.22.2.b: toggle de
``PpProperty.visible`` passa pelo QUndoStack via
:class:`EditVisibilityCommand`.

Cobre:

* Construção direta do comando (pré-estado capturado no __init__).
* ``redo`` aplica novo estado, ``undo`` restaura.
* ``mergeWith`` colapsa edições em sequência.
* ``rejeita IndexError`` com prop_index inválido.
* Integração: ``PpPropertiesPanel._on_row_changed`` → command push.
* Ctrl+Z desfaz toggle de visibility sozinho.
* Ctrl+Z desfaz separadamente edição de valor e toggle de
  visibility (dois comandos independentes empilhados).
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from app.gui.schematic_pp.commands import EditVisibilityCommand
from app.gui.schematic_pp.editor import PpEditor
from app.gui.schematic_pp.items import ComponentItem
from app.gui.schematic_pp.scene import PpScene
from app.preprocessor.models import PpComponent, PpProperty


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _make_vcb() -> PpComponent:
    """VCB com 10 propriedades, mix de visible."""
    return PpComponent(
        type="VCB", name="DJ1", visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[
            PpProperty("0.05", visible=True),   # T_open
            PpProperty("1e9",  visible=True),   # T_close
            PpProperty("5.0",  visible=True),   # I_chop
            PpProperty("1.0",  visible=False),  # sigma
            PpProperty("16.0", visible=True),   # di/dt
            PpProperty("0.034", visible=False), # didt_sigma
            PpProperty("17.0", visible=True),   # k
            PpProperty("690.0", visible=False), # U0
            PpProperty("5e-4", visible=False),  # T_bounce
            PpProperty("1",    visible=False),  # Seed
        ],
    )


# ---------------------------------------------------------------------------
# Construção + redo/undo diretos
# ---------------------------------------------------------------------------


class TestEditVisibilityCommandDirect:
    def test_constructor_captures_old_state(self, qapp):
        scene = PpScene()
        comp = _make_vcb()
        scene.add_component(comp)
        cmd = EditVisibilityCommand(scene, comp, 0, False)
        # Before redo, old state preserved
        assert comp.properties[0].visible is True  # nada ainda aplicado
        # text do QUndoCommand tem a ação
        assert "Ocultar" in cmd.text() or "DJ1" in cmd.text()

    def test_redo_applies_new_state(self, qapp):
        scene = PpScene()
        comp = _make_vcb()
        scene.add_component(comp)
        cmd = EditVisibilityCommand(scene, comp, 0, False)
        cmd.redo()
        assert comp.properties[0].visible is False

    def test_undo_restores_old_state(self, qapp):
        scene = PpScene()
        comp = _make_vcb()
        scene.add_component(comp)
        cmd = EditVisibilityCommand(scene, comp, 0, False)
        cmd.redo()
        cmd.undo()
        assert comp.properties[0].visible is True

    def test_rejects_invalid_prop_index(self, qapp):
        scene = PpScene()
        comp = _make_vcb()
        scene.add_component(comp)
        with pytest.raises(IndexError):
            EditVisibilityCommand(scene, comp, 99, True)

    def test_mergeWith_same_prop_collapses(self, qapp):
        scene = PpScene()
        comp = _make_vcb()
        scene.add_component(comp)
        c1 = EditVisibilityCommand(scene, comp, 0, False)
        c2 = EditVisibilityCommand(scene, comp, 0, True)
        assert c1.mergeWith(c2) is True
        # _new agora é o do 2nd comando
        c1.redo()
        assert comp.properties[0].visible is True

    def test_mergeWith_different_prop_rejects(self, qapp):
        scene = PpScene()
        comp = _make_vcb()
        scene.add_component(comp)
        c1 = EditVisibilityCommand(scene, comp, 0, False)
        c2 = EditVisibilityCommand(scene, comp, 1, False)
        assert c1.mergeWith(c2) is False

    def test_mergeWith_different_component_rejects(self, qapp):
        scene = PpScene()
        comp1 = _make_vcb()
        comp2 = _make_vcb()
        comp2.name = "DJ2"
        scene.add_component(comp1)
        scene.add_component(comp2)
        c1 = EditVisibilityCommand(scene, comp1, 0, False)
        c2 = EditVisibilityCommand(scene, comp2, 0, False)
        assert c1.mergeWith(c2) is False


# ---------------------------------------------------------------------------
# Integração: PpEditor.push_edit_visibility + _on_row_changed
# ---------------------------------------------------------------------------


class TestIntegrationWithEditor:
    def test_push_edit_visibility_enqueues_command(self, qapp):
        ed = PpEditor()
        ed.add_component_by_type("VCB")
        item = [i for i in ed.scene.items() if isinstance(i, ComponentItem)][0]
        comp = item.component
        initial = comp.properties[0].visible

        assert ed.undo_stack.count() == 1  # só AddComponent
        ed.push_edit_visibility(comp, 0, not initial)
        assert ed.undo_stack.count() == 2

    def test_push_edit_visibility_noop_when_unchanged(self, qapp):
        """Empilhar com mesmo valor não adiciona comando."""
        ed = PpEditor()
        ed.add_component_by_type("VCB")
        item = [i for i in ed.scene.items() if isinstance(i, ComponentItem)][0]
        comp = item.component
        before = ed.undo_stack.count()
        ed.push_edit_visibility(comp, 0, comp.properties[0].visible)
        assert ed.undo_stack.count() == before

    def test_on_row_changed_uses_visibility_command(self, qapp):
        """Alteração via PropertyRow (painel rico) entra no QUndoStack."""
        ed = PpEditor()
        ed.add_component_by_type("VCB")
        item = [i for i in ed.scene.items() if isinstance(i, ComponentItem)][0]
        ed.properties.bind_component(item)
        comp = item.component
        initial = comp.properties[0].visible
        before = ed.undo_stack.count()

        # Toggle visibility, sem mudar value
        ed.properties._on_row_changed(
            0, comp.properties[0].value, not initial,
        )
        assert ed.undo_stack.count() == before + 1
        assert comp.properties[0].visible == (not initial)

    def test_undo_reverts_visibility_toggle(self, qapp):
        ed = PpEditor()
        ed.add_component_by_type("VCB")
        item = [i for i in ed.scene.items() if isinstance(i, ComponentItem)][0]
        ed.properties.bind_component(item)
        comp = item.component
        initial = comp.properties[0].visible
        ed.properties._on_row_changed(
            0, comp.properties[0].value, not initial,
        )
        ed.undo_stack.undo()
        assert comp.properties[0].visible == initial

    def test_redo_after_undo(self, qapp):
        ed = PpEditor()
        ed.add_component_by_type("VCB")
        item = [i for i in ed.scene.items() if isinstance(i, ComponentItem)][0]
        ed.properties.bind_component(item)
        comp = item.component
        initial = comp.properties[0].visible
        ed.properties._on_row_changed(
            0, comp.properties[0].value, not initial,
        )
        ed.undo_stack.undo()
        ed.undo_stack.redo()
        assert comp.properties[0].visible == (not initial)

    def test_value_and_visibility_are_independent_commands(self, qapp):
        """Mudar value E visibility numa chamada gera 2 commands."""
        ed = PpEditor()
        ed.add_component_by_type("VCB")
        item = [i for i in ed.scene.items() if isinstance(i, ComponentItem)][0]
        ed.properties.bind_component(item)
        comp = item.component
        before = ed.undo_stack.count()
        original_value = comp.properties[2].value
        original_vis = comp.properties[2].visible

        # Muda ambos ao mesmo tempo
        ed.properties._on_row_changed(2, "8.5", not original_vis)
        assert ed.undo_stack.count() == before + 2
        assert comp.properties[2].value == "8.5"
        assert comp.properties[2].visible == (not original_vis)

        # Undo 1x desfaz APENAS o último (visibility)
        ed.undo_stack.undo()
        assert comp.properties[2].value == "8.5"   # ainda 8.5
        assert comp.properties[2].visible == original_vis  # visibility revertida

        # Undo 2º desfaz o value
        ed.undo_stack.undo()
        assert comp.properties[2].value == original_value

    def test_merge_multiple_visibility_toggles(self, qapp):
        """Dois toggles consecutivos do mesmo prop → 1 command (merge)."""
        ed = PpEditor()
        ed.add_component_by_type("VCB")
        item = [i for i in ed.scene.items() if isinstance(i, ComponentItem)][0]
        ed.properties.bind_component(item)
        comp = item.component
        initial = comp.properties[0].visible

        before = ed.undo_stack.count()
        # Toggle on → off → on (3 edits, devem colapsar para 1)
        ed.properties._on_row_changed(0, comp.properties[0].value, not initial)
        ed.properties._on_row_changed(0, comp.properties[0].value, initial)
        ed.properties._on_row_changed(0, comp.properties[0].value, not initial)
        # Qt QUndoStack com mergeWith usa o id() para decidir merge.
        # Devem estar todos mergeados em 1 entry (ou poucas).
        added = ed.undo_stack.count() - before
        assert added == 1, (
            f"Esperado 1 command (merge), obtive {added}"
        )
