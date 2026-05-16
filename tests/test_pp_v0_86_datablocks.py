"""
tests/test_pp_v0_86_datablocks.py — v0.86: PTW Equipment-style
datablocks.

Cobertura
---------

* PpDataBlock dataclass + PpProject.datablocks
* DataBlockItem QGraphicsObject (parent = ComponentItem):
  - sync_from_model atualiza pos
  - drag atualiza dx/dy do model
* PpScene API: add/remove/find datablock
* AddDataBlockCommand / RemoveDataBlockCommand /
  EditDataBlockLinesCommand (undoable)
* DataBlockEditDialog
* Sidecar JSON: save/load round-trip
* Editor integration: _on_request_add_datablock empilha
  AddDataBlockCommand
"""

from __future__ import annotations

import json

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import QPointF
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication, QDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_resistor(name: str = "R1", x: int = 100, y: int = 100):
    from app.preprocessor.models import PpComponent, PpProperty
    return PpComponent(
        type="R", name=name, visible=True,
        x=x, y=y,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty("1k")],
    )


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class TestPpDataBlockModel:

    def test_construct_with_defaults(self):
        from app.preprocessor.models import PpDataBlock
        db = PpDataBlock(component_name="R1")
        assert db.component_name == "R1"
        assert db.dx == 50
        assert db.dy == -10
        assert db.lines == []
        assert db.visible is True

    def test_pp_project_has_datablocks_field(self):
        from app.preprocessor.models import PpProject, PpDataBlock
        proj = PpProject()
        assert proj.datablocks == []
        db = PpDataBlock(component_name="R1", lines=["foo"])
        proj.datablocks.append(db)
        assert len(proj.datablocks) == 1


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------


class TestSceneDataBlockAPI:

    def test_add_datablock_creates_item(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.items import DataBlockItem
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_resistor("R1"))
        db = PpDataBlock(
            component_name="R1", lines=["I = 1.5 A"],
        )
        item = scene.add_datablock(db)
        assert isinstance(item, DataBlockItem)
        assert item.datablock is db
        # Item registrado em datablock_items
        assert item in scene.datablock_items()

    def test_add_datablock_returns_none_if_no_host(self, qapp):
        """Componente host não existe → None."""
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        db = PpDataBlock(component_name="GHOST")
        item = scene.add_datablock(db)
        assert item is None

    def test_remove_datablock(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_resistor("R1"))
        db = PpDataBlock(component_name="R1", lines=["x"])
        item = scene.add_datablock(db)
        scene.remove_datablock(item)
        assert item not in scene.datablock_items()
        assert db not in scene.project.datablocks

    def test_find_datablock_item(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_resistor("R1"))
        db = PpDataBlock(component_name="R1", lines=["x"])
        item = scene.add_datablock(db)
        assert scene.find_datablock_item(db) is item


# ---------------------------------------------------------------------------
# DataBlockItem visual
# ---------------------------------------------------------------------------


class TestDataBlockItem:

    def test_pos_reflects_dx_dy(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        db = PpDataBlock(
            component_name="R1", dx=80, dy=-30, lines=["x"],
        )
        item = scene.add_datablock(db)
        # Posição local relativa ao parent (host = R1)
        assert (item.pos().x(), item.pos().y()) == (80.0, -30.0)

    def test_drag_updates_dx_dy(self, qapp):
        """Mover datablock via setPos atualiza dx/dy do PpDataBlock."""
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_resistor("R1", 100, 100))
        db = PpDataBlock(component_name="R1", lines=["x"])
        item = scene.add_datablock(db)
        # Move datablock para nova posição relativa
        item.setPos(QPointF(120, 40))
        assert db.dx == 120
        assert db.dy == 40

    def test_bounding_rect_grows_with_lines(self, qapp):
        """Mais linhas → bounding rect mais alto."""
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_resistor("R1"))
        db = PpDataBlock(component_name="R1", lines=["a"])
        item = scene.add_datablock(db)
        h1 = item.boundingRect().height()
        # Adiciona 3 linhas → re-sync
        db.lines = ["a", "b", "c", "d"]
        item.prepareGeometryChange()
        item.sync_from_model()
        h2 = item.boundingRect().height()
        assert h2 > h1


# ---------------------------------------------------------------------------
# Commands undoable
# ---------------------------------------------------------------------------


