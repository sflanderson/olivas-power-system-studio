"""
tests/test_pp_v0_88_sticky_templates.py — v0.88: sticky
templates + multi-report extractors.

Cobertura
---------

* PpDataBlock.template_lines + effective_template().
* Sidecar IO persiste template_lines (round-trip).
* EditDataBlockTemplateCommand: redo/undo de template+lines.
* Editor _on_request_edit_datablock mostra template, salva
  via EditDataBlockTemplateCommand.
* refresh_datablocks_from_cache usa effective_template (não
  cumula substituições; idempotente entre re-runs).
* Migração legacy: datablock pré-v0.88 (template_lines vazio)
  promove lines a template no primeiro refresh.
* Extractors: SC, PF, Pipeline. Aggregator merge.
* Cache: 3 namespaces independentes.
* Hook PF: run_power_flow_analysis store solution.
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QMessageBox


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_bus(bus_id: str = "BUS-1", x: int = 100, y: int = 100):
    from app.preprocessor.models import PpComponent, PpProperty
    return PpComponent(
        type="BUS", name=bus_id, visible=True,
        x=x, y=y, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[
            PpProperty(bus_id, True),
            PpProperty("13.8", True),
            PpProperty("3", False),
            PpProperty("swgr_15kv", True),
            PpProperty("1", True),
        ],
    )


def _make_pipeline_report(bus_id: str = "BUS-1"):
    from app.postprocessor.bus_pipeline import BusPipelineReport
    return BusPipelineReport(
        bus_id=bus_id, rated_voltage_kV=13.8,
        panel_type="swgr_15kv",
        is_lineside=True, has_AFD=False,
        n_neighbors=2, n_sc_sources=2,
        sources_summary=("UTIL: 100%",),
        Ik_pp_kA=15.30, ip_kA=40.20, kappa=1.85,
        coordination_clearing_time_ms=500.0,
        effective_clearing_time_ms=200.0,
        incident_energy_cal_cm2=8.40,
        arc_flash_boundary_mm=1200.0,
        ppe_category="3", warnings=(),
    )


# ---------------------------------------------------------------------------
# PpDataBlock.template_lines
# ---------------------------------------------------------------------------


class TestStickyTemplateField:

    def test_default_template_empty(self):
        from app.preprocessor.models import PpDataBlock
        db = PpDataBlock(component_name="R1")
        assert db.template_lines == []

    def test_effective_template_returns_template_when_set(self):
        from app.preprocessor.models import PpDataBlock
        db = PpDataBlock(
            component_name="R1",
            lines=["rendered"],
            template_lines=["template"],
        )
        assert db.effective_template() == ["template"]

    def test_effective_template_fallback_to_lines(self):
        """Legacy: sem template_lines, usa lines."""
        from app.preprocessor.models import PpDataBlock
        db = PpDataBlock(
            component_name="R1",
            lines=["legacy"],
        )
        assert db.effective_template() == ["legacy"]


# ---------------------------------------------------------------------------
# Sidecar IO — round-trip de template_lines
# ---------------------------------------------------------------------------


class TestSidecarTemplateRoundtrip:

    def test_save_load_preserves_template(self, tmp_path):
        from app.gui.schematic_pp.datablock_io import (
            load_datablocks_sidecar, save_datablocks_sidecar,
        )
        from app.preprocessor.models import PpDataBlock
        sch = tmp_path / "x.sch"
        sch.write_text("dummy", encoding="utf-8")
        db = PpDataBlock(
            component_name="R1",
            lines=["Ik = 15.30 kA"],
            template_lines=["Ik = {Ik_pp_kA:.2f} kA"],
        )
        save_datablocks_sidecar(str(sch), [db])
        loaded = load_datablocks_sidecar(str(sch))
        assert len(loaded) == 1
        assert loaded[0].lines == ["Ik = 15.30 kA"]
        assert loaded[0].template_lines == ["Ik = {Ik_pp_kA:.2f} kA"]

    def test_legacy_sidecar_without_template_loads_empty(self, tmp_path):
        """Sidecar gerado por v0.86/v0.87 sem ``template_lines``
        ainda carrega — template_lines fica vazio."""
        import json
        from app.gui.schematic_pp.datablock_io import (
            load_datablocks_sidecar, sidecar_path,
        )
        sch = tmp_path / "y.sch"
        sch.write_text("dummy", encoding="utf-8")
        # Escreve sidecar legacy (sem template_lines)
        legacy = {
            "schema_version": 1,
            "datablocks": [
                {
                    "component_name": "R1",
                    "dx": 50, "dy": -10,
                    "lines": ["x", "y"],
                    "visible": True,
                }
            ],
        }
        sidecar_path(str(sch)).write_text(
            json.dumps(legacy), encoding="utf-8",
        )
        loaded = load_datablocks_sidecar(str(sch))
        assert len(loaded) == 1
        assert loaded[0].lines == ["x", "y"]
        assert loaded[0].template_lines == []


# ---------------------------------------------------------------------------
# EditDataBlockTemplateCommand
# ---------------------------------------------------------------------------


class TestEditDataBlockTemplateCommand:

    def test_redo_sets_both_fields(self, qapp):
        from app.gui.schematic_pp.commands import (
            EditDataBlockTemplateCommand,
        )
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_bus("BUS-1"))
        db = PpDataBlock(
            component_name="BUS-1",
            lines=["old rendered"],
            template_lines=["{x}"],
        )
        scene.add_datablock(db)
        cmd = EditDataBlockTemplateCommand(
            scene, db, ["new {y}"],
        )
        cmd.redo()
        # template = lines = nova string
        assert db.template_lines == ["new {y}"]
        assert db.lines == ["new {y}"]

    def test_undo_restores_both_fields(self, qapp):
        from app.gui.schematic_pp.commands import (
            EditDataBlockTemplateCommand,
        )
        from app.gui.schematic_pp.scene import PpScene
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_bus("BUS-1"))
        db = PpDataBlock(
            component_name="BUS-1",
            lines=["A"],
            template_lines=["{a}"],
        )
        scene.add_datablock(db)
        cmd = EditDataBlockTemplateCommand(scene, db, ["{b}"])
        cmd.redo()
        cmd.undo()
        # Voltou ao estado original (template + lines podem ser
        # diferentes — preserva).
        assert db.template_lines == ["{a}"]
        assert db.lines == ["A"]


# ---------------------------------------------------------------------------
# Editor edit dialog usa template_lines
# ---------------------------------------------------------------------------


class TestEditorEditFlow:

    def test_edit_dialog_shows_template(self, qapp, monkeypatch):
        """Dialog inicializa com template_lines (não lines)."""
        from app.gui.schematic_pp.editor import PpEditor
        from app.preprocessor.models import PpDataBlock
        ed = PpEditor()
        ed.scene.add_component(_make_bus("BUS-1"))
        db = PpDataBlock(
            component_name="BUS-1",
            lines=["Ik = 15.30 kA"],
            template_lines=["Ik = {Ik_pp_kA:.2f} kA"],
        )
        item = ed.scene.add_datablock(db)
        captured_initial = []

        from PySide6.QtWidgets import QDialog

        class FakeDialog:
            def __init__(self, parent, initial_lines, title):
                captured_initial.append(list(initial_lines))
            def exec(self): return QDialog.Rejected
            def lines(self): return []

        monkeypatch.setattr(
            "app.gui.datablock_dialog.DataBlockEditDialog",
            FakeDialog,
        )
        ed._on_request_edit_datablock(item)
        # Dialog viu o template (com placeholders), não o lines
        # renderizado.
        assert captured_initial == [["Ik = {Ik_pp_kA:.2f} kA"]]

    def test_edit_dialog_save_uses_template_command(
        self, qapp, monkeypatch,
    ):
        """OK no dialog → EditDataBlockTemplateCommand empilhado."""
        from app.gui.schematic_pp.editor import PpEditor
        from app.preprocessor.models import PpDataBlock
        ed = PpEditor()
        ed.scene.add_component(_make_bus("BUS-1"))
        db = PpDataBlock(
            component_name="BUS-1",
            lines=["old"],
            template_lines=["old"],
        )
        item = ed.scene.add_datablock(db)

        from PySide6.QtWidgets import QDialog

        class FakeDialog:
            def __init__(self, *a, **kw): pass
            def exec(self): return QDialog.Accepted
            def lines(self): return ["new template"]

        monkeypatch.setattr(
            "app.gui.datablock_dialog.DataBlockEditDialog",
            FakeDialog,
        )
        ed._on_request_edit_datablock(item)
        # Após edit, template e lines = novo texto
        assert db.template_lines == ["new template"]
        assert db.lines == ["new template"]

    def test_add_datablock_initializes_template_equal_to_lines(
        self, qapp, monkeypatch,
    ):
        """Ao criar datablock, template_lines = lines."""
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        ed.add_component_by_type("R")
        host = ed.scene.component_items()[0]

        from PySide6.QtWidgets import QDialog

        class FakeDialog:
            def __init__(self, *a, **kw): pass
            def exec(self): return QDialog.Accepted
            def lines(self): return ["{x:.2f}", "static"]

        monkeypatch.setattr(
            "app.gui.datablock_dialog.DataBlockEditDialog",
            FakeDialog,
        )
        ed._on_request_add_datablock(host)
        db = ed.scene.project.datablocks[0]
        assert db.lines == ["{x:.2f}", "static"]
        assert db.template_lines == ["{x:.2f}", "static"]


# ---------------------------------------------------------------------------
# Refresh idempotente + migração legacy
# ---------------------------------------------------------------------------


class TestRefreshStickyAndMigration:

    def test_refresh_uses_effective_template_not_lines(self, qapp):
        """Após 1ª refresh, lines tem valores. 2ª refresh com
        valores diferentes deve usar template (não re-render
        sobre lines já renderizado)."""
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.datablock_binder import (
            refresh_datablocks_from_cache,
        )
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_bus("BUS-1"))
        db = PpDataBlock(
            component_name="BUS-1",
            lines=["Ik = {Ik_pp_kA:.2f} kA"],
            template_lines=["Ik = {Ik_pp_kA:.2f} kA"],
        )
        scene.add_datablock(db)

        # 1ª refresh: Ik = 15.30
        scene.results_cache.set_pipeline_report(
            "BUS-1", _make_pipeline_report("BUS-1"),
        )
        refresh_datablocks_from_cache(scene, scene.results_cache)
        assert db.lines == ["Ik = 15.30 kA"]
        assert db.template_lines == ["Ik = {Ik_pp_kA:.2f} kA"]

        # 2ª refresh com novo Ik = 22.0
        report2 = _make_pipeline_report("BUS-1")
        # MutableImmutable: BusPipelineReport is dataclass — pode
        # ter @dataclass(frozen=True)? Não — já testamos que aceita
        # mudança via fields no _make_pipeline_report.
        # Usamos um report novo com Ik_pp_kA diferente.
        from dataclasses import replace
        report2 = replace(report2, Ik_pp_kA=22.0)
        scene.results_cache.set_pipeline_report("BUS-1", report2)
        refresh_datablocks_from_cache(scene, scene.results_cache)
        # Re-renderizado a partir do template — placeholder funcionou
        assert db.lines == ["Ik = 22.00 kA"]

    def test_legacy_datablock_promotes_lines_to_template(self, qapp):
        """Datablock pré-v0.88 (template_lines == []): primeiro
        refresh promove lines → template_lines."""
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.datablock_binder import (
            refresh_datablocks_from_cache,
        )
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_bus("BUS-1"))
        # Legacy: só lines, sem template_lines
        db = PpDataBlock(
            component_name="BUS-1",
            lines=["Ik = {Ik_pp_kA:.2f} kA"],
        )
        scene.add_datablock(db)
        scene.results_cache.set_pipeline_report(
            "BUS-1", _make_pipeline_report("BUS-1"),
        )
        refresh_datablocks_from_cache(scene, scene.results_cache)
        # template_lines populado (migração) E lines renderizado
        assert db.template_lines == ["Ik = {Ik_pp_kA:.2f} kA"]
        assert db.lines == ["Ik = 15.30 kA"]


# ---------------------------------------------------------------------------
# Extractors v0.88 — SC e PF standalone
# ---------------------------------------------------------------------------


class TestExtractValuesFromSC:

    def test_extracts_from_short_circuit_result(self):
        from app.gui.schematic_pp.datablock_binder import (
            extract_values_from_sc_result,
        )
        from app.standards.iec60909 import ShortCircuitResult
        result = ShortCircuitResult(
            Ik_pp_kA=15.0, ip_kA=37.5,
            idc_at_50ms_kA=2.0, Ib_kA=15.0,
            Ik_steady_kA=15.0,
            z_thevenin_ohm=complex(0.1, 0.5),
            r_over_x=0.1, kappa=1.85,
            voltage_factor_c=1.10, rated_voltage_kV=13.8,
            fault_distance="far_from_generator",
            source="IEC 60909",
        )
        v = extract_values_from_sc_result(result)
        assert v["Ik_pp_kA"] == 15.0
        assert v["ip_kA"] == 37.5
        assert v["kappa"] == 1.85
        assert v["rated_voltage_kV"] == 13.8
        assert v["V_LL_kV"] == 13.8   # alias
        # Sk derivado
        import math
        assert abs(v["Sk_pp_MVA"] - math.sqrt(3) * 13.8 * 15.0) < 0.01

    def test_none_returns_empty(self):
        from app.gui.schematic_pp.datablock_binder import (
            extract_values_from_sc_result,
        )
        assert extract_values_from_sc_result(None) == {}


class TestExtractValuesFromPF:

    def test_extracts_for_specific_bus(self):
        from app.gui.schematic_pp.datablock_binder import (
            extract_values_from_pf_solution,
        )
        from app.postprocessor.power_flow import PowerFlowSolution
        sol = PowerFlowSolution(
            converged=True, iterations=3, max_mismatch=1e-7,
            bus_voltages_pu={
                "SLACK": complex(1.0, 0.0),
                "LOAD": complex(0.95, -0.05),
            },
            line_flows=(),
            total_losses_pu=complex(0.001, 0.005),
        )
        v = extract_values_from_pf_solution(sol, "LOAD")
        assert v["pf_converged"] is True
        assert v["pf_iterations"] == 3
        # |0.95 - 0.05j| ≈ 0.9513
        assert 0.94 < v["V_pu"] < 0.96
        # angle = atan2(-0.05, 0.95) ≈ -3°
        assert -4 < v["V_angle_deg"] < -2

    def test_unknown_bus_no_voltage(self):
        from app.gui.schematic_pp.datablock_binder import (
            extract_values_from_pf_solution,
        )
        from app.postprocessor.power_flow import PowerFlowSolution
        sol = PowerFlowSolution(
            converged=True, iterations=2, max_mismatch=1e-9,
            bus_voltages_pu={"X": complex(1.0, 0.0)},
            line_flows=(),
            total_losses_pu=complex(0, 0),
        )
        v = extract_values_from_pf_solution(sol, "NOT-PRESENT")
        # converged/iterations populados, mas não tem V_pu
        assert v["pf_converged"] is True
        assert "V_pu" not in v

    def test_none_returns_empty(self):
        from app.gui.schematic_pp.datablock_binder import (
            extract_values_from_pf_solution,
        )
        assert extract_values_from_pf_solution(None, "X") == {}


# ---------------------------------------------------------------------------
# Cache — 3 namespaces
# ---------------------------------------------------------------------------


class TestCacheNamespaces:

    def test_pipeline_sc_pf_independent(self):
        from app.gui.schematic_pp.datablock_binder import (
            DataBlockResultCache,
        )
        c = DataBlockResultCache()
        c.set_pipeline_report("B1", "PIPE")
        c.set_sc_result("B1", "SC")
        c.set_pf_solution("B1", "PF")
        assert c.get_pipeline_report("B1") == "PIPE"
        assert c.get_sc_result("B1") == "SC"
        assert c.get_pf_solution("B1") == "PF"

    def test_clear_clears_all_namespaces(self):
        from app.gui.schematic_pp.datablock_binder import (
            DataBlockResultCache,
        )
        c = DataBlockResultCache()
        c.set_pipeline_report("X", "1")
        c.set_sc_result("Y", "2")
        c.set_pf_solution("Z", "3")
        c.clear()
        assert c.all_bus_ids() == []

    def test_all_bus_ids_union(self):
        from app.gui.schematic_pp.datablock_binder import (
            DataBlockResultCache,
        )
        c = DataBlockResultCache()
        c.set_pipeline_report("A", "1")
        c.set_sc_result("B", "2")
        c.set_pf_solution("A", "3")
        assert set(c.all_bus_ids()) == {"A", "B"}


# ---------------------------------------------------------------------------
# aggregate_values_for_bus
# ---------------------------------------------------------------------------


class TestAggregateValuesForBus:

    def test_pipeline_only(self):
        from app.gui.schematic_pp.datablock_binder import (
            DataBlockResultCache, aggregate_values_for_bus,
        )
        c = DataBlockResultCache()
        c.set_pipeline_report("BUS-1", _make_pipeline_report("BUS-1"))
        v = aggregate_values_for_bus(c, "BUS-1")
        assert v["Ik_pp_kA"] == 15.30
        assert v["bus_id"] == "BUS-1"

    def test_pf_overrides_pipeline_for_v_pu(self):
        """PF tem V_pu/V_angle_deg que pipeline não tem.
        PF aplicado por último → estes campos vêm do PF."""
        from app.gui.schematic_pp.datablock_binder import (
            DataBlockResultCache, aggregate_values_for_bus,
        )
        from app.postprocessor.power_flow import PowerFlowSolution
        c = DataBlockResultCache()
        c.set_pipeline_report("BUS-1", _make_pipeline_report("BUS-1"))
        c.set_pf_solution("BUS-1", PowerFlowSolution(
            converged=True, iterations=1, max_mismatch=0.0,
            bus_voltages_pu={"BUS-1": complex(0.97, -0.03)},
            line_flows=(),
            total_losses_pu=complex(0, 0),
        ))
        v = aggregate_values_for_bus(c, "BUS-1")
        assert "V_pu" in v
        # PF não tem Ik, mas pipeline tem — preservado
        assert v["Ik_pp_kA"] == 15.30


# ---------------------------------------------------------------------------
# Hook PF
# ---------------------------------------------------------------------------


class TestPFHook:

    def test_store_pf_and_refresh_no_scene(self, qapp):
        """Sem schematic_pp.scene atributo → 0 (não crasha)."""
        from app.gui.analysis_dialogs import (
            _store_pf_and_refresh_datablocks,
        )
        from app.postprocessor.power_flow import PowerFlowSolution

        class DummyParent:
            pass

        sol = PowerFlowSolution(
            converged=True, iterations=1, max_mismatch=0.0,
            bus_voltages_pu={"X": complex(1, 0)},
            line_flows=(),
            total_losses_pu=complex(0, 0),
        )
        # Não deve crashar
        n = _store_pf_and_refresh_datablocks(DummyParent(), sol)
        assert n == 0

    def test_store_pf_populates_cache_for_each_bus(self, qapp):
        """Para cada bus_id em bus_voltages_pu, set_pf_solution."""
        from app.gui.analysis_dialogs import (
            _store_pf_and_refresh_datablocks,
        )
        from app.gui.schematic_pp.editor import PpEditor
        from app.postprocessor.power_flow import PowerFlowSolution

        class FakeMW:
            def __init__(self, ed):
                self.schematic_pp = ed

        ed = PpEditor()
        # Adiciona BUSes correspondentes
        ed.scene.add_component(_make_bus("SLACK"))
        ed.scene.add_component(_make_bus("LOAD"))
        # PF solution
        sol = PowerFlowSolution(
            converged=True, iterations=2, max_mismatch=1e-9,
            bus_voltages_pu={
                "SLACK": complex(1.0, 0.0),
                "LOAD": complex(0.95, -0.05),
            },
            line_flows=(),
            total_losses_pu=complex(0.001, 0),
        )
        _store_pf_and_refresh_datablocks(FakeMW(ed), sol)
        # Cache contém entries para os 2 buses
        cache = ed.scene.results_cache
        assert cache.get_pf_solution("SLACK") is sol
        assert cache.get_pf_solution("LOAD") is sol


# ---------------------------------------------------------------------------
# Round-trip end-to-end (sticky template através de save/load)
# ---------------------------------------------------------------------------


class TestEndToEndSticky:

    def test_save_refresh_reload_preserves_template(
        self, qapp, tmp_path,
    ):
        """
        1. Cria datablock com template
        2. Refresh substitui valores
        3. Save
        4. Reload em novo editor
        5. Refresh novamente — deve dar mesmo resultado (template
           preservado)
        """
        from app.gui.schematic_pp.editor import PpEditor
        from app.preprocessor.models import PpDataBlock

        ed = PpEditor()
        ed.scene.add_component(_make_bus("BUS-XYZ"))
        # Cria datablock manualmente
        db = PpDataBlock(
            component_name="BUS-XYZ",
            lines=["Ik = {Ik_pp_kA:.2f} kA"],
            template_lines=["Ik = {Ik_pp_kA:.2f} kA"],
        )
        ed.scene.add_datablock(db)

        # Refresh c/ pipeline
        ed.scene.results_cache.set_pipeline_report(
            "BUS-XYZ", _make_pipeline_report("BUS-XYZ"),
        )
        from app.gui.schematic_pp.datablock_binder import (
            refresh_datablocks_from_cache,
        )
        refresh_datablocks_from_cache(
            ed.scene, ed.scene.results_cache,
        )
        assert db.lines == ["Ik = 15.30 kA"]

        # Save .sch (e sidecar)
        sch = tmp_path / "rt.sch"
        ed.save_to_sch(str(sch))

        # Reload em novo editor
        ed2 = PpEditor()
        ed2.load_from_sch(str(sch))
        loaded_db = ed2.scene.project.datablocks[0]
        # Lines: valores renderizados (preservados no save)
        assert loaded_db.lines == ["Ik = 15.30 kA"]
        # Template: placeholder original (preservado)
        assert loaded_db.template_lines == [
            "Ik = {Ik_pp_kA:.2f} kA",
        ]

        # Refresh novamente com novo report (Ik = 22.0)
        from dataclasses import replace
        new_report = replace(
            _make_pipeline_report("BUS-XYZ"),
            Ik_pp_kA=22.0,
        )
        ed2.scene.results_cache.set_pipeline_report(
            "BUS-XYZ", new_report,
        )
        refresh_datablocks_from_cache(
            ed2.scene, ed2.scene.results_cache,
        )
        assert loaded_db.lines == ["Ik = 22.00 kA"]
        # Template ainda preservado
        assert loaded_db.template_lines == [
            "Ik = {Ik_pp_kA:.2f} kA",
        ]
