"""
app.postprocessor.bus_energization — Detecção de bus
energizado (live) vs desenergizado (dead) (v1.7.0 Sprint B).

Algoritmo
=========

BFS a partir de cada fonte (Iac / Idc / Vrect / qualquer
componente com ``is_source=True``). Propaga "live" através de:

* Wires (sempre conduzem)
* Componentes passivos (BUS, CABLE, R, L, C, TR, etc) — sempre
  conduzem
* BREAKER, FUSE, CONTACTOR, switch — **só conduzem se NÃO open**

Buses que não recebem propagação ficam em estado **dead**.

Isso modela a realidade física: um BUS isolado (por disjuntor/
chave aberta) está desenergizado e deve aparecer **vermelho** no
modo Online (paridade PTW "Out of Service").

API
====

::

    from app.postprocessor.bus_energization import (
        compute_energization, BusState,
    )

    components = [{"id": "S1", "type": "Iac", "is_source": True}, ...]
    wires = [{"from": "S1", "to": "B1"}, ...]
    states = compute_energization(components=components, wires=wires)
    # {"B1": BusState.LIVE, "B2": BusState.DEAD, ...}

Os argumentos `components` e `wires` aceitam dicts simples (para
testabilidade) ou objetos com atributos correspondentes (para
integração com PpComponent/Wire reais).
"""

from __future__ import annotations

from collections import defaultdict, deque
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set


# Tipos de componentes que **interrompem propagação** quando abertos.
_INTERRUPTOR_TYPES = frozenset({
    "BREAKER", "VCB", "VCB3", "FUSE", "CONTACTOR",
    "SWITCH", "SW", "DISC", "DISCONNECTOR",
})


# Tipos identificáveis como FONTES por nome
# (caso `is_source` não esteja explícito)
_SOURCE_TYPE_FALLBACK = frozenset({
    "Iac", "Idc", "Vrect", "VAC", "VDC", "Source",
    "GENERATOR", "GEN", "UTILITY",
})


class BusState(str, Enum):
    """Estado de energização de um BUS."""
    LIVE = "live"     # Conectado a fonte via caminho fechado
    DEAD = "dead"     # Isolado (sem fonte ou todos breakers abertos)
    UNKNOWN = "unknown"   # Não pôde ser determinado


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(obj: Any, key: str, default=None):
    """Pega atributo OU chave do dict (compat dual)."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _is_source(comp: Any) -> bool:
    """True se componente é fonte (explicit ou pelo nome do tipo)."""
    if _get(comp, "is_source", False):
        return True
    ctype = _get(comp, "type", "")
    return ctype in _SOURCE_TYPE_FALLBACK


def _is_open_interruptor(comp: Any) -> bool:
    """True se componente é interruptor (breaker/fuse/etc.) aberto."""
    ctype = _get(comp, "type", "")
    if ctype not in _INTERRUPTOR_TYPES:
        return False
    return bool(_get(comp, "is_open", False))


def _component_id(comp: Any) -> str:
    return str(_get(comp, "id", "") or _get(comp, "name", ""))


def _component_type(comp: Any) -> str:
    return str(_get(comp, "type", ""))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def compute_energization(
    *,
    components: Sequence[Any],
    wires: Sequence[Any],
) -> Dict[str, BusState]:
    """
    Para cada componente, retorna BusState (live/dead/unknown).

    Usa BFS a partir das fontes. Componentes interruptores
    (BREAKER/FUSE/etc) com ``is_open=True`` quebram a propagação.

    Parameters
    ----------
    components:
        Lista de componentes com pelo menos:
        ``id``, ``type``, ``is_source`` (bool), ``is_open`` (bool,
        para interruptores).
    wires:
        Lista de wires com ``from`` e ``to`` (component IDs).

    Returns
    -------
    dict[str, BusState]
        Mapeamento ``component_id → state`` para TODOS os
        componentes (não só BUSes).
    """
    by_id: Dict[str, Any] = {
        _component_id(c): c for c in components
    }
    if not by_id:
        return {}

    # Build adjacency
    adj: Dict[str, Set[str]] = defaultdict(set)
    for w in wires:
        a = str(_get(w, "from", "") or "")
        b = str(_get(w, "to", "") or "")
        if a and b and a in by_id and b in by_id:
            adj[a].add(b)
            adj[b].add(a)

    # BFS a partir de cada fonte
    live: Set[str] = set()
    queue: deque = deque()
    for cid, comp in by_id.items():
        if _is_source(comp):
            live.add(cid)
            queue.append(cid)

    while queue:
        current = queue.popleft()
        # Se current é interruptor aberto, NÃO propaga além dele
        # (ele próprio fica live só do lado da fonte)
        if _is_open_interruptor(by_id[current]):
            continue
        for neighbor in adj[current]:
            if neighbor in live:
                continue
            # neighbor é alcançado — fica live
            live.add(neighbor)
            queue.append(neighbor)

    # Construir resultado
    states: Dict[str, BusState] = {}
    for cid, comp in by_id.items():
        if cid in live:
            states[cid] = BusState.LIVE
        else:
            states[cid] = BusState.DEAD

    return states


# ---------------------------------------------------------------------------
# Helpers para integração com PpProject (estrutura real do Olivas)
# ---------------------------------------------------------------------------


def compute_energization_for_pp_project(
    pp_project: Any,
) -> Dict[str, BusState]:
    """
    Wrapper para integrar com :class:`PpProject` real.

    Extrai components + wires do project e chama
    :func:`compute_energization`. Lê propriedades específicas para
    determinar `is_source` e `is_open` baseado no spec/properties
    de cada componente.

    Lookup de property por nome (cirúrgico, sem assumptions
    estruturais que podem quebrar):

    * Para `is_source`: True se ``component.type`` está em
      ``_SOURCE_TYPE_FALLBACK`` (heurística simples)
    * Para `is_open`: True se ``component.type`` está em
      ``_INTERRUPTOR_TYPES`` E há property "state"="open" OR
      property name contém "open"="true"
    """
    components_arg = []
    wires_arg = []

    for comp in getattr(pp_project, "components", []) or []:
        ctype = getattr(comp, "type", "") or ""
        cname = getattr(comp, "name", "") or ""
        is_source = ctype in _SOURCE_TYPE_FALLBACK
        is_open = False
        # Detecta state=open via properties
        if ctype in _INTERRUPTOR_TYPES:
            for p_spec, p_val in zip(
                getattr(comp, "_spec_properties", []) or [],
                getattr(comp, "properties", []) or [],
            ):
                pname = (
                    str(getattr(p_spec, "name", "")).lower()
                    if p_spec else ""
                )
                pval = str(getattr(p_val, "value", "")).lower()
                if pname in ("state", "status") and pval in ("open", "off", "1"):
                    is_open = True
                    break
        components_arg.append({
            "id": cname or ctype,
            "type": ctype,
            "is_source": is_source,
            "is_open": is_open,
        })

    # Wires: precisam de from/to com IDs de componentes.
    # Estrutura PpProject pode usar pin endpoints; aqui assumimos
    # que ``wire.start_component_name`` e ``end_component_name``
    # estão disponíveis (graceful fallback se não).
    for w in getattr(pp_project, "wires", []) or []:
        a = (
            getattr(w, "start_component_name", "")
            or getattr(w, "from_component", "")
        )
        b = (
            getattr(w, "end_component_name", "")
            or getattr(w, "to_component", "")
        )
        if a and b:
            wires_arg.append({"from": a, "to": b})

    return compute_energization(
        components=components_arg, wires=wires_arg,
    )
