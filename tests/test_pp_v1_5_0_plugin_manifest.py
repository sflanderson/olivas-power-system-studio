"""
tests/test_pp_v1_5_0_plugin_manifest.py — v1.5.0 Sprint A.

Cobre o módulo ``app.plugins.manifest`` (Pydantic schema +
YAML round-trip + validação de campos).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


# ===========================================================================
# Sprint A — Manifest schema (Pydantic)
# ===========================================================================


class TestPluginManifestEnums:

    def test_permission_enum_loadable(self):
        from app.plugins.manifest import PluginPermission
        assert PluginPermission.STUDIES.value == "studies"
        assert PluginPermission.NETWORK.value == "network"

    def test_category_enum_loadable(self):
        from app.plugins.manifest import PluginCategory
        assert PluginCategory.STUDY.value == "study"
        assert PluginCategory.EXPORTER.value == "exporter"


class TestPluginManifestModel:

    def test_minimal_valid_manifest(self):
        from app.plugins.manifest import PluginManifest, PluginCategory
        m = PluginManifest(
            name="my_plugin",
            display_name="My Plugin",
            version="1.0.0",
            author="Test",
            description="A test plugin",
            min_olivas_version="1.5.0",
            category=PluginCategory.STUDY,
        )
        assert m.name == "my_plugin"
        assert m.entry_point == "plugin.py"   # default
        assert m.permissions == []
        assert m.tags == []

    def test_rejects_uppercase_name(self):
        """Nome deve ser snake_case minúsculo."""
        from app.plugins.manifest import PluginManifest, PluginCategory
        with pytest.raises(Exception):   # ValidationError
            PluginManifest(
                name="MyPlugin",   # capital M é inválido
                display_name="My", version="1.0.0", author="x",
                description="x", min_olivas_version="1.5.0",
                category=PluginCategory.STUDY,
            )

    def test_rejects_short_name(self):
        from app.plugins.manifest import PluginManifest, PluginCategory
        with pytest.raises(Exception):
            PluginManifest(
                name="x",   # < 2 chars
                display_name="x", version="1.0.0", author="x",
                description="x", min_olivas_version="1.5.0",
                category=PluginCategory.STUDY,
            )

    def test_rejects_invalid_semver(self):
        from app.plugins.manifest import PluginManifest, PluginCategory
        with pytest.raises(Exception):
            PluginManifest(
                name="my_plugin",
                display_name="x", version="abc",   # não-semver
                author="x", description="x",
                min_olivas_version="1.5.0",
                category=PluginCategory.STUDY,
            )

    def test_accepts_known_permissions(self):
        from app.plugins.manifest import (
            PluginManifest, PluginPermission, PluginCategory,
        )
        m = PluginManifest(
            name="my_plugin",
            display_name="x", version="1.0.0", author="x",
            description="x", min_olivas_version="1.5.0",
            category=PluginCategory.STUDY,
            permissions=[
                PluginPermission.STUDIES,
                PluginPermission.FILESYSTEM_READ,
            ],
        )
        assert len(m.permissions) == 2

    def test_default_license_is_unknown(self):
        from app.plugins.manifest import PluginManifest, PluginCategory
        m = PluginManifest(
            name="my_plugin", display_name="x", version="1.0.0",
            author="x", description="x",
            min_olivas_version="1.5.0",
            category=PluginCategory.STUDY,
        )
        assert m.license == "Unknown"


class TestManifestYamlRoundTrip:

    def test_load_from_yaml_string(self, tmp_path):
        from app.plugins.manifest import load_manifest_from_yaml
        yaml_text = textwrap.dedent("""\
            schema_version: "1.0"
            name: solar_pv
            display_name: Solar PV Yield
            version: "1.0.0"
            author: Olivas Team
            license: MIT
            description: Calculate yield
            min_olivas_version: "1.5.0"
            category: study
            entry_point: plugin.py
            permissions:
              - studies
              - filesystem.read
            tags:
              - solar
              - photovoltaic
            """)
        m = load_manifest_from_yaml(yaml_text)
        assert m.name == "solar_pv"
        assert m.license == "MIT"
        assert "studies" in [p.value for p in m.permissions]
        assert "solar" in m.tags

    def test_load_from_path(self, tmp_path):
        from app.plugins.manifest import load_manifest_from_path
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(textwrap.dedent("""\
            name: test_x
            display_name: Test X
            version: "0.1.0"
            author: TBD
            description: TBD
            min_olivas_version: "1.5.0"
            category: validator
            """))
        m = load_manifest_from_path(manifest_file)
        assert m.name == "test_x"
        assert m.category.value == "validator"

    def test_invalid_manifest_raises(self, tmp_path):
        from app.plugins.manifest import load_manifest_from_yaml
        with pytest.raises(Exception):
            load_manifest_from_yaml("name: 123\n")   # missing required


class TestManifestVersionRange:

    def test_is_compatible_with_olivas_inside_range(self):
        from app.plugins.manifest import (
            PluginManifest, PluginCategory,
        )
        m = PluginManifest(
            name="my_plugin", display_name="x", version="1.0.0",
            author="x", description="x",
            min_olivas_version="1.5.0",
            max_olivas_version="2.0.0",
            category=PluginCategory.STUDY,
        )
        assert m.is_compatible_with_olivas("1.5.0") is True
        assert m.is_compatible_with_olivas("1.7.0") is True
        assert m.is_compatible_with_olivas("2.0.0") is True

    def test_is_compatible_below_min_returns_false(self):
        from app.plugins.manifest import (
            PluginManifest, PluginCategory,
        )
        m = PluginManifest(
            name="my_plugin", display_name="x", version="1.0.0",
            author="x", description="x",
            min_olivas_version="1.5.0",
            category=PluginCategory.STUDY,
        )
        assert m.is_compatible_with_olivas("1.4.4") is False

    def test_is_compatible_no_max_means_unbounded(self):
        from app.plugins.manifest import (
            PluginManifest, PluginCategory,
        )
        m = PluginManifest(
            name="my_plugin", display_name="x", version="1.0.0",
            author="x", description="x",
            min_olivas_version="1.5.0",
            category=PluginCategory.STUDY,
            # max_olivas_version omitted → null
        )
        assert m.is_compatible_with_olivas("99.0.0") is True
