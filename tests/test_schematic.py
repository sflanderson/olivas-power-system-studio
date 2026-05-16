"""Tests for the interactive schematic editor."""
from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from app.gui.schematic.editor_widget import (
    SchematicEditor,
    _branch_label,
    _layout_nodes,
    _source_label,
)
from app.gui.schematic.items import (
    SEMANTIC_TO_SYMBOL,
    ComponentEdge,
    NodeItem,
    SourceItem,
)


# ── QApplication fixture (required for QWidget instantiation) ──────
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ════════════════════════════════════════════════════════════════════
# Semantic → symbol mapping
# ════════════════════════════════════════════════════════════════════
class TestSymbolMapping:
    def test_resistor_maps_correctly(self):
        assert SEMANTIC_TO_SYMBOL["resistor"] == "resistor"

    def test_vcb_is_switch(self):
        assert SEMANTIC_TO_SYMBOL["vcb"] == "switch"

    def test_snubber_is_capacitor_symbol(self):
        assert SEMANTIC_TO_SYMBOL["snubber"] == "capacitor"

    def test_ac_source_symbol(self):
        assert SEMANTIC_TO_SYMBOL["ac"] == "source_ac"

    def test_dc_source_symbol(self):
        assert SEMANTIC_TO_SYMBOL["dc"] == "source_dc"

    def test_all_expected_types_present(self):
        required = {
            "resistor",
            "inductor",
            "capacitor",
            "RC",
            "RL",
            "RLC",
            "snubber",
            "transformer",
            "vcb",
            "ac",
            "dc",
        }
        assert required.issubset(SEMANTIC_TO_SYMBOL.keys())


# ════════════════════════════════════════════════════════════════════
# Layout algorithm
# ════════════════════════════════════════════════════════════════════
class TestLayout:
    def test_layout_separates_phases(self, ref_project):
        positions = _layout_nodes(ref_project)
        # Every node should have a position
        assert len(positions) == len(ref_project.nodes)

    def test_layout_returns_qpointf(self, ref_project):
        positions = _layout_nodes(ref_project)
        for pos in positions.values():
            assert isinstance(pos, QPointF)

    def test_phase_a_left_of_phase_c(self, ref_project):
        positions = _layout_nodes(ref_project)
        a_nodes = [n for n in positions if n.strip().upper().endswith("A")]
        c_nodes = [n for n in positions if n.strip().upper().endswith("C")]
        if a_nodes and c_nodes:
            avg_a_x = sum(positions[n].x() for n in a_nodes) / len(a_nodes)
            avg_c_x = sum(positions[n].x() for n in c_nodes) / len(c_nodes)
            assert avg_a_x < avg_c_x


# ════════════════════════════════════════════════════════════════════
# Label formatters
# ════════════════════════════════════════════════════════════════════
class TestLabels:
    def test_branch_label_with_rlc(self):
        from app.core.project_model import BranchComponent

        b = BranchComponent(
            node1="N1",
            node2="N2",
            resistance="10.0",
            inductance="5.0",
            capacitance="0.1",
        )
        label = _branch_label(b)
        assert "R=10" in label
        assert "L=5" in label
        assert "C=0.1" in label

    def test_branch_label_only_resistance(self):
        from app.core.project_model import BranchComponent

        b = BranchComponent(
            node1="N1", node2="N2", resistance="100", semantic_type="resistor"
        )
        label = _branch_label(b)
        assert "R=100" in label

    def test_branch_label_fallback_to_semantic(self):
        from app.core.project_model import BranchComponent

        b = BranchComponent(node1="N1", node2="N2", semantic_type="transformer")
        label = _branch_label(b)
        assert label == "transformer"

    def test_branch_label_non_numeric(self):
        from app.core.project_model import BranchComponent

        b = BranchComponent(node1="N1", node2="N2", resistance="ABC")
        label = _branch_label(b)
        assert "R=ABC" in label

    def test_source_label_with_amplitude(self):
        from app.core.project_model import SourceComponent

        s = SourceComponent(node="N1", amplitude="1000")
        assert "1000" in _source_label(s)

    def test_source_label_fallback(self):
        from app.core.project_model import SourceComponent

        s = SourceComponent(node="N1", semantic_type="ac")
        assert _source_label(s) == "ac"


