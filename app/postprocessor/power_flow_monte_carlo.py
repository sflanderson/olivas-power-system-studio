"""
app.postprocessor.power_flow_monte_carlo — análise Monte
Carlo de sensibilidade para Power Flow (v0.80).

Motivação
==========

PF determinístico assume cargas P, Q EXATAS. Real:

* **Cargas variam ±20-40%** ao longo do dia (carga base
  vs pico).
* **Cargas reativas** (Q) muito mais incertas que ativas
  (depende do FP do equipamento).
* **Topologia** pode ter chaves abertas/fechadas (cenários
  N-1).

Monte Carlo amostra cargas conforme distribuições e
calcula:

* Distribuição de V_min, V_max ao longo do horizonte
  operacional.
* Probabilidade de violação (V < 0.95 ou > 1.05 pu).
* Distribuição de perdas P+Q.
* Conjunto de "piores casos" (worst-case envelope).

API
====

::

    from app.postprocessor.power_flow_monte_carlo import (
        PfUncertainty, run_pf_monte_carlo,
    )

    sys = PowerFlowSystem()
    sys.add_slack(...)
    sys.add_pq(...)
    ...
    uncertainty = PfUncertainty(
        load_P_cv_pct=20.0,
        load_Q_cv_pct=30.0,
    )
    result = run_pf_monte_carlo(
        sys, uncertainty, n_samples=500,
    )
    print(result.summary())
    # P50 V_min: 0.96, P5 V_min: 0.93, violation_prob: 4%

Distribuição default: NORMAL truncada (CV variável).

Limitação:
* Topologia fixa (N-1 ainda em backlog).
* Sem correlação entre cargas (independência assumida).
"""

from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass
from typing import Optional

from app.commercial.feature_gates import Feature, requires_feature


@dataclass(frozen=True)
class PfUncertainty:
    """
    Especificação de incertezas para Monte Carlo PF.

    Attributes
    ----------
    load_P_cv_pct:
        CV (σ/μ) da carga ativa P em cada bus PQ.
        Default 20% (variação dia-noite típica).
    load_Q_cv_pct:
        CV da carga reativa Q.
        Default 30% (mais incerto que P).
    voltage_setpoint_cv_pct:
        CV da tensão setpoint dos buses PV/SLACK.
        Default 1% (regulação ±1%).
    """
    load_P_cv_pct: float = 20.0
    load_Q_cv_pct: float = 30.0
    voltage_setpoint_cv_pct: float = 1.0


@dataclass(frozen=True)
class PfMonteCarloResult:
    """
    Resultado de Monte Carlo PF.

    Attributes
    ----------
    n_samples:
        Amostras válidas.
    n_invalid:
        Amostras com PF não-convergente.
    voltages_min_pu:
        V_min de cada amostra (lista).
    voltages_max_pu:
        V_max de cada amostra.
    losses_P_pu:
        Perda P de cada amostra.
    P50_V_min / P5_V_min:
        Mediana e P5 do V_min.
    violation_prob_under_voltage:
        P(V_min < 0.95).
    violation_prob_over_voltage:
        P(V_max > 1.05).
    """
    n_samples: int
    n_invalid: int
    voltages_min_pu: tuple
    voltages_max_pu: tuple
    losses_P_pu: tuple
    P50_V_min: float
    P5_V_min: float
    P95_V_max: float
    P50_losses: float
    violation_prob_under_voltage: float
    violation_prob_over_voltage: float

    def summary(self) -> str:
        lines = [
            "=" * 60,
            "Monte Carlo Power Flow Sensitivity",
            "=" * 60,
            f"Samples: {self.n_samples} convergiram, "
            f"{self.n_invalid} não-convergentes",
            "",
            "Tensão MÍNIMA do sistema:",
            f"  P50 V_min = {self.P50_V_min:.4f} pu",
            f"  P5  V_min = {self.P5_V_min:.4f} pu",
            f"  P(V_min < 0.95) = "
            f"{self.violation_prob_under_voltage*100:.2f}%",
            "",
            "Tensão MÁXIMA do sistema:",
            f"  P95 V_max = {self.P95_V_max:.4f} pu",
            f"  P(V_max > 1.05) = "
            f"{self.violation_prob_over_voltage*100:.2f}%",
            "",
            "Perdas:",
            f"  P50 losses = {self.P50_losses:.4f} pu",
        ]
        return "\n".join(lines)


def _percentile(samples: list, p: float) -> float:
    if not samples:
        return 0.0
    sorted_s = sorted(samples)
    k = (len(sorted_s) - 1) * (p / 100.0)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return sorted_s[int(k)]
    return sorted_s[lo] + (k - lo) * (sorted_s[hi] - sorted_s[lo])


