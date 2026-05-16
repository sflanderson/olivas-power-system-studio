"""
app.integration.iec61850_sv — IEC 61850-9-2 Sample Values
(v2.2.0 Sprint B).

Filosofia
==========

SV é o protocolo high-bandwidth do IEC 61850 para medição
amostrada (V/I) entre Merging Units (MU) e IEDs/relés.

Parâmetros padrão IEC 61850-9-2LE:

* **80 samples/cycle** (proteção genérica): 4800 Hz @ 60 Hz
* **256 samples/cycle** (proteção precisão): 15360 Hz @ 60 Hz
* EtherType 0x88BA (multicast Ethernet)
* Header SV PDU + ASDUs com phsAB, phsBC, phsCA, neutA, etc

Implementação
==============

* **Stub mode** (default): gera waveforms sintéticos 60Hz
  (sinusoide pura V·sin(2πft + φ)) para demo + testes.
* **Real mode**: delegação para libiec61850 (não bundled).

Anti-alucinação
================

* Não simulamos rede real — apenas gera amostras matematicamente.
* Sample.value é float (representação do quantum do AD reais
  seria int32 com escala SVA, mas mantemos float para
  simplicidade do estudo).
* Real mode raise NotImplementedError com instrução clara.

Aplicação típica
=================

* Diferencial 87 com merging units distantes do relé
* Phasor-based protection
* Power quality monitoring de alta resolução
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from app.core.logging_config import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class SVConfig:
    """
    Configuração de stream SV.

    Attributes
    ----------
    sv_id:
        Identificador completo (IED/LD/svCB/dataset).
    samples_per_cycle:
        IEC 61850-9-2LE recomenda 80 ou 256.
    frequency_hz:
        60.0 (Brasil/USA) ou 50.0 (Europa).
    mode:
        ``"stub"`` (synthetic) ou ``"real"`` (libiec61850).
    """

    sv_id: str
    samples_per_cycle: int
    frequency_hz: float = 60.0
    mode: str = "stub"

    @property
    def sample_rate_hz(self) -> float:
        """Taxa de amostragem total em Hz."""
        return self.samples_per_cycle * self.frequency_hz

    @property
    def period_us(self) -> float:
        """Período entre amostras em microssegundos."""
        if self.sample_rate_hz <= 0:
            return 0.0
        return 1_000_000.0 / self.sample_rate_hz


@dataclass(frozen=True)
class SVSample:
    """
    Uma amostra individual do stream SV.

    smp_cnt: contador monotônico (0..N-1 dentro de um segundo;
             reseta no início de cada PPS).
    value: valor da medição (V em Volts ou I em Ampères).
    timestamp_us: tempo absoluto em microssegundos.
    """

    smp_cnt: int
    value: float
    timestamp_us: int


@dataclass(frozen=True)
class SVStream:
    """
    Coleção de SVSamples + metadata do stream.
    """

    sv_id: str
    samples: List[SVSample]
    config_snapshot: SVConfig


class SVPublisher:
    """
    Publica streams SV em modo stub (synthetic waveforms) ou
    real (libiec61850).

    Stub mode gera onda V·sin(2πft + φ) com amostragem na
    sample_rate_hz da config.
    """

    def __init__(
        self,
        config: SVConfig,
        *,
        amplitude: float = 100.0,
        phase_rad: float = 0.0,
    ) -> None:
        self.config = config
        self.amplitude = amplitude
        self.phase_rad = phase_rad

    def generate_stream(
        self, *, num_samples: int = 80,
    ) -> SVStream:
        """
        Gera stream com `num_samples` amostras.

        Stub mode: V·sin(2πft + φ) onde t = smp_cnt / sample_rate.
        Real mode: delega a libiec61850 (raise NotImplementedError
        sem lib).
        """
        if self.config.mode == "stub":
            samples: List[SVSample] = []
            sr = self.config.sample_rate_hz
            f = self.config.frequency_hz
            now_us = int(datetime.now().timestamp() * 1_000_000)
            for n in range(num_samples):
                t = n / sr if sr > 0 else 0.0
                value = (
                    self.amplitude
                    * math.sin(2.0 * math.pi * f * t + self.phase_rad)
                )
                ts_us = now_us + int(n * self.config.period_us)
                samples.append(SVSample(
                    smp_cnt=n,
                    value=value,
                    timestamp_us=ts_us,
                ))
            log.info(
                "SV stub stream: id=%s, samples=%d, rate=%.0f Hz",
                self.config.sv_id, len(samples), sr,
            )
            return SVStream(
                sv_id=self.config.sv_id,
                samples=samples,
                config_snapshot=self.config,
            )
        elif self.config.mode == "real":
            try:
                import libiec61850  # noqa: F401
            except ImportError:
                raise NotImplementedError(
                    "Real mode SV exige libiec61850. "
                    "Veja docs/IEC61850.md."
                )
            raise NotImplementedError(
                "Real mode SV implementation requires customer-"
                "specific configuration. Contact Olivas Team."
            )
        else:
            raise ValueError(
                f"Modo desconhecido: {self.config.mode!r}"
            )
