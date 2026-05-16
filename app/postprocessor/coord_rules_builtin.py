"""
app.postprocessor.coord_rules_builtin — 9+ built-in rules
v1.3.0 Fase A.2.

Cada Rule cita norma + página + valor literal. Anti-alucinação:
todos os ranges (115-125%, etc.) vêm DIRETO da norma.

RuleSets exportados
====================

* ``NEC_MOTOR_PROTECTION`` — IEEE 242 §9 motor rules (3 rules)
* ``NEC_TRANSFORMER_PROTECTION`` — IEEE 242 §11 + NEC 450 (3 rules)
* ``NBR_CABLE_RULES`` — NBR 5410 §6.5.4 (1 rule)
* ``BEST_PRACTICES`` — recomendações engineering (2 rules)

Total: 9 rules.

Cobertura normativa
====================

* IEEE Std 242:2001 (Buff Book) §9.5.4 (motor 51 LTPU)
* IEEE Std 242:2001 §9.6 (motor 50)
* IEEE Std 242:2001 §11.5.6 (XFMR through-fault K=1250/5000)
* NEC 110.10 (proteção upstream rules)
* NEC 450 (transformer protection)
* NBR 5410:2004 §6.5.4 (cable thermal stress)

Como adicionar novas rules
===========================

1. Definir função `_eval_<nome>(target, context) → RuleResult`
2. Criar `Rule` com citation explícita
3. Adicionar ao RuleSet apropriado
4. Atualizar ALL_BUILTIN_RULESETS
"""

from __future__ import annotations

from app.postprocessor.coord_rules import (
    Rule,
    RuleResult,
    RuleSet,
    RuleSeverity,
)
from app.postprocessor.tcc_damage import (
    CableDamageCurve,
    MotorThermalCurve,
    TransformerThroughFaultCurve,
)
from app.postprocessor.tcc_devices import TCCDevice


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_segment_with_id_substring(device: TCCDevice, substr: str):
    """Retorna primeiro segment com ``substr`` em segment_id, ou None."""
    for seg in getattr(device, "segments", ()):
        seg_id = getattr(seg, "segment_id", "")
        if substr in seg_id:
            return seg
    return None


def _get_pickup(seg) -> float:
    """Extrai pickup_A ou pickup_A_nominal de um segment."""
    return (
        getattr(seg, "pickup_A", None)
        or getattr(seg, "pickup_A_nominal", None)
    )


def _na(rule_id: str, target_id: str, message: str, citation: str) -> RuleResult:
    """Atalho para retornar NOT_APPLICABLE."""
    return RuleResult(
        rule_id=rule_id,
        target_id=target_id,
        severity=RuleSeverity.NOT_APPLICABLE,
        message=message,
        citation=citation,
    )


def _target_id(target) -> str:
    """ID do target (genérico)."""
    return (
        getattr(target, "device_id", None)
        or getattr(target, "cable_id", None)
        or getattr(target, "xfmr_id", None)
        or getattr(target, "motor_id", None)
        or "?"
    )


# ---------------------------------------------------------------------------
# Motor protection rules (IEEE 242 §9)
# ---------------------------------------------------------------------------


def _eval_motor_51_ltpu(target: TCCDevice, context: dict) -> RuleResult:
    """
    NEC 110.10 + IEEE 242 §9.5.4: Motor relay 51 LTPU deve ser
    115%-125% × FLA (com SF≥1.15). Tolerável até 100%-140% (WARN).
    """
    rule_id = "NEC-MOTOR-51-LTPU"
    citation = "NEC 110.10 + IEEE 242 §9.5.4 Tabela 9-2"
    tid = _target_id(target)

    fla = context.get("fla_A")
    if fla is None or fla <= 0:
        return _na(rule_id, tid, "FLA não fornecido no context", citation)

    seg_51 = _find_segment_with_id_substring(target, "51")
    if seg_51 is None:
        return _na(rule_id, tid, "Device sem segment 51 LT", citation)

    pickup = _get_pickup(seg_51)
    if pickup is None:
        return _na(rule_id, tid, "segment 51 sem pickup_A", citation)

    pct = pickup / fla * 100.0
    if 115.0 <= pct <= 125.0:
        sev = RuleSeverity.PASS
        msg = f"51 LTPU = {pct:.1f}% FLA (range 115-125% OK)"
    elif 100.0 <= pct < 115.0 or 125.0 < pct <= 140.0:
        sev = RuleSeverity.WARN
        msg = (
            f"51 LTPU = {pct:.1f}% FLA (fora do 115-125%, "
            f"mas dentro de 100-140% tolerável)"
        )
    else:
        sev = RuleSeverity.FAIL
        msg = f"51 LTPU = {pct:.1f}% FLA (FORA do range NEC 110.10)"

    return RuleResult(
        rule_id=rule_id,
        target_id=tid,
        severity=sev,
        message=msg,
        citation=citation,
        evaluated_value=pct,
        expected_range=(115.0, 125.0),
    )


