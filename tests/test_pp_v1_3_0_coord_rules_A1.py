"""
tests.test_pp_v1_3_0_coord_rules_A1 — sub-sprint A.1.

Cobre o **data model** do Coordination Rule Engine:

* ``RuleSeverity`` enum
* ``RuleResult`` dataclass + helpers (is_pass/is_fail/is_warn/is_na)
* ``Rule`` dataclass com `applies_to` e `evaluate`
* ``RuleSet`` dataclass com validação de uniqueness
* ``RuleEngine`` com apply_rule / apply_ruleset / filter / group / count

**Aceite A.1**: 12+ testes, 100% verde, sem regressão v1.2.0.
"""

from __future__ import annotations

import pytest

from app.postprocessor.coord_rules import (
    Rule,
    RuleEngine,
    RuleResult,
    RuleSet,
    RuleSeverity,
)


# Dummy target classes para testes (sem precisar TCCDevice)
class _DummyTarget:
    """Target genérico para testes do data model A.1."""

    def __init__(self, device_id: str, value: float = 100.0):
        self.device_id = device_id
        self.value = value


class _OtherTarget:
    """Target de outro tipo para testar isinstance check."""

    def __init__(self, name: str):
        self.name = name


# ---------------------------------------------------------------------------
# RuleSeverity enum
# ---------------------------------------------------------------------------


class TestRuleSeverity:

    def test_has_4_severities(self):
        assert len(list(RuleSeverity)) == 4

    def test_string_values(self):
        assert RuleSeverity.PASS == "pass"
        assert RuleSeverity.WARN == "warn"
        assert RuleSeverity.FAIL == "fail"
        assert RuleSeverity.NOT_APPLICABLE == "n/a"


# ---------------------------------------------------------------------------
# RuleResult
# ---------------------------------------------------------------------------


class TestRuleResult:

    def test_basic_construction(self):
        r = RuleResult(
            rule_id="X",
            target_id="T",
            severity=RuleSeverity.PASS,
            message="ok",
            citation="IEEE 242 §X",
        )
        assert r.is_pass()
        assert not r.is_fail()
        assert not r.is_warn()
        assert not r.is_not_applicable()

    def test_optional_fields_default_none(self):
        r = RuleResult(
            rule_id="X", target_id="T",
            severity=RuleSeverity.WARN,
            message="border", citation="C",
        )
        assert r.evaluated_value is None
        assert r.expected_range is None

    def test_with_evaluated_value_and_range(self):
        r = RuleResult(
            rule_id="X", target_id="T",
            severity=RuleSeverity.FAIL,
            message="out of range",
            citation="C",
            evaluated_value=130.5,
            expected_range=(115.0, 125.0),
        )
        assert r.evaluated_value == 130.5
        assert r.expected_range == (115.0, 125.0)
        assert r.is_fail()

    def test_severity_helpers_consistency(self):
        for sev, expected_method in [
            (RuleSeverity.PASS, "is_pass"),
            (RuleSeverity.WARN, "is_warn"),
            (RuleSeverity.FAIL, "is_fail"),
            (RuleSeverity.NOT_APPLICABLE, "is_not_applicable"),
        ]:
            r = RuleResult("x", "t", sev, "m", "c")
            assert getattr(r, expected_method)() is True


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------


