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
# Modelos digitalizados de manuais oficiais (FASE 2 do catálogo)
# ---------------------------------------------------------------------------
#
# Nota de faixas: nestes modelos ``tms_range`` e ``time_dial_range``
# reproduzem o parâmetro único "Time multiplier / TDM" publicado pelo
# fabricante (aplicável às curvas IEC e ANSI/IEEE). Onde o fabricante
# publica faixas distintas por família (SEL-751: US 0.50-15.00,
# IEC 0.05-1.50), isto está registrado em ``description``.
# ``manual_path`` guarda a referência documental (PDF não incluído).
#
# Achado da verificação contra o datasheet SEL-751 (não alterado — a
# entrada pré-existente ``SEL_751`` acima tem testes legados que a
# codificam, ex. ``validate_pickup_per_in(SEL_751, 16.0)``):
#   * ``pickup_range_per_in=(0.5, 16.0)`` reproduz a faixa em ampères
#     SECUNDÁRIOS do modelo 5 A (0.50-16.00 A); em múltiplos de In a
#     faixa é 0.10-3.20 xIn (modelo 1 A: 0.10-3.20 A).
#   * ``tms_range=(0.05, 1.0)``: o datasheet publica IEC 0.05-1.50.
# Decisão de correção cabe ao mantenedor (impacto em coordenação).


# ABB Relion 615 — REF615R (versão ANSI, norte-americana)
# Fonte: 1MRS240050-IB Rev. C (2019-07-02), Tabelas 68, 77-79, 122-124
ABB_REF615R = RelayModel(
    manufacturer="ABB",
    model="REF615R",
    family="ABB Relion 615 (ANSI)",
    application="feeder",
    firmware_version="4.1",
    manual_path="ABB 1MRS240050-IB Rev C — REF615R Technical Manual (ANSI)",
    ansi_functions=(
        "51P", "50P", "51N", "50N", "51G", "50G", "50P-3", "50N-3",
        "67/51P", "67/50P", "67/51N", "67/50N", "50SEF", "51LT",
        "46", "46PD", "37", "49F", "32P", "32N", "27", "59", "59N", "59G",
        "47", "24", "81", "81LSH", "79", "25", "87LOZREF", "50BF",
    ),
    tc_curve_standards=(
        CurveStandard.IEC, CurveStandard.IEEE, CurveStandard.ANSI,
        CurveStandard.DEFINITE_TIME, CurveStandard.CUSTOM,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE, IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE, IecCurveType.LONG_TIME_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE, IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE, IeeeCurveType.INVERSE,
    ),
    pickup_range_per_in=(0.05, 40.0),
    tms_range=(0.05, 15.0),
    time_dial_range=(0.05, 15.0),
    description=(
        "Funções ANSI da Tabela 1 (nem todas aplicáveis a toda configuração). "
        "51P: pickup 0.05-5.00 xIn passo 0.01; 50P-1/2: 0.10-40.00 xIn; "
        "50P-3: 1.00-40.00 xIn; 51N/G: 0.010-5.000 xIn passo 0.005 "
        "(pickup_range_per_in abrange 51+50, convenção das entradas ABB). "
        "Time multiplier 0.05-15.00 passo 0.01 (IEC e ANSI). Trip delay DT "
        "40-200000 ms. 18 tipos de curva selecionáveis (índices 1-19, sem 16): "
        "ANSI Ext/Very/Norm/Mod Inv + ANSI DT, Long Time Ext/Very/Inv, IEC "
        "Norm/Very/Inv/Ext/ST/LT Inv + IEC DT, programável, RI, RD. Curva "
        "programável A/B/C/D/E com defaults 28.2/0.1217/2.0/29.1/1.0 (= ANSI "
        "Extremely Inverse). Blocos IEC 61850: PHLPTOC/PHHPTOC/PHIPTOC."
    ),
)


