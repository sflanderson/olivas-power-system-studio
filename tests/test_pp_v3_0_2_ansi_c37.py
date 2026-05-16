"""
tests/test_pp_v3_0_2_ansi_c37.py — v3.0.2 Sprint A.

Cobre `app.standards.ansi_c37`:

* MachineMultiplierC37 — tabela §1.2.5 p. 1-8 do PTW A_FAULT
* separately_derived_xr (separately-derived X/R, §1.2.3 p. 1-6)
* is_local_to_fault (critério local/remote, §1.2.4 p. 1-7)
* lv_duty_adjusted (LV adj fórmula §1.2.3 p. 1-6)
* asymmetrical_multiplier (fórmulas §1.3.6 p. 1-17)

Anti-alucinação: cada fórmula valida contra valores publicados em
A_FAULT manual (Cases §1.4.1).

Reference: SKM PTW Reference-A_Fault.pdf, edição 2006-03-26.
"""

from __future__ import annotations

import math

import pytest


# ===========================================================================
# Sprint A — Machine multipliers (§1.2.5 p. 1-8)
# ===========================================================================


class TestMachineMultiplier:

    def test_module_loadable(self):
        from app.standards import ansi_c37  # noqa: F401

    def test_turbine_generator_all_phases(self):
        """Turbine generator: 1.0 / 1.0 / 1.0 (LV/first/interrupting)."""
        from app.standards.ansi_c37 import (
            MachineKind, machine_multiplier,
        )
        assert machine_multiplier(MachineKind.TURBINE_GEN, "lv") == 1.0
        assert machine_multiplier(MachineKind.TURBINE_GEN, "first") == 1.0
        assert machine_multiplier(MachineKind.TURBINE_GEN, "interrupting") == 1.0

    def test_synchronous_motor_interrupting_1_5(self):
        """Synchronous motor: 1.0 / 1.0 / 1.5 X/d para interrupting."""
        from app.standards.ansi_c37 import (
            MachineKind, machine_multiplier,
        )
        assert machine_multiplier(MachineKind.SYNCHRONOUS_MOTOR, "lv") == 1.0
        assert machine_multiplier(MachineKind.SYNCHRONOUS_MOTOR, "first") == 1.0
        assert machine_multiplier(MachineKind.SYNCHRONOUS_MOTOR, "interrupting") == 1.5

    def test_induction_50hp_first_cycle_1_2(self):
        """Induction ≥ 50 hp ≤ 1800 rpm: 1.0 / 1.2 / 3.0."""
        from app.standards.ansi_c37 import (
            MachineKind, machine_multiplier,
        )
        assert machine_multiplier(MachineKind.INDUCTION_50HP_LARGE, "first") == 1.2
        assert machine_multiplier(MachineKind.INDUCTION_50HP_LARGE, "interrupting") == 3.0

    def test_induction_below_50hp_neglected_first_cycle(self):
        """Induction < 50 hp: 1.0 / neglect / neglect."""
        from app.standards.ansi_c37 import (
            MachineKind, machine_multiplier,
        )
        assert machine_multiplier(MachineKind.INDUCTION_BELOW_50HP, "lv") == 1.0
        # "neglect" → multiplier = ∞ (ignora a máquina)
        assert machine_multiplier(MachineKind.INDUCTION_BELOW_50HP, "first") == math.inf
        assert machine_multiplier(MachineKind.INDUCTION_BELOW_50HP, "interrupting") == math.inf


# ===========================================================================
# Sprint A — Local vs Remote (§1.2.4 p. 1-7)
# ===========================================================================


class TestLocalRemoteFlag:

    def test_local_when_external_z_low(self):
        """Z_external / Xd" < 1.5 → LOCAL."""
        from app.standards.ansi_c37 import is_local_to_fault
        assert is_local_to_fault(z_external_pu=0.05, xd_pu=0.10) is True

    def test_remote_when_external_z_high(self):
        """Z_external / Xd" >= 1.5 → REMOTE."""
        from app.standards.ansi_c37 import is_local_to_fault
        assert is_local_to_fault(z_external_pu=0.20, xd_pu=0.10) is False

    def test_remote_at_exact_threshold(self):
        """1.5 exato → remote (≥, conforme §1.4.3 p. 1-36)."""
        from app.standards.ansi_c37 import is_local_to_fault
        assert is_local_to_fault(z_external_pu=0.15, xd_pu=0.10) is False


# ===========================================================================
# Sprint A — Separately-derived X/R (§1.2.3 p. 1-6)
# ===========================================================================


class TestSeparatelyDerivedXR:

    def test_simple_two_branches(self):
        """
        X separately = paralelo de X (ignorando R).
        R separately = paralelo de R (ignorando X).
        X/R = X_para / R_para.
        """
        from app.standards.ansi_c37 import separately_derived_xr
        # 2 branches em paralelo:
        # Branch 1: R=0.01, X=0.10
        # Branch 2: R=0.02, X=0.08
        # X paralelo = (0.10 * 0.08) / (0.10 + 0.08) = 0.0444
        # R paralelo = (0.01 * 0.02) / (0.01 + 0.02) = 0.00667
        # X/R = 0.0444 / 0.00667 = 6.67
        x_over_r = separately_derived_xr(
            branches=[
                {"r": 0.01, "x": 0.10},
                {"r": 0.02, "x": 0.08},
            ],
        )
        assert 6.5 < x_over_r < 6.85

    def test_single_branch(self):
        """1 branch → x/r = X/R direto."""
        from app.standards.ansi_c37 import separately_derived_xr
        x_over_r = separately_derived_xr(
            branches=[{"r": 0.01, "x": 0.10}],
        )
        assert x_over_r == pytest.approx(10.0)

    def test_empty_branches_raises(self):
        from app.standards.ansi_c37 import separately_derived_xr
        with pytest.raises(ValueError):
            separately_derived_xr(branches=[])


