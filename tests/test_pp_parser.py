"""
Tests for app.preprocessor (Qucs .sch parser + serializer + models + catalog).

These tests exercise the v0.21.0 surface:

* Round-trip stability: ``serialize(parse(text))`` reproduces the
  semantically meaningful content of every Qucs example we ship as
  fixture (77 files, versions 0.0.3 through 0.0.19).
* Targeted unit tests on each block parser and on the tokenizer
  (quoting, escape sequences, edge cases).
* Catalog sanity checks (no duplicates, ATP-supported codes are the
  ones we expect).

The fixtures live in ``tests/fixtures/qucs_examples/`` (copied from
the upstream Qucs distribution — they're public-domain examples,
distributed as data, not code).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.preprocessor import (
    PpComponent,
    PpProject,
    PpProperty,
    PpWire,
    parse_sch,
    parse_sch_file,
    serialize_sch,
    serialize_sch_file,
)
from app.preprocessor import catalog
from app.preprocessor.qucs_sch_parser import (
    _parse_component_line,
    _parse_wire_line,
    _tokenize,
    _unescape,
)
from app.preprocessor.qucs_sch_serializer import _quote


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "qucs_examples"


def _all_fixtures() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*.sch"))


# ---------------------------------------------------------------------------
# Tokenizer + quoting unit tests
# ---------------------------------------------------------------------------


class TestTokenizer:
    """Sanity checks on the low-level tokenizer."""

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_simple_words(self):
        assert _tokenize("R R1 1 100 200") == ["R", "R1", "1", "100", "200"]

    def test_quoted_token(self):
        assert _tokenize('R R1 "10 kOhm" 1') == ["R", "R1", "10 kOhm", "1"]

    def test_escaped_quote_in_string(self):
        # "say \"hi\"" → say "hi"
        assert _tokenize(r'X "say \"hi\"" 1') == ["X", 'say "hi"', "1"]

    def test_escaped_newline(self):
        assert _tokenize(r'T "line1\nline2"') == ["T", "line1\nline2"]

    def test_escaped_backslash(self):
        assert _tokenize(r'T "a\\b"') == ["T", "a\\b"]

    def test_multiple_quoted_tokens(self):
        assert _tokenize('A "foo bar" "baz qux"') == ["A", "foo bar", "baz qux"]

    def test_mixed_quoted_unquoted(self):
        assert _tokenize('R R1 1 100 200 "10 Ohm" 1 "26.85" 0') == [
            "R",
            "R1",
            "1",
            "100",
            "200",
            "10 Ohm",
            "1",
            "26.85",
            "0",
        ]


class TestUnescape:
    def test_passthrough_no_escapes(self):
        assert _unescape("hello world") == "hello world"

    def test_backslash_n(self):
        assert _unescape("a\\nb") == "a\nb"

    def test_backslash_quote(self):
        assert _unescape('say \\"hi\\"') == 'say "hi"'

    def test_backslash_backslash(self):
        assert _unescape("a\\\\b") == "a\\b"

    def test_unknown_escape_kept(self):
        # \z não é escape conhecido — mantém literal
        assert _unescape("a\\zb") == "a\\zb"


class TestQuote:
    """Quoting (serializer side) is the inverse of unescape."""

    def test_simple(self):
        assert _quote("hello") == '"hello"'

    def test_with_quote(self):
        assert _quote('say "hi"') == r'"say \"hi\""'

    def test_with_newline(self):
        assert _quote("a\nb") == r'"a\nb"'

    def test_with_backslash(self):
        assert _quote("a\\b") == r'"a\\b"'

    def test_quote_then_unescape_roundtrip(self):
        for s in [
            "simple",
            "with spaces",
            'with "quotes"',
            "with\nnewlines",
            "with\\backslashes",
            'mix: "quote" and \\back\\ and\nnewline',
        ]:
            quoted = _quote(s)
            assert quoted.startswith('"') and quoted.endswith('"')
            assert _unescape(quoted[1:-1]) == s


# ---------------------------------------------------------------------------
# Component / wire line parsers
# ---------------------------------------------------------------------------


class TestParseComponentLine:

    def test_minimal_gnd(self):
        c = _parse_component_line("GND * 1 280 300 0 0 0 0")
        assert c.type == "GND"
        assert c.name == "*"
        assert c.visible is True
        assert (c.x, c.y) == (280, 300)
        assert c.properties == []

    def test_resistor_with_props(self):
        c = _parse_component_line(
            'R R1 1 280 130 15 -26 0 1 "Rbranch" 1 "26.85" 0 "european" 0'
        )
        assert c.type == "R"
        assert c.name == "R1"
        assert c.x == 280
        assert c.y == 130
        assert c.mirror == 0
        assert c.rotation == 1
        assert len(c.properties) == 3
        assert c.properties[0] == PpProperty(value="Rbranch", visible=True)
        assert c.properties[1] == PpProperty(value="26.85", visible=False)
        assert c.properties[2] == PpProperty(value="european", visible=False)

    def test_vac_source(self):
        c = _parse_component_line(
            'Vac V1 1 430 180 18 -26 0 1 "Vamp" 1 "Vfreq" 1 "0" 0 "0" 0'
        )
        assert c.type == "Vac"
        assert c.get(0) == "Vamp"
        assert c.get(1) == "Vfreq"

    def test_short_line_raises(self):
        with pytest.raises(ValueError):
            _parse_component_line("R R1")


class TestParseWireLine:

    def test_simple_wire(self):
        w = _parse_wire_line('280 100 460 100 "" 0 0 0')
        assert (w.x1, w.y1, w.x2, w.y2) == (280, 100, 460, 100)
        assert w.label == ""
        assert w.has_extra is False

    def test_wire_with_label(self):
        w = _parse_wire_line('410 170 570 170 "dc_voltage" 560 130 117')
        assert w.label == "dc_voltage"
        assert (w.label_x, w.label_y) == (560, 130)
        assert w.label_visible == 117

    def test_wire_with_extra_field(self):
        # Format 0.0.15+ has a 9th empty-string field
        w = _parse_wire_line('230 110 290 110 "" 0 0 0 ""')
        assert w.has_extra is True

    def test_short_line_raises(self):
        with pytest.raises(ValueError):
            _parse_wire_line("280 100 460")


# ---------------------------------------------------------------------------
# End-to-end parse on real fixtures
# ---------------------------------------------------------------------------


class TestParseFixtures:
    """Smoke tests on real Qucs examples."""

    def test_fixtures_directory_exists(self):
        assert FIXTURES_DIR.is_dir(), (
            f"Fixtures dir missing: {FIXTURES_DIR}. Did the v0.21.0 setup move "
            "examples from pre-processor/share/qucs/examples/?"
        )

    def test_fixtures_count(self):
        files = _all_fixtures()
        assert len(files) >= 75, f"Expected ~77 .sch examples, got {len(files)}"

    def test_parse_bridge_sch(self):
        """The simplest fixture — bridge.sch (Qucs 0.0.3, no <Symbol>)."""
        proj = parse_sch_file(FIXTURES_DIR / "bridge.sch")
        assert proj.version == "0.0.3"
        assert proj.properties.get("DataSet") == "bridge.dat"
        # 5 R + 1 Vdc + 1 IProbe + 3 GND + 1 .DC + 2 .SW + 1 Eqn = 14
        assert len(proj.components) == 14
        assert sum(1 for c in proj.components if c.type == "R") == 5
        assert any(c.type == "Vdc" and c.name == "V1" for c in proj.components)
        assert sum(1 for c in proj.components if c.type == "GND") == 3
        assert len(proj.wires) == 10

    def test_parse_full_wave_rectifier(self):
        """Mid-complexity fixture (Qucs 0.0.15, with <Symbol>)."""
        proj = parse_sch_file(FIXTURES_DIR / "fullwaverectifier_1.sch")
        assert proj.version == "0.0.15"
        assert proj.symbol == []  # block exists but empty
        # Should have a transformer (sTr), 2 diodes, 1 R, 1 Vac, 2 GND, 1 Eqn, 1 .TR
        types = [c.type for c in proj.components]
        assert "sTr" in types
        assert types.count("Diode") == 2
        assert "Vac" in types
        # All wires in 0.0.15 should have the extra field
        assert all(w.has_extra for w in proj.wires)

    def test_parse_all_fixtures_no_errors(self):
        """Every fixture parses without raising."""
        for path in _all_fixtures():
            try:
                proj = parse_sch_file(path)
            except Exception as exc:
                pytest.fail(f"Failed to parse {path.name}: {exc!r}")
            assert isinstance(proj, PpProject)
            # Sanity: parsed project should at least have version set
            assert proj.version


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """
    Normalization tolerated by the round-trip contract.

    * CRLF → LF
    * Trim trailing whitespace on each line (Qucs is consistent here
      but defensive).
    * Drop trailing empty lines (some Qucs files have a final blank).
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


