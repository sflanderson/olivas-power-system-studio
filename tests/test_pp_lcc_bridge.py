"""
tests/test_pp_lcc_bridge.py — v0.25.1: integração LCC no bridge.
TLIN.ocomp com geometria → cards R-L-C reais via Carson-Deri-Tévan.

Cobre:

* TLIN com geometria completa → BranchComponent R-L-C lumped
  com semantic_type="line_pi_lcc".
* TLIN sem geometria → placeholder tipo -1 legacy.
* TLIN com geometria parcial (faltam campos críticos) →
  placeholder.
* Warning informativo com R/L/C de seq+ por km.
* compute_positive_sequence sanity para 3φ típica.
* make_3phase_geometry helper.
* BERG e JMARTI seguem como placeholder em v0.25.1.
"""

from __future__ import annotations

import math

import pytest

from app.preprocessor.bridge_to_atp import to_atp
from app.preprocessor.lcc import (
    Conductor, LineConstants, LineGeometry,
    compute_line_constants, compute_positive_sequence,
    make_3phase_geometry,
)
from app.preprocessor.models import PpComponent, PpProject, PpProperty


def _make_tlin_with_geom(name: str = "LT") -> PpComponent:
    return PpComponent(
        type="TLIN", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[
            PpProperty("100 km"),       # length
            PpProperty("0.05 Ohm/km"),   # R_per_km legacy
            PpProperty("0"),             # x_a
            PpProperty("15"),            # y_a
            PpProperty("0"),             # x_b
            PpProperty("12"),            # y_b
            PpProperty("0"),             # x_c
            PpProperty("9"),             # y_c
            PpProperty("0.0091"),        # cond_radius
            PpProperty("0.18"),          # cond_R_dc
            PpProperty("100"),           # soil_rho
        ],
    )


def _make_tlin_legacy(name: str = "LT_LEG") -> PpComponent:
    """Sem geometria — só os 2 campos legacy."""
    return PpComponent(
        type="TLIN", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty("100 km"), PpProperty("0.05 Ohm/km")],
    )


# ---------------------------------------------------------------------------
# Happy path: geometria completa → cards reais
# ---------------------------------------------------------------------------


