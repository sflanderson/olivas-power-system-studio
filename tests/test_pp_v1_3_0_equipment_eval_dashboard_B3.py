"""
tests.test_pp_v1_3_0_equipment_eval_dashboard_B3 — sub-sprint B.3.

Cobre dashboard generation (HTML + CSV) de Equipment Evaluation.

**Aceite B.3**: 8+ testes, 100% verde, HTML standalone valido,
CSV bem-formado.
"""

from __future__ import annotations

import pytest

from app.postprocessor.equipment_eval import (
    EquipmentInstance,
    evaluate_equipment,
    evaluate_project,
)
from app.postprocessor.equipment_eval_dashboard import (
    export_csv,
    generate_html_dashboard,
)
from app.postprocessor.equipment_eval_rules import (
    PTW_EQUIPMENT_EVALUATION,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_brk(eq_id: str = "BRK-1", **overrides) -> EquipmentInstance:
    defaults = dict(
        equipment_id=eq_id,
        equipment_type="breaker",
        rated_voltage_kV=15.0,
        rated_continuous_A=2000,
        rated_interrupt_kA=40.0,
        rated_asym_kA=104.0,
        bus_voltage_kV=13.8,
        duty={
            "I_load_A": 1500,
            "I_fault_kA": 25.0,
            "ip_kA": 65.0,
            "V_drop_pct": 0.5,
        },
    )
    defaults.update(overrides)
    return EquipmentInstance(**defaults)


# ---------------------------------------------------------------------------
# generate_html_dashboard
# ---------------------------------------------------------------------------


class TestGenerateHtmlDashboard:

    def test_empty_reports_returns_html(self):
        html = generate_html_dashboard([])
        assert "<html" in html
        assert "Nenhum equipamento" in html

    def test_single_equipment_renders_table(self):
        eq = _make_brk()
        rep = evaluate_equipment(eq, PTW_EQUIPMENT_EVALUATION)
        html = generate_html_dashboard([rep])

        # Estrutura HTML válida
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

        # Tem tabela
        assert "<table>" in html

        # Equipment ID aparece
        assert "BRK-1" in html
        assert "breaker" in html

    def test_multiple_equipments_one_row_each(self):
        eqs = [_make_brk(f"BRK-{i}") for i in range(5)]
        reports = evaluate_project(eqs, PTW_EQUIPMENT_EVALUATION)
        html = generate_html_dashboard(reports)

        # 5 equipment_ids no HTML
        for i in range(5):
            assert f"BRK-{i}" in html

    def test_html_contains_summary_bar(self):
        eq = _make_brk()
        rep = evaluate_equipment(eq, PTW_EQUIPMENT_EVALUATION)
        html = generate_html_dashboard([rep])
        # Sumário tem PASS, WARN, FAIL, N/A
        assert "PASS:" in html
        assert "WARN:" in html
        assert "FAIL:" in html
        assert "N/A:" in html

    def test_html_uses_color_classes(self):
        """Verifica que cores semantic estão presentes no CSS."""
        eq = _make_brk()
        rep = evaluate_equipment(eq, PTW_EQUIPMENT_EVALUATION)
        html = generate_html_dashboard([rep])
        # Verde PASS
        assert "#2E7D32" in html
        # Vermelho FAIL
        assert "#C0392B" in html

    def test_failure_equipment_status_FAIL(self):
        """Equipamento ruim → status FAIL aparece no HTML."""
        bad = _make_brk(
            equipment_id="BAD",
            rated_voltage_kV=10.0,  # < bus 13.8
            rated_interrupt_kA=20.0,  # < I_fault 25
        )
        rep = evaluate_equipment(bad, PTW_EQUIPMENT_EVALUATION)
        html = generate_html_dashboard([rep])
        assert "FAIL" in html

    def test_html_escapes_user_strings(self):
        """IDs com caracteres especiais devem ser escapados."""
        eq = _make_brk(equipment_id="BRK<script>alert(1)</script>")
        rep = evaluate_equipment(eq, PTW_EQUIPMENT_EVALUATION)
        html = generate_html_dashboard([rep])
        # NÃO deve ter <script> raw
        assert "<script>alert(1)</script>" not in html
        # DEVE ter escape
        assert "&lt;script&gt;" in html

    def test_custom_project_title(self):
        eq = _make_brk()
        rep = evaluate_equipment(eq, PTW_EQUIPMENT_EVALUATION)
        html = generate_html_dashboard(
            [rep],
            project_title="Subestação 13.8 kV — Audit 2026",
        )
        assert "Subestação 13.8 kV" in html


# ---------------------------------------------------------------------------
# export_csv
# ---------------------------------------------------------------------------


class TestExportCsv:

    def test_empty_reports_returns_header_only(self):
        csv = export_csv([])
        # Pelo menos header com colunas básicas
        assert "Equipment" in csv
        assert "Type" in csv

    def test_single_equipment_one_data_row(self):
        eq = _make_brk()
        rep = evaluate_equipment(eq, PTW_EQUIPMENT_EVALUATION)
        csv = export_csv([rep])
        lines = csv.strip().split("\n")
        # 1 header + 1 data
        assert len(lines) == 2
        # Equipment ID na linha de dados
        assert "BRK-1" in lines[1]

    def test_multiple_equipments_multiple_rows(self):
        eqs = [_make_brk(f"BRK-{i}") for i in range(3)]
        reports = evaluate_project(eqs, PTW_EQUIPMENT_EVALUATION)
        csv = export_csv(reports)
        lines = csv.strip().split("\n")
        # 1 header + 3 data
        assert len(lines) == 4

    def test_csv_separator_default_semicolon(self):
        """Excel BR usa ; como separador default."""
        eq = _make_brk()
        rep = evaluate_equipment(eq, PTW_EQUIPMENT_EVALUATION)
        csv = export_csv([rep])
        assert ";" in csv

    def test_csv_custom_separator_comma(self):
        eq = _make_brk()
        rep = evaluate_equipment(eq, PTW_EQUIPMENT_EVALUATION)
        csv = export_csv([rep], sep=",")
        # vírgula presente, ; ausente nas linhas de dados
        assert "," in csv
        # header começa com Equipment,Type,Status
        first_line = csv.strip().split("\n")[0]
        assert first_line.startswith("Equipment,Type,Status")

    def test_csv_includes_severity_columns(self):
        eq = _make_brk()
        rep = evaluate_equipment(eq, PTW_EQUIPMENT_EVALUATION)
        csv = export_csv([rep])
        # Header tem _severity para cada rule
        assert "EQ-VOLTAGE-RATING_severity" in csv
        assert "EQ-INTERRUPT-DUTY_severity" in csv

    def test_csv_severity_values_uppercase(self):
        """SEVERITY no CSV deve ser maiúsculo (PASS/WARN/FAIL/N/A)."""
        eq = _make_brk()
        rep = evaluate_equipment(eq, PTW_EQUIPMENT_EVALUATION)
        csv = export_csv([rep])
        # Pelo menos um PASS deve aparecer
        assert "PASS" in csv


# ---------------------------------------------------------------------------
# Smoke test integrado
# ---------------------------------------------------------------------------


class TestIntegrationSmoke:

    def test_realistic_substation_dashboard(self):
        """
        Cenário: 1 Bus + 2 Breakers + 2 Cables + 1 Transformer +
        1 Generator. Mix de PASS/WARN/FAIL.
        """
        equipment_list = [
            EquipmentInstance(
                equipment_id="BUS-MAIN",
                equipment_type="bus",
                rated_voltage_kV=13.8,
                rated_continuous_A=3000,
                duty={"V_drop_pct": 2.5},  # PASS
            ),
            _make_brk("BRK-MAIN", duty={"I_fault_kA": 25.0, "ip_kA": 65.0,
                                         "I_load_A": 1500, "V_drop_pct": 0.3}),
            _make_brk(
                "BRK-FEEDER",
                rated_continuous_A=600,
                rated_interrupt_kA=20.0,
                duty={"I_load_A": 580, "I_fault_kA": 18,
                      "ip_kA": 47, "V_drop_pct": 0.5},
            ),
            EquipmentInstance(
                equipment_id="CAB-1",
                equipment_type="cable",
                rated_voltage_kV=1.0,
                rated_continuous_A=200,
                duty={"I_load_A": 150, "I_design_A": 180, "V_drop_pct": 3.5},
            ),
            EquipmentInstance(
                equipment_id="CAB-2-OVER",
                equipment_type="cable",
                rated_voltage_kV=1.0,
                rated_continuous_A=200,
                duty={"I_load_A": 250, "I_design_A": 270, "V_drop_pct": 5.0},
            ),
            EquipmentInstance(
                equipment_id="GEN-1",
                equipment_type="generator",
                rated_voltage_kV=13.8,
                rated_continuous_A=1000,
                duty={"gen_load_A": 700},
            ),
            EquipmentInstance(
                equipment_id="T1",
                equipment_type="transformer",
                rated_voltage_kV=13.8,
                rated_continuous_A=500,
                duty={"I_load_A": 400, "I_design_A": 480},
            ),
        ]
        reports = evaluate_project(equipment_list, PTW_EQUIPMENT_EVALUATION)
        assert len(reports) == 7

        # HTML não crasha
        html = generate_html_dashboard(
            reports,
            project_title="Substation Audit 2026",
        )
        assert "BUS-MAIN" in html
        assert "GEN-1" in html
        assert "T1" in html

        # CAB-2-OVER deve ter FAIL (carga 125% + V_drop 125% do limit)
        cab2_rep = next(r for r in reports if r.equipment_id == "CAB-2-OVER")
        assert cab2_rep.has_failures()

        # CSV tem 7 linhas + 1 header
        csv = export_csv(reports)
        lines = csv.strip().split("\n")
        assert len(lines) == 8
