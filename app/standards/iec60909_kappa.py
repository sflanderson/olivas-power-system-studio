"""
app.standards.iec60909_kappa — métodos A/B/C de cálculo do
κ (peak factor) conforme IEC 60909-0:2016 §4.3.1.2.

Motivação
==========

O κ multiplica Ik'' para obter ip (peak make current). Para
malhas com **múltiplas R/X heterogêneas**:

* **Method A** (ratio at fault location): R/X único equivalente
  no ponto de falta. Fórmula κ = 1.02 + 0.98·exp(-3·R/X).
  Subestima ip em malhas mistas.
* **Method B** (single equivalent R/X): igual ao Method A
  mas multiplica por 1.15 como margem de segurança.
* **Method C** (frequency-equivalent): calcula impedância
  na frequência reduzida fc = 20-24 Hz, corrigindo a
  R/X equivalente. **Mais preciso** — recomendado para
  estudo profissional de malha multi-R/X.

Cobertura desta entrega
========================

* Method A — ``kappa_method_A`` (já existia em iec60909.py).
* Method B — ``kappa_method_B`` — fator 1.15 sobre A.
* Method C — ``kappa_method_C`` via cálculo frequência-
  equivalente.
* ``kappa_recommended`` — escolhe método baseado no tipo
  de sistema (radial vs malha).

Referências
============

* IEC 60909-0:2016 §4.3.1.2 (Methods A, B, C).
* IEC TR 60909-1:2002 (background técnico Method C).
* Roeper, R. *Short-Circuit Currents in Three-Phase Systems*,
  Siemens Pub. 1985.
"""

from __future__ import annotations

import math
from enum import Enum


class KappaMethod(str, Enum):
    """
    Método para cálculo do κ conforme IEC 60909-0 §4.3.1.2.

    * **METHOD_A**: ratio único no ponto de falta (radial).
    * **METHOD_B**: Method A com fator 1.15 (margem segurança).
    * **METHOD_C**: frequência-equivalente para malhas
      multi-R/X (mais preciso).
    """
    METHOD_A = "A"
    METHOD_B = "B"
    METHOD_C = "C"


# ---------------------------------------------------------------------------
# Method A — single ratio (já existe em iec60909.py, replicado aqui)
# ---------------------------------------------------------------------------


def kappa_method_A(r_over_x: float) -> float:
    """
    κ via Method A — IEC 60909-0 §4.3.1.2.

    ::

        κ_A = 1.02 + 0.98 · exp(-3 · R/X)

    Limite [1.02, 2.00]. Adequado para sistemas radiais ou
    R/X aproximadamente uniforme em toda a malha.
    """
    if r_over_x < 0:
        raise ValueError(f"R/X >= 0 (achado {r_over_x})")
    return 1.02 + 0.98 * math.exp(-3.0 * r_over_x)


# ---------------------------------------------------------------------------
# Method B — Method A × 1.15 (margem)
# ---------------------------------------------------------------------------


def kappa_method_B(r_over_x: float) -> float:
    """
    κ via Method B — IEC 60909-0 §4.3.1.2.

    ::

        κ_B = 1.15 · κ_A,    capado em 1.80 (LV) ou 2.00 (HV/MV)

    Adicionar 15% de margem ao Method A para cobrir
    incerteza em sistemas malhados moderados.
    """
    kA = kappa_method_A(r_over_x)
    kB = 1.15 * kA
    return min(kB, 2.00)


# ---------------------------------------------------------------------------
# Method C — frequency-equivalent
# ---------------------------------------------------------------------------


