"""
app.preprocessor.bridge_from_atp — converte um `AtpProject` em
`PpProject` Qucs-like com layout heurístico, para que o usuário
possa abrir um `.atp` legado no editor visual da v0.21.3.

Layout heurístico (v0.21.1)
---------------------------

Algoritmo simples e determinístico — refinado nas próximas sprints:

1. Cada *nó ATP* vira uma posição Y (linha horizontal):
   * Ground / nome vazio → coluna lateral, Y baixa.
   * Nós com sufixo A/B/C → colunas trifásicas (esquerda).
   * Outros nós → distribuídos verticalmente.
2. Cada *componente ATP* é posicionado na coluna que melhor
   encaixa seus dois terminais (média horizontal entre os dois
   nós que ele conecta).
3. Wires são gerados da posição do componente até cada nó.

O resultado é "feio mas correto" — abre no editor, e o usuário
re-arranja como quiser. Layout estético é um problema separado
(v0.21.7 talvez).

Limitações
----------

* Componentes com `semantic_type` desconhecido: convertidos em R
  com warning.
* Transformer / line / nonlinear: convertidos como blocos genéricos
  para que o ciclo round-trip não perca info — não viram componentes
  Qucs nativos perfeitos.
"""

from __future__ import annotations

from app.core.project_model import (
    AtpProject,
    BranchComponent,
    SourceComponent,
    SwitchComponent,
)

from .models import PpComponent, PpProject, PpProperty, PpWire


# ---------------------------------------------------------------------------
# Constantes de layout
# ---------------------------------------------------------------------------

_GRID = 10            # Qucs grid
_COL_WIDTH = 120      # espaço entre colunas de componentes
_ROW_HEIGHT = 80      # espaço entre nós (linhas horizontais)
_X_ORIGIN = 100
_Y_ORIGIN = 100
_GND_COL_X = 50       # coluna onde colocamos GNDs (à esquerda)


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


def _node_y_map(atp: AtpProject) -> dict[str, int]:
    """
    Atribui uma coordenada Y a cada nó. Nó "" (terra) fica num Y
    sintético separado (não aparece no mapa explícito — GNDs são
    colocados ad-hoc).
    """
    # Coletar nomes de nó preservando ordem de descoberta para
    # reprodutibilidade (em vez de set, usamos dict de chaves).
    seen: dict[str, None] = {}
    for b in atp.branches:
        for n in (b.node1, b.node2):
            if n and n not in seen:
                seen[n] = None
    for s in atp.switches:
        for n in (s.node1, s.node2):
            if n and n not in seen:
                seen[n] = None
    for src in atp.sources:
        if src.node and src.node not in seen:
            seen[src.node] = None

    result: dict[str, int] = {}
    for i, name in enumerate(seen):
        result[name] = _Y_ORIGIN + i * _ROW_HEIGHT
    return result


def _component_y_for_pair(n1: str, n2: str, ymap: dict[str, int]) -> int:
    """Y do componente: média dos Ys dos dois nós, ou Y do único nó."""
    y1 = ymap.get(n1)
    y2 = ymap.get(n2)
    if y1 is not None and y2 is not None:
        return (y1 + y2) // 2
    if y1 is not None:
        return y1
    if y2 is not None:
        return y2
    return _Y_ORIGIN


def _next_col_x(state: dict) -> int:
    """Aloca próxima coluna X."""
    state["next_x"] = state.get("next_x", _X_ORIGIN) + _COL_WIDTH
    return state["next_x"] - _COL_WIDTH


# ---------------------------------------------------------------------------
# Conversores por tipo
# ---------------------------------------------------------------------------


