"""
tests/test_pp_saturation_curve_editor.py — v0.24.3: widget
especializado para edição de curvas de saturação (Type-98).

Cobre:

* Construção com CSV inicial (e sem CSV).
* ``get_value`` retorna CSV válido sincronizado com a tabela.
* ``set_curve`` popula a tabela a partir de SaturationCurve.
* ``set_csv`` popula a partir de string.
* Botões: add row, delete row, aplicar default.
* Validação: monotonicidade → highlight de linhas inválidas.
* Parity com ``parse_csv_curve``: CSV que entra deve sair idêntico
  após round-trip pelo widget (exceto formato).
* Factory integration: ``make_value_editor`` com
  ``widget_hint='saturation_curve'`` retorna o widget certo.
* Integração end-to-end: LNL no editor usa o novo widget.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QTableWidgetItem

from app.gui.schematic_pp.saturation_curve_editor import (
    SaturationCurveEditor,
)
from app.preprocessor.spec import (
    PropertySpec,
    PropertyType,
    get_default_registry,
)
from app.preprocessor.type98 import (
    SaturationCurve,
    SaturationPoint,
    parse_csv_curve,
)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


# ---------------------------------------------------------------------------
# Construção
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_empty_csv_creates_default_empty(self, qapp):
        w = SaturationCurveEditor(initial_csv="")
        # Com CSV vazio, o widget popula 2 linhas (0,0) e (1,1)
        assert w._table.rowCount() == 2

    def test_valid_csv_populates_table(self, qapp):
        w = SaturationCurveEditor(initial_csv="0,0; 1,1; 5,1.1")
        assert w._table.rowCount() == 3

    def test_invalid_csv_falls_back_to_empty_defaults(self, qapp):
        """CSV ruim não deve crashar — widget fica com 2 linhas default."""
        w = SaturationCurveEditor(initial_csv="not,valid;data")
        assert w._table.rowCount() == 2

    def test_custom_units_in_headers(self, qapp):
        w = SaturationCurveEditor(
            initial_csv="0,0; 1,1",
            unit_i="A_pk", unit_psi="Wb",
        )
        # Headers devem refletir as unidades customizadas
        h0 = w._table.horizontalHeaderItem(0).text()
        h1 = w._table.horizontalHeaderItem(1).text()
        assert "A_pk" in h0
        assert "Wb" in h1


# ---------------------------------------------------------------------------
# get_value / round-trip
# ---------------------------------------------------------------------------


class TestGetValue:
    def test_get_value_returns_csv(self, qapp):
        w = SaturationCurveEditor(initial_csv="0,0; 1,0.95; 5,1.05")
        csv = w.get_value()
        # Parse back deve dar mesma curva
        curve = parse_csv_curve(csv)
        assert len(curve.points) == 3
        assert curve.points[0].current == 0.0
        assert curve.points[1].flux == pytest.approx(0.95)

    def test_empty_table_returns_empty_string(self, qapp):
        w = SaturationCurveEditor(initial_csv="0,0; 1,1")
        w._table.setRowCount(0)
        assert w.get_value() == ""

    def test_is_valid_true_for_monotonic_table(self, qapp):
        w = SaturationCurveEditor(initial_csv="0,0; 1,1; 5,1.1")
        assert w.is_valid() is True

    def test_is_valid_false_for_non_monotonic(self, qapp):
        w = SaturationCurveEditor()
        # Força CSV inválido
        w._table.setRowCount(0)
        w._append_row(0.0, 0.0)
        w._append_row(10.0, 1.0)
        w._append_row(5.0, 1.5)  # current decrementou
        assert w.is_valid() is False

    def test_is_valid_false_for_single_row(self, qapp):
        w = SaturationCurveEditor()
        w._table.setRowCount(0)
        w._append_row(0.0, 0.0)
        assert w.is_valid() is False


# ---------------------------------------------------------------------------
# Round-trip com parser CSV
# ---------------------------------------------------------------------------


class TestCsvRoundTrip:
    @pytest.mark.parametrize("csv", [
        "0,0; 1,1",
        "0,0; 1,0.95; 5,1.05",
        "0,0; 1e-3,1e-2; 100,1.5",
    ])
    def test_roundtrip(self, qapp, csv):
        """Widget → CSV → parse deve dar mesmo número de pontos."""
        original = parse_csv_curve(csv)
        w = SaturationCurveEditor(initial_csv=csv)
        serialized = w.get_value()
        rebuilt = parse_csv_curve(serialized)
        assert len(rebuilt.points) == len(original.points)
        for p_orig, p_new in zip(original.points, rebuilt.points):
            assert p_new.current == pytest.approx(p_orig.current)
            assert p_new.flux == pytest.approx(p_orig.flux)


# ---------------------------------------------------------------------------
# set_curve / set_csv
# ---------------------------------------------------------------------------


class TestSetters:
    def test_set_curve_replaces_table(self, qapp):
        w = SaturationCurveEditor(initial_csv="0,0; 1,1")
        assert w._table.rowCount() == 2
        new_curve = SaturationCurve(points=[
            SaturationPoint(0.0, 0.0),
            SaturationPoint(2.0, 1.0),
            SaturationPoint(10.0, 1.2),
            SaturationPoint(100.0, 1.25),
        ])
        w.set_curve(new_curve)
        assert w._table.rowCount() == 4

    def test_set_csv_valid(self, qapp):
        w = SaturationCurveEditor()
        w.set_csv("0,0; 5,1; 50,1.1")
        assert w._table.rowCount() == 3
        assert w.get_value()

    def test_set_csv_invalid_falls_back(self, qapp):
        w = SaturationCurveEditor(initial_csv="0,0; 1,1")
        w.set_csv("garbage; data")
        # Defaulta para 2 linhas vazias
        assert w._table.rowCount() == 2


# ---------------------------------------------------------------------------
# Botões: add / delete / default
# ---------------------------------------------------------------------------


class TestButtons:
    def test_add_row_increases_row_count(self, qapp):
        w = SaturationCurveEditor(initial_csv="0,0; 1,1")
        initial = w._table.rowCount()
        w._on_add_row()
        assert w._table.rowCount() == initial + 1

    def test_delete_row_no_selection_removes_last(self, qapp):
        w = SaturationCurveEditor(initial_csv="0,0; 1,1; 5,1.1")
        initial = w._table.rowCount()
        w._on_delete_row()
        assert w._table.rowCount() == initial - 1

    def test_apply_default_loads_5_points(self, qapp):
        w = SaturationCurveEditor(initial_csv="0,0; 1,1")
        w._on_apply_default()
        assert w._table.rowCount() == 5  # default_saturation_curve tem 5 pontos


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------


class TestSignals:
    def test_value_changed_emits_on_edit(self, qapp):
        w = SaturationCurveEditor(initial_csv="0,0; 1,1")
        captured = []
        w.value_changed.connect(lambda csv: captured.append(csv))
        # Modifica célula programaticamente
        w._table.item(1, w.COL_FLUX).setText("1.5")
        # Depois do setItem, o signal itemChanged deve ter sido emitido
        # → _revalidate → value_changed se válido
        assert captured, "value_changed deveria ter sido emitido"

    def test_invalid_state_emits_when_non_monotonic(self, qapp):
        w = SaturationCurveEditor()
        captured = []
        w.invalid_state.connect(lambda msg: captured.append(msg))
        # Força linha não-monotônica
        w._table.setRowCount(0)
        w._append_row(5.0, 1.0)
        w._append_row(3.0, 0.5)  # current menor — inválido
        w._revalidate()
        assert captured
        assert "monotônico" in captured[-1] or "monotonico" in captured[-1]


# ---------------------------------------------------------------------------
# Factory integration
# ---------------------------------------------------------------------------


class TestFactoryIntegration:
    def test_factory_uses_saturation_editor_when_hint_matches(self, qapp):
        from app.gui.schematic_pp.property_editor import make_value_editor
        ps = PropertySpec(
            name="sat", label="Curva",
            type=PropertyType.STRING, default="",
            widget_hint="saturation_curve",
        )
        widget, get_v, _ = make_value_editor(ps, "0,0; 1,1")
        assert isinstance(widget, SaturationCurveEditor)
        assert get_v() == "0,0; 1,1" or "0" in get_v()

    def test_factory_defaults_when_no_hint(self, qapp):
        """widget_hint=None → QLineEdit legacy para STRING."""
        from app.gui.schematic_pp.property_editor import make_value_editor
        from PySide6.QtWidgets import QLineEdit
        ps = PropertySpec(
            name="s", label="Str",
            type=PropertyType.STRING, default="abc",
        )
        widget, _, _ = make_value_editor(ps, "abc")
        assert isinstance(widget, QLineEdit)


# ---------------------------------------------------------------------------
# Integração end-to-end: LNL usa o widget novo no painel
# ---------------------------------------------------------------------------


class TestLNLPanelIntegration:
    def test_lnl_sat_curve_widget_is_editor(self, qapp):
        """Quando painel é bound a um LNL, o widget p/ sat_curve_csv é
        o SaturationCurveEditor."""
        from app.gui.schematic_pp.editor import PpEditor
        from app.gui.schematic_pp.items import ComponentItem
        ed = PpEditor()
        ed.add_component_by_type("LNL")
        item = [i for i in ed.scene.items() if isinstance(i, ComponentItem)][0]
        ed.properties.bind_component(item)
        # Procura o SaturationCurveEditor entre os filhos
        ed_widgets = ed.properties.findChildren(SaturationCurveEditor)
        assert len(ed_widgets) >= 1, (
            "Painel de LNL deveria conter SaturationCurveEditor após "
            "v0.24.3 (widget_hint=saturation_curve)"
        )