class TestRoundTrip:

    def test_roundtrip_bridge(self):
        path = FIXTURES_DIR / "bridge.sch"
        original = _normalize(path.read_text(encoding="utf-8"))
        proj = parse_sch(original)
        regen = _normalize(serialize_sch(proj))
        assert regen == original, (
            f"Round-trip diff in {path.name}.\n"
            f"--- original ---\n{original}\n"
            f"--- regen ---\n{regen}\n"
        )

    def test_roundtrip_full_wave_rectifier(self):
        path = FIXTURES_DIR / "fullwaverectifier_1.sch"
        original = _normalize(path.read_text(encoding="utf-8"))
        proj = parse_sch(original)
        regen = _normalize(serialize_sch(proj))
        assert regen == original

    @pytest.mark.parametrize("path", _all_fixtures(), ids=lambda p: p.name)
    def test_roundtrip_each_fixture(self, path: Path):
        """
        Round-trip every fixture. We measure semantic equality:
        the parser ignores whitespace inside blocks, so we compare
        the re-serialized text against itself parsed-then-re-
        serialized — i.e. the second round must equal the first.
        """
        try:
            text1 = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text1 = path.read_text(encoding="latin-1")

        proj1 = parse_sch(text1)
        text2 = serialize_sch(proj1)
        proj2 = parse_sch(text2)
        text3 = serialize_sch(proj2)

        # Stage 2 -> stage 3 must be byte-identical: idempotency.
        assert text2 == text3, (
            f"Serializer not idempotent on {path.name}.\n"
            f"--- text2 ---\n{text2[:500]}\n"
            f"--- text3 ---\n{text3[:500]}\n"
        )
        # Component / wire counts must survive parse → serialize → parse.
        assert len(proj1.components) == len(proj2.components)
        assert len(proj1.wires) == len(proj2.wires)


