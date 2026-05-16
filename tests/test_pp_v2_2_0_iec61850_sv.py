"""
tests/test_pp_v2_2_0_iec61850_sv.py — v2.2.0 Sprint B.

Cobre IEC 61850-9-2 Sample Values:

* SVStream dataclass + SVConfig
* Synthetic 60Hz waveform generator (Iarms / Vrms)
* Sample rate: 80 samples/cycle (4800/s a 60Hz)
* Sample rate: 256 samples/cycle (15360/s) — high-precision protection
"""

from __future__ import annotations

import math

import pytest


class TestSVConfig:

    def test_module_loadable(self):
        from app.integration import iec61850_sv  # noqa: F401

    def test_sv_config_dataclass(self):
        from app.integration.iec61850_sv import SVConfig
        cfg = SVConfig(
            sv_id="DEMO/MEAS_MUT/V_RMS",
            samples_per_cycle=80,
            frequency_hz=60.0,
            mode="stub",
        )
        assert cfg.sv_id == "DEMO/MEAS_MUT/V_RMS"
        assert cfg.samples_per_cycle == 80

    def test_sv_config_sample_rate_hz(self):
        """80 sps × 60 Hz = 4800 Hz."""
        from app.integration.iec61850_sv import SVConfig
        cfg = SVConfig(
            sv_id="X", samples_per_cycle=80,
            frequency_hz=60.0, mode="stub",
        )
        assert cfg.sample_rate_hz == 4800.0

    def test_sv_config_protection_rate(self):
        """256 sps × 60 Hz = 15360 Hz (proteção)."""
        from app.integration.iec61850_sv import SVConfig
        cfg = SVConfig(
            sv_id="X", samples_per_cycle=256,
            frequency_hz=60.0, mode="stub",
        )
        assert cfg.sample_rate_hz == 15360.0


class TestSVPublisherStub:

    def test_publisher_loadable(self):
        from app.integration.iec61850_sv import SVPublisher
        assert SVPublisher is not None

    def test_publisher_generates_n_samples(self):
        from app.integration.iec61850_sv import SVConfig, SVPublisher
        cfg = SVConfig(
            sv_id="X", samples_per_cycle=80,
            frequency_hz=60.0, mode="stub",
        )
        pub = SVPublisher(cfg, amplitude=120.0)
        # Solicita 1 ciclo completo = 80 amostras
        stream = pub.generate_stream(num_samples=80)
        assert len(stream.samples) == 80
        # SmpCnt monotonicamente crescente
        sample_cnts = [s.smp_cnt for s in stream.samples]
        assert sample_cnts == sorted(sample_cnts)

    def test_synthetic_waveform_amplitude(self):
        """Amostras devem ficar entre [-A, +A] aprox (sinusoide)."""
        from app.integration.iec61850_sv import SVConfig, SVPublisher
        cfg = SVConfig(
            sv_id="X", samples_per_cycle=80,
            frequency_hz=60.0, mode="stub",
        )
        amp = 100.0
        pub = SVPublisher(cfg, amplitude=amp)
        stream = pub.generate_stream(num_samples=80)
        values = [s.value for s in stream.samples]
        # Pico deve estar próximo de ±A
        assert max(values) <= amp * 1.01
        assert min(values) >= -amp * 1.01
        # Pico deve estar perto de A em pelo menos algum sample
        assert max(values) > amp * 0.95

    def test_synthetic_waveform_60hz_period(self):
        """80 samples × 60Hz = 1 ciclo completo: cruza zero ~80 vezes/s."""
        from app.integration.iec61850_sv import SVConfig, SVPublisher
        cfg = SVConfig(
            sv_id="X", samples_per_cycle=80,
            frequency_hz=60.0, mode="stub",
        )
        pub = SVPublisher(cfg, amplitude=100.0)
        stream = pub.generate_stream(num_samples=80)
        # Em 1 ciclo: 2 zero-crossings (subida + descida)
        zero_crossings = 0
        prev = stream.samples[0].value
        for s in stream.samples[1:]:
            if (prev < 0 and s.value >= 0) or (prev >= 0 and s.value < 0):
                zero_crossings += 1
            prev = s.value
        assert 1 <= zero_crossings <= 3  # 2 esperado, ±1 tolerância


class TestSVRealMode:

    def test_real_mode_raises_without_lib(self):
        from app.integration.iec61850_sv import SVConfig, SVPublisher
        cfg = SVConfig(
            sv_id="X", samples_per_cycle=80,
            frequency_hz=60.0, mode="real",
        )
        pub = SVPublisher(cfg, amplitude=100.0)
        with pytest.raises((NotImplementedError, ImportError, Exception)):
            pub.generate_stream(num_samples=10)
