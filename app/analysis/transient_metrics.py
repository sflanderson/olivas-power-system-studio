"""Transient analysis metrics for ATP simulation results.

DOM-002: Basic transient metrics (peak, frequency, damping)
DOM-003: TRV and RRRV analysis for vacuum circuit breakers
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TransientMetrics:
    """Basic transient waveform metrics."""
    variable_name: str = ""
    peak_value: float = 0.0
    peak_time: float = 0.0
    min_value: float = 0.0
    min_time: float = 0.0
    rms_value: float = 0.0
    mean_value: float = 0.0
    frequency_hz: Optional[float] = None
    damping_ratio: Optional[float] = None
    settling_time: Optional[float] = None
    n_samples: int = 0


@dataclass
class TrvMetrics:
    """Transient Recovery Voltage metrics for VCB analysis."""
    peak_trv_kv: float = 0.0
    peak_trv_time_us: float = 0.0
    rrrv_kv_per_us: float = 0.0
    first_pole_clear_time_us: float = 0.0
    withstand_ok: Optional[bool] = None
    iec_uc_kv: Optional[float] = None
    iec_t3_us: Optional[float] = None


def compute_transient_metrics(
    time: list[float], values: list[float], variable_name: str = ""
) -> TransientMetrics:
    """Compute basic transient metrics from a time-domain waveform."""
    if not time or not values or len(time) != len(values):
        return TransientMetrics(variable_name=variable_name)

    n = len(values)

    # Peak and min
    peak_val = max(values)
    peak_idx = values.index(peak_val)
    min_val = min(values)
    min_idx = values.index(min_val)

    # RMS and mean
    mean_val = sum(values) / n
    rms_val = math.sqrt(sum(v * v for v in values) / n)

    metrics = TransientMetrics(
        variable_name=variable_name,
        peak_value=peak_val,
        peak_time=time[peak_idx],
        min_value=min_val,
        min_time=time[min_idx],
        rms_value=rms_val,
        mean_value=mean_val,
        n_samples=n,
    )

    # Estimate frequency from zero crossings
    crossings = _find_zero_crossings(time, values)
    if len(crossings) >= 2:
        periods = [crossings[i + 1] - crossings[i] for i in range(len(crossings) - 1)]
        avg_half_period = sum(periods) / len(periods)
        if avg_half_period > 0:
            metrics.frequency_hz = 1.0 / (2.0 * avg_half_period)

    # Estimate damping from successive peaks
    peaks = _find_peaks(values)
    if len(peaks) >= 3:
        peak_vals = [abs(values[i]) for i in peaks]
        if peak_vals[0] > 0 and peak_vals[2] > 0:
            log_dec = math.log(peak_vals[0] / peak_vals[2]) / 2.0
            if log_dec > 0:
                metrics.damping_ratio = log_dec / math.sqrt(4 * math.pi**2 + log_dec**2)

    return metrics


def compute_trv_metrics(
    time: list[float],
    voltage: list[float],
    current_zero_time: float = 0.0,
    rated_voltage_kv: Optional[float] = None,
) -> TrvMetrics:
    """Compute TRV and RRRV from voltage waveform after current zero.

    Args:
        time: Time vector (seconds)
        voltage: Voltage across breaker contacts (volts)
        current_zero_time: Time of current zero crossing (seconds)
        rated_voltage_kv: Rated voltage for IEC comparison (kV)
    """
    if not time or not voltage or len(time) != len(voltage):
        return TrvMetrics()

    # Find data after current zero
    start_idx = 0
    for i, t in enumerate(time):
        if t >= current_zero_time:
            start_idx = i
            break

    post_time = time[start_idx:]
    post_voltage = voltage[start_idx:]

    if not post_time:
        return TrvMetrics()

    # Peak TRV
    abs_voltage = [abs(v) for v in post_voltage]
    peak_idx = abs_voltage.index(max(abs_voltage))
    peak_trv_v = abs_voltage[peak_idx]
    peak_trv_time = post_time[peak_idx]

    peak_trv_kv = peak_trv_v / 1000.0
    peak_trv_time_us = (peak_trv_time - current_zero_time) * 1e6

    # RRRV: Rate of Rise of Recovery Voltage (kV/us)
    rrrv = peak_trv_kv / peak_trv_time_us if peak_trv_time_us > 0 else 0.0

    # First-pole-to-clear time: time from CZ to first significant voltage rise
    threshold = 0.1 * peak_trv_v
    fpc_time_us = 0.0
    for i, v in enumerate(post_voltage):
        if abs(v) >= threshold:
            fpc_time_us = (post_time[i] - current_zero_time) * 1e6
            break

    metrics = TrvMetrics(
        peak_trv_kv=peak_trv_kv,
        peak_trv_time_us=peak_trv_time_us,
        rrrv_kv_per_us=rrrv,
        first_pole_clear_time_us=fpc_time_us,
    )

    # IEC 62271-100 comparison if rated voltage provided
    if rated_voltage_kv is not None and rated_voltage_kv > 0:
        # Simplified IEC TRV envelope (first-pole-to-clear factor kpp=1.3)
        kpp = 1.3
        uc_kv = kpp * rated_voltage_kv * math.sqrt(2) / math.sqrt(3)
        # t3 approximation: depends on rated current, using simplified formula
        t3_us = 4.0 * uc_kv  # simplified: ~4 us/kV for T100
        metrics.iec_uc_kv = uc_kv
        metrics.iec_t3_us = t3_us
        metrics.withstand_ok = peak_trv_kv <= uc_kv

    return metrics


def format_transient_report(metrics: TransientMetrics) -> str:
    """Format transient metrics as readable text."""
    parts = [
        f"Métricas de transitório: {metrics.variable_name}",
        f"{'─' * 45}",
        f"Pico:        {metrics.peak_value:>12.4g}   em t = {metrics.peak_time:.6f} s",
        f"Mínimo:      {metrics.min_value:>12.4g}   em t = {metrics.min_time:.6f} s",
        f"RMS:         {metrics.rms_value:>12.4g}",
        f"Média:       {metrics.mean_value:>12.4g}",
        f"Amostras:    {metrics.n_samples}",
    ]
    if metrics.frequency_hz is not None:
        parts.append(f"Frequência:  {metrics.frequency_hz:>12.1f} Hz")
    if metrics.damping_ratio is not None:
        parts.append(f"Amort. (ζ):  {metrics.damping_ratio:>12.4f}")
    return "\n".join(parts)


def format_trv_report(trv: TrvMetrics) -> str:
    """Format TRV metrics as readable text."""
    parts = [
        "Análise TRV (Transient Recovery Voltage)",
        f"{'─' * 45}",
        f"Pico TRV:    {trv.peak_trv_kv:>10.2f} kV",
        f"Tempo pico:  {trv.peak_trv_time_us:>10.2f} μs",
        f"RRRV:        {trv.rrrv_kv_per_us:>10.2f} kV/μs",
        f"1° polo:     {trv.first_pole_clear_time_us:>10.2f} μs",
    ]
    if trv.iec_uc_kv is not None:
        parts.append(f"{'─' * 45}")
        parts.append(f"IEC Uc:      {trv.iec_uc_kv:>10.2f} kV")
        parts.append(f"IEC t3:      {trv.iec_t3_us:>10.2f} μs")
        status = "OK" if trv.withstand_ok else "EXCEDIDO"
        parts.append(f"Suportabilidade: {status}")
    return "\n".join(parts)


# ======================================================================
# Helpers
# ======================================================================


def _find_zero_crossings(time: list[float], values: list[float]) -> list[float]:
    """Find times where signal crosses zero (linear interpolation)."""
    crossings: list[float] = []
    for i in range(len(values) - 1):
        if values[i] * values[i + 1] < 0:
            # Linear interpolation
            dt = time[i + 1] - time[i]
            dv = values[i + 1] - values[i]
            if dv != 0:
                t_cross = time[i] - values[i] * dt / dv
                crossings.append(t_cross)
    return crossings


def _find_peaks(values: list[float]) -> list[int]:
    """Find indices of local maxima (absolute value)."""
    peaks: list[int] = []
    for i in range(1, len(values) - 1):
        if abs(values[i]) > abs(values[i - 1]) and abs(values[i]) > abs(values[i + 1]):
            peaks.append(i)
    return peaks
