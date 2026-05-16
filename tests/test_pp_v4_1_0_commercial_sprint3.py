"""
tests/test_pp_v4_1_0_commercial_sprint3.py — Sprint commercial-3.

Cobre o build dual Pro/Community:

* Specs PyInstaller existentes e bem-formados
* Runtime hook do Community força tier educational
* Script de build aceita --edition pro|community|both
* Lista FORBIDDEN_PATHS_IN_BUNDLE inclui caminhos críticos
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = PROJECT_ROOT / "build"


# ---------------------------------------------------------------------------
# Spec existence + content
# ---------------------------------------------------------------------------


class TestSpecFiles:

    def test_pro_spec_exists(self):
        assert (BUILD_DIR / "olivas_pro.spec").is_file()

    def test_community_spec_exists(self):
        assert (BUILD_DIR / "olivas_community.spec").is_file()

    def test_runtime_hook_exists(self):
        assert (BUILD_DIR / "runtime_hook_community.py").is_file()

    def test_build_script_exists(self):
        assert (BUILD_DIR / "build_distribution.py").is_file()

    def test_pro_spec_names_executable_correctly(self):
        content = (BUILD_DIR / "olivas_pro.spec").read_text(encoding="utf-8")
        assert 'name="OlivasPSS-Pro"' in content

    def test_community_spec_names_executable_correctly(self):
        content = (
            BUILD_DIR / "olivas_community.spec"
        ).read_text(encoding="utf-8")
        assert 'name="OlivasPSS-Community"' in content

    def test_community_spec_uses_runtime_hook(self):
        content = (
            BUILD_DIR / "olivas_community.spec"
        ).read_text(encoding="utf-8")
        assert "runtime_hook_community.py" in content
        assert "runtime_hooks=runtime_hooks" in content


# ---------------------------------------------------------------------------
# Forbidden paths (clean-room)
# ---------------------------------------------------------------------------


REQUIRED_FORBIDDEN_PATHS = [
    "GNUATP",
    "pre-processor",
    "_tmp_ptw",
    "PTW_MANUAL",
    "LIBRARY",
    "library_relay/SEL",
    "restore_points",
    "runs",
]


class TestCleanRoomExclusions:

    def test_pro_spec_lists_forbidden_paths(self):
        content = (BUILD_DIR / "olivas_pro.spec").read_text(encoding="utf-8")
        for forbidden in REQUIRED_FORBIDDEN_PATHS:
            assert forbidden in content, (
                f"olivas_pro.spec deve mencionar '{forbidden}' em "
                f"FORBIDDEN_PATHS_IN_BUNDLE"
            )

    def test_community_spec_lists_forbidden_paths(self):
        content = (
            BUILD_DIR / "olivas_community.spec"
        ).read_text(encoding="utf-8")
        for forbidden in REQUIRED_FORBIDDEN_PATHS:
            assert forbidden in content, (
                f"olivas_community.spec deve mencionar '{forbidden}'"
            )

    def test_build_script_lists_forbidden_paths(self):
        content = (
            BUILD_DIR / "build_distribution.py"
        ).read_text(encoding="utf-8")
        for forbidden in REQUIRED_FORBIDDEN_PATHS:
            assert forbidden in content, (
                f"build_distribution.py deve mencionar '{forbidden}'"
            )

    def test_pro_spec_has_filter_logic(self):
        """O spec deve aplicar o filtro defensivo de _is_forbidden."""
        content = (BUILD_DIR / "olivas_pro.spec").read_text(encoding="utf-8")
        assert "_is_forbidden" in content
        assert "a.datas = [(dest, src, kind)" in content

    def test_community_spec_has_filter_logic(self):
        content = (
            BUILD_DIR / "olivas_community.spec"
        ).read_text(encoding="utf-8")
        assert "_is_forbidden" in content


# ---------------------------------------------------------------------------
# Runtime hook behavior
# ---------------------------------------------------------------------------


class TestRuntimeHookBehavior:

    def test_runtime_hook_sets_env_var(self):
        content = (
            BUILD_DIR / "runtime_hook_community.py"
        ).read_text(encoding="utf-8")
        assert 'OLIVAS_BUILD_EDITION' in content
        assert '"community"' in content

    def test_feature_gates_respects_community_env_var(self, monkeypatch):
        """
        Quando OLIVAS_BUILD_EDITION=community, current_tier() deve
        retornar 'educational' mesmo se houver licença ativa
        (curto-circuita o license_server_client check).
        """
        from app.commercial.feature_gates import current_tier, set_tier_override

        # Desliga override de teste (conftest seta enterprise)
        set_tier_override(None)
        monkeypatch.setenv("OLIVAS_BUILD_EDITION", "community")

        # Simula que existe licença commercial cacheada
        import time
        future = int(time.time()) + 86400
        monkeypatch.setattr(
            "app.commercial.license_server_client.check_active_license",
            lambda: __import__(
                "app.commercial.license_server_client",
                fromlist=["VerifiedLicense"],
            ).VerifiedLicense(
                tier="commercial",
                customer_id="X",
                expiry_unix=future,
                token="t",
            ),
        )

        # Community force educational mesmo com licença commercial
        assert current_tier() == "educational"

    def test_feature_gates_without_community_env_var_works_normally(
        self, monkeypatch
    ):
        """Sem a env var, current_tier() segue fluxo normal."""
        from app.commercial.feature_gates import current_tier, set_tier_override

        set_tier_override(None)
        monkeypatch.delenv("OLIVAS_BUILD_EDITION", raising=False)

        # Sem licença → educational
        monkeypatch.setattr(
            "app.commercial.license_server_client.check_active_license",
            lambda: None,
        )
        # Remove legacy QSettings também
        try:
            from PySide6.QtCore import QSettings
            QSettings("OlivasATPStudio", "OlivasATPStudio").remove(
                "commercial/legacy_license_key"
            )
        except ImportError:
            pass

        assert current_tier() == "educational"


# ---------------------------------------------------------------------------
# Build script (smoke: validar argparse, sem invocar PyInstaller)
# ---------------------------------------------------------------------------


class TestBuildScript:

    def test_build_script_loadable(self):
        import sys
        sys.path.insert(0, str(BUILD_DIR))
        try:
            import build_distribution  # noqa: F401
        finally:
            sys.path.pop(0)

    def test_build_script_has_editions_dict(self):
        import sys
        sys.path.insert(0, str(BUILD_DIR))
        try:
            import build_distribution as bd
            assert "pro" in bd.EDITIONS
            assert "community" in bd.EDITIONS
            assert bd.EDITIONS["pro"][1] == "OlivasPSS-Pro"
            assert bd.EDITIONS["community"][1] == "OlivasPSS-Community"
        finally:
            sys.path.pop(0)

    def test_verify_bundle_clean_detects_violations(self, tmp_path):
        """_verify_bundle_clean deve flagar caminhos proibidos."""
        import sys
        sys.path.insert(0, str(BUILD_DIR))
        try:
            import build_distribution as bd
            # Cria bundle simulado com violação
            fake_bundle = tmp_path / "bundle"
            fake_bundle.mkdir()
            (fake_bundle / "GNUATP").mkdir()
            (fake_bundle / "GNUATP" / "tpbigg32.exe").write_bytes(b"\x00")

            violations = bd._verify_bundle_clean(fake_bundle)
            assert any("GNUATP" in v for v in violations)
        finally:
            sys.path.pop(0)

    def test_verify_bundle_clean_passes_clean_bundle(self, tmp_path):
        import sys
        sys.path.insert(0, str(BUILD_DIR))
        try:
            import build_distribution as bd
            fake_bundle = tmp_path / "bundle"
            fake_bundle.mkdir()
            (fake_bundle / "OlivasPSS-Pro.exe").write_bytes(b"\x00")
            (fake_bundle / "_internal").mkdir()
            (fake_bundle / "_internal" / "app.pyc").write_bytes(b"\x00")

            violations = bd._verify_bundle_clean(fake_bundle)
            assert violations == []
        finally:
            sys.path.pop(0)