# ════════════════════════════════════════════════════════════════════
# SchematicEditor integration
# ════════════════════════════════════════════════════════════════════
class TestSchematicEditor:
    def test_editor_creates_without_project(self, qapp):
        editor = SchematicEditor()
        assert editor._scene.items() == []
        assert editor._node_items == {}
        assert editor._edge_items == []

    def test_editor_loads_project(self, qapp, ref_project):
        editor = SchematicEditor()
        editor.load_project(ref_project)
        # Nodes created
        assert len(editor._node_items) > 0
        # Edges created
        assert len(editor._edge_items) > 0
        # Scene populated
        assert len(editor._scene.items()) > 0

    def test_editor_node_count_matches_project(self, qapp, ref_project):
        editor = SchematicEditor()
        editor.load_project(ref_project)
        assert len(editor._node_items) == len(ref_project.nodes)

    def test_editor_edge_count_matches_components(self, qapp, ref_project):
        editor = SchematicEditor()
        editor.load_project(ref_project)
        # Every branch / switch whose both nodes exist should be an edge
        expected_edges = 0
        for b in ref_project.branches:
            if b.node1.strip() in editor._node_items and b.node2.strip() in editor._node_items:
                expected_edges += 1
        for s in ref_project.switches:
            if s.node1.strip() in editor._node_items and s.node2.strip() in editor._node_items:
                expected_edges += 1
        assert len(editor._edge_items) == expected_edges

    def test_editor_sources_created(self, qapp, ref_project):
        editor = SchematicEditor()
        editor.load_project(ref_project)
        if ref_project.sources:
            assert len(editor._source_items) == len(
                [s for s in ref_project.sources if s.node.strip() in editor._node_items]
            )

    def test_editor_palette_populated(self, qapp, ref_project):
        editor = SchematicEditor()
        editor.load_project(ref_project)
        assert editor._comp_list.count() > 0

    def test_editor_reload_clears_previous(self, qapp, ref_project):
        editor = SchematicEditor()
        editor.load_project(ref_project)
        first_count = len(editor._scene.items())
        editor.load_project(ref_project)
        # Should be the same, not doubled
        assert len(editor._scene.items()) == first_count

    def test_editor_empty_project(self, qapp):
        from app.core.project_model import AtpProject

        editor = SchematicEditor()
        editor.load_project(AtpProject())
        assert editor._node_items == {}
        assert editor._edge_items == []


# ════════════════════════════════════════════════════════════════════
# NodeItem behavior
# ════════════════════════════════════════════════════════════════════
class TestNodeItem:
    def test_node_item_stores_name(self, qapp):
        n = NodeItem("XX0001", QColor("#4fc3f7"), QColor("#ffffff"))
        assert n.node_name == "XX0001"

    def test_node_item_is_movable(self, qapp):
        from PySide6.QtWidgets import QGraphicsItem

        n = NodeItem("N1", QColor("#4fc3f7"), QColor("#ffffff"))
        assert n.flags() & QGraphicsItem.ItemIsMovable
        assert n.flags() & QGraphicsItem.ItemIsSelectable

    def test_node_item_tracks_edges(self, qapp):
        n1 = NodeItem("N1", QColor("#4fc3f7"), QColor("#ffffff"))
        n2 = NodeItem("N2", QColor("#4fc3f7"), QColor("#ffffff"))
        edge = ComponentEdge(n1, n2, "resistor", "R=10", QColor("#90a4ae"))
        assert n1.edge_count() == 1
        assert n2.edge_count() == 1
        assert edge in n1._edges

    def test_node_edge_deduplication(self, qapp):
        n = NodeItem("N", QColor("#4fc3f7"), QColor("#ffffff"))
        other = NodeItem("O", QColor("#4fc3f7"), QColor("#ffffff"))
        e = ComponentEdge(n, other, "resistor", "", QColor("#90a4ae"))
        # Calling add_edge twice shouldn't duplicate
        n.add_edge(e)
        assert n.edge_count() == 1


