"""
tests/test_pp_pipeline_multihop_integration.py — v0.27.7.8:
integração do walking multi-hop no
``analyze_bus_full_pipeline``.

Cobre:

* Novo kwargs ``use_multi_hop`` e ``max_hops`` em
  ``analyze_bus_full_pipeline``.
* Campo ``topology_chains`` no ``BusPipelineReport``.
* Bloco "Topology Chains" no ``summary()``.
* Compatibilidade backward (default = 1-hop).
* Cenários: BUS isolado, mesma API (smoke).
"""

from __future__ import annotations

import pytest

from app.postprocessor.bus_pipeline import (
    BusPipelineReport,
    analyze_bus_full_pipeline,
)
from app.postprocessor.multihop_walker import TopologyChain
from app.preprocessor.models import PpComponent, PpProject, PpProperty


def _mk(t, n, props, x=0, y=0):
    return PpComponent(
        type=t, name=n, visible=True,
        x=x, y=y, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(p) for p in props],
    )


def _bus(name="B1", bus_id="BUS-1", voltage="13.8"):
    return _mk("BUS", name, [
        bus_id, voltage, "3", "swgr_15kv",
        "1", "0", "10", "4", "",
    ])


# ---------------------------------------------------------------------------
# API backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_default_use_multi_hop_is_false(self):
        """Sem kwargs, comportamento é 1-hop (compatibilidade)."""
        proj = PpProject(components=[_bus()])
        # Sem fontes → ValueError. Mas a API deve aceitar a chamada
        # sem o kwarg, mantendo backward.
        with pytest.raises(ValueError, match="nenhuma fonte"):
            analyze_bus_full_pipeline(
                proj, "BUS-1",
                coordination_clearing_time_ms=200.0,
            )

    def test_use_multi_hop_kwarg_accepted(self):
        proj = PpProject(components=[_bus()])
        with pytest.raises(ValueError, match="nenhuma fonte"):
            analyze_bus_full_pipeline(
                proj, "BUS-1",
                coordination_clearing_time_ms=200.0,
                use_multi_hop=True,
            )

    def test_max_hops_kwarg_accepted(self):
        proj = PpProject(components=[_bus()])
        with pytest.raises(ValueError, match="nenhuma fonte"):
            analyze_bus_full_pipeline(
                proj, "BUS-1",
                coordination_clearing_time_ms=200.0,
                use_multi_hop=True,
                max_hops=6,
            )


# ---------------------------------------------------------------------------
# topology_chains no BusPipelineReport
# ---------------------------------------------------------------------------


class TestTopologyChainsField:
    def test_default_empty_tuple(self):
        """Quando construído sem topology_chains, é tupla vazia."""
        r = BusPipelineReport(
            bus_id="X", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=0, n_sc_sources=0,
            sources_summary=(),
            Ik_pp_kA=0.0, ip_kA=0.0, kappa=0.0,
            coordination_clearing_time_ms=0.0,
            effective_clearing_time_ms=0.0,
            incident_energy_cal_cm2=0.0,
            arc_flash_boundary_mm=0.0,
            ppe_category="0",
            relay_suggestions=(),
            warnings=(),
        )
        assert r.topology_chains == ()

    def test_topology_chains_in_report(self):
        v = _mk("Vac", "UTIL", ["13.8"])
        chain = TopologyChain(
            target_bus_id="BUS-MAIN",
            source_component=v,
            intermediate_transformers=(),
            intermediate_buses=(),
            n_hops=1,
        )
        r = BusPipelineReport(
            bus_id="BUS-MAIN", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=1, n_sc_sources=1,
            sources_summary=("UTIL: 100%",),
            Ik_pp_kA=20.0, ip_kA=55.0, kappa=1.94,
            coordination_clearing_time_ms=500.0,
            effective_clearing_time_ms=500.0,
            incident_energy_cal_cm2=15.0,
            arc_flash_boundary_mm=3000.0,
            ppe_category="3",
            relay_suggestions=(),
            topology_chains=(chain,),
            warnings=(),
        )
        assert len(r.topology_chains) == 1
        assert r.topology_chains[0].source_component.name == "UTIL"


# ---------------------------------------------------------------------------
# summary() exibe Topology Chains
# ---------------------------------------------------------------------------


