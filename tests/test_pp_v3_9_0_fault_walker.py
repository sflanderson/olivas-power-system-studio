"""v3.9.0 — B.4 Fault distance walker tests (closes SKIPPED_BACKLOG B.4).

Reference:
* IEC 60909-0:2016 §3.7 (near/far classification)
* PTW Tutorial §Part 5 p.136-137
* IEEE 141 §4.5
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.postprocessor.fault_distance_walker import (
    DEFAULT_BREAKER_MIN_DELAY_S,
    DEFAULT_UTILITY_XD_PU,
    DEFAULT_X_D_SUBTRANSIENT_PU,
    auto_classify_fault_distance,
    find_nearby_sources,
)
from app.standards.iec60909 import FaultDistance


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


@dataclass
class _StubProperty:
    name: str
    value: str


@dataclass
class _StubComponent:
    name: str = "X"
    type: str = "BUS"
    x: int = 0
    y: int = 0
    properties: list = field(default_factory=list)


@dataclass
class _StubProject:
    components: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# find_nearby_sources
# ---------------------------------------------------------------------------


class TestFindNearbySources:
    def test_no_components_returns_empty(self) -> None:
        proj = _StubProject()
        result = find_nearby_sources(proj, "B1")
        assert result == []

    def test_no_fault_bus_returns_empty(self) -> None:
        proj = _StubProject(components=[
            _StubComponent(name="X", type="MOTOR"),
        ])
        result = find_nearby_sources(proj, "NONEXISTENT")
        assert result == []

    def test_finds_sync_motor_within_hops(self) -> None:
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0),
            _StubComponent(
                name="M1", type="MOTOR", x=200, y=0,
                properties=[_StubProperty("motor_type", "synchronous")],
            ),
        ])
        result = find_nearby_sources(proj, "B1", max_hops=2)
        assert len(result) == 1
        comp, src_type, hops = result[0]
        assert comp.name == "M1"
        assert src_type == "synchronous_motor"
        assert hops == 1  # 200 px / 300 px = 1 hop ceil

    def test_finds_utility(self) -> None:
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0),
            _StubComponent(name="U1", type="UTIL", x=100, y=0),
        ])
        result = find_nearby_sources(proj, "B1")
        assert len(result) == 1
        assert result[0][1] == "utility"

    def test_excludes_far_components(self) -> None:
        """Component beyond max_hops × 300px is excluded."""
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0),
            _StubComponent(
                name="MFar", type="MOTOR", x=2000, y=0,
                properties=[_StubProperty("motor_type", "synchronous")],
            ),
        ])
        # max_hops=2 → max_distance=600 px; 2000 > 600 → excluded
        result = find_nearby_sources(proj, "B1", max_hops=2)
        assert result == []

    def test_classifies_induction_motor_separately(self) -> None:
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0),
            _StubComponent(
                name="M1", type="MOTOR", x=100, y=0,
                properties=[_StubProperty("motor_type", "induction")],
            ),
        ])
        result = find_nearby_sources(proj, "B1")
        assert result[0][1] == "induction_motor"

    def test_default_motor_type_is_induction(self) -> None:
        """No motor_type prop → defaults to induction (heurística conservadora)."""
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0),
            _StubComponent(name="M1", type="MOTOR", x=100, y=0),
        ])
        result = find_nearby_sources(proj, "B1")
        assert result[0][1] == "induction_motor"


# ---------------------------------------------------------------------------
# auto_classify_fault_distance
# ---------------------------------------------------------------------------


class TestAutoClassify:
    def test_no_sources_returns_far(self) -> None:
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS"),
        ])
        result = auto_classify_fault_distance(proj, "B1")
        assert result.fault_distance == FaultDistance.FAR_FROM_GENERATOR
        assert result.is_synchronous_motor is False
        assert result.suggested_x_d_subtransient_pu == DEFAULT_UTILITY_XD_PU
        assert "Nenhuma fonte" in result.notes

    def test_utility_only_returns_far(self) -> None:
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0),
            _StubComponent(name="U1", type="UTIL", x=100, y=0),
        ])
        result = auto_classify_fault_distance(proj, "B1")
        assert result.fault_distance == FaultDistance.FAR_FROM_GENERATOR

    def test_synchronous_motor_returns_near(self) -> None:
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0),
            _StubComponent(
                name="M1", type="MOTOR", x=200, y=0,
                properties=[
                    _StubProperty("motor_type", "synchronous"),
                    _StubProperty("n_poles", "4"),
                ],
            ),
        ])
        result = auto_classify_fault_distance(proj, "B1")
        assert result.fault_distance == FaultDistance.NEAR_TO_GENERATOR
        assert result.is_synchronous_motor is True
        assert result.suggested_x_d_subtransient_pu == DEFAULT_X_D_SUBTRANSIENT_PU
        # 4-pole → n=0.05
        assert result.motor_speed_gradient_pu_per_s == 0.05

    def test_2pole_sync_motor_yields_n_010(self) -> None:
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0),
            _StubComponent(
                name="M1", type="MOTOR", x=100, y=0,
                properties=[
                    _StubProperty("motor_type", "synchronous"),
                    _StubProperty("n_poles", "2"),
                ],
            ),
        ])
        result = auto_classify_fault_distance(proj, "B1")
        assert result.motor_speed_gradient_pu_per_s == 0.10

    def test_8pole_sync_motor_yields_n_002(self) -> None:
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0),
            _StubComponent(
                name="M1", type="MOTOR", x=100, y=0,
                properties=[
                    _StubProperty("motor_type", "synchronous"),
                    _StubProperty("n_poles", "8"),
                ],
            ),
        ])
        result = auto_classify_fault_distance(proj, "B1")
        assert result.motor_speed_gradient_pu_per_s == 0.02

    def test_breaker_default_50ms(self) -> None:
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS"),
        ])
        result = auto_classify_fault_distance(proj, "B1")
        assert result.suggested_breaker_min_delay_s == DEFAULT_BREAKER_MIN_DELAY_S
        assert result.suggested_breaker_min_delay_s == 0.050

    def test_nearby_sources_listed(self) -> None:
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0),
            _StubComponent(name="U1", type="UTIL", x=100, y=0),
            _StubComponent(name="U2", type="UTIL", x=200, y=0),
        ])
        result = auto_classify_fault_distance(proj, "B1")
        assert len(result.nearby_sources) == 2
        names = [n for n, _ in result.nearby_sources]
        assert "U1" in names and "U2" in names

    def test_max_hops_param_works(self) -> None:
        """Bigger max_hops finds farther components."""
        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0),
            _StubComponent(
                name="M1", type="MOTOR", x=900, y=0,
                properties=[_StubProperty("motor_type", "synchronous")],
            ),
        ])
        # 900 px / 300 px = 3 hops
        r1 = auto_classify_fault_distance(proj, "B1", max_hops=2)
        assert r1.fault_distance == FaultDistance.FAR_FROM_GENERATOR

        r2 = auto_classify_fault_distance(proj, "B1", max_hops=4)
        assert r2.fault_distance == FaultDistance.NEAR_TO_GENERATOR


# ---------------------------------------------------------------------------
# Integration: feed FaultClassification → calculate_short_circuit
# ---------------------------------------------------------------------------


class TestIntegrationWithCalculateSc:
    def test_classification_feeds_calculate_sc(self) -> None:
        """Auto-classify → use suggested params in calculate_short_circuit."""
        from app.standards.iec60909 import calculate_short_circuit

        proj = _StubProject(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0),
            _StubComponent(
                name="M1", type="MOTOR", x=200, y=0,
                properties=[
                    _StubProperty("motor_type", "synchronous"),
                    _StubProperty("n_poles", "4"),
                ],
            ),
        ])
        cls = auto_classify_fault_distance(proj, "B1")
        # Use the suggested params
        result = calculate_short_circuit(
            rated_voltage_kV=13.8,
            z_thevenin_ohm=complex(0.5, 2.0),
            fault_distance=cls.fault_distance,
            breaker_min_delay_s=cls.suggested_breaker_min_delay_s,
            generator_x_d_subtransient_pu=cls.suggested_x_d_subtransient_pu,
            is_synchronous_motor=cls.is_synchronous_motor,
            motor_speed_gradient_pu_per_s=cls.motor_speed_gradient_pu_per_s,
        )
        # Verify the classification flowed through
        assert result.Ik_pp_kA > 0
        # Sync motor → no q decay → Ik_steady = Ib
        assert result.Ik_steady_kA == result.Ib_kA


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