# Siemens SIPROTEC 5 — 7SJ82 / 7SJ85
# Fonte: C53000-G5040-C017-8 (11/2017), Technical Data §12.5 e §12.7
SIEMENS_7SJ82 = RelayModel(
    manufacturer="Siemens",
    model="7SJ82",
    family="SIPROTEC 5 (7SJ82/7SJ85)",
    application="feeder",
    firmware_version="V7.50+",
    manual_path="Siemens C53000-G5040-C017-8 — SIPROTEC 5 Overcurrent Protection 7SJ82/7SJ85 Technical Data",
    ansi_functions=(
        "50", "51", "50N", "51N", "67", "67N", "51V", "46", "49",
        "27", "59", "81", "79", "50BF", "25",
    ),
    tc_curve_standards=(
        CurveStandard.IEC, CurveStandard.IEEE, CurveStandard.ANSI,
        CurveStandard.DEFINITE_TIME, CurveStandard.CUSTOM,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE, IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE, IecCurveType.LONG_TIME_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE, IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE, IeeeCurveType.INVERSE,
        IeeeCurveType.SHORT_TIME_INVERSE,
    ),
    pickup_range_per_in=(0.03, 35.0),
    tms_range=(0.0, 15.0),
    time_dial_range=(0.0, 15.0),
    description=(
        "Dados técnicos da família SIPROTEC 5 (Cap. 12); lista ANSI restrita "
        "ao escopo verificável do 7SJ82. Pickup em A absoluto por banda de "
        "TC: 1 A @50/100×Irated 0.030-35.000 A (passo 0.001 A); 5 A: "
        "0.15-175.00 A; modo 1.6×Irated: 0.001-1.600 A (1 A). Time multiplier "
        "0.00-15.00 passo 0.01 (estágio inverso IEC/ANSI, fase §12.5.2 e "
        "terra §12.7.2); estágio de curva definida pelo usuário (§12.5.3) e "
        "51V: 0.05-15.00. Curvas IEC: Normal Inverse (A), Very (B), Extremely "
        "(C), Long-Time (B); ANSI/IEEE: Inverse (tipo C), Short, Long, "
        "Moderately, Very, Extremely, Definite Inverse. Curva programável por "
        "2-30 pares (X 1.00-20.00 pu, Y 0-999 s). Dropout 95% de 1.1×limiar."
    ),
)


# GE Multilin 850 — Feeder Protection System
# Fonte: 850 Instruction Manual, §Inverse Time Overcurrent Curves
# (pp. 4-114…4-122) e §Phase Time Overcurrent Protection (pp. 4-123/124)
GE_850 = RelayModel(
    manufacturer="GE",
    model="850",
    family="GE Multilin 8 Series",
    application="feeder",
    firmware_version="1.6x",
    manual_path="GE Multilin 850 Feeder Protection System Instruction Manual",
    ansi_functions=(
        "50", "51", "50N", "51N", "50G", "51G", "67", "67N", "46", "49",
        "51V", "27", "59", "59N", "81", "81R", "79", "50BF", "25", "32",
        "32N", "55", "87G",
    ),
    tc_curve_standards=(
        CurveStandard.IEC, CurveStandard.IEEE, CurveStandard.ANSI,
        CurveStandard.DEFINITE_TIME, CurveStandard.CUSTOM,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE, IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE, IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE,
    ),
    pickup_range_per_in=(0.05, 30.0),
    tms_range=(0.05, 600.0),
    time_dial_range=(0.05, 600.0),
    description=(
        "Phase TOC: pickup 0.050-30.000 ×CT passo 0.001 (default 1.000); "
        "TDM 0.05-600.00 passo 0.01. Famílias: IEEE (Ext/Very/Mod Inverse, "
        "Tab. 4-34), ANSI 5 constantes (Ext/Very/Normally/Mod, Tab. 4-36), "
        "IEC A/B/C + Short Inverse (Tab. 4-38), IAC (Tab. 4-40), FlexCurve "
        "A-D, I2t, I4t, DT. Reset instantâneo ou temporizado. '51V' = ajuste "
        "Voltage Restraint do Phase TOC (não é número ANSI na Tab. 1-1); "
        "latches não-voláteis não listados como 86. Constantes em "
        "vendor_curve_constants.py."
    ),
)


