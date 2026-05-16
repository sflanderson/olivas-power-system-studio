"""
Tests for app.preprocessor.bridge_to_atp and bridge_from_atp.

Cobertura
---------

* `to_atp`: cada tipo de componente Qucs vira o componente ATP
  esperado (R/L/C → BranchComponent; Vdc/Vac → SourceComponent;
  Diode → SwitchComponent; etc.).
* Topologia: nós são corretamente nomeados e propagados.
* Circuitos canônicos: divisor de tensão, RLC série, ponte de
  Wheatstone, retificador de meia onda.
* Round-trip parcial: `from_atp(to_atp(pp))` preserva contagem
  de componentes (a posição visual muda, mas o número e tipo
  dos elementos elétricos é estável).
* Warnings: componentes não-suportados acumulam mensagens em
  `AtpProject.warnings`.
* Integração com o serializer ATP existente: o resultado de
  `to_atp` pode ser serializado por `serialize_project` sem erro.
"""

from __future__ import annotations

import pytest

from app.core.project_model import (
    AtpProject,
    BranchComponent,
    SourceComponent,
    SwitchComponent,
)
from app.core.serializer import serialize_project

from app.preprocessor.bridge_from_atp import from_atp
from app.preprocessor.bridge_to_atp import to_atp
from app.preprocessor.models import (
    PpComponent,
    PpProperty,
    PpProject,
    PpWire,
)


# ---------------------------------------------------------------------------
# Builders compactos para testes
# ---------------------------------------------------------------------------


def _C(type_: str, name: str, x: int, y: int, *props: str,
       rotation: int = 1, mirror: int = 0) -> PpComponent:
    return PpComponent(
        type=type_, name=name, visible=True,
        x=x, y=y,
        label_dx=0, label_dy=0, mirror=mirror, rotation=rotation,
        properties=[PpProperty(value=p, visible=True) for p in props],
    )


def _GND(x: int, y: int) -> PpComponent:
    return PpComponent(
        type="GND", name="*", visible=True,
        x=x, y=y, label_dx=0, label_dy=0, mirror=0, rotation=0,
    )


def _wire(x1: int, y1: int, x2: int, y2: int, label: str = "") -> PpWire:
    lvis = 10 if label else 0
    return PpWire(
        x1=x1, y1=y1, x2=x2, y2=y2,
        label=label, label_x=x1, label_y=y1, label_visible=lvis,
    )


# ---------------------------------------------------------------------------
# Conversões individuais
# ---------------------------------------------------------------------------


class TestResistor:

    def test_resistor_becomes_branch(self):
        proj = PpProject()
        proj.components = [_C("R", "R1", 100, 100, "1k", rotation=1)]
        atp = to_atp(proj)
        assert len(atp.branches) == 1
        b = atp.branches[0]
        assert b.semantic_type == "resistor"
        # v0.91.10: ref1 deve ser blank para R linear (cols 15-20
        # ATP). Antes (bug) tinha o nome ("R1"), o que ATP
        # interpretava como bus3 inválido.
        assert b.ref1 == ""
        # 1k = 1000 — deve aparecer no campo de resistance
        assert "1000" in b.resistance

    def test_resistor_with_k_ohm(self):
        proj = PpProject()
        proj.components = [_C("R", "R1", 100, 100, "10 kOhm", rotation=1)]
        atp = to_atp(proj)
        assert "10000" in atp.branches[0].resistance


class TestInductor:

    def test_inductor_becomes_branch_with_mh(self):
        proj = PpProject()
        proj.components = [_C("L", "L1", 100, 100, "47uH", rotation=1)]
        atp = to_atp(proj)
        b = atp.branches[0]
        assert b.semantic_type == "inductor"
        # 47uH = 0.047 mH (ATP usa mH)
        assert "0.047" in b.inductance


class TestCapacitor:

    def test_capacitor_becomes_branch_with_uf(self):
        proj = PpProject()
        proj.components = [_C("C", "C1", 100, 100, "100u", rotation=1)]
        atp = to_atp(proj)
        b = atp.branches[0]
        assert b.semantic_type == "capacitor"
        # 100u = 100 uF (1e-4 F → 100 uF)
        assert "100" in b.capacitance


