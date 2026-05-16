"""
app.i18n — Internationalization (PT/EN/ES) — v2.0.0 Sprint A.

Olivas é um produto **brasileiro de origem** com PT como locale
default. Esta release adiciona suporte a EN e ES para mercado
LATAM e global.

API
====

::

    from app.i18n import _, set_locale

    # Default: PT
    print(_("Análise"))   # → "Análise"

    # Switch to EN
    set_locale("en")
    print(_("Análise"))   # → "Analysis"

    # Switch to ES
    set_locale("es")
    print(_("Análise"))   # → "Análisis"

Princípios (anti-alucinação)
=============================

* Cobertura **incremental** — começa com ~150 strings principais
  (menus, dialogs, botões frequentes); cobertura completa fica
  para v2.1+
* Strings sem entry no locale ativo retornam **passthrough**
  (string original PT) — sem inventar tradução
* Fallback para PT quando locale inválido (anti-crash)

Princípios (anti-perda)
========================

* `set_locale()` é opt-in — código existente que não chama
  continua funcionando em PT
* Traduções carregadas lazy de arquivos JSON em
  ``translations/<locale>.json``
* Locale é process-global; thread-safe via lock simples
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, Optional


_SUPPORTED_LOCALES = ("pt", "en", "es")
_DEFAULT_LOCALE = "pt"


# Estado global
_lock = threading.Lock()
_current_locale = _DEFAULT_LOCALE
_translations: Dict[str, Dict[str, str]] = {}   # locale → {key: translation}


def _translations_dir() -> Path:
    return Path(__file__).parent / "translations"


def _load_translations(locale: str) -> Dict[str, str]:
    """Carrega translations/<locale>.json se existir."""
    path = _translations_dir() / f"{locale}.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def set_locale(locale: str) -> None:
    """
    Set locale ativo. Locales suportados: pt, en, es.
    Locales inválidos caem para `pt` (default).
    """
    global _current_locale
    with _lock:
        if locale in _SUPPORTED_LOCALES:
            _current_locale = locale
        else:
            _current_locale = _DEFAULT_LOCALE
        # Lazy load
        if _current_locale not in _translations:
            _translations[_current_locale] = _load_translations(
                _current_locale,
            )


def get_locale() -> str:
    """Retorna locale ativo."""
    return _current_locale


def reset_locale() -> None:
    """Reset para default PT."""
    set_locale(_DEFAULT_LOCALE)


def _(text: str) -> str:
    """
    Traduz `text` para o locale ativo.

    Se locale é PT (default) ou key não existe, retorna `text`
    inalterado (passthrough).

    Anti-alucinação: NUNCA inventa tradução se não há entry.
    """
    if _current_locale == _DEFAULT_LOCALE:
        return text
    table = _translations.get(_current_locale, {})
    return table.get(text, text)


# Alias canônico Python (paridade gettext)
t = _


__all__ = [
    "_",
    "t",
    "set_locale",
    "get_locale",
    "reset_locale",
    "get_locale_choices",
    "get_coverage_stats",
]


# ---------------------------------------------------------------------------
# v2.1.0 — Locale UI helpers
# ---------------------------------------------------------------------------


def get_locale_choices() -> list:
    """
    Lista de locales suportados para UI de Configurações.

    Returns
    -------
    list[tuple[str, str]]
        ``[("pt", "Português"), ("en", "English"), ("es", "Español")]``
    """
    return [
        ("pt", "Português"),
        ("en", "English"),
        ("es", "Español"),
    ]


def get_coverage_stats() -> dict:
    """
    Estatísticas de cobertura por locale (anti-alucinação:
    valores reais lidos dos JSON, não hardcoded).

    Returns
    -------
    dict[str, int]
        ``{"pt": 0, "en": N, "es": M}`` (PT=0 porque é default
        e usa passthrough; sem JSON necessário)
    """
    stats = {"pt": 0}
    for loc in ("en", "es"):
        # Lazy load se ainda não carregou
        if loc not in _translations:
            _translations[loc] = _load_translations(loc)
        # Conta keys excluindo _meta
        keys = [
            k for k in _translations.get(loc, {})
            if not k.startswith("_")
        ]
        stats[loc] = len(keys)
    return stats
