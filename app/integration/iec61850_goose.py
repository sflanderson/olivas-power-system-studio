"""
app.integration.iec61850_goose — IEC 61850-8-1 §17 GOOSE
(Generic Object Oriented Substation Event) — v2.2.0 Sprint A.

Filosofia
==========

GOOSE é o protocolo time-critical do IEC 61850 para mensagens
binárias de status/comando entre IEDs (típico: trip rápido,
intertravamento, GOOSE-as-a-trip-replacement).

Característica chave (§17.2.6): mecanismo de **retransmissão
adaptativa**:

* Em estado estável: mensagens espaçadas em ~1s (keep-alive)
  com SqNum incrementando
* Em mudança de estado: rajada rápida (4-128 ms) com StNum++
  e SqNum=0

Implementação
==============

* **Stub mode** (default): publish/subscribe via bus interno
  in-memory (sem rede real). Testa lógica de protocolo sem
  exigir Ethernet ou libiec61850.

* **Real mode**: delegação para libiec61850 (não bundled). Em
  deploy real, lib publicaria frames Ethernet multicast com
  EtherType 0x88B8.

Anti-alucinação
================

* Não simulamos rede Ethernet real — apenas a lógica de
  StNum/SqNum + dispatch via callback.
* Cabeçalho GooseMessage segue spec mas formato wire (ASN.1
  BER) não é serializado em Python.
* Real mode raise NotImplementedError com instrução clara.

Cobertura normativa
====================

* IEC 61850-8-1:2020 §17 (GOOSE)
* IEC 61850-7-2:2010 §18 (BRCB / GoCB control blocks)

Aplicação típica em sistemas de proteção
==========================================

* Trip mensagem rápida (relé → disjuntor) com latência <4ms
* Interlocking entre bays (logical lockout, 25, 27)
* Status broadcast (52a/52b breaker position)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from app.core.logging_config import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class GooseMessage:
    """
    Uma mensagem GOOSE (frame Ethernet abstrato).

    Campos seguem IEC 61850-8-1 §17.2.5 GoCB Control Block PDU:

    * ``go_id``: identificador completo do GoCB (ex:
      "DEMO/LLN0$GO$gcb01" — IED/LD/LN0$GO$nome)
    * ``dataset``: nome do dataset publicado
    * ``st_num``: state number — incrementa em mudança de estado
    * ``sq_num``: sequence number — incrementa em retransmissão
      (reset para 0 em st_num++)
    * ``timestamp``: instante da publicação
    * ``test``: flag test (true = mensagem de teste, descartada
      por subscribers em produção)
    * ``data``: dict com os valores publicados (paridade DataSet
      do IEC 61850-7-2)
    """

    go_id: str
    dataset: str
    st_num: int
    sq_num: int
    timestamp: datetime
    test: bool
    data: Dict[str, Any] = field(default_factory=dict)


class GoosePublisher:
    """
    Publica mensagens GOOSE em um bus (stub) ou rede real.

    Implementa lógica de StNum/SqNum conforme IEC 61850-8-1
    §17.2.6:

    * `publish_state_change(data)`: StNum += 1, SqNum = 0
    * `publish_keep_alive()`: SqNum += 1 (reusa data anterior)
    """

    def __init__(
        self,
        *,
        go_id: str,
        dataset: str = "",
        mode: str = "stub",
    ) -> None:
        self.go_id = go_id
        self.dataset = dataset or f"{go_id}_DS"
        self.mode = mode
        self.st_num = 0
        self.sq_num = 0
        self._last_data: Dict[str, Any] = {}
        self._subscribers: List["GooseSubscriber"] = []

    def connect_subscriber(self, sub: "GooseSubscriber") -> None:
        """
        Stub mode: conecta um subscriber ao bus interno.

        Em real mode, subscribers escutam multicast Ethernet
        independentemente — não há `connect`.
        """
        if sub not in self._subscribers:
            self._subscribers.append(sub)

    def publish_state_change(
        self, *, data: Dict[str, Any], test: bool = False,
    ) -> GooseMessage:
        """
        Publica mudança de estado (StNum++, SqNum=0).

        Equivalente a um trip event (carga binária mudou).
        """
        if self.mode == "stub":
            self.st_num += 1
            self.sq_num = 0
            self._last_data = dict(data)
            msg = GooseMessage(
                go_id=self.go_id,
                dataset=self.dataset,
                st_num=self.st_num,
                sq_num=self.sq_num,
                timestamp=datetime.now(),
                test=test,
                data=dict(data),
            )
            self._dispatch(msg)
            log.info(
                "GOOSE state-change: %s StNum=%d SqNum=%d",
                self.go_id, self.st_num, self.sq_num,
            )
            return msg
        elif self.mode == "real":
            try:
                import libiec61850  # noqa: F401
            except ImportError:
                raise NotImplementedError(
                    "Real mode GOOSE exige libiec61850 + Ethernet "
                    "multicast. Veja docs/IEC61850.md."
                )
            raise NotImplementedError(
                "Real mode implementation requires customer-specific "
                "configuration. Contact Olivas Team for support."
            )
        else:
            raise ValueError(f"Modo desconhecido: {self.mode!r}")

    def publish_keep_alive(self) -> GooseMessage:
        """
        Publica retransmissão (StNum mantém, SqNum++).

        Equivalente a heartbeat — mantém subscribers cientes
        de que o publisher está vivo.
        """
        if self.mode == "stub":
            self.sq_num += 1
            msg = GooseMessage(
                go_id=self.go_id,
                dataset=self.dataset,
                st_num=self.st_num,
                sq_num=self.sq_num,
                timestamp=datetime.now(),
                test=False,
                data=dict(self._last_data),
            )
            self._dispatch(msg)
            return msg
        elif self.mode == "real":
            raise NotImplementedError(
                "Real mode GOOSE exige libiec61850."
            )
        else:
            raise ValueError(f"Modo desconhecido: {self.mode!r}")

    def _dispatch(self, msg: GooseMessage) -> None:
        """Dispatch a subscribers conectados (stub mode)."""
        for sub in self._subscribers:
            try:
                sub._receive(msg)
            except Exception as exc:
                log.warning(
                    "GOOSE dispatch falhou para subscriber %s: %s",
                    sub.go_id, exc,
                )


class GooseSubscriber:
    """
    Subscreve mensagens GOOSE de um go_id específico.

    Stub mode: chamado via `connect_subscriber` no publisher.
    Real mode: lib externa registra callback que escuta
    multicast Ethernet.
    """

    def __init__(
        self,
        *,
        go_id: str,
        callback: Callable[[GooseMessage], None],
        mode: str = "stub",
    ) -> None:
        self.go_id = go_id
        self.callback = callback
        self.mode = mode

    def _receive(self, msg: GooseMessage) -> None:
        """Filtro de go_id + dispatch para callback."""
        if msg.go_id != self.go_id:
            return
        try:
            self.callback(msg)
        except Exception as exc:
            log.error(
                "GOOSE callback falhou: %s", exc,
            )
