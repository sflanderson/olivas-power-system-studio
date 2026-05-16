"""
app.commercial.license_server_client — Cliente HTTP do license server
(v4.1.0 commercial Sprint 1).

Filosofia
=========

* **Offline-first**: JWT cacheado em QSettings permite uso sem rede
  até a expiração. Refresh é tentado a cada 7 dias quando online.
* **Sem deps novas**: usa ``urllib.request`` stdlib (sem requests).
* **Segurança**: o JWT é assinado pelo server com chave assimétrica;
  o cliente valida apenas a estrutura e expiração — a verificação
  criptográfica real é feita no server. Para offline puro, faríamos
  validação RS256 com chave pública embutida, mas isso fica para
  Sprint 2 (deferred).

Fluxo
=====

::

    1. App inicia
       └─ check_active_license() lê JWT do QSettings
          ├─ se válido (expiry > now): retorna VerifiedLicense
          └─ se expirado ou ausente: retorna None
                                      └─ GUI abre LicenseDialog

    2. Usuário cola chave OLV-COMM-...
       └─ activate(key, machine_id)
          ├─ POST /activate
          ├─ recebe { token, tier, expiry, customer_id }
          ├─ grava em QSettings
          └─ retorna VerifiedLicense

    3. Daily background check
       └─ try_refresh()
          ├─ POST /refresh com token atual
          └─ atualiza QSettings se sucesso

Anti-alucinação
================

* URL do server é configurável via env ``OLIVAS_LICENSE_SERVER_URL``;
  default ``None`` força configuração explícita pré-produção (não
  hardcode-ar para evitar typo silencioso).
* Toda chamada de rede tem timeout de 10s e fallback "tente offline".
* Nenhum dado de rede é logado em texto claro — apenas códigos HTTP.
"""

from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


_DEFAULT_TIMEOUT_SECONDS = 10
_QSETTINGS_TOKEN_KEY = "commercial/license_token"
_QSETTINGS_TIER_KEY = "commercial/license_tier"
_QSETTINGS_EXPIRY_KEY = "commercial/license_expiry"
_QSETTINGS_CUSTOMER_KEY = "commercial/license_customer"
_QSETTINGS_LAST_REFRESH_KEY = "commercial/license_last_refresh"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerifiedLicense:
    """
    Resultado de uma validação local de licença ativa.

    Attributes
    ----------
    tier:
        ``"educational"`` / ``"demo"`` / ``"commercial"`` /
        ``"pro_engineering"`` / ``"enterprise"``.
    customer_id:
        Hash do customer (não é PII bruto).
    expiry_unix:
        Timestamp Unix (segundos) da expiração do JWT.
    token:
        JWT completo (para refresh).
    raw_payload:
        Decodificado para inspeção e logging não-sensível.
    """

    tier: str
    customer_id: str
    expiry_unix: int
    token: str
    raw_payload: Dict[str, Any] = field(default_factory=dict)

    def is_active(self, *, now_unix: Optional[int] = None) -> bool:
        now = now_unix if now_unix is not None else int(time.time())
        return now < self.expiry_unix


@dataclass(frozen=True)
class ActivationResult:
    """Resultado de tentativa de ativação."""

    ok: bool
    license: Optional[VerifiedLicense] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Server URL
# ---------------------------------------------------------------------------


def get_server_url() -> Optional[str]:
    """
    Retorna URL do license server.

    Hierarquia:

    1. Env var ``OLIVAS_LICENSE_SERVER_URL``.
    2. QSettings (configurado via diálogo).
    3. None — não configurado.
    """
    env_url = os.environ.get("OLIVAS_LICENSE_SERVER_URL")
    if env_url:
        return env_url.rstrip("/")

    try:
        from PySide6.QtCore import QSettings
        settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
        v = settings.value("commercial/license_server_url", None)
        if v:
            return str(v).rstrip("/")
    except ImportError:
        pass

    return None


