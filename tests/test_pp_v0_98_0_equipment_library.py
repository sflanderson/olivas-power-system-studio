"""
tests/test_pp_v0_98_0_equipment_library.py — v0.98.0:

Biblioteca de equipamentos curados (vendor data).

Cobertura:

* Stats da biblioteca (15+ relés, 8+ motores, 5+ TR, 5+ disjuntores)
* Lookup por model_id
* Filtros: por aplicação, voltage_class, vendor, IEC 61850
* Lista vendors únicos
* Dataclasses: RelayModel/MotorModel/TransformerModel/BreakerModel
* Validações: ANSI devices como string, curves IEC/ANSI
"""

from __future__ import annotations

import pytest

from app.equipment import library
from app.equipment.library import (
    BreakerModel, MotorModel, RelayApplication, RelayModel,
    TransformerModel, VoltageClass,
)


# ---------------------------------------------------------------------------
# Library stats
# ---------------------------------------------------------------------------


class TestLibraryStats:

    def test_total_entries(self):
        s = library.stats()
        assert s["total"] >= 30

    def test_at_least_15_relays(self):
        assert library.stats()["relays"] >= 15

    def test_at_least_8_motors(self):
        assert library.stats()["motors"] >= 8

    def test_at_least_5_transformers(self):
        assert library.stats()["transformers"] >= 5

    def test_at_least_5_breakers(self):
        assert library.stats()["breakers"] >= 5

    def test_5_vendors(self):
        vendors = library.list_vendors()
        assert "SEL" in vendors
        assert "ABB" in vendors
        assert "Siemens" in vendors
        assert "WEG" in vendors
        assert "GE" in vendors


# ---------------------------------------------------------------------------
# Relay lookup
# ---------------------------------------------------------------------------


class TestRelayLookup:

    def test_get_sel_751(self):
        r = library.get_relay("SEL-751")
        assert r is not None
        assert r.manufacturer == "SEL"
        assert "Feeder" in r.full_name
        assert "50" in r.ansi_devices
        assert "51" in r.ansi_devices
        assert r.iec_61850 is True

    def test_get_case_insensitive(self):
        r1 = library.get_relay("sel-751")
        r2 = library.get_relay("SEL-751")
        assert r1 is r2

    def test_get_unknown_returns_none(self):
        assert library.get_relay("UNKNOWN-999") is None

    def test_filter_by_application(self):
        feeder_relays = library.list_relays(
            application=RelayApplication.FEEDER,
        )
        assert len(feeder_relays) >= 5
        for r in feeder_relays:
            assert r.application == RelayApplication.FEEDER

    def test_filter_by_voltage_class(self):
        mv_relays = library.list_relays(
            voltage_class=VoltageClass.MV,
        )
        assert len(mv_relays) > 0
        for r in mv_relays:
            assert r.voltage_class == VoltageClass.MV

    def test_filter_by_vendor(self):
        abb = library.list_relays(vendor="ABB")
        assert len(abb) >= 3
        for r in abb:
            assert r.manufacturer == "ABB"

    def test_filter_iec_61850_only(self):
        modern = library.list_relays(iec_61850_only=True)
        assert len(modern) > 0
        for r in modern:
            assert r.iec_61850 is True

    def test_combined_filters(self):
        sel_feeder_mv = library.list_relays(
            vendor="SEL",
            application=RelayApplication.FEEDER,
            voltage_class=VoltageClass.MV,
        )
        assert "SEL-751" in [r.model_id for r in sel_feeder_mv]


# ---------------------------------------------------------------------------
# Relay properties
# ---------------------------------------------------------------------------


class TestRelayProperties:

    def test_supports_iec(self):
        r = library.get_relay("SEL-751")
        assert r.supports_iec is True

    def test_supports_ansi(self):
        r = library.get_relay("SEL-751")
        assert r.supports_ansi is True

    def test_pickup_range_valid(self):
        r = library.get_relay("SEL-751")
        assert r.pickup_range_A[0] < r.pickup_range_A[1]


# ---------------------------------------------------------------------------
# Motor lookup
# ---------------------------------------------------------------------------


class TestMotorLookup:

    def test_get_weg_w22(self):
        m = library.get_motor("WEG-W22-100kW-380V")
        assert m is not None
        assert m.manufacturer == "WEG"
        assert m.rated_power_kW == 100.0

    def test_filter_by_min_kW(self):
        large = library.list_motors(min_kW=1000)
        assert len(large) > 0
        for m in large:
            assert m.rated_power_kW >= 1000

    def test_filter_by_voltage_with_tolerance(self):
        """voltage_V usa tolerância 5%."""
        motors = library.list_motors(voltage_V=380.0)
        # 380V e 400V (5% diff) entram
        assert len(motors) >= 1


# ---------------------------------------------------------------------------
# Transformer lookup
# ---------------------------------------------------------------------------


class TestTransformerLookup:

    def test_get_weg_distribution(self):
        t = library.get_transformer("WEG-Dist-300kVA-13800-380")
        assert t is not None
        assert t.rated_S_kVA == 300.0
        assert t.primary_kV == 13.8

    def test_filter_min_kVA(self):
        big = library.list_transformers(min_kVA=5000)
        assert len(big) >= 1


# ---------------------------------------------------------------------------
# Breaker lookup
# ---------------------------------------------------------------------------


class TestBreakerLookup:

    def test_get_abb_hd4(self):
        b = library.get_breaker("ABB-HD4-12kV-1250A")
        assert b is not None
        assert b.arc_quenching == "vacuum"

    def test_filter_voltage_class(self):
        hv = library.list_breakers(voltage_class=VoltageClass.HV)
        for b in hv:
            assert b.voltage_class == VoltageClass.HV

    def test_filter_min_breaking_kA(self):
        heavy = library.list_breakers(min_kA=50)
        for b in heavy:
            assert b.breaking_capacity_kA >= 50


# ---------------------------------------------------------------------------
# Dataclass invariants
# ---------------------------------------------------------------------------


class TestDataclassInvariants:

    def test_all_relays_have_ansi_devices_as_strings(self):
        for r in library.list_relays():
            for dev in r.ansi_devices:
                assert isinstance(dev, str), (
                    f"Relé {r.model_id} tem ANSI device "
                    f"não-str: {dev}"
                )

    def test_all_motors_have_positive_power(self):
        for m in library.list_motors():
            assert m.rated_power_kW > 0
            assert m.rated_voltage_V > 0
            assert m.rated_current_A > 0

    def test_all_transformers_consistent(self):
        for t in library.list_transformers():
            assert t.rated_S_kVA > 0
            assert t.primary_kV > 0
            assert t.secondary_kV > 0
            assert 0 < t.impedance_pct < 30
