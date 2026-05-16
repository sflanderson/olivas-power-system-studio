"""
app.postprocessor.arc_flash_label — Custom Label Designer
para arc-flash hazard (v1.4.0 — paridade SKM PTW Label
Designer; último P0 do roadmap original AUDIT v1.1.0).

Filosofia
==========

PTW Power*Tools "Custom Label Designer" gera labels arc-flash
imprimíveis NFPA 70E / NESC com 30 text fields user-customizable
+ cores dinâmicas conforme PPE category. Estes labels são o
**deliverable visual** mais importante para compliance comercial
(NFPA 70E §130.5 exige label permanente em equipamento ≥50V que
exija arc-flash hazard analysis).

Olivas v1.3.x tinha o cálculo (`arc_flash.py::ArcFlashReport`)
mas SEM gerador de label. Esta sub-sprint A entrega:

* `ArcFlashLabel` dataclass com 30 fields
* `from_arc_flash_report(report, **overrides)` auto-fill
* 3 templates: `LabelStyle.NFPA_70E_2024` / `NESC_2023` / `MINIMAL_BR`
* `render_html_label(label, style)` → HTML print-ready

Sem deps externas (HTML standalone com CSS inline + @media print).

Cobertura normativa
====================

* NFPA 70E:2024 §130.5(H) (label requirements)
* NFPA 70E:2024 Tabela 130.7(C)(15)(c) (PPE categories 0-4)
* IEEE Std 1584-2018 (incident energy + DLA)
* NESC 2023 §410 (utility worker arc-flash labels)
* NBR 17227:2025 (arc-flash brasileiro)
* OSHA 29 CFR 1910.269 (HV >15 kV labeling)

Limitações documentadas
========================

* v1.4.0 entrega text fields only (30). Picture fields (8 BMP
  no PTW) ficam para v1.4.1+ (requer Pillow ou Qt QPixmap).
* v1.4.0 entrega 3 estilos hard-coded. Custom designer drag-drop
  fica para v1.4.2+.
* Multilingual Keyword Table: v1.4.0 PT-BR + EN. Espanhol/Frances
  via plugin v1.5+.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from html import escape
from typing import Optional


# ---------------------------------------------------------------------------
# Style enum
# ---------------------------------------------------------------------------


class LabelStyle(str, Enum):
    """
    Estilos de template disponíveis para o label.

    * **NFPA_70E_2024** — formato US padrão (NFPA 70E §130.5(H)),
      cabeçalho "ARC FLASH AND SHOCK HAZARD", caixa colorida por
      PPE category.
    * **NESC_2023_TYPE_4_5** — utility worker (linhas vivas HV),
      menos focado em PPE category, mais em distâncias de
      aproximação.
    * **MINIMAL_BR** — formato compacto NBR 17227, cabeçalho
      "ATENÇÃO RISCO ARCO ELÉTRICO", sem dependência de
      tabelas NFPA 70E (uso geral em projetos brasileiros).
    """

    NFPA_70E_2024 = "NFPA 70E 2024"
    NESC_2023_TYPE_4_5 = "NESC 2023 Type 4-5"
    MINIMAL_BR = "NBR 17227 Minimal"


# ---------------------------------------------------------------------------
# Cores dinâmicas por PPE category (NFPA 70E §130.5(H))
# ---------------------------------------------------------------------------


_PPE_CATEGORY_COLOR_MAP = {
    "0": ("#2E7D32", "#E8F5E9"),    # verde escuro / fundo verde claro
    "1": ("#7CB342", "#F1F8E9"),    # verde
    "2": ("#FBC02D", "#FFFDE7"),    # amarelo
    "3": ("#FB8C00", "#FFF3E0"),    # laranja
    "4": ("#E64A19", "#FBE9E7"),    # vermelho-laranja
    "DANGER": ("#C62828", "#FFEBEE"),  # vermelho intenso
}


def ppe_category_color(category: str) -> tuple:
    """
    Retorna (text_color, background_color) para a PPE category.

    Categoria normalizada via uppercase + strip. Fallback para
    cinza neutro se não reconhecida.
    """
    cat_norm = (category or "").strip().upper()
    return _PPE_CATEGORY_COLOR_MAP.get(cat_norm, ("#424242", "#F5F5F5"))


# ---------------------------------------------------------------------------
# ArcFlashLabel dataclass — 30 fields
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArcFlashLabel:
    """
    Label arc-flash imprimível com 30 fields.

    Convenção de fields
    --------------------

    Todos os fields são strings (para flexibilidade — engenheiro
    pode formatar como quiser). Construtor `from_arc_flash_report`
    formata números automaticamente.

    Para fields opcionais não preenchidos, usa string vazia
    (não None) — render HTML produz célula vazia em vez de
    "None".

    30 fields cobertos
    -------------------

    Identificação:
    1. ``bus_name``
    2. ``bus_kV``
    3. ``label_number``
    4. ``equipment_owner``

    Cálculos arc-flash:
    5. ``Ibf_kA``        (bolted fault current)
    6. ``Iarc_kA``       (arcing fault current)
    7. ``arc_duration_ms``
    8. ``equipment_type`` (Switchgear / Panel / MCC / Cable / Open Air)
    9. ``gap_mm``
    10. ``working_distance_mm``
    11. ``electrode_config`` (VCB / VCBB / HCB / VOA / HOA)
    12. ``incident_energy_cal_cm2``
    13. ``arc_flash_boundary_mm``

    PPE (NFPA 70E Tabela 130.7(C)(15)(c)):
    14. ``ppe_category``  ("0", "1", "2", "3", "4", "DANGER")
    15. ``ppe_description``
    16. ``ppe_arc_rating_min_cal_cm2``

    Aproximação elétrica (NFPA 70E §130.4(D)):
    17. ``limited_approach_mm``
    18. ``restricted_approach_mm``
    19. ``glove_class``  ("00", "0", "1", "2", "3", "4")
    20. ``glove_voltage_V``
    21. ``shock_hazard_voltage_V``
    22. ``flash_hazard_range``

    Equipment Protection details:
    23. ``head_eye_hearing_protection``
    24. ``hand_arm_protection``
    25. ``foot_protection``

    Notes & Audit:
    26. ``notes``  (e.g., "*N1 Mis-coordinated; *N9 Max arcing")
    27. ``date_computed``
    28. ``computed_by``
    29. ``project_title``
    30. ``audit_sha256``

    Cobertura normativa
    --------------------

    * NFPA 70E:2024 §130.5(H) (campo-by-campo do label)
    * NFPA 70E:2024 Tabela 130.7(C)(15)(c) (PPE categories)
    * NFPA 70E:2024 §130.4(D) (limited/restricted approach)
    * IEEE Std 1584-2018 §A4 (incident energy + DLA)
    * NESC 2023 §410 (utility worker MAD)
    * NBR 17227:2025 (label brasileiro)
    """

    # Identificação
    bus_name: str = ""
    bus_kV: str = ""
    label_number: str = ""
    equipment_owner: str = ""

    # Cálculos arc-flash
    Ibf_kA: str = ""
    Iarc_kA: str = ""
    arc_duration_ms: str = ""
    equipment_type: str = ""
    gap_mm: str = ""
    working_distance_mm: str = ""
    electrode_config: str = ""
    incident_energy_cal_cm2: str = ""
    arc_flash_boundary_mm: str = ""

    # PPE
    ppe_category: str = ""
    ppe_description: str = ""
    ppe_arc_rating_min_cal_cm2: str = ""

    # Aproximação elétrica
    limited_approach_mm: str = ""
    restricted_approach_mm: str = ""
    glove_class: str = ""
    glove_voltage_V: str = ""
    shock_hazard_voltage_V: str = ""
    flash_hazard_range: str = ""

    # Protections
    head_eye_hearing_protection: str = ""
    hand_arm_protection: str = ""
    foot_protection: str = ""

    # Notes & Audit
    notes: str = ""
    date_computed: str = ""
    computed_by: str = ""
    project_title: str = ""
    audit_sha256: str = ""

    @classmethod
    def from_arc_flash_report(
        cls, report, **overrides,
    ) -> "ArcFlashLabel":
        """
        Auto-fill a partir de ``ArcFlashReport`` (do
        ``app/postprocessor/arc_flash.py``).

        Mapeia os campos numéricos do report para strings
        formatadas (3 casas decimais p/ kA, 0 casas p/ mm).

        Permite override de qualquer field via kwargs.

        Examples
        --------

        ::

            label = ArcFlashLabel.from_arc_flash_report(
                report,
                project_title="Subestação São João",
                computed_by="Eng. Landerson F. Silva",
                label_number="AF-2026-001",
            )
        """
        # PPE description default por category
        cat = getattr(report.ppe_category, "value", "0")
        ppe_desc = {
            "0": "Camisa manga longa + calça (não-FR opcional)",
            "1": "AR ≥ 4 cal/cm² (camisa + calça arc-rated)",
            "2": "AR ≥ 8 cal/cm² (camisa + calça arc-rated, hood opcional)",
            "3": "AR ≥ 25 cal/cm² (suit completo arc-rated + hood)",
            "4": "AR ≥ 40 cal/cm² (suit completo + hood + flash hood)",
            "DANGER": "PROIBIDO trabalhar energizado — desligue e teste",
        }.get(cat, "Consulte tabela NFPA 70E 130.7(C)(15)(c)")

        # Glove class typical lookup por kV
        kv = report.rated_voltage_kV
        if kv <= 0.5:
            glove_class = "00"
            glove_v = "500"
        elif kv <= 1.0:
            glove_class = "0"
            glove_v = "1000"
        elif kv <= 7.5:
            glove_class = "1"
            glove_v = "7500"
        elif kv <= 17:
            glove_class = "2"
            glove_v = "17000"
        elif kv <= 26.5:
            glove_class = "3"
            glove_v = "26500"
        else:
            glove_class = "4"
            glove_v = "36000"

        # Limited / Restricted approach (NFPA 70E §130.4(D)) — valores
        # típicos por kV. Para precisão real, consultar Tabela 130.4(D)(b).
        if kv <= 0.05:
            limited_mm = "1067"
            restricted_mm = "Avoid contact"
        elif kv <= 0.6:
            limited_mm = "1067"  # 42 inches
            restricted_mm = "305"  # 12 inches
        elif kv <= 5.0:
            limited_mm = "1500"
            restricted_mm = "660"
        elif kv <= 15:
            limited_mm = "1830"  # 6 ft
            restricted_mm = "660"
        else:
            limited_mm = "2440"  # 8 ft
            restricted_mm = "790"

        defaults = dict(
            bus_name=report.case_label,
            bus_kV=f"{report.rated_voltage_kV:.3f}",
            Ibf_kA=f"{report.Ibf_kA:.3f}",
            Iarc_kA=f"{report.Iarc_kA:.3f}",
            arc_duration_ms=f"{report.arc_duration_ms:.0f}",
            equipment_type=getattr(
                report.equipment_class, "value", "Switchgear",
            ),
            gap_mm=f"{report.gap_mm:.0f}",
            working_distance_mm=f"{report.working_distance_mm:.0f}",
            electrode_config=getattr(
                report.electrode_config, "value", "VCB",
            ),
            incident_energy_cal_cm2=f"{report.incident_energy_cal_cm2:.3f}",
            arc_flash_boundary_mm=f"{report.arc_flash_boundary_mm:.0f}",
            ppe_category=cat,
            ppe_description=ppe_desc,
            ppe_arc_rating_min_cal_cm2=(
                f"{report.ppe_arc_rating_min_cal_cm2:.1f}"
            ),
            limited_approach_mm=limited_mm,
            restricted_approach_mm=restricted_mm,
            glove_class=glove_class,
            glove_voltage_V=glove_v,
            shock_hazard_voltage_V=f"{int(report.rated_voltage_kV * 1000)}",
            flash_hazard_range=f"{report.incident_energy_cal_cm2:.1f}",
            head_eye_hearing_protection=(
                "Capacete classe E + face-shield arc-rated + "
                "protetor auricular"
            ),
            hand_arm_protection=(
                f"Luvas isolantes classe {glove_class} + luvas "
                f"de proteção mecânica sobreposta"
            ),
            foot_protection="Botas dielétricas + biqueira composite",
        )
        defaults.update(overrides)
        return cls(**defaults)


# ---------------------------------------------------------------------------
# CSS templates por estilo
# ---------------------------------------------------------------------------


_CSS_BASE = """
* { box-sizing: border-box; }
body {
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial,
                 sans-serif;
    margin: 0;
    padding: 20px;
    color: #212121;
}
.label-container {
    border: 4px solid #C62828;
    max-width: 600px;
    background: white;
    padding: 0;
    page-break-inside: avoid;
}
.label-header {
    background: #C62828;
    color: white;
    padding: 12px 16px;
    font-weight: 700;
    font-size: 18pt;
    text-align: center;
    letter-spacing: 1px;
}
.label-section {
    padding: 8px 16px;
    border-bottom: 1px solid #E0E0E0;
}
.label-section h3 {
    margin: 0 0 6px 0;
    font-size: 10pt;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.label-row {
    display: flex;
    justify-content: space-between;
    margin: 2px 0;
    font-size: 10pt;
}
.label-row .label-key {
    color: #666;
    flex: 1;
}
.label-row .label-value {
    color: #212121;
    font-weight: 600;
    text-align: right;
    flex: 1;
}
.ppe-banner {
    padding: 16px;
    text-align: center;
    font-size: 14pt;
    font-weight: 700;
}
.notes-section {
    background: #FAFAFA;
    padding: 8px 16px;
    font-size: 9pt;
    color: #555;
    font-style: italic;
}
.audit-section {
    background: #F5F5F5;
    padding: 6px 16px;
    font-size: 8pt;
    color: #888;
    font-family: 'Consolas', monospace;
    border-top: 2px solid #BDBDBD;
}
@media print {
    body { padding: 0; }
    .label-container { border-width: 4px; }
}
"""


# ---------------------------------------------------------------------------
# render_html_label
# ---------------------------------------------------------------------------


def _row(key: str, value: str) -> str:
    """Helper: renderiza uma linha key/value (escape XSS)."""
    if not value:
        return ""
    return (
        f'<div class="label-row">'
        f'<span class="label-key">{escape(key)}</span>'
        f'<span class="label-value">{escape(value)}</span>'
        f'</div>'
    )


def render_html_label(
    label: ArcFlashLabel,
    style: LabelStyle = LabelStyle.NFPA_70E_2024,
) -> str:
    """
    Renderiza HTML print-ready do label arc-flash.

    Parameters
    ----------

    label:
        ArcFlashLabel a renderizar.
    style:
        LabelStyle (NFPA_70E_2024 / NESC_2023_TYPE_4_5 /
        MINIMAL_BR). Cada estilo tem layout/header diferente.

    Returns
    -------

    str
        HTML completo standalone (com <html>, <head>, <body>) e
        CSS inline + @media print.

    Cobertura
    ----------

    * NFPA 70E:2024 §130.5(H) (campos obrigatórios do label)
    * NESC 2023 §410 (utility worker fields)
    * NBR 17227 (header em PT-BR)
    """
    text_color, bg_color = ppe_category_color(label.ppe_category)

    if style == LabelStyle.NFPA_70E_2024:
        header_text = "⚠ ARC FLASH AND SHOCK HAZARD ⚠"
        section1_title = "Arc Flash Hazard"
        section2_title = "Shock Hazard / Approach Boundaries"
    elif style == LabelStyle.NESC_2023_TYPE_4_5:
        header_text = "⚠ HIGH VOLTAGE — ARC FLASH RISK ⚠"
        section1_title = "Energy & Boundary"
        section2_title = "Live Line Approach (NESC §410)"
    else:  # MINIMAL_BR
        header_text = "⚠ ATENÇÃO — RISCO DE ARCO ELÉTRICO ⚠"
        section1_title = "Energia Incidente / DLA"
        section2_title = "Distâncias de Aproximação (NR-10)"

    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Arc-Flash Label — {escape(label.bus_name)}</title>
<style>{_CSS_BASE}</style>
</head>
<body>

<div class="label-container">

  <div class="label-header">{header_text}</div>

  <div class="ppe-banner" style="background:{bg_color};color:{text_color}">
    PPE Category: {escape(label.ppe_category or '?')}
    {' — ' + escape(label.ppe_description) if label.ppe_description else ''}
  </div>

  <div class="label-section">
    <h3>Identificação</h3>
    {_row("Bus", label.bus_name)}
    {_row("Tensão (kV)", label.bus_kV)}
    {_row("Label #", label.label_number)}
    {_row("Equipment Owner", label.equipment_owner)}
    {_row("Project", label.project_title)}
  </div>

  <div class="label-section">
    <h3>{section1_title}</h3>
    {_row("Ibf — Bolted Fault (kA)", label.Ibf_kA)}
    {_row("Iarc — Arcing (kA)", label.Iarc_kA)}
    {_row("Arc Duration (ms)", label.arc_duration_ms)}
    {_row("Equipment Type", label.equipment_type)}
    {_row("Gap (mm)", label.gap_mm)}
    {_row("Working Distance (mm)", label.working_distance_mm)}
    {_row("Electrode Config", label.electrode_config)}
    {_row("Incident Energy (cal/cm²)", label.incident_energy_cal_cm2)}
    {_row("Arc-Flash Boundary / DLA (mm)", label.arc_flash_boundary_mm)}
    {_row("Min Arc Rating PPE (cal/cm²)", label.ppe_arc_rating_min_cal_cm2)}
  </div>

  <div class="label-section">
    <h3>{section2_title}</h3>
    {_row("Limited Approach (mm)", label.limited_approach_mm)}
    {_row("Restricted Approach (mm)", label.restricted_approach_mm)}
    {_row("Glove Class", label.glove_class)}
    {_row("Glove Voltage (V)", label.glove_voltage_V)}
    {_row("Shock Hazard Voltage (V)", label.shock_hazard_voltage_V)}
    {_row("Flash Hazard Range (cal/cm²)", label.flash_hazard_range)}
  </div>

  <div class="label-section">
    <h3>EPI Adicional</h3>
    {_row("Cabeça/olhos/audição", label.head_eye_hearing_protection)}
    {_row("Mãos/braços", label.hand_arm_protection)}
    {_row("Pés", label.foot_protection)}
  </div>

  {f'<div class="notes-section"><strong>Notes:</strong> {escape(label.notes)}</div>' if label.notes else ''}

  <div class="audit-section">
    {f"Date: {escape(label.date_computed)}<br>" if label.date_computed else ""}
    {f"Computed By: {escape(label.computed_by)}<br>" if label.computed_by else ""}
    {f"Audit SHA256: {escape(label.audit_sha256)}" if label.audit_sha256 else ""}
  </div>

</div>

</body>
</html>"""
    return html
