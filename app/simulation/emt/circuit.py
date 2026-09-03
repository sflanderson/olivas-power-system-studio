"""
app.simulation.emt.circuit — montagem do circuito, fatoração LU com cache
por assinatura de topologia e laço de marcha no tempo (solver de Dommel).

Formulação
==========

O sistema resolvido a cada passo é a **análise nodal modificada** (MNA)

    A · x = b(t)

com ``x = [ v₁ … v_N , i_src₁ … i_srcM ]ᵀ``, onde:

* ``v_i`` são as tensões nodais em relação à terra (o nó de referência
  NÃO entra no sistema — sua linha e coluna são eliminadas, o que
  torna ``A`` não singular);
* ``i_src`` são as correntes de ramo das fontes de tensão ideais e das
  chaves ideais (ver :mod:`app.simulation.emt.components`).

A matriz ``A`` depende SOMENTE de ``Δt`` e do estado das chaves. Não
depende do modo de integração: como demonstrado no cabeçalho de
``components.py``, o Euler regressivo de meio-passo ``h = Δt/2`` produz
exatamente as mesmas condutâncias companheiras da regra trapezoidal de
passo ``Δt``. Só o vetor ``b`` muda.

A estrutura ``[[G, A_c], [A_l, A_d]]·[v_n; i_x] = [i_n; v_x]`` é a de
[FONTE: Ho, Ruehli & Brennan 1975, eq. (2), p. 504]; a notação e a
partição adotadas aqui são as de [LISTA: 02, §1.2, eq. (4)], em que
``G`` é a matriz de condutâncias nodal, ``v_n`` as tensões nodais
desconhecidas, ``i_x`` as correntes desconhecidas (fontes de tensão e
chaves), ``i_n`` as correntes conhecidas (fontes de corrente e termos
históricos) e ``v_x`` as tensões conhecidas.

[FONTE: H. W. Dommel, "Digital computer solution of electromagnetic
transients in single- and multiphase networks", *IEEE Trans. PAS*, vol.
PAS-88, n. 4, pp. 388-399, abr. 1969] — eqs. (12)-(13), p. 390.
[FONTE: C.-W. Ho, A. E. Ruehli, P. A. Brennan, "The modified nodal
approach to network analysis", *IEEE Trans. CAS*, vol. CAS-22, n. 6,
pp. 504-509, jun. 1975.]
[FONTE: J. Mahseredjian et al., "On a new approach for the simulation
of transients in power systems", *EPSR* 77 (2007) 1514-1520] — §2.
[LITERATURA: J. A. Martinez-Velasco (ed.), *Transient Analysis of
Power Systems: Solution Techniques, Tools and Applications*, Wiley/IEEE
Press, 2015, cap. 2.]

Amortecimento crítico (CDA) — procedimento publicado
=====================================================

O procedimento implementado é o de [FONTE: J. Lin, J. R. Martí,
"Implementation of the CDA procedure in the EMTP", *IEEE Trans. Power
Systems*, vol. 5, n. 2, pp. 394-402, maio 1990, §2, p. 394], reproduzido
aqui passo a passo porque é o ponto do kernel em que a paráfrase é mais
perigosa. Conceito original em [LITERATURA: J. R. Martí e J. Lin,
"Suppression of numerical oscillations in the EMTP", *IEEE Trans. Power
Systems*, vol. 4, n. 2, pp. 739-747, 1989].

1. A rede marcha normalmente com a regra trapezoidal em
   ``t = 0, Δt, 2Δt, …`` até que uma descontinuidade esteja prevista
   para ``t₁⁺``. São descontinuidades: manobras de chave, saltos no
   valor das fontes (**inclusive em ``t = 0``**) e transições de
   segmento em indutâncias lineares por partes.
2. A rede é resolvida NORMALMENTE em ``t₁``, supondo que a
   descontinuidade ainda não ocorreu — é a solução para ``t₁⁻``.
3. A descontinuidade é então aplicada (a matriz muda de topologia) e o
   CDA entra em ação.
4. O ponto seguinte é obtido em ``t₁ + Δt/2`` pela regra de Euler
   regressivo com passo ``Δt/2``. Como as condutâncias companheiras do
   Euler regressivo com ``Δt/2`` são IDÊNTICAS às da regra trapezoidal
   com ``Δt``, "a matriz [G] da eq. (1) não muda; só as fórmulas do
   vetor de históricos [h(t)] precisam mudar".
5. A rede é resolvida uma SEGUNDA vez por Euler regressivo com ``Δt/2``,
   em ``t₂ = (t₁ + Δt/2) + Δt/2 = t₁ + Δt`` — de modo que a marcha
   volta a cair sobre a malha uniforme de ``Δt``.
6. Em seguida a simulação prossegue normalmente com a regra trapezoidal
   em ``t₂ + Δt``, ``t₂ + 2Δt``, … até a próxima descontinuidade.

São, portanto, EXATAMENTE DOIS meios-passos por descontinuidade, com
passo ``h = Δt/2``, iniciados no instante da mudança de topologia e
terminando sobre o ponto ``t₁ + Δt`` da malha regular.

Regra de decisão durante o CDA (item explícito da fonte): "os
resultados em ``t₁ + Δt/2`` são apenas quantidades matemáticas usadas
pelo procedimento CDA, sem significado físico. Portanto NENHUMA decisão
sobre abrir ou fechar chaves é tomada com base nesses resultados. As
decisões seguintes são tomadas em ``t₁ + Δt``, quando a sobre-elongação
já foi amortecida." A única exceção admitida pela fonte é a transição
de segmento em indutâncias lineares por partes, que não existe neste
kernel. A implementação respeita a regra: os controladores só são
chamados no início de cada passo COMPLETO (ver :meth:`Solver.run`).

Reconstrução do histórico ao voltar ao trapezoidal: nenhuma é
necessária. O segundo meio-passo termina sobre ``t₂ = t₁ + Δt`` e deixa
``i(t₂)`` e ``v(t₂)`` armazenados em cada ramo; o passo trapezoidal
seguinte lê exatamente esse par pelas eqs. (9b)/(10b) de Dommel. É por
isso que o CDA "não interfere no esquema normal de solução do EMTP e
não exige o reajuste de condições iniciais nem outras complicações"
[FONTE: Lin & Martí 1990, §2, p. 394].

Por que isso é indispensável neste projeto: ao interromper a corrente
de um indutor (o *chopping* do disjuntor a vácuo, ``I_ch`` de 1 a 2 A
segundo o Documento A), a regra trapezoidal aplicada ao ramo
``L`` em série com uma resistência elevada ``R`` tem polo discreto

    z = (1 − R·Δt/2L) / (1 + R·Δt/2L)  →  −1   quando R·Δt/2L ≫ 1

isto é, oscilação de período ``2Δt`` com amortecimento desprezível.
Essa oscilação é ARTEFATO NUMÉRICO e contamina diretamente ``V_pk`` e
``dv/dt`` — as duas grandezas que alimentam o modelo de dano
dielétrico. Com Euler regressivo de meio-passo o polo é

    z = 1 / (1 + R·h/L)  →  0⁺

e o artefato desaparece em dois meios-passos. A opção
``cda_enabled=False`` existe APENAS para demonstrar o artefato em
ensaio numérico (cf. ``tests/test_emt_kernel.py``) e emite ``WARNING``.

Fatoração com cache — escolha justificada por medição
======================================================

``scipy`` não é dependência declarada do projeto (política de
dependências §4.7 do mapa de convenções), portanto não há
``scipy.linalg.lu_factor``/``lu_solve``. Restam três caminhos sobre
``numpy``, e a decisão foi tomada por MEDIÇÃO, não por princípio:

1. ``numpy.linalg.solve`` a cada passo — refatora a matriz toda vez,
   custo ``O(n³)``, mas inteiramente em LAPACK compilado;
2. fatoração LU de Doolittle própria (:func:`lu_factor`) com
   substituição direta/regressiva (:func:`lu_solve`) — ``O(n³)`` uma
   vez por topologia e ``O(n²)`` por passo, porém com o laço de
   substituição em PYTHON;
3. inversa cacheada por topologia, aplicada como ``A⁻¹·b`` — um único
   produto matriz-vetor em BLAS, ``O(n²)`` inteiramente compilado.

[CÁLCULO PRÓPRIO — medição desta sessão, matriz MNA real de um caso de
manobra com ``n = 7`` e número de condição 2,2·10²; tempo por solução:]

===================  ==========  ===========  ===========
caminho              n = 7       n = 32       n = 128
===================  ==========  ===========  ===========
``np.linalg.solve``  5,48 µs     16,2 µs      199,0 µs
``lu_solve`` (LU)    23,25 µs    112,2 µs     481,3 µs
``A⁻¹·b``            1,08 µs     1,24 µs      2,95 µs
===================  ==========  ===========  ===========

Erro relativo contra ``np.linalg.solve`` na mesma matriz: 7,2·10⁻¹⁹
para a substituição LU e 9,2·10⁻¹⁷ para a inversa — ambos dez ordens
de grandeza abaixo de qualquer significância física, e a matriz MNA
deste kernel é bem condicionada porque não há impedância fictícia de
chave (é exatamente o ganho da formulação MNA).

Decisão: o caminho padrão (``solve_strategy="auto"``) FATORA por LU
própria — que dá detecção explícita de singularidade com pivotamento
parcial e a estimativa de condicionamento — e aplica a solução pela
inversa cacheada. Se o condicionamento estimado exceder
:data:`INVERSE_CONDITION_LIMIT`, o solver registra ``WARNING`` e passa
a usar a substituição LU naquela topologia, que é a mais precisa.
``solve_strategy="lu"`` força a substituição LU para auditoria.

O cache ``assinatura de topologia → fatoração`` é o que torna tudo
isso relevante: numa sequência de reignições de VCB a mesma topologia
recorre milhares de vezes. [CÁLCULO PRÓPRIO: 6.666 mudanças de
topologia alternando entre 2 estados ⇒ 2 fatorações com cache contra
6.667 sem cache.]

Este módulo é puro: sem I/O, sem GUI, sem estado global,
determinístico.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

import numpy as np

from app.core.logging_config import get_logger

from app.simulation.emt.components import (
    MODE_BACKWARD_EULER_HALF,
    MODE_TRAPEZOIDAL,
    Component,
    Switch,
    is_ground,
)
from app.simulation.emt.steady_state import (
    INIT_MODES,
    INIT_STEADY_STATE,
    INIT_ZERO,
    PhasorSolution,
    initialize_steady_state,
)

log = get_logger(__name__)


#: Tolerância relativa de pivô abaixo da qual a matriz é considerada singular.
PIVOT_TOLERANCE: float = 1.0e-14

#: Número padrão de fatorações mantidas no cache (LRU simples).
DEFAULT_FACTORIZATION_CACHE_SIZE: int = 256

#: Condicionamento (estimativa em norma 1) acima do qual a aplicação por
#: inversa cacheada é abandonada em favor da substituição LU, mais precisa.
#: Valor de engenharia: com condicionamento de 1e10 e dupla precisão
#: (eps = 2,2e-16) ainda restam ~6 dígitos significativos na solução.
INVERSE_CONDITION_LIMIT: float = 1.0e10

#: Estratégias aceitas por ``Solver(solve_strategy=...)``.
SOLVE_STRATEGIES: tuple[str, ...] = ("auto", "inverse", "lu")


class SingularSystemError(RuntimeError):
    """Sistema MNA singular — tipicamente um nó flutuante ou laço de fontes."""


# ---------------------------------------------------------------------------
# Fatoração LU de Doolittle com pivotamento parcial (numpy puro)
# ---------------------------------------------------------------------------


def lu_factor(A: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fatoração ``P·A = L·U`` de Doolittle com pivotamento parcial.

    ``L`` (unitária na diagonal) e ``U`` são armazenadas no mesmo
    arranjo ``LU``: a parte estritamente inferior contém os
    multiplicadores de ``L`` e a triangular superior contém ``U``.

    Complexidade ``O(n³)`` com atualização de posto 1 vetorizada.

    Raises
    ------
    SingularSystemError
        Pivô nulo (dentro de :data:`PIVOT_TOLERANCE` relativo à maior
        magnitude da matriz original).
    """
    M = np.array(A, dtype=float, copy=True)
    if M.ndim != 2 or M.shape[0] != M.shape[1]:
        raise ValueError(f"lu_factor exige matriz quadrada, obtida {M.shape}")
    n = M.shape[0]
    piv = np.arange(n, dtype=np.intp)
    scale = float(np.max(np.abs(M))) if n else 0.0
    tol = PIVOT_TOLERANCE * (scale if scale > 0.0 else 1.0)
    for k in range(n):
        p = k + int(np.argmax(np.abs(M[k:, k])))
        if abs(M[p, k]) <= tol:
            raise SingularSystemError(
                f"pivô nulo na coluna {k} (|pivô| = {abs(M[p, k]):.3e} <= {tol:.3e}); "
                f"verifique nós flutuantes ou laço de fontes/chaves ideais"
            )
        if p != k:
            M[[k, p], :] = M[[p, k], :]
            piv[[k, p]] = piv[[p, k]]
        if k + 1 < n:
            M[k + 1 :, k] /= M[k, k]
            M[k + 1 :, k + 1 :] -= np.outer(M[k + 1 :, k], M[k, k + 1 :])
    return M, piv


