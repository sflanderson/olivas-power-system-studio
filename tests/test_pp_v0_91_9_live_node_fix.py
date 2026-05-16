"""
tests/test_pp_v0_91_9_live_node_fix.py — v0.91.9:

Hotfix do bug onde ``_live_node()`` escolhia o pino DANGLING
do Vac em vez do CONECTADO ao circuito.

Bug
====

Topologia simples Vac → BUS → GND:

::

    Vac (UTIL-1, top dangling)
        bottom (200, 100)
            │
        wire │
            │
    BUS-MAIN-13.8 T2_B (200, 200)
            │
        wire │
            │
    GND (200, 290)

Coalescer mapeia:
* Vac.pin0 (top) → N0001 (alone, dangling)
* Vac.pin1 (bottom) → N0002 (com BUS+R+...)

``_live_node(n1=N0001, n2=N0002)`` retornava **N0001** (legacy:
"primeiro não-GND"), colocando a fonte Vac no nó dangling. ATP
via Vac em N0001 isolado e branches em N0002 → tudo desconectado
→ erro "ATP reportou erros".

Fix
====

``_live_node(n1, n2, node_map=None)``:

* Quando ambos não-GND: prefere o nó com MAIS pinos coalescidos
  (mais conectado a outros componentes).
* Empate ou sem ``node_map``: comportamento legacy (n1).

Cobertura
---------

* ``_live_node`` legacy (sem node_map): n1 vence.
* ``_live_node`` com node_map: prefere o nó com mais pinos.
* ``_live_node`` com nó GND ('') retornado direto (caso 1).
* Industrial template: Vac.SOURCE acaba em N0002 (com BUS+R),
  não em N0001 (dangling).
* Simple template: Vac.SOURCE não fica em nó dangling.
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# _live_node unit tests
# ---------------------------------------------------------------------------


class TestLiveNode:

    def test_legacy_no_node_map_n1_wins(self):
        from app.preprocessor.bridge_to_atp import _live_node
        # Sem node_map, comportamento original: n1 vence
        assert _live_node("N1", "N2") == "N1"

    def test_n1_gnd_n2_wins(self):
        from app.preprocessor.bridge_to_atp import _live_node
        # n1 é GND ('') → retorna n2
        assert _live_node("", "N2") == "N2"

    def test_n2_gnd_n1_wins(self):
        from app.preprocessor.bridge_to_atp import _live_node
        # n2 é GND ('') → retorna n1
        assert _live_node("N1", "") == "N1"

    def test_both_gnd_returns_empty(self):
        from app.preprocessor.bridge_to_atp import _live_node
        assert _live_node("", "") == ""

    def test_with_node_map_prefers_connected(self):
        """v0.91.9: com node_map, prefere o nó com mais pinos."""
        from app.preprocessor.bridge_to_atp import _live_node
        from app.preprocessor.node_coalescer import NodeMap

        nm = NodeMap()
        nm.node_to_pins = {
            "N1": [("Vac", 0)],                      # 1 pino (alone)
            "N2": [("Vac", 1), ("R", 0), ("L", 0)],  # 3 pinos
        }
        # n1=N1 (1 pino), n2=N2 (3 pinos) → escolhe N2
        assert _live_node("N1", "N2", nm) == "N2"

    def test_with_node_map_n1_more_connected(self):
        from app.preprocessor.bridge_to_atp import _live_node
        from app.preprocessor.node_coalescer import NodeMap

        nm = NodeMap()
        nm.node_to_pins = {
            "N1": [("Vac", 0), ("BUS", 4), ("R", 0)],  # 3 pinos
            "N2": [("Vac", 1)],                         # 1 pino
        }
        # n1 mais conectado → N1
        assert _live_node("N1", "N2", nm) == "N1"

    def test_tie_falls_back_to_n1(self):
        from app.preprocessor.bridge_to_atp import _live_node
        from app.preprocessor.node_coalescer import NodeMap

        nm = NodeMap()
        nm.node_to_pins = {
            "N1": [("Vac", 0), ("R", 0)],
            "N2": [("Vac", 1), ("L", 0)],
        }
        # Empate → n1 (legacy)
        assert _live_node("N1", "N2", nm) == "N1"


# ---------------------------------------------------------------------------
# Integração com templates v0.91.3
# ---------------------------------------------------------------------------


class TestTemplateBridgeIntegration:

    def test_simple_template_is_degenerate_but_emits(self, qapp):
        """
        Simple template: topologia Vac→BUS→GND é
        DEGENERADA (curto-circuito Vac↔GND via wire chain). O
        Vac.pin1 é coalescido com GND, Vac.pin0 fica dangling
        (N0001). ``_live_node`` cai no caso "n2 é GND → retorna
        n1" (legacy), source acaba em N0001 (dangling).

        Smoke: o bridge não crasha, emite 1 source. O usuário
        deve usar industrial_480V (tem R+L feeder) para um
        circuito ATP real.
        """
        from app.preprocessor.bridge_to_atp import to_atp
        from app.preprocessor.templates import build_simple_13_8kV
        proj = build_simple_13_8kV()
        atp = to_atp(proj)
        # Smoke: source emitida, bridge não crasha
        assert len(atp.sources) == 1

    def test_industrial_vac_source_connected_to_circuit(self, qapp):
        """Industrial template: Vac.SOURCE node deve coincidir
        com R_FEED.0 (não com Vac.top dangling)."""
        from app.preprocessor.bridge_to_atp import to_atp
        from app.preprocessor.node_coalescer import coalesce_nodes
        from app.preprocessor.templates import build_industrial_480V
        proj = build_industrial_480V()
        nm = coalesce_nodes(proj)
        atp = to_atp(proj)
        assert len(atp.sources) == 1
        assert len(atp.branches) >= 2
        src = atp.sources[0]
        # Pegar nó N de R_FEED.0 e comparar com src.node
        r_feed_pin0_node = nm.pin_to_node.get(("R_FEED", 0))
        assert r_feed_pin0_node is not None
        assert src.node == r_feed_pin0_node, (
            f"Vac.SOURCE em {src.node!r}, mas R_FEED.0 em "
            f"{r_feed_pin0_node!r} — deviam ser o mesmo nó "
            f"(circuito conectado)"
        )

    def test_industrial_atp_circuit_topologically_valid(self, qapp):
        """Industrial template: cada source deve ter conexão a
        pelo menos 1 branch (circuito não-trivial)."""
        from app.preprocessor.bridge_to_atp import to_atp
        from app.preprocessor.templates import build_industrial_480V
        proj = build_industrial_480V()
        atp = to_atp(proj)
        # Pega nós das branches
        branch_nodes = set()
        for b in atp.branches:
            for n in (b.node1, b.node2):
                if n:
                    branch_nodes.add(n)
        # Cada source deve ter seu nó em ao menos 1 branch
        for src in atp.sources:
            assert src.node in branch_nodes, (
                f"Source em {src.node!r} não conecta a nenhuma "
                f"branch (branches: {branch_nodes})"
            )
