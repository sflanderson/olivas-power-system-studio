"""
app.postprocessor.studies.coordination — Estudo de
Coordenação e Seletividade MODULAR (v0.94.0).

PTW-style — REQUIRES Short-Circuit. Se SC não foi
computado para o bus alvo, este estudo:

* AUTO-RODA SC (default ``auto_run_prereqs=True``)
* OU levanta :class:`PrerequisiteError` (se
  ``auto_run_prereqs=False``).

Cobertura normativa
====================

* IEEE 242-2001 (Buff Book) §15 — Filosofia de
  coordenação 50/51
* IEC 60255-151 — Curvas TC inversas
* ANSI/IEEE C37.112 — Curvas inversas padrão
* NBR 5410 §6 — Tempos típicos de extinção

Saída
======

:class:`CoordinationStudyResult` — dataclass frozen com:

* ``relay_suggestions`` — tupla de sugestões 50/51 (TMS,
  pickup, tempo de operação no Ik'')
* ``effective_clearing_time_ms`` — tempo total de
  extinção estimado
* ``has_AFD`` — Arc Fault Detection ativo?
* ``warnings``

Uso
====

::

    from app.postprocessor.studies import coordination

    # Auto-roda SC se necessário
    coord = coordination.run(project, "BUS-MAIN-13.8", cache=cache)

    # Strict mode: raises se SC não foi computado
    try:
        coord = coordination.run(
            project, "BUS-MAIN-13.8", cache=cache,
            auto_run_prereqs=False,
        )
    except PrerequisiteError as e:
        print(f"Run SC first: {e}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.postprocessor.study_cache import (
    PrerequisiteError, StudyCache, hash_study_inputs,
)
from app.postprocessor.studies.short_circuit import (
    ShortCircuitStudyResult,
    run as run_sc,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoordinationStudyResult:
    """Resultado do estudo de coordenação (v0.94)."""

    bus_id: str

    # Sugestões 50/51 multi-vendor (tupla de RelaySuggestion)
    relay_suggestions: tuple = field(default_factory=tuple)

    # Tempo total de extinção (relé pickup + breaker)
    coordination_clearing_time_ms: float = 0.0
    effective_clearing_time_ms: float = 0.0

    # AFD detection (reduz tempo p/ ~10 ms)
    has_AFD: bool = False

    # Quem é a fonte da SC (referência)
    sc_input_Ik_pp_kA: float = 0.0
    sc_input_kappa: float = 0.0

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
    multi_vendor_suggestions: bool = False,
    load_S_MVA: Optional[float] = None,
    auto_run_prereqs: bool = True,
) -> CoordinationStudyResult:
    """
    Executa estudo de coordenação para ``bus_id``.

    **REQUIRES SC** — usa SC do cache. Se cache vazio:

    * ``auto_run_prereqs=True`` (default) → roda SC e cacheia.
    * ``auto_run_prereqs=False`` → :class:`PrerequisiteError`.

    Returns
    -------
    CoordinationStudyResult
    """
    from app.postprocessor.bus_pipeline import BusPipelineConfig

    if config is None:
        config = BusPipelineConfig()

    # Cache hit?
    if cache is not None:
        h = hash_study_inputs(
            project, bus_id,
            (
                "coord", config, coordination_clearing_time_ms,
                multi_vendor_suggestions, load_S_MVA,
            ),
        )
        cached = cache.get_coord_if_valid(bus_id, h)
        if cached is not None:
            return cached

    # Prereq: SC
    sc_result: Optional[ShortCircuitStudyResult] = None
    if cache is not None:
        sc_result = cache.get_sc(bus_id)

    if sc_result is None:
        if not auto_run_prereqs:
            raise PrerequisiteError(
                study="coordination",
                bus_id=bus_id,
                missing=["short_circuit"],
            )
        # Auto-run SC
        sc_result = run_sc(
            project, bus_id, cache=cache, config=config,
        )

    # Compute coord
    result = _compute_coordination(
        project, bus_id, sc_result, config,
        coordination_clearing_time_ms=coordination_clearing_time_ms,
        multi_vendor_suggestions=multi_vendor_suggestions,
        load_S_MVA=load_S_MVA,
    )

    # Store
    if cache is not None:
        cache.set_coord(bus_id, result, h)

    return result


# ---------------------------------------------------------------------------
# Internal: compute
# ---------------------------------------------------------------------------


def _compute_coordination(
    project, bus_id: str,
    sc_result: ShortCircuitStudyResult,
    config,
    *,
    coordination_clearing_time_ms: float,
    multi_vendor_suggestions: bool,
    load_S_MVA: Optional[float],
) -> CoordinationStudyResult:
    from app.postprocessor.bus_pipeline import (
        _bus_from_pp_component,
        effective_clearing_time_ms,
        find_bus_component,
    )

    bus_comp = find_bus_component(project, bus_id)
    if bus_comp is None:
        raise ValueError(f"BUS {bus_id!r} não encontrado.")
    bus = _bus_from_pp_component(bus_comp)

    # Sugestões de relé
    relay_suggestions: tuple = ()
    from app.postprocessor.relay_suggestions import (
        suggest_multi_relay_alternatives,
        suggest_settings_for_bus,
    )
    try:
        if multi_vendor_suggestions:
            relay_suggestions = tuple(
                suggest_multi_relay_alternatives(
                    bus, sc_result.Ik_pp_kA, load_S_MVA=load_S_MVA,
                )
            )
        else:
            relay_suggestions = (
                suggest_settings_for_bus(
                    bus, sc_result.Ik_pp_kA, load_S_MVA=load_S_MVA,
                ),
            )
    except Exception as exc:
        # Sugestões falharam — não fatal; coord continua sem
        relay_suggestions = ()

    return CoordinationStudyResult(
        bus_id=bus.bus_id,
        relay_suggestions=relay_suggestions,
        coordination_clearing_time_ms=coordination_clearing_time_ms,
        effective_clearing_time_ms=effective_clearing_time_ms(
            bus, coordination_clearing_time_ms,
        ),
        has_AFD=bus.has_AFD,
        sc_input_Ik_pp_kA=sc_result.Ik_pp_kA,
        sc_input_kappa=sc_result.kappa,
        warnings=(),
    )
