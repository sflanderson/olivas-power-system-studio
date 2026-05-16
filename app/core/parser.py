from __future__ import annotations

import re
from pathlib import Path

from app.core.project_model import (
    AtpProject,
    BranchComponent,
    DataParam,
    HeaderInfo,
    InputMapping,
    ModelDefinition,
    ModelsGlobalIO,
    Node,
    OutputMapping,
    Section,
    SourceComponent,
    SwitchComponent,
    UseInstance,
)


def _read_atp_text(path: Path) -> str:
    """
    Lê arquivo .atp tentando múltiplas codificações em ordem.

    v0.28.2-PRO + followup: corrige bug auditoria P0.

    Estratégia (refinada após code-review):

    1. Tenta UTF-8 (modernos, exportados por ATP studio).
    2. Tenta CP1252 antes de Latin-1, porque CP1252 RAISES em
       bytes 0x81/0x8D/0x8F/0x90/0x9D (slots indefinidos),
       enquanto Latin-1 aceita TUDO sem raise — então se
       latin-1 vier antes, nunca caímos para CP1252 mesmo
       quando os bytes são realmente CP1252.
    3. Tenta Latin-1 como último de "strict" (sempre sucede).
    4. Fallback: UTF-8 com errors="replace" (impossível chegar
       aqui, mas defensivo).

    A primeira codificação que decodificar SEM erro é usada.
    """
    raw_bytes = path.read_bytes()
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    # Defensivo (latin-1 nunca raise; este branch é inalcançável)
    return raw_bytes.decode("utf-8", errors="replace")


def parse_file(filepath: str) -> AtpProject:
    path = Path(filepath)
    # v0.28.2-PRO: encoding fallback (auditoria P0)
    raw_text = _read_atp_text(path)
    lines = raw_text.splitlines()

    project = AtpProject(file_path=str(path), raw_lines=list(lines))

    section_indices = _find_section_boundaries(lines)

    models_start = section_indices.get("MODELS")
    branch_start = section_indices.get("BRANCH")
    switch_start = section_indices.get("SWITCH")
    source_start = section_indices.get("SOURCE")
    output_start = section_indices.get("OUTPUT")

    # --- header: everything before /MODELS ---
    header_end = models_start if models_start is not None else len(lines)
    _parse_header(project, lines, 0, header_end)

    # --- MODELS section ---
    if models_start is not None:
        models_end = branch_start or switch_start or source_start or output_start or len(lines)
        _parse_models_section(project, lines, models_start, models_end)

    # --- BRANCH, SWITCH, SOURCE, OUTPUT ---
    ordered = ["BRANCH", "SWITCH", "SOURCE", "OUTPUT"]
    for i, name in enumerate(ordered):
        start = section_indices.get(name)
        if start is None:
            continue
        end = len(lines)
        for next_name in ordered[i + 1 :]:
            if next_name in section_indices:
                end = section_indices[next_name]
                break
        # trim BLANK cards
        actual_end = end
        for k in range(start + 1, end):
            if lines[k].strip().startswith("BLANK "):
                actual_end = k
                break
        section = Section(
            name=name,
            raw_lines=lines[start:actual_end],
            start_line=start,
            end_line=actual_end - 1,
        )
        project.sections[name] = section

    # --- tail lines (BLANK cards + final) ---
    # v0.28.2-PRO (auditoria P0): a versão anterior pegava o
    # PRIMEIRO BLANK encontrado, o que sobrepunha incorretamente
    # com seções subsequentes (ex: BLANK BRANCH terminando /BRANCH
    # vs BLANK final do arquivo). Agora pegamos o tail correto:
    # tudo APÓS o end_line da última seção parseada.
    if project.sections:
        last_section_end = max(
            sec.end_line for sec in project.sections.values()
        )
        # tail começa logo após a última seção (incluindo seu BLANK)
        tail_start = last_section_end + 1
        # Skip a BLANK card que pertence à última seção
        if (
            tail_start < len(lines)
            and lines[tail_start].strip().startswith("BLANK ")
        ):
            tail_start += 1
    else:
        # Sem seções estruturadas — usa heurística antiga
        tail_start = len(lines)
        for i, line in enumerate(lines):
            if line.strip().startswith("BLANK "):
                tail_start = i
                break
    project.tail_lines = lines[tail_start:]

    # --- parse components from sections ---
    if "BRANCH" in project.sections:
        _parse_branch_components(project, project.sections["BRANCH"])
    if "SWITCH" in project.sections:
        _parse_switch_components(project, project.sections["SWITCH"])
    if "SOURCE" in project.sections:
        _parse_source_components(project, project.sections["SOURCE"])

    # --- semantic classification [CORE-010] ---
    _classify_components(project)

    # --- extract nodes ---
    _extract_nodes(project)

    return project


