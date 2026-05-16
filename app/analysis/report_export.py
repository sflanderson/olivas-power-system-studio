"""HTML report export for Olivas ATP Studio.

Generates a self-contained HTML report with:
- Logo and header
- Project summary
- Validation results
- Transient metrics table
- Component counts
"""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.analysis.transient_metrics import TransientMetrics, compute_transient_metrics
from app.core.project_model import AtpProject
from app.simulation.results_reader import AtpResults, find_result_files, read_pl4
from app.validation.validator_models import ValidationMessage, validate_project
from app.validation.validator_physics import validate_physics
from app.validation.validator_vcb import validate_vcb

_LOGO_PATH = Path(__file__).parent.parent / "resources" / "logo.png"


def _logo_base64() -> str:
    """Encode logo as base64 for embedding in HTML (resized for report)."""
    if not _LOGO_PATH.is_file():
        return ""
    try:
        import io
        from PIL import Image
        img = Image.open(_LOGO_PATH)
        # Resize to max 200px height for report
        max_h = 200
        if img.height > max_h:
            ratio = max_h / img.height
            img = img.resize((int(img.width * ratio), max_h), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except ImportError:
        # Pillow not available — use raw file
        data = _LOGO_PATH.read_bytes()
        return base64.b64encode(data).decode("ascii")


def _fmt(v: Any, decimals: int = 4) -> str:
    if v is None:
        return "&mdash;"
    if isinstance(v, float):
        return f"{v:.{decimals}g}"
    return str(v)


def generate_html_report(
    project: AtpProject,
    pl4: Optional[AtpResults] = None,
    messages: Optional[list[ValidationMessage]] = None,
) -> str:
    """Generate a self-contained HTML report for an ATP project.

    Args:
        project: The ATP project to report on.
        pl4: Optional PL4 results (if None, tries to find them).
        messages: Optional validation messages (if None, runs validation).

    Returns:
        Complete HTML string.
    """
    # Auto-load PL4 if not provided
    if pl4 is None:
        found = find_result_files(project.file_path)
        if "pl4" in found:
            try:
                pl4 = read_pl4(found["pl4"])
            except Exception:
                pl4 = None

    # Auto-validate if not provided
    if messages is None:
        messages = validate_project(project)
        messages.extend(validate_physics(project))
        messages.extend(validate_vcb(project))

    # Compute metrics
    metrics: list[TransientMetrics] = []
    if pl4 and pl4.time:
        for var_name in pl4.variables[:50]:
            var_data = pl4.data.get(var_name, [])
            if var_data:
                metrics.append(compute_transient_metrics(pl4.time, var_data, var_name))

    logo_b64 = _logo_base64()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    filename = Path(project.file_path).name

    return _render_html(project, filename, now, logo_b64, messages, metrics, pl4)


def _render_html(
    project: AtpProject,
    filename: str,
    timestamp: str,
    logo_b64: str,
    messages: list[ValidationMessage],
    metrics: list[TransientMetrics],
    pl4: Optional[AtpResults],
) -> str:
    """Render the full HTML document."""
    logo_img = (
        f'<img src="data:image/png;base64,{logo_b64}" alt="Olivas Power System Studio" '
        f'style="height:80px;">'
        if logo_b64 else ""
    )

    # --- Summary section ---
    h = project.header
    summary_rows = f"""
    <tr><td>Arquivo</td><td><strong>{filename}</strong></td></tr>
    <tr><td>delta_t</td><td>{_fmt(h.delta_t)} s</td></tr>
    <tr><td>t_max</td><td>{_fmt(h.t_max)} s</td></tr>
    <tr><td>Frequência</td><td>{_fmt(h.frequency)} Hz</td></tr>
    <tr><td>MODELs</td><td>{len(project.models)}</td></tr>
    <tr><td>USEs</td><td>{len(project.uses)}</td></tr>
    <tr><td>Branches</td><td>{len(project.branches)}</td></tr>
    <tr><td>Switches</td><td>{len(project.switches)}</td></tr>
    <tr><td>Sources</td><td>{len(project.sources)}</td></tr>
    <tr><td>Nodes</td><td>{len(project.nodes)}</td></tr>
    """

    # --- Validation section ---
    n_err = sum(1 for m in messages if m.severity.value == "ERRO")
    n_warn = sum(1 for m in messages if m.severity.value == "AVISO")
    n_info = sum(1 for m in messages if m.severity.value == "INFO")

    val_summary = f"{n_err} erros, {n_warn} avisos, {n_info} info"

    val_rows = ""
    for m in messages:
        sev = m.severity.value
        css = {"ERRO": "sev-error", "AVISO": "sev-warning", "INFO": "sev-info"}.get(sev, "")
        val_rows += f'<tr class="{css}"><td>{sev}</td><td>{m.code}</td><td>{m.message}</td></tr>\n'

    # --- Metrics section ---
    metrics_rows = ""
    for mt in metrics:
        metrics_rows += (
            f"<tr>"
            f"<td>{mt.variable_name}</td>"
            f"<td>{_fmt(mt.peak_value)}</td>"
            f"<td>{_fmt(mt.peak_time, 6)}</td>"
            f"<td>{_fmt(mt.min_value)}</td>"
            f"<td>{_fmt(mt.rms_value)}</td>"
            f"<td>{_fmt(mt.frequency_hz, 1)}</td>"
            f"<td>{_fmt(mt.damping_ratio)}</td>"
            f"<td>{mt.n_samples}</td>"
            f"</tr>\n"
        )

    # --- PL4 info ---
    pl4_info = ""
    if pl4:
        pl4_info = f"""
        <h2>Resultados de Simulação</h2>
        <table class="summary">
            <tr><td>Variáveis</td><td>{len(pl4.variables)}</td></tr>
            <tr><td>Passos</td><td>{pl4.n_steps}</td></tr>
            <tr><td>delta_t</td><td>{_fmt(pl4.delta_t)} s</td></tr>
        </table>
        """

    # --- Component breakdown ---
    branch_types: dict[str, int] = {}
    for b in project.branches:
        t = b.semantic_type or "other"
        branch_types[t] = branch_types.get(t, 0) + 1
    switch_types: dict[str, int] = {}
    for s in project.switches:
        t = s.semantic_type or "other"
        switch_types[t] = switch_types.get(t, 0) + 1

    comp_rows = ""
    for t, c in sorted(branch_types.items()):
        comp_rows += f'<tr><td>BRANCH</td><td>{t}</td><td>{c}</td></tr>\n'
    for t, c in sorted(switch_types.items()):
        comp_rows += f'<tr><td>SWITCH</td><td>{t}</td><td>{c}</td></tr>\n'
    for src in project.sources:
        t = src.semantic_type or "other"
        comp_rows += f'<tr><td>SOURCE</td><td>{t}</td><td>{src.node}</td></tr>\n'

    # --- USE DATA ---
    use_rows = ""
    for use in project.uses:
        for d in use.data:
            val = d.assigned_value or d.default_value or ""
            use_rows += (
                f"<tr><td>{use.model_name}</td>"
                f"<td>{d.name}</td>"
                f"<td>{val}</td>"
                f"<td>{d.default_value or ''}</td></tr>\n"
            )

    # --- Compose conditional sections (Python 3.11 compat:
    # avoid nested f-strings with same-type quotes, PEP 701 only in 3.12+) ---
    if val_rows:
        val_section = (
            '<table><thead><tr><th>Nível</th><th>Código</th>'
            '<th>Mensagem</th></tr></thead><tbody>'
            f'{val_rows}</tbody></table>'
        )
    else:
        val_section = '<p>Nenhuma mensagem de validação.</p>'

    if use_rows:
        use_section = (
            '<table><thead><tr><th>USE</th><th>Parâmetro</th>'
            '<th>Valor</th><th>Default</th></tr></thead><tbody>'
            f'{use_rows}</tbody></table>'
        )
    else:
        use_section = '<p>Nenhum USE com DATA.</p>'

    if metrics_rows:
        metrics_section = (
            '<h2>Métricas de Transitório</h2>\n'
            '<table>\n'
            '<thead><tr><th>Variável</th><th>Pico</th>'
            '<th>t_pico (s)</th><th>Mínimo</th><th>RMS</th>'
            '<th>Freq (Hz)</th><th>Amort.</th><th>Amostras</th>'
            '</tr></thead>\n'
            f'<tbody>{metrics_rows}</tbody>\n'
            '</table>'
        )
    else:
        metrics_section = ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório — {filename}</title>
<style>
  body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0; padding: 20px 40px;
    background: #fafafa; color: #212121;
    max-width: 1100px; margin: auto;
  }}
  .header {{
    display: flex; align-items: center; gap: 20px;
    border-bottom: 2px solid #2e7d32; padding-bottom: 12px;
    margin-bottom: 24px;
  }}
  .header h1 {{ color: #1b5e20; margin: 0; font-size: 1.6em; }}
  .header .meta {{ color: #666; font-size: 0.9em; }}
  h2 {{
    color: #2e7d32; border-bottom: 1px solid #c8e6c9;
    padding-bottom: 4px; margin-top: 28px;
  }}
  table {{
    border-collapse: collapse; width: 100%;
    margin-bottom: 16px; font-size: 0.9em;
  }}
  th, td {{
    border: 1px solid #ddd; padding: 6px 10px; text-align: left;
  }}
  th {{ background: #e8f5e9; color: #1b5e20; }}
  table.summary {{ width: auto; }}
  table.summary td:first-child {{ font-weight: bold; min-width: 120px; }}
  .sev-error td {{ background: #ffebee; }}
  .sev-warning td {{ background: #fff8e1; }}
  .sev-info td {{ background: #e3f2fd; }}
  .val-summary {{
    font-size: 1.1em; margin-bottom: 8px;
    padding: 8px 12px; background: #f5f5f5; border-radius: 4px;
  }}
  .footer {{
    margin-top: 32px; padding-top: 12px;
    border-top: 1px solid #ddd; color: #999; font-size: 0.8em;
  }}
  @media print {{
    body {{ padding: 10px; }}
    .header {{ page-break-after: avoid; }}
    table {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>

<div class="header">
  {logo_img}
  <div>
    <h1>Olivas Power System Studio &mdash; Relatório</h1>
    <div class="meta">{filename} &bull; Gerado em {timestamp}</div>
  </div>
</div>

<h2>Resumo do Projeto</h2>
<table class="summary">{summary_rows}</table>

<h2>Validação</h2>
<div class="val-summary">{val_summary}</div>
{val_section}

<h2>Componentes por Tipo</h2>
<table>
<thead><tr><th>Seção</th><th>Tipo</th><th>Contagem / Nó</th></tr></thead>
<tbody>{comp_rows}</tbody>
</table>

<h2>Parâmetros USE DATA</h2>
{use_section}

{pl4_info}

{metrics_section}

<div class="footer">
  Olivas Power System Studio &bull; Relatório gerado automaticamente
</div>

</body>
</html>"""


def export_html_report(project: AtpProject, output_path: str) -> str:
    """Generate and save HTML report. Returns the output path."""
    html = generate_html_report(project)
    Path(output_path).write_text(html, encoding="utf-8")
    return output_path


def export_pdf_report(project: AtpProject, output_path: str) -> str:
    """Generate and save PDF report via Qt's QPrinter. Returns the output path."""
    from PySide6.QtCore import QMarginsF, QSizeF
    from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument
    from PySide6.QtPrintSupport import QPrinter
    from PySide6.QtWidgets import QApplication

    # Ensure QApplication exists (needed for QTextDocument rendering)
    app = QApplication.instance()
    if app is None:
        raise RuntimeError("QApplication must be running for PDF export.")

    html = generate_html_report(project)

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(output_path)
    printer.setPageLayout(
        QPageLayout(
            QPageSize(QPageSize.A4),
            QPageLayout.Portrait,
            QMarginsF(15, 15, 15, 15),  # mm
        )
    )

    doc = QTextDocument()
    doc.setHtml(html)
    doc.setPageSize(QSizeF(printer.pageRect(QPrinter.Point).size()))
    doc.print_(printer)

    return output_path