# Schneider Electric MiCOM série 20 — P127 (variante mais completa)
# Fonte: NRJED112402EN, tabelas de setting ranges
SCHNEIDER_MICOM_P127 = RelayModel(
    manufacturer="Schneider Electric",
    model="MiCOM P127",
    family="MiCOM series 20 (P122/P123/P127)",
    application="feeder",
    firmware_version="—",
    manual_path="Schneider NRJED112402EN — MiCOM P122/P123/P127 Technical Data",
    ansi_functions=(
        "27", "59", "59N", "32N", "67W", "37", "46BC", "46", "47", "49",
        "50N", "51N", "50", "51", "50BF", "51V", "64N", "67", "67N",
        "79", "81U/O", "81R", "86",
    ),
    tc_curve_standards=(
        CurveStandard.IEC, CurveStandard.IEEE, CurveStandard.DEFINITE_TIME,
        CurveStandard.CUSTOM,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE, IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE, IecCurveType.LONG_TIME_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE, IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE, IeeeCurveType.INVERSE,
        IeeeCurveType.SHORT_TIME_INVERSE,
    ),
    pickup_range_per_in=(0.1, 25.0),
    tms_range=(0.025, 1.5),
    time_dial_range=(0.025, 1.5),
    description=(
        "[51] I> 0.1-25 xIn, I>> e I>>> 0.5-40 xIn (passo 0.01); tI 0-150 s; "
        "TMS 0.025-1.5 passo 0.001; RTMS 0.025-1.5 (terra 0.025-3.2); tReset "
        "0-600 s; K(RI) 0.1-10. Tabela [67] específica do P127 (estágios "
        "direcionais): I>>/I>>> 0.1-40 xIn, RTMS 0.025-3.2 passo 0.025, tReset "
        "0-100 s, Ie> direcional 0.01-1 xIen. [50N/51N] Ie> média sens. "
        "0.01-2 xIen, baixa 0.1-25 xIen; 4 estágios. Curvas: IEC_STI/SI/VI/EI/"
        "LTI, C02, C08, IEEE_MI/VI/EI, RI, RECT, RXIDG (opcional). Interlock "
        "I>/>>/>>> explícito (No/Yes). P122/P123 (tabela ANSI codes): sem "
        "27/59/59N/32N/47/51V/67/67N/81U-O/81R/CTS/VTS; P122 também sem "
        "79/SOTF."
    ),
)


# WEG SRW01 — Relé Inteligente de proteção de motores
# Fonte: WEG SRW01 Manual do Usuário 0899.5838/06 (firmware V4.0X),
# §5.7 Parâmetros de Configuração das Proteções (§5.7.11 Sobrecarga,
# P640-P647; Referência Rápida P6xx)
WEG_SRW01 = RelayModel(
    manufacturer="WEG",
    model="SRW01",
    family="WEG Relé Inteligente",
    application="motor",
    firmware_version="V4.0X",
    manual_path="WEG SRW01 Manual do Usuário, documento 0899.5838/06 (V4.0X)",
    ansi_functions=(
        "49", "46", "47", "37", "50", "50G", "51G", "50GS", "49T", "27", "59",
        "32", "37P", "55", "81", "51LR",
    ),
    tc_curve_standards=(CurveStandard.DEFINITE_TIME,),
    description=(
        "Proteção de motores (não é relé de linha; nenhum IED de alimentador "
        "WEG foi localizado nas fontes consultadas). O manual não usa códigos "
        "ANSI: mapeamento inferido da nomenclatura em português (Falta a "
        "Terra calculada → 50G/51G; Fuga a Terra por sensor externo P632 "
        "0.3-5 A / P633 0.1-99 s → 50GS; Sobrecorrente P622 50-1000 % de "
        "P401, 1-99 s, default 400 % = rotor bloqueado → 50/51LR). Sobrecarga "
        "(49) por classe de disparo P640 {5,10,15,20,25,30,35,40,45} (default "
        "10) com curvas térmicas de aquecimento/resfriamento (não é tempo "
        "definido; DT descreve as demais proteções P6xx com tempo 1-99 s); "
        "pré-alarme P646 0-99 % (default 80 %), auto-reset P647 (default "
        "75 %). Corrente nominal do motor P401/P402: 0.0-5000.0 A (default "
        "0.5 A) — ranges padrão do dataclass (xIn) não se aplicam."
    ),
)


