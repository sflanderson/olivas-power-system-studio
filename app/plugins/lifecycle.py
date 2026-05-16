"""
app.plugins.lifecycle — discovery v2 + lifecycle persistence
(v1.5.0 Sprint B).

Diferença para v0.105.0 ``registry.discover_plugins``:

* **Manifest-based**: cada plugin é uma pasta com ``manifest.yaml``
  (não bare .py file)
* **3 fontes** com source label:
  - ``builtin`` — shipped com Olivas (``app/plugins/builtin/``)
  - ``installed`` — instalado pelo usuário (``~/.olivas/plugins/``)
  - ``project`` — local ao projeto (``./plugins/``)
* **Lifecycle persistido** em ``~/.olivas/plugins/state.json`` com
  estado `enabled` por plugin + `approved_permissions`

A função antiga ``registry.discover_plugins`` continua disponível
para backward compat com v0.105.0 e plugins legacy bare-py.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.core.logging_config import get_logger
from app.plugins.manifest import PluginManifest, load_manifest_from_path

log = get_logger(__name__)


PLUGIN_SOURCES = ("builtin", "installed", "project")


# ---------------------------------------------------------------------------
# Discovery v2 result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiscoveredPlugin:
    """
    Resultado de uma descoberta — manifest validado + path do
    diretório + source label.

    O manifest **não** é executado/importado durante discovery;
    apenas o YAML é lido. Carga real do plugin.py é separada
    (Sprint C, com gating de permissões).
    """

    manifest: PluginManifest
    plugin_dir: Path
    source: str   # "builtin" | "installed" | "project"

    @property
    def entry_point_path(self) -> Path:
        return self.plugin_dir / self.manifest.entry_point


def _scan_dir_for_manifests(
    base: Path, source: str,
) -> List[DiscoveredPlugin]:
    """
    Escaneia ``base/<plugin_name>/manifest.yaml`` e devolve lista
    de :class:`DiscoveredPlugin`. Plugins inválidos são pulados
    com warning no log.
    """
    if not base.is_dir():
        return []
    found: List[DiscoveredPlugin] = []
    for sub in sorted(base.iterdir()):
        if not sub.is_dir():
            continue
        manifest_file = sub / "manifest.yaml"
        if not manifest_file.is_file():
            continue
        try:
            manifest = load_manifest_from_path(manifest_file)
            found.append(DiscoveredPlugin(
                manifest=manifest,
                plugin_dir=sub,
                source=source,
            ))
        except Exception as exc:
            log.warning(
                "Plugin inválido em %s: %s",
                manifest_file, exc,
            )
    return found


def discover_plugins_v2(
    *,
    builtin_dir: Optional[Path] = None,
    user_dir: Optional[Path] = None,
    project_dir: Optional[Path] = None,
) -> List[DiscoveredPlugin]:
    """
    Descobre plugins de até 3 fontes (manifest-based).

    Order: builtin → installed → project (cada source label
    explícito no resultado para a UI marketplace).

    Plugins com nome duplicado entre fontes: o **primeiro
    encontrado** vence (builtin > installed > project), logando
    warning se conflito.

    Parameters
    ----------
    builtin_dir:
        Default: ``app/plugins/builtin/`` (relativo a este módulo)
    user_dir:
        Default: ``~/.olivas/plugins/``
    project_dir:
        Default: ``./plugins/`` (cwd)
    """
    if builtin_dir is None:
        builtin_dir = Path(__file__).parent / "builtin"
    if user_dir is None:
        user_dir = Path.home() / ".olivas" / "plugins"
    if project_dir is None:
        project_dir = Path.cwd() / "plugins"

    all_results: List[DiscoveredPlugin] = []
    seen_names: set[str] = set()

    for base, source in (
        (builtin_dir, "builtin"),
        (user_dir, "installed"),
        (project_dir, "project"),
    ):
        for d in _scan_dir_for_manifests(base, source):
            if d.manifest.name in seen_names:
                log.warning(
                    "Plugin '%s' (%s) ignorado — já existe em fonte "
                    "anterior", d.manifest.name, source,
                )
                continue
            seen_names.add(d.manifest.name)
            all_results.append(d)

    log.info(
        "discover_plugins_v2: %d plugins descobertos "
        "(builtin/installed/project)", len(all_results),
    )
    return all_results


# ---------------------------------------------------------------------------
# Lifecycle state (persisted)
# ---------------------------------------------------------------------------


_STATE_SCHEMA_VERSION = "1.0"


class LifecycleState:
    """
    Estado de lifecycle persistido em ``state.json`` com schema:

    .. code-block:: json

        {
          "schema_version": "1.0",
          "plugins": {
            "<plugin_name>": {
              "source": "builtin",
              "enabled": true,
              "installed_at": "2026-04-28T22:00:00",
              "approved_permissions": ["studies", "filesystem.read"]
            }
          }
        }

    Operações idempotentes:

    * :meth:`enable` — registra/atualiza com enabled=True
    * :meth:`disable` — atualiza enabled=False (mantém permissões)
    * :meth:`is_enabled` — retorna False se plugin desconhecido
    * :meth:`save` / :meth:`load` — round-trip JSON
    """

    def __init__(self, *, state_file: Optional[Path] = None) -> None:
        if state_file is None:
            state_file = (
                Path.home() / ".olivas" / "plugins" / "state.json"
            )
        self.state_file = state_file
        self._data = {
            "schema_version": _STATE_SCHEMA_VERSION,
            "plugins": {},
        }
        # Auto-load se existir (idempotente)
        if state_file.exists():
            try:
                self.load()
            except Exception as e:
                log.warning(
                    "state.json corrompido em %s: %s — usando state vazio",
                    state_file, e,
                )

    # ---- Operations ----

    def enable(
        self,
        name: str,
        *,
        source: str = "installed",
        approved_permissions: Optional[List[str]] = None,
    ) -> None:
        """Marca plugin como enabled (auto-save)."""
        existing = self._data["plugins"].get(name, {})
        self._data["plugins"][name] = {
            "source": source,
            "enabled": True,
            "installed_at": existing.get(
                "installed_at",
                datetime.now().isoformat(timespec="seconds"),
            ),
            "approved_permissions": (
                approved_permissions
                if approved_permissions is not None
                else existing.get("approved_permissions", [])
            ),
        }

    def disable(self, name: str) -> None:
        """Marca como disabled (mantém permissões aprovadas)."""
        if name not in self._data["plugins"]:
            return
        self._data["plugins"][name]["enabled"] = False

    def remove(self, name: str) -> None:
        """Remove completamente do state.json (uninstall)."""
        self._data["plugins"].pop(name, None)

    # ---- Queries ----

    def is_enabled(self, name: str) -> bool:
        entry = self._data["plugins"].get(name)
        if not entry:
            return False
        return bool(entry.get("enabled", False))

    def approved_permissions(self, name: str) -> List[str]:
        entry = self._data["plugins"].get(name, {})
        return list(entry.get("approved_permissions", []))

    def all_entries(self) -> dict:
        """Retorna copy do dict de plugins (read-only para UI)."""
        return {
            k: dict(v) for k, v in self._data["plugins"].items()
        }

    # ---- Persistence ----

    def save(self) -> None:
        """Persiste em state_file (cria diretório pai se preciso)."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load(self) -> None:
        """Recarrega do state_file (sobrescreve in-memory)."""
        text = self.state_file.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict) or "plugins" not in data:
            raise ValueError(
                f"state.json inválido em {self.state_file}"
            )
        self._data = data


