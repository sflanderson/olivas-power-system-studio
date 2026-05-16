"""
app.postprocessor.relay_coordination — análise de coordenação
seletiva entre relés de proteção.

Filosofia
=========

A coordenação seletiva (IEEE 242 Buff Book §15) garante que **a
proteção mais próxima da falta atue primeiro**, evitando trip
desnecessário de cargas saudáveis a montante. Para isso, deve-se
verificar:

1. **Margem de tempo** entre cada par upstream/downstream:

   ::

       Δt = t_upstream(I) - t_downstream(I) ≥ Δt_min

   Onde:

   * ``Δt_min`` = 200–300 ms (eletromecânicos), 100–200 ms
     (digitais — Buff Book §15.3.2).

2. **Margem em todos os múltiplos relevantes** de Ifault:
   tipicamente verifica em ``M = 2, 5, 10, 20`` × Ipickup.

3. **Hierarquia consistente**: pickup_upstream > pickup_downstream
   (caso contrário não há sentido em coordenação).

Workflow
=========

::

    from app.postprocessor.relay_coordination import (
        RelayInstance, CoordinationCheck,
    )

    upstream = RelayInstance(
        name="51-MAIN",
        location="MV main breaker",
        device_function="51",
        tc_curve=make_iec_si(pickup_A=300.0, tms=0.5),
        relay_model="SEL-751",
    )
    downstream = RelayInstance(
        name="51-FEEDER",
        location="Feeder breaker",
        device_function="51",
        tc_curve=make_iec_si(pickup_A=100.0, tms=0.2),
        relay_model="ABB-REF615",
    )
    check = CoordinationCheck(upstream=upstream, downstream=downstream)
    report = check.run(test_currents_A=[200, 500, 1000, 5000])
    print(report.summary())

Cobertura MVP v0.27.4
======================

* **Par upstream-downstream**: verifica margens em currents
  específicas.
* **Auto-test em múltiplos**: 2× e 10× pickup downstream.
* **Validação de relé**: confirma que o RelayModel suporta a
  função ANSI e a curva TC selecionada.
* **Cross-check com manual**: integra com ``app.standards.
  relay_models``.

Diferenciais vs ATPDraw
========================

ATPDraw 7.7 não tem módulo dedicado de coordenação de proteção.
O usuário consulta TC curves manualmente em catálogo do
fabricante e desenha em Excel ou software dedicado (ETAP, SKM,
EasyPower).

Olivas oferece:

* Codificação NORMATIVA (IEC 60255-151, IEEE C37.112) das curvas.
* Registry de RELÉS COMERCIAIS (SEL-751, ABB REF615, Schneider
  P3U) com funções suportadas.
* Validação automática (pickup no range, função suportada).
* Memorial de cálculo auditável vs IEEE 242.

Referências
============

* IEEE Std 242-2001 (Buff Book) §15 — Coordination of protective
  devices.
* IEEE Std 141-1993 (Red Book) — Industrial power distribution.
* IEEE Std C37.112-2018 — Inverse-time characteristic equations.
* IEC 60255-151:2009 — Functional requirements for OC protection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.standards.iec60255 import (
    CurveStandard, TcCurveSetting,
)
from app.standards.relay_models import (
    RelayModel, get_model,
    supports_curve_standard, supports_function,
    validate_pickup_per_in, validate_time_dial, validate_tms,
)


# ---------------------------------------------------------------------------
# RelayInstance — configuração de um relé real no projeto
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RelayInstance:
    """
    Instância de um relé de proteção configurado no projeto.

    Attributes
    ----------
    name:
        Identificador único do relé (ex: "51-MAIN", "BUS-A-OC1").
    location:
        Localização física (ex: "MT main breaker", "Feeder F1").
    device_function:
        Número ANSI/IEEE C37.2 (ex: "51", "50N", "67").
    tc_curve:
        Configuração da curva TC (``TcCurveSetting``).
    relay_model:
        Identificador do modelo no registry (ex: "SEL-751"); pode
        ser ``None`` se for um relé genérico.
    rated_current_A:
        Corrente nominal do relé (In, A) — tipicamente 1 A ou 5 A
        para CTs.
    description:
        Texto livre para memorial.
    """

    name: str
    location: str
    device_function: str
    tc_curve: TcCurveSetting
    relay_model: Optional[str] = None
    rated_current_A: float = 5.0
    description: str = ""

    def operate_time_at_current_s(self, current_A: float) -> float:
        """Retorna t(I) usando a curva TC configurada."""
        return self.tc_curve.operate_time_s(current_A)

    def model_object(self) -> Optional[RelayModel]:
        """Retorna o RelayModel resolvido do registry, ou None."""
        if self.relay_model is None:
            return None
        return get_model(self.relay_model)


def validate_relay_instance(instance: RelayInstance) -> list[str]:
    """
    Verifica consistência da instância vs RelayModel registry.

    Returns
    -------
    list[str]
        Lista de erros (vazia ⇒ ok).
    """
    errors: list[str] = []

    if not instance.name:
        errors.append("name vazio")
    if not instance.device_function:
        errors.append("device_function vazio")

    model = instance.model_object()
    if instance.relay_model and model is None:
        errors.append(
            f"relay_model {instance.relay_model!r} não encontrado no registry"
        )
        return errors

    if model is None:
        # genérico — sem cross-check
        return errors

    # Função ANSI suportada?
    if not supports_function(model, instance.device_function):
        errors.append(
            f"função ANSI {instance.device_function!r} não suportada por "
            f"{model.model} (suportadas: {model.ansi_functions})"
        )

    # Família de curva suportada?
    curve_std = instance.tc_curve.standard
    if not supports_curve_standard(model, curve_std):
        errors.append(
            f"family de curva {curve_std.value!r} não suportada por "
            f"{model.model}"
        )

    # TMS / TD nos ranges?
    if curve_std == CurveStandard.IEC:
        if not validate_tms(model, instance.tc_curve.tms):
            lo, hi = model.tms_range
            errors.append(
                f"TMS={instance.tc_curve.tms} fora do range "
                f"{model.model} [{lo}, {hi}]"
            )
    elif curve_std in (CurveStandard.IEEE, CurveStandard.ANSI):
        if not validate_time_dial(model, instance.tc_curve.time_dial):
            lo, hi = model.time_dial_range
            errors.append(
                f"Time Dial={instance.tc_curve.time_dial} fora do range "
                f"{model.model} [{lo}, {hi}]"
            )

    # Pickup no range (em pu de In)?
    pickup_pu = instance.tc_curve.pickup_A / instance.rated_current_A
    if not validate_pickup_per_in(model, pickup_pu):
        lo, hi = model.pickup_range_per_in
        errors.append(
            f"pickup={instance.tc_curve.pickup_A:.2f} A "
            f"({pickup_pu:.2f} pu In) fora do range {model.model} "
            f"[{lo} pu, {hi} pu]"
        )

    return errors


# ---------------------------------------------------------------------------
# CoordinationMargin — verificação de margem em uma corrente
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoordinationMargin:
    """
    Margem de tempo entre upstream e downstream em uma corrente
    específica.

    Attributes
    ----------
    test_current_A:
        Corrente de teste (A).
    t_downstream_s:
        Tempo de operação do relé jusante.
    t_upstream_s:
        Tempo de operação do relé montante.
    margin_s:
        ``t_upstream - t_downstream`` (deve ser ≥ Δt_min).
    margin_required_s:
        Δt_min mínimo aplicado.
    coordinated:
        ``True`` se margin_s ≥ margin_required_s.
    """

    test_current_A: float
    t_downstream_s: float
    t_upstream_s: float
    margin_s: float
    margin_required_s: float
    coordinated: bool


# ---------------------------------------------------------------------------
# CoordinationCheck
# ---------------------------------------------------------------------------


# Margens recomendadas conforme Buff Book §15.3.2.
# Margens menores → relés mais rápidos (digital).
# Margens maiores → relés mais lentos (eletromecânicos com
# overshoot e tempo de reset significativos).
MARGIN_DIGITAL_S = 0.20             # IEEE 242 §15.3 digital moderno
MARGIN_ELECTROMECHANICAL_S = 0.30   # IEEE 242 §15.3 eletromecânico
MARGIN_HYBRID_S = 0.25              # IEEE 242 §15.3 misto


@dataclass
class CoordinationCheck:
    """
    Verificação de coordenação entre dois relés (upstream-down-
    stream).

    Attributes
    ----------
    upstream:
        Relé a montante (deve ter tempo MAIOR).
    downstream:
        Relé a jusante (deve ter tempo MENOR).
    margin_required_s:
        Δt_min mínimo requerido. Default 0.20 s (digital).
        Use ``electromechanical=True`` em ``__init__`` para
        elevar a 0.30 s automaticamente (Buff Book §15.3.2).
    electromechanical:
        v0.28.1: se True, força margem 0.30s. Útil para painéis
        antigos com relés ABB CO-7/9, GE IAC, Westinghouse CO,
        que têm overshoot de disco e tempo de reset
        significativos.
    """

    upstream: RelayInstance
    downstream: RelayInstance
    margin_required_s: float = MARGIN_DIGITAL_S
    electromechanical: bool = False

    def __post_init__(self):
        # v0.28.1: aplica margem eletromecânica se flag setada
        # E margem ainda no default. Se usuário sobrescreveu
        # manualmente, respeita.
        if self.electromechanical and self.margin_required_s == MARGIN_DIGITAL_S:
            object.__setattr__(self, "margin_required_s", MARGIN_ELECTROMECHANICAL_S)

    def margin_at_current(self, current_A: float) -> CoordinationMargin:
        """Calcula margem em uma corrente específica."""
        t_dn = self.downstream.operate_time_at_current_s(current_A)
        t_up = self.upstream.operate_time_at_current_s(current_A)
        margin = t_up - t_dn
        return CoordinationMargin(
            test_current_A=current_A,
            t_downstream_s=t_dn,
            t_upstream_s=t_up,
            margin_s=margin,
            margin_required_s=self.margin_required_s,
            coordinated=margin >= self.margin_required_s,
        )

    def run(
        self,
        test_currents_A: list[float] | None = None,
    ) -> "CoordinationReport":
        """
        Executa a verificação. Se ``test_currents_A`` for None,
        gera lista padrão: 2×, 5×, 10× pickup downstream.
        """
        if test_currents_A is None:
            pk = self.downstream.tc_curve.pickup_A
            test_currents_A = [2 * pk, 5 * pk, 10 * pk]

        margins = tuple(
            self.margin_at_current(I) for I in test_currents_A
        )
        return CoordinationReport(
            upstream=self.upstream,
            downstream=self.downstream,
            margin_required_s=self.margin_required_s,
            margins=margins,
        )


# ---------------------------------------------------------------------------
# CoordinationReport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoordinationReport:
    """
    Relatório completo de coordenação de um par upstream-down.

    Aplicação principal: gerar memorial de cálculo conforme IEEE
    242 Buff Book §15.
    """

    upstream: RelayInstance
    downstream: RelayInstance
    margin_required_s: float
    margins: tuple[CoordinationMargin, ...]

    @property
    def all_coordinated(self) -> bool:
        """True se todas as margens passam."""
        return all(m.coordinated for m in self.margins)

    @property
    def worst_margin(self) -> CoordinationMargin:
        """Pior margem (menor margin_s) entre os pontos testados."""
        return min(self.margins, key=lambda m: m.margin_s)

    def summary(self) -> str:
        """Texto plano do relatório."""
        status = "COORDINATED ✓" if self.all_coordinated else "NOT COORDINATED ✗"
        worst = self.worst_margin
        lines = [
            f"=== Relay Coordination Report — {status} ===",
            f"Upstream: {self.upstream.name} @ {self.upstream.location}",
            f"  Function: {self.upstream.device_function}",
            f"  Curve:    {self.upstream.tc_curve.description()}",
            f"  Model:    {self.upstream.relay_model or 'generic'}",
            "",
            f"Downstream: {self.downstream.name} @ {self.downstream.location}",
            f"  Function: {self.downstream.device_function}",
            f"  Curve:    {self.downstream.tc_curve.description()}",
            f"  Model:    {self.downstream.relay_model or 'generic'}",
            "",
            f"Margin required (Δt_min): {self.margin_required_s:.3f} s",
            "",
            "--- Margin Points ---",
            f"  {'I (A)':>10}  {'t_dn (s)':>10}  {'t_up (s)':>10}  "
            f"{'Δt (s)':>10}  Status",
        ]
        for m in self.margins:
            t_dn_s = (
                f"{m.t_downstream_s:.3f}"
                if m.t_downstream_s != float("inf")
                else "  ∞   "
            )
            t_up_s = (
                f"{m.t_upstream_s:.3f}"
                if m.t_upstream_s != float("inf")
                else "  ∞   "
            )
            mg_s = (
                f"{m.margin_s:+.3f}"
                if m.margin_s != float("inf") and m.margin_s != float("-inf")
                else "    -"
            )
            ok = "✓" if m.coordinated else "✗"
            lines.append(
                f"  {m.test_current_A:>10.1f}  {t_dn_s:>10}  "
                f"{t_up_s:>10}  {mg_s:>10}  {ok}"
            )
        lines.append("")
        lines.append(
            f"--- Worst case @ I = {worst.test_current_A:.1f} A: "
            f"Δt = {worst.margin_s:+.3f} s "
            f"({'OK' if worst.coordinated else 'INSUFFICIENT'}) ---"
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers de alto nível
# ---------------------------------------------------------------------------


def quick_pair_check(
    upstream: RelayInstance,
    downstream: RelayInstance,
    fault_current_kA: float,
    margin_min_s: float = 0.20,
) -> CoordinationReport:
    """
    Atalho: verificação rápida em uma única corrente de falta
    (vinda do estudo de SC IEC 60909-0).
    """
    check = CoordinationCheck(
        upstream=upstream,
        downstream=downstream,
        margin_required_s=margin_min_s,
    )
    return check.run(test_currents_A=[fault_current_kA * 1000.0])


def validate_coordination_chain(
    relays: list[RelayInstance],
    fault_currents_A: list[float],
    margin_min_s: float = 0.20,
) -> list[CoordinationReport]:
    """
    Valida cadeia de N relés (do mais a montante ao mais a jusante)
    e retorna relatórios de cada par adjacente.

    Convenção: ``relays[0]`` é o **mais a montante** (maior tempo
    de operação esperado). ``relays[-1]`` é o **mais a jusante**.

    Returns
    -------
    list[CoordinationReport]
        N-1 relatórios para os pares adjacentes.
    """
    if len(relays) < 2:
        raise ValueError("precisa de ≥ 2 relés para coordenação")
    reports: list[CoordinationReport] = []
    for i in range(len(relays) - 1):
        check = CoordinationCheck(
            upstream=relays[i],
            downstream=relays[i + 1],
            margin_required_s=margin_min_s,
        )
        reports.append(check.run(test_currents_A=fault_currents_A))
    return reports
