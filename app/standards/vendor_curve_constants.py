"""
app.standards.vendor_curve_constants — constantes de curvas
tempo-corrente **publicadas pelos fabricantes** de relés IED, com
proveniência explícita por família de curva.

Motivação
=========

``app.standards.iec60255`` codifica os coeficientes genéricos
IEC 60255-151 / IEEE C37.112. Ao digitalizar os manuais oficiais
(ABB REF615R, Siemens SIPROTEC 7SJ82/85, SEL-751, GE Multilin
850, Schneider MiCOM P12x) constatou-se que **existem duas
famílias numéricas distintas** circulando na indústria sob os
mesmos nomes descritivos ("Moderately / Very / Extremely
Inverse"):

1. **IEEE C37.112-1996 Anexo A** ("família nova") —
   ``t = TD · [A/(M^p − 1) + B]``. Confirmada em três fontes
   independentes: constantes públicas da norma, *defaults* da
   curva programável do ABB REF615R (A=28.2, B=0.1217, D=29.1)
   e Tabela 4-34 do manual GE 850.
2. **Família legada "US/CO"** (réplica de relés eletromecânicos
   Westinghouse/GE CO) — publicada pela SEL (curvas U1–U5, forma
   de 3 constantes) e pela GE (Tabela 4-36 "ANSI", forma de 5
   constantes A–E). As duas descrevem a **mesma curva física**:
   a constante de reset ``tr`` coincide exatamente entre SEL e GE
   (EI 5.67, VI 3.88, Inverse 5.95, MI 1.08).

As duas famílias **não são intercambiáveis**. Este módulo guarda
cada conjunto com a sua fonte e não tenta unificá-los.

Nota sobre ``iec60255.IEEE_CURVE_COEFFICIENTS`` (pré-existente)
-----------------------------------------------------------------

O dicionário genérico rotula as constantes do Anexo A com os
códigos ``U1/U2/U3`` (nomenclatura SEL) e, na mesma tabela,
codifica ``INVERSE="CO8"`` com ``k=5.95, β=0.18`` — valores que
pertencem à família legada (SEL U2). A tabela genérica é portanto
mista. Além disso a fórmula ``operate_time_ieee_s`` divide por 7,
convenção de normalização de *time dial* que **não** aparece nas
equações publicadas por GE, SEL ou ABB. Nenhum dos dois pontos
foi alterado aqui (risco de regressão em coordenação existente);
ficam registrados para decisão do mantenedor. Este módulo é
puramente aditivo.

Constantes IEC de **operação** (k, α) são universais e coincidem
em todas as fontes (SI 0.14/0.02, VI 13.5/1, EI 80/2). As
constantes IEC de **reset** são específicas de cada fabricante
(SEL: 13.5/47.3/80; GE: 9.7/43.2/58.2) — a norma padroniza a
curva de operação, não a de reset.

Fontes (documentos oficiais)
============================

* SEL — *PowerSystemProtection, IEC 61131 Library for ACSELERATOR
  RTAC*, Date Code 20180920, Tabelas 1 e 2 (equações C1–C5 e
  U1–U5 usadas nos relés SEL).
* GE Multilin — *850 Feeder Protection System Instruction
  Manual*, Tabelas 4-34 (IEEE), 4-36 (ANSI), 4-38 (IEC/BS142),
  4-40 (IAC).
* ABB — *REF615R Technical Manual* 1MRS240050-IB Rev. C, Tabela
  78 (parâmetros A–E da curva programável).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CurveFamily(str, Enum):
    """Família numérica de uma curva tempo-corrente."""
    IEC_60255 = "IEC_60255"                  # k, α (operação universal)
    IEEE_C37112_ANNEX_A = "IEEE_ANNEX_A"     # "nova" (ABB/GE 4-34)
    US_LEGACY_CO = "US_LEGACY_CO"            # SEL U1-U5 / GE ANSI 4-36
    GE_IAC = "GE_IAC"                        # proprietária GE tipo IAC


@dataclass(frozen=True)
class VendorCurveConstants:
    """
    Constantes de uma curva conforme publicadas por um fabricante.

    Forma de 3 constantes (IEC, IEEE Anexo A, SEL):
        ``t = TD · (a / (M^p − 1) + b)``  (IEC: b = 0)
    Forma de 5 constantes (GE ANSI / IAC): a–e conforme manual GE,
    fórmula fechada não transcrita (apenas a tabela).

    Attributes
    ----------
    reset_tr:
        Constante da curva de reset ``t_reset = TD · tr / (1 − M^2)``.
        0.0 quando não publicada.
    """
    family: CurveFamily
    vendor: str
    code: str            # C1..C5, U1..U5, IEEE-EI, ANSI-EI, IAC-EI…
    curve_name: str
    a: float             # k (IEC) / A (IEEE) / B da SEL (numerador)
    p: float             # α (IEC) / p (IEEE) / C da SEL (expoente)
    b: float = 0.0       # β (IEEE) / A da SEL (termo constante)
    c: float = 0.0       # GE 5-param apenas
    d: float = 0.0
    e: float = 0.0
    reset_tr: float = 0.0
    reset_denominator: str = "1-M^2"
    source: str = ""


# ---------------------------------------------------------------------------
# SEL — Tabela 1 (IEC) e Tabela 2 (US)
# ---------------------------------------------------------------------------

_SEL_SRC = "SEL RTAC PowerSystemProtection lib, Date Code 20180920, Tab. 1-2"

SEL_IEC_CURVES: tuple[VendorCurveConstants, ...] = (
    VendorCurveConstants(CurveFamily.IEC_60255, "SEL", "C1", "Standard Inverse",
                         a=0.14, p=0.02, reset_tr=13.5, source=_SEL_SRC),
    VendorCurveConstants(CurveFamily.IEC_60255, "SEL", "C2", "Very Inverse",
                         a=13.5, p=1.0, reset_tr=47.3, source=_SEL_SRC),
    VendorCurveConstants(CurveFamily.IEC_60255, "SEL", "C3", "Extremely Inverse",
                         a=80.0, p=2.0, reset_tr=80.0, source=_SEL_SRC),
    VendorCurveConstants(CurveFamily.IEC_60255, "SEL", "C4", "Long-Time Inverse",
                         a=120.0, p=1.0, reset_tr=120.0,
                         reset_denominator="1-M", source=_SEL_SRC),
    VendorCurveConstants(CurveFamily.IEC_60255, "SEL", "C5", "Short-Time Inverse",
                         a=0.05, p=0.04, reset_tr=4.85, source=_SEL_SRC),
)

# SEL publica t = TD·(A + B/(M^C − 1)); aqui a = B (numerador), b = A.
SEL_US_CURVES: tuple[VendorCurveConstants, ...] = (
    VendorCurveConstants(CurveFamily.US_LEGACY_CO, "SEL", "U1", "Moderately Inverse",
                         a=0.0104, p=0.02, b=0.0226, reset_tr=1.08, source=_SEL_SRC),
    VendorCurveConstants(CurveFamily.US_LEGACY_CO, "SEL", "U2", "Inverse",
                         a=5.95, p=2.0, b=0.180, reset_tr=5.95, source=_SEL_SRC),
    VendorCurveConstants(CurveFamily.US_LEGACY_CO, "SEL", "U3", "Very Inverse",
                         a=3.88, p=2.0, b=0.0963, reset_tr=3.88, source=_SEL_SRC),
    VendorCurveConstants(CurveFamily.US_LEGACY_CO, "SEL", "U4", "Extremely Inverse",
                         a=5.67, p=2.0, b=0.0352, reset_tr=5.67, source=_SEL_SRC),
    VendorCurveConstants(CurveFamily.US_LEGACY_CO, "SEL", "U5", "Short-Time Inverse",
                         a=0.00342, p=0.02, b=0.00262, reset_tr=0.323, source=_SEL_SRC),
)


# ---------------------------------------------------------------------------
# GE Multilin 850 — Tabelas 4-34, 4-36, 4-38, 4-40
# ---------------------------------------------------------------------------

_GE_SRC = "GE Multilin 850 Instruction Manual, Tab. 4-34/4-36/4-38/4-40"

GE_IEEE_CURVES: tuple[VendorCurveConstants, ...] = (
    VendorCurveConstants(CurveFamily.IEEE_C37112_ANNEX_A, "GE", "IEEE-EI",
                         "IEEE Extremely Inverse", a=28.2, p=2.0, b=0.1217,
                         reset_tr=29.1, source=_GE_SRC),
    VendorCurveConstants(CurveFamily.IEEE_C37112_ANNEX_A, "GE", "IEEE-VI",
                         "IEEE Very Inverse", a=19.61, p=2.0, b=0.491,
                         reset_tr=21.6, source=_GE_SRC),
    VendorCurveConstants(CurveFamily.IEEE_C37112_ANNEX_A, "GE", "IEEE-MI",
                         "IEEE Moderately Inverse", a=0.0515, p=0.02, b=0.1140,
                         reset_tr=4.85, source=_GE_SRC),
)

# Forma de 5 constantes da GE (A..E); a=A, b=B, p=C, d=D, e=E.
GE_ANSI_CURVES: tuple[VendorCurveConstants, ...] = (
    VendorCurveConstants(CurveFamily.US_LEGACY_CO, "GE", "ANSI-EI",
                         "ANSI Extremely Inverse", a=0.0399, b=0.2294, p=0.5000,
                         d=3.0094, e=0.7222, reset_tr=5.67, source=_GE_SRC),
    VendorCurveConstants(CurveFamily.US_LEGACY_CO, "GE", "ANSI-VI",
                         "ANSI Very Inverse", a=0.0615, b=0.7989, p=0.3400,
                         d=-0.2840, e=4.0505, reset_tr=3.88, source=_GE_SRC),
    VendorCurveConstants(CurveFamily.US_LEGACY_CO, "GE", "ANSI-NI",
                         "ANSI Normally Inverse", a=0.0274, b=2.2614, p=0.3000,
                         d=-4.1899, e=9.1272, reset_tr=5.95, source=_GE_SRC),
    VendorCurveConstants(CurveFamily.US_LEGACY_CO, "GE", "ANSI-MI",
                         "ANSI Moderately Inverse", a=0.1735, b=0.6791, p=0.8000,
                         d=-0.0800, e=0.1271, reset_tr=1.08, source=_GE_SRC),
)

GE_IEC_CURVES: tuple[VendorCurveConstants, ...] = (
    VendorCurveConstants(CurveFamily.IEC_60255, "GE", "IEC-A", "IEC Curve A (BS142)",
                         a=0.140, p=0.020, reset_tr=9.7, source=_GE_SRC),
    VendorCurveConstants(CurveFamily.IEC_60255, "GE", "IEC-B", "IEC Curve B (BS142)",
                         a=13.500, p=1.000, reset_tr=43.2, source=_GE_SRC),
    VendorCurveConstants(CurveFamily.IEC_60255, "GE", "IEC-C", "IEC Curve C (BS142)",
                         a=80.000, p=2.000, reset_tr=58.2, source=_GE_SRC),
    VendorCurveConstants(CurveFamily.IEC_60255, "GE", "IEC-SI", "IEC Short Inverse",
                         a=0.050, p=0.040, reset_tr=0.500, source=_GE_SRC),
)

GE_IAC_CURVES: tuple[VendorCurveConstants, ...] = (
    VendorCurveConstants(CurveFamily.GE_IAC, "GE", "IAC-EI", "IAC Extremely Inverse",
                         a=0.0040, b=0.6379, p=0.6200, d=1.7872, e=0.2461,
                         reset_tr=6.008, source=_GE_SRC),
    VendorCurveConstants(CurveFamily.GE_IAC, "GE", "IAC-VI", "IAC Very Inverse",
                         a=0.0900, b=0.7965, p=0.1000, d=-1.2885, e=7.9586,
                         reset_tr=4.678, source=_GE_SRC),
    VendorCurveConstants(CurveFamily.GE_IAC, "GE", "IAC-I", "IAC Inverse",
                         a=0.2078, b=0.8630, p=0.8000, d=-0.4180, e=0.1947,
                         reset_tr=0.990, source=_GE_SRC),
    VendorCurveConstants(CurveFamily.GE_IAC, "GE", "IAC-SI", "IAC Short Inverse",
                         a=0.0428, b=0.0609, p=0.6200, d=-0.0010, e=0.0221,
                         reset_tr=0.222, source=_GE_SRC),
)


# ---------------------------------------------------------------------------
# ABB REF615R — defaults da curva programável (Tabela 78)
# ---------------------------------------------------------------------------

ABB_REF615R_PROGRAMMABLE_DEFAULTS: VendorCurveConstants = VendorCurveConstants(
    CurveFamily.IEEE_C37112_ANNEX_A, "ABB", "PROG-DEFAULT",
    "Programmable curve factory defaults (= IEEE EI)",
    a=28.2000, p=2.00, b=0.1217, d=29.10, e=1.0, reset_tr=29.10,
    source="ABB REF615R Technical Manual 1MRS240050-IB Rev C, Tab. 78 "
           "(Curve parameter A/B/C/D/E defaults)",
)


ALL_VENDOR_CURVES: tuple[VendorCurveConstants, ...] = (
    SEL_IEC_CURVES + SEL_US_CURVES + GE_IEEE_CURVES + GE_ANSI_CURVES
    + GE_IEC_CURVES + GE_IAC_CURVES + (ABB_REF615R_PROGRAMMABLE_DEFAULTS,)
)


def find_curve(
    *,
    vendor: Optional[str] = None,
    family: Optional[CurveFamily] = None,
    code: Optional[str] = None,
) -> list[VendorCurveConstants]:
    """Filtra o registry por fabricante, família e/ou código."""
    out = list(ALL_VENDOR_CURVES)
    if vendor is not None:
        out = [c for c in out if c.vendor.lower() == vendor.lower()]
    if family is not None:
        out = [c for c in out if c.family == family]
    if code is not None:
        out = [c for c in out if c.code.lower() == code.lower()]
    return out


def operate_time_3param_s(
    current_A: float, pickup_A: float, time_dial: float,
    curve: VendorCurveConstants,
) -> float:
    """
    ``t = TD · (a / (M^p − 1) + b)`` — forma de 3 constantes, **sem**
    divisor de normalização, conforme publicado por SEL, GE (IEEE)
    e ABB. Retorna ``inf`` se M ≤ 1. Só válido para curvas com
    ``c = d = e = 0`` (as formas de 5 constantes da GE não têm
    fórmula fechada transcrita neste módulo).
    """
    if pickup_A <= 0 or current_A <= 0:
        raise ValueError("pickup_A e current_A devem ser > 0")
    if curve.d != 0.0 or curve.e != 0.0:
        raise ValueError(
            f"Curva {curve.code} usa forma de 5 constantes; fórmula "
            "fechada não disponível neste módulo"
        )
    m = current_A / pickup_A
    if m <= 1.0:
        return float("inf")
    return time_dial * (curve.a / (m ** curve.p - 1.0) + curve.b)
