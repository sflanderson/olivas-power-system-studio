from __future__ import annotations

from app.core.project_model import AtpProject, ModelDefinition, UseInstance
from app.validation.validator_models import Severity, ValidationMessage


def validate_vcb(project: AtpProject) -> list[ValidationMessage]:
    """Domain-specific validations for vacuum circuit breaker models."""
    msgs: list[ValidationMessage] = []

    vcb_models = [m for m in project.models if m.name.upper().startswith("VCB_")]
    vcb_uses = [u for u in project.uses if u.model_name.upper().startswith("VCB_")]

    if not vcb_models:
        return msgs

    for model in vcb_models:
        _validate_vcb_model_structure(model, msgs)

    for use in vcb_uses:
        model = project.find_model(use.model_name)
        _validate_vcb_data_ranges(use, model, msgs)

    _validate_vcb_phases(vcb_uses, msgs)
    _validate_snubber_connection(project, msgs)

    return msgs


def _validate_vcb_model_structure(model: ModelDefinition, msgs: list[ValidationMessage]) -> None:
    """Check VCB model has expected structure."""
    expected_inputs = {"V_POS", "V_NEG", "I_CB"}
    expected_outputs = {"SW_STATE", "R_VAL", "L_VAL", "C_VAL", "CB_STATE"}

    # Strip phase suffix for comparison
    actual_inputs = set()
    for inp in model.inputs:
        for prefix in expected_inputs:
            if inp.upper().startswith(prefix.upper()):
                actual_inputs.add(prefix)

    actual_outputs = set()
    for out in model.outputs:
        for prefix in expected_outputs:
            if out.upper().startswith(prefix.upper()):
                actual_outputs.add(prefix)

    missing_in = expected_inputs - actual_inputs
    if missing_in:
        msgs.append(ValidationMessage(
            severity=Severity.ERROR,
            code="VCB-001",
            message=f"MODEL '{model.name}': missing expected VCB inputs: {missing_in}",
        ))

    missing_out = expected_outputs - actual_outputs
    if missing_out:
        msgs.append(ValidationMessage(
            severity=Severity.ERROR,
            code="VCB-002",
            message=f"MODEL '{model.name}': missing expected VCB outputs: {missing_out}",
        ))

    # Check RRDS parameters exist in DATA
    data_names = {d.name.upper()[:4] for d in model.data}
    if "RRDS" not in "".join(data_names):
        rrds_found = any("RRDS" in d.name.upper() for d in model.data)
        if not rrds_found:
            msgs.append(ValidationMessage(
                severity=Severity.WARNING,
                code="VCB-003",
                message=f"MODEL '{model.name}': RRDS parameters not found in DATA (needed for TRV withstand).",
            ))