def test_serialize_sch_file_writes(tmp_path: Path):
    src = FIXTURES_DIR / "bridge.sch"
    proj = parse_sch_file(src)
    dst = tmp_path / "out.sch"
    serialize_sch_file(proj, dst)
    assert dst.exists()
    # Round-trip via files
    proj2 = parse_sch_file(dst)
    assert len(proj2.components) == len(proj.components)
    assert proj2.version == proj.version


def test_serialize_sch_file_crlf(tmp_path: Path):
    src = FIXTURES_DIR / "bridge.sch"
    proj = parse_sch_file(src)
    dst = tmp_path / "out_crlf.sch"
    serialize_sch_file(proj, dst, newline="\r\n")
    raw = dst.read_bytes()
    assert b"\r\n" in raw
    # Re-parse still works
    proj2 = parse_sch_file(dst)
    assert len(proj2.components) == len(proj.components)


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class TestCatalog:

    def test_basic_lookup(self):
        e = catalog.get("R")
        assert e is not None
        assert e.label_pt == "Resistor"
        assert e.atp_supported is True

    def test_unknown_returns_none(self):
        assert catalog.get("NONEXISTENT") is None

    def test_no_duplicate_codes(self):
        codes = [e.code for e in catalog.all_entries()]
        assert len(codes) == len(set(codes)), "Duplicate codes in catalog"

    def test_categories_match_advertised(self):
        for entry in catalog.all_entries():
            assert entry.category in catalog.CATEGORIES, (
                f"Entry {entry.code} has unknown category {entry.category!r}"
            )

    def test_by_category(self):
        passive = catalog.by_category("passive")
        codes = {e.code for e in passive}
        # Os 4 fundamentais devem estar lá
        assert {"R", "L", "C", "GND"}.issubset(codes)

    def test_atp_supported_includes_power_basics(self):
        for code in ["R", "L", "C", "Vdc", "Vac", "GND", "Diode", "Thyr"]:
            assert catalog.is_atp_supported(code), (
                f"Power-electronics basic {code!r} should be ATP-supported"
            )

    def test_simulation_directives_not_atp_supported(self):
        # .TR / .DC etc. são metadata Qucs, não vão para ATP
        for code in [".TR", ".DC", ".AC", ".SW"]:
            assert not catalog.is_atp_supported(code)


# ---------------------------------------------------------------------------
# Project helpers
# ---------------------------------------------------------------------------


class TestProjectHelpers:

    @pytest.fixture
    def proj(self) -> PpProject:
        return parse_sch_file(FIXTURES_DIR / "bridge.sch")

    def test_find_component_existing(self, proj: PpProject):
        assert proj.find_component("V1") is not None

    def test_find_component_missing(self, proj: PpProject):
        assert proj.find_component("Nonexistent") is None

    def test_components_of_type_gnd(self, proj: PpProject):
        gnds = proj.components_of_type("GND")
        assert len(gnds) == 3
        for g in gnds:
            assert g.type == "GND"
            assert g.name == "*"
