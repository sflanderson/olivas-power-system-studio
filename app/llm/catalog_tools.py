"""
app.llm.catalog_tools — expõe o catálogo de ``.ocomp`` como
``tools[]`` do Anthropic API (Claude tool_use).

Por que este módulo existe
--------------------------

O ``agent.py`` expõe tools para **manipular um AtpProject** (abrir
arquivo, listar MODELs, editar USE, etc.). Este módulo expõe tools
para **adicionar componentes ao esquemático** a partir do catálogo
de 40 ``.ocomp``. Complementar ao agent.py, não conflitante.

O Claude, ao ver estas tools, pode:

* "Adicione um resistor de 100 Ω entre N1 e GND" → ``add_R(name="R1",
  x=100, y=100, R=100)``
* "Crie uma fonte AC de 13.8 kV, 60 Hz" → ``add_Vac(...)``
* "Inclua um VCB com reignição estatística (I_chop=8A)" →
  ``add_VCB(..., I_chop=8.0)``

Cada tool tem:

* ``name``: ``add_{code}`` (ex: ``add_R``, ``add_VCB3``).
* ``description``: combina ``spec.description`` + principais
  ``llm_hints.typical_applications``.
* ``input_schema``: JSON Schema derivado automaticamente de
  ``spec.properties`` + coordenadas x/y/rotation/mirror/name.

Compatível com ``anthropic`` SDK v0.x — o dict retornado vai direto
para ``messages.create(tools=[...])``.
"""

from __future__ import annotations

from typing import Any, Optional

from app.preprocessor.spec import (
    ComponentSpec,
    PropertySpec,
    PropertyType,
    get_default_registry,
)


# ---------------------------------------------------------------------------
# Mapeamento PropertyType → JSON Schema type
# ---------------------------------------------------------------------------


_TYPE_TO_JSON_SCHEMA: dict[PropertyType, str] = {
    PropertyType.FLOAT:      "number",
    PropertyType.INT:        "integer",
    PropertyType.STRING:     "string",
    PropertyType.BOOL:       "boolean",
    PropertyType.FILE:       "string",
    PropertyType.ENUM:       "string",
    PropertyType.TABLE:      "string",
    PropertyType.EXPRESSION: "string",
}


def _property_to_schema_entry(prop: PropertySpec) -> dict[str, Any]:
    """Converte uma ``PropertySpec`` para uma entry de ``properties`` em JSON Schema."""
    entry: dict[str, Any] = {
        "type": _TYPE_TO_JSON_SCHEMA.get(prop.type, "string"),
    }
    # Descrição inclui label + unidade + descrição livre + exemplo
    desc_parts: list[str] = []
    if prop.label:
        label = prop.label
        if prop.unit:
            label += f" [{prop.unit}]"
        desc_parts.append(label)
    if prop.description:
        desc_parts.append(prop.description)
    if prop.example is not None:
        desc_parts.append(f"Example: {prop.example}")
    if desc_parts:
        entry["description"] = " — ".join(desc_parts)
    # Constraints numéricas
    if prop.type in (PropertyType.FLOAT, PropertyType.INT):
        if prop.min is not None:
            entry["minimum"] = prop.min
        if prop.max is not None:
            entry["maximum"] = prop.max
    # Enum
    if prop.type == PropertyType.ENUM and prop.choices:
        entry["enum"] = list(prop.choices)
    # Default
    if prop.default is not None:
        entry["default"] = prop.default
    return entry


def spec_to_tool(spec: ComponentSpec) -> dict[str, Any]:
    """
    Converte uma ``ComponentSpec`` para uma tool do Anthropic API.

    Parameters
    ----------
    spec:
        Schema declarativo do componente.

    Returns
    -------
    dict
        Formato aceito por ``anthropic.messages.create(tools=[...])``.
        Tem ``name``, ``description``, ``input_schema``.

    Shape típica (resumida):
    ::

        {
            "name": "add_VCB",
            "description": "Disjuntor a vácuo (VCB) 1φ — ...",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "..."},
                    "x": {"type": "integer", "default": 100},
                    "y": {"type": "integer", "default": 100},
                    "rotation": {"type": "integer", "enum": [0,1,2,3]},
                    "mirror": {"type": "boolean", "default": false},
                    "T_open": {"type": "number", "minimum": 0.0, ...},
                    ...
                },
                "required": ["name"]
            }
        }
    """
    # Monta descrição: resumo do componente + 1-2 applications típicas
    desc_parts: list[str] = []
    desc_parts.append(f"{spec.label_pt} ({spec.category}).")
    if spec.description:
        # Primeira frase da descrição, para manter compacto
        first_sentence = spec.description.strip().split(". ")[0]
        desc_parts.append(first_sentence)
    if spec.llm_hints.typical_applications:
        apps = ", ".join(spec.llm_hints.typical_applications[:2])
        desc_parts.append(f"Aplicações típicas: {apps}.")
    description = " ".join(desc_parts)

    # Propriedades gerais do componente (identidade + geometria)
    properties: dict[str, Any] = {
        "name": {
            "type": "string",
            "description": "Nome único do componente (ex: R1, DJ1, V_fonte).",
        },
        "x": {
            "type": "integer",
            "description": "Posição X no esquemático (grid 10px).",
            "default": 100,
        },
        "y": {
            "type": "integer",
            "description": "Posição Y no esquemático (grid 10px).",
            "default": 100,
        },
        "rotation": {
            "type": "integer",
            "description": "Rotação em múltiplos de 90° CCW (0, 1, 2, 3).",
            "enum": [0, 1, 2, 3],
            "default": 0,
        },
        "mirror": {
            "type": "boolean",
            "description": "Se True, espelha horizontalmente.",
            "default": False,
        },
    }

    # Propriedades específicas do componente (de spec.properties)
    for prop in spec.properties:
        properties[prop.name] = _property_to_schema_entry(prop)

    return {
        "name": f"add_{spec.code}",
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": ["name"],
        },
    }


