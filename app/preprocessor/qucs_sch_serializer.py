"""
app.preprocessor.qucs_sch_serializer — escritor do formato `.sch`.

Pareia com `qucs_sch_parser.parse_sch`. O contrato fundamental é:
para todo arquivo `.sch` válido produzido pelo Qucs,

    serialize_sch(parse_sch(text)) == text

(tolerando uma normalização mínima descrita abaixo).

Normalizações aceitas no round-trip
------------------------------------
* CRLF → LF: o serializer sempre emite LF. Testes que comparam
  byte-a-byte devem normalizar EOL antes.
* Linhas em branco entre blocos: o Qucs varia (às vezes uma linha
  em branco entre `<Properties>` e `<Components>`, às vezes não).
  Reproduzimos o estilo majoritário do Qucs 0.0.19: sem linhas
  em branco extras dentro do header de blocos.
* Trailing newline: o serializer emite EOL após o último bloco.
"""

from __future__ import annotations

from pathlib import Path

from .models import (
    PpComponent,
    PpDiagram,
    PpPainting,
    PpProject,
    PpProperty,
    PpWire,
)


# ---------------------------------------------------------------------------
# Quoting
# ---------------------------------------------------------------------------


def _quote(value: str) -> str:
    """
    Envolve uma string em aspas, escapando ``\\``, ``"``, ``\n``,
    ``\t`` no estilo Qucs.

    A ordem de substituição importa: ``\\`` PRIMEIRO, senão ele
    re-escaparia escapes de outras substituições.
    """
    s = (
        value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f'"{s}"'


# ---------------------------------------------------------------------------
# Serializadores por tipo
# ---------------------------------------------------------------------------


def _serialize_property(prop: PpProperty) -> str:
    return f"{_quote(prop.value)} {1 if prop.visible else 0}"


def _serialize_component(c: PpComponent) -> str:
    parts = [
        c.type,
        c.name,
        "1" if c.visible else "0",
        str(c.x),
        str(c.y),
        str(c.label_dx),
        str(c.label_dy),
        str(c.mirror),
        str(c.rotation),
    ]
    for prop in c.properties:
        parts.append(_serialize_property(prop))
    if c.raw_extra_fields:
        parts.extend(c.raw_extra_fields)
    return "  <" + " ".join(parts) + ">"


def _serialize_wire(w: PpWire) -> str:
    parts = [
        str(w.x1),
        str(w.y1),
        str(w.x2),
        str(w.y2),
        _quote(w.label),
        str(w.label_x),
        str(w.label_y),
        str(w.label_visible),
    ]
    if w.has_extra:
        parts.append('""')
    return "  <" + " ".join(parts) + ">"


def _serialize_diagram(d: PpDiagram) -> list[str]:
    out = [f"  <{d.raw_header}>"]
    for curve in d.raw_curves:
        # Curvas no Qucs original usam tabulação para indentar.
        # Reproduzimos: tab + < ... >.
        out.append(f"\t<{curve}>")
    return out


def _serialize_painting(p: PpPainting) -> str:
    if p.raw:
        return f"  <{p.type} {p.raw}>"
    return f"  <{p.type}>"


# ---------------------------------------------------------------------------
# Serializador principal
# ---------------------------------------------------------------------------


def serialize_sch(project: PpProject) -> str:
    """
    Reconstrói o texto `.sch` a partir de `PpProject`.

    A saída usa LF (``\n``) como terminador de linha. Para gravar
    no Windows preservando CRLF do original, use
    `serialize_sch_file(..., newline=...)` ou trate fora.
    """
    lines: list[str] = []

    # Pre-header (raro)
    lines.extend(project.raw_pre_header)

    # Header
    lines.append(f"<Qucs Schematic {project.version}>")

    # Properties
    lines.append("<Properties>")
    for key, value in project.properties.items():
        # Chaves sintéticas "_raw_N" (vindas de linhas sem '=')
        # voltam como antes, sem '='.
        if key.startswith("_raw_"):
            lines.append(f"  <{value}>")
        else:
            lines.append(f"  <{key}={value}>")
    lines.append("</Properties>")

    # Symbol (só emite o bloco se não-vazio OU se o original tinha
    # — não temos como saber sem flag adicional. Política: emite
    # sempre que `symbol` for set explicitamente, mesmo vazio. Para
    # não-emitir, o usuário pode passar `symbol=None`-equivalente
    # via remover a key. Aqui consideramos lista vazia = "emite
    # bloco vazio" para preservar arquivos 0.0.5+.)
    #
    # Heurística pragmática: emitimos o bloco <Symbol> sempre,
    # exceto quando version < 0.0.5 (antes do Symbol existir).
    if _version_supports_symbol(project.version):
        lines.append("<Symbol>")
        for raw in project.symbol:
            lines.append(f"  <{raw}>")
        lines.append("</Symbol>")

    # Components
    lines.append("<Components>")
    for c in project.components:
        lines.append(_serialize_component(c))
    lines.append("</Components>")

    # Wires
    lines.append("<Wires>")
    for w in project.wires:
        lines.append(_serialize_wire(w))
    lines.append("</Wires>")

    # Diagrams
    lines.append("<Diagrams>")
    for d in project.diagrams:
        lines.extend(_serialize_diagram(d))
    lines.append("</Diagrams>")

    # Paintings
    lines.append("<Paintings>")
    for p in project.paintings:
        lines.append(_serialize_painting(p))
    lines.append("</Paintings>")

    return "\n".join(lines) + "\n"


def _version_supports_symbol(version: str) -> bool:
    """
    Bloco <Symbol> aparece a partir do formato 0.0.5.
    """
    try:
        parts = [int(x) for x in version.split(".")]
        # 0.0.5 → [0,0,5]
        if len(parts) >= 3:
            return parts[2] >= 5
    except ValueError:
        pass
    # Quando em dúvida, emite (mais inclusivo)
    return True


def serialize_sch_file(
    project: PpProject,
    path: str | Path,
    encoding: str = "utf-8",
    newline: str = "\n",
) -> None:
    """
    Conveniência: serializa e grava em disco.

    O parâmetro `newline` controla o terminador de linha gravado
    (use ``"\\r\\n"`` para gerar arquivos Windows-style).
    """
    text = serialize_sch(project)
    if newline != "\n":
        text = text.replace("\n", newline)
    Path(path).write_text(text, encoding=encoding, newline="")
