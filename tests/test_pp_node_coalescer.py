"""
Tests for app.preprocessor.node_coalescer.

Verifica que a topologia gráfica (componentes posicionados + fios)
gera a malha de nós correta para a bridge ATP.
"""

from __future__ import annotations

import pytest

from app.preprocessor.models import (
    PpComponent,
    PpProperty,
    PpProject,
    PpWire,
)
from app.preprocessor.node_coalescer import (
    coalesce_nodes,
    pin_positions,
    _transform_pin,
)


# ---------------------------------------------------------------------------
# Helpers para construir circuitos rapidamente
# ---------------------------------------------------------------------------


def _R(name: str, x: int, y: int, value: str = "1k", rotation: int = 1) -> PpComponent:
    """Resistor vertical (rotation=1) por default."""
    return PpComponent(
        type="R", name=name, visible=True,
        x=x, y=y,
        label_dx=15, label_dy=-26, mirror=0, rotation=rotation,
        properties=[
            PpProperty(value=value, visible=True),
            PpProperty(value="26.85", visible=False),
            PpProperty(value="european", visible=False),
        ],
    )


def _Vdc(name: str, x: int, y: int, value: str = "12V") -> PpComponent:
    return PpComponent(
        type="Vdc", name=name, visible=True,
        x=x, y=y,
        label_dx=18, label_dy=-26, mirror=0, rotation=1,
        properties=[PpProperty(value=value, visible=True)],
    )


