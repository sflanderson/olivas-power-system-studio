"""
tests.test_pp_v1_2_0_tcc_devices_beta3 — sub-sprint β.3.

Cobre coordenação device-vs-device:

* ``DeviceCoordinationCheck`` — dataclass com triggered_segment_id
* ``check_device_coordination`` — Δt usando composite envelope
* ``check_device_coordination_multi_point`` — múltiplas correntes

**Aceite β.3**: 8+ testes, 100% verde, fecha Fase β.
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_curves import CurveType
from app.postprocessor.tcc_devices import (
    DeviceCoordinationCheck,
    MultiFunctionRelay,
    TCCDevice,
    check_device_coordination,
    check_device_coordination_multi_point,
)


# ---------------------------------------------------------------------------
# Coordenação básica relé-relé
# ---------------------------------------------------------------------------


class TestCheckDeviceCoordination:

    def _build_upstream_downstream(self):
        """Dois relés IDMT em série, upstream lento (TMS=0.5),
        downstream rápido (TMS=0.1). Coord deve passar."""
        up = MultiFunctionRelay.relay_51_only(
            device_id="R-MAIN",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=200, tms=0.5,
            manufacturer="ABB", model="REF615",
        )
        dn = MultiFunctionRelay.relay_51_only(
            device_id="R-FEEDER",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=80, tms=0.1,
        )
        return up, dn

    def test_returns_dataclass(self):
        up, dn = self._build_upstream_downstream()
        chk = check_device_coordination(up, dn, fault_current_A=2000)
        assert isinstance(chk, DeviceCoordinationCheck)

    def test_carries_device_ids(self):
        up, dn = self._build_upstream_downstream()
        chk = check_device_coordination(up, dn, 2000)
        assert chk.upstream_id == "R-MAIN"
        assert chk.downstream_id == "R-FEEDER"

    def test_passes_with_proper_margin(self):
        """TMS upstream 0.5 vs downstream 0.1 → Δt grande."""
        up, dn = self._build_upstream_downstream()
        chk = check_device_coordination(up, dn, 2000, relay_type="digital")
        assert chk.passes is True
        assert chk.actual_delta_t_s > chk.required_delta_t_s

    def test_fails_with_close_TMS(self):
        """TMS quase iguais → Δt insuficiente."""
        up = MultiFunctionRelay.relay_51_only(
            device_id="up",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=200, tms=0.15,
        )
        dn = MultiFunctionRelay.relay_51_only(
            device_id="dn",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=80, tms=0.1,
        )
        chk = check_device_coordination(up, dn, 2000, relay_type="digital")
        # Mesma curve type, TMS muito perto → margem pequena
        assert chk.passes is False

    def test_required_delta_t_by_relay_type(self):
        up, dn = self._build_upstream_downstream()
        # Digital tem margem 0.25, eletromecânico 0.40
        chk_dig = check_device_coordination(up, dn, 2000, "digital")
        chk_em = check_device_coordination(up, dn, 2000, "electromechanical")
        assert chk_dig.required_delta_t_s == pytest.approx(0.25)
        assert chk_em.required_delta_t_s == pytest.approx(0.40)

    def test_unknown_relay_type_falls_back_to_default(self):
        up, dn = self._build_upstream_downstream()
        chk = check_device_coordination(up, dn, 2000, "nonsense_type")
        assert chk.required_delta_t_s == pytest.approx(0.30)


# ---------------------------------------------------------------------------
# Triggered segment identification
# ---------------------------------------------------------------------------


class TestTriggeredSegmentInCoord:

    def test_triggered_segments_identified(self):
        """Numa coord 51+50 vs 51, mostra qual segment ditou
        o composite de cada lado."""
        up = MultiFunctionRelay.relay_51_and_50(
            device_id="up",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_51_A=200, tms_51=0.5,
            pickup_50_A=5000,  # alto, só pickup em fault grande
        )
        dn = MultiFunctionRelay.relay_51_only(
            device_id="dn",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=80, tms=0.1,
        )
        # 2000A: upstream 50 não pickup, só 51; dn só 51
        chk = check_device_coordination(up, dn, 2000)
        assert chk.triggered_upstream_segment_id == "51"
        assert chk.triggered_downstream_segment_id == "51"

    def test_triggered_INST_in_high_fault(self):
        """Em fault alto, upstream 50 INST domina."""
        up = MultiFunctionRelay.relay_51_and_50(
            device_id="up",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_51_A=200, tms_51=0.5,
            pickup_50_A=2000,
        )
        dn = MultiFunctionRelay.relay_51_only(
            device_id="dn",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=80, tms=0.1,
        )
        # 5000A: upstream 50 vence; dn só 51
        chk = check_device_coordination(up, dn, 5000)
        assert chk.triggered_upstream_segment_id == "50"
        assert chk.triggered_downstream_segment_id == "51"

    def test_triggered_none_below_pickups(self):
        """Em corrente abaixo dos pickups, triggered = '(none)'."""
        up = MultiFunctionRelay.relay_51_only(
            device_id="up",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=200, tms=0.5,
        )
        dn = MultiFunctionRelay.relay_51_only(
            device_id="dn",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=80, tms=0.1,
        )
        # 50A: ambos abaixo do pickup
        chk = check_device_coordination(up, dn, 50)
        assert chk.triggered_upstream_segment_id == "(none)"
        assert chk.triggered_downstream_segment_id == "(none)"
        assert chk.passes is False  # times = inf


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:

    def test_inf_composite_marks_fail(self):
        """Se algum lado retorna inf, passes=False."""
        up = MultiFunctionRelay.relay_51_only(
            device_id="up",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=10000,  # pickup muito alto, não dispara
            tms=0.5,
        )
        dn = MultiFunctionRelay.relay_51_only(
            device_id="dn",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=80, tms=0.1,
        )
        chk = check_device_coordination(up, dn, 1000)
        assert math.isinf(chk.upstream_composite_time_s)
        assert chk.passes is False

    def test_empty_upstream_fails(self):
        """Device vazio → composite=inf → fail."""
        up = TCCDevice(device_id="empty")
        dn = MultiFunctionRelay.relay_51_only(
            device_id="dn",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=80, tms=0.1,
        )
        chk = check_device_coordination(up, dn, 1000)
        assert chk.passes is False
        assert chk.triggered_upstream_segment_id == "(none)"


# ---------------------------------------------------------------------------
# Multi-point check
# ---------------------------------------------------------------------------


class TestMultiPoint:

    def test_returns_one_check_per_current(self):
        up = MultiFunctionRelay.relay_51_only(
            device_id="up",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=200, tms=0.5,
        )
        dn = MultiFunctionRelay.relay_51_only(
            device_id="dn",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=80, tms=0.1,
        )
        currents = [500, 1000, 2000, 5000]
        results = check_device_coordination_multi_point(
            up, dn, currents, relay_type="digital",
        )
        assert len(results) == 4
        for chk in results:
            assert isinstance(chk, DeviceCoordinationCheck)

    def test_multi_point_currents_recorded(self):
        up = MultiFunctionRelay.relay_51_only(
            device_id="up",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=200, tms=0.5,
        )
        dn = MultiFunctionRelay.relay_51_only(
            device_id="dn",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=80, tms=0.1,
        )
        currents = [500, 2000, 5000]
        results = check_device_coordination_multi_point(up, dn, currents)
        for chk, I in zip(results, currents):
            assert chk.fault_current_A == I


# ---------------------------------------------------------------------------
# Citation + metadata
# ---------------------------------------------------------------------------


class TestCitation:

    def test_citation_includes_buff_book(self):
        up = MultiFunctionRelay.relay_51_only(
            device_id="u", curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=100, tms=0.3,
        )
        dn = MultiFunctionRelay.relay_51_only(
            device_id="d", curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=80, tms=0.1,
        )
        chk = check_device_coordination(up, dn, 500)
        assert "IEEE Std 242" in chk.citation
        assert "§15.10.1" in chk.citation
