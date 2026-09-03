"""Testes do núcleo computacional de prognóstico de isolamento (RUL).

Cobre ``app/postprocessor/prognosis/``:

* extração de eventos de estresse de forma de onda sintética, incluindo o
  caso da Tabela III do Documento A (fase B sem snubber: pico 41,44 kV,
  RRRV 15,05 kV/µs);
* ``T1 = 1,67 (t90 − t30)`` [NORMA: IEC 60034-15:2009, §2.4];
* avisos de passo de amostragem grosseiro (Etapa 1 §3.3);
* modelos de dano D1 a D7 contra valores calculados à mão;
* monotonicidade (mais tensão ⇒ menos vida) e limiar (abaixo ⇒ dano zero);
* regra de Miner (D4);
* EKF sobre série exponencial sintética e RUL com intervalo;
* índice de saúde (AHI) nas faixas e ``explain()`` somando 100 %;
* validações que devem levantar ``ValueError``.

Valores "golden" citam a origem no comentário da própria asserção.
"""

from __future__ import annotations

import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.postprocessor.prognosis import (
    KNOWN_LIMITATIONS,
    AssetHealthIndex,
    CombinedDamageAccumulator,
    DamageModelParams,
    EkfRulEstimator,
    HealthIndexThresholds,
    HealthIndexWeights,
    StressEvent,
    StressProfile,
    ThermalInterval,
    arrhenius_life,
    event_damage,
    extract_stress_events,
    front_time_correction,
    inverse_power_law_life,
    ipl_with_threshold,
    miner_damage,
    montsinger_life,
    psi_linear,
    rul_from_damage,
    simoni_life,
    supportable_events,
)

# ---------------------------------------------------------------------------
# Constantes do Documento A (fase B, sem snubber) — [FATO: doc A, Tabela III,
# p. 3]: pico 41,44 kV e RRRV 15,05 kV/µs, medidos no VCB.
# ---------------------------------------------------------------------------

DOC_A_PHASE_B_PEAK_KV = 41.44
DOC_A_PHASE_B_RRRV_KV_PER_US = 15.05


def _ramp_waveform(
    peak_kV: float,
    slope_kV_per_us: float,
    dt_s: float,
    *,
    tail_tau_s: float = 20.0e-6,
    n_tail: int = 2000,
    t_start_s: float = 0.0,
) -> tuple[list[float], list[float]]:
    """Rampa linear até ``peak_kV`` com inclinação dada, seguida de cauda RC.

    A rampa linear é o caso em que ``dv/dt`` máximo é exatamente a
    inclinação, o que permite comparar a extração com um valor exato.
    """
    t_ramp = peak_kV / slope_kV_per_us * 1.0e-6
    times: list[float] = []
    volts: list[float] = []
    n_up = max(1, int(round(t_ramp / dt_s)))
    for i in range(n_up + 1):
        tt = i * (t_ramp / n_up)
        times.append(t_start_s + tt)
        volts.append(slope_kV_per_us * tt * 1.0e6)
    for i in range(1, n_tail + 1):
        tt = t_ramp + i * dt_s
        times.append(t_start_s + tt)
        volts.append(peak_kV * math.exp(-(tt - t_ramp) / tail_tau_s))
    return times, volts


# ---------------------------------------------------------------------------
# 1. StressEvent — validação e propriedades
# ---------------------------------------------------------------------------


class TestStressEvent:
    def test_valid_event(self) -> None:
        ev = StressEvent(
            V_pk_kV=-38.30,  # fase C sem snubber [FATO: doc A, Tabela III]
            T1_us=2.0,
            dvdt_kV_per_us=19.00,
            energy_J=1.5,
            n_reignitions=5,
            theta_C=90.0,
            timestamp_s=0.0245,
            source="doc A Tabela III fase C",
        )
        assert ev.abs_V_pk_kV == pytest.approx(38.30)
        assert ev.n_reignitions == 5
        assert ev.theta_K == pytest.approx(363.15)

    def test_zero_peak_raises(self) -> None:
        with pytest.raises(ValueError, match="V_pk_kV"):
            StressEvent(V_pk_kV=0.0, T1_us=1.0, dvdt_kV_per_us=1.0)

    def test_non_positive_t1_raises(self) -> None:
        with pytest.raises(ValueError, match="T1_us"):
            StressEvent(V_pk_kV=10.0, T1_us=0.0, dvdt_kV_per_us=1.0)

    def test_negative_dvdt_raises(self) -> None:
        with pytest.raises(ValueError, match="dvdt_kV_per_us"):
            StressEvent(V_pk_kV=10.0, T1_us=1.0, dvdt_kV_per_us=-1.0)

    def test_negative_energy_raises(self) -> None:
        with pytest.raises(ValueError, match="energy_J"):
            StressEvent(V_pk_kV=10.0, T1_us=1.0, dvdt_kV_per_us=1.0, energy_J=-1.0)

    def test_zero_reignitions_raises(self) -> None:
        with pytest.raises(ValueError, match="n_reignitions"):
            StressEvent(
                V_pk_kV=10.0, T1_us=1.0, dvdt_kV_per_us=1.0, n_reignitions=0
            )

    def test_theta_below_absolute_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="theta_C"):
            StressEvent(
                V_pk_kV=10.0, T1_us=1.0, dvdt_kV_per_us=1.0, theta_C=-300.0
            )

    def test_front_time_from_rrrv_is_indicative(self) -> None:
        """``V_pk/RRRV`` NÃO é tempo de frente (Etapa 1 §3.3) — só indicativo."""
        ev = StressEvent(
            V_pk_kV=DOC_A_PHASE_B_PEAK_KV,
            T1_us=2.76,
            dvdt_kV_per_us=DOC_A_PHASE_B_RRRV_KV_PER_US,
        )
        # 41,44 / 15,05 = 2,7535 µs [CÁLCULO PRÓPRIO].
        assert ev.front_time_from_rrrv_us == pytest.approx(2.7535, rel=1e-3)
        assert ev.front_time_from_rrrv_us != ev.T1_us

    def test_in_per_unit_uses_phase_to_ground_base(self) -> None:
        """1 pu = 3,397 kV para 4,16 kV ⇒ 41,44 kV = 12,20 pu (Etapa 1 §4.5)."""
        ev = StressEvent(
            V_pk_kV=DOC_A_PHASE_B_PEAK_KV, T1_us=2.76, dvdt_kV_per_us=15.05
        )
        assert ev.in_per_unit(3.397) == pytest.approx(12.20, rel=1e-3)

    def test_in_per_unit_zero_base_raises(self) -> None:
        ev = StressEvent(V_pk_kV=10.0, T1_us=1.0, dvdt_kV_per_us=1.0)
        with pytest.raises(ValueError, match="base_kV"):
            ev.in_per_unit(0.0)


# ---------------------------------------------------------------------------
# 2. Extração de eventos de forma de onda
# ---------------------------------------------------------------------------


