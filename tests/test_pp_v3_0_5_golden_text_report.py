"""
tests/test_pp_v3_0_5_golden_text_report.py — v3.0.5 Sprint D.3.

Golden text reproduction — §1.4.4 Plant Project formato output.

Anti-alucinação MÁXIMA: reproduce o formato do report do manual com
valores PUBLICADOS, garantindo que o output do Olivas é estruturalmente
equivalente ao do PTW.

Reference: PTW Reference-A_Fault.pdf §1.4.4 p. 1-41/1-50.
"""

from __future__ import annotations

import pytest


# ===========================================================================
# Sprint D.3.A — §1.4.4 Plant Project full report
# ===========================================================================


class TestPlant144FullReport:

    def _build_plant_report(self):
        """Helper: constrói o AnsiFaultReport completo do Plant §1.4.4."""
        from app.postprocessor.ansi_fault_report import (
            AnsiFaultBus, AnsiFaultReport,
        )
        report = AnsiFaultReport(project_name="Plant Project (§1.4.4)")
        # 5 buses publicados
        plant_buses = [
            ("BLDG_115_SERV", 4.16, 10.560, 7.03),
            ("025-MTR-25", 4.16, 8.786, 6.07),
            ("026-TX-G-PRI", 4.16, 8.558, 3.10),
            ("027-DSB-3", 0.480, 38.277, 3.69),
            ("028-MTR-28", 0.480, 21.638, 2.85),
        ]
        for name, kv, i, xr in plant_buses:
            report.add_bus(AnsiFaultBus(
                bus_name=name, kv_base=kv, sym_rms_kA=i, x_over_r=xr,
            ))
        return report

    def test_text_format_includes_all_5_buses(self):
        """Text format deve listar os 5 buses publicados."""
        report = self._build_plant_report()
        text = report.format_text()
        for bus_name in [
            "BLDG_115_SERV", "025-MTR-25", "026-TX-G-PRI",
            "027-DSB-3", "028-MTR-28",
        ]:
            assert bus_name in text, f"Bus {bus_name} not in text format"

    def test_text_format_includes_published_currents(self):
        """Text deve mostrar correntes publicadas (rounded to 3 decimals)."""
        report = self._build_plant_report()
        text = report.format_text()
        # Manual cita: 10.560, 8.786, 8.558, 38.277, 21.638
        for current in ["10.560", "8.786", "8.558", "38.277", "21.638"]:
            assert current in text, f"Current {current} not in text format"

    def test_text_format_includes_x_over_r_values(self):
        """Text deve mostrar X/R publicados."""
        report = self._build_plant_report()
        text = report.format_text()
        # Manual cita: 7.03, 6.07, 3.10, 3.69, 2.85
        for xr in ["7.03", "6.07", "3.10", "3.69", "2.85"]:
            assert xr in text, f"X/R {xr} not in text format"

    def test_markdown_format_includes_h1_project_name(self):
        """Markdown deve ter H1 com project name."""
        report = self._build_plant_report()
        md = report.format_markdown()
        assert "# ANSI Fault Report — Plant Project" in md

    def test_markdown_format_table_has_5_data_rows(self):
        """Markdown table deve ter header + separator + 5 buses = 7+ linhas."""
        report = self._build_plant_report()
        md = report.format_markdown()
        # Conta linhas que começam com `| ` (table rows)
        table_lines = [line for line in md.splitlines() if line.startswith("|")]
        # 1 header + 1 separator + 5 buses = 7
        assert len(table_lines) >= 7

    def test_csv_format_round_trip_via_io(self):
        """CSV format deve ser parseable como CSV válido."""
        import io
        import csv as csv_mod
        report = self._build_plant_report()
        csv_text = report.format_csv()
        reader = csv_mod.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 5
        # Validação de tipos via header
        assert "bus_name" in rows[0]
        assert "sym_rms_kA" in rows[0]


# ===========================================================================
# Sprint D.3.B — Manual citation requirement
# ===========================================================================


class TestManualCitation:

    def test_text_cites_ansi_standards(self):
        """
        Anti-alucinação: text format deve citar ANSI C37.x.
        """
        from app.postprocessor.ansi_fault_report import (
            AnsiFaultBus, AnsiFaultReport,
        )
        report = AnsiFaultReport(project_name="Test")
        report.add_bus(AnsiFaultBus(
            bus_name="B", kv_base=1.0, sym_rms_kA=1.0, x_over_r=1.0,
        ))
        text = report.format_text()
        assert "ANSI" in text
        assert "C37" in text

    def test_markdown_cites_section_reference(self):
        """Markdown deve citar §1.4 do manual."""
        from app.postprocessor.ansi_fault_report import (
            AnsiFaultBus, AnsiFaultReport,
        )
        report = AnsiFaultReport(project_name="Test")
        report.add_bus(AnsiFaultBus(
            bus_name="B", kv_base=1.0, sym_rms_kA=1.0, x_over_r=1.0,
        ))
        md = report.format_markdown()
        assert "§1.4" in md or "1.4" in md
        assert "PTW" in md or "A_Fault" in md
