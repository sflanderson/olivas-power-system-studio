"""
tests/test_pp_tacs_blocks.py — v0.26.3: blocos discretos
``/TACS HYBRID`` — limitador, dead-band, zero-order hold,
weighted sum.

Cobre:

* ``TacsLimiter``: dataclass + validate (lo>=hi rejeitado, vazio,
  >6 chars) + emit.
* ``TacsDeadBand``: validate (half_width<=0 rejeitado) + emit.
* ``TacsZOH``: validate (input==trigger rejeitado, 4 strings
  obrigatórias) + emit.
* ``TacsSum``: validate (sem inputs, >6 inputs, par malformado,
  weight não-numérico, signal_name >6 chars) + emit.
* Helpers ``make_subtractor`` (y = a - b) e ``make_adder``
  (y = sum xi).
* Despacho via ``emit_tacs_section`` para os 4 novos tipos +
  combinação realista (subtractor → PID → limiter → dead-band →
  ZOH → adder).
"""

from __future__ import annotations

import pytest

from app.preprocessor.tacs import emit_tacs_section
from app.preprocessor.tacs_blocks import (
    TacsDeadBand, TacsLimiter, TacsSum, TacsZOH,
    emit_dead_band_lines, emit_limiter_lines,
    emit_sum_lines, emit_zoh_lines,
    make_adder, make_subtractor,
    validate_dead_band, validate_limiter,
    validate_sum, validate_zoh,
)
from app.preprocessor.tacs_tf import make_pid


# ---------------------------------------------------------------------------
# TacsLimiter
# ---------------------------------------------------------------------------


class TestLimiter:
    def test_dataclass_frozen(self):
        b = TacsLimiter(
            name="lim", output="y", input_signal="u",
            output_min=-1.0, output_max=1.0,
        )
        with pytest.raises(Exception):
            b.output_min = 0.0  # frozen

    def test_validate_ok(self):
        b = TacsLimiter(
            name="lim", output="y", input_signal="u",
            output_min=-1.0, output_max=1.0,
        )
        assert validate_limiter(b) == []

    def test_validate_lo_ge_hi(self):
        b = TacsLimiter(
            name="lim", output="y", input_signal="u",
            output_min=2.0, output_max=1.0,
        )
        errs = validate_limiter(b)
        assert any("output_min" in e for e in errs)

    def test_validate_lo_eq_hi(self):
        b = TacsLimiter(
            name="lim", output="y", input_signal="u",
            output_min=1.0, output_max=1.0,
        )
        errs = validate_limiter(b)
        assert any("output_min" in e for e in errs)

    def test_validate_empty_name(self):
        b = TacsLimiter(
            name="", output="y", input_signal="u",
            output_min=0, output_max=1,
        )
        errs = validate_limiter(b)
        assert any("name vazio" in e for e in errs)

    def test_validate_long_name(self):
        b = TacsLimiter(
            name="abcdefgh", output="y", input_signal="u",
            output_min=0, output_max=1,
        )
        errs = validate_limiter(b)
        assert any("> 6 chars" in e for e in errs)

    def test_emit_card_54(self):
        b = TacsLimiter(
            name="lim", output="y", input_signal="u",
            output_min=-1.0, output_max=1.0,
        )
        lines = emit_limiter_lines(b)
        card_lines = [l for l in lines if l.startswith("54")]
        assert len(card_lines) == 1
        assert "y" in card_lines[0]
        assert "u" in card_lines[0]

    def test_emit_summary_in_comment(self):
        b = TacsLimiter(
            name="lim", output="y", input_signal="u",
            output_min=-1.0, output_max=1.0,
        )
        lines = emit_limiter_lines(b)
        first = lines[0]
        assert first.startswith("C  TACS Limiter")
        assert "clip" in first


# ---------------------------------------------------------------------------
# TacsDeadBand
# ---------------------------------------------------------------------------


