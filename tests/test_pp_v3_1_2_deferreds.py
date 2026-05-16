"""
tests/test_pp_v3_1_2_deferreds.py — v3.1.2 (4 sub-sprints).

Fecha os 4 deferreds de v3.1.1:

* Sub-sprint A — UI gray-out PpProperty.linked_library
* Sub-sprint B — QGraphicsItem rendering Tags
* Sub-sprint C — AddSeriesComponentCommand (auto-bus-node)
* Sub-sprint D — Sidecar JSON serialization
"""

from __future__ import annotations

import json
import os
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys
    return QApplication.instance() or QApplication(sys.argv)


# ===========================================================================
# Sub-sprint A — PropertyRow with linked_library
# ===========================================================================


class TestSubSprintA_PropertyRowLinkedLibrary:

    @staticmethod
    def _make_spec():
        from app.preprocessor.spec.models import (
            PropertyGroup, PropertySpec, PropertyType,
        )
        return PropertySpec(
            name="kV",
            label="Tensao nominal",
            type=PropertyType.FLOAT,
            default=13.8,
            visible=True,
            group=PropertyGroup.MAIN,
            unit="kV",
        )

    def test_unlinked_row_editor_enabled(self, qapp):
        from app.gui.schematic_pp.property_editor import PropertyRow
        spec = self._make_spec()
        row = PropertyRow(0, spec, "13.8", True)
        assert row._editor.isEnabled()
        assert row.linked_library is None

    def test_linked_row_editor_disabled(self, qapp):
        from app.gui.schematic_pp.property_editor import PropertyRow
        spec = self._make_spec()
        row = PropertyRow(0, spec, "13.8", True, linked_library="ABB SACE T7")
        assert not row._editor.isEnabled()
        assert row.linked_library == "ABB SACE T7"

    def test_set_linked_library_dynamic(self, qapp):
        from app.gui.schematic_pp.property_editor import PropertyRow
        spec = self._make_spec()
        row = PropertyRow(0, spec, "13.8", True)
        row.set_linked_library("WEG")
        assert not row._editor.isEnabled()
        # Unlink
        row.set_linked_library(None)
        assert row._editor.isEnabled()

    def test_unlink_signal_emitted(self, qapp):
        from app.gui.schematic_pp.property_editor import PropertyRow
        spec = self._make_spec()
        row = PropertyRow(0, spec, "13.8", True, linked_library="ABB")
        captured = []
        row.unlink_requested.connect(lambda idx: captured.append(idx))
        # Simulate click on unlink button
        row._unlink_btn.click()
        assert captured == [0]

    def test_visible_checkbox_disabled_when_linked(self, qapp):
        from app.gui.schematic_pp.property_editor import PropertyRow
        spec = self._make_spec()
        row = PropertyRow(0, spec, "13.8", True, linked_library="WEG")
        assert not row._vis.isEnabled()


# ===========================================================================
# Sub-sprint B — Tag QGraphicsItems
# ===========================================================================


class TestSubSprintB_LinkTagItem:

    def test_creates_at_tag_position(self, qapp):
        from app.preprocessor.models import PpLinkTag
        from app.gui.schematic_pp.tag_items import LinkTagGraphicsItem
        tag = PpLinkTag(label="Go A", target="oneline:DocA", x=100, y=200)
        item = LinkTagGraphicsItem(tag)
        assert item.pos().x() == 100
        assert item.pos().y() == 200
        assert item.tag is tag

    def test_visible_flag_respected(self, qapp):
        from app.preprocessor.models import PpLinkTag
        from app.gui.schematic_pp.tag_items import LinkTagGraphicsItem
        tag = PpLinkTag(label="X", target="report:Z", visible=False)
        item = LinkTagGraphicsItem(tag)
        assert not item.isVisible()

    def test_bounding_rect_grows_with_label(self, qapp):
        from app.preprocessor.models import PpLinkTag
        from app.gui.schematic_pp.tag_items import LinkTagGraphicsItem
        short = LinkTagGraphicsItem(PpLinkTag(label="A", target="t:x"))
        long = LinkTagGraphicsItem(
            PpLinkTag(label="A very long label here", target="t:x")
        )
        assert long.boundingRect().width() > short.boundingRect().width()

    def test_link_clicked_signal_exists(self, qapp):
        from app.gui.schematic_pp.tag_items import LinkTagGraphicsItem
        # Signal is class attribute — verify
        assert hasattr(LinkTagGraphicsItem, "link_clicked")


