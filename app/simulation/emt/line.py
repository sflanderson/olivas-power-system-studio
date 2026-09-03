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

a grandeza ``e + Z·i`` é constante ao longo da característica
``x − vt = const``: um observador fictício que deixa o nó ``m`` em
``t − τ`` e chega ao nó ``k`` em ``t`` encontra o mesmo valor, isto é
``e_m(t−τ) + Z·i_mk(t−τ) = e_k(t) + Z·(−i_km(t))`` [FONTE: Dommel
1969, eqs. (4)-(6), p. 389]. Disso resulta o par de equivalentes de
Norton DESACOPLADOS [FONTE: Dommel 1969, eqs. (7a) e (7b), p. 389;
Fig. 1(b)]::

    i_km(t)  = (1/Z_c)·e_k(t) + I_k(t−τ)                   (7a)
    I_k(t−τ) = −(1/Z_c)·e_m(t−τ) − i_mk(t−τ)               (7b)

    i_mk(t)  = (1/Z_c)·e_m(t) + I_m(t−τ)                   (7a)
    I_m(t−τ) = −(1/Z_c)·e_k(t−τ) − i_km(t−τ)               (7b)

O acoplamento entre os dois terminais é APENAS pelo histórico: "os
terminais não estão topologicamente conectados; as condições da outra
extremidade só são vistas indiretamente e com atraso ``τ``" [FONTE:
Dommel 1969, p. 389]. Na matriz nodal cada extremidade contribui
somente com ``1/Z_c`` na PRÓPRIA DIAGONAL — "linhas sem perdas
contribuem apenas para os elementos diagonais da matriz; elementos
fora da diagonal resultam apenas de parâmetros concentrados" [FONTE:
Dommel 1969, §I, p. 389]. É essa propriedade que torna a linha o
elemento que "parte" a matriz do sistema em blocos [FONTE: Dommel
1969, Fig. 9, p. 392; Dommel 1971, §V, p. 2563].

Perdas concentradas (R/4, R/2, R/4)
====================================

O modelo com perdas segue a aproximação de [FONTE: Dommel 1969,
"Approximation of Series Resistance of Lines", p. 390]: "o programa da
BPA concentra automaticamente ``R/4`` nas duas extremidades e ``R/2``
no meio da linha", tratando os dois trechos como meias-linhas sem
perdas e mantendo válido o equivalente da Fig. 1; muda apenas

    Z = sqrt(L'/C') + R/4          ζ = (Z_c − R/4)/(Z_c + R/4)

Empregou-se a forma REFINADA do modelo, a que resulta de eliminar
explicitamente o nó central [LITERATURA: H. W. Dommel, *EMTP Theory
Book*, BPA, 1986, §4.2.1.4] — e não a combinação linear de ``I_k`` e
``I_m`` impressa em [FONTE: Dommel 1969, p. 390], que omite o fator
``ζ`` sobre as correntes de histórico::

    i_km(t) = v_k(t)/Z + I_k(t−τ)

    I_k(t−τ) = −(1+ζ)/2 · [ v_m(t−τ)/Z + ζ·i_mk(t−τ) ]
               −(1−ζ)/2 · [ v_k(t−τ)/Z + ζ·i_km(t−τ) ]

Para ``R = 0`` tem-se ``ζ = 1`` e a expressão recai EXATAMENTE em
(7a)-(7b). O critério que decidiu entre as duas formas é a
consistência em corrente contínua. [CÁLCULO PRÓPRIO] Em regime
permanente contínuo (``i_km = −i_mk = I`` constante), com
``1 − ζ = (R/2)/Z`` e ``a − b = ζ``, a forma acima fornece
``I·4ab = (1/Z)·a·(v_k − v_m)`` e portanto ``I = (v_k − v_m)/R``
EXATAMENTE — a resistência total vista pelo circuito é ``R``, sem erro
de truncamento, que é o que a aproximação de Dommel promete. A forma
impressa em 1969, submetida à mesma verificação, devolve
``R·(Z_c + R/4)/(2·Z_c) ≈ R/2``, ou seja, metade da resistência
pretendida. Esse é o teste de aceitação implementado em
``tests/test_emt_kernel.py``.

Interpolação de histórico
==========================

Quando ``τ`` não é múltiplo inteiro de ``Δt`` — e também durante os
meios-passos do amortecimento crítico (CDA), em que a base de tempo
deixa de ser uniforme — o valor em ``t − τ`` é obtido por
**interpolação linear** entre as duas amostras que o cercam. É a opção
padrão do programa da BPA: "uma opção usa interpolação linear, porque
na maioria dos casos práticos as curvas ``e(t)`` e ``i(t)`` são suaves
em vez de descontínuas; para casos com descontinuidades esperadas,
outra opção arredonda o tempo de trânsito ``τ`` para o múltiplo
inteiro de ``Δt`` mais próximo. As duas opções elevam tempos de
trânsito ``τ < Δt`` para ``Δt``" [FONTE: Dommel 1969, "Accuracy",
p. 391]. Aqui apenas a interpolação linear está implementada; o
arredondamento de ``τ`` NÃO está, e ``τ < Δt`` é sinalizado por
``WARNING`` com retenção de ordem zero em vez de ser elevado a ``Δt``
— divergência declarada em relação à fonte, cf.
:meth:`BergeronLine.prepare`. A interpolação introduz um pequeno
amortecimento numérico da frente de onda, discutido em [LITERATURA:
J. A. Martinez-Velasco (ed.), *Transient Analysis of Power Systems*,
Wiley/IEEE Press, 2015, cap. 2] e em [LITERATURA: A. Greenwood,
*Electrical Transients in Power Systems*, 2. ed., Wiley, 1991, cap. 5].

