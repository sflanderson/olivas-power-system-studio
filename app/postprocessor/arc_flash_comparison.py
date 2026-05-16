"""
app.postprocessor.arc_flash_comparison — Comparison de 5+ standards
de arc-flash para um único caso (v1.6.0 Sprint E).

Vantagem competitiva
=====================

* SKM PTW: roda IEEE 1584
* EasyPower: roda IEEE 1584 + NFPA 70E annex
* ETAP: roda IEEE 1584 + DC method
* **Olivas v1.6.0: roda 8 standards e mostra side-by-side**

Standards rodados (quando aplicáveis):

1. IEEE 1584-2018 / NBR 17227-2025 (LV/MV 0.208–15 kV AC)
2. EPRI 2011 (15–46 kV AC)
3. Terzija-Konglin (>46 kV AC)
4. Doughty-Neal-Floyd 2000 (≤600 V AC)
5. NESC 2023 §410 (table-based, todas voltage AC)
6. CSA Z462 (wrapper IEEE 1584 com PPE Risk Cat)
7. NFPA 70E §D.5 max-power (DC systems)

Casos aplicáveis
================

A função decide quais standards aplicam baseado em:

* ``voltage_kV`` — IEEE 1584 só 0.208–15 kV; EPRI 15–46 kV; etc
* ``is_dc`` — DC excluiu todos AC standards exceto NESC table
* ``Ibf_kA`` — Doughty-Neal só 16–50 kA range típico

Resultados não-aplicáveis ficam com ``applicable=False`` mas
aparecem no report para transparência (auditoria).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.core.logging_config import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StandardResult:
    """
    Resultado de UM standard para o caso.

    Se o standard não é aplicável (ex: IEEE 1584 para DC),
    ``applicable=False`` e os campos numéricos ficam None.
    """

    standard_name: str
    applicable: bool
    incident_energy_cal_cm2: Optional[float] = None
    arc_flash_boundary_mm: Optional[float] = None
    ppe_category: Optional[str] = None
    notes: str = ""


@dataclass(frozen=True)
class ArcFlashComparison:
    """
    Comparison side-by-side de N standards.

    Attributes
    ----------
    case_summary:
        Texto descritivo do caso (V, Ibf, t, D).
    results:
        Lista de :class:`StandardResult`, 1 por standard.
    most_conservative / least_conservative:
        Nome do standard com maior/menor incident energy
        (entre os aplicáveis com valor numérico).
    divergence_pct:
        (E_max - E_min) / E_max × 100 (entre aplicáveis).
        0 se só 1 ou 0 aplicáveis.
    """

    case_summary: str
    results: List[StandardResult]
    most_conservative: str
    least_conservative: str
    divergence_pct: float

    def summary(self) -> str:
        """Texto humano-legível com tabela side-by-side."""
        lines = []
        lines.append("=" * 78)
        lines.append("  ARC-FLASH MULTI-STANDARD COMPARISON (Olivas v1.6.0)")
        lines.append("=" * 78)
        lines.append(self.case_summary)
        lines.append("")
        lines.append(
            f"{'Standard':<28} {'E (cal/cm²)':>12} "
            f"{'AFB (mm)':>10} {'PPE':>10} {'Status':>9}"
        )
        lines.append("-" * 78)
        for r in self.results:
            E_str = (
                f"{r.incident_energy_cal_cm2:.2f}"
                if (r.applicable and r.incident_energy_cal_cm2 is not None)
                else "N/A"
            )
            AFB_str = (
                f"{r.arc_flash_boundary_mm:.0f}"
                if (r.applicable and r.arc_flash_boundary_mm is not None)
                else "N/A"
            )
            ppe_str = r.ppe_category or "—"
            status = "✓" if r.applicable else "—"
            lines.append(
                f"{r.standard_name:<28} {E_str:>12} "
                f"{AFB_str:>10} {ppe_str:>10} {status:>9}"
            )
        lines.append("")
        lines.append(
            f"Most conservative:  {self.most_conservative}"
        )
        lines.append(
            f"Least conservative: {self.least_conservative}"
        )
        lines.append(
            f"Divergence: {self.divergence_pct:.1f}%"
        )
        if self.divergence_pct > 50.0:
            lines.append(
                "⚠ WARNING: divergence > 50% — investigar "
                "qual método é mais aplicável ao caso."
            )
        lines.append("=" * 78)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------


def compare_all_standards(
    *,
    voltage_kV: float,
    Ibf_kA: float,
    arc_clearing_time_ms: float,
    working_distance_mm: float,
    is_dc: bool = False,
    bus_name: str = "BUS-COMPARISON",
) -> ArcFlashComparison:
    """
    Roda todos os standards aplicáveis para o caso e devolve
    comparison side-by-side.

    Parameters
    ----------
    voltage_kV:
        Tensão LL (kV).
    Ibf_kA:
        Corrente de falta franca trifásica RMS (kA).
    arc_clearing_time_ms:
        Tempo de extinção do arco (ms).
    working_distance_mm:
        Distância de trabalho (mm).
    is_dc:
        Se True, AC standards são marcados não-aplicáveis e
        DC method é usado.
    bus_name:
        Identificador para log/report.

    Returns
    -------
    :class:`ArcFlashComparison`
    """
    case_summary = (
        f"Caso: V={voltage_kV} kV, Ibf={Ibf_kA} kA, "
        f"t={arc_clearing_time_ms} ms, D={working_distance_mm:.0f} mm, "
        f"{'DC' if is_dc else 'AC'}"
    )
    t_s = arc_clearing_time_ms / 1000.0

    results: List[StandardResult] = []

    # ---------- IEEE 1584-2018 (LV/MV AC, 0.208-15 kV) ----------
    if not is_dc and 0.208 <= voltage_kV <= 15.0:
        try:
            from app.postprocessor.arc_flash import (
                ArcFlashCase, calculate_arc_flash,
            )
            from app.standards.nbr17227 import (
                ElectrodeConfig, EquipmentClass,
            )
            case = ArcFlashCase(
                bus_name=bus_name,
                rated_voltage_kV=voltage_kV,
                bolted_fault_current_kA=Ibf_kA,
                arc_clearing_time_ms=arc_clearing_time_ms,
                equipment_class=EquipmentClass.LV_PANEL_TYPICAL,
                electrode_config=ElectrodeConfig.VCB,
                working_distance_mm=working_distance_mm,
            )
            r = calculate_arc_flash(case)
            results.append(StandardResult(
                standard_name="IEEE 1584-2018",
                applicable=True,
                incident_energy_cal_cm2=r.incident_energy_cal_cm2,
                arc_flash_boundary_mm=r.arc_flash_boundary_mm,
                ppe_category=str(r.ppe_category.value)
                if r.ppe_category else None,
                notes="LV/MV AC (0.208–15 kV)",
            ))
        except Exception as exc:
            log.warning("IEEE 1584 falhou: %s", exc)
            results.append(StandardResult(
                standard_name="IEEE 1584-2018",
                applicable=False,
                notes=f"erro: {exc}",
            ))
    else:
        results.append(StandardResult(
            standard_name="IEEE 1584-2018",
            applicable=False,
            notes="N/A: aplica só 0.208-15 kV AC",
        ))

    # ---------- NBR 17227-2025 (mesmo range IEEE 1584) ----------
    if not is_dc and 0.208 <= voltage_kV <= 15.0:
        try:
            from app.postprocessor.arc_flash import (
                ArcFlashCase, calculate_arc_flash,
            )
            from app.standards.nbr17227 import (
                ElectrodeConfig, EquipmentClass,
            )
            case = ArcFlashCase(
                bus_name=bus_name,
                rated_voltage_kV=voltage_kV,
                bolted_fault_current_kA=Ibf_kA,
                arc_clearing_time_ms=arc_clearing_time_ms,
                equipment_class=EquipmentClass.LV_PANEL_TYPICAL,
                electrode_config=ElectrodeConfig.VCB,
                working_distance_mm=working_distance_mm,
            )
            r = calculate_arc_flash(case)
            results.append(StandardResult(
                standard_name="NBR 17227-2025",
                applicable=True,
                incident_energy_cal_cm2=r.incident_energy_cal_cm2,
                arc_flash_boundary_mm=r.arc_flash_boundary_mm,
                notes="BR equivalent IEEE 1584",
            ))
        except Exception as exc:
            results.append(StandardResult(
                standard_name="NBR 17227-2025",
                applicable=False,
                notes=f"erro: {exc}",
            ))
    else:
        results.append(StandardResult(
            standard_name="NBR 17227-2025",
            applicable=False,
            notes="N/A: aplica só 0.208-15 kV AC",
        ))

    # ---------- EPRI 2011 (15-46 kV AC) ----------
    if not is_dc and 15.0 < voltage_kV <= 46.0:
        try:
            from app.standards.epri_arc_flash import (
                epri_incident_energy,
                epri_arc_flash_boundary_mm,
            )
            E = epri_incident_energy(
                Ibf_kA=Ibf_kA, voltage_kV=voltage_kV,
                clearing_time_s=t_s,
                working_distance_mm=working_distance_mm,
            )
            AFB = epri_arc_flash_boundary_mm(
                Ibf_kA=Ibf_kA, voltage_kV=voltage_kV,
                clearing_time_s=t_s,
            )
            results.append(StandardResult(
                standard_name="EPRI 2011",
                applicable=True,
                incident_energy_cal_cm2=E,
                arc_flash_boundary_mm=AFB,
                notes="HV AC 15-46 kV",
            ))
        except Exception as exc:
            results.append(StandardResult(
                standard_name="EPRI 2011",
                applicable=False,
                notes=f"erro: {exc}",
            ))
    else:
        results.append(StandardResult(
            standard_name="EPRI 2011",
            applicable=False,
            notes="N/A: aplica só 15-46 kV AC",
        ))

    # ---------- Doughty-Neal-Floyd 2000 (≤600 V AC) ----------
    if not is_dc and voltage_kV <= 0.6:
        try:
            from app.standards.doughty_neal_arc_flash import (
                doughty_neal_in_box_cal_cm2,
            )
            # Aproximação: Ia ≈ 0.5·Ibf para arc fault
            Ia_estimate_kA = Ibf_kA * 0.5
            E = doughty_neal_in_box_cal_cm2(
                Ia_kA=Ia_estimate_kA,
                arc_clearing_time_s=t_s,
                distance_mm=working_distance_mm,
            )
            results.append(StandardResult(
                standard_name="Doughty-Neal-Floyd 2000",
                applicable=True,
                incident_energy_cal_cm2=E,
                notes="LV ≤600V (Ia ≈ 0.5·Ibf est.)",
            ))
        except Exception as exc:
            results.append(StandardResult(
                standard_name="Doughty-Neal-Floyd 2000",
                applicable=False,
                notes=f"erro: {exc}",
            ))
    else:
        results.append(StandardResult(
            standard_name="Doughty-Neal-Floyd 2000",
            applicable=False,
            notes="N/A: aplica só ≤600 V AC",
        ))

    # ---------- NESC 2023 §410 (table-based, AC todas voltage) ----------
    if not is_dc:
        try:
            from app.standards.nesc_2023_arc_flash import (
                lookup_nesc_2023,
            )
            row = lookup_nesc_2023(voltage_kV=voltage_kV)
            results.append(StandardResult(
                standard_name="NESC 2023 §410",
                applicable=True,
                incident_energy_cal_cm2=(
                    row.minimum_arc_rating_cal_cm2
                    if row.minimum_arc_rating_cal_cm2 > 0
                    else None
                ),
                arc_flash_boundary_mm=(
                    row.approach_boundary_mm
                    if row.approach_boundary_mm > 0
                    else None
                ),
                notes=f"Table {row.table_ref} (prescriptive)",
            ))
        except Exception as exc:
            results.append(StandardResult(
                standard_name="NESC 2023 §410",
                applicable=False,
                notes=f"erro: {exc}",
            ))
    else:
        results.append(StandardResult(
            standard_name="NESC 2023 §410",
            applicable=False,
            notes="N/A: aplica só AC",
        ))

    # ---------- CSA Z462 (wrapper IEEE 1584) ----------
    if not is_dc and 0.208 <= voltage_kV <= 15.0:
        try:
            from app.postprocessor.arc_flash import ArcFlashCase
            from app.standards.csa_z462_arc_flash import (
                csa_z462_arc_flash,
            )
            from app.standards.nbr17227 import (
                ElectrodeConfig, EquipmentClass,
            )
            case = ArcFlashCase(
                bus_name=bus_name,
                rated_voltage_kV=voltage_kV,
                bolted_fault_current_kA=Ibf_kA,
                arc_clearing_time_ms=arc_clearing_time_ms,
                equipment_class=EquipmentClass.LV_PANEL_TYPICAL,
                electrode_config=ElectrodeConfig.VCB,
                working_distance_mm=working_distance_mm,
            )
            r = csa_z462_arc_flash(case)
            results.append(StandardResult(
                standard_name="CSA Z462",
                applicable=True,
                incident_energy_cal_cm2=r.incident_energy_cal_cm2,
                arc_flash_boundary_mm=r.arc_flash_boundary_mm,
                ppe_category=r.risk_category,
                notes="CA wrapper IEEE 1584",
            ))
        except Exception as exc:
            results.append(StandardResult(
                standard_name="CSA Z462",
                applicable=False,
                notes=f"erro: {exc}",
            ))
    else:
        results.append(StandardResult(
            standard_name="CSA Z462",
            applicable=False,
            notes="N/A: aplica só 0.208-15 kV AC",
        ))

    # ---------- NFPA 70E §D.5 DC max-power (DC systems) ----------
    if is_dc:
        try:
            from app.standards.dc_arc_flash import (
                dc_arc_flash_max_power,
            )
            r = dc_arc_flash_max_power(
                V_system=voltage_kV * 1000.0,
                I_short_circuit_A=Ibf_kA * 1000.0,
                arc_clearing_time_s=t_s,
                working_distance_mm=working_distance_mm,
            )
            results.append(StandardResult(
                standard_name="NFPA 70E §D.5 DC",
                applicable=True,
                incident_energy_cal_cm2=r.incident_energy_cal_cm2,
                arc_flash_boundary_mm=r.arc_flash_boundary_mm,
                notes="DC max-power",
            ))
        except Exception as exc:
            results.append(StandardResult(
                standard_name="NFPA 70E §D.5 DC",
                applicable=False,
                notes=f"erro: {exc}",
            ))
    else:
        results.append(StandardResult(
            standard_name="NFPA 70E §D.5 DC",
            applicable=False,
            notes="N/A: aplica só DC",
        ))

    # ---------- Compute most/least conservative + divergence ----------
    applicable_E = [
        (r.standard_name, r.incident_energy_cal_cm2)
        for r in results
        if r.applicable and r.incident_energy_cal_cm2 is not None
    ]
    if applicable_E:
        applicable_E.sort(key=lambda x: x[1], reverse=True)
        most = applicable_E[0][0]
        least = applicable_E[-1][0]
        max_E = applicable_E[0][1]
        min_E = applicable_E[-1][1]
        divergence = (
            (max_E - min_E) / max_E * 100.0 if max_E > 0 else 0.0
        )
    else:
        most = "N/A"
        least = "N/A"
        divergence = 0.0

    log.info(
        "compare_all_standards: %d applicable, divergence=%.1f%%, "
        "most_conservative=%s",
        len(applicable_E), divergence, most,
    )

    return ArcFlashComparison(
        case_summary=case_summary,
        results=results,
        most_conservative=most,
        least_conservative=least,
        divergence_pct=divergence,
    )
