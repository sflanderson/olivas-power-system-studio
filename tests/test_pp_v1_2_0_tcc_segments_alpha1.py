"""
tests.test_pp_v1_2_0_tcc_segments_alpha1 — sub-sprint α.1.

Cobre os 4 segments fundacionais introduzidos em v1.2.0 α.1:

* ``TCCSegmentLT`` — Pickup Long-Time (51 IDMT)
* ``TCCSegmentST`` — Pickup Short-Time (50 backup com delay)
* ``TCCSegmentINST`` — Pickup Instantaneous (50)
* ``TCCSegmentDefiniteTime`` — Definite-time element

Aceite α.1
==========

* 16+ testes (4 por segment) — cobre time_at_current, points,
  enabled flag, edge cases (I = pickup, I = 0, I muito grande).
* Smoke test composição: 4 segments num plot, verifica
  que ``composite_time_at_current`` retorna o min correto.
* Não regride o módulo legacy ``tcc_curves.py``.

Cobertura normativa
====================

* IEC 60255-151:2009 (Pickup characteristics)
* IEEE C37.112-2018 (Inverse-Time equations)
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_curves import CurveType
from app.postprocessor.tcc_segments import (
    TCCSegment,
    TCCSegmentDefiniteTime,
    TCCSegmentINST,
    TCCSegmentLT,
    TCCSegmentST,
    composite_time_at_current,
)


# ---------------------------------------------------------------------------
# TCCSegmentLT — Long-Time IDMT
# ---------------------------------------------------------------------------


class TestTCCSegmentLT:

    def test_below_pickup_returns_inf(self):
        s = TCCSegmentLT(
            segment_id="51 IEC SI",
            pickup_A=100.0,
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            tms=0.5,
        )
        assert math.isinf(s.time_at_current(50.0))
        assert math.isinf(s.time_at_current(99.0))
        assert math.isinf(s.time_at_current(100.0))  # exatamente no pickup

    def test_above_pickup_finite_decreasing(self):
        s = TCCSegmentLT(
            segment_id="51 IEC SI",
            pickup_A=100.0,
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            tms=1.0,
        )
        t1 = s.time_at_current(200.0)   # M=2
        t2 = s.time_at_current(500.0)   # M=5
        t3 = s.time_at_current(1000.0)  # M=10
        assert math.isfinite(t1)
        assert t1 > t2 > t3, "tempo deve diminuir com aumento da corrente"

    def test_iec_si_at_2x_around_10s(self):
        """Para IEC SI, M=2, TMS=1: t ≈ 10s (referência)."""
        s = TCCSegmentLT(
            segment_id="51",
            pickup_A=100.0,
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            tms=1.0,
        )
        t = s.time_at_current(200.0)
        assert 9 < t < 11, f"esperado ~10s, obteve {t:.2f}s"

    def test_disabled_returns_inf_always(self):
        s = TCCSegmentLT(
            segment_id="51",
            pickup_A=100.0,
            curve_type=CurveType.IEC_VERY_INVERSE,
            tms=0.5,
            enabled=False,
        )
        assert math.isinf(s.time_at_current(500.0))
        assert math.isinf(s.time_at_current(10000.0))

    def test_points_excludes_inf(self):
        s = TCCSegmentLT(
            segment_id="51",
            pickup_A=100.0,
            curve_type=CurveType.IEC_VERY_INVERSE,
            tms=0.3,
        )
        pts = s.points(i_min_A=10, i_max_A=10000, n_points=50)
        # Todos os pontos têm t finito
        for I, t in pts:
            assert math.isfinite(t)
            assert t > 0
            assert I > s.pickup_A
        # Pelo menos alguns pontos
        assert len(pts) >= 30


# ---------------------------------------------------------------------------
# TCCSegmentST — Short-Time
# ---------------------------------------------------------------------------


class TestTCCSegmentST:

    def test_below_pickup_returns_inf(self):
        s = TCCSegmentST(
            segment_id="50ST",
            pickup_A=500.0,
            delay_s=0.10,
        )
        assert math.isinf(s.time_at_current(100.0))
        assert math.isinf(s.time_at_current(499.0))

    def test_at_or_above_pickup_returns_delay(self):
        s = TCCSegmentST(
            segment_id="50ST",
            pickup_A=500.0,
            delay_s=0.10,
        )
        assert s.time_at_current(500.0) == 0.10
        assert s.time_at_current(1000.0) == 0.10
        assert s.time_at_current(10000.0) == 0.10

    def test_disabled_returns_inf(self):
        s = TCCSegmentST(
            segment_id="50ST",
            pickup_A=500.0,
            delay_s=0.10,
            enabled=False,
        )
        assert math.isinf(s.time_at_current(2000.0))

    def test_points_constant_after_pickup(self):
        s = TCCSegmentST(
            segment_id="50ST",
            pickup_A=500.0,
            delay_s=0.05,
        )
        pts = s.points(i_min_A=100, i_max_A=10000, n_points=50)
        # Todo ponto tem t = 0.05
        assert len(pts) >= 30
        for _, t in pts:
            assert t == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# TCCSegmentINST — Instantaneous
# ---------------------------------------------------------------------------


class TestTCCSegmentINST:

    def test_below_pickup_returns_inf(self):
        s = TCCSegmentINST(
            segment_id="50",
            pickup_A=2000.0,
        )
        assert math.isinf(s.time_at_current(1500.0))

    def test_default_delay_is_2cycles(self):
        """default 0.04s = 2 ciclos @ 50Hz."""
        s = TCCSegmentINST(
            segment_id="50",
            pickup_A=2000.0,
        )
        assert s.inherent_delay_s == pytest.approx(0.04)
        assert s.time_at_current(5000.0) == pytest.approx(0.04)

    def test_custom_inherent_delay(self):
        s = TCCSegmentINST(
            segment_id="50",
            pickup_A=2000.0,
            inherent_delay_s=0.025,  # 1.25 ciclos
        )
        assert s.time_at_current(5000.0) == pytest.approx(0.025)

    def test_disabled_returns_inf(self):
        s = TCCSegmentINST(
            segment_id="50",
            pickup_A=2000.0,
            enabled=False,
        )
        assert math.isinf(s.time_at_current(10000.0))


# ---------------------------------------------------------------------------
# TCCSegmentDefiniteTime — DT element
# ---------------------------------------------------------------------------


class TestTCCSegmentDefiniteTime:

    def test_dt_returns_delay_above_pickup(self):
        s = TCCSegmentDefiniteTime(
            segment_id="51DT-backup",
            pickup_A=300.0,
            delay_s=0.50,
        )
        assert math.isinf(s.time_at_current(100.0))
        assert s.time_at_current(500.0) == pytest.approx(0.50)
        assert s.time_at_current(10000.0) == pytest.approx(0.50)

    def test_dt_disabled_returns_inf(self):
        s = TCCSegmentDefiniteTime(
            segment_id="51DT",
            pickup_A=300.0,
            delay_s=0.50,
            enabled=False,
        )
        assert math.isinf(s.time_at_current(5000.0))


# ---------------------------------------------------------------------------
# composite_time_at_current
# ---------------------------------------------------------------------------


class TestCompositeTimeAtCurrent:
    """
    Modela um relé real com 51 LT + 50 INST. Em correntes
    pequenas, só 51 dispara (LT controla). Em correntes
    altas, 50 dispara primeiro (envelope colapsa para
    inherent_delay).
    """

    def _build_relay(self):
        return [
            TCCSegmentLT(
                segment_id="51 IEC VI",
                pickup_A=100.0,
                curve_type=CurveType.IEC_VERY_INVERSE,
                tms=0.30,
            ),
            TCCSegmentINST(
                segment_id="50",
                pickup_A=2000.0,
                inherent_delay_s=0.04,
            ),
        ]

    def test_low_current_only_LT_drives(self):
        relay = self._build_relay()
        # 500A: M=5 para LT, abaixo do pickup do INST
        # IEC VI t = 0.30 * 13.5/(5-1) = 1.0125s
        t = composite_time_at_current(relay, 500.0)
        assert 0.9 < t < 1.2

    def test_high_current_INST_drives(self):
        relay = self._build_relay()
        # 5000A: bem acima do pickup INST → 0.04s domina
        t = composite_time_at_current(relay, 5000.0)
        assert t == pytest.approx(0.04)

    def test_below_all_pickups_returns_inf(self):
        relay = self._build_relay()
        t = composite_time_at_current(relay, 50.0)
        assert math.isinf(t)

    def test_empty_returns_inf(self):
        assert math.isinf(composite_time_at_current([], 100.0))

    def test_disabled_segment_ignored(self):
        relay = [
            TCCSegmentLT(
                segment_id="51", pickup_A=100.0,
                curve_type=CurveType.IEC_VERY_INVERSE, tms=0.30,
                enabled=False,  # desligado
            ),
            TCCSegmentINST(
                segment_id="50", pickup_A=2000.0, inherent_delay_s=0.04,
            ),
        ]
        # 500A: LT desligado, INST não pickup → inf
        t = composite_time_at_current(relay, 500.0)
        assert math.isinf(t)
        # 5000A: só INST disponível
        t2 = composite_time_at_current(relay, 5000.0)
        assert t2 == pytest.approx(0.04)


# ---------------------------------------------------------------------------
# Protocol conformance — todas as classes seguem TCCSegment
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    """Garante que cada segment satisfaz o protocol TCCSegment."""

    @pytest.mark.parametrize("seg_factory", [
        lambda: TCCSegmentLT(
            segment_id="x", pickup_A=100, curve_type=CurveType.IEC_VERY_INVERSE,
            tms=0.3,
        ),
        lambda: TCCSegmentST(segment_id="x", pickup_A=100, delay_s=0.1),
        lambda: TCCSegmentINST(segment_id="x", pickup_A=100),
        lambda: TCCSegmentDefiniteTime(
            segment_id="x", pickup_A=100, delay_s=0.5,
        ),
    ])
    def test_isinstance_TCCSegment(self, seg_factory):
        seg = seg_factory()
        assert isinstance(seg, TCCSegment)
        # interface básica
        assert hasattr(seg, "segment_id")
        assert hasattr(seg, "enabled")
        assert callable(seg.time_at_current)
        assert callable(seg.points)
