"""
app.simulation.emt.line — linha/cabo a parâmetros distribuídos constantes
(modelo de Bergeron) para o motor EMT dedicado.

Fundamento
==========

Para uma linha monofásica SEM perdas, as equações do telegrafista

    −∂v/∂x = L'·∂i/∂t          −∂i/∂x = C'·∂v/∂t

admitem a solução de d'Alembert em ondas viajantes. Definindo

    Z_c = sqrt(L'/C')          (impedância de surto, Ω)
    τ   = ℓ · sqrt(L'·C')      (tempo de trânsito, s)

a grandeza ``v + Z_c·i`` é invariante ao longo de uma característica
que percorre a linha em ``τ``. Disso resulta o par de equivalentes de
Norton DESACOPLADOS de Dommel [LITERATURA: H. W. Dommel, "Digital
Computer Solution of Electromagnetic Transients in Single- and
Multiphase Networks", *IEEE Trans. PAS*, vol. PAS-88, n. 4, pp.
388-399, 1969, §III]::

    i_km(t) = v_k(t)/Z_c + I_k(t−τ)
    I_k(t−τ) = −v_m(t−τ)/Z_c − i_mk(t−τ)

    i_mk(t) = v_m(t)/Z_c + I_m(t−τ)
    I_m(t−τ) = −v_k(t−τ)/Z_c − i_km(t−τ)

O acoplamento entre os dois terminais é APENAS pelo histórico: na
matriz nodal cada extremidade contribui somente com ``1/Z_c`` na
própria diagonal. É essa propriedade que torna a linha o elemento que
"parte" a matriz do sistema em blocos.

Perdas concentradas (R/4, R/2, R/4)
====================================

O modelo com perdas segue a aproximação clássica do EMTP: a
resistência série total ``R`` é concentrada em três pontos — ``R/4``
em cada extremidade e ``R/2`` no meio — e a linha é tratada como duas
meias-linhas sem perdas. O resultado, com

    Z = Z_c + R/4                  ζ = (Z_c − R/4)/(Z_c + R/4)

é

    i_km(t) = v_k(t)/Z + I_k(t−τ)

    I_k(t−τ) = −(1+ζ)/2 · [ v_m(t−τ)/Z + ζ·i_mk(t−τ) ]
               −(1−ζ)/2 · [ v_k(t−τ)/Z + ζ·i_km(t−τ) ]

Para ``R = 0`` tem-se ``ζ = 1`` e a expressão recai exatamente no caso
sem perdas. [CÁLCULO PRÓPRIO] Em regime permanente contínuo
(``i_km = −i_mk = I`` constante) a expressão acima fornece
``I = (v_k − v_m)/R`` EXATAMENTE, o que se verifica substituindo
``1 − ζ = (R/2)/Z``; portanto o modelo é exato em corrente contínua e
a resistência total vista pelo circuito é ``R``, sem erro de
truncamento. Esse é o teste de aceitação implementado em
``tests/test_emt_kernel.py``.

Interpolação de histórico
==========================

Quando ``τ`` não é múltiplo inteiro de ``Δt`` — e também durante os
meios-passos do amortecimento crítico (CDA), em que a base de tempo
deixa de ser uniforme — o valor em ``t − τ`` é obtido por
**interpolação linear** entre as duas amostras que o cercam. É a mesma
opção do EMTP; ela introduz um pequeno amortecimento numérico da
frente de onda, discutido em [LITERATURA: J. A. Martinez-Velasco
(ed.), *Transient Analysis of Power Systems*, Wiley/IEEE Press, 2015,
cap. 2] e em [LITERATURA: A. Greenwood, *Electrical Transients in
Power Systems*, 2. ed., Wiley, 1991, cap. 5].

Limitação declarada — dependência de frequência
================================================

Este modelo é de **parâmetros constantes** (CP / Bergeron). Não há
modelo de dependência de frequência tipo JMarti [LITERATURA: J. R.
Marti, "Accurate Modelling of Frequency-Dependent Transmission Lines
in Electromagnetic Transient Simulations", *IEEE Trans. PAS*, vol.
PAS-101, n. 1, pp. 147-157, 1982] nem transformação modal para
múltiplos condutores. Impacto sobre a frente de onda, relevante para o
estudo de TRV de disjuntor a vácuo:

* o efeito pelicular e o retorno pela terra atenuam e DEFORMAM a
  frente real; com parâmetros constantes o degrau chega à outra
  extremidade praticamente sem atenuação e com tempo de subida
  determinado apenas por ``Δt`` e pela interpolação — logo a
  ``dv/dt`` e o ``V_pk`` calculados são CONSERVADORES (superiores aos
  reais) para cabos longos;
* a impedância de surto real varia com a frequência (tipicamente
  decrescente na faixa de MHz); um ``Z_c`` único, ajustado em 60 Hz,
  subestima a corrente injetada nas reignições de frente muito rápida;
* modos de propagação (aéreo e de terra) têm velocidades distintas;
  com um único modo, a dispersão entre fases não é reproduzida.

Consequência prática: os valores de ``V_pk`` e ``dv/dt`` extraídos por
``app.postprocessor.prognosis.stress_profile.extract_stress_events``
sobre formas de onda deste modelo devem ser lidos como **cota
superior** de estresse dielétrico, não como estimativa central.
"""