def _validate_vcb_data_ranges(
    use: UseInstance, model: ModelDefinition | None, msgs: list[ValidationMessage]
) -> None:
    """Validate VCB DATA parameter ranges are physically reasonable."""
    params: dict[str, float] = {}
    for d in use.data:
        try:
            val = float(d.assigned_value) if d.assigned_value else None
            if val is not None:
                # Normalize name: strip phase suffix
                base = d.name.rstrip("rstRST")
                params[base.upper()] = val
        except (ValueError, TypeError):
            pass

    # T_OPEN: should be positive and reasonable
    t_open = params.get("T_OPEN")
    if t_open is not None:
        if t_open < 0:
            msgs.append(ValidationMessage(
                severity=Severity.ERROR,
                code="VCB-010",
                message=f"USE '{use.model_name}': T_OPEN={t_open} is negative.",
            ))
        elif t_open > 1.0:
            msgs.append(ValidationMessage(
                severity=Severity.WARNING,
                code="VCB-011",
                message=f"USE '{use.model_name}': T_OPEN={t_open}s is unusually large (>1s).",
            ))

    # I_CHOP: typical range 1-15 A for VCB
    i_chop = params.get("I_CHOP")
    if i_chop is not None:
        if i_chop <= 0:
            msgs.append(ValidationMessage(
                severity=Severity.ERROR,
                code="VCB-012",
                message=f"USE '{use.model_name}': I_CHOP={i_chop} must be positive.",
            ))
        elif i_chop > 20:
            msgs.append(ValidationMessage(
                severity=Severity.WARNING,
                code="VCB-013",
                message=f"USE '{use.model_name}': I_CHOP={i_chop}A is above typical VCB range (1-15A).",
            ))

    # RRDS_A and RRDS_B: should be positive
    rrds_a = params.get("RRDS_A")
    rrds_b = params.get("RRDS_B")
    if rrds_a is not None and rrds_a <= 0:
        msgs.append(ValidationMessage(
            severity=Severity.WARNING,
            code="VCB-014",
            message=f"USE '{use.model_name}': RRDS_A={rrds_a} should be positive for TRV withstand.",
        ))
    if rrds_b is not None and rrds_b <= 0:
        msgs.append(ValidationMessage(
            severity=Severity.WARNING,
            code="VCB-015",
            message=f"USE '{use.model_name}': RRDS_B={rrds_b} should be positive for TRV withstand.",
        ))

    # RCLOSED should be small, ROPEN should be large
    r_closed = params.get("RCLOSED")
    r_open = params.get("ROPEN")
    if r_closed is not None and r_open is not None:
        if r_closed >= r_open:
            msgs.append(ValidationMessage(
                severity=Severity.ERROR,
                code="VCB-016",
                message=f"USE '{use.model_name}': RCLOSED={r_closed} >= ROPEN={r_open} (should be RCLOSED << ROPEN).",
            ))

    # DIDT_CRIT: should be positive
    didt = params.get("DIDT_CRIT")
    if didt is not None and didt <= 0:
        msgs.append(ValidationMessage(
            severity=Severity.ERROR,
            code="VCB-017",
            message=f"USE '{use.model_name}': DIDT_CRIT={didt} must be positive.",
        ))


def _validate_vcb_phases(vcb_uses: list[UseInstance], msgs: list[ValidationMessage]) -> None:
    """Check that VCB uses cover expected phases."""
    if len(vcb_uses) == 0:
        return

    phase_suffixes = set()
    for u in vcb_uses:
        name = u.model_name.upper()
        if name.startswith("VCB_R"):
            suffix = name[5:] if len(name) > 5 else ""
            phase_suffixes.add(suffix)

    if len(vcb_uses) >= 2 and len(phase_suffixes) < 3:
        msgs.append(ValidationMessage(
            severity=Severity.INFO,
            code="VCB-020",
            message=f"VCB phases found: {phase_suffixes}. Typical 3-phase system expects R, S, T.",
        ))


def _validate_snubber_connection(project: AtpProject, msgs: list[ValidationMessage]) -> None:
    """Check that SNUB_CTRL model exists and is connected to VCB CB_STATE outputs."""
    snub_models = [m for m in project.models if "SNUB" in m.name.upper()]
    snub_uses = [u for u in project.uses if "SNUB" in u.model_name.upper()]

    vcb_uses = [u for u in project.uses if u.model_name.upper().startswith("VCB_")]

    if vcb_uses and not snub_uses:
        msgs.append(ValidationMessage(
            severity=Severity.INFO,
            code="VCB-030",
            message="VCB models found but no Snubber controller USE. Consider adding snubber circuit.",
        ))

    if snub_uses:
        for su in snub_uses:
            # Check that snubber inputs are connected to VCB CB_STATE outputs
            connected_signals = {inp.mapped_to for inp in su.inputs}

            for vu in vcb_uses:
                cb_state_outputs = [
                    out.global_name for out in vu.outputs
                    if "STATE" in out.local_name.upper() and "CB" in out.local_name.upper()
                ]
                for cb_out in cb_state_outputs:
                    if cb_out not in connected_signals:
                        msgs.append(ValidationMessage(
                            severity=Severity.WARNING,
                            code="VCB-031",
                            message=(
                                f"VCB '{vu.model_name}' output '{cb_out}' (CB_STATE) "
                                f"may not be connected to snubber '{su.model_name}' inputs."
                            ),
                        ))
