"""v3.7.2 — Cross-cutting cleanup C.1 + C.2 tests.

Closes SKIPPED_BACKLOG C.1 (deprecate 2-bus PF dialog) + C.2
(hybrid mode demo+project em EquipmentEvalDialog).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    return app


# ---------------------------------------------------------------------------
# C.1 — PowerFlowDialog deprecation banner
# ---------------------------------------------------------------------------


class TestPowerFlowDialogDeprecation:
    def test_deprecated_message_class_attr(self) -> None:
        from app.gui.analysis_dialogs import PowerFlowDialog
        msg = PowerFlowDialog.DEPRECATED_MESSAGE
        assert "DEPRECATED" in msg
        assert "v3.7.2" in msg
        assert "BUS components" in msg

    def test_dialog_title_contains_legacy_marker(self, qapp) -> None:
        from app.gui.analysis_dialogs import PowerFlowDialog
        dlg = PowerFlowDialog(parent=None)
        assert "LEGACY" in dlg.windowTitle() or "legacy" in dlg.windowTitle()

    def test_dialog_has_warning_label(self, qapp) -> None:
        """Banner LABEL exists in form layout."""
        from PySide6.QtWidgets import QLabel
        from app.gui.analysis_dialogs import PowerFlowDialog
        dlg = PowerFlowDialog(parent=None)
        # Find any QLabel containing "DEPRECATED"
        labels = dlg.findChildren(QLabel)
        assert any("DEPRECATED" in lbl.text() for lbl in labels), (
            "PowerFlowDialog must show deprecation banner"
        )


# ---------------------------------------------------------------------------
# C.2 — EquipmentEvalDialog hybrid demo+project mode
# ---------------------------------------------------------------------------


def _make_eq(equipment_id: str = "P1"):
    """Build a real EquipmentInstance for tests (avoids attr mismatch)."""
    from app.postprocessor.equipment_eval import EquipmentInstance
    return EquipmentInstance(
        equipment_id=equipment_id,
        equipment_type="breaker",
        rated_voltage_kV=13.8,
        rated_continuous_A=1200.0,
        rated_interrupt_kA=25.0,
        bus_voltage_kV=13.8,
        duty={
            "I_load_A": 100.0,
            "I_design_A": 200.0,
            "I_fault_kA": 10.0,
            "ip_kA": 25.0,
            "V_drop_pct": 1.5,
        },
    )


class TestHybridDemoMode:
    def test_chk_hybrid_demo_exists(self, qapp) -> None:
        from app.gui.equipment_eval_dialog import EquipmentEvalDialog
        dlg = EquipmentEvalDialog(parent=None)
        assert hasattr(dlg, "chk_hybrid_demo")
        assert "demo" in dlg.chk_hybrid_demo.text().lower()

    def test_chk_default_unchecked(self, qapp) -> None:
        from app.gui.equipment_eval_dialog import EquipmentEvalDialog
        dlg = EquipmentEvalDialog(parent=None)
        # Default: not in hybrid mode
        assert dlg.chk_hybrid_demo.isChecked() is False

    def test_set_equipments_replaces_when_unchecked(self, qapp) -> None:
        """Default: set_equipments overrides demos."""
        from app.gui.equipment_eval_dialog import EquipmentEvalDialog
        dlg = EquipmentEvalDialog(parent=None)
        dlg.chk_hybrid_demo.setChecked(False)
        # 1 fake equipment
        dlg.set_equipments([_make_eq("P1")])
        # Result should be just 1 (project)
        assert len(dlg.equipments) == 1
        assert dlg.equipments[0].equipment_id == "P1"

    def test_set_equipments_appends_when_checked(self, qapp) -> None:
        """Hybrid mode: demos + project = bigger list."""
        from app.gui.equipment_eval_dialog import (
            EquipmentEvalDialog,
            _build_demo_equipment,
        )
        dlg = EquipmentEvalDialog(parent=None)
        dlg.chk_hybrid_demo.setChecked(True)
        n_demos = len(_build_demo_equipment())
        dlg.set_equipments([_make_eq("P1")])
        # demos + 1 project = n_demos + 1
        assert len(dlg.equipments) == n_demos + 1
        # Last equipment is the project one
        assert dlg.equipments[-1].equipment_id == "P1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