from __future__ import annotations

import math

import numpy as np

from app.core.logging_config import get_logger

from app.simulation.emt.components import (
    GROUND_INDEX,
    Component,
    _require_non_negative,
    _require_positive,
    node_voltage,
)

log = get_logger(__name__)


class _TravelHistory:
    """Buffer circular de histórico de onda viajante com interpolação linear.

    Armazena a sequência ``(t, v_k, i_km, v_m, i_mk)`` de todos os
    passos já resolvidos e devolve o valor em ``t − τ`` por interpolação
    linear entre as duas amostras vizinhas. O cursor avança
    monotonicamente (o argumento de consulta é monotônico crescente),
    de modo que o custo amortizado por consulta é O(1); as amostras
    anteriores ao cursor são descartadas periodicamente para que a
    memória permaneça O(τ/Δt).
    """

    _PRUNE_THRESHOLD: int = 4096

    def __init__(self) -> None:
        self._t: list[float] = [0.0]
        self._data: list[tuple[float, float, float, float]] = [(0.0, 0.0, 0.0, 0.0)]
        self._cursor: int = 0

    def reset(self) -> None:
        """Zera o buffer, mantendo a amostra inicial nula em ``t = 0``."""
        self._t = [0.0]
        self._data = [(0.0, 0.0, 0.0, 0.0)]
        self._cursor = 0

    def append(
        self, t: float, v_k: float, i_km: float, v_m: float, i_mk: float
    ) -> None:
        """Registra o estado dos terminais no instante ``t``."""
        self._t.append(float(t))
        self._data.append((float(v_k), float(i_km), float(v_m), float(i_mk)))
        if len(self._t) > self._PRUNE_THRESHOLD and self._cursor > 1:
            keep = self._cursor - 1
            self._t = self._t[keep:]
            self._data = self._data[keep:]
            self._cursor -= keep

    def value_at(self, t_query: float) -> tuple[float, float, float, float]:
        """Estado dos terminais em ``t_query`` por interpolação linear."""
        if t_query <= self._t[0]:
            return (0.0, 0.0, 0.0, 0.0)
        last = len(self._t) - 1
        if t_query >= self._t[last]:
            # Extrapolação: só ocorre se τ < Δt (linha mais curta que o
            # passo). Retenção de ordem zero, com aviso emitido pelo
            # chamador na validação de τ.
            return self._data[last]
        c = self._cursor
        if c > last - 1:
            c = last - 1
        while c + 1 <= last and self._t[c + 1] < t_query:
            c += 1
        while c > 0 and self._t[c] > t_query:
            c -= 1
        self._cursor = c
        t0, t1 = self._t[c], self._t[c + 1]
        d0, d1 = self._data[c], self._data[c + 1]
        span = t1 - t0
        if span <= 0.0:  # pragma: no cover - defensivo
            return d0
        w = (t_query - t0) / span
        return (
            d0[0] + w * (d1[0] - d0[0]),
            d0[1] + w * (d1[1] - d0[1]),
            d0[2] + w * (d1[2] - d0[2]),
            d0[3] + w * (d1[3] - d0[3]),
        )

    def __len__(self) -> int:  # pragma: no cover - conveniência
        return len(self._t)


