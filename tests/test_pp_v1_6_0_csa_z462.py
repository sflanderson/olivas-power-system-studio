"""
tests/test_pp_v1_6_0_csa_z462.py — v1.6.0 Sprint D.

Cobre o módulo ``app.standards.csa_z462_arc_flash``:

* Wrapper sobre :func:`calculate_arc_flash` (IEEE 1584-2018)
* Mapeamento PPE Cat → CSA Risk Cat
* Mantém arc_flash_boundary do IEEE 1584
"""

from __future__ import annotations

import pytest


@pytest.fixture
def lv_panel_case():
    """Caso típico LV panel para CSA Z462 wrapper test."""
    from app.postprocessor.arc_flash import ArcFlashCase
    from app.standards.nbr17227 import (
        ElectrodeConfig, EquipmentClass,
    )
    return ArcFlashCase(
        bus_name="CCM-A",
        rated_voltage_kV=0.480,
        bolted_fault_current_kA=25.0,
        arc_clearing_time_ms=200,
        equipment_class=EquipmentClass.LV_PANEL_TYPICAL,
        electrode_config=ElectrodeConfig.VCB,
    )


class TestCSAZ462Wrapper:

    def test_module_loadable(self):
        from app.standards import csa_z462_arc_flash  # noqa: F401

    def test_wrapper_returns_result(self, lv_panel_case):
        from app.standards.csa_z462_arc_flash import (
            CSAZ462Result, csa_z462_arc_flash,
        )
        result = csa_z462_arc_flash(lv_panel_case)
        assert isinstance(result, CSAZ462Result)
        assert result.incident_energy_cal_cm2 >= 0
        assert result.arc_flash_boundary_mm >= 0
        assert "IEEE 1584" in result.underlying_method

    def test_wrapper_uses_ieee_1584_underlying(self, lv_panel_case):
        """Energia deve casar com calculate_arc_flash do IEEE 1584."""
        from app.postprocessor.arc_flash import calculate_arc_flash
        from app.standards.csa_z462_arc_flash import csa_z462_arc_flash

        ieee = calculate_arc_flash(lv_panel_case)
        csa = csa_z462_arc_flash(lv_panel_case)

        # Mesma energia incidente (CSA wraps IEEE)
        assert csa.incident_energy_cal_cm2 == pytest.approx(
            ieee.incident_energy_cal_cm2, rel=1e-6,
        )
        assert csa.arc_flash_boundary_mm == pytest.approx(
            ieee.arc_flash_boundary_mm, rel=1e-6,
        )


class TestCSARiskCategoryMapping:

    def test_low_energy_returns_risk_0_or_1(self):
        from app.standards.csa_z462_arc_flash import (
            map_to_csa_risk_category,
        )
        assert map_to_csa_risk_category(0.5) == "Risk Cat 0"
        assert map_to_csa_risk_category(2.0) == "Risk Cat 1"

    def test_medium_energy_returns_risk_2(self):
        from app.standards.csa_z462_arc_flash import (
            map_to_csa_risk_category,
        )
        assert map_to_csa_risk_category(6.0) == "Risk Cat 2"

    def test_high_energy_returns_risk_3(self):
        from app.standards.csa_z462_arc_flash import (
            map_to_csa_risk_category,
        )
        assert map_to_csa_risk_category(15.0) == "Risk Cat 3"

    def test_very_high_energy_returns_risk_4(self):
        from app.standards.csa_z462_arc_flash import (
            map_to_csa_risk_category,
        )
        assert map_to_csa_risk_category(30.0) == "Risk Cat 4"

    def test_extreme_energy_returns_dangerous(self):
        from app.standards.csa_z462_arc_flash import (
            map_to_csa_risk_category,
        )
        assert "DANGEROUS" in map_to_csa_risk_category(50.0).upper() \
            or "PERIGO" in map_to_csa_risk_category(50.0).upper()
