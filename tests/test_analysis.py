"""Tests for analysis modules — metrics, CSV export, comparison, report."""
from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path

from app.analysis.case_compare import compare_cases
from app.analysis.csv_export import export_metrics_csv, export_waveforms_csv
from app.analysis.report_export import export_html_report, _logo_base64
from app.analysis.transient_metrics import (
    TransientMetrics,
    compute_transient_metrics,
    compute_trv_metrics,
)
from app.core.parser import parse_file
from app.core.project_model import AtpProject
from app.simulation.results_reader import AtpResults
from tests.conftest import REF_FILE


def _synthetic_results() -> AtpResults:
    """Create synthetic 60Hz AC results for testing."""
    n = 1000
    dt = 1e-5
    t = [i * dt for i in range(n)]
    v = [100 * math.sin(2 * math.pi * 60 * ti) for ti in t]
    c = [50 * math.cos(2 * math.pi * 60 * ti) for ti in t]
    return AtpResults(
        file_path="synthetic.pl4",
        variables=["VOLTAGE", "CURRENT"],
        time=t,
        data={"VOLTAGE": v, "CURRENT": c},
        delta_t=dt,
        n_steps=n,
    )


class TestTransientMetrics:
    def test_peak_detection(self):
        results = _synthetic_results()
        m = compute_transient_metrics(results.time, results.data["VOLTAGE"], "V")
        assert m.peak_value > 99.0
        assert m.min_value < -50.0

    def test_rms(self):
        results = _synthetic_results()
        m = compute_transient_metrics(results.time, results.data["VOLTAGE"], "V")
        assert m.rms_value > 0

    def test_sample_count(self):
        results = _synthetic_results()
        m = compute_transient_metrics(results.time, results.data["VOLTAGE"], "V")
        assert m.n_samples == 1000

    def test_empty_input(self):
        m = compute_transient_metrics([], [], "empty")
        assert m.n_samples == 0

    def test_variable_name(self):
        results = _synthetic_results()
        m = compute_transient_metrics(results.time, results.data["VOLTAGE"], "MYVAR")
        assert m.variable_name == "MYVAR"


class TestTrvMetrics:
    def test_trv_basic(self):
        # Simple ramp voltage after current zero
        t = [i * 1e-6 for i in range(100)]
        v = [i * 1000 for i in range(100)]  # 1 kV/us ramp
        trv = compute_trv_metrics(t, v, current_zero_time=0.0)
        assert trv.peak_trv_kv > 0
        assert trv.rrrv_kv_per_us > 0

    def test_trv_with_iec(self):
        t = [i * 1e-6 for i in range(100)]
        v = [i * 500 for i in range(100)]
        trv = compute_trv_metrics(t, v, current_zero_time=0.0, rated_voltage_kv=24.0)
        assert trv.iec_uc_kv is not None
        assert trv.withstand_ok is not None


class TestCsvExport:
    def test_waveforms_csv(self):
        results = _synthetic_results()
        path = os.path.join(tempfile.gettempdir(), "test_wf.csv")
        try:
            out = export_waveforms_csv(results, path)
            assert Path(out).is_file()
            lines = Path(out).read_text().splitlines()
            assert lines[0] == "time_s,VOLTAGE,CURRENT"
            assert len(lines) == 1001  # header + 1000 rows
        finally:
            Path(path).unlink(missing_ok=True)

    def test_metrics_csv(self):
        results = _synthetic_results()
        path = os.path.join(tempfile.gettempdir(), "test_met.csv")
        try:
            out = export_metrics_csv(results, path)
            assert Path(out).is_file()
            lines = Path(out).read_text().splitlines()
            assert "variable_name" in lines[0]
            assert len(lines) == 3  # header + 2 variables
        finally:
            Path(path).unlink(missing_ok=True)


class TestCaseCompare:
    def test_same_file_no_diffs(self, ref_project: AtpProject):
        result = compare_cases(ref_project, ref_project)
        assert len(result.diffs) == 0

    def test_modified_header_detected(self):
        p1 = parse_file(REF_FILE)
        p2 = parse_file(REF_FILE)
        p2.header.delta_t = 1e-7
        result = compare_cases(p1, p2)
        assert result.has_diffs
        labels = [d.label for d in result.diffs]
        assert any("delta_t" in l for l in labels)

    def test_modified_use_data_detected(self):
        p1 = parse_file(REF_FILE)
        p2 = parse_file(REF_FILE)
        p2.uses[0].data[0].assigned_value = "999"
        result = compare_cases(p1, p2)
        assert result.has_diffs


class TestReportExport:
    def test_logo_base64(self):
        b64 = _logo_base64()
        # May be empty if logo file missing, but should not crash
        assert isinstance(b64, str)

    def test_html_report_generates(self, ref_project: AtpProject):
        path = os.path.join(tempfile.gettempdir(), "test_report.html")
        try:
            out = export_html_report(ref_project, path)
            assert Path(out).is_file()
            content = Path(out).read_text(encoding="utf-8")
            # v0.92.2: rebrand
            assert "Olivas Power System Studio" in content
            assert "Relatório" in content
            assert ref_project.file_path.split("\\")[-1] in content or \
                   ref_project.file_path.split("/")[-1] in content
        finally:
            Path(path).unlink(missing_ok=True)
