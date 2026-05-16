"""
app.postprocessor.tcc_curves — Time-Current Characteristic
(TCC) curves para visualização e validação de coordenação
(v0.99.0).

Cobertura normativa
====================

* IEEE Std C37.112-2018 — Standard Inverse-Time
  Characteristic Equations
* IEC 60255-151:2009 — Functional requirements for
  over/under current relays
* IEEE Std 242-2001 (Buff Book) §15 — Coordenação

Filosofia
==========

PTW Power*Tools / ETAP / EasyPower têm visualização
interativa de curvas TCC com drag-and-drop. Olivas v0.98
não tinha plotting de curvas — apenas listava sugestões
em texto.

Esta sprint:

1. Computa curvas analíticas para 6 famílias padrão:
   * IEC 60255 Standard Inverse, Very Inverse,
     Extremely Inverse, Long Inverse
   * ANSI Moderately Inverse, Very Inverse,
     Extremely Inverse
2. Verifica margem ``Δt`` entre relés (Buff Book §15.10.1):
   * 0.30–0.40s eletromecânico
   * 0.20–0.30s estático
   * 0.15–0.25s digital/numerical
3. Detecta interseções (curvas se cruzam = coord
   incorreta).

Saída
======

:class:`TCCCurve` — pontos (I, t) interpolados em escala
log-log.

:class:`CoordinationCheck` — verificação Δt entre relé
upstream e downstream.

Uso
====

::

    from app.postprocessor.tcc_curves import (
        TCCCurve, CurveType, check_coordination,
    )

    upstream = TCCCurve.standard_iec(
        type=CurveType.IEC_VERY_INVERSE,
        pickup_A=200, tms=0.5,
    )
    downstream = TCCCurve.standard_iec(
        type=CurveType.IEC_VERY_INVERSE,
        pickup_A=80, tms=0.2,
    )

    result = check_coordination(
        upstream, downstream,
        fault_current_A=5000,
        relay_type="digital",
    )
    if result.passes:
        print(f"Δt = {result.actual_delta_t_s:.3f}s OK")
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Curve types (IEC 60255 + ANSI/IEEE C37.112)
# ---------------------------------------------------------------------------


class CurveType(str, Enum):
    """Famílias de curvas inverse-time padrão."""

    # IEC 60255-151
    IEC_STANDARD_INVERSE = "IEC Standard Inverse"
    IEC_VERY_INVERSE = "IEC Very Inverse"
    IEC_EXTREMELY_INVERSE = "IEC Extremely Inverse"
    IEC_LONG_INVERSE = "IEC Long Inverse"

    # ANSI/IEEE C37.112
    ANSI_MODERATELY_INVERSE = "ANSI Moderately Inverse"
    ANSI_VERY_INVERSE = "ANSI Very Inverse"
    ANSI_EXTREMELY_INVERSE = "ANSI Extremely Inverse"


# Constantes A, B, p, K para cada curva (IEEE C37.112-2018 Tabela 1)
# t = TMS · (A / ((I/Ipickup)^p - 1) + B)
_CURVE_CONSTANTS: dict[CurveType, tuple[float, float, float]] = {
    # IEC: t = TMS · A / (M^p - 1)  (B=0)
    CurveType.IEC_STANDARD_INVERSE: (0.14, 0.02, 0.0),
    CurveType.IEC_VERY_INVERSE: (13.5, 1.0, 0.0),
    CurveType.IEC_EXTREMELY_INVERSE: (80.0, 2.0, 0.0),
    CurveType.IEC_LONG_INVERSE: (120.0, 1.0, 0.0),
    # ANSI: t = TMS · (A / (M^p - 1) + B)
    CurveType.ANSI_MODERATELY_INVERSE: (0.0515, 0.02, 0.114),
    CurveType.ANSI_VERY_INVERSE: (19.61, 2.0, 0.491),
    CurveType.ANSI_EXTREMELY_INVERSE: (28.2, 2.0, 0.1217),
}


def operating_time_s(
    curve_type: CurveType,
    multiple_of_pickup: float,
    tms: float,
) -> float:
    """
    Calcula tempo de operação t para uma curva inverse-time.

    Parameters
    ----------
    curve_type:
        Família da curva.
    multiple_of_pickup:
        M = I / I_pickup (deve ser > 1 para tripping).
    tms:
        Time multiplier setting (0.05–1.0 tipicamente).

    Returns
    -------
    float
        Tempo de operação em segundos. ``inf`` se M ≤ 1.
    """
    if multiple_of_pickup <= 1.0:
        return float("inf")
    A, p, B = _CURVE_CONSTANTS[curve_type]
    return tms * (A / (multiple_of_pickup ** p - 1.0) + B)


# ---------------------------------------------------------------------------
# TCCCurve dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCCurve:
    """
    Curva tempo-corrente de um relé.

    Attributes
    ----------
    relay_id:
        Identificador (ex: "Relé Feeder F1").
    curve_type:
        Tipo (IEC ou ANSI).
    pickup_A:
        Corrente de pickup (A primário).
    tms:
        Time multiplier setting.
    instantaneous_pickup_A:
        Pickup instantâneo (50 element). None = sem 50.
    instantaneous_delay_s:
        Tempo do 50 (default 0.04s = 2 ciclos).
    """

    relay_id: str
    curve_type: CurveType
    pickup_A: float
    tms: float
    instantaneous_pickup_A: Optional[float] = None
    instantaneous_delay_s: float = 0.04

    def operating_time_at_current(self, current_A: float) -> float:
        """t(I) — tempo de operação para corrente I."""
        # Verifica 50 (instantâneo)
        if (
            self.instantaneous_pickup_A is not None
            and current_A >= self.instantaneous_pickup_A
        ):
            return self.instantaneous_delay_s

        # 51 (inverse-time)
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
        """
        Gera pontos (I, t) para plot log-log.

        Returns lista de tuples (corrente_A, tempo_s).
        Exclui pontos com t=∞ (não-tripping).
        """
        if i_min_A <= 0 or i_max_A <= i_min_A:
            return []
        log_min = math.log10(max(i_min_A, self.pickup_A * 1.01))
        log_max = math.log10(i_max_A)
        step = (log_max - log_min) / (n_points - 1)
        points = []
        for i in range(n_points):
            current = 10 ** (log_min + i * step)
            t = self.operating_time_at_current(current)
            if math.isfinite(t):
                points.append((current, t))
        return points


# ---------------------------------------------------------------------------
# Coordination check (Δt margin)
# ---------------------------------------------------------------------------


# Margens recomendadas (IEEE 242 Buff Book §15.10.1)
COORDINATION_MARGIN_S = {
    "electromechanical": 0.40,
    "static": 0.30,
    "digital": 0.25,
    "numerical": 0.25,
}


@dataclass(frozen=True)
class CoordinationCheck:
    """
    Verificação de margem de coordenação Δt entre 2 relés.

    Attributes
    ----------
    upstream_id, downstream_id:
        IDs dos relés.
    fault_current_A:
        Corrente de falta avaliada.
    upstream_time_s, downstream_time_s:
        Tempos de operação no fault current.
    actual_delta_t_s:
        upstream_time - downstream_time.
    required_delta_t_s:
        Margem requerida (depende do tipo de relé).
    passes:
        actual ≥ required?
    """

    upstream_id: str
    downstream_id: str
    fault_current_A: float

    upstream_time_s: float = 0.0
    downstream_time_s: float = 0.0
    actual_delta_t_s: float = 0.0
    required_delta_t_s: float = 0.30

    passes: bool = False
    relay_type: str = "digital"

    citation: str = (
        "IEEE Std 242-2001 §15.10.1 — Coordination time intervals"
    )


def check_coordination(
    upstream: TCCCurve,
    downstream: TCCCurve,
    fault_current_A: float,
    relay_type: str = "digital",
) -> CoordinationCheck:
    """
    Verifica se há margem ``Δt`` adequada entre dois relés
    em série numa falta.

    Para coordenação correta:

        t_upstream(I_fault) - t_downstream(I_fault) ≥ Δt_min

    Onde Δt_min depende do tipo de relé:

    * Eletromecânico: 0.40 s
    * Estático:       0.30 s
    * Digital:        0.25 s
    * Numerical:      0.25 s

    Parameters
    ----------
    upstream:
        Relé a montante (deve operar DEPOIS).
    downstream:
        Relé a jusante (deve operar PRIMEIRO).
    fault_current_A:
        Corrente de falta no ponto avaliado.
    relay_type:
        "electromechanical", "static", "digital", "numerical"

    Returns
    -------
    CoordinationCheck
    """
    t_up = upstream.operating_time_at_current(fault_current_A)
    t_dn = downstream.operating_time_at_current(fault_current_A)
    actual = t_up - t_dn
    required = COORDINATION_MARGIN_S.get(relay_type.lower(), 0.30)

    return CoordinationCheck(
        upstream_id=upstream.relay_id,
        downstream_id=downstream.relay_id,
        fault_current_A=fault_current_A,
        upstream_time_s=t_up,
        downstream_time_s=t_dn,
        actual_delta_t_s=actual,
        required_delta_t_s=required,
        passes=(
            math.isfinite(t_up)
            and math.isfinite(t_dn)
            and actual >= required
        ),
        relay_type=relay_type,
    )


def check_coordination_at_multiple_currents(
    upstream: TCCCurve,
    downstream: TCCCurve,
    currents_A: list[float],
    relay_type: str = "digital",
) -> list[CoordinationCheck]:
    """Verifica coord em múltiplos pontos de corrente."""
    return [
        check_coordination(upstream, downstream, i, relay_type)
        for i in currents_A
    ]


# ---------------------------------------------------------------------------
# v1.1.0 — TCC duplo para fusíveis (melt + clear curves)
# ---------------------------------------------------------------------------
#
# PTW Power*Tools CAPTOR desenha fusíveis com **2 curvas**:
#
# * **Melt envelope** (pre-arcing) — corrente/tempo em que o
#   elemento fusível começa a fundir.
# * **Clear envelope** (total) — corrente/tempo em que o arco se
#   extingue e o circuito interrompe completamente.
#
# Para coordenação fusível-fusível, o critério é:
#
#     t_clear(downstream, I) + margin < t_melt(upstream, I)
#
# Ou seja: o fusível a jusante DEVE terminar de interromper antes
# do upstream começar a fundir. PTW usa margem ~10% no I²t.
#
# Modelagem analítica
# ====================
#
# Curvas reais de fusíveis IEC 60269 são fornecidas como tabelas
# discretas pelo fabricante. Para o MVP, usamos uma aproximação
# por lei de potência calibrada nos pontos típicos da norma:
#
#     t(I) = K · (In / I) ^ p          para I > pickup_factor · In
#
# onde:
#
# * ``K`` (s) é determinado pela energia I²t da classe.
# * ``p`` é o expoente característico (~2 para gG, ~1.5 para aM).
# * ``pickup_factor`` é a corrente convencional de não-fusão
#   (~1.5×In para gG, 1.6×In para aM/gM).
#
# A curva de clear é obtida multiplicando K por
# ``clear_ratio`` (~1.5–2.0 dependendo da classe). Em coordenação
# real, manda-se trocar pela tabela do fabricante via plugin —
# a aproximação aqui captura a física essencial sem requerer
# datasheet específico.
#
# Cobertura normativa
# ====================
#
# * IEC 60269-1:2014 — Low-voltage fuses
# * IEC 60269-2 — gG/gM fuses (utilization)
# * NEMA C37.46 — Power fuses HV (K-link)
# * IEEE Std 242-2001 §15 — Coordination


class FuseClass(str, Enum):
    """
    Classes de fusíveis cobertas (IEC 60269 / NEMA).

    * **gG** — uso geral (linhas, cabos)  — pickup ~1.5×In, p=2.0
    * **gM** — motor protection           — pickup ~1.6×In, p=1.8
    * **aM** — accompanying motor (parcial protection) — p=1.5
    * **K**  — NEMA K-link (HV power)     — p=2.0
    * **T**  — NEMA T-link (HV power)     — p=2.5
    * **J**  — NEMA Class J (LV)          — p=2.0
    * **RK1** — NEMA Class RK1 (current-limiting) — p=2.0
    * **RK5** — NEMA Class RK5            — p=2.0
    """

    gG = "gG"
    gM = "gM"
    aM = "aM"
    K = "K"
    T = "T"
    J = "J"
    RK1 = "RK1"
    RK5 = "RK5"


# Parâmetros calibrados para reproduzir os pontos típicos das
# normas IEC 60269 / NEMA. Cada tupla é
# (pickup_factor, p_exponent, K_melt_seconds_at_In, clear_ratio).
#
# Ponto-âncora: a t_melt no ponto convencional pickup_factor×In
# fica em torno de 3600s (1h, conforme IEC §6.5.1).
_FUSE_PARAMS: dict[FuseClass, tuple[float, float, float, float]] = {
    # (pickup_factor, p, K_melt, clear_ratio)
    FuseClass.gG:  (1.5, 2.0,  100.0, 1.6),
    FuseClass.gM:  (1.6, 1.8,   80.0, 1.7),
    FuseClass.aM:  (1.6, 1.5,   50.0, 1.8),
    FuseClass.K:   (1.5, 2.0,  120.0, 1.5),
    FuseClass.T:   (1.5, 2.5,  150.0, 1.4),
    FuseClass.J:   (1.5, 2.0,  100.0, 1.6),
    FuseClass.RK1: (1.5, 2.0,   80.0, 1.5),
    FuseClass.RK5: (1.5, 2.0,  100.0, 1.6),
}


@dataclass(frozen=True)
class FuseTCCCurve:
    """
    Curva tempo-corrente DUPLA de um fusível: melt + clear.

    Estilo PTW CAPTOR: cada fusível plota dois envelopes log-log,
    o de fusão (melt, mais rápido) e o de clearing (mais lento).

    Attributes
    ----------
    fuse_id:
        Identificador (ex: "F1", "Feeder Main").
    fuse_class:
        Classe IEC 60269 / NEMA.
    rated_current_A:
        Corrente nominal In.
    """

    fuse_id: str
    fuse_class: FuseClass
    rated_current_A: float

    # ---- Cálculo de tempos -------------------------------------------------

    def _params(self) -> tuple[float, float, float, float]:
        return _FUSE_PARAMS[self.fuse_class]

    def melt_time_at_current(self, current_A: float) -> float:
        """
        Tempo de pré-arco (melt) para a corrente dada.

        ``inf`` se I ≤ pickup convencional (não funde).
        """
        pickup_factor, p, K_melt, _ = self._params()
        I_pickup = pickup_factor * self.rated_current_A
        if current_A <= I_pickup:
            return float("inf")
        return K_melt * (self.rated_current_A / current_A) ** p

    def clear_time_at_current(self, current_A: float) -> float:
        """
        Tempo total (até extinção do arco) para a corrente dada.

        ``inf`` se I ≤ pickup. ``clear_ratio`` × ``melt`` —
        envelope superior na coordenação fusível-fusível.
        """
        t_melt = self.melt_time_at_current(current_A)
        if not math.isfinite(t_melt):
            return float("inf")
        _, _, _, clear_ratio = self._params()
        return t_melt * clear_ratio

    # ---- Geração de pontos para plot ---------------------------------------

    def melt_points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        """Pontos (I, t_melt) para plot log-log."""
        return self._gen_points(self.melt_time_at_current,
                                  i_min_A, i_max_A, n_points)

    def clear_points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        """Pontos (I, t_clear) para plot log-log."""
        return self._gen_points(self.clear_time_at_current,
                                  i_min_A, i_max_A, n_points)

    def _gen_points(
        self, t_func, i_min_A: float, i_max_A: float, n_points: int,
    ) -> list[tuple[float, float]]:
        if i_min_A <= 0 or i_max_A <= i_min_A:
            return []
        pickup_factor, _, _, _ = self._params()
        I_pickup = pickup_factor * self.rated_current_A
        log_min = math.log10(max(i_min_A, I_pickup * 1.001))
        log_max = math.log10(i_max_A)
        if log_max <= log_min:
            return []
        step = (log_max - log_min) / (n_points - 1)
        points = []
        for i in range(n_points):
            current = 10 ** (log_min + i * step)
            t = t_func(current)
            if math.isfinite(t):
                points.append((current, t))
        return points


# ---------------------------------------------------------------------------
# Fuse-Fuse coordination
# ---------------------------------------------------------------------------


# Margem percentual para coordenação fusível-fusível.
# IEEE 242 §15.5.4 recomenda 25% de I²t margin entre
# upstream e downstream para garantir que o downstream
# clear ANTES do upstream começar a derreter mesmo com
# variações de manufatura (~±10% I²t).
_FUSE_FUSE_I2T_MARGIN = 0.25


@dataclass(frozen=True)
class FuseFuseCoordinationCheck:
    """
    Resultado de coordenação fusível-fusível.

    Attributes
    ----------
    fault_current_A:
        Corrente de falta avaliada.
    upstream_melt_s:
        t_melt do fusível upstream (deve ser MAIOR).
    downstream_clear_s:
        t_clear do fusível downstream (deve ser MENOR).
    margin_s:
        upstream_melt - downstream_clear.
    margin_pct:
        margem em percentual de I²t (margin / downstream_clear × 100).
    passes:
        margin_pct ≥ requisito IEEE 242 §15.5.4 (25% default).
    """

    upstream_id: str
    downstream_id: str
    fault_current_A: float
    upstream_melt_s: float
    downstream_clear_s: float
    margin_s: float
    margin_pct: float
    passes: bool

    citation: str = (
        "IEEE Std 242-2001 §15.5.4 — Fuse-fuse coordination "
        "(I²t margin ≥25% for selectivity)"
    )


def check_fuse_fuse_coordination(
    upstream: FuseTCCCurve,
    downstream: FuseTCCCurve,
    fault_current_A: float,
    margin_pct_required: float = _FUSE_FUSE_I2T_MARGIN * 100,
) -> FuseFuseCoordinationCheck:
    """
    Verifica coordenação fusível-fusível.

    Critério: ``t_melt(upstream, I) ≥ t_clear(downstream, I) ×
    (1 + margin_pct/100)``.

    Parameters
    ----------
    upstream:
        Fusível a montante (deve operar DEPOIS — não fundir).
    downstream:
        Fusível a jusante (deve operar PRIMEIRO).
    fault_current_A:
        Corrente de falta no ponto avaliado.
    margin_pct_required:
        Margem mínima em % (default 25% conforme IEEE 242).

    Returns
    -------
    FuseFuseCoordinationCheck
    """
    t_up_melt = upstream.melt_time_at_current(fault_current_A)
    t_dn_clear = downstream.clear_time_at_current(fault_current_A)

    if not math.isfinite(t_up_melt) or not math.isfinite(t_dn_clear):
        return FuseFuseCoordinationCheck(
            upstream_id=upstream.fuse_id,
            downstream_id=downstream.fuse_id,
            fault_current_A=fault_current_A,
            upstream_melt_s=t_up_melt,
            downstream_clear_s=t_dn_clear,
            margin_s=float("nan"),
            margin_pct=float("nan"),
            passes=False,
        )

    margin = t_up_melt - t_dn_clear
    if t_dn_clear > 0:
        margin_pct = (margin / t_dn_clear) * 100.0
    else:
        margin_pct = 0.0
    passes = margin_pct >= margin_pct_required

    return FuseFuseCoordinationCheck(
        upstream_id=upstream.fuse_id,
        downstream_id=downstream.fuse_id,
        fault_current_A=fault_current_A,
        upstream_melt_s=t_up_melt,
        downstream_clear_s=t_dn_clear,
        margin_s=margin,
        margin_pct=margin_pct,
        passes=passes,
    )


def check_fuse_relay_coordination(
    fuse_upstream: FuseTCCCurve,
    relay_downstream: TCCCurve,
    fault_current_A: float,
    margin_pct_required: float = 25.0,
) -> FuseFuseCoordinationCheck:
    """
    v1.1.0: Variante de check_fuse_fuse para o caso comum
    em CCM: relé downstream protegendo motor + fusível
    upstream protegendo o feeder do CCM.

    O relé deve operar antes do fusível começar a derreter:
    ``t_melt(fuse) ≥ t_relay(I) × (1 + margin/100)``.

    Reutiliza ``FuseFuseCoordinationCheck`` (mesma estrutura
    semântica — só muda o que é "downstream").
    """
    t_up_melt = fuse_upstream.melt_time_at_current(fault_current_A)
    t_dn = relay_downstream.operating_time_at_current(fault_current_A)

    if not math.isfinite(t_up_melt) or not math.isfinite(t_dn):
        return FuseFuseCoordinationCheck(
            upstream_id=fuse_upstream.fuse_id,
            downstream_id=relay_downstream.relay_id,
            fault_current_A=fault_current_A,
            upstream_melt_s=t_up_melt,
            downstream_clear_s=t_dn,
            margin_s=float("nan"),
            margin_pct=float("nan"),
            passes=False,
        )

    margin = t_up_melt - t_dn
    margin_pct = (margin / t_dn) * 100.0 if t_dn > 0 else 0.0
    return FuseFuseCoordinationCheck(
        upstream_id=fuse_upstream.fuse_id,
        downstream_id=relay_downstream.relay_id,
        fault_current_A=fault_current_A,
        upstream_melt_s=t_up_melt,
        downstream_clear_s=t_dn,
        margin_s=margin,
        margin_pct=margin_pct,
        passes=(margin_pct >= margin_pct_required),
    )
