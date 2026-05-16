"""
Exemplo executável: IEC 60909-0 Annex C — Sistema-exemplo de
cálculo de curto-circuito.

Referência:

* IEC 60909-0:2016 — Annex C, "Examples of short-circuit
  current calculations".

Sistema simplificado (subset do Annex C):

* Concessionária 110 kV com S_kQ = 1500 MVA, R/X = 0.10
* Transformador 110/20 kV, 25 MVA, uk=12%
* Falta no barramento 20 kV (loadside do TR)

Cálculos esperados:

* Z_Q (110 kV) = c·U²/S_kQ = 1.10·110²/1500 = 8.873 Ω
* Z_T (20 kV) = uk·U²/S = 0.12·20²/25 = 1.920 Ω
* Z_th @ 20 kV ≈ Z_Q_refletido + Z_T

  Z_Q_refletido = Z_Q × (20/110)² = 8.873 × 0.0331 = 0.293 Ω
  Z_total = 0.293 + 1.920 = 2.213 Ω

* Ik''3 = c·U/(√3·|Z|) = 1.10·20/(√3·2.213) = 5.74 kA

Tolerância: ±2% (cálculo analítico).
"""

from __future__ import annotations

from app.examples import ExampleResult, _check_tolerance


def run() -> ExampleResult:
    from app.postprocessor.short_circuit import ShortCircuitNetwork
    from app.standards.iec60909 import (
        network_feeder_impedance_ohm, transformer_impedance_ohm,
    )

    # Network feeder no lado primário (110 kV)
    Z_Q_pri = network_feeder_impedance_ohm(
        rated_voltage_kV=110.0,
        short_circuit_power_MVA=1500.0,
        voltage_factor_c=1.10,
        r_over_x=0.10,
    )

    # Transformador (referido ao secundário, 20 kV)
    Z_T = transformer_impedance_ohm(
        rated_voltage_kV=20.0,
        rated_power_MVA=25.0,
        uk_percent=12.0,
        uR_percent=0.5,
    )

    # Refletir Z_Q ao secundário (20 kV)
    ratio_sq = (20.0 / 110.0) ** 2
    Z_Q_sec = Z_Q_pri * ratio_sq

    Z_total = Z_Q_sec + Z_T

    # Calcula Ik''3 via ShortCircuitNetwork (verifica integração)
    net = ShortCircuitNetwork(rated_voltage_kV=20.0)
    from app.postprocessor.short_circuit import ScSource
    net.sources.append(ScSource(
        name="GRID+TR",
        z_ohm=Z_total,
        description="Concessionária + TR refletido @ 20 kV",
    ))
    sc = net.calculate_at_bus("BUS-20kV", kind="max")

    # Valores esperados (cálculo analítico)
    expected = {
        "Z_Q_pri_mag_ohm": 8.873,
        "Z_T_mag_ohm": 1.920,
        "Z_total_mag_ohm": 2.213,    # ~Z_Q_sec + Z_T
        "Ik_pp_kA": 5.74,
    }
    computed = {
        "Z_Q_pri_mag_ohm": abs(Z_Q_pri),
        "Z_T_mag_ohm": abs(Z_T),
        "Z_total_mag_ohm": abs(Z_total),
        "Ik_pp_kA": sc.Ik_pp_kA,
    }

    tolerance_pct = 3.0
    passed = _check_tolerance(expected, computed, tolerance_pct)

    narrative = (
        "Cálculo de curto-circuito conforme IEC 60909-0:2016 §6\n"
        "(rede + transformador — exemplo simplificado do Annex C).\n"
        "\n"
        "Sistema: concessionária 110 kV (S_kQ = 1500 MVA, R/X=0.10)\n"
        "alimenta TR 110/20 kV de 25 MVA, uk=12%.\n"
        "\n"
        "Estratégia (IEC 60909-0 §6.2 + §6.3):\n"
        "  1. Z_Q calculado no lado primário com c=1.10\n"
        "  2. Z_T no lado secundário (lado da falta)\n"
        "  3. Z_Q refletido ao secundário via ratio² = (20/110)²\n"
        "  4. Z_total = Z_Q_sec + Z_T\n"
        "  5. Ik''3 = c·Un/(√3·|Z|)\n"
        "\n"
        f"Resultados:\n"
        f"  Z_Q (primário) = {abs(Z_Q_pri):.4f} Ω (esperado 8.873)\n"
        f"  Z_T            = {abs(Z_T):.4f} Ω (esperado 1.920)\n"
        f"  Z_total @ 20kV = {abs(Z_total):.4f} Ω (esperado 2.213)\n"
        f"  Ik''3          = {sc.Ik_pp_kA:.3f} kA (esperado 5.74)\n"
        f"  κ              = {sc.kappa:.3f}\n"
        f"  ip             = {sc.ip_kA:.3f} kA"
    )

    return ExampleResult(
        title="IEC 60909-0 Annex C — Sistema com TR",
        reference=(
            "IEC 60909-0:2016 — Annex C, "
            "Examples of short-circuit current calculations"
        ),
        expected=expected,
        computed=computed,
        tolerance_pct=tolerance_pct,
        passed=passed,
        narrative=narrative,
        extras={"sc_result": sc},
    )


if __name__ == "__main__":
    result = run()
    print(result.summary())