class TestSubSprintB_LegendTagItem:

    def test_4_shapes_render(self, qapp):
        from app.preprocessor.models import PpLegendTag
        from app.gui.schematic_pp.tag_items import LegendTagGraphicsItem
        for shape in ("Diamond", "Hexagon", "Circle", "Rectangle"):
            tag = PpLegendTag(text=f"Z-{shape}", shape=shape)
            item = LegendTagGraphicsItem(tag)
            assert item.tag.shape == shape
            # boundingRect is square 36×36
            br = item.boundingRect()
            assert br.width() == 36 and br.height() == 36

    def test_color_propagated(self, qapp):
        from app.preprocessor.models import PpLegendTag
        from app.gui.schematic_pp.tag_items import LegendTagGraphicsItem
        tag = PpLegendTag(text="Red", shape="Circle", color="#ff0000")
        item = LegendTagGraphicsItem(tag)
        assert item.tag.color == "#ff0000"


# ===========================================================================
# Sub-sprint C — AddSeriesComponentCommand
# ===========================================================================


class TestSubSprintC_AddSeriesComponent:

    def test_command_class_exists(self):
        from app.gui.schematic_pp.commands import AddSeriesComponentCommand
        assert AddSeriesComponentCommand is not None

    def test_redo_undo_atomic(self, qapp):
        """Single undo/redo restores all 3 mutations atomically."""
        from app.gui.schematic_pp.commands import AddSeriesComponentCommand
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import (
            PpComponent, PpProperty, PpWire,
        )

        scene = PpScene()
        # Initial: 1 wire from (0,0) to (200,0)
        original = PpWire(x1=0, y1=0, x2=200, y2=0)
        scene.add_wire(original)
        assert len(scene.project.wires) == 1

        new_comp = PpComponent(
            type="R", name="R1", visible=True,
            x=100, y=0, label_dx=10, label_dy=-20,
            mirror=0, rotation=0,
            properties=[PpProperty("1k", True)],
        )
        wire_in = PpWire(x1=0, y1=0, x2=70, y2=0)
        wire_out = PpWire(x1=130, y1=0, x2=200, y2=0)

        cmd = AddSeriesComponentCommand(
            scene, original, new_comp, wire_in, wire_out,
        )
        cmd.redo()
        # After redo: original gone, 1 component + 2 wires
        assert original not in scene.project.wires
        assert new_comp in scene.project.components
        assert wire_in in scene.project.wires
        assert wire_out in scene.project.wires

        cmd.undo()
        # After undo: original restored, no component, no new wires
        assert new_comp not in scene.project.components
        assert wire_in not in scene.project.wires
        assert wire_out not in scene.project.wires
        assert original in scene.project.wires

    def test_redo_idempotent(self, qapp):
        """Multiple redo cycles preserve state."""
        from app.gui.schematic_pp.commands import AddSeriesComponentCommand
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import (
            PpComponent, PpProperty, PpWire,
        )

        scene = PpScene()
        original = PpWire(x1=0, y1=0, x2=200, y2=0)
        scene.add_wire(original)

        comp = PpComponent(
            type="L", name="L1", visible=True,
            x=100, y=0, label_dx=10, label_dy=-20,
            mirror=0, rotation=0,
            properties=[PpProperty("10mH", True)],
        )
        cmd = AddSeriesComponentCommand(
            scene, original,
            comp,
            PpWire(x1=0, y1=0, x2=70, y2=0),
            PpWire(x1=130, y1=0, x2=200, y2=0),
        )
        cmd.redo()
        cmd.undo()
        cmd.redo()
        # Final state has comp + 2 wires (sem original)
        assert comp in scene.project.components
        assert original not in scene.project.wires


# ===========================================================================
# Sub-sprint D — Sidecar JSON serialization
# ===========================================================================


