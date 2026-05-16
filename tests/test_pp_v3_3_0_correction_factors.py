"""
tests/test_pp_v3_3_0_correction_factors.py — v3.3.0 Sprints 2, 4, 5.

* Sprint 2 — kappa_method dropdown wiring (A/B/C produce different κ)
* Sprint 4 — build_equipment_from_project (auto-extract from PpProject)
* Sprint 5 — KT / KG / KSO impedance correction factors (IEC 60909)
"""

from __future__ import annotations

import math
import pytest


# ===========================================================================
# Sprint 2 — kappa_method wiring
# ===========================================================================


class TestKappaMethodsDifferentResults:

    def test_method_A_vs_B_differ_for_same_xr(self):
        from app.standards.iec60909_kappa import KappaMethod, kappa_recommended
        ka = kappa_recommended(r_over_x_at_fn=0.1, method=KappaMethod.METHOD_A)
        kb = kappa_recommended(r_over_x_at_fn=0.1, method=KappaMethod.METHOD_B)
        assert ka != kb
        # Method B is 1.15 × Method A capped at 2.0 (per IEC 60909-0 §4.4.1.2)
        assert kb >= ka

    def test_method_B_capped_at_2(self):
        from app.standards.iec60909_kappa import KappaMethod, kappa_recommended
        # Very high X/R → κ_A near 1.96, B = 1.15 × 1.96 = 2.25 → capped to 2.0
        kb = kappa_recommended(
            r_over_x_at_fn=0.001, method=KappaMethod.METHOD_B,
        )
        assert kb <= 2.0


# ===========================================================================
# Sprint 4 — build_equipment_from_project
# ===========================================================================


class TestBuildEquipmentFromProject:

    def test_empty_project_yields_empty_list(self):
        from app.postprocessor.equipment_eval import (
            build_equipment_from_project,
        )
        from app.preprocessor.models import PpProject
        proj = PpProject()
        equipments = build_equipment_from_project(proj)
        assert equipments == []

    def test_breaker_extracted(self):
        from app.postprocessor.equipment_eval import (
            build_equipment_from_project,
        )
        from app.preprocessor.models import PpComponent, PpProject, PpProperty
        proj = PpProject()
        proj.components.append(PpComponent(
            type="BREAKER", name="Q1", visible=True,
            x=0, y=0, label_dx=10, label_dy=-20, mirror=0, rotation=0,
            properties=[PpProperty("Q-01", True)],
        ))
        equipments = build_equipment_from_project(proj)
        assert len(equipments) == 1
        assert equipments[0].equipment_type == "breaker"
        assert equipments[0].equipment_id == "Q1"

    def test_skips_non_eq_types(self):
        """R, L, C genéricos não são equipamentos — devem ser pulados."""
        from app.postprocessor.equipment_eval import (
            build_equipment_from_project,
        )
        from app.preprocessor.models import PpComponent, PpProject, PpProperty
        proj = PpProject()
        for code in ("R", "L", "C", "GND", "Vdc"):
            proj.components.append(PpComponent(
                type=code, name=f"X-{code}", visible=True,
                x=0, y=0, label_dx=10, label_dy=-20, mirror=0, rotation=0,
                properties=[PpProperty("1", True)],
            ))
        equipments = build_equipment_from_project(proj)
        assert equipments == []

    def test_multiple_types_extracted(self):
        from app.postprocessor.equipment_eval import (
            build_equipment_from_project,
        )
        from app.preprocessor.models import PpComponent, PpProject, PpProperty
        proj = PpProject()
        for type_code in ("BREAKER", "FUSE", "BUS", "CABLE", "MOTOR", "Tr"):
            proj.components.append(PpComponent(
                type=type_code, name=f"{type_code}-1", visible=True,
                x=0, y=0, label_dx=10, label_dy=-20, mirror=0, rotation=0,
                properties=[PpProperty("dummy", True)],
            ))
        equipments = build_equipment_from_project(proj)
        types = {eq.equipment_type for eq in equipments}
        # All 6 should map
        assert types == {"breaker", "fuse", "bus", "cable", "motor", "transformer"}

    def test_extracts_voltage_from_property_string(self):
        from app.postprocessor.equipment_eval import (
            build_equipment_from_project,
        )
        from app.preprocessor.models import PpComponent, PpProject, PpProperty
        proj = PpProject()
        proj.components.append(PpComponent(
            type="BREAKER", name="Q1", visible=True,
            x=0, y=0, label_dx=10, label_dy=-20, mirror=0, rotation=0,
            properties=[PpProperty("Q-01", True), PpProperty("15 kV", True)],
        ))
        equipments = build_equipment_from_project(proj)
        assert len(equipments) == 1
        # Heuristic extracted "15 kV" → 15.0
        assert equipments[0].rated_voltage_kV == 15.0

    def test_none_project_yields_empty(self):
        from app.postprocessor.equipment_eval import (
            build_equipment_from_project,
        )
        equipments = build_equipment_from_project(None)
        assert equipments == []


# ===========================================================================
# Sprint 5 — KT (transformer correction factor)
# ===========================================================================


