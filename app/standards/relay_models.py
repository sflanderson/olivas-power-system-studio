"""
app.standards.relay_models — registry de modelos comerciais de
relés de proteção, com suas funções ANSI suportadas, ranges
de configuração e curvas TC implementadas.

Fonte: manuais oficiais em ``LIBRARY/library_relay/``:

* **SEL-751** — Feeder Protection Relay (SEL/751_IM_20250801.pdf,
  PM751-01-NB, 2025).
* **ABB Relion 615** — Família REF615/RET615/REM615/RED615
  (ABB/RE_615_tech_757783_PTa.pdf, 2013, v3.0).
* **Schneider Easergy P3U** — P3U10/P3U20/P3U30 Universal Relays
  (SCHNEIDER/P3U_en_M_J006_ANSI_web.pdf, 2022).

Esta codificação permite ao Olivas:

1. **Selecionar** um modelo de relé real do catálogo via UI.
2. **Validar** que as funções de proteção exigidas pela
   coordenação estão disponíveis no modelo escolhido.
3. **Sugerir** ajustes (TMS, pickup) dentro dos ranges
   admissíveis pelo fabricante.
4. **Gerar** memorial de ajustes referenciando model number +
   firmware + manual.

Estrutura
=========

Cada modelo é um ``RelayModel`` com:

* **manufacturer**, **model**, **firmware_version**.
* **ansi_functions**: tupla de números ANSI suportados.
* **tc_curves**: tupla de curvas TC implementadas.
* **pickup_range_per_unit**: range de pickup em pu da corrente
  nominal do relé.
* **tms_range** / **time_dial_range**: ranges para TMS (IEC) e
  Time Dial (IEEE).
* **manual_path**: localização do PDF original.

Referências
============

* SEL-751 Instruction Manual (2025): seção 4 "Protection and
  Logic Functions" lista as funções 50/51/27/59/79/81 etc.
* ABB RE_615 Manual Técnico v3.0 (2013): tabela 5 "Functions
  supported".
* Schneider Easergy P3U Manual (2022): seções 5.1–5.40 listam
  funções por número ANSI.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.standards.iec60255 import (
    CurveStandard, IecCurveType, IeeeCurveType,
)


# ---------------------------------------------------------------------------
# RelayModel
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RelayModel:
    """
    Modelo comercial de relé com funções suportadas e ranges.

    Attributes
    ----------
    manufacturer:
        Fabricante (SEL, ABB, Schneider, etc.).
    model:
        Identificador do modelo (SEL-751, REF615, P3U30).
    family:
        Família comercial (Relion 615, Easergy P3, etc.).
    application:
        Aplicação primária ("feeder", "transformer", "motor",
        "generator", "line", "universal").
    firmware_version:
        Versão de firmware na qual a funcionalidade aqui
        descrita é válida.
    manual_path:
        Caminho relativo ao PDF do manual.
    ansi_functions:
        Tupla de números ANSI suportados.
    tc_curve_standards:
        Tupla das famílias de curvas implementadas
        (IEC, IEEE, DEFINITE_TIME, CUSTOM).
    iec_curves_supported:
        Tupla das curvas IEC específicas implementadas.
    ieee_curves_supported:
        Tupla das curvas IEEE específicas implementadas.
    pickup_range_per_in:
        Range de pickup como múltiplo da corrente nominal do
        relé (In). Tupla (mínimo, máximo).
    tms_range:
        Range de TMS (IEC). Tupla (mínimo, máximo).
    time_dial_range:
        Range de Time Dial (IEEE). Tupla (mínimo, máximo).
    """

    manufacturer: str
    model: str
    family: str
    application: str
    firmware_version: str
    manual_path: str

    ansi_functions: tuple[str, ...]
    tc_curve_standards: tuple[CurveStandard, ...]
    iec_curves_supported: tuple[IecCurveType, ...] = ()
    ieee_curves_supported: tuple[IeeeCurveType, ...] = ()

    pickup_range_per_in: tuple[float, float] = (0.1, 30.0)
    tms_range: tuple[float, float] = (0.05, 1.0)
    time_dial_range: tuple[float, float] = (0.5, 15.0)

    description: str = ""


def supports_function(model: RelayModel, ansi_number: str) -> bool:
    """Verifica se o modelo suporta uma função ANSI específica."""
    return ansi_number.upper() in model.ansi_functions


def supports_curve_standard(
    model: RelayModel, standard: CurveStandard,
) -> bool:
    """Verifica suporte a uma família de curva."""
    return standard in model.tc_curve_standards


def validate_pickup_per_in(
    model: RelayModel, pickup_per_in: float,
) -> bool:
    """Verifica se pickup (em multiplos de In) está no range."""
    lo, hi = model.pickup_range_per_in
    return lo <= pickup_per_in <= hi


def validate_tms(model: RelayModel, tms: float) -> bool:
    """Verifica TMS no range do fabricante."""
    lo, hi = model.tms_range
    return lo <= tms <= hi


def validate_time_dial(model: RelayModel, time_dial: float) -> bool:
    """Verifica Time Dial no range."""
    lo, hi = model.time_dial_range
    return lo <= time_dial <= hi


# ---------------------------------------------------------------------------
# Modelo SEL-751
# ---------------------------------------------------------------------------


# SEL-751 Feeder Protection Relay
# Fonte: SEL/751_IM_20250801.pdf, PM751-01-NB, 2025
# Seção 1 (Features), Seção 4 (Protection and Logic Functions).
SEL_751 = RelayModel(
    manufacturer="SEL",
    model="SEL-751",
    family="SEL Feeder Protection",
    application="feeder",
    firmware_version="R300+",
    manual_path="library_relay/SEL/751_IM_20250801.pdf",
    ansi_functions=(
        "27",           # Undervoltage
        "32",           # Directional power
        "37",           # Undercurrent
        "46",           # NS overcurrent
        "47",           # NS overvoltage / phase sequence
        "49",           # Thermal overload (RMS)
        "50",           # Instantaneous overcurrent
        "50N",          # Inst. neutral OC
        "50BF",         # Breaker failure
        "50HS",         # Switch-on-to-fault
        "51",           # Time OC
        "51N",          # Time neutral OC
        "59",           # Overvoltage
        "59N",          # Neutral overvoltage
        "67",           # Directional OC
        "67N",          # Directional neutral OC
        "79",           # Auto-recloser
        "81",           # Over/under frequency
        "81R",          # df/dt
        "86",           # Lockout
        "87",           # Differential (with restraint)
    ),
    tc_curve_standards=(
        CurveStandard.IEC,
        CurveStandard.IEEE,
        CurveStandard.DEFINITE_TIME,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE,
        IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE,
        IecCurveType.LONG_TIME_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE,
        IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE,
        IeeeCurveType.INVERSE,
        IeeeCurveType.SHORT_TIME_INVERSE,
    ),
    pickup_range_per_in=(0.5, 16.0),
    tms_range=(0.05, 1.0),
    time_dial_range=(0.5, 15.0),
    description=(
        "Feeder protection relay com proteção de sobrecorrente "
        "direcional, religamento automático, comunicação IEC 61850, "
        "DNP3, Modbus. Aplicação típica: alimentadores de "
        "distribuição MT (4.16-34.5 kV)."
    ),
)


# ---------------------------------------------------------------------------
# Modelo ABB Relion 615 (família genérica REx615)
# ---------------------------------------------------------------------------


# ABB REF615 — Feeder protection (mais comum da família 615)
# Fonte: ABB/RE_615_tech_757783_PTa.pdf, ID 1MRS757783, 2013
ABB_REF615 = RelayModel(
    manufacturer="ABB",
    model="REF615",
    family="ABB Relion 615",
    application="feeder",
    firmware_version="3.0+",
    manual_path="library_relay/ABB/RE_615_tech_757783_PTa.pdf",
    ansi_functions=(
        "50",
        "50N",
        "51",
        "51N",
        "67",
        "67N",
        "46",
        "46BC",
        "49",
        "27",
        "59",
        "59N",
        "47",
        "79",
        "81",
        "86",
        "50BF",
    ),
    tc_curve_standards=(
        CurveStandard.IEC,
        CurveStandard.IEEE,
        CurveStandard.DEFINITE_TIME,
        CurveStandard.CUSTOM,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE,
        IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE,
        IecCurveType.LONG_TIME_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE,
        IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE,
    ),
    pickup_range_per_in=(0.05, 40.0),
    tms_range=(0.05, 1.0),
    time_dial_range=(0.5, 15.0),
    description=(
        "Relion 615 family — proteção de alimentador, transformador, "
        "motor ou gerador conforme variante. Plataforma comum com "
        "IEC 61850 nativo, painel HMI gráfico, autodiagnóstico."
    ),
)


ABB_RET615 = RelayModel(
    manufacturer="ABB",
    model="RET615",
    family="ABB Relion 615",
    application="transformer",
    firmware_version="3.0+",
    manual_path="library_relay/ABB/RE_615_tech_757783_PTa.pdf",
    ansi_functions=(
        "50",
        "50N",
        "51",
        "51N",
        "67",
        "67N",
        "87T",          # Differential transformador
        "64REF",        # REF (restricted earth fault)
        "68F2",         # Bloqueio 2ª harmônica (inrush)
        "68H5",         # Bloqueio 5ª harmônica (overexcitation)
        "49",
        "27",
        "59",
        "59N",
        "47",
        "81",
        "86",
        "50BF",
    ),
    tc_curve_standards=(
        CurveStandard.IEC, CurveStandard.IEEE,
        CurveStandard.DEFINITE_TIME, CurveStandard.CUSTOM,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE,
        IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE,
        IecCurveType.LONG_TIME_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE,
        IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE,
    ),
    pickup_range_per_in=(0.05, 40.0),
    description="Relion 615 para proteção de transformador (87T + REF + backup OC).",
)


# ---------------------------------------------------------------------------
# Modelo Schneider Easergy P3U
# ---------------------------------------------------------------------------


# Schneider Easergy P3U30 (variant mais completa da família)
# Fonte: SCHNEIDER/P3U_en_M_J006_ANSI_web.pdf, 2022
# Seções 5.1-5.40 listam todas as funções ANSI implementadas.
SCHNEIDER_P3U30 = RelayModel(
    manufacturer="Schneider Electric",
    model="P3U30",
    family="Easergy P3 Universal",
    application="universal",
    firmware_version="J006+",
    manual_path="library_relay/SCHNEIDER/P3U_en_M_J006_ANSI_web.pdf",
    ansi_functions=(
        "25",           # Synchronism check
        "27",           # Undervoltage
        "32",           # Directional power
        "37",           # Undercurrent
        "46",           # NS overcurrent
        "46BC",         # Broken conductor
        "47",           # NS overvoltage
        "48",           # Motor start supervision
        "49",           # Thermal overload
        "50",           # Inst overcurrent
        "50BF",         # Breaker failure
        "50HS",         # Switch-on-to-fault
        "50N",          # Inst neutral OC
        "51",           # Time OC
        "51C",          # Capacitor unbalance
        "51LR",         # Locked rotor
        "51N",          # Time neutral OC
        "51V",          # Voltage-dependent OC
        "59",           # Overvoltage
        "59C",          # Capacitor overvoltage
        "59N",          # Neutral overvoltage
        "64REF",        # Restricted earth fault
        "66",           # Restart inhibition
        "67",           # Directional OC
        "67N",          # Directional neutral OC
        "67NI",         # Transient intermittent ground fault
        "68F2",         # Inrush 2nd harmonic
        "68H5",         # 5th harmonic
        "78V",          # Vector shift
        "79",           # Auto-recloser
        "81",           # Over/under frequency
        "81R",          # df/dt
        "86",           # Lockout
        "99",           # Programmable stages
    ),
    tc_curve_standards=(
        CurveStandard.IEC,
        CurveStandard.IEEE,
        CurveStandard.ANSI,
        CurveStandard.DEFINITE_TIME,
        CurveStandard.CUSTOM,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE,
        IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE,
        IecCurveType.LONG_TIME_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE,
        IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE,
        IeeeCurveType.INVERSE,
        IeeeCurveType.SHORT_TIME_INVERSE,
    ),
    pickup_range_per_in=(0.05, 40.0),
    tms_range=(0.025, 1.5),
    time_dial_range=(0.5, 15.0),
    description=(
        "Universal Relay P3U — feeder, transformer, motor ou "
        "generator. Curvas IEC, IEEE e IEEE2 + RI + custom + "
        "programmable. 34 funções ANSI implementadas."
    ),
)


SCHNEIDER_P3U10 = RelayModel(
    manufacturer="Schneider Electric",
    model="P3U10",
    family="Easergy P3 Universal",
    application="feeder_basic",
    firmware_version="J006+",
    manual_path="library_relay/SCHNEIDER/P3U_en_M_J006_ANSI_web.pdf",
    # P3U10 é variante reduzida (menos funções)
    ansi_functions=(
        "27", "46", "49", "50", "50N", "51", "51N",
        "59", "59N", "79", "81", "86", "50BF",
    ),
    tc_curve_standards=(
        CurveStandard.IEC, CurveStandard.IEEE,
        CurveStandard.DEFINITE_TIME,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE,
        IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE,
        IecCurveType.LONG_TIME_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE,
        IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE,
    ),
    description="Easergy P3U10 — variante feeder básica (subset do P3U30).",
)


# ---------------------------------------------------------------------------
# Registry global
# ---------------------------------------------------------------------------


RELAY_MODELS_REGISTRY: dict[str, RelayModel] = {
    "SEL-751": SEL_751,
    "ABB-REF615": ABB_REF615,
    "ABB-RET615": ABB_RET615,
    "Schneider-P3U30": SCHNEIDER_P3U30,
    "Schneider-P3U10": SCHNEIDER_P3U10,
}


def list_models() -> tuple[str, ...]:
    """Retorna todos os identificadores no registry."""
    return tuple(RELAY_MODELS_REGISTRY.keys())


def get_model(identifier: str) -> RelayModel | None:
    """Retorna o ``RelayModel`` por ID, ou ``None`` se não existe."""
    return RELAY_MODELS_REGISTRY.get(identifier)


def list_models_by_application(application: str) -> list[RelayModel]:
    """Filtra modelos por aplicação (feeder, transformer, motor etc.)."""
    return [
        m for m in RELAY_MODELS_REGISTRY.values()
        if m.application == application
        or m.application == "universal"
    ]


def list_models_supporting_function(ansi_number: str) -> list[RelayModel]:
    """Lista modelos que suportam uma função ANSI específica."""
    return [
        m for m in RELAY_MODELS_REGISTRY.values()
        if supports_function(m, ansi_number)
    ]
