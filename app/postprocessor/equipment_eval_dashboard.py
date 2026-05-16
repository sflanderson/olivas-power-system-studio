"""
app.postprocessor.equipment_eval_dashboard — HTML + CSV
dashboard generator para Equipment Evaluation
(v1.3.0 Fase B.3 — paridade SKM PTW dashboard tabular).

Filosofia
==========

PTW Power*Tools mostra Equipment Evaluation como **tabela
linha-por-equipamento × coluna-por-critério** com cores:

* Verde — PASS (margem confortável)
* Amarelo — WARN (margem reduzida)
* Vermelho — FAIL (rating excedido)
* Cinza — N/A (critério não aplica)

Este módulo gera:
* `generate_html_dashboard(reports)` → HTML standalone
  (CSS inline, sem deps externas)
* `export_csv(reports)` → CSV para Excel

Sem deps externas (sem jinja2, openpyxl, etc).

Compatibilidade
================

Consume `EvaluationReport` da Fase B.1 + `RuleResult` da Fase A.1.
"""

from __future__ import annotations

from html import escape

from app.postprocessor.coord_rules import RuleSeverity
from app.postprocessor.equipment_eval import EvaluationReport


# ---------------------------------------------------------------------------
# Cores semantic (paleta PTW corporativa Olivas)
# ---------------------------------------------------------------------------


_COLOR_PASS = "#2E7D32"      # verde
_COLOR_WARN = "#F9A825"      # amarelo
_COLOR_FAIL = "#C0392B"      # vermelho
_COLOR_NA   = "#9E9E9E"      # cinza
_COLOR_BG_PASS = "#E8F5E9"
_COLOR_BG_WARN = "#FFF8DC"
_COLOR_BG_FAIL = "#FDE8E6"
_COLOR_BG_NA   = "#F5F5F5"


def _color_for_severity(sev: RuleSeverity) -> tuple:
    """Retorna (text_color, background_color) por severity."""
    if sev == RuleSeverity.PASS:
        return _COLOR_PASS, _COLOR_BG_PASS
    if sev == RuleSeverity.WARN:
        return _COLOR_WARN, _COLOR_BG_WARN
    if sev == RuleSeverity.FAIL:
        return _COLOR_FAIL, _COLOR_BG_FAIL
    return _COLOR_NA, _COLOR_BG_NA


def _label_for_severity(sev: RuleSeverity) -> str:
    """Label curto para célula da tabela."""
    if sev == RuleSeverity.PASS:
        return "✓"
    if sev == RuleSeverity.WARN:
        return "⚠"
    if sev == RuleSeverity.FAIL:
        return "✗"
    return "—"


# ---------------------------------------------------------------------------
# CSS inline
# ---------------------------------------------------------------------------


_CSS = """
body {
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial,
                 sans-serif;
    margin: 20px;
    background: #FAFAFA;
    color: #212121;
}
h1 { color: #143250; margin-bottom: 0.2em; }
h2 { color: #143250; margin-top: 1.5em; }
.subtitle {
    color: #555;
    font-size: 0.9em;
    margin-top: 0;
}
table {
    border-collapse: collapse;
    margin: 1em 0;
    background: white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
th, td {
    border: 1px solid #E0E0E0;
    padding: 8px 12px;
    text-align: left;
    font-size: 0.9em;
}
th {
    background: #143250;
    color: white;
    font-weight: 600;
    text-align: center;
}
td.id { font-family: 'Consolas', monospace; font-weight: 600; }
td.criterion {
    text-align: center;
    font-weight: 600;
    font-size: 1.1em;
}
.summary-bar {
    display: inline-block;
    margin: 4px 8px 4px 0;
    padding: 6px 14px;
    border-radius: 4px;
    font-weight: 600;
}
.legend { font-size: 0.85em; margin-top: 1em; color: #666; }
.legend span {
    display: inline-block;
    margin-right: 12px;
    padding: 2px 8px;
    border-radius: 3px;
}
"""


# ---------------------------------------------------------------------------
# generate_html_dashboard
# ---------------------------------------------------------------------------


def generate_html_dashboard(
    reports: list,
    project_title: str = "Equipment Evaluation Dashboard",
    norm_reference: str = "IEEE 242 §15 + NBR 5410 §6.2.7",
) -> str:
    """
    Gera HTML standalone (sem deps externas) com tabela
    linha-por-equipamento × coluna-por-critério.

    Parameters
    ----------

    reports:
        Lista de EvaluationReport (de evaluate_project()).
    project_title:
        Título do dashboard.
    norm_reference:
        Sub-título com normas referenciadas.

    Returns
    -------

    str
        HTML completo (com <html>, <head>, <body>) — pode ser
        salvo direto e aberto em browser.
    """
    if not reports:
        return _empty_html(project_title)

    # Coleta todos os rule_ids únicos (preservando ordem de primeira aparição)
    rule_ids: list = []
    seen = set()
    for rep in reports:
        for r in rep.results:
            if r.rule_id not in seen:
                rule_ids.append(r.rule_id)
                seen.add(r.rule_id)

    # Sumário global
    total_pass = sum(len(r.passes()) for r in reports)
    total_warn = sum(len(r.warnings()) for r in reports)
    total_fail = sum(len(r.failures()) for r in reports)
    total_na = sum(len(r.not_applicables()) for r in reports)

    # Header
    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>{escape(project_title)}</title>
<style>{_CSS}</style>
</head>
<body>
<h1>{escape(project_title)}</h1>
<p class="subtitle">Olivas Power System Studio · Norma: {escape(norm_reference)}</p>

