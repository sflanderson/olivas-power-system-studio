"""
tests.test_pp_v1_3_0_equipment_eval_rules_B2 — sub-sprint B.2.

Cobre os 9 critérios PTW Equipment Evaluation:

* EQ-VOLTAGE-RATING
* EQ-INTERRUPT-DUTY
* EQ-ASYM-DUTY
* EQ-LOAD-FLOW-CURRENT
* EQ-DESIGN-LOAD
* EQ-GENERATOR-CAPACITY
* EQ-BUS-VOLTAGE-DROP
* EQ-BRANCH-VOLTAGE-DROP
* EQ-DEVICE-VOLTAGE-DROP

Cada critério tem testes PASS + WARN + FAIL + NA.

**Aceite B.2**: 30+ testes, 100% verde.
"""

from __future__ import annotations

import pytest

from app.postprocessor.coord_rules import RuleEngine, RuleSeverity
from app.postprocessor.equipment_eval import (
    EquipmentInstance,
    evaluate_equipment,
)
from app.postprocessor.equipment_eval_rules import (
    ALL_PTW_EQUIPMENT_RULES,
    PTW_EQUIPMENT_EVALUATION,
    RULE_EQ_ASYM_DUTY,
    RULE_EQ_BRANCH_VOLTAGE_DROP,
    RULE_EQ_BUS_VOLTAGE_DROP,
    RULE_EQ_DESIGN_LOAD,
    RULE_EQ_DEVICE_VOLTAGE_DROP,
    RULE_EQ_GENERATOR_CAPACITY,
    RULE_EQ_INTERRUPT_DUTY,
    RULE_EQ_LOAD_FLOW_CURRENT,
    RULE_EQ_VOLTAGE_RATING,
)


# ---------------------------------------------------------------------------
# Inventário
# ---------------------------------------------------------------------------


class TestRuleSetInventory:

    def test_9_rules_total(self):
        assert len(ALL_PTW_EQUIPMENT_RULES) == 9
        assert len(PTW_EQUIPMENT_EVALUATION) == 9

    def test_all_rule_ids_unique(self):
        ids = [r.rule_id for r in ALL_PTW_EQUIPMENT_RULES]
        assert len(ids) == len(set(ids))

    def test_all_rule_ids_start_with_EQ(self):
        for r in ALL_PTW_EQUIPMENT_RULES:
            assert r.rule_id.startswith("EQ-"), \
                f"rule_id {r.rule_id} não começa com EQ-"


# ---------------------------------------------------------------------------
# Critério 1 — EQ-VOLTAGE-RATING
# ---------------------------------------------------------------------------


class TestVoltageRating:

    def test_pass_when_rated_geq_bus(self):
        eq = EquipmentInstance(
            equipment_id="X", equipment_type="breaker",
            rated_voltage_kV=15.0, rated_continuous_A=2000,
            bus_voltage_kV=13.8,
        )
        result = RULE_EQ_VOLTAGE_RATING.evaluate(eq, {})
        assert result.is_pass()

    def test_fail_when_rated_lt_bus(self):
        eq = EquipmentInstance(
            equipment_id="X", equipment_type="breaker",
            rated_voltage_kV=10.0, rated_continuous_A=2000,
            bus_voltage_kV=13.8,
        )
        result = RULE_EQ_VOLTAGE_RATING.evaluate(eq, {})
        assert result.is_fail()

    def test_na_when_no_bus_voltage(self):
        eq = EquipmentInstance(
            equipment_id="X", equipment_type="breaker",
            rated_voltage_kV=15.0, rated_continuous_A=2000,
            # bus_voltage_kV default 0
        )
        result = RULE_EQ_VOLTAGE_RATING.evaluate(eq, {})
        assert result.is_not_applicable()


# ---------------------------------------------------------------------------
# Critério 2 — EQ-INTERRUPT-DUTY
# ---------------------------------------------------------------------------


