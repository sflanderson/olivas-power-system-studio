"""
app.preprocessor.spec.loader — I/O YAML para arquivos ``.ocomp``.

Este módulo lida com a serialização entre o modelo pydantic canônico
(:class:`ComponentSpec`) e representações YAML/string.

Por que YAML?
-------------
YAML é o formato escolhido para ``.ocomp`` porque:

* É amigável para autores humanos (comentários, multiline strings).
* Mapeia 1-para-1 a estruturas dict/list, compatível com pydantic.
* ``yaml.safe_load`` não executa código arbitrário (diferente do ``yaml.load``).
* Suporta Unicode sem BOM (useful para labels em português).

Formato canônico
----------------
Os arquivos ``.ocomp`` devem ser serializados com:

* ``sort_keys=False`` para preservar a ordem declarada (pins antes de
  properties, etc.).
* ``allow_unicode=True`` para preservar acentos.
* ``default_flow_style=False`` para estilo blocado (legível).

Consulte ``docs/OCOMP_AUTHORING.md`` (v0.21.9) para convenções de estilo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.preprocessor.spec.models import ComponentSpec


def load_ocomp_string(yaml_text: str) -> ComponentSpec:
    """
    Carrega um ``ComponentSpec`` a partir de uma string YAML.

    Parameters
    ----------
    yaml_text:
        String contendo o YAML do spec.

    Returns
    -------
    ComponentSpec
        Spec validado.

    Raises
    ------
    yaml.YAMLError
        Se o YAML for sintaticamente inválido.
    pydantic.ValidationError
        Se o YAML for válido mas o conteúdo não satisfaz o schema.
    """
    data = yaml.safe_load(yaml_text)
    if not isinstance(data, dict):
        raise ValueError(
            f"YAML não é um dict raiz (é {type(data).__name__}). "
            "Um .ocomp deve começar com chaves no nível raiz."
        )
    return ComponentSpec.model_validate(data)


def load_ocomp_file(path: str | Path) -> ComponentSpec:
    """
    Carrega um ``ComponentSpec`` a partir de um arquivo ``.ocomp``.

    Parameters
    ----------
    path:
        Caminho para o arquivo ``.ocomp``.

    Returns
    -------
    ComponentSpec
        Spec validado.

    Raises
    ------
    FileNotFoundError
        Se o arquivo não existir.
    yaml.YAMLError, pydantic.ValidationError
        Como em :func:`load_ocomp_string`.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"arquivo .ocomp não encontrado: {p}")
    text = p.read_text(encoding="utf-8")
    try:
        return load_ocomp_string(text)
    except Exception as exc:
        # PEP 678: adiciona contexto do arquivo sem perder o tipo da
        # exceção original (ValidationError do pydantic tem construtor
        # especial que impede re-levantar via ``type(exc)(msg)``).
        exc.add_note(f"em {p}")
        raise


def dump_ocomp_string(spec: ComponentSpec) -> str:
    """
    Serializa um ``ComponentSpec`` para string YAML (formato canônico).
    """
    data: dict[str, Any] = spec.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        indent=2,
    )


def dump_ocomp_file(spec: ComponentSpec, path: str | Path) -> None:
    """
    Escreve um ``ComponentSpec`` para um arquivo ``.ocomp``.

    O arquivo é escrito em UTF-8 sem BOM, com terminadores Unix (``\\n``).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(dump_ocomp_string(spec), encoding="utf-8", newline="\n")
