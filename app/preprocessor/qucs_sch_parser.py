"""
app.preprocessor.qucs_sch_parser — leitor do formato `.sch` do Qucs.

O formato é um texto tagueado, ASCII/UTF-8, com blocos delimitados
por linhas ``<Bloco>`` ... ``</Bloco>`` e itens em uma linha cada,
delimitados por ``<...>``. Esta implementação foi validada contra
todas as versões do formato presentes nos exemplos do Qucs 0.0.19
(0.0.3, 0.0.4, 0.0.5, 0.0.7, 0.0.9 a 0.0.19).

Observação de licença
---------------------
Reconhecer e produzir um formato de arquivo público é uma operação
sobre **dados**, não derivação de código GPL. Esta implementação
é nossa, escrita do zero a partir da inspeção de arquivos `.sch`
de exemplo (que são distribuídos pelo Qucs como dados).
"""

from __future__ import annotations

import re
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
# Tokenizer
# ---------------------------------------------------------------------------


# Captura ou um token entre aspas (com escapes \" \\ \n) ou um
# token não-espaço sem aspas. Aspas internas SEM escape (raras,
# vistas em alguns Paintings) são tratadas como heurística no
# parser de paintings — aqui assumimos escape correto, que é o
# que o Qucs gera ao salvar.
_TOKEN_RE = re.compile(r'"((?:[^"\\]|\\.)*)"|(\S+)')