Condições iniciais da linha — lacuna declarada
===============================================

[FONTE: Dommel 1969, Apêndice I, p. 395] exige que, para uma linha sem
perdas, os valores ``I_k`` e ``I_m`` sejam dados em
``t = 0, −Δt, −2Δt, …, −τ``: "a necessidade de conhecê-los antes de
``t = 0`` é consequência de registrar somente as condições terminais;
se as condições fossem dadas também ao longo da linha, em incrementos
de tempo de trânsito ``Δt``, os valores iniciais em ``t = 0``
bastariam". O padrão deste módulo é o histórico NULO antes de ``t = 0``
(:meth:`_TravelHistory.value_at` devolve zeros), isto é, linha
inicialmente desenergizada — o que basta para a partida do repouso.

Para a partida em REGIME PERMANENTE a exigência do Apêndice I é
atendida por :meth:`BergeronLine.seed_steady_state`, que preenche o
buffer com a onda senoidal de regime nos instantes
``0, −Δt, −2Δt, …`` cobrindo todo o tempo de trânsito ``τ`` — os
``I_k`` e ``I_m`` de que Dommel fala, calculados a partir da solução
fasorial do PRÓPRIO modelo (:mod:`app.simulation.emt.steady_state`).
Sem esse preenchimento, os primeiros ``τ/Δt`` passos veriam histórico
nulo e a linha injetaria um degrau espúrio de amplitude igual à tensão
de regime.

Limitação declarada — dependência de frequência
================================================

Este modelo é de **parâmetros constantes** (CP / Bergeron): não
representa a dependência de frequência nem o acoplamento entre
condutores. O modelo dependente da frequência
[LITERATURA: J. R. Marti, "Accurate Modelling of Frequency-Dependent
Transmission Lines in Electromagnetic Transient Simulations", *IEEE
Trans. PAS*, vol. PAS-101, n. 1, pp. 147-157, 1982] está implementado
em :mod:`app.simulation.emt.jmarti` (:class:`~app.simulation.emt.jmarti.JMartiLine`
e :class:`~app.simulation.emt.jmarti.ModalJMartiLine`), com a MESMA
interface de componente — trocar de modelo não exige mudar mais nada do
circuito. O que segue descreve, portanto, o que se perde ao ficar
NESTE modelo. Impacto sobre a frente de onda, relevante para o estudo
de TRV de disjuntor a vácuo:

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

