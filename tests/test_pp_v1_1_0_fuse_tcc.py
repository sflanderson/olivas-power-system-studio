"""
tests.test_pp_v1_1_0_fuse_tcc — testes do TCC duplo
para fusíveis (melt + clear envelopes), v1.1.0.

Cobertura
==========

1. **FuseTCCCurve API**:
   - melt_time_at_current() retorna inf abaixo do pickup
   - clear_time_at_current() = melt × clear_ratio (≥1)
   - Curva monotônica decrescente: I↑ → t↓
   - melt_points()/clear_points() geram pontos válidos para plot

2. **FuseClass coverage**:
   - 8 classes (gG, gM, aM, K, T, J, RK1, RK5) computam sem crashar

3. **Coordenação fusível-fusível**:
   - check_fuse_fuse_coordination() retorna pass/fail consistente
   - 2:1 ratio in In passa com folga (margin > 25%)
   - 1.1:1 ratio falha em fault baixo (margin insuficiente)

4. **Coord fusível-relé** (CCM bucket pattern):
   - check_fuse_relay_coordination() integra TCCCurve do relé
   - Reutiliza estrutura FuseFuseCoordinationCheck

Cobertura normativa testada
============================

* IEC 60269-1:2014 — pickup factors e expoentes
* IEEE 242-2001 §15.5.4 — 25% I²t margin para fuse-fuse
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_curves import (
    CurveType,
    FuseClass,
    FuseFuseCoordinationCheck,
    FuseTCCCurve,
    TCCCurve,
    check_fuse_fuse_coordination,
    check_fuse_relay_coordination,
)


# ---------------------------------------------------------------------------
# FuseTCCCurve — comportamento básico
# ---------------------------------------------------------------------------


class TestFuseTCCCurveBasics:

    def test_below_pickup_returns_inf(self):
        f = FuseTCCCurve(
            fuse_id="F1",
            fuse_class=FuseClass.gG,
            rated_current_A=100.0,
        )
        # Pickup factor for gG = 1.5 → não funde abaixo de 150A
        assert math.isinf(f.melt_time_at_current(100.0))
        assert math.isinf(f.melt_time_at_current(140.0))
        assert math.isinf(f.clear_time_at_current(100.0))

    def test_clear_is_slower_than_melt(self):
        f = FuseTCCCurve(
            fuse_id="F1",
            fuse_class=FuseClass.gG,
            rated_current_A=100.0,
        )
        for I in (200, 500, 1000, 5000):
            t_m = f.melt_time_at_current(I)
            t_c = f.clear_time_at_current(I)
            assert t_c > t_m, (
                f"clear deveria ser MAIOR que melt em I={I}A: "
                f"melt={t_m:.4g}, clear={t_c:.4g}"
            )

    def test_curve_is_monotonically_decreasing(self):
        f = FuseTCCCurve(
            fuse_id="F1",
            fuse_class=FuseClass.gG,
            rated_current_A=100.0,
        )
        currents = [200, 300, 500, 1000, 2000, 5000, 10000]
        prev_t = float("inf")
        for I in currents:
            t = f.melt_time_at_current(I)
            assert t < prev_t, (
                f"curva deveria ser decrescente — em I={I}A "
                f"t={t:.4g} ≥ t_anterior={prev_t:.4g}"
            )
            prev_t = t

    def test_melt_points_log_log(self):
        f = FuseTCCCurve(
            fuse_id="F1",
            fuse_class=FuseClass.gG,
            rated_current_A=100.0,
        )
        pts = f.melt_points(i_min_A=10, i_max_A=10000, n_points=50)
        # deve ter pontos (a partir do pickup)
        assert len(pts) > 30
        # cada ponto é (I, t) com t finito e positivo
        for I, t in pts:
            assert math.isfinite(t)
            assert t > 0

    def test_clear_points_log_log(self):
        f = FuseTCCCurve(
            fuse_id="F1",
            fuse_class=FuseClass.gG,
            rated_current_A=100.0,
        )
        pts = f.clear_points(i_min_A=10, i_max_A=10000, n_points=50)
        assert len(pts) > 30


# ---------------------------------------------------------------------------
# FuseClass — todas as classes computam
# ---------------------------------------------------------------------------


class TestFuseClassCoverage:

    @pytest.mark.parametrize("fuse_class", list(FuseClass))
    def test_each_class_computes_without_crash(self, fuse_class):
        f = FuseTCCCurve(
            fuse_id=f"F-{fuse_class.value}",
            fuse_class=fuse_class,
            rated_current_A=100.0,
        )
        # Pickup factor varia por classe (1.5–1.6) — usar 5×In
        # pra estar bem acima do pickup pra qualquer classe.
        t_m = f.melt_time_at_current(500.0)
        t_c = f.clear_time_at_current(500.0)
        assert math.isfinite(t_m)
        assert math.isfinite(t_c)
        assert t_c >= t_m  # clear nunca é mais rápido que melt


# ---------------------------------------------------------------------------
# Fuse-Fuse coordination
# ---------------------------------------------------------------------------


class TestFuseFuseCoordination:

    def test_2to1_ratio_passes_easily(self):
        # In_up = 200A, In_dn = 100A: relação 2:1, margem grande
        up = FuseTCCCurve("F-MAIN", FuseClass.gG, 200.0)
        dn = FuseTCCCurve("F-FEEDER", FuseClass.gG, 100.0)
        chk = check_fuse_fuse_coordination(up, dn, fault_current_A=2000)
        assert chk.passes is True
        assert chk.margin_pct > 100, (
            f"esperava margin >100%, obteve {chk.margin_pct:.1f}%"
        )

    def test_close_ratio_fails_or_marginal(self):
        # In_up = 110A, In_dn = 100A: razão 1.1×, margem mínima.
        # gG p=2 → t_melt(I, 110A) / t_melt(I, 100A) = (110/100)^2 = 1.21
        # Mas t_dn é × clear_ratio (1.6). Logo:
        # margin = t_up_melt - t_dn_clear
        #        = t_dn_melt × 1.21 - t_dn_melt × 1.6
        #        = t_dn_melt × (-0.39)  → NEGATIVO!
        # Em outras palavras, fusíveis muito próximos de tamanho não
        # coordenam — falha esperada.
        up = FuseTCCCurve("F-MAIN", FuseClass.gG, 110.0)
        dn = FuseTCCCurve("F-FEEDER", FuseClass.gG, 100.0)
        chk = check_fuse_fuse_coordination(up, dn, fault_current_A=1000)
        assert chk.passes is False
        assert chk.margin_pct < 25, (
            "fusíveis muito próximos NÃO devem passar"
        )

    def test_returns_dataclass_with_citation(self):
        up = FuseTCCCurve("U", FuseClass.gG, 200.0)
        dn = FuseTCCCurve("D", FuseClass.gG, 100.0)
        chk = check_fuse_fuse_coordination(up, dn, 1000)
        assert isinstance(chk, FuseFuseCoordinationCheck)
        assert "IEEE Std 242" in chk.citation
        assert "§15.5.4" in chk.citation

    def test_no_arc_returns_passes_false(self):
        # Falta abaixo do pickup → t_melt = inf → não-passa
        up = FuseTCCCurve("U", FuseClass.gG, 200.0)
        dn = FuseTCCCurve("D", FuseClass.gG, 100.0)
        # 100A é abaixo do pickup do upstream (1.5×200=300A)
        chk = check_fuse_fuse_coordination(up, dn, fault_current_A=50)
        assert chk.passes is False

    def test_higher_fault_smaller_margin_pct_for_p2(self):
        """Para curvas paralelas (mesma classe, p igual), a
        margem pct é constante — confirma o modelo."""
        up = FuseTCCCurve("U", FuseClass.gG, 200.0)
        dn = FuseTCCCurve("D", FuseClass.gG, 100.0)
        m1 = check_fuse_fuse_coordination(up, dn, 1000).margin_pct
        m2 = check_fuse_fuse_coordination(up, dn, 5000).margin_pct
        # Modelo simplificado: margem pct é a mesma porque
        # ambas curvas têm o mesmo expoente p=2.
        assert abs(m1 - m2) < 1.0

    def test_custom_margin_threshold(self):
        up = FuseTCCCurve("U", FuseClass.gG, 200.0)
        dn = FuseTCCCurve("D", FuseClass.gG, 100.0)
        # Mesma config — passa com 25% mas falha com 200%
        chk_easy = check_fuse_fuse_coordination(
            up, dn, 1000, margin_pct_required=25,
        )
        chk_strict = check_fuse_fuse_coordination(
            up, dn, 1000, margin_pct_required=200,
        )
        assert chk_easy.passes is True
        assert chk_strict.passes is False


# ---------------------------------------------------------------------------
# Fuse-Relay coordination (CCM bucket)
# ---------------------------------------------------------------------------


class TestFuseRelayCoordination:

    def test_relay_must_operate_before_fuse_melts(self):
        # Fuse upstream (200A gG), relé downstream (50/51 IEC SI)
        fuse_up = FuseTCCCurve("F-UP", FuseClass.gG, 200.0)
        relay_dn = TCCCurve(
            relay_id="R-DN",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=80.0,
            tms=0.10,  # rápido
        )
        chk = check_fuse_relay_coordination(
            fuse_up, relay_dn, fault_current_A=1500,
        )
        # Espera-se que o relé opere antes do fusível derreter
        assert chk.passes is True

    def test_slow_relay_fails_coord(self):
        fuse_up = FuseTCCCurve("F-UP", FuseClass.gG, 200.0)
        # Relé com TMS muito alto — opera DEPOIS do fusível
        relay_dn = TCCCurve(
            relay_id="R-DN",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=80.0,
            tms=10.0,  # extremamente lento
        )
        chk = check_fuse_relay_coordination(
            fuse_up, relay_dn, fault_current_A=1500,
        )
        assert chk.passes is False
