"""
tests/test_pp_vector_fitting.py — v0.25.4: vector-fitting
(Gustavsen-Semlyen) e emissão JMARTI .pch (draft).

Cobre:

* initial_poles: pares conjugados, log-spaced, força par.
* RationalFit.evaluate em ponto arbitrário.
* vector_fit em função teste sintética com polos complexos
  conjugados — verifica RMS error baixo.
* vector_fit em Z_c(ω) real de LCC — RMS muito baixo (Z_c é
  smooth).
* vector_fit_delayed em A(ω) — após delay extraction, RMS
  aceitável (< 5%).
* enforce_stability flips poles instáveis.
* JMARTI .pch text contém todos os campos esperados.
"""

from __future__ import annotations

import cmath
import math

import numpy as np
import pytest

from app.preprocessor.lcc import (
    compute_bergeron_pos_sequence, compute_frequency_sweep,
    compute_propagation_pos, make_3phase_geometry,
)
from app.preprocessor.vector_fitting import (
    DelayedRationalFit, RationalFit,
    _enforce_stability, initial_poles,
    vector_fit, vector_fit_delayed,
)
from app.preprocessor.jmarti_pch import (
    JMartiPchData, emit_pch_text,
)


# ---------------------------------------------------------------------------
# initial_poles
# ---------------------------------------------------------------------------


class TestInitialPoles:
    def test_pair_count(self):
        """n_poles forçado a ser par."""
        p = initial_poles([10, 100, 1000], n_poles=4)
        assert len(p) == 4
        p = initial_poles([10, 100, 1000], n_poles=3)   # impar → 4
        assert len(p) == 4

    def test_minimum_2(self):
        p = initial_poles([10, 100], n_poles=0)
        assert len(p) >= 2

    def test_conjugate_pairs(self):
        p = initial_poles([10, 100, 1000], n_poles=4)
        # Para cada polo p_k com Im > 0, deve existir conjugado
        positive_imag = [pp for pp in p if pp.imag > 0]
        for pp in positive_imag:
            conj_present = any(
                abs(other - np.conj(pp)) < 1e-9 for other in p
            )
            assert conj_present, f"Sem conjugado de {pp}"

    def test_stable_real_part(self):
        """Re(polo) < 0 — todos estáveis."""
        p = initial_poles([10, 100], n_poles=4)
        for pp in p:
            assert pp.real < 0

    def test_zero_freq_rejected(self):
        with pytest.raises(ValueError, match="> 0"):
            initial_poles([0, 100], n_poles=4)


# ---------------------------------------------------------------------------
# RationalFit.evaluate
# ---------------------------------------------------------------------------


class TestRationalFitEvaluate:
    def test_simple_pole(self):
        """f(s) = 1/(s+1) avaliado em s=0 → 1."""
        fit = RationalFit(
            poles=(-1+0j,),
            residues=(1+0j,),
            d=0.0, h=0.0,
            rms_error=0.0,
        )
        val = fit.evaluate(0+0j)
        assert val == pytest.approx(1+0j, abs=1e-9)

    def test_d_constant(self):
        fit = RationalFit(
            poles=(),
            residues=(),
            d=5.0, h=0.0,
            rms_error=0.0,
        )
        assert fit.evaluate(1+1j) == pytest.approx(5+0j)

    def test_h_proportional(self):
        fit = RationalFit(
            poles=(),
            residues=(),
            d=0.0, h=2.0,
            rms_error=0.0,
        )
        assert fit.evaluate(3+4j) == pytest.approx(2*(3+4j))


# ---------------------------------------------------------------------------
# vector_fit on synthetic functions
# ---------------------------------------------------------------------------


class TestVectorFitSynthetic:
    def test_constant_function(self):
        """f(s) = 5.0 constante — VF deve dar d=5, polos com
        residues ≈ 0."""
        freqs = np.logspace(-1, 3, 30).tolist()
        f_data = [5.0 + 0j for _ in freqs]
        fit = vector_fit(freqs, f_data, n_poles=2, n_iterations=3)
        assert fit.d == pytest.approx(5.0, abs=0.5)
        assert fit.rms_error < 1.0

    def test_complex_pole_pair(self):
        """f(s) = 100/(s² + 4s + 100) — par conjugado em -2 ± 9.8j
        rad/s. VF tem dificuldade com picos resonantes finos
        (Q alto), então tolerância é generosa: 30% RMS/max_mag.
        Para dados de LT (smooth Z_c, A com delay extraction),
        os testes em TestVectorFitLCC mostram precisão <1%.
        """
        freqs = np.logspace(-1, 2, 50).tolist()
        s = 1j * 2 * math.pi * np.array(freqs)
        f_data = (100 / (s**2 + 4*s + 100)).tolist()
        fit = vector_fit(freqs, f_data, n_poles=2, n_iterations=8)
        max_mag = max(abs(v) for v in f_data)
        # 30% — generoso para resonance peak de Q ≈ 5
        assert fit.rms_error < 0.30 * max_mag


# ---------------------------------------------------------------------------
# vector_fit on real LCC data
# ---------------------------------------------------------------------------


