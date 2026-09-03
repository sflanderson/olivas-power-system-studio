"""
app.postprocessor.prognosis.rul_estimator — estimação de RUL por filtro de
Kalman estendido (EKF) sobre tendência exponencial, e caminho determinístico
a partir do dano acumulado.

Escopo
======

Duas rotas independentes para a vida útil remanescente (RUL):

1. **Orientada a dados** — :class:`EkfRulEstimator`. Reproduz a
   arquitetura de Jensen, Strangas e Foster (2018) (artigo 02 do corpus):
   indicador de saúde com tendência exponencial, vetor de estados
   ``x = [I, α, β]^T``, EKF, projeção até um limiar de falha e RUL.

   Equações transcritas do artigo (p. 5-6)::

       x_k = F_{k-1} x_{k-1} + w_{k-1}                     (1)
       z_k = H_k x_k + v_k                                 (2)
       M_k = F_{k-1} P_{k-1} F_{k-1}^T + Q_{k-1}           (3)
       K_k = M_k H_k^T (H_k M_k H_k^T + R_k)^{-1}          (4)
       x_k = x_k + K_k (z_k - H_k x_k)                     (5)
       P_k = (I - K_k H_k) M_k                             (6)
       I_leak = α e^{β t}                                  (7)
       x = [I_leak, α, β]^T                                (8)

   [FATO: artigo 02, Jensen, Strangas e Foster, IEEE, 2018, p. 5-6].

   O artigo **não** explicita o jacobiano de ``F`` para (7) — "o leitor
   deve reconstruí-las de (7)-(8)". A reconstrução adotada aqui, com
   ``α`` e ``β`` modelados como passeio aleatório e o indicador
   reconstruído em tempo absoluto, é::

       I_k^- = α_{k-1} exp(β_{k-1} t_k)
       F = [[0, exp(β t_k), α t_k exp(β t_k)],
            [0,          1,                0],
            [0,          0,                1]]
       H = [1, 0, 0]

   [INFERÊNCIA — reconstrução do módulo, declarada como tal.]

2. **Determinístico** — :func:`rul_from_damage`, ``RUL = (1 - D)/dD/dt``,
   coerente com o acumulador (5.1)-(5.2) e com D7 (Etapa 1 §5.4).

Limitações declaradas (do artigo-fonte e do módulo)
====================================================

* O indicador de Jensen et al. foi validado com **envelhecimento
  térmico** em estatores de BT de 5 kW (n = 3 máquinas), monitorando
  fase-terra; os pulsos de excitação "were not designed to contribute to
  the degradation of the insulation" [FATO: artigo 02, p. 2-4].
* O pico do *overshoot* depende do dv/dt aplicado, e "the actual dV/dt of
  the switching device is **assumed to be constant** for this method to
  detect changes in the insulation properties" [FATO: artigo 02, p. 3] —
  num esquema com snubber, a variação de dv/dt introduzida pela própria
  mitigação deve ser compensada antes de usar a resposta ao impulso como
  precursor [INFERÊNCIA, Etapa 1 §7.3].
* O artigo **não reporta intervalos de RUL**: "o EKF fornece P_k, mas o
  artigo não reporta intervalos" [FATO por omissão: artigo 02]. O
  intervalo aqui é propagação de covariância pelo método delta
  (linearização de primeira ordem) — **não** é um intervalo de
  cobertura exata.
* Os parâmetros ``Q``, ``R`` e ``P_0`` do artigo (Tabela III) **não
  constam do texto acessado** [INSERIR CITAÇÃO]; os defaults deste
  módulo são NÃO CALIBRADOS.
* ISO 13381-1:2015, 3.3 e 3.9 exigem nível de confiança explícito na
  saída de prognóstico [NORMA]; :attr:`RulPrediction.confidence` cumpre
  esse requisito de forma.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Sequence

import numpy as np

# ---------------------------------------------------------------------------
# Defaults NÃO CALIBRADOS
# ---------------------------------------------------------------------------

#: Covariância de processo Q (diagonal) para [I, α, β]. Os valores da
#: Tabela III de Jensen et al. (2018) não constam do texto acessado
#: [INSERIR CITAÇÃO]. NÃO CALIBRADO — ordem de grandeza escolhida para
#: tratar α e β como quase constantes (passeio aleatório lento).
DEFAULT_Q_DIAG: tuple[float, float, float] = (1.0e-8, 1.0e-10, 1.0e-12)

#: Covariância de medição R (escalar). NÃO CALIBRADO.
DEFAULT_R: float = 1.0e-4

#: Covariância inicial P_0 (diagonal). NÃO CALIBRADO.
DEFAULT_P0_DIAG: tuple[float, float, float] = (1.0e-2, 1.0e-2, 1.0e-4)

#: Nível de confiança padrão do intervalo de RUL [NORMA: ISO 13381-1:2015,
#: 3.3, 3.9 — exige nível de confiança explícito].
DEFAULT_CONFIDENCE: float = 0.95

#: Limite numérico do argumento de exp(), para evitar overflow.
_MAX_EXPONENT: float = 700.0


# ---------------------------------------------------------------------------
# Saída de prognóstico
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RulPrediction:
    """Resultado de prognóstico com intervalo e nível de confiança.

    Attributes
    ----------
    rul:
        Vida útil remanescente estimada, na unidade de tempo usada nas
        atualizações (tipicamente horas).
    rul_lower, rul_upper:
        Extremos do intervalo, por propagação de covariância (método
        delta). ``rul_lower`` é saturado em 0.
    sigma:
        Desvio-padrão propagado do instante de falha.
    time_to_failure:
        Instante absoluto previsto de cruzamento do limiar.
    t_now:
        Instante da última atualização.
    threshold:
        Limiar de falha usado.
    confidence:
        Nível de confiança do intervalo [NORMA: ISO 13381-1:2015, 3.3].
    alpha, beta:
        Estado do modelo de tendência no instante da previsão.
    n_updates:
        Número de medições assimiladas.
    """

    rul: float
    rul_lower: float
    rul_upper: float
    sigma: float
    time_to_failure: float
    t_now: float
    threshold: float
    confidence: float
    alpha: float
    beta: float
    n_updates: int

    def summary(self) -> str:
        """Resumo textual determinístico."""
        return (
            f"RUL = {self.rul:.6g} "
            f"[{self.rul_lower:.6g}; {self.rul_upper:.6g}] "
            f"(confiança {self.confidence * 100:.1f} %, "
            f"σ = {self.sigma:.6g}, n = {self.n_updates} medições; "
            f"α = {self.alpha:.6g}, β = {self.beta:.6g}) "
            f"[ISO 13381-1:2015, 3.3]"
        )


# ---------------------------------------------------------------------------
# EKF
# ---------------------------------------------------------------------------


class EkfRulEstimator:
    """EKF com estado ``[indicador, α, β]`` sobre ``I(t) = α e^{β t}``.

    Padrão de Jensen, Strangas e Foster (2018) — artigo 02, eqs. (1)-(8),
    p. 5-6. Determinístico: mesmas entradas ⇒ mesmas saídas (sem RNG).

    Parameters
    ----------
    alpha0:
        Valor inicial de ``α`` (amplitude da tendência), != 0. O artigo
        atribui a ``α`` o primeiro pico observado: "first finds a peak
        value in the data and assigns that value to α" [FATO: artigo 02,
        p. 6].
    beta0:
        Valor inicial de ``β`` (taxa exponencial). Negativo para
        indicador decrescente, positivo para crescente.
    q_diag, r, p0_diag:
        Covariâncias ``Q``, ``R`` e ``P_0``. Defaults NÃO CALIBRADOS
        (ver :data:`DEFAULT_Q_DIAG`).
    t0:
        Origem da base de tempo do modelo de tendência.

    Raises
    ------
    ValueError
        ``alpha0 == 0``, covariâncias não positivas, ``r <= 0`` ou
        dimensões incorretas.
    """

    #: Dimensão do vetor de estados [I, α, β].
    N_STATES: int = 3

    def __init__(
        self,
        *,
        alpha0: float,
        beta0: float,
        q_diag: Sequence[float] = DEFAULT_Q_DIAG,
        r: float = DEFAULT_R,
        p0_diag: Sequence[float] = DEFAULT_P0_DIAG,
        t0: float = 0.0,
    ) -> None:
        if not math.isfinite(alpha0) or alpha0 == 0.0:
            raise ValueError(f"alpha0 deve ser finito e != 0, obtido {alpha0}")
        if not math.isfinite(beta0):
            raise ValueError(f"beta0 deve ser finito, obtido {beta0}")
        if not math.isfinite(r) or r <= 0.0:
            raise ValueError(f"r (covariância de medição) deve ser > 0, obtido {r}")
        if not math.isfinite(t0):
            raise ValueError(f"t0 deve ser finito, obtido {t0}")
        q = [float(x) for x in q_diag]
        p0 = [float(x) for x in p0_diag]
        if len(q) != self.N_STATES:
            raise ValueError(
                f"q_diag deve ter {self.N_STATES} elementos, obtido {len(q)}"
            )
        if len(p0) != self.N_STATES:
            raise ValueError(
                f"p0_diag deve ter {self.N_STATES} elementos, obtido {len(p0)}"
            )
        if any((not math.isfinite(x)) or x < 0.0 for x in q):
            raise ValueError(f"q_diag deve ser finito e >= 0, obtido {q}")
        if any((not math.isfinite(x)) or x <= 0.0 for x in p0):
            raise ValueError(f"p0_diag deve ser finito e > 0, obtido {p0}")

        self.t0: float = float(t0)
        self._t: float = float(t0)
        self._x: np.ndarray = np.array(
            [alpha0 * 1.0, alpha0, beta0], dtype=float
        )
        self._P: np.ndarray = np.diag(np.asarray(p0, dtype=float))
        self._Q: np.ndarray = np.diag(np.asarray(q, dtype=float))
        self._R: float = float(r)
        self._H: np.ndarray = np.array([[1.0, 0.0, 0.0]], dtype=float)
        self._n_updates: int = 0
        self._history: list[tuple[float, float, float, float]] = []

    # -- acesso ao estado ---------------------------------------------------

    @property
    def state(self) -> tuple[float, float, float]:
        """Estado corrente ``(I, α, β)``."""
        return (float(self._x[0]), float(self._x[1]), float(self._x[2]))

    @property
    def indicator(self) -> float:
        """Indicador filtrado ``I`` no último instante atualizado."""
        return float(self._x[0])

    @property
    def alpha(self) -> float:
        """``α`` corrente."""
        return float(self._x[1])

    @property
    def beta(self) -> float:
        """``β`` corrente."""
        return float(self._x[2])

    @property
    def covariance(self) -> np.ndarray:
        """Cópia de ``P`` (3x3)."""
        return self._P.copy()

    @property
    def t_now(self) -> float:
        """Instante da última atualização."""
        return self._t

    @property
    def n_updates(self) -> int:
        """Número de medições assimiladas."""
        return self._n_updates

    @property
    def history(self) -> list[tuple[float, float, float, float]]:
        """Histórico ``(t, I, α, β)`` após cada atualização."""
        return list(self._history)

    # -- núcleo do EKF ------------------------------------------------------

    @staticmethod
    def _safe_exp(value: float) -> float:
        return math.exp(max(-_MAX_EXPONENT, min(_MAX_EXPONENT, value)))

    def predict_indicator(self, t: float) -> float:
        """``I(t) = α e^{β (t - t0)}`` com o estado corrente (eq. 7)."""
        if not math.isfinite(t):
            raise ValueError(f"t deve ser finito, obtido {t}")
        return self.alpha * self._safe_exp(self.beta * (t - self.t0))

    def update(self, t: float, z: float) -> tuple[float, float, float]:
        """Assimila uma medição ``z`` do indicador no instante ``t``.

        Executa (3)-(6) do artigo 02 com o jacobiano reconstruído de (7).

        Returns
        -------
        tuple
            Estado ``(I, α, β)`` após a atualização.

        Raises
        ------
        ValueError
            ``t`` não finito, ``t`` anterior ao último instante, ou ``z``
            não finito.
        """
        if not math.isfinite(t):
            raise ValueError(f"t deve ser finito, obtido {t}")
        if not math.isfinite(z):
            raise ValueError(f"z deve ser finito, obtido {z}")
        if t < self._t:
            raise ValueError(
                f"t deve ser não decrescente: recebido {t} após {self._t}"
            )

        tau = t - self.t0
        alpha = float(self._x[1])
        beta = float(self._x[2])
        e = self._safe_exp(beta * tau)

        # (predição) x^- = f(x); α e β são passeio aleatório.
        x_pred = np.array([alpha * e, alpha, beta], dtype=float)

        # Jacobiano F = ∂f/∂x avaliado no estado anterior.
        F = np.array(
            [
                [0.0, e, alpha * tau * e],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=float,
        )

        # (3) M = F P F^T + Q
        M = F @ self._P @ F.T + self._Q

        # (4) K = M H^T (H M H^T + R)^-1
        S = float((self._H @ M @ self._H.T)[0, 0]) + self._R
        K = (M @ self._H.T) / S

        # (5) x = x^- + K (z - H x^-)
        innovation = z - float((self._H @ x_pred)[0])
        self._x = x_pred + (K * innovation).reshape(self.N_STATES)

        # (6) P = (I - K H) M
        eye = np.eye(self.N_STATES)
        self._P = (eye - K @ self._H) @ M

        self._t = float(t)
        self._n_updates += 1
        self._history.append((self._t, *self.state))
        return self.state

    def update_series(
        self, times: Sequence[float], values: Sequence[float]
    ) -> tuple[float, float, float]:
        """Assimila uma série completa; retorna o estado final.

        Raises
        ------
        ValueError
            Comprimentos diferentes ou série vazia.
        """
        if len(times) != len(values):
            raise ValueError(
                f"times e values devem ter o mesmo comprimento, obtidos "
                f"{len(times)} e {len(values)}"
            )
        if len(times) == 0:
            raise ValueError("a série de medições está vazia")
        for t, z in zip(times, values):
            self.update(float(t), float(z))
        return self.state

    # -- prognóstico --------------------------------------------------------

    def predict_rul(
        self,
        threshold: float,
        *,
        confidence: float = DEFAULT_CONFIDENCE,
    ) -> RulPrediction:
        """Projeta a tendência até ``threshold`` e retorna RUL com intervalo.

        Instante de falha: ``α e^{β T} = threshold`` ⇒
        ``T = ln(threshold/α)/β``; ``RUL = T - t_now``.

        Intervalo por método delta sobre ``(α, β)``::

            ∂T/∂α = -1/(α β)
            ∂T/∂β = -ln(threshold/α)/β² = -T/β
            var(T) = J P_{αβ} J^T

        [INFERÊNCIA — o artigo-fonte não reporta intervalos; ver
        limitações no docstring do módulo. NORMA: ISO 13381-1:2015, 3.3
        exige nível de confiança explícito.]

        Raises
        ------
        ValueError
            ``threshold`` não positivo quando ``α > 0`` (ou de sinal
            incompatível), ``β = 0``, ou tendência que **nunca** cruza o
            limiar (por exemplo indicador crescente com limiar abaixo do
            valor atual); ``confidence`` fora de (0, 1).
        """
        if not math.isfinite(threshold):
            raise ValueError(f"threshold deve ser finito, obtido {threshold}")
        if not math.isfinite(confidence) or not (0.0 < confidence < 1.0):
            raise ValueError(
                f"confidence deve estar em (0, 1), obtido {confidence}"
            )
        alpha = self.alpha
        beta = self.beta
        if beta == 0.0:
            raise ValueError(
                "β = 0: a tendência é constante e nunca cruza o limiar"
            )
        ratio = threshold / alpha
        if ratio <= 0.0:
            raise ValueError(
                f"threshold ({threshold}) e α ({alpha}) devem ter o mesmo "
                f"sinal: o modelo α e^{{β t}} nunca muda de sinal"
            )
        t_fail = math.log(ratio) / beta + self.t0
        rul = t_fail - self._t
        if rul < 0.0:
            raise ValueError(
                f"o limiar já foi cruzado em t = {t_fail:.6g} "
                f"(instante atual {self._t:.6g}): RUL negativa"
            )

        # Método delta sobre (α, β).
        tau_fail = t_fail - self.t0
        d_alpha = -1.0 / (alpha * beta)
        d_beta = -tau_fail / beta
        J = np.array([[d_alpha, d_beta]], dtype=float)
        P_ab = self._P[1:3, 1:3]
        var = float((J @ P_ab @ J.T)[0, 0])
        var = max(0.0, var)
        sigma = math.sqrt(var)
        z_score = NormalDist().inv_cdf(0.5 + confidence / 2.0)
        half = z_score * sigma

        return RulPrediction(
            rul=rul,
            rul_lower=max(0.0, rul - half),
            rul_upper=rul + half,
            sigma=sigma,
            time_to_failure=t_fail,
            t_now=self._t,
            threshold=threshold,
            confidence=confidence,
            alpha=alpha,
            beta=beta,
            n_updates=self._n_updates,
        )


# ---------------------------------------------------------------------------
# Caminho determinístico
# ---------------------------------------------------------------------------


def rul_from_damage(D: float, dD_dt: float) -> float:
    """``RUL = (1 - D) / (dD/dt)`` — caminho determinístico (D7).

    Coerente com ``RUL_N = (1 - D(t)) / E[ΔD_m]`` da Etapa 1 §5.4 (D7) e
    com o acumulador (5.1)-(5.2) da Etapa 2 §5.2. A unidade da saída é a
    inversa da unidade de ``dD_dt``.

    Retorna ``math.inf`` quando ``dD_dt = 0`` (nenhum dano em curso, por
    exemplo todos os eventos abaixo do limiar ``V_th``) e ``0.0`` quando
    ``D >= 1`` (falha convencionada).

    Raises
    ------
    ValueError
        ``D < 0``, ``dD_dt < 0`` ou valores não finitos.
    """
    if not math.isfinite(D) or D < 0.0:
        raise ValueError(f"D deve ser >= 0, obtido {D}")
    if not math.isfinite(dD_dt) or dD_dt < 0.0:
        raise ValueError(f"dD_dt deve ser >= 0, obtido {dD_dt}")
    if D >= 1.0:
        return 0.0
    if dD_dt == 0.0:
        return math.inf
    return (1.0 - D) / dD_dt
