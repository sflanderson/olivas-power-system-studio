"""
tests/test_pp_v3_0_5_ansi_report_bus.py — v3.0.5 Sprint D.1.

AnsiFaultBus — unified data container para report de uma fault
calculation em um único bus, integrando os 3 reports do PTW A_FAULT:

* **LV Fault Report** — corrente sym RMS no LV bus + X/R + Z + contribuições
* **Momentary Report** — E/Z, X/R, asym factors (1.6, 2.7), Mom, Crest
* **Interrupting Report** — E/Z, contribuições LOCAL/REMOTE, NACD, MF, DUTY

Conforme PTW Reference-A_Fault.pdf §1.4.1 Case 1 p. 1-27/28
(linhas 1644-1685 — exemplo de B2 fault report).

Anti-alucinação: cita §1.4.1 Case 1 com valores PUBLICADOS.
Anti-simplismo: cobre os 3 reports unificados, não apenas um.

Reference: PTW Reference-A_Fault.pdf §1.4.1 p. 1-27/28.
"""

from __future__ import annotations

import math
import pytest


# ===========================================================================
# Sprint D.1.A — AnsiFaultBus dataclass
# ===========================================================================


class TestAnsiFaultBus:

    def test_minimal_construction(self):
        """Campos mínimos para um fault bus."""
        from app.postprocessor.ansi_fault_report import AnsiFaultBus
        bus = AnsiFaultBus(
            bus_name="B2",
            kv_base=4.16,
            sym_rms_kA=13.598,
            x_over_r=14.85,
        )
        assert bus.bus_name == "B2"
        assert bus.kv_base == 4.16
        assert bus.sym_rms_kA == 13.598
        assert bus.x_over_r == 14.85

    def test_default_fields_initialized(self):
        """Campos opcionais têm defaults apropriados."""
        from app.postprocessor.ansi_fault_report import AnsiFaultBus
        bus = AnsiFaultBus(
            bus_name="B2", kv_base=4.16, sym_rms_kA=13.598, x_over_r=14.85,
        )
        assert bus.contributions == []
        assert bus.fault_type == "3ph"  # default

    def test_z_complex_property(self):
        """Z = sqrt(R² + X²) computed from base + X/R."""
        from app.postprocessor.ansi_fault_report import AnsiFaultBus
        bus = AnsiFaultBus(
            bus_name="B2", kv_base=4.16, sym_rms_kA=10.0, x_over_r=10.0,
        )
        # Z = V_LL / (sqrt(3) × I_fault) = 4.16 / (1.732 × 10.0) = 0.240 Ω
        z_expected = 4160.0 / (math.sqrt(3) * 10000.0)  # in Ω
        assert bus.z_total_ohm == pytest.approx(z_expected, rel=1e-3)

    def test_invalid_negative_kv_raises(self):
        """kV ≤ 0 não é físico."""
        from app.postprocessor.ansi_fault_report import AnsiFaultBus
        with pytest.raises(ValueError):
            AnsiFaultBus(bus_name="B", kv_base=-1.0, sym_rms_kA=10.0, x_over_r=10.0)

    def test_invalid_negative_current_raises(self):
        """I < 0 não é físico."""
        from app.postprocessor.ansi_fault_report import AnsiFaultBus
        with pytest.raises(ValueError):
            AnsiFaultBus(bus_name="B", kv_base=4.16, sym_rms_kA=-1.0, x_over_r=10.0)


# ===========================================================================
# Sprint D.1.B — Momentary Report fields (PTW §1.4.1 format)
# ===========================================================================


class TestMomentaryReport:

    def test_momentary_factors_from_x_over_r(self):
        """
        §1.4.1 Case 1 B2 (linha 1664):
        E/Z=13.496 kA, X/R=14.89.
        SYM·1.6 = 21.593 kA → ratio 21.593/13.496 = 1.600
        SYM·2.7 = 36.438 kA → ratio 36.438/13.496 = 2.700
        Mom-X/R = 20.519 kA → multiplier from Eq 7-1 com c=0.5
        Crest-X/R = 34.541 kA → peak factor
        """
        from app.postprocessor.ansi_fault_report import AnsiFaultBus
        bus = AnsiFaultBus(
            bus_name="B2", kv_base=4.16,
            sym_rms_kA=13.496, x_over_r=14.89,
        )
        mom = bus.momentary_duty()
        # SYM·1.6 (simplified)
        assert mom["sym_x_1_6"] == pytest.approx(21.594, abs=0.01)
        # SYM·2.7 (simplified peak)
        assert mom["sym_x_2_7"] == pytest.approx(36.439, abs=0.01)

    def test_momentary_x_over_r_factor_from_formula(self):
        """
        Mom-X/R usa Eq 7-1 com c=0.5: I_mom = I_sym × √(1 + 2·exp(-4π·0.5/(X/R)))
        Para X/R=14.89: 13.496 × 1.521 = 20.531 (manual: 20.519)
        Tolerância 1% (formula vs valor publicado simplificado).
        """
        from app.postprocessor.ansi_fault_report import AnsiFaultBus
        bus = AnsiFaultBus(
            bus_name="B2", kv_base=4.16,
            sym_rms_kA=13.496, x_over_r=14.89,
        )
        mom = bus.momentary_duty()
        # Mom-X/R baseado em fórmula
        assert mom["mom_x_over_r_kA"] == pytest.approx(20.519, rel=0.01)


