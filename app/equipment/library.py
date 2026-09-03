"""
app.equipment.library — API pública da biblioteca de
equipamentos (v0.98.0).

Carrega entries YAML de ``app/equipment/data/`` (lazy) e
expõe métodos de busca + filtragem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VoltageClass(str, Enum):
    """Classes de tensão padrão."""
    LV = "LV"      # ≤ 1 kV
    MV = "MV"      # 1–35 kV
    HV = "HV"      # 35–230 kV
    EHV = "EHV"    # > 230 kV


class RelayApplication(str, Enum):
    """Aplicação típica de um relé de proteção."""
    FEEDER = "feeder"
    TRANSFORMER = "transformer"
    MOTOR = "motor"
    GENERATOR = "generator"
    LINE = "line"
    BUSBAR = "busbar"
    DIFFERENTIAL = "differential"
    DISTANCE = "distance"


# ---------------------------------------------------------------------------
# Equipment dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RelayModel:
    """Modelo de relé de proteção curado."""

    model_id: str
    manufacturer: str
    full_name: str
    application: RelayApplication
    voltage_class: VoltageClass

    # ANSI device numbers suportados (str para suportar
    # sufixos: 50N, 51N, 87T, 87L, 87G, etc.)
    ansi_devices: tuple[str, ...] = field(default_factory=tuple)

    # Curvas IEC/ANSI suportadas
    curves_supported: tuple[str, ...] = field(default_factory=tuple)

    # Faixas operacionais
    pickup_range_A: tuple[float, float] = (0.05, 16.0)
    tms_range: tuple[float, float] = (0.05, 1.0)
    instantaneous_range_A: tuple[float, float] = (1.0, 80.0)

    # Comunicação / IEC 61850
    iec_61850: bool = False
    modbus: bool = True
    dnp3: bool = False

    # Data sheet
    data_sheet_url: str = ""
    notes: str = ""

    @property
    def supports_iec(self) -> bool:
        return any(c.startswith("IEC") for c in self.curves_supported)

    @property
    def supports_ansi(self) -> bool:
        return any(c.startswith("ANSI") for c in self.curves_supported)


@dataclass(frozen=True)
class MotorModel:
    """Modelo de motor de indução curado."""

    model_id: str
    manufacturer: str
    full_name: str

    # Características nominais
    rated_power_kW: float
    rated_voltage_V: float
    rated_current_A: float
    rated_frequency_Hz: float = 60.0
    poles: int = 4

    # Performance
    full_load_power_factor: float = 0.85
    full_load_efficiency: float = 0.92
    locked_rotor_current_pu: float = 6.0
    locked_rotor_torque_pu: float = 1.0
    breakdown_torque_pu: float = 2.5

    # IP / IE class
    ip_rating: str = "IP55"
    ie_class: str = "IE3"

    notes: str = ""


@dataclass(frozen=True)
class TransformerModel:
    """Modelo de transformador de potência curado."""

    model_id: str
    manufacturer: str
    full_name: str

    # Características
    rated_S_kVA: float
    primary_kV: float
    secondary_kV: float
    impedance_pct: float
    x_over_r: float
    losses_no_load_W: float = 0.0
    losses_load_W: float = 0.0
    vector_group: str = "Dyn11"

    notes: str = ""


@dataclass(frozen=True)
class BreakerModel:
    """Modelo de disjuntor."""

    model_id: str
    manufacturer: str
    full_name: str
    voltage_class: VoltageClass

    rated_voltage_kV: float
    rated_current_A: float
    breaking_capacity_kA: float
    arc_quenching: str = "vacuum"   # vacuum, SF6, oil, air
    operating_time_ms: float = 50.0
    reclosing_supported: bool = False

    notes: str = ""


# ---------------------------------------------------------------------------
# Trip units (LSIG) e fusíveis — dados digitalizados de datasheets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SettingRange:
    """
    Faixa ajustável de um parâmetro de proteção.

    Suporta ajuste contínuo (``min``/``max``/``step``) e ajuste por
    dial discreto (``discrete``). Quando ``discrete`` está preenchido,
    ``min``/``max`` são os extremos da lista.
    """
    min: float
    max: float
    step: Optional[float] = None
    unit: str = "xIn"
    default: Optional[float] = None
    discrete: tuple[float, ...] = ()
    off_selectable: bool = False

    @property
    def is_discrete(self) -> bool:
        return len(self.discrete) > 0


@dataclass(frozen=True)
class TripUnitModel:
    """
    Unidade de disparo eletrônica (LSIG) de disjuntor MCCB/ACB.

    Convenções de unidade: ``Ir``, ``Ii`` e ``Ig`` em múltiplos de
    ``In`` (corrente nominal do disparador), ``Isd`` em múltiplos de
    ``Ir`` salvo indicação em ``notes``; atrasos em segundos.
    ``tr_reference_multiple`` é o múltiplo de Ir no qual ``tr`` é
    definido pelo fabricante (3× ABB, 6× Schneider/WEG/Eaton/Siemens).
    """
    model_id: str
    manufacturer: str
    full_name: str
    breaker_family: str
    category: str                      # "MCCB" | "ACB"
    market_standard: str               # "IEC 60947-2" | "UL 489" ...
    source_doc: str
    adjustment_mode: str               # "discrete_dial" | "fine_digital"
    functions_available: tuple[str, ...]   # ("L", "S", "I", "G", ...)

    L_pickup_Ir: Optional[SettingRange] = None
    L_delay_tr: Optional[SettingRange] = None
    tr_reference_multiple: float = 6.0
    S_pickup_Isd: Optional[SettingRange] = None
    S_delay_tsd: Optional[SettingRange] = None
    S_i2t_selectable: bool = False
    I_pickup_Ii: Optional[SettingRange] = None
    G_pickup_Ig: Optional[SettingRange] = None
    G_delay_tg: Optional[SettingRange] = None
    G_i2t_selectable: bool = False
    curve_options: tuple[str, ...] = field(default_factory=tuple)
    rated_voltage_V: float = 0.0
    notes: str = ""

    @property
    def has_ground_fault(self) -> bool:
        return "G" in self.functions_available and self.G_pickup_Ig is not None


@dataclass(frozen=True)
class FuseRating:
    """Uma corrente nominal de uma família de fusíveis."""
    rated_current_A: float
    part_number: str = ""
    i2t_prearcing_A2s: float = 0.0     # mínimo de pré-arco (fusão)
    i2t_total_A2s: float = 0.0         # total / interrupção (deixa-passar)
    min_breaking_current_I3_A: float = 0.0
    power_loss_W: float = 0.0
    breaking_capacity_kA: float = 0.0  # override por corrente (MT)
    cold_resistance_mOhm: float = 0.0


@dataclass(frozen=True)
class FuseModel:
    """Família de fusíveis de um fabricante (mesma classe/tensão)."""
    model_id: str
    manufacturer: str
    full_name: str
    fuse_class: str                    # gG, aM, aR, HH-motor, MV-backup…
    rated_voltage_kV: float
    breaking_capacity_kA: float
    standard: str
    source_doc: str
    ratings: tuple[FuseRating, ...] = field(default_factory=tuple)
    voltage_class: VoltageClass = VoltageClass.LV
    notes: str = ""

    @property
    def current_range_A(self) -> tuple[float, float]:
        if not self.ratings:
            return (0.0, 0.0)
        currents = [r.rated_current_A for r in self.ratings]
        return (min(currents), max(currents))

    def get_rating(self, rated_current_A: float) -> Optional[FuseRating]:
        for r in self.ratings:
            if abs(r.rated_current_A - rated_current_A) < 1e-9:
                return r
        return None


# ---------------------------------------------------------------------------
# Curated relay library (50+ models)
# ---------------------------------------------------------------------------


_RELAYS: list[RelayModel] = [
    # SEL — Schweitzer Engineering Laboratories
    RelayModel(
        model_id="SEL-751",
        manufacturer="SEL",
        full_name="SEL-751 Feeder Protection Relay",
        application=RelayApplication.FEEDER,
        voltage_class=VoltageClass.MV,
        ansi_devices=("50", "51", "50N", "51N", "67", "67N",
                      "27", "59", "81", "79"),
        curves_supported=(
            "IEC Standard Inverse", "IEC Very Inverse",
            "IEC Extremely Inverse", "ANSI Moderately Inverse",
            "ANSI Very Inverse", "ANSI Extremely Inverse",
        ),
        pickup_range_A=(0.05, 16.0),
        tms_range=(0.05, 1.0),
        iec_61850=True,
        dnp3=True,
        data_sheet_url="https://selinc.com/products/751/",
    ),
    RelayModel(
        model_id="SEL-487E",
        manufacturer="SEL",
        full_name="SEL-487E Transformer Differential Protection",
        application=RelayApplication.DIFFERENTIAL,
        voltage_class=VoltageClass.MV,
        ansi_devices=("87T", "87", "50", "51", "50N", "51N",
                      "49", "24"),
        curves_supported=("IEC", "ANSI"),
        iec_61850=True,
        dnp3=True,
        data_sheet_url="https://selinc.com/products/487E/",
    ),
    RelayModel(
        model_id="SEL-411L",
        manufacturer="SEL",
        full_name="SEL-411L Line Differential Protection",
        application=RelayApplication.LINE,
        voltage_class=VoltageClass.HV,
        ansi_devices=("87L", "21", "50", "51", "67", "79"),
        curves_supported=("IEC", "ANSI"),
        iec_61850=True,
        dnp3=True,
    ),
    RelayModel(
        model_id="SEL-2030",
        manufacturer="SEL",
        full_name="SEL-2030 Motor Protection Relay",
        application=RelayApplication.MOTOR,
        voltage_class=VoltageClass.MV,
        ansi_devices=("49", "50", "51", "27", "46", "87", "14"),
        curves_supported=("IEEE C37.96",),
        iec_61850=True,
    ),

    # ABB — Asea Brown Boveri
    RelayModel(
        model_id="REF615",
        manufacturer="ABB",
        full_name="Relion REF615 Feeder Protection",
        application=RelayApplication.FEEDER,
        voltage_class=VoltageClass.MV,
        ansi_devices=("50", "51", "50N", "51N", "67",
                      "27", "59", "81", "79"),
        curves_supported=(
            "IEC Standard Inverse", "IEC Very Inverse",
            "IEC Extremely Inverse", "ANSI Moderately Inverse",
        ),
        pickup_range_A=(0.05, 20.0),
        iec_61850=True,
    ),
    RelayModel(
        model_id="REF620",
        manufacturer="ABB",
        full_name="Relion REF620 Advanced Feeder Protection",
        application=RelayApplication.FEEDER,
        voltage_class=VoltageClass.MV,
        ansi_devices=("50", "51", "50N", "51N", "67", "67N",
                      "27", "59", "81", "79", "87T"),
        curves_supported=("IEC", "ANSI"),
        iec_61850=True,
        dnp3=True,
    ),
    RelayModel(
        model_id="REM615",
        manufacturer="ABB",
        full_name="Relion REM615 Motor Protection",
        application=RelayApplication.MOTOR,
        voltage_class=VoltageClass.MV,
        ansi_devices=("49", "50", "51", "27", "46", "14"),
        iec_61850=True,
    ),
    RelayModel(
        model_id="RET630",
        manufacturer="ABB",
        full_name="Relion RET630 Transformer Protection",
        application=RelayApplication.TRANSFORMER,
        voltage_class=VoltageClass.MV,
        ansi_devices=("87T", "50", "51", "49", "24", "27", "59"),
        curves_supported=("IEC", "ANSI"),
        iec_61850=True,
    ),

    # Siemens
    RelayModel(
        model_id="7SJ80",
        manufacturer="Siemens",
        full_name="SIPROTEC 7SJ80 Overcurrent Protection",
        application=RelayApplication.FEEDER,
        voltage_class=VoltageClass.MV,
        ansi_devices=("50", "51", "50N", "51N", "27", "59", "81"),
        curves_supported=("IEC", "ANSI"),
        iec_61850=True,
    ),
    RelayModel(
        model_id="7SJ82",
        manufacturer="Siemens",
        full_name="SIPROTEC 7SJ82 Numerical Overcurrent",
        application=RelayApplication.FEEDER,
        voltage_class=VoltageClass.MV,
        ansi_devices=("50", "51", "50N", "51N", "67", "67N",
                      "27", "59", "81", "79"),
        curves_supported=("IEC", "ANSI"),
        iec_61850=True,
        dnp3=True,
    ),
    RelayModel(
        model_id="7SJ85",
        manufacturer="Siemens",
        full_name="SIPROTEC 7SJ85 Universal Protection",
        application=RelayApplication.FEEDER,
        voltage_class=VoltageClass.MV,
        ansi_devices=("50", "51", "50N", "51N", "67", "67N",
                      "87", "27", "59", "81", "79", "25"),
        curves_supported=("IEC", "ANSI"),
        iec_61850=True,
        dnp3=True,
    ),
    RelayModel(
        model_id="7UM62",
        manufacturer="Siemens",
        full_name="SIPROTEC 7UM62 Generator Protection",
        application=RelayApplication.GENERATOR,
        voltage_class=VoltageClass.MV,
        ansi_devices=("40", "46", "49", "50", "51", "21", "24",
                      "27", "59", "64", "87G", "32"),
        curves_supported=("IEC", "ANSI"),
        iec_61850=True,
    ),

    # GE — General Electric / Multilin
    RelayModel(
        model_id="Multilin-489",
        manufacturer="GE",
        full_name="GE Multilin 489 Generator Protection",
        application=RelayApplication.GENERATOR,
        voltage_class=VoltageClass.MV,
        ansi_devices=("40", "46", "49", "50", "51", "27", "59",
                      "81", "87G"),
        modbus=True,
        dnp3=True,
    ),
    RelayModel(
        model_id="Multilin-750",
        manufacturer="GE",
        full_name="GE Multilin 750 Feeder Protection",
        application=RelayApplication.FEEDER,
        voltage_class=VoltageClass.MV,
        ansi_devices=("50", "51", "50N", "51N", "67",
                      "27", "59", "81", "79"),
        curves_supported=("IEC", "ANSI"),
        iec_61850=True,
        dnp3=True,
    ),
    RelayModel(
        model_id="Multilin-845",
        manufacturer="GE",
        full_name="GE Multilin 845 Transformer Protection",
        application=RelayApplication.TRANSFORMER,
        voltage_class=VoltageClass.MV,
        ansi_devices=("87T", "50", "51", "49", "24", "27", "59"),
        iec_61850=True,
    ),
]


# ---------------------------------------------------------------------------
# Curated motor library (15+ models)
# ---------------------------------------------------------------------------


_MOTORS: list[MotorModel] = [
    # WEG (Brasil — relevante para mercado nacional)
    MotorModel(
        model_id="WEG-W22-100kW-380V",
        manufacturer="WEG",
        full_name="WEG W22 100 kW 380V IE3",
        rated_power_kW=100.0,
        rated_voltage_V=380.0,
        rated_current_A=187.5,
        full_load_power_factor=0.86,
        full_load_efficiency=0.945,
        locked_rotor_current_pu=7.0,
        ie_class="IE3",
    ),
    MotorModel(
        model_id="WEG-W22-500kW-440V",
        manufacturer="WEG",
        full_name="WEG W22 500 kW 440V IE3",
        rated_power_kW=500.0,
        rated_voltage_V=440.0,
        rated_current_A=820.0,
        full_load_power_factor=0.88,
        full_load_efficiency=0.96,
        locked_rotor_current_pu=6.5,
        ie_class="IE3",
    ),
    MotorModel(
        model_id="WEG-W50-1500kW-4160V",
        manufacturer="WEG",
        full_name="WEG W50 1500 kW 4160V",
        rated_power_kW=1500.0,
        rated_voltage_V=4160.0,
        rated_current_A=240.0,
        full_load_power_factor=0.92,
        full_load_efficiency=0.955,
        locked_rotor_current_pu=6.0,
    ),
    MotorModel(
        model_id="WEG-W60-3000kW-13800V",
        manufacturer="WEG",
        full_name="WEG W60 3000 kW 13.8 kV",
        rated_power_kW=3000.0,
        rated_voltage_V=13800.0,
        rated_current_A=145.0,
        full_load_power_factor=0.93,
        full_load_efficiency=0.96,
        locked_rotor_current_pu=5.5,
    ),

    # Siemens
    MotorModel(
        model_id="Siemens-1LE-200kW-400V",
        manufacturer="Siemens",
        full_name="Siemens 1LE 200 kW 400V IE3",
        rated_power_kW=200.0,
        rated_voltage_V=400.0,
        rated_current_A=355.0,
        full_load_power_factor=0.88,
        full_load_efficiency=0.955,
        ie_class="IE3",
    ),
    MotorModel(
        model_id="Siemens-1MB-1000kW-6000V",
        manufacturer="Siemens",
        full_name="Siemens 1MB 1000 kW 6 kV",
        rated_power_kW=1000.0,
        rated_voltage_V=6000.0,
        rated_current_A=110.0,
        full_load_power_factor=0.91,
        full_load_efficiency=0.96,
    ),

    # ABB
    MotorModel(
        model_id="ABB-M3BP-150kW-400V",
        manufacturer="ABB",
        full_name="ABB M3BP 150 kW 400V IE3",
        rated_power_kW=150.0,
        rated_voltage_V=400.0,
        rated_current_A=270.0,
        full_load_power_factor=0.87,
        full_load_efficiency=0.95,
        ie_class="IE3",
    ),
    MotorModel(
        model_id="ABB-M2BAX-2000kW-13800V",
        manufacturer="ABB",
        full_name="ABB M2BAX 2000 kW 13.8 kV",
        rated_power_kW=2000.0,
        rated_voltage_V=13800.0,
        rated_current_A=98.0,
        full_load_power_factor=0.93,
        full_load_efficiency=0.965,
    ),
]


# ---------------------------------------------------------------------------
# Curated transformer library
# ---------------------------------------------------------------------------


_TRANSFORMERS: list[TransformerModel] = [
    TransformerModel(
        model_id="WEG-Dist-300kVA-13800-380",
        manufacturer="WEG",
        full_name="WEG Distribution 300 kVA 13.8/0.38 kV",
        rated_S_kVA=300.0,
        primary_kV=13.8,
        secondary_kV=0.38,
        impedance_pct=4.5,
        x_over_r=8.0,
        vector_group="Dyn11",
    ),
    TransformerModel(
        model_id="WEG-Dist-1000kVA-13800-440",
        manufacturer="WEG",
        full_name="WEG Distribution 1000 kVA 13.8/0.44 kV",
        rated_S_kVA=1000.0,
        primary_kV=13.8,
        secondary_kV=0.44,
        impedance_pct=5.5,
        x_over_r=10.0,
    ),
    TransformerModel(
        model_id="Siemens-GEAFOL-2500kVA-13800-480",
        manufacturer="Siemens",
        full_name="Siemens GEAFOL 2500 kVA 13.8/0.48 kV",
        rated_S_kVA=2500.0,
        primary_kV=13.8,
        secondary_kV=0.48,
        impedance_pct=6.5,
        x_over_r=12.0,
    ),
    TransformerModel(
        model_id="ABB-Resibloc-5000kVA-34500-13800",
        manufacturer="ABB",
        full_name="ABB Resibloc 5000 kVA 34.5/13.8 kV",
        rated_S_kVA=5000.0,
        primary_kV=34.5,
        secondary_kV=13.8,
        impedance_pct=7.0,
        x_over_r=15.0,
    ),
    TransformerModel(
        model_id="WEG-Power-25000kVA-138-13800",
        manufacturer="WEG",
        full_name="WEG Power 25 MVA 138/13.8 kV",
        rated_S_kVA=25000.0,
        primary_kV=138.0,
        secondary_kV=13.8,
        impedance_pct=10.5,
        x_over_r=25.0,
    ),
]


# ---------------------------------------------------------------------------
# Curated breaker library
# ---------------------------------------------------------------------------


_BREAKERS: list[BreakerModel] = [
    # ABB
    BreakerModel(
        model_id="ABB-HD4-12kV-1250A",
        manufacturer="ABB",
        full_name="ABB HD4 Vacuum Circuit Breaker",
        voltage_class=VoltageClass.MV,
        rated_voltage_kV=12.0,
        rated_current_A=1250.0,
        breaking_capacity_kA=25.0,
        arc_quenching="vacuum",
        operating_time_ms=45.0,
    ),
    BreakerModel(
        model_id="ABB-HV4-72.5kV-2000A",
        manufacturer="ABB",
        full_name="ABB HV4 SF6 Circuit Breaker",
        voltage_class=VoltageClass.HV,
        rated_voltage_kV=72.5,
        rated_current_A=2000.0,
        breaking_capacity_kA=40.0,
        arc_quenching="SF6",
        operating_time_ms=50.0,
        reclosing_supported=True,
    ),
    # Siemens
    BreakerModel(
        model_id="Siemens-8DJH-12kV",
        manufacturer="Siemens",
        full_name="Siemens 8DJH Vacuum CB 12kV",
        voltage_class=VoltageClass.MV,
        rated_voltage_kV=12.0,
        rated_current_A=630.0,
        breaking_capacity_kA=25.0,
        arc_quenching="vacuum",
    ),
    BreakerModel(
        model_id="Siemens-3WL-LV",
        manufacturer="Siemens",
        full_name="Siemens 3WL Air Circuit Breaker",
        voltage_class=VoltageClass.LV,
        rated_voltage_kV=0.69,
        rated_current_A=2000.0,
        breaking_capacity_kA=85.0,
        arc_quenching="air",
        operating_time_ms=30.0,
    ),
    BreakerModel(
        model_id="Siemens-8DA-145kV",
        manufacturer="Siemens",
        full_name="Siemens 8DA SF6 145kV",
        voltage_class=VoltageClass.HV,
        rated_voltage_kV=145.0,
        rated_current_A=2500.0,
        breaking_capacity_kA=63.0,
        arc_quenching="SF6",
        operating_time_ms=40.0,
        reclosing_supported=True,
    ),
]


# ---------------------------------------------------------------------------
# Public lookup API
# ---------------------------------------------------------------------------


def list_relays(
    *,
    application: Optional[RelayApplication] = None,
    voltage_class: Optional[VoltageClass] = None,
    vendor: Optional[str] = None,
    iec_61850_only: bool = False,
) -> list[RelayModel]:
    """Lista relés filtrados."""
    items = list(_RELAYS)
    if application is not None:
        items = [r for r in items if r.application == application]
    if voltage_class is not None:
        items = [r for r in items if r.voltage_class == voltage_class]
    if vendor is not None:
        items = [
            r for r in items
            if r.manufacturer.lower() == vendor.lower()
        ]
    if iec_61850_only:
        items = [r for r in items if r.iec_61850]
    return items


def get_relay(model_id: str) -> Optional[RelayModel]:
    """Busca relé por model_id (case-insensitive)."""
    for r in _RELAYS:
        if r.model_id.lower() == model_id.lower():
            return r
    return None


def list_motors(
    *,
    vendor: Optional[str] = None,
    min_kW: Optional[float] = None,
    max_kW: Optional[float] = None,
    voltage_V: Optional[float] = None,
) -> list[MotorModel]:
    """Lista motores filtrados."""
    items = list(_MOTORS)
    if vendor is not None:
        items = [
            m for m in items
            if m.manufacturer.lower() == vendor.lower()
        ]
    if min_kW is not None:
        items = [m for m in items if m.rated_power_kW >= min_kW]
    if max_kW is not None:
        items = [m for m in items if m.rated_power_kW <= max_kW]
    if voltage_V is not None:
        items = [
            m for m in items
            if abs(m.rated_voltage_V - voltage_V) < voltage_V * 0.05
        ]
    return items


def get_motor(model_id: str) -> Optional[MotorModel]:
    for m in _MOTORS:
        if m.model_id.lower() == model_id.lower():
            return m
    return None


def list_transformers(
    *,
    vendor: Optional[str] = None,
    min_kVA: Optional[float] = None,
    max_kVA: Optional[float] = None,
) -> list[TransformerModel]:
    items = list(_TRANSFORMERS)
    if vendor is not None:
        items = [
            t for t in items
            if t.manufacturer.lower() == vendor.lower()
        ]
    if min_kVA is not None:
        items = [t for t in items if t.rated_S_kVA >= min_kVA]
    if max_kVA is not None:
        items = [t for t in items if t.rated_S_kVA <= max_kVA]
    return items


def get_transformer(model_id: str) -> Optional[TransformerModel]:
    for t in _TRANSFORMERS:
        if t.model_id.lower() == model_id.lower():
            return t
    return None


def list_breakers(
    *,
    vendor: Optional[str] = None,
    voltage_class: Optional[VoltageClass] = None,
    min_kA: Optional[float] = None,
) -> list[BreakerModel]:
    items = list(_BREAKERS)
    if vendor is not None:
        items = [
            b for b in items
            if b.manufacturer.lower() == vendor.lower()
        ]
    if voltage_class is not None:
        items = [b for b in items if b.voltage_class == voltage_class]
    if min_kA is not None:
        items = [b for b in items if b.breaking_capacity_kA >= min_kA]
    return items


def get_breaker(model_id: str) -> Optional[BreakerModel]:
    for b in _BREAKERS:
        if b.model_id.lower() == model_id.lower():
            return b
    return None


# ---------------------------------------------------------------------------
# Curated trip-unit library (LSIG) — fontes oficiais por entrada
# ---------------------------------------------------------------------------


def _sr(min_: float, max_: float, step: Optional[float] = None, *,
        unit: str = "xIn", default: Optional[float] = None,
        discrete: tuple[float, ...] = (), off: bool = False) -> SettingRange:
    return SettingRange(min=min_, max=max_, step=step, unit=unit,
                        default=default, discrete=discrete, off_selectable=off)


def _dial(values: tuple[float, ...], *, unit: str = "xIn",
          default: Optional[float] = None, off: bool = False) -> SettingRange:
    return SettingRange(min=min(values), max=max(values), unit=unit,
                        default=default, discrete=values, off_selectable=off)


_TRIP_UNITS: list[TripUnitModel] = [
    # ABB — SACE Tmax XT2-XT4, Ekip Touch/Hi-Touch (IEC)
    # Fonte: 1SDH002031A1002 Rev. B, págs. 35-40, 78
    TripUnitModel(
        model_id="ABB-XT2-XT4-EKIP-TOUCH-LSIG",
        manufacturer="ABB",
        full_name="SACE Tmax XT2-XT4 Ekip Touch / Hi-Touch LSIG",
        breaker_family="Tmax XT2/XT4",
        category="MCCB",
        market_standard="IEC 60947-2 (curvas IEC 60255-151 opcionais)",
        source_doc="ABB 1SDH002031A1002 Rev. B (Ekip Touch user manual)",
        adjustment_mode="fine_digital",
        functions_available=("L", "S", "S2", "I", "G"),
        L_pickup_Ir=_sr(0.4, 1.0, 0.001, default=1.0),
        L_delay_tr=_sr(3.0, 60.0, 1.0, unit="s", default=60.0),
        tr_reference_multiple=3.0,
        S_pickup_Isd=_sr(0.6, 10.0, 0.1, unit="xIn", default=2.0, off=True),
        S_delay_tsd=_sr(0.05, 0.4, 0.01, unit="s", default=0.05),
        S_i2t_selectable=True,
        I_pickup_Ii=_sr(1.5, 10.0, 0.1, default=4.0, off=True),
        G_pickup_Ig=_sr(0.1, 1.0, 0.001, default=0.2, off=True),
        G_delay_tg=_sr(0.1, 1.0, 0.05, unit="s", default=0.4),
        G_i2t_selectable=True,
        curve_options=(
            "L: t=k/I2 (IEC 60947-2)", "L: IEC 60255-151 SI",
            "L: IEC 60255-151 VI", "L: IEC 60255-151 EI", "L: t=k/I4",
            "S/G: t=k ou t=k/I2",
        ),
        notes=(
            "Isd em xIn (não xIr). Fórmula L (t=k/I2): tt = 9·t1/(If/I1)^2 "
            "(t1 = tempo em 3×I1). Interlocks: I1<I2<I3. S2 (I5 0.6-10 xIn, "
            "t5 0.05-0.4 s) estágio independente. tt forçado a 1 s se "
            "If>12 In. S, I e G possuem parâmetro Enable ON/OFF (default "
            "OFF) — representado por off_selectable. Com curva t=k, t4 "
            "também pode ser configurado como 'instantâneo'."
        ),
    ),
    # ABB — Tmax XT5 Ekip DIP (UL 489) — TCC 9AKK108468A0480 (abr/2023)
    TripUnitModel(
        model_id="ABB-XT5-EKIP-DIP-LSI-LSIG-UL",
        manufacturer="ABB",
        full_name="Tmax XT5 Ekip DIP LSI/LSIG (Short Time I2T OFF)",
        breaker_family="Tmax XT5 (250/400 A, 300/600 A)",
        category="MCCB",
        market_standard="UL (catálogo UL, 600 Vac; norma não declarada no TCC)",
        source_doc="ABB Electrification 9AKK108468A0480 (TCC, 2023-04)",
        adjustment_mode="discrete_dial",
        functions_available=("L", "S", "I"),
        L_pickup_Ir=_sr(0.4, 1.0, 0.02),
        L_delay_tr=_dial((3.0, 12.0, 36.0, 48.0), unit="s"),
        tr_reference_multiple=3.0,
        S_pickup_Isd=_dial((1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.5, 5.5, 6.5,
                            7.0, 7.5, 8.0, 8.5, 9.0, 10.0), off=True),
        S_delay_tsd=_dial((0.05, 0.1, 0.2, 0.4), unit="s"),
        S_i2t_selectable=False,
        I_pickup_Ii=_dial((1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.5, 5.5, 6.5,
                           7.0, 7.5, 8.0, 8.5, 9.0, 10.0), off=True),
        rated_voltage_V=600.0,
        notes=(
            "Variante I2T OFF (tempo definido). Isd em xIn. Override "
            "instantâneo fixo 8000 A (+25%/-15.62%) com I3=OFF. Curva de "
            "terra em TCC 9AKK108468A0479 (não digitalizada)."
        ),
    ),
    # ABB — Emax E2.2 Ekip Touch/Hi-Touch (UL) — TCC 9AKK108468A2275 (jun/2023)
    TripUnitModel(
        model_id="ABB-EMAX-E2.2-EKIP-TOUCH-LSI-LSIG-UL",
        manufacturer="ABB",
        full_name="Emax E2.2 Ekip Touch/Hi-Touch LSI/LSIG (Short Time I2T OFF)",
        breaker_family="Emax E2.2 (In 250-1200 / 400-1600 / 800-2000 A)",
        category="ACB",
        market_standard="UL (tsd conforme IEEE/ANSI C37.17; norma UL não declarada no TCC)",
        source_doc="ABB Electrification 9AKK108468A2275 (TCC, 2023-06)",
        adjustment_mode="fine_digital",
        functions_available=("L", "S", "I"),
        L_pickup_Ir=_sr(0.400, 1.000, 0.001),
        L_delay_tr=_sr(3.0, 144.0, 1.0, unit="s"),
        tr_reference_multiple=3.0,
        S_pickup_Isd=_sr(0.6, 10.0, 0.1, unit="xIn"),
        S_delay_tsd=_sr(0.05, 0.4, 0.01, unit="s"),
        S_i2t_selectable=False,
        I_pickup_Ii=_sr(1.5, 15.0, 0.1),
        rated_voltage_V=635.0,
        notes=(
            "Isd em xIn. Voltage rating 635 Vac. Ajuste de pickup (override) "
            "por interrupting rating: B-A/N-A/S-A 65 000 A (-15.38 %/+0 %), "
            "V-A/H-A 85 000 A (-11.76 %/+0 %). Curva de terra em TCC "
            "9AKK108468A2168 (não digitalizada)."
        ),
    ),
    # ABB — SACE Tmax XT7, Ekip Touch/Hi-Touch (IEC) — TCC/manual
    # Fonte: ABB 1SDH001821A1002 Rev. B (Ekip Touch user manual, XT7),
    # págs. 5-6 (famílias), 40-44 (L/S/S2/I/G), 84-85 (fórmulas/tolerâncias)
    TripUnitModel(
        model_id="ABB-XT7-EKIP-TOUCH-LSIG",
        manufacturer="ABB",
        full_name="SACE Tmax XT7 Ekip Touch / Hi-Touch / G-Hi-Touch LSIG",
        breaker_family="Tmax XT7 (800-1600 A)",
        category="MCCB",
        market_standard="IEC 60947-2",
        source_doc="ABB 1SDH001821A1002 Rev. B (Ekip Touch user manual, XT7)",
        adjustment_mode="fine_digital",
        functions_available=("L", "S", "S2", "I", "G"),
        L_pickup_Ir=_sr(0.4, 1.0, 0.001, default=1.0),
        L_delay_tr=_sr(3.0, 144.0, 1.0, unit="s", default=144.0),
        tr_reference_multiple=3.0,
        S_pickup_Isd=_sr(0.6, 10.0, 0.1, unit="xIn", default=2.0, off=True),
        S_delay_tsd=_sr(0.05, 0.8, 0.01, unit="s", default=0.05),
        S_i2t_selectable=True,
        I_pickup_Ii=_sr(1.5, 15.0, 0.1, default=4.0, off=True),
        G_pickup_Ig=_sr(0.1, 1.0, 0.001, default=0.2, off=True),
        G_delay_tg=_sr(0.1, 1.0, 0.05, unit="s", default=0.4),
        G_i2t_selectable=True,
        curve_options=(
            "L: t=k/I2 (IEC 60947-2)", "L: IEC 60255-151 SI",
            "L: IEC 60255-151 VI", "L: IEC 60255-151 EI", "L: t=k/I4",
            "S/G: t=k ou t=k/I2",
        ),
        rated_voltage_V=690.0,
        notes=(
            "Isd/Ii/Ig em xIn (não xIn da placa de corrente do rating "
            "plug, mas do próprio In configurado). Fórmula L (t=k/I2): "
            "tt = 9·t1/(If/I1)^2 (t1 = tempo em 3×I1, idêntica à XT2-XT4). "
            "S2 (I5 0.6-10 xIn, t5 0.05-0.8 s) estágio independente de S. "
            "tt forçado a 1 s se If>12 In. S, I e G possuem parâmetro "
            "Enable ON/OFF (default OFF). Frame 800-1600 A (rating plug). "
            "Protações adicionais não modeladas neste dataclass (fora do "
            "escopo LSIG): MCR, 2I, IU[46] desbalanço, D[67] direcional, "
            "UV/OV[27/59], UF/OF[81], RP[32R] — ver fonte."
        ),
    ),
    # ABB — SACE Emax 2 E1.2/E2.2/E4.2/E6.2, Ekip Touch/Hi-Touch (IEC)
    # Fonte: ABB 1SDH001316R0002 Rev. C, pág. 12-14 (tabela-resumo de
    # proteções básicas + tabela de parâmetros IEC 60255-151 a/b/k)
    TripUnitModel(
        model_id="ABB-EMAX2-EKIP-TOUCH-LSIG-IEC",
        manufacturer="ABB",
        full_name="SACE Emax 2 Ekip Touch / Hi-Touch / G-Hi-Touch LSIG (IEC)",
        breaker_family="Emax 2 E1.2/E2.2/E4.2/E6.2 (400-6300 A)",
        category="ACB",
        market_standard="IEC 60947-2",
        source_doc="ABB 1SDH001316R0002 Rev. C (Ekip Touch instructions, Emax 2)",
        adjustment_mode="fine_digital",
        functions_available=("L", "S", "I", "G"),
        L_pickup_Ir=_sr(0.4, 1.0, 0.001),
        L_delay_tr=_sr(3.0, 144.0, 1.0, unit="s"),
        tr_reference_multiple=3.0,
        S_pickup_Isd=_sr(0.6, 10.0, 0.1, unit="xIn"),
        S_delay_tsd=_sr(0.05, 0.8, 0.01, unit="s"),
        S_i2t_selectable=True,
        I_pickup_Ii=_sr(1.5, 15.0, 0.1, off=True),
        G_pickup_Ig=_sr(0.1, 1.0, 0.001, off=True),
        G_delay_tg=_sr(0.1, 1.0, 0.05, unit="s"),
        G_i2t_selectable=True,
        curve_options=(
            "L: t=k/I2 (IEC 60947-2), tt=9·t1/(If/I1)^2",
            "L: IEC 60255-151 SI (a=0.02 b=0.15873 k=0.16)",
            "L: IEC 60255-151 VI (a=1 b=0.148148 k=13.7)",
            "L: IEC 60255-151 EI (a=2 b=0.1 k=82)",
            "L: t=k/I4 (a=4 b=1 k=82)",
            "S: t=k ou t=k/I2 (tt=100·t2/If^2, If em xIn)",
            "G: t=k ou t=k/I2 (tt=2/(If/I4)^2 — constante fixa, não escala com t4 na fonte)",
        ),
        rated_voltage_V=1150.0,
        notes=(
            "Tabela-resumo válida para E1.2/E2.2/E4.2/E6.2 (mesma plataforma "
            "Ekip Touch; In real definido pelo rating plug por frame: E1.2 "
            "400-1600 A, E4.2 400-4000 A, E6.2 400-6300 A). Ue padrão "
            "690 V, disponível até 1150 V AC conforme catálogo técnico. "
            "Defaults de fábrica não digitalizados (remetidos ao 'Engineering "
            "Manual' 1SDH001330R0002, não obtido). G: mínimo real de "
            "autoalimentação 0.3 In (In=100 A) / 0.25 In (In=400 A) / 0.2 In "
            "(demais). I3/I31 (2I) não ajustáveis em tempo (<30 ms); MCR "
            "40-500 ms não modelado. Curva IEC 60255-151 usa t1 (s) direto "
            "como escala (não TMS 0-1): fórmula tt=(t1·k·b)/((If/I1)^a-1), "
            "coeficientes a/b/k acima são os PRÓPRIOS da ABB para este "
            "produto — não coincidem com os universais (SI k=0.14 vs "
            "0.16·0.15873≈0.0254 aqui); ver vendor_curve_constants.py para "
            "a família IEC universal usada pelos relés IED. ATENÇÃO: o "
            "manual-fonte imprime a fórmula de forma inconsistente entre a "
            "tabela-resumo (pág. 12: expoente 'k') e a tabela detalhada de "
            "coeficientes (pág. 13: expoente 'a', usada acima); o exemplo "
            "numérico da própria fonte para SI (I1=0.4In, t1=3s, If=0.8In → "
            "tt=4.78s) não fecha com nenhuma das duas leituras — provável "
            "erro tipográfico/de extração do PDF original da ABB, não do "
            "código (mantida a leitura estruturalmente mais plausível, com "
            "expoente 'a' consistente com os universais α=0.02/1/2/4). I "
            "possui estado Off (mutuamente exclusivo com MCR, notas (2)/(3) "
            "da fonte) — off_selectable=True. G no modo "
            "t=k/I2 (51N): fórmula impressa usa constante fixa '2', "
            "aparentemente independente do ajuste t4 (0.1-1 s) — "
            "inconsistência da própria fonte, preservada como impressa "
            "(verificada por exemplo numérico do manual: I4=0.8In, t4=0.2s, "
            "If=2In → tt=0.32s = 2/(2/0.8)²). Variante UL do mesmo produto: "
            "teto de tg 0.4 s e de Ig 1200 A (não modelada aqui — ver "
            "ABB-EMAX-E2.2-EKIP-TOUCH-LSI-LSIG-UL para a entrada UL)."
        ),
    ),
    # Schneider — ComPact NSX Micrologic 5/6/7 (IEC) — DOCA0141EN-03
    TripUnitModel(
        model_id="SE-NSX-MICROLOGIC-5-6-7",
        manufacturer="Schneider Electric",
        full_name="ComPact NSX Micrologic 5.x / 6.x / 7.x",
        breaker_family="ComPact NSX 100-630 A",
        category="MCCB",
        market_standard="IEC/EN 60947-2",
        source_doc="Schneider DOCA0141EN-03 (págs. 54-61)",
        adjustment_mode="fine_digital",
        functions_available=("L", "S", "I", "G"),
        L_pickup_Ir=_sr(0.4, 1.0, unit="xIn", default=1.0),
        L_delay_tr=_dial((0.5, 1.0, 2.0, 4.0, 8.0, 16.0), unit="s", default=16.0),
        tr_reference_multiple=6.0,
        S_pickup_Isd=_dial((1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0),
                           unit="xIr", default=1.5),
        S_delay_tsd=_dial((0.0, 0.1, 0.2, 0.3, 0.4), unit="s", default=0.0),
        S_i2t_selectable=True,
        I_pickup_Ii=_sr(1.5, 15.0, 0.5, default=15.0),
        G_pickup_Ig=_sr(0.2, 1.0, 0.05, default=0.2, off=True),
        G_delay_tg=_dial((0.0, 0.1, 0.2, 0.3, 0.4), unit="s", default=0.0),
        G_i2t_selectable=True,
        notes=(
            "Ir pré-ajustado por dial em A (ex. In=250 A: 100..250 A; dial "
            "mín 0.4 xIn para In≥100 A, 18 A = 0.45 xIn para In=40 A), fino "
            "no teclado passo 1 A, mín. 0.9×menor dial (In=400 A: mín 100 A); "
            "faixa 1.05-1.20 Ir. tr tabela: 1.5×Ir {15,25,50,100,200,400} s; "
            "7.2×Ir {0.35,0.7,1.4,2.8,5.5,11} s. Isd: dial ML5 (lista "
            "discreta) com ajuste fino no teclado 1.5-dial passo 0.5 xIr; "
            "ML6/7 teclado 1.5-10 xIr passo 0.5. Ii default = máximo do "
            "rating: 15/12/11 xIn para In 100-160/250-400/630 A. tsd=0 e "
            "tg=0 só com I2t OFF. G só Micrologic 6 (Micrologic 7: proteção "
            "diferencial IΔn/Δt, não modelada); Ig mín 0.4 xIn para In=40 A. "
            "tsd hold {20,80,140,230,350} ms (tg: 360 ms em 0.4 s), break "
            "máx {80,140,200,320,500} ms."
        ),
    ),
    # Schneider — MasterPact MTZ Micrologic X — DOCA0102EN-07
    TripUnitModel(
        model_id="SE-MTZ-MICROLOGIC-X",
        manufacturer="Schneider Electric",
        full_name="MasterPact MTZ Micrologic 2.0X/3.0X/5.0X/6.0X/7.0X",
        breaker_family="MasterPact MTZ1/MTZ2/MTZ3",
        category="ACB",
        market_standard="IEC (2.0X/5.0X/6.0X/7.0X) e UL (UL489SE; 3.0X/5.0X/6.0X)",
        source_doc="Schneider DOCA0102EN-07 (págs. 100-114, 158-160)",
        adjustment_mode="fine_digital",
        functions_available=("L", "S", "I", "G"),
        L_pickup_Ir=_sr(0.4, 1.0, default=1.0),
        L_delay_tr=_sr(0.5, 24.0, 0.5, unit="s", default=0.5),
        tr_reference_multiple=6.0,
        S_pickup_Isd=_sr(1.5, 10.0, 0.5, unit="xIr", default=1.5),
        S_delay_tsd=_sr(0.0, 0.4, 0.1, unit="s", default=0.0),
        S_i2t_selectable=True,
        I_pickup_Ii=_sr(2.0, 15.0, 0.5, default=2.0),
        G_pickup_Ig=_sr(0.2, 1.0, default=0.2, off=True),
        G_delay_tg=_sr(0.0, 0.4, 0.1, unit="s", default=0.0),
        G_i2t_selectable=True,
        curve_options=(
            "L: térmica padrão",
            "IDMTL DT / SIT / VIT / EIT / HVF (todas via módulo digital "
            "ANSI 51 opcional, LV850037)",
        ),
        notes=(
            "Passos: Ir 1 A; Isd 0.5 xIr e Ii 0.5 xIn (resolução mais fina "
            "via software EcoStruxure Power Commission/app, não pelo display); "
            "Ig 10 A (IEC) ou 0.1 xIn (UL). tr fábrica 0.5 s (três ocorrências "
            "consistentes no manual; atipicamente rápido — confirmar em campo). "
            "S em 5.0X/6.0X/7.0X (IEC) e 5.0X/6.0X (UL); G apenas 6.0X (7.0X: "
            "proteção diferencial IΔn, não modelada). Ii 2-15 xIn vale para "
            "5.0X+; 3.0X (UL): 1.5-12 xIn, fábrica 1.5; 2.0X sem Ii. Ii "
            "desabilitável só em 5.0X+. Ig OFF só na versão IEC (UL: sempre "
            "ON). Ig 0.3-1 xIn se In≤400 A (IEC e UL); UL In>1200 A: 500-1200 A "
            "absoluto. tsd=0 e tg=0 só com I2t OFF (se tg=0 e I2t→ON, tg vai "
            "a 0.1 s). tr tabela 1.5×Ir {12.5,25,50,100,200,300,400,500,600} s."
        ),
    ),
    # Schneider (Square D) — MasterPact NT/NW Micrologic 2.0A/3.0A/5.0A/6.0A
    # (mercado UL) — Instruction Bulletin 48049-136-05 Rev. 03, 06/2020
    TripUnitModel(
        model_id="SE-NT-NW-MICROLOGIC-2-3-5-6.0A",
        manufacturer="Schneider Electric",
        full_name="MasterPact NT/NW MicroLogic 2.0A / 3.0A / 5.0A / 6.0A (Square D)",
        breaker_family="MasterPact NT/NW",
        category="ACB",
        market_standard="UL/ANSI (Square D; Ii=UL/ANSI instantâneo, Isd=IEC instantâneo)",
        source_doc="Schneider (Square D) 48049-136-05 Rev. 03, 06/2020",
        adjustment_mode="discrete_dial",
        functions_available=("L", "S", "I", "G"),
        L_pickup_Ir=_dial((0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 1.0)),
        L_delay_tr=_dial((0.5, 1.0, 2.0, 4.0, 8.0, 12.0, 16.0, 20.0, 24.0), unit="s"),
        tr_reference_multiple=6.0,
        S_pickup_Isd=_dial((1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0), unit="xIr"),
        S_delay_tsd=_dial((0.0, 0.1, 0.2, 0.3, 0.4), unit="s"),
        S_i2t_selectable=True,
        I_pickup_Ii=_dial((2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0, 15.0), off=True),
        G_pickup_Ig=_dial((0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0), off=False),
        G_delay_tg=_dial((0.0, 0.1, 0.2, 0.3, 0.4), unit="s"),
        G_i2t_selectable=True,
        curve_options=("S/G: I²t ON (inverso até 10×Ir/In) ou I²t OFF (tempo fixo)",),
        notes=(
            "Família com 4 variantes de funções: 2.0A (só L; I via Isd com "
            "tsd=0 de fábrica, base Ir — dial Isd 1.5-10×Ir); 3.0A (L+I, sem "
            "S; Ii base In, dial 1.5-12×In); 5.0A (L+S+I, sem G); 6.0A "
            "(L+S+I+G, completa — modelada aqui). tr também tabelado a "
            "1.5×Ir {12.5,25,50,100,200,300,400,500,600} s e a 7.2×Ir "
            "{0.343,0.69,1.38,2.7,5.5,8.3,11,13.8,16.6} s (mesmos 9 dials); "
            "com tsd=0.4-on ou 4.0-off, tr=0.5 em vez de 0.34 (5.0A/6.0A). "
            "Trip threshold Ir real: 1.05-1.20×Ir. tsd/tg: dial rotula o "
            "tempo a 10×Ir/In com I²t OFF; tolerância min/max real 20-80/"
            "80-140/140-200/230-320/350-500 ms (S) e igual para G. Ig por "
            "faixa de In: {0.3,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0}×In se "
            "In≤400 A (posição A=0.3, não 0.2 — dial acima é para "
            "400<In≤1200 A); para In>1200 A, Ig em A absoluto: "
            "{500,640,720,800,880,960,1040,1120,1200}. Ii possui posição "
            "Off (5.0A/6.0A). Corrente de defeito de terra nominal do "
            "equipamento: 1200 A."
        ),
    ),
    # WEG — ABW-OCR Tipo P (ACB) — Manual Disjuntor Aberto ABW, págs. 13-14
    TripUnitModel(
        model_id="WEG-ABW-OCR-TIPO-P",
        manufacturer="WEG",
        full_name="ABW-OCR Tipo P (PC1/PC6) — unidade de proteção ACB",
        breaker_family="ABW16...63",
        category="ACB",
        market_standard="IEC (norma não citada no catálogo digitalizado)",
        source_doc="WEG Catálogo Disjuntor Aberto ABW 50011456.05/062010, págs. 13-14",
        adjustment_mode="discrete_dial",
        functions_available=("L", "S", "I", "G"),
        L_pickup_Ir=_dial((0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)),
        L_delay_tr=_dial((0.5, 1.0, 2.0, 4.0, 8.0, 12.0, 16.0, 20.0),
                         unit="s", off=True),
        tr_reference_multiple=6.0,
        S_pickup_Isd=_dial((1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0),
                           unit="xIr", off=True),
        S_delay_tsd=_dial((0.05, 0.1, 0.2, 0.3, 0.4), unit="s"),
        S_i2t_selectable=True,
        I_pickup_Ii=_dial((2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0, 15.0), off=True),
        G_pickup_Ig=_dial((0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0), off=True),
        G_delay_tg=_dial((0.05, 0.1, 0.2, 0.3, 0.4), unit="s"),
        G_i2t_selectable=True,
        rated_voltage_V=690.0,
        notes=(
            "tsd impresso no catálogo como '(0,05-0,1-0,2-0,3-0,4) x Ir' e tg "
            "sem unidade — erro tipográfico da fonte; a única unidade "
            "fisicamente coerente para retardo é segundos. I2t ON: "
            "{0.1,0.2,0.3,0.4} s. Tipo A (AZ1/AC1) usa ajuste em dois "
            "estágios: Iu {0.5..1.0} xIn × Ir {0.8,0.83,0.85,0.88,0.89,0.9,"
            "0.93,0.95,0.98,1.0} xIu. Interlock Ir<Is<Ii não explicitado no "
            "manual."
        ),
    ),
    # WEG — ACW ETS (MCCB — NÃO disjuntor aberto), disparador eletrônico
    # LSI — Catálogo "Disjuntor em Caixa Moldada de Alta Capacidade ACW"
    # 50022907. Confirmado: WEG não possui segunda linha de disjuntor
    # aberto além do ABW/ABWC — ACW é caixa moldada, categoria à parte.
    TripUnitModel(
        model_id="WEG-ACW-ETS-LSI",
        manufacturer="WEG",
        full_name="ACW ETS400/ETS630/ETS800 — disparador eletrônico LSI",
        breaker_family="ACW400/ACW630/ACW800 (MCCB alta capacidade, 400-800 A)",
        category="MCCB",
        market_standard="IEC 60947-2 (norma não declarada explicitamente no catálogo)",
        source_doc="WEG Catálogo Disjuntor em Caixa Moldada de Alta Capacidade ACW, doc. 50022907",
        adjustment_mode="discrete_dial",
        functions_available=("L", "S", "I"),
        L_pickup_Ir=_dial((0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8,
                          0.85, 0.9, 0.95, 1.0)),
        L_delay_tr=None,
        tr_reference_multiple=6.0,
        S_pickup_Isd=_dial((1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0),
                           unit="xIr"),
        S_delay_tsd=_dial((0.05, 0.1, 0.2, 0.3), unit="s"),
        S_i2t_selectable=False,
        I_pickup_Ii=_dial((11.0,)),
        notes=(
            "Único disparador eletrônico da linha ACW (frames ACW100/160/250 "
            "usam disparadores termomagnéticos FMU/ATU, não modelados aqui "
            "por não terem proteção L/S/I eletrônica comparável). Diferente "
            "da linha ABW (disjuntor aberto): sem função G, sem opção I²t, "
            "sem curva selecionável. tr NÃO é ajustável — a fonte informa "
            "apenas que a tolerância de disparo é verificada em 6×Ir "
            "(±20 %), sem publicar o valor de tempo em si; L_delay_tr "
            "deixado em branco por ausência de dado, não por omissão. Ii "
            "fixo em 11×In, sem dial (I_pickup_Ii modelado como valor único "
            "discreto). tsd convertido de ms para s (50/100/200/300 ms). "
            "Referências por frame: ACW400H-ETS400-3 (160-400 A), "
            "ACW630H-ETS630-3 (252-630 A), ACW800U-ETS800-3 (320-800 A)."
        ),
    ),
    # Siemens — SENTRON 3WA, disparador eletrônico ETU600 (sucessor do
    # 3WL) — Equipment Manual MAN_92310000002-04, ed. 08/2021, IEC 60947-2
    TripUnitModel(
        model_id="SIEMENS-3WA-ETU600",
        manufacturer="Siemens",
        full_name="SENTRON 3WA ETU600 LSI / LSIG / LSIG Hi-Z",
        breaker_family="3WA1 Size 1/2/3 (630-6300 A)",
        category="ACB",
        market_standard="IEC 60947-2",
        source_doc="Siemens 3WA Equipment Manual MAN_92310000002-04, ed. 08/2021",
        adjustment_mode="fine_digital",
        functions_available=("L", "S", "I", "N", "G"),
        # Ajuste contínuo 'e.SET' (display/software) como faixa primária —
        # inclui o default de fábrica Ir=0.4×In, que fica FORA da faixa da
        # chave rotativa (0.5-1.0×In, 9 posições). As posições discretas da
        # chave rotativa (base xIr para S/I, distinta de xIn do e.SET) e os
        # tetos dependentes do disjuntor (0.8×Icw, 0.8×Ics) ficam em notes.
        L_pickup_Ir=_sr(0.4, 1.0, unit="xIn", default=0.4),
        L_delay_tr=_sr(0.5, 30.0, unit="s", default=0.5),
        tr_reference_multiple=6.0,
        S_pickup_Isd=_sr(1.5, 10.0, unit="xIr", default=1.5),
        S_delay_tsd=_sr(0.02, 0.4, unit="s", default=0.1),
        S_i2t_selectable=True,
        I_pickup_Ii=_sr(1.5, 15.0, default=1.5),
        G_pickup_Ig=_sr(15.0, 2000.0, unit="A", default=100.0, off=True),
        G_delay_tg=_sr(0.0, 5.0, unit="s", default=0.1),
        G_i2t_selectable=True,
        curve_options=(
            "L: I²t ou I⁴t (tr a I²t: 0.5-30 s; a I⁴t: 0.5-5 s)",
            "S: I0t (tempo fixo) ou I²t",
            "G: I0t/I²t/I4t/I6t (LSIG); I0t/I2t/I4t/I6t (LSIG Hi-Z, zonas UREF/REF)",
        ),
        rated_voltage_V=1000.0,
        notes=(
            "Ir/tr/Ii acima em faixa contínua 'e.SET' (xIn), unidade padrão "
            "deste dataclass. S_pickup_Isd modelado em xIr (base da chave "
            "rotativa, 1.5-10×Ir, 9 posições) — a faixa e.SET usa base "
            "DIFERENTE, xIn: 0.6×In...0.8×Icw (teto depende do Icw do "
            "disjuntor, não modelável como número fixo). Ii e.SET: "
            "1.5×In...0.8×Ics (mesmo tipo de teto dependente do disjuntor; "
            "chave rotativa 1.5-15×In, 9 posições, usada acima). Chave "
            "rotativa — demais campos: Ir {0.5,0.6,0.7,0.75,0.8,0.85,0.9,"
            "0.95,1.0}×In (SEM a posição 0.4, só via e.SET); tr(6×Ir) "
            "{1,2,5,8,10,14,17,21,25} s; tsd {0.08,0.15,0.22,0.3,0.4} s "
            "(I²t OFF) ou {0.1,0.2,0.3,0.4} s (I²t ON). Referência tsd "
            "(IST ref) ajustável 6-12×Ir (default 8, valor de fábrica). "
            "Defaults de fábrica (Anexo A.1): Ir=0.4×In, tr(6×Ir)=0.5s, "
            "Isd=0.6×In, tsd=0.1s, Ii=1.5×In, Ig=100A (size 1/2) ou 400A "
            "(size 3), tg=0.1s; G desligado de fábrica. IN (neutro): "
            "3 polos 0.2-2.0×In, 4 polos 0.2×In-In máx (não modelado — "
            "função separada da fase). Proteção reversa de potência RP "
            "(32R) e direcional dST (67, opcional) disponíveis, não "
            "modeladas (fora do escopo LSIG). Ig por método/tamanho: "
            "residual size 1/2 100-2000A, size 3 400-2000A; direto "
            "15-2000A (faixa ampla 15-2000A usada acima; default 100A é "
            "o de fábrica para size 1/2, size 3 usa 400A). tg: "
            "I²t/I⁴t/I⁶t OFF 0-5s, ON (a 3×Ig) 0-30s. Alarme Ig "
            "(não-disparo) com teto mais alto (5000A), não modelado. "
            "Tensão nominal até 1000 V CA (1150 V citado em material "
            "comercial, não confirmado no manual técnico)."
        ),
    ),
    # Eaton — NZM PXR25 (EMEA) — MN012005EN, Tabela 4
    TripUnitModel(
        model_id="EATON-NZM-PXR25",
        manufacturer="Eaton",
        full_name="NZM Power Xpert Release PXR25 (-PX…-TZ: LSIG)",
        breaker_family="NZM (EMEA)",
        category="MCCB",
        market_standard="IEC 60947-2",
        source_doc="Eaton MN012005EN 01/22, Tabelas 2-4 (págs. 12-13) e Fig. 2 (pág. 11)",
        adjustment_mode="fine_digital",
        functions_available=("L", "S", "I", "G"),
        L_pickup_Ir=_sr(0.4, 1.0),
        L_delay_tr=_sr(2.0, 20.0, 0.1, unit="s", off=True),
        tr_reference_multiple=6.0,
        S_pickup_Isd=_sr(2.0, 10.0, unit="xIr"),
        S_delay_tsd=_sr(0.0, 1.0, 0.01, unit="s"),
        S_i2t_selectable=True,
        I_pickup_Ii=_sr(2.0, 18.0),
        G_pickup_Ig=_sr(0.2, 1.0, off=True),
        G_delay_tg=_sr(0.0, 1.0, 0.01, unit="s"),
        G_i2t_selectable=True,
        notes=(
            "Incrementos de Ir/Isd/Ii/Ig em 1 A absoluto (Tabela 4; a tabela "
            "de registros Modbus do mesmo manual indica passos de 0,1 xIr/xIn "
            "para Isd/Ii/Ig); tsd/tg 0-1000 ms passo 10 ms; Ig Alarm/Trip/OFF. "
            "Disponibilidade por variante: PXR10-AX (L+I), PXR20-MX (L+tr+I), "
            "PXR20-VX (+S), PXR20-VX-T (+G), PXR25-PX (LSI), PXR25-PMX "
            "(L+tr+I), PXR25-PX…-TZ (LSIG). "
            "Dial PXR10/20: Ir {0.4..1.0}, Isd {2,3,4,5,6,6.5,7,7.5,8,8.5,9,"
            "9.5,10} xIr, Ii {2,4,6,8,10,11..18} xIn, tr {2,4,5,6,7,8,10,12,"
            "14,16,18,20,∞} s."
        ),
    ),
    # Eaton — Magnum Digitrip 1150/1150i (ACB) — IL 70C1036H04
    TripUnitModel(
        model_id="EATON-MAGNUM-DIGITRIP-1150",
        manufacturer="Eaton",
        full_name="Magnum / Magnum DS Digitrip 1150 & 1150i",
        breaker_family="Magnum DS",
        category="ACB",
        market_standard="UL/ANSI (curvas IEEE C37.112 e IEC 60255 opcionais)",
        source_doc="Eaton I.L. 70C1036H04 (11/2003), §4.2.1",
        adjustment_mode="fine_digital",
        functions_available=("L", "S", "I", "G"),
        L_pickup_Ir=_sr(0.4, 1.0, 0.05),
        L_delay_tr=_sr(2.0, 24.0, 0.5, unit="s"),
        tr_reference_multiple=6.0,
        S_pickup_Isd=_sr(1.5, 10.0, 0.5, unit="xIr"),
        S_delay_tsd=_sr(0.10, 0.50, 0.05, unit="s"),
        S_i2t_selectable=True,
        I_pickup_Ii=_sr(2.0, 14.0, 0.5, off=True),
        G_pickup_Ig=_sr(0.24, 1.0, 0.01),
        G_delay_tg=_sr(0.10, 0.50, 0.05, unit="s"),
        G_i2t_selectable=True,
        curve_options=(
            "L: I2T (45 ajustes 2-24 s)", "L: I4T (9 ajustes 1-5 s)",
            "IEEE MI/VI/EI (PC37.112)", "IEC-A/B/C (IEC 255)",
        ),
        notes=(
            "Ir 13 ajustes discretos (passo 0.05). Isd 18 ajustes 1.5-10 xIr "
            "(passo 0.5) e Ii 2-M1 (passo 0.5) mais o ajuste adicional M1, "
            "aplicável a Isd e Ii; M1 por rating plug (Standard Breaker): "
            "14× (100-1250 A), 12× (1600-2500 A), 10× (3000-3200 A); Double "
            "Wide: 14× (2000-2500 A), 12× (3200-5000 A), 10× (6000-6300 A). "
            "tsd I2T "
            "referenciado a 8×Ir, plano acima. Ig ANSI/UL limitado a 1200 A; "
            "IEC-EF 0.10-1.0 xIn. I2T de S indisponível com L em I4T/IEEE/IEC."
        ),
    ),
    # Siemens — 3VA ETU560/ETU860 LSIG — A5E03603177010-02, págs. 120-122
    TripUnitModel(
        model_id="SIEMENS-3VA-ETU560-ETU860",
        manufacturer="Siemens",
        full_name="SENTRON 3VA ETU560 / ETU860 LSIG",
        breaker_family="SENTRON 3VA (5/8-series)",
        category="MCCB",
        market_standard="IEC 60947-2",
        source_doc="Siemens A5E03603177010-02 (04/2015), §3.1 págs. 120-122",
        adjustment_mode="fine_digital",
        functions_available=("L", "S", "I", "G", "N"),
        L_pickup_Ir=_sr(0.4, 1.0),
        L_delay_tr=_sr(0.5, 25.0, 0.1, unit="s"),
        tr_reference_multiple=6.0,
        S_pickup_Isd=_sr(0.6, 10.0, unit="xIn"),
        S_delay_tsd=_sr(0.05, 0.5, 0.01, unit="s"),
        S_i2t_selectable=True,
        I_pickup_Ii=_sr(1.5, 12.0),
        G_pickup_Ig=_sr(0.2, 1.0, unit="xIn", off=True),
        G_delay_tg=_sr(0.05, 0.8, 0.01, unit="s"),
        G_i2t_selectable=True,
        notes=(
            "Isd em xIn. Passo Ir/Isd 0.5 A (<50 A) ou 1 A; Ii passo 1 A, "
            "1.5-10/12 xIn para 100-400 A (630 A: tabela própria). Ig contínuo "
            "em passos de 1 A, limite inferior 0.2/0.25/0.4/0.6 xIn conforme "
            "tamanho (o dial de 5 posições 0.2/0.25/0.4/0.6/1.0 é do ETU330). "
            "Isd máx 9/10 xIn e tr máx "
            "12/15/17/20/25 s conforme tamanho. tsd referenciado a Isd=8×Ir; "
            "tg a 2×Ig. Alarme IgA 0.2-1 xIn. Imagem térmica desativável. "
            "ETU350 LSI: Ii FIXO 9/10/11/12 xIn — possível sobreposição com "
            "Isd até 10×Ir (não resolvida na fonte)."
        ),
    ),
    # Siemens — 3WL1 ETU45B (ACB) — SENTRON LV10, págs. 34-35
    TripUnitModel(
        model_id="SIEMENS-3WL1-ETU45B",
        manufacturer="Siemens",
        full_name="SENTRON 3WL1 ETU45B",
        breaker_family="SENTRON 3WL1 (tamanhos I/II/III)",
        category="ACB",
        market_standard="IEC 60947-2",
        source_doc="Siemens 3WL1 SENTRON Configuration Manual, ed. 04/2018 (PH 0718 60 En), págs. 34-35",
        adjustment_mode="discrete_dial",
        functions_available=("L", "S", "I", "N", "G"),
        L_pickup_Ir=_dial((0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8, 0.9, 1.0)),
        L_delay_tr=_dial((2.0, 3.5, 5.5, 8.0, 10.0, 14.0, 17.0, 21.0, 25.0, 30.0),
                         unit="s"),
        tr_reference_multiple=6.0,
        S_pickup_Isd=_dial((1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0),
                           unit="xIn", off=True),
        S_delay_tsd=_dial((0.02, 0.1, 0.2, 0.3, 0.4), unit="s"),
        S_i2t_selectable=True,
        I_pickup_Ii=_dial((1.5, 2.2, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0), off=True),
        G_pickup_Ig=_dial((100.0, 300.0, 600.0, 900.0, 1200.0), unit="A", off=True),
        G_delay_tg=_dial((0.1, 0.2, 0.3, 0.4, 0.5), unit="s"),
        G_i2t_selectable=True,
        notes=(
            "Isd em xIn. S, I e G podem ser desligados (OFF). tr I4t "
            "alternativo {1,2,3,4,5} s. tsd 0.02 s = posição 'M' (proteção "
            "de motor, 20 ms), indisponível com I2t selecionado (I2t: 100-400 "
            "ms). Ii possui posição adicional do dial '0.8×Ics' (depende do "
            "Ics do disjuntor; não expressa em xIn). "
            "Ig letras A-E = 100/300/600/900/1200 A (tamanhos I/II); "
            "tamanho III: 400/600/800/1000/1200 A. G é módulo opcional "
            "retrofit (GFM AT 45B). ETU76B: faixas contínuas (Ir 0.4-1, tr 2-30 s, "
            "Isd 1.25×In-0.8×Icw, tsd 80-4000 ms, Ii 1.5×In-0.8×Ics)."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Curated fuse library — I²t de datasheets oficiais
# ---------------------------------------------------------------------------


def _fr(pn: str, A: float, i2t_min: float = 0.0, i2t_tot: float = 0.0,
        W: float = 0.0, *, I3: float = 0.0, kA: float = 0.0,
        mohm: float = 0.0) -> FuseRating:
    return FuseRating(rated_current_A=A, part_number=pn,
                      i2t_prearcing_A2s=i2t_min, i2t_total_A2s=i2t_tot,
                      min_breaking_current_I3_A=I3, power_loss_W=W,
                      breaking_capacity_kA=kA, cold_resistance_mOhm=mohm)


_BUSSMANN_10164 = "Eaton Bussmann Technical Data 10164 (2015-09), NH 500 V gG/gL"
_BUSSMANN_10165 = "Eaton Bussmann Technical Data 10165 (2017-10), NH 500/690 V aM"
_BUSSMANN_720104 = "Eaton Bussmann Technical Data 720104 (2017-09), 12 kV DIN"
_SIBA_HHM = "SIBA HHM catalogue Rev 1b (HV fuses for motor applications)"
_ABB_CEF = "ABB Catalogue 1YMB631051-en (04/2003), CEF & CMF"
_WEG_FUS = "WEG Fusíveis aR e gL/gG, catálogo 50009817"

_FUSES: list[FuseModel] = [
    FuseModel(
        model_id="BUSSMANN-NH000-GG-500V",
        manufacturer="Eaton",
        full_name="Bussmann NH tamanho 000 gG/gL 500 V a.c.",
        fuse_class="gG", rated_voltage_kV=0.5, breaking_capacity_kA=120.0,
        standard="IEC 60269", source_doc=_BUSSMANN_10164,
        ratings=(
            _fr("2NHG000B", 2, 3.5, 6, 3.9), _fr("4NHG000B", 4, 6, 12, 1.8),
            _fr("6NHG000B", 6, 14, 21, 2), _fr("10NHG000B", 10, 58, 290, 1.5),
            _fr("16NHG000B", 16, 234, 1200, 2.3),
            _fr("20NHG000B", 20, 490, 2500, 2.2),
            _fr("25NHG000B", 25, 920, 4600, 3.1),
            _fr("32NHG000B", 32, 1800, 9000, 3.4),
            _fr("35NHG000B", 35, 2400, 11800, 3.7),
            _fr("40NHG000B", 40, 3300, 16500, 4),
            _fr("50NHG000B", 50, 5900, 29500, 4.9),
            _fr("63NHG000B", 63, 6300, 24900, 4.6),
            _fr("80NHG000B", 80, 9800, 38900, 6.3),
            _fr("100NHG000B", 100, 18100, 72300, 7.4),
        ),
        notes="i2t_total = I1 a 120 kA / 500 V a.c. (ensaio IEC 60269).",
    ),
    FuseModel(
        model_id="BUSSMANN-NH00-GG-500V",
        manufacturer="Eaton",
        full_name="Bussmann NH tamanho 00 gG/gL 500 V a.c.",
        fuse_class="gG", rated_voltage_kV=0.5, breaking_capacity_kA=120.0,
        standard="IEC 60269", source_doc=_BUSSMANN_10164,
        ratings=(
            _fr("50NHG00B", 50, 5800, 21500, 5), _fr("63NHG00B", 63, 5800, 25000, 5),
            _fr("80NHG00B", 80, 11000, 35000, 7),
            _fr("100NHG00B", 100, 19000, 60000, 7.5),
            _fr("125NHG00B", 125, 25000, 125000, 10),
            _fr("160NHG00B", 160, 64000, 310000, 10),
        ),
    ),
    FuseModel(
        model_id="BUSSMANN-NH0-GG-500V",
        manufacturer="Eaton",
        full_name="Bussmann NH tamanho 0 gG/gL 500 V a.c.",
        fuse_class="gG", rated_voltage_kV=0.5, breaking_capacity_kA=120.0,
        standard="IEC 60269", source_doc=_BUSSMANN_10164,
        ratings=(
            _fr("6NHG0B", 6, 14, 21, 2), _fr("10NHG0B", 10, 58, 290, 2),
            _fr("16NHG0B", 16, 240, 1200, 3), _fr("20NHG0B", 20, 490, 2500, 3.5),
            _fr("25NHG0B", 25, 1200, 5600, 3.2), _fr("32NHG0B", 32, 1800, 9000, 4.8),
            _fr("35NHG0B", 35, 2400, 11800, 4.7), _fr("40NHG0B", 40, 3300, 16500, 5),
            _fr("50NHG0B", 50, 5600, 27800, 6.3), _fr("63NHG0B", 63, 6600, 26100, 5.6),
            _fr("80NHG0B", 80, 9800, 38900, 7.1),
            _fr("100NHG0B", 100, 20600, 82300, 7.5),
            _fr("125NHG0B", 125, 25000, 125000, 11.8),
            _fr("160NHG0B", 160, 62000, 310000, 12.3),
        ),
    ),
    FuseModel(
        model_id="BUSSMANN-NH1-GG-500V",
        manufacturer="Eaton",
        full_name="Bussmann NH tamanho 1 gG/gL 500 V a.c.",
        fuse_class="gG", rated_voltage_kV=0.5, breaking_capacity_kA=120.0,
        standard="IEC 60269", source_doc=_BUSSMANN_10164,
        ratings=(
            _fr("50NHG1B", 50, 6350, 18000, 6.4),
            _fr("63NHG1B", 63, 6800, 23000, 5.6),
            _fr("80NHG1B", 80, 10500, 31200, 7.7),
            _fr("100NHG1B", 100, 22000, 68200, 8.2),
            _fr("125NHG1B", 125, 29000, 82000, 13),
            _fr("160NHG1B", 160, 62000, 310000, 12.3),
            _fr("200NHG1B", 200, 97000, 368600, 15),
            _fr("224NHG1B", 224, 124000, 471200, 18),
            _fr("250NHG1B", 250, 151300, 574900, 19),
            _fr("315NHG1B", 315, 320000, 750000, 22),
            _fr("355NHG1B", 355, 320000, 750000, 32),
        ),
        notes=(
            "i2t_total = I1 a 120 kA / 500 V a.c. (ensaio IEC 60269). "
            "315/355 A: rated_voltage de catálogo 440 V a.c. (não 500 V); "
            "I²t pré-arco e total idênticos entre 315 e 355 A — impresso "
            "assim na fonte (mesmo elemento fusível), não corrigido."
        ),
    ),
    FuseModel(
        model_id="BUSSMANN-NH02-GG-500V",
        manufacturer="Eaton",
        full_name="Bussmann NH tamanho 02 gG/gL 500 V a.c.",
        fuse_class="gG", rated_voltage_kV=0.5, breaking_capacity_kA=120.0,
        standard="IEC 60269", source_doc=_BUSSMANN_10164,
        ratings=(
            _fr("35NHG02B", 35, 2400, 11800, 4.7),
            _fr("40NHG02B", 40, 3300, 16500, 5),
            _fr("50NHG02B", 50, 5600, 27800, 6.4),
            _fr("63NHG02B", 63, 6600, 26100, 5.5),
            _fr("80NHG02B", 80, 9800, 38900, 7.3),
            _fr("100NHG02B", 100, 20600, 82300, 7.5),
            _fr("125NHG02B", 125, 25000, 100000, 12),
            _fr("160NHG02B", 160, 62000, 248000, 12),
            _fr("200NHG02B", 200, 96900, 367900, 15),
            _fr("224NHG02B", 224, 124000, 471200, 18),
            _fr("250NHG02B", 250, 151300, 574900, 19),
        ),
        notes=(
            "Tamanho '02' — corpo intermediário entre 0 e 2 (norma DIN/"
            "IEC), distinto do tamanho '2'. i2t_total = I1 a 120 kA / "
            "500 V a.c."
        ),
    ),
    FuseModel(
        model_id="BUSSMANN-NH2-GG-500V",
        manufacturer="Eaton",
        full_name="Bussmann NH tamanho 2 gG/gL 500 V a.c.",
        fuse_class="gG", rated_voltage_kV=0.5, breaking_capacity_kA=120.0,
        standard="IEC 60269", source_doc=_BUSSMANN_10164,
        ratings=(
            _fr("250NHG2B", 250, 170000, 437000, 23),
            _fr("300NHG2B", 300, 320000, 840000, 20),
            _fr("315NHG2B", 315, 361700, 1446500, 21),
            _fr("355NHG2B", 355, 446500, 1785800, 27),
            _fr("400NHG2B", 400, 642900, 2571500, 30),
            _fr("425NHG2B", 425, 720000, 1862000, 31),
            _fr("450NHG2B", 450, 870000, 2275000, 31),
            _fr("500NHG2B", 500, 1200000, 2720000, 37),
        ),
        notes=(
            "i2t_total = I1 a 120 kA / 500 V a.c. 500 A: rated_voltage de "
            "catálogo 440 V a.c. (não 500 V)."
        ),
    ),
    FuseModel(
        model_id="BUSSMANN-NH03-GG-500V",
        manufacturer="Eaton",
        full_name="Bussmann NH tamanho 03 gG/gL 500 V a.c.",
        fuse_class="gG", rated_voltage_kV=0.5, breaking_capacity_kA=120.0,
        standard="IEC 60269", source_doc=_BUSSMANN_10164,
        ratings=(
            _fr("250NHG03B", 250, 160800, 642900, 20),
            _fr("315NHG03B", 315, 361700, 1446500, 21),
            _fr("355NHG03B", 355, 446500, 1785800, 27),
            _fr("400NHG03B", 400, 642900, 2571500, 30),
        ),
        notes=(
            "Tamanho '03' — corpo intermediário entre 0 e 3, distinto do "
            "tamanho '3'. i2t_total = I1 a 120 kA / 500 V a.c."
        ),
    ),
    FuseModel(
        model_id="BUSSMANN-NH3-GG-500V",
        manufacturer="Eaton",
        full_name="Bussmann NH tamanho 3 gG/gL 500 V a.c.",
        fuse_class="gG", rated_voltage_kV=0.5, breaking_capacity_kA=120.0,
        standard="IEC 60269", source_doc=_BUSSMANN_10164,
        ratings=(
            _fr("315NHG3B", 315, 375000, 970000, 22),
            _fr("355NHG3B", 355, 400000, 1110000, 25),
            _fr("400NHG3B", 400, 642900, 2571500, 30),
            _fr("425NHG3B", 425, 570000, 1934000, 30),
            _fr("450NHG3B", 450, 670000, 2260000, 33),
            _fr("500NHG3B", 500, 886000, 3898400, 37),
            _fr("630NHG3B", 630, 1590000, 6996000, 47),
            _fr("800NHG3B", 800, 2420000, 5420000, 59),
        ),
        notes=(
            "i2t_total = I1 a 120 kA / 500 V a.c. 800 A: rated_voltage de "
            "catálogo 440 V a.c. (não 500 V)."
        ),
    ),
    FuseModel(
        model_id="BUSSMANN-NH4-GG-500V",
        manufacturer="Eaton",
        full_name="Bussmann NH tamanho 4 gG/gL 500 V a.c.",
        fuse_class="gG", rated_voltage_kV=0.5, breaking_capacity_kA=120.0,
        standard="IEC 60269", source_doc=_BUSSMANN_10164,
        ratings=(
            _fr("500NHG4G", 500, 800000, 3850000, 37),
            _fr("630NHG4G", 630, 880000, 4100000, 47),
            _fr("800NHG4G", 800, 1500000, 6480000, 68),
            _fr("1000NHG4G", 1000, 4800000, 13000000, 80),
            _fr("1250NHG4G", 1250, 7000000, 18000000, 108),
        ),
        notes=(
            "Part numbers com sufixo 'G' (não 'B' como os demais tamanhos "
            "NH) — impresso assim na fonte, único conjunto sem variante de "
            "lug isolado listada. i2t_total = I1 a 120 kA / 500 V a.c."
        ),
    ),
    FuseModel(
        model_id="BUSSMANN-NH-AM-500-690V",
        manufacturer="Eaton",
        full_name="Bussmann NH aM 500/690 V a.c. (tamanhos 000-3)",
        fuse_class="aM", rated_voltage_kV=0.5, breaking_capacity_kA=120.0,
        standard="IEC 60269-2 / DIN 43620", source_doc=_BUSSMANN_10165,
        ratings=(
            _fr("6NHM000B", 6, 48, 650, 0.3), _fr("10NHM000B", 10, 200, 1800, 0.5),
            _fr("16NHM000B", 16, 500, 4400, 0.8),
            _fr("20NHM000B", 20, 1450, 7250, 0.9),
            _fr("25NHM000B", 25, 3500, 13500, 1.1),
            _fr("32NHM000B", 32, 2200, 7500, 2.1),
            _fr("35NHM000B", 35, 3000, 12000, 2.1),
            _fr("40NHM000B", 40, 4700, 14500, 2.3),
            _fr("50NHM000B", 50, 11000, 27000, 2.7),
            _fr("63NHM00B", 63, 16000, 52000, 3.1),
            _fr("80NHM00B", 80, 24000, 69500, 4.3),
            _fr("100NHM00B", 100, 35000, 110000, 4.5),
            _fr("50NHM1B", 50, 10000, 39500, 3), _fr("63NHM1B", 63, 12500, 49500, 4.4),
            _fr("80NHM1B", 80, 19500, 77500, 5.6),
            _fr("100NHM1B", 100, 33000, 105000, 6.7),
            _fr("125NHM1B", 125, 49500, 170000, 8.8),
            _fr("160NHM1B", 160, 110000, 315000, 10.6),
            _fr("125NHM2B", 125, 56500, 215000, 9.7),
            _fr("160NHM2B", 160, 120000, 510000, 11),
            _fr("200NHM2B", 200, 175000, 730000, 14),
            _fr("224NHM2B", 224, 255000, 1050000, 15),
            _fr("250NHM2B", 250, 300000, 1280000, 17),
            _fr("315NHM2B", 315, 510000, 1150000, 23),
            _fr("355NHM2B", 355, 570000, 1300000, 28),
            _fr("315NHM3B", 315, 480000, 1600000, 20),
            _fr("355NHM3B", 355, 500000, 1300000, 27),
            _fr("400NHM3B", 400, 680000, 2000000, 28),
            _fr("500NHM3B", 500, 1050000, 2800000, 36),
        ),
        notes=(
            "Part numbers '(A)NHM(tam)B' são a versão 500 V a.c.; a versão "
            "690 V a.c. usa o sufixo '-690' (ex. 315NHM2B-690) com os mesmos "
            "I²t e perdas. i2t_total cotado a 690 V a.c. Anomalia da fonte: "
            "tam. 000 25 A (3500 A²s) > 32 A (2200 A²s) no pré-arco — "
            "impresso assim no datasheet, não corrigido. 315/355 A tam. 2 "
            "marcados com asterisco no catálogo (legenda ausente na extração)."
        ),
    ),
    FuseModel(
        model_id="BUSSMANN-12KV-DIN-MV",
        manufacturer="Eaton",
        full_name="Bussmann 12 kV DIN medium voltage fuse links (transformador)",
        fuse_class="MV-backup", rated_voltage_kV=12.0, breaking_capacity_kA=50.0,
        standard="IEC 60282-1 (2005) / DIN 43625 / VDE 0670",
        source_doc=_BUSSMANN_720104, voltage_class=VoltageClass.MV,
        ratings=(
            _fr("12TDLEJ6.3", 6.3, 98, 1000, 10, I3=23, kA=63, mohm=222),
            _fr("12TDLEJ10", 10, 280, 2300, 16, I3=35, kA=63, mohm=131),
            _fr("12TDLEJ16", 16, 260, 3900, 16, I3=53, kA=63, mohm=54.6),
            _fr("12TDLEJ20", 20, 520, 5400, 18, I3=73, kA=63, mohm=39.1),
            _fr("12TDLEJ25", 25, 810, 8400, 24, I3=87, kA=63, mohm=31.2),
            _fr("12TDLEJ31.5", 31.5, 1400, 15000, 28, I3=111, kA=63, mohm=23.4),
            _fr("12TDLEJ40", 40, 2400, 25000, 36, I3=143, kA=63, mohm=17.2),
            _fr("12TDLEJ50", 50, 2800, 31000, 47, I3=168, kA=63, mohm=13.5),
            _fr("12TDLEJ63", 63, 4300, 47000, 60, I3=235, kA=63, mohm=10.6),
            _fr("12THLEJ80", 80, 7900, 91000, 72, I3=272, kA=63, mohm=7.81),
            _fr("12THLEJ100", 100, 20000, 140000, 85, I3=388, kA=63, mohm=5.74),
            _fr("12AILSJ100", 100, 14000, 200000, 70, I3=176, kA=31.5, mohm=53),
            _fr("12TKLEJ125", 125, 40000, 350000, 93, I3=687, kA=63, mohm=3.99),
            _fr("12TXLEJ160", 160, 110000, 500000, 217, I3=560, kA=63, mohm=4.3),
            _fr("12TXLEJ200", 200, 150000, 650000, 333, I3=610, kA=63, mohm=3.8),
            _fr("12THMEJ100", 100, 20000, 140000, 85, I3=272, kA=63, mohm=5.74),
            _fr("12TFMSJ160", 160, 50000, 350000, 139, I3=485, kA=50, mohm=3.65),
        ),
        notes=(
            "Classe back-up. breaking_capacity_kA de família = 50 kA "
            "('Technical data' do datasheet); o I1 por peça prevalece via "
            "FuseRating.breaking_capacity_kA (AILSJ100 31.5 kA, TFMSJ160 "
            "50 kA; demais 63 kA). AILSJ não "
            "adequado a uso externo; TXLEJ não conforme VDE 0670-402."
        ),
    ),
    FuseModel(
        model_id="SIBA-HHM-12KV",
        manufacturer="SIBA",
        full_name="SIBA HHBM 12 kV back-up, aplicação motor (A=587 mm)",
        fuse_class="HH-motor", rated_voltage_kV=12.0, breaking_capacity_kA=50.0,
        standard="IEC 60282-1 / BS 2692-1", source_doc=_SIBA_HHM,
        voltage_class=VoltageClass.MV,
        ratings=(
            _fr("3027456.50", 50, 3400, 23000, 55, I3=140, mohm=17),
            _fr("3027456.63", 63, 5400, 35000, 74, I3=165, mohm=14),
            _fr("3027456.80", 80, 6200, 36500, 100, I3=200, mohm=11),
            _fr("3027456.100", 100, 14000, 79000, 107, I3=285, mohm=7.5),
            _fr("3027456.125", 125, 25000, 141000, 128, I3=375, mohm=5.6),
            _fr("3027456.160", 160, 64000, 362000, 136, I3=480, mohm=3.5),
            _fr("3027456.200", 200, 121000, 685000, 157, I3=600, mohm=2.6),
            _fr("3027556.224", 224, 127000, 717000, 188, I3=675, mohm=2.5),
            _fr("3027556.250", 250, 189000, 1100000, 210, I3=750, mohm=2.0),
            _fr("3027556.315", 315, 257000, 1450000, 270, I3=960, mohm=1.8),
            _fr("3027556.355", 355, 325000, 1840000, 305, I3=1050, mohm=1.6),
            _fr("3027556.400", 400, 486000, 2740000, 325, I3=1200, mohm=1.3),
        ),
        notes="i2t_total a 0.87·Un. 3027456 barril simples, 3027556 duplo (gatilho 50N).",
    ),
    FuseModel(
        model_id="SIBA-HHM-3.6KV",
        manufacturer="SIBA",
        full_name="SIBA HHBM-BM 3.6 kV back-up, aplicação motor (A=254 mm)",
        fuse_class="HH-motor", rated_voltage_kV=3.6, breaking_capacity_kA=50.0,
        standard="DIN 43625 / IEC 60282-1 / IEC 60644 / BS 2692-1",
        source_doc=_SIBA_HHM, voltage_class=VoltageClass.MV,
        ratings=(
            _fr("3026956.50", 50, 3400, 16000, 23, I3=140, mohm=7),
            _fr("3026956.63", 63, 5400, 25000, 31, I3=165, mohm=5.7),
            _fr("3026956.80", 80, 6200, 29000, 36, I3=200, mohm=4),
            _fr("3026956.100", 100, 14000, 65000, 39, I3=285, mohm=3),
            _fr("3026956.125", 125, 25000, 115000, 44, I3=375, mohm=2.5),
            _fr("3026956.160", 160, 64000, 295000, 46, I3=490, mohm=1.5),
            _fr("3026956.200", 200, 121000, 559000, 54, I3=690, mohm=1.1),
            _fr("3026956.224", 224, 144000, 665000, 57, I3=790, mohm=1),
            _fr("3026956.250", 250, 307000, 1414000, 61, I3=1050, mohm=0.7),
            _fr("3026956.315", 315, 627000, 2880000, 70, I3=1500, mohm=0.6),
            _fr("3027056.355", 355, 760000, 3700000, 89, I3=2130, mohm=1),
            _fr("3027056.400", 400, 900000, 4400000, 108, I3=2400, mohm=0.9),
            _fr("3027056.450", 450, 1230000, 6000000, 120, I3=2700, mohm=0.8),
            _fr("3027056.500", 500, 1230000, 6000000, 141, I3=2700, mohm=0.7),
        ),
        notes="i2t_total a 0.87·Un. Gatilho 50N com limitador de temperatura.",
    ),
    FuseModel(
        model_id="ABB-CMF-3.6KV",
        manufacturer="ABB",
        full_name="ABB CMF 3.6 kV motor protection (K-factor IEC 644)",
        fuse_class="HH-motor", rated_voltage_kV=3.6, breaking_capacity_kA=50.0,
        standard="IEC 60282-1 / IEC 644", source_doc=_ABB_CEF,
        voltage_class=VoltageClass.MV,
        ratings=(
            _fr("1YMB531028M0001", 100, 14000, 170000, 49, I3=275, mohm=3.25),
            _fr("1YMB531028M0002", 160, 38000, 500000, 75, I3=400, mohm=1.94),
            _fr("1YMB531028M0003", 200, 76000, 710000, 75, I3=500, mohm=1.42),
            _fr("1YMB531028M0004", 250, 140000, 1150000, 90, I3=760, mohm=1.03),
            _fr("1YMB531028M0005", 315, 210000, 1800000, 122, I3=900, mohm=0.85),
        ),
        notes=(
            "K-factor 0.75/0.7/0.7/0.6/0.6. part_number = 'New No.' da tabela de "
            "pedido (e=292 mm); 'Old No.' NHPL052760R1..NHPL052764R1."
        ),
    ),
    FuseModel(
        model_id="ABB-CMF-7.2KV",
        manufacturer="ABB",
        full_name="ABB CMF 7.2 kV motor protection (K-factor IEC 644)",
        fuse_class="HH-motor", rated_voltage_kV=7.2, breaking_capacity_kA=50.0,
        standard="IEC 60282-1 / IEC 644", source_doc=_ABB_CEF,
        voltage_class=VoltageClass.MV,
        ratings=(
            _fr("1YMB531029M0001", 63, 4800, 65000, 45, I3=175, mohm=8.63),
            _fr("1YMB531029M0002", 100, 14000, 180000, 67, I3=275, mohm=4.93),
            _fr("1YMB531029M0003", 160, 38000, 540000, 119, I3=400, mohm=2.96),
            _fr("1YMB531029M0004", 200, 76000, 750000, 118, I3=500, mohm=2.15),
            _fr("1YMB531029M0005", 250, 140000, 1200000, 142, I3=800, mohm=1.56),
            _fr("1YMB531029M0006", 315, 210000, 2200000, 193, I3=950, mohm=1.30),
        ),
        notes=(
            "part_number = 'New No.' da tabela de pedido (e=442 mm); 'Old No.' "
            "NHPL052770R1..NHPL052775R1."
        ),
    ),
    FuseModel(
        model_id="ABB-CMF-12KV",
        manufacturer="ABB",
        full_name="ABB CMF 12 kV motor protection (K-factor IEC 644)",
        fuse_class="HH-motor", rated_voltage_kV=12.0, breaking_capacity_kA=50.0,
        standard="IEC 60282-1 / IEC 644", source_doc=_ABB_CEF,
        voltage_class=VoltageClass.MV,
        ratings=(
            _fr("1YMB531030M0001", 63, 4800, 110000, 77, I3=190, mohm=13.3),
            _fr("1YMB531030M0002", 100, 14000, 200000, 103, I3=275, mohm=6.72),
            _fr("1YMB531030M0003", 160, 38000, 700000, 155, I3=480, mohm=4.04),
            _fr("1YMB531030M0004", 200, 93000, 910000, 173, I3=560, mohm=2.89),
        ),
        notes=(
            "part_number = 'New No.' da tabela de pedido (e=442 mm); 'Old No.' "
            "NHPL052776R1..NHPL052779R1."
        ),
    ),
    FuseModel(
        model_id="ABB-CEF-12KV",
        manufacturer="ABB",
        full_name="ABB CEF 12 kV current limiting back-up (transformador / uso geral)",
        fuse_class="MV-backup", rated_voltage_kV=12.0, breaking_capacity_kA=50.0,
        standard="IEC 60282-1", source_doc=_ABB_CEF, voltage_class=VoltageClass.MV,
        ratings=(
            _fr("1YMB531002M0001", 6, W=41, I3=35, mohm=735), _fr("1YMB531002M0002", 10, W=33, I3=55, mohm=180),
            _fr("1YMB531002M0003", 16, W=32, I3=55, mohm=105), _fr("1YMB531002M0004", 25, W=47, I3=77, mohm=52.6),
            _fr("1YMB531002M0005", 40, W=52, I3=105, mohm=23.0), _fr("1YMB531002M0006", 50, W=70, I3=190, mohm=17.9),
            _fr("1YMB531002M0007", 63, W=78, I3=190, mohm=13.4), _fr("1YMB531002M0008", 80, W=82, I3=250, mohm=9.2),
            _fr("1YMB531002M0009", 100, W=103, I3=275, mohm=6.6), _fr("1YMB531002M0010", 125, W=125, I3=375, mohm=5.3),
            _fr("1YMB531002M0011", 160, W=170, I3=480, mohm=3.9), _fr("1YMB531002M0012", 200, W=174, I3=650, mohm=2.7),
        ),
        notes=(
            "Tipo back-up (zona entre corrente mínima de fusão e I3 em que o "
            "elo pode não interromper). Catálogo CEF não publica I²t (campos "
            "= 0). part_number = 'New No.' 1YMB531002M0001..M0012: 6-100 A "
            "com e=292 mm (variante e=442 mm: 1YMB531035M0001..M0009); "
            "125-200 A apenas e=442 mm. Outras tensões (3.6/7.2/17.5/24/27/"
            "36 kV) na fonte."
        ),
    ),
    FuseModel(
        model_id="WEG-AR-NH-CONTATO-FACA-100KA",
        manufacturer="WEG",
        full_name="WEG FNH aR ultrarrápido NH contato faca 690 V",
        fuse_class="aR", rated_voltage_kV=0.69, breaking_capacity_kA=100.0,
        standard="IEC 60269-4 / UL 248-13", source_doc=_WEG_FUS,
        ratings=(
            _fr("FNH00-20K-A", 20, 16, 240, 3.2), _fr("FNH00-25K-A", 25, 19, 255, 3.5),
            _fr("FNH00-35K-A", 35, 23, 430, 5), _fr("FNH00-40K-A", 40, 56, 580, 7),
            _fr("FNH00-50K-A", 50, 130, 1430, 9), _fr("FNH00-63K-A", 63, 180, 2170, 10.5),
            _fr("FNH00-80K-A", 80, 270, 2710, 13.5), _fr("FNH00-100K-A", 100, 400, 4530, 14),
            _fr("FNH00-125K-A", 125, 810, 6350, 16.5),
            _fr("FNH00-160K-A", 160, 2100, 15270, 22.5),
            _fr("FNH00-200K-A", 200, 2900, 25870, 26.5),
            _fr("FNH00-250K-A", 250, 6200, 43980, 30.5),
            _fr("FNH1-63K-A", 63, 63, 770, 15), _fr("FNH1-80K-A", 80, 175, 1610, 19),
            _fr("FNH1-100K-A", 100, 320, 3050, 21), _fr("FNH1-125K-A", 125, 695, 6360, 25),
            _fr("FNH1-160K-A", 160, 1460, 13090, 29.5),
            _fr("FNH1-200K-A", 200, 2420, 16380, 34.5),
            _fr("FNH1-250K-A", 250, 4920, 29810, 40.5),
            _fr("FNH1-315K-A", 315, 7310, 39590, 48),
            _fr("FNH1-350K-A", 350, 11430, 64870, 52),
            _fr("FNH1-400K-A", 400, 16950, 98860, 59),
            _fr("FNH2-250K-A", 250, 3390, 24370, 45.5),
            _fr("FNH2-315K-A", 315, 4760, 32780, 57.5),
            _fr("FNH2-350K-A", 350, 7990, 60150, 66.5),
            _fr("FNH2-400K-A", 400, 14850, 92060, 77),
            _fr("FNH2-450K-A", 450, 18420, 132990, 91),
            _fr("FNH2-500K-A", 500, 23040, 146250, 103),
            _fr("FNH2-630K-A", 630, 49130, 298820, 127),
            _fr("FNH2-710K-A", 710, 57910, 378450, 137.5),
            _fr("FNH3-400K-A", 400, 6520, 66830, 70),
            _fr("FNH3-450K-A", 450, 15090, 105220, 74.5),
            _fr("FNH3-500K-A", 500, 18770, 107200, 79.5),
            _fr("FNH3-630K-A", 630, 32500, 222540, 94),
            _fr("FNH3-710K-A", 710, 56620, 308900, 105),
            _fr("FNH3-800K-A", 800, 87390, 420500, 117),
            _fr("FNH3-900K-A", 900, 129380, 636150, 130),
            _fr("FNH3-1000K-A", 1000, 197890, 893350, 150),
        ),
        notes=(
            "i2t_total = I²t total de arco a 690 V a.c.; perdas a 0.8·In. "
            "Sem proteção contra sobrecarga (classe aR). Mesma corrente em "
            "tamanhos diferentes tem I²t distinto (ex. 250 A: FNH1 4920 vs "
            "FNH2 3390 A²s pré-arco)."
        ),
    ),
    FuseModel(
        model_id="WEG-AR-NH-FLUSH-END-200KA",
        manufacturer="WEG",
        full_name="WEG FNH aR ultrarrápido NH flush end 690 V",
        fuse_class="aR", rated_voltage_kV=0.69, breaking_capacity_kA=200.0,
        standard="IEC 60269-4 / UL 248-13", source_doc=_WEG_FUS,
        ratings=(
            _fr("FNH3FEM-450Y-A", 450, 32000, 94500, 115),
            _fr("FNH3FEM-500Y-A", 500, 40000, 129000, 115),
            _fr("FNH3FEM-550Y-A", 550, 66500, 177000, 120),
            _fr("FNH3FEM-630Y-A", 630, 84000, 227000, 120),
            _fr("FNH3FEM-700Y-A", 700, 100000, 309000, 125),
            _fr("FNH3FEM-800Y-A", 800, 140500, 470000, 135),
            _fr("FNH3FEM-900Y-A", 900, 180000, 650000, 135),
            _fr("FNH3FEM-1000Y-A", 1000, 239500, 890000, 145),
            _fr("FNH3FEM-1100Y-A", 1100, 292000, 1340000, 150),
            _fr("FNH3FEM-1250Y-A", 1250, 385000, 1970000, 155),
            _fr("FNH3FEM-1400Y-A", 1400, 500000, 2680000, 215),
            _fr("FNH23FEA-1000Y-A", 1000, 151000, 446000, 230),
            _fr("FNH23FEA-1250Y-A", 1250, 213000, 822000, 250),
            _fr("FNH23FEA-1400Y-A", 1400, 279000, 1050000, 270),
            _fr("FNH23FEA-1600Y-A", 1600, 360000, 1760000, 295),
            _fr("FNH23FEA-1800Y-A", 1800, 529000, 2430000, 320),
            _fr("FNH23FEA-2000Y-A", 2000, 710000, 3170000, 365),
        ),
        notes=(
            "i2t_total = I²t de arco a 660 V a.c.; perdas a 1×In. FNH23FEA = 2 fusíveis "
            "em paralelo. A tabela técnica do catálogo imprime o 1100 A como "
            "'NH3FEM-1100Y-A' (sem o 'F'); as tabelas de seleção do mesmo documento "
            "grafam 'FNH3FEM-1100Y-A' com o mesmo código de material 12661664 — "
            "adotada a grafia consistente."
        ),
    ),
]


def list_trip_units(
    *,
    vendor: Optional[str] = None,
    category: Optional[str] = None,
    ground_fault_only: bool = False,
) -> list[TripUnitModel]:
    """Lista unidades de disparo filtradas."""
    items = list(_TRIP_UNITS)
    if vendor is not None:
        items = [t for t in items if t.manufacturer.lower() == vendor.lower()]
    if category is not None:
        items = [t for t in items if t.category.upper() == category.upper()]
    if ground_fault_only:
        items = [t for t in items if t.has_ground_fault]
    return items


def get_trip_unit(model_id: str) -> Optional[TripUnitModel]:
    for t in _TRIP_UNITS:
        if t.model_id.lower() == model_id.lower():
            return t
    return None


def list_fuses(
    *,
    vendor: Optional[str] = None,
    fuse_class: Optional[str] = None,
    voltage_class: Optional[VoltageClass] = None,
    rated_voltage_kV: Optional[float] = None,
) -> list[FuseModel]:
    """Lista famílias de fusíveis filtradas."""
    items = list(_FUSES)
    if vendor is not None:
        items = [f for f in items if f.manufacturer.lower() == vendor.lower()]
    if fuse_class is not None:
        items = [f for f in items if f.fuse_class.lower() == fuse_class.lower()]
    if voltage_class is not None:
        items = [f for f in items if f.voltage_class == voltage_class]
    if rated_voltage_kV is not None:
        items = [
            f for f in items
            if abs(f.rated_voltage_kV - rated_voltage_kV) < 1e-6
        ]
    return items


def get_fuse(model_id: str) -> Optional[FuseModel]:
    for f in _FUSES:
        if f.model_id.lower() == model_id.lower():
            return f
    return None


def stats() -> dict[str, int]:
    """Estatísticas da biblioteca."""
    return {
        "relays": len(_RELAYS),
        "motors": len(_MOTORS),
        "transformers": len(_TRANSFORMERS),
        "breakers": len(_BREAKERS),
        "trip_units": len(_TRIP_UNITS),
        "fuses": len(_FUSES),
        "total": (
            len(_RELAYS) + len(_MOTORS) + len(_TRANSFORMERS)
            + len(_BREAKERS) + len(_TRIP_UNITS) + len(_FUSES)
        ),
    }


def list_vendors() -> list[str]:
    """Lista todos os fabricantes presentes."""
    vendors: set[str] = set()
    for r in _RELAYS:
        vendors.add(r.manufacturer)
    for m in _MOTORS:
        vendors.add(m.manufacturer)
    for t in _TRANSFORMERS:
        vendors.add(t.manufacturer)
    for b in _BREAKERS:
        vendors.add(b.manufacturer)
    for tu in _TRIP_UNITS:
        vendors.add(tu.manufacturer)
    for f in _FUSES:
        vendors.add(f.manufacturer)
    return sorted(vendors)
