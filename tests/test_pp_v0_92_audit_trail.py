"""
tests/test_pp_v0_92_audit_trail.py — v0.92:

Auditoria das primitivas de auditabilidade para relatórios
profissionais.

Cobertura:

* ``citation()`` formata referências normativas conforme
  catálogo (IEC, NBR, IEEE, NFPA).
* ``compute_input_checksum()`` é estável (mesma entrada →
  mesmo digest, independente da ordem das chaves).
* ``AuditHeader.to_text()`` e ``to_html()`` incluem todos os
  campos esperados.
* ``KNOWN_LIMITATIONS`` cobre as 7 heurísticas declaradas
  do MVP.
* ``format_limitations_block()`` e ``format_limitations_html()``
  rendem todas as keys válidas.
* Integration: ``generate_html_report()`` e
  ``save_pdf_report()`` agora incluem audit header,
  citações por linha, e bloco de limitações.

Princípio testado: rastreabilidade ISO 9001 / NR-10
(software, timestamp, checksum, responsável, normas,
limitações).
"""

from __future__ import annotations

import os
import tempfile

import pytest

from app.postprocessor.audit_trail import (
    AuditHeader,
    KNOWN_LIMITATIONS,
    STANDARDS_CATALOG,
    citation,
    compute_input_checksum,
    format_limitations_block,
    format_limitations_html,
    make_audit_header,
)


# ---------------------------------------------------------------------------
# citation()
# ---------------------------------------------------------------------------


class TestCitation:

    def test_citation_with_section_and_equation(self):
        """v0.92: citação completa com seção + eq."""
        c = citation("IEC 60909-0", "§4.3.1", "Eq.(31)")
        assert c == "IEC 60909-0:2016 §4.3.1 Eq.(31)"

    def test_citation_no_section(self):
        """v0.92: só nome da norma."""
        c = citation("IEEE 1584")
        assert c == "IEEE Std 1584-2018"

    def test_citation_with_extra(self):
        """v0.92: 'extra' aparece entre parênteses no fim."""
        c = citation("NBR 17227", "§5.2.6.2", "Eq.(3-6)", "VCB cabinet")
        assert c == (
            "ABNT NBR 17227:2025 §5.2.6.2 Eq.(3-6) (VCB cabinet)"
        )

    def test_citation_uncatalogued(self):
        """v0.92: norma fora do catálogo usa nome direto."""
        c = citation("ISO 99999", "§A.1")
        assert c == "ISO 99999 §A.1"

    def test_standards_catalog_minimum_count(self):
        """v0.92: catálogo cobre IEC/IEEE/NBR/NFPA/NR essenciais."""
        # IEC, NBR, IEEE, NFPA, NR — pelo menos 5 famílias
        keys = set(STANDARDS_CATALOG.keys())
        assert "IEC 60909-0" in keys
        assert "NBR 17227" in keys
        assert "IEEE 1584" in keys
        assert "IEEE 242" in keys
        assert "NFPA 70E" in keys
        assert "NR-10" in keys
        # E pelo menos 10 entradas
        assert len(keys) >= 10


# ---------------------------------------------------------------------------
# compute_input_checksum()
# ---------------------------------------------------------------------------


class TestChecksum:

    def test_checksum_is_sha256_hex(self):
        """v0.92: digest tem 64 chars hex."""
        d = compute_input_checksum({"x": 1})
        assert len(d) == 64
        assert all(c in "0123456789abcdef" for c in d)

    def test_checksum_stable_dict_order(self):
        """v0.92: mesmos dados em ordem diferente → mesmo digest."""
        d1 = compute_input_checksum({"a": 1, "b": 2, "c": 3})
        d2 = compute_input_checksum({"c": 3, "a": 1, "b": 2})
        assert d1 == d2

    def test_checksum_different_for_different_data(self):
        """v0.92: dados diferentes → digests diferentes."""
        d1 = compute_input_checksum({"x": 1})
        d2 = compute_input_checksum({"x": 2})
        assert d1 != d2

    def test_checksum_handles_dataclass(self):
        """v0.92: dataclass é serializado via asdict."""
        from dataclasses import dataclass

        @dataclass
        class _Sample:
            a: int
            b: str

        d1 = compute_input_checksum(_Sample(a=1, b="x"))
        d2 = compute_input_checksum({"a": 1, "b": "x"})
        # Mesmo conteúdo (após asdict) → mesmo digest
        assert d1 == d2

    def test_checksum_handles_nested(self):
        """v0.92: estruturas aninhadas funcionam."""
        d = compute_input_checksum({
            "items": [1, 2, {"k": "v"}],
            "meta": {"v": 0.92},
        })
        assert len(d) == 64

    def test_checksum_handles_set(self):
        """v0.92: sets são ordenados antes de hash (estabilidade)."""
        d1 = compute_input_checksum({"s": {3, 1, 2}})
        d2 = compute_input_checksum({"s": {1, 2, 3}})
        assert d1 == d2

    def test_checksum_handles_complex(self):
        """v0.92: complex serializado como [real, imag]."""
        d = compute_input_checksum({"z": complex(1, 2)})
        assert len(d) == 64

    def test_checksum_handles_arbitrary_object(self):
        """v0.92: objetos não-serializáveis caem no fallback repr."""

        class _Custom:
            pass

        d = compute_input_checksum({"obj": _Custom()})
        assert len(d) == 64  # Não deve crashar


