"""
app.postprocessor.report_pdf — gerador de relatório PDF
multi-página da análise consolidada de barramentos.

Estratégia
==========

Usa **matplotlib PdfPages** (já disponível) para gerar PDFs
multi-página sem adicionar dependências externas (reportlab,
weasyprint, etc.). Cada página é uma ``matplotlib.figure.Figure``
com layout customizado:

* **Texto** via ``fig.text(x, y, ...)`` posicionado em
  coordenadas relativas (0..1).
* **Tabelas** via ``axes.table()``.
* **Gráficos** reutilizando helpers de ``report_html.py``.

Páginas
========

1. **Capa**: título, bus_id, ratings, panel_type, KPIs grandes.
2. **Topology**: diagrama da cadeia + tabela de fontes.
3. **SC Analysis**: tabela IEC 60909-0 + dados brutos.
4. **Arc-Flash Analysis**: tabela NBR 17227 + boundary plot.
5. **TC Curves**: log-log dos relés sugeridos.
6. **Relay Settings**: vendor format por fabricante (texto).
7. **Footer page**: warnings + refs normativas.

Workflow
========

::

    from app.postprocessor.bus_pipeline import (
        analyze_bus_full_pipeline,
    )
    from app.postprocessor.report_pdf import save_pdf_report

    report = analyze_bus_full_pipeline(
        project, "BUS-MAIN",
        coordination_clearing_time_ms=500.0,
        use_multi_hop=True,
        multi_vendor_suggestions=True,
    )
    save_pdf_report(report, "report-BUS-MAIN.pdf")

Dependências
=============

* matplotlib (já em ``requirements.txt``).

Limitações MVP
===============

* Sem hyperlinks internos (matplotlib não suporta nativamente).
* Texto monoespaçado em blocos vendor — não aplica syntax
  highlighting.
* Layout fixo A4 portrait. Para landscape ou outros tamanhos,
  parâmetros futuros.

Referências
============

* matplotlib backends.backend_pdf documentation.
* IEEE 242-2001 (Buff Book) — formato de relatórios técnicos.
* ABNT NBR 6022 — Documentação técnica (estrutura).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.postprocessor.audit_trail import (
    KNOWN_LIMITATIONS,
    citation,
    make_audit_header,
)

if TYPE_CHECKING:
    from app.postprocessor.bus_pipeline import BusPipelineReport


# v0.92: limitações relevantes ao bus_pipeline (idem report_html)
_BUS_PIPELINE_LIMITATIONS = (
    "sc_ib_far_only",
    "sc_method_b_kappa",
    "arc_flash_lv_only",
    "arc_flash_3p_only",
    "coord_no_auto_dt_min",
)

_BUS_PIPELINE_STANDARDS = (
    "IEC 60909-0",
    "NBR 17227",
    "IEEE 1584",
    "IEEE 242",
    "NFPA 70E",
)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------


# Layout A4 retrato em polegadas (matplotlib usa polegadas)
_A4_WIDTH_IN = 8.27
_A4_HEIGHT_IN = 11.69

# Cores Cat PPE (mesmas do HTML)
_CAT_COLORS = {
    "0": "#2ecc71",
    "1": "#f1c40f",
    "2": "#e67e22",
    "3": "#e74c3c",
    "4": "#c0392b",
    "DANGER": "#1c2833",
}


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------


def _build_audit_cover_page(
    fig,
    report: "BusPipelineReport",
    *,
    responsible_engineer: str,
    crea_number: str,
    art_number: str,
    notes: str,
) -> None:
    """
    v0.92: PRIMEIRA página do PDF — capa profissional auditável.

    Layout vertical em A4:

    ::

        ┌────────────────────────────────────────┐
        │       RELATÓRIO TÉCNICO                │
        │  Análise consolidada — BUS-MAIN        │
        │  ──────────────────────────────────    │
        │  Software:   Olivas Power Sys. v0.92.2 │
        │  Gerado em:  2026-04-26T12:34:56       │
        │  Checksum:   SHA256:ab12cd34ef56…       │
        │                                        │
        │  Normas aplicadas:                     │
        │   • IEC 60909-0:2016 — Short-circuit   │
        │   • ABNT NBR 17227:2025 — Arco         │
        │   • IEEE Std 1584-2018 — Arc-flash     │
        │   • IEEE Std 242-2001 — Coord (Buff)   │
        │   • NFPA 70E:2024 — PPE                │
        │                                        │
        │  Responsável técnico: ___________      │
        │  CREA / Registro:     ___________      │
        │  ART:                 ___________      │
        │  Assinatura:          ___________      │
        │                                        │
        │  Observações: …                        │
        └────────────────────────────────────────┘

    Cumpre Princípios 1+3+4 da auditabilidade:
    identidade do cálculo, responsabilidade técnica,
    limitações declaradas (in line abaixo).
    """
    header = make_audit_header(
        report_kind=f"Análise consolidada — Barramento {report.bus_id}",
        inputs=report,
        standards_applied=list(_BUS_PIPELINE_STANDARDS),
        responsible_engineer=responsible_engineer,
        crea_number=crea_number,
        art_number=art_number,
        notes=notes,
    )

    # Logo no topo
    from pathlib import Path
    logo_path = (
        Path(__file__).resolve().parent.parent
        / "resources" / "logo.png"
    )
    if logo_path.is_file():
        try:
            import matplotlib.image as mpimg
            img = mpimg.imread(str(logo_path))
            ax_logo = fig.add_axes([0.06, 0.88, 0.10, 0.10])
            ax_logo.imshow(img)
            ax_logo.axis("off")
        except Exception:
            pass

    # Título
    fig.text(
        0.5, 0.94, "RELATÓRIO TÉCNICO",
        ha="center", va="top", fontsize=20, fontweight="bold",
        color="#556B2F",
    )
    fig.text(
        0.5, 0.91, header.report_kind,
        ha="center", va="top", fontsize=14, color="#5C4D3C",
        style="italic",
    )

    # Linha decorativa
    fig.patches.append(__mpl_rect(
        (0.10, 0.88), 0.80, 0.002,
        facecolor="#6B8E23", edgecolor="#6B8E23",
    ))

    # Bloco software / timestamp / checksum
    y = 0.83
    fig.text(0.10, y, "Software:", fontsize=10, fontweight="bold",
             color="#556B2F")
    fig.text(0.30, y,
             f"{header.software_name} v{header.software_version}",
             fontsize=10, color="#2A2D24")
    y -= 0.025
    fig.text(0.10, y, "Gerado em:", fontsize=10, fontweight="bold",
             color="#556B2F")
    fig.text(0.30, y, header.timestamp_iso,
             fontsize=10, color="#2A2D24")
    y -= 0.025
    fig.text(0.10, y, "Checksum (inputs):", fontsize=10,
             fontweight="bold", color="#556B2F")
    fig.text(0.30, y,
             f"SHA256:{header.input_checksum[:32]}…",
             fontsize=9, family="monospace", color="#7E2BA8")

    # Bloco normas aplicadas
    y -= 0.045
    fig.text(0.10, y, "Normas aplicadas:", fontsize=11,
             fontweight="bold", color="#556B2F")
    from app.postprocessor.audit_trail import STANDARDS_CATALOG
    y -= 0.025
    for std in header.standards_applied:
        full = STANDARDS_CATALOG.get(std, std)
        # Trunca em 90 chars para caber na largura A4
        if len(full) > 90:
            full = full[:87] + "…"
        fig.text(0.12, y, f"•  {full}", fontsize=9, color="#2A2D24")
        y -= 0.022

    # Bloco responsável técnico
    y -= 0.025
    fig.patches.append(__mpl_rect(
        (0.08, y - 0.16), 0.84, 0.16,
        facecolor="#FAFAF5", edgecolor="#B5D4A8",
        linewidth=1.5,
    ))
    fig.text(0.10, y - 0.015, "RESPONSABILIDADE TÉCNICA",
             fontsize=11, fontweight="bold", color="#556B2F")

    eng = header.responsible_engineer or "_" * 50
    crea = header.crea_number or "_" * 50
    art = header.art_number or "_" * 50

    y2 = y - 0.045
    fig.text(0.10, y2, "Engenheiro:", fontsize=10, fontweight="bold")
    fig.text(0.28, y2, eng, fontsize=10, color="#2A2D24")
    y2 -= 0.025
    fig.text(0.10, y2, "CREA / Registro:",
             fontsize=10, fontweight="bold")
    fig.text(0.28, y2, crea, fontsize=10, color="#2A2D24")
    y2 -= 0.025
    fig.text(0.10, y2, "ART:", fontsize=10, fontweight="bold")
    fig.text(0.28, y2, art, fontsize=10, color="#2A2D24")
    y2 -= 0.025
    fig.text(0.10, y2, "Assinatura:", fontsize=10, fontweight="bold")
    fig.text(0.28, y2, "_" * 50, fontsize=10, color="#7f8c8d")

    # Notas (se houver)
    if header.notes:
        y2 -= 0.05
        fig.text(0.10, y2, "Observações:",
                 fontsize=10, fontweight="bold", color="#5C4D3C")
        y2 -= 0.022
        # Quebra em linhas de ~80 chars
        for ln in header.notes.splitlines():
            for i in range(0, len(ln), 80):
                fig.text(0.12, y2, ln[i:i + 80],
                         fontsize=9, color="#2A2D24")
                y2 -= 0.020
                if y2 < 0.10:
                    break
            if y2 < 0.10:
                break

    # Footer
    fig.text(
        0.5, 0.05,
        "Este relatório foi gerado automaticamente. "
        "Validade depende de revisão e assinatura por engenheiro habilitado.",
        ha="center", va="bottom", fontsize=8, color="#5C4D3C",
        style="italic",
    )


def _build_cover_page(fig, report: "BusPipelineReport") -> None:
    """
    Página 1: capa com logo Olivas + título + bus_id + KPIs.

    v0.83: logo posicionado no topo (canto superior esquerdo,
    1.5 inch quadrado), título reposicionado, paleta Oliveira
    (#556B2F olive-deep + #6B8E23 olive-medium).

    Layout:

    ::

        ┌─────┬─────────────────────────────────┐
        │LOGO │  Bus Pipeline Analysis Report    │
        │     │  BUS-MAIN-13.8                   │
        └─────┴─────────────────────────────────┘
        (tags: panel | V | side | AFD)
        Generated: timestamp
        ┌─KPI─┬─KPI─┬─KPI─┬─KPI─┬─KPI─┐
        ...
        Topology Summary
        ...
        Olivas Power System Studio · standards
    """
    # ---- Logo (canto superior esquerdo) ----
    from pathlib import Path
    logo_path = (
        Path(__file__).resolve().parent.parent
        / "resources" / "logo.png"
    )
    if logo_path.is_file():
        try:
            import matplotlib.image as mpimg
            img = mpimg.imread(str(logo_path))
            ax_logo = fig.add_axes([0.06, 0.86, 0.10, 0.10])
            ax_logo.imshow(img)
            ax_logo.axis("off")
        except Exception:
            pass

    # ---- Título + bus_id ao lado do logo ----
    fig.text(
        0.20, 0.94,
        "Bus Pipeline Analysis Report",
        ha="left", va="top", fontsize=18, fontweight="bold",
        color="#556B2F",   # OLIVE_DEEP
    )
    fig.text(
        0.20, 0.91,
        report.bus_id,
        ha="left", va="top", fontsize=22, fontweight="bold",
        color="#7E2BA8",   # PURPLE_DEEP (logo "ATP")
    )

    # Tagline brand
    fig.text(
        0.20, 0.875,
        "Olivas Power System Studio — ATP Power System Simulation",
        ha="left", va="top", fontsize=9, color="#6B8E23",
        style="italic",
    )

    # ---- Tags ----
    side_str = "LINESIDE" if report.is_lineside else "LOADSIDE"
    afd_str = "AFD ON" if report.has_AFD else "AFD OFF"
    tag_text = (
        f"{report.panel_type}  •  {report.rated_voltage_kV:.2f} kV  •  "
        f"{side_str}  •  {afd_str}"
    )
    fig.text(
        0.5, 0.83, tag_text,
        ha="center", va="top", fontsize=11, color="#5C4D3C",   # OLIVE_BARK
    )

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fig.text(
        0.5, 0.81, f"Generated: {timestamp}",
        ha="center", va="top", fontsize=9, color="#87A96B",   # OLIVE_LIGHT
        style="italic",
    )

    # KPI block (5 boxes) — paleta Oliveira para acentos
    kpis = [
        (f"{report.Ik_pp_kA:.2f}", "Ik'' (kA)", "#0077B5"),    # cyan logo
        (f"{report.ip_kA:.2f}", "ip (kA peak)", "#0077B5"),
        (
            f"{report.incident_energy_cal_cm2:.2f}",
            "E (cal/cm²)", "#D4AF37",   # OLIVE_GOLD
        ),
        (
            f"{report.arc_flash_boundary_mm:.0f}",
            "DLA (mm)", "#7E2BA8",   # PURPLE_DEEP (logo)
        ),
        (
            f"CAT {report.ppe_category}",
            "PPE Category", _CAT_COLORS.get(
                report.ppe_category, "#5C4D3C"
            ),
        ),
    ]

    n_kpis = len(kpis)
    box_width = 0.16
    spacing = 0.02
    total_width = n_kpis * box_width + (n_kpis - 1) * spacing
    x_start = (1.0 - total_width) / 2

    y_box_top = 0.72
    y_box_bottom = 0.60

    for i, (value, label, color) in enumerate(kpis):
        x_left = x_start + i * (box_width + spacing)
        # Background box
        fig.patches.append(
            __mpl_rect(
                (x_left, y_box_bottom),
                box_width, y_box_top - y_box_bottom,
                facecolor=color, alpha=0.15, edgecolor=color,
            )
        )
        fig.text(
            x_left + box_width / 2, y_box_bottom + 0.075, value,
            ha="center", va="center",
            fontsize=18, fontweight="bold", color=color,
        )
        fig.text(
            x_left + box_width / 2, y_box_bottom + 0.025, label,
            ha="center", va="center",
            fontsize=8, color="#7f8c8d",
        )

    # Topology summary
    fig.text(
        0.1, 0.50, "Topology Summary",
        fontsize=14, fontweight="bold", color="#556B2F",   # OLIVE_DEEP
    )
    fig.text(
        0.1, 0.47,
        f"Neighbors: {report.n_neighbors}  |  "
        f"SC sources: {report.n_sc_sources}",
        fontsize=11, color="#2A2D24",
    )

    y_pos = 0.43
    for src in report.sources_summary:
        fig.text(
            0.12, y_pos, f"• {src}",
            fontsize=10, color="#2A2D24",
        )
        y_pos -= 0.025

    # Footer da capa — versão dinâmica + brand
    try:
        from app.core.version import VERSION
    except ImportError:
        VERSION = "0.83.0"
    fig.text(
        0.5, 0.05,
        f"Generated by Olivas Power System Studio v{VERSION}\n"
        "Standards: IEC 60909-0 · NBR 17227:2025 · "
        "IEEE 1584-2018 · IEEE 242 · NFPA 70E:2024",
        ha="center", va="bottom", fontsize=8, color="#5C4D3C",   # BARK
        style="italic",
    )
    # Linha decorativa olive
    fig.patches.append(
        __mpl_rect(
            (0.10, 0.085), 0.80, 0.001,
            facecolor="#6B8E23", edgecolor="#6B8E23",
        ),
    )


def __mpl_rect(xy, width, height, **kwargs):
    """Helper: cria matplotlib Rectangle com boas defaults."""
    from matplotlib.patches import Rectangle
    return Rectangle(xy, width, height, **kwargs)


def _build_topology_page(fig, report: "BusPipelineReport") -> None:
    """Página: topology diagram + cadeias de fontes."""
    fig.text(
        0.5, 0.96, "Topology — Multi-hop Walking",
        ha="center", va="top", fontsize=16, fontweight="bold",
        color="#2c3e50",
    )
    fig.text(
        0.5, 0.93,
        "BFS over transformers and buses (IEC 60909-0 §6.3)",
        ha="center", va="top", fontsize=10, color="#7f8c8d",
    )

    if report.topology_chains:
        # Diagram (60% of page)
        ax_diag = fig.add_axes([0.05, 0.50, 0.90, 0.40])
        _render_topology_axes(ax_diag, report)

        # Tabela de cadeias
        ax_tbl = fig.add_axes([0.05, 0.10, 0.90, 0.35])
        ax_tbl.axis("off")
        rows = [
            [f"#{i+1}", str(chain.n_hops), chain.describe()[:80]]
            for i, chain in enumerate(report.topology_chains)
        ]
        ax_tbl.table(
            cellText=rows,
            colLabels=["#", "Hops", "Path"],
            colWidths=[0.05, 0.08, 0.87],
            cellLoc="left", loc="upper left",
        )
    else:
        # Fall back: lista textual
        fig.text(
            0.5, 0.7,
            "No multi-hop chains discovered.\n"
            "Use 1-hop walking results (sources_summary above).",
            ha="center", va="center", fontsize=11, color="#7f8c8d",
            style="italic",
        )

    _add_footer(fig, "Topology")


def _render_topology_axes(ax, report: "BusPipelineReport") -> None:
    """Desenha o diagrama topology no axis fornecido."""
    from matplotlib.patches import FancyBboxPatch

    chains = report.topology_chains
    if not chains:
        ax.axis("off")
        return

    ax.set_xlim(0, 10)
    ax.set_ylim(0, max(len(chains) + 2, 4))
    ax.axis("off")

    # BUS alvo
    bus_x = 8.5
    bus_y = (max(len(chains), 2) + 1) / 2
    ax.add_patch(FancyBboxPatch(
        (bus_x - 0.5, bus_y - 0.3), 1.6, 0.6,
        boxstyle="round,pad=0.05",
        edgecolor="#34495e", facecolor="#3498db",
        linewidth=2,
    ))
    ax.text(
        bus_x + 0.3, bus_y, report.bus_id,
        ha="center", va="center", fontsize=10,
        fontweight="bold", color="white",
    )

    for i, chain in enumerate(chains):
        y = (len(chains) - i)
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

        n_int = (
            len(chain.intermediate_transformers)
            + len(chain.intermediate_buses)
        )
        if n_int > 0:
            x_step = (bus_x - 1.5 - (src_x + 1.2)) / (n_int + 1)
            x_pos = src_x + 1.2 + x_step
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

        ax.annotate(
            "",
            xy=(bus_x - 0.5, bus_y),
            xytext=(src_x + 1.2, y),
            arrowprops=dict(
                arrowstyle="->", color="#34495e",
                linewidth=1.5,
                connectionstyle="arc3,rad=0.15",
            ),
        )
        ax.text(
            (src_x + 1.2 + bus_x - 0.5) / 2,
            (y + bus_y) / 2 - 0.3,
            f"{chain.n_hops} hops",
            fontsize=8, color="#7f8c8d", style="italic",
            ha="center",
        )


def _build_sc_arcflash_page(fig, report: "BusPipelineReport") -> None:
    """Página com tabelas SC + Arc-flash."""
    fig.text(
        0.5, 0.96, "Short-Circuit & Arc-Flash Analysis",
        ha="center", va="top", fontsize=16, fontweight="bold",
        color="#2c3e50",
    )

    # SC table
    ax_sc = fig.add_axes([0.10, 0.65, 0.80, 0.22])
    ax_sc.axis("off")
    ax_sc.set_title(
        "IEC 60909-0:2016 — Short-Circuit Analysis",
        fontsize=12, fontweight="bold", color="#34495e",
        loc="left", pad=10,
    )
    sc_data = [
        ["Initial symmetric current Ik''",
         f"{report.Ik_pp_kA:.3f} kA"],
        ["Peak SC current ip", f"{report.ip_kA:.3f} kA"],
        ["κ factor", f"{report.kappa:.4f}"],
    ]
    tbl_sc = ax_sc.table(
        cellText=sc_data,
        colLabels=["Parameter", "Value"],
        colWidths=[0.65, 0.35],
        cellLoc="left", loc="upper left",
    )
    tbl_sc.auto_set_font_size(False)
    tbl_sc.set_fontsize(10)
    tbl_sc.scale(1, 1.3)

    # Arc-flash table
    ax_af = fig.add_axes([0.10, 0.30, 0.80, 0.30])
    ax_af.axis("off")
    ax_af.set_title(
        "NBR 17227:2025 / IEEE 1584-2018 — Arc-Flash Analysis",
        fontsize=12, fontweight="bold", color="#34495e",
        loc="left", pad=10,
    )
    afd_marker = (
        f"AFD override (T={report.effective_clearing_time_ms:.0f} ms)"
        if report.has_AFD else "No AFD"
    )
    af_data = [
        ["Coordination clearing time",
         f"{report.coordination_clearing_time_ms:.0f} ms"],
        ["Effective clearing time",
         f"{report.effective_clearing_time_ms:.0f} ms ({afd_marker})"],
        ["Incident energy",
         f"{report.incident_energy_cal_cm2:.3f} cal/cm²"],
        ["Arc-flash boundary (DLA)",
         f"{report.arc_flash_boundary_mm:.0f} mm"],
        ["NFPA 70E PPE Category",
         f"Cat {report.ppe_category}"],
    ]
    tbl_af = ax_af.table(
        cellText=af_data,
        colLabels=["Parameter", "Value"],
        colWidths=[0.55, 0.45],
        cellLoc="left", loc="upper left",
    )
    tbl_af.auto_set_font_size(False)
    tbl_af.set_fontsize(10)
    tbl_af.scale(1, 1.3)

    # Cor da Cat PPE row
    cat_color = _CAT_COLORS.get(report.ppe_category, "#7f8c8d")
    cell = tbl_af[5, 1]   # row 5 (Cat PPE), col 1 (value)
    cell.set_facecolor(cat_color)
    cell.set_text_props(color="white", fontweight="bold")

    _add_footer(fig, "Short-Circuit & Arc-Flash")


def _build_arcflash_boundary_page(fig, report: "BusPipelineReport") -> None:
    """Página com plot da boundary arc-flash."""
    fig.text(
        0.5, 0.96, "Arc-Flash Boundary Visualization",
        ha="center", va="top", fontsize=16, fontweight="bold",
        color="#2c3e50",
    )
    fig.text(
        0.5, 0.93,
        "Concentric circles: arc point → working distance → DLA",
        ha="center", va="top", fontsize=10, color="#7f8c8d",
    )

    ax = fig.add_axes([0.15, 0.15, 0.70, 0.70])
    _render_arc_flash_boundary_axes(ax, report)
    _add_footer(fig, "Arc-Flash Boundary")


def _render_arc_flash_boundary_axes(ax, report: "BusPipelineReport") -> None:
    """Desenha boundary no axis fornecido."""
    from matplotlib.patches import Circle

    wd_mm = 914.4 if "kv" in report.panel_type.lower() else 457.2
    DLA = report.arc_flash_boundary_mm
    cat_color = _CAT_COLORS.get(report.ppe_category, "#7f8c8d")
    max_r = max(DLA, wd_mm) * 1.25

    # Arc point
    ax.add_patch(Circle((0, 0), 50, color="#c0392b",
                        alpha=0.9, zorder=10))
    # Working distance
    ax.add_patch(Circle(
        (0, 0), wd_mm, fill=False,
        edgecolor="#3498db", linewidth=2.5, linestyle="--",
        zorder=5,
    ))
    # DLA
    ax.add_patch(Circle(
        (0, 0), DLA, fill=False,
        edgecolor=cat_color, linewidth=2.0, zorder=4,
    ))

    ax.annotate(
        "Arc point", xy=(0, 0), xytext=(150, 100),
        fontsize=9, color="#c0392b", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#c0392b"),
    )
    ax.annotate(
        f"Working dist = {wd_mm:.0f} mm",
        xy=(wd_mm, 0), xytext=(wd_mm + 100, 200),
        fontsize=9, color="#3498db", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#3498db"),
    )
    ax.annotate(
        f"DLA (1.2 cal/cm²) = {DLA:.0f} mm",
        xy=(DLA * 0.7, DLA * 0.7),
        xytext=(DLA * 0.7, DLA * 1.05),
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
        f"Cat {report.ppe_category} — "
        f"E = {report.incident_energy_cal_cm2:.2f} cal/cm²",
        fontsize=11, fontweight="bold",
    )


def _build_tc_curves_page(fig, report: "BusPipelineReport") -> None:
    """Página com TC curves overlap."""
    fig.text(
        0.5, 0.96, "Time-Current Curves (TCC)",
        ha="center", va="top", fontsize=16, fontweight="bold",
        color="#2c3e50",
    )
    fig.text(
        0.5, 0.93,
        "Relay 51 curves overlap (IEEE 242 §15)",
        ha="center", va="top", fontsize=10, color="#7f8c8d",
    )

    if not report.relay_suggestions:
        fig.text(
            0.5, 0.5,
            "No relay suggestions available.",
            ha="center", va="center", fontsize=11, color="#7f8c8d",
            style="italic",
        )
        _add_footer(fig, "TC Curves")
        return

    ax = fig.add_axes([0.12, 0.15, 0.80, 0.70])
    _render_tc_curves_axes(ax, report)
    _add_footer(fig, "TC Curves")


def _render_tc_curves_axes(ax, report: "BusPipelineReport") -> None:
    """Desenha TC curves no axis fornecido."""
    import math
    import numpy as np

    suggestions = report.relay_suggestions
    Ik_pp_A = report.Ik_pp_kA * 1000.0

    ax.set_xscale("log")
    ax.set_yscale("log")

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
            times.append(t if math.isfinite(t) else None)
        I_plot = [I for I, t in zip(I_range, times) if t is not None]
        t_plot = [t for t in times if t is not None]
        ax.plot(
            I_plot, t_plot,
            label=f"{sg.relay_model_id} ({sg.curve_51_type})",
            color=colors[i % len(colors)], linewidth=2,
        )
        ax.axvline(
            sg.pickup_51_A,
            color=colors[i % len(colors)],
            linestyle=":", alpha=0.6, linewidth=1,
        )

    ax.axvline(
        Ik_pp_A, color="red", linestyle="--", linewidth=2,
        label=f"Ik''  = {Ik_pp_A/1000:.2f} kA",
    )

    ax.set_xlabel("Current (A)", fontsize=11)
    ax.set_ylabel("Operate time (s)", fontsize=11)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_ylim(0.01, 100)


def _build_relay_settings_pages(fig, sg) -> None:
    """Uma página por sugestão de relé com vendor format."""
    fig.text(
        0.5, 0.96,
        f"Relay Settings — {sg.relay_model_id}",
        ha="center", va="top", fontsize=15, fontweight="bold",
        color="#2c3e50",
    )
    fig.text(
        0.5, 0.93,
        f"{sg.application}  •  {sg.relay_manufacturer}",
        ha="center", va="top", fontsize=10, color="#7f8c8d",
    )

    # Quick info
    info = (
        f"I_n = {sg.rated_current_A:.1f} A   "
        f"Ik'' = {sg.Ik_pp_kA:.2f} kA   "
        f"Curve 51: {sg.curve_51_standard} {sg.curve_51_type}   "
        f"TMS = {sg.tms_51:.3f}"
    )
    fig.text(
        0.5, 0.89, info,
        ha="center", va="top", fontsize=9, color="#34495e",
    )

    # Vendor format (texto monoespaçado)
    vendor_text = sg.to_vendor_format()
    # Trunca se muito longo (max ~50 linhas para caber em A4)
    lines = vendor_text.split("\n")
    if len(lines) > 50:
        lines = lines[:48] + ["...", "[truncated — see HTML report for full]"]
    truncated = "\n".join(lines)

    fig.text(
        0.05, 0.85, truncated,
        ha="left", va="top",
        fontsize=8.5, family="monospace",
        color="#202020",
        bbox=dict(boxstyle="round,pad=0.5",
                  facecolor="#f8f9fa", edgecolor="#bdc3c7"),
    )

    _add_footer(fig, f"Relay Settings — {sg.relay_model_id}")


def _build_limitations_page(
    fig, report: "BusPipelineReport",
) -> None:
    """
    v0.92: página dedicada às **limitações técnicas declaradas**.

    Cumpre Princípio 4 da auditabilidade: heurísticas e
    simplificações declaradas explicitamente. Defendível em
    auditoria e tribunal.
    """
    fig.text(
        0.5, 0.96, "Limitações Técnicas Declaradas",
        ha="center", va="top", fontsize=16, fontweight="bold",
        color="#7D6608",
    )
    fig.text(
        0.5, 0.93,
        "Heurísticas e simplificações aplicadas nesta versão "
        "do software (v0.92).",
        ha="center", va="top", fontsize=10, color="#5C4D3C",
        style="italic",
    )

    # Caixa amarela ao redor das limitações
    fig.patches.append(__mpl_rect(
        (0.06, 0.10), 0.88, 0.78,
        facecolor="#FEF9E7", edgecolor="#D4AF37",
        linewidth=1.5,
    ))

    fig.text(
        0.10, 0.85,
        "⚠  Limitações aplicadas nesta análise:",
        fontsize=12, fontweight="bold", color="#7D6608",
    )

    y = 0.81
    for key in _BUS_PIPELINE_LIMITATIONS:
        text = KNOWN_LIMITATIONS.get(key)
        if not text:
            continue
        # Quebra texto em ~80 chars
        words = text.split()
        line, lines = "", []
        for w in words:
            if len(line) + len(w) + 1 > 78:
                lines.append(line)
                line = w
            else:
                line = (line + " " + w) if line else w
        if line:
            lines.append(line)
        # Bullet
        fig.text(0.10, y, f"•  [{key}]",
                 fontsize=9, fontweight="bold", color="#7D6608")
        y -= 0.022
        for ln in lines:
            fig.text(0.13, y, ln, fontsize=9, color="#5C4D3C")
            y -= 0.020
        y -= 0.012
        if y < 0.15:
            break

    # Aviso final
    fig.text(
        0.5, 0.07,
        "O usuário deve revisar manualmente as áreas tocadas "
        "por estas limitações antes de aprovar o estudo.",
        ha="center", va="bottom", fontsize=9, color="#5C4D3C",
        fontweight="bold", style="italic",
    )

    _add_footer(fig, "Limitations")


def _build_warnings_footer_page(fig, report: "BusPipelineReport") -> None:
    """Página final com warnings + refs normativas."""
    fig.text(
        0.5, 0.96, "Diagnostics & References",
        ha="center", va="top", fontsize=16, fontweight="bold",
        color="#2c3e50",
    )

    # Warnings
    if report.warnings:
        fig.text(
            0.05, 0.88, "Warnings",
            fontsize=13, fontweight="bold", color="#e67e22",
        )
        y = 0.84
        for w in report.warnings:
            fig.text(
                0.07, y, f"• {w[:120]}",
                fontsize=9, color="#202020",
                wrap=True,
            )
            y -= 0.025
            if y < 0.45:
                break
    else:
        fig.text(
            0.05, 0.88, "No warnings",
            fontsize=13, fontweight="bold", color="#27ae60",
        )

    # References
    fig.text(
        0.05, 0.40, "References",
        fontsize=13, fontweight="bold", color="#2c3e50",
    )

    refs = [
        "IEC 60909-0:2016 — Short-Circuit Currents in Three-Phase a.c. Systems",
        "IEC 60255-151:2009 — Functional Requirements for Over/Under Current Protection",
        "IEC 62271-100:2021 — High-Voltage AC Circuit-Breakers",
        "ABNT NBR 17227:2025 — Arco Elétrico (Brazilian arc-flash standard)",
        "IEEE Std 1584-2018 — Guide for Performing Arc-Flash Hazard Calculations",
        "IEEE Std 242-2001 (Buff Book) — Protection and Coordination",
        "IEEE Std C37.112-2018 — Inverse-Time Characteristic Equations",
        "NFPA 70E:2024 — Electrical Safety in the Workplace",
        "ANSI/IEEE C37.2 — Standard Device Function Numbers",
    ]
    y = 0.36
    for ref in refs:
        fig.text(
            0.07, y, f"• {ref}",
            fontsize=9, color="#34495e",
        )
        y -= 0.025

    # Footer (v0.92: usa VERSION dinâmico)
    try:
        from app.core.version import VERSION
    except ImportError:
        VERSION = "?"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fig.text(
        0.5, 0.04,
        f"Olivas Power System Studio v{VERSION} — Generated {timestamp}",
        ha="center", va="bottom", fontsize=8, color="#95a5a6",
        style="italic",
    )


def _add_footer(fig, section: str) -> None:
    """Footer com identificação do relatório."""
    fig.text(
        0.5, 0.02,
        f"Olivas Power System Studio — {section}",
        ha="center", va="bottom", fontsize=7, color="#95a5a6",
        style="italic",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_pdf_report(
    report: "BusPipelineReport",
    path: str,
    *,
    responsible_engineer: str = "",
    crea_number: str = "",
    art_number: str = "",
    notes: str = "",
) -> None:
    """
    Gera e salva o relatório PDF multi-página.

    Estrutura (v0.92):

    * **Página 1: Audit cover** (NEW v0.92) — software, checksum,
      normas, responsável técnico (ISO 9001 / NR-10).
    * Página 2: KPIs e capa visual.
    * Página 3: Topology + chains.
    * Página 4: SC + Arc-flash tables (com citações).
    * Página 5: Arc-flash boundary plot.
    * Página 6: TC curves overlap.
    * Páginas 7+: Vendor format por relé sugerido.
    * **Página N-1: Limitações declaradas** (NEW v0.92).
    * Página N: warnings + refs normativas.

    Parameters
    ----------
    report:
        ``BusPipelineReport`` com análise completa.
    path:
        Caminho de saída (.pdf).
    responsible_engineer, crea_number, art_number, notes
        v0.92: identificação do responsável técnico (preenchido
        no PDF). Vazio = mostra placeholder ``______`` para o
        engenheiro preencher manualmente após revisão.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    with PdfPages(path) as pdf:
        # 1. NEW v0.92: Audit cover — primeira página
        fig = plt.figure(figsize=(_A4_WIDTH_IN, _A4_HEIGHT_IN))
        _build_audit_cover_page(
            fig, report,
            responsible_engineer=responsible_engineer,
            crea_number=crea_number,
            art_number=art_number,
            notes=notes,
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # 2. Capa visual (existente — KPIs + topology)
        fig = plt.figure(figsize=(_A4_WIDTH_IN, _A4_HEIGHT_IN))
        _build_cover_page(fig, report)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # 3. Topology
        fig = plt.figure(figsize=(_A4_WIDTH_IN, _A4_HEIGHT_IN))
        _build_topology_page(fig, report)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # 4. SC + Arc-flash
        fig = plt.figure(figsize=(_A4_WIDTH_IN, _A4_HEIGHT_IN))
        _build_sc_arcflash_page(fig, report)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # 5. Arc-flash boundary
        fig = plt.figure(figsize=(_A4_WIDTH_IN, _A4_HEIGHT_IN))
        _build_arcflash_boundary_page(fig, report)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # 6. TC curves
        fig = plt.figure(figsize=(_A4_WIDTH_IN, _A4_HEIGHT_IN))
        _build_tc_curves_page(fig, report)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # 7+. Relay settings (uma página por sugestão)
        for sg in report.relay_suggestions:
            fig = plt.figure(figsize=(_A4_WIDTH_IN, _A4_HEIGHT_IN))
            _build_relay_settings_pages(fig, sg)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

        # Penúltima. NEW v0.92: Limitações declaradas
        fig = plt.figure(figsize=(_A4_WIDTH_IN, _A4_HEIGHT_IN))
        _build_limitations_page(fig, report)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Final. Warnings + refs
        fig = plt.figure(figsize=(_A4_WIDTH_IN, _A4_HEIGHT_IN))
        _build_warnings_footer_page(fig, report)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Metadata
        d = pdf.infodict()
        d["Title"] = f"Bus Pipeline Report — {report.bus_id}"
        d["Author"] = (
            f"Olivas Power System Studio — {responsible_engineer}"
            if responsible_engineer else "Olivas Power System Studio"
        )
        d["Subject"] = (
            "Short-circuit + Arc-flash + Relay coordination "
            "analysis (IEC 60909-0 / NBR 17227 / IEEE 242 / NFPA 70E)"
        )
        d["Keywords"] = (
            "short-circuit, arc-flash, NBR 17227, IEEE 1584, "
            "IEEE 242, relay coordination, IEC 60909, ISO 9001, "
            "NR-10, audit-trail"
        )
        d["CreationDate"] = datetime.now()
