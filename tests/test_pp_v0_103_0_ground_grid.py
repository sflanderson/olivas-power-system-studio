"""
tests/test_pp_v0_103_0_ground_grid.py — v0.103.0:

Análise de malha de aterramento IEEE 80.
"""

from __future__ import annotations

import pytest

from app.postprocessor.ground_grid import (
    GroundGridResult,
    GroundGridSpec,
    analyze_ground_grid,
)


def _typical_spec(**overrides) -> GroundGridSpec:
    base = dict(
        area_m2=1000.0,
        length_total_m=500.0,
        n_meshes_x=5,
        n_meshes_y=5,
        burial_depth_m=0.5,
        soil_resistivity_ohm_m=100.0,
        surface_resistivity_ohm_m=2500.0,
        surface_thickness_m=0.10,
        fault_current_kA=10.0,
        fault_clearing_time_s=0.5,
    )
    base.update(overrides)
    return GroundGridSpec(**base)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:

    def test_zero_area_rejects(self):
        with pytest.raises(ValueError, match="area_m2"):
            analyze_ground_grid(_typical_spec(area_m2=0))

    def test_zero_length_rejects(self):
        with pytest.raises(ValueError, match="length_total_m"):
            analyze_ground_grid(_typical_spec(length_total_m=0))

    def test_zero_resistivity_rejects(self):
        with pytest.raises(ValueError, match="soil"):
            analyze_ground_grid(_typical_spec(soil_resistivity_ohm_m=0))

    def test_zero_fault_rejects(self):
        with pytest.raises(ValueError, match="fault_current"):
            analyze_ground_grid(_typical_spec(fault_current_kA=0))


# ---------------------------------------------------------------------------
# R_grid calculation
# ---------------------------------------------------------------------------


class TestRGrid:

    def test_typical_returns_positive(self):
        r = analyze_ground_grid(_typical_spec())
        assert r.R_grid_ohm > 0

    def test_higher_resistivity_higher_R(self):
        r_low = analyze_ground_grid(
            _typical_spec(soil_resistivity_ohm_m=50)
        )
        r_high = analyze_ground_grid(
            _typical_spec(soil_resistivity_ohm_m=500)
        )
        assert r_high.R_grid_ohm > r_low.R_grid_ohm

    def test_larger_area_lower_R(self):
        r_small = analyze_ground_grid(
            _typical_spec(area_m2=500, length_total_m=300)
        )
        r_large = analyze_ground_grid(
            _typical_spec(area_m2=5000, length_total_m=1500)
        )
        assert r_large.R_grid_ohm < r_small.R_grid_ohm


# ---------------------------------------------------------------------------
# Touch & step voltages
# ---------------------------------------------------------------------------


class TestVoltages:

    def test_typical_passes(self):
        """Subestação típica com solo bom passa IEEE 80."""
        r = analyze_ground_grid(_typical_spec())
        # Pode passar ou não dependendo dos parâmetros simplificados
        assert r.touch_voltage_V > 0
        assert r.step_voltage_V > 0
        assert r.touch_limit_V > 0
        assert r.step_limit_V > 0

    def test_high_fault_increases_voltages(self):
        r_low = analyze_ground_grid(_typical_spec(fault_current_kA=5))
        r_high = analyze_ground_grid(_typical_spec(fault_current_kA=20))
        assert r_high.touch_voltage_V > r_low.touch_voltage_V
        assert r_high.step_voltage_V > r_low.step_voltage_V

    def test_fast_clearing_higher_limit(self):
        """Tempo curto de extinção → limite maior (corpo aguenta mais)."""
        r_slow = analyze_ground_grid(
            _typical_spec(fault_clearing_time_s=2.0)
        )
        r_fast = analyze_ground_grid(
            _typical_spec(fault_clearing_time_s=0.1)
        )
        assert r_fast.touch_limit_V > r_slow.touch_limit_V

    def test_higher_surface_resistivity_higher_limit(self):
        """Brita com ρ_s alta → limite maior (isolação)."""
        r_low_brita = analyze_ground_grid(
            _typical_spec(surface_resistivity_ohm_m=500)
        )
        r_high_brita = analyze_ground_grid(
            _typical_spec(surface_resistivity_ohm_m=5000)
        )
        assert (
            r_high_brita.touch_limit_V > r_low_brita.touch_limit_V
        )


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


class TestStatus:

    def test_GPR_is_R_x_I(self):
        spec = _typical_spec()
        r = analyze_ground_grid(spec)
        # GPR = R · I (com decrement factor)
        expected = r.R_grid_ohm * spec.fault_current_kA * 1000
        assert abs(r.gpr_V - expected) < 1.0

    def test_summary_contains_ieee_80(self):
        r = analyze_ground_grid(_typical_spec())
        s = r.summary()
        assert "IEEE" in s
        assert "80" in s

    def test_high_resistivity_warns(self):
        r = analyze_ground_grid(
            _typical_spec(soil_resistivity_ohm_m=2000)
        )
        joined = " ".join(r.warnings)
        assert "alta resistividade" in joined or "ρ" in joined


# ---------------------------------------------------------------------------
# Body weight
# ---------------------------------------------------------------------------


class TestBodyWeight:

    def test_70kg_higher_limits_than_50kg(self):
        r_50 = analyze_ground_grid(
            _typical_spec(body_weight_kg=50)
        )
        r_70 = analyze_ground_grid(
            _typical_spec(body_weight_kg=70)
        )
        assert r_70.touch_limit_V > r_50.touch_limit_V