def _find_section_boundaries(lines: list[str]) -> dict[str, int]:
    indices: dict[str, int] = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "/MODELS":
            indices.setdefault("MODELS", i)
        elif stripped == "/BRANCH":
            indices.setdefault("BRANCH", i)
        elif stripped == "/SWITCH":
            indices.setdefault("SWITCH", i)
        elif stripped == "/SOURCE":
            indices.setdefault("SOURCE", i)
        elif stripped == "/OUTPUT":
            indices.setdefault("OUTPUT", i)
    return indices


def _parse_header(project: AtpProject, lines: list[str], start: int, end: int) -> None:
    header = HeaderInfo(raw_lines=lines[start:end])

    freq_found = False
    for i in range(start, end):
        line = lines[i]

        if "POWER FREQUENCY" in line.upper():
            match = re.search(r"[\d.Ee+-]+", line.split("FREQUENCY")[-1], re.IGNORECASE)
            if match:
                try:
                    header.frequency = float(match.group())
                except ValueError:
                    pass
            freq_found = True
            continue

        if freq_found and not line.startswith("C") and not line.startswith("$"):
            stripped = line.strip()
            if stripped and not stripped.startswith("C"):
                parts = stripped.split()
                if len(parts) >= 1:
                    try:
                        header.delta_t = float(parts[0])
                    except ValueError:
                        pass
                if len(parts) >= 2:
                    try:
                        header.t_max = float(parts[1])
                    except ValueError:
                        pass
                freq_found = False

    project.header = header


def _parse_models_section(
    project: AtpProject, lines: list[str], start: int, end: int
) -> None:
    # Find MODELS keyword and ENDMODELS
    models_kw = None
    endmodels = None
    for i in range(start, end):
        stripped = lines[i].strip()
        if stripped == "MODELS" and models_kw is None:
            models_kw = i
        if stripped == "ENDMODELS":
            endmodels = i
            break

    if models_kw is None:
        project.warnings.append("Keyword MODELS not found inside /MODELS section")
        return

    if endmodels is None:
        endmodels = end
        project.warnings.append("ENDMODELS not found; assuming section end")

    # Parse global INPUT/OUTPUT and MODEL/USE blocks
    i = models_kw + 1
    global_io = ModelsGlobalIO()

    # Global INPUT block
    if i < endmodels and lines[i].strip() == "INPUT":
        global_io.raw_lines.append(lines[i])
        i += 1
        while i < endmodels:
            stripped = lines[i].strip()
            if stripped in ("OUTPUT", "") or stripped.startswith("MODEL ") or stripped.startswith("USE "):
                if stripped == "":
                    i += 1
                    continue
                break
            match = re.match(r"\s+(\S+)\s+\{(.+)\}", lines[i])
            if match:
                global_io.inputs.append(
                    InputMapping(
                        local_name=match.group(1),
                        mapped_to=match.group(2),
                        raw_line=lines[i],
                    )
                )
            global_io.raw_lines.append(lines[i])
            i += 1

    # Global OUTPUT block
    if i < endmodels and lines[i].strip() == "OUTPUT":
        global_io.raw_lines.append(lines[i])
        i += 1
        while i < endmodels:
            stripped = lines[i].strip()
            if stripped.startswith("MODEL ") or stripped.startswith("USE "):
                break
            if stripped:
                global_io.outputs.append(stripped)
            global_io.raw_lines.append(lines[i])
            i += 1

    project.models_global_io = global_io

    # Parse MODEL and USE blocks
    while i < endmodels:
        stripped = lines[i].strip()
        if stripped.startswith("MODEL "):
            model, i = _parse_model_block(lines, i, endmodels)
            project.models.append(model)
        elif stripped.startswith("USE "):
            use, i = _parse_use_block(lines, i, endmodels)
            project.uses.append(use)
        else:
            i += 1


