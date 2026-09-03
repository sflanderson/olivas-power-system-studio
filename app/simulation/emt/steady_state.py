"""
app.simulation.emt.steady_state — inicialização em REGIME PERMANENTE
SENOIDAL do kernel EMT.

O problema
===========

A marcha no tempo de Dommel resolve, a cada passo, um sistema algébrico
cujo lado direito carrega os TERMOS HISTÓRICOS dos elementos
armazenadores. Partir do repouso — todos os históricos nulos — significa
partir de um estado que NÃO é solução do circuito energizado: a resposta
natural que daí decorre é um transitório de energização espúrio, que se
superpõe ao fenômeno de interesse e contamina o ``V_pk`` e o ``dv/dt``
extraídos para o vetor de estresse.

A solução, prescrita pela fonte primária e adotada pelo ATP, é resolver
o circuito por TRANSFORMAÇÃO FASORIAL no estado inicial das chaves e
semear os históricos de forma coerente com os modelos companheiros:

    I_L(0) = i_L(0) + G_L·v_L(0)          G_L = Δt/(2L)
    I_C(0) = −[G_C·v_C(0) + i_C(0)]       G_C = 2C/Δt

[LISTA: 02, §1.4 e eq. (6)]; [FONTE: Dommel 1969, Apêndice I, p. 395,
"if the initial conditions are not zero, the history terms must be
preloaded"]. No ATP o mesmo efeito vem do ``TSTART`` negativo do cartão
de fonte, que inclui a fonte na solução fasorial executada antes da
integração no tempo, com as chaves no estado que possuem em ``t = 0``
[LISTA: 02, §1.4 e §3.6].

Convenção de fasor
===================

**Fasor de AMPLITUDE com o COSSENO como referência**, isto é

    x(t) = Re{ X̂ · e^{jωt} },     X̂ = A·e^{jφ}

de modo que ``v_s(t) = 100·cos(377 t)`` V corresponde a ``V̂ = 100∠0°``
e ``v_s(0) = 100 V`` [LISTA: 02, §1.4]. Uma fonte declarada com
``phase_reference="sin"`` é convertida por ``sen(θ) = cos(θ − 90°)``,
de modo que a semeadura é correta nas duas convenções.

Impedâncias de ramo
====================

O sistema MNA COMPLEXO é montado em ``ω`` com a MESMA numeração de nós e
de incógnitas do sistema real (``Circuit.build()``), trocando apenas os
carimbos:

===================  =====================================================
Ramo                 Admitância em ``ω``
===================  =====================================================
``Resistor``         ``1/R``
``Inductor``         ``1/(jωL)``
``Capacitor``        ``jωC``
``CoupledRL``        ``(R + jωL)⁻¹`` (matricial)
``VoltageSource``    incidência ±1 e restrição ``v_p − v_n = V̂``
``Switch``           idêntica ao caso real: ``v_k − v_m = 0`` (fechada)
                     ou ``i_km = 0`` (aberta)
``BergeronLine``     matriz de admitância 2×2 do PRÓPRIO modelo discreto
===================  =====================================================

A linha de Bergeron merece nota. Não se usa a admitância da linha ideal
de parâmetros distribuídos, e sim a admitância que as EQUAÇÕES DO MODELO
IMPLEMENTADO exibem em regime senoidal — com o operador de atraso
``d = e^{−jωτ}``, o fator de atenuação ``ζ`` e a repartição ``a, b`` das
perdas concentradas de :mod:`app.simulation.emt.line`. Só assim a
semeadura é coerente com o que a marcha no tempo vai efetivamente
recursar. Para a linha sem perdas o resultado se reduz, como deve, ao
par clássico ``Y₁₁ = 1/(jZ_c·tg ωτ)`` e ``Y₁₂ = −1/(jZ_c·sen ωτ)``
[CÁLCULO PRÓPRIO; conferido no teste
``test_linha_sem_perdas_reduz_a_admitancia_classica``].

Exatidão medida
================

A semeadura usa fasores CONTÍNUOS (``jωL``, ``1/jωC``), que NÃO são o
ponto fixo exato da recursão trapezoidal: aplicada a um seno amostrado,
a recursão do indutor exibe impedância ``j·(2L/Δt)·tg(ωΔt/2)``, isto é,
a rede discreta responde como a rede contínua em ``ω_ef = (2/Δt)·
tg(ωΔt/2)``. O desvio relativo é ``(ωΔt)²/12`` e o resíduo que dele
decorre é um **desvio PERMANENTE de amplitude constante**, não um
transitório de energização que decaia — o que importa é que ele é
minúsculo e converge como ``Δt²``. [CÁLCULO PRÓPRIO, medido em
``tests/test_emt_steady_state.py``:] no RL série de referência
(``R = 0,5 Ω``, ``L = 25 mH``, 60 Hz) com ``Δt = 1 µs`` mede-se
``1,36 × 10⁻⁷ A`` sobre 4,43 A, e o resíduo cai por 4 a cada divisão
de ``Δt`` por 2.

Em circuitos cuja saída é POUCO sensível a ``ω`` o resíduo é ainda
menor por cancelamento. É o caso do circuito de referência da Lista 02
(Questão 2, ``Δt = 1 µs``), cuja tensão de reator vale ``90,912 V∠
−0,0005°`` — quase estacionária em ``ω``:

    max |v_num(t) − v_fasor(t)| = 1,39 × 10⁻¹⁰ V   (t < t₀)

[LISTA: 02, Tabela 3] — reproduzido por este módulo com ``1,392 ×
10⁻¹⁰ V`` [CÁLCULO PRÓPRIO]. Em qualquer dos dois patamares não há
transitório espúrio de energização: é essa a diferença que importa em
relação à partida do repouso, em que o desvio inicial é da ordem da
própria amplitude de regime.

Limitação declarada
====================

UMA ÚNICA FREQUÊNCIA. O módulo resolve um problema fasorial em um único
``ω``; harmônicos, componente contínua e fontes de frequências distintas
exigiriam superposição de soluções, não implementada. Detectada mais de
uma frequência — ou qualquer ``dc_offset_V`` não nulo — levanta-se
:class:`MultipleFrequenciesError` em vez de produzir uma semeadura
silenciosamente errada. Mesma política para ramo não suportado
(:class:`UnsupportedComponentError`).

Referências
============

* [FONTE: H. W. Dommel, "Digital computer solution of electromagnetic
  transients in single- and multiphase networks", *IEEE Trans. PAS*,
  vol. PAS-88, n. 4, pp. 388-399, abr. 1969] — Apêndice I, p. 395
  (pré-carga dos termos históricos) e p. 389, eq. (7) (linha).
* [FONTE: C.-W. Ho, A. E. Ruehli, P. A. Brennan, "The modified nodal
  approach to network analysis", *IEEE Trans. CAS*, vol. CAS-22, n. 6,
  pp. 504-509, jun. 1975] — eq. (2) e Tabela I (estrutura do sistema).
* [LISTA: 02, §1.4, eq. (6); §2.3; §3.3; §3.6; Tabela 3].
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from app.core.logging_config import get_logger

from app.simulation.emt.components import (
    GROUND_INDEX,
    Capacitor,
    Component,
    CoupledRL,
    Inductor,
    Resistor,
    Switch,
    VoltageSource,
    is_ground,
)
from app.simulation.emt.line import BergeronLine

if TYPE_CHECKING:  # pragma: no cover - somente para anotações
    from app.simulation.emt.circuit import Circuit

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

#: Partida do repouso — históricos nulos, salvo condição inicial
#: explícita nos ramos. Comportamento histórico do kernel.
INIT_ZERO: str = "zero"

#: Partida em regime permanente senoidal por solução fasorial.
INIT_STEADY_STATE: str = "steady_state"

#: Modos de partida aceitos por :class:`app.simulation.emt.Solver`.
INIT_MODES: tuple[str, ...] = (INIT_ZERO, INIT_STEADY_STATE)

#: Tolerância RELATIVA para considerar duas frequências como a mesma.
FREQUENCY_TOLERANCE: float = 1.0e-9

#: Limite de condicionamento estimado acima do qual se emite ``WARNING``
#: na solução fasorial (ressonância série/paralela quase exata, ou linha
#: em múltiplo de meia onda).
PHASOR_CONDITION_LIMIT: float = 1.0e12


# ---------------------------------------------------------------------------
# Erros
# ---------------------------------------------------------------------------


class SteadyStateError(ValueError):
    """Falha na inicialização em regime permanente senoidal."""


class MultipleFrequenciesError(SteadyStateError):
    """O circuito não tem UMA única frequência de excitação bem definida.

    Levantado quando há fontes ativas em frequências distintas, quando há
    componente contínua (``dc_offset_V``) junto de excitação senoidal, ou
    quando não há nenhuma fonte senoidal ativa que defina ``ω``.
    """


class UnsupportedComponentError(SteadyStateError):
    """Ramo sem equivalente fasorial implementado.

    Preferiu-se o erro explícito à semeadura parcial: um ramo ignorado
    produziria uma solução fasorial que NÃO é a do circuito, e o
    transitório espúrio resultante seria atribuído à física.
    """


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------


@dataclass
class PhasorSolution:
    """Solução fasorial do circuito na topologia inicial das chaves.

    Attributes
    ----------
    omega_rad_s:
        Frequência angular da solução [rad/s].
    frequency_Hz:
        Frequência da solução [Hz].
    x:
        Vetor solução COMPLEXO do sistema MNA, com a mesma numeração de
        :meth:`app.simulation.emt.Circuit.build` — tensões nodais
        seguidas das incógnitas de corrente.
    node_index:
        Mapa ``nome do nó → índice``, cópia do circuito.
    branch_phasors:
        Mapa ``nome do ramo → tupla de pares (V̂, Î)``, um par por ramo
        elétrico do componente (``Component.n_branches()``). Tensão
        ``v_p − v_n`` e corrente SAINDO do nó ``p``, mesma convenção de
        :meth:`Component.branch_voltage` / :meth:`branch_current`.
    condition_estimate:
        Estimativa de ``cond(A)`` da matriz complexa — valor muito
        elevado indica ressonância quase exata.
    """

    omega_rad_s: float
    frequency_Hz: float
    x: np.ndarray
    node_index: dict[str, int] = field(default_factory=dict)
    branch_phasors: dict[str, tuple[tuple[complex, complex], ...]] = field(
        default_factory=dict
    )
    condition_estimate: float = 0.0

    # -- leitura ------------------------------------------------------------

    def node_phasor(self, node: str) -> complex:
        """Fasor de amplitude da tensão do nó ``node`` [V]."""
        if is_ground(node):
            return 0.0 + 0.0j
        idx = self.node_index.get(str(node))
        if idx is None:
            raise SteadyStateError(f"nó {node!r} não existe no circuito")
        return complex(self.x[idx])

    def node_value_at(self, node: str, t: float) -> float:
        """Valor instantâneo da tensão do nó ``node`` em ``t`` [V]."""
        return instantaneous(self.node_phasor(node), self.omega_rad_s, t)

    def branch_phasor(self, name: str, index: int = 0) -> tuple[complex, complex]:
        """Par ``(V̂, Î)`` do ramo ``index`` do componente ``name``."""
        pairs = self.branch_phasors.get(str(name))
        if pairs is None:
            raise SteadyStateError(f"componente {name!r} ausente da solução fasorial")
        if not 0 <= int(index) < len(pairs):
            raise SteadyStateError(
                f"ramo {index!r} inválido para {name!r} "
                f"({len(pairs)} ramo(s) disponível(is))"
            )
        return pairs[int(index)]

    def state_at(self, t: float) -> np.ndarray:
        """Vetor solução REAL do sistema MNA no instante ``t``."""
        return np.real(self.x * np.exp(1j * self.omega_rad_s * float(t)))


def instantaneous(phasor: complex, omega_rad_s: float, t: float) -> float:
    """``Re{X̂·e^{jωt}}`` — valor instantâneo do fasor de amplitude."""
    return float(np.real(complex(phasor) * np.exp(1j * float(omega_rad_s) * float(t))))


# ---------------------------------------------------------------------------
# Frequência de excitação
# ---------------------------------------------------------------------------


def source_phasor(source: VoltageSource) -> complex:
    """Fasor de amplitude da fonte, com o COSSENO como referência.

    ``phase_reference="cos"`` ⇒ ``V̂ = A·e^{jφ}``;
    ``phase_reference="sin"`` ⇒ ``V̂ = A·e^{j(φ − π/2)}``, pois
    ``sen(θ) = cos(θ − 90°)`` [LISTA: 02, §1.4].
    """
    phase = math.radians(source.phase_deg)
    if source.phase_reference != "cos":
        phase -= 0.5 * math.pi
    return complex(source.amplitude_V * np.exp(1j * phase))


def source_frequency(circuit: Circuit, *, frequency_Hz: float | None = None) -> float:
    """Determina a ÚNICA frequência de excitação do circuito [Hz].

    Parameters
    ----------
    circuit:
        Circuito a inspecionar.
    frequency_Hz:
        Frequência imposta pelo usuário. Se informada e o circuito tiver
        uma frequência detectável distinta, é erro — a divergência
        significa semeadura errada.

    Raises
    ------
    MultipleFrequenciesError
        Mais de uma frequência ativa, componente contínua presente, ou
        nenhuma frequência determinável.
    """
    detected: list[tuple[str, float]] = []
    with_dc: list[str] = []
    for comp in circuit.components:
        if not isinstance(comp, VoltageSource):
            continue
        if comp.dc_offset_V != 0.0:
            with_dc.append(comp.name)
        if comp.amplitude_V != 0.0:
            detected.append((comp.name, float(comp.frequency_Hz)))

    if with_dc:
        raise MultipleFrequenciesError(
            "inicialização em regime permanente senoidal exige excitação de UMA "
            f"única frequência; as fontes {sorted(with_dc)!r} têm dc_offset_V "
            "não nulo, o que acrescenta a frequência zero. A solução do ponto "
            "de operação em corrente contínua exigiria superposição (indutor em "
            "curto, capacitor em aberto), NÃO implementada — use init='zero' e "
            "uma janela de acomodação, ou semeie as condições iniciais à mão."
        )

    dc_like = sorted(name for name, f in detected if f <= 0.0)
    if dc_like:
        raise MultipleFrequenciesError(
            f"as fontes {dc_like!r} têm amplitude não nula com frequency_Hz = 0; "
            "isso é uma fonte de corrente contínua, cuja inicialização não é "
            "coberta pela solução fasorial deste módulo — use init='zero'."
        )

    unique: list[float] = []
    for _, f in detected:
        if not any(abs(f - u) <= FREQUENCY_TOLERANCE * max(1.0, abs(u)) for u in unique):
            unique.append(f)

    if len(unique) > 1:
        detalhe = ", ".join(f"{name}: {f:.9g} Hz" for name, f in sorted(detected))
        raise MultipleFrequenciesError(
            "inicialização em regime permanente senoidal restrita a UMA única "
            f"frequência; foram detectadas {len(unique)} — {detalhe}. A "
            "superposição de soluções fasoriais em frequências distintas NÃO "
            "está implementada (limitação emt_steady_state_single_frequency)."
        )

    if not unique:
        if frequency_Hz is None:
            raise MultipleFrequenciesError(
                "não há fonte senoidal ativa que defina ω: nenhum VoltageSource "
                "com amplitude_V não nula e frequency_Hz > 0. Informe "
                "frequency_Hz explicitamente ou use init='zero'."
            )
        f_user = float(frequency_Hz)
        if not math.isfinite(f_user) or f_user <= 0.0:
            raise SteadyStateError(
                f"frequency_Hz deve ser finita e > 0, obtida {frequency_Hz!r}"
            )
        return f_user

    f_det = unique[0]
    if frequency_Hz is not None:
        f_user = float(frequency_Hz)
        if abs(f_user - f_det) > FREQUENCY_TOLERANCE * max(1.0, abs(f_det)):
            raise MultipleFrequenciesError(
                f"frequency_Hz={f_user:.9g} Hz diverge da frequência detectada "
                f"nas fontes ({f_det:.9g} Hz); a semeadura resultante seria "
                "incoerente com a excitação."
            )
    return f_det


# ---------------------------------------------------------------------------
# Estampagem complexa
# ---------------------------------------------------------------------------


def _stamp_admittance(A: np.ndarray, p: int, n: int, y: complex) -> None:
    """Estampa uma admitância ``y`` entre os nós ``p`` e ``n``."""
    if p != GROUND_INDEX:
        A[p, p] += y
    if n != GROUND_INDEX:
        A[n, n] += y
    if p != GROUND_INDEX and n != GROUND_INDEX:
        A[p, n] -= y
        A[n, p] -= y


def _stamp_incidence(A: np.ndarray, p: int, n: int, col: int) -> None:
    """Estampa a incidência ±1 da corrente de ramo MNA nas linhas de nó."""
    if p != GROUND_INDEX:
        A[p, col] += 1.0
    if n != GROUND_INDEX:
        A[n, col] -= 1.0


def _line_admittance(line: BergeronLine, omega: float) -> tuple[complex, complex]:
    """Admitância 2×2 do modelo de Bergeron IMPLEMENTADO, em ``ω``.

    Parte das equações de :meth:`BergeronLine._history_sources` e
    :meth:`stamp_matrix`, com ``d = e^{−jωτ}``::

        I_km = g·V_k − a·d·(g·V_m + ζ·I_mk) − b·d·(g·V_k + ζ·I_km)
        I_mk = g·V_m − a·d·(g·V_k + ζ·I_km) − b·d·(g·V_m + ζ·I_mk)

    cuja solução é ``I = [[y11, y12], [y12, y11]]·V``. Devolve
    ``(y11, y12)``.
    """
    g = line.conductance_S
    zeta = line.attenuation_factor
    d = complex(np.exp(-1j * omega * line.travel_time_s))
    a = 0.5 * (1.0 + zeta)
    b = 0.5 * (1.0 - zeta)

    P = 1.0 + b * d * zeta
    Q = a * d * zeta
    alpha = g * (1.0 - b * d)
    beta = -a * d * g

    det = P * P - Q * Q
    if abs(det) <= 1.0e-14 * max(1.0, abs(P) + abs(Q)):
        raise SteadyStateError(
            f"linha {line.name!r}: o sistema fasorial do modelo de Bergeron é "
            f"singular em f = {omega / (2.0 * math.pi):.6g} Hz (ωτ = "
            f"{omega * line.travel_time_s:.6g} rad, múltiplo de π — linha em "
            "meia onda). Não existe regime permanente único nessa combinação "
            "de comprimento e frequência sem perdas; acrescente resistance_ohm "
            "ou altere o comprimento."
        )
    y11 = (P * alpha - Q * beta) / det
    y12 = (P * beta - Q * alpha) / det
    return complex(y11), complex(y12)


def assemble_phasor_system(
    circuit: Circuit, omega_rad_s: float
) -> tuple[np.ndarray, np.ndarray]:
    """Monta ``(A, b)`` complexos do sistema MNA em ``ω``.

    A numeração é EXATAMENTE a de :meth:`Circuit.build`, de modo que a
    solução complexa é diretamente comparável ao vetor real da marcha no
    tempo.

    Raises
    ------
    UnsupportedComponentError
        Ramo sem equivalente fasorial.
    """
    if not circuit.is_built:
        circuit.build()
    omega = float(omega_rad_s)
    if not math.isfinite(omega) or omega <= 0.0:
        raise SteadyStateError(f"ω deve ser finita e > 0, obtida {omega_rad_s!r}")

    n = circuit.dimension
    A = np.zeros((n, n), dtype=complex)
    b = np.zeros(n, dtype=complex)

    for comp in circuit.components:
        hook = getattr(comp, "stamp_phasor", None)
        if callable(hook):
            hook(A, b, omega)
            continue
        _stamp_component(comp, A, b, omega)
    return A, b


def _stamp_component(
    comp: Component, A: np.ndarray, b: np.ndarray, omega: float
) -> None:
    """Estampa um ramo conhecido no sistema complexo."""
    idx = comp._idx  # noqa: SLF001 - índices resolvidos por Circuit.build()
    if isinstance(comp, Resistor):
        _stamp_admittance(A, idx[0], idx[1], 1.0 / comp.resistance_ohm)
        return
    if isinstance(comp, Inductor):
        _stamp_admittance(A, idx[0], idx[1], 1.0 / (1j * omega * comp.inductance_H))
        return
    if isinstance(comp, Capacitor):
        _stamp_admittance(A, idx[0], idx[1], 1j * omega * comp.capacitance_F)
        return
    if isinstance(comp, VoltageSource):
        col = comp._extra[0]  # noqa: SLF001
        _stamp_incidence(A, idx[0], idx[1], col)
        if idx[0] != GROUND_INDEX:
            A[col, idx[0]] += 1.0
        if idx[1] != GROUND_INDEX:
            A[col, idx[1]] -= 1.0
        b[col] += source_phasor(comp)
        return
    if isinstance(comp, Switch):
        col = comp._extra[0]  # noqa: SLF001
        _stamp_incidence(A, idx[0], idx[1], col)
        if comp.closed:
            if idx[0] != GROUND_INDEX:
                A[col, idx[0]] += 1.0
            if idx[1] != GROUND_INDEX:
                A[col, idx[1]] -= 1.0
        else:
            A[col, col] += 1.0
        return
    if isinstance(comp, CoupledRL):
        Y = np.linalg.inv(comp.resistance_ohm + 1j * omega * comp.inductance_H)
        n_w = comp.n_branches()
        for row in range(n_w):
            p, q = idx[2 * row], idx[2 * row + 1]
            for col_w in range(n_w):
                r, s = idx[2 * col_w], idx[2 * col_w + 1]
                y = complex(Y[row, col_w])
                if y == 0.0:
                    continue
                for i_node, s_i in ((p, 1.0), (q, -1.0)):
                    if i_node == GROUND_INDEX:
                        continue
                    for j_node, s_j in ((r, 1.0), (s, -1.0)):
                        if j_node == GROUND_INDEX:
                            continue
                        A[i_node, j_node] += s_i * s_j * y
        return
    if isinstance(comp, BergeronLine):
        y11, y12 = _line_admittance(comp, omega)
        k, m = idx[0], idx[1]
        if k != GROUND_INDEX:
            A[k, k] += y11
        if m != GROUND_INDEX:
            A[m, m] += y11
        if k != GROUND_INDEX and m != GROUND_INDEX:
            A[k, m] += y12
            A[m, k] += y12
        return
    raise UnsupportedComponentError(
        f"ramo {comp.name!r} do tipo {type(comp).__name__} não tem equivalente "
        "fasorial implementado em app.simulation.emt.steady_state. Implemente o "
        "método stamp_phasor(A, b, omega) no componente, ou use init='zero' — a "
        "semeadura parcial produziria um regime permanente que NÃO é o do "
        "circuito."
    )


# ---------------------------------------------------------------------------
# Solução fasorial
# ---------------------------------------------------------------------------


def solve_phasor(
    circuit: Circuit, *, frequency_Hz: float | None = None
) -> PhasorSolution:
    """Resolve o circuito em regime permanente senoidal.

    A topologia usada é a CORRENTE das chaves — no ATP, "as chaves entram
    na solução fasorial no estado que possuem em ``t = 0``"
    [LISTA: 02, §1.4].

    Raises
    ------
    MultipleFrequenciesError, UnsupportedComponentError, SteadyStateError
    """
    freq = source_frequency(circuit, frequency_Hz=frequency_Hz)
    omega = 2.0 * math.pi * freq
    A, b = assemble_phasor_system(circuit, omega)

    cond = float(np.linalg.cond(A)) if A.size else 0.0
    if not math.isfinite(cond) or cond > PHASOR_CONDITION_LIMIT:
        log.warning(
            "sistema fasorial de %r mal condicionado (cond ≈ %.3e) em %.6g Hz: "
            "ressonância quase exata ou ramo sem caminho para a terra com a "
            "chave aberta; a semeadura pode ser numericamente pobre",
            circuit.name,
            cond,
            freq,
        )
    try:
        x = np.linalg.solve(A, b)
    except np.linalg.LinAlgError as exc:
        raise SteadyStateError(
            f"sistema fasorial de {circuit.name!r} singular em {freq:.6g} Hz "
            f"({exc}). Causa típica: nó isolado com a chave ABERTA — em regime "
            "permanente esse nó não tem tensão definida. Acrescente um caminho "
            "de fuga (resistência elevada) ou inicie com a chave fechada."
        ) from exc

    solution = PhasorSolution(
        omega_rad_s=omega,
        frequency_Hz=freq,
        x=np.asarray(x, dtype=complex),
        node_index=dict(circuit.node_index),
        condition_estimate=cond,
    )
    solution.branch_phasors = _branch_phasors(circuit, solution)
    return solution


def _node_phasor_by_index(x: np.ndarray, index: int) -> complex:
    """Fasor da tensão nodal por índice, tratando a terra como 0 V."""
    if index == GROUND_INDEX:
        return 0.0 + 0.0j
    return complex(x[index])


def _branch_phasors(
    circuit: Circuit, solution: PhasorSolution
) -> dict[str, tuple[tuple[complex, complex], ...]]:
    """Calcula ``(V̂, Î)`` de cada ramo a partir da solução nodal."""
    x = solution.x
    omega = solution.omega_rad_s
    out: dict[str, tuple[tuple[complex, complex], ...]] = {}
    for comp in circuit.components:
        idx = comp._idx  # noqa: SLF001
        if isinstance(comp, Resistor):
            v = _node_phasor_by_index(x, idx[0]) - _node_phasor_by_index(x, idx[1])
            out[comp.name] = ((v, v / comp.resistance_ohm),)
        elif isinstance(comp, Inductor):
            v = _node_phasor_by_index(x, idx[0]) - _node_phasor_by_index(x, idx[1])
            out[comp.name] = ((v, v / (1j * omega * comp.inductance_H)),)
        elif isinstance(comp, Capacitor):
            v = _node_phasor_by_index(x, idx[0]) - _node_phasor_by_index(x, idx[1])
            out[comp.name] = ((v, v * 1j * omega * comp.capacitance_F),)
        elif isinstance(comp, (VoltageSource, Switch)):
            v = _node_phasor_by_index(x, idx[0]) - _node_phasor_by_index(x, idx[1])
            out[comp.name] = ((v, complex(x[comp._extra[0]])),)  # noqa: SLF001
        elif isinstance(comp, CoupledRL):
            Y = np.linalg.inv(comp.resistance_ohm + 1j * omega * comp.inductance_H)
            v_vec = np.array(
                [
                    _node_phasor_by_index(x, idx[2 * k])
                    - _node_phasor_by_index(x, idx[2 * k + 1])
                    for k in range(comp.n_branches())
                ],
                dtype=complex,
            )
            i_vec = Y @ v_vec
            out[comp.name] = tuple(
                (complex(v_vec[k]), complex(i_vec[k])) for k in range(comp.n_branches())
            )
        elif isinstance(comp, BergeronLine):
            y11, y12 = _line_admittance(comp, omega)
            v_k = _node_phasor_by_index(x, idx[0])
            v_m = _node_phasor_by_index(x, idx[1])
            out[comp.name] = (
                (v_k, y11 * v_k + y12 * v_m),
                (v_m, y12 * v_k + y11 * v_m),
            )
        else:  # pragma: no cover - já barrado na estampagem
            raise UnsupportedComponentError(
                f"ramo {comp.name!r} do tipo {type(comp).__name__} sem leitura "
                "fasorial implementada"
            )
    return out


# ---------------------------------------------------------------------------
# Semeadura dos termos históricos
# ---------------------------------------------------------------------------


def seed_from_phasor(
    circuit: Circuit, solution: PhasorSolution, dt: float
) -> dict[str, tuple[float, ...]]:
    """Semeia os históricos de todos os ramos a partir da solução fasorial.

    Aplica, elemento a elemento, a eq. (6) da Lista 02 — pela via
    declarada do kernel, que é impor ``i(0)`` e ``v(0)`` nos parâmetros
    de condição inicial dos ramos, de onde
    :meth:`Inductor.history_current_A` e
    :meth:`Capacitor.history_current_A` produzem exatamente
    ``I_L(0) = i_L(0) + G_L·v_L(0)`` e ``I_C(0) = −[G_C·v_C(0) + i_C(0)]``.

    A linha de Bergeron recebe o preenchimento do buffer de histórico com
    a ONDA DE REGIME ao longo de todo o tempo de trânsito ``τ`` — sem
    isso os primeiros ``τ/Δt`` passos veriam histórico nulo e a linha
    injetaria um degrau espúrio.

    Returns
    -------
    dict
        Mapa ``nome do ramo → valores instantâneos semeados em t = 0``,
        para auditoria: ``(i, v)`` para indutor e ``CoupledRL``,
        ``(v, i)`` para capacitor, ``(v_k, i_km, v_m, i_mk)`` para linha.
    """
    dt_f = float(dt)
    if not math.isfinite(dt_f) or dt_f <= 0.0:
        raise SteadyStateError(f"dt deve ser finito e > 0, obtido {dt!r}")
    omega = solution.omega_rad_s
    report: dict[str, tuple[float, ...]] = {}

    for comp in circuit.components:
        pairs = solution.branch_phasors.get(comp.name)
        if pairs is None:  # pragma: no cover - defensivo
            raise SteadyStateError(f"ramo {comp.name!r} ausente da solução fasorial")
        if isinstance(comp, Inductor):
            v0 = instantaneous(pairs[0][0], omega, 0.0)
            i0 = instantaneous(pairs[0][1], omega, 0.0)
            comp.initial_current_A = i0
            comp.initial_voltage_V = v0
            comp.reset()
            report[comp.name] = (i0, v0)
        elif isinstance(comp, Capacitor):
            v0 = instantaneous(pairs[0][0], omega, 0.0)
            i0 = instantaneous(pairs[0][1], omega, 0.0)
            comp.initial_voltage_V = v0
            comp.initial_current_A = i0
            comp.reset()
            report[comp.name] = (v0, i0)
        elif isinstance(comp, CoupledRL):
            i_vec = np.array(
                [instantaneous(p[1], omega, 0.0) for p in pairs], dtype=float
            )
            v_vec = np.array(
                [instantaneous(p[0], omega, 0.0) for p in pairs], dtype=float
            )
            comp.set_initial_state(current_A=i_vec, voltage_V=v_vec)
            comp.reset()
            report[comp.name] = tuple(i_vec) + tuple(v_vec)
        elif isinstance(comp, BergeronLine):
            comp.seed_steady_state(
                v_k=pairs[0][0],
                i_km=pairs[0][1],
                v_m=pairs[1][0],
                i_mk=pairs[1][1],
                omega_rad_s=omega,
                dt=dt_f,
            )
            report[comp.name] = (
                instantaneous(pairs[0][0], omega, 0.0),
                instantaneous(pairs[0][1], omega, 0.0),
                instantaneous(pairs[1][0], omega, 0.0),
                instantaneous(pairs[1][1], omega, 0.0),
            )
        else:
            # Ramos algébricos (resistor, fonte, chave): não têm histórico,
            # mas as leituras branch_voltage/branch_current devem valer o
            # regime permanente já em t = 0, porque é sobre ELAS que os
            # controladores decidem a manobra no primeiro passo — inclusive
            # o critério de margem de corrente Imar [LISTA: 02, §1.3].
            comp.reset()
            v0 = instantaneous(pairs[0][0], omega, 0.0)
            i0 = instantaneous(pairs[0][1], omega, 0.0)
            comp._v = v0  # noqa: SLF001
            if not isinstance(comp, Resistor):
                # O resistor deriva a corrente da tensão (i = G·v); os
                # demais (fonte e chave) guardam a incógnita de corrente
                # do MNA, que precisa ser imposta.
                comp._i = i0  # noqa: SLF001
            report[comp.name] = (v0, i0)
    return report


def initialize_steady_state(
    circuit: Circuit, dt: float, *, frequency_Hz: float | None = None
) -> PhasorSolution:
    """Resolve o fasor e semeia o circuito — ponto de entrada do módulo.

    Equivale ao ``TSTART`` negativo do cartão de fonte do ATP: o circuito
    é resolvido em regime permanente na topologia corrente das chaves e
    os históricos entram na marcha no tempo já carregados
    [LISTA: 02, §1.4 e §3.6].

    Parameters
    ----------
    circuit:
        Circuito montado; ``build()`` e ``prepare(dt)`` são garantidos.
    dt:
        Passo da marcha no tempo [s] — necessário para o buffer de
        histórico da linha de Bergeron.
    frequency_Hz:
        Frequência imposta; ``None`` (padrão) detecta das fontes.

    Returns
    -------
    PhasorSolution
        Solução usada na semeadura, para auditoria e comparação.
    """
    circuit.build()
    circuit.prepare(dt)
    solution = solve_phasor(circuit, frequency_Hz=frequency_Hz)
    seed_from_phasor(circuit, solution, dt)
    return solution


__all__ = [
    "INIT_ZERO",
    "INIT_STEADY_STATE",
    "INIT_MODES",
    "FREQUENCY_TOLERANCE",
    "PHASOR_CONDITION_LIMIT",
    "SteadyStateError",
    "MultipleFrequenciesError",
    "UnsupportedComponentError",
    "PhasorSolution",
    "instantaneous",
    "source_phasor",
    "source_frequency",
    "assemble_phasor_system",
    "solve_phasor",
    "seed_from_phasor",
    "initialize_steady_state",
]
