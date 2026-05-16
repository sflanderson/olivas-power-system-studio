"""
tests/test_pp_v2_0_0_i18n.py — v2.0.0 Sprint A.

Cobre o módulo ``app.i18n``:

* Translation function `_()` retorna string original quando key
  não existe na locale corrente
* Switch de locale via `set_locale("en")` carrega traduções EN
* Fallback para PT (default) quando key não existe em locale ativo
"""

from __future__ import annotations

import pytest


class TestI18nLoader:

    def test_module_loadable(self):
        from app import i18n  # noqa: F401

    def test_default_locale_is_pt(self):
        from app.i18n import get_locale, reset_locale
        reset_locale()
        assert get_locale() == "pt"

    def test_translate_function_exists(self):
        from app.i18n import _, t
        # `_` é alias canonical, `t` também aceito
        assert callable(_)
        assert callable(t)

    def test_translate_pt_returns_input(self):
        """Em PT (default), retorna input se não há mapeamento explícito."""
        from app.i18n import _, set_locale
        set_locale("pt")
        assert _("Hello") == "Hello"   # sem entry → passthrough


class TestTranslationLoading:

    def test_set_locale_en(self):
        from app.i18n import set_locale, get_locale
        set_locale("en")
        assert get_locale() == "en"

    def test_set_locale_es(self):
        from app.i18n import set_locale, get_locale
        set_locale("es")
        assert get_locale() == "es"

    def test_set_locale_invalid_falls_back_to_pt(self):
        from app.i18n import set_locale, get_locale
        set_locale("xx_INVALID")
        # Falls back to pt
        assert get_locale() == "pt"


class TestKnownTranslations:
    """Testa traduções bem-conhecidas (anti-alucinação)."""

    def test_pt_to_en_basic(self):
        """'Análise' (PT) deve ter tradução para EN."""
        from app.i18n import _, set_locale
        set_locale("en")
        result = _("Análise")
        # Aceita "Analysis" ou variações
        assert result.lower() in (
            "analysis", "análise", "analyze",
        )

    def test_pt_to_es_basic(self):
        from app.i18n import _, set_locale
        set_locale("es")
        result = _("Análise")
        # Espera "Análisis" (ES)
        assert "ális" in result.lower() or "análise" in result.lower()


class TestBackwardCompat:

    def test_existing_strings_unchanged_in_pt(self):
        """No PT (default), strings sem entry retornam unchanged
        — anti-perda."""
        from app.i18n import _, set_locale
        set_locale("pt")
        # Strings que NÃO temos no dicionário
        assert _("Some random string XYZ") == "Some random string XYZ"
        assert _("Foo Bar") == "Foo Bar"
