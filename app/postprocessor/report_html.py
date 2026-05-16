"""
app.postprocessor.report_html — gerador de relatório HTML
auto-contido para análise consolidada de barramentos.

Inclui gráficos via matplotlib (incorporados como base64 PNG):

* **TC curves overlap** — curvas tempo-corrente dos relés
  sugeridos em escala log-log, com pickup e Ik''.
* **Arc-flash boundary** — círculo concentrico com working
  distance e DLA.
* **Motor decay curves** — exponencial NBR 17227 §4.2.2
  (3-8 ciclos) para cada motor identificado.
* **Topology diagram** — diagrama hierarquico simplificado
  da cadeia BUS → fontes (multi-hop walking).

Saída: arquivo HTML standalone, abrir em qualquer navegador.
Sem dependências externas no runtime do navegador (todos os
gráficos embeded via base64).

Workflow
========

::

    from app.postprocessor.bus_pipeline import (
        analyze_bus_full_pipeline,
    )
    from app.postprocessor.report_html import save_html_report

    report = analyze_bus_full_pipeline(
        project, "BUS-MAIN",
        coordination_clearing_time_ms=500.0,
        use_multi_hop=True,
        multi_vendor_suggestions=True,
    )
    save_html_report(report, "report-BUS-MAIN.html")

Dependências
=============

* matplotlib (já em ``requirements.txt``).
* base64 (stdlib).

Limitações MVP
===============

* Topology diagram é puramente textual (boxes ASCII via
  matplotlib). Diagrama vetorial completo fica para v0.27.7.11.
* CSS simples — sem framework externo. Aparência industrial
  estilo ATPDraw/PowerWorld.

Referências
============

* IEEE 242-2001 (Buff Book) §15 — TC curves layout
* IEC 60909-0 §6 — SC analysis
* NBR 17227:2025 §5 — arc-flash + relay coord
* NFPA 70E:2024 — PPE categorization
"""

from __future__ import annotations

import base64
import html
import io
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from app.commercial.feature_gates import Feature, requires_feature

from app.postprocessor.audit_trail import (
    KNOWN_LIMITATIONS,
    citation,
    format_limitations_html,
    make_audit_header,
)

if TYPE_CHECKING:
    from app.postprocessor.bus_pipeline import BusPipelineReport
    from app.postprocessor.relay_suggestions import RelaySuggestion


# v0.92: limitações relevantes ao bus_pipeline (SC + arc-flash
# + coordenação). Aplicadas a todos os relatórios pipeline.
_BUS_PIPELINE_LIMITATIONS = (
    "sc_ib_far_only",
    "sc_method_b_kappa",
    "arc_flash_lv_only",
    "arc_flash_3p_only",
    "coord_no_auto_dt_min",
)

# v0.92: normas formalmente referenciadas no relatório
# bus_pipeline. Order = order of appearance nos cálculos.
_BUS_PIPELINE_STANDARDS = (
    "IEC 60909-0",
    "NBR 17227",
    "IEEE 1584",
    "IEEE 242",
    "NFPA 70E",
)


# ---------------------------------------------------------------------------
# Helpers de plot
# ---------------------------------------------------------------------------


