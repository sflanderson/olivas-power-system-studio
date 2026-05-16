"""
app.commercial.feature_gates — Gating de features comerciais
(v4.1.0 commercial Sprint 1).

Filosofia
=========

* **Tier hierarchy explícita**: educational < demo < commercial <
  pro_engineering < enterprise. Funções declaram tier mínimo via
  decorator ``@requires_tier``.
* **Tier source-of-truth**: :func:`current_tier` consulta o license
  server client (cache JWT offline) com fallback para
  :func:`app.commercial.license_key.validate_license_key` (HMAC
  stub para legacy).
* **GUI-friendly**: :func:`is_feature_available` é uma checagem
  silenciosa (sem exception) para gray-out de menus e ações.
* **Backend-friendly**: ``@requires_tier`` ergue
  :class:`LicenseRequiredError` que o caller pode capturar e
  converter em diálogo "Upgrade para Pro" ou em log estruturado.

Anti-alucinação
===============

* Lista de features comerciais é estática (FEATURE_TIER_MAP). Não
  inventar nomes — adicionar aqui e referenciar pela constante.
* Em ambiente de teste (sem QSettings/PySide6), default é
  ``educational`` — não falha silenciosamente nem libera Pro.
"""

from __future__ import annotations

import functools
import os
from typing import Callable, Dict, Optional, TypeVar


_BUILD_EDITION_ENV = "OLIVAS_BUILD_EDITION"


# ---------------------------------------------------------------------------
# Tier hierarchy
# ---------------------------------------------------------------------------

# Ordem do menos privilegiado para o mais privilegiado.
_TIER_ORDER = (
    "invalid",
    "educational",
    "demo",
    "commercial",        # = Pro Individual
    "pro_engineering",   # = Pro Engenharia
    "enterprise",        # = Empresarial
)


def _tier_rank(tier: str) -> int:
    try:
        return _TIER_ORDER.index(tier)
    except ValueError:
        return 0  # tratado como "invalid"


# ---------------------------------------------------------------------------
# Feature catalog
# ---------------------------------------------------------------------------


class Feature:
    """Constantes de nome de feature — referência única e auditável."""

    AUDIT_TRAIL_SHA256 = "audit_trail_sha256"
    PDF_PROFESSIONAL = "pdf_professional"
    AI_LAUDO = "ai_laudo"
    RELIABILITY_MC = "reliability_monte_carlo"
    ARC_FLASH_MC = "arc_flash_monte_carlo"
    POWER_FLOW_MC = "power_flow_monte_carlo"
    PREMIUM_RELAY_LIBRARY = "premium_relay_library"
    NBR_17227_TEMPLATE = "nbr_17227_template"
    MULTI_SEAT = "multi_seat"
    WHITE_LABEL = "white_label"
    ETAP_SKM_IMPORTER = "etap_skm_importer"


# Tier MÍNIMO requerido por feature.
FEATURE_TIER_MAP: Dict[str, str] = {
    Feature.AUDIT_TRAIL_SHA256: "commercial",
    Feature.PDF_PROFESSIONAL: "commercial",
    Feature.AI_LAUDO: "commercial",
    Feature.RELIABILITY_MC: "commercial",
    Feature.ARC_FLASH_MC: "commercial",
    Feature.POWER_FLOW_MC: "commercial",
    Feature.PREMIUM_RELAY_LIBRARY: "pro_engineering",
    Feature.NBR_17227_TEMPLATE: "pro_engineering",
    Feature.MULTI_SEAT: "enterprise",
    Feature.WHITE_LABEL: "enterprise",
    Feature.ETAP_SKM_IMPORTER: "enterprise",
}


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class LicenseRequiredError(RuntimeError):
    """
    Levantado quando uma chamada requer um tier superior ao
    atual.

    Attributes
    ----------
    feature:
        Nome canônico (de :class:`Feature`).
    required_tier:
        Tier mínimo necessário.
    current_tier:
        Tier ativo no momento.
    """

    def __init__(
        self,
        feature: str,
        required_tier: str,
        current_tier: str,
    ) -> None:
        msg = (
            f"Feature '{feature}' requer tier '{required_tier}' "
            f"(atual: '{current_tier}'). "
            f"Atualize sua licença em Ajuda → Ativar Licença."
        )
        super().__init__(msg)
        self.feature = feature
        self.required_tier = required_tier
        self.current_tier = current_tier


