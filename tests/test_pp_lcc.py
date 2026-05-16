"""
tests/test_pp_lcc.py — v0.25.0: rotina LCC para cálculo de
matrizes [Z] e [Y] de linhas aéreas a partir da geometria.

Cobre:

* Validação de inputs (Conductor, LineGeometry).
* Sanidade física: matrizes simétricas, Z_self maior em magnitude
  que Z_mutual, Y diagonal positiva imaginária (capacitância).
* Casos limite: condutor único, n condutores idênticos.
* Frequency scaling: aumentar f aumenta termo indutivo
  (proporcional) e reduz |p| (profundidade complexa).
* Helpers geométricos.
* Algoritmo de inversão simétrica.
"""

from __future__ import annotations

import cmath
import math

import pytest

from app.preprocessor.lcc import (
    Conductor,
    LineConstants,
    LineGeometry,
    _invert_symmetric_real,
    complex_ground_depth,
    compute_line_constants,
    distance_between,
    image_distance,
)


# ---------------------------------------------------------------------------
# Conductor
# ---------------------------------------------------------------------------


class TestConductor:
    def test_valid_conductor(self):
        c = Conductor(name="A", x=0, y=10, radius_outer=0.01, R_dc_per_km=0.1)
        assert c.name == "A"

    def test_y_zero_rejected(self):
        with pytest.raises(ValueError, match="y ="):
            Conductor(name="A", x=0, y=0, radius_outer=0.01, R_dc_per_km=0.1)

    def test_negative_y_rejected(self):
        with pytest.raises(ValueError, match="y ="):
            Conductor(name="A", x=0, y=-1, radius_outer=0.01, R_dc_per_km=0.1)

    def test_negative_radius_rejected(self):
        with pytest.raises(ValueError, match="radius_outer"):
            Conductor(name="A", x=0, y=10, radius_outer=-0.01, R_dc_per_km=0.1)

    def test_negative_resistance_rejected(self):
        with pytest.raises(ValueError, match="R_dc_per_km"):
            Conductor(name="A", x=0, y=10, radius_outer=0.01, R_dc_per_km=-0.1)

    def test_effective_gmr_default(self):
        """Default: GMR = 0.7788 × radius_outer."""
        c = Conductor(name="A", x=0, y=10, radius_outer=0.01, R_dc_per_km=0.1)
        assert c.effective_gmr() == pytest.approx(0.7788 * 0.01)

    def test_effective_gmr_explicit(self):
        c = Conductor(
            name="A", x=0, y=10, radius_outer=0.01,
            R_dc_per_km=0.1, gmr=0.0085,
        )
        assert c.effective_gmr() == 0.0085


# ---------------------------------------------------------------------------
# LineGeometry
# ---------------------------------------------------------------------------


def _std_3p_line() -> LineGeometry:
    """Linha 138 kV vertical típica."""
    return LineGeometry(
        conductors=[
            Conductor("A", 0.0, 15.0, 0.0091, 0.18),
            Conductor("B", 0.0, 12.0, 0.0091, 0.18),
            Conductor("C", 0.0, 9.0,  0.0091, 0.18),
        ],
        soil_resistivity=100.0,
        frequency=60.0,
    )


class TestLineGeometryValidation:
    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="conductors"):
            LineGeometry(conductors=[], soil_resistivity=100, frequency=60)

    def test_negative_rho_rejected(self):
        with pytest.raises(ValueError, match="soil_resistivity"):
            LineGeometry(
                conductors=[Conductor("A", 0, 10, 0.01, 0.1)],
                soil_resistivity=-1, frequency=60,
            )

    def test_zero_frequency_rejected(self):
        with pytest.raises(ValueError, match="frequency"):
            LineGeometry(
                conductors=[Conductor("A", 0, 10, 0.01, 0.1)],
                soil_resistivity=100, frequency=0,
            )

    def test_duplicate_names_rejected(self):
        with pytest.raises(ValueError, match="duplicados"):
            LineGeometry(
                conductors=[
                    Conductor("A", 0, 10, 0.01, 0.1),
                    Conductor("A", 1, 10, 0.01, 0.1),
                ],
                soil_resistivity=100, frequency=60,
            )


# ---------------------------------------------------------------------------
# Geometric helpers
# ---------------------------------------------------------------------------


