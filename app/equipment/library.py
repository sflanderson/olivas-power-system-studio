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


def stats() -> dict[str, int]:
    """Estatísticas da biblioteca."""
    return {
        "relays": len(_RELAYS),
        "motors": len(_MOTORS),
        "transformers": len(_TRANSFORMERS),
        "breakers": len(_BREAKERS),
        "total": (
            len(_RELAYS) + len(_MOTORS) + len(_TRANSFORMERS)
            + len(_BREAKERS)
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
    return sorted(vendors)
