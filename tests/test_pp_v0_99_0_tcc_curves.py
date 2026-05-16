"""
tests/test_pp_v0_99_0_tcc_curves.py — v0.99.0:

TCC curves + coordenação automática.
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_curves import (
    COORDINATION_MARGIN_S,
    CoordinationCheck,
    CurveType,
    TCCCurve,
    check_coordination,
    operating_time_s,
)


# ---------------------------------------------------------------------------
# operating_time_s
# ---------------------------------------------------------------------------


class TestOperatingTime:

    def test_below_pickup_returns_inf(self):
        # M = 1 → t = ∞
        t = operating_time_s(
            CurveType.IEC_STANDARD_INVERSE,
            multiple_of_pickup=1.0,
            tms=0.5,
        )
        assert t == float("inf")

    def test_iec_standard_inverse_at_2x(self):
        """IEC SI: t = TMS · 0.14 / (M^0.02 - 1) — para M=2,
        TMS=1, t ≈ 10s."""
        t = operating_time_s(
            CurveType.IEC_STANDARD_INVERSE,
            multiple_of_pickup=2.0,
            tms=1.0,
        )
        # Valor esperado ≈ 10.03s
        assert 9 < t < 11

    def test_iec_very_inverse_at_5x(self):
        """IEC VI: t = TMS · 13.5 / (M-1) — para M=5, TMS=1, t≈3.4s."""
        t = operating_time_s(
            CurveType.IEC_VERY_INVERSE,
            multiple_of_pickup=5.0,
            tms=1.0,
        )
        assert 3 < t < 4

    def test_extremely_inverse_faster_than_very_inverse(self):
        """EI mais rápido que VI para alta corrente."""
        t_ei = operating_time_s(
            CurveType.IEC_EXTREMELY_INVERSE,
            multiple_of_pickup=10.0,
            tms=0.5,
        )
        t_vi = operating_time_s(
            CurveType.IEC_VERY_INVERSE,
            multiple_of_pickup=10.0,
            tms=0.5,
        )
        assert t_ei < t_vi

    def test_higher_tms_longer_time(self):
        """TMS maior → tempo maior (linear)."""
        t1 = operating_time_s(
            CurveType.IEC_STANDARD_INVERSE, 5.0, tms=0.5,
        )
        t2 = operating_time_s(
            CurveType.IEC_STANDARD_INVERSE, 5.0, tms=1.0,
        )
        assert abs(t2 / t1 - 2.0) < 0.01

    def test_ansi_curves_work(self):
        for ct in (
            CurveType.ANSI_MODERATELY_INVERSE,
            CurveType.ANSI_VERY_INVERSE,
            CurveType.ANSI_EXTREMELY_INVERSE,
        ):
            t = operating_time_s(ct, 5.0, 0.5)
            assert math.isfinite(t)
            assert t > 0


# ---------------------------------------------------------------------------
# TCCCurve
# ---------------------------------------------------------------------------


class TestTCCCurve:

    def test_curve_at_pickup(self):
        curve = TCCCurve(
            relay_id="R1",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=100,
            tms=0.5,
        )
        # Corrente igual ao pickup → t = ∞
        t = curve.operating_time_at_current(100)
        assert t == float("inf")

    def test_curve_above_pickup(self):
        curve = TCCCurve(
            relay_id="R1",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=100, tms=0.5,
        )
        t = curve.operating_time_at_current(500)   # M=5
        assert math.isfinite(t)
        assert t > 0

    def test_instantaneous_overrides_inverse(self):
        """50 atua antes do 51 quando I > pickup_50."""
        curve = TCCCurve(
            relay_id="R1",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=100, tms=0.5,
            instantaneous_pickup_A=2000,
            instantaneous_delay_s=0.04,
        )
        # I = 5000 > 2000 → 50 atua → t = 0.04
        t = curve.operating_time_at_current(5000)
        assert t == 0.04

    def test_points_log_spaced(self):
        curve = TCCCurve(
            relay_id="R1",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=100, tms=0.5,
        )
        points = curve.points(i_min_A=200, i_max_A=10000, n_points=20)
        assert len(points) > 10
        # Ordem crescente
        for i in range(len(points) - 1):
            assert points[i + 1][0] > points[i][0]
        # Todos têm t finito
        for _, t in points:
            assert math.isfinite(t)


# ---------------------------------------------------------------------------
# check_coordination
# ---------------------------------------------------------------------------


class TestCoordinationCheck:

    def test_proper_coordination_passes(self):
        """Upstream com TMS maior → opera depois → passa."""
        upstream = TCCCurve(
            "Up", CurveType.IEC_VERY_INVERSE,
            pickup_A=200, tms=0.5,
        )
        downstream = TCCCurve(
            "Down", CurveType.IEC_VERY_INVERSE,
            pickup_A=80, tms=0.1,
        )
        # Falta de 2000A — ambos veem
        result = check_coordination(
            upstream, downstream,
            fault_current_A=2000, relay_type="digital",
        )
        assert result.passes
        assert result.actual_delta_t_s >= result.required_delta_t_s

    def test_violation_when_no_margin(self):
        """Mesma curva e mesma TMS → Δt ≈ 0 → fail."""
        u = TCCCurve("U", CurveType.IEC_STANDARD_INVERSE, 100, 0.5)
        d = TCCCurve("D", CurveType.IEC_STANDARD_INVERSE, 100, 0.5)
        result = check_coordination(u, d, 1000, "digital")
        assert not result.passes
        assert result.actual_delta_t_s < 0.01

    def test_relay_type_affects_required_margin(self):
        u = TCCCurve("U", CurveType.IEC_VERY_INVERSE, 200, 0.5)
        d = TCCCurve("D", CurveType.IEC_VERY_INVERSE, 80, 0.2)
        # Eletromecânico exige mais margem
        r_em = check_coordination(u, d, 2000, "electromechanical")
        r_dig = check_coordination(u, d, 2000, "digital")
        assert r_em.required_delta_t_s > r_dig.required_delta_t_s

    def test_inf_times_dont_pass(self):
        """Se nenhum dos relés enxerga a falta (M ≤ 1), não passa."""
        u = TCCCurve("U", CurveType.IEC_STANDARD_INVERSE, 1000, 0.5)
        d = TCCCurve("D", CurveType.IEC_STANDARD_INVERSE, 800, 0.5)
        # I = 500 < pickups → ambos t=inf
        r = check_coordination(u, d, 500, "digital")
        assert not r.passes


class TestMarginConstants:

    def test_margins_decreasing_by_technology(self):
        """EM > Static > Digital ≥ Numerical."""
        assert (
            COORDINATION_MARGIN_S["electromechanical"]
            > COORDINATION_MARGIN_S["static"]
        )
        assert (
            COORDINATION_MARGIN_S["static"]
            > COORDINATION_MARGIN_S["digital"]
        )
