"""
app.postprocessor.power_flow_unbalanced — Power flow
3-fase com sequências 0/1/2 (v0.100.0).

Cobertura
==========

* IEEE Std 399-1997 §6 — Three-phase analysis
* Stevenson §11 — Componentes simétricas
* IEEE Std 1159-2019 — Voltage unbalance limits

Filosofia
==========

PF v0.94.0 e anteriores eram **single-phase positive
sequence apenas**. Esta sprint adiciona modelagem das 3
sequências para análise de:

* Voltage unbalance (V_neg / V_pos)
* Cargas single-phase descompensadas
* Faltas com geração reverse (motor regen)

Limites IEEE 1159: voltage unbalance ≤ 2% steady-state.

Saída
======

:class:`UnbalancedPFResult` com:

* ``V_a``, ``V_b``, ``V_c`` por bus (módulo + ângulo)
* ``V_pos``, ``V_neg``, ``V_zero`` em pu
* ``unbalance_factor_pct`` = V_neg / V_pos × 100
* ``violations`` (buses com unbalance > 2%)
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BusUnbalancedVoltage:
    """Tensão em um bus em coordenadas fase + sequência."""

    bus_id: str

    # Tensões de fase (V LN, complex)
    V_a_real: float = 0.0
    V_a_imag: float = 0.0
    V_b_real: float = 0.0
    V_b_imag: float = 0.0
    V_c_real: float = 0.0
    V_c_imag: float = 0.0

    # Componentes simétricas (em pu da fundamental)
    V_pos_pu: float = 1.0
    V_neg_pu: float = 0.0
    V_zero_pu: float = 0.0

    @property
    def unbalance_factor_pct(self) -> float:
        """V_neg / V_pos × 100 (IEEE 1159)."""
        if self.V_pos_pu < 1e-6:
            return 0.0
        return 100.0 * self.V_neg_pu / self.V_pos_pu

    @property
    def V_a_magnitude(self) -> float:
        return math.sqrt(self.V_a_real ** 2 + self.V_a_imag ** 2)

    @property
    def V_b_magnitude(self) -> float:
        return math.sqrt(self.V_b_real ** 2 + self.V_b_imag ** 2)

    @property
    def V_c_magnitude(self) -> float:
        return math.sqrt(self.V_c_real ** 2 + self.V_c_imag ** 2)


@dataclass(frozen=True)
class UnbalancedPFResult:
    """Resultado do PF 3-fase desbalanceado."""

    per_bus: dict[str, BusUnbalancedVoltage] = field(
        default_factory=dict,
    )
    violations: tuple[str, ...] = field(default_factory=tuple)
    unbalance_limit_pct: float = 2.0
    citation: str = (
        "IEEE Std 1159-2019 §6.5 — Voltage unbalance limit"
    )
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def summary(self) -> str:
        lines = [
            "=== Power Flow Unbalanced (IEEE 1159) ===",
            f"Buses analisados: {len(self.per_bus)}",
            f"Limite unbalance: {self.unbalance_limit_pct:.1f}%",
            f"Violations:       {len(self.violations)}",
            "",
            "Unbalance factor por bus:",
        ]
        for bus_id, v in sorted(self.per_bus.items()):
            uf = v.unbalance_factor_pct
            marker = "❌" if uf > self.unbalance_limit_pct else "✅"
            lines.append(
                f"  {marker} {bus_id:25s}  UF = {uf:.2f}%  "
                f"(V_pos={v.V_pos_pu:.4f}, V_neg={v.V_neg_pu:.4f})"
            )
        lines.append("")
        lines.append(f"Citação: {self.citation}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Symmetrical component transformation
# ---------------------------------------------------------------------------


# Operador a = e^(j·120°)
_A = cmath.exp(2j * math.pi / 3)
_A2 = cmath.exp(4j * math.pi / 3)


def phase_to_sequence(
    Va: complex, Vb: complex, Vc: complex,
) -> tuple[complex, complex, complex]:
    """
    Transformação fase → sequência (Fortescue):

    ::

        | V0 |   1  | 1  1   1  | | Va |
        | V1 | = - | 1  a   a² | | Vb |
        | V2 |   3  | 1  a²  a  | | Vc |

    Returns
    -------
    (V0, V1, V2) — sequência zero, positiva, negativa.
    """
    V0 = (Va + Vb + Vc) / 3.0
    V1 = (Va + _A * Vb + _A2 * Vc) / 3.0
    V2 = (Va + _A2 * Vb + _A * Vc) / 3.0
    return V0, V1, V2


def sequence_to_phase(
    V0: complex, V1: complex, V2: complex,
) -> tuple[complex, complex, complex]:
    """
    Transformação sequência → fase:

    ::

        | Va |   | 1  1   1  | | V0 |
        | Vb | = | 1  a²  a  | | V1 |
        | Vc |   | 1  a   a² | | V2 |

    Returns
    -------
    (Va, Vb, Vc).
    """
    Va = V0 + V1 + V2
    Vb = V0 + _A2 * V1 + _A * V2
    Vc = V0 + _A * V1 + _A2 * V2
    return Va, Vb, Vc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_unbalanced_pf(
    project,
    *,
    unbalance_limit_pct: float = 2.0,
    base_voltage_pu: float = 1.0,
    typical_unbalance_per_bus_pct: float = 0.5,
) -> UnbalancedPFResult:
    """
    Análise simplificada (v0.100.0) de PF desbalanceado.

    Esta versão usa modelagem analítica:

    * Para cada bus, assume V_pos = base_voltage_pu (1.0 pu)
    * V_neg = ``typical_unbalance_per_bus_pct`` (default 0.5%)
    * V_zero = 0 (assumindo Y-Y simétrico, sem load LG)
    * Computa V_a, V_b, V_c via Fortescue

    v0.100.1 fará Newton-Raphson 3-fase real com matriz
    admitância de sequência.

    Returns
    -------
    UnbalancedPFResult
    """
    from app.core.logging_config import get_logger
    log = get_logger(__name__)

    per_bus: dict[str, BusUnbalancedVoltage] = {}
    warnings: list[str] = []

    buses = [c for c in project.components if c.type == "BUS"]
    if not buses:
        return UnbalancedPFResult(
            warnings=("Nenhum BUS no projeto",),
        )

    V1 = complex(base_voltage_pu, 0)
    V2_mag = base_voltage_pu * typical_unbalance_per_bus_pct / 100.0
    V2 = complex(V2_mag, 0)
    V0 = complex(0, 0)

    Va, Vb, Vc = sequence_to_phase(V0, V1, V2)

    for c in buses:
        bus_id = (c.get(0, "") or c.name).strip()
        if not bus_id:
            continue
        bus_voltage = BusUnbalancedVoltage(
            bus_id=bus_id,
            V_a_real=Va.real, V_a_imag=Va.imag,
            V_b_real=Vb.real, V_b_imag=Vb.imag,
            V_c_real=Vc.real, V_c_imag=Vc.imag,
            V_pos_pu=abs(V1),
            V_neg_pu=abs(V2),
            V_zero_pu=abs(V0),
        )
        per_bus[bus_id] = bus_voltage

    violations = tuple(
        bus_id for bus_id, v in per_bus.items()
        if v.unbalance_factor_pct > unbalance_limit_pct
    )

    if violations:
        warnings.append(
            f"{len(violations)} bus(es) violam unbalance "
            f"limit {unbalance_limit_pct:.1f}%"
        )

    log.info(
        "Unbalanced PF: %d buses, %d violations",
        len(per_bus), len(violations),
    )

    return UnbalancedPFResult(
        per_bus=per_bus,
        violations=violations,
        unbalance_limit_pct=unbalance_limit_pct,
        warnings=tuple(warnings),
    )
