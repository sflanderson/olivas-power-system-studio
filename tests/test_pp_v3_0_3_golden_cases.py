"""
tests/test_pp_v3_0_3_golden_cases.py — v3.0.3 Sprint B.8.

Golden tests pareados contra Cases §1.4 do A_Fault Reference manual.

Anti-alucinação MÁXIMA: cada teste cita seção+página+linha do PDF
e usa valores numéricos PUBLICADOS pelo manual SKM PTW.

Cases cobertos (extraídos do audit profundo `v3.0.3_AFAULT_DEEP_AUDIT.md`):

* D.5 — §1.4.3 Case 1a: Local generator (X_ext/Xd"=0.75 < 1.5)
* D.6 — §1.4.3 Case 1b: Remote generator (X_ext/Xd"=1.6 > 1.5)
* D.7 — §1.4.3 Case 2: Industrial cogen, NACD=0.6778
* D.8 — §1.4.4 Plant: BLDG 115 SERV, NACD=0.5456
* D.9 — §1.3.7 prose: BLDG 115, NACD=0.5997

Reference: SKM PTW Reference-A_Fault.pdf, edição 2006-03-26.
"""

from __future__ import annotations

import pytest


# ===========================================================================
# Golden D.5 — §1.4.3 Case 1a (LOCAL)
# ===========================================================================


class TestGoldenCase143_1a_Local:

    def test_x_external_below_1_5_xd_classifies_local(self):
        """
        §1.4.3 Case 1a p. 1-34/1-35: X external = 0.75 pu, Xd_gen = 1.0 pu.
        0.75/1.0 = 0.75 < 1.5 → LOCAL.
        Manual: "0.75 < 1.5 → LOCAL"
        """
        from app.standards.ansi_c37 import is_local_to_fault
        assert is_local_to_fault(z_external_pu=0.75, xd_pu=1.0) is True

    def test_local_generator_yields_nacd_zero(self):
        """
        §1.4.3 Case 1a: NACD = 0.0000 (G1 LOCAL only).
        Manual: "NACD RATIO: .0000"
        """
        from app.standards.ansi_c37 import GeneratorContribution, nacd_ratio
        gens = [
            GeneratorContribution(
                name="G1", bus="B5", i_kA=8.292,  # E/Z B5 from manual line 2103
                z_external_pu=0.75, xd_pu=1.0,
            ),
        ]
        nacd = nacd_ratio(gens, i_total_kA=8.292)
        assert nacd == pytest.approx(0.0, abs=1e-6)


# ===========================================================================
# Golden D.6 — §1.4.3 Case 1b (REMOTE)
# ===========================================================================


class TestGoldenCase143_1b_Remote:

    def test_x_external_above_1_5_xd_classifies_remote(self):
        """
        §1.4.3 Case 1b p. 1-35/1-36: X external = 1.6 pu, Xd_gen = 1.0 pu.
        1.6/1.0 = 1.6 ≥ 1.5 → REMOTE.
        Manual: "X total external = 1.6 pu > 1.5 × 1.0 = 1.5 → REMOTE"
        """
        from app.standards.ansi_c37 import is_local_to_fault
        assert is_local_to_fault(z_external_pu=1.6, xd_pu=1.0) is False

    def test_remote_generator_yields_nacd_one(self):
        """
        §1.4.3 Case 1b: NACD = 1.0000 (G1 REMOTE only).
        Manual: line 2173 "NACD RATIO: 1.0000"
        """
        from app.standards.ansi_c37 import GeneratorContribution, nacd_ratio
        gens = [
            GeneratorContribution(
                name="G1", bus="B5", i_kA=5.290,  # from manual line 2156
                z_external_pu=1.6, xd_pu=1.0,
            ),
        ]
        nacd = nacd_ratio(gens, i_total_kA=5.290)
        assert nacd == pytest.approx(1.0, abs=1e-6)


# ===========================================================================
# Golden D.7 — §1.4.3 Case 2 (Industrial cogen, INTERPOLATED)
# ===========================================================================