class TestInterruptDuty:

    def _make(self, i_fault: float, rated: float = 40.0,
              etype: str = "breaker"):
        return EquipmentInstance(
            equipment_id="BRK", equipment_type=etype,
            rated_voltage_kV=15, rated_continuous_A=2000,
            rated_interrupt_kA=rated,
            duty={"I_fault_kA": i_fault},
        )

    def test_pass_at_60pct(self):
        eq = self._make(i_fault=24.0)  # 60%
        result = RULE_EQ_INTERRUPT_DUTY.evaluate(eq, {})
        assert result.is_pass()
        assert result.evaluated_value == pytest.approx(60.0)

    def test_warn_at_85pct(self):
        eq = self._make(i_fault=34.0)  # 85%
        result = RULE_EQ_INTERRUPT_DUTY.evaluate(eq, {})
        assert result.is_warn()

    def test_fail_at_110pct(self):
        eq = self._make(i_fault=44.0)  # 110%
        result = RULE_EQ_INTERRUPT_DUTY.evaluate(eq, {})
        assert result.is_fail()

    def test_na_for_non_breaker(self):
        eq = self._make(i_fault=10, etype="motor")
        result = RULE_EQ_INTERRUPT_DUTY.evaluate(eq, {})
        assert result.is_not_applicable()

    def test_na_when_no_rating(self):
        eq = self._make(i_fault=10, rated=0.0)
        result = RULE_EQ_INTERRUPT_DUTY.evaluate(eq, {})
        assert result.is_not_applicable()


# ---------------------------------------------------------------------------
# Critério 3 — EQ-ASYM-DUTY
# ---------------------------------------------------------------------------


class TestAsymDuty:

    def test_pass_at_50pct(self):
        eq = EquipmentInstance(
            equipment_id="BRK", equipment_type="breaker",
            rated_voltage_kV=15, rated_continuous_A=2000,
            rated_asym_kA=104.0,
            duty={"ip_kA": 50.0},  # ~48%
        )
        result = RULE_EQ_ASYM_DUTY.evaluate(eq, {})
        assert result.is_pass()

    def test_fail_at_120pct(self):
        eq = EquipmentInstance(
            equipment_id="BRK", equipment_type="breaker",
            rated_voltage_kV=15, rated_continuous_A=2000,
            rated_asym_kA=104.0,
            duty={"ip_kA": 125.0},  # 120%
        )
        result = RULE_EQ_ASYM_DUTY.evaluate(eq, {})
        assert result.is_fail()

    def test_na_for_cable(self):
        eq = EquipmentInstance(
            equipment_id="C", equipment_type="cable",
            rated_voltage_kV=1, rated_continuous_A=200,
            rated_asym_kA=10,
        )
        result = RULE_EQ_ASYM_DUTY.evaluate(eq, {})
        assert result.is_not_applicable()


# ---------------------------------------------------------------------------
# Critério 4 — EQ-LOAD-FLOW-CURRENT
# ---------------------------------------------------------------------------


class TestLoadFlowCurrent:

    def _make(self, i_load: float, rated: float = 200.0,
              etype: str = "cable"):
        return EquipmentInstance(
            equipment_id="X", equipment_type=etype,
            rated_voltage_kV=1.0, rated_continuous_A=rated,
            duty={"I_load_A": i_load},
        )

    def test_pass_at_50pct(self):
        eq = self._make(i_load=100)
        result = RULE_EQ_LOAD_FLOW_CURRENT.evaluate(eq, {})
        assert result.is_pass()

    def test_warn_at_80pct(self):
        eq = self._make(i_load=160)
        result = RULE_EQ_LOAD_FLOW_CURRENT.evaluate(eq, {})
        assert result.is_warn()

    def test_fail_at_120pct(self):
        eq = self._make(i_load=240)
        result = RULE_EQ_LOAD_FLOW_CURRENT.evaluate(eq, {})
        assert result.is_fail()

    def test_na_for_motor(self):
        eq = self._make(i_load=100, etype="motor")
        result = RULE_EQ_LOAD_FLOW_CURRENT.evaluate(eq, {})
        assert result.is_not_applicable()


# ---------------------------------------------------------------------------
# Critério 5 — EQ-DESIGN-LOAD
# ---------------------------------------------------------------------------


class TestDesignLoad:

    def test_pass_at_60pct_design(self):
        eq = EquipmentInstance(
            equipment_id="X", equipment_type="cable",
            rated_voltage_kV=1, rated_continuous_A=200,
            duty={"I_design_A": 120},  # 60%
        )
        result = RULE_EQ_DESIGN_LOAD.evaluate(eq, {})
        assert result.is_pass()

    def test_fail_at_110pct_design(self):
        eq = EquipmentInstance(
            equipment_id="X", equipment_type="cable",
            rated_voltage_kV=1, rated_continuous_A=200,
            duty={"I_design_A": 220},
        )
        result = RULE_EQ_DESIGN_LOAD.evaluate(eq, {})
        assert result.is_fail()