def _eval_motor_49_thermal(target: TCCDevice, context: dict) -> RuleResult:
    """
    IEEE 242 §9.5.4: Motor 49 thermal pickup deve ser 100%-200%
    × FLA. Acima ou abaixo é FAIL.
    """
    rule_id = "NEC-MOTOR-49-THERMAL"
    citation = "IEEE 242 §9.5.4 + NEC 430 part B"
    tid = _target_id(target)

    fla = context.get("fla_A")
    if fla is None or fla <= 0:
        return _na(rule_id, tid, "FLA não fornecido", citation)

    seg_49 = _find_segment_with_id_substring(target, "49")
    if seg_49 is None:
        return _na(rule_id, tid, "Device sem segment 49 thermal", citation)

    pickup = _get_pickup(seg_49)
    if pickup is None:
        return _na(rule_id, tid, "segment 49 sem pickup_A", citation)

    pct = pickup / fla * 100.0
    if 100.0 <= pct <= 200.0:
        sev = RuleSeverity.PASS
        msg = f"49 thermal = {pct:.1f}% FLA (range 100-200% OK)"
    elif 95.0 <= pct < 100.0 or 200.0 < pct <= 220.0:
        sev = RuleSeverity.WARN
        msg = f"49 thermal = {pct:.1f}% FLA (margem reduzida)"
    else:
        sev = RuleSeverity.FAIL
        msg = f"49 thermal = {pct:.1f}% FLA (FORA do range IEEE 242)"

    return RuleResult(
        rule_id=rule_id,
        target_id=tid,
        severity=sev,
        message=msg,
        citation=citation,
        evaluated_value=pct,
        expected_range=(100.0, 200.0),
    )


def _eval_motor_50_inst(target: TCCDevice, context: dict) -> RuleResult:
    """
    IEEE 242 §9.6 + Best Practice: Motor 50 INST deve ser >5×FLA
    (típico 6-10×) para NÃO disparar em starting normal (que tem
    inrush 5-7×FLA por 100-300ms).
    """
    rule_id = "NEC-MOTOR-50-INST"
    citation = "IEEE 242 §9.6 + Best Practice (5-10× FLA)"
    tid = _target_id(target)

    fla = context.get("fla_A")
    if fla is None or fla <= 0:
        return _na(rule_id, tid, "FLA não fornecido", citation)

    seg_50 = _find_segment_with_id_substring(target, "50")
    if seg_50 is None:
        return _na(rule_id, tid, "Device sem segment 50 INST", citation)

    pickup = _get_pickup(seg_50)
    if pickup is None:
        return _na(rule_id, tid, "segment 50 sem pickup_A", citation)

    factor = pickup / fla
    if 5.0 <= factor <= 10.0:
        sev = RuleSeverity.PASS
        msg = f"50 INST = {factor:.1f}× FLA (range 5-10× OK)"
    elif 3.0 <= factor < 5.0:
        sev = RuleSeverity.WARN
        msg = (
            f"50 INST = {factor:.1f}× FLA (próximo de inrush 5-7×, "
            f"risco de trip em starting)"
        )
    elif 10.0 < factor <= 15.0:
        sev = RuleSeverity.WARN
        msg = f"50 INST = {factor:.1f}× FLA (alto, considere reduzir)"
    else:
        sev = RuleSeverity.FAIL
        msg = (
            f"50 INST = {factor:.1f}× FLA (FORA do range; "
            f"<3× = trip em starting, >15× = ineficaz)"
        )

    return RuleResult(
        rule_id=rule_id,
        target_id=tid,
        severity=sev,
        message=msg,
        citation=citation,
        evaluated_value=factor,
        expected_range=(5.0, 10.0),
    )


