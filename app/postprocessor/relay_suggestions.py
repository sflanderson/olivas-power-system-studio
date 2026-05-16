"""
app.postprocessor.relay_suggestions — geração automática de
sugestões de ajustes para relés de proteção, com base em:

* Tipo de painel (BusComponent.panel_type) — define se é
  feeder, MCC, switchgear, etc.
* Resultado do SC (Ik'', ip via IEC 60909-0).
* Corrente de carga (I_load) — vem do estudo de fluxo de
  potência (default = I_n do equipamento se não fornecido).
* Catálogo de relés comerciais (``app.standards.relay_models``).

Princípios IEEE 242 (Buff Book) §15
=====================================

Para coordenação seletiva, a regra geral é:

* **Pickup 51** (tempo): 1.20–1.30× I_load_max (margem para
  carga + harmônicas + corrente de partida temporária).
* **Pickup 50** (instantâneo): ≥ 0.80× I_thru_max (corrente
  através do equipamento sem ser falta — geralmente 0.8× Ik''
  para garantir que opere em faltas francas).
* **Pickup 50/51N** (neutro): tipicamente 10–30% da pickup
  de fase, calibrada para detectar falta à terra (10% Ipick =
  10% I_load).
* **TMS 51**: escalonado por nível hierárquico — main mais
  lento, feeders progressivamente mais rápidos. 0.5 / 0.3 / 0.1
  é uma escala típica.
* **Curva 51**:
    - IEC SI (Standard Inverse): geral distribuição.
    - IEC VI (Very Inverse): mais seletividade em alta corrente.
    - IEC EI (Extremely Inverse): motores (suporta partida).

Aplicações específicas
=======================

* **Switchgear principal** (lineside): 51 main, TMS 0.5+,
  pickup 1.25 × I_n.
* **Feeder branch**: 51 com TMS reduzido (~0.2), pickup
  1.25 × I_load_branch.
* **MCC (Motor Control Center)**: 51LR (locked rotor) +
  curva EI para suportar inrush de motor.
* **Transformer protection**: 51 + 87T, pickup 1.25× I_n;
  além de bloqueio 2ª harmônica (68F2).

Modelos de relé sugeridos (por aplicação)
==========================================

Heurística Olivas (auto-seleção):

* **Feeder MV (1-15 kV)**: SEL-751 (preferred) ou ABB-REF615.
* **Feeder LV**: Schneider-P3U10 (econômico) ou P3U30.
* **CCM**: ABB-REF615 ou Schneider-P3U30.
* **Transformer**: ABB-RET615 (87T nativo) ou Schneider-P3U30.
* **Universal**: Schneider-P3U30 (34 funções).

Referências
============

* IEEE Std 242-2001 (Buff Book) §15 — coordination of
  protective devices.
* IEEE C37.91-2008 — transformer protection.
* IEEE C37.96-2012 — motor protection.
* IEEE C37.113-2015 — transmission line protection.
* SEL-751 / ABB RE_615 / Schneider P3U manuals (LIBRARY/
  library_relay/).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from app.preprocessor.bus import BusComponent
from app.standards.iec60255 import (
    CurveStandard, IecCurveType, IeeeCurveType, TcCurveSetting,
)
from app.standards.nbr17227 import EquipmentClass
from app.standards.relay_models import (
    ABB_REF615, ABB_RET615, RELAY_MODELS_REGISTRY,
    RelayModel, SCHNEIDER_P3U10, SCHNEIDER_P3U30, SEL_751,
)


# ---------------------------------------------------------------------------
# Application classification
# ---------------------------------------------------------------------------


def classify_bus_application(bus: BusComponent) -> str:
    """
    Classifica a aplicação do barramento para escolher heurística
    de ajustes:

    * ``"main_switchgear"`` — barramento principal (lineside)
      lado MT/AT.
    * ``"feeder_branch"`` — alimentador derivado (loadside).
    * ``"motor_control_center"`` — CCM.
    * ``"transformer"`` — barramento de transformador.
    * ``"lv_panel"`` — painel BT.
    """
    pt = bus.panel_type
    if pt in (
        EquipmentClass.SWITCHGEAR_15KV, EquipmentClass.SWITCHGEAR_5KV,
    ):
        return (
            "main_switchgear" if bus.is_lineside
            else "feeder_branch"
        )
    if pt in (
        EquipmentClass.CCM_15KV, EquipmentClass.CCM_5KV,
    ):
        return "motor_control_center"
    if pt in (
        EquipmentClass.LV_PANEL_SHALLOW, EquipmentClass.LV_PANEL_TYPICAL,
        EquipmentClass.LV_SWITCHGEAR,
    ):
        return "lv_panel"
    if pt == EquipmentClass.CABLE_JUNCTION_BOX:
        return "feeder_branch"
    return "feeder_branch"


def select_default_relay_model(
    bus: BusComponent, application: str,
) -> RelayModel:
    """
    Auto-seleciona um RelayModel apropriado para a aplicação.

    Heurística:

    * Transformer + 87T → ABB-RET615 (único com 87T+REF nativo).
    * Main switchgear MV → SEL-751 (industry-standard feeder).
    * Feeder branch MV → ABB-REF615.
    * MCC → ABB-REF615.
    * LV panel → Schneider-P3U10 (econômico).

    Caller pode override usando ``RELAY_MODELS_REGISTRY`` direto.
    """
    if application == "transformer":
        return ABB_RET615
    if application == "main_switchgear":
        return SEL_751
    if application == "feeder_branch":
        return ABB_REF615
    if application == "motor_control_center":
        return ABB_REF615
    if application == "lv_panel":
        return SCHNEIDER_P3U10
    return SCHNEIDER_P3U30   # universal fallback


# ---------------------------------------------------------------------------
# RelaySuggestion
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RelaySuggestion:
    """
    Sugestão de ajustes para um relé instalado no barramento.

    Reúne:
    * Modelo recomendado (do registry).
    * Pickups das funções 50/51/50N/51N.
    * Curvas TC sugeridas (51 e 51N).
    * Rationale + referências normativas.

    Os valores são **sugestões iniciais** baseadas em IEEE 242
    §15. O usuário deve refinar via estudo de coordenação
    completo (``app.postprocessor.relay_coordination``).
    """

    bus_id: str
    application: str             # "main_switchgear", etc.
    relay_model_id: str          # "SEL-751", "ABB-REF615", ...
    relay_manufacturer: str
    relay_application_target: str   # do RelayModel.application

    # Carga assumida
    rated_current_A: float       # I_n base do estudo
    load_current_assumed_A: float

    # SC (vindo do pipeline)
    Ik_pp_kA: float

    # Pickups sugeridas
    pickup_51_A: float           # 51 fase (time-delayed)
    pickup_51_per_in: float      # múltiplo de I_n
    pickup_50_A: float           # 50 fase (instantâneo)
    pickup_50_per_in: float
    pickup_51N_A: float          # 51N neutro (time)
    pickup_50N_A: float          # 50N neutro (instant)

    # Curvas TC
    curve_51_standard: str       # "IEC" / "IEEE"
    curve_51_type: str           # "SI", "VI", "EI", etc.
    tms_51: float                # IEC TMS (ou IEEE TD)

    # Tempo definido
    delay_50_ms: float           # tipicamente 0–50 ms

    # Outros
    has_50BF: bool               # breaker failure recomendado
    has_87: bool                 # diferencial recomendado
    has_AFD_recommended: bool

    # Rationale + refs
    rationale: tuple[str, ...]
    references: tuple[str, ...]

    # ------------------------------------------------------------------
    # Vendor-specific output formats (v0.27.7.10)
    # ------------------------------------------------------------------

    def to_vendor_format(self) -> str:
        """
        Retorna os ajustes no formato textual do fabricante,
        pronto para colar/digitar na ferramenta de configuração:

        * **SEL-751** → comandos ``SET <setting>=<value>`` (formato
          QuickSet / ASCII command interface).
        * **ABB REF615/RET615** → blocos function-block do PCM600.
        * **Schneider P3U** → blocos Easergy Pro com seções por
          stage.

        Caller pode integrar este texto em laudo / memorial /
        ordem de serviço.
        """
        manuf = self.relay_manufacturer
        if manuf.startswith("SEL"):
            return self._to_sel_format()
        if manuf.startswith("ABB"):
            return self._to_abb_format()
        if "Schneider" in manuf:
            return self._to_schneider_format()
        return self._to_generic_format()

    def _to_sel_format(self) -> str:
        """
        Formato SEL-751 (QuickSet / ASCII interface).

        Convenção do manual SEL-751:

        * ``50P1P`` — Phase 1 Instantaneous Overcurrent Pickup (A primary)
        * ``51P1P`` — Phase 1 Time-Overcurrent Pickup (A primary)
        * ``51P1C`` — Phase 1 Curve (U1..U5, C1..C5)
        * ``51P1TD`` — Phase 1 Time Dial (IEEE) ou TMS (IEC)
        * ``50G1P`` / ``51G1P`` — Ground (51G1C, 51G1TD análogos)

        Curvas IEC mapeadas:
        * SI → C1, VI → C2, EI → C3, LTI → C4, Short Inv → C5

        Curvas IEEE:
        * U1 (Moderately Inverse), U2 (Inverse/Very), U3 (Very/Ext)
        """
        # Mapeamento curva → código SEL
        if self.curve_51_standard == "IEC":
            sel_curve = {
                "SI": "C1", "VI": "C2", "EI": "C3", "LTI": "C4",
            }.get(self.curve_51_type, "C1")
        else:
            sel_curve = {
                "U1": "U1", "U2": "U2", "U3": "U3",
                "CO8": "U4", "CO2": "U5",
            }.get(self.curve_51_type, "U2")

        td_label = "TD" if self.curve_51_standard != "IEC" else "TD (TMS)"
        lines = [
            "=== SEL-751 Settings (paste into QuickSet ASCII) ===",
            "GROUP 1 — Phase + Ground Time/Inst Overcurrent",
            "",
            f"50P1P = {self.pickup_50_A:.1f}      "
            "; 50 Phase 1 instantaneous pickup (A primary)",
            f"50P1D = {self.delay_50_ms/1000.0:.3f}     "
            "; 50 Phase 1 delay (s)",
            f"51P1P = {self.pickup_51_A:.1f}       "
            "; 51 Phase 1 time pickup (A primary)",
            f"51P1C = {sel_curve}             "
            f"; 51 Phase 1 curve ({self.curve_51_standard} "
            f"{self.curve_51_type})",
            f"51P1{('TD' if self.curve_51_standard == 'IEC' else 'TD')}"
            f" = {self.tms_51:.3f}     "
            f"; 51 Phase 1 {td_label}",
            "",
            f"50G1P = {self.pickup_50N_A:.1f}      "
            "; 50G ground inst pickup (A)",
            f"51G1P = {self.pickup_51N_A:.1f}       "
            "; 51G ground time pickup (A)",
            f"51G1C = {sel_curve}             "
            "; 51G ground curve",
            f"51G1TD = {self.tms_51:.3f}     "
            "; 51G ground TD",
        ]
        if self.has_50BF:
            lines.extend([
                "",
                "50BF1P = " + f"{self.pickup_50_A * 0.9:.1f}     "
                "; 50BF backup pickup (90% of 50)",
                "BFD1 = 0.150         ; 50BF time delay (150 ms typical)",
            ])
        if self.has_AFD_recommended:
            lines.extend([
                "",
                "; ===== ARC-FLASH DETECTION (AFD) =====",
                "; Recomenda-se SEL-751A com AFR (Arc-Flash Reduction)",
                "; ou módulo SEL-751 + AF-2 sensor óptico.",
                "; Configurar com tempo de extinção alvo ≤ 15 ms.",
            ])
        return "\n".join(lines)

    def _to_abb_format(self) -> str:
        """
        Formato ABB Relion 615 (PCM600 / SCT).

        Convenção do manual ABB:

        * ``PHHPTOC1`` — Phase High-set Overcurrent (50)
        * ``PHIPTOC1`` — Phase Inverse Time Overcurrent (51)
        * ``EFHPTOC1`` — Earth-Fault High-set (50N)
        * ``EFLPTOC1`` — Earth-Fault Low-set (51N)
        """
        # Mapeamento curva → string ABB
        if self.curve_51_standard == "IEC":
            abb_curve = {
                "SI": "IEC Norm Inv",
                "VI": "IEC Very Inv",
                "EI": "IEC Ext Inv",
                "LTI": "IEC Long Inv",
            }.get(self.curve_51_type, "IEC Norm Inv")
        else:
            abb_curve = {
                "U1": "ANSI Mod Inv",
                "U2": "ANSI Very Inv",
                "U3": "ANSI Ext Inv",
            }.get(self.curve_51_type, "ANSI Mod Inv")

        lines = [
            "=== ABB Relion 615 Settings (PCM600 / SCT) ===",
            "Function blocks for OC protection:",
            "",
            "[PHHPTOC1] — Phase High-set Overcurrent (50)",
            f"  PickupOpVal     = {self.pickup_50_A:.1f} A",
            f"  OperateDelay    = {self.delay_50_ms:.0f} ms",
            f"  TripBlockMode   = Off",
            "",
            "[PHIPTOC1] — Phase Inverse Time Overcurrent (51)",
            f"  PickupOpVal     = {self.pickup_51_A:.1f} A",
            f"  CurveType       = \"{abb_curve}\"",
            f"  TimeMultiplier  = {self.tms_51:.3f}",
            "",
            "[EFHPTOC1] — Earth-Fault High-set (50N)",
            f"  PickupOpVal     = {self.pickup_50N_A:.1f} A",
            f"  OperateDelay    = {self.delay_50_ms:.0f} ms",
            "",
            "[EFLPTOC1] — Earth-Fault Inverse Time (51N)",
            f"  PickupOpVal     = {self.pickup_51N_A:.1f} A",
            f"  CurveType       = \"{abb_curve}\"",
            f"  TimeMultiplier  = {self.tms_51:.3f}",
        ]
        if self.has_50BF:
            lines.extend([
                "",
                "[CCBRBRF1] — Breaker Failure (50BF)",
                f"  PickupCurr      = {self.pickup_50_A * 0.9:.1f} A",
                "  CbFailTimerSet  = 150 ms",
            ])
        if self.has_87:
            lines.extend([
                "",
                "[T2WPDIF1 / T3WPDIF1] — Differential (87T)",
                "  Recomendar configuração separada via ABB",
                "  RET615 (já tem 87T+REF nativos).",
            ])
        if self.has_AFD_recommended:
            lines.extend([
                "",
                "; ===== AFD Recommendation =====",
                "; ABB REA arc-flash protection scheme:",
                "; - Optical sensor (REA 101/103/105)",
                "; - Connected to REJ603 / REF615 binary input",
                "; - Trip time target ≤ 12 ms",
            ])
        return "\n".join(lines)

    def _to_schneider_format(self) -> str:
        """
        Formato Schneider Easergy P3U (Easergy Pro).

        Convenção do manual P3U:

        * ``I>>>`` — 50 Phase Inst (alta atuação)
        * ``I>>``  — 50 Phase Inst (média)
        * ``I>``   — 51 Phase Time
        * ``I0>``  — 51N Earth time
        * ``I0>>`` — 50N Earth inst
        """
        # Mapeamento curva → string Schneider
        if self.curve_51_standard == "IEC":
            sch_curve = {
                "SI": "IEC NI",
                "VI": "IEC VI",
                "EI": "IEC EI",
                "LTI": "IEC LTI",
            }.get(self.curve_51_type, "IEC NI")
        else:
            sch_curve = {
                "U1": "IEEE MI",
                "U2": "IEEE VI",
                "U3": "IEEE EI",
            }.get(self.curve_51_type, "IEEE MI")

        lines = [
            "=== Schneider Easergy P3U Settings (Easergy Pro) ===",
            "",
            "[Stage 1 — Phase Time-OC (I>, ANSI 51)]",
            f"  Pickup          = {self.pickup_51_A:.1f} A",
            f"  Curve           = {sch_curve}",
            f"  Time multiplier = {self.tms_51:.3f}",
            "",
            "[Stage 2 — Phase Inst (I>>, ANSI 50)]",
            f"  Pickup          = {self.pickup_50_A:.1f} A",
            f"  Delay           = {self.delay_50_ms:.0f} ms",
            "",
            "[Stage 1 — Earth Time-OC (I0>, ANSI 51N)]",
            f"  Pickup          = {self.pickup_51N_A:.1f} A",
            f"  Curve           = {sch_curve}",
            f"  Time multiplier = {self.tms_51:.3f}",
            "",
            "[Stage 2 — Earth Inst (I0>>, ANSI 50N)]",
            f"  Pickup          = {self.pickup_50N_A:.1f} A",
            f"  Delay           = {self.delay_50_ms:.0f} ms",
        ]
        if self.has_50BF:
            lines.extend([
                "",
                "[CBFP — Breaker Failure (ANSI 50BF)]",
                f"  Pickup          = {self.pickup_50_A * 0.9:.1f} A",
                "  Time delay      = 150 ms",
            ])
        if self.has_AFD_recommended:
            lines.extend([
                "",
                "; ===== Schneider VAMP 320 / VAMP 50 (AFD) =====",
                "; Sensor de arco óptico VAMP integrado a P3U30",
                "; via binary input + custom logic. Trip ≤ 10 ms.",
            ])
        return "\n".join(lines)

    def _to_generic_format(self) -> str:
        """Fallback genérico — formato chave-valor."""
        return self.summary()

    @property
    def tc_curve_51(self) -> TcCurveSetting:
        """Reconstrói o TcCurveSetting da função 51."""
        if self.curve_51_standard == "IEC":
            iec_curve = IecCurveType(self.curve_51_type)
            return TcCurveSetting(
                standard=CurveStandard.IEC,
                pickup_A=self.pickup_51_A,
                iec_curve=iec_curve,
                tms=self.tms_51,
            )
        ieee_curve = IeeeCurveType(self.curve_51_type)
        return TcCurveSetting(
            standard=CurveStandard.IEEE,
            pickup_A=self.pickup_51_A,
            ieee_curve=ieee_curve,
            time_dial=self.tms_51,
        )

    def summary(self) -> str:
        """Texto formatado do bloco de relé."""
        lines = [
            f"  Bus: {self.bus_id}  ({self.application})",
            f"  Relay: {self.relay_model_id} "
            f"({self.relay_manufacturer})",
            f"  Rated I_n = {self.rated_current_A:.1f} A,  "
            f"Load assumed = {self.load_current_assumed_A:.1f} A",
            f"  Ik''       = {self.Ik_pp_kA:.3f} kA",
            "",
            "  Pickups:",
            f"    51   (phase, time)     = "
            f"{self.pickup_51_A:.1f} A  "
            f"({self.pickup_51_per_in:.2f} pu In)",
            f"    50   (phase, instant)  = "
            f"{self.pickup_50_A:.1f} A  "
            f"({self.pickup_50_per_in:.2f} pu In)",
            f"    51N  (neutral, time)   = "
            f"{self.pickup_51N_A:.1f} A",
            f"    50N  (neutral, instant)= "
            f"{self.pickup_50N_A:.1f} A",
            "",
            "  Curve 51:",
            f"    Standard: {self.curve_51_standard} {self.curve_51_type}",
            f"    {'TMS' if self.curve_51_standard == 'IEC' else 'TD'} = "
            f"{self.tms_51:.3f}",
            f"    Delay 50: {self.delay_50_ms:.0f} ms",
            "",
            "  Recomendações:",
            f"    50BF (breaker failure): "
            f"{'sim' if self.has_50BF else 'não'}",
            f"    87 (differential):     "
            f"{'sim' if self.has_87 else 'não'}",
            f"    AFD (arc detection):   "
            f"{'sim' if self.has_AFD_recommended else 'não'}",
            "",
            "  Rationale:",
        ]
        for r in self.rationale:
            lines.append(f"    • {r}")
        if self.references:
            lines.append("")
            lines.append("  References:")
            for ref in self.references:
                lines.append(f"    [{ref}]")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Suggestion engine
# ---------------------------------------------------------------------------


def _rated_current_for_bus(bus: BusComponent, S_load_MVA: float) -> float:
    """I_n = S / (√3 · V_LL) em A."""
    return (
        S_load_MVA * 1.0e6
        / (math.sqrt(3.0) * bus.rated_voltage_kV * 1.0e3)
    )


def suggest_settings_for_bus(
    bus: BusComponent,
    Ik_pp_kA: float,
    load_S_MVA: Optional[float] = None,
    relay_model: Optional[RelayModel] = None,
    pickup_51_factor: float = 1.25,
    pickup_50_factor: float = 0.80,
    tms_51: Optional[float] = None,
    *,
    grounding_type: str = "solidly_grounded",
    pickup_51N_factor: Optional[float] = None,
) -> RelaySuggestion:
    """
    Gera sugestão de ajustes para o relé do barramento.

    Heurística IEEE 242 §15 / NFPA 70E + manuais dos fabricantes:

    * **51** (phase time): pickup = ``factor × I_n`` (default
      1.25). Curva selecionada por aplicação (SI geral, EI motor).
    * **50** (phase instant): pickup = ``factor × Ik''`` (default
      0.80). Garante operação em faltas francas próximas.
    * **51N**: depende de ``grounding_type`` (v0.28.0-PRO):
      - ``solidly_grounded`` (TN): 10% do pickup 51 (default).
      - ``resistance_grounded`` (TT/NGR): 30% do pickup 51.
      - ``impedance_grounded`` / ``ungrounded``: 50% pickup 51.
      Override via ``pickup_51N_factor`` se necessário.
    * **50N**: 50% do pickup 50.
    * **TMS 51**: 0.5 (main), 0.3 (sec), 0.1 (load) — escalonado.

    Parameters
    ----------
    bus:
        Barramento com metadata.
    Ik_pp_kA:
        Corrente de SC inicial simétrica (kA RMS) — vinda do
        IEC 60909-0.
    load_S_MVA:
        Potência de carga (MVA) para calcular I_n base.

        .. warning::
            Se ``None``, usa heurística ``Ik''/20`` (assume
            Z_pu=5%). v0.28.0-PRO emite **WARNING CRÍTICO**
            no rationale do relatório quando isso ocorre — para
            painéis CCM com Z_pu=15-25%, a heurística estima
            I_n 3-5× maior que real, levando a pickup_51 alto
            demais e potencial falha de coordenação.
            **Sempre forneça load_S_MVA explícito em laudo final.**
    relay_model:
        Override do modelo de relé. Se None, auto-seleção.
    pickup_51_factor:
        Multiplicador do I_n para pickup 51. Default 1.25.
    pickup_50_factor:
        Fração de Ik'' para pickup 50. Default 0.80.
    tms_51:
        TMS (IEC) ou Time Dial (IEEE) para 51. Se None,
        seleção por aplicação.
    grounding_type:
        ``solidly_grounded`` / ``resistance_grounded`` /
        ``impedance_grounded`` / ``ungrounded`` /
        ``resonant_grounded``. Determina pickup_51N por default.
    pickup_51N_factor:
        Override explícito do fator (fração de pickup 51).

    Returns
    -------
    RelaySuggestion
    """
    # 1) Aplicação + relay model
    application = classify_bus_application(bus)
    if relay_model is None:
        relay_model = select_default_relay_model(bus, application)

    # 2) Carga base — heurística se não fornecida
    heuristic_load_warning: Optional[str] = None
    if load_S_MVA is None:
        # Rule of thumb: I_n ≈ Ik'' / 20 (i.e., Z_pu ≈ 5%)
        I_n_kA_default = Ik_pp_kA / 20.0
        I_n_A = I_n_kA_default * 1000.0
        # Reconstrói S a partir de I_n
        S_load_MVA = (
            I_n_A * math.sqrt(3.0) * bus.rated_voltage_kV / 1000.0
        )
        # v0.28.0-PRO P2.7: warning crítico (heurística tóxica)
        heuristic_load_warning = (
            "ATENÇÃO: load_S_MVA não fornecido. Usando heurística "
            f"Ik''/20 → I_n estimado = {I_n_A:.1f} A "
            f"(S_load = {S_load_MVA:.2f} MVA assumido). "
            "Para CCM com Z_pu = 15-25%, I_n REAL pode ser "
            "3-5× MENOR que esta estimativa, fazendo pickup_51 "
            "ficar muito alto e FALHANDO coordenação. "
            "Sempre forneça load_S_MVA explícito em laudo final."
        )
    else:
        S_load_MVA = load_S_MVA
        I_n_A = _rated_current_for_bus(bus, S_load_MVA)

    load_current_assumed_A = I_n_A

    # 3) Pickups
    pickup_51_A = pickup_51_factor * I_n_A
    pickup_50_A = pickup_50_factor * Ik_pp_kA * 1000.0

    # v0.28.0-PRO P2.9: pickup_51N depende do tipo de aterramento.
    if pickup_51N_factor is None:
        grounding_factors = {
            "solidly_grounded": 0.10,         # TN
            "resistance_grounded": 0.30,      # TT com R_N
            "impedance_grounded": 0.50,       # IT
            "ungrounded": 0.50,
            "resonant_grounded": 0.05,        # Petersen — corrente quase nula
        }
        pickup_51N_factor = grounding_factors.get(grounding_type, 0.10)

    pickup_51N_A = pickup_51N_factor * pickup_51_A
    # 50N: 50% do pickup 50
    pickup_50N_A = 0.50 * pickup_50_A

    # 4) Curve selection por aplicação
    if application == "motor_control_center":
        # EI suporta inrush de partida sem trip falso
        curve_std = "IEC"
        curve_type = "EI"
        tms_def = 0.10 if tms_51 is None else tms_51
    elif application == "transformer":
        curve_std = "IEC"
        curve_type = "VI"
        tms_def = 0.30 if tms_51 is None else tms_51
    elif application == "main_switchgear":
        # Main: SI (Standard Inverse) com TMS alto para coordenar
        curve_std = "IEC"
        curve_type = "SI"
        tms_def = 0.50 if tms_51 is None else tms_51
    elif application == "feeder_branch":
        curve_std = "IEC"
        curve_type = "SI"
        tms_def = 0.20 if tms_51 is None else tms_51
    else:
        curve_std = "IEC"
        curve_type = "SI"
        tms_def = 0.30 if tms_51 is None else tms_51

    # 5) Recomendações adicionais
    has_87 = application == "transformer"   # 87T para TR
    has_50BF = application in (
        "main_switchgear", "transformer", "motor_control_center",
    )
    has_AFD_rec = (
        bus.panel_type in (
            EquipmentClass.SWITCHGEAR_15KV,
            EquipmentClass.SWITCHGEAR_5KV,
            EquipmentClass.CCM_15KV,
            EquipmentClass.CCM_5KV,
        )
        and not bus.has_AFD   # já habilitado? não recomenda
    )

    # 6) Rationale
    rationale_list = []
    # v0.28.0-PRO P2.7: warning crítico no topo
    if heuristic_load_warning is not None:
        rationale_list.append(heuristic_load_warning)
    rationale_list.extend([
        f"Pickup 51 = {pickup_51_factor}× I_n "
        f"({pickup_51_factor*100:.0f}% acima da carga máxima) "
        "— margem para harmônicas + partidas temporárias.",
        f"Pickup 50 = {pickup_50_factor}× Ik'' garante operação "
        "em faltas francas (Buff Book §15.3).",
        f"Curva {curve_type} ({curve_std}) selecionada para "
        f"aplicação {application} — "
        + (
            "EI suporta inrush de motor."
            if curve_type == "EI"
            else "VI dá maior seletividade vs corrente."
            if curve_type == "VI"
            else "SI é o padrão para distribuição geral."
        ),
        f"TMS = {tms_def} escalonado conforme hierarquia "
        "(main lento, feeders progressivamente rápidos).",
        # v0.28.0-PRO P2.9: documenta grounding-aware 51N
        f"Pickup 51N = {pickup_51N_factor:.2f}× pickup_51 "
        f"baseado em grounding_type={grounding_type!r}.",
    ])
    rationale = tuple(rationale_list)
    if has_87:
        rationale = rationale + (
            "87T (diferencial) recomendado para transformador — "
            "proteção primária de zona.",
        )
    if has_AFD_rec:
        rationale = rationale + (
            f"AFD recomendado para {bus.panel_type.value} — "
            "redução típica de ~50× na energia incidente.",
        )

    # 7) Referências
    references = [
        "IEEE Std 242-2001 (Buff Book) §15.3 — pickup levels",
        "IEEE Std C37.112-2018 — TC equations",
        "IEC 60255-151 — TC curves",
    ]
    if application == "transformer":
        references.append("IEEE C37.91-2008 — transformer protection")
    elif application == "motor_control_center":
        references.append("IEEE C37.96-2012 — motor protection")
    elif application == "main_switchgear":
        references.append("IEEE C37.113-2015 — line protection")
    if has_AFD_rec:
        references.append("ABNT NBR 17227:2025 §5.1.9 — AFD")

    return RelaySuggestion(
        bus_id=bus.bus_id,
        application=application,
        relay_model_id=f"{relay_model.manufacturer.split()[0]}-{relay_model.model}",
        relay_manufacturer=relay_model.manufacturer,
        relay_application_target=relay_model.application,
        rated_current_A=I_n_A,
        load_current_assumed_A=load_current_assumed_A,
        Ik_pp_kA=Ik_pp_kA,
        pickup_51_A=pickup_51_A,
        pickup_51_per_in=pickup_51_factor,
        pickup_50_A=pickup_50_A,
        pickup_50_per_in=pickup_50_A / I_n_A,
        pickup_51N_A=pickup_51N_A,
        pickup_50N_A=pickup_50N_A,
        curve_51_standard=curve_std,
        curve_51_type=curve_type,
        tms_51=tms_def,
        delay_50_ms=0.0,         # instantâneo padrão
        has_50BF=has_50BF,
        has_87=has_87,
        has_AFD_recommended=has_AFD_rec,
        rationale=rationale,
        references=tuple(references),
    )


def suggest_multi_relay_alternatives(
    bus: BusComponent,
    Ik_pp_kA: float,
    load_S_MVA: Optional[float] = None,
) -> list[RelaySuggestion]:
    """
    Gera sugestões para **todos os 3 fabricantes** principais
    (SEL, ABB, Schneider) — útil para benchmarking de equipamento.
    """
    results = []
    for model in (SEL_751, ABB_REF615, SCHNEIDER_P3U30):
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA, load_S_MVA=load_S_MVA,
            relay_model=model,
        )
        results.append(sg)
    return results
