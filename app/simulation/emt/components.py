"""
app.simulation.emt.components — modelos companheiros (*companion models*)
de Dommel para o motor EMT dedicado do Olivas Power System Studio.

Fundamento
==========

O método nodal de Dommel [LITERATURA: H. W. Dommel, "Digital Computer
Solution of Electromagnetic Transients in Single- and Multiphase
Networks", *IEEE Transactions on Power Apparatus and Systems*, vol.
PAS-88, n. 4, pp. 388-399, abr. 1969, doi:10.1109/TPAS.1969.292459]
discretiza cada ramo com armazenamento de energia pela **regra
trapezoidal** e o substitui por um *equivalente companheiro*: uma
condutância constante ``G`` em paralelo com uma fonte de corrente
``I_hist`` calculada apenas com grandezas do passo anterior.

Convenção de sinal adotada em TODO o pacote::

    i(t) = G · v(t) + I_hist(t)

com ``v = v_p − v_n`` (tensão do nó positivo menos a do negativo) e
``i`` positiva saindo do nó ``p`` e entrando no nó ``n``.

Álgebra dos modelos companheiros
=================================

**Resistor** — ``v = R·i`` é algébrico::

    G = 1/R,        I_hist = 0

**Indutor** — ``v = L·di/dt``. Integrando de ``t−Δt`` a ``t`` pela
regra trapezoidal::

    i(t) − i(t−Δt) = (1/L) ∫ v dt ≈ (Δt / 2L) · [ v(t) + v(t−Δt) ]

    ⇒ i(t) = (Δt/2L)·v(t) + [ i(t−Δt) + (Δt/2L)·v(t−Δt) ]

    G_L = Δt/(2L)
    I_hist(t) = i(t−Δt) + (Δt/2L)·v(t−Δt)

**Capacitor** — ``i = C·dv/dt``. Trapézio::

    v(t) − v(t−Δt) = (1/C) ∫ i dt ≈ (Δt / 2C) · [ i(t) + i(t−Δt) ]

    ⇒ i(t) = (2C/Δt)·v(t) + [ −i(t−Δt) − (2C/Δt)·v(t−Δt) ]

    G_C = 2C/Δt
    I_hist(t) = −i(t−Δt) − (2C/Δt)·v(t−Δt)

**Ramo RL acoplado (n enrolamentos)** — ``v = R·i + L·di/dt`` com
``R`` e ``L`` matrizes ``n×n``. Trapézio::

    v(t) + v(t−Δt) = R·[i(t)+i(t−Δt)] + (2L/Δt)·[i(t) − i(t−Δt)]

    ⇒ (R + 2L/Δt)·i(t) = v(t) + v(t−Δt) + (2L/Δt − R)·i(t−Δt)

    G = (R + 2L/Δt)⁻¹
    I_hist(t) = G · [ v(t−Δt) + (2L/Δt − R)·i(t−Δt) ]

Amortecimento crítico (CDA) — o motivo da invariância da matriz
================================================================

A regra trapezoidal aplicada a uma descontinuidade (interrupção
abrupta da corrente de um indutor — exatamente o *chopping* do
disjuntor a vácuo) tem polo discreto ``z → −1`` e produz oscilação
numérica NÃO amortecida de período ``2Δt``, que não é fenômeno físico
[LITERATURA: J. R. Marti e J. Lin, "Suppression of numerical
oscillations in the EMTP", *IEEE Transactions on Power Systems*, vol.
4, n. 2, pp. 739-747, maio 1989, doi:10.1109/59.193849].

A correção do ATP (*critical damping adjustment*) substitui UM passo
trapezoidal de ``Δt`` por DOIS meios-passos de Euler regressivo de
``h = Δt/2``. Euler regressivo com passo ``h``::

    Indutor:   i(t) = i(t−h) + (h/L)·v(t)
               ⇒ G = h/L,          I_hist = i(t−h)

    Capacitor: i(t) = (C/h)·[v(t) − v(t−h)]
               ⇒ G = C/h,          I_hist = −(C/h)·v(t−h)

    RL acopl.: (R + L/h)·i(t) = v(t) + (L/h)·i(t−h)
               ⇒ G = (R + L/h)⁻¹,  I_hist = G·(L/h)·i(t−h)

Com ``h = Δt/2`` resulta ``h/L = Δt/(2L) = G_L`` e ``C/h = 2C/Δt =
G_C`` e ``(R + L/h) = (R + 2L/Δt)``: **as condutâncias companheiras
são IDÊNTICAS às trapezoidais**. Só o termo de histórico muda. Essa é
a razão pela qual o CDA não exige refatoração da matriz — propriedade
explorada pelo cache de fatoração em :mod:`app.simulation.emt.circuit`.

Formulação nodal aumentada (MNA)
=================================

Fontes de tensão ideais e chaves ideais não têm equivalente Norton.
Adota-se a **análise nodal modificada** (MNA): cada uma acrescenta uma
incógnita de corrente de ramo e uma equação de restrição. A alternativa
(eliminação de nós de tensão conhecida) foi descartada porque a chave
ideal não tem tensão conhecida quando aberta e porque a eliminação
renumera o sistema a cada manobra — inviável para o cache de
fatoração. Detalhe adicional decisivo: mantendo a incógnita de corrente
da chave também no estado ABERTO (com a equação ``i = 0``), a DIMENSÃO
do sistema é invariante à topologia e só os coeficientes mudam.

Fontes secundárias consultadas
===============================

* [LITERATURA: J. A. Martinez-Velasco (ed.), *Transient Analysis of
  Power Systems: Solution Techniques, Tools and Applications*, Wiley/
  IEEE Press, 2015, cap. 2] — formulação nodal, modelos companheiros e
  tratamento de chaves.
* [LITERATURA: L. van der Sluis, *Transients in Power Systems*, Wiley,
  2001, cap. 4-6] — TRV, corrente de *chopping* e reacendimento em
  disjuntores a vácuo.
* [LITERATURA: A. Greenwood, *Electrical Transients in Power Systems*,
  2. ed., Wiley, 1991, cap. 5 e 10] — ondas viajantes e interrupção de
  correntes indutivas.

Este módulo é puro: sem I/O, sem GUI, sem estado global, determinístico.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from app.core.logging_config import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constantes de modo de integração
# ---------------------------------------------------------------------------

#: Regra trapezoidal com passo Δt (modo normal de marcha).
MODE_TRAPEZOIDAL: str = "trapezoidal"

#: Euler regressivo com meio-passo h = Δt/2 (modo CDA, dois passos
#: consecutivos após cada evento de chaveamento).
MODE_BACKWARD_EULER_HALF: str = "backward_euler_half"

#: Modos válidos aceitos por :meth:`Component.stamp_rhs`.
INTEGRATION_MODES: tuple[str, ...] = (
    MODE_TRAPEZOIDAL,
    MODE_BACKWARD_EULER_HALF,
)

#: Nomes reservados que identificam o nó de referência (terra).
GROUND_NAMES: frozenset[str] = frozenset({"gnd", "GND", "0", "ground", "terra"})

#: Índice sentinela do nó de terra (não aparece na matriz).
GROUND_INDEX: int = -1


# ---------------------------------------------------------------------------
# Validação auxiliar
# ---------------------------------------------------------------------------


def _require_positive(value: float, label: str) -> float:
    """Valida um parâmetro físico estritamente positivo e finito."""
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensivo
        raise ValueError(f"{label} deve ser numérico, obtido {value!r}") from exc
    if not math.isfinite(v) or v <= 0.0:
        raise ValueError(f"{label} deve ser finito e > 0, obtido {v!r}")
    return v


def _require_finite(value: float, label: str) -> float:
    """Valida um parâmetro numérico finito (pode ser negativo ou nulo)."""
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensivo
        raise ValueError(f"{label} deve ser numérico, obtido {value!r}") from exc
    if not math.isfinite(v):
        raise ValueError(f"{label} deve ser finito, obtido {v!r}")
    return v


def _require_non_negative(value: float, label: str) -> float:
    """Valida um parâmetro físico não negativo e finito."""
    v = _require_finite(value, label)
    if v < 0.0:
        raise ValueError(f"{label} deve ser >= 0, obtido {v!r}")
    return v


def is_ground(node: str) -> bool:
    """Indica se ``node`` nomeia o nó de referência."""
    return str(node) in GROUND_NAMES


def node_voltage(x: np.ndarray, index: int) -> float:
    """Tensão nodal a partir do vetor solução, tratando terra como 0 V."""
    if index == GROUND_INDEX:
        return 0.0
    return float(x[index])


# ---------------------------------------------------------------------------
# Classe base
# ---------------------------------------------------------------------------


class Component:
    """Ramo genérico do circuito EMT.

    Contrato de ciclo de vida, na ordem em que o solver chama:

    1. :meth:`bind` — resolve nomes de nó em índices e reserva as
       incógnitas extras de MNA (uma vez, em ``Circuit.build()``).
    2. :meth:`prepare` — pré-computa a condutância companheira para o
       passo ``Δt`` (uma vez por valor de ``Δt``).
    3. :meth:`reset` — zera (ou impõe) o estado inicial.
    4. Por passo: :meth:`stamp_matrix` (só quando a topologia muda),
       :meth:`stamp_rhs`, solução do sistema, :meth:`commit`.

    Convenção de sinal: ``i = G·v + I_hist``, ``v = v_p − v_n``, ``i``
    saindo do nó ``p``.
    """

    def __init__(self, name: str, nodes: Sequence[str]) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("o nome do componente deve ser uma string não vazia")
        node_tuple = tuple(str(n) for n in nodes)
        if len(node_tuple) < 2:
            raise ValueError(
                f"componente {name!r} precisa de ao menos 2 nós, obtidos {node_tuple!r}"
            )
        self.name: str = name
        self.nodes: tuple[str, ...] = node_tuple
        self._idx: tuple[int, ...] = ()
        self._extra: tuple[int, ...] = ()
        self._dt: float = 0.0

    # -- ciclo de vida ------------------------------------------------------

    def n_extra(self) -> int:
        """Número de incógnitas de corrente MNA exigidas pelo ramo."""
        return 0

    def bind(self, node_index: dict[str, int], extra_offset: int) -> int:
        """Resolve índices de nó e reserva as incógnitas extras.

        Returns
        -------
        int
            Quantidade de incógnitas extras consumidas.
        """
        resolved: list[int] = []
        for n in self.nodes:
            if is_ground(n):
                resolved.append(GROUND_INDEX)
                continue
            if n not in node_index:
                raise ValueError(
                    f"componente {self.name!r} referencia nó desconhecido {n!r}"
                )
            resolved.append(node_index[n])
        self._idx = tuple(resolved)
        n_extra = self.n_extra()
        self._extra = tuple(range(extra_offset, extra_offset + n_extra))
        return n_extra

    def prepare(self, dt: float) -> None:
        """Pré-computa a condutância companheira para o passo ``dt``."""
        self._dt = _require_positive(dt, "dt")

    def reset(self) -> None:
        """Reinicia o estado interno (histórico) do ramo."""

    def topology_signature(self) -> object:
        """Parte da assinatura de topologia; ``None`` = ramo invariante."""
        return None

    # -- estampagem ---------------------------------------------------------

    def stamp_matrix(self, A: np.ndarray) -> None:
        """Acumula as contribuições constantes do ramo em ``A``."""

    def stamp_rhs(self, b: np.ndarray, t: float, mode: str) -> None:
        """Acumula o termo de histórico / excitação em ``b`` no instante ``t``."""

    def commit(self, x: np.ndarray, t: float, mode: str) -> None:
        """Atualiza o estado interno a partir da solução ``x`` do passo."""

    # -- leitura ------------------------------------------------------------

    def n_branches(self) -> int:
        """Número de ramos elétricos distintos representados."""
        return 1

    def branch_voltage(self, index: int = 0) -> float:
        """Tensão do ramo ``index`` no último passo resolvido [V]."""
        raise NotImplementedError

    def branch_current(self, index: int = 0) -> float:
        """Corrente do ramo ``index`` no último passo resolvido [A]."""
        raise NotImplementedError

    # -- utilitários de estampagem -----------------------------------------

    @staticmethod
    def _stamp_conductance(A: np.ndarray, p: int, n: int, g: float) -> None:
        """Estampa uma condutância ``g`` entre os nós ``p`` e ``n``."""
        if p != GROUND_INDEX:
            A[p, p] += g
        if n != GROUND_INDEX:
            A[n, n] += g
        if p != GROUND_INDEX and n != GROUND_INDEX:
            A[p, n] -= g
            A[n, p] -= g

    @staticmethod
    def _stamp_current_source(b: np.ndarray, p: int, n: int, i_hist: float) -> None:
        """Injeta ``I_hist`` (que SAI do nó ``p``) no vetor independente."""
        if p != GROUND_INDEX:
            b[p] -= i_hist
        if n != GROUND_INDEX:
            b[n] += i_hist

    @staticmethod
    def _stamp_incidence(A: np.ndarray, p: int, n: int, col: int) -> None:
        """Estampa a incidência ±1 da corrente de ramo MNA nas linhas de nó."""
        if p != GROUND_INDEX:
            A[p, col] += 1.0
        if n != GROUND_INDEX:
            A[n, col] -= 1.0

    def __repr__(self) -> str:  # pragma: no cover - conveniência
        return f"{type(self).__name__}({self.name!r}, {self.nodes!r})"


# ---------------------------------------------------------------------------
# Resistor
# ---------------------------------------------------------------------------


class Resistor(Component):
    """Resistor linear invariante no tempo.

    Modelo companheiro (Dommel 1969, §II): ``v = R·i`` é algébrico,
    logo ``G = 1/R`` e ``I_hist = 0`` — não há termo de histórico e o
    ramo é insensível ao modo de integração.
    """

    def __init__(self, name: str, node_p: str, node_n: str, resistance_ohm: float) -> None:
        super().__init__(name, (node_p, node_n))
        if self.nodes[0] == self.nodes[1]:
            raise ValueError(f"resistor {name!r} curto-circuitado (mesmo nó nos dois terminais)")
        self.resistance_ohm: float = _require_positive(resistance_ohm, "resistance_ohm")
        self._g: float = 1.0 / self.resistance_ohm
        self._v: float = 0.0

    def prepare(self, dt: float) -> None:
        super().prepare(dt)
        self._g = 1.0 / self.resistance_ohm

    def reset(self) -> None:
        self._v = 0.0

    @property
    def conductance_S(self) -> float:
        """Condutância companheira ``G = 1/R`` [S]."""
        return self._g

    def stamp_matrix(self, A: np.ndarray) -> None:
        self._stamp_conductance(A, self._idx[0], self._idx[1], self._g)

    def commit(self, x: np.ndarray, t: float, mode: str) -> None:
        self._v = node_voltage(x, self._idx[0]) - node_voltage(x, self._idx[1])

    def branch_voltage(self, index: int = 0) -> float:
        return self._v

    def branch_current(self, index: int = 0) -> float:
        return self._g * self._v


# ---------------------------------------------------------------------------
# Indutor
# ---------------------------------------------------------------------------


class Inductor(Component):
    """Indutor linear com modelo companheiro trapezoidal / Euler regressivo.

    Trapézio (Dommel 1969, eq. 5)::

        G_L = Δt/(2L)
        I_hist(t) = i(t−Δt) + (Δt/2L)·v(t−Δt)

    Euler regressivo de meio-passo ``h = Δt/2`` (CDA, Marti & Lin 1989)::

        G_L = h/L = Δt/(2L)   (idêntico ao trapezoidal)
        I_hist(t) = i(t−h)

    A condição inicial ``i_L(0)`` é imposta por ``initial_current_A`` —
    injeção clássica de condição inicial no termo de histórico.
    """

    def __init__(
        self,
        name: str,
        node_p: str,
        node_n: str,
        inductance_H: float,
        *,
        initial_current_A: float = 0.0,
    ) -> None:
        super().__init__(name, (node_p, node_n))
        if self.nodes[0] == self.nodes[1]:
            raise ValueError(f"indutor {name!r} curto-circuitado (mesmo nó nos dois terminais)")
        self.inductance_H: float = _require_positive(inductance_H, "inductance_H")
        self.initial_current_A: float = _require_finite(initial_current_A, "initial_current_A")
        self._g: float = 0.0
        self._v: float = 0.0
        self._i: float = self.initial_current_A

    def prepare(self, dt: float) -> None:
        super().prepare(dt)
        self._g = self._dt / (2.0 * self.inductance_H)

    def reset(self) -> None:
        self._v = 0.0
        self._i = self.initial_current_A

    @property
    def conductance_S(self) -> float:
        """``G_L = Δt/(2L)`` [S]."""
        return self._g

    def history_current_A(self, mode: str = MODE_TRAPEZOIDAL) -> float:
        """Termo ``I_hist`` para o modo de integração informado."""
        if mode == MODE_TRAPEZOIDAL:
            return self._i + self._g * self._v
        if mode == MODE_BACKWARD_EULER_HALF:
            return self._i
        raise ValueError(f"modo de integração inválido: {mode!r}")

    def stamp_matrix(self, A: np.ndarray) -> None:
        self._stamp_conductance(A, self._idx[0], self._idx[1], self._g)

    def stamp_rhs(self, b: np.ndarray, t: float, mode: str) -> None:
        self._stamp_current_source(
            b, self._idx[0], self._idx[1], self.history_current_A(mode)
        )

    def commit(self, x: np.ndarray, t: float, mode: str) -> None:
        i_hist = self.history_current_A(mode)
        v = node_voltage(x, self._idx[0]) - node_voltage(x, self._idx[1])
        self._i = self._g * v + i_hist
        self._v = v

    def branch_voltage(self, index: int = 0) -> float:
        return self._v

    def branch_current(self, index: int = 0) -> float:
        return self._i


# ---------------------------------------------------------------------------
# Capacitor
# ---------------------------------------------------------------------------


class Capacitor(Component):
    """Capacitor linear com modelo companheiro trapezoidal / Euler regressivo.

    Trapézio (Dommel 1969, eq. 8)::

        G_C = 2C/Δt
        I_hist(t) = −i(t−Δt) − (2C/Δt)·v(t−Δt)

    Euler regressivo de meio-passo ``h = Δt/2`` (CDA)::

        G_C = C/h = 2C/Δt     (idêntico ao trapezoidal)
        I_hist(t) = −(2C/Δt)·v(t−Δt)

    A condição inicial ``v_C(0)`` é imposta por ``initial_voltage_V``.
    """

    def __init__(
        self,
        name: str,
        node_p: str,
        node_n: str,
        capacitance_F: float,
        *,
        initial_voltage_V: float = 0.0,
    ) -> None:
        super().__init__(name, (node_p, node_n))
        if self.nodes[0] == self.nodes[1]:
            raise ValueError(f"capacitor {name!r} curto-circuitado (mesmo nó nos dois terminais)")
        self.capacitance_F: float = _require_positive(capacitance_F, "capacitance_F")
        self.initial_voltage_V: float = _require_finite(initial_voltage_V, "initial_voltage_V")
        self._g: float = 0.0
        self._v: float = self.initial_voltage_V
        self._i: float = 0.0

    def prepare(self, dt: float) -> None:
        super().prepare(dt)
        self._g = 2.0 * self.capacitance_F / self._dt

    def reset(self) -> None:
        self._v = self.initial_voltage_V
        self._i = 0.0

    @property
    def conductance_S(self) -> float:
        """``G_C = 2C/Δt`` [S]."""
        return self._g

    def history_current_A(self, mode: str = MODE_TRAPEZOIDAL) -> float:
        """Termo ``I_hist`` para o modo de integração informado."""
        if mode == MODE_TRAPEZOIDAL:
            return -self._i - self._g * self._v
        if mode == MODE_BACKWARD_EULER_HALF:
            return -self._g * self._v
        raise ValueError(f"modo de integração inválido: {mode!r}")

    def stamp_matrix(self, A: np.ndarray) -> None:
        self._stamp_conductance(A, self._idx[0], self._idx[1], self._g)

    def stamp_rhs(self, b: np.ndarray, t: float, mode: str) -> None:
        self._stamp_current_source(
            b, self._idx[0], self._idx[1], self.history_current_A(mode)
        )

    def commit(self, x: np.ndarray, t: float, mode: str) -> None:
        i_hist = self.history_current_A(mode)
        v = node_voltage(x, self._idx[0]) - node_voltage(x, self._idx[1])
        self._i = self._g * v + i_hist
        self._v = v

    def branch_voltage(self, index: int = 0) -> float:
        return self._v

    def branch_current(self, index: int = 0) -> float:
        return self._i


# ---------------------------------------------------------------------------
# Fonte de tensão ideal (MNA)
# ---------------------------------------------------------------------------


class VoltageSource(Component):
    """Fonte de tensão ideal senoidal com deslocamento contínuo opcional.

    Forma de onda::

        e(t) = V_pico · sin(2π f t + φ) + V_cc

    Estampagem MNA — acrescenta a incógnita ``i_src`` (positiva saindo
    do nó ``p``) e a equação de restrição ``v_p − v_n = e(t)``::

        [ …   +1 ] [ v ]   [ … ]
        [ +1  -1  0 ] [ i ] = [ e(t) ]

    Justificativa da escolha de MNA em vez de eliminação de nó fixo:
    a eliminação exige renumerar o sistema quando a topologia muda
    (chave em série com a fonte) e não representa a chave ideal sem
    impedância fictícia. Com MNA a dimensão do sistema é invariante e
    a fatoração pode ser cacheada por assinatura de topologia.
    """

    def __init__(
        self,
        name: str,
        node_p: str,
        node_n: str,
        *,
        amplitude_V: float,
        frequency_Hz: float = 60.0,
        phase_deg: float = 0.0,
        dc_offset_V: float = 0.0,
    ) -> None:
        super().__init__(name, (node_p, node_n))
        if self.nodes[0] == self.nodes[1]:
            raise ValueError(f"fonte {name!r} curto-circuitada (mesmo nó nos dois terminais)")
        self.amplitude_V: float = _require_finite(amplitude_V, "amplitude_V")
        self.frequency_Hz: float = _require_non_negative(frequency_Hz, "frequency_Hz")
        self.phase_deg: float = _require_finite(phase_deg, "phase_deg")
        self.dc_offset_V: float = _require_finite(dc_offset_V, "dc_offset_V")
        self._omega: float = 2.0 * math.pi * self.frequency_Hz
        self._phase_rad: float = math.radians(self.phase_deg)
        self._v: float = 0.0
        self._i: float = 0.0

    def n_extra(self) -> int:
        return 1

    def reset(self) -> None:
        self._v = 0.0
        self._i = 0.0

    def value_at(self, t: float) -> float:
        """Tensão da fonte no instante ``t`` [V]."""
        return self.amplitude_V * math.sin(self._omega * t + self._phase_rad) + self.dc_offset_V

    def stamp_matrix(self, A: np.ndarray) -> None:
        p, n = self._idx[0], self._idx[1]
        col = self._extra[0]
        self._stamp_incidence(A, p, n, col)
        if p != GROUND_INDEX:
            A[col, p] += 1.0
        if n != GROUND_INDEX:
            A[col, n] -= 1.0

    def stamp_rhs(self, b: np.ndarray, t: float, mode: str) -> None:
        b[self._extra[0]] += self.value_at(t)

    def commit(self, x: np.ndarray, t: float, mode: str) -> None:
        self._v = node_voltage(x, self._idx[0]) - node_voltage(x, self._idx[1])
        self._i = float(x[self._extra[0]])

    def branch_voltage(self, index: int = 0) -> float:
        return self._v

    def branch_current(self, index: int = 0) -> float:
        return self._i


def three_phase_voltage_sources(
    prefix: str,
    nodes_abc: Sequence[str],
    node_neutral: str,
    *,
    amplitude_V: float,
    frequency_Hz: float = 60.0,
    phase_deg: float = 0.0,
    sequence: str = "abc",
) -> list[VoltageSource]:
    """Constrói as três fontes de um sistema trifásico equilibrado.

    As defasagens são 0°, −120° e +120° em sequência direta (``"abc"``)
    e 0°, +120°, −120° em sequência inversa (``"acb"``). ``phase_deg`` é
    a fase inicial COMUM às três fontes, isto é, o ângulo da fase A no
    instante ``t = 0`` — parâmetro que, no estudo de manobra, define o
    instante de abertura relativo à onda de tensão.

    Raises
    ------
    ValueError
        ``nodes_abc`` sem exatamente 3 nós, ou ``sequence`` inválida.
    """
    nodes = tuple(str(n) for n in nodes_abc)
    if len(nodes) != 3:
        raise ValueError(f"nodes_abc deve conter exatamente 3 nós, obtidos {nodes!r}")
    if len(set(nodes)) != 3:
        raise ValueError(f"nodes_abc deve conter 3 nós DISTINTOS, obtidos {nodes!r}")
    seq = str(sequence).lower()
    if seq == "abc":
        offsets = (0.0, -120.0, 120.0)
    elif seq == "acb":
        offsets = (0.0, 120.0, -120.0)
    else:
        raise ValueError(f"sequence deve ser 'abc' ou 'acb', obtida {sequence!r}")
    labels = ("a", "b", "c")
    return [
        VoltageSource(
            f"{prefix}_{lab}",
            node,
            node_neutral,
            amplitude_V=amplitude_V,
            frequency_Hz=frequency_Hz,
            phase_deg=phase_deg + off,
        )
        for lab, node, off in zip(labels, nodes, offsets)
    ]


# ---------------------------------------------------------------------------
# Chave ideal controlada (MNA)
# ---------------------------------------------------------------------------


class Switch(Component):
    """Chave ideal controlada externamente.

    Estampagem MNA com DIMENSÃO INVARIANTE — a incógnita de corrente
    ``i_sw`` existe nos dois estados:

    * fechada: linha de restrição ``v_p − v_n = 0``;
    * aberta:  linha de restrição ``i_sw = 0``.

    Nos dois casos as linhas de nó recebem a incidência ``±i_sw``; com a
    chave aberta essa corrente é nula e o ramo não conduz. Não há
    resistência fictícia de chave aberta nem de chave fechada, o que
    elimina a constante de tempo espúria ``R_open·C`` que degrada o
    passo de integração em modelos com chave resistiva.

    Advertência física: a chave é IDEAL. Não há modelo de arco, de
    rigidez dielétrica de recuperação nem de corrente de *chopping* —
    esses fenômenos pertencem ao controlador que comanda a chave
    (camada acima do kernel).
    """

    def __init__(
        self,
        name: str,
        node_p: str,
        node_n: str,
        *,
        closed: bool = False,
    ) -> None:
        super().__init__(name, (node_p, node_n))
        if self.nodes[0] == self.nodes[1]:
            raise ValueError(f"chave {name!r} curto-circuitada (mesmo nó nos dois terminais)")
        self.closed: bool = bool(closed)
        self._v: float = 0.0
        self._i: float = 0.0

    def n_extra(self) -> int:
        return 1

    def reset(self) -> None:
        self._v = 0.0
        self._i = 0.0

    def topology_signature(self) -> object:
        return bool(self.closed)

    def set_state(self, closed: bool) -> bool:
        """Comanda a chave; devolve ``True`` se o estado mudou."""
        new_state = bool(closed)
        changed = new_state != self.closed
        self.closed = new_state
        return changed

    def close(self) -> bool:
        """Fecha a chave; devolve ``True`` se houve mudança de estado."""
        return self.set_state(True)

    def open(self) -> bool:
        """Abre a chave; devolve ``True`` se houve mudança de estado."""
        return self.set_state(False)

    def stamp_matrix(self, A: np.ndarray) -> None:
        p, n = self._idx[0], self._idx[1]
        col = self._extra[0]
        self._stamp_incidence(A, p, n, col)
        if self.closed:
            if p != GROUND_INDEX:
                A[col, p] += 1.0
            if n != GROUND_INDEX:
                A[col, n] -= 1.0
        else:
            A[col, col] += 1.0

    def commit(self, x: np.ndarray, t: float, mode: str) -> None:
        self._v = node_voltage(x, self._idx[0]) - node_voltage(x, self._idx[1])
        self._i = float(x[self._extra[0]])

    def branch_voltage(self, index: int = 0) -> float:
        return self._v

    def branch_current(self, index: int = 0) -> float:
        return self._i


# ---------------------------------------------------------------------------
# Ramo RL acoplado (n enrolamentos)
# ---------------------------------------------------------------------------


class CoupledRL(Component):
    """Ramo RL mutuamente acoplado de ``n`` enrolamentos.

    Equação de ramo ``v = R·i + L·di/dt`` com ``R`` e ``L`` matrizes
    ``n×n`` simétricas, ``L`` definida positiva. Modelo companheiro
    trapezoidal (dedução no cabeçalho do módulo)::

        G = (R + 2L/Δt)⁻¹
        I_hist(t) = G · [ v(t−Δt) + (2L/Δt − R)·i(t−Δt) ]         (trapézio)
        I_hist(t) = G · (2L/Δt)·i(t−h)                            (Euler h=Δt/2)

    **Simplificação declarada — transformador por impedância de
    dispersão.** Um transformador de dois enrolamentos é representado
    aqui pela matriz de indutâncias própria/mútua com acoplamento
    ``k = M/√(L₁L₂)`` próximo de 1, tudo REFERIDO a um mesmo lado.
    Consequências:

    * não há relação de espiras ideal — a razão de transformação deve
      ser embutida pelo usuário ao referir os parâmetros;
    * não há saturação, histerese nem perdas no ferro (o ramo é
      estritamente linear);
    * a capacitância entre enrolamentos, dominante na transferência de
      surto de frente rápida, NÃO está representada e deve ser
      adicionada como :class:`Capacitor` externo.

    Essa é a mesma classe de simplificação do modelo de dispersão de
    ramo do ATP (BCTRAN sem saturação), e é suficiente para o estudo de
    TRV em que o transformador aparece como impedância de curto.
    """

    def __init__(
        self,
        name: str,
        node_pairs: Sequence[Sequence[str]],
        inductance_H: Sequence[Sequence[float]] | np.ndarray,
        *,
        resistance_ohm: float | Sequence[float] | np.ndarray = 0.0,
    ) -> None:
        pairs = tuple(tuple(str(x) for x in pair) for pair in node_pairs)
        if not pairs:
            raise ValueError(f"CoupledRL {name!r} precisa de ao menos 1 par de nós")
        for pair in pairs:
            if len(pair) != 2:
                raise ValueError(
                    f"CoupledRL {name!r}: cada elemento de node_pairs deve ter 2 nós, "
                    f"obtido {pair!r}"
                )
            if pair[0] == pair[1]:
                raise ValueError(f"CoupledRL {name!r}: enrolamento curto-circuitado em {pair!r}")
        flat: list[str] = []
        for pair in pairs:
            flat.extend(pair)
        super().__init__(name, flat)
        self.node_pairs: tuple[tuple[str, str], ...] = pairs

        n = len(pairs)
        L = np.asarray(inductance_H, dtype=float)
        if L.ndim == 0:
            L = L.reshape(1, 1)
        if L.shape != (n, n):
            raise ValueError(
                f"CoupledRL {name!r}: inductance_H deve ser {n}x{n}, obtida {L.shape}"
            )
        if not np.all(np.isfinite(L)):
            raise ValueError(f"CoupledRL {name!r}: inductance_H contém valores não finitos")
        if not np.allclose(L, L.T, rtol=1e-12, atol=1e-18):
            raise ValueError(f"CoupledRL {name!r}: inductance_H deve ser simétrica")
        eigs = np.linalg.eigvalsh(L)
        if float(np.min(eigs)) <= 0.0:
            raise ValueError(
                f"CoupledRL {name!r}: inductance_H deve ser definida positiva "
                f"(menor autovalor {float(np.min(eigs)):.6g})"
            )
        self.inductance_H: np.ndarray = L

        R = np.asarray(resistance_ohm, dtype=float)
        if R.ndim == 0:
            R = np.eye(n) * float(R)
        elif R.ndim == 1:
            if R.shape[0] != n:
                raise ValueError(
                    f"CoupledRL {name!r}: resistance_ohm vetorial deve ter {n} elementos"
                )
            R = np.diag(R)
        elif R.shape != (n, n):
            raise ValueError(
                f"CoupledRL {name!r}: resistance_ohm deve ser escalar, vetor {n} ou {n}x{n}"
            )
        if not np.all(np.isfinite(R)):
            raise ValueError(f"CoupledRL {name!r}: resistance_ohm contém valores não finitos")
        if float(np.min(np.diag(R))) < 0.0:
            raise ValueError(f"CoupledRL {name!r}: resistência diagonal negativa")
        self.resistance_ohm: np.ndarray = R

        self._n = n
        self._G: np.ndarray = np.zeros((n, n))
        self._twoL_dt: np.ndarray = np.zeros((n, n))
        self._v: np.ndarray = np.zeros(n)
        self._i: np.ndarray = np.zeros(n)

    def n_branches(self) -> int:
        return self._n

    def prepare(self, dt: float) -> None:
        super().prepare(dt)
        self._twoL_dt = (2.0 / self._dt) * self.inductance_H
        self._G = np.linalg.inv(self.resistance_ohm + self._twoL_dt)

    def reset(self) -> None:
        self._v = np.zeros(self._n)
        self._i = np.zeros(self._n)

    @property
    def conductance_matrix_S(self) -> np.ndarray:
        """Matriz companheira ``G = (R + 2L/Δt)⁻¹`` [S]."""
        return self._G.copy()

    def history_current_A(self, mode: str = MODE_TRAPEZOIDAL) -> np.ndarray:
        """Vetor ``I_hist`` para o modo de integração informado."""
        if mode == MODE_TRAPEZOIDAL:
            return self._G @ (self._v + (self._twoL_dt - self.resistance_ohm) @ self._i)
        if mode == MODE_BACKWARD_EULER_HALF:
            return self._G @ (self._twoL_dt @ self._i)
        raise ValueError(f"modo de integração inválido: {mode!r}")

    def _pair_indices(self, k: int) -> tuple[int, int]:
        return self._idx[2 * k], self._idx[2 * k + 1]

    def stamp_matrix(self, A: np.ndarray) -> None:
        for p_row in range(self._n):
            a, b_ = self._pair_indices(p_row)
            for q_col in range(self._n):
                c, d = self._pair_indices(q_col)
                g = float(self._G[p_row, q_col])
                if g == 0.0:
                    continue
                for row, s_row in ((a, 1.0), (b_, -1.0)):
                    if row == GROUND_INDEX:
                        continue
                    for col, s_col in ((c, 1.0), (d, -1.0)):
                        if col == GROUND_INDEX:
                            continue
                        A[row, col] += s_row * s_col * g

    def stamp_rhs(self, b: np.ndarray, t: float, mode: str) -> None:
        i_hist = self.history_current_A(mode)
        for k in range(self._n):
            p, n = self._pair_indices(k)
            self._stamp_current_source(b, p, n, float(i_hist[k]))

    def commit(self, x: np.ndarray, t: float, mode: str) -> None:
        i_hist = self.history_current_A(mode)
        v = np.array(
            [
                node_voltage(x, self._pair_indices(k)[0])
                - node_voltage(x, self._pair_indices(k)[1])
                for k in range(self._n)
            ]
        )
        self._i = self._G @ v + i_hist
        self._v = v

    def branch_voltage(self, index: int = 0) -> float:
        return float(self._v[index])

    def branch_current(self, index: int = 0) -> float:
        return float(self._i[index])


__all__ = [
    "MODE_TRAPEZOIDAL",
    "MODE_BACKWARD_EULER_HALF",
    "INTEGRATION_MODES",
    "GROUND_NAMES",
    "GROUND_INDEX",
    "Component",
    "Resistor",
    "Inductor",
    "Capacitor",
    "VoltageSource",
    "Switch",
    "CoupledRL",
    "three_phase_voltage_sources",
    "is_ground",
    "node_voltage",
]
