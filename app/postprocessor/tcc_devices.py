"""
app.postprocessor.tcc_devices — Multi-function protection
devices (v1.2.0 Fase β — paridade CAPTOR PTW).

Filosofia
==========

PTW Power*Tools CAPTOR modela cada **dispositivo** de
proteção (relé SEL-751, ABB REF615, breaker MCCB com trip
unit, fusível com 2 envelopes) como um container de N
``TCCSegment`` (vide ``tcc_segments.py``). Múltiplas
funções (50/51/49/87, etc.) coexistem no mesmo device, e
a curva visível é o **composite envelope**:

    t_device(I) = min over enabled segments of t_segment(I)

Este módulo expõe:

* :class:`TCCDevice` — container genérico (β.1)
* :class:`MultiFunctionRelay` — subclasse com helpers
  para padrões comuns 50/51/49/87 (β.2)
* :func:`check_device_coordination` — verifica Δt entre
  dois devices considerando todos os segments
  simultaneamente, identifica qual segment "venceu" no
  envelope (β.3)

Compatibilidade
================

Este módulo é **paralelo** a:

* ``tcc_curves.py`` (v1.1.0 — TCCCurve, FuseTCCCurve, legacy)
* ``tcc_segments.py`` (v1.2.0 α — 16 segment types)

O legacy permanece exportado para retrocompatibilidade.
A integração GUI virá em Fase δ.

Cobertura normativa
====================

* IEC 60255-151:2009 (relé multi-função)
* IEEE C37.112-2018 (curve types)
* IEEE C37.04 (breakers)
* IEEE 242:2001 (Buff Book) §15 (coordenação)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from app.postprocessor.tcc_segments import (
    TCCSegment,
    composite_time_at_current,
)


# ---------------------------------------------------------------------------
# β.1 — TCCDevice base
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TCCDevice:
    """
    Container imutável de N ``TCCSegment`` formando um
    dispositivo de proteção.

    Cobertura normativa
    --------------------

    * IEC 60255-151:2009 (multi-function relays)
    * IEEE C37.2-2008 (device function numbers — 50/51/49/87)
    * IEEE C37.04-2018 (Power Circuit Breakers)
    * IEEE 242:2001 (Buff Book) — coordenação
    * PTW Reference-CAPTOR.pdf — "Multiple Functions per
      Protection Component"

    Diferença vs. TCCCurve legacy
    ------------------------------

    * ``TCCCurve`` (v1.1.0): 1 característica IDMT ± 50
      simples — modela 1 função apenas.
    * ``TCCDevice`` (v1.2.0): N segments simultâneos — modela
      um dispositivo real (relé multi-função, breaker com
      trip unit LSI, fusível com melt+clear).

    Estado dinâmico
    ----------------

    Para alterar enable/disable de um segment durante análise,
    use :meth:`with_segment_enabled` que retorna **nova
    instância** (pattern functional). Não muta in-place
    porque o dataclass é ``frozen=True``.

    Imutabilidade real
    -------------------

    Atributos do dataclass usam ``tuple`` (não ``list``)
    para que mutação acidental seja detectada cedo.
    ``__post_init__`` valida formato.

    Attributes
    ----------

    device_id:
        Identificador humano único (ex: "SEL-751 main feeder").
    manufacturer:
        Fabricante (default "Generic"). Útil para audit + UI.
    model:
        Modelo específico (default "Generic"). Idem.
    segments:
        Tuple imutável de TCCSegment. Cada um pode ter
        enabled=True/False. Para device sem segments
        (placeholder), use ``segments=()``.
    """

    device_id: str
    manufacturer: str = "Generic"
    model: str = "Generic"
    segments: tuple = ()    # tuple[TCCSegment, ...]

    def __post_init__(self) -> None:
        # Aceita tuple (preferido) ou list (mas converte para tuple)
        # — proteção contra erros comuns. dataclass frozen permite
        # mutação via object.__setattr__ no __post_init__.
        if not isinstance(self.segments, tuple):
            object.__setattr__(self, "segments", tuple(self.segments))
        # Sanity check: todo elemento satisfaz Protocol
        for i, s in enumerate(self.segments):
            if not isinstance(s, TCCSegment):
                raise TypeError(
                    f"TCCDevice.segments[{i}] não satisfaz Protocol "
                    f"TCCSegment (tipo recebido: {type(s).__name__})"
                )

    # ---- Computação de tempo / pontos -----------------------------

    def composite_time_at_current(self, current_A: float) -> float:
        """
        Tempo composto do device: ``min`` sobre todos os
        segments habilitados.

        Reusa ``tcc_segments.composite_time_at_current``.
        """
        return composite_time_at_current(list(self.segments), current_A)

    def composite_points(
        self,
        i_min_A: float = 1.0,
        i_max_A: float = 1e6,
        n_points: int = 200,
    ) -> list[tuple[float, float]]:
        """
        Pontos do **envelope composto** para plot log-log.

        Densidade default 200 (>= um TCCSegment individual)
        para capturar transições entre segments adjacentes
        (ex: junção LT → INST onde a curva colapsa de
        inverse-time para definite-time).
        """
        if i_min_A <= 0 or i_max_A <= i_min_A or n_points < 2:
            return []
        log_min = math.log10(i_min_A)
        log_max = math.log10(i_max_A)
        step = (log_max - log_min) / (n_points - 1)
        pts: list[tuple[float, float]] = []
        for i in range(n_points):
            I = 10 ** (log_min + i * step)
            t = self.composite_time_at_current(I)
            if math.isfinite(t):
                pts.append((I, t))
        return pts

    # ---- Identificação do segment "vencedor" ----------------------

    def triggered_segment(self, current_A: float):
        """
        Retorna o ``TCCSegment`` cujo ``time_at_current`` é
        igual ao composite (o "vencedor" na corrente dada).

        Útil para debug: "qual função do relé disparou no
        fault de 5 kA?" — resposta tipicamente "50 INST" ou
        "51 LT".

        Returns
        -------
        TCCSegment ou None
            Segment com tempo mínimo entre os enabled.
            ``None`` se nenhum segment dispara (composite=∞).
        """
        if not self.segments:
            return None
        winner = None
        winner_t = float("inf")
        for s in self.segments:
            if not getattr(s, "enabled", True):
                continue
            t = s.time_at_current(current_A)
            if math.isfinite(t) and t < winner_t:
                winner_t = t
                winner = s
        return winner

    # ---- Mutação imutável (returns new instance) ------------------

    def with_segment_enabled(
        self, idx: int, enabled: bool,
    ) -> "TCCDevice":
        """
        Retorna nova instância com o segment ``idx`` toggled.

        Como ``TCCSegment`` também é frozen, precisa criar
        nova instância do segment via ``replace`` (já tem
        suporte para os 16 segment types — todos frozen).

        Parameters
        ----------
        idx:
            Índice do segment na tuple (0-based).
        enabled:
            Novo valor para ``enabled``.

        Returns
        -------
        TCCDevice
            Nova instância com o segment substituído.

        Raises
        ------
        IndexError
            Se ``idx`` fora do range.
        """
        if idx < 0 or idx >= len(self.segments):
            raise IndexError(
                f"idx={idx} fora do range [0, {len(self.segments)})"
            )
        from dataclasses import replace
        old_seg = self.segments[idx]
        new_seg = replace(old_seg, enabled=enabled)
        new_segments = (
            self.segments[:idx] + (new_seg,) + self.segments[idx + 1:]
        )
        return replace(self, segments=new_segments)

    def with_segment_added(self, segment) -> "TCCDevice":
        """
        Retorna nova instância com 1 segment adicional ao final.

        Útil para builder pattern (ex: começar com 51, depois
        ``.with_segment_added(seg_50_inst)``).
        """
        if not isinstance(segment, TCCSegment):
            raise TypeError(
                f"segment não satisfaz Protocol TCCSegment "
                f"(tipo recebido: {type(segment).__name__})"
            )
        from dataclasses import replace
        return replace(self, segments=self.segments + (segment,))

    def enabled_segments(self) -> list:
        """Lista de segments habilitados (em ordem original)."""
        return [s for s in self.segments if getattr(s, "enabled", True)]

    def __len__(self) -> int:
        """Número total de segments (enabled + disabled)."""
        return len(self.segments)


# ---------------------------------------------------------------------------
# β.2 — MultiFunctionRelay (subclasse com helpers para padrões comuns)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MultiFunctionRelay(TCCDevice):
    """
    Subclasse de :class:`TCCDevice` especializada para
    relés de proteção. Não adiciona campos novos — serve
    como **tipo discriminado** + **factory de padrões
    comuns** via classmethods.

    Padrões cobertos
    -----------------

    1. ``relay_51_only`` — overcurrent IDMT puro (51)
    2. ``relay_51_and_50`` — IDMT + instantâneo (51 + 50)
    3. ``relay_51_50_49`` — motor protection (51 + 50 + 49 thermal)
    4. ``relay_51_50_87`` — transformer differential (51 + 50 + 87)

    Cada helper instancia automaticamente os segments
    apropriados (LT, INST, DefiniteTime) já testados em α.1.
    Assim, modelagem de relés reais fica em 1-2 linhas:

    ::

        sel = MultiFunctionRelay.relay_51_50_49(
            device_id="R-MOT-1",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=120.0, tms_51=0.20,
            pickup_50_A=1500.0,
            pickup_49_A=130.0, delay_49_s=8.0,
            manufacturer="SEL", model="751",
        )

    Cobertura normativa
    --------------------

    * IEEE C37.2 (device function numbers 50/51/49/87)
    * IEC 60255-151 (multi-function relays)

    Notes
    -----

    Para padrões fora desses 4 (ex: 27 undervoltage, 81
    frequency, 21 distance), use o construtor base
    ``TCCDevice(...)`` diretamente com a tuple de segments
    apropriada.
    """

    @classmethod
    def relay_51_only(
        cls,
        *,
        device_id: str,
        curve_type,
        pickup_A: float,
        tms: float,
        manufacturer: str = "Generic",
        model: str = "Generic",
        segment_id: str = "51",
    ) -> "MultiFunctionRelay":
        """
        Helper: relé com apenas 51 IDMT.

        Útil para overcurrent simples (feeder LV, distribuição
        radial). Equivalente ao ``TCCCurve`` legacy v1.1.0,
        mas em formato Device para compor com outros depois.
        """
        from app.postprocessor.tcc_segments import TCCSegmentLT
        s51 = TCCSegmentLT(
            segment_id=segment_id,
            pickup_A=pickup_A,
            curve_type=curve_type,
            tms=tms,
        )
        return cls(
            device_id=device_id,
            manufacturer=manufacturer,
            model=model,
            segments=(s51,),
        )

    @classmethod
    def relay_51_and_50(
        cls,
        *,
        device_id: str,
        curve_type,
        pickup_51_A: float,
        tms_51: float,
        pickup_50_A: float,
        delay_50_s: float = 0.04,
        manufacturer: str = "Generic",
        model: str = "Generic",
    ) -> "MultiFunctionRelay":
        """
        Helper: relé com 51 IDMT + 50 instantâneo.

        Padrão IEEE 242 §15 para feeder com proteção primária
        (51) + backup rápido (50). 50 default 0.04 s
        (2 ciclos @ 60 Hz).

        Cobertura: IEC 60255-151 §6.3.4 (instantaneous element).
        """
        from app.postprocessor.tcc_segments import (
            TCCSegmentINST, TCCSegmentLT,
        )
        s51 = TCCSegmentLT(
            segment_id="51",
            pickup_A=pickup_51_A,
            curve_type=curve_type,
            tms=tms_51,
        )
        s50 = TCCSegmentINST(
            segment_id="50",
            pickup_A=pickup_50_A,
            inherent_delay_s=delay_50_s,
        )
        return cls(
            device_id=device_id,
            manufacturer=manufacturer,
            model=model,
            segments=(s51, s50),
        )

    @classmethod
    def relay_51_50_49(
        cls,
        *,
        device_id: str,
        curve_type,
        pickup_51_A: float,
        tms_51: float,
        pickup_50_A: float,
        pickup_49_A: float,
        delay_49_s: float,
        delay_50_s: float = 0.04,
        manufacturer: str = "Generic",
        model: str = "Generic",
    ) -> "MultiFunctionRelay":
        """
        Helper: relé motor (51 IDMT + 50 INST + 49 thermal).

        49 thermal é modelado como ``TCCSegmentDefiniteTime``
        (fix delay quando I > pickup_49). Modelagem fiel ao
        thermal replica curve do datasheet exigiria
        ``TCCSegmentTimeCurrentPoints`` — fica para v1.4
        (vendor library).

        Cobertura: IEEE C37.2 dev 49, IEC 60079 (motors), IEC
        60255-151.
        """
        from app.postprocessor.tcc_segments import (
            TCCSegmentDefiniteTime, TCCSegmentINST, TCCSegmentLT,
        )
        s51 = TCCSegmentLT(
            segment_id="51",
            pickup_A=pickup_51_A,
            curve_type=curve_type,
            tms=tms_51,
        )
        s50 = TCCSegmentINST(
            segment_id="50",
            pickup_A=pickup_50_A,
            inherent_delay_s=delay_50_s,
        )
        s49 = TCCSegmentDefiniteTime(
            segment_id="49 thermal",
            pickup_A=pickup_49_A,
            delay_s=delay_49_s,
        )
        return cls(
            device_id=device_id,
            manufacturer=manufacturer,
            model=model,
            segments=(s51, s50, s49),
        )

    @classmethod
    def relay_51_50_87(
        cls,
        *,
        device_id: str,
        curve_type,
        pickup_51_A: float,
        tms_51: float,
        pickup_50_A: float,
        pickup_87_A: float,
        delay_87_s: float = 0.025,
        delay_50_s: float = 0.04,
        manufacturer: str = "Generic",
        model: str = "Generic",
    ) -> "MultiFunctionRelay":  # noqa
        """
        Helper: relé transformador (51 IDMT + 50 INST + 87
        diferencial).

        87 diferencial é modelado como instantâneo dedicado
        (typical 1-1.5 cycles, default 0.025 s = 1.5 ciclos
        @ 60 Hz). Restraint slope, harmonic blocking, etc. —
        v1.4+ (modelagem detalhada do diff).

        Cobertura: IEEE C37.2 dev 87, IEC 60255-151 §6.4
        (differential), IEEE C37.91.
        """
        from app.postprocessor.tcc_segments import (
            TCCSegmentINST, TCCSegmentLT,
        )
        s51 = TCCSegmentLT(
            segment_id="51",
            pickup_A=pickup_51_A,
            curve_type=curve_type,
            tms=tms_51,
        )
        s50 = TCCSegmentINST(
            segment_id="50",
            pickup_A=pickup_50_A,
            inherent_delay_s=delay_50_s,
        )
        s87 = TCCSegmentINST(
            segment_id="87 diff",
            pickup_A=pickup_87_A,
            inherent_delay_s=delay_87_s,
        )
        return cls(
            device_id=device_id,
            manufacturer=manufacturer,
            model=model,
            segments=(s51, s50, s87),
        )


# ---------------------------------------------------------------------------
# β.3 — Device-vs-Device coordination check
# ---------------------------------------------------------------------------


# Reusa COORDINATION_MARGIN_S do legacy (Buff Book §15.10.1).
# Importado lazy para não criar circular dependency entre os módulos
# durante eventual carregamento.
def _coordination_margin_for(relay_type: str) -> float:
    """Lookup de margin Δt mínima conforme tipo de relé."""
    from app.postprocessor.tcc_curves import COORDINATION_MARGIN_S
    return COORDINATION_MARGIN_S.get(relay_type.lower(), 0.30)


@dataclass(frozen=True)
class DeviceCoordinationCheck:
    """
    Resultado de coordenação entre 2 ``TCCDevice``.

    Reúne o ``min`` envelope dos dois (``composite_time_at_current``)
    e identifica explicitamente qual segment "venceu" em cada
    device — útil para diagnóstico ("o INST do upstream
    competiu com o LT do downstream → margem insuficiente").

    Cobertura normativa
    --------------------

    * IEEE Std 242-2001 (Buff Book) §15.10.1 —
      Coordination time intervals (margens 0.25/0.30/0.40 s)
    * IEC 60255-151:2009 (relay characteristics)
    * PTW Reference-CAPTOR.pdf — Coordination check workflow

    Attributes
    ----------
    upstream_id, downstream_id:
        IDs dos devices.
    fault_current_A:
        Corrente avaliada.
    upstream_composite_time_s:
        ``min`` envelope do upstream em I_fault.
    downstream_composite_time_s:
        ``min`` envelope do downstream em I_fault.
    actual_delta_t_s:
        ``upstream_composite - downstream_composite`` (positivo
        para coordenação correta).
    required_delta_t_s:
        Margin mínima conforme ``relay_type`` (Buff Book §15.10.1):

        * electromechanical: 0.40 s
        * static: 0.30 s
        * digital / numerical: 0.25 s
    passes:
        ``actual ≥ required`` AND ambos finitos.
    triggered_upstream_segment_id:
        ID do segment que ditou o composite do upstream
        (ex: "51 IEC SI", "50", "49 thermal", "87 diff").
        ``"(none)"`` se composite=∞.
    triggered_downstream_segment_id:
        Idem para downstream.
    relay_type:
        Tipo passado ao check (echo).
    citation:
        Norma de referência.
    """

    upstream_id: str
    downstream_id: str
    fault_current_A: float

    upstream_composite_time_s: float
    downstream_composite_time_s: float
    actual_delta_t_s: float
    required_delta_t_s: float
    passes: bool

    triggered_upstream_segment_id: str
    triggered_downstream_segment_id: str

    relay_type: str = "digital"
    citation: str = (
        "IEEE Std 242-2001 §15.10.1 — Coordination time intervals"
    )


def check_device_coordination(
    upstream: TCCDevice,
    downstream: TCCDevice,
    fault_current_A: float,
    relay_type: str = "digital",
) -> DeviceCoordinationCheck:
    """
    Verifica margem ``Δt`` adequada entre 2 devices em série.

    Usa o **composite envelope** de cada device (``min`` sobre
    todos os segments enabled) — a função que dispara primeiro
    é a que conta. Identifica qual segment "venceu" em cada
    device para debug de coordenação.

    Parameters
    ----------
    upstream:
        Device a montante (deve operar DEPOIS).
    downstream:
        Device a jusante (deve operar PRIMEIRO).
    fault_current_A:
        Corrente de falta avaliada.
    relay_type:
        ``"electromechanical"`` (0.40s), ``"static"`` (0.30s),
        ``"digital"`` (0.25s, default), ``"numerical"`` (0.25s).

    Returns
    -------
    DeviceCoordinationCheck
        Inclui ``triggered_*_segment_id`` para diagnóstico.

    Notes
    -----
    Para coordenação em **múltiplos pontos** (low fault, mid
    fault, high fault), chame N vezes — cada call é
    self-contained.
    """
    t_up = upstream.composite_time_at_current(fault_current_A)
    t_dn = downstream.composite_time_at_current(fault_current_A)

    seg_up = upstream.triggered_segment(fault_current_A)
    seg_dn = downstream.triggered_segment(fault_current_A)

    seg_up_id = seg_up.segment_id if seg_up is not None else "(none)"
    seg_dn_id = seg_dn.segment_id if seg_dn is not None else "(none)"

    actual_dt = t_up - t_dn
    required_dt = _coordination_margin_for(relay_type)
    passes = (
        math.isfinite(t_up)
        and math.isfinite(t_dn)
        and actual_dt >= required_dt
    )

    return DeviceCoordinationCheck(
        upstream_id=upstream.device_id,
        downstream_id=downstream.device_id,
        fault_current_A=fault_current_A,
        upstream_composite_time_s=t_up,
        downstream_composite_time_s=t_dn,
        actual_delta_t_s=actual_dt,
        required_delta_t_s=required_dt,
        passes=passes,
        triggered_upstream_segment_id=seg_up_id,
        triggered_downstream_segment_id=seg_dn_id,
        relay_type=relay_type,
    )


def check_device_coordination_multi_point(
    upstream: TCCDevice,
    downstream: TCCDevice,
    currents_A: list,
    relay_type: str = "digital",
) -> list:
    """
    Helper: verifica coordenação em N correntes simultaneamente.

    Útil para validar coord em low/mid/high fault (3 pontos
    típicos de IEEE 242 §15.10).

    Returns
    -------
    list[DeviceCoordinationCheck]
        Uma checagem por corrente.
    """
    return [
        check_device_coordination(
            upstream, downstream, I, relay_type=relay_type,
        )
        for I in currents_A
    ]
