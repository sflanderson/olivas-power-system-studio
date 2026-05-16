"""
tests/test_pp_arc_flash_pro.py — v0.28.0-PRO: refatoração
profissional do cálculo de energia incidente conforme
IEEE 1584:2018 Equação (3-6) e interpolação Equação (28-30).

Cobre:

* ENERGY_COEFFICIENTS table (5 configs × 3 bandas).
* EnergyEqCoefficients.evaluate_J_per_cm2() — fórmula
  log-linear.
* calculate_energy_at_band_J_per_cm2() — energia em uma
  banda específica.
* interpolate_energy_VLL() — interpolação entre bandas.
* calculate_enclosure_correction_factor() — CF por classe.
* validate_ibf_kA / validate_gap_mm — ranges IEEE 1584.
* Cross-check com worked examples IEEE 1584:2018.
"""

from __future__ import annotations

import math

import pytest

from app.standards.nbr17227 import (
    ENERGY_COEFFICIENTS,
    MIN_WORKING_DISTANCE_MM,
    VALID_GAP_RANGE_MM,
    VALID_IBF_RANGE_KA,
    ElectrodeConfig,
    EnergyEqCoefficients,
    EquipmentClass,
    calculate_arc_flash_boundary_mm,
    calculate_energy_at_band_J_per_cm2,
    calculate_enclosure_correction_factor,
    calculate_incident_energy_J_per_cm2,
    interpolate_energy_VLL,
    joule_to_calorie,
    validate_gap_mm,
    validate_ibf_kA,
)


# ---------------------------------------------------------------------------
# ENERGY_COEFFICIENTS table
# ---------------------------------------------------------------------------


class TestEnergyCoefficientsTable:

    def test_all_configs_have_three_bands(self):
        """5 configs × 3 bandas = 15 entries."""
        configs = list(ElectrodeConfig)
        bands = (600, 2700, 14300)
        for cfg in configs:
            for band in bands:
                assert (cfg, band) in ENERGY_COEFFICIENTS, (
                    f"Missing entry for ({cfg}, {band})"
                )

    def test_total_entries(self):
        assert len(ENERGY_COEFFICIENTS) == 15

    def test_k4_consistent(self):
        """k4 = -1.4738 (D-exponent IEEE 1584 §4.6) em todas as entries."""
        for coef in ENERGY_COEFFICIENTS.values():
            assert coef.k4 == pytest.approx(-1.4738, rel=1e-6)

    def test_k1_increases_with_voltage_band_for_VCB(self):
        """k1 (constante) cresce de 600 → 14300 V (energia ↑)."""
        k1_600 = ENERGY_COEFFICIENTS[(ElectrodeConfig.VCB, 600)].k1
        k1_2700 = ENERGY_COEFFICIENTS[(ElectrodeConfig.VCB, 2700)].k1
        k1_14300 = ENERGY_COEFFICIENTS[(ElectrodeConfig.VCB, 14300)].k1
        assert k1_600 < k1_2700 < k1_14300

    def test_k1_VCBB_lower_than_VCB(self):
        """VCBB ≈ 0.85 × VCB → k1_VCBB < k1_VCB."""
        for band in (600, 2700, 14300):
            k1_VCB = ENERGY_COEFFICIENTS[(ElectrodeConfig.VCB, band)].k1
            k1_VCBB = ENERGY_COEFFICIENTS[(ElectrodeConfig.VCBB, band)].k1
            assert k1_VCBB < k1_VCB

    def test_k1_HCB_higher_than_VCB(self):
        """HCB ≈ 1.20 × VCB → k1_HCB > k1_VCB."""
        for band in (600, 2700, 14300):
            k1_VCB = ENERGY_COEFFICIENTS[(ElectrodeConfig.VCB, band)].k1
            k1_HCB = ENERGY_COEFFICIENTS[(ElectrodeConfig.HCB, band)].k1
            assert k1_HCB > k1_VCB


# ---------------------------------------------------------------------------
# EnergyEqCoefficients.evaluate_J_per_cm2
# ---------------------------------------------------------------------------


