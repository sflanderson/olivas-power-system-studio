"""
app.collab.crdt — Conflict-free Replicated Data Types
(v3.0.0 Sprint A).

Foundation para real-time collab no Olivas: múltiplos engenheiros
editando o mesmo schematic concorrentemente, com convergência
garantida sem central server (peer-to-peer).

CRDTs implementados v3.0.0
============================

* :class:`LamportClock` — relógio lógico (Lamport 1978) com
  tie-break por node_id
* :class:`LWWRegister` — single value, last-write-wins
  (uso típico: bus voltage, component property)
* :class:`ORSet` — Observed-Remove Set (Shapiro et al. 2011)
  (uso típico: lista de componentes no schematic)
* :class:`CRDTOperation` — dataclass immutable de op individual
  (event sourcing para replay)

Referências
============

* **Shapiro, M. et al. (2011)** "Conflict-Free Replicated Data
  Types", INRIA Tech Report. Estabelece OR-Set (§3.3.5).
* **Lamport, L. (1978)** "Time, Clocks, and the Ordering of
  Events in a Distributed System", CACM 21(7):558-565.
* **Preguiça, N. (2018)** "Conflict-Free Replicated Data Types:
  An Overview" — survey dos algoritmos.

Anti-alucinação
================

* OR-Set semantics segue Shapiro 2011 §3.3.5: concurrent
  add+remove → add wins (não é arbitrary; é a definição formal).
* Lamport clock segue Lamport 1978 §3: ``clock = max(local, remote)``.
* LWW tie-break determinístico por (timestamp, node_id) lexico.

Limitações declaradas v3.0.0
==============================

* **Sem network transport**: CRDTs operam em memória. Sync entre
  peers exige camada de network (WebSocket/gRPC) deferred to v3.0.x.
* **Sem persistence**: state em RAM apenas; persistence via JSON
  serialization deferred to v3.0.x.
* **Sem tombstones GC**: OR-Set tombstones acumulam indefinidamente
  (memory leak em sessões longas). Compactação deferred to v3.1+.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Set, TypeVar


T = TypeVar("T")


class LamportClock:
    """
    Logical clock para ordenação total entre nodes distribuídos.

    Algorithm (Lamport 1978 §3):
    * ``tick()``: ``t = t + 1``
    * ``observe(remote_t)``: ``t = max(t, remote_t)``
    """

    def __init__(self, node_id: str, initial: int = 0) -> None:
        self.node_id = node_id
        self._t = initial

    def now(self) -> int:
        """Retorna timestamp atual (sem incrementar)."""
        return self._t

    def tick(self) -> int:
        """Incrementa e retorna novo timestamp."""
        self._t += 1
        return self._t

    def observe(self, remote_t: int) -> int:
        """
        Sincroniza com timestamp remoto:
        ``t = max(local, remote)``. Próximo tick será > remote.
        """
        if remote_t > self._t:
            self._t = remote_t
        return self._t


class LWWRegister(Generic[T]):
    """
    Single-value register com semântica Last-Write-Wins.

    Cada `set` carimba o value com (timestamp, node_id). Em
    merge, o write com **maior** (timestamp, node_id) wins.

    Uso típico no Olivas:
    * Bus.voltage_kV (set por usuário no painel de propriedades)
    * Component.position (set ao arrastar)
    * BREAKER.state (open/closed)
    """

    def __init__(
        self,
        node_id: str,
        initial_value: T,
        *,
        clock: "LamportClock | None" = None,
    ) -> None:
        self.node_id = node_id
        self._clock = clock if clock else LamportClock(node_id)
        self._value: T = initial_value
        self._timestamp = self._clock.now()
        self._origin = node_id

    @property
    def value(self) -> T:
        return self._value

    def set(self, new_value: T) -> None:
        """Atualiza value + carimba com novo timestamp."""
        self._value = new_value
        self._timestamp = self._clock.tick()
        self._origin = self.node_id

    def merge(self, other: "LWWRegister[T]") -> None:
        """
        Merge com outro register. O com (timestamp, node_id)
        maior wins.
        """
        self._clock.observe(other._timestamp)
        local_key = (self._timestamp, self._origin)
        other_key = (other._timestamp, other._origin)
        if other_key > local_key:
            self._value = other._value
            self._timestamp = other._timestamp
            self._origin = other._origin

    def state(self) -> dict:
        """Snapshot do state para serialização."""
        return {
            "value": self._value,
            "timestamp": self._timestamp,
            "origin": self._origin,
        }


@dataclass(frozen=True)
class _ORTag:
    """
    Tag única para uma adição. (node_id, sequence) única para
    cada add → permite múltiplas adds do mesmo elemento sem
    conflito.
    """

    node_id: str
    seq: int


class ORSet:
    """
    Observed-Remove Set conforme Shapiro 2011 §3.3.5.

    Semântica:
    * ``add(x)``: cria nova tag (node_id, seq); adiciona (x, tag) ao
      set de elements
    * ``remove(x)``: move TODAS as tags atuais de x para tombstone
    * ``__contains__(x)``: True se há tag de x não-tombstone

    Concurrent add+remove: a add com tag NEW (após remove) sobrevive
    porque tombstone só captura tags **observadas**.
    """

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self._seq = 0
        self._elements: Dict[Any, Set[_ORTag]] = {}
        self._tombstones: Set[tuple] = set()

    def add(self, element: Any) -> _ORTag:
        """Adiciona element com nova tag."""
        self._seq += 1
        tag = _ORTag(node_id=self.node_id, seq=self._seq)
        self._elements.setdefault(element, set()).add(tag)
        return tag

    def remove(self, element: Any) -> None:
        """
        Remove TODAS as tags atuais (observadas) de element.
        Tombstones criados; novas adds (com tags novas) não
        são afetadas.
        """
        if element not in self._elements:
            return
        tags = self._elements[element]
        for tag in tags:
            self._tombstones.add((element, tag))
        del self._elements[element]

    def __contains__(self, element: Any) -> bool:
        return element in self._elements and len(
            self._elements[element]
        ) > 0

    def __len__(self) -> int:
        return sum(
            1 for el, tags in self._elements.items() if tags
        )

    def __iter__(self):
        for el, tags in self._elements.items():
            if tags:
                yield el

    def merge(self, other: "ORSet") -> None:
        """
        Merge state-based: união dos elements (com tags), filtrada
        pelos tombstones combinados.

        Algorithm:
        1. tombstones_merged = self._tombstones ∪ other._tombstones
        2. all_elements = união de (element, tag) pairs de ambos
        3. live = all_elements − tombstones_merged
        4. self._elements = projeção de live agrupada por element
        """
        merged_tombstones = self._tombstones | other._tombstones
        all_pairs: Set[tuple] = set()
        for el, tags in self._elements.items():
            for t in tags:
                all_pairs.add((el, t))
        for el, tags in other._elements.items():
            for t in tags:
                all_pairs.add((el, t))
        live_pairs = all_pairs - merged_tombstones
        new_elements: Dict[Any, Set[_ORTag]] = {}
        for el, tag in live_pairs:
            new_elements.setdefault(el, set()).add(tag)
        self._elements = new_elements
        self._tombstones = merged_tombstones
        max_other_seq = max(
            (t.seq for tags in other._elements.values() for t in tags),
            default=0,
        )
        self._seq = max(self._seq, max_other_seq)


@dataclass(frozen=True)
class CRDTOperation:
    """
    Operação CRDT individual para event sourcing.

    Replay deste log em qualquer ordem (com seus timestamps
    Lamport) deve produzir o mesmo state final em todos os
    peers — propriedade convergence-by-design dos CRDTs.
    """

    op_type: str
    target_id: str
    value: Any
    node_id: str
    timestamp: int
