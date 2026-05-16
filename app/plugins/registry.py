"""
app.plugins.registry — registry e discovery de plugins
(v0.105.0).
"""

from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


# Registries globais
_STUDIES: dict[str, Callable] = {}
_EQUIPMENT: dict[str, dict[str, Callable]] = {}   # vendor → category → fn
_PLUGIN_INFOS: list["PluginInfo"] = []


@dataclass(frozen=True)
class PluginInfo:
    """Metadados de um plugin descoberto."""

    name: str
    module_path: str
    studies: tuple[str, ...] = field(default_factory=tuple)
    equipment_vendors: tuple[str, ...] = field(default_factory=tuple)
    version: str = "0.0.1"
    author: str = ""
    description: str = ""


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------


def register_study(name: str) -> Callable:
    """
    Decorator: registra uma função como novo estudo custom.

    O estudo aparece automaticamente no menu Análise e na
    API ``app.postprocessor.studies``.

    Exemplo::

        @register_study("solar_pv_yield")
        def calculate_yield(project, **kwargs):
            ...
            return result
    """
    def decorator(fn: Callable) -> Callable:
        if name in _STUDIES:
            raise ValueError(
                f"Estudo {name!r} já registrado por outro plugin"
            )
        _STUDIES[name] = fn
        return fn
    return decorator


def register_equipment(
    vendor: str, *, category: str = "generic",
) -> Callable:
    """
    Decorator: registra entries de equipamentos por fabricante.

    A função decorada deve retornar uma lista de dicts com
    metadados do equipamento (model_id, ratings, etc).

    Exemplo::

        @register_equipment("CustomVendor", category="relay")
        def my_relays():
            return [
                {"model_id": "CV-501", "voltage_class": "MV", ...},
                ...
            ]
    """
    def decorator(fn: Callable) -> Callable:
        _EQUIPMENT.setdefault(vendor, {})[category] = fn
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_plugins(
    *,
    user_dir: Optional[Path] = None,
    project_dir: Optional[Path] = None,
) -> list[PluginInfo]:
    """
    Descobre e carrega plugins de:

    1. ``user_dir`` (default ``~/.olivas/plugins/``)
    2. ``project_dir`` (default ``./plugins/``)
    3. Pacotes PyPI ``olivas_plugin_*`` (futuro)

    Returns
    -------
    list[PluginInfo]
        Lista de plugins descobertos.
    """
    discovered: list[PluginInfo] = []

    user_dir = user_dir or Path.home() / ".olivas" / "plugins"
    project_dir = project_dir or Path.cwd() / "plugins"

    for plugin_dir in (user_dir, project_dir):
        if not plugin_dir.is_dir():
            continue
        # Add to sys.path for imports
        sys.path.insert(0, str(plugin_dir.parent))
        try:
            for py_file in plugin_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                module_name = (
                    f"{plugin_dir.name}.{py_file.stem}"
                )
                try:
                    studies_before = set(_STUDIES.keys())
                    eqv_before = set(_EQUIPMENT.keys())

                    importlib.import_module(module_name)

                    new_studies = (
                        set(_STUDIES.keys()) - studies_before
                    )
                    new_vendors = (
                        set(_EQUIPMENT.keys()) - eqv_before
                    )

                    info = PluginInfo(
                        name=py_file.stem,
                        module_path=str(py_file),
                        studies=tuple(sorted(new_studies)),
                        equipment_vendors=tuple(sorted(new_vendors)),
                    )
                    discovered.append(info)
                    _PLUGIN_INFOS.append(info)
                except Exception as exc:
                    from app.core.logging_config import get_logger
                    get_logger(__name__).warning(
                        "Falha ao carregar plugin %s: %s",
                        py_file.name, exc,
                    )
        finally:
            if str(plugin_dir.parent) in sys.path:
                sys.path.remove(str(plugin_dir.parent))

    return discovered


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


def get_registered_studies() -> dict[str, Callable]:
    """Retorna dict {study_name: function} dos estudos registrados."""
    return dict(_STUDIES)


def get_registered_equipment() -> dict[str, dict[str, Callable]]:
    """Retorna dict {vendor: {category: function}}."""
    return {v: dict(c) for v, c in _EQUIPMENT.items()}


def reset_for_tests() -> None:
    """Limpa todos os registries — usado em testes isolados."""
    _STUDIES.clear()
    _EQUIPMENT.clear()
    _PLUGIN_INFOS.clear()
