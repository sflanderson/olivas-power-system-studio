"""
tests/test_pp_v1_7_0_bus_energization.py — v1.7.0 Sprint B.

Cobre o módulo ``app.postprocessor.bus_energization``:

* Detecção live (conectado a fonte via switches fechados)
* Detecção dead (chave/disjuntor aberto no caminho)
* Sem fonte = dead
* Algoritmo BFS robusto a ciclos
"""

from __future__ import annotations

import pytest


class TestBusEnergization:

    def test_module_loadable(self):
        from app.postprocessor import bus_energization  # noqa: F401

    def test_busenergization_state_enum(self):
        from app.postprocessor.bus_energization import BusState
        assert BusState.LIVE.value == "live"
        assert BusState.DEAD.value == "dead"
        assert BusState.UNKNOWN.value == "unknown"

    def test_compute_with_no_components(self):
        """Sistema vazio: nenhum bus está live."""
        from app.postprocessor.bus_energization import (
            compute_energization,
        )
        result = compute_energization(components=[], wires=[])
        assert result == {}


class TestSimpleSourceToBus:
    """
    Topologia: SOURCE — BUS
    Esperado: BUS = live
    """

    def test_direct_connection_makes_bus_live(self):
        from app.postprocessor.bus_energization import (
            BusState, compute_energization,
        )
        components = [
            {"id": "S1", "type": "Iac", "is_source": True},
            {"id": "B1", "type": "BUS", "is_source": False},
        ]
        wires = [
            {"from": "S1", "to": "B1"},
        ]
        result = compute_energization(
            components=components, wires=wires,
        )
        assert result["B1"] == BusState.LIVE


class TestBreakerOpenIsolatesBus:
    """
    Topologia: SOURCE — BREAKER (open) — BUS
    Esperado: BUS = dead (breaker quebra o caminho)
    """

    def test_open_breaker_isolates_downstream_bus(self):
        from app.postprocessor.bus_energization import (
            BusState, compute_energization,
        )
        components = [
            {"id": "S1", "type": "Iac", "is_source": True},
            {"id": "Q1", "type": "BREAKER",
             "is_source": False, "is_open": True},
            {"id": "B1", "type": "BUS", "is_source": False},
        ]
        wires = [
            {"from": "S1", "to": "Q1"},
            {"from": "Q1", "to": "B1"},
        ]
        result = compute_energization(
            components=components, wires=wires,
        )
        assert result["B1"] == BusState.DEAD

    def test_closed_breaker_propagates(self):
        from app.postprocessor.bus_energization import (
            BusState, compute_energization,
        )
        components = [
            {"id": "S1", "type": "Iac", "is_source": True},
            {"id": "Q1", "type": "BREAKER",
             "is_source": False, "is_open": False},
            {"id": "B1", "type": "BUS", "is_source": False},
        ]
        wires = [
            {"from": "S1", "to": "Q1"},
            {"from": "Q1", "to": "B1"},
        ]
        result = compute_energization(
            components=components, wires=wires,
        )
        assert result["B1"] == BusState.LIVE


class TestBusWithoutSource:
    """
    Topologia: BUS — BUS (sem fonte)
    Esperado: ambos dead
    """

    def test_no_source_makes_all_dead(self):
        from app.postprocessor.bus_energization import (
            BusState, compute_energization,
        )
        components = [
            {"id": "B1", "type": "BUS", "is_source": False},
            {"id": "B2", "type": "BUS", "is_source": False},
        ]
        wires = [
            {"from": "B1", "to": "B2"},
        ]
        result = compute_energization(
            components=components, wires=wires,
        )
        assert result["B1"] == BusState.DEAD
        assert result["B2"] == BusState.DEAD


class TestMultiBranch:
    """
    Topologia:
        SOURCE — BUS1 — BREAKER (closed) — BUS2
                  |
                  L— BREAKER (open) — BUS3

    Esperado: BUS1 live, BUS2 live, BUS3 dead.
    """

    def test_partial_isolation(self):
        from app.postprocessor.bus_energization import (
            BusState, compute_energization,
        )
        components = [
            {"id": "S1", "type": "Iac", "is_source": True},
            {"id": "B1", "type": "BUS", "is_source": False},
            {"id": "Q1", "type": "BREAKER",
             "is_source": False, "is_open": False},
            {"id": "B2", "type": "BUS", "is_source": False},
            {"id": "Q2", "type": "BREAKER",
             "is_source": False, "is_open": True},
            {"id": "B3", "type": "BUS", "is_source": False},
        ]
        wires = [
            {"from": "S1", "to": "B1"},
            {"from": "B1", "to": "Q1"},
            {"from": "Q1", "to": "B2"},
            {"from": "B1", "to": "Q2"},
            {"from": "Q2", "to": "B3"},
        ]
        result = compute_energization(
            components=components, wires=wires,
        )
        assert result["B1"] == BusState.LIVE
        assert result["B2"] == BusState.LIVE
        assert result["B3"] == BusState.DEAD


class TestEnergizationAnnotationBuilder:
    """v1.7.0 Sprint B — annotation builder for online overlay."""

    def test_live_returns_ok_severity(self):
        from app.gui.schematic_pp.online_overlay import (
            annotation_from_energization,
        )
        from app.postprocessor.bus_energization import BusState
        ann = annotation_from_energization(BusState.LIVE)
        assert ann.severity == "ok"
        assert "Energizado" in ann.lines[0] or "Energizado" in str(ann.lines)

    def test_dead_returns_violation_severity(self):
        """Severity 'violation' = vermelho — paridade PTW Out-of-Service."""
        from app.gui.schematic_pp.online_overlay import (
            annotation_from_energization,
        )
        from app.postprocessor.bus_energization import BusState
        ann = annotation_from_energization(BusState.DEAD)
        assert ann.severity == "violation"
        assert "Desenergizado" in ann.lines[0]

    def test_unknown_returns_warn_severity(self):
        from app.gui.schematic_pp.online_overlay import (
            annotation_from_energization,
        )
        from app.postprocessor.bus_energization import BusState
        ann = annotation_from_energization(BusState.UNKNOWN)
        assert ann.severity == "warn"


class TestCycleRobustness:
    """Algoritmo BFS deve sair de ciclos sem infinite loop."""

    def test_handles_cycle_without_infinite_loop(self):
        from app.postprocessor.bus_energization import (
            BusState, compute_energization,
        )
        components = [
            {"id": "S1", "type": "Iac", "is_source": True},
            {"id": "B1", "type": "BUS", "is_source": False},
            {"id": "B2", "type": "BUS", "is_source": False},
        ]
        wires = [
            {"from": "S1", "to": "B1"},
            {"from": "B1", "to": "B2"},
            {"from": "B2", "to": "B1"},   # ciclo
        ]
        result = compute_energization(
            components=components, wires=wires,
        )
        assert result["B1"] == BusState.LIVE
        assert result["B2"] == BusState.LIVE
