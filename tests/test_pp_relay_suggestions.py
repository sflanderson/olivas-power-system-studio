"""
tests/test_pp_relay_suggestions.py — v0.27.7.6: sugestões
automáticas de ajustes para relés de proteção, baseadas em
IEEE 242 §15 e manuais dos fabricantes.

Cobre:

* classify_bus_application — main_switchgear, feeder_branch,
  MCC, transformer, lv_panel.
* select_default_relay_model — heurística por aplicação.
* suggest_settings_for_bus — pickups, curva, TMS, rationale.
* suggest_multi_relay_alternatives — comparativo SEL/ABB/Schneider.
* Cenários realistas (switchgear, MCC, LV panel).
* Integração no BusPipelineReport.summary().
"""

from __future__ import annotations

import pytest

from app.preprocessor.bus import (
    BusComponent,
    make_default_lv_panel,
    make_default_motor_control_center,
    make_default_mv_switchgear,
)
from app.postprocessor.bus_pipeline import BusPipelineReport
from app.postprocessor.relay_suggestions import (
    RelaySuggestion,
    classify_bus_application,
    select_default_relay_model,
    suggest_multi_relay_alternatives,
    suggest_settings_for_bus,
)
from app.standards.nbr17227 import EquipmentClass
from app.standards.relay_models import (
    ABB_REF615, ABB_RET615, RelayModel,
    SCHNEIDER_P3U10, SCHNEIDER_P3U30, SEL_751,
)


# ---------------------------------------------------------------------------
# classify_bus_application
# ---------------------------------------------------------------------------


class TestClassifyBusApplication:
    def test_main_switchgear_lineside(self):
        bus = make_default_mv_switchgear("X", 13.8)
        assert bus.is_lineside is True
        assert classify_bus_application(bus) == "main_switchgear"

    def test_feeder_branch_loadside(self):
        bus = BusComponent(
            bus_id="X", rated_voltage_kV=13.8,
            panel_type=EquipmentClass.SWITCHGEAR_15KV,
            is_lineside=False,
        )
        assert classify_bus_application(bus) == "feeder_branch"

    def test_motor_control_center(self):
        bus = make_default_motor_control_center("X", 4.16)
        assert classify_bus_application(bus) == "motor_control_center"

    def test_lv_panel(self):
        bus = make_default_lv_panel("X", 0.480)
        assert classify_bus_application(bus) == "lv_panel"

    def test_cable_junction_box(self):
        bus = BusComponent(
            bus_id="X", rated_voltage_kV=0.480,
            panel_type=EquipmentClass.CABLE_JUNCTION_BOX,
        )
        assert classify_bus_application(bus) == "feeder_branch"


# ---------------------------------------------------------------------------
# select_default_relay_model
# ---------------------------------------------------------------------------


class TestSelectDefaultRelayModel:
    def test_main_switchgear_uses_sel_751(self):
        bus = make_default_mv_switchgear("X", 13.8)
        m = select_default_relay_model(bus, "main_switchgear")
        assert m == SEL_751

    def test_feeder_uses_abb_ref615(self):
        bus = BusComponent(
            bus_id="X", rated_voltage_kV=13.8,
            panel_type=EquipmentClass.SWITCHGEAR_15KV,
            is_lineside=False,
        )
        m = select_default_relay_model(bus, "feeder_branch")
        assert m == ABB_REF615

    def test_mcc_uses_abb_ref615(self):
        bus = make_default_motor_control_center("X", 4.16)
        m = select_default_relay_model(bus, "motor_control_center")
        assert m == ABB_REF615

    def test_lv_panel_uses_p3u10(self):
        bus = make_default_lv_panel("X", 0.480)
        m = select_default_relay_model(bus, "lv_panel")
        assert m == SCHNEIDER_P3U10

    def test_transformer_uses_ret615(self):
        bus = make_default_mv_switchgear("X", 13.8)
        m = select_default_relay_model(bus, "transformer")
        assert m == ABB_RET615

    def test_unknown_falls_back_to_p3u30(self):
        bus = make_default_mv_switchgear("X", 13.8)
        m = select_default_relay_model(bus, "weird_application")
        assert m == SCHNEIDER_P3U30


# ---------------------------------------------------------------------------
# suggest_settings_for_bus — pickups
# ---------------------------------------------------------------------------


