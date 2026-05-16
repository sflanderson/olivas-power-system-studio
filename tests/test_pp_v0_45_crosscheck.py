"""
tests/test_pp_v0_45_crosscheck.py — v0.45 cross-check vs
casos publicados ETAP/SKM/IEEE/CIGRÉ.
"""

from __future__ import annotations

import pytest

from app.validation.etap_skm_crosscheck import (
    CrossCheckCase, CrossCheckReport, CrossCheckResult,
    run_all_crosschecks,
)


class TestCrossCheckSuite:

    def test_returns_report(self):
        np = pytest.importorskip("numpy")
        report = run_all_crosschecks()
        assert isinstance(report, CrossCheckReport)
        assert report.n_total >= 5

    def test_all_pass(self):
        np = pytest.importorskip("numpy")
        report = run_all_crosschecks()
        assert report.all_passed, (
            f"Cross-check FAILED:\n{report.summary()}"
        )

    def test_summary_includes_tools(self):
        np = pytest.importorskip("numpy")
        report = run_all_crosschecks()
        text = report.summary()
        assert "ETAP" in text or "SKM" in text
        assert "IEEE" in text


class TestIndividualCases:

    def test_red_book(self):
        from app.validation.etap_skm_crosscheck import (
            _crosscheck_ieee_red_book,
        )
        result = _crosscheck_ieee_red_book()
        assert result.passed

    def test_brown_book_pf(self):
        np = pytest.importorskip("numpy")
        from app.validation.etap_skm_crosscheck import (
            _crosscheck_brown_book_pf,
        )
        result = _crosscheck_brown_book_pf()
        assert result.passed

    def test_brown_book_motor(self):
        from app.validation.etap_skm_crosscheck import (
            _crosscheck_brown_book_motor,
        )
        result = _crosscheck_brown_book_motor()
        assert result.passed

    def test_epri_distribution(self):
        from app.validation.etap_skm_crosscheck import (
            _crosscheck_epri_distribution,
        )
        result = _crosscheck_epri_distribution()
        assert result.passed

    def test_cigre_b5(self):
        from app.validation.etap_skm_crosscheck import (
            _crosscheck_cigre_b5,
        )
        result = _crosscheck_cigre_b5()
        assert result.passed


class TestCrossCheckCase:

    def test_dataclass(self):
        case = CrossCheckCase(
            name="Test", tool="ETAP", citation="ref",
            inputs={}, expected={"v": 1.0},
            tolerance_pct=10.0,
        )
        assert case.name == "Test"
        assert case.tool == "ETAP"
