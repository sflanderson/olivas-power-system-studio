"""
app.simulation.emt.nonlinear — elementos não lineares por COMPENSAÇÃO.

Por que compensação e não estampagem
=====================================

Um ramo não linear estampado em ``[Y]`` mudaria a matriz a cada mudança
de ponto de operação e exigiria refatoração a cada passo. O método de
compensação evita isso: o ramo é **excluído** de ``[Y]`` e substituído
por uma fonte de corrente cujo valor sai da interseção de duas equações
escalares [FONTE: Dommel 1971, §V, p. 2562].

Para um ramo entre os nós ``k`` e ``m``:

.. math::

   e_k(t) - e_m(t) = e^{(0)}_{km}(t) - z_T\\, i_{km}(t)
   \\qquad \\text{(equação da rede — eq. 4)}

.. math::

   e_k(t) - e_m(t) = f\\big(i_{km}(t)\\big)
   \\qquad \\text{(característica do ramo — eq. 5)}

onde ``e^{(0)}`` é a solução SEM o ramo e ``z_T`` é a impedância de
Thévenin vista pelos seus terminais. Achado ``i_{km}``, a solução final
sai por superposição [FONTE: Dommel 1971, eq. (6)]:

.. math::

   [e(t)] = [e^{(0)}(t)] - [z]\\, i_{km}(t).

Dommel é explícito quanto ao custo: *"the extra work of steps 2 and 3,
which is a result of the nonlinearity, is rather small compared to a
re-factorization of [Y]"* [FONTE: Dommel 1971, §V, p. 2562]. O exemplo
trabalhado do próprio artigo é exatamente o caso deste projeto — um
**para-raios** protegendo um transformador através de um cabo
[FONTE: Dommel 1971, Fig. 3 e Fig. 4, p. 2562-2563].

Representação da característica
================================

Ponto a ponto, por trechos lineares, como o programa da BPA: *"BPA's
transients program uses a point-by-point representation of the
nonlinearity as indicated in Fig. 2"*, com a busca da interseção partindo
*"at the location of the intersection in the preceding time step"*
[FONTE: Dommel 1971, §V, p. 2562-2563]. Dentro de um trecho a
característica é ``i = g·v + b`` e a interseção é a solução de um sistema
linear de ordem ``M`` (número de ramos compensados), não uma iteração de
Newton.

Convenção de sinal
===================

A do resto do pacote: ``v = v_k − v_m`` e ``i`` SAI do nó ``k`` pelo ramo.
A injeção equivalente no vetor independente é ``b[k] −= i`` e
``b[m] += i``, de modo que, com

.. math::

   w_j = [Y]^{-1}\\,(\\mathbf{e}_{m_j} - \\mathbf{e}_{k_j}),

vale ``x = x^{(0)} + \\sum_j i_j\\, w_j`` e
``z_{T}[l,j] = -\\big(w_j[k_l] - w_j[m_l]\\big)``. Para um resistor ``R``
isolado entre ``k`` e a terra a fórmula devolve ``z_T = R``, como deve
[CÁLCULO PRÓPRIO: verificado em ``tests/test_emt_nonlinear.py``].

Limitações
===========

Ver :data:`KNOWN_LIMITATIONS`.

Fontes
=======

* DOMMEL, H. W. Nonlinear and time-varying elements in digital simulation
  of electromagnetic transients. **IEEE Transactions on Power Apparatus
  and Systems**, v. PAS-90, n. 6, p. 2561-2567, 1971.
* TINNEY, W. F. Compensation methods for network solutions by optimally
  ordered triangular factorization. **IEEE Transactions on Power
  Apparatus and Systems**, v. PAS-91, p. 123-127, 1972 [referência 7 de
  Dommel 1971; não acessada].
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from app.core.logging_config import get_logger

from .components import GROUND_INDEX, Component, node_voltage

log = get_logger(__name__)


#: Tolerância relativa de fronteira na busca do trecho ativo. Um ponto de
#: operação que caia sobre um vértice da característica pertence ao trecho
#: em que a busca já estava, e não oscila entre os dois.
SEGMENT_TOLERANCE: float = 1.0e-9

#: Teto de trocas de trecho por passo antes de desistir e registrar. A
#: busca de Dommel caminha de um trecho para o vizinho; com característica
#: monótona ela converge em poucas trocas.
MAX_SEGMENT_ITERATIONS: int = 50


# ---------------------------------------------------------------------------
# Característica v-i por trechos
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PiecewiseLinearVI:
    """Característica ``i(v)`` monótona, ímpar e linear por trechos.

    Os pontos informados descrevem apenas o **primeiro quadrante**; o
    terceiro é o seu simétrico, que é a hipótese usual para para-raios e
    para resistores não lineares sem polaridade
    [FONTE: Dommel 1971, Fig. 2 — curva por pontos].

    Fora do último ponto a característica é EXTRAPOLADA com a inclinação
    do último trecho. É escolha deliberada e conservadora: extrapolar com
    a inclinação alta do trecho de alta corrente subestima a tensão
    residual, enquanto travar no último ponto a fixaria — o que
    esconderia uma solicitação acima da faixa caracterizada. A
    extrapolação é registrada em log na primeira ocorrência.

    Attributes
    ----------
    voltage_V:
        Tensões dos pontos [V], estritamente crescentes e > 0.
    current_A:
        Correntes dos pontos [A], estritamente crescentes e > 0.
    name:
        Rótulo para mensagens.
    """

    voltage_V: tuple[float, ...]
    current_A: tuple[float, ...]
    name: str = "vi"

    def __post_init__(self) -> None:
        v = np.asarray(self.voltage_V, dtype=float)
        i = np.asarray(self.current_A, dtype=float)
        if v.ndim != 1 or i.ndim != 1 or v.size != i.size:
            raise ValueError(
                f"{self.name!r}: voltage_V e current_A devem ser vetores do mesmo "
                f"tamanho, obtidos {v.shape} e {i.shape}"
            )
        if v.size < 2:
            raise ValueError(f"{self.name!r}: a característica exige ao menos 2 pontos")
        if not (np.all(np.isfinite(v)) and np.all(np.isfinite(i))):
            raise ValueError(f"{self.name!r}: pontos não finitos na característica")
        if np.any(v <= 0.0) or np.any(i <= 0.0):
            raise ValueError(
                f"{self.name!r}: os pontos descrevem o primeiro quadrante e devem "
                "ser estritamente positivos"
            )
        if np.any(np.diff(v) <= 0.0) or np.any(np.diff(i) <= 0.0):
            raise ValueError(
                f"{self.name!r}: a característica deve ser estritamente crescente "
                "nos dois eixos (monotonicidade é o que garante interseção única)"
            )
        object.__setattr__(self, "_v", v)
        object.__setattr__(self, "_i", i)
        # Trechos no eixo POSITIVO, mais o trecho central que atravessa a
        # origem por simetria ímpar: (-v1, -i1) → (v1, i1).
        g_central = float(i[0] / v[0])
        g = [g_central]
        b = [0.0]
        lo = [-float(v[0])]
        hi = [float(v[0])]
        for k in range(v.size - 1):
            gk = float((i[k + 1] - i[k]) / (v[k + 1] - v[k]))
            g.append(gk)
            b.append(float(i[k] - gk * v[k]))
            lo.append(float(v[k]))
            hi.append(float(v[k + 1]))
        object.__setattr__(self, "_g", np.asarray(g, dtype=float))
        object.__setattr__(self, "_b", np.asarray(b, dtype=float))
        object.__setattr__(self, "_lo", np.asarray(lo, dtype=float))
        object.__setattr__(self, "_hi", np.asarray(hi, dtype=float))

    @property
    def n_segments(self) -> int:
        """Número de trechos no semieixo positivo, incluindo o central."""
        return int(self._g.size)  # type: ignore[attr-defined]

    @property
    def knee_voltage_V(self) -> float:
        """Tensão do primeiro ponto informado [V] — o joelho da curva."""
        return float(self._v[0])  # type: ignore[attr-defined]

    @property
    def max_point(self) -> tuple[float, float]:
        """Último ponto ``(v, i)`` caracterizado [V, A]."""
        return float(self._v[-1]), float(self._i[-1])  # type: ignore[attr-defined]

    def segment_index(self, v_V: float) -> int:
        """Índice do trecho que contém ``|v|``, com extrapolação no topo."""
        a = abs(float(v_V))
        hi = self._hi  # type: ignore[attr-defined]
        k = int(np.searchsorted(hi, a, side="left"))
        return min(k, int(hi.size) - 1)

    def segment(self, index: int) -> tuple[float, float, float, float]:
        """``(g, b, v_min, v_max)`` do trecho ``index`` no semieixo positivo.

        ``i = g·v + b`` vale para ``v`` no intervalo devolvido; para ``v``
        negativo aplica-se a simetria ímpar, tratada por
        :meth:`linearize`.
        """
        k = int(index)
        if not (0 <= k < self.n_segments):
            raise IndexError(f"trecho {index!r} fora de 0..{self.n_segments - 1}")
        return (
            float(self._g[k]),  # type: ignore[attr-defined]
            float(self._b[k]),  # type: ignore[attr-defined]
            float(self._lo[k]),  # type: ignore[attr-defined]
            float(self._hi[k]),  # type: ignore[attr-defined]
        )

    def linearize(self, index: int, sign: float) -> tuple[float, float, float, float]:
        """``(g, b, v_min, v_max)`` já com o sinal do semieixo aplicado.

        ``sign`` é ``+1`` para o primeiro quadrante e ``−1`` para o
        terceiro. O trecho central (índice 0) atravessa a origem e é o
        mesmo nos dois.
        """
        g, b, lo, hi = self.segment(index)
        if int(index) == 0 or sign >= 0.0:
            return g, b, lo, hi
        return g, -b, -hi, -lo

    def current_A_at(self, v_V: float) -> float:
        """Corrente da característica em ``v`` [A]."""
        v = float(v_V)
        k = self.segment_index(v)
        g, b, _lo, _hi = self.linearize(k, math.copysign(1.0, v) if v else 1.0)
        return g * v + b

    def contains(self, index: int, v_V: float, sign: float) -> bool:
        """``True`` se ``v`` pertence ao trecho ``index`` no semieixo ``sign``."""
        _g, _b, lo, hi = self.linearize(index, sign)
        tol = SEGMENT_TOLERANCE * max(abs(lo), abs(hi), 1.0)
        topo = int(index) == self.n_segments - 1
        return (lo - tol) <= float(v_V) <= (float("inf") if topo else hi + tol)


# ---------------------------------------------------------------------------
# Ramo compensado
# ---------------------------------------------------------------------------


class CompensatedBranch(Component):
    """Ramo excluído de ``[Y]`` e resolvido por compensação.

    Não estampa matriz nem vetor independente: o solver o retira da rede,
    resolve o sistema linear sem ele, acha a corrente pela interseção das
    duas equações escalares e superpõe a resposta
    [FONTE: Dommel 1971, §V].

    Subclasses fornecem a característica em :attr:`characteristic`.
    """

    def __init__(
        self, name: str, node_p: str, node_n: str, characteristic: PiecewiseLinearVI
    ) -> None:
        super().__init__(name, (node_p, node_n))
        if self.nodes[0] == self.nodes[1]:
            raise ValueError(
                f"ramo compensado {name!r} curto-circuitado (mesmo nó nos dois terminais)"
            )
        if not isinstance(characteristic, PiecewiseLinearVI):
            raise TypeError(
                f"{name!r}: characteristic deve ser PiecewiseLinearVI, "
                f"obtido {type(characteristic).__name__}"
            )
        self.characteristic: PiecewiseLinearVI = characteristic
        self._v: float = 0.0
        self._i: float = 0.0
        self._segment: int = 0
        self._sign: float = 1.0
        self._peak_v: float = 0.0
        self._peak_i: float = 0.0
        self._energy_J: float = 0.0
        self._t_prev: float = -1.0
        self._extrapolated: bool = False

    # -- contrato de compensação -------------------------------------------

    def is_compensated(self) -> bool:
        return True

    def compensation_nodes(self) -> tuple[int, int]:
        """Índices ``(k, m)`` dos terminais, já resolvidos."""
        if not self._idx:
            raise ValueError(
                f"ramo compensado {self.name!r} não foi ligado; chame Circuit.build()"
            )
        return int(self._idx[0]), int(self._idx[1])

    def active_segment(self) -> tuple[int, float]:
        """``(índice, sinal)`` do trecho ativo — o do passo anterior.

        É o ponto de partida da busca, como no programa da BPA: *"the
        search process starts at the location of the intersection in the
        preceding time step"* [FONTE: Dommel 1971, §V, p. 2563].
        """
        return int(self._segment), float(self._sign)

    def set_active_segment(self, index: int, sign: float) -> None:
        """Registra o trecho em que a interseção foi encontrada."""
        self._segment = int(index)
        self._sign = 1.0 if float(sign) >= 0.0 else -1.0

    def set_solution(self, v_V: float, i_A: float, t: float) -> None:
        """Recebe do solver o ponto de operação do passo."""
        v = float(v_V)
        i = float(i_A)
        v_max, i_max = self.characteristic.max_point
        if abs(v) > v_max and not self._extrapolated:
            # Estar no último TRECHO é normal; estar além do último PONTO
            # é operar fora do dado caracterizado, e isso se registra.
            self._extrapolated = True
            log.warning(
                "ramo %r operando ALÉM do último ponto caracterizado "
                "(%.4g V / %.4g A): a tensão residual está sendo "
                "EXTRAPOLADA com a inclinação do trecho final e não é mais "
                "dado publicado",
                self.name,
                v_max,
                i_max,
            )
        if self._t_prev >= 0.0 and t > self._t_prev:
            # Trapézio sobre p = v·i, com o ponto anterior.
            dt = float(t) - self._t_prev
            self._energy_J += 0.5 * (self._v * self._i + v * i) * dt
        self._v = v
        self._i = i
        self._t_prev = float(t)
        if abs(v) > abs(self._peak_v):
            self._peak_v = v
        if abs(i) > abs(self._peak_i):
            self._peak_i = i

    # -- leitura ------------------------------------------------------------

    @property
    def peak_voltage_V(self) -> float:
        """Maior tensão em módulo vista pelo ramo, COM sinal [V]."""
        return self._peak_v

    @property
    def peak_current_A(self) -> float:
        """Maior corrente em módulo conduzida, COM sinal [A]."""
        return self._peak_i

    @property
    def energy_J(self) -> float:
        """Energia dissipada acumulada [J]."""
        return self._energy_J

    @property
    def extrapolated(self) -> bool:
        """``True`` se o ramo já operou além do último ponto caracterizado."""
        return self._extrapolated

    # -- ciclo de vida ------------------------------------------------------

    def reset(self) -> None:
        self._v = 0.0
        self._i = 0.0
        self._segment = 0
        self._sign = 1.0
        self._peak_v = 0.0
        self._peak_i = 0.0
        self._energy_J = 0.0
        self._t_prev = -1.0
        self._extrapolated = False

    def stamp_matrix(self, A: np.ndarray) -> None:
        """Nada: o ramo está FORA de ``[Y]`` por construção."""

    def stamp_rhs(self, b: np.ndarray, t: float, mode: str) -> None:
        """Nada: a injeção equivalente é aplicada pela superposição."""

    def commit(self, x: np.ndarray, t: float, mode: str) -> None:
        """Nada: o ponto de operação chega por :meth:`set_solution`."""

    # -- regime permanente --------------------------------------------------

    def stamp_phasor(self, A: np.ndarray, b: np.ndarray, omega: float) -> None:
        """Estampa a CONDUTÂNCIA DO TRECHO CENTRAL no sistema fasorial.

        O trecho central é o que atravessa a origem — a região de fuga de
        um para-raios. Enquanto o ponto de operação de regime permanecer
        dentro dele, essa condutância é a linearização EXATA do ramo, e
        não uma aproximação: a característica é literalmente linear ali.

        Se a tensão de regime ultrapassar o joelho, a linearização deixa
        de valer e o fato é registrado em log por
        :meth:`check_phasor_operating_point` — o regime resultante estaria
        errado, e o caso deve ser revisto (um para-raios que conduz em
        regime é um para-raios mal selecionado).
        """
        g, _b, _lo, _hi = self.characteristic.linearize(0, 1.0)
        p, n = self._idx[0], self._idx[1]
        if p != GROUND_INDEX:
            A[p, p] += g
        if n != GROUND_INDEX:
            A[n, n] += g
        if p != GROUND_INDEX and n != GROUND_INDEX:
            A[p, n] -= g
            A[n, p] -= g

    def phasor_branches(self, x: np.ndarray, omega: float):
        """Par ``(V̂, Î)`` do ramo na solução fasorial."""
        g, _b, _lo, _hi = self.characteristic.linearize(0, 1.0)
        p, n = self._idx[0], self._idx[1]
        vp = 0.0 if p == GROUND_INDEX else complex(x[p])
        vn = 0.0 if n == GROUND_INDEX else complex(x[n])
        v = vp - vn
        self.check_phasor_operating_point(v)
        return ((v, v * g),)

    def check_phasor_operating_point(self, v_phasor: complex) -> bool:
        """Verifica se o regime cai dentro do trecho central; registra se não.

        Returns
        -------
        bool
            ``True`` se a linearização de regime é válida.
        """
        joelho = self.characteristic.knee_voltage_V
        pico = abs(complex(v_phasor))
        if pico <= joelho:
            return True
        log.warning(
            "ramo %r com tensão de regime de %.4g V de pico ACIMA do joelho "
            "da característica (%.4g V): a linearização do regime permanente "
            "não vale e o estado inicial da marcha está errado",
            self.name,
            pico,
            joelho,
        )
        return False

    def topology_signature(self) -> object:
        """Constante: mudar de trecho NÃO muda ``[Y]``.

        É a vantagem central do método — o trecho ativo não aparece na
        matriz, logo não há refatoração nem CDA a cada mudança de ponto
        de operação.
        """
        return ("COMP", self.name)

    def branch_voltage(self, index: int = 0) -> float:
        return self._v

    def branch_current(self, index: int = 0) -> float:
        return self._i


# ---------------------------------------------------------------------------
# Rede de compensação
# ---------------------------------------------------------------------------


class CompensationNetwork:
    """Resolve o conjunto de ramos compensados de um circuito.

    Mantém os vetores de superposição ``w_j`` e a matriz de Thévenin
    ``z_T`` entre os ramos, recomputados a cada refatoração — e só nela,
    porque *"the slope z_T remains unchanged as long as no switchings take
    place in the network"* [FONTE: Dommel 1971, §V, p. 2563].

    Parameters
    ----------
    branches:
        Ramos compensados, na ordem em que aparecem no circuito.
    """

    def __init__(self, branches) -> None:
        self.branches = tuple(branches)
        self._w: np.ndarray | None = None
        self._zt: np.ndarray | None = None
        self._singular_warned: bool = False

    def __len__(self) -> int:
        return len(self.branches)

    @property
    def thevenin_ohm(self) -> np.ndarray:
        """Matriz ``z_T`` (M×M) vista pelos ramos [Ω]."""
        if self._zt is None:
            raise ValueError("chame prepare() antes de ler thevenin_ohm")
        return self._zt.copy()

    def invalidate(self) -> None:
        """Marca ``w`` e ``z_T`` como obsoletos (topologia mudou)."""
        self._w = None
        self._zt = None

    @property
    def prepared(self) -> bool:
        """``True`` se ``w`` e ``z_T`` estão válidos para a topologia atual."""
        return self._w is not None

    def prepare(self, dimension: int, solve) -> None:
        """Computa ``w_j`` e ``z_T`` com a fatoração corrente.

        Parameters
        ----------
        dimension:
            Ordem do sistema.
        solve:
            Chamável ``b → x`` que aplica a fatoração vigente.
        """
        m = len(self.branches)
        w = np.zeros((int(dimension), m), dtype=float)
        for j, ramo in enumerate(self.branches):
            k, n = ramo.compensation_nodes()
            b = np.zeros(int(dimension), dtype=float)
            # Corrente unitária SAINDO de k pelo ramo: b[k] -= 1, b[m] += 1.
            if k != GROUND_INDEX:
                b[k] -= 1.0
            if n != GROUND_INDEX:
                b[n] += 1.0
            w[:, j] = np.asarray(solve(b), dtype=float).ravel()
        zt = np.zeros((m, m), dtype=float)
        for l, ramo in enumerate(self.branches):
            k, n = ramo.compensation_nodes()
            for j in range(m):
                zt[l, j] = -(
                    node_voltage(w[:, j], k) - node_voltage(w[:, j], n)
                )
        self._w = w
        self._zt = zt

    def correct(self, x0: np.ndarray, t: float) -> np.ndarray:
        """Aplica a compensação à solução ``x0`` obtida SEM os ramos.

        Returns
        -------
        numpy.ndarray
            Solução final ``x = x⁽⁰⁾ + Σ_j i_j·w_j`` [FONTE: Dommel 1971,
            eq. (6)].
        """
        m = len(self.branches)
        if m == 0:
            # Rede sem ramo compensado é transparente: nada a preparar e
            # nada a corrigir.
            return x0
        if self._w is None or self._zt is None:
            raise ValueError("chame prepare() antes de correct()")
        v0 = np.empty(m, dtype=float)
        for l, ramo in enumerate(self.branches):
            k, n = ramo.compensation_nodes()
            v0[l] = node_voltage(x0, k) - node_voltage(x0, n)

        # Trecho de partida: o do passo anterior, com o sinal sugerido pela
        # tensão de circuito aberto — que é a melhor informação disponível
        # antes de resolver.
        indices = []
        sinais = []
        for l, ramo in enumerate(self.branches):
            idx, _sig = ramo.active_segment()
            indices.append(idx)
            sinais.append(1.0 if v0[l] >= 0.0 else -1.0)

        g = np.empty(m, dtype=float)
        b = np.empty(m, dtype=float)
        v = v0.copy()
        i = np.zeros(m, dtype=float)
        eye = np.eye(m)
        for _ in range(MAX_SEGMENT_ITERATIONS):
            for l, ramo in enumerate(self.branches):
                g[l], b[l], _lo, _hi = ramo.characteristic.linearize(
                    indices[l], sinais[l]
                )
            # (I + z_T·G)·v = v0 − z_T·b
            A = eye + self._zt @ np.diag(g)
            rhs = v0 - self._zt @ b
            try:
                v = np.linalg.solve(A, rhs)
            except np.linalg.LinAlgError:  # pragma: no cover - defensivo
                if not self._singular_warned:
                    self._singular_warned = True
                    log.warning(
                        "sistema de compensação singular em t = %.6g s; ramos "
                        "mantidos no ponto de operação anterior neste passo",
                        t,
                    )
                return x0
            i = g * v + b
            movidos = False
            for l, ramo in enumerate(self.branches):
                sinal = 1.0 if v[l] >= 0.0 else -1.0
                car = ramo.characteristic
                alvo = car.segment_index(v[l])
                if alvo != indices[l] or sinal != sinais[l]:
                    indices[l] = alvo
                    sinais[l] = sinal
                    movidos = True
            if not movidos:
                break
        else:  # pragma: no cover - guarda numérica
            log.warning(
                "busca de trecho não convergiu em %d trocas em t = %.6g s; "
                "adotado o último ponto de operação",
                MAX_SEGMENT_ITERATIONS,
                t,
            )

        x = np.asarray(x0, dtype=float) + self._w @ i
        for l, ramo in enumerate(self.branches):
            k, n = ramo.compensation_nodes()
            ramo.set_active_segment(indices[l], sinais[l])
            ramo.set_solution(node_voltage(x, k) - node_voltage(x, n), float(i[l]), t)
        return x


def collect_compensated(components) -> tuple:
    """Ramos compensados de uma coleção de componentes, na ordem dada."""
    return tuple(c for c in components if getattr(c, "is_compensated", None) and c.is_compensated())


# ---------------------------------------------------------------------------
# Limitações
# ---------------------------------------------------------------------------

KNOWN_LIMITATIONS: dict[str, str] = {
    "emt_nonlinear_absent_from_phasor_solution": (
        "O ramo compensado NÃO participa da solução fasorial de regime "
        "permanente: ele não estampa a matriz de admitância nem em regime "
        "nem na marcha, e a partida em regime o ignora. Para um para-raios "
        "isso é aceitável — a corrente de fuga na tensão de operação "
        "contínua é de microampères e não altera o regime —, mas para "
        "qualquer não linearidade que conduza em regime (saturação de "
        "transformador, por exemplo) o estado inicial ficaria ERRADO. O "
        "primeiro passo da marcha corrige o ponto de operação, de modo que "
        "o erro é transitório, não permanente."
    ),
    "emt_nonlinear_odd_symmetry_assumed": (
        "A característica é informada apenas no PRIMEIRO QUADRANTE e o "
        "terceiro é tomado como seu simétrico. É a hipótese usual para "
        "para-raios de óxido metálico e resistores não lineares sem "
        "polaridade, e é a representação da Fig. 2 de Dommel 1971. Um "
        "elemento com característica assimétrica (diodo, varistor "
        "polarizado) NÃO pode ser representado por esta classe."
    ),
    "emt_nonlinear_extrapolates_beyond_last_point": (
        "Além do último ponto informado a característica é extrapolada com "
        "a inclinação do trecho final, e a primeira ocorrência é "
        "registrada em log. A escolha é conservadora para a tensão "
        "residual, mas o valor extrapolado NÃO é dado caracterizado: "
        "resultados em que o ramo operou nessa região devem citar a "
        "extrapolação. A propriedade ``extrapolated`` do ramo diz se isso "
        "ocorreu."
    ),
    "emt_nonlinear_no_dynamic_arrester_model": (
        "O para-raios é representado apenas por sua característica "
        "estática v-i. Não há o modelo dinâmico dependente da frequência "
        "(IEEE WG 3.4.11 / Pinceti-Giannettoni), em que a tensão residual "
        "de uma frente rápida excede a estática em 10 a 20 %. Para frentes "
        "de microssegundo o nível de proteção calculado é, portanto, COTA "
        "INFERIOR. [LITERATURA não acessada nesta sessão — a afirmação "
        "sobre a ordem de grandeza vem da prática corrente e deve ser "
        "verificada antes de citação acadêmica.]"
    ),
}


__all__ = [
    "KNOWN_LIMITATIONS",
    "MAX_SEGMENT_ITERATIONS",
    "SEGMENT_TOLERANCE",
    "CompensatedBranch",
    "CompensationNetwork",
    "PiecewiseLinearVI",
    "collect_compensated",
]