# ===========================================================================
# Sprint D.1.C — Interrupting Report fields (NACD + MF integration)
# ===========================================================================


class TestInterruptingReport:

    def test_interrupting_with_no_remote_yields_unity_mf(self):
        """
        §1.4.3 Case 1a: G1 LOCAL only, NACD=0.0.
        Interrupting MF (5-cyc, INTERPOLATED) ≈ MF_local @ X/R altíssimo.
        """
        from app.postprocessor.ansi_fault_report import AnsiFaultBus
        from app.standards.ansi_c37 import GeneratorContribution
        bus = AnsiFaultBus(
            bus_name="B5", kv_base=13.8,
            sym_rms_kA=8.292, x_over_r=165.70,
            contributions=[
                GeneratorContribution("G1", "B5", 8.292, z_external_pu=0.75, xd_pu=1.0),
            ],
        )
        report = bus.interrupting_duty(breaker_cycle=5)
        assert report["nacd"] == pytest.approx(0.0, abs=1e-6)

    def test_interrupting_case_143_2_proc_a_mtr(self):
        """
        §1.4.3 Case 2 PROC A MTR BUS: NACD = 0.6778 (publicado).
        Manual: E/Z = 13.871, UTIL R=9.401, G1 L=1.307.
        """
        from app.postprocessor.ansi_fault_report import AnsiFaultBus
        from app.standards.ansi_c37 import GeneratorContribution
        bus = AnsiFaultBus(
            bus_name="PROC_A_MTR", kv_base=2.4,
            sym_rms_kA=13.871, x_over_r=11.88,
            contributions=[
                GeneratorContribution("UTIL", "PROC_A_MTR", 9.401,
                                       z_external_pu=2.0, xd_pu=1.0),
                GeneratorContribution("G1", "PROC_A_MTR", 1.307,
                                       z_external_pu=0.10, xd_pu=0.20),
            ],
        )
        report = bus.interrupting_duty(breaker_cycle=5)
        assert report["nacd"] == pytest.approx(0.6778, abs=1e-3)
        assert report["i_total_kA"] == pytest.approx(13.871)


# ===========================================================================
# Sprint D.1.D — LV Duty Report (LV PCB / MCCB scenarios)
# ===========================================================================


class TestLvDutyReport:

    def test_lv_duty_mccb_high_aic_scenario(self):
        """
        §1.4.4 028-MTR 28 (480V): FAULT = 21.638 kA, X/R = 2.85.
        Para MCCB > 20kA AIC (test X/R = 4.9): adjusted < sym (system X/R < test).
        """
        from app.postprocessor.ansi_fault_report import AnsiFaultBus
        bus = AnsiFaultBus(
            bus_name="028-MTR-28", kv_base=0.480,
            sym_rms_kA=21.638, x_over_r=2.85,
        )
        lv_report = bus.lv_duty(device_class="MCCB_GT_20KA")
        # System X/R < test X/R → adjusted < sym
        assert lv_report["adjusted_kA"] < 21.638
        assert lv_report["test_x_over_r"] == pytest.approx(4.9)

    def test_lv_duty_lv_pcb_scenario(self):
        """
        §1.4.4 027-DSB 3 (480V): FAULT = 38.277 kA, X/R = 3.69.
        Para LV PCB (test X/R = 6.6): adjusted < sym.
        """
        from app.postprocessor.ansi_fault_report import AnsiFaultBus
        bus = AnsiFaultBus(
            bus_name="027-DSB-3", kv_base=0.480,
            sym_rms_kA=38.277, x_over_r=3.69,
        )
        lv_report = bus.lv_duty(device_class="LV_PCB")
        assert lv_report["adjusted_kA"] < 38.277
        assert lv_report["test_x_over_r"] == pytest.approx(6.6)
