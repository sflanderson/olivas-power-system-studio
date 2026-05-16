"""
app.postprocessor.study_cache — cache de resultados de
estudos elétricos (v0.94.0).

Filosofia
==========

PTW Power*Tools / ETAP / EasyPower implementam estudos
**modulares** com **encadeamento de pré-requisitos**:

* **Short-Circuit (SC)** — standalone (sem prereqs)
* **Coordenação e Seletividade** — REQUIRES SC
* **Arc-Flash / Energia incidente** — REQUIRES SC + COORD
* **Motor Starting** — usa PF como entrada opcional
* **CT Saturation** — usa SC + Coord como entrada

Sem cache, cada chamada recomputaria os pré-requisitos. Em
sistemas reais (50+ buses, ~30 min total), isso é proibitivo.
PTW resolve com **cache por bus + invalidação por SHA256**:

* Resultados gravados por ``(study_kind, bus_id)``
* Chave inclui SHA256 dos inputs (config + topologia +
  parâmetros do bus). Mudança em qualquer entrada invalida.
* Acesso O(1) via dict.

API
====

::

    cache = StudyCache(project)
    sc = cache.get_or_compute_sc("BUS-MAIN", config)
    coord = cache.get_or_compute_coord("BUS-MAIN", config)
    af = cache.get_or_compute_arc_flash("BUS-MAIN", config)

    # Ou check explícito de prereqs:
    if not cache.has_sc("BUS-MAIN"):
        raise PrerequisiteError("Run SC first")

Invalidação:

* ``cache.invalidate_bus("BUS-X")`` — todas as análises de
  um bus.
* ``cache.invalidate_all()`` — full reset (usuário mudou
  topologia substancialmente).
* Auto-invalidação por hash mismatch — silenciosa, recomputa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.postprocessor.audit_trail import compute_input_checksum


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------


# Result types (forward declarations) — evitam imports circulares.
# Cada estudo retorna seu próprio dataclass do módulo dedicado.

# Sentinela para resultados ainda não computados.
_UNSET = object()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PrerequisiteError(Exception):
    """
    Raised quando um estudo é solicitado sem seu(s)
    pré-requisito(s) computado(s) e o caller pediu modo
    estrito (sem auto-run).
    """

    def __init__(
        self,
        study: str,
        bus_id: str,
        missing: list[str],
    ) -> None:
        self.study = study
        self.bus_id = bus_id
        self.missing = missing
        super().__init__(
            f"Pré-requisitos faltando para {study} em {bus_id!r}: "
            f"{', '.join(missing)}. Execute-os antes ou use "
            f"`auto_run=True`."
        )


# ---------------------------------------------------------------------------
# Cache entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CacheEntry:
    """
    Entrada genérica no cache: o resultado + o hash do input
    que o produziu. Permite invalidação silenciosa quando
    inputs mudam.
    """

    result: Any
    input_hash: str

    def is_valid_for(self, current_hash: str) -> bool:
        return self.input_hash == current_hash


# ---------------------------------------------------------------------------
# Study cache
# ---------------------------------------------------------------------------


@dataclass
class StudyCache:
    """
    Cache de resultados de estudos por bus_id.

    O cache vive associado a um ``PpProject`` específico (1
    cache por projeto aberto). Cada estudo tem seu próprio
    dict; chaves são ``bus_id``; valores são :class:`CacheEntry`
    contendo result + hash dos inputs.

    Invalidação automática: ao buscar um resultado, o cache
    compara o hash atual dos inputs com o hash gravado. Se
    mudou, retorna ``None`` (forçando recomputação).
    """

    # Cache por estudo, por bus
    _sc: dict[str, CacheEntry] = field(default_factory=dict)
    _coord: dict[str, CacheEntry] = field(default_factory=dict)
    _arc_flash: dict[str, CacheEntry] = field(default_factory=dict)
    _power_flow: Optional[CacheEntry] = None    # 1 PF por projeto
    _motor_starting: dict[str, CacheEntry] = field(default_factory=dict)
    _ct_saturation: dict[str, CacheEntry] = field(default_factory=dict)

    # ---- SC (standalone) ---------------------------------------------------

    def has_sc(self, bus_id: str) -> bool:
        return bus_id in self._sc

    def get_sc(self, bus_id: str) -> Optional[Any]:
        entry = self._sc.get(bus_id)
        return entry.result if entry is not None else None

    def get_sc_if_valid(
        self, bus_id: str, current_hash: str,
    ) -> Optional[Any]:
        entry = self._sc.get(bus_id)
        if entry is None or not entry.is_valid_for(current_hash):
            return None
        return entry.result

    def set_sc(self, bus_id: str, result: Any, input_hash: str) -> None:
        self._sc[bus_id] = CacheEntry(result=result, input_hash=input_hash)
        # Invalida estudos derivados pois SC mudou
        self._coord.pop(bus_id, None)
        self._arc_flash.pop(bus_id, None)

    # ---- Coordenação (REQUIRES SC) -----------------------------------------

    def has_coord(self, bus_id: str) -> bool:
        return bus_id in self._coord

    def get_coord(self, bus_id: str) -> Optional[Any]:
        entry = self._coord.get(bus_id)
        return entry.result if entry is not None else None

    def get_coord_if_valid(
        self, bus_id: str, current_hash: str,
    ) -> Optional[Any]:
        entry = self._coord.get(bus_id)
        if entry is None or not entry.is_valid_for(current_hash):
            return None
        return entry.result

    def set_coord(
        self, bus_id: str, result: Any, input_hash: str,
    ) -> None:
        self._coord[bus_id] = CacheEntry(
            result=result, input_hash=input_hash,
        )
        # Invalida arc-flash derivado
        self._arc_flash.pop(bus_id, None)

    # ---- Arc-flash (REQUIRES SC + COORD) -----------------------------------

    def has_arc_flash(self, bus_id: str) -> bool:
        return bus_id in self._arc_flash

    def get_arc_flash(self, bus_id: str) -> Optional[Any]:
        entry = self._arc_flash.get(bus_id)
        return entry.result if entry is not None else None

    def get_arc_flash_if_valid(
        self, bus_id: str, current_hash: str,
    ) -> Optional[Any]:
        entry = self._arc_flash.get(bus_id)
        if entry is None or not entry.is_valid_for(current_hash):
            return None
        return entry.result

    def set_arc_flash(
        self, bus_id: str, result: Any, input_hash: str,
    ) -> None:
        self._arc_flash[bus_id] = CacheEntry(
            result=result, input_hash=input_hash,
        )

    # ---- Power Flow (project-level, 1 PF) -----------------------------------

    def has_pf(self) -> bool:
        return self._power_flow is not None

    def get_pf(self) -> Optional[Any]:
        return self._power_flow.result if self._power_flow else None

    def get_pf_if_valid(self, current_hash: str) -> Optional[Any]:
        if (
            self._power_flow is None
            or not self._power_flow.is_valid_for(current_hash)
        ):
            return None
        return self._power_flow.result

    def set_pf(self, result: Any, input_hash: str) -> None:
        self._power_flow = CacheEntry(result=result, input_hash=input_hash)

    # ---- Motor Starting -----------------------------------------------------

    def has_motor_starting(self, motor_id: str) -> bool:
        return motor_id in self._motor_starting

    def get_motor_starting(self, motor_id: str) -> Optional[Any]:
        entry = self._motor_starting.get(motor_id)
        return entry.result if entry is not None else None

    def set_motor_starting(
        self, motor_id: str, result: Any, input_hash: str,
    ) -> None:
        self._motor_starting[motor_id] = CacheEntry(
            result=result, input_hash=input_hash,
        )

    # ---- CT Saturation (REQUIRES SC + Coord) ------------------------------

    def has_ct_saturation(self, ct_tag: str) -> bool:
        return ct_tag in self._ct_saturation

    def get_ct_saturation(self, ct_tag: str) -> Optional[Any]:
        entry = self._ct_saturation.get(ct_tag)
        return entry.result if entry is not None else None

    def set_ct_saturation(
        self, ct_tag: str, result: Any, input_hash: str,
    ) -> None:
        self._ct_saturation[ct_tag] = CacheEntry(
            result=result, input_hash=input_hash,
        )

    # ---- Invalidação --------------------------------------------------------

    def invalidate_bus(self, bus_id: str) -> None:
        """Remove TODOS os estudos cacheados para um bus."""
        self._sc.pop(bus_id, None)
        self._coord.pop(bus_id, None)
        self._arc_flash.pop(bus_id, None)
        self._motor_starting.pop(bus_id, None)
        self._ct_saturation.pop(bus_id, None)

    def invalidate_all(self) -> None:
        """Reset total."""
        self._sc.clear()
        self._coord.clear()
        self._arc_flash.clear()
        self._power_flow = None
        self._motor_starting.clear()
        self._ct_saturation.clear()

    # ---- Status (UI) --------------------------------------------------------

    def status_summary(self, bus_id: str) -> dict[str, str]:
        """
        Retorna ``{study: status_emoji}`` para o status bar
        da UI. Status:

        * "✅" — computado e cacheado
        * "—" — não computado
        """
        return {
            "sc": "✅" if self.has_sc(bus_id) else "—",
            "coord": "✅" if self.has_coord(bus_id) else "—",
            "arc_flash": "✅" if self.has_arc_flash(bus_id) else "—",
        }


# ---------------------------------------------------------------------------
# Helper: hash dos inputs comum a todos os estudos
# ---------------------------------------------------------------------------


def hash_study_inputs(
    project, bus_id: str, config: Any,
) -> str:
    """
    Calcula SHA256 estável dos inputs de um estudo:
    project (componentes + wires + propriedades) +
    bus_id + config.

    Reusa :func:`compute_input_checksum` do audit_trail —
    consistência com os hashes que aparecem no laudo.
    """
    payload = {
        "project_components": [
            {
                "type": c.type, "name": c.name,
                "x": c.x, "y": c.y,
                "rotation": c.rotation, "mirror": c.mirror,
                "props": [(p.value, p.visible) for p in c.properties],
            }
            for c in project.components
        ],
        "project_wires": [
            (w.x1, w.y1, w.x2, w.y2, w.label)
            for w in project.wires
        ],
        "bus_id": bus_id,
        "config": config,
    }
    return compute_input_checksum(payload)