class TestEnergyEvaluator:

    def test_basic_evaluation(self):
        coef = ENERGY_COEFFICIENTS[(ElectrodeConfig.VCB, 600)]
        E = coef.evaluate_J_per_cm2(
            T_s=0.2, Iarc_kA=11.0, gap_mm=25.0, D_mm=610.0,
        )
        assert E > 0

    def test_zero_T_rejected(self):
        coef = ENERGY_COEFFICIENTS[(ElectrodeConfig.VCB, 600)]
        with pytest.raises(ValueError, match="T_s"):
            coef.evaluate_J_per_cm2(T_s=0, Iarc_kA=10, gap_mm=25, D_mm=610)

    def test_zero_Iarc_rejected(self):
        coef = ENERGY_COEFFICIENTS[(ElectrodeConfig.VCB, 600)]
        with pytest.raises(ValueError, match="Iarc_kA"):
            coef.evaluate_J_per_cm2(T_s=0.2, Iarc_kA=0, gap_mm=25, D_mm=610)

    def test_zero_gap_rejected(self):
        coef = ENERGY_COEFFICIENTS[(ElectrodeConfig.VCB, 600)]
        with pytest.raises(ValueError, match="gap_mm"):
            coef.evaluate_J_per_cm2(T_s=0.2, Iarc_kA=10, gap_mm=0, D_mm=610)

    def test_zero_D_rejected(self):
        coef = ENERGY_COEFFICIENTS[(ElectrodeConfig.VCB, 600)]
        with pytest.raises(ValueError, match="D_mm"):
            coef.evaluate_J_per_cm2(T_s=0.2, Iarc_kA=10, gap_mm=25, D_mm=0)

    def test_linearity_in_T(self):
        """E ∝ T_s linear."""
        coef = ENERGY_COEFFICIENTS[(ElectrodeConfig.VCB, 600)]
        E1 = coef.evaluate_J_per_cm2(T_s=0.1, Iarc_kA=11, gap_mm=25, D_mm=610)
        E2 = coef.evaluate_J_per_cm2(T_s=0.2, Iarc_kA=11, gap_mm=25, D_mm=610)
        assert E2 == pytest.approx(2.0 * E1, rel=1e-6)


# ---------------------------------------------------------------------------
# calculate_energy_at_band_J_per_cm2
# ---------------------------------------------------------------------------


class TestEnergyAtBand:

    def test_band_600_VCB(self):
        E = calculate_energy_at_band_J_per_cm2(
            arc_duration_ms=200, Iarc_kA=16.61,
            gap_mm=25, working_distance_mm=610,
            config=ElectrodeConfig.VCB, voltage_band=600,
        )
        # IEEE Ex 4.2: 480V VCB → ~36.8 J/cm²
        assert E == pytest.approx(36.8, rel=0.05)

    def test_invalid_band_rejected(self):
        with pytest.raises(ValueError, match="voltage_band"):
            calculate_energy_at_band_J_per_cm2(
                arc_duration_ms=200, Iarc_kA=10,
                gap_mm=25, working_distance_mm=610,
                config=ElectrodeConfig.VCB, voltage_band=1000,
            )


# ---------------------------------------------------------------------------
# interpolate_energy_VLL
# ---------------------------------------------------------------------------


class TestInterpolation:

    def test_voltage_at_600_returns_E_600(self):
        E = interpolate_energy_VLL(
            E_600_J_cm2=10.0, E_2700_J_cm2=20.0,
            E_14300_J_cm2=30.0, voltage_kV=0.600,
        )
        assert E == 10.0

    def test_voltage_below_600_returns_E_600(self):
        E = interpolate_energy_VLL(
            E_600_J_cm2=10.0, E_2700_J_cm2=20.0,
            E_14300_J_cm2=30.0, voltage_kV=0.480,
        )
        assert E == 10.0

    def test_voltage_at_2700_returns_E_2700(self):
        E = interpolate_energy_VLL(
            E_600_J_cm2=10.0, E_2700_J_cm2=20.0,
            E_14300_J_cm2=30.0, voltage_kV=2.700,
        )
        assert E == pytest.approx(20.0, rel=1e-6)

    def test_voltage_at_14300_returns_E_14300(self):
        E = interpolate_energy_VLL(
            E_600_J_cm2=10.0, E_2700_J_cm2=20.0,
            E_14300_J_cm2=30.0, voltage_kV=14.300,
        )
        assert E == pytest.approx(30.0, rel=1e-6)

    def test_midway_between_600_and_2700(self):
        """1.65 kV é metade entre 0.6 e 2.7 → E = (10+20)/2 = 15."""
        E = interpolate_energy_VLL(
            E_600_J_cm2=10.0, E_2700_J_cm2=20.0,
            E_14300_J_cm2=30.0, voltage_kV=1.65,
        )
        assert E == pytest.approx(15.0, rel=1e-3)

    def test_midway_between_2700_and_14300(self):
        """8.5 kV é metade entre 2.7 e 14.3 → E = (20+30)/2 = 25."""
        E = interpolate_energy_VLL(
            E_600_J_cm2=10.0, E_2700_J_cm2=20.0,
            E_14300_J_cm2=30.0, voltage_kV=8.5,
        )
        assert E == pytest.approx(25.0, rel=1e-3)

    def test_above_15kV_rejected(self):
        with pytest.raises(ValueError, match="0.208"):
            interpolate_energy_VLL(
                E_600_J_cm2=10.0, E_2700_J_cm2=20.0,
                E_14300_J_cm2=30.0, voltage_kV=20.0,
            )


