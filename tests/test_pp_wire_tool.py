"""
Tests for wire-placement tool and drag-drop from palette (v0.21.5).

Cobertura
---------

* ``PpView.set_tool`` troca entre select e wire, com estado visual.
* Dois cliques em modo wire emitem ``wire_drawn`` com as coordenadas
  snappadas corretas.
* ``Esc`` cancela fio em progresso; tecla ``V`` volta ao modo
  select.
* ``PpPalette.build_drag`` produz um ``QDrag`` com mime-type
  ``application/x-atp-studio-pp-type`` e payload correto.
* ``PpView`` aceita drop com esse mime e emite
  ``component_dropped(type_code, scene_pos)``.
* Integração: PpEditor conectado → drop adiciona um componente
  via comando undoable; wire drawing empilha ``AddWireCommand``.
* Undo desfaz ambas operações.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QEvent, QMimeData, QPoint, QPointF, Qt
from PySide6.QtGui import (
    QDrag,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeyEvent,
    QMouseEvent,
)
from PySide6.QtWidgets import QApplication

from app.gui.schematic_pp import (
    PpEditor,
    PpPalette,
    PpScene,
    PpView,
)
from app.preprocessor.models import PpComponent, PpProperty, PpWire


_PP_MIME_TYPE = "application/x-atp-studio-pp-type"


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


def _click(view: PpView, x: int, y: int) -> None:
    """Dispara um click esquerdo no ponto ``(x, y)`` (coords da viewport)."""
    press = QMouseEvent(
        QEvent.MouseButtonPress,
        QPointF(x, y),
        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier,
    )
    view.mousePressEvent(press)
    release = QMouseEvent(
        QEvent.MouseButtonRelease,
        QPointF(x, y),
        Qt.LeftButton, Qt.NoButton, Qt.NoModifier,
    )
    view.mouseReleaseEvent(release)


def _move(view: PpView, x: int, y: int) -> None:
    mv = QMouseEvent(
        QEvent.MouseMove,
        QPointF(x, y),
        Qt.NoButton, Qt.NoButton, Qt.NoModifier,
    )
    view.mouseMoveEvent(mv)


# ---------------------------------------------------------------------------
# PpView tool switching
# ---------------------------------------------------------------------------


class TestToolSwitching:

    def test_default_is_select(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        assert v.tool == PpView.TOOL_SELECT

    def test_set_tool_wire(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        v.set_tool(PpView.TOOL_WIRE)
        assert v.tool == PpView.TOOL_WIRE

    def test_set_invalid_tool_raises(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        with pytest.raises(ValueError):
            v.set_tool("bogus")

    def test_tool_changed_signal_fires(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        received: list[str] = []
        v.tool_changed.connect(received.append)
        v.set_tool(PpView.TOOL_WIRE)
        assert received == [PpView.TOOL_WIRE]

    def test_tool_changed_does_not_fire_when_same(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        received: list[str] = []
        v.tool_changed.connect(received.append)
        # já é TOOL_SELECT; setar para ele não deve emitir.
        v.set_tool(PpView.TOOL_SELECT)
        assert received == []

    def test_keyboard_w_enters_wire_mode(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        ev = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_W, Qt.NoModifier)
        v.keyPressEvent(ev)
        assert v.tool == PpView.TOOL_WIRE

    def test_keyboard_v_enters_select_mode(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        v.set_tool(PpView.TOOL_WIRE)
        ev = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_V, Qt.NoModifier)
        v.keyPressEvent(ev)
        assert v.tool == PpView.TOOL_SELECT

    def test_escape_cancels_wire_in_progress(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        v.set_tool(PpView.TOOL_WIRE)
        # Começa um fio (primeiro clique).
        _click(v, 100, 100)
        assert v._wire_start is not None
        ev = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        v.keyPressEvent(ev)
        assert v._wire_start is None
        # Ainda em wire mode (só o fio em progresso foi cancelado).
        assert v.tool == PpView.TOOL_WIRE

    def test_escape_without_progress_returns_to_select(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        v.set_tool(PpView.TOOL_WIRE)
        ev = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        v.keyPressEvent(ev)
        assert v.tool == PpView.TOOL_SELECT


# ---------------------------------------------------------------------------
# Wire placement
# ---------------------------------------------------------------------------


class TestWireDrawing:

    def test_two_clicks_emit_wire_drawn(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        # Um view precisa ter tamanho para mapToScene funcionar
        # como esperado; show() força layout mínimo.
        v.resize(400, 400)
        v.set_tool(PpView.TOOL_WIRE)
        wires: list[PpWire] = []
        v.wire_drawn.connect(wires.append)

        _click(v, 10, 10)
        _click(v, 100, 50)

        assert len(wires) == 1
        w = wires[0]
        # coordenadas snappadas para múltiplos de 10.
        assert w.x1 % 10 == 0 and w.y1 % 10 == 0
        assert w.x2 % 10 == 0 and w.y2 % 10 == 0

    def test_click_at_same_spot_does_not_emit(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        v.resize(400, 400)
        v.set_tool(PpView.TOOL_WIRE)
        wires: list[PpWire] = []
        v.wire_drawn.connect(wires.append)

        _click(v, 50, 50)
        _click(v, 50, 50)  # mesmo ponto
        assert wires == []

    def test_wire_tool_click_in_select_mode_does_nothing(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        v.resize(400, 400)
        # tool é SELECT por default.
        wires: list[PpWire] = []
        v.wire_drawn.connect(wires.append)
        _click(v, 10, 10)
        _click(v, 100, 100)
        assert wires == []

    def test_ghost_wire_created_after_first_click(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        v.resize(400, 400)
        v.set_tool(PpView.TOOL_WIRE)

        _click(v, 10, 10)
        _move(v, 80, 40)  # fake hover

        assert v._ghost_wire is not None

    def test_ghost_wire_removed_after_completion(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        v.resize(400, 400)
        v.set_tool(PpView.TOOL_WIRE)

        _click(v, 10, 10)
        _move(v, 80, 40)
        _click(v, 80, 40)

        assert v._ghost_wire is None


# ---------------------------------------------------------------------------
# PpPalette drag
# ---------------------------------------------------------------------------


class TestPaletteDrag:

    def test_build_drag_returns_qdrag(self, qapp):
        p = PpPalette()
        drag = p.build_drag("R")
        assert isinstance(drag, QDrag)

    def test_build_drag_mime_contains_type_code(self, qapp):
        p = PpPalette()
        drag = p.build_drag("Vdc")
        mime = drag.mimeData()
        assert mime.hasFormat(_PP_MIME_TYPE)
        raw = bytes(mime.data(_PP_MIME_TYPE)).decode("utf-8")
        assert raw == "Vdc"

    def test_build_drag_also_has_text_fallback(self, qapp):
        p = PpPalette()
        drag = p.build_drag("R")
        mime = drag.mimeData()
        assert mime.text() == "R"

    def test_drag_enabled(self, qapp):
        p = PpPalette()
        assert p.dragEnabled()


# ---------------------------------------------------------------------------
# PpView drop
# ---------------------------------------------------------------------------


class _FakeDropEvent:
    """
    Stand-in para ``QDropEvent`` / ``QDragEnterEvent`` em testes.

    Não usamos as classes reais porque o PySide6 decola a referência
    da ``QMimeData`` que passamos no construtor, e o ``mimeData()``
    retorna um QObject nu sem ``hasFormat``. Como nosso handler
    acessa apenas ``event.position()``, ``event.mimeData()`` e
    ``event.acceptProposedAction()``, um duck type basta.
    """

    def __init__(self, mime: QMimeData, pos: QPointF) -> None:
        self._mime = mime
        self._pos = pos
        self._accepted = False

    def mimeData(self) -> QMimeData:
        return self._mime

    def position(self) -> QPointF:
        return self._pos

    def pos(self) -> QPoint:
        return self._pos.toPoint()

    def acceptProposedAction(self) -> None:
        self._accepted = True

    def accept(self) -> None:
        self._accepted = True

    def isAccepted(self) -> bool:
        return self._accepted


class TestViewDrop:

    def _make_drop(self, code: str, pos: QPointF) -> _FakeDropEvent:
        mime = QMimeData()
        mime.setData(_PP_MIME_TYPE, code.encode("utf-8"))
        return _FakeDropEvent(mime, pos)

    def test_drop_emits_component_dropped(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        v.resize(400, 400)
        received: list[tuple[str, QPointF]] = []
        v.component_dropped.connect(lambda c, p: received.append((c, p)))

        ev = self._make_drop("R", QPointF(80, 60))
        v.dropEvent(ev)

        assert len(received) == 1
        code, pos = received[0]
        assert code == "R"
        # snap para múltiplo de 10.
        assert int(pos.x()) % 10 == 0
        assert int(pos.y()) % 10 == 0

    def test_drop_without_pp_mime_is_ignored(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        v.resize(400, 400)
        received: list = []
        v.component_dropped.connect(lambda c, p: received.append((c, p)))

        mime = QMimeData()
        mime.setText("hello")  # outro mime, sem o nosso tipo
        ev = _FakeDropEvent(mime, QPointF(50, 50))
        # O código chega em super().dropEvent(event), que rejeita
        # duck type. O importante é que o nosso signal NÃO foi
        # emitido e o evento não foi aceito pelo nosso handler.
        try:
            v.dropEvent(ev)
        except TypeError:
            # super().dropEvent rejeita o fake — tudo bem, é porque
            # nosso código caiu no ramo "não é o nosso mime" e
            # delegou para o pai.
            pass
        assert received == []
        assert not ev.isAccepted()

    def test_drag_enter_accepts_pp_mime(self, qapp):
        scene = PpScene()
        v = PpView(scene)
        v.resize(400, 400)
        mime = QMimeData()
        mime.setData(_PP_MIME_TYPE, b"R")
        ev = _FakeDropEvent(mime, QPointF(10, 10))
        v.dragEnterEvent(ev)
        assert ev.isAccepted()


# ---------------------------------------------------------------------------
# Editor integration (drop → AddComponentCommand; wire → AddWireCommand)
# ---------------------------------------------------------------------------


class TestEditorIntegration:

    def test_drop_adds_component_with_undo(self, qapp):
        ed = PpEditor()
        before = len(ed.scene.component_items())

        ed._on_component_dropped("R", QPointF(100, 100))

        items = ed.scene.component_items()
        assert len(items) == before + 1
        assert ed.undo_stack.count() == 1

        ed.undo_stack.undo()
        assert len(ed.scene.component_items()) == before

    def test_wire_drawn_adds_wire_with_undo(self, qapp):
        ed = PpEditor()
        before = len(ed.scene.wire_items())

        w = PpWire(x1=100, y1=100, x2=200, y2=100, label="")
        ed._on_wire_drawn(w)

        assert len(ed.scene.wire_items()) == before + 1
        assert ed.undo_stack.count() == 1

        ed.undo_stack.undo()
        assert len(ed.scene.wire_items()) == before

    def test_add_component_by_type_is_undoable(self, qapp):
        ed = PpEditor()
        ed.view.resize(400, 400)
        ed.add_component_by_type("R")
        assert len(ed.scene.component_items()) == 1
        assert ed.undo_stack.count() == 1
        ed.undo_stack.undo()
        assert len(ed.scene.component_items()) == 0
        ed.undo_stack.redo()
        assert len(ed.scene.component_items()) == 1

    def test_new_project_clears_undo_stack(self, qapp):
        ed = PpEditor()
        ed.view.resize(400, 400)
        ed.add_component_by_type("R")
        ed.add_component_by_type("C")
        assert ed.undo_stack.count() == 2

        ed.new_project()
        assert ed.undo_stack.count() == 0

    def test_tool_changed_updates_toolbar_buttons(self, qapp):
        ed = PpEditor()
        # default: select checked, wire not.
        assert ed.act_tool_select.isChecked()
        assert not ed.act_tool_wire.isChecked()

        ed.view.set_tool(PpView.TOOL_WIRE)
        assert ed.act_tool_wire.isChecked()
        assert not ed.act_tool_select.isChecked()

    def test_properties_panel_uses_command_sink(self, qapp):
        ed = PpEditor()
        ed.view.resize(400, 400)
        item = ed.add_component_by_type("R")
        ed.properties.bind_component(item)
        # Limpa o stack para isolar a próxima ação.
        ed.undo_stack.clear()

        ed.properties._on_prop_changed(0, "4.7k")
        assert item.component.properties[0].value == "4.7k"
        # Deve ter gerado um comando no stack.
        assert ed.undo_stack.count() == 1

        ed.undo_stack.undo()
        assert item.component.properties[0].value != "4.7k"

    def test_properties_panel_name_edit_uses_command_sink(self, qapp):
        ed = PpEditor()
        ed.view.resize(400, 400)
        item = ed.add_component_by_type("R")
        ed.properties.bind_component(item)
        ed.undo_stack.clear()

        old = item.component.name
        ed.properties._on_name_changed("R_NEW")
        assert item.component.name == "R_NEW"
        assert ed.undo_stack.count() == 1

        ed.undo_stack.undo()
        assert item.component.name == old
