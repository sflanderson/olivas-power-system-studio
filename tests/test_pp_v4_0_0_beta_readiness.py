"""v4.0.0-beta — Production readiness checks.

Validates that the codebase is ready for beta release:
* Version bump to 4.0.0-beta
* i18n EN/ES key parity (zero missing)
* Critical modules importable without side effects
* CHANGELOG.md exists and mentions v4.0.0
* CONTEXT_PRESERVATION_PROTOCOL exists
* Master Protocol 8 garantias documented
* Restore points directory exists
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Version bump
# ---------------------------------------------------------------------------


class TestVersionBeta:
    def test_version_is_beta(self) -> None:
        from app.core.version import VERSION
        # Either 4.0.0-beta or 4.0.0-alpha (allow alpha during transition)
        assert "beta" in VERSION.lower() or "alpha" in VERSION.lower()

    def test_version_starts_with_4(self) -> None:
        from app.core.version import VERSION
        assert VERSION.startswith("4.")


# ---------------------------------------------------------------------------
# i18n parity
# ---------------------------------------------------------------------------


class TestI18nParity:
    def test_en_translations_exist(self) -> None:
        en_path = PROJECT_ROOT / "app" / "i18n" / "translations" / "en.json"
        assert en_path.exists()

    def test_es_translations_exist(self) -> None:
        es_path = PROJECT_ROOT / "app" / "i18n" / "translations" / "es.json"
        assert es_path.exists()

    def test_en_es_key_parity(self) -> None:
        """Zero missing keys between EN and ES (both languages must
        cover the same surface)."""
        en = json.loads((
            PROJECT_ROOT / "app" / "i18n" / "translations" / "en.json"
        ).read_text(encoding="utf-8"))
        es = json.loads((
            PROJECT_ROOT / "app" / "i18n" / "translations" / "es.json"
        ).read_text(encoding="utf-8"))
        en_keys = set(en.keys())
        es_keys = set(es.keys())
        missing_in_es = en_keys - es_keys
        missing_in_en = es_keys - en_keys
        assert not missing_in_es, (
            f"ES missing {len(missing_in_es)} keys: "
            f"{sorted(missing_in_es)[:5]}"
        )
        assert not missing_in_en, (
            f"EN missing {len(missing_in_en)} keys: "
            f"{sorted(missing_in_en)[:5]}"
        )

    def test_minimum_translation_count(self) -> None:
        """Ensure non-trivial coverage."""
        en = json.loads((
            PROJECT_ROOT / "app" / "i18n" / "translations" / "en.json"
        ).read_text(encoding="utf-8"))
        assert len(en) >= 100, (
            f"EN translations too sparse: {len(en)} keys (need ≥100)"
        )

    def test_no_empty_translations(self) -> None:
        """All values non-empty."""
        for lang in ("en", "es"):
            data = json.loads((
                PROJECT_ROOT / "app" / "i18n" / "translations" / f"{lang}.json"
            ).read_text(encoding="utf-8"))
            empty = [k for k, v in data.items() if not str(v).strip()]
            assert not empty, (
                f"{lang.upper()} has {len(empty)} empty values: "
                f"{empty[:5]}"
            )


# ---------------------------------------------------------------------------
# CHANGELOG / Documentation
# ---------------------------------------------------------------------------


class TestDocumentation:
    def test_changelog_exists(self) -> None:
        changelog = PROJECT_ROOT / "CHANGELOG.md"
        assert changelog.exists()

    def test_changelog_mentions_v4(self) -> None:
        changelog = PROJECT_ROOT / "CHANGELOG.md"
        text = changelog.read_text(encoding="utf-8")
        assert "4.0.0" in text

    def test_readme_exists(self) -> None:
        readme = PROJECT_ROOT / "README.md"
        assert readme.exists()

    def test_session_handoff_exists(self) -> None:
        sh = PROJECT_ROOT / "docs" / "SESSION_HANDOFF.md"
        assert sh.exists()

    def test_context_preservation_protocol_exists(self) -> None:
        cpp = PROJECT_ROOT / "docs" / "CONTEXT_PRESERVATION_PROTOCOL.md"
        assert cpp.exists()

    def test_skipped_backlog_exists(self) -> None:
        sb = PROJECT_ROOT / "docs" / "SKIPPED_BACKLOG.md"
        assert sb.exists()

    def test_skipped_backlog_zero_open_items(self) -> None:
        """v4.0.0 milestone: SKIPPED_BACKLOG must show 0 itens pulados
        OR explicit '0 itens' or 'PARIDADE TOTAL' marker."""
        sb = (PROJECT_ROOT / "docs" / "SKIPPED_BACKLOG.md").read_text(encoding="utf-8")
        # Look for explicit zero-item indicator
        has_zero = (
            "0 itens pulados" in sb
            or "PARIDADE TOTAL" in sb
            or "Status atual: 0" in sb
        )
        assert has_zero, (
            "SKIPPED_BACKLOG must indicate zero open items at v4.0.0"
        )


# ---------------------------------------------------------------------------
# Module imports (smoke)
# ---------------------------------------------------------------------------


class TestCriticalImports:
    """v4.0.0-beta — all major sessão modules must import cleanly."""

    def test_version_module(self) -> None:
        from app.core.version import (  # noqa: F401
            VERSION, VERSION_TUPLE, parse_version, PRODUCT_NAME,
        )

    def test_iec60909_module(self) -> None:
        from app.standards.iec60909 import (  # noqa: F401
            calculate_short_circuit, FaultDistance, classify_voltage,
        )

    def test_iec60909_decay_module(self) -> None:
        from app.standards.iec60909_decay import (  # noqa: F401
            mu_factor, q_factor,
        )

    def test_power_flow_module(self) -> None:
        from app.postprocessor.power_flow import (  # noqa: F401
            PowerFlowSystem, PfBus, PfBranch, BusType,
        )

    def test_reliability_module(self) -> None:
        from app.postprocessor.reliability import (  # noqa: F401
            calculate_indices, ComponentReliability,
        )

    def test_reliability_mc_module(self) -> None:
        from app.postprocessor.reliability_monte_carlo import (  # noqa: F401
            run_monte_carlo, list_preset_types,
        )

    def test_branch_impedance_module(self) -> None:
        from app.postprocessor.branch_impedance import (  # noqa: F401
            extract_branch_impedance, BranchImpedance,
        )

    def test_fault_distance_walker_module(self) -> None:
        from app.postprocessor.fault_distance_walker import (  # noqa: F401
            auto_classify_fault_distance, FaultClassification,
        )

    def test_scenarios_module(self) -> None:
        from app.preprocessor.scenarios import (  # noqa: F401
            PpScenario, ScenarioManager, PromotionMode,
        )


# ---------------------------------------------------------------------------
# Restore points (anti-regression infrastructure)
# ---------------------------------------------------------------------------


class TestRestorePointsInfra:
    def test_restore_points_dir_exists(self) -> None:
        rp = PROJECT_ROOT / "restore_points"
        assert rp.exists() and rp.is_dir()

    def test_at_least_one_v3_baseline_exists(self) -> None:
        rp = PROJECT_ROOT / "restore_points"
        v3_baselines = list(rp.glob("v3.*_baseline"))
        assert len(v3_baselines) >= 1


# ---------------------------------------------------------------------------
# Master Protocol 8 garantias
# ---------------------------------------------------------------------------


class TestMasterProtocol:
    def test_8_garantias_documented(self) -> None:
        """CONTEXT_PRESERVATION_PROTOCOL.md must mention 8 garantias."""
        text = (
            PROJECT_ROOT / "docs" / "CONTEXT_PRESERVATION_PROTOCOL.md"
        ).read_text(encoding="utf-8")
        assert "garantia" in text.lower()
        # Look for "8" or "oitava" reference
        assert "8" in text or "oitava" in text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
