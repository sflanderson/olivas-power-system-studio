"""
app.standards.iec60255 — codificação das curvas tempo-corrente
(TC curves) padronizadas da IEC 60255-151 e IEEE C37.112 para
relés de sobrecorrente.

Fonte: parametrizações conforme:
* IEC 60255-151:2009 (e versões posteriores) — Measuring relays
  and protection equipment, Part 151: Functional requirements
  for over/under current protection.
* IEEE Std C37.112-2018 — IEEE Standard Inverse-Time
  Characteristic Equations for Overcurrent Relays.
* Schneider Easergy P3U (LIBRARY/library_relay/SCHNEIDER) —
  reproduz IEC e IEEE2 curves.
* ABB Relion 615 (LIBRARY/library_relay/ABB) — IEC e ANSI
  curves implementados.
* SEL-751 (LIBRARY/library_relay/SEL) — US (IEEE C37.112) e
  IEC curves implementados via TYPE setting.

Fundamentos
============

A curva tempo-corrente (TC curve) define o tempo de operação
``t(I)`` de um relé de sobrecorrente em função do múltiplo de
corrente ``M = I / Is`` (Is = pickup current setting):

**IEC 60255-151** (forma clássica):

::

    t(I) = TMS · k / (M^α - 1)

Onde TMS é o Time Multiplier Setting (0.05 a 1.0 típico).

**IEEE C37.112** (forma com constante β):

::

    t(I) = TD · (k / (M^α - 1) + β) / 7

Onde TD é o Time Dial (0.5 a 15 típico). O divisor 7 vem da
adoção histórica do CO-9 (electromechanical relay).

Curvas IEC (Tabela 2 da IEC 60255-151)
=======================================

==========================  ======  =====
Tipo (IEC)                  k       α
==========================  ======  =====
Standard Inverse (SI)       0.14    0.02
Very Inverse (VI)           13.5    1.00
Extremely Inverse (EI)      80.0    2.00
Long Time Inverse (LTI)     120.0   1.00
==========================  ======  =====

Curvas IEEE (Tabela 1 da IEEE C37.112)
======================================

==========================  ========  ====  =======
Tipo (IEEE)                 k         α     β
==========================  ========  ====  =======
Moderately Inverse (U1)     0.0515    0.02  0.114
Very Inverse (U2)           19.61     2.00  0.491
Extremely Inverse (U3)      28.2      2.00  0.1217
Inverse (CO-8)              5.95      2.00  0.18
Short Time Inverse (CO-2)   0.02394   0.02  0.01694
==========================  ========  ====  =======

Tipos adicionais (vendor-specific)
==================================

* **RI (Reverse Inverse)** — usado por ABB/AREVA, fórmula
  específica não-IEC (vide ABB RE615 Tabela 5.4).
* **Definite Time (DT)** — t = constante (não-inversa).
* **Programmable** — usuário define curva via tabela.

Ranges típicos de TMS / TD
===========================

* IEC TMS: 0.05 → 1.0 (default 0.5).
* IEEE TD: 0.5 → 15 (default 5).
* Pickup Is: 0.1× → 30× corrente nominal do relé.

Aplicações
===========

* **Relé 50** (instantaneous overcurrent): t = 0 (DT com 0 atraso).
* **Relé 51** (time-delayed overcurrent): TC curve completa.
* **Relé 50/51** (combo): instantaneous + delayed em pickup
  diferente.
* **Coordenação** entre relés: time grading via TMS escalonado
  (IEEE 242 Buff Book §15).

Referências
============

* IEC 60255-151:2009 — Functional requirements for over/under
  current protection.
* IEEE Std C37.112-2018 — Inverse-time characteristic equations.
* IEEE Std 242-2001 (Buff Book) — Industrial protection.
* ABB RE_615 Manual Técnico (LIBRARY/library_relay/ABB).
* Schneider Easergy P3U manual (LIBRARY/library_relay/SCHNEIDER).
* SEL-751 Instruction Manual (LIBRARY/library_relay/SEL).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CurveStandard(str, Enum):
    """Família da curva TC."""
    IEC = "IEC"           # IEC 60255-151
    IEEE = "IEEE"         # IEEE C37.112
    ANSI = "ANSI"         # ANSI alias (= IEEE)
    DEFINITE_TIME = "DT"  # tempo definido (constante)
    CUSTOM = "CUSTOM"     # tabela usuário


class IecCurveType(str, Enum):
    """Curvas IEC 60255-151 Tabela 2."""
    STANDARD_INVERSE = "SI"
    VERY_INVERSE = "VI"
    EXTREMELY_INVERSE = "EI"
    LONG_TIME_INVERSE = "LTI"


class IeeeCurveType(str, Enum):
    """Curvas IEEE C37.112 Tabela 1 e equivalents ANSI."""
    MODERATELY_INVERSE = "U1"   # CO-8 historic
    VERY_INVERSE = "U2"
    EXTREMELY_INVERSE = "U3"
    INVERSE = "CO8"             # alternative
    SHORT_TIME_INVERSE = "CO2"


# ---------------------------------------------------------------------------
# Coeficientes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IecCurveCoefficients:
    """
    Coeficientes da forma ``t = TMS · k / (M^α - 1)``.

    IEC 60255-151 Tabela 2.
    """
    k: float
    alpha: float


@dataclass(frozen=True)
class IeeeCurveCoefficients:
    """
    Coeficientes da forma ``t = TD · (k / (M^α - 1) + β) / 7``.

    IEEE C37.112 Tabela 1.
    """
    k: float
    alpha: float
    beta: float


# IEC 60255-151 Tabela 2 — coeficientes oficiais.
IEC_CURVE_COEFFICIENTS: dict[IecCurveType, IecCurveCoefficients] = {
    IecCurveType.STANDARD_INVERSE: IecCurveCoefficients(
        k=0.14, alpha=0.02,
    ),
    IecCurveType.VERY_INVERSE: IecCurveCoefficients(
        k=13.5, alpha=1.0,
    ),
    IecCurveType.EXTREMELY_INVERSE: IecCurveCoefficients(
        k=80.0, alpha=2.0,
    ),
    IecCurveType.LONG_TIME_INVERSE: IecCurveCoefficients(
        k=120.0, alpha=1.0,
    ),
}


# IEEE C37.112 Tabela 1 — coeficientes oficiais.
IEEE_CURVE_COEFFICIENTS: dict[IeeeCurveType, IeeeCurveCoefficients] = {
    IeeeCurveType.MODERATELY_INVERSE: IeeeCurveCoefficients(
        k=0.0515, alpha=0.02, beta=0.114,
    ),
    IeeeCurveType.VERY_INVERSE: IeeeCurveCoefficients(
        k=19.61, alpha=2.0, beta=0.491,
    ),
    IeeeCurveType.EXTREMELY_INVERSE: IeeeCurveCoefficients(
        k=28.2, alpha=2.0, beta=0.1217,
    ),
    IeeeCurveType.INVERSE: IeeeCurveCoefficients(
        k=5.95, alpha=2.0, beta=0.18,
    ),
    IeeeCurveType.SHORT_TIME_INVERSE: IeeeCurveCoefficients(
        k=0.02394, alpha=0.02, beta=0.01694,
    ),
}


# ---------------------------------------------------------------------------
# Cálculo TC curve
# ---------------------------------------------------------------------------


def operate_time_iec_s(
    current_A: float,
    pickup_A: float,
    tms: float,
    curve: IecCurveType,
    *,
    tms_range: tuple[float, float] = (0.05, 1.0),
) -> float:
    """
    Tempo de operação t (segundos) para curva IEC 60255-151:

    ::

        t = TMS · k / (M^α - 1)

    onde M = I / Is.

    Parameters
    ----------
    current_A:
        Corrente medida.
    pickup_A:
        Corrente de pickup Is.
    tms:
        Time Multiplier Setting.
    curve:
        Tipo de curva (SI/VI/EI/LTI).
    tms_range:
        v0.28.0-PRO: range válido de TMS, default (0.05, 1.0)
        IEC 60255-151. Vendor specific (ex: Schneider P3U30
        usa (0.025, 1.5)) pode ser passado para conciliar
        com o registry.

    Returns
    -------
    float
        Tempo em segundos. Retorna ``inf`` se M ≤ 1 (não pickup).

    Raises
    ------
    ValueError
        Se ``pickup_A`` ou ``current_A`` ≤ 0, ou ``tms`` fora do
        range fornecido.
    """
    if pickup_A <= 0:
        raise ValueError(f"pickup_A deve ser > 0 (achado {pickup_A})")
    if current_A <= 0:
        raise ValueError(f"current_A deve ser > 0 (achado {current_A})")
    lo, hi = tms_range
    if not (lo <= tms <= hi):
        raise ValueError(
            f"tms={tms} fora do range [{lo}, {hi}]"
        )

    multiple = current_A / pickup_A
    if multiple <= 1.0:
        return float("inf")

    coef = IEC_CURVE_COEFFICIENTS[curve]
    return tms * coef.k / (multiple ** coef.alpha - 1.0)


def operate_time_ieee_s(
    current_A: float,
    pickup_A: float,
    time_dial: float,
    curve: IeeeCurveType,
) -> float:
    """
    Tempo de operação t (segundos) para curva IEEE C37.112:

    ::

        t = TD · (k / (M^α - 1) + β) / 7

    O divisor 7 normaliza o time dial à escala 0.5–15 do CO-9
    histórico.

    Raises
    ------
    ValueError
        Se ``time_dial`` fora de [0.5, 15].
    """
    if pickup_A <= 0:
        raise ValueError(f"pickup_A deve ser > 0 (achado {pickup_A})")
    if current_A <= 0:
        raise ValueError(f"current_A deve ser > 0 (achado {current_A})")
    if not (0.5 <= time_dial <= 15.0):
        raise ValueError(
            f"time_dial={time_dial} fora do range IEEE [0.5, 15]"
        )

    multiple = current_A / pickup_A
    if multiple <= 1.0:
        return float("inf")

    coef = IEEE_CURVE_COEFFICIENTS[curve]
    return time_dial * (coef.k / (multiple ** coef.alpha - 1.0) + coef.beta) / 7.0


def operate_time_definite_time_s(
    current_A: float,
    pickup_A: float,
    delay_s: float,
) -> float:
    """
    Curva definite time: ``t = delay_s`` se ``I > Is``, else ``inf``.

    Usado em relés 50 (instantâneo) com pickup_A alto e
    delay_s = 0, ou em proteção de zona com tempo fixo.
    """
    if delay_s < 0:
        raise ValueError(f"delay_s deve ser >= 0 (achado {delay_s})")
    return delay_s if current_A > pickup_A else float("inf")


# ---------------------------------------------------------------------------
# Helper unificado (curva polimórfica)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TcCurveSetting:
    """
    Configuração completa de uma curva TC para um relé.

    Esta dataclass é polimórfica via ``standard`` —
    interpretadores chamam o método ``operate_time_s`` que
    despacha para a fórmula apropriada.

    Examples
    --------
    IEC SI com TMS 0.5, pickup 100 A:

    >>> tc = TcCurveSetting(
    ...     standard=CurveStandard.IEC,
    ...     iec_curve=IecCurveType.STANDARD_INVERSE,
    ...     pickup_A=100.0, tms=0.5,
    ... )
    >>> tc.operate_time_s(500)  # M=5
    1.080...

    IEEE Very Inverse com TD 5, pickup 200 A:

    >>> tc = TcCurveSetting(
    ...     standard=CurveStandard.IEEE,
    ...     ieee_curve=IeeeCurveType.VERY_INVERSE,
    ...     pickup_A=200.0, time_dial=5.0,
    ... )
    """

    standard: CurveStandard
    pickup_A: float

    # IEC
    iec_curve: IecCurveType | None = None
    tms: float = 0.5

    # IEEE
    ieee_curve: IeeeCurveType | None = None
    time_dial: float = 5.0

    # Definite time
    delay_s: float = 0.0

    # Custom (caller fornece função)
    custom_t_of_I: object | None = None

    # v0.28.0-PRO P2.12: ranges customizáveis por vendor
    # (ex: Schneider P3U30 → tms_range=(0.025, 1.5)).
    # None = usa padrão IEC/IEEE.
    tms_range_override: tuple[float, float] | None = None
    time_dial_range_override: tuple[float, float] | None = None

    def operate_time_s(self, current_A: float) -> float:
        """Despacha para a fórmula apropriada conforme ``standard``."""
        if self.standard == CurveStandard.IEC:
            if self.iec_curve is None:
                raise ValueError("iec_curve obrigatório para CurveStandard.IEC")
            tms_range = self.tms_range_override or (0.05, 1.0)
            return operate_time_iec_s(
                current_A=current_A,
                pickup_A=self.pickup_A,
                tms=self.tms,
                curve=self.iec_curve,
                tms_range=tms_range,
            )
        if self.standard in (CurveStandard.IEEE, CurveStandard.ANSI):
            if self.ieee_curve is None:
                raise ValueError(
                    "ieee_curve obrigatório para CurveStandard.IEEE/ANSI"
                )
            return operate_time_ieee_s(
                current_A=current_A,
                pickup_A=self.pickup_A,
                time_dial=self.time_dial,
                curve=self.ieee_curve,
            )
        if self.standard == CurveStandard.DEFINITE_TIME:
            return operate_time_definite_time_s(
                current_A=current_A,
                pickup_A=self.pickup_A,
                delay_s=self.delay_s,
            )
        if self.standard == CurveStandard.CUSTOM:
            if self.custom_t_of_I is None:
                raise ValueError("custom_t_of_I obrigatório")
            return self.custom_t_of_I(current_A)
        raise ValueError(f"Standard desconhecido: {self.standard!r}")

    def description(self) -> str:
        """String identificadora da curva (para relatórios)."""
        if self.standard == CurveStandard.IEC:
            return (
                f"IEC 60255-151 {self.iec_curve.value if self.iec_curve else '?'} "
                f"(TMS={self.tms}, Is={self.pickup_A:.1f} A)"
            )
        if self.standard in (CurveStandard.IEEE, CurveStandard.ANSI):
            return (
                f"IEEE C37.112 {self.ieee_curve.value if self.ieee_curve else '?'} "
                f"(TD={self.time_dial}, Is={self.pickup_A:.1f} A)"
            )
        if self.standard == CurveStandard.DEFINITE_TIME:
            return (
                f"Definite Time (Is={self.pickup_A:.1f} A, "
                f"t={self.delay_s:.3f} s)"
            )
        return f"Custom (Is={self.pickup_A:.1f} A)"


# ---------------------------------------------------------------------------
# Helpers de construção
# ---------------------------------------------------------------------------


def make_iec_si(pickup_A: float, tms: float = 0.5) -> TcCurveSetting:
    """Atalho: curva IEC Standard Inverse."""
    return TcCurveSetting(
        standard=CurveStandard.IEC,
        iec_curve=IecCurveType.STANDARD_INVERSE,
        pickup_A=pickup_A, tms=tms,
    )


def make_iec_vi(pickup_A: float, tms: float = 0.5) -> TcCurveSetting:
    """Atalho: curva IEC Very Inverse."""
    return TcCurveSetting(
        standard=CurveStandard.IEC,
        iec_curve=IecCurveType.VERY_INVERSE,
        pickup_A=pickup_A, tms=tms,
    )


def make_iec_ei(pickup_A: float, tms: float = 0.5) -> TcCurveSetting:
    """Atalho: curva IEC Extremely Inverse."""
    return TcCurveSetting(
        standard=CurveStandard.IEC,
        iec_curve=IecCurveType.EXTREMELY_INVERSE,
        pickup_A=pickup_A, tms=tms,
    )


def make_ieee_vi(pickup_A: float, time_dial: float = 5.0) -> TcCurveSetting:
    """Atalho: curva IEEE Very Inverse."""
    return TcCurveSetting(
        standard=CurveStandard.IEEE,
        ieee_curve=IeeeCurveType.VERY_INVERSE,
        pickup_A=pickup_A, time_dial=time_dial,
    )


def make_ieee_ei(pickup_A: float, time_dial: float = 5.0) -> TcCurveSetting:
    """Atalho: curva IEEE Extremely Inverse."""
    return TcCurveSetting(
        standard=CurveStandard.IEEE,
        ieee_curve=IeeeCurveType.EXTREMELY_INVERSE,
        pickup_A=pickup_A, time_dial=time_dial,
    )


def make_definite_time(pickup_A: float, delay_s: float) -> TcCurveSetting:
    """Atalho: curva tempo definido."""
    return TcCurveSetting(
        standard=CurveStandard.DEFINITE_TIME,
        pickup_A=pickup_A,
        delay_s=delay_s,
    )


def make_instantaneous(pickup_A: float) -> TcCurveSetting:
    """Atalho: relé 50 (instantâneo) — DT com delay=0."""
    return make_definite_time(pickup_A, delay_s=0.0)