def _plot_to_base64_png(fig, dpi: int = 100) -> str:
    """
    Converte matplotlib Figure → base64 PNG string.
    Útil para embed em HTML como ``<img src="data:image/png;base64,...">``.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("ascii")
    buf.close()
    return encoded


def _logo_data_uri() -> str:
    """
    v0.83: retorna o logo do Olivas Power System Studio como data URI
    para embed direto em HTML (sem dependência externa).

    Returns
    -------
    str
        ``data:image/png;base64,...`` ou string vazia se logo
        não encontrado.
    """
    from pathlib import Path
    logo_path = (
        Path(__file__).resolve().parent.parent
        / "resources" / "logo.png"
    )
    if not logo_path.is_file():
        return ""
    try:
        b = logo_path.read_bytes()
        encoded = base64.b64encode(b).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except OSError:
        return ""


def _plot_tc_curves(
    suggestions: tuple,
    Ik_pp_A: float,
    title: str = "Time-Current Curves (TCC)",
) -> Optional[str]:
    """
    Plota TC curves dos relés sugeridos em escala log-log.

    Marca:
    * Pickup horizontal de cada curva
    * Ik'' vertical (corrente de SC)
    * Operate time em cada curva no Ik''

    Returns
    -------
    str
        base64 PNG string. Vazio se matplotlib indisponível.
    """
    if not suggestions:
        return None

    try:
        import matplotlib
        matplotlib.use("Agg")  # backend sem GUI
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return None

    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    ax.set_xscale("log")
    ax.set_yscale("log")

    # Currents axis (multiplos do menor pickup)
    min_pickup = min(s.pickup_51_A for s in suggestions)
    I_range = np.logspace(
        math.log10(min_pickup * 1.01),
        math.log10(max(Ik_pp_A * 1.5, min_pickup * 100)),
        200,
    )

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    for i, sg in enumerate(suggestions):
        curve = sg.tc_curve_51
        times = []
        for I in I_range:
            try:
                t = curve.operate_time_s(I)
            except Exception:
                t = float("inf")
            if math.isfinite(t):
                times.append(t)
            else:
                times.append(None)
        # Filter Nones
        I_plot = [I for I, t in zip(I_range, times) if t is not None]
        t_plot = [t for t in times if t is not None]
        ax.plot(
            I_plot, t_plot,
            label=f"{sg.relay_model_id} (51 {sg.curve_51_type})",
            color=colors[i % len(colors)],
            linewidth=2,
        )
        # Pickup marker
        ax.axvline(
            sg.pickup_51_A,
            color=colors[i % len(colors)],
            linestyle=":", alpha=0.6, linewidth=1,
        )

    # Ik'' marker
    ax.axvline(
        Ik_pp_A, color="red", linestyle="--",
        linewidth=2, label=f"Ik''  = {Ik_pp_A/1000:.2f} kA",
    )

    ax.set_xlabel("Current (A)", fontsize=11)
    ax.set_ylabel("Operate time (s)", fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_ylim(0.01, 100)

    encoded = _plot_to_base64_png(fig)
    plt.close(fig)
    return encoded


def _plot_arc_flash_boundary(
    incident_energy_cal_cm2: float,
    DLA_mm: float,
    working_distance_mm: float,
    ppe_category: str,
) -> Optional[str]:
    """
    Visualização da fronteira arc-flash (DLA) com working distance.

    Círculos concêntricos:
    * Centro (vermelho): ponto do arco
    * working_distance (laranja): trabalhador
    * DLA (amarelo): fronteira limite (1.2 cal/cm²)
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.patches import Circle
    except ImportError:
        return None

    fig, ax = plt.subplots(figsize=(7, 7), dpi=100)
    max_r = max(DLA_mm, working_distance_mm) * 1.2

    # Cor pela categoria PPE
    cat_color = {
        "0": "#2ecc71",  # verde
        "1": "#f1c40f",
        "2": "#e67e22",
        "3": "#e74c3c",
        "4": "#c0392b",
        "DANGER": "#000000",
    }.get(ppe_category, "#7f8c8d")

    # Centro (arco)
    arc = Circle((0, 0), 50, color="#c0392b", alpha=0.9, zorder=10)
    ax.add_patch(arc)
    # Working distance
    wd_circle = Circle(
        (0, 0), working_distance_mm, fill=False,
        edgecolor="#3498db", linewidth=2.5, linestyle="--",
        zorder=5,
    )
    ax.add_patch(wd_circle)
    # DLA
    dla_circle = Circle(
        (0, 0), DLA_mm, fill=False,
        edgecolor=cat_color, linewidth=2.0, linestyle="-",
        zorder=4,
    )
    ax.add_patch(dla_circle)

    # Labels
    ax.annotate(
        "Arc point", xy=(0, 0), xytext=(150, 100),
        fontsize=9, color="#c0392b", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#c0392b"),
    )
    ax.annotate(
        f"Working dist = {working_distance_mm:.0f} mm",
        xy=(working_distance_mm, 0),
        xytext=(working_distance_mm + 100, 200),
        fontsize=9, color="#3498db", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#3498db"),
    )
    ax.annotate(
        f"DLA (1.2 cal/cm²) = {DLA_mm:.0f} mm",
        xy=(DLA_mm * 0.7, DLA_mm * 0.7),
        xytext=(DLA_mm * 0.7, DLA_mm * 1.05),
        fontsize=10, color=cat_color, fontweight="bold",
        ha="center",
    )

    ax.set_xlim(-max_r, max_r)
    ax.set_ylim(-max_r, max_r)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("Distance (mm)", fontsize=10)
    ax.set_ylabel("Distance (mm)", fontsize=10)
    ax.set_title(
        f"Arc-Flash Boundary — Cat {ppe_category} "
        f"(E = {incident_energy_cal_cm2:.2f} cal/cm²)",
        fontsize=12, fontweight="bold",
    )

    encoded = _plot_to_base64_png(fig)
    plt.close(fig)
    return encoded


