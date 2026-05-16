"""
tests/test_pp_iec60909_decay.py — v0.28.0-PRO P1.3: fatores
μ e q para faltas near-to-generator (IEC 60909-0 §4.5/4.6).

Cobre:

* mu_factor com r ≤ 2 (far) → 1.0.
* mu_factor com r > 2 e diferentes t_min — curvas calibradas.
* q_factor — decaimento dependente de t_min.
* apply_near_to_generator_decay — wrapper.
* DecayResult dataclass.
* Boundary near vs far (r=2).
"""

from __future__ import annotations

import pytest

from app.standards.iec60909_decay import (
    DecayResult,
    apply_near_to_generator_decay,
    mu_factor,
    q_factor,
)


# ---------------------------------------------------------------------------
# mu_factor
# ---------------------------------------------------------------------------


class TestMuFactor:

    def test_far_from_generator_returns_one(self):
        """r ≤ 2 → μ = 1 (far)."""
        for r in [0.5, 1.0, 1.5, 2.0]:
            assert mu_factor(r, minimum_clearing_time_s=0.05) == 1.0

    def test_near_decreases_with_r(self):
        """r > 2 → μ decresce monotonicamente com r."""
        mu_3 = mu_factor(3.0, 0.05)
        mu_5 = mu_factor(5.0, 0.05)
        mu_10 = mu_factor(10.0, 0.05)
        assert mu_3 > mu_5 > mu_10

    def test_decreases_with_t_min(self):
        """t_min maior → μ menor (mais decaimento)."""
        # r=10 → curvas diferentes com t_min
        mu_fast = mu_factor(10.0, 0.020)
        mu_slow = mu_factor(10.0, 0.250)
        assert mu_slow < mu_fast

    def test_minimum_floor(self):
        """μ ≥ 0.40 para qualquer r."""
        for r in [3.0, 10.0, 50.0]:
            assert mu_factor(r, 0.250) >= 0.40

    def test_negative_r_rejected(self):
        with pytest.raises(ValueError):
            mu_factor(-1.0, 0.05)

    def test_negative_t_rejected(self):
        with pytest.raises(ValueError):
            mu_factor(3.0, -0.01)


# ---------------------------------------------------------------------------
# q_factor
# ---------------------------------------------------------------------------


class TestQFactor:

    def test_subcycle_returns_one(self):
        """t_min < 5 ms → q = 1 (sem decaimento)."""
        assert q_factor(0.001) == 1.0

    def test_long_clearing_returns_floor(self):
        """t_min ≥ 0.25 → q = 0.79."""
        assert q_factor(0.250) == pytest.approx(0.79, rel=1e-3)
        assert q_factor(0.500) == pytest.approx(0.79, rel=1e-3)

    def test_decreases_with_t_min(self):
        q_fast = q_factor(0.020)
        q_slow = q_factor(0.200)
        assert q_slow < q_fast

    def test_q_in_range(self):
        for t in [0.005, 0.020, 0.050, 0.100, 0.250]:
            q = q_factor(t)
            assert 0.50 <= q <= 1.0

    def test_negative_t_rejected(self):
        with pytest.raises(ValueError):
            q_factor(-0.01)


# ---------------------------------------------------------------------------
# apply_near_to_generator_decay
# ---------------------------------------------------------------------------


class TestApplyDecay:

    def test_far_from_generator_no_decay(self):
        """Ik''/I_rG = 1 (longe do gerador) → Ib = Ik = Ik''."""
        result = apply_near_to_generator_decay(
            Ik_pp_kA=10.0,
            IrG_kA=10.0,    # ratio = 1.0
            minimum_clearing_time_s=0.05,
        )
        assert result.mu == 1.0
        assert result.q == 1.0
        assert result.Ib_kA == result.Ik_pp_kA
        assert result.Ik_steady_kA == result.Ik_pp_kA
        assert not result.is_near_to_generator

    def test_near_to_generator_with_decay(self):
        """Ik''/I_rG = 5 (perto do gerador) → Ib < Ik'' e Ik < Ib."""
        result = apply_near_to_generator_decay(
            Ik_pp_kA=10.0, IrG_kA=2.0,
            minimum_clearing_time_s=0.05,
        )
        assert result.is_near_to_generator
        assert result.mu < 1.0
        assert result.q < 1.0
        assert result.Ib_kA < result.Ik_pp_kA
        assert result.Ik_steady_kA < result.Ib_kA

    def test_returns_DecayResult(self):
        r = apply_near_to_generator_decay(10.0, 5.0)
        assert isinstance(r, DecayResult)

    def test_zero_Ik_rejected(self):
        with pytest.raises(ValueError):
            apply_near_to_generator_decay(0.0, 5.0)

    def test_zero_IrG_rejected(self):
        with pytest.raises(ValueError):
            apply_near_to_generator_decay(10.0, 0.0)

    def test_typical_breaking_current_reduction(self):
        """
        IEC 60909-0 §4.5 — breaking current típica para gerador
        forte (Ik''/IrG=10) é 60-80% de Ik'' a t=50ms.
        """
        r = apply_near_to_generator_decay(
            Ik_pp_kA=20.0, IrG_kA=2.0,    # ratio=10
            minimum_clearing_time_s=0.05,
        )
        ratio = r.Ib_kA / r.Ik_pp_kA
        assert 0.55 < ratio < 0.85

    def test_steady_state_lower_than_breaking(self):
        """Ik (steady) < Ib (breaking) sempre near-to-gen."""
        r = apply_near_to_generator_decay(20.0, 2.0, 0.05)
        assert r.Ik_steady_kA < r.Ib_kA


class TestBoundaryConditions:

    def test_boundary_r_equal_2(self):
        """r=2 exatamente → ainda far (μ=1)."""
        r = apply_near_to_generator_decay(10.0, 5.0)   # ratio=2.0
        assert r.mu == 1.0
        assert not r.is_near_to_generator

    def test_just_above_boundary(self):
        """r=2.01 → near, μ < 1."""
        r = apply_near_to_generator_decay(20.1, 10.0)
        assert r.is_near_to_generator
        assert r.mu < 1.0
