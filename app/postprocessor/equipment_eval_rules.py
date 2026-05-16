"""
app.postprocessor.equipment_eval_rules — 9 critérios PTW
para Equipment Evaluation (v1.3.0 Fase B.2).

Cada critério é uma `Rule` (reusa Fase A.1 framework):
* `applicable_to=(EquipmentInstance,)` — sempre
* `eval_func` retorna PASS/WARN/FAIL/NA com % do rating

Convenção de severity (paleta PTW)
====================================

* `< 70%` → PASS verde (margem confortável)
* `70-100%` → WARN amarelo (margem reduzida)
* `> 100%` → FAIL vermelho (rating excedido — violação)
* falta de dados / inaplicável → NOT_APPLICABLE

9 critérios cobertos
=====================

| # | Rule ID | Equipment | Verifica |
|---|---|---|---|
| 1 | EQ-VOLTAGE-RATING | All | rated_V ≥ bus_V |
| 2 | EQ-INTERRUPT-DUTY | breaker, fuse | I_fault ≤ rated_interrupt |
| 3 | EQ-ASYM-DUTY | breaker | ip ≤ rated_asym |
| 4 | EQ-LOAD-FLOW-CURRENT | cable, breaker | I_load ≤ rated_continuous |
| 5 | EQ-DESIGN-LOAD | cable, breaker | I_design ≤ rated_continuous |
| 6 | EQ-GENERATOR-CAPACITY | generator | gen_load ≤ gen_capacity |
| 7 | EQ-BUS-VOLTAGE-DROP | bus | V_drop ≤ 4% (NBR 5410) |
| 8 | EQ-BRANCH-VOLTAGE-DROP | cable | V_drop_branch ≤ 4% |
| 9 | EQ-DEVICE-VOLTAGE-DROP | breaker | V_drop_device ≤ 1% (típico) |

Cobertura normativa
====================

* IEEE Std 242-2001 §15 (Equipment Evaluation criteria)
* NBR 5410:2004 §6.2.7 (queda de tensão limites)
* IEC 62271-100 (HV breaker ratings)
* ANSI C37.04 (LV breaker ratings)
"""

from __future__ import annotations

from app.postprocessor.coord_rules import (
    Rule, RuleResult, RuleSet, RuleSeverity,
)
from app.postprocessor.equipment_eval import EquipmentInstance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _na(rule_id: str, target_id: str, msg: str, citation: str) -> RuleResult:
    """Atalho para NOT_APPLICABLE."""
    return RuleResult(
        rule_id=rule_id, target_id=target_id,
        severity=RuleSeverity.NOT_APPLICABLE,
        message=msg, citation=citation,
    )


def _severity_from_pct(pct: float, warn_at_pct: float = 70.0) -> RuleSeverity:
    """
    Determina severity por % do rating utilizado.

    Convenção PTW:
    * `< warn_at_pct` (default 70%) → PASS
    * `warn_at_pct ≤ pct ≤ 100%` → WARN
    * `> 100%` → FAIL
    """
    if pct > 100.0:
        return RuleSeverity.FAIL
    if pct >= warn_at_pct:
        return RuleSeverity.WARN
    return RuleSeverity.PASS


# ---------------------------------------------------------------------------
# Critério 1 — Voltage Rating
# ---------------------------------------------------------------------------


def _eval_voltage_rating(target: EquipmentInstance, ctx: dict) -> RuleResult:
    """
    IEEE 242 §15.6.1: equipment rated_voltage DEVE ser ≥ bus_voltage.

    Severity:
    * V_rated ≥ V_bus → PASS
    * V_rated < V_bus → FAIL (subdimensionamento perigoso)

    Não aplicável se bus_voltage_kV = 0 (não fornecido).
    """
    rule_id = "EQ-VOLTAGE-RATING"
    citation = "IEEE 242 §15.6.1 + IEC 62271 / ANSI C37.04"
    tid = target.equipment_id

    if target.bus_voltage_kV <= 0:
        return _na(rule_id, tid, "bus_voltage_kV não fornecido", citation)

    if target.rated_voltage_kV >= target.bus_voltage_kV:
        sev = RuleSeverity.PASS
        msg = (
            f"V_rated={target.rated_voltage_kV} ≥ "
            f"V_bus={target.bus_voltage_kV} kV OK"
        )
    else:
        sev = RuleSeverity.FAIL
        msg = (
            f"V_rated={target.rated_voltage_kV} < "
            f"V_bus={target.bus_voltage_kV} kV — UNDERRATED"
        )

    pct = target.bus_voltage_kV / target.rated_voltage_kV * 100.0 \
        if target.rated_voltage_kV > 0 else 999.0
    return RuleResult(
        rule_id=rule_id, target_id=tid,
        severity=sev, message=msg, citation=citation,
        evaluated_value=pct,
        expected_range=(0.0, 100.0),
    )