def _plot_motor_decay(
    motors_info: list[dict],
    title: str = "Motor SC Contribution Decay (NBR 17227 §4.2.2)",
) -> Optional[str]:
    """
    Plota decaimento da contribuição de motores no tempo.

    motors_info: lista de dicts com keys:
    * 'name': string
    * 'I_LR_kA': contribuição inicial
    * 'Td_pp_ms': constante de tempo
    * 'type': 'induction' ou 'synchronous'
    """
    if not motors_info:
        return None

    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return None

    fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
    t_ms = np.linspace(0, 200, 200)

    colors = ["#3498db", "#e67e22", "#9b59b6", "#16a085"]
    for i, m in enumerate(motors_info):
        I_LR = m.get("I_LR_kA", 1.0)
        td = m.get("Td_pp_ms", 20.0)
        I_t = I_LR * np.exp(-t_ms / td)
        ax.plot(
            t_ms, I_t,
            label=f"{m['name']} ({m.get('type', 'induction')}, "
                  f"τ={td:.0f} ms, I_LR={I_LR:.2f} kA)",
            color=colors[i % len(colors)],
            linewidth=2,
        )

    # Limite NBR 17227 (3-8 ciclos = 50-133 ms)
    ax.axvspan(50, 133, alpha=0.15, color="green",
               label="NBR 17227: 3-8 cycles (IM)")

    ax.set_xlabel("Time after fault (ms)", fontsize=11)
    ax.set_ylabel("Motor SC contribution (kA)", fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_xlim(0, 200)
    ax.set_ylim(bottom=0)

    encoded = _plot_to_base64_png(fig)
    plt.close(fig)
    return encoded


def _plot_topology_diagram(
    bus_id: str,
    chains: tuple,
    title: str = "Topology Diagram (multi-hop walking)",
) -> Optional[str]:
    """
    Diagrama esquemático da topologia: BUS alvo no centro com
    cadeias hierarquicas saindo para as fontes.
    """
    if not chains:
        return None

    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch
    except ImportError:
        return None

    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, max(len(chains) + 2, 4))
    ax.axis("off")

    # BUS alvo no canto direito
    bus_x = 8.5
    bus_y = (max(len(chains), 2) + 1) / 2
    bus_box = FancyBboxPatch(
        (bus_x - 0.5, bus_y - 0.3), 1.6, 0.6,
        boxstyle="round,pad=0.05",
        edgecolor="#34495e", facecolor="#3498db",
        linewidth=2,
    )
    ax.add_patch(bus_box)
    ax.text(
        bus_x + 0.3, bus_y, bus_id,
        ha="center", va="center", fontsize=10,
        fontweight="bold", color="white",
    )

    # Para cada chain, desenha série
    for i, chain in enumerate(chains):
        y = (len(chains) - i)
        # Source à esquerda
        src_x = 0.3
        ax.add_patch(FancyBboxPatch(
            (src_x, y - 0.25), 1.2, 0.5,
            boxstyle="round,pad=0.05",
            edgecolor="#27ae60", facecolor="#2ecc71",
            linewidth=2,
        ))
        ax.text(
            src_x + 0.6, y, chain.source_component.name,
            ha="center", va="center", fontsize=9,
            fontweight="bold", color="white",
        )

        # Intermediários (TRs) entre source e bus
        n_trs = len(chain.intermediate_transformers)
        n_buses = len(chain.intermediate_buses)
        n_intermediate = n_trs + n_buses
        if n_intermediate > 0:
            x_step = (bus_x - 1.5 - (src_x + 1.2)) / (n_intermediate + 1)
            x_pos = src_x + 1.2 + x_step
            # TRs primeiro (em direção à fonte)
            for tr in reversed(chain.intermediate_transformers):
                ax.add_patch(FancyBboxPatch(
                    (x_pos, y - 0.2), 0.9, 0.4,
                    boxstyle="round,pad=0.03",
                    edgecolor="#7f8c8d", facecolor="#bdc3c7",
                    linewidth=1.5,
                ))
                ax.text(
                    x_pos + 0.45, y, tr.name,
                    ha="center", va="center", fontsize=8,
                )
                x_pos += x_step
            for bus_int in reversed(chain.intermediate_buses):
                ax.add_patch(FancyBboxPatch(
                    (x_pos, y - 0.2), 0.9, 0.4,
                    boxstyle="round,pad=0.03",
                    edgecolor="#34495e", facecolor="#85c1e2",
                    linewidth=1.5,
                ))
                ax.text(
                    x_pos + 0.45, y, bus_int.name,
                    ha="center", va="center", fontsize=8,
                )
                x_pos += x_step

        # Linha conectando source → bus
        ax.annotate(
            "",
            xy=(bus_x - 0.5, bus_y),
            xytext=(src_x + 1.2, y),
            arrowprops=dict(
                arrowstyle="->",
                color="#34495e",
                linewidth=1.5,
                connectionstyle="arc3,rad=0.15",
            ),
        )

        # Hops label
        ax.text(
            (src_x + 1.2 + bus_x - 0.5) / 2,
            (y + bus_y) / 2 - 0.3,
            f"{chain.n_hops} hops",
            fontsize=8, color="#7f8c8d", style="italic",
            ha="center",
        )

    ax.set_title(title, fontsize=12, fontweight="bold")
    encoded = _plot_to_base64_png(fig)
    plt.close(fig)
    return encoded


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


