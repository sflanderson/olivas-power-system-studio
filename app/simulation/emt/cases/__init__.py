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
* :mod:`app.simulation.emt.cases.atp_reference` — o MESMO caso, porém
  ancorado nos arquivos de dados do ATP e na solução fasorial impressa
  pela listagem de saída, com a rede a montante entrando por equivalente
  de Thévenin deduzido daquela solução (a matriz do transformador
  permanece indecifrada e não é adivinhada).

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
from app.simulation.emt.cases.atp_reference import (
    AtpReference,
    AtpReferenceCase,
    AtpReferenceModel,
    CoupledBergeronCable,
    SnubberArmingGate,
    TheveninEquivalent,
    ValidationRow,
    build_reference_model,
    derive_thevenin,
    load_reference,
)
from app.simulation.emt.cases.atp_reference import (
    KNOWN_LIMITATIONS as ATP_REFERENCE_LIMITATIONS,
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
    "AtpReference",
    "AtpReferenceCase",
    "AtpReferenceModel",
    "CoupledBergeronCable",
    "SnubberArmingGate",
    "TheveninEquivalent",
    "ValidationRow",
    "build_reference_model",
    "derive_thevenin",
    "load_reference",
    "ATP_REFERENCE_LIMITATIONS",
]