# Eaton (Cutler-Hammer) Digitrip 3000/3030 — relé de proteção de MÉDIA
# TENSÃO (retrofit para disjuntores a vácuo VCP-W e qualquer disjuntor
# com bobina de abertura por shunt trip) — NÃO é unidade de disparo
# integrada de disjuntor Magnum LV (confirmado: sem qualquer menção a
# "Magnum"/"DS"/"SB" nas 92 páginas do manual).
# Fonte: Cutler-Hammer/Eaton I.B. 17555C (efetivo nov/1999), Tabelas
# 2.2, 2.3, 2.4 e Seção 2-3.
EATON_DIGITRIP_3000 = RelayModel(
    manufacturer="Eaton",
    model="Digitrip 3000/3030",
    family="Cutler-Hammer/Eaton Digitrip 3000 Protective Relay",
    application="feeder",
    firmware_version="—",
    manual_path="Cutler-Hammer/Eaton I.B. 17555C (efetivo 11/1999)",
    ansi_functions=("50", "51", "50N", "51N"),
    tc_curve_standards=(
        CurveStandard.IEC, CurveStandard.IEEE, CurveStandard.ANSI,
        CurveStandard.DEFINITE_TIME, CurveStandard.CUSTOM,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE, IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE, IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE,
    ),
    pickup_range_per_in=(0.20, 2.20),
    tms_range=(0.025, 1.00),
    time_dial_range=(0.1, 5.0),
    description=(
        "Relé de proteção standalone para redes de MÉDIA TENSÃO — "
        "substitui 3-4 relés eletromecânicos + amperímetro + relé de "
        "bloqueio (86); alimentado por TCs externos (5 A secundário, "
        "relações 5:5 a 5000:5, mesmo conjunto para fase e terra), não é "
        "uma unidade de disparo integrada de disjuntor. Pickup de "
        "sobrecorrente de tempo inverso: fase 0.20-2.20×In "
        "(passo 0.05/0.10, 29 posições); terra 0.100-2.00×In (ou OFF) — "
        "pickup_range_per_in acima usa a faixa de fase. Multiplicador de "
        "tempo por família de curva: IT/I2T/I4T 0.20-40.0 (48 posições); "
        "FLAT (tempo definido) 0.20-2.00 s direto; ANSI MOD/VERY/XTRM "
        "0.1-5.0 (usado em time_dial_range); IEC A/B/C/D 0.025-1.00 "
        "(usado em tms_range). Curto retardo (fase): 1.00-11.0×In ou "
        "OFF; terra: 0.100-11.0×In ou OFF; tempo 0.05-1.50 s (ambos). "
        "Instantâneo: fase 1.00-25.0×In ou OFF (discriminador fixo em "
        "11×In se OFF); terra 0.50-11.0×In ou OFF. Curvas IEC A/B/C "
        "mapeadas por convenção BS142 (A=SI, B=VI, C=EI — mesmos k/α do "
        "IEC_CURVE_COEFFICIENTS, mesma convenção usada em "
        "vendor_curve_constants.py para a GE). IEC-D é TEMPO DEFINIDO "
        "(flat, sem expoente de corrente, ajuste direto em segundos "
        "0.20-2.00 s — confirmado na Seção 7-2 'Curve Equations' do "
        "manual: A=0, B=4), NÃO Long Time Inverse — por isso omitida de "
        "iec_curves_supported (já coberta por CurveStandard.DEFINITE_TIME "
        "acima). Certificação UL 1053 / ANSI C37.90. Alimentação DT3000: "
        "48-250 Vdc ou 120-240 Vac; DT3030: 24-48 Vdc."
    ),
)


# SEL-487E — relé DIFERENCIAL DE TRANSFORMADOR (87T/87Q/REF). O modelo
# de barra da SEL é o SEL-487B (conhecimento geral de catálogo — não
# confirmado nas fontes do 487E digitalizadas aqui, que não o
# mencionam). As equações das curvas U1-U5/C1-C5 do 487E conferem
# coeficiente a coeficiente com as do SEL-751 (mesma família de curva);
# a atribuição a IEEE C37.112-1996 é citada explicitamente no manual do
# SEL-751, mas NÃO no do 487E — inferida por transitividade.
# Fonte: SEL-487E Data Sheet (487E_DS_20120810.pdf) e Instruction
# Manual (Date Code 20090626), Tabelas 1, 3, 4.3, 4.4.
SEL_487E = RelayModel(
    manufacturer="SEL",
    model="SEL-487E",
    family="SEL Transformer Protection",
    application="transformer",
    firmware_version="—",
    manual_path="SEL-487E Instruction Manual, Date Code 20090626",
    ansi_functions=(
        "87U",          # Diferencial sem restrição
        "87R",          # Diferencial com restrição
        "87Q",          # Diferencial de sequência negativa
        "REF",          # Falha à terra restrita (até 3 elementos F/R)
        "50",           # Instantâneo (P/Q/N)
        "51S",          # Sobrecorrente de tempo adaptativo (seletivo)
        "50BF",         # Falha de disjuntor
        "46",           # Desbalanço de corrente
        "32",           # Potência direcional
        "67",           # Sobrecorrente direcional
        "81",           # Frequência (over/under)
        "27",           # Subtensão
        "59",           # Sobretensão
        "24",           # Volts/Hertz
        "49",           # Térmico
    ),
    tc_curve_standards=(
        CurveStandard.IEC, CurveStandard.IEEE, CurveStandard.DEFINITE_TIME,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE, IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE, IecCurveType.LONG_TIME_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE, IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE, IeeeCurveType.INVERSE,
        IeeeCurveType.SHORT_TIME_INVERSE,
    ),
    pickup_range_per_in=(0.05, 3.20),
    tms_range=(0.05, 1.00),
    time_dial_range=(0.50, 15.00),
    description=(
        "Relé diferencial de transformador (não de barra — o modelo de "
        "barra da SEL é o SEL-487B, produto distinto; essa distinção é "
        "conhecimento geral de catálogo SEL, não confirmada nas fontes "
        "do 487E aqui digitalizadas, que não mencionam o 487B). Até 5 "
        "enrolamentos, 1 zona de proteção. TAP pickup: 0.1-32.0×INOM "
        "A secundário (TAPMAX/TAPMIN≤35). Diferencial restrita: pickup "
        "0.1-4.0 pu, inclinação (slope) 1 e 2 ajustáveis 5-100 %. "
        "Diferencial sem restrição: 1.0-20.0×TAP. Diferencial de "
        "sequência negativa (87Q): pickup 0.05-1 pu, slope 5-100 %, "
        "detecta falta a partir de 2 % do enrolamento. REF (falha à "
        "terra restrita): até 3 elementos independentes F/R, pickup "
        "0.05-5 pu. Sobrecorrente instantânea (50): 5 A nom. "
        "0.25-100.00 A sec.; 1 A nom. 0.05-20.00 A sec. Sobrecorrente de "
        "tempo adaptativa (51S), 10 curvas selecionáveis por elemento "
        "(5 US + 5 IEC — coeficientes idênticos, elemento a elemento, "
        "aos U1-U5/C1-C5 do SEL-751; a atribuição a IEEE C37.112-1996 "
        "está no manual do SEL-751, não no do 487E — inferência por "
        "transitividade, não citação direta): pickup 5 A nom. "
        "0.25-16.00 A sec. (=0.05-3.20×In, "
        "usado em pickup_range_per_in), 1 A nom. 0.05-3.20 A sec.; Time "
        "Dial US 0.50-15.00 (usado em time_dial_range), IEC 0.05-1.00 "
        "(usado em tms_range) — nota: constantes de curva U1-U5/C1-C5 "
        "não recodificadas aqui por imperfeição de extração de frações "
        "empilhadas no PDF; usar as já verificadas em "
        "vendor_curve_constants.py (mesma família SEL)."
    ),
)


