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

[LITERATURA: H. W. Dommel, "Digital Computer Solution of
Electromagnetic Transients in Single- and Multiphase Networks", *IEEE
Trans. PAS*, vol. PAS-88, n. 4, pp. 388-399, 1969.]
[LITERATURA: J. A. Martinez-Velasco (ed.), *Transient Analysis of
Power Systems: Solution Techniques, Tools and Applications*, Wiley/IEEE
Press, 2015, cap. 2.]

Amortecimento crítico (CDA)
============================

Após CADA mudança de topologia (abertura ou fechamento de chave), o
passo seguinte de ``Δt`` é substituído por DOIS meios-passos de Euler
regressivo de ``Δt/2``, como faz o ATP [LITERATURA: J. R. Marti e J.
Lin, "Suppression of numerical oscillations in the EMTP", *IEEE Trans.
Power Systems*, vol. 4, n. 2, pp. 739-747, 1989].

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
    """Controlador de chave por tempo absoluto.

    A chave é fechada no primeiro passo com ``t >= close_time_s`` e
    aberta no primeiro passo com ``t >= open_time_s``. Como o passo é
    fixo, o instante efetivo de manobra é quantizado em ``Δt`` —
    limitação declarada ``emt_switching_quantized_to_step``.
    """

    def __init__(
        self,
        switch: Switch,
        *,
        close_time_s: float | None = None,
        open_time_s: float | None = None,
    ) -> None:
        if not isinstance(switch, Switch):
            raise ValueError("TimedSwitchController exige um componente Switch")
        if close_time_s is not None and not math.isfinite(float(close_time_s)):
            raise ValueError("close_time_s deve ser finito ou None")
        if open_time_s is not None and not math.isfinite(float(open_time_s)):
            raise ValueError("open_time_s deve ser finito ou None")
        self.switch = switch
        self.close_time_s = None if close_time_s is None else float(close_time_s)
        self.open_time_s = None if open_time_s is None else float(open_time_s)

    def __call__(self, t: float, solver: "Solver") -> None:
        if self.close_time_s is not None and t >= self.close_time_s:
            if self.open_time_s is None or t < self.open_time_s:
                self.switch.set_state(True)
        if self.open_time_s is not None and t >= self.open_time_s:
            self.switch.set_state(False)


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
        meios-passos de Euler regressivo após cada evento (padrão 1,
        que é o do ATP). Em redes muito rígidas depois do evento — a
        constante de tempo residual muito menor que ``Δt`` — o valor 2
        elimina o resíduo que um único passo de CDA ainda deixa.
    record_half_steps:
        Registra também as amostras dos meios-passos do CDA (padrão
        ``False``). Ative quando o pico da grandeza de interesse puder
        cair DENTRO do par de meios-passos — é o caso do primeiro
        semiciclo da TRV logo após a interrupção. A base de tempo deixa
        de ser uniforme, o que ``extract_stress_events`` aceita mas
        sinaliza em ``StressProfile.warnings``.
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
    O estado inicial é o repouso (todas as correntes de indutor e
    tensões de capacitor nulas, salvo condição inicial explícita nos
    componentes). NÃO há inicialização fasorial em regime permanente —
    limitação declarada ``emt_no_steady_state_init``: simule uma janela
    de acomodação antes do evento de interesse.
    """

    def __init__(
        self,
        circuit: Circuit,
        *,
        dt: float,
        cda_enabled: bool = True,
        cda_full_steps: int = 1,
        record_half_steps: bool = False,
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

        self.circuit = circuit
        self.dt = dt_f
        self.cda_enabled = bool(cda_enabled)
        self.cda_full_steps = n_cda
        self.record_half_steps = bool(record_half_steps)
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
        if not first:
            self.stats.topology_changes += 1
        return not first

    # -- passos -------------------------------------------------------------

    def _advance(self, t_target: float, mode: str) -> None:
        """Resolve um passo cujo instante de chegada é ``t_target``."""
        b = self.circuit.assemble_rhs(t_target, mode)
        x = self._solve(b)
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
        for probe in self._probes:
            probe.bind(self.circuit)

        wall0 = time.perf_counter()
        self._sync_topology()
        # Primeiro passo em CDA: os termos de histórico partem de zero e,
        # na regra trapezoidal, o termo do capacitor usa i(t−Δt) — que não
        # é conhecido em t = 0 e é INCONSISTENTE com a rede (o capacitor
        # descarregado conduz i = v_fonte/R no instante inicial). O Euler
        # regressivo não usa i(t−h) no capacitor, de modo que dois
        # meios-passos bastam para estabelecer histórico consistente. Sem
        # isso o erro global do degrau degenera de O(Δt²) para O(Δt).
        # [CÁLCULO PRÓPRIO: ver tests/test_emt_kernel.py, convergência.]
        if self.cda_enabled:
            self._pending_cda = self.cda_full_steps
        # NÃO se registra amostra em t = 0: a solução nodal nesse
        # instante exigiria uma rodada de condições iniciais consistentes
        # (indutor como fonte de corrente i_L0, capacitor como fonte de
        # tensão v_C0), não implementada — cf. KNOWN_LIMITATIONS
        # ``emt_no_steady_state_init``. Registrar o vetor nulo produziria
        # uma amostra FALSA em séries com condição inicial não nula.
        times: list[float] = []

        n_steps = int(math.floor((t_end_f + 0.5 * self.dt) / self.dt))
        for _ in range(n_steps):
            for ctrl in ctrls:
                ctrl(self._t, self)
            if self._sync_topology():
                self._pending_cda = self.cda_full_steps if self.cda_enabled else 0
            t0 = self._t
            if self._pending_cda > 0:
                half = 0.5 * self.dt
                self._advance(t0 + half, MODE_BACKWARD_EULER_HALF)
                if self.record_half_steps:
                    times.append(self._t)
                    self._record()
                self._advance(t0 + 2.0 * half, MODE_BACKWARD_EULER_HALF)
                self._pending_cda -= 1
                self.stats.cda_events += 1
            else:
                self._advance(t0 + self.dt, MODE_TRAPEZOIDAL)
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