def catalog_to_tools(
    registry=None,
    *,
    categories: Optional[list[str]] = None,
    exclude_unsupported: bool = True,
) -> list[dict[str, Any]]:
    """
    Converte todo o registry (ou subset filtrado) para lista de tools.

    Parameters
    ----------
    registry:
        Registry a consultar. Default: ``get_default_registry()``.
    categories:
        Se fornecido, filtra apenas componentes dessas categorias
        (ex: ``["passive", "source"]``).
    exclude_unsupported:
        Se True (default), exclui componentes com ``atp_supported=False``
        — diretivas de simulação (.TR/.DC/.AC/etc.) não entram no
        tool set visível ao Claude (elas não geram ATP).

    Returns
    -------
    list[dict]
        Formato aceito por ``messages.create(tools=[...])``.
    """
    reg = registry if registry is not None else get_default_registry()
    tools: list[dict[str, Any]] = []
    for spec in reg.all_specs():
        if exclude_unsupported and not spec.atp_supported:
            continue
        if categories and spec.category not in categories:
            continue
        tools.append(spec_to_tool(spec))
    return tools


# ---------------------------------------------------------------------------
# Dispatch — executa um tool_use retornado pelo Claude
# ---------------------------------------------------------------------------


def dispatch_add_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    editor,
) -> dict[str, Any]:
    """
    Executa um ``add_<CODE>`` tool_use do Claude, chamando o editor.

    Parameters
    ----------
    tool_name:
        Nome da tool (ex: ``"add_R"``).
    tool_input:
        Dict com os argumentos resolvidos pelo Claude.
    editor:
        Instância de :class:`app.gui.schematic_pp.PpEditor` (ou
        qualquer objeto que expõe ``add_component_by_type`` e
        ``scene.find_component_item``).

    Returns
    -------
    dict
        Resultado estruturado. ``{"success": True, "name": "R1",
        "code": "R", "position": [100, 100]}`` em caso de sucesso;
        ``{"success": False, "error": "..."}`` em caso de falha.
    """
    if not tool_name.startswith("add_"):
        return {
            "success": False,
            "error": f"Tool {tool_name!r} não é um add_* reconhecido.",
        }
    code = tool_name[len("add_"):]

    spec = get_default_registry().get(code)
    if spec is None:
        return {
            "success": False,
            "error": f"Código {code!r} não existe no registry.",
        }

    try:
        from PySide6.QtCore import QPointF
        x = int(tool_input.get("x", 100))
        y = int(tool_input.get("y", 100))
        item = editor.add_component_by_type(
            code, scene_pos=QPointF(x, y),
        )
    except Exception as e:  # pragma: no cover - defensive
        return {"success": False, "error": f"Falha ao adicionar {code}: {e}"}

    comp = item.component
    # Aplica nome, rotation, mirror
    name = (tool_input.get("name") or "").strip()
    if name:
        comp.name = name
    rotation = int(tool_input.get("rotation", 0)) % 4
    if rotation != comp.rotation:
        comp.rotation = rotation
    mirror = 1 if tool_input.get("mirror", False) else 0
    if mirror != comp.mirror:
        comp.mirror = mirror

    # Aplica properties
    applied_props: dict[str, Any] = {}
    for i, prop_spec in enumerate(spec.properties):
        if prop_spec.name in tool_input:
            raw = tool_input[prop_spec.name]
            comp.properties[i].value = str(raw)
            applied_props[prop_spec.name] = raw

    item.sync_from_model()
    item.update()

    return {
        "success": True,
        "name": comp.name,
        "code": code,
        "position": [comp.x, comp.y],
        "properties_applied": applied_props,
    }
