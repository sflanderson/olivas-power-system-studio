"""v3.7.1 — Branch impedance extraction (closes SKIPPED_BACKLOG B.1) tests.

Reference:
* IEC 60076-1:2011 §10 (transformer v_sc% impedance)
* IEC 60364-5-52:2009 (cable resistivity Cu/Al)
* PTW Tutorial §Part 1 p.54-58 (libraries)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pytest

from app.postprocessor.branch_impedance import (
    DEFAULT_BRANCH_R_PU,
    DEFAULT_BRANCH_X_PU,
    BranchImpedance,
    _parse_numeric,
    cable_impedance_pu,
    extract_branch_impedance,
    tline_impedance_pu,
    transformer_impedance_pu,
)


# ---------------------------------------------------------------------------
# Stub component
# ---------------------------------------------------------------------------


@dataclass
class _StubProperty:
    name: str
    value: str


@dataclass
class _StubComponent:
    name: str = "X"
    type: str = "Tr"
    x: int = 0
    y: int = 0
    properties: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# _parse_numeric
# ---------------------------------------------------------------------------


class TestParseNumeric:
    def test_plain_number(self) -> None:
        assert _parse_numeric("1.5") == 1.5

    def test_with_unit_suffix(self) -> None:
        assert _parse_numeric("1.5 MVA") == 1.5
        assert _parse_numeric("0.05 Ohm/km") == 0.05
        assert _parse_numeric("13.8 kV") == 13.8

    def test_scientific(self) -> None:
        assert _parse_numeric("1.5e-3") == 0.0015

    def test_none_returns_default(self) -> None:
        assert _parse_numeric(None, default=99.0) == 99.0

    def test_empty_returns_default(self) -> None:
        assert _parse_numeric("", default=42.0) == 42.0

    def test_garbage_returns_default(self) -> None:
        assert _parse_numeric("notanumber", default=7.0) == 7.0

    def test_int_input(self) -> None:
        assert _parse_numeric(5) == 5.0


# ---------------------------------------------------------------------------
# Transformer
# ---------------------------------------------------------------------------


class TestTransformerImpedance:
    def test_typical_5MVA_transformer(self) -> None:
        """5 MVA, 6% impedance, 0.7% R losses → known Z_pu values."""
        comp = _StubComponent(
            type="Tr",
            properties=[
                _StubProperty("S_nom", "5"),       # 5 MVA
                _StubProperty("v_sc_pct", "6"),    # 6%
                _StubProperty("p_sc_kW", "35"),    # 35 kW losses
            ],
        )
        z = transformer_impedance_pu(comp, base_MVA=100.0)
        # On xfmr base: Z = 0.06, R = 35/(5×1000) = 0.007
        # X = sqrt(0.06² - 0.007²) ≈ 0.0596
        # System base ratio = 100/5 = 20
        # R_sys = 0.007 × 20 = 0.14, X_sys ≈ 0.0596 × 20 ≈ 1.192
        assert math.isclose(z.R_pu, 0.14, abs_tol=0.001)
        assert math.isclose(z.X_pu, 1.192, abs_tol=0.005)
        assert z.source == "transformer"

    def test_missing_data_falls_back_to_default(self) -> None:
        comp = _StubComponent(type="Tr")
        z = transformer_impedance_pu(comp, base_MVA=100.0)
        assert z.R_pu == DEFAULT_BRANCH_R_PU
        assert z.X_pu == DEFAULT_BRANCH_X_PU
        assert "missing_data" in z.source

    def test_no_p_sc_uses_xr_heuristic(self) -> None:
        """Without p_sc_kW, defaults to X/R ≈ 7."""
        comp = _StubComponent(
            type="Tr",
            properties=[
                _StubProperty("S_nom", "10"),
                _StubProperty("v_sc_pct", "6"),
            ],
        )
        z = transformer_impedance_pu(comp, base_MVA=100.0)
        # Z = 0.06 on xfmr base; R = 0.06/sqrt(50), X ≈ R×7
        # System base ratio = 10
        assert z.X_pu / z.R_pu == pytest.approx(7.0, rel=0.01)

    def test_zero_S_nom_falls_back(self) -> None:
        comp = _StubComponent(
            type="Tr",
            properties=[
                _StubProperty("S_nom", "0"),
                _StubProperty("v_sc_pct", "6"),
            ],
        )
        z = transformer_impedance_pu(comp, base_MVA=100.0)
        assert "missing_data" in z.source


# ---------------------------------------------------------------------------
# Cable
# ---------------------------------------------------------------------------


class TestCableImpedance:
    def test_copper_cable_typical(self) -> None:
        """50mm² Cu, 100m, 480V, 100MVA → expected R."""
        comp = _StubComponent(
            type="CABLE",
            properties=[
                _StubProperty("section_mm2", "50"),
                _StubProperty("length_m", "100"),
                _StubProperty("material", "Cu"),
            ],
        )
        z = cable_impedance_pu(
            comp, base_MVA=100.0, voltage_base_kV=0.480,
        )
        # R_ohm = (1/56) × 100/50 = 0.03571
        # Z_base = 0.480² / 100 = 0.002304 Ω
        # R_pu = 0.03571 / 0.002304 ≈ 15.5
        assert math.isclose(z.R_pu, 15.5, abs_tol=0.5)
        assert z.source == "cable"

    def test_aluminum_higher_R_than_copper(self) -> None:
        """Same dimensions Cu vs Al → Al has higher R."""
        cu = _StubComponent(
            type="CABLE",
            properties=[
                _StubProperty("section_mm2", "50"),
                _StubProperty("length_m", "100"),
                _StubProperty("material", "Cu"),
            ],
        )
        al = _StubComponent(
            type="CABLE",
            properties=[
                _StubProperty("section_mm2", "50"),
                _StubProperty("length_m", "100"),
                _StubProperty("material", "Al"),
            ],
        )
        z_cu = cable_impedance_pu(cu, base_MVA=100.0, voltage_base_kV=0.480)
        z_al = cable_impedance_pu(al, base_MVA=100.0, voltage_base_kV=0.480)
        # Al ρ = 1/35 vs Cu 1/56 → Al ≈ 1.6× higher R
        assert z_al.R_pu > z_cu.R_pu
        assert math.isclose(z_al.R_pu / z_cu.R_pu, 56/35, rel_tol=0.01)

    def test_zero_section_falls_back(self) -> None:
        comp = _StubComponent(
            type="CABLE",
            properties=[
                _StubProperty("section_mm2", "0"),
                _StubProperty("length_m", "100"),
            ],
        )
        z = cable_impedance_pu(comp, base_MVA=100.0)
        assert "missing_data" in z.source


# ---------------------------------------------------------------------------
# TLine
# ---------------------------------------------------------------------------


class TestTLineImpedance:
    def test_typical_138kV_tline(self) -> None:
        """100km × 0.05 Ω/km @ 138kV / 100MVA."""
        comp = _StubComponent(
            type="TLIN",
            properties=[
                _StubProperty("length", "100 km"),
                _StubProperty("R_per_km", "0.05 Ohm/km"),
            ],
        )
        z = tline_impedance_pu(comp, base_MVA=100.0, voltage_base_kV=138.0)
        # R = 0.05 × 100 = 5 Ω
        # X = 5 × 5 = 25 Ω (X/R ≈ 5 default)
        # Z_base = 138²/100 = 190.44 Ω
        # R_pu ≈ 0.0263, X_pu ≈ 0.131
        assert math.isclose(z.R_pu, 0.0263, abs_tol=0.001)
        assert math.isclose(z.X_pu, 0.131, abs_tol=0.005)
        assert z.source == "tline"


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


class TestExtractDispatch:
    def test_dispatch_to_transformer(self) -> None:
        comp = _StubComponent(
            type="Tr",
            properties=[
                _StubProperty("S_nom", "5"),
                _StubProperty("v_sc_pct", "6"),
            ],
        )
        z = extract_branch_impedance(comp, base_MVA=100.0)
        assert z.source == "transformer"

    def test_dispatch_to_cable(self) -> None:
        comp = _StubComponent(
            type="CABLE",
            properties=[
                _StubProperty("section_mm2", "50"),
                _StubProperty("length_m", "100"),
                _StubProperty("material", "Cu"),
            ],
        )
        z = extract_branch_impedance(comp, base_MVA=100.0)
        assert z.source == "cable"

    def test_dispatch_to_tline(self) -> None:
        comp = _StubComponent(
            type="TLIN",
            properties=[
                _StubProperty("length", "10 km"),
                _StubProperty("R_per_km", "0.1 Ohm/km"),
            ],
        )
        z = extract_branch_impedance(comp, base_MVA=100.0, voltage_base_kV=13.8)
        assert z.source == "tline"

    def test_dispatch_unknown_type_returns_default(self) -> None:
        comp = _StubComponent(type="MOTOR")
        z = extract_branch_impedance(comp, base_MVA=100.0)
        assert z.source == "default_unknown_type"
        assert z.R_pu == DEFAULT_BRANCH_R_PU
        assert z.X_pu == DEFAULT_BRANCH_X_PU

    def test_dispatch_sTr_alias(self) -> None:
        comp = _StubComponent(
            type="sTr",
            properties=[
                _StubProperty("S_nom", "1"),
                _StubProperty("v_sc_pct", "5"),
            ],
        )
        z = extract_branch_impedance(comp, base_MVA=100.0)
        assert z.source == "transformer"


# ---------------------------------------------------------------------------
# Integration with build_pf_system_from_project
# ---------------------------------------------------------------------------


class TestBuildPfRealImpedance:
    def test_uses_transformer_impedance_when_available(self) -> None:
        from app.gui.analysis_dialogs import build_pf_system_from_project

        @dataclass
        class _StubProj:
            components: list = field(default_factory=list)

        # 2 BUS + 1 Transformer between them
        proj = _StubProj(components=[
            _StubComponent(name="B1", type="BUS", x=0, y=0,
                           properties=[_StubProperty("rated_voltage_kV", "13.8")]),
            _StubComponent(name="B2", type="BUS", x=200, y=0,
                           properties=[_StubProperty("rated_voltage_kV", "13.8")]),
            _StubComponent(name="T1", type="Tr", x=100, y=0, properties=[
                _StubProperty("S_nom", "5"),
                _StubProperty("v_sc_pct", "6"),
                _StubProperty("p_sc_kW", "35"),
            ]),
        ])
        sys = build_pf_system_from_project(proj, base_MVA=100.0)
        assert sys is not None
        # The single branch should not have default impedance
        assert len(sys.branches) == 1
        br = sys.branches[0]
        # Transformer extraction yields R≈0.14, X≈1.192 (not defaults)
        assert br.R_pu != DEFAULT_BRANCH_R_PU
        assert br.X_pu != DEFAULT_BRANCH_X_PU
        # Sanity: real values
        assert br.R_pu > 0.05  # Way above default 0.01
        assert br.X_pu > 0.5   # Way above default 0.05

    def test_falls_back_to_default_when_no_branch_component(self) -> None:
        """2 BUS, no Tr/CABLE between → branch uses defaults."""
        from app.gui.analysis_dialogs import build_pf_system_from_project

        @dataclass
        class _StubProj:
            components: list = field(default_factory=list)

        proj = _StubProj(components=[
            _StubComponent(name="B1", type="BUS"),
            _StubComponent(name="B2", type="BUS"),
        ])
        sys = build_pf_system_from_project(proj, base_MVA=100.0)
        assert sys is not None
        br = sys.branches[0]
        # Should fall back to default (no branch component to extract from)
        assert br.R_pu == DEFAULT_BRANCH_R_PU
        assert br.X_pu == DEFAULT_BRANCH_X_PU


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
