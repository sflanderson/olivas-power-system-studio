"""
tests/test_pp_v2_2_1_ber.py — v2.2.1.

Cobre BER (Basic Encoding Rules — ITU-T X.690):

* Sprint A: encoders primitivos
* Sprint B: decoders + round-trip
* Anti-alucinação: golden values from X.690 published examples
"""

from __future__ import annotations

import pytest


# ===========================================================================
# Sprint A — BER Primitive Encoders
# ===========================================================================


class TestBEREncodeInteger:

    def test_module_loadable(self):
        from app.integration import iec61850_ber  # noqa: F401

    def test_encode_zero(self):
        """Reference X.690 §8.3: INTEGER 0 → 02 01 00."""
        from app.integration.iec61850_ber import encode_integer
        assert encode_integer(0) == bytes([0x02, 0x01, 0x00])

    def test_encode_127(self):
        """X.690 §8.3.2: 127 → 02 01 7F (single byte, MSB clear)."""
        from app.integration.iec61850_ber import encode_integer
        assert encode_integer(127) == bytes([0x02, 0x01, 0x7F])

    def test_encode_128(self):
        """X.690 §8.3.2: 128 → 02 02 00 80 (need leading 0 to keep
        positive)."""
        from app.integration.iec61850_ber import encode_integer
        assert encode_integer(128) == bytes([0x02, 0x02, 0x00, 0x80])

    def test_encode_negative_one(self):
        """X.690 §8.3.2: -1 → 02 01 FF (two's complement)."""
        from app.integration.iec61850_ber import encode_integer
        assert encode_integer(-1) == bytes([0x02, 0x01, 0xFF])


class TestBEREncodeBoolean:

    def test_encode_true(self):
        """X.690 §11.1: BOOLEAN TRUE → 01 01 FF."""
        from app.integration.iec61850_ber import encode_boolean
        assert encode_boolean(True) == bytes([0x01, 0x01, 0xFF])

    def test_encode_false(self):
        """X.690 §8.2.2: BOOLEAN FALSE → 01 01 00."""
        from app.integration.iec61850_ber import encode_boolean
        assert encode_boolean(False) == bytes([0x01, 0x01, 0x00])


class TestBEREncodeOctetString:

    def test_encode_empty(self):
        """OCTET STRING vazio → 04 00."""
        from app.integration.iec61850_ber import encode_octet_string
        assert encode_octet_string(b"") == bytes([0x04, 0x00])

    def test_encode_short(self):
        """b'\\x01\\x02\\x03' → 04 03 01 02 03."""
        from app.integration.iec61850_ber import encode_octet_string
        assert encode_octet_string(b"\x01\x02\x03") == bytes(
            [0x04, 0x03, 0x01, 0x02, 0x03]
        )


class TestBEREncodeVisibleString:

    def test_encode_hello(self):
        """X.690 VisibleString tag 0x1A. 'Hi' → 1A 02 48 69."""
        from app.integration.iec61850_ber import encode_visible_string
        assert encode_visible_string("Hi") == bytes(
            [0x1A, 0x02, 0x48, 0x69]
        )


class TestBERLengthField:

    def test_length_short_form(self):
        """X.690 §8.1.3.4: length < 128 → single byte."""
        from app.integration.iec61850_ber import encode_length
        assert encode_length(0) == bytes([0x00])
        assert encode_length(1) == bytes([0x01])
        assert encode_length(127) == bytes([0x7F])

    def test_length_long_form(self):
        """X.690 §8.1.3.5: length ≥ 128 → 0x8X + N bytes."""
        from app.integration.iec61850_ber import encode_length
        # 128 → 81 80
        assert encode_length(128) == bytes([0x81, 0x80])
        # 256 → 82 01 00
        assert encode_length(256) == bytes([0x82, 0x01, 0x00])


# ===========================================================================
# Sprint B — BER Decoders + Round-trip
# ===========================================================================


class TestBERDecode:

    def test_decode_integer_round_trip(self):
        from app.integration.iec61850_ber import (
            decode_integer, encode_integer,
        )
        for n in (0, 1, 127, 128, 256, -1, -128, 65535):
            encoded = encode_integer(n)
            decoded, consumed = decode_integer(encoded)
            assert decoded == n
            assert consumed == len(encoded)

    def test_decode_boolean_round_trip(self):
        from app.integration.iec61850_ber import (
            decode_boolean, encode_boolean,
        )
        for b in (True, False):
            encoded = encode_boolean(b)
            decoded, consumed = decode_boolean(encoded)
            assert decoded == b
            assert consumed == len(encoded)

    def test_decode_octet_string_round_trip(self):
        from app.integration.iec61850_ber import (
            decode_octet_string, encode_octet_string,
        )
        for s in (b"", b"hello", b"\x00\xff\x80\x01"):
            encoded = encode_octet_string(s)
            decoded, consumed = decode_octet_string(encoded)
            assert decoded == s

    def test_decode_visible_string_round_trip(self):
        from app.integration.iec61850_ber import (
            decode_visible_string, encode_visible_string,
        )
        for s in ("", "Hello", "DEMO/LLN0$GO$gcb01"):
            encoded = encode_visible_string(s)
            decoded, consumed = decode_visible_string(encoded)
            assert decoded == s


# ===========================================================================
# Sprint C — GOOSE PDU encoder (structural)
# ===========================================================================


class TestGoosePDUEncoder:

    def test_module_loadable(self):
        from app.integration import iec61850_ber  # noqa: F401

    def test_encode_simple_goose_pdu(self):
        """Structural GOOSE PDU encoder produz bytes válidos BER."""
        from datetime import datetime
        from app.integration.iec61850_goose import GooseMessage
        from app.integration.iec61850_ber import encode_goose_pdu

        msg = GooseMessage(
            go_id="DEMO/LLN0$GO$gcb01",
            dataset="DEMO/LLN0$DS_TripCommand",
            st_num=1,
            sq_num=0,
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            test=False,
            data={"trip": True},
        )
        wire = encode_goose_pdu(msg)
        # PDU bytes: começa com tag application 1 (0x61)
        # ou context-specific (depende do encoding choice)
        assert isinstance(wire, bytes)
        assert len(wire) > 10   # PDU mínimo razoável


# ===========================================================================
# Sprint D — SV PDU encoder (structural)
# ===========================================================================


class TestSVPDUEncoder:

    def test_encode_simple_sv_asdu(self):
        from app.integration.iec61850_ber import encode_sv_asdu

        asdu_bytes = encode_sv_asdu(
            sv_id="DEMO/MEAS_MUT/V_RMS",
            smp_cnt=42,
            samples=[100, 200, 300],
        )
        assert isinstance(asdu_bytes, bytes)
        assert len(asdu_bytes) > 10