# ---------------------------------------------------------------------------
# AuditHeader
# ---------------------------------------------------------------------------


class TestAuditHeader:

    def test_to_text_contains_all_fields(self):
        """v0.92: representação texto plano tem todos os campos."""
        h = AuditHeader(
            report_kind="Curto-circuito",
            software_name="Olivas ATP Studio",
            software_version="0.92.0",
            timestamp_iso="2026-04-26T10:00:00",
            input_checksum="a" * 64,
            standards_applied=["IEC 60909-0", "NBR 17227"],
            responsible_engineer="Eng. João Silva",
            crea_number="CREA-MG 1234567",
            art_number="ART-2026/000001",
            notes="Observação técnica.",
        )
        txt = h.to_text()
        assert "RELATÓRIO TÉCNICO" in txt
        assert "Curto-circuito" in txt
        assert "0.92.0" in txt
        assert "2026-04-26T10:00:00" in txt
        assert "SHA256:" in txt
        assert "aaaaaaaa" in txt   # primeiros 16 chars
        assert "IEC 60909-0:2016" in txt   # full title via catalog
        assert "ABNT NBR 17227:2025" in txt
        assert "Eng. João Silva" in txt
        assert "CREA-MG 1234567" in txt
        assert "Observação técnica" in txt

    def test_to_text_with_empty_responsible(self):
        """v0.92: campos vazios viram placeholder ____."""
        h = AuditHeader(
            report_kind="X",
            software_name="Y",
            software_version="0",
            timestamp_iso="t",
            input_checksum="c",
            standards_applied=[],
        )
        txt = h.to_text()
        assert "____" in txt   # Placeholder visible

    def test_to_html_contains_all_fields(self):
        """v0.92: HTML tem audit-header div, table, e checksum."""
        h = AuditHeader(
            report_kind="Curto-circuito",
            software_name="Olivas ATP Studio",
            software_version="0.92.0",
            timestamp_iso="2026-04-26T10:00:00",
            input_checksum="a" * 64,
            standards_applied=["IEC 60909-0"],
            responsible_engineer="Eng. João Silva",
            crea_number="CREA-MG 1234567",
            art_number="ART-2026/000001",
            notes="Nota livre.",
        )
        html = h.to_html()
        assert "audit-header" in html
        assert "audit-meta" in html
        assert "Olivas ATP Studio v0.92.0" in html
        assert "SHA256:aaaaaaaa" in html
        assert "Eng. João Silva" in html
        assert "Nota livre" in html
        assert "<code>" in html   # checksum em mono
        assert "<ul>" in html   # normas em lista

    def test_to_html_empty_fields_show_placeholder(self):
        """v0.92: HTML com '(a preencher)' quando vazio."""
        h = AuditHeader(
            report_kind="X",
            software_name="Y",
            software_version="0",
            timestamp_iso="t",
            input_checksum="c",
            standards_applied=["IEC 60909-0"],
        )
        html = h.to_html()
        assert "a preencher" in html


# ---------------------------------------------------------------------------
# make_audit_header() integration
# ---------------------------------------------------------------------------