class TestGeometricHelpers:
    def test_distance_between(self):
        c1 = Conductor("A", 0, 10, 0.01, 0.1)
        c2 = Conductor("B", 3, 14, 0.01, 0.1)
        # √((3-0)² + (14-10)²) = √(9+16) = 5
        assert distance_between(c1, c2) == pytest.approx(5.0)

    def test_image_distance(self):
        """Imagem de c2 em (3, -14): distância de (0,10) até (3,-14)
        = √(9 + 576) = √585 ≈ 24.19."""
        c1 = Conductor("A", 0, 10, 0.01, 0.1)
        c2 = Conductor("B", 3, 14, 0.01, 0.1)
        assert image_distance(c1, c2) == pytest.approx(math.sqrt(585))

    def test_image_distance_self_is_2y(self):
        """Distância de c até a imagem de si mesmo = 2·y."""
        c = Conductor("A", 5, 15, 0.01, 0.1)
        assert image_distance(c, c) == pytest.approx(30.0)

    def test_complex_ground_depth_60hz_100ohm(self):
        """p = √(100/(jωμ₀)) — magnitude calculável analiticamente."""
        p = complex_ground_depth(100.0, 60.0)
        # |p|² = 100/(2π·60·4π·1e-7) = 100/(4.74e-4) ≈ 2.11e5
        # |p| ≈ 459 m
        assert abs(p) == pytest.approx(459, abs=1.0)

    def test_complex_ground_depth_higher_freq_smaller(self):
        """Frequência maior → profundidade menor."""
        p_60 = complex_ground_depth(100.0, 60.0)
        p_1000 = complex_ground_depth(100.0, 1000.0)
        assert abs(p_1000) < abs(p_60)

    def test_complex_ground_depth_higher_rho_larger(self):
        """ρ maior → profundidade maior (penetra mais em solo seco)."""
        p_low = complex_ground_depth(10.0, 60.0)
        p_high = complex_ground_depth(10000.0, 60.0)
        assert abs(p_high) > abs(p_low)


# ---------------------------------------------------------------------------
# Matrix inversion helper
# ---------------------------------------------------------------------------


class TestInvertSymmetric:
    def test_invert_2x2(self):
        P = [[2.0, 1.0], [1.0, 2.0]]
        Pinv = _invert_symmetric_real(P)
        # Esperado: 1/3 [[2, -1], [-1, 2]]
        assert Pinv[0][0] == pytest.approx(2.0 / 3.0)
        assert Pinv[0][1] == pytest.approx(-1.0 / 3.0)
        assert Pinv[1][1] == pytest.approx(2.0 / 3.0)

    def test_invert_identity(self):
        P = [[1.0, 0.0], [0.0, 1.0]]
        Pinv = _invert_symmetric_real(P)
        assert Pinv == [[1.0, 0.0], [0.0, 1.0]]

    def test_singular_rejected(self):
        with pytest.raises(ValueError, match="singular"):
            # Linhas linearmente dependentes
            _invert_symmetric_real([[1.0, 2.0], [2.0, 4.0]])


# ---------------------------------------------------------------------------
# compute_line_constants — output structure
# ---------------------------------------------------------------------------


class TestComputeLineConstants:
    def test_returns_LineConstants(self):
        lc = compute_line_constants(_std_3p_line())
        assert isinstance(lc, LineConstants)
        assert lc.n == 3
        assert lc.frequency == 60.0
        assert lc.conductor_names == ("A", "B", "C")

    def test_Z_is_symmetric(self):
        lc = compute_line_constants(_std_3p_line())
        for i in range(lc.n):
            for j in range(i + 1, lc.n):
                assert lc.Z[i][j] == pytest.approx(lc.Z[j][i], abs=1e-9)

    def test_Y_is_symmetric(self):
        lc = compute_line_constants(_std_3p_line())
        for i in range(lc.n):
            for j in range(i + 1, lc.n):
                assert lc.Y[i][j] == pytest.approx(lc.Y[j][i], abs=1e-15)

    def test_Z_real_part_at_diagonal_includes_R_dc(self):
        """Re(Z_ii) deve ser pelo menos R_dc_per_km."""
        lc = compute_line_constants(_std_3p_line())
        for i in range(lc.n):
            assert lc.Z[i][i].real >= 0.18 - 0.01  # tolerância pequena

    def test_Z_imag_dominates_real(self):
        """Em LT, |Im(Z)| >> Re(Z). Razão 4-6 típica para 138 kV."""
        lc = compute_line_constants(_std_3p_line())
        for i in range(lc.n):
            assert abs(lc.Z[i][i].imag) > 2 * lc.Z[i][i].real

    def test_Y_diagonal_pure_imaginary(self):
        """G ≈ 0 → Y é puramente imaginária (e positiva: capacitiva)."""
        lc = compute_line_constants(_std_3p_line())
        for i in range(lc.n):
            assert abs(lc.Y[i][i].real) < 1e-15
            assert lc.Y[i][i].imag > 0   # capacitância shunt

    def test_self_Z_greater_than_mutual(self):
        """|Z_ii| > |Z_ij| (i ≠ j) — auto-impedância domina."""
        lc = compute_line_constants(_std_3p_line())
        for i in range(lc.n):
            for j in range(lc.n):
                if i != j:
                    assert abs(lc.Z[i][i]) > abs(lc.Z[i][j])

    def test_adjacent_mutual_greater_than_extreme(self):
        """A↔B (adjacente) acopla mais que A↔C (extremos da pilha)."""
        lc = compute_line_constants(_std_3p_line())
        # A=0, B=1, C=2 em ordem vertical
        assert abs(lc.Z[0][1]) > abs(lc.Z[0][2])  # AB > AC
        assert abs(lc.Y[0][1]) > abs(lc.Y[0][2])