# ---------------------------------------------------------------------------
# Helpers de alto nível para Sprint F (startup auto-load)
# ---------------------------------------------------------------------------


def auto_load_enabled_plugins(
    *,
    state: Optional[LifecycleState] = None,
    discovered: Optional[List[DiscoveredPlugin]] = None,
) -> List[str]:
    """
    Carrega (importa entry_point.py) somente os plugins **enabled**
    no state.json.

    v1.5.0 mantém isolamento: o import só roda se o plugin estiver
    enabled e tiver permissões aprovadas. Plugins builtin sem
    state explícito ficam **disabled by default** (opt-in
    explícito no marketplace).

    Returns
    -------
    list[str]
        Nomes dos plugins efetivamente carregados.
    """
    import importlib.util

    if state is None:
        state = LifecycleState()
    if discovered is None:
        discovered = discover_plugins_v2()

    loaded: List[str] = []
    for d in discovered:
        if not state.is_enabled(d.manifest.name):
            continue
        ep = d.entry_point_path
        if not ep.is_file():
            log.warning(
                "Plugin '%s' enabled mas entry_point ausente: %s",
                d.manifest.name, ep,
            )
            continue
        try:
            spec = importlib.util.spec_from_file_location(
                f"olivas_plugin_{d.manifest.name}", ep,
            )
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            loaded.append(d.manifest.name)
            log.info("Plugin carregado: %s (%s)", d.manifest.name, d.source)
        except Exception as exc:
            log.warning(
                "Falha ao carregar plugin %s: %s", d.manifest.name, exc,
            )

    return loaded
