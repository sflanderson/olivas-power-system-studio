"""
tests/test_pp_v3_0_4_transformer_taps.py — v3.0.4 Sprint C.1.

Transformer Tap modeling + voltage adjustment.

Conforme PTW Reference-A_Fault.pdf §1.4.2 p. 1-31/32/33:

* TX with -2.5% primary tap → V_no-load_secondary = 1.0256 pu
* TAPS YES vs TAPS NO scenarios
* Compare 3-φ vs SLG faults (delta-wye-grounded near transformer)

Anti-alucinação: cita §1.4.2 p. 1-31/32/33 + valores PUBLICADOS:
- TAPS YES, V=1.0256: B4=19.772 kA, X/R=2.59
- TAPS NO,  V=1.0:    B4=19.360 kA, X/R=2.58
- SLG > 3-φ near delta-wye-grounded: 36.864 vs 34.795 kA

Reference: PTW Reference-A_Fault.pdf §1.4.2 p. 1-31/32/33.
"""

from __future__ import annotations

import math
import pytest


# ===========================================================================
# Sprint C.1.A — TransformerTap dataclass
# ===========================================================================


class TestTransformerTap:

    def test_default_tap_zero_percent(self):
        """Tap default = 0% (nominal)."""
        from app.standards.transformer_tap import TransformerTap
        tap = TransformerTap()
        assert tap.tap_percent == 0.0

    def test_negative_tap_increases_secondary_voltage(self):
        """
        §1.4.2 p. 1-31: tap primário -2.5% → V_secondary aumenta.
        Manual: tap=-2.5% → V_no-load = 1/(1-0.025) = 1.0256 pu
        """
        from app.standards.transformer_tap import TransformerTap
        tap = TransformerTap(tap_percent=-2.5)
        v = tap.no_load_secondary_voltage_pu(v_primary_pu=1.0)
        assert v == pytest.approx(1.0 / (1 - 0.025), rel=1e-6)
        assert v == pytest.approx(1.0256, abs=1e-3)

    def test_positive_tap_decreases_secondary_voltage(self):
        """Tap primário +2.5% → V_secondary diminui."""
        from app.standards.transformer_tap import TransformerTap
        tap = TransformerTap(tap_percent=+2.5)
        v = tap.no_load_secondary_voltage_pu(v_primary_pu=1.0)
        assert v == pytest.approx(1.0 / 1.025, rel=1e-6)
        # ≈ 0.9756

    def test_tap_zero_yields_unity(self):
        """Tap 0% → V_secondary = V_primary."""
        from app.standards.transformer_tap import TransformerTap
        tap = TransformerTap(tap_percent=0.0)
        assert tap.no_load_secondary_voltage_pu(v_primary_pu=1.0) == 1.0

    def test_invalid_tap_above_100_raises(self):
        """Tap = 100% causa divisão por zero (1 - 1.0 = 0)."""
        from app.standards.transformer_tap import TransformerTap
        with pytest.raises(ValueError):
            TransformerTap(tap_percent=100.0)

    def test_typical_taps_within_range(self):
        """Taps típicos: ±2.5%, ±5% (NEMA standard 5-step)."""
        from app.standards.transformer_tap import TransformerTap, STANDARD_NEMA_TAPS
        # NEMA standard: -5%, -2.5%, 0%, +2.5%, +5%
        assert STANDARD_NEMA_TAPS == (-5.0, -2.5, 0.0, +2.5, +5.0)


# ===========================================================================
# Sprint C.1.B — voltage_with_tap() function
# ===========================================================================