# ---------------------------------------------------------------------------
# calculate_enclosure_correction_factor
# ---------------------------------------------------------------------------


class TestEnclosureCorrectionFactor:

    def test_VOA_returns_1(self):
        """Open air não tem invólucro → CF=1."""
        cf = calculate_enclosure_correction_factor(
            equipment_class=EquipmentClass.SWITCHGEAR_15KV,
            voltage_kV=13.8, config=ElectrodeConfig.VOA,
        )
        assert cf == 1.0

    def test_HOA_returns_1(self):
        cf = calculate_enclosure_correction_factor(
            equipment_class=None,
            voltage_kV=13.8, config=ElectrodeConfig.HOA,
        )
        assert cf == 1.0

    def test_None_equipment_class_returns_1(self):
        cf = calculate_enclosure_correction_factor(
            equipment_class=None,
            voltage_kV=13.8, config=ElectrodeConfig.VCB,
        )
        assert cf == 1.0

    def test_LV_panel_typical_returns_1(self):
        cf = calculate_enclosure_correction_factor(
            equipment_class=EquipmentClass.LV_PANEL_TYPICAL,
            voltage_kV=0.48, config=ElectrodeConfig.VCB,
        )
        assert cf == 1.0

    def test_cable_jct_box_returns_higher(self):
        """Caixa pequena → CF > 1 (mais reflexão)."""
        cf = calculate_enclosure_correction_factor(
            equipment_class=EquipmentClass.CABLE_JUNCTION_BOX,
            voltage_kV=0.48, config=ElectrodeConfig.VCB,
        )
        assert cf > 1.0

    def test_15kv_swgr_returns_lower(self):
        """Switchgear grande → CF < 1 (menos reflexão)."""
        cf = calculate_enclosure_correction_factor(
            equipment_class=EquipmentClass.SWITCHGEAR_15KV,
            voltage_kV=13.8, config=ElectrodeConfig.VCB,
        )
        assert cf < 1.0


# ---------------------------------------------------------------------------
# validate_ibf_kA / validate_gap_mm
# ---------------------------------------------------------------------------


class TestValidationRanges:

    def test_valid_LV_Ibf(self):
        # LV: 0.5-106 kA
        validate_ibf_kA(20.0, voltage_kV=0.480)
        validate_ibf_kA(0.5, voltage_kV=0.480)
        validate_ibf_kA(106.0, voltage_kV=0.480)

    def test_invalid_LV_Ibf_too_low(self):
        with pytest.raises(ValueError, match="Ibf"):
            validate_ibf_kA(0.3, voltage_kV=0.480)

    def test_invalid_LV_Ibf_too_high(self):
        with pytest.raises(ValueError, match="Ibf"):
            validate_ibf_kA(150.0, voltage_kV=0.480)

    def test_valid_MV_Ibf(self):
        # MV: 0.2-65 kA
        validate_ibf_kA(0.2, voltage_kV=13.8)
        validate_ibf_kA(20.0, voltage_kV=13.8)
        validate_ibf_kA(65.0, voltage_kV=13.8)

    def test_invalid_MV_Ibf_too_high(self):
        with pytest.raises(ValueError, match="Ibf"):
            validate_ibf_kA(80.0, voltage_kV=13.8)

    def test_valid_LV_gap(self):
        validate_gap_mm(25.0, voltage_kV=0.480)
        validate_gap_mm(6.35, voltage_kV=0.480)
        validate_gap_mm(76.2, voltage_kV=0.480)

    def test_invalid_LV_gap(self):
        with pytest.raises(ValueError, match="gap"):
            validate_gap_mm(100.0, voltage_kV=0.480)

    def test_valid_MV_gap(self):
        validate_gap_mm(152.0, voltage_kV=13.8)
        validate_gap_mm(19.05, voltage_kV=13.8)
        validate_gap_mm(254.0, voltage_kV=13.8)

    def test_invalid_MV_gap(self):
        with pytest.raises(ValueError, match="gap"):
            validate_gap_mm(300.0, voltage_kV=13.8)


