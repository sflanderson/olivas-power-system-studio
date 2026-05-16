"""
tests.test_pp_v1_2_0_tcc_segments_alpha5 — sub-sprint α.5.

Cobre os 2 segments finais introduzidos em v1.2.0 α.5:

* ``TCCSegmentSlopeT`` — `T = K · (I/Ipu)^(-slope)` no log-log
* ``TCCSegmentDelayBand`` — banda entre 2 SlopeT (min/max)

**Aceite α.5**: 8+ testes, 100% verde, fecha 16/16 segments
da Fase α.

Cobertura normativa
====================

* PTW Reference-CAPTOR.pdf "Delay Band (I^Slope-T)"
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_segments import (
    TCCSegment,
    TCCSegmentDelayBand,
    TCCSegmentSlopeT,
)


# ---------------------------------------------------------------------------
# TCCSegmentSlopeT
# ---------------------------------------------------------------------------


class TestTCCSegmentSlopeT:

    def test_below_pickup_returns_inf(self):
        s = TCCSegmentSlopeT(
            segment_id="x", pickup_A=100, K=1.0, slope=2.0,
        )
        assert math.isinf(s.time_at_current(50))
        assert math.isinf(s.time_at_current(100))

    def test_slope_2_is_inverse_square(self):
        """T = K * (I/Ipu)^(-2). I=2*Ipu → T=K/4. I=10*Ipu → T=K/100."""
        s = TCCSegmentSlopeT(
            segment_id="x", pickup_A=100, K=1.0, slope=2.0,
        )
        assert s.time_at_current(200) == pytest.approx(0.25, rel=1e-3)
        assert s.time_at_current(1000) == pytest.approx(0.01, rel=1e-3)

    def test_slope_0_is_constant(self):
        """slope=0 → curva horizontal = K segundos."""
        s = TCCSegmentSlopeT(
            segment_id="x", pickup_A=100, K=0.5, slope=0.0,
        )
        # Acima do pickup, sempre retorna K
        assert s.time_at_current(200) == pytest.approx(0.5)
        assert s.time_at_current(10000) == pytest.approx(0.5)

    def test_slope_1_is_inverse_linear(self):
        s = TCCSegmentSlopeT(
            segment_id="x", pickup_A=100, K=10.0, slope=1.0,
        )
        # I=200 → T = 10 * (1/2) = 5
        assert s.time_at_current(200) == pytest.approx(5.0, rel=1e-3)
        # I=1000 → T = 10 * (1/10) = 1
        assert s.time_at_current(1000) == pytest.approx(1.0, rel=1e-3)

    def test_disabled_returns_inf(self):
        s = TCCSegmentSlopeT(
            segment_id="x", pickup_A=100, K=1.0, slope=2.0,
            enabled=False,
        )
        assert math.isinf(s.time_at_current(500))

    def test_negative_K_returns_inf(self):
        s = TCCSegmentSlopeT(
            segment_id="x", pickup_A=100, K=-1.0, slope=2.0,
        )
        # K negativo → tempo negativo → inf
        assert math.isinf(s.time_at_current(500))

    def test_points_non_empty(self):
        s = TCCSegmentSlopeT(
            segment_id="x", pickup_A=100, K=10.0, slope=2.0,
        )
        pts = s.points(i_min_A=10, i_max_A=10000, n_points=50)
        assert len(pts) > 30
        for I, t in pts:
            assert math.isfinite(t)
            assert t > 0


# ---------------------------------------------------------------------------
# TCCSegmentDelayBand
# ---------------------------------------------------------------------------


class TestTCCSegmentDelayBand:

    def _make_band(self):
        # Banda entre slope=2 K=8 (rápido) e slope=2 K=12 (lento).
        # Mesma slope, K diferente: deslocamento vertical no log-log.
        s_min = TCCSegmentSlopeT(
            segment_id="min", pickup_A=100, K=8.0, slope=2.0,
        )
        s_max = TCCSegmentSlopeT(
            segment_id="max", pickup_A=100, K=12.0, slope=2.0,
        )
        return TCCSegmentDelayBand(
            segment_id="band",
            min_segment=s_min,
            max_segment=s_max,
        )

    def test_time_at_current_returns_max(self):
        b = self._make_band()
        # I=200, slope=2, M=2: t_min = 8/4=2, t_max = 12/4=3
        assert b.time_at_current(200) == pytest.approx(3.0, rel=1e-3)

    def test_time_min_separately(self):
        b = self._make_band()
        assert b.time_min(200) == pytest.approx(2.0, rel=1e-3)

    def test_time_max_separately(self):
        b = self._make_band()
        assert b.time_max(200) == pytest.approx(3.0, rel=1e-3)

    def test_min_less_than_max_at_all_currents(self):
        b = self._make_band()
        for I in (200, 500, 1000, 5000):
            assert b.time_min(I) < b.time_max(I)

    def test_below_pickup_returns_inf_in_all(self):
        b = self._make_band()
        assert math.isinf(b.time_min(50))
        assert math.isinf(b.time_max(50))
        assert math.isinf(b.time_at_current(50))

    def test_disabled_returns_inf_in_all(self):
        s_min = TCCSegmentSlopeT(
            segment_id="min", pickup_A=100, K=8.0, slope=2.0,
        )
        s_max = TCCSegmentSlopeT(
            segment_id="max", pickup_A=100, K=12.0, slope=2.0,
        )
        b = TCCSegmentDelayBand(
            segment_id="x",
            min_segment=s_min, max_segment=s_max,
            enabled=False,
        )
        assert math.isinf(b.time_min(500))
        assert math.isinf(b.time_max(500))
        assert math.isinf(b.time_at_current(500))

    def test_points_minmax_separately(self):
        b = self._make_band()
        min_pts = b.min_points(i_min_A=200, i_max_A=10000, n_points=20)
        max_pts = b.max_points(i_min_A=200, i_max_A=10000, n_points=20)
        assert len(min_pts) > 5
        assert len(max_pts) > 5


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:

    @pytest.mark.parametrize("seg_factory", [
        lambda: TCCSegmentSlopeT(
            segment_id="x", pickup_A=100, K=1.0, slope=2.0,
        ),
        lambda: TCCSegmentDelayBand(
            segment_id="x",
            min_segment=TCCSegmentSlopeT(
                segment_id="m", pickup_A=100, K=8.0, slope=2.0,
            ),
            max_segment=TCCSegmentSlopeT(
                segment_id="M", pickup_A=100, K=12.0, slope=2.0,
            ),
        ),
    ])
    def test_protocol(self, seg_factory):
        seg = seg_factory()
        assert isinstance(seg, TCCSegment)
        assert callable(seg.time_at_current)
        assert callable(seg.points)
