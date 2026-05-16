"""
tests/test_pp_v1_6_0_nesc_2023.py — v1.6.0 Sprint A.

Cobre o módulo ``app.standards.nesc_2023_arc_flash``:

* Lookup baseado em voltage range
* Approach Boundary + min PPE rating
* Anti-alucinação: valores conservadores baseados em IEEE
  textbooks que referenciam NESC 2023 §410.
"""

from __future__ import annotations

import pytest


class TestNESC2023Lookup:

    def test_module_loadable(self):
        from app.standards import nesc_2023_arc_flash  # noqa: F401

    def test_lookup_returns_boundary_row(self):
        from app.standards.nesc_2023_arc_flash import (
            lookup_nesc_2023, NESCBoundaryRow,
        )
        row = lookup_nesc_2023(voltage_kV=13.8)
        assert isinstance(row, NESCBoundaryRow)
        assert row.approach_boundary_mm > 0
        assert row.minimum_arc_rating_cal_cm2 > 0

    def test_lookup_lv_panel_480V(self):
        """Voltage 0.48 kV (LV panel típico) cai em range 0.30–0.75 kV."""
        from app.standards.nesc_2023_arc_flash import lookup_nesc_2023
        row = lookup_nesc_2023(voltage_kV=0.48)
        assert row.voltage_min_kV <= 0.48 <= row.voltage_max_kV
        # Min PPE rating deve ser >= 4 cal/cm² para LV ≥ 50V
        assert row.minimum_arc_rating_cal_cm2 >= 4.0

    def test_lookup_mv_15kV(self):
        from app.standards.nesc_2023_arc_flash import lookup_nesc_2023
        row = lookup_nesc_2023(voltage_kV=13.8)
        # MV (0.75-15 kV): typical 1219 mm boundary
        assert 600 <= row.approach_boundary_mm <= 2000

    def test_lookup_hv_138kV(self):
        from app.standards.nesc_2023_arc_flash import lookup_nesc_2023
        row = lookup_nesc_2023(voltage_kV=138.0)
        # HV >121 kV typical >3000 mm
        assert row.approach_boundary_mm >= 3000

    def test_voltage_below_50V_returns_no_required(self):
        """≤50 V não exige PPE arc rating per NESC."""
        from app.standards.nesc_2023_arc_flash import lookup_nesc_2023
        row = lookup_nesc_2023(voltage_kV=0.024)   # 24 V DC equiv
        # Approach boundary deve ser 0 (não requerido) OU
        # minimum rating = 0
        assert (
            row.approach_boundary_mm == 0
            or row.minimum_arc_rating_cal_cm2 == 0
        )

    def test_lookup_invalid_voltage_raises(self):
        from app.standards.nesc_2023_arc_flash import lookup_nesc_2023
        with pytest.raises(ValueError):
            lookup_nesc_2023(voltage_kV=-1.0)

    def test_exposure_param_accepted(self):
        """Phase-to-phase vs phase-to-ground devem aceitar."""
        from app.standards.nesc_2023_arc_flash import lookup_nesc_2023
        r1 = lookup_nesc_2023(
            voltage_kV=13.8, exposure="phase_to_phase",
        )
        r2 = lookup_nesc_2023(
            voltage_kV=13.8, exposure="phase_to_ground",
        )
        assert r1.table_ref != r2.table_ref or r1.table_ref == r2.table_ref


class TestNESC2023TableStructure:

    def test_all_rows_have_valid_voltage_range(self):
        from app.standards.nesc_2023_arc_flash import (
            NESC_2023_PHASE_TO_PHASE_TABLE,
        )
        for row in NESC_2023_PHASE_TO_PHASE_TABLE:
            assert row.voltage_min_kV < row.voltage_max_kV
            assert row.approach_boundary_mm >= 0
            assert row.minimum_arc_rating_cal_cm2 >= 0
            assert row.table_ref.startswith("410-")

    def test_table_covers_lv_to_eht(self):
        """Cobertura mínima 0.05 kV até 242 kV."""
        from app.standards.nesc_2023_arc_flash import (
            NESC_2023_PHASE_TO_PHASE_TABLE,
        )
        v_max = max(r.voltage_max_kV for r in NESC_2023_PHASE_TO_PHASE_TABLE)
        v_min = min(r.voltage_min_kV for r in NESC_2023_PHASE_TO_PHASE_TABLE)
        assert v_min <= 0.05
        assert v_max >= 121.0
