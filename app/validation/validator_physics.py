"""Physical validation of circuit component parameters.

VAL-010: Check that component values are physically reasonable.
"""
from __future__ import annotations

from app.core.project_model import AtpProject, BranchComponent, SourceComponent, SwitchComponent
from app.validation.validator_models import Severity, ValidationMessage


def validate_physics(project: AtpProject) -> list[ValidationMessage]:
    """Run physical validations on all parsed components."""
    msgs: list[ValidationMessage] = []

    for b in project.branches:
        _validate_branch_physics(b, msgs)

    for s in project.switches:
        _validate_switch_physics(s, msgs)

    for s in project.sources:
        _validate_source_physics(s, msgs)

    _validate_floating_nodes(project, msgs)

    return msgs


def _try_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _validate_branch_physics(b: BranchComponent, msgs: list[ValidationMessage]) -> None:
    label = f"BRANCH {b.node1}–{b.node2} (L{b.line_number + 1})"

    r = _try_float(b.resistance)
    l = _try_float(b.inductance)
    c = _try_float(b.capacitance)

    # Coupled-branch rows (type_code 2, 3, 4…) legitimately carry
    # off-diagonal mutual terms that are negative. Don't flag those as
    # physics errors — ATP allows them.
    type_code = (b.type_code or "").strip()
    is_coupled_row = type_code in ("2", "3", "4", "5", "6", "7", "8", "9")
    neg_severity = Severity.INFO if is_coupled_row else Severity.ERROR
    neg_note = " (linha acoplada)" if is_coupled_row else ""

    # Negative resistance
    if r is not None and r < 0:
        msgs.append(ValidationMessage(
            severity=neg_severity,
            code="PHY-001",
            message=f"{label}: resistência negativa R={r}{neg_note}",
        ))

    # Negative inductance
    if l is not None and l < 0:
        msgs.append(ValidationMessage(
            severity=neg_severity,
            code="PHY-002",
            message=f"{label}: indutância negativa L={l}{neg_note}",
        ))

    # Negative capacitance
    if c is not None and c < 0:
        msgs.append(ValidationMessage(
            severity=neg_severity,
            code="PHY-003",
            message=f"{label}: capacitância negativa C={c}{neg_note}",
        ))

    # Very large resistance (>1e12 Ω) — may indicate open circuit typo
    if r is not None and r > 1e12:
        msgs.append(ValidationMessage(
            severity=Severity.WARNING,
            code="PHY-004",
            message=f"{label}: R={r:.2e} Ω muito elevada (>1e12), possível circuito aberto",
        ))

    # Zero resistance with inductance — numerical instability
    if r is not None and r == 0 and l is not None and l > 0:
        msgs.append(ValidationMessage(
            severity=Severity.INFO,
            code="PHY-005",
            message=f"{label}: R=0 com L={l} — considere pequena resistência para estabilidade numérica",
        ))

    # Self-loop (node1 == node2 with non-empty nodes)
    if b.node1 and b.node2 and b.node1 == b.node2:
        msgs.append(ValidationMessage(
            severity=Severity.ERROR,
            code="PHY-006",
            message=f"{label}: nó1 = nó2 = '{b.node1}' — curto-circuito ou erro de entrada",
        ))


def _validate_switch_physics(s: SwitchComponent, msgs: list[ValidationMessage]) -> None:
    label = f"SWITCH {s.node1}–{s.node2} (L{s.line_number + 1})"

    t_close = _try_float(s.t_close)
    t_open = _try_float(s.t_open)

    # Tclose > Topen (switch opens before closing)
    # In ATP, a very large Tclose (e.g. 3000 s) is a common "never closes during
    # simulation" idiom — treat as INFO, not WARNING. Only flag as WARNING when
    # both times look like they belong to the same simulation window.
    if t_close is not None and t_open is not None:
        if t_close > 0 and t_open > 0 and t_close > t_open:
            # Heuristic: if Tclose is an order of magnitude > Topen AND > 100 s,
            # it's the "always open" / "always closed" idiom → downgrade.
            sev = Severity.INFO if (t_close > 100 and t_close > 10 * t_open) else Severity.WARNING
            note = (
                " — Tclose alto: chave provavelmente permanece no estado inicial"
                if sev == Severity.INFO
                else " — chave abre antes de fechar"
            )
            msgs.append(ValidationMessage(
                severity=sev,
                code="PHY-010",
                message=f"{label}: Tclose={t_close} > Topen={t_open}{note}",
            ))

    # Negative switching times
    if t_close is not None and t_close < 0:
        msgs.append(ValidationMessage(
            severity=Severity.WARNING,
            code="PHY-011",
            message=f"{label}: Tclose={t_close} negativo (chave inicialmente fechada no ATP)",
        ))

    # Self-loop
    if s.node1 and s.node2 and s.node1 == s.node2:
        msgs.append(ValidationMessage(
            severity=Severity.ERROR,
            code="PHY-012",
            message=f"{label}: nó1 = nó2 = '{s.node1}' — chave em curto permanente",
        ))


def _validate_source_physics(s: SourceComponent, msgs: list[ValidationMessage]) -> None:
    label = f"SOURCE {s.node} (L{s.line_number + 1})"

    amp = _try_float(s.amplitude)
    freq = _try_float(s.frequency)
    t_start = _try_float(s.t_start)
    t_stop = _try_float(s.t_stop)

    # Zero amplitude
    if amp is not None and amp == 0:
        msgs.append(ValidationMessage(
            severity=Severity.INFO,
            code="PHY-020",
            message=f"{label}: amplitude zero — fonte inativa",
        ))

    # Negative frequency
    if freq is not None and freq < 0:
        msgs.append(ValidationMessage(
            severity=Severity.ERROR,
            code="PHY-021",
            message=f"{label}: frequência negativa f={freq} Hz",
        ))

    # Tstart > Tstop
    if t_start is not None and t_stop is not None:
        if t_start > 0 and t_stop > 0 and t_start >= t_stop:
            msgs.append(ValidationMessage(
                severity=Severity.WARNING,
                code="PHY-022",
                message=f"{label}: Tstart={t_start} >= Tstop={t_stop} — fonte nunca ativa",
            ))

    # Very high voltage (>1e7 V = 10 MV)
    if amp is not None and abs(amp) > 1e7:
        msgs.append(ValidationMessage(
            severity=Severity.WARNING,
            code="PHY-023",
            message=f"{label}: amplitude={amp:.2e} V muito elevada (>10 MV)",
        ))


def _validate_floating_nodes(project: AtpProject, msgs: list[ValidationMessage]) -> None:
    """Detect nodes connected to only one component (potentially floating)."""
    node_connections: dict[str, int] = {}

    for b in project.branches:
        for n in (b.node1, b.node2):
            if n:
                node_connections[n] = node_connections.get(n, 0) + 1
    for s in project.switches:
        for n in (s.node1, s.node2):
            if n:
                node_connections[n] = node_connections.get(n, 0) + 1
    for s in project.sources:
        if s.node:
            node_connections[s.node] = node_connections.get(s.node, 0) + 1

    for name, count in sorted(node_connections.items()):
        if count == 1:
            # Skip purely numeric tokens (parser artifacts from fixed-column data)
            stripped = name.strip().lstrip("-+")
            if stripped.replace(".", "").replace("E", "").replace("e", "").isdigit():
                continue
            msgs.append(ValidationMessage(
                severity=Severity.INFO,
                code="PHY-030",
                message=f"Nó '{name}' conectado a apenas 1 componente — possível nó flutuante",
            ))