def _parse_model_block(
    lines: list[str], start: int, limit: int
) -> tuple[ModelDefinition, int]:
    header_line = lines[start].strip()
    name = header_line.split()[1] if len(header_line.split()) > 1 else "UNKNOWN"

    model = ModelDefinition(name=name, start_line=start)
    raw_lines: list[str] = [lines[start]]

    i = start + 1
    current_section = None

    while i < limit:
        stripped = lines[i].strip()
        raw_lines.append(lines[i])

        if stripped == "ENDMODEL":
            model.end_line = i
            model.raw_text = "\n".join(raw_lines)
            return model, i + 1

        if stripped == "COMMENT":
            current_section = "COMMENT"
            comment_lines: list[str] = []
            i += 1
            while i < limit and lines[i].strip() != "ENDCOMMENT":
                comment_lines.append(lines[i])
                raw_lines.append(lines[i])
                i += 1
            raw_lines.append(lines[i])  # ENDCOMMENT
            model.comment = "\n".join(comment_lines)
            i += 1
            continue

        if stripped == "INPUT" and current_section != "EXEC":
            current_section = "INPUT"
            i += 1
            continue

        if stripped == "OUTPUT" and current_section != "EXEC":
            current_section = "OUTPUT"
            i += 1
            continue

        if stripped == "DATA":
            current_section = "DATA"
            i += 1
            continue

        if stripped == "VAR":
            current_section = "VAR"
            i += 1
            continue

        if stripped == "INIT":
            current_section = "INIT"
            init_lines: list[str] = []
            i += 1
            while i < limit and lines[i].strip() != "ENDINIT":
                init_lines.append(lines[i])
                raw_lines.append(lines[i])
                i += 1
            raw_lines.append(lines[i])  # ENDINIT
            model.init_code = "\n".join(init_lines)
            current_section = None
            i += 1
            continue

        if stripped == "EXEC":
            current_section = "EXEC"
            exec_lines: list[str] = []
            i += 1
            while i < limit and lines[i].strip() != "ENDEXEC":
                exec_lines.append(lines[i])
                raw_lines.append(lines[i])
                i += 1
            raw_lines.append(lines[i])  # ENDEXEC
            model.exec_code = "\n".join(exec_lines)
            current_section = None
            i += 1
            continue

        # Parse content of current section
        if current_section == "INPUT" and stripped:
            model.inputs.append(stripped)
        elif current_section == "OUTPUT" and stripped:
            model.outputs.append(stripped)
        elif current_section == "DATA" and stripped:
            match = re.match(r"\s*(\S+)\s+\{DFLT:(.+)\}", lines[i])
            if match:
                model.data.append(
                    DataParam(
                        name=match.group(1),
                        default_value=match.group(2),
                        raw_line=lines[i],
                    )
                )
        elif current_section == "VAR" and stripped:
            model.variables.append(stripped)

        i += 1

    # If we reach here, ENDMODEL was not found
    model.end_line = i - 1
    model.raw_text = "\n".join(raw_lines)
    return model, i


