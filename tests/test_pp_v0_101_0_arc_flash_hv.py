"""
tests/test_pp_v0_101_0_arc_flash_hv.py — v0.101.0:

Arc-flash HV/EHV (>15 kV) — EPRI 2011 + Terzija-Konglin.
"""

from __future__ import annotations

import math

import pytest

from app.standards.epri_arc_flash import (
    HVArcFlashResult,
    calculate_hv_arc_flash,
    epri_arc_flash_boundary_mm,
    epri_incident_energy,
    terzija_incident_energy,
)


# ---------------------------------------------------------------------------
# EPRI 2011
# ---------------------------------------------------------------------------


class TestEPRI2011:

    def test_typical_34kV_case(self):
        """34.5 kV, 15 kA, 0.5s, distância padrão."""
        E = epri_incident_energy(
            Ibf_kA=15.0,
            voltage_kV=34.5,
            clearing_time_s=0.5,
            working_distance_mm=914.0,
        )
        assert E > 0
        assert math.isfinite(E)

    def test_below_range_rejects(self):
        with pytest.raises(ValueError, match="15"):
            epri_incident_energy(
                Ibf_kA=10, voltage_kV=10, clearing_time_s=0.5,
            )

    def test_above_range_rejects(self):
        with pytest.raises(ValueError, match="46"):
            epri_incident_energy(
                Ibf_kA=10, voltage_kV=138, clearing_time_s=0.5,
            )

    def test_higher_current_higher_energy(self):
        E_low = epri_incident_energy(10, 30, 0.5, 914)
        E_high = epri_incident_energy(20, 30, 0.5, 914)
        assert E_high > E_low

    def test_longer_clearing_higher_energy(self):
        E_fast = epri_incident_energy(15, 30, 0.2, 914)
        E_slow = epri_incident_energy(15, 30, 0.8, 914)
        assert E_slow > E_fast

    def test_higher_voltage_higher_energy(self):
        """V^1.5 efeito."""
        E_15 = epri_incident_energy(15, 15.1, 0.5, 914)
        E_45 = epri_incident_energy(15, 45.0, 0.5, 914)
        assert E_45 > E_15

    def test_farther_distance_lower_energy(self):
        """E ∝ 1/D²."""
        E_close = epri_incident_energy(15, 30, 0.5, 600)
        E_far = epri_incident_energy(15, 30, 0.5, 1500)
        assert E_close > E_far

    def test_arc_flash_boundary_when_E_above_threshold(self):
        afb = epri_arc_flash_boundary_mm(
            incident_energy_cal_cm2=10.0,
            Ibf_kA=15, voltage_kV=30, clearing_time_s=0.5,
        )
        assert afb > 0

    def test_arc_flash_boundary_zero_when_below_threshold(self):
        afb = epri_arc_flash_boundary_mm(
            incident_energy_cal_cm2=0.5,   # < 1.2
            Ibf_kA=15, voltage_kV=30, clearing_time_s=0.5,
        )
        assert afb == 0.0


# ---------------------------------------------------------------------------
# Terzija-Konglin (>46 kV)
# ---------------------------------------------------------------------------


class TestTerzijaKonglin:

    def test_138kV_case(self):
        E = terzija_incident_energy(
            Ibf_kA=20.0,
            voltage_kV=138.0,
            clearing_time_s=0.3,
            working_distance_mm=1524.0,
        )
        assert E > 0
        assert math.isfinite(E)

    def test_below_46kV_rejects(self):
        with pytest.raises(ValueError, match="46"):
            terzija_incident_energy(
                Ibf_kA=10, voltage_kV=30, clearing_time_s=0.5,
            )

    def test_higher_voltage_higher_energy(self):
        E_138 = terzija_incident_energy(20, 138, 0.3, 1524)
        E_345 = terzija_incident_energy(20, 345, 0.3, 1524)
        assert E_345 > E_138

    def test_farther_distance_quadratic_decrease(self):
        """E ∝ 1/D²."""
        E_close = terzija_incident_energy(20, 138, 0.3, 1000)
        E_far = terzija_incident_energy(20, 138, 0.3, 2000)
        # Aproximadamente 4x menor
        assert abs(E_close / E_far - 4.0) < 0.5


# ---------------------------------------------------------------------------
# calculate_hv_arc_flash (auto-select)
# ---------------------------------------------------------------------------


class TestCalculateHVArcFlash:

    def test_below_15kV_rejects(self):
        with pytest.raises(ValueError):
            calculate_hv_arc_flash(15, 13.8, 0.5)

    def test_15_to_46_uses_epri(self):
        r = calculate_hv_arc_flash(15, 34.5, 0.5)
        assert r.method_used == "EPRI_2011"
        assert "EPRI" in r.citation

    def test_above_46_uses_terzija(self):
        r = calculate_hv_arc_flash(20, 138, 0.3)
        assert r.method_used == "TERZIJA_KONGLIN"
        assert "Terzija" in r.citation

    def test_returns_hv_result_dataclass(self):
        r = calculate_hv_arc_flash(15, 34.5, 0.5)
        assert isinstance(r, HVArcFlashResult)
        assert r.incident_energy_cal_cm2 > 0
        assert r.arc_flash_boundary_mm >= 0


# ---------------------------------------------------------------------------
# Integration with main arc_flash module
# ---------------------------------------------------------------------------


class TestIntegrationGap:

    def test_lv_uses_nbr_or_ieee(self):
        """≤15 kV ainda usa NBR 17227 / IEEE 1584."""
        # Simply checks separate module exists
        from app.postprocessor import arc_flash
        assert hasattr(arc_flash, "calculate_arc_flash")

    def test_full_voltage_coverage_now(self):
        """Cobertura completa: LV (NBR 17227) + MV (EPRI) + HV (TK)."""
        # LV: covered by app.postprocessor.arc_flash
        # MV (15-46 kV): EPRI
        E_mv = epri_incident_energy(15, 34.5, 0.5)
        assert E_mv > 0
        # EHV (>46 kV): Terzija
        E_ehv = terzija_incident_energy(20, 138, 0.3)
        assert E_ehv > 0
