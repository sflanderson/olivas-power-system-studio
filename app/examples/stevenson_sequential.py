"""
Exemplo executável: Stevenson §11 — Componentes simétricas
0/1/2 e faltas assimétricas.

Referência:

* Grainger & Stevenson, *Power System Analysis*, McGraw-Hill,
  1994 — Capítulo 11.

Cenário canônico
=================

Sistema 13.8 kV solidamente aterrado, gerador síncrono 100 MVA
com:

* X_d'' = 0.20 pu (subtransient positive sequence)
* X_2  = 0.20 pu (negative sequence ≈ X_d'')
* X_0  = 0.10 pu (zero sequence — leakage)

Usando V_th = 1.0 pu (sem c-factor), Z em pu:

* Z_1 = j0.20
* Z_2 = j0.20
* Z_0 = j0.10

Faltas no terminal do gerador:

* **Trifásica**: Ik''3 = 1/Z_1 = 1/0.20 = 5.0 pu
* **Bifásica**: Ik''2 = (√3/2)·Ik''3 = 4.33 pu
* **LG**: Ik''1 = 3·V/(Z₁+Z₂+Z₀) = 3/0.50 = 6.0 pu (mais
  severa que trifásica! Característica de TN)
* **LLG**: complex (não detalhado aqui)

Ratio Ik''1/Ik''3 = 1.20 (sistema com Z₀ menor que Z₁ ⇒
falta LG amplificada).
"""

from __future__ import annotations

from app.examples import ExampleResult, _check_tolerance


def run() -> ExampleResult:
    from app.standards.iec60909_seq import (
        SequenceImpedances, calculate_all_faults,
        GroundingType,
    )

    # Sistema em pu (Un=1.0, Z em pu)
    # Para evitar denominadores em pu: usamos V real = 1 pu × 13.8 kV
    Un_kV = 13.8
    base_Z = Un_kV ** 2 / 100.0   # 100 MVA → Z_base = 1.904 Ω

    # Z em ohms (já que iec60909_seq usa V em kV e Z em ohms)
    Z1 = complex(0, 0.20 * base_Z)
    Z2 = complex(0, 0.20 * base_Z)
    Z0 = complex(0, 0.10 * base_Z)
    seq = SequenceImpedances(Z1=Z1, Z2=Z2, Z0=Z0)

    result = calculate_all_faults(
        Un_kV=Un_kV, seq_impedances=seq,
        grounding=GroundingType.SOLIDLY_GROUNDED,
        voltage_factor_c=1.00,   # Stevenson usa V_th = 1.0 pu
    )

    # Convertendo de kA para pu para comparar com Stevenson
    I_base_kA = 100.0 / (3 ** 0.5 * Un_kV)   # I_base @ 100 MVA, 13.8 kV
    Ik3_pu = result.Ik3_kA / I_base_kA
    Ik2_pu = result.Ik2_kA / I_base_kA
    Ik1_pu = result.Ik1_kA / I_base_kA

    expected = {
        "Ik3_pu": 5.0,                # 1/X_1 = 1/0.20
        "Ik2_pu": 5.0 * (3 ** 0.5) / 2,  # 4.330
        "Ik1_pu": 6.0,                # 3·V/(X1+X2+X0)
        "Ik1_to_Ik3_ratio": 1.20,
    }

    computed = {
        "Ik3_pu": Ik3_pu,
        "Ik2_pu": Ik2_pu,
        "Ik1_pu": Ik1_pu,
        "Ik1_to_Ik3_ratio": result.Ik1_to_Ik3_ratio,
    }

    tolerance_pct = 1.0   # cálculo analítico exato — tolerância apertada
    passed = _check_tolerance(expected, computed, tolerance_pct)

    narrative = (
        "Faltas assimétricas em terminal de gerador 100 MVA / 13.8 kV\n"
        "solidamente aterrado.\n"
        "\n"
        "Cenário Stevenson §11: gerador com X_d''=0.20, X_2=0.20,\n"
        "X_0=0.10 pu.\n"
        "\n"
        "Característica importante: para X_0 < X_1 (TN típico),\n"
        "**a falta monofásica é MAIS SEVERA que a trifásica**.\n"
        "Isto justifica dimensionamento de aterramento e malha\n"
        "de terra para Ik1 (não Ik3).\n"
        "\n"
        f"Ik''3 (3φ)         = {result.Ik3_kA:.3f} kA = {Ik3_pu:.3f} pu\n"
        f"Ik''2 (LL)         = {result.Ik2_kA:.3f} kA = {Ik2_pu:.3f} pu\n"
        f"Ik''1 (LG)         = {result.Ik1_kA:.3f} kA = {Ik1_pu:.3f} pu\n"
        f"\n"
        f"Razão Ik1/Ik3 = {result.Ik1_to_Ik3_ratio:.3f} "
        "→ falta LG é dominante.\n"
        f"\n"
        "Conclusão: dimensionar relé 50N/51N para detectar\n"
        f"corrente de terra de aproximadamente {result.Ik1_kA:.1f} kA\n"
        "no terminal."
    )

    return ExampleResult(
        title="Stevenson §11 — Faltas Assimétricas (sequencial 0/1/2)",
        reference=(
            "Grainger & Stevenson, Power System Analysis, "
            "McGraw-Hill 1994, Chapter 11"
        ),
        expected=expected,
        computed=computed,
        tolerance_pct=tolerance_pct,
        passed=passed,
        narrative=narrative,
        extras={"fault_result": result},
    )


if __name__ == "__main__":
    result = run()
    print(result.summary())