def _parse_use_block(
    lines: list[str], start: int, limit: int
) -> tuple[UseInstance, int]:
    header_line = lines[start].strip()
    parts = header_line.split()
    # USE MODEL_NAME AS INSTANCE_NAME
    model_name = parts[1] if len(parts) > 1 else "UNKNOWN"
    instance_name = parts[3] if len(parts) > 3 else "DEFAULT"

    use = UseInstance(
        model_name=model_name,
        instance_name=instance_name,
        start_line=start,
    )
    use.raw_lines.append(lines[start])

    i = start + 1
    current_section = None

    while i < limit:
        stripped = lines[i].strip()
        use.raw_lines.append(lines[i])

        if stripped == "ENDUSE":
            use.end_line = i
            return use, i + 1

        if stripped == "INPUT":
            current_section = "INPUT"
            i += 1
            continue

        if stripped == "DATA":
            current_section = "DATA"
            i += 1
            continue

        if stripped == "OUTPUT":
            current_section = "OUTPUT"
            i += 1
            continue

        if current_section == "INPUT" and stripped:
            match = re.match(r"\s*(\S+):=\s*(\S+)", lines[i])
            if match:
                use.inputs.append(
                    InputMapping(
                        local_name=match.group(1),
                        mapped_to=match.group(2),
                        raw_line=lines[i],
                    )
                )

        elif current_section == "DATA" and stripped:
            match = re.match(r"\s*(\S+):=\s*(.+)", lines[i])
            if match:
                use.data.append(
                    DataParam(
                        name=match.group(1),
                        assigned_value=match.group(2).strip(),
                        raw_line=lines[i],
                    )
                )

        elif current_section == "OUTPUT" and stripped:
            match = re.match(r"\s*(\S+):=\s*(\S+)", lines[i])
            if match:
                use.outputs.append(
                    OutputMapping(
                        global_name=match.group(1),
                        local_name=match.group(2),
                        raw_line=lines[i],
                    )
                )

        i += 1

    use.end_line = i - 1
    return use, i


# ======================================================================
# Component parsers (CORE-001, CORE-002, CORE-003)
# ======================================================================

_SKIP_PREFIXES = ("C ", "C\t", "$", "BLANK")
_SKIP_CONTAINS = ("TACS CONTROL", "USE AR", "USE OLD", "NAME  PHASOR")


def _is_data_line(line: str) -> bool:
    """Check if a line is a component data line (not comment/control)."""
    if not line or len(line) < 8:
        return False
    stripped = line.strip()
    if not stripped:
        return False
    if any(stripped.startswith(p) for p in _SKIP_PREFIXES):
        return False
    if any(kw in line for kw in _SKIP_CONTAINS):
        return False
    return True


def _safe_col(line: str, start: int, end: int) -> str:
    """Extract column slice, stripped."""
    if len(line) < start:
        return ""
    return line[start:min(end, len(line))].strip()


def _looks_like_node_name(s: str) -> bool:
    """Heuristic: a valid ATP node name has at least one non-E letter.

    ATP numeric continuation lines (Bergeron line-model data, transformer
    admittance matrices, etc.) are fixed-column numbers that get parsed as
    garbage "node names" like '1.48554' and '9584425'. Those contain only
    digits, dots, '+'/'-', and possibly 'E'/'e' (scientific notation). Real
    node names — 'X0030A', 'BUS1', 'NEUTRA' — always contain at least one
    letter that isn't the exponent marker.
    """
    if not s:
        return False
    has_digit = any(c.isdigit() for c in s)
    has_non_e_alpha = any(c.isalpha() and c.upper() != "E" for c in s)
    if has_non_e_alpha:
        return True
    if has_digit:
        # Only E among letters + digits → scientific notation, not a name
        return False
    # Pure letters (even all-E like "EEE"): accept as name
    return any(c.isalpha() for c in s)


