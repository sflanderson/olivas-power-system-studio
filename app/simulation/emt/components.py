"""
app.simulation.emt.components — modelos companheiros (*companion models*)
de Dommel para o motor EMT dedicado do Olivas Power System Studio.

Fundamento
==========

O método nodal de Dommel [FONTE: Dommel 1969, §II, p. 388-390] discretiza
cada ramo com armazenamento de energia pela **regra trapezoidal** e o
substitui por um *equivalente companheiro*: uma condutância constante
``G`` em paralelo com uma fonte de corrente ``I_hist`` calculada apenas
com grandezas do passo anterior.

Fontes primárias contra as quais este módulo foi conferido equação a
equação:

* [FONTE: H. W. Dommel, "Digital computer solution of electromagnetic
  transients in single- and multiphase networks", *IEEE Trans. PAS*,
  vol. PAS-88, n. 4, pp. 388-399, abr. 1969] — eqs. (7a)/(7b) linha,
  (9a)/(9b) indutor, (10a)/(10b) capacitor, (11) resistor,
  (17a)/(17b) ramo acoplado, Apêndice I (recursões e pré-carga).
* [FONTE: C.-W. Ho, A. E. Ruehli, P. A. Brennan, "The modified nodal
  approach to network analysis", *IEEE Trans. CAS*, vol. CAS-22, n. 6,
  pp. 504-509, jun. 1975] — eq. (2) e Tabela I (*element stamps*).
* [FONTE: J. Lin, J. R. Martí, "Implementation of the CDA procedure in
  the EMTP", *IEEE Trans. Power Systems*, vol. 5, n. 2, pp. 394-402,
  maio 1990] — §2 (procedimento) e eqs. (2)-(4) (histórico de Euler
  regressivo com Δt/2).
* [FONTE: H. W. Dommel, "Nonlinear and time-varying elements in digital
  simulation of electromagnetic transients", *IEEE Trans. PAS*, vol.
  PAS-90, pp. 2561-2567, nov./dez. 1971] — §III (chave ideal como caso
  particular de resistência variante no tempo).
* [FONTE: J. Mahseredjian et al., "On a new approach for the simulation
  of transients in power systems", *EPSR* 77 (2007) 1514-1520] — §2,
  eq. (2) (formulação aumentada de posto fixo para chaves ideais).
* [LISTA: 01, Seções 1-2 e Tabela 1] e [LISTA: 02, Seção 1] — notação e
  convenções do autor, validadas contra o ATP.

Convenção de sinal adotada em TODO o pacote::

    i(t) = G · v(t) + I_hist(t)

com ``v = v_p − v_n`` (tensão do nó positivo menos a do negativo) e
``i`` positiva saindo do nó ``p`` e entrando no nó ``n``. É a mesma de
[LISTA: 02, eqs. (1)-(2)] e de [FONTE: Dommel 1969, eqs. (9a) e (10a)].

Álgebra dos modelos companheiros
=================================

**Resistor** — ``v = R·i`` é algébrico [FONTE: Dommel 1969, eq. (11),
p. 390]::

    G = 1/R,        I_hist = 0

**Indutor** — ``v = L·di/dt``. Integrando de ``t−Δt`` a ``t`` pela
regra trapezoidal [FONTE: Dommel 1969, eqs. (8b), (9a) e (9b),
p. 389]; [LISTA: 02, eq. (1)]; [LISTA: 01, Tabela 1]::

    i(t) − i(t−Δt) = (1/L) ∫ v dt ≈ (Δt / 2L) · [ v(t) + v(t−Δt) ]

    ⇒ i(t) = (Δt/2L)·v(t) + [ i(t−Δt) + (Δt/2L)·v(t−Δt) ]     (9a)

    G_L = Δt/(2L)
    I_hist(t) = i(t−Δt) + (Δt/2L)·v(t−Δt)                     (9b)

Forma recursiva equivalente, obtida substituindo (9a) em (9b) [FONTE:
Dommel 1969, Apêndice I, p. 395: ``I(t−Δt) = I(t−2Δt) + 2x`` com
``x = G·v(t−Δt)``, sinal **+** para indutância]; [LISTA: 02, eq. (3)]::

    I_L(t) = 2·G_L·v_L(t) + I_L(t−Δt)

Este módulo guarda o par ``(i, v)`` do passo anterior em vez do valor
recursivo único; as duas formas são **algebricamente idênticas** — a
prova está em :meth:`Inductor.commit` seguido de
:meth:`Inductor.history_current_A`, que reproduz exatamente
``2·G_L·v + I_hist_anterior``.

**Capacitor** — ``i = C·dv/dt``. Trapézio [FONTE: Dommel 1969, eqs.
(10a) e (10b), p. 390]; [LISTA: 02, eq. (2)]; [LISTA: 01, Tabela 1]::

    v(t) − v(t−Δt) = (1/C) ∫ i dt ≈ (Δt / 2C) · [ i(t) + i(t−Δt) ]

    ⇒ i(t) = (2C/Δt)·v(t) + [ −i(t−Δt) − (2C/Δt)·v(t−Δt) ]    (10a)

    G_C = 2C/Δt
    I_hist(t) = −i(t−Δt) − (2C/Δt)·v(t−Δt)                    (10b)

**Atenção ao sinal**: o termo histórico do capacitor é NEGATIVO nas
duas parcelas. A forma recursiva correspondente alterna de sinal a cada
passo [FONTE: Dommel 1969, Apêndice I, p. 395, sinal **−** para
capacitância]; [LISTA: 02, eq. (3)]; [LISTA: 01, §2.1]::

    I_C(t) = −2·G_C·v_C(t) − I_C(t−Δt)

**Ramo RL acoplado (n enrolamentos)** — ``v = R·i + L·di/dt`` com
``R`` e ``L`` matrizes ``n×n``. Trapézio [FONTE: Dommel 1969, eqs.
(17a) e (17b), p. 392]::

    v(t) + v(t−Δt) = R·[i(t)+i(t−Δt)] + (2L/Δt)·[i(t) − i(t−Δt)]

    ⇒ [S]·i(t) = v(t) + v(t−Δt) + ([S] − 2R)·i(t−Δt),  [S] = R + 2L/Δt

    G = [S]⁻¹
    I_hist(t) = [S]⁻¹ · [ v(t−Δt) + (2L/Δt − R)·i(t−Δt) ]      (17a)

Dommel escreve (17b) na forma recursiva ``[I(t−Δt)] = [H]([v(t−Δt)] +
[S][I(t−2Δt)]) − [I(t−2Δt)]`` com ``[H] = 2([S]⁻¹ − [S]⁻¹[R][S]⁻¹)``.
[CÁLCULO PRÓPRIO] As duas formas coincidem: ``[H][S] − 1 = 1 −
2[S]⁻¹[R]``, e substituindo ``i(t−Δt) = [S]⁻¹v(t−Δt) + I(t−2Δt)`` na
expressão acima recupera-se termo a termo a recursão publicada.

Amortecimento crítico (CDA) — o motivo da invariância da matriz
================================================================

A regra trapezoidal aplicada a uma descontinuidade (interrupção
abrupta da corrente de um indutor — exatamente o *chopping* do
disjuntor a vácuo) tem polo discreto ``z → −1`` e produz oscilação
numérica NÃO amortecida de período ``2Δt``, que não é fenômeno físico
[FONTE: Lin & Martí 1990, §2, p. 394]. O caso é reproduzido dígito a
dígito contra o ATP em [LISTA: 02, §3.8, eqs. (28)-(29)].

A correção do EMTP (*critical damping adjustment*) substitui UM passo
trapezoidal de ``Δt`` por DOIS meios-passos de Euler regressivo de
``h = Δt/2`` [FONTE: Lin & Martí 1990, §2, p. 394; conceito original em
J. R. Martí e J. Lin, "Suppression of numerical oscillations in the
EMTP", *IEEE Trans. Power Systems*, vol. 4, n. 2, pp. 739-747, 1989].
Euler regressivo com passo ``h`` [FONTE: Lin & Martí 1990, eqs. (2)-(4)
e Apêndice, eqs. (A.3), (A.5), (A.6)]; [LISTA: 01, §1.2, §2.2 e
Tabela 1]::

    Indutor:   i(t) = i(t−h) + (h/L)·v(t)
               ⇒ G = h/L,          I_hist = i(t−h)          eq. (4)

    Capacitor: i(t) = (C/h)·[v(t) − v(t−h)]
               ⇒ G = C/h,          I_hist = −(C/h)·v(t−h)

    RL acopl.: (R + L/h)·i(t) = v(t) + (L/h)·i(t−h)
               ⇒ G = (R + L/h)⁻¹,  I_hist = G·(L/h)·i(t−h)

Com ``h = Δt/2`` resulta ``h/L = Δt/(2L) = G_L`` e ``C/h = 2C/Δt =
G_C`` e ``(R + L/h) = (R + 2L/Δt)``: **as condutâncias companheiras
são IDÊNTICAS às trapezoidais**. Só o termo de histórico muda — é a
propriedade central declarada em [FONTE: Lin & Martí 1990, §2, p. 394 e
Conclusões, p. 401] e a razão pela qual o CDA não exige refatoração da
matriz, explorada pelo cache de fatoração em
:mod:`app.simulation.emt.circuit`.

Note-se que o histórico de Euler regressivo do indutor usa APENAS a
corrente do passo anterior, enquanto o trapezoidal usa corrente E
tensão [FONTE: Lin & Martí 1990, p. 395, comparação entre eqs. (3) e
(4)] — é exatamente essa supressão do termo de tensão que mata a
oscilação de período 2Δt.

Formulação nodal aumentada (MNA)
=================================

Fontes de tensão ideais e chaves ideais não têm equivalente Norton.
Adota-se a **análise nodal modificada** [FONTE: Ho, Ruehli & Brennan
1975, eq. (2) e Tabela I]; [LISTA: 02, §1.2, eqs. (4)-(5)]: cada uma
acrescenta uma incógnita de corrente de ramo e uma equação de
restrição. A alternativa (eliminação de nós de tensão conhecida) foi
descartada porque a chave ideal não tem tensão conhecida quando aberta
e porque a eliminação renumera o sistema a cada manobra — inviável para
o cache de fatoração. Detalhe adicional decisivo: mantendo a incógnita
de corrente da chave também no estado ABERTO (com a equação ``i = 0``),
a DIMENSÃO e o POSTO do sistema são invariantes à topologia e só os
coeficientes mudam — é o "*fixed rank system*" de [FONTE: Mahseredjian
et al. 2007, §2, p. 1516] e o "ponto essencial" de [LISTA: 02, §1.2].

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

#: Referências de fase aceitas por :class:`VoltageSource`. ``"cos"`` é a
#: convenção de fasor de amplitude do autor [LISTA: 02, §1.4].
PHASE_REFERENCES: tuple[str, ...] = ("sin", "cos")

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

    Modelo companheiro [FONTE: Dommel 1969, eq. (11), p. 390]:
    ``i_km(t) = (1/R)·(e_k(t) − e_m(t))`` é algébrico, logo ``G = 1/R``
    e ``I_hist = 0`` — não há termo de histórico e o ramo é insensível
    ao modo de integração. Resistências e linhas sem perdas são os
    únicos elementos tratados de forma RIGOROSA, sem erro de truncamento
    [FONTE: Dommel 1969, "Accuracy", p. 391].
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

    Trapézio [FONTE: Dommel 1969, eqs. (9a) e (9b), p. 389]; [LISTA: 02,
    eq. (1)]; [LISTA: 01, §1.1 e Tabela 1]::

        G_L = Δt/(2L)
        I_hist(t) = i(t−Δt) + (Δt/2L)·v(t−Δt)

    Forma recursiva equivalente [FONTE: Dommel 1969, Apêndice I, p. 395,
    sinal **+** para indutância]; [LISTA: 02, eq. (3)]::

        I_L(t) = 2·G_L·v_L(t) + I_L(t−Δt)

    :meth:`commit` armazena ``i(t)`` e ``v(t)``; a chamada seguinte de
    :meth:`history_current_A` devolve ``G_L·v + I_hist_anterior + G_L·v``
    ``= 2·G_L·v + I_hist_anterior`` — exatamente a recursão publicada.

    Euler regressivo de meio-passo ``h = Δt/2`` (CDA) [FONTE: Lin &
    Martí 1990, eqs. (2) e (4), p. 395]; [LISTA: 01, §1.2 e Tabela 1]::

        G_L = h/L = Δt/(2L)   (idêntico ao trapezoidal)
        I_hist(t) = i(t−h)    — só a corrente, sem o termo de tensão

    Condições iniciais não nulas. [FONTE: Dommel 1969, Apêndice I,
    p. 395: ``I(inicial)`` deve ser pré-carregado a partir de ``i(0)`` e
    ``e(0)``]; [LISTA: 02, eq. (6): ``I_L(0) = i_L(0) + G_L·v_L(0)``].
    Por isso os DOIS parâmetros são necessários: ``initial_current_A``
    (``i_L(0)``) e ``initial_voltage_V`` (``v_L(0)``). Impor apenas a
    corrente equivale a assumir ``v_L(0) = 0``, o que é correto no
    repouso mas ERRADO na partida em regime permanente senoidal — e,
    conforme [LISTA: 01, §6.2, verificação 2], é justamente a semeadura
    de ``v_L(0⁺)`` que restaura a ordem 2 de convergência da regra
    trapezoidal (``p`` medido sobe de 1,02 para 1,998).
    """

    def __init__(
        self,
        name: str,
        node_p: str,
        node_n: str,
        inductance_H: float,
        *,
        initial_current_A: float = 0.0,
        initial_voltage_V: float = 0.0,
    ) -> None:
        super().__init__(name, (node_p, node_n))
        if self.nodes[0] == self.nodes[1]:
            raise ValueError(f"indutor {name!r} curto-circuitado (mesmo nó nos dois terminais)")
        self.inductance_H: float = _require_positive(inductance_H, "inductance_H")
        self.initial_current_A: float = _require_finite(initial_current_A, "initial_current_A")
        self.initial_voltage_V: float = _require_finite(initial_voltage_V, "initial_voltage_V")
        self._g: float = 0.0
        self._v: float = self.initial_voltage_V
        self._i: float = self.initial_current_A

    def prepare(self, dt: float) -> None:
        super().prepare(dt)
        self._g = self._dt / (2.0 * self.inductance_H)

    def reset(self) -> None:
        # Pré-carga do histórico conforme [FONTE: Dommel 1969, Apêndice I,
        # p. 395] e [LISTA: 02, eq. (6)]: I_L(0) = i_L(0) + G_L·v_L(0).
        self._v = self.initial_voltage_V
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

    Trapézio [FONTE: Dommel 1969, eqs. (10a) e (10b), p. 390]; [LISTA:
    02, eq. (2)]; [LISTA: 01, §2.1 e Tabela 1]::

        G_C = 2C/Δt
        I_hist(t) = −i(t−Δt) − (2C/Δt)·v(t−Δt)

    **As duas parcelas são negativas** — é o ponto em que a álgebra do
    capacitor difere estruturalmente da do indutor. A forma recursiva
    alterna de sinal a cada passo [FONTE: Dommel 1969, Apêndice I,
    p. 395, sinal **−** para capacitância]; [LISTA: 02, eq. (3)]::

        I_C(t) = −2·G_C·v_C(t) − I_C(t−Δt)

    Euler regressivo de meio-passo ``h = Δt/2`` (CDA) [FONTE: Lin &
    Martí 1990, §3, p. 395, "o tratamento do ramo capacitivo é
    inteiramente análogo ao do indutivo"]; [LISTA: 01, Tabela 1]::

        G_C = C/h = 2C/Δt     (idêntico ao trapezoidal)
        I_hist(t) = −(2C/Δt)·v(t−Δt)   — só a tensão, sem o termo de corrente

    Condições iniciais não nulas [FONTE: Dommel 1969, Apêndice I,
    p. 395]; [LISTA: 02, eq. (6): ``I_C(0) = −[G_C·v_C(0) + i_C(0)]``]:
    exigem os DOIS parâmetros, ``initial_voltage_V`` (``v_C(0)``) e
    ``initial_current_A`` (``i_C(0)``). Impor apenas a tensão equivale a
    assumir ``i_C(0) = 0``, correto no repouso e errado na partida em
    regime permanente senoidal.
    """

    def __init__(
        self,
        name: str,
        node_p: str,
        node_n: str,
        capacitance_F: float,
        *,
        initial_voltage_V: float = 0.0,
        initial_current_A: float = 0.0,
    ) -> None:
        super().__init__(name, (node_p, node_n))
        if self.nodes[0] == self.nodes[1]:
            raise ValueError(f"capacitor {name!r} curto-circuitado (mesmo nó nos dois terminais)")
        self.capacitance_F: float = _require_positive(capacitance_F, "capacitance_F")
        self.initial_voltage_V: float = _require_finite(initial_voltage_V, "initial_voltage_V")
        self.initial_current_A: float = _require_finite(initial_current_A, "initial_current_A")
        self._g: float = 0.0
        self._v: float = self.initial_voltage_V
        self._i: float = self.initial_current_A

    def prepare(self, dt: float) -> None:
        super().prepare(dt)
        self._g = 2.0 * self.capacitance_F / self._dt

    def reset(self) -> None:
        # Pré-carga do histórico conforme [FONTE: Dommel 1969, Apêndice I,
        # p. 395] e [LISTA: 02, eq. (6)]: I_C(0) = −[G_C·v_C(0) + i_C(0)].
        self._v = self.initial_voltage_V
        self._i = self.initial_current_A

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

    Forma de onda, conforme ``phase_reference``::

        "sin" (padrão):  e(t) = V_pico · sin(2π f t + φ) + V_cc
        "cos":           e(t) = V_pico · cos(2π f t + φ) + V_cc

    A referência ``"cos"`` é a convenção fixada pelo autor — "fasor de
    amplitude com o cosseno como referência, de modo que
    ``x(t) = Re{X̂ e^{jωt}}``" [LISTA: 02, §1.4] — e é a que torna
    ``e(0) = V_pico`` para ``φ = 0``, como nos dois circuitos de
    referência validados contra o ATP (``vs(t) = 100·cos(377 t)`` V).
    Use-a sempre que as condições iniciais vierem de uma solução
    fasorial; a referência seno é mantida como padrão apenas por
    compatibilidade com o restante do pacote.

    Estampagem MNA [FONTE: Ho, Ruehli & Brennan 1975, Tabela I, entrada
    ``E``, p. 505]; [LISTA: 02, §1.2, eqs. (4)-(5)] — acrescenta a
    incógnita ``i_src`` e a equação de restrição ``v_p − v_n = e(t)``::

        [ …    +1 ] [ v ]   [ …    ]
        [ +1 −1  0 ] [ i ] = [ e(t) ]

    Convenção de sinal de ``i_src`` [LISTA: 02, §1.2]: a LKC é escrita
    somando as correntes que SAEM de cada nó, e ``i_src`` é a corrente
    que ENTRA pelo terminal positivo da fonte — daí o ``+1`` na linha do
    nó ``p``. Consequência prática, também registrada na Lista 02: a
    corrente FORNECIDA pela fonte ao circuito é ``−i_src``, e é esse o
    sinal a usar ao comparar com a corrente impressa pelo ATP.

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
        phase_reference: str = "sin",
    ) -> None:
        super().__init__(name, (node_p, node_n))
        if self.nodes[0] == self.nodes[1]:
            raise ValueError(f"fonte {name!r} curto-circuitada (mesmo nó nos dois terminais)")
        self.amplitude_V: float = _require_finite(amplitude_V, "amplitude_V")
        self.frequency_Hz: float = _require_non_negative(frequency_Hz, "frequency_Hz")
        self.phase_deg: float = _require_finite(phase_deg, "phase_deg")
        self.dc_offset_V: float = _require_finite(dc_offset_V, "dc_offset_V")
        ref = str(phase_reference).lower()
        if ref not in PHASE_REFERENCES:
            raise ValueError(
                f"phase_reference deve ser um de {PHASE_REFERENCES}, "
                f"obtida {phase_reference!r}"
            )
        self.phase_reference: str = ref
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
        """Tensão da fonte no instante ``t`` [V].

        Seno ou cosseno conforme ``phase_reference``; a segunda opção é a
        convenção de fasor de amplitude do autor [LISTA: 02, §1.4].
        """
        arg = self._omega * t + self._phase_rad
        wave = math.cos(arg) if self.phase_reference == "cos" else math.sin(arg)
        return self.amplitude_V * wave + self.dc_offset_V

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
    phase_reference: str = "sin",
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
            phase_reference=phase_reference,
        )
        for lab, node, off in zip(labels, nodes, offsets)
    ]


# ---------------------------------------------------------------------------
# Chave ideal controlada (MNA)
# ---------------------------------------------------------------------------


class Switch(Component):
    """Chave ideal controlada externamente.

    A chave é ideal no sentido de [FONTE: Dommel 1969, "Switches",
    p. 391]: ``R = 0`` fechada e ``R = ∞`` aberta; qualquer propriedade
    física (resistência variável no tempo, arco) é obtida por ramos em
    série ou em paralelo. É também o caso particular de resistência
    variante no tempo de [FONTE: Dommel 1971, §III, p. 2561].

    Estampagem MNA com DIMENSÃO E POSTO INVARIANTES — a incógnita de
    corrente ``i_sw`` existe nos dois estados [LISTA: 02, §1.2, eqs. (5)
    e (18)]; [FONTE: Mahseredjian et al. 2007, §2, p. 1516]:

    * fechada: linha de restrição ``v_k − v_m = 0``;
    * aberta:  linha de restrição ``i_km = 0`` (célula diagonal = 1).

    Nos dois casos as linhas de nó recebem a incidência ``±i_sw``; com a
    chave aberta essa corrente é nula e o ramo não conduz. Só UMA LINHA
    da matriz muda na comutação — "o ponto essencial", nas palavras de
    [LISTA: 02, §1.2].

    Não há resistência fictícia de chave aberta nem de chave fechada, o
    que elimina a constante de tempo espúria ``R_open·C`` que degrada o
    passo de integração em modelos com chave resistiva, e evita as
    "*superfluous natural frequencies and matrix conditioning
    problems*" de [FONTE: Mahseredjian et al. 2007, §1, p. 1515].

    Diferença deliberada em relação a [FONTE: Dommel 1969, p. 391], que
    reordena os nós com chave para o fim da matriz e refaz apenas a
    parte inferior da fatoração: aqui a matriz é remontada inteira e a
    fatoração é recuperada do cache por assinatura de topologia (ver
    :mod:`app.simulation.emt.circuit`). O ganho de Dommel vem da
    esparsidade em redes grandes; o ganho do cache vem da RECORRÊNCIA
    das mesmas duas topologias em sequências de reignição — o regime de
    uso deste kernel.

    Campo ``Imar``. ``current_margin_A`` reproduz o campo *current
    margin* (colunas 35-44) do cartão de chave do ATP: a abertura
    comandada só se efetiva no primeiro instante em que ``|i| <= Imar``
    [LISTA: 02, §1.3 e §3.6]. O teste está em :meth:`may_interrupt` e a
    ação em :meth:`open_within_margin`; quem comanda o instante ``t0`` é
    o controlador (:class:`app.simulation.emt.TimedSwitchController` ou
    o polo de :mod:`app.simulation.emt.vcb`). ``None`` (padrão) =
    abertura forçada, sem critério de corrente.

    Advertência física: a chave é IDEAL. Não há modelo de arco, de
    rigidez dielétrica de recuperação nem de corrente de *chopping* —
    esses fenômenos pertencem ao controlador que comanda a chave
    (camada acima do kernel; ver :mod:`app.simulation.emt.vcb`).
    """

    def __init__(
        self,
        name: str,
        node_p: str,
        node_n: str,
        *,
        closed: bool = False,
        current_margin_A: float | None = None,
    ) -> None:
        super().__init__(name, (node_p, node_n))
        if self.nodes[0] == self.nodes[1]:
            raise ValueError(f"chave {name!r} curto-circuitada (mesmo nó nos dois terminais)")
        self.closed: bool = bool(closed)
        if current_margin_A is None:
            self.current_margin_A: float | None = None
        else:
            self.current_margin_A = _require_non_negative(
                current_margin_A, "current_margin_A"
            )
        self._v: float = 0.0
        self._i: float = 0.0

    def n_extra(self) -> int:
        return 1

    # -- critério de margem de corrente (campo Imar do cartão do ATP) -------

    def may_interrupt(self, current_A: float | None = None) -> bool:
        """``True`` se a abertura comandada pode se efetivar AGORA.

        Implementa o campo **Imar** (*current margin*, colunas 35-44) do
        cartão de chave do ATP, cuja semântica é a da Seção 5 das notas
        de aula: "a abertura comandada em ``t0`` só se efetiva a partir
        do primeiro instante ``t >= t0`` em que a corrente na chave se
        anula ou cai abaixo de um limiar ``|Imar|``" [LISTA: 02, §1.3 e
        §3.6]. É esse campo — e só ele — que representa o CORTE DE
        CORRENTE do disjuntor a vácuo: "sem o campo Imar o ATP esperaria
        um zero natural de corrente e a sobretensão praticamente
        desapareceria" [LISTA: 02, §3.6].

        ``current_margin_A = None`` significa AUSÊNCIA de critério, isto
        é, abertura forçada no instante comandado — o interruptor ideal
        do ensaio numérico, não o disjuntor.

        Parameters
        ----------
        current_A:
            Corrente a testar [A]. ``None`` (padrão) usa a corrente do
            último passo resolvido, :meth:`branch_current`.
        """
        if self.current_margin_A is None:
            return True
        i = self._i if current_A is None else float(current_A)
        return abs(i) <= self.current_margin_A

    def open_within_margin(self, current_A: float | None = None) -> bool:
        """Abre a chave se o critério ``Imar`` permitir.

        Returns
        -------
        bool
            ``True`` se a interrupção está efetivada ao fim da chamada
            (a chave abriu agora ou já estava aberta pelo critério);
            ``False`` se a corrente ainda excede ``|Imar|`` e a chave
            permanece fechada.
        """
        if not self.may_interrupt(current_A):
            return False
        self.set_state(False)
        return True

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
        """Estampa a chave conforme [LISTA: 02, eqs. (5) e (18)].

        Fechada: ``v_k − v_m = 0``. Aberta: ``i_km = 0``, obtido pondo 1
        na célula diagonal da linha de restrição — exatamente o
        ``S_d`` de [FONTE: Mahseredjian et al. 2007, eq. (2), p. 1516].
        O lado direito da linha é nulo nos dois estados, por isso
        :meth:`stamp_rhs` não é sobrescrito.
        """
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
    trapezoidal [FONTE: Dommel 1969, eqs. (17a) e (17b), p. 392], com
    ``[S] = [R] + (2/Δt)[L]`` — dedução e prova de equivalência com a
    recursão publicada no cabeçalho do módulo::

        G = [S]⁻¹ = (R + 2L/Δt)⁻¹
        I_hist(t) = G · [ v(t−Δt) + (2L/Δt − R)·i(t−Δt) ]         (trapézio)
        I_hist(t) = G · (2L/Δt)·i(t−h)                            (Euler h=Δt/2)

    O modo de Euler regressivo segue [FONTE: Lin & Martí 1990, §3,
    p. 395]: "o procedimento estende-se de imediato a ramos acoplados
    indutivamente, que têm as mesmas relações do indutor básico, porém
    em forma matricial". Como em (17), na montagem de ``[Y]`` entra a
    matriz ``[S]⁻¹`` no lugar de um escalar.

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
        initial_current_A: Sequence[float] | np.ndarray | None = None,
        initial_voltage_V: Sequence[float] | np.ndarray | None = None,
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
        self.initial_current_A: np.ndarray = np.zeros(n)
        self.initial_voltage_V: np.ndarray = np.zeros(n)
        self.set_initial_state(
            current_A=initial_current_A, voltage_V=initial_voltage_V
        )
        self._v: np.ndarray = self.initial_voltage_V.copy()
        self._i: np.ndarray = self.initial_current_A.copy()

    def n_branches(self) -> int:
        return self._n

    def set_initial_state(
        self,
        *,
        current_A: Sequence[float] | np.ndarray | None = None,
        voltage_V: Sequence[float] | np.ndarray | None = None,
    ) -> None:
        """Impõe ``i(0)`` e ``v(0)`` de cada enrolamento.

        Os dois vetores são necessários pelo mesmo motivo do indutor
        escalar: o termo histórico trapezoidal do ramo acoplado vale
        ``I_hist = G·[v(0) + (2L/Δt − R)·i(0)]``, de modo que impor
        apenas a corrente equivale a assumir ``v(0) = 0`` — correto no
        repouso e ERRADO na partida em regime permanente senoidal
        [FONTE: Dommel 1969, eq. (17b), p. 392 e Apêndice I, p. 395];
        [LISTA: 02, eq. (6)].

        ``None`` mantém o vetor nulo. É este o gancho usado por
        :func:`app.simulation.emt.steady_state.seed_from_phasor`.
        """
        if current_A is not None:
            vec = np.asarray(current_A, dtype=float).reshape(-1)
            if vec.shape[0] != self._n:
                raise ValueError(
                    f"CoupledRL {self.name!r}: initial_current_A deve ter "
                    f"{self._n} elementos, obtidos {vec.shape[0]}"
                )
            if not np.all(np.isfinite(vec)):
                raise ValueError(
                    f"CoupledRL {self.name!r}: initial_current_A não finita"
                )
            self.initial_current_A = vec
        if voltage_V is not None:
            vec = np.asarray(voltage_V, dtype=float).reshape(-1)
            if vec.shape[0] != self._n:
                raise ValueError(
                    f"CoupledRL {self.name!r}: initial_voltage_V deve ter "
                    f"{self._n} elementos, obtidos {vec.shape[0]}"
                )
            if not np.all(np.isfinite(vec)):
                raise ValueError(
                    f"CoupledRL {self.name!r}: initial_voltage_V não finita"
                )
            self.initial_voltage_V = vec

    def prepare(self, dt: float) -> None:
        super().prepare(dt)
        self._twoL_dt = (2.0 / self._dt) * self.inductance_H
        self._G = np.linalg.inv(self.resistance_ohm + self._twoL_dt)

    def reset(self) -> None:
        # Pré-carga do histórico [FONTE: Dommel 1969, Apêndice I, p. 395];
        # [LISTA: 02, eq. (6)], em forma vetorial.
        self._v = self.initial_voltage_V.copy()
        self._i = self.initial_current_A.copy()

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
    "PHASE_REFERENCES",
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