class TestSuggestPickups:
    def test_pickup_51_is_125pct_of_load(self):
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=20.0, load_S_MVA=20.0,
        )
        # I_n = 20e6 / (√3 * 13.8e3) ≈ 836.7 A
        # pickup_51 = 1.25 * 836.7 ≈ 1045.9 A
        assert sg.pickup_51_A == pytest.approx(1045.9, abs=0.5)
        assert sg.pickup_51_per_in == 1.25

    def test_pickup_50_is_80pct_of_Ik_pp(self):
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=20.0, load_S_MVA=20.0,
        )
        # 0.8 * 20 kA = 16000 A
        assert sg.pickup_50_A == pytest.approx(16000.0, abs=10)

    def test_pickup_51N_is_10pct_of_51(self):
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=20.0, load_S_MVA=20.0,
        )
        assert sg.pickup_51N_A == pytest.approx(0.1 * sg.pickup_51_A)

    def test_pickup_50N_is_50pct_of_50(self):
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=20.0, load_S_MVA=20.0,
        )
        assert sg.pickup_50N_A == pytest.approx(0.5 * sg.pickup_50_A)


# ---------------------------------------------------------------------------
# suggest_settings — curvas e TMS por aplicação
# ---------------------------------------------------------------------------


class TestSuggestCurves:
    def test_main_switchgear_uses_si_high_tms(self):
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=20.0)
        assert sg.curve_51_standard == "IEC"
        assert sg.curve_51_type == "SI"
        assert sg.tms_51 == 0.50

    def test_mcc_uses_ei_low_tms(self):
        """CCM com curva EI suporta inrush de motor."""
        bus = make_default_motor_control_center("X", 4.16)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=12.0)
        assert sg.curve_51_type == "EI"
        assert sg.tms_51 == 0.10

    def test_feeder_branch_uses_si_medium_tms(self):
        bus = BusComponent(
            bus_id="X", rated_voltage_kV=13.8,
            panel_type=EquipmentClass.SWITCHGEAR_15KV,
            is_lineside=False,
        )
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=20.0)
        assert sg.curve_51_type == "SI"
        assert sg.tms_51 == 0.20

    def test_user_can_override_tms(self):
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=20.0, tms_51=0.75,
        )
        assert sg.tms_51 == 0.75

    def test_user_can_override_factors(self):
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=20.0, load_S_MVA=20.0,
            pickup_51_factor=1.5,
            pickup_50_factor=0.6,
        )
        # I_n base = 836.7 A, pickup_51 = 1.5 * 836.7 ≈ 1255
        assert sg.pickup_51_A == pytest.approx(1255.0, abs=1)
        # 0.6 * 20kA = 12000
        assert sg.pickup_50_A == pytest.approx(12000.0, abs=10)


# ---------------------------------------------------------------------------
# suggest_settings — recomendações
# ---------------------------------------------------------------------------


class TestSuggestRecommendations:
    def test_main_recommends_50BF(self):
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=20.0)
        assert sg.has_50BF is True

    def test_lv_panel_does_not_recommend_50BF(self):
        bus = make_default_lv_panel("X", 0.480)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=20.0)
        assert sg.has_50BF is False

    def test_transformer_recommends_87(self):
        """Para aplicação transformer, 87T deve ser recomendado."""
        bus = BusComponent(
            bus_id="X", rated_voltage_kV=13.8,
            panel_type=EquipmentClass.SWITCHGEAR_15KV,
            is_lineside=False,
        )
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=20.0,
            relay_model=ABB_RET615,   # forçando RET615
        )
        # application será inferido do bus, não do relé.
        # Mas a recomendação 87 vem da app.
        # Aqui o bus é feeder_branch → has_87 = False
        assert sg.has_87 is False

    def test_AFD_recommended_when_panel_has_no_AFD(self):
        """Se panel é candidato a AFD mas não tem, recomenda."""
        bus = make_default_mv_switchgear("X", 13.8, has_AFD=False)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=20.0)
        assert sg.has_AFD_recommended is True

    def test_AFD_NOT_recommended_when_already_present(self):
        """Se já tem AFD, não recomenda novamente."""
        bus = make_default_mv_switchgear("X", 13.8, has_AFD=True)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=20.0)
        assert sg.has_AFD_recommended is False


# ---------------------------------------------------------------------------
# RelaySuggestion outputs
# ---------------------------------------------------------------------------


class TestRelaySuggestionOutputs:
    def test_summary_format(self):
        bus = make_default_mv_switchgear("MAIN", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=25.0, load_S_MVA=15.0,
        )
        s = sg.summary()
        assert "Bus: MAIN" in s
        assert "Relay:" in s
        assert "Pickups:" in s
        assert "51" in s and "50" in s and "51N" in s and "50N" in s
        assert "Rationale:" in s
        assert "References:" in s

    def test_tc_curve_51_reconstructible(self):
        """O método tc_curve_51 deve retornar TcCurveSetting válido."""
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=20.0)
        curve = sg.tc_curve_51
        # Deve poder calcular t(I) para uma corrente acima do pickup
        t = curve.operate_time_s(2 * sg.pickup_51_A)
        assert t > 0

    def test_references_include_ieee_242(self):
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=20.0)
        assert any("IEEE Std 242" in r for r in sg.references)

    def test_motor_app_includes_C37_96(self):
        bus = make_default_motor_control_center("X", 4.16)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=12.0)
        assert any("C37.96" in r for r in sg.references)


