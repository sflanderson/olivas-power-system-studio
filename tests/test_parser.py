"""Tests for app.core.parser — the heart of Olivas ATP Studio."""
from __future__ import annotations

from collections import Counter

from app.core.project_model import AtpProject


class TestHeader:
    def test_delta_t(self, ref_project: AtpProject):
        assert ref_project.header.delta_t == 1e-6

    def test_t_max(self, ref_project: AtpProject):
        assert ref_project.header.t_max == 0.045

    def test_frequency(self, ref_project: AtpProject):
        assert ref_project.header.frequency == 60.0


class TestModels:
    def test_model_count(self, ref_project: AtpProject):
        assert len(ref_project.models) == 4

    def test_model_names(self, ref_project: AtpProject):
        names = {m.name for m in ref_project.models}
        assert names == {"VCB_Rr", "VCB_Rs", "VCB_Rt", "SNUB_CTRL"}

    def test_vcb_model_structure(self, ref_project: AtpProject):
        m = ref_project.find_model("VCB_Rr")
        assert m is not None
        assert len(m.inputs) == 3
        assert len(m.outputs) == 5
        assert len(m.data) == 14
        assert len(m.variables) == 17

    def test_snub_ctrl_structure(self, ref_project: AtpProject):
        m = ref_project.find_model("SNUB_CTRL")
        assert m is not None
        assert len(m.inputs) == 3
        assert len(m.outputs) == 6
        assert len(m.data) == 0
        assert len(m.variables) == 7

    def test_model_has_exec_code(self, ref_project: AtpProject):
        for m in ref_project.models:
            assert m.exec_code, f"MODEL {m.name} has no EXEC code"

    def test_model_data_params_have_names(self, ref_project: AtpProject):
        m = ref_project.find_model("VCB_Rr")
        for d in m.data:
            assert d.name.strip(), f"DATA param has empty name"

    def test_find_model_case_insensitive(self, ref_project: AtpProject):
        assert ref_project.find_model("vcb_rr") is not None
        assert ref_project.find_model("VCB_RR") is not None
        assert ref_project.find_model("NONEXISTENT") is None


class TestUses:
    def test_use_count(self, ref_project: AtpProject):
        assert len(ref_project.uses) == 4

    def test_use_names(self, ref_project: AtpProject):
        names = {u.model_name for u in ref_project.uses}
        assert names == {"VCB_RR", "VCB_RS", "VCB_RT", "SNUB_CTRL"}

    def test_vcb_use_structure(self, ref_project: AtpProject):
        u = ref_project.find_use("VCB_RR")
        assert u is not None
        assert len(u.inputs) == 3
        assert len(u.outputs) == 5
        assert len(u.data) == 14

    def test_snub_ctrl_use_structure(self, ref_project: AtpProject):
        u = ref_project.find_use("SNUB_CTRL")
        assert u is not None
        assert len(u.inputs) == 3
        assert len(u.outputs) == 6
        assert len(u.data) == 0

    def test_use_data_has_values(self, ref_project: AtpProject):
        u = ref_project.find_use("VCB_RR")
        for d in u.data:
            val = d.assigned_value or d.default_value
            assert val is not None, f"DATA {d.name} has no value"

    def test_find_use_case_insensitive(self, ref_project: AtpProject):
        assert ref_project.find_use("vcb_rr") is not None
        assert ref_project.find_use("VCB_RR") is not None


