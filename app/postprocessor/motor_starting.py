"""
app.postprocessor.motor_starting — análise de partida de
motores grandes (voltage dip + tempo de aceleração).

Motivação
==========

Motores de indução grandes (≥ 100 HP) absorvem **5-7× I_n**
durante a partida (locked-rotor current). Em sistemas com
impedância de fonte significativa, isso pode causar:

* **Voltage dip** ≥ 15% no bus do motor → afeta outras cargas
  conectadas (lâmpadas piscam, drives reset, contatores caem).
* **Tempo de partida** longo se torque insuficiente → estresse
  térmico no enrolamento.

NBR 17227 §4.2.2 e IEEE 399 (Brown Book) §10 estipulam
critérios para análise de partida.

Critérios de aceitação
=======================

* **V > 0.85 pu** durante a partida (IEEE 399 §10).
* **V > 0.80 pu** absoluto mínimo (NEMA MG 1).
* **t_start < 0.7 × t_locked_rotor_thermal** (proteção
  térmica do motor).
* **N_starts/hora** dentro do limite NEMA MG 1 §20.43.

Modelagem (IEEE 399 §10)
=========================

Voltage dip durante partida:

::

    ΔV / V_pre = Z_motor / (Z_th_system + Z_motor)

    V_during_start = V_pre × (Z_motor) / (Z_th + Z_motor)

Onde:
* ``Z_th`` = impedância de Thevenin do sistema visto do bus
  do motor (vinda do estudo de SC: Z_th = V_n / Ik'').
* ``Z_motor`` = impedância do motor em partida ≈ V² / S_LR
  onde S_LR = √3 × V × I_LR.

Tempo de aceleração:

::

    dω/dt = (T_motor(ω) - T_load(ω)) / (2 H_motor)

    t_start = ∫ 2H / (T_m - T_load) dω

Para MVP, usamos aproximação simples assumindo torque
constante médio:

::

    t_start ≈ 2 H × ωs / (T_m_avg - T_load_avg)

Limitações conhecidas
======================

* MVP: assume T_motor constante (refinamento: curva torque-
  speed).
* Não modela contribuição harmônica de drives.
* Não trata starts simultâneos (assume start único).

Referências
============

* IEEE Std 399-1997 (Brown Book) §10 — Motor Starting Studies.
* IEEE Std 1100-2005 (Emerald Book) — Powering and Grounding.
* NEMA MG 1-2018 §20.43 — Motor starting limits.
* NBR 17227:2025 §4.2.2 — Motor contribution to SC.
* IEEE C37.96-2012 — Motor protection.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Critérios de aceitação
# ---------------------------------------------------------------------------


# Limite IEEE 399 — voltage dip durante partida.
DEFAULT_VOLTAGE_DIP_LIMIT_PU = 0.85

# Limite NEMA MG 1 — mínimo absoluto.
ABSOLUTE_MIN_VOLTAGE_LIMIT_PU = 0.80

# Limite típico de tempo de partida (% do tempo térmico).
DEFAULT_START_TIME_FRACTION_LIMIT = 0.70


class StartingResult(str, Enum):
    """Categoria do resultado de aceitação."""
    ACCEPTABLE = "acceptable"           # V > 0.85 e t_start OK
    MARGINAL = "marginal"               # 0.80 < V < 0.85 (IEEE 399)
    UNACCEPTABLE = "unacceptable"       # V < 0.80


# ---------------------------------------------------------------------------
# MotorStartingCase
# ---------------------------------------------------------------------------


class LoadType(str, Enum):
    """
    Tipo de carga mecânica acoplada ao motor.

    Define a curva torque × velocidade da carga, conforme
    NEMA MG-1 §20:

    * **CONSTANT**: T_load = T_n constante (guincho, esteira
      carregada, britador). Mais exigente para acelerar.
    * **LINEAR**: T_load ∝ ω (ventiladores axiais leves,
      moinhos com fricção viscosa).
    * **QUADRATIC**: T_load ∝ ω² (ventiladores centrífugos,
      bombas centrífugas, sopradores). Mais comum em
      indústria — torque inicial pequeno.
    * **CUBIC**: T_load ∝ ω³ (compressores em alguns regimes).

    Para MVP/PRO, a forma da curva afeta o torque MÉDIO
    durante a aceleração:

    ::

        T_load_avg(ω: 0 → ω_n) = ∫T_load dω / ω_n

    * CONSTANT: T_load_avg = T_n
    * LINEAR: T_load_avg = T_n / 2
    * QUADRATIC: T_load_avg = T_n / 3
    * CUBIC: T_load_avg = T_n / 4
    """
    CONSTANT = "constant"
    LINEAR = "linear"
    QUADRATIC = "quadratic"
    CUBIC = "cubic"


def average_load_torque_factor(load_type: LoadType) -> float:
    """
    Fator médio do torque resistente durante aceleração
    0 → ω_n, em pu de T_n_load.

    ::

        ∫T(ω)dω/ω_n = T_n / (k+1) onde T(ω) ∝ ω^k

    * k=0 (CONSTANT): 1.0
    * k=1 (LINEAR):  0.5
    * k=2 (QUADRATIC): 1/3 ≈ 0.333
    * k=3 (CUBIC):   1/4 = 0.25
    """
    factors = {
        LoadType.CONSTANT: 1.0,
        LoadType.LINEAR: 0.5,
        LoadType.QUADRATIC: 1.0 / 3.0,
        LoadType.CUBIC: 0.25,
    }
    return factors[load_type]


@dataclass(frozen=True)
class MotorStartingCase:
    """
    Cenário de partida de motor.

    v0.28.1 mudanças:

    * ``bus_thevenin_impedance_ohm`` (float, módulo) DEPRECATED;
      use ``bus_thevenin_impedance_complex`` (R + jX).
    * Novo campo ``load_type: LoadType`` para curva torque×ω
      (CONSTANT/LINEAR/QUADRATIC/CUBIC).
    * Backward compat: se ``bus_thevenin_impedance_complex`` é
      None, usa ``bus_thevenin_impedance_ohm`` com heurística
      90%-indutivo (compatibilidade com código existente).

    Attributes
    ----------
    motor_name:
        Nome do motor.
    motor_rated_power_kW:
        Potência nominal de eixo (kW).
    motor_rated_voltage_kV:
        Tensão nominal V_LL.
    motor_rated_pf:
        Fator de potência nominal.
    motor_efficiency:
        Rendimento nominal η.
    locked_rotor_current_pu:
        I_LR / I_n (típico 5-7 para NEMA Design B).
    starting_pf:
        Fator de potência durante partida (típico 0.20-0.30).
    starting_torque_pu:
        Torque de partida em pu de T_n.
    load_torque_pu:
        Torque resistente da carga em pu de T_n na velocidade
        nominal. Default 1.0.
    load_type:
        v0.28.1: tipo da curva torque-velocidade da carga.
        Default CONSTANT (conservador).
    inertia_motor_kg_m2:
        Momento de inércia do rotor + carga (kg·m²).
    bus_pre_fault_voltage_pu:
        Tensão pré-partida no bus (vem do PF).
    bus_thevenin_impedance_ohm:
        |Z_th| do sistema (módulo) — DEPRECATED, mantido para
        compatibilidade. Se ``bus_thevenin_impedance_complex``
        fornecido, este é ignorado.
    bus_thevenin_impedance_complex:
        v0.28.1: Z_th = R + jX completo (do estudo SC). Quando
        fornecido, substitui a heurística 90%-indutivo do MVP.
    bus_rated_voltage_kV:
        V_LL nominal do bus (para conversão pu → SI).
    n_poles:
        Número de polos do motor.
    frequency_Hz:
        Frequência do sistema.
    """

    motor_name: str
    motor_rated_power_kW: float
    motor_rated_voltage_kV: float
    motor_rated_pf: float
    motor_efficiency: float
    locked_rotor_current_pu: float
    starting_pf: float
    starting_torque_pu: float
    load_torque_pu: float
    inertia_motor_kg_m2: float
    bus_pre_fault_voltage_pu: float
    bus_thevenin_impedance_ohm: float
    bus_rated_voltage_kV: float
    n_poles: int = 4
    frequency_Hz: float = 60.0
    # v0.28.1
    load_type: "LoadType" = None  # type: ignore[assignment]
    bus_thevenin_impedance_complex: complex | None = None

    def __post_init__(self):
        # Default para LoadType.CONSTANT (conservador)
        if self.load_type is None:
            object.__setattr__(self, "load_type", LoadType.CONSTANT)


# ---------------------------------------------------------------------------
# MotorStartingReport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MotorStartingReport:
    """
    Resultado da análise de partida.

    Attributes
    ----------
    motor_name:
        Identificador.
    voltage_dip_pu:
        Tensão durante a partida (V_pre × fator de divisão).
    voltage_dip_pct:
        Queda em % do V_pre.
    starting_current_kA:
        Corrente RMS na partida (locked-rotor).
    starting_apparent_power_MVA:
        S na partida (= √3 V_during × I_LR).
    starting_time_s:
        Tempo estimado para atingir 95% da velocidade nominal.
    synchronous_speed_rpm:
        n_s = 120 f / poles.
    motor_impedance_ohm:
        |Z_M| equivalente do motor em partida.
    acceptance:
        ACCEPTABLE / MARGINAL / UNACCEPTABLE.
    rationale:
        Explicação da decisão.
    references:
        Refs normativas.
    """

    motor_name: str
    voltage_dip_pu: float
    voltage_dip_pct: float
    starting_current_kA: float
    starting_apparent_power_MVA: float
    starting_time_s: float
    synchronous_speed_rpm: float
    motor_impedance_ohm: float
    acceptance: StartingResult
    rationale: tuple[str, ...]
    references: tuple[str, ...] = (
        "IEEE Std 399-1997 (Brown Book) §10 — Motor Starting",
        "NEMA MG 1-2018 §20.43 — Motor starting limits",
        "NBR 17227:2025 §4.2.2",
    )

    def summary(self) -> str:
        """Texto humano-readable."""
        lines = [
            f"=== Motor Starting Analysis — {self.motor_name} ===",
            f"  Synchronous speed: {self.synchronous_speed_rpm:.0f} rpm",
            f"  Motor impedance Z_M: {self.motor_impedance_ohm:.4f} Ω",
            "",
            f"  Voltage dip:  {self.voltage_dip_pu:.4f} pu",
            f"               ({self.voltage_dip_pct:.2f}% drop)",
            f"  Start current: {self.starting_current_kA:.3f} kA",
            f"  Start S:       {self.starting_apparent_power_MVA:.2f} MVA",
            f"  Time to 95%:   {self.starting_time_s:.2f} s",
            "",
            f"  Acceptance: {self.acceptance.value.upper()}",
            "",
            "  Rationale:",
        ]
        for r in self.rationale:
            lines.append(f"    • {r}")
        lines.append("")
        lines.append("  References:")
        for ref in self.references:
            lines.append(f"    [{ref}]")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cálculos
# ---------------------------------------------------------------------------


def motor_impedance_at_start_ohm(case: MotorStartingCase) -> complex:
    """
    Impedância equivalente do motor durante a partida (locked
    rotor).

    ::

        Z_M = (1 / I_LR_pu) × V² / S
        S = P / (η × pf)

    com R/X derivado do starting_pf.
    """
    S_motor_VA = (
        case.motor_rated_power_kW * 1000.0
        / (case.motor_efficiency * case.motor_rated_pf)
    )
    V_motor = case.motor_rated_voltage_kV * 1000.0
    Z_base = V_motor ** 2 / S_motor_VA
    z_mag = Z_base / case.locked_rotor_current_pu

    if case.starting_pf <= 0 or case.starting_pf >= 1:
        return complex(0, z_mag)

    phi = math.acos(case.starting_pf)
    R_X = 1.0 / math.tan(phi)
    X = z_mag / math.sqrt(1.0 + R_X ** 2)
    R = R_X * X
    return complex(R, X)


def calculate_voltage_dip_pu(
    case: MotorStartingCase,
) -> tuple[float, complex, complex]:
    """
    Calcula voltage dip durante a partida via divisor de
    impedância:

    ::

        V_during / V_pre = Z_M / (Z_th + Z_M)

    v0.28.1: prioriza ``bus_thevenin_impedance_complex`` (vindo
    do SC IEC 60909) quando fornecido. Fallback para a
    heurística 90%-indutivo do MVP apenas se apenas o módulo
    estiver disponível.

    Returns
    -------
    tuple[float, complex, complex]
        (V_during_pu, Z_motor_complex, Z_thevenin_complex).
    """
    Z_M = motor_impedance_at_start_ohm(case)

    # v0.28.1 — usa Z_th complex se fornecido
    if case.bus_thevenin_impedance_complex is not None:
        Z_th = case.bus_thevenin_impedance_complex
        if abs(Z_th) <= 0:
            Z_th = complex(0, 1e-9)
    else:
        # Backward compat: heurística 90% indutivo
        Z_th_mag = case.bus_thevenin_impedance_ohm
        Z_th = (
            complex(0.1 * Z_th_mag, 0.9 * Z_th_mag)
            if Z_th_mag > 0 else complex(0, 1e-9)
        )

    # Divisor de impedância
    V_pre_complex = complex(case.bus_pre_fault_voltage_pu, 0)
    V_during = V_pre_complex * Z_M / (Z_th + Z_M)
    V_during_pu_mag = abs(V_during)
    return V_during_pu_mag, Z_M, Z_th


def estimate_starting_time_s(case: MotorStartingCase) -> float:
    """
    Tempo estimado para o motor atingir 95% da velocidade
    nominal:

    ::

        t = J × Δω / (T_m_avg - T_load_avg)

    Onde:

    * J = inércia (motor + carga)
    * ωs = velocidade síncrona em rad/s
    * Δω = 0.95 × ωs
    * T_m_avg ≈ starting_torque_pu × T_n
    * T_load_avg = factor(load_type) × load_torque_pu × T_n
        - CONSTANT: factor = 1.0 (T_n constante)
        - LINEAR:   factor = 0.5
        - QUADRATIC: factor = 1/3 (ventilador/bomba)
        - CUBIC:    factor = 1/4

    v0.28.1: usa ``case.load_type`` para selecionar a curva
    de carga; default CONSTANT preserva comportamento MVP.
    """
    n_s_rpm = synchronous_speed_rpm(case.frequency_Hz, case.n_poles)
    omega_s = n_s_rpm * 2.0 * math.pi / 60.0  # rad/s

    # Torque nominal em N·m
    P_W = case.motor_rated_power_kW * 1000.0
    T_n_Nm = P_W / omega_s

    T_motor_avg = case.starting_torque_pu * T_n_Nm
    # v0.28.1: T_load_avg via curva torque-speed escolhida
    factor = average_load_torque_factor(case.load_type)
    T_load_avg = factor * case.load_torque_pu * T_n_Nm

    if T_motor_avg <= T_load_avg:
        return float("inf")    # motor não consegue acelerar

    delta_omega = 0.95 * omega_s
    t = case.inertia_motor_kg_m2 * delta_omega / (
        T_motor_avg - T_load_avg
    )
    return t


def synchronous_speed_rpm(frequency_Hz: float, n_poles: int) -> float:
    """Velocidade síncrona n_s = 120 f / poles."""
    return 120.0 * frequency_Hz / n_poles


def classify_acceptance(V_during_pu: float) -> StartingResult:
    """
    Classifica resultado conforme IEEE 399 §10:

    * V > 0.85 → ACCEPTABLE
    * 0.80 < V ≤ 0.85 → MARGINAL
    * V ≤ 0.80 → UNACCEPTABLE
    """
    if V_during_pu > DEFAULT_VOLTAGE_DIP_LIMIT_PU:
        return StartingResult.ACCEPTABLE
    if V_during_pu > ABSOLUTE_MIN_VOLTAGE_LIMIT_PU:
        return StartingResult.MARGINAL
    return StartingResult.UNACCEPTABLE


# ---------------------------------------------------------------------------
# Análise principal
# ---------------------------------------------------------------------------


def analyze_motor_starting(
    case: MotorStartingCase,
) -> MotorStartingReport:
    """
    Análise completa de partida de motor: voltage dip, tempo
    de aceleração, aceitação IEEE 399.
    """
    V_during_pu, Z_M, Z_th = calculate_voltage_dip_pu(case)
    voltage_dip_pct = (
        (case.bus_pre_fault_voltage_pu - V_during_pu)
        / case.bus_pre_fault_voltage_pu * 100.0
    )

    # Corrente de partida (locked rotor) em A
    V_motor = case.motor_rated_voltage_kV * 1000.0
    S_motor_VA = (
        case.motor_rated_power_kW * 1000.0
        / (case.motor_efficiency * case.motor_rated_pf)
    )
    I_n_A = S_motor_VA / (math.sqrt(3.0) * V_motor)
    I_LR_A = I_n_A * case.locked_rotor_current_pu

    # Considerando tensão reduzida durante partida:
    # Corrente de partida é proporcional à tensão (Z_M ≈ const)
    I_during_A = I_LR_A * V_during_pu / case.bus_pre_fault_voltage_pu

    # Potência aparente de partida
    S_during_VA = math.sqrt(3.0) * V_motor * V_during_pu * I_during_A
    S_during_MVA = S_during_VA / 1.0e6

    t_start = estimate_starting_time_s(case)
    n_s = synchronous_speed_rpm(case.frequency_Hz, case.n_poles)
    acceptance = classify_acceptance(V_during_pu)

    rationale = []
    if acceptance == StartingResult.ACCEPTABLE:
        rationale.append(
            f"V_during = {V_during_pu:.3f} pu > 0.85 (IEEE 399 limit)."
        )
    elif acceptance == StartingResult.MARGINAL:
        rationale.append(
            f"V_during = {V_during_pu:.3f} pu na zona MARGINAL "
            f"(0.80–0.85). Avaliar impacto em outras cargas."
        )
    else:
        rationale.append(
            f"V_during = {V_during_pu:.3f} pu < 0.80 (NEMA limit). "
            "Considerar partida assistida (soft-starter, "
            "auto-trafo, VFD)."
        )

    if t_start == float("inf"):
        rationale.append(
            "Torque do motor INSUFICIENTE para acelerar a "
            "carga (T_motor < T_load_avg). Motor não partirá."
        )
    elif t_start > 30.0:
        rationale.append(
            f"Tempo de partida {t_start:.1f}s > 30s pode "
            "violar limite térmico (verificar curva I²t do motor)."
        )

    rationale.append(
        f"Z_th_sys = {abs(Z_th):.4f} Ω, "
        f"Z_M = {abs(Z_M):.4f} Ω, "
        f"ratio Z_M/Z_th = {abs(Z_M)/abs(Z_th) if abs(Z_th) > 0 else float('inf'):.2f}"
    )

    return MotorStartingReport(
        motor_name=case.motor_name,
        voltage_dip_pu=V_during_pu,
        voltage_dip_pct=voltage_dip_pct,
        starting_current_kA=I_during_A / 1000.0,
        starting_apparent_power_MVA=S_during_MVA,
        starting_time_s=t_start,
        synchronous_speed_rpm=n_s,
        motor_impedance_ohm=abs(Z_M),
        acceptance=acceptance,
        rationale=tuple(rationale),
    )
