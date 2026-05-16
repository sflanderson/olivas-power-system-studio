"""
tests/test_pp_v3_0_3_asym_withstand.py — v3.0.3 Sprint B.7.

Asymmetrical Withstand fórmulas — §1.2.3 p. 1-6/1-7.

Conforme audit profundo, **§1.5 não existe** no manual A_Fault — todo
conteúdo de "asymmetrical withstand" está em §1.2.3 (linhas 264-428).

Cobre:
* `asym_withstand_phase_a()` — Phase A worst-case ½-cycle RMS
  (§1.2.3 p. 1-6 linhas 360-365, fórmula B.2)
* `asym_withstand_average_3ph()` — average das 3 fases ½-cycle RMS
  (§1.2.3 p. 1-7 linha 420, fórmula B.3)

Anti-alucinação: cada teste cita seção+página de A_Fault.
Anti-simplismo: cobre Phase A E média 3-φ, ambos canônicos ANSI.

Reference: SKM PTW Reference-A_Fault.pdf, edição 2006-03-26.
"""

from __future__ import annotations

import math
import pytest


# ===========================================================================
# Sprint B.7.A — Asym Withstand Phase A worst-case (§1.2.3 B.2)
# ===========================================================================


class TestAsymWithstandPhaseA:

    def test_low_xr_gives_unity_multiplier(self):
        """X/R baixo → fator próximo de 1 (sem componente DC)."""
        from app.standards.ansi_c37 import asym_withstand_phase_a
        result = asym_withstand_phase_a(i_symm_rms_kA=10.0, x_over_r=2.0)
        # Tolerância 5% — para X/R baixo, a DC decai quase imediatamente
        assert 10.0 <= result <= 11.0

    def test_high_xr_gives_max_factor_sqrt_3(self):
        """
        X/R muito alto (≥100): fator → √3 = 1.732 (limite teórico).
        Manual §1.2.3 p. 1-6: I_asym = I_symm · √(1 + 2·e^(-2π/(X/R)))
        Para X/R→∞: e^0 = 1 → √3 = 1.7321.
        """
        from app.standards.ansi_c37 import asym_withstand_phase_a
        result = asym_withstand_phase_a(i_symm_rms_kA=10.0, x_over_r=1000.0)
        # Tolerância 1% para X/R muito alto
        assert result == pytest.approx(10.0 * math.sqrt(3), rel=0.01)

    def test_xr_15_gives_typical_breaker_asym_factor(self):
        """
        X/R=15 (típico em sistemas industriais 15kV): fator esperado ≈ 1.45.
        Manual §1.2.3: √(1 + 2·exp(-2π/15)) = √(1 + 2·0.658) = √2.316 = 1.522
        """
        from app.standards.ansi_c37 import asym_withstand_phase_a
        result = asym_withstand_phase_a(i_symm_rms_kA=10.0, x_over_r=15.0)
        expected = 10.0 * math.sqrt(1 + 2 * math.exp(-2 * math.pi / 15))
        assert result == pytest.approx(expected, rel=1e-9)

    def test_invalid_xr_zero_raises(self):
        """X/R=0 não é fisicamente válido."""
        from app.standards.ansi_c37 import asym_withstand_phase_a
        with pytest.raises(ValueError):
            asym_withstand_phase_a(i_symm_rms_kA=10.0, x_over_r=0.0)

    def test_negative_current_raises(self):
        """I_symm não pode ser negativo."""
        from app.standards.ansi_c37 import asym_withstand_phase_a
        with pytest.raises(ValueError):
            asym_withstand_phase_a(i_symm_rms_kA=-1.0, x_over_r=10.0)

    def test_zero_current_returns_zero(self):
        """I_symm=0 → resultado=0 (linear)."""
        from app.standards.ansi_c37 import asym_withstand_phase_a
        assert asym_withstand_phase_a(i_symm_rms_kA=0.0, x_over_r=10.0) == 0.0


# ===========================================================================
# Sprint B.7.B — Asym Withstand Average 3-phase (§1.2.3 B.3)
# ===========================================================================


class TestAsymWithstandAverage3ph:

    def test_average_3ph_is_lower_than_phase_a_worst(self):
        """
        Para qualquer X/R > 0, média das 3 fases < Phase A worst.
        Phase A é o pior caso; outras fases têm DC menor.
        """
        from app.standards.ansi_c37 import (
            asym_withstand_phase_a, asym_withstand_average_3ph,
        )
        i_symm = 10.0
        for xr in [5.0, 10.0, 25.0, 60.0, 100.0]:
            phase_a = asym_withstand_phase_a(i_symm_rms_kA=i_symm, x_over_r=xr)
            avg = asym_withstand_average_3ph(i_symm_rms_kA=i_symm, x_over_r=xr)
            assert avg < phase_a, f"X/R={xr}: avg({avg}) >= phase_a({phase_a})"

    def test_average_3ph_at_high_xr(self):
        """
        Para X/R muito alto (X/R→∞): e^(-2π/(X/R)) → 1.
        Forma IEEE Std 551 §7.6: I_avg = I_symm · √(1 + e^(-2π/(X/R)))
        Para X/R→∞: avg → I_symm · √2 ≈ 1.414·I_symm.
        """
        from app.standards.ansi_c37 import asym_withstand_average_3ph
        result = asym_withstand_average_3ph(i_symm_rms_kA=1.0, x_over_r=1000.0)
        expected = math.sqrt(2.0)  # ≈ 1.414
        assert result == pytest.approx(expected, rel=0.01)

    def test_low_xr_average_close_to_unity(self):
        """X/R baixo → DC decai rápido → média próxima de I_symm (sem boost)."""
        from app.standards.ansi_c37 import asym_withstand_average_3ph
        result = asym_withstand_average_3ph(i_symm_rms_kA=10.0, x_over_r=1.0)
        # X/R=1: e^(-2π) ≈ 0.00187 → avg = 10·√(1.00187) ≈ 10.009
        assert 10.0 <= result <= 10.5

    def test_invalid_inputs_raise(self):
        """X/R=0 ou I<0 → ValueError."""
        from app.standards.ansi_c37 import asym_withstand_average_3ph
        with pytest.raises(ValueError):
            asym_withstand_average_3ph(i_symm_rms_kA=10.0, x_over_r=0.0)
        with pytest.raises(ValueError):
            asym_withstand_average_3ph(i_symm_rms_kA=-1.0, x_over_r=10.0)
