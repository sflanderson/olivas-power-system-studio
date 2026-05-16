"""ATP file serializer.

Rebuilds ATP file text from a parsed AtpProject, preserving the exact
bytes of anything that wasn't edited. Three kinds of edits are honored:

1. USE blocks (MODELS instances) — any ``UseInstance`` with ``modified=True``
   is fully regenerated. Works since v0.5.0.

2. BRANCH / SWITCH / SOURCE components (Phase 4, v0.20.0):
   - ``modified=True`` on an existing component → regenerate that line in
     fixed-column ATP format, replacing the original ``raw_line``.
   - ``deleted=True``                         → drop the line.
   - ``is_new=True``                          → append the formatted line
     just before the BLANK card that terminates its section.

The fixed-column formatters are symmetric with the parser at
``app/core/parser.py`` — same column widths, same truncation rules.
"""
from __future__ import annotations

import re
from typing import Optional

from app.core.project_model import (
    AtpProject,
    BranchComponent,
    InputMapping,
    OutputMapping,
    SourceComponent,
    SwitchComponent,
    UseInstance,
)


# ════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════
def serialize_project(project: AtpProject) -> str:
    """Rebuild ATP file text, applying all edits.

    Order of operations (matters — later steps must not invalidate earlier
    line indices):

      1. Apply in-place rewrites for modified/deleted existing BRANCH /
         SWITCH / SOURCE lines (at their original ``line_number``).
         Deletes are marked with ``None`` sentinels and filtered later.
      2. Append new (``is_new``) BRANCH / SWITCH / SOURCE entries before
         each section's BLANK card, processing sections bottom-up so
         earlier sections' boundaries stay valid.
      3. Filter ``None`` sentinels (the deletions).
      4. Replace modified USE blocks (bottom-up by start_line).

    Steps 1–3 only touch lines **below** /MODELS, so USE line numbers
    remain valid for step 4.
    """
    lines: list[Optional[str]] = list(project.raw_lines)

    # ── Step 1: existing BRANCH/SWITCH/SOURCE — modify / delete in place
    for b in project.branches:
        if not b.raw_line:  # purely new, no original line
            continue
        if b.deleted:
            lines[b.line_number] = None
        elif b.modified:
            lines[b.line_number] = _format_branch_line(b)

    for s in project.switches:
        if not s.raw_line:
            continue
        if s.deleted:
            lines[s.line_number] = None
        elif s.modified:
            lines[s.line_number] = _format_switch_line(s)

    for src in project.sources:
        if not src.raw_line:
            continue
        if src.deleted:
            lines[src.line_number] = None
        elif src.modified:
            lines[src.line_number] = _format_source_line(src)

    # ── Step 2: insert new components, bottom-up by section
    # Order: SOURCE → SWITCH → BRANCH (bottom to top in the file)
    for section_name, items, formatter in [
        ("SOURCE", project.sources, _format_source_line),
        ("SWITCH", project.switches, _format_switch_line),
        ("BRANCH", project.branches, _format_branch_line),
    ]:
        section = project.sections.get(section_name)
        if section is None:
            continue
        new_items = [
            i for i in items if i.is_new and not i.deleted
        ]
        if not new_items:
            continue
        insert_at = section.end_line + 1  # position of BLANK card
        new_lines = [formatter(i) for i in new_items]
        lines[insert_at:insert_at] = new_lines

    # ── Step 3: drop deletion sentinels
    lines = [ln for ln in lines if ln is not None]

    # ── Step 4: USE-block replacements (bottom-up by start_line)
    modified_uses = sorted(
        [u for u in project.uses if u.modified],
        key=lambda u: u.start_line,
        reverse=True,
    )
    for use in modified_uses:
        new_block = _serialize_use(use)
        lines[use.start_line : use.end_line + 1] = new_block

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# Column-fixed formatters for BRANCH / SWITCH / SOURCE  (Phase 4)
# ════════════════════════════════════════════════════════════════════
def _fit(value: Optional[str], width: int) -> str:
    """Return ``value`` padded/truncated to exactly ``width`` chars."""
    s = (value or "").strip()
    if len(s) >= width:
        return s[:width]
    return s.ljust(width)


def _rfit(value: Optional[str], width: int) -> str:
    """Right-align numeric value, padded/truncated to ``width`` chars."""
    s = (value or "").strip()
    if len(s) >= width:
        return s[:width]
    return s.rjust(width)


def _format_branch_line(b: BranchComponent) -> str:
    """Render a ``BranchComponent`` as a fixed-column ATP BRANCH line.

    Columns (parser-symmetric)::

        0-1   type_code   (2)
        2-7   node1       (6)   left-aligned
        8-13  node2       (6)   left-aligned
        14-19 ref1        (6)   left-aligned
        20-25 ref2        (6)   left-aligned
        26-31 R           (6)   right-aligned
        32-37 L           (6)   right-aligned
        38-43 C           (6)   right-aligned
    """
    parts = [
        _fit(b.type_code, 2),
        _fit(b.node1, 6),
        _fit(b.node2, 6),
        _fit(b.ref1, 6),
        _fit(b.ref2, 6),
        _rfit(b.resistance, 6),
        _rfit(b.inductance, 6),
        _rfit(b.capacitance, 6),
    ]
    return "".join(parts).rstrip()


