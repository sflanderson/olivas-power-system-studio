"""
tests.test_pp_v1_3_1_gui_integration — sub-sprints G.1 + G.2 + G.3.

Cobre dialogs GUI integrando backends v1.2.0+v1.3.0:

* G.1 — EquipmentEvalDialog (Equipment Evaluation Dashboard)
* G.2 — CoordRulesDialog (Coord Rule Engine)
* G.3 — TCCCoordinogramDialog populated (modificação do v1.0.2)

**Aceite v1.3.1**: 21+ testes, 100% verde, regression v1.0+ OK.
"""

from __future__ import annotations

import os
import tempfile

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.gui.coord_rules_dialog import CoordRulesDialog
from app.gui.equipment_eval_dialog import (
    EquipmentEvalDialog,
    _build_demo_equipment,
)
from app.postprocessor.coord_rules import RuleSeverity
from app.postprocessor.equipment_eval import EquipmentInstance


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
# G.1 — EquipmentEvalDialog
# ---------------------------------------------------------------------------


class TestEquipmentEvalDialogConstruction:

    def test_dialog_constructs(self, qapp):
        dlg = EquipmentEvalDialog()
        assert dlg is not None

    def test_demo_loaded_on_init(self, qapp):
        """Demo é carregado automaticamente ao abrir."""
        dlg = EquipmentEvalDialog()
        assert len(dlg.equipments) == 7  # 7 equipment demo

    def test_html_browser_not_empty(self, qapp):
        dlg = EquipmentEvalDialog()
        # Após init, last_html deve estar populado
        assert len(dlg.last_html) > 100
        assert "<html" in dlg.last_html.lower()

    def test_status_label_populated(self, qapp):
        dlg = EquipmentEvalDialog()
        # Status mostra X equipamentos · Y PASS · Z FAIL
        text = dlg.status_label.text()
        assert "equipamentos" in text
        assert "PASS" in text


class TestEquipmentEvalDialogActions:

    def test_load_demo_button(self, qapp):
        dlg = EquipmentEvalDialog()
        # Limpa, depois recarrega
        dlg.equipments = []
        dlg.load_demo()
        assert len(dlg.equipments) == 7

    def test_set_equipments_external(self, qapp):
        """Permite passar equipamentos vindos de fora."""
        dlg = EquipmentEvalDialog()
        custom_eqs = [
            EquipmentInstance(
                equipment_id="X-CUSTOM",
                equipment_type="bus",
                rated_voltage_kV=13.8,
                rated_continuous_A=3000,
                duty={"V_drop_pct": 1.0},
            ),
        ]
        dlg.set_equipments(custom_eqs)
        assert len(dlg.equipments) == 1
        assert "X-CUSTOM" in dlg.last_html

    def test_run_evaluation_with_empty(self, qapp):
        dlg = EquipmentEvalDialog()
        dlg.equipments = []
        dlg.run_evaluation()
        assert "Nenhum equipamento" in dlg.html_browser.toHtml() \
            or dlg.last_html == ""

    def test_html_contains_dashboard_elements(self, qapp):
        dlg = EquipmentEvalDialog()
        # Esperado: tabela, sumário PASS/WARN/FAIL/N/A
        assert "<table" in dlg.last_html
        assert "BUS-MAIN-13.8kV" in dlg.last_html


class TestDemoEquipmentValidation:

    def test_demo_has_diverse_types(self):
        eqs = _build_demo_equipment()
        types = {eq.equipment_type for eq in eqs}
        assert "bus" in types
        assert "breaker" in types
        assert "cable" in types
        assert "generator" in types
        assert "transformer" in types

    def test_demo_has_failing_cable(self):
        """CAB-OVERSIZED deve ter FAIL no design load."""
        eqs = _build_demo_equipment()
        bad_cab = next(
            e for e in eqs if e.equipment_id == "CAB-OVERSIZED"
        )
        assert bad_cab.duty.get("I_design_A") > bad_cab.rated_continuous_A