class TestExtractStressEvents:
    def test_doc_a_table_iii_phase_b_peak_and_rrrv(self) -> None:
        """Caso da Tabela III do Documento A: 41,44 kV e 15,05 kV/µs."""
        times, volts = _ramp_waveform(
            DOC_A_PHASE_B_PEAK_KV, DOC_A_PHASE_B_RRRV_KV_PER_US, 10.0e-9
        )
        prof = extract_stress_events(
            times, volts, threshold_kV=5.0, label="doc A fase B sem snubber"
        )
        assert prof.n_events == 1
        assert prof.peak_max_kV == pytest.approx(DOC_A_PHASE_B_PEAK_KV, rel=1e-3)
        assert prof.dvdt_max_kV_per_us == pytest.approx(
            DOC_A_PHASE_B_RRRV_KV_PER_US, rel=1e-3
        )

    def test_t1_matches_iec_60034_15_definition(self) -> None:
        """T1 = 1,67 (t90 − t30). Numa rampa linear, T1 = 1,002 · t_rampa."""
        times, volts = _ramp_waveform(
            DOC_A_PHASE_B_PEAK_KV, DOC_A_PHASE_B_RRRV_KV_PER_US, 10.0e-9
        )
        prof = extract_stress_events(times, volts, threshold_kV=5.0)
        t_ramp_us = DOC_A_PHASE_B_PEAK_KV / DOC_A_PHASE_B_RRRV_KV_PER_US
        expected = 1.67 * 0.6 * t_ramp_us  # = 1,002 · 2,7535 = 2,7590 µs
        assert prof.events[0].T1_us == pytest.approx(expected, rel=2e-3)

    def test_fine_sampling_has_no_warnings(self) -> None:
        times, volts = _ramp_waveform(
            DOC_A_PHASE_B_PEAK_KV, DOC_A_PHASE_B_RRRV_KV_PER_US, 10.0e-9
        )
        prof = extract_stress_events(times, volts, threshold_kV=5.0)
        assert prof.warnings == []

    def test_coarse_step_emits_warning(self) -> None:
        """Passo de 2 µs > 1 µs ⇒ aviso (Etapa 1 §3.3, item 3)."""
        times, volts = _ramp_waveform(
            DOC_A_PHASE_B_PEAK_KV,
            DOC_A_PHASE_B_RRRV_KV_PER_US,
            2.0e-6,
            n_tail=50,
        )
        prof = extract_stress_events(times, volts, threshold_kV=5.0)
        assert prof.warnings
        assert any("Passo de amostragem" in w for w in prof.warnings)
        assert any("LIMITES INFERIORES" in w for w in prof.warnings)

    def test_coarse_step_emits_undersampled_front_warning(self) -> None:
        times, volts = _ramp_waveform(
            DOC_A_PHASE_B_PEAK_KV,
            DOC_A_PHASE_B_RRRV_KV_PER_US,
            2.0e-6,
            n_tail=50,
        )
        prof = extract_stress_events(
            times, volts, threshold_kV=5.0, min_samples_per_front=5
        )
        assert any("t90" in w for w in prof.warnings)

    def test_reignition_grouping_counts_n_r(self) -> None:
        """Três excursões dentro da janela ⇒ n_reignitions = 3 em todas."""
        times: list[float] = []
        volts: list[float] = []
        for k, peak in enumerate((19.0, 23.0, DOC_A_PHASE_B_PEAK_KV)):
            t_i, v_i = _ramp_waveform(
                peak,
                DOC_A_PHASE_B_RRRV_KV_PER_US,
                10.0e-9,
                n_tail=400,
                t_start_s=k * 100.0e-6,
            )
            times.extend(t_i)
            volts.extend(v_i)
        prof = extract_stress_events(
            times, volts, threshold_kV=5.0, group_window_s=1.0e-3
        )
        assert prof.n_events == 3
        assert all(ev.n_reignitions == 3 for ev in prof.events)
        assert prof.n_operations == 1
        assert prof.peak_max_kV == pytest.approx(DOC_A_PHASE_B_PEAK_KV, rel=1e-3)

    def test_separate_operations_are_not_grouped(self) -> None:
        times: list[float] = []
        volts: list[float] = []
        for k, start in enumerate((0.0, 10.0e-3)):
            t_i, v_i = _ramp_waveform(
                DOC_A_PHASE_B_PEAK_KV,
                DOC_A_PHASE_B_RRRV_KV_PER_US,
                10.0e-9,
                n_tail=400,
                t_start_s=start,
            )
            times.extend(t_i)
            volts.extend(v_i)
        prof = extract_stress_events(
            times, volts, threshold_kV=5.0, group_window_s=1.0e-3
        )
        assert prof.n_events == 2
        assert all(ev.n_reignitions == 1 for ev in prof.events)
        assert prof.n_operations == 2

    def test_energy_requires_surge_impedance(self) -> None:
        times, volts = _ramp_waveform(
            DOC_A_PHASE_B_PEAK_KV, DOC_A_PHASE_B_RRRV_KV_PER_US, 10.0e-9
        )
        without = extract_stress_events(times, volts, threshold_kV=5.0)
        with_z = extract_stress_events(
            times, volts, threshold_kV=5.0, surge_impedance_ohm=50.0
        )
        assert without.energy_total_J == 0.0
        assert with_z.energy_total_J > 0.0

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="mesmo comprimento"):
            extract_stress_events([0.0, 1.0, 2.0], [1.0, 2.0], threshold_kV=1.0)

    def test_non_increasing_time_raises(self) -> None:
        with pytest.raises(ValueError, match="estritamente crescente"):
            extract_stress_events(
                [0.0, 1.0, 1.0], [1.0, 2.0, 3.0], threshold_kV=1.0
            )

    def test_non_positive_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold_kV"):
            extract_stress_events(
                [0.0, 1.0, 2.0], [1.0, 2.0, 3.0], threshold_kV=0.0
            )

    def test_too_few_samples_raises(self) -> None:
        with pytest.raises(ValueError, match="pelo menos 3 amostras"):
            extract_stress_events([0.0, 1.0], [1.0, 2.0], threshold_kV=1.0)

    def test_negative_surge_impedance_raises(self) -> None:
        times, volts = _ramp_waveform(10.0, 10.0, 10.0e-9, n_tail=50)
        with pytest.raises(ValueError, match="surge_impedance_ohm"):
            extract_stress_events(
                times, volts, threshold_kV=1.0, surge_impedance_ohm=-1.0
            )


# ---------------------------------------------------------------------------
# 3. StressProfile — estatísticas
# ---------------------------------------------------------------------------


