"""
tests.test_pp_v1_2_0_tcc_segments_alpha4 — sub-sprint α.4.

Cobre os 4 segments de breaker introduzidos em v1.2.0 α.4:

* ``TCCSegmentOpening`` — opening time (mecânico, sem arc)
* ``TCCSegmentClearing`` — total clearing (opening + arc)
* ``TCCSegmentOpenClearCurve`` — base segment + arc adicional
* ``TCCSegmentOpenClearBand`` — banda entre 2 envelopes

Aceite α.4
==========

* 16+ testes, 100% verde
* Não regride α.1, α.2, α.3

Cobertura normativa
====================

* IEEE C37.04 — Power Circuit Breakers
* IEC 62271-100 — High-voltage switchgear
* IEEE 242 §15 — Coordination
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_curves import CurveType
from app.postprocessor.tcc_segments import (
    TCCSegment,
    TCCSegmentClearing,
    TCCSegmentLT,
    TCCSegmentOpening,
    TCCSegmentOpenClearBand,
    TCCSegmentOpenClearCurve,
)


# ---------------------------------------------------------------------------
# TCCSegmentOpening
# ---------------------------------------------------------------------------


class TestTCCSegmentOpening:

    def test_below_pickup_returns_inf(self):
        s = TCCSegmentOpening(
            segment_id="LV CB opening",
            pickup_A=500.0,
            opening_time_s=0.05,    # 3 cycles @ 60Hz
        )
        assert math.isinf(s.time_at_current(100.0))

    def test_above_pickup_returns_opening_time(self):
        s = TCCSegmentOpening(
            segment_id="x", pickup_A=500.0, opening_time_s=0.05,
        )
        assert s.time_at_current(500.0) == pytest.approx(0.05)
        assert s.time_at_current(5000.0) == pytest.approx(0.05)

    def test_disabled_returns_inf(self):
        s = TCCSegmentOpening(
            segment_id="x", pickup_A=500.0, opening_time_s=0.05,
            enabled=False,
        )
        assert math.isinf(s.time_at_current(2000.0))

    def test_points_constant_after_pickup(self):
        s = TCCSegmentOpening(
            segment_id="x", pickup_A=500.0, opening_time_s=0.04,
        )
        pts = s.points(i_min_A=100, i_max_A=10000, n_points=30)
        for _, t in pts:
            assert t == pytest.approx(0.04)


# ---------------------------------------------------------------------------
# TCCSegmentClearing
# ---------------------------------------------------------------------------


class TestTCCSegmentClearing:

    def test_clearing_slower_than_opening(self):
        """Para o mesmo CB, clearing > opening sempre."""
        opn = TCCSegmentOpening(
            segment_id="open", pickup_A=500, opening_time_s=0.05,
        )
        clr = TCCSegmentClearing(
            segment_id="clear", pickup_A=500, clearing_time_s=0.083,
        )
        for I in (1000, 5000, 10000):
            assert clr.time_at_current(I) > opn.time_at_current(I)

    def test_below_pickup_returns_inf(self):
        s = TCCSegmentClearing(
            segment_id="x", pickup_A=500, clearing_time_s=0.083,
        )
        assert math.isinf(s.time_at_current(100))

    def test_above_pickup_returns_clearing(self):
        s = TCCSegmentClearing(
            segment_id="x", pickup_A=500, clearing_time_s=0.083,
        )
        assert s.time_at_current(2000) == pytest.approx(0.083)


# ---------------------------------------------------------------------------
# TCCSegmentOpenClearCurve
# ---------------------------------------------------------------------------


class TestTCCSegmentOpenClearCurve:

    def _make_relay_with_breaker(self):
        """Relé IEC SI 100A TMS=0.5 + adicional de arc 40ms."""
        relay = TCCSegmentLT(
            segment_id="51 IEC SI",
            pickup_A=100.0,
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            tms=0.5,
        )
        return relay, TCCSegmentOpenClearCurve(
            segment_id="51 + breaker",
            base_segment=relay,
            arc_extinguishing_s=0.04,
        )

    def test_total_is_relay_plus_breaker_arc(self):
        relay, total = self._make_relay_with_breaker()
        I = 500.0
        t_relay = relay.time_at_current(I)
        t_total = total.time_at_current(I)
        assert t_total == pytest.approx(t_relay + 0.04)

    def test_below_pickup_returns_inf(self):
        relay, total = self._make_relay_with_breaker()
        # 50A está abaixo do pickup do relé
        assert math.isinf(total.time_at_current(50.0))

    def test_disabled_returns_inf(self):
        relay = TCCSegmentLT(
            segment_id="51", pickup_A=100,
            curve_type=CurveType.IEC_VERY_INVERSE, tms=0.5,
        )
        total = TCCSegmentOpenClearCurve(
            segment_id="x", base_segment=relay,
            arc_extinguishing_s=0.04, enabled=False,
        )
        assert math.isinf(total.time_at_current(500))

    def test_default_arc_is_2cycles_60hz(self):
        relay = TCCSegmentLT(
            segment_id="51", pickup_A=100,
            curve_type=CurveType.IEC_STANDARD_INVERSE, tms=0.5,
        )
        total = TCCSegmentOpenClearCurve(
            segment_id="x", base_segment=relay,
        )
        assert total.arc_extinguishing_s == pytest.approx(0.04)

    def test_points_count(self):
        _, total = self._make_relay_with_breaker()
        pts = total.points(i_min_A=100, i_max_A=10000, n_points=50)
        assert len(pts) > 30


# ---------------------------------------------------------------------------
# TCCSegmentOpenClearBand
# ---------------------------------------------------------------------------


class TestTCCSegmentOpenClearBand:

    def _make_band(self):
        opn = TCCSegmentOpening(
            segment_id="opening", pickup_A=500, opening_time_s=0.05,
        )
        clr = TCCSegmentClearing(
            segment_id="clearing", pickup_A=500, clearing_time_s=0.083,
        )
        return TCCSegmentOpenClearBand(
            segment_id="LV CB band",
            opening_segment=opn,
            clearing_segment=clr,
        )

    def test_time_at_current_returns_clearing(self):
        """Convenção: time_at_current = clearing (conservador)."""
        b = self._make_band()
        assert b.time_at_current(1000) == pytest.approx(0.083)

    def test_time_opening_separately(self):
        b = self._make_band()
        assert b.time_opening(1000) == pytest.approx(0.05)

    def test_time_clearing_separately(self):
        b = self._make_band()
        assert b.time_clearing(1000) == pytest.approx(0.083)

    def test_below_pickup_returns_inf_in_all(self):
        b = self._make_band()
        assert math.isinf(b.time_opening(100))
        assert math.isinf(b.time_clearing(100))
        assert math.isinf(b.time_at_current(100))

    def test_disabled_returns_inf_in_all(self):
        opn = TCCSegmentOpening(
            segment_id="o", pickup_A=500, opening_time_s=0.05,
        )
        clr = TCCSegmentClearing(
            segment_id="c", pickup_A=500, clearing_time_s=0.083,
        )
        b = TCCSegmentOpenClearBand(
            segment_id="x",
            opening_segment=opn, clearing_segment=clr,
            enabled=False,
        )
        assert math.isinf(b.time_opening(2000))
        assert math.isinf(b.time_clearing(2000))
        assert math.isinf(b.time_at_current(2000))

    def test_opening_and_clearing_points_separately(self):
        b = self._make_band()
        pts_o = b.opening_points(i_min_A=100, i_max_A=10000, n_points=20)
        pts_c = b.clearing_points(i_min_A=100, i_max_A=10000, n_points=20)
        assert len(pts_o) > 5
        assert len(pts_c) > 5


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:

    def _factories(self):
        return [
            lambda: TCCSegmentOpening(
                segment_id="x", pickup_A=500, opening_time_s=0.05,
            ),
            lambda: TCCSegmentClearing(
                segment_id="x", pickup_A=500, clearing_time_s=0.083,
            ),
            lambda: TCCSegmentOpenClearCurve(
                segment_id="x",
                base_segment=TCCSegmentLT(
                    segment_id="b", pickup_A=100,
                    curve_type=CurveType.IEC_STANDARD_INVERSE,
                    tms=0.5,
                ),
                arc_extinguishing_s=0.04,
            ),
            lambda: TCCSegmentOpenClearBand(
                segment_id="x",
                opening_segment=TCCSegmentOpening(
                    segment_id="o", pickup_A=500, opening_time_s=0.05,
                ),
                clearing_segment=TCCSegmentClearing(
                    segment_id="c", pickup_A=500, clearing_time_s=0.083,
                ),
            ),
        ]

    def test_each_factory_satisfies_protocol(self):
        for factory in self._factories():
            seg = factory()
            assert isinstance(seg, TCCSegment)
            assert callable(seg.time_at_current)
            assert callable(seg.points)
