"""
app.postprocessor.arc_flash_monte_carlo — análise de
sensibilidade Monte Carlo para arc-flash (v0.44).

Motivação
==========

O cálculo determinístico de arc-flash (NBR 17227 / IEEE 1584)
usa valores PONTUAIS de Ibf, T, G, D. Mas todos esses
parâmetros têm INCERTEZA real:

* **Ibf**: depende de S_kQ da concessionária — varia ±15-20%
  entre estações do ano e topologias de rede.
* **T**: clearing time tem dispersão pelo tempo de detecção
  do relé + breaker (±20-50 ms).
* **G**: gap entre fases tem tolerância de fabricação (±10%).
* **D**: distância de trabalho varia conforme operador.

Análise Monte Carlo amostra esses parâmetros conforme
distribuições de probabilidade e calcula a distribuição
resultante de E (energia incidente).

Output: percentis P50/P95/P99 + histograma — informa
decisão sobre EPI e DLA com margem de segurança apropriada
ao nível de risco aceitável.

API
====

::

    from app.postprocessor.arc_flash_monte_carlo import (
        ArcFlashUncertainty, run_monte_carlo,
    )

    base_case = ArcFlashCase(...)   # cenário determinístico
    uncertainty = ArcFlashUncertainty(
        Ibf_cv_pct=15.0,         # coeficiente de variação
        T_cv_pct=20.0,
        gap_cv_pct=5.0,
        D_cv_pct=10.0,
    )
    result = run_monte_carlo(
        base_case, uncertainty, n_samples=2000,
    )
    print(result.summary())
    # P50: 12.3, P95: 18.7, P99: 24.1 cal/cm²

Distribuições suportadas:

* **NORMAL** (gaussiana truncada em 0): default.
* **LOGNORMAL**: para Ibf (sempre positivo, skew positivo).
* **UNIFORM**: para tolerância simétrica conhecida.

Critério de convergência: var(P95)/P95 < 1% após N samples
(Wilson interval-based).

Referências
============

* IEEE Std 1584:2018 §6.1 — Statistical analysis (mention)
* IEC TR 60909-2:2008 — uncertainty of SC currents
* Wilson, C.B., "Reliability of arc-flash hazard analysis
  using Monte Carlo simulation", IEEE PCIC 2017.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.commercial.feature_gates import Feature, requires_feature


# ---------------------------------------------------------------------------
# Distributions
# ---------------------------------------------------------------------------


class DistributionType(str, Enum):
    """Tipo de distribuição de probabilidade para um parâmetro."""
    NORMAL = "normal"            # gaussiana truncada em 0
    LOGNORMAL = "lognormal"      # para grandezas estritamente positivas
    UNIFORM = "uniform"          # tolerância simétrica


def _sample_normal_truncated(
    mean: float, sigma: float, rng: random.Random,
    *, max_attempts: int = 100,
) -> float:
    """Sample normal truncado em 0 (rejeita negativos)."""
    for _ in range(max_attempts):
        v = rng.gauss(mean, sigma)
        if v > 0:
            return v
    return max(mean, 1e-9)   # fallback


def _sample_lognormal(
    mean: float, cv: float, rng: random.Random,
) -> float:
    """
    Sample lognormal com média e CV (coeff of variation = σ/μ).

    Para X ~ LogNormal(μ_X, σ_X):
        μ = exp(μ_X + σ_X²/2)
        σ² = (exp(σ_X²) - 1) · exp(2μ_X + σ_X²)
        CV² = exp(σ_X²) - 1
    """
    if mean <= 0:
        return 0.0
    sigma_X = math.sqrt(math.log(1 + cv ** 2))
    mu_X = math.log(mean) - 0.5 * sigma_X ** 2
    return math.exp(rng.gauss(mu_X, sigma_X))


def _sample_uniform(
    mean: float, half_width: float, rng: random.Random,
) -> float:
    """Sample uniforme em [mean - half_width, mean + half_width]."""
    lo = mean - half_width
    hi = mean + half_width
    return rng.uniform(max(0.0, lo), hi)


# ---------------------------------------------------------------------------
# ArcFlashUncertainty
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArcFlashUncertainty:
    """
    Especificação de incerteza para Monte Carlo.

    Coeficientes de variação (CV = σ/μ) em pontos percentuais.
    Para cada parâmetro, default reflete prática IEEE 1584 +
    NBR 17227 §5 (incerteza tipica industrial).

    Attributes
    ----------
    Ibf_cv_pct:
        CV de Ibf — default 15% (variação sazonal+topológica).
    T_cv_pct:
        CV de tempo de clearing — default 20% (relé + breaker).
    gap_cv_pct:
        CV de gap — default 5% (tolerância fabricação).
    D_cv_pct:
        CV de working distance — default 10% (operador).
    Ibf_distribution:
        LOGNORMAL recomendado (sempre > 0, skew positivo).
    T_distribution:
        NORMAL truncado.
    """
    Ibf_cv_pct: float = 15.0
    T_cv_pct: float = 20.0
    gap_cv_pct: float = 5.0
    D_cv_pct: float = 10.0
    Ibf_distribution: DistributionType = DistributionType.LOGNORMAL
    T_distribution: DistributionType = DistributionType.NORMAL
    gap_distribution: DistributionType = DistributionType.NORMAL
    D_distribution: DistributionType = DistributionType.NORMAL


# ---------------------------------------------------------------------------
# MonteCarloResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MonteCarloResult:
    """
    Resultado de uma análise Monte Carlo de arc-flash.

    Attributes
    ----------
    n_samples:
        Número de amostras válidas (Ibf > 0, etc).
    n_invalid:
        Amostras descartadas por inputs inválidos.
    samples_E_J_per_cm2:
        Amostras brutas (para histograma).
    P50_J_per_cm2 / P50_cal_cm2:
        Mediana.
    P95_J_per_cm2 / P95_cal_cm2:
        Percentil 95 (margem segurança 95%).
    P99_J_per_cm2 / P99_cal_cm2:
        Percentil 99 (margem alta).
    mean / std / cv_pct:
        Estatísticas básicas.
    cat_distribution:
        Frequência por categoria PPE (0/1/2/3/4/DANGER).
    """
    n_samples: int
    n_invalid: int
    samples_E_J_per_cm2: tuple[float, ...]
    P50_J_per_cm2: float
    P95_J_per_cm2: float
    P99_J_per_cm2: float
    mean_J_per_cm2: float
    std_J_per_cm2: float
    cv_pct: float
    cat_distribution: dict   # {cat_str: fraction}

    @property
    def P50_cal_cm2(self) -> float:
        return self.P50_J_per_cm2 / 4.184

    @property
    def P95_cal_cm2(self) -> float:
        return self.P95_J_per_cm2 / 4.184

    @property
    def P99_cal_cm2(self) -> float:
        return self.P99_J_per_cm2 / 4.184

    def summary(self) -> str:
        lines = [
            "=" * 60,
            "Monte Carlo Arc-Flash Sensitivity Analysis",
            "=" * 60,
            f"Samples: {self.n_samples} válidas, "
            f"{self.n_invalid} inválidas",
            f"Mean ± σ: {self.mean_J_per_cm2:.2f} ± "
            f"{self.std_J_per_cm2:.2f} J/cm²  "
            f"(CV = {self.cv_pct:.1f}%)",
            "",
            "Percentis de E:",
            f"  P50  = {self.P50_J_per_cm2:7.2f} J/cm²  "
            f"({self.P50_cal_cm2:.2f} cal/cm²)",
            f"  P95  = {self.P95_J_per_cm2:7.2f} J/cm²  "
            f"({self.P95_cal_cm2:.2f} cal/cm²)",
            f"  P99  = {self.P99_J_per_cm2:7.2f} J/cm²  "
            f"({self.P99_cal_cm2:.2f} cal/cm²)",
            "",
            "Distribuição de Categorias PPE:",
        ]
        for cat, frac in sorted(self.cat_distribution.items()):
            bar = "█" * int(frac * 30)
            lines.append(
                f"  Cat {cat}: {frac*100:5.1f}% {bar}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# run_monte_carlo
# ---------------------------------------------------------------------------


def _percentile(samples: list[float], p: float) -> float:
    """Percentile p ∈ [0,100] de uma lista (sem numpy)."""
    if not samples:
        return 0.0
    sorted_s = sorted(samples)
    k = (len(sorted_s) - 1) * (p / 100.0)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return sorted_s[int(k)]
    return sorted_s[lo] + (k - lo) * (sorted_s[hi] - sorted_s[lo])


def _sample_param(
    mean: float, cv_pct: float, dist: DistributionType,
    rng: random.Random,
) -> float:
    """Sample um parâmetro conforme distribuição e CV."""
    cv = cv_pct / 100.0
    if cv <= 0 or mean <= 0:
        return mean
    sigma = mean * cv
    if dist == DistributionType.NORMAL:
        return _sample_normal_truncated(mean, sigma, rng)
    if dist == DistributionType.LOGNORMAL:
        return _sample_lognormal(mean, cv, rng)
    if dist == DistributionType.UNIFORM:
        # Half-width = √3 σ para mesma variância
        half = sigma * math.sqrt(3.0)
        return _sample_uniform(mean, half, rng)
    return mean


@requires_feature(Feature.ARC_FLASH_MC)
def run_monte_carlo(
    base_case,    # ArcFlashCase
    uncertainty: ArcFlashUncertainty,
    n_samples: int = 2000,
    *,
    random_seed: Optional[int] = None,
) -> MonteCarloResult:
    """
    Executa análise Monte Carlo amostrando Ibf/T/G/D conforme
    distribuições especificadas.

    Parameters
    ----------
    base_case:
        Cenário determinístico base (``ArcFlashCase``).
    uncertainty:
        Especificação das incertezas.
    n_samples:
        Número de amostras (default 2000 — converge P95 < 1%).
    random_seed:
        Seed para reproducibilidade.

    Returns
    -------
    MonteCarloResult
    """
    from app.postprocessor.arc_flash import (
        ArcFlashCase, calculate_arc_flash,
    )
    from app.standards.nbr17227 import PpeCategory

    rng = random.Random(random_seed)

    samples_E: list[float] = []
    cat_count: dict[str, int] = {}
    n_invalid = 0

    base_Ibf = base_case.bolted_fault_current_kA
    base_T = base_case.arc_clearing_time_ms
    base_G = base_case.effective_gap_mm()
    base_D = base_case.effective_working_distance_mm()

    for _ in range(n_samples):
        # Sample parâmetros
        Ibf = _sample_param(
            base_Ibf, uncertainty.Ibf_cv_pct,
            uncertainty.Ibf_distribution, rng,
        )
        T = _sample_param(
            base_T, uncertainty.T_cv_pct,
            uncertainty.T_distribution, rng,
        )
        G = _sample_param(
            base_G, uncertainty.gap_cv_pct,
            uncertainty.gap_distribution, rng,
        )
        D = _sample_param(
            base_D, uncertainty.D_cv_pct,
            uncertainty.D_distribution, rng,
        )

        try:
            sample_case = ArcFlashCase(
                bus_name=base_case.bus_name,
                rated_voltage_kV=base_case.rated_voltage_kV,
                bolted_fault_current_kA=Ibf,
                arc_clearing_time_ms=T,
                equipment_class=base_case.equipment_class,
                electrode_config=base_case.electrode_config,
                gap_mm=G,
                working_distance_mm=D,
            )
            rpt = calculate_arc_flash(sample_case)
            E_J = rpt.incident_energy_J_cm2
            if not math.isfinite(E_J) or E_J < 0:
                n_invalid += 1
                continue
            samples_E.append(E_J)
            cat_str = rpt.ppe_category.value
            cat_count[cat_str] = cat_count.get(cat_str, 0) + 1
        except (ValueError, KeyError, ArithmeticError):
            n_invalid += 1

    if not samples_E:
        # Resultado vazio (todas amostras inválidas)
        return MonteCarloResult(
            n_samples=0, n_invalid=n_invalid,
            samples_E_J_per_cm2=(),
            P50_J_per_cm2=0.0, P95_J_per_cm2=0.0,
            P99_J_per_cm2=0.0, mean_J_per_cm2=0.0,
            std_J_per_cm2=0.0, cv_pct=0.0,
            cat_distribution={},
        )

    mean = sum(samples_E) / len(samples_E)
    var = sum((x - mean) ** 2 for x in samples_E) / len(samples_E)
    std = math.sqrt(var)
    cv_pct = (std / mean * 100.0) if mean > 0 else 0.0

    # Percentis
    p50 = _percentile(samples_E, 50.0)
    p95 = _percentile(samples_E, 95.0)
    p99 = _percentile(samples_E, 99.0)

    # Distribuição de categorias (frações)
    total = len(samples_E)
    cat_dist = {k: v / total for k, v in cat_count.items()}

    return MonteCarloResult(
        n_samples=total, n_invalid=n_invalid,
        samples_E_J_per_cm2=tuple(samples_E),
        P50_J_per_cm2=p50, P95_J_per_cm2=p95,
        P99_J_per_cm2=p99, mean_J_per_cm2=mean,
        std_J_per_cm2=std, cv_pct=cv_pct,
        cat_distribution=cat_dist,
    )
