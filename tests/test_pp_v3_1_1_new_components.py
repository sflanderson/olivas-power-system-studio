"""
tests/test_pp_v3_1_1_new_components.py — v3.1.1 Sprint 2.

Component types Util / Load / Filter — paridade Tutorial PTW §Part 1 p.21-28.

Cobre:
* UTIL.ocomp / LOAD.ocomp / FILTER.ocomp registrados no catalog
* PTW symbols renderizam (UtilitySymbol, LoadSymbol, FilterSymbol)
* Properties default canonical (kV, MVAsc, X/R, kW, kVAR etc.)
"""

from __future__ import annotations

import os
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys
    return QApplication.instance() or QApplication(sys.argv)


# ===========================================================================
# Sprint 2.A — Catalog registration
# ===========================================================================


class TestCatalogRegistration:

    def test_util_in_catalog(self, qapp):
        from app.preprocessor.catalog import all_entries
        codes = {e.code for e in all_entries()}
        assert "UTIL" in codes

    def test_load_in_catalog(self, qapp):
        from app.preprocessor.catalog import all_entries
        codes = {e.code for e in all_entries()}
        assert "LOAD" in codes

    def test_filter_in_catalog(self, qapp):
        from app.preprocessor.catalog import all_entries
        codes = {e.code for e in all_entries()}
        assert "FILTER" in codes

    def test_util_category_source(self, qapp):
        from app.preprocessor.catalog import all_entries
        e = next(e for e in all_entries() if e.code == "UTIL")
        assert e.category == "source"

    def test_load_category_load(self, qapp):
        from app.preprocessor.catalog import all_entries
        e = next(e for e in all_entries() if e.code == "LOAD")
        assert e.category == "load"

    def test_filter_category_filter(self, qapp):
        from app.preprocessor.catalog import all_entries
        e = next(e for e in all_entries() if e.code == "FILTER")
        assert e.category == "filter"


# ===========================================================================
# Sprint 2.B — PTW Symbol renderers
# ===========================================================================


class TestPTWSymbolRenderers:

    def test_util_renderer_class(self, qapp):
        from app.preprocessor.symbols import get_renderer
        from app.preprocessor.ptw_symbols import UtilitySymbol
        r = get_renderer("UTIL")
        assert isinstance(r, UtilitySymbol)

    def test_load_renderer_class(self, qapp):
        from app.preprocessor.symbols import get_renderer
        from app.preprocessor.ptw_symbols import LoadSymbol
        r = get_renderer("LOAD")
        assert isinstance(r, LoadSymbol)

    def test_filter_renderer_class(self, qapp):
        from app.preprocessor.symbols import get_renderer
        from app.preprocessor.ptw_symbols import FilterSymbol
        r = get_renderer("FILTER")
        assert isinstance(r, FilterSymbol)


# ===========================================================================
# Sprint 2.C — Properties default canonical values
# ===========================================================================


class TestUtilDefaults:

    def test_util_default_voltage_13_8_kV(self, qapp):
        """Tutorial-style typical MV value 13.8 kV."""
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("UTIL")
        nominal = next(p for p in spec.properties if p.name == "nominal_voltage_kV")
        assert nominal.default == 13.8

    def test_util_has_mva_sc_field(self, qapp):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("UTIL")
        names = [p.name for p in spec.properties]
        assert "mva_sc" in names
        assert "x_over_r" in names

    def test_util_default_x_over_r_10(self, qapp):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("UTIL")
        xr = next(p for p in spec.properties if p.name == "x_over_r")
        assert xr.default == 10.0


class TestLoadDefaults:

    def test_load_has_kw_kvar(self, qapp):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("LOAD")
        names = [p.name for p in spec.properties]
        assert "kW" in names
        assert "kVAR" in names

    def test_load_type_choices(self, qapp):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("LOAD")
        lt = next(p for p in spec.properties if p.name == "load_type")
        choices = lt.choices or ()
        assert "motor_3ph" in choices
        assert "lighting" in choices
        assert "heating" in choices


class TestFilterDefaults:

    def test_filter_has_harmonic_order(self, qapp):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("FILTER")
        names = [p.name for p in spec.properties]
        assert "harmonic_order" in names
        assert "q_factor" in names

    def test_filter_default_5th_harmonic(self, qapp):
        """Default tune to 5th harmonic (most common in industry)."""
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().get("FILTER")
        h = next(p for p in spec.properties if p.name == "harmonic_order")
        assert h.default == 5.0


# ===========================================================================
# Sprint 2.D — 7ª garantia: paleta mostra os 3 novos
# ===========================================================================


class TestSeventhGuaranteePaletteAccess:

    def test_3_new_codes_in_palette(self, qapp):
        """Paleta carrega do catalog → 3 novos codes aparecem para o user."""
        from app.gui.schematic_pp.editor import PpEditor
        from app.preprocessor.catalog import all_entries

        codes = {e.code for e in all_entries()}
        for new in ("UTIL", "LOAD", "FILTER"):
            assert new in codes, f"{new} ausente do catalog → não aparece na paleta"

    def test_palette_widget_has_new_items(self, qapp):
        """PpPalette QListWidget tem entries para UTIL/LOAD/FILTER."""
        from app.gui.schematic_pp.editor import PpEditor
        editor = PpEditor()
        items = []
        for i in range(editor.palette.count()):
            it = editor.palette.item(i)
            if it is not None:
                items.append(it.data(0x0100))  # Qt.UserRole
        # Items são (label, code) tuples ou só codes; verifica presença
        flat = []
        for it in items:
            if isinstance(it, tuple):
                flat.append(it[1] if len(it) > 1 else it[0])
            else:
                flat.append(it)
        for new in ("UTIL", "LOAD", "FILTER"):
            assert new in flat, f"{new} ausente da PpPalette"
