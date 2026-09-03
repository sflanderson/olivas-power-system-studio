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

Fatoração LU com cache
=======================

``scipy`` não é dependência declarada do projeto (política de
dependências §4.7 do mapa de convenções). Usa-se portanto uma
fatoração LU de Doolittle com pivotamento parcial escrita sobre
``numpy`` (operações de linha vetorizadas, atualização de posto 1 por
``np.outer``). Motivo de NÃO usar ``numpy.linalg.solve`` no laço:
``solve`` refatora a matriz a cada chamada (custo ``O(n³)``), enquanto
o par ``_lu_factor`` / ``_lu_solve`` paga ``O(n³)`` uma única vez por
TOPOLOGIA e ``O(n²)`` por passo. Numa sequência de reignições de VCB a
mesma topologia recorre milhares de vezes, de modo que o cache
``assinatura → (LU, piv)`` elimina praticamente toda a refatoração.
``numpy.linalg.inv`` foi descartada por ser numericamente inferior à
substituição direta/regressiva para a mesma finalidade.

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
        que é o do ATP).
    use_cached_factorization:
        Ativa o cache ``assinatura de topologia → (LU, piv)``
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

        self.circuit = circuit
        self.dt = dt_f
        self.cda_enabled = bool(cda_enabled)
        self.cda_full_steps = n_cda
        self.use_cached_factorization = bool(use_cached_factorization)
        self.cache_size = int(cache_size)

        self._cache: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
        self._cache_order: list[tuple] = []
        self._lu: np.ndarray | None = None
        self._piv: np.ndarray | None = None
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
        """Obtém ``(LU, piv)`` da topologia, usando o cache quando possível."""
        if self.use_cached_factorization and signature in self._cache:
            self._lu, self._piv = self._cache[signature]
            self.stats.cache_hits += 1
            try:
                self._cache_order.remove(signature)
            except ValueError:  # pragma: no cover - defensivo
                pass
            self._cache_order.append(signature)
            self._signature = signature
            return
        A = self.circuit.assemble_matrix()
        lu, piv = lu_factor(A)
        self.stats.factorizations += 1
        self._lu, self._piv = lu, piv
        self._signature = signature
        if self.use_cached_factorization:
            self._cache[signature] = (lu, piv)
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
        assert self._lu is not None and self._piv is not None
        try:
            return lu_solve(self._lu, self._piv, b)
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
        if signature == self._signature and self._lu is not None:
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
                self._lu = None
                self._piv = None
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
            self._lu = None
            self._piv = None
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
        times: list[float] = [self._t]
        self._record()
        if on_step is not None:
            on_step(self._t, self._x, self)

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
    "lu_factor",
    "lu_solve",
    "Circuit",
    "Controller",
    "TimedSwitchController",
    "Solver",
    "SolverResult",
]
