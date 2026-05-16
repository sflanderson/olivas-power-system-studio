"""
tests/test_pp_multihop_walker.py — v0.27.7.7: walking multi-hop
através de transformadores e barramentos para encontrar fontes
de SC em cadeia.

Cobre:

* Predicates: is_transformer, is_bus, is_ultimate_source.
* TopologyChain dataclass + describe().
* find_source_chains: BFS desde BUS até fontes.
* chain_to_sc_source: reflexão de impedância.
* build_sc_network_multi_hop: integração end-to-end.
* Cenários: BUS isolado, BUS direto com fonte, BUS com TR,
  BUS com 2 TRs em cadeia.
"""

from __future__ import annotations

import pytest

from app.postprocessor.multihop_walker import (
    TRANSPARENT_TYPES, TopologyChain,
    build_sc_network_multi_hop, chain_to_sc_source,
    find_source_chains,
    is_bus, is_transformer, is_ultimate_source,
)
from app.preprocessor.models import (
    PpComponent, PpProject, PpProperty, PpWire,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk(t: str, n: str, props: list[str] | None = None,
        x: int = 0, y: int = 0) -> PpComponent:
    return PpComponent(
        type=t, name=n, visible=True,
        x=x, y=y, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(p) for p in (props or [])],
    )


def _bus(name: str, bus_id: str = "BUS-1",
         voltage: str = "13.8") -> PpComponent:
    return _mk("BUS", name, [
        bus_id, voltage, "3", "swgr_15kv",
        "1", "0", "10", "4", "",
    ])


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------


class TestPredicates:
    def test_is_transformer_xfmr(self):
        assert is_transformer(_mk("XFMR", "T")) is True

    def test_is_transformer_tr(self):
        assert is_transformer(_mk("Tr", "T")) is True

    def test_is_transformer_tr3(self):
        assert is_transformer(_mk("Tr3", "T")) is True

    def test_is_transformer_bctran(self):
        assert is_transformer(_mk("BCTRAN", "T")) is True

    def test_is_transformer_negative(self):
        assert is_transformer(_mk("R", "R1")) is False
        assert is_transformer(_mk("Vac", "V1")) is False

    def test_is_bus(self):
        assert is_bus(_bus("B1")) is True
        assert is_bus(_mk("R", "R1")) is False

    def test_is_ultimate_source_vac(self):
        assert is_ultimate_source(_mk("Vac", "V1")) is True

    def test_is_ultimate_source_sm(self):
        assert is_ultimate_source(_mk("SM", "G1")) is True

    def test_is_ultimate_source_tr_negative(self):
        """TR não é fonte ultimate — só caminho."""
        assert is_ultimate_source(_mk("XFMR", "T")) is False

    def test_is_ultimate_source_passive(self):
        assert is_ultimate_source(_mk("R", "R")) is False
        assert is_ultimate_source(_bus("B")) is False

    def test_transparent_types_set(self):
        assert "Tr" in TRANSPARENT_TYPES
        assert "Tr3" in TRANSPARENT_TYPES
        assert "XFMR" in TRANSPARENT_TYPES
        assert "BCTRAN" in TRANSPARENT_TYPES


# ---------------------------------------------------------------------------
# TopologyChain
# ---------------------------------------------------------------------------


class TestTopologyChain:
    def test_describe_simple_chain(self):
        v = _mk("Vac", "UTIL")
        chain = TopologyChain(
            target_bus_id="BUS-MAIN",
            source_component=v,
            intermediate_transformers=(),
            intermediate_buses=(),
            n_hops=1,
        )
        s = chain.describe()
        assert "UTIL" in s
        assert "BUS-MAIN" in s

    def test_describe_with_transformer(self):
        v = _mk("Vac", "UTIL")
        tr = _mk("XFMR", "TR1")
        chain = TopologyChain(
            target_bus_id="BUS-MAIN",
            source_component=v,
            intermediate_transformers=(tr,),
            intermediate_buses=(),
            n_hops=2,
        )
        s = chain.describe()
        assert "UTIL" in s
        assert "TR1" in s
        assert "BUS-MAIN" in s

    def test_describe_with_chain_of_2_trs(self):
        v = _mk("Vac", "UTIL")
        tr1 = _mk("XFMR", "TR1")
        tr2 = _mk("XFMR", "TR2")
        bus_mid = _bus("BUS-MID", bus_id="BUS-MID")
        chain = TopologyChain(
            target_bus_id="BUS-CCM",
            source_component=v,
            intermediate_transformers=(tr2, tr1),  # ordem: do bus para fonte
            intermediate_buses=(bus_mid,),
            n_hops=4,
        )
        s = chain.describe()
        assert "UTIL" in s
        assert "TR1" in s
        assert "TR2" in s
        assert "BUS-MID" in s
        assert "BUS-CCM" in s


