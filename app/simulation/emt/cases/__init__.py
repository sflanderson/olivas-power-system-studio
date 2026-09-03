"""
app.simulation.emt.cases — casos de estudo paramétricos montados sobre o
kernel EMT dedicado do Olivas Power System Studio.

Cada caso é uma **montagem declarativa**: um conjunto de dataclasses de
parâmetros, com os valores publicados na fonte primária e as lacunas
explicitamente rotuladas, e um método ``build()`` que devolve circuito,
sondas e controladores prontos para ``Solver.run``.

Casos disponíveis
=================

* :mod:`app.simulation.emt.cases.motor_switching` — interrupção
  intempestiva da partida de um motor de indução de 1250 kW / 4,16 kV
  por disjuntor a vácuo, com e sem *snubber* ativo a tiristor
  (Documento A, SEPOC 2026).

Sem I/O, sem GUI.
"""

from __future__ import annotations

from app.simulation.emt.cases.motor_switching import (
    DOC_A_TABLE_III,
    RL_VARIANT_FIG2,
    RL_VARIANT_TABLE_I,
    RL_VARIANTS,
    CableParameters,
    MotorParameters,
    MotorSwitchingCase,
    MotorSwitchingModel,
    SnubberParameters,
    SourceParameters,
    TransformerParameters,
    VCBParameters,
)
from app.simulation.emt.cases.motor_switching import (
    KNOWN_LIMITATIONS as MOTOR_SWITCHING_LIMITATIONS,
)

__all__ = [
    "SourceParameters",
    "TransformerParameters",
    "CableParameters",
    "MotorParameters",
    "VCBParameters",
    "SnubberParameters",
    "MotorSwitchingCase",
    "MotorSwitchingModel",
    "RL_VARIANT_FIG2",
    "RL_VARIANT_TABLE_I",
    "RL_VARIANTS",
    "DOC_A_TABLE_III",
    "MOTOR_SWITCHING_LIMITATIONS",
]