def set_server_url(url: str) -> None:
    """Persiste URL do license server em QSettings."""
    try:
        from PySide6.QtCore import QSettings
        settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
        settings.setValue("commercial/license_server_url", url.rstrip("/"))
        settings.sync()
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# QSettings helpers
# ---------------------------------------------------------------------------


def _qsettings_read() -> Optional[Dict[str, Any]]:
    try:
        from PySide6.QtCore import QSettings
    except ImportError:
        return None

    settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
    token = settings.value(_QSETTINGS_TOKEN_KEY, None)
    tier = settings.value(_QSETTINGS_TIER_KEY, None)
    expiry = settings.value(_QSETTINGS_EXPIRY_KEY, None)
    customer = settings.value(_QSETTINGS_CUSTOMER_KEY, None)

    if not token or not tier or not expiry:
        return None

    try:
        expiry_int = int(expiry)
    except (TypeError, ValueError):
        return None

    return {
        "token": str(token),
        "tier": str(tier),
        "expiry_unix": expiry_int,
        "customer_id": str(customer) if customer else "",
    }


def _qsettings_write(license: VerifiedLicense) -> None:
    try:
        from PySide6.QtCore import QSettings
    except ImportError:
        return

    settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
    settings.setValue(_QSETTINGS_TOKEN_KEY, license.token)
    settings.setValue(_QSETTINGS_TIER_KEY, license.tier)
    settings.setValue(_QSETTINGS_EXPIRY_KEY, license.expiry_unix)
    settings.setValue(_QSETTINGS_CUSTOMER_KEY, license.customer_id)
    settings.setValue(_QSETTINGS_LAST_REFRESH_KEY, int(time.time()))
    settings.sync()


def _qsettings_clear() -> None:
    try:
        from PySide6.QtCore import QSettings
    except ImportError:
        return

    settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
    for k in (
        _QSETTINGS_TOKEN_KEY,
        _QSETTINGS_TIER_KEY,
        _QSETTINGS_EXPIRY_KEY,
        _QSETTINGS_CUSTOMER_KEY,
        _QSETTINGS_LAST_REFRESH_KEY,
    ):
        settings.remove(k)
    settings.sync()


# ---------------------------------------------------------------------------
# Local verification (offline)
# ---------------------------------------------------------------------------


def check_active_license() -> Optional[VerifiedLicense]:
    """
    Lê QSettings e retorna VerifiedLicense se o JWT ainda está
    dentro da validade. Caso contrário, retorna None.

    Não chama rede.
    """
    data = _qsettings_read()
    if data is None:
        return None

    license = VerifiedLicense(
        tier=data["tier"],
        customer_id=data["customer_id"],
        expiry_unix=data["expiry_unix"],
        token=data["token"],
    )

    if not license.is_active():
        return None

    return license


# ---------------------------------------------------------------------------
# HTTP primitives
# ---------------------------------------------------------------------------