# ---------------------------------------------------------------------------
# Critério 2 — Interrupting Fault Duty
# ---------------------------------------------------------------------------


def _eval_interrupt_duty(target: EquipmentInstance, ctx: dict) -> RuleResult:
    """
    IEEE 242 §15.6.2 / ANSI C37.04: I_fault no bus DEVE ser
    ≤ rated_interrupt_kA do disjuntor/fusível.

    Aplicável a breaker e fuse. Outros tipos retornam NA.
    """
    rule_id = "EQ-INTERRUPT-DUTY"
    citation = "IEEE 242 §15.6.2 + ANSI C37.04 / IEC 62271-100"
    tid = target.equipment_id

    if target.equipment_type not in ("breaker", "fuse"):
        return _na(
            rule_id, tid,
            f"tipo {target.equipment_type} não tem interrupt rating",
            citation,
        )
    if target.rated_interrupt_kA <= 0:
        return _na(rule_id, tid, "rated_interrupt_kA não fornecido", citation)

    i_fault = ctx.get("I_fault_kA") or target.duty.get("I_fault_kA")
    if i_fault is None or i_fault <= 0:
        return _na(rule_id, tid, "I_fault_kA não fornecido", citation)

    pct = i_fault / target.rated_interrupt_kA * 100.0
    sev = _severity_from_pct(pct)
    msg = (
        f"I_fault={i_fault:.1f} kA / Interrupt={target.rated_interrupt_kA:.1f} "
        f"kA = {pct:.0f}%"
    )

    return RuleResult(
        rule_id=rule_id, target_id=tid,
        severity=sev, message=msg, citation=citation,
        evaluated_value=pct,
        expected_range=(0.0, 70.0),  # PASS < 70%
    )


# ---------------------------------------------------------------------------
# Critério 3 — Asymmetrical Duty
# ---------------------------------------------------------------------------


def _eval_asym_duty(target: EquipmentInstance, ctx: dict) -> RuleResult:
    """
    ANSI C37.04 / IEEE C37.010: ip (peak) DEVE ser ≤ rated_asym_kA.

    Aplicável a breaker. Outros NA.
    """
    rule_id = "EQ-ASYM-DUTY"
    citation = "ANSI C37.04 + IEEE C37.010"
    tid = target.equipment_id

    if target.equipment_type != "breaker":
        return _na(
            rule_id, tid,
            f"tipo {target.equipment_type} não tem asym rating",
            citation,
        )
    if target.rated_asym_kA <= 0:
        return _na(rule_id, tid, "rated_asym_kA não fornecido", citation)

    ip = ctx.get("ip_kA") or target.duty.get("ip_kA")
    if ip is None or ip <= 0:
        return _na(rule_id, tid, "ip_kA (peak) não fornecido", citation)

    pct = ip / target.rated_asym_kA * 100.0
    sev = _severity_from_pct(pct)
    msg = (
        f"ip={ip:.1f} kA / Asym_rating={target.rated_asym_kA:.1f} kA = "
        f"{pct:.0f}%"
    )

    return RuleResult(
        rule_id=rule_id, target_id=tid,
        severity=sev, message=msg, citation=citation,
        evaluated_value=pct, expected_range=(0.0, 70.0),
    )


# ---------------------------------------------------------------------------
# Critério 4 — Load Flow Current
# ---------------------------------------------------------------------------


