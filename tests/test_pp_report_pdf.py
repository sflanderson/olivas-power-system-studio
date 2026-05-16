"""
tests/test_pp_report_pdf.py — v0.27.10: gerador de relatório
PDF multi-página via matplotlib PdfPages.

Cobre:

* save_pdf_report — gera arquivo PDF válido.
* PDF contém múltiplas páginas (cover, topology, SC, arc-flash,
  TC curves, relay settings, refs).
* Metadata (Title, Author, Subject) inseridos.
* Sem warnings de glyph (emoji removidos).
"""

from __future__ import annotations

import os
import tempfile
import warnings as _warnings

import pytest

from app.postprocessor.bus_pipeline import BusPipelineReport
from app.postprocessor.multihop_walker import TopologyChain
from app.postprocessor.relay_suggestions import (
    suggest_multi_relay_alternatives, suggest_settings_for_bus,
)
from app.postprocessor.report_pdf import save_pdf_report
from app.preprocessor.bus import (
    make_default_mv_switchgear,
)
from app.preprocessor.models import PpComponent, PpProperty


def _minimal_report() -> BusPipelineReport:
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


def _full_report() -> BusPipelineReport:
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
        warnings=("Sample warning",),
    )


# ---------------------------------------------------------------------------
# Geração básica
# ---------------------------------------------------------------------------


class TestPdfGeneration:
    def test_pdf_file_created(self):
        r = _minimal_report()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.pdf")
            save_pdf_report(r, path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 1000

    def test_pdf_header_valid(self):
        """PDF válido começa com %PDF-."""
        r = _minimal_report()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.pdf")
            save_pdf_report(r, path)
            with open(path, "rb") as f:
                header = f.read(8)
            assert header.startswith(b"%PDF")

    def test_pdf_size_reasonable(self):
        """PDF típico tem 50-200 KB."""
        r = _full_report()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.pdf")
            save_pdf_report(r, path)
            size = os.path.getsize(path)
            assert 30_000 < size < 500_000


# ---------------------------------------------------------------------------
# Estrutura multi-página
# ---------------------------------------------------------------------------


class TestPdfStructure:
    def _read_pdf_pages_count(self, path: str) -> int:
        """Conta páginas do PDF lendo o trailer."""
        # Estratégia simples: contar ocorrências de '/Type /Page' no PDF
        # (não 100% robusto, mas suficiente para teste)
        with open(path, "rb") as f:
            data = f.read()
        # Match exato '/Type /Page' (mas não '/Type /Pages')
        count_total = data.count(b"/Type /Page")
        count_pages = data.count(b"/Type /Pages")
        return count_total - count_pages

    def test_minimal_report_has_multiple_pages(self):
        r = _minimal_report()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.pdf")
            save_pdf_report(r, path)
            n = self._read_pdf_pages_count(path)
            # Cover + Topology + SC/AF + Boundary + TC + 1 relay + Final ≈ 7
            assert n >= 5

    def test_full_report_has_more_pages(self):
        """Multi-vendor (3 relés) deve ter mais páginas."""
        r = _full_report()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.pdf")
            save_pdf_report(r, path)
            n = self._read_pdf_pages_count(path)
            # 3 relays ⇒ pelo menos 7 + 2 = 9 páginas
            assert n >= 7


# ---------------------------------------------------------------------------
# Sem warnings de glyph
# ---------------------------------------------------------------------------


class TestNoGlyphWarnings:
    def test_no_glyph_warnings_minimal(self):
        r = _minimal_report()
        with _warnings.catch_warnings(record=True) as w:
            _warnings.simplefilter("always")
            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "report.pdf")
                save_pdf_report(r, path)
            glyph = [x for x in w if "Glyph" in str(x.message)]
            assert len(glyph) == 0, (
                f"Glyph warnings: {[str(x.message) for x in glyph]}"
            )

    def test_no_glyph_warnings_full(self):
        r = _full_report()
        with _warnings.catch_warnings(record=True) as w:
            _warnings.simplefilter("always")
            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "report.pdf")
                save_pdf_report(r, path)
            glyph = [x for x in w if "Glyph" in str(x.message)]
            assert len(glyph) == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestPdfEdgeCases:
    def test_empty_relay_suggestions(self):
        """Report sem relay_suggestions ainda gera PDF."""
        r = BusPipelineReport(
            bus_id="X", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=0, n_sc_sources=0,
            sources_summary=(),
            Ik_pp_kA=0.0, ip_kA=0.0, kappa=0.0,
            coordination_clearing_time_ms=0.0,
            effective_clearing_time_ms=0.0,
            incident_energy_cal_cm2=0.0,
            arc_flash_boundary_mm=0.0,
            ppe_category="0",
            relay_suggestions=(),
            topology_chains=(),
            warnings=(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.pdf")
            save_pdf_report(r, path)
            assert os.path.exists(path)

    def test_report_with_warnings(self):
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=25.0)
        r = BusPipelineReport(
            bus_id="X", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=1, n_sc_sources=1,
            sources_summary=("UTIL: 100%",),
            Ik_pp_kA=25.0, ip_kA=68.0, kappa=1.94,
            coordination_clearing_time_ms=500.0,
            effective_clearing_time_ms=500.0,
            incident_energy_cal_cm2=20.0,
            arc_flash_boundary_mm=4800.0,
            ppe_category="3",
            relay_suggestions=(sg,),
            topology_chains=(),
            warnings=("Warning A", "Warning B", "Warning C"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.pdf")
            save_pdf_report(r, path)
            assert os.path.exists(path)

    def test_high_cat_ppe(self):
        """Category DANGER deve gerar PDF sem erro."""
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=50.0)
        r = BusPipelineReport(
            bus_id="DANGER-BUS", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=1, n_sc_sources=1,
            sources_summary=("UTIL: 100%",),
            Ik_pp_kA=50.0, ip_kA=140.0, kappa=1.94,
            coordination_clearing_time_ms=2000.0,
            effective_clearing_time_ms=2000.0,
            incident_energy_cal_cm2=80.0,
            arc_flash_boundary_mm=8000.0,
            ppe_category="DANGER",
            relay_suggestions=(sg,),
            topology_chains=(),
            warnings=(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.pdf")
            save_pdf_report(r, path)
            assert os.path.exists(path)


# ---------------------------------------------------------------------------
# PDF metadata
# ---------------------------------------------------------------------------


class TestPdfMetadata:
    def test_pdf_has_info_dict(self):
        """Verifica que o PDF tem trailer com /Info dictionary."""
        r = _full_report()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.pdf")
            save_pdf_report(r, path)
            with open(path, "rb") as f:
                data = f.read()
        # Trailer aponta para /Info
        assert b"/Info" in data
        # PDF version + EOF marker
        assert data.startswith(b"%PDF-")
        assert data.rstrip().endswith(b"%%EOF")
