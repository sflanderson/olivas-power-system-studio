"""
app.preprocessor.models — modelo de dados do esquemático estilo Qucs.

Este módulo define apenas dataclasses puras (sem dependência de Qt,
PySide6, ATP ou qualquer engine de simulação). O parser e o
serializer constroem e consomem essas estruturas; o editor visual
em PySide6 (sprint v0.21.3) e a bridge para AtpProject (sprint
v0.21.1) trabalham em cima delas.

Convenções herdadas do formato `.sch` do Qucs:

* Coordenadas em pixels (origem no canto sup. esquerdo, x→direita,
  y→baixo). O grid padrão é 10 px.
* `mirror`: 0 = normal, 1 = espelhado horizontalmente.
* `rotation`: 0..3, em múltiplos de 90° anti-horário.
* `visible` em propriedade: 1 = label desenhado no canvas, 0 = oculto.
* `name = "*"` para componentes sem nome explícito (ex: GND).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Propriedade de componente
# ---------------------------------------------------------------------------


@dataclass
class PpProperty:
    """
    Uma propriedade nomeada de um componente.

    No formato `.sch` propriedades aparecem como pares
    `"<valor>" <0|1>` após os campos posicionais do componente.
    O índice/posição da propriedade na lista é que dá significado
    semântico (ex: 0 = R em ohms para um resistor); o nome
    "humano" vive no catálogo (`catalog.py`), não aqui.

    Attributes
    ----------
    value:
        Valor textual exatamente como aparece no `.sch`. Pode incluir
        unidades (ex: ``"10 kOhm"``, ``"1 mH"``, ``"Vamp"``).
        Não fazemos parse para SI no modelo — isso é responsabilidade
        do `units.py` na sprint v0.21.1.
    visible:
        Se True, o label da propriedade é desenhado no canvas pelo
        editor (campo `1` no `.sch`).
    """

    value: str
    visible: bool = False
    # v3.1.1 Sprint 3: Library link/unlink (PTW Tutorial §Part 1 p.55).
    # Se ``linked_library`` não é None, o valor é herdado de uma library
    # vendor (ex: "ABB SACE Tmax T7") e o widget de propriedade fica
    # gray-out + read-only no Component Editor. Backward-compatible:
    # arquivos `.sch` antigos sem este campo carregam com None default.
    linked_library: Optional[str] = None


# ---------------------------------------------------------------------------
# Componente
# ---------------------------------------------------------------------------


@dataclass
class PpComponent:
    """
    Um componente posicionado no canvas.

    Formato textual no `.sch`::

        <TYPE NAME visible x y label_dx label_dy mirror rotation
              "prop1_value" prop1_visible
              "prop2_value" prop2_visible ...>

    Onde:

    * `TYPE`        — código curto Qucs (``R``, ``L``, ``C``, ``Vdc``,
                      ``Vac``, ``GND``, ``Diode``, ``Tr``, ``sTr``,
                      ``Relais``, ``IProbe``, ``Eqn``, ``.TR``,
                      ``.DC``, ``.SW``, ...).
    * `NAME`        — identificador único no esquemático
                      (``R1``, ``V2``, ``*`` para ground).
    * `visible`     — se 1, o nome do componente é desenhado.
    * `x`, `y`      — coordenadas do ponto de ancoragem (pixels).
    * `label_dx`,
      `label_dy`    — offset do nome em relação ao ponto de ancoragem.
    * `mirror`      — 0 ou 1.
    * `rotation`    — 0..3 (×90° anti-horário).
    * propriedades  — pares (valor, visível) variáveis por tipo.

    Attributes
    ----------
    raw_extra_fields:
        Tokens posicionais EXTRAS encontrados no `.sch` que não
        estavam previstos (ex: campos novos em versões futuras do
        formato). Preservados para round-trip perfeito.
    """

    type: str
    name: str
    visible: bool
    x: int
    y: int
    label_dx: int
    label_dy: int
    mirror: int
    rotation: int
    properties: list[PpProperty] = field(default_factory=list)
    raw_extra_fields: list[str] = field(default_factory=list)
    # v1.7.1: Active/Inactive flag (default True = active).
    # Não serializado no .sch (preservado em .ovs session ou via
    # property "state" para switching components). Backward-compat
    # total: campo com default não quebra construções existentes.
    is_active: bool = True

    def get(self, index: int, default: str = "") -> str:
        """Retorna o valor da propriedade no índice dado, ou default."""
        if 0 <= index < len(self.properties):
            return self.properties[index].value
        return default


# ---------------------------------------------------------------------------
# Fio
# ---------------------------------------------------------------------------


@dataclass
class PpWire:
    """
    Segmento de fio (sempre horizontal ou vertical no Qucs).

    Formato textual::

        <x1 y1 x2 y2 "label" label_x label_y label_visible [extra]>

    Onde `label`, quando não-vazio, dá nome ao **nó** ao qual
    aquele fio pertence — esse nome é o que vai virar nome de nó
    ATP no momento da bridge.

    O campo `extra` (uma string vazia adicional) aparece em versões
    do formato 0.0.15+; preservamos para round-trip.

    Attributes
    ----------
    x1, y1, x2, y2:
        Extremidades em pixels.
    label:
        Nome do nó (string vazia = nó anônimo, recebe nome
        sintético na bridge).
    label_x, label_y:
        Posição do label em pixels.
    label_visible:
        Bitmask Qucs (geralmente 0 quando vazio, ≠0 quando visível).
        Mantemos como int para fidelidade.
    has_extra:
        True se o `.sch` original tinha o 9º campo (string vazia
        opcional do formato 0.0.15+). Round-trip preserva.
    """

    x1: int
    y1: int
    x2: int
    y2: int
    label: str = ""
    label_x: int = 0
    label_y: int = 0
    label_visible: int = 0
    has_extra: bool = False


# ---------------------------------------------------------------------------
# Diagrama (preservado raw na v0.21.0)
# ---------------------------------------------------------------------------


@dataclass
class PpDiagram:
    """
    Diagrama Qucs (Rect, Polar, Smith, Tab, Curve3D, ...).

    Na sprint v0.21.0 preservamos o conteúdo bruto do bloco
    `<Diagrams>` para garantir round-trip sem perdas, sem ainda
    interpretar a semântica.

    Attributes
    ----------
    type:
        Primeiro token do bloco (ex: ``"Rect"``, ``"Polar"``).
    raw_header:
        Linha de cabeçalho completa **sem** os ``<`` e ``>``
        delimitadores.
    raw_curves:
        Linhas internas (cada curva/dataset) **sem** delimitadores.
    """

    type: str
    raw_header: str
    raw_curves: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Painting (anotação visual: Text, Arrow, Line, Rectangle, Ellipse)
# ---------------------------------------------------------------------------


@dataclass
class PpPainting:
    """
    Elemento gráfico decorativo (não-elétrico).

    Tipos comuns: ``Text``, ``Arrow``, ``Line``, ``Rectangle``,
    ``Ellipse``, ``EArc``.

    Como em `PpDiagram`, na v0.21.0 mantemos o restante da linha
    como string raw para garantir round-trip sem perdas.
    """

    type: str
    raw: str  # tudo após o tipo, sem os <> delimitadores


# ---------------------------------------------------------------------------
# Link Tags (PTW Tutorial §Part 1 p.35-42) — v3.1.1 Sprint 4
# ---------------------------------------------------------------------------


@dataclass
class PpLinkTag:
    """Hyperlink-style tag in a one-line diagram (PTW §Part 1 p.35-42).

    Click on a Link Tag in the canvas to navigate to:
    * Another one-line drawing (target = "oneline:DocName")
    * A TCC drawing (target = "tcc:CoordName")
    * A report (target = "report:RPT_Name")
    * A PDF / external file (target = "pdf:path/to/file.pdf")

    The ``target`` URI is a string with prefix indicating destination.
    The ``visible_text`` is what the user sees on the canvas.

    Attributes
    ----------
    label:
        Text shown on the canvas (default = same as `target`).
    target:
        URI-style target (``"oneline:..."``, ``"tcc:..."``, etc.).
    x, y:
        Position in scene coordinates.
    visible:
        Whether the tag is rendered.
    closed_arrow:
        If True, draw a small filled triangle indicator (PTW style).

    References
    ----------
    PTW Tutorial v8.0 §Part 1 p.35-42.
    """

    label: str
    target: str
    x: int = 0
    y: int = 0
    visible: bool = True
    closed_arrow: bool = True


# ---------------------------------------------------------------------------
# Legend Tags (PTW Tutorial §Part 1 p.43-52) — v3.1.1 Sprint 4
# ---------------------------------------------------------------------------


@dataclass
class PpLegendTag:
    """Legend tag for one-line annotations (PTW §Part 1 p.43-52).

    Provides a shape (Diamond / Hexagon / Circle / Rectangle) with text
    inside, used to annotate buses/zones/categories in one-line diagrams.
    Listed in View>Legend list for navigation.

    Attributes
    ----------
    text:
        Text shown inside the shape.
    shape:
        ``"Diamond"``, ``"Hexagon"``, ``"Circle"``, or ``"Rectangle"``.
    x, y:
        Position in scene coordinates.
    color:
        Fill color in hex (default ``#fff7c0`` light yellow per PTW).
    visible:
        Whether the tag is rendered.

    References
    ----------
    PTW Tutorial v8.0 §Part 1 p.43-52.
    """

    text: str
    shape: str = "Diamond"
    x: int = 0
    y: int = 0
    color: str = "#fff7c0"
    visible: bool = True

    _VALID_SHAPES = ("Diamond", "Hexagon", "Circle", "Rectangle")

    def __post_init__(self) -> None:
        if self.shape not in self._VALID_SHAPES:
            raise ValueError(
                f"shape must be one of {self._VALID_SHAPES}; "
                f"got {self.shape!r}"
            )


# ---------------------------------------------------------------------------
# Projeto inteiro
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Datablock (v0.86 — PTW Equipment-style)
# ---------------------------------------------------------------------------


@dataclass
class PpDataBlock:
    """
    Datablock textual ancorado a um componente do esquemático.

    Inspirado em SKM PowerTools Workstation Equipment datablocks:
    pequenas caixas de texto exibidas próximas a componentes com
    resultados-chave de análises (Ip, AFB, IE, categoria PPE,
    Loading %, V_pu, etc.).

    Não-persistente no `.sch` original (formato Qucs não tem
    suporte). Round-trip via sidecar JSON
    ``<schematic>.datablocks.json``.

    Sticky templates (v0.88)
    --------------------------

    O datablock mantém DOIS conjuntos de linhas:

    * ``template_lines`` — fonte com placeholders ``{nome:fmt}``,
      preservada entre refreshes. Edição via dialog atualiza
      este campo.
    * ``lines`` — view renderizada (resultado do último
      ``bind_lines(template_lines, values)``). É o que aparece no
      canvas. Atualizada por refresh ou edição.

    Compatibilidade v0.86/v0.87:
    Datablocks antigos têm ``template_lines == []``. Na primeira
    operação de bind/render que precisa do template, o sistema
    promove ``lines`` a ``template_lines`` (one-time migration
    durante load_project).

    Attributes
    ----------
    component_name:
        Nome do componente host (``PpComponent.name``).
    dx, dy:
        Offset do ancoragem do datablock em relação ao
        ``host.x/host.y`` (em pixels da scene). Atualizado
        automaticamente quando o usuário arrasta o datablock.
    lines:
        Linhas RENDERIZADAS (com valores substituídos quando
        houver). É o que o ``DataBlockItem`` desenha.
    template_lines:
        Linhas TEMPLATE com ``{placeholder:fmt}``. Preservadas
        entre análises para permitir múltiplos refreshes sem
        perder estrutura.
    visible:
        Toggle para esconder sem deletar.
    """

    component_name: str
    dx: int = 50
    dy: int = -10
    lines: list[str] = field(default_factory=list)
    template_lines: list[str] = field(default_factory=list)
    visible: bool = True

    def effective_template(self) -> list[str]:
        """
        Retorna o template "efetivo" para refresh:

        * ``template_lines`` se não-vazio (caso normal v0.88+).
        * ``lines`` em fallback (datablocks legacy v0.86/v0.87).

        Não muta o estado — apenas retorna a lista que deve ser
        passada para ``bind_lines``. A migração para
        ``template_lines`` acontece em ``load_project`` ou no
        primeiro edit.
        """
        return self.template_lines if self.template_lines else self.lines


# ---------------------------------------------------------------------------
# Diagrama (preservado raw na v0.21.0)
# ---------------------------------------------------------------------------


@dataclass
class PpProject:
    """
    Esquemático Qucs completo, equivalente a um arquivo `.sch`.

    Estrutura::

        <Qucs Schematic VERSION>
        <Properties> ... </Properties>
        <Symbol>     ... </Symbol>          # opcional, formato 0.0.5+
        <Components> ... </Components>
        <Wires>      ... </Wires>
        <Diagrams>   ... </Diagrams>
        <Paintings>  ... </Paintings>

    Attributes
    ----------
    version:
        Versão declarada no header (ex: ``"0.0.19"``).
        O serializer escreve exatamente este valor — útil para
        manter compatibilidade com o Qucs externo se um dia o
        usuário quiser exportar para abrir lá.
    properties:
        Dicionário ordenado de chave→valor do bloco
        ``<Properties>``. Valores são strings cruas.
    symbol:
        Linhas brutas (sem ``<>``) do bloco ``<Symbol>``. Vazio
        quando o esquemático não é um sub-circuito.
    components:
        Lista de componentes na ordem em que aparecem no `.sch`.
    wires:
        Lista de fios, mesma observação.
    diagrams:
        Diagramas de visualização (raw na v0.21.0).
    paintings:
        Anotações decorativas (raw na v0.21.0).
    raw_pre_header:
        Comentários ou linhas que o Qucs eventualmente coloca
        ANTES do `<Qucs Schematic ...>` — preservado para
        round-trip de arquivos vindos de versões futuras.
    """

    version: str = "0.0.19"
    properties: dict[str, str] = field(default_factory=dict)
    symbol: list[str] = field(default_factory=list)
    components: list[PpComponent] = field(default_factory=list)
    wires: list[PpWire] = field(default_factory=list)
    diagrams: list[PpDiagram] = field(default_factory=list)
    paintings: list[PpPainting] = field(default_factory=list)
    raw_pre_header: list[str] = field(default_factory=list)
    # v0.86: datablocks (não persistidos no .sch — sidecar JSON).
    datablocks: list["PpDataBlock"] = field(default_factory=list)
    # v3.1.1 Sprint 4: Link Tags + Legend Tags (PTW Tutorial §Part 1 p.35-52).
    # Persistidos como sidecar JSON (não no .sch raw para backward-compat).
    link_tags: list[PpLinkTag] = field(default_factory=list)
    legend_tags: list[PpLegendTag] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Helpers de acesso
    # ------------------------------------------------------------------

    def find_component(self, name: str) -> Optional[PpComponent]:
        """Localiza componente por nome (ex: ``'R1'``). None se ausente."""
        for c in self.components:
            if c.name == name:
                return c
        return None

    def components_of_type(self, type_code: str) -> list[PpComponent]:
        """Filtra componentes pelo código de tipo (ex: ``'R'``, ``'GND'``)."""
        return [c for c in self.components if c.type == type_code]

    def __repr__(self) -> str:  # pragma: no cover - cosmético
        return (
            f"PpProject(version={self.version!r}, "
            f"components={len(self.components)}, "
            f"wires={len(self.wires)}, "
            f"diagrams={len(self.diagrams)}, "
            f"paintings={len(self.paintings)})"
        )