def _eval_load_flow_current(target: EquipmentInstance, ctx: dict) -> RuleResult:
    """
    IEEE 242 §15.6.4: I_load DEVE ser ≤ rated_continuous_A.

    Aplicável a cable, breaker, fuse, transformer.
    """
    rule_id = "EQ-LOAD-FLOW-CURRENT"
    citation = "IEEE 242 §15.6.4 + NBR 5410 §6.2"
    tid = target.equipment_id

    if target.equipment_type not in ("cable", "breaker", "fuse", "transformer"):
        return _na(
            rule_id, tid,
            f"tipo {target.equipment_type} não tem continuous rating",
            citation,
        )
    if target.rated_continuous_A <= 0:
        return _na(rule_id, tid, "rated_continuous_A não fornecido", citation)

    i_load = ctx.get("I_load_A") or target.duty.get("I_load_A")
    if i_load is None or i_load <= 0:
        return _na(rule_id, tid, "I_load_A não fornecido", citation)

    pct = i_load / target.rated_continuous_A * 100.0
    sev = _severity_from_pct(pct)
    msg = (
        f"I_load={i_load:.1f} A / Continuous={target.rated_continuous_A:.1f} "
        f"A = {pct:.0f}%"
    )

    return RuleResult(
        rule_id=rule_id, target_id=tid,
        severity=sev, message=msg, citation=citation,
        evaluated_value=pct, expected_range=(0.0, 70.0),
    )


# ---------------------------------------------------------------------------
# Critério 5 — Design Load
# ---------------------------------------------------------------------------


def _eval_design_load(target: EquipmentInstance, ctx: dict) -> RuleResult:
    """
    IEEE 242 §15.6.4: I_design (pico esperado) DEVE ser ≤
    rated_continuous_A. Mais conservador que load flow current.
    """
    rule_id = "EQ-DESIGN-LOAD"
    citation = "IEEE 242 §15.6.4 (design load conservative)"
    tid = target.equipment_id

    if target.equipment_type not in ("cable", "breaker", "transformer"):
        return _na(
            rule_id, tid,
            f"tipo {target.equipment_type} sem design load criterion",
            citation,
        )
    if target.rated_continuous_A <= 0:
        return _na(rule_id, tid, "rated_continuous_A não fornecido", citation)

    i_design = ctx.get("I_design_A") or target.duty.get("I_design_A")
    if i_design is None or i_design <= 0:
        return _na(rule_id, tid, "I_design_A não fornecido", citation)

    pct = i_design / target.rated_continuous_A * 100.0
    sev = _severity_from_pct(pct)
    msg = (
        f"I_design={i_design:.1f} A / Continuous={target.rated_continuous_A:.1f}"
        f" A = {pct:.0f}%"
    )

    return RuleResult(
        rule_id=rule_id, target_id=tid,
        severity=sev, message=msg, citation=citation,
        evaluated_value=pct, expected_range=(0.0, 70.0),
    )


# ---------------------------------------------------------------------------
# Critério 6 — Generator Capacity
# ---------------------------------------------------------------------------


def _eval_generator_capacity(target: EquipmentInstance, ctx: dict) -> RuleResult:
    """
    IEEE 242 §15.6.5: gen_load (carga atual atendida) DEVE ser
    ≤ rated_continuous_A do gerador.
    """
    rule_id = "EQ-GENERATOR-CAPACITY"
    citation = "IEEE 242 §15.6.5 + NEMA MG-1"
    tid = target.equipment_id

    if target.equipment_type != "generator":
        return _na(rule_id, tid, "tipo não é generator", citation)
    if target.rated_continuous_A <= 0:
        return _na(rule_id, tid, "rated_continuous_A não fornecido", citation)

    gen_load = ctx.get("gen_load_A") or target.duty.get("gen_load_A")
    if gen_load is None or gen_load <= 0:
        return _na(rule_id, tid, "gen_load_A não fornecido", citation)

    pct = gen_load / target.rated_continuous_A * 100.0
    sev = _severity_from_pct(pct)
    msg = (
        f"gen_load={gen_load:.1f} A / Capacity={target.rated_continuous_A:.1f}"
        f" A = {pct:.0f}%"
    )

    return RuleResult(
        rule_id=rule_id, target_id=tid,
        severity=sev, message=msg, citation=citation,
        evaluated_value=pct, expected_range=(0.0, 70.0),
    )