class TestDeadBand:
    def test_validate_ok(self):
        b = TacsDeadBand(
            name="dz", output="y", input_signal="u",
            half_width=0.05,
        )
        assert validate_dead_band(b) == []

    def test_with_center(self):
        b = TacsDeadBand(
            name="dz", output="y", input_signal="u",
            half_width=0.1, center=0.5,
        )
        assert validate_dead_band(b) == []

    def test_zero_half_width_rejected(self):
        b = TacsDeadBand(
            name="dz", output="y", input_signal="u",
            half_width=0.0,
        )
        errs = validate_dead_band(b)
        assert any("half_width" in e for e in errs)

    def test_negative_half_width_rejected(self):
        b = TacsDeadBand(
            name="dz", output="y", input_signal="u",
            half_width=-0.01,
        )
        errs = validate_dead_band(b)
        assert any("half_width" in e for e in errs)

    def test_emit_card_53(self):
        b = TacsDeadBand(
            name="dz", output="y", input_signal="u",
            half_width=0.1, center=0.0,
        )
        lines = emit_dead_band_lines(b)
        cards = [l for l in lines if l.startswith("53")]
        assert len(cards) == 1
        assert "0.1" in cards[0]

    def test_emit_window_in_comment(self):
        """Comentário mostra janela [center-hw, center+hw]."""
        b = TacsDeadBand(
            name="dz", output="y", input_signal="u",
            half_width=0.1, center=2.0,
        )
        lines = emit_dead_band_lines(b)
        # janela = [1.9, 2.1]
        all_text = "\n".join(lines)
        assert "1.9" in all_text
        assert "2.1" in all_text


# ---------------------------------------------------------------------------
# TacsZOH
# ---------------------------------------------------------------------------


class TestZOH:
    def test_validate_ok(self):
        b = TacsZOH(
            name="z", output="y", input_signal="u",
            trigger_signal="clk",
        )
        assert validate_zoh(b) == []

    def test_input_eq_trigger_rejected(self):
        b = TacsZOH(
            name="z", output="y", input_signal="x",
            trigger_signal="x",
        )
        errs = validate_zoh(b)
        assert any("degenerado" in e for e in errs)

    def test_missing_trigger(self):
        b = TacsZOH(
            name="z", output="y", input_signal="u",
            trigger_signal="",
        )
        errs = validate_zoh(b)
        assert any("trigger_signal vazio" in e for e in errs)

    def test_emit_card_65(self):
        b = TacsZOH(
            name="z", output="y", input_signal="u",
            trigger_signal="clk", initial_output=2.5,
        )
        lines = emit_zoh_lines(b)
        cards = [l for l in lines if l.startswith("65")]
        assert len(cards) == 1
        assert "u" in cards[0]
        assert "clk" in cards[0]
        assert "2.5" in cards[0]

    def test_initial_output_in_comment(self):
        b = TacsZOH(
            name="z", output="y", input_signal="u",
            trigger_signal="clk", initial_output=3.7,
        )
        lines = emit_zoh_lines(b)
        comment_text = "\n".join(lines[:-1])
        assert "initial_output" in comment_text
        assert "3.7" in comment_text

    def test_initial_output_zero_no_comment(self):
        b = TacsZOH(
            name="z", output="y", input_signal="u",
            trigger_signal="clk", initial_output=0.0,
        )
        lines = emit_zoh_lines(b)
        comment_text = "\n".join(lines[:-1])
        assert "initial_output" not in comment_text


# ---------------------------------------------------------------------------
# TacsSum
# ---------------------------------------------------------------------------


class TestSum:
    def test_basic(self):
        b = TacsSum(
            name="s", output="y",
            inputs=(("a", 1.0), ("b", -1.0)),
        )
        assert validate_sum(b) == []

    def test_with_bias(self):
        b = TacsSum(
            name="s", output="y",
            inputs=(("a", 1.0),), bias=10.0,
        )
        assert validate_sum(b) == []

    def test_empty_inputs_rejected(self):
        b = TacsSum(name="s", output="y", inputs=())
        errs = validate_sum(b)
        assert any("inputs vazio" in e for e in errs)

    def test_too_many_inputs(self):
        b = TacsSum(
            name="s", output="y",
            inputs=tuple((f"x{i}", 1.0) for i in range(7)),
        )
        errs = validate_sum(b)
        assert any("> 6" in e for e in errs)

    def test_max_inputs_ok(self):
        b = TacsSum(
            name="s", output="y",
            inputs=tuple((f"x{i}", 1.0) for i in range(6)),
        )
        assert validate_sum(b) == []

    def test_malformed_input_pair(self):
        b = TacsSum(
            name="s", output="y",
            inputs=(("a",),),  # falta weight
        )
        errs = validate_sum(b)
        assert any("tupla" in e for e in errs)

    def test_non_numeric_weight(self):
        b = TacsSum(
            name="s", output="y",
            inputs=(("a", "not_a_num"),),
        )
        errs = validate_sum(b)
        assert any("weight" in e for e in errs)

    def test_long_input_signal(self):
        b = TacsSum(
            name="s", output="y",
            inputs=(("very_long_signal_name", 1.0),),
        )
        errs = validate_sum(b)
        assert any("> 6 chars" in e for e in errs)

    def test_emit_card_98(self):
        b = TacsSum(
            name="s", output="y",
            inputs=(("a", 1.0), ("b", -1.0)),
        )
        lines = emit_sum_lines(b)
        cards = [l for l in lines if l.startswith("98")]
        assert len(cards) == 1

    def test_emit_summary(self):
        b = TacsSum(
            name="s", output="err",
            inputs=(("ref", 1.0), ("meas", -1.0)),
        )
        lines = emit_sum_lines(b)
        # primeira linha tem "C  TACS Sum: err = ref - meas"
        first = lines[0]
        assert "TACS Sum" in first
        assert "ref" in first and "meas" in first


