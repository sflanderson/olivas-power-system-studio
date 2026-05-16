"""
app.plugins — sistema de plugins extensível (v0.105.0).

Permite que terceiros estendam o Olivas com:

* **Novos estudos** (custom analysis modules)
* **Equipamentos vendor-specific** (relés, motores, etc.)
* **Templates de schematic** (sistema solar, eólico, etc.)
* **Reports formatadores** (PDF custom, integração ERP)

Plugins são módulos Python descobertos automaticamente em:

* ``~/.olivas/plugins/`` (user)
* ``./plugins/`` (project local)
* Pacotes PyPI com namespace ``olivas_plugin_*``

API
====

Para criar um plugin custom::

    # ~/.olivas/plugins/my_company.py
    from app.plugins import register_study, register_equipment

    @register_study("my_custom_analysis")
    def my_analysis(project, bus_id, **kwargs):
        ...
        return result

    @register_equipment("MyVendor", category="relay")
    def get_models():
        return [
            {"model_id": "MV-CUSTOM-1", ...}
        ]
"""

from __future__ import annotations

# v0.105.0 — backward-compat API (decorators + bare-py discovery)
from app.plugins.registry import (
    PluginInfo,
    discover_plugins,
    get_registered_studies,
    get_registered_equipment,
    register_equipment,
    register_study,
)

# v1.5.0 — Plugin Marketplace API (manifest + lifecycle + security)
from app.plugins.manifest import (
    PluginCategory,
    PluginManifest,
    PluginPermission,
    load_manifest_from_path,
    load_manifest_from_yaml,
)
from app.plugins.lifecycle import (
    DiscoveredPlugin,
    LifecycleState,
    auto_load_enabled_plugins,
    discover_plugins_v2,
)
from app.plugins.security import (
    InstallResult,
    check_permissions_supported,
    compute_sha256,
    install_plugin,
    uninstall_plugin,
    verify_sha256,
)

__all__ = [
    # v0.105.0 (backward compat)
    "PluginInfo",
    "discover_plugins",
    "get_registered_studies",
    "get_registered_equipment",
    "register_equipment",
    "register_study",
    # v1.5.0 — manifest
    "PluginCategory",
    "PluginManifest",
    "PluginPermission",
    "load_manifest_from_path",
    "load_manifest_from_yaml",
    # v1.5.0 — lifecycle
    "DiscoveredPlugin",
    "LifecycleState",
    "auto_load_enabled_plugins",
    "discover_plugins_v2",
    # v1.5.0 — security
    "InstallResult",
    "check_permissions_supported",
    "compute_sha256",
    "install_plugin",
    "uninstall_plugin",
    "verify_sha256",
]
