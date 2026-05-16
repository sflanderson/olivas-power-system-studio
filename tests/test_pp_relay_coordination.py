"""
tests/test_pp_relay_coordination.py — v0.27.4: coordenação
seletiva entre relés de proteção.

Cobre:

* IEC 60255-151 TC curves (SI, VI, EI, LTI) — fórmula
  t = TMS·k/(M^α-1).
* IEEE C37.112 TC curves (Mod Inv, VI, EI, etc.) — fórmula
  t = TD·(k/(M^α-1)+β)/7.
* TcCurveSetting polimórfico — IEC, IEEE, definite-time.
* ANSI Device Numbers registry (catálogo de funções de proteção).
* Relay Models registry (SEL-751, ABB REF615/RET615,
  Schneider P3U10/P3U30) com cross-check de funções e ranges.
* RelayInstance + validação vs RelayModel.
* CoordinationCheck + CoordinationReport (par upstream-down).
* Cenário realista IEEE 242 §15: cadeia main → feeder com
  margens em múltiplas correntes.
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.relay_coordination import (
    CoordinationCheck, CoordinationMargin, CoordinationReport,
    RelayInstance, quick_pair_check, validate_coordination_chain,
    validate_relay_instance,
)
from app.standards.ansi_devices import (
    ANSI_DEVICE_FUNCTIONS, all_function_numbers,
    get_function, search_by_keyword,
)
from app.standards.iec60255 import (
    CurveStandard, IecCurveType, IeeeCurveType,
    IEC_CURVE_COEFFICIENTS, IEEE_CURVE_COEFFICIENTS,
    TcCurveSetting,
    make_definite_time, make_iec_ei, make_iec_si, make_iec_vi,
    make_ieee_ei, make_ieee_vi, make_instantaneous,
    operate_time_definite_time_s,
    operate_time_iec_s, operate_time_ieee_s,
)
from app.standards.relay_models import (
    ABB_REF615, ABB_RET615,
    RELAY_MODELS_REGISTRY, RelayModel,
    SCHNEIDER_P3U10, SCHNEIDER_P3U30,
    SEL_751,
    get_model, list_models, list_models_by_application,
    list_models_supporting_function,
    supports_curve_standard, supports_function,
    validate_pickup_per_in, validate_time_dial, validate_tms,
)


# ---------------------------------------------------------------------------
# IEC 60255-151 TC curves
# ---------------------------------------------------------------------------


class TestIecCurves:
    def test_si_coefficients(self):
        coef = IEC_CURVE_COEFFICIENTS[IecCurveType.STANDARD_INVERSE]
        assert coef.k == 0.14
        assert coef.alpha == 0.02

    def test_vi_coefficients(self):
        coef = IEC_CURVE_COEFFICIENTS[IecCurveType.VERY_INVERSE]
        assert coef.k == 13.5
        assert coef.alpha == 1.0

    def test_ei_coefficients(self):
        coef = IEC_CURVE_COEFFICIENTS[IecCurveType.EXTREMELY_INVERSE]
        assert coef.k == 80.0
        assert coef.alpha == 2.0

    def test_lti_coefficients(self):
        coef = IEC_CURVE_COEFFICIENTS[IecCurveType.LONG_TIME_INVERSE]
        assert coef.k == 120.0
        assert coef.alpha == 1.0

    def test_si_at_M2_TMS1(self):
        """IEC SI: t = 1·0.14/(2^0.02-1) ≈ 10.03 s."""
        t = operate_time_iec_s(
            current_A=200, pickup_A=100, tms=1.0,
            curve=IecCurveType.STANDARD_INVERSE,
        )
        assert t == pytest.approx(10.03, abs=0.05)

    def test_vi_at_M5_TMS05(self):
        """VI: t = 0.5·13.5/(5-1) = 1.6875 s."""
        t = operate_time_iec_s(
            current_A=500, pickup_A=100, tms=0.5,
            curve=IecCurveType.VERY_INVERSE,
        )
        assert t == pytest.approx(1.6875, abs=0.001)

    def test_ei_at_M10_TMS05(self):
        """EI: t = 0.5·80/(100-1) ≈ 0.404 s."""
        t = operate_time_iec_s(
            current_A=1000, pickup_A=100, tms=0.5,
            curve=IecCurveType.EXTREMELY_INVERSE,
        )
        assert t == pytest.approx(0.404, abs=0.005)

    def test_below_pickup_returns_inf(self):
        t = operate_time_iec_s(
            50, 100, 0.5, IecCurveType.STANDARD_INVERSE,
        )
        assert t == float("inf")

    def test_at_pickup_returns_inf(self):
        t = operate_time_iec_s(
            100, 100, 0.5, IecCurveType.STANDARD_INVERSE,
        )
        assert t == float("inf")

    def test_invalid_tms_rejected(self):
        with pytest.raises(ValueError, match="tms"):
            operate_time_iec_s(
                200, 100, 2.0, IecCurveType.STANDARD_INVERSE,
            )

    def test_zero_pickup_rejected(self):
        with pytest.raises(ValueError):
            operate_time_iec_s(
                200, 0, 0.5, IecCurveType.STANDARD_INVERSE,
            )


# ---------------------------------------------------------------------------
# IEEE C37.112 TC curves
# ---------------------------------------------------------------------------


class TestIeeeCurves:
    def test_moderately_inverse_coefs(self):
        c = IEEE_CURVE_COEFFICIENTS[IeeeCurveType.MODERATELY_INVERSE]
        assert c.k == 0.0515
        assert c.alpha == 0.02
        assert c.beta == 0.114

    def test_very_inverse_coefs(self):
        c = IEEE_CURVE_COEFFICIENTS[IeeeCurveType.VERY_INVERSE]
        assert c.k == 19.61
        assert c.alpha == 2.0
        assert c.beta == 0.491

    def test_extremely_inverse_coefs(self):
        c = IEEE_CURVE_COEFFICIENTS[IeeeCurveType.EXTREMELY_INVERSE]
        assert c.k == 28.2
        assert c.alpha == 2.0

    def test_vi_at_M5_TD5(self):
        """IEEE VI: t = 5·(19.61/(25-1)+0.491)/7 = 5·1.308/7 ≈ 0.934 s."""
        t = operate_time_ieee_s(
            current_A=500, pickup_A=100, time_dial=5.0,
            curve=IeeeCurveType.VERY_INVERSE,
        )
        # 5·(19.61/24 + 0.491)/7
        expected = 5.0 * (19.61 / 24.0 + 0.491) / 7.0
        assert t == pytest.approx(expected, abs=0.005)

    def test_below_pickup_inf(self):
        t = operate_time_ieee_s(
            50, 100, 5.0, IeeeCurveType.VERY_INVERSE,
        )
        assert t == float("inf")

    def test_invalid_time_dial(self):
        with pytest.raises(ValueError, match="time_dial"):
            operate_time_ieee_s(
                200, 100, 20.0, IeeeCurveType.VERY_INVERSE,
            )


# ---------------------------------------------------------------------------
# Definite Time
# ---------------------------------------------------------------------------


class TestDefiniteTime:
    def test_above_pickup(self):
        assert operate_time_definite_time_s(200, 100, 0.5) == 0.5

    def test_below_pickup(self):
        assert operate_time_definite_time_s(50, 100, 0.5) == float("inf")

    def test_at_pickup_below(self):
        """Strict > comparison: I = Is é considerado abaixo."""
        assert operate_time_definite_time_s(100, 100, 0.5) == float("inf")

    def test_negative_delay_rejected(self):
        with pytest.raises(ValueError):
            operate_time_definite_time_s(200, 100, -0.5)


# ---------------------------------------------------------------------------
# TcCurveSetting (polimórfico)
# ---------------------------------------------------------------------------


class TestTcCurveSetting:
    def test_iec_si_helper(self):
        tc = make_iec_si(pickup_A=100, tms=0.5)
        assert tc.standard == CurveStandard.IEC
        assert tc.iec_curve == IecCurveType.STANDARD_INVERSE
        t = tc.operate_time_s(500)
        assert math.isfinite(t)
        assert t > 0

    def test_iec_vi_helper(self):
        tc = make_iec_vi(100, 0.5)
        assert tc.iec_curve == IecCurveType.VERY_INVERSE

    def test_iec_ei_helper(self):
        tc = make_iec_ei(100, 0.5)
        assert tc.iec_curve == IecCurveType.EXTREMELY_INVERSE

    def test_ieee_vi_helper(self):
        tc = make_ieee_vi(100, 5.0)
        assert tc.standard == CurveStandard.IEEE

    def test_definite_time_helper(self):
        tc = make_definite_time(100, 0.3)
        assert tc.standard == CurveStandard.DEFINITE_TIME
        assert tc.operate_time_s(200) == 0.3

    def test_instantaneous_helper(self):
        """50 instantâneo = DT com delay=0."""
        tc = make_instantaneous(100)
        assert tc.operate_time_s(200) == 0.0

    def test_description(self):
        tc = make_iec_si(100, 0.5)
        d = tc.description()
        assert "IEC" in d and "SI" in d

    def test_description_ieee(self):
        tc = make_ieee_ei(100, 5.0)
        d = tc.description()
        assert "IEEE" in d and "U3" in d


# ---------------------------------------------------------------------------
# ANSI Device Numbers
# ---------------------------------------------------------------------------


class TestAnsiDevices:
    def test_50_overcurrent(self):
        f = get_function("50")
        assert f is not None
        assert "instantânea" in f.name_pt.lower() or "instant" in f.name_en.lower()

    def test_51_time_overcurrent(self):
        f = get_function("51")
        assert f is not None
        assert "temporizada" in f.name_pt.lower() or "delay" in f.name_en.lower()

    def test_50N_neutral(self):
        f = get_function("50N")
        assert f is not None
        assert "neutro" in f.name_pt.lower()

    def test_87_differential(self):
        f = get_function("87")
        assert f is not None

    def test_unknown_returns_none(self):
        assert get_function("XX") is None

    def test_case_insensitive(self):
        assert get_function("50n") == get_function("50N")

    def test_all_function_numbers_returns_tuple(self):
        nums = all_function_numbers()
        assert "50" in nums
        assert "51" in nums
        assert "87" in nums
        assert "27" in nums

    def test_search_by_keyword_motor(self):
        results = search_by_keyword("motor")
        assert len(results) > 0
        nums = [r.number for r in results]
        assert any(n.startswith("4") or n.startswith("5") for n in nums)


# ---------------------------------------------------------------------------
# Relay Models registry
# ---------------------------------------------------------------------------


class TestRelayModelsRegistry:
    def test_sel_751_present(self):
        assert get_model("SEL-751") is not None

    def test_abb_ref615_present(self):
        assert get_model("ABB-REF615") is not None

    def test_schneider_p3u30_present(self):
        assert get_model("Schneider-P3U30") is not None

    def test_unknown_model_returns_none(self):
        assert get_model("INVALID-99X") is None

    def test_list_models(self):
        ids = list_models()
        assert "SEL-751" in ids
        assert "Schneider-P3U30" in ids

    def test_p3u30_supports_50_51_67(self):
        m = SCHNEIDER_P3U30
        assert supports_function(m, "50")
        assert supports_function(m, "51")
        assert supports_function(m, "67")
        assert supports_function(m, "67N")
        assert supports_function(m, "67NI")
        assert supports_function(m, "78V")

    def test_p3u10_subset_of_p3u30(self):
        """P3U10 é subset reduzido."""
        for func in SCHNEIDER_P3U10.ansi_functions:
            assert supports_function(SCHNEIDER_P3U30, func), (
                f"{func} suportado em P3U10 mas não em P3U30"
            )

    def test_ret615_has_87T_and_REF(self):
        assert supports_function(ABB_RET615, "87T")
        assert supports_function(ABB_RET615, "64REF")

    def test_sel_751_supports_iec_and_ieee(self):
        assert supports_curve_standard(SEL_751, CurveStandard.IEC)
        assert supports_curve_standard(SEL_751, CurveStandard.IEEE)

    def test_models_supporting_67(self):
        m_list = list_models_supporting_function("67")
        # Pelo menos SEL-751, P3U30 e ABB-REF615
        ids = [m.model for m in m_list]
        assert "SEL-751" in ids
        assert "P3U30" in ids
        assert "REF615" in ids

    def test_models_by_feeder_application(self):
        feeders = list_models_by_application("feeder")
        ids = [m.model for m in feeders]
        # Universal (P3U30) também conta como feeder
        assert "SEL-751" in ids or "P3U30" in ids

    def test_validate_pickup_per_in_sel(self):
        # SEL-751: pickup range 0.5 → 16 × In
        assert validate_pickup_per_in(SEL_751, 1.0) is True
        assert validate_pickup_per_in(SEL_751, 16.0) is True
        assert validate_pickup_per_in(SEL_751, 0.3) is False
        assert validate_pickup_per_in(SEL_751, 20.0) is False

    def test_validate_tms_in_range(self):
        # IEC TMS: 0.05 → 1.0
        assert validate_tms(SEL_751, 0.5) is True
        assert validate_tms(SEL_751, 0.04) is False
        assert validate_tms(SEL_751, 1.5) is False

    def test_validate_time_dial(self):
        assert validate_time_dial(SEL_751, 5.0) is True
        assert validate_time_dial(SEL_751, 0.4) is False
        assert validate_time_dial(SEL_751, 16.0) is False


# ---------------------------------------------------------------------------
# RelayInstance + validation
# ---------------------------------------------------------------------------


class TestRelayInstance:
    def test_basic_instance(self):
        r = RelayInstance(
            name="51-MAIN", location="Main",
            device_function="51",
            tc_curve=make_iec_si(pickup_A=20.0, tms=0.5),
            relay_model="SEL-751",
            rated_current_A=5.0,
        )
        assert r.name == "51-MAIN"

    def test_validate_ok(self):
        r = RelayInstance(
            name="OK", location="Main",
            device_function="51",
            tc_curve=make_iec_si(pickup_A=10.0, tms=0.5),
            relay_model="SEL-751", rated_current_A=5.0,
        )
        # 10/5 = 2 pu — dentro do range 0.5-16 do SEL-751
        assert validate_relay_instance(r) == []

    def test_unsupported_function_warned(self):
        r = RelayInstance(
            name="Bad", location="X",
            device_function="21",  # 21 não suportado pelo SEL-751
            tc_curve=make_iec_si(50, 0.5),
            relay_model="SEL-751", rated_current_A=5.0,
        )
        errs = validate_relay_instance(r)
        assert any("21" in e for e in errs)

    def test_pickup_out_of_range_warned(self):
        r = RelayInstance(
            name="BadPickup", location="X",
            device_function="51",
            tc_curve=make_iec_si(pickup_A=200, tms=0.5),  # 40 pu
            relay_model="SEL-751", rated_current_A=5.0,
        )
        errs = validate_relay_instance(r)
        assert any("pickup" in e.lower() for e in errs)

    def test_unknown_model_warned(self):
        r = RelayInstance(
            name="X", location="Y", device_function="51",
            tc_curve=make_iec_si(50, 0.5),
            relay_model="GENERIC-XYZ-99",
        )
        errs = validate_relay_instance(r)
        assert any("registry" in e.lower() for e in errs)

    def test_no_model_no_validation(self):
        """relay_model=None → sem validação cross-check."""
        r = RelayInstance(
            name="Generic", location="Y", device_function="51",
            tc_curve=make_iec_si(50, 0.5),
            relay_model=None,
        )
        assert validate_relay_instance(r) == []

    def test_empty_name(self):
        r = RelayInstance(
            name="", location="X", device_function="51",
            tc_curve=make_iec_si(50, 0.5),
        )
        errs = validate_relay_instance(r)
        assert any("name" in e for e in errs)


# ---------------------------------------------------------------------------
# CoordinationCheck
# ---------------------------------------------------------------------------


class TestCoordinationCheck:
    def _make_pair(self):
        upstream = RelayInstance(
            name="UP", location="Main 13.8 kV",
            device_function="51",
            tc_curve=make_iec_si(pickup_A=20.0, tms=0.5),  # mais lento
            relay_model="SEL-751", rated_current_A=5.0,
        )
        downstream = RelayInstance(
            name="DN", location="Feeder F1",
            device_function="51",
            tc_curve=make_iec_si(pickup_A=10.0, tms=0.15),  # mais rápido
            relay_model="ABB-REF615", rated_current_A=5.0,
        )
        return upstream, downstream

    def test_basic_check(self):
        up, dn = self._make_pair()
        check = CoordinationCheck(upstream=up, downstream=dn)
        m = check.margin_at_current(100)
        assert m.t_downstream_s < m.t_upstream_s
        assert m.margin_s > 0

    def test_run_default_currents(self):
        up, dn = self._make_pair()
        check = CoordinationCheck(upstream=up, downstream=dn)
        report = check.run()
        # default = 2×, 5×, 10× pickup downstream (10 A) = [20, 50, 100]
        assert len(report.margins) == 3
        assert report.margins[0].test_current_A == 20.0
        assert report.margins[1].test_current_A == 50.0
        assert report.margins[2].test_current_A == 100.0

    def test_run_custom_currents(self):
        up, dn = self._make_pair()
        check = CoordinationCheck(
            upstream=up, downstream=dn, margin_required_s=0.30,
        )
        report = check.run(test_currents_A=[50, 100, 500])
        assert len(report.margins) == 3

    def test_coordinated_when_margin_high(self):
        up, dn = self._make_pair()
        check = CoordinationCheck(upstream=up, downstream=dn,
                                   margin_required_s=0.20)
        # Em correntes altas, both rápidos mas dn ainda mais rápido
        report = check.run(test_currents_A=[500, 1000])
        assert report.all_coordinated is True

    def test_uncoordinated_when_margin_too_low(self):
        """Curvas idênticas → margem zero, FAIL."""
        same_curve = make_iec_si(pickup_A=10, tms=0.3)
        up = RelayInstance(
            name="A", location="X", device_function="51",
            tc_curve=same_curve,
            rated_current_A=5.0,
        )
        dn = RelayInstance(
            name="B", location="Y", device_function="51",
            tc_curve=same_curve,
            rated_current_A=5.0,
        )
        check = CoordinationCheck(upstream=up, downstream=dn)
        report = check.run(test_currents_A=[100])
        assert report.all_coordinated is False

    def test_worst_margin(self):
        up, dn = self._make_pair()
        check = CoordinationCheck(upstream=up, downstream=dn)
        report = check.run(test_currents_A=[20, 100, 1000])
        worst = report.worst_margin
        assert worst is not None

    def test_summary_format(self):
        up, dn = self._make_pair()
        check = CoordinationCheck(upstream=up, downstream=dn)
        report = check.run(test_currents_A=[100, 500])
        s = report.summary()
        assert "Coordination Report" in s
        assert "UP" in s and "DN" in s
        assert "Margin Points" in s


# ---------------------------------------------------------------------------
# Helpers de alto nível
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_quick_pair_check(self):
        up = RelayInstance(
            name="UP", location="X", device_function="51",
            tc_curve=make_iec_si(20, 0.5),
            rated_current_A=5.0,
        )
        dn = RelayInstance(
            name="DN", location="Y", device_function="51",
            tc_curve=make_iec_si(10, 0.15),
            rated_current_A=5.0,
        )
        # Falta de 1 kA = 1000 A
        report = quick_pair_check(up, dn, fault_current_kA=1.0)
        assert len(report.margins) == 1
        assert report.margins[0].test_current_A == 1000.0

    def test_validate_chain_3_relays(self):
        r1 = RelayInstance(
            name="R1-MAIN", location="Main", device_function="51",
            tc_curve=make_iec_si(30, 0.6),
            rated_current_A=5.0,
        )
        r2 = RelayInstance(
            name="R2-MID", location="Mid", device_function="51",
            tc_curve=make_iec_si(20, 0.4),
            rated_current_A=5.0,
        )
        r3 = RelayInstance(
            name="R3-LOAD", location="Load", device_function="51",
            tc_curve=make_iec_si(10, 0.15),
            rated_current_A=5.0,
        )
        reports = validate_coordination_chain(
            relays=[r1, r2, r3],
            fault_currents_A=[500, 1000],
        )
        assert len(reports) == 2  # 3 relés = 2 pares
        # Cada par deve estar coordenado com TMS escalonado
        for r in reports:
            assert r.all_coordinated

    def test_chain_too_short_raises(self):
        r1 = RelayInstance(
            name="R1", location="X", device_function="51",
            tc_curve=make_iec_si(10, 0.3),
        )
        with pytest.raises(ValueError, match="2"):
            validate_coordination_chain(relays=[r1], fault_currents_A=[100])


# ---------------------------------------------------------------------------
# Cenário realista IEEE 242 §15
# ---------------------------------------------------------------------------


class TestRealisticScenarioIEEE242:
    """
    Cenário IEEE 242 Buff Book §15 (industrial coordination):

    13.8 kV main → 4.16 kV secondary → 480 V tertiary → motor.

    Cadeia típica de 3-4 relés. Aqui simplificamos para 3 níveis.
    """

    def test_three_level_coordination(self):
        """
        IEEE 242 §15: TMS escalonado garante coordenação.

        Standard Inverse (SI) dá curvas mais "abertas" que VI/EI
        em correntes altas — facilita coordenação real.
        """
        # Nível 1: Main 13.8 kV — TMS 1.0 (mais lento)
        main = RelayInstance(
            name="51-MAIN-13.8", location="Main 13.8 kV",
            device_function="51",
            tc_curve=make_iec_si(pickup_A=20, tms=1.0),
            relay_model="SEL-751", rated_current_A=5.0,
        )
        # Nível 2: TR secundário — TMS 0.5
        sec = RelayInstance(
            name="51-SEC-4.16", location="TR Sec 4.16 kV",
            device_function="51",
            tc_curve=make_iec_si(pickup_A=15, tms=0.5),
            relay_model="ABB-REF615", rated_current_A=5.0,
        )
        # Nível 3: Motor — TMS 0.1
        feeder = RelayInstance(
            name="51-MOTOR", location="Motor feeder",
            device_function="51",
            tc_curve=make_iec_si(pickup_A=10, tms=0.1),
            relay_model="Schneider-P3U30", rated_current_A=5.0,
        )

        reports = validate_coordination_chain(
            relays=[main, sec, feeder],
            fault_currents_A=[100, 500, 1000],   # médias
            margin_min_s=0.20,
        )
        assert len(reports) == 2

        # Verifica que coordenação OK em correntes médias (100A)
        for r in reports:
            low_I_margin = next(
                m for m in r.margins if m.test_current_A == 100
            )
            assert low_I_margin.coordinated, (
                f"Falhou coordenação @ 100A entre "
                f"{r.upstream.name} e {r.downstream.name}: "
                f"Δt={low_I_margin.margin_s:.3f}s"
            )

    def test_main_uses_iec_si_feeder_uses_ieee_vi(self):
        """Mistura de standards é permitida (não exige mesma família)."""
        main = RelayInstance(
            name="MAIN", location="X",
            device_function="51",
            tc_curve=make_iec_si(15, 0.5),
            relay_model="SEL-751", rated_current_A=5.0,
        )
        feeder = RelayInstance(
            name="FEEDER", location="Y",
            device_function="51",
            tc_curve=make_ieee_vi(10, 3.0),
            relay_model="SEL-751", rated_current_A=5.0,
        )
        check = CoordinationCheck(upstream=main, downstream=feeder)
        report = check.run(test_currents_A=[100, 500, 1000])
        # Não verificamos all_coordinated (depende dos params),
        # mas o check deve rodar sem erro
        assert isinstance(report, CoordinationReport)
        assert len(report.margins) == 3
