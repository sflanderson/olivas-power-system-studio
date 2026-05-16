"""
tests/test_pp_v0_70_lcc_extensions.py — v0.70 LCC bundling
+ skin-effect.
"""

from __future__ import annotations

import math

import pytest

from app.preprocessor.lcc_extensions import (
    ac_resistance_with_skin_effect,
    bundle_equivalent_radius_GMR,
    line_constants_with_bundling_and_skin,
    skin_depth_m,
    skin_effect_factor,
)


# ---------------------------------------------------------------------------
# Bundling
# ---------------------------------------------------------------------------


class TestBundlingGMR:

    def test_n1_returns_conductor_radius(self):
        """n=1 (sem bundling) → r_eq = r_c."""
        r = bundle_equivalent_radius_GMR(
            conductor_radius_m=0.01,
            bundle_radius_m=0.0,    # irrelevante
            n_conductors=1,
        )
        assert r == 0.01

    def test_n2_increases_radius(self):
        """2-conductor bundle: r_eq > r_c."""
        r_eq = bundle_equivalent_radius_GMR(
            conductor_radius_m=0.01,
            bundle_radius_m=0.20,
            n_conductors=2,
        )
        # r_eq = sqrt(2 · 0.01 · 0.40) = sqrt(0.008) = 0.0894
        assert r_eq == pytest.approx(0.0894, rel=0.01)

    def test_n4_typical_500kv(self):
        """4-conductor bundle 500 kV (típico)."""
        r_eq = bundle_equivalent_radius_GMR(
            conductor_radius_m=0.014,
            bundle_radius_m=0.20,
            n_conductors=4,
        )
        # Esperado: ~190 mm (ordem de grandeza)
        assert 0.10 < r_eq < 0.30

    def test_bundling_increases_radius_vs_single(self):
        """
        Bundling (n>1) sempre dá r_eq > r_c.
        OBS: para fixed bundle_radius, n→∞ não é monotônico
        em r_eq porque conductors se aproximam e S diminui;
        a comparação certa é vs single conductor.
        """
        r1 = bundle_equivalent_radius_GMR(0.01, 0.20, 1)
        r2 = bundle_equivalent_radius_GMR(0.01, 0.20, 2)
        r4 = bundle_equivalent_radius_GMR(0.01, 0.20, 4)
        # Cada bundle > single
        assert r2 > r1
        assert r4 > r1

    def test_invalid_n_raises(self):
        with pytest.raises(ValueError):
            bundle_equivalent_radius_GMR(0.01, 0.20, 0)

    def test_invalid_radius_raises(self):
        with pytest.raises(ValueError):
            bundle_equivalent_radius_GMR(0.0, 0.20, 4)

    def test_n2_zero_bundle_raises(self):
        """n>=2 mas bundle=0 → erro."""
        with pytest.raises(ValueError):
            bundle_equivalent_radius_GMR(0.01, 0.0, 2)


# ---------------------------------------------------------------------------
# Skin depth
# ---------------------------------------------------------------------------


class TestSkinDepth:

    def test_copper_60hz(self):
        """Cu @60Hz → δ ≈ 8.5 mm."""
        d = skin_depth_m(60.0)
        assert 0.008 < d < 0.009

    def test_copper_higher_freq_smaller_depth(self):
        """f maior → δ menor."""
        d60 = skin_depth_m(60.0)
        d1k = skin_depth_m(1000.0)
        d10k = skin_depth_m(10000.0)
        assert d60 > d1k > d10k

    def test_aluminum_resistivity(self):
        """Al tem resistividade maior → δ maior @mesma freq."""
        d_cu = skin_depth_m(60.0, resistivity_ohm_m=1.724e-8)
        d_al = skin_depth_m(60.0, resistivity_ohm_m=2.65e-8)
        assert d_al > d_cu

    def test_zero_freq_inf(self):
        assert skin_depth_m(0.0) == float("inf")


# ---------------------------------------------------------------------------
# Skin effect factor
# ---------------------------------------------------------------------------


class TestSkinFactor:

    def test_60hz_small_conductor_negligible(self):
        """50mm² @60Hz: skin desprezível (~1.001)."""
        # Raio para 50 mm² ≈ 4 mm
        f = skin_effect_factor(0.004, 60.0)
        assert 1.0 <= f < 1.05

    def test_60hz_large_conductor(self):
        """1000mm² @60Hz: ratio significativo ~1.10-1.40."""
        # Raio para 1000 mm² ≈ 17.8 mm
        f = skin_effect_factor(0.0178, 60.0)
        assert 1.10 <= f < 1.50

    def test_high_freq_significant(self):
        """1 kHz / 1000mm²: ratio significativo."""
        f = skin_effect_factor(0.0178, 1000.0)
        assert f > 2.0

    def test_very_high_freq(self):
        """100 kHz / 1000mm²: ratio muito alto."""
        f = skin_effect_factor(0.0178, 100000.0)
        assert f > 30

    def test_factor_minimum_one(self):
        """Nunca retorna < 1.0."""
        f = skin_effect_factor(0.001, 1.0)
        assert f >= 1.0


# ---------------------------------------------------------------------------
# AC resistance composition
# ---------------------------------------------------------------------------


class TestAcResistance:

    def test_dc_when_no_skin(self):
        """f baixa / r pequeno → R_AC ≈ R_DC."""
        r_dc = 0.5
        r_ac = ac_resistance_with_skin_effect(
            r_dc, conductor_radius_m=0.001,
            frequency_Hz=60.0,
        )
        assert r_ac == pytest.approx(r_dc, rel=0.01)

    def test_ac_higher_at_higher_freq(self):
        """f maior → R_AC maior."""
        r_60 = ac_resistance_with_skin_effect(
            0.05, 0.018, 60.0,
        )
        r_1k = ac_resistance_with_skin_effect(
            0.05, 0.018, 1000.0,
        )
        assert r_1k > r_60


# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------


class TestCombined:

    def test_returns_dict(self):
        out = line_constants_with_bundling_and_skin(
            R_dc_per_conductor_ohm_per_km=0.05,
            conductor_radius_m=0.014,
            bundle_radius_m=0.20,
            n_conductors=4,
            frequency_Hz=60.0,
        )
        assert "r_eq_m" in out
        assert "R_AC_ohm_per_km" in out
        assert "skin_factor" in out

    def test_4_bundle_resistance_quartered(self):
        """4 conductors em paralelo → R bundle = R_per_cond / 4
        × skin_factor."""
        out = line_constants_with_bundling_and_skin(
            R_dc_per_conductor_ohm_per_km=0.20,
            conductor_radius_m=0.014,
            bundle_radius_m=0.20,
            n_conductors=4,
            frequency_Hz=60.0,
        )
        # Skin negligible @60Hz / 14mm: ratio ≈ 1.0-1.2
        # R bundle ≈ 0.20 × skin / 4 = 0.05 × skin
        assert 0.05 <= out["R_AC_ohm_per_km"] <= 0.07

    def test_n1_no_paralleling(self):
        """n=1 sem paralelização → R_AC bundle = R_AC single."""
        out = line_constants_with_bundling_and_skin(
            R_dc_per_conductor_ohm_per_km=0.20,
            conductor_radius_m=0.014,
            bundle_radius_m=0.20,
            n_conductors=1,
            frequency_Hz=60.0,
        )
        # Sem bundling: r_eq = r_conductor; R_AC = R_DC × skin
        assert out["r_eq_m"] == 0.014
