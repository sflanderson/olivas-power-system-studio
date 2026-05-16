"""
app.integration.iec61850_ber — ASN.1 BER (Basic Encoding Rules)
encoders/decoders para wire format de GOOSE + SV PDUs (v2.2.1).

Filosofia
==========

ASN.1 BER (ITU-T X.690:2021) é o formato wire de IEC 61850.
Cada elemento é encoded como **TLV** (Tag-Length-Value):

* **Tag** (1+ bytes): class + form + tag number
* **Length** (1+ bytes): comprimento do Value em bytes
* **Value** (N bytes): conteúdo

Esta release entrega:

* **Primitives** completos: INTEGER, BOOLEAN, OCTET STRING,
  VisibleString
* **Length encoder/decoder** com short e long form
* **GOOSE PDU encoder estrutural** (paridade IEC 61850-8-1 §17)
* **SV ASDU encoder estrutural** (paridade IEC 61850-9-2)

Anti-alucinação
================

* Cada primitive validado contra **golden values publicados**:
  - INTEGER 0 → ``02 01 00`` (X.690 §8.3.1)
  - BOOLEAN TRUE → ``01 01 FF`` (X.690 §11.1)
  - VisibleString tag 0x1A (X.680 §41.6)
* PDU encoders usam **estrutura BER válida** mas **NÃO** garantem
  byte-by-byte interop com IEDs reais — para isso, libiec61850.
* Ainda assim, output PDU passa em ASN.1 BER decoders genéricos
  (qualquer parser BER lê os bytes corretamente).

Cobertura normativa
====================

* ITU-T X.680:2021 (ASN.1 syntax)
* ITU-T X.690:2021 (BER/CER/DER encoding rules)
* IEC 61850-8-1:2020 §17 (GOOSE)
* IEC 61850-9-2:2020 (SV)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Tuple


# ---------------------------------------------------------------------------
# Universal class tags (X.680 §41)
# ---------------------------------------------------------------------------


TAG_BOOLEAN = 0x01
TAG_INTEGER = 0x02
TAG_OCTET_STRING = 0x04
TAG_VISIBLE_STRING = 0x1A   # ISO 646 / VisibleString
TAG_SEQUENCE = 0x30   # constructed
TAG_SEQUENCE_OF = 0x30


# ---------------------------------------------------------------------------
# Length field (X.690 §8.1.3)
# ---------------------------------------------------------------------------


def encode_length(n: int) -> bytes:
    """
    Encode integer length (X.690 §8.1.3).

    * Short form (n < 128): single byte
    * Long form (n >= 128): 0x80 | num_bytes + N bytes (BE)

    Raises
    ------
    ValueError
        Se n < 0.
    """
    if n < 0:
        raise ValueError(f"Length deve ser >= 0 (got {n})")
    if n < 128:
        return bytes([n])
    # Long form
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def decode_length(data: bytes, offset: int = 0) -> Tuple[int, int]:
    """
    Decode length starting at ``offset``.

    Returns
    -------
    (length_value, num_bytes_consumed_for_length)
    """
    if offset >= len(data):
        raise ValueError("Buffer too short to decode length")
    first = data[offset]
    if first < 0x80:
        return first, 1
    # Long form
    nbytes = first & 0x7F
    if nbytes == 0:
        raise ValueError("Indefinite length not supported")
    if offset + 1 + nbytes > len(data):
        raise ValueError("Buffer too short for long-form length")
    length = int.from_bytes(
        data[offset + 1: offset + 1 + nbytes], "big",
    )
    return length, 1 + nbytes


# ---------------------------------------------------------------------------
# INTEGER (X.690 §8.3)
# ---------------------------------------------------------------------------


def encode_integer(n: int) -> bytes:
    """
    Encode INTEGER em BER (X.690 §8.3).

    * Mínimo 1 byte de Value
    * Two's complement
    * Padding com 00 (positivo grande) ou FF (negativo) quando
      necessário para preservar sinal
    """
    if n == 0:
        value = bytes([0x00])
    elif n > 0:
        # Mínimo de bytes para representar positive
        nbytes = max(1, (n.bit_length() + 8) // 8)
        # Se MSB do primeiro byte está setado, prefixar 0x00 para
        # manter positive
        raw = n.to_bytes(nbytes, "big")
        if raw[0] & 0x80:
            raw = bytes([0x00]) + raw
        value = raw
    else:  # negative
        # Two's complement
        nbytes = max(1, ((-n - 1).bit_length() + 8) // 8)
        # Try +1 byte se MSB clear (precisa preservar negative)
        for trial in (nbytes, nbytes + 1):
            try:
                raw = n.to_bytes(trial, "big", signed=True)
                if raw[0] & 0x80:   # MSB set → realmente negative
                    value = raw
                    break
            except OverflowError:
                continue
        else:
            raise ValueError(f"Cannot encode integer {n}")

    return bytes([TAG_INTEGER]) + encode_length(len(value)) + value


def decode_integer(data: bytes, offset: int = 0) -> Tuple[int, int]:
    """Decode INTEGER. Returns (value, num_bytes_consumed)."""
    if offset >= len(data) or data[offset] != TAG_INTEGER:
        raise ValueError(
            f"Expected INTEGER tag {TAG_INTEGER:02X}"
        )
    length, lbytes = decode_length(data, offset + 1)
    start = offset + 1 + lbytes
    end = start + length
    if end > len(data):
        raise ValueError("Buffer too short for INTEGER value")
    value_bytes = data[start: end]
    if len(value_bytes) == 0:
        return 0, end - offset
    value = int.from_bytes(value_bytes, "big", signed=True)
    return value, end - offset


# ---------------------------------------------------------------------------
# BOOLEAN (X.690 §8.2 + §11.1 for canonical TRUE)
# ---------------------------------------------------------------------------


def encode_boolean(b: bool) -> bytes:
    """
    Encode BOOLEAN em BER. TRUE = 0xFF (DER canonical, X.690 §11.1),
    FALSE = 0x00 (X.690 §8.2.2).
    """
    return bytes([TAG_BOOLEAN, 0x01, 0xFF if b else 0x00])


def decode_boolean(data: bytes, offset: int = 0) -> Tuple[bool, int]:
    """Decode BOOLEAN. Returns (value, num_bytes_consumed)."""
    if offset >= len(data) or data[offset] != TAG_BOOLEAN:
        raise ValueError(
            f"Expected BOOLEAN tag {TAG_BOOLEAN:02X}"
        )
    length, lbytes = decode_length(data, offset + 1)
    if length != 1:
        raise ValueError(f"BOOLEAN length must be 1 (got {length})")
    val = data[offset + 1 + lbytes] != 0
    return val, 1 + lbytes + 1


# ---------------------------------------------------------------------------
# OCTET STRING (X.690 §8.7)
# ---------------------------------------------------------------------------


def encode_octet_string(b: bytes) -> bytes:
    """Encode OCTET STRING."""
    return bytes([TAG_OCTET_STRING]) + encode_length(len(b)) + b


def decode_octet_string(
    data: bytes, offset: int = 0,
) -> Tuple[bytes, int]:
    """Decode OCTET STRING. Returns (value, num_bytes_consumed)."""
    if offset >= len(data) or data[offset] != TAG_OCTET_STRING:
        raise ValueError(
            f"Expected OCTET STRING tag {TAG_OCTET_STRING:02X}"
        )
    length, lbytes = decode_length(data, offset + 1)
    start = offset + 1 + lbytes
    end = start + length
    if end > len(data):
        raise ValueError("Buffer too short for OCTET STRING")
    return bytes(data[start: end]), end - offset


# ---------------------------------------------------------------------------
# VisibleString (X.680 §41.6, tag 0x1A)
# ---------------------------------------------------------------------------


def encode_visible_string(s: str) -> bytes:
    """Encode VisibleString (ASCII printable)."""
    raw = s.encode("ascii")
    return bytes([TAG_VISIBLE_STRING]) + encode_length(len(raw)) + raw


def decode_visible_string(
    data: bytes, offset: int = 0,
) -> Tuple[str, int]:
    """Decode VisibleString."""
    if offset >= len(data) or data[offset] != TAG_VISIBLE_STRING:
        raise ValueError(
            f"Expected VisibleString tag {TAG_VISIBLE_STRING:02X}"
        )
    length, lbytes = decode_length(data, offset + 1)
    start = offset + 1 + lbytes
    end = start + length
    if end > len(data):
        raise ValueError("Buffer too short for VisibleString")
    return data[start: end].decode("ascii"), end - offset


# ---------------------------------------------------------------------------
# Context-specific tag helper (IEC 61850 PDUs use [n] IMPLICIT tags)
# ---------------------------------------------------------------------------


def encode_implicit_tagged(
    tag_number: int, value: bytes,
) -> bytes:
    """
    Encode com context-specific IMPLICIT tag [n].

    Tag byte: class (10b context) | form (0=primitive) | number
    = 0x80 | tag_number (assuming primitive single-byte tag).

    For tag_number >= 31, multi-byte tag form is needed (X.690
    §8.1.2.4) — não implementado em v2.2.1 (IEC 61850 GOOSE/SV
    usa tags 0..14).
    """
    if tag_number < 0 or tag_number >= 31:
        raise ValueError(
            f"tag_number deve ser 0..30 (got {tag_number})"
        )
    return bytes([0x80 | tag_number]) + encode_length(len(value)) + value


# ---------------------------------------------------------------------------
# GOOSE PDU encoder (estrutural — IEC 61850-8-1 §17.2.5)
# ---------------------------------------------------------------------------


def encode_goose_pdu(msg) -> bytes:
    """
    Encode GooseMessage como BER PDU.

    Estrutura (IEC 61850-8-1 §17.2.5):
    ::

        GoosePdu ::= [APPLICATION 1] IMPLICIT SEQUENCE {
            gocbRef             [0] IMPLICIT VisibleString,
            timeAllowedToLive   [1] IMPLICIT INTEGER,
            datSet              [2] IMPLICIT VisibleString,
            goID                [3] IMPLICIT VisibleString,
            t                   [4] IMPLICIT UtcTime,
            stNum               [5] IMPLICIT INTEGER,
            sqNum               [6] IMPLICIT INTEGER,
            test                [7] IMPLICIT BOOLEAN DEFAULT FALSE,
            confRev             [8] IMPLICIT INTEGER,
            ndsCom              [9] IMPLICIT BOOLEAN DEFAULT FALSE,
            numDatSetEntries    [10] IMPLICIT INTEGER,
            allData             [11] IMPLICIT SEQUENCE OF Data
        }

    Anti-alucinação: Data encoding interno é simplificado
    (apenas BOOLEAN/INTEGER nessa release). Real interop com
    IEDs precisaria libiec61850.
    """
    # Encode each context-tagged field
    fields = []
    fields.append(encode_implicit_tagged(0, msg.go_id.encode("ascii")))
    # timeAllowedToLive default 1000ms
    fields.append(_encode_implicit_integer(1, 1000))
    fields.append(encode_implicit_tagged(2, msg.dataset.encode("ascii")))
    fields.append(encode_implicit_tagged(3, msg.go_id.encode("ascii")))
    # t (UtcTime — simplificado: 8 bytes seconds_since_epoch + ms)
    ts_bytes = _encode_utctime(msg.timestamp)
    fields.append(encode_implicit_tagged(4, ts_bytes))
    fields.append(_encode_implicit_integer(5, msg.st_num))
    fields.append(_encode_implicit_integer(6, msg.sq_num))
    fields.append(
        encode_implicit_tagged(7, b"\xff" if msg.test else b"\x00")
    )
    fields.append(_encode_implicit_integer(8, 1))   # confRev
    fields.append(encode_implicit_tagged(9, b"\x00"))   # ndsCom
    fields.append(_encode_implicit_integer(10, len(msg.data)))
    # allData: simplificado — sequence of BOOLEAN
    all_data = b""
    for value in msg.data.values():
        if isinstance(value, bool):
            all_data += encode_boolean(value)
        elif isinstance(value, int):
            all_data += encode_integer(value)
        else:
            all_data += encode_visible_string(str(value))
    fields.append(encode_implicit_tagged(11, all_data))

    body = b"".join(fields)
    # APPLICATION 1 IMPLICIT SEQUENCE → tag 0x61 (constructed app 1)
    return bytes([0x61]) + encode_length(len(body)) + body


def _encode_implicit_integer(tag_number: int, n: int) -> bytes:
    """Helper: INTEGER com tag IMPLICIT [tag_number]."""
    # Encode integer body (sem tag universal 0x02)
    full = encode_integer(n)
    # Strip universal tag + length
    _, lbytes = decode_length(full, 1)
    body = full[1 + lbytes:]
    return encode_implicit_tagged(tag_number, body)


def _encode_utctime(ts: datetime) -> bytes:
    """
    UtcTime simplificado: 4 bytes seconds since epoch (unsigned)
    + 4 bytes nanoseconds-component (consistente com docstring).

    v3.0.0 fix (audit #4): docstring antes dizia "ms" mas código
    usava nanos. Agora alinhado em "nanoseconds". Limitação Y2106
    (unsigned 32-bit overflow em 2106-02-07) declarada
    explicitamente — para deploy real pós-2106, IEC 61850-8-1
    spec real usa 8 bytes seconds + 4 bytes fraction; aqui mantemos
    4+4 simplificado para v3.x e migramos em v3.1+.
    """
    epoch_secs = int(ts.timestamp())
    if epoch_secs < 0 or epoch_secs > 0xFFFFFFFF:
        raise ValueError(
            f"UtcTime overflow: timestamp {epoch_secs} fora de "
            f"[0, 2^32-1]. Range válido: 1970..2106."
        )
    nanos = ts.microsecond * 1000   # microsecond → nanosecond
    return epoch_secs.to_bytes(4, "big") + nanos.to_bytes(4, "big")


# ---------------------------------------------------------------------------
# SV ASDU encoder (estrutural — IEC 61850-9-2 §6)
# ---------------------------------------------------------------------------


def encode_sv_asdu(
    *,
    sv_id: str,
    smp_cnt: int,
    samples: list,
    conf_rev: int = 1,
) -> bytes:
    """
    Encode SV ASDU como BER (IEC 61850-9-2 §6.2).

    Estrutura:
    ::

        ASDU ::= SEQUENCE {
            svID    [0] IMPLICIT VisibleString,
            smpCnt  [2] IMPLICIT OCTET STRING (16 bits BE),
            confRev [3] IMPLICIT OCTET STRING (32 bits BE),
            smpSynch [5] IMPLICIT OCTET STRING (1 byte),
            sample  [6] IMPLICIT OCTET STRING (samples concatenados,
                        each as int32 BE)
        }
    """
    fields = []
    fields.append(encode_implicit_tagged(0, sv_id.encode("ascii")))
    fields.append(encode_implicit_tagged(
        2, smp_cnt.to_bytes(2, "big"),
    ))
    fields.append(encode_implicit_tagged(
        3, conf_rev.to_bytes(4, "big"),
    ))
    fields.append(encode_implicit_tagged(5, b"\x00"))   # smpSynch
    # Samples: each int32 BE
    sample_bytes = b"".join(
        int(v).to_bytes(4, "big", signed=True) for v in samples
    )
    fields.append(encode_implicit_tagged(6, sample_bytes))

    body = b"".join(fields)
    # ASDU é SEQUENCE constructed
    return bytes([0x30]) + encode_length(len(body)) + body