def _parse_branch_components(project: AtpProject, section: Section) -> None:
    """Parse /BRANCH lines into BranchComponent objects.

    ATP BRANCH format (6-char fields):
      Col 0-1:  type/sequence code
      Col 2-7:  node 1
      Col 8-13: node 2
      Col 14-19: ref1
      Col 20-25: ref2
      Col 26-31: R
      Col 32-37: L
      Col 38-43: C
    """
    base = section.start_line
    for idx, line in enumerate(section.raw_lines):
        if idx == 0:  # skip the /BRANCH header line
            continue
        if not _is_data_line(line):
            continue

        node1 = _safe_col(line, 2, 8)
        node2 = _safe_col(line, 8, 14)

        # Both empty → not a branch
        if not node1 and not node2:
            continue
        # Reject numeric-continuation lines whose "node names" are really
        # fragments of Bergeron / matrix data (e.g. "1.48554" / "95844256").
        if not _looks_like_node_name(node1) and not _looks_like_node_name(node2):
            continue

        comp = BranchComponent(
            node1=node1,
            node2=node2,
            type_code=_safe_col(line, 0, 2),
            ref1=_safe_col(line, 14, 20),
            ref2=_safe_col(line, 20, 26),
            resistance=_safe_col(line, 26, 32) or None,
            inductance=_safe_col(line, 32, 38) or None,
            capacitance=_safe_col(line, 38, 44) or None,
            raw_line=line,
            line_number=base + idx,
        )
        project.branches.append(comp)


def _parse_switch_components(project: AtpProject, section: Section) -> None:
    """Parse /SWITCH lines into SwitchComponent objects.

    ATP SWITCH format:
      Col 0-1:  type code
      Col 2-7:  node 1
      Col 8-13: node 2
      Col 14-23: Tclose (10 chars)
      Col 24-33: Top/Tde (10 chars)
      Col 34-43: Ie (10 chars)
      Col 44-53: Vf/CLOP (10 chars)
      Col 54-63: type (CLOSED/MEASURING/etc)
    """
    base = section.start_line
    for idx, line in enumerate(section.raw_lines):
        if idx == 0:
            continue
        if not _is_data_line(line):
            continue

        node1 = _safe_col(line, 2, 8)
        node2 = _safe_col(line, 8, 14)

        if not node1 and not node2:
            continue
        if not _looks_like_node_name(node1) and not _looks_like_node_name(node2):
            continue

        # Extract TACS output node (after the type field, around col 64+)
        tacs_out = ""
        rest = line[64:].strip() if len(line) > 64 else ""
        # TACS output node is typically 6 chars after type/spaces
        parts = rest.split()
        if parts:
            candidate = parts[0]
            if candidate and candidate[0].isalpha():
                tacs_out = candidate

        comp = SwitchComponent(
            node1=node1,
            node2=node2,
            type_code=_safe_col(line, 0, 2),
            t_close=_safe_col(line, 14, 24) or None,
            t_open=_safe_col(line, 24, 34) or None,
            ie=_safe_col(line, 34, 44) or None,
            switch_type=_safe_col(line, 44, 64),
            tacs_output=tacs_out,
            raw_line=line,
            line_number=base + idx,
        )
        project.switches.append(comp)


def _parse_source_components(project: AtpProject, section: Section) -> None:
    """Parse /SOURCE lines into SourceComponent objects.

    ATP SOURCE format:
      Col 0-1:  type code
      Col 2-7:  node (6 chars)
      Col 8-9:  blank/sign
      Col 10-19: amplitude (10 chars)
      Col 20-29: frequency (10 chars)
      Col 30-39: phase/T0 (10 chars)
      Col 40-49: A1 (10 chars)
      Col 50-59: T1 (10 chars)
      Col 60-69: TSTART (10 chars)
      Col 70-79: TSTOP (10 chars)
    """
    base = section.start_line
    for idx, line in enumerate(section.raw_lines):
        if idx == 0:
            continue
        if not _is_data_line(line):
            continue

        node = _safe_col(line, 2, 8)
        if not node:
            continue
        if not _looks_like_node_name(node):
            continue

        comp = SourceComponent(
            node=node,
            type_code=_safe_col(line, 0, 2),
            amplitude=_safe_col(line, 10, 20) or None,
            frequency=_safe_col(line, 20, 30) or None,
            phase=_safe_col(line, 30, 40) or None,
            t_start=_safe_col(line, 60, 70) or None,
            t_stop=_safe_col(line, 70, 80) or None,
            raw_line=line,
            line_number=base + idx,
        )
        project.sources.append(comp)


# ======================================================================
# Semantic classification (CORE-010)
# ======================================================================


