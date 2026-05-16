"""
Exemplo executável: Stevenson §9 Example 9.5 — Power flow 3-bus
Newton-Raphson.

Referência:

* John J. Grainger, William D. Stevenson Jr., *Power System
  Analysis*, McGraw-Hill, 1994 — Capítulo 9, Example 9.5.

Sistema 3-bus
==============

::

    Bus 1 (Slack)        Bus 2 (PV)
       V=1.05∠0°  ─[L]─  V=1.04, P=0.5
            |              |
            └─[L]─Bus 3─[L]┘
                   (PQ)
                P=-1.0, Q=-0.30

Linhas:

* L12: R=0.02, X=0.04 pu
* L13: R=0.01, X=0.03 pu
* L23: R=0.0125, X=0.025 pu

Solução esperada (Stevenson §9.5):

* V₁ = 1.05∠0°
* V₂ = 1.04∠+5.83° (PV bus, |V| fixed, θ varia)
* V₃ ≈ 1.0165∠-1.77°

Convergência: ~4 iterações até max mismatch < 1e-6 pu.
"""

from __future__ import annotations

from app.examples import ExampleResult, _check_tolerance


def run() -> ExampleResult:
    """Roda o exemplo e retorna ExampleResult."""
    from app.postprocessor.power_flow import (
        BusType, PfBranch, PfBus, solve_power_flow,
    )

    # Setup
    buses = [
        PfBus(id="B1", type=BusType.SLACK, V_pu_set=1.05),
        PfBus(id="B2", type=BusType.PV, V_pu_set=1.04, P_pu_set=0.50),
        PfBus(id="B3", type=BusType.PQ, P_pu_set=-1.0, Q_pu_set=-0.30),
    ]
    branches = [
        PfBranch(from_bus="B1", to_bus="B2", R_pu=0.02, X_pu=0.04),
        PfBranch(from_bus="B1", to_bus="B3", R_pu=0.01, X_pu=0.03),
        PfBranch(from_bus="B2", to_bus="B3", R_pu=0.0125, X_pu=0.025),
    ]

    sol = solve_power_flow(buses, branches, tolerance=1e-6)

    # Valores esperados (Stevenson §9.5)
    expected = {
        "V1_mag_pu": 1.05,
        "V2_mag_pu": 1.04,
        "V3_mag_pu": 1.0165,
        "iterations_max": 6.0,
        "converged": 1.0,
    }

    # Valores calculados
    import math
    v1 = sol.bus_voltages_pu["B1"]
    v2 = sol.bus_voltages_pu["B2"]
    v3 = sol.bus_voltages_pu["B3"]
    computed = {
        "V1_mag_pu": abs(v1),
        "V2_mag_pu": abs(v2),
        "V3_mag_pu": abs(v3),
        "iterations_max": float(sol.iterations),
        "converged": 1.0 if sol.converged else 0.0,
    }

    # Tolerância
    tolerance_pct = 2.0  # ±2%
    # Iterações é "menor ou igual", não tolerância simétrica
    iter_ok = sol.iterations <= 6
    converged_ok = sol.converged
    voltages_ok = _check_tolerance(
        {k: v for k, v in expected.items()
         if k.startswith("V")},
        {k: v for k, v in computed.items()
         if k.startswith("V")},
        tolerance_pct,
    )
    passed = iter_ok and converged_ok and voltages_ok

    narrative = (
        "Power flow Newton-Raphson em sistema 3-bus do livro\n"
        "Stevenson (Capítulo 9, Example 9.5).\n"
        "\n"
        "Bus 1 é slack (V=1.05∠0°), Bus 2 é PV (geração\n"
        "regulada V=1.04, P=0.5), Bus 3 é PQ (carga 1.0+j0.3).\n"
        "\n"
        f"Convergência alcançada em {sol.iterations} iterações\n"
        f"(esperado ≤ 6) com max mismatch {sol.max_mismatch:.2e} pu.\n"
        "\n"
        f"Solução resolvida:\n"
        f"  V₁ = {abs(v1):.4f}∠{math.degrees(math.atan2(v1.imag, v1.real)):+.3f}°\n"
        f"  V₂ = {abs(v2):.4f}∠{math.degrees(math.atan2(v2.imag, v2.real)):+.3f}°\n"
        f"  V₃ = {abs(v3):.4f}∠{math.degrees(math.atan2(v3.imag, v3.real)):+.3f}°\n"
        f"\n"
        f"Total de perdas P+jQ na rede: "
        f"{sol.total_losses_pu.real:+.4f} + j{sol.total_losses_pu.imag:+.4f} pu"
    )

    return ExampleResult(
        title="Stevenson §9.5 — Power Flow 3-bus (Newton-Raphson)",
        reference=(
            "Grainger & Stevenson, Power System Analysis, "
            "McGraw-Hill 1994, Chapter 9, Example 9.5"
        ),
        expected=expected,
        computed=computed,
        tolerance_pct=tolerance_pct,
        passed=passed,
        narrative=narrative,
        extras={"solution": sol},
    )


if __name__ == "__main__":
    result = run()
    print(result.summary())