class TestDataBlockCommands:

    def test_add_command_redo_undo(self, qapp):
        from app.gui.schematic_pp.commands import AddDataBlockCommand
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_resistor("R1"))
        stack = QUndoStack()
        scene.undo_stack = stack
        db = PpDataBlock(component_name="R1", lines=["foo"])
        cmd = AddDataBlockCommand(scene, db)
        stack.push(cmd)
        assert db in scene.project.datablocks
        stack.undo()
        assert db not in scene.project.datablocks
        stack.redo()
        assert db in scene.project.datablocks

    def test_remove_command_redo_undo(self, qapp):
        from app.gui.schematic_pp.commands import RemoveDataBlockCommand
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_resistor("R1"))
        db = PpDataBlock(component_name="R1", lines=["x"])
        scene.add_datablock(db)
        stack = QUndoStack()
        cmd = RemoveDataBlockCommand(scene, db)
        stack.push(cmd)
        assert db not in scene.project.datablocks
        stack.undo()
        assert db in scene.project.datablocks

    def test_edit_lines_command(self, qapp):
        from app.gui.schematic_pp.commands import (
            EditDataBlockLinesCommand,
        )
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_resistor("R1"))
        db = PpDataBlock(component_name="R1", lines=["old"])
        scene.add_datablock(db)
        stack = QUndoStack()
        stack.push(
            EditDataBlockLinesCommand(scene, db, ["new1", "new2"])
        )
        assert db.lines == ["new1", "new2"]
        stack.undo()
        assert db.lines == ["old"]


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


class TestDataBlockEditDialog:

    def test_dialog_instantiates(self, qapp):
        from app.gui.datablock_dialog import DataBlockEditDialog
        dlg = DataBlockEditDialog(initial_lines=["a", "b"])
        assert isinstance(dlg, QDialog)

    def test_initial_lines_populated(self, qapp):
        from app.gui.datablock_dialog import DataBlockEditDialog
        dlg = DataBlockEditDialog(initial_lines=["foo", "bar"])
        assert "foo" in dlg._text_edit.toPlainText()
        assert "bar" in dlg._text_edit.toPlainText()

    def test_lines_returns_split(self, qapp):
        from app.gui.datablock_dialog import DataBlockEditDialog
        dlg = DataBlockEditDialog(initial_lines=["a", "b", "c"])
        assert dlg.lines() == ["a", "b", "c"]

    def test_lines_strips_trailing_empty(self, qapp):
        from app.gui.datablock_dialog import DataBlockEditDialog
        dlg = DataBlockEditDialog(initial_lines=[])
        dlg._text_edit.setPlainText("foo\nbar\n\n")
        assert dlg.lines() == ["foo", "bar"]

    def test_apply_template_replaces_text(self, qapp):
        from app.gui.datablock_dialog import DataBlockEditDialog
        dlg = DataBlockEditDialog(initial_lines=["old"])
        # Aplica o template "Curto-circuito"
        idx = dlg._template_combo.findText(
            "Curto-circuito (IEC 60909)"
        )
        dlg._template_combo.setCurrentIndex(idx)
        dlg._apply_template()
        text = dlg._text_edit.toPlainText()
        assert "Ik''" in text
        assert "ip" in text


# ---------------------------------------------------------------------------
# Sidecar I/O
# ---------------------------------------------------------------------------


class TestSidecarIO:

    def test_save_load_roundtrip(self, tmp_path):
        from app.gui.schematic_pp.datablock_io import (
            load_datablocks_sidecar, save_datablocks_sidecar,
        )
        from app.preprocessor.models import PpDataBlock
        sch = tmp_path / "x.sch"
        sch.write_text("dummy", encoding="utf-8")
        dbs = [
            PpDataBlock(
                component_name="R1", dx=80, dy=-30,
                lines=["a", "b"], visible=True,
            ),
            PpDataBlock(
                component_name="L1", dx=20, dy=10,
                lines=["c"], visible=False,
            ),
        ]
        save_datablocks_sidecar(str(sch), dbs)
        loaded = load_datablocks_sidecar(str(sch))
        assert len(loaded) == 2
        assert loaded[0].component_name == "R1"
        assert loaded[0].dx == 80
        assert loaded[0].lines == ["a", "b"]
        assert loaded[1].visible is False

    def test_load_nonexistent_returns_empty(self, tmp_path):
        from app.gui.schematic_pp.datablock_io import (
            load_datablocks_sidecar,
        )
        sch = tmp_path / "missing.sch"
        result = load_datablocks_sidecar(str(sch))
        assert result == []

    def test_save_empty_removes_sidecar(self, tmp_path):
        from app.gui.schematic_pp.datablock_io import (
            load_datablocks_sidecar, save_datablocks_sidecar,
            sidecar_path,
        )
        from app.preprocessor.models import PpDataBlock
        sch = tmp_path / "y.sch"
        sch.write_text("dummy", encoding="utf-8")
        # Save com 1 datablock → sidecar existe
        save_datablocks_sidecar(
            str(sch),
            [PpDataBlock(component_name="R1", lines=["x"])],
        )
        side = sidecar_path(str(sch))
        assert side.is_file()
        # Save com vazio → sidecar removido
        save_datablocks_sidecar(str(sch), [])
        assert not side.is_file()

    def test_load_corrupted_returns_empty(self, tmp_path):
        from app.gui.schematic_pp.datablock_io import (
            load_datablocks_sidecar, sidecar_path,
        )
        sch = tmp_path / "z.sch"
        sch.write_text("dummy", encoding="utf-8")
        side = sidecar_path(str(sch))
        side.write_text("not json {{ broken", encoding="utf-8")
        result = load_datablocks_sidecar(str(sch))
        assert result == []


