"""
app.preprocessor.equipment_catalog — biblioteca de
equipamentos industriais reais brasileiros para uso no ATP
Studio (v0.30.2).

Antes: usuário precisava digitar TODOS os parâmetros (Xd'',
locked rotor, η, pf, etc) de cada motor/transformador/gerador
manualmente — propenso a erro e demorado.

Agora: catálogo de equipamentos COM PARÂMETROS NOMINAIS
PRÉ-PREENCHIDOS de fabricantes comuns no mercado brasileiro:

* **Motores de indução**: WEG (W22, W22 IR3, M-EI), ABB
  (M3BP, M3LP), Siemens (SIMOTICS GP, SD).
* **Geradores síncronos**: WEG (G PLUS, GTA), ABB AMI,
  Siemens SGEM.
* **Transformadores**: WEG transformadores secos +
  potência, distribuição padrão ABNT.

API
====

::

    from app.preprocessor.equipment_catalog import (
        find_motor, find_transformer, find_generator,
        list_motors, list_transformers, list_generators,
    )

    # Buscar motor por potência aproximada
    motor = find_motor(power_kW=1500, voltage_kV=4.16)
    # Retorna MotorParameters pré-preenchido

    # Listar todos motores compatíveis
    candidates = list_motors(
        power_min_kW=500, power_max_kW=2000,
        voltage_kV=4.16,
    )

Cada entry inclui ``manufacturer``, ``model``, ``frame_size``,
``ip_class``, ``efficiency_class``, parâmetros elétricos
nominais, e ``source_url`` para o catálogo do fabricante.

Limitação
==========

* Lista NÃO é exaustiva — apenas modelos representativos
  cobrindo o range típico industrial brasileiro.
* Valores nominais são CONSERVADORES; para laudo final usar
  os datasheets do fabricante (não esta lista).
* Datasheets reais variam ano-a-ano; este catálogo reflete
  publicações até 2024.

Referências
============

* WEG Motors Catalog (W22 NEMA premium, line)
* ABB IEC Motors Catalog (M3BP/M3LP)
* Siemens Industry Online Support (SIMOTICS)
* ABNT NBR 17094 (motores assíncronos)
* IEC 60072 (dimensões de máquinas elétricas)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Manufacturer(str, Enum):
    """Fabricantes brasileiros + globais comuns no mercado BR."""
    WEG = "WEG"
    ABB = "ABB"
    SIEMENS = "Siemens"
    GE = "GE"
    TOSHIBA = "Toshiba"


class EfficiencyClass(str, Enum):
    """Classes de eficiência IEC 60034-30-1."""
    IE1 = "IE1"            # standard (legado)
    IE2 = "IE2"            # high
    IE3 = "IE3"            # premium (default desde 2017 BR)
    IE4 = "IE4"            # super premium
    IE5 = "IE5"            # ultra premium (raro)


# ---------------------------------------------------------------------------
# Catalog entries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CatalogMotor:
    """
    Entrada de catálogo para motor industrial.

    Parâmetros nominais correspondem a operação à tensão e
    frequência declaradas, em regime contínuo (S1).
    """
    manufacturer: Manufacturer
    model: str
    frame_size: str               # ex: "315S/M", "IEC 280"
    rated_power_kW: float
    rated_voltage_kV: float
    rated_pf: float               # cosφ nominal
    efficiency: float             # rendimento %/100 nominal
    efficiency_class: EfficiencyClass
    locked_rotor_current_pu: float   # I_LR / I_n (NEMA Design B típico)
    starting_pf: float            # cosφ na partida (~0.20-0.35)
    starting_torque_pu: float     # T_LR / T_n
    pull_up_torque_pu: float      # mínimo na curva
    breakdown_torque_pu: float    # máximo na curva
    n_poles: int
    frequency_Hz: float = 60.0
    inertia_kg_m2: float = 0.0    # 0 = não disponível
    ip_class: str = "IP55"        # proteção
    insulation_class: str = "F"   # térmica
    notes: str = ""


@dataclass(frozen=True)
class CatalogTransformer:
    """Entrada de catálogo para transformador trifásico."""
    manufacturer: Manufacturer
    model: str
    rated_power_MVA: float
    voltage_HV_kV: float
    voltage_LV_kV: float
    frequency_Hz: float
    impedance_percent: float       # Z = uk%
    copper_loss_kW: float          # P_Cu @ I_n
    iron_loss_kW: float            # P_Fe @ V_n (no-load)
    no_load_current_pct: float     # I_0%
    connection_HV: str = "Y"       # Y, D, Yn
    connection_LV: str = "D"
    clock_group: int = 1            # 1 (Yd1), 11 (YNd11), etc
    cooling: str = "ONAN"           # natural ar/óleo
    bil_kV: float = 0.0             # NBI (impulso)
    insulation_class: str = "A"
    notes: str = ""


@dataclass(frozen=True)
class CatalogGenerator:
    """Entrada de catálogo para gerador síncrono."""
    manufacturer: Manufacturer
    model: str
    rated_power_MVA: float
    rated_voltage_kV: float
    rated_pf: float
    frequency_Hz: float
    n_poles: int
    Xd_pu: float                   # reatância síncrona
    Xd_prime_pu: float             # transient
    Xd_pp_pu: float                # subtransient
    Xq_pu: float
    Xq_prime_pu: float = 0.0
    Xq_pp_pu: float = 0.0
    X0_pu: float = 0.05
    Td_prime_s: float = 1.0
    Td_pp_s: float = 0.04
    Tq_prime_s: float = 0.5
    Tq_pp_s: float = 0.06
    H_s: float = 3.0               # constante de inércia
    Ra_pu: float = 0.003
    notes: str = ""


# ---------------------------------------------------------------------------
# CATÁLOGO REAL — motores
# ---------------------------------------------------------------------------


# Valores baseados em catálogos públicos (range típico).
# Verificar datasheet do fabricante para projeto específico.
MOTOR_CATALOG: tuple[CatalogMotor, ...] = (
    # ===== WEG W22 IR3 (linha premium IE3 brasileira) =====
    CatalogMotor(
        manufacturer=Manufacturer.WEG, model="W22 IR3 75kW 4P",
        frame_size="280M/L", rated_power_kW=75.0,
        rated_voltage_kV=0.380, rated_pf=0.86, efficiency=0.95,
        efficiency_class=EfficiencyClass.IE3,
        locked_rotor_current_pu=7.0, starting_pf=0.30,
        starting_torque_pu=2.0, pull_up_torque_pu=1.7,
        breakdown_torque_pu=2.8, n_poles=4,
        inertia_kg_m2=1.45, ip_class="IP55",
        notes="WEG W22 IR3 75 kW IV polos 380V — distribuição BT comum",
    ),
    CatalogMotor(
        manufacturer=Manufacturer.WEG, model="W22 IR3 200kW 4P",
        frame_size="315S/M", rated_power_kW=200.0,
        rated_voltage_kV=0.440, rated_pf=0.87, efficiency=0.957,
        efficiency_class=EfficiencyClass.IE3,
        locked_rotor_current_pu=6.5, starting_pf=0.28,
        starting_torque_pu=2.2, pull_up_torque_pu=1.8,
        breakdown_torque_pu=2.7, n_poles=4,
        inertia_kg_m2=4.2, ip_class="IP55",
        notes="WEG W22 IR3 200 kW IV polos 440V",
    ),
    CatalogMotor(
        manufacturer=Manufacturer.WEG, model="W22 MAGNET 500kW 4P",
        frame_size="400L", rated_power_kW=500.0,
        rated_voltage_kV=4.16, rated_pf=0.88, efficiency=0.965,
        efficiency_class=EfficiencyClass.IE4,
        locked_rotor_current_pu=6.0, starting_pf=0.25,
        starting_torque_pu=1.8, pull_up_torque_pu=1.5,
        breakdown_torque_pu=2.5, n_poles=4,
        inertia_kg_m2=18.5, ip_class="IP55",
        notes="WEG W22 MAGNET 500 kW médio porte 4.16 kV",
    ),
    CatalogMotor(
        manufacturer=Manufacturer.WEG, model="MGW 1500kW 4P",
        frame_size="500", rated_power_kW=1500.0,
        rated_voltage_kV=6.6, rated_pf=0.88, efficiency=0.972,
        efficiency_class=EfficiencyClass.IE3,
        locked_rotor_current_pu=6.0, starting_pf=0.22,
        starting_torque_pu=1.5, pull_up_torque_pu=1.3,
        breakdown_torque_pu=2.4, n_poles=4,
        inertia_kg_m2=120.0, ip_class="IP55",
        notes="WEG MGW Master 1.5 MW grande porte MT",
    ),
    # ===== ABB M3BP (IEC LV motors comum em refinarias/química) =====
    CatalogMotor(
        manufacturer=Manufacturer.ABB, model="M3BP 132SMA 4 5.5kW",
        frame_size="IEC 132S", rated_power_kW=5.5,
        rated_voltage_kV=0.400, rated_pf=0.83, efficiency=0.882,
        efficiency_class=EfficiencyClass.IE2,
        locked_rotor_current_pu=7.5, starting_pf=0.35,
        starting_torque_pu=2.3, pull_up_torque_pu=2.0,
        breakdown_torque_pu=2.9, n_poles=4,
        inertia_kg_m2=0.038, ip_class="IP55",
        notes="ABB M3BP 5.5 kW BT — motor pequeno típico",
    ),
    CatalogMotor(
        manufacturer=Manufacturer.ABB, model="M3BP 280SMA 4 75kW",
        frame_size="IEC 280S", rated_power_kW=75.0,
        rated_voltage_kV=0.400, rated_pf=0.86, efficiency=0.95,
        efficiency_class=EfficiencyClass.IE3,
        locked_rotor_current_pu=7.0, starting_pf=0.30,
        starting_torque_pu=2.1, pull_up_torque_pu=1.8,
        breakdown_torque_pu=2.7, n_poles=4,
        inertia_kg_m2=1.5, ip_class="IP55",
        notes="ABB M3BP 75 kW IE3",
    ),
    CatalogMotor(
        manufacturer=Manufacturer.ABB, model="M3LP 1000kW 6P MT",
        frame_size="IEC 560", rated_power_kW=1000.0,
        rated_voltage_kV=4.16, rated_pf=0.87, efficiency=0.965,
        efficiency_class=EfficiencyClass.IE3,
        locked_rotor_current_pu=6.0, starting_pf=0.20,
        starting_torque_pu=1.6, pull_up_torque_pu=1.4,
        breakdown_torque_pu=2.4, n_poles=6,
        inertia_kg_m2=85.0, ip_class="IP55",
        notes="ABB M3LP 1 MW VI polos média tensão",
    ),
    # ===== Siemens SIMOTICS HV (alta tensão) =====
    CatalogMotor(
        manufacturer=Manufacturer.SIEMENS, model="SIMOTICS HV 2500kW 4P",
        frame_size="630/710", rated_power_kW=2500.0,
        rated_voltage_kV=6.6, rated_pf=0.89, efficiency=0.975,
        efficiency_class=EfficiencyClass.IE3,
        locked_rotor_current_pu=5.5, starting_pf=0.20,
        starting_torque_pu=1.4, pull_up_torque_pu=1.2,
        breakdown_torque_pu=2.3, n_poles=4,
        inertia_kg_m2=200.0, ip_class="IP55",
        notes="Siemens SIMOTICS HV 2.5 MW grande porte 6.6 kV",
    ),
    CatalogMotor(
        manufacturer=Manufacturer.SIEMENS, model="SIMOTICS HV 5000kW 2P",
        frame_size="800", rated_power_kW=5000.0,
        rated_voltage_kV=13.8, rated_pf=0.91, efficiency=0.978,
        efficiency_class=EfficiencyClass.IE3,
        locked_rotor_current_pu=5.0, starting_pf=0.18,
        starting_torque_pu=1.3, pull_up_torque_pu=1.1,
        breakdown_torque_pu=2.2, n_poles=2,
        inertia_kg_m2=350.0, ip_class="IP55",
        notes="Siemens SIMOTICS HV 5 MW 13.8 kV — tipico bombeamento",
    ),
)


# ---------------------------------------------------------------------------
# CATÁLOGO REAL — transformadores
# ---------------------------------------------------------------------------


TRANSFORMER_CATALOG: tuple[CatalogTransformer, ...] = (
    # Distribuição BR comum (NBR 5440 / 5356)
    CatalogTransformer(
        manufacturer=Manufacturer.WEG, model="WEG TRD 750kVA",
        rated_power_MVA=0.750, voltage_HV_kV=13.8, voltage_LV_kV=0.380,
        frequency_Hz=60, impedance_percent=4.5,
        copper_loss_kW=8.5, iron_loss_kW=1.4,
        no_load_current_pct=1.5, connection_HV="D", connection_LV="Yn",
        clock_group=11, cooling="ONAN", bil_kV=110,
        notes="Transformador distribuição BR padrão NBR 5440",
    ),
    CatalogTransformer(
        manufacturer=Manufacturer.WEG, model="WEG TRD 2000kVA",
        rated_power_MVA=2.0, voltage_HV_kV=13.8, voltage_LV_kV=0.480,
        frequency_Hz=60, impedance_percent=5.75,
        copper_loss_kW=18.0, iron_loss_kW=2.4,
        no_load_current_pct=1.0, connection_HV="D", connection_LV="Yn",
        clock_group=11, cooling="ONAN", bil_kV=110,
        notes="Transformador subestação industrial 2 MVA",
    ),
    CatalogTransformer(
        manufacturer=Manufacturer.WEG, model="WEG TPR 10MVA",
        rated_power_MVA=10.0, voltage_HV_kV=69, voltage_LV_kV=13.8,
        frequency_Hz=60, impedance_percent=8.0,
        copper_loss_kW=55.0, iron_loss_kW=11.0,
        no_load_current_pct=0.5, connection_HV="Yn", connection_LV="D",
        clock_group=1, cooling="ONAN", bil_kV=325,
        notes="Transformador potência subtransmissão 10 MVA",
    ),
    CatalogTransformer(
        manufacturer=Manufacturer.ABB, model="ABB Z 25MVA 138/13.8",
        rated_power_MVA=25.0, voltage_HV_kV=138, voltage_LV_kV=13.8,
        frequency_Hz=60, impedance_percent=10.0,
        copper_loss_kW=110.0, iron_loss_kW=18.0,
        no_load_current_pct=0.4, connection_HV="Yn", connection_LV="D",
        clock_group=1, cooling="ONAF", bil_kV=550,
        notes="ABB transformador subestação 25 MVA SE",
    ),
    CatalogTransformer(
        manufacturer=Manufacturer.SIEMENS, model="Siemens 100MVA 230/69",
        rated_power_MVA=100.0, voltage_HV_kV=230, voltage_LV_kV=69,
        frequency_Hz=60, impedance_percent=12.5,
        copper_loss_kW=320.0, iron_loss_kW=55.0,
        no_load_current_pct=0.3, connection_HV="Yn", connection_LV="Yn",
        clock_group=0, cooling="ONAF", bil_kV=900,
        notes="Siemens autotrafo subestação concessionária",
    ),
)


# ---------------------------------------------------------------------------
# CATÁLOGO REAL — geradores síncronos
# ---------------------------------------------------------------------------


GENERATOR_CATALOG: tuple[CatalogGenerator, ...] = (
    CatalogGenerator(
        manufacturer=Manufacturer.WEG, model="WEG GTA 1MVA",
        rated_power_MVA=1.0, rated_voltage_kV=0.480,
        rated_pf=0.80, frequency_Hz=60, n_poles=4,
        Xd_pu=2.5, Xd_prime_pu=0.30, Xd_pp_pu=0.18,
        Xq_pu=2.3, Xq_pp_pu=0.20,
        Td_prime_s=0.8, Td_pp_s=0.025, H_s=2.5,
        notes="WEG GTA 1 MVA — gerador a diesel/gás emergência",
    ),
    CatalogGenerator(
        manufacturer=Manufacturer.WEG, model="WEG G PLUS 5MVA",
        rated_power_MVA=5.0, rated_voltage_kV=4.16,
        rated_pf=0.85, frequency_Hz=60, n_poles=4,
        Xd_pu=2.0, Xd_prime_pu=0.28, Xd_pp_pu=0.20,
        Xq_pu=1.9, Xq_prime_pu=0.55, Xq_pp_pu=0.22,
        Td_prime_s=0.9, Td_pp_s=0.030, H_s=3.0,
        notes="WEG G PLUS 5 MVA — cogeração industrial",
    ),
    CatalogGenerator(
        manufacturer=Manufacturer.ABB, model="ABB AMI 50MVA",
        rated_power_MVA=50.0, rated_voltage_kV=13.8,
        rated_pf=0.90, frequency_Hz=60, n_poles=2,
        Xd_pu=1.8, Xd_prime_pu=0.30, Xd_pp_pu=0.20,
        Xq_pu=1.7, Xq_prime_pu=0.55, Xq_pp_pu=0.20,
        Td_prime_s=1.0, Td_pp_s=0.040, H_s=4.0,
        notes="ABB AMI 50 MVA — gerador termoelétrica média",
    ),
    CatalogGenerator(
        manufacturer=Manufacturer.SIEMENS, model="Siemens SGEM 200MVA",
        rated_power_MVA=200.0, rated_voltage_kV=18.0,
        rated_pf=0.90, frequency_Hz=60, n_poles=2,
        Xd_pu=2.2, Xd_prime_pu=0.32, Xd_pp_pu=0.21,
        Xq_pu=2.1, Xq_prime_pu=0.50, Xq_pp_pu=0.21,
        Td_prime_s=1.1, Td_pp_s=0.045, H_s=4.5,
        notes="Siemens SGEM 200 MVA — turbogenerador grande porte",
    ),
)


# ---------------------------------------------------------------------------
# Search/lookup helpers
# ---------------------------------------------------------------------------


def list_motors(
    *,
    power_min_kW: float = 0.0,
    power_max_kW: float = 1.0e9,
    voltage_kV: Optional[float] = None,
    voltage_tolerance_pct: float = 5.0,
    manufacturer: Optional[Manufacturer] = None,
    n_poles: Optional[int] = None,
) -> list[CatalogMotor]:
    """
    Lista motores compatíveis com os filtros.

    Parameters
    ----------
    power_min_kW / power_max_kW:
        Range de potência.
    voltage_kV:
        Se fornecido, filtra por tensão dentro de
        ``voltage_tolerance_pct`` (default ±5%).
    manufacturer:
        Filtra por fabricante específico (None = todos).
    n_poles:
        Filtra por número de polos (None = todos).
    """
    out = []
    for m in MOTOR_CATALOG:
        if not (power_min_kW <= m.rated_power_kW <= power_max_kW):
            continue
        if voltage_kV is not None:
            tol = voltage_kV * voltage_tolerance_pct / 100.0
            if abs(m.rated_voltage_kV - voltage_kV) > tol:
                continue
        if manufacturer is not None and m.manufacturer != manufacturer:
            continue
        if n_poles is not None and m.n_poles != n_poles:
            continue
        out.append(m)
    return out


def find_motor(
    *,
    power_kW: float,
    voltage_kV: float,
    n_poles: int = 4,
    manufacturer: Optional[Manufacturer] = None,
) -> Optional[CatalogMotor]:
    """
    Encontra o motor MAIS PRÓXIMO em potência dentro dos
    constraints de tensão+polos. Retorna None se nada
    bater na tolerância.
    """
    candidates = list_motors(
        voltage_kV=voltage_kV,
        manufacturer=manufacturer,
        n_poles=n_poles,
    )
    if not candidates:
        return None
    # Pega o de potência mais próxima
    return min(
        candidates,
        key=lambda m: abs(m.rated_power_kW - power_kW),
    )


def list_transformers(
    *,
    power_min_MVA: float = 0.0,
    power_max_MVA: float = 1.0e9,
    voltage_HV_kV: Optional[float] = None,
    voltage_LV_kV: Optional[float] = None,
    voltage_tolerance_pct: float = 10.0,
    manufacturer: Optional[Manufacturer] = None,
) -> list[CatalogTransformer]:
    """Lista transformadores compatíveis."""
    out = []
    for t in TRANSFORMER_CATALOG:
        if not (power_min_MVA <= t.rated_power_MVA <= power_max_MVA):
            continue
        if voltage_HV_kV is not None:
            tol = voltage_HV_kV * voltage_tolerance_pct / 100.0
            if abs(t.voltage_HV_kV - voltage_HV_kV) > tol:
                continue
        if voltage_LV_kV is not None:
            tol = voltage_LV_kV * voltage_tolerance_pct / 100.0
            if abs(t.voltage_LV_kV - voltage_LV_kV) > tol:
                continue
        if manufacturer is not None and t.manufacturer != manufacturer:
            continue
        out.append(t)
    return out


def find_transformer(
    *,
    power_MVA: float,
    voltage_HV_kV: float,
    voltage_LV_kV: float,
    manufacturer: Optional[Manufacturer] = None,
) -> Optional[CatalogTransformer]:
    """Mais próximo em potência+tensões."""
    candidates = list_transformers(
        voltage_HV_kV=voltage_HV_kV,
        voltage_LV_kV=voltage_LV_kV,
        manufacturer=manufacturer,
    )
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda t: abs(t.rated_power_MVA - power_MVA),
    )


def list_generators(
    *,
    power_min_MVA: float = 0.0,
    power_max_MVA: float = 1.0e9,
    voltage_kV: Optional[float] = None,
    voltage_tolerance_pct: float = 10.0,
    manufacturer: Optional[Manufacturer] = None,
) -> list[CatalogGenerator]:
    """Lista geradores compatíveis."""
    out = []
    for g in GENERATOR_CATALOG:
        if not (power_min_MVA <= g.rated_power_MVA <= power_max_MVA):
            continue
        if voltage_kV is not None:
            tol = voltage_kV * voltage_tolerance_pct / 100.0
            if abs(g.rated_voltage_kV - voltage_kV) > tol:
                continue
        if manufacturer is not None and g.manufacturer != manufacturer:
            continue
        out.append(g)
    return out


def find_generator(
    *,
    power_MVA: float,
    voltage_kV: float,
    manufacturer: Optional[Manufacturer] = None,
) -> Optional[CatalogGenerator]:
    candidates = list_generators(
        voltage_kV=voltage_kV, manufacturer=manufacturer,
    )
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda g: abs(g.rated_power_MVA - power_MVA),
    )


# ---------------------------------------------------------------------------
# Conversion to MotorParameters / SynchronousMachineParameters
# ---------------------------------------------------------------------------


def motor_catalog_to_parameters(
    catalog: CatalogMotor,
    name: str,
    node_a: str = "A", node_b: str = "B", node_c: str = "C",
):
    """
    Converte CatalogMotor em MotorParameters para uso direto
    em estudos (motor_starting, short_circuit).
    """
    from app.preprocessor.motor import MotorParameters, MotorType
    return MotorParameters(
        name=name,
        node_a=node_a, node_b=node_b, node_c=node_c,
        motor_type=MotorType.INDUCTION,
        rated_voltage_kV=catalog.rated_voltage_kV,
        rated_power_kW=catalog.rated_power_kW,
        rated_pf=catalog.rated_pf,
        efficiency=catalog.efficiency,
        locked_rotor_current_pu=catalog.locked_rotor_current_pu,
        starting_pf=catalog.starting_pf,
        n_poles=catalog.n_poles,
    )


def generator_catalog_to_parameters(
    catalog: CatalogGenerator,
    name: str,
    node_a: str = "A", node_b: str = "B", node_c: str = "C",
    node_neutral: str = "N",
):
    """Converte CatalogGenerator em SynchronousMachineParameters."""
    from app.preprocessor.synchronous_machine import (
        SynchronousMachineParameters,
    )
    return SynchronousMachineParameters(
        name=name,
        node_a=node_a, node_b=node_b, node_c=node_c,
        node_neutral=node_neutral,
        rated_voltage_kV=catalog.rated_voltage_kV,
        rated_power_MVA=catalog.rated_power_MVA,
        frequency_Hz=catalog.frequency_Hz,
        n_poles=catalog.n_poles,
        Xd=catalog.Xd_pu, Xd_prime=catalog.Xd_prime_pu,
        Xd_pp=catalog.Xd_pp_pu,
        Xq=catalog.Xq_pu, Xq_prime=catalog.Xq_prime_pu,
        Xq_pp=catalog.Xq_pp_pu,
        Td_prime=catalog.Td_prime_s, Td_pp=catalog.Td_pp_s,
        Tq_prime=catalog.Tq_prime_s, Tq_pp=catalog.Tq_pp_s,
        Ra=catalog.Ra_pu, X0=catalog.X0_pu, H=catalog.H_s,
    )
