"""
tests/test_pp_v3_2_0_component_editor_multipanel.py — v3.2.0.

Component Editor Multipanel (PTW Tutorial §Part 1 p.52-60).

Cobre:
* Sprint 1+2 — N tabs por PropertyGroup (em vez de 2 tabs Parâmetros/Descrição)
* Sprint 2 — ordem canônica + ícones unicode por grupo
* Sprint 3 — Datablock tab integration (📊 Datablocks)
* 7ª garantia — linked_library propagado de PpProperty para PropertyRow
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


def _make_component(qapp, code: str = "BREAKER"):
    """Helper: build PpComponent populated with default property values."""
    from app.preprocessor.models import PpComponent, PpProperty
    from app.preprocessor.spec import get_default_registry

    spec = get_default_registry().get(code)
    if spec is None:
        return None, None
    comp = PpComponent(
        type=code, name=f"{code}1", visible=True,
        x=0, y=0, label_dx=10, label_dy=-20, mirror=0, rotation=0,
        properties=[
            PpProperty(str(p.default), p.visible) for p in spec.properties
        ],
    )
    return spec, comp


# ===========================================================================
# Sprint 1+2 — Multi-tab structure
# ===========================================================================


class TestMultiTabStructure:

    def test_breaker_has_at_least_3_tabs(self, qapp):
        """BREAKER has props in main + timing + advanced groups."""
        from app.gui.schematic_pp.property_editor import ComponentPropertyDialog
        spec, comp = _make_component(qapp, "BREAKER")
        dlg = ComponentPropertyDialog(spec, comp)
        # Tabs: Principal + (subset) + Descrição
        assert dlg._tabs.count() >= 3

    def test_main_tab_always_present(self, qapp):
        """Sprint 2: MAIN tab é ancora visual (always present)."""
        from app.gui.schematic_pp.property_editor import ComponentPropertyDialog
        spec, comp = _make_component(qapp, "BREAKER")
        dlg = ComponentPropertyDialog(spec, comp)
        # Primeira tab deve ter "Principal" no nome
        first_tab_text = dlg._tabs.tabText(0)
        assert "Principal" in first_tab_text or "MAIN" in first_tab_text.upper()

    def test_descricao_tab_is_last(self, qapp):
        """Descrição tab is always last."""
        from app.gui.schematic_pp.property_editor import ComponentPropertyDialog
        spec, comp = _make_component(qapp, "BREAKER")
        dlg = ComponentPropertyDialog(spec, comp)
        last_tab_text = dlg._tabs.tabText(dlg._tabs.count() - 1)
        assert "Descrição" in last_tab_text or "📄" in last_tab_text

    def test_tab_titles_have_icons(self, qapp):
        """Sprint 2: ícones unicode por grupo (📋 Principal, ⏱ Timing, ⚙ Avançado)."""
        from app.gui.schematic_pp.property_editor import ComponentPropertyDialog
        spec, comp = _make_component(qapp, "BREAKER")
        dlg = ComponentPropertyDialog(spec, comp)
        for tab_text in dlg._created_tabs:
            # Each tab should contain a unicode pictogram icon — covers
            # both emoji range (U+1F300+) and misc-tech range (U+2300+)
            # such as ⏱ U+23F1, ⚙ U+2699, ⚡ U+26A1.
            has_icon = any(ord(c) > 0x2300 for c in tab_text)
            assert has_icon, f"Tab without icon: {tab_text!r}"

    def test_canonical_order_main_first_advanced_late(self, qapp):
        """MAIN must come before ADVANCED in tab order."""
        from app.gui.schematic_pp.property_editor import ComponentPropertyDialog
        spec, comp = _make_component(qapp, "BREAKER")
        dlg = ComponentPropertyDialog(spec, comp)
        idx_main = -1
        idx_advanced = -1
        for i, tab in enumerate(dlg._created_tabs):
            if "Principal" in tab:
                idx_main = i
            if "Avançado" in tab or "Advanced" in tab:
                idx_advanced = i
        if idx_main >= 0 and idx_advanced >= 0:
            assert idx_main < idx_advanced


# ===========================================================================
# Sprint 3 — Datablock tab integration
# ===========================================================================


class TestDatablockTab:

    def test_no_datablocks_no_extra_tab(self, qapp):
        """Sem datablocks anexados → não cria tab Datablocks."""
        from app.gui.schematic_pp.property_editor import ComponentPropertyDialog
        spec, comp = _make_component(qapp, "BREAKER")
        dlg = ComponentPropertyDialog(spec, comp)
        # Tab "Datablocks" não deve existir
        for tab in dlg._created_tabs:
            assert "Datablock" not in tab

    def test_attach_datablock_tab_inserts_before_description(self, qapp):
        """attach_datablock_tab insere a tab antes da Descrição."""
        from app.gui.schematic_pp.property_editor import ComponentPropertyDialog
        from app.preprocessor.models import PpDataBlock
        spec, comp = _make_component(qapp, "BREAKER")
        dlg = ComponentPropertyDialog(spec, comp)
        n_before = dlg._tabs.count()

        db = PpDataBlock(component_name="BREAKER1", lines=["I_n: 1200 A"])
        dlg.attach_datablock_tab([db])

        assert dlg._tabs.count() == n_before + 1
        # Datablocks penúltimo (Description é o último)
        assert "Datablock" in dlg._created_tabs[-2]

    def test_empty_datablock_list_skips_tab(self, qapp):
        """Empty list → no tab added."""
        from app.gui.schematic_pp.property_editor import ComponentPropertyDialog
        spec, comp = _make_component(qapp, "BREAKER")
        dlg = ComponentPropertyDialog(spec, comp)
        n_before = dlg._tabs.count()
        dlg.attach_datablock_tab([])
        assert dlg._tabs.count() == n_before


# ===========================================================================
# 7ª garantia — linked_library propagado
# ===========================================================================


class TestLinkedLibraryPropagation:

    def test_property_with_linked_library_creates_disabled_row(self, qapp):
        """build_property_rows propaga linked_library para PropertyRow."""
        from app.preprocessor.models import PpComponent, PpProperty
        from app.preprocessor.spec import get_default_registry
        from app.gui.schematic_pp.property_editor import build_property_rows

        spec = get_default_registry().get("BREAKER")
        # Construct component with linked property
        props = [
            PpProperty(str(p.default), p.visible) for p in spec.properties
        ]
        # Mark first non-tag property as linked (typically index 1+)
        if len(props) > 2:
            props[2].linked_library = "ABB HD4"

        comp = PpComponent(
            type="BREAKER", name="Q1", visible=True,
            x=0, y=0, label_dx=10, label_dy=-20, mirror=0, rotation=0,
            properties=props,
        )
        groups = build_property_rows(spec, comp, parent=None)

        # Find the linked row across all groups
        all_rows = [r for rows in groups.values() for r in rows]
        linked_rows = [r for r in all_rows if r.linked_library is not None]
        assert len(linked_rows) == 1
        assert linked_rows[0].linked_library == "ABB HD4"
        # Editor disabled
        assert not linked_rows[0]._editor.isEnabled()


# ===========================================================================
# Backward-compat — public API preserved
# ===========================================================================


class TestBackwardCompat:

    def test_property_changed_signal_still_emits(self, qapp):
        """Signal property_changed (pre-v3.2.0 API) preserved."""
        from app.gui.schematic_pp.property_editor import ComponentPropertyDialog
        spec, comp = _make_component(qapp, "BREAKER")
        dlg = ComponentPropertyDialog(spec, comp)
        captured = []
        dlg.property_changed.connect(
            lambda i, v, vis: captured.append((i, v, vis))
        )
        # Trigger via internal handler (real edit would go through PropertyRow)
        dlg._on_row_changed(0, "new_value", True)
        assert captured == [(0, "new_value", True)]

    def test_constructor_signature_unchanged(self, qapp):
        """Constructor (spec, component, parent=None) compatible."""
        from app.gui.schematic_pp.property_editor import ComponentPropertyDialog
        spec, comp = _make_component(qapp, "BREAKER")
        # Old call signature
        dlg = ComponentPropertyDialog(spec, comp)
        assert dlg is not None


# ===========================================================================
# 7ª garantia GUI — verify multipanel is reachable from editor
# ===========================================================================


class TestSeventhGuaranteeMultipanel:

    def test_editor_open_modal_dialog_uses_new_dialog(self):
        """editor.py:_open_modal_dialog instancia ComponentPropertyDialog
        com possibilidade de attach_datablock_tab."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/schematic_pp/editor.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "ComponentPropertyDialog" in content
        assert "attach_datablock_tab" in content
        assert "_datablocks_for_component" in content
