"""
tests/test_pp_arc_flash.py — v0.27.3: cálculo de energia
incidente NBR 17227:2025 / IEEE 1584-2018.

Cobre:

* Tabelas de equipamentos (gap, working distance, enclosure
  size) por classe.
* Coeficientes Iarc por config e voltage band.
* Equação (1) — corrente de arco intermediária.
* Equação (2) — fator de correção VarCf.
* Equação (34) — Iarc_min.
* Equação (3-6) simplificada — energia incidente.
* DLA (arc-flash boundary).
* Categoria PPE NFPA 70E:2024.
* Workflow ArcFlashCase → ArcFlashReport.
* Cenários realistas (LV, MV, HV) com cross-check de magnitude.
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.arc_flash import (
    ArcFlashCase, ArcFlashReport, calculate_arc_flash,
)
from app.standards.nbr17227 import (
    ElectrodeConfig, EquipmentClass, PpeCategory,
    TYPICAL_ENCLOSURE_MM, TYPICAL_GAP_MM, TYPICAL_WORKING_DISTANCE_MM,
    calculate_arc_current_kA,
    calculate_arc_current_min_kA,
    calculate_arc_flash_boundary_mm,
    calculate_incident_energy_J_per_cm2,
    calculate_VarCf,
    calorie_to_joule, joule_to_calorie,
    ppe_arc_rating_required_cal_cm2,
    ppe_category_from_energy,
)


# ---------------------------------------------------------------------------
# Tabelas de equipamentos
# ---------------------------------------------------------------------------


class TestEquipmentTables:
    def test_gap_15kv_ccm(self):
        assert TYPICAL_GAP_MM[EquipmentClass.CCM_15KV] == 152.0

    def test_gap_5kv_ccm(self):
        assert TYPICAL_GAP_MM[EquipmentClass.CCM_5KV] == 104.0

    def test_gap_lv_panel(self):
        assert TYPICAL_GAP_MM[EquipmentClass.LV_PANEL_TYPICAL] == 25.0

    def test_working_distance_15kv(self):
        assert TYPICAL_WORKING_DISTANCE_MM[EquipmentClass.CCM_15KV] == 914.4

    def test_working_distance_lv(self):
        assert TYPICAL_WORKING_DISTANCE_MM[EquipmentClass.LV_PANEL_TYPICAL] == 457.2

    def test_enclosure_dimensions(self):
        h, w, d = TYPICAL_ENCLOSURE_MM[EquipmentClass.SWITCHGEAR_15KV]
        assert h == 1143.0
        assert w == 762.0
        assert d == 762.0


# ---------------------------------------------------------------------------
# Conversões cal ↔ J
# ---------------------------------------------------------------------------


class TestEnergyConversions:
    def test_joule_to_calorie(self):
        """1 cal = 4.184 J → 4.184 J/cm² = 1 cal/cm²."""
        assert joule_to_calorie(4.184) == pytest.approx(1.0, abs=0.001)

    def test_calorie_to_joule(self):
        assert calorie_to_joule(1.0) == pytest.approx(4.184, abs=0.001)

    def test_round_trip(self):
        assert joule_to_calorie(calorie_to_joule(8.0)) == pytest.approx(8.0, abs=0.001)


# ---------------------------------------------------------------------------
# PPE Category
# ---------------------------------------------------------------------------


class TestPpeCategory:
    def test_cat_0(self):
        assert ppe_category_from_energy(0.5) == PpeCategory.CAT_0
        assert ppe_category_from_energy(1.2) == PpeCategory.CAT_0

    def test_cat_1(self):
        assert ppe_category_from_energy(2.0) == PpeCategory.CAT_1
        assert ppe_category_from_energy(4.0) == PpeCategory.CAT_1

    def test_cat_2(self):
        assert ppe_category_from_energy(5.0) == PpeCategory.CAT_2
        assert ppe_category_from_energy(8.0) == PpeCategory.CAT_2

    def test_cat_3(self):
        assert ppe_category_from_energy(15.0) == PpeCategory.CAT_3
        assert ppe_category_from_energy(25.0) == PpeCategory.CAT_3

    def test_cat_4(self):
        assert ppe_category_from_energy(30.0) == PpeCategory.CAT_4
        assert ppe_category_from_energy(40.0) == PpeCategory.CAT_4

    def test_danger(self):
        assert ppe_category_from_energy(50.0) == PpeCategory.DANGER

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            ppe_category_from_energy(-1.0)

    def test_arc_rating_for_cat_0(self):
        assert ppe_arc_rating_required_cal_cm2(PpeCategory.CAT_0) == 0.0

    def test_arc_rating_for_cat_2(self):
        assert ppe_arc_rating_required_cal_cm2(PpeCategory.CAT_2) == 8.0

    def test_arc_rating_for_cat_4(self):
        assert ppe_arc_rating_required_cal_cm2(PpeCategory.CAT_4) == 40.0

    def test_arc_rating_for_danger(self):
        assert ppe_arc_rating_required_cal_cm2(PpeCategory.DANGER) == float("inf")


# ---------------------------------------------------------------------------
# Equação (1) — Iarc
# ---------------------------------------------------------------------------


class TestArcCurrentCalculation:
    def test_typical_lv_vcb(self):
        """480V, Ibf=20kA, G=25mm, VCB → Iarc esperado ~10-14 kA."""
        Iarc = calculate_arc_current_kA(
            Ibf_kA=20.0, gap_mm=25.0,
            config=ElectrodeConfig.VCB, voltage_kV=0.480,
        )
        assert 8.0 < Iarc < 18.0

    def test_typical_mv_vcb(self):
        """13.8 kV, Ibf=40 kA, G=152 mm → Iarc esperado ~30-40 kA."""
        Iarc = calculate_arc_current_kA(
            Ibf_kA=40.0, gap_mm=152.0,
            config=ElectrodeConfig.VCB, voltage_kV=13.8,
        )
        assert 30.0 < Iarc < 42.0

    def test_iarc_less_than_ibf(self):
        """Iarc deve ser menor que Ibf (impedância do arco)."""
        Iarc = calculate_arc_current_kA(
            Ibf_kA=25.0, gap_mm=25.0,
            config=ElectrodeConfig.VCB, voltage_kV=0.480,
        )
        assert Iarc < 25.0

    def test_voltage_out_of_scope(self):
        with pytest.raises(ValueError, match="escopo"):
            calculate_arc_current_kA(
                Ibf_kA=20.0, gap_mm=25.0,
                config=ElectrodeConfig.VCB, voltage_kV=20.0,  # > 15 kV
            )

    def test_zero_ibf_rejected(self):
        with pytest.raises(ValueError):
            calculate_arc_current_kA(
                Ibf_kA=0, gap_mm=25,
                config=ElectrodeConfig.VCB, voltage_kV=0.480,
            )

    def test_zero_gap_rejected(self):
        with pytest.raises(ValueError):
            calculate_arc_current_kA(
                Ibf_kA=20, gap_mm=0,
                config=ElectrodeConfig.VCB, voltage_kV=0.480,
            )


# ---------------------------------------------------------------------------
# Equação (2) — VarCf
# ---------------------------------------------------------------------------


class TestVarCfCalculation:
    def test_vcb_at_15kv(self):
        """VCB @ 15 kV → VarCf típico < 0.05."""
        v = calculate_VarCf(ElectrodeConfig.VCB, 15.0)
        assert -0.1 < v < 0.1

    def test_voa_at_4kv(self):
        v = calculate_VarCf(ElectrodeConfig.VOA, 4.0)
        # VOA tem coefs específicos; verifica retorno real finito
        assert math.isfinite(v)

    def test_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            calculate_VarCf(ElectrodeConfig.VCB, 20.0)


# ---------------------------------------------------------------------------
# Equação (34) — Iarc_min
# ---------------------------------------------------------------------------


class TestIarcMin:
    def test_basic(self):
        """VarCf=0.10 ⇒ Iarc_min = 0.95·Iarc."""
        Iarc_min = calculate_arc_current_min_kA(20.0, 0.10)
        assert Iarc_min == pytest.approx(19.0, abs=0.01)

    def test_zero_varcf(self):
        """VarCf=0 ⇒ Iarc_min = Iarc."""
        Iarc_min = calculate_arc_current_min_kA(20.0, 0.0)
        assert Iarc_min == pytest.approx(20.0, abs=0.001)


# ---------------------------------------------------------------------------
# Energia incidente
# ---------------------------------------------------------------------------


class TestIncidentEnergy:
    def test_calibration_against_ieee_example(self):
        """
        Cross-check: 480 V, Iarc=11kA, T=200ms, G=25mm, D=610mm
        VCB → IEEE 1584:2018 Ex 4.2 indica E ≈ 8.8 cal/cm² ≈ 36.8 J/cm².
        Tolerância MVP: ±25% (calibração simplificada).
        """
        E = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=200,
            Iarc_kA=11.0,
            Ibf_kA=20.0,
            gap_mm=25.0,
            working_distance_mm=610.0,
            config=ElectrodeConfig.VCB,
            voltage_kV=0.480,
        )
        E_cal = joule_to_calorie(E)
        # 8.8 cal/cm² ± 25%
        assert 6.6 < E_cal < 11.0

    def test_doubling_time_doubles_energy(self):
        """Linear em T (segundos)."""
        E1 = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=100, Iarc_kA=10, Ibf_kA=15, gap_mm=25,
            working_distance_mm=457, config=ElectrodeConfig.VCB,
            voltage_kV=0.480,
        )
        E2 = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=200, Iarc_kA=10, Ibf_kA=15, gap_mm=25,
            working_distance_mm=457, config=ElectrodeConfig.VCB,
            voltage_kV=0.480,
        )
        assert E2 == pytest.approx(2.0 * E1, abs=0.01)

    def test_doubling_distance_scales_by_D_exponent(self):
        """
        v0.28.0-PRO: IEEE 1584:2018 Eq (3) usa D^(-1.4738), não
        1/D². Dobrar D escala E por 2^(-1.4738) ≈ 0.360, não 1/4.
        """
        import math
        E1 = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=200, Iarc_kA=10, Ibf_kA=15, gap_mm=25,
            working_distance_mm=457, config=ElectrodeConfig.VCB,
            voltage_kV=0.480,
        )
        E2 = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=200, Iarc_kA=10, Ibf_kA=15, gap_mm=25,
            working_distance_mm=914, config=ElectrodeConfig.VCB,
            voltage_kV=0.480,
        )
        expected_ratio = 2.0 ** (-1.4738)   # ≈ 0.360
        assert E2 / E1 == pytest.approx(expected_ratio, rel=0.01)

    def test_distance_below_305_rejected(self):
        with pytest.raises(ValueError, match="305"):
            calculate_incident_energy_J_per_cm2(
                arc_duration_ms=100, Iarc_kA=10, Ibf_kA=15, gap_mm=25,
                working_distance_mm=200,  # < 305
                config=ElectrodeConfig.VCB, voltage_kV=0.480,
            )


# ---------------------------------------------------------------------------
# DLA
# ---------------------------------------------------------------------------


class TestArcFlashBoundary:
    def test_dla_consistent_with_E(self):
        """DLA é onde E=5 J/cm². Inverter dá D que produz E=5."""
        T_ms = 200.0
        Iarc = 15.0
        D_test = calculate_arc_flash_boundary_mm(
            arc_duration_ms=T_ms, Iarc_kA=Iarc, Ibf_kA=20,
            gap_mm=25, config=ElectrodeConfig.VCB, voltage_kV=0.480,
            threshold_J_per_cm2=5.0,
        )
        E_at_dla = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=T_ms, Iarc_kA=Iarc, Ibf_kA=20,
            gap_mm=25, working_distance_mm=D_test,
            config=ElectrodeConfig.VCB, voltage_kV=0.480,
        )
        assert E_at_dla == pytest.approx(5.0, abs=0.05)

    def test_higher_T_gives_larger_dla(self):
        D_short = calculate_arc_flash_boundary_mm(
            100, 15, 20, 25, ElectrodeConfig.VCB, 0.480,
        )
        D_long = calculate_arc_flash_boundary_mm(
            500, 15, 20, 25, ElectrodeConfig.VCB, 0.480,
        )
        assert D_long > D_short


# ---------------------------------------------------------------------------
# ArcFlashCase + calculate_arc_flash workflow
# ---------------------------------------------------------------------------


class TestArcFlashWorkflow:
    def test_basic_case(self):
        case = ArcFlashCase(
            bus_name="CCM-A",
            rated_voltage_kV=4.16,
            bolted_fault_current_kA=15.0,
            arc_clearing_time_ms=200.0,
            equipment_class=EquipmentClass.CCM_5KV,
        )
        report = calculate_arc_flash(case)
        assert isinstance(report, ArcFlashReport)
        assert report.incident_energy_cal_cm2 > 0
        assert report.arc_flash_boundary_mm > 0
        assert report.ppe_category in PpeCategory

    def test_uses_typical_gap_when_not_specified(self):
        case = ArcFlashCase(
            bus_name="C", rated_voltage_kV=4.16,
            bolted_fault_current_kA=15.0, arc_clearing_time_ms=200,
            equipment_class=EquipmentClass.CCM_5KV,
        )
        assert case.effective_gap_mm() == 104.0

    def test_override_gap(self):
        case = ArcFlashCase(
            bus_name="C", rated_voltage_kV=4.16,
            bolted_fault_current_kA=15.0, arc_clearing_time_ms=200,
            equipment_class=EquipmentClass.CCM_5KV,
            gap_mm=200.0,
        )
        assert case.effective_gap_mm() == 200.0

    def test_summary_format(self):
        case = ArcFlashCase(
            bus_name="C", rated_voltage_kV=4.16,
            bolted_fault_current_kA=15.0, arc_clearing_time_ms=200,
            equipment_class=EquipmentClass.CCM_5KV,
        )
        s = calculate_arc_flash(case).summary()
        assert "ABNT NBR 17227" in s
        assert "Incident Energy" in s
        assert "Category" in s
        assert "Arc Rating" in s

    def test_max_of_two_currents(self):
        """Report deve usar max(E_avg, E_min)."""
        case = ArcFlashCase(
            bus_name="C", rated_voltage_kV=4.16,
            bolted_fault_current_kA=15.0, arc_clearing_time_ms=200,
            equipment_class=EquipmentClass.CCM_5KV,
        )
        r = calculate_arc_flash(case)
        assert r.incident_energy_J_cm2 == max(
            r.E_arc_J_cm2, r.E_arc_min_J_cm2,
        )


# ---------------------------------------------------------------------------
# Cenários realistas com expected ranges
# ---------------------------------------------------------------------------


class TestRealisticScenarios:
    def test_ccm_4kv_moderate(self):
        """
        CCM 4.16 kV, Ibf 15 kA, T 200 ms → Cat 2-3 (IEEE 1584
        v0.28.0-PRO calibrado: ~11 cal/cm²; valor MVP anterior
        com K=6.23 dava ~5 cal/cm² subestimado).
        """
        case = ArcFlashCase(
            bus_name="CCM",
            rated_voltage_kV=4.16,
            bolted_fault_current_kA=15.0,
            arc_clearing_time_ms=200.0,
            equipment_class=EquipmentClass.CCM_5KV,
        )
        r = calculate_arc_flash(case)
        assert r.ppe_category in (
            PpeCategory.CAT_2, PpeCategory.CAT_3,
        )

    def test_lv_panel_fast_protection(self):
        """480V, 25kA, T=50ms (proteção rápida) → Cat 1 esperada."""
        case = ArcFlashCase(
            bus_name="QGBT",
            rated_voltage_kV=0.480,
            bolted_fault_current_kA=25.0,
            arc_clearing_time_ms=50.0,
            equipment_class=EquipmentClass.LV_PANEL_TYPICAL,
        )
        r = calculate_arc_flash(case)
        # T tão pequeno deve dar Cat baixa
        assert r.ppe_category in (
            PpeCategory.CAT_1, PpeCategory.CAT_2,
        )

    def test_hv_switchgear_slow_protection_danger(self):
        """13.8 kV, Ibf 40 kA, T=2000 ms → DANGER ou Cat 4."""
        case = ArcFlashCase(
            bus_name="SWGR",
            rated_voltage_kV=13.8,
            bolted_fault_current_kA=40.0,
            arc_clearing_time_ms=2000.0,
            equipment_class=EquipmentClass.SWITCHGEAR_15KV,
        )
        r = calculate_arc_flash(case)
        # T longo + Ibf alto → DANGER
        assert r.ppe_category == PpeCategory.DANGER

    def test_hv_switchgear_fast_protection(self):
        """13.8 kV, 40 kA, T=100ms (proteção bem rápida) → Cat 2 ou menos."""
        case = ArcFlashCase(
            bus_name="SWGR",
            rated_voltage_kV=13.8,
            bolted_fault_current_kA=40.0,
            arc_clearing_time_ms=100.0,
            equipment_class=EquipmentClass.SWITCHGEAR_15KV,
        )
        r = calculate_arc_flash(case)
        # T curto reduz drasticamente
        assert r.ppe_category != PpeCategory.DANGER


# ---------------------------------------------------------------------------
# Integração com short-circuit calculator
# ---------------------------------------------------------------------------


class TestIntegrationWithShortCircuit:
    def test_pipeline_sc_to_arcflash(self):
        """
        Pipeline NBR 17227 §5.1.1: SC IEC 60909 → arc-flash.

        Cenário realista:
        - Gerador 13.8 kV / 100 MVA + concessionária 2 GVA
        - Falta no bus 13.8 kV
        - Tempo de extinção 200 ms
        """
        from app.postprocessor.short_circuit import ShortCircuitNetwork
        from app.preprocessor.synchronous_machine import (
            make_default_thermal_generator,
        )

        # 1) Estudo SC IEC 60909
        gen = make_default_thermal_generator(
            "GEN", "A", "B", "C", 13.8, 100.0,
        )
        net = ShortCircuitNetwork(rated_voltage_kV=13.8)
        net.add_synchronous_machine_from_sm(gen)
        sc = net.calculate_at_bus("BUS")

        # 2) Estudo arc-flash NBR 17227
        case = ArcFlashCase(
            bus_name="BUS",
            rated_voltage_kV=13.8,
            bolted_fault_current_kA=sc.Ik_pp_kA,
            arc_clearing_time_ms=200.0,
            equipment_class=EquipmentClass.SWITCHGEAR_15KV,
        )
        r = calculate_arc_flash(case)

        # Cross-check: Ibf ≈ 23 kA esperado (gen alone via Xd''=0.20)
        assert sc.Ik_pp_kA == pytest.approx(23.0, abs=1.0)
        # Energia razoável (>0, <50 cal/cm²)
        assert 0 < r.incident_energy_cal_cm2 < 50