class TestSources:

    def test_vdc_becomes_dc_source(self):
        proj = PpProject()
        proj.components = [
            _C("Vdc", "V1", 100, 100, "12V", rotation=1),
            _GND(70, 100),
        ]
        atp = to_atp(proj)
        assert len(atp.sources) == 1
        s = atp.sources[0]
        assert s.type_code == "11"
        assert s.semantic_type == "dc"
        assert "12" in s.amplitude

    def test_vac_becomes_ac_source(self):
        proj = PpProject()
        proj.components = [
            _C("Vac", "V1", 100, 100, "220 V", "60 Hz", "0", "0", rotation=1),
            _GND(70, 100),
        ]
        atp = to_atp(proj)
        s = atp.sources[0]
        assert s.type_code == "14"
        assert s.semantic_type == "ac"
        assert "220" in s.amplitude
        assert "60" in s.frequency


class TestSwitches:

    def test_diode_becomes_switch(self):
        proj = PpProject()
        proj.components = [_C("Diode", "D1", 100, 100, rotation=0)]
        atp = to_atp(proj)
        assert len(atp.switches) == 1
        sw = atp.switches[0]
        assert sw.semantic_type == "diode"
        assert sw.switch_type == "DIODE"

    def test_thyristor_becomes_switch(self):
        proj = PpProject()
        proj.components = [_C("Thyr", "T1", 100, 100, rotation=0)]
        atp = to_atp(proj)
        assert atp.switches[0].switch_type == "THYR"

    def test_igbt_and_mosfet(self):
        proj = PpProject()
        proj.components = [
            _C("IGBT", "Q1", 100, 100, rotation=0),
            _C("MOSFET", "Q2", 200, 100, rotation=0),
        ]
        atp = to_atp(proj)
        types = {sw.switch_type for sw in atp.switches}
        assert types == {"IGBT", "MOSFET"}


class TestIgnoredTypes:

    def test_eqn_ignored(self):
        proj = PpProject()
        proj.components = [_C("Eqn", "E1", 100, 100, "x=1")]
        atp = to_atp(proj)
        assert atp.branches == []
        assert atp.sources == []
        assert atp.switches == []

    def test_simulation_directives_ignored(self):
        proj = PpProject()
        proj.components = [
            _C(".TR", "TR1", 100, 100),
            _C(".DC", "DC1", 200, 100),
            _C(".SW", "SW1", 300, 100),
        ]
        atp = to_atp(proj)
        assert (atp.branches, atp.sources, atp.switches) == ([], [], [])


class TestUnknownTypeWarning:

    def test_unknown_type_warns(self):
        proj = PpProject()
        proj.components = [_C("WeirdRF", "X1", 100, 100)]
        atp = to_atp(proj)
        assert any("WeirdRF" in w for w in atp.warnings)


# ---------------------------------------------------------------------------
# Circuitos canônicos
# ---------------------------------------------------------------------------


class TestVoltageDivider:
    """
    Vdc(12V) — N1 — R1(1k) — N2 — R2(1k) — GND

    Esperado: 1 Vdc source, 2 R branches, todos com nós corretos.
    """

    @pytest.fixture
    def atp(self) -> AtpProject:
        proj = PpProject()
        proj.components = [
            _C("Vdc", "V1", 100, 200, "12V", rotation=1),
            _C("R", "R1", 250, 200, "1k", rotation=1),
            _C("R", "R2", 400, 200, "1k", rotation=1),
            _GND(480, 200),
            _GND(70, 200),
        ]
        proj.wires = [
            _wire(130, 200, 220, 200, "VCC"),
            _wire(280, 200, 370, 200, "MID"),
            _wire(430, 200, 480, 200),
        ]
        return to_atp(proj)

    def test_three_components(self, atp: AtpProject):
        assert len(atp.sources) == 1
        assert len(atp.branches) == 2

    def test_topology(self, atp: AtpProject):
        # Vdc liga em VCC (nó vivo, GND no outro lado)
        assert atp.sources[0].node == "VCC"
        # v0.91.10: ref1 agora é blank (correto ATP). Identifica
        # branches por seus nós em vez de ref1 (que era nome do
        # componente, semanticamente errado).
        # R1: VCC - MID
        r1 = next(
            b for b in atp.branches
            if {b.node1, b.node2} == {"VCC", "MID"}
        )
        assert r1.semantic_type == "resistor"
        # R2: MID - GND ("")
        r2 = next(
            b for b in atp.branches
            if {b.node1, b.node2} == {"MID", ""}
        )
        assert r2.semantic_type == "resistor"

    def test_serializable(self, atp: AtpProject):
        # Não deve crashar
        text = serialize_project(atp)
        assert "BEGIN NEW DATA CASE" in text
        assert "VCC" in text
        assert "MID" in text


