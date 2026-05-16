"""
app/standards/solution_method.py — ANSI Solution method + standard conversion.

Implements PTW Reference-A_Fault.pdf §1.3.3 p. 1-9/1-11 + §1.3.7 p. 1-19/1-20:

* **SolutionMethod enum** — E_Z (default, complex Z) vs E_X (reactance only)
* **x_over_r_from_complex_impedance(r, x)** — Comprehensive method X/R
* **convert_total_to_symmetrical(i, factor)** — C37.5 → C37.010 conversion
* **convert_symmetrical_to_total(i, factor)** — inverso

Métodos:
* **E/Z** (Comprehensive, default ANSI) — usa impedância complexa Z = R + jX.
  X/R derivado do ângulo: tan(angle) = X/R.
* **E/X** (legacy) — apenas reactância; assume R=0 ou despreza.

Conversão:
* C37.5 (pre-1964 Total Rated, breaker rated em corrente asimétrica)
* C37.010 (post-1964 Symmetrical Rated, breaker rated em corrente simétrica)
* Conversão típica: i_total = i_symm × asym_factor, factor ~1.6 para X/R=25,
  ~1.5 para X/R=15 (per §1.3.6 Eq. 7-1 simplificado).

Reference
---------
PTW Reference-A_Fault.pdf §1.3.3 p. 1-9 a 1-11 (Solution Method).
PTW Reference-A_Fault.pdf §1.3.7 p. 1-19/1-20 (C37.5 vs C37.010).
ANSI/IEEE C37.5-1979, ANSI/IEEE C37.010-1979.
"""

from __future__ import annotations

import math
from enum import Enum


class SolutionMethod(str, Enum):
    """ANSI solution method (§1.3.3 p. 1-11 linhas 615-619).

    * **E_Z** — Equivalent E divided by complex impedance Z = R + jX.
      Default ANSI workflow; mais preciso. X/R derivado de arctan(X/R)
      do equivalente.

    * **E_X** — Equivalent E divided by reactance X only (R desprezado).
      Método legacy / simplificado; mais conservador (yield maior I_fault).

    References
    ----------
    PTW A_Fault §1.3.3 p. 1-11 (linhas 615-619).
    """

    E_Z = "E_Z"
    E_X = "E_X"


# §1.3.3 default per A_Fault p. 1-11.
DEFAULT_SOLUTION_METHOD: SolutionMethod = SolutionMethod.E_Z


def x_over_r_from_complex_impedance(r: float, x: float) -> float:
    """Compute X/R ratio from complex impedance Z = R + jX.

    Per PTW A_Fault §1.3.3 p. 1-9: para método E/Z (Comprehensive),
    X/R é derivado do ângulo da impedância complexa:

    .. math::
        \\frac{X}{R} = \\tan(\\angle Z) = \\frac{X}{R}

    Manual cita (§1.4.1 Case 2 p. 1-29):
    ``Z = 0.065 + j0.922 pu`` → X/R = 0.922/0.065 = **14.18** (manual: 14.105)

    Note: este X/R diverge do **separately-derived** X/R quando há
    múltiplas branches em paralelo. Veja
    :func:`app.standards.ansi_c37.separately_derived_xr`.

    Parameters
    ----------
    r
        Resistance (real part of Z), pu ou Ohm. Deve ser ≥ 0.
    x
        Reactance (imag part of Z), pu ou Ohm. Deve ser ≥ 0.

    Returns
    -------
    float
        X/R ratio. ``math.inf`` se R=0 e X>0; 0.0 se X=0 e R>0.

    References
    ----------
    PTW A_Fault §1.3.3 p. 1-9.
    """
    if r < 0:
        raise ValueError(f"r must be ≥ 0; got {r!r}")
    if x < 0:
        raise ValueError(f"x must be ≥ 0; got {x!r}")
    if r == 0.0:
        return math.inf if x > 0 else 0.0
    return x / r


def convert_total_to_symmetrical(
    i_total_kA: float,
    asym_factor: float,
) -> float:
    """Convert from C37.5 Total Rated to C37.010 Symmetrical Rated.

    Per PTW A_Fault §1.3.7 p. 1-19/1-20:

    .. math::
        I_{symm} = \\frac{I_{total}}{f_{asym}}

    onde ``f_asym`` é o asymmetrical factor (típico 1.5-1.7 em momentary,
    1.0-1.2 em interrupting).

    Manual prosa §1.3.6 simplificado:
    * X/R=25, momentary: f_asym ≈ 1.6
    * X/R=15, momentary: f_asym ≈ 1.5

    Parameters
    ----------
    i_total_kA
        Corrente Total Rated (asymmetrical), kA.
    asym_factor
        Asymmetrical factor para conversão. Deve ser > 0.

    Returns
    -------
    float
        Corrente Symmetrical Rated equivalent, kA.

    References
    ----------
    PTW A_Fault §1.3.7 p. 1-19/1-20.
    ANSI C37.5-1979, ANSI C37.010-1979.
    """
    if asym_factor <= 0:
        raise ValueError(
            f"asym_factor must be > 0; got {asym_factor!r}"
        )
    if i_total_kA < 0:
        raise ValueError(
            f"i_total_kA must be ≥ 0; got {i_total_kA!r}"
        )
    return i_total_kA / asym_factor


def convert_symmetrical_to_total(
    i_symm_kA: float,
    asym_factor: float,
) -> float:
    """Convert from C37.010 Symmetrical Rated to C37.5 Total Rated.

    Inverso de :func:`convert_total_to_symmetrical`.

    .. math::
        I_{total} = I_{symm} \\times f_{asym}

    References
    ----------
    PTW A_Fault §1.3.7 p. 1-19/1-20.
    """
    if asym_factor < 0:
        raise ValueError(
            f"asym_factor must be ≥ 0; got {asym_factor!r}"
        )
    if i_symm_kA < 0:
        raise ValueError(
            f"i_symm_kA must be ≥ 0; got {i_symm_kA!r}"
        )
    return i_symm_kA * asym_factor


__all__ = [
    "SolutionMethod",
    "DEFAULT_SOLUTION_METHOD",
    "x_over_r_from_complex_impedance",
    "convert_total_to_symmetrical",
    "convert_symmetrical_to_total",
]
