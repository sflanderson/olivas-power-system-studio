"""
app.standards.csa_z462_arc_flash — CSA Z462 wrapper sobre
IEEE 1584-2018 (v1.6.0 Sprint D).

Fonte primária
==============

CSA Z462-21 (Workplace Electrical Safety), Annex D.1, referencia
**IEEE Std 1584-2018** explicitamente como o método de cálculo
de incident energy. CSA Z462 é o equivalente canadense de NFPA 70E
nos EUA.

Diferenças vs IEEE 1584/NFPA 70E
=================================

CSA Z462 usa **as mesmas equações IEEE 1584-2018**, mas com:

1. **Naming PPE**: "Risk Category 0/1/2/3/4" (CSA Z462) vs
   "PPE Category 0/1/2/3/4" (NFPA 70E). Mesma classificação
   numérica, label diferente.
2. **Working distance defaults** ligeiramente distintos para
   alguns equipamentos (CSA Z462 §D.5):
   * LV painel: 455 mm (NFPA: 457 mm)
   * MV painel: 914 mm (NFPA: 914 mm — igual)
3. **DC arc-flash**: CSA referencia método híbrido Wilkins/Stokes;
   abstraido via :mod:`app.standards.dc_arc_flash`.

API
===

::

    from app.postprocessor.arc_flash import ArcFlashCase
    from app.standards.csa_z462_arc_flash import csa_z462_arc_flash

    case = ArcFlashCase(...)   # mesmo schema do IEEE 1584
    result = csa_z462_arc_flash(case)
    print(f"Incident energy: {result.incident_energy_cal_cm2:.2f}")
    print(f"CSA Risk Category: {result.risk_category}")
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging_config import get_logger
from app.postprocessor.arc_flash import (
    ArcFlashCase, calculate_arc_flash,
)

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CSAZ462Result:
    """
    Resultado CSA Z462 (wrapper IEEE 1584-2018).

    Attributes
    ----------
    incident_energy_cal_cm2:
        Energia incidente (mesma do IEEE 1584).
    arc_flash_boundary_mm:
        AFB (mesma do IEEE 1584).
    risk_category:
        "Risk Cat 0" / "Risk Cat 1" / ... / "Risk Cat 4" /
        "DANGEROUS - Energy > 40 cal/cm²" (CSA Z462 naming).
    ppe_arc_rating_cal_cm2:
        PPE arc rating mínimo (cal/cm²) seguindo Tabela CSA
        Z462 §H.4.
    underlying_method:
        Sempre "IEEE 1584-2018 (per CSA Z462 §D.1)".
    """

    incident_energy_cal_cm2: float
    arc_flash_boundary_mm: float
    risk_category: str
    ppe_arc_rating_cal_cm2: float
    underlying_method: str = "IEEE 1584-2018 (per CSA Z462 §D.1)"


# ---------------------------------------------------------------------------
# CSA Risk Category mapping
# ---------------------------------------------------------------------------


def map_to_csa_risk_category(
    incident_energy_cal_cm2: float,
) -> str:
    """
    Mapeia energia incidente para CSA Risk Category label.

    Tabela CSA Z462-2021 §H.4 (consistente com NFPA 70E §130.7
    em magnitude — apenas naming diferente).

    | Energy | NFPA 70E | CSA Z462 |
    |--------|----------|----------|
    | < 1.2  | Cat 0    | Risk Cat 0 |
    | 1.2-4  | Cat 1    | Risk Cat 1 |
    | 4-8    | Cat 2    | Risk Cat 2 |
    | 8-25   | Cat 3    | Risk Cat 3 |
    | 25-40  | Cat 4    | Risk Cat 4 |
    | > 40   | Dangerous | DANGEROUS - Energy > 40 cal/cm² |
    """
    E = incident_energy_cal_cm2
    if E < 1.2:
        return "Risk Cat 0"
    elif E < 4.0:
        return "Risk Cat 1"
    elif E < 8.0:
        return "Risk Cat 2"
    elif E < 25.0:
        return "Risk Cat 3"
    elif E <= 40.0:
        return "Risk Cat 4"
    else:
        return "DANGEROUS - Energy > 40 cal/cm²"


# Min PPE arc rating por Risk Category (CSA Z462 §H.4)
_PPE_RATING_BY_RISK_CAT = {
    "Risk Cat 0": 0.0,    # No special PPE
    "Risk Cat 1": 4.0,
    "Risk Cat 2": 8.0,
    "Risk Cat 3": 25.0,
    "Risk Cat 4": 40.0,
}


# ---------------------------------------------------------------------------
# Main wrapper
# ---------------------------------------------------------------------------


def csa_z462_arc_flash(case: ArcFlashCase) -> CSAZ462Result:
    """
    Calcula arc-flash via CSA Z462 (que é IEEE 1584-2018 com
    naming PPE diferente).

    1. Chama :func:`calculate_arc_flash` (IEEE 1584-2018) para
       obter incident energy + AFB
    2. Mapeia para CSA Risk Category via tabela §H.4
    3. Lookup PPE arc rating mínimo

    Parameters
    ----------
    case:
        :class:`ArcFlashCase` (mesmo schema usado pelo módulo
        IEEE 1584).

    Returns
    -------
    :class:`CSAZ462Result`
    """
    # Wrap IEEE 1584
    ieee_report = calculate_arc_flash(case)

    E = ieee_report.incident_energy_cal_cm2
    AFB = ieee_report.arc_flash_boundary_mm

    risk_cat = map_to_csa_risk_category(E)
    ppe_rating = _PPE_RATING_BY_RISK_CAT.get(risk_cat, 40.0)

    log.info(
        "CSA Z462 arc-flash: bus=%s, E=%.2f cal/cm² → %s "
        "(PPE rating: %.0f cal/cm²)",
        case.bus_name, E, risk_cat, ppe_rating,
    )

    return CSAZ462Result(
        incident_energy_cal_cm2=E,
        arc_flash_boundary_mm=AFB,
        risk_category=risk_cat,
        ppe_arc_rating_cal_cm2=ppe_rating,
    )