class TestStressProfile:
    def test_equivalent_events_matches_hand_calculation(self) -> None:
        """n_eq = Σ (V_j/V_max)^n (Etapa 1 §5.5, Passo 1).

        Com {41,44; 20,72} kV e n = 4: n_eq = 1 + 0,5^4 = 1,0625.
        """
        prof = StressProfile(
            events=[
                StressEvent(V_pk_kV=41.44, T1_us=2.76, dvdt_kV_per_us=15.05),
                StressEvent(V_pk_kV=20.72, T1_us=2.76, dvdt_kV_per_us=15.05),
            ]
        )
        assert prof.equivalent_events(4.0) == pytest.approx(1.0625)

    def test_events_above_filters_by_peak(self) -> None:
        prof = StressProfile(
            events=[
                StressEvent(V_pk_kV=41.44, T1_us=2.76, dvdt_kV_per_us=15.05),
                StressEvent(V_pk_kV=6.35, T1_us=2.0, dvdt_kV_per_us=3.28),
            ]
        )
        # 14,07 kV = U'_P entre espiras a 4,16 kV [NORMA: IEC 60034-15:2009,
        # Tab. 1, via §4.5 da Etapa 1].
        assert len(prof.events_above(14.07)) == 1

    def test_empty_profile_statistics_are_neutral(self) -> None:
        prof = StressProfile()
        assert prof.n_events == 0
        assert prof.peak_max_kV == 0.0
        assert prof.equivalent_events(4.0) == 0.0
        assert math.isinf(prof.T1_min_us)

    def test_profile_rejects_non_stress_event(self) -> None:
        with pytest.raises(ValueError, match="StressEvent"):
            StressProfile(events=[object()])  # type: ignore[list-item]

    def test_profile_rejects_non_positive_sampling_step(self) -> None:
        with pytest.raises(ValueError, match="sampling_step_s"):
            StressProfile(sampling_step_s=0.0)


# ---------------------------------------------------------------------------
# 4. D1 a D6 — funções puras
# ---------------------------------------------------------------------------


class TestInversePowerLaw:
    def test_hand_value(self) -> None:
        """L = k V^-n; k = 1e6, V = 10, n = 4 ⇒ 1e6/1e4 = 100."""
        assert inverse_power_law_life(10.0, 1.0e6, 4.0) == pytest.approx(100.0)

    def test_monotonic_more_voltage_less_life(self) -> None:
        """Monotonicidade D1: mais tensão ⇒ menos vida."""
        assert inverse_power_law_life(20.0, 1.0e6, 6.4) < inverse_power_law_life(
            10.0, 1.0e6, 6.4
        )

    def test_zero_voltage_raises(self) -> None:
        with pytest.raises(ValueError, match="V deve ser > 0"):
            inverse_power_law_life(0.0, 1.0e6, 4.0)

    def test_negative_exponent_raises(self) -> None:
        with pytest.raises(ValueError, match="n deve ser >= 0"):
            inverse_power_law_life(10.0, 1.0e6, -1.0)


class TestIplWithThreshold:
    def test_below_threshold_is_infinite_life(self) -> None:
        """D2: abaixo do limiar não há dano (Etapa 1 §5.6; Gupta 1990)."""
        assert math.isinf(ipl_with_threshold(5.0, 7.8, 1.0e4, 4.0))

    def test_at_threshold_is_infinite_life(self) -> None:
        assert math.isinf(ipl_with_threshold(7.8, 7.8, 1.0e4, 4.0))

    def test_above_threshold_hand_value(self) -> None:
        """C = 100, V − V_th = 2, m = 2 ⇒ 100 · 2^-2 = 25."""
        assert ipl_with_threshold(12.0, 10.0, 100.0, 2.0) == pytest.approx(25.0)

    def test_negative_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="V_th"):
            ipl_with_threshold(12.0, -1.0, 100.0, 2.0)


class TestFrontTimeCorrection:
    def test_hand_value(self) -> None:
        """(0,6/1,2)^1 = 0,5 — frente metade ⇒ metade dos eventos suportáveis."""
        assert front_time_correction(0.6, 1.2, 1.0) == pytest.approx(0.5)

    def test_neutral_when_m_is_zero(self) -> None:
        assert front_time_correction(0.2, 1.2, 0.0) == pytest.approx(1.0)

    def test_zero_front_raises(self) -> None:
        with pytest.raises(ValueError, match="t_f deve ser > 0"):
            front_time_correction(0.0, 1.2, 1.0)


class TestMinerDamage:
    def test_sum_of_ratios(self) -> None:
        """D4: D = 10/100 + 5/50 = 0,20."""
        assert miner_damage([(10, 100), (5, 50)]) == pytest.approx(0.20)

    def test_infinite_capacity_contributes_zero(self) -> None:
        assert miner_damage([(10, math.inf), (5, 50)]) == pytest.approx(0.10)

    def test_empty_is_zero(self) -> None:
        assert miner_damage([]) == 0.0

    def test_zero_capacity_raises(self) -> None:
        with pytest.raises(ValueError, match="N_i"):
            miner_damage([(1, 0)])

    def test_negative_count_raises(self) -> None:
        with pytest.raises(ValueError, match="n_i"):
            miner_damage([(-1, 10)])

    def test_malformed_pair_raises(self) -> None:
        with pytest.raises(ValueError, match="par"):
            miner_damage([(1, 2, 3)])


class TestThermalLife:
    def test_montsinger_halving_interval(self) -> None:
        """D6: θ = θ0 + HIC ⇒ vida = L0/2 (Montsinger)."""
        life = montsinger_life(50.0, L0_h=100_000.0, theta0_C=40.0, HIC=10.0)
        assert life == pytest.approx(50_000.0)

    def test_montsinger_neutral_at_reference(self) -> None:
        life = montsinger_life(40.0, L0_h=100_000.0, theta0_C=40.0, HIC=10.0)
        assert life == pytest.approx(100_000.0)

    def test_montsinger_monotonic(self) -> None:
        hot = montsinger_life(90.0, L0_h=1.0e5, theta0_C=40.0, HIC=10.0)
        cold = montsinger_life(30.0, L0_h=1.0e5, theta0_C=40.0, HIC=10.0)
        assert hot < cold

    def test_montsinger_zero_hic_raises(self) -> None:
        with pytest.raises(ValueError, match="HIC"):
            montsinger_life(50.0, L0_h=1.0e5, theta0_C=40.0, HIC=0.0)

    def test_arrhenius_sign_convention_life_decreases_with_heat(self) -> None:
        """c_T = 1/T0 − 1/T (Etapa 1 §5.4, D5, nota de sinal)."""
        hot = arrhenius_life(120.0, L0_h=1.0e5, theta0_C=40.0, B_K=12_000.0)
        ref = arrhenius_life(40.0, L0_h=1.0e5, theta0_C=40.0, B_K=12_000.0)
        assert ref == pytest.approx(1.0e5)
        assert hot < ref

    def test_arrhenius_hand_value(self) -> None:
        """B = 1000 K, θ = 50 °C, θ0 = 40 °C ⇒ L = L0 exp[-1000 c_T]."""
        c_T = 1.0 / 313.15 - 1.0 / 323.15
        expected = 1.0e5 * math.exp(-1000.0 * c_T)
        got = arrhenius_life(50.0, L0_h=1.0e5, theta0_C=40.0, B_K=1000.0)
        assert got == pytest.approx(expected)

    def test_arrhenius_below_absolute_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="zero absoluto"):
            arrhenius_life(-300.0, L0_h=1.0e5, theta0_C=40.0, B_K=1000.0)

    def test_simoni_reduces_life_with_voltage_and_heat(self) -> None:
        """D5 Simoni: vida cai com V e com T."""
        base = simoni_life(
            10.0, 40.0, t0_h=1.0e5, V0=10.0, n=6.4, B_K=12_000.0, theta0_C=40.0
        )
        assert base == pytest.approx(1.0e5)
        assert (
            simoni_life(
                20.0, 40.0, t0_h=1.0e5, V0=10.0, n=6.4, B_K=12_000.0, theta0_C=40.0
            )
            < base
        )
        assert (
            simoni_life(
                10.0, 90.0, t0_h=1.0e5, V0=10.0, n=6.4, B_K=12_000.0, theta0_C=40.0
            )
            < base
        )

    def test_simoni_zero_voltage_raises(self) -> None:
        with pytest.raises(ValueError, match="V deve ser > 0"):
            simoni_life(
                0.0, 40.0, t0_h=1.0e5, V0=10.0, n=6.4, B_K=12_000.0, theta0_C=40.0
            )


