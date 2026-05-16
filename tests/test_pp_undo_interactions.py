"""
Tests para integrações undo-aware v0.21.6.

Cobertura
---------

* :class:`ComponentItem` drag → :class:`MoveComponentCommand`
  empilhado via ``scene.undo_stack`` (injetado pelo :class:`PpEditor`).
* Atalhos de teclado (R, Shift+R, E, Del) empilham comandos
  correspondentes.
* Context menu no :class:`PpView` produz :class:`QMenu` com as
  ações esperadas por tipo de item; as ações, quando acionadas,
  empilham comandos.
* Ghost wire usa cor do :class:`QPalette` (Highlight).
* ``_render_drag_preview`` gera :class:`QPixmap` para tipos
  válidos e retorna ``None`` para tipos sem renderer.
* ``PpPalette.build_drag`` anexa o pixmap ao :class:`QDrag`.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import (
    QContextMenuEvent,
    QKeyEvent,
    QMouseEvent,
    QPalette,
    QPixmap,
    QUndoStack,
)
from PySide6.QtWidgets import QApplication, QGraphicsSceneMouseEvent

from app.gui.schematic_pp import (
    PpEditor,
    PpPalette,
    PpScene,
    PpView,
)
from app.gui.schematic_pp import commands as cmd
from app.gui.schematic_pp.editor import _render_drag_preview
from app.gui.schematic_pp.items import ComponentItem
from app.preprocessor.models import PpComponent, PpProperty, PpWire


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_component(type_code: str = "R", name: str = "R1",
                    x: int = 100, y: int = 100) -> PpComponent:
    return PpComponent(
        type=type_code, name=name, visible=True,
        x=x, y=y, label_dx=15, label_dy=-26,
        mirror=0, rotation=0,
        properties=[PpProperty(value="1k", visible=True)],
    )


def _key(key: int, modifiers=Qt.NoModifier) -> QKeyEvent:
    return QKeyEvent(QEvent.KeyPress, key, modifiers)


def _gfx_press() -> QGraphicsSceneMouseEvent:
    """Constrói um :class:`QGraphicsSceneMouseEvent` de press LeftButton."""
    ev = QGraphicsSceneMouseEvent(QEvent.GraphicsSceneMousePress)
    ev.setButton(Qt.LeftButton)
    ev.setButtons(Qt.LeftButton)
    ev.setPos(QPointF(0, 0))
    return ev


def _gfx_release() -> QGraphicsSceneMouseEvent:
    ev = QGraphicsSceneMouseEvent(QEvent.GraphicsSceneMouseRelease)
    ev.setButton(Qt.LeftButton)
    ev.setButtons(Qt.NoButton)
    ev.setPos(QPointF(0, 0))
    return ev


# ---------------------------------------------------------------------------
# ComponentItem drag → MoveComponentCommand
# ---------------------------------------------------------------------------


class TestComponentItemDragUndoable:
    """Drag com mouse de um ComponentItem empilha MoveCommand."""

    def test_scene_accepts_undo_stack_attr(self, qapp):
        scene = PpScene()
        assert hasattr(scene, "undo_stack")
        # Default é None — só o editor conecta.
        assert scene.undo_stack is None

    def test_editor_attaches_stack_to_scene(self, qapp):
        editor = PpEditor()
        assert editor.scene.undo_stack is editor.undo_stack

    def test_press_captures_starting_position(self, qapp):
        scene = PpScene()
        comp = _make_component(x=100, y=100)
        item = scene.add_component(comp)
        item.mousePressEvent(_gfx_press())
        assert item._press_pos == (100, 100)

    def test_release_without_movement_no_command(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        comp = _make_component(x=100, y=100)
        item = scene.add_component(comp)
        item.mousePressEvent(_gfx_press())
        # Não move — a posição permanece (100, 100).
        item.mouseReleaseEvent(_gfx_release())
        assert stack.count() == 0

    def test_release_with_movement_pushes_command(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        comp = _make_component(x=100, y=100)
        item = scene.add_component(comp)
        item.mousePressEvent(_gfx_press())
        # Simula drag: itemChange atualiza o component.
        comp.x = 200
        comp.y = 150
        item.mouseReleaseEvent(_gfx_release())
        assert stack.count() == 1
        # Posição final deve ser (200, 150) após o redo.
        assert (comp.x, comp.y) == (200, 150)
        # Undo volta para (100, 100).
        stack.undo()
        assert (comp.x, comp.y) == (100, 100)
        # Redo volta para (200, 150).
        stack.redo()
        assert (comp.x, comp.y) == (200, 150)

    def test_release_without_stack_preserves_position(self, qapp):
        scene = PpScene()
        # Sem undo_stack anexo.
        comp = _make_component(x=100, y=100)
        item = scene.add_component(comp)
        item.mousePressEvent(_gfx_press())
        comp.x = 250
        comp.y = 120
        item.mouseReleaseEvent(_gfx_release())
        # Sem stack: a posição nova vence (já estava setada via itemChange).
        assert (comp.x, comp.y) == (250, 120)


# ---------------------------------------------------------------------------
# Keyboard → commands
# ---------------------------------------------------------------------------


class TestKeyboardUndoable:

    def test_r_pushes_rotate_command(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        comp = _make_component()
        item = scene.add_component(comp)
        item.setSelected(True)
        v = PpView(scene)
        v.keyPressEvent(_key(Qt.Key_R))
        assert stack.count() == 1
        assert comp.rotation == 1

    def test_shift_r_pushes_rotate_inverse(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        comp = _make_component()
        item = scene.add_component(comp)
        item.setSelected(True)
        v = PpView(scene)
        v.keyPressEvent(_key(Qt.Key_R, Qt.ShiftModifier))
        assert stack.count() == 1
        # rotation = (0 - 1) % 4 = 3
        assert comp.rotation == 3

    def test_r_without_selection_is_noop(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        v = PpView(scene)
        v.keyPressEvent(_key(Qt.Key_R))
        assert stack.count() == 0

    def test_e_pushes_mirror_command(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        comp = _make_component()
        item = scene.add_component(comp)
        item.setSelected(True)
        v = PpView(scene)
        v.keyPressEvent(_key(Qt.Key_E))
        assert stack.count() == 1
        assert comp.mirror == 1

    def test_delete_pushes_remove_selection_command(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        comp = _make_component()
        item = scene.add_component(comp)
        item.setSelected(True)
        v = PpView(scene)
        v.keyPressEvent(_key(Qt.Key_Delete))
        assert stack.count() == 1
        assert comp not in scene.project.components
        # Undo restores.
        stack.undo()
        assert comp in scene.project.components

    def test_multi_rotate_wrapped_in_macro(self, qapp):
        """Rotacionar 3 itens = 1 entrada no histórico (macro)."""
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        items = []
        for i in range(3):
            c = _make_component(name=f"R{i + 1}", x=100 + 50 * i)
            it = scene.add_component(c)
            it.setSelected(True)
            items.append(it)
        v = PpView(scene)
        v.keyPressEvent(_key(Qt.Key_R))
        # 1 macro na stack (que engloba os 3 rotates).
        assert stack.count() == 1
        assert all(it.component.rotation == 1 for it in items)
        # Undo reverte todas.
        stack.undo()
        assert all(it.component.rotation == 0 for it in items)

    def test_fallback_without_stack_still_rotates(self, qapp):
        """View sem undo_stack na cena ainda aplica a rotação direta."""
        scene = PpScene()
        # Sem stack anexa.
        comp = _make_component()
        item = scene.add_component(comp)
        item.setSelected(True)
        v = PpView(scene)
        v.keyPressEvent(_key(Qt.Key_R))
        assert comp.rotation == 1


# ---------------------------------------------------------------------------
# Context menu
# ---------------------------------------------------------------------------


class TestContextMenu:

    def test_build_menu_for_component_has_five_actions(self, qapp):
        scene = PpScene()
        comp = _make_component()
        item = scene.add_component(comp)
        v = PpView(scene)
        menu = v._build_context_menu(item, scene)
        assert menu is not None
        actions = [a for a in menu.actions() if not a.isSeparator()]
        texts = [a.text() for a in actions]
        assert any("Propriedades" in t for t in texts)
        assert any("Rotacionar" in t and "inverso" not in t for t in texts)
        assert any("inverso" in t for t in texts)
        assert any("Espelhar" in t for t in texts)
        assert any("Excluir" in t for t in texts)

    def test_build_menu_for_wire_has_only_delete(self, qapp):
        scene = PpScene()
        wire = PpWire(x1=0, y1=0, x2=100, y2=0, label="")
        item = scene.add_wire(wire)
        v = PpView(scene)
        menu = v._build_context_menu(item, scene)
        assert menu is not None
        actions = [a for a in menu.actions() if not a.isSeparator()]
        texts = [a.text() for a in actions]
        assert len(texts) == 1
        assert "Excluir" in texts[0]

    def test_build_menu_returns_none_for_other_item(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        # passa algo que não é Component nem Wire.
        assert v._build_context_menu(object(), scene) is None

    def test_menu_rotate_action_pushes_command(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        comp = _make_component()
        item = scene.add_component(comp)
        item.setSelected(True)
        v = PpView(scene)
        menu = v._build_context_menu(item, scene)
        rot_action = next(
            a for a in menu.actions()
            if "Rotacionar" in a.text() and "inverso" not in a.text()
        )
        rot_action.trigger()
        assert stack.count() == 1
        assert comp.rotation == 1

    def test_menu_delete_action_pushes_command(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        comp = _make_component()
        item = scene.add_component(comp)
        item.setSelected(True)
        v = PpView(scene)
        menu = v._build_context_menu(item, scene)
        del_action = next(a for a in menu.actions() if "Excluir" in a.text())
        del_action.trigger()
        assert stack.count() == 1
        assert comp not in scene.project.components

    def test_menu_mirror_action_pushes_command(self, qapp):
        scene = PpScene()
        stack = QUndoStack()
        scene.undo_stack = stack
        comp = _make_component()
        item = scene.add_component(comp)
        item.setSelected(True)
        v = PpView(scene)
        menu = v._build_context_menu(item, scene)
        mirror_action = next(a for a in menu.actions() if "Espelhar" in a.text())
        mirror_action.trigger()
        assert stack.count() == 1
        assert comp.mirror == 1

    def test_menu_properties_action_emits_double_click_signal(self, qapp):
        scene = PpScene()
        comp = _make_component()
        item = scene.add_component(comp)
        v = PpView(scene)
        received = []
        v.item_double_clicked.connect(lambda it: received.append(it))
        menu = v._build_context_menu(item, scene)
        props_action = next(
            a for a in menu.actions() if "Propriedades" in a.text()
        )
        props_action.trigger()
        assert received == [item]


# ---------------------------------------------------------------------------
# Ghost wire theming
# ---------------------------------------------------------------------------


class TestGhostWireTheme:

    def test_ghost_wire_pen_uses_highlight_color(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        v.set_tool(PpView.TOOL_WIRE)
        v._wire_start = QPointF(0, 0)
        v._update_ghost_wire(QPointF(50, 50))
        assert v._ghost_wire is not None
        pen_color = v._ghost_wire.pen().color()
        hi = v.palette().color(QPalette.Highlight)
        # As cores devem bater (ignorando o alpha que forçamos).
        assert pen_color.red() == hi.red()
        assert pen_color.green() == hi.green()
        assert pen_color.blue() == hi.blue()
        assert pen_color.alpha() == 160


# ---------------------------------------------------------------------------
# Drag preview (palette pixmap)
# ---------------------------------------------------------------------------


class TestDragPreviewPixmap:

    def test_render_preview_for_known_type(self, qapp):
        pm = _render_drag_preview("R")
        assert pm is not None
        assert isinstance(pm, QPixmap)
        assert not pm.isNull()
        assert pm.width() >= 32
        assert pm.height() >= 32

    def test_render_preview_for_capacitor(self, qapp):
        pm = _render_drag_preview("C")
        assert pm is not None
        assert not pm.isNull()

    def test_render_preview_for_unknown_type(self, qapp):
        pm = _render_drag_preview("__DOES_NOT_EXIST__")
        assert pm is None

    def test_build_drag_sets_pixmap(self, qapp):
        palette = PpPalette()
        drag = palette.build_drag("R")
        pm = drag.pixmap()
        assert pm is not None
        assert not pm.isNull()

    def test_build_drag_unknown_has_no_pixmap(self, qapp):
        palette = PpPalette()
        drag = palette.build_drag("__NONE__")
        # Quando o tipo é desconhecido, setPixmap não é chamado.
        # A API do Qt retorna QPixmap vazio (null).
        pm = drag.pixmap()
        assert pm is None or pm.isNull()


# ---------------------------------------------------------------------------
# Integração end-to-end no editor
# ---------------------------------------------------------------------------


class TestEditorIntegrationV0216:

    def test_drag_move_in_editor_creates_undoable_move(self, qapp):
        editor = PpEditor()
        item = editor.add_component_by_type("R", scene_pos=QPointF(100, 100))
        assert editor.undo_stack.count() == 1  # só o add
        # Simula drag.
        item.mousePressEvent(_gfx_press())
        item.component.x = 200
        item.component.y = 200
        item.mouseReleaseEvent(_gfx_release())
        assert editor.undo_stack.count() == 2
        # Undo reverte só o move.
        editor.undo_stack.undo()
        assert (item.component.x, item.component.y) == (100, 100)
        # Mas o componente continua na cena.
        assert item.component in editor.scene.project.components

    def test_keyboard_rotate_in_editor_undoable(self, qapp):
        editor = PpEditor()
        item = editor.add_component_by_type("R", scene_pos=QPointF(100, 100))
        item.setSelected(True)
        editor.view.keyPressEvent(_key(Qt.Key_R))
        # 1 add + 1 rotate macro = 2 entradas.
        assert editor.undo_stack.count() == 2
        assert item.component.rotation == 1
        editor.undo_stack.undo()
        assert item.component.rotation == 0

    def test_new_project_clears_stack_and_scene(self, qapp):
        editor = PpEditor()
        editor.add_component_by_type("R", scene_pos=QPointF(100, 100))
        editor.add_component_by_type("C", scene_pos=QPointF(200, 100))
        assert editor.undo_stack.count() == 2
        editor.new_project()
        assert editor.undo_stack.count() == 0
        assert len(editor.scene.project.components) == 0

    def test_context_menu_delete_in_editor(self, qapp):
        editor = PpEditor()
        item = editor.add_component_by_type("R", scene_pos=QPointF(100, 100))
        item.setSelected(True)
        menu = editor.view._build_context_menu(item, editor.scene)
        del_action = next(
            a for a in menu.actions() if "Excluir" in a.text()
        )
        del_action.trigger()
        # Add + Remove = 2 entradas.
        assert editor.undo_stack.count() == 2
        assert item.component not in editor.scene.project.components
        editor.undo_stack.undo()
        assert item.component in editor.scene.project.components
