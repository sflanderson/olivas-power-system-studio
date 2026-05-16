"""
app.preprocessor.spec — schema declarativo de componente (.ocomp).

Este pacote contém o modelo canônico de um componente do Olivas ATP
Studio. A arquitetura foi desenhada para **escalabilidade com a API
Claude**:

1. Pydantic v2 é o modelo canônico (single source of truth).
2. YAML é a serialização humana (para arquivos .ocomp no disco).
3. JSON / dict é o transport layer (para a API Claude).
4. ``ComponentSpec.model_json_schema()`` exporta o schema do componente
   diretamente para o campo ``tools[].input_schema`` do Claude, permitindo
   que o LLM leia e gere specs validados nativamente.

Módulos expostos
----------------
- :mod:`app.preprocessor.spec.models`: modelos pydantic
  (``ComponentSpec``, ``PinSpec``, ``PropertySpec``, ...).
- :mod:`app.preprocessor.spec.loader`: I/O de arquivos ``.ocomp`` (YAML).
- :mod:`app.preprocessor.spec.registry`: ``ComponentSpecRegistry``,
  registry em memória que carrega um diretório de specs.

Referências
-----------
- Política clean-room: ``docs/LICENSING.md`` §3.
- Roadmap de paridade ATPDraw: v0.21.8 (este módulo) → v0.22.7.
"""

from __future__ import annotations

from pathlib import Path

from app.preprocessor.spec.models import (
    AtpEmissionKind,
    AtpEmissionSpec,
    BranchMapping,
    ComponentSpec,
    LLMHintsSpec,
    PinPhase,
    PinRole,
    PinSpec,
    PropertyGroup,
    PropertySpec,
    PropertyType,
    SymbolSpec,
)
from app.preprocessor.spec.loader import (
    dump_ocomp_file,
    dump_ocomp_string,
    load_ocomp_file,
    load_ocomp_string,
)
from app.preprocessor.spec.registry import ComponentSpecRegistry


# ---------------------------------------------------------------------------
# Registry singleton (lazy-loaded a partir de app/preprocessor/catalog_specs/)
# ---------------------------------------------------------------------------
# O registry default é o ponto de entrada para os módulos legados
# (``catalog.py``, ``node_coalescer.py``, ``editor.py``) consultarem os
# ``.ocomp`` disponíveis. Carrega uma única vez no primeiro uso — import do
# pacote NÃO toca o filesystem.
#
# Thread-safety: o singleton é construído lazy em um único thread (não há
# garantia de proteção em multi-thread). O Olivas ATP Studio é single-
# threaded no front-end (PySide6); backend de simulação roda em processo
# separado, então isso não é problema na prática.
# ---------------------------------------------------------------------------


_DEFAULT_CATALOG_DIR: Path = (
    Path(__file__).resolve().parent.parent / "catalog_specs"
)

_DEFAULT_REGISTRY: ComponentSpecRegistry | None = None


def get_default_registry() -> ComponentSpecRegistry:
    """
    Retorna o registry default, carregado de
    ``app/preprocessor/catalog_specs/``.

    A primeira chamada carrega todos os ``*.ocomp`` do diretório. Chamadas
    subsequentes retornam a instância cacheada (mesmo objeto).

    Uso típico (código legado consultando o registry):

    .. code-block:: python

        from app.preprocessor.spec import get_default_registry

        spec = get_default_registry().get("VCB3")
        if spec is not None:
            pins = spec.pins
        else:
            # Fallback para dict legado (componente ainda não migrado)
            ...

    Returns
    -------
    ComponentSpecRegistry
        Registry carregado com todos os .ocomp disponíveis.

    Notes
    -----
    Use :func:`reset_default_registry` em testes que precisam forçar
    reload (por exemplo, após escrever um ``.ocomp`` temporário).
    """
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        reg = ComponentSpecRegistry()
        if _DEFAULT_CATALOG_DIR.is_dir():
            reg.load_directory(_DEFAULT_CATALOG_DIR)
        _DEFAULT_REGISTRY = reg
    return _DEFAULT_REGISTRY


def reset_default_registry() -> None:
    """
    Descarta o registry cacheado. Próxima chamada de
    :func:`get_default_registry` recarrega do disco.

    Uso típico: testes que escrevem ``.ocomp`` temporários em
    ``catalog_specs/`` e precisam invalidar o cache.
    """
    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = None


__all__ = [
    # Models
    "ComponentSpec",
    "PinSpec",
    "PinPhase",
    "PinRole",
    "PropertySpec",
    "PropertyType",
    "PropertyGroup",
    "SymbolSpec",
    "AtpEmissionSpec",
    "AtpEmissionKind",
    "BranchMapping",
    "LLMHintsSpec",
    # I/O
    "load_ocomp_file",
    "load_ocomp_string",
    "dump_ocomp_file",
    "dump_ocomp_string",
    # Registry
    "ComponentSpecRegistry",
    "get_default_registry",
    "reset_default_registry",
]