# ---------------------------------------------------------------------------
# Editor integration
# ---------------------------------------------------------------------------


class TestEditorIntegration:

    def test_request_add_datablock_with_lines(self, qapp, monkeypatch):
        """request_add_datablock + dialog accept → AddDataBlockCommand
        empilhado."""
        from app.gui.schematic_pp.editor import PpEditor
        from app.gui.datablock_dialog import DataBlockEditDialog
        ed = PpEditor()
        # Adiciona componente host primeiro
        ed.add_component_by_type("R")
        host = ed.scene.component_items()[0]

        # Mock dialog para retornar "Accepted" + lines
        class FakeDialog:
            def __init__(self, *args, **kw): pass
            def exec(self): return QDialog.Accepted
            def lines(self): return ["mock-line-1", "mock-line-2"]

        monkeypatch.setattr(
            "app.gui.datablock_dialog.DataBlockEditDialog",
            FakeDialog,
        )
        ed._on_request_add_datablock(host)
        assert len(ed.scene.project.datablocks) == 1
        db = ed.scene.project.datablocks[0]
        assert db.lines == ["mock-line-1", "mock-line-2"]
        assert db.component_name == host.component.name

    def test_request_add_datablock_cancelled(self, qapp, monkeypatch):
        """Dialog rejeitado → nenhum datablock criado."""
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        ed.add_component_by_type("R")
        host = ed.scene.component_items()[0]

        class FakeDialog:
            def __init__(self, *args, **kw): pass
            def exec(self): return QDialog.Rejected
            def lines(self): return ["x"]

        monkeypatch.setattr(
            "app.gui.datablock_dialog.DataBlockEditDialog",
            FakeDialog,
        )
        ed._on_request_add_datablock(host)
        assert len(ed.scene.project.datablocks) == 0

    def test_request_add_datablock_empty_lines_skipped(
        self, qapp, monkeypatch,
    ):
        """Aceito mas vazio → nenhum datablock (UX prefere)."""
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        ed.add_component_by_type("R")
        host = ed.scene.component_items()[0]

        class FakeDialog:
            def __init__(self, *args, **kw): pass
            def exec(self): return QDialog.Accepted
            def lines(self): return []  # vazio

        monkeypatch.setattr(
            "app.gui.datablock_dialog.DataBlockEditDialog",
            FakeDialog,
        )
        ed._on_request_add_datablock(host)
        assert len(ed.scene.project.datablocks) == 0


# ---------------------------------------------------------------------------
# Round-trip via load_from_sch / save_to_sch
# ---------------------------------------------------------------------------


class TestEditorSchRoundtrip:

    def test_save_then_load_preserves_datablocks(self, qapp, tmp_path):
        """
        Workflow real: editor salva .sch + sidecar; carrega de
        novo (mesmo path) e datablocks aparecem ancorados.
        """
        from app.gui.schematic_pp.editor import PpEditor
        from app.preprocessor.models import PpDataBlock
        ed = PpEditor()
        ed.add_component_by_type("R")
        host = ed.scene.component_items()[0]
        original_name = host.component.name
        # Adiciona datablock manualmente (sem dialog)
        db = PpDataBlock(
            component_name=original_name,
            dx=100, dy=20,
            lines=["Test line A", "Test line B"],
        )
        ed.scene.add_datablock(db)
        # Salva
        sch = tmp_path / "rt.sch"
        ed.save_to_sch(str(sch))
        assert sch.is_file()
        # Sidecar existe
        from app.gui.schematic_pp.datablock_io import sidecar_path
        side = sidecar_path(str(sch))
        assert side.is_file()
        # Cria editor novo, carrega
        ed2 = PpEditor()
        ed2.load_from_sch(str(sch))
        assert len(ed2.scene.project.datablocks) == 1
        loaded_db = ed2.scene.project.datablocks[0]
        assert loaded_db.lines == ["Test line A", "Test line B"]
        assert loaded_db.dx == 100
        assert loaded_db.component_name == original_name
        # DataBlockItem foi criado e ancorado.
        assert len(ed2.scene.datablock_items()) == 1