def lu_solve(LU: np.ndarray, piv: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Resolve ``A·x = b`` a partir de ``(LU, piv)`` de :func:`lu_factor`.

    Substituição direta em ``L`` (diagonal unitária) seguida de
    substituição regressiva em ``U``. Complexidade ``O(n²)``.
    """
    n = LU.shape[0]
    x = np.array(b, dtype=float, copy=True)[piv]
    for k in range(n - 1):
        x[k + 1 :] -= LU[k + 1 :, k] * x[k]
    for k in range(n - 1, -1, -1):
        if k + 1 < n:
            x[k] -= float(LU[k, k + 1 :] @ x[k + 1 :])
        x[k] /= LU[k, k]
    return x


class _Factorization:
    """Fatoração de uma topologia, com os dois caminhos de aplicação.

    Guarda a fatoração LU (referência auditável e caminho preciso) e a
    inversa (caminho rápido, um produto matriz-vetor em BLAS). A
    escolha entre os dois é feita uma única vez, por estimativa de
    condicionamento em norma 1 — ``κ₁(A) ≈ ‖A‖₁·‖A⁻¹‖₁`` — e vale para
    todos os passos que reutilizarem esta topologia.
    """

    __slots__ = ("lu", "piv", "inverse", "condition_estimate", "use_inverse")

    def __init__(self, A: np.ndarray, strategy: str) -> None:
        self.lu, self.piv = lu_factor(A)
        self.inverse: np.ndarray | None = None
        self.condition_estimate: float = float("nan")
        self.use_inverse: bool = False
        if strategy == "lu":
            return
        inv = np.linalg.inv(A)
        self.condition_estimate = float(
            np.linalg.norm(A, 1) * np.linalg.norm(inv, 1)
        )
        if strategy == "inverse" or self.condition_estimate <= INVERSE_CONDITION_LIMIT:
            self.inverse = inv
            self.use_inverse = True

    def apply(self, b: np.ndarray) -> np.ndarray:
        """Resolve ``A·x = b`` pelo caminho escolhido para esta topologia."""
        if self.use_inverse and self.inverse is not None:
            return self.inverse @ b
        return lu_solve(self.lu, self.piv, b)


# ---------------------------------------------------------------------------
# Circuito
# ---------------------------------------------------------------------------


class Circuit:
    """Coleção de ramos, numeração de nós e montagem da matriz MNA.

    O nó de referência é reconhecido pelos nomes de
    :data:`app.simulation.emt.components.GROUND_NAMES` (``"gnd"``,
    ``"0"``, ``"GND"``, ``"ground"``, ``"terra"``) e recebe o índice
    sentinela ``-1``; sua equação de KCL é eliminada do sistema, o que
    fixa o potencial de referência e torna ``A`` não singular.

    Os nós recebem índices na ORDEM DE PRIMEIRA APARIÇÃO entre os
    componentes adicionados — numeração determinística e reproduzível.
    """

    def __init__(self, name: str = "circuito") -> None:
        self.name: str = str(name)
        self._components: list[Component] = []
        self._names: set[str] = set()
        self._node_index: dict[str, int] = {}
        self._dimension: int = 0
        self._n_nodes: int = 0
        self._built: bool = False

    # -- construção ---------------------------------------------------------

    def add(self, component: Component) -> Component:
        """Adiciona um ramo ao circuito e o devolve (encadeamento fluente)."""
        if not isinstance(component, Component):
            raise ValueError(
                f"esperado Component, obtido {type(component).__name__}"
            )
        if component.name in self._names:
            raise ValueError(f"já existe um componente chamado {component.name!r}")
        self._names.add(component.name)
        self._components.append(component)
        self._built = False
        return component

    def extend(self, components: Iterable[Component]) -> list[Component]:
        """Adiciona vários ramos de uma vez."""
        return [self.add(c) for c in components]

    def get(self, name: str) -> Component:
        """Recupera um ramo por nome."""
        for c in self._components:
            if c.name == name:
                return c
        raise ValueError(f"componente {name!r} não encontrado no circuito")

    # -- consulta -----------------------------------------------------------

    @property
    def components(self) -> tuple[Component, ...]:
        """Ramos do circuito, na ordem de inserção."""
        return tuple(self._components)

    @property
    def switches(self) -> tuple[Switch, ...]:
        """Chaves do circuito, na ordem de inserção."""
        return tuple(c for c in self._components if isinstance(c, Switch))

    @property
    def node_index(self) -> dict[str, int]:
        """Mapa ``nome do nó → índice na matriz`` (terra ausente)."""
        if not self._built:
            raise ValueError("chame Circuit.build() antes de consultar node_index")
        return dict(self._node_index)

    @property
    def dimension(self) -> int:
        """Dimensão do sistema MNA (nós + incógnitas de corrente)."""
        if not self._built:
            raise ValueError("chame Circuit.build() antes de consultar dimension")
        return self._dimension

    @property
    def n_nodes(self) -> int:
        """Número de nós excluída a terra."""
        if not self._built:
            raise ValueError("chame Circuit.build() antes de consultar n_nodes")
        return self._n_nodes

    @property
    def is_built(self) -> bool:
        """``True`` se :meth:`build` já foi executado após a última alteração."""
        return self._built

    # -- montagem -----------------------------------------------------------

    def build(self) -> int:
        """Numera nós, reserva incógnitas MNA e devolve a dimensão do sistema.

        Raises
        ------
        ValueError
            Circuito vazio, sem nó de referência, ou com nó referenciado
            por um único ramo sem caminho para a terra (detectado apenas
            na fatoração, como :class:`SingularSystemError`).
        """
        if not self._components:
            raise ValueError("circuito vazio: adicione ao menos um componente")
        node_index: dict[str, int] = {}
        has_ground = False
        for comp in self._components:
            for node in comp.nodes:
                if is_ground(node):
                    has_ground = True
                    continue
                if node not in node_index:
                    node_index[node] = len(node_index)
        if not has_ground:
            raise ValueError(
                "circuito sem nó de referência: use um dos nomes "
                f"{sorted(GROUND_NAMES_TUPLE)} em algum terminal"
            )
        if not node_index:
            raise ValueError("circuito sem nós além da terra")
        offset = len(node_index)
        for comp in self._components:
            offset += comp.bind(node_index, offset)
        self._node_index = node_index
        self._n_nodes = len(node_index)
        self._dimension = offset
        self._built = True
        return self._dimension

    def prepare(self, dt: float) -> None:
        """Pré-computa as condutâncias companheiras de todos os ramos."""
        if not self._built:
            self.build()
        for comp in self._components:
            comp.prepare(dt)

    def reset(self) -> None:
        """Zera o histórico de todos os ramos (condições iniciais impostas)."""
        for comp in self._components:
            comp.reset()

    def topology_signature(self) -> tuple:
        """Assinatura da topologia corrente (estado de todas as chaves)."""
        return tuple(
            (c.name, c.topology_signature())
            for c in self._components
            if c.topology_signature() is not None
        )

    def assemble_matrix(self) -> np.ndarray:
        """Monta e devolve a matriz MNA ``A`` da topologia corrente."""
        if not self._built:
            raise ValueError("chame Circuit.build() antes de assemble_matrix()")
        A = np.zeros((self._dimension, self._dimension), dtype=float)
        for comp in self._components:
            comp.stamp_matrix(A)
        return A

    def assemble_rhs(self, t: float, mode: str = MODE_TRAPEZOIDAL) -> np.ndarray:
        """Monta e devolve o vetor independente ``b(t)`` do passo."""
        if not self._built:
            raise ValueError("chame Circuit.build() antes de assemble_rhs()")
        if mode not in (MODE_TRAPEZOIDAL, MODE_BACKWARD_EULER_HALF):
            raise ValueError(f"modo de integração inválido: {mode!r}")
        b = np.zeros(self._dimension, dtype=float)
        for comp in self._components:
            comp.stamp_rhs(b, t, mode)
        return b


# Tupla auxiliar só para a mensagem de erro de build() (evita import circular
# de nomes na f-string).
GROUND_NAMES_TUPLE: tuple[str, ...] = ("0", "GND", "gnd", "ground", "terra")


# ---------------------------------------------------------------------------
# Controladores
# ---------------------------------------------------------------------------

#: Um controlador é qualquer chamável ``f(t, solver) -> None`` executado
#: ANTES de cada passo. Pode ler correntes/tensões de ramo e comandar
#: chaves. Mudanças de estado são detectadas automaticamente pelo solver.
Controller = Callable[[float, "Solver"], None]


class TimedSwitchController:
    """Controlador de chave por tempo absoluto, com margem de corrente.

    Critério de comutação [LISTA: 02, §1.3], que reproduz a semântica do
    cartão de chave do ATP:

    * **Fechamento** comandado em ``t0`` é INSTANTÂNEO, valendo para
      todo passo com ``t >= close_time_s``.
    * **Abertura** comandada em ``t0`` só se efetiva a partir do primeiro
      instante ``t >= open_time_s`` em que a corrente na chave se anula
      ou cai abaixo do limiar ``|I_mar|`` — o campo *current margin*
      (colunas 35-44) do cartão de chave do ATP. É esse campo, e só ele,
      que representa o corte de corrente do disjuntor a vácuo: "sem o
      campo Imar o ATP esperaria um zero natural de corrente e a
      sobretensão praticamente desapareceria" [LISTA: 02, §3.6].

    ``current_margin_A = None`` (padrão) delega o valor ao campo
    :attr:`Switch.current_margin_A` da própria chave; se este também for
    ``None``, mantém-se a ABERTURA FORÇADA — a chave abre no primeiro
    passo com ``t >= open_time_s``, independentemente da corrente. É o
    comportamento de um interruptor ideal comandado, útil em ensaio
    numérico, mas NÃO é o de um disjuntor: quem quiser o critério físico
    deve informar ``I_mar`` (ou usar o polo de VCB de
    :mod:`app.simulation.emt.vcb`, que implementa o mesmo critério com
    corrente de *chopping* amostrada). O instante em que a abertura
    efetivamente ocorre fica registrado em
    :attr:`effective_open_time_s`.

    Convenção do instante de comutação. O controlador é chamado com o
    instante JÁ resolvido; a mudança de estado, portanto, só se reflete
    na solução do passo SEGUINTE. É deliberadamente a convenção do ATP,
    que "avalia o estado das chaves antes de resolver cada passo, usando
    o instante anterior" — e que, conforme [LISTA: 02, §2.7 e Tabela 1],
    reduz o desvio contra o ATP de 4,11·10⁻³ A para 1,21·10⁻⁵ A no
    circuito de referência da Questão 1.

    Como o passo é fixo, o instante efetivo de manobra é quantizado em
    ``Δt`` — limitação declarada ``emt_switching_quantized_to_step``.
    [LISTA: 02, Tabela 4] mede o efeito no caso de referência: com
    ``Δt = 1 µs`` o corte atrasa 1,578 µs e o pico da TRV cai de
    506,17 V (analítico) para 504,29 V.
    """

    def __init__(
        self,
        switch: Switch,
        *,
        close_time_s: float | None = None,
        open_time_s: float | None = None,
        current_margin_A: float | None = None,
    ) -> None:
        if not isinstance(switch, Switch):
            raise ValueError("TimedSwitchController exige um componente Switch")
        if close_time_s is not None and not math.isfinite(float(close_time_s)):
            raise ValueError("close_time_s deve ser finito ou None")
        if open_time_s is not None and not math.isfinite(float(open_time_s)):
            raise ValueError("open_time_s deve ser finito ou None")
        if current_margin_A is not None:
            margin = float(current_margin_A)
            if not math.isfinite(margin) or margin < 0.0:
                raise ValueError(
                    f"current_margin_A deve ser finita e >= 0, obtida {current_margin_A!r}"
                )
        else:
            margin = None
        self.switch = switch
        self.close_time_s = None if close_time_s is None else float(close_time_s)
        self.open_time_s = None if open_time_s is None else float(open_time_s)
        self.current_margin_A = margin
        #: Instante em que a abertura comandada EFETIVAMENTE ocorreu [s],
        #: ou ``None``. Com ``I_mar`` ele é posterior a ``open_time_s`` —
        #: é o ``t_c`` de [LISTA: 02, §3.4 e Tabela 4].
        self.effective_open_time_s: float | None = None
        self._last_t: float = -1.0

    @property
    def margin_in_force_A(self) -> float | None:
        """``I_mar`` efetivamente aplicado [A], ou ``None`` (abertura forçada).

        O valor do controlador tem precedência; ``None`` recai sobre o
        campo :attr:`Switch.current_margin_A` da própria chave, que é
        onde o cartão do ATP guardaria o dado.
        """
        if self.current_margin_A is not None:
            return self.current_margin_A
        return self.switch.current_margin_A

    def reset(self) -> None:
        """Reinicia a memória de instante efetivo de abertura."""
        self.effective_open_time_s = None
        self._last_t = -1.0

    def __call__(self, t: float, solver: "Solver") -> None:
        t_f = float(t)
        if self._last_t >= 0.0 and t_f < self._last_t:
            # Nova execução do solver: o relógio retrocedeu.
            self.reset()
        self._last_t = t_f
        if self.close_time_s is not None and t_f >= self.close_time_s:
            if self.open_time_s is None or t_f < self.open_time_s:
                self.switch.set_state(True)
        if self.open_time_s is not None and t_f >= self.open_time_s:
            # [LISTA: 02, §1.3]: comandada a abertura, ela só se efetiva no
            # primeiro passo em que |i_sw| <= I_mar (campo Imar do ATP).
            margin = self.margin_in_force_A
            if margin is None:
                interrupted = True
                self.switch.set_state(False)
            else:
                interrupted = (
                    abs(float(self.switch.branch_current(0))) <= margin
                )
                if interrupted:
                    self.switch.set_state(False)
            if interrupted and self.effective_open_time_s is None:
                self.effective_open_time_s = t_f


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------


@dataclass
class SolverResult:
    """Estatísticas e base de tempo de uma execução.

    Attributes
    ----------
    time_s:
        Instantes registrados [s], estritamente crescentes.
    steps:
        Passos completos de ``Δt`` executados.
    topology_changes:
        Número de mudanças de estado de chave detectadas.
    cda_events:
        Número de passos completos executados em modo CDA (dois
        meios-passos de Euler regressivo).
    factorizations:
        Fatorações LU efetivamente calculadas.
    cache_hits:
        Vezes em que a fatoração foi reaproveitada do cache.
    wall_time_s:
        Tempo de parede da execução [s] — medida de desempenho, não
        determinística; NÃO deve ser usada em asserção de teste.
    """

    time_s: np.ndarray = field(default_factory=lambda: np.zeros(0))
    steps: int = 0
    topology_changes: int = 0
    cda_events: int = 0
    factorizations: int = 0
    cache_hits: int = 0
    wall_time_s: float = 0.0


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------


class Solver:
    """Laço de marcha no tempo de Dommel com passo fixo e CDA.

    Parameters
    ----------
    circuit:
        Circuito já montado ou montável.
    dt:
        Passo de integração [s], > 0.
    cda_enabled:
        Aplica o amortecimento crítico após cada mudança de topologia
        (padrão ``True``). ``False`` reproduz o artefato numérico
        trapezoidal e emite ``WARNING`` — uso exclusivamente
        demonstrativo.
    cda_full_steps:
        Quantidade de passos completos substituídos por pares de
        meios-passos de Euler regressivo após cada evento. O padrão 1 —
        isto é, UM par, ou DOIS meios-passos de ``Δt/2`` — é o
        procedimento publicado: "a rede é resolvida uma segunda vez com
        a regra de Euler regressivo usando passo ``Δt/2``, isto é, em
        ``t₂ = (t₁ + Δt/2) + Δt/2``. Em seguida a simulação continua
        normalmente com a regra trapezoidal" [FONTE: Lin & Martí 1990,
        §2, p. 394]. Valores maiores que 1 NÃO têm respaldo na fonte
        [HIPÓTESE]: a única situação em que ela prevê meios-passos
        adicionais é a mudança de segmento de uma indutância linear por
        partes detectada logo após o primeiro meio-passo, caso em que
        são feitos TRÊS meios-passos adicionais — número ímpar,
        justamente para recair sobre a malha uniforme de ``Δt``
        [FONTE: Lin & Martí 1990, §4, p. 395]. Esse elemento não existe
        neste kernel. Mantenha 1 salvo em ensaio numérico declarado.
    record_half_steps:
        Registra também a amostra INTERMEDIÁRIA do par de meios-passos
        do CDA (padrão ``False``, que é o correto). A fonte é explícita:
        "os resultados em ``t₁ + Δt/2`` são apenas quantidades
        matemáticas usadas pelo procedimento CDA, sem significado
        físico" [FONTE: Lin & Martí 1990, §2, p. 394] — são o ponto
        intermediário de um amortecimento deliberado, não a forma de
        onda da rede. Ativar esta opção injeta esse ponto na série de
        saída e, portanto, no vetor de estresse ``s_{m,j}``; use-a
        apenas em ensaio numérico, e nunca para "capturar o pico" da
        TRV. Para resolver melhor o pico o caminho legítimo é REDUZIR
        ``Δt``: [LISTA: 02, Tabela 4] mostra o pico convergindo
        monotonicamente para o valor analítico (501,37 V em 4 µs;
        504,29 V em 1 µs; 505,84 V em 0,25 µs; 506,17 V analítico).
        A base de tempo também deixa de ser uniforme, o que
        ``extract_stress_events`` aceita mas sinaliza em
        ``StressProfile.warnings``. Emite ``WARNING`` quando ativada.
    init:
        Estado inicial da marcha. ``"zero"`` (padrão) parte do REPOUSO —
        históricos nulos, salvo condição inicial explícita nos ramos.
        ``"steady_state"`` resolve o circuito por transformação fasorial
        na topologia CORRENTE das chaves e semeia os históricos por
        ``I_L(0) = i_L(0) + G_L·v_L(0)`` e
        ``I_C(0) = −[G_C·v_C(0) + i_C(0)]`` [LISTA: 02, §1.4 e eq. (6)],
        preenchendo também o histórico de trânsito das linhas de
        Bergeron com a onda de regime. É o equivalente do ``TSTART``
        negativo do cartão de fonte do ATP. Nesse modo o paliativo de
        meios-passos na PARTIDA é desligado automaticamente (não há
        descontinuidade em ``t = 0``); o CDA das manobras permanece
        ativo, que é outra coisa. Ver
        :mod:`app.simulation.emt.steady_state`.
    init_frequency_Hz:
        Frequência imposta à solução fasorial [Hz]. ``None`` (padrão)
        detecta a frequência das fontes; havendo mais de uma, é erro
        (:class:`MultipleFrequenciesError`).
    cda_at_start:
        Aplica o CDA também no primeiro passo. ``None`` (padrão)
        RESOLVE pelo modo de partida: ``True`` com ``init="zero"``,
        ``False`` com ``init="steady_state"``. A fonte
        lista entre as descontinuidades os "saltos no valor das fontes
        aplicadas (inclusive em ``t = 0``)" [FONTE: Lin & Martí 1990,
        §2, p. 394], e é o caso quando a simulação parte do REPOUSO com
        fonte já em valor não nulo. Deve ser ``False`` quando a partida
        for em REGIME PERMANENTE, com os históricos semeados por
        ``I_L(0) = i_L(0) + G_L·v_L(0)`` e
        ``I_C(0) = −[G_C·v_C(0) + i_C(0)]`` [LISTA: 02, eq. (6)]: nesse
        caso não há descontinuidade em ``t = 0``, e os dois meios-passos
        de Euler regressivo introduziriam amortecimento numérico onde a
        marcha trapezoidal reproduz a solução fasorial desde o primeiro
        passo — desvio de 1,39·10⁻¹⁰ V no circuito de referência
        [LISTA: 02, §3.7 e Tabela 3].
    solve_strategy:
        ``"auto"`` (padrão) aplica a solução pela inversa cacheada e
        recai automaticamente na substituição LU quando o
        condicionamento estimado excede
        :data:`INVERSE_CONDITION_LIMIT` (com ``WARNING`` em log);
        ``"inverse"`` força a inversa; ``"lu"`` força a substituição
        direta/regressiva, que é a mais precisa e a de auditoria.
    use_cached_factorization:
        Ativa o cache ``assinatura de topologia → fatoração``
        (padrão ``True``). ``False`` refatora a cada mudança —
        usado para comprovar equivalência numérica nos testes.
    cache_size:
        Número máximo de fatorações retidas (descarte LRU).

    Notes
    -----
    Com ``init="zero"`` (padrão) o estado inicial é o repouso — todas as
    correntes de indutor e tensões de capacitor nulas, salvo condição
    inicial explícita nos componentes. Com ``init="steady_state"`` a
    partida é a do regime permanente senoidal, resolvido por
    :func:`app.simulation.emt.steady_state.initialize_steady_state`, e a
    solução fasorial usada fica disponível em
    :attr:`Solver.steady_state_solution` para auditoria.

    Em nenhum dos dois modos se registra amostra em ``t = 0``: a
    primeira amostra da série é a de ``t = Δt``. Com
    ``init="steady_state"``, porém, o vetor de estado em ``t = 0`` é o do
    regime permanente, de modo que :meth:`node_voltage` e as leituras de
    ramo já valem o regime ANTES do primeiro passo — é sobre elas que os
    controladores decidem a manobra, inclusive pelo critério de margem
    de corrente ``Imar``.
    """

    def __init__(
        self,
        circuit: Circuit,
        *,
        dt: float,
        cda_enabled: bool = True,
        cda_full_steps: int = 1,
        record_half_steps: bool = False,
        cda_at_start: bool | None = None,
        init: str = INIT_ZERO,
        init_frequency_Hz: float | None = None,
        solve_strategy: str = "auto",
        use_cached_factorization: bool = True,
        cache_size: int = DEFAULT_FACTORIZATION_CACHE_SIZE,
    ) -> None:
        if not isinstance(circuit, Circuit):
            raise ValueError(f"esperado Circuit, obtido {type(circuit).__name__}")
        dt_f = float(dt)
        if not math.isfinite(dt_f) or dt_f <= 0.0:
            raise ValueError(f"dt deve ser finito e > 0, obtido {dt!r}")
        n_cda = int(cda_full_steps)
        if n_cda < 1:
            raise ValueError(f"cda_full_steps deve ser >= 1, obtido {cda_full_steps!r}")
        if int(cache_size) < 1:
            raise ValueError(f"cache_size deve ser >= 1, obtido {cache_size!r}")
        if str(solve_strategy) not in SOLVE_STRATEGIES:
            raise ValueError(
                f"solve_strategy deve ser um de {SOLVE_STRATEGIES}, "
                f"obtido {solve_strategy!r}"
            )
        init_mode = str(init)
        if init_mode not in INIT_MODES:
            raise ValueError(
                f"init deve ser um de {INIT_MODES}, obtido {init!r}"
            )
        if init_frequency_Hz is not None:
            f_init = float(init_frequency_Hz)
            if not math.isfinite(f_init) or f_init <= 0.0:
                raise ValueError(
                    f"init_frequency_Hz deve ser finita e > 0, obtida "
                    f"{init_frequency_Hz!r}"
                )

        self.circuit = circuit
        self.dt = dt_f
        self.cda_enabled = bool(cda_enabled)
        self.cda_full_steps = n_cda
        if n_cda > 1:
            log.warning(
                "cda_full_steps=%d em %r: o procedimento publicado prevê "
                "EXATAMENTE um par de meios-passos de Δt/2 por descontinuidade "
                "[Lin & Martí 1990, §2, p. 394]; valores maiores são extensão "
                "não publicada e introduzem amortecimento numérico adicional",
                n_cda,
                circuit.name,
            )
        self.record_half_steps = bool(record_half_steps)
        if self.record_half_steps:
            log.warning(
                "record_half_steps=True em %r: a amostra em t+Δt/2 é quantidade "
                "matemática do CDA, SEM significado físico [Lin & Martí 1990, "
                "§2, p. 394]; ela contaminará a série de saída e o vetor de "
                "estresse — para resolver o pico da TRV reduza Δt",
                circuit.name,
            )
        self.init = init_mode
        self.init_frequency_Hz = (
            None if init_frequency_Hz is None else float(init_frequency_Hz)
        )
        # Partida em regime permanente NÃO tem descontinuidade em t = 0:
        # os dois meios-passos de Euler regressivo introduziriam
        # amortecimento numérico onde a marcha trapezoidal já reproduz a
        # solução fasorial desde o primeiro passo [LISTA: 02, §1.4 e §3.7].
        # O CDA das MANOBRAS continua ativo — é outra coisa.
        if cda_at_start is None:
            self.cda_at_start = init_mode == INIT_ZERO
        else:
            self.cda_at_start = bool(cda_at_start)
            if self.cda_at_start and init_mode == INIT_STEADY_STATE:
                log.warning(
                    "cda_at_start=True com init='steady_state' em %r: não há "
                    "descontinuidade em t = 0 na partida em regime permanente, "
                    "e o par de meios-passos de Euler regressivo AMORTECE o "
                    "regime que acabou de ser semeado; o desvio contra a "
                    "solução fasorial deixa de ser da ordem de 1e-10 V "
                    "[LISTA: 02, Tabela 3]",
                    circuit.name,
                )
        self.solve_strategy = str(solve_strategy)
        self.use_cached_factorization = bool(use_cached_factorization)
        self.cache_size = int(cache_size)

        self._cache: dict[tuple, _Factorization] = {}
        self._cache_order: list[tuple] = []
        self._factorization: _Factorization | None = None
        self._signature: tuple | None = None
        self._x: np.ndarray = np.zeros(0)
        self._t: float = 0.0
        self._probes: list = []
        self._pending_cda: int = 0
        self._warned_no_cda: bool = False
        self._steady_state: "PhasorSolution | None" = None
        # Ramos não lineares tratados por COMPENSAÇÃO: ficam fora de [Y] e
        # entram por superposição depois da solução linear do passo
        # [FONTE: Dommel 1971, §V]. A descoberta é automática — o ramo se
        # declara por ``is_compensated()`` — para que a assinatura de
        # ``run`` não mude e circuitos sem não linearidade paguem apenas
        # um teste de lista vazia.
        from .nonlinear import CompensationNetwork, collect_compensated

        self._compensation = CompensationNetwork(
            collect_compensated(self.circuit.components)
        )

        self.stats = SolverResult()

        self.circuit.build()
        self.circuit.prepare(self.dt)

    # -- estado -------------------------------------------------------------

    @property
    def time_s(self) -> float:
        """Instante corrente da simulação [s]."""
        return self._t

    @property
    def state(self) -> np.ndarray:
        """Cópia do vetor solução ``x`` do último passo."""
        return self._x.copy()

    @property
    def matrix(self) -> np.ndarray:
        """Cópia da matriz MNA da topologia corrente (monta sob demanda)."""
        return self.circuit.assemble_matrix()

    @property
    def cache_entries(self) -> int:
        """Número de fatorações retidas no cache."""
        return len(self._cache)

    @property
    def steady_state_solution(self) -> "PhasorSolution | None":
        """Solução fasorial usada na partida, ou ``None``.

        Só é preenchida com ``init="steady_state"``, após a primeira
        chamada de :meth:`run` com ``reset=True``. Serve à auditoria:
        permite confrontar a marcha no tempo com o fasor que a semeou.
        """
        return self._steady_state

    def node_voltage(self, node: str) -> float:
        """Tensão do nó ``node`` no último passo resolvido [V]."""
        if is_ground(node):
            return 0.0
        idx = self.circuit.node_index.get(str(node))
        if idx is None:
            raise ValueError(f"nó {node!r} não existe no circuito")
        if self._x.size == 0:
            return 0.0
        return float(self._x[idx])

    # -- sondas -------------------------------------------------------------

    def add_probe(self, probe) -> object:
        """Registra uma sonda; devolve a própria sonda."""
        if not hasattr(probe, "record") or not hasattr(probe, "bind"):
            raise ValueError("a sonda deve expor os métodos bind() e record()")
        self._probes.append(probe)
        return probe

    @property
    def probes(self) -> tuple:
        """Sondas registradas, na ordem de inserção."""
        return tuple(self._probes)

    # -- fatoração ----------------------------------------------------------

    def _factorize(self, signature: tuple) -> None:
        """Obtém a fatoração da topologia, usando o cache quando possível."""
        if self.use_cached_factorization and signature in self._cache:
            self._factorization = self._cache[signature]
            self.stats.cache_hits += 1
            try:
                self._cache_order.remove(signature)
            except ValueError:  # pragma: no cover - defensivo
                pass
            self._cache_order.append(signature)
            self._signature = signature
            return
        A = self.circuit.assemble_matrix()
        fact = _Factorization(A, self.solve_strategy)
        if self.solve_strategy == "auto" and not fact.use_inverse:
            log.warning(
                "topologia %r com condicionamento estimado %.3e > %.1e: "
                "aplicação por inversa cacheada abandonada, fallback para "
                "substituição LU (mais precisa, mais lenta)",
                signature,
                fact.condition_estimate,
                INVERSE_CONDITION_LIMIT,
            )
        self.stats.factorizations += 1
        self._factorization = fact
        self._signature = signature
        if self.use_cached_factorization:
            self._cache[signature] = fact
            self._cache_order.append(signature)
            while len(self._cache_order) > self.cache_size:
                evicted = self._cache_order.pop(0)
                self._cache.pop(evicted, None)
                log.warning(
                    "cache de fatoração cheio (%d entradas): topologia %r "
                    "descartada e será refatorada se recorrer",
                    self.cache_size,
                    evicted,
                )

    def _solve(self, b: np.ndarray) -> np.ndarray:
        """Resolve o sistema do passo, com fallback registrado em log."""
        assert self._factorization is not None
        try:
            return self._factorization.apply(b)
        except (np.linalg.LinAlgError, FloatingPointError) as exc:  # pragma: no cover
            log.warning(
                "falha na substituição LU (%s); fallback para "
                "numpy.linalg.lstsq nesta iteração",
                exc,
            )
            A = self.circuit.assemble_matrix()
            x, *_ = np.linalg.lstsq(A, b, rcond=None)
            return x

    def _sync_topology(self) -> bool:
        """Refatora se a topologia mudou; devolve ``True`` se mudou."""
        signature = self.circuit.topology_signature()
        if signature == self._signature and self._factorization is not None:
            return False
        first = self._signature is None
        self._factorize(signature)
        # z_T e os vetores de superposição valem apenas para a topologia
        # em que foram computados: "the slope z_T remains unchanged as long
        # as no switchings take place in the network" [FONTE: Dommel 1971,
        # §V, p. 2563].
        self._compensation.invalidate()
        if not first:
            self.stats.topology_changes += 1
        return not first

    # -- passos -------------------------------------------------------------

    def _advance(self, t_target: float, mode: str) -> None:
        """Resolve um passo cujo instante de chegada é ``t_target``."""
        b = self.circuit.assemble_rhs(t_target, mode)
        x = self._solve(b)
        if len(self._compensation):
            # x é a solução SEM os ramos não lineares — o ``e⁽⁰⁾`` do
            # passo 1 de Dommel. A correção resolve as duas equações
            # escalares por ramo e superpõe [FONTE: Dommel 1971, eqs.
            # (4)-(6)].
            if not self._compensation.prepared:
                self._compensation.prepare(self.circuit.dimension, self._solve)
            x = self._compensation.correct(x, t_target)
        for comp in self.circuit.components:
            comp.commit(x, t_target, mode)
        self._x = x
        self._t = t_target

    def _record(self) -> None:
        for probe in self._probes:
            probe.record(self._t, self._x, self)

    # -- execução -----------------------------------------------------------

    def run(
        self,
        t_end: float,
        dt: float | None = None,
        controllers: Sequence[Controller] = (),
        *,
        on_step: Callable[[float, np.ndarray, "Solver"], None] | None = None,
        reset: bool = True,
    ) -> SolverResult:
        """Executa a simulação de ``0`` a ``t_end``.

        Parameters
        ----------
        t_end:
            Instante final [s], > 0.
        dt:
            Passo [s]. ``None`` (padrão) usa o ``dt`` do construtor.
            Trocar ``dt`` reinicia obrigatoriamente o estado — os termos
            de histórico trapezoidais não são convertíveis entre passos.
        controllers:
            Chamáveis ``f(t, solver)`` executados ANTES de cada passo,
            com ``t`` o instante JÁ resolvido (início do passo). Podem
            comandar chaves; mudanças de topologia são detectadas e
            disparam refatoração e CDA.
        on_step:
            Callback ``f(t, x, solver)`` chamado após cada passo
            completo (nunca nos meios-passos internos do CDA).
        reset:
            Zera o histórico antes de iniciar (padrão ``True``).

        Returns
        -------
        SolverResult
            Base de tempo registrada e estatísticas da execução.

        Raises
        ------
        ValueError
            ``t_end <= 0``, ``dt`` inválido ou controlador não chamável.
        """
        t_end_f = float(t_end)
        if not math.isfinite(t_end_f) or t_end_f <= 0.0:
            raise ValueError(f"t_end deve ser finito e > 0, obtido {t_end!r}")
        if dt is not None:
            dt_f = float(dt)
            if not math.isfinite(dt_f) or dt_f <= 0.0:
                raise ValueError(f"dt deve ser finito e > 0, obtido {dt!r}")
            if dt_f != self.dt:
                self.dt = dt_f
                self.circuit.prepare(self.dt)
                self._cache.clear()
                self._cache_order.clear()
                self._factorization = None
                self._signature = None
        if t_end_f < self.dt:
            raise ValueError(
                f"t_end ({t_end_f:.6g} s) menor que o passo dt ({self.dt:.6g} s)"
            )
        ctrls = tuple(controllers or ())
        for c in ctrls:
            if not callable(c):
                raise ValueError(f"controlador não chamável: {c!r}")

        if not self.cda_enabled and not self._warned_no_cda:
            self._warned_no_cda = True
            log.warning(
                "CDA DESLIGADO em %r: a regra trapezoidal produzirá oscilação "
                "numérica de período 2·Δt na interrupção de correntes indutivas. "
                "Resultados de V_pk e dv/dt NÃO são válidos para estudo de "
                "isolamento — use cda_enabled=True",
                self.circuit.name,
            )

        if reset:
            self.circuit.reset()
            for probe in self._probes:
                probe.reset()
            self._t = 0.0
            self._x = np.zeros(self.circuit.dimension)
            self.stats = SolverResult()
            self._pending_cda = 0
            self._signature = None
            self._factorization = None
            if self.init == INIT_STEADY_STATE:
                # Solução fasorial na topologia CORRENTE das chaves e
                # semeadura dos históricos [LISTA: 02, §1.4, eq. (6)] —
                # o equivalente do TSTART negativo do cartão de fonte do
                # ATP. O estado em t = 0 passa a ser o do regime, de modo
                # que os controladores já leem correntes de regime no
                # primeiro passo (critério Imar inclusive).
                self._steady_state = initialize_steady_state(
                    self.circuit, self.dt, frequency_Hz=self.init_frequency_Hz
                )
                self._x = self._steady_state.state_at(0.0)
        for probe in self._probes:
            probe.bind(self.circuit)

        wall0 = time.perf_counter()
        self._sync_topology()
        # Primeiro passo em CDA. A fonte inclui explicitamente entre as
        # descontinuidades que disparam o CDA os "saltos no valor das fontes
        # aplicadas (inclusive em t = 0)" [FONTE: Lin & Martí 1990, §2,
        # p. 394]. Aqui a razão é a mesma vista pelo lado do histórico: os
        # termos partem de zero e, na regra trapezoidal, o termo do capacitor
        # usa i(t−Δt) — que não é conhecido em t = 0 e é INCONSISTENTE com a
        # rede (o capacitor descarregado conduz i = v_fonte/R no instante
        # inicial). O Euler regressivo não usa i(t−h) no capacitor, de modo
        # que dois meios-passos bastam para estabelecer histórico
        # consistente. Sem isso o erro global do degrau degenera de O(Δt²)
        # para O(Δt).
        # [CÁLCULO PRÓPRIO: ver tests/test_emt_kernel.py, convergência.]
        # Na partida em REGIME PERMANENTE não há descontinuidade em t = 0 e
        # o CDA inicial é indevido — use cda_at_start=False [LISTA: 02, §1.4
        # e eq. (6)].
        if self.cda_enabled and self.cda_at_start:
            self._pending_cda = self.cda_full_steps
        # NÃO se registra amostra em t = 0, nos DOIS modos de partida, para
        # que a base de tempo seja a mesma e as séries sejam comparáveis.
        # Com init='zero' a amostra em t = 0 seria o vetor nulo, FALSA em
        # séries com condição inicial não nula; com init='steady_state' ela
        # existe e é válida (self._x já é o regime), mas registrá-la
        # mudaria o comprimento das séries conforme o modo — cf.
        # KNOWN_LIMITATIONS ``emt_steady_state_residual_deviation``.
        times: list[float] = []

        # Base de tempo por ÍNDICE, não por acumulação. Somar Δt ao
        # relógio a cada passo faz o erro de arredondamento crescer com o
        # número de passos: em 1600 passos de 50 µs a marcha acumulada
        # chega a t = 0,079999999999999 s, ABAIXO do 0,08 s exato, o que
        # desloca de um passo qualquer comparação contra uma malha exata
        # — a do ATP, que imprime n·Δt, e a das rotinas de referência do
        # autor, que constroem t = (0:N−1)·Δt [LISTA: 01, Apêndice A;
        # LISTA: 02, Apêndice A]. Reconstruir t_n = t_origem + n·Δt
        # mantém o erro no nível do arredondamento de UMA operação,
        # independentemente da duração da simulação.
        # [REPO: tests/test_emt_referencia_eee873.py, marcha temporal]
        t_origin = self._t
        n_steps = int(math.floor((t_end_f + 0.5 * self.dt) / self.dt))
        for k_step in range(n_steps):
            for ctrl in ctrls:
                ctrl(self._t, self)
            if self._sync_topology():
                self._pending_cda = self.cda_full_steps if self.cda_enabled else 0
            t0 = t_origin + k_step * self.dt
            t1 = t_origin + (k_step + 1) * self.dt
            if self._pending_cda > 0:
                # DOIS meios-passos de Euler regressivo com h = Δt/2, o
                # primeiro em t0 + Δt/2 e o segundo em t0 + Δt, de modo que a
                # marcha recai sobre a malha uniforme [FONTE: Lin & Martí
                # 1990, §2, p. 394, itens 4-5]. Os controladores NÃO são
                # chamados entre os dois: a amostra intermediária não tem
                # significado físico e não pode decidir manobra (mesma fonte).
                self._advance(0.5 * (t0 + t1), MODE_BACKWARD_EULER_HALF)
                if self.record_half_steps:
                    times.append(self._t)
                    self._record()
                self._advance(t1, MODE_BACKWARD_EULER_HALF)
                self._pending_cda -= 1
                self.stats.cda_events += 1
            else:
                self._advance(t1, MODE_TRAPEZOIDAL)
            self.stats.steps += 1
            times.append(self._t)
            self._record()
            if on_step is not None:
                on_step(self._t, self._x, self)

        self.stats.wall_time_s = time.perf_counter() - wall0
        self.stats.time_s = np.asarray(times, dtype=float)
        return self.stats


__all__ = [
    "PIVOT_TOLERANCE",
    "DEFAULT_FACTORIZATION_CACHE_SIZE",
    "SingularSystemError",
    "INVERSE_CONDITION_LIMIT",
    "SOLVE_STRATEGIES",
    "lu_factor",
    "lu_solve",
    "Circuit",
    "Controller",
    "TimedSwitchController",
    "Solver",
    "SolverResult",
]