# ---------------------------------------------------------------------------
# 5. D7 — número suportável e dano por evento
# ---------------------------------------------------------------------------


def _doc_a_params(**kwargs) -> DamageModelParams:
    """Parâmetros do exemplo numérico da Etapa 1 §5.5 (H1-H3)."""
    base = {
        "n_voltage": 4.0,
        "m_front": 0.0,
        "V_th_kV": 0.0,
        # V_ref = 7,8 pu × 3,397 kV = 26,50 kV [Etapa 1 §5.5, H2].
        "V_ref_kV": 26.50,
        "N0_events": 1.0e4,
        "HIC_C": 10.0,
        "theta0_C": 40.0,
    }
    base.update(kwargs)
    return DamageModelParams(**base)


class TestD7EventDamage:
    def test_golden_value_from_etapa1_example(self) -> None:
        """ΔD = (V_pk/V_ref)^n / N_0 com n = 4 [CÁLCULO PRÓPRIO, Etapa 1 §5.5].

        (41,44/26,50)^4 / 1e4 = 5,9799e-4.
        """
        params = _doc_a_params()
        ev = StressEvent(
            V_pk_kV=DOC_A_PHASE_B_PEAK_KV, T1_us=2.76, dvdt_kV_per_us=15.05
        )
        expected = (DOC_A_PHASE_B_PEAK_KV / 26.50) ** 4 / 1.0e4
        assert event_damage(ev, params) == pytest.approx(expected)
        assert event_damage(ev, params) == pytest.approx(5.9799e-4, rel=1e-3)

    def test_damage_is_monotonic_in_voltage(self) -> None:
        """Mais tensão ⇒ mais dano por evento (⇒ menos vida)."""
        params = _doc_a_params()
        low = StressEvent(V_pk_kV=13.65, T1_us=2.0, dvdt_kV_per_us=13.11)
        high = StressEvent(V_pk_kV=41.44, T1_us=2.0, dvdt_kV_per_us=15.05)
        assert event_damage(high, params) > event_damage(low, params)

    def test_below_threshold_gives_exactly_zero_damage(self) -> None:
        """Com V_th = 7,8 pu, o evento mitigado (4,02 pu) tem ΔD = 0 exato."""
        params = _doc_a_params(V_th_kV=26.50, V_ref_kV=40.0)
        mitigated = StressEvent(V_pk_kV=13.65, T1_us=2.0, dvdt_kV_per_us=13.11)
        assert event_damage(mitigated, params) == 0.0
        assert math.isinf(supportable_events(mitigated, params))

    def test_above_threshold_still_damages(self) -> None:
        params = _doc_a_params(V_th_kV=26.50, V_ref_kV=40.0)
        severe = StressEvent(V_pk_kV=41.44, T1_us=2.0, dvdt_kV_per_us=15.05)
        assert event_damage(severe, params) > 0.0

    def test_thermal_factor_multiplies_damage_not_capacity(self) -> None:
        """Etapa 2 §3.1: +HIC kelvin ⇒ taxa de dano × 2 (sinal corrigido)."""
        params = _doc_a_params()
        cold = StressEvent(
            V_pk_kV=41.44, T1_us=2.0, dvdt_kV_per_us=15.05, theta_C=40.0
        )
        hot = StressEvent(
            V_pk_kV=41.44, T1_us=2.0, dvdt_kV_per_us=15.05, theta_C=50.0
        )
        assert event_damage(hot, params) == pytest.approx(
            2.0 * event_damage(cold, params)
        )

    def test_thermal_factor_plus_20K_gives_four_times(self) -> None:
        """+20 K com HIC = 10 K ⇒ 2^2 = 4,0 [CÁLCULO PRÓPRIO, Etapa 2 §3.1]."""
        params = _doc_a_params()
        cold = StressEvent(
            V_pk_kV=41.44, T1_us=2.0, dvdt_kV_per_us=15.05, theta_C=40.0
        )
        hot = StressEvent(
            V_pk_kV=41.44, T1_us=2.0, dvdt_kV_per_us=15.05, theta_C=60.0
        )
        assert event_damage(hot, params) == pytest.approx(
            4.0 * event_damage(cold, params)
        )

    def test_front_correction_penalises_short_fronts(self) -> None:
        """Com m = 1, frente de 0,6 µs (metade de 1,2 µs) dobra o dano (D3)."""
        params = _doc_a_params(m_front=1.0, t_f0_us=1.2)
        long_front = StressEvent(V_pk_kV=41.44, T1_us=1.2, dvdt_kV_per_us=15.05)
        short_front = StressEvent(V_pk_kV=41.44, T1_us=0.6, dvdt_kV_per_us=30.0)
        assert event_damage(short_front, params) == pytest.approx(
            2.0 * event_damage(long_front, params)
        )

    def test_residual_withstand_requires_u_w(self) -> None:
        params = _doc_a_params()
        ev = StressEvent(V_pk_kV=41.44, T1_us=2.0, dvdt_kV_per_us=15.05)
        with pytest.raises(ValueError, match="U_w_kV"):
            supportable_events(ev, params, normalization="residual_withstand")

    def test_unknown_normalization_raises(self) -> None:
        params = _doc_a_params()
        ev = StressEvent(V_pk_kV=41.44, T1_us=2.0, dvdt_kV_per_us=15.05)
        with pytest.raises(ValueError, match="normalization"):
            supportable_events(ev, params, normalization="inexistente")

    def test_params_reject_threshold_above_reference(self) -> None:
        with pytest.raises(ValueError, match="V_ref_kV"):
            DamageModelParams(V_th_kV=30.0, V_ref_kV=26.50)

    def test_params_reject_negative_exponent(self) -> None:
        with pytest.raises(ValueError, match="n_voltage"):
            DamageModelParams(n_voltage=-1.0)

    def test_params_calibration_warnings_are_declared(self) -> None:
        msgs = DamageModelParams().calibration_warnings()
        assert any("NÃO CALIBRADOS" in m for m in msgs)

    def test_default_params_are_inside_literature_ranges(self) -> None:
        """n = 6,4 ∈ [3,8; 11,7] e HIC = 10 ∈ [8; 15] (CIGRE / Theofanous)."""
        params = DamageModelParams()
        assert params.n_within_literature_range
        assert params.hic_within_literature_range


