"""
app.commercial.license_key — License key validation
(v2.0.0 Sprint D).

Filosofia
==========

* **Educational tier** (default): zero chave necessária. Todas
  as features core do Olivas funcionam sem licença.
* **Commercial tier**: chave HMAC-SHA256 valida. Habilita
  features avançadas (PDF profissional, multi-user, support).
* **Demo tier**: chave embutida `DEMO_KEY` para apresentações.

Anti-alucinação
================

Não inventamos chaves comerciais reais. Apenas:
* Algoritmo HMAC-SHA256 documentado (público)
* Chave DEMO embutida com `tier=demo`
* Validação rejeita chaves random (anti-pirata simples)

Em deploy real, vendor (Olivas Team) emite chaves usando:
``python -m app.commercial.license_key generate <customer_id>``
(comando ainda não implementado em v2.0.0; v2.1+).

Format de chave
================

::

    OLV-<TIER>-<CUSTOMER_HASH>-<EXPIRY>-<HMAC>

Exemplos:
* ``OLV-DEMO-XYZ12345-99991231-AABBCCDD`` (demo)
* ``OLV-COMM-AA001234-20260101-1A2B3C4D`` (comercial)
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Optional


# Chave secreta interna (em produção real, vem de env var)
# Anti-alucinação: chave dummy explicitamente identificável.
_HMAC_SECRET = b"OLIVAS_DUMMY_HMAC_SECRET_v2.0.0_TEST_ONLY"

# Demo key embutida — válida indefinidamente, tier=demo
DEMO_KEY = "OLV-DEMO-XYZ12345-99991231-AABBCCDD"


@dataclass(frozen=True)
class LicenseValidationResult:
    """
    Resultado de validar uma chave.

    Attributes
    ----------
    valid:
        True se a chave validou OU se está em educational tier
        (sem chave). False se chave foi fornecida mas é inválida.
    tier:
        "educational" / "demo" / "commercial" / "invalid"
    customer_id:
        Identificador do customer (string), ou None.
    expiry_date:
        YYYYMMDD string, ou None.
    """

    valid: bool
    tier: str
    customer_id: Optional[str] = None
    expiry_date: Optional[str] = None


def validate_license_key(key: str) -> LicenseValidationResult:
    """
    Valida chave de licença.

    Empty/None → educational tier (válido sem chave).
    Demo key → demo tier.
    Inválido → invalid tier.

    Parameters
    ----------
    key:
        String da chave (formato OLV-TIER-CUSTOMER-EXPIRY-HMAC) ou
        empty string.

    Returns
    -------
    :class:`LicenseValidationResult`
    """
    if not key or not key.strip():
        return LicenseValidationResult(
            valid=True,
            tier="educational",
        )

    # Demo key check (constant-time comparison)
    if hmac.compare_digest(key, DEMO_KEY):
        return LicenseValidationResult(
            valid=True,
            tier="demo",
            customer_id="XYZ12345",
            expiry_date="99991231",
        )

    # Format check
    parts = key.split("-")
    if len(parts) != 5 or parts[0] != "OLV":
        return LicenseValidationResult(
            valid=False,
            tier="invalid",
        )

    _, tier_code, customer_id, expiry, provided_hmac = parts

    # Recompute HMAC
    msg = f"OLV-{tier_code}-{customer_id}-{expiry}".encode()
    expected = hmac.new(_HMAC_SECRET, msg, hashlib.sha256).hexdigest()
    expected_truncated = expected[:8].upper()

    if not hmac.compare_digest(provided_hmac.upper(), expected_truncated):
        return LicenseValidationResult(
            valid=False,
            tier="invalid",
        )

    tier_map = {
        "DEMO": "demo",
        "COMM": "commercial",
        "EDU": "educational",
    }
    tier = tier_map.get(tier_code, "invalid")

    return LicenseValidationResult(
        valid=tier != "invalid",
        tier=tier,
        customer_id=customer_id,
        expiry_date=expiry,
    )