class TestLCCEmission:
    def test_full_geometry_emits_branch_with_RLC(self):
        proj = PpProject(
            components=[_make_tlin_with_geom()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        assert len(atp.branches) == 1
        b = atp.branches[0]
        assert b.semantic_type == "line_pi_lcc"
        # R, L, C devem ser não-vazios
        assert b.resistance.strip() != ""
        assert b.inductance.strip() != ""
        assert b.capacitance.strip() != ""

    def test_no_placeholder_for_lcc_tlin(self):
        proj = PpProject(
            components=[_make_tlin_with_geom()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        # Não deve haver branches type_code "-1" (placeholder)
        placeholders = [b for b in atp.branches if b.type_code == "-1"]
        assert placeholders == []

    def test_warning_mentions_carson(self):
        proj = PpProject(
            components=[_make_tlin_with_geom()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "Carson" in joined or "LCC" in joined

    def test_warning_includes_per_km_values(self):
        proj = PpProject(
            components=[_make_tlin_with_geom()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        # R = 0.18 Ω/km esperado
        assert "0.180" in joined or "0.18" in joined

    def test_RLC_values_sane_for_138kV_line(self):
        """100 km de LT 138 kV: R~18Ω, L~125mH, C~0.9µF (esperado)."""
        proj = PpProject(
            components=[_make_tlin_with_geom()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        b = atp.branches[0]
        r = float(b.resistance)
        l_mh = float(b.inductance)
        c_uf = float(b.capacitance)
        assert 17.5 < r < 18.5      # ≈ 18 Ω
        assert 120 < l_mh < 130      # ≈ 125 mH
        assert 0.85 < c_uf < 1.0     # ≈ 0.93 µF


# ---------------------------------------------------------------------------
# Fallback: sem geometria → placeholder
# ---------------------------------------------------------------------------


class TestFallback:
    def test_legacy_falls_back_to_placeholder(self):
        proj = PpProject(
            components=[_make_tlin_legacy()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        placeholders = [b for b in atp.branches if b.type_code == "-1"]
        assert len(placeholders) == 1

    def test_legacy_warning_suggests_geometry(self):
        proj = PpProject(
            components=[_make_tlin_legacy()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "x_a" in joined or "geometria" in joined.lower()

    def test_partial_geometry_falls_back(self):
        """y_a = 0 (inválido) → fallback."""
        comp = PpComponent(
            type="TLIN", name="X", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[
                PpProperty("100 km"), PpProperty("0.05"),
                PpProperty("0"), PpProperty("0"),  # y_a = 0!
                PpProperty("0"), PpProperty("12"),
                PpProperty("0"), PpProperty("9"),
                PpProperty("0.0091"), PpProperty("0.18"),
                PpProperty("100"),
            ],
        )
        proj = PpProject(components=[comp], wires=[], diagrams=[])
        atp = to_atp(proj)
        placeholders = [b for b in atp.branches if b.type_code == "-1"]
        assert len(placeholders) == 1


# ---------------------------------------------------------------------------
# BERG e JMARTI seguem placeholder em v0.25.1
# ---------------------------------------------------------------------------


class TestBergAndJMartiPlaceholder:
    def test_berg_remains_placeholder(self):
        comp = PpComponent(
            type="BERG", name="B1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100 km"), PpProperty("500 Ohm")],
        )
        proj = PpProject(components=[comp], wires=[], diagrams=[])
        atp = to_atp(proj)
        placeholders = [b for b in atp.branches if b.type_code == "-1"]
        assert len(placeholders) == 1

    def test_jmarti_remains_placeholder(self):
        comp = PpComponent(
            type="JMARTI", name="J1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("model.pch")],
        )
        proj = PpProject(components=[comp], wires=[], diagrams=[])
        atp = to_atp(proj)
        placeholders = [b for b in atp.branches if b.type_code == "-1"]
        assert len(placeholders) == 1


# ---------------------------------------------------------------------------
# compute_positive_sequence — sanity
# ---------------------------------------------------------------------------


class TestComputePositiveSequence:
    def test_138kv_line_R_pos_matches_R_dc(self):
        """Carson é desprezível na seq+; R_pos ≈ R_dc do condutor."""
        geom = make_3phase_geometry(
            x_a=0, y_a=15, x_b=0, y_b=12, x_c=0, y_c=9,
            radius=0.0091, R_dc_per_km=0.18,
            soil_resistivity=100.0, frequency=60.0,
        )
        lc = compute_line_constants(geom)
        ps = compute_positive_sequence(lc)
        assert ps.R_per_km == pytest.approx(0.18, abs=0.01)

    def test_X_pos_typical_range(self):
        """X_pos = ωL_pos típico de 138 kV: 0.4-0.5 Ω/km."""
        geom = make_3phase_geometry(
            x_a=0, y_a=15, x_b=0, y_b=12, x_c=0, y_c=9,
            radius=0.0091, R_dc_per_km=0.18,
        )
        lc = compute_line_constants(geom)
        ps = compute_positive_sequence(lc)
        x_pos = 2 * math.pi * 60 * ps.L_per_km
        assert 0.35 < x_pos < 0.55

    def test_B_pos_typical_range(self):
        """B_pos = ωC_pos típico de 138 kV: 3-5 µS/km."""
        geom = make_3phase_geometry(
            x_a=0, y_a=15, x_b=0, y_b=12, x_c=0, y_c=9,
            radius=0.0091, R_dc_per_km=0.18,
        )
        lc = compute_line_constants(geom)
        ps = compute_positive_sequence(lc)
        b_pos = 2 * math.pi * 60 * ps.C_per_km
        assert 3e-6 < b_pos < 5e-6

    def test_zero_frequency_rejected(self):
        # Manualmente cria LineConstants com freq=0 (improvável)
        # via construtor direto — workaround para o teste.
        # Geometria normal mas alteramos frequency depois? LineConstants
        # é frozen, então criamos um novo:
        lc_zero = LineConstants(
            Z=((1+1j,),), Y=((1j,),), frequency=0.0,
            conductor_names=("A",),
        )
        with pytest.raises(ValueError, match="frequency=0"):
            compute_positive_sequence(lc_zero)


# ---------------------------------------------------------------------------
# make_3phase_geometry helper
# ---------------------------------------------------------------------------


class TestMake3PhaseGeometry:
    def test_returns_geometry_with_3_conductors(self):
        geom = make_3phase_geometry(
            x_a=0, y_a=15, x_b=2, y_b=15, x_c=4, y_c=15,
            radius=0.01, R_dc_per_km=0.1,
        )
        assert len(geom.conductors) == 3
        assert geom.conductors[0].name == "A"
        assert geom.conductors[2].x == 4

    def test_default_soil_and_frequency(self):
        geom = make_3phase_geometry(
            x_a=0, y_a=10, x_b=1, y_b=10, x_c=2, y_c=10,
            radius=0.01, R_dc_per_km=0.1,
        )
        assert geom.soil_resistivity == 100.0
        assert geom.frequency == 60.0