# ABB Relion 620 series (ANSI) — REF620 (feeder protection; linha
# superior à REF615/REF615R, mesma plataforma 620 usada também por
# RET620/transformador e REM620/motor). Achado relevante: proteção de
# DISTÂNCIA (21) e diferencial de alta impedância (87) na revisão do
# Technical Manual consultada (2019) são exclusivas do REM620 — o
# REF620 (linha feeder) NÃO tem 21P; o Product Guide REF620 mais
# recente (2022) já lista 87 de alta impedância, mas sem tabela de
# faixas numéricas confirmada para essa revisão especificamente.
# Fonte: ABB 1MAC504801-IB Rev. E (620 series ANSI Technical Manual,
# 2019-05-29, Seções 1.4.3, 4.1.1-4.1.5, 12.1-12.2) + 1MRS757844 Rev. G
# (REF620 Product Guide, 2022). REF630 (produto legado): Product
# Guide/Application Manual oficiais obtidos não continham tabelas de
# faixas de ajuste — não digitalizado por ausência de dado.
ABB_REF620 = RelayModel(
    manufacturer="ABB",
    model="REF620",
    family="ABB Relion 620 series (ANSI)",
    application="feeder",
    firmware_version="2.0/2.1",
    manual_path="ABB 1MAC504801-IB Rev. E (620 series Technical Manual, ANSI)",
    ansi_functions=(
        "51P", "50P-1", "50P-2", "50P-3", "51LT",
        "67/51P", "67/50P-1", "67/50P-2",
        "51G", "50SEF", "50G-1", "50G-2", "50G-3",
        "67/51N", "67/50N-1", "67/50N-2",
        "46-1", "46-2", "46PD",
        "59G", "59N", "27-1", "27-2", "59-1", "59-2", "47-1", "47-2",
        "81-1", "81-2", "81LSH", "49F", "50BF", "51BF",
        "86", "94", "HIZ", "AFD", "60", "25", "79", "52",
    ),
    tc_curve_standards=(
        CurveStandard.IEC, CurveStandard.IEEE, CurveStandard.ANSI,
        CurveStandard.DEFINITE_TIME, CurveStandard.CUSTOM,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE, IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE, IecCurveType.LONG_TIME_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE, IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE,
    ),
    pickup_range_per_in=(0.05, 40.0),
    tms_range=(0.05, 15.0),
    time_dial_range=(0.05, 15.0),
    description=(
        "Funções de sobrecorrente com 2 estágios de tempo definido "
        "(50-1/2, terra 50G/N-1/2) + 1 instantâneo (50-3) + 1 IDMT "
        "(51/51G). Estágio IDMT (51P/51G/51LT, 67/51P, 67/51N): pickup "
        "0.05-5.00 xIn passo 0.01 (51N/G: 0.010-5.000 passo 0.005), "
        "multiplicador de escala 0.8-10.0. Estágio alto (50-1/2): "
        "0.10-40.00 xIn passo 0.01. Estágio instantâneo (50-3): "
        "1.00-40.00 xIn passo 0.01. Retardo de tempo definido: "
        "40-200000 ms (IDMT) / 20-200000 ms (instantâneo); reset "
        "0-60000 ms. Time multiplier (IEC/ANSI IDMT): 0.05-15.00 passo "
        "0.01, idêntico em todos os estágios de baixa/direcionais. "
        "Curvas: ANSI EI/VI/NI/MI (esta última faixa 4, 'Normal "
        "Inverse', não mapeada a nenhum membro de IeeeCurveType — "
        "coeficientes A=0.0086/B=0.0185/C=0.02, distinta das 3 "
        "mapeadas); Long-Time EI/VI/Inverse (3 curvas adicionais, "
        "tr distinto: A=64.07/28.55/0.086); IEC NI/VI/Inverse/EI/STI/"
        "LTI/DT; Programável (RI, RD). Curva programável A-E "
        "(idêntica ao REF615R): A 0.0086-120.0000 (default 28.2000), "
        "B 0.0000-0.7120 (default 0.1217), C 0.02-2.00 (default 2.00), "
        "D 0.46-30.00 (default 29.10), E 0.0-1.0 (default 1.0) — "
        "defaults reproduzem a curva ANSI Extremely Inverse. Fórmula "
        "publicada (Tab. 612): t[s] = A/((I/I>)^C-1) + B·k. Constantes "
        "IEC (SI 0.14/0.02; VI 13.5/1.0; EI 80.0/2.0; STI 0.05/0.04; "
        "LTI 120/1.0) e ANSI EI/VI (28.2/0.1217/2.0; 19.61/0.491/2.0) "
        "idênticas às já digitalizadas para REF615R/GE — confirma "
        "consistência entre fontes independentes. Direcionalidade "
        "(67): ângulo característico -179..180°, quantidade de "
        "polarização configurável (self/neg-seq/cross/pos-seq). "
        "Distância (21P) e diferencial de alta impedância de barra "
        "(87/HIPDIF) confirmados como exclusivos do REM620 pela seção "
        "de identificação da função ('available in REM620 Ver.2.1 "
        "only', §4.7.1.1/4.6.4.1 do manual técnico 2019) — leitura "
        "inequívoca; a Tabela 1 (índice consolidado de funções) tem "
        "uma anomalia de alinhamento na linha do 21P especificamente, "
        "não usada como evidência primária aqui. O Product Guide "
        "REF620 2022 já anuncia 87 (fase A/B/C) mas sem faixa numérica "
        "confirmada para essa revisão — não modelado aqui por "
        "ausência de dado verificado."
    ),
)


