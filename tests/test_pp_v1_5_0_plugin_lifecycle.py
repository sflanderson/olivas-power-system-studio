"""
tests/test_pp_v1_5_0_plugin_lifecycle.py — v1.5.0 Sprint B.

Cobre o módulo ``app.plugins.lifecycle``:

* Lifecycle states persistidos em ``state.json``
* Discovery v2 (manifest-based, 3 fontes: builtin/installed/project)
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest


# ===========================================================================
# Sprint B — Lifecycle states
# ===========================================================================


class TestLifecycleState:

    def test_lifecycle_state_loadable(self):
        from app.plugins.lifecycle import LifecycleState
        assert LifecycleState is not None

    def test_state_default_disabled(self, tmp_path):
        """Plugin sem entrada no state.json é considerado disabled."""
        from app.plugins.lifecycle import LifecycleState
        state = LifecycleState(state_file=tmp_path / "state.json")
        assert state.is_enabled("not_yet_seen") is False

    def test_enable_then_disable_round_trip(self, tmp_path):
        from app.plugins.lifecycle import LifecycleState
        state = LifecycleState(state_file=tmp_path / "state.json")
        state.enable("my_plugin", source="builtin",
                     approved_permissions=["studies"])
        assert state.is_enabled("my_plugin") is True

        state.disable("my_plugin")
        assert state.is_enabled("my_plugin") is False

    def test_state_persisted_to_json(self, tmp_path):
        from app.plugins.lifecycle import LifecycleState
        state_file = tmp_path / "state.json"
        s1 = LifecycleState(state_file=state_file)
        s1.enable(
            "plugin_a", source="builtin",
            approved_permissions=["studies", "filesystem.read"],
        )
        s1.save()

        # Re-abre no mesmo path
        s2 = LifecycleState(state_file=state_file)
        s2.load()
        assert s2.is_enabled("plugin_a") is True
        approved = s2.approved_permissions("plugin_a")
        assert "studies" in approved

    def test_state_json_has_schema_version(self, tmp_path):
        from app.plugins.lifecycle import LifecycleState
        state_file = tmp_path / "state.json"
        s = LifecycleState(state_file=state_file)
        s.enable("p1", source="builtin", approved_permissions=[])
        s.save()
        data = json.loads(state_file.read_text("utf-8"))
        assert data.get("schema_version") == "1.0"


# ===========================================================================
# Sprint B — Discovery v2 (manifest-based)
# ===========================================================================


@pytest.fixture
def fake_plugin_dir(tmp_path):
    """Cria estrutura: tmp/<plugin_name>/manifest.yaml + plugin.py."""
    def _make(plugin_name: str, *, category: str = "study"):
        plugin_dir = tmp_path / plugin_name
        plugin_dir.mkdir()
        (plugin_dir / "manifest.yaml").write_text(textwrap.dedent(f"""\
            name: {plugin_name}
            display_name: {plugin_name.replace('_', ' ').title()}
            version: "1.0.0"
            author: Test
            license: MIT
            description: Test plugin {plugin_name}
            min_olivas_version: "1.5.0"
            category: {category}
            entry_point: plugin.py
            permissions: [studies]
            tags: [test]
            """))
        (plugin_dir / "plugin.py").write_text(textwrap.dedent("""\
            from app.plugins import register_study

            @register_study('test_study_from_plugin')
            def my_study(p):
                return {'ok': True}
            """))
        return plugin_dir
    return _make


class TestDiscoveryV2:

    def test_discover_v2_loadable(self):
        from app.plugins.lifecycle import discover_plugins_v2
        assert discover_plugins_v2 is not None

    def test_discover_finds_plugin_in_user_dir(
        self, tmp_path, fake_plugin_dir,
    ):
        fake_plugin_dir("solar_pv")
        from app.plugins.lifecycle import discover_plugins_v2
        results = discover_plugins_v2(
            user_dir=tmp_path,
            builtin_dir=tmp_path / "nonexistent",
        )
        names = [d.manifest.name for d in results]
        assert "solar_pv" in names

    def test_discover_separates_sources(
        self, tmp_path, fake_plugin_dir,
    ):
        """Plugin em builtin_dir tem source='builtin'; em user_dir
        tem source='installed'."""
        builtin_dir = tmp_path / "builtin"
        builtin_dir.mkdir()
        user_dir = tmp_path / "user"
        user_dir.mkdir()

        # Builtin plugin
        bp = builtin_dir / "from_builtin"
        bp.mkdir()
        (bp / "manifest.yaml").write_text(textwrap.dedent("""\
            name: from_builtin
            display_name: Built-in
            version: "1.0.0"
            author: Olivas
            description: builtin
            min_olivas_version: "1.5.0"
            category: study
            """))

        # User plugin
        up = user_dir / "from_user"
        up.mkdir()
        (up / "manifest.yaml").write_text(textwrap.dedent("""\
            name: from_user
            display_name: User
            version: "1.0.0"
            author: U
            description: user
            min_olivas_version: "1.5.0"
            category: study
            """))

        from app.plugins.lifecycle import discover_plugins_v2
        results = discover_plugins_v2(
            user_dir=user_dir, builtin_dir=builtin_dir,
        )
        sources = {d.manifest.name: d.source for d in results}
        assert sources.get("from_builtin") == "builtin"
        assert sources.get("from_user") == "installed"

    def test_invalid_manifest_logged_and_skipped(
        self, tmp_path,
    ):
        bad = tmp_path / "bad_plugin"
        bad.mkdir()
        # YAML inválido (faltam campos obrigatórios)
        (bad / "manifest.yaml").write_text("name: x\n")

        # Plugin válido para confirmar que continua processando
        good = tmp_path / "good_plugin"
        good.mkdir()
        (good / "manifest.yaml").write_text(textwrap.dedent("""\
            name: good_plugin
            display_name: Good
            version: "1.0.0"
            author: x
            description: x
            min_olivas_version: "1.5.0"
            category: study
            """))

        from app.plugins.lifecycle import discover_plugins_v2
        results = discover_plugins_v2(
            user_dir=tmp_path,
            builtin_dir=tmp_path / "nonexistent",
        )
        names = [d.manifest.name for d in results]
        assert "good_plugin" in names
        assert "x" not in names   # bad foi pulado