class TestRule:

    def _make_rule_value_above_50(self):
        """Rule simples: value > 50 → PASS."""
        def eval_func(target, context):
            return RuleResult(
                rule_id="DUMMY-VAL-50",
                target_id=target.device_id,
                severity=(RuleSeverity.PASS if target.value > 50
                          else RuleSeverity.FAIL),
                message=f"value={target.value}",
                citation="DUMMY",
                evaluated_value=target.value,
                expected_range=(50.0, float("inf")),
            )
        return Rule(
            rule_id="DUMMY-VAL-50",
            description="Test rule: value > 50",
            citation="DUMMY",
            applicable_to=(_DummyTarget,),
            eval_func=eval_func,
        )

    def test_applies_to_correct_type(self):
        rule = self._make_rule_value_above_50()
        target = _DummyTarget("T1", value=100)
        assert rule.applies_to(target) is True

    def test_applies_to_returns_false_for_wrong_type(self):
        rule = self._make_rule_value_above_50()
        wrong = _OtherTarget("X")
        assert rule.applies_to(wrong) is False

    def test_evaluate_pass(self):
        rule = self._make_rule_value_above_50()
        target = _DummyTarget("T1", value=100)
        result = rule.evaluate(target)
        assert result.is_pass()
        assert result.target_id == "T1"
        assert result.evaluated_value == 100

    def test_evaluate_fail(self):
        rule = self._make_rule_value_above_50()
        target = _DummyTarget("T2", value=20)
        result = rule.evaluate(target)
        assert result.is_fail()

    def test_evaluate_wrong_type_returns_not_applicable(self):
        rule = self._make_rule_value_above_50()
        wrong = _OtherTarget("X")
        result = rule.evaluate(wrong)
        assert result.is_not_applicable()
        assert "não é instância" in result.message

    def test_evaluate_with_context(self):
        """Rule pode usar context dict."""
        def eval_with_ctx(target, context):
            mult = context.get("multiplier", 1.0)
            v = target.value * mult
            return RuleResult(
                rule_id="CTX-TEST",
                target_id=target.device_id,
                severity=RuleSeverity.PASS,
                message=f"v×mult = {v}",
                citation="—",
                evaluated_value=v,
            )
        rule = Rule(
            rule_id="CTX-TEST",
            description="ctx test",
            citation="—",
            applicable_to=(_DummyTarget,),
            eval_func=eval_with_ctx,
        )
        target = _DummyTarget("T", value=10)
        result = rule.evaluate(target, {"multiplier": 5.0})
        assert result.evaluated_value == 50.0


# ---------------------------------------------------------------------------
# RuleSet
# ---------------------------------------------------------------------------


class TestRuleSet:

    def _dummy_rule(self, rule_id: str = "R1"):
        return Rule(
            rule_id=rule_id,
            description="d",
            citation="c",
            applicable_to=(_DummyTarget,),
            eval_func=lambda t, ctx: RuleResult(
                rule_id, "x", RuleSeverity.PASS, "m", "c",
            ),
        )

    def test_constructs_with_tuple(self):
        rs = RuleSet(
            name="N", norm_reference="NR",
            rules=(self._dummy_rule("R1"), self._dummy_rule("R2")),
        )
        assert len(rs) == 2

    def test_constructs_with_list_converts_to_tuple(self):
        rs = RuleSet(
            name="N", norm_reference="NR",
            rules=[self._dummy_rule("R1")],
        )
        assert isinstance(rs.rules, tuple)

    def test_rejects_non_rule_items(self):
        with pytest.raises(TypeError):
            RuleSet(
                name="N", norm_reference="NR",
                rules=("not_a_rule",),
            )

    def test_rejects_duplicate_rule_ids(self):
        with pytest.raises(ValueError):
            RuleSet(
                name="N", norm_reference="NR",
                rules=(self._dummy_rule("R1"), self._dummy_rule("R1")),
            )

    def test_get_rule_by_id(self):
        rs = RuleSet(
            name="N", norm_reference="NR",
            rules=(self._dummy_rule("R-A"), self._dummy_rule("R-B")),
        )
        r = rs.get_rule("R-A")
        assert r is not None
        assert r.rule_id == "R-A"

    def test_get_rule_returns_none_for_missing(self):
        rs = RuleSet(
            name="N", norm_reference="NR",
            rules=(self._dummy_rule("R-A"),),
        )
        assert rs.get_rule("NONEXISTENT") is None


# ---------------------------------------------------------------------------
# RuleEngine
# ---------------------------------------------------------------------------