_HTML_CSS = """
/* v0.83 — Paleta Oliveira (cream + olive + brand accents) */
body { font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
       margin: 0; padding: 20px;
       background-color: #EFF0E8; color: #2A2D24; }
.container { max-width: 1100px; margin: 0 auto;
             background-color: #FAFAF5; padding: 30px;
             border: 1px solid #B5D4A8;
             box-shadow: 0 2px 8px rgba(85, 107, 47, 0.08); }
h1 { color: #556B2F; border-bottom: 3px solid #6B8E23;
     padding-bottom: 8px; margin-top: 0; }
h2 { color: #556B2F; border-bottom: 1px solid #B5D4A8;
     padding-bottom: 4px; margin-top: 30px; }
h3 { color: #6B8E23; margin-top: 20px; }
table { border-collapse: collapse; width: 100%; margin: 15px 0; }
th, td { border: 1px solid #B5D4A8; padding: 8px 12px;
         text-align: left; }
th { background-color: #556B2F; color: #FAFAF5; }
tr:nth-child(even) { background-color: #EFF0E8; }
.kpi { display: inline-block; padding: 12px 20px;
       margin: 5px; border-radius: 6px; min-width: 130px;
       text-align: center;
       border: 1px solid #B5D4A8;
       background: linear-gradient(135deg, #FAFAF5 0%, #EFF0E8 100%); }
.kpi-value { font-size: 22px; font-weight: bold; display: block;
             color: #556B2F; }
.kpi-label { font-size: 11px; color: #5C4D3C; }
.cat-0 { background: #d4efdf; color: #186a3b; }
.cat-1 { background: #fef9e7; color: #7d6608; }
.cat-2 { background: #fdebd0; color: #784212; }
.cat-3 { background: #fadbd8; color: #6e2c00; }
.cat-4 { background: #f5b7b1; color: #641e16; }
.cat-DANGER { background: #1c2833; color: white; }
pre { background-color: #1c1f1a; color: #BFFF00;
      padding: 15px; border-radius: 4px; overflow-x: auto;
      font-family: 'Consolas', 'Courier New', Courier, monospace;
      font-size: 13px; line-height: 1.4;
      border-left: 3px solid #6B8E23; }
img { max-width: 100%; height: auto; display: block;
      margin: 15px auto; }
img.report-figure { border: 1px solid #B5D4A8;
                     border-radius: 4px;
                     box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
.footer { color: #5C4D3C; font-size: 11px; margin-top: 40px;
          padding-top: 15px; border-top: 2px solid #556B2F; }
.tag { display: inline-block; padding: 3px 10px; border-radius: 12px;
       background-color: #B5D4A8; font-size: 11px;
       color: #556B2F; margin-right: 4px; font-weight: 500; }
a { color: #7E2BA8; text-decoration: none; }
a:hover { text-decoration: underline; color: #9B59B6; }
.brand-accent { color: #BFFF00; }
/* v0.92 — Audit trail blocks (ISO 9001 / NR-10 traceability) */
.audit-header { border: 2px solid #556B2F; padding: 16px 20px;
                margin: 0 0 24px 0; background-color: #FAFAF5;
                box-shadow: inset 0 0 0 1px #B5D4A8; }
.audit-header .audit-title { color: #556B2F; margin: 0 0 12px 0;
                              font-size: 17px; letter-spacing: 0.5px;
                              border-bottom: 2px solid #6B8E23;
                              padding-bottom: 6px; }
.audit-header table.audit-meta { width: 100%; margin: 8px 0;
                                   border: 0; }
.audit-header table.audit-meta th { background: transparent;
                                      color: #556B2F; text-align: right;
                                      width: 200px; font-size: 12px;
                                      border: 0; padding: 5px 12px 5px 0;
                                      vertical-align: top;
                                      font-weight: 600; }
.audit-header table.audit-meta td { background: transparent;
                                      color: #2A2D24; font-size: 13px;
                                      border: 0; padding: 5px 0;
                                      vertical-align: top; }
.audit-header table.audit-meta tr:nth-child(even) { background: transparent; }
.audit-header table.audit-meta code { background: #EFF0E8;
                                        padding: 2px 6px; border-radius: 3px;
                                        color: #7E2BA8;
                                        font-family: 'Consolas', monospace;
                                        font-size: 12px; }
.audit-header table.audit-meta ul { margin: 0; padding-left: 18px;
                                      font-size: 12px; }
.audit-header table.audit-meta em { color: #87A96B; font-size: 11px; }
.audit-notes { margin-top: 12px; padding-top: 10px;
                 border-top: 1px dashed #B5D4A8; font-size: 12px;
                 color: #5C4D3C; }
.audit-limitations { border-left: 4px solid #D4AF37;
                       background-color: #FEF9E7; padding: 14px 18px;
                       margin: 24px 0; border-radius: 0 6px 6px 0; }
.audit-limitations h3 { color: #7D6608; margin: 0 0 10px 0;
                          font-size: 14px; font-weight: 600; }
.audit-limitations ul { margin: 0; padding-left: 22px; font-size: 12px;
                          line-height: 1.6; color: #5C4D3C; }
.audit-limitations li { margin-bottom: 6px; }
.citation-footnote { color: #5C4D3C; font-size: 10px; font-style: italic;
                      margin-top: 4px; }
"""


