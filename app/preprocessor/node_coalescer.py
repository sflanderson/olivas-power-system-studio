"""
app.preprocessor.node_coalescer — converte a topologia gráfica do
PpProject (componentes posicionados + fios) em um conjunto de nós
nomeados usáveis pelo ATP.

Algoritmo
---------

1. Coletamos todos os "pinos elétricos" (pontos do canvas onde algo
   se conecta): extremidades dos fios, e pinos dos componentes.
2. Construímos uma estrutura union-find (DSU) sobre esses pontos:
    * cada fio une suas duas extremidades;
    * cada componente une seus pinos? **NÃO** — pinos do mesmo
      componente são *terminais distintos* eletricamente. O union
      acontece SÓ pelos fios.
3. O resultado é uma partição do conjunto de pinos em **componentes
   conexos**. Cada componente conexo é um *nó elétrico*.
4. Atribuímos um nome ATP a cada nó:
   * se algum fio do nó tem `label` não-vazio → usa o label
     (truncado a 6 chars, padrão ATP);
   * se algum pino do nó pertence a um componente `GND` → o nó
     vira `""` (terra implícita do ATP);
   * caso contrário, gera um nome sintético `N0001`, `N0002`, ...

A saída é um `NodeMap` que mapeia ``(component_name, pin_index)``
→ nome do nó ATP. A bridge `to_atp.py` consulta esse mapa para
preencher os campos `node1`/`node2`/`node` dos componentes ATP.

Limitações conhecidas (v0.21.1)
-------------------------------

* Pinos de componente são derivados de uma tabela estática em
  `pin_geometry()` por tipo. Tipos não tabelados terão pinos
  inferidos a partir de orientação/rotação padrão (1 pino na
  ancoragem + 1 a uma distância padrão).
* Rotações 90/180/270 não são aplicadas com precisão geométrica
  na v1 — assumimos pinos no eixo horizontal a partir do anchor
  (suficiente para circuitos simples; refino na v0.21.2 quando
  os símbolos vetoriais forem desenhados).
* Wires diagonais não existem no Qucs (sempre H ou V), então não
  precisamos de tolerância angular.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from app.preprocessor.spec import get_default_registry

from .models import PpComponent, PpProject, PpWire


# ---------------------------------------------------------------------------
# Geometria de pinos
# ---------------------------------------------------------------------------


# Para cada tipo de componente, lista de (dx, dy) representando os
# pinos relativos ao ponto de ancoragem em rotação 0, sem espelho.
# O Qucs usa grid 10px e os pinos ficam tipicamente em múltiplos de
# 10 a partir do anchor.
#
# REFERÊNCIA: inspeção dos exemplos. Não é completa — componentes
# desconhecidos caem no default.
#
# A partir de v0.21.8.b, :func:`pin_positions` consulta o registry
# ``get_default_registry()`` primeiro (``spec.pins[*].position``) e
# só cai neste dict legado para códigos sem ``.ocomp``.
_PIN_GEOMETRY: dict[str, list[tuple[int, int]]] = {
    # 2-terminal passivos / fontes verticais: pinos a ±30 do anchor no eixo Y
    "R":       [(0, -30), (0,  30)],
    "L":       [(0, -30), (0,  30)],
    "C":       [(0, -30), (0,  30)],
    "Vdc":     [(0, -30), (0,  30)],
    "Vac":     [(0, -30), (0,  30)],
    "Idc":     [(0, -30), (0,  30)],
    "Iac":     [(0, -30), (0,  30)],
    "Vrect":   [(0, -30), (0,  30)],
    "Vsurge":  [(0, -30), (0,  30)],
    "VProbe":  [(0, -30), (0,  30)],
    # Não-lineares verticais
    "ZnO":     [(0, -30), (0,  30)],
    "RNL":     [(0, -30), (0,  30)],
    "LNL":     [(0, -30), (0,  30)],
    # Semicondutores horizontais (2 pinos)
    "Diode":   [(-30, 0), (30, 0)],
    "IProbe":  [(-30, 0), (30, 0)],
    # Semicondutores horizontais com gate (3 pinos)
    "Thyr":    [(-30, 0), (30, 0), (10, -20)],
    "GTO":     [(-30, 0), (30, 0), (10, -20)],
    "IGBT":    [(-30, 0), (30, 0), (0,  20)],
    "MOSFET":  [(-30, 0), (30, 0), (0,  20)],
    # Ground: 1 pino, no anchor
    "GND":     [(0, 0)],
    # Chaves horizontais (SwIdeal / SwTACS / VCB em ±30, Relais em ±50)
    "SwIdeal": [(-30, 0), (30, 0)],
    "SwTACS":  [(-30, 0), (30, 0)],
    "VCB":     [(-30, 0), (30, 0)],
    "Relais":  [(-50, 0), (50, 0)],   # Qucs Relais é comprido
    # VCB trifásico: 3 chaves empilhadas, pinos em ±40
    # Ordem: A_in, A_out, B_in, B_out, C_in, C_out
    "VCB3":    [(-40, -30), (40, -30),
                (-40,   0), (40,   0),
                (-40,  30), (40,  30)],
    # Transformers / acoplados: 4 pinos (primário e secundário)
    "Tr":      [(-30, -20), (-30, 20), (30, -20), (30, 20)],
    "sTr":     [(-30, -20), (-30, 20), (30, -20), (30, 20)],
    "Tr3":     [(-30, -20), (-30, 20), (30, -20), (30, 20)],
    "MUT":     [(-30, -20), (-30, 20), (30, -20), (30, 20)],
    # Linhas: retângulo horizontal com 2 pinos
    "TLIN":    [(-30, 0), (30, 0)],
    "BERG":    [(-30, 0), (30, 0)],
    "JMARTI":  [(-30, 0), (30, 0)],
    # Blocos de controle e diretivas: nenhum pino elétrico
    "TACS":    [],
    "MODEL":   [],
    "Eqn":     [],
    ".TR":     [],
    ".DC":     [],
    ".AC":     [],
    ".SW":     [],
    ".SP":     [],
    # Substrate, etc. — sem pinos elétricos (paramétrico)
}


# Quando a rotação do componente é 1, 2 ou 3 (90, 180, 270 anti-
# horário), o vetor de pino (dx, dy) sofre transformação rígida.
# Espelho horizontal inverte dy. (Notação: rotação CCW.)
def _transform_pin(dx: int, dy: int, rotation: int, mirror: int) -> tuple[int, int]:
    """Aplica rotação (0..3 ×90° CCW) e espelho ao vetor de pino."""
    rotation %= 4
    # Mirror = 1 espelha eixo Y (inverte x)
    if mirror:
        dx = -dx
    if rotation == 0:
        return (dx, dy)
    if rotation == 1:    # 90° CCW: (x,y) -> (-y, x)
        return (-dy, dx)
    if rotation == 2:    # 180°: (x,y) -> (-x, -y)
        return (-dx, -dy)
    if rotation == 3:    # 270° CCW: (x,y) -> (y, -x)
        return (dy, -dx)
    return (dx, dy)


def _pin_geometry_for(type_code: str) -> list[tuple[int, int]] | None:
    """
    Resolve a geometria de pinos (offsets `(dx, dy)`) para um tipo.

    Registry-first (v0.21.8.b): consulta ``get_default_registry()``;
    se o tipo tem ``.ocomp`` registrado, retorna ``spec.pins[*].position``.
    Caso contrário, consulta ``_PIN_GEOMETRY`` legado.

    Retorna None se o tipo não está em lugar nenhum — o caller decide o
    fallback (atualmente, 2-terminal vertical).
    """
    spec = get_default_registry().get(type_code)
    if spec is not None:
        return [p.position for p in spec.pins]
    return _PIN_GEOMETRY.get(type_code)


def pin_positions(component: PpComponent) -> list[tuple[int, int]]:
    """
    Retorna as coordenadas absolutas (x, y) de cada pino elétrico
    de `component`, na ordem em que aparecem no catálogo
    `_PIN_GEOMETRY`.

    Registry-first (v0.21.8.b): se há ``.ocomp`` para ``component.type``,
    usa ``spec.pins[*].position``; senão consulta ``_PIN_GEOMETRY`` legado.

    Componentes não tabelados recebem o default ``[(0, -30), (0, 30)]``
    (componente 2-terminal vertical) — o suficiente para a v0.21.1.

    v0.92.1: para ``BUS``, gera pinos SINTÉTICOS a cada 10 px ao
    longo da barra (estilo PTW Power*Tools). O comprimento é lido
    da propriedade ``"length"`` (default 200 px). Isto permite
    que wires conectem em qualquer ponto do barramento e o
    analyzer (find_neighbors_of_bus) os reconheça corretamente.
    """
    if component.type == "BUS":
        return _bus_pin_positions(component)

    geom = _pin_geometry_for(component.type)
    if geom is None:
        # default: 2-terminal vertical
        geom = [(0, -30), (0, 30)]
    out: list[tuple[int, int]] = []
    for dx, dy in geom:
        tx, ty = _transform_pin(dx, dy, component.rotation, component.mirror)
        out.append((component.x + tx, component.y + ty))
    return out


def _bus_pin_positions(component: PpComponent) -> list[tuple[int, int]]:
    """
    v0.92.1 — Pinos sintéticos do BUS PTW.

    Lê o comprimento da barra da propriedade ``length`` do
    PpComponent (consultando o spec do catálogo para o índice).
    Gera pinos a cada 10 px ao longo do eixo Y=0 (local), de
    ``-length/2`` a ``+length/2``.

    Aplica rotação e espelho via :func:`_transform_pin` para
    suportar BUS verticais (rotation=1) ou espelhados.
    """
    # Default 200 (mesmo do BusSymbol)
    length = 200
    spec = get_default_registry().get("BUS")
    if spec is not None:
        for idx, prop_spec in enumerate(spec.properties):
            if prop_spec.name == "length":
                if idx < len(component.properties):
                    raw = component.properties[idx].value
                    try:
                        length = max(60, min(4000,
                            int(float(str(raw)))))
                    except (TypeError, ValueError):
                        pass
                break
    half = (length // 2 // 10) * 10
    spacing = 10

    out: list[tuple[int, int]] = []
    x = -half
    while x <= half:
        tx, ty = _transform_pin(
            x, 0, component.rotation, component.mirror,
        )
        out.append((component.x + tx, component.y + ty))
        x += spacing
    return out


# ---------------------------------------------------------------------------
# Union-find (DSU) sobre pontos do canvas
# ---------------------------------------------------------------------------


class _DSU:
    """Disjoint-set union para chaves arbitrárias hashable."""

    def __init__(self) -> None:
        self.parent: dict = {}
        self.rank: dict = {}

    def make(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0

    def find(self, x):
        self.make(x)
        # path compression
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def _point_on_segment(
    ax: int, ay: int, bx: int, by: int, px: int, py: int,
) -> bool:
    """
    Verifica se o ponto (px, py) está sobre o segmento de reta
    A(ax, ay) → B(bx, by) (collinear E dentro do range).

    Implementação para coordenadas inteiras (Qucs sempre emite
    em grid). Para wires diagonais (raros mas possíveis),
    usamos cross-product = 0 + bounding box check.

    v0.28.2-PRO: novo helper para detecção de pinos no meio
    de wires (auditoria P0).
    """
    # Cross product = 0 → colinear
    cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
    if cross != 0:
        return False
    # Dentro do bounding box (estritamente entre, não nos endpoints)
    if min(ax, bx) <= px <= max(ax, bx) and min(ay, by) <= py <= max(ay, by):
        # Excluir endpoints (já tratados em Passo 4)
        if (px, py) == (ax, ay) or (px, py) == (bx, by):
            return False
        return True
    return False


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------


@dataclass
class NodeMap:
    """
    Resultado da coalescência de nós.

    Attributes
    ----------
    pin_to_node:
        ``(component_name, pin_index) → nome_atp``.
        Para componentes sem nome explícito (ex: GND com nome "*"),
        usamos uma chave sintética ``"*<idx>"`` baseada na ordem.
    node_to_pins:
        Inverso, para inspeção.
    ground_node:
        Nome usado para a terra. ATP usa string vazia (`""`) por
        convenção. Componentes GND fazem com que seu cluster
        receba esse nome.
    next_synthetic:
        Próximo número usado em geração `N0001, N0002, ...`. Útil
        em testes para validar contagem.
    """

    pin_to_node: dict[tuple[str, int], str] = field(default_factory=dict)
    node_to_pins: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    ground_node: str = ""
    next_synthetic: int = 1


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------


_ATP_NODE_MAX_LEN = 6


def _normalize_label(label: str) -> str:
    """
    Sanitiza um label do `.sch` para virar nome de nó ATP.
    * Strip whitespace.
    * Substitui caracteres não-alfanuméricos por `_`.
    * Trunca a 6 caracteres.
    * Vazio → vazio (deixa o caller decidir GND vs sintético).
    """
    s = label.strip()
    if not s:
        return ""
    out_chars = []
    for ch in s:
        if ch.isalnum():
            out_chars.append(ch)
        else:
            out_chars.append("_")
    return "".join(out_chars)[:_ATP_NODE_MAX_LEN]


def coalesce_nodes(project: PpProject) -> NodeMap:
    """
    Calcula a malha de nós ATP de `project`.

    Procedimento
    ------------
    1. Atribui chave sintética `"*0"`, `"*1"`, ... a cada componente
       sem nome explícito (GND com name="*").
    2. Adiciona TODOS os pinos de TODOS os componentes ao DSU como
       elementos individuais.
    3. Para cada wire, une seus dois endpoints.
    4. Para cada pino de componente que cai exatamente sobre uma
       extremidade ou ponto intermediário de um wire, une-o àquele
       endpoint.
    5. Coleta clusters; resolve nome (GND > label de wire > sintético).
    """
    nm = NodeMap()
    dsu = _DSU()

    # ---- Passo 1: chaves de componente (lidar com nome "*")
    comp_keys: list[tuple[PpComponent, str]] = []
    star_counter = 0
    for c in project.components:
        if c.name == "*":
            key = f"*{star_counter}"
            star_counter += 1
        else:
            key = c.name
        comp_keys.append((c, key))

    # ---- Passo 2: pinos como tokens DSU
    # token de um pino: ("pin", comp_key, pin_index)
    # token de um endpoint de wire: ("pt", x, y)
    pin_pts: dict[tuple[int, int], list[tuple[str, int]]] = defaultdict(list)
    for c, key in comp_keys:
        positions = pin_positions(c)
        for idx, (px, py) in enumerate(positions):
            tok = ("pin", key, idx)
            dsu.make(tok)
            pin_pts[(px, py)].append((key, idx))
        # v0.93.3 — BUS é fisicamente uma barra de cobre interna-
        # mente em curto. Todos os seus pinos compartilham o
        # mesmo potencial elétrico. Antes (v0.92.1+v0.92.2) cada
        # um dos 21 pinos sintéticos era um nó independente,
        # quebrando find_neighbors_of_bus / build_sc_network
        # quando as fontes ligavam apenas em uma ponta da barra.
        # Corrigido aqui: unimos todos os pinos do BUS num único
        # cluster lógico já no passo 2.
        if c.type == "BUS" and len(positions) > 1:
            anchor_tok = ("pin", key, 0)
            for idx in range(1, len(positions)):
                dsu.union(anchor_tok, ("pin", key, idx))

    # ---- Passo 3: wires
    for w in project.wires:
        a = ("pt", w.x1, w.y1)
        b = ("pt", w.x2, w.y2)
        dsu.make(a)
        dsu.make(b)
        dsu.union(a, b)

    # ---- Passo 4: pinos de componente que coincidem com pontos de wire
    for (px, py), pin_keys in pin_pts.items():
        pt_tok = ("pt", px, py)
        if pt_tok in dsu.parent:
            for ck, idx in pin_keys:
                dsu.union(("pin", ck, idx), pt_tok)
        # Se não há wire passando por esse ponto, união só entre os
        # pinos que coincidirem (componentes encostados sem fio):
        if len(pin_keys) > 1:
            anchor = pin_keys[0]
            for ck, idx in pin_keys[1:]:
                dsu.union(("pin", *anchor), ("pin", ck, idx))

    # ---- Passo 4.5: pinos no MEIO de wires (auditoria v0.27.11.1 P0)
    # v0.28.2-PRO: detecta pinos colineares com wires (não apenas
    # endpoints). Resolve bug topológico onde pinos no meio de fios
    # eram tratados como desconectados, gerando netlists incorretos.
    for w in project.wires:
        ax, ay = w.x1, w.y1
        bx, by = w.x2, w.y2
        for (px, py), pin_keys in pin_pts.items():
            # Já tratado se for endpoint exato — pula
            if (px, py) == (ax, ay) or (px, py) == (bx, by):
                continue
            # Verifica colinearidade e dentro do segmento
            if _point_on_segment(ax, ay, bx, by, px, py):
                # Pino está no meio do wire — une com o wire
                pt_tok = ("pt", ax, ay)
                if pt_tok in dsu.parent:
                    for ck, idx in pin_keys:
                        dsu.union(("pin", ck, idx), pt_tok)

    # Também: wires que passam sobre wires/pontos com mesmo (x, y)
    # já são unidos automaticamente pelo passo 3 (mesma chave DSU).

    # ---- Passo 5: agrupar por root e nomear
    cluster_pins: dict = defaultdict(list)
    cluster_labels: dict = defaultdict(list)
    cluster_has_gnd: dict = defaultdict(bool)

    # Coleta pinos por cluster
    for c, key in comp_keys:
        for idx, _ in enumerate(pin_positions(c)):
            tok = ("pin", key, idx)
            root = dsu.find(tok)
            cluster_pins[root].append((key, idx))
            if c.type == "GND":
                cluster_has_gnd[root] = True

    # Coleta labels via wire endpoints
    for w in project.wires:
        if w.label:
            for tok in (("pt", w.x1, w.y1), ("pt", w.x2, w.y2)):
                if tok in dsu.parent:
                    root = dsu.find(tok)
                    cluster_labels[root].append(w.label)

    # ---- Atribuir nomes
    synthetic = 1
    for root, pins in cluster_pins.items():
        if cluster_has_gnd[root]:
            name = nm.ground_node  # ""
        elif cluster_labels[root]:
            # Pega o primeiro label (a maioria dos circuitos tem
            # só um label por cluster; se houver múltiplos, é
            # ambiguidade do desenhista — pegamos o primeiro).
            name = _normalize_label(cluster_labels[root][0])
            if not name:  # label virou vazia após sanitização
                name = f"N{synthetic:04d}"
                synthetic += 1
        else:
            name = f"N{synthetic:04d}"
            synthetic += 1
        for pin in pins:
            nm.pin_to_node[pin] = name
        nm.node_to_pins.setdefault(name, []).extend(pins)

    nm.next_synthetic = synthetic
    return nm


# ---------------------------------------------------------------------------
# Helpers de inspeção (úteis em debug e testes)
# ---------------------------------------------------------------------------


def get_pin_node(node_map: NodeMap, component: PpComponent, pin_index: int,
                 component_index: Optional[int] = None) -> str:
    """
    Lookup do nome de nó atribuído a um pino específico.

    Para componentes ``GND`` (nome `*`), passe `component_index`
    (índice na lista `project.components`) — a mesma convenção
    `*N` usada internamente é aplicada.
    """
    if component.name == "*":
        if component_index is None:
            raise ValueError("GND requer component_index para lookup")
        # Esta heurística NÃO é robusta se houver outros nomes "*"
        # antes do pretendido — usar com cuidado.
        # Para precisão, prefira iterar via `project.components` e
        # contar GNDs.
        key = f"*{component_index}"
    else:
        key = component.name
    return node_map.pin_to_node.get((key, pin_index), "")
