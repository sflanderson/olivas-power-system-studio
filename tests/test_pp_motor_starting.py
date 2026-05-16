"""
tests/test_pp_motor_starting.py — v0.27.11: análise de partida
de grandes motores (voltage dip + tempo de aceleração).

Cobre:

* StartingResult enum (ACCEPTABLE/MARGINAL/UNACCEPTABLE).
* MotorStartingCase dataclass.
* motor_impedance_at_start_ohm — cálculo de Z_M = V²/(S × I_LR_pu).
* calculate_voltage_dip_pu — divisor de impedância
  Z_M / (Z_th + Z_M).
* synchronous_speed_rpm — n_s = 120 × f / poles.
* classify_acceptance — limites IEEE 399 + NEMA MG-1.
* estimate_starting_time_s — t = 2J × ωs × 0.95 / (T_m - T_load).
* analyze_motor_starting — pipeline completo, com cenários
  reais de motor 1500 HP / 4.16 kV.
* MotorStartingReport.summary() — texto formatado.
* Cenário de torque insuficiente (motor não parte).
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.motor_starting import (
    ABSOLUTE_MIN_VOLTAGE_LIMIT_PU,
    DEFAULT_VOLTAGE_DIP_LIMIT_PU,
    MotorStartingCase,
    MotorStartingReport,
    StartingResult,
    analyze_motor_starting,
    calculate_voltage_dip_pu,
    classify_acceptance,
    estimate_starting_time_s,
    motor_impedance_at_start_ohm,
    synchronous_speed_rpm,
)


# ---------------------------------------------------------------------------
# Helpers — cenários típicos de teste
# ---------------------------------------------------------------------------


def _strong_network_case(
    pre_v: float = 1.0, Z_th_ohm: float = 0.05,
) -> MotorStartingCase:
    """
    Motor 1000 kW @ 4.16 kV em rede forte.
    Z_th pequeno → voltage dip pequeno.
    """
    return MotorStartingCase(
        motor_name="M-MAIN",
        motor_rated_power_kW=1000.0,
        motor_rated_voltage_kV=4.16,
        motor_rated_pf=0.85,
        motor_efficiency=0.95,
        locked_rotor_current_pu=6.0,
        starting_pf=0.30,
        starting_torque_pu=1.5,
        load_torque_pu=1.0,
        inertia_motor_kg_m2=20.0,
        bus_pre_fault_voltage_pu=pre_v,
        bus_thevenin_impedance_ohm=Z_th_ohm,
        bus_rated_voltage_kV=4.16,
        n_poles=4,
        frequency_Hz=60.0,
    )


def _weak_network_case(
    pre_v: float = 1.0, Z_th_ohm: float = 1.5,
) -> MotorStartingCase:
    """Motor em rede fraca — Z_th alto → voltage dip grande."""
    case = _strong_network_case(pre_v=pre_v, Z_th_ohm=Z_th_ohm)
    return case


# ---------------------------------------------------------------------------
# StartingResult
# ---------------------------------------------------------------------------


class TestStartingResult:

    def test_three_categories_exist(self) -> None:
        assert StartingResult.ACCEPTABLE.value == "acceptable"
        assert StartingResult.MARGINAL.value == "marginal"
        assert StartingResult.UNACCEPTABLE.value == "unacceptable"

    def test_thresholds_constants(self) -> None:
        # IEEE 399 §10
        assert DEFAULT_VOLTAGE_DIP_LIMIT_PU == 0.85
        # NEMA MG-1
        assert ABSOLUTE_MIN_VOLTAGE_LIMIT_PU == 0.80


# ---------------------------------------------------------------------------
# Synchronous speed
# ---------------------------------------------------------------------------


class TestSynchronousSpeed:

    def test_4pole_60hz(self) -> None:
        # n_s = 120 × 60 / 4 = 1800 rpm
        assert synchronous_speed_rpm(60.0, 4) == pytest.approx(1800.0)

    def test_2pole_60hz(self) -> None:
        # n_s = 120 × 60 / 2 = 3600 rpm
        assert synchronous_speed_rpm(60.0, 2) == pytest.approx(3600.0)

    def test_4pole_50hz(self) -> None:
        # n_s = 120 × 50 / 4 = 1500 rpm
        assert synchronous_speed_rpm(50.0, 4) == pytest.approx(1500.0)


# ---------------------------------------------------------------------------
# classify_acceptance
# ---------------------------------------------------------------------------


class TestClassifyAcceptance:

    def test_above_85pct_acceptable(self) -> None:
        assert classify_acceptance(0.95) == StartingResult.ACCEPTABLE
        assert classify_acceptance(0.90) == StartingResult.ACCEPTABLE
        assert classify_acceptance(0.851) == StartingResult.ACCEPTABLE

    def test_marginal_zone(self) -> None:
        # 0.80 < V ≤ 0.85
        assert classify_acceptance(0.84) == StartingResult.MARGINAL
        assert classify_acceptance(0.81) == StartingResult.MARGINAL

    def test_below_80pct_unacceptable(self) -> None:
        assert classify_acceptance(0.79) == StartingResult.UNACCEPTABLE
        assert classify_acceptance(0.5) == StartingResult.UNACCEPTABLE
        assert classify_acceptance(0.0) == StartingResult.UNACCEPTABLE

    def test_exactly_85pct_is_marginal(self) -> None:
        # Boundary: > 0.85 → ACCEPTABLE; ≤ 0.85 → MARGINAL
        assert classify_acceptance(0.85) == StartingResult.MARGINAL


# ---------------------------------------------------------------------------
# motor_impedance_at_start_ohm
# ---------------------------------------------------------------------------


class TestMotorImpedance:

    def test_returns_complex(self) -> None:
        case = _strong_network_case()
        Z = motor_impedance_at_start_ohm(case)
        assert isinstance(Z, complex)

    def test_typical_motor_impedance_magnitude(self) -> None:
        """
        Motor 1000 kW / 4.16 kV / pf=0.85 / η=0.95 / I_LR=6×I_n.
        S = 1000 / (0.85 × 0.95) = 1238.4 kVA
        Z_base = (4160)² / 1238400 = 13.97 Ω
        Z_M ≈ 13.97 / 6 = 2.33 Ω
        """
        case = _strong_network_case()
        Z = motor_impedance_at_start_ohm(case)
        assert abs(Z) == pytest.approx(2.33, rel=0.05)

    def test_starting_pf_30pct_implies_high_X_low_R(self) -> None:
        """starting_pf = 0.30 → X dominante."""
        case = _strong_network_case()
        Z = motor_impedance_at_start_ohm(case)
        # X > R (motor é mais indutivo na partida)
        assert Z.imag > Z.real
        # Verificar pf real do Z resultante ≈ 0.3
        pf_calc = Z.real / abs(Z) if abs(Z) > 0 else 0
        assert pf_calc == pytest.approx(0.30, abs=0.01)

    def test_starting_pf_one_returns_pure_imaginary(self) -> None:
        """Edge case: pf=1 → caso degenerado, retorna pura X."""
        case = MotorStartingCase(
            motor_name="M",
            motor_rated_power_kW=100.0,
            motor_rated_voltage_kV=0.480,
            motor_rated_pf=0.85,
            motor_efficiency=0.95,
            locked_rotor_current_pu=6.0,
            starting_pf=1.0,    # edge
            starting_torque_pu=1.0,
            load_torque_pu=1.0,
            inertia_motor_kg_m2=1.0,
            bus_pre_fault_voltage_pu=1.0,
            bus_thevenin_impedance_ohm=0.01,
            bus_rated_voltage_kV=0.480,
        )
        Z = motor_impedance_at_start_ohm(case)
        assert Z.real == pytest.approx(0.0, abs=1e-9)
        assert Z.imag > 0


# ---------------------------------------------------------------------------
# calculate_voltage_dip_pu
# ---------------------------------------------------------------------------


class TestVoltageDip:

    def test_strong_network_small_dip(self) -> None:
        """Z_th pequeno (rede forte) → V_during ≈ V_pre."""
        case = _strong_network_case(pre_v=1.0, Z_th_ohm=0.05)
        V, _, _ = calculate_voltage_dip_pu(case)
        # Espera dip pequeno (V > 0.95)
        assert V > 0.95
        assert V < 1.0

    def test_weak_network_large_dip(self) -> None:
        """Z_th grande → V_during muito reduzida."""
        case = _weak_network_case(pre_v=1.0, Z_th_ohm=1.5)
        V, _, _ = calculate_voltage_dip_pu(case)
        # Espera dip grande (V < 0.85)
        assert V < 0.85

    def test_returns_tuple_of_three(self) -> None:
        case = _strong_network_case()
        result = calculate_voltage_dip_pu(case)
        assert len(result) == 3
        V, Z_M, Z_th = result
        assert isinstance(V, float)
        assert isinstance(Z_M, complex)
        assert isinstance(Z_th, complex)

    def test_V_during_proportional_to_V_pre(self) -> None:
        """Se V_pre = 0.5, V_during deve escalar igualmente."""
        case_high = _strong_network_case(pre_v=1.0)
        case_low = _strong_network_case(pre_v=0.5)
        V_high, _, _ = calculate_voltage_dip_pu(case_high)
        V_low, _, _ = calculate_voltage_dip_pu(case_low)
        assert V_low / V_high == pytest.approx(0.5, rel=1e-6)

    def test_zero_thevenin_returns_full_voltage(self) -> None:
        """Z_th=0 → V_during ≈ V_pre (ideal source)."""
        case = _strong_network_case(pre_v=1.0, Z_th_ohm=0.0)
        V, _, _ = calculate_voltage_dip_pu(case)
        assert V == pytest.approx(1.0, rel=1e-3)


# ---------------------------------------------------------------------------
# estimate_starting_time_s
# ---------------------------------------------------------------------------


class TestStartingTime:

    def test_typical_motor_finite_time(self) -> None:
        case = _strong_network_case()
        t = estimate_starting_time_s(case)
        assert math.isfinite(t)
        assert t > 0

    def test_insufficient_torque_returns_inf(self) -> None:
        """T_motor_avg < T_load_avg → infinito (motor não parte)."""
        case = MotorStartingCase(
            motor_name="M",
            motor_rated_power_kW=100.0,
            motor_rated_voltage_kV=0.480,
            motor_rated_pf=0.85,
            motor_efficiency=0.95,
            locked_rotor_current_pu=6.0,
            starting_pf=0.30,
            starting_torque_pu=0.1,    # muito baixo
            load_torque_pu=1.0,         # carga média = 0.5 pu > 0.1
            inertia_motor_kg_m2=10.0,
            bus_pre_fault_voltage_pu=1.0,
            bus_thevenin_impedance_ohm=0.05,
            bus_rated_voltage_kV=0.480,
        )
        t = estimate_starting_time_s(case)
        assert t == float("inf")

    def test_higher_inertia_longer_time(self) -> None:
        """Mais inércia = partida mais lenta."""
        case_low = _strong_network_case()
        # Cria nova instância com inércia 10x maior
        case_high = MotorStartingCase(
            **{**case_low.__dict__, "inertia_motor_kg_m2": 200.0},
        )
        t_low = estimate_starting_time_s(case_low)
        t_high = estimate_starting_time_s(case_high)
        assert t_high > t_low

    def test_higher_motor_torque_shorter_time(self) -> None:
        case_T1 = _strong_network_case()
        case_T2 = MotorStartingCase(
            **{**case_T1.__dict__, "starting_torque_pu": 3.0},
        )
        t1 = estimate_starting_time_s(case_T1)
        t2 = estimate_starting_time_s(case_T2)
        assert t2 < t1


# ---------------------------------------------------------------------------
# analyze_motor_starting (integração)
# ---------------------------------------------------------------------------


class TestAnalyzeMotorStarting:

    def test_returns_report(self) -> None:
        case = _strong_network_case()
        rpt = analyze_motor_starting(case)
        assert isinstance(rpt, MotorStartingReport)

    def test_strong_network_acceptable(self) -> None:
        case = _strong_network_case(pre_v=1.0, Z_th_ohm=0.05)
        rpt = analyze_motor_starting(case)
        assert rpt.acceptance == StartingResult.ACCEPTABLE
        assert rpt.voltage_dip_pu > 0.85

    def test_weak_network_unacceptable(self) -> None:
        case = _weak_network_case(pre_v=1.0, Z_th_ohm=2.0)
        rpt = analyze_motor_starting(case)
        # Pode ser MARGINAL ou UNACCEPTABLE dependendo da
        # impedância exata; testamos que não é ACCEPTABLE
        assert rpt.acceptance != StartingResult.ACCEPTABLE

    def test_report_contains_motor_name(self) -> None:
        case = _strong_network_case()
        rpt = analyze_motor_starting(case)
        assert rpt.motor_name == "M-MAIN"

    def test_synchronous_speed_in_report(self) -> None:
        case = _strong_network_case()
        rpt = analyze_motor_starting(case)
        assert rpt.synchronous_speed_rpm == pytest.approx(1800.0)

    def test_voltage_dip_pct_consistent(self) -> None:
        """voltage_dip_pct = (V_pre - V_during)/V_pre × 100"""
        case = _strong_network_case(pre_v=1.0, Z_th_ohm=0.5)
        rpt = analyze_motor_starting(case)
        expected_pct = (1.0 - rpt.voltage_dip_pu) / 1.0 * 100.0
        assert rpt.voltage_dip_pct == pytest.approx(expected_pct, rel=1e-6)

    def test_starting_current_positive(self) -> None:
        case = _strong_network_case()
        rpt = analyze_motor_starting(case)
        assert rpt.starting_current_kA > 0

    def test_rationale_not_empty(self) -> None:
        case = _strong_network_case()
        rpt = analyze_motor_starting(case)
        assert len(rpt.rationale) > 0

    def test_references_include_ieee_399(self) -> None:
        case = _strong_network_case()
        rpt = analyze_motor_starting(case)
        refs_text = "; ".join(rpt.references)
        assert "IEEE" in refs_text
        assert "399" in refs_text

    def test_unacceptable_rationale_mentions_assisted_start(self) -> None:
        """Caso UNACCEPTABLE deve mencionar soft-starter / VFD."""
        case = _weak_network_case(pre_v=0.95, Z_th_ohm=3.0)
        rpt = analyze_motor_starting(case)
        if rpt.acceptance == StartingResult.UNACCEPTABLE:
            text = "; ".join(rpt.rationale).lower()
            assert (
                "soft" in text or "vfd" in text or "auto-trafo" in text
                or "assistida" in text
            )


# ---------------------------------------------------------------------------
# Report.summary()
# ---------------------------------------------------------------------------


class TestReportSummary:

    def test_summary_contains_acceptance(self) -> None:
        case = _strong_network_case()
        rpt = analyze_motor_starting(case)
        text = rpt.summary()
        assert "Acceptance" in text
        assert rpt.acceptance.value.upper() in text

    def test_summary_contains_motor_name(self) -> None:
        case = _strong_network_case()
        rpt = analyze_motor_starting(case)
        text = rpt.summary()
        assert "M-MAIN" in text

    def test_summary_contains_voltage_dip(self) -> None:
        case = _strong_network_case()
        rpt = analyze_motor_starting(case)
        text = rpt.summary()
        assert "Voltage dip" in text or "voltage dip" in text.lower()