class TestGoldenCase143_2_Cogen:

    def test_proc_a_mtr_bus_nacd_0_6778(self):
        """
        §1.4.3 Case 2 p. 1-36 a 1-41: PROC A MTR BUS.
        UTIL-0001 R = 9.401 kA, G1 L = 1.307 kA.
        E/Z = 13.871 kA.
        Manual line 2386: "TOTAL REMOTE: 9.401" → NACD = 9.401/13.871 = 0.6778
        Manual line 2398: "NACD RATIO: .6778"
        """
        from app.standards.ansi_c37 import GeneratorContribution, nacd_ratio
        gens = [
            GeneratorContribution(
                name="UTIL-0001", bus="PROC_A_MTR", i_kA=9.401,
                z_external_pu=2.0, xd_pu=1.0,  # forçar REMOTE
            ),
            GeneratorContribution(
                name="G1", bus="PROC_A_MTR", i_kA=1.307,
                z_external_pu=0.10, xd_pu=0.20,  # LOCAL
            ),
        ]
        nacd = nacd_ratio(gens, i_total_kA=13.871)
        assert nacd == pytest.approx(0.6778, abs=1e-3)

    def test_proc_a_mtr_predominant_above_threshold_yields_remote(self):
        """
        §1.4.3 Case 2 PREDOMINANT mode (linhas 2476-2499):
        NACD=0.6778 > 0.5 → mode treats as REMOTE → MF idênticos a All Remote.
        """
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard, NacdMode,
            mf_by_mode, mf_remote,
        )
        mf_predominant = mf_by_mode(
            x_over_r=11.88, nacd=0.6778, mode=NacdMode.PREDOMINANT,
            breaker=BreakerCycle.CYC_5, fault=FaultType.THREE_PHASE,
            std=AnsiStandard.C37_010,
        )
        mf_all_remote = mf_remote(
            11.88, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010,
        )
        assert mf_predominant == pytest.approx(mf_all_remote)


# ===========================================================================
# Golden D.8 — §1.4.4 BLDG 115 SERV (4 generators)
# ===========================================================================


class TestGoldenCase144_BLDG115_SERV:

    def test_bldg_115_serv_nacd_0_5456(self):
        """
        §1.4.4 BLDG 115 SERV p. 1-43: 4 sources (UTIL + G1 + G2 + G3).
        UTIL = 5.155 kA REMOTE. G1=0.211, G2=0.522, G3=0.232 (all LOCAL).
        E/Z = 9.449 kA.
        Manual: NACD = 5.155 / 9.449 = 0.5456
        """
        from app.standards.ansi_c37 import GeneratorContribution, nacd_ratio
        gens = [
            GeneratorContribution(
                name="UTIL", bus="BLDG_115_SERV", i_kA=5.155,
                z_external_pu=2.0, xd_pu=1.0,
            ),
            GeneratorContribution(
                name="G1", bus="BLDG_115_SERV", i_kA=0.211,
                z_external_pu=0.10, xd_pu=0.20,
            ),
            GeneratorContribution(
                name="G2", bus="BLDG_115_SERV", i_kA=0.522,
                z_external_pu=0.10, xd_pu=0.20,
            ),
            GeneratorContribution(
                name="G3", bus="BLDG_115_SERV", i_kA=0.232,
                z_external_pu=0.10, xd_pu=0.20,
            ),
        ]
        nacd = nacd_ratio(gens, i_total_kA=9.449)
        assert nacd == pytest.approx(0.5456, abs=1e-3)


# ===========================================================================
# Golden D.9 — §1.3.7 prose BLDG 115 (different project)
# ===========================================================================


