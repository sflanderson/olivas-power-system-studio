"""
app.postprocessor.coord_rules — Coordination Rule Engine
(v1.3.0 Fase A — paridade SKM PTW Coordination Evaluation).

Filosofia
==========

PTW Power*Tools "Coordination Evaluation" é um add-on que requer
DAPPER + CAPTOR. Ao rodar, gera dashboard tabular Pass/Warning/Fail
por equipamento com regras de engenharia codificadas tipo:

    Motor Relay 51 LTPU = 115%-125% × FLA  ✓ PASS
    Motor 49 thermal    = 100%-200% × FLA  ⚠ WARN (95%)
    LV XFMR primário    = 100%-167% × FLA  ✓ PASS
    Cable damage 80%                       ✗ FAIL

Olivas v1.2.0 tem **cálculo numérico** (`check_device_coordination`
da β.3) mas não tem **regras de engenharia**. Esta sub-sprint A.1
entrega o **modelo de dados** para regras reutilizáveis.

Sub-sprints subsequentes:
* A.2 — `coord_rules_builtin.py` com 15 regras (NEC 110.10 + IEEE 242 + NBR)
* A.3 — `RuleEngine` que aplica RuleSets a coleções de targets

Compatibilidade
================

Módulo paralelo a:
* `tcc_segments.py` (Fase α v1.2.0)
* `tcc_devices.py` (Fase β v1.2.0)
* `tcc_damage.py` (Fase γ v1.2.0)

Não modifica nenhum dos anteriores.

Cobertura normativa
====================

* IEEE Std 242-2001 (Buff Book) §9 (motor protection rules)
* NEC 110.10 (proteção upstream rules)
* IEEE C57.109-1993 (XFMR damage coordination)
* NBR 5410:2004 (cable thermal stress)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# Severity enum
# ---------------------------------------------------------------------------


class RuleSeverity(str, Enum):
    """
    Severidade do resultado de uma regra de coordenação.

    * **PASS** — regra satisfeita
    * **WARN** — fora do range ideal mas tolerável (engenheiro pode aceitar)
    * **FAIL** — fora do range aceitável (correção obrigatória)
    * **NOT_APPLICABLE** — regra não se aplica ao target ou
      context insuficiente

    Cobertura
    ----------

    * IEEE 242:2001 §15 (níveis de severity para evaluation)
    * Convenção PTW Coordination Eval (Pass/Warning/Fail/Accepted)
    """

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_APPLICABLE = "n/a"


# ---------------------------------------------------------------------------
# RuleResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleResult:
    """
    Resultado da aplicação de uma ``Rule`` a um ``target``.

    Carrega todos os dados necessários para auditoria forense
    (rastrear DECISÃO de coordenação): valor avaliado, range
    esperado, citation à norma, mensagem humano-legível.

    Attributes
    ----------

    rule_id:
        ID humano da regra (ex: ``"NEC-MOTOR-51-LTPU"``).
    target_id:
        ID do equipamento avaliado (ex: ``"R-MOTOR-1"``,
        ``"C-FEEDER-50mm2"``).
    severity:
        PASS / WARN / FAIL / NOT_APPLICABLE.
    message:
        Texto humano-legível com diagnóstico (ex: ``"51 LTPU = 130%
        FLA — fora do range NEC 110.10 (115-125%)"``).
    citation:
        Norma + página (ex: ``"NEC 110.10 + IEEE 242 §9.5.4 Tabela 9-2"``).
    evaluated_value:
        Valor numérico computado (ex: 130.0 % FLA). Opcional.
    expected_range:
        ``(min, max)`` do range aceito. Opcional.
    """

    rule_id: str
    target_id: str
    severity: RuleSeverity
    message: str
    citation: str
    evaluated_value: Optional[float] = None
    expected_range: Optional[tuple] = None  # (min, max) ou None

    def is_pass(self) -> bool:
        return self.severity == RuleSeverity.PASS

    def is_fail(self) -> bool:
        return self.severity == RuleSeverity.FAIL

    def is_warn(self) -> bool:
        return self.severity == RuleSeverity.WARN

    def is_not_applicable(self) -> bool:
        return self.severity == RuleSeverity.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    """
    Regra de coordenação aplicável a um tipo específico de
    equipamento.

    Cobertura
    ----------

    * IEEE 242:2001 (Buff Book) §15 — princípio geral de
      coordination evaluation rules
    * NEC 110.10 — exemplo concreto de framework de regras
      aplicáveis
    * Convenção PTW Coordination Evaluation (rule + applicable
      device + severity)

    Cada regra tem:
    * ``rule_id`` único humano-legível
    * ``description`` (1-2 frases)
    * ``citation`` à norma (obrigatório — anti-alucinação)
    * ``applicable_to`` tuple de tipos (isinstance check)
    * ``eval_func`` função pura `(target, context) → RuleResult`

    A função ``eval_func`` deve:
    1. Verificar se o target tem dados necessários (e.g., FLA no
       context); se não, retornar `NOT_APPLICABLE`.
    2. Computar o valor avaliado (e.g., pickup% FLA).
    3. Retornar `RuleResult` com severity apropriada.

    Attributes
    ----------

    rule_id:
        Identificador único humano (ex: ``"NEC-MOTOR-51-LTPU"``).
    description:
        Descrição curta (1-2 frases).
    citation:
        Norma + seção + página.
    applicable_to:
        Tuple de tipos para isinstance check do target.
    eval_func:
        Callable ``(target, context: dict) → RuleResult``.
    severity_default:
        Severity default se eval_func não decide (raramente usado).
    """

    rule_id: str
    description: str
    citation: str
    applicable_to: tuple
    eval_func: Callable
    severity_default: RuleSeverity = RuleSeverity.NOT_APPLICABLE

    def applies_to(self, target) -> bool:
        """Verifica se ``target`` é instância de algum tipo aceito."""
        return isinstance(target, self.applicable_to)

    def evaluate(self, target, context: Optional[dict] = None) -> RuleResult:
        """
        Aplica a regra ao target.

        Se target não satisfaz ``applicable_to``, retorna
        NOT_APPLICABLE. Caso contrário, delega para ``eval_func``.

        Parameters
        ----------
        target:
            Equipamento a avaliar (TCCDevice, DamageCurve, etc.)
        context:
            Dict opcional com dados adicionais (FLA do motor, kVA do
            transformador, etc.) que a regra pode precisar.
        """
        if context is None:
            context = {}
        if not self.applies_to(target):
            return RuleResult(
                rule_id=self.rule_id,
                target_id=getattr(target, "device_id", "?")
                          or getattr(target, "cable_id", "?")
                          or getattr(target, "xfmr_id", "?")
                          or getattr(target, "motor_id", "?")
                          or "?",
                severity=RuleSeverity.NOT_APPLICABLE,
                message=(
                    f"target {type(target).__name__} não é "
                    f"instância de {[t.__name__ for t in self.applicable_to]}"
                ),
                citation=self.citation,
            )
        return self.eval_func(target, context)


# ---------------------------------------------------------------------------
# RuleSet
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleSet:
    """
    Coleção imutável de Rules de mesma origem normativa.

    Examples
    --------

    ::

        nec_motor = RuleSet(
            name="NEC 110.10 — Motor Protection",
            norm_reference="NEC 110.10 + IEEE 242 §9",
            rules=(
                rule_motor_51_ltpu,
                rule_motor_49_thermal,
                rule_motor_50_inst,
            ),
        )

    Attributes
    ----------

    name:
        Nome descritivo (ex: ``"NEC 110.10 Motor Protection"``).
    norm_reference:
        Norma de referência geral.
    rules:
        Tuple imutável de Rules.
    """

    name: str
    norm_reference: str
    rules: tuple = ()

    def __post_init__(self) -> None:
        # Aceita tuple ou list
        if not isinstance(self.rules, tuple):
            object.__setattr__(self, "rules", tuple(self.rules))
        # Sanity: cada item é Rule
        for i, r in enumerate(self.rules):
            if not isinstance(r, Rule):
                raise TypeError(
                    f"RuleSet.rules[{i}] não é Rule "
                    f"(tipo recebido: {type(r).__name__})"
                )
        # Sanity: rule_ids únicos no RuleSet
        ids = [r.rule_id for r in self.rules]
        if len(ids) != len(set(ids)):
            duplicates = [x for x in set(ids) if ids.count(x) > 1]
            raise ValueError(
                f"RuleSet '{self.name}' tem rule_ids duplicados: "
                f"{duplicates}"
            )

    def __len__(self) -> int:
        return len(self.rules)

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Retorna Rule por ID, ou None se não existir."""
        for r in self.rules:
            if r.rule_id == rule_id:
                return r
        return None


# ---------------------------------------------------------------------------
# RuleEngine
# ---------------------------------------------------------------------------


class RuleEngine:
    """
    Aplica RuleSets a coleções de targets, agregando RuleResults.

    Cobertura
    ----------

    * IEEE 242:2001 §15 — orchestration de evaluation rules
    * Inspirado em PTW Coordination Evaluation engine
      (mas: pure Python + plugin-friendly + auditável)

    Métodos principais:
    * ``apply_rule(rule, target, context)`` → RuleResult
    * ``apply_ruleset(ruleset, targets, context)`` → list[RuleResult]
    * ``apply_rulesets(rulesets, targets, context)`` → list[RuleResult]
    * ``filter_by_severity(results, severity)`` → list[RuleResult]
    * ``group_by_severity(results)`` → dict[RuleSeverity, list[RuleResult]]
    * ``count_by_severity(results)`` → dict[RuleSeverity, int]
    """

    def apply_rule(
        self,
        rule: Rule,
        target,
        context: Optional[dict] = None,
    ) -> RuleResult:
        """Atalho para `rule.evaluate(target, context)`."""
        return rule.evaluate(target, context)

    def apply_ruleset(
        self,
        ruleset: RuleSet,
        targets: list,
        context: Optional[dict] = None,
    ) -> list:
        """
        Aplica todo o ``ruleset`` a cada target.

        Retorna lista achatada de RuleResults — uma entrada por
        (rule, target). NOT_APPLICABLE entries são incluídos
        (caller pode filtrar via ``filter_by_severity``).
        """
        results = []
        for target in targets:
            for rule in ruleset.rules:
                results.append(rule.evaluate(target, context))
        return results

    def apply_rulesets(
        self,
        rulesets: list,
        targets: list,
        context: Optional[dict] = None,
    ) -> list:
        """Aplica vários RuleSets — útil para misturar normas."""
        results = []
        for rs in rulesets:
            results.extend(self.apply_ruleset(rs, targets, context))
        return results

    @staticmethod
    def filter_by_severity(
        results: list, severity: RuleSeverity,
    ) -> list:
        """Retorna só RuleResults com severity dada."""
        return [r for r in results if r.severity == severity]

    @staticmethod
    def group_by_severity(results: list) -> dict:
        """Agrupa por severity. Sempre tem todas as keys."""
        groups: dict = {sev: [] for sev in RuleSeverity}
        for r in results:
            groups[r.severity].append(r)
        return groups

    @staticmethod
    def count_by_severity(results: list) -> dict:
        """Conta por severity. Sempre tem todas as keys."""
        return {
            sev: sum(1 for r in results if r.severity == sev)
            for sev in RuleSeverity
        }

    @staticmethod
    def has_failures(results: list) -> bool:
        """True se há ≥1 FAIL."""
        return any(r.severity == RuleSeverity.FAIL for r in results)

    @staticmethod
    def summary_line(results: list) -> str:
        """
        Sumário humano-legível: "PASS=12, WARN=3, FAIL=1, N/A=5".

        Usado em logs de console.
        """
        c = RuleEngine.count_by_severity(results)
        return (
            f"PASS={c[RuleSeverity.PASS]}, "
            f"WARN={c[RuleSeverity.WARN]}, "
            f"FAIL={c[RuleSeverity.FAIL]}, "
            f"N/A={c[RuleSeverity.NOT_APPLICABLE]}"
        )