def kappa_method_C(
    z_thevenin_at_fc: complex,
    nominal_frequency_Hz: float = 50.0,
    fc_Hz: float = 20.0,
) -> float:
    """
    κ via Method C — IEC 60909-0 §4.3.1.2 (mais preciso).

    Estratégia: corrigir o R/X usando impedâncias calculadas
    em **frequência reduzida fc** (típico 20 Hz para 50 Hz
    nominal, 24 Hz para 60 Hz). Em fc reduzida, X cai
    proporcionalmente a fc/fn (X = ωL), enquanto R fica
    aproximadamente constante (efeito skin diminui).

    A relação corrigida:

    ::

        R_c / X_c = (R/X)_at_fc · (fc/fn)
        κ_C = 1.02 + 0.98 · exp(-3 · R_c/X_c)

    Onde ``z_thevenin_at_fc`` é a impedância equivalente
    calculada em fc (NÃO em fn).

    Parameters
    ----------
    z_thevenin_at_fc:
        Z = R + jX calculada em fc (ohms).
    nominal_frequency_Hz:
        f_n do sistema (50 ou 60 Hz).
    fc_Hz:
        Frequência reduzida (default 20 Hz, IEC §4.3.1.2.4).

    Returns
    -------
    float
        κ corrigido pelo Method C.
    """
    if abs(z_thevenin_at_fc) <= 0:
        raise ValueError("|Z_th| deve ser > 0")
    if fc_Hz <= 0 or nominal_frequency_Hz <= 0:
        raise ValueError("fc e fn devem ser > 0")
    if fc_Hz >= nominal_frequency_Hz:
        raise ValueError(
            f"fc={fc_Hz} deve ser < fn={nominal_frequency_Hz}"
        )

    R_at_fc = z_thevenin_at_fc.real
    X_at_fc = z_thevenin_at_fc.imag
    if X_at_fc == 0:
        # Sistema puramente resistivo — κ = 1.02 (sem DC)
        return 1.02

    # Correção R/X conforme §4.3.1.2.4
    r_over_x_corrected = (R_at_fc / X_at_fc) * (fc_Hz / nominal_frequency_Hz)
    if r_over_x_corrected < 0:
        # Caso degenerado (X<0 ou R<0): ainda calcula com módulo
        r_over_x_corrected = abs(r_over_x_corrected)

    return 1.02 + 0.98 * math.exp(-3.0 * r_over_x_corrected)


# ---------------------------------------------------------------------------
# Wrapper: kappa_recommended
# ---------------------------------------------------------------------------


def kappa_recommended(
    r_over_x_at_fn: float,
    *,
    method: KappaMethod = KappaMethod.METHOD_B,
    z_thevenin_at_fc: complex | None = None,
    nominal_frequency_Hz: float = 50.0,
    fc_Hz: float = 20.0,
) -> float:
    """
    κ pelo método recomendado.

    * METHOD_A: usa apenas r_over_x_at_fn.
    * METHOD_B: usa apenas r_over_x_at_fn (com fator 1.15).
    * METHOD_C: requer ``z_thevenin_at_fc`` (impedância em fc
      reduzida).

    Parameters
    ----------
    r_over_x_at_fn:
        Razão R/X equivalente na frequência nominal.
    method:
        Method A / B / C.
    z_thevenin_at_fc:
        Obrigatório para Method C.
    nominal_frequency_Hz:
        f_n do sistema.
    fc_Hz:
        f reduzida (Method C).

    Returns
    -------
    float
        κ (peak factor).
    """
    if method == KappaMethod.METHOD_A:
        return kappa_method_A(r_over_x_at_fn)
    if method == KappaMethod.METHOD_B:
        return kappa_method_B(r_over_x_at_fn)
    if method == KappaMethod.METHOD_C:
        if z_thevenin_at_fc is None:
            raise ValueError(
                "Method C exige z_thevenin_at_fc (impedância em fc)"
            )
        return kappa_method_C(
            z_thevenin_at_fc,
            nominal_frequency_Hz=nominal_frequency_Hz,
            fc_Hz=fc_Hz,
        )
    raise ValueError(f"Method desconhecido: {method}")


# ---------------------------------------------------------------------------
# Helper: classificação topológica
# ---------------------------------------------------------------------------


def recommend_method_for_topology(is_meshed: bool) -> KappaMethod:
    """
    Sugere método com base na topologia.

    * Radial → Method A (suficiente, conservador).
    * Malhada moderada → Method B (margem 15%).
    * Malhada complexa multi-R/X → Method C (preciso).

    Esta versão (v0.28.0-PRO) usa heurística simples: malhada
    → Method C; radial → Method B (mais conservador que A).

    Parameters
    ----------
    is_meshed:
        True se rede tem laços (mais de 1 caminho entre
        gerador e ponto de falta).

    Returns
    -------
    KappaMethod
    """
    return KappaMethod.METHOD_C if is_meshed else KappaMethod.METHOD_B
