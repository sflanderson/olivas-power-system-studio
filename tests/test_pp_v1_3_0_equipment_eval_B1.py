"""
tests.test_pp_v1_3_0_equipment_eval_B1 — sub-sprint B.1.

Cobre o data model de Equipment Evaluation:
* `EquipmentInstance` (ratings + duty)
* `EvaluationReport` (container de RuleResults)
* `evaluate_equipment()` orquestrador
* `evaluate_project()` batch

**Aceite B.1**: 12+ testes, 100% verde, sem regressão Fase A.
"""

from __future__ import annotations

import pytest

from app.postprocessor.coord_rules import (
    Rule, RuleResult, RuleSet, RuleSeverity,
)
from app.postprocessor.equipment_eval import (
    EquipmentInstance,
    EvaluationReport,
    evaluate_equipment,
    evaluate_project,
)


# ---------------------------------------------------------------------------
# EquipmentInstance
# ---------------------------------------------------------------------------


class TestEquipmentInstance:

    def test_basic_construction(self):
        eq = EquipmentInstance(
            equipment_id="BRK-1",
            equipment_type="breaker",
            rated_voltage_kV=15.0,
            rated_continuous_A=2000,
            rated_interrupt_kA=40.0,
            rated_asym_kA=104.0,
            bus_voltage_kV=13.8,
            duty={"I_load_A": 1500, "I_fault_kA": 25.0},
        )
        assert eq.equipment_id == "BRK-1"
        assert eq.equipment_type == "breaker"
        assert eq.rated_voltage_kV == 15.0
        assert eq.duty["I_load_A"] == 1500

    def test_default_optional_fields(self):
        eq = EquipmentInstance(
            equipment_id="BUS-1",
            equipment_type="bus",
            rated_voltage_kV=13.8,
            rated_continuous_A=3000,
        )
        assert eq.rated_interrupt_kA == 0.0
        assert eq.rated_asym_kA == 0.0
        assert eq.bus_voltage_kV == 0.0
        assert eq.duty == {}
        assert eq.model_ref is None

    def test_get_duty_with_default(self):
        eq = EquipmentInstance(
            equipment_id="X", equipment_type="cable",
            rated_voltage_kV=1.0, rated_continuous_A=100,
            duty={"I_load_A": 80},
        )
        assert eq.get_duty("I_load_A") == 80
        assert eq.get_duty("nonexistent", 0) == 0

    def test_negative_voltage_raises(self):
        with pytest.raises(ValueError):
            EquipmentInstance(
                equipment_id="X", equipment_type="breaker",
                rated_voltage_kV=-1.0, rated_continuous_A=100,
            )

    def test_negative_current_raises(self):
        with pytest.raises(ValueError):
            EquipmentInstance(
                equipment_id="X", equipment_type="breaker",
                rated_voltage_kV=1.0, rated_continuous_A=-100,
            )

    def test_invalid_equipment_type_raises(self):
        with pytest.raises(ValueError):
            EquipmentInstance(
                equipment_id="X", equipment_type="UFO",
                rated_voltage_kV=1.0, rated_continuous_A=100,
            )

    def test_valid_equipment_types(self):
        for et in ("breaker", "cable", "transformer",
                   "generator", "motor", "bus", "fuse", "contactor"):
            eq = EquipmentInstance(
                equipment_id="X", equipment_type=et,
                rated_voltage_kV=1.0, rated_continuous_A=100,
            )
            assert eq.equipment_type == et

    def test_with_model_ref(self):
        eq = EquipmentInstance(
            equipment_id="X", equipment_type="breaker",
            rated_voltage_kV=15.0, rated_continuous_A=2000,
            model_ref="ABB-HD4",
        )
        assert eq.model_ref == "ABB-HD4"


# ---------------------------------------------------------------------------
# EvaluationReport
# ---------------------------------------------------------------------------


def _make_result(rule_id: str, severity: RuleSeverity) -> RuleResult:
    """Helper para criar RuleResult de teste."""
    return RuleResult(
        rule_id=rule_id,
        target_id="T",
        severity=severity,
        message="msg",
        citation="C",
    )