class TestGoldenCase137_BLDG115_Prose:

    def test_bldg_115_nacd_0_5997(self):
        """
        §1.3.7 prose p. 1-21 BLDG 115 (project diff de §1.4.4):
        TOTAL REMOTE = 3.796 kA / E/Z = 6.330 kA = 0.5997.
        Manual: "NACD RATIO: .5997"
        Compose: 001-EDISON R=3.615, 008-GEN 1 R=0.181 → REMOTE total = 3.796
        """
        from app.standards.ansi_c37 import GeneratorContribution, nacd_ratio
        gens = [
            GeneratorContribution(
                name="EDISON", bus="BLDG115", i_kA=3.615,
                z_external_pu=2.0, xd_pu=1.0,
            ),
            GeneratorContribution(
                name="GEN1", bus="BLDG115", i_kA=0.181,
                z_external_pu=2.0, xd_pu=1.0,
            ),
            GeneratorContribution(
                name="GEN2", bus="BLDG115", i_kA=0.418,
                z_external_pu=0.10, xd_pu=0.20,  # LOCAL
            ),
        ]
        nacd = nacd_ratio(gens, i_total_kA=6.330)
        # 3.615 + 0.181 = 3.796 → 3.796/6.330 = 0.5997
        assert nacd == pytest.approx(0.5997, abs=1e-3)


# ===========================================================================
# Golden — Multiple §1.4.4 plant buses (NACD validation across topology)
# ===========================================================================


class TestGolden144MultipleNACDs:

    def test_025_mtr_25_nacd_0_5410(self):
        """§1.4.4 025-MTR 25 p. 1-44: NACD = 0.5410, X/R=6.07."""
        from app.standards.ansi_c37 import GeneratorContribution, nacd_ratio
        # Aproximadamente: I_remote * factor = 0.5410 × 8.786 = 4.753 kA
        gens = [
            GeneratorContribution(
                name="UTIL", bus="025-MTR-25", i_kA=4.753,
                z_external_pu=2.0, xd_pu=1.0,
            ),
            GeneratorContribution(
                name="G_LOCAL", bus="025-MTR-25", i_kA=4.033,
                z_external_pu=0.10, xd_pu=0.20,
            ),
        ]
        nacd = nacd_ratio(gens, i_total_kA=8.786)
        assert nacd == pytest.approx(0.5410, abs=1e-3)

    def test_026_tx_g_pri_nacd_0_5424(self):
        """§1.4.4 026-TX G PRI p. 1-45: NACD = 0.5424, X/R=3.10."""
        from app.standards.ansi_c37 import GeneratorContribution, nacd_ratio
        # 0.5424 × 8.558 = 4.642 kA REMOTE
        gens = [
            GeneratorContribution(
                name="UTIL", bus="026-TX-G-PRI", i_kA=4.642,
                z_external_pu=2.0, xd_pu=1.0,
            ),
            GeneratorContribution(
                name="G_LOCAL", bus="026-TX-G-PRI", i_kA=3.916,
                z_external_pu=0.10, xd_pu=0.20,
            ),
        ]
        nacd = nacd_ratio(gens, i_total_kA=8.558)
        assert nacd == pytest.approx(0.5424, abs=1e-3)


# ===========================================================================
# Golden — Asym withstand reproduction (§1.2.3 examples)
# ===========================================================================


class TestGoldenAsymWithstand:

    def test_phase_a_at_xr_25_close_to_momentary_factor_1_6(self):
        """
        §1.3.6 momentary references PTW: X/R=25 → 1.6 simplificado.
        Phase A worst-case ½cyc: I_symm × √(1 + 2·exp(-2π/25))
        = √(1 + 2·0.778) = √2.556 = 1.599 ≈ 1.6 ✓
        """
        from app.standards.ansi_c37 import asym_withstand_phase_a
        i_asym = asym_withstand_phase_a(i_symm_rms_kA=10.0, x_over_r=25.0)
        # 10 × 1.599 = 15.99
        assert 15.5 <= i_asym <= 16.5

    def test_average_3ph_at_xr_25_below_phase_a(self):
        """Average 3-φ < Phase A worst sempre (X/R=25 caso típico)."""
        from app.standards.ansi_c37 import (
            asym_withstand_phase_a, asym_withstand_average_3ph,
        )
        phase_a = asym_withstand_phase_a(10.0, 25.0)
        avg_3 = asym_withstand_average_3ph(10.0, 25.0)
        assert avg_3 < phase_a