def _branch_to_pp(b: BranchComponent, x: int, y: int) -> PpComponent:
    """Resolve um `BranchComponent` ATP no melhor componente Qucs."""
    sem = (b.semantic_type or "").lower()
    name = (b.ref1 or "B?").strip() or "B?"

    if sem == "resistor" or (b.resistance and not b.inductance and not b.capacitance):
        return PpComponent(
            type="R", name=name, visible=True,
            x=x, y=y,
            label_dx=15, label_dy=-26, mirror=0, rotation=1,
            properties=[
                PpProperty(value=f"{b.resistance or '0'} Ohm", visible=True),
                PpProperty(value="26.85", visible=False),
                PpProperty(value="european", visible=False),
            ],
        )
    if sem == "inductor" or (b.inductance and not b.resistance and not b.capacitance):
        return PpComponent(
            type="L", name=name, visible=True,
            x=x, y=y,
            label_dx=-26, label_dy=10, mirror=0, rotation=0,
            properties=[
                PpProperty(value=f"{b.inductance or '0'} mH", visible=True),
                PpProperty(value="0", visible=False),
            ],
        )
    if sem == "capacitor" or (b.capacitance and not b.resistance and not b.inductance):
        return PpComponent(
            type="C", name=name, visible=True,
            x=x, y=y,
            label_dx=17, label_dy=-26, mirror=0, rotation=1,
            properties=[
                PpProperty(value=f"{b.capacitance or '0'} uF", visible=True),
                PpProperty(value="0", visible=False),
            ],
        )
    # Fallback: R genérico (para preservar topologia)
    return PpComponent(
        type="R", name=name, visible=True,
        x=x, y=y,
        label_dx=15, label_dy=-26, mirror=0, rotation=1,
        properties=[
            PpProperty(value=f"{b.resistance or '1'} Ohm", visible=True),
        ],
    )


def _switch_to_pp(s: SwitchComponent, x: int, y: int) -> PpComponent:
    """Resolve um `SwitchComponent` ATP no melhor componente Qucs."""
    sem = (s.semantic_type or "").lower()
    name = "Sw"
    if sem == "diode":
        return PpComponent(
            type="Diode", name=name, visible=True,
            x=x, y=y,
            label_dx=-26, label_dy=15, mirror=0, rotation=0,
        )
    if sem == "thyristor":
        return PpComponent(
            type="Thyr", name=name, visible=True,
            x=x, y=y,
            label_dx=-26, label_dy=15, mirror=0, rotation=0,
        )
    if sem == "igbt":
        return PpComponent(type="IGBT", name=name, visible=True,
                           x=x, y=y, label_dx=-26, label_dy=15,
                           mirror=0, rotation=0)
    if sem == "mosfet":
        return PpComponent(type="MOSFET", name=name, visible=True,
                           x=x, y=y, label_dx=-26, label_dy=15,
                           mirror=0, rotation=0)
    return PpComponent(
        type="Relais", name=name, visible=True,
        x=x, y=y, label_dx=-26, label_dy=15, mirror=0, rotation=0,
        properties=[
            PpProperty(value=f"{s.t_close or '0'}", visible=False),
            PpProperty(value=f"{s.t_open or '1'}", visible=False),
        ],
    )


def _source_to_pp(src: SourceComponent, x: int, y: int) -> PpComponent:
    """Source ATP → Vdc/Vac/Idc/Iac Qucs."""
    sem = (src.semantic_type or "").lower()
    name = "V?"
    if sem == "ac":
        type_ = "Iac" if (src.type_code or "").startswith("-") else "Vac"
        props = [
            PpProperty(value=f"{src.amplitude or '0'} V", visible=True),
            PpProperty(value=f"{src.frequency or '60'} Hz", visible=True),
            PpProperty(value=src.phase or "0", visible=False),
            PpProperty(value="0", visible=False),
        ]
    else:
        type_ = "Idc" if (src.type_code or "").startswith("-") else "Vdc"
        props = [
            PpProperty(value=f"{src.amplitude or '0'} V", visible=True),
        ]
    return PpComponent(
        type=type_, name=name, visible=True,
        x=x, y=y,
        label_dx=18, label_dy=-26, mirror=0, rotation=1,
        properties=props,
    )


