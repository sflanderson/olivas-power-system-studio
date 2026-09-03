"""
app.simulation.emt.probes — sondas de tensão nodal, tensão de ramo e
corrente de ramo do motor EMT dedicado.

Papel no fluxo de trabalho
===========================

O kernel EMT existe para alimentar o núcleo de prognóstico de vida
residual do isolamento. A cadeia é::

    Circuit + Solver  →  Probe (série temporal)
                      →  app.postprocessor.prognosis.stress_profile
                         .extract_stress_events(...)
                      →  s_{m,j} = [V_pk, T1, dv/dt, E, n_r, θ]
                      →  CombinedDamageAccumulator / EkfRulEstimator

As sondas gravam em unidades do SI (volts e ampères). A conversão para
quilovolts — unidade exigida por ``extract_stress_events`` — é feita
por :func:`to_stress_profile`, que também repassa a impedância de
surto usada na estimativa de energia ``E = ∫ v²/Z dt``.

Convenções
==========

* A sonda de tensão nodal mede em relação ao nó de referência.
* A sonda de tensão de ramo mede ``v_p − v_n`` do próprio ramo.
* A sonda de corrente de ramo devolve a corrente do modelo companheiro
  ``i = G·v + I_hist``, positiva SAINDO do terminal ``p``. Para a
  linha de Bergeron, ``terminal=0`` é ``i_km`` e ``terminal=1`` é
  ``i_mk`` (ambas entrando na linha).
* Nenhuma sonda faz I/O: as séries ficam em memória, em listas de
  ``float``, e são convertidas para ``numpy`` sob demanda.

Este módulo é puro: sem I/O, sem GUI, sem estado global, determinístico.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence

import numpy as np

from app.core.logging_config import get_logger

from app.simulation.emt.components import Component, is_ground, node_voltage

if TYPE_CHECKING:  # pragma: no cover - apenas para type hints
    from app.postprocessor.prognosis.stress_profile import StressProfile
    from app.simulation.emt.circuit import Circuit, Solver

log = get_logger(__name__)

#: Fator de conversão de volt para quilovolt.
V_TO_KV: float = 1.0e-3


class Probe:
    """Sonda genérica: acumula ``(t, valor)`` a cada passo registrado.

    Contrato usado por :class:`app.simulation.emt.circuit.Solver`:

    * :meth:`bind` é chamado no início da execução, com o circuito já
      montado;
    * :meth:`reset` limpa as séries;
    * :meth:`record` é chamado após cada passo completo.
    """

    def __init__(self, name: str, unit: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("o nome da sonda deve ser uma string não vazia")
        self.name: str = name
        self.unit: str = str(unit)
        self._t: list[float] = []
        self._y: list[float] = []

    # -- ciclo de vida ------------------------------------------------------

    def bind(self, circuit: "Circuit") -> None:
        """Resolve referências ao circuito montado."""

    def reset(self) -> None:
        """Descarta as séries acumuladas."""
        self._t = []
        self._y = []

    def sample(self, t: float, x: np.ndarray, solver: "Solver") -> float:
        """Valor instantâneo da grandeza medida. Redefinido nas subclasses."""
        raise NotImplementedError

    def record(self, t: float, x: np.ndarray, solver: "Solver") -> None:
        """Grava uma amostra da grandeza no instante ``t``."""
        self._t.append(float(t))
        self._y.append(float(self.sample(t, x, solver)))

    # -- leitura ------------------------------------------------------------

    @property
    def time_s(self) -> np.ndarray:
        """Base de tempo registrada [s]."""
        return np.asarray(self._t, dtype=float)

    @property
    def values(self) -> np.ndarray:
        """Série registrada, na unidade :attr:`unit`."""
        return np.asarray(self._y, dtype=float)

    @property
    def n_samples(self) -> int:
        """Número de amostras registradas."""
        return len(self._t)

    def peak(self) -> float:
        """Maior valor em MÓDULO da série, com sinal preservado."""
        if not self._y:
            raise ValueError(f"sonda {self.name!r} sem amostras")
        idx = int(np.argmax(np.abs(self.values)))
        return float(self._y[idx])

    def __len__(self) -> int:  # pragma: no cover - conveniência
        return len(self._t)

    def __repr__(self) -> str:  # pragma: no cover - conveniência
        return f"{type(self).__name__}({self.name!r}, n={len(self._t)})"


class NodeVoltageProbe(Probe):
    """Tensão de um nó em relação à terra [V]."""

    def __init__(self, name: str, node: str) -> None:
        super().__init__(name, "V")
        self.node: str = str(node)
        self._index: int = -1

    def bind(self, circuit: "Circuit") -> None:
        if is_ground(self.node):
            self._index = -1
            return
        index = circuit.node_index.get(self.node)
        if index is None:
            raise ValueError(
                f"sonda {self.name!r}: nó {self.node!r} não existe no circuito"
            )
        self._index = int(index)

    def sample(self, t: float, x: np.ndarray, solver: "Solver") -> float:
        return node_voltage(x, self._index)


class BranchVoltageProbe(Probe):
    """Tensão sobre um ramo, ``v_p − v_n`` [V]."""

    def __init__(self, name: str, component: Component, *, terminal: int = 0) -> None:
        super().__init__(name, "V")
        if not isinstance(component, Component):
            raise ValueError(
                f"sonda {name!r}: esperado Component, obtido {type(component).__name__}"
            )
        term = int(terminal)
        if term < 0 or term >= component.n_branches():
            raise ValueError(
                f"sonda {name!r}: terminal {term} fora da faixa "
                f"[0, {component.n_branches() - 1}] do ramo {component.name!r}"
            )
        self.component: Component = component
        self.terminal: int = term

    def sample(self, t: float, x: np.ndarray, solver: "Solver") -> float:
        return self.component.branch_voltage(self.terminal)


class BranchCurrentProbe(Probe):
    """Corrente de um ramo, positiva saindo do terminal ``p`` [A]."""

    def __init__(self, name: str, component: Component, *, terminal: int = 0) -> None:
        super().__init__(name, "A")
        if not isinstance(component, Component):
            raise ValueError(
                f"sonda {name!r}: esperado Component, obtido {type(component).__name__}"
            )
        term = int(terminal)
        if term < 0 or term >= component.n_branches():
            raise ValueError(
                f"sonda {name!r}: terminal {term} fora da faixa "
                f"[0, {component.n_branches() - 1}] do ramo {component.name!r}"
            )
        self.component: Component = component
        self.terminal: int = term

    def sample(self, t: float, x: np.ndarray, solver: "Solver") -> float:
        return self.component.branch_current(self.terminal)


class DifferentialVoltageProbe(Probe):
    """Diferença de tensão entre dois nós, ``v_a − v_b`` [V].

    Útil para a TRV medida sobre os contatos do disjuntor quando a
    chave é composta por vários ramos (arco, capacitância de contato).
    """

    def __init__(self, name: str, node_a: str, node_b: str) -> None:
        super().__init__(name, "V")
        self.node_a: str = str(node_a)
        self.node_b: str = str(node_b)
        if self.node_a == self.node_b:
            raise ValueError(f"sonda {name!r}: nós iguais {self.node_a!r}")
        self._ia: int = -1
        self._ib: int = -1

    def bind(self, circuit: "Circuit") -> None:
        idx = circuit.node_index
        for attr, node in (("_ia", self.node_a), ("_ib", self.node_b)):
            if is_ground(node):
                setattr(self, attr, -1)
                continue
            if node not in idx:
                raise ValueError(
                    f"sonda {self.name!r}: nó {node!r} não existe no circuito"
                )
            setattr(self, attr, int(idx[node]))

    def sample(self, t: float, x: np.ndarray, solver: "Solver") -> float:
        return node_voltage(x, self._ia) - node_voltage(x, self._ib)


# ---------------------------------------------------------------------------
# Ponte para o núcleo de prognóstico
# ---------------------------------------------------------------------------


def to_kV(probe: Probe) -> np.ndarray:
    """Converte a série de uma sonda de tensão de volts para quilovolts.

    Raises
    ------
    ValueError
        A sonda não é de tensão (``unit != "V"``) ou está vazia.
    """
    if probe.unit != "V":
        raise ValueError(
            f"sonda {probe.name!r} é de unidade {probe.unit!r}; "
            f"a conversão para kV só se aplica a sondas de tensão"
        )
    if probe.n_samples == 0:
        raise ValueError(f"sonda {probe.name!r} sem amostras")
    return probe.values * V_TO_KV


def to_stress_profile(
    probe: Probe,
    *,
    threshold_kV: float,
    surge_impedance_ohm: float | None = None,
    theta_C: float = 40.0,
    label: str = "",
    source: str = "",
    **kwargs: Any,
) -> "StressProfile":
    """Converte a série de uma sonda de tensão em perfil de estresse.

    Delega a
    :func:`app.postprocessor.prognosis.stress_profile.extract_stress_events`,
    convertendo a série de volts para quilovolts. Os argumentos extras
    (``group_window_s``, ``min_samples_per_front``, ``coarse_step_s``)
    são repassados sem alteração.

    O ``source`` padrão identifica o motor EMT dedicado, para que o
    laudo distinga séries simuladas de oscilografias reais.

    Raises
    ------
    ValueError
        Sonda vazia, sonda que não é de tensão, ou menos de 3 amostras
        (validação de ``extract_stress_events``).
    """
    from app.postprocessor.prognosis.stress_profile import extract_stress_events

    voltage_kV = to_kV(probe)
    return extract_stress_events(
        probe.time_s.tolist(),
        voltage_kV.tolist(),
        threshold_kV=threshold_kV,
        surge_impedance_ohm=surge_impedance_ohm,
        theta_C=theta_C,
        source=source or f"emt:{probe.name}",
        label=label or probe.name,
        **kwargs,
    )


def probe_series(probes: Sequence[Probe]) -> dict[str, np.ndarray]:
    """Agrupa as séries de várias sondas em um dicionário ``nome → série``."""
    out: dict[str, np.ndarray] = {}
    for p in probes:
        if p.name in out:
            raise ValueError(f"nomes de sonda duplicados: {p.name!r}")
        out[p.name] = p.values
    return out


__all__ = [
    "V_TO_KV",
    "Probe",
    "NodeVoltageProbe",
    "BranchVoltageProbe",
    "BranchCurrentProbe",
    "DifferentialVoltageProbe",
    "to_kV",
    "to_stress_profile",
    "probe_series",
]