[CÁLCULO PRÓPRIO, tests/test_emt_jmarti.py] Medida do viés sobre a
mesma frente íngreme (cabo de 500 m com ``R' = 20 mΩ/m``,
``Δt = 5 ns``, fonte casada e terminação aberta): o Bergeron sem perdas
entrega pico de 100,000 V com ``dv/dt = 2,000·10¹⁰ V/s`` e tempo de
frente NULO na resolução de ``Δt`` — a onda sobe em um único passo,
qualquer que seja o comprimento —, enquanto o modelo dependente da
frequência entrega 99,194 V, ``1,750·10¹⁰ V/s`` (−12,5 %) e
``T1 = 1,29 µs``. O viés dominante é, portanto, o TEMPO DE FRENTE, não
a amplitude.
"""

from __future__ import annotations

import math
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

    def seed(
        self,
        times: Sequence[float],
        samples: Sequence[tuple[float, float, float, float]],
    ) -> None:
        """Substitui o buffer por um histórico pré-existente.

        ``times`` deve ser estritamente crescente e terminar em ``0,0``;
        os instantes NEGATIVOS representam o passado que a marcha no
        tempo não simulou — é assim que a onda de regime permanente
        entra no histórico de trânsito (ver
        :meth:`BergeronLine.seed_steady_state`).
        """
        ts = [float(t) for t in times]
        if len(ts) != len(samples) or not ts:
            raise ValueError("seed exige times e samples do mesmo tamanho, não vazios")
        if any(ts[k] >= ts[k + 1] for k in range(len(ts) - 1)):
            raise ValueError("seed exige times estritamente crescente")
        self._t = ts
        self._data = [
            (float(s[0]), float(s[1]), float(s[2]), float(s[3])) for s in samples
        ]
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
        #: Semente de regime permanente: ``(V̂_k, Î_km, V̂_m, Î_mk, ω, Δt)``
        #: ou ``None``. Preservada através de :meth:`reset`, como as
        #: condições iniciais dos elementos concentrados.
        self._seed: tuple[complex, complex, complex, complex, float, float] | None = None

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
                "elementos concentrados. Dommel 1969, p. 391, eleva nesse caso "
                "τ para Δt para preservar o equivalente da Fig. 1; aqui isso "
                "NÃO é feito, para que a divergência fique visível ao usuário",
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
        if self._seed is not None:
            self._apply_seed()

    # -- condição inicial em regime permanente ------------------------------

    def seed_steady_state(
        self,
        *,
        v_k: complex,
        i_km: complex,
        v_m: complex,
        i_mk: complex,
        omega_rad_s: float,
        dt: float,
    ) -> int:
        """Preenche o histórico de trânsito com a onda de regime permanente.

        Atende à exigência de [FONTE: Dommel 1969, Apêndice I, p. 395] de
        conhecer as grandezas terminais em ``t = 0, −Δt, …, −τ``. Os
        fasores são de AMPLITUDE com o cosseno como referência,
        ``x(t) = Re{X̂ e^{jωt}}`` [LISTA: 02, §1.4], e as correntes são as
        que ENTRAM na linha por cada terminal — a mesma convenção de
        :meth:`branch_current`.

        A semente é PRESERVADA por :meth:`reset`, de modo que a
        reexecução do solver reinicia sempre do mesmo regime permanente,
        exatamente como as condições iniciais de indutor e capacitor.
        Use :meth:`clear_steady_state_seed` para voltar à partida do
        repouso.

        Returns
        -------
        int
            Número de amostras escritas no buffer.
        """
        dt_f = _require_positive(dt, "dt")
        w = float(omega_rad_s)
        if not math.isfinite(w) or w <= 0.0:
            raise ValueError(f"omega_rad_s deve ser finita e > 0, obtida {omega_rad_s!r}")
        self._seed = (
            complex(v_k),
            complex(i_km),
            complex(v_m),
            complex(i_mk),
            w,
            dt_f,
        )
        return self._apply_seed()

    def clear_steady_state_seed(self) -> None:
        """Descarta a semente de regime e volta ao histórico nulo."""
        self._seed = None
        self._history.reset()

    def _apply_seed(self) -> int:
        """Escreve no buffer as amostras da onda de regime até ``−(τ + 2Δt)``."""
        assert self._seed is not None
        v_k, i_km, v_m, i_mk, w, dt_f = self._seed
        # Duas amostras de folga: a consulta mais antiga é em t = Δt − τ
        # (primeiro passo) e, com CDA na partida, em Δt/2 − τ; o buffer
        # precisa ENVOLVER esse instante para que a interpolação linear
        # não caia no ramo de retenção de ordem zero.
        n = int(math.ceil(self.travel_time_s / dt_f)) + 2
        times = [-(n - k) * dt_f for k in range(n + 1)]
        samples = []
        for t in times:
            rot = np.exp(1j * w * t)
            samples.append(
                (
                    float(np.real(v_k * rot)),
                    float(np.real(i_km * rot)),
                    float(np.real(v_m * rot)),
                    float(np.real(i_mk * rot)),
                )
            )
        self._history.seed(times, samples)
        last = samples[-1]
        self._v_k, self._i_km, self._v_m, self._i_mk = last
        return len(times)

    # -- estampagem ---------------------------------------------------------

    def _history_sources(self, t: float) -> tuple[float, float]:
        """Calcula ``(I_k, I_m)`` em ``t`` a partir do estado em ``t − τ``.

        Sem perdas (``ζ = 1``, ``a = 1``, ``b = 0``) reduz-se termo a
        termo a [FONTE: Dommel 1969, eq. (7b), p. 389]::

            I_k(t−τ) = −(1/Z_c)·e_m(t−τ) − i_mk(t−τ)
            I_m(t−τ) = −(1/Z_c)·e_k(t−τ) − i_km(t−τ)

        Com perdas concentradas, a forma refinada da aproximação
        ``R/4, R/2, R/4`` de [FONTE: Dommel 1969, p. 390] — ver a
        dedução e a verificação em corrente contínua no cabeçalho do
        módulo.
        """
        v_k_d, i_km_d, v_m_d, i_mk_d = self._history.value_at(t - self.travel_time_s)
        z = self._zeta
        a = 0.5 * (1.0 + z)
        b = 0.5 * (1.0 - z)
        i_k = -a * (v_m_d * self._g + z * i_mk_d) - b * (v_k_d * self._g + z * i_km_d)
        i_m = -a * (v_k_d * self._g + z * i_km_d) - b * (v_m_d * self._g + z * i_mk_d)
        return i_k, i_m

    def stamp_matrix(self, A: np.ndarray) -> None:
        """Estampa ``1/Z`` SÓ nas diagonais das duas extremidades.

        A ausência de termo fora da diagonal não é economia: é a própria
        estrutura do modelo das características, em que os dois
        terminais estão topologicamente desconectados e só se comunicam
        pelo histórico com atraso ``τ`` [FONTE: Dommel 1969, §I, p. 389
        e Fig. 1(b)].
        """
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
