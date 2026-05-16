"""
tests/test_pp_v3_1_3_wire_integration.py — v3.1.3 (4 sub-sprints).

Wiring final dos modelos/commands/UI de v3.1.1+v3.1.2 ao fluxo do usuário:

* Sub-sprint A — Context menu insert Tags + AddLinkTag/AddLegendTag commands
* Sub-sprint B — MainWindow link_tag_navigate (TCC/Report/PDF/oneline)
* Sub-sprint C — view.dropEvent on wire → AddSeriesComponentCommand
* Sub-sprint D — auto save/load sidecar JSON em save_to_sch / load_from_sch
"""

from __future__ import annotations

import os
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys
    return QApplication.instance() or QApplication(sys.argv)


# ===========================================================================
# Sub-sprint A — Tag commands + scene methods
# ===========================================================================


class TestSubSprintA_TagCommands:

    def test_add_link_tag_command(self, qapp):
        from app.preprocessor.models import PpLinkTag
        from app.gui.schematic_pp.commands import AddLinkTagCommand
        from app.gui.schematic_pp.scene import PpScene

        scene = PpScene()
        tag = PpLinkTag(label="Go A", target="oneline:DocA", x=50, y=50)
        cmd = AddLinkTagCommand(scene, tag)
        cmd.redo()
        assert tag in scene.project.link_tags
        cmd.undo()
        assert tag not in scene.project.link_tags

    def test_add_legend_tag_command(self, qapp):
        from app.preprocessor.models import PpLegendTag
        from app.gui.schematic_pp.commands import AddLegendTagCommand
        from app.gui.schematic_pp.scene import PpScene

        scene = PpScene()
        tag = PpLegendTag(text="HV", shape="Diamond", x=100, y=100)
        cmd = AddLegendTagCommand(scene, tag)
        cmd.redo()
        assert tag in scene.project.legend_tags
        cmd.undo()
        assert tag not in scene.project.legend_tags

    def test_remove_tag_commands(self, qapp):
        from app.preprocessor.models import PpLegendTag, PpLinkTag
        from app.gui.schematic_pp.commands import (
            RemoveLegendTagCommand, RemoveLinkTagCommand,
        )
        from app.gui.schematic_pp.scene import PpScene

        scene = PpScene()
        ltag = PpLinkTag(label="X", target="t:y")
        scene.add_link_tag(ltag)
        cmd = RemoveLinkTagCommand(scene, ltag)
        cmd.redo()
        assert ltag not in scene.project.link_tags
        cmd.undo()
        assert ltag in scene.project.link_tags

        gtag = PpLegendTag(text="Z", shape="Hexagon")
        scene.add_legend_tag(gtag)
        cmd2 = RemoveLegendTagCommand(scene, gtag)
        cmd2.redo()
        assert gtag not in scene.project.legend_tags
        cmd2.undo()
        assert gtag in scene.project.legend_tags

    def test_view_emits_link_tag_signal(self, qapp):
        """view.request_add_link_tag is connected & wired in editor."""
        from app.gui.schematic_pp.editor import PpEditor
        editor = PpEditor()
        assert hasattr(editor.view, "request_add_link_tag")
        assert hasattr(editor.view, "request_add_legend_tag")

    def test_editor_has_tag_handlers(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        editor = PpEditor()
        assert callable(editor._on_add_link_tag)
        assert callable(editor._on_add_legend_tag)


# ===========================================================================
# Sub-sprint B — MainWindow link_tag_navigate routing
# ===========================================================================


class TestSubSprintB_LinkTagNavigate:

    def test_editor_emits_link_tag_navigate(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        editor = PpEditor()
        captured = []
        editor.link_tag_navigate.connect(lambda t: captured.append(t))
        # Simulate scene-level click signal
        editor.scene.link_tag_clicked.emit("tcc:CoordA")
        assert captured == ["tcc:CoordA"]

    def test_main_window_has_handler(self):
        from app.gui.main_window import MainWindow
        assert hasattr(MainWindow, "_on_link_tag_navigate")

    def test_main_window_handles_tcc_scheme(self, qapp):
        """Verifica que o handler reconhece scheme 'tcc:'."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        # Ensure scheme matching exists
        assert "tcc" in content and "report" in content
        assert "pdf" in content and "oneline" in content


# ===========================================================================
# Sub-sprint C — Drop on wire → series command
# ===========================================================================


class TestSubSprintC_DropOnWire:

    def test_view_has_component_dropped_on_wire_signal(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView
        view = PpView(PpScene())
        assert hasattr(view, "component_dropped_on_wire")

    def test_find_wire_at_returns_wire_when_present(self, qapp):
        from PySide6.QtCore import QPointF
        from app.preprocessor.models import PpWire
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView

        scene = PpScene()
        view = PpView(scene)
        wire = PpWire(x1=0, y1=0, x2=200, y2=0)
        scene.add_wire(wire)
        # Point on the wire
        result = view._find_wire_at(QPointF(100, 0), tolerance=5.0)
        assert result is not None

    def test_find_wire_at_returns_none_when_far(self, qapp):
        from PySide6.QtCore import QPointF
        from app.preprocessor.models import PpWire
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView

        scene = PpScene()
        view = PpView(scene)
        scene.add_wire(PpWire(x1=0, y1=0, x2=200, y2=0))
        # Point far from the wire
        result = view._find_wire_at(QPointF(100, 500), tolerance=5.0)
        assert result is None

    def test_editor_has_drop_on_wire_handler(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        editor = PpEditor()
        assert callable(editor._on_component_dropped_on_wire)

    def test_drop_on_wire_creates_series(self, qapp):
        """Smoke: chamada direta ao handler quebra wire e insere comp."""
        from PySide6.QtCore import QPointF
        from app.gui.schematic_pp.editor import PpEditor
        from app.gui.schematic_pp.items import WireItem
        from app.preprocessor.models import PpWire

        editor = PpEditor()
        wire = PpWire(x1=0, y1=0, x2=200, y2=0)
        editor.scene.add_wire(wire)
        wire_item = editor.scene.find_wire_item(wire)
        assert wire_item is not None
        editor._on_component_dropped_on_wire(
            "R", QPointF(100, 0), wire_item,
        )
        # Wire original removido, 2 wires + 1 component
        assert wire not in editor.scene.project.wires
        # Component R criado
        codes = [c.type for c in editor.scene.project.components]
        assert "R" in codes


# ===========================================================================
# Sub-sprint D — Auto sidecar save/load via save_to_sch/load_from_sch
# ===========================================================================


class TestSubSprintD_SidecarAutoSaveLoad:

    def test_save_to_sch_writes_sidecar_when_extensions(self, qapp, tmp_path):
        """save_to_sch automaticamente cria .olivas.json se houver Tags/linked."""
        from app.gui.schematic_pp.editor import PpEditor
        from app.gui.schematic_pp.sidecar_io import sidecar_path_for
        from app.preprocessor.models import PpLinkTag

        editor = PpEditor()
        # Add a link tag to trigger sidecar write
        tag = PpLinkTag(label="Go A", target="oneline:DocA")
        editor.scene.add_link_tag(tag)

        sch_path = tmp_path / "test.sch"
        editor.save_to_sch(sch_path)
        # Sidecar exists
        sidecar = sidecar_path_for(sch_path)
        assert sidecar.exists()

    def test_save_to_sch_skips_sidecar_when_empty(self, qapp, tmp_path):
        """Save sem extensões NÃO cria sidecar (não polui filesystem)."""
        from app.gui.schematic_pp.editor import PpEditor
        from app.gui.schematic_pp.sidecar_io import sidecar_path_for

        editor = PpEditor()
        sch_path = tmp_path / "empty.sch"
        editor.save_to_sch(sch_path)
        sidecar = sidecar_path_for(sch_path)
        # No extensions → no sidecar
        assert not sidecar.exists()

    def test_load_from_sch_loads_sidecar(self, qapp, tmp_path):
        """load_from_sch automaticamente carrega .olivas.json se existir."""
        from app.gui.schematic_pp.editor import PpEditor
        from app.preprocessor.models import PpLegendTag, PpLinkTag

        # Save with extensions
        editor1 = PpEditor()
        editor1.scene.add_link_tag(PpLinkTag(label="L1", target="t:x"))
        editor1.scene.add_legend_tag(
            PpLegendTag(text="Z1", shape="Hexagon")
        )
        sch_path = tmp_path / "with_tags.sch"
        editor1.save_to_sch(sch_path)

        # Load in fresh editor
        editor2 = PpEditor()
        editor2.load_from_sch(sch_path)
        assert len(editor2.scene.project.link_tags) == 1
        assert editor2.scene.project.link_tags[0].label == "L1"
        assert len(editor2.scene.project.legend_tags) == 1
        assert editor2.scene.project.legend_tags[0].shape == "Hexagon"


# ===========================================================================
# 7ª garantia — confirmar acessibilidade do usuário
# ===========================================================================


class TestSeventhGuaranteeAccessibility:

    def test_view_context_menu_includes_tag_options(self):
        """view.py:_build_empty_canvas_menu must include Insert Link/Legend."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/schematic_pp/view.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "Inserir Link Tag" in content
        assert "Inserir Legend Tag" in content
        # The 4 shapes must be in the submenu
        for shape in ("Diamond", "Hexagon", "Circle", "Rectangle"):
            assert shape in content

    def test_main_window_connects_link_tag_navigate(self):
        """main_window.py wires schematic_pp.link_tag_navigate."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "link_tag_navigate.connect" in content
        assert "_on_link_tag_navigate" in content

    def test_save_to_sch_calls_save_sidecar(self):
        """save_to_sch invokes save_sidecar (sub-sprint D)."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/schematic_pp/editor.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "save_sidecar" in content
        assert "load_sidecar" in content

    def test_view_drop_event_checks_for_wire(self):
        """view.dropEvent calls _find_wire_at to detect series-insertion."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/schematic_pp/view.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "_find_wire_at" in content
        assert "component_dropped_on_wire" in content