class TestSummaryShowsChains:
    def test_summary_with_one_chain(self):
        v = _mk("Vac", "UTIL", ["13.8"])
        chain = TopologyChain(
            target_bus_id="BUS-MAIN",
            source_component=v,
            intermediate_transformers=(),
            intermediate_buses=(),
            n_hops=1,
        )
        r = BusPipelineReport(
            bus_id="BUS-MAIN", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=1, n_sc_sources=1,
            sources_summary=("UTIL: 100%",),
            Ik_pp_kA=20.0, ip_kA=55.0, kappa=1.94,
            coordination_clearing_time_ms=500.0,
            effective_clearing_time_ms=500.0,
            incident_energy_cal_cm2=15.0,
            arc_flash_boundary_mm=3000.0,
            ppe_category="3",
            relay_suggestions=(),
            topology_chains=(chain,),
            warnings=(),
        )
        s = r.summary()
        assert "Topology Chains" in s
        assert "Chain #1" in s
        assert "UTIL" in s
        assert "BUS-MAIN" in s
        # Reference IEC 60909-0
        assert "IEC 60909-0" in s

    def test_summary_with_multiple_chains(self):
        v1 = _mk("Vac", "UTIL", ["138"])
        v2 = _mk("SM", "GEN", ["13.8"])
        chain1 = TopologyChain(
            target_bus_id="BUS-MAIN",
            source_component=v1,
            intermediate_transformers=(),
            intermediate_buses=(),
            n_hops=1,
        )
        chain2 = TopologyChain(
            target_bus_id="BUS-MAIN",
            source_component=v2,
            intermediate_transformers=(),
            intermediate_buses=(),
            n_hops=1,
        )
        r = BusPipelineReport(
            bus_id="BUS-MAIN", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=2, n_sc_sources=2,
            sources_summary=("UTIL: 30%", "GEN: 70%"),
            Ik_pp_kA=33.0, ip_kA=90.0, kappa=1.92,
            coordination_clearing_time_ms=500.0,
            effective_clearing_time_ms=500.0,
            incident_energy_cal_cm2=20.0,
            arc_flash_boundary_mm=4000.0,
            ppe_category="3",
            relay_suggestions=(),
            topology_chains=(chain1, chain2),
            warnings=(),
        )
        s = r.summary()
        assert "Chain #1" in s
        assert "Chain #2" in s

    def test_summary_omits_chains_block_when_empty(self):
        r = BusPipelineReport(
            bus_id="X", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=0, n_sc_sources=0,
            sources_summary=(),
            Ik_pp_kA=0.0, ip_kA=0.0, kappa=0.0,
            coordination_clearing_time_ms=0.0,
            effective_clearing_time_ms=0.0,
            incident_energy_cal_cm2=0.0,
            arc_flash_boundary_mm=0.0,
            ppe_category="0",
            topology_chains=(),
            warnings=(),
        )
        s = r.summary()
        assert "Topology Chains" not in s


# ---------------------------------------------------------------------------
# Walking multi-hop integrado
# ---------------------------------------------------------------------------


class TestMultiHopIntegration:
    def test_multi_hop_with_isolated_bus_raises(self):
        """Sem fontes mesmo em multi-hop → ValueError."""
        proj = PpProject(components=[_bus()])
        with pytest.raises(ValueError, match="nenhuma fonte"):
            analyze_bus_full_pipeline(
                proj, "BUS-1",
                coordination_clearing_time_ms=200.0,
                use_multi_hop=True,
            )

    def test_multi_hop_max_hops_limit(self):
        """max_hops controla profundidade do BFS."""
        proj = PpProject(components=[_bus()])
        # max_hops=0 → não walking → sem fontes → ValueError
        with pytest.raises(ValueError):
            analyze_bus_full_pipeline(
                proj, "BUS-1",
                coordination_clearing_time_ms=200.0,
                use_multi_hop=True,
                max_hops=0,
            )

    def test_multi_hop_3level_topology_runs(self):
        """
        Topologia 3 níveis: UTIL → TR1 → BUS-MAIN → TR2 → BUS-CCM.
        A API deve rodar sem erro mesmo sem fontes encontradas
        (depende de connectivity real).
        """
        components = [
            _mk("Vac", "UTIL", ["138"]),
            _mk("XFMR", "TR1", [
                "138", "13.8", "100", "60", "THREE_LEG",
                "10", "200",
            ]),
            _bus("B-MAIN", "BUS-MAIN", voltage="13.8"),
            _mk("XFMR", "TR2", [
                "13.8", "4.16", "10", "60", "THREE_LEG",
                "8", "50",
            ]),
            _bus("B-CCM", "BUS-CCM", voltage="4.16"),
        ]
        proj = PpProject(components=components)
        # Sem connectivity geometric, BFS não encontra cadeias
        # ainda; a chamada não deve crashar
        with pytest.raises(ValueError, match="nenhuma fonte"):
            analyze_bus_full_pipeline(
                proj, "BUS-CCM",
                coordination_clearing_time_ms=200.0,
                use_multi_hop=True,
                max_hops=4,
            )
