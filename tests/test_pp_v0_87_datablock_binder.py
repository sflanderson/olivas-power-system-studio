"""
tests/test_pp_v0_87_datablock_binder.py — v0.87:

Auto-binding de datablocks com resultados de análises.

Cobertura
---------

* ``bind_lines`` substitui ``{key}`` / ``{key:fmt}`` corretamente.
* Chaves desconhecidas permanecem literais (não crash).
* Format-spec inválido cai pra ``str(val)`` (graceful).
* ``extract_values_from_pipeline_report`` extrai todos os campos
  esperados + aliases + Sk_pp_MVA derivado.
* ``DataBlockResultCache`` armazena/recupera por bus_id.
* ``refresh_datablocks_from_cache`` substitui datablocks
  ancorados a um BUS pelo report cacheado.
* Templates atualizados (v0.87) usam {nome:fmt} em vez de <unit>.
* Editor: botão refresh atualiza datablocks; mensagens de
  warning quando ausentes.
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QMessageBox


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_bus_component(
    bus_id: str = "BUS-1", x: int = 100, y: int = 100,
):
    """Cria PpComponent BUS com props mínimas (alinhado ao .ocomp)."""
    from app.preprocessor.models import PpComponent, PpProperty
    return PpComponent(
        type="BUS", name=bus_id, visible=True,
        x=x, y=y, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[
            PpProperty(bus_id, True),         # 0: bus_id
            PpProperty("13.8", True),         # 1: V_LL
            PpProperty("3", False),           # 2: n_phases
            PpProperty("swgr_15kv", True),    # 3: panel_type
            PpProperty("1", True),            # 4: lineside
        ],
    )


def _make_pipeline_report(bus_id: str = "BUS-1"):
    from app.postprocessor.bus_pipeline import BusPipelineReport
    return BusPipelineReport(
        bus_id=bus_id, rated_voltage_kV=13.8,
        panel_type="swgr_15kv",
        is_lineside=True, has_AFD=False,
        n_neighbors=2, n_sc_sources=2,
        sources_summary=("UTIL: 60%", "GEN: 40%"),
        Ik_pp_kA=15.30, ip_kA=40.20, kappa=1.85,
        coordination_clearing_time_ms=500.0,
        effective_clearing_time_ms=200.0,
        incident_energy_cal_cm2=8.40,
        arc_flash_boundary_mm=1200.0,
        ppe_category="3", warnings=(),
    )


# ---------------------------------------------------------------------------
# bind_lines — substituição
# ---------------------------------------------------------------------------


class TestBindLines:

    def test_simple_substitution(self):
        from app.gui.schematic_pp.datablock_binder import bind_lines
        out = bind_lines(
            ["Ip = {Ik_pp_kA} kA"],
            {"Ik_pp_kA": 15.3},
        )
        assert out == ["Ip = 15.3 kA"]

    def test_format_spec_precision(self):
        from app.gui.schematic_pp.datablock_binder import bind_lines
        out = bind_lines(
            ["Ip = {x:.2f} kA"],
            {"x": 15.3},
        )
        assert out == ["Ip = 15.30 kA"]

    def test_unknown_key_kept_literal(self):
        from app.gui.schematic_pp.datablock_binder import bind_lines
        out = bind_lines(
            ["x = {missing}, y = {present}"],
            {"present": 1},
        )
        assert out == ["x = {missing}, y = 1"]

    def test_invalid_format_spec_falls_back_to_str(self):
        """``{key:Q}`` não é format spec válido → str(val)."""
        from app.gui.schematic_pp.datablock_binder import bind_lines
        out = bind_lines(["{x:Q}"], {"x": "abc"})
        assert out == ["abc"]

    def test_empty_lines_passthrough(self):
        from app.gui.schematic_pp.datablock_binder import bind_lines
        assert bind_lines([], {"x": 1}) == []
        assert bind_lines([""], {"x": 1}) == [""]

    def test_multiple_placeholders_per_line(self):
        from app.gui.schematic_pp.datablock_binder import bind_lines
        out = bind_lines(
            ["V = {v:.2f} pu, ∠ = {a:.1f}°"],
            {"v": 1.025, "a": -3.5},
        )
        assert out == ["V = 1.02 pu, ∠ = -3.5°"]

    def test_idempotent(self):
        """Aplicar duas vezes o mesmo dict dá o mesmo resultado."""
        from app.gui.schematic_pp.datablock_binder import bind_lines
        lines = ["I = {x} kA"]
        v = {"x": 10}
        once = bind_lines(lines, v)
        twice = bind_lines(once, v)
        # Após primeira sub, não há mais {x}; segundo não muda nada.
        assert once == twice == ["I = 10 kA"]


# ---------------------------------------------------------------------------
# extract_values_from_pipeline_report
# ---------------------------------------------------------------------------


class TestExtractValuesFromPipelineReport:

    def test_extracts_direct_fields(self):
        from app.gui.schematic_pp.datablock_binder import (
            extract_values_from_pipeline_report,
        )
        report = _make_pipeline_report()
        v = extract_values_from_pipeline_report(report)
        assert v["bus_id"] == "BUS-1"
        assert v["rated_voltage_kV"] == 13.8
        assert v["panel_type"] == "swgr_15kv"
        assert v["Ik_pp_kA"] == 15.30
        assert v["ip_kA"] == 40.20
        assert v["kappa"] == 1.85
        assert v["incident_energy_cal_cm2"] == 8.40
        assert v["arc_flash_boundary_mm"] == 1200.0
        assert v["ppe_category"] == "3"

    def test_provides_aliases(self):
        from app.gui.schematic_pp.datablock_binder import (
            extract_values_from_pipeline_report,
        )
        report = _make_pipeline_report()
        v = extract_values_from_pipeline_report(report)
        assert v["V_LL_kV"] == v["rated_voltage_kV"]
        assert v["IE_cal"] == v["incident_energy_cal_cm2"]
        assert v["AFB_mm"] == v["arc_flash_boundary_mm"]
        assert v["PPE"] == v["ppe_category"]
        assert v["t_clear_ms"] == v["effective_clearing_time_ms"]

    def test_computes_derived_sk(self):
        """Sk'' = √3 · V_LL · Ik''. Com V=13.8 e Ik=15.3 → ~365.7 MVA"""
        from app.gui.schematic_pp.datablock_binder import (
            extract_values_from_pipeline_report,
        )
        import math
        report = _make_pipeline_report()
        v = extract_values_from_pipeline_report(report)
        expected = math.sqrt(3) * 13.8 * 15.30
        assert abs(v["Sk_pp_MVA"] - expected) < 0.01

    def test_none_report_returns_empty_dict(self):
        from app.gui.schematic_pp.datablock_binder import (
            extract_values_from_pipeline_report,
        )
        assert extract_values_from_pipeline_report(None) == {}


# ---------------------------------------------------------------------------
# DataBlockResultCache
# ---------------------------------------------------------------------------


class TestResultCache:

    def test_set_get_pipeline_report(self):
        from app.gui.schematic_pp.datablock_binder import (
            DataBlockResultCache,
        )
        c = DataBlockResultCache()
        report = _make_pipeline_report("BUS-A")
        c.set_pipeline_report("BUS-A", report)
        assert c.get_pipeline_report("BUS-A") is report
        assert c.get_pipeline_report("BUS-OTHER") is None

    def test_all_bus_ids(self):
        from app.gui.schematic_pp.datablock_binder import (
            DataBlockResultCache,
        )
        c = DataBlockResultCache()
        c.set_pipeline_report("B1", _make_pipeline_report("B1"))
        c.set_pipeline_report("B2", _make_pipeline_report("B2"))
        assert set(c.all_bus_ids()) == {"B1", "B2"}

    def test_empty_bus_id_ignored(self):
        from app.gui.schematic_pp.datablock_binder import (
            DataBlockResultCache,
        )
        c = DataBlockResultCache()
        c.set_pipeline_report("", _make_pipeline_report())
        assert c.all_bus_ids() == []

    def test_clear(self):
        from app.gui.schematic_pp.datablock_binder import (
            DataBlockResultCache,
        )
        c = DataBlockResultCache()
        c.set_pipeline_report("X", _make_pipeline_report())
        c.clear()
        assert c.all_bus_ids() == []


# ---------------------------------------------------------------------------
# refresh_datablocks_from_cache
# ---------------------------------------------------------------------------


class TestRefreshDatablocks:

    def test_refresh_substitutes_lines(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.datablock_binder import (
            refresh_datablocks_from_cache,
        )
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_bus_component("BUS-1"))
        # Datablock com placeholders SC
        db = PpDataBlock(
            component_name="BUS-1",
            lines=[
                "Ik''  = {Ik_pp_kA:.2f} kA",
                "ip    = {ip_kA:.2f} kA",
                "κ     = {kappa:.2f}",
            ],
        )
        scene.add_datablock(db)
        # Popula cache
        scene.results_cache.set_pipeline_report(
            "BUS-1", _make_pipeline_report("BUS-1"),
        )
        n = refresh_datablocks_from_cache(scene, scene.results_cache)
        assert n == 1
        assert db.lines == [
            "Ik''  = 15.30 kA",
            "ip    = 40.20 kA",
            "κ     = 1.85",
        ]

    def test_no_cache_no_refresh(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.datablock_binder import (
            refresh_datablocks_from_cache,
        )
        from app.preprocessor.models import PpDataBlock
        scene = PpScene()
        scene.add_component(_make_bus_component("BUS-2"))
        db = PpDataBlock(
            component_name="BUS-2",
            lines=["Ik = {Ik_pp_kA} kA"],
        )
        scene.add_datablock(db)
        # Cache vazio
        n = refresh_datablocks_from_cache(scene, scene.results_cache)
        assert n == 0
        # Lines inalteradas
        assert db.lines == ["Ik = {Ik_pp_kA} kA"]

    def test_unrelated_datablock_skipped(self, qapp):
        """Datablock em componente que não é BUS → não atualiza."""
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.datablock_binder import (
            refresh_datablocks_from_cache,
        )
        from app.preprocessor.models import (
            PpComponent, PpDataBlock, PpProperty,
        )
        scene = PpScene()
        # Resistor (não-BUS)
        scene.add_component(PpComponent(
            type="R", name="R1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("1k")],
        ))
        db = PpDataBlock(
            component_name="R1",
            lines=["Ik = {Ik_pp_kA} kA"],
        )
        scene.add_datablock(db)
        scene.results_cache.set_pipeline_report(
            "R1", _make_pipeline_report(),
        )
        n = refresh_datablocks_from_cache(scene, scene.results_cache)
        # R1 não é BUS → resolve_bus_id retorna None
        assert n == 0


# ---------------------------------------------------------------------------
# Templates v0.87 (placeholders nomeados)
# ---------------------------------------------------------------------------


class TestUpdatedTemplates:

    def test_sc_template_uses_named_placeholders(self, qapp):
        from app.gui.datablock_dialog import _TEMPLATES
        sc = _TEMPLATES["Curto-circuito (IEC 60909)"]
        # Cada linha tem {nome:fmt}
        joined = "\n".join(sc)
        assert "{Ik_pp_kA" in joined
        assert "{ip_kA" in joined
        assert "{kappa" in joined
        assert "{Sk_pp_MVA" in joined

    def test_af_template_uses_named_placeholders(self, qapp):
        from app.gui.datablock_dialog import _TEMPLATES
        af = _TEMPLATES["Arc-Flash (NBR 17227)"]
        joined = "\n".join(af)
        assert "{IE_cal" in joined
        assert "{AFB_mm" in joined
        assert "{PPE" in joined
        assert "{t_clear_ms" in joined

    def test_equipment_template_uses_named_placeholders(self, qapp):
        from app.gui.datablock_dialog import _TEMPLATES
        eq = _TEMPLATES["Equipamento (PTW Equipment)"]
        joined = "\n".join(eq)
        assert "{bus_id" in joined
        assert "{V_LL_kV" in joined


# ---------------------------------------------------------------------------
# PpScene.results_cache (criado no construtor)
# ---------------------------------------------------------------------------


class TestSceneResultsCache:

    def test_scene_has_results_cache(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.datablock_binder import (
            DataBlockResultCache,
        )
        scene = PpScene()
        assert hasattr(scene, "results_cache")
        assert isinstance(scene.results_cache, DataBlockResultCache)


# ---------------------------------------------------------------------------
# Editor: refresh button + handler
# ---------------------------------------------------------------------------


class TestEditorRefreshDatablocks:

    def test_refresh_button_exists(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        assert hasattr(ed, "act_refresh_datablocks")

    def test_handler_warns_when_cache_empty(self, qapp, monkeypatch):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        called = []
        monkeypatch.setattr(
            QMessageBox, "information",
            lambda *args, **kw: called.append(args),
        )
        ed._on_refresh_datablocks()
        assert len(called) == 1
        # Mensagem menciona "análise"
        msg_text = " ".join(str(a) for a in called[0])
        assert "análise" in msg_text.lower() or "estudo" in msg_text.lower()

    def test_handler_warns_when_no_datablocks(self, qapp, monkeypatch):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        # Popula cache mas sem datablocks
        ed.scene.results_cache.set_pipeline_report(
            "BUS-X", _make_pipeline_report("BUS-X"),
        )
        called = []
        monkeypatch.setattr(
            QMessageBox, "information",
            lambda *args, **kw: called.append(args),
        )
        ed._on_refresh_datablocks()
        assert len(called) == 1
        msg = " ".join(str(a) for a in called[0])
        assert "datablock" in msg.lower()

    def test_handler_refreshes_when_both_present(self, qapp, monkeypatch):
        from app.gui.schematic_pp.editor import PpEditor
        from app.preprocessor.models import PpDataBlock
        ed = PpEditor()
        # 1) Cria BUS no scene
        ed.scene.add_component(_make_bus_component("BUS-9"))
        # 2) Cria datablock com placeholder SC
        db = PpDataBlock(
            component_name="BUS-9",
            lines=["Ik = {Ik_pp_kA:.2f} kA"],
        )
        ed.scene.add_datablock(db)
        # 3) Popula cache
        ed.scene.results_cache.set_pipeline_report(
            "BUS-9", _make_pipeline_report("BUS-9"),
        )
        # 4) Mock QMessageBox para não bloquear
        monkeypatch.setattr(
            QMessageBox, "information", lambda *args, **kw: None,
        )
        ed._on_refresh_datablocks()
        # Substituição feita
        assert db.lines == ["Ik = 15.30 kA"]
        # Undo restaura
        ed.undo_stack.undo()
        assert db.lines == ["Ik = {Ik_pp_kA:.2f} kA"]


# ---------------------------------------------------------------------------
# Resolver de bus_id (integração)
# ---------------------------------------------------------------------------


class TestResolveBusId:

    def test_resolves_via_props0(self, qapp):
        """component_name == PpComponent.name → retorna props[0]."""
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.datablock_binder import (
            _resolve_bus_id_for_component,
        )
        scene = PpScene()
        scene.add_component(_make_bus_component("BUS-MAIN"))
        # _make_bus_component define name=bus_id="BUS-MAIN", então
        # ambos casam. Vou sobrescrever name p/ testar.
        bus = scene.component_items()[0]
        bus.component.name = "B1"
        # bus_id permanece "BUS-MAIN" em props[0]
        result = _resolve_bus_id_for_component(scene, "B1")
        assert result == "BUS-MAIN"

    def test_resolves_via_bus_id_match(self, qapp):
        """component_name == bus_id (props[0]) → retorna props[0]."""
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.datablock_binder import (
            _resolve_bus_id_for_component,
        )
        scene = PpScene()
        scene.add_component(_make_bus_component("BUS-MAIN"))
        # Aqui name == bus_id. Mas vamos passar o bus_id explícito.
        result = _resolve_bus_id_for_component(scene, "BUS-MAIN")
        assert result == "BUS-MAIN"

    def test_returns_none_for_non_bus(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.datablock_binder import (
            _resolve_bus_id_for_component,
        )
        from app.preprocessor.models import PpComponent, PpProperty
        scene = PpScene()
        scene.add_component(PpComponent(
            type="R", name="R1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("1k")],
        ))
        result = _resolve_bus_id_for_component(scene, "R1")
        assert result is None