def _format_switch_line(s: SwitchComponent) -> str:
    """Render a ``SwitchComponent`` as a fixed-column ATP SWITCH line.

    Columns (parser-symmetric)::

        0-1   type_code  (2)
        2-7   node1      (6)   left-aligned
        8-13  node2      (6)   left-aligned
        14-23 Tclose     (10)  right-aligned
        24-33 Topen      (10)  right-aligned
        34-43 Ie         (10)  right-aligned
        44-63 switch_type(20)  left-aligned
        64+   TACS output (6 + trailing space if present)
    """
    parts = [
        _fit(s.type_code, 2),
        _fit(s.node1, 6),
        _fit(s.node2, 6),
        _rfit(s.t_close, 10),
        _rfit(s.t_open, 10),
        _rfit(s.ie, 10),
        _fit(s.switch_type, 20),
    ]
    line = "".join(parts)
    if s.tacs_output:
        line += _fit(s.tacs_output, 6)
    return line.rstrip()


def _format_source_line(src: SourceComponent) -> str:
    """Render a ``SourceComponent`` as a fixed-column ATP SOURCE line.

    Columns (parser-symmetric)::

        0-1   type_code  (2)
        2-7   node       (6)  left-aligned
        8-9   blank      (2)
        10-19 amplitude  (10) right-aligned
        20-29 frequency  (10) right-aligned
        30-39 phase      (10) right-aligned
        40-49 A1         (10) blank (unused)
        50-59 T1         (10) blank (unused)
        60-69 Tstart     (10) right-aligned
        70-79 Tstop      (10) right-aligned
    """
    parts = [
        _fit(src.type_code, 2),
        _fit(src.node, 6),
        " " * 2,
        _rfit(src.amplitude, 10),
        _rfit(src.frequency, 10),
        _rfit(src.phase, 10),
        " " * 10,
        " " * 10,
        _rfit(src.t_start, 10),
        _rfit(src.t_stop, 10),
    ]
    return "".join(parts).rstrip()


# ════════════════════════════════════════════════════════════════════
# USE-block serialization (existing, unchanged)
# ════════════════════════════════════════════════════════════════════
def _serialize_use(use: UseInstance) -> list[str]:
    """Regenerate lines for a single USE block, preserving formatting where possible."""
    result: list[str] = []

    result.append(f"USE {use.model_name} AS {use.instance_name}")

    if use.inputs:
        result.append("INPUT")
        for inp in use.inputs:
            if inp.raw_line:
                new_line = _replace_mapping(inp.raw_line, inp.local_name, inp.mapped_to)
                result.append(new_line)
            else:
                result.append(f"  {inp.local_name}:= {inp.mapped_to}")

    if use.data:
        result.append("DATA")
        for param in use.data:
            value = param.assigned_value or param.default_value or "0"
            if param.raw_line:
                new_line = _replace_data_value(param.raw_line, param.name, value)
                result.append(new_line)
            else:
                result.append(f"  {param.name}:= {value}")

    if use.outputs:
        result.append("OUTPUT")
        for out in use.outputs:
            if out.raw_line:
                new_line = _replace_output_mapping(out.raw_line, out.global_name, out.local_name)
                result.append(new_line)
            else:
                result.append(f"  {out.global_name}:={out.local_name}")

    result.append("ENDUSE")
    return result


def _replace_data_value(raw_line: str, param_name: str, new_value: str) -> str:
    """Replace the value after := in a DATA line, preserving prefix formatting."""
    pattern = re.compile(
        r"(\s*" + re.escape(param_name) + r":=\s*)(.*)",
        re.IGNORECASE,
    )
    match = pattern.match(raw_line)
    if match:
        prefix = match.group(1)
        return f"{prefix}{new_value}"
    return f"  {param_name}:= {new_value}"


def _replace_mapping(raw_line: str, local_name: str, mapped_to: str) -> str:
    """Replace an INPUT mapping line, preserving prefix formatting."""
    pattern = re.compile(r"(\s*)(\S+):=\s*(\S+)")
    match = pattern.match(raw_line)
    if match:
        indent = match.group(1)
        return f"{indent}{local_name}:= {mapped_to}"
    return f"  {local_name}:= {mapped_to}"


def _replace_output_mapping(raw_line: str, global_name: str, local_name: str) -> str:
    """Replace an OUTPUT mapping line, preserving prefix formatting."""
    pattern = re.compile(r"(\s*)(\S+):=\s*(\S+)")
    match = pattern.match(raw_line)
    if match:
        indent = match.group(1)
        return f"{indent}{global_name}:={local_name}"
    return f"  {global_name}:={local_name}"