# ---------------------------------------------------------------------------
# 6. Acumulador combinado (5.1)-(5.2)
# ---------------------------------------------------------------------------


class TestCombinedDamageAccumulator:
    def test_total_is_sum_of_parcels(self) -> None:
        acc = CombinedDamageAccumulator(params=_doc_a_params())
        acc.add_event(
            StressEvent(V_pk_kV=41.44, T1_us=2.76, dvdt_kV_per_us=15.05)
        )
        acc.add_thermal_interval(40.0, 8760.0)
        assert acc.D_total == pytest.approx(acc.D_el + acc.D_th + acc.D_sin)
        assert acc.D_sin == 0.0
        assert acc.is_lower_bound is True

    def test_thermal_integral_hand_value(self) -> None:
        """D_th = Δt / L(θ0) com L0 = 175 200 h e Δt = 175 200 h ⇒ 1,0."""
        acc = CombinedDamageAccumulator()
        acc.add_thermal_interval(40.0, 175_200.0)
        assert acc.D_th == pytest.approx(1.0)
        assert acc.remaining_fraction == pytest.approx(0.0)

    def test_thermal_profile_accumulates(self) -> None:
        acc = CombinedDamageAccumulator()
        acc.add_thermal_profile(
            [
                ThermalInterval(40.0, 8760.0),
                ThermalInterval(50.0, 8760.0),
            ]
        )
        # 50 °C = θ0 + HIC ⇒ vida metade ⇒ dano dobro.
        assert acc.D_th == pytest.approx(3.0 * 8760.0 / 175_200.0)
        assert acc.thermal_hours == pytest.approx(17_520.0)

    def test_synergy_callable_is_used(self) -> None:
        acc = CombinedDamageAccumulator(
            params=_doc_a_params(), synergy_fn=lambda th, el: 0.25 * (th + el)
        )
        acc.add_thermal_interval(40.0, 175_200.0)
        assert acc.D_sin == pytest.approx(0.25)
        assert acc.is_lower_bound is False

    def test_gamma_and_residual_withstand(self) -> None:
        """γ = U_w/U_s com U_w = U_w0 ψ(D) (Etapa 1 §6)."""
        acc = CombinedDamageAccumulator(
            params=_doc_a_params(), U_w0_kV=14.07, U_s_kV=14.07, psi_min=0.5
        )
        assert acc.gamma() == pytest.approx(1.0)
        acc.add_thermal_interval(40.0, 175_200.0)  # D = 1 ⇒ ψ = 0,5
        assert acc.psi() == pytest.approx(0.5)
        assert acc.gamma() == pytest.approx(0.5)

    def test_gamma_without_u_s_raises(self) -> None:
        acc = CombinedDamageAccumulator(U_w0_kV=14.07)
        with pytest.raises(ValueError, match="U_s_kV"):
            acc.gamma()

    def test_u_w_without_u_w0_raises(self) -> None:
        acc = CombinedDamageAccumulator()
        with pytest.raises(ValueError, match="U_w0_kV"):
            acc.U_w_kV()

    def test_residual_withstand_mode_requires_u_w0(self) -> None:
        with pytest.raises(ValueError, match="U_w0_kV"):
            CombinedDamageAccumulator(normalization="residual_withstand")

    def test_residual_withstand_is_monotonic_in_damage(self) -> None:
        """Etapa 2 §5.2 (saída ii): ∂F/∂D > 0 é ESTRUTURAL nesse modo."""
        ev = StressEvent(V_pk_kV=41.44, T1_us=2.76, dvdt_kV_per_us=15.05)
        pristine = CombinedDamageAccumulator(
            params=_doc_a_params(),
            U_w0_kV=14.07,
            normalization="residual_withstand",
        )
        aged = CombinedDamageAccumulator(
            params=_doc_a_params(),
            U_w0_kV=14.07,
            normalization="residual_withstand",
        )
        aged.add_thermal_interval(40.0, 87_600.0)  # D_th = 0,5 ⇒ U_w menor
        assert aged.add_event(ev) > pristine.add_event(ev)

    def test_state_dependent_threshold_reopens_damage(self) -> None:
        """Etapa 2 §5.1: o envelhecimento move o evento para cima do limiar."""
        params = _doc_a_params(V_th_kV=20.0, V_ref_kV=40.0)
        ev = StressEvent(V_pk_kV=19.0, T1_us=2.0, dvdt_kV_per_us=10.0)
        acc = CombinedDamageAccumulator(
            params=params,
            U_w0_kV=14.07,
            psi_min=0.5,
            state_dependent_threshold=True,
        )
        assert acc.add_event(ev) == 0.0  # V_th = 20,0 > 19,0
        acc.add_thermal_interval(40.0, 175_200.0)  # D = 1 ⇒ V_th = 10,0
        assert acc.add_event(ev) > 0.0

    def test_rul_operations_requires_profile(self) -> None:
        acc = CombinedDamageAccumulator(params=_doc_a_params())
        acc.add_event(
            StressEvent(V_pk_kV=41.44, T1_us=2.76, dvdt_kV_per_us=15.05)
        )
        with pytest.raises(ValueError, match="nenhuma manobra"):
            acc.rul_operations()

    def test_rul_operations_and_years(self) -> None:
        """RUL_N = (1 − D)/E[ΔD_m]; RUL_t = RUL_N/λ_m (D7)."""
        params = _doc_a_params()
        prof = StressProfile(
            events=[
                StressEvent(V_pk_kV=41.44, T1_us=2.76, dvdt_kV_per_us=15.05)
            ]
        )
        acc = CombinedDamageAccumulator(params=params)
        acc.add_profile(prof)
        delta = (41.44 / 26.50) ** 4 / 1.0e4
        assert acc.n_operations == 1
        assert acc.rul_operations() == pytest.approx((1.0 - delta) / delta)
        # λ_m = 10 partidas abortadas/ano [Etapa 1 §5.5, H5].
        assert acc.rul_years(10.0) == pytest.approx(acc.rul_operations() / 10.0)

    def test_rul_years_rejects_non_positive_lambda(self) -> None:
        acc = CombinedDamageAccumulator(params=_doc_a_params())
        acc.add_profile(
            StressProfile(
                events=[
                    StressEvent(V_pk_kV=41.44, T1_us=2.76, dvdt_kV_per_us=15.05)
                ]
            )
        )
        with pytest.raises(ValueError, match="operations_per_year"):
            acc.rul_years(0.0)

    def test_rul_is_infinite_when_all_events_below_threshold(self) -> None:
        params = _doc_a_params(V_th_kV=26.50, V_ref_kV=40.0)
        acc = CombinedDamageAccumulator(params=params)
        acc.add_profile(
            StressProfile(
                events=[
                    StressEvent(V_pk_kV=13.65, T1_us=2.0, dvdt_kV_per_us=13.11)
                ]
            )
        )
        assert acc.n_events_below_threshold == 1
        assert math.isinf(acc.rul_operations())

    def test_invalid_thermal_model_raises(self) -> None:
        with pytest.raises(ValueError, match="thermal_model"):
            CombinedDamageAccumulator(thermal_model="weibull")

    def test_add_event_rejects_wrong_type(self) -> None:
        acc = CombinedDamageAccumulator()
        with pytest.raises(ValueError, match="StressEvent"):
            acc.add_event(object())  # type: ignore[arg-type]

    def test_negative_thermal_duration_raises(self) -> None:
        acc = CombinedDamageAccumulator()
        with pytest.raises(ValueError, match="duration_h"):
            acc.add_thermal_interval(40.0, -1.0)

    def test_summary_declares_lower_bound(self) -> None:
        acc = CombinedDamageAccumulator(params=_doc_a_params())
        assert "COTA INFERIOR" in acc.summary()


