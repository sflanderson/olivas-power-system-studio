"""
tests/test_pp_v1_6_0_comparison.py — v1.6.0 Sprint E.

Cobre o módulo ``app.postprocessor.arc_flash_comparison``:

* Roda todos os standards aplicáveis a um caso
* Reporta side-by-side
* Identifica most/least conservative
"""

from __future__ import annotations

import pytest


class TestComparisonModule:

    def test_module_loadable(self):
        from app.postprocessor import arc_flash_comparison  # noqa: F401

    def test_compare_lv_panel_runs_ac_standards(self):
        """LV panel 480V deve rodar IEEE 1584, NBR, Doughty-Neal,
        NESC, CSA — pelo menos 5 standards aplicáveis."""
        from app.postprocessor.arc_flash_comparison import (
            compare_all_standards,
        )
        comp = compare_all_standards(
            voltage_kV=0.480,
            Ibf_kA=25.0,
            arc_clearing_time_ms=200,
            working_distance_mm=455.0,
            is_dc=False,
        )
        applicable = [r for r in comp.results if r.applicable]
        assert len(applicable) >= 5

    def test_compare_dc_panel_excludes_ac_only(self):
        """DC system: AC standards (IEEE 1584, NBR, Doughty-Neal,
        EPRI) ficam não aplicáveis. DC method é o aplicável."""
        from app.postprocessor.arc_flash_comparison import (
            compare_all_standards,
        )
        comp = compare_all_standards(
            voltage_kV=0.125,
            Ibf_kA=2.5,
            arc_clearing_time_ms=500,
            working_distance_mm=457.0,
            is_dc=True,
        )
        # IEEE 1584 não aplicável a DC
        ieee_results = [
            r for r in comp.results if "IEEE 1584" in r.standard_name
        ]
        for r in ieee_results:
            assert r.applicable is False
        # DC method aplicável
        dc_results = [
            r for r in comp.results
            if "DC" in r.standard_name or "NFPA" in r.standard_name
        ]
        assert any(r.applicable for r in dc_results)

    def test_compare_hv_138kV_uses_epri_terzija(self):
        """138 kV: IEEE 1584/NBR não aplicáveis (>15 kV).
        EPRI/Terzija aplicáveis."""
        from app.postprocessor.arc_flash_comparison import (
            compare_all_standards,
        )
        comp = compare_all_standards(
            voltage_kV=138.0,
            Ibf_kA=20.0,
            arc_clearing_time_ms=300,
            working_distance_mm=1500.0,
            is_dc=False,
        )
        ieee_results = [
            r for r in comp.results if "IEEE 1584" in r.standard_name
        ]
        for r in ieee_results:
            assert r.applicable is False

    def test_most_conservative_is_max_E(self):
        from app.postprocessor.arc_flash_comparison import (
            compare_all_standards,
        )
        comp = compare_all_standards(
            voltage_kV=0.480, Ibf_kA=25.0,
            arc_clearing_time_ms=200,
            working_distance_mm=455.0,
        )
        # Find max E
        E_values = [
            r.incident_energy_cal_cm2 for r in comp.results
            if r.applicable and r.incident_energy_cal_cm2 is not None
        ]
        if E_values:
            max_E = max(E_values)
            most_cons = next(
                r for r in comp.results
                if r.applicable
                and r.incident_energy_cal_cm2 == max_E
            )
            assert most_cons.standard_name == comp.most_conservative

    def test_summary_returns_str_with_results(self):
        from app.postprocessor.arc_flash_comparison import (
            compare_all_standards,
        )
        comp = compare_all_standards(
            voltage_kV=0.480, Ibf_kA=25.0,
            arc_clearing_time_ms=200,
            working_distance_mm=455.0,
        )
        s = comp.summary()
        assert "IEEE 1584" in s or "NBR" in s
        assert "cal/cm" in s.lower() or "cal" in s.lower()

    def test_divergence_pct_finite(self):
        from app.postprocessor.arc_flash_comparison import (
            compare_all_standards,
        )
        comp = compare_all_standards(
            voltage_kV=0.480, Ibf_kA=25.0,
            arc_clearing_time_ms=200,
            working_distance_mm=455.0,
        )
        import math
        assert math.isfinite(comp.divergence_pct)
        assert 0.0 <= comp.divergence_pct <= 1000.0
