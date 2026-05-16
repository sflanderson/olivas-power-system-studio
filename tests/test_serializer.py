"""Tests for app.core.serializer — roundtrip fidelity and Phase 4 edits."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.core.diff_util import has_changes
from app.core.parser import parse_file
from app.core.project_model import (
    AtpProject,
    BranchComponent,
    SourceComponent,
    SwitchComponent,
)
from app.core.serializer import (
    _format_branch_line,
    _format_source_line,
    _format_switch_line,
    serialize_project,
)
from tests.conftest import REF_FILE


class TestRoundtrip:
    def test_no_changes_roundtrip(self, ref_project: AtpProject):
        """Serializing an unmodified project should produce no diff."""
        content = serialize_project(ref_project)
        original = "\n".join(ref_project.raw_lines)
        assert not has_changes(original, content), "Roundtrip changed the file"

    def test_roundtrip_line_count(self, ref_project: AtpProject):
        """Serialized output should have the same number of lines."""
        content = serialize_project(ref_project)
        original_lines = len(ref_project.raw_lines)
        serialized_lines = content.count("\n") + (0 if content.endswith("\n") else 1)
        # Allow small tolerance for trailing newlines
        assert abs(original_lines - serialized_lines) <= 1


class TestModification:
    def test_modify_use_data_produces_diff(self):
        """Changing a USE DATA value should produce a detectable diff."""
        project = parse_file(REF_FILE)
        original = "\n".join(project.raw_lines)

        use = project.find_use("VCB_RR")
        assert use is not None
        old_val = use.data[0].assigned_value
        use.data[0].assigned_value = "999.999"
        use.modified = True

        content = serialize_project(project)
        assert has_changes(original, content), "Modification was not detected"
        assert "999.999" in content

    def test_reparse_after_serialize(self):
        """Modified + serialized project should be re-parseable."""
        import tempfile
        from pathlib import Path

        project = parse_file(REF_FILE)
        use = project.find_use("VCB_RR")
        use.data[0].assigned_value = "42.0"
        use.modified = True

        content = serialize_project(project)
        tmp = Path(tempfile.gettempdir()) / "test_reparse.atp"
        tmp.write_text(content, encoding="utf-8")

        try:
            p2 = parse_file(str(tmp))
            assert len(p2.models) == 4
            assert len(p2.uses) == 4
            u2 = p2.find_use("VCB_RR")
            assert u2 is not None
            assert u2.data[0].assigned_value == "42.0"
        finally:
            tmp.unlink(missing_ok=True)


# ════════════════════════════════════════════════════════════════════
# Phase 4 — column-fixed formatters
# ════════════════════════════════════════════════════════════════════
class TestBranchFormatter:
    def test_branch_columns_are_fixed(self):
        b = BranchComponent(
            node1="A", node2="B", resistance="10", inductance="5", capacitance="0.1"
        )
        line = _format_branch_line(b)
        # Must be at most 44 chars (8 columns × widths 2+6+6+6+6+6+6+6)
        assert len(line) <= 44
        # Node names appear at the expected positions
        assert line[2:8].rstrip() == "A"
        assert line[8:14].rstrip() == "B"
        # R/L/C right-aligned
        assert line[26:32].strip() == "10"
        assert line[32:38].strip() == "5"
        assert line[38:44].strip() == "0.1"

    def test_branch_preserves_type_code_and_refs(self):
        b = BranchComponent(
            node1="X", node2="Y", type_code="11", ref1="REF1", ref2="REF2",
        )
        line = _format_branch_line(b)
        assert line[0:2] == "11"
        assert line[14:20].rstrip() == "REF1"
        assert line[20:26].rstrip() == "REF2"

    def test_branch_truncates_long_names(self):
        b = BranchComponent(node1="VERYLONGNODE", node2="B")
        line = _format_branch_line(b)
        # node1 field is 6 chars wide → truncated
        assert line[2:8] == "VERYLO"

    def test_branch_empty_values(self):
        b = BranchComponent(node1="A", node2="B")
        line = _format_branch_line(b)
        # Trailing blank fields are rstripped (keeps output diff-clean)
        assert line == "  A     B"
        # But node positions are preserved
        assert line[2:8].rstrip() == "A"
        assert line[8:].rstrip() == "B"


class TestSwitchFormatter:
    def test_switch_basic_columns(self):
        s = SwitchComponent(
            node1="N1", node2="N2", t_close="0.01", t_open="0.02",
        )
        line = _format_switch_line(s)
        assert line[2:8].rstrip() == "N1"
        assert line[8:14].rstrip() == "N2"
        assert line[14:24].strip() == "0.01"
        assert line[24:34].strip() == "0.02"

    def test_switch_tacs_output_appended(self):
        s = SwitchComponent(
            node1="A", node2="B", tacs_output="TACS01",
        )
        line = _format_switch_line(s)
        # switch_type field ends at col 64, tacs output follows
        assert "TACS01" in line[64:]

    def test_switch_no_tacs_output(self):
        s = SwitchComponent(node1="A", node2="B")
        line = _format_switch_line(s)
        # Line trails with no TACS
        assert "TACS" not in line


class TestSourceFormatter:
    def test_source_basic_columns(self):
        src = SourceComponent(
            node="BUS1", amplitude="1000", frequency="60", phase="0",
        )
        line = _format_source_line(src)
        assert line[2:8].rstrip() == "BUS1"
        assert line[10:20].strip() == "1000"
        assert line[20:30].strip() == "60"
        assert line[30:40].strip() == "0"

    def test_source_tstart_tstop(self):
        src = SourceComponent(
            node="N", amplitude="1", t_start="0.0", t_stop="0.5",
        )
        line = _format_source_line(src)
        assert line[60:70].strip() == "0.0"
        assert line[70:80].strip() == "0.5"


# ════════════════════════════════════════════════════════════════════
# Phase 4 — modify / delete / insert on existing project
# ════════════════════════════════════════════════════════════════════
class TestBranchEdits:
    def test_modify_branch_resistance_produces_diff(self):
        project = parse_file(REF_FILE)
        original = "\n".join(project.raw_lines)

        b = project.branches[0]
        b.resistance = "99.99"
        b.modified = True

        content = serialize_project(project)
        assert has_changes(original, content)
        assert "99.99" in content

    def test_delete_branch_removes_line(self):
        project = parse_file(REF_FILE)
        n_before = len(project.raw_lines)
        b = project.branches[0]
        b.deleted = True

        content = serialize_project(project)
        # One fewer line in output
        new_lines = content.splitlines()
        assert len(new_lines) == n_before - 1
        # Original raw_line should no longer be present
        assert b.raw_line not in new_lines

    def test_insert_new_branch_goes_before_blank(self):
        project = parse_file(REF_FILE)
        new_branch = BranchComponent(
            node1="NEWA",
            node2="NEWB",
            resistance="42",
            is_new=True,
            modified=True,
        )
        project.branches.append(new_branch)

        content = serialize_project(project)
        lines = content.splitlines()
        # The new line must appear before the first BLANK after BRANCH
        branch_section = project.sections["BRANCH"]
        # Find BLANK in output
        blank_idx = next(
            i for i, ln in enumerate(lines)
            if ln.strip().startswith("BLANK") and i > branch_section.start_line
        )
        # New branch should be somewhere in BRANCH section and before BLANK
        matching = [i for i, ln in enumerate(lines) if "NEWA" in ln and "NEWB" in ln]
        assert matching, "new branch line not found in output"
        assert matching[0] < blank_idx


class TestSwitchEdits:
    def test_modify_switch_tclose(self):
        project = parse_file(REF_FILE)
        if not project.switches:
            pytest.skip("reference file has no switches")
        s = project.switches[0]
        original = "\n".join(project.raw_lines)
        s.t_close = "0.123456"
        s.modified = True
        content = serialize_project(project)
        assert has_changes(original, content)
        assert "0.123456" in content

    def test_delete_switch(self):
        project = parse_file(REF_FILE)
        if not project.switches:
            pytest.skip("reference file has no switches")
        s = project.switches[0]
        s.deleted = True
        content = serialize_project(project)
        assert s.raw_line not in content.splitlines()

    def test_insert_new_switch(self):
        project = parse_file(REF_FILE)
        if "SWITCH" not in project.sections:
            pytest.skip("reference file has no SWITCH section")
        project.switches.append(
            SwitchComponent(
                node1="SWNEW",
                node2="GND",
                t_close="0.01",
                is_new=True,
                modified=True,
            )
        )
        content = serialize_project(project)
        assert "SWNEW" in content


class TestSourceEdits:
    def test_modify_source_amplitude(self):
        project = parse_file(REF_FILE)
        if not project.sources:
            pytest.skip("reference file has no sources")
        src = project.sources[0]
        original = "\n".join(project.raw_lines)
        src.amplitude = "555.5"
        src.modified = True
        content = serialize_project(project)
        assert has_changes(original, content)
        assert "555.5" in content

    def test_delete_source(self):
        project = parse_file(REF_FILE)
        if not project.sources:
            pytest.skip("reference file has no sources")
        src = project.sources[0]
        src.deleted = True
        content = serialize_project(project)
        assert src.raw_line not in content.splitlines()

    def test_insert_new_source(self):
        project = parse_file(REF_FILE)
        if "SOURCE" not in project.sections:
            pytest.skip("reference file has no SOURCE section")
        project.sources.append(
            SourceComponent(
                node="NEW",
                amplitude="2000",
                frequency="60",
                is_new=True,
                modified=True,
            )
        )
        content = serialize_project(project)
        assert "2000" in content


# ════════════════════════════════════════════════════════════════════
# Combined edits & roundtrip
# ════════════════════════════════════════════════════════════════════
class TestCombinedEdits:
    def test_modify_and_delete_simultaneously(self):
        project = parse_file(REF_FILE)
        # Mark one branch modified and another deleted
        project.branches[0].resistance = "777"
        project.branches[0].modified = True
        project.branches[1].deleted = True

        content = serialize_project(project)
        lines = content.splitlines()
        # 777 appears
        assert "777" in content
        # branches[1].raw_line no longer present
        assert project.branches[1].raw_line not in lines
        # total line count decreased by exactly one
        assert len(lines) == len(project.raw_lines) - 1

    def test_insert_multiple_new_branches(self):
        project = parse_file(REF_FILE)
        for i in range(3):
            project.branches.append(
                BranchComponent(
                    node1=f"N{i}",
                    node2=f"M{i}",
                    resistance="1",
                    is_new=True,
                    modified=True,
                )
            )
        content = serialize_project(project)
        for i in range(3):
            assert f"N{i}" in content
            assert f"M{i}" in content

    def test_roundtrip_after_branch_modification(self):
        project = parse_file(REF_FILE)
        project.branches[0].resistance = "88.8"
        project.branches[0].modified = True

        content = serialize_project(project)
        tmp = Path(tempfile.gettempdir()) / "test_branch_edit.atp"
        tmp.write_text(content, encoding="utf-8")
        try:
            p2 = parse_file(str(tmp))
            # First branch should now have R=88.8
            assert p2.branches[0].resistance == "88.8"
            # Node1/node2 preserved
            assert p2.branches[0].node1 == project.branches[0].node1
            assert p2.branches[0].node2 == project.branches[0].node2
        finally:
            tmp.unlink(missing_ok=True)

    def test_roundtrip_after_insert_new_branch(self):
        project = parse_file(REF_FILE)
        project.branches.append(
            BranchComponent(
                node1="ADD1",
                node2="ADD2",
                resistance="314",
                inductance="159",
                is_new=True,
                modified=True,
            )
        )
        content = serialize_project(project)
        tmp = Path(tempfile.gettempdir()) / "test_branch_insert.atp"
        tmp.write_text(content, encoding="utf-8")
        try:
            p2 = parse_file(str(tmp))
            # Find the new branch
            added = [
                b for b in p2.branches
                if b.node1 == "ADD1" and b.node2 == "ADD2"
            ]
            assert len(added) == 1
            assert added[0].resistance == "314"
            assert added[0].inductance == "159"
        finally:
            tmp.unlink(missing_ok=True)

    def test_no_edits_roundtrip_unchanged(self):
        """With no flags set, output must be byte-identical to raw."""
        project = parse_file(REF_FILE)
        content = serialize_project(project)
        original = "\n".join(project.raw_lines)
        assert content == original

    def test_edits_preserve_use_blocks(self):
        """Editing a branch must not disturb unrelated USE blocks."""
        project = parse_file(REF_FILE)
        project.branches[0].resistance = "42"
        project.branches[0].modified = True
        content = serialize_project(project)
        # All USE headers still present
        for use in project.uses:
            assert f"USE {use.model_name} AS {use.instance_name}" in content