def _classify_components(project: AtpProject) -> None:
    """Assign semantic_type to parsed components based on parameters and naming."""

    for b in project.branches:
        b.semantic_type = _classify_branch(b)

    for s in project.switches:
        s.semantic_type = _classify_switch(s)

    for s in project.sources:
        s.semantic_type = _classify_source(s)


def _classify_branch(b: BranchComponent) -> str:
    has_r = b.resistance and b.resistance not in ("0", "0.", "")
    has_l = b.inductance and b.inductance not in ("0", "0.", "")
    has_c = b.capacitance and b.capacitance not in ("0", "0.", "")

    nodes = (b.node1 + b.node2).upper()

    # Snubber: typically RC with "SNUB" or "SN" in node names
    if ("SNUB" in nodes or "SN" in nodes) and has_r and has_c and not has_l:
        return "snubber"

    # Transformer: type code often starts with specific codes, or node names contain "TRAFO"/"XFMR"
    if b.type_code.strip() in ("1", "2", "3") and b.ref1:
        return "transformer"

    # Line model / distributed parameter
    if b.type_code.strip() in ("-1", "-2", "-3"):
        return "line"

    # Pure elements
    count = sum([bool(has_r), bool(has_l), bool(has_c)])
    if count == 1:
        if has_r:
            return "resistor"
        if has_l:
            return "inductor"
        if has_c:
            return "capacitor"
    if count == 2:
        if has_r and has_c:
            return "RC"
        if has_r and has_l:
            return "RL"
        if has_l and has_c:
            return "LC"
    if count == 3:
        return "RLC"

    return "branch"


def _classify_switch(s: SwitchComponent) -> str:
    nodes = (s.node1 + s.node2).upper()
    sw_type = s.switch_type.upper().strip()

    if "MEASURING" in sw_type:
        return "measuring"
    if "SYSTEMATIC" in sw_type:
        return "systematic"

    # VCB: vacuum circuit breaker, often with TACS output and VCB/CB in node names
    if s.tacs_output and ("VCB" in nodes or "CB" in nodes or "DISJ" in nodes):
        return "vcb"

    # TACS-controlled switch (has TACS output but not VCB)
    if s.tacs_output:
        return "tacs_controlled"

    # Time-controlled
    if s.t_close or s.t_open:
        return "time_controlled"

    return "switch"


def _classify_source(s: SourceComponent) -> str:
    type_code = (s.type_code or "").strip()
    freq = s.frequency

    # Type codes: 11/14 = AC cosine, 13 = DC step, etc.
    if type_code in ("11", "14"):
        return "ac"
    if type_code == "13":
        return "dc"
    if type_code == "12":
        return "ramp"

    # Heuristic: if frequency is non-zero, likely AC
    if freq:
        try:
            if float(freq) > 0:
                return "ac"
        except ValueError:
            pass

    return "source"


# ======================================================================
# Node extraction (CORE-004)
# ======================================================================


def _extract_nodes(project: AtpProject) -> None:
    """Collect all unique nodes from parsed components."""
    nodes: dict[str, Node] = {}

    def _add(name: str, source: str) -> None:
        name = name.strip()
        if not name or len(name) > 6:
            return
        # Skip purely numeric continuation data
        if all(c in "0123456789.+-Ee " for c in name):
            return
        if name not in nodes:
            nodes[name] = Node(name=name)
        if source not in nodes[name].sources:
            nodes[name].sources.append(source)

    for b in project.branches:
        if b.node1:
            _add(b.node1, "BRANCH")
        if b.node2:
            _add(b.node2, "BRANCH")

    for s in project.switches:
        if s.node1:
            _add(s.node1, "SWITCH")
        if s.node2:
            _add(s.node2, "SWITCH")

    for s in project.sources:
        if s.node:
            _add(s.node, "SOURCE")

    # Also extract from MODELS global I/O
    for inp in project.models_global_io.inputs:
        match = re.search(r"v\((\w+)\)", inp.mapped_to, re.IGNORECASE)
        if match:
            _add(match.group(1), "MODELS")

    project.nodes = dict(sorted(nodes.items()))
