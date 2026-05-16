"""
Exemplo executável: NBR 17227:2025 — Worked example arc-flash
em sistema MV brasileiro.

Referência:

* ABNT NBR 17227:2025 — *Arco elétrico — Gerenciamento de
  risco de energia incidente, precauções e métodos de
  cálculo*.

Cenário típico industrial brasileiro:

* Subestação 13.8 kV (MV)
* Switchgear (conjunto de manobra) classe 15 kV
* Gap entre fases típico G = 152 mm (NBR 17227 Tabela 1)
* Distância de trabalho D = 914.4 mm (NBR 17227 Tabela 3)
* Eletrodos VCB (vertical em invólucro)
* Falta franca trifásica Ibf = 18 kA
* Tempo de extinção total T = 200 ms (relé 51 + breaker)

Esperado:

* Iarc ≈ 16-17 kA (corrente reduzida pela impedância do arco)
* E ≈ 17-19 cal/cm² (Cat 3 — 8 < E ≤ 25)
* DLA ≈ 2-3 metros
"""

from __future__ import annotations

from app.examples import ExampleResult, _check_tolerance


def run() -> ExampleResult:
    from app.postprocessor.arc_flash import (
        ArcFlashCase, calculate_arc_flash,
    )
    from app.standards.nbr17227 import (
        ElectrodeConfig, EquipmentClass,
    )

    case = ArcFlashCase(
        bus_name="SWGR-13.8",
        rated_voltage_kV=13.8,
        bolted_fault_current_kA=18.0,
        arc_clearing_time_ms=200.0,
        equipment_class=EquipmentClass.SWITCHGEAR_15KV,
        electrode_config=ElectrodeConfig.VCB,
        gap_mm=152.0,
        working_distance_mm=914.4,
    )
    rpt = calculate_arc_flash(case)

    expected = {
        "Iarc_kA": 16.5,
        "incident_energy_cal_cm2": 18.0,
        "ppe_category_int": 3.0,
    }
    cat_str = rpt.ppe_category.value
    cat_int = int(cat_str) if cat_str.isdigit() else 5
    computed = {
        "Iarc_kA": rpt.Iarc_kA,
        "incident_energy_cal_cm2": rpt.incident_energy_cal_cm2,
        "ppe_category_int": float(cat_int),
    }

    tolerance_pct = 15.0
    iarc_ok = abs(rpt.Iarc_kA - 16.5) / 16.5 < tolerance_pct / 100
    energy_ok = abs(
        rpt.incident_energy_cal_cm2 - 18.0
    ) / 18.0 < tolerance_pct / 100
    cat_ok = abs(cat_int - 3) <= 1
    passed = iarc_ok and energy_ok and cat_ok

    narrative = (
        "Análise arc-flash em switchgear 13.8 kV conforme\n"
        "ABNT NBR 17227:2025 (adoção brasileira da IEEE 1584:2018).\n"
        "\n"
        "Sistema típico industrial brasileiro:\n"
        "  • Subestação 13.8 kV / classe 15 kV\n"
        "  • Switchgear metalclad com eletrodos VCB\n"
        "  • Falta franca de 18 kA\n"
        "  • Coordenação principal: 200 ms (50/51 + breaker MV)\n"
        "\n"
        "Parâmetros NBR 17227 §5.2.2 (escopo válido):\n"
        "  • Voltage range: 0.208–15 kV ✓ (13.8 kV)\n"
        "  • Ibf: 0.2–65 kA  ✓ (18 kA)\n"
        "  • Gap: 19.05–254 mm  ✓ (152 mm Tabela 1)\n"
        "  • D ≥ 305 mm  ✓ (914.4 mm Tabela 3)\n"
        "\n"
        f"Resultados:\n"
        f"  Iarc        = {rpt.Iarc_kA:.3f} kA\n"
        f"  Iarc_min    = {rpt.Iarc_min_kA:.3f} kA\n"
        f"  E (max)     = {rpt.incident_energy_cal_cm2:.3f} cal/cm²\n"
        f"  DLA         = {rpt.arc_flash_boundary_mm:.0f} mm "
        f"({rpt.arc_flash_boundary_mm/1000:.2f} m)\n"
        f"  Categoria   = {rpt.ppe_category.value}\n"
        f"  EPI mínimo  = {rpt.ppe_arc_rating_min_cal_cm2:.0f} cal/cm²\n"
        "\n"
        "Recomendações operacionais (NBR 17227 §6):\n"
        "  • EPI: Cat 3 (calça + camisa de manga longa ARC 25 cal/cm²,\n"
        "    capuz balaclava + face shield).\n"
        "  • Sinalização: zona de DLA com fita amarela.\n"
        "  • Considerar AFD (Arc Fault Detection) para reduzir\n"
        "    T para 10 ms — categoria cairia para 0/1.\n"
        "  • Ou redução de Ibf via NGR/IT — mas NBR alerta que\n"
        "    isso aumenta T por menor sensibilidade do 51N."
    )

    return ExampleResult(
        title="NBR 17227 — Arc-flash 13.8 kV switchgear",
        reference=(
            "ABNT NBR 17227:2025 §5.2 + §6 / IEEE 1584:2018"
        ),
        expected=expected,
        computed=computed,
        tolerance_pct=tolerance_pct,
        passed=passed,
        narrative=narrative,
        extras={"report": rpt},
    )


if __name__ == "__main__":
    result = run()
    print(result.summary())