class TestTransformerCorrectionFactor_KT:

    def test_kt_typical_values(self):
        """For typical TX (x=0.05, c=1.10): KT ≈ 0.95 × 1.10 / 1.030 = 1.014"""
        from app.standards.iec60909 import transformer_correction_factor_KT
        kt = transformer_correction_factor_KT(
            voltage_factor_c_max=1.10, x_T_pu=0.05,
        )
        # 0.95 × 1.10 / (1 + 0.6 × 0.05) = 1.045 / 1.03 = 1.0146
        assert kt == pytest.approx(1.0146, abs=1e-3)

    def test_kt_high_reactance(self):
        """For very high x: KT decreases below 1."""
        from app.standards.iec60909 import transformer_correction_factor_KT
        kt = transformer_correction_factor_KT(
            voltage_factor_c_max=1.10, x_T_pu=0.30,
        )
        # 0.95 × 1.10 / (1 + 0.18) = 1.045 / 1.18 = 0.886
        assert kt == pytest.approx(0.886, abs=1e-3)

    def test_kt_invalid_raises(self):
        from app.standards.iec60909 import transformer_correction_factor_KT
        with pytest.raises(ValueError):
            transformer_correction_factor_KT(
                voltage_factor_c_max=1.10, x_T_pu=0.0,
            )
        with pytest.raises(ValueError):
            transformer_correction_factor_KT(
                voltage_factor_c_max=0.0, x_T_pu=0.05,
            )


# ===========================================================================
# Sprint 5 — KG (generator correction factor)
# ===========================================================================


class TestGeneratorCorrectionFactor_KG:

    def test_kg_typical(self):
        """For c=1.10, xd''=0.20, cos φ=0.85: KG = 1.10 / (1 + 0.20 × 0.527)"""
        from app.standards.iec60909 import generator_correction_factor_KG
        kg = generator_correction_factor_KG(
            voltage_factor_c_max=1.10,
            x_d_subtransient_pu=0.20,
            cos_phi_rg=0.85,
        )
        # sin(arccos(0.85)) = 0.527
        # KG = 1.10 / (1 + 0.20 × 0.527) = 1.10 / 1.1054 = 0.995
        assert kg == pytest.approx(0.995, abs=1e-3)

    def test_kg_at_unity_pf(self):
        """At cos φ = 1.0: KG = c (no correction since sin φ = 0)."""
        from app.standards.iec60909 import generator_correction_factor_KG
        kg = generator_correction_factor_KG(
            voltage_factor_c_max=1.10,
            x_d_subtransient_pu=0.20,
            cos_phi_rg=1.0,
        )
        assert kg == pytest.approx(1.10, abs=1e-9)

    def test_kg_invalid_raises(self):
        from app.standards.iec60909 import generator_correction_factor_KG
        with pytest.raises(ValueError):
            generator_correction_factor_KG(
                voltage_factor_c_max=1.10,
                x_d_subtransient_pu=-0.1,
            )
        with pytest.raises(ValueError):
            generator_correction_factor_KG(
                voltage_factor_c_max=1.10,
                x_d_subtransient_pu=0.20,
                cos_phi_rg=1.5,  # invalid
            )


# ===========================================================================
# Sprint 5 — KSO (motor correction factor)
# ===========================================================================


class TestMotorCorrectionFactor_KSO:

    def test_kso_typical(self):
        """For c=1.10, xM''=0.20, cos φ=0.83: KSO ≈ 0.985"""
        from app.standards.iec60909 import motor_correction_factor_KSO
        kso = motor_correction_factor_KSO(
            voltage_factor_c_max=1.10,
            x_M_subtransient_pu=0.20,
            cos_phi_motor=0.83,
        )
        # sin(arccos(0.83)) = 0.5577
        # KSO = 1.10 / (1 + 0.20 × 0.5577) = 1.10 / 1.1116 = 0.989
        assert kso == pytest.approx(0.989, abs=1e-2)

    def test_kso_factors_signature_distinct_from_KG(self):
        """KSO uses cos_phi_motor (default 0.83) vs KG uses cos_phi_rg (0.85)."""
        from app.standards.iec60909 import (
            generator_correction_factor_KG, motor_correction_factor_KSO,
        )
        # Same physics but different defaults
        kg = generator_correction_factor_KG(
            voltage_factor_c_max=1.10, x_d_subtransient_pu=0.20,
        )  # default cos_phi_rg=0.85
        kso = motor_correction_factor_KSO(
            voltage_factor_c_max=1.10, x_M_subtransient_pu=0.20,
        )  # default cos_phi_motor=0.83
        # They should be close but different (due to cos φ default)
        assert kg != kso


# ===========================================================================
# 7ª garantia — verify wiring
# ===========================================================================


class TestSeventhGuaranteeAccessibility:

    def test_kappa_method_wired_in_analysis_dialogs(self):
        """analysis_dialogs.run_short_circuit_analysis uses kappa_recommended."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/analysis_dialogs.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        # Sprint 2 wired the kappa_method dropdown
        assert "kappa_user = kappa_recommended" in content
        assert "Method A" in content or "method = " in content

    def test_iec60909_exports_kt_kg_kso(self):
        """IEC 60909 module must export the 3 correction factors."""
        from app.standards.iec60909 import (
            transformer_correction_factor_KT,
            generator_correction_factor_KG,
            motor_correction_factor_KSO,
        )
        assert callable(transformer_correction_factor_KT)
        assert callable(generator_correction_factor_KG)
        assert callable(motor_correction_factor_KSO)
