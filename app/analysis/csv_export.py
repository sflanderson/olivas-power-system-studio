"""CSV export for ATP simulation results and transient metrics.

Exports raw waveform data and computed metrics to CSV files.
"""
from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from app.analysis.transient_metrics import (
    TransientMetrics,
    compute_transient_metrics,
)
from app.simulation.results_reader import AtpResults


def export_waveforms_csv(results: AtpResults, output_path: str) -> str:
    """Export raw waveform data (time + all variables) to CSV.

    Returns the path of the written file.
    """
    path = Path(output_path)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["time_s"] + results.variables
        writer.writerow(header)
        for i, t in enumerate(results.time):
            row = [t]
            for var in results.variables:
                data = results.data.get(var, [])
                row.append(data[i] if i < len(data) else "")
            writer.writerow(row)
    return str(path)


def export_metrics_csv(results: AtpResults, output_path: str) -> str:
    """Export transient metrics summary for all variables to CSV.

    Returns the path of the written file.
    """
    path = Path(output_path)

    metrics_list: list[TransientMetrics] = []
    for var_name in results.variables:
        var_data = results.data.get(var_name, [])
        if var_data and results.time:
            m = compute_transient_metrics(results.time, var_data, var_name)
            metrics_list.append(m)

    if not metrics_list:
        path.write_text("Nenhuma variavel com dados.\n", encoding="utf-8")
        return str(path)

    fields = [
        "variable_name", "peak_value", "peak_time", "min_value", "min_time",
        "rms_value", "mean_value", "frequency_hz", "damping_ratio", "n_samples",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for m in metrics_list:
            writer.writerow(asdict(m))

    return str(path)
