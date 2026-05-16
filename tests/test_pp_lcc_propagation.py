"""
tests/test_pp_lcc_propagation.py — v0.25.3: frequency sweep e
extração de Z_c(ω) e A(ω) de sequência positiva — base para
fitting JMARTI (vector-fitting Gustavsen-Semlyen) em v0.25.4+.

Cobre:

* compute_frequency_sweep: 1 freq, N freqs, ordem crescente,
  rejeita zero e negativo, dedupe.
* compute_propagation_pos: Z_c real em alta f, |A| ≤ 1
  (passividade), arg(A) ∝ ωτ.
* Sanity: limite de alta frequência converge para √(L/C).
* Aceita 1 freq como caso degenerado.
"""

from __future__ import annotations

import cmath
import math

import pytest

from app.preprocessor.lcc import (
    FrequencySweep, LineGeometry, PropagationFunction,
    compute_frequency_sweep, compute_propagation_pos,
    make_3phase_geometry,
)


def _std_geom() -> LineGeometry:
    return make_3phase_geometry(
        x_a=0, y_a=15, x_b=0, y_b=12, x_c=0, y_c=9,
        radius=0.0091, R_dc_per_km=0.18,
        soil_resistivity=100.0,
    )


# ---------------------------------------------------------------------------
# compute_frequency_sweep
# ---------------------------------------------------------------------------


class TestFrequencySweep:
    def test_single_frequency(self):
        sweep = compute_frequency_sweep(_std_geom(), [60.0])
        assert sweep.n_freq == 1
        assert sweep.frequencies == (60.0,)

    def test_multiple_freqs_sorted(self):
        sweep = compute_frequency_sweep(_std_geom(), [10000, 60, 1000])
        assert sweep.frequencies == (60.0, 1000.0, 10000.0)

    def test_dedupe(self):
        sweep = compute_frequency_sweep(_std_geom(), [60, 60, 60])
        assert sweep.frequencies == (60.0,)

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="frequencies"):
            compute_frequency_sweep(_std_geom(), [])

    def test_zero_rejected(self):
        with pytest.raises(ValueError, match="> 0"):
            compute_frequency_sweep(_std_geom(), [0, 60])

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="> 0"):
            compute_frequency_sweep(_std_geom(), [-10, 60])

    def test_constants_have_correct_frequency(self):
        sweep = compute_frequency_sweep(_std_geom(), [60, 1000])
        assert sweep.constants[0].frequency == 60.0
        assert sweep.constants[1].frequency == 1000.0


# ---------------------------------------------------------------------------
# compute_propagation_pos
# ---------------------------------------------------------------------------


class TestPropagationPos:
    def test_returns_correct_dimensions(self):
        sweep = compute_frequency_sweep(_std_geom(), [60, 1000, 10000])
        prop = compute_propagation_pos(sweep, length_km=100)
        assert len(prop.Zc) == 3
        assert len(prop.A) == 3
        assert prop.length_km == 100

    def test_zc_high_frequency_limit_real(self):
        """Em f alta, Z_c → √(L/C), real puro."""
        sweep = compute_frequency_sweep(_std_geom(), [1e6])
        prop = compute_propagation_pos(sweep, length_km=100)
        Zc = prop.Zc[0]
        # |arg(Zc)| < 1° (quase real)
        assert abs(math.degrees(cmath.phase(Zc))) < 1.0

    def test_zc_high_freq_matches_lossless_z_char(self):
        """|Z_c| em alta f ≈ Z_char_pos da Bergeron (limite sem perdas)."""
        from app.preprocessor.lcc import compute_bergeron_pos_sequence
        bp = compute_bergeron_pos_sequence(_std_geom(), 100)
        sweep = compute_frequency_sweep(_std_geom(), [1e6])
        prop = compute_propagation_pos(sweep, 100)
        # |Z_c(1MHz)| ≈ Z_char_pos com 5% tolerância
        assert abs(prop.Zc[0]) == pytest.approx(bp.Z_char_pos, rel=0.05)

    def test_A_magnitude_le_one(self):
        """|A| ≤ 1 — passividade (energia não cresce na propagação)."""
        sweep = compute_frequency_sweep(_std_geom(), [60, 1000, 1e5])
        prop = compute_propagation_pos(sweep, 100)
        for A in prop.A:
            assert abs(A) <= 1.0 + 1e-9   # tolerância numérica

    def test_zero_length_rejected(self):
        sweep = compute_frequency_sweep(_std_geom(), [60])
        with pytest.raises(ValueError, match="length_km"):
            compute_propagation_pos(sweep, length_km=0)

    def test_negative_length_rejected(self):
        sweep = compute_frequency_sweep(_std_geom(), [60])
        with pytest.raises(ValueError, match="length_km"):
            compute_propagation_pos(sweep, length_km=-1)

    def test_higher_freq_more_phase_shift_in_A(self):
        """arg(A) acumula fase ∝ ω·τ → diferenças visíveis com f."""
        sweep = compute_frequency_sweep(_std_geom(), [100, 5000])
        prop = compute_propagation_pos(sweep, 100)
        phase_low = math.degrees(cmath.phase(prop.A[0]))
        phase_high = math.degrees(cmath.phase(prop.A[1]))
        # As fases devem ser diferentes (modulo 360°)
        assert phase_low != pytest.approx(phase_high, abs=1.0)

    def test_attenuation_few_percent_for_typical_line(self):
        """LT 138 kV típica: |A(60 Hz)| > 0.95 (atenuação < 5%)."""
        sweep = compute_frequency_sweep(_std_geom(), [60])
        prop = compute_propagation_pos(sweep, 100)
        assert abs(prop.A[0]) > 0.95


# ---------------------------------------------------------------------------
# Sanity acoplado: sweep + propagation usado em conjunto
# ---------------------------------------------------------------------------


class TestSweepPropagationCoupled:
    def test_attenuation_grows_with_length(self):
        """ℓ↑ → |A|↓ (mais atenuação na propagação)."""
        sweep = compute_frequency_sweep(_std_geom(), [60])
        prop_short = compute_propagation_pos(sweep, length_km=50)
        prop_long = compute_propagation_pos(sweep, length_km=500)
        assert abs(prop_short.A[0]) > abs(prop_long.A[0])

    def test_zc_independent_of_length(self):
        """Z_c não depende de comprimento."""
        sweep = compute_frequency_sweep(_std_geom(), [1e5])
        prop_50 = compute_propagation_pos(sweep, 50)
        prop_500 = compute_propagation_pos(sweep, 500)
        assert prop_50.Zc[0] == pytest.approx(prop_500.Zc[0], rel=1e-9)
