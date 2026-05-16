"""
app.postprocessor.bus_pipeline — pipeline end-to-end para
análise de barramentos (BUS): topology walking → SC IEC 60909
→ Arc-flash NBR 17227 → relatório consolidado.

Workflow
========

Em vez do usuário ter que coletar manualmente fontes e
construir uma ``ShortCircuitNetwork``, este módulo walking
automaticamente o ``PpProject`` para identificar tudo que
contribui para a falta no barramento de interesse:

::

    from app.preprocessor.models import PpProject
    from app.postprocessor.bus_pipeline import (
        analyze_bus_full_pipeline,
    )

    project = parse_sch_file("plant.sch")
    report = analyze_bus_full_pipeline(
        project,
        bus_id="BUS-MAIN-13.8",
        coordination_clearing_time_ms=500.0,
    )
    print(report.summary())
    # Output:
    # === BUS-MAIN-13.8 — Pipeline Analysis ===
    # SC analysis: Ik'' = 23.5 kA (κ=1.94, ip=64 kA)
    # Sources: GEN1 (69%), UTIL+TR (31%)
    # Arc-flash: E=21 cal/cm², Cat 3, DLA=4.8m
    # AFD: disabled

Classificação de fontes SC
===========================

O walking inspeciona cada componente vizinho do BUS e
classifica:

* ``voltage_source_ac`` (Vac, Vrect): fonte ideal — usa S_kQ
  default ou specificada na prop.
* ``voltage_source_dc`` (Vdc): em regime AC, geralmente não
  contribui — ignora com warning.
* ``synchronous_machine`` (SM): contribuição via Xd''
  (subtransient).
* ``transformer_feeder`` (Tr/sTr/Tr3/BCTRAN/XFMR): refletido
  via uk%; assumimos a outra ponta conectada a uma rede com
  S_kQ default.
* ``passive`` (R, L, C, GND, BUS, PROBE): não contribui.
* ``unknown``: warning + ignora.

Limitações MVP v0.27.7.5
=========================

* Walking simples — apenas vizinhos diretos do BUS (1-hop).
  Para topologias multi-bus, usar várias chamadas + soma manual.
* S_kQ default = 500 MVA quando não inferível de upstream.
* Não trata loops (ex: 2 alimentadores paralelos com mesma
  tensão precisam de S_kQ explícito).
* Não classifica motors como contribuintes (apenas geradores
  síncronos via SM). NBR 17227 §4.2.2 alerta sobre motores
  contribuírem por 3-8 ciclos — refinamento em v0.27.7.6.

Referências
============

* NBR 17227:2025 §5.1.4 (estudo SC IEC 60909/IEEE 3002.3)
* NBR 17227:2025 §4.2.4 (locais com mais de uma fonte)
* IEEE 242:2001 (Buff Book) — coordenação multi-fonte
* SKM PowerTools Workstation — Topology auto-build
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from app.preprocessor.bus import (
    BusComponent, bus_to_arc_flash_case,
    effective_clearing_time_ms,
)
from app.preprocessor.models import PpComponent, PpProject
from app.preprocessor.node_coalescer import NodeMap, coalesce_nodes


# ---------------------------------------------------------------------------
# Classificação de fontes
# ---------------------------------------------------------------------------


# Tipos que contribuem para SC (NBR 17227 §4.2 / IEC 60909-0).
SC_SOURCE_TYPES: dict[str, str] = {
    "Vac":   "voltage_source_ac",
    "Vrect": "voltage_source_ac",
    "Vsurge": "voltage_source_ac",
    "SM":    "synchronous_machine",
    "MOTOR": "motor",                # v0.27.7.9 — IM/MS contribuição SC
    "Tr":    "transformer_feeder",
    "sTr":   "transformer_feeder",
    "Tr3":   "transformer_feeder",
    "XFMR":  "transformer_feeder",
}

# Tipos passivos (não contribuem).
PASSIVE_TYPES: frozenset[str] = frozenset({
    "R", "L", "C", "GND", "BUS",
    "VProbe", "IProbe",
    "TLIN", "BERG", "JMARTI",
    "ZnO", "RNL", "LNL",
    # TACS-family não contribuem eletricamente
    "TACS", "PID", "Integrator", "LowPass", "Limiter", "TSum",
    "MODEL", "SwTACS",
    # Switches: contribuem via continuidade, mas não como fonte
    "SwIdeal", "Relais", "VCB", "VCB3", "Diode", "Thyr",
    "IGBT", "MOSFET", "GTO",
    # Diretivas (não-físicas)
    "Eqn", ".TR", ".DC", ".AC", ".SW", ".SP",
})


def classify_sc_source(comp: PpComponent) -> str:
    """
    Classifica o tipo de contribuição SC de um componente.

    Returns
    -------
    str
        Uma das categorias:
        * ``"voltage_source_ac"``: Vac, Vrect — assume rede
          atrás com S_kQ default.
        * ``"voltage_source_dc"``: Vdc — não contribui em AC.
        * ``"synchronous_machine"``: SM — via Xd''.
        * ``"transformer_feeder"``: Tr/Tr3/XFMR — feeder via
          impedância do TR.
        * ``"passive"``: passivo, não contribui.
        * ``"load"``: cargas (M, IM) — em MVP, ignoradas.
        * ``"unknown"``: tipo não reconhecido.
    """
    t = comp.type
    if t in SC_SOURCE_TYPES:
        return SC_SOURCE_TYPES[t]
    if t in PASSIVE_TYPES:
        return "passive"
    if t in ("Vdc", "Idc"):
        return "voltage_source_dc"
    if t in ("Iac",):
        # Fonte de corrente AC — não usual em estudo de SC
        return "current_source_ac"
    return "unknown"


# ---------------------------------------------------------------------------
# Topology walking
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BusNeighbor:
    """
    Componente vizinho de um BUS, descoberto via topology walk.

    Attributes
    ----------
    component:
        O ``PpComponent`` vizinho.
    sc_class:
        Classificação retornada por ``classify_sc_source``.
    shared_nodes:
        Tupla de nós compartilhados com o bus (1 para 1φ, até 3
        para 3φ).
    """
    component: PpComponent
    sc_class: str
    shared_nodes: tuple[str, ...]


# v0.28.0-PRO P1.2: helper para truncamento seguro de nomes
# com warning estruturado quando truncamento ocorre.
def _safe_short_name(
    name: str | None,
    max_len: int = 6,
    *,
    warnings: list[str] | None = None,
) -> str:
    """
    Trunca ``name`` para ``max_len`` caracteres, emitindo um
    warning estruturado se truncamento ocorrer.

    Estratégia anti-colisão:

    * Se ``name`` ≤ max_len → retorna direto.
    * Se ``name`` > max_len → trunca e adiciona aviso na
      lista de warnings (rastreabilidade).

    Esta função substitui ``comp.name[:max_len]`` em vários
    pontos do bus_pipeline para garantir que o usuário
    saiba que o ID auditável foi shortcutted.
    """
    if name is None:
        return ""[:max_len]
    name = str(name)
    if len(name) <= max_len:
        return name
    truncated = name[:max_len]
    if warnings is not None:
        warnings.append(
            f"Nome de componente {name!r} truncado para "
            f"{truncated!r} (max {max_len} chars). Possível "
            "colisão de nomes — verifique se há outros "
            "componentes com mesmo prefixo no relatório."
        )
    return truncated


def find_bus_component(
    project: PpProject, bus_id: str,
) -> Optional[PpComponent]:
    """
    Localiza um componente BUS no projeto pelo ``bus_id`` (que é
    a propriedade 0 — primeiro slot) ou pelo ``name`` (fallback).
    """
    for comp in project.components:
        if comp.type != "BUS":
            continue
        # bus_id é a primeira propriedade
        bus_id_prop = (comp.get(0, "") or "").strip()
        if bus_id_prop == bus_id or comp.name == bus_id:
            return comp
    return None


def find_neighbors_of_bus(
    project: PpProject,
    bus_id: str,
    node_map: Optional[NodeMap] = None,
) -> list[BusNeighbor]:
    """
    Walking 1-hop: encontra todos os componentes que compartilham
    pelo menos um nó com o BUS de ``bus_id``.

    Parameters
    ----------
    project:
        Projeto Qucs-style.
    bus_id:
        ID do barramento (prop 0 do componente BUS).
    node_map:
        Resultado de ``coalesce_nodes`` (opcional — recalcula se
        None).

    Returns
    -------
    list[BusNeighbor]
        Lista de vizinhos com classificação SC.

    Raises
    ------
    ValueError
        Se o BUS não for encontrado.
    """
    bus_comp = find_bus_component(project, bus_id)
    if bus_comp is None:
        raise ValueError(f"BUS {bus_id!r} não encontrado no projeto.")

    if node_map is None:
        node_map = coalesce_nodes(project)

    # Coleta todos os nós do BUS
    bus_nodes: set[str] = set()
    for (comp_name, pin_idx), node in node_map.pin_to_node.items():
        if comp_name == bus_comp.name:
            bus_nodes.add(node)

    # Para cada componente, vê quais pinos compartilham nós com o BUS
    neighbors: list[BusNeighbor] = []
    for comp in project.components:
        if comp.name == bus_comp.name:
            continue
        if comp.type == "BUS":
            # Outros barramentos: tratados como passive (zero-Z)
            # mas não são fontes de SC neles mesmos.
            continue
        comp_shared_nodes: set[str] = set()
        for (cname, pin_idx), node in node_map.pin_to_node.items():
            if cname == comp.name and node in bus_nodes:
                comp_shared_nodes.add(node)
        if comp_shared_nodes:
            sc_class = classify_sc_source(comp)
            neighbors.append(BusNeighbor(
                component=comp,
                sc_class=sc_class,
                shared_nodes=tuple(sorted(comp_shared_nodes)),
            ))
    return neighbors


# ---------------------------------------------------------------------------
# Auto-coleta de fontes para ShortCircuitNetwork
# ---------------------------------------------------------------------------


@dataclass
class BusPipelineConfig:
    """
    Parâmetros default usados pelo pipeline para inferir dados
    quando o componente não os tem explicitamente.

    Modos de cálculo do c-factor (IEC 60909-0 §4.2.2 Table 1)
    =========================================================

    O pipeline suporta DOIS modos de operação complementares:

    1. **Standalone IEC 60909 (estilo SKM PTW)** — ``pre_fault_
       voltage_pu`` omitido em ``analyze_bus_full_pipeline``.
       Usa o c-factor da Table 1 (auto-classificado por
       ``rated_voltage_kV`` ou explícito via ``voltage_factor_c``).
       Modo recomendado quando NÃO há estudo de fluxo de potência
       disponível. Replica o workflow padrão de ferramentas como
       SKM PTW e ETAP.

       Ajuste ``calculation_kind`` para escolher:
        * ``"max"`` (default) — máxima Ik'' para
          dimensionamento de equipamentos
          (c_max=1.05/1.10/1.10/1.10).
        * ``"min"`` — mínima Ik'' para estudo de
          sensibilidade de proteção (c_min=0.95/0.95/1.00/1.00).

    2. **PF-driven** — ``pre_fault_voltage_pu`` fornecido
       (típico vindo de ``app.postprocessor.power_flow``).
       Reescala Ik'' por V_real/c, usando a tensão real
       pré-falta. Mais preciso para coordenação seletiva
       com pouca margem ou arc-flash NBR 17227.

    Attributes
    ----------
    default_utility_S_kQ_MVA:
        S_kQ'' default para fontes Vac sem feeder explícito
        (concessionária forte = 2000 MVA, fraca = 200 MVA).
    default_utility_r_over_x:
        R/X da rede default.
    voltage_factor_c:
        c da IEC 60909-0 explícito. Se None (default),
        é auto-classificado por ``rated_voltage_kV`` via
        ``app.standards.iec60909.classify_voltage`` +
        ``calculation_kind``.
    calculation_kind:
        ``"max"`` (default) ou ``"min"`` — escolhe c_max ou
        c_min da Table 1.
    transformer_default_uk_pct:
        uk% default se o TR não declarar.
    transformer_default_uR_pct:
        uR% default se o TR não declarar.

    Examples
    --------
    SC standalone máximo (default, equipamentos):

    >>> config = BusPipelineConfig()
    >>> # Para 13.8 kV (MV) → c=1.10 auto

    SC standalone mínimo (sensibilidade de proteção):

    >>> config = BusPipelineConfig(calculation_kind="min")
    >>> # Para 13.8 kV (MV) → c=1.00 auto

    SC com c manual (override explícito):

    >>> config = BusPipelineConfig(voltage_factor_c=1.05)
    """
    default_utility_S_kQ_MVA: float = 500.0
    default_utility_r_over_x: float = 0.10
    voltage_factor_c: Optional[float] = None
    calculation_kind: str = "max"
    transformer_default_uk_pct: float = 10.0
    transformer_default_uR_pct: float = 0.5

    # v0.29.0: integração 0/1/2 + μ·q + Method C
    # Faltas assimétricas (IEC 60909-0 §4.3.2-4.3.4)
    compute_asymmetric_faults: bool = False
    grounding_type: str = "solid"   # solid/resistance/impedance/ungrounded/resonant
    grounding_R_N_ohm: float = 0.0  # se resistance grounding

    # Decay near-to-generator (IEC 60909-0 §4.5/4.6)
    apply_near_to_generator_decay: bool = False
    minimum_clearing_time_s: float = 0.05    # t_min do disjuntor

    # κ Method (A/B/C — IEC 60909-0 §4.3.1.2)
    kappa_method: str = "B"      # "A"/"B"/"C"
    is_meshed_topology: bool = False   # True → recomenda Method C
    fc_Hz: float = 20.0          # frequência reduzida para Method C

    def resolve_voltage_factor_c(
        self, rated_voltage_kV: float,
    ) -> float:
        """
        Resolve o c-factor efetivo a ser usado.

        Se ``voltage_factor_c`` foi explicitamente fornecido,
        usa esse valor. Caso contrário, auto-classifica
        conforme IEC 60909-0 Table 1 com base em
        ``rated_voltage_kV`` e ``calculation_kind``.

        Returns
        -------
        float
            c-factor a usar no cálculo SC.
        """
        if self.voltage_factor_c is not None:
            return self.voltage_factor_c
        from app.standards.iec60909 import (
            classify_voltage, voltage_factor_c as _c,
        )
        level = classify_voltage(rated_voltage_kV)
        return _c(level, kind=self.calculation_kind)


def build_sc_network_from_bus(
    project: PpProject,
    bus_id: str,
    config: Optional[BusPipelineConfig] = None,
):
    """
    Walking + auto-build de ``ShortCircuitNetwork`` no bus
    indicado.

    Estratégia (MVP v0.27.7.5):

    1. Localiza o BUS e seus vizinhos 1-hop.
    2. Para cada vizinho:
       - **Vac/Vrect**: adiciona ``add_network_feeder`` com S_kQ
         default.
       - **SM**: extrai parâmetros do componente, adiciona via
         ``add_synchronous_machine_from_sm``.
       - **Tr/sTr/Tr3/XFMR**: combina rede default ATRÁS do TR
         (refletida ao secundário) e adiciona como source custom.
       - **Outros**: warning, skip.
    3. Retorna a network pronta para ``calculate_at_bus``.

    Parameters
    ----------
    project:
        PpProject.
    bus_id:
        ID do barramento.
    config:
        Override dos defaults (S_kQ, R/X, uk%, etc.).

    Returns
    -------
    tuple[ShortCircuitNetwork, list[str]]
        A network pronta + lista de warnings emitidos.
    """
    from app.postprocessor.short_circuit import ShortCircuitNetwork
    from app.standards.iec60909 import (
        network_feeder_impedance_ohm, transformer_impedance_ohm,
    )

    if config is None:
        config = BusPipelineConfig()

    bus_comp = find_bus_component(project, bus_id)
    if bus_comp is None:
        raise ValueError(f"BUS {bus_id!r} não encontrado no projeto.")

    # Voltagem do BUS — propriedade 1 (V_LL kV).
    try:
        V_bus = float(bus_comp.get(1, "13.8"))
    except (TypeError, ValueError):
        V_bus = 13.8

    # Resolve c-factor: se config.voltage_factor_c=None, auto-
    # classifica via IEC 60909-0 Table 1 (estilo SKM PTW).
    c_factor = config.resolve_voltage_factor_c(V_bus)

    net = ShortCircuitNetwork(rated_voltage_kV=V_bus)
    warnings: list[str] = []
    neighbors = find_neighbors_of_bus(project, bus_id)

    sc_count = 0
    for nb in neighbors:
        comp = nb.component
        cls = nb.sc_class

        if cls == "voltage_source_ac":
            # v0.28.0-PRO P1.1: warning crítico ao usar default S_kQ.
            # Não há propriedade explícita de S_kQ no Vac.ocomp;
            # se default usado, sinaliza para auditoria.
            if config.default_utility_S_kQ_MVA == 500.0:
                warnings.append(
                    f"BUS {bus_id!r}: Vac {comp.name!r} usando "
                    f"S_kQ default = 500 MVA. Para concessionária "
                    "real (>1500 MVA), Ik'' pode ser SUBESTIMADO. "
                    "Configure config.default_utility_S_kQ_MVA "
                    "com valor real da concessionária."
                )
            # v0.28.0-PRO P1.2: nome seguro (warning se truncado).
            short_name = _safe_short_name(
                comp.name, max_len=6, warnings=warnings,
            )
            net.add_network_feeder(
                name=short_name,
                S_kQ_MVA=config.default_utility_S_kQ_MVA,
                rated_voltage_kV=V_bus,
                voltage_factor=c_factor,
                r_over_x=config.default_utility_r_over_x,
            )
            sc_count += 1

        elif cls == "synchronous_machine":
            # Extrai parâmetros do SM via bridge helper.
            sm_params = _extract_sm_params(comp, V_bus, warnings)
            if sm_params is not None:
                net.add_synchronous_machine_from_sm(sm_params)
                sc_count += 1

        elif cls == "motor":
            # v0.27.7.9 — extrai contribuição do motor (IM/MS).
            motor_src = _extract_motor_source(comp, warnings)
            if motor_src is not None:
                net.sources.append(motor_src)
                sc_count += 1

        elif cls == "transformer_feeder":
            # Refletir rede atrás do TR.
            sc_source = _build_transformer_feeder_source(
                comp, V_bus, config, warnings,
            )
            if sc_source is not None:
                net.sources.append(sc_source)
                sc_count += 1

        elif cls == "voltage_source_dc":
            warnings.append(
                f"BUS {bus_id!r}: vizinho {comp.name!r} (Vdc/Idc) "
                "não contribui em SC AC — ignorado."
            )

        elif cls == "passive":
            pass   # silencioso

        else:
            warnings.append(
                f"BUS {bus_id!r}: vizinho {comp.name!r} tipo "
                f"{comp.type!r} ({cls}) — não classificado como "
                "fonte SC, ignorado."
            )

    if sc_count == 0:
        warnings.append(
            f"BUS {bus_id!r}: nenhuma fonte de SC encontrada — "
            "adicione Vac, SM ou TR conectado."
        )

    return net, warnings


def _extract_motor_source(comp: PpComponent, warnings: list[str]):
    """
    Extrai contribuição de SC do componente MOTOR.

    v0.27.7.9: lê parâmetros do MOTOR.ocomp e retorna ``ScSource``
    com Z''_M = (1/I_LR_rel) · V²/S, conforme IEC 60909-0 §6.5.
    """
    from app.preprocessor.motor import (
        MotorParameters, MotorType, motor_to_sc_source,
        validate_motor,
    )

    def _pf(idx: int, default: float) -> float:
        raw = (comp.get(idx, "") or "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    def _ps(idx: int, default: str) -> str:
        raw = (comp.get(idx, "") or "").strip()
        return raw or default

    name = _safe_short_name(
        comp.name or "MOTOR", max_len=6, warnings=warnings,
    )
    motor_type_str = _ps(0, "induction")
    try:
        m_type = MotorType(motor_type_str.lower())
    except ValueError:
        m_type = MotorType.INDUCTION

    motor = MotorParameters(
        name=name,
        node_a="A", node_b="B", node_c="C",  # placeholder
        motor_type=m_type,
        rated_voltage_kV=_pf(1, 0.480),
        rated_power_kW=_pf(2, 100.0),
        rated_pf=_pf(3, 0.85),
        efficiency=_pf(4, 0.95),
        locked_rotor_current_pu=_pf(5, 6.0),
        starting_pf=_pf(6, 0.30),
        n_poles=int(_pf(7, 4)),
        Td_pp_ms=_pf(8, 20.0),
    )
    errs = validate_motor(motor)
    if errs:
        warnings.append(
            f"MOTOR {comp.name!r}: validação falhou — "
            + "; ".join(errs)
        )
        return None
    return motor_to_sc_source(motor)


def _extract_sm_params(
    comp: PpComponent, V_bus: float, warnings: list[str],
):
    """Extrai SynchronousMachineParameters do componente SM."""
    from app.preprocessor.synchronous_machine import (
        SynchronousMachineParameters, validate_sm,
    )

    def _pf(idx: int, default: float) -> float:
        raw = (comp.get(idx, "") or "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    name = _safe_short_name(
        comp.name or "SM", max_len=6, warnings=warnings,
    )
    sm = SynchronousMachineParameters(
        name=name,
        node_a="A", node_b="B", node_c="C",   # placeholder
        rated_voltage_kV=_pf(0, V_bus),
        rated_power_MVA=_pf(1, 100.0),
        frequency_Hz=_pf(2, 60.0),
        n_poles=int(_pf(3, 2)),
        Xd=_pf(4, 1.8),
        Xd_prime=_pf(5, 0.30),
        Xd_pp=_pf(6, 0.20),
        Td_prime=_pf(7, 0.8),
        Td_pp=_pf(8, 0.030),
        Xq=_pf(9, 1.7),
        Xq_prime=_pf(10, 0.55),
        Xq_pp=_pf(11, 0.20),
        Tq_prime=_pf(12, 0.4),
        Tq_pp=_pf(13, 0.050),
        Ra=_pf(14, 0.003),
        xL=_pf(15, 0.15),
        X0=_pf(16, 0.05),
        H=_pf(17, 3.0),
        D=_pf(18, 0.0),
    )
    errs = validate_sm(sm)
    if errs:
        warnings.append(
            f"SM {comp.name!r}: validação falhou — "
            + "; ".join(errs)
        )
        return None
    return sm


def _build_transformer_feeder_source(
    comp: PpComponent, V_bus: float,
    config: BusPipelineConfig, warnings: list[str],
):
    """
    Constrói uma ``ScSource`` representando rede + TR refletida
    ao bus (para Tr/sTr/Tr3/XFMR).

    Aproxima usando uk% default e S_kQ default. Para precisão
    completa, o usuário deve construir a network manualmente.
    """
    from app.postprocessor.short_circuit import ScSource
    from app.standards.iec60909 import (
        network_feeder_impedance_ohm, transformer_impedance_ohm,
    )

    # Tenta extrair S e uk% do componente. Cada tipo de TR tem
    # layout próprio de propriedades; aqui usamos defaults
    # conservadores em MVP.
    def _pf(idx: int, default: float) -> float:
        raw = (comp.get(idx, "") or "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    if comp.type == "XFMR":
        # XFMR.ocomp: prop 0=V_HV, 1=V_LV, 2=S, 5=uk%, 6=p_load.
        V_HV = _pf(0, 138.0)
        V_LV = _pf(1, V_bus)
        S_MVA = _pf(2, 25.0)
        uk_pct = _pf(5, config.transformer_default_uk_pct)
    else:
        # Tr/sTr/Tr3 — assume S=25 MVA, uk=10% default.
        # Refinamento exige conhecimento do schema específico.
        V_HV = _pf(0, 138.0)
        V_LV = V_bus
        S_MVA = _pf(2, 25.0) if comp.type == "Tr3" else 25.0
        uk_pct = config.transformer_default_uk_pct

    # Resolve c-factor (idem build_sc_network_from_bus).
    c_factor = config.resolve_voltage_factor_c(V_HV)

    # Z da rede no primário
    z_net_pri = network_feeder_impedance_ohm(
        rated_voltage_kV=V_HV,
        short_circuit_power_MVA=config.default_utility_S_kQ_MVA,
        voltage_factor_c=c_factor,
        r_over_x=config.default_utility_r_over_x,
    )
    # Refletir ao secundário (lado do bus)
    ratio_sq = (V_LV / V_HV) ** 2
    z_net_sec = z_net_pri * ratio_sq
    # Z do trafo (já no lado do secundário)
    z_tr = transformer_impedance_ohm(
        rated_voltage_kV=V_LV,
        rated_power_MVA=S_MVA,
        uk_percent=uk_pct,
        uR_percent=config.transformer_default_uR_pct,
    )
    z_total = z_net_sec + z_tr

    # v0.28.0-PRO P1.1: warning se uk default (10%) usado vs schema
    if uk_pct == config.transformer_default_uk_pct:
        warnings.append(
            f"BUS lookup: TR {comp.name!r} usando uk default = "
            f"{uk_pct:.1f}%. TRs reais geralmente 4-8% — verifique "
            "specs do equipamento antes de laudo final."
        )

    # v0.28.0-PRO P1.2: nome seguro
    short_name = _safe_short_name(
        comp.name, max_len=6, warnings=warnings,
    )
    return ScSource(
        name=short_name,
        z_ohm=z_total,
        description=(
            f"{comp.type} {comp.name!r} ({V_HV:.1f}/{V_LV:.1f} kV, "
            f"S={S_MVA:.1f} MVA, uk={uk_pct:.1f}%) refletida ao bus"
        ),
    )


# ---------------------------------------------------------------------------
# Pipeline end-to-end
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BusPipelineReport:
    """
    Relatório consolidado da análise pipeline:
    walking → SC → arc-flash → relay suggestions.

    v0.27.7.6: agora inclui sugestões de ajustes para relés
    de proteção, baseadas em IEEE 242 §15 + manuais dos
    fabricantes.
    """

    bus_id: str
    rated_voltage_kV: float
    panel_type: str
    is_lineside: bool
    has_AFD: bool

    # Topology
    n_neighbors: int
    n_sc_sources: int
    sources_summary: tuple[str, ...]   # ex: ("GEN1: 69%", "UTIL: 31%")

    # SC results (subset relevante)
    Ik_pp_kA: float
    ip_kA: float
    kappa: float

    # Arc-flash results
    coordination_clearing_time_ms: float
    effective_clearing_time_ms: float
    incident_energy_cal_cm2: float
    arc_flash_boundary_mm: float
    ppe_category: str

    # Relay suggestions (v0.27.7.6) — pode ser tupla vazia
    relay_suggestions: tuple = ()

    # Topology chains (v0.27.7.8) — cadeias do walking multi-hop
    # (vazia quando use_multi_hop=False).
    topology_chains: tuple = ()

    # v0.29.0: faltas assimétricas (sequencial 0/1/2)
    # None quando compute_asymmetric_faults=False
    asymmetric_fault_result: object = None

    # v0.29.0: decay near-to-generator (μ·q)
    # None quando apply_near_to_generator_decay=False ou
    # far-from-generator
    decay_result: object = None
    Ib_kA: float = 0.0   # breaking current (after decay)
    Ik_steady_kA: float = 0.0   # steady-state current

    # v0.29.0: kappa method usado (A/B/C)
    kappa_method_used: str = "B"

    # Diagnostics
    warnings: tuple[str, ...] = ()

    def summary(self) -> str:
        """Texto plano resumido."""
        afd_str = (
            f"on (T={self.effective_clearing_time_ms:.0f} ms)"
            if self.has_AFD else "off"
        )
        side_str = "lineside" if self.is_lineside else "loadside"
        lines = [
            f"=== {self.bus_id} — Pipeline Analysis ===",
            f"Panel: {self.panel_type} @ {self.rated_voltage_kV:.2f} kV "
            f"({side_str}), AFD: {afd_str}",
            "",
            f"Topology: {self.n_neighbors} neighbors, "
            f"{self.n_sc_sources} SC sources",
            "  Contributions:",
        ]
        for s in self.sources_summary:
            lines.append(f"    {s}")
        lines.extend([
            "",
            "SC analysis (IEC 60909-0):",
            f"  Ik'' = {self.Ik_pp_kA:.3f} kA  "
            f"(κ={self.kappa:.3f}, ip={self.ip_kA:.3f} kA, "
            f"Method {self.kappa_method_used})",
        ])

        # v0.29.0: decay near-to-generator
        if self.decay_result is not None:
            lines.append(
                f"  Ib = {self.Ib_kA:.3f} kA "
                f"(μ={self.decay_result.mu:.3f}), "
                f"Ik = {self.Ik_steady_kA:.3f} kA "
                f"(μ·q={self.decay_result.mu * self.decay_result.q:.3f})"
            )
            if self.decay_result.is_near_to_generator:
                lines.append(
                    "  → near-to-generator decay aplicado "
                    "(IEC 60909-0 §4.5/4.6)"
                )

        # v0.29.0: faltas assimétricas
        if self.asymmetric_fault_result is not None:
            r = self.asymmetric_fault_result
            lines.extend([
                "",
                "Faltas assimétricas (IEC 60909-0 §4.3):",
                f"  Trifásica:    Ik''3   = {r.Ik3_kA:7.3f} kA",
                f"  Bifásica:     Ik''2   = {r.Ik2_kA:7.3f} kA",
                f"  Mono-terra:   Ik''1   = {r.Ik1_kA:7.3f} kA",
                f"  Bif-terra:    Ik''2EG = {r.Ik2EG_phase_kA:7.3f} kA",
                f"  Aterramento:  {r.grounding.value}",
                f"  Razão Ik1/Ik3 = {r.Ik1_to_Ik3_ratio:.3f}",
            ])

        lines.extend([
            "",
            "Arc-flash (NBR 17227 / IEEE 1584):",
            f"  T coord = {self.coordination_clearing_time_ms:.0f} ms",
            f"  T efetivo = {self.effective_clearing_time_ms:.0f} ms "
            f"({'AFD override' if self.has_AFD else 'sem AFD'})",
            f"  Energia = {self.incident_energy_cal_cm2:.3f} cal/cm²",
            f"  DLA = {self.arc_flash_boundary_mm:.0f} mm",
            f"  Categoria PPE: {self.ppe_category}",
        ])

        # v0.27.7.8: bloco de cadeias topológicas (multi-hop)
        if self.topology_chains:
            lines.append("")
            lines.append(
                "Topology Chains (multi-hop walking, IEC 60909-0 §6.3):"
            )
            for i, chain in enumerate(self.topology_chains, 1):
                lines.append(
                    f"  Chain #{i} ({chain.n_hops} hops): "
                    f"{chain.describe()}"
                )

        # v0.27.7.6: bloco de sugestões de relés
        if self.relay_suggestions:
            lines.append("")
            lines.append(
                "Relay Settings Suggestions (IEEE 242 §15):"
            )
            for sg in self.relay_suggestions:
                lines.append("")
                lines.append(sg.summary())

        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  • {w}")
        return "\n".join(lines)


def analyze_bus_full_pipeline(
    project: PpProject,
    bus_id: str,
    coordination_clearing_time_ms: float,
    config: Optional[BusPipelineConfig] = None,
    include_relay_suggestions: bool = True,
    multi_vendor_suggestions: bool = False,
    load_S_MVA: Optional[float] = None,
    use_multi_hop: bool = False,
    max_hops: int = 4,
    pre_fault_voltage_pu: Optional[float] = None,
) -> BusPipelineReport:
    """
    Análise end-to-end de um BUS:

    1. Walking topology (1-hop default; multi-hop opcional via
       ``use_multi_hop=True``).
    2. Auto-build ``ShortCircuitNetwork``.
    3. Calcula Ik'' / ip / Ib via IEC 60909-0.

       **Modo standalone (estilo SKM PTW / ETAP)** — sem PF:
       Usa o c-factor da IEC 60909-0 §4.2.2 Table 1, auto-
       classificado por ``rated_voltage_kV``. Selecione
       ``config.calculation_kind="max"`` (default, c=1.10
       MV/HV) para dimensionamento de equipamentos, ou
       ``"min"`` (c=1.00 MV/HV / 0.95 LV) para sensibilidade
       de proteção.

       **Modo PF-driven** — com PF disponível:
       Se ``pre_fault_voltage_pu`` fornecido (típico vindo de
       estudo de PF — ``app.postprocessor.power_flow``),
       reescala Ik'' por V_real/c. Mais preciso para arc-flash
       e coordenação seletiva apertada.

    4. Constrói ``ArcFlashCase`` com metadata do BUS.
    5. Calcula E / DLA / PPE via NBR 17227.
    6. Gera sugestões de ajuste de relé (IEEE 242 §15) — opcional.
    7. Gera relatório consolidado.

    Parameters
    ----------
    project:
        ``PpProject`` carregado de .sch.
    bus_id:
        ID do barramento (prop 0 do componente BUS).
    coordination_clearing_time_ms:
        Tempo de extinção da coordenação principal (vindo de
        ``app.postprocessor.relay_coordination``).
    config:
        Override dos defaults do pipeline (incluindo
        ``calculation_kind`` "max"/"min" e ``voltage_factor_c``
        explícito).
    include_relay_suggestions:
        Se True (default), gera bloco "Relay Settings Suggestions"
        com ajustes IEEE 242 §15.
    multi_vendor_suggestions:
        Se True, compara 3 fabricantes (SEL/ABB/Schneider) em vez
        de auto-selecionar 1.
    load_S_MVA:
        Carga base para cálculo de I_n. None → heurística Ik''/20.
    use_multi_hop:
        v0.27.7.8: Se True, usa BFS multi-hop através de
        transformadores e barramentos (encontra fontes em cadeia
        — útil para topologias industriais multi-nível). Se False
        (default), usa walking 1-hop tradicional.
    max_hops:
        Profundidade máxima do BFS multi-hop (default 4).
    pre_fault_voltage_pu:
        v0.27.11: Tensão pré-falta REAL (do estudo PF) em pu.
        Quando fornecido, ativa modo PF-driven (substitui
        c-factor por V_real/U_n). Quando None (default),
        modo standalone com c-factor IEC.

    Returns
    -------
    BusPipelineReport
    """
    from app.postprocessor.arc_flash import calculate_arc_flash

    if config is None:
        config = BusPipelineConfig()

    bus_comp = find_bus_component(project, bus_id)
    if bus_comp is None:
        raise ValueError(f"BUS {bus_id!r} não encontrado.")

    # Reconstrói o BusComponent a partir do PpComponent
    bus = _bus_from_pp_component(bus_comp)

    # 1+2: walking + SC network
    # v0.27.7.8: opção use_multi_hop=True para BFS através de
    # transformadores e barramentos (encontra fontes em cadeia).
    topology_chains: tuple = ()
    if use_multi_hop:
        from app.postprocessor.multihop_walker import (
            build_sc_network_multi_hop,
        )
        net, chains_list, walk_warnings = build_sc_network_multi_hop(
            project, bus_id, max_hops=max_hops, config=config,
        )
        topology_chains = tuple(chains_list)
    else:
        net, walk_warnings = build_sc_network_from_bus(
            project, bus_id, config,
        )

    # 3: SC analysis
    if not net.sources:
        raise ValueError(
            f"BUS {bus_id!r}: nenhuma fonte de SC encontrada. "
            "Conecte Vac/SM/Tr ao bus antes de analisar."
        )
    # Modo standalone: c-factor da Table 1 (kind=max ou min,
    # auto-classificado pela tensão se config.voltage_factor_c
    # for None).
    sc_result = net.calculate_at_bus(
        bus.bus_id, kind=config.calculation_kind,
    )

    # v0.27.11: aplica V_pre-fault do PF (se fornecido) — re-
    # escala Ik''. A IEC 60909-0 §3.8 considera c·U_n; quando
    # PF fornece V real, podemos usar V_real/U_n no lugar de c.
    if pre_fault_voltage_pu is not None and pre_fault_voltage_pu > 0:
        # Razão entre V_real e c·U_n usado na network.
        # Usamos resolve_voltage_factor_c() para suportar tanto
        # override explícito quanto auto-classificação.
        c_used = config.resolve_voltage_factor_c(bus.rated_voltage_kV)
        scale = pre_fault_voltage_pu / c_used
        # Reescala Ik'' (proporcional a V); ip e Ib seguem
        new_Ik = sc_result.Ik_pp_kA * scale
        new_ip = sc_result.ip_kA * scale
        new_Ib = sc_result.Ib_kA * scale
        new_Iss = sc_result.Ik_steady_kA * scale
        new_idc = sc_result.idc_at_50ms_kA * scale
        from app.standards.iec60909 import ShortCircuitResult
        sc_result = ShortCircuitResult(
            Ik_pp_kA=new_Ik,
            ip_kA=new_ip,
            idc_at_50ms_kA=new_idc,
            Ib_kA=new_Ib,
            Ik_steady_kA=new_Iss,
            z_thevenin_ohm=sc_result.z_thevenin_ohm,
            r_over_x=sc_result.r_over_x,
            kappa=sc_result.kappa,
            voltage_factor_c=pre_fault_voltage_pu,  # registra V_real
            rated_voltage_kV=sc_result.rated_voltage_kV,
            fault_distance=sc_result.fault_distance,
        )
        walk_warnings.append(
            f"V_pre-fault = {pre_fault_voltage_pu:.4f} pu "
            f"(do estudo PF) substituiu c={c_used:.2f} default."
        )

    # Sources summary (% por fonte)
    breakdown = net.contribution_breakdown()
    sources_summary = tuple(
        f"{name}: {frac*100:.1f}%" for name, frac in breakdown.items()
    )

    # ----------------------------------------------------------------
    # v0.29.0: integrações IEC 60909-0 §4.3.1.2 / §4.3.2-4.3.4 / §4.5/4.6
    # ----------------------------------------------------------------

    # κ via Method A/B/C (IEC 60909-0 §4.3.1.2).
    # Method A: usado por sc_result.calculate_at_bus (já default).
    # Method B: aplicar fator 1.15 sobre A + cap.
    # Method C: requer impedância em fc reduzida.
    kappa_method_used = config.kappa_method.upper()
    if kappa_method_used in ("B", "C"):
        from app.standards.iec60909_kappa import (
            kappa_method_B, kappa_method_C, kappa_recommended,
            KappaMethod,
        )
        from app.standards.iec60909 import ShortCircuitResult
        if kappa_method_used == "B":
            new_kappa = kappa_method_B(sc_result.r_over_x)
        else:  # Method C
            # Para Method C precisamos da impedância em fc.
            # Aproximação: assume R inalterado e X escalonado por
            # fc/fn (X = ωL).
            fc_over_fn = config.fc_Hz / 60.0  # assume 60 Hz
            z_at_fc = complex(
                sc_result.z_thevenin_ohm.real,
                sc_result.z_thevenin_ohm.imag * fc_over_fn,
            )
            new_kappa = kappa_method_C(
                z_at_fc,
                nominal_frequency_Hz=60.0,
                fc_Hz=config.fc_Hz,
            )
        # Recompõe sc_result com novo κ + ip
        new_ip = math.sqrt(2.0) * new_kappa * sc_result.Ik_pp_kA
        sc_result = ShortCircuitResult(
            Ik_pp_kA=sc_result.Ik_pp_kA,
            ip_kA=new_ip,
            idc_at_50ms_kA=sc_result.idc_at_50ms_kA,
            Ib_kA=sc_result.Ib_kA,
            Ik_steady_kA=sc_result.Ik_steady_kA,
            z_thevenin_ohm=sc_result.z_thevenin_ohm,
            r_over_x=sc_result.r_over_x,
            kappa=new_kappa,
            voltage_factor_c=sc_result.voltage_factor_c,
            rated_voltage_kV=sc_result.rated_voltage_kV,
            fault_distance=sc_result.fault_distance,
        )
        walk_warnings.append(
            f"κ Method {kappa_method_used} aplicado: "
            f"κ={new_kappa:.3f}, ip={new_ip:.3f} kA"
        )

    # Decay near-to-generator (μ·q) — IEC 60909-0 §4.5/4.6
    decay_result = None
    Ib_kA_final = sc_result.Ib_kA
    Ik_steady_kA_final = sc_result.Ik_steady_kA
    if config.apply_near_to_generator_decay:
        from app.standards.iec60909_decay import (
            apply_near_to_generator_decay,
        )
        # Estima I_rG a partir das fontes do tipo SM (somando
        # potências nominais e dividindo por √3·V).
        I_rG_kA = _estimate_rated_current_from_sources(net, bus.rated_voltage_kV)
        if I_rG_kA > 0:
            try:
                decay_result = apply_near_to_generator_decay(
                    Ik_pp_kA=sc_result.Ik_pp_kA,
                    IrG_kA=I_rG_kA,
                    minimum_clearing_time_s=config.minimum_clearing_time_s,
                )
                Ib_kA_final = decay_result.Ib_kA
                Ik_steady_kA_final = decay_result.Ik_steady_kA
                if decay_result.is_near_to_generator:
                    walk_warnings.append(
                        f"Decay near-to-gen aplicado: μ={decay_result.mu:.3f}, "
                        f"q={decay_result.q:.3f}, "
                        f"Ib={Ib_kA_final:.3f} kA, "
                        f"Ik={Ik_steady_kA_final:.3f} kA"
                    )
            except (ValueError, ZeroDivisionError):
                # Sem geradores ou inputs inválidos — pula
                decay_result = None

    # Faltas assimétricas (sequencial 0/1/2) — IEC 60909-0 §4.3.2-4.3.4
    asymmetric_fault_result = None
    if config.compute_asymmetric_faults:
        from app.standards.iec60909_seq import (
            calculate_all_faults, GroundingType,
            sequence_impedances_from_grounding,
        )
        try:
            grounding = GroundingType(config.grounding_type)
        except ValueError:
            grounding = GroundingType.SOLIDLY_GROUNDED
            walk_warnings.append(
                f"grounding_type {config.grounding_type!r} inválido, "
                "usando 'solid'."
            )
        seq = sequence_impedances_from_grounding(
            sc_result.z_thevenin_ohm,
            grounding,
            R_N_ohm=config.grounding_R_N_ohm,
        )
        c_used = config.resolve_voltage_factor_c(bus.rated_voltage_kV)
        asymmetric_fault_result = calculate_all_faults(
            Un_kV=bus.rated_voltage_kV,
            seq_impedances=seq,
            grounding=grounding,
            voltage_factor_c=c_used,
        )

    # 4+5: Arc-flash
    # v0.93.4: arc-flash NÃO é fatal — se a tensão estiver
    # fora do escopo IEEE 1584 (>15 kV) ou Ibf fora da faixa
    # (sistemas de alta-tensão / micro-faltas), pulamos arc-flash
    # mas SC e coordenação CONTINUAM. Geramos um warning e
    # retornamos campos arc-flash zerados.
    af_report = None
    try:
        af_case = bus_to_arc_flash_case(
            bus,
            bolted_fault_current_kA=sc_result.Ik_pp_kA,
            coordination_clearing_time_ms=coordination_clearing_time_ms,
        )
        af_report = calculate_arc_flash(af_case)
    except ValueError as exc:
        msg = str(exc)
        walk_warnings.append(
            f"Arc-flash pulado: {msg}"
        )
        from app.core.logging_config import get_logger
        get_logger(__name__).warning(
            "Arc-flash pulado para bus %s (V=%.2f kV): %s",
            bus.bus_id, bus.rated_voltage_kV, msg,
        )

    # Defaults arc-flash quando pulado (sistemas HV/EHV)
    if af_report is not None:
        af_incident_energy = af_report.incident_energy_cal_cm2
        af_boundary = af_report.arc_flash_boundary_mm
        af_ppe = af_report.ppe_category.value
    else:
        af_incident_energy = 0.0
        af_boundary = 0.0
        af_ppe = "N/A"

    # 6: Sugestões de relé (v0.27.7.6)
    relay_suggestions: tuple = ()
    if include_relay_suggestions:
        from app.postprocessor.relay_suggestions import (
            suggest_multi_relay_alternatives,
            suggest_settings_for_bus,
        )
        if multi_vendor_suggestions:
            relay_suggestions = tuple(
                suggest_multi_relay_alternatives(
                    bus, sc_result.Ik_pp_kA, load_S_MVA=load_S_MVA,
                )
            )
        else:
            relay_suggestions = (
                suggest_settings_for_bus(
                    bus, sc_result.Ik_pp_kA, load_S_MVA=load_S_MVA,
                ),
            )

    # 7: Relatório consolidado
    return BusPipelineReport(
        bus_id=bus.bus_id,
        rated_voltage_kV=bus.rated_voltage_kV,
        panel_type=bus.panel_type.value,
        is_lineside=bus.is_lineside,
        has_AFD=bus.has_AFD,
        n_neighbors=len(find_neighbors_of_bus(project, bus_id)),
        n_sc_sources=len(net.sources),
        sources_summary=sources_summary,
        Ik_pp_kA=sc_result.Ik_pp_kA,
        ip_kA=sc_result.ip_kA,
        kappa=sc_result.kappa,
        coordination_clearing_time_ms=coordination_clearing_time_ms,
        effective_clearing_time_ms=effective_clearing_time_ms(
            bus, coordination_clearing_time_ms,
        ),
        incident_energy_cal_cm2=af_incident_energy,
        arc_flash_boundary_mm=af_boundary,
        ppe_category=af_ppe,
        relay_suggestions=relay_suggestions,
        topology_chains=topology_chains,
        # v0.29.0: integrações sequencial + decay + Method
        asymmetric_fault_result=asymmetric_fault_result,
        decay_result=decay_result,
        Ib_kA=Ib_kA_final,
        Ik_steady_kA=Ik_steady_kA_final,
        kappa_method_used=kappa_method_used,
        warnings=tuple(walk_warnings),
    )


def _estimate_rated_current_from_sources(
    net, bus_rated_voltage_kV: float,
) -> float:
    """
    v0.29.0: estima I_rG total das fontes SM/MOTOR para uso em
    apply_near_to_generator_decay.

    Estratégia: para cada fonte com semantic_type "synchronous_machine"
    ou "motor", soma S_rated_MVA e calcula
    I_rG = S_total / (√3 · V_LL) em kA.

    Para fontes Vac/utility (sem rating natural), assume Ik''/2
    como estimativa conservadora (caller pode override).

    Returns
    -------
    float
        I_rG em kA.
    """
    total_S_MVA = 0.0
    for src in net.sources:
        # ScSource pode ter atributo opcional rated_power_MVA
        rated = getattr(src, "rated_power_MVA", None)
        if rated and rated > 0:
            total_S_MVA += rated
    if total_S_MVA <= 0 or bus_rated_voltage_kV <= 0:
        return 0.0
    # I_rG = S / (√3 · V) — em kA com V em kV e S em MVA
    return total_S_MVA / (math.sqrt(3.0) * bus_rated_voltage_kV)


def _bus_from_pp_component(comp: PpComponent) -> BusComponent:
    """
    Reconstrói ``BusComponent`` a partir do ``PpComponent``.
    Mesmo parsing usado em ``bridge_to_atp._convert_bus`` (mas
    sem warnings — usa defaults silenciosos).
    """
    from app.standards.nbr17227 import EquipmentClass

    def _pf(idx: int, default: float) -> float:
        raw = (comp.get(idx, "") or "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    def _ps(idx: int, default: str) -> str:
        raw = (comp.get(idx, "") or "").strip()
        return raw or default

    bus_id = _ps(0, comp.name or "BUS")
    voltage = _pf(1, 13.8)
    n_phases = int(_pf(2, 3))
    pt_str = _ps(3, "swgr_15kv")
    try:
        panel_type = EquipmentClass(pt_str)
    except ValueError:
        panel_type = EquipmentClass.SWITCHGEAR_15KV
    is_lineside = bool(_pf(4, 1.0))
    has_AFD = bool(_pf(5, 0.0))
    AFD_t = _pf(6, 10.0)
    n_taps = int(_pf(7, 4))
    desc = _ps(8, "")
    return BusComponent(
        bus_id=bus_id,
        rated_voltage_kV=voltage,
        n_phases=n_phases,
        panel_type=panel_type,
        is_lineside=is_lineside,
        has_AFD=has_AFD,
        AFD_clearing_time_ms=AFD_t,
        n_taps=n_taps,
        description=desc,
    )
