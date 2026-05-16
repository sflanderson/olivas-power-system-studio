"""
app.postprocessor.studies.arc_flash_study — Estudo de
Energia Incidente / Arc-Flash MODULAR (v0.94.0).

PTW-style — REQUIRES Short-Circuit + Coordenação.

Cobertura normativa
====================

* ABNT NBR 17227:2025 — Arco elétrico (Brasil)
* IEEE Std 1584-2018 — IEEE Guide for Performing
  Arc-Flash Hazard Calculations
* NFPA 70E:2024 §130.5 — Arc-flash risk assessment

Saída
======

:class:`ArcFlashStudyResult` — dataclass frozen com:

* ``incident_energy_cal_cm2`` — Energia incidente
* ``arc_flash_boundary_mm`` — DLA
* ``ppe_category`` — Cat 0/1/2/3/4 ou DANGER/N/A
* ``warnings``

Out-of-scope handling
======================

Para sistemas HV (>15 kV), o módulo arc-flash NBR 17227 /
IEEE 1584 não se aplica. v0.93.4 introduziu fallback
graceful — este módulo herda esse comportamento:

* Try/except ValueError → ``status="out_of_scope"``,
  E=0, DLA=0, PPE="N/A"
* Warning explícito com motivo

Uso
====

::

    from app.postprocessor.studies import arc_flash_study

    # Auto-roda SC + Coord
    af = arc_flash_study.run(project, "BUS-MAIN-13.8", cache=cache)
    if af.status == "computed":
        print(f"E = {af.incident_energy_cal_cm2:.2f} cal/cm²")
    elif af.status == "out_of_scope":
        print("Bus HV — arc-flash não aplicável")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.postprocessor.study_cache import (
    PrerequisiteError, StudyCache, hash_study_inputs,
)
from app.postprocessor.studies.coordination import (
    CoordinationStudyResult,
    run as run_coord,
)
from app.postprocessor.studies.short_circuit import (
    ShortCircuitStudyResult,
    run as run_sc,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArcFlashStudyResult:
    """Resultado do estudo de arc-flash (v0.94)."""

    bus_id: str

    # Status: "computed" (válido) | "out_of_scope" (HV) |
    # "no_clearing_time" (coord faltou)
    status: str = "computed"

    # Resultado quando status="computed"
    incident_energy_cal_cm2: float = 0.0
    arc_flash_boundary_mm: float = 0.0
    ppe_category: str = "N/A"

    # Inputs derivados (referências cruzadas)
    sc_input_Ibf_kA: float = 0.0
    coord_clearing_time_ms: float = 0.0

    # Justificativa quando out_of_scope
    out_of_scope_reason: str = ""

    warnings: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run(
    project,
    bus_id: str,
    *,
    cache: Optional[StudyCache] = None,
    config: Optional[Any] = None,
    coordination_clearing_time_ms: float = 500.0,
    auto_run_prereqs: bool = True,
) -> ArcFlashStudyResult:
    """
    Executa estudo de arc-flash para ``bus_id``.

    **REQUIRES SC + Coordenação**.

    Auto-rodam se ``auto_run_prereqs=True``. Senão raises
    :class:`PrerequisiteError`.

    Out-of-scope (>15 kV): retorna ``status="out_of_scope"``
    com warning, em vez de levantar exceção.

    Returns
    -------
    ArcFlashStudyResult
    """
    from app.postprocessor.bus_pipeline import BusPipelineConfig

    if config is None:
        config = BusPipelineConfig()

    # Cache hit?
    if cache is not None:
        h = hash_study_inputs(
            project, bus_id,
            ("arc_flash", config, coordination_clearing_time_ms),
        )
        cached = cache.get_arc_flash_if_valid(bus_id, h)
        if cached is not None:
            return cached

    # Prereqs: SC + Coord
    missing = []
    sc_result: Optional[ShortCircuitStudyResult] = None
    coord_result: Optional[CoordinationStudyResult] = None
    if cache is not None:
        sc_result = cache.get_sc(bus_id)
        coord_result = cache.get_coord(bus_id)

    if sc_result is None:
        missing.append("short_circuit")
    if coord_result is None:
        missing.append("coordination")

    if missing and not auto_run_prereqs:
        raise PrerequisiteError(
            study="arc_flash",
            bus_id=bus_id,
            missing=missing,
        )

    if sc_result is None:
        sc_result = run_sc(
            project, bus_id, cache=cache, config=config,
        )
    if coord_result is None:
        coord_result = run_coord(
            project, bus_id, cache=cache, config=config,
            coordination_clearing_time_ms=coordination_clearing_time_ms,
        )

    # Compute arc-flash
    result = _compute_arc_flash(
        project, bus_id, sc_result, coord_result,
    )

    # Store
    if cache is not None:
        cache.set_arc_flash(bus_id, result, h)

    return result


# ---------------------------------------------------------------------------
# Internal: compute
# ---------------------------------------------------------------------------


def _compute_arc_flash(
    project, bus_id: str,
    sc_result: ShortCircuitStudyResult,
    coord_result: CoordinationStudyResult,
) -> ArcFlashStudyResult:
    from app.postprocessor.arc_flash import calculate_arc_flash
    from app.postprocessor.bus_pipeline import (
        _bus_from_pp_component, bus_to_arc_flash_case,
        find_bus_component,
    )

    bus_comp = find_bus_component(project, bus_id)
    if bus_comp is None:
        raise ValueError(f"BUS {bus_id!r} não encontrado.")
    bus = _bus_from_pp_component(bus_comp)

    try:
        af_case = bus_to_arc_flash_case(
            bus,
            bolted_fault_current_kA=sc_result.Ik_pp_kA,
            coordination_clearing_time_ms=(
                coord_result.coordination_clearing_time_ms
            ),
        )
        af_report = calculate_arc_flash(af_case)
    except ValueError as exc:
        # Out-of-scope (HV ou Ibf inválido)
        from app.core.logging_config import get_logger
        get_logger(__name__).warning(
            "Arc-flash out-of-scope para %s (V=%.2f kV): %s",
            bus_id, bus.rated_voltage_kV, exc,
        )
        return ArcFlashStudyResult(
            bus_id=bus_id,
            status="out_of_scope",
            sc_input_Ibf_kA=sc_result.Ik_pp_kA,
            coord_clearing_time_ms=(
                coord_result.coordination_clearing_time_ms
            ),
            out_of_scope_reason=str(exc),
            warnings=(f"Arc-flash pulado: {exc}",),
        )

    return ArcFlashStudyResult(
        bus_id=bus_id,
        status="computed",
        incident_energy_cal_cm2=af_report.incident_energy_cal_cm2,
        arc_flash_boundary_mm=af_report.arc_flash_boundary_mm,
        ppe_category=af_report.ppe_category.value,
        sc_input_Ibf_kA=sc_result.Ik_pp_kA,
        coord_clearing_time_ms=(
            coord_result.coordination_clearing_time_ms
        ),
        warnings=(),
    )