<h2>Sumário Global</h2>
<div>
<span class="summary-bar" style="background:{_COLOR_BG_PASS};color:{_COLOR_PASS}">
PASS: {total_pass}
</span>
<span class="summary-bar" style="background:{_COLOR_BG_WARN};color:{_COLOR_WARN}">
WARN: {total_warn}
</span>
<span class="summary-bar" style="background:{_COLOR_BG_FAIL};color:{_COLOR_FAIL}">
FAIL: {total_fail}
</span>
<span class="summary-bar" style="background:{_COLOR_BG_NA};color:{_COLOR_NA}">
N/A: {total_na}
</span>
</div>
"""

    # Tabela
    html += "<h2>Avaliação por Equipamento</h2>\n<table>\n<thead>\n<tr>\n"
    html += "<th>Equipment</th><th>Type</th><th>Status</th>"
    for rid in rule_ids:
        # Encurta rule_id para display (remove prefix EQ-)
        short = rid.replace("EQ-", "")
        html += f"<th title=\"{escape(rid)}\">{escape(short)}</th>"
    html += "\n</tr>\n</thead>\n<tbody>\n"

    for rep in reports:
        # Mapa rule_id → result para esta linha
        by_rule = {r.rule_id: r for r in rep.results}
        overall = rep.overall_status()
        overall_text_color, overall_bg = _color_for_severity(
            {
                "PASS": RuleSeverity.PASS,
                "WARN": RuleSeverity.WARN,
                "FAIL": RuleSeverity.FAIL,
                "N/A": RuleSeverity.NOT_APPLICABLE,
            }[overall]
        )
        html += "<tr>"
        html += f"<td class=\"id\">{escape(rep.equipment_id)}</td>"
        html += f"<td>{escape(rep.equipment_type)}</td>"
        html += (
            f"<td class=\"criterion\" "
            f"style=\"background:{overall_bg};color:{overall_text_color}\">"
            f"{escape(overall)}</td>"
        )
        for rid in rule_ids:
            r = by_rule.get(rid)
            if r is None:
                # Equipment não tinha esta rule (não deveria ocorrer se
                # todos compartem RuleSet, mas defensive)
                html += "<td>—</td>"
                continue
            text_c, bg_c = _color_for_severity(r.severity)
            label = _label_for_severity(r.severity)
            tooltip = escape(r.message)
            value = ""
            if r.evaluated_value is not None:
                value = f" {r.evaluated_value:.0f}%"
            html += (
                f"<td class=\"criterion\" "
                f"style=\"background:{bg_c};color:{text_c}\" "
                f"title=\"{tooltip}\">"
                f"{label}{escape(value)}"
                f"</td>"
            )
        html += "</tr>\n"

    html += "</tbody>\n</table>\n"

    # Legend
    html += """
<div class="legend">
<strong>Legenda:</strong>
<span style="background:""" + _COLOR_BG_PASS + ";color:" + _COLOR_PASS + """">
✓ PASS &lt;70%</span>
<span style="background:""" + _COLOR_BG_WARN + ";color:" + _COLOR_WARN + """">
⚠ WARN 70-100%</span>
<span style="background:""" + _COLOR_BG_FAIL + ";color:" + _COLOR_FAIL + """">
✗ FAIL &gt;100%</span>
<span style="background:""" + _COLOR_BG_NA + ";color:" + _COLOR_NA + """">
— N/A</span>
</div>
</body></html>"""

    return html


def _empty_html(title: str) -> str:
    """HTML para caso sem reports."""
    return f"""<!DOCTYPE html>
<html lang="pt-br"><head>
<meta charset="utf-8"><title>{escape(title)}</title>
<style>{_CSS}</style>
</head>
<body><h1>{escape(title)}</h1>
<p>Nenhum equipamento avaliado.</p>
</body></html>"""


# ---------------------------------------------------------------------------
# export_csv
# ---------------------------------------------------------------------------


def export_csv(reports: list, sep: str = ";") -> str:
    """
    Exporta dashboard como CSV (Excel-friendly).

    Layout: 1 linha por equipamento, colunas:
    Equipment, Type, Status, <rule_id>_severity, <rule_id>_value, ...

    Sem deps (csv module nativo, mas usamos formatação simples
    para controle total).
    """
    if not reports:
        return f"Equipment{sep}Type{sep}Status\n"

    rule_ids: list = []
    seen = set()
    for rep in reports:
        for r in rep.results:
            if r.rule_id not in seen:
                rule_ids.append(r.rule_id)
                seen.add(r.rule_id)

    # Header
    cols = ["Equipment", "Type", "Status"]
    for rid in rule_ids:
        cols.append(f"{rid}_severity")
        cols.append(f"{rid}_value_pct")
    lines = [sep.join(cols)]

    # Linhas
    for rep in reports:
        by_rule = {r.rule_id: r for r in rep.results}
        row = [
            rep.equipment_id,
            rep.equipment_type,
            rep.overall_status(),
        ]
        for rid in rule_ids:
            r = by_rule.get(rid)
            if r is None:
                row.append("")
                row.append("")
            else:
                row.append(r.severity.value.upper())
                if r.evaluated_value is not None:
                    row.append(f"{r.evaluated_value:.2f}")
                else:
                    row.append("")
        # Escape sep que possa estar nos values
        cleaned_row = [
            str(c).replace(sep, " ").replace("\n", " ")
            for c in row
        ]
        lines.append(sep.join(cleaned_row))

    return "\n".join(lines) + "\n"
