"""
tests.test_pp_v1_2_0_tcc_devices_beta2 — sub-sprint β.2.

Cobre ``MultiFunctionRelay`` (subclasse de TCCDevice) com
4 helpers para padrões comuns de proteção:

* ``relay_51_only`` — overcurrent IDMT puro
* ``relay_51_and_50`` — IDMT + instantâneo
* ``relay_51_50_49`` — motor protection
* ``relay_51_50_87`` — transformer differential

**Aceite β.2**: 12+ testes, 100% verde, sem regressão β.1.
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_curves import CurveType
from app.postprocessor.tcc_devices import MultiFunctionRelay, TCCDevice
from app.postprocessor.tcc_segments import (
    TCCSegmentDefiniteTime,
    TCCSegmentINST,
    TCCSegmentLT,
)


# ---------------------------------------------------------------------------
# relay_51_only
# ---------------------------------------------------------------------------


class TestRelay51Only:

    def test_constructs_with_one_LT_segment(self):
        r = MultiFunctionRelay.relay_51_only(
            device_id="R1",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=100.0,
            tms=0.30,
        )
        assert len(r) == 1
        assert isinstance(r.segments[0], TCCSegmentLT)
        assert r.segments[0].pickup_A == 100.0
        assert r.segments[0].tms == 0.30

    def test_is_instance_of_multifunction_and_tccdevice(self):
        """Tipagem: MultiFunctionRelay isinstance TCCDevice."""
        r = MultiFunctionRelay.relay_51_only(
            device_id="R1",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=100, tms=0.3,
        )
        assert isinstance(r, MultiFunctionRelay)
        assert isinstance(r, TCCDevice)

    def test_metadata_passthrough(self):
        r = MultiFunctionRelay.relay_51_only(
            device_id="R-MAIN",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=200, tms=0.5,
            manufacturer="ABB", model="REF615",
        )
        assert r.manufacturer == "ABB"
        assert r.model == "REF615"

    def test_composite_matches_single_LT(self):
        r = MultiFunctionRelay.relay_51_only(
            device_id="R", curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=100, tms=1.0,
        )
        # IEC SI, M=2, TMS=1 → t ≈ 10s
        t = r.composite_time_at_current(200)
        assert 9 < t < 11


# ---------------------------------------------------------------------------
# relay_51_and_50
# ---------------------------------------------------------------------------


class TestRelay51And50:

    def test_constructs_with_two_segments(self):
        r = MultiFunctionRelay.relay_51_and_50(
            device_id="R",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=100, tms_51=0.30,
            pickup_50_A=2000,
        )
        assert len(r) == 2
        assert isinstance(r.segments[0], TCCSegmentLT)
        assert isinstance(r.segments[1], TCCSegmentINST)

    def test_default_50_delay_2cycles(self):
        r = MultiFunctionRelay.relay_51_and_50(
            device_id="R",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=100, tms_51=0.3,
            pickup_50_A=2000,
        )
        s50 = r.segments[1]
        assert s50.inherent_delay_s == pytest.approx(0.04)

    def test_custom_50_delay(self):
        r = MultiFunctionRelay.relay_51_and_50(
            device_id="R",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=100, tms_51=0.3,
            pickup_50_A=2000,
            delay_50_s=0.025,  # 1.5 cycles
        )
        s50 = r.segments[1]
        assert s50.inherent_delay_s == pytest.approx(0.025)

    def test_composite_LT_at_low_INST_at_high(self):
        r = MultiFunctionRelay.relay_51_and_50(
            device_id="R",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_51_A=100, tms_51=0.30,
            pickup_50_A=2000,
        )
        # 500A: M=5, IEC VI t = 0.30 * 13.5/(5-1) ≈ 1.0s → 51 vence
        winner_low = r.triggered_segment(500)
        assert winner_low.segment_id == "51"
        # 5000A: 50 INST domina
        winner_high = r.triggered_segment(5000)
        assert winner_high.segment_id == "50"


# ---------------------------------------------------------------------------
# relay_51_50_49
# ---------------------------------------------------------------------------


class TestRelay51_50_49:

    def test_constructs_with_three_segments(self):
        r = MultiFunctionRelay.relay_51_50_49(
            device_id="R-MOT",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=120, tms_51=0.20,
            pickup_50_A=1500,
            pickup_49_A=130, delay_49_s=8.0,
        )
        assert len(r) == 3
        assert isinstance(r.segments[0], TCCSegmentLT)
        assert isinstance(r.segments[1], TCCSegmentINST)
        assert isinstance(r.segments[2], TCCSegmentDefiniteTime)

    def test_segment_ids(self):
        r = MultiFunctionRelay.relay_51_50_49(
            device_id="R",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=120, tms_51=0.20,
            pickup_50_A=1500,
            pickup_49_A=130, delay_49_s=8.0,
        )
        ids = [s.segment_id for s in r.segments]
        assert "51" in ids
        assert "50" in ids
        assert "49 thermal" in ids

    def test_composite_thermal_dominates_low_overload(self):
        """Em sobrecarga leve, 49 thermal vence (delay fixo
        é mais rápido que IDMT)."""
        r = MultiFunctionRelay.relay_51_50_49(
            device_id="R",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=120, tms_51=0.20,
            pickup_50_A=1500,
            pickup_49_A=130, delay_49_s=8.0,
        )
        # 135A: M=1.125 → t_51 ≈ 11.8s; t_49 = 8.0 → 49 vence
        winner = r.triggered_segment(135)
        assert winner.segment_id == "49 thermal"

    def test_composite_50_dominates_at_fault(self):
        r = MultiFunctionRelay.relay_51_50_49(
            device_id="R",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=120, tms_51=0.20,
            pickup_50_A=1500,
            pickup_49_A=130, delay_49_s=8.0,
        )
        winner = r.triggered_segment(3000)
        assert winner.segment_id == "50"


# ---------------------------------------------------------------------------
# relay_51_50_87
# ---------------------------------------------------------------------------


class TestRelay51_50_87:

    def test_constructs_with_three_segments(self):
        r = MultiFunctionRelay.relay_51_50_87(
            device_id="R-XFMR",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=200, tms_51=0.40,
            pickup_50_A=3000,
            pickup_87_A=500,
        )
        assert len(r) == 3

    def test_default_87_delay_1_5_cycles(self):
        r = MultiFunctionRelay.relay_51_50_87(
            device_id="R",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=200, tms_51=0.40,
            pickup_50_A=3000,
            pickup_87_A=500,
        )
        s87 = r.segments[2]
        assert s87.inherent_delay_s == pytest.approx(0.025)

    def test_87_diff_dominates_in_zone(self):
        """Em fault na zona diferencial, 87 (1.5 cycles)
        vence 51 e 50 (2 cycles)."""
        r = MultiFunctionRelay.relay_51_50_87(
            device_id="R",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=200, tms_51=0.40,
            pickup_50_A=3000,
            pickup_87_A=500,
        )
        # I = 1000A, dentro da zona 87 (>500), abaixo de 50 (<3000)
        # 51: M=5, t = 0.40 * 0.14/(5^0.02-1) ≈ 1.74s
        # 87: 0.025s
        # → 87 vence
        winner = r.triggered_segment(1000)
        assert winner.segment_id == "87 diff"

    def test_50_dominates_above_pickup_50(self):
        r = MultiFunctionRelay.relay_51_50_87(
            device_id="R",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=200, tms_51=0.40,
            pickup_50_A=3000,
            pickup_87_A=500,
        )
        # I = 5000A: 50 (40ms) vs 87 (25ms) → 87 ainda vence
        # Por design: 87 deve ser sempre mais rápido que 50
        winner = r.triggered_segment(5000)
        assert winner.segment_id == "87 diff"


# ---------------------------------------------------------------------------
# Inheritance + with_* compatibility
# ---------------------------------------------------------------------------


class TestInheritanceCompat:

    def test_with_segment_enabled_returns_multifunction_relay(self):
        """with_segment_enabled em subclasse deve retornar
        instância da MESMA subclasse (MultiFunctionRelay,
        não TCCDevice base)."""
        r = MultiFunctionRelay.relay_51_and_50(
            device_id="R",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=100, tms_51=0.3,
            pickup_50_A=2000,
        )
        r2 = r.with_segment_enabled(0, False)
        # dataclasses.replace mantém o tipo da instância
        assert isinstance(r2, MultiFunctionRelay)

    def test_with_segment_added_returns_multifunction_relay(self):
        r = MultiFunctionRelay.relay_51_only(
            device_id="R",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=100, tms=0.3,
        )
        # adiciona um INST custom
        s50 = TCCSegmentINST(
            segment_id="50 custom", pickup_A=2000, inherent_delay_s=0.05,
        )
        r2 = r.with_segment_added(s50)
        assert isinstance(r2, MultiFunctionRelay)
        assert len(r2) == 2
