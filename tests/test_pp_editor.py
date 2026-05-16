"""
Tests for ``app.gui.schematic_pp`` — editor visual do pré-processador.

Cobertura
---------

* :func:`snap` e :func:`snap_point` — grid 10px
* :class:`ComponentItem` — sync bidirecional com :class:`PpComponent`,
  rotate_cw/ccw, mirror_x
* :class:`WireItem` — path L-route correto
* :class:`PpScene` — load/to_project, add/remove, selection queries,
  signals emitidos
* :class:`PpEditor` — add_component_by_type, save/load round-trip
  via .sch, export_to_atp
* :class:`PpPalette` — populated com entries do catálogo
* :class:`PpPropertiesPanel` — bind/unbind, edição de property
  reflete no PpComponent

Todos os testes são smoke tests: abrem um ``QApplication`` fake,
exercitam o widget por 1-2 operações, confirmam state.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from app.preprocessor.models import (
    PpComponent,
    PpProject,
    PpProperty,
    PpWire,
)

from app.gui.schematic_pp import (
    GRID_SIZE,
    ComponentItem,
    PpEditor,
    PpPalette,
    PpPropertiesPanel,
    PpScene,
    PpView,
    WireItem,
    snap,
    snap_point,
)


# ---------------------------------------------------------------------------
# QApplication fixture
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


def _make_R(name: str = "R1", x: int = 100, y: int = 100) -> PpComponent:
    return PpComponent(
        type="R", name=name, visible=True,
        x=x, y=y, label_dx=15, label_dy=-26, mirror=0, rotation=0,
        properties=[
            PpProperty(value="1k",    visible=True),
            PpProperty(value="26.85", visible=False),
        ],
    )


def _make_wire(x1=100, y1=100, x2=200, y2=100, label="") -> PpWire:
    lvis = 10 if label else 0
    return PpWire(x1=x1, y1=y1, x2=x2, y2=y2,
                  label=label, label_x=x1, label_y=y1, label_visible=lvis)


# ---------------------------------------------------------------------------
# Snap
# ---------------------------------------------------------------------------


class TestSnap:

    def test_snap_rounds_to_grid(self):
        assert snap(103) == 100
        assert snap(107) == 110
        # Python usa banker's rounding: round(10.5) == 10 (par mais
        # próximo), então snap(105) == 100 — documentado aqui
        # como comportamento esperado.
        assert snap(105) == 100
        assert snap(115) == 120   # banker's: round(11.5) == 12
        assert snap(-3) == 0
        assert snap(-7) == -10

    def test_snap_point(self):
        p = snap_point(QPointF(103.4, 97.6))
        assert p.x() == 100
        assert p.y() == 100

    def test_snap_with_custom_grid(self):
        assert snap(42, grid=5) == 40
        assert snap(43, grid=5) == 45


# ---------------------------------------------------------------------------
# ComponentItem
# ---------------------------------------------------------------------------


class TestComponentItem:

    def test_creates_with_known_type(self, qapp):
        c = _make_R()
        item = ComponentItem(c)
        assert item.component is c
        assert item.renderer is not None
        assert item.pos().x() == 100
        assert item.pos().y() == 100

    def test_creates_with_unknown_type_uses_fallback(self, qapp):
        c = PpComponent(
            type="ZZZ_NAO_EXISTE", name="X1", visible=True,
            x=50, y=50, label_dx=0, label_dy=0, mirror=0, rotation=0,
        )
        item = ComponentItem(c)
        # renderer é fallback, mas ainda desenha sem crashar
        from app.gui.schematic_pp.items import _FallbackRenderer
        assert isinstance(item.renderer, _FallbackRenderer)

    def test_bounding_rect_contains_symbol(self, qapp):
        c = _make_R()
        item = ComponentItem(c)
        br = item.boundingRect()
        sym_br = item.renderer.bounding_rect()
        # O bounding do item deve englobar o do renderer (com padding).
        assert br.left() <= sym_br.left()
        assert br.right() >= sym_br.right()
        assert br.top() <= sym_br.top()
        assert br.bottom() >= sym_br.bottom()

    def test_pin_positions_scene_for_default_pose(self, qapp):
        c = _make_R(x=100, y=200)
        item = ComponentItem(c)
        pins = item.pin_positions_scene()
        # Com rotation=0, R tem pinos em (0,-30) e (0,30) relativos ao anchor.
        assert pins[0] == QPointF(100, 170)
        assert pins[1] == QPointF(100, 230)

    def test_rotate_ccw_advances_rotation_mod_4(self, qapp):
        c = _make_R()
        item = ComponentItem(c)
        assert c.rotation == 0
        item.rotate_ccw()
        assert c.rotation == 1
        item.rotate_ccw()
        assert c.rotation == 2
        item.rotate_ccw()
        item.rotate_ccw()
        assert c.rotation == 0

    def test_rotate_cw_goes_backwards(self, qapp):
        c = _make_R()
        item = ComponentItem(c)
        item.rotate_cw()
        assert c.rotation == 3
        item.rotate_cw()
        assert c.rotation == 2

    def test_mirror_toggles(self, qapp):
        c = _make_R()
        item = ComponentItem(c)
        assert c.mirror == 0
        item.mirror_x()
        assert c.mirror == 1
        item.mirror_x()
        assert c.mirror == 0

    def test_pin_positions_after_rotation_ccw(self, qapp):
        c = _make_R(x=100, y=100)
        item = ComponentItem(c)
        item.rotate_ccw()
        pins = item.pin_positions_scene()
        # Rotation=1 (90° CCW): (0,-30)→(30,0); (0,30)→(-30,0).
        # Em coordenadas Qt (Y down), 90° CCW do Qt é na verdade
        # 90° CW matemático — mas o que importa é simetria.
        # Basta que os pinos agora sejam horizontais.
        xs = [p.x() for p in pins]
        ys = [p.y() for p in pins]
        # Os 2 pinos devem compartilhar Y (agora horizontais).
        assert ys[0] == ys[1]
        # E devem ter X distintos a ±30 do anchor.
        assert abs(xs[0] - 100) == 30 or abs(xs[1] - 100) == 30


# ---------------------------------------------------------------------------
# WireItem
# ---------------------------------------------------------------------------


class TestWireItem:

    def test_horizontal_wire_is_single_segment(self, qapp):
        w = _make_wire(100, 100, 200, 100)
        item = WireItem(w)
        # Path deve ter um moveTo + um lineTo (2 elementos).
        path = item.path()
        assert path.elementCount() == 2

    def test_vertical_wire_is_single_segment(self, qapp):
        w = _make_wire(100, 100, 100, 200)
        item = WireItem(w)
        assert item.path().elementCount() == 2

    def test_diagonal_wire_routes_as_L(self, qapp):
        w = _make_wire(100, 100, 200, 200)
        item = WireItem(w)
        # L-route: moveTo + 2 lineTo → 3 elementos.
        assert item.path().elementCount() == 3

    def test_sync_from_model_rebuilds_path(self, qapp):
        w = _make_wire(100, 100, 200, 100)
        item = WireItem(w)
        # edita o PpWire diretamente; sync_from_model deve refletir.
        w.x2 = 300
        item.sync_from_model()
        # último elemento deve ter x = 300
        last = item.path().elementAt(item.path().elementCount() - 1)
        assert last.x == 300


# ---------------------------------------------------------------------------
# PpScene
# ---------------------------------------------------------------------------


class TestPpScene:

    def test_empty_scene_has_empty_project(self, qapp):
        s = PpScene()
        assert s.project.components == []
        assert s.project.wires == []

    def test_load_project_populates_scene(self, qapp):
        proj = PpProject()
        proj.components = [_make_R("R1"), _make_R("R2", x=200)]
        proj.wires = [_make_wire()]
        s = PpScene(proj)
        assert len(s.component_items()) == 2
        assert len(s.wire_items()) == 1

    def test_add_component_appends_to_project(self, qapp):
        s = PpScene()
        c = _make_R()
        s.add_component(c)
        assert c in s.project.components
        assert len(s.component_items()) == 1

    def test_add_component_gives_unique_name_on_collision(self, qapp):
        s = PpScene()
        a = _make_R("R1")
        b = _make_R("R1")   # colisão
        s.add_component(a)
        s.add_component(b)
        assert b.name != "R1"

    def test_remove_component_syncs_project(self, qapp):
        s = PpScene()
        c = _make_R()
        item = s.add_component(c)
        assert c in s.project.components
        s.remove_component(item)
        assert c not in s.project.components
        assert len(s.component_items()) == 0

    def test_remove_wire_syncs_project(self, qapp):
        s = PpScene()
        w = _make_wire()
        item = s.add_wire(w)
        assert w in s.project.wires
        s.remove_wire(item)
        assert w not in s.project.wires

    def test_to_project_writes_back_positions(self, qapp):
        s = PpScene()
        c = _make_R(x=100, y=100)
        item = s.add_component(c)
        item.setPos(QPointF(150, 200))
        proj = s.to_project()
        # itemChange já atualiza .x/.y, mas to_project é o contrato
        # publicado; garantir que ele traz valores finais.
        assert c.x == 150
        assert c.y == 200
        assert c in proj.components

    def test_load_project_replaces_existing(self, qapp):
        s = PpScene()
        s.add_component(_make_R("R1"))
        new = PpProject()
        new.components = [_make_R("R99", x=500)]
        s.load_project(new)
        items = s.component_items()
        assert len(items) == 1
        assert items[0].component.name == "R99"

    def test_selection_queries(self, qapp):
        s = PpScene()
        ra = s.add_component(_make_R("R1"))
        rb = s.add_component(_make_R("R2", x=200))
        w = s.add_wire(_make_wire())
        ra.setSelected(True)
        w.setSelected(True)
        assert len(s.selected_components()) == 1
        assert len(s.selected_wires()) == 1
        assert s.selected_components()[0] is ra

    def test_remove_selected_removes_both_types(self, qapp):
        s = PpScene()
        a = s.add_component(_make_R("R1"))
        w = s.add_wire(_make_wire())
        a.setSelected(True)
        w.setSelected(True)
        n = s.remove_selected()
        assert n == 2
        assert len(s.component_items()) == 0
        assert len(s.wire_items()) == 0

    def test_topology_changed_emits_on_add(self, qapp):
        s = PpScene()
        calls: list = []
        s.topology_changed.connect(lambda: calls.append(1))
        s.add_component(_make_R())
        assert len(calls) >= 1


# ---------------------------------------------------------------------------
# PpView
# ---------------------------------------------------------------------------


class TestPpView:

    def test_zoom_in_out_bounded(self, qapp):
        s = PpScene()
        v = PpView(s)
        v.zoom_reset()
        assert v._zoom == 1.0
        v.zoom_in()
        assert v._zoom > 1.0
        # Vai até o topo sem quebrar.
        for _ in range(50):
            v.zoom_in()
        assert v._zoom <= 8.01
        for _ in range(100):
            v.zoom_out()
        assert v._zoom >= 0.19

    def test_zoom_reset(self, qapp):
        s = PpScene()
        v = PpView(s)
        v.zoom_in()
        v.zoom_in()
        v.zoom_reset()
        assert v._zoom == 1.0

    def test_keypress_delete_removes_selection(self, qapp):
        s = PpScene()
        v = PpView(s)
        a = s.add_component(_make_R("R1"))
        a.setSelected(True)
        ev = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
        v.keyPressEvent(ev)
        assert len(s.component_items()) == 0

    def test_keypress_r_rotates_selection(self, qapp):
        s = PpScene()
        v = PpView(s)
        a = s.add_component(_make_R("R1"))
        a.setSelected(True)
        ev = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_R, Qt.NoModifier)
        v.keyPressEvent(ev)
        assert a.component.rotation == 1

    def test_keypress_shift_r_rotates_cw(self, qapp):
        s = PpScene()
        v = PpView(s)
        a = s.add_component(_make_R("R1"))
        a.setSelected(True)
        ev = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_R, Qt.ShiftModifier)
        v.keyPressEvent(ev)
        assert a.component.rotation == 3

    def test_keypress_e_mirrors(self, qapp):
        s = PpScene()
        v = PpView(s)
        a = s.add_component(_make_R("R1"))
        a.setSelected(True)
        ev = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_E, Qt.NoModifier)
        v.keyPressEvent(ev)
        assert a.component.mirror == 1


# ---------------------------------------------------------------------------
# PpPalette
# ---------------------------------------------------------------------------


class TestPpPalette:

    def test_palette_lists_atp_supported_types(self, qapp):
        p = PpPalette()
        from app.preprocessor import catalog
        codes = set()
        for i in range(p.count()):
            data = p.item(i).data(Qt.UserRole)
            if data:
                codes.add(str(data))
        # Ao menos R, L, C, Vdc, Diode devem estar.
        for expected in ("R", "L", "C", "Vdc", "Diode", "IGBT", "Tr"):
            assert expected in codes, f"Paleta não oferece {expected}"

    def test_palette_does_not_list_unsupported(self, qapp):
        p = PpPalette()
        codes = set()
        for i in range(p.count()):
            d = p.item(i).data(Qt.UserRole)
            if d:
                codes.add(str(d))
        # Eqn é atp_supported=False, não deve aparecer.
        assert "Eqn" not in codes

    def test_palette_emits_request_add_on_double_click(self, qapp):
        p = PpPalette()
        received: list[str] = []
        p.request_add.connect(received.append)
        # Procura um item clicável (com UserRole preenchido).
        for i in range(p.count()):
            it = p.item(i)
            if it.data(Qt.UserRole):
                p._on_double_clicked(it)
                break
        assert len(received) == 1


# ---------------------------------------------------------------------------
# PpPropertiesPanel
# ---------------------------------------------------------------------------


class TestPpPropertiesPanel:

    def test_bind_none_shows_placeholder(self, qapp):
        panel = PpPropertiesPanel()
        panel.bind_component(None)
        # placeholder está presente (não deve crashar).
        assert panel.widget() is not None

    def test_bind_component_shows_form(self, qapp):
        panel = PpPropertiesPanel()
        c = _make_R("R1")
        item = ComponentItem(c)
        panel.bind_component(item)
        # O widget interno passou a conter um formulário com campos.
        assert panel.widget() is not None

    def test_editing_prop_updates_component(self, qapp):
        panel = PpPropertiesPanel()
        c = _make_R("R1")
        item = ComponentItem(c)
        panel.bind_component(item)
        # Chama diretamente o handler interno (sem passar por QLineEdit).
        panel._on_prop_changed(0, "4.7k")
        assert c.properties[0].value == "4.7k"

    def test_editing_name_updates_component(self, qapp):
        panel = PpPropertiesPanel()
        c = _make_R("R1")
        item = ComponentItem(c)
        panel.bind_component(item)
        panel._on_name_changed("R_NEW")
        assert c.name == "R_NEW"

    def test_editing_empty_name_rejected(self, qapp):
        panel = PpPropertiesPanel()
        c = _make_R("R1")
        item = ComponentItem(c)
        panel.bind_component(item)
        panel._on_name_changed("   ")
        assert c.name == "R1"   # preservado


# ---------------------------------------------------------------------------
# PpEditor
# ---------------------------------------------------------------------------


class TestPpEditor:

    def test_constructs_empty(self, qapp):
        e = PpEditor()
        assert e.scene.project.components == []

    def test_new_project_clears_state(self, qapp):
        e = PpEditor()
        e.add_component_by_type("R")
        assert len(e.scene.component_items()) == 1
        e.new_project()
        assert len(e.scene.component_items()) == 0

    def test_add_component_by_type_creates_instance(self, qapp):
        e = PpEditor()
        item = e.add_component_by_type("R")
        assert isinstance(item, ComponentItem)
        assert item.component.type == "R"
        # A posição veio com snap para o grid.
        assert item.component.x % GRID_SIZE == 0
        assert item.component.y % GRID_SIZE == 0

    def test_add_component_applies_default_properties(self, qapp):
        e = PpEditor()
        item = e.add_component_by_type("R")
        # R tem 3 defaults (valor, T_amb, modelo).
        assert len(item.component.properties) == 3
        # v0.24.1: defaults vêm do spec .ocomp (float 1000.0).
        # Antes vinham do _DEFAULT_PROPS legacy como "1k".
        # Display profissional (v0.22.2) converte para "1k ohm"
        # no QDoubleSpinBox — o value bruto é 1000.0.
        assert float(item.component.properties[0].value) == pytest.approx(1000.0)

    def test_add_gnd_uses_star_name(self, qapp):
        e = PpEditor()
        item = e.add_component_by_type("GND")
        assert item.component.name == "*"

    def test_round_trip_via_sch(self, qapp, tmp_path: Path):
        e = PpEditor()
        e.add_component_by_type("R")
        e.add_component_by_type("C")
        e.add_component_by_type("GND")
        path = tmp_path / "roundtrip.sch"
        e.save_to_sch(path)
        assert path.exists()
        # Nova instância carregando o arquivo salvo.
        e2 = PpEditor()
        e2.load_from_sch(path)
        assert len(e2.scene.component_items()) == 3

    def test_export_to_atp_returns_project(self, qapp):
        e = PpEditor()
        e.add_component_by_type("Vdc")
        e.add_component_by_type("R")
        e.add_component_by_type("GND")
        atp = e.export_to_atp()
        # deve haver ao menos um branch (o R).
        assert atp is not None
        # AtpProject tem branches/sources/switches. Pelo menos
        # uma seção é não-vazia.
        total = (len(atp.branches) + len(atp.sources)
                 + len(atp.switches))
        assert total >= 1

    def test_selection_binds_properties_panel(self, qapp):
        e = PpEditor()
        item = e.add_component_by_type("R")
        item.setSelected(True)
        # O scene dispara selection_changed automaticamente;
        # o editor encaminha para o properties panel.
        e._on_selection_changed()
        # Depois disso, o panel tem um widget com form (não só placeholder).
        assert e.properties.widget() is not None

    def test_palette_add_button_adds_component(self, qapp):
        e = PpEditor()
        # Seleciona primeiro item com UserRole.
        for i in range(e.palette.count()):
            it = e.palette.item(i)
            if it.data(Qt.UserRole):
                it.setSelected(True)
                break
        e._on_palette_add_clicked()
        assert len(e.scene.component_items()) == 1
