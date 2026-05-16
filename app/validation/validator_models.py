from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.core.project_model import AtpProject


class Severity(Enum):
    INFO = "INFO"
    WARNING = "AVISO"
    ERROR = "ERRO"


@dataclass
class ValidationMessage:
    severity: Severity
    code: str
    message: str


def validate_project(project: AtpProject) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []

    _validate_use_references(project, messages)
    _validate_io_counts(project, messages)
    _validate_similar_names(project, messages)
    _validate_duplicate_names(project, messages)
    _validate_sections_present(project, messages)
    _validate_section_syntax(project, messages)
    _validate_nodes(project, messages)

    return messages


def _validate_use_references(project: AtpProject, msgs: list[ValidationMessage]) -> None:
    model_names_upper = {m.name.upper() for m in project.models}

    for use in project.uses:
        if use.model_name.upper() not in model_names_upper:
            msgs.append(
                ValidationMessage(
                    severity=Severity.ERROR,
                    code="USE-001",
                    message=f"USE '{use.model_name}' references a MODEL not found in this file.",
                )
            )


def _validate_io_counts(project: AtpProject, msgs: list[ValidationMessage]) -> None:
    for use in project.uses:
        model = project.find_model(use.model_name)
        if model is None:
            continue

        if len(use.inputs) != len(model.inputs):
            msgs.append(
                ValidationMessage(
                    severity=Severity.WARNING,
                    code="IO-001",
                    message=(
                        f"USE '{use.model_name}': {len(use.inputs)} INPUT(s) "
                        f"but MODEL '{model.name}' declares {len(model.inputs)}."
                    ),
                )
            )

        if len(use.outputs) != len(model.outputs):
            msgs.append(
                ValidationMessage(
                    severity=Severity.WARNING,
                    code="IO-002",
                    message=(
                        f"USE '{use.model_name}': {len(use.outputs)} OUTPUT(s) "
                        f"but MODEL '{model.name}' declares {len(model.outputs)}."
                    ),
                )
            )

        if len(use.data) != len(model.data):
            msgs.append(
                ValidationMessage(
                    severity=Severity.WARNING,
                    code="IO-003",
                    message=(
                        f"USE '{use.model_name}': {len(use.data)} DATA param(s) "
                        f"but MODEL '{model.name}' declares {len(model.data)}."
                    ),
                )
            )


def _validate_similar_names(project: AtpProject, msgs: list[ValidationMessage]) -> None:
    model_names = [m.name for m in project.models]
    use_names = [u.model_name for u in project.uses]

    for use_name in use_names:
        for model_name in model_names:
            if use_name == model_name:
                continue
            if use_name.upper() == model_name.upper():
                msgs.append(
                    ValidationMessage(
                        severity=Severity.WARNING,
                        code="NAME-001",
                        message=(
                            f"Case mismatch: USE references '{use_name}' "
                            f"but MODEL is defined as '{model_name}'. "
                            f"ATP MODELS is case-insensitive, but this may cause confusion."
                        ),
                    )
                )


def _validate_duplicate_names(project: AtpProject, msgs: list[ValidationMessage]) -> None:
    seen_models: dict[str, int] = {}
    for m in project.models:
        key = m.name.upper()
        seen_models[key] = seen_models.get(key, 0) + 1

    for name, count in seen_models.items():
        if count > 1:
            msgs.append(
                ValidationMessage(
                    severity=Severity.ERROR,
                    code="DUP-001",
                    message=f"MODEL name '{name}' appears {count} times.",
                )
            )

    seen_uses: dict[str, int] = {}
    for u in project.uses:
        key = u.model_name.upper()
        seen_uses[key] = seen_uses.get(key, 0) + 1

    for name, count in seen_uses.items():
        if count > 1:
            msgs.append(
                ValidationMessage(
                    severity=Severity.INFO,
                    code="DUP-002",
                    message=f"USE of MODEL '{name}' appears {count} times (may be intentional).",
                )
            )


def _validate_sections_present(project: AtpProject, msgs: list[ValidationMessage]) -> None:
    expected = ["BRANCH", "SWITCH", "SOURCE", "OUTPUT"]
    for name in expected:
        if name not in project.sections:
            msgs.append(
                ValidationMessage(
                    severity=Severity.WARNING,
                    code="SEC-001",
                    message=f"Section /{name} not found in file.",
                )
            )


def _validate_section_syntax(project: AtpProject, msgs: list[ValidationMessage]) -> None:
    """Syntactic checks on sections (VAL-001)."""
    # Check MODELS has matching ENDMODELS
    if project.models or project.uses:
        raw = "\n".join(project.raw_lines)
        if "MODELS" in raw and "ENDMODELS" not in raw:
            msgs.append(
                ValidationMessage(
                    severity=Severity.ERROR,
                    code="SYN-001",
                    message="MODELS block opened but ENDMODELS not found.",
                )
            )

    # Check all MODELs have ENDMODEL
    for model in project.models:
        if model.end_line <= model.start_line:
            msgs.append(
                ValidationMessage(
                    severity=Severity.ERROR,
                    code="SYN-002",
                    message=f"MODEL '{model.name}' may be missing ENDMODEL.",
                )
            )

    # Check all USEs have ENDUSE
    for use in project.uses:
        if use.end_line <= use.start_line:
            msgs.append(
                ValidationMessage(
                    severity=Severity.ERROR,
                    code="SYN-003",
                    message=f"USE '{use.model_name}' may be missing ENDUSE.",
                )
            )

    # Check BLANK cards present
    has_blank = any(line.strip().startswith("BLANK ") for line in project.raw_lines)
    if not has_blank:
        msgs.append(
            ValidationMessage(
                severity=Severity.WARNING,
                code="SYN-004",
                message="No BLANK terminator cards found at end of file.",
            )
        )

    # Check sections are not empty
    for name, section in project.sections.items():
        data_lines = [l for l in section.raw_lines[1:] if l.strip() and not l.strip().startswith("C")]
        if not data_lines:
            msgs.append(
                ValidationMessage(
                    severity=Severity.WARNING,
                    code="SYN-005",
                    message=f"Section /{name} appears to be empty.",
                )
            )


def _validate_nodes(project: AtpProject, msgs: list[ValidationMessage]) -> None:
    """Check node consistency."""
    if not project.nodes:
        return

    # Nodes referenced in MODELS I/O should exist in BRANCH/SWITCH/SOURCE
    circuit_nodes = {
        name for name, node in project.nodes.items()
        if any(s in node.sources for s in ("BRANCH", "SWITCH", "SOURCE"))
    }
    model_nodes = {
        name for name, node in project.nodes.items()
        if "MODELS" in node.sources
    }

    orphan = model_nodes - circuit_nodes
    for name in sorted(orphan):
        msgs.append(
            ValidationMessage(
                severity=Severity.INFO,
                code="NODE-001",
                message=f"Node '{name}' referenced in MODELS I/O but not found in BRANCH/SWITCH/SOURCE.",
            )
        )
