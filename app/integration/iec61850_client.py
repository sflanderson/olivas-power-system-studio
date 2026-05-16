"""
app.integration.iec61850_client — Live SCADA via IEC 61850 MMS
(v2.0.0 Sprint B).

Cobertura
=========

* **Stub mode** (default): gera dados sintéticos para demo + testes
* **Real mode**: interface estável para libiec61850 (lib C com
  bindings Python — não bundled; usuário instala em deploy real)

Padrão IEC 61850-8-1 MMS
=========================

IEC 61850 (Communication networks and systems for power utility
automation) define:

* **MMS** (Manufacturing Message Specification, ISO 9506) —
  client/server com IED (Intelligent Electronic Device)
* **GOOSE** (Generic Object Oriented Substation Event) —
  multicast Ethernet event messages
* **SV** (Sample Values) — high-rate measurement streaming

v2.0.0 cobre **apenas MMS** (modelo client-server). GOOSE e SV
ficam para v2.1+.

Workflow
========

::

    from app.integration.iec61850_client import (
        IEC61850MMSConfig, IEC61850MMSClient,
    )

    cfg = IEC61850MMSConfig(
        host="192.168.1.100",
        port=102,                 # IEC 61850 default
        ied_name="IED_BAY_01",
        mode="stub",              # ou "real"
    )
    client = IEC61850MMSClient(cfg)
    report = client.get_report()

    print(f"IED: {report.ied_name} @ {report.timestamp}")
    for meas in report.measurements:
        print(f"  {meas.name} = {meas.value} {meas.unit}")

Anti-alucinação
================

* IEC 61850 é spec massiva (>1000 pp.). v2.0.0 entrega **interface
  estável**, não implementação completa.
* Em real mode, API delega para libiec61850 (não bundled).
* Stub mode gera dados realistas usando perfis típicos
  brasileiros (V≈13.8 kV, I dependendo do bus, etc).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple

from app.core.logging_config import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Config + dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IEC61850MMSConfig:
    """
    Configuração do client MMS.

    Attributes
    ----------
    host:
        IP ou hostname do IED (Intelligent Electronic Device).
    port:
        Porta TCP. IEC 61850-8-1 default = 102.
    ied_name:
        Nome do IED no LD (Logical Device) tree.
    mode:
        ``"stub"`` (default — dados sintéticos) ou ``"real"``
        (delega para libiec61850).
    timeout_s:
        Timeout para leituras (real mode).
    """

    host: str
    port: int = 102
    ied_name: str = "IED-DEFAULT"
    mode: str = "stub"
    timeout_s: float = 5.0


@dataclass(frozen=True)
class MMSMeasurement:
    """
    Uma medição individual do report MMS.

    Common Data Class (CDC) suportadas v2.0.0:
    * MV (Measured Value) — V/I/P/Q
    * SPS (Single Point Status) — booleans (breaker open/closed)
    """

    name: str
    value: float
    unit: str
    quality: str = "good"   # "good" / "questionable" / "invalid"


@dataclass(frozen=True)
class MMSReport:
    """
    Report completo recebido do IED em um instante.

    Equivalente ao Buffered Report Control Block (BRCB) ou
    Unbuffered Report Control Block (URCB) do IEC 61850-7-2.
    """

    ied_name: str
    timestamp: datetime
    measurements: Tuple[MMSMeasurement, ...]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class IEC61850MMSClient:
    """
    Cliente MMS para IEC 61850.

    Default mode: ``stub`` (dados sintéticos).
    Real mode: tenta delegate para libiec61850 (não bundled).
    """

    def __init__(self, config: IEC61850MMSConfig) -> None:
        self.config = config

    def get_report(self) -> MMSReport:
        """
        Retorna report MMS atual.

        Stub mode: gera dados sintéticos realistas.
        Real mode: delega para libiec61850 (raise se lib ausente).
        """
        if self.config.mode == "stub":
            return self._stub_report()
        elif self.config.mode == "real":
            return self._real_report()
        else:
            raise ValueError(
                f"Modo IEC 61850 desconhecido: {self.config.mode!r}. "
                f"Use 'stub' ou 'real'."
            )

    def _stub_report(self) -> MMSReport:
        """
        Gera report sintético com perfil típico brasileiro:
        * V_RMS_A/B/C ≈ 13.8 kV ± 1%
        * I_RMS_A/B/C ≈ 100 A ± 10%
        * P_total ≈ 2.0 MW ± 5%
        * Q_total ≈ 0.5 MVAr ± 5%
        * BREAKER status: closed (default)
        """
        rnd = random.Random()
        # Valores típicos com pequena variação realista
        v_nom = 13.8
        i_nom = 100.0
        meas: List[MMSMeasurement] = []
        for phase in ("A", "B", "C"):
            v = v_nom * (1.0 + rnd.uniform(-0.01, 0.01))
            meas.append(MMSMeasurement(
                name=f"V_RMS_{phase}",
                value=round(v, 3),
                unit="kV",
            ))
        for phase in ("A", "B", "C"):
            i = i_nom * (1.0 + rnd.uniform(-0.10, 0.10))
            meas.append(MMSMeasurement(
                name=f"I_RMS_{phase}",
                value=round(i, 1),
                unit="A",
            ))
        meas.append(MMSMeasurement(
            name="P_total",
            value=round(2.0 * (1.0 + rnd.uniform(-0.05, 0.05)), 3),
            unit="MW",
        ))
        meas.append(MMSMeasurement(
            name="Q_total",
            value=round(0.5 * (1.0 + rnd.uniform(-0.05, 0.05)), 3),
            unit="MVAr",
        ))
        meas.append(MMSMeasurement(
            name="BREAKER_status",
            value=1.0,   # 1 = closed
            unit="bool",
        ))

        log.info(
            "IEC61850 stub report: ied=%s, %d measurements",
            self.config.ied_name, len(meas),
        )
        return MMSReport(
            ied_name=self.config.ied_name,
            timestamp=datetime.now(),
            measurements=tuple(meas),
        )

    def _real_report(self) -> MMSReport:
        """
        Real mode: delega para libiec61850 (não bundled).

        Em deploy real:

        ::

            pip install libiec61850   # ou wheel custom
            cfg = IEC61850MMSConfig(host="...", mode="real")

        Aqui retorna NotImplementedError com mensagem instrutiva.
        """
        try:
            import libiec61850   # noqa: F401
        except ImportError:
            raise NotImplementedError(
                "Real mode IEC 61850 exige libiec61850 instalado. "
                "Veja docs/IEC61850.md para deploy."
            )
        # Se chegou aqui, lib está disponível — implementação real
        # seria aqui (delega para libiec61850 API).
        raise NotImplementedError(
            "Real mode implementation requires customer-specific "
            "configuration. Contact Olivas Team for support."
        )