# ---------------------------------------------------------------------------
# Helpers make_subtractor / make_adder
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_subtractor(self):
        b = make_subtractor("e", "err", "ref", "meas")
        assert b.inputs == (("ref", 1.0), ("meas", -1.0))
        assert validate_sum(b) == []

    def test_adder_two_args(self):
        b = make_adder("a", "y", "x1", "x2")
        assert b.inputs == (("x1", 1.0), ("x2", 1.0))

    def test_adder_many_args(self):
        b = make_adder("a", "y", "x1", "x2", "x3", "x4")
        assert len(b.inputs) == 4
        assert all(w == 1.0 for _, w in b.inputs)

    def test_adder_validates(self):
        b = make_adder("a", "y", "x1")
        assert validate_sum(b) == []


# ---------------------------------------------------------------------------
# Dispatch via emit_tacs_section
# ---------------------------------------------------------------------------


class TestDispatchAllNew:
    def test_dispatch_limiter(self):
        b = TacsLimiter(
            name="lim", output="y", input_signal="u",
            output_min=-1.0, output_max=1.0,
        )
        text = emit_tacs_section([b])
        assert "/TACS HYBRID" in text
        assert "54" in text

    def test_dispatch_dead_band(self):
        b = TacsDeadBand(
            name="dz", output="y", input_signal="u",
            half_width=0.05,
        )
        text = emit_tacs_section([b])
        assert "53" in text

    def test_dispatch_zoh(self):
        b = TacsZOH(
            name="z", output="y", input_signal="u",
            trigger_signal="clk",
        )
        text = emit_tacs_section([b])
        assert "65" in text

    def test_dispatch_sum(self):
        b = TacsSum(
            name="s", output="y",
            inputs=(("a", 1.0), ("b", -1.0)),
        )
        text = emit_tacs_section([b])
        assert "98" in text

    def test_invalid_limiter_raises(self):
        b = TacsLimiter(
            name="lim", output="y", input_signal="u",
            output_min=2.0, output_max=1.0,
        )
        with pytest.raises(ValueError, match="inválid"):
            emit_tacs_section([b])

    def test_full_control_pipeline(self):
        """Pipeline realista: subtractor → PID → limiter →
        dead-band → ZOH → adder."""
        items = [
            make_subtractor("esub", "err", "ref", "meas"),
            make_pid("pid1", "err", "upid", Kp=10.0, Ki=50.0, Kd=0.01),
            TacsLimiter(
                name="clip1", output="ulim", input_signal="upid",
                output_min=-1.0, output_max=1.0,
            ),
            TacsDeadBand(
                name="dz1", output="udz", input_signal="ulim",
                half_width=0.05,
            ),
            TacsZOH(
                name="zoh1", output="uzoh", input_signal="udz",
                trigger_signal="clk",
            ),
            make_adder("add1", "utot", "uzoh", "ffwd"),
        ]
        text = emit_tacs_section(items)
        # Cada device-type aparece pelo menos 1×
        for device in ("98", "1upid", "54", "53", "65"):
            assert device in text, f"falta {device!r}"
        # 2 sums (subtractor + adder), 1 PID, 1 limiter, 1 deadband, 1 zoh
        assert text.count("98") >= 2

    def test_blank_card_at_end(self):
        b = TacsLimiter(
            name="l", output="y", input_signal="u",
            output_min=-1, output_max=1,
        )
        text = emit_tacs_section([b])
        assert text.rstrip().endswith("BLANK CARD ENDING TACS")

    def test_only_one_section_header(self):
        items = [
            make_subtractor("e", "err", "ref", "meas"),
            TacsLimiter(
                name="l", output="ul", input_signal="err",
                output_min=-1, output_max=1,
            ),
        ]
        text = emit_tacs_section(items)
        assert text.count("/TACS HYBRID") == 1
        assert text.count("BLANK CARD ENDING TACS") == 1