@requires_feature(Feature.PDF_PROFESSIONAL)
def generate_html_report(
    report: "BusPipelineReport",
    *,
    responsible_engineer: str = "",
    crea_number: str = "",
    art_number: str = "",
    notes: str = "",
) -> str:
    """
    Gera o HTML auto-contido da análise do BUS.

    Estrutura do report:

    1. **Audit header** (v0.92): SHA256 + normas + responsável.
    2. Header visual (bus_id, ratings, panel_type, AFD).
    3. KPIs (Ik'', E, DLA, Cat PPE).
    4. Topology (sources_summary + diagram).
    5. SC Analysis (IEC 60909-0 numbers + citations).
    6. Arc-flash (NBR 17227 + NFPA 70E + boundary plot).
    7. Topology Chains (multi-hop, se aplicável).
    8. Relay Suggestions (TC curves overlap + vendor formats).
    9. Warnings.
    10. **Limitations** (v0.92): bloco amarelo destacando heurísticas.
    11. Footer com refs normativas.

    Parameters
    ----------
    responsible_engineer, crea_number, art_number, notes
        v0.92: identificação do responsável técnico para
        rastreabilidade ISO 9001 / NR-10. Vazio = "(a preencher)".
    """
    sections = []

    # 1. Audit header (v0.92) — primeiro bloco do relatório
    sections.append(_build_audit_header_block(
        report,
        responsible_engineer=responsible_engineer,
        crea_number=crea_number,
        art_number=art_number,
        notes=notes,
    ))

    # 2. Header visual
    sections.append(_build_header(report))

    # 3. KPIs
    sections.append(_build_kpi_block(report))

    # 4. Topology (sources + diagram)
    sections.append(_build_topology_section(report))

    # 5. SC + Arc-flash
    sections.append(_build_sc_arcflash_section(report))

    # 6. Arc-flash boundary plot
    sections.append(_build_arcflash_boundary_section(report))

    # 7. Topology chains (multi-hop)
    if report.topology_chains:
        sections.append(_build_topology_chains_section(report))

    # 8. Relay suggestions com TC curves + vendor formats
    if report.relay_suggestions:
        sections.append(_build_relay_section(report))

    # 9. Warnings
    if report.warnings:
        sections.append(_build_warnings_section(report))

    # 10. Limitations (v0.92) — heurísticas declaradas
    sections.append(_build_limitations_block(report))

    # 11. Footer
    sections.append(_build_footer())

    body = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Bus Pipeline Report — {html.escape(report.bus_id)}</title>
