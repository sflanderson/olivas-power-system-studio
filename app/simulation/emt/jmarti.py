"""
app.simulation.emt.jmarti — linha/cabo com DEPENDÊNCIA DE FREQUÊNCIA
(modelo de J. R. Martí) para o motor EMT dedicado.

Posição no pacote
==================

Este módulo é o par de :mod:`app.simulation.emt.line`, que implementa a
linha a parâmetros constantes (Bergeron). A interface de componente é a
MESMA — mesma classe base :class:`~app.simulation.emt.components.Component`,
mesmos ``stamp_matrix``/``stamp_rhs``/``commit``, mesmas
``branch_voltage``/``branch_current`` com ``index = 0`` para o terminal
``k`` e ``1`` para o terminal ``m`` —, de modo que um caso troca de
modelo por um único parâmetro, sem mudar mais nada do circuito.

Fonte do método e o que foi possível verificar
===============================================

O método é o de [LITERATURA: J. R. Martí, "Accurate modelling of
frequency-dependent transmission lines in electromagnetic transient
simulations", *IEEE Trans. PAS*, vol. PAS-101, n. 1, pp. 147-157, jan.
1982, doi:10.1109/TPAS.1982.317332]. **O texto integral do artigo NÃO
esteve disponível nesta sessão**; a formulação abaixo foi montada a
partir de fontes secundárias efetivamente acessadas e conferida contra
o limite sem perdas de Dommel, que é conhecido linha a linha. As URLs
consultadas em 3 set. 2026 foram:

* https://www.intechopen.com/chapters/39330 — L. Faria da Silva et al.
  (IntechOpen), "An advanced transmission line and cable model in
  Matlab…": fatoração ``e^{−γ_i ℓ} = e^{−γ̃_i ℓ}·e^{−sτ_i}`` (parte de
  fase mínima × atraso puro), delays estimados "via Bode's relation for
  minimum phase complex functions", decomposição modal ``H = M H_m
  M^{−1}`` e recursão ``a_{k,i} = (2 + Δt·p_{k,i})/(2 − Δt·p_{k,i})``.
* https://colib.net/models/6-NetworkComponents/Line/FDLine/ — funções de
  onda progressiva/regressiva ``f_S(t) = v_S(t) + e_S(t)``,
  ``b_S(t) = v_S(t) − e_S(t)`` com ``e_S(t) = i_S(t) ∗ Z_C(t)``, e a
  relação ``B_S(ω) = A_1(ω)·F_R(ω)`` com ``A_1 = e^{−γ(ω)ℓ}``.
* https://www.pscad.com/webhelp/EMTDC/Transmission_Lines/Frequency_Dependent_Models.htm
* https://www.sintef.no/en/software/vector-fitting/ — implementação de
  referência do *vector fitting*.

Os NÚMEROS DE EQUAÇÃO e de PÁGINA do artigo de 1982 não puderam ser
conferidos e aparecem como [INSERIR CITAÇÃO] onde seriam devidos. Nada
foi atribuído ao artigo sem lastro em fonte acessada.

Formulação
===========

Para uma linha uniforme de comprimento ``ℓ``, com impedância série
``z(ω)`` e admitância derivação ``y(ω)`` por unidade de comprimento::

    γ(ω) = sqrt(z·y) = α(ω) + jβ(ω)        (constante de propagação)
    Z_c(ω) = sqrt(z/y)                     (impedância característica)
    A(ω) = e^{−γ(ω)·ℓ}                     (função de propagação)

Definem-se, em cada terminal, as funções de onda [FONTE acessada:
colib.net/models/…/FDLine]::

    F_k(t) = v_k(t) + z_c ∗ i_k(t)         (onda que PARTE de k)
    B_k(t) = v_k(t) − z_c ∗ i_k(t)         (onda que CHEGA a k)

com ``i_k`` ENTRANDO na linha pelo terminal ``k`` — a mesma convenção de
:class:`~app.simulation.emt.line.BergeronLine`. A onda que parte de um
terminal chega ao outro filtrada por ``A``::

    B_k(ω) = A(ω)·F_m(ω)        B_m(ω) = A(ω)·F_k(ω)

De ``F = 2v − B`` (identidade imediata das duas definições) resulta que
``F`` NÃO exige convolução com ``z_c``: basta a tensão nodal e a onda
que chega, ambas conhecidas ao fim do passo. Esse é o artifício que
torna o modelo executável — [INSERIR CITAÇÃO] para a equação
correspondente em Martí 1982.

A corrente terminal sai de ``i_k = y_c ∗ (v_k − B_k)``, com
``y_c = 1/Z_c``. Realizando ``y_c`` como função racional
``Y_c(s) = d + Σ_i k_i/(s − p_i)`` e integrando cada termo por recursão
exponencial, cada parcela vira ``y_i(t) = α_i·y_i(t−h) + c1_i·x(t) +
c2_i·x(t−h)``, de modo que::

    i_k(t) = G·v_k(t) + I_hist,k(t)
    G      = d + Σ_i w_i·Re(c1_i)                       (constante)
    I_hist,k(t) = −G·B_k(t) + Σ_i w_i·Re[α_i·y_i(t−h) + c2_i·x(t−h)]

isto é, EXATAMENTE a mesma estampagem do Bergeron — condutância só na
diagonal do próprio terminal e uma fonte de corrente de histórico —,
que é o motivo pelo qual a linha continua "partindo" a matriz do
sistema em blocos [FONTE: Dommel 1969, §I, p. 389].

O atraso é extraído de ``A`` e tratado à parte::

    A(ω) = A_min(ω) · e^{−jωτ}

``A_min`` é de FASE MÍNIMA e é o que se ajusta em função racional;
``e^{−jωτ}`` vira um deslocamento no buffer de histórico, com
interpolação linear quando ``τ`` não é múltiplo inteiro de ``Δt`` —
mesma escolha e mesma justificativa do Bergeron [FONTE: Dommel 1969,
"Accuracy", p. 391].

Ajuste racional: por que *vector fitting*
==========================================

O artigo de 1982 ajusta o MÓDULO por assíntotas de Bode e reconstrói a
fase pela relação de fase mínima. Aqui a rotina PADRÃO é o *vector
fitting* [LITERATURA: B. Gustavsen, A. Semlyen, "Rational approximation
of frequency domain responses by vector fitting", *IEEE Trans. Power
Delivery*, vol. 14, n. 3, pp. 1052-1061, jul. 1999; implementação de
referência em https://www.sintef.no/en/software/vector-fitting/].
Justificativa da escolha, declarada como exige o autor:

1. o *vector fitting* ajusta módulo E fase simultaneamente, por mínimos
   quadrados LINEARES iterados sobre um deslocamento de polos, sem a
   etapa heurística de traçado de assíntotas;
2. admite pares complexos conjugados, necessários para ``A_min`` de
   cabos, enquanto o traçado de Bode clássico produz apenas polos e
   zeros reais;
3. o erro de ajuste é uma saída natural do próprio método e pode ser
   comparado a uma tolerância declarada — requisito de auditoria deste
   repositório;
4. dispensa ``scipy`` (apenas ``numpy.linalg``), que não é dependência
   do projeto.

A maquinaria de FASE MÍNIMA não foi abandonada: ela é o que extrai o
atraso ``τ`` (:func:`minimum_phase_angle`, :func:`estimate_time_delay`)
e serve de instrumento de auditoria do ajuste, exatamente como em
Martí — a fatoração ``e^{−γℓ} = e^{−γ̃ℓ}·e^{−sτ}`` com "delays
estimated via Bode's relation for minimum phase complex functions"
[FONTE acessada: intechopen.com/chapters/39330].

Discretização: por que recursão exponencial "híbrida"
======================================================

A recursão por polo poderia ser trapezoidal, ``α = (2 + pΔt)/(2 − pΔt)``
[FONTE acessada: intechopen.com/chapters/39330]. Não é o que se faz
aqui, e a razão é numérica: os polos rápidos de ``Y_c`` e de ``A_min``
de um cabo chegam a ``|p| ~ 10^7 rad/s``; com ``Δt = 1 µs`` isso dá
``pΔt ≈ −10``, ``α ≈ −0,67`` — oscilação numérica alternada de período
``2Δt``, a MESMA patologia que o CDA existe para eliminar [FONTE: Lin &
Martí 1990, §2, p. 394].

Adota-se então [CÁLCULO PRÓPRIO], sobre a ideia de convolução recursiva
por exponenciais de [LITERATURA: A. Semlyen, A. Dabuleanu, "Fast and
accurate switching transient calculations on transmission lines with
ground return using recursive convolutions", *IEEE Trans. PAS*, vol.
PAS-94, n. 2, pp. 561-571, mar./abr. 1975]::

    α_i(h) = e^{p_i·h}                        (decaimento EXATO)
    c1_i   = k_i·Δt/(2 − p_i·Δt)              (parcela instantânea)
    c2_i(h) = k_i·(e^{p_i·h} − 1)/p_i − c1_i  (fecha o ganho do passo)

Três propriedades, todas verificadas em ``tests/test_emt_jmarti.py``:

* **estabilidade incondicional**: ``|α| < 1`` para todo ``Re(p) < 0`` e
  todo ``h``, sem o polo discreto ``z → −1`` do trapézio;
* **ganho de regime exato**: ``c1 + c2 = k(e^{ph} − 1)/p`` é a integral
  exata do passo com entrada constante, logo o valor final é ``−k/p``
  sem erro;
* **compatibilidade com o CDA**: ``c1`` depende de ``Δt``, NÃO de ``h``,
  e ``k·Δt/(2 − pΔt)`` é ao mesmo tempo o coeficiente instantâneo do
  trapézio com passo ``Δt`` e o do Euler regressivo com ``h = Δt/2``.
  É a mesma coincidência que torna ``G_L = Δt/2L`` válida nos dois modos
  [FONTE: Lin & Martí 1990, §2, p. 394] e a razão pela qual **a matriz
  do sistema não muda nos meios-passos do CDA** — sem isso o cache de
  fatoração de :mod:`app.simulation.emt.circuit` estamparia uma matriz
  errada, porque ``_sync_topology`` não é reavaliado entre os dois
  meios-passos.

Para ``|pΔt| ≪ 1`` o esquema coincide com o trapezoidal até
``O(Δt²)`` [CÁLCULO PRÓPRIO: expansão em série de ``c1`` e ``c2``]; para
``|pΔt| ≫ 1`` degenera em ganho estático sem oscilação, que é o
comportamento fisicamente correto de um polo cuja constante de tempo é
muito menor que o passo.

Entrada de dados: o ``.atp`` continua sendo a fonte da verdade
===============================================================

Por decisão de projeto, o caminho PRIMÁRIO de entrada são **tabelas
amostradas** de ``Z_c(ω)`` e ``A(ω)`` (:class:`LineFrequencyData`), que
podem vir do cálculo de parâmetros de linha/cabo do próprio caso ATP
(``LINE CONSTANTS`` / ``CABLE CONSTANTS``). Isso separa o problema de
*line constants* — geometria, efeito pelicular, retorno pela terra,
semicondutoras, blindagem — do problema de AJUSTE RACIONAL, que é o que
este módulo resolve. O caminho interno
(:meth:`LineFrequencyData.from_overhead_geometry`) existe para ensaio e
para casos sem dados tabelados, e suas aproximações estão declaradas na
própria docstring.

Limitações declaradas
======================

Ver :data:`JMARTI_LIMITATIONS`, exportado e agregado a
``app.simulation.emt.KNOWN_LIMITATIONS``.

Este módulo é puro: sem I/O, sem GUI, sem estado global, determinístico.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

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


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

#: Permeabilidade magnética do vácuo [H/m].
MU_0: float = 4.0e-7 * math.pi

#: Permissividade elétrica do vácuo [F/m].
EPSILON_0: float = 8.8541878128e-12

#: Tolerância relativa PADRÃO do ajuste racional (RMS de |erro| dividido
#: pelo RMS de |f|). Valor conservador para uso em estudo de frente
#: rápida; o ajuste que não a atender levanta :class:`RationalFitError`.
DEFAULT_FIT_TOLERANCE: float = 2.0e-2

#: Número padrão de iterações de deslocamento de polos do *vector fitting*.
DEFAULT_FIT_ITERATIONS: int = 10

#: Pesos aceitos por :func:`vector_fit`.
FIT_WEIGHTS: tuple[str, ...] = ("none", "inverse", "sqrt_inverse")

#: Métodos aceitos por :func:`estimate_time_delay`.
DELAY_METHODS: tuple[str, ...] = ("minimum_phase", "phase_slope")

#: Piso relativo aplicado ao módulo antes do logaritmo em
#: :func:`minimum_phase_angle` (evita ``ln 0`` em ``ω → 0``).
MAGNITUDE_FLOOR_RATIO: float = 1.0e-12


# ---------------------------------------------------------------------------
# Erros
# ---------------------------------------------------------------------------


class JMartiError(ValueError):
    """Erro de base do modelo dependente da frequência."""


class LineDataError(JMartiError):
    """Tabelas de ``Z_c(ω)`` / ``A(ω)`` ausentes, insuficientes ou inválidas."""


class RationalFitError(JMartiError):
    """O ajuste racional não atingiu a tolerância declarada."""


# ---------------------------------------------------------------------------
# Auxiliares numéricos
# ---------------------------------------------------------------------------


def _expm1_over(z: np.ndarray) -> np.ndarray:
    """``(e^z − 1)/z`` estável para ``|z| → 0``, com ``z`` complexo.

    ``numpy.expm1`` não aceita argumento complexo; para ``|z|`` pequeno
    usa-se a série ``1 + z/2 + z²/6 + z³/24``, cujo erro relativo é
    inferior a ``|z|⁴/120`` — abaixo de ``1e−17`` no corte adotado
    [CÁLCULO PRÓPRIO].
    """
    z = np.asarray(z, dtype=complex)
    out = np.empty_like(z)
    small = np.abs(z) < 1.0e-4
    zs = z[small]
    out[small] = 1.0 + zs / 2.0 + zs * zs / 6.0 + zs * zs * zs / 24.0
    zb = z[~small]
    out[~small] = (np.exp(zb) - 1.0) / zb
    return out


def _as_omega(omega: Sequence[float] | np.ndarray, label: str = "omega") -> np.ndarray:
    """Valida e devolve o vetor de frequências angulares [rad/s]."""
    w = np.asarray(omega, dtype=float).ravel()
    if w.size < 2:
        raise LineDataError(f"{label} precisa de ao menos 2 amostras, obtidas {w.size}")
    if not np.all(np.isfinite(w)):
        raise LineDataError(f"{label} contém valores não finitos")
    if np.any(w <= 0.0):
        raise LineDataError(
            f"{label} deve ser estritamente positivo — ω = 0 torna Z_c singular "
            "em linha sem condutância de dispersão"
        )
    if np.any(np.diff(w) <= 0.0):
        raise LineDataError(f"{label} deve ser estritamente crescente")
    return w


def frequency_grid(
    f_min_Hz: float = 1.0e-2, f_max_Hz: float = 1.0e7, n_points: int = 200
) -> np.ndarray:
    """Malha logarítmica de ``ω`` [rad/s] entre ``f_min_Hz`` e ``f_max_Hz``.

    A faixa padrão (0,01 Hz a 10 MHz) cobre desde o regime permanente de
    60 Hz até a frente de reignição de disjuntor a vácuo, cujo conteúdo
    espectral relevante vai a alguns MHz [INFERÊNCIA FÍSICA: ``t_f`` da
    ordem de 0,1 µs ⇒ ``f ≈ 0,35/t_f ≈ 3,5 MHz``].
    """
    fmin = _require_positive(f_min_Hz, "f_min_Hz")
    fmax = _require_positive(f_max_Hz, "f_max_Hz")
    if fmax <= fmin:
        raise ValueError(f"f_max_Hz ({fmax:.6g}) deve ser > f_min_Hz ({fmin:.6g})")
    n = int(n_points)
    if n < 4:
        raise ValueError(f"n_points deve ser >= 4, obtido {n_points!r}")
    return 2.0 * math.pi * np.logspace(math.log10(fmin), math.log10(fmax), n)


def frequency_grid_for_delay(
    travel_time_s: float,
    *,
    f_min_Hz: float = 1.0,
    f_max_Hz: float = 2.0e6,
    safety: float = 2.0,
) -> np.ndarray:
    """Malha logarítmica DENSA o bastante para extrair um atraso ``τ`` conhecido.

    O termo ``e^{−jωτ}`` gira ``ωτ`` radianos; para que
    :func:`estimate_time_delay` não sofra *aliasing* de fase, o giro
    entre amostras vizinhas deve ficar bem abaixo de ``π``. Em malha
    logarítmica o passo é máximo no topo da faixa, onde
    ``Δω ≈ ω_max·ln10/ppd``; exigindo ``τ·Δω <= π/safety`` resulta
    [CÁLCULO PRÓPRIO]::

        ppd >= safety · τ · ω_max · ln10 / π

    Parameters
    ----------
    travel_time_s:
        Estimativa de ``τ`` (por exemplo ``ℓ·sqrt(L'C')``) [s].
    safety:
        Folga sobre o limite de Nyquist de fase; 2 é o padrão.
    """
    tau = _require_positive(travel_time_s, "travel_time_s")
    fmin = _require_positive(f_min_Hz, "f_min_Hz")
    fmax = _require_positive(f_max_Hz, "f_max_Hz")
    saf = _require_positive(safety, "safety")
    if fmax <= fmin:
        raise ValueError(f"f_max_Hz ({fmax:.6g}) deve ser > f_min_Hz ({fmin:.6g})")
    w_max = 2.0 * math.pi * fmax
    ppd = saf * tau * w_max * math.log(10.0) / math.pi
    decades = math.log10(fmax / fmin)
    n = int(math.ceil(max(40.0, ppd) * decades)) + 1
    return frequency_grid(fmin, fmax, max(n, 40))


# ---------------------------------------------------------------------------
# Função racional ajustada
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RationalFit:
    """Aproximação racional ``f(s) ≈ d + Σ_i k_i/(s − p_i)``.

    Os polos vêm em pares complexos conjugados ADJACENTES (``p``,
    ``p*``) ou isolados quando reais, na convenção do *vector fitting*.

    Attributes
    ----------
    poles, residues:
        Vetores complexos de mesmo tamanho (podem ser vazios).
    d:
        Termo constante (valor assintótico em ``ω → ∞``).
    rms_error, max_error:
        Erro RELATIVO do ajuste sobre as amostras: RMS de ``|f̂ − f|``
        dividido pelo RMS de ``|f|``, e máximo de ``|f̂ − f|`` dividido
        pelo máximo de ``|f|``.
    n_iterations:
        Iterações de deslocamento de polos efetivamente executadas.
    flipped_poles:
        Quantos polos instáveis foram refletidos para o semiplano
        esquerdo durante o ajuste.
    """

    poles: np.ndarray
    residues: np.ndarray
    d: float
    rms_error: float = 0.0
    max_error: float = 0.0
    n_iterations: int = 0
    flipped_poles: int = 0

    def __post_init__(self) -> None:
        p = np.asarray(self.poles, dtype=complex).ravel()
        k = np.asarray(self.residues, dtype=complex).ravel()
        if p.size != k.size:
            raise RationalFitError(
                f"polos ({p.size}) e resíduos ({k.size}) em quantidade diferente"
            )
        if p.size and not (np.all(np.isfinite(p)) and np.all(np.isfinite(k))):
            raise RationalFitError("polos ou resíduos não finitos")
        if not math.isfinite(float(self.d)):
            raise RationalFitError("termo constante d não finito")
        object.__setattr__(self, "poles", p)
        object.__setattr__(self, "residues", k)
        object.__setattr__(self, "d", float(self.d))

    @property
    def n_poles(self) -> int:
        """Número de polos do ajuste."""
        return int(self.poles.size)

    def is_stable(self) -> bool:
        """``True`` se TODOS os polos têm parte real estritamente negativa."""
        if self.poles.size == 0:
            return True
        return bool(np.all(self.poles.real < 0.0))

    def evaluate(self, omega: Sequence[float] | np.ndarray) -> np.ndarray:
        """Avalia ``f̂(jω)`` nas frequências dadas."""
        w = np.asarray(omega, dtype=float).ravel()
        s = 1j * w
        out = np.full(s.shape, complex(self.d))
        for p, k in zip(self.poles, self.residues):
            out = out + k / (s - p)
        return out

    def dc_gain(self) -> complex:
        """``f̂(0) = d − Σ k_i/p_i`` — valor assintótico em corrente contínua."""
        out = complex(self.d)
        for p, k in zip(self.poles, self.residues):
            out -= k / p
        return out

    def condensed(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Condensa pares conjugados: devolve ``(p, k, w)``.

        ``w_i = 1`` para polo real e ``2`` para o representante de um par
        conjugado, de modo que ``Σ w_i·Re[k_i/(s − p_i)]`` reproduz a
        soma completa quando ``s = jω`` — o que permite propagar UM
        estado complexo por par em vez de dois.
        """
        return _condense_conjugates(self.poles, self.residues)


