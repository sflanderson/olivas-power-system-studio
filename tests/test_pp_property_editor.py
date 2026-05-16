"""
tests/test_pp_property_editor.py — v0.22.2: painel rico de edição
de propriedades baseado em ``.ocomp`` schema.

Cobre:

* ``make_value_editor``: widget factory por ``PropertyType``.
    FLOAT → QDoubleSpinBox (com min/max/unit suffix)
    INT   → QSpinBox
    BOOL  → QCheckBox
    ENUM  → QComboBox (items de ``spec.choices``)
    FILE  → container com QLineEdit + browse button
    EXPRESSION → QLineEdit monospace
    STRING → QLineEdit

* ``PropertyRow``: linha completa (editor + visible checkbox + restore).
    - value_changed emite (idx, value, visible).
    - Botão restore reseta para ``spec.default``.

* ``PropertyGroupBox``: QGroupBox com várias PropertyRow.

* ``ComponentPropertyDialog``: construção (sem exec — evita bloqueio
    em CI headless).

* Integração em ``PpPropertiesPanel.bind_component``: painel rico
    quando há spec; fallback QLineEdit quando não há.

* ``_on_row_changed`` propaga valor E visibility para PpProperty.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QSpinBox,
)

from app.gui.schematic_pp.editor import PpEditor, PpPropertiesPanel
from app.gui.schematic_pp.items import ComponentItem
from app.gui.schematic_pp.property_editor import (
    ComponentPropertyDialog,
    PropertyGroupBox,
    PropertyRow,
    _parse_float_lenient,
    build_property_rows,
    make_value_editor,
    resolve_spec,
)
from app.preprocessor.models import PpComponent, PpProperty
from app.preprocessor.spec import (
    PropertyGroup,
    PropertySpec,
    PropertyType,
)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


# ---------------------------------------------------------------------------
# Widget factory por tipo
# ---------------------------------------------------------------------------


class TestWidgetFactory:
    def test_float_returns_doublespinbox(self, qapp):
        ps = PropertySpec(
            name="R", label="R", unit="ohm", type=PropertyType.FLOAT,
            default=1000.0, min=0.0, max=1.0e6,
        )
        w, get_v, _ = make_value_editor(ps, "1000")
        assert isinstance(w, QDoubleSpinBox)
        assert w.minimum() == 0.0
        assert w.maximum() == 1.0e6
        assert " ohm" in w.suffix()
        # get_v retorna string compatível com PpProperty.value
        assert float(get_v()) == 1000.0

    def test_float_accepts_SI_prefix_lenient(self, qapp):
        ps = PropertySpec(
            name="L", label="L", unit="H", type=PropertyType.FLOAT,
            default=0.001,
        )
        w, get_v, _ = make_value_editor(ps, "1k")  # 1k = 1000
        assert isinstance(w, QDoubleSpinBox)
        assert float(get_v()) == 1000.0

    def test_float_fallback_to_default_on_invalid(self, qapp):
        ps = PropertySpec(
            name="L", label="L", type=PropertyType.FLOAT, default=2.5,
        )
        w, get_v, _ = make_value_editor(ps, "not-a-number")
        assert float(get_v()) == 2.5

    def test_int_returns_spinbox(self, qapp):
        ps = PropertySpec(
            name="Seed", label="Seed", type=PropertyType.INT,
            default=1, min=0, max=9999,
        )
        w, get_v, _ = make_value_editor(ps, "42")
        assert isinstance(w, QSpinBox)
        assert w.minimum() == 0
        assert w.maximum() == 9999
        assert int(get_v()) == 42

    def test_bool_returns_checkbox(self, qapp):
        ps = PropertySpec(
            name="flag", label="Flag", type=PropertyType.BOOL, default=False,
        )
        w, get_v, _ = make_value_editor(ps, "true")
        assert isinstance(w, QCheckBox)
        assert w.isChecked() is True
        assert get_v() == "true"
        w.setChecked(False)
        assert get_v() == "false"

    def test_enum_returns_combobox(self, qapp):
        ps = PropertySpec(
            name="polarity", label="Polarity", type=PropertyType.ENUM,
            default="neutral", choices=["neutral", "polarized"],
        )
        w, get_v, _ = make_value_editor(ps, "polarized")
        assert isinstance(w, QComboBox)
        assert w.count() == 2
        assert w.currentText() == "polarized"

    def test_enum_falls_back_to_default_on_unknown_value(self, qapp):
        ps = PropertySpec(
            name="mode", label="Mode", type=PropertyType.ENUM,
            default="a", choices=["a", "b", "c"],
        )
        w, get_v, _ = make_value_editor(ps, "z")  # valor fora das choices
        assert isinstance(w, QComboBox)
        # Cai no default "a"
        assert w.currentText() == "a"

    def test_file_returns_container_with_lineedit(self, qapp):
        ps = PropertySpec(
            name="lookup", label="Lookup table", type=PropertyType.FILE,
            default="default.dat",
        )
        w, get_v, _ = make_value_editor(ps, "my_file.dat")
        # Container com QLineEdit + botão "…"
        line_edits = w.findChildren(QLineEdit)
        assert len(line_edits) == 1
        assert get_v() == "my_file.dat"

    def test_string_returns_lineedit(self, qapp):
        ps = PropertySpec(
            name="desc", label="Desc", type=PropertyType.STRING,
            default="hello",
        )
        w, get_v, _ = make_value_editor(ps, "world")
        assert isinstance(w, QLineEdit)
        assert get_v() == "world"

    def test_expression_returns_monospace_lineedit(self, qapp):
        ps = PropertySpec(
            name="eq", label="Eq", type=PropertyType.EXPRESSION,
            default="f(t)",
        )
        w, get_v, _ = make_value_editor(ps, "sin(wt)")
        assert isinstance(w, QLineEdit)
        # Fonte monospace
        font = w.font()
        families = font.family().lower()
        # Aceita Consolas ou Courier (Qt resolve no SO)
        assert "consol" in families or "courier" in families or "mono" in families


# ---------------------------------------------------------------------------
# Parse SI helper
# ---------------------------------------------------------------------------


class TestParseFloatLenient:
    @pytest.mark.parametrize("text,expected", [
        ("1", 1.0),
        ("1.5", 1.5),
        ("1e3", 1000.0),
        ("1k", 1000.0),
        ("1 k", 1000.0),
        ("1m", 1e-3),
        ("1u", 1e-6),
        ("1µ", 1e-6),
        ("1M", 1e6),
        ("", 0.0),
    ])
    def test_accepts_various_forms(self, text, expected):
        assert _parse_float_lenient(text) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# PropertyRow
# ---------------------------------------------------------------------------


class TestPropertyRow:
    def _ps(self, **kw) -> PropertySpec:
        defaults = dict(
            name="R", label="R", unit="ohm", type=PropertyType.FLOAT,
            default=1000.0, visible=True, group=PropertyGroup.MAIN,
        )
        defaults.update(kw)
        return PropertySpec(**defaults)

    def test_label_text_includes_unit(self, qapp):
        row = PropertyRow(0, self._ps(), "1000", True)
        assert row.label_text == "R [ohm]"

    def test_label_text_without_unit(self, qapp):
        row = PropertyRow(0, self._ps(unit=""), "1000", True)
        assert row.label_text == "R"

    def test_value_changed_signal_on_edit(self, qapp):
        ps = self._ps()
        row = PropertyRow(3, ps, "1000", True)
        captured = []
        row.value_changed.connect(lambda i, v, vis: captured.append((i, v, vis)))
        # Simula edição via _emit_changed (sem evento Qt real)
        row._emit_changed()
        assert captured
        idx, v, vis = captured[-1]
        assert idx == 3
        assert float(v) == 1000.0
        assert vis is True

    def test_visibility_toggle_emits_signal(self, qapp):
        ps = self._ps()
        row = PropertyRow(0, ps, "1000", True)
        captured = []
        row.value_changed.connect(lambda i, v, vis: captured.append((i, v, vis)))
        row._vis.setChecked(False)  # toggle
        # setChecked dispara toggled que chama _emit_changed
        assert captured
        assert captured[-1][2] is False


# ---------------------------------------------------------------------------
# build_property_rows
# ---------------------------------------------------------------------------


class TestBuildPropertyRows:
    def test_returns_rows_grouped(self, qapp):
        spec = resolve_spec("VCB")
        comp = PpComponent(
            type="VCB", name="DJ1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty(str(p.default)) for p in spec.properties],
        )
        rows = build_property_rows(spec, comp)
        # VCB tem 10 props: 2 timing + 8 reignition
        timing = rows.get(PropertyGroup.TIMING, [])
        reignition = rows.get(PropertyGroup.REIGNITION, [])
        assert len(timing) == 2  # T_open, T_close
        assert len(reignition) == 8  # I_chop, sigma, di/dt, d(di/dt), k, U0, T_bounce, Seed


# ---------------------------------------------------------------------------
# PropertyGroupBox colapsível (v0.22.3)
# ---------------------------------------------------------------------------


class TestPropertyGroupBoxCollapsible:
    """Groupbox é checkable; ADVANCED e METADATA começam recolhidos."""

    def _make_row(self, qapp):
        from app.preprocessor.spec import PropertySpec, PropertyType
        ps = PropertySpec(
            name="R", label="R", unit="ohm", type=PropertyType.FLOAT,
            default=1000.0,
        )
        from app.gui.schematic_pp.property_editor import PropertyRow
        return PropertyRow(0, ps, "1000", True)

    def test_main_group_starts_expanded(self, qapp):
        from app.gui.schematic_pp.property_editor import PropertyGroupBox
        box = PropertyGroupBox(PropertyGroup.MAIN, [self._make_row(qapp)])
        assert box.isCheckable()
        assert box.is_expanded() is True
        assert not box._content.isHidden()

    def test_advanced_group_starts_collapsed(self, qapp):
        from app.gui.schematic_pp.property_editor import PropertyGroupBox
        box = PropertyGroupBox(PropertyGroup.ADVANCED, [self._make_row(qapp)])
        assert box.is_expanded() is False
        assert box._content.isHidden()

    def test_metadata_group_starts_collapsed(self, qapp):
        from app.gui.schematic_pp.property_editor import PropertyGroupBox
        box = PropertyGroupBox(PropertyGroup.METADATA, [self._make_row(qapp)])
        assert box.is_expanded() is False
        assert box._content.isHidden()

    def test_timing_group_starts_expanded(self, qapp):
        """Timing não está na lista default-collapsed — expandido."""
        from app.gui.schematic_pp.property_editor import PropertyGroupBox
        box = PropertyGroupBox(PropertyGroup.TIMING, [self._make_row(qapp)])
        assert box.is_expanded() is True

    def test_reignition_group_starts_expanded(self, qapp):
        """Reignição é relevante no doutorado — não começa recolhido."""
        from app.gui.schematic_pp.property_editor import PropertyGroupBox
        box = PropertyGroupBox(PropertyGroup.REIGNITION, [self._make_row(qapp)])
        assert box.is_expanded() is True

    def test_toggle_check_shows_hides_content(self, qapp):
        from app.gui.schematic_pp.property_editor import PropertyGroupBox
        box = PropertyGroupBox(PropertyGroup.ADVANCED, [self._make_row(qapp)])
        assert box._content.isHidden()
        box.setChecked(True)  # expand
        assert not box._content.isHidden()
        box.setChecked(False)  # collapse again
        assert box._content.isHidden()

    def test_explicit_collapsed_override(self, qapp):
        """Passar collapsed=True em group normalmente expandido."""
        from app.gui.schematic_pp.property_editor import PropertyGroupBox
        box = PropertyGroupBox(
            PropertyGroup.MAIN, [self._make_row(qapp)], collapsed=True,
        )
        assert box.is_expanded() is False

    def test_explicit_expanded_override(self, qapp):
        """Passar collapsed=False em group normalmente recolhido."""
        from app.gui.schematic_pp.property_editor import PropertyGroupBox
        box = PropertyGroupBox(
            PropertyGroup.ADVANCED, [self._make_row(qapp)], collapsed=False,
        )
        assert box.is_expanded() is True

    def test_row_signals_still_propagate_when_collapsed(self, qapp):
        """Mesmo com groupbox recolhido, edições das rows propagam."""
        from app.gui.schematic_pp.property_editor import PropertyGroupBox
        row = self._make_row(qapp)
        box = PropertyGroupBox(PropertyGroup.ADVANCED, [row])
        captured = []
        box.row_changed.connect(lambda i, v, vis: captured.append((i, v, vis)))
        # Simula mudança do row (independente de visibilidade)
        row._emit_changed()
        assert captured  # sinal propaga mesmo com content escondido


# ---------------------------------------------------------------------------
# ComponentPropertyDialog (smoke — sem exec)
# ---------------------------------------------------------------------------


class TestComponentPropertyDialog:
    def test_construction_for_vcb(self, qapp):
        spec = resolve_spec("VCB")
        comp = PpComponent(
            type="VCB", name="DJ1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty(str(p.default)) for p in spec.properties],
        )
        dlg = ComponentPropertyDialog(spec, comp)
        assert "VCB" in dlg.windowTitle() or "Disjuntor" in dlg.windowTitle()
        # Contém os dois tabs
        tabs = dlg.findChild(type(dlg).__mro__[0])  # QDialog subclass
        # Busca QTabWidget
        from PySide6.QtWidgets import QTabWidget
        tabwidget = dlg.findChild(QTabWidget)
        assert tabwidget is not None
        assert tabwidget.count() == 2  # Parâmetros + Descrição
        assert tabwidget.tabText(0) == "Parâmetros"
        assert tabwidget.tabText(1) == "Descrição"

    def test_description_tab_renders_llm_hints(self, qapp):
        spec = resolve_spec("VCB")
        comp = PpComponent(
            type="VCB", name="DJ1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[],
        )
        dlg = ComponentPropertyDialog(spec, comp)
        html = dlg._build_description_html()
        # Deve conter pelo menos uma referência CIGRE e uma aplicação típica
        assert "CIGRE" in html or "cigre" in html.lower()
        assert "Aplicações típicas" in html


# ---------------------------------------------------------------------------
# Integração em PpPropertiesPanel (painel rico vs fallback)
# ---------------------------------------------------------------------------


class TestPpPropertiesPanelIntegration:
    def test_rich_panel_for_vcb(self, qapp):
        ed = PpEditor()
        ed.add_component_by_type("VCB")
        item = [i for i in ed.scene.items() if isinstance(i, ComponentItem)][0]
        ed.properties.bind_component(item)
        # Painel rico deve conter pelo menos um QDoubleSpinBox (T_open)
        dspin = ed.properties.findChild(QDoubleSpinBox)
        assert dspin is not None, (
            "Painel não está usando o novo widget factory — nenhum "
            "QDoubleSpinBox encontrado."
        )

    def test_on_row_changed_updates_value(self, qapp):
        ed = PpEditor()
        ed.add_component_by_type("VCB")
        item = [i for i in ed.scene.items() if isinstance(i, ComponentItem)][0]
        ed.properties.bind_component(item)
        # Edita I_chop (index 2)
        original = item.component.properties[2].value
        ed.properties._on_row_changed(2, "8.5", True)
        assert item.component.properties[2].value == "8.5"
        assert original != "8.5"

    def test_on_row_changed_toggles_visibility(self, qapp):
        ed = PpEditor()
        ed.add_component_by_type("VCB")
        item = [i for i in ed.scene.items() if isinstance(i, ComponentItem)][0]
        ed.properties.bind_component(item)
        original_vis = item.component.properties[0].visible
        # Toggle visibility (sem mudar value)
        ed.properties._on_row_changed(0, item.component.properties[0].value, not original_vis)
        assert item.component.properties[0].visible == (not original_vis)

    def test_fallback_for_component_without_spec(self, qapp):
        """Se um componente não tem .ocomp, painel cai em QLineEdit legacy."""
        # Após v0.22.0, todos os 40 códigos têm .ocomp. Criamos um
        # componente com type="XYZ" inexistente.
        comp = PpComponent(
            type="XYZ_UNKNOWN", name="X1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("42")],
        )
        item = ComponentItem(comp)
        panel = PpPropertiesPanel()
        panel.bind_component(item)
        # Painel cai no fallback QLineEdit (sem QDoubleSpinBox)
        assert panel.findChild(QDoubleSpinBox) is None
        assert panel.findChild(QLineEdit) is not None