class TestMakeAuditHeader:

    def test_make_header_uses_app_version(self):
        """v0.92: make_audit_header lê app.core.version.VERSION."""
        h = make_audit_header(
            report_kind="Test",
            inputs={"a": 1},
            standards_applied=["IEC 60909-0"],
        )
        # VERSION pode ser "?", "0.92.x" ou similar — só checa que
        # software_version foi setado (não vazio)
        assert h.software_version
        # v0.92.2: rebrand para "Olivas Power System Studio"
        assert h.software_name == "Olivas Power System Studio"

    def test_make_header_computes_checksum(self):
        """v0.92: checksum é computado dos inputs."""
        h = make_audit_header(
            report_kind="Test",
            inputs={"a": 1},
            standards_applied=[],
        )
        # Mesmos inputs → mesmo checksum
        h2 = make_audit_header(
            report_kind="Other",
            inputs={"a": 1},
            standards_applied=["IEC 60909-0"],
        )
        assert h.input_checksum == h2.input_checksum

    def test_make_header_different_inputs_different_checksum(self):
        """v0.92: inputs diferentes → checksums diferentes."""
        h1 = make_audit_header("X", {"a": 1}, [])
        h2 = make_audit_header("X", {"a": 2}, [])
        assert h1.input_checksum != h2.input_checksum

    def test_make_header_timestamp_is_iso(self):
        """v0.92: timestamp formato ISO 8601."""
        h = make_audit_header("X", {}, [])
        # "2026-04-26T10:00:00" — pelo menos contém T
        assert "T" in h.timestamp_iso


# ---------------------------------------------------------------------------
# Limitations
# ---------------------------------------------------------------------------


class TestLimitations:

    def test_known_limitations_cover_audit_findings(self):
        """v0.92: dicionário cobre as 7 limitações da auditoria."""
        expected_keys = {
            "sc_ib_far_only",
            "sc_method_b_kappa",
            "arc_flash_lv_only",
            "arc_flash_3p_only",
            "pf_positive_seq_only",
            "pf_no_q_limits",
            "coord_no_auto_dt_min",
        }
        assert expected_keys.issubset(set(KNOWN_LIMITATIONS.keys()))

    def test_format_limitations_block_filters_keys(self):
        """v0.92: só rende keys passadas, ignora outras."""
        txt = format_limitations_block(["sc_ib_far_only"])
        assert "factor μ·q" in txt
        # Não deve incluir limitação não pedida
        assert "Method B" not in txt
        assert "LIMITAÇÕES TÉCNICAS APLICADAS" in txt

    def test_format_limitations_block_empty(self):
        """v0.92: lista vazia → string vazia."""
        assert format_limitations_block([]) == ""

    def test_format_limitations_html_uses_warning_class(self):
        """v0.92: HTML tem class audit-limitations + lista."""
        html = format_limitations_html(["sc_ib_far_only"])
        assert "audit-limitations" in html
        assert "<ul>" in html
        assert "<li>" in html
        assert "factor μ·q" in html

    def test_format_limitations_html_empty(self):
        """v0.92: lista vazia → string vazia."""
        assert format_limitations_html([]) == ""

    def test_format_limitations_html_skips_unknown_keys(self):
        """v0.92: keys desconhecidas são silenciosamente ignoradas."""
        html = format_limitations_html(["nonexistent_key"])
        # Deve retornar string vazia (nenhum item válido)
        assert html == ""

    def test_format_limitations_html_mixed_keys(self):
        """v0.92: mistura de keys válidas + inválidas inclui só válidas."""
        html = format_limitations_html(["sc_ib_far_only", "bogus"])
        assert "factor μ·q" in html
        # Só uma <li> renderizada
        assert html.count("<li>") == 1


# ---------------------------------------------------------------------------
# Integration: report_html.py
# ---------------------------------------------------------------------------


