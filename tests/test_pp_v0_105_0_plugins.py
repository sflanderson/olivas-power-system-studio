"""
tests/test_pp_v0_105_0_plugins.py — v0.105.0:

Sistema de plugins extensível.
"""

from __future__ import annotations

import pytest

from app.plugins import (
    PluginInfo, discover_plugins,
    get_registered_equipment, get_registered_studies,
    register_equipment, register_study,
)
from app.plugins.registry import reset_for_tests


@pytest.fixture(autouse=True)
def reset_registries():
    reset_for_tests()
    yield
    reset_for_tests()


# ---------------------------------------------------------------------------
# register_study decorator
# ---------------------------------------------------------------------------


class TestRegisterStudy:

    def test_register_simple(self):
        @register_study("custom_test_1")
        def my_study(project):
            return {"ok": True}

        studies = get_registered_studies()
        assert "custom_test_1" in studies
        assert studies["custom_test_1"](None) == {"ok": True}

    def test_duplicate_raises(self):
        @register_study("dup")
        def s1(p):
            return 1

        with pytest.raises(ValueError, match="já registrado"):
            @register_study("dup")
            def s2(p):
                return 2


# ---------------------------------------------------------------------------
# register_equipment decorator
# ---------------------------------------------------------------------------


class TestRegisterEquipment:

    def test_register_relay_vendor(self):
        @register_equipment("CustomVendor", category="relay")
        def my_relays():
            return [{"model_id": "CV-100"}]

        eq = get_registered_equipment()
        assert "CustomVendor" in eq
        assert "relay" in eq["CustomVendor"]
        assert eq["CustomVendor"]["relay"]() == [{"model_id": "CV-100"}]

    def test_multiple_categories_per_vendor(self):
        @register_equipment("V", category="relay")
        def relays():
            return []

        @register_equipment("V", category="motor")
        def motors():
            return []

        eq = get_registered_equipment()
        assert "relay" in eq["V"]
        assert "motor" in eq["V"]


# ---------------------------------------------------------------------------
# discover_plugins
# ---------------------------------------------------------------------------


class TestDiscoverPlugins:

    def test_no_dirs_returns_empty(self, tmp_path):
        # Pass non-existent dirs
        plugins = discover_plugins(
            user_dir=tmp_path / "fake_user",
            project_dir=tmp_path / "fake_project",
        )
        assert plugins == []

    def test_loads_plugin_from_dir(self, tmp_path):
        # Create a fake plugin file
        plugin_dir = tmp_path / "myplugins"
        plugin_dir.mkdir()
        plugin_file = plugin_dir / "test_plugin.py"
        plugin_file.write_text(
            "from app.plugins import register_study\n"
            "\n"
            "@register_study('discovered_study')\n"
            "def my_study(p):\n"
            "    return 'hello'\n"
        )

        plugins = discover_plugins(
            user_dir=plugin_dir,
            project_dir=tmp_path / "nonexistent",
        )
        assert len(plugins) == 1
        assert "discovered_study" in get_registered_studies()


# ---------------------------------------------------------------------------
# PluginInfo dataclass
# ---------------------------------------------------------------------------


class TestPluginInfo:

    def test_creation(self):
        info = PluginInfo(
            name="my_plugin",
            module_path="/path/to/plugin.py",
            studies=("study1", "study2"),
            equipment_vendors=("VendorX",),
            version="1.0.0",
            author="Test User",
        )
        assert info.name == "my_plugin"
        assert len(info.studies) == 2
