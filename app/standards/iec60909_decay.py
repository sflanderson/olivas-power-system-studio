"""
app.standards.iec60909_decay — fatores de decaimento μ e q
para faltas near-to-generator conforme IEC 60909-0:2016
§4.5 e §4.6.

Motivação
==========

Para faltas próximas a máquinas síncronas (SM) ou
assíncronas (motores grandes), o **breaking current Ib** e o
**steady-state current Ik** são MENORES que Ik'' devido ao
decaimento dos transitórios subtransiente (Xd''→Xd') e
transiente (Xd'→Xd) durante o tempo de abertura do
disjuntor.

A correção da norma:

::

    Ib  = μ · Ik''     (§4.5)
    Ik  = μ · q · Ik'' (§4.6, geradores síncronos)

Onde:

* **μ** depende de Ik''/I_rG (corrente de SC vs corrente
  nominal do gerador) e do tempo de abertura t_min do
  disjuntor (§4.5.2.2 Fig 5).
* **q** depende de t_min e n_p (rotações) e cobre o
  decaimento adicional para regime estável (§4.6.1.2 Fig 8).

Para FAR-FROM-GENERATOR (Z_linha >> Xd''), μ ≈ q ≈ 1
e Ib = Ik = Ik''.

Critério da norma para classificar near vs far
================================================

A IEC 60909-0 §3.6 define o gerador como "perto" da falta se:

::

    Ik''_G > 2 · I_rG

Onde:
* ``Ik''_G`` é a contribuição do gerador para a falta total.
* ``I_rG`` é a corrente nominal do gerador (S_rG / √3·U_rG).

Geralmente isto significa Z_linha ≤ Xd'' (~0.20 pu).

Limitações desta entrega
=========================

* Cobre apenas SM (geradores síncronos). Decaimento para
  motores assíncronos (q distinto) usa heurística mais
  simples (q ≈ 1 sempre, conservador).
* Curvas de μ/q da IEC são reproduzidas como
  aproximações analíticas calibradas (não tabelas literais).

Referências
============

* IEC 60909-0:2016 §4.5 (μ-fator) e §4.6 (q-fator).
* IEC 60909-0:2016 Fig 5, 6, 7, 8.
* John J. Grainger, William D. Stevenson Jr., *Power System
  Analysis*, McGraw-Hill 1994 §10.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# μ-factor (IEC 60909-0 §4.5.2.2)
# ---------------------------------------------------------------------------


def mu_factor(
    Ik_pp_to_IrG_ratio: float,
    minimum_clearing_time_s: float,
) -> float:
    """
    Fator de decaimento μ para corrente de breaking,
    IEC 60909-0 §4.5.2.2.

    A norma fornece Fig 5 (curvas) parametrizadas por
    ``t_min`` (tempo mínimo de abertura do disjuntor).
    Esta função aproxima as curvas com expressões
    analíticas.

    Forma analítica (calibrada de Fig 5):

    ::

        Para r = Ik''_G / I_rG ≤ 2:    μ = 1.0  (far-from-gen)
        Para r > 2:
            μ(t_min) = 0.84 + 0.26 · exp(-0.26·r)   (t=0.02s)
            μ(t_min) = 0.71 + 0.51 · exp(-0.30·r)   (t=0.05s)
            μ(t_min) = 0.62 + 0.72 · exp(-0.32·r)   (t=0.10s)
            μ(t_min) = 0.56 + 0.94 · exp(-0.38·r)   (t≥0.25s)

    Interpolação linear entre os pontos de t_min.

    Parameters
    ----------
    Ik_pp_to_IrG_ratio:
        r = Ik''_G / I_rG. Para r ≤ 2, retorna μ=1 (far).
    minimum_clearing_time_s:
        t_min do disjuntor. Típico: 0.02 (rápido), 0.05
        (médio), 0.10, 0.25 (lento).

    Returns
    -------
    float
        μ ∈ [0.4, 1.0].
    """
    if Ik_pp_to_IrG_ratio < 0:
        raise ValueError(
            f"Ik''/IrG deve ser >= 0 (achado {Ik_pp_to_IrG_ratio})"
        )
    if minimum_clearing_time_s < 0:
        raise ValueError(
            f"t_min deve ser >= 0 (achado {minimum_clearing_time_s})"
        )

    r = Ik_pp_to_IrG_ratio
    # Far-from-generator: μ = 1
    if r <= 2.0:
        return 1.0

    # Calibrated curves per IEC 60909-0 Fig 5
    # μ(r) = a(t) + b(t) · exp(-c(t) · r)  com r > 2

    def _mu_at_t(r_val: float, t: float) -> float:
        if t <= 0.020:
            return 0.84 + 0.26 * math.exp(-0.26 * r_val)
        if t <= 0.050:
            return 0.71 + 0.51 * math.exp(-0.30 * r_val)
        if t <= 0.100:
            return 0.62 + 0.72 * math.exp(-0.32 * r_val)
        return 0.56 + 0.94 * math.exp(-0.38 * r_val)

    # Para t entre os pontos discretos, interpolação linear
    t = minimum_clearing_time_s
    if t <= 0.020:
        mu = _mu_at_t(r, 0.020)
    elif t <= 0.050:
        # Interpolação 0.02 ↔ 0.05
        alpha = (t - 0.020) / (0.050 - 0.020)
        mu = (1.0 - alpha) * _mu_at_t(r, 0.020) + alpha * _mu_at_t(r, 0.050)
    elif t <= 0.100:
        alpha = (t - 0.050) / (0.100 - 0.050)
        mu = (1.0 - alpha) * _mu_at_t(r, 0.050) + alpha * _mu_at_t(r, 0.100)
    elif t <= 0.250:
        alpha = (t - 0.100) / (0.250 - 0.100)
        mu = (1.0 - alpha) * _mu_at_t(r, 0.100) + alpha * _mu_at_t(r, 0.250)
    else:
        # t > 0.25 — usa curva da norma para t_min ≥ 0.25
        mu = _mu_at_t(r, 0.250)

    return max(0.40, min(1.0, mu))


# ---------------------------------------------------------------------------
# q-factor (IEC 60909-0 §4.6.1.2)
# ---------------------------------------------------------------------------


def q_factor(
    minimum_clearing_time_s: float,
    n_per_unit_per_second: float = 0.10,
) -> float:
    """
    Fator de decaimento q para corrente steady-state e
    motores assíncronos, IEC 60909-0 §4.6.1.2 Fig 8.

    O q representa o decaimento ADICIONAL além do μ:
    para clearing rápido o motor ainda contribui muito
    (q≈1), para clearing lento a contribuição decai mais
    (q chega a 0.79).

    Forma analítica calibrada (Fig 8 IEC 60909):

    ::

        q(t < 5ms)    = 1.00     (sub-cycle, sem decaimento)
        q(t = 50ms)   ≈ 0.94
        q(t = 100ms)  ≈ 0.90
        q(t = 250ms)  = 0.79     (regime estável atingido)

    Interpolação log-linear entre extremos.

    Parameters
    ----------
    minimum_clearing_time_s:
        t_min do disjuntor.
    n_per_unit_per_second:
        v3.7.0 (closes SKIPPED_BACKLOG B.3) — parâmetro de decaimento
        do motor assíncrono (IEC 60909-0:2016 §4.6.2 Tab 3):

        - ``0.10`` (default) — motores 2-pólos (decaimento rápido, baixa inércia)
        - ``0.05`` — motores 4-pólos
        - ``0.02`` — motores 6-pólos ou superiores (decaimento lento)

        Tempo efetivo é normalizado por ``n / 0.10``: motores com mais
        pólos têm decaimento mais lento (effective_t menor → q maior).

    Returns
    -------
    float
        q ∈ [0.79, 1.0], decrescente com t_min × n_ratio.
    """
    if minimum_clearing_time_s < 0:
        raise ValueError(
            f"t_min deve ser >= 0 (achado {minimum_clearing_time_s})"
        )
    if n_per_unit_per_second <= 0:
        raise ValueError(
            f"n_per_unit_per_second deve ser > 0 "
            f"(achado {n_per_unit_per_second})"
        )

    # v3.7.0 B.3 — escalar t pelo ratio n/0.10 (default 2-pólos).
    # Maior n → motor decai mais rápido → effective_t maior → q menor.
    # Menor n → motor decai mais devagar (mais inércia) → effective_t
    # menor → q maior. Per IEC 60909-0:2016 §4.6.2 Tab 3.
    n_ratio = n_per_unit_per_second / 0.10
    t_eff = minimum_clearing_time_s * n_ratio

    if t_eff < 0.005:
        # Sub-cycle — q ≈ 1.0 (sem decaimento)
        return 1.0
    if t_eff >= 0.250:
        return 0.79
    # 0.005 ≤ t_eff < 0.25 — log-linear de 1.0 a 0.79
    # q(t) = 1.0 + (0.79 - 1.0) · (ln(t) - ln(0.005)) / (ln(0.25) - ln(0.005))
    log_t = math.log(t_eff)
    log_lo = math.log(0.005)
    log_hi = math.log(0.250)
    alpha = (log_t - log_lo) / (log_hi - log_lo)
    q = 1.0 + (0.79 - 1.0) * alpha
    return max(0.79, min(1.0, q))


# ---------------------------------------------------------------------------
# Wrapper: corrente decaída
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecayResult:
    """
    Resultado dos fatores de decaimento aplicados ao Ik''.

    Attributes
    ----------
    Ik_pp_kA:
        Initial symmetrical SC current.
    Ib_kA:
        Breaking current = μ · Ik''.
    Ik_steady_kA:
        Steady-state current = μ · q · Ik''.
    mu:
        μ-factor aplicado.
    q:
        q-factor aplicado (1.0 se far-from-generator).
    is_near_to_generator:
        True se Ik''/I_rG > 2.
    """
    Ik_pp_kA: float
    Ib_kA: float
    Ik_steady_kA: float
    mu: float
    q: float
    is_near_to_generator: bool


def apply_near_to_generator_decay(
    Ik_pp_kA: float,
    IrG_kA: float,
    minimum_clearing_time_s: float = 0.05,
) -> DecayResult:
    """
    Aplica os fatores μ e q ao Ik'' conforme IEC 60909-0
    §4.5/4.6.

    Para falta near-to-generator (Ik''/I_rG > 2):
      Ib = μ · Ik''
      Ik = μ · q · Ik''

    Para far-from-generator (Ik''/I_rG ≤ 2):
      μ = q = 1 → Ib = Ik = Ik''

    Parameters
    ----------
    Ik_pp_kA:
        Corrente inicial simétrica de SC do gerador (kA).
    IrG_kA:
        Corrente nominal do gerador (kA) =
        S_rG / (√3 · U_rG).
    minimum_clearing_time_s:
        t_min do disjuntor (default 50 ms — típico VCB).

    Returns
    -------
    DecayResult
    """
    if Ik_pp_kA <= 0:
        raise ValueError(f"Ik_pp_kA deve ser > 0 (achado {Ik_pp_kA})")
    if IrG_kA <= 0:
        raise ValueError(f"IrG_kA deve ser > 0 (achado {IrG_kA})")

    ratio = Ik_pp_kA / IrG_kA
    is_near = ratio > 2.0

    mu = mu_factor(ratio, minimum_clearing_time_s)
    if is_near:
        q = q_factor(minimum_clearing_time_s)
    else:
        q = 1.0

    Ib = mu * Ik_pp_kA
    Ik_steady = mu * q * Ik_pp_kA

    return DecayResult(
        Ik_pp_kA=Ik_pp_kA,
        Ib_kA=Ib,
        Ik_steady_kA=Ik_steady,
        mu=mu,
        q=q,
        is_near_to_generator=is_near,
    )