class TestPsi:
    def test_psi_at_zero_damage_is_one(self) -> None:
        assert psi_linear(0.0) == pytest.approx(1.0)

    def test_psi_is_decreasing(self) -> None:
        assert psi_linear(1.0, psi_min=0.5) == pytest.approx(0.5)
        assert psi_linear(0.5, psi_min=0.5) == pytest.approx(0.75)

    def test_psi_rejects_negative_damage(self) -> None:
        with pytest.raises(ValueError, match="D deve ser >= 0"):
            psi_linear(-0.1)


# ---------------------------------------------------------------------------
# 7. EKF e RUL
# ---------------------------------------------------------------------------


def _exponential_series(
    alpha: float, beta: float, n: int = 101
) -> tuple[list[float], list[float]]:
    times = [float(k) for k in range(n)]
    values = [alpha * math.exp(beta * t) for t in times]
    return times, values


class TestEkfRulEstimator:
    def test_converges_on_synthetic_exponential(self) -> None:
        """I = α e^{βt} com α = 1,0 e β = 0,05 (artigo 02, eq. 7)."""
        times, values = _exponential_series(1.0, 0.05)
        ekf = EkfRulEstimator(alpha0=1.2, beta0=0.02)
        ekf.update_series(times, values)
        assert ekf.alpha == pytest.approx(1.0, rel=1e-3)
        assert ekf.beta == pytest.approx(0.05, rel=1e-3)
        assert ekf.n_updates == 101

    def test_converges_on_decaying_series(self) -> None:
        times, values = _exponential_series(10.0, -0.03)
        ekf = EkfRulEstimator(alpha0=9.0, beta0=-0.01)
        ekf.update_series(times, values)
        assert ekf.alpha == pytest.approx(10.0, rel=1e-2)
        assert ekf.beta == pytest.approx(-0.03, rel=1e-2)

    def test_predict_rul_point_matches_analytic(self) -> None:
        """T = ln(limiar/α)/β; RUL = T − t_now."""
        times, values = _exponential_series(1.0, 0.05)
        ekf = EkfRulEstimator(alpha0=1.2, beta0=0.02)
        ekf.update_series(times, values)
        threshold = 2.0 * math.exp(0.05 * 100.0)
        pred = ekf.predict_rul(threshold)
        expected = math.log(threshold / 1.0) / 0.05 - 100.0
        assert pred.rul == pytest.approx(expected, rel=1e-3)

    def test_predict_rul_returns_bracketing_interval(self) -> None:
        times, values = _exponential_series(1.0, 0.05)
        ekf = EkfRulEstimator(alpha0=1.2, beta0=0.02)
        ekf.update_series(times, values)
        pred = ekf.predict_rul(2.0 * math.exp(5.0), confidence=0.95)
        assert pred.rul_lower <= pred.rul <= pred.rul_upper
        assert pred.sigma > 0.0
        assert pred.confidence == 0.95
        assert "ISO 13381-1" in pred.summary()

    def test_wider_confidence_gives_wider_interval(self) -> None:
        times, values = _exponential_series(1.0, 0.05)
        ekf = EkfRulEstimator(alpha0=1.2, beta0=0.02)
        ekf.update_series(times, values)
        thr = 2.0 * math.exp(5.0)
        narrow = ekf.predict_rul(thr, confidence=0.68)
        wide = ekf.predict_rul(thr, confidence=0.99)
        assert (wide.rul_upper - wide.rul_lower) > (
            narrow.rul_upper - narrow.rul_lower
        )

    def test_is_deterministic(self) -> None:
        times, values = _exponential_series(1.0, 0.05)
        a = EkfRulEstimator(alpha0=1.2, beta0=0.02)
        b = EkfRulEstimator(alpha0=1.2, beta0=0.02)
        a.update_series(times, values)
        b.update_series(times, values)
        assert a.state == b.state

    def test_history_length_matches_updates(self) -> None:
        times, values = _exponential_series(1.0, 0.05, n=11)
        ekf = EkfRulEstimator(alpha0=1.0, beta0=0.05)
        ekf.update_series(times, values)
        assert len(ekf.history) == 11
        assert ekf.t_now == pytest.approx(10.0)

    def test_zero_alpha0_raises(self) -> None:
        with pytest.raises(ValueError, match="alpha0"):
            EkfRulEstimator(alpha0=0.0, beta0=0.05)

    def test_non_positive_r_raises(self) -> None:
        with pytest.raises(ValueError, match="covariância de medição"):
            EkfRulEstimator(alpha0=1.0, beta0=0.05, r=0.0)

    def test_wrong_q_dimension_raises(self) -> None:
        with pytest.raises(ValueError, match="q_diag"):
            EkfRulEstimator(alpha0=1.0, beta0=0.05, q_diag=(1.0, 2.0))

    def test_backwards_time_raises(self) -> None:
        ekf = EkfRulEstimator(alpha0=1.0, beta0=0.05)
        ekf.update(1.0, 1.05)
        with pytest.raises(ValueError, match="não decrescente"):
            ekf.update(0.5, 1.02)

    def test_zero_beta_rul_raises(self) -> None:
        ekf = EkfRulEstimator(alpha0=1.0, beta0=0.0)
        with pytest.raises(ValueError, match="β = 0"):
            ekf.predict_rul(2.0)

    def test_sign_mismatch_threshold_raises(self) -> None:
        ekf = EkfRulEstimator(alpha0=1.0, beta0=0.05)
        with pytest.raises(ValueError, match="mesmo sinal"):
            ekf.predict_rul(-2.0)

    def test_already_crossed_threshold_raises(self) -> None:
        times, values = _exponential_series(1.0, 0.05)
        ekf = EkfRulEstimator(alpha0=1.0, beta0=0.05)
        ekf.update_series(times, values)
        with pytest.raises(ValueError, match="já foi cruzado"):
            ekf.predict_rul(1.0)

    def test_confidence_out_of_range_raises(self) -> None:
        times, values = _exponential_series(1.0, 0.05, n=11)
        ekf = EkfRulEstimator(alpha0=1.0, beta0=0.05)
        ekf.update_series(times, values)
        with pytest.raises(ValueError, match="confidence"):
            ekf.predict_rul(10.0, confidence=1.5)

    def test_update_series_length_mismatch_raises(self) -> None:
        ekf = EkfRulEstimator(alpha0=1.0, beta0=0.05)
        with pytest.raises(ValueError, match="mesmo comprimento"):
            ekf.update_series([0.0, 1.0], [1.0])


