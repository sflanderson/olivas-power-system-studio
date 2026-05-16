"""
app.preprocessor.motor — modelagem de motores elétricos
(indução e síncrono) com contribuição para curto-circuito
conforme IEC 60909-0:2016 §6.5 e NBR 17227:2025 §4.2.2.

Motivação
=========

Motores são **fontes secundárias de SC** durante a fase
inicial da falta (energia armazenada no rotor). NBR 17227
§4.2.2 explicita:

    A contribuição de motores de indução é limitada em um
    período de três a oito ciclos, enquanto a contribuição
    de motores síncronos se estende por um período maior.

Para arc-flash (clearing typ. 50-200 ms = 3-12 ciclos a 60Hz),
a contribuição de motores **importa**:

* Aumenta Ik'' inicial em 10-50% em plantas com muitos motores.
* Eleva a categoria PPE (NBR 17227).
* Influencia coordenação de proteção (51/51N).

Modelagem (IEC 60909-0 §6.5)
============================

**Motor de indução** (IM):

::

    X''_M = (1 / I_LR_rel) · U_rM² / S_rM

Onde ``I_LR_rel = I_LR / I_rM`` é o **ratio de partida**
(locked rotor current, tipicamente 5-7 para motores standard).

Contribuição máxima (subtransitório):

::

    I''_M = I_rM · I_LR_rel    (= corrente de rotor bloqueado)

Decaimento exponencial com τ_M ≈ 10-50 ms (motor pequeno) ou
~100 ms (motor grande).

**Motor síncrono**:

* Equivalente elétrico = ``SynchronousMachine`` em modo motor
  (usar componente SM já existente com ``P0_MW < 0``).

MVP v0.27.7.9 cobre apenas motores de indução. Síncronos →
usar SM com sinal de potência invertido.

Limitações conhecidas
======================

* Motores < 50 HP **não** contribuem significativamente
  (IEC 60909-0 §6.5: motores com I_rM < 80 A são geralmente
  desprezados em estudos de SC para sistemas de média tensão).
* Decay exponencial não modelado em tempo: usamos contribuição
  no Ik'' (subtransitório, t=0).
* Para tempo de extinção > 100 ms, contribuição de IM é
  praticamente nula — caller deve usar fator de redução
  (``contribution_factor_at_time``).

Referências
============

* IEC 60909-0:2016 §6.5 — Asynchronous motors.
* NBR 17227:2025 §4.2.2 — Inclusão de motores em SC.
* IEEE 242-2001 (Buff Book) §15 — motor contribution.
* Anderson-Fouad, *Power System Control and Stability*, §5.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# MotorType
# ---------------------------------------------------------------------------


class MotorType(str, Enum):
    """Tipo de motor — afeta cálculo da contribuição."""
    INDUCTION = "induction"        # IM (mais comum em plantas)
    SYNCHRONOUS = "synchronous"    # MS (uso especializado)


# ---------------------------------------------------------------------------
# MotorParameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MotorParameters:
    """
    Parâmetros de motor para cálculo da contribuição de SC.

    Attributes
    ----------
    name:
        Identificador (≤ 6 chars).
    node_a, node_b, node_c:
        Terminais do motor (≤ 6 chars). Trifásico apenas no MVP.
    motor_type:
        Indução ou síncrono.
    rated_voltage_kV:
        Tensão nominal V_LL (kV).
    rated_power_kW:
        Potência nominal de eixo (kW). Para conversão a S:
        ``S_rM = P / (η · cos(φ))``.
    rated_pf:
        Fator de potência (cosφ) na placa. Default 0.85.
    efficiency:
        Rendimento (η) na placa. Default 0.95.
    locked_rotor_current_pu:
        Razão I_LR / I_rM (ratio de partida). Tipicamente 5-7
        para motores standard NEMA Design B; até 12 para
        motores Design D. Default 6.0.
    starting_pf:
        Fator de potência durante partida. Default 0.30.
    n_poles:
        Número de polos. Default 4 (1800 rpm @ 60Hz).
    Td_pp_ms:
        Constante de tempo subtransitória (decaimento). Default
        20 ms — típico motor médio (NBR 17227 cita 3-8 ciclos
        ≈ 50-133 ms para decay total).
    """

    name: str
    node_a: str
    node_b: str
    node_c: str
    motor_type: MotorType = MotorType.INDUCTION

    rated_voltage_kV: float = 0.480
    rated_power_kW: float = 100.0
    rated_pf: float = 0.85
    efficiency: float = 0.95

    locked_rotor_current_pu: float = 6.0
    starting_pf: float = 0.30
    n_poles: int = 4
    Td_pp_ms: float = 20.0


# ---------------------------------------------------------------------------
# Cálculos
# ---------------------------------------------------------------------------


def rated_apparent_power_kVA(p: MotorParameters) -> float:
    """``S_rM = P_eixo / (η · cosφ)`` em kVA."""
    if p.efficiency <= 0 or p.rated_pf <= 0:
        raise ValueError("efficiency e rated_pf devem > 0")
    return p.rated_power_kW / (p.efficiency * p.rated_pf)


def rated_current_A(p: MotorParameters) -> float:
    """``I_rM = S / (√3 · V_LL)`` em A."""
    S_kVA = rated_apparent_power_kVA(p)
    return S_kVA / (math.sqrt(3.0) * p.rated_voltage_kV)


def locked_rotor_current_A(p: MotorParameters) -> float:
    """``I_LR = I_rM · I_LR_rel`` (corrente de rotor bloqueado)."""
    return rated_current_A(p) * p.locked_rotor_current_pu


def base_impedance_ohm(p: MotorParameters) -> float:
    """Z_base = V² / S em ohms."""
    S_VA = rated_apparent_power_kVA(p) * 1000.0
    return (p.rated_voltage_kV * 1000.0) ** 2 / S_VA


def subtransient_reactance_pu(p: MotorParameters) -> float:
    """
    Reatância subtransitória X''_M em pu (base do motor).

    Para IM (IEC 60909-0 §6.5):

    ::

        X''_M = 1 / I_LR_rel  (em pu)

    Para motor síncrono: usa Xd'' do datasheet (típico 0.15-0.25).
    Aqui usamos a mesma fórmula simplificada — para precisão,
    use ``SynchronousMachineParameters`` no lugar.
    """
    if p.locked_rotor_current_pu <= 0:
        raise ValueError("locked_rotor_current_pu deve > 0")
    return 1.0 / p.locked_rotor_current_pu


def subtransient_impedance_ohm(p: MotorParameters) -> complex:
    """
    Z''_M complexa = R_M + j·X''_M em ohms.

    R_M derivado do starting_pf:
    ``R_M = X''_M · tan(arccos(starting_pf))`` na verdade é:
    ``R_M = X''_M / Q_factor`` onde Q = X/R = tan(φ).

    Para starting_pf = 0.30: Q ≈ 3.18.
    """
    X_pu = subtransient_reactance_pu(p)
    Z_base = base_impedance_ohm(p)
    X_ohm = X_pu * Z_base

    if p.starting_pf <= 0 or p.starting_pf >= 1:
        # fallback: X-only
        return complex(0.0, X_ohm)

    # Q = tan(arccos(pf))
    phi = math.acos(p.starting_pf)
    R_X_ratio = 1.0 / math.tan(phi)  # R/X = cot(phi)
    R_ohm = R_X_ratio * X_ohm
    return complex(R_ohm, X_ohm)


def initial_sc_contribution_kA(p: MotorParameters) -> float:
    """
    Contribuição inicial de SC do motor (kA RMS) — aproximação
    de I''_M baseada em locked rotor current.

    ::

        I''_M ≈ I_LR (kA)
    """
    return locked_rotor_current_A(p) / 1000.0


def contribution_factor_at_time(
    p: MotorParameters, time_ms: float,
) -> float:
    """
    Fator de redução da contribuição em ``time_ms`` segundos
    após a falta.

    Decaimento exponencial:

    ::

        f(t) = exp(-t / Td_pp_ms)

    Para IM com Td_pp = 20 ms:
    * t = 0: f = 1.0
    * t = 20 ms: f = 0.37 (1 ciclo a 60Hz)
    * t = 50 ms (3 ciclos): f = 0.082
    * t = 100 ms (6 ciclos): f = 0.007
    * t > 130 ms (8 ciclos): f ≈ 0 (NBR 17227 §4.2.2)

    Para motor síncrono, Td_pp_ms maior — contribuição
    permanece por mais tempo.
    """
    if time_ms < 0:
        raise ValueError(f"time_ms deve ser >= 0 (achado {time_ms})")
    if p.Td_pp_ms <= 0:
        return 0.0
    return math.exp(-time_ms / p.Td_pp_ms)


# ---------------------------------------------------------------------------
# Validador
# ---------------------------------------------------------------------------


def validate_motor(p: MotorParameters) -> list[str]:
    """Valida parâmetros do motor."""
    errors: list[str] = []

    if not p.name:
        errors.append("name vazio")
    elif len(p.name) > 6:
        errors.append(f"name {p.name!r} > 6 chars")

    for attr in ("node_a", "node_b", "node_c"):
        v = getattr(p, attr)
        if not v:
            errors.append(f"{attr} vazio")
        elif len(v) > 6:
            errors.append(f"{attr} {v!r} > 6 chars")

    if p.rated_voltage_kV <= 0:
        errors.append("rated_voltage_kV deve ser > 0")
    if p.rated_power_kW <= 0:
        errors.append("rated_power_kW deve ser > 0")
    if not (0 < p.rated_pf <= 1.0):
        errors.append(f"rated_pf={p.rated_pf} fora de (0, 1]")
    if not (0 < p.efficiency <= 1.0):
        errors.append(f"efficiency={p.efficiency} fora de (0, 1]")

    if p.locked_rotor_current_pu <= 1.0:
        errors.append(
            f"locked_rotor_current_pu={p.locked_rotor_current_pu} "
            "deve ser > 1 (típico 5-7 para IM standard)"
        )
    if p.locked_rotor_current_pu > 15.0:
        errors.append(
            f"locked_rotor_current_pu={p.locked_rotor_current_pu} "
            "anormal (> 15× — verificar datasheet)"
        )

    if p.n_poles < 2 or p.n_poles % 2 != 0:
        errors.append(f"n_poles deve ser par e ≥ 2 (achado {p.n_poles})")

    if p.Td_pp_ms <= 0:
        errors.append("Td_pp_ms deve ser > 0")

    return errors


# ---------------------------------------------------------------------------
# Conversão para ScSource
# ---------------------------------------------------------------------------


def motor_to_sc_source(p: MotorParameters):
    """
    Converte ``MotorParameters`` em ``ScSource`` com Z''_M
    para inserção em ``ShortCircuitNetwork``.

    Returns
    -------
    ScSource
        Pronta para inserir via ``net.sources.append(src)``.
    """
    from app.postprocessor.short_circuit import ScSource

    z = subtransient_impedance_ohm(p)
    I_n = rated_current_A(p)
    I_LR = locked_rotor_current_A(p)
    return ScSource(
        name=p.name[:6],
        z_ohm=z,
        description=(
            f"Motor {p.motor_type.value} {p.rated_power_kW:.0f} kW "
            f"({p.rated_voltage_kV:.3f} kV, I_rM = {I_n:.1f} A, "
            f"I_LR = {I_LR:.1f} A, I_LR/I_rM = "
            f"{p.locked_rotor_current_pu:.1f}, "
            f"τ = {p.Td_pp_ms:.0f} ms)"
        ),
    )


# ---------------------------------------------------------------------------
# Emissão de cartões ATP
# ---------------------------------------------------------------------------


def emit_motor_metadata_lines(p: MotorParameters) -> list[str]:
    """
    Emite comentários ATP descrevendo o motor.

    Não emite cartão UM (Universal Machine) — para simulação
    transitória completa, use ``app.preprocessor.synchronous_
    machine`` (motor síncrono) ou aguarde implementação UM
    (v0.28.x).

    Apenas documenta os parâmetros como metadata.
    """
    errs = validate_motor(p)
    if errs:
        raise ValueError(
            f"MotorParameters {p.name!r} inválido: " + "; ".join(errs)
        )

    S_kVA = rated_apparent_power_kVA(p)
    I_n = rated_current_A(p)
    I_LR = locked_rotor_current_A(p)
    z = subtransient_impedance_ohm(p)
    n_s_rpm = 120.0 * 60.0 / p.n_poles   # assumindo 60 Hz

    lines = [
        "C ===============================",
        f"C MOTOR: {p.name}",
        f"C   Type: {p.motor_type.value}",
        f"C   V_LL = {p.rated_voltage_kV:.3f} kV  "
        f"P = {p.rated_power_kW:.1f} kW  "
        f"S = {S_kVA:.1f} kVA",
        f"C   cos(φ) = {p.rated_pf:.3f}  η = {p.efficiency:.3f}",
        f"C   n_poles = {p.n_poles}, n_s = {n_s_rpm:.0f} rpm",
        f"C   I_rM = {I_n:.1f} A  I_LR = {I_LR:.1f} A  "
        f"(I_LR/I_rM = {p.locked_rotor_current_pu:.1f})",
        f"C   Z''_M = {z.real:.4f} + j{z.imag:.4f} Ω",
        f"C   Td'' = {p.Td_pp_ms:.0f} ms (decay)",
        "C   SC contribution (subtransient): "
        f"{initial_sc_contribution_kA(p):.3f} kA",
        "C ===============================",
    ]
    return lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_default_induction_motor(
    name: str, node_a: str, node_b: str, node_c: str,
    voltage_kV: float = 0.480, power_kW: float = 100.0,
    locked_rotor_pu: float = 6.0,
) -> MotorParameters:
    """
    Helper: motor de indução padrão NEMA Design B (locked rotor
    ratio 6×, cos(φ) = 0.85, η = 0.95).
    """
    return MotorParameters(
        name=name,
        node_a=node_a, node_b=node_b, node_c=node_c,
        motor_type=MotorType.INDUCTION,
        rated_voltage_kV=voltage_kV,
        rated_power_kW=power_kW,
        rated_pf=0.85, efficiency=0.95,
        locked_rotor_current_pu=locked_rotor_pu,
        starting_pf=0.30, n_poles=4,
        Td_pp_ms=20.0,
    )


def make_large_synchronous_motor(
    name: str, node_a: str, node_b: str, node_c: str,
    voltage_kV: float = 4.16, power_kW: float = 1000.0,
) -> MotorParameters:
    """
    Helper: motor síncrono MV grande (1 MW, 4.16 kV, decay
    longo τ ≈ 200 ms).

    Para precisão completa em estudos de estabilidade,
    considere usar ``SynchronousMachineParameters`` com
    ``P0_MW < 0``.
    """
    return MotorParameters(
        name=name,
        node_a=node_a, node_b=node_b, node_c=node_c,
        motor_type=MotorType.SYNCHRONOUS,
        rated_voltage_kV=voltage_kV,
        rated_power_kW=power_kW,
        rated_pf=0.95, efficiency=0.96,
        locked_rotor_current_pu=5.5,
        starting_pf=0.20, n_poles=4,
        Td_pp_ms=200.0,    # decay longo (síncrono)
    )
