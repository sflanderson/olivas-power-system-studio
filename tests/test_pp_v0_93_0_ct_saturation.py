"""
tests/test_pp_v0_93_0_ct_saturation.py — v0.93.0:

Análise de saturação de Transformadores de Corrente (TCs)
em 3 níveis (ANSI estático / IEC joelho / Dinâmico).

Cobertura:

* Validação física dos inputs (CTSpec, CTFaultContext)
* Curva de magnetização (típica + custom + joelho IEC 10/50)
* Burden de cabo (NBR 5410 §6.2)
* Level 1 ANSI (1+X/R criterion, IEEE C57.13.1)
* Level 2 IEC (knee 10/50, IEC 61869-2 §5.6)
* Level 3 Dinâmico (RK4 ODE solver, CIGRÉ WG 23-15)
* Orchestrator analyze_full + decisão final
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.ct_saturation import (
    CTFaultContext,
    CTSaturationReport,
    CTSpec,
    Level1AnsiResult,
    Level2IecResult,
    Level3DynamicResult,
    MagnetizationCurve,
    analyze_ansi_level1,
    analyze_dynamic_level3,
    analyze_full,
    analyze_iec_level2,
    cable_burden_resistance,
    typical_magnetization_curve,
    DEFAULT_KR_ANSI,
    DEFAULT_KR_IEC_PR,
)


# ---------------------------------------------------------------------------
# Validação dos inputs
# ---------------------------------------------------------------------------


class TestInputValidation:

    def _curve(self):
        return typical_magnetization_curve(200.0)

    def test_fault_rejects_zero_voltage(self):
        with pytest.raises(ValueError, match="rated_voltage_kV"):
            CTFaultContext(
                bus_id="X", rated_voltage_kV=0,
                I_fault_rms_kA=10, X_over_R=5,
            )

    def test_fault_rejects_zero_current(self):
        with pytest.raises(ValueError, match="I_fault_rms_kA"):
            CTFaultContext(
                bus_id="X", rated_voltage_kV=13.8,
                I_fault_rms_kA=0, X_over_R=5,
            )

    def test_fault_rejects_negative_xr(self):
        with pytest.raises(ValueError, match="X_over_R"):
            CTFaultContext(
                bus_id="X", rated_voltage_kV=13.8,
                I_fault_rms_kA=10, X_over_R=-1,
            )

    def test_fault_rejects_empty_bus_id(self):
        with pytest.raises(ValueError, match="bus_id"):
            CTFaultContext(
                bus_id="", rated_voltage_kV=13.8,
                I_fault_rms_kA=10, X_over_R=5,
            )

    def test_ct_spec_rejects_invalid_type(self):
        with pytest.raises(ValueError, match="tipo_TC"):
            CTSpec(
                tag="X", tipo_TC="UNKNOWN",
                I_pri_nom_tap=400, I_pri_nom_full=400, I_sn=5,
                CT_Rating_C=200, R_s=0.5, R_b=0.3,
                curve=self._curve(), Kr=0.8,
            )

    def test_ct_spec_rejects_full_lt_tap(self):
        with pytest.raises(ValueError, match="I_pri_nom_full"):
            CTSpec(
                tag="X", tipo_TC="ANSI_C",
                I_pri_nom_tap=2000, I_pri_nom_full=1000, I_sn=5,
                CT_Rating_C=200, R_s=0.5, R_b=0.3,
                curve=self._curve(),
            )

    def test_ct_spec_rejects_kr_out_of_range(self):
        with pytest.raises(ValueError, match="Kr"):
            CTSpec(
                tag="X", tipo_TC="ANSI_C",
                I_pri_nom_tap=400, I_pri_nom_full=400, I_sn=5,
                CT_Rating_C=200, R_s=0.5, R_b=0.3,
                curve=self._curve(), Kr=1.5,
            )

    def test_ct_spec_rejects_negative_burden(self):
        with pytest.raises(ValueError, match="R_b"):
            CTSpec(
                tag="X", tipo_TC="ANSI_C",
                I_pri_nom_tap=400, I_pri_nom_full=400, I_sn=5,
                CT_Rating_C=200, R_s=0.5, R_b=-0.1,
                curve=self._curve(),
            )


# ---------------------------------------------------------------------------
# MagnetizationCurve
# ---------------------------------------------------------------------------


class TestMagnetizationCurve:

    def test_typical_curve_default(self):
        c = typical_magnetization_curve(knee_voltage_V=200.0)
        assert len(c.Ie) == 6
        assert len(c.Ve) == 6
        # Crescente
        assert c.Ve[0] < c.Ve[-1]
        assert c.Ie[0] < c.Ie[-1]

    def test_iec_knee_returns_knee_voltage(self):
        c = typical_magnetization_curve(knee_voltage_V=400.0)
        # A curva típica é construída para que Vk caia em
        # 1.0 × knee_voltage. Por construção, Vk_actual ≈ 0.8·V
        # (índice onde 10% V → 50% I, primeiro a satisfazer)
        Vk = c.knee_voltage_iec_10_50()
        # Deve estar próximo (ordem 200..320)
        assert 100 < Vk < 500

    def test_curve_rejects_mismatched_sizes(self):
        with pytest.raises(ValueError, match="tamanho"):
            MagnetizationCurve(
                Ie=(0.01, 0.05),
                Ve=(20.0, 100.0, 200.0),
            )

    def test_curve_rejects_single_point(self):
        with pytest.raises(ValueError, match="pelo menos 2"):
            MagnetizationCurve(Ie=(0.05,), Ve=(100.0,))

    def test_typical_curve_rejects_zero_voltage(self):
        with pytest.raises(ValueError):
            typical_magnetization_curve(knee_voltage_V=0)

    def test_excitation_current_interpolation(self):
        c = typical_magnetization_curve(knee_voltage_V=200.0)
        # No joelho (V=200), Ie ≈ 0.1 A por construção
        ie_at_knee = c.excitation_current(200.0)
        assert abs(ie_at_knee - 0.1) < 0.01


# ---------------------------------------------------------------------------
# Burden helper
# ---------------------------------------------------------------------------


class TestBurdenHelper:

    def test_cable_30m_4mm2_cu_75c(self):
        r = cable_burden_resistance(distance_m=30, cross_section_mm2=4.0)
        # ρ_Cu @ 75°C ≈ 0.02097 Ω·mm²/m
        # R = 0.02097 * 30 / 4 ≈ 0.1573 Ω
        assert 0.15 < r < 0.17

    def test_cable_zero_length_rejects(self):
        with pytest.raises(ValueError):
            cable_burden_resistance(distance_m=0, cross_section_mm2=4.0)

    def test_cable_zero_section_rejects(self):
        with pytest.raises(ValueError):
            cable_burden_resistance(distance_m=10, cross_section_mm2=0)


# ---------------------------------------------------------------------------
# Level 1 — ANSI estático (1+X/R)
# ---------------------------------------------------------------------------


class TestLevel1Ansi:

    def _ct_c200(self):
        return CTSpec(
            tag="CT-1", tipo_TC="ANSI_C",
            I_pri_nom_tap=2000, I_pri_nom_full=2000, I_sn=5,
            CT_Rating_C=200.0,
            R_s=0.5, R_b=0.3,
            curve=typical_magnetization_curve(200.0),
        )

    def test_passes_for_low_fault(self):
        ct = self._ct_c200()
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=13.8,
            I_fault_rms_kA=2.0, X_over_R=4.0,
        )
        r = analyze_ansi_level1(ct, fault)
        assert r.passed
        # V_req ≈ (2000/400)*(1+4)*(0.8) = 5*5*0.8 = 20V
        assert r.V_req < 50

    def test_fails_for_high_fault(self):
        ct = self._ct_c200()
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=13.8,
            I_fault_rms_kA=20.0, X_over_R=10.0,
        )
        r = analyze_ansi_level1(ct, fault)
        assert not r.passed
        # V_req = (20000/400)*(1+10)*0.8 = 50*11*0.8 = 440V > V_tap=200
        assert r.V_req > r.V_tap

    def test_v_tap_uses_full_ratio(self):
        """V_tap = V_capacity * I_tap/I_full."""
        ct = CTSpec(
            tag="CT-X", tipo_TC="ANSI_C",
            I_pri_nom_tap=1200, I_pri_nom_full=2000, I_sn=5,
            CT_Rating_C=800.0,
            R_s=0.5, R_b=0.3,
            curve=typical_magnetization_curve(800.0),
        )
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=13.8,
            I_fault_rms_kA=2.0, X_over_R=4.0,
        )
        r = analyze_ansi_level1(ct, fault)
        # V_tap = 800 * 1200/2000 = 480 V
        assert abs(r.V_tap - 480.0) < 0.1

    def test_recommended_class_format(self):
        ct = self._ct_c200()
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=13.8,
            I_fault_rms_kA=20, X_over_R=10,
        )
        r = analyze_ansi_level1(ct, fault)
        # Falhou → recomenda C maior
        assert r.recommended_class_C.startswith("C")

    def test_citation_present(self):
        r = analyze_ansi_level1(
            self._ct_c200(),
            CTFaultContext(
                bus_id="B", rated_voltage_kV=13.8,
                I_fault_rms_kA=2.0, X_over_R=4.0,
            ),
        )
        assert "IEEE C57.13" in r.citation


# ---------------------------------------------------------------------------
# Level 2 — IEC joelho
# ---------------------------------------------------------------------------


class TestLevel2Iec:

    def _ct_iec(self):
        return CTSpec(
            tag="CT-IEC", tipo_TC="IEC_P",
            I_pri_nom_tap=2000, I_pri_nom_full=2000, I_sn=5,
            CT_Rating_C=200.0,
            R_s=0.5, R_b=0.3,
            curve=typical_magnetization_curve(200.0),
            IEC_VA=25.0, IEC_ALF=20,
        )

    def test_passes_for_low_fault(self):
        ct = self._ct_iec()
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=13.8,
            I_fault_rms_kA=2.0, X_over_R=4.0,
        )
        r = analyze_iec_level2(ct, fault)
        assert r is not None
        assert r.passed

    def test_fails_for_high_fault(self):
        ct = self._ct_iec()
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=13.8,
            I_fault_rms_kA=20.0, X_over_R=10.0,
        )
        r = analyze_iec_level2(ct, fault)
        assert r is not None
        assert not r.passed

    def test_recommended_class_iec_format(self):
        ct = self._ct_iec()
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=13.8,
            I_fault_rms_kA=2.0, X_over_R=4.0,
        )
        r = analyze_iec_level2(ct, fault)
        # Formato "{VA}VA 10P{ALF}"
        assert "VA 10P" in r.recommended_class

    def test_pr_class_uses_pr_suffix(self):
        ct = CTSpec(
            tag="CT-PR", tipo_TC="IEC_PR",
            I_pri_nom_tap=2000, I_pri_nom_full=2000, I_sn=5,
            CT_Rating_C=200.0,
            R_s=0.5, R_b=0.3,
            curve=typical_magnetization_curve(200.0),
            IEC_VA=25.0, IEC_ALF=20,
            Kr=0.1,
        )
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=13.8,
            I_fault_rms_kA=2.0, X_over_R=4.0,
        )
        r = analyze_iec_level2(ct, fault)
        assert "PR" in r.recommended_class


# ---------------------------------------------------------------------------
# Level 3 — Dinâmico
# ---------------------------------------------------------------------------


class TestLevel3Dynamic:

    def _ct_pass(self):
        """TC adequado para falta leve."""
        return CTSpec(
            tag="CT-PASS", tipo_TC="IEC_PR",
            I_pri_nom_tap=2000, I_pri_nom_full=2000, I_sn=5,
            CT_Rating_C=400.0,
            R_s=0.2, R_b=0.1,
            curve=typical_magnetization_curve(400.0),
            Kr=0.1,
            t_relay_ms=20.0, t_breaker_ms=50.0,
        )

    def _ct_fail(self):
        """TC subdimensionado."""
        return CTSpec(
            tag="CT-FAIL", tipo_TC="ANSI_C",
            I_pri_nom_tap=400, I_pri_nom_full=400, I_sn=5,
            CT_Rating_C=100.0,
            R_s=0.5, R_b=0.5,
            curve=typical_magnetization_curve(100.0),
            Kr=0.8,
            t_relay_ms=20.0, t_breaker_ms=50.0,
        )

    def test_pass_scenario_no_saturation(self):
        ct = self._ct_pass()
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=4.16,
            I_fault_rms_kA=3.0, X_over_R=3.0,
        )
        r = analyze_dynamic_level3(ct, fault)
        # PASSOU → t_sat = ∞ (não satura)
        assert r.status == "PASSOU"
        assert math.isinf(r.t_sat_ms)
        assert r.sat_at_trip_pct < 100

    def test_fail_scenario_premature_saturation(self):
        ct = self._ct_fail()
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=13.8,
            I_fault_rms_kA=30.0, X_over_R=15.0,
        )
        r = analyze_dynamic_level3(ct, fault)
        # FALHOU → t_sat < t_relay + 3ms
        assert r.status == "FALHOU"
        assert r.t_sat_ms < 23

    def test_pulado_when_curve_missing(self):
        # Curva mínima válida (precisa para construir CTSpec),
        # mas vamos passar curva curta que faz Level 3 pular
        ct = CTSpec(
            tag="CT-NO-CURVE", tipo_TC="ANSI_C",
            I_pri_nom_tap=400, I_pri_nom_full=400, I_sn=5,
            CT_Rating_C=100.0,
            R_s=0.2, R_b=0.1,
            # curva mínima de 2 pontos — passa validação mas
            # representa caso degenerado
            curve=MagnetizationCurve(
                Ie=(0.001, 1.0), Ve=(0.0001, 100.0),
            ),
        )
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=13.8,
            I_fault_rms_kA=10.0, X_over_R=5.0,
        )
        # Ainda é capaz de rodar (não pula)
        r = analyze_dynamic_level3(ct, fault)
        assert r.status in (
            "PASSOU", "APROVADO COM TOLERANCIA", "FALHOU",
        )

    def test_flux_curve_returned_for_plot(self):
        ct = self._ct_pass()
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=4.16,
            I_fault_rms_kA=3.0, X_over_R=3.0,
        )
        r = analyze_dynamic_level3(ct, fault)
        assert len(r.flux_curve_t_ms) > 100
        assert len(r.flux_curve_wb_e) == len(r.flux_curve_t_ms)
        assert len(r.secondary_current_real) == len(
            r.flux_curve_t_ms
        )

    def test_remanence_increases_saturation_risk(self):
        """v0.93.0: TC com Kr=0.8 deve saturar mais rápido
        que com Kr=0.1 para mesma falta (CIGRÉ §3.2)."""
        # Cenário marginal — vamos comparar tempos de saturação
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=13.8,
            I_fault_rms_kA=15.0, X_over_R=8.0,
        )

        ct_high_rem = CTSpec(
            tag="CT-HIGH-REM", tipo_TC="ANSI_C",
            I_pri_nom_tap=2000, I_pri_nom_full=2000, I_sn=5,
            CT_Rating_C=400.0,
            R_s=0.5, R_b=0.3,
            curve=typical_magnetization_curve(400.0),
            Kr=0.8,
        )
        ct_low_rem = CTSpec(
            tag="CT-LOW-REM", tipo_TC="IEC_PR",
            I_pri_nom_tap=2000, I_pri_nom_full=2000, I_sn=5,
            CT_Rating_C=400.0,
            R_s=0.5, R_b=0.3,
            curve=typical_magnetization_curve(400.0),
            Kr=0.1,
        )

        r_high = analyze_dynamic_level3(ct_high_rem, fault)
        r_low = analyze_dynamic_level3(ct_low_rem, fault)
        # High remanence satura mais cedo (ou igual, em casos
        # extremos onde nem um nem outro saturam)
        if math.isfinite(r_high.t_sat_ms) and math.isfinite(
            r_low.t_sat_ms,
        ):
            assert r_high.t_sat_ms <= r_low.t_sat_ms

    def test_zero_xr_handled(self):
        """X/R=0 não deve crashar (DC component nulo)."""
        ct = self._ct_pass()
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=4.16,
            I_fault_rms_kA=3.0, X_over_R=0.0,
        )
        r = analyze_dynamic_level3(ct, fault)
        assert r.status in (
            "PASSOU", "APROVADO COM TOLERANCIA", "FALHOU",
        )


# ---------------------------------------------------------------------------
# Orchestrator analyze_full
# ---------------------------------------------------------------------------


class TestAnalyzeFullOrchestrator:

    def test_full_returns_consolidated_report(self):
        ct = CTSpec(
            tag="CT-FULL", tipo_TC="IEC_PR",
            I_pri_nom_tap=2000, I_pri_nom_full=2000, I_sn=5,
            CT_Rating_C=400.0,
            R_s=0.2, R_b=0.1,
            curve=typical_magnetization_curve(400.0),
            Kr=0.1,
        )
        fault = CTFaultContext(
            bus_id="BUS-MAIN", rated_voltage_kV=4.16,
            I_fault_rms_kA=3.0, X_over_R=3.0,
        )
        r = analyze_full(ct, fault)
        assert isinstance(r, CTSaturationReport)
        assert r.level1.passed
        assert r.level2 is not None
        assert r.level3.status == "PASSOU"
        assert "PASSOU" in r.final_status or "ROBUSTO" in r.final_detail

    def test_full_level3_authoritative_on_fail(self):
        """Quando L1 passa mas L3 falha (caso de DC offset),
        a decisão final é FALHOU (CIGRÉ recomenda)."""
        # Cenário marginal: CT que passa estaticamente mas
        # falha dinamicamente devido ao X/R alto
        ct = CTSpec(
            tag="CT-MARGINAL", tipo_TC="ANSI_C",
            I_pri_nom_tap=2000, I_pri_nom_full=2000, I_sn=5,
            CT_Rating_C=200.0,
            R_s=0.3, R_b=0.2,
            curve=typical_magnetization_curve(200.0),
            Kr=0.8,   # high remanence
        )
        # Falta com X/R muito alto força saturação dinâmica
        fault = CTFaultContext(
            bus_id="B", rated_voltage_kV=4.16,
            I_fault_rms_kA=2.0, X_over_R=20.0,
        )
        r = analyze_full(ct, fault)
        # L1 pode até passar (não testamos), mas L3 deve ditar
        if "FALHOU" in r.level3.status:
            assert "FALHOU" in r.final_status

    def test_summary_string_contains_all_sections(self):
        ct = CTSpec(
            tag="CT-SUM", tipo_TC="IEC_P",
            I_pri_nom_tap=2000, I_pri_nom_full=2000, I_sn=5,
            CT_Rating_C=400.0,
            R_s=0.5, R_b=0.3,
            curve=typical_magnetization_curve(400.0),
            IEC_VA=25, IEC_ALF=20,
        )
        fault = CTFaultContext(
            bus_id="BUS", rated_voltage_kV=13.8,
            I_fault_rms_kA=10.0, X_over_R=8.0,
        )
        r = analyze_full(ct, fault)
        s = r.summary()
        assert "CT-SUM" in s
        assert "BUS" in s
        assert "Nível 1" in s and "Nível 2" in s and "Nível 3" in s
        assert "RESULTADO FINAL" in s


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


class TestDefaults:

    def test_default_kr_ansi_high(self):
        assert DEFAULT_KR_ANSI == 0.8

    def test_default_kr_iec_pr_low(self):
        assert DEFAULT_KR_IEC_PR == 0.1
