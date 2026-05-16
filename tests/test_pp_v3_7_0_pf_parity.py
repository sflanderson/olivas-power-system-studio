"""v3.7.0 — Categoria B Algorithm refinements (B.2 + B.3) tests.

Closes SKIPPED_BACKLOG B.2 (bus_role explicit SLACK/PV/PQ) + B.3
(q_factor com n_per_unit_per_second integrado em calculate_short_circuit).

Reference:
* IEEE 399 §5 — Power flow bus types
* IEC 60909-0:2016 §4.6.2 Tab 3 — Asynchronous motor decay (n parameter)
* PTW Tutorial §Part 2 p.63 (B.2) + §Part 5 p.136-137 (B.3)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import pytest


# ---------------------------------------------------------------------------
# B.2 — bus_role helpers
# ---------------------------------------------------------------------------


@dataclass
class _StubProperty:
    name: str
    value: str


@dataclass
class _StubBusComponent:
    name: str
    type: str = "BUS"
    x: int = 0
    y: int = 0
    properties: list = field(default_factory=list)


class TestBusRoleHelpers:
    """v3.7.0 B.2 closure — bus_role property reading."""

    def test_read_bus_role_default_auto(self) -> None:
        from app.gui.analysis_dialogs import _read_bus_role
        bus = _StubBusComponent(name="B1")
        assert _read_bus_role(bus) == "auto"

    def test_read_bus_role_explicit_slack(self) -> None:
        from app.gui.analysis_dialogs import _read_bus_role
        bus = _StubBusComponent(
            name="B1",
            properties=[_StubProperty("bus_role", "slack")],
        )
        assert _read_bus_role(bus) == "slack"

    def test_read_bus_role_explicit_pv(self) -> None:
        from app.gui.analysis_dialogs import _read_bus_role
        bus = _StubBusComponent(
            name="B1",
            properties=[_StubProperty("bus_role", "PV")],  # uppercase
        )
        assert _read_bus_role(bus) == "pv"

    def test_read_bus_role_invalid_falls_back(self) -> None:
        from app.gui.analysis_dialogs import _read_bus_role
        bus = _StubBusComponent(
            name="B1",
            properties=[_StubProperty("bus_role", "garbage")],
        )
        assert _read_bus_role(bus) == "auto"

    def test_find_explicit_slack_returns_marked(self) -> None:
        from app.gui.analysis_dialogs import _find_explicit_slack
        b1 = _StubBusComponent(name="B1")
        b2 = _StubBusComponent(
            name="B2",
            properties=[_StubProperty("bus_role", "slack")],
        )
        b3 = _StubBusComponent(name="B3")
        slack = _find_explicit_slack([b1, b2, b3])
        assert slack is b2

    def test_find_explicit_slack_returns_none_when_no_marks(self) -> None:
        from app.gui.analysis_dialogs import _find_explicit_slack
        bs = [_StubBusComponent(name=f"B{i}") for i in range(3)]
        assert _find_explicit_slack(bs) is None


class TestBuildPfWithExplicitSlack:
    """v3.7.0 B.2 — build_pf_system_from_project respeita bus_role."""

    def test_first_bus_is_slack_when_no_role(self) -> None:
        """Legacy v3.3.1 behavior preserved when bus_role absent."""
        from app.gui.analysis_dialogs import build_pf_system_from_project

        @dataclass
        class _StubProject:
            components: list = field(default_factory=list)

        proj = _StubProject(components=[
            _StubBusComponent(name="B1"),
            _StubBusComponent(name="B2"),
        ])
        sys = build_pf_system_from_project(proj)
        assert sys is not None
        # First bus should be the slack
        slack_bus = sys.buses[0]
        assert slack_bus.id == "B1"

    def test_explicit_slack_overrides_first(self) -> None:
        """v3.7.0 B.2 — bus_role: slack wins over position."""
        from app.gui.analysis_dialogs import build_pf_system_from_project

        @dataclass
        class _StubProject:
            components: list = field(default_factory=list)

        proj = _StubProject(components=[
            _StubBusComponent(name="B1"),
            _StubBusComponent(
                name="B2",
                properties=[_StubProperty("bus_role", "slack")],
            ),
            _StubBusComponent(name="B3"),
        ])
        sys = build_pf_system_from_project(proj)
        assert sys is not None
        # B2 should be the slack (not B1)
        slack_bus = sys.buses[0]
        assert slack_bus.id == "B2"


# ---------------------------------------------------------------------------
# B.3 — q_factor with n_per_unit_per_second
# ---------------------------------------------------------------------------


class TestQFactorWithN:
    """v3.7.0 B.3 closure — q_factor uses n_per_unit_per_second."""

    def test_default_n_matches_legacy_behavior(self) -> None:
        """n=0.10 default → same q values as v3.6.x."""
        from app.standards.iec60909_decay import q_factor
        # t = 50ms with default n=0.10 → effective_t = 50ms
        q_default = q_factor(0.050)
        assert 0.79 <= q_default <= 1.0
        # Should match interpolation: log_t between log(0.005) and log(0.250)
        # alpha = (log(0.05) - log(0.005)) / (log(0.25) - log(0.005)) ≈ 0.589
        # q ≈ 1.0 + (-0.21) × 0.589 ≈ 0.876
        assert math.isclose(q_default, 0.876, abs_tol=0.01)

    def test_lower_n_means_higher_q(self) -> None:
        """4-pole motor (n=0.05) decays slower → higher q for same t."""
        from app.standards.iec60909_decay import q_factor
        q_2pole = q_factor(0.050, n_per_unit_per_second=0.10)
        q_4pole = q_factor(0.050, n_per_unit_per_second=0.05)
        assert q_4pole > q_2pole

    def test_higher_n_means_lower_q(self) -> None:
        """Hypothetical higher n → faster decay → lower q."""
        from app.standards.iec60909_decay import q_factor
        q_default = q_factor(0.050, n_per_unit_per_second=0.10)
        q_high = q_factor(0.050, n_per_unit_per_second=0.20)
        assert q_high < q_default

    def test_n_zero_raises(self) -> None:
        from app.standards.iec60909_decay import q_factor
        with pytest.raises(ValueError, match="n_per_unit"):
            q_factor(0.05, n_per_unit_per_second=0.0)

    def test_n_negative_raises(self) -> None:
        from app.standards.iec60909_decay import q_factor
        with pytest.raises(ValueError, match="n_per_unit"):
            q_factor(0.05, n_per_unit_per_second=-0.05)

    def test_high_pole_motor_at_long_clearing_time(self) -> None:
        """6-pole motor (n=0.02) at 100ms → effective_t = 20ms (small).
        q should be high because effective_t is in the low end."""
        from app.standards.iec60909_decay import q_factor
        q = q_factor(0.100, n_per_unit_per_second=0.02)
        # effective_t = 0.020s. q ≈ 1.0 + (-0.21) × alpha
        # alpha = (log(0.020) - log(0.005)) / (log(0.250) - log(0.005))
        # alpha ≈ 1.386 / 3.912 ≈ 0.354
        # q ≈ 1.0 - 0.21 × 0.354 ≈ 0.926
        assert math.isclose(q, 0.926, abs_tol=0.02)

    def test_subcycle_returns_unity(self) -> None:
        from app.standards.iec60909_decay import q_factor
        # t=2ms, default n: effective_t = 2ms → < 5ms → q=1.0
        assert q_factor(0.002) == 1.0


class TestCalculateScWithMotorGradient:
    """v3.7.0 B.3 — calculate_short_circuit accepts motor_speed_gradient."""

    def test_default_gradient_is_010(self) -> None:
        """Default = 2-pole motor (n=0.10), backward-compatible."""
        from app.standards.iec60909 import calculate_short_circuit
        # Sanity: function accepts the kwarg with default
        # Use FAR_FROM_GENERATOR (no near-gen logic triggers)
        result = calculate_short_circuit(
            rated_voltage_kV=13.8,
            z_thevenin_ohm=complex(0.5, 2.0),
        )
        # Just confirm it returns ShortCircuitResult
        assert hasattr(result, "Ik_pp_kA")
        assert result.Ik_pp_kA > 0

    def test_motor_gradient_explicit_param_works(self) -> None:
        """Async motor near-gen with explicit gradient."""
        from app.standards.iec60909 import (
            FaultDistance,
            calculate_short_circuit,
        )
        result = calculate_short_circuit(
            rated_voltage_kV=0.480,
            z_thevenin_ohm=complex(0.05, 0.20),
            fault_distance=FaultDistance.NEAR_TO_GENERATOR,
            breaker_min_delay_s=0.080,
            generator_x_d_subtransient_pu=0.20,
            is_synchronous_motor=False,  # async motor case
            motor_speed_gradient_pu_per_s=0.05,  # 4-pole
        )
        # Compare with synchronous (no q decay)
        result_sync = calculate_short_circuit(
            rated_voltage_kV=0.480,
            z_thevenin_ohm=complex(0.05, 0.20),
            fault_distance=FaultDistance.NEAR_TO_GENERATOR,
            breaker_min_delay_s=0.080,
            generator_x_d_subtransient_pu=0.20,
            is_synchronous_motor=True,
        )
        # Async should have lower steady-state (q < 1.0)
        assert result.Ik_steady_kA < result_sync.Ik_steady_kA

    def test_async_motor_4pole_higher_steady_than_2pole(self) -> None:
        """4-pole motor decays slower → higher Ik_steady than 2-pole."""
        from app.standards.iec60909 import (
            FaultDistance,
            calculate_short_circuit,
        )
        common = dict(
            rated_voltage_kV=0.480,
            z_thevenin_ohm=complex(0.05, 0.20),
            fault_distance=FaultDistance.NEAR_TO_GENERATOR,
            breaker_min_delay_s=0.080,
            generator_x_d_subtransient_pu=0.20,
            is_synchronous_motor=False,
        )
        r_2pole = calculate_short_circuit(
            **common, motor_speed_gradient_pu_per_s=0.10
        )
        r_4pole = calculate_short_circuit(
            **common, motor_speed_gradient_pu_per_s=0.05
        )
        assert r_4pole.Ik_steady_kA > r_2pole.Ik_steady_kA


# ---------------------------------------------------------------------------
# Acessibilidade GUI (Master Protocol garantia 7ª)
# ---------------------------------------------------------------------------


def test_bus_ocomp_has_bus_role_property() -> None:
    """BUS.ocomp schema declares bus_role property (v3.7.0)."""
    from pathlib import Path
    bus_ocomp = (
        Path(__file__).parent.parent / "app" / "preprocessor"
        / "catalog_specs" / "BUS.ocomp"
    )
    text = bus_ocomp.read_text(encoding="utf-8")
    assert "name: bus_role" in text
    assert "auto" in text and "slack" in text and "pv" in text and "pq" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
