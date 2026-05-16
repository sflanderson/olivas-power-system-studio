"""
Builtin plugin: CSV Exporter
=============================

Exporta dict de resultados para arquivo CSV padrão Excel-compatible.
"""

import csv
from pathlib import Path

from app.plugins import register_study


@register_study("export_results_csv")
def export_csv(
    project=None,
    *,
    results: dict,
    output_path: str,
):
    """
    Escreve dict {column_name: value} como uma linha CSV.

    Se ``output_path`` já existe, append linha (sem reescrever
    header). Se não existe, cria com header.
    """
    p = Path(output_path)
    file_exists = p.exists()
    with p.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        if not file_exists:
            writer.writerow(list(results.keys()))
        writer.writerow(list(results.values()))
    return {
        "ok": True,
        "rows_written": 1,
        "header_written": not file_exists,
        "path": str(p.resolve()),
    }