def _post_json(
    url: str,
    payload: Dict[str, Any],
    *,
    timeout: int = _DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """
    POST JSON, retorna corpo JSON parseado.

    Levanta ``urllib.error.HTTPError`` em status != 2xx.
    """
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "OlivasPowerStudio/4.1 license-client",
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _decode_jwt_payload(token: str) -> Dict[str, Any]:
    """
    Decodifica payload JWT sem verificar assinatura.

    NÃO usar para autorização — apenas para extrair ``exp``, ``tier``
    e ``customer_id`` para cache. A verificação criptográfica
    autoritativa é feita no server.
    """
    import base64

    try:
        _, payload_b64, _ = token.split(".")
    except ValueError:
        return {}

    # Padding pad para base64url
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return {}


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def activate(key: str, machine_id: str) -> ActivationResult:
    """
    Tenta ativar uma chave no license server.

    Em caso de sucesso, persiste JWT em QSettings e retorna
    ``ActivationResult(ok=True, license=...)``. Em caso de falha,
    retorna ``ActivationResult(ok=False, error_code=...)`` sem
    modificar o estado persistente.

    Parameters
    ----------
    key:
        Chave no formato ``OLV-<TIER>-<CUSTOMER>-<EXPIRY>-<HMAC>``.
    machine_id:
        Fingerprint da máquina obtido de
        :func:`app.commercial.machine_id.get_machine_id`.
    """
    server_url = get_server_url()
    if not server_url:
        return ActivationResult(
            ok=False,
            error_code="server_not_configured",
            error_message="License server URL not set",
        )

    if not key or not key.strip():
        return ActivationResult(
            ok=False,
            error_code="empty_key",
            error_message="License key is empty",
        )

    try:
        body = _post_json(
            f"{server_url}/activate",
            {"key": key.strip(), "machine_id": machine_id},
        )
    except urllib.error.HTTPError as e:
        return ActivationResult(
            ok=False,
            error_code=f"http_{e.code}",
            error_message=e.reason,
        )
    except urllib.error.URLError as e:
        return ActivationResult(
            ok=False,
            error_code="network_error",
            error_message=str(e.reason),
        )
    except (json.JSONDecodeError, ValueError) as e:
        return ActivationResult(
            ok=False,
            error_code="invalid_response",
            error_message=str(e),
        )

    token = body.get("token")
    if not isinstance(token, str) or not token:
        return ActivationResult(
            ok=False,
            error_code="missing_token",
            error_message="Server response missing token",
        )

    payload = _decode_jwt_payload(token)
    tier = body.get("tier") or payload.get("tier", "invalid")
    customer_id = body.get("customer_id") or payload.get("sub", "")
    expiry = body.get("expiry_unix") or payload.get("exp", 0)

    try:
        expiry_int = int(expiry)
    except (TypeError, ValueError):
        return ActivationResult(
            ok=False,
            error_code="invalid_expiry",
            error_message="Server response has invalid expiry",
        )

    license = VerifiedLicense(
        tier=str(tier),
        customer_id=str(customer_id),
        expiry_unix=expiry_int,
        token=token,
        raw_payload=payload,
    )
    _qsettings_write(license)
    return ActivationResult(ok=True, license=license)


def try_refresh() -> ActivationResult:
    """
    Tenta refresh do token atual.

    Se sem token local, retorna ``ok=False`` com
    ``error_code="no_local_token"``.
    """
    server_url = get_server_url()
    if not server_url:
        return ActivationResult(ok=False, error_code="server_not_configured")

    local = _qsettings_read()
    if local is None:
        return ActivationResult(ok=False, error_code="no_local_token")

    try:
        body = _post_json(
            f"{server_url}/refresh",
            {"token": local["token"]},
        )
    except urllib.error.HTTPError as e:
        return ActivationResult(
            ok=False,
            error_code=f"http_{e.code}",
            error_message=e.reason,
        )
    except urllib.error.URLError as e:
        return ActivationResult(
            ok=False,
            error_code="network_error",
            error_message=str(e.reason),
        )

    new_token = body.get("token")
    if not isinstance(new_token, str):
        return ActivationResult(ok=False, error_code="missing_token")

    payload = _decode_jwt_payload(new_token)
    license = VerifiedLicense(
        tier=str(body.get("tier") or payload.get("tier", local["tier"])),
        customer_id=str(
            body.get("customer_id")
            or payload.get("sub", local["customer_id"])
        ),
        expiry_unix=int(
            body.get("expiry_unix") or payload.get("exp", 0)
        ),
        token=new_token,
        raw_payload=payload,
    )
    _qsettings_write(license)
    return ActivationResult(ok=True, license=license)


def clear_local_license() -> None:
    """Remove credenciais locais (logout)."""
    _qsettings_clear()


def days_until_expiry() -> Optional[int]:
    """
    Retorna dias até expiração do token local, ou None se sem token.
    """
    license = check_active_license()
    if license is None:
        return None
    delta_seconds = license.expiry_unix - int(time.time())
    return max(0, delta_seconds // 86400)