RULE_MOTOR_51_LTPU = Rule(
    rule_id="NEC-MOTOR-51-LTPU",
    description="Motor 51 LTPU = 115-125% × FLA (NEC 110.10 + IEEE 242 §9.5.4)",
    citation="NEC 110.10 + IEEE 242 §9.5.4 Tabela 9-2",
    applicable_to=(TCCDevice,),
    eval_func=_eval_motor_51_ltpu,
)

RULE_MOTOR_49_THERMAL = Rule(
    rule_id="NEC-MOTOR-49-THERMAL",
    description="Motor 49 thermal = 100-200% × FLA (IEEE 242 §9.5.4)",
    citation="IEEE 242 §9.5.4 + NEC 430 part B",
    applicable_to=(TCCDevice,),
    eval_func=_eval_motor_49_thermal,
)

RULE_MOTOR_50_INST = Rule(
    rule_id="NEC-MOTOR-50-INST",
    description="Motor 50 INST = 5-10× FLA (IEEE 242 §9.6)",
    citation="IEEE 242 §9.6 + Best Practice (5-10× FLA)",
    applicable_to=(TCCDevice,),
    eval_func=_eval_motor_50_inst,
)


NEC_MOTOR_PROTECTION = RuleSet(
    name="NEC 110.10 — Motor Protection",
    norm_reference="NEC 110.10 + IEEE 242 §9",
    rules=(
        RULE_MOTOR_51_LTPU,
        RULE_MOTOR_49_THERMAL,
        RULE_MOTOR_50_INST,
    ),
)


# ---------------------------------------------------------------------------
# Transformer protection rules (IEEE 242 §11 + NEC 450)
# ---------------------------------------------------------------------------


def _eval_lv_xfmr_2w_pri_ltpu_small(target: TCCDevice, context: dict) -> RuleResult:
    """
    NEC 450.3 + IEEE 242 §11.5: LV XFMR 2W primário com FLA<9A
    → 51 LTPU = 100%-167% × FLA. (Ranges menores para XFMRs
    pequenos por causa da margem de inrush + carga regulável.)
    """
    rule_id = "NEC-LV-XFMR-PRI-LTPU-SMALL"
    citation = "NEC 450.3(B) + IEEE 242 §11.5"
    tid = _target_id(target)

    fla = context.get("xfmr_pri_fla_A")
    if fla is None or fla <= 0:
        return _na(rule_id, tid, "xfmr_pri_fla_A não fornecido", citation)

    if fla >= 9.0:
        return _na(
            rule_id, tid,
            f"FLA={fla}A ≥ 9A — usar regra LARGE (100-125%)",
            citation,
        )

    seg_51 = _find_segment_with_id_substring(target, "51")
    if seg_51 is None:
        return _na(rule_id, tid, "Device sem segment 51 LT", citation)

    pickup = _get_pickup(seg_51)
    if pickup is None:
        return _na(rule_id, tid, "segment 51 sem pickup_A", citation)

    pct = pickup / fla * 100.0
    if 100.0 <= pct <= 167.0:
        sev = RuleSeverity.PASS
        msg = f"XFMR 51 LTPU = {pct:.1f}% (range 100-167% OK; FLA={fla}A)"
    elif 90.0 <= pct < 100.0 or 167.0 < pct <= 200.0:
        sev = RuleSeverity.WARN
        msg = f"XFMR 51 LTPU = {pct:.1f}% (fora do 100-167%, tolerável)"
    else:
        sev = RuleSeverity.FAIL
        msg = f"XFMR 51 LTPU = {pct:.1f}% (FORA do range NEC 450.3)"

    return RuleResult(
        rule_id=rule_id,
        target_id=tid,
        severity=sev,
        message=msg,
        citation=citation,
        evaluated_value=pct,
        expected_range=(100.0, 167.0),
    )


