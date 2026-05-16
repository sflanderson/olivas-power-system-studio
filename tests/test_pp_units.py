"""
Tests for app.preprocessor.units — Qucs unit-string parser and ATP
fixed-width formatter.
"""

from __future__ import annotations

import math

import pytest

from app.preprocessor.units import (
    format_atp_str,
    format_atp_value,
    is_numeric,
    parse_value,
    parse_value_or_keep,
)


class TestParseValue:

    @pytest.mark.parametrize("text,expected", [
        ("10", 10.0),
        ("10.5", 10.5),
        (".5", 0.5),
        ("0.001", 0.001),
        ("1e3", 1000.0),
        ("1.5e-3", 0.0015),
        ("-5", -5.0),
        ("+3.14", 3.14),
        ("  42  ", 42.0),
    ])
    def test_pure_numbers(self, text: str, expected: float):
        assert parse_value(text) == pytest.approx(expected)

    @pytest.mark.parametrize("text,expected", [
        ("10 k", 10000.0),
        ("10k", 10000.0),
        ("10 kOhm", 10000.0),
        ("10kOhm", 10000.0),
        ("1 MEG", 1e6),
        ("1 M", 1e6),       # M maiúsculo = Mega
        ("1 m", 0.001),     # m minúsculo = mili
        ("47 uH", 47e-6),
        ("47uH", 47e-6),
        ("100 uF", 100e-6),
        ("1 nF", 1e-9),
        ("1 pF", 1e-12),
        ("1 GHz", 1e9),
        ("1 THz", 1e12),
    ])
    def test_si_prefixes(self, text: str, expected: float):
        assert parse_value(text) == pytest.approx(expected, rel=1e-9)

    @pytest.mark.parametrize("text", [
        "",
        None,
        "   ",
        "Vamp",          # variável simbólica
        "abc",
        "Bduty",
        "1.5 xyz",       # sufixo desconhecido
    ])
    def test_non_numeric_returns_none(self, text):
        assert parse_value(text) is None

    def test_micro_unicode(self):
        assert parse_value("10 µF") == pytest.approx(10e-6)

    def test_negative_with_prefix(self):
        assert parse_value("-3 mA") == pytest.approx(-0.003)


class TestFormatAtp:

    @pytest.mark.parametrize("value,width,expected", [
        (1000, 6, "  1000"),
        (10, 6, "    10"),
        (0, 6, "     0"),
        (-5, 6, "    -5"),
        (1.5, 6, "   1.5"),
        (0.001, 6, " 0.001"),
        (1234567, 6, " 1e+06"),  # cientifica quando inteiro estoura
    ])
    def test_format_atp_value(self, value: float, width: int, expected: str):
        out = format_atp_value(value, width)
        assert out == expected, f"got {out!r}"
        assert len(out) == width

    def test_format_atp_value_inf_is_blanks(self):
        assert format_atp_value(math.inf, 6) == "      "

    def test_format_atp_value_nan_is_blanks(self):
        assert format_atp_value(math.nan, 6) == "      "

    def test_format_atp_value_none_is_blanks(self):
        # type: ignore — testando comportamento defensivo
        assert format_atp_value(None, 6) == "      "  # type: ignore

    def test_format_atp_str_strips(self):
        assert format_atp_str(1000.0, 6) == "1000"

    def test_format_atp_value_width_10(self):
        out = format_atp_value(0.000123456, 10)
        assert len(out) == 10
        # Deve ser parseável de volta com pequena tolerância
        assert parse_value(out.strip()) == pytest.approx(0.000123456, rel=1e-3)


class TestRoundTrip:
    """Parse → format → parse deve ser estável (relativo)."""

    @pytest.mark.parametrize("text", [
        "1000",
        "10 kOhm",
        "47 uH",
        "100 uF",
        "60 Hz",
        "0.001",
        "1.5e3",
        "230 V",
    ])
    def test_roundtrip_numeric(self, text: str):
        v1 = parse_value(text)
        assert v1 is not None
        s = format_atp_str(v1, width=12)
        v2 = parse_value(s)
        assert v2 is not None
        assert v1 == pytest.approx(v2, rel=1e-6)


class TestParseOrKeep:

    def test_numeric_gets_converted(self):
        out = parse_value_or_keep("10 kOhm")
        # Deve virar string numérica
        assert "10000" in out or "1e+04" in out.lower()

    def test_symbolic_kept_as_is(self):
        assert parse_value_or_keep("Vamp") == "Vamp"

    def test_empty_kept(self):
        assert parse_value_or_keep("") == ""


class TestIsNumeric:

    @pytest.mark.parametrize("text,expected", [
        ("10", True),
        ("10 kOhm", True),
        ("Vamp", False),
        ("", False),
        ("1.5e-3", True),
        ("abc", False),
    ])
    def test_is_numeric(self, text: str, expected: bool):
        assert is_numeric(text) is expected
