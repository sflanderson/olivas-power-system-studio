"""
tests/test_pp_tacs_transfer.py — v0.26.2: transfer functions
s-domain (devices type-1) na seção ``/TACS HYBRID``.

Cobre:

* ``TacsTransferFunction`` dataclass (frozen, defaults).
* Helpers ``make_integrator``, ``make_derivative``,
  ``make_low_pass``, ``make_high_pass``, ``make_lead_lag``,
  ``make_pid`` — verificando coeficientes corretos.
* ``validate_tf`` — name/output/input vazios ou >6 chars,
  numerator/denominator vazios ou ordem >5, denominator todo
  zero, output_min/max coerentes.
* Pretty-printer ``render_tf_summary`` — string canônica
  human-readable.
* ``emit_tf_lines`` — formato draft com comentário, cartão
  type-1, numerator/denominator/saturation (quando aplicável).
* ``emit_tacs_section`` despachando entre TacsBlock e
  TacsTransferFunction (mistura).
"""

from __future__ import annotations

import pytest

from app.preprocessor.tacs import TacsBlock, emit_tacs_section
from app.preprocessor.tacs_tf import (
    TacsTransferFunction,
    emit_tf_lines,
    make_derivative, make_high_pass, make_integrator,
    make_lead_lag, make_low_pass, make_pid,
    render_tf_summary,
    validate_tf,
)


# ---------------------------------------------------------------------------
# TacsTransferFunction defaults
# ---------------------------------------------------------------------------


class TestTfDataclass:
    def test_minimal(self):
        tf = TacsTransferFunction(
            name="b1", output="y", input_signal="u",
            numerator=(1.0,), denominator=(1.0, 0.5),
        )
        assert tf.gain == 1.0
        assert tf.initial_output == 0.0
        assert tf.output_min is None
        assert tf.output_max is None

    def test_frozen(self):
        tf = TacsTransferFunction(
            name="a", output="y", input_signal="u",
            numerator=(1.0,), denominator=(1.0,),
        )
        with pytest.raises(Exception):
            tf.gain = 2.0  # frozen


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------


class TestMakeIntegrator:
    def test_basic_integrator(self):
        """K/s ⇒ N=(1,), D=(0,1)."""
        tf = make_integrator("int1", "u", "y", K=2.5)
        assert tf.numerator == (1.0,)
        assert tf.denominator == (0.0, 1.0)
        assert tf.gain == 2.5

    def test_with_initial(self):
        tf = make_integrator("int1", "u", "y", K=1.0, initial_output=3.7)
        assert tf.initial_output == 3.7

    def test_with_saturation(self):
        tf = make_integrator(
            "int1", "u", "y", output_min=-10, output_max=10,
        )
        assert tf.output_min == -10
        assert tf.output_max == 10


class TestMakeDerivative:
    def test_basic(self):
        """K·s ⇒ N=(0,1), D=(1,)."""
        tf = make_derivative("d1", "u", "y", K=4.0)
        assert tf.numerator == (0.0, 1.0)
        assert tf.denominator == (1.0,)
        assert tf.gain == 4.0


class TestMakeLowPass:
    def test_basic(self):
        """K/(1+τs) ⇒ N=(1,), D=(1, τ)."""
        tf = make_low_pass("lp1", "u", "y", K=1.5, tau=0.01)
        assert tf.numerator == (1.0,)
        assert tf.denominator == (1.0, 0.01)
        assert tf.gain == 1.5

    def test_zero_tau_rejected(self):
        with pytest.raises(ValueError, match="tau"):
            make_low_pass("a", "u", "y", tau=0.0)

    def test_negative_tau_rejected(self):
        with pytest.raises(ValueError, match="tau"):
            make_low_pass("a", "u", "y", tau=-0.001)


class TestMakeHighPass:
    def test_basic(self):
        """K·τs/(1+τs) ⇒ N=(0,τ), D=(1,τ)."""
        tf = make_high_pass("hp1", "u", "y", K=1.0, tau=0.05)
        assert tf.numerator == (0.0, 0.05)
        assert tf.denominator == (1.0, 0.05)


class TestMakeLeadLag:
    def test_lead(self):
        """T1 > T2 → lead (avanço de fase)."""
        tf = make_lead_lag("ll1", "u", "y", K=1.0, T1=0.1, T2=0.01)
        assert tf.numerator == (1.0, 0.1)
        assert tf.denominator == (1.0, 0.01)

    def test_lag(self):
        tf = make_lead_lag("ll1", "u", "y", K=1.0, T1=0.001, T2=0.1)
        assert tf.numerator[1] < tf.denominator[1]

    def test_zero_t2_rejected(self):
        with pytest.raises(ValueError, match="T1.*T2"):
            make_lead_lag("a", "u", "y", T1=1.0, T2=0.0)