class TestRLCSeries:
    """Vac — R — L — C — GND, todos em série."""

    @pytest.fixture
    def atp(self) -> AtpProject:
        proj = PpProject()
        proj.components = [
            _C("Vac", "V1", 100, 200, "220 V", "60 Hz", "0", "0", rotation=1),
            _C("R", "R1", 250, 200, "1 Ohm", rotation=1),
            _C("L", "L1", 400, 200, "10 mH", rotation=1),
            _C("C", "C1", 550, 200, "100 uF", rotation=1),
            _GND(620, 200),
            _GND(70, 200),
        ]
        proj.wires = [
            _wire(130, 200, 220, 200, "N1"),
            _wire(280, 200, 370, 200, "N2"),
            _wire(430, 200, 520, 200, "N3"),
            _wire(580, 200, 620, 200),
        ]
        return to_atp(proj)

    def test_counts(self, atp: AtpProject):
        assert len(atp.sources) == 1  # Vac
        assert len(atp.branches) == 3  # R + L + C

    def test_each_branch_has_correct_semantic(self, atp: AtpProject):
        sems = {b.semantic_type for b in atp.branches}
        assert sems == {"resistor", "inductor", "capacitor"}

    def test_topology_in_series(self, atp: AtpProject):
        # Cada branch tem um nó em comum com o próximo
        all_nodes = []
        for b in atp.branches:
            all_nodes.append((b.node1, b.node2))
        # Conjunto total de nós: N1, N2, N3, "" (GND)
        flat = set()
        for n1, n2 in all_nodes:
            flat.update([n1, n2])
        assert flat == {"N1", "N2", "N3", ""}


class TestHalfWaveRectifier:
    """Vac — Diode — R — GND."""

    @pytest.fixture
    def atp(self) -> AtpProject:
        proj = PpProject()
        proj.components = [
            _C("Vac", "V1", 100, 200, "220 V", "60 Hz", "0", "0", rotation=1),
            _C("Diode", "D1", 250, 200, rotation=0),    # horizontal
            _C("R", "R1", 400, 200, "1k", rotation=1),
            _GND(480, 200),
            _GND(70, 200),
        ]
        proj.wires = [
            _wire(130, 200, 220, 200, "N1"),
            _wire(280, 200, 370, 200, "N2"),
            _wire(430, 200, 480, 200),
        ]
        return to_atp(proj)

    def test_one_source_one_switch_one_branch(self, atp: AtpProject):
        assert len(atp.sources) == 1
        assert len(atp.switches) == 1
        assert len(atp.branches) == 1

    def test_diode_is_marked_as_diode(self, atp: AtpProject):
        assert atp.switches[0].semantic_type == "diode"
        assert atp.switches[0].switch_type == "DIODE"


# ---------------------------------------------------------------------------
# Bridge inversa (ATP → Pp)
# ---------------------------------------------------------------------------


