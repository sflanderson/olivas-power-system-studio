"""
tests/test_pp_iec60909_kappa.py — v0.28.0-PRO P1.4: Methods
A/B/C de cálculo do κ (peak factor) IEC 60909-0 §4.3.1.2.

Cobre:

* KappaMethod enum.
* kappa_method_A — fórmula clássica.
* kappa_method_B — fator 1.15 + cap 2.00.
* kappa_method_C — frequência-equivalente.
* kappa_recommended dispatcher.
* recommend_method_for_topology heurística.
"""

from __future__ import annotations

import math

import pytest

from app.standards.iec60909_kappa import (
    KappaMethod,
    kappa_method_A,
    kappa_method_B,
    kappa_method_C,
    kappa_recommended,
    recommend_method_for_topology,
)


# ---------------------------------------------------------------------------
# Method A
# ---------------------------------------------------------------------------


class TestMethodA:

    def test_zero_rovx_gives_2(self):
        """R/X=0 (puramente indutivo) → κ = 2.00."""
        assert kappa_method_A(0.0) == pytest.approx(2.00, rel=1e-6)

    def test_inf_rovx_gives_1_02(self):
        """R/X muito grande (resistivo) → κ → 1.02."""
        assert kappa_method_A(100.0) == pytest.approx(1.02, abs=0.01)

    def test_typical_HV(self):
        """R/X = 0.10 → κ ≈ 1.747."""
        assert kappa_method_A(0.10) == pytest.approx(1.746, rel=1e-3)

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            kappa_method_A(-0.1)


# ---------------------------------------------------------------------------
# Method B
# ---------------------------------------------------------------------------


class TestMethodB:

    def test_method_B_15pct_higher_for_typical(self):
        """Method B = 1.15 × Method A para R/X moderado."""
        kA = kappa_method_A(0.30)
        kB = kappa_method_B(0.30)
        assert kB == pytest.approx(1.15 * kA, rel=1e-6)

    def test_method_B_capped_at_2(self):
        """R/X=0 → 1.15 × 2.0 = 2.30 → cap 2.00."""
        kB = kappa_method_B(0.0)
        assert kB == 2.00


# ---------------------------------------------------------------------------
# Method C
# ---------------------------------------------------------------------------


class TestMethodC:

    def test_purely_inductive_at_fc_gives_2(self):
        """R=0 em qualquer frequência → R/X corrigido = 0 → κ = 2.00."""
        z_at_fc = complex(0, 1.0)
        kC = kappa_method_C(z_at_fc, nominal_frequency_Hz=50, fc_Hz=20)
        assert kC == pytest.approx(2.00, rel=1e-6)

    def test_purely_resistive_returns_low_kappa(self):
        """X=0 → puramente resistivo → κ = 1.02."""
        z_at_fc = complex(1.0, 0.0)
        kC = kappa_method_C(z_at_fc, nominal_frequency_Hz=50, fc_Hz=20)
        assert kC == pytest.approx(1.02, rel=1e-3)

    def test_correction_factor_applied(self):
        """
        Para R/X=0.30 em fc, fc/fn=20/50=0.40:
        R/X corrigido = 0.30 × 0.40 = 0.12
        κ = 1.02 + 0.98·exp(-3·0.12) = 1.703
        """
        z_at_fc = complex(0.30, 1.0)   # R/X em fc = 0.30
        kC = kappa_method_C(z_at_fc, nominal_frequency_Hz=50, fc_Hz=20)
        expected_rovx = 0.30 * 0.40
        expected_k = 1.02 + 0.98 * math.exp(-3 * expected_rovx)
        assert kC == pytest.approx(expected_k, rel=1e-3)

    def test_zero_Z_rejected(self):
        with pytest.raises(ValueError):
            kappa_method_C(0j)

    def test_fc_above_fn_rejected(self):
        with pytest.raises(ValueError):
            kappa_method_C(complex(1, 1), nominal_frequency_Hz=50, fc_Hz=60)


# ---------------------------------------------------------------------------
# kappa_recommended dispatcher
# ---------------------------------------------------------------------------


class TestKappaRecommended:

    def test_method_A_dispatch(self):
        k = kappa_recommended(0.10, method=KappaMethod.METHOD_A)
        assert k == kappa_method_A(0.10)

    def test_method_B_dispatch(self):
        k = kappa_recommended(0.10, method=KappaMethod.METHOD_B)
        assert k == kappa_method_B(0.10)

    def test_method_C_requires_z_at_fc(self):
        with pytest.raises(ValueError, match="z_thevenin_at_fc"):
            kappa_recommended(0.10, method=KappaMethod.METHOD_C)

    def test_method_C_with_z_at_fc(self):
        z = complex(0.10, 1.0)
        k = kappa_recommended(
            r_over_x_at_fn=0.10, method=KappaMethod.METHOD_C,
            z_thevenin_at_fc=z, nominal_frequency_Hz=50, fc_Hz=20,
        )
        assert k > 0


# ---------------------------------------------------------------------------
# recommend_method_for_topology
# ---------------------------------------------------------------------------


class TestTopologyRecommendation:

    def test_radial_recommends_B(self):
        assert recommend_method_for_topology(is_meshed=False) == KappaMethod.METHOD_B

    def test_meshed_recommends_C(self):
        assert recommend_method_for_topology(is_meshed=True) == KappaMethod.METHOD_C
