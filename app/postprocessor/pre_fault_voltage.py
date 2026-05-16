"""
app/postprocessor/pre_fault_voltage.py — Pre-Fault Voltage tolerance handling.

Implementa as 4 opções de pre-fault voltage do PTW Tutorial §Part 5
(p. 131-135) e os 3 conjuntos de tolerância (Utility / Cable / Transformer)
referidos em §Part 5 p. 135-136 e A_Fault §1.3.3 p. 1-10.

Conforme PTW Tutorial §Part 5 p. 131-135:

* **LOAD_FLOW** — usa voltagem do Load Flow study (mais realista mas
  requer LF resolvido)
* **PU_ALL** — todas barras a 1.0 pu (default ANSI)
* **PU_PER_BUS** — voltagem específica por barra (ajuste manual)
* **NO_LOAD_WITH_TAP** — voltagem nominal + taps (pior caso conservador)

Cada equipamento (Utility, Cable, Transformer) tem suas próprias
tolerâncias min/regular/max para análise de pior-caso (Min/Reg/Max
scenarios em arc-flash + interrupting duty).

Reference
---------
PTW Tutorial §Part 5 p. 131-135 (Pre-Fault Voltage options).
PTW A_Fault §1.3.3 p. 1-10 linhas 558-565 (default 1.0 pu).
IEEE 1584-2018 §6 (pre-fault voltage para arc-flash).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PreFaultMode(str, Enum):
    """Pre-fault voltage application mode (§Tutorial Part 5 p. 131-135).

    * **LOAD_FLOW** — usa voltagens calculadas pelo Load Flow.
      Mais realista; reflete carga real, drops, regulação.
      Requer ``lf_voltage_pu`` parameter.

    * **PU_ALL** — todas as barras a 1.0 pu (ou ``regular_pu``).
      Default ANSI workflow per §1.3.3 A_Fault p. 1-10.
      Conservador: ignora voltage drops da rede.

    * **PU_PER_BUS** — voltagem por barra explicitada pelo engenheiro.
      Útil para cenários what-if. Requer ``bus_voltage_pu`` parameter.

    * **NO_LOAD_WITH_TAP** — voltagem nominal + taps de transformador.
      Pior-caso conservador (típico para arc-flash dimensionamento).
      Aplica ``max_pu`` da tolerância.

    References
    ----------
    PTW Tutorial §Part 5 p. 131-135.
    """

    LOAD_FLOW = "load_flow"
    PU_ALL = "pu_all"
    PU_PER_BUS = "pu_per_bus"
    NO_LOAD_WITH_TAP = "no_load_with_tap"


# A_Fault §1.3.3 p. 1-10 linha 558 — default mode.
DEFAULT_PRE_FAULT_MODE: PreFaultMode = PreFaultMode.PU_ALL


@dataclass(frozen=True)
class VoltageTolerance:
    """Tolerância de voltagem em 3 níveis: min / regular / max.

    Per PTW Tutorial §Part 5 p. 135-136: cada equipamento (Utility, Cable,
    Transformer) tem sua tolerância de voltagem para cenários Min/Reg/Max
    em arc-flash e interrupting duty.

    Invariante: ``min_pu ≤ regular_pu ≤ max_pu``.

    Attributes
    ----------
    min_pu
        Pior-caso baixo (ex: 0.95 pu = -5% ANSI).
    regular_pu
        Valor regular/típico (ex: 1.00 pu).
    max_pu
        Pior-caso alto (ex: 1.05 pu = +5% ANSI).

    References
    ----------
    PTW Tutorial §Part 5 p. 135-136.
    NEMA + IEEE Std 141 (Red Book) — ±5% típico industrial.
    """

    min_pu: float
    regular_pu: float
    max_pu: float

    def __post_init__(self) -> None:
        if self.min_pu < 0 or self.regular_pu < 0 or self.max_pu < 0:
            raise ValueError(
                f"Voltages must be non-negative: "
                f"min={self.min_pu}, reg={self.regular_pu}, max={self.max_pu}"
            )
        if not (self.min_pu <= self.regular_pu <= self.max_pu):
            raise ValueError(
                f"VoltageTolerance violation: must be min ≤ regular ≤ max; "
                f"got ({self.min_pu}, {self.regular_pu}, {self.max_pu})"
            )


# Defaults canônicos por classe de equipamento (NEMA / IEEE 141).
DEFAULT_ANSI_TOLERANCE: VoltageTolerance = VoltageTolerance(
    min_pu=0.95, regular_pu=1.00, max_pu=1.05
)

DEFAULT_UTILITY_TOLERANCE: VoltageTolerance = VoltageTolerance(
    min_pu=0.95, regular_pu=1.00, max_pu=1.05
)

DEFAULT_CABLE_TOLERANCE: VoltageTolerance = VoltageTolerance(
    min_pu=1.00, regular_pu=1.00, max_pu=1.00
)

DEFAULT_TRANSFORMER_TOLERANCE: VoltageTolerance = VoltageTolerance(
    min_pu=0.975, regular_pu=1.00, max_pu=1.025
)


def voltage_with_tolerance(
    nominal_pu: float,
    tolerance: VoltageTolerance,
    mode: PreFaultMode,
    *,
    lf_voltage_pu: float | None = None,
    bus_voltage_pu: float | None = None,
) -> float:
    """Compute the **effective pre-fault voltage** under a given mode.

    Per PTW Tutorial §Part 5 p. 131-135:

    * ``LOAD_FLOW``: returns ``lf_voltage_pu`` (must be provided).
    * ``PU_ALL``: returns ``tolerance.regular_pu``.
    * ``PU_PER_BUS``: returns ``bus_voltage_pu`` (or regular if missing).
    * ``NO_LOAD_WITH_TAP``: returns ``tolerance.max_pu`` (worst-case high).

    Parameters
    ----------
    nominal_pu
        Nominal system voltage at the bus, pu.
    tolerance
        Voltage tolerance for the equipment class.
    mode
        Pre-fault voltage application mode.
    lf_voltage_pu
        Load Flow result (required for ``LOAD_FLOW`` mode).
    bus_voltage_pu
        Per-bus override (used by ``PU_PER_BUS`` mode).

    Returns
    -------
    float
        Effective pre-fault voltage in pu.

    Raises
    ------
    ValueError
        If ``LOAD_FLOW`` mode without ``lf_voltage_pu``.

    References
    ----------
    PTW Tutorial §Part 5 p. 131-135.
    """
    if mode == PreFaultMode.LOAD_FLOW:
        if lf_voltage_pu is None:
            raise ValueError(
                "LOAD_FLOW mode requires lf_voltage_pu argument"
            )
        return lf_voltage_pu

    if mode == PreFaultMode.PU_PER_BUS:
        return bus_voltage_pu if bus_voltage_pu is not None else tolerance.regular_pu

    if mode == PreFaultMode.NO_LOAD_WITH_TAP:
        return tolerance.max_pu

    # PU_ALL (default)
    return tolerance.regular_pu


def combined_worst_case_voltage(
    utility_tolerance: VoltageTolerance,
    transformer_tolerance: VoltageTolerance,
    cable_tolerance: VoltageTolerance,
    scenario: str = "max",
) -> float:
    """Combine multiplicative tolerances Util × TX × Cable for worst-case.

    Per PTW Tutorial §Part 5 p. 135-136: para cenário **worst-case high**,
    multiplicar Util.max × TX.max × Cable.max — o resultado dá a maior
    voltagem possível pré-falta.

    Para **worst-case low**, multiplicar mínimos.

    Parameters
    ----------
    utility_tolerance, transformer_tolerance, cable_tolerance
        Tolerâncias por equipamento.
    scenario
        ``"max"`` → multiplicar máximos; ``"min"`` → mínimos;
        ``"regular"`` → regulares.

    Returns
    -------
    float
        Voltagem combinada efetiva, pu.

    References
    ----------
    PTW Tutorial §Part 5 p. 135-136.
    """
    if scenario not in ("min", "regular", "max"):
        raise ValueError(
            f"scenario must be 'min', 'regular', or 'max'; got {scenario!r}"
        )
    if scenario == "max":
        return utility_tolerance.max_pu * transformer_tolerance.max_pu * cable_tolerance.max_pu
    if scenario == "min":
        return utility_tolerance.min_pu * transformer_tolerance.min_pu * cable_tolerance.min_pu
    return (
        utility_tolerance.regular_pu
        * transformer_tolerance.regular_pu
        * cable_tolerance.regular_pu
    )


__all__ = [
    "PreFaultMode",
    "DEFAULT_PRE_FAULT_MODE",
    "VoltageTolerance",
    "DEFAULT_ANSI_TOLERANCE",
    "DEFAULT_UTILITY_TOLERANCE",
    "DEFAULT_CABLE_TOLERANCE",
    "DEFAULT_TRANSFORMER_TOLERANCE",
    "voltage_with_tolerance",
    "combined_worst_case_voltage",
]