# GE Multilin 369 — Motor Management Relay (linha de proteção de
# motor da GE, distinta da 8-Series feeder/transformer 750/845/850 —
# premissa original do pedido corrigida: 750 é relé de ALIMENTADOR,
# não de motor; 845 é de transformador e não pôde ser obtido).
# Curva de sobrecarga térmica PRÓPRIA da GE (forma quadrática em
# (pickup-1), não pertence a nenhuma família IEC 60255-151/IEEE
# C37.112 já codificada — não recodificada em vendor_curve_constants.py
# por ser específica de proteção térmica de motor, fora do escopo de
# curvas de sobrecorrente de linha daquele módulo.
# Fonte: GE Power Management GEK-106288, P/N 1601-0077-BC (2001),
# Seções 2.1.3, 2.2.5, 5.3.2, 5.4.3.
GE_369 = RelayModel(
    manufacturer="GE",
    model="369",
    family="GE Multilin 369 Motor Management Relay",
    application="motor",
    firmware_version="53CMB18x.000",
    manual_path="GE GEK-106288, P/N 1601-0077-BC (2001)",
    ansi_functions=(
        "14", "27", "37", "38", "46", "47", "49", "50", "50G", "51G",
        "51", "55", "59", "66", "74", "81", "86", "87",
    ),
    tc_curve_standards=(CurveStandard.CUSTOM, CurveStandard.DEFINITE_TIME),
    description=(
        "Relé de proteção de motor (não usa as famílias de curva IEC "
        "60255-151/IEEE C37.112 — proteção 51/sobrecarga usa réplica "
        "térmica proprietária da GE). 51 Sobrecarga/Rotor "
        "bloqueado/Modelo térmico: pickup 1.01-1.25×FLA; 15 formas de "
        "curva padrão (1-15) ou curva customizada (30 pontos "
        "tempo-corrente, 1.01-20.0×FLA); dropout 96-98% do pickup. "
        "Alarme de sobrecarga: 1.01-1.50×FLA passo 0.01, retardo "
        "0.1-60.0 s. 50 Curto-circuito: 2.0-20.0×TC passo 0.1, retardo "
        "0-255.00 s, retardo de retaguarda 0.10-255.00 s. Emperramento "
        "mecânico: 1.01-6.00×FLA, retardo 0.5-125.0 s. 37 Subcorrente: "
        "0.10-0.99×FLA, retardo 1-255 s, retardo de partida 0-15000 s. "
        "46 Desbalanço: 4-30% passo 1%, retardo 1-255 s. 50G/51G/50N/"
        "51N Falha à terra: 0.10-1.00×TC (TC 1A/5A) ou 0.25-25.00 A "
        "(TC sensível 50:0.025), retardo 0-255.00 s. 38/49 RTD: "
        "1-200 °C. 27 Subtensão: 0.50-0.99×nominal passo 0.01; 59 "
        "Sobretensão: 1.01-1.25×nominal passo 0.01; ambas retardo "
        "0.0-255.0 s. 81 Frequência: 20.00-70.00 Hz passo 0.01, "
        "retardo 0.0-255.0 s. 55 Fator de potência: 0.99-0.05 passo "
        "0.01. Curva de sobrecarga padrão (fórmula publicada, "
        "verbatim): tempo_disparo = (multiplicador_curva × 2.2116623) "
        "/ [0.02530337×(pickup-1)² + 0.05054758×(pickup-1)], onde "
        "pickup = corrente/FLA e multiplicador_curva ∈ {1..15}; acima "
        "de 8.0×pickup o tempo é mantido no valor de 8.0× (curva "
        "achatada para não agir como elemento instantâneo). Não é a "
        "mesma fórmula/família de nenhuma curva já em "
        "vendor_curve_constants.py — proteção térmica de motor "
        "verdadeira, não sobrecorrente de linha."
    ),
)