class TestBranches:
    def test_branch_count(self, ref_project: AtpProject):
        # 40 branches after fixing the phantom-continuation-line bug
        # (v0.20.1). Previously the parser saw 98, but 58 of those were
        # numeric continuation lines from coupled-line and transformer
        # impedance matrices — not real branches.
        assert len(ref_project.branches) == 40

    def test_semantic_types(self, ref_project: AtpProject):
        types = Counter(b.semantic_type for b in ref_project.branches)
        # Counts after parser fix (v0.20.1)
        assert types["resistor"] == 12
        assert types["RL"] == 6
        assert types["line"] == 6
        assert types["RLC"] == 4
        assert types["capacitor"] == 4
        assert types["branch"] == 3
        assert types["RC"] == 3
        assert types["LC"] == 2

    def test_no_phantom_numeric_branches(self, ref_project: AtpProject):
        """Regression: ATP numeric continuation lines must not parse as branches."""
        from app.core.parser import _looks_like_node_name
        for b in ref_project.branches:
            assert _looks_like_node_name(b.node1) or _looks_like_node_name(b.node2), (
                f"Phantom branch with numeric-only names: {b.node1!r} / {b.node2!r} "
                f"at line {b.line_number + 1}"
            )

    def test_all_branches_have_at_least_one_node(self, ref_project: AtpProject):
        for b in ref_project.branches:
            has_node = b.node1.strip() or b.node2.strip()
            assert has_node, f"Branch at line {b.line_number} has no nodes at all"

    def test_branches_have_semantic_type(self, ref_project: AtpProject):
        for b in ref_project.branches:
            assert b.semantic_type, f"Branch {b.node1}-{b.node2} has no semantic_type"


class TestSwitches:
    def test_switch_count(self, ref_project: AtpProject):
        assert len(ref_project.switches) == 15

    def test_semantic_types(self, ref_project: AtpProject):
        types = Counter(s.semantic_type for s in ref_project.switches)
        assert types["tacs_controlled"] == 9
        assert types["measuring"] == 6

    def test_all_switches_have_nodes(self, ref_project: AtpProject):
        for s in ref_project.switches:
            assert s.node1.strip(), f"Switch at line {s.line_number} has empty node1"


class TestSources:
    def test_source_count(self, ref_project: AtpProject):
        assert len(ref_project.sources) == 3

    def test_all_ac(self, ref_project: AtpProject):
        for s in ref_project.sources:
            assert s.semantic_type == "ac"

    def test_sources_have_node(self, ref_project: AtpProject):
        for s in ref_project.sources:
            assert s.node.strip()


class TestNodes:
    def test_node_count(self, ref_project: AtpProject):
        assert len(ref_project.nodes) == 34

    def test_nodes_have_sources(self, ref_project: AtpProject):
        for name, node in ref_project.nodes.items():
            assert node.sources, f"Node {name} has no source info"


class TestSections:
    def test_sections_present(self, ref_project: AtpProject):
        assert "BRANCH" in ref_project.sections
        assert "SWITCH" in ref_project.sections
        assert "SOURCE" in ref_project.sections
        assert "OUTPUT" in ref_project.sections

    def test_sections_have_lines(self, ref_project: AtpProject):
        for name, section in ref_project.sections.items():
            assert section.raw_lines, f"Section {name} has no raw_lines"


class TestRawLines:
    def test_raw_lines_not_empty(self, ref_project: AtpProject):
        assert len(ref_project.raw_lines) == 867


class TestLooksLikeNodeName:
    """Unit tests for the _looks_like_node_name heuristic (v0.20.1)."""

    def test_empty_rejected(self):
        from app.core.parser import _looks_like_node_name
        assert _looks_like_node_name("") is False

    def test_normal_name_accepted(self):
        from app.core.parser import _looks_like_node_name
        assert _looks_like_node_name("X0030A") is True
        assert _looks_like_node_name("BUS1") is True
        assert _looks_like_node_name("NEUTRA") is True

    def test_pure_digits_rejected(self):
        from app.core.parser import _looks_like_node_name
        assert _looks_like_node_name("12345") is False
        assert _looks_like_node_name("5.213") is False
        assert _looks_like_node_name("660109") is False

    def test_scientific_notation_rejected(self):
        from app.core.parser import _looks_like_node_name
        assert _looks_like_node_name("1.48E+03") is False
        assert _looks_like_node_name("-3.58E-05") is False
        assert _looks_like_node_name("4.18749E") is False

    def test_all_letters_accepted(self):
        from app.core.parser import _looks_like_node_name
        # Even "EEE" — pure letters, no digits, so not scientific notation
        assert _looks_like_node_name("EEE") is True
        assert _looks_like_node_name("GND") is True

    def test_mixed_with_non_e_letter_accepted(self):
        from app.core.parser import _looks_like_node_name
        assert _looks_like_node_name("E1A") is True  # has A (non-E)
        assert _looks_like_node_name("1XB") is True  # has X, B