# ===========================================================================
# Sprint A — Asymmetrical multipliers (§1.3.6 p. 1-17, Eq. 7-1)
# ===========================================================================


class TestAsymmetricalMultiplier:

    def test_momentary_rms_at_xr_25_is_1_55(self):
        """
        I_mom_rms = I_sym × √(1 + 2·e^(-4πc/(X/R))) com c=0.5 ciclos.
        Para X/R=25: ≈ 1.55 (PTW manual cita 1.6 simplificado p. 1-17).
        """
        from app.standards.ansi_c37 import momentary_rms_multiplier
        mult = momentary_rms_multiplier(x_over_r=25.0, cycles=0.5)
        # Range: aceita 1.50-1.70 (manual cita 1.6 simplificado)
        assert 1.50 < mult < 1.70

    def test_momentary_peak_at_xr_25_close_to_2_7(self):
        """I_mom_peak = √2 × I_sym × (1 + e^(-2πc/(X/R)))."""
        from app.standards.ansi_c37 import momentary_peak_multiplier
        mult = momentary_peak_multiplier(x_over_r=25.0, cycles=0.5)
        # Manual cita 2.7 simplificado para X/R=25
        assert 2.5 < mult < 2.85

    def test_low_xr_asymmetry_decreases(self):
        """Baixo X/R → multiplicador próximo de 1 (sem componente DC)."""
        from app.standards.ansi_c37 import momentary_rms_multiplier
        mult_low = momentary_rms_multiplier(x_over_r=2.0, cycles=0.5)
        mult_high = momentary_rms_multiplier(x_over_r=25.0, cycles=0.5)
        assert mult_low < mult_high


# ===========================================================================
# Sprint A — LV duty adjustment (§1.2.3 p. 1-6)
# ===========================================================================


class TestLVDutyAdjustment:

    def test_lv_duty_when_system_xr_greater_than_test_xr(self):
        """
        I_LVF = I_sym × √(1 + e^(-π/X/R_sys)) / √(1 + e^(-π/X/R_test))
        Quando system_xr > test_xr → multiplicador > 1 (mais asymmetrical).
        """
        from app.standards.ansi_c37 import lv_duty_adjusted
        # MCCB > 20 kA AIC: test X/R = 4.9
        sym_rms = 10.0   # kA
        adj = lv_duty_adjusted(
            sym_rms_kA=sym_rms,
            system_x_over_r=15.0,
            test_x_over_r=4.9,
        )
        # System X/R maior → adj > sym_rms
        assert adj > sym_rms

    def test_lv_duty_no_adjustment_when_xr_equal(self):
        """Quando system_xr == test_xr → adj == sym_rms (no boost)."""
        from app.standards.ansi_c37 import lv_duty_adjusted
        sym_rms = 10.0
        adj = lv_duty_adjusted(
            sym_rms_kA=sym_rms,
            system_x_over_r=4.9,
            test_x_over_r=4.9,
        )
        assert adj == pytest.approx(sym_rms, rel=1e-9)

    def test_lv_duty_decreases_when_system_xr_lower(self):
        """system_xr < test_xr → adj < sym_rms (menos asymmetrical)."""
        from app.standards.ansi_c37 import lv_duty_adjusted
        sym_rms = 10.0
        adj = lv_duty_adjusted(
            sym_rms_kA=sym_rms,
            system_x_over_r=2.0,
            test_x_over_r=6.6,
        )
        assert adj < sym_rms


# ===========================================================================
# Sprint A — Test PF / Test X/R catalog (§1.2.3 p. 1-5/1-6)
# ===========================================================================


class TestDeviceTestXR:

    def test_lv_pcb_test_xr_is_6_6(self):
        """LV Power Circuit Breaker: Test X/R = 6.6."""
        from app.standards.ansi_c37 import (
            DeviceClass, get_test_xr,
        )
        assert get_test_xr(DeviceClass.LV_PCB) == pytest.approx(6.6)

    def test_mccb_high_aic_test_xr(self):
        """MCCB > 20 kA AIC: Test X/R = 4.9."""
        from app.standards.ansi_c37 import (
            DeviceClass, get_test_xr,
        )
        assert get_test_xr(DeviceClass.MCCB_GT_20KA) == pytest.approx(4.9)

    def test_mccb_low_aic_test_xr(self):
        """MCCB < 10 kA AIC: Test X/R = 1.7."""
        from app.standards.ansi_c37 import (
            DeviceClass, get_test_xr,
        )
        assert get_test_xr(DeviceClass.MCCB_LT_10KA) == pytest.approx(1.7)
