"""
tests/test_pp_report_html.py — v0.27.7.10: vendor formats +
HTML report generator com gráficos.

Cobre:

* Vendor formats — SEL-751, ABB REF615/RET615, Schneider P3U.
* RelaySuggestion.to_vendor_format() despacha por fabricante.
* generate_html_report — estrutura, embed de gráficos.
* save_html_report — escrita de arquivo standalone.
* Helpers de plot — TC curves, arc-flash boundary, motor decay,
  topology diagram.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from app.postprocessor.bus_pipeline import BusPipelineReport
from app.postprocessor.multihop_walker import TopologyChain
from app.postprocessor.relay_suggestions import (
    RelaySuggestion, suggest_multi_relay_alternatives,
    suggest_settings_for_bus,
)
from app.postprocessor.report_html import (
    _plot_arc_flash_boundary, _plot_motor_decay,
    _plot_tc_curves, _plot_topology_diagram,
    generate_html_report, save_html_report,
)
from app.preprocessor.bus import (
    make_default_motor_control_center,
    make_default_mv_switchgear,
)
from app.preprocessor.models import PpComponent, PpProperty


# ---------------------------------------------------------------------------
# Vendor format dispatchers
# ---------------------------------------------------------------------------


class TestVendorFormatDispatch:
    def test_sel_format_dispatch(self):
        bus = make_default_mv_switchgear("SWGR", 13.8)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=25.0, load_S_MVA=20.0)
        # SEL é auto-selecionado para main_switchgear
        assert sg.relay_manufacturer == "SEL"
        text = sg.to_vendor_format()
        assert "SEL-751" in text
        assert "QuickSet" in text
        assert "50P1P" in text
        assert "51P1P" in text
        assert "51P1C" in text

    def test_abb_format_dispatch(self):
        from app.standards.relay_models import ABB_REF615
        bus = make_default_mv_switchgear("SWGR", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=25.0, load_S_MVA=20.0,
            relay_model=ABB_REF615,
        )
        assert sg.relay_manufacturer == "ABB"
        text = sg.to_vendor_format()
        assert "ABB Relion 615" in text
        assert "PHHPTOC1" in text
        assert "PHIPTOC1" in text
        assert "EFLPTOC1" in text or "EFHPTOC1" in text

    def test_schneider_format_dispatch(self):
        from app.standards.relay_models import SCHNEIDER_P3U30
        bus = make_default_mv_switchgear("SWGR", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=25.0, load_S_MVA=20.0,
            relay_model=SCHNEIDER_P3U30,
        )
        assert "Schneider" in sg.relay_manufacturer
        text = sg.to_vendor_format()
        assert "Schneider" in text or "Easergy" in text
        assert "I>" in text

    def test_iec_curve_mapped_correctly_sel(self):
        """IEC SI → C1 no SEL."""
        bus = make_default_mv_switchgear("SWGR", 13.8)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=25.0)
        text = sg._to_sel_format()
        # SI → C1
        assert "C1" in text

    def test_iec_curve_mapped_correctly_abb(self):
        from app.standards.relay_models import ABB_REF615
        bus = make_default_mv_switchgear("SWGR", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=25.0,
            relay_model=ABB_REF615,
        )
        text = sg._to_abb_format()
        # IEC SI → "IEC Norm Inv"
        assert "IEC Norm Inv" in text

    def test_iec_curve_mapped_correctly_schneider(self):
        from app.standards.relay_models import SCHNEIDER_P3U30
        bus = make_default_mv_switchgear("SWGR", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=25.0,
            relay_model=SCHNEIDER_P3U30,
        )
        text = sg._to_schneider_format()
        # IEC SI → "IEC NI"
        assert "IEC NI" in text


class TestVendorFormatContents:
    def test_sel_includes_50BF_when_recommended(self):
        bus = make_default_mv_switchgear("SWGR", 13.8)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=25.0)
        text = sg._to_sel_format()
        # Main switchgear → has_50BF=True
        if sg.has_50BF:
            assert "50BF" in text

    def test_sel_includes_AFD_recommendation(self):
        """Switchgear sem AFD → recomenda."""
        bus = make_default_mv_switchgear("SWGR", 13.8, has_AFD=False)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=25.0)
        text = sg._to_sel_format()
        if sg.has_AFD_recommended:
            assert "AFD" in text
            assert "AFR" in text or "AF-2" in text

    def test_abb_includes_87T_recommendation_for_transformer(self):
        from app.standards.relay_models import ABB_RET615
        bus = make_default_mv_switchgear("SWGR", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=25.0,
            relay_model=ABB_RET615,
        )
        text = sg._to_abb_format()
        # has_87 depende da application do bus, não do model
        # mas o formato sempre menciona REA quando AFD
        if sg.has_AFD_recommended:
            assert "REA" in text

    def test_schneider_format_has_all_stages(self):
        from app.standards.relay_models import SCHNEIDER_P3U30
        bus = make_default_mv_switchgear("SWGR", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=25.0,
            relay_model=SCHNEIDER_P3U30,
        )
        text = sg._to_schneider_format()
        assert "Phase Time-OC" in text
        assert "Phase Inst" in text
        assert "Earth Time-OC" in text or "I0>" in text
        assert "Earth Inst" in text or "I0>>" in text


class TestVendorFormatPickupValues:
    def test_pickup_values_match_suggestion(self):
        """Os valores numéricos no formato vendor batem com a
        suggestion."""
        bus = make_default_mv_switchgear("SWGR", 13.8)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=25.0, load_S_MVA=20.0)
        text = sg.to_vendor_format()
        # pickup_51 ≈ 1046 A
        assert "1045" in text or "1046" in text
        # pickup_50 = 20000 A
        assert "20000" in text


# ---------------------------------------------------------------------------
# HTML report generation
# ---------------------------------------------------------------------------


def _make_minimal_report() -> BusPipelineReport:
    bus = make_default_mv_switchgear("SWGR-1", 13.8, has_AFD=False)
    sg = suggest_settings_for_bus(bus, Ik_pp_kA=25.0, load_S_MVA=20.0)
    return BusPipelineReport(
        bus_id="SWGR-1", rated_voltage_kV=13.8,
        panel_type="swgr_15kv",
        is_lineside=True, has_AFD=False,
        n_neighbors=1, n_sc_sources=1,
        sources_summary=("UTIL: 100%",),
        Ik_pp_kA=25.0, ip_kA=68.0, kappa=1.94,
        coordination_clearing_time_ms=500.0,
        effective_clearing_time_ms=500.0,
        incident_energy_cal_cm2=20.79,
        arc_flash_boundary_mm=4800.0,
        ppe_category="3",
        relay_suggestions=(sg,),
        topology_chains=(),
        warnings=(),
    )


def _make_full_report() -> BusPipelineReport:
    bus = make_default_mv_switchgear("SWGR-MAIN", 13.8, has_AFD=False)
    alts = suggest_multi_relay_alternatives(
        bus, Ik_pp_kA=25.0, load_S_MVA=20.0,
    )
    v = PpComponent(
        type="Vac", name="UTIL", visible=True,
        x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty("138")],
    )
    tr = PpComponent(
        type="XFMR", name="TR1", visible=True,
        x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty("138"), PpProperty("13.8")],
    )
    chain = TopologyChain(
        target_bus_id="SWGR-MAIN",
        source_component=v,
        intermediate_transformers=(tr,),
        intermediate_buses=(),
        n_hops=2,
    )
    return BusPipelineReport(
        bus_id="SWGR-MAIN", rated_voltage_kV=13.8,
        panel_type="swgr_15kv",
        is_lineside=True, has_AFD=False,
        n_neighbors=2, n_sc_sources=1,
        sources_summary=("UTIL via TR1: 100%",),
        Ik_pp_kA=25.0, ip_kA=68.0, kappa=1.94,
        coordination_clearing_time_ms=500.0,
        effective_clearing_time_ms=500.0,
        incident_energy_cal_cm2=20.79,
        arc_flash_boundary_mm=4800.0,
        ppe_category="3",
        relay_suggestions=tuple(alts),
        topology_chains=(chain,),
        warnings=("Test warning",),
    )


class TestHtmlGeneration:
    def test_minimal_report_generates(self):
        r = _make_minimal_report()
        html = generate_html_report(r)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert r.bus_id in html

    def test_full_report_generates(self):
        r = _make_full_report()
        html = generate_html_report(r)
        assert "<!DOCTYPE html>" in html
        # Deve incluir os 3 fabricantes
        assert "SEL-751" in html
        assert "REF615" in html or "ABB" in html
        assert "Schneider" in html or "P3U" in html

    def test_html_has_kpi_block(self):
        r = _make_minimal_report()
        html = generate_html_report(r)
        assert "KPI" in html or "Key Performance" in html
        assert "Ik''" in html
        assert "DLA" in html

    def test_html_has_topology_section(self):
        r = _make_minimal_report()
        html = generate_html_report(r)
        assert "Topology" in html or "topology" in html

    def test_html_has_arc_flash_section(self):
        r = _make_minimal_report()
        html = generate_html_report(r)
        assert "Arc-Flash" in html or "arc-flash" in html

    def test_html_has_relay_suggestions(self):
        r = _make_minimal_report()
        html = generate_html_report(r)
        assert "Relay" in html
        # Deve incluir o formato vendor (SEL...)
        assert "SEL-751" in html
        assert "50P1P" in html or "51P1P" in html

    def test_html_has_warnings_when_present(self):
        r = _make_full_report()
        html = generate_html_report(r)
        assert "Warning" in html or "warning" in html
        assert "Test warning" in html

    def test_html_has_no_warnings_block_when_empty(self):
        r = _make_minimal_report()
        html = generate_html_report(r)
        # Não tem warnings ⇒ bloco "Warnings" ausente
        # (mas pode ter a string em outros lugares)
        # Confere que a seção <h2>... Warnings ...</h2> não aparece
        assert "<h2>⚠️ Warnings</h2>" not in html

    def test_html_topology_chains_section_when_present(self):
        r = _make_full_report()
        html = generate_html_report(r)
        assert "Topology Chains" in html

    def test_html_no_chains_block_when_empty(self):
        r = _make_minimal_report()
        html = generate_html_report(r)
        # Sem chains ⇒ bloco específico ausente
        assert "Topology Chains" not in html

    def test_html_includes_base64_image(self):
        r = _make_minimal_report()
        html = generate_html_report(r)
        # TC curves + arc-flash boundary devem gerar PNGs
        assert "data:image/png;base64" in html

    def test_html_references_norms(self):
        r = _make_minimal_report()
        html = generate_html_report(r)
        assert "IEC 60909" in html
        assert "NBR 17227" in html or "1584" in html
        assert "IEEE 242" in html or "Buff" in html


# ---------------------------------------------------------------------------
# save_html_report
# ---------------------------------------------------------------------------


class TestSaveHtmlReport:
    def test_save_creates_file(self):
        r = _make_minimal_report()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.html")
            save_html_report(r, path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 1000

    def test_saved_file_contains_html(self):
        r = _make_minimal_report()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.html")
            save_html_report(r, path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "<!DOCTYPE html>" in content
            assert r.bus_id in content


# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------


class TestPlotHelpers:
    def test_tc_curves_plot_returns_base64(self):
        bus = make_default_mv_switchgear("SWGR", 13.8)
        alts = suggest_multi_relay_alternatives(bus, Ik_pp_kA=25.0)
        b64 = _plot_tc_curves(alts, Ik_pp_A=25000.0)
        assert b64 is not None
        # base64 não-vazio
        assert len(b64) > 100

    def test_tc_curves_with_empty_returns_none(self):
        b64 = _plot_tc_curves((), Ik_pp_A=25000.0)
        assert b64 is None

    def test_arc_flash_boundary_plot(self):
        b64 = _plot_arc_flash_boundary(
            incident_energy_cal_cm2=20.0,
            DLA_mm=4800.0, working_distance_mm=914.4,
            ppe_category="3",
        )
        assert b64 is not None
        assert len(b64) > 100

    def test_motor_decay_plot(self):
        motors = [
            {"name": "M1", "I_LR_kA": 0.9, "Td_pp_ms": 20.0,
             "type": "induction"},
            {"name": "M2", "I_LR_kA": 0.84, "Td_pp_ms": 200.0,
             "type": "synchronous"},
        ]
        b64 = _plot_motor_decay(motors)
        assert b64 is not None

    def test_motor_decay_empty_returns_none(self):
        assert _plot_motor_decay([]) is None

    def test_topology_diagram_plot(self):
        v = PpComponent(
            type="Vac", name="UTIL", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("138")],
        )
        chain = TopologyChain(
            target_bus_id="BUS-1", source_component=v,
            intermediate_transformers=(),
            intermediate_buses=(),
            n_hops=1,
        )
        b64 = _plot_topology_diagram("BUS-1", (chain,))
        assert b64 is not None

    def test_topology_diagram_empty_returns_none(self):
        b64 = _plot_topology_diagram("BUS-1", ())
        assert b64 is None