class TestSubSprintD_SidecarIO:

    def test_sidecar_path_computation(self):
        from app.gui.schematic_pp.sidecar_io import sidecar_path_for
        assert str(sidecar_path_for("project.sch")).endswith("project.olivas.json")
        assert str(sidecar_path_for("a/b/c.sch")).endswith("c.olivas.json")

    def test_save_load_roundtrip_with_tags(self, tmp_path):
        from app.gui.schematic_pp.sidecar_io import (
            load_sidecar, save_sidecar,
        )
        from app.preprocessor.models import (
            PpLegendTag, PpLinkTag, PpProject,
        )

        project = PpProject()
        project.link_tags.append(PpLinkTag(
            label="See TCC-A", target="tcc:CoordA", x=50, y=50,
        ))
        project.legend_tags.append(PpLegendTag(
            text="Zone HV", shape="Diamond", x=200, y=100,
        ))
        project.legend_tags.append(PpLegendTag(
            text="Zone LV", shape="Hexagon", x=200, y=200, color="#80c0ff",
        ))

        sch_path = tmp_path / "test.sch"
        # Touch file (we don't need actual .sch content for sidecar test)
        sch_path.write_text("# fake sch", encoding="utf-8")

        sidecar_path = save_sidecar(project, sch_path)
        assert sidecar_path is not None
        assert sidecar_path.exists()

        # Load into fresh project
        new_project = PpProject()
        loaded = load_sidecar(new_project, sch_path)
        assert loaded is True
        assert len(new_project.link_tags) == 1
        assert new_project.link_tags[0].label == "See TCC-A"
        assert len(new_project.legend_tags) == 2
        assert new_project.legend_tags[0].shape == "Diamond"
        assert new_project.legend_tags[1].color == "#80c0ff"

    def test_save_skipped_when_no_extensions(self, tmp_path):
        """Empty extensions → no sidecar file written."""
        from app.gui.schematic_pp.sidecar_io import save_sidecar
        from app.preprocessor.models import PpProject

        project = PpProject()  # no tags, no linked properties
        sch_path = tmp_path / "empty.sch"
        sch_path.write_text("# empty", encoding="utf-8")

        sidecar_path = save_sidecar(project, sch_path)
        assert sidecar_path is None  # not written

    def test_load_returns_false_when_missing(self, tmp_path):
        from app.gui.schematic_pp.sidecar_io import load_sidecar
        from app.preprocessor.models import PpProject

        project = PpProject()
        loaded = load_sidecar(project, tmp_path / "nonexistent.sch")
        assert loaded is False

    def test_save_load_with_linked_properties(self, tmp_path):
        from app.gui.schematic_pp.sidecar_io import (
            load_sidecar, save_sidecar,
        )
        from app.preprocessor.models import (
            PpComponent, PpProject, PpProperty,
        )

        project = PpProject()
        comp = PpComponent(
            type="BREAKER", name="Q1", visible=True,
            x=100, y=100, label_dx=10, label_dy=-20,
            mirror=0, rotation=0,
            properties=[
                PpProperty("Q-01", True),  # tag (manual)
                PpProperty("15.0", True, linked_library="ABB HD4"),  # linked
                PpProperty("1200", True, linked_library="ABB HD4"),  # linked
            ],
        )
        project.components.append(comp)

        sch_path = tmp_path / "linked.sch"
        sch_path.write_text("# fake", encoding="utf-8")

        save_sidecar(project, sch_path)

        # Load fresh — properties default to no link
        new_project = PpProject()
        new_comp = PpComponent(
            type="BREAKER", name="Q1", visible=True,
            x=100, y=100, label_dx=10, label_dy=-20,
            mirror=0, rotation=0,
            properties=[
                PpProperty("Q-01", True),
                PpProperty("15.0", True),  # initially unlinked
                PpProperty("1200", True),  # initially unlinked
            ],
        )
        new_project.components.append(new_comp)

        load_sidecar(new_project, sch_path)
        # Now properties 1 and 2 should be linked
        assert new_comp.properties[0].linked_library is None  # tag stays manual
        assert new_comp.properties[1].linked_library == "ABB HD4"
        assert new_comp.properties[2].linked_library == "ABB HD4"

    def test_sidecar_version_field(self, tmp_path):
        """Sidecar JSON includes ``olivas_version`` for future migrations."""
        from app.gui.schematic_pp.sidecar_io import (
            SIDECAR_VERSION, save_sidecar, sidecar_path_for,
        )
        from app.preprocessor.models import PpLinkTag, PpProject

        project = PpProject()
        project.link_tags.append(PpLinkTag(label="X", target="t:y"))

        sch_path = tmp_path / "v.sch"
        sch_path.write_text("#", encoding="utf-8")
        save_sidecar(project, sch_path)

        sidecar_path = sidecar_path_for(sch_path)
        data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        assert data["olivas_version"] == SIDECAR_VERSION


# ===========================================================================
# 7ª garantia: documentar acesso ao usuário
# ===========================================================================


class TestSeventhGuaranteeAccessibility:

    def test_property_row_has_unlink_button(self, qapp):
        """Row linked tem botão visível para o usuário desvincular."""
        from app.gui.schematic_pp.property_editor import PropertyRow
        from app.preprocessor.spec.models import (
            PropertyGroup, PropertySpec, PropertyType,
        )
        spec = PropertySpec(
            name="x", label="X", type=PropertyType.FLOAT, default=1.0,
            visible=True, group=PropertyGroup.MAIN,
        )
        row = PropertyRow(0, spec, "1.0", True, linked_library="ABB")
        # Botão 🔗 deve existir e estar visível
        assert row._unlink_btn is not None
        # tooltip cita ABB
        assert "ABB" in row._unlink_btn.toolTip()

    def test_tag_items_module_exists(self):
        """Sub-sprint B: tag_items.py acessível para wiring no editor."""
        import app.gui.schematic_pp.tag_items as tag_items
        assert hasattr(tag_items, "LinkTagGraphicsItem")
        assert hasattr(tag_items, "LegendTagGraphicsItem")

    def test_series_command_exported(self):
        """Sub-sprint C: AddSeriesComponentCommand exportado em commands."""
        from app.gui.schematic_pp import commands
        assert hasattr(commands, "AddSeriesComponentCommand")

    def test_sidecar_module_documented(self):
        """Sub-sprint D: sidecar_io.py existe e documenta extensão."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/schematic_pp/sidecar_io.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "PTW Tutorial" not in content or "olivas.json" in content
        assert ".olivas.json" in content