class TestRulFromDamage:
    def test_hand_value(self) -> None:
        """RUL = (1 − 0,25)/0,001 = 750."""
        assert rul_from_damage(0.25, 0.001) == pytest.approx(750.0)

    def test_zero_rate_is_infinite(self) -> None:
        assert math.isinf(rul_from_damage(0.5, 0.0))

    def test_failed_asset_is_zero(self) -> None:
        assert rul_from_damage(1.0, 0.001) == 0.0

    def test_negative_damage_raises(self) -> None:
        with pytest.raises(ValueError, match="D deve ser >= 0"):
            rul_from_damage(-0.1, 0.001)

    def test_negative_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="dD_dt"):
            rul_from_damage(0.1, -0.001)


# ---------------------------------------------------------------------------
# 8. Índice de saúde (AHI)
# ---------------------------------------------------------------------------


class TestAssetHealthIndex:
    def test_pristine_asset_scores_100(self) -> None:
        ahi = AssetHealthIndex(D_el=0.0, D_th=0.0, gamma=2.0)
        assert ahi.index == pytest.approx(100.0)
        assert ahi.classification == "BOM"
        assert ahi.traffic_light == "verde"

    def test_exhausted_asset_scores_zero(self) -> None:
        ahi = AssetHealthIndex(D_el=1.0, D_th=1.0, gamma=1.0)
        assert ahi.index == pytest.approx(0.0)
        assert ahi.classification == "CRITICO"
        assert ahi.traffic_light == "vermelho"

    def test_intermediate_bands(self) -> None:
        degraded = AssetHealthIndex(D_el=0.4, D_th=0.4, gamma=1.4)
        assert 50.0 <= degraded.index < 70.0
        assert degraded.classification == "DEGRADADO"
        assert degraded.traffic_light == "laranja"

    def test_acceptable_band(self) -> None:
        ok = AssetHealthIndex(D_el=0.2, D_th=0.2, gamma=1.75)
        assert 70.0 <= ok.index < 85.0
        assert ok.classification == "ACEITAVEL"
        assert ok.traffic_light == "amarelo"

    def test_explain_contributions_sum_to_100(self) -> None:
        ahi = AssetHealthIndex(
            D_el=0.05,
            D_th=0.10,
            gamma=1.6,
            ir_Mohm=500.0,
            pi=2.5,
            tan_delta=8.0e-3,
            pd_qm_mV=50.0,
            asset_id="M-4160-01",
        )
        contributions = ahi.explain()
        assert len(contributions) == 6
        assert sum(c.contribution_pct for c in contributions) == pytest.approx(100.0)
        assert sum(c.contribution_points for c in contributions) == pytest.approx(
            ahi.index
        )

    def test_explain_sums_to_100_even_when_index_is_zero(self) -> None:
        ahi = AssetHealthIndex(D_el=1.0, D_th=1.0, gamma=1.0)
        assert sum(c.contribution_pct for c in ahi.explain()) == pytest.approx(100.0)

    def test_unavailable_components_are_declared_not_omitted(self) -> None:
        ahi = AssetHealthIndex(D_el=0.1, D_th=0.1)
        by_name = {c.name: c for c in ahi.explain()}
        assert by_name["coordination_margin"].available is False
        assert by_name["partial_discharge"].available is False
        assert by_name["coordination_margin"].normalized_weight == 0.0
        assert by_name["damage_electrical"].available is True

    def test_weights_renormalise_over_available_components(self) -> None:
        """Sem indicadores medidos, D_el e D_th dividem o peso total."""
        ahi = AssetHealthIndex(D_el=0.0, D_th=1.0)
        w = HealthIndexWeights()
        expected = 100.0 * w.damage_electrical / (
            w.damage_electrical + w.damage_thermal
        )
        assert ahi.index == pytest.approx(expected)

    def test_ir_pi_component_takes_the_worse_score(self) -> None:
        """Leitura conservadora: min(escore IR, escore PI)."""
        good_ir_bad_pi = AssetHealthIndex(ir_Mohm=1000.0, pi=2.0)
        by_name = {c.name: c for c in good_ir_bad_pi.explain()}
        assert by_name["insulation_resistance"].score == pytest.approx(0.0)

    def test_ir_at_normative_minimum_scores_zero(self) -> None:
        """IR = 100 MΩ [NORMA: ABNT NBR 17094-3:2018, 6.8.2, Tab. 2]."""
        ahi = AssetHealthIndex(ir_Mohm=100.0)
        by_name = {c.name: c for c in ahi.explain()}
        assert by_name["insulation_resistance"].score == pytest.approx(0.0)

    def test_pd_at_p90_alarm_scores_zero(self) -> None:
        """Q_m = 208 mV = percentil 90 (2–<6 kV) [Warren, IRMC 2022, Tab. 1]."""
        ahi = AssetHealthIndex(pd_qm_mV=208.0)
        by_name = {c.name: c for c in ahi.explain()}
        assert by_name["partial_discharge"].score == pytest.approx(0.0)

    def test_tan_delta_at_limit_scores_zero(self) -> None:
        """tan δ = 20 × 10⁻³ [IEC 60034-27-3, Tab. 1, via Iris Power]."""
        ahi = AssetHealthIndex(tan_delta=20.0e-3)
        by_name = {c.name: c for c in ahi.explain()}
        assert by_name["dissipation_factor"].score == pytest.approx(0.0)

    def test_gamma_at_end_of_life_scores_zero(self) -> None:
        """γ → 1 é o critério de fim de vida por coordenação (Etapa 1 §6)."""
        ahi = AssetHealthIndex(gamma=1.0)
        by_name = {c.name: c for c in ahi.explain()}
        assert by_name["coordination_margin"].score == pytest.approx(0.0)

    def test_negative_damage_raises(self) -> None:
        with pytest.raises(ValueError, match="D_el"):
            AssetHealthIndex(D_el=-0.1)

    def test_non_positive_gamma_raises(self) -> None:
        with pytest.raises(ValueError, match="gamma"):
            AssetHealthIndex(gamma=0.0)

    def test_non_positive_ir_raises(self) -> None:
        with pytest.raises(ValueError, match="ir_Mohm"):
            AssetHealthIndex(ir_Mohm=0.0)

    def test_negative_tan_delta_raises(self) -> None:
        with pytest.raises(ValueError, match="tan_delta"):
            AssetHealthIndex(tan_delta=-1.0e-3)

    def test_negative_pd_raises(self) -> None:
        with pytest.raises(ValueError, match="pd_qm_mV"):
            AssetHealthIndex(pd_qm_mV=-1.0)

    def test_no_available_component_raises(self) -> None:
        weights = HealthIndexWeights(
            damage_electrical=0.0,
            damage_thermal=0.0,
            coordination_margin=0.0,
            insulation_resistance=0.0,
            dissipation_factor=0.0,
            partial_discharge=1.0,
        )
        ahi = AssetHealthIndex(weights=weights)
        with pytest.raises(ValueError, match="nenhum componente disponível"):
            _ = ahi.index

    def test_weights_reject_negative_value(self) -> None:
        with pytest.raises(ValueError, match="damage_thermal"):
            HealthIndexWeights(damage_thermal=-0.1)

    def test_thresholds_reject_inverted_ir_band(self) -> None:
        with pytest.raises(ValueError, match="ir_good_Mohm"):
            HealthIndexThresholds(ir_min_Mohm=100.0, ir_good_Mohm=50.0)

    def test_thresholds_reject_inverted_gamma_band(self) -> None:
        with pytest.raises(ValueError, match="gamma_healthy"):
            HealthIndexThresholds(gamma_end_of_life=2.0, gamma_healthy=1.0)

    def test_empty_bands_raise(self) -> None:
        with pytest.raises(ValueError, match="bands"):
            AssetHealthIndex(bands=())

    def test_summary_declares_non_normative_bands(self) -> None:
        ahi = AssetHealthIndex(D_el=0.1, D_th=0.1, asset_id="M-1")
        text = ahi.summary()
        assert "NÃO NORMATIVAS" in text
        assert "M-1" in text


