"""
tests/test_pp_v3_5_0_scenario_manager.py — v3.5.0.

Scenario Manager (PTW Tutorial §Part 11 p.319-347).

Cobre:
* PpScenario create_base / clone / is_base
* ScenarioManager add / find / get_base / get_active / activate
* clone_active
* PromotionMode (ALL_FIELDS / UNMODIFIED_ONLY / DO_NOT_PROMOTE)
* diff_with_base (added/removed/modified)
* GUI dialog accessibility (7ª garantia)
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


def _make_project_with_buses(n: int = 2):
    from app.preprocessor.models import PpComponent, PpProject, PpProperty
    proj = PpProject()
    for i in range(n):
        proj.components.append(PpComponent(
            type="BUS", name=f"B{i+1}", visible=True,
            x=i*100, y=0, label_dx=10, label_dy=-20, mirror=0, rotation=0,
            properties=[PpProperty(f"B{i+1}", True)],
        ))
    return proj


# ===========================================================================
# PpScenario
# ===========================================================================


class TestPpScenario:

    def test_create_base_has_no_parent(self):
        from app.preprocessor.scenarios import PpScenario
        proj = _make_project_with_buses()
        base = PpScenario.create_base(proj, name="Base")
        assert base.is_base()
        assert base.base_id is None
        assert base.name == "Base"

    def test_clone_creates_new_id_with_parent(self):
        from app.preprocessor.scenarios import PpScenario
        proj = _make_project_with_buses()
        base = PpScenario.create_base(proj, name="Base")
        clone = base.clone(new_name="Scenario A")
        assert clone.id != base.id
        assert clone.base_id == base.id
        assert not clone.is_base()
        assert clone.name == "Scenario A"

    def test_clone_is_independent(self):
        """Mutating clone's project must not affect base's project."""
        from app.preprocessor.scenarios import PpScenario
        proj = _make_project_with_buses()
        base = PpScenario.create_base(proj, name="Base")
        clone = base.clone(new_name="Branch")
        # Mutate clone
        clone.project_snapshot.components[0].name = "MODIFIED"
        # Base unchanged
        assert base.project_snapshot.components[0].name == "B1"


# ===========================================================================
# ScenarioManager
# ===========================================================================


class TestScenarioManager:

    def test_empty_manager(self):
        from app.preprocessor.scenarios import ScenarioManager
        m = ScenarioManager()
        assert m.scenarios == []
        assert m.active_id is None

    def test_add_first_scenario_becomes_active(self):
        from app.preprocessor.scenarios import PpScenario, ScenarioManager
        proj = _make_project_with_buses()
        m = ScenarioManager()
        base = PpScenario.create_base(proj)
        m.add(base)
        assert m.active_id == base.id

    def test_get_base_returns_base(self):
        from app.preprocessor.scenarios import PpScenario, ScenarioManager
        proj = _make_project_with_buses()
        m = ScenarioManager()
        base = PpScenario.create_base(proj)
        m.add(base)
        assert m.get_base() is base

    def test_clone_active_creates_branch(self):
        from app.preprocessor.scenarios import PpScenario, ScenarioManager
        proj = _make_project_with_buses()
        m = ScenarioManager()
        m.add(PpScenario.create_base(proj))
        clone = m.clone_active("Branch A")
        assert clone is not None
        assert len(m.scenarios) == 2
        assert clone.base_id == m.get_base().id

    def test_activate_changes_active(self):
        from app.preprocessor.scenarios import PpScenario, ScenarioManager
        proj = _make_project_with_buses()
        m = ScenarioManager()
        base = PpScenario.create_base(proj)
        m.add(base)
        clone = m.clone_active("Branch A")
        m.activate(base.id)
        assert m.active_id == base.id


# ===========================================================================
# Diff with base
# ===========================================================================


class TestDiff:

    def test_diff_added_component(self):
        from app.preprocessor.models import PpComponent, PpProperty
        from app.preprocessor.scenarios import PpScenario, ScenarioManager
        proj = _make_project_with_buses()
        m = ScenarioManager()
        m.add(PpScenario.create_base(proj))
        clone = m.clone_active("Branch A")
        # Add a new component to clone
        clone.project_snapshot.components.append(PpComponent(
            type="BREAKER", name="Q1", visible=True,
            x=200, y=0, label_dx=10, label_dy=-20, mirror=0, rotation=0,
            properties=[PpProperty("Q-01", True)],
        ))
        diff = m.diff_with_base(clone.id)
        assert "Q1" in diff["added"]
        assert diff["removed"] == []

    def test_diff_removed_component(self):
        from app.preprocessor.scenarios import PpScenario, ScenarioManager
        proj = _make_project_with_buses(n=3)
        m = ScenarioManager()
        m.add(PpScenario.create_base(proj))
        clone = m.clone_active("Branch B")
        # Remove B2 from clone
        clone.project_snapshot.components = [
            c for c in clone.project_snapshot.components
            if c.name != "B2"
        ]
        diff = m.diff_with_base(clone.id)
        assert "B2" in diff["removed"]

    def test_diff_modified_component_property(self):
        from app.preprocessor.scenarios import PpScenario, ScenarioManager
        proj = _make_project_with_buses()
        m = ScenarioManager()
        m.add(PpScenario.create_base(proj))
        clone = m.clone_active("Branch C")
        # Modify B1's property value
        clone.project_snapshot.components[0].properties[0].value = "B1-MOD"
        diff = m.diff_with_base(clone.id)
        assert "B1" in diff["modified"]


# ===========================================================================
# Promotion modes
# ===========================================================================


class TestPromotion:

    def test_promote_all_fields_overwrites_base(self):
        from app.preprocessor.scenarios import (
            PpScenario, PromotionMode, ScenarioManager,
        )
        proj = _make_project_with_buses()
        m = ScenarioManager()
        m.add(PpScenario.create_base(proj))
        clone = m.clone_active("Branch A")
        clone.project_snapshot.components[0].name = "MODIFIED"
        clone.promotion_mode = PromotionMode.ALL_FIELDS
        ok = m.promote_to_base(clone.id)
        assert ok
        # Base now has the modified component
        assert m.get_base().project_snapshot.components[0].name == "MODIFIED"

    def test_promote_do_not_promote_blocks(self):
        from app.preprocessor.scenarios import (
            PpScenario, PromotionMode, ScenarioManager,
        )
        proj = _make_project_with_buses()
        m = ScenarioManager()
        m.add(PpScenario.create_base(proj))
        clone = m.clone_active("Read-only")
        clone.promotion_mode = PromotionMode.DO_NOT_PROMOTE
        ok = m.promote_to_base(clone.id)
        assert ok is False

    def test_cannot_promote_base(self):
        from app.preprocessor.scenarios import PpScenario, ScenarioManager
        proj = _make_project_with_buses()
        m = ScenarioManager()
        base = PpScenario.create_base(proj)
        m.add(base)
        ok = m.promote_to_base(base.id)
        assert ok is False


# ===========================================================================
# GUI dialog (7ª garantia)
# ===========================================================================


class TestDialogAccessibility:

    def test_dialog_imports(self):
        from app.gui.scenario_manager_dialog import (
            ScenarioManagerDialog, run_scenario_manager_dialog,
        )
        assert ScenarioManagerDialog is not None

    def test_dialog_creates_with_project(self, qapp):
        from app.gui.scenario_manager_dialog import ScenarioManagerDialog
        proj = _make_project_with_buses()
        dlg = ScenarioManagerDialog(project=proj)
        # Base auto-created
        assert dlg.scenarios_list.count() == 1

    def test_dialog_creates_without_project(self, qapp):
        """Sem project, dialog ainda funciona (lista vazia)."""
        from app.gui.scenario_manager_dialog import ScenarioManagerDialog
        dlg = ScenarioManagerDialog()
        assert dlg.scenarios_list.count() == 0

    def test_main_window_handler_exists(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "_on_show_scenario_manager" in content
        assert "Scenario Manager" in content
