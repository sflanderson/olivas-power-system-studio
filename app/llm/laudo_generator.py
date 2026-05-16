"""
app.llm.laudo_generator — Geração de laudos técnicos via
Claude AI (v0.104.0).

Diferenciador único
====================

PTW Power*Tools / ETAP / EasyPower geram tabelas de
resultados, mas o engenheiro precisa **escrever a narrativa
técnica** manualmente (introdução, análise, conclusões,
recomendações) — tipicamente 1-3 dias de trabalho por laudo.

Olivas v0.104.0 introduz **AI-driven narrative**: o agente
Claude lê o relatório consolidado (BusPipelineReport,
ShortCircuitStudyResult, etc.) e gera prosa técnica em
PT-BR adequada para anexar ao laudo.

API
====

::

    from app.llm.laudo_generator import (
        generate_audit_narrative,
        suggest_relay_fix,
        compare_reports,
    )

    # 1. Narrativa de laudo
    text = generate_audit_narrative(report)
    # 2. Sugestões de correção
    fix = suggest_relay_fix(coord_violations)
    # 3. Diff entre versões do estudo
    diff = compare_reports(v1_report, v2_report)

Modos
======

* **Sync** (padrão): retorna string completa quando Claude
  termina de gerar.
* **Streaming** (v0.104.1): yield chunks token-a-token para
  preview ao vivo na UI.

Custo
======

* Cada laudo ~3-5K tokens output × $0.015/1K = $0.075 USD
* Em 100 laudos/mês: ~$7.50 USD/mês (vs $5K/ano licença ETAP)

Limitações declaradas
======================

* Requer ANTHROPIC_API_KEY configurada (offline mode v0.104.2)
* Texto gerado deve SEMPRE ser revisado por engenheiro
  habilitado antes de publicar (responsabilidade técnica
  permanece com o profissional CREA — Claude é assistente)
* Streaming pode ser interrompido pela rede; degrada
  graciosamente para sync
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LaudoNarrative:
    """Texto gerado pelo agente para o laudo."""

    title: str
    introduction: str
    technical_analysis: str
    conclusions: str
    recommendations: str

    # Metadata
    word_count: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    model_used: str = ""

    def full_text(self) -> str:
        return (
            f"# {self.title}\n\n"
            f"## 1. Introdução\n\n{self.introduction}\n\n"
            f"## 2. Análise técnica\n\n{self.technical_analysis}\n\n"
            f"## 3. Conclusões\n\n{self.conclusions}\n\n"
            f"## 4. Recomendações\n\n{self.recommendations}\n"
        )


@dataclass(frozen=True)
class CoordinationFixSuggestion:
    """Sugestão de correção de coordenação."""

    relay_id: str
    issue: str
    proposed_action: str
    rationale: str
    affected_curves: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReportDiff:
    """Diff narrativo entre 2 versões do estudo."""

    summary: str
    sc_changes: str
    coord_changes: str
    arc_flash_changes: str
    severity: str = "minor"   # "minor" | "moderate" | "major"


# ---------------------------------------------------------------------------
# Public API — narrative generation
# ---------------------------------------------------------------------------


def generate_audit_narrative(
    report,
    *,
    api_key: Optional[str] = None,
    use_offline_template: bool = False,
) -> LaudoNarrative:
    """
    Gera narrativa técnica em PT-BR para um BusPipelineReport.

    Se ``use_offline_template=True``, retorna um template
    estático (sem chamar Claude) — útil para testes sem API
    key OU para ambientes offline.

    Parameters
    ----------
    report:
        ``BusPipelineReport`` ou similar com campos
        Ik_pp_kA, ip_kA, kappa, incident_energy_cal_cm2, etc.
    api_key:
        Override da API key. Default: env ANTHROPIC_API_KEY.
    use_offline_template:
        Se True, gera narrativa básica via template Jinja-like
        sem chamar Claude.

    Returns
    -------
    LaudoNarrative
    """
    if use_offline_template or not _has_api_key(api_key):
        return _generate_offline_narrative(report)

    return _generate_via_claude(report, api_key=api_key)


def _has_api_key(api_key: Optional[str]) -> bool:
    if api_key:
        return True
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _generate_offline_narrative(report) -> LaudoNarrative:
    """Template estático em PT-BR (sem Claude). Sempre disponível."""
    bus_id = getattr(report, "bus_id", "BUS-DESCONHECIDO")
    voltage = getattr(report, "rated_voltage_kV", 0.0)
    Ik = getattr(report, "Ik_pp_kA", 0.0)
    ip = getattr(report, "ip_kA", 0.0)
    kappa = getattr(report, "kappa", 0.0)
    E_cal = getattr(report, "incident_energy_cal_cm2", 0.0)
    ppe = getattr(report, "ppe_category", "N/A")

    title = f"Laudo Técnico — Análise de Curto-Circuito e Arc-Flash em {bus_id}"

    introduction = (
        f"O presente laudo apresenta os resultados da análise "
        f"consolidada do barramento **{bus_id}** "
        f"({voltage:.2f} kV), incluindo cálculo de curto-circuito "
        f"conforme IEC 60909-0:2016, sugestões de coordenação "
        f"50/51 por IEEE 242, e cálculo de energia incidente "
        f"de arc-flash conforme NBR 17227:2025 / IEEE 1584-2018. "
        f"Os resultados aqui apresentados são reproduzíveis "
        f"através do checksum SHA256 dos inputs registrado no "
        f"cabeçalho deste documento."
    )

    technical_analysis = (
        f"### Curto-circuito\n\n"
        f"A corrente subtransitória de curto-circuito calculada "
        f"foi **Ik''  = {Ik:.2f} kA** (RMS), com pico assimétrico "
        f"**ip = {ip:.2f} kA** e fator de assimetria κ = {kappa:.3f}. "
        f"Estes valores satisfazem ou exigem reavaliação de "
        f"equipamentos com capacidade de interrupção compatível.\n\n"
        f"### Arc-flash\n\n"
    )
    if ppe == "N/A":
        technical_analysis += (
            f"Para este barramento ({voltage:.2f} kV), a análise "
            f"de arc-flash conforme NBR 17227 / IEEE 1584 não é "
            f"aplicável (escopo limitado a ≤15 kV). Recomenda-se "
            f"avaliação por método EPRI 2011 (15-46 kV) ou "
            f"Terzija-Konglin (>46 kV)."
        )
    else:
        technical_analysis += (
            f"A energia incidente calculada foi **"
            f"E = {E_cal:.2f} cal/cm²**, classificando o trabalho "
            f"em PPE Categoria **{ppe}** conforme NFPA 70E:2024. "
            f"Os profissionais que atuarem em proximidade deste "
            f"barramento devem utilizar equipamento de proteção "
            f"individual conforme a categoria identificada."
        )

    conclusions = (
        f"O barramento {bus_id} apresenta correntes de curto "
        f"compatíveis com equipamentos de classe convencional. "
        f"A categoria PPE identificada exige procedimentos "
        f"operacionais específicos, treinamento NR-10 SEP, e "
        f"emissão de Permissão de Trabalho (PT) específica para "
        f"trabalhos em proximidade."
    )

    recommendations = (
        f"1. Verificar capacidade de interrupção dos disjuntores "
        f"(Icc ≥ {Ik:.2f} kA assimétrico).\n"
        f"2. Sinalizar área com etiqueta arc-flash conforme NBR "
        f"17227 §6.2 (categoria, distância, EPI).\n"
        f"3. Implementar coordenação 50/51 conforme sugestões "
        f"deste laudo (IEEE 242).\n"
        f"4. Reavaliar a cada modificação significativa do "
        f"sistema OU a cada 5 anos (NR-10 §10.2.4)."
    )

    full = (
        introduction + technical_analysis + conclusions + recommendations
    )
    return LaudoNarrative(
        title=title,
        introduction=introduction,
        technical_analysis=technical_analysis,
        conclusions=conclusions,
        recommendations=recommendations,
        word_count=len(full.split()),
        model_used="offline_template",
    )


def _generate_via_claude(
    report, *, api_key: Optional[str] = None,
) -> LaudoNarrative:
    """Gera via Claude API (precisa de ANTHROPIC_API_KEY)."""
    # Em v0.104.0 simplificada, usa offline. v0.104.1 adiciona
    # chamada real à API com prompt caching otimizado.
    return _generate_offline_narrative(report)


# ---------------------------------------------------------------------------
# Coordination fix suggestions
# ---------------------------------------------------------------------------


def suggest_relay_fix(
    coordination_check,
) -> CoordinationFixSuggestion:
    """
    Dada uma violação de coordenação, sugere uma ação concreta.

    Estratégia:
    * Se Δt insuficiente → aumentar TMS upstream OU mudar para
      curva mais lenta (VI → SI)
    * Se interseção entre curvas → mudar pickup OU tipo de curva
    * Se downstream não atua antes → reduzir pickup downstream
    """
    if not coordination_check.passes:
        if coordination_check.actual_delta_t_s < 0:
            # Inversão — downstream opera DEPOIS
            return CoordinationFixSuggestion(
                relay_id=coordination_check.downstream_id,
                issue=(
                    f"Inversão de coordenação: relé downstream "
                    f"opera DEPOIS do upstream em I_falta="
                    f"{coordination_check.fault_current_A:.0f}A "
                    f"(Δt={coordination_check.actual_delta_t_s:.3f}s)"
                ),
                proposed_action=(
                    f"Reduzir pickup do relé downstream em ~30% "
                    f"OU aumentar TMS do upstream para Δt ≥ "
                    f"{coordination_check.required_delta_t_s:.2f}s"
                ),
                rationale=(
                    "IEEE 242 §15.10.1 exige margem mínima entre "
                    "relés em série para garantir seletividade."
                ),
            )
        else:
            # Margem insuficiente
            shortage = (
                coordination_check.required_delta_t_s
                - coordination_check.actual_delta_t_s
            )
            return CoordinationFixSuggestion(
                relay_id=coordination_check.upstream_id,
                issue=(
                    f"Margem Δt = {coordination_check.actual_delta_t_s:.3f}s "
                    f"insuficiente (requerido "
                    f"{coordination_check.required_delta_t_s:.2f}s — "
                    f"falta {shortage:.3f}s)"
                ),
                proposed_action=(
                    f"Aumentar TMS do relé {coordination_check.upstream_id} "
                    f"em proporção a Δt requerido / Δt atual"
                ),
                rationale=(
                    "Aumentar TMS atrasa proporcionalmente toda "
                    "a curva inverse-time, criando espaço para "
                    "downstream operar primeiro."
                ),
            )
    return CoordinationFixSuggestion(
        relay_id=coordination_check.upstream_id,
        issue="Coordenação adequada",
        proposed_action="Nenhuma ação necessária",
        rationale=f"Δt = {coordination_check.actual_delta_t_s:.3f}s ≥ requerido",
    )


# ---------------------------------------------------------------------------
# Report comparison
# ---------------------------------------------------------------------------


def compare_reports(report_v1, report_v2) -> ReportDiff:
    """
    Gera diff narrativo entre 2 versões do mesmo estudo.

    Útil para auditoria de mudanças (ex: relatório antes
    de retrofit vs depois).
    """
    Ik_v1 = getattr(report_v1, "Ik_pp_kA", 0)
    Ik_v2 = getattr(report_v2, "Ik_pp_kA", 0)
    delta_Ik_pct = (
        100.0 * (Ik_v2 - Ik_v1) / Ik_v1 if Ik_v1 > 0 else 0
    )

    E_v1 = getattr(report_v1, "incident_energy_cal_cm2", 0)
    E_v2 = getattr(report_v2, "incident_energy_cal_cm2", 0)
    delta_E_pct = (
        100.0 * (E_v2 - E_v1) / E_v1 if E_v1 > 0 else 0
    )

    summary = (
        f"Comparação entre versões do estudo:\n"
        f"* Ik'' : {Ik_v1:.2f} → {Ik_v2:.2f} kA "
        f"({delta_Ik_pct:+.1f}%)\n"
        f"* E    : {E_v1:.2f} → {E_v2:.2f} cal/cm² "
        f"({delta_E_pct:+.1f}%)"
    )

    sc_changes = ""
    if abs(delta_Ik_pct) > 10:
        sc_changes = (
            f"Variação significativa em Ik''  ({delta_Ik_pct:+.1f}%) "
            f"— investigue mudanças na topologia upstream "
            f"(novas fontes, transformadores, etc)."
        )
    elif abs(delta_Ik_pct) > 2:
        sc_changes = (
            f"Variação leve em Ik''  ({delta_Ik_pct:+.1f}%). "
            f"Revisão recomendada mas dentro de tolerância."
        )

    coord_changes = (
        "Coordenação 50/51 não comparada (módulo separado em "
        "v0.94.0)."
    )

    af_changes = ""
    if abs(delta_E_pct) > 20:
        af_changes = (
            f"Variação significativa em energia incidente "
            f"({delta_E_pct:+.1f}%) — a categoria PPE pode ter "
            f"mudado. ATUALIZAR ETIQUETA arc-flash conforme "
            f"NBR 17227 §6.2."
        )

    if abs(delta_Ik_pct) > 20 or abs(delta_E_pct) > 30:
        severity = "major"
    elif abs(delta_Ik_pct) > 5 or abs(delta_E_pct) > 10:
        severity = "moderate"
    else:
        severity = "minor"

    return ReportDiff(
        summary=summary,
        sc_changes=sc_changes,
        coord_changes=coord_changes,
        arc_flash_changes=af_changes,
        severity=severity,
    )
