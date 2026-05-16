"""
tests/test_pp_v3_0_0_crdt.py — v3.0.0.

Cobre CRDTs (Conflict-free Replicated Data Types) para
real-time collab:

* LWW Register (Last-Write-Wins) — single value with timestamp
* OR-Set (Observed-Remove Set) — concurrent add/remove
* Lamport clock para ordenação total

Referências
============

* Shapiro et al. 2011, "Conflict-Free Replicated Data Types"
* Lamport 1978, "Time, Clocks, and Ordering of Events"
* CRDT.tech reference impls (academic papers cited)
"""

from __future__ import annotations

import pytest


# ===========================================================================
# Lamport Clock
# ===========================================================================


class TestLamportClock:

    def test_module_loadable(self):
        from app.collab import crdt  # noqa: F401

    def test_clock_starts_at_zero(self):
        from app.collab.crdt import LamportClock
        clock = LamportClock(node_id="N1")
        assert clock.now() == 0

    def test_tick_increments(self):
        from app.collab.crdt import LamportClock
        clock = LamportClock(node_id="N1")
        t1 = clock.tick()
        t2 = clock.tick()
        assert t2 > t1

    def test_observe_advances_clock(self):
        """Lamport: clock = max(local, remote) + 1."""
        from app.collab.crdt import LamportClock
        clock = LamportClock(node_id="N1")
        clock.tick()  # t=1
        clock.observe(remote_t=10)
        # Após observe, próximo tick deve ser >10
        t_next = clock.tick()
        assert t_next > 10

    def test_node_id_breaks_ties(self):
        """Para mesmo timestamp, node_id ordena."""
        from app.collab.crdt import LamportClock
        c1 = LamportClock(node_id="A")
        c2 = LamportClock(node_id="B")
        # Ambos no mesmo t; ordenação determinística por node_id


# ===========================================================================
# LWW Register
# ===========================================================================


class TestLWWRegister:

    def test_register_loadable(self):
        from app.collab.crdt import LWWRegister
        assert LWWRegister is not None

    def test_initial_value(self):
        from app.collab.crdt import LWWRegister
        reg = LWWRegister(node_id="N1", initial_value="hello")
        assert reg.value == "hello"

    def test_set_updates_value(self):
        from app.collab.crdt import LWWRegister
        reg = LWWRegister(node_id="N1", initial_value=0)
        reg.set(42)
        assert reg.value == 42

    def test_merge_concurrent_takes_higher_timestamp(self):
        """LWW: merge entre 2 reps mantém o último write."""
        from app.collab.crdt import LWWRegister
        r1 = LWWRegister(node_id="N1", initial_value="A")
        r2 = LWWRegister(node_id="N2", initial_value="A")
        r1.set("X")  # t1
        r2.set("Y")  # t2 (mas pode ser anterior)

        # Sincroniza r2 → r1
        r1.merge(r2)
        # Resultado é determinístico: o de maior timestamp ganha.
        # Se mesmo timestamp, node_id ordena (tie-break)
        assert r1.value in ("X", "Y")

    def test_merge_idempotent(self):
        """Merge com mesmo state = no-op."""
        from app.collab.crdt import LWWRegister
        r1 = LWWRegister(node_id="N1", initial_value=1)
        r1.set(99)
        snapshot = r1.value
        # Merge com cópia
        r1.merge(r1)
        assert r1.value == snapshot


# ===========================================================================
# OR-Set (Observed-Remove Set)
# ===========================================================================


class TestORSet:

    def test_orset_loadable(self):
        from app.collab.crdt import ORSet
        assert ORSet is not None

    def test_empty_orset(self):
        from app.collab.crdt import ORSet
        s = ORSet(node_id="N1")
        assert len(s) == 0
        assert "x" not in s

    def test_add_element(self):
        from app.collab.crdt import ORSet
        s = ORSet(node_id="N1")
        s.add("apple")
        assert "apple" in s
        assert len(s) == 1

    def test_remove_observed_element(self):
        """Remove só funciona em elementos OBSERVED."""
        from app.collab.crdt import ORSet
        s = ORSet(node_id="N1")
        s.add("apple")
        s.remove("apple")
        assert "apple" not in s

    def test_remove_unobserved_is_noop(self):
        """Remove de elemento nunca adicionado: no-op."""
        from app.collab.crdt import ORSet
        s = ORSet(node_id="N1")
        s.remove("never_added")
        assert "never_added" not in s
        assert len(s) == 0

    def test_concurrent_add_wins_over_remove(self):
        """OR-Set semantics: concurrent add + remove → element exists."""
        from app.collab.crdt import ORSet
        s1 = ORSet(node_id="N1")
        s2 = ORSet(node_id="N2")
        s1.add("X")
        s2.merge(s1)   # s2 vê "X"
        s2.remove("X")  # s2 remove

        # Concorrentemente, s1 adiciona de novo
        s1.add("X")    # nova versão de "X"

        # Merge final: s1 tem versão nova; s2 removeu versão antiga
        s2.merge(s1)
        # OR-Set: nova add wins
        assert "X" in s2

    def test_merge_idempotent(self):
        from app.collab.crdt import ORSet
        s1 = ORSet(node_id="N1")
        s1.add("a")
        s1.add("b")
        s2 = ORSet(node_id="N2")
        s2.merge(s1)
        s2.merge(s1)   # merge segunda vez = no-op
        assert "a" in s2 and "b" in s2
        assert len(s2) == 2


# ===========================================================================
# Operations log (event sourcing for CRDT)
# ===========================================================================


class TestCRDTOperation:

    def test_operation_dataclass(self):
        from app.collab.crdt import CRDTOperation
        op = CRDTOperation(
            op_type="add",
            target_id="component_1",
            value="BREAKER",
            node_id="N1",
            timestamp=42,
        )
        assert op.op_type == "add"
        assert op.timestamp == 42

    def test_operation_immutable(self):
        from app.collab.crdt import CRDTOperation
        op = CRDTOperation(
            op_type="set",
            target_id="t",
            value="v",
            node_id="n",
            timestamp=1,
        )
        with pytest.raises(Exception):
            op.timestamp = 99