<style>{_HTML_CSS}</style>
</head>
<body>
<div class="container">
{body}
</div>
</body>
</html>
"""


def _build_audit_header_block(
    r: "BusPipelineReport",
    *,
    responsible_engineer: str = "",
    crea_number: str = "",
    art_number: str = "",
    notes: str = "",
) -> str:
    """
    v0.92: renderiza o bloco de identificação profissional
    (audit header) — primeiro elemento do relatório, contendo:

    * Identidade do software (versão + checksum SHA256 dos inputs).
    * Timestamp imutável.
    * Catálogo de normas aplicadas (com títulos completos).
    * Responsável técnico (CREA + ART).
    * Notas técnicas livres.

    Atende:
    * NBR ISO 9001 (rastreabilidade documental).
    * NR-10 §10.2.4 (responsabilidade técnica).
    * NBR 17227 §5.4.4 (assinatura do responsável).
    * NFPA 70E §130.5(C) (rastreabilidade do estudo).
    """
    header = make_audit_header(
        report_kind=f"Análise consolidada — Barramento {r.bus_id}",
        inputs=r,
        standards_applied=list(_BUS_PIPELINE_STANDARDS),
        responsible_engineer=responsible_engineer,
        crea_number=crea_number,
        art_number=art_number,
        notes=notes,
    )
    return header.to_html()


def _build_limitations_block(r: "BusPipelineReport") -> str:
    """
    v0.92: bloco amarelo destacando as limitações técnicas
    aplicadas no MVP. Cumpre o Princípio 4 da auditabilidade:
    "Limitações declaradas explicitamente."

    A lista é dinâmica — só inclui limitações relevantes ao
    escopo do relatório (SC, arc-flash, coordenação).
    """
    applied = list(_BUS_PIPELINE_LIMITATIONS)

    # Adiciona limitações condicionais
    if not r.has_AFD:
        # Se não tem AFD, não há ressalva relevante extra
        pass
    if r.rated_voltage_kV > 15.0:
        # arc_flash_lv_only realmente limita aqui
        # (já está em applied; mantém destaque)
        pass

    return format_limitations_html(applied)


def _build_header(r: "BusPipelineReport") -> str:
    """
    v0.83: header com logo Olivas + título + tags + assinatura
    normativa.

    Layout:

    ::

        ┌─────────┬──────────────────────────────────────┐
        │  LOGO   │  Bus Pipeline Analysis Report — XXX │
        │ 96×96px │  [tags: panel | V | side | AFD]      │
        │         │  Análise IEC/NBR/IEEE...             │
        └─────────┴──────────────────────────────────────┘
    """
    afd_str = "ON" if r.has_AFD else "OFF"
    side_str = "LINESIDE" if r.is_lineside else "LOADSIDE"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logo_uri = _logo_data_uri()
    logo_html = ""
    if logo_uri:
        logo_html = (
            f'<img src="{logo_uri}" alt="Olivas Power System Studio" '
            'style="width: 96px; height: 96px; '
            'object-fit: contain; flex-shrink: 0;" />'
        )
    return f"""
<div style="display: flex; align-items: center; gap: 24px;
            border-bottom: 3px solid #556B2F; padding-bottom: 16px;
            margin-bottom: 16px;">
  {logo_html}
  <div style="flex: 1;">
    <h1 style="margin: 0; color: #556B2F;">
      Bus Pipeline Analysis Report — {html.escape(r.bus_id)}
    </h1>
    <p style="margin: 8px 0 4px 0;">
      <span class="tag">{html.escape(r.panel_type)}</span>
      <span class="tag">{r.rated_voltage_kV:.2f} kV</span>
      <span class="tag">{html.escape(side_str)}</span>
      <span class="tag">AFD: {afd_str}</span>
      <span class="tag">{timestamp}</span>
    </p>
    <p style="color: #5C4D3C; font-size: 12px; margin: 4px 0 0 0;
              font-style: italic;">
      Análise conforme IEC 60909-0:2016, ABNT NBR 17227:2025,
      IEEE 1584-2018, IEEE 242-2001 (Buff Book), NFPA 70E:2024.
    </p>
  </div>
</div>
"""


def _build_kpi_block(r: "BusPipelineReport") -> str:
    cat = r.ppe_category
    return f"""
<h2>Key Performance Indicators</h2>
<div>
  <div class="kpi">
    <span class="kpi-value">{r.Ik_pp_kA:.2f}</span>
    <span class="kpi-label">Ik'' (kA)</span>
  </div>
  <div class="kpi">
    <span class="kpi-value">{r.ip_kA:.2f}</span>
    <span class="kpi-label">ip (kA peak)</span>
  </div>
  <div class="kpi">
    <span class="kpi-value">{r.incident_energy_cal_cm2:.2f}</span>
    <span class="kpi-label">E (cal/cm²)</span>
  </div>
  <div class="kpi">
    <span class="kpi-value">{r.arc_flash_boundary_mm:.0f}</span>
    <span class="kpi-label">DLA (mm)</span>
  </div>
  <div class="kpi cat-{html.escape(cat)}">
    <span class="kpi-value">CAT {html.escape(cat)}</span>
    <span class="kpi-label">PPE Category (NFPA 70E)</span>
  </div>