class TestReportHtmlIntegration:

    def _make_report(self):
        from app.postprocessor.bus_pipeline import BusPipelineReport
        return BusPipelineReport(
            bus_id="BUS-MAIN-13.8",
            rated_voltage_kV=13.8,
            panel_type="MV switchgear",
            is_lineside=True,
            has_AFD=False,
            n_neighbors=3,
            n_sc_sources=2,
            sources_summary=("GEN1: 69%", "UTIL: 31%"),
            Ik_pp_kA=12.5,
            ip_kA=31.7,
            kappa=1.78,
            coordination_clearing_time_ms=500.0,
            effective_clearing_time_ms=500.0,
            incident_energy_cal_cm2=8.4,
            arc_flash_boundary_mm=1240.0,
            ppe_category="2",
            relay_suggestions=(),
            topology_chains=(),
            Ib_kA=12.5,
            Ik_steady_kA=8.7,
        )

    def test_html_includes_audit_header(self):
        """v0.92: HTML report tem audit header no topo."""
        from app.postprocessor.report_html import generate_html_report
        html = generate_html_report(self._make_report())
        assert "audit-header" in html
        assert "SHA256:" in html
        assert "RELATÓRIO TÉCNICO" in html

    def test_html_includes_citations_per_value(self):
        """v0.92: cada parâmetro tem norma + equação."""
        from app.postprocessor.report_html import generate_html_report
        html = generate_html_report(self._make_report())
        # IEC 60909-0 §4.3.1 Eq.(31) para Ik''
        assert "§4.3.1" in html and "Eq.(31)" in html
        # NBR 17227 §5.2.6.2 Eq.(3-6) para incident energy
        assert "§5.2.6.2" in html and "Eq.(3-6)" in html
        # NFPA 70E para PPE
        assert "NFPA 70E:2024" in html

    def test_html_includes_limitations_block(self):
        """v0.92: bloco de limitações está presente."""
        from app.postprocessor.report_html import generate_html_report
        html = generate_html_report(self._make_report())
        assert "audit-limitations" in html
        assert "Limitações técnicas aplicadas" in html
        # Pelo menos sc_ib_far_only e arc_flash_lv_only
        assert "factor μ·q" in html
        assert "≤15 kV" in html or "15 kV" in html

    def test_html_passes_through_responsible_engineer(self):
        """v0.92: kwargs do save_html_report fluem para o header."""
        from app.postprocessor.report_html import generate_html_report
        html = generate_html_report(
            self._make_report(),
            responsible_engineer="Eng. Test",
            crea_number="CREA-MG 999",
            art_number="ART-X",
            notes="My note here",
        )
        assert "Eng. Test" in html
        assert "CREA-MG 999" in html
        assert "ART-X" in html
        assert "My note here" in html


# ---------------------------------------------------------------------------
# Integration: report_pdf.py
# ---------------------------------------------------------------------------


class TestReportPdfIntegration:

    def _make_report(self):
        from app.postprocessor.bus_pipeline import BusPipelineReport
        return BusPipelineReport(
            bus_id="BUS-MAIN-13.8",
            rated_voltage_kV=13.8,
            panel_type="MV switchgear",
            is_lineside=True,
            has_AFD=False,
            n_neighbors=2,
            n_sc_sources=1,
            sources_summary=("UTIL: 100%",),
            Ik_pp_kA=10.0,
            ip_kA=25.0,
            kappa=1.65,
            coordination_clearing_time_ms=400.0,
            effective_clearing_time_ms=400.0,
            incident_energy_cal_cm2=5.0,
            arc_flash_boundary_mm=900.0,
            ppe_category="2",
            relay_suggestions=(),
            topology_chains=(),
            Ib_kA=10.0,
            Ik_steady_kA=7.0,
        )

    def test_pdf_generates_with_audit_cover(self):
        """v0.92: PDF gera com nova capa audit + página limitações."""
        from app.postprocessor.report_pdf import save_pdf_report
        with tempfile.NamedTemporaryFile(
            suffix=".pdf", delete=False,
        ) as tf:
            path = tf.name
        try:
            save_pdf_report(
                self._make_report(), path,
                responsible_engineer="Eng. PDF Test",
                crea_number="CREA-001",
            )
            sz = os.path.getsize(path)
            # PDF mínimo (capa + 6 páginas + limitações + warnings)
            # — ~60 KB para A4 vetorial básico
            assert sz > 30_000, f"PDF muito pequeno ({sz} bytes)"
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Repro doctest examples from module docstrings
# ---------------------------------------------------------------------------


class TestModuleDocstrings:

    def test_doctest_compute_input_checksum_stable(self):
        """v0.92: doctest do compute_input_checksum."""
        a = compute_input_checksum({"a": 1, "b": 2})
        b = compute_input_checksum({"b": 2, "a": 1})
        assert a == b

    def test_doctest_citation_iec(self):
        """v0.92: doctest exemplo IEC 60909."""
        assert (
            citation("IEC 60909-0", "§4.3.1", "Eq.(31)")
            == "IEC 60909-0:2016 §4.3.1 Eq.(31)"
        )

    def test_doctest_format_limitations_block_contains_mu_q(self):
        """v0.92: doctest format_limitations_block."""
        txt = format_limitations_block(["sc_ib_far_only"])
        assert "factor μ·q" in txt
