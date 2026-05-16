"""Tests for validation modules."""
from __future__ import annotations

from app.core.project_model import AtpProject
from app.validation.validator_models import Severity, validate_project
from app.validation.validator_physics import validate_physics
from app.validation.validator_vcb import validate_vcb


class TestValidatorModels:
    def test_returns_list(self, ref_project: AtpProject):
        msgs = validate_project(ref_project)
        assert isinstance(msgs, list)

    def test_no_errors(self, ref_project: AtpProject):
        """Reference file should have no structural ERRO."""
        msgs = validate_project(ref_project)
        errors = [m for m in msgs if m.severity == Severity.ERROR]
        assert len(errors) == 0, f"Unexpected errors: {[m.message for m in errors]}"

    def test_message_structure(self, ref_project: AtpProject):
        msgs = validate_project(ref_project)
        for m in msgs:
            assert m.severity in Severity
            assert m.code
            assert m.message


class TestValidatorPhysics:
    def test_returns_list(self, ref_project: AtpProject):
        msgs = validate_physics(ref_project)
        assert isinstance(msgs, list)

    def test_messages_have_severity(self, ref_project: AtpProject):
        msgs = validate_physics(ref_project)
        for m in msgs:
            assert m.severity in Severity


class TestValidatorVcb:
    def test_returns_list(self, ref_project: AtpProject):
        msgs = validate_vcb(ref_project)
        assert isinstance(msgs, list)

    def test_no_errors_on_valid_vcb(self, ref_project: AtpProject):
        """VCB validator should not produce errors on well-configured VCB file."""
        msgs = validate_vcb(ref_project)
        errors = [m for m in msgs if m.severity == Severity.ERROR]
        assert len(errors) == 0, f"Unexpected VCB errors: {[m.message for m in errors]}"


class TestAllValidators:
    def test_combined_no_crash(self, ref_project: AtpProject):
        """Running all validators together should not crash."""
        msgs = validate_project(ref_project)
        msgs.extend(validate_physics(ref_project))
        msgs.extend(validate_vcb(ref_project))
        assert isinstance(msgs, list)
        assert len(msgs) > 0