def _Vac(name: str, x: int, y: int) -> PpComponent:
    return PpComponent(
        type="Vac", name=name, visible=True,
        x=x, y=y,
        label_dx=18, label_dy=-26, mirror=0, rotation=1,
        properties=[
            PpProperty(value="220 V", visible=True),
            PpProperty(value="60 Hz", visible=True),
            PpProperty(value="0", visible=False),
            PpProperty(value="0", visible=False),
        ],
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
# Pin geometry
# ---------------------------------------------------------------------------


class TestPinGeometry:

    def test_resistor_default_rotation_1_vertical(self):
        # rotation=1 → 90° CCW: (0,-30) -> (30,0); (0,30) -> (-30,0)
        # Mas o catálogo é definido em rotation=0 (vertical: ±30 em y).
        # Em rotation=1, fica horizontal.
        r = _R("R1", 100, 100, rotation=1)
        pins = pin_positions(r)
        assert pins == [(130, 100), (70, 100)]

    def test_resistor_rotation_0_keeps_vertical(self):
        r = _R("R1", 100, 100, rotation=0)
        pins = pin_positions(r)
        assert pins == [(100, 70), (100, 130)]

    def test_gnd_single_pin_at_anchor(self):
        g = _GND(50, 50)
        pins = pin_positions(g)
        assert pins == [(50, 50)]

    def test_unknown_type_uses_default(self):
        c = PpComponent(
            type="UNKNOWN_FOO", name="X1", visible=True,
            x=200, y=300,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
        )
        pins = pin_positions(c)
        # default 2-terminal vertical
        assert pins == [(200, 270), (200, 330)]

    def test_transform_rotations(self):
        # (10, 0) rotated 90 CCW → (0, 10)
        assert _transform_pin(10, 0, 1, 0) == (0, 10)
        # (10, 0) rotated 180 → (-10, 0)
        assert _transform_pin(10, 0, 2, 0) == (-10, 0)
        # (10, 0) rotated 270 CCW → (0, -10)
        assert _transform_pin(10, 0, 3, 0) == (0, -10)

    def test_transform_mirror(self):
        # mirror inverte X
        assert _transform_pin(10, 5, 0, 1) == (-10, 5)


# ---------------------------------------------------------------------------
# Cenários de coalescência
# ---------------------------------------------------------------------------


class TestCoalesceVoltageDivider:
    """
    Divisor de tensão simples:

        Vdc — N1 — R1 — N2 — R2 — GND

    Esperamos 2 nós elétricos: o nó vivo entre R1 e R2 (N2) e
    o nó VCC (N1). Mais a terra implícita.
    """

    @pytest.fixture
    def project(self) -> PpProject:
        proj = PpProject()
        # Layout:
        #   Vdc em (100, 200), pinos em (130, 200) e (70, 200)
        #   R1  em (250, 200), pinos em (280, 200) e (220, 200)
        #   R2  em (400, 200), pinos em (430, 200) e (370, 200)
        #   GND em (480, 200)
        # Com fios:
        #   (130,200) - (220,200)   conecta Vdc topo a R1 esq → "VCC"
        #   (280,200) - (370,200)   conecta R1 dir a R2 esq → "MID"
        #   (430,200) - (480,200)   conecta R2 dir a GND
        #   (70,200)  - (480,210)   conecta Vdc base a GND? — não,
        #                            Vdc base também vai pra GND via outro
        #                            caminho. Simplificamos: outra GND.
        proj.components = [
            _Vdc("V1", 100, 200),
            _R("R1", 250, 200, "1k", rotation=1),
            _R("R2", 400, 200, "1k", rotation=1),
            _GND(480, 200),
            _GND(70, 200),
        ]
        proj.wires = [
            _wire(130, 200, 220, 200, "VCC"),
            _wire(280, 200, 370, 200, "MID"),
            _wire(430, 200, 480, 200),
            # base do Vdc encosta direto na GND em (70, 200)
        ]
        return proj

    def test_two_elementsn_get_VCC_node(self, project: PpProject):
        nm = coalesce_nodes(project)
        # Vdc topo (pin 0) e R1 esq (pin 1) devem estar no nó "VCC"
        # Atenção: rotation=1 troca a ordem dos pinos. Para Vdc:
        # pin 0 era (0,-30) → vira (30, 0) → posição (130, 200)
        # pin 1 era (0, 30) → vira (-30, 0) → posição (70, 200)
        assert nm.pin_to_node[("V1", 0)] == "VCC"
        assert nm.pin_to_node[("R1", 1)] == "VCC"

    def test_mid_node(self, project: PpProject):
        nm = coalesce_nodes(project)
        assert nm.pin_to_node[("R1", 0)] == "MID"
        assert nm.pin_to_node[("R2", 1)] == "MID"

    def test_ground_is_empty_string(self, project: PpProject):
        nm = coalesce_nodes(project)
        assert nm.pin_to_node[("R2", 0)] == ""  # liga em GND
        # Vdc base também em GND (encosta diretamente em (70, 200))
        assert nm.pin_to_node[("V1", 1)] == ""

    def test_node_count(self, project: PpProject):
        nm = coalesce_nodes(project)
        # 3 nós distintos: VCC, MID, ""
        nodes = set(nm.pin_to_node.values())
        assert nodes == {"VCC", "MID", ""}


class TestCoalesceSyntheticNames:
    """Nós sem label e sem GND recebem nomes N0001, N0002, ..."""

    def test_one_unlabeled_node(self):
        proj = PpProject()
        proj.components = [
            _R("R1", 100, 100, rotation=1),
            _R("R2", 200, 100, rotation=1),
        ]
        # Conecta R1 dir a R2 esq, sem label
        proj.wires = [_wire(130, 100, 170, 100)]
        nm = coalesce_nodes(proj)
        # Deve existir um nó N0001
        names = set(nm.pin_to_node.values())
        assert any(n.startswith("N") for n in names)


class TestCoalesceLabelTruncation:
    """Labels longos > 6 chars são truncados (limitação do ATP)."""

    def test_label_truncated_to_6_chars(self):
        proj = PpProject()
        proj.components = [
            _R("R1", 100, 100, rotation=1),
            _R("R2", 200, 100, rotation=1),
        ]
        proj.wires = [_wire(130, 100, 170, 100, "MUITO_LONGO_DEMAIS")]
        nm = coalesce_nodes(proj)
        names = set(nm.pin_to_node.values()) - {""}
        # Algum nome com ≤ 6 chars
        assert any(len(n) <= 6 and n.startswith("MUITO") for n in names)


class TestCoalesceLabelSanitization:
    """Caracteres especiais em labels viram '_'."""

    def test_non_alnum_replaced(self):
        proj = PpProject()
        proj.components = [_R("R1", 100, 100, rotation=1)]
        proj.wires = [_wire(130, 100, 200, 100, "n+1")]
        nm = coalesce_nodes(proj)
        for name in nm.pin_to_node.values():
            assert "+" not in name


class TestCoalesceMultipleGNDs:
    """Múltiplos GNDs no mesmo cluster permanecem como '' apenas."""

    def test_two_gnds_one_node(self):
        proj = PpProject()
        proj.components = [
            _R("R1", 100, 100, rotation=1),
            _GND(70, 100),     # liga ao pino esq (rot=1) de R1
            _GND(130, 100),    # liga ao pino dir (rot=1) de R1
        ]
        nm = coalesce_nodes(proj)
        # Ambos pinos de R1 viram ""
        assert nm.pin_to_node[("R1", 0)] == ""
        assert nm.pin_to_node[("R1", 1)] == ""


class TestCoalesceEmptyProject:

    def test_empty_returns_empty_map(self):
        nm = coalesce_nodes(PpProject())
        assert nm.pin_to_node == {}
        assert nm.next_synthetic == 1
