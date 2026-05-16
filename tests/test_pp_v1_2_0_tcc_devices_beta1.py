"""
tests.test_pp_v1_2_0_tcc_devices_beta1 — sub-sprint β.1.

Cobre ``TCCDevice`` base introduzido em v1.2.0 β.1:

* Construção com tuple (preferido) ou list (auto-convert)
* Validação de TCCSegment Protocol nos elementos
* ``composite_time_at_current`` reusa helper α
* ``composite_points`` para plot
* ``triggered_segment`` (qual segment "venceu")
* ``with_segment_enabled`` (functional immutable update)
* ``with_segment_added`` (builder pattern)
* ``enabled_segments`` filter
* Edge cases (device vazio, todos disabled)

**Aceite β.1**: 12+ testes, 100% verde, sem regressão α.
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_curves import CurveType
from app.postprocessor.tcc_devices import TCCDevice
from app.postprocessor.tcc_segments import (
    TCCSegment,
    TCCSegmentDefiniteTime,
    TCCSegmentINST,
    TCCSegmentLT,
)


# ---------------------------------------------------------------------------
# Construção e validação
# ---------------------------------------------------------------------------


class TestTCCDeviceConstruction:

    def test_empty_device_constructs(self):
        d = TCCDevice(device_id="empty")
        assert len(d) == 0
        assert d.segments == ()

    def test_with_one_segment(self):
        seg = TCCSegmentLT(
            segment_id="51", pickup_A=100.0,
            curve_type=CurveType.IEC_VERY_INVERSE, tms=0.30,
        )
        d = TCCDevice(device_id="x", segments=(seg,))
        assert len(d) == 1

    def test_list_is_converted_to_tuple(self):
        """Aceita list mas armazena tuple."""
        seg = TCCSegmentLT(
            segment_id="51", pickup_A=100.0,
            curve_type=CurveType.IEC_VERY_INVERSE, tms=0.30,
        )
        d = TCCDevice(device_id="x", segments=[seg])
        assert isinstance(d.segments, tuple)

    def test_invalid_segment_raises_typeerror(self):
        """Elementos que não satisfazem Protocol TCCSegment falham."""
        with pytest.raises(TypeError):
            TCCDevice(device_id="x", segments=("not_a_segment",))

    def test_default_metadata(self):
        d = TCCDevice(device_id="x")
        assert d.manufacturer == "Generic"
        assert d.model == "Generic"

    def test_custom_metadata(self):
        d = TCCDevice(
            device_id="R-MAIN-FEEDER",
            manufacturer="SEL",
            model="751",
        )
        assert d.manufacturer == "SEL"
        assert d.model == "751"


# ---------------------------------------------------------------------------
# composite_time_at_current
# ---------------------------------------------------------------------------


class TestCompositeTimeAtCurrent:
    """
    Modela um relé real com 51 LT (IEC VI) + 50 INST (2kA).
    Em correntes baixas, só 51 dispara. Em correntes altas,
    50 vence (envelope colapsa para 0.04s).
    """

    def _build_relay(self) -> TCCDevice:
        s51 = TCCSegmentLT(
            segment_id="51 IEC VI",
            pickup_A=100.0,
            curve_type=CurveType.IEC_VERY_INVERSE,
            tms=0.30,
        )
        s50 = TCCSegmentINST(
            segment_id="50",
            pickup_A=2000.0,
            inherent_delay_s=0.04,
        )
        return TCCDevice(
            device_id="R-MAIN",
            manufacturer="SEL",
            model="751",
            segments=(s51, s50),
        )

    def test_low_current_LT_dominates(self):
        d = self._build_relay()
        # I = 500A: M=5 IEC VI t = 0.30 * 13.5/(5-1) = 1.0125s
        t = d.composite_time_at_current(500)
        assert 0.9 < t < 1.2

    def test_high_current_INST_dominates(self):
        d = self._build_relay()
        t = d.composite_time_at_current(5000)
        assert t == pytest.approx(0.04)

    def test_below_all_pickups_returns_inf(self):
        d = self._build_relay()
        assert math.isinf(d.composite_time_at_current(50))

    def test_empty_device_returns_inf(self):
        d = TCCDevice(device_id="empty")
        assert math.isinf(d.composite_time_at_current(1000))


# ---------------------------------------------------------------------------
# composite_points
# ---------------------------------------------------------------------------


class TestCompositePoints:

    def test_points_count_default(self):
        s = TCCSegmentLT(
            segment_id="51", pickup_A=100,
            curve_type=CurveType.IEC_STANDARD_INVERSE, tms=0.5,
        )
        d = TCCDevice(device_id="x", segments=(s,))
        pts = d.composite_points(i_min_A=10, i_max_A=10000, n_points=200)
        assert len(pts) > 100  # alguns são abaixo do pickup → excluídos

    def test_points_finite_only(self):
        s = TCCSegmentLT(
            segment_id="51", pickup_A=100,
            curve_type=CurveType.IEC_VERY_INVERSE, tms=0.3,
        )
        d = TCCDevice(device_id="x", segments=(s,))
        pts = d.composite_points()
        for I, t in pts:
            assert math.isfinite(t)
            assert t > 0

    def test_points_empty_device(self):
        d = TCCDevice(device_id="empty")
        pts = d.composite_points()
        assert pts == []


# ---------------------------------------------------------------------------
# triggered_segment
# ---------------------------------------------------------------------------


class TestTriggeredSegment:

    def _build_relay(self) -> TCCDevice:
        s51 = TCCSegmentLT(
            segment_id="51 IEC VI", pickup_A=100,
            curve_type=CurveType.IEC_VERY_INVERSE, tms=0.30,
        )
        s50 = TCCSegmentINST(
            segment_id="50", pickup_A=2000, inherent_delay_s=0.04,
        )
        return TCCDevice(device_id="x", segments=(s51, s50))

    def test_low_current_triggered_is_LT(self):
        d = self._build_relay()
        winner = d.triggered_segment(500)
        assert winner is not None
        assert winner.segment_id == "51 IEC VI"

    def test_high_current_triggered_is_INST(self):
        d = self._build_relay()
        winner = d.triggered_segment(5000)
        assert winner is not None
        assert winner.segment_id == "50"

    def test_below_pickups_triggered_is_none(self):
        d = self._build_relay()
        assert d.triggered_segment(50) is None

    def test_empty_device_triggered_is_none(self):
        d = TCCDevice(device_id="empty")
        assert d.triggered_segment(1000) is None


# ---------------------------------------------------------------------------
# with_segment_enabled / with_segment_added
# ---------------------------------------------------------------------------


class TestImmutableUpdates:

    def _build_relay(self) -> TCCDevice:
        s51 = TCCSegmentLT(
            segment_id="51", pickup_A=100,
            curve_type=CurveType.IEC_VERY_INVERSE, tms=0.30,
        )
        s50 = TCCSegmentINST(
            segment_id="50", pickup_A=2000, inherent_delay_s=0.04,
        )
        return TCCDevice(device_id="x", segments=(s51, s50))

    def test_with_segment_enabled_returns_new_instance(self):
        d = self._build_relay()
        d2 = d.with_segment_enabled(0, False)
        assert d is not d2
        # Original mantém enabled=True
        assert d.segments[0].enabled is True
        # Nova tem enabled=False
        assert d2.segments[0].enabled is False

    def test_with_segment_enabled_disables_LT(self):
        """Se desativar 51 LT, em I baixa volta para inf."""
        d = self._build_relay()
        d2 = d.with_segment_enabled(0, False)
        # 500A: 51 desativado, 50 não pickup → inf
        assert math.isinf(d2.composite_time_at_current(500))
        # 5000A: 50 ainda funciona
        assert d2.composite_time_at_current(5000) == pytest.approx(0.04)

    def test_with_segment_enabled_invalid_idx_raises(self):
        d = self._build_relay()
        with pytest.raises(IndexError):
            d.with_segment_enabled(99, False)
        with pytest.raises(IndexError):
            d.with_segment_enabled(-1, False)

    def test_with_segment_added_appends(self):
        d = self._build_relay()
        s49 = TCCSegmentDefiniteTime(
            segment_id="49 thermal", pickup_A=120, delay_s=2.0,
        )
        d2 = d.with_segment_added(s49)
        assert len(d) == 2
        assert len(d2) == 3
        assert d2.segments[-1] is s49

    def test_with_segment_added_invalid_type_raises(self):
        d = self._build_relay()
        with pytest.raises(TypeError):
            d.with_segment_added("not_a_segment")


# ---------------------------------------------------------------------------
# enabled_segments
# ---------------------------------------------------------------------------


class TestEnabledSegments:

    def test_all_enabled(self):
        s1 = TCCSegmentINST(segment_id="50", pickup_A=2000)
        s2 = TCCSegmentLT(
            segment_id="51", pickup_A=100,
            curve_type=CurveType.IEC_VERY_INVERSE, tms=0.5,
        )
        d = TCCDevice(device_id="x", segments=(s1, s2))
        en = d.enabled_segments()
        assert len(en) == 2

    def test_one_disabled_filtered(self):
        s1 = TCCSegmentINST(segment_id="50", pickup_A=2000)
        s2 = TCCSegmentLT(
            segment_id="51", pickup_A=100,
            curve_type=CurveType.IEC_VERY_INVERSE, tms=0.5,
            enabled=False,
        )
        d = TCCDevice(device_id="x", segments=(s1, s2))
        en = d.enabled_segments()
        assert len(en) == 1
        assert en[0].segment_id == "50"


# ---------------------------------------------------------------------------
# Smoke test SEL-751-like (51 + 50 + 49)
# ---------------------------------------------------------------------------


class TestSmokeRealRelay:
    """Modela um relé multi-função real para verificar
    que a API agrupa coerentemente."""

    def test_sel_751_motor_protection(self):
        """SEL-751 motor protection: 51 (overcurrent) + 50
        (instantaneous) + 49 (thermal model)."""
        s51 = TCCSegmentLT(
            segment_id="51 IEC SI",
            pickup_A=120,
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            tms=0.20,
        )
        s50 = TCCSegmentINST(
            segment_id="50 INST",
            pickup_A=1500,
            inherent_delay_s=0.04,
        )
        s49 = TCCSegmentDefiniteTime(
            segment_id="49 thermal",
            pickup_A=130,
            delay_s=8.0,  # tempo grande de stall
        )
        relay = TCCDevice(
            device_id="R-MOT-1",
            manufacturer="SEL",
            model="751",
            segments=(s51, s50, s49),
        )

        # Em corrente nominal (100A): nada dispara
        # (51 pickup=120, 49 pickup=130, 50 pickup=1500)
        assert math.isinf(relay.composite_time_at_current(100))

        # Em sobrecorrente moderada (200A): cálculo IEC SI
        # M = 200/120 = 1.667
        # t_51 = 0.20 * 0.14 / (1.667^0.02 - 1)
        #      = 0.20 * 0.14 / 0.01032 ≈ 2.71 s
        # t_49 = 8.0 s (DT)
        # t_50 = inf (200 < 1500)
        # min(2.71, 8.0, inf) = 2.71 s → 51 vence
        t = relay.composite_time_at_current(200)
        assert 2.5 < t < 3.0, f"esperado ~2.71s (51 IEC SI), obteve {t}"
        winner = relay.triggered_segment(200)
        assert winner is s51

        # Em sobrecorrente leve (135A — pouco acima do pickup 49):
        # M = 135/120 = 1.125
        # t_51 = 0.20 * 0.14 / (1.125^0.02 - 1)
        #      = 0.20 * 0.14 / 0.00237 ≈ 11.8 s
        # t_49 = 8.0 s (DT, 135 > pickup 130)
        # min = 8.0 → 49 thermal vence (cenário típico de
        # proteção de motor onde 49 atua antes de 51 em
        # correntes baixas)
        t135 = relay.composite_time_at_current(135)
        assert t135 == pytest.approx(8.0)
        winner135 = relay.triggered_segment(135)
        assert winner135 is s49

        # Em fault (3000A): 50 INST domina (3000 > 1500)
        t = relay.composite_time_at_current(3000)
        assert t == pytest.approx(0.04)
        winner = relay.triggered_segment(3000)
        assert winner is s50