class TestEvaluationReport:

    def test_basic_construction(self):
        rep = EvaluationReport(
            equipment_id="BRK-1",
            equipment_type="breaker",
            results=(),
        )
        assert rep.equipment_id == "BRK-1"
        assert len(rep.results) == 0

    def test_list_converted_to_tuple(self):
        rep = EvaluationReport(
            equipment_id="X", equipment_type="bus",
            results=[_make_result("R1", RuleSeverity.PASS)],
        )
        assert isinstance(rep.results, tuple)

    def test_rejects_non_RuleResult(self):
        with pytest.raises(TypeError):
            EvaluationReport(
                equipment_id="X", equipment_type="bus",
                results=("not_a_result",),
            )

    def test_passes_warnings_failures_helpers(self):
        rep = EvaluationReport(
            equipment_id="X", equipment_type="bus",
            results=[
                _make_result("R1", RuleSeverity.PASS),
                _make_result("R2", RuleSeverity.WARN),
                _make_result("R3", RuleSeverity.FAIL),
                _make_result("R4", RuleSeverity.PASS),
                _make_result("R5", RuleSeverity.NOT_APPLICABLE),
            ],
        )
        assert len(rep.passes()) == 2
        assert len(rep.warnings()) == 1
        assert len(rep.failures()) == 1
        assert len(rep.not_applicables()) == 1

    def test_passes_all_true_when_no_fails(self):
        rep = EvaluationReport(
            equipment_id="X", equipment_type="bus",
            results=[
                _make_result("R1", RuleSeverity.PASS),
                _make_result("R2", RuleSeverity.PASS),
                _make_result("R3", RuleSeverity.NOT_APPLICABLE),
            ],
        )
        assert rep.passes_all() is True

    def test_passes_all_false_with_warnings(self):
        rep = EvaluationReport(
            equipment_id="X", equipment_type="bus",
            results=[
                _make_result("R1", RuleSeverity.PASS),
                _make_result("R2", RuleSeverity.WARN),
            ],
        )
        # WARN não é PASS → passes_all = False
        assert rep.passes_all() is False

    def test_passes_all_true_when_only_NA(self):
        """Sem rules aplicáveis: trivially passes."""
        rep = EvaluationReport(
            equipment_id="X", equipment_type="bus",
            results=[
                _make_result("R1", RuleSeverity.NOT_APPLICABLE),
            ],
        )
        assert rep.passes_all() is True

    def test_overall_status_hierarchy(self):
        # FAIL é o pior
        rep_fail = EvaluationReport(
            equipment_id="X", equipment_type="bus",
            results=[
                _make_result("R1", RuleSeverity.PASS),
                _make_result("R2", RuleSeverity.WARN),
                _make_result("R3", RuleSeverity.FAIL),
            ],
        )
        assert rep_fail.overall_status() == "FAIL"

        # WARN sem FAIL
        rep_warn = EvaluationReport(
            equipment_id="X", equipment_type="bus",
            results=[
                _make_result("R1", RuleSeverity.PASS),
                _make_result("R2", RuleSeverity.WARN),
            ],
        )
        assert rep_warn.overall_status() == "WARN"

        # PASS only
        rep_pass = EvaluationReport(
            equipment_id="X", equipment_type="bus",
            results=[_make_result("R1", RuleSeverity.PASS)],
        )
        assert rep_pass.overall_status() == "PASS"

        # NA only
        rep_na = EvaluationReport(
            equipment_id="X", equipment_type="bus",
            results=[_make_result("R1", RuleSeverity.NOT_APPLICABLE)],
        )
        assert rep_na.overall_status() == "N/A"

    def test_count_by_severity(self):
        rep = EvaluationReport(
            equipment_id="X", equipment_type="bus",
            results=[
                _make_result("R1", RuleSeverity.PASS),
                _make_result("R2", RuleSeverity.PASS),
                _make_result("R3", RuleSeverity.FAIL),
            ],
        )
        counts = rep.count_by_severity()
        assert counts[RuleSeverity.PASS] == 2
        assert counts[RuleSeverity.FAIL] == 1
        assert counts[RuleSeverity.WARN] == 0


# ---------------------------------------------------------------------------
# evaluate_equipment
# ---------------------------------------------------------------------------