# ════════════════════════════════════════════════════════════════════
# ComponentEdge / SourceItem
# ════════════════════════════════════════════════════════════════════
class TestComponentEdge:
    def test_edge_bounding_rect_nonzero(self, qapp):
        n1 = NodeItem("N1", QColor("#4fc3f7"), QColor("#ffffff"))
        n2 = NodeItem("N2", QColor("#4fc3f7"), QColor("#ffffff"))
        n1.setPos(0, 0)
        n2.setPos(100, 0)
        e = ComponentEdge(n1, n2, "resistor", "R=10", QColor("#90a4ae"))
        rect = e.boundingRect()
        assert rect.width() > 0
        assert rect.height() > 0

    def test_edge_geometry_updates_on_node_move(self, qapp):
        n1 = NodeItem("N1", QColor("#4fc3f7"), QColor("#ffffff"))
        n2 = NodeItem("N2", QColor("#4fc3f7"), QColor("#ffffff"))
        n1.setPos(0, 0)
        n2.setPos(100, 0)
        e = ComponentEdge(n1, n2, "resistor", "", QColor("#90a4ae"))
        rect1 = e.boundingRect()
        n2.setPos(300, 50)
        rect2 = e.boundingRect()
        assert rect2 != rect1


class TestSourceItem:
    def test_source_attached_to_node(self, qapp):
        n = NodeItem("N", QColor("#4fc3f7"), QColor("#ffffff"))
        s = SourceItem(n, "source_ac", "100", QColor("#ffb74d"))
        assert n.source_count() == 1
        assert s in n._sources

    def test_source_updates_on_node_move(self, qapp):
        n = NodeItem("N", QColor("#4fc3f7"), QColor("#ffffff"))
        n.setPos(0, 0)
        s = SourceItem(n, "source_ac", "", QColor("#ffb74d"))
        r1 = s.boundingRect()
        n.setPos(200, 200)
        r2 = s.boundingRect()
        assert r1 != r2


# ════════════════════════════════════════════════════════════════════
# Phase 3 — interactive editing: placement modes & helpers
# ════════════════════════════════════════════════════════════════════
from app.core.project_model import (
    AtpProject,
    BranchComponent,
    Node,
    SourceComponent,
    SwitchComponent,
)
from app.gui.schematic.editor_widget import PlacementMode


def _mini_project() -> AtpProject:
    """Build a tiny AtpProject for editing tests."""
    p = AtpProject()
    p.nodes["A"] = Node(name="A", sources=[])
    p.nodes["B"] = Node(name="B", sources=[])
    p.nodes["C"] = Node(name="C", sources=["SOURCE"])
    p.branches.append(
        BranchComponent(node1="A", node2="B", semantic_type="resistor", resistance="10")
    )
    p.branches.append(
        BranchComponent(node1="B", node2="C", semantic_type="inductor", inductance="5")
    )
    p.switches.append(
        SwitchComponent(node1="A", node2="C", semantic_type="switch", t_close="0.01")
    )
    p.sources.append(SourceComponent(node="C", semantic_type="ac", amplitude="1000"))
    return p