def _unescape(s: str) -> str:
    """Decodifica escapes Qucs em uma string entre aspas."""
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            nxt = s[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            elif nxt == '"':
                out.append('"')
            elif nxt == "\\":
                out.append("\\")
            else:
                # escape desconhecido — mantém literal
                out.append(c)
                out.append(nxt)
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _tokenize(line: str) -> list[str]:
    """Divide uma linha em tokens, respeitando aspas e escapes."""
    tokens: list[str] = []
    for m in _TOKEN_RE.finditer(line):
        if m.group(1) is not None:
            tokens.append(_unescape(m.group(1)))
        else:
            tokens.append(m.group(2))
    return tokens


# ---------------------------------------------------------------------------
# Helpers de leitura linha-a-linha
# ---------------------------------------------------------------------------


_HEADER_RE = re.compile(r"^<Qucs Schematic\s+([\d.]+)>\s*$")


def _strip_brackets(line: str) -> str | None:
    """
    Remove ``<`` ... ``>`` de uma linha de item. Retorna None se a
    linha não tem o formato esperado.
    """
    s = line.strip()
    if s.startswith("<") and s.endswith(">"):
        return s[1:-1]
    return None


# ---------------------------------------------------------------------------
# Parsers de bloco
# ---------------------------------------------------------------------------


def _parse_properties_block(lines: list[str]) -> dict[str, str]:
    """
    Bloco ``<Properties>`` contém pares ``Key=Value`` por linha::

        <View=0,0,800,800,1,0,0>
        <Grid=10,10,1>
        <DataSet=bridge.dat>
    """
    props: dict[str, str] = {}
    for raw in lines:
        inner = _strip_brackets(raw)
        if inner is None:
            continue
        if "=" in inner:
            key, _, value = inner.partition("=")
            props[key] = value
        else:
            # linha sem '=' (raro): preserva sob chave sintética
            props[f"_raw_{len(props)}"] = inner
    return props


def _parse_symbol_block(lines: list[str]) -> list[str]:
    """Mantém as linhas internas brutas (sem ``<>``)."""
    out: list[str] = []
    for raw in lines:
        inner = _strip_brackets(raw)
        if inner is not None:
            out.append(inner)
    return out


def _parse_component_line(inner: str) -> PpComponent:
    """
    Faz parse de uma linha de componente já sem ``<>``.

    Layout::

        TYPE NAME visible x y label_dx label_dy mirror rotation
                  "p1" v1 "p2" v2 ...

    Os 9 primeiros tokens são posicionais; o resto vem em pares
    (string, int) representando propriedades. Caso o número de
    tokens após os 9 fixos seja ímpar, o último vai para
    ``raw_extra_fields`` para preservar round-trip.
    """
    toks = _tokenize(inner)
    if len(toks) < 9:
        raise ValueError(f"Linha de componente curta demais: {inner!r}")

    type_ = toks[0]
    name = toks[1]
    visible = toks[2] == "1"
    x = int(toks[3])
    y = int(toks[4])
    label_dx = int(toks[5])
    label_dy = int(toks[6])
    mirror = int(toks[7])
    rotation = int(toks[8])

    rest = toks[9:]
    properties: list[PpProperty] = []
    extra: list[str] = []

    i = 0
    while i + 1 < len(rest):
        value = rest[i]
        flag = rest[i + 1]
        # Propriedade legítima: o flag deve ser "0" ou "1".
        if flag in ("0", "1"):
            properties.append(PpProperty(value=value, visible=flag == "1"))
            i += 2
        else:
            # Não é par válido — empurra para extras e avança 1.
            extra.append(value)
            i += 1
    # Se sobrou um token solto, vai para extras.
    if i < len(rest):
        extra.append(rest[i])

    return PpComponent(
        type=type_,
        name=name,
        visible=visible,
        x=x,
        y=y,
        label_dx=label_dx,
        label_dy=label_dy,
        mirror=mirror,
        rotation=rotation,
        properties=properties,
        raw_extra_fields=extra,
    )


def _parse_wire_line(inner: str) -> PpWire:
    """
    Layout::

        x1 y1 x2 y2 "label" label_x label_y label_visible [extra]

    Versões 0.0.15+ têm um 9º campo (string vazia) — preservamos
    via ``has_extra``.
    """
    toks = _tokenize(inner)
    if len(toks) < 8:
        raise ValueError(f"Linha de wire curta demais: {inner!r}")

    x1, y1, x2, y2 = (int(t) for t in toks[:4])
    label = toks[4]
    label_x = int(toks[5])
    label_y = int(toks[6])
    label_visible = int(toks[7])
    has_extra = len(toks) > 8

    return PpWire(
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        label=label,
        label_x=label_x,
        label_y=label_y,
        label_visible=label_visible,
        has_extra=has_extra,
    )


def _parse_diagrams_block(lines: list[str]) -> list[PpDiagram]:
    """
    Diagramas têm forma::

        <Tipo header_fields...>
                <"curva1" ...>
                <"curva2" ...>
                ...
        </Tipo>     (não — na verdade não há fechamento, o próximo <Tipo> abre outro
                    e curvas são linhas indentadas que começam com <")

    Estratégia: a linha que começa com ``<`` seguido de identificador
    abre um diagrama; linhas seguintes começando com ``<"`` são
    curvas daquele diagrama.
    """
    diagrams: list[PpDiagram] = []
    current: PpDiagram | None = None
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        inner = _strip_brackets(s)
        if inner is None:
            continue
        if inner.startswith('"'):
            # curva do diagrama corrente
            if current is not None:
                current.raw_curves.append(inner)
            # se não há corrente, ignora (não deveria acontecer em arquivos válidos)
        else:
            # novo diagrama
            type_ = inner.split(None, 1)[0]
            current = PpDiagram(type=type_, raw_header=inner, raw_curves=[])
            diagrams.append(current)
    return diagrams


def _parse_paintings_block(lines: list[str]) -> list[PpPainting]:
    """
    Cada linha é ``<Tipo restante>``. Mantemos o restante como raw
    (textos contém aspas internas e escapes que faríamos mal de
    re-tokenizar prematuramente).
    """
    paintings: list[PpPainting] = []
    for raw in lines:
        inner = _strip_brackets(raw)
        if inner is None:
            continue
        type_, _, rest = inner.partition(" ")
        paintings.append(PpPainting(type=type_, raw=rest))
    return paintings


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------


_BLOCK_NAMES = ("Properties", "Symbol", "Components", "Wires", "Diagrams", "Paintings")


def parse_sch(text: str) -> PpProject:
    """
    Faz parse de uma string contendo um arquivo `.sch` do Qucs e
    retorna um `PpProject`.

    Tolerante a:
      * Linhas em branco em qualquer lugar.
      * Quebras de linha CRLF / LF.
      * Indentação variável (Qucs usa 2 espaços, mas não dependemos).
      * Comentários ou linhas inesperadas antes do header (preservados
        em ``raw_pre_header``).
      * Bloco ``<Symbol>`` ausente (versões antes de 0.0.5).
    """
    lines = text.splitlines()

    project = PpProject()

    # 1. Localizar header e capturar pre-header
    i = 0
    pre: list[str] = []
    while i < len(lines):
        m = _HEADER_RE.match(lines[i])
        if m:
            project.version = m.group(1)
            i += 1
            break
        # linha não-header antes do <Qucs Schematic>: preserva
        if lines[i].strip():
            pre.append(lines[i])
        i += 1
    else:
        raise ValueError("Header '<Qucs Schematic ...>' não encontrado.")
    project.raw_pre_header = pre

    # 2. Iterar pelos blocos
    while i < len(lines):
        s = lines[i].strip()
        i += 1
        if not s:
            continue
        # Esperamos algo do tipo "<Properties>" iniciando um bloco
        block_name = None
        for name in _BLOCK_NAMES:
            if s == f"<{name}>":
                block_name = name
                break
        if block_name is None:
            # Linha solta que não inicia bloco conhecido — ignora
            # (o Qucs não emite isso, mas não vale crashar).
            continue
        # Coletar até "</Block>"
        body: list[str] = []
        end_tag = f"</{block_name}>"
        while i < len(lines) and lines[i].strip() != end_tag:
            body.append(lines[i])
            i += 1
        if i < len(lines):
            i += 1  # consome o </Block>

        if block_name == "Properties":
            project.properties = _parse_properties_block(body)
        elif block_name == "Symbol":
            project.symbol = _parse_symbol_block(body)
        elif block_name == "Components":
            for raw in body:
                inner = _strip_brackets(raw)
                if inner is None:
                    continue
                project.components.append(_parse_component_line(inner))
        elif block_name == "Wires":
            for raw in body:
                inner = _strip_brackets(raw)
                if inner is None:
                    continue
                project.wires.append(_parse_wire_line(inner))
        elif block_name == "Diagrams":
            project.diagrams = _parse_diagrams_block(body)
        elif block_name == "Paintings":
            project.paintings = _parse_paintings_block(body)

    return project


def parse_sch_file(path: str | Path, encoding: str = "utf-8") -> PpProject:
    """
    Conveniência: lê arquivo do disco e devolve `PpProject`.

    O Qucs salva tipicamente em UTF-8, mas alguns arquivos antigos
    podem ser em Latin-1. Se o decode em UTF-8 falhar, reabre em
    Latin-1 (que não pode falhar) e segue.
    """
    p = Path(path)
    try:
        text = p.read_text(encoding=encoding)
    except UnicodeDecodeError:
        text = p.read_text(encoding="latin-1")
    return parse_sch(text)