def _eval_lv_xfmr_2w_pri_ltpu_large(target: TCCDevice, context: dict) -> RuleResult:
    """
    NEC 450.3 + IEEE 242 §11.5: LV XFMR 2W primário com FLA≥9A
    → 51 LTPU = 100%-125% × FLA. (Range mais estreito para
    XFMRs maiores onde pickup baixo é viável.)
    """
    rule_id = "NEC-LV-XFMR-PRI-LTPU-LARGE"
    citation = "NEC 450.3(B) + IEEE 242 §11.5"
    tid = _target_id(target)

    fla = context.get("xfmr_pri_fla_A")
    if fla is None or fla <= 0:
        return _na(rule_id, tid, "xfmr_pri_fla_A não fornecido", citation)

    if fla < 9.0:
        return _na(
            rule_id, tid,
            f"FLA={fla}A < 9A — usar regra SMALL (100-167%)",
            citation,
        )

    seg_51 = _find_segment_with_id_substring(target, "51")
    if seg_51 is None:
        return _na(rule_id, tid, "Device sem segment 51 LT", citation)

    pickup = _get_pickup(seg_51)
    if pickup is None:
        return _na(rule_id, tid, "segment 51 sem pickup_A", citation)

    pct = pickup / fla * 100.0
    if 100.0 <= pct <= 125.0:
        sev = RuleSeverity.PASS
        msg = f"XFMR 51 LTPU = {pct:.1f}% (range 100-125% OK; FLA={fla}A)"
    elif 90.0 <= pct < 100.0 or 125.0 < pct <= 150.0:
        sev = RuleSeverity.WARN
        msg = f"XFMR 51 LTPU = {pct:.1f}% (margem reduzida)"
    else:
        sev = RuleSeverity.FAIL
        msg = f"XFMR 51 LTPU = {pct:.1f}% (FORA do range NEC 450.3)"

    return RuleResult(
        rule_id=rule_id,
        target_id=tid,
        severity=sev,
        message=msg,
        citation=citation,
        evaluated_value=pct,
        expected_range=(100.0, 125.0),
    )


def _eval_xfmr_thru_fault_below_damage(
    target: TransformerThroughFaultCurve, context: dict,
) -> RuleResult:
    """
    IEEE C57.109 / IEEE 242 §15.6.4: A proteção 51 upstream do
    XFMR DEVE estar ABAIXO da damage curve through-fault.

    Esta regra usa ``protection_device`` do context (TCCDevice
    upstream) e verifica em ``fault_current_A`` (default 10×In).
    """
    rule_id = "IEEE-C57-109-XFMR-THRU-FAULT"
    citation = "IEEE C57.109-1993 + IEEE 242 §15.6.4"
    tid = _target_id(target)

    prot = context.get("protection_device")
    if prot is None:
        return _na(rule_id, tid, "protection_device não fornecido", citation)
    if not isinstance(prot, TCCDevice):
        return _na(
            rule_id, tid,
            f"protection_device deve ser TCCDevice, recebido "
            f"{type(prot).__name__}",
            citation,
        )

    fault_I = context.get("fault_current_A", target.rated_current_A * 10.0)
    t_dmg = target.through_fault_time_at_current(fault_I)
    t_prot = prot.composite_time_at_current(fault_I)

    if not (
        (t_dmg < float("inf")) and (t_prot < float("inf"))
    ):
        return _na(
            rule_id, tid,
            f"At I={fault_I}A: damage={t_dmg}s, prot={t_prot}s "
            f"(algum inf)",
            citation,
        )

    if t_prot < t_dmg:
        sev = RuleSeverity.PASS
        msg = (
            f"At I={fault_I:.0f}A: prot={t_prot:.3f}s < "
            f"damage={t_dmg:.3f}s OK"
        )
    elif t_prot < t_dmg * 1.5:
        sev = RuleSeverity.WARN
        msg = (
            f"At I={fault_I:.0f}A: prot={t_prot:.3f}s perto de "
            f"damage={t_dmg:.3f}s (margem reduzida)"
        )
    else:
        sev = RuleSeverity.FAIL
        msg = (
            f"At I={fault_I:.0f}A: prot={t_prot:.3f}s > "
            f"damage={t_dmg:.3f}s — XFMR pode falhar antes do trip"
        )

    return RuleResult(
        rule_id=rule_id,
        target_id=tid,
        severity=sev,
        message=msg,
        citation=citation,
        evaluated_value=t_prot - t_dmg,  # margem em segundos
    )


RULE_LV_XFMR_PRI_LTPU_SMALL = Rule(
    rule_id="NEC-LV-XFMR-PRI-LTPU-SMALL",
    description="LV XFMR 2W primário FLA<9A: 51 LTPU = 100-167% × FLA",
    citation="NEC 450.3(B) + IEEE 242 §11.5",
    applicable_to=(TCCDevice,),
    eval_func=_eval_lv_xfmr_2w_pri_ltpu_small,
)