class TestMakePid:
    def test_pid_full(self):
        """PID = Kp + Ki/s + Kd·s = (Kd·s² + Kp·s + Ki)/s."""
        tf = make_pid("p", "u", "y", Kp=2.0, Ki=10.0, Kd=0.05)
        assert tf.numerator == (10.0, 2.0, 0.05)  # ascending: Ki, Kp, Kd
        assert tf.denominator == (0.0, 1.0)

    def test_pid_p_only(self):
        tf = make_pid("p", "u", "y", Kp=3.0)
        # Ki=0, Kd=0 → numerator=(0, 3, 0)
        assert tf.numerator == (0.0, 3.0, 0.0)

    def test_pid_with_anti_windup_limits(self):
        tf = make_pid(
            "p", "u", "y", Kp=1, Ki=10, Kd=0,
            output_min=-1.0, output_max=1.0,
        )
        assert tf.output_min == -1.0
        assert tf.output_max == 1.0


# ---------------------------------------------------------------------------
# validate_tf
# ---------------------------------------------------------------------------


class TestValidateTf:
    def test_valid(self):
        tf = make_low_pass("lp", "u", "y", tau=0.01)
        assert validate_tf(tf) == []

    def test_empty_name(self):
        tf = TacsTransferFunction(
            name="", output="y", input_signal="u",
            numerator=(1.0,), denominator=(1.0,),
        )
        errs = validate_tf(tf)
        assert any("name vazio" in e for e in errs)

    def test_long_name(self):
        tf = TacsTransferFunction(
            name="abcdefgh", output="y", input_signal="u",
            numerator=(1.0,), denominator=(1.0,),
        )
        errs = validate_tf(tf)
        assert any("> 6 chars" in e for e in errs)

    def test_long_output(self):
        tf = TacsTransferFunction(
            name="ok", output="abcdefgh", input_signal="u",
            numerator=(1.0,), denominator=(1.0,),
        )
        errs = validate_tf(tf)
        assert any("output" in e and "> 6 chars" in e for e in errs)

    def test_long_input_signal(self):
        tf = TacsTransferFunction(
            name="ok", output="y", input_signal="abcdefgh",
            numerator=(1.0,), denominator=(1.0,),
        )
        errs = validate_tf(tf)
        assert any("input_signal" in e and "> 6 chars" in e for e in errs)

    def test_empty_numerator(self):
        tf = TacsTransferFunction(
            name="ok", output="y", input_signal="u",
            numerator=(), denominator=(1.0,),
        )
        errs = validate_tf(tf)
        assert any("numerator vazio" in e for e in errs)

    def test_empty_denominator(self):
        tf = TacsTransferFunction(
            name="ok", output="y", input_signal="u",
            numerator=(1.0,), denominator=(),
        )
        errs = validate_tf(tf)
        assert any("denominator vazio" in e for e in errs)

    def test_zero_denominator(self):
        tf = TacsTransferFunction(
            name="ok", output="y", input_signal="u",
            numerator=(1.0,), denominator=(0.0, 0.0, 0.0),
        )
        errs = validate_tf(tf)
        assert any("todo zero" in e for e in errs)

    def test_high_order_denominator(self):
        tf = TacsTransferFunction(
            name="ok", output="y", input_signal="u",
            numerator=(1.0,),
            denominator=(1.0,) * 7,   # ordem 6 > limite 5
        )
        errs = validate_tf(tf)
        assert any("denominator de ordem" in e for e in errs)

    def test_high_order_numerator(self):
        tf = TacsTransferFunction(
            name="ok", output="y", input_signal="u",
            numerator=(1.0,) * 7,
            denominator=(1.0,),
        )
        errs = validate_tf(tf)
        assert any("numerator de ordem" in e for e in errs)

    def test_min_max_inverted(self):
        tf = make_pid(
            "p", "u", "y", Kp=1.0,
            output_min=10.0, output_max=-10.0,
        )
        errs = validate_tf(tf)
        assert any("output_min" in e for e in errs)


# ---------------------------------------------------------------------------
# render_tf_summary
# ---------------------------------------------------------------------------


class TestRenderSummary:
    def test_integrator(self):
        tf = make_integrator("int", "u", "y", K=10.0)
        s = render_tf_summary(tf)
        assert "y" in s and "u" in s
        assert "10" in s

    def test_low_pass_shows_tau(self):
        tf = make_low_pass("lp", "u", "y", K=1.0, tau=0.01)
        s = render_tf_summary(tf)
        # "1 + 0.01·s" no denominador
        assert "0.01" in s
        assert "·s" in s

    def test_no_gain_no_K_prefix(self):
        """gain=1 não imprime '1 · '."""
        tf = make_low_pass("lp", "u", "y", K=1.0, tau=1.0)
        s = render_tf_summary(tf)
        # não deve começar com gain explícito
        assert not s.startswith("y = 1 ·")

    def test_with_saturation(self):
        tf = make_pid(
            "p", "u", "y", Kp=1.0,
            output_min=-5.0, output_max=5.0,
        )
        s = render_tf_summary(tf)
        assert "clip" in s
        assert "-5" in s and "5" in s


