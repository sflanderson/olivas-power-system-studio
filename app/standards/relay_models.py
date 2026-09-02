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
        "46", "27", "59", "59N", "47", "81", "79", "86", "50BF",
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
    pickup_range_per_in=(0.05, 5.0),
    tms_range=(0.05, 15.0),
    time_dial_range=(0.05, 15.0),
    description=(
        "51P: pickup 0.05-5.00 xIn passo 0.01; 50P-1/2: 0.10-40.00 xIn; "
        "51N/G: 0.010-5.000 xIn passo 0.005. Time multiplier 0.05-15.00 "
        "passo 0.01 (IEC e ANSI). Trip delay DT 40-200000 ms. 19 tipos de "
        "curva (7 IEEE C37.112, 6 IEC 60255-3, LT Inv, RI, RD, programável). "
        "Curva programável A/B/C/D/E com defaults 28.2/0.1217/2.0/29.1/1.0 "
        "(= IEEE Extremely Inverse). Blocos IEC 61850: PHLPTOC/PHHPTOC/PHIPTOC."
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
        "27", "59", "81", "79", "50BF", "86", "25",
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
    pickup_range_per_in=(0.03, 35.0),
    tms_range=(0.05, 15.0),
    time_dial_range=(0.05, 15.0),
    description=(
        "Pickup em A absoluto por banda de TC: 1 A @50/100×Irated 0.030-35.000 A "
        "(passo 0.001 A); 5 A: 0.15-175.00 A; modo 1.6×Irated: 0.001-1.600 A "
        "(1 A). Time multiplier fase 0.05-15.00, terra 0.00-15.00 (passo 0.01). "
        "Curvas IEC: Normal Inverse (A), Very (B), Extremely (C), Long-Time (B); "
        "ANSI: Moderately/Very/Extremely/Definite Inverse. Curva programável "
        "por 2-30 pares (X 1.00-20.00 pu, Y 0-999 s). Dropout 95% de 1.1×limiar."
    ),
)


# GE Multilin 850 — Feeder Protection System
# Fonte: 850 Instruction Manual, §Phase TOC (pp. 4-115…4-123)
GE_850 = RelayModel(
    manufacturer="GE",
    model="850",
    family="GE Multilin 8 Series",
    application="feeder",
    firmware_version="1.6x",
    manual_path="GE Multilin 850 Feeder Protection System Instruction Manual",
    ansi_functions=(
        "50", "51", "50N", "51N", "50G", "51G", "67", "67N", "46", "49",
        "51V", "27", "59", "59N", "81", "79", "50BF", "86", "25", "32",
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
        "A-D, I2t, I4t, DT. Reset instantâneo ou temporizado. Voltage "
        "restraint opcional. Constantes em vendor_curve_constants.py."
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
        "27", "59", "32N", "67W", "37", "46BC", "46", "47", "49",
        "50N", "51N", "50", "51", "50BF", "51V", "67", "67N",
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
    pickup_range_per_in=(0.1, 25.0),
    tms_range=(0.025, 1.5),
    time_dial_range=(0.025, 1.5),
    description=(
        "[51] I> 0.1-25 xIn, I>> e I>>> 0.5-40 xIn (passo 0.01); tI 0-150 s; "
        "TMS 0.025-1.5 passo 0.001; RTMS 0.025-1.5 (terra 0.025-3.2); tReset "
        "0-600 s; K(RI) 0.1-10. [50N/51N] Ie> média sens. 0.01-2 xIen, baixa "
        "0.1-25 xIen; 4 estágios. Curvas: IEC_STI/SI/VI/EI/LTI, C02, C08, "
        "IEEE_MI/VI/EI, RI, RECT, RXIDG (opcional). Interlock I>/>>/>>> "
        "explícito (No/Yes). P122/P123: subconjunto sem 27/59/32N/47/51V/67."
    ),
)


# WEG SRW01 — Relé Inteligente de proteção de motores
# Fonte: WEG SRW01 Manual do Usuário v4.x, §5.7 (Tabela 5.10, P640-P647)
WEG_SRW01 = RelayModel(
    manufacturer="WEG",
    model="SRW01",
    family="WEG Relé Inteligente",
    application="motor",
    firmware_version="4.x",
    manual_path="WEG SRW01 Manual do Usuário 10000445381 v4.x",
    ansi_functions=(
        "49", "46", "47", "37", "50G", "51G", "50GS", "49T", "27", "59",
        "32", "37P", "55", "81", "51LR",
    ),
    tc_curve_standards=(CurveStandard.DEFINITE_TIME,),
    description=(
        "Proteção de motores (não é relé de linha — WEG não fabrica IED de "
        "alimentador MT/AT). Mapeamento ANSI inferido da nomenclatura em "
        "português do manual. Sobrecarga (49) por classe de disparo P640 "
        "{5,10,15,20,25,30,35,40,45} (default 10 = tempo de partida 10 s); "
        "pré-alarme P646 0-99% (default 80%), auto-reset P647 (default 75%). "
        "Faixas de pickup (FLA) não digitalizadas — ranges padrão do dataclass "
        "não se aplicam."
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