def _sample_normal_truncated(
    mean: float, sigma: float, rng: random.Random,
    *, max_attempts: int = 50,
) -> float:
    """
    Sample normal sem clip de sinal (cargas P podem ser
    positivas ou negativas: P>0 = injection, P<0 = consumption).
    Para CV, σ = |mean| × CV.
    """
    return rng.gauss(mean, sigma)


@requires_feature(Feature.POWER_FLOW_MC)
def run_pf_monte_carlo(
    pf_system,    # PowerFlowSystem
    uncertainty: PfUncertainty,
    n_samples: int = 500,
    *,
    random_seed: Optional[int] = None,
    tolerance: float = 1.0e-6,
    max_iterations: int = 50,
) -> PfMonteCarloResult:
    """
    Executa MC sampling cargas, recalculando PF para cada.

    Parameters
    ----------
    pf_system:
        ``PowerFlowSystem`` configurado (slack + PV + PQ + branches).
    uncertainty:
        ``PfUncertainty`` com CVs.
    n_samples:
        Default 500.
    random_seed:
        Reproducibilidade.

    Returns
    -------
    PfMonteCarloResult
    """
    from app.postprocessor.power_flow import (
        BusType, PfBus, solve_power_flow,
    )

    rng = random.Random(random_seed)

    # Salva originais (P_pu_set, Q_pu_set, V_pu_set)
    original_loads = []
    for b in pf_system.buses:
        original_loads.append((b.P_pu_set, b.Q_pu_set, b.V_pu_set))

    voltages_min: list[float] = []
    voltages_max: list[float] = []
    losses_P: list[float] = []
    n_invalid = 0

    for _ in range(n_samples):
        # Sample novas cargas
        for i, b in enumerate(pf_system.buses):
            P0, Q0, V0 = original_loads[i]
            if b.type == BusType.PQ:
                # Sample P e Q
                if uncertainty.load_P_cv_pct > 0 and abs(P0) > 1e-9:
                    sigma_P = abs(P0) * uncertainty.load_P_cv_pct / 100.0
                    b.P_pu_set = _sample_normal_truncated(P0, sigma_P, rng)
                if uncertainty.load_Q_cv_pct > 0 and abs(Q0) > 1e-9:
                    sigma_Q = abs(Q0) * uncertainty.load_Q_cv_pct / 100.0
                    b.Q_pu_set = _sample_normal_truncated(Q0, sigma_Q, rng)
            elif b.type in (BusType.PV, BusType.SLACK):
                # Sample V setpoint
                if uncertainty.voltage_setpoint_cv_pct > 0:
                    sigma_V = V0 * uncertainty.voltage_setpoint_cv_pct / 100
                    new_V = _sample_normal_truncated(V0, sigma_V, rng)
                    if 0.5 < new_V < 1.5:
                        b.V_pu_set = new_V

        # Resolve PF
        try:
            sol = solve_power_flow(
                pf_system.buses, pf_system.branches,
                tolerance=tolerance, max_iterations=max_iterations,
            )
            if not sol.converged:
                n_invalid += 1
                continue
            voltages = [abs(v) for v in sol.bus_voltages_pu.values()]
            voltages_min.append(min(voltages))
            voltages_max.append(max(voltages))
            losses_P.append(sol.total_losses_pu.real)
        except (ValueError, ZeroDivisionError, ArithmeticError):
            n_invalid += 1

    # Restaura originais (não vaza side-effect)
    for i, b in enumerate(pf_system.buses):
        b.P_pu_set, b.Q_pu_set, b.V_pu_set = original_loads[i]

    if not voltages_min:
        return PfMonteCarloResult(
            n_samples=0, n_invalid=n_invalid,
            voltages_min_pu=(), voltages_max_pu=(),
            losses_P_pu=(),
            P50_V_min=0.0, P5_V_min=0.0,
            P95_V_max=0.0, P50_losses=0.0,
            violation_prob_under_voltage=0.0,
            violation_prob_over_voltage=0.0,
        )

    P50_v_min = _percentile(voltages_min, 50.0)
    P5_v_min = _percentile(voltages_min, 5.0)
    P95_v_max = _percentile(voltages_max, 95.0)
    P50_losses = _percentile(losses_P, 50.0)

    n = len(voltages_min)
    n_under = sum(1 for v in voltages_min if v < 0.95)
    n_over = sum(1 for v in voltages_max if v > 1.05)
    prob_under = n_under / n if n > 0 else 0.0
    prob_over = n_over / n if n > 0 else 0.0

    return PfMonteCarloResult(
        n_samples=n,
        n_invalid=n_invalid,
        voltages_min_pu=tuple(voltages_min),
        voltages_max_pu=tuple(voltages_max),
        losses_P_pu=tuple(losses_P),
        P50_V_min=P50_v_min,
        P5_V_min=P5_v_min,
        P95_V_max=P95_v_max,
        P50_losses=P50_losses,
        violation_prob_under_voltage=prob_under,
        violation_prob_over_voltage=prob_over,
    )
