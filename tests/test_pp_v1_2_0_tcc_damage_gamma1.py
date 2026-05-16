"""
tests.test_pp_v1_2_0_tcc_damage_gamma1 — sub-sprint γ.1.

Cable damage curve (NBR 5410 §6.5.4 / IEC 60364-4-43).

Validação anti-alucinação
==========================

Todos os K factors são validados contra valores literais
da Tabela 43 NBR 5410:2004:

* Cu/PVC ≤300 mm² → K = 115
* Cu/PVC >300 mm² → K = 103
* Cu/EPR ou XLPE → K = 143
* Al/PVC → K = 76
* Al/EPR ou XLPE → K = 94

E todos os exemplos de cálculo são feitos à mão antes de
asserir o tempo:

* Cabo 50mm² Cu/PVC em 1kA: t = (115·50)² / 1000² =
  5750² / 1e6 = 33.0625 s

**Aceite γ.1**: 12+ testes, 100% verde, K factors corretos.
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_damage import (
    CableDamageCurve,
    CableMaterial,
    _K_factor,
)


# ---------------------------------------------------------------------------
# K factor lookup (validação canônica NBR 5410 Tabela 43)
# ---------------------------------------------------------------------------


class TestKFactorCanonical:
    """K factors devem coincidir EXATAMENTE com NBR 5410 Tabela 43."""

    def test_cu_pvc_below_300_is_115(self):
        assert _K_factor(CableMaterial.Cu_PVC, 50.0) == 115.0
        assert _K_factor(CableMaterial.Cu_PVC, 240.0) == 115.0
        assert _K_factor(CableMaterial.Cu_PVC, 300.0) == 115.0

    def test_cu_pvc_above_300_is_103(self):
        assert _K_factor(CableMaterial.Cu_PVC, 400.0) == 103.0
        assert _K_factor(CableMaterial.Cu_PVC, 500.0) == 103.0

    def test_cu_xlpe_is_143(self):
        assert _K_factor(CableMaterial.Cu_XLPE, 50.0) == 143.0
        assert _K_factor(CableMaterial.Cu_XLPE, 500.0) == 143.0

    def test_cu_epr_same_as_xlpe(self):
        assert _K_factor(CableMaterial.Cu_EPR, 50.0) == 143.0

    def test_al_pvc_is_76(self):
        assert _K_factor(CableMaterial.Al_PVC, 50.0) == 76.0

    def test_al_xlpe_is_94(self):
        assert _K_factor(CableMaterial.Al_XLPE, 50.0) == 94.0

    def test_al_epr_same_as_xlpe(self):
        assert _K_factor(CableMaterial.Al_EPR, 50.0) == 94.0


# ---------------------------------------------------------------------------
# CableDamageCurve construção e validação
# ---------------------------------------------------------------------------


class TestCableDamageCurveConstruction:

    def test_constructs_with_required_params(self):
        c = CableDamageCurve(
            cable_id="C1",
            section_mm2=50.0,
            material=CableMaterial.Cu_PVC,
        )
        assert c.cable_id == "C1"
        assert c.section_mm2 == 50.0
        assert c.material == CableMaterial.Cu_PVC

    def test_section_must_be_positive(self):
        with pytest.raises(ValueError):
            CableDamageCurve(
                cable_id="x", section_mm2=0,
                material=CableMaterial.Cu_PVC,
            )
        with pytest.raises(ValueError):
            CableDamageCurve(
                cable_id="x", section_mm2=-50,
                material=CableMaterial.Cu_PVC,
            )

    def test_imin_must_be_positive(self):
        with pytest.raises(ValueError):
            CableDamageCurve(
                cable_id="x", section_mm2=50,
                material=CableMaterial.Cu_PVC,
                i_min_A=0,
            )

    def test_K_factor_method_matches_lookup(self):
        c = CableDamageCurve(
            cable_id="x", section_mm2=400,
            material=CableMaterial.Cu_PVC,
        )
        # 400mm² Cu/PVC = 103 (>300mm²)
        assert c.K_factor() == 103.0


# ---------------------------------------------------------------------------
# damage_time_at_current — fórmula t = (K·S)²/I² validada à mão
# ---------------------------------------------------------------------------


class TestDamageTimeFormula:
    """Validação da fórmula NBR 5410 §6.5.4 com cálculos manuais."""

    def test_50mm2_cu_pvc_at_1kA_is_33s(self):
        """t = (115 · 50)² / 1000² = 5750²/1e6 = 33.0625s."""
        c = CableDamageCurve(
            cable_id="C", section_mm2=50,
            material=CableMaterial.Cu_PVC,
        )
        t = c.damage_time_at_current(1000)
        assert t == pytest.approx(33.0625, rel=1e-6)

    def test_50mm2_cu_pvc_at_10kA_is_0_33s(self):
        """t = (115·50)² / 10000² = 33.0625/100 = 0.330625s."""
        c = CableDamageCurve(
            cable_id="C", section_mm2=50,
            material=CableMaterial.Cu_PVC,
        )
        t = c.damage_time_at_current(10000)
        assert t == pytest.approx(0.330625, rel=1e-6)

    def test_50mm2_cu_xlpe_higher_K(self):
        """XLPE tem K=143 (vs PVC 115). Damage time maior."""
        c_pvc = CableDamageCurve(
            cable_id="P", section_mm2=50,
            material=CableMaterial.Cu_PVC,
        )
        c_xlpe = CableDamageCurve(
            cable_id="X", section_mm2=50,
            material=CableMaterial.Cu_XLPE,
        )
        # Para mesma I, XLPE aguenta mais tempo
        assert c_xlpe.damage_time_at_current(1000) > c_pvc.damage_time_at_current(1000)
        # Razão = (143/115)² = 1.547
        ratio = c_xlpe.damage_time_at_current(1000) / c_pvc.damage_time_at_current(1000)
        assert ratio == pytest.approx((143.0 / 115.0) ** 2, rel=1e-6)

    def test_400mm2_cu_pvc_uses_K103(self):
        """t = (103 · 400)² / 10000² = 41200²/1e8 = 16.97s."""
        c = CableDamageCurve(
            cable_id="C", section_mm2=400,
            material=CableMaterial.Cu_PVC,
        )
        t = c.damage_time_at_current(10000)
        # K=103, S=400, I=10000:  (103*400)^2 / 10000^2 = 16974400/1e8 = 0.169744
        # Hmm, espera: 41200² = 1697440000. /1e8 = 16.9744
        # Wait, (103*400)^2 = 41200^2 = 1.69744e9. / 10000^2 = 1e8
        # = 16.9744
        assert t == pytest.approx(16.9744, rel=1e-3)

    def test_below_imin_returns_inf(self):
        c = CableDamageCurve(
            cable_id="C", section_mm2=50,
            material=CableMaterial.Cu_PVC,
            i_min_A=10.0,
        )
        assert math.isinf(c.damage_time_at_current(5))
        assert math.isinf(c.damage_time_at_current(10))

    def test_disabled_returns_inf(self):
        c = CableDamageCurve(
            cable_id="C", section_mm2=50,
            material=CableMaterial.Cu_PVC,
            enabled=False,
        )
        assert math.isinf(c.damage_time_at_current(10000))

    def test_inverse_square_relationship(self):
        """Dobrar I deve dividir t por 4 (relação inversa quadrática)."""
        c = CableDamageCurve(
            cable_id="C", section_mm2=50,
            material=CableMaterial.Cu_XLPE,
        )
        t1 = c.damage_time_at_current(1000)
        t2 = c.damage_time_at_current(2000)
        assert t1 / t2 == pytest.approx(4.0, rel=1e-6)


# ---------------------------------------------------------------------------
# damage_points — plot data
# ---------------------------------------------------------------------------


class TestDamagePoints:

    def test_points_finite_only(self):
        c = CableDamageCurve(
            cable_id="C", section_mm2=50,
            material=CableMaterial.Cu_XLPE,
        )
        pts = c.damage_points(i_min_A=100, i_max_A=10000, n_points=50)
        for I, t in pts:
            assert math.isfinite(t)
            assert t > 0
            assert I > 0

    def test_points_decreasing_in_t(self):
        """Damage time diminui com I."""
        c = CableDamageCurve(
            cable_id="C", section_mm2=50,
            material=CableMaterial.Cu_XLPE,
        )
        pts = c.damage_points(i_min_A=100, i_max_A=10000, n_points=20)
        ts = [t for _, t in pts]
        for i in range(1, len(ts)):
            assert ts[i] < ts[i - 1]

    def test_disabled_returns_empty_useful_points(self):
        c = CableDamageCurve(
            cable_id="C", section_mm2=50,
            material=CableMaterial.Cu_XLPE,
            enabled=False,
        )
        pts = c.damage_points(i_min_A=100, i_max_A=10000)
        # Disabled → todo damage_time é inf → pts vazio
        assert pts == []