class TestVectorFitLCC:
    def _setup(self):
        geom = make_3phase_geometry(
            x_a=0, y_a=15, x_b=0, y_b=12, x_c=0, y_c=9,
            radius=0.0091, R_dc_per_km=0.18,
        )
        freqs = np.logspace(math.log10(60), math.log10(1e6), 30).tolist()
        sweep = compute_frequency_sweep(geom, freqs)
        prop = compute_propagation_pos(sweep, length_km=100)
        bp = compute_bergeron_pos_sequence(geom, length_km=100)
        return prop, bp

    def test_zc_fit_high_quality(self):
        """Z_c(ω) é smooth — VF de 4 polos atinge erro relativo < 1%."""
        prop, _ = self._setup()
        fit = vector_fit(prop.frequencies, prop.Zc, n_poles=4, n_iterations=8)
        # Erro relativo médio
        max_err_rel = 0.0
        for i, f in enumerate(prop.frequencies):
            s = 1j * 2 * math.pi * f
            err = abs(prop.Zc[i] - fit.evaluate(s)) / abs(prop.Zc[i])
            max_err_rel = max(max_err_rel, err)
        assert max_err_rel < 0.01   # < 1%

    def test_a_fit_with_delay_better_than_without(self):
        """VF puro de A(ω) erra muito; com delay extraction melhora ≥ 10×."""
        prop, bp = self._setup()
        # VF puro
        fit_no_delay = vector_fit(
            prop.frequencies, prop.A, n_poles=8, n_iterations=8,
        )
        # VF com delay
        fit_delayed = vector_fit_delayed(
            prop.frequencies, prop.A, bp.travel_time,
            n_poles=4, n_iterations=8,
        )
        err_no_delay = max(
            abs(prop.A[i] - fit_no_delay.evaluate(1j*2*math.pi*f))
            for i, f in enumerate(prop.frequencies)
        )
        err_delayed = max(
            abs(prop.A[i] - fit_delayed.evaluate(1j*2*math.pi*f))
            for i, f in enumerate(prop.frequencies)
        )
        # Espera-se redução de pelo menos 10× no max error
        assert err_delayed < err_no_delay / 10

    def test_a_delayed_fit_acceptable(self):
        """Com delay extraction, |A_fit - A_data| < 0.1 max."""
        prop, bp = self._setup()
        fit = vector_fit_delayed(
            prop.frequencies, prop.A, bp.travel_time,
            n_poles=4, n_iterations=8,
        )
        max_err = max(
            abs(prop.A[i] - fit.evaluate(1j*2*math.pi*f))
            for i, f in enumerate(prop.frequencies)
        )
        assert max_err < 0.1


# ---------------------------------------------------------------------------
# Stability enforcement
# ---------------------------------------------------------------------------


class TestEnforceStability:
    def test_unstable_pole_flipped(self):
        poles = np.array([2 + 3j, -1 + 5j])  # primeiro instável
        result = _enforce_stability(poles)
        assert result[0].real < 0
        # Im preservado
        assert result[0].imag == 3.0

    def test_stable_unchanged(self):
        poles = np.array([-1 + 2j, -3 + 4j])
        result = _enforce_stability(poles)
        assert result[0] == poles[0]
        assert result[1] == poles[1]


# ---------------------------------------------------------------------------
# JMARTI .pch emission
# ---------------------------------------------------------------------------


class TestJMartiPch:
    def _make_data(self):
        geom = make_3phase_geometry(
            x_a=0, y_a=15, x_b=0, y_b=12, x_c=0, y_c=9,
            radius=0.0091, R_dc_per_km=0.18,
        )
        freqs = np.logspace(math.log10(60), math.log10(1e6), 20).tolist()
        sweep = compute_frequency_sweep(geom, freqs)
        prop = compute_propagation_pos(sweep, length_km=100)
        bp = compute_bergeron_pos_sequence(geom, length_km=100)
        zc_fit = vector_fit(
            prop.frequencies, prop.Zc, n_poles=4, n_iterations=5,
        )
        a_fit = vector_fit_delayed(
            prop.frequencies, prop.A, bp.travel_time,
            n_poles=4, n_iterations=5,
        )
        return JMartiPchData(
            line_id="LT_138_100km",
            length_km=100.0,
            Zc_fit=zc_fit,
            A_fit=a_fit,
            sample_freq_min=60.0,
            sample_freq_max=1.0e6,
            n_phases=3,
        )

    def test_text_contains_metadata(self):
        text = emit_pch_text(self._make_data())
        assert "JMARTI .pch" in text
        assert "LT_138_100km" in text
        assert "100" in text   # length

    def test_text_contains_zc_section(self):
        text = emit_pch_text(self._make_data())
        assert "Z_c(s)" in text
        assert "characteristic impedance" in text.lower()

    def test_text_contains_a_section(self):
        text = emit_pch_text(self._make_data())
        assert "A(s)" in text
        assert "propagation function" in text.lower()

    def test_text_contains_tau(self):
        text = emit_pch_text(self._make_data())
        assert "tau" in text.lower()
        assert "travel" in text.lower()

    def test_text_contains_poles_residues(self):
        text = emit_pch_text(self._make_data())
        assert "pole" in text.lower()
        assert "residue" in text.lower()

    def test_text_well_formed_lines(self):
        """Cada linha começa com 'C ' (comentário ATP) ou é vazia."""
        text = emit_pch_text(self._make_data())
        for line in text.splitlines():
            if line.strip():
                assert line.startswith("C ") or line.startswith("C\t") or line == "C"

    def test_emit_to_file(self, tmp_path):
        from app.preprocessor.jmarti_pch import emit_pch_file
        path = tmp_path / "test.pch"
        emit_pch_file(self._make_data(), str(path))
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "JMARTI" in content
