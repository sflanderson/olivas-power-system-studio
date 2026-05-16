"""
app.preprocessor.bridge_to_atp — converte um `PpProject` (esquemático
estilo Qucs) em um `AtpProject` pronto para serializar via
`app.core.serializer.serialize_project`.

Estratégia
----------

1. Coalesce nós usando `node_coalescer.coalesce_nodes()`.
2. Para cada componente Qucs com mapeamento ATP, cria a entidade
   ATP correspondente:
     - **R / L / C**         → `BranchComponent` (1 elemento RLC).
     - **Vdc**               → `SourceComponent` type 11 (DC step).
     - **Vac**               → `SourceComponent` type 14 (AC sinusoid).
     - **Idc / Iac**         → mesmo, com sinal trocado (corrente).
     - **Vrect**             → `SourceComponent` type 13 (rampa).
     - **GND**               → não emite nada — o nome de nó já é
                                ``""`` por convenção do node_coalescer.
     - **Diode**             → `SwitchComponent` (chave controlada
                                por tensão, type 11 ATP).
     - **SwIdeal / Relais**  → `SwitchComponent` (time-controlled).
     - **VCB (1φ)**          → `SwitchComponent` com ``switch_type="VCB"``.
     - **VCB3 (3φ)**         → 3× `SwitchComponent` (um por fase) com
                                T_open/T_close independentes.
     - **Eqn / .TR / .DC /
        .SW / .AC / .SP**     → ignorado (apenas metadata Qucs).
3. Construímos o `AtpProject` com as 3 seções padrão (`/BRANCH`,
   `/SWITCH`, `/SOURCE`) já populadas, mais o esqueleto de raw_lines
   compatível com `serialize_project`.

Limitações conhecidas (v0.21.1)
-------------------------------

* Transformador (Tr/sTr/Tr3): emitido como branch tipo 19 placeholder
  com warning. Implementação completa precisa de saturação e múltiplos
  enrolamentos via /BRANCH IDEAL — fica para v0.21.5 (extensão).
* Linhas (TLIN/BERG/JMARTI): mesmo — placeholder com warning.
* Tiristor / IGBT / MOSFET / GTO: traduzidos como SWITCH controlado
  (type 11) com flag em `switch_type` indicando o tipo. A modelagem
  refinada com TACS/MODELS para gate fica para v0.21.6.
* Não-lineares (ZnO / RNL / LNL): branch placeholder com warning.

Estes warnings são acumulados em `AtpProject.warnings` para que o
caller (e a futura GUI) possam alertar o usuário.
"""

from __future__ import annotations

from typing import Optional

from app.core.project_model import (
    AtpProject,
    BranchComponent,
    HeaderInfo,
    Node,
    Section,
    SourceComponent,
    SwitchComponent,
)