class TestRuleEngine:

    def _make_engine_and_ruleset(self):
        """Engine + RuleSet de 2 rules para teste."""
        def above_50(target, ctx):
            return RuleResult(
                "R-50", target.device_id,
                (RuleSeverity.PASS if target.value > 50 else RuleSeverity.FAIL),
                f"v={target.value}", "C",
                evaluated_value=target.value,
            )

        def above_200(target, ctx):
            return RuleResult(
                "R-200", target.device_id,
                (RuleSeverity.PASS if target.value > 200 else RuleSeverity.FAIL),
                f"v={target.value}", "C",
                evaluated_value=target.value,
            )

        rs = RuleSet(
            name="DUMMY", norm_reference="DUMMY",
            rules=(
                Rule(
                    rule_id="R-50",
                    description="value > 50",
                    citation="C",
                    applicable_to=(_DummyTarget,),
                    eval_func=above_50,
                ),
                Rule(
                    rule_id="R-200",
                    description="value > 200",
                    citation="C",
                    applicable_to=(_DummyTarget,),
                    eval_func=above_200,
                ),
            ),
        )
        return RuleEngine(), rs

    def test_apply_ruleset_returns_one_per_target_per_rule(self):
        engine, rs = self._make_engine_and_ruleset()
        targets = [
            _DummyTarget("T1", value=300),  # PASS, PASS
            _DummyTarget("T2", value=100),  # PASS, FAIL
            _DummyTarget("T3", value=10),   # FAIL, FAIL
        ]
        results = engine.apply_ruleset(rs, targets)
        assert len(results) == 6  # 3 targets × 2 rules

    def test_filter_by_severity(self):
        engine, rs = self._make_engine_and_ruleset()
        targets = [_DummyTarget("T1", value=10)]  # FAIL, FAIL
        results = engine.apply_ruleset(rs, targets)
        fails = engine.filter_by_severity(results, RuleSeverity.FAIL)
        assert len(fails) == 2

    def test_group_by_severity_has_all_keys(self):
        engine, rs = self._make_engine_and_ruleset()
        targets = [_DummyTarget("T1", value=300)]  # PASS, PASS
        results = engine.apply_ruleset(rs, targets)
        groups = engine.group_by_severity(results)
        assert RuleSeverity.PASS in groups
        assert RuleSeverity.FAIL in groups
        assert RuleSeverity.WARN in groups
        assert RuleSeverity.NOT_APPLICABLE in groups
        assert len(groups[RuleSeverity.PASS]) == 2
        assert len(groups[RuleSeverity.FAIL]) == 0

    def test_count_by_severity(self):
        engine, rs = self._make_engine_and_ruleset()
        targets = [
            _DummyTarget("T1", value=300),  # PASS, PASS
            _DummyTarget("T2", value=10),   # FAIL, FAIL
        ]
        results = engine.apply_ruleset(rs, targets)
        counts = engine.count_by_severity(results)
        assert counts[RuleSeverity.PASS] == 2
        assert counts[RuleSeverity.FAIL] == 2
        assert counts[RuleSeverity.WARN] == 0

    def test_has_failures(self):
        engine, rs = self._make_engine_and_ruleset()
        good = [_DummyTarget("T1", value=300)]
        bad = [_DummyTarget("T2", value=10)]
        results_good = engine.apply_ruleset(rs, good)
        results_bad = engine.apply_ruleset(rs, bad)
        assert engine.has_failures(results_good) is False
        assert engine.has_failures(results_bad) is True

    def test_summary_line_format(self):
        engine, rs = self._make_engine_and_ruleset()
        targets = [
            _DummyTarget("T1", value=300),  # PASS, PASS
            _DummyTarget("T2", value=10),   # FAIL, FAIL
        ]
        results = engine.apply_ruleset(rs, targets)
        summary = engine.summary_line(results)
        assert "PASS=2" in summary
        assert "FAIL=2" in summary
        assert "WARN=0" in summary

    def test_apply_rulesets_combines_multiple(self):
        engine, rs1 = self._make_engine_and_ruleset()
        # Cria segundo RuleSet com 1 rule
        def above_zero(t, ctx):
            return RuleResult(
                "R-0", t.device_id, RuleSeverity.PASS, "v>0", "C",
                evaluated_value=t.value,
            )
        rs2 = RuleSet(
            name="X", norm_reference="X",
            rules=(Rule("R-0", "d", "c", (_DummyTarget,), above_zero),),
        )
        targets = [_DummyTarget("T", value=300)]
        results = engine.apply_rulesets([rs1, rs2], targets)
        # rs1 = 2 rules, rs2 = 1 rule → 3 results para 1 target
        assert len(results) == 3

    def test_not_applicable_target_filtered_correctly(self):
        engine, rs = self._make_engine_and_ruleset()
        # _OtherTarget não satisfaz applicable_to=(_DummyTarget,)
        targets = [_OtherTarget("X")]
        results = engine.apply_ruleset(rs, targets)
        # 2 rules × 1 wrong target = 2 NOT_APPLICABLE
        nas = engine.filter_by_severity(results, RuleSeverity.NOT_APPLICABLE)
        assert len(nas) == 2