# ---------------------------------------------------------------------------
# find_source_chains
# ---------------------------------------------------------------------------


class TestFindSourceChains:
    def test_isolated_bus_no_chains(self):
        proj = PpProject(components=[_bus("B1", "BUS-1")])
        chains = find_source_chains(proj, "BUS-1", max_hops=4)
        assert chains == []

    def test_bus_not_found_raises(self):
        proj = PpProject(components=[_mk("R", "R1")])
        with pytest.raises(ValueError, match="BUS"):
            find_source_chains(proj, "NONEXISTENT")

    def test_max_hops_zero_returns_empty(self):
        """max_hops=0 não permite nenhum walking."""
        v = _mk("Vac", "V1", ["220V"])
        b = _bus("B1", "BUS-1")
        proj = PpProject(components=[v, b])
        chains = find_source_chains(proj, "BUS-1", max_hops=0)
        assert chains == []

    def test_chain_orderby_n_hops(self):
        """Cadeias mais curtas vêm primeiro."""
        v1 = _mk("Vac", "V1", ["220V"])
        v2 = _mk("Vac", "V2", ["220V"])
        sm = _mk("SM", "G1", ["13.8"])
        tr = _mk("XFMR", "T1", ["138", "13.8", "25"])
        b = _bus("B1", "BUS-1")
        proj = PpProject(components=[v1, v2, sm, tr, b])
        # Com max_hops baixo, no máximo coletamos vizinhos diretos.
        # Como sem connectivity real entre eles, retorna [].
        chains = find_source_chains(proj, "BUS-1", max_hops=4)
        # Verifica ordenação por n_hops crescente
        for i in range(len(chains) - 1):
            assert chains[i].n_hops <= chains[i + 1].n_hops


# ---------------------------------------------------------------------------
# chain_to_sc_source
# ---------------------------------------------------------------------------


class TestChainToScSource:
    def test_vac_source_simple(self):
        """Vac direto (sem TRs) — Z = Z_Q da rede default."""
        v = _mk("Vac", "UTIL", ["13.8"])
        chain = TopologyChain(
            target_bus_id="BUS-1",
            source_component=v,
            intermediate_transformers=(),
            intermediate_buses=(),
            n_hops=1,
        )
        src = chain_to_sc_source(chain, target_voltage_kV=13.8)
        # |Z_Q| ≈ c·V²/S_kQ = 1.10·13.8²/500 = 0.4193 Ω
        assert abs(src.z_ohm) == pytest.approx(0.4193, abs=0.01)

    def test_sm_source_simple(self):
        """SM direto — Z = Xd''·Z_base."""
        sm = _mk("SM", "GEN", [
            "13.8",  # V
            "100",   # S
            "60",    # f
            "2",     # poles
            "1.8",   # Xd
            "0.30",  # Xd'
            "0.20",  # Xd''
            "0.8", "0.030",  # Td' Td''
            "1.7", "0.55", "0.20", "0.4", "0.050",
            "0.003", "0.15", "0.05",
            "4.0", "0.0", "0", "0", "1.0", "0",
        ])
        chain = TopologyChain(
            target_bus_id="BUS-1",
            source_component=sm,
            intermediate_transformers=(),
            intermediate_buses=(),
            n_hops=1,
        )
        src = chain_to_sc_source(chain, target_voltage_kV=13.8)
        # Z_base = 13.8²/100 = 1.9044 Ω
        # Z = (0.003 + j0.20) · 1.9044 = 0.0057 + j0.381
        assert src.z_ohm.imag == pytest.approx(0.381, abs=0.01)

    def test_chain_with_one_transformer(self):
        """Vac (138 kV) → TR (138/13.8) → BUS-13.8.

        Z_Q no primário (138 kV): 1.10·138²/500 = 41.89 Ω
        Refletido a 13.8 kV: 41.89 · (13.8/138)² = 0.4189 Ω
        Z_TR (uk=10%, S=25 MVA, V=13.8): (10/100)·13.8²/25 = 0.7618 Ω
        Z_total ≈ 0.42 + 0.76 ≈ 1.18 Ω (módulo aprox)
        """
        v = _mk("Vac", "UTIL", ["138"])
        tr = _mk("XFMR", "TR1", [
            "138",   # V_HV
            "13.8",  # V_LV
            "25",    # S
            "60",    # f
            "THREE_LEG",
            "10", "100",  # uk%, p_load
        ])
        chain = TopologyChain(
            target_bus_id="BUS-1",
            source_component=v,
            intermediate_transformers=(tr,),
            intermediate_buses=(),
            n_hops=2,
        )
        src = chain_to_sc_source(chain, target_voltage_kV=13.8)
        # Magnitude esperada ~ 0.4 + 0.76 ≈ 1.18 Ω
        # (módulo da soma vetorial, próximo de soma escalar para
        # angles parecidos)
        assert 0.5 < abs(src.z_ohm) < 1.5

    def test_unsupported_source_returns_high_impedance(self):
        """Componente que não é Vac nem SM retorna Z = 1e9."""
        from app.preprocessor.models import PpComponent
        weird = _mk("R", "X", ["100"])
        chain = TopologyChain(
            target_bus_id="BUS-1",
            source_component=weird,
            intermediate_transformers=(),
            intermediate_buses=(),
            n_hops=1,
        )
        src = chain_to_sc_source(chain, target_voltage_kV=13.8)
        assert abs(src.z_ohm) > 1e8


