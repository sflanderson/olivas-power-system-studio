"""
app.plugins.manifest — Pydantic schema do manifest de plugins
(v1.5.0 Sprint A).

Cada plugin é uma pasta com:

* ``manifest.yaml`` — metadados, versão, permissões (este módulo)
* ``plugin.py`` — código de entrada (referenciado por ``entry_point``)

O manifest é a camada de **declaração de intenção** do plugin:

* Quais permissões precisa (filesystem, network, etc.)
* Em qual categoria se encaixa (study, exporter, validator, ...)
* Qual range de versões do Olivas suporta

Validação é via Pydantic v2 (já dep do projeto):

* ``name``: snake_case, [a-z][a-z0-9_]+, 2-64 chars
* ``version`` e ``min/max_olivas_version``: semver simples
* ``permissions``: enum whitelist (sem "free-form")
* ``category``: enum (7 categorias suportadas em v1.5.0)

Compatibilidade Olivas: ``is_compatible_with_olivas(version)`` testa
se a versão do Olivas atual está em ``[min, max]``.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums (whitelist de valores conhecidos — anti-typo + segurança)
# ---------------------------------------------------------------------------


class PluginPermission(str, Enum):
    """
    Whitelist de permissões que um plugin pode declarar.

    Plugins só podem usar APIs cobertas pela permissão. Se um
    plugin tenta importar `requests` sem `network` na lista, o
    loader recusa carregá-lo (Sprint C).

    A whitelist é fechada — `permissions: [exotic_permission]`
    no YAML resulta em ValidationError.
    """

    # Hooks de extensão (mapeiam aos decorators de registry.py)
    STUDIES = "studies"
    EQUIPMENT = "equipment"
    RENDERERS = "renderers"
    EXPORTERS = "exporters"
    POSTPROCESSORS = "postprocessors"
    VALIDATORS = "validators"
    CATALOG_SPECS = "catalog_specs"

    # Capabilities I/O
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    NETWORK = "network"
    SUBPROCESS = "subprocess"


class PluginCategory(str, Enum):
    """
    Categoria primária do plugin (1 categoria por plugin).

    Usada pela UI Marketplace para agrupar plugins por tipo.
    Plugins multifacetados (ex: study + exporter) escolhem a
    categoria principal e declaram as outras via `permissions`.
    """

    STUDY = "study"
    EQUIPMENT = "equipment"
    RENDERER = "renderer"
    EXPORTER = "exporter"
    POSTPROCESSOR = "postprocessor"
    VALIDATOR = "validator"
    CATALOG_SPEC = "catalog_spec"


# ---------------------------------------------------------------------------
# Helpers de versão
# ---------------------------------------------------------------------------


def _parse_semver(s: str) -> tuple[int, ...]:
    """
    Aceita "1.0.0", "1.0", "1". Não suporta sufixos ("1.0.0-rc1").
    Para v1.5.0 mantemos simples; v2+ pode usar packaging.version.

    Raises
    ------
    ValueError
        Se houver chars não-numéricos.
    """
    parts = s.split(".")
    return tuple(int(p) for p in parts)


def _semver_le(a: str, b: str) -> bool:
    """a <= b lexicograficamente em tuplas inteiras."""
    return _parse_semver(a) <= _parse_semver(b)


# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------


class PluginManifest(BaseModel):
    """
    Schema do manifest.yaml de um plugin Olivas v1.5.0.

    Campos obrigatórios: name, display_name, version, author,
    description, min_olivas_version, category.

    Campos opcionais: license, max_olivas_version, entry_point
    (default 'plugin.py'), permissions, content_sha256, tags.
    """

    schema_version: str = "1.0"

    # Identidade
    name: str = Field(
        min_length=2, max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Identificador snake_case único do plugin",
    )
    display_name: str = Field(min_length=1, max_length=128)
    version: str
    author: str = Field(min_length=1)
    license: str = "Unknown"
    description: str = Field(min_length=1)

    # Compatibilidade Olivas
    min_olivas_version: str
    max_olivas_version: Optional[str] = None

    # Categoria
    category: PluginCategory

    # Entry point (relativo ao diretório do plugin)
    entry_point: str = "plugin.py"

    # Segurança
    permissions: List[PluginPermission] = Field(default_factory=list)
    content_sha256: Optional[str] = None

    # Marketplace UI
    tags: List[str] = Field(default_factory=list)

    @field_validator("version", "min_olivas_version")
    @classmethod
    def _validate_semver(cls, v: str) -> str:
        try:
            _parse_semver(v)
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"Versão '{v}' não é semver válido (ex: '1.0.0')"
            ) from e
        return v

    @field_validator("max_olivas_version")
    @classmethod
    def _validate_max_semver(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            _parse_semver(v)
        except ValueError as e:
            raise ValueError(
                f"max_olivas_version '{v}' inválido"
            ) from e
        return v

    # ---- API pública ----

    def is_compatible_with_olivas(self, olivas_version: str) -> bool:
        """
        True se ``olivas_version`` está em ``[min, max]``.

        Se ``max_olivas_version`` é None, considera unbounded
        (qualquer versão >= min é compatível).
        """
        try:
            if not _semver_le(self.min_olivas_version, olivas_version):
                return False
            if self.max_olivas_version is not None:
                if not _semver_le(olivas_version, self.max_olivas_version):
                    return False
            return True
        except ValueError:
            return False


# ---------------------------------------------------------------------------
# Loaders YAML
# ---------------------------------------------------------------------------


def load_manifest_from_yaml(yaml_text: str) -> PluginManifest:
    """
    Parse string YAML → :class:`PluginManifest`.

    Lança :class:`pydantic.ValidationError` se inválido.
    """
    data = yaml.safe_load(yaml_text)
    if not isinstance(data, dict):
        raise ValueError(
            "Manifest YAML deve ser um mapping (dict), "
            f"got {type(data).__name__}"
        )
    return PluginManifest(**data)


def load_manifest_from_path(
    path: Union[str, Path],
) -> PluginManifest:
    """
    Lê arquivo manifest.yaml e devolve :class:`PluginManifest`.

    Raises
    ------
    FileNotFoundError
        Se ``path`` não existe.
    pydantic.ValidationError
        Se o conteúdo é inválido.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    return load_manifest_from_yaml(text)