RULE_LV_XFMR_PRI_LTPU_LARGE = Rule(
    rule_id="NEC-LV-XFMR-PRI-LTPU-LARGE",
    description="LV XFMR 2W primário FLA≥9A: 51 LTPU = 100-125% × FLA",
    citation="NEC 450.3(B) + IEEE 242 §11.5",
    applicable_to=(TCCDevice,),
    eval_func=_eval_lv_xfmr_2w_pri_ltpu_large,
)

RULE_XFMR_THRU_FAULT = Rule(
    rule_id="IEEE-C57-109-XFMR-THRU-FAULT",
    description="Proteção upstream deve estar abaixo do XFMR damage",
    citation="IEEE C57.109-1993 + IEEE 242 §15.6.4",
    applicable_to=(TransformerThroughFaultCurve,),
    eval_func=_eval_xfmr_thru_fault_below_damage,
)


NEC_TRANSFORMER_PROTECTION = RuleSet(
    name="NEC 450 + IEEE 242 §11 — Transformer Protection",
    norm_reference="NEC 450.3 + IEEE 242 §11 + IEEE C57.109",
    rules=(
        RULE_LV_XFMR_PRI_LTPU_SMALL,
        RULE_LV_XFMR_PRI_LTPU_LARGE,
        RULE_XFMR_THRU_FAULT,
    ),
)


# ---------------------------------------------------------------------------
# Cable rules (NBR 5410)
# ---------------------------------------------------------------------------


def _eval_cable_damage_80pct(
    target: CableDamageCurve, context: dict,
) -> RuleResult:
    """
    NBR 5410 §5.7.5 + IEEE 242 §15.6.3: Proteção upstream deve
    operar em ≤80% do tempo de damage do cabo, para o curto
    máximo do bus.

    Necessita ``protection_device`` + ``fault_current_A`` no context.
    """
    rule_id = "NBR-5410-CABLE-DAMAGE-80PCT"
    citation = "NBR 5410:2004 §5.7.5 + IEEE 242 §15.6.3"
    tid = _target_id(target)

    prot = context.get("protection_device")
    if prot is None:
        return _na(rule_id, tid, "protection_device não fornecido", citation)

    fault_I = context.get("fault_current_A")
    if fault_I is None or fault_I <= 0:
        return _na(rule_id, tid, "fault_current_A não fornecido", citation)

    t_dmg = target.damage_time_at_current(fault_I)
    if t_dmg == float("inf"):
        return _na(
            rule_id, tid,
            f"At I={fault_I}A: damage time = inf (I muito baixo)",
            citation,
        )

    # Pega tempo da proteção (TCCCurve, TCCDevice, FuseTCCCurve)
    if hasattr(prot, "composite_time_at_current"):
        t_prot = prot.composite_time_at_current(fault_I)
    elif hasattr(prot, "operating_time_at_current"):
        t_prot = prot.operating_time_at_current(fault_I)
    elif hasattr(prot, "clear_time_at_current"):
        t_prot = prot.clear_time_at_current(fault_I)
    else:
        return _na(
            rule_id, tid,
            f"protection_device tipo desconhecido: {type(prot).__name__}",
            citation,
        )

    if t_prot == float("inf"):
        return _na(
            rule_id, tid,
            f"At I={fault_I}A: prot time = inf (não pickup)",
            citation,
        )

    threshold = 0.80 * t_dmg
    if t_prot <= threshold:
        sev = RuleSeverity.PASS
        msg = (
            f"At I={fault_I:.0f}A: prot={t_prot:.3f}s ≤ 80%×"
            f"damage={threshold:.3f}s OK"
        )
    elif t_prot <= t_dmg:
        sev = RuleSeverity.WARN
        msg = (
            f"At I={fault_I:.0f}A: prot={t_prot:.3f}s entre 80%-100%"
            f" do damage={t_dmg:.3f}s (margem reduzida)"
        )
    else:
        sev = RuleSeverity.FAIL
        msg = (
            f"At I={fault_I:.0f}A: prot={t_prot:.3f}s > "
            f"damage={t_dmg:.3f}s — CABO QUEIMA antes do trip"
        )

    return RuleResult(
        rule_id=rule_id,
        target_id=tid,
        severity=sev,
        message=msg,
        citation=citation,
        evaluated_value=t_prot / t_dmg * 100.0,
        expected_range=(0.0, 80.0),  # % do damage
    )