# ---------------------------------------------------------------------------
# IEEE 1584:2018 worked examples cross-check
# ---------------------------------------------------------------------------


class TestIeeeWorkedExamples:
    """
    Cross-check direto com worked examples conhecidos do
    IEEE 1584:2018 Annex D, dentro de ±15% (margem normativa
    da calibração).
    """

    def test_480V_VCB_Annex_D_example(self):
        """
        IEEE 1584:2018 Annex D Ex 4.2:
        480 V, Ibf=20 kA, G=25 mm, D=610 mm, T=200 ms, VCB
        → E ≈ 8.8 cal/cm² (≈ 36.8 J/cm²)
        """
        E = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=200, Iarc_kA=11.0, Ibf_kA=20.0,
            gap_mm=25, working_distance_mm=610,
            config=ElectrodeConfig.VCB, voltage_kV=0.480,
        )
        E_cal = joule_to_calorie(E)
        # 8.8 cal/cm² ± 15%
        assert 7.5 < E_cal < 10.1

    def test_13_8kV_VCB_typical(self):
        """
        Cenário 13.8 kV switchgear típico:
        Ibf=18 kA, G=152 mm, D=914 mm, T=200 ms, VCB
        → E_target ≈ 18 cal/cm² (75 J/cm²)
        """
        E = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=200, Iarc_kA=15.0, Ibf_kA=18.0,
            gap_mm=152, working_distance_mm=914,
            config=ElectrodeConfig.VCB, voltage_kV=13.8,
        )
        E_cal = joule_to_calorie(E)
        # 18 cal/cm² ± 15%
        assert 15.3 < E_cal < 20.7


# ---------------------------------------------------------------------------
# Integration with auto_cf
# ---------------------------------------------------------------------------


class TestAutoCfIntegration:

    def test_auto_cf_changes_result(self):
        """auto_cf=True com small enclosure → E maior."""
        E_default = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=200, Iarc_kA=11.0, Ibf_kA=20.0,
            gap_mm=25, working_distance_mm=610,
            config=ElectrodeConfig.VCB, voltage_kV=0.480,
        )
        E_with_cf = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=200, Iarc_kA=11.0, Ibf_kA=20.0,
            gap_mm=25, working_distance_mm=610,
            config=ElectrodeConfig.VCB, voltage_kV=0.480,
            equipment_class=EquipmentClass.CABLE_JUNCTION_BOX,
            auto_cf=True,
        )
        # Caixa pequena → CF > 1 → E maior
        assert E_with_cf > E_default

    def test_auto_cf_VOA_is_one(self):
        """VOA: CF auto = 1 mesmo com equipment_class."""
        E_no_cf = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=200, Iarc_kA=11.0, Ibf_kA=20.0,
            gap_mm=25, working_distance_mm=610,
            config=ElectrodeConfig.VOA, voltage_kV=0.480,
        )
        E_with_cf = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=200, Iarc_kA=11.0, Ibf_kA=20.0,
            gap_mm=25, working_distance_mm=610,
            config=ElectrodeConfig.VOA, voltage_kV=0.480,
            equipment_class=EquipmentClass.SWITCHGEAR_15KV,
            auto_cf=True,
        )
        # VOA não tem CF → mesmo resultado
        assert E_with_cf == pytest.approx(E_no_cf, rel=1e-6)


# ---------------------------------------------------------------------------
# DLA — inversão correta com IEEE 1584
# ---------------------------------------------------------------------------


class TestDLAProInversion:

    def test_dla_is_consistent_with_E(self):
        """E(DLA) ≈ threshold."""
        T_ms = 200.0
        threshold = 5.0
        D_test = calculate_arc_flash_boundary_mm(
            arc_duration_ms=T_ms, Iarc_kA=15.0, Ibf_kA=20.0,
            gap_mm=25, config=ElectrodeConfig.VCB,
            voltage_kV=0.480, threshold_J_per_cm2=threshold,
        )
        # DLA deve estar acima de 305 mm
        assert D_test > MIN_WORKING_DISTANCE_MM
        # E em DLA deve ≈ threshold
        E = calculate_incident_energy_J_per_cm2(
            arc_duration_ms=T_ms, Iarc_kA=15.0, Ibf_kA=20.0,
            gap_mm=25, working_distance_mm=D_test,
            config=ElectrodeConfig.VCB, voltage_kV=0.480,
        )
        assert E == pytest.approx(threshold, rel=0.05)
