"""
tests/test_pp_v0_104_0_laudo_generator.py — v0.104.0:

AI-driven laudo generator (offline template + Claude-ready API).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.llm.laudo_generator import (
    CoordinationFixSuggestion,
    LaudoNarrative,
    ReportDiff,
    compare_reports,
    generate_audit_narrative,
    suggest_relay_fix,
)


# Mock report (avoids dependency on bus_pipeline)
@dataclass(frozen=True)
class _MockReport:
    bus_id: str = "BUS-MAIN-13.8"
    rated_voltage_kV: float = 13.8
    Ik_pp_kA: float = 12.5
    ip_kA: float = 31.7
    kappa: float = 1.78
    incident_energy_cal_cm2: float = 8.4
    arc_flash_boundary_mm: float = 1240.0
    ppe_category: str = "2"


# ---------------------------------------------------------------------------
# Offline narrative generator
# ---------------------------------------------------------------------------


class TestOfflineNarrative:

    def test_basic_lv_report(self):
        report = _MockReport()
        n = generate_audit_narrative(
            report, use_offline_template=True,
        )
        assert isinstance(n, LaudoNarrative)
        assert "BUS-MAIN-13.8" in n.title
        assert "13.80 kV" in n.introduction
        assert "12.50 kA" in n.technical_analysis
        assert n.word_count > 50

    def test_full_text_has_4_sections(self):
        report = _MockReport()
        n = generate_audit_narrative(
            report, use_offline_template=True,
        )
        full = n.full_text()
        assert "Introdução" in full
        assert "Análise técnica" in full
        assert "Conclusões" in full
        assert "Recomendações" in full

    def test_NA_ppe_handled(self):
        """Bus HV → ppe_category='N/A' → narrative explica."""
        report = _MockReport(
            ppe_category="N/A",
            rated_voltage_kV=110.0,
            incident_energy_cal_cm2=0,
        )
        n = generate_audit_narrative(
            report, use_offline_template=True,
        )
        assert "EPRI" in n.technical_analysis
        assert "Terzija" in n.technical_analysis

    def test_citations_present(self):
        report = _MockReport()
        n = generate_audit_narrative(
            report, use_offline_template=True,
        )
        full = n.full_text()
        assert "IEC 60909" in full
        assert "NBR 17227" in full or "IEEE 1584" in full
        assert "IEEE 242" in full or "NFPA 70E" in full

    def test_recommendations_have_actionable_items(self):
        report = _MockReport()
        n = generate_audit_narrative(
            report, use_offline_template=True,
        )
        rec = n.recommendations
        # Recomendações numeradas
        assert "1." in rec
        # Inclui ação NR-10
        assert "NR-10" in rec or "Reavaliar" in rec


# ---------------------------------------------------------------------------
# Coordination fix suggestions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _MockCoordCheck:
    upstream_id: str
    downstream_id: str
    fault_current_A: float
    upstream_time_s: float
    downstream_time_s: float
    actual_delta_t_s: float
    required_delta_t_s: float
    passes: bool


class TestCoordinationFix:

    def test_inversion_suggests_pickup_change(self):
        check = _MockCoordCheck(
            upstream_id="R_UP",
            downstream_id="R_DOWN",
            fault_current_A=2000,
            upstream_time_s=0.5,
            downstream_time_s=0.7,
            actual_delta_t_s=-0.2,   # negativo = inversão
            required_delta_t_s=0.25,
            passes=False,
        )
        fix = suggest_relay_fix(check)
        assert isinstance(fix, CoordinationFixSuggestion)
        assert "Inversão" in fix.issue
        assert "pickup" in fix.proposed_action

    def test_insufficient_margin_suggests_TMS_increase(self):
        check = _MockCoordCheck(
            upstream_id="R_UP",
            downstream_id="R_DOWN",
            fault_current_A=2000,
            upstream_time_s=0.6,
            downstream_time_s=0.5,
            actual_delta_t_s=0.1,   # ≥ 0 mas < required
            required_delta_t_s=0.25,
            passes=False,
        )
        fix = suggest_relay_fix(check)
        assert "TMS" in fix.proposed_action
        assert "insuficiente" in fix.issue

    def test_passing_coordination_no_action(self):
        check = _MockCoordCheck(
            upstream_id="R_UP",
            downstream_id="R_DOWN",
            fault_current_A=2000,
            upstream_time_s=0.8,
            downstream_time_s=0.4,
            actual_delta_t_s=0.4,
            required_delta_t_s=0.25,
            passes=True,
        )
        fix = suggest_relay_fix(check)
        assert "adequada" in fix.issue
        assert "Nenhuma" in fix.proposed_action


# ---------------------------------------------------------------------------
# Report comparison
# ---------------------------------------------------------------------------


class TestReportDiff:

    def test_minor_change(self):
        v1 = _MockReport(Ik_pp_kA=12.0, incident_energy_cal_cm2=8.0)
        v2 = _MockReport(Ik_pp_kA=12.1, incident_energy_cal_cm2=8.1)
        diff = compare_reports(v1, v2)
        assert isinstance(diff, ReportDiff)
        assert diff.severity == "minor"

    def test_major_change_in_Ik(self):
        v1 = _MockReport(Ik_pp_kA=10.0)
        v2 = _MockReport(Ik_pp_kA=15.0)   # +50%
        diff = compare_reports(v1, v2)
        assert diff.severity == "major"
        assert "investigue" in diff.sc_changes.lower()

    def test_summary_shows_deltas(self):
        v1 = _MockReport(Ik_pp_kA=10.0)
        v2 = _MockReport(Ik_pp_kA=12.0)
        diff = compare_reports(v1, v2)
        assert "10.00" in diff.summary
        assert "12.00" in diff.summary
        assert "+20" in diff.summary or "20.0%" in diff.summary

    def test_arc_flash_change_warns_label_update(self):
        v1 = _MockReport(incident_energy_cal_cm2=5.0)
        v2 = _MockReport(incident_energy_cal_cm2=10.0)   # 2x
        diff = compare_reports(v1, v2)
        assert "ETIQUETA" in diff.arc_flash_changes.upper()
