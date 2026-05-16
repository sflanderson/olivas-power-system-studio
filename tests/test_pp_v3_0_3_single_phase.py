"""
tests/test_pp_v3_0_3_single_phase.py — v3.0.3 Sprint B.5.

Single-phase Mid-Tap Transformer + per-phase load.

Conforme PTW Tutorial §Part 9 p. 247-252 (Single-phase Mid-Tap pole mount
transformer 100 kVA 240 V):

* TX 1φ split-phase: 240 V L-L → 120 V L-N (cada metade)
* Per-phase load (Phase A only, etc.)
* Phase A/B/C balance check

Anti-alucinação: cita Tutorial §Part 9 p. 247-252.
Anti-simplismo: cobre split-phase + per-phase loads + balance.

Reference: PTW Tutorial §Part 9 p. 247-252.
"""

from __future__ import annotations

import pytest


# ===========================================================================
# Sprint B.5.A — split_phase_secondary_voltages()
# ===========================================================================


class TestSplitPhaseSecondaryVoltages:

    def test_240v_primary_gives_120_120_240(self):
        """
        §Tutorial Part 9 p. 247-250: TX 1φ Mid-Tap 100 kVA 240 V.
        L-L = 240 V; L-N (Phase A−Neutral, Phase B−Neutral) = 120 V cada.
        """
        from app.standards.single_phase import split_phase_secondary_voltages
        v_an, v_bn, v_ll = split_phase_secondary_voltages(v_primary_v=240.0)
        assert v_an == pytest.approx(120.0)
        assert v_bn == pytest.approx(120.0)
        assert v_ll == pytest.approx(240.0)

    def test_480v_primary_gives_240_240_480(self):
        """480 V primary → 240 V L-N each, 480 V L-L."""
        from app.standards.single_phase import split_phase_secondary_voltages
        v_an, v_bn, v_ll = split_phase_secondary_voltages(v_primary_v=480.0)
        assert v_an == pytest.approx(240.0)
        assert v_bn == pytest.approx(240.0)
        assert v_ll == pytest.approx(480.0)

    def test_l_n_voltages_sum_to_l_l(self):
        """
        Invariante físico: V_AN + V_BN = V_LL (Phase A e B em oposição
        no mid-tap secundário).
        """
        from app.standards.single_phase import split_phase_secondary_voltages
        for v_pri in [120.0, 240.0, 480.0, 4160.0]:
            v_an, v_bn, v_ll = split_phase_secondary_voltages(v_primary_v=v_pri)
            assert v_an + v_bn == pytest.approx(v_ll)

    def test_negative_voltage_raises(self):
        """Voltagem negativa não é física."""
        from app.standards.single_phase import split_phase_secondary_voltages
        with pytest.raises(ValueError):
            split_phase_secondary_voltages(v_primary_v=-100.0)


# ===========================================================================
# Sprint B.5.B — PerPhaseLoad + per_phase_balance_factor()
# ===========================================================================


class TestPerPhaseLoad:

    def test_per_phase_load_construction(self):
        """LOAD-0002 100 A only on Phase A (§Part 9 p. 250)."""
        from app.standards.single_phase import PerPhaseLoad
        load = PerPhaseLoad(
            phase_a_amps=100.0,
            phase_b_amps=0.0,
            phase_c_amps=0.0,
        )
        assert load.phase_a_amps == 100.0
        assert load.is_balanced is False

    def test_balanced_load_detected(self):
        """3-φ balanced: A=B=C → is_balanced=True."""
        from app.standards.single_phase import PerPhaseLoad
        load = PerPhaseLoad(
            phase_a_amps=50.0,
            phase_b_amps=50.0,
            phase_c_amps=50.0,
        )
        assert load.is_balanced is True

    def test_unbalanced_load_detected(self):
        """Phase A only → is_balanced=False."""
        from app.standards.single_phase import PerPhaseLoad
        load = PerPhaseLoad(
            phase_a_amps=100.0,
            phase_b_amps=0.0,
            phase_c_amps=0.0,
        )
        assert load.is_balanced is False

    def test_balance_factor_zero_for_balanced(self):
        """Balance factor: 0 = perfeito balanced; 1 = totalmente unbalanced."""
        from app.standards.single_phase import PerPhaseLoad
        load = PerPhaseLoad(
            phase_a_amps=50.0,
            phase_b_amps=50.0,
            phase_c_amps=50.0,
        )
        assert load.unbalance_factor == pytest.approx(0.0)

    def test_balance_factor_high_for_phase_a_only(self):
        """Phase A only com B=C=0: unbalance_factor próximo de 1."""
        from app.standards.single_phase import PerPhaseLoad
        load = PerPhaseLoad(
            phase_a_amps=100.0,
            phase_b_amps=0.0,
            phase_c_amps=0.0,
        )
        # Max deviation from average (33.3) / max = 66.7/100 = 0.667
        assert load.unbalance_factor > 0.5

    def test_negative_current_raises(self):
        """Corrente negativa não é física."""
        from app.standards.single_phase import PerPhaseLoad
        with pytest.raises(ValueError):
            PerPhaseLoad(
                phase_a_amps=-1.0, phase_b_amps=0.0, phase_c_amps=0.0,
            )

    def test_total_current_sum_of_phases(self):
        """Total current = soma das 3 fases."""
        from app.standards.single_phase import PerPhaseLoad
        load = PerPhaseLoad(
            phase_a_amps=100.0,
            phase_b_amps=50.0,
            phase_c_amps=25.0,
        )
        assert load.total_amps == 175.0

    def test_classmethod_phase_only(self):
        """Constructor helper: PerPhaseLoad.phase_only("A", 100.0)."""
        from app.standards.single_phase import PerPhaseLoad
        load = PerPhaseLoad.phase_only("A", amps=100.0)
        assert load.phase_a_amps == 100.0
        assert load.phase_b_amps == 0.0
        assert load.phase_c_amps == 0.0
