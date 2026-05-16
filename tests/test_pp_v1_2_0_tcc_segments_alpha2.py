"""
tests.test_pp_v1_2_0_tcc_segments_alpha2 — sub-sprint α.2.

Cobre os 4 segments adicionais introduzidos em v1.2.0 α.2:

* ``TCCSegmentAdjustableTolerance`` — pickup com banda ±%
* ``TCCSegmentI2T`` — energia constante I²t (HRC fuses,
  cable damage)
* ``TCCSegmentTimeCurrentPoints`` — datasheet tabular com
  interpolação log-log
* ``TCCSegmentFixTimeHorizontal`` — fix-time entre i_min e i_max

Aceite α.2
==========

* 16+ testes (4 por segment), 100% verde
* Não regride α.1 (24 testes anteriores)

Cobertura normativa
====================

* IEC 60269-1 (fusíveis I²t)
* NBR 5410 §6.5.4 (cable thermal stress)
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_curves import CurveType
from app.postprocessor.tcc_segments import (
    TCCSegment,
    TCCSegmentAdjustableTolerance,
    TCCSegmentFixTimeHorizontal,
    TCCSegmentI2T,
    TCCSegmentTimeCurrentPoints,
)


# ---------------------------------------------------------------------------
# TCCSegmentAdjustableTolerance
# ---------------------------------------------------------------------------


class TestTCCSegmentAdjustableTolerance:

    def _make(self, tol_pct=10.0):
        return TCCSegmentAdjustableTolerance(
            segment_id="51 IEC SI ±10%",
            pickup_A_nominal=100.0,
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            tms=1.0,
            tolerance_pct=tol_pct,
        )

    def test_below_pickup_nominal_returns_inf(self):
        s = self._make()
        assert math.isinf(s.time_at_current(50.0))

    def test_envelope_min_is_more_sensitive(self):
        """Envelope min (pickup × 0.9) dispara em correntes
        que não disparam no nominal."""
        s = self._make(tol_pct=10.0)
        # 95A: nominal = inf (abaixo de 100), env_min = finito
        # (95A está acima de pickup_min = 90A)
        assert math.isinf(s.time_at_current(95.0))
        assert math.isfinite(s.time_envelope_min(95.0))

    def test_envelope_max_is_less_sensitive(self):
        """Envelope max (pickup × 1.1) NÃO dispara em
        correntes que disparam no nominal."""
        s = self._make(tol_pct=10.0)
        # 105A: nominal finito, env_max = inf (105 < 110)
        assert math.isfinite(s.time_at_current(105.0))
        assert math.isinf(s.time_envelope_max(105.0))

    def test_envelope_max_slower_than_min_at_same_I(self):
        s = self._make(tol_pct=10.0)
        I = 500.0  # bem acima de todos os pickups
        t_min = s.time_envelope_min(I)
        t_nom = s.time_at_current(I)
        t_max = s.time_envelope_max(I)
        assert t_min < t_nom < t_max

    def test_disabled_returns_inf_in_all(self):
        s = TCCSegmentAdjustableTolerance(
            segment_id="x", pickup_A_nominal=100.0,
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            tms=1.0, tolerance_pct=10.0, enabled=False,
        )
        assert math.isinf(s.time_at_current(500))
        assert math.isinf(s.time_envelope_min(500))
        assert math.isinf(s.time_envelope_max(500))

    def test_envelope_points_count(self):
        s = self._make()
        pts_nom = s.points(i_min_A=100, i_max_A=10000, n_points=50)
        pts_min = s.envelope_min_points(i_min_A=100, i_max_A=10000, n_points=50)
        pts_max = s.envelope_max_points(i_min_A=100, i_max_A=10000, n_points=50)
        assert len(pts_nom) > 30
        assert len(pts_min) > 30
        assert len(pts_max) > 30


# ---------------------------------------------------------------------------
# TCCSegmentI2T
# ---------------------------------------------------------------------------


class TestTCCSegmentI2T:

    def test_below_pickup_returns_inf(self):
        s = TCCSegmentI2T(
            segment_id="HRC fuse I²t",
            pickup_A=100.0,
            K_I2T_kA2_s=50.0,
        )
        assert math.isinf(s.time_at_current(50.0))

    def test_above_pickup_t_proportional_inverse_I_squared(self):
        """t = K_kA²·s / I_kA². Para K=50 kA²·s, I=10kA: t=0.5s."""
        s = TCCSegmentI2T(
            segment_id="x", pickup_A=100.0, K_I2T_kA2_s=50.0,
            time_floor_s=0.001,  # baixo para não interferir
        )
        # I = 10000A = 10kA → t = 50 / 100 = 0.5s
        t = s.time_at_current(10000.0)
        assert t == pytest.approx(0.5, rel=0.01)
        # I = 5000A = 5kA → t = 50 / 25 = 2.0s
        t2 = s.time_at_current(5000.0)
        assert t2 == pytest.approx(2.0, rel=0.01)

    def test_time_floor_clipping(self):
        s = TCCSegmentI2T(
            segment_id="x", pickup_A=100.0, K_I2T_kA2_s=50.0,
            time_floor_s=0.05,
        )
        # I = 100kA → t naive = 50/10000 = 0.005s, clipped to 0.05
        t = s.time_at_current(100000.0)
        assert t == pytest.approx(0.05)

    def test_disabled_returns_inf(self):
        s = TCCSegmentI2T(
            segment_id="x", pickup_A=100.0, K_I2T_kA2_s=50.0,
            enabled=False,
        )
        assert math.isinf(s.time_at_current(10000.0))

    def test_points_decrease_with_I(self):
        s = TCCSegmentI2T(
            segment_id="x", pickup_A=100.0, K_I2T_kA2_s=50.0,
        )
        pts = s.points(i_min_A=200, i_max_A=10000, n_points=20)
        assert len(pts) >= 10
        ts = [t for _, t in pts]
        # tempos descrescentes
        for i in range(1, len(ts)):
            assert ts[i] <= ts[i - 1]


# ---------------------------------------------------------------------------
# TCCSegmentTimeCurrentPoints
# ---------------------------------------------------------------------------


class TestTCCSegmentTimeCurrentPoints:

    def test_minimum_2_points_required(self):
        with pytest.raises(ValueError):
            TCCSegmentTimeCurrentPoints(
                segment_id="x",
                point_pairs=((100.0, 1.0),),
            )

    def test_points_must_be_ordered_increasing_I(self):
        with pytest.raises(ValueError):
            TCCSegmentTimeCurrentPoints(
                segment_id="x",
                point_pairs=((100.0, 1.0), (50.0, 2.0)),
            )

    def test_below_imin_returns_inf(self):
        s = TCCSegmentTimeCurrentPoints(
            segment_id="datasheet",
            point_pairs=(
                (100.0, 10.0),
                (1000.0, 0.1),
            ),
        )
        assert math.isinf(s.time_at_current(50.0))

    def test_at_known_points_returns_exact(self):
        s = TCCSegmentTimeCurrentPoints(
            segment_id="x",
            point_pairs=(
                (100.0, 10.0),
                (1000.0, 0.1),
            ),
        )
        assert s.time_at_current(100.0) == pytest.approx(10.0)
        assert s.time_at_current(1000.0) == pytest.approx(0.1)

    def test_log_log_interpolation(self):
        """Entre (100, 10) e (1000, 0.1): em I=316.2 (meio em log)
        deve dar t ≈ sqrt(10 * 0.1) = 1.0."""
        s = TCCSegmentTimeCurrentPoints(
            segment_id="x",
            point_pairs=(
                (100.0, 10.0),
                (1000.0, 0.1),
            ),
        )
        t = s.time_at_current(316.227766)  # 10**2.5
        assert t == pytest.approx(1.0, rel=0.01)

    def test_extrapolation_above_imax(self):
        s = TCCSegmentTimeCurrentPoints(
            segment_id="x",
            point_pairs=(
                (100.0, 10.0),
                (1000.0, 0.1),
            ),
        )
        # Slope log-log = (log 0.1 - log 10)/(log 1000 - log 100) = -1
        # Extrapolando para I=10000: t = 0.001
        t = s.time_at_current(10000.0)
        assert t == pytest.approx(0.001, rel=0.05)

    def test_disabled_returns_inf(self):
        s = TCCSegmentTimeCurrentPoints(
            segment_id="x",
            point_pairs=(
                (100.0, 10.0),
                (1000.0, 0.1),
            ),
            enabled=False,
        )
        assert math.isinf(s.time_at_current(500.0))


# ---------------------------------------------------------------------------
# TCCSegmentFixTimeHorizontal
# ---------------------------------------------------------------------------


class TestTCCSegmentFixTimeHorizontal:

    def test_outside_range_returns_inf(self):
        s = TCCSegmentFixTimeHorizontal(
            segment_id="breaker mech",
            time_s=0.083,
            i_min_A=100.0,
            i_max_A=50000.0,
        )
        assert math.isinf(s.time_at_current(50.0))     # below i_min
        assert math.isinf(s.time_at_current(100000.0)) # above i_max

    def test_inside_range_returns_time(self):
        s = TCCSegmentFixTimeHorizontal(
            segment_id="x", time_s=0.083, i_min_A=100, i_max_A=50000,
        )
        assert s.time_at_current(100.0) == pytest.approx(0.083)
        assert s.time_at_current(5000.0) == pytest.approx(0.083)
        assert s.time_at_current(50000.0) == pytest.approx(0.083)

    def test_default_imax_unbounded(self):
        s = TCCSegmentFixTimeHorizontal(
            segment_id="x", time_s=0.05, i_min_A=100.0,
        )
        # Sem limite superior (default 1e9)
        assert s.time_at_current(1e8) == pytest.approx(0.05)

    def test_disabled_returns_inf(self):
        s = TCCSegmentFixTimeHorizontal(
            segment_id="x", time_s=0.05, i_min_A=100, enabled=False,
        )
        assert math.isinf(s.time_at_current(500.0))


# ---------------------------------------------------------------------------
# Protocol conformance — α.2 segments
# ---------------------------------------------------------------------------


class TestProtocolConformance:

    @pytest.mark.parametrize("seg_factory", [
        lambda: TCCSegmentAdjustableTolerance(
            segment_id="x", pickup_A_nominal=100.0,
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            tms=1.0, tolerance_pct=10.0,
        ),
        lambda: TCCSegmentI2T(
            segment_id="x", pickup_A=100.0, K_I2T_kA2_s=50.0,
        ),
        lambda: TCCSegmentTimeCurrentPoints(
            segment_id="x",
            point_pairs=((100.0, 10.0), (1000.0, 0.1)),
        ),
        lambda: TCCSegmentFixTimeHorizontal(
            segment_id="x", time_s=0.05, i_min_A=100,
        ),
    ])
    def test_segment_satisfies_protocol(self, seg_factory):
        seg = seg_factory()
        assert isinstance(seg, TCCSegment)
        assert hasattr(seg, "segment_id")
        assert hasattr(seg, "enabled")
        assert callable(seg.time_at_current)
        assert callable(seg.points)
