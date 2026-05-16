"""
app/postprocessor/mis_coordination.py — Mis-coordination detection.

Implementa PTW Tutorial §Part 5 p. 144-145:

* Cleared Fault Threshold (default 80%)
* Mis-Coordination Ratio
* Upstream Search (Levels to Search)
* Conditions 1 & 2 do mis-coord check

Aplicação: detectar problemas de coordenação onde backup operates
before/concurrently with main, levando a desligamentos amplos
desnecessários (arc-flash pode "explodir" o bus inteiro).

Reference
---------
PTW Tutorial §Part 5 p. 144-145.
IEEE Std 242 (Buff Book) §15 (coordination).
"""

from __future__ import annotations

from typing import Mapping


# §Tutorial Part 5 p. 144 — default values.
DEFAULT_CLEARED_FAULT_THRESHOLD: float = 0.80
DEFAULT_LEVELS_TO_SEARCH: int = 3
DEFAULT_MIS_COORDINATION_RATIO: float = 1.0


def is_main_cleared(
    i_main_kA: float,
    i_total_kA: float,
    threshold: float = DEFAULT_CLEARED_FAULT_THRESHOLD,
) -> bool:
    """Determine if the main protection device clears the fault.

    Per PTW Tutorial §Part 5 p. 144-145 (Cleared Fault Threshold):
    se a corrente que **passa pelo main** representa ≥ ``threshold``
    (default 80%) da corrente total da falta, considera-se que o main
    é capaz de "limpar" a falta. Caso contrário, há contribuição
    significativa "by-passing" (ex: motores no bus alimentando da fault),
    e a coordenação backup é necessária.

    Parameters
    ----------
    i_main_kA
        Corrente fluindo pelo main protection device, kA.
    i_total_kA
        Corrente total na fault, kA.
    threshold
        Threshold ∈ [0, 1] para considerar "cleared". Default 0.80.

    Returns
    -------
    bool
        True iff i_main / i_total >= threshold.

    References
    ----------
    PTW Tutorial §Part 5 p. 144-145.
    """
    if i_main_kA < 0 or i_total_kA < 0:
        raise ValueError("Currents must be ≥ 0")
    if i_total_kA == 0:
        return True  # Vacuously cleared (no fault)
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(
            f"threshold must be ∈ [0, 1]; got {threshold!r}"
        )
    return (i_main_kA / i_total_kA) >= threshold


def mis_coordination_ratio(
    t_main_trip_s: float,
    t_backup_trip_s: float,
) -> float:
    """Compute mis-coordination ratio = t_main / t_backup.

    Per PTW Tutorial §Part 5 p. 144-145:

    * **Ratio < 1.0** — main trips first → coordinated (good)
    * **Ratio = 1.0** — simultaneous trip (borderline)
    * **Ratio > 1.0** — backup trips first → mis-coordination (bad)

    Em mis-coordination, o backup desliga o bus antes do main, causando
    desligamentos amplos desnecessários e potencialmente aumentando
    arc-flash incident energy (mais devices desligando contribuem para
    accumulated energy).

    Parameters
    ----------
    t_main_trip_s, t_backup_trip_s
        Trip times do main e backup devices, em segundos. Backup deve
        ser > 0.

    Returns
    -------
    float
        Mis-coord ratio.

    References
    ----------
    PTW Tutorial §Part 5 p. 144-145.
    IEEE Std 242 (Buff Book) §15.
    """
    if t_main_trip_s < 0 or t_backup_trip_s < 0:
        raise ValueError("Trip times must be ≥ 0")
    if t_backup_trip_s == 0:
        raise ValueError("t_backup_trip_s must be > 0 (else division by zero)")
    return t_main_trip_s / t_backup_trip_s


def upstream_search(
    start_device: str,
    topology: Mapping[str, str | None],
    max_levels: int = DEFAULT_LEVELS_TO_SEARCH,
) -> list[str]:
    """Walk the upstream chain from a device, up to max_levels.

    Per PTW Tutorial §Part 5 p. 145 (Levels to Search): para cada
    device, busca os próximos N upstream devices na cadeia de
    proteção, retornando a lista (mais próximo primeiro).

    Útil para verificar mis-coordination em múltiplos níveis (ex:
    feeder → main → utility breaker).

    Parameters
    ----------
    start_device
        Device de onde iniciar a busca.
    topology
        Mapeamento ``{device: upstream_device or None}``.
    max_levels
        Quantidade máxima de levels a percorrer (default 3).

    Returns
    -------
    list[str]
        Lista dos upstream devices, ordem mais-próximo → mais-distante.
        Vazia se ``start_device`` não tem upstream.

    References
    ----------
    PTW Tutorial §Part 5 p. 145.
    """
    if max_levels < 0:
        raise ValueError(f"max_levels must be ≥ 0; got {max_levels!r}")
    upstream_chain: list[str] = []
    current = start_device
    for _ in range(max_levels):
        next_upstream = topology.get(current)
        if next_upstream is None:
            break
        upstream_chain.append(next_upstream)
        current = next_upstream
    return upstream_chain


__all__ = [
    "DEFAULT_CLEARED_FAULT_THRESHOLD",
    "DEFAULT_LEVELS_TO_SEARCH",
    "DEFAULT_MIS_COORDINATION_RATIO",
    "is_main_cleared",
    "mis_coordination_ratio",
    "upstream_search",
]