# ---------------------------------------------------------------------------
# Critérios 7-9 — Voltage Drop family (NBR 5410 §6.2.7)
# ---------------------------------------------------------------------------


def _eval_bus_voltage_drop(target: EquipmentInstance, ctx: dict) -> RuleResult:
    """
    NBR 5410 §6.2.7: V_drop no bus DEVE ser ≤ 4% (regime
    permanente) / 7% (motor partida) / 10% (iluminação).

    Default verifica regime permanente 4%.
    """
    rule_id = "EQ-BUS-VOLTAGE-DROP"
    citation = "NBR 5410:2004 §6.2.7"
    tid = target.equipment_id

    if target.equipment_type != "bus":
        return _na(rule_id, tid, "tipo não é bus", citation)

    v_drop = ctx.get("V_drop_pct") or target.duty.get("V_drop_pct")
    if v_drop is None:
        return _na(rule_id, tid, "V_drop_pct não fornecido", citation)

    limit = ctx.get("V_drop_limit_pct", 4.0)
    pct = v_drop / limit * 100.0
    sev = _severity_from_pct(pct)
    msg = f"V_drop={v_drop:.2f}% / Limit={limit:.1f}% = {pct:.0f}%"

    return RuleResult(
        rule_id=rule_id, target_id=tid,
        severity=sev, message=msg, citation=citation,
        evaluated_value=v_drop, expected_range=(0.0, limit),
    )


def _eval_branch_voltage_drop(target: EquipmentInstance, ctx: dict) -> RuleResult:
    """NBR 5410 §6.2.7 aplicado a cable (branch)."""
    rule_id = "EQ-BRANCH-VOLTAGE-DROP"
    citation = "NBR 5410:2004 §6.2.7"
    tid = target.equipment_id

    if target.equipment_type != "cable":
        return _na(rule_id, tid, "tipo não é cable", citation)

    v_drop = ctx.get("V_drop_pct") or target.duty.get("V_drop_pct")
    if v_drop is None:
        return _na(rule_id, tid, "V_drop_pct não fornecido", citation)

    limit = ctx.get("V_drop_limit_pct", 4.0)
    pct = v_drop / limit * 100.0
    sev = _severity_from_pct(pct)
    msg = f"V_drop_branch={v_drop:.2f}% / Limit={limit:.1f}% = {pct:.0f}%"

    return RuleResult(
        rule_id=rule_id, target_id=tid,
        severity=sev, message=msg, citation=citation,
        evaluated_value=v_drop, expected_range=(0.0, limit),
    )


def _eval_device_voltage_drop(target: EquipmentInstance, ctx: dict) -> RuleResult:
    """
    Best Practice: V_drop em device (breaker, contactor)
    deve ser ≤ 1% (típico para LV switchgear).
    """
    rule_id = "EQ-DEVICE-VOLTAGE-DROP"
    citation = "Best Practice (LV device V-drop ≤ 1%)"
    tid = target.equipment_id

    if target.equipment_type not in ("breaker", "contactor", "fuse"):
        return _na(
            rule_id, tid,
            f"tipo {target.equipment_type} sem device V-drop criterion",
            citation,
        )

    v_drop = ctx.get("V_drop_pct") or target.duty.get("V_drop_pct")
    if v_drop is None:
        return _na(rule_id, tid, "V_drop_pct não fornecido", citation)

    limit = ctx.get("V_drop_device_limit_pct", 1.0)
    pct = v_drop / limit * 100.0
    sev = _severity_from_pct(pct)
    msg = f"V_drop_device={v_drop:.2f}% / Limit={limit:.1f}% = {pct:.0f}%"

    return RuleResult(
        rule_id=rule_id, target_id=tid,
        severity=sev, message=msg, citation=citation,
        evaluated_value=v_drop, expected_range=(0.0, limit),
    )


# ---------------------------------------------------------------------------
# Rule objects
# ---------------------------------------------------------------------------


RULE_EQ_VOLTAGE_RATING = Rule(
    rule_id="EQ-VOLTAGE-RATING",
    description="V rating ≥ V bus (IEEE 242 §15.6.1)",
    citation="IEEE 242 §15.6.1 + IEC 62271 / ANSI C37.04",
    applicable_to=(EquipmentInstance,),
    eval_func=_eval_voltage_rating,
)

