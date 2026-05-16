"""
app.preprocessor.lcc_extensions — extensões para Line/Cable
Constants conforme auditoria P1: bundling + skin-effect
(v0.70).

Limitações herdadas (v0.27.x lcc.py auditoria P1):

1. **Sem bundling**: cada conductor era tratado como uma
   fase. Real EHV usa 2/4/6 conductors/fase (bundles)
   mas LCC reduzia tudo a phases independentes — geração
   sequencial errada.

2. **Sem skin effect**: ``R_dc_per_km`` usado em todas as
   frequências. Para >1 kHz (relevante p/ JMARTI), R real
   é ~2× maior — fitting errado.

Esta extensão fornece:

* ``bundle_equivalent_radius_GMR(...)`` — raio equivalente
  geométrico (GMR) para bundle com N conductors em formação
  regular polygonal (raio do bundle r_b, raio individual r,
  N conductors).

* ``ac_resistance_with_skin_effect(...)`` — R_AC corrigido
  por skin effect via aproximação Bessel (Schelkunoff /
  Carson).

* ``effective_radius_after_bundling(...)`` — combina ambos
  para uso direto no cálculo de impedâncias positiva/zero.

Referências
============

* Stevenson, *Elements of Power System Analysis*, 4th ed,
  McGraw-Hill 1982 — §5 (line constants + bundling).
* Carson, J.R., "Wave Propagation in Overhead Wires with
  Ground Return", Bell System Technical Journal, 1926.
* IEC TR 60909-2:2008 §5.2 (skin effect).
* CIGRÉ Working Group 22.04 — Conductor characteristics.
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# Bundling reduction
# ---------------------------------------------------------------------------


def bundle_equivalent_radius_GMR(
    conductor_radius_m: float,
    bundle_radius_m: float,
    n_conductors: int,
) -> float:
    """
    Raio equivalente GMR (Geometric Mean Radius) de um bundle
    de ``n`` conductors em formação polygonal regular de
    raio ``bundle_radius_m``.

    Fórmula (Stevenson §5.10 / Carson):

    ::

        r_eq = (n · r_c · S^(n-1))^(1/n)

    Onde:
    * r_c = raio individual do conductor (corrigido para GMR)
    * S = ``bundle_radius_m`` × ``2 sin(π/n)`` = lado do
      polígono do bundle
    * n = número de conductors no bundle

    Nota: para n=1 (sem bundling), retorna ``conductor_radius_m``.

    Configurações típicas EHV:
    * 2-conductor (n=2): linhas 230 kV BR
    * 3-conductor: linhas 345-400 kV
    * 4-conductor: linhas 500 kV
    * 6-conductor: linhas 765 kV+

    Parameters
    ----------
    conductor_radius_m:
        Raio individual r_c (m). Use GMR físico
        (≈ 0.7788·raio_externo para conductor sólido).
    bundle_radius_m:
        Raio do bundle (distância do centro até cada
        conductor) em metros.
    n_conductors:
        Número de conductors por fase (1, 2, 3, 4, 6).

    Returns
    -------
    float
        r_eq (m) — usar em fórmulas de Z_série e Y_shunt
        no lugar do raio físico.
    """
    if n_conductors < 1:
        raise ValueError(
            f"n_conductors >= 1 (achado {n_conductors})"
        )
    if conductor_radius_m <= 0:
        raise ValueError(
            f"conductor_radius_m > 0 (achado {conductor_radius_m})"
        )

    if n_conductors == 1:
        return conductor_radius_m

    if bundle_radius_m <= 0:
        raise ValueError(
            f"bundle_radius_m > 0 para n>1 "
            f"(achado {bundle_radius_m})"
        )

    # Lado do polígono regular: S = 2 r_b sin(π/n)
    S = 2.0 * bundle_radius_m * math.sin(math.pi / n_conductors)
    # GMR do bundle: (n · r_c · S^(n-1))^(1/n)
    r_eq = (
        n_conductors * conductor_radius_m * (S ** (n_conductors - 1))
    ) ** (1.0 / n_conductors)
    return r_eq


# ---------------------------------------------------------------------------
# Skin effect AC resistance
# ---------------------------------------------------------------------------


def skin_depth_m(
    frequency_Hz: float,
    resistivity_ohm_m: float = 1.724e-8,    # cobre puro 20°C
    permeability_relative: float = 1.0,
) -> float:
    """
    Profundidade de penetração (skin depth) δ:

    ::

        δ = √(ρ / (π · f · μ))

    Onde μ = μ_0 · μ_r.

    Parameters
    ----------
    frequency_Hz:
        Frequência (Hz). Para 60 Hz → δ ≈ 8.5 mm em cobre.
    resistivity_ohm_m:
        Resistividade do material. Cobre 1.724e-8, alumínio
        2.65e-8 (Ω·m).
    permeability_relative:
        μ_r (1.0 para Cu/Al não-magnéticos; 100-1000 para aço).

    Returns
    -------
    float
        δ em metros.
    """
    if frequency_Hz <= 0:
        return float("inf")
    mu_0 = 4.0 * math.pi * 1.0e-7
    mu = mu_0 * permeability_relative
    return math.sqrt(resistivity_ohm_m / (math.pi * frequency_Hz * mu))


def skin_effect_factor(
    conductor_radius_m: float,
    frequency_Hz: float,
    *,
    resistivity_ohm_m: float = 1.724e-8,
    permeability_relative: float = 1.0,
) -> float:
    """
    Fator R_AC / R_DC devido a skin effect.

    Aproximação para conductor cilíndrico maciço (Schelkunoff
    / Carson asymptotic):

    ::

        x = r/δ
        Para x < 1.5 (low freq): R_AC/R_DC ≈ 1 + x⁴/48
        Para x ≥ 1.5 (high freq): R_AC/R_DC ≈ x/2 + 0.25 + 3/(64x)

    Resultado limitado ao mínimo de 1.0 (sem skin → R_AC = R_DC).

    Parameters
    ----------
    conductor_radius_m:
        Raio físico externo (m).
    frequency_Hz:
        Frequência operacional (Hz).
    resistivity_ohm_m:
        Resistividade.
    permeability_relative:
        μ_r.

    Returns
    -------
    float
        R_AC/R_DC ratio (≥ 1.0).
    """
    if conductor_radius_m <= 0 or frequency_Hz <= 0:
        return 1.0

    delta = skin_depth_m(
        frequency_Hz,
        resistivity_ohm_m=resistivity_ohm_m,
        permeability_relative=permeability_relative,
    )
    x = conductor_radius_m / delta
    if x < 1.5:
        # Low-frequency series expansion
        ratio = 1.0 + (x ** 4) / 48.0
    else:
        # High-frequency asymptotic
        ratio = x / 2.0 + 0.25 + 3.0 / (64.0 * x)
    return max(1.0, ratio)


def ac_resistance_with_skin_effect(
    R_dc_ohm_per_km: float,
    conductor_radius_m: float,
    frequency_Hz: float,
    *,
    resistivity_ohm_m: float = 1.724e-8,
    permeability_relative: float = 1.0,
) -> float:
    """
    R_AC (Ω/km) corrigido por skin effect a partir do R_DC.

    Cobertura de aplicação:
    * 60 Hz: ratio ≈ 1.005 (efeito desprezível para cabos
      pequenos; 5-10% para conductors grandes >800 mm²).
    * 1 kHz: ratio ≈ 2-3.
    * 10 kHz: ratio ≈ 8-15.
    * 100 kHz: ratio ≈ 30-50.

    Parameters
    ----------
    R_dc_ohm_per_km:
        Resistência DC tabelada (Ω/km).
    conductor_radius_m:
        Raio externo do conductor (m).
    frequency_Hz:
        Frequência operacional.

    Returns
    -------
    float
        R_AC em Ω/km na frequência dada.
    """
    factor = skin_effect_factor(
        conductor_radius_m, frequency_Hz,
        resistivity_ohm_m=resistivity_ohm_m,
        permeability_relative=permeability_relative,
    )
    return R_dc_ohm_per_km * factor


# ---------------------------------------------------------------------------
# Effective radius após bundling + skin
# ---------------------------------------------------------------------------


def line_constants_with_bundling_and_skin(
    R_dc_per_conductor_ohm_per_km: float,
    conductor_radius_m: float,
    bundle_radius_m: float,
    n_conductors: int,
    frequency_Hz: float,
    *,
    resistivity_ohm_m: float = 1.724e-8,
    permeability_relative: float = 1.0,
) -> dict:
    """
    Combina bundling + skin effect e retorna parâmetros
    equivalentes para uso direto em cálculo de Z e Y de
    linha trifásica.

    Estratégia:

    1. Calcula r_eq via ``bundle_equivalent_radius_GMR``
       (geometria do bundle).
    2. Calcula R_AC por conductor com skin effect.
    3. R_AC do bundle = R_AC por conductor / N (paralelo).

    Returns
    -------
    dict
        ``{
            "r_eq_m": float,      # raio equiv do bundle
            "R_AC_ohm_per_km": float,  # do bundle
            "skin_factor": float,
            "n_conductors": int,
        }``
    """
    r_eq = bundle_equivalent_radius_GMR(
        conductor_radius_m=conductor_radius_m,
        bundle_radius_m=bundle_radius_m,
        n_conductors=n_conductors,
    )
    skin_f = skin_effect_factor(
        conductor_radius_m, frequency_Hz,
        resistivity_ohm_m=resistivity_ohm_m,
        permeability_relative=permeability_relative,
    )
    # Resistência AC do bundle (N conductors em paralelo)
    R_per_cond = R_dc_per_conductor_ohm_per_km * skin_f
    R_AC_bundle = R_per_cond / n_conductors

    return {
        "r_eq_m": r_eq,
        "R_AC_ohm_per_km": R_AC_bundle,
        "skin_factor": skin_f,
        "n_conductors": n_conductors,
        "frequency_Hz": frequency_Hz,
    }
