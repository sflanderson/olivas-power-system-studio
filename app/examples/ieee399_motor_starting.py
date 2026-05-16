"""
Exemplo executável: IEEE 399 (Brown Book) §10 — Motor starting.

Referência:

* IEEE Std 399-1997 (Brown Book) — *Industrial and Commercial
  Power System Analysis*, §10 Motor Starting Studies.

Cenário típico industrial:

* Motor: 1500 kW, 4.16 kV, η=0.96, pf=0.88, 4 polos
* I_LR = 6× I_n
* Torque partida = 1.4× T_n; carga constante 1.0× T_n
* Inércia 80 kg·m²
* Bus pré-partida: V = 0.97 pu (do PF)
* Z_th do sistema: 0.10 Ω (rede industrial forte 4.16 kV
  com S_kQ ~ 200 MVA)

Esperado (IEEE 399 §10):

* Voltage dip moderado → ACCEPTABLE (V > 0.85 pu)
* Tempo de partida < 5 segundos
* Categoria de aceitação: ACCEPTABLE
"""

from __future__ import annotations

from app.examples import ExampleResult, _check_tolerance


def run() -> ExampleResult:
    from app.postprocessor.motor_starting import (
        LoadType, MotorStartingCase, StartingResult,
        analyze_motor_starting,
    )

    case = MotorStartingCase(
        motor_name="M-MAIN-1500",
        motor_rated_power_kW=1500.0,
        motor_rated_voltage_kV=4.16,
        motor_rated_pf=0.88,
        motor_efficiency=0.96,
        locked_rotor_current_pu=6.0,
        starting_pf=0.30,
        starting_torque_pu=1.4,
        load_torque_pu=1.0,
        inertia_motor_kg_m2=80.0,
        bus_pre_fault_voltage_pu=0.97,
        bus_thevenin_impedance_ohm=0.10,
        bus_rated_voltage_kV=4.16,
        n_poles=4,
        load_type=LoadType.CONSTANT,
    )
    rpt = analyze_motor_starting(case)

    expected = {
        "voltage_dip_pu_min": 0.85,    # > 0.85 → ACCEPTABLE
        "starting_time_max_s": 5.0,
        "acceptance_int": 1.0,         # ACCEPTABLE = 1
    }
    # Map StartingResult enum
    accept_map = {
        StartingResult.ACCEPTABLE: 1.0,
        StartingResult.MARGINAL: 0.5,
        StartingResult.UNACCEPTABLE: 0.0,
    }
    computed = {
        "voltage_dip_pu_min": rpt.voltage_dip_pu,
        "starting_time_max_s": rpt.starting_time_s,
        "acceptance_int": accept_map[rpt.acceptance],
    }

    tolerance_pct = 10.0
    # Aceitação binária (não tolerância simétrica)
    v_ok = rpt.voltage_dip_pu > 0.85
    t_ok = rpt.starting_time_s < 5.0
    accept_ok = rpt.acceptance == StartingResult.ACCEPTABLE
    passed = v_ok and t_ok and accept_ok

    narrative = (
        "Análise de partida de motor industrial conforme\n"
        "IEEE Std 399-1997 §10 (Brown Book).\n"
        "\n"
        "Motor 1500 kW / 4.16 kV alimenta carga constante (guincho/\n"
        "esteira). Sistema de alimentação tem Z_th = 0.5 Ω (rede\n"
        "forte) e tensão pré-partida 0.97 pu (vinda de PF).\n"
        "\n"
        "Critério IEEE 399 §10:\n"
        "  • V_during > 0.85 pu → ACCEPTABLE\n"
        "  • 0.80 < V ≤ 0.85   → MARGINAL (avaliar impacto)\n"
        "  • V ≤ 0.80          → UNACCEPTABLE (use VFD/soft-starter)\n"
        "\n"
        "Modelagem:\n"
        "  • Voltage dip = V_pre × Z_M / (Z_th + Z_M)\n"
        "  • Z_M = (1/I_LR_pu) × V²/S_motor\n"
        "  • t_start = J × Δω / (T_motor_avg - T_load_avg)\n"
        "\n"
        f"Resultados:\n"
        f"  V_during    = {rpt.voltage_dip_pu:.4f} pu "
        f"(esperado > 0.85)\n"
        f"  Voltage dip = {rpt.voltage_dip_pct:.2f}%\n"
        f"  Iarc        = {rpt.starting_current_kA:.3f} kA\n"
        f"  S_partida   = {rpt.starting_apparent_power_MVA:.2f} MVA\n"
        f"  Tempo→95%   = {rpt.starting_time_s:.2f} s "
        f"(esperado < 5)\n"
        f"  Aceitação   = {rpt.acceptance.value.upper()}"
    )

    return ExampleResult(
        title="IEEE 399 §10 — Partida Motor 1500 kW",
        reference=(
            "IEEE Std 399-1997 Brown Book §10 — "
            "Motor Starting Studies"
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