# ---------------------------------------------------------------------------
# Tier resolution
# ---------------------------------------------------------------------------


_TIER_OVERRIDE: Optional[str] = None


def set_tier_override(tier: Optional[str]) -> None:
    """
    Define tier override (para testes e modo development).

    Em produção, **não chamar**. Em testes,
    ``set_tier_override("commercial")`` força tier sem precisar
    de QSettings nem server real.
    """
    global _TIER_OVERRIDE
    _TIER_OVERRIDE = tier


def current_tier() -> str:
    """
    Resolve o tier atual.

    Hierarquia:

    1. Override de teste (``set_tier_override``).
    2. Build edition forçada (``OLIVAS_BUILD_EDITION=community``
       no env, setado pelo runtime hook do bundle Community).
       Curto-circuita para ``educational`` independente de tudo.
    3. JWT cache do license server
       (:func:`license_server_client.check_active_license`).
    4. Fallback HMAC legacy
       (:func:`license_key.validate_license_key` com chave em
       QSettings — formato antigo).
    5. Default ``educational``.
    """
    if _TIER_OVERRIDE is not None:
        return _TIER_OVERRIDE

    if os.environ.get(_BUILD_EDITION_ENV, "").lower() == "community":
        return "educational"

    try:
        from app.commercial.license_server_client import (
            check_active_license,
        )
        license = check_active_license()
        if license is not None:
            return license.tier
    except ImportError:
        pass

    # Fallback legacy (HMAC stub)
    try:
        from PySide6.QtCore import QSettings
        from app.commercial.license_key import validate_license_key

        settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
        legacy_key = settings.value("commercial/legacy_license_key", "")
        if legacy_key:
            result = validate_license_key(str(legacy_key))
            if result.valid:
                return result.tier
    except ImportError:
        pass

    return "educational"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_feature_available(feature: str) -> bool:
    """
    True se o tier atual cobre o tier requerido pela feature.

    GUI usa esta função para gray-out de menus/botões — sem
    exception.
    """
    required = FEATURE_TIER_MAP.get(feature)
    if required is None:
        # Feature não catalogada → considerar aberta (não
        # bloquear features que ainda não foram comercializadas)
        return True

    return _tier_rank(current_tier()) >= _tier_rank(required)


def require_feature(feature: str) -> None:
    """
    Imperativo: ergue :class:`LicenseRequiredError` se a feature
    não está disponível.

    Útil em pontos de entrada de função antes de operação cara.
    """
    required = FEATURE_TIER_MAP.get(feature)
    if required is None:
        return

    tier = current_tier()
    if _tier_rank(tier) < _tier_rank(required):
        raise LicenseRequiredError(
            feature=feature,
            required_tier=required,
            current_tier=tier,
        )


F = TypeVar("F", bound=Callable[..., object])


def requires_tier(tier: str) -> Callable[[F], F]:
    """
    Decorator: ergue :class:`LicenseRequiredError` se o tier
    atual é inferior ao requerido.

    Ao contrário de :func:`require_feature`, este decorator
    não usa ``FEATURE_TIER_MAP`` — é para guardar funções de
    alto nível que não correspondem a uma feature catalogada.

    Examples
    --------
    >>> @requires_tier("commercial")
    ... def generate_pdf_report(project):
    ...     ...
    """

    if tier not in _TIER_ORDER:
        raise ValueError(
            f"Tier '{tier}' não reconhecido. "
            f"Use um de: {_TIER_ORDER}"
        )

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            actual = current_tier()
            if _tier_rank(actual) < _tier_rank(tier):
                raise LicenseRequiredError(
                    feature=fn.__qualname__,
                    required_tier=tier,
                    current_tier=actual,
                )
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def requires_feature(feature: str) -> Callable[[F], F]:
    """
    Decorator: variante de :func:`requires_tier` que consulta
    o catálogo ``FEATURE_TIER_MAP`` pelo nome.

    Examples
    --------
    >>> @requires_feature(Feature.AUDIT_TRAIL_SHA256)
    ... def build_audit_block(project):
    ...     ...
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            require_feature(feature)
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