# Schneider Electric Sepam série 40 (plataforma Sepam 1000+) — linha
# NATIVA Schneider, distinta do MiCOM P12x (linhagem ex-Alstom/GE já
# digitalizada). 14 variantes (S40-S53 alimentador, T40-T52
# transformador, M41 motor, G40 gerador) compartilham o mesmo motor
# de proteção/curvas — modelado aqui como S40 (variante básica).
# Fonte: Schneider PCRED301006EN ed. 02/2017 (User's manual, faixas de
# ajuste pp. 47-50, curvas pp. 104-106) + PCRED301002EN ed. 01/2010
# (Technical data sheet, matriz de funções por variante).
SCHNEIDER_SEPAM_S40 = RelayModel(
    manufacturer="Schneider Electric",
    model="Sepam S40",
    family="Sepam série 40 (plataforma Sepam 1000+)",
    application="feeder",
    firmware_version="—",
    manual_path="Schneider PCRED301006EN ed. 02/2017 (Sepam série 40 User's Manual)",
    ansi_functions=(
        "50", "51", "50N", "51N", "50G", "51G", "50BF",
        "46", "27", "27S", "59", "59N", "47",
        "81H", "81L", "79",
    ),
    tc_curve_standards=(
        CurveStandard.IEC, CurveStandard.IEEE, CurveStandard.DEFINITE_TIME,
        CurveStandard.CUSTOM,
    ),
    iec_curves_supported=(
        IecCurveType.STANDARD_INVERSE, IecCurveType.VERY_INVERSE,
        IecCurveType.EXTREMELY_INVERSE, IecCurveType.LONG_TIME_INVERSE,
    ),
    ieee_curves_supported=(
        IeeeCurveType.MODERATELY_INVERSE, IeeeCurveType.VERY_INVERSE,
        IeeeCurveType.EXTREMELY_INVERSE,
    ),
    pickup_range_per_in=(0.1, 24.0),
    # TMS varia POR CURVA (manual, nota "Setting ranges in TMS mode"):
    # SIT/A 0.04-4.20; VIT/B 0.07-8.33; LTI/B 0.01-0.93; EIT/C
    # 0.13-15.47; IEEE MI 0.42-51.86; VI 0.73-90.57; EI 1.24-154.32;
    # IAC Inv 0.34-42.08; VI 0.61-75.75; EI 1.08-134.4. Usado abaixo:
    # VIT/B, curva de referência do próprio manual ("VIT com TMS=1
    # corresponde a T=1.5s").
    tms_range=(0.07, 8.33),
    time_dial_range=(0.1, 12.5),
    description=(
        "Variante básica de 14 da plataforma Sepam 1000+ (S40-S53 "
        "alimentador; T40-T52 transformador +49RMS/RTD; M41 motor "
        "+37/48/51LR/66; G40 gerador +50V/51V/32Q). 50/51 (fase): Is "
        "0.1-24×In (tempo definido) ou 0.1-2.4×In (IDMT); tempo "
        "definido 0.05-300 s; IDMT 0.1-12.5 s @10×Is (usado em "
        "pickup_range_per_in/time_dial_range); reset (timer hold) "
        "0.5-20 s (IDMT) ou 0.05-300 s (DT). 50N/51N e 50G/51G "
        "(terra): Is0 0.1-15×In0 (DT) ou 0.1-1×In0 (IDMT); TC "
        "toroidal 2A: 0.1-30 A, 20A: 2-300 A; TC sensível 1A: "
        "0.05-15×In0 (mín. 0.1 A). 46 Desbalanço: tempo definido "
        "0.1-5×Ib / 0.1-300 s; IDMT 0.1-0.5×Ib (curva Schneider) ou "
        "0.1-1×Ib (IEC/IEEE). 27 Subtensão: 5-120% Unp; 27S "
        "(fase-neutro): 5-120% Vnp; 59 Sobretensão: 50-150% Unp "
        "(Uns<208V) ou 50-135% (Uns≥208V) — NÃO a mesma faixa de 27; "
        "59N (deslocamento de tensão de neutro): 2-80% Unp; 47 "
        "(sobretensão seq. negativa): 1-50% Unp; todas com retardo "
        "0.05-300 s. 27R (subtensão remanente, 5-100% Unp) é exclusivo "
        "do M41/motor — não suportado pelo S40 (removido de "
        "ansi_functions; 46BC, exclusivo de S50-S53/T50/T52, idem). "
        "81H/81L: "
        "50-65 Hz / 40-60 Hz (faixas por banda), 0.1-300 s. Ajuste de "
        "retardo IDMT por dois métodos equivalentes: tempo T "
        "(operação a 10×Is) ou fator TMS = T/β (β = constante de "
        "normalização própria de cada curva). Curvas IEC: t=k/((I/Is)^"
        "α-1)×T/β — SI/A k=0.14 α=0.02 β=2.97; VI/B k=13.5 α=1 "
        "β=1.50; Long-Time/B k=120 α=1 β=13.33; EI/C k=80 α=2 "
        "β=0.808; Ultra Inverse k=315.2 α=2.5 β=1 (constantes k/α "
        "coincidem com os valores universais IEC 60255-151 já em "
        "vendor_curve_constants.py; β é normalização específica da "
        "Schneider, não presente nas demais fontes). Curvas IEEE: "
        "t=[A/((I/Is)^p-1)+B]×T/β — MI(D) A=0.010 B=0.023 p=0.02 "
        "β=0.241; VI(E) A=3.922 B=0.098 p=2 β=0.138; EI(F) A=5.64 "
        "B=0.0243 p=2 β=0.081 — coeficientes A/B/p DIFERENTES dos "
        "universais IEEE C37.112 Anexo A (28.2/0.1217/2.0 etc.) já "
        "digitalizados para ABB/GE — família numérica distinta apesar "
        "do nome comum, mesma cautela já registrada no módulo "
        "vendor_curve_constants.py para SEL vs GE ANSI. Curvas IAC "
        "(forma de 5 constantes, fórmula com denominador (I/Is-C)) e "
        "RI (t=1/(0.339-0.236/(I/Is))×T/3.1706) também suportadas, "
        "não recodificadas. Acima de 20×Is tempo de disparo travado "
        "no valor de 20×Is."
    ),
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
    # FASE 2 — digitalizados de manuais oficiais
    "ABB-REF615R": ABB_REF615R,
    "Siemens-7SJ82": SIEMENS_7SJ82,
    "GE-850": GE_850,
    "Schneider-MiCOM-P127": SCHNEIDER_MICOM_P127,
    "WEG-SRW01": WEG_SRW01,
    "Eaton-Digitrip-3000": EATON_DIGITRIP_3000,
    "SEL-487E": SEL_487E,
    "ABB-REF620": ABB_REF620,
    "GE-369": GE_369,
    "Schneider-Sepam-S40": SCHNEIDER_SEPAM_S40,
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
