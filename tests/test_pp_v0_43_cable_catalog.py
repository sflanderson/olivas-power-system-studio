"""
tests/test_pp_v0_43_cable_catalog.py — v0.43: catálogo de
cabos brasileiros NBR 5356 / NBR 6251 / NBR 7286.
"""

from __future__ import annotations

import pytest

from app.preprocessor.cable_catalog import (
    CABLE_CATALOG, CatalogCable, ConductorMaterial,
    InsulationType, InstallationType,
    cable_impedance_per_km_complex, cable_impedance_total_ohm,
    find_cable, find_cable_by_ampacity, list_cables,
)


class TestCatalogPopulated:

    def test_min_count(self):
        # 8 PVC LV + 5 EPR 15kV + 3 XLPE 20kV + 3 BARE = 19
        assert len(CABLE_CATALOG) >= 19

    def test_pvc_low_voltage_present(self):
        pvc = list_cables(insulation=InsulationType.PVC)
        assert len(pvc) >= 8

    def test_epr_15kv_present(self):
        epr = list_cables(insulation=InsulationType.EPR)
        assert len(epr) >= 5

    def test_xlpe_20kv_present(self):
        xlpe = list_cables(insulation=InsulationType.XLPE)
        assert len(xlpe) >= 3

    def test_bare_copper_present(self):
        bare = list_cables(insulation=InsulationType.BARE)
        assert len(bare) >= 3


class TestDataclassValidation:

    def test_all_cables_valid_data(self):
        for c in CABLE_CATALOG:
            assert isinstance(c, CatalogCable)
            assert c.cross_section_mm2 > 0
            assert c.R_dc_ohm_per_km_at_20C > 0
            assert c.R_ac_ohm_per_km_at_90C > c.R_dc_ohm_per_km_at_20C
            assert c.X_ohm_per_km >= 0

    def test_isolated_cables_have_capacitance(self):
        """Cabos isolados (não BARE) devem ter C > 0 OU
        ser cabo curto LV onde C é desprezível."""
        for c in CABLE_CATALOG:
            if c.insulation in (InsulationType.EPR, InsulationType.XLPE):
                assert c.C_uF_per_km > 0


class TestListCables:

    def test_no_filters_returns_all(self):
        assert len(list_cables()) == len(CABLE_CATALOG)

    def test_filter_by_cross_section(self):
        small = list_cables(cross_section_min=0, cross_section_max=10)
        for c in small:
            assert c.cross_section_mm2 <= 10

    def test_filter_by_voltage(self):
        # 15 kV class
        results = list_cables(
            rated_voltage_kV=15.0, voltage_tolerance_pct=10,
        )
        for c in results:
            assert abs(c.rated_voltage_kV - 15.0) <= 1.5

    def test_filter_by_material(self):
        cu = list_cables(material=ConductorMaterial.COPPER)
        for c in cu:
            assert c.conductor_material == ConductorMaterial.COPPER

    def test_filter_by_min_ampacity(self):
        results = list_cables(min_ampacity_air_A=200)
        for c in results:
            assert c.ampacity_air_A >= 200

    def test_filter_by_min_icw(self):
        results = list_cables(min_icw_kA=10.0)
        for c in results:
            assert c.icw_kA_1s >= 10.0


class TestFindCable:

    def test_finds_closest_section(self):
        c = find_cable(cross_section_mm2=100, rated_voltage_kV=1)
        assert c is not None
        assert abs(c.cross_section_mm2 - 100) < 50

    def test_returns_none_when_no_match(self):
        c = find_cable(
            cross_section_mm2=10, rated_voltage_kV=999.0,
        )
        assert c is None


class TestFindCableByAmpacity:

    def test_returns_smallest_satisfying_ampacity(self):
        """Para 100A em ar @ LV, retorna 25mm² (que tem 101A)."""
        c = find_cable_by_ampacity(
            required_ampacity_A=100, rated_voltage_kV=1,
        )
        assert c is not None
        assert c.ampacity_air_A >= 100
        # Não deve ser desnecessariamente grande
        assert c.cross_section_mm2 <= 50

    def test_buried_method(self):
        c = find_cable_by_ampacity(
            required_ampacity_A=200, rated_voltage_kV=1,
            installation=InstallationType.BURIED,
        )
        assert c is not None
        assert c.ampacity_buried_A >= 200

    def test_no_match_returns_none(self):
        c = find_cable_by_ampacity(
            required_ampacity_A=10000, rated_voltage_kV=1,
        )
        assert c is None


class TestImpedanceCalc:

    def test_per_km_complex(self):
        c = find_cable(cross_section_mm2=70, rated_voltage_kV=15)
        z = cable_impedance_per_km_complex(c)
        assert z.real > 0
        assert z.imag > 0
        assert abs(z) > 0

    def test_total_proportional_to_length(self):
        c = find_cable(cross_section_mm2=70, rated_voltage_kV=15)
        z_500m = cable_impedance_total_ohm(c, 500)
        z_1km = cable_impedance_total_ohm(c, 1000)
        # Z é proporcional ao comprimento
        assert abs(z_1km) == pytest.approx(2 * abs(z_500m), rel=1e-9)


class TestSanity:

    def test_higher_section_lower_resistance(self):
        """Cabos maiores devem ter menor R."""
        c25 = find_cable(
            cross_section_mm2=25, rated_voltage_kV=1,
            insulation=InsulationType.PVC,
        )
        c95 = find_cable(
            cross_section_mm2=95, rated_voltage_kV=1,
            insulation=InsulationType.PVC,
        )
        assert c25.R_ac_ohm_per_km_at_90C > c95.R_ac_ohm_per_km_at_90C

    def test_higher_section_higher_ampacity(self):
        c10 = find_cable(
            cross_section_mm2=10, rated_voltage_kV=1,
            insulation=InsulationType.PVC,
        )
        c95 = find_cable(
            cross_section_mm2=95, rated_voltage_kV=1,
            insulation=InsulationType.PVC,
        )
        assert c95.ampacity_air_A > c10.ampacity_air_A

    def test_icw_consistency_K_factor_copper(self):
        """ICW (1s) Cu EPR ≈ 143 × S/1000 kA (K=143 EPR/XLPE)."""
        for c in CABLE_CATALOG:
            if (
                c.conductor_material == ConductorMaterial.COPPER
                and c.insulation in (
                    InsulationType.EPR, InsulationType.XLPE,
                )
                and c.icw_kA_1s > 0
            ):
                expected = 0.143 * c.cross_section_mm2
                err_pct = abs(c.icw_kA_1s - expected) / expected * 100
                # Tolerância 5% (arredondamentos)
                assert err_pct < 5, (
                    f"{c.name}: ICW={c.icw_kA_1s} vs esperado "
                    f"{expected:.2f} ({err_pct:.1f}% err)"
                )
