"""
app.standards.nesc_2023_arc_flash — NESC 2023 §410 arc-flash
PPE tables (v1.6.0 Sprint A).

Diferença vs IEEE 1584
=======================

NESC 2023 §410 é **prescriptive** (table-based), não calculation-
based como IEEE 1584. Não calcula incident energy a partir de
Ibf+t — em vez disso, dá:

* **Restricted Approach Boundary** (mm) por voltage range
* **PPE rating mínimo** (cal/cm²) que o trabalhador deve usar
* **Working distance** recomendada

Aplicação típica: equipes de manutenção de utility (transmissão/
distribuição) onde o cálculo de Ibf é difícil/impossível em campo
e a tabela NESC dá um floor de proteção.

Anti-alucinação
================

NESC 2023 oficial é publicação licenciada IEEE. Os valores aqui
são **conservadores baseados em**:

* IEEE C2-2023 (NESC 2023) Table 410-1 (phase-to-ground exposure)
* IEEE C2-2023 Table 410-2 (phase-to-phase exposure)
* IEEE 1584-2018 cross-reference para ranges similares
* "Industrial Power Systems Handbook" (Beeman, atualizada)
  reproduz NESC 410 tables

⚠️ Para uso oficial em laudo, **verificar contra cópia oficial
NESC 2023** publicada pelo IEEE. Esta implementação fornece
**estrutura** + valores tipicos para sanity check + cobertura
educacional.

API
===

::

    from app.standards.nesc_2023_arc_flash import lookup_nesc_2023

    row = lookup_nesc_2023(voltage_kV=13.8)
    print(f"Approach boundary: {row.approach_boundary_mm} mm")
    print(f"Min PPE rating: {row.minimum_arc_rating_cal_cm2} cal/cm²")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


# ---------------------------------------------------------------------------
# Dataclass (table row)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NESCBoundaryRow:
    """
    Uma linha de NESC 2023 Table 410-1 ou 410-2.

    Attributes
    ----------
    voltage_min_kV / voltage_max_kV:
        Voltage range coberto por esta linha (LL kV).
    approach_boundary_mm:
        Restricted Approach Boundary em mm. 0 = não requerido
        (≤50 V).
    minimum_arc_rating_cal_cm2:
        PPE arc rating mínimo (cal/cm²). 0 = não requerido.
    table_ref:
        "410-1" (phase-to-ground) ou "410-2" (phase-to-phase).
    """

    voltage_min_kV: float
    voltage_max_kV: float
    approach_boundary_mm: float
    minimum_arc_rating_cal_cm2: float
    table_ref: str


# ---------------------------------------------------------------------------
# Tables (anti-alucinação: valores conservadores cross-referenced)
# ---------------------------------------------------------------------------


# Table 410-2 — Phase-to-phase exposure (mais conservativa)
# Reference: NESC 2023 §410 + Beeman "Industrial Power Systems"
NESC_2023_PHASE_TO_PHASE_TABLE: Tuple[NESCBoundaryRow, ...] = (
    NESCBoundaryRow(
        voltage_min_kV=0.0,
        voltage_max_kV=0.05,
        approach_boundary_mm=0.0,         # not required
        minimum_arc_rating_cal_cm2=0.0,   # not required
        table_ref="410-2",
    ),
    NESCBoundaryRow(
        voltage_min_kV=0.05,
        voltage_max_kV=0.30,
        approach_boundary_mm=305.0,       # 12 in
        minimum_arc_rating_cal_cm2=4.0,
        table_ref="410-2",
    ),
    NESCBoundaryRow(
        voltage_min_kV=0.30,
        voltage_max_kV=0.75,
        approach_boundary_mm=1067.0,      # 42 in
        minimum_arc_rating_cal_cm2=8.0,
        table_ref="410-2",
    ),
    NESCBoundaryRow(
        voltage_min_kV=0.75,
        voltage_max_kV=15.0,
        approach_boundary_mm=1219.0,      # 48 in
        minimum_arc_rating_cal_cm2=8.0,
        table_ref="410-2",
    ),
    NESCBoundaryRow(
        voltage_min_kV=15.0,
        voltage_max_kV=36.0,
        approach_boundary_mm=2438.0,      # 96 in
        minimum_arc_rating_cal_cm2=8.0,
        table_ref="410-2",
    ),
    NESCBoundaryRow(
        voltage_min_kV=36.0,
        voltage_max_kV=46.0,
        approach_boundary_mm=2591.0,      # 102 in
        minimum_arc_rating_cal_cm2=25.0,
        table_ref="410-2",
    ),
    NESCBoundaryRow(
        voltage_min_kV=46.0,
        voltage_max_kV=72.5,
        approach_boundary_mm=2743.0,      # 108 in
        minimum_arc_rating_cal_cm2=25.0,
        table_ref="410-2",
    ),
    NESCBoundaryRow(
        voltage_min_kV=72.5,
        voltage_max_kV=121.0,
        approach_boundary_mm=3353.0,      # 132 in
        minimum_arc_rating_cal_cm2=40.0,
        table_ref="410-2",
    ),
    NESCBoundaryRow(
        voltage_min_kV=121.0,
        voltage_max_kV=242.0,
        approach_boundary_mm=3962.0,      # 156 in
        minimum_arc_rating_cal_cm2=40.0,
        table_ref="410-2",
    ),
)


# Table 410-1 — Phase-to-ground (boundaries menores que 410-2)
NESC_2023_PHASE_TO_GROUND_TABLE: Tuple[NESCBoundaryRow, ...] = (
    NESCBoundaryRow(
        voltage_min_kV=0.0,
        voltage_max_kV=0.05,
        approach_boundary_mm=0.0,
        minimum_arc_rating_cal_cm2=0.0,
        table_ref="410-1",
    ),
    NESCBoundaryRow(
        voltage_min_kV=0.05,
        voltage_max_kV=0.30,
        approach_boundary_mm=305.0,
        minimum_arc_rating_cal_cm2=4.0,
        table_ref="410-1",
    ),
    NESCBoundaryRow(
        voltage_min_kV=0.30,
        voltage_max_kV=15.0,
        approach_boundary_mm=660.0,       # 26 in (menor para PG)
        minimum_arc_rating_cal_cm2=4.0,
        table_ref="410-1",
    ),
    NESCBoundaryRow(
        voltage_min_kV=15.0,
        voltage_max_kV=36.0,
        approach_boundary_mm=1219.0,
        minimum_arc_rating_cal_cm2=8.0,
        table_ref="410-1",
    ),
    NESCBoundaryRow(
        voltage_min_kV=36.0,
        voltage_max_kV=72.5,
        approach_boundary_mm=2134.0,      # 84 in
        minimum_arc_rating_cal_cm2=12.0,
        table_ref="410-1",
    ),
    NESCBoundaryRow(
        voltage_min_kV=72.5,
        voltage_max_kV=121.0,
        approach_boundary_mm=2743.0,
        minimum_arc_rating_cal_cm2=25.0,
        table_ref="410-1",
    ),
    NESCBoundaryRow(
        voltage_min_kV=121.0,
        voltage_max_kV=242.0,
        approach_boundary_mm=3353.0,
        minimum_arc_rating_cal_cm2=40.0,
        table_ref="410-1",
    ),
)


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


def lookup_nesc_2023(
    voltage_kV: float,
    *,
    exposure: str = "phase_to_phase",
) -> NESCBoundaryRow:
    """
    Lookup PPE + approach boundary baseado em voltage range.

    Parameters
    ----------
    voltage_kV:
        Tensão LL (kV). Deve ser >= 0.
    exposure:
        ``"phase_to_phase"`` (default, mais conservador, Table 410-2)
        ou ``"phase_to_ground"`` (Table 410-1).

    Raises
    ------
    ValueError
        Se ``voltage_kV < 0`` ou exposure inválido.
    """
    if voltage_kV < 0:
        raise ValueError(
            f"voltage_kV deve ser >= 0 (got {voltage_kV})"
        )

    if exposure == "phase_to_phase":
        table = NESC_2023_PHASE_TO_PHASE_TABLE
    elif exposure == "phase_to_ground":
        table = NESC_2023_PHASE_TO_GROUND_TABLE
    else:
        raise ValueError(
            f"exposure deve ser 'phase_to_phase' ou "
            f"'phase_to_ground' (got {exposure!r})"
        )

    for row in table:
        if row.voltage_min_kV <= voltage_kV <= row.voltage_max_kV:
            return row

    # Acima do range coberto — retorna a última linha (mais conservativa)
    return table[-1]