# ---------------------------------------------------------------------------
# emit_tf_lines
# ---------------------------------------------------------------------------


class TestEmitTfLines:
    def test_card_type_1(self):
        tf = make_low_pass("lp", "u", "y", K=2.0, tau=0.01)
        lines = emit_tf_lines(tf)
        # cartão type-1 começa com " 1"
        card = [l for l in lines if l.lstrip().startswith("1")]
        assert len(card) == 1
        assert "lp" not in card[0]   # name não vai no cartão type-1
        assert "y" in card[0]
        assert "u" in card[0]

    def test_summary_in_comment(self):
        tf = make_low_pass("lp", "u", "y", tau=0.5)
        lines = emit_tf_lines(tf)
        first_comment = lines[0]
        assert first_comment.startswith("C  TACS TF:")

    def test_initial_output_emitted(self):
        tf = make_integrator("int", "u", "y", initial_output=2.5)
        lines = emit_tf_lines(tf)
        assert any("initial_output" in l and "2.5" in l for l in lines)

    def test_initial_output_zero_omitted(self):
        tf = make_integrator("int", "u", "y", initial_output=0.0)
        lines = emit_tf_lines(tf)
        assert not any("initial_output" in l for l in lines)

    def test_saturation_emitted(self):
        tf = make_pid(
            "p", "u", "y", Kp=1.0,
            output_min=-1.0, output_max=1.0,
        )
        lines = emit_tf_lines(tf)
        assert any("saturation" in l for l in lines)

    def test_numerator_denominator_emitted(self):
        tf = make_lead_lag("ll", "u", "y", K=1.0, T1=0.01, T2=0.001)
        lines = emit_tf_lines(tf)
        assert any("numerator" in l for l in lines)
        assert any("denominator" in l for l in lines)


# ---------------------------------------------------------------------------
# emit_tacs_section dispatch
# ---------------------------------------------------------------------------


class TestEmitDispatch:
    def test_only_blocks_works(self):
        """Backward compat — emit_tacs_section ainda aceita só TacsBlock."""
        blk = TacsBlock(
            name="b", expression="a + b", output="y", inputs=("a", "b"),
        )
        text = emit_tacs_section([blk])
        assert "/TACS HYBRID" in text
        assert "88" in text

    def test_only_tfs_works(self):
        tf = make_low_pass("lp", "u", "y", tau=0.01)
        text = emit_tacs_section([tf])
        assert "/TACS HYBRID" in text
        assert " 1y" in text or " 1y " in text  # type-1 card

    def test_mixed_blocks_and_tfs(self):
        blk = TacsBlock(
            name="b", expression="step(t - 0.05)", output="trig",
            inputs=("t",),
        )
        tf = make_pid(
            "p", "err", "u",
            Kp=1.0, Ki=10.0, Kd=0.001,
            output_min=-1.0, output_max=1.0,
        )
        text = emit_tacs_section([tf, blk])
        # TF emite type-1 + block emite 88
        type1 = [l for l in text.splitlines() if l.lstrip().startswith("1")]
        type88 = [l for l in text.splitlines() if l.startswith("88")]
        assert len(type1) >= 1
        assert len(type88) == 1

    def test_invalid_tf_raises(self):
        tf = TacsTransferFunction(
            name="", output="y", input_signal="u",
            numerator=(1.0,), denominator=(1.0,),
        )
        with pytest.raises(ValueError, match="inválid"):
            emit_tacs_section([tf])

    def test_unknown_item_type_raises(self):
        with pytest.raises(TypeError, match="desconhecido"):
            emit_tacs_section(["not a TACS item"])

    def test_blank_card_at_end(self):
        tf = make_integrator("i", "u", "y")
        text = emit_tacs_section([tf])
        assert text.rstrip().endswith("BLANK CARD ENDING TACS")

    def test_section_preserves_order(self):
        """Ordem de emissão = ordem de items (não reordena)."""
        tf1 = make_integrator("i1", "u", "y1")
        tf2 = make_low_pass("lp", "y1", "y2", tau=0.01)
        text = emit_tacs_section([tf1, tf2])
        # i1 vem antes de lp no texto
        i1_idx = text.find("y1")
        lp_idx = text.find("y2")
        assert 0 < i1_idx < lp_idx
