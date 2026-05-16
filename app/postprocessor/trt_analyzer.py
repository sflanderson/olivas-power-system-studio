"""
app.postprocessor.trt_analyzer — análise de TRT (Transient
Recovery Voltage) vs envelopes IEC 62271-100.

Fluxo de uso
============

::

    from app.postprocessor.trt_analyzer import (
        TrtWaveform, analyze_trt,
    )
    from app.standards.iec62271 import (
        GroundingType, TestDuty, trt_envelope_4param,
    )

    # Onda TRT da simulação (vinda do PL4 ou gerada)
    waveform = TrtWaveform(
        time_s=[...],   # tempos absolutos
        voltage_kV=[...],  # tensões correspondentes
        opening_time_s=0.020,  # instante da abertura
    )

    # Envelope de referência da norma
    env = trt_envelope_4param(
        rated_voltage_kV=145.0,
        grounding=GroundingType.EFFECTIVELY_GROUNDED,
        duty=TestDuty.T100s,
    )

    # Análise + relatório
    report = analyze_trt(waveform, env)
    print(report.summary())  # PASS / FAIL + métricas

Métricas calculadas
====================

* **u_c_observed**: tensão de pico real (kV).
* **t_to_peak_us**: tempo de pico relativo à abertura (μs).
* **rrrv_max_kV_per_us**: máxima du/dt observada nos primeiros
  μs após abertura.
* **margin_uc**: ``u_c_observed / u_c_envelope`` (>1 = falha).
* **margin_rrrv**: ``rrrv_observed / rrrv_envelope``.
* **violation_points**: lista de ``(t, v_obs, v_env)`` onde a
  TRT excedeu o envelope.

Resultado
=========

* ``PASS``: nenhum ponto da TRT excede o envelope; todas as
  margens < 1.0.
* ``FAIL``: pelo menos um ponto excede ⇒ disjuntor inadequado
  (re-acendimento provável); recomenda-se re-coordenação.

Implementação MVP v0.27.1
==========================

Aceita waveform como pares ``(time, voltage)`` puros — não exige
PL4 reader (esse virá em v0.27.1.5). Caller pode produzir a
waveform via:

* Simulação ATP (rodar TPBIG, ler PL4 quando reader pronto).
* Análise sintética (formulas analíticas para cenários
  benchmark).
* Cálculo de circuito LC equivalente (TRT ≈ ω·L·I_pp em t=0
  para curto bem-localizado).

Referências
============

* IEC 62271-100:2021 §6.102.10 (Test duties).
* IEC 62271-200:2021 (medium-voltage switchgear).
* CIGRE TB 304 (TRT in electrical systems).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

from app.standards.iec62271 import (
    TestDuty, TrtEnvelope2Param, TrtEnvelope4Param,
)


# ---------------------------------------------------------------------------
# Waveform de entrada
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrtWaveform:
    """
    Onda TRT de entrada para análise.

    Convenção
    ---------

    * ``time_s``: monotônico crescente, em segundos absolutos da
      simulação.
    * ``voltage_kV``: tensão entre os terminais do disjuntor —
      preferencialmente a fase mais carregada.
    * ``opening_time_s``: instante exato da abertura (cruzamento
      de zero da corrente). Tempos relativos pré-abertura geram
      ruído na TRT — análise usa apenas t > opening_time_s.

    Validação automática:

    * ``len(time_s) == len(voltage_kV)``.
    * ``opening_time_s`` dentro do range.
    * tempos monotônicos.

    Attributes
    ----------
    time_s, voltage_kV:
        Vetores paralelos (tuple para frozen).
    opening_time_s:
        Instante da abertura (s).
    label:
        Identificação textual (para o relatório).
    phase:
        Identificador da fase (A/B/C/N).
    """

    time_s: tuple[float, ...]
    voltage_kV: tuple[float, ...]
    opening_time_s: float
    label: str = ""
    phase: str = ""

    def __post_init__(self) -> None:
        if len(self.time_s) != len(self.voltage_kV):
            raise ValueError(
                f"len(time_s)={len(self.time_s)} != "
                f"len(voltage_kV)={len(self.voltage_kV)}"
            )
        if len(self.time_s) < 2:
            raise ValueError("waveform precisa de >= 2 pontos")
        # Monotônico crescente
        for i in range(len(self.time_s) - 1):
            if self.time_s[i + 1] < self.time_s[i]:
                raise ValueError(
                    f"time_s não-monotônico em i={i+1}: "
                    f"{self.time_s[i+1]} < {self.time_s[i]}"
                )
        if not (self.time_s[0] <= self.opening_time_s <= self.time_s[-1]):
            raise ValueError(
                f"opening_time_s={self.opening_time_s} fora "
                f"do range [{self.time_s[0]}, {self.time_s[-1]}]"
            )


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrtViolation:
    """Ponto onde a TRT observada excedeu o envelope."""
    t_us: float           # tempo relativo à abertura (μs)
    v_observed_kV: float
    v_envelope_kV: float
    margin: float         # v_observed / v_envelope (>1 = excede)


@dataclass(frozen=True)
class TrtAnalysisReport:
    """
    Relatório completo de análise TRT.

    Aproveita a tipagem rica de ``TestDuty`` e refere-se ao
    envelope original (mantido por referência na metadata).
    """

    # Resultado primário
    passed: bool
    violations: tuple[TrtViolation, ...]

    # Métricas observadas
    u_c_observed_kV: float
    t_to_peak_us: float
    rrrv_max_kV_per_us: float

    # Métricas do envelope (para comparação)
    u_c_envelope_kV: float
    rrrv_envelope_kV_per_us: float

    # Margens
    margin_uc: float          # u_obs / u_env
    margin_rrrv: float        # rrrv_obs / rrrv_env

    # Metadata
    duty: TestDuty
    rated_voltage_kV: float
    envelope_type: str        # "2param" ou "4param"
    waveform_label: str
    waveform_phase: str
    source: str = "IEC 62271-100:2021"

    # Severity score: max(margin_uc, margin_rrrv) — quanto > 1, mais grave.
    @property
    def severity(self) -> float:
        return max(self.margin_uc, self.margin_rrrv)

    def summary(self) -> str:
        """Sumário 1-página do relatório (texto plano)."""
        status = "PASS ✓" if self.passed else "FAIL ✗"
        lines = [
            f"=== TRT Analysis Report — {status} ===",
            f"Source: {self.source}",
            f"Duty: {self.duty.value}, U_r = {self.rated_voltage_kV} kV, "
            f"envelope = {self.envelope_type}",
            f"Phase: {self.waveform_phase or 'N/A'}, "
            f"Label: {self.waveform_label or 'N/A'}",
            "",
            "--- Observed ---",
            f"  u_c = {self.u_c_observed_kV:.3f} kV "
            f"@ t = {self.t_to_peak_us:.1f} μs",
            f"  RRRV (max) = {self.rrrv_max_kV_per_us:.3f} kV/μs",
            "",
            "--- Envelope (reference) ---",
            f"  u_c = {self.u_c_envelope_kV:.3f} kV",
            f"  RRRV = {self.rrrv_envelope_kV_per_us:.3f} kV/μs",
            "",
            "--- Margins ---",
            f"  u_c   margin = {self.margin_uc:.3f} "
            f"({'OK' if self.margin_uc <= 1.0 else 'EXCEEDED'})",
            f"  RRRV  margin = {self.margin_rrrv:.3f} "
            f"({'OK' if self.margin_rrrv <= 1.0 else 'EXCEEDED'})",
            f"  Severity (overall) = {self.severity:.3f}",
        ]
        if self.violations:
            lines.append("")
            lines.append(f"--- Violations ({len(self.violations)}) ---")
            for v in self.violations[:10]:
                lines.append(
                    f"  @ t={v.t_us:.2f} μs: "
                    f"observed={v.v_observed_kV:.3f} kV, "
                    f"envelope={v.v_envelope_kV:.3f} kV, "
                    f"margin={v.margin:.3f}"
                )
            if len(self.violations) > 10:
                lines.append(
                    f"  ... e mais {len(self.violations) - 10} pontos"
                )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Núcleo da análise
# ---------------------------------------------------------------------------


Envelope = Union[TrtEnvelope2Param, TrtEnvelope4Param]


def _samples_after_opening(
    waveform: TrtWaveform,
) -> list[tuple[float, float]]:
    """
    Retorna pares ``(t_us_relative, v_kV)`` para amostras com
    ``t > opening_time``. ``t_us_relative`` em μs desde a abertura.
    """
    t0 = waveform.opening_time_s
    samples: list[tuple[float, float]] = []
    for t, v in zip(waveform.time_s, waveform.voltage_kV):
        if t < t0:
            continue
        samples.append(((t - t0) * 1.0e6, v))
    return samples


def _moving_average_filter(
    samples: list[tuple[float, float]], window: int = 5,
) -> list[tuple[float, float]]:
    """
    Filtro digital simples (média móvel central) para
    atenuar ruído numérico do PL4 antes de calcular RRRV.

    Para waveform com 100k pontos e ruído da ordem de
    1% do pico, window=5-9 é adequado. Window=1 desativa.

    v0.28.1: substitui RRRV calculado em sinal cru por
    versão filtrada por padrão.
    """
    if window <= 1 or len(samples) < window:
        return samples
    half = window // 2
    filtered: list[tuple[float, float]] = []
    for i in range(len(samples)):
        lo = max(0, i - half)
        hi = min(len(samples), i + half + 1)
        avg = sum(s[1] for s in samples[lo:hi]) / (hi - lo)
        filtered.append((samples[i][0], avg))
    return filtered


def _compute_max_rrrv(
    samples: list[tuple[float, float]],
    *,
    window_us: float | None = None,
    consider_negative_slope: bool = True,
    filter_window: int = 5,
) -> float:
    """
    Calcula RRRV máximo observado (kV/μs).

    v0.28.1 — três melhorias profissionais:

    * **Janela temporal** (``window_us``): restringe cálculo
      aos primeiros N μs após abertura, conforme IEC
      62271-100 §6.111.4 (RRRV = u_c / t_3 para 2-param,
      ou u_1 / t_1 para 4-param). Default ``None`` = sem
      restrição (compatibilidade backward).
    * **Slope negativo** (``consider_negative_slope=True``):
      considera ``|slope|`` — TRT real pode ter slope
      negativo significativo após o pico (oscilação pole-
      to-pole), que MVP ignorava.
    * **Filtro digital** (``filter_window=5`` média móvel):
      atenua ruído numérico do PL4 que poderia inflar
      RRRV artificialmente.

    Parameters
    ----------
    samples:
        Lista de (t_us, v_kV) pós-abertura.
    window_us:
        Se fornecido, considera apenas amostras com
        ``t <= window_us``.
    consider_negative_slope:
        Se True, max sobre ``|slope|``; se False, apenas
        slope > 0 (comportamento MVP).
    filter_window:
        Tamanho da janela do filtro de média móvel (1 desliga).

    Returns
    -------
    float
        max RRRV (kV/μs).
    """
    # Filtro digital
    filtered = _moving_average_filter(samples, window=filter_window)

    # Janela temporal
    if window_us is not None:
        filtered = [(t, v) for t, v in filtered if t <= window_us]

    max_rrrv = 0.0
    for i in range(len(filtered) - 1):
        t1, v1 = filtered[i]
        t2, v2 = filtered[i + 1]
        dt = t2 - t1
        if dt <= 0:
            continue
        slope = (v2 - v1) / dt
        candidate = abs(slope) if consider_negative_slope else max(slope, 0)
        if candidate > max_rrrv:
            max_rrrv = candidate
    return max_rrrv


def _envelope_uc_and_rrrv(env: Envelope) -> tuple[float, float]:
    """Retorna (u_c, rrrv_ref) do envelope — distingue 2/4 param."""
    if isinstance(env, TrtEnvelope4Param):
        return env.u_c_kV, env.rrrv_initial_kV_per_us
    if isinstance(env, TrtEnvelope2Param):
        return env.u_c_kV, env.rrrv_kV_per_us
    raise TypeError(f"Envelope desconhecido: {type(env)}")


def analyze_trt(
    waveform: TrtWaveform, envelope: Envelope,
    *,
    rrrv_window_us: float | None = None,
    rrrv_filter_window: int = 5,
    rrrv_consider_negative_slope: bool = True,
) -> TrtAnalysisReport:
    """
    Compara a waveform TRT contra o envelope da norma e produz
    relatório PASS/FAIL com métricas e violações.

    Algoritmo:

    1. Filtra amostras pós-abertura.
    2. Para cada amostra (t, v_obs), calcula v_env(t) via
       ``envelope.voltage_at(t)``. Considera **valores absolutos**
       (TRT pode ser positiva ou negativa).
    3. Acumula violações: ponto onde |v_obs| > |v_env|.
    4. Métricas: u_c_obs (max abs), t_to_peak, RRRV_max (slope max).
    5. Margens: u_c_obs / u_c_env, RRRV_obs / RRRV_env.
    6. PASS se ambas margens ≤ 1.0 e violations == 0.

    Parameters
    ----------
    waveform:
        Forma de onda TRT amostrada.
    envelope:
        Envelope da norma (2 ou 4 parâmetros).
    rrrv_window_us:
        v0.28.1: janela temporal (μs) para cálculo de RRRV.
        Default None = sem restrição. IEC 62271-100 §6.111.4
        sugere t_3 (2-param) ou t_1 (4-param) como janela.
    rrrv_filter_window:
        v0.28.1: tamanho da janela de média móvel para
        atenuar ruído numérico (default 5; 1 desativa).
    rrrv_consider_negative_slope:
        v0.28.1: se True (default), considera ``|slope|`` para
        capturar oscilação pole-to-pole. Se False, apenas
        slope > 0 (comportamento MVP).

    Notas
    -----

    * O envelope é simétrico (define o módulo); por isso usamos
      ``abs(v_obs)`` na comparação.
    * Test duties ``T100a`` (asimétrica) podem ter pico negativo
      maior — ainda dentro do envelope absoluto.

    Returns
    -------
    TrtAnalysisReport
    """
    samples = _samples_after_opening(waveform)
    if not samples:
        raise ValueError(
            "waveform sem amostras pós-abertura — "
            "verifique opening_time_s"
        )

    envelope_type = "4param" if isinstance(env := envelope, TrtEnvelope4Param) else "2param"
    u_c_env, rrrv_env = _envelope_uc_and_rrrv(envelope)

    # Métricas observadas
    u_c_obs = 0.0
    t_to_peak_us = 0.0
    for t, v in samples:
        v_abs = abs(v)
        if v_abs > u_c_obs:
            u_c_obs = v_abs
            t_to_peak_us = t
    rrrv_obs = _compute_max_rrrv(
        samples,
        window_us=rrrv_window_us,
        consider_negative_slope=rrrv_consider_negative_slope,
        filter_window=rrrv_filter_window,
    )

    # Violations
    violations: list[TrtViolation] = []
    for t, v in samples:
        v_abs = abs(v)
        v_env = envelope.voltage_at(t)
        if v_env <= 0:
            continue
        if v_abs > v_env:
            violations.append(TrtViolation(
                t_us=t,
                v_observed_kV=v,
                v_envelope_kV=v_env,
                margin=v_abs / v_env,
            ))

    margin_uc = u_c_obs / u_c_env if u_c_env > 0 else float("inf")
    margin_rrrv = rrrv_obs / rrrv_env if rrrv_env > 0 else float("inf")
    passed = (
        len(violations) == 0
        and margin_uc <= 1.0
        and margin_rrrv <= 1.0
    )

    return TrtAnalysisReport(
        passed=passed,
        violations=tuple(violations),
        u_c_observed_kV=u_c_obs,
        t_to_peak_us=t_to_peak_us,
        rrrv_max_kV_per_us=rrrv_obs,
        u_c_envelope_kV=u_c_env,
        rrrv_envelope_kV_per_us=rrrv_env,
        margin_uc=margin_uc,
        margin_rrrv=margin_rrrv,
        duty=envelope.duty,
        rated_voltage_kV=envelope.rated_voltage_kV,
        envelope_type=envelope_type,
        waveform_label=waveform.label,
        waveform_phase=waveform.phase,
    )
