"""
tests/test_pp_v0_100_0_pf_unbalanced.py — v0.100.0:

Power Flow desbalanceado (sequências 0/1/2 + IEEE 1159).
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.power_flow_unbalanced import (
    BusUnbalancedVoltage,
    UnbalancedPFResult,
    analyze_unbalanced_pf,
    phase_to_sequence,
    sequence_to_phase,
)


@pytest.fixture
def project_simple():
    from app.preprocessor.templates import build_simple_13_8kV
    return build_simple_13_8kV()


# ---------------------------------------------------------------------------
# Symmetrical components
# ---------------------------------------------------------------------------


class TestSymmetricalComponents:

    def test_balanced_system_has_only_positive_sequence(self):
        """Sistema balanceado: V_a, V_b, V_c iguais (defasagem
        120°) → V0=0, V2=0, V1=Va."""
        Va = complex(1, 0)
        # Vb = a²·Va, Vc = a·Va
        a = complex(math.cos(2*math.pi/3), math.sin(2*math.pi/3))
        Vb = a*a * Va
        Vc = a * Va
        V0, V1, V2 = phase_to_sequence(Va, Vb, Vc)
        assert abs(V0) < 1e-10
        assert abs(V2) < 1e-10
        assert abs(V1 - Va) < 1e-10

    def test_inverse_transformation(self):
        """sequence_to_phase é inverso de phase_to_sequence."""
        Va, Vb, Vc = complex(1, 0), complex(0.95, -0.5), complex(0.9, 0.6)
        V0, V1, V2 = phase_to_sequence(Va, Vb, Vc)
        Va2, Vb2, Vc2 = sequence_to_phase(V0, V1, V2)
        assert abs(Va - Va2) < 1e-10
        assert abs(Vb - Vb2) < 1e-10
        assert abs(Vc - Vc2) < 1e-10

    def test_zero_seq_when_va_vb_vc_equal(self):
        """Va=Vb=Vc → V1=0, V2=0, V0=Va."""
        V = complex(1, 0)
        V0, V1, V2 = phase_to_sequence(V, V, V)
        assert abs(V0 - V) < 1e-10
        assert abs(V1) < 1e-10
        assert abs(V2) < 1e-10


# ---------------------------------------------------------------------------
# BusUnbalancedVoltage dataclass
# ---------------------------------------------------------------------------


class TestBusUnbalancedVoltage:

    def test_unbalance_factor(self):
        """UF = V_neg / V_pos × 100."""
        bus = BusUnbalancedVoltage(
            bus_id="X",
            V_pos_pu=1.0, V_neg_pu=0.02, V_zero_pu=0.0,
        )
        assert abs(bus.unbalance_factor_pct - 2.0) < 1e-6

    def test_unbalance_zero_when_pos_zero(self):
        """V_pos = 0 não causa div por zero."""
        bus = BusUnbalancedVoltage(
            bus_id="X", V_pos_pu=0, V_neg_pu=0.02,
        )
        assert bus.unbalance_factor_pct == 0.0

    def test_phase_magnitudes(self):
        bus = BusUnbalancedVoltage(
            bus_id="X",
            V_a_real=1.0, V_a_imag=0,
            V_b_real=-0.5, V_b_imag=-0.866,
            V_c_real=-0.5, V_c_imag=0.866,
        )
        assert abs(bus.V_a_magnitude - 1.0) < 1e-6
        assert abs(bus.V_b_magnitude - 1.0) < 1e-3
        assert abs(bus.V_c_magnitude - 1.0) < 1e-3


# ---------------------------------------------------------------------------
# analyze_unbalanced_pf
# ---------------------------------------------------------------------------


class TestAnalyzeUnbalancedPF:

    def test_returns_result_per_bus(self, project_simple):
        r = analyze_unbalanced_pf(project_simple)
        assert isinstance(r, UnbalancedPFResult)
        assert len(r.per_bus) >= 1

    def test_low_unbalance_no_violations(self, project_simple):
        """Default 0.5% unbalance, limite 2% → sem violations."""
        r = analyze_unbalanced_pf(
            project_simple,
            typical_unbalance_per_bus_pct=0.5,
            unbalance_limit_pct=2.0,
        )
        assert len(r.violations) == 0

    def test_high_unbalance_finds_violations(self, project_simple):
        """5% unbalance > 2% limite → violations."""
        r = analyze_unbalanced_pf(
            project_simple,
            typical_unbalance_per_bus_pct=5.0,
            unbalance_limit_pct=2.0,
        )
        assert len(r.violations) > 0

    def test_empty_project_warns(self):
        from app.preprocessor.models import PpProject
        proj = PpProject(version="0.0.19")
        r = analyze_unbalanced_pf(proj)
        assert "Nenhum BUS" in " ".join(r.warnings)

    def test_summary_shows_ieee_1159(self, project_simple):
        r = analyze_unbalanced_pf(project_simple)
        # Citation format is "IEEE Std 1159-2019"
        assert "1159" in r.citation
        assert "IEEE" in r.citation

    def test_voltages_are_consistent_via_fortescue(self, project_simple):
        """V_a, V_b, V_c devem ser reconstruíveis via Fortescue."""
        r = analyze_unbalanced_pf(project_simple)
        for bus_id, v in r.per_bus.items():
            Va = complex(v.V_a_real, v.V_a_imag)
            Vb = complex(v.V_b_real, v.V_b_imag)
            Vc = complex(v.V_c_real, v.V_c_imag)
            V0, V1, V2 = phase_to_sequence(Va, Vb, Vc)
            assert abs(abs(V1) - v.V_pos_pu) < 1e-6
            assert abs(abs(V2) - v.V_neg_pu) < 1e-6
