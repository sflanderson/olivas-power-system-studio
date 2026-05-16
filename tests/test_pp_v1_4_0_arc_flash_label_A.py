"""
tests.test_pp_v1_4_0_arc_flash_label_A — sub-sprint A.

Cobre data model + render HTML do Custom Label Designer:
* `ArcFlashLabel` (30 fields)
* `LabelStyle` enum (3 estilos)
* `render_html_label`
* `from_arc_flash_report` auto-fill
* `ppe_category_color` dynamic colors

**Aceite A**: 12+ testes, 100% verde.
"""

from __future__ import annotations

import pytest

from app.postprocessor.arc_flash_label import (
    ArcFlashLabel,
    LabelStyle,
    ppe_category_color,
    render_html_label,
)


# ---------------------------------------------------------------------------
# ArcFlashLabel construction
# ---------------------------------------------------------------------------


class TestArcFlashLabel:

    def test_default_all_empty_strings(self):
        lab = ArcFlashLabel()
        # Todos os 30 fields default = ""
        for f in lab.__dataclass_fields__:
            assert getattr(lab, f) == ""

    def test_construct_with_some_fields(self):
        lab = ArcFlashLabel(
            bus_name="BUS-MAIN",
            bus_kV="13.8",
            ppe_category="2",
            incident_energy_cal_cm2="5.2",
        )
        assert lab.bus_name == "BUS-MAIN"
        assert lab.ppe_category == "2"

    def test_30_fields_total(self):
        """Garante que data model tem exatamente 30 campos."""
        lab = ArcFlashLabel()
        assert len(lab.__dataclass_fields__) == 30


# ---------------------------------------------------------------------------
# from_arc_flash_report
# ---------------------------------------------------------------------------


class TestFromArcFlashReport:

    def _make_demo_report(self):
        """Cria ArcFlashReport demo via cálculo real."""
        from app.postprocessor.arc_flash import (
            ArcFlashCase, ElectrodeConfig, EquipmentClass,
            calculate_arc_flash,
        )
        case = ArcFlashCase(
            bus_name="BUS-MAIN-13.8kV",
            rated_voltage_kV=13.8,
            bolted_fault_current_kA=25.0,
            arc_clearing_time_ms=200.0,
            gap_mm=153.0,
            working_distance_mm=914.0,
            electrode_config=ElectrodeConfig.VCB,
            equipment_class=EquipmentClass.SWITCHGEAR_15KV,
        )
        return calculate_arc_flash(case)

    def test_auto_fill_from_report(self):
        report = self._make_demo_report()
        lab = ArcFlashLabel.from_arc_flash_report(report)
        # Bus name vem do case_label
        assert lab.bus_name == "BUS-MAIN-13.8kV"
        assert lab.bus_kV == "13.800"
        # Numéricos formatados
        assert "25" in lab.Ibf_kA  # ~25 kA
        # PPE category populated
        assert lab.ppe_category in ("0", "1", "2", "3", "4", "DANGER")

    def test_overrides_kwargs(self):
        report = self._make_demo_report()
        lab = ArcFlashLabel.from_arc_flash_report(
            report,
            project_title="Subestação São João",
            computed_by="Eng. Landerson F. Silva",
            label_number="AF-2026-001",
        )
        assert lab.project_title == "Subestação São João"
        assert lab.computed_by == "Eng. Landerson F. Silva"
        assert lab.label_number == "AF-2026-001"

    def test_glove_class_by_voltage(self):
        """Validação manual: kV=13.8 → glove class 2 (≤17 kV)."""
        report = self._make_demo_report()
        lab = ArcFlashLabel.from_arc_flash_report(report)
        assert lab.glove_class == "2"
        assert lab.glove_voltage_V == "17000"

    def test_low_voltage_glove(self):
        """0.48 kV → glove class 00 (≤500 V)."""
        from app.postprocessor.arc_flash import (
            ArcFlashCase, ElectrodeConfig, EquipmentClass,
            calculate_arc_flash,
        )
        case = ArcFlashCase(
            bus_name="BUS-LV", rated_voltage_kV=0.48,
            bolted_fault_current_kA=15.0, arc_clearing_time_ms=100.0,
            gap_mm=32.0, working_distance_mm=455.0,
            electrode_config=ElectrodeConfig.VCB,
            equipment_class=EquipmentClass.LV_PANEL_TYPICAL,
        )
        report = calculate_arc_flash(case)
        lab = ArcFlashLabel.from_arc_flash_report(report)
        assert lab.glove_class == "00"


# ---------------------------------------------------------------------------
# ppe_category_color
# ---------------------------------------------------------------------------


