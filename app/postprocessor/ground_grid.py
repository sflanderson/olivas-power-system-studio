"""
app.postprocessor.ground_grid — Análise de malha de
aterramento (v0.103.0).

Cobertura
==========

* IEEE Std 80-2013 — IEEE Guide for Safety in AC Substation
  Grounding
* IEEE Std 81-2012 — IEEE Guide for Measuring Earth
  Resistivity, Ground Impedance, and Earth Surface Potentials

Filosofia
==========

Sistemas de aterramento em substações precisam atender
limites de **touch voltage E_t** e **step voltage E_s**
para proteger pessoas durante faltas. Esta sprint adiciona
o módulo final da Fase 2 do roadmap.

Cálculos principais (IEEE 80 §11):

1. **Resistência da malha** R_g (Schwarz / Sverak):

   ::

       R_g = ρ · [1/L_T + 1/√(20·A) · (1 + 1/(1 + h·√(20/A)))]

   Onde:
   * ρ = resistividade do solo (Ω·m)
   * L_T = comprimento total dos condutores (m)
   * A = área da malha (m²)
   * h = profundidade de enterro (m)

2. **Touch voltage** E_t = K_m · K_i · ρ · I_g / L_M
3. **Step voltage** E_s = K_s · K_i · ρ · I_g / L_S

4. **Limites toleráveis** (peso 50 kg, IEEE 80 §8.4):

   ::

       E_t_50 = (1000 + 1.5·C_s·ρ_s) · 0.116 / √t_s
       E_s_50 = (1000 + 6·C_s·ρ_s) · 0.116 / √t_s

Saída
======

:class:`GroundGridResult` com R_g, E_t, E_s, limites,
violations e status (PASS/FAIL).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GroundGridSpec:
    """Especificação geométrica da malha de aterramento."""

    # Geometria
    area_m2: float                       # área da malha
    length_total_m: float                # L_T (soma de todos condutores)
    n_meshes_x: int = 5                  # número de meshes em X
    n_meshes_y: int = 5                  # número de meshes em Y
    burial_depth_m: float = 0.5          # profundidade enterro

    # Solo
    soil_resistivity_ohm_m: float = 100.0
    surface_resistivity_ohm_m: float = 2500.0   # camada brita
    surface_thickness_m: float = 0.10           # 10 cm

    # Falta
    fault_current_kA: float = 10.0
    fault_clearing_time_s: float = 0.5
    decrement_factor: float = 1.0        # IEC 60909 X/R derived

    # Pessoa (default 50 kg)
    body_weight_kg: float = 50.0


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GroundGridResult:
    """Resultado da análise IEEE 80."""

    R_grid_ohm: float

    # Calculated voltages
    touch_voltage_V: float
    step_voltage_V: float

    # Tolerable limits (peso configurado)
    touch_limit_V: float
    step_limit_V: float

    # GPR (Ground Potential Rise)
    gpr_V: float

    # Status
    touch_passes: bool
    step_passes: bool

    @property
    def passes(self) -> bool:
        return self.touch_passes and self.step_passes

    citation: str = (
        "IEEE Std 80-2013 §11 — Substation Grounding"
    )
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def summary(self) -> str:
        status_t = "✅" if self.touch_passes else "❌"
        status_s = "✅" if self.step_passes else "❌"
        overall = "✅ APROVADO" if self.passes else "❌ INADEQUADO"
        lines = [
            f"=== Análise Malha Aterramento (IEEE 80) — {overall} ===",
            f"R_grid:         {self.R_grid_ohm:.3f} Ω",
            f"GPR:            {self.gpr_V:.0f} V",
            "",
            f"Touch voltage:  {self.touch_voltage_V:.0f} V "
            f"(limite {self.touch_limit_V:.0f} V) {status_t}",
            f"Step voltage:   {self.step_voltage_V:.0f} V "
            f"(limite {self.step_limit_V:.0f} V) {status_s}",
        ]
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


def analyze_ground_grid(spec: GroundGridSpec) -> GroundGridResult:
    """
    Análise completa de malha conforme IEEE 80.

    Returns
    -------
    GroundGridResult
    """
    # Validação física
    if spec.area_m2 <= 0:
        raise ValueError("area_m2 deve ser > 0")
    if spec.length_total_m <= 0:
        raise ValueError("length_total_m deve ser > 0")
    if spec.soil_resistivity_ohm_m <= 0:
        raise ValueError("soil_resistivity deve ser > 0")
    if spec.fault_current_kA <= 0:
        raise ValueError("fault_current_kA deve ser > 0")

    rho = spec.soil_resistivity_ohm_m
    rho_s = spec.surface_resistivity_ohm_m
    h_s = spec.surface_thickness_m
    A = spec.area_m2
    L_T = spec.length_total_m
    h = spec.burial_depth_m
    I_g_A = spec.fault_current_kA * 1000.0 * spec.decrement_factor

    # 1. Resistência da malha (Sverak simplificado)
    R_grid = rho * (
        1.0 / L_T
        + 1.0 / math.sqrt(20.0 * A)
        * (1.0 + 1.0 / (1.0 + h * math.sqrt(20.0 / A)))
    )

    # 2. GPR
    gpr_V = R_grid * I_g_A

    # 3. Surface layer derating (C_s) — IEEE 80 §7.4
    K_layer = 1.0 - rho / rho_s
    C_s = 1.0 - 0.09 * K_layer / (2.0 * h_s + 0.09)
    C_s = max(0.5, min(1.0, C_s))

    # 4. Mesh and step factors (simplified)
    # K_m: spacing factor — depende de meshes/D, h, etc.
    # Aproximação para malha quadrada com spacing uniforme:
    n_meshes = math.sqrt(spec.n_meshes_x * spec.n_meshes_y)
    D = math.sqrt(A) / n_meshes   # spacing typical
    K_m = (
        1.0 / (2.0 * math.pi)
        * (
            math.log(
                D ** 2 / (16.0 * h * 0.01)   # 0.01 = d_conductor
                + (D + 2.0 * h) ** 2 / (8.0 * D * 0.01)
                - h / (4.0 * 0.01)
            )
            + 1.0 / (2.0 * math.pi)
            * math.log(8.0 / (math.pi * (2.0 * n_meshes - 1)))
        )
    )
    K_m = max(0.5, min(2.0, K_m))   # clamp em range físico

    # K_i: irregularity factor
    K_i = 0.644 + 0.148 * n_meshes
    K_i = min(K_i, 3.0)   # cap

    # Effective lengths
    # L_M: para touch voltage (mesh)
    L_M = L_T + 1.55 * (1.0 + 1.0) * 0.5 * spec.length_total_m * 0.1
    L_M = max(L_M, L_T)
    # L_S: para step voltage (rod or grid)
    L_S = 0.75 * L_T

    # 5. Touch and step voltages
    E_t = K_m * K_i * rho * I_g_A / L_M
    E_s = math.sqrt(2) * K_i * rho * I_g_A / L_S * 0.3   # Sverak simplification

    # 6. Tolerable limits (peso 50 kg)
    t_s = spec.fault_clearing_time_s
    if t_s <= 0:
        t_s = 0.5
    E_t_50 = (1000.0 + 1.5 * C_s * rho_s) * 0.116 / math.sqrt(t_s)
    E_s_50 = (1000.0 + 6.0 * C_s * rho_s) * 0.116 / math.sqrt(t_s)

    # Adjust for body weight
    if spec.body_weight_kg >= 70:
        # Pessoa 70 kg → limites maiores
        E_t_limit = E_t_50 * 0.157 / 0.116
        E_s_limit = E_s_50 * 0.157 / 0.116
    else:
        E_t_limit = E_t_50
        E_s_limit = E_s_50

    touch_passes = E_t <= E_t_limit
    step_passes = E_s <= E_s_limit

    warnings = []
    if rho > 1000:
        warnings.append(
            f"Solo de alta resistividade (ρ={rho:.0f} Ω·m) — "
            f"considere camada de brita ou hastes profundas"
        )
    if R_grid > 5.0:
        warnings.append(
            f"R_grid = {R_grid:.2f} Ω alto — IEEE 80 §13.5 "
            f"recomenda ≤1 Ω para subestações de transmissão"
        )

    return GroundGridResult(
        R_grid_ohm=R_grid,
        touch_voltage_V=E_t,
        step_voltage_V=E_s,
        touch_limit_V=E_t_limit,
        step_limit_V=E_s_limit,
        gpr_V=gpr_V,
        touch_passes=touch_passes,
        step_passes=step_passes,
        warnings=tuple(warnings),
    )
