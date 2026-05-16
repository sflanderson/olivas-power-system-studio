"""
tests/test_pp_v1_6_0_dc_arc_flash.py — v1.6.0 Sprint C.

Cobre o módulo ``app.standards.dc_arc_flash`` (NFPA 70E:2024
§D.5 max-power method para sistemas DC).
"""

from __future__ import annotations

import math

import pytest


class TestDCArcFlashBasic:

    def test_module_loadable(self):
        from app.standards import dc_arc_flash  # noqa: F401

    def test_returns_result_dataclass(self):
        from app.standards.dc_arc_flash import (
            DCArcFlashResult, dc_arc_flash_max_power,
        )
        result = dc_arc_flash_max_power(
            V_system=125.0,
            I_short_circuit_A=2500.0,
            arc_clearing_time_s=0.5,
            working_distance_mm=457.0,
        )
        assert isinstance(result, DCArcFlashResult)
        assert result.incident_energy_cal_cm2 > 0
        assert math.isfinite(result.incident_energy_cal_cm2)

    def test_arc_voltage_is_half_system(self):
        """V_arc = V_sys / 2 (max power transfer theorem)."""
        from app.standards.dc_arc_flash import dc_arc_flash_max_power
        result = dc_arc_flash_max_power(
            V_system=125.0, I_short_circuit_A=2500.0,
            arc_clearing_time_s=0.5, working_distance_mm=457.0,
        )
        assert result.arc_voltage_V == pytest.approx(62.5)

    def test_arc_current_is_half_isc(self):
        from app.standards.dc_arc_flash import dc_arc_flash_max_power
        result = dc_arc_flash_max_power(
            V_system=125.0, I_short_circuit_A=2500.0,
            arc_clearing_time_s=0.5, working_distance_mm=457.0,
        )
        assert result.arc_current_A == pytest.approx(1250.0)


class TestDCArcFlashScaling:

    def test_higher_voltage_higher_energy(self):
        from app.standards.dc_arc_flash import dc_arc_flash_max_power
        E1 = dc_arc_flash_max_power(
            V_system=125.0, I_short_circuit_A=2500.0,
            arc_clearing_time_s=0.5, working_distance_mm=457.0,
        ).incident_energy_cal_cm2
        E2 = dc_arc_flash_max_power(
            V_system=600.0, I_short_circuit_A=2500.0,
            arc_clearing_time_s=0.5, working_distance_mm=457.0,
        ).incident_energy_cal_cm2
        assert E2 > E1

    def test_distance_squared_scaling(self):
        """E ∝ 1/D² (esférica)."""
        from app.standards.dc_arc_flash import dc_arc_flash_max_power
        E1 = dc_arc_flash_max_power(
            V_system=125.0, I_short_circuit_A=2500.0,
            arc_clearing_time_s=0.5, working_distance_mm=457.0,
        ).incident_energy_cal_cm2
        E2 = dc_arc_flash_max_power(
            V_system=125.0, I_short_circuit_A=2500.0,
            arc_clearing_time_s=0.5, working_distance_mm=914.0,
        ).incident_energy_cal_cm2
        # Distance ×2 → E /4 (esférica)
        ratio = E2 / E1
        assert 0.20 < ratio < 0.30

    def test_time_linear_scaling(self):
        from app.standards.dc_arc_flash import dc_arc_flash_max_power
        E1 = dc_arc_flash_max_power(
            V_system=125.0, I_short_circuit_A=2500.0,
            arc_clearing_time_s=0.25, working_distance_mm=457.0,
        ).incident_energy_cal_cm2
        E2 = dc_arc_flash_max_power(
            V_system=125.0, I_short_circuit_A=2500.0,
            arc_clearing_time_s=0.50, working_distance_mm=457.0,
        ).incident_energy_cal_cm2
        assert E2 == pytest.approx(2 * E1, rel=1e-9)


class TestDCArcFlashValidation:

    def test_negative_voltage_raises(self):
        from app.standards.dc_arc_flash import dc_arc_flash_max_power
        with pytest.raises(ValueError):
            dc_arc_flash_max_power(
                V_system=-125.0, I_short_circuit_A=2500.0,
                arc_clearing_time_s=0.5, working_distance_mm=457.0,
            )

    def test_negative_current_raises(self):
        from app.standards.dc_arc_flash import dc_arc_flash_max_power
        with pytest.raises(ValueError):
            dc_arc_flash_max_power(
                V_system=125.0, I_short_circuit_A=-1.0,
                arc_clearing_time_s=0.5, working_distance_mm=457.0,
            )

    def test_zero_distance_raises(self):
        from app.standards.dc_arc_flash import dc_arc_flash_max_power
        with pytest.raises(ValueError):
            dc_arc_flash_max_power(
                V_system=125.0, I_short_circuit_A=2500.0,
                arc_clearing_time_s=0.5, working_distance_mm=0.0,
            )
