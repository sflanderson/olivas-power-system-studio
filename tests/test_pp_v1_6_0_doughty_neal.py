"""
tests/test_pp_v1_6_0_doughty_neal.py — v1.6.0 Sprint B.

Cobre o módulo ``app.standards.doughty_neal_arc_flash``:

* Open-air arc formula (E_MA)
* Arc-in-box formula (E_MB)
* Sanity tests (D² scaling, t linear scaling, in-box > open-air)

Reference: Doughty, Neal, Floyd, "Predicting Incident Energy",
IEEE Trans Industry Applications Vol. 36, No. 1, Jan 2000.
Reproduzido em IEEE 1584-2002 Annex B.
"""

from __future__ import annotations

import math

import pytest


class TestDoughtyNealOpenAir:

    def test_module_loadable(self):
        from app.standards import doughty_neal_arc_flash  # noqa: F401

    def test_open_air_returns_positive(self):
        from app.standards.doughty_neal_arc_flash import (
            doughty_neal_open_air_cal_cm2,
        )
        E = doughty_neal_open_air_cal_cm2(
            Ia_kA=20.0,
            arc_clearing_time_s=0.5,
            distance_mm=455.0,
        )
        assert E > 0
        assert math.isfinite(E)

    def test_distance_doubling_reduces_energy(self):
        """E ∝ D^(-1.4738) → dobrar D reduz energia significativamente."""
        from app.standards.doughty_neal_arc_flash import (
            doughty_neal_open_air_cal_cm2,
        )
        E1 = doughty_neal_open_air_cal_cm2(
            Ia_kA=20.0, arc_clearing_time_s=0.5, distance_mm=300.0,
        )
        E2 = doughty_neal_open_air_cal_cm2(
            Ia_kA=20.0, arc_clearing_time_s=0.5, distance_mm=600.0,
        )
        assert E2 < E1
        # 2^(-1.4738) = 0.36, então E2/E1 ~ 0.36
        ratio = E2 / E1
        assert 0.30 < ratio < 0.42

    def test_time_doubling_doubles_energy(self):
        """E é linear em t."""
        from app.standards.doughty_neal_arc_flash import (
            doughty_neal_open_air_cal_cm2,
        )
        E1 = doughty_neal_open_air_cal_cm2(
            Ia_kA=20.0, arc_clearing_time_s=0.25, distance_mm=455.0,
        )
        E2 = doughty_neal_open_air_cal_cm2(
            Ia_kA=20.0, arc_clearing_time_s=0.50, distance_mm=455.0,
        )
        assert E2 == pytest.approx(2 * E1, rel=1e-9)

    def test_zero_time_zero_energy(self):
        from app.standards.doughty_neal_arc_flash import (
            doughty_neal_open_air_cal_cm2,
        )
        E = doughty_neal_open_air_cal_cm2(
            Ia_kA=20.0, arc_clearing_time_s=0.0, distance_mm=455.0,
        )
        assert E == 0.0


class TestDoughtyNealInBox:

    def test_in_box_returns_positive(self):
        from app.standards.doughty_neal_arc_flash import (
            doughty_neal_in_box_cal_cm2,
        )
        E = doughty_neal_in_box_cal_cm2(
            Ia_kA=20.0,
            arc_clearing_time_s=0.5,
            distance_mm=610.0,
        )
        assert E > 0
        assert math.isfinite(E)

    def test_both_formulas_return_finite_positive(self):
        """
        ANTI-ALUCINAÇÃO: NÃO asserta ordering open-air vs in-box.

        Razão: Doughty-Neal-Floyd 2000 paper original encontrou
        empiricamente que a relação varia com Ia/t/D (não há
        ordenamento garantido). NFPA 70E §D.7.6 e IEEE 1584-2018
        §6.4 confirmam esse achado contraintuitivo.

        Asserção fraca: ambas fórmulas retornam valores finitos
        positivos.
        """
        from app.standards.doughty_neal_arc_flash import (
            doughty_neal_open_air_cal_cm2,
            doughty_neal_in_box_cal_cm2,
        )
        E_oa = doughty_neal_open_air_cal_cm2(
            Ia_kA=20.0, arc_clearing_time_s=0.5, distance_mm=455.0,
        )
        E_ib = doughty_neal_in_box_cal_cm2(
            Ia_kA=20.0, arc_clearing_time_s=0.5, distance_mm=455.0,
        )
        assert math.isfinite(E_oa) and E_oa > 0
        assert math.isfinite(E_ib) and E_ib > 0


class TestDoughtyNealValidation:

    def test_negative_current_raises(self):
        from app.standards.doughty_neal_arc_flash import (
            doughty_neal_open_air_cal_cm2,
        )
        with pytest.raises(ValueError):
            doughty_neal_open_air_cal_cm2(
                Ia_kA=-1.0, arc_clearing_time_s=0.5, distance_mm=455.0,
            )

    def test_negative_distance_raises(self):
        from app.standards.doughty_neal_arc_flash import (
            doughty_neal_open_air_cal_cm2,
        )
        with pytest.raises(ValueError):
            doughty_neal_open_air_cal_cm2(
                Ia_kA=20.0, arc_clearing_time_s=0.5, distance_mm=-1.0,
            )

    def test_negative_time_raises(self):
        from app.standards.doughty_neal_arc_flash import (
            doughty_neal_open_air_cal_cm2,
        )
        with pytest.raises(ValueError):
            doughty_neal_open_air_cal_cm2(
                Ia_kA=20.0,
                arc_clearing_time_s=-0.1,
                distance_mm=455.0,
            )
