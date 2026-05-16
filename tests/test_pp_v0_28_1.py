"""
tests/test_pp_v0_28_1.py — v0.28.1: endurecimentos P3.

Cobre:

* P3.1: motor_starting com Z_th complex (sem heurística 90%).
* P3.2: LoadType enum (CONSTANT/LINEAR/QUADRATIC/CUBIC).
* P3.3: relay_coordination electromechanical flag.
* P3.5/6: trt_analyzer slope negativo + filtro digital.
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.motor_starting import (
    LoadType,
    MotorStartingCase,
    average_load_torque_factor,
    calculate_voltage_dip_pu,
    estimate_starting_time_s,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_case(
    load_type: LoadType = LoadType.CONSTANT,
    Z_th_complex: complex | None = None,
) -> MotorStartingCase:
    return MotorStartingCase(
        motor_name="M1",
        motor_rated_power_kW=1000.0,
        motor_rated_voltage_kV=4.16,
        motor_rated_pf=0.85,
        motor_efficiency=0.95,
        locked_rotor_current_pu=6.0,
        starting_pf=0.30,
        starting_torque_pu=1.5,
        load_torque_pu=1.0,
        inertia_motor_kg_m2=20.0,
        bus_pre_fault_voltage_pu=1.0,
        bus_thevenin_impedance_ohm=0.5,
        bus_thevenin_impedance_complex=Z_th_complex,
        bus_rated_voltage_kV=4.16,
        load_type=load_type,
    )


# ---------------------------------------------------------------------------
# P3.2 — LoadType
# ---------------------------------------------------------------------------


class TestLoadType:

    def test_four_types(self):
        assert LoadType.CONSTANT.value == "constant"
        assert LoadType.LINEAR.value == "linear"
        assert LoadType.QUADRATIC.value == "quadratic"
        assert LoadType.CUBIC.value == "cubic"

    def test_average_factor_constant(self):
        assert average_load_torque_factor(LoadType.CONSTANT) == 1.0

    def test_average_factor_linear(self):
        assert average_load_torque_factor(LoadType.LINEAR) == 0.5

    def test_average_factor_quadratic(self):
        assert average_load_torque_factor(LoadType.QUADRATIC) == pytest.approx(
            1.0 / 3.0, rel=1e-6,
        )

    def test_average_factor_cubic(self):
        assert average_load_torque_factor(LoadType.CUBIC) == 0.25


class TestStartingTimeWithLoadType:

    def test_quadratic_faster_than_constant(self):
        """
        Ventilador (quadratic) acelera mais rápido que carga
        constante porque T_load_avg é menor.
        """
        case_const = _base_case(load_type=LoadType.CONSTANT)
        case_quad = _base_case(load_type=LoadType.QUADRATIC)
        t_const = estimate_starting_time_s(case_const)
        t_quad = estimate_starting_time_s(case_quad)
        assert t_quad < t_const

    def test_cubic_fastest(self):
        case_cubic = _base_case(load_type=LoadType.CUBIC)
        case_const = _base_case(load_type=LoadType.CONSTANT)
        t_cubic = estimate_starting_time_s(case_cubic)
        t_const = estimate_starting_time_s(case_const)
        assert t_cubic < t_const

    def test_constant_default(self):
        """Sem load_type explícito, default é CONSTANT (conservador)."""
        case = MotorStartingCase(
            motor_name="M",
            motor_rated_power_kW=1000.0,
            motor_rated_voltage_kV=4.16,
            motor_rated_pf=0.85,
            motor_efficiency=0.95,
            locked_rotor_current_pu=6.0,
            starting_pf=0.30,
            starting_torque_pu=1.5,
            load_torque_pu=1.0,
            inertia_motor_kg_m2=20.0,
            bus_pre_fault_voltage_pu=1.0,
            bus_thevenin_impedance_ohm=0.5,
            bus_rated_voltage_kV=4.16,
        )
        assert case.load_type == LoadType.CONSTANT


# ---------------------------------------------------------------------------
# P3.1 — Z_th complex
# ---------------------------------------------------------------------------


class TestZthComplex:

    def test_complex_used_when_provided(self):
        """Quando Z_th complex fornecido, ignora heurística."""
        Z_th = complex(0.05, 0.50)   # R/X = 0.10 (10% R)
        case = _base_case(Z_th_complex=Z_th)
        V, _, Z_th_used = calculate_voltage_dip_pu(case)
        # Z_th_used deve ser exatamente o complex passado
        assert Z_th_used == Z_th

    def test_heuristic_fallback_when_None(self):
        """Sem Z_th complex, usa heurística 90% indutivo do MVP."""
        case = _base_case(Z_th_complex=None)
        _, _, Z_th_used = calculate_voltage_dip_pu(case)
        # Heurística: 0.1·|Z| + j·0.9·|Z| = 0.05 + j·0.45
        assert Z_th_used.real == pytest.approx(0.05, rel=1e-6)
        assert Z_th_used.imag == pytest.approx(0.45, rel=1e-6)

    def test_resistive_grid_different_dip(self):
        """Z_th muito resistivo dá dip diferente da heurística."""
        Z_resistive = complex(0.45, 0.05)   # 90% resistivo
        Z_inductive = complex(0.05, 0.45)   # 90% indutivo

        case_R = _base_case(Z_th_complex=Z_resistive)
        case_X = _base_case(Z_th_complex=Z_inductive)

        V_R, _, _ = calculate_voltage_dip_pu(case_R)
        V_X, _, _ = calculate_voltage_dip_pu(case_X)

        # Dip diferente para R vs X domain
        assert V_R != pytest.approx(V_X, rel=1e-3)


# ---------------------------------------------------------------------------
# P3.3 — relay_coordination electromechanical flag
# ---------------------------------------------------------------------------


class TestElectromechanicalFlag:

    def test_default_digital_margin(self):
        """Sem flag, margem default = 0.20s."""
        from app.postprocessor.relay_coordination import (
            CoordinationCheck, MARGIN_DIGITAL_S,
        )
        from app.standards.iec60255 import (
            CurveStandard, IecCurveType, TcCurveSetting,
        )
        from app.postprocessor.relay_coordination import RelayInstance
        from app.standards.relay_models import SEL_751

        tc_dn = TcCurveSetting(
            standard=CurveStandard.IEC,
            iec_curve=IecCurveType.STANDARD_INVERSE,
            pickup_A=100.0, tms=0.10,
        )
        tc_up = TcCurveSetting(
            standard=CurveStandard.IEC,
            iec_curve=IecCurveType.STANDARD_INVERSE,
            pickup_A=200.0, tms=0.30,
        )
        dn = RelayInstance(
            name="DN", location="loadside", device_function="51",
            tc_curve=tc_dn,
        )
        up = RelayInstance(
            name="UP", location="lineside", device_function="51",
            tc_curve=tc_up,
        )
        chk = CoordinationCheck(upstream=up, downstream=dn)
        assert chk.margin_required_s == MARGIN_DIGITAL_S

    def test_electromechanical_flag_raises_to_30s(self):
        from app.postprocessor.relay_coordination import (
            CoordinationCheck, MARGIN_ELECTROMECHANICAL_S,
        )
        from app.standards.iec60255 import (
            CurveStandard, IecCurveType, TcCurveSetting,
        )
        from app.postprocessor.relay_coordination import RelayInstance
        from app.standards.relay_models import SEL_751

        tc_dn = TcCurveSetting(
            standard=CurveStandard.IEC,
            iec_curve=IecCurveType.STANDARD_INVERSE,
            pickup_A=100.0, tms=0.10,
        )
        tc_up = TcCurveSetting(
            standard=CurveStandard.IEC,
            iec_curve=IecCurveType.STANDARD_INVERSE,
            pickup_A=200.0, tms=0.30,
        )
        dn = RelayInstance(
            name="DN", location="loadside", device_function="51",
            tc_curve=tc_dn,
        )
        up = RelayInstance(
            name="UP", location="lineside", device_function="51",
            tc_curve=tc_up,
        )
        chk = CoordinationCheck(
            upstream=up, downstream=dn, electromechanical=True,
        )
        assert chk.margin_required_s == MARGIN_ELECTROMECHANICAL_S
        assert chk.margin_required_s == 0.30

    def test_explicit_margin_overrides_flag(self):
        """Se usuário forneceu margin_required_s != default, respeita."""
        from app.postprocessor.relay_coordination import CoordinationCheck
        from app.standards.iec60255 import (
            CurveStandard, IecCurveType, TcCurveSetting,
        )
        from app.postprocessor.relay_coordination import RelayInstance
        from app.standards.relay_models import SEL_751

        tc = TcCurveSetting(
            standard=CurveStandard.IEC,
            iec_curve=IecCurveType.STANDARD_INVERSE,
            pickup_A=100.0, tms=0.10,
        )
        dn = RelayInstance(
            name="DN", location="loadside", device_function="51",
            tc_curve=tc,
        )
        up = RelayInstance(
            name="UP", location="lineside", device_function="51",
            tc_curve=tc,
        )
        chk = CoordinationCheck(
            upstream=up, downstream=dn,
            margin_required_s=0.40,  # explícito
            electromechanical=True,
        )
        # Override do usuário não foi default → preservado
        assert chk.margin_required_s == 0.40


# ---------------------------------------------------------------------------
# P3.5/6 — trt_analyzer slope negativo + filtro
# ---------------------------------------------------------------------------


class TestTrtSlopeAndFilter:

    def test_negative_slope_considered(self):
        """RRRV com consider_negative_slope=True captura slope negativo."""
        from app.postprocessor.trt_analyzer import _compute_max_rrrv

        # Forma de onda: sobe rapidamente, depois cai LENTO.
        # Slope negativo deve ser considerado.
        samples = [
            (0.0, 0.0),
            (1.0, 100.0),    # +100 kV/μs
            (2.0, 50.0),     # -50 kV/μs (oscilação)
            (3.0, 0.0),
        ]
        rrrv_pos = _compute_max_rrrv(
            samples, consider_negative_slope=False,
            filter_window=1,
        )
        rrrv_abs = _compute_max_rrrv(
            samples, consider_negative_slope=True,
            filter_window=1,
        )
        # Ambos pegam +100 (maior em módulo)
        assert rrrv_pos == 100.0
        assert rrrv_abs == 100.0

    def test_negative_slope_dominates_when_larger(self):
        """Se |slope_neg| > slope_pos, |negativo| ganha."""
        from app.postprocessor.trt_analyzer import _compute_max_rrrv

        samples = [
            (0.0, 0.0),
            (1.0, 50.0),       # +50
            (2.0, -100.0),     # -150 (slope neg dominante)
        ]
        rrrv_pos = _compute_max_rrrv(
            samples, consider_negative_slope=False, filter_window=1,
        )
        rrrv_abs = _compute_max_rrrv(
            samples, consider_negative_slope=True, filter_window=1,
        )
        # Apenas positivo: 50; Considerando negativo: 150
        assert rrrv_pos == 50.0
        assert rrrv_abs == 150.0

    def test_filter_attenuates_noise(self):
        """Filtro de média móvel reduz ruído."""
        from app.postprocessor.trt_analyzer import _compute_max_rrrv

        # Sinal com ruído alto
        samples = [
            (0.0, 0.0), (1.0, 100.0), (2.0, 50.0),  # ruído
            (3.0, 105.0), (4.0, 55.0), (5.0, 110.0),
        ]
        # Sem filtro: pega oscilação alta (slope ±50)
        rrrv_unfiltered = _compute_max_rrrv(
            samples, filter_window=1, consider_negative_slope=True,
        )
        # Com filtro window=3: suaviza
        rrrv_filtered = _compute_max_rrrv(
            samples, filter_window=3, consider_negative_slope=True,
        )
        assert rrrv_filtered < rrrv_unfiltered

    def test_window_us_restricts_calculation(self):
        """window_us limita análise temporalmente."""
        from app.postprocessor.trt_analyzer import _compute_max_rrrv

        samples = [
            (0.0, 0.0),
            (5.0, 100.0),     # slope 20 (dentro da janela)
            (50.0, 5000.0),   # slope HUGE (fora da janela)
        ]
        rrrv_full = _compute_max_rrrv(
            samples, filter_window=1, window_us=None,
        )
        rrrv_short = _compute_max_rrrv(
            samples, filter_window=1, window_us=10.0,
        )
        # Janela curta tem slope menor (apenas primeiros 10 μs)
        assert rrrv_short < rrrv_full
