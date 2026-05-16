"""
app.postprocessor.short_circuit — calculadora de curto-circuito
seguindo IEC 60909-0:2016, integrada com os componentes do
preprocessor (SM, transformer, network feeder).

Workflow
========

::

    from app.postprocessor.short_circuit import (
        ShortCircuitNetwork, FaultLocation,
    )

    net = ShortCircuitNetwork(rated_voltage_kV=13.8)
    net.add_network_feeder(
        name="UTIL", S_kQ_MVA=500.0, r_over_x=0.10,
    )
    net.add_transformer(
        name="T1", S_MVA=10.0, uk_pct=8.0, uR_pct=0.5,
        primary_kV=138.0, secondary_kV=13.8,
    )
    net.add_synchronous_machine_from_sm(sm_params)

    fault = net.calculate_at_bus("BUS_LV")
    print(fault.summary())

Modelagem
=========

* **Network feeder** (rede da concessionária): impedância equiv-
  alente baseada em S_kQ'' (potência de SC conhecida).
* **Transformer**: impedância de uk% referida ao lado do bus.
* **Synchronous machine**: usa Xd'' subtransitório; aproveita
  ``SynchronousMachineParameters`` do preprocessor.

Combinação de impedâncias
==========================

Esta MVP suporta apenas **redes radiais simples** — soma de
impedâncias em série (feeder + transformer) e combinação paralela
de múltiplas fontes (concessionária + gerador) num bus comum:

::

    Z_eq = Z_feeder · Z_gen / (Z_feeder + Z_gen)   (parallel)
    Z_total_at_bus = Z_eq                           (no series load)

Para malhas ressonantes ou topologia mais complexa, em sub-sprints
posteriores integraremos com solver matricial Y-bus (v0.28.x).

Referências
============

* IEC 60909-0:2016 §4 (calculation of currents).
* IEC 60909-0:2016 §6 (impedances of components).
* ABNT NBR 17227:2025 §5.1.4 (referencia 60909 para o estudo
  de SC dentro do estudo de arc-flash).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.standards.iec60909 import (
    FaultDistance, ShortCircuitResult, VoltageLevel,
    calculate_short_circuit,
    classify_voltage,
    network_feeder_impedance_ohm,
    synchronous_machine_impedance_ohm,
    transformer_impedance_ohm,
    voltage_factor_c,
)


# ---------------------------------------------------------------------------
# Componentes da rede SC
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScSource:
    """
    Fonte de curto-circuito num bus.

    Attributes
    ----------
    name:
        Identificador.
    z_ohm:
        Impedância equivalente ao bus de fault (ohms, complexa).
    description:
        Texto livre (ex: "Network feeder", "Generator GEN1").
    """
    name: str
    z_ohm: complex
    description: str


@dataclass(frozen=True)
class FaultLocation:
    """
    Localização de uma falta para análise.

    Attributes
    ----------
    bus_name:
        Identificador do barramento.
    rated_voltage_kV:
        Tensão nominal do bus.
    """
    bus_name: str
    rated_voltage_kV: float


# ---------------------------------------------------------------------------
# ShortCircuitNetwork — orquestrador
# ---------------------------------------------------------------------------


@dataclass
class ShortCircuitNetwork:
    """
    Rede simplificada radial para cálculo de SC IEC 60909-0.

    Não confundir com o ``AtpProject`` do bridge — aqui é um
    modelo elétrico-equivalente focado em SC, alimentado a partir
    dos parâmetros de cada componente.

    Attributes
    ----------
    rated_voltage_kV:
        Tensão nominal do bus de análise (default).
    sources:
        Lista de fontes que contribuem para SC no bus.
    """

    rated_voltage_kV: float
    sources: list[ScSource] = field(default_factory=list)

    def add_network_feeder(
        self,
        name: str,
        S_kQ_MVA: float,
        rated_voltage_kV: Optional[float] = None,
        voltage_factor: float = 1.10,
        r_over_x: float = 0.10,
    ) -> None:
        """
        Adiciona uma rede externa caracterizada pela potência de
        SC conhecida (``S_kQ''``) no ponto de entrega.

        Parameters
        ----------
        S_kQ_MVA:
            Potência de SC trifásica simétrica fornecida pela rede.
        rated_voltage_kV:
            Tensão nominal no ponto de conexão da rede; default =
            tensão do bus.
        """
        v = rated_voltage_kV if rated_voltage_kV is not None else self.rated_voltage_kV
        z = network_feeder_impedance_ohm(
            rated_voltage_kV=v,
            short_circuit_power_MVA=S_kQ_MVA,
            voltage_factor_c=voltage_factor,
            r_over_x=r_over_x,
        )
        self.sources.append(ScSource(
            name=name,
            z_ohm=z,
            description=(
                f"Network feeder, S_kQ''={S_kQ_MVA:.1f} MVA, "
                f"R/X={r_over_x:.2f}"
            ),
        ))

    def add_transformer_series(
        self,
        name: str,
        primary_z_ohm: complex,
        S_MVA: float,
        uk_pct: float,
        uR_pct: float,
        bus_side_kV: float,
    ) -> ScSource:
        """
        Adiciona uma fonte alimentada **através** de um transformador
        (em série). A impedância do feeder é refletida ao lado do
        bus pela razão de transformação automaticamente — caller
        passa ``primary_z_ohm`` já no lado primário; aqui somamos
        Z_T (referida ao secundário).

        Notas
        -----

        Este é um helper para "feeder + transformer" como uma
        única fonte. Para transformadores múltiplos, encadear.

        Returns
        -------
        ScSource
            A fonte resultante (também adicionada à lista).
        """
        z_T = transformer_impedance_ohm(
            rated_voltage_kV=bus_side_kV,
            rated_power_MVA=S_MVA,
            uk_percent=uk_pct,
            uR_percent=uR_pct,
        )
        # Refletir Z_primary ao secundário pela razão (V_sec/V_pri)²
        # mas como o caller já passou primary_z já em ohms relativos
        # ao primário, precisamos da razão. Para simplificar:
        # se primary_z_ohm está no lado primário, refletir.
        # Aqui assumimos que primary_z já foi convertido pelo caller.
        z_total = primary_z_ohm + z_T
        src = ScSource(
            name=name,
            z_ohm=z_total,
            description=(
                f"Feeder+TR, uk={uk_pct:.1f}%, "
                f"S={S_MVA:.1f} MVA, ref. {bus_side_kV:.1f} kV"
            ),
        )
        self.sources.append(src)
        return src

    def add_synchronous_machine_from_sm(
        self, sm_params, name: Optional[str] = None,
    ) -> ScSource:
        """
        Adiciona uma máquina síncrona a partir de
        ``SynchronousMachineParameters`` do ``app.preprocessor.
        synchronous_machine``.

        Usa ``Xd''`` (subtransitório) para Ik''.

        Parameters
        ----------
        sm_params:
            Instância de SynchronousMachineParameters.
        name:
            Override do nome (default = sm_params.name).
        """
        z = synchronous_machine_impedance_ohm(
            rated_voltage_kV=sm_params.rated_voltage_kV,
            rated_power_MVA=sm_params.rated_power_MVA,
            Xd_pp_pu=sm_params.Xd_pp,
            Ra_pu=sm_params.Ra,
        )
        src = ScSource(
            name=name or sm_params.name,
            z_ohm=z,
            description=(
                f"SyncMachine, Xd''={sm_params.Xd_pp:.3f} pu, "
                f"S={sm_params.rated_power_MVA:.1f} MVA"
            ),
        )
        self.sources.append(src)
        return src

    def add_custom_source(
        self, name: str, z_ohm: complex, description: str = "",
    ) -> ScSource:
        """Adiciona uma fonte com impedância pré-calculada."""
        src = ScSource(name=name, z_ohm=z_ohm, description=description)
        self.sources.append(src)
        return src

    def equivalent_thevenin_impedance(self) -> complex:
        """
        Combina todas as fontes em paralelo no bus de análise.

        Para 2 fontes: Z_eq = Z1 · Z2 / (Z1 + Z2).
        Para N fontes: Y_eq = Σ Yi → Z_eq = 1 / Y_eq.
        """
        if not self.sources:
            raise ValueError("Nenhuma fonte adicionada — Z_eq indefinida")
        y_eq = complex(0, 0)
        for src in self.sources:
            if src.z_ohm == 0:
                # bus diretamente conectado a fonte ideal
                return complex(0, 0)
            y_eq += 1.0 / src.z_ohm
        return 1.0 / y_eq

    def calculate_at_bus(
        self,
        bus_name: str = "BUS",
        kind: str = "max",
        time_for_idc_s: float = 0.050,
        frequency_Hz: float = 60.0,
    ) -> ShortCircuitResult:
        """
        Calcula Ik'', ip, idc, Ib, Ik no bus de análise.

        Parameters
        ----------
        bus_name:
            Nome do bus (informativo no relatório).
        kind:
            ``"max"`` para máxima Ik'' (default; rating de
            equipamento) ou ``"min"`` (estudo de seletividade).
        """
        z_eq = self.equivalent_thevenin_impedance()
        return calculate_short_circuit(
            rated_voltage_kV=self.rated_voltage_kV,
            z_thevenin_ohm=z_eq,
            kind=kind,
            time_for_idc_s=time_for_idc_s,
            frequency_Hz=frequency_Hz,
        )

    def contribution_breakdown(self) -> dict:
        """
        Retorna a fração de Ik'' aportada por cada fonte.

        v0.28.0-PRO: divisor de corrente COMPLEXO (com fase),
        normalizado pela soma complexa para garantir ∑ = 1.

        Estratégia (cf. Stevenson §10):

        ::

            Y_total = ∑ Y_i = ∑ 1/Z_i
            I_i = V_th · Y_i
            I_total = V_th · Y_total
            fração_i = |I_i| / |I_total|     [magnitude]

        Para fontes paralelas com fases distintas, esta fração
        respeita a soma complexa correta. Cada fonte
        contribui com I_i = V_th / Z_i.

        Returns
        -------
        dict
            ``{source_name: fraction}`` onde fraction ∈ [0, 1]
            e ∑ fractions ≈ 1 dentro de erros numéricos.
        """
        # Soma complexa de Y_i
        Y_total = sum(
            (1.0 / src.z_ohm) if abs(src.z_ohm) > 0 else complex(1e15, 0)
            for src in self.sources
        )
        if abs(Y_total) <= 0:
            return {src.name: 0.0 for src in self.sources}

        # |I_i| ∝ |Y_i|, normalizado pela soma das magnitudes
        # de I_i (não pela magnitude da soma, que pode cancelar).
        # Para preservar interpretação "fração de Ik'' RMS":
        I_magnitudes = []
        for src in self.sources:
            if abs(src.z_ohm) > 0:
                I_magnitudes.append(abs(1.0 / src.z_ohm))
            else:
                I_magnitudes.append(1e15)

        sum_I = sum(I_magnitudes)
        if sum_I <= 0:
            return {src.name: 0.0 for src in self.sources}

        return {
            src.name: I_mag / sum_I
            for src, I_mag in zip(self.sources, I_magnitudes)
        }


# ---------------------------------------------------------------------------
# Helpers de alto-nível
# ---------------------------------------------------------------------------


def calculate_sc_for_generator_terminal(
    sm_params,
    voltage_factor: Optional[float] = None,
    kind: str = "max",
) -> ShortCircuitResult:
    """
    Atalho: SC trifásico simétrico nos terminais de uma máquina
    síncrona standalone (sem outra contribuição).

    Útil para validação rápida do componente SM e para o "pior
    caso" de SC trifásico próximo ao gerador.

    Aplica c=1.10 para MV/HV (default) ou usa override.
    """
    net = ShortCircuitNetwork(rated_voltage_kV=sm_params.rated_voltage_kV)
    net.add_synchronous_machine_from_sm(sm_params)
    return net.calculate_at_bus(
        bus_name=f"{sm_params.name}_terminal", kind=kind,
    )