class TestEvaluateEquipment:

    def _make_eq(self, **overrides):
        defaults = dict(
            equipment_id="BRK-1",
            equipment_type="breaker",
            rated_voltage_kV=15.0,
            rated_continuous_A=2000,
            rated_interrupt_kA=40.0,
            bus_voltage_kV=13.8,
            duty={"I_load_A": 1500, "I_fault_kA": 25.0},
        )
        defaults.update(overrides)
        return EquipmentInstance(**defaults)

    def _voltage_rating_rule(self):
        """Rule simples: rated_V >= bus_V."""
        def eval_func(target, ctx):
            sev = (
                RuleSeverity.PASS
                if target.rated_voltage_kV >= target.bus_voltage_kV
                else RuleSeverity.FAIL
            )
            return RuleResult(
                rule_id="V-RATING",
                target_id=target.equipment_id,
                severity=sev,
                message=f"V_rated={target.rated_voltage_kV} vs "
                        f"V_bus={target.bus_voltage_kV}",
                citation="IEEE 242 §15.6.1",
            )
        return Rule(
            rule_id="V-RATING",
            description="V rating ≥ V bus",
            citation="IEEE 242 §15.6.1",
            applicable_to=(EquipmentInstance,),
            eval_func=eval_func,
        )

    def test_evaluate_returns_report(self):
        eq = self._make_eq()
        rule = self._voltage_rating_rule()
        rep = evaluate_equipment(eq, [rule])
        assert isinstance(rep, EvaluationReport)
        assert rep.equipment_id == "BRK-1"
        assert len(rep.results) == 1

    def test_evaluate_pass_case(self):
        eq = self._make_eq(rated_voltage_kV=15.0, bus_voltage_kV=13.8)
        rule = self._voltage_rating_rule()
        rep = evaluate_equipment(eq, [rule])
        assert rep.passes_all()

    def test_evaluate_fail_case(self):
        eq = self._make_eq(rated_voltage_kV=10.0, bus_voltage_kV=13.8)
        rule = self._voltage_rating_rule()
        rep = evaluate_equipment(eq, [rule])
        assert rep.has_failures()

    def test_evaluate_with_ruleset(self):
        eq = self._make_eq()
        rule = self._voltage_rating_rule()
        rs = RuleSet(
            name="EQ-V-RULES", norm_reference="IEEE 242 §15",
            rules=(rule,),
        )
        rep = evaluate_equipment(eq, rs)
        assert len(rep.results) == 1

    def test_duty_merged_into_context(self):
        """duty keys são passadas ao eval_func via context."""
        captured = {}

        def eval_func(target, ctx):
            captured.update(ctx)
            return RuleResult(
                "X", target.equipment_id, RuleSeverity.PASS, "m", "c",
            )

        rule = Rule(
            rule_id="X", description="d", citation="c",
            applicable_to=(EquipmentInstance,), eval_func=eval_func,
        )
        eq = self._make_eq(duty={"I_load_A": 1500, "X_factor": 0.5})
        evaluate_equipment(eq, [rule])
        assert captured["I_load_A"] == 1500
        assert captured["X_factor"] == 0.5

    def test_external_context_overrides_duty(self):
        """Context passado externamente tem precedência sobre duty."""
        captured = {}

        def eval_func(target, ctx):
            captured.update(ctx)
            return RuleResult(
                "X", target.equipment_id, RuleSeverity.PASS, "m", "c",
            )

        rule = Rule(
            rule_id="X", description="d", citation="c",
            applicable_to=(EquipmentInstance,), eval_func=eval_func,
        )
        eq = self._make_eq(duty={"I_load_A": 1500})
        # Override I_load_A via context externo
        evaluate_equipment(eq, [rule], context={"I_load_A": 9999})
        assert captured["I_load_A"] == 9999


# ---------------------------------------------------------------------------
# evaluate_project (batch)
# ---------------------------------------------------------------------------


class TestEvaluateProject:

    def test_batch_returns_one_report_per_equipment(self):
        eqs = [
            EquipmentInstance(
                equipment_id="BRK-1", equipment_type="breaker",
                rated_voltage_kV=15.0, rated_continuous_A=2000,
            ),
            EquipmentInstance(
                equipment_id="BRK-2", equipment_type="breaker",
                rated_voltage_kV=15.0, rated_continuous_A=1000,
            ),
            EquipmentInstance(
                equipment_id="CAB-1", equipment_type="cable",
                rated_voltage_kV=1.0, rated_continuous_A=200,
            ),
        ]

        def trivial_pass(target, ctx):
            return RuleResult(
                "TRIVIAL", target.equipment_id,
                RuleSeverity.PASS, "ok", "—",
            )

        rule = Rule(
            rule_id="TRIVIAL", description="d", citation="c",
            applicable_to=(EquipmentInstance,), eval_func=trivial_pass,
        )
        reports = evaluate_project(eqs, [rule])
        assert len(reports) == 3
        for rep in reports:
            assert rep.passes_all()
