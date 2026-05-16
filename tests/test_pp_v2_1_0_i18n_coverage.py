"""
tests/test_pp_v2_1_0_i18n_coverage.py — v2.1.0.

Cobre:

* Cobertura ampliada (~150 strings por locale)
* EN/ES parity (mesmas keys)
* Helper get_locale_choices
* Helper get_coverage_stats
* Anti-alucinação: nenhuma key em uma língua sem tradução
  na outra
"""

from __future__ import annotations

import pytest


class TestI18nCoverageExpanded:

    def test_en_coverage_at_least_120(self):
        from app.i18n import set_locale, get_coverage_stats
        set_locale("en")
        stats = get_coverage_stats()
        assert stats.get("en", 0) >= 120, (
            f"EN coverage muito baixa: {stats}"
        )

    def test_es_coverage_at_least_120(self):
        from app.i18n import set_locale, get_coverage_stats
        set_locale("es")
        stats = get_coverage_stats()
        assert stats.get("es", 0) >= 120

    def test_en_es_parity(self):
        """Anti-alucinação: mesmas keys nos dois locales."""
        import json
        from pathlib import Path
        i18n_dir = Path(
            "D:/000 - UFMG - DOUTORADO/MVP/app/i18n/translations"
        )
        en = json.loads(
            (i18n_dir / "en.json").read_text(encoding="utf-8")
        )
        es = json.loads(
            (i18n_dir / "es.json").read_text(encoding="utf-8")
        )
        en_keys = set(k for k in en if not k.startswith("_"))
        es_keys = set(k for k in es if not k.startswith("_"))
        diff_en_only = en_keys - es_keys
        diff_es_only = es_keys - en_keys
        assert not diff_en_only, (
            f"Keys em EN mas não ES: {diff_en_only}"
        )
        assert not diff_es_only, (
            f"Keys em ES mas não EN: {diff_es_only}"
        )


class TestLocaleChoices:

    def test_get_locale_choices_returns_list(self):
        from app.i18n import get_locale_choices
        choices = get_locale_choices()
        assert isinstance(choices, list)
        assert len(choices) >= 3

    def test_locale_choices_includes_pt_en_es(self):
        from app.i18n import get_locale_choices
        choices = get_locale_choices()
        codes = [c[0] for c in choices]
        assert "pt" in codes
        assert "en" in codes
        assert "es" in codes

    def test_locale_choices_have_human_labels(self):
        from app.i18n import get_locale_choices
        choices = get_locale_choices()
        for code, label in choices:
            assert label
            assert len(label) >= 2


class TestCommonStringsTranslated:
    """Smoke test que strings comuns têm tradução."""

    def test_save_button_translates_to_en(self):
        from app.i18n import _, set_locale, reset_locale
        set_locale("en")
        result = _("Salvar")
        assert result == "Save"
        reset_locale()

    def test_save_button_translates_to_es(self):
        from app.i18n import _, set_locale, reset_locale
        set_locale("es")
        result = _("Salvar")
        assert result == "Guardar"
        reset_locale()

    def test_circuit_breaker_translates(self):
        from app.i18n import _, set_locale, reset_locale
        set_locale("en")
        assert _("Disjuntor") == "Circuit breaker"
        set_locale("es")
        assert _("Disjuntor") == "Interruptor"
        reset_locale()

    def test_state_open_closed_translates(self):
        """v1.7.1 state property values."""
        from app.i18n import _, set_locale, reset_locale
        set_locale("en")
        assert _("Aberto") == "Open"
        assert _("Fechado") == "Closed"
        reset_locale()

    def test_active_inactive_translates(self):
        from app.i18n import _, set_locale, reset_locale
        set_locale("en")
        assert _("Ativo") == "Active"
        assert _("Inativo") == "Inactive"
        set_locale("es")
        assert _("Ativo") == "Activo"
        assert _("Inativo") == "Inactivo"
        reset_locale()


class TestBackwardCompat:

    def test_v2_0_0_strings_still_work(self):
        """Strings de v2.0.0 (cobertura inicial) continuam OK."""
        from app.i18n import _, set_locale, reset_locale
        set_locale("en")
        assert _("Análise") == "Analysis"
        assert _("Visualizar") == "View"
        assert _("Ferramentas") == "Tools"
        reset_locale()
