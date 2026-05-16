"""
tests/test_pp_v0_93_3_examples_connectivity.py — v0.93.3:

Regressão: garante que TODOS os esquemáticos de exemplo
(``app/examples/schematics/*.sch``) tenham BUSes conectados
ao loadar.

Bug original (reportado pelo usuário com screenshot):
após v0.92.1 (Bus PTW = 21 pinos sintéticos a cada 10 px),
os arquivos .sch antigos tinham wires desalinhados em 10-50px
relação aos pinos atuais → BUSes detectados com 0 vizinhos
→ pipeline reportava "nenhuma fonte de SC encontrada".

Causa raiz dupla:

1. Wires nos .sch desalinhados (corrigido via
   ``scripts/migrate_sch_wires.py`` + ``rebuild_example_sch.py``).
2. Pinos do BUS NÃO eram unificados internamente — cada um
   dos 21 pinos sintéticos virava um nó isolado, em vez de
   compartilharem a mesma malha (BUS = barra de cobre =
   equipotencial). Corrigido em ``node_coalescer.coalesce_nodes``.

Esta suite garante que ambos os bugs não voltem.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.preprocessor.qucs_sch_parser import parse_sch_file
from app.preprocessor.node_coalescer import coalesce_nodes
from app.postprocessor.bus_pipeline import find_neighbors_of_bus


SCHEMATICS_DIR = (
    Path(__file__).resolve().parent.parent
    / "app" / "examples" / "schematics"
)


def _load_example(name: str):
    path = SCHEMATICS_DIR / name
    assert path.is_file(), f"Schematic não encontrado: {path}"
    return parse_sch_file(str(path))


# ---------------------------------------------------------------------------
# BUS pins equipotential (root cause #2)
# ---------------------------------------------------------------------------


class TestBusEquipotential:
    """v0.93.3: todos os pinos sintéticos do BUS DEVEM ser
    unificados (mesmo nó). Antes (v0.92.1+v0.92.2) cada pino
    era um nó isolado, quebrando find_neighbors_of_bus."""

    @pytest.mark.parametrize(
        "sch_name",
        [
            "iec60909_annex_c.sch",
            "ieee1584_ex_d2.sch",
            "ieee399_motor_starting.sch",
            "nbr17227_example.sch",
            "stevenson_pf_3bus.sch",
            "stevenson_sequential.sch",
        ],
    )
    def test_bus_pins_share_node(self, sch_name):
        """Em cada exemplo, TODOS os 21 pinos de cada BUS
        devem mapear para um único nó (a barra é equipotencial)."""
        proj = _load_example(sch_name)
        nm = coalesce_nodes(proj)
        for c in proj.components:
            if c.type != "BUS":
                continue
            # Coleta todos os nodes dos 21 pinos deste BUS
            bus_nodes = set()
            for (comp_name, pin_idx), node in nm.pin_to_node.items():
                if comp_name == c.name:
                    bus_nodes.add(node)
            assert len(bus_nodes) == 1, (
                f"BUS {c.name!r} em {sch_name}: pinos espalhados "
                f"entre {len(bus_nodes)} nós: {sorted(bus_nodes)}"
            )

    def test_artificial_bus_with_no_wires(self):
        """v0.93.3: mesmo um BUS isolado (sem wires) deve ter
        todos os pinos no mesmo nó."""
        from app.preprocessor.models import (
            PpComponent, PpProject, PpProperty,
        )
        proj = PpProject(version="0.0.19")
        proj.components.append(PpComponent(
            type="BUS", name="LONELY", visible=True,
            x=200, y=200, label_dx=0, label_dy=0,
            mirror=0, rotation=0,
            properties=[
                PpProperty("LONELY", True),
                PpProperty("13.8", True),
                PpProperty("3", False),
                PpProperty("swgr_15kv", True),
                PpProperty("1", True),
                PpProperty("0", True),
                PpProperty("10", False),
                PpProperty("4", False),
                PpProperty("", False),
            ],
        ))
        nm = coalesce_nodes(proj)
        bus_nodes = set()
        for (comp_name, pin_idx), node in nm.pin_to_node.items():
            if comp_name == "LONELY":
                bus_nodes.add(node)
        assert len(bus_nodes) == 1


# ---------------------------------------------------------------------------
# Examples: BUS connectivity (root cause #1)
# ---------------------------------------------------------------------------


class TestExamplesConnectivity:
    """v0.93.3: cada exemplo .sch deve ter PELO MENOS 1
    vizinho em cada BUS (com exceção de buses PQ
    explicitamente sem fonte como stevenson B3)."""

    EXAMPLES_MIN_NEIGHBORS: dict[str, dict[str, int]] = {
        "iec60909_annex_c.sch": {"BUS_HV": 1, "BUS_LV": 1},
        "ieee1584_ex_d2.sch": {"BUS_LV": 1},
        "ieee399_motor_starting.sch": {"BUS_4": 2},
        "nbr17227_example.sch": {"BUS_HV": 1, "SWGR_138": 1},
        "stevenson_pf_3bus.sch": {"B1": 1, "B2": 1, "B3": 1},
        "stevenson_sequential.sch": {"BUS_F": 1},
    }

    @pytest.mark.parametrize(
        "sch_name", sorted(EXAMPLES_MIN_NEIGHBORS.keys()),
    )
    def test_bus_has_minimum_neighbors(self, sch_name):
        proj = _load_example(sch_name)
        expected = self.EXAMPLES_MIN_NEIGHBORS[sch_name]
        for bus_id, min_n in expected.items():
            neighbors = find_neighbors_of_bus(proj, bus_id)
            assert len(neighbors) >= min_n, (
                f"{sch_name}::{bus_id} tem {len(neighbors)} "
                f"vizinhos; esperado ≥{min_n}. "
                f"Vizinhos: "
                f"{[(n.component.type, n.component.name) for n in neighbors]}"
            )


# ---------------------------------------------------------------------------
# Pipeline integration (1 example smoke)
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """v0.93.3: pelo menos 1 exemplo MV (NBR 17227) deve
    rodar o pipeline completo de SC + arc-flash sem erro."""

    def test_nbr17227_swgr_runs_full_pipeline(self):
        from app.postprocessor.bus_pipeline import (
            analyze_bus_full_pipeline,
        )
        proj = _load_example("nbr17227_example.sch")
        # SWGR_138 é 13.8 kV (nome confuso, a tensão é 13.8)
        report = analyze_bus_full_pipeline(
            proj, "SWGR_138",
            coordination_clearing_time_ms=500.0,
            use_multi_hop=True,
        )
        assert report.Ik_pp_kA > 0
        assert report.incident_energy_cal_cm2 > 0