# ---------------------------------------------------------------------------
# Single conductor
# ---------------------------------------------------------------------------


class TestSingleConductor:
    def test_single_conductor_symmetric(self):
        geom = LineGeometry(
            conductors=[Conductor("X", 0, 10, 0.01, 0.1)],
            soil_resistivity=100, frequency=60,
        )
        lc = compute_line_constants(geom)
        assert lc.n == 1
        assert lc.is_symmetric()

    def test_single_conductor_finite_self_impedance(self):
        geom = LineGeometry(
            conductors=[Conductor("X", 0, 10, 0.01, 0.1)],
            soil_resistivity=100, frequency=60,
        )
        lc = compute_line_constants(geom)
        # Z_self deve ser finito e positivo
        assert math.isfinite(lc.Z[0][0].real)
        assert math.isfinite(lc.Z[0][0].imag)
        assert lc.Z[0][0].real > 0
        assert lc.Z[0][0].imag > 0


# ---------------------------------------------------------------------------
# Frequency scaling
# ---------------------------------------------------------------------------


class TestFrequencyScaling:
    def test_higher_freq_increases_imag_Z(self):
        """ω↑ → ωL↑, então Im(Z) cresce com f (linear no termo
        indutivo principal; correção Carson varia mais devagar)."""
        geom_60 = _std_3p_line()
        geom_400 = LineGeometry(
            conductors=geom_60.conductors,
            soil_resistivity=geom_60.soil_resistivity,
            frequency=400.0,
        )
        z60 = compute_line_constants(geom_60).Z[0][0].imag
        z400 = compute_line_constants(geom_400).Z[0][0].imag
        # Pelo menos 5× mais reativo
        assert z400 > 5 * z60

    def test_higher_freq_increases_imag_Y(self):
        """ω↑ → ωC↑, então Im(Y) escala linearmente."""
        geom_60 = _std_3p_line()
        geom_120 = LineGeometry(
            conductors=geom_60.conductors,
            soil_resistivity=geom_60.soil_resistivity,
            frequency=120.0,
        )
        y60 = compute_line_constants(geom_60).Y[0][0].imag
        y120 = compute_line_constants(geom_120).Y[0][0].imag
        # Y é linear em ω: f×2 → Y×2
        ratio = y120 / y60
        assert 1.95 < ratio < 2.05


# ---------------------------------------------------------------------------
# Soil resistivity sensitivity
# ---------------------------------------------------------------------------


class TestSoilResistivity:
    def test_higher_rho_changes_Z(self):
        """Diferentes ρ produzem diferentes Z (correção Carson)."""
        geom_low = LineGeometry(
            conductors=_std_3p_line().conductors,
            soil_resistivity=10.0, frequency=60,
        )
        geom_high = LineGeometry(
            conductors=_std_3p_line().conductors,
            soil_resistivity=10000.0, frequency=60,
        )
        z_low = compute_line_constants(geom_low).Z[0][0]
        z_high = compute_line_constants(geom_high).Z[0][0]
        # Devem ser diferentes (correção Carson sensível a ρ)
        assert abs(z_low - z_high) > 0.01


# ---------------------------------------------------------------------------
# Identical conductors
# ---------------------------------------------------------------------------


class TestIdenticalConductors:
    def test_two_identical_conductors_same_height_same_self(self):
        """Dois condutores idênticos em mesmas alturas → mesmas
        Z_ii e Y_ii."""
        c1 = Conductor("A", 0, 12, 0.01, 0.1)
        c2 = Conductor("B", 5, 12, 0.01, 0.1)
        geom = LineGeometry(
            conductors=[c1, c2], soil_resistivity=100, frequency=60,
        )
        lc = compute_line_constants(geom)
        assert lc.Z[0][0] == pytest.approx(lc.Z[1][1], rel=1e-6)
        assert lc.Y[0][0] == pytest.approx(lc.Y[1][1], rel=1e-6)