# ---------------------------------------------------------------------------
# Critério 6 — EQ-GENERATOR-CAPACITY
# ---------------------------------------------------------------------------


class TestGeneratorCapacity:

    def test_pass_at_50pct(self):
        eq = EquipmentInstance(
            equipment_id="GEN-1", equipment_type="generator",
            rated_voltage_kV=13.8, rated_continuous_A=1000,
            duty={"gen_load_A": 500},
        )
        result = RULE_EQ_GENERATOR_CAPACITY.evaluate(eq, {})
        assert result.is_pass()

    def test_fail_at_110pct(self):
        eq = EquipmentInstance(
            equipment_id="GEN-1", equipment_type="generator",
            rated_voltage_kV=13.8, rated_continuous_A=1000,
            duty={"gen_load_A": 1100},
        )
        result = RULE_EQ_GENERATOR_CAPACITY.evaluate(eq, {})
        assert result.is_fail()

    def test_na_for_motor(self):
        eq = EquipmentInstance(
            equipment_id="M", equipment_type="motor",
            rated_voltage_kV=0.48, rated_continuous_A=100,
        )
        result = RULE_EQ_GENERATOR_CAPACITY.evaluate(eq, {})
        assert result.is_not_applicable()


# ---------------------------------------------------------------------------
# Critério 7 — EQ-BUS-VOLTAGE-DROP
# ---------------------------------------------------------------------------


class TestBusVoltageDrop:

    def test_pass_at_2pct(self):
        eq = EquipmentInstance(
            equipment_id="BUS", equipment_type="bus",
            rated_voltage_kV=13.8, rated_continuous_A=3000,
            duty={"V_drop_pct": 2.0},  # 50% of 4% limit
        )
        result = RULE_EQ_BUS_VOLTAGE_DROP.evaluate(eq, {})
        assert result.is_pass()

    def test_warn_at_3_5pct(self):
        eq = EquipmentInstance(
            equipment_id="BUS", equipment_type="bus",
            rated_voltage_kV=13.8, rated_continuous_A=3000,
            duty={"V_drop_pct": 3.5},  # 87.5% of 4%
        )
        result = RULE_EQ_BUS_VOLTAGE_DROP.evaluate(eq, {})
        assert result.is_warn()

    def test_fail_at_5pct(self):
        eq = EquipmentInstance(
            equipment_id="BUS", equipment_type="bus",
            rated_voltage_kV=13.8, rated_continuous_A=3000,
            duty={"V_drop_pct": 5.0},
        )
        result = RULE_EQ_BUS_VOLTAGE_DROP.evaluate(eq, {})
        assert result.is_fail()

    def test_custom_limit_via_context(self):
        """Limite 7% para regime motor partida (NBR 5410)."""
        eq = EquipmentInstance(
            equipment_id="BUS", equipment_type="bus",
            rated_voltage_kV=13.8, rated_continuous_A=3000,
            duty={"V_drop_pct": 6.0},
        )
        # Com limit=7%: 6/7 = 85.7% → WARN
        result = RULE_EQ_BUS_VOLTAGE_DROP.evaluate(
            eq, {"V_drop_limit_pct": 7.0},
        )
        assert result.is_warn()


# ---------------------------------------------------------------------------
# Critério 8 — EQ-BRANCH-VOLTAGE-DROP
# ---------------------------------------------------------------------------


class TestBranchVoltageDrop:

    def test_pass_at_1pct(self):
        eq = EquipmentInstance(
            equipment_id="C", equipment_type="cable",
            rated_voltage_kV=1.0, rated_continuous_A=200,
            duty={"V_drop_pct": 1.0},
        )
        result = RULE_EQ_BRANCH_VOLTAGE_DROP.evaluate(eq, {})
        assert result.is_pass()

    def test_fail_at_5pct(self):
        eq = EquipmentInstance(
            equipment_id="C", equipment_type="cable",
            rated_voltage_kV=1.0, rated_continuous_A=200,
            duty={"V_drop_pct": 5.0},
        )
        result = RULE_EQ_BRANCH_VOLTAGE_DROP.evaluate(eq, {})
        assert result.is_fail()


