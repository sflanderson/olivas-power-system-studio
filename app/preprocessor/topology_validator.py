"""
app.preprocessor.topology_validator — Validação de topologia de
proteção (v1.7.3).

Verifica que o esquemático satisfaz a cadeia canônica:

::

    BUS → BREAKER (T1→T2) → CT (P1→P2) → MOTOR/LOAD
                  ↑                  │
                  │                  ↓ (S1, S2 secundário)
                  │                  │
                  └─ Trip_in ←── Trip_out.RELAY ←─ TC_link.RELAY

Pin connections esperadas
==========================

* **Power chain** (em série):
    BUS.T_RIGHT → BREAKER.T1 → BREAKER.T2 → CT.P1 → CT.P2 → MOTOR.T1

* **Signal chain** (medição):
    CT.S1 → RELAY.TC_link
    (S2 → terra ou comum, geralmente)

* **Trip chain** (proteção):
    RELAY.Trip_out → BREAKER.Trip_in

Anti-alucinação
================

Validador NÃO impõe a topologia — apenas REPORTA desvios. Usuário
pode ter razões legítimas (estudo what-if, exemplos didáticos com
topologia simplificada). Resultado é diagnóstico, não bloqueio.

API
====

::

    from app.preprocessor.topology_validator import (
        validate_protection_chain,
    )

    result = validate_protection_chain(
        components=components, wires=wires,
    )
    if not result.valid:
        for warning in result.warnings:
            print(f"⚠ {warning}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence


@dataclass
class TopologyValidationResult:
    """Resultado da validação."""

    valid: bool
    message: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    components_found: Dict[str, List[str]] = field(default_factory=dict)
    # ex: {"BREAKER": ["Q1"], "CT": ["TC1"], "RELAY": ["R1"]}


def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def validate_protection_chain(
    *,
    components: Sequence[Any],
    wires: Sequence[Any],
) -> TopologyValidationResult:
    """
    Verifica que o esquemático tem cadeia BREAKER + CT + RELAY
    conectada corretamente com Trip wire.

    Parameters
    ----------
    components:
        Lista de dicts ou objetos com ``id``/``type``.
    wires:
        Lista de dicts ou objetos com ``from``/``to``/``from_pin``/
        ``to_pin``.

    Returns
    -------
    :class:`TopologyValidationResult`

    Critério de validade:

    * Se há BREAKER + CT + RELAY no esquemático, **deve haver**
      pelo menos um wire com ``from_pin=Trip_out`` (ou
      ``to_pin=Trip_in``) — senão warning sobre falta de trip.
    * Se há CT, **deve haver** pelo menos um wire conectando
      pin secundário (S1/S2) — senão warning sobre TC não
      conectado a relé.
    """
    errors: List[str] = []
    warnings: List[str] = []
    found: Dict[str, List[str]] = {}

    # Index components by type
    for c in components:
        ctype = str(_get(c, "type", ""))
        cid = str(_get(c, "id", "") or _get(c, "name", ""))
        if not ctype:
            continue
        found.setdefault(ctype, []).append(cid)

    has_breaker = bool(found.get("BREAKER")) or bool(found.get("VCB"))
    has_ct = bool(found.get("CT"))
    has_relay = bool(found.get("RELAY"))

    # Check trip wire
    if has_breaker and has_relay:
        has_trip_wire = any(
            (
                str(_get(w, "from_pin", "")).lower().startswith("trip_out")
                or str(_get(w, "to_pin", "")).lower().startswith("trip_in")
            )
            for w in wires
        )
        if not has_trip_wire:
            warnings.append(
                "BREAKER + RELAY presentes mas Trip wire ausente. "
                "Esperado: RELAY.Trip_out → BREAKER.Trip_in"
            )

    # Check CT secondary wire
    if has_ct and has_relay:
        has_ct_link = any(
            (
                str(_get(w, "from_pin", "")) in ("S1", "S2")
                or str(_get(w, "to_pin", "")).lower() == "tc_link"
            )
            for w in wires
        )
        if not has_ct_link:
            warnings.append(
                "CT + RELAY presentes mas link de medição ausente. "
                "Esperado: CT.S1 → RELAY.TC_link"
            )

    # Compose message
    n_chain = sum([has_breaker, has_ct, has_relay])
    if n_chain >= 2 and not warnings:
        message = "OK: cadeia de proteção bem conectada."
    elif n_chain == 0:
        message = "Sem componentes de proteção (BREAKER/CT/RELAY)."
    else:
        message = (
            f"Cadeia de proteção parcial: {n_chain}/3 components. "
            f"Verifique {len(warnings)} warnings."
        )

    valid = len(errors) == 0
    return TopologyValidationResult(
        valid=valid,
        message=message,
        errors=errors,
        warnings=warnings,
        components_found=found,
    )
