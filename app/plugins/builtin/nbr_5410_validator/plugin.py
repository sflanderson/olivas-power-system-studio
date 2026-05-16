"""
Builtin plugin: NBR 5410 Validator
====================================

Valida um circuito terminal contra ABNT NBR 5410:2004:

* §6.2.7 — Queda de tensão máxima (4% iluminação, 5% tomadas)
* §6.2.5 — Fator de correção FCt (temperatura) e FCa (agrupamento)
* §5.3.4 — Proteção contra sobrecorrente: In ≤ Iz·FC

Implementa o Sandia simplificado adaptado ao contexto NBR.
"""

from app.plugins import register_study


@register_study("nbr_5410_circuit_check")
def validate_circuit(
    project=None,
    *,
    circuit_type: str = "tomadas",   # "iluminacao" | "tomadas"
    Ib_A: float,
    cable_Iz_A: float,
    fc_temperature: float = 1.0,
    fc_grouping: float = 1.0,
    voltage_drop_pct: float,
    breaker_In_A: float,
):
    """
    Returns dict com 3 checks (queda V / FC / proteção).

    Cada check é {ok: bool, value: float, limit: float, msg: str}.
    """
    # Queda de tensão
    vd_limit = 4.0 if circuit_type == "iluminacao" else 5.0
    vd_ok = voltage_drop_pct <= vd_limit

    # FC (Iz' = Iz × FCt × FCa ≥ Ib)
    iz_corrected = cable_Iz_A * fc_temperature * fc_grouping
    fc_ok = iz_corrected >= Ib_A

    # Proteção: In ≤ Iz' (NBR 5410 §5.3.4)
    prot_ok = breaker_In_A <= iz_corrected

    all_ok = vd_ok and fc_ok and prot_ok

    return {
        "all_ok": all_ok,
        "checks": {
            "voltage_drop": {
                "ok": vd_ok,
                "value": voltage_drop_pct,
                "limit": vd_limit,
                "unit": "%",
                "rule": f"NBR 5410 §6.2.7 ({circuit_type})",
            },
            "fc_correction": {
                "ok": fc_ok,
                "iz_corrected_A": round(iz_corrected, 1),
                "ib_A": Ib_A,
                "rule": "NBR 5410 §6.2.5 (Iz×FCt×FCa ≥ Ib)",
            },
            "overcurrent_protection": {
                "ok": prot_ok,
                "in_A": breaker_In_A,
                "iz_corrected_A": round(iz_corrected, 1),
                "rule": "NBR 5410 §5.3.4 (In ≤ Iz·FC)",
            },
        },
    }
