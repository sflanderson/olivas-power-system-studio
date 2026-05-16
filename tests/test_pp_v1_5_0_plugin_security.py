"""
tests/test_pp_v1_5_0_plugin_security.py — v1.5.0 Sprint C.

Cobre o módulo ``app.plugins.security``:

* SHA256 hash do entry_point.py
* Permissions whitelist + version compat check
* Install/uninstall workflow
"""

from __future__ import annotations

import hashlib
import textwrap
from pathlib import Path

import pytest


# ===========================================================================
# Sprint C — Security: SHA256
# ===========================================================================


class TestSHA256:

    def test_module_loadable(self):
        from app.plugins import security  # noqa: F401

    def test_compute_sha256_for_known_content(self, tmp_path):
        from app.plugins.security import compute_sha256
        f = tmp_path / "x.py"
        content = b"hello world"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert compute_sha256(f) == expected

    def test_verify_sha256_matches(self, tmp_path):
        from app.plugins.security import compute_sha256, verify_sha256
        f = tmp_path / "p.py"
        f.write_bytes(b"abc")
        h = compute_sha256(f)
        assert verify_sha256(f, h) is True

    def test_verify_sha256_rejects_tampering(self, tmp_path):
        from app.plugins.security import compute_sha256, verify_sha256
        f = tmp_path / "p.py"
        f.write_bytes(b"original")
        h = compute_sha256(f)
        f.write_bytes(b"tampered")
        assert verify_sha256(f, h) is False


# ===========================================================================
# Sprint C — Permissions check
# ===========================================================================


class TestPermissionCheck:

    def test_check_passes_when_all_in_whitelist(self):
        from app.plugins.security import check_permissions_supported
        ok, msg = check_permissions_supported(
            ["studies", "filesystem.read"]
        )
        assert ok is True
        assert msg == ""

    def test_check_rejects_unknown_permission(self):
        from app.plugins.security import check_permissions_supported
        ok, msg = check_permissions_supported(
            ["studies", "exotic_xyz"]
        )
        assert ok is False
        assert "exotic_xyz" in msg


# ===========================================================================
# Sprint C — Install / Uninstall workflow
# ===========================================================================


@pytest.fixture
def fake_plugin_source(tmp_path):
    """Cria diretório de plugin source (simula pacote a instalar)."""
    src = tmp_path / "_source" / "my_plugin"
    src.mkdir(parents=True)
    (src / "manifest.yaml").write_text(textwrap.dedent("""\
        name: my_plugin
        display_name: My Plugin
        version: "1.0.0"
        author: Test
        description: Test plugin
        min_olivas_version: "1.5.0"
        category: study
        permissions: [studies]
        """))
    (src / "plugin.py").write_text(
        "from app.plugins import register_study\n"
        "@register_study('my_plugin_study')\n"
        "def f(p): return 'ok'\n"
    )
    return src


class TestInstallWorkflow:

    def test_install_loadable(self):
        from app.plugins.security import install_plugin  # noqa: F401

    def test_install_copies_to_target(
        self, tmp_path, fake_plugin_source,
    ):
        from app.plugins.security import install_plugin
        target_root = tmp_path / "_target"
        result = install_plugin(
            source_dir=fake_plugin_source,
            target_root=target_root,
            olivas_version="1.5.0",
        )
        assert result.success is True
        assert (target_root / "my_plugin" / "manifest.yaml").exists()
        assert (target_root / "my_plugin" / "plugin.py").exists()

    def test_install_rejects_version_mismatch(
        self, tmp_path, fake_plugin_source,
    ):
        from app.plugins.security import install_plugin
        target_root = tmp_path / "_target"
        result = install_plugin(
            source_dir=fake_plugin_source,
            target_root=target_root,
            olivas_version="1.0.0",   # < min_olivas_version 1.5.0
        )
        assert result.success is False
        assert "compat" in result.message.lower()

    def test_uninstall_removes_dir(
        self, tmp_path, fake_plugin_source,
    ):
        from app.plugins.security import install_plugin, uninstall_plugin
        target_root = tmp_path / "_target"
        install_plugin(
            source_dir=fake_plugin_source,
            target_root=target_root,
            olivas_version="1.5.0",
        )
        assert (target_root / "my_plugin").exists()

        uninstall_plugin(name="my_plugin", target_root=target_root)
        assert not (target_root / "my_plugin").exists()
