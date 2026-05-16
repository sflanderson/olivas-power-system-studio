"""
tests.test_pp_v1_2_0_tcc_damage_gamma2 — sub-sprint γ.2.

Transformer through-fault curve (IEEE C57.109 / IEEE 242 §11.5.6).

Validação anti-alucinação
==========================

K factors validados literalmente contra IEEE Std 242-2001
(Buff Book) §11.5.6:

> "For the frequent-fault region, the I²t curve corresponds
> to a value of K = 1250 (where I is in per unit of nameplate
> full-load current and t is in seconds). For the
> infrequent-fault region, K = 5000."

Mechanical floor de 2s vem de IEEE C57.109 §5:

> "for currents up to approximately 25 times the transformer
> rated current, the I²t = constant curve [...]; for higher
> currents, [...] the curve is limited to 2 s due to mechanical
> considerations..."

Logo: ``t(I) = MAX(K/I_pu², 2s)``.

Cálculos validados à mão:
* K=1250, I_pu=10: t = 1250/100 = 12.5s. MAX(12.5, 2) = 12.5s
* K=1250, I_pu=25: t = 1250/625 = 2s. MAX(2, 2) = 2s (junção)
* K=1250, I_pu=50: t = 1250/2500 = 0.5s. MAX(0.5, 2) = 2s (mech floor)
* K=5000, I_pu=10: t = 5000/100 = 50s. MAX(50, 2) = 50s

**Histórico anti-alucinação**: a primeira implementação usava
MIN em vez de MAX. Os testes canônicos detectaram o bug
imediatamente. Implementação corrigida + comentário detalhado
no docstring de TransformerThroughFaultCurve.

**Aceite γ.2**: 12+ testes, K factors corretos, MAX (não MIN).
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_damage import (
    TransformerThroughFaultCurve,
    XfmrFaultCategory,
    _K_THROUGH_FAULT,
    _T_MECHANICAL_FLOOR_S,
)


# ---------------------------------------------------------------------------
# Constantes K — validação canônica IEEE 242 §11.5.6
# ---------------------------------------------------------------------------


class TestKConstants:
    """K factors devem coincidir EXATAMENTE com IEEE Std 242 §11.5.6."""

    def test_frequent_K_is_1250(self):
        assert _K_THROUGH_FAULT[XfmrFaultCategory.FREQUENT] == 1250.0

    def test_infrequent_K_is_5000(self):
        assert _K_THROUGH_FAULT[XfmrFaultCategory.INFREQUENT] == 5000.0

    def test_mechanical_floor_is_2s(self):
        """IEEE C57.109 §5: mechanical floor 2s em high-I."""
        assert _T_MECHANICAL_FLOOR_S == 2.0


# ---------------------------------------------------------------------------
# Construção e validação
# ---------------------------------------------------------------------------


class TestConstruction:

    def test_constructs_with_required(self):
        x = TransformerThroughFaultCurve(
            xfmr_id="T1",
            rated_current_A=100.0,
            category=XfmrFaultCategory.FREQUENT,
        )
        assert x.xfmr_id == "T1"
        assert x.rated_current_A == 100.0

    def test_rated_current_must_be_positive(self):
        with pytest.raises(ValueError):
            TransformerThroughFaultCurve(
                xfmr_id="T", rated_current_A=0,
                category=XfmrFaultCategory.FREQUENT,
            )

    def test_K_factor_method(self):
        x = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.FREQUENT,
        )
        assert x.K_factor() == 1250.0


# ---------------------------------------------------------------------------
# Fórmula t = MAX(K/I_pu², 2s) validada à mão
# ---------------------------------------------------------------------------


class TestFormulaCorrected:
    """
    Fórmula correta: t = MAX(K/I_pu², 2s).

    Em I_pu pequeno: thermal domina (t > 2s).
    Em I_pu grande: mech floor 2s domina (t = 2s).
    Junção em I_pu = sqrt(K/2):
        K=1250 → 25
        K=5000 → 50
    """

    def test_below_In_returns_inf(self):
        x = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.FREQUENT,
        )
        assert math.isinf(x.through_fault_time_at_current(50))
        assert math.isinf(x.through_fault_time_at_current(100))

    def test_frequent_at_10pu_is_12_5s_thermal(self):
        """I/In=10, K=1250: t_thermal = 12.5s. 12.5 > 2 floor.
        damage = MAX(12.5, 2) = 12.5s."""
        x = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.FREQUENT,
        )
        t = x.through_fault_time_at_current(1000)  # 10pu
        assert t == pytest.approx(12.5, rel=1e-3)

    def test_frequent_at_25pu_is_2s_junction(self):
        """I/In=25, K=1250: t_thermal = 2s. MAX(2,2) = 2s (junção)."""
        x = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.FREQUENT,
        )
        t = x.through_fault_time_at_current(2500)  # 25pu
        assert t == pytest.approx(2.0, rel=1e-3)

    def test_frequent_at_50pu_is_2s_mech_floor(self):
        """I/In=50, K=1250: t_thermal = 0.5s. MAX(0.5, 2) = 2s.
        Mech floor domina."""
        x = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.FREQUENT,
        )
        t = x.through_fault_time_at_current(5000)  # 50pu
        assert t == pytest.approx(2.0, rel=1e-3)

    def test_frequent_at_100pu_still_2s_mech_floor(self):
        """Em I_pu altíssimo, ainda é 2s (não desce abaixo do floor)."""
        x = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.FREQUENT,
        )
        t = x.through_fault_time_at_current(10000)  # 100pu
        assert t == pytest.approx(2.0, rel=1e-3)

    def test_infrequent_K_5000_at_10pu(self):
        """K=5000, I/In=10: t_thermal = 50s. MAX(50, 2) = 50s."""
        x = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.INFREQUENT,
        )
        t = x.through_fault_time_at_current(1000)  # 10pu
        assert t == pytest.approx(50.0, rel=1e-3)

    def test_infrequent_at_50pu_is_2s_junction(self):
        """K=5000, I/In=50: t_thermal = 5000/2500 = 2s. MAX = 2s."""
        x = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.INFREQUENT,
        )
        t = x.through_fault_time_at_current(5000)  # 50pu
        assert t == pytest.approx(2.0, rel=1e-3)

    def test_infrequent_at_100pu_is_2s_mech_floor(self):
        """K=5000, I/In=100: t_thermal = 0.5s. MAX(0.5, 2) = 2s."""
        x = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.INFREQUENT,
        )
        t = x.through_fault_time_at_current(10000)  # 100pu
        assert t == pytest.approx(2.0, rel=1e-3)

    def test_disabled_returns_inf(self):
        x = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.FREQUENT,
            enabled=False,
        )
        assert math.isinf(x.through_fault_time_at_current(2000))


# ---------------------------------------------------------------------------
# Comparação categories — INFREQUENT mais tolerante
# ---------------------------------------------------------------------------


class TestCategoryComparison:

    def test_infrequent_tolerates_more_than_frequent(self):
        """Mesma I, INFREQUENT (K=5000) >= FREQUENT (K=1250)."""
        x_freq = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.FREQUENT,
        )
        x_infreq = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.INFREQUENT,
        )
        for I in (1000, 1500, 2500):  # 10pu, 15pu, 25pu
            t_f = x_freq.through_fault_time_at_current(I)
            t_i = x_infreq.through_fault_time_at_current(I)
            # Em I_pu < 25, infreq aguenta MAIS tempo (4x mais)
            if I < 2500:
                assert t_i > t_f, (
                    f"INFREQUENT deveria aguentar mais em I={I}, "
                    f"obteve freq={t_f} infreq={t_i}"
                )


# ---------------------------------------------------------------------------
# through_fault_points (plot data)
# ---------------------------------------------------------------------------


class TestPoints:

    def test_points_finite_only(self):
        x = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.FREQUENT,
        )
        pts = x.through_fault_points(i_max_A=10000, n_points=50)
        for I, t in pts:
            assert math.isfinite(t)
            assert t > 0

    def test_points_decreasing_then_floor(self):
        """t diminui até atingir o piso de 2s, depois constante."""
        x = TransformerThroughFaultCurve(
            xfmr_id="T", rated_current_A=100,
            category=XfmrFaultCategory.INFREQUENT,
        )
        # K=5000, threshold I_pu=50 → I=5000A
        pts = x.through_fault_points(i_min_A=200, i_max_A=20000, n_points=30)
        # Em I baixo (200=2pu): t = 5000/4 = 1250s
        # Em I alto (20000=200pu): t = 2s (floor)
        assert len(pts) > 10
        # Último ponto deve estar no floor
        last_t = pts[-1][1]
        assert last_t == pytest.approx(2.0, rel=1e-3)
