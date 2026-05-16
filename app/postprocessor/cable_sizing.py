"""
app.postprocessor.cable_sizing — Dimensionamento de cabos
elétricos conforme ABNT NBR 5410 / NEC 310 / IEC 60364
(v0.95.0).

Filosofia
==========

PTW Power*Tools / ETAP / EasyPower têm dimensionamento
automático de cabos como módulo CORE. Olivas v0.94 não
tinha — esta é o **bloqueador #1** identificado no audit
estratégico (gap vs comerciais).

Algoritmo
==========

Para uma corrente de carga ``I_load`` numa tensão ``V``:

1. **Aplica fatores de correção (FC)**:
   * FC_temp(T_ambiente) — Tabela 40 NBR 5410
   * FC_grouping(n_circuits) — Tabela 42 NBR 5410
   * FC_total = FC_temp · FC_grouping

2. **Itera bitolas** (1.5 → 500 mm²) buscando a primeira em
   que ``Iz · FC_total ≥ I_load``.

3. **Verifica queda de tensão** (NBR 5410 §6.2.7):
   * ΔV% = (I_load · L · 100) / (V · S · σ_Cu) · cos θ + ...
   * Limite: 4% em regime; 7% em partida de motor.
   * Se exceder, sobe uma bitola e re-itera.

4. **Verifica curto-circuito** (estresse térmico):
   * Bitola mínima por equação t·Ik² ≤ K²·S²
     (K=143 Cu PVC, K=176 Cu EPR/XLPE, K=94 Al PVC).
   * Se a bitola por ampacidade não suporta SC, sobe.

Retorna :class:`CableDesign` com toda a auditoria.

Tabelas implementadas
======================

* Tabela 36 — Cu, PVC 70°C, B1 (eletroduto aparente)
* Tabela 37 — Cu, EPR/XLPE 90°C, B1
* Tabela 38 — Cu, PVC 70°C, A1 (eletroduto embutido)
* Tabela 39 — Cu, EPR/XLPE 90°C, A1
* Tabelas 40–42 — fatores de correção

Limitações declaradas (v0.95.0)
================================

* Apenas Cu (Al em v0.95.1)
* Apenas instalação A1/B1 (subterrâneo D em v0.95.2)
* Apenas trifásico (monofásico em v0.95.3)
* Sem suporte a derivação (apenas feeder direto)
* Considera fp = 0.92 (ajustável por parâmetro)

Cobertura normativa
====================

* ABNT NBR 5410:2008+Em.1:2024 §6.2 — Dimensionamento
* ABNT NBR 5410:2008+Em.1:2024 §6.5.4 — Estresse térmico
* IEC 60364-5-52:2009 — Selection and erection of cables
* NEC 2023 §310 — Conductor ampacities (referência)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.core.logging_config import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ConductorMaterial(str, Enum):
    """Material do condutor."""

    COPPER = "Cu"
    ALUMINUM = "Al"


class Insulation(str, Enum):
    """Tipo de isolação (impacta T_max do cabo)."""

    PVC = "PVC"      # 70°C
    EPR = "EPR"      # 90°C
    XLPE = "XLPE"    # 90°C


class InstallationMethod(str, Enum):
    """
    Método de instalação NBR 5410 (impacta dissipação
    térmica, logo a corrente máxima Iz).

    Apenas os 2 mais comuns na v0.95.0:

    * A1 — Cabos isolados em eletroduto embutido em
           parede termicamente isolante.
    * B1 — Cabos isolados em eletroduto aparente sobre
           parede ou em canaleta sobre parede.

    v0.95.x adicionará: C (bandeja perfurada), D
    (subterrâneo direto), E (cabo no ar), F (multicore
    ao ar), G (single-core no ar).
    """

    A1 = "A1"
    B1 = "B1"


# ---------------------------------------------------------------------------
# Tabelas NBR 5410 — Ampacidades (Iz em A @ 30°C ambient,
# 2 cabos carregados — para 3 cabos aplicar FC_grouping)
# ---------------------------------------------------------------------------


# Tabela 36 — Cu, PVC, B1 (eletroduto aparente)
_TABELA_36_CU_PVC_B1: dict[float, float] = {
    1.5: 17.5, 2.5: 24, 4: 32, 6: 41, 10: 57,
    16: 76, 25: 101, 35: 125, 50: 151, 70: 192,
    95: 232, 120: 269, 150: 309, 185: 353,
    240: 415, 300: 477,
}

# Tabela 37 — Cu, EPR/XLPE 90°C, B1
_TABELA_37_CU_XLPE_B1: dict[float, float] = {
    1.5: 23, 2.5: 31, 4: 42, 6: 54, 10: 75,
    16: 100, 25: 133, 35: 164, 50: 198, 70: 253,
    95: 306, 120: 354, 150: 407, 185: 464,
    240: 546, 300: 628,
}

# Tabela 38 — Cu, PVC, A1 (eletroduto embutido)
_TABELA_38_CU_PVC_A1: dict[float, float] = {
    1.5: 14, 2.5: 18.5, 4: 25, 6: 32, 10: 44,
    16: 60, 25: 79, 35: 97, 50: 118, 70: 150,
    95: 181, 120: 210, 150: 240, 185: 273,
    240: 320, 300: 367,
}

# Tabela 39 — Cu, EPR/XLPE, A1
_TABELA_39_CU_XLPE_A1: dict[float, float] = {
    1.5: 19, 2.5: 26, 4: 35, 6: 45, 10: 61,
    16: 81, 25: 106, 35: 131, 50: 158, 70: 200,
    95: 241, 120: 278, 150: 318, 185: 362,
    240: 424, 300: 486,
}

# Lookup pela combinação (material, isolação, método)
_AMPACITY_TABLES: dict[
    tuple[ConductorMaterial, Insulation, InstallationMethod],
    dict[float, float],
] = {
    (ConductorMaterial.COPPER, Insulation.PVC, InstallationMethod.B1):
        _TABELA_36_CU_PVC_B1,
    (ConductorMaterial.COPPER, Insulation.EPR, InstallationMethod.B1):
        _TABELA_37_CU_XLPE_B1,
    (ConductorMaterial.COPPER, Insulation.XLPE, InstallationMethod.B1):
        _TABELA_37_CU_XLPE_B1,
    (ConductorMaterial.COPPER, Insulation.PVC, InstallationMethod.A1):
        _TABELA_38_CU_PVC_A1,
    (ConductorMaterial.COPPER, Insulation.EPR, InstallationMethod.A1):
        _TABELA_39_CU_XLPE_A1,
    (ConductorMaterial.COPPER, Insulation.XLPE, InstallationMethod.A1):
        _TABELA_39_CU_XLPE_A1,
}


# Bitolas padrão NBR 5410 §6.2.6
STANDARD_SECTIONS_MM2 = (
    1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70,
    95, 120, 150, 185, 240, 300, 400, 500,
)


# Resistividades em Ω·mm²/m a 70°C (operação típica)
RESISTIVITY_OHM_MM2_PER_M = {
    ConductorMaterial.COPPER: 0.02256,    # ρ_Cu @ 70°C
    ConductorMaterial.ALUMINUM: 0.03635,
}


# Constante K para estresse térmico (NBR 5410 Tabela 41)
# t·Ik² ≤ K²·S²  → S_min = Ik · √(t)/K
THERMAL_K_FACTORS = {
    (ConductorMaterial.COPPER, Insulation.PVC): 115,
    (ConductorMaterial.COPPER, Insulation.EPR): 143,
    (ConductorMaterial.COPPER, Insulation.XLPE): 143,
    (ConductorMaterial.ALUMINUM, Insulation.PVC): 76,
    (ConductorMaterial.ALUMINUM, Insulation.EPR): 94,
    (ConductorMaterial.ALUMINUM, Insulation.XLPE): 94,
}


# ---------------------------------------------------------------------------
# Fatores de correção
# ---------------------------------------------------------------------------


# Tabela 40 NBR 5410 — FC para temperatura ambiente
# (assumindo cabo PVC 70°C — para EPR/XLPE 90°C usar Tabela 40b
# em v0.95.1)
_FC_TEMP_PVC = {
    10: 1.22, 15: 1.17, 20: 1.12, 25: 1.06, 30: 1.00,
    35: 0.94, 40: 0.87, 45: 0.79, 50: 0.71, 55: 0.61, 60: 0.50,
}

_FC_TEMP_XLPE = {
    10: 1.15, 15: 1.12, 20: 1.08, 25: 1.04, 30: 1.00,
    35: 0.96, 40: 0.91, 45: 0.87, 50: 0.82, 55: 0.76, 60: 0.71,
}


def _fc_temperature(
    ambient_temp_C: float, insulation: Insulation,
) -> float:
    """
    Fator de correção por temperatura ambiente.
    Interpolação linear para temperaturas intermediárias.
    """
    table = _FC_TEMP_PVC if insulation == Insulation.PVC else _FC_TEMP_XLPE
    if ambient_temp_C <= min(table):
        return table[min(table)]
    if ambient_temp_C >= max(table):
        log.warning(
            "Temperatura ambiente %.1f°C >= 60°C — extrapolando "
            "FC linearmente (verifique manualmente).",
            ambient_temp_C,
        )
        return table[max(table)]
    # Linear interp
    keys = sorted(table.keys())
    for i, k in enumerate(keys[:-1]):
        if k <= ambient_temp_C <= keys[i + 1]:
            t = (ambient_temp_C - k) / (keys[i + 1] - k)
            return table[k] + t * (table[keys[i + 1]] - table[k])
    return 1.0


# Tabela 42 NBR 5410 — FC para agrupamento (eletroduto)
_FC_GROUPING = {
    1: 1.00, 2: 0.80, 3: 0.70, 4: 0.65, 5: 0.60,
    6: 0.57, 7: 0.54, 8: 0.52, 9: 0.50, 10: 0.48,
    12: 0.45, 14: 0.43, 16: 0.41, 18: 0.39, 20: 0.38,
}


def _fc_grouping(n_circuits: int) -> float:
    """Fator de correção por agrupamento (default 0.80 se >20)."""
    if n_circuits <= 0:
        return 1.0
    if n_circuits >= 20:
        return _FC_GROUPING[20]
    if n_circuits in _FC_GROUPING:
        return _FC_GROUPING[n_circuits]
    # Aproximação para valores intermediários
    keys = sorted(_FC_GROUPING.keys())
    for i, k in enumerate(keys[:-1]):
        if k <= n_circuits <= keys[i + 1]:
            t = (n_circuits - k) / (keys[i + 1] - k)
            return _FC_GROUPING[k] + t * (
                _FC_GROUPING[keys[i + 1]] - _FC_GROUPING[k]
            )
    return 1.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CableDesign:
    """
    Resultado do dimensionamento de cabo.

    Atributos
    ---------
    section_mm2:
        Bitola escolhida (mm²).
    material, insulation, installation:
        Tipo do condutor.
    rated_ampacity_A:
        Iz da tabela (sem correções).
    corrected_ampacity_A:
        Iz · FC_temp · FC_grouping.
    voltage_drop_pct:
        Queda de tensão calculada (%).
    voltage_drop_limit_pct:
        Limite (4% regime; 7% partida).
    thermal_min_section_mm2:
        Bitola mínima por estresse térmico (se SC fornecido).
    citation:
        Referência normativa para auditoria.
    warnings:
        Lista de avisos (extrapolações, fc agressivo, etc.).
    """

    # Especificação resultante
    section_mm2: float
    material: ConductorMaterial
    insulation: Insulation
    installation: InstallationMethod

    # Inputs registrados
    load_current_A: float
    rated_voltage_V: float
    length_m: float
    n_phases: int = 3

    # Cálculos
    rated_ampacity_A: float = 0.0
    fc_temperature: float = 1.0
    fc_grouping: float = 1.0
    corrected_ampacity_A: float = 0.0
    voltage_drop_pct: float = 0.0
    voltage_drop_limit_pct: float = 4.0
    thermal_min_section_mm2: Optional[float] = None

    # Status
    passes_ampacity: bool = True
    passes_voltage_drop: bool = True
    passes_thermal: bool = True

    # Auditoria
    citation: str = field(default="NBR 5410:2008+Em.1:2024 §6.2")
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_acceptable(self) -> bool:
        """True se passa todos os critérios (ampacidade + V-drop +
        thermal)."""
        return (
            self.passes_ampacity
            and self.passes_voltage_drop
            and self.passes_thermal
        )

    def summary(self) -> str:
        """Texto humano-legível para popup/laudo."""
        status = "✅ APROVADO" if self.is_acceptable else "❌ INADEQUADO"
        lines = [
            f"=== Cabo dimensionado — {status} ===",
            f"Bitola:              {self.section_mm2:.0f} mm²",
            f"Material:            {self.material.value}",
            f"Isolação:            {self.insulation.value}",
            f"Instalação:          {self.installation.value}",
            f"",
            f"Ampacidade Iz:       {self.rated_ampacity_A:.1f} A "
            f"(Tabela NBR 5410)",
            f"FC temperatura:      {self.fc_temperature:.3f}",
            f"FC agrupamento:      {self.fc_grouping:.3f}",
            f"Ampacidade efetiva:  {self.corrected_ampacity_A:.1f} A",
            f"Corrente de carga:   {self.load_current_A:.1f} A",
            f"  → Margem:          "
            f"{self.corrected_ampacity_A - self.load_current_A:.1f} A "
            f"({100 * (self.corrected_ampacity_A / self.load_current_A - 1):.1f}%)",
            f"",
            f"Comprimento:         {self.length_m:.0f} m",
            f"Queda de tensão:     {self.voltage_drop_pct:.2f}% "
            f"(limite {self.voltage_drop_limit_pct:.0f}%)",
        ]
        if self.thermal_min_section_mm2 is not None:
            lines.append(
                f"Bitola mín térmica:  "
                f"{self.thermal_min_section_mm2:.1f} mm² "
                f"(estresse curto-circuito)"
            )
        if self.warnings:
            lines.append("")
            lines.append("⚠ AVISOS:")
            for w in self.warnings:
                lines.append(f"  • {w}")
        lines.append("")
        lines.append(f"Citação: {self.citation}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def dimension_cable(
    load_current_A: float,
    rated_voltage_V: float,
    length_m: float,
    *,
    material: ConductorMaterial = ConductorMaterial.COPPER,
    insulation: Insulation = Insulation.PVC,
    installation: InstallationMethod = InstallationMethod.B1,
    ambient_temp_C: float = 30.0,
    n_circuits: int = 1,
    n_phases: int = 3,
    power_factor: float = 0.92,
    voltage_drop_limit_pct: float = 4.0,
    sc_current_kA: Optional[float] = None,
    sc_clearing_time_s: Optional[float] = None,
    min_section_override_mm2: Optional[float] = None,
) -> CableDesign:
    """
    Dimensiona um cabo conforme NBR 5410 §6.2.

    Algoritmo:

    1. Aplica FCs (temperatura + agrupamento).
    2. Itera bitolas crescentes até Iz·FC ≥ I_load.
    3. Calcula V-drop; se > limite, sobe bitola e repete.
    4. Verifica estresse térmico SC (se fornecido).

    Parameters
    ----------
    load_current_A:
        Corrente de carga (A).
    rated_voltage_V:
        Tensão nominal LL (V).
    length_m:
        Comprimento do cabo (m).
    material, insulation, installation:
        Tipo do condutor.
    ambient_temp_C:
        Temperatura ambiente (default 30°C).
    n_circuits:
        Número de circuitos no agrupamento (default 1).
    n_phases:
        3 (default) ou 1.
    power_factor:
        cos θ (default 0.92).
    voltage_drop_limit_pct:
        Limite de queda (default 4% NBR 5410 §6.2.7;
        partida de motor usar 7%).
    sc_current_kA:
        Ik'' (kA) para verificação térmica (opcional).
    sc_clearing_time_s:
        Tempo de extinção (s).
    min_section_override_mm2:
        Bitola mínima a usar (ignora bitolas menores).

    Returns
    -------
    CableDesign

    Raises
    ------
    ValueError
        Se inputs físicos forem inválidos.
    """
    # Validação física
    if load_current_A <= 0:
        raise ValueError(
            f"load_current_A deve ser > 0 (got {load_current_A})"
        )
    if rated_voltage_V <= 0:
        raise ValueError(
            f"rated_voltage_V deve ser > 0 (got {rated_voltage_V})"
        )
    if length_m <= 0:
        raise ValueError(f"length_m deve ser > 0 (got {length_m})")
    if not (0 < power_factor <= 1.0):
        raise ValueError(
            f"power_factor deve estar em (0, 1] (got {power_factor})"
        )

    # Lookup tabela
    key = (material, insulation, installation)
    if key not in _AMPACITY_TABLES:
        raise ValueError(
            f"Combinação não tabelada (v0.95.0 cobre Cu PVC/EPR/XLPE "
            f"em A1/B1): {material.value}/{insulation.value}/"
            f"{installation.value}"
        )
    table = _AMPACITY_TABLES[key]

    # Fatores de correção
    fc_temp = _fc_temperature(ambient_temp_C, insulation)
    fc_group = _fc_grouping(n_circuits)
    fc_total = fc_temp * fc_group

    warnings: list[str] = []
    if fc_total < 0.5:
        warnings.append(
            f"FC_total = {fc_total:.3f} é muito agressivo "
            f"(temp={ambient_temp_C}°C, n_circ={n_circuits}). "
            "Considere mudar método de instalação."
        )

    # Bitola mínima por SC (se fornecido)
    thermal_min = None
    if sc_current_kA is not None and sc_clearing_time_s is not None:
        K = THERMAL_K_FACTORS.get(
            (material, insulation),
            THERMAL_K_FACTORS[
                (ConductorMaterial.COPPER, Insulation.PVC)
            ],
        )
        # S_min = Ik * sqrt(t) / K
        thermal_min = (
            sc_current_kA * 1000.0 * math.sqrt(sc_clearing_time_s) / K
        )

    # Itera bitolas
    sections = sorted(s for s in table.keys()
                      if min_section_override_mm2 is None
                      or s >= min_section_override_mm2)
    chosen_section = None
    chosen_iz = 0.0
    chosen_v_drop = 0.0

    for section in sections:
        iz = table[section]
        iz_corrected = iz * fc_total

        # Critério 1: ampacidade
        if iz_corrected < load_current_A:
            continue

        # Critério 2: V-drop
        v_drop_pct = _calculate_voltage_drop(
            load_current_A=load_current_A,
            length_m=length_m,
            section_mm2=section,
            material=material,
            voltage_V=rated_voltage_V,
            power_factor=power_factor,
            n_phases=n_phases,
        )
        if v_drop_pct > voltage_drop_limit_pct:
            continue

        # Critério 3: estresse térmico (se aplicável)
        if thermal_min is not None and section < thermal_min:
            continue

        # Passou todos os critérios
        chosen_section = section
        chosen_iz = iz
        chosen_v_drop = v_drop_pct
        break

    if chosen_section is None:
        # Nenhuma bitola padrão atende — retorna a maior + status fail
        chosen_section = sections[-1]
        chosen_iz = table[chosen_section]
        chosen_v_drop = _calculate_voltage_drop(
            load_current_A, length_m, chosen_section,
            material, rated_voltage_V, power_factor, n_phases,
        )
        warnings.append(
            f"Nenhuma bitola padrão até {chosen_section} mm² "
            f"atende todos os critérios. Considere paralelizar "
            f"condutores ou subir tensão."
        )

    iz_corrected_chosen = chosen_iz * fc_total
    passes_ampacity = iz_corrected_chosen >= load_current_A
    passes_v_drop = chosen_v_drop <= voltage_drop_limit_pct
    passes_thermal = (
        thermal_min is None or chosen_section >= thermal_min
    )

    log.info(
        "Cabo dimensionado: %.0f mm² %s/%s/%s — Iz_eff=%.1fA, "
        "V-drop=%.2f%%, status=%s",
        chosen_section, material.value, insulation.value,
        installation.value, iz_corrected_chosen, chosen_v_drop,
        "OK" if (passes_ampacity and passes_v_drop and passes_thermal)
        else "FAIL",
    )

    return CableDesign(
        section_mm2=chosen_section,
        material=material,
        insulation=insulation,
        installation=installation,
        load_current_A=load_current_A,
        rated_voltage_V=rated_voltage_V,
        length_m=length_m,
        n_phases=n_phases,
        rated_ampacity_A=chosen_iz,
        fc_temperature=fc_temp,
        fc_grouping=fc_group,
        corrected_ampacity_A=iz_corrected_chosen,
        voltage_drop_pct=chosen_v_drop,
        voltage_drop_limit_pct=voltage_drop_limit_pct,
        thermal_min_section_mm2=thermal_min,
        passes_ampacity=passes_ampacity,
        passes_voltage_drop=passes_v_drop,
        passes_thermal=passes_thermal,
        warnings=tuple(warnings),
    )


def _calculate_voltage_drop(
    load_current_A: float,
    length_m: float,
    section_mm2: float,
    material: ConductorMaterial,
    voltage_V: float,
    power_factor: float,
    n_phases: int,
) -> float:
    """
    Calcula queda de tensão percentual.

    Para sistema trifásico (NBR 5410 §6.2.7.1):

    ::

        ΔV = √3 · I · L · (R_km · cos θ + X_km · sin θ) / 1000

    Para monofásico:

    ::

        ΔV = 2 · I · L · (R_km · cos θ + X_km · sin θ) / 1000

    Resistência por unidade de comprimento:

    ::

        R_km = ρ · 1000 / S    [Ω/km]

    Reatância por unidade (X_km) é aproximada como 10% de
    R_km para cabos LV (caso conservador).

    Returns
    -------
    float
        ΔV em percentual (0..100).
    """
    rho = RESISTIVITY_OHM_MM2_PER_M[material]
    R_km = rho * 1000.0 / section_mm2          # Ω/km
    X_km = 0.1 * R_km                          # aproximação LV
    sin_theta = math.sqrt(max(0.0, 1.0 - power_factor ** 2))
    factor = math.sqrt(3.0) if n_phases == 3 else 2.0
    delta_V = (
        factor * load_current_A * length_m
        * (R_km * power_factor + X_km * sin_theta)
        / 1000.0
    )
    return 100.0 * delta_V / voltage_V


def voltage_drop_percent(
    load_current_A: float,
    length_m: float,
    section_mm2: float,
    *,
    material: ConductorMaterial = ConductorMaterial.COPPER,
    voltage_V: float = 380.0,
    power_factor: float = 0.92,
    n_phases: int = 3,
) -> float:
    """
    API pública para cálculo de queda de tensão sem
    dimensionamento.

    Útil em :mod:`app.postprocessor.studies.voltage_drop` (v0.96).
    """
    return _calculate_voltage_drop(
        load_current_A=load_current_A,
        length_m=length_m,
        section_mm2=section_mm2,
        material=material,
        voltage_V=voltage_V,
        power_factor=power_factor,
        n_phases=n_phases,
    )