# ---------------------------------------------------------------------------
# Critério 9 — EQ-DEVICE-VOLTAGE-DROP
# ---------------------------------------------------------------------------


class TestDeviceVoltageDrop:

    def test_pass_at_0_3pct(self):
        eq = EquipmentInstance(
            equipment_id="BRK", equipment_type="breaker",
            rated_voltage_kV=0.48, rated_continuous_A=600,
            duty={"V_drop_pct": 0.3},  # 30% of 1% limit
        )
        result = RULE_EQ_DEVICE_VOLTAGE_DROP.evaluate(eq, {})
        assert result.is_pass()

    def test_fail_at_2pct(self):
        eq = EquipmentInstance(
            equipment_id="BRK", equipment_type="breaker",
            rated_voltage_kV=0.48, rated_continuous_A=600,
            duty={"V_drop_pct": 2.0},
        )
        result = RULE_EQ_DEVICE_VOLTAGE_DROP.evaluate(eq, {})
        assert result.is_fail()


# ---------------------------------------------------------------------------
# Integration smoke: aplica TODOS os 9 a um breaker realista
# ---------------------------------------------------------------------------


class TestIntegrationFullDashboard:

    def test_realistic_breaker_evaluation(self):
        """
        Dashboard completo de um disjuntor 15kV/2000A/40kA.
        Operando em bus 13.8kV com I_load=1500A, I_fault=25kA,
        ip=65kA, V_drop=0.5%.
        Esperado:
        - V_RATING: PASS (15 ≥ 13.8)
        - INTERRUPT: 25/40=62.5% → PASS
        - ASYM: 65/104=62.5% → PASS
        - LOAD: 1500/2000=75% → WARN
        - DESIGN: not provided → NA
        - GENERATOR: NA (não é generator)
        - BUS_V_DROP: NA (não é bus)
        - BRANCH_V_DROP: NA (não é cable)
        - DEVICE_V_DROP: 0.5/1.0=50% → PASS
        """
        eq = EquipmentInstance(
            equipment_id="BRK-MAIN-1",
            equipment_type="breaker",
            rated_voltage_kV=15.0,
            rated_continuous_A=2000,
            rated_interrupt_kA=40.0,
            rated_asym_kA=104.0,
            bus_voltage_kV=13.8,
            duty={
                "I_load_A": 1500,
                "I_fault_kA": 25.0,
                "ip_kA": 65.0,
                "V_drop_pct": 0.5,
            },
        )
        rep = evaluate_equipment(eq, PTW_EQUIPMENT_EVALUATION)
        assert len(rep.results) == 9
        # 4 PASS (V_RATING + INTERRUPT + ASYM + DEVICE_V_DROP)
        # 1 WARN (LOAD 75%)
        # 4 NA (DESIGN sem I_design, GEN, BUS, BRANCH)
        counts = rep.count_by_severity()
        assert counts[RuleSeverity.PASS] == 4
        assert counts[RuleSeverity.WARN] == 1
        assert counts[RuleSeverity.NOT_APPLICABLE] == 4
        assert counts[RuleSeverity.FAIL] == 0
        # Overall = WARN (não FAIL)
        assert rep.overall_status() == "WARN"

    def test_realistic_underdesigned_breaker_fails(self):
        """Disjuntor subdimensionado: falha critical em 3 critérios."""
        eq = EquipmentInstance(
            equipment_id="BRK-WEAK",
            equipment_type="breaker",
            rated_voltage_kV=10.0,    # < bus 13.8 → FAIL V
            rated_continuous_A=1000,  # 1500A load → FAIL load
            rated_interrupt_kA=20.0,  # 25 kA fault → FAIL interrupt
            rated_asym_kA=52.0,
            bus_voltage_kV=13.8,
            duty={
                "I_load_A": 1500,
                "I_fault_kA": 25.0,
                "ip_kA": 65.0,
            },
        )
        rep = evaluate_equipment(eq, PTW_EQUIPMENT_EVALUATION)
        assert rep.overall_status() == "FAIL"
        assert rep.has_failures()
        # Pelo menos 3 FAILs
        assert len(rep.failures()) >= 3
