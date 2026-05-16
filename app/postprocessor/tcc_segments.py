"""
app.postprocessor.tcc_segments — Segment-based TCC modeling
(v1.2.0 — paridade CAPTOR PTW Power*Tools).

Filosofia
==========

PTW Power*Tools CAPTOR modela cada dispositivo de proteção
como um conjunto de **segments** (segmentos atômicos da curva
tempo-corrente). Cada segment tem responsabilidade única e
parâmetros específicos:

* **Pickup LT/ST/INST** (Long-Time, Short-Time, Instantaneous)
* **Definite-time delay** (chão fixo após o pickup)
* **I²t element** (energy-limited)
* **Time-Current Points** (datasheet tabulado)
* **Analytic formulas** (AD formula, SM polynomial)
* **Breaker opening/clearing** (mechanical delay)
* **Bands & tolerances** (envelope min/max)

Um relé moderno SEL-751 ou ABB REF615 pode ter 4-6 segments
ativos simultaneamente: pickup LT (51) + ST (50backup) + INST
(50) + thermal (49). A função real é o **composite envelope**:

    t(I) = min over enabled segments of segment.time_at_current(I)

Esta sub-sprint (v1.2.0 α.1) entrega o **protocolo
TCCSegment** + **4 segments fundacionais** (LT, ST, INST,
DefiniteTime). Os outros 12+ vêm em α.2-α.5.

Compatibilidade
================

Este módulo é PARALELO ao ``tcc_curves.py`` legacy (v1.0.x +
v1.1.0). ``TCCCurve`` e ``FuseTCCCurve`` continuam exportados
por ``tcc_curves.py`` para retrocompatibilidade. A integração
das duas APIs está prevista para a Fase β (TCCDevice).

Cobertura normativa (α.1)
==========================

* IEC 60255-151:2009 — Functional requirements over/under
  current (Pickup characteristics)
* IEEE C37.112-2018 — Inverse-Time equations (constants
  A/B/p das curvas IEC/ANSI)
* IEEE Std 242-2001 (Buff Book) §15 — Coordenação
* ANSI/IEEE C37.2 — Standard device function numbers
  (51, 50, 50N, 49)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol, runtime_checkable

# Reusa CurveType + _CURVE_CONSTANTS do módulo legacy.
# Não duplica para evitar drift.
from app.postprocessor.tcc_curves import (
    CurveType, operating_time_s,
)


# ---------------------------------------------------------------------------
# Protocolo TCCSegment
# ---------------------------------------------------------------------------


@runtime_checkable
class TCCSegment(Protocol):
    """
    Interface mínima de um segment TCC.

    Cada segment representa **uma parcela** da característica
    tempo-corrente de um dispositivo. Múltiplos segments
    compõem um TCCDevice (Fase β).

    Métodos
    --------

    ``time_at_current(I_A)`` — retorna o tempo de operação
    (segundos) para a corrente dada. ``inf`` se não dispara.

    ``points(i_min, i_max, n)`` — gera pontos (I, t) para
    plot log-log. Pontos com t=∞ são excluídos.

    Atributos
    ----------

    ``segment_id`` — identificador humano-legível (ex:
    "51-LT IEC SI", "50-INST", "49-Thermal").

    ``enabled`` — se False, segment é ignorado em
    composições (composite envelope).
    """

    segment_id: str
    enabled: bool

    def time_at_current(self, current_A: float) -> float:
        ...

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        ...


# ---------------------------------------------------------------------------
# Helper compartilhado: gerar pontos log-log
# ---------------------------------------------------------------------------


def _generate_loglog_points(
    t_func,
    i_pickup_A: float,
    i_min_A: float,
    i_max_A: float,
    n_points: int,
) -> list[tuple[float, float]]:
    """
    Helper genérico: dado uma função ``t = f(I)`` e o pickup,
    gera pontos para plot log-log.

    Pontos com ``t = inf`` são excluídos.
    Garante que ``i_min_A`` é levantado para ``i_pickup_A * 1.001``
    se o pickup é maior — evita pontos abaixo da característica.
    """
    if i_min_A <= 0 or i_max_A <= i_min_A or n_points < 2:
        return []
    log_min = math.log10(max(i_min_A, i_pickup_A * 1.001))
    log_max = math.log10(i_max_A)
    if log_max <= log_min:
        return []
    step = (log_max - log_min) / (n_points - 1)
    pts: list[tuple[float, float]] = []
    for i in range(n_points):
        I = 10 ** (log_min + i * step)
        t = t_func(I)
        if math.isfinite(t):
            pts.append((I, t))
    return pts


# ---------------------------------------------------------------------------
# α.1 — Pickup LT (Long-Time) — função 51 / IEC LTPU
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCSegmentLT:
    """
    Pickup Long-Time (função 51, IDMT inverse-time).

    Replica o comportamento do ``TCCCurve`` legacy mas em
    formato segment para composição com outros elements
    (50, 49, 87) no mesmo dispositivo (Fase β).

    Convenção
    ----------

    Para ``current_A ≤ pickup_A``: ``time = inf`` (não
    dispara). Acima: ``operating_time_s(curve_type,
    M=I/Ipu, tms)``.

    Attributes
    -----------

    segment_id:
        ID humano (ex: "51 IEC SI", "51 ANSI Mod-Inv").
    pickup_A:
        Corrente de pickup (A primário).
    curve_type:
        Família IEC/ANSI (vide ``CurveType`` em ``tcc_curves``).
    tms:
        Time multiplier setting (0.05–1.0 tipicamente).
    enabled:
        Se False, ignorado em composição.

    Cobertura: IEC 60255-151:2009, IEEE C37.112-2018.
    """

    segment_id: str
    pickup_A: float
    curve_type: CurveType
    tms: float
    enabled: bool = True

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        if current_A <= self.pickup_A:
            return float("inf")
        m = current_A / self.pickup_A
        return operating_time_s(self.curve_type, m, self.tms)

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=self.pickup_A,
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


# ---------------------------------------------------------------------------
# α.1 — Pickup ST (Short-Time) — função 50backup com delay
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCSegmentST:
    """
    Pickup Short-Time (função 50ST / 51-Short).

    Definite-time element ABOVE pickup. PTW: "Short Time
    Pickup" segment usado em relés digitais (SEL-751, ABB
    REF615) como nível intermediário entre 51 LT e 50 INST.

    Convenção
    ----------

    Para ``current_A < pickup_A``: ``time = inf``.
    Para ``current_A ≥ pickup_A``: ``time = delay_s`` (fixo).

    Attributes
    -----------

    segment_id, pickup_A, delay_s, enabled

    Cobertura: IEC 60255-151:2009 §6.3.3 (definite-time
    elements).
    """

    segment_id: str
    pickup_A: float
    delay_s: float
    enabled: bool = True

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        if current_A < self.pickup_A:
            return float("inf")
        return self.delay_s

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=self.pickup_A,
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


# ---------------------------------------------------------------------------
# α.1 — Pickup INST (Instantaneous) — função 50
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCSegmentINST:
    """
    Pickup Instantaneous (função 50).

    Operação rápida sem delay propositado — só o tempo
    inerente do mecanismo do relé + breaker. Tipicamente
    20–50 ms.

    Convenção
    ----------

    Para ``current_A < pickup_A``: ``time = inf``.
    Para ``current_A ≥ pickup_A``: ``time = inherent_delay_s``
    (default 0.04 s = 2 cycles @ 50 Hz).

    Attributes
    -----------

    segment_id, pickup_A, inherent_delay_s (default 0.04),
    enabled.

    Cobertura: ANSI/IEEE C37.2 dev 50, IEC 60255-151 §6.3.4.
    """

    segment_id: str
    pickup_A: float
    inherent_delay_s: float = 0.04
    enabled: bool = True

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        if current_A < self.pickup_A:
            return float("inf")
        return self.inherent_delay_s

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=self.pickup_A,
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


# ---------------------------------------------------------------------------
# α.1 — Definite-time (51 definite, sem inverse-time)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCSegmentDefiniteTime:
    """
    Definite-time element (DT). Diferente de ST porque
    ``pickup_A`` aqui pode ser bem mais alto (típico de
    backup zone) e o ``delay`` é ajustável independente do
    setting do 51.

    Em PTW é o "Fix Time Horizontal" segment.

    Convenção
    ----------

    Idêntica a ST funcionalmente, mas ``segment_id`` deve
    refletir nomeclatura DT (ex: "51DT-Backup",
    "21-Definite").

    Attributes
    -----------

    segment_id, pickup_A, delay_s, enabled.

    Cobertura: IEC 60255-151 §6.3.3.
    """

    segment_id: str
    pickup_A: float
    delay_s: float
    enabled: bool = True

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        if current_A < self.pickup_A:
            return float("inf")
        return self.delay_s

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=self.pickup_A,
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


# ---------------------------------------------------------------------------
# Composite helper — minimum t(I) over enabled segments
# ---------------------------------------------------------------------------


def composite_time_at_current(
    segments: list,    # list[TCCSegment]
    current_A: float,
) -> float:
    """
    Calcula o tempo de operação composto: o **menor** tempo
    entre todos os segments habilitados.

    Em coordenação real, a função que dispara primeiro é a
    que conta — equivalente ao ``min`` analítico.

    Returns
    -------
    float
        Menor t entre todos enabled. ``inf`` se nenhum dispara.

    Notes
    -----
    Esta função é exportada para uso direto fora de
    TCCDevice (Fase β). Permite plot de "envelope composto"
    sem precisar instanciar device.
    """
    if not segments:
        return float("inf")
    times = [
        s.time_at_current(current_A)
        for s in segments
        if getattr(s, "enabled", True)
    ]
    if not times:
        return float("inf")
    return min(times)


# ---------------------------------------------------------------------------
# α.2 — Adjustable Tolerance (PTW: "Pickup with Adjustable Tolerance")
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCSegmentAdjustableTolerance:
    """
    Pickup com tolerância configurável ±%.

    Em PTW: o pickup do dispositivo varia entre
    ``pickup × (1 - tol/100)`` e ``pickup × (1 + tol/100)``,
    gerando uma **banda** no plot (envelope min e max).

    O método ``time_at_current()`` usa o pickup NOMINAL
    (centro da banda); helpers ``time_envelope_min`` e
    ``time_envelope_max`` retornam os extremos.

    Attributes
    -----------

    segment_id, pickup_A_nominal, curve_type, tms,
    tolerance_pct (0–50%), enabled.

    Cobertura: PTW Reference-CAPTOR.pdf §"Pickup with
    Adjustable Tolerance".
    """

    segment_id: str
    pickup_A_nominal: float
    curve_type: CurveType
    tms: float
    tolerance_pct: float = 10.0  # ±10% típico
    enabled: bool = True

    def _pickup_min(self) -> float:
        """Pickup mais sensível (curva mais rápida)."""
        return self.pickup_A_nominal * (1.0 - self.tolerance_pct / 100.0)

    def _pickup_max(self) -> float:
        """Pickup menos sensível (curva mais lenta)."""
        return self.pickup_A_nominal * (1.0 + self.tolerance_pct / 100.0)

    def time_at_current(self, current_A: float) -> float:
        """Tempo nominal (centro da banda)."""
        if not self.enabled:
            return float("inf")
        if current_A <= self.pickup_A_nominal:
            return float("inf")
        m = current_A / self.pickup_A_nominal
        return operating_time_s(self.curve_type, m, self.tms)

    def time_envelope_min(self, current_A: float) -> float:
        """Tempo mais rápido (pickup mais baixo)."""
        if not self.enabled:
            return float("inf")
        pkmin = self._pickup_min()
        if current_A <= pkmin:
            return float("inf")
        m = current_A / pkmin
        return operating_time_s(self.curve_type, m, self.tms)

    def time_envelope_max(self, current_A: float) -> float:
        """Tempo mais lento (pickup mais alto)."""
        if not self.enabled:
            return float("inf")
        pkmax = self._pickup_max()
        if current_A <= pkmax:
            return float("inf")
        m = current_A / pkmax
        return operating_time_s(self.curve_type, m, self.tms)

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        """Pontos da curva NOMINAL."""
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=self.pickup_A_nominal,
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )

    def envelope_min_points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        """Pontos do envelope mais rápido (pickup × (1-tol))."""
        return _generate_loglog_points(
            self.time_envelope_min,
            i_pickup_A=self._pickup_min(),
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )

    def envelope_max_points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        """Pontos do envelope mais lento (pickup × (1+tol))."""
        return _generate_loglog_points(
            self.time_envelope_max,
            i_pickup_A=self._pickup_max(),
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


# ---------------------------------------------------------------------------
# α.2 — I²t (Energy-limited element, fusíveis HRC + cabo damage)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCSegmentI2T:
    """
    I²t element — característica de energia constante.

    Para corrente ``I``, ``t = K_I2T / I²``. Modela:

    * Fusíveis HRC (envelope simplificado)
    * Cable damage curves (NBR 5410 §6.5.4)
    * Eletrônica de proteção com I²t protection

    Convenção
    ----------

    Para ``current_A < pickup_A``: ``time = inf``.
    Para ``current_A ≥ pickup_A``: ``time = K_I2T / I²``,
    clipped por ``time_floor_s`` (default 0.01s, evita
    tempos absurdos perto do limite mecânico).

    Attributes
    -----------

    segment_id, pickup_A, K_I2T_kA2_s (em kA²·s), time_floor_s,
    enabled.

    Cobertura: IEC 60269-1 (fuses I²t), NBR 5410 §6.5.4
    (cable thermal stress).
    """

    segment_id: str
    pickup_A: float
    K_I2T_kA2_s: float        # em kA²·s
    time_floor_s: float = 0.01
    enabled: bool = True

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        if current_A < self.pickup_A:
            return float("inf")
        # I²t: K em kA²·s, I em A → I_kA = I/1000, I_kA² = I²/1e6
        I_kA = current_A / 1000.0
        if I_kA <= 0:
            return float("inf")
        t = self.K_I2T_kA2_s / (I_kA ** 2)
        return max(t, self.time_floor_s)

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=self.pickup_A,
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


# ---------------------------------------------------------------------------
# α.2 — Time-Current Points (datasheet tabular)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCSegmentTimeCurrentPoints:
    """
    Curva tabulada por pontos (datasheet do fabricante).

    Recebe lista de tuples ``(I_A, t_s)`` ordenada por I.
    Interpolação log-log linear entre pontos. Fora do range:
    extrapolação por slope dos extremos (ou ``inf`` para
    abaixo do menor I).

    Útil para representar fielmente curvas de fusíveis
    específicos (datasheet Bussmann, Mersen) ou relés
    eletromecânicos antigos sem fórmula analítica simples.

    Attributes
    -----------

    segment_id, points: tuple[tuple[float, float], ...]
        Lista imutável de (I_A, t_s) em ordem crescente de I.
    enabled.

    Pré-condições
    --------------

    * Mínimo 2 pontos
    * Pontos ordenados por I crescente
    * Todos t > 0
    * Todos I > 0
    """

    segment_id: str
    point_pairs: tuple        # tuple[tuple[float, float], ...]
    enabled: bool = True

    def __post_init__(self):
        if len(self.point_pairs) < 2:
            raise ValueError(
                f"TCCSegmentTimeCurrentPoints precisa ≥2 pontos, "
                f"recebido {len(self.point_pairs)}"
            )
        prev_I = -1.0
        for I, t in self.point_pairs:
            if I <= 0 or t <= 0:
                raise ValueError(
                    f"pontos devem ter I>0 e t>0; obtido ({I}, {t})"
                )
            if I <= prev_I:
                raise ValueError(
                    f"pontos devem ser ordenados crescente por I; "
                    f"violação em I={I}"
                )
            prev_I = I

    def _i_min(self) -> float:
        return self.point_pairs[0][0]

    def _i_max(self) -> float:
        return self.point_pairs[-1][0]

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        if current_A < self._i_min():
            return float("inf")
        # Localiza interval que contém current_A
        for i in range(len(self.point_pairs) - 1):
            I0, t0 = self.point_pairs[i]
            I1, t1 = self.point_pairs[i + 1]
            if I0 <= current_A <= I1:
                # Interpolação log-log linear
                if I0 == I1:
                    return t0
                log_I = math.log10(current_A)
                log_I0 = math.log10(I0)
                log_I1 = math.log10(I1)
                log_t0 = math.log10(t0)
                log_t1 = math.log10(t1)
                slope = (log_t1 - log_t0) / (log_I1 - log_I0)
                log_t = log_t0 + slope * (log_I - log_I0)
                return 10 ** log_t
        # Acima do maior I — extrapolação por slope dos 2 últimos
        I_n2, t_n2 = self.point_pairs[-2]
        I_n1, t_n1 = self.point_pairs[-1]
        log_I = math.log10(current_A)
        log_I_n2 = math.log10(I_n2)
        log_I_n1 = math.log10(I_n1)
        log_t_n2 = math.log10(t_n2)
        log_t_n1 = math.log10(t_n1)
        slope = (log_t_n1 - log_t_n2) / (log_I_n1 - log_I_n2)
        log_t = log_t_n1 + slope * (log_I - log_I_n1)
        return max(10 ** log_t, 1e-6)  # floor numérico

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=self._i_min(),
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


# ---------------------------------------------------------------------------
# α.2 — Fix Time Horizontal (PTW segment, semântica idêntica a DT)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCSegmentFixTimeHorizontal:
    """
    Segmento de tempo fixo horizontal — característica
    horizontal no plot log-log.

    Idêntico funcionalmente ao ``TCCSegmentDefiniteTime``,
    mas mantido como classe distinta para preservar a
    semântica PTW ("Fix Time Horizontal" no Library editor)
    + permitir customizações futuras (cor padrão, label
    no plot, etc.).

    Diferença semântica vs. DefiniteTime
    -------------------------------------

    * **DT**: característica derivada de função de proteção
      específica (51DT, 21, etc.) com pickup definido.
    * **FixTime**: linha horizontal user-defined entre
      ``i_min`` e ``i_max`` (ex: tempo total do disjuntor
      mecânico = 5 ciclos = 0.083 s entre 100A e 50kA).

    Attributes
    -----------

    segment_id, time_s, i_min_A, i_max_A (default ∞), enabled.

    Cobertura
    ----------

    * IEC 60255-151:2009 §6.3.3 (definite-time elements)
    * PTW Reference-CAPTOR.pdf — segment "Fix Time Horizontal"
    * IEEE C37.04 (mechanical breaker time)
    """

    segment_id: str
    time_s: float
    i_min_A: float
    i_max_A: float = 1e9
    enabled: bool = True

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        if current_A < self.i_min_A or current_A > self.i_max_A:
            return float("inf")
        return self.time_s

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        # Os limites efetivos são interseção de [i_min_A, i_max_A]
        # do segment com [i_min_A, i_max_A] de plot range.
        eff_min = max(self.i_min_A, i_min_A)
        eff_max = min(self.i_max_A, i_max_A)
        if eff_max <= eff_min:
            return []
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=eff_min,
            i_min_A=eff_min,
            i_max_A=eff_max,
            n_points=n_points,
        )


# ---------------------------------------------------------------------------
# α.3 — PTW Analytic Formula AD
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCSegmentAnalyticAD:
    """
    PTW Analytic Formula "AD":

        T = AD / ((I/Ipu)^N - C) + BD + K

    onde:

    * ``AD`` (s) — coeficiente de escalonamento principal
    * ``N`` — expoente da curva (1.0 ≤ N ≤ ~3.0 típico)
    * ``C`` — offset do M (subtraído antes da exponenciação)
    * ``BD`` (s) — termo aditivo (offset de tempo)
    * ``K`` (s) — constante adicional

    Citação manual: ``Reference-CAPTOR.pdf`` página de
    "Pickup Curve formulas" (segment type "Analytic AD").

    Características
    ----------------

    * Para ``I/Ipu = C``: divisor zero → ``time = inf``
      (relé não dispara — é o "pickup efetivo").
    * Para ``I/Ipu < C``: ``(M^N - C)`` pode ficar negativo
      → também tratado como ``inf`` (não-físico).

    Convenção
    ----------

    Pickup efetivo é onde ``M^N = C``, i.e.,
    ``I = pickup_A × C^(1/N)``. Esta classe trata
    automaticamente isso e retorna ``inf`` abaixo.

    Attributes
    -----------

    segment_id, pickup_A (Ipu), AD, N, C, BD, K, enabled.

    Range de validade
    ------------------

    Função analítica generaliza IEEE C37.112: ANSI Mod-Inv
    é caso particular com (AD=0.0515, N=0.02, C=1.0, BD=0,
    K=0.114) — vide ``_CURVE_CONSTANTS`` em ``tcc_curves``.

    Esta versão expõe os 5 parâmetros para que datasheets
    PTW-curated específicos (relés digitais SEL/ABB com
    customização) possam ser modelados sem hard-coding.
    """

    segment_id: str
    pickup_A: float
    AD: float
    N: float
    C: float = 1.0
    BD: float = 0.0
    K: float = 0.0
    enabled: bool = True

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        if current_A <= 0 or self.pickup_A <= 0:
            return float("inf")
        if current_A <= self.pickup_A:
            return float("inf")
        m = current_A / self.pickup_A
        # M^N - C
        try:
            denom = (m ** self.N) - self.C
        except (ValueError, OverflowError):
            return float("inf")
        if denom <= 0:
            return float("inf")
        try:
            return self.AD / denom + self.BD + self.K
        except (ZeroDivisionError, OverflowError):
            return float("inf")

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        # Pickup efetivo: I onde M^N = C
        try:
            i_pickup_eff = self.pickup_A * (self.C ** (1.0 / self.N))
        except (ValueError, ZeroDivisionError):
            i_pickup_eff = self.pickup_A
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=i_pickup_eff,
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


# ---------------------------------------------------------------------------
# α.3 — PTW Analytic Formula SM (polynomial)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCSegmentAnalyticSM:
    """
    PTW Analytic Formula "SM" (polynomial fit):

        T = SM × [A + B(M - C) + D/(M - C)^2 + E/(M - C)^3]

    onde ``M = I / Ipu``.

    Citação manual: ``Reference-CAPTOR.pdf`` páginas de
    "Analytic SM" / fit polinomial multiparâmetro.

    Características
    ----------------

    * 5 parâmetros (A, B, D, E, C) + scalar SM permitem fit
      preciso de curvas de relés digitais com forma não-
      monotônica (ex: relé térmico com região plana entre
      surge e settle).
    * Divisores de ordem 2 e 3 dominam perto de M=C → curva
      diverge para infinito quando I aproxima de pickup
      efetivo.

    Convenção
    ----------

    Para ``I/Ipu ≤ C``: divisor zero/negativo → ``time = inf``.
    Idem para ``time < 0`` (caso o polinômio fique negativo
    em algum range — sinal de fit fora do domínio).

    Attributes
    -----------

    segment_id, pickup_A, SM, A, B, C, D, E, enabled.
    """

    segment_id: str
    pickup_A: float
    SM: float
    A: float
    B: float
    C: float
    D: float
    E: float
    enabled: bool = True

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        if current_A <= 0 or self.pickup_A <= 0:
            return float("inf")
        m = current_A / self.pickup_A
        delta = m - self.C
        if delta <= 0:
            return float("inf")
        try:
            poly = (
                self.A
                + self.B * delta
                + self.D / (delta ** 2)
                + self.E / (delta ** 3)
            )
        except (ZeroDivisionError, OverflowError):
            return float("inf")
        t = self.SM * poly
        if t <= 0 or not math.isfinite(t):
            return float("inf")
        return t

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        # Pickup efetivo: I = pickup × C
        i_pickup_eff = self.pickup_A * max(self.C, 1.0)
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=i_pickup_eff,
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


# ---------------------------------------------------------------------------
# α.4 — Breaker Opening / Clearing / OpenClearCurve / OpenClearBand
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCSegmentOpening:
    """
    Tempo de abertura mecânico de um disjuntor.

    PTW segment "Opening" — é o tempo entre o trip signal e o
    momento em que os contatos se separam (sem arco ainda).
    Tipicamente 2-3 ciclos:

    * LV Power CB: 1.5-3 cycles (25–50 ms @ 60 Hz)
    * HV Vacuum CB: 2-3 cycles (33–50 ms @ 60 Hz)
    * MV Air Magnetic: 4-6 cycles (66–100 ms @ 60 Hz)

    Convenção
    ----------

    Para ``current_A < pickup_A``: ``time = inf``.
    Acima: ``time = opening_time_s`` (constante).

    Cobertura: IEEE C37.04, IEC 62271-100.
    """

    segment_id: str
    pickup_A: float
    opening_time_s: float
    enabled: bool = True

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        if current_A < self.pickup_A:
            return float("inf")
        return self.opening_time_s

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=self.pickup_A,
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


@dataclass(frozen=True)
class TCCSegmentClearing:
    """
    Tempo total de extinção de arco em um disjuntor.

    PTW segment "Clearing" — é ``opening + arcing``. Para um
    LV Power CB típico: opening (3 cycles) + arcing (1-2
    cycles) = 4-5 cycles total = 67–83 ms @ 60 Hz.

    Para coordenação com fusível downstream, é o ``clearing``
    que importa (não o opening) — equivalente ao
    ``clear_time_at_current`` do ``FuseTCCCurve``.

    Convenção
    ----------

    Idêntica a Opening, com tempo maior. Mantido como classe
    distinta para preservar semântica e permitir:

    * Plot diferenciado (Opening tracejado, Clearing sólido)
    * Coordenação entre Opening (upstream backup) e
      Clearing (downstream primary)

    Cobertura: IEEE C37.04, IEC 62271-100, IEEE 242 §15.
    """

    segment_id: str
    pickup_A: float
    clearing_time_s: float
    enabled: bool = True

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        if current_A < self.pickup_A:
            return float("inf")
        return self.clearing_time_s

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=self.pickup_A,
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


@dataclass(frozen=True)
class TCCSegmentOpenClearCurve:
    """
    Composto: segmento base + adicional de arc extinguishing.

    PTW segment "Open-Clear Curve" — para dispositivos onde
    o fabricante dá uma curva inverse-time (ex: relé) e o
    tempo de breaker associado é constante adicional. O
    resultado é a curva total `t_relay(I) + t_breaker`.

    Usado em: ``MultiFunctionDevice`` (Fase β) para combinar
    automaticamente um segment LT/ST/INST com o tempo do
    disjuntor downstream.

    Convenção
    ----------

    ``time_at_current(I) = base_segment.time_at_current(I) +
    arc_extinguishing_s``.

    Se ``base_segment`` retorna ``inf``, idem aqui.

    Attributes
    -----------

    segment_id, base_segment, arc_extinguishing_s, enabled.

    Cobertura
    ----------

    * IEEE C37.04 — Power Circuit Breakers (arc extinction time)
    * IEC 62271-100 — High-voltage switchgear
    * IEEE 242:2001 §15.10 — Coordination time intervals
    * PTW Reference-CAPTOR.pdf — segment "Open-Clear Curve"
    """

    segment_id: str
    base_segment: object   # TCCSegment
    arc_extinguishing_s: float = 0.04   # 2 cycles @ 60Hz default
    enabled: bool = True

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        t_base = self.base_segment.time_at_current(current_A)
        if not math.isfinite(t_base):
            return float("inf")
        return t_base + self.arc_extinguishing_s

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        # Reusa pickup do segment base
        i_pickup = getattr(
            self.base_segment, "pickup_A",
            getattr(self.base_segment, "pickup_A_nominal", 1.0),
        )
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=i_pickup,
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


@dataclass(frozen=True)
class TCCSegmentOpenClearBand:
    """
    Banda entre 2 envelopes (Opening + Clearing).

    PTW segment "Open-Clear Bands" — para fusíveis e
    disjuntores onde o fabricante publica DUAS curvas:
    "minimum melt" / "maximum clear" (fusíveis) ou
    "fastest opening" / "slowest clearing" (breakers).

    Em log-log, a banda é uma faixa entre as 2 curvas —
    coordenação requer que o downstream esteja COMPLETAMENTE
    abaixo da banda upstream e o upstream COMPLETAMENTE
    acima da banda downstream.

    Convenção para ``time_at_current``
    -----------------------------------

    Por design, retorna o tempo CLEARING (envelope mais
    lento — pior caso para coordenação a montante). Usar
    ``time_opening`` e ``time_clearing`` para acessar os
    extremos individualmente.

    Attributes
    -----------

    segment_id, opening_segment, clearing_segment, enabled.

    Pré-condição
    -------------

    ``opening_segment.time_at_current(I)`` ≤
    ``clearing_segment.time_at_current(I)`` para todo I onde
    ambos retornam finitos. A classe NÃO valida — é
    responsabilidade do consumer.

    Cobertura
    ----------

    * IEC 60269-1:2014 — Fuses (min melt / total clear curves)
    * IEEE C37.04 — Power Circuit Breakers
    * IEEE 242:2001 §15.5.4 — Fuse-fuse / breaker bands coordination
    * PTW Reference-CAPTOR.pdf — segment "Open-Clear Bands"
    """

    segment_id: str
    opening_segment: object    # TCCSegment
    clearing_segment: object   # TCCSegment
    enabled: bool = True

    def time_opening(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        return self.opening_segment.time_at_current(current_A)

    def time_clearing(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        return self.clearing_segment.time_at_current(current_A)

    def time_at_current(self, current_A: float) -> float:
        """Retorna ``clearing`` (envelope superior — conservador)."""
        return self.time_clearing(current_A)

    def opening_points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        return self.opening_segment.points(i_min_A, i_max_A, n_points)

    def clearing_points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        return self.clearing_segment.points(i_min_A, i_max_A, n_points)

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        """Por consistência com Protocol: retorna clearing."""
        return self.clearing_points(i_min_A, i_max_A, n_points)


# ---------------------------------------------------------------------------
# α.5 — SlopeT + DelayBand
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCSegmentSlopeT:
    """
    PTW segment "Delay Band (I^Slope-T)" — característica
    com slope ajustável no plano log-log.

    Fórmula:

        T = K · (I / Ipu)^(-slope)

    Slope negativo = curva descendente (caso padrão de
    inverse-time). Slope=0 = horizontal (definite-time).
    Slope positivo = ascendente (raro mas possível em
    curvas de damage).

    Característica
    ---------------

    No plano log-log, é uma reta. O ``slope`` é o coeficiente
    angular dessa reta:

    * slope = 1: hipérbole "1/I" (típica I*t = const)
    * slope = 2: típica I²t (energia constante)
    * slope = 0.5: curva mais plana (relés eletrônicos
      com feedback)

    Convenção
    ----------

    Para ``current_A < pickup_A``: ``time = inf``.
    Acima: ``time = K · (I/Ipu)^(-slope)`` (slope ≥ 0
    convencional, mas aceita qualquer real).

    Attributes
    -----------

    segment_id, pickup_A, K (coeficiente, em segundos),
    slope (positivo para curva descendente), enabled.

    Cobertura: PTW Reference-CAPTOR.pdf "Delay Band".
    """

    segment_id: str
    pickup_A: float
    K: float
    slope: float
    enabled: bool = True

    def time_at_current(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        if current_A <= self.pickup_A:
            return float("inf")
        if self.pickup_A <= 0:
            return float("inf")
        m = current_A / self.pickup_A
        try:
            t = self.K * (m ** (-self.slope))
        except (OverflowError, ValueError):
            return float("inf")
        if t <= 0 or not math.isfinite(t):
            return float("inf")
        return t

    def points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        return _generate_loglog_points(
            self.time_at_current,
            i_pickup_A=self.pickup_A,
            i_min_A=i_min_A,
            i_max_A=i_max_A,
            n_points=n_points,
        )


@dataclass(frozen=True)
class TCCSegmentDelayBand:
    """
    Banda entre 2 SlopeT segments — uma "região" de tempos
    aceitáveis no log-log entre `min` e `max`.

    PTW segment "Delay Band com bands" — útil para
    representar relés eletrônicos com tolerância de fábrica
    onde a curva real fica dentro de uma faixa.

    Convenção para ``time_at_current``
    -----------------------------------

    Por design, retorna ``max_segment.time_at_current(I)``
    (envelope superior — conservador para coordenação a
    montante).

    Use ``time_min`` e ``time_max`` para acessar separadamente.

    Attributes
    -----------

    segment_id, min_segment (TCCSegmentSlopeT mais rápido),
    max_segment (TCCSegmentSlopeT mais lento), enabled.

    Pré-condição
    -------------

    ``min_segment.time_at_current(I) ≤ max_segment.time_at_current(I)``
    para todo I onde ambos retornam finito. NÃO valida.

    Cobertura
    ----------

    * IEC 60255-151:2009 §6.3 (delay element tolerance)
    * IEEE C37.112-2018 (curve manufacturing tolerance)
    * PTW Reference-CAPTOR.pdf — segment "Delay Band com bands"
    """

    segment_id: str
    min_segment: object   # TCCSegmentSlopeT (mais rápido)
    max_segment: object   # TCCSegmentSlopeT (mais lento)
    enabled: bool = True

    def time_min(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        return self.min_segment.time_at_current(current_A)

    def time_max(self, current_A: float) -> float:
        if not self.enabled:
            return float("inf")
        return self.max_segment.time_at_current(current_A)

    def time_at_current(self, current_A: float) -> float:
        """Retorna t_max (envelope conservador)."""
        return self.time_max(current_A)

    def min_points(
        self, i_min_A=1.0, i_max_A=1e6, n_points=100,
    ) -> list[tuple[float, float]]:
        return self.min_segment.points(i_min_A, i_max_A, n_points)

    def max_points(
        self, i_min_A=1.0, i_max_A=1e6, n_points=100,
    ) -> list[tuple[float, float]]:
        return self.max_segment.points(i_min_A, i_max_A, n_points)

    def points(
        self, i_min_A=1.0, i_max_A=1e6, n_points=100,
    ) -> list[tuple[float, float]]:
        """Por consistência com Protocol: retorna max."""
        return self.max_points(i_min_A, i_max_A, n_points)