# ---------------------------------------------------------------------------
# G.2 — CoordRulesDialog
# ---------------------------------------------------------------------------


class TestCoordRulesDialogConstruction:

    def test_dialog_constructs(self, qapp):
        dlg = CoordRulesDialog()
        assert dlg is not None

    def test_demo_targets_loaded(self, qapp):
        dlg = CoordRulesDialog()
        assert len(dlg.targets_with_ctx) == 5

    def test_results_populated_on_init(self, qapp):
        dlg = CoordRulesDialog()
        # 5 targets × ~8 rules = ~40 results
        assert len(dlg.results) > 20

    def test_4_rulesets_with_checkboxes(self, qapp):
        dlg = CoordRulesDialog()
        assert len(dlg._ruleset_checkboxes) == 4

    def test_all_rulesets_checked_by_default(self, qapp):
        dlg = CoordRulesDialog()
        for rs, cb in dlg._ruleset_checkboxes.values():
            assert cb.isChecked()


class TestCoordRulesDialogBehavior:

    def test_apply_with_no_rulesets_clears_tree(self, qapp):
        dlg = CoordRulesDialog()
        # Desmarca todos
        for rs, cb in dlg._ruleset_checkboxes.values():
            cb.setChecked(False)
        dlg.apply_selected_rulesets()
        # Tree deve ficar vazio
        assert dlg.tree.topLevelItemCount() == 0

    def test_apply_with_only_motor_ruleset(self, qapp):
        dlg = CoordRulesDialog()
        # Só NEC_MOTOR_PROTECTION (3 rules)
        for rs, cb in dlg._ruleset_checkboxes.values():
            cb.setChecked("Motor" in rs.name)
        dlg.apply_selected_rulesets()
        # Pelo menos os 2 motor relays demo terão results
        assert len(dlg.results) > 0
        # Status atualizado
        assert "PASS" in dlg.status_label.text()

    def test_results_have_severity_distribution(self, qapp):
        dlg = CoordRulesDialog()
        # Demo tem motor_relay_good (PASS) + motor_relay_bad (FAIL)
        sev_set = {r.severity for r in dlg.results}
        assert RuleSeverity.PASS in sev_set
        assert RuleSeverity.FAIL in sev_set

    def test_tree_top_items_match_unique_targets(self, qapp):
        dlg = CoordRulesDialog()
        unique_target_ids = {r.target_id for r in dlg.results}
        # Tree top items são targets únicos
        assert dlg.tree.topLevelItemCount() == len(unique_target_ids)


# ---------------------------------------------------------------------------
# Main window menu integration
# ---------------------------------------------------------------------------


class TestMainWindowMenuIntegration:
    """Verifica que actions de v1.3.1 estão no menu Análise."""

    def test_main_window_has_equipment_eval_handler(self, qapp):
        # Importação tardia (main_window é grande)
        from app.gui.main_window import MainWindow
        assert hasattr(MainWindow, "_on_show_equipment_eval")

    def test_main_window_has_coord_rules_handler(self, qapp):
        from app.gui.main_window import MainWindow
        assert hasattr(MainWindow, "_on_show_coord_rules_check")


# ---------------------------------------------------------------------------
# G.3 — TCCCoordinogramDialog populated com mix v1.2+v1.3
# ---------------------------------------------------------------------------


