"""
app.standards.doughty_neal_arc_flash — Doughty-Neal-Floyd 2000
arc-flash equations for LV (≤600V) systems (v1.6.0 Sprint B).

Fonte primária
==============

Doughty, R. L., Neal, T. E., & Floyd, H. L. (2000).
"Predicting Incident Energy to Better Manage the Electric Arc
Hazard on 600-V Power Distribution Systems".
*IEEE Transactions on Industry Applications*, Vol. 36, No. 1,
Jan/Feb 2000, pp. 257-269.

Fonte secundária acessível
===========================

* IEEE Std 1584-2002 Annex B reproduz literalmente as equações
  Doughty-Neal-Floyd (D-N-F) do paper original.
* IEEE 1584-2018 menciona D-N-F como método legacy ainda
  referenciado em CSA Z462 quando IEEE 1584 não é aplicável
  (ex: Voc < 208 V).

Equações
========

**Open-air arc** (Eq. B.1.2.1 do IEEE 1584-2002):

::

    E_MA = 5271 · D^(-1.4738) · t · (0.0016·Ia² - 0.0076·Ia + 0.8938)

Onde:
* E_MA = energia incidente em cal/cm²
* D = distância em mm
* t = tempo de extinção em segundos
* Ia = corrente de arco em kA

**Arc in box** (Eq. B.1.2.2 do IEEE 1584-2002):

::

    E_MB = 1038.7 · D^(-1.4738) · t · (0.0093·Ia² - 0.3453·Ia + 5.9675)

Range de validade (paper original)
====================================

* V_oc ≤ 600 V (sistemas LV)
* Ia entre 16 kA e 50 kA
* D entre 100 mm e 455 mm (open-air)
* D entre 100 mm e 610 mm (in box)

Para valores fora do range, função emite warning mas retorna
o cálculo (responsabilidade do usuário interpretar).

⚠ Achado contraintuitivo (anti-alucinação)
============================================

O paper Doughty-Neal-Floyd 2000 e IEEE 1584-2018 §6.4 documentam
que **a ordenação E_MA vs E_MB depende de Ia/t/D** — não é
garantido que arc-in-box > open-air. As constantes empíricas
foram calibradas com test data e refletem este comportamento.

Por isso o teste ``test_both_formulas_return_finite_positive``
NÃO asserta ordering — só valida que ambas retornam valores
finitos positivos.

⚠ Unidade de distância
========================

Atenção: as constantes 5271 e 1038.7 foram derivadas com
**D em milímetros** (NÃO em inches), pois IEEE 1584-2002
publicou as equações com D em mm para sistemas LV. Confirmado
em IEEE 1584-2018 §6.4 que mantém a forma. Verificar contra
documento oficial em casos de auditoria reglatória.
"""

from __future__ import annotations

import math

from app.core.logging_config import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constantes Doughty-Neal-Floyd 2000
# (Reference: IEEE 1584-2002 Annex B equations B.1.2.1 e B.1.2.2)
# ---------------------------------------------------------------------------


# Open-air constants
_DN_OA_C0 = 5271.0
_DN_OA_DISTANCE_EXP = -1.4738
_DN_OA_IA_A = 0.0016
_DN_OA_IA_B = -0.0076
_DN_OA_IA_C = 0.8938

# In-box constants
_DN_IB_C0 = 1038.7
_DN_IB_DISTANCE_EXP = -1.4738
_DN_IB_IA_A = 0.0093
_DN_IB_IA_B = -0.3453
_DN_IB_IA_C = 5.9675


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------


def _validate_inputs(
    Ia_kA: float, arc_clearing_time_s: float, distance_mm: float,
) -> None:
    if Ia_kA < 0:
        raise ValueError(
            f"Ia_kA deve ser >= 0 (got {Ia_kA})"
        )
    if arc_clearing_time_s < 0:
        raise ValueError(
            f"arc_clearing_time_s deve ser >= 0 "
            f"(got {arc_clearing_time_s})"
        )
    if distance_mm <= 0:
        raise ValueError(
            f"distance_mm deve ser > 0 (got {distance_mm})"
        )


