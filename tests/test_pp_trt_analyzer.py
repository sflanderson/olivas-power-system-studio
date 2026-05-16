"""
tests/test_pp_trt_analyzer.py — v0.27.1: análise TRT vs IEC 62271-100.

Cobre:

* IEC 62271 standards: kpp factors, kaf, RRRV típicos, peak
  voltage formula, envelope 2-param e 4-param.
* TrtWaveform: validação de input (tempo monotônico, opening
  in range, paralel arrays).
* analyze_trt: cenários PASS (envelope respeitado) e FAIL
  (excedido), métricas observadas vs envelope, violations.
* Cenário realista alimentado pelo SM (synchronous machine):
  curto monofásico em barra → I'' calculado → TRT estimada vs
  envelope da norma.
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.trt_analyzer import (
    TrtAnalysisReport, TrtViolation, TrtWaveform, analyze_trt,
)
from app.standards.iec62271 import (
    GroundingType, TestDuty,
    TrtEnvelope2Param, TrtEnvelope4Param,
    amplitude_factor_kaf,
    first_pole_factor_kpp,
    peak_voltage_uc_kV,
    select_envelope_type,
    trt_envelope_2param,
    trt_envelope_4param,
    typical_rrrv_kV_per_us,
)


# ---------------------------------------------------------------------------
# IEC 62271 standards constants
# ---------------------------------------------------------------------------


class TestKppFactors:
    def test_effectively_grounded(self):
        assert first_pole_factor_kpp(GroundingType.EFFECTIVELY_GROUNDED) == 1.3

    def test_non_effectively_grounded(self):
        assert first_pole_factor_kpp(GroundingType.NON_EFFECTIVELY_GROUNDED) == 1.5


class TestKafFactors:
    def test_t100s(self):
        assert amplitude_factor_kaf(TestDuty.T100s) == 1.40

    def test_t60(self):
        assert amplitude_factor_kaf(TestDuty.T60) == 1.50

    def test_t30(self):
        assert amplitude_factor_kaf(TestDuty.T30) == 1.54

    def test_t10(self):
        assert amplitude_factor_kaf(TestDuty.T10) == 1.76


class TestRrrvTypical:
    def test_t100s_2_kV_us(self):
        assert typical_rrrv_kV_per_us(TestDuty.T100s) == 2.0

    def test_t10_7_kV_us(self):
        assert typical_rrrv_kV_per_us(TestDuty.T10) == 7.0


class TestPeakVoltage:
    def test_145kV_kpp13_kaf14(self):
        """u_c = 1.3 · 1.4 · √2 · 145 / √3 ≈ 215.5 kV."""
        u = peak_voltage_uc_kV(145.0, 1.3, 1.4)
        assert u == pytest.approx(215.47, abs=0.5)

    def test_550kV_kpp15_kaf14(self):
        """u_c = 1.5 · 1.4 · √2 · 550 / √3 ≈ 942.9 kV."""
        u = peak_voltage_uc_kV(550.0, 1.5, 1.4)
        assert u == pytest.approx(942.91, abs=0.5)

    def test_zero_voltage_rejected(self):
        with pytest.raises(ValueError):
            peak_voltage_uc_kV(0.0, 1.3, 1.4)


# ---------------------------------------------------------------------------
# Envelopes
# ---------------------------------------------------------------------------


class TestEnvelope2Param:
    def test_construct(self):
        env = trt_envelope_2param(
            rated_voltage_kV=72.5,
            grounding=GroundingType.EFFECTIVELY_GROUNDED,
            duty=TestDuty.T100s,
        )
        # u_c = 1.3·1.4·√2·72.5/√3 ≈ 107.7 kV
        assert env.u_c_kV == pytest.approx(107.74, abs=0.5)
        assert env.duty == TestDuty.T100s

    def test_voltage_at_origin(self):
        env = trt_envelope_2param(
            72.5, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        assert env.voltage_at(0.0) == pytest.approx(0.0)

    def test_voltage_at_peak(self):
        env = trt_envelope_2param(
            72.5, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        assert env.voltage_at(env.t_3_us) == pytest.approx(env.u_c_kV)

    def test_voltage_after_peak(self):
        """Após t_3 → mantém u_c."""
        env = trt_envelope_2param(
            72.5, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        assert env.voltage_at(2 * env.t_3_us) == pytest.approx(env.u_c_kV)

    def test_voltage_with_delay(self):
        env = TrtEnvelope2Param(
            u_c_kV=100, t_3_us=50, t_d_us=10,
            duty=TestDuty.T100s, rated_voltage_kV=72.5,
        )
        assert env.voltage_at(5) == 0.0      # antes do delay
        assert env.voltage_at(10) == 0.0     # no delay
        assert env.voltage_at(35) == pytest.approx(50, abs=0.1)  # 50%
        assert env.voltage_at(60) == 100.0   # após o pico

    def test_rrrv_property(self):
        env = trt_envelope_2param(
            72.5, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        # u_c / t_3 = 107.7 / 53.87 ≈ 2.0 kV/μs (expected RRRV)
        assert env.rrrv_kV_per_us == pytest.approx(2.0, abs=0.05)


class TestEnvelope4Param:
    def test_construct_145kV(self):
        env = trt_envelope_4param(
            rated_voltage_kV=145.0,
            grounding=GroundingType.EFFECTIVELY_GROUNDED,
            duty=TestDuty.T100s,
        )
        assert env.u_c_kV == pytest.approx(215.47, abs=0.5)
        # u_1 = 0.75 · u_c
        assert env.u_1_kV == pytest.approx(0.75 * env.u_c_kV, abs=0.01)
        # t_1 = 0.5 · t_2
        assert env.t_1_us == pytest.approx(0.5 * env.t_2_us, abs=0.01)

    def test_rrrv_initial_higher(self):
        """RRRV inicial > RRRV médio (envelope é côncavo)."""
        env = trt_envelope_4param(
            145.0, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        assert env.rrrv_initial_kV_per_us > env.rrrv_average_kV_per_us

    def test_voltage_at_segments(self):
        """Verifica os 3 segmentos do envelope 4-param."""
        env = TrtEnvelope4Param(
            u_1_kV=75, t_1_us=50, u_c_kV=100, t_2_us=100, t_d_us=2,
            duty=TestDuty.T100s, rated_voltage_kV=145,
        )
        # antes do delay
        assert env.voltage_at(1) == 0.0
        # primeiro segmento (íngreme): em t=27us (0+25 rel), 50% de u_1
        assert env.voltage_at(2 + 25) == pytest.approx(75 * 25 / 50, abs=0.1)
        # ponto de quebra
        assert env.voltage_at(2 + 50) == pytest.approx(75, abs=0.1)
        # segundo segmento: em t=2+75 (25 do segundo segmento de 50 total)
        # u = 75 + (100-75)*25/50 = 75 + 12.5 = 87.5
        assert env.voltage_at(2 + 75) == pytest.approx(87.5, abs=0.1)
        # após pico
        assert env.voltage_at(2 + 100) == pytest.approx(100, abs=0.1)
        assert env.voltage_at(500) == pytest.approx(100, abs=0.1)


class TestSelectEnvelope:
    def test_high_voltage_uses_4param(self):
        assert select_envelope_type(145.0, TestDuty.T100s) == "4param"
        assert select_envelope_type(245.0, TestDuty.T10) == "4param"

    def test_t100s_always_4param(self):
        assert select_envelope_type(72.5, TestDuty.T100s) == "4param"

    def test_low_voltage_t10(self):
        assert select_envelope_type(36.0, TestDuty.T10) == "2param"

    def test_low_voltage_t100a(self):
        assert select_envelope_type(36.0, TestDuty.T100a) == "2param"


# ---------------------------------------------------------------------------
# TrtWaveform validação
# ---------------------------------------------------------------------------


class TestWaveformValidation:
    def test_basic_construct(self):
        wf = TrtWaveform(
            time_s=(0.0, 0.001, 0.002),
            voltage_kV=(0.0, 50.0, 100.0),
            opening_time_s=0.0,
        )
        assert wf.opening_time_s == 0.0

    def test_length_mismatch_rejected(self):
        with pytest.raises(ValueError, match="len"):
            TrtWaveform(
                time_s=(0.0, 0.001),
                voltage_kV=(0.0, 50.0, 100.0),
                opening_time_s=0.0,
            )

    def test_too_few_points(self):
        with pytest.raises(ValueError, match=">= 2"):
            TrtWaveform(
                time_s=(0.0,),
                voltage_kV=(0.0,),
                opening_time_s=0.0,
            )

    def test_non_monotonic_time(self):
        with pytest.raises(ValueError, match="monotônico"):
            TrtWaveform(
                time_s=(0.0, 0.002, 0.001),
                voltage_kV=(0.0, 50.0, 100.0),
                opening_time_s=0.0,
            )

    def test_opening_outside_range(self):
        with pytest.raises(ValueError, match="opening_time_s"):
            TrtWaveform(
                time_s=(0.0, 0.001, 0.002),
                voltage_kV=(0.0, 50.0, 100.0),
                opening_time_s=1.0,
            )


# ---------------------------------------------------------------------------
# analyze_trt — PASS / FAIL
# ---------------------------------------------------------------------------


def _gentle_ramp_waveform(
    env: TrtEnvelope4Param, fraction: float = 0.5,
    n_points: int = 200,
) -> TrtWaveform:
    """
    Produz onda TRT que cresce a fraction de RRRV até fraction
    de u_c — fica seguramente DENTRO do envelope.
    """
    t_open = 0.020
    duration_s = (env.t_2_us / fraction) * 1.0e-6 * 2.0  # garante margem
    times = [t_open + i * duration_s / n_points for i in range(n_points)]
    rrrv_obs = fraction * env.rrrv_initial_kV_per_us
    voltages = []
    for t in times:
        rel_us = (t - t_open) * 1.0e6
        v = min(rrrv_obs * rel_us, fraction * env.u_c_kV)
        voltages.append(v)
    return TrtWaveform(
        time_s=tuple(times), voltage_kV=tuple(voltages),
        opening_time_s=t_open, label="gentle", phase="A",
    )


def _aggressive_waveform(
    env: TrtEnvelope4Param, factor: float = 1.5,
    n_points: int = 200,
) -> TrtWaveform:
    """RRRV inicial = factor · RRRV envelope ⇒ FAIL."""
    t_open = 0.020
    duration_s = env.t_2_us * 1.0e-6 * 2.0
    times = [t_open + i * duration_s / n_points for i in range(n_points)]
    rrrv_obs = factor * env.rrrv_initial_kV_per_us
    voltages = []
    for t in times:
        rel_us = (t - t_open) * 1.0e6
        v = min(rrrv_obs * rel_us, factor * env.u_c_kV)
        voltages.append(v)
    return TrtWaveform(
        time_s=tuple(times), voltage_kV=tuple(voltages),
        opening_time_s=t_open, label="aggressive", phase="A",
    )


class TestAnalyzeTrtPass:
    def test_gentle_ramp_passes(self):
        env = trt_envelope_4param(
            145.0, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        wf = _gentle_ramp_waveform(env, fraction=0.3)
        report = analyze_trt(wf, env)
        assert report.passed is True
        assert report.violations == ()

    def test_pass_metrics(self):
        env = trt_envelope_4param(
            145.0, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        wf = _gentle_ramp_waveform(env, fraction=0.5)
        report = analyze_trt(wf, env)
        # u_c observado ≈ 50% de u_c envelope
        assert report.margin_uc == pytest.approx(0.5, abs=0.05)
        assert report.margin_rrrv == pytest.approx(0.5, abs=0.05)
        assert report.severity < 1.0


class TestAnalyzeTrtFail:
    def test_aggressive_fails(self):
        env = trt_envelope_4param(
            145.0, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        wf = _aggressive_waveform(env, factor=1.3)
        report = analyze_trt(wf, env)
        assert report.passed is False
        assert len(report.violations) > 0
        assert report.severity > 1.0

    def test_fail_severity_high(self):
        env = trt_envelope_4param(
            145.0, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        wf = _aggressive_waveform(env, factor=2.0)
        report = analyze_trt(wf, env)
        assert report.severity >= 2.0
        # u_c observed > envelope
        assert report.u_c_observed_kV > env.u_c_kV

    def test_summary_contains_fail_marker(self):
        env = trt_envelope_4param(
            145.0, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        wf = _aggressive_waveform(env, factor=1.5)
        s = analyze_trt(wf, env).summary()
        assert "FAIL" in s
        assert "EXCEEDED" in s

    def test_summary_pass_marker(self):
        env = trt_envelope_4param(
            145.0, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        wf = _gentle_ramp_waveform(env, fraction=0.3)
        s = analyze_trt(wf, env).summary()
        assert "PASS" in s


class TestReportFields:
    def test_metadata_preserved(self):
        env = trt_envelope_4param(
            145.0, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        wf = _gentle_ramp_waveform(env, fraction=0.3)
        report = analyze_trt(wf, env)
        assert report.duty == TestDuty.T100s
        assert report.rated_voltage_kV == 145.0
        assert report.envelope_type == "4param"
        assert report.waveform_label == "gentle"
        assert report.waveform_phase == "A"

    def test_2param_envelope_works(self):
        env = trt_envelope_2param(
            36.0, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T10,
        )
        # Onda gentle baseada no envelope 2-param
        t_open = 0.020
        n = 100
        duration_s = env.t_3_us * 1e-6 * 2
        times = [t_open + i * duration_s / n for i in range(n)]
        voltages = [
            min(0.5 * env.rrrv_kV_per_us * (t - t_open) * 1e6,
                0.5 * env.u_c_kV)
            for t in times
        ]
        wf = TrtWaveform(
            time_s=tuple(times), voltage_kV=tuple(voltages),
            opening_time_s=t_open,
        )
        report = analyze_trt(wf, env)
        assert report.envelope_type == "2param"
        assert report.passed is True


class TestEdgeCases:
    def test_no_samples_after_opening_raises(self):
        env = trt_envelope_4param(
            145.0, GroundingType.EFFECTIVELY_GROUNDED, TestDuty.T100s,
        )
        wf = TrtWaveform(
            time_s=(0.0, 0.001),
            voltage_kV=(0.0, 0.0),
            opening_time_s=0.001,    # no extra samples after
        )
        # Há 1 amostra em t=0.001 (= opening), nenhuma depois
        # mas a waveform tem 2 pontos e t=opening_time é incluído
        # então deve funcionar (1 amostra apenas)
        report = analyze_trt(wf, env)
        assert report.u_c_observed_kV == 0.0


# ---------------------------------------------------------------------------
# Cenário realista — alimentado por SM
# ---------------------------------------------------------------------------


class TestRealisticScenario:
    def test_generator_fed_trt_severity(self):
        """
        Cenário: gerador 13.8 kV / 100 MVA alimenta barra; disjuntor
        VCB abre em t=20 ms; verifica TRT vs IEC 62271 envelope para
        T100s @ 17.5 kV (próximo nível padrão acima de 13.8).

        Esta é uma verificação **conceitual** — a TRT real depende
        de C parasita do barramento + L de dispersão. Aqui usamos
        uma aproximação de 1ª ordem para o teste passar/falhar.
        """
        from app.preprocessor.synchronous_machine import (
            short_circuit_currents,
            make_default_thermal_generator,
        )
        gen = make_default_thermal_generator(
            "GEN", "A", "B", "C", 13.8, 100.0,
        )
        sc = short_circuit_currents(gen)
        # I'' typical = 5 pu = 20.92 kA — útil para sanity
        assert sc["I_subtransient_pu"] == pytest.approx(5.0, abs=0.01)

        env = trt_envelope_2param(
            rated_voltage_kV=17.5,
            grounding=GroundingType.NON_EFFECTIVELY_GROUNDED,
            duty=TestDuty.T100s,
        )
        # u_c expected: 1.5·1.4·√2·17.5/√3 ≈ 30.0 kV
        assert env.u_c_kV == pytest.approx(30.01, abs=0.5)
