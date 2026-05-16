"""
tests/test_pp_v0_37_benchmarks.py — v0.37 validation
benchmark suite contra benchmarks publicados.
"""

from __future__ import annotations

import pytest

from app.validation.benchmarks import (
    BenchmarkCase, BenchmarkResult, StudyType,
    ValidationReport, list_benchmark_names,
    run_all_benchmarks,
)


class TestBenchmarkSuite:

    def test_list_has_five_benchmarks(self):
        names = list_benchmark_names()
        assert len(names) >= 5

    def test_run_all_returns_report(self):
        np = pytest.importorskip("numpy")  # PF needs numpy
        report = run_all_benchmarks()
        assert isinstance(report, ValidationReport)
        assert len(report.results) >= 5

    def test_all_pass(self):
        """Suite inteira deve passar — regression guard."""
        np = pytest.importorskip("numpy")
        report = run_all_benchmarks()
        assert report.all_passed, (
            f"Validation suite FAILED:\n{report.summary()}"
        )

    def test_iec60909_annex_c(self):
        from app.validation.benchmarks import _bench_iec60909_annex_c
        result = _bench_iec60909_annex_c()
        assert result.passed
        assert result.case.study_type == StudyType.SHORT_CIRCUIT

    def test_ieee1584_d4(self):
        from app.validation.benchmarks import _bench_ieee1584_d4
        result = _bench_ieee1584_d4()
        assert result.passed
        assert result.case.study_type == StudyType.ARC_FLASH

    def test_stevenson_seq(self):
        from app.validation.benchmarks import _bench_stevenson_seq_full
        result = _bench_stevenson_seq_full()
        assert result.passed
        assert result.max_error_pct < 1.0

    def test_industrial_br(self):
        np = pytest.importorskip("numpy")
        from app.validation.benchmarks import (
            _bench_industrial_petroquimica,
        )
        result = _bench_industrial_petroquimica()
        assert result.passed


class TestBenchmarkCase:

    def test_dataclass_fields(self):
        case = BenchmarkCase(
            name="Test", reference="Ref", description="d",
            inputs={}, expected={"v": 1.0},
            tolerance_pct=5.0,
            study_type=StudyType.SHORT_CIRCUIT,
        )
        assert case.name == "Test"
        assert case.tolerance_pct == 5.0


class TestValidationReport:

    def test_summary_has_status(self):
        np = pytest.importorskip("numpy")
        report = run_all_benchmarks()
        text = report.summary()
        assert "VALIDATION SUITE" in text
        assert "Passed:" in text
