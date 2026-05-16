"""
tests/test_pp_v3_0_3_decay.py — v3.0.3 Sprint B.4.

Generator/Sync Motor decay step + Recalculate Trip Time.

Conforme PTW Tutorial §Part 5 p. 136-137:

* Reduce Generator/Sync Motor Fault Contribution — decay step
  (e.g., 1000% → 300% após 10 cycles)
* Recalculate Trip Time using reduced current
* Induction Motor exclude after N cycles + hp threshold

Anti-alucinação: cita Tutorial §Part 5 p. 136-138.

Reference: PTW Tutorial §Part 5 p. 136-138; A_Fault §1.2.5 p. 1-8.
"""

from __future__ import annotations

import pytest


# ===========================================================================
# Sprint B.4.A — gen_sync_decay_step()
# ===========================================================================


class TestGenSyncDecay:

    def test_decay_at_t_zero_returns_initial(self):
        """t=0: corrente = subtransient (sem decay)."""
        from app.postprocessor.fault_decay import gen_sync_decay_step
        i = gen_sync_decay_step(
            i_subtransient_pct=1000.0,  # 1000% (10× rated)
            i_steady_pct=300.0,         # 300% (3× rated)
            decay_time_constant_cycles=5.0,
            current_cycle=0.0,
        )
        assert i == 1000.0

    def test_decay_at_long_time_approaches_steady(self):
        """t→∞: corrente → steady-state."""
        from app.postprocessor.fault_decay import gen_sync_decay_step
        i = gen_sync_decay_step(
            i_subtransient_pct=1000.0,
            i_steady_pct=300.0,
            decay_time_constant_cycles=5.0,
            current_cycle=100.0,  # muito tempo
        )
        # Muito perto de 300% (steady)
        assert i == pytest.approx(300.0, rel=0.01)

    def test_decay_at_one_time_constant(self):
        """t = τ: corrente decaiu por (1/e) entre subtrans e steady."""
        from app.postprocessor.fault_decay import gen_sync_decay_step
        import math
        i_sub = 1000.0
        i_ss = 300.0
        tau = 5.0
        i = gen_sync_decay_step(
            i_subtransient_pct=i_sub,
            i_steady_pct=i_ss,
            decay_time_constant_cycles=tau,
            current_cycle=tau,
        )
        # i(τ) = i_ss + (i_sub - i_ss)·exp(-1) = 300 + 700·0.368 = 557.5
        expected = i_ss + (i_sub - i_ss) * math.exp(-1.0)
        assert i == pytest.approx(expected, rel=1e-9)

    def test_invalid_negative_time_constant_raises(self):
        """τ ≤ 0 não físico."""
        from app.postprocessor.fault_decay import gen_sync_decay_step
        with pytest.raises(ValueError):
            gen_sync_decay_step(1000.0, 300.0, decay_time_constant_cycles=-1.0, current_cycle=0.0)


# ===========================================================================
# Sprint B.4.B — induction_motor_exclude()
# ===========================================================================


class TestInductionMotorExclude:

    def test_below_50hp_excluded_after_first_cycle(self):
        """
        §A_Fault Tab §1.2.5 p. 1-8: ind motor < 50 hp → neglect first-cycle.
        Para Tutorial §Part 5 p. 138, ind < 50hp após 1 cycle = excluído.
        """
        from app.postprocessor.fault_decay import induction_motor_excluded
        assert induction_motor_excluded(hp=25.0, cycles_after_fault=1.5) is True

    def test_large_motor_kept_in_first_cycle(self):
        """≥ 50 hp: incluso no first-cycle."""
        from app.postprocessor.fault_decay import induction_motor_excluded
        assert induction_motor_excluded(hp=100.0, cycles_after_fault=0.5) is False

    def test_large_motor_excluded_after_30_cycles(self):
        """
        §Part 5 p. 138: motor ind > 50 hp normalmente excluído após
        ~30 cycles (steady state em 0.5 sec).
        """
        from app.postprocessor.fault_decay import induction_motor_excluded
        assert induction_motor_excluded(hp=100.0, cycles_after_fault=30.0) is True


# ===========================================================================
# Sprint B.4.C — recalculate_trip_time()
# ===========================================================================


class TestRecalculateTripTime:

    def test_simple_inverse_curve_higher_current_faster(self):
        """Curva inversa: corrente maior → trip mais rápido."""
        from app.postprocessor.fault_decay import recalculate_trip_time
        # Curva extremely inverse simplificada: t = K / (I/Ipickup - 1)
        def inverse_curve(i_per_pickup: float) -> float:
            if i_per_pickup <= 1.0:
                return float('inf')
            return 28.2 / (i_per_pickup**2 - 1)
        t_high = recalculate_trip_time(curve=inverse_curve, i_per_pickup=10.0)
        t_low = recalculate_trip_time(curve=inverse_curve, i_per_pickup=2.0)
        assert t_high < t_low

    def test_below_pickup_returns_infinity(self):
        """I < Ipickup → relé não opera (∞ trip time)."""
        from app.postprocessor.fault_decay import recalculate_trip_time
        def inverse_curve(i_per_pickup: float) -> float:
            if i_per_pickup <= 1.0:
                return float('inf')
            return 1.0 / (i_per_pickup - 1)
        t = recalculate_trip_time(curve=inverse_curve, i_per_pickup=0.5)
        assert t == float('inf')