</div>
"""


def _build_topology_section(r: "BusPipelineReport") -> str:
    rows = "\n".join(
        f'    <tr><td>{html.escape(s)}</td></tr>'
        for s in r.sources_summary
    )
    img_html = ""
    if r.topology_chains:
        b64 = _plot_topology_diagram(r.bus_id, r.topology_chains)
        if b64:
            img_html = (
                f'<img src="data:image/png;base64,{b64}" '
                f'alt="Topology diagram">'
            )

    return f"""
<h2>📡 Topology</h2>
<p>
  <strong>Neighbors:</strong> {r.n_neighbors} &nbsp;|&nbsp;
  <strong>SC sources:</strong> {r.n_sc_sources}
</p>
<table>
  <tr><th>Source contributions</th></tr>
{rows}
</table>
{img_html}
"""


def _build_sc_arcflash_section(r: "BusPipelineReport") -> str:
    """
    v0.92: tabelas SC e Arc-flash com **citação explícita
    da norma + equação** ao lado de cada valor calculado.
    Cumpre Princípio 2 da auditabilidade: rastreabilidade
    norma → resultado.
    """
    afd_marker = (
        f"AFD override (T={r.effective_clearing_time_ms:.0f} ms)"
        if r.has_AFD else "Sem AFD"
    )
    cit_ikpp = citation("IEC 60909-0", "§4.3.1", "Eq.(31)")
    cit_ip = citation("IEC 60909-0", "§4.3.1.2", "Eq.(43)")
    cit_kappa = citation("IEC 60909-0", "§4.3.1.2", "Method B")
    cit_clearing = citation("IEEE 242", "§15.10")
    cit_inc_energy = citation("NBR 17227", "§5.2.6.2", "Eq.(3-6)")
    cit_dla = citation("NBR 17227", "§5.2.6.5", "Eq.(7)")
    cit_ppe = citation("NFPA 70E", "Tabela 130.5(G)")
    return f"""
<h2>⚡ Short-Circuit Analysis (IEC 60909-0:2016)</h2>
<table>
  <tr><th>Parameter</th><th>Value</th><th>Norma — equação</th></tr>
  <tr><td>Initial symmetric current Ik''</td>
      <td>{r.Ik_pp_kA:.3f} kA</td>
      <td><code>{html.escape(cit_ikpp)}</code></td></tr>
  <tr><td>Peak SC current ip</td>
      <td>{r.ip_kA:.3f} kA</td>
      <td><code>{html.escape(cit_ip)}</code></td></tr>
  <tr><td>κ factor</td>
      <td>{r.kappa:.4f}</td>
      <td><code>{html.escape(cit_kappa)}</code></td></tr>
</table>

<h2>🔥 Arc-Flash Analysis (NBR 17227:2025 / IEEE 1584-2018)</h2>
<table>
  <tr><th>Parameter</th><th>Value</th><th>Norma — equação</th></tr>
  <tr><td>Coordination clearing time</td>
      <td>{r.coordination_clearing_time_ms:.0f} ms</td>
      <td><code>{html.escape(cit_clearing)}</code></td></tr>
  <tr><td>Effective clearing time</td>
      <td>{r.effective_clearing_time_ms:.0f} ms ({afd_marker})</td>
      <td><em>derivado coord + AFD</em></td></tr>
  <tr><td>Incident energy</td>
      <td>{r.incident_energy_cal_cm2:.3f} cal/cm² =
          {r.incident_energy_cal_cm2 * 4.184:.3f} J/cm²</td>
      <td><code>{html.escape(cit_inc_energy)}</code></td></tr>
  <tr><td>Arc-flash boundary (DLA)</td>
      <td>{r.arc_flash_boundary_mm:.0f} mm</td>
      <td><code>{html.escape(cit_dla)}</code></td></tr>
  <tr><td>NFPA 70E PPE Category</td>
      <td><span class="cat-{html.escape(r.ppe_category)}"
                style="padding:3px 8px;border-radius:3px;">
          Cat {html.escape(r.ppe_category)}</span></td>
      <td><code>{html.escape(cit_ppe)}</code></td></tr>
</table>
"""


def _build_arcflash_boundary_section(r: "BusPipelineReport") -> str:
    # Working distance default por panel type — usa NBR Tabela 3
    wd_mm = 914.4 if "kv" in r.panel_type.lower() else 457.2
    b64 = _plot_arc_flash_boundary(
        r.incident_energy_cal_cm2,
        r.arc_flash_boundary_mm,
        wd_mm,
        r.ppe_category,
    )
    if not b64:
        return ""
    return f"""