# ---------------------------------------------------------------------------
# Wires de conexão
# ---------------------------------------------------------------------------


def _make_wires_for_pair(
    cx: int, cy: int, n1: str, n2: str, ymap: dict[str, int],
) -> list[PpWire]:
    """
    Gera 2 fios verticais ligando o componente em (cx, cy) aos
    nós n1 (acima) e n2 (abaixo). Usa o Y do nó no ymap.
    """
    wires: list[PpWire] = []
    if n1 in ymap:
        wires.append(PpWire(
            x1=cx, y1=cy - 30, x2=cx, y2=ymap[n1],
            label=n1, label_x=cx + 10, label_y=ymap[n1] - 10,
            label_visible=10,
        ))
    if n2 in ymap:
        wires.append(PpWire(
            x1=cx, y1=cy + 30, x2=cx, y2=ymap[n2],
            label=n2, label_x=cx + 10, label_y=ymap[n2] + 10,
            label_visible=10,
        ))
    return wires


def _make_gnd(x: int, y: int) -> PpComponent:
    return PpComponent(
        type="GND", name="*", visible=True,
        x=x, y=y, label_dx=0, label_dy=0, mirror=0, rotation=0,
    )


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------


def from_atp(atp: AtpProject, version: str = "0.0.19") -> PpProject:
    """
    Constrói um `PpProject` a partir de um `AtpProject`.

    O layout é determinístico (mesma entrada → mesma saída) mas
    "preliminar" — o usuário deve arrumar o esquemático no editor.

    Wires usam labels de nó para preservar nomes ATP no round-trip:
    parsear o `.sch` resultante e rodar `to_atp` deve recuperar a
    mesma malha de nós.
    """
    pp = PpProject(version=version)
    # Properties default
    pp.properties = {
        "View": "0,0,800,800,1,0,0",
        "Grid": "10,10,1",
        "DataSet": "circuit.dat",
        "DataDisplay": "circuit.dpl",
        "OpenDisplay": "1",
        "showFrame": "0",
        "FrameText0": "Title",
        "FrameText1": "Drawn By:",
        "FrameText2": "Date:",
        "FrameText3": "Revision:",
    }

    ymap = _node_y_map(atp)
    state: dict = {"next_x": _X_ORIGIN}

    # 1. Branches → Qucs components + wires
    for b in atp.branches:
        x = _next_col_x(state)
        y = _component_y_for_pair(b.node1, b.node2, ymap)
        comp = _branch_to_pp(b, x, y)
        pp.components.append(comp)
        pp.wires.extend(_make_wires_for_pair(x, y, b.node1, b.node2, ymap))

    # 2. Switches
    for s in atp.switches:
        x = _next_col_x(state)
        y = _component_y_for_pair(s.node1, s.node2, ymap)
        comp = _switch_to_pp(s, x, y)
        pp.components.append(comp)
        pp.wires.extend(_make_wires_for_pair(x, y, s.node1, s.node2, ymap))

    # 3. Sources (single-terminal: o outro pino vai para GND)
    for src in atp.sources:
        x = _next_col_x(state)
        y = _component_y_for_pair(src.node, "", ymap)
        comp = _source_to_pp(src, x, y)
        pp.components.append(comp)
        # Nó vivo
        if src.node in ymap:
            pp.wires.append(PpWire(
                x1=x, y1=y - 30, x2=x, y2=ymap[src.node],
                label=src.node,
                label_x=x + 18, label_y=ymap[src.node] - 10,
                label_visible=10,
            ))
        # GND no outro lado
        gnd_y = y + 60
        pp.components.append(_make_gnd(x, gnd_y))
        pp.wires.append(PpWire(
            x1=x, y1=y + 30, x2=x, y2=gnd_y,
            label="", label_x=0, label_y=0, label_visible=0,
        ))

    return pp
