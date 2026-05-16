"""
app.postprocessor.equipment_eval — Equipment Evaluation
data model (v1.3.0 Fase B.1 — paridade SKM PTW Equipment Eval).

Filosofia
==========

PTW Power*Tools "Equipment Evaluation" gera dashboard tabular
único com 9 critérios automáticos por equipamento:

* Voltage Rating vs Bus
* Interrupting Fault Duty vs Rating
* Asymmetrical Duty vs Asym Rating
* Load Flow Current vs Continuous Rating
* Design Load vs Continuous
* Generator Capacity vs Load Flow
* Bus Voltage Drop vs limit (NBR 4%)
* Branch Voltage Drop
* Device Voltage Drop

Cada critério retorna PASS/WARN/FAIL com % do rating utilizado.

Olivas v1.2.0+ tem EquipmentLibrary (templates de fabricante)
e DamageCurves (γ). Esta sub-sprint B.1 entrega o **data model**
para representar uma INSTÂNCIA de equipamento num projeto
específico (com duty operacional) + container de resultados.

Sub-sprints subsequentes:
* B.2 — `equipment_eval_rules.py` com 9 critérios como Rules
* B.3 — `generate_html_dashboard` (HTML report standalone)

Compatibilidade
================

Reusa Rule Engine da Fase A (`coord_rules.py`):
* `RuleResult` para cada critério avaliado
* `RuleEngine` para batch evaluation

Não duplica modelos da `EquipmentLibrary` — referencia via
`model_ref` opcional.

Cobertura normativa
====================

* IEEE Std 242-2001 (Buff Book) §15 (equipment evaluation)
* NBR 5410:2004 §6.2.7 (queda de tensão 4% / 7% / 10%)
* IEC 62271 (HV switchgear ratings)
* ANSI C37.04 (LV breaker ratings)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# EquipmentInstance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EquipmentInstance:
    """
    Instância de equipamento num projeto específico.

    Diferente dos modelos em ``app/equipment/library.py`` que
    são templates de catálogo de fabricante, esta classe carrega:

    * **ratings** (capacidade nominal — copiado do model)
    * **duty operacional** (valores REAIS de operação:
      I_load, V_bus, I_fault, V_drop)

    Esta separação permite:
    * Mesmo modelo usado em N instâncias com duties diferentes
    * Auditoria forense: o que estava no datasheet vs o que está
      operando

    Attributes
    ----------

    equipment_id:
        Identificador humano único no projeto (ex: ``"BRK-MAIN-1"``).
    equipment_type:
        Categoria: ``"breaker"``, ``"cable"``, ``"transformer"``,
        ``"generator"``, ``"motor"``, ``"bus"``.
    rated_voltage_kV:
        Tensão nominal do equipamento (V_rating).
    rated_continuous_A:
        Corrente nominal contínua (I_rating).
    rated_interrupt_kA:
        Capacidade de interrupção (kA, simétrica). Default 0.
    rated_asym_kA:
        Capacidade assimétrica (peak kA). Default 0.
    bus_voltage_kV:
        Tensão NOMINAL DO BUS onde está conectado. Para
        comparação com rated_voltage_kV.
    duty:
        Dict opaco com valores operacionais. Chaves esperadas:

        * ``I_load_A`` (corrente operacional média)
        * ``I_design_A`` (corrente de design — pico esperado)
        * ``I_fault_kA`` (Ik'' do bus)
        * ``ip_kA`` (peak fault current)
        * ``V_drop_pct`` (% queda de tensão sob carga)
    model_ref:
        ID opcional de model em ``EquipmentLibrary``.
        Para auditoria (datasheet usado).

    Cobertura normativa
    --------------------

    * IEEE 242:2001 §15 (equipment evaluation criteria)
    * NBR 5410 §6.2.7 (V-drop limits)
    """

    equipment_id: str
    equipment_type: str
    rated_voltage_kV: float
    rated_continuous_A: float
    rated_interrupt_kA: float = 0.0
    rated_asym_kA: float = 0.0
    bus_voltage_kV: float = 0.0
    duty: dict = field(default_factory=dict)
    model_ref: Optional[str] = None

    def __post_init__(self) -> None:
        # Validações básicas
        if self.rated_voltage_kV < 0:
            raise ValueError(
                f"rated_voltage_kV deve ser ≥ 0, recebido "
                f"{self.rated_voltage_kV}"
            )
        if self.rated_continuous_A < 0:
            raise ValueError(
                f"rated_continuous_A deve ser ≥ 0, recebido "
                f"{self.rated_continuous_A}"
            )
        if self.rated_interrupt_kA < 0:
            raise ValueError(
                f"rated_interrupt_kA deve ser ≥ 0, recebido "
                f"{self.rated_interrupt_kA}"
            )
        if self.rated_asym_kA < 0:
            raise ValueError(
                f"rated_asym_kA deve ser ≥ 0"
            )
        if self.bus_voltage_kV < 0:
            raise ValueError(
                f"bus_voltage_kV deve ser ≥ 0"
            )
        # Tipo válido
        valid_types = {
            "breaker", "cable", "transformer", "generator",
            "motor", "bus", "fuse", "contactor",
        }
        if self.equipment_type not in valid_types:
            raise ValueError(
                f"equipment_type inválido: {self.equipment_type!r}. "
                f"Esperado um de {sorted(valid_types)}"
            )

    def get_duty(self, key: str, default=None):
        """Atalho para `self.duty.get(key, default)`."""
        return self.duty.get(key, default)


# ---------------------------------------------------------------------------
# EvaluationReport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvaluationReport:
    """
    Sumário de avaliação de uma EquipmentInstance contra Rules.

    Cobertura
    ----------

    * IEEE 242:2001 §15 — equipment evaluation summary
    * Inspirado em PTW Equipment Evaluation tabular report
      (mas: data structure pura — render é responsabilidade
      separada via equipment_eval_dashboard)

    Attributes
    ----------

    equipment_id:
        ID do equipamento avaliado.
    equipment_type:
        Categoria (echo de EquipmentInstance.equipment_type).
    results:
        Tuple imutável de RuleResults (1 por Rule aplicada).

    Métodos auxiliares
    -------------------

    * ``passes_all()`` — True se todos resultados são PASS
    * ``has_failures()`` — True se há ≥1 FAIL
    * ``failures()`` — lista de RuleResults com severity=FAIL
    * ``warnings()`` — idem WARN
    * ``passes()`` — idem PASS
    * ``not_applicables()`` — idem NOT_APPLICABLE
    * ``count_by_severity()`` — dict[severity, count]
    """

    equipment_id: str
    equipment_type: str
    results: tuple = ()

    def __post_init__(self) -> None:
        # Aceita tuple ou list
        if not isinstance(self.results, tuple):
            object.__setattr__(self, "results", tuple(self.results))
        # Sanity: cada item é RuleResult
        # Lazy import para evitar circular
        from app.postprocessor.coord_rules import RuleResult
        for i, r in enumerate(self.results):
            if not isinstance(r, RuleResult):
                raise TypeError(
                    f"EvaluationReport.results[{i}] não é RuleResult "
                    f"(tipo recebido: {type(r).__name__})"
                )

    def passes(self) -> list:
        """Lista de RuleResults com severity PASS."""
        from app.postprocessor.coord_rules import RuleSeverity
        return [r for r in self.results if r.severity == RuleSeverity.PASS]

    def warnings(self) -> list:
        """Lista de RuleResults com severity WARN."""
        from app.postprocessor.coord_rules import RuleSeverity
        return [r for r in self.results if r.severity == RuleSeverity.WARN]

    def failures(self) -> list:
        """Lista de RuleResults com severity FAIL."""
        from app.postprocessor.coord_rules import RuleSeverity
        return [r for r in self.results if r.severity == RuleSeverity.FAIL]

    def not_applicables(self) -> list:
        """Lista de RuleResults com severity NOT_APPLICABLE."""
        from app.postprocessor.coord_rules import RuleSeverity
        return [
            r for r in self.results
            if r.severity == RuleSeverity.NOT_APPLICABLE
        ]

    def passes_all(self) -> bool:
        """True se TODOS resultados aplicáveis são PASS (NA não conta)."""
        applicable = [
            r for r in self.results
            if not r.is_not_applicable()
        ]
        if not applicable:
            return True
        return all(r.is_pass() for r in applicable)

    def has_failures(self) -> bool:
        """True se há ≥1 FAIL."""
        return any(r.is_fail() for r in self.results)

    def has_warnings(self) -> bool:
        """True se há ≥1 WARN."""
        return any(r.is_warn() for r in self.results)

    def count_by_severity(self) -> dict:
        """Dict {severity: count} sempre com todas as keys."""
        from app.postprocessor.coord_rules import RuleSeverity
        return {
            sev: sum(1 for r in self.results if r.severity == sev)
            for sev in RuleSeverity
        }

    def overall_status(self) -> str:
        """
        Sumário humano-legível: ``"FAIL"``, ``"WARN"``, ``"PASS"``,
        ou ``"N/A"``.

        Hierarquia: FAIL > WARN > PASS > N/A.
        """
        if self.has_failures():
            return "FAIL"
        if self.has_warnings():
            return "WARN"
        if any(r.is_pass() for r in self.results):
            return "PASS"
        return "N/A"


# ---------------------------------------------------------------------------
# Helpers para evaluation
# ---------------------------------------------------------------------------


def evaluate_equipment(
    equipment: EquipmentInstance,
    rules,
    context: Optional[dict] = None,
) -> EvaluationReport:
    """
    Aplica uma lista de Rules a um EquipmentInstance e gera
    EvaluationReport.

    Parameters
    ----------

    equipment:
        Instância a avaliar.
    rules:
        list[Rule] OR RuleSet.
    context:
        Dict opcional adicional. EquipmentInstance.duty é
        merged automaticamente neste context (com `duty` keys
        tendo precedência sobre `context` conflitante? — NÃO,
        context tem precedência: caller pode override duty).

    Returns
    -------

    EvaluationReport com 1 RuleResult por Rule aplicada.
    """
    from app.postprocessor.coord_rules import RuleSet

    # Permite passar RuleSet ou list[Rule]
    rule_list = rules.rules if isinstance(rules, RuleSet) else list(rules)

    # Merge duty + context (context tem precedência se passado)
    full_context = dict(equipment.duty)
    if context:
        full_context.update(context)

    results = tuple(
        rule.evaluate(equipment, full_context) for rule in rule_list
    )

    return EvaluationReport(
        equipment_id=equipment.equipment_id,
        equipment_type=equipment.equipment_type,
        results=results,
    )


def evaluate_project(
    equipments: list,
    rules,
    context: Optional[dict] = None,
) -> list:
    """
    Aplica rules a uma lista de EquipmentInstance.

    Returns
    -------

    list[EvaluationReport], um por EquipmentInstance.
    """
    return [
        evaluate_equipment(eq, rules, context)
        for eq in equipments
    ]


# ---------------------------------------------------------------------------
# v3.3.0 Sprint 4 — Auto-extract EquipmentInstance de PpProject
# Reference: PTW Tutorial §Part 4 p.109-117
# ---------------------------------------------------------------------------


# Mapping de PpComponent.type → equipment_type canônico do EquipmentEval
_TYPE_MAP: dict[str, str] = {
    "BREAKER": "breaker",
    "VCB": "breaker",
    "VCB3": "breaker",
    "FUSE": "fuse",
    "CABLE": "cable",
    "Tr": "transformer",
    "sTr": "transformer",
    "Tr3": "transformer",
    "XFMR": "transformer",
    "XFMR3": "transformer",
    "MOTOR": "motor",
    "SM": "generator",  # Synchronous Machine (default to generator)
    "BUS": "bus",
    "CONTACTOR": "contactor",
}


def build_equipment_from_project(
    project,
    *,
    default_continuous_A: float = 1200.0,
    default_interrupt_kA: float = 25.0,
    default_voltage_kV: float = 13.8,
) -> list:
    """v3.3.0 Sprint 4: extrai EquipmentInstance da topologia PpProject.

    Per PTW Tutorial §Part 4 p.109-117: Equipment Evaluation deve ler
    do projeto real, não de demo data. Este helper mapeia
    `PpComponent.type` → `equipment_type` canônico do
    :class:`EquipmentInstance` e extrai ratings dos properties (quando
    disponíveis) ou usa defaults.

    Parameters
    ----------
    project
        :class:`PpProject` com componentes a avaliar.
    default_continuous_A, default_interrupt_kA, default_voltage_kV
        Fallbacks se properties não tiverem os ratings.

    Returns
    -------
    list[EquipmentInstance]
        Lista pronta para passar a :func:`evaluate_project`.

    References
    ----------
    PTW Tutorial v8.0 §Part 4 p.109-117.
    """
    if project is None or not hasattr(project, "components"):
        return []

    equipments: list = []
    for comp in project.components:
        eq_type = _TYPE_MAP.get(comp.type)
        if eq_type is None:
            continue  # Tipo não-avaliável (R, L, C genéricos, etc.)

        # Extrai ratings dos properties (best-effort)
        rated_kV = default_voltage_kV
        rated_A = default_continuous_A
        rated_kA = default_interrupt_kA
        for prop in comp.properties:
            v_str = prop.value.strip().lower() if prop.value else ""
            if not v_str:
                continue
            try:
                # Heuristic: parse number prefix
                val = float(v_str.split()[0]) if v_str else 0.0
            except (ValueError, IndexError):
                continue
            # Match by value range (very heuristic)
            if 0.1 <= val <= 1000.0 and "kv" in v_str:
                rated_kV = val
            elif 100.0 <= val <= 100000.0 and ("a" in v_str or v_str.endswith(".0")):
                rated_A = val
            elif 1.0 <= val <= 200.0 and "ka" in v_str:
                rated_kA = val

        try:
            eq = EquipmentInstance(
                equipment_id=comp.name or f"{comp.type}-{id(comp)}",
                equipment_type=eq_type,
                rated_voltage_kV=rated_kV,
                rated_continuous_A=rated_A,
                rated_interrupt_kA=rated_kA,
                rated_asym_kA=rated_kA * 1.6,  # PTW typical 1.6× asym factor
                bus_voltage_kV=rated_kV,
                duty={},  # caller fills via study results
            )
            equipments.append(eq)
        except (ValueError, TypeError):
            continue
    return equipments


__all__ = [
    "EquipmentInstance",
    "EvaluationReport",
    "evaluate_equipment",
    "evaluate_project",
    "build_equipment_from_project",
]