RULE_EQ_INTERRUPT_DUTY = Rule(
    rule_id="EQ-INTERRUPT-DUTY",
    description="I_fault ≤ Interrupt rating (ANSI C37.04)",
    citation="IEEE 242 §15.6.2 + ANSI C37.04 / IEC 62271-100",
    applicable_to=(EquipmentInstance,),
    eval_func=_eval_interrupt_duty,
)

RULE_EQ_ASYM_DUTY = Rule(
    rule_id="EQ-ASYM-DUTY",
    description="ip ≤ Asym rating (ANSI C37.04)",
    citation="ANSI C37.04 + IEEE C37.010",
    applicable_to=(EquipmentInstance,),
    eval_func=_eval_asym_duty,
)

RULE_EQ_LOAD_FLOW_CURRENT = Rule(
    rule_id="EQ-LOAD-FLOW-CURRENT",
    description="I_load ≤ Continuous rating (IEEE 242 §15.6.4)",
    citation="IEEE 242 §15.6.4 + NBR 5410 §6.2",
    applicable_to=(EquipmentInstance,),
    eval_func=_eval_load_flow_current,
)

RULE_EQ_DESIGN_LOAD = Rule(
    rule_id="EQ-DESIGN-LOAD",
    description="I_design ≤ Continuous rating (conservative)",
    citation="IEEE 242 §15.6.4 (design load)",
    applicable_to=(EquipmentInstance,),
    eval_func=_eval_design_load,
)

RULE_EQ_GENERATOR_CAPACITY = Rule(
    rule_id="EQ-GENERATOR-CAPACITY",
    description="gen_load ≤ Capacity (IEEE 242 §15.6.5)",
    citation="IEEE 242 §15.6.5 + NEMA MG-1",
    applicable_to=(EquipmentInstance,),
    eval_func=_eval_generator_capacity,
)

RULE_EQ_BUS_VOLTAGE_DROP = Rule(
    rule_id="EQ-BUS-VOLTAGE-DROP",
    description="V_drop ≤ 4% (NBR 5410 §6.2.7)",
    citation="NBR 5410:2004 §6.2.7",
    applicable_to=(EquipmentInstance,),
    eval_func=_eval_bus_voltage_drop,
)

RULE_EQ_BRANCH_VOLTAGE_DROP = Rule(
    rule_id="EQ-BRANCH-VOLTAGE-DROP",
    description="V_drop_branch ≤ 4% (NBR 5410)",
    citation="NBR 5410:2004 §6.2.7",
    applicable_to=(EquipmentInstance,),
    eval_func=_eval_branch_voltage_drop,
)

RULE_EQ_DEVICE_VOLTAGE_DROP = Rule(
    rule_id="EQ-DEVICE-VOLTAGE-DROP",
    description="V_drop em device ≤ 1% (Best Practice LV)",
    citation="Best Practice (LV device V-drop ≤ 1%)",
    applicable_to=(EquipmentInstance,),
    eval_func=_eval_device_voltage_drop,
)


# ---------------------------------------------------------------------------
# RuleSet consolidado: 9 critérios PTW
# ---------------------------------------------------------------------------


PTW_EQUIPMENT_EVALUATION = RuleSet(
    name="PTW-style Equipment Evaluation (9 criteria)",
    norm_reference="IEEE 242 §15 + NBR 5410 §6.2.7 + ANSI C37.04",
    rules=(
        RULE_EQ_VOLTAGE_RATING,
        RULE_EQ_INTERRUPT_DUTY,
        RULE_EQ_ASYM_DUTY,
        RULE_EQ_LOAD_FLOW_CURRENT,
        RULE_EQ_DESIGN_LOAD,
        RULE_EQ_GENERATOR_CAPACITY,
        RULE_EQ_BUS_VOLTAGE_DROP,
        RULE_EQ_BRANCH_VOLTAGE_DROP,
        RULE_EQ_DEVICE_VOLTAGE_DROP,
    ),
)


# Lista dos 9 critérios para introspecção / iteração
ALL_PTW_EQUIPMENT_RULES = list(PTW_EQUIPMENT_EVALUATION.rules)