class TestFromAtp:

    def test_round_trip_count_voltage_divider(self):
        """to_atp → from_atp → to_atp: contagens estáveis."""
        proj1 = PpProject()
        proj1.components = [
            _C("Vdc", "V1", 100, 200, "12V", rotation=1),
            _C("R", "R1", 250, 200, "1k", rotation=1),
            _C("R", "R2", 400, 200, "1k", rotation=1),
            _GND(480, 200),
            _GND(70, 200),
        ]
        proj1.wires = [
            _wire(130, 200, 220, 200, "VCC"),
            _wire(280, 200, 370, 200, "MID"),
            _wire(430, 200, 480, 200),
        ]
        atp1 = to_atp(proj1)
        proj2 = from_atp(atp1)

        assert len(proj2.components_of_type("R")) == 2
        assert len(proj2.components_of_type("Vdc")) == 1

        atp2 = to_atp(proj2)
        # Counts preservados
        assert len(atp2.branches) == len(atp1.branches)
        assert len(atp2.sources) == len(atp1.sources)

    def test_from_atp_creates_default_properties(self):
        """from_atp para projeto vazio gera bloco de Properties default."""
        atp = AtpProject()
        proj = from_atp(atp)
        assert "View" in proj.properties
        assert "Grid" in proj.properties
        assert proj.version == "0.0.19"

    def test_from_atp_branch_resistor(self):
        atp = AtpProject()
        atp.branches.append(BranchComponent(
            node1="A", node2="B", ref1="R1",
            resistance="100", semantic_type="resistor",
        ))
        proj = from_atp(atp)
        rs = proj.components_of_type("R")
        assert len(rs) == 1
        assert "100" in rs[0].properties[0].value

    def test_from_atp_branch_inductor(self):
        atp = AtpProject()
        atp.branches.append(BranchComponent(
            node1="A", node2="B", ref1="L1",
            inductance="10", semantic_type="inductor",
        ))
        proj = from_atp(atp)
        ls = proj.components_of_type("L")
        assert len(ls) == 1

    def test_from_atp_branch_capacitor(self):
        atp = AtpProject()
        atp.branches.append(BranchComponent(
            node1="A", node2="B", ref1="C1",
            capacitance="100", semantic_type="capacitor",
        ))
        proj = from_atp(atp)
        cs = proj.components_of_type("C")
        assert len(cs) == 1

    def test_from_atp_source_ac(self):
        atp = AtpProject()
        atp.sources.append(SourceComponent(
            node="A", type_code="14",
            amplitude="220", frequency="60", phase="0",
            semantic_type="ac",
        ))
        proj = from_atp(atp)
        vacs = proj.components_of_type("Vac")
        assert len(vacs) == 1
        # Tem um GND companion
        assert len(proj.components_of_type("GND")) == 1


class TestPlaceholderWarnings:

    def test_transformer_emits_warning(self):
        proj = PpProject()
        proj.components = [_C("Tr", "TR1", 100, 100, "20")]
        atp = to_atp(proj)
        assert any("Transformador" in w and "TR1" in w for w in atp.warnings)

    def test_line_emits_warning(self):
        proj = PpProject()
        proj.components = [_C("BERG", "LN1", 100, 100)]
        atp = to_atp(proj)
        assert any("Linha" in w for w in atp.warnings)

    def test_zno_emits_warning(self):
        proj = PpProject()
        proj.components = [_C("ZnO", "ZN1", 100, 100)]
        atp = to_atp(proj)
        assert any("Não-linear" in w for w in atp.warnings)


class TestEmptyProject:

    def test_empty_pp_to_atp(self):
        atp = to_atp(PpProject())
        assert atp.branches == []
        assert atp.switches == []
        assert atp.sources == []
        # Mas tem o esqueleto serializável
        assert "BRANCH" in atp.sections
        text = serialize_project(atp)
        assert "BLANK BRANCH" in text


class TestNodesPopulated:

    def test_nodes_dict_filled(self):
        proj = PpProject()
        proj.components = [
            _C("Vdc", "V1", 100, 200, "12V", rotation=1),
            _C("R", "R1", 250, 200, "1k", rotation=1),
            _GND(70, 200),
            _GND(280, 200),
        ]
        proj.wires = [_wire(130, 200, 220, 200, "VCC")]
        atp = to_atp(proj)
        # VCC deve estar no dict de nós
        assert "VCC" in atp.nodes
        # Source e Branch ambos referenciam VCC
        assert "source" in atp.nodes["VCC"].sources
        assert "branch" in atp.nodes["VCC"].sources
