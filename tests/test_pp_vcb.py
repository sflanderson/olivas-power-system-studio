"""
Tests for the VCB (Vacuum Circuit Breaker) component — sprint v0.21.7.

Escopo
------

Esta sprint adicionou:

1. ``VCB`` 1φ (já existia no catálogo, mas passou a ter tradução
   dedicada em :mod:`app.preprocessor.bridge_to_atp` com 10
   propriedades: ``T_open``, ``T_close`` e 8 parâmetros estatísticos
   de reignição).
2. ``VCB3`` 3φ (NOVO): disjuntor a vácuo trifásico, com três chaves
   independentes (6 pinos), ``T_open``/``T_close`` por fase e os
   mesmos parâmetros estatísticos compartilhados pelo pólo
   (``I_chop``, σ, di/dt, k_dielec, etc.).
3. :func:`app.preprocessor.catalog.property_labels` — mapeia ``code``
   → tupla de labels humanos (ex: ``"T_open_A [s]"``). A GUI usa
   esses labels em vez de ``"#1:"`` para os 14 parâmetros do VCB3.
4. Renderer :class:`VCB3PhaseSymbol` — 3 chaves empilhadas
   verticalmente dentro de um invólucro tracejado (câmara de vácuo).

O teste suite abaixo cobre:

* Catálogo: entrada VCB3 presente, ``is_atp_supported``, labels.
* Geometria de pinos: ``_PIN_GEOMETRY`` retorna 6 pinos em ±40.
* Coalescência: duas VCBs 3φ conectadas por fase geram 3 nós.
* Bridge ``to_atp``: VCB 1φ emite 1 SWITCH ``VCB``; VCB3 emite 3
  SWITCHes com ``T_open``/``T_close`` independentes.
* Warnings: parâmetros de reignição acumulam aviso.
* Renderer: bounding rect correto, paint não crasha, 6 pinos.
* Editor: ``add_component_by_type("VCB3")`` cria componente com
  as 14 properties default; painel exibe label humano.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication, QFormLayout, QGroupBox, QLabel

from app.preprocessor import catalog
from app.preprocessor.bridge_to_atp import to_atp
from app.preprocessor.models import PpComponent, PpProject, PpProperty, PpWire
from app.preprocessor.node_coalescer import _PIN_GEOMETRY, coalesce_nodes, pin_positions
from app.preprocessor.symbols import (
    VCB3PhaseSymbol,
    all_renderers,
    get_renderer,
)

from app.gui.schematic_pp import ComponentItem, PpEditor, PpPropertiesPanel


# ---------------------------------------------------------------------------
# QApplication fixture — obrigatório para qualquer teste que use PySide6.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vcb3(name: str = "B1", x: int = 100, y: int = 100,
               **overrides) -> PpComponent:
    """
    Cria um ``PpComponent`` VCB3 com as 14 propriedades default.
    Use ``overrides[idx] = value`` para sobrescrever propriedades
    específicas (ex: ``overrides[0]="25e-3"`` muda T_open_A).
    """
    default_props = [
        "50e-3", "1e9",
        "50e-3", "1e9",
        "50e-3", "1e9",
        "5", "1",
        "16", "0.034",
        "17", "0.69e3",
        "5e-4", "1",
    ]
    for idx, val in overrides.items():
        default_props[idx] = val
    return PpComponent(
        type="VCB3", name=name, visible=True,
        x=x, y=y, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(value=v, visible=True) for v in default_props],
    )


def _make_vcb1(name: str = "B1", x: int = 100, y: int = 100,
               **overrides) -> PpComponent:
    default_props = [
        "0", "1e9",
        "5", "1",
        "16", "0.034",
        "17", "0.69e3",
        "5e-4", "1",
    ]
    for idx, val in overrides.items():
        default_props[idx] = val
    return PpComponent(
        type="VCB", name=name, visible=True,
        x=x, y=y, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(value=v, visible=True) for v in default_props],
    )


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------


class TestCatalog:

    def test_vcb3_entry_exists(self):
        e = catalog.get("VCB3")
        assert e is not None
        assert e.code == "VCB3"
        assert e.category == "switch"
        assert e.atp_supported is True

    def test_vcb_and_vcb3_are_distinct_entries(self):
        v1 = catalog.get("VCB")
        v3 = catalog.get("VCB3")
        assert v1 is not None and v3 is not None
        assert v1.code != v3.code
        # O label é distinto — o usuário precisa diferenciar na paleta.
        assert v1.label_pt != v3.label_pt
        assert "3" in v3.label_pt or "tri" in v3.label_pt.lower()

    def test_switch_category_contains_vcb3(self):
        codes = [e.code for e in catalog.by_category("switch")]
        assert "VCB3" in codes
        assert "VCB" in codes

    def test_is_atp_supported_vcb3_true(self):
        assert catalog.is_atp_supported("VCB3") is True


class TestPropertyLabels:

    def test_vcb_has_10_labels(self):
        labels = catalog.property_labels("VCB")
        assert len(labels) == 10
        # Primeiros dois são T_open / T_close
        assert "T_open" in labels[0]
        assert "T_close" in labels[1]

    def test_vcb3_has_14_labels(self):
        labels = catalog.property_labels("VCB3")
        assert len(labels) == 14

    def test_vcb3_per_phase_labels(self):
        labels = catalog.property_labels("VCB3")
        # Pares T_open_X / T_close_X por fase A, B, C
        assert labels[0] == "T_open_A [s]"
        assert labels[1] == "T_close_A [s]"
        assert labels[2] == "T_open_B [s]"
        assert labels[3] == "T_close_B [s]"
        assert labels[4] == "T_open_C [s]"
        assert labels[5] == "T_close_C [s]"

    def test_vcb3_reignition_labels_present(self):
        labels = catalog.property_labels("VCB3")
        # I_chop aparece em algum slot entre 6 e 13
        joined = " | ".join(labels[6:])
        assert "I_chop" in joined
        assert "di/dt" in joined
        assert "k_dielec" in joined
        assert "Seed" in joined

    def test_unknown_code_returns_empty_tuple(self):
        assert catalog.property_labels("XYZ_NAO_EXISTE") == ()

    def test_labels_are_strings(self):
        for code in ("R", "VCB", "VCB3", "Vac"):
            for label in catalog.property_labels(code):
                assert isinstance(label, str)
                assert label  # não vazio


# ---------------------------------------------------------------------------
# Node coalescer: geometria de pinos
# ---------------------------------------------------------------------------


class TestPinGeometry:

    def test_vcb3_has_6_pins(self):
        assert "VCB3" in _PIN_GEOMETRY
        pins = _PIN_GEOMETRY["VCB3"]
        assert len(pins) == 6

    def test_vcb3_pins_in_horizontal_pairs(self):
        pins = _PIN_GEOMETRY["VCB3"]
        # Três pares left/right
        lefts = sorted({p for p in pins if p[0] < 0}, key=lambda q: q[1])
        rights = sorted({p for p in pins if p[0] > 0}, key=lambda q: q[1])
        assert len(lefts) == 3
        assert len(rights) == 3
        # Mesmos Y: -30, 0, 30
        assert [p[1] for p in lefts] == [-30, 0, 30]
        assert [p[1] for p in rights] == [-30, 0, 30]

    def test_vcb3_leads_at_plus_minus_40(self):
        pins = _PIN_GEOMETRY["VCB3"]
        xs = {p[0] for p in pins}
        assert xs == {-40, 40}

    def test_pin_positions_on_rotated_vcb3(self):
        """
        Rotação 1 (90° CCW) transforma (dx, dy) → (-dy, dx).
        Garante que o helper `pin_positions` aplica corretamente.
        """
        c = _make_vcb3(name="B1", x=0, y=0)
        c.rotation = 0
        ps_0 = pin_positions(c)
        c.rotation = 1
        ps_1 = pin_positions(c)
        # Não são idênticos — a rotação altera as coordenadas.
        assert ps_0 != ps_1
        # Ainda são 6 pinos.
        assert len(ps_1) == 6


# ---------------------------------------------------------------------------
# Node coalescer: conectividade elétrica
# ---------------------------------------------------------------------------


class TestCoalescenceVCB3:

    def test_three_independent_phases_produce_three_nodes(self):
        """
        Dois VCB3 conectados fase-a-fase (sem ground) devem
        produzir exatamente 3 nós elétricos (um por fase).

        Layout: VCB3_1 @ (100, 100) → VCB3_2 @ (200, 100)
          Pinos VCB3_1: (60,70)(140,70) (60,100)(140,100) (60,130)(140,130)
          Pinos VCB3_2: (160,70)(240,70) (160,100)(240,100) (160,130)(240,130)
        Wires: ligando (140,Y) ↔ (160,Y) para cada fase.
        """
        proj = PpProject()
        proj.components = [
            _make_vcb3(name="B1", x=100, y=100),
            _make_vcb3(name="B2", x=200, y=100),
        ]
        proj.wires = [
            PpWire(x1=140, y1=70, x2=160, y2=70),
            PpWire(x1=140, y1=100, x2=160, y2=100),
            PpWire(x1=140, y1=130, x2=160, y2=130),
        ]
        nm = coalesce_nodes(proj)
        # B1 out (pinos 1, 3, 5) ↔ B2 in (pinos 0, 2, 4) por fase
        nodes_b1_out = {
            nm.pin_to_node[("B1", 1)],
            nm.pin_to_node[("B1", 3)],
            nm.pin_to_node[("B1", 5)],
        }
        nodes_b2_in = {
            nm.pin_to_node[("B2", 0)],
            nm.pin_to_node[("B2", 2)],
            nm.pin_to_node[("B2", 4)],
        }
        # 3 nós distintos (uma por fase)
        assert len(nodes_b1_out) == 3
        assert nodes_b1_out == nodes_b2_in

    def test_phases_do_not_short_without_wires(self):
        """
        Sem fios conectando as fases, cada par in/out deve ter
        seu próprio nome de nó.
        """
        proj = PpProject()
        proj.components = [_make_vcb3(name="B1", x=100, y=100)]
        nm = coalesce_nodes(proj)
        names = {nm.pin_to_node[("B1", i)] for i in range(6)}
        # 6 pinos isolados = 6 nós sintéticos distintos
        assert len(names) == 6


# ---------------------------------------------------------------------------
# Bridge to_atp
# ---------------------------------------------------------------------------


class TestBridgeVCB1:

    def test_vcb1_emits_single_switch_with_vcb_flag(self):
        proj = PpProject()
        proj.components = [_make_vcb1(name="B1", x=100, y=100)]
        atp = to_atp(proj)
        assert len(atp.switches) == 1
        sw = atp.switches[0]
        assert sw.switch_type == "VCB"
        assert sw.semantic_type == "vcb"

    def test_vcb1_uses_tprops_for_open_close(self):
        proj = PpProject()
        c = _make_vcb1(name="B1", x=100, y=100)
        c.properties[0].value = "25e-3"   # T_open
        c.properties[1].value = "1000"    # T_close
        proj.components = [c]
        atp = to_atp(proj)
        sw = atp.switches[0]
        assert "0.025" in sw.t_open or "25" in sw.t_open
        assert "1000" in sw.t_close

    def test_vcb1_reignition_params_add_warning(self):
        """v0.22.1: VCB com reignição CUSTOMIZADA (≠ defaults CIGRE) emite
        warning sobre a emissão MODEL + wiring TACS manual.

        Antes de v0.22.1, o warning era emitido mesmo com defaults (porque
        os params estavam "reservados mas não emitidos"). Agora, com a
        emissão efetiva do bloco /MODELS, o warning só aparece quando o
        usuário realmente customizou algum parâmetro.
        """
        proj = PpProject()
        # Customiza I_chop (slot 2): default "5" → "8" ativa o MODEL.
        props = ["0", "1e9", "8", "1", "16", "0.034", "17", "0.69e3", "5e-4", "1"]
        c = PpComponent(
            type="VCB", name="B1", visible=True,
            x=100, y=100, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty(value=v, visible=True) for v in props],
        )
        proj.components = [c]
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "VCB" in joined
        assert "reignição" in joined.lower() or "reignicao" in joined.lower()

    def test_vcb1_without_reignition_props_has_no_warning(self):
        """Apenas T_open/T_close preenchidos → sem warning de reignição."""
        proj = PpProject()
        c = PpComponent(
            type="VCB", name="B1", visible=True,
            x=100, y=100, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[
                PpProperty(value="0",    visible=True),
                PpProperty(value="1e9",  visible=True),
                # Slots 2-9 ausentes
            ],
        )
        proj.components = [c]
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "reignição" not in joined.lower()


class TestBridgeVCB3:

    def test_vcb3_emits_three_switches(self):
        proj = PpProject()
        proj.components = [_make_vcb3(name="B1", x=100, y=100)]
        atp = to_atp(proj)
        assert len(atp.switches) == 3

    def test_all_three_switches_have_vcb_flag(self):
        proj = PpProject()
        proj.components = [_make_vcb3(name="B1", x=100, y=100)]
        atp = to_atp(proj)
        for sw in atp.switches:
            assert sw.switch_type == "VCB"

    def test_three_phases_have_distinct_semantic_types(self):
        proj = PpProject()
        proj.components = [_make_vcb3(name="B1", x=100, y=100)]
        atp = to_atp(proj)
        semantics = {sw.semantic_type for sw in atp.switches}
        assert semantics == {"vcb_3ph_A", "vcb_3ph_B", "vcb_3ph_C"}

    def test_independent_topen_per_phase(self):
        """Fases A/B/C podem ter T_open diferentes (staggered pole)."""
        proj = PpProject()
        c = _make_vcb3(name="B1", x=100, y=100)
        c.properties[0].value = "10e-3"   # T_open_A
        c.properties[2].value = "11e-3"   # T_open_B
        c.properties[4].value = "12e-3"   # T_open_C
        proj.components = [c]
        atp = to_atp(proj)
        # Mapeia ordem das fases pela semantic_type
        by_phase = {sw.semantic_type: sw for sw in atp.switches}
        # Topen_A ≈ 0.010, Topen_B ≈ 0.011, Topen_C ≈ 0.012
        assert "0.01" in by_phase["vcb_3ph_A"].t_open
        assert "0.011" in by_phase["vcb_3ph_B"].t_open
        assert "0.012" in by_phase["vcb_3ph_C"].t_open

    def test_pins_map_to_correct_nodes(self):
        """
        Cada SWITCH gerado deve ter node1/node2 correspondendo
        à fase correta (in/out). Testamos via conectividade.
        """
        proj = PpProject()
        proj.components = [
            _make_vcb3(name="B1", x=100, y=100),
            # Resistor ligado na fase B (out) para referenciar o nó
            PpComponent(
                type="R", name="R1", visible=True,
                x=200, y=100, label_dx=0, label_dy=0, mirror=0, rotation=1,
                properties=[PpProperty(value="100", visible=True)],
            ),
        ]
        # Conecta: B1 pino 3 (B_out em (140, 100)) → R1 pino esquerdo
        # R1 @ (200,100) rotation=1: pinos em (230,100) e (170,100)
        #   — o pino esquerdo (170,100) é o índice 1 (após rotação).
        proj.wires = [
            PpWire(x1=140, y1=100, x2=170, y2=100),
        ]
        atp = to_atp(proj)
        by_phase = {sw.semantic_type: sw for sw in atp.switches}
        r1 = atp.branches[0]
        # A fase B_out (switch vcb_3ph_B.node2) deve casar com algum
        # nó do R1 (o pino rotacionado conectado pelo wire).
        r1_nodes = {r1.node1, r1.node2}
        assert by_phase["vcb_3ph_B"].node2 in r1_nodes
        assert by_phase["vcb_3ph_B"].node2 != ""   # não é ground
        # Fases A e C NÃO se conectam ao R1 (nós independentes)
        assert by_phase["vcb_3ph_A"].node2 not in r1_nodes
        assert by_phase["vcb_3ph_C"].node2 not in r1_nodes

    def test_vcb3_reignition_warning_emitted(self):
        """v0.22.1: VCB3 com reignição CUSTOMIZADA emite warning sobre
        emissão MODEL + wiring TACS manual (ver rationale em
        test_vcb1_reignition_params_add_warning)."""
        proj = PpProject()
        # Customiza I_chop (slot 6 no VCB3): default "5" → "8" ativa MODEL.
        props = [
            "50e-3", "1e9", "50e-3", "1e9", "50e-3", "1e9",
            "8",  # I_chop customizado
            "1", "16", "0.034", "17", "0.69e3", "5e-4", "1",
        ]
        c = PpComponent(
            type="VCB3", name="B1", visible=True,
            x=100, y=100, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty(value=v, visible=True) for v in props],
        )
        proj.components = [c]
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "VCB3" in joined
        assert "reignição" in joined.lower() or "reignicao" in joined.lower()

    def test_vcb3_ignored_when_no_reignition_props(self):
        """VCB3 só com Topen/Tclose → sem warning de reignição."""
        proj = PpProject()
        c = PpComponent(
            type="VCB3", name="B1", visible=True,
            x=100, y=100, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty(value="0.05", visible=True)] * 6,
        )
        proj.components = [c]
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "reignição" not in joined.lower()

    def test_vcb3_does_not_pollute_branch_or_source_lists(self):
        proj = PpProject()
        proj.components = [_make_vcb3(name="B1", x=100, y=100)]
        atp = to_atp(proj)
        assert atp.branches == []
        assert atp.sources == []


# ---------------------------------------------------------------------------
# Renderer: VCB3PhaseSymbol
# ---------------------------------------------------------------------------


def _paint_offscreen(renderer):
    img = QImage(200, 200, QImage.Format_ARGB32)
    img.fill(Qt.white)
    p = QPainter(img)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.translate(100, 100)
        renderer.paint(p)
    finally:
        p.end()
    return img


class TestVCB3Renderer:

    def test_registered_in_registry(self, qapp):
        reg = all_renderers()
        assert "VCB3" in reg

    def test_get_renderer_returns_instance(self, qapp):
        r = get_renderer("VCB3")
        assert isinstance(r, VCB3PhaseSymbol)

    def test_has_six_pins(self, qapp):
        pins = VCB3PhaseSymbol().pin_positions()
        assert len(pins) == 6

    def test_pins_match_node_coalescer(self, qapp):
        # Consistência crítica: se symbols e node_coalescer divergirem,
        # o pino desenhado não cai sobre o nó elétrico calculado.
        assert VCB3PhaseSymbol().pin_positions() == _PIN_GEOMETRY["VCB3"]

    def test_bounding_rect_contains_all_pins(self, qapp):
        r = VCB3PhaseSymbol()
        br = r.bounding_rect()
        for (px, py) in r.pin_positions():
            assert br.left() <= px <= br.right(), f"pino ({px},{py}) fora da BR"
            assert br.top() <= py <= br.bottom()

    def test_paint_does_not_raise(self, qapp):
        img = _paint_offscreen(VCB3PhaseSymbol())
        # Algum pixel central deve estar pintado
        found_ink = False
        for dx in range(-30, 31, 2):
            for dy in range(-30, 31, 2):
                px = img.pixelColor(100 + dx, 100 + dy)
                if px.red() < 250 or px.green() < 250 or px.blue() < 250:
                    found_ink = True
                    break
            if found_ink:
                break
        assert found_ink, "VCB3 paint() não deixou traço visível"

    def test_bounding_rect_wider_than_singlephase(self, qapp):
        v1 = get_renderer("VCB")
        v3 = get_renderer("VCB3")
        # O 3φ é mais alto que o 1φ (empilha 3 chaves)
        assert v3.bounding_rect().height() > v1.bounding_rect().height()


# ---------------------------------------------------------------------------
# Editor / UI integration
# ---------------------------------------------------------------------------


class TestEditorVCB3:

    def test_add_vcb3_via_editor(self, qapp):
        e = PpEditor()
        e.add_component_by_type("VCB3")
        # 1 componente adicionado
        items = e.scene.component_items()
        assert len(items) == 1
        c = items[0].component
        assert c.type == "VCB3"

    def test_vcb3_has_14_default_properties(self, qapp):
        e = PpEditor()
        e.add_component_by_type("VCB3")
        c = e.scene.component_items()[0].component
        assert len(c.properties) == 14

    def test_vcb1_has_10_default_properties(self, qapp):
        e = PpEditor()
        e.add_component_by_type("VCB")
        c = e.scene.component_items()[0].component
        assert len(c.properties) == 10

    def test_vcb3_default_values_are_reasonable(self, qapp):
        e = PpEditor()
        e.add_component_by_type("VCB3")
        c = e.scene.component_items()[0].component
        # Topen das 3 fases idêntico por default (50 ms = 0.05 s)
        assert c.properties[0].value == c.properties[2].value
        assert c.properties[2].value == c.properties[4].value
        # v0.24.1: defaults agora vêm do spec (floats) em vez das
        # strings SI legacy. Verificamos o valor numérico
        # equivalente a 50 ms (= 0.05 s).
        assert float(c.properties[0].value) == pytest.approx(0.05)


class TestPropertyPanelVCB3:

    def _iter_form_labels(self, panel) -> list[str]:
        """
        Extrai os textos dos QLabel de rótulo das QFormLayout do
        painel — ignora campos de edição.

        v0.22.2: o painel rico usa groupboxes por PropertyGroup
        (Timing/Reignição/etc.) em vez do antigo "Propriedades".
        v0.22.3: os groupboxes ficaram colapsíveis — QFormLayout
        agora está dentro de um content widget filho, não mais no
        QGroupBox direto. Usa ``findChildren(QFormLayout)`` para
        encontrar qualquer QFormLayout dentro do groupbox.
        """
        labels: list[str] = []
        root = panel.widget()
        if root is None:
            return labels
        for group in root.findChildren(QGroupBox):
            if group.title() == "Identificação":
                continue
            for form in group.findChildren(QFormLayout):
                for row in range(form.rowCount()):
                    label_item = form.itemAt(row, QFormLayout.LabelRole)
                    if label_item is None:
                        continue
                    w = label_item.widget()
                    if isinstance(w, QLabel):
                        labels.append(w.text())
        return labels

    def test_panel_uses_human_labels_for_vcb3(self, qapp):
        """
        v0.22.2: o painel rico deriva labels do ``spec.properties[i].label``
        (em VCB3.ocomp: "T_open A", "T_close A", "I_chop" — com espaço
        em vez de underscore, mais legível). Antes o teste assumia
        labels com underscore (da legacy ``_PROPERTY_LABELS``).
        """
        panel = PpPropertiesPanel()
        c = _make_vcb3(name="B1", x=100, y=100)
        item = ComponentItem(c)
        panel.bind_component(item)
        labels = self._iter_form_labels(panel)
        label_blob = " | ".join(labels)
        # Labels do novo painel rico (spec.label + " [" + unit + "]:"):
        assert "T_open A" in label_blob or "T_open_A" in label_blob
        assert "T_close A" in label_blob or "T_close_A" in label_blob
        assert "I_chop" in label_blob

    def test_panel_shows_numeric_fallback_for_typeless(self, qapp):
        """
        Componente com type inexistente cai em labels genéricos "#N:".
        Garante que o fallback continua operacional.
        """
        panel = PpPropertiesPanel()
        c = PpComponent(
            type="XYZ_NAO_EXISTE", name="?", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty(value="a", visible=True),
                        PpProperty(value="b", visible=True)],
        )
        item = ComponentItem(c)
        panel.bind_component(item)
        labels = self._iter_form_labels(panel)
        # Fallback: "#1:" e "#2:"
        assert "#1:" in labels
        assert "#2:" in labels

    def test_edit_topen_a_updates_component(self, qapp):
        panel = PpPropertiesPanel()
        c = _make_vcb3(name="B1")
        item = ComponentItem(c)
        panel.bind_component(item)
        panel._on_prop_changed(0, "25e-3")
        assert c.properties[0].value == "25e-3"

    def test_edit_seed_updates_component(self, qapp):
        """Slot 13 (Seed) é o último — garante que ainda é editável."""
        panel = PpPropertiesPanel()
        c = _make_vcb3(name="B1")
        item = ComponentItem(c)
        panel.bind_component(item)
        panel._on_prop_changed(13, "42")
        assert c.properties[13].value == "42"