# ---------------------------------------------------------------------------
# 9. Integração da cadeia e auditoria
# ---------------------------------------------------------------------------


class TestEndToEndChain:
    def test_waveform_to_health_index(self) -> None:
        """Cadeia completa: forma de onda ⇒ dano ⇒ AHI, sem I/O."""
        times, volts = _ramp_waveform(
            DOC_A_PHASE_B_PEAK_KV, DOC_A_PHASE_B_RRRV_KV_PER_US, 10.0e-9
        )
        prof = extract_stress_events(
            times, volts, threshold_kV=5.0, theta_C=90.0, label="partida abortada"
        )
        acc = CombinedDamageAccumulator(
            params=_doc_a_params(), U_w0_kV=14.07, U_s_kV=14.07
        )
        acc.add_profile(prof)
        acc.add_thermal_interval(90.0, 100.0)
        ahi = AssetHealthIndex(
            D_el=acc.D_el, D_th=acc.D_th, gamma=acc.gamma(), asset_id="M-4160-01"
        )
        assert acc.D_el > 0.0
        assert acc.D_th > 0.0
        assert 0.0 <= ahi.index <= 100.0
        assert sum(c.contribution_pct for c in ahi.explain()) == pytest.approx(100.0)

    def test_mitigation_moves_event_below_threshold(self) -> None:
        """Etapa 1 §5.5: com V_th = 7,8 pu o evento mitigado tem ΔD = 0."""
        params = _doc_a_params(V_th_kV=26.50, V_ref_kV=40.0)
        without = CombinedDamageAccumulator(params=params)
        with_snubber = CombinedDamageAccumulator(params=params)
        # [FATO: doc A, Tabela III, p. 3] fase B: 41,44 kV sem, 13,65 kV com.
        without.add_event(
            StressEvent(V_pk_kV=41.44, T1_us=2.76, dvdt_kV_per_us=15.05)
        )
        with_snubber.add_event(
            StressEvent(V_pk_kV=13.65, T1_us=1.04, dvdt_kV_per_us=13.11)
        )
        assert without.D_el > 0.0
        assert with_snubber.D_el == 0.0


class TestModuleAudit:
    def test_known_limitations_keys_are_namespaced(self) -> None:
        assert KNOWN_LIMITATIONS
        assert all(k.startswith("rul_") for k in KNOWN_LIMITATIONS)

    def test_known_limitations_declare_calibration_gap(self) -> None:
        assert "rul_params_not_calibrated" in KNOWN_LIMITATIONS
        assert "NÃO CALIBRADOS" in KNOWN_LIMITATIONS["rul_params_not_calibrated"]

    def test_known_limitations_declare_lower_bound(self) -> None:
        assert "COTA INFERIOR" in KNOWN_LIMITATIONS["rul_synergy_lower_bound"]

    def test_known_limitations_values_are_non_empty(self) -> None:
        assert all(v.strip() for v in KNOWN_LIMITATIONS.values())

    def test_package_exports_public_api(self) -> None:
        import app.postprocessor.prognosis as pkg

        for name in pkg.__all__:
            assert hasattr(pkg, name), name

    def test_core_modules_do_not_import_gui_or_plotting(self) -> None:
        """O núcleo não pode importar PySide6 nem matplotlib (lint.yml job
        ``imports`` instala apenas numpy/pydantic/PyYAML)."""
        import inspect

        import app.postprocessor.prognosis as pkg
        import app.postprocessor.prognosis.damage_models as dm
        import app.postprocessor.prognosis.health_index as hi
        import app.postprocessor.prognosis.rul_estimator as re_
        import app.postprocessor.prognosis.stress_profile as sp

        for mod in (pkg, dm, hi, re_, sp):
            src = inspect.getsource(mod)
            assert "import PySide6" not in src, mod.__name__
            assert "from PySide6" not in src, mod.__name__
            assert "import matplotlib" not in src, mod.__name__

    def test_core_modules_do_not_perform_io(self) -> None:
        """Sem I/O: nenhum ``open(``, ``json.dump`` ou ``Path(`` no núcleo."""
        import inspect

        import app.postprocessor.prognosis.damage_models as dm
        import app.postprocessor.prognosis.health_index as hi
        import app.postprocessor.prognosis.rul_estimator as re_
        import app.postprocessor.prognosis.stress_profile as sp

        for mod in (dm, hi, re_, sp):
            src = inspect.getsource(mod)
            assert "open(" not in src, mod.__name__
            assert "import os" not in src, mod.__name__
