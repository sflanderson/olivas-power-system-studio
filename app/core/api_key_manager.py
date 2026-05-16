"""
app.core.api_key_manager — gerenciamento centralizado da
ANTHROPIC_API_KEY (v0.81).

Antes: cada componente fazia ``os.environ.get("ANTHROPIC_API_KEY")``
isoladamente. Sem persistência via GUI — usuário precisava
configurar variável de ambiente externamente.

Agora: hierarquia de fontes (mais alta prioridade primeiro):

1. ``QSettings("OlivasATPStudio")["anthropic_api_key"]``
   (configurado via dialog GUI).
2. Variável de ambiente ``ANTHROPIC_API_KEY``.
3. Arquivo ``.env`` na raiz do projeto.
4. ``~/.olivas_atp_studio/api_keys.json``.

Use a função ``get_anthropic_api_key()`` em vez de
``os.environ.get`` direto.

Para configurar via GUI: ``set_anthropic_api_key(key)``.

Segurança: a key NUNCA é logada nem incluída em crash dumps.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


_CACHED_KEY: Optional[str] = None
_CACHE_INITIALIZED = False


def _read_dotenv() -> Optional[str]:
    """Lê ANTHROPIC_API_KEY de .env na raiz do projeto."""
    # Procura .env subindo do app/core até encontrar repo root
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        env_file = parent / ".env"
        if env_file.is_file():
            try:
                for line in env_file.read_text(
                    encoding="utf-8",
                ).splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    if k.strip() == "ANTHROPIC_API_KEY":
                        v = v.strip().strip('"').strip("'")
                        if v:
                            return v
            except OSError:
                pass
            break
    return None


def _read_user_config() -> Optional[str]:
    """Lê de ~/.olivas_atp_studio/api_keys.json."""
    config = Path.home() / ".olivas_atp_studio" / "api_keys.json"
    if not config.is_file():
        return None
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
        return data.get("anthropic_api_key")
    except (OSError, json.JSONDecodeError):
        return None


def _read_qsettings() -> Optional[str]:
    """Lê de QSettings se PySide6 disponível."""
    try:
        from PySide6.QtCore import QSettings
        settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
        v = settings.value("anthropic_api_key", None)
        if v:
            return str(v)
    except ImportError:
        pass
    return None


def get_anthropic_api_key(*, force_refresh: bool = False) -> Optional[str]:
    """
    Retorna a API key conforme hierarquia:

    1. QSettings (configurado via GUI) — prioridade máxima.
    2. Env var ANTHROPIC_API_KEY.
    3. .env file na raiz do projeto.
    4. ~/.olivas_atp_studio/api_keys.json.
    5. None se nenhuma fonte tem.

    Cache em ``_CACHED_KEY`` para evitar IO repetido.

    Parameters
    ----------
    force_refresh:
        Se True, ignora cache e re-lê todas as fontes.

    Returns
    -------
    Optional[str]
        API key ou None.
    """
    global _CACHED_KEY, _CACHE_INITIALIZED
    if _CACHE_INITIALIZED and not force_refresh:
        return _CACHED_KEY

    # Tenta cada fonte em ordem
    key = (
        _read_qsettings()
        or os.environ.get("ANTHROPIC_API_KEY")
        or _read_dotenv()
        or _read_user_config()
    )

    _CACHED_KEY = key
    _CACHE_INITIALIZED = True
    return key


def set_anthropic_api_key(key: str) -> None:
    """
    Persiste API key em QSettings (preferred) ou JSON file
    (fallback).

    Atualiza cache + sincroniza ``os.environ`` para que
    componentes legacy (``os.environ.get(...)``) também
    enxerguem.
    """
    global _CACHED_KEY, _CACHE_INITIALIZED

    if not key:
        clear_anthropic_api_key()
        return

    # 1) QSettings se disponível
    saved_in_qsettings = False
    try:
        from PySide6.QtCore import QSettings
        settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
        settings.setValue("anthropic_api_key", key)
        settings.sync()
        saved_in_qsettings = True
    except ImportError:
        pass

    # 2) Fallback: ~/.olivas_atp_studio/api_keys.json
    if not saved_in_qsettings:
        config_dir = Path.home() / ".olivas_atp_studio"
        config_dir.mkdir(parents=True, exist_ok=True)
        config = config_dir / "api_keys.json"
        try:
            existing = {}
            if config.is_file():
                existing = json.loads(config.read_text(encoding="utf-8"))
            existing["anthropic_api_key"] = key
            config.write_text(
                json.dumps(existing, indent=2),
                encoding="utf-8",
            )
            # Restringe permissão (Linux/Mac)
            try:
                config.chmod(0o600)
            except (OSError, NotImplementedError):
                pass
        except OSError:
            pass

    # 3) Sincroniza env var (componentes legacy)
    os.environ["ANTHROPIC_API_KEY"] = key
    _CACHED_KEY = key
    _CACHE_INITIALIZED = True


def clear_anthropic_api_key() -> None:
    """Remove API key de todas as fontes persistentes."""
    global _CACHED_KEY, _CACHE_INITIALIZED

    try:
        from PySide6.QtCore import QSettings
        settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
        settings.remove("anthropic_api_key")
        settings.sync()
    except ImportError:
        pass

    config = Path.home() / ".olivas_atp_studio" / "api_keys.json"
    if config.is_file():
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
            data.pop("anthropic_api_key", None)
            config.write_text(
                json.dumps(data, indent=2), encoding="utf-8",
            )
        except (OSError, json.JSONDecodeError):
            pass

    os.environ.pop("ANTHROPIC_API_KEY", None)
    _CACHED_KEY = None
    _CACHE_INITIALIZED = True


def is_configured() -> bool:
    """True se alguma fonte tem API key válida."""
    key = get_anthropic_api_key()
    return bool(key) and key.startswith("sk-")


def masked_key() -> str:
    """Retorna chave mascarada para exibição (sk-ant-...****)."""
    key = get_anthropic_api_key()
    if not key:
        return "(não configurada)"
    if len(key) <= 12:
        return "*" * len(key)
    return key[:10] + "*" * (len(key) - 14) + key[-4:]
