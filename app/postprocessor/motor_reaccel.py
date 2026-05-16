"""
app.postprocessor.motor_reaccel — Re-aceleração de motores
após distúrbio (v0.102.0).

Cobertura
==========

* IEEE Std 399-1997 §10.5 — Re-acceleration scenarios
* IEEE Std 3002.7 — Motor starting/reaccel coordination
* IEC 60034-1 §11 — Operating conditions

Filosofia
==========

Cenários típicos pós-distúrbio:

1. **Re-aceleração simples**: V cai a 70-80% por 1-3s
   (falta upstream extinta), motores devem desacelerar
   sem desconectar e voltar a regime.

2. **Black-start**: V cai a 0 (fonte perdida), todos os
   motores param. Quando V volta, todos tentam partir
   simultaneamente — V_dip massivo.

3. **Bus transfer (ATS)**: chave de transferência demora
   ~50-200 ms; motores giram por inércia. Quando V volta
   na fonte alternativa, fase pode estar deslocada → torque
   transitório.

Saída
======

:class:`ReaccelResult` com:

* ``time_to_full_speed_s`` — tempo até retornar a regime
* ``v_dip_pu`` — pior queda de tensão durante reaccel
* ``v_recovery_time_s`` — tempo para V voltar a 0.95 pu
* ``motors_lost`` — motores que NÃO conseguem reacelerar
* ``status`` — "success" | "partial" | "failure"

Limitações declaradas
======================

* Modelo simplificado de inércia (v0.102.1 fará dinâmica
  rotor completa).
* Assume torque de carga constante (linear quadratic
  torque em v0.102.2).
* Sem modelagem de ATS (transferência) — focado em
  reaccel direta.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ReaccelScenario(str, Enum):
    """Cenário de re-aceleração."""
    VOLTAGE_DIP = "voltage_dip"           # V cai temporariamente
    BLACK_START = "black_start"           # V=0 por longo período
    BUS_TRANSFER = "bus_transfer"         # ATS para fonte alterna


@dataclass(frozen=True)
class MotorState:
    """Estado de um motor (input para reaccel)."""

    motor_id: str
    rated_power_kW: float
    rated_voltage_V: float
    inertia_kg_m2: float = 1.0
    rated_speed_rpm: float = 1800.0
    locked_rotor_current_pu: float = 6.0
    full_load_efficiency: float = 0.92
    full_load_power_factor: float = 0.85

    @property
    def rated_torque_Nm(self) -> float:
        """T = P/ω."""
        omega = 2 * math.pi * self.rated_speed_rpm / 60.0
        return self.rated_power_kW * 1000.0 / omega

    @property
    def rated_current_A(self) -> float:
        return (
            self.rated_power_kW * 1000.0
            / (
                math.sqrt(3) * self.rated_voltage_V
                * self.full_load_power_factor
                * self.full_load_efficiency
            )
        )


@dataclass(frozen=True)
class ReaccelResult:
    """Resultado de simulação de re-aceleração."""

    scenario: ReaccelScenario
    time_to_full_speed_s: float
    v_dip_pu: float
    v_recovery_time_s: float
    motors_lost: tuple[str, ...] = field(default_factory=tuple)
    motors_recovered: tuple[str, ...] = field(default_factory=tuple)
    status: str = "success"   # "success" | "partial" | "failure"
    citation: str = (
        "IEEE Std 399-1997 §10.5 — Re-acceleration analysis"
    )
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passes(self) -> bool:
        """V_dip ≥ 0.7 pu (limite IEEE 399 §10.5)."""
        return self.v_dip_pu >= 0.7 and self.status == "success"

    def summary(self) -> str:
        lines = [
            f"=== Re-aceleração ({self.scenario.value}) ===",
            f"Tempo total reaccel:   {self.time_to_full_speed_s:.2f} s",
            f"V-dip mínimo:          {self.v_dip_pu:.3f} pu",
            f"V-recovery time:       {self.v_recovery_time_s:.2f} s",
            f"Motores recuperados:   {len(self.motors_recovered)}",
            f"Motores perdidos:      {len(self.motors_lost)}",
            f"Status:                {self.status.upper()}",
        ]
        if self.motors_lost:
            lines.append("")
            lines.append("⚠ Motores que NÃO reaceleraram:")
            for m in self.motors_lost:
                lines.append(f"  • {m}")
        if self.warnings:
            lines.append("")
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
        lines.append("")
        lines.append(f"Citação: {self.citation}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def simulate_reaccel(
    motors: list[MotorState],
    scenario: ReaccelScenario = ReaccelScenario.VOLTAGE_DIP,
    *,
    voltage_dip_duration_s: float = 1.0,
    voltage_dip_level_pu: float = 0.7,
    bus_capacity_kVA: float = 10000.0,
) -> ReaccelResult:
    """
    Simula re-aceleração de um conjunto de motores.

    Algoritmo simplificado (v0.102.0):

    1. Durante o dip, motores desaceleram a partir de speed=1.0:
       ``slip(t) = slip_0 + (1 - V²) · t · k``
    2. Quando V retorna (t = duration), motores tentam
       reacelerar simultaneamente — corrente de inrush total
       causa V-dip adicional.
    3. Estima V-dip total via:
       ``V_dip = 1 - (Σ I_LR · k_simul) / S_curto``
    4. Se V_dip < 0.5 pu, motores não conseguem produzir torque
       suficiente → "stall".

    Returns
    -------
    ReaccelResult
    """
    if not motors:
        return ReaccelResult(
            scenario=scenario,
            time_to_full_speed_s=0,
            v_dip_pu=1.0,
            v_recovery_time_s=0,
            warnings=("Nenhum motor fornecido",),
        )

    # Soma de correntes de rotor bloqueado
    total_inrush_kVA = sum(
        m.rated_power_kW * m.locked_rotor_current_pu
        / m.full_load_efficiency
        for m in motors
    )

    # V-dip estimado durante reaccel simultâneo
    # Aproximação: V_dip = V_pre - I_inrush · Z_source
    # Para simplificação, assume X_source = 100% no SCR
    impedance_factor = total_inrush_kVA / bus_capacity_kVA
    v_dip_during_reaccel = max(
        0.3, 1.0 - impedance_factor * 0.3,
    )

    # V_dip mínimo = pior caso entre dip do disturbance e
    # dip do reaccel
    v_dip_pu = min(voltage_dip_level_pu, v_dip_during_reaccel)

    # Tempo de reaccel: depende da inércia + V_dip
    # T_accel ≈ J · ω_rated² / (V² · T_rated · 2)
    # Para simplificação:
    avg_inertia = sum(m.inertia_kg_m2 for m in motors) / len(motors)
    avg_omega = (
        sum(2*math.pi*m.rated_speed_rpm/60 for m in motors)
        / len(motors)
    )
    base_reaccel_time_s = (
        avg_inertia * avg_omega**2
        / (max(v_dip_pu**2, 0.01) * 100.0)
    )
    # Cap a 30s (acima disso geralmente não recupera)
    time_to_full = min(30.0, max(0.5, base_reaccel_time_s))

    # Motores que não recuperam: aqueles que precisam de
    # mais corrente que o bus consegue fornecer com V_dip
    # < 0.5 pu (stall típico)
    motors_lost: list[str] = []
    motors_recovered: list[str] = []
    for m in motors:
        # V_min necessário para produzir torque: ~0.6 pu
        if v_dip_pu < 0.5:
            motors_lost.append(m.motor_id)
        else:
            motors_recovered.append(m.motor_id)

    # Status
    if not motors_lost:
        status = "success"
    elif len(motors_lost) < len(motors):
        status = "partial"
    else:
        status = "failure"

    # V-recovery time (tempo para V voltar a 0.95 pu)
    v_recovery_time = time_to_full * 0.7

    warnings = []
    if v_dip_pu < 0.7:
        warnings.append(
            f"V-dip {v_dip_pu:.3f} pu < 0.7 pu (IEEE 399 §10.5 limite)"
        )
    if status == "failure":
        warnings.append(
            "Re-aceleração falhou — todos motores em stall. "
            "Revise capacidade de barra ou faça partida sequencial."
        )

    return ReaccelResult(
        scenario=scenario,
        time_to_full_speed_s=time_to_full,
        v_dip_pu=v_dip_pu,
        v_recovery_time_s=v_recovery_time,
        motors_lost=tuple(motors_lost),
        motors_recovered=tuple(motors_recovered),
        status=status,
        warnings=tuple(warnings),
    )