class TestVoltageWithTap:

    def test_taps_yes_scenario_minus_2_5_percent(self):
        """
        §1.4.2 p. 1-31: TAPS YES com tap=-2.5% → V_eff = 1.0256 pu.
        Manual cita: B4 fault = 19.772 kA com taps ON.
        """
        from app.standards.transformer_tap import voltage_with_tap
        v = voltage_with_tap(v_nominal_pu=1.0, tap_percent=-2.5)
        assert v == pytest.approx(1.0256, abs=1e-3)

    def test_taps_no_scenario(self):
        """§1.4.2 TAPS NO: tap ignorado → V = V_nominal."""
        from app.standards.transformer_tap import voltage_with_tap
        v = voltage_with_tap(v_nominal_pu=1.0, tap_percent=0.0)
        assert v == 1.0

    def test_voltage_higher_yields_higher_fault_current(self):
        """
        §1.4.2 invariante: V_pre-fault maior → I_fault maior (linear).
        Manual: TAPS YES (V=1.0256) → 19.772 kA vs TAPS NO (V=1.0) → 19.360 kA
        Ratio: 19.772 / 19.360 = 1.0213 ≈ 1.0256 (não exato pois X/R diff)
        """
        from app.standards.transformer_tap import voltage_with_tap
        v_taps_yes = voltage_with_tap(v_nominal_pu=1.0, tap_percent=-2.5)
        v_taps_no = voltage_with_tap(v_nominal_pu=1.0, tap_percent=0.0)
        # Para mesmo Z, I é proporcional a V
        i_ratio = v_taps_yes / v_taps_no
        manual_ratio = 19.772 / 19.360
        # Tolerância larga porque tap também muda Z efetivo
        assert i_ratio == pytest.approx(manual_ratio, abs=0.01)


# ===========================================================================
# Sprint C.1.C — SLG vs 3-phase fault comparison (§1.4.2 p. 1-33)
# ===========================================================================


class TestSlgVs3PhFault:

    def test_slg_greater_than_3ph_near_delta_wye_grounded(self):
        """
        §1.4.2 p. 1-33: em delta-wye-grounded próximo,
        I_SLG > I_3ph (manual: 36.864 vs 34.795 kA).

        Razão: I_SLG = 3·E / (Z1 + Z2 + Z0). Em delta-wye-grounded,
        Z0 é baixo (caminho de retorno via neutro), e o fator 3 no numerador
        domina, fazendo SLG > 3-phase em alguns sistemas próximos do TX.
        """
        from app.standards.transformer_tap import slg_vs_3ph_ratio
        # Z0/Z1 ratio típico para delta-wye-grounded próximo: ~0.85
        ratio = slg_vs_3ph_ratio(z0_over_z1=0.85)
        # I_SLG/I_3ph = 3 / (1 + 1 + 0.85) = 3/2.85 = 1.0526
        assert ratio > 1.0
        assert ratio == pytest.approx(3.0 / (1.0 + 1.0 + 0.85), rel=1e-6)

    def test_slg_less_than_3ph_with_high_z0(self):
        """
        Z0 muito alto (sistema isolado ou wye-wye sem grounding) →
        I_SLG << I_3ph (limite isolado → SLG ≈ 0).
        """
        from app.standards.transformer_tap import slg_vs_3ph_ratio
        ratio = slg_vs_3ph_ratio(z0_over_z1=10.0)
        # 3/(1+1+10) = 3/12 = 0.25
        assert ratio < 1.0

    def test_solidly_grounded_gives_unity_ratio(self):
        """Z0 = Z1 (sistema sólidamente aterrado simétrico) → SLG = 3-φ."""
        from app.standards.transformer_tap import slg_vs_3ph_ratio
        ratio = slg_vs_3ph_ratio(z0_over_z1=1.0)
        assert ratio == 1.0  # 3/(1+1+1) = 1

    def test_invalid_negative_z0_raises(self):
        """Z0 negativo não é físico."""
        from app.standards.transformer_tap import slg_vs_3ph_ratio
        with pytest.raises(ValueError):
            slg_vs_3ph_ratio(z0_over_z1=-1.0)


# ===========================================================================
# Sprint C.1.D — Tap configuration helper
# ===========================================================================


class TestTapConfiguration:

    def test_step_to_percent_conversion(self):
        """NEMA 5-step: step -2 → -5%, step -1 → -2.5%, step 0 → 0%, etc."""
        from app.standards.transformer_tap import TransformerTap
        for step, expected_pct in [(-2, -5.0), (-1, -2.5), (0, 0.0), (1, 2.5), (2, 5.0)]:
            tap = TransformerTap.from_nema_step(step)
            assert tap.tap_percent == expected_pct

    def test_invalid_nema_step_raises(self):
        """Step fora de [-2, 2] não é NEMA 5-step."""
        from app.standards.transformer_tap import TransformerTap
        with pytest.raises(ValueError):
            TransformerTap.from_nema_step(3)
        with pytest.raises(ValueError):
            TransformerTap.from_nema_step(-3)