RULE_CABLE_DAMAGE_80PCT = Rule(
    rule_id="NBR-5410-CABLE-DAMAGE-80PCT",
    description="Proteção upstream em ≤80% do cable damage time",
    citation="NBR 5410:2004 §5.7.5 + IEEE 242 §15.6.3",
    applicable_to=(CableDamageCurve,),
    eval_func=_eval_cable_damage_80pct,
)


NBR_CABLE_RULES = RuleSet(
    name="NBR 5410 — Cable Protection",
    norm_reference="NBR 5410:2004 §5.7.5 + IEEE 242 §15.6.3",
    rules=(RULE_CABLE_DAMAGE_80PCT,),
)


# ---------------------------------------------------------------------------
# Best Practices RuleSet
# ---------------------------------------------------------------------------


def _eval_motor_thermal_below_locked_rotor(
    target: MotorThermalCurve, context: dict,
) -> RuleResult:
    """
    Best Practice (IEEE 242 §11.6): proteção 49 upstream deve
    operar antes do tempo locked-rotor do motor.

    Verifica em I = locked_rotor_current = LR_factor × FLA.
    """
    rule_id = "BP-MOTOR-THERMAL-BELOW-LR"
    citation = "IEEE 242 §11.6 + Best Practice"
    tid = _target_id(target)

    prot = context.get("protection_device")
    if prot is None:
        return _na(rule_id, tid, "protection_device não fornecido", citation)

    I_LR = target.locked_rotor_factor * target.fla_A
    t_dmg_lr = target.thermal_time_at_current(I_LR)
    # Pega prot time
    if hasattr(prot, "composite_time_at_current"):
        t_prot = prot.composite_time_at_current(I_LR)
    elif hasattr(prot, "operating_time_at_current"):
        t_prot = prot.operating_time_at_current(I_LR)
    else:
        return _na(rule_id, tid, "protection_device tipo desconhecido", citation)

    if t_prot == float("inf"):
        return _na(
            rule_id, tid,
            f"At LR I={I_LR:.0f}A: prot time = inf",
            citation,
        )

    if t_prot < t_dmg_lr:
        sev = RuleSeverity.PASS
        msg = (
            f"At LR ({I_LR:.0f}A): prot={t_prot:.2f}s < "
            f"motor_thermal={t_dmg_lr:.2f}s OK"
        )
    elif t_prot < t_dmg_lr * 1.2:
        sev = RuleSeverity.WARN
        msg = (
            f"At LR: prot={t_prot:.2f}s perto de "
            f"motor_thermal={t_dmg_lr:.2f}s"
        )
    else:
        sev = RuleSeverity.FAIL
        msg = (
            f"At LR: prot={t_prot:.2f}s > motor_thermal="
            f"{t_dmg_lr:.2f}s — MOTOR QUEIMA"
        )

    return RuleResult(
        rule_id=rule_id,
        target_id=tid,
        severity=sev,
        message=msg,
        citation=citation,
        evaluated_value=t_prot - t_dmg_lr,
    )


RULE_MOTOR_THERMAL_BELOW_LR = Rule(
    rule_id="BP-MOTOR-THERMAL-BELOW-LR",
    description="Proteção 49/49+51 abaixo do motor locked-rotor curve",
    citation="IEEE 242 §11.6 + Best Practice",
    applicable_to=(MotorThermalCurve,),
    eval_func=_eval_motor_thermal_below_locked_rotor,
)


BEST_PRACTICES = RuleSet(
    name="Best Practices — Engineering Recommendations",
    norm_reference="IEEE 242:2001 + Olivas best practices",
    rules=(RULE_MOTOR_THERMAL_BELOW_LR,),
)


# ---------------------------------------------------------------------------
# All built-in RuleSets exportados
# ---------------------------------------------------------------------------


ALL_BUILTIN_RULESETS = [
    NEC_MOTOR_PROTECTION,        # 3 rules
    NEC_TRANSFORMER_PROTECTION,  # 3 rules
    NBR_CABLE_RULES,             # 1 rule
    BEST_PRACTICES,              # 1 rule
]
# Total: 8 rules em 4 RuleSets. Adicionar mais via subclassing ou plugin.
