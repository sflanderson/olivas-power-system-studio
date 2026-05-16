"""
tests/test_pp_v3_0_5_ansi_report_container.py — v3.0.5 Sprint D.2.

AnsiFaultReport — container para múltiplos buses + text/markdown formatter.

Reproduz formato dos reports publicados no manual A_Fault §1.4.x,
incluindo headers, tabelas alinhadas, citações de norma + valores.

Anti-alucinação: cita §1.4.x do manual.
Anti-simplismo: cobre 3 formats (text/markdown/csv) + multi-bus.

Reference: PTW Reference-A_Fault.pdf §1.4.1 a §1.4.4.
"""

from __future__ import annotations

import pytest


# ===========================================================================
# Sprint D.2.A — AnsiFaultReport container
# ===========================================================================


class TestAnsiFaultReport:

    def test_empty_report_construction(self):
        """Report sem buses — válido (pode ser populado depois)."""
        from app.postprocessor.ansi_fault_report import AnsiFaultReport
        report = AnsiFaultReport(project_name="Test")
        assert report.project_name == "Test"
        assert report.buses == []

    def test_add_single_bus(self):
        """Adicionar 1 bus ao report."""
        from app.postprocessor.ansi_fault_report import (
            AnsiFaultBus, AnsiFaultReport,
        )
        report = AnsiFaultReport(project_name="Test")
        bus = AnsiFaultBus(
            bus_name="B2", kv_base=4.16, sym_rms_kA=13.598, x_over_r=14.85,
        )
        report.add_bus(bus)
        assert len(report.buses) == 1

    def test_add_multiple_buses_plant_144(self):
        """
        §1.4.4 Plant Project: 5 buses publicados.
        AnsiFaultReport deve suportar todos.
        """
        from app.postprocessor.ansi_fault_report import (
            AnsiFaultBus, AnsiFaultReport,
        )
        report = AnsiFaultReport(project_name="Plant Project")
        buses_data = [
            ("BLDG_115_SERV", 4.16, 10.560, 7.03),
            ("025-MTR-25", 4.16, 8.786, 6.07),
            ("026-TX-G-PRI", 4.16, 8.558, 3.10),
            ("027-DSB-3", 0.480, 38.277, 3.69),
            ("028-MTR-28", 0.480, 21.638, 2.85),
        ]
        for name, kv, i, xr in buses_data:
            report.add_bus(AnsiFaultBus(
                bus_name=name, kv_base=kv, sym_rms_kA=i, x_over_r=xr,
            ))
        assert len(report.buses) == 5


# ===========================================================================
# Sprint D.2.B — Text format (PTW-style)
# ===========================================================================


class TestTextFormat:

    def test_format_text_includes_header(self):
        """Text format deve ter cabeçalho ANSI/PTW-style."""
        from app.postprocessor.ansi_fault_report import (
            AnsiFaultBus, AnsiFaultReport,
        )
        report = AnsiFaultReport(project_name="TestProject")
        report.add_bus(AnsiFaultBus(
            bus_name="B2", kv_base=4.16,
            sym_rms_kA=13.598, x_over_r=14.85,
        ))
        text = report.format_text()
        # Header deve incluir nome do projeto e identificação ANSI
        assert "TestProject" in text
        assert "ANSI" in text

    def test_format_text_includes_bus_data(self):
        """Text deve listar dados do bus."""
        from app.postprocessor.ansi_fault_report import (
            AnsiFaultBus, AnsiFaultReport,
        )
        report = AnsiFaultReport(project_name="Test")
        report.add_bus(AnsiFaultBus(
            bus_name="B2", kv_base=4.16,
            sym_rms_kA=13.598, x_over_r=14.85,
        ))
        text = report.format_text()
        assert "B2" in text
        assert "13.598" in text or "13.60" in text  # current
        assert "14.85" in text or "14.9" in text   # X/R

    def test_format_text_cites_manual(self):
        """
        Anti-alucinação: text format deve citar o manual reference.
        """
        from app.postprocessor.ansi_fault_report import (
            AnsiFaultBus, AnsiFaultReport,
        )
        report = AnsiFaultReport(project_name="Test")
        report.add_bus(AnsiFaultBus(
            bus_name="B2", kv_base=4.16,
            sym_rms_kA=13.598, x_over_r=14.85,
        ))
        text = report.format_text()
        assert "C37" in text or "PTW" in text or "A_Fault" in text


# ===========================================================================
# Sprint D.2.C — Markdown format (Olivas-specific superação)
# ===========================================================================


class TestMarkdownFormat:

    def test_format_markdown_uses_table(self):
        """Markdown format usa tabela (`|`) — superação visual vs PTW text-only."""
        from app.postprocessor.ansi_fault_report import (
            AnsiFaultBus, AnsiFaultReport,
        )
        report = AnsiFaultReport(project_name="Test")
        for i, name in enumerate(["B1", "B2", "B3"]):
            report.add_bus(AnsiFaultBus(
                bus_name=name, kv_base=4.16,
                sym_rms_kA=10.0 + i, x_over_r=10.0,
            ))
        md = report.format_markdown()
        # Markdown table separator
        assert "|" in md
        assert "---" in md  # markdown table header divider

    def test_format_markdown_has_h2_per_bus(self):
        """Markdown structure: ## per bus."""
        from app.postprocessor.ansi_fault_report import (
            AnsiFaultBus, AnsiFaultReport,
        )
        report = AnsiFaultReport(project_name="Test")
        report.add_bus(AnsiFaultBus(
            bus_name="B2", kv_base=4.16,
            sym_rms_kA=13.598, x_over_r=14.85,
        ))
        md = report.format_markdown()
        assert "##" in md  # at least one h2


# ===========================================================================
# Sprint D.2.D — CSV format (datablock-style export)
# ===========================================================================


class TestCsvFormat:

    def test_format_csv_has_header_row(self):
        """CSV deve ter row de header com nomes das colunas."""
        from app.postprocessor.ansi_fault_report import (
            AnsiFaultBus, AnsiFaultReport,
        )
        report = AnsiFaultReport(project_name="Test")
        report.add_bus(AnsiFaultBus(
            bus_name="B2", kv_base=4.16,
            sym_rms_kA=13.598, x_over_r=14.85,
        ))
        csv = report.format_csv()
        first_line = csv.splitlines()[0]
        assert "bus_name" in first_line.lower() or "bus" in first_line.lower()
        assert "kv" in first_line.lower()

    def test_format_csv_has_one_row_per_bus(self):
        """CSV deve ter N+1 linhas (header + N buses)."""
        from app.postprocessor.ansi_fault_report import (
            AnsiFaultBus, AnsiFaultReport,
        )
        report = AnsiFaultReport(project_name="Test")
        for i in range(3):
            report.add_bus(AnsiFaultBus(
                bus_name=f"B{i}", kv_base=4.16,
                sym_rms_kA=10.0, x_over_r=10.0,
            ))
        csv = report.format_csv()
        lines = csv.splitlines()
        # Header + 3 buses = 4 lines minimum
        assert len(lines) >= 4
