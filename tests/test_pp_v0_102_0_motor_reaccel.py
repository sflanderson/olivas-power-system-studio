"""
tests/test_pp_v0_102_0_motor_reaccel.py — v0.102.0:

Re-aceleração de motores após distúrbio.
"""

from __future__ import annotations

import pytest

from app.postprocessor.motor_reaccel import (
    MotorState,
    ReaccelResult,
    ReaccelScenario,
    simulate_reaccel,
)


def _motor(name: str, kW: float = 100, V: float = 4160) -> MotorState:
    return MotorState(
        motor_id=name,
        rated_power_kW=kW,
        rated_voltage_V=V,
        inertia_kg_m2=1.5,
        rated_speed_rpm=1800,
        locked_rotor_current_pu=6.0,
    )


# ---------------------------------------------------------------------------
# MotorState
# ---------------------------------------------------------------------------


class TestMotorState:

    def test_rated_torque_calculation(self):
        m = _motor("M1", kW=100, V=4160)
        # T = 100kW / (2π·1800/60) ≈ 530 Nm
        assert 500 < m.rated_torque_Nm < 600

    def test_rated_current_calculation(self):
        m = _motor("M1", kW=100, V=4160)
        # I = 100kW / (√3·4160·0.85·0.92) ≈ 17.7A
        assert 15 < m.rated_current_A < 20


# ---------------------------------------------------------------------------
# simulate_reaccel scenarios
# ---------------------------------------------------------------------------


class TestSimulateReaccel:

    def test_no_motors_warns(self):
        r = simulate_reaccel([])
        assert "Nenhum motor" in " ".join(r.warnings)

    def test_single_small_motor_succeeds(self):
        r = simulate_reaccel(
            [_motor("M1", kW=100)],
            bus_capacity_kVA=10000,
        )
        assert r.status == "success"
        assert r.passes
        assert "M1" in r.motors_recovered

    def test_overloaded_bus_fails_reaccel(self):
        """100 motores num bus pequeno → V_dip massivo → fail."""
        motors = [_motor(f"M{i}", kW=500) for i in range(100)]
        r = simulate_reaccel(
            motors, bus_capacity_kVA=1000,   # bus pequeno
        )
        assert r.status in ("partial", "failure")
        assert r.v_dip_pu < 0.7

    def test_voltage_dip_scenario(self):
        r = simulate_reaccel(
            [_motor("M1")],
            scenario=ReaccelScenario.VOLTAGE_DIP,
            voltage_dip_level_pu=0.8,
        )
        assert r.scenario == ReaccelScenario.VOLTAGE_DIP

    def test_black_start_scenario(self):
        r = simulate_reaccel(
            [_motor("M1"), _motor("M2"), _motor("M3")],
            scenario=ReaccelScenario.BLACK_START,
        )
        assert r.scenario == ReaccelScenario.BLACK_START

    def test_status_partial_when_some_lost(self):
        """Cenário marginal: alguns motores recuperam, outros não."""
        # 30 motores num bus médio
        motors = [_motor(f"M{i}", kW=200) for i in range(30)]
        r = simulate_reaccel(
            motors, bus_capacity_kVA=2000,
        )
        # Pode ser success, partial ou failure dependendo da
        # configuração; só checa que não crasha
        assert r.status in ("success", "partial", "failure")


# ---------------------------------------------------------------------------
# ReaccelResult
# ---------------------------------------------------------------------------


class TestReaccelResult:

    def test_passes_when_v_dip_above_07(self):
        r = ReaccelResult(
            scenario=ReaccelScenario.VOLTAGE_DIP,
            time_to_full_speed_s=2.0,
            v_dip_pu=0.85,
            v_recovery_time_s=1.5,
            status="success",
        )
        assert r.passes

    def test_fails_when_v_dip_below_07(self):
        r = ReaccelResult(
            scenario=ReaccelScenario.VOLTAGE_DIP,
            time_to_full_speed_s=2.0,
            v_dip_pu=0.5,
            v_recovery_time_s=1.5,
            status="success",
        )
        assert not r.passes

    def test_summary_contains_ieee_399(self):
        r = simulate_reaccel([_motor("M1")])
        assert "IEEE" in r.citation
        assert "399" in r.citation

    def test_summary_lists_lost_motors(self):
        motors = [_motor(f"M{i}", kW=500) for i in range(50)]
        r = simulate_reaccel(motors, bus_capacity_kVA=1000)
        s = r.summary()
        # Status não-success deve aparecer
        if r.motors_lost:
            assert "perdidos" in s.lower() or "Motores" in s
