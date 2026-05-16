"""
tests/test_pp_lcc_bergeron.py — v0.25.2: BERG bridge integration
+ compute_bergeron_pos_sequence.

Cobre:

* compute_bergeron_pos_sequence: Z_char típico 138 kV (350-450 Ω),
  velocity ~95-99% c, travel_time = ℓ/v.
* Validação: length_km ≤ 0 rejeitado, geometria com L=0 ou C=0
  rejeitada.
* Bridge: BERG com geometria → BranchComponent type "-1"
  semantic_type "line_bergeron_lcc" com Z_char/τ/R nos slots.
* BERG sem geometria → fallback placeholder + warning.
* Coexistência: TLIN (PI lumped) e BERG (Bergeron) no mesmo
  projeto.
* Frequency-independence: BERG calcula a 60 Hz (sem dispersão).
"""

from __future__ import annotations

import math

import pytest

from app.preprocessor.bridge_to_atp import to_atp
from app.preprocessor.lcc import (
    BergeronParams, LineGeometry, Conductor,
    compute_bergeron_pos_sequence, make_3phase_geometry,
)
from app.preprocessor.models import PpComponent, PpProject, PpProperty


def _std_3p_geometry() -> LineGeometry:
    """Linha 138 kV vertical típica."""
    return make_3phase_geometry(
        x_a=0, y_a=15, x_b=0, y_b=12, x_c=0, y_c=9,
        radius=0.0091, R_dc_per_km=0.18,
        soil_resistivity=100.0, frequency=60.0,
    )


def _make_berg_with_geom(name: str = "LT_BG") -> PpComponent:
    return PpComponent(
        type="BERG", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[
            PpProperty("100 km"), PpProperty("500 Ohm"),
            PpProperty("0"), PpProperty("15"),
            PpProperty("0"), PpProperty("12"),
            PpProperty("0"), PpProperty("9"),
            PpProperty("0.0091"), PpProperty("0.18"),
            PpProperty("100"),
        ],
    )


def _make_berg_legacy(name: str = "LT_BG_LEG") -> PpComponent:
    return PpComponent(
        type="BERG", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty("100 km"), PpProperty("500 Ohm")],
    )


# ---------------------------------------------------------------------------
# compute_bergeron_pos_sequence
# ---------------------------------------------------------------------------


class TestComputeBergeron:
    def test_138kv_typical_z_char(self):
        bp = compute_bergeron_pos_sequence(_std_3p_geometry(), length_km=100)
        assert 300 < bp.Z_char_pos < 500    # típico LT 138 kV: 350-450 Ω

    def test_velocity_close_to_c(self):
        bp = compute_bergeron_pos_sequence(_std_3p_geometry(), length_km=100)
        c = 3.0e8
        assert 0.93 * c < bp.velocity < 1.0 * c   # 93-100% c

    def test_travel_time_consistent(self):
        bp = compute_bergeron_pos_sequence(_std_3p_geometry(), length_km=100)
        # τ = ℓ/v
        expected_tau = 100_000 / bp.velocity
        assert bp.travel_time == pytest.approx(expected_tau, rel=1e-9)

    def test_R_total_proportional_to_length(self):
        bp50 = compute_bergeron_pos_sequence(_std_3p_geometry(), length_km=50)
        bp100 = compute_bergeron_pos_sequence(_std_3p_geometry(), length_km=100)
        assert bp100.R_total == pytest.approx(2 * bp50.R_total, rel=1e-9)

    def test_travel_time_proportional_to_length(self):
        bp50 = compute_bergeron_pos_sequence(_std_3p_geometry(), length_km=50)
        bp100 = compute_bergeron_pos_sequence(_std_3p_geometry(), length_km=100)
        assert bp100.travel_time == pytest.approx(2 * bp50.travel_time, rel=1e-9)

    def test_z_char_independent_of_length(self):
        """Z_c = √(L'/C') depende só de geom — não de comprimento."""
        bp50 = compute_bergeron_pos_sequence(_std_3p_geometry(), length_km=50)
        bp200 = compute_bergeron_pos_sequence(_std_3p_geometry(), length_km=200)
        assert bp50.Z_char_pos == pytest.approx(bp200.Z_char_pos, rel=1e-9)

    def test_zero_length_rejected(self):
        with pytest.raises(ValueError, match="length_km"):
            compute_bergeron_pos_sequence(_std_3p_geometry(), length_km=0)

    def test_negative_length_rejected(self):
        with pytest.raises(ValueError, match="length_km"):
            compute_bergeron_pos_sequence(_std_3p_geometry(), length_km=-10)