from .models import PpComponent, PpProject
from .node_coalescer import NodeMap, coalesce_nodes, pin_positions
from .bus import (
    BusComponent, emit_bus_metadata_lines, validate_bus,
)
from .motor import (
    MotorParameters, MotorType, emit_motor_metadata_lines,
    validate_motor,
)
from .synchronous_machine import (
    SynchronousMachineParameters, emit_sm_cards, validate_sm,
)
from .xfmr import (
    CoreType, HybridTransformerParameters, WindingConnection,
    emit_xfmr_cards, validate_xfmr,
)
from .tacs import (
    TacsBlock, collect_variables, emit_tacs_section,
    parse_tacs_expression, validate_tacs_block,
)
from .units import format_atp_str, parse_value
from .vcb_model_emitter import build_models_section, vcb_needs_model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Limite de comprimento de nomes em ATP (campos de 6 caracteres em
# fixed-format; alguns campos podem aceitar até 12 em extended-format,
# mas o conservador é 6).
ATP_NAME_MAX_LEN = 6


def _insert_lines_at(
    project: AtpProject,
    insert_at: int,
    lines: list[str],
    *,
    grow_section: Optional[str] = None,
) -> int:
    """
    Insere ``lines`` em ``project.raw_lines`` no índice ``insert_at``
    e atualiza CORRETAMENTE ``start_line``/``end_line`` de TODAS as
    seções afetadas (não apenas SWITCH/SOURCE).

    v0.28.2-PRO: substitui o padrão fragmentado de
    ``for other in ("SWITCH", "SOURCE")`` espalhado em 9 funções
    ``_inject_*`` (auditoria P0). O bug original era que cada
    helper independentemente tinha que enumerar TODAS as seções
    downstream — uma seção esquecida (ex: OUTPUT em uma versão
    futura) causava ``end_line`` desatualizado e corrupção
    silenciosa de slicing.

    Estratégia
    ===========

    1. Insere ``lines`` na posição ``insert_at`` da raw_lines.
    2. Para cada seção do project:
       - Se ``section.end_line`` < insert_at: não afetada.
       - Se ``section.start_line`` >= insert_at: shift inteiro.
       - Se ``section.start_line < insert_at <= section.end_line``:
         growth interno → ``end_line`` shifted, ``start_line`` não.
    3. Se ``grow_section`` fornecido, força crescimento dessa
       seção (mesmo se ``insert_at == section.end_line + 1``,
       o que ambíguo entre "apend ao final" vs "início da próxima").

    Parameters
    ----------
    project:
        AtpProject sendo populado.
    insert_at:
        Índice em raw_lines onde as linhas serão inseridas.
    lines:
        Linhas a inserir.
    grow_section:
        Nome da seção que deve crescer (em vez de só shift downstream).
        Ex: "BRANCH" para metadata appended ao /BRANCH.

    Returns
    -------
    int
        Número de linhas inseridas (= len(lines)).
    """
    if not lines:
        return 0
    project.raw_lines[insert_at:insert_at] = lines
    shift = len(lines)

    for sec_name, sec in project.sections.items():
        # Caso especial: grow_section explícito quando insert_at
        # está logo após o final da seção (apêndice).
        is_grow_target = (
            grow_section is not None
            and sec_name == grow_section
            and insert_at == sec.end_line + 1
        )
        if is_grow_target:
            sec.end_line += shift
            continue

        if sec.end_line < insert_at - 1:
            # Seção termina ANTES do insert_at (não na fronteira)
            continue
        if sec.start_line >= insert_at:
            # Seção totalmente abaixo
            sec.start_line += shift
            sec.end_line += shift
            continue
        # insert_at no MEIO da seção: cresce a seção
        if insert_at <= sec.end_line:
            sec.end_line += shift

    return shift


def _truncate_atp_name(
    name: str,
    *,
    where: str = "",
    project: Optional[AtpProject] = None,
    max_len: int = ATP_NAME_MAX_LEN,
) -> str:
    """
    Trunca um nome para o limite de campos ATP, emitindo
    warning estruturado quando o truncamento ocorrer.

    v0.28.2-PRO: substitui ``name[:6]`` espalhado em 30+
    pontos do bridge_to_atp por uma chamada centralizada.
    Resolve auditoria P0: colisão silenciosa
    (ex: ``"BUS-A-13.8kV"`` → ``"BUS-A-"`` colide com
    ``"BUS-A-loadside"``).

    Parameters
    ----------
    name:
        Nome original.
    where:
        Identificador da chamada para rastreabilidade
        (ex: "Vac source", "TR3 secondary leg", "SM rotor").
    project:
        Se fornecido, warnings são apendados a
        ``project.warnings``; senão silenciosos.
    max_len:
        Default 6 (ATP fixed-format). Use 12 para
        extended-format quando aplicável.

    Returns
    -------
    str
        Nome truncado.
    """
    if name is None:
        return ""
    s = str(name)
    if len(s) <= max_len:
        return s
    truncated = s[:max_len]
    if project is not None:
        ctx = f" em {where}" if where else ""
        project.warnings.append(
            f"Nome ATP {s!r} truncado para {truncated!r}{ctx} "
            f"(limite de campo {max_len} chars). Verifique se há "
            "outros componentes com mesmo prefixo (risco de "
            "colisão silenciosa)."
        )
    return truncated


def _component_key(comp: PpComponent, gnd_counter: list[int]) -> str:
    """Reproduz a convenção do node_coalescer para chave de pino."""
    if comp.name == "*":
        key = f"*{gnd_counter[0]}"
        gnd_counter[0] += 1
        return key
    return comp.name


def _node_of(node_map: NodeMap, comp_key: str, pin_index: int) -> str:
    return node_map.pin_to_node.get((comp_key, pin_index), "")


def _fmt_or_empty(value: Optional[float], width: int = 6) -> str:
    """Formata número ou devolve string vazia se None."""
    if value is None:
        return ""
    return format_atp_str(value, width=width)


def _parse_or_keep(text: str, width: int = 6) -> str:
    """
    Tenta extrair número da string Qucs e formatar; se falhar,
    devolve a string original (truncada à largura).
    """
    v = parse_value(text)
    if v is None:
        return (text or "").strip()[:width]
    return format_atp_str(v, width=width)


# ---------------------------------------------------------------------------
# Tradução por tipo
# ---------------------------------------------------------------------------


def _convert_resistor(comp: PpComponent, n1: str, n2: str) -> BranchComponent:
    """
    Qucs `R Rname ... "value [unit]" v "T" v "Tc1" v "Tc2" v "Tnom" v "model" v`
    → ATP /BRANCH com R apenas.

    v0.91.10: ``ref1`` em BRANCH (cols 15-20 do formato ATP) é
    REFERÊNCIA a uma branch anterior em circuitos mutually-
    coupled (type_code 1/2/3). Para R-L-C linear simples
    (type_code blank), ``ref1`` DEVE ser blank — caso contrário
    ATP interpreta como bus3 inválido e emite ERROR.

    Antes (bug): ``ref1=comp.name[:6]`` colocava "R_FEED" em
    cols 15-20, ATP rejeitava com errors.
    """
    return BranchComponent(
        node1=n1,
        node2=n2,
        type_code="",
        ref1="",       # v0.91.10: blank para R linear
        resistance=_parse_or_keep(comp.get(0, "0"), width=10),
        inductance="",
        capacitance="",
        semantic_type="resistor",
        is_new=True,
    )


def _convert_inductor(comp: PpComponent, n1: str, n2: str) -> BranchComponent:
    """
    Qucs `L Lname ... "value [unit]" v "I" v`
    → ATP /BRANCH com L apenas (mH no ATP, então convertemos H → mH).

    v0.91.10: ``ref1`` blank (mesmo motivo de _convert_resistor).
    """
    h = parse_value(comp.get(0, "0"))
    if h is None:
        l_str = comp.get(0, "")
    else:
        l_str = format_atp_str(h * 1000.0, width=10)  # ATP usa mH

    return BranchComponent(
        node1=n1,
        node2=n2,
        type_code="",
        ref1="",       # v0.91.10: blank para L linear
        resistance="",
        inductance=l_str,
        capacitance="",
        semantic_type="inductor",
        is_new=True,
    )


def _convert_capacitor(comp: PpComponent, n1: str, n2: str) -> BranchComponent:
    """
    Qucs `C Cname ... "value [unit]" v "V" v "type" v`
    → ATP /BRANCH com C apenas (uF no ATP, então H → uF: ×1e6).

    v0.91.10: ``ref1`` blank (mesmo motivo).
    """
    f = parse_value(comp.get(0, "0"))
    if f is None:
        c_str = comp.get(0, "")
    else:
        c_str = format_atp_str(f * 1e6, width=10)  # ATP usa uF

    return BranchComponent(
        node1=n1,
        node2=n2,
        type_code="",
        ref1="",       # v0.91.10: blank para C linear
        resistance="",
        inductance="",
        capacitance=c_str,
        semantic_type="capacitor",
        is_new=True,
    )


def _convert_vdc(comp: PpComponent, n: str) -> SourceComponent:
    """Qucs Vdc → ATP SOURCE type 11 (DC step)."""
    amp = _parse_or_keep(comp.get(0, "0"), width=10)
    return SourceComponent(
        node=n,
        type_code="11",
        amplitude=amp,
        frequency="",
        phase="",
        t_start="",
        t_stop="",
        semantic_type="dc",
        is_new=True,
    )


def _convert_vac(comp: PpComponent, n: str) -> SourceComponent:
    """
    Qucs Vac (Vamp, Vfreq, phase, delay) → ATP SOURCE type 14.

    v0.91.11: ``t_start = -1.0`` por padrão (Rule Book §10.3.4
    Rule 6): "An AC steady-state solution is automatically
    computed if Tstart < 0 on one or more AC source cards
    (Type-14)". Sem isso, ATP iniciava no t=0 sem pré-condição
    → transientes numéricos espúrios na partida + ERROR no
    solver.

    Para sobrescrever, edite a propriedade do componente após
    criar.
    """
    amp = _parse_or_keep(comp.get(0, "0"), width=10)
    freq = _parse_or_keep(comp.get(1, "60"), width=10)
    phase = _parse_or_keep(comp.get(2, "0"), width=10)
    return SourceComponent(
        node=n,
        type_code="14",
        amplitude=amp,
        frequency=freq,
        phase=phase,
        # v0.91.11: tstart=-1 → AC steady-state init pelo solver
        t_start="-1.",
        t_stop="",
        semantic_type="ac",
        is_new=True,
    )


def _convert_idc(comp: PpComponent, n: str) -> SourceComponent:
    """
    Qucs Idc → ATP SOURCE type **-11** (DC current).

    v0.28.2-PRO: corrigido bug crítico — type_code anterior era
    ``"-1"`` (não-existente em ATP). A convenção ATP é:

    * Type 11 = DC voltage step (positive = voltage source)
    * Type **-11** = DC current step (negative sign = current
      source, mesma família 11)

    Type "-1" não tem semântica em ATP e era ignorado/
    misinterpretado pelo solver. Auditoria v0.27.11.1 P0.
    """
    amp = _parse_or_keep(comp.get(0, "0"), width=10)
    return SourceComponent(
        node=n,
        type_code="-11",   # v0.28.2-PRO: era "-1" (errado)
        amplitude=amp,
        frequency="",
        phase="",
        t_start="",
        t_stop="",
        semantic_type="dc",
        is_new=True,
    )


def _convert_iac(comp: PpComponent, n: str) -> SourceComponent:
    """
    Qucs Iac → ATP SOURCE type **-14** (AC current cosine).

    v0.28.2-PRO: corrigido bug crítico — type_code anterior era
    ``"-4"`` (não-existente em ATP). A convenção ATP é:

    * Type 14 = AC voltage cosine source
    * Type **-14** = AC current cosine source (mesma família 14)

    Auditoria v0.27.11.1 P0.

    v0.91.11: ``t_start = -1.0`` por padrão (Rule Book §10.3.4
    Rule 6) — habilita AC steady-state init.
    """
    amp = _parse_or_keep(comp.get(0, "0"), width=10)
    freq = _parse_or_keep(comp.get(1, "60"), width=10)
    phase = _parse_or_keep(comp.get(2, "0"), width=10)
    return SourceComponent(
        node=n,
        type_code="-14",   # v0.28.2-PRO: era "-4" (errado)
        amplitude=amp,
        frequency=freq,
        phase=phase,
        t_start="-1.",     # v0.91.11: AC steady-state init
        t_stop="",
        semantic_type="ac",
        is_new=True,
    )


def _convert_diode(comp: PpComponent, n1: str, n2: str) -> SwitchComponent:
    """
    Qucs Diode → ATP SWITCH controlado por tensão (type 11), com
    Vign = 0.7V default. ATPDraw modela diodo assim quando não há
    eletrônica refinada disponível.
    """
    return SwitchComponent(
        node1=n1,
        node2=n2,
        type_code="11",
        t_close="-1",   # always
        t_open="1000",  # never
        ie="0.7",       # forward voltage (V)
        switch_type="DIODE",
        semantic_type="diode",
        is_new=True,
    )


def _convert_switch_ideal(comp: PpComponent, n1: str, n2: str) -> SwitchComponent:
    """Qucs SwIdeal / Relais → ATP SWITCH controlado por tempo."""
    # Relais: "Vt" "Vh" "1" "1e12" "Tc"
    # SwIdeal: dependerá do schema final (v0.21.6).
    # Aqui usamos defaults razoáveis: chave aberta sempre.
    return SwitchComponent(
        node1=n1,
        node2=n2,
        type_code="",
        t_close="1.0",
        t_open="1000.0",
        ie="0",
        switch_type="MEASURING",
        semantic_type="time_controlled",
        is_new=True,
    )


def _convert_motor(
    comp: PpComponent, key: str, node_map: NodeMap, project: AtpProject,
) -> Optional[MotorParameters]:
    """
    Qucs MOTOR.ocomp → MotorParameters.

    Pinos: 3 (A, B, C). Properties (9, v0.27.7.9):

    ====  ============================  ============================
    idx   significado                    tipo
    ====  ============================  ============================
    0     motor_type                    string (induction/synchronous)
    1     rated_voltage_kV              float kV
    2     rated_power_kW                float kW
    3     rated_pf                      float
    4     efficiency                    float
    5     locked_rotor_current_pu       float
    6     starting_pf                   float
    7     n_poles                       float (par)
    8     Td_pp_ms                      float ms
    ====  ============================  ============================
    """
    n_a = _node_of(node_map, key, 0)
    n_b = _node_of(node_map, key, 1)
    n_c = _node_of(node_map, key, 2)

    def _pf(idx: int, default: float, label: str) -> Optional[float]:
        raw = (comp.get(idx, "") or "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            project.warnings.append(
                f"MOTOR {comp.name!r}: prop {label}={raw!r} não-numérica."
            )
            return None

    def _ps(idx: int, default: str) -> str:
        raw = (comp.get(idx, "") or "").strip()
        return raw or default

    motor_type_str = _ps(0, "induction")
    voltage = _pf(1, 0.480, "rated_voltage_kV")
    power = _pf(2, 100.0, "rated_power_kW")
    pf = _pf(3, 0.85, "rated_pf")
    eff = _pf(4, 0.95, "efficiency")
    locked = _pf(5, 6.0, "locked_rotor_current_pu")
    start_pf = _pf(6, 0.30, "starting_pf")
    n_poles = _pf(7, 4.0, "n_poles")
    Td = _pf(8, 20.0, "Td_pp_ms")

    if None in (voltage, power, pf, eff, locked, start_pf, n_poles, Td):
        return None

    try:
        m_type = MotorType(motor_type_str.lower())
    except ValueError:
        project.warnings.append(
            f"MOTOR {comp.name!r}: motor_type {motor_type_str!r} "
            "inválido — usando induction default."
        )
        m_type = MotorType.INDUCTION

    name = _truncate_atp_name(
        comp.name or "MOTOR", where="MOTOR component", project=project,
    )
    motor = MotorParameters(
        name=name,
        node_a=n_a, node_b=n_b, node_c=n_c,
        motor_type=m_type,
        rated_voltage_kV=voltage,
        rated_power_kW=power,
        rated_pf=pf,
        efficiency=eff,
        locked_rotor_current_pu=locked,
        starting_pf=start_pf,
        n_poles=int(round(n_poles)),
        Td_pp_ms=Td,
    )
    errs = validate_motor(motor)
    if errs:
        project.warnings.append(
            f"MOTOR {comp.name!r}: validação falhou — "
            + "; ".join(errs) + ". Descartado."
        )
        return None
    return motor


def _inject_motor_metadata(
    motor: MotorParameters, project: AtpProject,
) -> None:
    """Injeta comentários metadata no /BRANCH."""
    cards = emit_motor_metadata_lines(motor)
    section = project.sections.get("BRANCH")
    if section is None:
        project.warnings.append(
            f"MOTOR {motor.name!r}: metadata sem /BRANCH."
        )
        return
    insert_at = section.end_line + 1
    # v0.28.2-PRO: helper centralizado (era loop manual)
    _insert_lines_at(
        project, insert_at, cards, grow_section="BRANCH",
    )
    from app.preprocessor.motor import (
        initial_sc_contribution_kA, rated_current_A,
    )
    project.warnings.append(
        f"MOTOR {motor.name!r}: {motor.motor_type.value} "
        f"{motor.rated_power_kW:.0f} kW @ "
        f"{motor.rated_voltage_kV:.3f} kV; "
        f"I_rM = {rated_current_A(motor):.1f} A, "
        f"contribuição SC = {initial_sc_contribution_kA(motor):.3f} kA"
        f" (decay τ = {motor.Td_pp_ms:.0f} ms)."
    )


def _convert_bus(
    comp: PpComponent, key: str, node_map: NodeMap, project: AtpProject,
) -> Optional[BusComponent]:
    """
    Qucs BUS.ocomp → BusComponent.

    O BUS é um nó zero-impedância — eletricamente, a coalescência
    de nós já trata isso (todos os pinos do BUS coalescem para o
    mesmo nó). Aqui apenas emitimos metadata de painel como
    comentários no .atp para auditoria e integração com
    arc-flash analysis.

    Properties (8, v0.27.7):

    ====  =========================  ========================
    idx   significado                 tipo
    ====  =========================  ========================
    0     bus_id                      string
    1     rated_voltage_kV            float kV
    2     n_phases                    float (1 ou 3)
    3     panel_type                  string (key do enum)
    4     is_lineside                 float (1=true, 0=false)
    5     has_AFD                     float (1=true, 0=false)
    6     AFD_clearing_time_ms        float ms
    7     n_taps                      float
    8     description                 string (opcional)
    ====  =========================  ========================
    """
    from app.standards.nbr17227 import EquipmentClass

    def _pf(idx: int, default: float, label: str) -> Optional[float]:
        raw = (comp.get(idx, "") or "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            project.warnings.append(
                f"BUS {comp.name!r}: prop {label}={raw!r} não-numérica."
            )
            return None

    def _ps(idx: int, default: str) -> str:
        raw = (comp.get(idx, "") or "").strip()
        return raw or default

    bus_id = _ps(0, comp.name or "BUS")
    voltage = _pf(1, 13.8, "rated_voltage_kV")
    n_phases = _pf(2, 3.0, "n_phases")
    panel_type_str = _ps(3, "swgr_15kv")
    is_lineside_f = _pf(4, 1.0, "is_lineside")
    has_AFD_f = _pf(5, 0.0, "has_AFD")
    AFD_t = _pf(6, 10.0, "AFD_clearing_time_ms")
    n_taps_f = _pf(7, 4.0, "n_taps")
    desc = _ps(8, "")

    if None in (voltage, n_phases, is_lineside_f, has_AFD_f,
                AFD_t, n_taps_f):
        return None

    # Parse panel_type enum
    try:
        panel_type = EquipmentClass(panel_type_str)
    except ValueError:
        project.warnings.append(
            f"BUS {comp.name!r}: panel_type {panel_type_str!r} "
            "inválido — usando swgr_15kv default."
        )
        panel_type = EquipmentClass.SWITCHGEAR_15KV

    bus = BusComponent(
        bus_id=bus_id[:32],   # ATP comments suportam textos longos
        rated_voltage_kV=voltage,
        n_phases=int(round(n_phases)),
        panel_type=panel_type,
        is_lineside=bool(is_lineside_f),
        has_AFD=bool(has_AFD_f),
        AFD_clearing_time_ms=AFD_t,
        n_taps=int(round(n_taps_f)),
        description=desc,
    )
    errs = validate_bus(bus)
    if errs:
        project.warnings.append(
            f"BUS {comp.name!r}: validação falhou — "
            + "; ".join(errs) + ". Descartado."
        )
        return None
    return bus


def _inject_bus_metadata(
    bus: BusComponent, project: AtpProject,
) -> None:
    """Injeta comentários metadata do BUS no /BRANCH."""
    cards = emit_bus_metadata_lines(bus)
    section = project.sections.get("BRANCH")
    if section is None:
        # Sem /BRANCH: apenas adiciona warning informativo
        project.warnings.append(
            f"BUS {bus.bus_id!r}: metadata gerada sem /BRANCH."
        )
        return
    insert_at = section.end_line + 1
    # v0.28.2-PRO: helper centralizado
    _insert_lines_at(
        project, insert_at, cards, grow_section="BRANCH",
    )
    afd_str = "AFD on" if bus.has_AFD else "no AFD"
    side = "lineside" if bus.is_lineside else "loadside"
    project.warnings.append(
        f"BUS {bus.bus_id!r}: painel {bus.panel_type.value} "
        f"@ {bus.rated_voltage_kV:.1f} kV, {side}, {afd_str}."
    )


def _convert_xfmr(
    comp: PpComponent, key: str, node_map: NodeMap, project: AtpProject,
) -> Optional[HybridTransformerParameters]:
    """
    Qucs XFMR.ocomp → HybridTransformerParameters (Mork hybrid).

    XFMR tem 6 pinos: HV_A (0), HV_B (1), HV_C (2), LV_A (3),
    LV_B (4), LV_C (5).

    Properties (15, v0.27.5):

    ====  ============================  =========================
    idx   significado                    tipo / unidade
    ====  ============================  =========================
    0     rated_voltage_HV_kV           float kV
    1     rated_voltage_LV_kV           float kV
    2     rated_power_MVA               float MVA
    3     frequency_Hz                  float Hz
    4     core_type                     str (TRIPLEX/THREE_LEG/...)
    5     uk_pos_pct                    float %
    6     p_load_kW                     float kW
    7     i_no_load_pct                 float %
    8     p_no_load_kW                  float kW
    9     residual_flux_pu              float [-0.95, 0.95]
    10    final_slope_inductance_pu     float pu
    11    connection_HV                 str (Y/Yg/D/A/Z)
    12    connection_LV                 str
    13    C_HV_to_ground_pF             float pF
    14    C_LV_to_ground_pF             float pF
    15    C_HV_LV_pF                    float pF
    ====  ============================  =========================
    """
    nodes_hv = (
        _node_of(node_map, key, 0),
        _node_of(node_map, key, 1),
        _node_of(node_map, key, 2),
    )
    nodes_lv = (
        _node_of(node_map, key, 3),
        _node_of(node_map, key, 4),
        _node_of(node_map, key, 5),
    )

    def _pf(idx: int, default: float, label: str) -> Optional[float]:
        raw = (comp.get(idx, "") or "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            project.warnings.append(
                f"XFMR {comp.name!r}: prop {label}={raw!r} não-numérica."
            )
            return None

    def _ps(idx: int, default: str) -> str:
        raw = (comp.get(idx, "") or "").strip()
        return raw or default

    V_HV = _pf(0, 138.0, "rated_voltage_HV_kV")
    V_LV = _pf(1, 13.8, "rated_voltage_LV_kV")
    S = _pf(2, 25.0, "rated_power_MVA")
    f = _pf(3, 60.0, "frequency_Hz")
    core_str = _ps(4, "THREE_LEG")
    uk = _pf(5, 10.0, "uk_pos_pct")
    p_load = _pf(6, 100.0, "p_load_kW")
    i_0 = _pf(7, 0.5, "i_no_load_pct")
    p_0 = _pf(8, 15.0, "p_no_load_kW")
    residual = _pf(9, 0.0, "residual_flux_pu")
    La = _pf(10, 0.04, "final_slope_inductance_pu")
    conn_hv_str = _ps(11, "Yg")
    conn_lv_str = _ps(12, "D")
    C_HV_g = _pf(13, 0.0, "C_HV_to_ground_pF")
    C_LV_g = _pf(14, 0.0, "C_LV_to_ground_pF")
    C_HV_LV = _pf(15, 0.0, "C_HV_LV_pF")

    if None in (V_HV, V_LV, S, f, uk, p_load, i_0, p_0, residual, La):
        return None

    # Parse enums
    try:
        core_type = CoreType(core_str.upper())
    except ValueError:
        project.warnings.append(
            f"XFMR {comp.name!r}: core_type {core_str!r} inválido — "
            "usando THREE_LEG default."
        )
        core_type = CoreType.THREE_LEG_STACKED
    try:
        conn_hv = WindingConnection(conn_hv_str)
    except ValueError:
        conn_hv = WindingConnection.WYE_GROUNDED
    try:
        conn_lv = WindingConnection(conn_lv_str)
    except ValueError:
        conn_lv = WindingConnection.DELTA

    name = _truncate_atp_name(
        comp.name or "XFMR", where="XFMR component", project=project,
    )
    xfmr = HybridTransformerParameters(
        name=name,
        nodes_hv=nodes_hv, nodes_lv=nodes_lv,
        rated_voltage_HV_kV=V_HV, rated_voltage_LV_kV=V_LV,
        rated_power_MVA=S, frequency_Hz=f,
        connection_HV=conn_hv, connection_LV=conn_lv,
        uk_pos_pct=uk, p_load_kW=p_load,
        i_no_load_pct=i_0, p_no_load_kW=p_0,
        core_type=core_type,
        residual_flux_pu=residual,
        final_slope_inductance_pu=La,
        C_HV_to_ground_pF=C_HV_g or 0.0,
        C_LV_to_ground_pF=C_LV_g or 0.0,
        C_HV_LV_pF=C_HV_LV or 0.0,
    )
    errs = validate_xfmr(xfmr)
    if errs:
        project.warnings.append(
            f"XFMR {comp.name!r}: validação falhou — "
            + "; ".join(errs) + ". Descartado."
        )
        return None
    return xfmr


def _inject_xfmr_cards(
    xfmr: HybridTransformerParameters, project: AtpProject,
) -> None:
    """Injeta cartões XFMR no /BRANCH (similar a BCTRAN)."""
    cards = emit_xfmr_cards(xfmr)
    section = project.sections.get("BRANCH")
    if section is None:
        project.warnings.append(
            f"XFMR {xfmr.name!r}: cards gerados mas sem seção /BRANCH."
        )
        return
    insert_at = section.end_line + 1
    # v0.28.2-PRO: helper centralizado
    _insert_lines_at(
        project, insert_at, cards, grow_section="BRANCH",
    )
    project.warnings.append(
        f"XFMR {xfmr.name!r}: emitido com core {xfmr.core_type.value}, "
        f"V={xfmr.rated_voltage_HV_kV:.1f}/{xfmr.rated_voltage_LV_kV:.1f} kV, "
        f"S={xfmr.rated_power_MVA:.1f} MVA, fluxo residual="
        f"{xfmr.residual_flux_pu:+.2f} pu (use estimate_peak_inrush_current_kA "
        "para análise)."
    )


def _convert_synchronous_machine(
    comp: PpComponent, key: str, node_map: NodeMap, project: AtpProject,
) -> Optional[SynchronousMachineParameters]:
    """
    Qucs SM.ocomp → ATP MACHINE-59/58.

    SM tem 4 pinos: A (0), B (1), C (2), N (3 — neutro opcional).

    Properties (24, v0.27.0):

    ====  ==============================  ==================================
    idx   significado                      tipo / unidade
    ====  ==============================  ==================================
    0     rated_voltage_kV                float kV (V_LL)
    1     rated_power_MVA                  float MVA
    2     frequency_Hz                     float Hz
    3     n_poles                          int (par, ≥ 2)
    4     Xd                               float pu
    5     Xd_prime                         float pu
    6     Xd_pp                            float pu
    7     Td_prime                         float s
    8     Td_pp                            float s
    9     Xq                               float pu
    10    Xq_prime                         float pu (0 ⇒ tipo 58)
    11    Xq_pp                            float pu
    12    Tq_prime                         float s
    13    Tq_pp                            float s
    14    Ra                               float pu
    15    xL                               float pu
    16    X0                               float pu
    17    H                                float s
    18    D                                float pu
    19    P0_MW                            float MW
    20    Q0_MVAr                          float MVAr
    21    V0_pu                            float pu
    22    angle0_deg                       float graus
    ====  ==============================  ==================================

    Em caso de validação falha, acumula warning e retorna None.
    """
    n_a = _node_of(node_map, key, 0)
    n_b = _node_of(node_map, key, 1)
    n_c = _node_of(node_map, key, 2)
    n_n = _node_of(node_map, key, 3) if 3 < len(comp.properties) else ""

    def _pf(idx: int, default: float, label: str) -> Optional[float]:
        raw = (comp.get(idx, "") or "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            project.warnings.append(
                f"SM {comp.name!r}: prop {label}={raw!r} não-numérica."
            )
            return None

    rated_voltage_kV = _pf(0, 13.8, "rated_voltage_kV")
    rated_power_MVA = _pf(1, 100.0, "rated_power_MVA")
    frequency_Hz = _pf(2, 60.0, "frequency_Hz")
    n_poles_f = _pf(3, 2.0, "n_poles")
    Xd = _pf(4, 1.8, "Xd")
    Xd_prime = _pf(5, 0.30, "Xd_prime")
    Xd_pp = _pf(6, 0.20, "Xd_pp")
    Td_prime = _pf(7, 0.8, "Td_prime")
    Td_pp = _pf(8, 0.030, "Td_pp")
    Xq = _pf(9, 1.7, "Xq")
    Xq_prime = _pf(10, 0.55, "Xq_prime")
    Xq_pp = _pf(11, 0.20, "Xq_pp")
    Tq_prime = _pf(12, 0.4, "Tq_prime")
    Tq_pp = _pf(13, 0.050, "Tq_pp")
    Ra = _pf(14, 0.003, "Ra")
    xL = _pf(15, 0.15, "xL")
    X0 = _pf(16, 0.05, "X0")
    H = _pf(17, 3.0, "H")
    D = _pf(18, 0.0, "D")
    P0_MW = _pf(19, 0.0, "P0_MW")
    Q0_MVAr = _pf(20, 0.0, "Q0_MVAr")
    V0_pu = _pf(21, 1.0, "V0_pu")
    angle0_deg = _pf(22, 0.0, "angle0_deg")

    if None in (
        rated_voltage_kV, rated_power_MVA, frequency_Hz, n_poles_f,
        Xd, Xd_prime, Xd_pp, Td_prime, Td_pp,
        Xq, Xq_prime, Xq_pp, Tq_prime, Tq_pp,
        Ra, xL, X0, H, D, P0_MW, Q0_MVAr, V0_pu, angle0_deg,
    ):
        return None

    name = _truncate_atp_name(
        comp.name or "SM", where="SM component", project=project,
    )
    sm = SynchronousMachineParameters(
        name=name,
        node_a=n_a, node_b=n_b, node_c=n_c, node_neutral=n_n,
        rated_voltage_kV=rated_voltage_kV,
        rated_power_MVA=rated_power_MVA,
        frequency_Hz=frequency_Hz,
        n_poles=int(round(n_poles_f)),
        Xd=Xd, Xd_prime=Xd_prime, Xd_pp=Xd_pp,
        Td_prime=Td_prime, Td_pp=Td_pp,
        Xq=Xq, Xq_prime=Xq_prime, Xq_pp=Xq_pp,
        Tq_prime=Tq_prime, Tq_pp=Tq_pp,
        Ra=Ra, xL=xL, X0=X0, H=H, D=D,
        P0_MW=P0_MW, Q0_MVAr=Q0_MVAr,
        V0_pu=V0_pu, angle0_deg=angle0_deg,
    )
    errs = validate_sm(sm)
    if errs:
        project.warnings.append(
            f"SM {comp.name!r}: validação falhou — "
            + "; ".join(errs) + ". Descartado."
        )
        return None
    return sm


def _inject_sm_cards(
    sm: SynchronousMachineParameters, project: AtpProject,
) -> None:
    """
    Injeta cartões MACHINE-59/58 nas raw_lines, **antes** do
    /SOURCE (posição canônica ATP). Ajusta tail_lines também.

    Não cria seção dedicada — usa o pseudo-bloco "MACHINE" embutido
    no fluxo padrão ATP-EMTP (mesma estratégia de BCTRAN).
    """
    cards = emit_sm_cards(sm)
    section = project.sections.get("SOURCE")
    if section is None:
        project.warnings.append(
            f"SM {sm.name!r}: cards gerados mas sem seção /SOURCE — "
            "perdido."
        )
        return
    insert_at = section.start_line
    # v0.28.2-PRO (followup code-review): MIGRADO para
    # _insert_lines_at. SM cards vão ANTES da /SOURCE — sem
    # grow_section, então _insert_lines_at apenas faz shift.
    # Tail_lines recalculado a posteriori porque o helper
    # genérico não sabe sobre tail.
    _insert_lines_at(project, insert_at, cards)

    # Recalcula tail_lines com base no fim REAL (última seção
    # processada após shift) — auditoria P0.
    last_section_end = max(
        (s.end_line for s in project.sections.values()),
        default=-1,
    )
    if last_section_end + 1 <= len(project.raw_lines):
        project.tail_lines = project.raw_lines[last_section_end + 1:]
    else:
        project.tail_lines = []
    project.warnings.append(
        f"SM {sm.name!r}: emitida MACHINE-{'59' if sm.Xq_prime > 0 else '58'} "
        f"com {len(cards)} cards (V_LL={sm.rated_voltage_kV:.1f} kV, "
        f"S={sm.rated_power_MVA:.1f} MVA)."
    )


def _convert_sw_tacs(
    comp: PpComponent, n1: str, n2: str, project: AtpProject,
) -> SwitchComponent:
    """
    Qucs SwTACS → ATP SWITCH TYPE-13 (TACS-controlled).

    Properties (v0.26.4):

    ====  ==========================  ========================
    idx   significado                  uso
    ====  ==========================  ========================
    0     trigger_signal               nome do sinal TACS de
                                       controle (≤ 6 chars)
    ====  ==========================  ========================

    A chave fecha quando ``trigger_signal > 0.5`` (default
    binário 0/1). Caller precisa garantir que o sinal exista
    no bloco /TACS HYBRID — bridge não verifica cross-link.
    """
    trigger = (comp.get(0, "trigger") or "trigger").strip()[:6]
    project.warnings.append(
        f"SwTACS {comp.name!r}: SWITCH TYPE-13 emitida; trigger_signal "
        f"= {trigger!r}. Garanta que esse sinal existe em /TACS HYBRID "
        "(bridge não verifica cross-link)."
    )
    return SwitchComponent(
        node1=n1,
        node2=n2,
        type_code="13",
        t_close="0",
        t_open="0",
        ie="0",
        switch_type="TACS",
        semantic_type=f"tacs_controlled:{trigger}",
        is_new=True,
    )


def _convert_vcb_single_phase(
    comp: PpComponent, n1: str, n2: str, project: AtpProject,
) -> SwitchComponent:
    """
    Qucs VCB 1φ → ATP SWITCH controlado por tempo com flag ``VCB``.

    Properties esperadas (v0.21.7):

    ====  ==================  ================================
    idx   significado          usado em SwitchComponent?
    ====  ==================  ================================
    0     T_open [s]           sim  (t_open)
    1     T_close [s]          sim  (t_close)
    2     I_chop [A]           não (futuro MODEL de reignição)
    3     σ(I_chop) [A]        não
    4     di/dt_crit [A/µs]    não
    5     d(di/dt) [A/µs²]     não
    6     k_dielec [V/µs]      não
    7     U0_dielec [V]        não
    8     T_bounce [s]         não
    9     Seed                 não
    ====  ==================  ================================

    As properties 2..9 descrevem o modelo estatístico de reignição
    (corte de corrente, recuperação dielétrica). Ficam armazenadas
    no ``PpComponent`` mas não são emitidas no SWITCH card hoje —
    uma sprint futura adicionará integração MODEL/TACS.
    """
    t_open = _parse_or_keep(comp.get(0, "0"), width=10)
    t_close = _parse_or_keep(comp.get(1, "1e9"), width=10)
    # v0.22.1: se reignition customizada, sinaliza que o MODEL foi
    # emitido mas o wiring TACS é manual (virá em v0.22.2).
    if vcb_needs_model(comp):
        project.warnings.append(
            f"VCB {comp.name!r}: MODEL de reignição emitido no bloco "
            "/MODELS. Wiring TACS (MEASURING na chave + SOURCE TACS "
            "conectando switch_cmd ao TYPE-13) é MANUAL nesta versão — "
            "editar o .atp diretamente. Automação em v0.22.2."
        )
    return SwitchComponent(
        node1=n1,
        node2=n2,
        type_code="",
        t_close=t_close,
        t_open=t_open,
        ie="0",
        switch_type="VCB",
        semantic_type="vcb",
        is_new=True,
    )


def _convert_vcb_three_phase(
    comp: PpComponent, key: str, node_map: NodeMap, project: AtpProject,
) -> list[SwitchComponent]:
    """
    Qucs VCB 3φ → 3 ATP SWITCH (um por fase), com T_open/T_close
    independentes por pólo.

    Pinos:  0=A_in, 1=A_out, 2=B_in, 3=B_out, 4=C_in, 5=C_out.

    Properties esperadas (v0.21.7):

    ======  ========================
    idx     significado
    ======  ========================
    0       T_open_A [s]
    1       T_close_A [s]
    2       T_open_B [s]
    3       T_close_B [s]
    4       T_open_C [s]
    5       T_close_C [s]
    6..13   parâmetros de reignição
            (mesmo schema do VCB 1φ,
            compartilhados pelo pólo)
    ======  ========================
    """
    switches: list[SwitchComponent] = []
    phase_names = ("A", "B", "C")
    # (prop_topen_idx, prop_tclose_idx, pin_in_idx, pin_out_idx)
    phase_layout = (
        (0, 1, 0, 1),
        (2, 3, 2, 3),
        (4, 5, 4, 5),
    )
    for phase, (p_open, p_close, p_in, p_out) in zip(phase_names, phase_layout):
        t_open = _parse_or_keep(comp.get(p_open, "0"), width=10)
        t_close = _parse_or_keep(comp.get(p_close, "1e9"), width=10)
        n_in = _node_of(node_map, key, p_in)
        n_out = _node_of(node_map, key, p_out)
        switches.append(
            SwitchComponent(
                node1=n_in,
                node2=n_out,
                type_code="",
                t_close=t_close,
                t_open=t_open,
                ie="0",
                switch_type="VCB",
                semantic_type=f"vcb_3ph_{phase}",
                is_new=True,
            )
        )
    # v0.22.1: se reignition customizada, o MODEL é emitido — mesmo
    # warning do VCB 1φ (wiring TACS manual).
    if vcb_needs_model(comp):
        project.warnings.append(
            f"VCB3 {comp.name!r}: MODEL de reignição emitido para as 3 "
            "fases (A/B/C) no bloco /MODELS. Wiring TACS manual até "
            "v0.22.2."
        )
    return switches


def _convert_thyristor(comp: PpComponent, n1: str, n2: str) -> SwitchComponent:
    """Tiristor → ATP SWITCH type 11 com flag THYR."""
    return SwitchComponent(
        node1=n1,
        node2=n2,
        type_code="11",
        t_close="-1",
        t_open="1000",
        ie="0",
        switch_type="THYR",
        semantic_type="thyristor",
        is_new=True,
    )


def _convert_igbt(comp: PpComponent, n1: str, n2: str) -> SwitchComponent:
    return SwitchComponent(
        node1=n1, node2=n2, type_code="13",
        t_close="-1", t_open="1000", ie="0",
        switch_type="IGBT", semantic_type="igbt", is_new=True,
    )


def _convert_mosfet(comp: PpComponent, n1: str, n2: str) -> SwitchComponent:
    return SwitchComponent(
        node1=n1, node2=n2, type_code="13",
        t_close="-1", t_open="1000", ie="0",
        switch_type="MOSFET", semantic_type="mosfet", is_new=True,
    )


def _convert_transformer_placeholder(
    comp: PpComponent, nodes: list[str], project: AtpProject,
) -> Optional[BranchComponent]:
    """
    Converter transformador para cards ATP.

    v0.24.1: Tr/sTr com campos 2-enrolamento → cards tipo 51/52.
    v0.24.5: Tr3 com campos 3-enrolamento → 6 cards (1 tipo 51 +
        5 tipo 52) referidos ao H, com ``B1``/``B2`` em nós
        sintéticos para wiring manual (Tr3.ocomp tem só 4 pinos).
    Fallback geral: placeholder tipo 19.

    Nota sobre retorno: quando BCTRAN é usado, as linhas reais
    são injetadas em ``project.raw_lines`` (mecanismo análogo
    ao MODEL de VCB v0.22.1); retornamos ``None``. Caminho legacy
    retorna o BranchComponent.
    """
    if len(nodes) < 4:
        project.warnings.append(
            f"Transformador {comp.name!r}: pinos insuficientes ({len(nodes)})."
        )
        return None

    # v0.24.5: tenta primeiro 3-enrolamento (Tr3 com layout extenso)
    if comp.type == "Tr3":
        bctran3_data = _extract_bctran3_data(comp)
        if bctran3_data is not None:
            _inject_bctran3_cards(bctran3_data, nodes, comp, project)
            return None  # cards inseridos em raw_lines

    # v0.24.1: detecta dados BCTRAN 2-enrolamento no PpComponent
    bctran_data = _extract_bctran_data(comp)
    if bctran_data is not None:
        _inject_bctran_cards(bctran_data, nodes, comp, project)
        # Não retorna BranchComponent — cards já foram injetados em raw_lines
        return None

    # Caminho legacy: placeholder tipo 19
    project.warnings.append(
        f"Transformador {comp.name!r}: emitido como placeholder. "
        "Preencha V_H/V_L/S_nom + dados de teste SC/OC para emissão "
        "BCTRAN real (cards tipo 51/52)."
    )
    return BranchComponent(
        node1=nodes[0],
        node2=nodes[1],
        type_code="19",
        ref1=comp.name[:6],
        ref2=nodes[2][:6],
        resistance="",
        inductance="",
        capacitance="",
        semantic_type="transformer",
        is_new=True,
    )


def _extract_bctran_data(comp: PpComponent):
    """
    Tenta extrair ``TransformerBCTRANData`` das properties do
    componente. Retorna ``None`` se algum campo obrigatório está
    vazio/zero — sinal para usar o placeholder legacy.

    Layout esperado (v0.24.1, Tr.ocomp props 2-8):
        idx 2 = V_H
        idx 3 = V_L
        idx 4 = S_nom
        idx 5 = v_sc_pct
        idx 6 = p_sc_kW
        idx 7 = i_0_pct
        idx 8 = p_0_kW
    """
    from .bctran import (
        TransformerBCTRANData, TransformerOCTest, TransformerSCTest,
    )

    # props 0 = ratio, 1 = L_mag (legacy); 2..8 = BCTRAN
    def _pf(i: int) -> float:
        try:
            return float((comp.get(i, "") or "0").strip())
        except (TypeError, ValueError):
            return 0.0

    v_h    = _pf(2)
    v_l    = _pf(3)
    s_nom  = _pf(4)
    v_sc   = _pf(5)
    p_sc   = _pf(6)
    i_0    = _pf(7)
    p_0    = _pf(8)

    # Critério: exige V_H, V_L, S_nom E v_sc_pct > 0 (os mínimos).
    # p_sc/i_0/p_0 podem ser 0 (magnetização/resistência desprezível).
    if v_h <= 0 or v_l <= 0 or s_nom <= 0 or v_sc <= 0:
        return None

    try:
        return TransformerBCTRANData(
            v_h=v_h,
            v_l=v_l,
            s_nom=s_nom,
            frequency=60.0,
            sc_test=TransformerSCTest(v_sc_pct=v_sc, p_sc_kw=p_sc),
            oc_test=TransformerOCTest(i_0_pct=i_0, p_0_kw=p_0),
            name=comp.name or comp.type,
        )
    except ValueError as e:
        # Dados inconsistentes — marca warning e usa legacy
        return None


def _inject_bctran_cards(
    data, nodes: list[str], comp: PpComponent, project: AtpProject,
) -> None:
    """
    Calcula parâmetros BCTRAN e injeta os cards /BRANCH tipo
    51/52 em ``project.raw_lines``. Anexa warning educativo.

    ``nodes`` = [p1_top, p1_bot, p2_top, p2_bot] — mapeia para
    H1, H2, L1, L2.
    """
    from .bctran import compute_bctran_parameters

    params = compute_bctran_parameters(data)
    n_h1, n_h2, n_l1, n_l2 = nodes[0], nodes[1], nodes[2], nodes[3]
    cards = params.to_atp_cards(n_h1, n_h2, n_l1, n_l2)

    # Insere os cards na seção /BRANCH, antes da BLANK BRANCH.
    section = project.sections.get("BRANCH")
    if section is None:
        # Fallback defensivo — projeto sem seção BRANCH estruturada
        project.warnings.append(
            f"Trafo {comp.name!r}: BCTRAN gerado mas sem seção "
            "/BRANCH para inserir — cards perdidos."
        )
        return
    insert_at = section.end_line + 1  # posição da BLANK BRANCH
    # v0.28.2-PRO: helper centralizado
    _insert_lines_at(
        project, insert_at, cards, grow_section="BRANCH",
    )

    project.warnings.append(
        f"Trafo {comp.name!r}: emitido via BCTRAN "
        f"(V_H={data.v_h:.0f} V, V_L={data.v_l:.0f} V, "
        f"S={data.s_nom:.0f} VA, Z_sc={data.sc_test.v_sc_pct:.1f}%). "
        "Cards tipo 51/52 inseridos em /BRANCH."
    )


def _extract_bctran3_data(comp: PpComponent):
    """
    Tenta extrair ``TransformerBCTRAN3Data`` das properties do Tr3.

    Retorna ``None`` se algum campo crítico está vazio/zero —
    sinal para tentar fallback 2-enrolamento ou placeholder.

    Layout esperado (Tr3.ocomp pós v0.24.5):
        idx 0..1   = ratio, L_mag (legacy, ignorados)
        idx 2..4   = V_H, V_M, V_B
        idx 5..7   = S_H, S_M, S_B
        idx 8..9   = v_sc_HM_pct, p_sc_HM_kW
        idx 10..11 = v_sc_HB_pct, p_sc_HB_kW
        idx 12..13 = v_sc_MB_pct, p_sc_MB_kW
        idx 14..15 = i_0_pct, p_0_kW
        idx 16     = clock (0..11)
    """
    from .bctran import (
        TransformerBCTRAN3Data, TransformerOCTest, TransformerSCTest,
        ThreePhaseGroup, TransformerConnection,
    )

    def _pf(i: int) -> float:
        try:
            return float((comp.get(i, "") or "0").strip())
        except (TypeError, ValueError):
            return 0.0

    def _pi(i: int, default: int = 0) -> int:
        try:
            return int(float((comp.get(i, "") or str(default)).strip()))
        except (TypeError, ValueError):
            return default

    v_h = _pf(2)
    v_m = _pf(3)
    v_b = _pf(4)
    s_h = _pf(5)
    s_m = _pf(6)
    s_b = _pf(7)
    v_sc_hm = _pf(8)
    p_sc_hm = _pf(9)
    v_sc_hb = _pf(10)
    p_sc_hb = _pf(11)
    v_sc_mb = _pf(12)
    p_sc_mb = _pf(13)
    i_0 = _pf(14)
    p_0 = _pf(15)
    clock = _pi(16, 0)

    # Critério mínimo: V_H, V_M, V_B, S_H, S_M, S_B + v_sc_HM_pct.
    # Se v_sc_HB_pct ou v_sc_MB_pct estão zerados, ainda emitimos
    # mas o solver pode dar matriz singular — warning mais abaixo.
    if (
        v_h <= 0 or v_m <= 0 or v_b <= 0
        or s_h <= 0 or s_m <= 0 or s_b <= 0
        or v_sc_hm <= 0
    ):
        return None

    # Para os SCs incompletos, usamos pequenos valores nominais
    # para evitar singularidade — e warning informa.
    if v_sc_hb <= 0:
        v_sc_hb = v_sc_hm  # assume similar
    if v_sc_mb <= 0:
        v_sc_mb = v_sc_hm * 0.5  # heurística — typically MB < HM

    try:
        return TransformerBCTRAN3Data(
            v_h=v_h, v_m=v_m, v_b=v_b,
            s_h=s_h, s_m=s_m, s_b=s_b,
            sc_h_m=TransformerSCTest(v_sc_pct=v_sc_hm, p_sc_kw=p_sc_hm),
            sc_h_b=TransformerSCTest(v_sc_pct=v_sc_hb, p_sc_kw=p_sc_hb),
            sc_m_b=TransformerSCTest(v_sc_pct=v_sc_mb, p_sc_kw=p_sc_mb),
            oc_test=TransformerOCTest(i_0_pct=i_0, p_0_kw=p_0),
            group_3phase=ThreePhaseGroup(
                h_connection=TransformerConnection.Y,
                l_connection=TransformerConnection.Y,
                clock=max(0, min(11, clock)),
            ),
            frequency=60.0,
            name=comp.name or comp.type,
        )
    except ValueError:
        return None


def _inject_bctran3_cards(
    data, nodes: list[str], comp: PpComponent, project: AtpProject,
) -> None:
    """
    Calcula parâmetros BCTRAN 3-enrolamento e injeta os 6 cards
    em ``project.raw_lines``. Para o 3º enrolamento (B), usa nós
    sintéticos ``"TR3_<name>_B1"`` / ``"TR3_<name>_B2"`` (Tr3.ocomp
    tem só 4 pinos físicos no renderer atual). Warning instrui o
    usuário a wirear B manualmente no .atp.

    ``nodes`` = [p1_top, p1_bot, p2_top, p2_bot] — mapeia para
    H1, H2, M1, M2.
    """
    from .bctran import compute_bctran_parameters_3w

    params = compute_bctran_parameters_3w(data)
    n_h1, n_h2, n_m1, n_m2 = nodes[0], nodes[1], nodes[2], nodes[3]
    # Nós sintéticos para enrolamento B — wiring manual pelo usuário.
    # ATP node = máximo 6 chars. Reservamos 4 chars para o sufixo
    # ``_B1``/``_B2`` e preenchemos os 2 primeiros com o início do
    # nome (ou "T" como fallback). Isso garante n_b1 ≠ n_b2 mesmo
    # com nomes longos.
    base = (comp.name or comp.type).strip().replace(" ", "_")[:2]
    if not base:
        base = "T"
    n_b1 = f"{base}_B1"
    n_b2 = f"{base}_B2"

    cards = params.to_atp_cards(
        n_h1, n_h2, n_m1, n_m2, n_b1, n_b2,
        comment=f"BCTRAN 3w {comp.name or comp.type}: H={data.v_h:.0f} M={data.v_m:.0f} B={data.v_b:.0f} V",
    )

    section = project.sections.get("BRANCH")
    if section is None:
        project.warnings.append(
            f"Trafo {comp.name!r}: BCTRAN 3w gerado mas sem seção "
            "/BRANCH para inserir — cards perdidos."
        )
        return
    insert_at = section.end_line + 1
    # v0.28.2-PRO: helper centralizado
    _insert_lines_at(
        project, insert_at, cards, grow_section="BRANCH",
    )

    project.warnings.append(
        f"Trafo {comp.name!r}: emitido via BCTRAN 3-enrolamento "
        f"(H/M/B = {data.v_h:.0f}/{data.v_m:.0f}/{data.v_b:.0f} V, "
        f"grupo {params.group.describe()}, "
        f"clock {params.group.clock}h). Cards tipo 51/52 inseridos. "
        f"NOTA: enrolamento B usa nós sintéticos {n_b1!r}/{n_b2!r} — "
        "wiring manual no .atp se necessário (Tr3.ocomp tem apenas 4 "
        "pinos físicos no renderer atual)."
    )


def _convert_line_placeholder(
    comp: PpComponent, n1: str, n2: str, project: AtpProject,
) -> Optional[BranchComponent]:
    """
    Converter linha (TLIN/BERG/JMARTI) para cards ATP.

    v0.25.1: TLIN com campos de geometria LCC preenchidos
    (x_a, y_a, ..., cond_radius, cond_R_dc) → calcula
    R/L/C de sequência positiva via Carson-Deri-Tévan e emite
    branch R-L-C lumped equivalente. Caso contrário, fallback
    para placeholder tipo "-1" legacy.

    BERG e JMARTI seguem como placeholder em v0.25.1; integração
    em v0.25.2.
    """
    # v0.25.1: caminho LCC para TLIN (PI lumped)
    if comp.type == "TLIN":
        rlc = _try_compute_tlin_via_lcc(comp, project)
        if rlc is not None:
            r_total, l_mh_total, c_uf_total = rlc
            return BranchComponent(
                node1=n1, node2=n2, type_code="",
                ref1=comp.name[:6],
                resistance=_fmt_or_empty(r_total, width=10),
                inductance=_fmt_or_empty(l_mh_total, width=10),
                capacitance=_fmt_or_empty(c_uf_total, width=10),
                semantic_type="line_pi_lcc",
                is_new=True,
            )

    # v0.25.2: caminho Bergeron para BERG (linha distribuída)
    if comp.type == "BERG":
        bg = _try_compute_berg_via_lcc(comp, project)
        if bg is not None:
            z_char, tau_s, r_total = bg
            # Bergeron card: type "-1" com Z_c, τ, R como
            # convenção EMTP-RV / ATP. Codificamos no
            # BranchComponent usando os campos R/L/C como
            # placeholders de Z_char (R), travel_time em ms (L)
            # e R_total (C).
            # Nota: ATP tipo "-1" tem formato canônico próprio;
            # esta é uma representação intermediária — uma
            # sub-sprint futura emitirá o formato strict.
            return BranchComponent(
                node1=n1, node2=n2, type_code="-1",
                ref1=comp.name[:6],
                resistance=_fmt_or_empty(z_char, width=10),
                inductance=_fmt_or_empty(tau_s * 1000.0, width=10),  # ms
                capacitance=_fmt_or_empty(r_total, width=10),
                semantic_type="line_bergeron_lcc",
                is_new=True,
            )

    # Caminho legacy: placeholder tipo -1
    extra = ""
    if comp.type == "TLIN":
        extra = (
            " Preencha geometria LCC (x_a/y_a/...,cond_radius/R_dc) "
            "para emissão R-L-C real via Carson."
        )
    elif comp.type == "BERG":
        extra = (
            " Preencha geometria LCC (x_a/y_a/...,cond_radius/R_dc) "
            "para emissão Bergeron real (Z_char + travel time)."
        )
    project.warnings.append(
        f"Linha {comp.name!r} ({comp.type}): emitido como placeholder."
        f"{extra}"
    )
    return BranchComponent(
        node1=n1, node2=n2, type_code="-1",
        ref1=comp.name[:6], resistance="", inductance="", capacitance="",
        semantic_type="line", is_new=True,
    )


def _try_compute_tlin_via_lcc(
    comp: PpComponent,
    project: AtpProject,
) -> Optional[tuple[float, float, float]]:
    """
    Tenta computar parâmetros LCC do TLIN.

    Layout esperado de TLIN.ocomp pós v0.25.1:
        idx 0..1   = length, R_per_km (legacy)
        idx 2..7   = x_a, y_a, x_b, y_b, x_c, y_c
        idx 8..10  = cond_radius, cond_R_dc, soil_rho

    Retorna ``(R_total_Ω, L_total_mH, C_total_µF)`` se geometria
    completa preenchida e cálculo bem-sucedido. ``None`` caso
    contrário (caller usa fallback placeholder).
    """
    from .lcc import (
        LineGeometry, Conductor,
        compute_line_constants, compute_positive_sequence,
    )
    from .units import parse_value

    def _pf(i: int) -> float:
        try:
            return float((comp.get(i, "") or "0").strip())
        except (TypeError, ValueError):
            return 0.0

    # Comprimento: aceita "100 km", "100", "1e5 m"
    length_raw = (comp.get(0, "100") or "100").strip()
    length_val = parse_value(length_raw)
    if length_val is None:
        # Fallback: tenta extrair número
        try:
            length_val = float(length_raw.split()[0])
        except (ValueError, IndexError):
            return None
    length_km = length_val
    # Heurística: se valor > 1e3 e a unidade no string é "m", divide
    if "km" not in length_raw.lower() and "m" in length_raw.lower():
        length_km = length_val / 1000.0
    if length_km <= 0:
        return None

    y_a = _pf(3)
    y_b = _pf(5)
    y_c = _pf(7)
    cond_r = _pf(8)
    cond_R = _pf(9)
    rho = _pf(10) or 100.0   # default 100 if zero

    if y_a <= 0 or y_b <= 0 or y_c <= 0:
        return None
    if cond_r <= 0 or cond_R < 0:
        return None

    try:
        geom = LineGeometry(
            conductors=[
                Conductor("A", _pf(2), y_a, cond_r, cond_R),
                Conductor("B", _pf(4), y_b, cond_r, cond_R),
                Conductor("C", _pf(6), y_c, cond_r, cond_R),
            ],
            soil_resistivity=rho,
            frequency=60.0,
        )
        lc = compute_line_constants(geom)
        ps = compute_positive_sequence(lc)
    except (ValueError, ZeroDivisionError) as e:
        project.warnings.append(
            f"TLIN {comp.name!r}: geometria LCC inválida ({e}). "
            "Placeholder legacy emitido."
        )
        return None

    # Multiplica por comprimento (totais)
    R_total = ps.R_per_km * length_km          # Ω
    L_total_mH = ps.L_per_km * length_km * 1000.0   # H/km × km × 1000 = mH
    C_total_uF = ps.C_per_km * length_km * 1.0e6    # F/km × km × 1e6 = µF

    project.warnings.append(
        f"TLIN {comp.name!r}: emitido via LCC (Carson-Deri-Tévan). "
        f"Geometria 3φ → seq positiva: R = {ps.R_per_km:.4f} Ω/km, "
        f"L = {ps.L_per_km*1000:.3f} mH/km, "
        f"C = {ps.C_per_km*1e9:.3f} nF/km. "
        f"Lumped (× {length_km:.1f} km): "
        f"R={R_total:.3f} Ω, L={L_total_mH:.3f} mH, C={C_total_uF:.3f} µF."
    )

    return (R_total, L_total_mH, C_total_uF)


def _try_compute_berg_via_lcc(
    comp: PpComponent,
    project: AtpProject,
) -> Optional[tuple[float, float, float]]:
    """
    Tenta computar parâmetros Bergeron (Z_char, τ, R_total) do
    BERG.

    Layout esperado de BERG.ocomp pós v0.25.2:
        idx 0..1   = length, Z_char (legacy, ignorado)
        idx 2..7   = x_a, y_a, x_b, y_b, x_c, y_c
        idx 8..10  = cond_radius, cond_R_dc, soil_rho

    Retorna ``(Z_char_Ω, travel_time_s, R_total_Ω)`` se geometria
    completa preenchida e cálculo bem-sucedido. ``None`` caso
    contrário (caller usa fallback placeholder).
    """
    from .lcc import (
        LineGeometry, Conductor, compute_bergeron_pos_sequence,
    )
    from .units import parse_value

    def _pf(i: int) -> float:
        try:
            return float((comp.get(i, "") or "0").strip())
        except (TypeError, ValueError):
            return 0.0

    length_raw = (comp.get(0, "100") or "100").strip()
    length_val = parse_value(length_raw)
    if length_val is None:
        try:
            length_val = float(length_raw.split()[0])
        except (ValueError, IndexError):
            return None
    length_km = length_val
    if "km" not in length_raw.lower() and "m" in length_raw.lower():
        length_km = length_val / 1000.0
    if length_km <= 0:
        return None

    y_a = _pf(3)
    y_b = _pf(5)
    y_c = _pf(7)
    cond_r = _pf(8)
    cond_R = _pf(9)
    rho = _pf(10) or 100.0

    if y_a <= 0 or y_b <= 0 or y_c <= 0:
        return None
    if cond_r <= 0 or cond_R < 0:
        return None

    try:
        geom = LineGeometry(
            conductors=[
                Conductor("A", _pf(2), y_a, cond_r, cond_R),
                Conductor("B", _pf(4), y_b, cond_r, cond_R),
                Conductor("C", _pf(6), y_c, cond_r, cond_R),
            ],
            soil_resistivity=rho,
            frequency=60.0,
        )
        bp = compute_bergeron_pos_sequence(geom, length_km)
    except (ValueError, ZeroDivisionError) as e:
        project.warnings.append(
            f"BERG {comp.name!r}: geometria LCC inválida ({e}). "
            "Placeholder legacy emitido."
        )
        return None

    project.warnings.append(
        f"BERG {comp.name!r}: emitido como Bergeron via LCC. "
        f"Z_char = {bp.Z_char_pos:.1f} Ω, "
        f"τ = {bp.travel_time*1e6:.2f} µs ({bp.length_km:.1f} km / "
        f"{bp.velocity/1e6:.1f} Mm/s = {bp.velocity/3e8*100:.1f}% c), "
        f"R_total = {bp.R_total:.2f} Ω."
    )

    return (bp.Z_char_pos, bp.travel_time, bp.R_total)


def _convert_nonlinear_placeholder(
    comp: PpComponent, n1: str, n2: str, project: AtpProject,
) -> Optional[BranchComponent]:
    """
    Converter não-linear (ZnO / RNL / LNL) para cards ATP.

    v0.24.2: LNL (indutor saturável) com ``sat_curve_csv`` preenchido
    emite cards Type-98 reais via :mod:`app.preprocessor.type98`.
    Sem curva, cai no placeholder tipo 92 legado.

    ZnO e RNL continuam placeholder (integração v0.24.x+).
    """
    if comp.type == "LNL":
        # LNL layout (pós v0.24.2):
        #   [0] lookup_file  [1] sat_curve_csv
        #   [2] i_ss         [3] flux_ss
        csv = (comp.get(1, "") or "").strip()
        if csv:
            success = _inject_type98_cards(comp, n1, n2, project, csv)
            if success:
                return None  # cards inseridos; sem BranchComponent
            # Se o parse falhou, cai no placeholder legacy abaixo.

    # Caminho legacy: placeholder tipo 92
    extra_hint = ""
    if comp.type == "LNL":
        extra_hint = (
            " Preencha 'sat_curve_csv' (ex: \"0,0; 5,1.0; 50,1.1\") "
            "para emissão Type-98 real."
        )
    project.warnings.append(
        f"Não-linear {comp.name!r} ({comp.type}): emitido como placeholder."
        f"{extra_hint}"
    )
    return BranchComponent(
        node1=n1, node2=n2, type_code="92",
        ref1=comp.name[:6], resistance="", inductance="", capacitance="",
        semantic_type="nonlinear", is_new=True,
    )


def _inject_type98_cards(
    comp: PpComponent,
    n1: str, n2: str,
    project: AtpProject,
    csv: str,
) -> bool:
    """
    Parseia o CSV de saturação e injeta cards Type-98 na seção
    /BRANCH (mesmo mecanismo de _inject_bctran_cards em v0.24.1).

    Lê também ``i_ss`` (prop 2) e ``flux_ss`` (prop 3) se presentes
    para popular o header do Type-98.

    Returns
    -------
    bool
        True se cards foram emitidos com sucesso; False se o parse
        falhou ou não há seção /BRANCH. Nesse caso o caller deve
        cair no placeholder legacy.
    """
    from .type98 import parse_csv_curve, emit_type98_cards

    try:
        curve = parse_csv_curve(csv)
    except ValueError as e:
        project.warnings.append(
            f"LNL {comp.name!r}: curva CSV inválida — "
            f"{e} Placeholder legacy emitido."
        )
        return False

    # Pega i_ss e flux_ss se preenchidos
    def _pf(i: int) -> float:
        try:
            return float((comp.get(i, "") or "0").strip())
        except (TypeError, ValueError):
            return 0.0

    curve.i_ss = _pf(2)
    curve.flux_ss = _pf(3)

    cards = emit_type98_cards(
        n1, n2, curve,
        comment=f"LNL {comp.name or comp.type}: {len(curve.points)} pontos PWL",
    )

    section = project.sections.get("BRANCH")
    if section is None:
        project.warnings.append(
            f"LNL {comp.name!r}: Type-98 gerado mas sem seção /BRANCH — perdido."
        )
        return False

    insert_at = section.end_line + 1
    # v0.28.2-PRO: helper centralizado
    _insert_lines_at(
        project, insert_at, cards, grow_section="BRANCH",
    )

    project.warnings.append(
        f"LNL {comp.name!r}: emitido como Type-98 "
        f"({len(curve.points)} pontos PWL, canônica={curve.is_canonical()})."
    )
    return True


# ---------------------------------------------------------------------------
# Tradutor principal
# ---------------------------------------------------------------------------


_IGNORED_TYPES = {
    "Eqn", ".TR", ".DC", ".AC", ".SW", ".SP",
    "GND", "VProbe", "IProbe",
    # TACS-family tratada em batch via
    # _inject_tacs_section_if_needed (v0.26.5).
    "TACS", "PID", "Integrator", "LowPass", "Limiter", "TSum",
}


def to_atp(project: PpProject) -> AtpProject:
    """
    Constrói um `AtpProject` a partir do `PpProject` Qucs-like.

    O AtpProject resultante já tem `raw_lines` mínimas para ser
    serializado por `app.core.serializer.serialize_project` sem
    edição manual extra.

    Tipos não suportados acumulam mensagens em `atp_project.warnings`
    em vez de levantar exceção — a filosofia é "exporte o que dá,
    avise o que faltou".
    """
    node_map = coalesce_nodes(project)

    # Esqueleto raw_lines com cartas mínimas para ATP rodar.
    #
    # v0.91.10/v0.91.11: cartas ATP conforme EMTP Rule Book §4.2:
    #
    # First Misc Data Card (floating-point, 7 fields × 8 cols cada):
    #   DELTAT    cols 1-8   E8.0  - time step [s]
    #   TMAX      cols 9-16  E8.0  - end time  [s]
    #   XOPT      cols 17-24 E8.0  - 0=mH; f=Ω@f Hz
    #   COPT      cols 25-32 E8.0  - 0=μF; f=μ℧@f Hz
    #   EPSILN    cols 33-40 E8.0  - matrix singularity ε
    #   TOLMAT    cols 41-48 E8.0  - Y matrix singularity
    #   TSTART    cols 49-56 E8.0  - start time
    #
    # Second Misc Data Card (integer, 10 fields × 8 cols cada):
    #   IOUT IPLOT IDOUBL KSSOUT MAXOUT IPUN MEMSAV ICAT NENERG IPRSUP
    #
    # Defaults para análise transiente típica:
    #   DELTAT=1μs (captura transientes rápidos)
    #   TMAX=0.05s (50ms — vários ciclos 60Hz)
    #   XOPT=COPT=blank (0) → bridge converte H→mH, F→μF
    #     (se setarmos XOPT=60Hz, ATP reinterpretaria valores em
    #      mH como Ω@60Hz, gerando indutância errada)
    #   IOUT=500, IPLOT=1, IDOUBL=1, KSSOUT=1, MAXOUT=1
    #
    # IMPORTANTE: cada campo é EXATAMENTE 8 cols (E8.0 / I8).
    # "5 spaces + 3-char value" para 8 chars total.
    raw_lines = [
        "BEGIN NEW DATA CASE",
        "C  dT  >< Tmax >< Xopt >< Copt ><Epsiln>< Tolmat >< Tstart >",
        # 8+8+8+8+8+8+8 = 56 chars. XOPT/COPT/EPSILN/TOLMAT/TSTART blank
        "   1.E-6     .05",
        # 10 fields × 8 cols = 80 cols. IPRSUP=0 explícito.
        "     500       1       1       1       1       0       0       1       0       0",
        "/BRANCH",
        "BLANK BRANCH",
        "/SWITCH",
        "BLANK SWITCH",
        "/SOURCE",
        "BLANK SOURCE",
        "/OUTPUT",
        "BLANK OUTPUT",
        "BLANK",
        "BEGIN NEW DATA CASE",
        "BLANK",
    ]
    atp = AtpProject(
        file_path="",
        raw_lines=raw_lines,
        # Header inclui BEGIN + comment + TIME + MISC (4 linhas
        # até antes de /BRANCH).
        header=HeaderInfo(raw_lines=raw_lines[:4]),
        tail_lines=raw_lines[12:],
    )
    atp.sections["BRANCH"] = Section(
        name="BRANCH", raw_lines=[raw_lines[4]], start_line=4, end_line=4,
    )
    atp.sections["SWITCH"] = Section(
        name="SWITCH", raw_lines=[raw_lines[6]], start_line=6, end_line=6,
    )
    atp.sections["SOURCE"] = Section(
        name="SOURCE", raw_lines=[raw_lines[8]], start_line=8, end_line=8,
    )

    # Reusar a mesma convenção de chave que o node_coalescer
    gnd_counter = [0]

    for comp in project.components:
        key = _component_key(comp, gnd_counter)
        ctype = comp.type

        if ctype in _IGNORED_TYPES:
            continue

        # 2-terminal: pega n1, n2 dos pinos 0 e 1
        n1 = _node_of(node_map, key, 0)
        n2 = _node_of(node_map, key, 1)

        if ctype == "R":
            atp.branches.append(_convert_resistor(comp, n1, n2))
        elif ctype == "L":
            atp.branches.append(_convert_inductor(comp, n1, n2))
        elif ctype == "C":
            atp.branches.append(_convert_capacitor(comp, n1, n2))
        elif ctype == "Vdc":
            # Source single-terminal: vai para o nó "vivo" (não-GND).
            # v0.91.9: passa node_map para preferir nó mais conectado.
            n = _live_node(n1, n2, node_map)
            atp.sources.append(_convert_vdc(comp, n))
        elif ctype == "Vac":
            n = _live_node(n1, n2, node_map)
            atp.sources.append(_convert_vac(comp, n))
        elif ctype == "Idc":
            n = _live_node(n1, n2, node_map)
            atp.sources.append(_convert_idc(comp, n))
        elif ctype == "Iac":
            n = _live_node(n1, n2, node_map)
            atp.sources.append(_convert_iac(comp, n))
        elif ctype == "Diode":
            atp.switches.append(_convert_diode(comp, n1, n2))
        elif ctype in ("SwIdeal", "Relais"):
            atp.switches.append(_convert_switch_ideal(comp, n1, n2))
        elif ctype == "SwTACS":
            atp.switches.append(_convert_sw_tacs(comp, n1, n2, atp))
        elif ctype == "SM":
            sm = _convert_synchronous_machine(comp, key, node_map, atp)
            if sm is not None:
                _inject_sm_cards(sm, atp)
        elif ctype == "XFMR":
            xfmr = _convert_xfmr(comp, key, node_map, atp)
            if xfmr is not None:
                _inject_xfmr_cards(xfmr, atp)
        elif ctype == "BUS":
            bus = _convert_bus(comp, key, node_map, atp)
            if bus is not None:
                _inject_bus_metadata(bus, atp)
        elif ctype == "MOTOR":
            motor = _convert_motor(comp, key, node_map, atp)
            if motor is not None:
                _inject_motor_metadata(motor, atp)
        elif ctype == "VCB":
            atp.switches.append(_convert_vcb_single_phase(comp, n1, n2, atp))
        elif ctype == "VCB3":
            atp.switches.extend(
                _convert_vcb_three_phase(comp, key, node_map, atp)
            )
        elif ctype == "Thyr":
            atp.switches.append(_convert_thyristor(comp, n1, n2))
        elif ctype == "IGBT":
            atp.switches.append(_convert_igbt(comp, n1, n2))
        elif ctype == "MOSFET":
            atp.switches.append(_convert_mosfet(comp, n1, n2))
        elif ctype in ("Tr", "sTr", "Tr3"):
            nodes = [_node_of(node_map, key, i) for i in range(4)]
            br = _convert_transformer_placeholder(comp, nodes, atp)
            if br is not None:
                atp.branches.append(br)
        elif ctype in ("TLIN", "BERG", "JMARTI"):
            br = _convert_line_placeholder(comp, n1, n2, atp)
            if br is not None:
                atp.branches.append(br)
        elif ctype in ("ZnO", "RNL", "LNL"):
            br = _convert_nonlinear_placeholder(comp, n1, n2, atp)
            if br is not None:
                atp.branches.append(br)
        else:
            atp.warnings.append(
                f"Componente {comp.name!r} tipo {ctype!r} ignorado: "
                "sem mapeamento ATP definido."
            )

    # Popula o dict de nós (consultado pelo validador)
    _populate_nodes(atp)

    # v0.26.0: injeta seção /TACS HYBRID se algum componente TACS
    # tiver expressão válida. Vai antes de /MODELS (TACS define
    # variáveis que MODELS pode consumir).
    _inject_tacs_section_if_needed(atp, project)

    # v0.22.1: injeta seção /MODELS se algum VCB/VCB3 tiver reignição
    # customizada. A seção entra ANTES de /BRANCH (posição canônica no
    # formato ATP-EMTP). Ajusta start_line/end_line de BRANCH/SWITCH/
    # SOURCE para refletir o deslocamento.
    _inject_models_section_if_needed(atp, project)

    return atp


def _extract_tacs_blocks(project: PpProject) -> tuple[list[TacsBlock], list[str]]:
    """
    Coleta blocos TACS de ``project.components``.

    Cada componente do tipo ``TACS`` vira um ``TacsBlock`` com:

    * ``name``  = ``comp.name`` (truncado a 6 chars)
    * ``output`` = ``comp.name`` (mesmo — ATP nomeia a saída pelo
      bloco). Se o nome for > 6 chars, trunca.
    * ``expression`` = ``comp.get(0, "")`` (prop ``expression``).
    * ``inputs`` = variáveis livres detectadas via parse, excluindo
      ``pi`` e ``e``.

    v0.26.5: também coleta PID, Integrator, LowPass, Limiter e
    TSum (.ocomp specs adicionados na sprint), criando os items
    apropriados (TacsTransferFunction / TacsLimiter / TacsSum)
    via os helpers de ``tacs_tf`` / ``tacs_blocks``.

    Retorna a lista (mista) + warnings textuais (expressão
    inválida, validação falhou, etc.).
    """
    items: list = []
    warns: list[str] = []
    for comp in project.components:
        if comp.type == "TACS":
            item = _build_tacs_block_from_comp(comp, warns)
            if item is not None:
                items.append(item)
        elif comp.type == "PID":
            item = _build_pid_from_comp(comp, warns)
            if item is not None:
                items.append(item)
        elif comp.type == "Integrator":
            item = _build_integrator_from_comp(comp, warns)
            if item is not None:
                items.append(item)
        elif comp.type == "LowPass":
            item = _build_lowpass_from_comp(comp, warns)
            if item is not None:
                items.append(item)
        elif comp.type == "Limiter":
            item = _build_limiter_from_comp(comp, warns)
            if item is not None:
                items.append(item)
        elif comp.type == "TSum":
            item = _build_tsum_from_comp(comp, warns)
            if item is not None:
                items.append(item)
    return items, warns


def _build_tacs_block_from_comp(comp, warns: list[str]):
    """TACS.ocomp → TacsBlock. None se inválido."""
    expr = (comp.get(0, "") or "").strip()
    if not expr:
        warns.append(
            f"TACS {comp.name!r}: expressão vazia — bloco descartado."
        )
        return None
    try:
        ast = parse_tacs_expression(expr)
    except SyntaxError as exc:
        warns.append(
            f"TACS {comp.name!r}: expressão inválida ({exc}). "
            "Bloco descartado."
        )
        return None
    inputs = tuple(sorted(collect_variables(ast)))
    name = (comp.name or "TACS")[:6]
    block = TacsBlock(
        name=name,
        expression=expr,
        output=name,
        inputs=inputs,
        initial_value=0.0,
    )
    block_errors = validate_tacs_block(block)
    if block_errors:
        warns.append(
            f"TACS {comp.name!r}: validação falhou — "
            + "; ".join(block_errors) + ". Bloco descartado."
        )
        return None
    return block


def _parse_float_prop(
    comp, idx: int, default: float, label: str, warns: list[str],
) -> Optional[float]:
    """Parse uma prop numérica do componente. Retorna None se erro."""
    raw = (comp.get(idx, "") or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        warns.append(
            f"{comp.type} {comp.name!r}: prop {label}={raw!r} não-numérica."
        )
        return None


def _parse_optional_float(
    comp, idx: int, label: str, warns: list[str],
) -> Optional[float]:
    """Parse uma prop float opcional (vazio = None). Retorna
    sentinel ``-1`` se erro."""
    raw = (comp.get(idx, "") or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        warns.append(
            f"{comp.type} {comp.name!r}: prop {label}={raw!r} não-numérica "
            "(ignorada)."
        )
        return None


def _build_pid_from_comp(comp, warns: list[str]):
    """PID.ocomp → TacsTransferFunction via make_pid."""
    from .tacs_tf import make_pid, validate_tf
    name = (comp.name or "PID")[:6]
    in_sig = ((comp.get(0, "err") or "err").strip() or "err")[:6]
    out_name = ((comp.get(1, name) or name).strip() or name)[:6]
    Kp = _parse_float_prop(comp, 2, 1.0, "Kp", warns)
    Ki = _parse_float_prop(comp, 3, 0.0, "Ki", warns)
    Kd = _parse_float_prop(comp, 4, 0.0, "Kd", warns)
    if None in (Kp, Ki, Kd):
        return None
    out_min = _parse_optional_float(comp, 5, "output_min", warns)
    out_max = _parse_optional_float(comp, 6, "output_max", warns)
    init = _parse_float_prop(comp, 7, 0.0, "initial_output", warns) or 0.0
    tf = make_pid(
        name=name, input_signal=in_sig, output=out_name,
        Kp=Kp, Ki=Ki, Kd=Kd,
        output_min=out_min, output_max=out_max,
        initial_output=init,
    )
    errs = validate_tf(tf)
    if errs:
        warns.append(
            f"PID {comp.name!r}: validação falhou — "
            + "; ".join(errs) + ". Descartado."
        )
        return None
    return tf


def _build_integrator_from_comp(comp, warns: list[str]):
    """Integrator.ocomp → TacsTransferFunction via make_integrator."""
    from .tacs_tf import make_integrator, validate_tf
    name = (comp.name or "INT")[:6]
    in_sig = ((comp.get(0, "u") or "u").strip() or "u")[:6]
    out_name = ((comp.get(1, name) or name).strip() or name)[:6]
    K = _parse_float_prop(comp, 2, 1.0, "K", warns)
    init = _parse_float_prop(comp, 3, 0.0, "initial_output", warns)
    if None in (K, init):
        return None
    out_min = _parse_optional_float(comp, 4, "output_min", warns)
    out_max = _parse_optional_float(comp, 5, "output_max", warns)
    tf = make_integrator(
        name=name, input_signal=in_sig, output=out_name,
        K=K, initial_output=init,
        output_min=out_min, output_max=out_max,
    )
    errs = validate_tf(tf)
    if errs:
        warns.append(
            f"Integrator {comp.name!r}: validação falhou — "
            + "; ".join(errs) + ". Descartado."
        )
        return None
    return tf


def _build_lowpass_from_comp(comp, warns: list[str]):
    """LowPass.ocomp → TacsTransferFunction via make_low_pass."""
    from .tacs_tf import make_low_pass, validate_tf
    name = (comp.name or "LP")[:6]
    in_sig = ((comp.get(0, "u") or "u").strip() or "u")[:6]
    out_name = ((comp.get(1, name) or name).strip() or name)[:6]
    K = _parse_float_prop(comp, 2, 1.0, "K", warns)
    tau = _parse_float_prop(comp, 3, 0.001, "tau", warns)
    if None in (K, tau):
        return None
    if tau <= 0:
        warns.append(
            f"LowPass {comp.name!r}: tau={tau} deve ser > 0. Descartado."
        )
        return None
    tf = make_low_pass(
        name=name, input_signal=in_sig, output=out_name,
        K=K, tau=tau,
    )
    errs = validate_tf(tf)
    if errs:
        warns.append(
            f"LowPass {comp.name!r}: validação falhou — "
            + "; ".join(errs) + ". Descartado."
        )
        return None
    return tf


def _build_limiter_from_comp(comp, warns: list[str]):
    """Limiter.ocomp → TacsLimiter."""
    from .tacs_blocks import TacsLimiter, validate_limiter
    name = (comp.name or "LIM")[:6]
    in_sig = ((comp.get(0, "u") or "u").strip() or "u")[:6]
    out_name = ((comp.get(1, name) or name).strip() or name)[:6]
    out_min = _parse_float_prop(comp, 2, -1.0, "output_min", warns)
    out_max = _parse_float_prop(comp, 3, 1.0, "output_max", warns)
    if None in (out_min, out_max):
        return None
    lim = TacsLimiter(
        name=name, output=out_name, input_signal=in_sig,
        output_min=out_min, output_max=out_max,
    )
    errs = validate_limiter(lim)
    if errs:
        warns.append(
            f"Limiter {comp.name!r}: validação falhou — "
            + "; ".join(errs) + ". Descartado."
        )
        return None
    return lim


def _build_tsum_from_comp(comp, warns: list[str]):
    """TSum.ocomp → TacsSum."""
    from .tacs_blocks import TacsSum, validate_sum
    name = (comp.name or "SUM")[:6]
    out_name = ((comp.get(0, name) or name).strip() or name)[:6]
    inputs: list[tuple[str, float]] = []
    # 4 pares de (signal_name, weight) em props 1..8.
    for i in range(4):
        sig_idx = 1 + i * 2
        w_idx = 2 + i * 2
        sig = (comp.get(sig_idx, "") or "").strip()
        if not sig:
            continue
        w = _parse_float_prop(comp, w_idx, 1.0, f"input{i+1}_weight", warns)
        if w is None:
            continue
        inputs.append((sig[:6], w))
    bias = _parse_float_prop(comp, 9, 0.0, "bias", warns) or 0.0
    if not inputs:
        warns.append(
            f"TSum {comp.name!r}: sem inputs preenchidos — descartado."
        )
        return None
    summer = TacsSum(
        name=name, output=out_name,
        inputs=tuple(inputs), bias=bias,
    )
    errs = validate_sum(summer)
    if errs:
        warns.append(
            f"TSum {comp.name!r}: validação falhou — "
            + "; ".join(errs) + ". Descartado."
        )
        return None
    return summer


def _inject_tacs_section_if_needed(
    atp: AtpProject, project: PpProject,
) -> None:
    """
    Se houver blocos TACS válidos em ``project.components``, insere
    ``/TACS HYBRID … BLANK CARD ENDING TACS`` entre o
    ``BEGIN NEW DATA CASE`` e o resto. Ajusta os índices das seções
    /BRANCH, /SWITCH, /SOURCE.
    """
    items, warns = _extract_tacs_blocks(project)
    for w in warns:
        atp.warnings.append(w)
    if not items:
        return

    section_text = emit_tacs_section(items)
    section_lines = section_text.splitlines()

    INSERT_AT = 1
    shift = len(section_lines)
    atp.raw_lines = (
        atp.raw_lines[:INSERT_AT]
        + section_lines
        + atp.raw_lines[INSERT_AT:]
    )
    for section_name in ("BRANCH", "SWITCH", "SOURCE"):
        section = atp.sections.get(section_name)
        if section is not None and section.start_line >= INSERT_AT:
            section.start_line += shift
            section.end_line += shift
    atp.tail_lines = atp.raw_lines[7 + shift:]
    atp.warnings.append(
        f"TACS: emitidos {len(items)} item(ns) na seção /TACS HYBRID."
    )


def _inject_models_section_if_needed(
    atp: AtpProject, project: PpProject,
) -> None:
    """
    Se algum VCB/VCB3 em ``project.components`` tem parâmetros de
    reignição customizados, insere bloco ``/MODELS ... ENDUSE`` entre
    o ``BEGIN NEW DATA CASE`` e o ``/BRANCH`` em ``atp.raw_lines``.

    Também ajusta ``atp.sections[X].start_line`` / ``end_line`` para
    que a serialização de ``BRANCH/SWITCH/SOURCE`` continue
    referenciando as linhas corretas após o shift.
    """
    models_lines = build_models_section(project.components)
    if not models_lines:
        return

    # Inserção: depois do header (linha 0 = BEGIN NEW DATA CASE),
    # antes de /BRANCH (linha 1 atual).
    INSERT_AT = 1
    shift = len(models_lines)

    atp.raw_lines = (
        atp.raw_lines[:INSERT_AT]
        + models_lines
        + atp.raw_lines[INSERT_AT:]
    )

    # Ajusta os índices das seções subsequentes pelo shift.
    for section_name in ("BRANCH", "SWITCH", "SOURCE"):
        section = atp.sections.get(section_name)
        if section is not None and section.start_line >= INSERT_AT:
            section.start_line += shift
            section.end_line += shift

    # tail_lines também referencia a fatia raw_lines[7:] original;
    # agora deve apontar para a fatia deslocada.
    atp.tail_lines = atp.raw_lines[7 + shift:]


def _live_node(n1: str, n2: str, node_map=None) -> str:
    """
    Para fonte single-terminal: escolhe o nó NÃO-terra E
    EFETIVAMENTE conectado a outros componentes.

    v0.91.9: quando ambos n1 e n2 são não-GND, preferimos o que
    tem MAIS pinos no node_map (= conectado a outros components).
    Isto resolve o bug onde Vac.pin0 (top, dangling) era
    escolhido em vez de Vac.pin1 (bottom, conectado a BUS+R) →
    fonte aparecia desconectada do circuito → ATP erro.

    Heurística:
    1. Se um é GND ('') e outro não → escolhe o não-GND.
    2. Ambos não-GND, node_map disponível → escolhe o com mais
       pinos (mais conectado).
    3. Empate ou node_map ausente → escolhe n1 (preserva
       comportamento legacy).
    """
    # Caso 1: um é GND, outro não
    if n1 and not n2:
        return n1
    if n2 and not n1:
        return n2
    if not n1 and not n2:
        return n2     # ambos GND, retorna vazio (degenerado)
    # Caso 2: ambos não-GND, prefere o mais conectado
    if node_map is not None:
        try:
            count1 = len(node_map.node_to_pins.get(n1, []))
            count2 = len(node_map.node_to_pins.get(n2, []))
            if count2 > count1:
                return n2
            return n1
        except Exception:
            pass
    # Caso 3: empate ou sem node_map → legacy
    return n1


def _populate_nodes(atp: AtpProject) -> None:
    """Popula `AtpProject.nodes` derivando de branches/switches/sources."""
    nodes: dict[str, Node] = {}
    def _touch(name: str, source: str) -> None:
        if not name:
            return
        nd = nodes.setdefault(name, Node(name=name, sources=[]))
        if source not in nd.sources:
            nd.sources.append(source)
    for b in atp.branches:
        _touch(b.node1, "branch")
        _touch(b.node2, "branch")
    for s in atp.switches:
        _touch(s.node1, "switch")
        _touch(s.node2, "switch")
    for src in atp.sources:
        _touch(src.node, "source")
    atp.nodes = nodes