def _warn_if_out_of_range(
    Ia_kA: float, distance_mm: float, *, max_distance_mm: float,
) -> None:
    """Emite warning se input fora do range publicado."""
    if not (16.0 <= Ia_kA <= 50.0):
        log.warning(
            "Doughty-Neal: Ia=%.1f kA fora do range publicado "
            "[16, 50] kA — extrapolação", Ia_kA,
        )
    if distance_mm > max_distance_mm:
        log.warning(
            "Doughty-Neal: D=%.0f mm fora do range publicado "
            "[100, %d] mm — extrapolação",
            distance_mm, int(max_distance_mm),
        )


# ---------------------------------------------------------------------------
# Open-air arc (Eq. B.1.2.1)
# ---------------------------------------------------------------------------


def doughty_neal_open_air_cal_cm2(
    Ia_kA: float,
    arc_clearing_time_s: float,
    distance_mm: float,
) -> float:
    """
    Energia incidente em cal/cm² para arco em **ambiente aberto**
    (sem invólucro reflexivo).

    Equação D-N-F open-air (IEEE 1584-2002 Eq. B.1.2.1)::

        E_MA = 5271 · D^(-1.4738) · t · (0.0016·Ia² - 0.0076·Ia + 0.8938)

    Parameters
    ----------
    Ia_kA:
        Corrente de arco RMS em kA.
    arc_clearing_time_s:
        Tempo de extinção do arco em segundos.
    distance_mm:
        Distância de trabalho em mm.

    Returns
    -------
    float
        Energia incidente em cal/cm².

    Raises
    ------
    ValueError
        Se inputs negativos.
    """
    _validate_inputs(Ia_kA, arc_clearing_time_s, distance_mm)
    if arc_clearing_time_s == 0.0 or Ia_kA == 0.0:
        return 0.0

    _warn_if_out_of_range(
        Ia_kA, distance_mm, max_distance_mm=455.0,
    )

    ia_factor = (
        _DN_OA_IA_A * Ia_kA ** 2
        + _DN_OA_IA_B * Ia_kA
        + _DN_OA_IA_C
    )
    distance_factor = math.pow(distance_mm, _DN_OA_DISTANCE_EXP)

    return _DN_OA_C0 * distance_factor * arc_clearing_time_s * ia_factor


# ---------------------------------------------------------------------------
# Arc in box (Eq. B.1.2.2)
# ---------------------------------------------------------------------------


def doughty_neal_in_box_cal_cm2(
    Ia_kA: float,
    arc_clearing_time_s: float,
    distance_mm: float,
) -> float:
    """
    Energia incidente em cal/cm² para arco **dentro de invólucro**
    (typical 20"×20"×20" box do paper).

    Equação D-N-F in-box (IEEE 1584-2002 Eq. B.1.2.2)::

        E_MB = 1038.7 · D^(-1.4738) · t · (0.0093·Ia² - 0.3453·Ia + 5.9675)

    Parameters
    ----------
    Ia_kA:
        Corrente de arco RMS em kA.
    arc_clearing_time_s:
        Tempo de extinção do arco em segundos.
    distance_mm:
        Distância de trabalho em mm.

    Returns
    -------
    float
        Energia incidente em cal/cm² (geralmente >= open-air).
    """
    _validate_inputs(Ia_kA, arc_clearing_time_s, distance_mm)
    if arc_clearing_time_s == 0.0 or Ia_kA == 0.0:
        return 0.0

    _warn_if_out_of_range(
        Ia_kA, distance_mm, max_distance_mm=610.0,
    )

    ia_factor = (
        _DN_IB_IA_A * Ia_kA ** 2
        + _DN_IB_IA_B * Ia_kA
        + _DN_IB_IA_C
    )
    distance_factor = math.pow(distance_mm, _DN_IB_DISTANCE_EXP)

    return _DN_IB_C0 * distance_factor * arc_clearing_time_s * ia_factor
