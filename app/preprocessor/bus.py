"""
app.preprocessor.bus — barramentos elétricos com metadata de
painel (estilo SKM PowerTools Workstation / EasyPower / ETAP).

Conceito
========

Em sistemas de potência industriais, **barramentos** (ou
**painéis**) são pontos de conexão multi-tap que cumprem dois
papéis simultâneos:

1. **Elétrico**: nó zero-impedância que une múltiplos componentes
   (alimentadores, transformadores, cargas, geração).
2. **Físico**: invólucro real (CCM 15kV, switchgear LV, etc.)
   com características relevantes para arc-flash, coordenação,
   manutenção.

No SKM PTW, cada barramento tem um *Equipment Tab* onde o
usuário define:

* Classe de equipamento (CCM, switchgear, painel BT raso/típico).
* Lado de análise: **lineside** (alimentação) vs **loadside**
  (carga).
* Presença de **AFD** (Arc Flash Detection relay): quando
  habilitado, o tempo de extinção do arco cai para ~5–10 ms,
  reduzindo drasticamente a energia incidente.

Esta implementação reproduz esses conceitos para o Olivas, com
integração direta com:

* ``app.standards.nbr17227.EquipmentClass`` (8 tipos de painel).
* ``app.postprocessor.arc_flash.ArcFlashCase`` (cálculo NBR
  17227).
* ``app.preprocessor.bridge_to_atp`` (emite metadata como
  comentários no .atp).

Lineside vs Loadside (NBR 17227 §4.2.4)
========================================

* **Lineside (alimentação)**: ponto de análise antes do
  dispositivo de proteção. Energia incidente baseada em:
    - ``Ibf`` da fonte (concessionária + geradores upstream)
    - Tempo de extinção do dispositivo de **backup**
      (relé upstream → mais lento)
    - Geralmente o **pior caso** — categoria PPE alta.

* **Loadside (carga)**: ponto após o dispositivo de proteção.
  Energia baseada em:
    - Mesmo ``Ibf`` (a falta vê os mesmos componentes)
    - Tempo do dispositivo **local** (mais rápido)
    - Geralmente categoria PPE menor.

AFD (Arc Flash Detection relay)
================================

Sensor óptico (luz do arco) + trip rápido por fibra → reduz
extinção para 5–15 ms tipicamente. Tecnologia ABB REA, Schneider
VAMP 320, GE Multilin AF-2 etc. NBR 17227 §5.1.9.1 menciona
explicitamente "relés de detecção de arco".

Quando ``has_AFD = True``, este módulo override o tempo de
extinção para ``AFD_clearing_time_ms`` (default 10 ms) — sem
substituir a coordenação de proteção principal (51/51N), apenas
adicionando um caminho rápido para faltas internas no painel.

Tipos de barra
==============

* **Single-phase**: 1 nó elétrico, até 8 taps.
* **Three-phase**: 3 nós (A/B/C), até 4 taps (cada tap é 3φ).

MVP v0.27.7 cobre 3-phase com 4 taps; single-phase fica para
sub-sprint.

Referências
============

* SKM PTW Equipment Tab (industry standard).
* IEEE 242:2001 (Buff Book) §15 — bus ratings and protection.
* ABNT NBR 17227:2025 §4.2.4, §5.1.9 — múltiplas fontes,
  AFD/relé de detecção de arco.
* NFPA 70E:2024 Tabela 130.5(C) — categorias PPE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.standards.nbr17227 import EquipmentClass


# ---------------------------------------------------------------------------
# BusComponent
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BusComponent:
    """
    Barramento elétrico com metadata de painel para arc-flash.

    Attributes
    ----------
    bus_id:
        Identificador único do painel (ex: "BUS-A-13.8kV",
        "MCC-101"). Aparece em todos os relatórios e cards ATP.
    rated_voltage_kV:
        Tensão nominal L-L (kV).
    n_phases:
        1 (monofásico) ou 3 (trifásico).
    panel_type:
        Classe do equipamento conforme NBR 17227 / IEEE 1584
        (CCM_15KV, SWITCHGEAR_5KV, LV_PANEL_TYPICAL, etc.).
    is_lineside:
        True se o ponto de análise é antes do dispositivo de
        proteção (pior caso, energia maior). False = loadside.
    has_AFD:
        True se o painel tem AFD (Arc Flash Detection relay).
        Quando True, o tempo de extinção é reduzido para
        ``AFD_clearing_time_ms``.
    AFD_clearing_time_ms:
        Tempo de extinção pelo AFD (default 10 ms — tecnologia
        atual ABB REA / Schneider VAMP / GE AF-2).
    n_taps:
        Número de pontos de conexão (taps) na barra. Para 3φ,
        cada tap é 3φ. Default 4.
    description:
        Texto livre (ex: "Painel principal 13.8 kV — CCM A").
    """

    bus_id: str
    rated_voltage_kV: float
    n_phases: int = 3
    panel_type: EquipmentClass = EquipmentClass.SWITCHGEAR_5KV
    is_lineside: bool = True
    has_AFD: bool = False
    AFD_clearing_time_ms: float = 10.0
    n_taps: int = 4
    description: str = ""

    @property
    def n_pins(self) -> int:
        """
        Número total de pinos do componente. Para 3φ, cada tap
        tem 3 pinos (A/B/C); para 1φ, cada tap tem 1 pino.
        """
        return self.n_taps * self.n_phases


def validate_bus(b: BusComponent) -> list[str]:
    """
    Valida a configuração de um barramento.

    Verifica:

    * ``bus_id`` não-vazio.
    * Tensão > 0.
    * n_phases ∈ {1, 3}.
    * n_taps em 2..8 (faixa prática).
    * AFD_clearing_time_ms > 0 quando has_AFD = True.
    * Coerência tensão × panel_type (ex: SWITCHGEAR_15KV vs
      tensão > 5 kV, LV_PANEL vs tensão ≤ 1 kV).
    """
    errors: list[str] = []

    if not b.bus_id:
        errors.append("bus_id vazio")

    if b.rated_voltage_kV <= 0:
        errors.append(
            f"rated_voltage_kV deve ser > 0 (achado {b.rated_voltage_kV})"
        )

    if b.n_phases not in (1, 3):
        errors.append(
            f"n_phases deve ser 1 ou 3 (achado {b.n_phases})"
        )

    if not (2 <= b.n_taps <= 8):
        errors.append(
            f"n_taps deve estar em [2, 8] (achado {b.n_taps})"
        )

    if b.has_AFD and b.AFD_clearing_time_ms <= 0:
        errors.append(
            f"AFD habilitado mas AFD_clearing_time_ms = "
            f"{b.AFD_clearing_time_ms} <= 0"
        )

    # Coerência tensão × panel_type
    voltage = b.rated_voltage_kV
    pt = b.panel_type
    lv_panels = (
        EquipmentClass.LV_PANEL_SHALLOW,
        EquipmentClass.LV_PANEL_TYPICAL,
        EquipmentClass.LV_SWITCHGEAR,
        EquipmentClass.CABLE_JUNCTION_BOX,
    )
    mv_5kv = (
        EquipmentClass.CCM_5KV,
        EquipmentClass.SWITCHGEAR_5KV,
    )
    mv_15kv = (
        EquipmentClass.CCM_15KV,
        EquipmentClass.SWITCHGEAR_15KV,
    )
    if pt in lv_panels and voltage > 1.0:
        errors.append(
            f"panel_type={pt.value} é LV mas V_LL={voltage} kV > 1 kV"
        )
    if pt in mv_5kv and not (1.0 < voltage <= 5.0):
        errors.append(
            f"panel_type={pt.value} é 5kV class mas V_LL={voltage} kV "
            "fora de (1, 5] kV"
        )
    if pt in mv_15kv and not (5.0 < voltage <= 15.0):
        errors.append(
            f"panel_type={pt.value} é 15kV class mas V_LL={voltage} kV "
            "fora de (5, 15] kV"
        )

    return errors


# ---------------------------------------------------------------------------
# Conversão para arc-flash analysis
# ---------------------------------------------------------------------------


def effective_clearing_time_ms(
    bus: BusComponent,
    coordination_clearing_time_ms: float,
) -> float:
    """
    Calcula o tempo efetivo de extinção considerando AFD.

    * Sem AFD: retorna o tempo da coordenação (51/51N do relé
      upstream).
    * Com AFD: retorna ``min(AFD_time, coordination_time)`` — o
      AFD não substitui a proteção principal, apenas adiciona
      um caminho rápido.

    Parameters
    ----------
    bus:
        Configuração do barramento.
    coordination_clearing_time_ms:
        Tempo de extinção do esquema de proteção principal
        (vindo de ``app.postprocessor.relay_coordination``).
    """
    if bus.has_AFD:
        return min(bus.AFD_clearing_time_ms, coordination_clearing_time_ms)
    return coordination_clearing_time_ms


def bus_to_arc_flash_case(
    bus: BusComponent,
    bolted_fault_current_kA: float,
    coordination_clearing_time_ms: float,
    electrode_config=None,
):
    """
    Constrói um ``ArcFlashCase`` a partir do BusComponent +
    estudos de SC e coordenação.

    Esta função é o ponto de integração entre a parte topológica
    (Bus do schematic) e o cálculo NBR 17227 (arc-flash).

    Parameters
    ----------
    bus:
        Barramento com metadata.
    bolted_fault_current_kA:
        Corrente de falta franca trifásica no barramento (vinda
        do estudo IEC 60909 — ``app.postprocessor.short_circuit``).
    coordination_clearing_time_ms:
        Tempo de extinção do dispositivo de proteção principal
        (vindo do estudo de coordenação).
    electrode_config:
        Configuração de eletrodos (default VCB para painéis
        fechados; HOA para ar livre etc.). Se None, usa VCB.

    Returns
    -------
    ArcFlashCase
        Pronto para passar a ``calculate_arc_flash``.
    """
    # Imports locais (evita ciclo)
    from app.postprocessor.arc_flash import ArcFlashCase
    from app.standards.nbr17227 import ElectrodeConfig

    if electrode_config is None:
        electrode_config = ElectrodeConfig.VCB

    # Tempo efetivo (com AFD se aplicável)
    T_ms = effective_clearing_time_ms(bus, coordination_clearing_time_ms)

    return ArcFlashCase(
        bus_name=bus.bus_id,
        rated_voltage_kV=bus.rated_voltage_kV,
        bolted_fault_current_kA=bolted_fault_current_kA,
        arc_clearing_time_ms=T_ms,
        equipment_class=bus.panel_type,
        electrode_config=electrode_config,
    )


# ---------------------------------------------------------------------------
# Emissão de metadata para .atp (comentários)
# ---------------------------------------------------------------------------


def emit_bus_metadata_lines(bus: BusComponent) -> list[str]:
    """
    Emite comentários ATP descrevendo o barramento como um
    "painel" — útil para auditoria do .atp e documentação.

    Estrutura:

    ::

        C ===============================
        C BUS / PANEL: <bus_id>
        C   Voltage: <V> kV (<n_phases>φ)
        C   Panel type: <type>
        C   Side: lineside | loadside
        C   AFD: enabled (T = <ms> ms) | disabled
        C   Description: <text>
        C ===============================
    """
    side = "lineside" if bus.is_lineside else "loadside"
    afd_str = (
        f"enabled (T_AFD = {bus.AFD_clearing_time_ms:.1f} ms)"
        if bus.has_AFD else "disabled"
    )
    lines = [
        "C ===============================",
        f"C BUS / PANEL: {bus.bus_id}",
        f"C   Voltage: {bus.rated_voltage_kV:.3f} kV ({bus.n_phases}φ)",
        f"C   Panel type: {bus.panel_type.value}",
        f"C   Side: {side}",
        f"C   AFD: {afd_str}",
        f"C   Taps: {bus.n_taps} ({bus.n_pins} pins total)",
    ]
    if bus.description:
        lines.append(f"C   Description: {bus.description}")
    lines.append("C ===============================")
    return lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_default_mv_switchgear(
    bus_id: str, voltage_kV: float = 13.8,
    has_AFD: bool = False,
) -> BusComponent:
    """
    Helper: switchgear MT 5–15 kV típico (4 taps, 3φ, lineside).

    Auto-classifica o ``panel_type`` baseado na tensão.
    """
    if 1.0 < voltage_kV <= 5.0:
        pt = EquipmentClass.SWITCHGEAR_5KV
    else:
        pt = EquipmentClass.SWITCHGEAR_15KV
    return BusComponent(
        bus_id=bus_id,
        rated_voltage_kV=voltage_kV,
        n_phases=3,
        panel_type=pt,
        is_lineside=True,
        has_AFD=has_AFD,
        n_taps=4,
        description=(
            f"Switchgear MT {voltage_kV} kV — barramento principal "
            f"({'AFD habilitado' if has_AFD else 'sem AFD'})."
        ),
    )


def make_default_lv_panel(
    bus_id: str, voltage_kV: float = 0.480,
    has_AFD: bool = False,
) -> BusComponent:
    """
    Helper: painel BT (≤ 1 kV) típico (4 taps, 3φ, loadside).

    Default: LV_PANEL_TYPICAL.
    """
    return BusComponent(
        bus_id=bus_id,
        rated_voltage_kV=voltage_kV,
        n_phases=3,
        panel_type=EquipmentClass.LV_PANEL_TYPICAL,
        is_lineside=False,   # LV típico é loadside (cargas)
        has_AFD=has_AFD,
        n_taps=4,
        description=(
            f"Painel BT {voltage_kV*1000:.0f} V — distribuição."
        ),
    )


def make_default_motor_control_center(
    bus_id: str, voltage_kV: float = 4.16,
    has_AFD: bool = True,   # CCMs modernos comumente têm AFD
) -> BusComponent:
    """
    Helper: CCM (Motor Control Center) — sub-distribuição de
    motores. Default 4.16 kV com AFD habilitado.
    """
    if 1.0 < voltage_kV <= 5.0:
        pt = EquipmentClass.CCM_5KV
    elif 5.0 < voltage_kV <= 15.0:
        pt = EquipmentClass.CCM_15KV
    else:
        pt = EquipmentClass.LV_PANEL_TYPICAL
    return BusComponent(
        bus_id=bus_id,
        rated_voltage_kV=voltage_kV,
        n_phases=3,
        panel_type=pt,
        is_lineside=False,
        has_AFD=has_AFD,
        n_taps=4,
        description=f"CCM {voltage_kV} kV — controle de motores.",
    )