<h3>Arc-flash boundary visualization</h3>
<img src="data:image/png;base64,{b64}" alt="Arc-flash boundary">
"""


def _build_topology_chains_section(r: "BusPipelineReport") -> str:
    rows = []
    for i, chain in enumerate(r.topology_chains, 1):
        rows.append(
            f'    <tr>'
            f'<td>#{i}</td>'
            f'<td>{chain.n_hops}</td>'
            f'<td>{html.escape(chain.describe())}</td>'
            f'</tr>'
        )
    return f"""
<h2>🔗 Topology Chains (multi-hop walking, IEC 60909-0 §6.3)</h2>
<table>
  <tr><th>#</th><th>Hops</th><th>Path</th></tr>
{chr(10).join(rows)}
</table>
"""


def _build_relay_section(r: "BusPipelineReport") -> str:
    # TC curves overlap
    Ik_pp_A = r.Ik_pp_kA * 1000.0
    tc_b64 = _plot_tc_curves(r.relay_suggestions, Ik_pp_A)
    img_html = ""
    if tc_b64:
        img_html = (
            f'<img src="data:image/png;base64,{tc_b64}" '
            f'alt="TC curves overlap">'
        )

    blocks = []
    for sg in r.relay_suggestions:
        vendor = sg.to_vendor_format()
        blocks.append(
            f'<h3>{html.escape(sg.relay_model_id)} '
            f'<span class="tag">{html.escape(sg.application)}</span></h3>'
            f'<p style="font-size:13px;color:#7f8c8d">'
            f'I_n = {sg.rated_current_A:.1f} A &nbsp;|&nbsp; '
            f'Ik'' = {sg.Ik_pp_kA:.2f} kA &nbsp;|&nbsp; '
            f'Curva 51: {html.escape(sg.curve_51_standard)} '
            f'{html.escape(sg.curve_51_type)} '
            f'(TMS={sg.tms_51:.3f})</p>'
            f'<pre>{html.escape(vendor)}</pre>'
        )
    blocks_html = "\n".join(blocks)

    return f"""
<h2>🛡️ Relay Settings Suggestions (IEEE 242 §15)</h2>
{img_html}
{blocks_html}
"""


def _build_warnings_section(r: "BusPipelineReport") -> str:
    items = "\n".join(
        f"  <li>{html.escape(w)}</li>" for w in r.warnings
    )
    return f"""
<h2>⚠️ Warnings</h2>
<ul>
{items}
</ul>
"""


def _build_footer() -> str:
    """
    v0.83: footer com logo miniatura + assinatura normativa
    em paleta Oliveira (olive-deep border + bark text).
    """
    try:
        from app.core.version import VERSION
    except ImportError:
        VERSION = "0.83.0"
    logo_uri = _logo_data_uri()
    logo_html = ""
    if logo_uri:
        logo_html = (
            f'<img src="{logo_uri}" alt="Olivas" '
            'style="width: 32px; height: 32px; '
            'vertical-align: middle; margin-right: 8px;" />'
        )
    return f"""
<div class="footer" style="border-top: 2px solid #556B2F;
     padding: 16px 12px; margin-top: 24px; color: #5C4D3C;
     font-size: 11px; text-align: center;
     background-color: #FAFAF5;">
  {logo_html}
  <strong style="color: #556B2F;">Olivas Power System Studio</strong>
  &mdash; ATP Power System Simulation
  &mdash; <span style="color: #7E2BA8;">v{VERSION}</span>
  <br>
  <span style="font-style: italic;">
    Standards: IEC 60909-0:2016 &middot; IEC 60255-151 &middot;
    IEC 62271-100 &middot; ABNT NBR 17227:2025 &middot;
    IEEE Std 1584-2018 &middot; IEEE Std 242-2001 (Buff Book)
    &middot; IEEE C37.112-2018 &middot; NFPA 70E:2024 &middot;
    ANSI/IEEE C37.2.
  </span>
</div>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@requires_feature(Feature.PDF_PROFESSIONAL)
def save_html_report(
    report: "BusPipelineReport",
    path: str,
    *,
    responsible_engineer: str = "",
    crea_number: str = "",
    art_number: str = "",
    notes: str = "",
) -> None:
    """
    Gera e salva o relatório HTML auto-contido no path indicado.

    O arquivo resultante pode ser aberto em qualquer navegador
    moderno — todos os gráficos estão embeded em base64.

    v0.92: aceita identificação do responsável técnico para
    rastreabilidade ISO 9001 / NR-10 (forwarded para
    :func:`generate_html_report`).
    """
    html_str = generate_html_report(
        report,
        responsible_engineer=responsible_engineer,
        crea_number=crea_number,
        art_number=art_number,
        notes=notes,
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_str)