class TestPpeColors:

    def test_DANGER_is_red(self):
        text, bg = ppe_category_color("DANGER")
        # Red component dominante
        assert text.startswith("#C62") or "red" in text.lower() \
            or text.upper().startswith("#C")

    def test_category_0_is_green(self):
        text, bg = ppe_category_color("0")
        # Verde intenso #2E7D32
        assert text == "#2E7D32"

    def test_category_4_is_orange_red(self):
        text, bg = ppe_category_color("4")
        # Vermelho-laranja #E64A19
        assert text == "#E64A19"

    def test_unknown_category_returns_neutral(self):
        text, bg = ppe_category_color("XYZ")
        # Cinza neutro
        assert text == "#424242"

    def test_lowercase_category_normalized(self):
        text, bg = ppe_category_color("danger")
        # Mesmo retorno que "DANGER"
        text2, bg2 = ppe_category_color("DANGER")
        assert text == text2


# ---------------------------------------------------------------------------
# render_html_label
# ---------------------------------------------------------------------------


class TestRenderHtmlLabel:

    def _make_full_label(self):
        return ArcFlashLabel(
            bus_name="BUS-MAIN-13.8kV",
            bus_kV="13.8",
            label_number="AF-2026-001",
            equipment_owner="Subestação A",
            Ibf_kA="25.000",
            Iarc_kA="22.500",
            arc_duration_ms="200",
            equipment_type="Switchgear",
            gap_mm="153",
            working_distance_mm="914",
            electrode_config="VCB",
            incident_energy_cal_cm2="5.234",
            arc_flash_boundary_mm="1234",
            ppe_category="2",
            ppe_description="AR ≥ 8 cal/cm² + hood opcional",
            ppe_arc_rating_min_cal_cm2="8.0",
            limited_approach_mm="1830",
            restricted_approach_mm="660",
            glove_class="2",
            glove_voltage_V="17000",
            shock_hazard_voltage_V="13800",
            flash_hazard_range="5.2",
            head_eye_hearing_protection="Capacete + face-shield",
            hand_arm_protection="Luvas classe 2",
            foot_protection="Botas dielétricas",
            notes="*N1 OK",
            date_computed="2026-04-28",
            computed_by="Eng. Landerson",
            project_title="Subestação São João",
            audit_sha256="abc123def456",
        )

    def test_renders_valid_html(self):
        lab = self._make_full_label()
        html = render_html_label(lab)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_three_styles_render(self):
        lab = self._make_full_label()
        for style in LabelStyle:
            html = render_html_label(lab, style)
            assert "<html" in html
            assert "</html>" in html

    def test_NFPA_style_has_arc_flash_header(self):
        lab = self._make_full_label()
        html = render_html_label(lab, LabelStyle.NFPA_70E_2024)
        assert "ARC FLASH" in html

    def test_BR_style_has_portuguese_header(self):
        lab = self._make_full_label()
        html = render_html_label(lab, LabelStyle.MINIMAL_BR)
        assert "ATENÇÃO" in html or "ARCO ELÉTRICO" in html

    def test_NESC_style_has_high_voltage(self):
        lab = self._make_full_label()
        html = render_html_label(lab, LabelStyle.NESC_2023_TYPE_4_5)
        assert "HIGH VOLTAGE" in html or "NESC" in html

    def test_html_includes_bus_name(self):
        lab = self._make_full_label()
        html = render_html_label(lab)
        assert "BUS-MAIN-13.8kV" in html

    def test_html_xss_safe(self):
        lab = ArcFlashLabel(
            bus_name="<script>alert(1)</script>",
            ppe_category="2",
        )
        html = render_html_label(lab)
        # NÃO tem script raw
        assert "<script>alert(1)</script>" not in html
        # TEM escape
        assert "&lt;script&gt;" in html

    def test_html_uses_ppe_color_for_DANGER(self):
        lab = ArcFlashLabel(
            bus_name="X", ppe_category="DANGER",
        )
        html = render_html_label(lab)
        # Cor DANGER = #C62828
        assert "C62828" in html

    def test_empty_fields_omitted_from_render(self):
        """Fields vazios não devem aparecer como '— : —' no HTML."""
        lab = ArcFlashLabel(
            bus_name="BUS-X",
            ppe_category="2",
            # Demais campos = ""
        )
        html = render_html_label(lab)
        # bus_name presente
        assert "BUS-X" in html
        # Não deve haver "Equipment Owner" como linha pq vazio
        # (verifica que campos vazios não geram <div class="label-row">)
        # Conta linhas — deve ser pequeno
        n_rows = html.count('<div class="label-row">')
        # Apenas 2 fields preenchidos (bus_name + ppe_category)
        # pode gerar até 2 rows. Aceitamos ≤5.
        assert n_rows <= 5

    def test_audit_sha256_appears(self):
        lab = ArcFlashLabel(
            bus_name="X", ppe_category="2",
            audit_sha256="abc123def456",
        )
        html = render_html_label(lab)
        assert "abc123def456" in html

    def test_notes_section_when_present(self):
        lab = ArcFlashLabel(
            bus_name="X", ppe_category="2",
            notes="*N1 mis-coordinated",
        )
        html = render_html_label(lab)
        assert "*N1 mis-coordinated" in html