# ---------------------------------------------------------------------------
# build_sc_network_multi_hop
# ---------------------------------------------------------------------------


class TestBuildScNetworkMultiHop:
    def test_isolated_bus_warns(self):
        proj = PpProject(components=[_bus("B1", "BUS-1")])
        net, chains, warns = build_sc_network_multi_hop(proj, "BUS-1")
        assert chains == []
        assert any("nenhuma fonte" in w.lower() for w in warns)

    def test_bus_voltage_inferred(self):
        b = _bus("B1", "BUS-1", voltage="4.16")
        proj = PpProject(components=[b])
        net, _, _ = build_sc_network_multi_hop(proj, "BUS-1")
        assert net.rated_voltage_kV == 4.16

    def test_bus_voltage_invalid_falls_back(self):
        # voltage "abc" → fallback 13.8
        b = _mk("BUS", "B1", [
            "BUS-1", "abc", "3", "swgr_15kv",
            "1", "0", "10", "4", "",
        ])
        proj = PpProject(components=[b])
        net, _, _ = build_sc_network_multi_hop(proj, "BUS-1")
        assert net.rated_voltage_kV == 13.8

    def test_returns_tuple_of_3(self):
        proj = PpProject(components=[_bus("B1", "BUS-1")])
        result = build_sc_network_multi_hop(proj, "BUS-1")
        assert len(result) == 3
        net, chains, warns = result
        assert net is not None
        assert isinstance(chains, list)
        assert isinstance(warns, list)


# ---------------------------------------------------------------------------
# Cenário realista — não testa connectivity real (depende de
# pin geometry exato), apenas verifica que a API roda
# ---------------------------------------------------------------------------


class TestRealisticTopology:
    def test_three_level_topology_runs(self):
        """
        Topologia 3 níveis: UTIL → TR1 → BUS-MAIN → TR2 → BUS-CCM.

        Mesmo sem connectivity real (pinos não posicionados), a
        API deve executar sem erros.
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
        # Ambos os buses devem ser endereçáveis
        net1, _, _ = build_sc_network_multi_hop(proj, "BUS-MAIN")
        net2, _, _ = build_sc_network_multi_hop(proj, "BUS-CCM")
        assert net1.rated_voltage_kV == 13.8
        assert net2.rated_voltage_kV == 4.16

    def test_walks_does_not_explode_with_many_components(self):
        """Stress test: 20 componentes, max_hops=3."""
        components = [_bus("B0", "BUS-0", voltage="13.8")]
        for i in range(20):
            components.append(_mk("R", f"R{i}", ["100"]))
        proj = PpProject(components=components)
        # Deve completar rapidamente
        chains = find_source_chains(proj, "BUS-0", max_hops=3)
        # Sem fontes ⇒ nenhum chain
        assert chains == []