class BergeronLine(Component):
    """Linha/cabo a parâmetros distribuídos constantes (Bergeron).

    Parameters
    ----------
    name:
        Identificador do ramo.
    node_k, node_m:
        Nós das extremidades emissora e receptora.
    surge_impedance_ohm:
        ``Z_c = sqrt(L'/C')`` [Ω], > 0.
    travel_time_s:
        ``τ = ℓ·sqrt(L'C')`` [s], > 0.
    resistance_ohm:
        Resistência série TOTAL da linha [Ω], >= 0, concentrada em
        ``R/4``, ``R/2``, ``R/4``. ``0.0`` (padrão) ⇒ linha sem perdas.

    Raises
    ------
    ValueError
        ``Z_c <= 0``, ``τ <= 0``, ``R < 0``, ``R/4 >= Z_c`` (perdas
        excessivas para a aproximação concentrada) ou nós coincidentes.
    """

    def __init__(
        self,
        name: str,
        node_k: str,
        node_m: str,
        *,
        surge_impedance_ohm: float,
        travel_time_s: float,
        resistance_ohm: float = 0.0,
    ) -> None:
        super().__init__(name, (node_k, node_m))
        if self.nodes[0] == self.nodes[1]:
            raise ValueError(f"linha {name!r} com os dois terminais no mesmo nó")
        self.surge_impedance_ohm: float = _require_positive(
            surge_impedance_ohm, "surge_impedance_ohm"
        )
        self.travel_time_s: float = _require_positive(travel_time_s, "travel_time_s")
        self.resistance_ohm: float = _require_non_negative(resistance_ohm, "resistance_ohm")
        r_quarter = self.resistance_ohm / 4.0
        if r_quarter >= self.surge_impedance_ohm:
            raise ValueError(
                f"linha {name!r}: R/4 = {r_quarter:.6g} Ω >= Z_c = "
                f"{self.surge_impedance_ohm:.6g} Ω — a aproximação de perdas "
                f"concentradas exige R/4 < Z_c"
            )
        #: Z = Z_c + R/4 — impedância vista pela estampagem nodal.
        self._z: float = self.surge_impedance_ohm + r_quarter
        #: ζ = (Z_c − R/4)/(Z_c + R/4) — fator de atenuação da meia-linha.
        self._zeta: float = (self.surge_impedance_ohm - r_quarter) / self._z
        self._g: float = 1.0 / self._z
        self._history = _TravelHistory()
        self._v_k: float = 0.0
        self._v_m: float = 0.0
        self._i_km: float = 0.0
        self._i_mk: float = 0.0
        self._i_hist_k: float = 0.0
        self._i_hist_m: float = 0.0
        self._warned_short: bool = False

    # -- construção alternativa --------------------------------------------

    @classmethod
    def from_distributed_parameters(
        cls,
        name: str,
        node_k: str,
        node_m: str,
        *,
        length_m: float,
        inductance_H_per_m: float,
        capacitance_F_per_m: float,
        resistance_ohm_per_m: float = 0.0,
    ) -> "BergeronLine":
        """Constrói a linha a partir de ``ℓ``, ``L'``, ``C'`` e ``R'``.

        ``Z_c = sqrt(L'/C')``; ``τ = ℓ·sqrt(L'·C')``; ``R = R'·ℓ``.
        A velocidade de propagação implícita é ``u = 1/sqrt(L'C')``.
        """
        ell = _require_positive(length_m, "length_m")
        lp = _require_positive(inductance_H_per_m, "inductance_H_per_m")
        cp = _require_positive(capacitance_F_per_m, "capacitance_F_per_m")
        rp = _require_non_negative(resistance_ohm_per_m, "resistance_ohm_per_m")
        return cls(
            name,
            node_k,
            node_m,
            surge_impedance_ohm=math.sqrt(lp / cp),
            travel_time_s=ell * math.sqrt(lp * cp),
            resistance_ohm=rp * ell,
        )

    # -- propriedades -------------------------------------------------------

    @property
    def conductance_S(self) -> float:
        """``1/Z`` com ``Z = Z_c + R/4`` [S]."""
        return self._g

    @property
    def attenuation_factor(self) -> float:
        """``ζ = (Z_c − R/4)/(Z_c + R/4)``; vale 1,0 na linha sem perdas."""
        return self._zeta

    def n_branches(self) -> int:
        return 2

    # -- ciclo de vida ------------------------------------------------------

    def prepare(self, dt: float) -> None:
        super().prepare(dt)
        if self.travel_time_s < self._dt and not self._warned_short:
            self._warned_short = True
            log.warning(
                "linha %r: tempo de trânsito τ=%.6g s menor que o passo Δt=%.6g s; "
                "o histórico será retido por ordem zero (fallback) e a linha "
                "comporta-se como um ramo concentrado — reduza Δt ou use "
                "elementos concentrados",
                self.name,
                self.travel_time_s,
                self._dt,
            )

    def reset(self) -> None:
        self._history.reset()
        self._v_k = 0.0
        self._v_m = 0.0
        self._i_km = 0.0
        self._i_mk = 0.0
        self._i_hist_k = 0.0
        self._i_hist_m = 0.0

    # -- estampagem ---------------------------------------------------------

    def _history_sources(self, t: float) -> tuple[float, float]:
        """Calcula ``(I_k, I_m)`` em ``t`` a partir do estado em ``t − τ``."""
        v_k_d, i_km_d, v_m_d, i_mk_d = self._history.value_at(t - self.travel_time_s)
        z = self._zeta
        a = 0.5 * (1.0 + z)
        b = 0.5 * (1.0 - z)
        i_k = -a * (v_m_d * self._g + z * i_mk_d) - b * (v_k_d * self._g + z * i_km_d)
        i_m = -a * (v_k_d * self._g + z * i_km_d) - b * (v_m_d * self._g + z * i_mk_d)
        return i_k, i_m

    def stamp_matrix(self, A: np.ndarray) -> None:
        k, m = self._idx[0], self._idx[1]
        if k != GROUND_INDEX:
            A[k, k] += self._g
        if m != GROUND_INDEX:
            A[m, m] += self._g

    def stamp_rhs(self, b: np.ndarray, t: float, mode: str) -> None:
        i_k, i_m = self._history_sources(t)
        self._i_hist_k = i_k
        self._i_hist_m = i_m
        k, m = self._idx[0], self._idx[1]
        if k != GROUND_INDEX:
            b[k] -= i_k
        if m != GROUND_INDEX:
            b[m] -= i_m

    def commit(self, x: np.ndarray, t: float, mode: str) -> None:
        v_k = node_voltage(x, self._idx[0])
        v_m = node_voltage(x, self._idx[1])
        self._v_k = v_k
        self._v_m = v_m
        self._i_km = self._g * v_k + self._i_hist_k
        self._i_mk = self._g * v_m + self._i_hist_m
        self._history.append(t, v_k, self._i_km, v_m, self._i_mk)

    # -- leitura ------------------------------------------------------------

    def branch_voltage(self, index: int = 0) -> float:
        """``index = 0`` ⇒ tensão do terminal k; ``1`` ⇒ terminal m [V]."""
        if index == 0:
            return self._v_k
        if index == 1:
            return self._v_m
        raise ValueError(f"terminal inválido para linha: {index!r}")

    def branch_current(self, index: int = 0) -> float:
        """``index = 0`` ⇒ ``i_km``; ``1`` ⇒ ``i_mk`` (ambas ENTRANDO na linha) [A]."""
        if index == 0:
            return self._i_km
        if index == 1:
            return self._i_mk
        raise ValueError(f"terminal inválido para linha: {index!r}")


def surge_impedance(inductance_H_per_m: float, capacitance_F_per_m: float) -> float:
    """``Z_c = sqrt(L'/C')`` [Ω]. Valida ``L' > 0`` e ``C' > 0``."""
    lp = _require_positive(inductance_H_per_m, "inductance_H_per_m")
    cp = _require_positive(capacitance_F_per_m, "capacitance_F_per_m")
    return math.sqrt(lp / cp)


def travel_time(
    length_m: float, inductance_H_per_m: float, capacitance_F_per_m: float
) -> float:
    """``τ = ℓ·sqrt(L'·C')`` [s]. Valida os três argumentos como > 0."""
    ell = _require_positive(length_m, "length_m")
    lp = _require_positive(inductance_H_per_m, "inductance_H_per_m")
    cp = _require_positive(capacitance_F_per_m, "capacitance_F_per_m")
    return ell * math.sqrt(lp * cp)


__all__ = [
    "BergeronLine",
    "surge_impedance",
    "travel_time",
]
