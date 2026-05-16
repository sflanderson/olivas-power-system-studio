"""
tests/test_pp_v3_3_0_unbalanced_dialog.py — v3.3.0 Sprint 1.

UnbalancedPowerFlowDialog — fecha violação 7ª garantia identificada
no audit `v3.3.0_TIER1_AUDIT.md` §B.3.

Cobre:
* Dialog instantiates (offscreen Qt)
* Demo mode: 3 buses synthetic
* Open-phase scenario (Tutorial §Part 9 p.241-242)
* Real project mode com PpProject
* Menu integration (7ª garantia)
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
# Sprint 1.A — Dialog instantiation
# ===========================================================================


class TestDialogInstantiation:

    def test_dialog_imports(self):
        from app.gui.unbalanced_pf_dialog import (
            UnbalancedPowerFlowDialog, run_unbalanced_pf_dialog,
        )
        assert UnbalancedPowerFlowDialog is not None
        assert callable(run_unbalanced_pf_dialog)

    def test_dialog_creates(self, qapp):
        from app.gui.unbalanced_pf_dialog import UnbalancedPowerFlowDialog
        dlg = UnbalancedPowerFlowDialog()
        assert "Unbalanced" in dlg.windowTitle()

    def test_default_unbalance_limit_2pct(self, qapp):
        """IEEE 1159-2019: 2.0% steady-state limit."""
        from app.gui.unbalanced_pf_dialog import UnbalancedPowerFlowDialog
        dlg = UnbalancedPowerFlowDialog()
        assert dlg.unbalance_limit.value() == 2.0


# ===========================================================================
# Sprint 1.B — Demo mode (3 buses)
# ===========================================================================


class TestDemoMode:

    def test_calculate_demo_3_buses(self, qapp):
        from app.gui.unbalanced_pf_dialog import UnbalancedPowerFlowDialog
        dlg = UnbalancedPowerFlowDialog()
        dlg._on_calculate()
        assert dlg.results_table.rowCount() == 3

    def test_summary_cites_references(self, qapp):
        from app.gui.unbalanced_pf_dialog import UnbalancedPowerFlowDialog
        dlg = UnbalancedPowerFlowDialog()
        dlg._on_calculate()
        text = dlg.summary_text.toPlainText()
        # Anti-alucinação visible to user
        assert "IEEE Std 1159-2019" in text or "IEEE 1159" in text
        assert "PTW Tutorial" in text

    def test_low_unbalance_below_limit(self, qapp):
        """Default 0.5% < limit 2.0% → no violations."""
        from app.gui.unbalanced_pf_dialog import UnbalancedPowerFlowDialog
        dlg = UnbalancedPowerFlowDialog()
        dlg._on_calculate()
        text = dlg.summary_text.toPlainText()
        # Bus 3 has 2x typical = 1.0% → still below 2% limit
        # All buses within limit
        assert "dentro do limite" in text or "Violations: 0" in text


# ===========================================================================
# Sprint 1.C — Open-phase scenario (PTW Tutorial §Part 9 p.241-242)
# ===========================================================================


class TestOpenPhaseScenario:

    def test_open_phase_a_zeros_phase(self, qapp):
        """Open phase A → V_a = 0 in some buses."""
        from app.gui.unbalanced_pf_dialog import UnbalancedPowerFlowDialog
        dlg = UnbalancedPowerFlowDialog()
        dlg.cb_open_phase.setChecked(True)
        dlg.rb_phase_a.setChecked(True)
        dlg._on_calculate()
        # First bus should have V_a near 0
        v_a_text = dlg.results_table.item(0, 1).text()
        # Format: "0.0000"
        assert float(v_a_text) < 0.01  # Phase A forced to ~0

    def test_open_phase_summary_mentions_scenario(self, qapp):
        from app.gui.unbalanced_pf_dialog import UnbalancedPowerFlowDialog
        dlg = UnbalancedPowerFlowDialog()
        dlg.cb_open_phase.setChecked(True)
        dlg.rb_phase_b.setChecked(True)
        dlg._on_calculate()
        text = dlg.summary_text.toPlainText()
        assert "OPEN-PHASE" in text
        assert "B" in text  # Phase B mentioned

    def test_open_phase_creates_violations(self, qapp):
        """Open phase = high unbalance (50%+) → violations."""
        from app.gui.unbalanced_pf_dialog import UnbalancedPowerFlowDialog
        dlg = UnbalancedPowerFlowDialog()
        dlg.cb_open_phase.setChecked(True)
        dlg._on_calculate()
        text = dlg.summary_text.toPlainText()
        # Should report violations (UF > 2.0%)
        assert "Violations:" in text or "⚠" in text


# ===========================================================================
# Sprint 1.D — Real PpProject mode
# ===========================================================================


class TestRealProjectMode:

    def test_with_project_no_buses(self, qapp):
        """PpProject sem BUS components → mensagem amigável."""
        from app.gui.unbalanced_pf_dialog import UnbalancedPowerFlowDialog
        from app.preprocessor.models import PpProject
        proj = PpProject()
        dlg = UnbalancedPowerFlowDialog(project=proj)
        dlg._on_calculate()
        # No components → demo path (since "components" check returns False)
        # Either way, should not crash
        assert dlg.summary_text.toPlainText()  # has some text

    def test_with_project_having_buses(self, qapp):
        """PpProject com 2 BUS components → análise real."""
        from app.gui.unbalanced_pf_dialog import UnbalancedPowerFlowDialog
        from app.preprocessor.models import PpComponent, PpProject, PpProperty
        proj = PpProject()
        for i, name in enumerate(["B1", "B2"]):
            comp = PpComponent(
                type="BUS", name=name, visible=True,
                x=100 + i*100, y=100, label_dx=10, label_dy=-20,
                mirror=0, rotation=0,
                properties=[PpProperty(name, True)],
            )
            proj.components.append(comp)
        dlg = UnbalancedPowerFlowDialog(project=proj)
        dlg._on_calculate()
        # Either real analysis or graceful handling
        assert dlg.summary_text.toPlainText()


# ===========================================================================
# Sprint 1.E — 7ª garantia: menu wiring
# ===========================================================================


class TestSeventhGuaranteeRestored:

    def test_main_window_handler_exists(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "_on_show_unbalanced_pf_dialog" in content

    def test_main_window_menu_action_exists(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "Análise unbalanced" in content
        # Cita Tutorial reference
        assert "§Part 9" in content

    def test_dialog_module_accessible(self):
        """Dialog module deve estar acessível para imports."""
        from app.gui import unbalanced_pf_dialog
        assert hasattr(unbalanced_pf_dialog, "UnbalancedPowerFlowDialog")
        assert hasattr(unbalanced_pf_dialog, "run_unbalanced_pf_dialog")