def _condense_conjugates(
    poles: np.ndarray, residues: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Agrupa pares conjugados adjacentes; ver :meth:`RationalFit.condensed`."""
    p = np.asarray(poles, dtype=complex).ravel()
    k = np.asarray(residues, dtype=complex).ravel()
    out_p: list[complex] = []
    out_k: list[complex] = []
    out_w: list[float] = []
    i = 0
    n = p.size
    while i < n:
        pi = p[i]
        if abs(pi.imag) <= 1.0e-12 * max(abs(pi), 1.0):
            out_p.append(complex(pi.real, 0.0))
            out_k.append(complex(k[i].real, 0.0))
            out_w.append(1.0)
            i += 1
            continue
        if i + 1 >= n or abs(p[i + 1] - np.conj(pi)) > 1.0e-6 * abs(pi):
            raise RationalFitError(
                f"polo complexo {pi!r} sem conjugado adjacente — o ajuste não "
                "produz resposta real no tempo"
            )
        out_p.append(complex(pi))
        out_k.append(complex(k[i]))
        out_w.append(2.0)
        i += 2
    return (
        np.asarray(out_p, dtype=complex),
        np.asarray(out_k, dtype=complex),
        np.asarray(out_w, dtype=float),
    )


# ---------------------------------------------------------------------------
# Vector fitting
# ---------------------------------------------------------------------------


def initial_poles(omega: np.ndarray, n_poles: int) -> np.ndarray:
    """Polos de partida: pares conjugados com ``Re = −Im/100``.

    Recomendação do próprio *vector fitting* para funções suaves em
    escala logarítmica [LITERATURA: Gustavsen & Semlyen 1999, §III;
    implementação de referência da SINTEF]. Com ``n_poles`` ímpar o
    primeiro polo é REAL, no início da faixa.
    """
    w = _as_omega(omega)
    n = int(n_poles)
    if n < 0:
        raise RationalFitError(f"n_poles deve ser >= 0, obtido {n_poles!r}")
    if n == 0:
        return np.zeros(0, dtype=complex)
    poles: list[complex] = []
    n_pairs = n // 2
    if n % 2 == 1:
        poles.append(complex(-w[0], 0.0))
    if n_pairs:
        beta = np.logspace(math.log10(w[0]), math.log10(w[-1]), n_pairs)
        for b in beta:
            poles.append(complex(-b / 100.0, b))
            poles.append(complex(-b / 100.0, -b))
    return np.asarray(poles, dtype=complex)


def _basis(s: np.ndarray, poles: np.ndarray) -> np.ndarray:
    """Base real do *vector fitting* avaliada em ``s`` (colunas complexas).

    Para polo real: coluna ``1/(s − p)``. Para par conjugado, DUAS
    colunas — ``1/(s−p) + 1/(s−p*)`` e ``j/(s−p) − j/(s−p*)`` — de modo
    que os coeficientes procurados sejam REAIS e o resíduo do par seja
    ``k = x_re + j·x_im`` [LITERATURA: Gustavsen & Semlyen 1999, §II-B].
    """
    n = poles.size
    cols = np.empty((s.size, n), dtype=complex)
    i = 0
    while i < n:
        p = poles[i]
        if abs(p.imag) <= 1.0e-14 * max(abs(p), 1.0):
            cols[:, i] = 1.0 / (s - p)
            i += 1
            continue
        q1 = 1.0 / (s - p)
        q2 = 1.0 / (s - np.conj(p))
        cols[:, i] = q1 + q2
        cols[:, i + 1] = 1j * (q1 - q2)
        i += 2
    return cols


def _residues_from_real(poles: np.ndarray, xr: np.ndarray) -> np.ndarray:
    """Converte os coeficientes reais da base em resíduos complexos."""
    n = poles.size
    k = np.zeros(n, dtype=complex)
    i = 0
    while i < n:
        p = poles[i]
        if abs(p.imag) <= 1.0e-14 * max(abs(p), 1.0):
            k[i] = complex(xr[i], 0.0)
            i += 1
            continue
        k[i] = complex(xr[i], xr[i + 1])
        k[i + 1] = np.conj(k[i])
        i += 2
    return k


def _new_poles(poles: np.ndarray, sigma_r: np.ndarray) -> np.ndarray:
    """Zeros de ``σ(s)`` = novos polos, por autovalores de ``A − b·c̃ᵀ``.

    Forma real de [LITERATURA: Gustavsen & Semlyen 1999, eq. (10)]: o
    par conjugado entra como bloco ``[[Re, Im], [−Im, Re]]`` com
    ``b = (2, 0)ᵀ``.
    """
    n = poles.size
    A = np.zeros((n, n), dtype=float)
    b = np.zeros(n, dtype=float)
    i = 0
    while i < n:
        p = poles[i]
        if abs(p.imag) <= 1.0e-14 * max(abs(p), 1.0):
            A[i, i] = p.real
            b[i] = 1.0
            i += 1
            continue
        A[i, i] = p.real
        A[i, i + 1] = p.imag
        A[i + 1, i] = -p.imag
        A[i + 1, i + 1] = p.real
        b[i] = 2.0
        b[i + 1] = 0.0
        i += 2
    H = A - np.outer(b, np.asarray(sigma_r, dtype=float))
    return np.linalg.eigvals(H).astype(complex)


def _sort_poles(poles: np.ndarray) -> np.ndarray:
    """Ordena polos deixando cada par conjugado adjacente (``+Im`` antes)."""
    reals = sorted((p for p in poles if abs(p.imag) <= 1.0e-12 * max(abs(p), 1.0)),
                   key=lambda z: z.real)
    complexes = [p for p in poles if abs(p.imag) > 1.0e-12 * max(abs(p), 1.0)]
    complexes.sort(key=lambda z: (abs(z.imag), z.real))
    out: list[complex] = [complex(p.real, 0.0) for p in reals]
    used = [False] * len(complexes)
    for i, p in enumerate(complexes):
        if used[i]:
            continue
        used[i] = True
        partner = None
        for j in range(i + 1, len(complexes)):
            if used[j]:
                continue
            if abs(complexes[j] - np.conj(p)) <= 1.0e-6 * max(abs(p), 1.0):
                partner = j
                break
        if partner is None:
            # Sem parceiro: força o par pela própria conjugação.
            out.append(complex(p.real, abs(p.imag)))
            out.append(complex(p.real, -abs(p.imag)))
            continue
        used[partner] = True
        q = complex(p.real, abs(p.imag))
        out.append(q)
        out.append(np.conj(q))
    return np.asarray(out, dtype=complex)


def _weights(values: np.ndarray, weight: str | np.ndarray) -> np.ndarray:
    """Pesos do problema de mínimos quadrados."""
    if isinstance(weight, str):
        if weight not in FIT_WEIGHTS:
            raise RationalFitError(
                f"weight deve ser um de {FIT_WEIGHTS} ou um vetor, obtido {weight!r}"
            )
        mag = np.abs(values)
        floor = max(float(np.max(mag)) * 1.0e-12, 1.0e-300)
        mag = np.maximum(mag, floor)
        if weight == "none":
            return np.ones_like(mag)
        if weight == "inverse":
            return 1.0 / mag
        return 1.0 / np.sqrt(mag)
    w = np.asarray(weight, dtype=float).ravel()
    if w.size != values.size:
        raise RationalFitError(
            f"vetor de pesos com {w.size} amostras, esperado {values.size}"
        )
    if np.any(w <= 0.0) or not np.all(np.isfinite(w)):
        raise RationalFitError("pesos devem ser finitos e > 0")
    return w


def _fit_errors(fitted: np.ndarray, values: np.ndarray) -> tuple[float, float]:
    """Erros relativos RMS e máximo do ajuste."""
    err = np.abs(fitted - values)
    ref_rms = float(np.sqrt(np.mean(np.abs(values) ** 2)))
    ref_max = float(np.max(np.abs(values)))
    rms = float(np.sqrt(np.mean(err**2)))
    mx = float(np.max(err))
    if ref_rms <= 0.0 or ref_max <= 0.0:  # pragma: no cover - defensivo
        return rms, mx
    return rms / ref_rms, mx / ref_max


def vector_fit(
    omega: Sequence[float] | np.ndarray,
    values: Sequence[complex] | np.ndarray,
    *,
    n_poles: int = 8,
    n_iterations: int = DEFAULT_FIT_ITERATIONS,
    weight: str | np.ndarray = "inverse",
    include_constant: bool = True,
    enforce_stability: bool = True,
    tolerance: float | None = None,
    label: str = "f",
) -> RationalFit:
    """Ajuste racional por *vector fitting*.

    Implementa o deslocamento iterativo de polos de [LITERATURA:
    Gustavsen & Semlyen 1999]: a cada iteração resolve-se, por mínimos
    quadrados LINEARES,

    ``Σ c_n/(s − a_n) + d − f(s)·Σ c̃_n/(s − a_n) = f(s)``

    e os novos polos são os ZEROS de ``σ(s) = 1 + Σ c̃_n/(s − a_n)``,
    obtidos como autovalores de ``A − b·c̃ᵀ``. Ao fim, os resíduos são
    reajustados com os polos finais.

    Parameters
    ----------
    omega:
        Frequências angulares das amostras [rad/s], crescentes e > 0.
    values:
        Valores complexos ``f(jω)``.
    n_poles:
        Ordem do ajuste; ``0`` reduz o problema ao termo constante.
    n_iterations:
        Iterações de deslocamento de polos (>= 1 quando ``n_poles > 0``).
    weight:
        ``"inverse"`` (padrão, erro RELATIVO — adequado a grandezas que
        variam ordens de grandeza na faixa), ``"sqrt_inverse"``,
        ``"none"`` ou um vetor explícito.
    include_constant:
        Ajusta o termo ``d``; ``False`` força ``d = 0`` (ajuste
        estritamente próprio).
    enforce_stability:
        Reflete polos com ``Re(p) > 0`` para o semiplano esquerdo
        (``p → −Re(p) + j·Im(p)``), procedimento padrão do método.
    tolerance:
        Se dado, levanta :class:`RationalFitError` quando o erro RMS
        relativo o exceder.

    Raises
    ------
    RationalFitError
        Entradas inconsistentes, sistema de mínimos quadrados
        degenerado, ajuste instável com ``enforce_stability=False`` ou
        erro acima de ``tolerance``.
    LineDataError
        ``omega`` inválido.
    """
    w = _as_omega(omega)
    f = np.asarray(values, dtype=complex).ravel()
    if f.size != w.size:
        raise RationalFitError(
            f"{label}: {f.size} amostras de valor para {w.size} de frequência"
        )
    if not np.all(np.isfinite(f)):
        raise RationalFitError(f"{label}: amostras não finitas")
    n = int(n_poles)
    if n < 0:
        raise RationalFitError(f"n_poles deve ser >= 0, obtido {n_poles!r}")
    if n > 0 and n >= w.size:
        raise RationalFitError(
            f"{label}: {n} polos para apenas {w.size} amostras — o sistema de "
            "mínimos quadrados fica subdeterminado; forneça mais pontos de "
            "frequência ou reduza n_poles"
        )
    n_it = int(n_iterations)
    if n > 0 and n_it < 1:
        raise RationalFitError(f"n_iterations deve ser >= 1, obtido {n_iterations!r}")
    wt = _weights(f, weight)
    s = 1j * w

    if n == 0:
        if not include_constant:
            raise RationalFitError(
                f"{label}: n_poles = 0 com include_constant=False descreve a "
                "função identicamente nula"
            )
        # d real que minimiza Σ wt²·|d − f|²  ⇒  média ponderada da parte real.
        d = float(np.sum(wt**2 * f.real) / np.sum(wt**2))
        fit = RationalFit(
            poles=np.zeros(0, dtype=complex),
            residues=np.zeros(0, dtype=complex),
            d=d,
        )
        rms, mx = _fit_errors(fit.evaluate(w), f)
        fit = RationalFit(fit.poles, fit.residues, d, rms, mx, 0, 0)
        _report_fit(label, fit, tolerance)
        return fit

    poles = _sort_poles(initial_poles(w, n))
    flipped = 0
    it_done = 0
    for it in range(n_it):
        it_done = it + 1
        phi = _basis(s, poles)
        n_d = 1 if include_constant else 0
        A = np.empty((w.size, 2 * n + n_d), dtype=complex)
        A[:, :n] = phi
        if include_constant:
            A[:, n] = 1.0
        A[:, n + n_d :] = -phi * f[:, None]
        Ar = np.vstack([A.real, A.imag]) * np.concatenate([wt, wt])[:, None]
        br = np.concatenate([f.real, f.imag]) * np.concatenate([wt, wt])
        try:
            x, *_ = np.linalg.lstsq(Ar, br, rcond=None)
        except np.linalg.LinAlgError as exc:  # pragma: no cover - defensivo
            raise RationalFitError(
                f"{label}: sistema de mínimos quadrados singular na iteração {it}"
            ) from exc
        sigma_r = x[n + n_d :]
        new = _new_poles(poles, sigma_r)
        if not np.all(np.isfinite(new)):
            raise RationalFitError(
                f"{label}: deslocamento de polos divergiu na iteração {it}"
            )
        if enforce_stability:
            unstable = new.real > 0.0
            flipped += int(np.count_nonzero(unstable))
            new = np.where(unstable, -new.real + 1j * new.imag, new)
        poles = _sort_poles(new)

    if enforce_stability:
        # Polos exatamente sobre o eixo (parte real nula) tornam o modelo
        # marginalmente estável: empurra-os para dentro do semiplano.
        margin = 1.0e-9 * float(w[-1])
        touching = poles.real >= -0.0
        if np.any(touching):
            flipped += int(np.count_nonzero(touching))
            poles = np.where(touching, -margin + 1j * poles.imag, poles)
            poles = _sort_poles(poles)

    phi = _basis(s, poles)
    n_d = 1 if include_constant else 0
    A = np.empty((w.size, n + n_d), dtype=complex)
    A[:, :n] = phi
    if include_constant:
        A[:, n] = 1.0
    Ar = np.vstack([A.real, A.imag]) * np.concatenate([wt, wt])[:, None]
    br = np.concatenate([f.real, f.imag]) * np.concatenate([wt, wt])
    x, *_ = np.linalg.lstsq(Ar, br, rcond=None)
    residues = _residues_from_real(poles, x[:n])
    d = float(x[n]) if include_constant else 0.0

    fit = RationalFit(poles, residues, d)
    if not fit.is_stable():
        if enforce_stability:  # pragma: no cover - defensivo
            raise RationalFitError(
                f"{label}: polos instáveis remanescentes após reflexão"
            )
        log.warning("%s: ajuste com polos instáveis (enforce_stability=False)", label)
    rms, mx = _fit_errors(fit.evaluate(w), f)
    fit = RationalFit(poles, residues, d, rms, mx, it_done, flipped)
    _report_fit(label, fit, tolerance)
    return fit


def _report_fit(label: str, fit: RationalFit, tolerance: float | None) -> None:
    """Registra o erro do ajuste em log e aplica a tolerância declarada."""
    log.info(
        "ajuste racional %r: %d polo(s), d = %.6g, erro RMS relativo = %.3e, "
        "erro máximo relativo = %.3e, %d iteração(ões), %d polo(s) refletido(s)",
        label,
        fit.n_poles,
        fit.d,
        fit.rms_error,
        fit.max_error,
        fit.n_iterations,
        fit.flipped_poles,
    )
    if tolerance is None:
        return
    tol = float(tolerance)
    if not math.isfinite(tol) or tol <= 0.0:
        raise RationalFitError(f"tolerance deve ser finita e > 0, obtida {tolerance!r}")
    if fit.rms_error > tol:
        raise RationalFitError(
            f"{label}: erro RMS relativo {fit.rms_error:.3e} acima da tolerância "
            f"declarada {tol:.3e} com {fit.n_poles} polo(s). Aumente n_poles, "
            "estreite a faixa de frequência ou reveja as tabelas de entrada"
        )
    if fit.rms_error > 0.5 * tol:
        log.warning(
            "ajuste racional %r com erro RMS relativo %.3e, acima de metade da "
            "tolerância %.3e — margem estreita",
            label,
            fit.rms_error,
            tol,
        )


# ---------------------------------------------------------------------------
# Fase mínima e extração do atraso
# ---------------------------------------------------------------------------


def minimum_phase_angle(
    omega: Sequence[float] | np.ndarray,
    magnitude: Sequence[float] | np.ndarray,
    *,
    points_per_decade: int = 64,
    pad_decades: float = 6.0,
) -> np.ndarray:
    """Fase de FASE MÍNIMA associada a um módulo amostrado [rad].

    Implementa a **relação de ganho-fase de Bode** na sua forma
    integral em escala logarítmica de frequência::

        φ(ω₀) = (1/π) · ∫_{−∞}^{+∞} (dA/du) · ln|coth(u/2)| du
        A(u) = ln|H|,      u = ln(ω/ω₀)

    [LITERATURA: H. W. Bode, *Network Analysis and Feedback Amplifier
    Design*, Van Nostrand, 1945, cap. XIV]. É a relação que Martí usa
    para separar o atraso puro da parte de fase mínima da função de
    propagação — "delays estimated via Bode's relation for minimum phase
    complex functions" [FONTE acessada:
    https://www.intechopen.com/chapters/39330]; equação correspondente
    em Martí 1982: [INSERIR CITAÇÃO].

    A forma logarítmica é a adequada aqui porque os dados de linha/cabo
    são tabelados em décadas: o núcleo ``ln|coth(u/2)|`` concentra o peso
    em ``|u| < 1`` (a inclinação LOCAL do módulo é o que determina a
    fase) e cai exponencialmente longe da origem.

    Aproximações DECLARADAS:

    * ``ln|H|`` é reamostrado por interpolação linear sobre malha
      uniforme em ``ln ω`` com ``points_per_decade`` pontos por década;
    * fora da faixa tabelada o módulo é EXTRAPOLADO por reta em
      ``ln|H| × ln ω``, com a inclinação assintótica medida nos 20 % de
      amostras de cada extremo, ao longo de ``pad_decades`` décadas de
      cada lado — é a hipótese de comportamento assintótico em lei de
      potência, verdadeira para funções de rede racionais;
    * a singularidade logarítmica do núcleo em ``u = 0`` é integrada
      analiticamente na própria célula: ``∫_{−Δ/2}^{Δ/2} ln(2/|u|) du =
      Δ·[1 + ln(4/Δ)]`` [CÁLCULO PRÓPRIO];
    * o módulo é limitado inferiormente por
      ``MAGNITUDE_FLOOR_RATIO × max|H|`` para evitar ``ln 0``.

    Exatidão medida [CÁLCULO PRÓPRIO, tests/test_emt_jmarti.py]: erro
    inferior a 0,01 rad no interior da faixa para funções racionais de
    primeira e segunda ordem, degradando para algumas centésimas de
    radiano nas amostras extremas, onde a extrapolação domina.

    Returns
    -------
    numpy.ndarray
        Fase [rad] nas MESMAS frequências de ``omega``, negativa para
        módulo decrescente, como convém a sistema de fase mínima.
    """
    w = _as_omega(omega)
    m = np.asarray(magnitude, dtype=float).ravel()
    if m.size != w.size:
        raise LineDataError(
            f"magnitude com {m.size} amostras para {w.size} de frequência"
        )
    if np.any(m <= 0.0) or not np.all(np.isfinite(m)):
        raise LineDataError("magnitude deve ser finita e > 0")
    ppd = int(points_per_decade)
    if ppd < 8:
        raise LineDataError(f"points_per_decade deve ser >= 8, obtido {points_per_decade!r}")
    pad = float(pad_decades)
    if not math.isfinite(pad) or pad < 1.0:
        raise LineDataError(f"pad_decades deve ser >= 1, obtido {pad_decades!r}")
    floor = float(np.max(m)) * MAGNITUDE_FLOOR_RATIO
    ln_w = np.log(w)
    ln_m = np.log(np.maximum(m, floor))
    du = math.log(10.0) / ppd
    lo = ln_w[0] - pad * math.log(10.0)
    hi = ln_w[-1] + pad * math.log(10.0)
    n = int(math.ceil((hi - lo) / du)) + 1
    u = lo + du * np.arange(n)
    n_band = max(2, int(round(0.2 * w.size)))
    slope_lo = float(np.polyfit(ln_w[:n_band], ln_m[:n_band], 1)[0])
    slope_hi = float(np.polyfit(ln_w[-n_band:], ln_m[-n_band:], 1)[0])
    g = np.interp(u, ln_w, ln_m)
    below = u < ln_w[0]
    above = u > ln_w[-1]
    g[below] = ln_m[0] + slope_lo * (u[below] - ln_w[0])
    g[above] = ln_m[-1] + slope_hi * (u[above] - ln_w[-1])
    dg = np.gradient(g, du)
    j = np.arange(-(n - 1), n)
    kernel = np.empty(j.size, dtype=float)
    nz = j != 0
    kernel[nz] = np.log(np.abs(1.0 / np.tanh(j[nz] * du / 2.0))) / math.pi
    kernel[~nz] = (1.0 + math.log(4.0 / du)) / math.pi
    full = np.convolve(dg, kernel[::-1], mode="full") * du
    phi = full[n - 1 : 2 * n - 1]
    return np.interp(ln_w, u, phi)


def estimate_time_delay(
    omega: Sequence[float] | np.ndarray,
    values: Sequence[complex] | np.ndarray,
    *,
    method: str = "minimum_phase",
    band_fraction: float = 0.3,
    points_per_decade: int = 64,
) -> float:
    """Extrai o atraso puro ``τ`` de ``A(ω) = A_min(ω)·e^{−jωτ}`` [s].

    ``method = "minimum_phase"`` (padrão, o de Martí): calcula a fase de
    fase mínima a partir de ``|A|`` pela relação de Bode
    (:func:`minimum_phase_angle`) e ajusta por mínimos quadrados a reta
    ``φ(ω) − φ_min(ω) = −ωτ`` sobre a faixa superior de frequências.
    ``method = "phase_slope"``: ajusta diretamente a inclinação da fase
    desembrulhada na mesma faixa — mais robusto quando o módulo tabelado
    é ruidoso, porém enviesado pela dispersão remanescente (devolve o
    atraso ``ℓ/v(ω_max)`` da borda da faixa, e não o assintótico).

    Parameters
    ----------
    band_fraction:
        Fração SUPERIOR do vetor de frequências usada no ajuste da reta
        (0 < f <= 1). O atraso é uma propriedade de alta frequência.

    Returns
    -------
    float
        ``τ > 0`` [s].

    Raises
    ------
    LineDataError
        Método inválido, faixa vazia ou atraso resultante não positivo
        (tabela incompatível com uma linha causal).
    """
    w = _as_omega(omega)
    a = np.asarray(values, dtype=complex).ravel()
    if a.size != w.size:
        raise LineDataError(f"{a.size} amostras de A para {w.size} de frequência")
    if str(method) not in DELAY_METHODS:
        raise LineDataError(
            f"method deve ser um de {DELAY_METHODS}, obtido {method!r}"
        )
    frac = float(band_fraction)
    if not (0.0 < frac <= 1.0):
        raise LineDataError(f"band_fraction deve estar em (0, 1], obtida {frac!r}")
    phase = np.unwrap(np.angle(a))
    if str(method) == "minimum_phase":
        phase = phase - minimum_phase_angle(
            w, np.abs(a), points_per_decade=points_per_decade
        )
    n_band = max(2, int(round(frac * w.size)))
    ws = w[-n_band:]
    ps = phase[-n_band:]
    # Reta pela origem em (ω, φ): τ = −Σ ω·φ / Σ ω².
    tau = -float(np.sum(ws * ps) / np.sum(ws * ws))
    if not math.isfinite(tau) or tau <= 0.0:
        raise LineDataError(
            f"atraso extraído não positivo (τ = {tau!r}) — verifique se as "
            "amostras de A(ω) correspondem a uma linha causal com o sinal de "
            "fase convencionado (A = e^{−γℓ})"
        )
    # Verificação de ALIASING DE FASE. O termo e^{−jωτ} gira ωτ radianos; se
    # entre duas amostras vizinhas o giro exceder π, numpy.unwrap não tem como
    # recuperar a volta e o τ estimado sai ERRADO (menor que o verdadeiro).
    # Em malha logarítmica o passo é maior justamente no topo da faixa, que é
    # onde o atraso é medido. [CÁLCULO PRÓPRIO: com ℓ = 500 m, f_max = 10 MHz
    # e 43 pontos por década mede-se τ = 1,10 µs contra 1,67 µs corretos; com
    # 86 pontos por década o valor converge.]
    step = tau * float(w[-1] - w[-2])
    if step >= math.pi:
        raise LineDataError(
            f"malha de frequência grosseira demais para extrair o atraso: o "
            f"giro de fase entre as duas últimas amostras é {step:.3g} rad "
            f"(>= π), o que alias a fase e falseia τ. Aumente o número de "
            f"pontos por década para pelo menos "
            f"{math.ceil(step / math.pi * (w.size - 1) / math.log10(w[-1] / w[0]))} "
            f"ou reduza a frequência máxima da tabela"
        )
    if step >= 0.5 * math.pi:
        log.warning(
            "malha de frequência no limite para extração do atraso: giro de "
            "fase de %.3g rad entre as duas últimas amostras (τ = %.6g s); "
            "considere adensar a tabela",
            step,
            tau,
        )
    return tau


# ---------------------------------------------------------------------------
# Tabelas de entrada
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LineFrequencyData:
    """Tabelas amostradas de ``Z_c(ω)`` e ``A(ω)`` de UM modo de propagação.

    É o caminho PRIMÁRIO de entrada do modelo: as tabelas podem vir do
    cálculo de parâmetros do próprio caso ATP (``LINE CONSTANTS`` /
    ``CABLE CONSTANTS``), preservando o ``.atp`` como fonte da verdade.

    Attributes
    ----------
    omega:
        Frequências angulares [rad/s], estritamente crescentes e > 0.
    z_c:
        ``Z_c(jω)`` [Ω], complexo, não nulo.
    a:
        ``A(jω) = e^{−γ(ω)ℓ}``, complexo, com ``0 < |A| <= 1``.
    length_m:
        Comprimento [m], opcional, só para registro/auditoria.
    label:
        Rótulo para mensagens de log.

    Raises
    ------
    LineDataError
        Vetores de tamanhos distintos, com menos de 4 amostras, não
        finitos, ``ω`` não crescente ou não positivo, ``Z_c`` nulo,
        ``A`` nulo. ``|A| > 1`` (ganho de propagação — linha ativa) é
        registrado como ``WARNING`` e tolerado até 1 %, além disso é
        erro.
    """

    omega: np.ndarray
    z_c: np.ndarray
    a: np.ndarray
    length_m: float | None = None
    label: str = "linha"

    def __post_init__(self) -> None:
        w = _as_omega(self.omega, "omega")
        zc = np.asarray(self.z_c, dtype=complex).ravel()
        aa = np.asarray(self.a, dtype=complex).ravel()
        if zc.size != w.size or aa.size != w.size:
            raise LineDataError(
                f"{self.label}: tabelas de tamanhos distintos — ω {w.size}, "
                f"Z_c {zc.size}, A {aa.size}"
            )
        if w.size < 4:
            raise LineDataError(
                f"{self.label}: {w.size} amostras é insuficiente para ajuste "
                "racional; forneça ao menos 4 (na prática, dezenas por década)"
            )
        if not (np.all(np.isfinite(zc)) and np.all(np.isfinite(aa))):
            raise LineDataError(f"{self.label}: tabelas com valores não finitos")
        if np.any(np.abs(zc) <= 0.0):
            raise LineDataError(f"{self.label}: Z_c nula em alguma frequência")
        if np.any(np.abs(aa) <= 0.0):
            raise LineDataError(f"{self.label}: A nula em alguma frequência")
        mag_max = float(np.max(np.abs(aa)))
        if mag_max > 1.01:
            raise LineDataError(
                f"{self.label}: |A| = {mag_max:.4g} > 1 — função de propagação "
                "com ganho, o que descreve linha ATIVA; verifique o sinal do "
                "expoente (A = e^{−γℓ})"
            )
        if mag_max > 1.0 + 1.0e-9:
            log.warning(
                "%s: |A| máximo = %.6g ligeiramente acima de 1 (%.2e); tolerado "
                "como erro de tabulação",
                self.label,
                mag_max,
                mag_max - 1.0,
            )
        if self.length_m is not None:
            _require_positive(self.length_m, "length_m")
        object.__setattr__(self, "omega", w)
        object.__setattr__(self, "z_c", zc)
        object.__setattr__(self, "a", aa)

    @property
    def n_samples(self) -> int:
        """Número de amostras de frequência."""
        return int(self.omega.size)

    @property
    def y_c(self) -> np.ndarray:
        """``Y_c(jω) = 1/Z_c(jω)`` [S]."""
        return 1.0 / self.z_c

    # -- construtores -------------------------------------------------------

    @classmethod
    def from_series_shunt(
        cls,
        omega: Sequence[float] | np.ndarray,
        z_series_per_m: Sequence[complex] | np.ndarray,
        y_shunt_per_m: Sequence[complex] | np.ndarray,
        *,
        length_m: float,
        label: str = "linha",
    ) -> "LineFrequencyData":
        """Constrói as tabelas a partir de ``z(ω)`` e ``y(ω)`` por metro.

        ``γ = sqrt(z·y)`` com o ramo de parte real NÃO negativa (onda que
        se atenua ao propagar), ``Z_c = sqrt(z/y)`` e ``A = e^{−γℓ}``.
        """
        w = _as_omega(omega)
        z = np.asarray(z_series_per_m, dtype=complex).ravel()
        y = np.asarray(y_shunt_per_m, dtype=complex).ravel()
        if z.size != w.size or y.size != w.size:
            raise LineDataError(
                f"{label}: z ({z.size}) e y ({y.size}) devem ter {w.size} amostras"
            )
        if np.any(np.abs(y) <= 0.0):
            raise LineDataError(f"{label}: admitância derivação nula")
        ell = _require_positive(length_m, "length_m")
        gamma = np.sqrt(z * y)
        gamma = np.where(gamma.real < 0.0, -gamma, gamma)
        zc = np.sqrt(z / y)
        zc = np.where(zc.real < 0.0, -zc, zc)
        return cls(w, zc, np.exp(-gamma * ell), length_m=ell, label=label)

    @classmethod
    def from_constant_parameters(
        cls,
        *,
        surge_impedance_ohm: float,
        travel_time_s: float,
        omega: Sequence[float] | np.ndarray | None = None,
        label: str = "linha CP",
    ) -> "LineFrequencyData":
        """Tabelas da linha SEM dependência de frequência (referência).

        ``Z_c`` constante e ``A = e^{−jωτ}``. É o caso em que o modelo
        deve reproduzir o Bergeron sem perdas — o teste de consistência
        mais importante do módulo.
        """
        zc = _require_positive(surge_impedance_ohm, "surge_impedance_ohm")
        tau = _require_positive(travel_time_s, "travel_time_s")
        w = _as_omega(omega) if omega is not None else frequency_grid()
        return cls(
            w,
            np.full(w.size, complex(zc)),
            np.exp(-1j * w * tau),
            label=label,
        )

    @classmethod
    def from_distributed_parameters(
        cls,
        *,
        length_m: float,
        inductance_H_per_m: float,
        capacitance_F_per_m: float,
        resistance_ohm_per_m: float = 0.0,
        conductance_S_per_m: float = 0.0,
        omega: Sequence[float] | np.ndarray | None = None,
        label: str = "linha RLGC",
    ) -> "LineFrequencyData":
        """Tabelas de uma linha ``R'L'G'C'`` com parâmetros CONSTANTES.

        Note-se que, mesmo com ``R'`` constante, ``Z_c`` e ``A``
        DEPENDEM da frequência: é a dependência de uma linha com perdas
        sem efeito pelicular. Com ``R' = G' = 0`` recai-se na linha sem
        perdas, com ``Z_c = sqrt(L'/C')`` e ``A = e^{−jωτ}`` exatos.
        """
        ell = _require_positive(length_m, "length_m")
        lp = _require_positive(inductance_H_per_m, "inductance_H_per_m")
        cp = _require_positive(capacitance_F_per_m, "capacitance_F_per_m")
        rp = _require_non_negative(resistance_ohm_per_m, "resistance_ohm_per_m")
        gp = _require_non_negative(conductance_S_per_m, "conductance_S_per_m")
        w = _as_omega(omega) if omega is not None else frequency_grid()
        if rp == 0.0 and gp == 0.0:
            zc = np.full(w.size, complex(math.sqrt(lp / cp)))
            tau = ell * math.sqrt(lp * cp)
            return cls(w, zc, np.exp(-1j * w * tau), length_m=ell, label=label)
        z = rp + 1j * w * lp
        y = gp + 1j * w * cp
        return cls.from_series_shunt(w, z, y, length_m=ell, label=label)

    @classmethod
    def from_overhead_geometry(
        cls,
        *,
        length_m: float,
        radius_m: float,
        height_m: float,
        conductor_resistivity_ohm_m: float = 2.8264e-8,
        earth_resistivity_ohm_m: float = 100.0,
        relative_permeability: float = 1.0,
        omega: Sequence[float] | np.ndarray | None = None,
        label: str = "condutor aéreo",
    ) -> "LineFrequencyData":
        """Caminho INTERNO de cálculo a partir da geometria, com aproximações declaradas.

        Condutor cilíndrico único sobre solo homogêneo. **Não substitui
        o cálculo de parâmetros do ATP**; existe para ensaio e para casos
        sem dados tabelados.

        Aproximações, TODAS declaradas:

        1. **Efeito pelicular** por interpolação assintótica
           ``Z_int(ω) = R_cc·sqrt(1 + jω/ω_s)`` com
           ``ω_s = 8·ρ_c/(µ·r²)``. [CÁLCULO PRÓPRIO] Essa escolha de
           ``ω_s`` faz a expressão coincidir EXATAMENTE com ``R_cc`` em
           corrente contínua e com a assíntota exata de alta frequência
           ``R = sqrt(ωµ/(8σ))/(π r)``, que é ``1/(σ·2πr·δ)`` com
           ``δ = sqrt(2/(ωµσ))``. Entre as duas assíntotas a curva é
           aproximada — a solução exata envolve funções de Bessel
           [LITERATURA: J. R. Carson, "Wave propagation in overhead
           wires with ground return", *Bell System Technical Journal*,
           v. 5, 1926].
        2. **Retorno pela terra** pelo plano de retorno de PROFUNDIDADE
           COMPLEXA ``p = sqrt(ρ_g/(jωµ_0))``, com
           ``Z_ext = jωµ_0/(2π)·ln(2(h + p)/r)`` [LITERATURA: A. Deri,
           G. Tevan, A. Semlyen, A. Castanheira, "The complex ground
           return plane: a simplified model for homogeneous and
           multi-layer earth return", *IEEE Trans. PAS*, vol. PAS-100,
           n. 8, pp. 3686-3693, ago. 1981 — fórmulas originalmente de
           Dubanton, publicadas por Gary; erro ante Carson "menor que
           poucos por cento" na maior parte da faixa, conforme a
           descrição do artigo acessada em
           https://www.pscad.com/webhelp/EMTDC/Transmission_Lines/References.htm].
        3. **Admitância derivação** ``y = jω·2πε_0/ln(2h/r)``: terra
           PERFEITA para o cálculo capacitivo, sem condutância de
           dispersão e sem efeito corona.
        4. Um único condutor: sem acoplamento mútuo, sem cabo-guarda,
           sem feixe.

        Raises
        ------
        ValueError
            Parâmetros geométricos não positivos ou ``h <= r``.
        """
        ell = _require_positive(length_m, "length_m")
        r = _require_positive(radius_m, "radius_m")
        h = _require_positive(height_m, "height_m")
        rho_c = _require_positive(
            conductor_resistivity_ohm_m, "conductor_resistivity_ohm_m"
        )
        rho_g = _require_positive(earth_resistivity_ohm_m, "earth_resistivity_ohm_m")
        mu_r = _require_positive(relative_permeability, "relative_permeability")
        if h <= r:
            raise ValueError(
                f"altura h = {h:.6g} m deve ser maior que o raio r = {r:.6g} m"
            )
        w = _as_omega(omega) if omega is not None else frequency_grid()
        mu = MU_0 * mu_r
        r_dc = rho_c / (math.pi * r * r)
        omega_s = 8.0 * rho_c / (mu * r * r)
        z_int = r_dc * np.sqrt(1.0 + 1j * w / omega_s)
        p = np.sqrt(rho_g / (1j * w * MU_0))
        z_ext = 1j * w * MU_0 / (2.0 * math.pi) * np.log(2.0 * (h + p) / r)
        y = 1j * w * 2.0 * math.pi * EPSILON_0 / math.log(2.0 * h / r)
        return cls.from_series_shunt(
            w, z_int + z_ext, y, length_m=ell, label=label
        )


# ---------------------------------------------------------------------------
# Modelo modal ajustado
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModalLineModel:
    """Ajuste racional de UM modo: ``Y_c(s)``, ``A_min(s)`` e ``τ``.

    Attributes
    ----------
    y_c:
        Ajuste de ``Y_c = 1/Z_c`` [S]. O termo ``d`` é a admitância
        característica em alta frequência e deve ser > 0.
    a_min:
        Ajuste da parte de FASE MÍNIMA da função de propagação
        (adimensional).
    travel_time_s:
        Atraso puro ``τ`` [s], > 0.
    label:
        Rótulo do modo.
    """

    y_c: RationalFit
    a_min: RationalFit
    travel_time_s: float
    label: str = "modo"

    def __post_init__(self) -> None:
        if not isinstance(self.y_c, RationalFit) or not isinstance(
            self.a_min, RationalFit
        ):
            raise JMartiError("y_c e a_min devem ser RationalFit")
        tau = _require_positive(self.travel_time_s, "travel_time_s")
        object.__setattr__(self, "travel_time_s", tau)
        if not self.y_c.is_stable() or not self.a_min.is_stable():
            raise RationalFitError(
                f"{self.label}: ajuste com polo no semiplano direito — o modelo "
                "no tempo divergiria"
            )
        if self.y_c.d <= 0.0:
            raise RationalFitError(
                f"{self.label}: Y_c(∞) = {self.y_c.d:.6g} S não é positiva; a "
                "estampagem exigiria condutância negativa"
            )

    def characteristic_impedance(
        self, omega: Sequence[float] | np.ndarray
    ) -> np.ndarray:
        """``Z_c(jω)`` reconstruída do ajuste [Ω]."""
        return 1.0 / self.y_c.evaluate(omega)

    def propagation(self, omega: Sequence[float] | np.ndarray) -> np.ndarray:
        """``A(jω) = A_min(jω)·e^{−jωτ}`` reconstruída do ajuste."""
        w = np.asarray(omega, dtype=float).ravel()
        return self.a_min.evaluate(w) * np.exp(-1j * w * self.travel_time_s)

    def fit_report(self) -> dict[str, float | int | str]:
        """Resumo auditável do ajuste (erros, ordens e atraso)."""
        return {
            "label": self.label,
            "travel_time_s": self.travel_time_s,
            "yc_poles": self.y_c.n_poles,
            "yc_rms_error": self.y_c.rms_error,
            "yc_max_error": self.y_c.max_error,
            "yc_d_S": self.y_c.d,
            "a_poles": self.a_min.n_poles,
            "a_rms_error": self.a_min.rms_error,
            "a_max_error": self.a_min.max_error,
            "a_d": self.a_min.d,
        }

    # -- construtores -------------------------------------------------------

    @classmethod
    def constant_parameter(
        cls, *, surge_impedance_ohm: float, travel_time_s: float
    ) -> "ModalLineModel":
        """Modo SEM dependência de frequência, sem ajuste numérico.

        ``Y_c = 1/Z_c`` exata e ``A_min = 1`` exata; toda a propagação
        fica no atraso puro. É o modo em que
        :class:`JMartiLine` deve reproduzir
        :class:`~app.simulation.emt.line.BergeronLine` sem perdas termo
        a termo.
        """
        zc = _require_positive(surge_impedance_ohm, "surge_impedance_ohm")
        tau = _require_positive(travel_time_s, "travel_time_s")
        empty = np.zeros(0, dtype=complex)
        return cls(
            y_c=RationalFit(empty, empty, 1.0 / zc),
            a_min=RationalFit(empty, empty, 1.0),
            travel_time_s=tau,
            label="modo CP",
        )

    @classmethod
    def fit(
        cls,
        data: "LineFrequencyData",
        *,
        n_poles_yc: int = 8,
        n_poles_a: int = 10,
        tolerance: float | None = DEFAULT_FIT_TOLERANCE,
        n_iterations: int = DEFAULT_FIT_ITERATIONS,
        weight: str | np.ndarray = "inverse",
        travel_time_s: float | None = None,
        delay_method: str = "minimum_phase",
        label: str | None = None,
    ) -> "ModalLineModel":
        """Ajusta ``Y_c`` e ``A_min`` a partir das tabelas amostradas.

        Sequência, que é a do método [LITERATURA: Martí 1982;
        [INSERIR CITAÇÃO] para a seção correspondente]:

        1. extrai ``τ`` de ``A(ω)`` (:func:`estimate_time_delay`) ou usa
           o valor imposto por ``travel_time_s``;
        2. remove o atraso, ``A_min(ω) = A(ω)·e^{+jωτ}``;
        3. ajusta ``Y_c(ω)`` e ``A_min(ω)`` por *vector fitting*,
           forçando polos estáveis;
        4. registra os erros e aplica a tolerância declarada.

        Raises
        ------
        LineDataError, RationalFitError
            Tabelas inválidas, atraso inconsistente ou ajuste acima da
            tolerância.
        """
        if not isinstance(data, LineFrequencyData):
            raise LineDataError(
                f"esperado LineFrequencyData, obtido {type(data).__name__}"
            )
        name = str(label if label is not None else data.label)
        tau = (
            _require_positive(travel_time_s, "travel_time_s")
            if travel_time_s is not None
            else estimate_time_delay(data.omega, data.a, method=delay_method)
        )
        a_min = data.a * np.exp(1j * data.omega * tau)
        fit_yc = vector_fit(
            data.omega,
            data.y_c,
            n_poles=int(n_poles_yc),
            n_iterations=int(n_iterations),
            weight=weight,
            include_constant=True,
            enforce_stability=True,
            tolerance=tolerance,
            label=f"{name}: Y_c(ω)",
        )
        fit_a = vector_fit(
            data.omega,
            a_min,
            n_poles=int(n_poles_a),
            n_iterations=int(n_iterations),
            weight=weight,
            include_constant=True,
            enforce_stability=True,
            tolerance=tolerance,
            label=f"{name}: A_min(ω)",
        )
        return cls(y_c=fit_yc, a_min=fit_a, travel_time_s=tau, label=name)


# ---------------------------------------------------------------------------
# Núcleo no tempo: recursão por polo e histórico de trânsito
# ---------------------------------------------------------------------------


class _PoleRecursion:
    """Convolução recursiva de ``Σ_i k_i/(s − p_i)`` por recursão exponencial.

    Cada termo obedece a ``ẏ = p·y + k·x``. Discretizando com passo
    ``h``::

        y(t) = α(h)·y(t−h) + c1·x(t) + c2(h)·x(t−h)
        α(h) = e^{p·h}
        c1   = k·Δt/(2 − p·Δt)                     (independente de h)
        c2(h) = k·h·φ(p·h) − c1,   φ(z) = (e^z − 1)/z

    A justificativa da forma "híbrida" — decaimento exponencial exato,
    parcela instantânea trapezoidal — está no cabeçalho do módulo.
    """

    def __init__(self, fit: RationalFit) -> None:
        p, k, w = fit.condensed()
        self._p = p
        self._k = k
        self._w = w
        self._state = np.zeros(p.size, dtype=complex)
        self._c1 = np.zeros(p.size, dtype=complex)
        self._cache: dict[float, tuple[np.ndarray, np.ndarray]] = {}
        self.d: float = fit.d
        self.instantaneous: float = fit.d

    @property
    def n_terms(self) -> int:
        """Número de termos condensados (par conjugado conta 1)."""
        return int(self._p.size)

    def prepare(self, dt: float) -> None:
        """Fixa ``c1`` no passo de referência ``Δt`` e zera o cache."""
        step = _require_positive(dt, "dt")
        if self._p.size:
            self._c1 = self._k * step / (2.0 - self._p * step)
            self.instantaneous = self.d + float(np.sum(self._w * self._c1.real))
        else:
            self._c1 = np.zeros(0, dtype=complex)
            self.instantaneous = self.d
        self._cache.clear()

    def reset(self) -> None:
        """Zera os estados internos."""
        self._state = np.zeros(self._p.size, dtype=complex)

    def _coefficients(self, h: float) -> tuple[np.ndarray, np.ndarray]:
        """``(α, c2)`` para o passo ``h``, com cache."""
        key = float(h)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        if self._p.size == 0:
            out = (np.zeros(0, dtype=complex), np.zeros(0, dtype=complex))
        else:
            z = self._p * key
            alpha = np.exp(z)
            total = self._k * key * _expm1_over(z)
            out = (alpha, total - self._c1)
        self._cache[key] = out
        return out

    def history(self, h: float, x_prev: float) -> float:
        """Parcela do passo que NÃO depende de ``x(t)``."""
        if self._p.size == 0:
            return 0.0
        alpha, c2 = self._coefficients(h)
        return float(np.sum(self._w * (alpha * self._state + c2 * x_prev).real))

    def advance(self, h: float, x_now: float, x_prev: float) -> None:
        """Atualiza os estados com a entrada do passo concluído."""
        if self._p.size == 0:
            return
        alpha, c2 = self._coefficients(h)
        self._state = alpha * self._state + self._c1 * x_now + c2 * x_prev

    def output(self, x_now: float) -> float:
        """Saída total ``d·x + Σ w·Re(y)`` com os estados JÁ atualizados."""
        if self._p.size == 0:
            return self.d * x_now
        return self.d * x_now + float(np.sum(self._w * self._state.real))


class _WaveHistory:
    """Buffer de uma função de onda ``F(t)`` com interpolação linear.

    Mesma política do histórico de trânsito do Bergeron
    [REPO: app/simulation/emt/line.py:172]: cursor monotônico, custo
    amortizado O(1), poda periódica, retenção de ordem zero na
    extrapolação e valor NULO antes de ``t = 0`` (linha inicialmente
    desenergizada).
    """

    _PRUNE_THRESHOLD: int = 4096

    def __init__(self) -> None:
        self._t: list[float] = [0.0]
        self._f: list[float] = [0.0]
        self._cursor: int = 0

    def reset(self) -> None:
        """Zera o buffer, mantendo a amostra nula em ``t = 0``."""
        self._t = [0.0]
        self._f = [0.0]
        self._cursor = 0

    def append(self, t: float, value: float) -> None:
        """Registra ``F(t)``."""
        self._t.append(float(t))
        self._f.append(float(value))
        if len(self._t) > self._PRUNE_THRESHOLD and self._cursor > 1:
            keep = self._cursor - 1
            self._t = self._t[keep:]
            self._f = self._f[keep:]
            self._cursor -= keep

    def value_at(self, t_query: float) -> float:
        """``F(t_query)`` por interpolação linear."""
        if t_query <= self._t[0]:
            return 0.0
        last = len(self._t) - 1
        if t_query >= self._t[last]:
            return self._f[last]
        c = self._cursor
        if c > last - 1:
            c = last - 1
        while c + 1 <= last and self._t[c + 1] < t_query:
            c += 1
        while c > 0 and self._t[c] > t_query:
            c -= 1
        self._cursor = c
        t0, t1 = self._t[c], self._t[c + 1]
        span = t1 - t0
        if span <= 0.0:  # pragma: no cover - defensivo
            return self._f[c]
        w = (t_query - t0) / span
        return self._f[c] + w * (self._f[c + 1] - self._f[c])

    def __len__(self) -> int:  # pragma: no cover - conveniência
        return len(self._t)


class _ModeChannel:
    """Canal de UM modo: dois terminais, convoluções e histórico de trânsito."""

    def __init__(self, model: ModalLineModel) -> None:
        self.model = model
        self._yc_k = _PoleRecursion(model.y_c)
        self._yc_m = _PoleRecursion(model.y_c)
        self._a_k = _PoleRecursion(model.a_min)
        self._a_m = _PoleRecursion(model.a_min)
        self._hist_k = _WaveHistory()
        self._hist_m = _WaveHistory()
        self._x_prev_k = 0.0
        self._x_prev_m = 0.0
        self._xa_prev_k = 0.0
        self._xa_prev_m = 0.0
        self._t_prev = 0.0
        self._h = 0.0
        self._b_k = 0.0
        self._b_m = 0.0
        self._xa_k = 0.0
        self._xa_m = 0.0
        self.i_hist_k = 0.0
        self.i_hist_m = 0.0
        self.g: float = 0.0

    def prepare(self, dt: float) -> None:
        """Fixa os coeficientes instantâneos e a condutância estampada."""
        for rec in (self._yc_k, self._yc_m, self._a_k, self._a_m):
            rec.prepare(dt)
        self.g = self._yc_k.instantaneous
        if not math.isfinite(self.g) or self.g <= 0.0:
            raise RationalFitError(
                f"{self.model.label}: condutância estampada G = {self.g!r} S não "
                "é positiva; o ajuste de Y_c não é passivo no passo escolhido"
            )

    def reset(self) -> None:
        """Volta ao repouso (linha desenergizada)."""
        for rec in (self._yc_k, self._yc_m, self._a_k, self._a_m):
            rec.reset()
        self._hist_k.reset()
        self._hist_m.reset()
        self._x_prev_k = 0.0
        self._x_prev_m = 0.0
        self._xa_prev_k = 0.0
        self._xa_prev_m = 0.0
        self._t_prev = 0.0
        self._h = 0.0
        self._b_k = 0.0
        self._b_m = 0.0
        self._xa_k = 0.0
        self._xa_m = 0.0
        self.i_hist_k = 0.0
        self.i_hist_m = 0.0

    def begin_step(self, t: float) -> None:
        """Calcula ``B_k``, ``B_m`` e as fontes de histórico do passo."""
        h = float(t) - self._t_prev
        if h <= 0.0:
            raise JMartiError(
                f"{self.model.label}: passo não positivo (t = {t!r}, anterior = "
                f"{self._t_prev!r}); a linha exige marcha monotônica no tempo"
            )
        self._h = h
        tau = self.model.travel_time_s
        self._xa_k = self._hist_m.value_at(float(t) - tau)
        self._xa_m = self._hist_k.value_at(float(t) - tau)
        self._b_k = (
            self._a_k.d * self._xa_k
            + self._a_k.history(h, self._xa_prev_k)
            + self._instant(self._a_k, self._xa_k)
        )
        self._b_m = (
            self._a_m.d * self._xa_m
            + self._a_m.history(h, self._xa_prev_m)
            + self._instant(self._a_m, self._xa_m)
        )
        self.i_hist_k = (
            -self.g * self._b_k
            + self._yc_k.history(h, self._x_prev_k)
        )
        self.i_hist_m = (
            -self.g * self._b_m
            + self._yc_m.history(h, self._x_prev_m)
        )

    @staticmethod
    def _instant(rec: _PoleRecursion, x_now: float) -> float:
        """Parcela ``Σ w·Re(c1)·x(t)`` de uma recursão com entrada CONHECIDA."""
        return (rec.instantaneous - rec.d) * x_now

    def commit_step(self, t: float, v_k: float, v_m: float) -> tuple[float, float]:
        """Fecha o passo; devolve ``(i_k, i_m)`` [A] entrando na linha."""
        h = self._h
        x_k = v_k - self._b_k
        x_m = v_m - self._b_m
        self._yc_k.advance(h, x_k, self._x_prev_k)
        self._yc_m.advance(h, x_m, self._x_prev_m)
        self._a_k.advance(h, self._xa_k, self._xa_prev_k)
        self._a_m.advance(h, self._xa_m, self._xa_prev_m)
        self._x_prev_k = x_k
        self._x_prev_m = x_m
        self._xa_prev_k = self._xa_k
        self._xa_prev_m = self._xa_m
        i_k = self.g * v_k + self.i_hist_k
        i_m = self.g * v_m + self.i_hist_m
        self._hist_k.append(t, 2.0 * v_k - self._b_k)
        self._hist_m.append(t, 2.0 * v_m - self._b_m)
        self._t_prev = float(t)
        return i_k, i_m

    @property
    def incident_k(self) -> float:
        """``B_k(t)`` do passo corrente [V] — onda que CHEGA ao terminal k."""
        return self._b_k

    @property
    def incident_m(self) -> float:
        """``B_m(t)`` do passo corrente [V]."""
        return self._b_m


# ---------------------------------------------------------------------------
# Componente monofásico / modal
# ---------------------------------------------------------------------------


class JMartiLine(Component):
    """Linha/cabo com dependência de frequência (JMarti), UM condutor/modo.

    Interface IDÊNTICA à de :class:`~app.simulation.emt.line.BergeronLine`:
    mesma classe base, mesmos ``stamp_matrix``/``stamp_rhs``/``commit``,
    ``branch_voltage(0|1)`` para as tensões dos terminais ``k`` e ``m`` e
    ``branch_current(0|1)`` para as correntes que ENTRAM na linha por
    cada terminal.

    Parameters
    ----------
    name:
        Identificador do ramo.
    node_k, node_m:
        Nós das extremidades.
    model:
        :class:`ModalLineModel` já ajustado.

    Raises
    ------
    JMartiError
        ``model`` de tipo errado ou nós coincidentes.
    """

    def __init__(
        self, name: str, node_k: str, node_m: str, *, model: ModalLineModel
    ) -> None:
        super().__init__(name, (node_k, node_m))
        if self.nodes[0] == self.nodes[1]:
            raise JMartiError(f"linha {name!r} com os dois terminais no mesmo nó")
        if not isinstance(model, ModalLineModel):
            raise JMartiError(
                f"linha {name!r}: esperado ModalLineModel, obtido "
                f"{type(model).__name__}"
            )
        self.model: ModalLineModel = model
        self._channel = _ModeChannel(model)
        self._v_k = 0.0
        self._v_m = 0.0
        self._i_k = 0.0
        self._i_m = 0.0
        self._warned_short = False

    # -- construtores alternativos -----------------------------------------

    @classmethod
    def constant_parameter(
        cls,
        name: str,
        node_k: str,
        node_m: str,
        *,
        surge_impedance_ohm: float,
        travel_time_s: float,
    ) -> "JMartiLine":
        """Linha SEM dependência de frequência — referência de consistência.

        Reproduz :class:`~app.simulation.emt.line.BergeronLine` sem
        perdas termo a termo: com ``Y_c`` constante e ``A_min = 1``, o
        histórico vale ``I_k = −(1/Z_c)·F_m(t−τ)``, que é exatamente a
        eq. (7b) de [FONTE: Dommel 1969, p. 389].
        """
        return cls(
            name,
            node_k,
            node_m,
            model=ModalLineModel.constant_parameter(
                surge_impedance_ohm=surge_impedance_ohm, travel_time_s=travel_time_s
            ),
        )

    @classmethod
    def from_tables(
        cls,
        name: str,
        node_k: str,
        node_m: str,
        *,
        data: LineFrequencyData,
        **fit_kwargs,
    ) -> "JMartiLine":
        """Ajusta o modelo a partir das tabelas ``Z_c(ω)`` e ``A(ω)``."""
        return cls(
            name,
            node_k,
            node_m,
            model=ModalLineModel.fit(data, label=name, **fit_kwargs),
        )

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
        conductance_S_per_m: float = 0.0,
        omega: Sequence[float] | np.ndarray | None = None,
        **fit_kwargs,
    ) -> "JMartiLine":
        """Mesma assinatura do Bergeron, com ajuste racional automático.

        Com ``R' = G' = 0`` desvia para :meth:`constant_parameter` — não
        há o que ajustar e o resultado é EXATO.
        """
        if float(resistance_ohm_per_m) == 0.0 and float(conductance_S_per_m) == 0.0:
            lp = _require_positive(inductance_H_per_m, "inductance_H_per_m")
            cp = _require_positive(capacitance_F_per_m, "capacitance_F_per_m")
            ell = _require_positive(length_m, "length_m")
            return cls.constant_parameter(
                name,
                node_k,
                node_m,
                surge_impedance_ohm=math.sqrt(lp / cp),
                travel_time_s=ell * math.sqrt(lp * cp),
            )
        data = LineFrequencyData.from_distributed_parameters(
            length_m=length_m,
            inductance_H_per_m=inductance_H_per_m,
            capacitance_F_per_m=capacitance_F_per_m,
            resistance_ohm_per_m=resistance_ohm_per_m,
            conductance_S_per_m=conductance_S_per_m,
            omega=omega,
            label=name,
        )
        return cls.from_tables(name, node_k, node_m, data=data, **fit_kwargs)

    # -- propriedades -------------------------------------------------------

    @property
    def travel_time_s(self) -> float:
        """Atraso puro ``τ`` [s]."""
        return self.model.travel_time_s

    @property
    def conductance_S(self) -> float:
        """Condutância estampada em cada terminal [S] (após ``prepare``)."""
        return self._channel.g

    def fit_report(self) -> dict[str, float | int | str]:
        """Resumo auditável do ajuste racional."""
        return self.model.fit_report()

    def n_branches(self) -> int:
        return 2

    # -- ciclo de vida ------------------------------------------------------

    def prepare(self, dt: float) -> None:
        super().prepare(dt)
        self._channel.prepare(self._dt)
        if self.model.travel_time_s < self._dt and not self._warned_short:
            self._warned_short = True
            log.warning(
                "linha %r: atraso τ=%.6g s menor que o passo Δt=%.6g s; o "
                "histórico de trânsito será retido por ordem zero e a linha "
                "deixa de representar propagação — reduza Δt ou use elementos "
                "concentrados (mesma divergência declarada do modelo de "
                "Bergeron ante Dommel 1969, p. 391)",
                self.name,
                self.model.travel_time_s,
                self._dt,
            )

    def reset(self) -> None:
        self._channel.reset()
        self._v_k = 0.0
        self._v_m = 0.0
        self._i_k = 0.0
        self._i_m = 0.0

    # -- estampagem ---------------------------------------------------------

    def stamp_matrix(self, A: np.ndarray) -> None:
        """Estampa ``G`` SÓ nas diagonais das duas extremidades.

        Como no Bergeron, não há termo fora da diagonal: os terminais
        estão topologicamente desconectados e só se comunicam pelo
        histórico com atraso ``τ`` [FONTE: Dommel 1969, §I, p. 389].
        """
        g = self._channel.g
        k, m = self._idx[0], self._idx[1]
        if k != GROUND_INDEX:
            A[k, k] += g
        if m != GROUND_INDEX:
            A[m, m] += g

    def stamp_rhs(self, b: np.ndarray, t: float, mode: str) -> None:
        self._channel.begin_step(t)
        k, m = self._idx[0], self._idx[1]
        if k != GROUND_INDEX:
            b[k] -= self._channel.i_hist_k
        if m != GROUND_INDEX:
            b[m] -= self._channel.i_hist_m

    def commit(self, x: np.ndarray, t: float, mode: str) -> None:
        v_k = node_voltage(x, self._idx[0])
        v_m = node_voltage(x, self._idx[1])
        self._v_k = v_k
        self._v_m = v_m
        self._i_k, self._i_m = self._channel.commit_step(t, v_k, v_m)

    # -- leitura ------------------------------------------------------------

    def branch_voltage(self, index: int = 0) -> float:
        """``index = 0`` ⇒ tensão do terminal k; ``1`` ⇒ terminal m [V]."""
        if index == 0:
            return self._v_k
        if index == 1:
            return self._v_m
        raise ValueError(f"terminal inválido para linha: {index!r}")

    def branch_current(self, index: int = 0) -> float:
        """``index = 0`` ⇒ ``i_km``; ``1`` ⇒ ``i_mk`` (ENTRANDO na linha) [A]."""
        if index == 0:
            return self._i_k
        if index == 1:
            return self._i_m
        raise ValueError(f"terminal inválido para linha: {index!r}")


# ---------------------------------------------------------------------------
# Transformação modal real e constante
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModalTransform:
    """Matriz de transformação modal REAL e CONSTANTE.

    É a aproximação característica do método de Martí: a matriz de
    autovetores de ``[Y][Z]`` é, na verdade, função da frequência, e o
    modelo a congela em um valor real — tipicamente calculado em uma
    frequência de referência [LITERATURA: Martí 1982; [INSERIR CITAÇÃO]
    para a seção correspondente]. A consequência está declarada em
    :data:`JMARTI_LIMITATIONS`.

    Convenção::

        v_fase = T_v · v_modo          i_fase = T_i · i_modo
        T_i = (T_vᵀ)⁻¹                 (invariância de potência)

    Attributes
    ----------
    t_v:
        Matriz ``n×n`` real e inversível de transformação de TENSÃO.
    label:
        Rótulo para mensagens.
    """

    t_v: np.ndarray
    label: str = "T"

    def __post_init__(self) -> None:
        m = np.asarray(self.t_v, dtype=float)
        if m.ndim != 2 or m.shape[0] != m.shape[1] or m.shape[0] < 1:
            raise JMartiError(
                f"{self.label}: matriz modal deve ser quadrada, obtida {m.shape}"
            )
        if not np.all(np.isfinite(m)):
            raise JMartiError(f"{self.label}: matriz modal com valores não finitos")
        det = float(np.linalg.det(m))
        if abs(det) < 1.0e-12:
            raise JMartiError(
                f"{self.label}: matriz modal singular (det = {det:.3e})"
            )
        object.__setattr__(self, "t_v", m)

    @property
    def n(self) -> int:
        """Número de fases/modos."""
        return int(self.t_v.shape[0])

    @property
    def t_v_inv(self) -> np.ndarray:
        """``T_v⁻¹`` — leva tensões de fase a tensões modais."""
        return np.linalg.inv(self.t_v)

    @property
    def t_i(self) -> np.ndarray:
        """``T_i = (T_vᵀ)⁻¹`` — leva correntes modais a correntes de fase."""
        return np.linalg.inv(self.t_v.T)

    def conductance_block(self, g_modal: Sequence[float]) -> np.ndarray:
        """``T_i·diag(g)·T_v⁻¹`` — bloco ``n×n`` estampado em cada terminal."""
        g = np.asarray(g_modal, dtype=float).ravel()
        if g.size != self.n:
            raise JMartiError(
                f"{self.label}: {g.size} condutâncias modais para {self.n} modos"
            )
        return self.t_i @ np.diag(g) @ self.t_v_inv


def clarke_transform(n: int = 3) -> ModalTransform:
    """Transformação de Clarke ORTONORMAL de ``n`` fases.

    Primeira coluna: modo homopolar (todas as fases em fase — o modo de
    "terra", mais lento e mais atenuado); demais colunas: modos aéreos,
    ortogonais entre si. Por ser ortonormal, ``T_i = T_v`` e o bloco de
    condutância com modos IDÊNTICOS degenera em ``g·I``, isto é, fases
    desacopladas — propriedade usada como teste de consistência.

    É EXATA apenas para linha perfeitamente equilibrada e transposta
    [INFERÊNCIA FÍSICA]; para cabo real a matriz deve vir do cálculo de
    parâmetros do caso.
    """
    m = int(n)
    if m < 1:
        raise JMartiError(f"n deve ser >= 1, obtido {n!r}")
    cols = [np.ones(m) / math.sqrt(m)]
    for j in range(1, m):
        v = np.zeros(m)
        v[:j] = 1.0
        v[j] = -float(j)
        v /= np.linalg.norm(v)
        cols.append(v)
    return ModalTransform(np.column_stack(cols), label=f"Clarke({m})")


class ModalJMartiLine(Component):
    """Linha multifásica JMarti com transformação modal real e constante.

    Cada modo é um canal independente (mesma máquina de
    :class:`JMartiLine`); o acoplamento entre fases aparece apenas nos
    blocos ``T_i·diag(g)·T_v⁻¹`` estampados em cada terminal e no
    mapeamento ``I_fase = T_i·I_modo`` das fontes de histórico. Os dois
    terminais continuam topologicamente desconectados.

    Parameters
    ----------
    name:
        Identificador do ramo.
    nodes_k, nodes_m:
        Nós das ``n`` fases em cada extremidade.
    models:
        Um :class:`ModalLineModel` por modo, na ordem das colunas de
        ``transform.t_v``.
    transform:
        :class:`ModalTransform` com ``n`` igual ao número de fases.

    Notas
    ------
    ``branch_voltage(i)`` devolve a tensão da fase ``i`` no terminal
    ``k`` e ``branch_voltage(n + i)`` no terminal ``m``; o mesmo para
    ``branch_current``.
    """

    def __init__(
        self,
        name: str,
        nodes_k: Sequence[str],
        nodes_m: Sequence[str],
        *,
        models: Sequence[ModalLineModel],
        transform: ModalTransform,
    ) -> None:
        nk = tuple(str(x) for x in nodes_k)
        nm = tuple(str(x) for x in nodes_m)
        if len(nk) != len(nm) or not nk:
            raise JMartiError(
                f"linha {name!r}: {len(nk)} nós em k e {len(nm)} em m"
            )
        super().__init__(name, nk + nm)
        if not isinstance(transform, ModalTransform):
            raise JMartiError(
                f"linha {name!r}: esperado ModalTransform, obtido "
                f"{type(transform).__name__}"
            )
        if transform.n != len(nk):
            raise JMartiError(
                f"linha {name!r}: transformação de {transform.n} modos para "
                f"{len(nk)} fases"
            )
        mods = tuple(models)
        if len(mods) != len(nk):
            raise JMartiError(
                f"linha {name!r}: {len(mods)} modelos modais para {len(nk)} modos"
            )
        for mdl in mods:
            if not isinstance(mdl, ModalLineModel):
                raise JMartiError(
                    f"linha {name!r}: esperado ModalLineModel, obtido "
                    f"{type(mdl).__name__}"
                )
        self.n_phases: int = len(nk)
        self.transform: ModalTransform = transform
        self.models: tuple[ModalLineModel, ...] = mods
        self._channels = [_ModeChannel(m) for m in mods]
        self._block = np.zeros((self.n_phases, self.n_phases))
        self._v_k = np.zeros(self.n_phases)
        self._v_m = np.zeros(self.n_phases)
        self._i_k = np.zeros(self.n_phases)
        self._i_m = np.zeros(self.n_phases)
        self._ih_k = np.zeros(self.n_phases)
        self._ih_m = np.zeros(self.n_phases)

    def n_branches(self) -> int:
        return 2 * self.n_phases

    def prepare(self, dt: float) -> None:
        super().prepare(dt)
        for ch in self._channels:
            ch.prepare(self._dt)
        self._block = self.transform.conductance_block([ch.g for ch in self._channels])
        for ch in self._channels:
            if ch.model.travel_time_s < self._dt:
                log.warning(
                    "linha %r, modo %r: atraso τ=%.6g s menor que o passo "
                    "Δt=%.6g s; histórico retido por ordem zero",
                    self.name,
                    ch.model.label,
                    ch.model.travel_time_s,
                    self._dt,
                )

    def reset(self) -> None:
        for ch in self._channels:
            ch.reset()
        self._v_k = np.zeros(self.n_phases)
        self._v_m = np.zeros(self.n_phases)
        self._i_k = np.zeros(self.n_phases)
        self._i_m = np.zeros(self.n_phases)
        self._ih_k = np.zeros(self.n_phases)
        self._ih_m = np.zeros(self.n_phases)

    def stamp_matrix(self, A: np.ndarray) -> None:
        n = self.n_phases
        for side in (0, n):
            idx = self._idx[side : side + n]
            for a in range(n):
                ia = idx[a]
                if ia == GROUND_INDEX:
                    continue
                for b in range(n):
                    ib = idx[b]
                    if ib == GROUND_INDEX:
                        continue
                    A[ia, ib] += self._block[a, b]

    def stamp_rhs(self, b: np.ndarray, t: float, mode: str) -> None:
        n = self.n_phases
        for ch in self._channels:
            ch.begin_step(t)
        i_mode_k = np.asarray([ch.i_hist_k for ch in self._channels], dtype=float)
        i_mode_m = np.asarray([ch.i_hist_m for ch in self._channels], dtype=float)
        t_i = self.transform.t_i
        self._ih_k = t_i @ i_mode_k
        self._ih_m = t_i @ i_mode_m
        for a in range(n):
            ia = self._idx[a]
            if ia != GROUND_INDEX:
                b[ia] -= self._ih_k[a]
            im = self._idx[n + a]
            if im != GROUND_INDEX:
                b[im] -= self._ih_m[a]

    def commit(self, x: np.ndarray, t: float, mode: str) -> None:
        n = self.n_phases
        v_k = np.asarray(
            [node_voltage(x, self._idx[a]) for a in range(n)], dtype=float
        )
        v_m = np.asarray(
            [node_voltage(x, self._idx[n + a]) for a in range(n)], dtype=float
        )
        inv = self.transform.t_v_inv
        vm_k = inv @ v_k
        vm_m = inv @ v_m
        im_k = np.zeros(n)
        im_m = np.zeros(n)
        for j, ch in enumerate(self._channels):
            im_k[j], im_m[j] = ch.commit_step(t, float(vm_k[j]), float(vm_m[j]))
        t_i = self.transform.t_i
        self._v_k = v_k
        self._v_m = v_m
        self._i_k = t_i @ im_k
        self._i_m = t_i @ im_m

    def branch_voltage(self, index: int = 0) -> float:
        n = self.n_phases
        i = int(index)
        if 0 <= i < n:
            return float(self._v_k[i])
        if n <= i < 2 * n:
            return float(self._v_m[i - n])
        raise ValueError(f"terminal inválido para linha modal: {index!r}")

    def branch_current(self, index: int = 0) -> float:
        n = self.n_phases
        i = int(index)
        if 0 <= i < n:
            return float(self._i_k[i])
        if n <= i < 2 * n:
            return float(self._i_m[i - n])
        raise ValueError(f"terminal inválido para linha modal: {index!r}")


# ---------------------------------------------------------------------------
# Limitações conhecidas
# ---------------------------------------------------------------------------

JMARTI_LIMITATIONS: dict[str, str] = {
    "emt_jmarti_constant_real_modal_matrix": (
        "A decomposição modal usa matriz de transformação REAL e CONSTANTE — a "
        "aproximação característica do método de Martí. A matriz de autovetores "
        "de [Y][Z] é, na verdade, função da frequência e complexa; congelá-la "
        "em um valor real introduz erro crescente com o desequilíbrio da "
        "geometria e com a frequência, e é justamente o que os modelos de "
        "domínio de fases (ULM/Universal Line Model) vieram corrigir. Para o "
        "cabo tripolar do caso de manobra, o modo de terra e os modos aéreos "
        "são de fato mal separados por matriz constante em alta frequência."
    ),
    "emt_jmarti_single_conductor_default": (
        "O componente PADRÃO (JMartiLine) é MONOFÁSICO/monomodal: um condutor "
        "por instância, sem acoplamento mútuo. O caso multifásico existe em "
        "ModalJMartiLine, que exige do usuário a matriz de transformação e um "
        "modelo por modo — nenhum dos dois é calculado a partir da geometria "
        "de um feixe/cabo real por este módulo. Sem tabelas modais vindas do "
        "cálculo de parâmetros do caso, o multifásico permanece exercício."
    ),
    "emt_jmarti_no_steady_state_init": (
        "A partida em regime permanente senoidal (Solver(init='steady_state')) "
        "NÃO suporta a linha JMarti: app.simulation.emt.steady_state não conhece "
        "o componente e levanta UnsupportedComponentError — o que é o "
        "comportamento desejado, pois semear o histórico exigiria a resposta "
        "fasorial de TODAS as recursões por polo e do buffer de trânsito ao "
        "longo de τ. Casos com linha dependente da frequência devem usar "
        "init='zero' com janela de acomodação."
    ),
    "emt_jmarti_fit_is_the_model": (
        "O que se simula NÃO é Z_c(ω) e A(ω) tabelados, e sim o AJUSTE "
        "racional deles. O erro de ajuste (RationalFit.rms_error, relativo, "
        "reportado em log e sujeito a tolerância declarada) é um erro de "
        "MODELO, que se propaga para V_pk e dv/dt e não é reduzido por "
        "refinamento de Δt. Fora da faixa de frequência tabelada o ajuste "
        "extrapola sem controle: a faixa deve cobrir o conteúdo espectral da "
        "frente de interesse (para frente de 0,1 µs, alguns MHz)."
    ),
    "emt_jmarti_hybrid_recursion": (
        "A convolução recursiva usa decaimento exponencial EXATO com parcela "
        "instantânea trapezoidal (c1 = k·Δt/(2 − pΔt)), escolha própria e não "
        "publicada, feita para que a condutância estampada seja a mesma no "
        "passo completo e nos meios-passos do CDA — sem isso a matriz "
        "fatorada ficaria inconsistente, já que o solver não reavalia a "
        "topologia entre os dois meios-passos. O esquema coincide com o "
        "trapezoidal até O(Δt²) e é incondicionalmente estável, mas o par "
        "(c1, c2) não é o de Semlyen & Dabuleanu 1975 nem o de Martí 1982."
    ),
    "emt_jmarti_delay_interpolation": (
        "O atraso τ é aplicado por interpolação LINEAR no buffer de trânsito, "
        "como no Bergeron; τ < Δt não é elevado a Δt (divergência declarada "
        "ante Dommel 1969, p. 391) e sim sinalizado por WARNING com retenção "
        "de ordem zero. A interpolação amortece numericamente a frente, o que "
        "se soma — e não se distingue automaticamente — da atenuação FÍSICA "
        "que o modelo passou a representar."
    ),
    "emt_jmarti_no_passivity_enforcement": (
        "Impõe-se estabilidade (todos os polos no semiplano esquerdo) e "
        "verifica-se que a condutância estampada seja positiva, mas NÃO se "
        "impõe passividade no sentido forte (Re{Y_c(jω)} >= 0 em toda a "
        "frequência, e |A(jω)| <= 1 para o ajuste, não só para a tabela). Um "
        "ajuste estável porém não passivo pode gerar crescimento de energia "
        "em rede com realimentação; o sintoma é divergência lenta da "
        "simulação."
    ),
}


__all__ = [
    # constantes
    "MU_0",
    "EPSILON_0",
    "DEFAULT_FIT_TOLERANCE",
    "DEFAULT_FIT_ITERATIONS",
    "FIT_WEIGHTS",
    "DELAY_METHODS",
    "MAGNITUDE_FLOOR_RATIO",
    # erros
    "JMartiError",
    "LineDataError",
    "RationalFitError",
    # ajuste racional
    "RationalFit",
    "vector_fit",
    "initial_poles",
    "minimum_phase_angle",
    "estimate_time_delay",
    "frequency_grid",
    "frequency_grid_for_delay",
    # dados e modelo
    "LineFrequencyData",
    "ModalLineModel",
    # componentes
    "JMartiLine",
    "ModalJMartiLine",
    "ModalTransform",
    "clarke_transform",
    # auditoria
    "JMARTI_LIMITATIONS",
]