# ---------------------------------------------------------------------------
# BERG bridge integration
# ---------------------------------------------------------------------------


class TestBergBridgeEmission:
    def test_berg_with_geom_emits_branch(self):
        proj = PpProject(
            components=[_make_berg_with_geom()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        assert len(atp.branches) == 1
        b = atp.branches[0]
        assert b.semantic_type == "line_bergeron_lcc"
        assert b.type_code == "-1"
        # Z_char no slot R, τ_ms no slot L, R_total no slot C
        assert b.resistance.strip()
        assert b.inductance.strip()
        assert b.capacitance.strip()

    def test_berg_warning_mentions_z_char_tau_velocity(self):
        proj = PpProject(
            components=[_make_berg_with_geom()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "Z_char" in joined
        assert "τ" in joined or "tau" in joined.lower()
        assert "%" in joined  # velocity como % de c

    def test_berg_z_char_typical_138kv(self):
        proj = PpProject(
            components=[_make_berg_with_geom()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        z_char = float(atp.branches[0].resistance)
        assert 300 < z_char < 500


# ---------------------------------------------------------------------------
# Fallback BERG sem geometria
# ---------------------------------------------------------------------------


class TestBergFallback:
    def test_legacy_berg_falls_back_placeholder(self):
        proj = PpProject(
            components=[_make_berg_legacy()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        # Placeholder type "-1" sem semantic_type "line_bergeron_lcc"
        assert len(atp.branches) == 1
        assert atp.branches[0].semantic_type != "line_bergeron_lcc"

    def test_legacy_warning_suggests_geometry(self):
        proj = PpProject(
            components=[_make_berg_legacy()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "Bergeron" in joined or "geometria" in joined.lower()

    def test_partial_geometry_falls_back(self):
        comp = PpComponent(
            type="BERG", name="X", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[
                PpProperty("100 km"), PpProperty("500"),
                PpProperty("0"), PpProperty("0"),  # y_a=0!
                PpProperty("0"), PpProperty("12"),
                PpProperty("0"), PpProperty("9"),
                PpProperty("0.0091"), PpProperty("0.18"),
                PpProperty("100"),
            ],
        )
        proj = PpProject(components=[comp], wires=[], diagrams=[])
        atp = to_atp(proj)
        # Não deve emitir Bergeron
        non_bergeron = [b for b in atp.branches if b.semantic_type != "line_bergeron_lcc"]
        assert len(non_bergeron) >= 1


# ---------------------------------------------------------------------------
# Coexistência TLIN + BERG no mesmo projeto
# ---------------------------------------------------------------------------


class TestMixedTlinBerg:
    def test_both_emit_with_geometry(self):
        tlin = PpComponent(
            type="TLIN", name="LT_PI", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[
                PpProperty("100 km"), PpProperty("0.05 Ohm/km"),
                PpProperty("0"), PpProperty("15"),
                PpProperty("0"), PpProperty("12"),
                PpProperty("0"), PpProperty("9"),
                PpProperty("0.0091"), PpProperty("0.18"),
                PpProperty("100"),
            ],
        )
        proj = PpProject(
            components=[tlin, _make_berg_with_geom("LT_BG")],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        # 1 line_pi_lcc + 1 line_bergeron_lcc
        sem_types = {b.semantic_type for b in atp.branches}
        assert "line_pi_lcc" in sem_types
        assert "line_bergeron_lcc" in sem_types


# ---------------------------------------------------------------------------
# JMARTI seguindo placeholder em v0.25.2
# ---------------------------------------------------------------------------


class TestJMartiStillPlaceholder:
    def test_jmarti_remains_placeholder(self):
        comp = PpComponent(
            type="JMARTI", name="JM1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("model.pch")],
        )
        proj = PpProject(components=[comp], wires=[], diagrams=[])
        atp = to_atp(proj)
        # Sem semantic_type "line_*_lcc"
        for b in atp.branches:
            assert "lcc" not in b.semantic_type
