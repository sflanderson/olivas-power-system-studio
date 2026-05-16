"""
tests.test_pp_v1_2_0_tcc_damage_gamma3 — sub-sprint γ.3.

Motor thermal limit (IEC 60079-7 / NEMA MG-1 §12.45).

Validação anti-alucinação
==========================

Modelo single-time-constant: ``t = K_motor / (I/FLA)²``,
calibrado para passar por (I_LR, tE).

K_motor = tE × (I_LR/FLA)²

Cálculos validados à mão:
* FLA=100A, I_LR=600A (6×), tE=10s:
  - K = 10 × 36 = 360 (s)
  - At I=600A (LR): t = 360/36 = 10s ✓ (anchor)
  - At I=300A (3×): t = 360/9 = 40s
  - At I=1200A (12×): t = 360/144 = 2.5s

**Aceite γ.3**: 10+ testes, 100% verde, fórmula validada à mão.
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_damage import MotorThermalCurve


# ---------------------------------------------------------------------------
# Construção e validação
# ---------------------------------------------------------------------------


class TestConstruction:

    def test_constructs_with_required(self):
        m = MotorThermalCurve(
            motor_id="M1",
            fla_A=100.0,
        )
        assert m.fla_A == 100.0
        # defaults
        assert m.locked_rotor_factor == 6.0
        assert m.locked_rotor_time_s == 10.0

    def test_fla_must_be_positive(self):
        with pytest.raises(ValueError):
            MotorThermalCurve(motor_id="M", fla_A=0)
        with pytest.raises(ValueError):
            MotorThermalCurve(motor_id="M", fla_A=-100)

    def test_lr_factor_must_be_above_1(self):
        with pytest.raises(ValueError):
            MotorThermalCurve(
                motor_id="M", fla_A=100,
                locked_rotor_factor=1.0,
            )
        with pytest.raises(ValueError):
            MotorThermalCurve(
                motor_id="M", fla_A=100,
                locked_rotor_factor=0.5,
            )

    def test_te_must_be_positive(self):
        with pytest.raises(ValueError):
            MotorThermalCurve(
                motor_id="M", fla_A=100,
                locked_rotor_time_s=0,
            )

    def test_K_motor_calibration(self):
        """K = tE × (I_LR/FLA)²."""
        m = MotorThermalCurve(
            motor_id="M", fla_A=100,
            locked_rotor_factor=6.0,
            locked_rotor_time_s=10.0,
        )
        assert m.K_motor() == pytest.approx(360.0)
        # Outro motor: tE=15s, LR=8x → K = 15 × 64 = 960
        m2 = MotorThermalCurve(
            motor_id="M", fla_A=100,
            locked_rotor_factor=8.0,
            locked_rotor_time_s=15.0,
        )
        assert m2.K_motor() == pytest.approx(960.0)


# ---------------------------------------------------------------------------
# thermal_time_at_current — fórmula validada à mão
# ---------------------------------------------------------------------------


class TestFormula:
    """t = K_motor / (I/FLA)²."""

    def test_at_FLA_returns_inf(self):
        """Em FLA, motor opera contínuo."""
        m = MotorThermalCurve(motor_id="M", fla_A=100)
        assert math.isinf(m.thermal_time_at_current(100))
        # Até 1.05 × FLA também
        assert math.isinf(m.thermal_time_at_current(105))

    def test_above_1_05_FLA_finite(self):
        """Logo acima de 1.05·FLA já tem damage time finito."""
        m = MotorThermalCurve(motor_id="M", fla_A=100)
        t = m.thermal_time_at_current(110)  # 1.10·FLA
        assert math.isfinite(t)
        # K=360, I_pu=1.10: t = 360/1.21 ≈ 297.5s
        assert t == pytest.approx(360 / 1.21, rel=1e-3)

    def test_at_locked_rotor_returns_te(self):
        """Anchor: em I=I_LR, t = locked_rotor_time_s."""
        m = MotorThermalCurve(
            motor_id="M", fla_A=100,
            locked_rotor_factor=6.0,
            locked_rotor_time_s=10.0,
        )
        # I = 6 × FLA = 600A
        t = m.thermal_time_at_current(600)
        assert t == pytest.approx(10.0, rel=1e-6)

    def test_at_3x_FLA(self):
        """K=360, I_pu=3: t = 360/9 = 40s."""
        m = MotorThermalCurve(motor_id="M", fla_A=100)
        t = m.thermal_time_at_current(300)
        assert t == pytest.approx(40.0, rel=1e-6)

    def test_at_12x_FLA(self):
        """K=360, I_pu=12: t = 360/144 = 2.5s."""
        m = MotorThermalCurve(motor_id="M", fla_A=100)
        t = m.thermal_time_at_current(1200)
        assert t == pytest.approx(2.5, rel=1e-6)

    def test_inverse_square_relationship(self):
        """Dobrar I divide t por 4."""
        m = MotorThermalCurve(motor_id="M", fla_A=100)
        t1 = m.thermal_time_at_current(300)
        t2 = m.thermal_time_at_current(600)
        assert t1 / t2 == pytest.approx(4.0, rel=1e-6)

    def test_disabled_returns_inf(self):
        m = MotorThermalCurve(
            motor_id="M", fla_A=100,
            enabled=False,
        )
        assert math.isinf(m.thermal_time_at_current(500))


# ---------------------------------------------------------------------------
# Custom motor parameters
# ---------------------------------------------------------------------------


class TestCustomMotors:

    def test_motor_with_high_te(self):
        """Motor com PT100 e ventilação forçada: tE=30s."""
        m = MotorThermalCurve(
            motor_id="M-high-te",
            fla_A=100,
            locked_rotor_factor=6.0,
            locked_rotor_time_s=30.0,
        )
        # K = 30 × 36 = 1080
        # At I=600A (LR): t = 30s
        assert m.thermal_time_at_current(600) == pytest.approx(30.0, rel=1e-3)

    def test_motor_with_low_lr_factor(self):
        """Motor de soft-starter: I_LR efetivo só 4× FLA."""
        m = MotorThermalCurve(
            motor_id="M-soft",
            fla_A=100,
            locked_rotor_factor=4.0,
            locked_rotor_time_s=10.0,
        )
        # K = 10 × 16 = 160
        # At I=400A (4×LR): t = 10s ✓
        assert m.thermal_time_at_current(400) == pytest.approx(10.0, rel=1e-3)


# ---------------------------------------------------------------------------
# thermal_points (plot data)
# ---------------------------------------------------------------------------


class TestPoints:

    def test_points_finite_only(self):
        m = MotorThermalCurve(motor_id="M", fla_A=100)
        pts = m.thermal_points(i_max_A=10000, n_points=50)
        for I, t in pts:
            assert math.isfinite(t)
            assert t > 0

    def test_points_decreasing_in_t(self):
        m = MotorThermalCurve(motor_id="M", fla_A=100)
        pts = m.thermal_points(i_max_A=5000, n_points=30)
        ts = [t for _, t in pts]
        for i in range(1, len(ts)):
            assert ts[i] < ts[i - 1]