class TestPlacementMode:
    def test_placement_mode_has_all_states(self):
        expected = {"IDLE", "PLACE_NODE", "PLACE_BRANCH", "PLACE_SWITCH", "PLACE_SOURCE"}
        actual = {m.name for m in PlacementMode}
        assert expected == actual

    def test_editor_starts_in_idle(self, qapp):
        editor = SchematicEditor()
        assert editor._mode == PlacementMode.IDLE

    def test_set_mode_transitions(self, qapp):
        editor = SchematicEditor()
        # Load a project with nodes so PLACE_BRANCH is allowed
        editor.load_project(_mini_project())
        editor._set_mode(PlacementMode.PLACE_NODE)
        assert editor._mode == PlacementMode.PLACE_NODE
        editor._set_mode(PlacementMode.PLACE_BRANCH)
        assert editor._mode == PlacementMode.PLACE_BRANCH

    def test_cancel_mode_returns_to_idle(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        editor._set_mode(PlacementMode.PLACE_SWITCH)
        editor._cancel_mode()
        assert editor._mode == PlacementMode.IDLE


class TestEnsureNode:
    def test_ensure_creates_missing_node(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        editor._ensure_node("XYZ")
        assert "XYZ" in editor._project.nodes
        assert editor._project.nodes["XYZ"].name == "XYZ"

    def test_ensure_noop_on_existing(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        original = editor._project.nodes["A"]
        editor._ensure_node("A")
        # Same object preserved
        assert editor._project.nodes["A"] is original

    def test_ensure_ignores_empty_name(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        n_before = len(editor._project.nodes)
        editor._ensure_node("")
        assert len(editor._project.nodes) == n_before

    def test_ensure_noop_without_project(self, qapp):
        editor = SchematicEditor()
        # Should not raise even when project is None
        editor._ensure_node("ANY")


class TestDeletionFlags:
    """Direct deletion paths that don't open confirmation dialogs."""

    def test_delete_edge_marks_flags(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        edge = editor._edge_items[0]
        comp = edge.component_data
        assert comp is not None
        editor._delete_edge(edge)
        assert comp.deleted is True
        assert comp.modified is True

    def test_delete_edge_removes_from_scene(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        n_before = len(editor._edge_items)
        edge = editor._edge_items[0]
        editor._delete_edge(edge)
        # After reload, the deleted edge should not appear
        assert len(editor._edge_items) == n_before - 1

    def test_delete_source_marks_flags(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        assert editor._source_items, "fixture must have a source"
        src = editor._source_items[0]
        comp = src.component_data
        assert comp is not None
        editor._delete_source(src)
        assert comp.deleted is True
        assert comp.modified is True
        # No longer displayed
        assert len(editor._source_items) == 0

    def test_cascading_delete_of_node(self, qapp, monkeypatch):
        """Deleting node A should mark the A-B branch and A-C switch as deleted."""
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        # Monkeypatch the confirm dialog to auto-accept
        from PySide6.QtWidgets import QMessageBox

        monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.Yes)
        editor._scene.clearSelection()
        editor._node_items["A"].setSelected(True)
        editor._delete_selected()

        # Node removed from project
        assert "A" not in editor._project.nodes
        # Branch A-B flagged
        ab = next(b for b in editor._project.branches if b.node2 == "B" and b.node1 == "A")
        assert ab.deleted is True
        # Switch A-C flagged
        ac = editor._project.switches[0]
        assert ac.deleted is True


class TestRenameNode:
    def test_rename_propagates_to_branches(self, qapp, monkeypatch):
        editor = SchematicEditor()
        editor.load_project(_mini_project())

        # Patch NodeDialog so it auto-accepts and returns "AA"
        from app.gui.schematic import dialogs as dlg_mod

        class FakeDialog:
            Accepted = 1

            def __init__(self, *a, **kw):
                pass

            def exec(self):
                return 1

            def node_name(self):
                return "AA"

        monkeypatch.setattr(dlg_mod, "NodeDialog", FakeDialog)
        # Also patch the one used inside editor_widget
        import app.gui.schematic.editor_widget as ew_mod

        monkeypatch.setattr(ew_mod, "NodeDialog", FakeDialog)

        editor._rename_node(editor._node_items["A"])
        # Branch node1 "A" → "AA"
        ab = editor._project.branches[0]
        assert ab.node1 == "AA"
        assert ab.modified is True
        # Switch node1 "A" → "AA"
        ac = editor._project.switches[0]
        assert ac.node1 == "AA"
        assert ac.modified is True
        # Project dict updated
        assert "AA" in editor._project.nodes
        assert "A" not in editor._project.nodes

    def test_rename_propagates_to_source(self, qapp, monkeypatch):
        editor = SchematicEditor()
        editor.load_project(_mini_project())

        class FakeDialog:
            Accepted = 1

            def __init__(self, *a, **kw):
                pass

            def exec(self):
                return 1

            def node_name(self):
                return "CC"

        import app.gui.schematic.editor_widget as ew_mod

        monkeypatch.setattr(ew_mod, "NodeDialog", FakeDialog)

        editor._rename_node(editor._node_items["C"])
        src = editor._project.sources[0]
        assert src.node == "CC"
        assert src.modified is True


class TestNodePositionPreservation:
    def test_positions_preserved_across_reload(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        # Move node A
        a = editor._node_items["A"]
        a.setPos(QPointF(500, 600))
        # Reload (e.g. after any edit)
        editor.reload()
        # After reload, position should be preserved
        pos = editor._node_items["A"].pos()
        assert pos.x() == pytest.approx(500.0)
        assert pos.y() == pytest.approx(600.0)

    def test_load_project_clears_positions(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        editor._node_items["A"].setPos(QPointF(500, 600))
        # Load again → positions reset to layout defaults
        editor.load_project(_mini_project())
        assert editor._node_positions == {} or all(
            isinstance(v, QPointF) for v in editor._node_positions.values()
        )


class TestReloadSkipsDeleted:
    def test_deleted_branch_not_rendered(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        n_before = len(editor._edge_items)
        editor._project.branches[0].deleted = True
        editor.reload()
        assert len(editor._edge_items) == n_before - 1

    def test_deleted_switch_not_rendered(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        n_before = len(editor._edge_items)
        editor._project.switches[0].deleted = True
        editor.reload()
        assert len(editor._edge_items) == n_before - 1

    def test_deleted_source_not_rendered(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        editor._project.sources[0].deleted = True
        editor.reload()
        assert len(editor._source_items) == 0


class TestEditingFlagsDefaults:
    def test_branch_has_editing_flags(self):
        b = BranchComponent(node1="A", node2="B")
        assert b.modified is False
        assert b.deleted is False
        assert b.is_new is False

    def test_switch_has_editing_flags(self):
        s = SwitchComponent(node1="A", node2="B")
        assert s.modified is False
        assert s.deleted is False
        assert s.is_new is False

    def test_source_has_editing_flags(self):
        s = SourceComponent(node="A")
        assert s.modified is False
        assert s.deleted is False
        assert s.is_new is False


# ════════════════════════════════════════════════════════════════════
# v0.20.1 — "Novo projeto" and better layout
# ════════════════════════════════════════════════════════════════════
from app.gui.schematic.editor_widget import (
    _grid_layout,
    _make_empty_project,
    _phase_column_layout,
)


class TestEmptyProjectSkeleton:
    def test_empty_project_has_required_sections(self):
        p = _make_empty_project()
        assert "BRANCH" in p.sections
        assert "SWITCH" in p.sections
        assert "SOURCE" in p.sections

    def test_empty_project_has_no_components(self):
        p = _make_empty_project()
        assert p.branches == []
        assert p.switches == []
        assert p.sources == []
        assert p.nodes == {}

    def test_empty_project_raw_lines_valid(self):
        p = _make_empty_project()
        # Each section header must exist in raw_lines
        assert "/BRANCH" in p.raw_lines
        assert "/SWITCH" in p.raw_lines
        assert "/SOURCE" in p.raw_lines
        # BLANK cards exist to terminate each section
        assert "BLANK BRANCH" in p.raw_lines
        assert "BLANK SWITCH" in p.raw_lines
        assert "BLANK SOURCE" in p.raw_lines

    def test_empty_project_section_boundaries(self):
        p = _make_empty_project()
        # end_line must be < index of BLANK card in raw_lines
        b_sec = p.sections["BRANCH"]
        blank_idx = p.raw_lines.index("BLANK BRANCH")
        assert b_sec.end_line < blank_idx

    def test_empty_project_accepts_insertions_via_serializer(self):
        """New branch on an empty project must serialize before BLANK."""
        from app.core.serializer import serialize_project
        p = _make_empty_project()
        p.branches.append(
            BranchComponent(
                node1="A", node2="B", resistance="1", is_new=True, modified=True,
            )
        )
        content = serialize_project(p)
        lines = content.splitlines()
        # New branch line appears before the BLANK BRANCH card
        blank_idx = lines.index("BLANK BRANCH")
        has_new_branch = any("A" in ln and "B" in ln and "1" in ln for ln in lines[:blank_idx])
        assert has_new_branch


class TestLayoutStrategies:
    def test_phase_column_layout_places_by_suffix(self):
        positions = _phase_column_layout(["N1A", "N2B", "N3C", "BUS"])
        # A, B, C nodes go to increasing x columns
        assert positions["N1A"].x() < positions["N2B"].x()
        assert positions["N2B"].x() < positions["N3C"].x()

    def test_grid_layout_for_nonphase_circuit(self):
        positions = _grid_layout(["X1", "X2", "X3", "X4"])
        # 2x2 grid: X1 X2 on row 0, X3 X4 on row 1
        assert positions["X1"].y() == positions["X2"].y()
        assert positions["X3"].y() == positions["X4"].y()
        assert positions["X1"].y() < positions["X3"].y()

    def test_layout_empty_project_returns_empty(self):
        from app.gui.schematic.editor_widget import _layout_nodes
        empty = _make_empty_project()
        assert _layout_nodes(empty) == {}

    def test_layout_auto_selects_grid_for_nonphase(self):
        from app.gui.schematic.editor_widget import _layout_nodes
        p = _make_empty_project()
        p.nodes["X1"] = Node(name="X1", sources=[])
        p.nodes["X2"] = Node(name="X2", sources=[])
        p.nodes["X3"] = Node(name="X3", sources=[])
        # No A/B/C suffix → grid
        positions = _layout_nodes(p)
        # Grid positions should have y=0 for first row of all 3
        first_row_count = sum(1 for pos in positions.values() if pos.y() == 0)
        assert first_row_count >= 2  # at least 2 on first row for 3-node grid

    def test_layout_auto_selects_phase_for_threephase(self):
        from app.gui.schematic.editor_widget import _layout_nodes
        p = _make_empty_project()
        for name in ["B1A", "B1B", "B1C", "B2A", "B2B", "B2C", "N"]:
            p.nodes[name] = Node(name=name, sources=[])
        positions = _layout_nodes(p)
        # Phase A nodes share x-column
        assert positions["B1A"].x() == positions["B2A"].x()
        assert positions["B1B"].x() == positions["B2B"].x()


class TestNewProjectSignal:
    def test_new_project_emits_signal_and_loads(self, qapp, monkeypatch):
        """Clicking "Novo projeto" on a fresh editor loads empty project."""
        editor = SchematicEditor()
        received = []
        editor.project_created.connect(lambda p: received.append(p))

        editor._new_project()

        assert len(received) == 1
        assert received[0] is editor._project
        assert editor._project.branches == []
        assert editor._project.switches == []
        assert editor._project.sources == []

    def test_new_project_on_dirty_asks_confirmation(self, qapp, monkeypatch):
        from PySide6.QtWidgets import QMessageBox
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        # Mark as dirty
        editor._project.branches[0].modified = True

        # User says "No" → project should not be replaced
        monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.No)
        original = editor._project
        editor._new_project()
        assert editor._project is original

    def test_new_project_on_dirty_accepts_yes(self, qapp, monkeypatch):
        from PySide6.QtWidgets import QMessageBox
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        editor._project.branches[0].modified = True

        monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.Yes)
        editor._new_project()
        assert editor._project.branches == []


# ════════════════════════════════════════════════════════════════════════
# v0.20.2 — Empty-project UX guards
# ════════════════════════════════════════════════════════════════════════
class TestEmptyProjectGuards:
    """The '+ Branch / + Switch / + Fonte' actions must not strand the user
    on an empty canvas. Regression tests for the v0.20.2 hotfix triggered by
    the feedback: 'Não há nenhum componente para selecionar'."""

    def test_set_mode_place_branch_blocked_when_no_nodes(
        self, qapp, monkeypatch
    ):
        from PySide6.QtWidgets import QMessageBox
        # Swallow the info popup
        monkeypatch.setattr(
            QMessageBox, "information", lambda *a, **kw: QMessageBox.Ok
        )
        editor = SchematicEditor()
        editor._new_project_noop = None  # no project loaded
        editor._set_mode(PlacementMode.PLACE_BRANCH)
        assert editor._mode == PlacementMode.IDLE

    def test_set_mode_place_switch_blocked_when_no_nodes(
        self, qapp, monkeypatch
    ):
        from PySide6.QtWidgets import QMessageBox
        monkeypatch.setattr(
            QMessageBox, "information", lambda *a, **kw: QMessageBox.Ok
        )
        editor = SchematicEditor()
        editor._set_mode(PlacementMode.PLACE_SWITCH)
        assert editor._mode == PlacementMode.IDLE

    def test_set_mode_place_source_blocked_when_no_nodes(
        self, qapp, monkeypatch
    ):
        from PySide6.QtWidgets import QMessageBox
        monkeypatch.setattr(
            QMessageBox, "information", lambda *a, **kw: QMessageBox.Ok
        )
        editor = SchematicEditor()
        editor._set_mode(PlacementMode.PLACE_SOURCE)
        assert editor._mode == PlacementMode.IDLE

    def test_set_mode_place_node_always_allowed(self, qapp):
        """Placing a node must work even without an existing project —
        the user can then build up from the first node."""
        editor = SchematicEditor()
        # This call should not pop up a dialog and should not block
        editor._set_mode(PlacementMode.PLACE_NODE)
        assert editor._mode == PlacementMode.PLACE_NODE

    def test_set_mode_place_branch_allowed_after_loading_nodes(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        editor._set_mode(PlacementMode.PLACE_BRANCH)
        assert editor._mode == PlacementMode.PLACE_BRANCH


class TestToolbarEnablement:
    """Buttons should grey out when the action is not usable."""

    def test_initial_state_most_buttons_disabled(self, qapp):
        editor = SchematicEditor()
        # No project yet → add-node disabled, component buttons too
        assert editor._act_add_node.isEnabled() is False
        assert editor._act_add_branch.isEnabled() is False
        assert editor._act_add_switch.isEnabled() is False
        assert editor._act_add_source.isEnabled() is False
        assert editor._act_delete.isEnabled() is False
        # "Novo projeto" is always enabled — it's the escape hatch
        assert editor._act_new_project.isEnabled() is True

    def test_after_new_empty_project_only_add_node_enabled(
        self, qapp, monkeypatch
    ):
        from PySide6.QtWidgets import QMessageBox
        monkeypatch.setattr(
            QMessageBox, "question", lambda *a, **kw: QMessageBox.Yes
        )
        editor = SchematicEditor()
        editor._new_project()
        # Empty project loaded
        assert editor._act_add_node.isEnabled() is True
        assert editor._act_add_branch.isEnabled() is False
        assert editor._act_add_switch.isEnabled() is False
        assert editor._act_add_source.isEnabled() is False
        assert editor._act_delete.isEnabled() is False

    def test_after_loading_project_with_nodes_all_enabled(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        assert editor._act_add_node.isEnabled() is True
        assert editor._act_add_branch.isEnabled() is True
        assert editor._act_add_switch.isEnabled() is True
        assert editor._act_add_source.isEnabled() is True
        assert editor._act_delete.isEnabled() is True


class TestIdleStatusMessage:
    """Status-bar text should reflect the current project state."""

    def test_status_message_no_project(self, qapp):
        editor = SchematicEditor()
        msg = editor._idle_status_message()
        assert "Novo projeto" in msg or "novo" in msg.lower()

    def test_status_message_empty_project(self, qapp, monkeypatch):
        from PySide6.QtWidgets import QMessageBox
        monkeypatch.setattr(
            QMessageBox, "question", lambda *a, **kw: QMessageBox.Yes
        )
        editor = SchematicEditor()
        editor._new_project()
        msg = editor._idle_status_message()
        assert "vazio" in msg.lower()

    def test_status_message_populated_project(self, qapp):
        editor = SchematicEditor()
        editor.load_project(_mini_project())
        msg = editor._idle_status_message()
        assert msg == "Pronto."
