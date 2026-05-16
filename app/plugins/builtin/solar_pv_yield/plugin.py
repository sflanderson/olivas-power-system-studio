"""
Builtin plugin: Solar PV Yield Calculator
==========================================

Calcula yield anual estimado de sistema fotovoltaico usando o método
NREL Sandia simplificado para o contexto brasileiro.

Inputs:
* irradiance_kwh_m2_year — irradiação anual local (1500-2200 típico)
* panel_kWp — potência DC instalada (kWp)
* performance_ratio — PR (default 0.78, típico Brasil)
* tilt_loss_factor — perda por inclinação não ótima (default 0.97)

Output:
* yield_kwh_year — energia anual gerada
* capacity_factor — fator de capacidade (yield / (kWp × 8760))
* specific_yield_kwh_per_kwp — kWh/kWp/ano (1300-1700 típico)
"""

from app.plugins import register_study


@register_study("solar_pv_yield_brazil")
def calculate_pv_yield(
    project=None,
    *,
    irradiance_kwh_m2_year: float = 1800.0,
    panel_kWp: float = 1.0,
    performance_ratio: float = 0.78,
    tilt_loss_factor: float = 0.97,
):
    """
    Estima yield anual de sistema fotovoltaico (Brasil).

    Yield = G × kWp × PR × tilt_factor

    Onde:
    * G: irradiação solar (kWh/m²/ano) — área do painel é absorvida
      no PR (Performance Ratio).
    * PR ≈ 0.78 captura: temperatura ambiente, soiling, mismatch,
      cabos DC, inversor (95-97%), transformador.
    """
    yield_kwh_year = (
        irradiance_kwh_m2_year * panel_kWp
        * performance_ratio * tilt_loss_factor
    )
    capacity_factor = yield_kwh_year / (panel_kWp * 8760.0)
    specific_yield = yield_kwh_year / panel_kWp
    return {
        "yield_kwh_year": round(yield_kwh_year, 1),
        "capacity_factor": round(capacity_factor, 4),
        "specific_yield_kwh_per_kwp": round(specific_yield, 1),
        "method": "NREL Sandia simplificado (Brasil)",
    }