class TestG3CoordinogramDemoMix:
    """Verifica que o demo loader carrega mix de tipos v1.2+v1.3."""

    def test_demo_has_at_least_5_curves(self, qapp):
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        dlg = TCCCoordinogramDialog(fault_current_A=3000)
        # 1 TCCCurve + 1 MultiFunctionRelay + 1 FuseTCCCurve + 3 DamageCurves = 6
        assert dlg._curve_list.count() >= 5

    def test_demo_includes_multifunction_relay(self, qapp):
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        from app.postprocessor.tcc_devices import MultiFunctionRelay
        dlg = TCCCoordinogramDialog(fault_current_A=3000)
        curves = dlg._coord_widget.get_curves()
        has_mfr = any(isinstance(c, MultiFunctionRelay) for c in curves)
        assert has_mfr

    def test_demo_includes_damage_curve(self, qapp):
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        from app.postprocessor.tcc_damage import (
            CableDamageCurve,
            MotorThermalCurve,
            TransformerThroughFaultCurve,
        )
        dlg = TCCCoordinogramDialog(fault_current_A=3000)
        curves = dlg._coord_widget.get_curves()
        has_cable_dmg = any(
            isinstance(c, CableDamageCurve) for c in curves
        )
        has_xfmr_dmg = any(
            isinstance(c, TransformerThroughFaultCurve) for c in curves
        )
        has_motor_dmg = any(
            isinstance(c, MotorThermalCurve) for c in curves
        )
        assert has_cable_dmg
        assert has_xfmr_dmg
        assert has_motor_dmg

    def test_demo_includes_fuse_curve(self, qapp):
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        from app.postprocessor.tcc_curves import FuseTCCCurve
        dlg = TCCCoordinogramDialog(fault_current_A=3000)
        curves = dlg._coord_widget.get_curves()
        has_fuse = any(isinstance(c, FuseTCCCurve) for c in curves)
        assert has_fuse

    def test_demo_includes_legacy_TCCCurve(self, qapp):
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        from app.postprocessor.tcc_curves import TCCCurve
        dlg = TCCCoordinogramDialog(fault_current_A=3000)
        curves = dlg._coord_widget.get_curves()
        has_legacy = any(
            isinstance(c, TCCCurve)
            and not type(c).__name__ == 'FuseTCCCurve'
            for c in curves
        )
        assert has_legacy

    def test_curve_display_label_handles_all_types(self, qapp):
        """O helper _curve_display_label não crasha em nenhum tipo."""
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        from app.postprocessor.tcc_curves import (
            CurveType, FuseClass, FuseTCCCurve, TCCCurve,
        )
        from app.postprocessor.tcc_damage import (
            CableDamageCurve, CableMaterial,
            MotorThermalCurve,
            TransformerThroughFaultCurve, XfmrFaultCategory,
        )
        from app.postprocessor.tcc_devices import MultiFunctionRelay

        # Cada tipo gera label não-vazio
        cases = [
            TCCCurve(
                relay_id="R1",
                curve_type=CurveType.IEC_VERY_INVERSE,
                pickup_A=100, tms=0.3,
            ),
            MultiFunctionRelay.relay_51_only(
                device_id="D1",
                curve_type=CurveType.IEC_STANDARD_INVERSE,
                pickup_A=100, tms=0.3,
            ),
            FuseTCCCurve("F1", FuseClass.gG, rated_current_A=100),
            CableDamageCurve(
                "C1", section_mm2=50,
                material=CableMaterial.Cu_XLPE,
            ),
            TransformerThroughFaultCurve(
                "T1", rated_current_A=100,
                category=XfmrFaultCategory.FREQUENT,
            ),
            MotorThermalCurve("M1", fla_A=100),
        ]
        for c in cases:
            label = TCCCoordinogramDialog._curve_display_label(c)
            assert label
            assert len(label) > 5

    def test_dialog_count_correct_drag_able(self, qapp):
        """
        Drag-able artists: TCCCurve + MultiFunctionRelay + FuseTCCCurve = 3.
        DamageCurves NÃO entram em drag.
        """
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        dlg = TCCCoordinogramDialog(fault_current_A=3000)
        widget = dlg._coord_widget
        # Demo tem 6 curves: 1 TCCCurve + 1 Device + 1 Fuse + 3 Damage
        # Drag-able: 3 primeiros
        assert len(widget._line_artists) == 3
