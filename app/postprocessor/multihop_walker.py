"""
app.postprocessor.multihop_walker — walking topológico multi-hop
através de transformadores e barramentos para encontrar fontes
de SC em cadeia.

Motivação
=========

A v0.27.7.5 fez walking 1-hop apenas — encontra os vizinhos
imediatos do BUS (componentes que compartilham um nó). Em
sistemas industriais reais, a cadeia tipicamente é:

::

    [UTIL] ── [TR1: 138/13.8] ── [BUS-MAIN] ── [TR2: 13.8/4.16] ── [BUS-CCM]
                                                                       │
                                                                  [Motors]

Para análise de SC no BUS-CCM, precisamos das fontes ULTIMATE
(UTIL via TR1+TR2 refletidos), não só dos vizinhos diretos
(que seriam apenas TR2 e os motors).

Conceitos
=========

* **TopologyChain**: caminho de uma fonte (Vac, SM) até o BUS
  alvo, passando por N transformadores.
* **find_source_chains**: BFS através do grafo
  componentes-conectados-por-nós, parando em fontes.
* **Transformer pass-through**: ao entrar num TR via um pino,
  saímos pelos pinos do "outro lado" (HV ↔ LV).

Cadeia → impedância
====================

Para cada chain, a impedância equivalente refletida ao bus alvo:

::

    Z_eq = Z_source + Σ_i (Z_TRi · ratio_i²)

Onde:
* Z_source: impedância da fonte ultimate (S_kQ" para rede ou
  Xd'' para SM).
* Z_TRi: impedância do i-ésimo TR no caminho (uk% × V²/S).
* ratio_i: razão de transformação acumulada do TR ao bus alvo.

Limitações MVP v0.27.7.7
=========================

* BFS simples — não trata loops corretamente (assume topologia
  radial).
* Pinos HV/LV identificados via heurística (primeiros N são
  HV, últimos M são LV) — pode falhar para componentes com
  geometria inversa.
* Apenas Tr/sTr/Tr3/BCTRAN/XFMR são "transparentes". TLIN/
  BERG/JMARTI são considerados como conexões diretas
  (impedância ignorada — MVP).

Referências
============

* IEC 60909-0:2016 §6.3 (transformer impedance reflection).
* IEEE 242-2001 (Buff Book) §15 (multi-level coordination).
* SKM PowerTools Workstation auto-topology.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.postprocessor.bus_pipeline import (
    SC_SOURCE_TYPES, classify_sc_source, find_bus_component,
)
from app.preprocessor.models import PpComponent, PpProject
from app.preprocessor.node_coalescer import NodeMap, coalesce_nodes


# ---------------------------------------------------------------------------
# TopologyChain
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TopologyChain:
    """
    Caminho de um BUS até uma fonte ultimate, passando por N
    transformadores intermediários.

    Attributes
    ----------
    target_bus_id:
        BUS alvo da análise.
    source_component:
        Componente fonte (Vac, SM).
    intermediate_transformers:
        Tupla de transformadores entre BUS e fonte. Ordem: do
        mais próximo do bus para o mais próximo da fonte.
    intermediate_buses:
        Tupla de outros BUSes intermediários no caminho.
    n_hops:
        Número de hops (componentes atravessados). 1 = vizinho
        direto, 2 = via 1 TR, 3 = via 2 TRs, etc.
    """

    target_bus_id: str
    source_component: PpComponent
    intermediate_transformers: tuple[PpComponent, ...]
    intermediate_buses: tuple[PpComponent, ...]
    n_hops: int

    def describe(self) -> str:
        """String legível mostrando o caminho."""
        parts = [self.source_component.name]
        for tr in reversed(self.intermediate_transformers):
            parts.append(f"[{tr.type} {tr.name}]")
        for bus in reversed(self.intermediate_buses):
            parts.append(f"[BUS {bus.name}]")
        parts.append(self.target_bus_id)
        return " ──> ".join(parts)


# ---------------------------------------------------------------------------
# Topology types
# ---------------------------------------------------------------------------


# Tipos "transparentes" — atravessamos durante BFS.
TRANSPARENT_TYPES: frozenset[str] = frozenset({
    "Tr", "sTr", "Tr3", "BCTRAN", "XFMR",
})


def is_transformer(comp: PpComponent) -> bool:
    """True se o componente é um transformador (transparente no walk)."""
    return comp.type in TRANSPARENT_TYPES


def is_bus(comp: PpComponent) -> bool:
    return comp.type == "BUS"


def is_ultimate_source(comp: PpComponent) -> bool:
    """
    True se é uma fonte ultimate — para o BFS, motores também
    são "fontes" (contribuem com SC mas não têm upstream a
    explorar).

    v0.27.7.9: motor adicionado às fontes ultimate.
    """
    cls = classify_sc_source(comp)
    return cls in (
        "voltage_source_ac", "synchronous_machine", "motor",
    )


# ---------------------------------------------------------------------------
# Helpers para coletar nós de um componente
# ---------------------------------------------------------------------------


def _component_nodes(
    comp: PpComponent, node_map: NodeMap,
) -> set[str]:
    """Retorna o conjunto de nós onde o componente está conectado."""
    nodes: set[str] = set()
    for (cname, _pin_idx), node in node_map.pin_to_node.items():
        if cname == comp.name:
            nodes.add(node)
    return nodes


def _components_at_node(
    project: PpProject, node: str, node_map: NodeMap,
) -> list[PpComponent]:
    """Retorna todos os componentes conectados a um nó."""
    pin_list = node_map.node_to_pins.get(node, [])
    names = {comp_name for (comp_name, _pin_idx) in pin_list}
    return [c for c in project.components if c.name in names]


def _other_side_nodes(
    transformer: PpComponent,
    entry_nodes: set[str],
    node_map: NodeMap,
) -> set[str]:
    """
    Dado que entramos no TR via ``entry_nodes``, retorna o
    conjunto de nós do "outro lado".

    Heurística: todos os nós do TR exceto os de entrada.
    """
    all_nodes = _component_nodes(transformer, node_map)
    return all_nodes - entry_nodes


# ---------------------------------------------------------------------------
# BFS para descobrir cadeias
# ---------------------------------------------------------------------------


def find_source_chains(
    project: PpProject,
    bus_id: str,
    max_hops: int = 4,
    *,
    warnings: list[str] | None = None,
) -> list[TopologyChain]:
    """
    Walking BFS desde o BUS alvo até fontes ultimate
    (Vac, SM), atravessando transformadores e barramentos
    intermediários.

    Algoritmo:

    1. Localiza o BUS alvo.
    2. Inicia BFS na fronteira = nós do bus.
    3. Para cada componente ``c`` na fronteira:
       - Se ``c`` é fonte ultimate: registra TopologyChain.
       - Se ``c`` é transformer: atravessa para o outro lado;
         adiciona o "outro lado" à fronteira de próxima rodada.
       - Se ``c`` é outro BUS: adiciona seus outros nós à
         fronteira.
       - Caso contrário: ignora (passive).

    Limita profundidade a ``max_hops`` para evitar explosão em
    topologias com muitos componentes.

    Returns
    -------
    list[TopologyChain]
        Cadeias ordenadas por n_hops (mais curtas primeiro).
    """
    bus_comp = find_bus_component(project, bus_id)
    if bus_comp is None:
        raise ValueError(f"BUS {bus_id!r} não encontrado.")

    node_map = coalesce_nodes(project)
    bus_nodes = _component_nodes(bus_comp, node_map)
    if not bus_nodes:
        return []

    # Estado da BFS:
    # frontier: lista de tuplas (current_nodes, intermediate_TRs,
    #           intermediate_BUSes, hops_consumed, visited_components)
    chains: list[TopologyChain] = []
    visited_global: set[str] = {bus_comp.name}

    # v0.28.0-PRO P2.11: detecção de loops topológicos.
    # Mantém um set de "fingerprints" de chains encontradas
    # (set de nomes de componentes percorridos). Se uma nova
    # chain produz o mesmo set (mesmas fontes via paths
    # diferentes), reporta loop e evita duplicação.
    chain_fingerprints: set[frozenset[str]] = set()

    # Inicial: começamos pelos nós do BUS, com 0 hops consumidos
    initial = (
        frozenset(bus_nodes),
        (),                # transformers visitados
        (),                # buses visitados
        0,                 # hops
        frozenset({bus_comp.name}),  # comps visitados nesta path
    )
    queue: list = [initial]

    while queue:
        next_queue = []
        for (curr_nodes, trs, buses, hops, visited) in queue:
            if hops >= max_hops:
                continue
            # Para cada nó na fronteira, descobre componentes vizinhos
            for node in curr_nodes:
                comps_here = _components_at_node(
                    project, node, node_map,
                )
                for comp in comps_here:
                    if comp.name in visited:
                        continue

                    # Caso 1: fonte ultimate → registra chain
                    if is_ultimate_source(comp):
                        # v0.28.0-PRO P2.11: detecta loop
                        # (mesma fonte via path alternativa).
                        fp = frozenset(
                            {comp.name}
                            | {t.name for t in trs}
                            | {b.name for b in buses}
                        )
                        if fp in chain_fingerprints:
                            # Loop detectado — emite warning e
                            # NÃO duplica chain.
                            if warnings is not None:
                                warnings.append(
                                    f"Loop topológico detectado: "
                                    f"fonte {comp.name!r} alcançável "
                                    "por múltiplos caminhos. "
                                    "Apenas o caminho mais curto foi "
                                    "considerado para evitar dupla "
                                    "contagem."
                                )
                            continue
                        chain_fingerprints.add(fp)
                        chains.append(TopologyChain(
                            target_bus_id=bus_id,
                            source_component=comp,
                            intermediate_transformers=trs,
                            intermediate_buses=buses,
                            n_hops=hops + 1,
                        ))
                        continue

                    # Caso 2: transformador — atravessa para o
                    # outro lado
                    if is_transformer(comp):
                        # Nós de entrada do TR: os que estão na
                        # interseção com curr_nodes.
                        entry_nodes = _component_nodes(comp, node_map) & curr_nodes
                        other_side = _other_side_nodes(
                            comp, entry_nodes, node_map,
                        )
                        if not other_side:
                            continue
                        new_visited = visited | {comp.name}
                        new_trs = trs + (comp,)
                        next_queue.append((
                            frozenset(other_side),
                            new_trs,
                            buses,
                            hops + 1,
                            new_visited,
                        ))
                        continue

                    # Caso 3: outro BUS — adiciona seus nós
                    if is_bus(comp):
                        other_bus_nodes = _component_nodes(
                            comp, node_map,
                        )
                        new_visited = visited | {comp.name}
                        new_buses = buses + (comp,)
                        next_queue.append((
                            frozenset(other_bus_nodes),
                            trs,
                            new_buses,
                            hops + 1,
                            new_visited,
                        ))
                        continue

                    # Caso 4: outros tipos — não atravessam
                    pass
        queue = next_queue

    # Ordena por n_hops crescente
    chains.sort(key=lambda c: c.n_hops)
    return chains


# ---------------------------------------------------------------------------
# Construção da impedância da cadeia
# ---------------------------------------------------------------------------


def chain_to_sc_source(
    chain: TopologyChain,
    target_voltage_kV: float,
    config=None,
):
    """
    Converte uma TopologyChain em ``ScSource`` com impedância
    refletida ao bus alvo.

    Estratégia:

    * Fonte Vac (rede): Z_Q = c·V²/S_kQ no nível da fonte.
    * Fonte SM: Z = (Ra + jXd'') · Z_base no nível da máquina.
    * Para cada TR no chain: adiciona Z_TR = uk%·V²/S no nível
      do enrolamento do bus.

    Reflexão ao bus alvo:

    * Identifica o nível de tensão de cada estágio percorrido.
    * Multiplica Z em níveis superiores por ratio² descendente.

    MVP v0.27.7.7: assume cadeia ordenada do bus para a fonte;
    cada TR no chain reduz a impedância pela razão². Defaults:
    S_kQ = 500 MVA, uk = 10%, R/X = 0.10.

    Returns
    -------
    ScSource
        Pronta para inserir em ``ShortCircuitNetwork``.
    """
    from app.postprocessor.bus_pipeline import BusPipelineConfig
    from app.postprocessor.short_circuit import ScSource
    from app.standards.iec60909 import (
        network_feeder_impedance_ohm,
        synchronous_machine_impedance_ohm,
        transformer_impedance_ohm,
    )

    if config is None:
        config = BusPipelineConfig()

    src = chain.source_component

    # Estimativa da tensão da fonte: usa a primeira propriedade
    # da fonte se tiver, senão a tensão do bus.
    def _pf(comp, idx, default):
        raw = (comp.get(idx, "") or "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            # Tenta extrair número do início (ex: "13.8 kV")
            import re
            m = re.match(r"[+-]?\d+\.?\d*", raw)
            if m:
                try:
                    return float(m.group())
                except ValueError:
                    pass
            return default

    # Z_source no nível da fonte
    if classify_sc_source(src) == "voltage_source_ac":
        # Vac — assume rede atrás com S_kQ default
        V_source = _pf(src, 0, target_voltage_kV)
        # v0.27.11.1: usa resolve_voltage_factor_c() para
        # suportar auto-classificação por nível de tensão.
        c_factor = config.resolve_voltage_factor_c(V_source)
        z_source_at_source = network_feeder_impedance_ohm(
            rated_voltage_kV=V_source,
            short_circuit_power_MVA=config.default_utility_S_kQ_MVA,
            voltage_factor_c=c_factor,
            r_over_x=config.default_utility_r_over_x,
        )
    elif classify_sc_source(src) == "motor":
        # v0.27.7.9 — Motor IM/MS (NBR 17227 §4.2.2)
        from app.preprocessor.motor import (
            MotorParameters, MotorType,
            subtransient_impedance_ohm,
        )
        # Reconstrói MotorParameters do componente
        motor_type_str = (src.get(0, "") or "induction").strip().lower()
        try:
            m_type = MotorType(motor_type_str)
        except ValueError:
            m_type = MotorType.INDUCTION
        motor_p = MotorParameters(
            name=src.name[:6],
            node_a="A", node_b="B", node_c="C",
            motor_type=m_type,
            rated_voltage_kV=_pf(src, 1, target_voltage_kV),
            rated_power_kW=_pf(src, 2, 100.0),
            rated_pf=_pf(src, 3, 0.85),
            efficiency=_pf(src, 4, 0.95),
            locked_rotor_current_pu=_pf(src, 5, 6.0),
            starting_pf=_pf(src, 6, 0.30),
            n_poles=int(_pf(src, 7, 4)),
            Td_pp_ms=_pf(src, 8, 20.0),
        )
        V_source = motor_p.rated_voltage_kV
        z_source_at_source = subtransient_impedance_ohm(motor_p)

    elif classify_sc_source(src) == "synchronous_machine":
        # SM — Xd'' do modelo (props 0 = V, 1 = S, 6 = Xd_pp)
        V_source = _pf(src, 0, target_voltage_kV)
        S_source = _pf(src, 1, 100.0)
        Xd_pp = _pf(src, 6, 0.20)
        Ra = _pf(src, 14, 0.003)
        z_source_at_source = synchronous_machine_impedance_ohm(
            rated_voltage_kV=V_source,
            rated_power_MVA=S_source,
            Xd_pp_pu=Xd_pp,
            Ra_pu=Ra,
        )
    else:
        # Não suportado — retorna fonte com Z muito alta para
        # efetivamente desconsiderar.
        return ScSource(
            name=src.name[:6],
            z_ohm=complex(1e9, 1e9),
            description=f"{src.type} {src.name} (não suportado)",
        )

    # Refletir Z_source ao bus alvo, atravessando cada TR.
    # Para cada TR: razão de transformação = V_bus / V_TR_lado_fonte.
    # Aproximação: assume que a tensão "do lado da fonte" do TR
    # é V_HV (prop 0 do XFMR ou Tr3) e "do lado do bus" é V_LV
    # (prop 1).
    z_total = z_source_at_source
    current_voltage = V_source

    # Cadeia: [TR_mais_próximo_do_bus, ..., TR_mais_próximo_da_fonte]
    # Para refletir corretamente, atravessamos NA ORDEM REVERSA
    # (do TR mais próximo da fonte para o bus).
    for tr in reversed(chain.intermediate_transformers):
        # Tipos de TR: extraem V_HV, V_LV, S, uk de props
        V_HV = _pf(tr, 0, current_voltage)
        V_LV = _pf(tr, 1, target_voltage_kV)
        S_MVA = _pf(tr, 2, 25.0)
        uk_pct = (
            _pf(tr, 5, config.transformer_default_uk_pct)
            if tr.type == "XFMR"
            else config.transformer_default_uk_pct
        )

        # Decide qual lado do TR está em direção à fonte.
        # Heurística: se tensão atual ≈ V_HV, fonte está no HV.
        # Refletimos current_z (no lado da fonte) para V_LV.
        if abs(current_voltage - V_HV) < abs(current_voltage - V_LV):
            ratio_sq = (V_LV / V_HV) ** 2
            current_voltage = V_LV
        else:
            ratio_sq = (V_HV / V_LV) ** 2
            current_voltage = V_HV

        z_total = z_total * ratio_sq

        # Soma a impedância do próprio TR (no lado V_LV ou V_HV
        # — usamos o lado em direção ao bus)
        z_tr = transformer_impedance_ohm(
            rated_voltage_kV=current_voltage,
            rated_power_MVA=S_MVA,
            uk_percent=uk_pct,
            uR_percent=config.transformer_default_uR_pct,
        )
        z_total = z_total + z_tr

    # Atravessa BUSes intermediários: zero impedância (BUS é nó
    # ideal). Apenas trocamos o "current_voltage" para o do bus.
    # Na prática, a tensão deve já estar correta no nível V_LV
    # do último TR.

    return ScSource(
        name=src.name[:6],
        z_ohm=z_total,
        description=(
            f"Chain ({chain.n_hops}h): {chain.describe()}"
        ),
    )


# ---------------------------------------------------------------------------
# Build SC network multi-hop
# ---------------------------------------------------------------------------


def build_sc_network_multi_hop(
    project: PpProject,
    bus_id: str,
    max_hops: int = 4,
    config=None,
):
    """
    Versão multi-hop do build_sc_network — usa BFS através de
    transformadores e barramentos para encontrar fontes
    ultimate.

    Returns
    -------
    tuple[ShortCircuitNetwork, list[TopologyChain], list[str]]
        Network pronta + cadeias descobertas + warnings.
    """
    from app.postprocessor.bus_pipeline import BusPipelineConfig
    from app.postprocessor.short_circuit import ShortCircuitNetwork

    if config is None:
        config = BusPipelineConfig()

    bus_comp = find_bus_component(project, bus_id)
    if bus_comp is None:
        raise ValueError(f"BUS {bus_id!r} não encontrado.")

    # V_LL do bus alvo (prop 1)
    try:
        V_bus = float(bus_comp.get(1, "13.8"))
    except (TypeError, ValueError):
        V_bus = 13.8

    warnings: list[str] = []
    # v0.28.0-PRO P2.11: propaga warnings (loops detectados)
    chains = find_source_chains(
        project, bus_id, max_hops=max_hops, warnings=warnings,
    )

    if not chains:
        warnings.append(
            f"BUS {bus_id!r}: nenhuma fonte SC encontrada em "
            f"até {max_hops} hops. Verifique conexões."
        )

    net = ShortCircuitNetwork(rated_voltage_kV=V_bus)
    for chain in chains:
        sc_source = chain_to_sc_source(
            chain, target_voltage_kV=V_bus, config=config,
        )
        net.sources.append(sc_source)

    return net, chains, warnings