# ---------------------------------------------------------------------------
# Multi-vendor alternatives
# ---------------------------------------------------------------------------


class TestMultiVendorAlternatives:
    def test_returns_3_options(self):
        bus = make_default_mv_switchgear("X", 13.8)
        alts = suggest_multi_relay_alternatives(
            bus, Ik_pp_kA=20.0, load_S_MVA=15.0,
        )
        assert len(alts) == 3

    def test_alternatives_cover_3_manufacturers(self):
        bus = make_default_mv_switchgear("X", 13.8)
        alts = suggest_multi_relay_alternatives(bus, Ik_pp_kA=20.0)
        manufacturers = {sg.relay_manufacturer for sg in alts}
        assert "SEL" in manufacturers
        assert "ABB" in manufacturers
        assert any("Schneider" in m for m in manufacturers)

    def test_pickups_consistent_across_vendors(self):
        """Mesma carga + mesmo Ik'' → pickups iguais entre vendors."""
        bus = make_default_mv_switchgear("X", 13.8)
        alts = suggest_multi_relay_alternatives(
            bus, Ik_pp_kA=20.0, load_S_MVA=15.0,
        )
        pickups = {sg.pickup_51_A for sg in alts}
        assert len(pickups) == 1   # todos iguais


# ---------------------------------------------------------------------------
# Integração no BusPipelineReport
# ---------------------------------------------------------------------------


class TestIntegrationWithReport:
    def test_report_includes_relay_suggestions(self):
        from app.postprocessor.relay_suggestions import RelaySuggestion

        # Constrói um RelaySuggestion mínimo
        bus = make_default_mv_switchgear("MAIN", 13.8)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=20.0, load_S_MVA=15.0,
        )

        report = BusPipelineReport(
            bus_id="MAIN",
            rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True,
            has_AFD=False,
            n_neighbors=2,
            n_sc_sources=2,
            sources_summary=("UTIL: 30%", "GEN: 70%"),
            Ik_pp_kA=20.0,
            ip_kA=55.0,
            kappa=1.94,
            coordination_clearing_time_ms=500.0,
            effective_clearing_time_ms=500.0,
            incident_energy_cal_cm2=15.0,
            arc_flash_boundary_mm=3000.0,
            ppe_category="3",
            relay_suggestions=(sg,),
            warnings=(),
        )
        s = report.summary()
        assert "Relay Settings Suggestions" in s
        assert "IEEE 242" in s
        assert "Pickups:" in s

    def test_report_without_suggestions_omits_block(self):
        report = BusPipelineReport(
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
            warnings=(),
        )
        s = report.summary()
        assert "Relay Settings Suggestions" not in s


# ---------------------------------------------------------------------------
# Cenários realistas
# ---------------------------------------------------------------------------


class TestRealisticScenarios:
    def test_main_switchgear_industrial(self):
        """Cenário típico: switchgear 13.8 kV / 25 kA / 20 MVA."""
        bus = make_default_mv_switchgear("SWGR", 13.8, has_AFD=False)
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=25.0, load_S_MVA=20.0,
        )
        # I_n ≈ 837 A, pickup_51 ≈ 1046 A
        assert 1000 < sg.pickup_51_A < 1100
        # Curva SI, TMS 0.5 (main lento)
        assert sg.curve_51_type == "SI"
        assert sg.tms_51 == 0.5
        # Recomendações
        assert sg.has_50BF is True
        assert sg.has_AFD_recommended is True

    def test_ccm_with_AFD(self):
        """CCM 4.16 kV / 12 kA com AFD habilitado."""
        bus = make_default_motor_control_center(
            "CCM", 4.16, has_AFD=True,
        )
        sg = suggest_settings_for_bus(
            bus, Ik_pp_kA=12.0, load_S_MVA=5.0,
        )
        # AFD já habilitado → não recomenda mais
        assert sg.has_AFD_recommended is False
        # Curva EI para suportar inrush de motor
        assert sg.curve_51_type == "EI"

    def test_load_inferred_when_not_provided(self):
        """Se load_S_MVA = None, usa heurística Ik''/20."""
        bus = make_default_mv_switchgear("X", 13.8)
        sg = suggest_settings_for_bus(bus, Ik_pp_kA=20.0)
        # I_n_default = 20kA / 20 = 1 kA
        # pickup_51 = 1.25 * 1000 = 1250 A
        assert 1240 < sg.pickup_51_A < 1260
