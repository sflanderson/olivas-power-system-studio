"""
app.postprocessor.power_flow — Estudo de fluxo de potência
trifásico balanceado (positive-sequence) via Newton-Raphson,
fundação para os estudos de curto-circuito e arc-flash.

Motivação
==========

A IEC 60909-0 §3 menciona o **voltage factor c** (1.10 max,
1.05 / 0.95 para LV) que compensa variações da tensão real
da rede. Mas esses defaults são conservadores. Para análise
de **arc-flash NBR 17227** com clearing rápido, ou
**coordenação seletiva** com baixa margem, precisamos da
tensão pré-falta REAL — que vem do fluxo de potência.

Cadeia de estudos integrados (NBR 17227 §5.1.1)
================================================

::

    ┌──────────────────┐
    │ PF + LOAD BALANCE│  ← este módulo
    │ + MOTOR STARTING │
    └────────┬─────────┘
             ↓ V_pre-fault, I_load
    ┌──────────────────┐
    │   SHORT-CIRCUIT  │  app.postprocessor.short_circuit
    │   (IEC 60909-0)  │
    └────────┬─────────┘
             ↓ Ik''
    ┌──────────────────┐
    │   COORDINATION   │  app.postprocessor.relay_coordination
    │   (IEEE 242)     │
    └────────┬─────────┘
             ↓ T_clearing
    ┌──────────────────┐
    │   ARC-FLASH      │  app.postprocessor.arc_flash
    │   (NBR 17227)    │
    └──────────────────┘

Esta entrega completa a fundação inicial (PF) — o pipeline
v0.27.7.x já tem os outros estágios.

Algoritmo Newton-Raphson
=========================

Para um sistema com n barras:

::

    [ΔP]   [∂P/∂θ  ∂P/∂V] [Δθ]
    [  ] = [             ] [  ]
    [ΔQ]   [∂Q/∂θ  ∂Q/∂V] [ΔV]

Onde a matriz é o **Jacobiano** (J). Cada iteração:

1. Calcular P_i, Q_i para cada barra a partir de V e θ
   correntes.
2. Mismatches ΔP_i = P_set_i - P_calc_i, ΔQ_i análogo.
3. Se max |ΔP|, |ΔQ| < tolerância → convergiu.
4. Resolver J·Δx = [ΔP; ΔQ].
5. Atualizar θ ← θ + Δθ, V ← V + ΔV.

Tipos de barra
===============

* **SLACK** (referência): V e θ fixos (geralmente concessionária).
* **PV** (controle de tensão): P gerado e |V| fixos (típico
  geradores síncronos com excitação automática).
* **PQ** (carga): P e Q fixos (cargas, motores).

MVP v0.27.11
=============

* Trifásico balanceado positive-sequence.
* Modelo Y-bus simples (R+jX em série, B/2 shunt).
* Sem limites de Q em PV buses (refinamento futuro).
* Tolerância default 1e-6 pu, max 50 iterações.
* Numpy para álgebra linear.

Limitações conhecidas
======================

* Sem desbalanços de fases — para isso, sequencial 0/1/2
  precisa ser implementado (v0.27.11.5).
* Sem PV→PQ switching quando Q excede limites.
* Sem otimização (load shedding, FACTS).
* Para sistemas grandes (>100 barras), considerar PYPOWER
  ou pandapower.

Referências
============

* John J. Grainger, William D. Stevenson Jr., *Power System
  Analysis*, McGraw-Hill, 1994 — §9 (Newton-Raphson PF).
* Hadi Saadat, *Power System Analysis*, 2nd ed, McGraw-Hill,
  2002 — Chapter 6.
* IEEE Std 399-1997 (Brown Book) — Industrial Power System
  Analysis.
* IEC 60909-0:2016 §3.8 — Voltage factor c (relação com PF).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BusType(str, Enum):
    """Tipo de barra para fluxo de potência (Stevenson §9)."""
    SLACK = "slack"     # V e θ fixos (referência angular)
    PV = "pv"           # |V| e P fixos (gerador com AVR)
    PQ = "pq"           # P e Q fixos (carga, motor)


# ---------------------------------------------------------------------------
# Bus + Branch
# ---------------------------------------------------------------------------


@dataclass
class PfBus:
    """
    Barra para análise de fluxo de potência.

    Para SLACK: V_pu_set e theta_set são fixados.
    Para PV: V_pu_set fixado; P_pu_set fixado; Q_pu_set é
    saída da convergência.
    Para PQ: P_pu_set e Q_pu_set fixados; V e θ são saídas.

    Attributes
    ----------
    id:
        Identificador da barra.
    type:
        Slack, PV ou PQ.
    V_pu_set:
        Tensão setpoint em pu (slack e PV).
    theta_set_rad:
        Ângulo setpoint (slack only). Default 0.
    P_pu_set:
        Potência ativa setpoint em pu (PV e PQ; geração positiva,
        carga negativa).
    Q_pu_set:
        Potência reativa setpoint em pu (PQ only).
    rated_voltage_kV:
        V_LL nominal da barra (para conversão para SI).
    base_MVA:
        Potência base do sistema (default 100).

    Após resolve():

    V_pu_solved, theta_solved_rad: tensão e ângulo soluções.
    P_pu_solved, Q_pu_solved: potências calculadas.
    """

    id: str
    type: BusType
    V_pu_set: float = 1.0
    theta_set_rad: float = 0.0
    P_pu_set: float = 0.0
    Q_pu_set: float = 0.0
    rated_voltage_kV: float = 13.8
    base_MVA: float = 100.0
    # v3.8.1 (closes SKIPPED_BACKLOG C.4) — Q-limits para PV buses
    # Per IEEE 399 §5.3.4: PV bus pode violar Q-limits → switch para PQ
    # mantendo Q no limite (V passa a flutuar).
    Q_min_pu: float = -1e9   # default sem limite (effectively infinite)
    Q_max_pu: float = 1e9
    # Tipo original antes de eventual switching (auditável)
    original_type: BusType | None = None

    # Outputs (preenchidos após resolve())
    V_pu_solved: float = 1.0
    theta_solved_rad: float = 0.0
    P_pu_solved: float = 0.0
    Q_pu_solved: float = 0.0

    @property
    def voltage_kV_solved(self) -> float:
        """Tensão resolvida em kV (linha-linha)."""
        return self.V_pu_solved * self.rated_voltage_kV

    @property
    def voltage_complex_pu(self) -> complex:
        """V·e^(jθ) em pu."""
        return self.V_pu_solved * (
            math.cos(self.theta_solved_rad)
            + 1j * math.sin(self.theta_solved_rad)
        )


@dataclass
class PfBranch:
    """
    Branch (linha ou transformador) entre duas barras.

    Modelo π:

    ::

        from ─[R + jX]─ to
              │       │
              [B/2]   [B/2]   (shunt)
              │       │
             gnd     gnd

    Attributes
    ----------
    from_bus:
        ID da barra de origem.
    to_bus:
        ID da barra de destino.
    R_pu:
        Resistência série (pu).
    X_pu:
        Reatância série (pu).
    B_pu:
        Susceptância shunt total (pu). Cada extremidade recebe
        B/2.
    tap_ratio:
        Tap do transformador (1.0 default; 0.95-1.05 típico).
    description:
        Texto livre.
    """

    from_bus: str
    to_bus: str
    R_pu: float = 0.0
    X_pu: float = 0.1
    B_pu: float = 0.0
    tap_ratio: float = 1.0
    description: str = ""


# ---------------------------------------------------------------------------
# PowerFlowSolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LineFlow:
    """Fluxo em uma linha/branch (em ambos os sentidos)."""
    from_bus: str
    to_bus: str
    P_pu_from: float
    Q_pu_from: float
    P_pu_to: float
    Q_pu_to: float
    P_loss_pu: float
    Q_loss_pu: float


@dataclass(frozen=True)
class PowerFlowSolution:
    """
    Resultado de uma análise de fluxo de potência.

    Attributes
    ----------
    converged:
        True se NR convergiu dentro de max_iterations.
    iterations:
        Número de iterações executadas.
    max_mismatch:
        Maior mismatch (P ou Q) na última iteração.
    bus_voltages_pu:
        ``{bus_id: V_complex}`` em pu.
    line_flows:
        Lista de fluxos por linha.
    total_losses_pu:
        Soma das perdas (P + jQ) na rede.
    """

    converged: bool
    iterations: int
    max_mismatch: float
    bus_voltages_pu: dict
    line_flows: tuple
    total_losses_pu: complex

    def summary(self) -> str:
        """Sumário humano-readable."""
        status = "✓ Converged" if self.converged else "✗ DID NOT converge"
        lines = [
            f"=== Power Flow Solution ({status}) ===",
            f"Iterations: {self.iterations}",
            f"Max mismatch: {self.max_mismatch:.6e} pu",
            f"Total losses: {self.total_losses_pu.real:.6f} + "
            f"j{self.total_losses_pu.imag:.6f} pu",
            "",
            "Bus voltages:",
        ]
        for bus_id, V in self.bus_voltages_pu.items():
            mag = abs(V)
            ang_deg = math.degrees(math.atan2(V.imag, V.real))
            lines.append(
                f"  {bus_id:>10}: |V| = {mag:.4f} pu, "
                f"∠ = {ang_deg:+.3f}°"
            )
        if self.line_flows:
            lines.append("")
            lines.append("Line flows (from → to, S = P + jQ):")
            for f in self.line_flows:
                lines.append(
                    f"  {f.from_bus:>6} → {f.to_bus:<6}: "
                    f"S = {f.P_pu_from:+.4f} + "
                    f"j{f.Q_pu_from:+.4f} pu  "
                    f"(losses: {f.P_loss_pu:.4f} + "
                    f"j{f.Q_loss_pu:.4f})"
                )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Y-bus matrix
# ---------------------------------------------------------------------------


def build_ybus(
    buses: list, branches: list,
) -> "tuple[dict[str, int], object]":
    """
    Constrói a matriz Y-bus (admittance) do sistema.

    Y[i,j] (i≠j) = -y_ij (admitância série entre i e j)
    Y[i,i] = Σ y_ij + Σ y_shunt_i (auto-admitância)

    Returns
    -------
    tuple[dict, np.ndarray]
        Mapeamento bus_id → índice na matriz; matriz Y complexa
        (n × n).
    """
    import numpy as np

    bus_idx = {b.id: i for i, b in enumerate(buses)}
    n = len(buses)
    Y = np.zeros((n, n), dtype=complex)

    for br in branches:
        if br.from_bus not in bus_idx or br.to_bus not in bus_idx:
            raise ValueError(
                f"Branch references unknown bus: "
                f"{br.from_bus} → {br.to_bus}"
            )
        i = bus_idx[br.from_bus]
        j = bus_idx[br.to_bus]
        z_series = complex(br.R_pu, br.X_pu)
        if abs(z_series) == 0:
            raise ValueError(
                f"Branch {br.from_bus}→{br.to_bus} has zero impedance"
            )
        y_series = 1.0 / z_series
        # Tap (em from_bus side por convenção)
        a = br.tap_ratio
        y_half_shunt = 1j * br.B_pu / 2.0
        # Off-diagonal: -y_series / a
        Y[i, j] -= y_series / a
        Y[j, i] -= y_series / a
        # Diagonal i: y_series / a² + B/2
        Y[i, i] += y_series / (a * a) + y_half_shunt
        # Diagonal j: y_series + B/2
        Y[j, j] += y_series + y_half_shunt
    return bus_idx, Y


# ---------------------------------------------------------------------------
# Newton-Raphson Power Flow
# ---------------------------------------------------------------------------


def solve_power_flow(
    buses: list,
    branches: list,
    tolerance: float = 1.0e-6,
    max_iterations: int = 50,
    verbose: bool = False,
) -> PowerFlowSolution:
    """
    Resolve o fluxo de potência por Newton-Raphson.

    Parameters
    ----------
    buses:
        Lista de ``PfBus``. Pelo menos 1 SLACK obrigatória.
    branches:
        Lista de ``PfBranch``.
    tolerance:
        Tolerância de convergência em pu.
    max_iterations:
        Máximo de iterações antes de declarar não-convergente.
    verbose:
        Se True, imprime diagnóstico iteração-a-iteração.

    Returns
    -------
    PowerFlowSolution
    """
    import numpy as np

    if not buses:
        raise ValueError("Lista de buses vazia.")

    # Verifica que existe pelo menos 1 SLACK
    n_slack = sum(1 for b in buses if b.type == BusType.SLACK)
    if n_slack != 1:
        raise ValueError(
            f"Sistema deve ter exatamente 1 barra SLACK "
            f"(achadas {n_slack})."
        )

    bus_idx, Y = build_ybus(buses, branches)
    n = len(buses)

    # Inicialização (flat start)
    V = np.array(
        [b.V_pu_set if b.type != BusType.PQ else 1.0 for b in buses],
        dtype=float,
    )
    theta = np.array(
        [b.theta_set_rad if b.type == BusType.SLACK else 0.0
         for b in buses],
        dtype=float,
    )

    # Setpoints de P e Q
    P_set = np.array([b.P_pu_set for b in buses], dtype=float)
    Q_set = np.array([b.Q_pu_set for b in buses], dtype=float)

    # Listas de índices por tipo
    pq_idx = [i for i, b in enumerate(buses) if b.type == BusType.PQ]
    pv_idx = [i for i, b in enumerate(buses) if b.type == BusType.PV]
    slack_idx = [i for i, b in enumerate(buses) if b.type == BusType.SLACK][0]

    # Listas para Jacobian (não-slack para P e PQ para Q)
    p_eq_idx = pv_idx + pq_idx     # equações de P (não-slack)
    q_eq_idx = pq_idx              # equações de Q (PQ only)

    G = Y.real
    B = Y.imag

    converged = False
    iteration = 0
    max_mismatch = float("inf")

    for iteration in range(1, max_iterations + 1):
        # Calcula P e Q para cada barra a partir de V e θ
        P_calc = np.zeros(n)
        Q_calc = np.zeros(n)
        for i in range(n):
            for k in range(n):
                P_calc[i] += V[i] * V[k] * (
                    G[i, k] * math.cos(theta[i] - theta[k])
                    + B[i, k] * math.sin(theta[i] - theta[k])
                )
                Q_calc[i] += V[i] * V[k] * (
                    G[i, k] * math.sin(theta[i] - theta[k])
                    - B[i, k] * math.cos(theta[i] - theta[k])
                )

        # Mismatches
        dP = np.array([P_set[i] - P_calc[i] for i in p_eq_idx])
        dQ = np.array([Q_set[i] - Q_calc[i] for i in q_eq_idx])
        mismatch = np.concatenate([dP, dQ])
        max_mismatch = float(np.max(np.abs(mismatch))) if len(mismatch) else 0.0

        if verbose:
            print(f"  iter {iteration}: max mismatch = {max_mismatch:.6e}")

        if max_mismatch < tolerance:
            converged = True
            break

        # Build Jacobian
        n_p = len(p_eq_idx)
        n_q = len(q_eq_idx)
        J = np.zeros((n_p + n_q, n_p + n_q))

        # H = ∂P/∂θ (top-left)
        for r, i in enumerate(p_eq_idx):
            for c, k in enumerate(p_eq_idx):
                if i == k:
                    J[r, c] = -Q_calc[i] - B[i, i] * V[i] ** 2
                else:
                    J[r, c] = V[i] * V[k] * (
                        G[i, k] * math.sin(theta[i] - theta[k])
                        - B[i, k] * math.cos(theta[i] - theta[k])
                    )

        # N = ∂P/∂V (top-right) — só PQ buses
        for r, i in enumerate(p_eq_idx):
            for c, k in enumerate(q_eq_idx):
                if i == k:
                    J[r, n_p + c] = (
                        P_calc[i] / V[i] + G[i, i] * V[i]
                    )
                else:
                    J[r, n_p + c] = V[i] * (
                        G[i, k] * math.cos(theta[i] - theta[k])
                        + B[i, k] * math.sin(theta[i] - theta[k])
                    )

        # M = ∂Q/∂θ (bottom-left)
        for r, i in enumerate(q_eq_idx):
            for c, k in enumerate(p_eq_idx):
                if i == k:
                    J[n_p + r, c] = (
                        P_calc[i] - G[i, i] * V[i] ** 2
                    )
                else:
                    J[n_p + r, c] = -V[i] * V[k] * (
                        G[i, k] * math.cos(theta[i] - theta[k])
                        + B[i, k] * math.sin(theta[i] - theta[k])
                    )

        # L = ∂Q/∂V (bottom-right)
        for r, i in enumerate(q_eq_idx):
            for c, k in enumerate(q_eq_idx):
                if i == k:
                    J[n_p + r, n_p + c] = (
                        Q_calc[i] / V[i] - B[i, i] * V[i]
                    )
                else:
                    J[n_p + r, n_p + c] = V[i] * (
                        G[i, k] * math.sin(theta[i] - theta[k])
                        - B[i, k] * math.cos(theta[i] - theta[k])
                    )

        # Solve J · dx = mismatch
        try:
            dx = np.linalg.solve(J, mismatch)
        except np.linalg.LinAlgError:
            # Singular Jacobian — não converge
            break

        # Update
        for r, i in enumerate(p_eq_idx):
            theta[i] += dx[r]
        for r, i in enumerate(q_eq_idx):
            V[i] += dx[n_p + r]

    # Atualiza buses com soluções
    for i, b in enumerate(buses):
        b.V_pu_solved = V[i]
        b.theta_solved_rad = theta[i]
        b.P_pu_solved = P_calc[i]
        b.Q_pu_solved = Q_calc[i]

    # Calcula fluxos de linha
    line_flows = _compute_line_flows(buses, branches, bus_idx)

    # Total losses (soma de fluxos com sinal apropriado)
    total_losses = sum(
        complex(f.P_loss_pu, f.Q_loss_pu) for f in line_flows
    )

    bus_voltages_pu = {
        b.id: b.voltage_complex_pu for b in buses
    }

    return PowerFlowSolution(
        converged=converged,
        iterations=iteration,
        max_mismatch=max_mismatch,
        bus_voltages_pu=bus_voltages_pu,
        line_flows=tuple(line_flows),
        total_losses_pu=total_losses,
    )


def _compute_line_flows(
    buses: list, branches: list, bus_idx: dict,
) -> list:
    """Calcula fluxos de potência em cada branch."""
    bus_by_id = {b.id: b for b in buses}
    flows = []
    for br in branches:
        bf = bus_by_id[br.from_bus]
        bt = bus_by_id[br.to_bus]
        Vf = bf.voltage_complex_pu
        Vt = bt.voltage_complex_pu
        z_series = complex(br.R_pu, br.X_pu)
        y_series = 1.0 / z_series
        y_half = 1j * br.B_pu / 2.0
        a = br.tap_ratio

        # Current from from_bus into branch (excluding shunt)
        I_ft = (Vf / a - Vt) * y_series + Vf / a * y_half
        I_tf = (Vt - Vf / a) * y_series + Vt * y_half

        S_from = (Vf / a) * I_ft.conjugate()
        S_to = Vt * I_tf.conjugate()
        S_loss = S_from + S_to

        flows.append(LineFlow(
            from_bus=br.from_bus,
            to_bus=br.to_bus,
            P_pu_from=S_from.real,
            Q_pu_from=S_from.imag,
            P_pu_to=S_to.real,
            Q_pu_to=S_to.imag,
            P_loss_pu=S_loss.real,
            Q_loss_pu=S_loss.imag,
        ))
    return flows


# ---------------------------------------------------------------------------
# High-level system builder
# ---------------------------------------------------------------------------


@dataclass
class PowerFlowSystem:
    """
    Sistema de PF de alto nível com builder API.

    Use ``system.add_slack(...)``, ``add_pv(...)``, ``add_pq(...)``
    para construir, depois ``system.solve()``.

    Attributes
    ----------
    base_MVA:
        Potência base do sistema (default 100 MVA).
    """

    base_MVA: float = 100.0
    buses: list = field(default_factory=list)
    branches: list = field(default_factory=list)

    def add_slack(
        self, id: str, V_pu: float = 1.0,
        theta_rad: float = 0.0, rated_voltage_kV: float = 13.8,
    ) -> PfBus:
        """Adiciona barra SLACK (referência)."""
        b = PfBus(
            id=id, type=BusType.SLACK,
            V_pu_set=V_pu, theta_set_rad=theta_rad,
            rated_voltage_kV=rated_voltage_kV,
            base_MVA=self.base_MVA,
        )
        self.buses.append(b)
        return b

    def add_pv(
        self, id: str, P_pu: float, V_pu: float = 1.0,
        rated_voltage_kV: float = 13.8,
        Q_min_pu: float = -1e9,
        Q_max_pu: float = 1e9,
    ) -> PfBus:
        """Adiciona barra PV (gerador com AVR).

        v3.8.1 (closes SKIPPED_BACKLOG C.4): aceita Q_min_pu/Q_max_pu para
        suporte a switching PV→PQ via :meth:`solve_with_q_limits`.
        Defaults effectively infinitos preservam comportamento legacy.
        """
        b = PfBus(
            id=id, type=BusType.PV,
            V_pu_set=V_pu, P_pu_set=P_pu,
            rated_voltage_kV=rated_voltage_kV,
            base_MVA=self.base_MVA,
            Q_min_pu=Q_min_pu,
            Q_max_pu=Q_max_pu,
        )
        self.buses.append(b)
        return b

    def add_pq(
        self, id: str, P_pu: float, Q_pu: float,
        rated_voltage_kV: float = 13.8,
    ) -> PfBus:
        """
        Adiciona barra PQ. Convenção: cargas com P negativo
        (consomem); geração com P positivo.
        """
        b = PfBus(
            id=id, type=BusType.PQ,
            P_pu_set=P_pu, Q_pu_set=Q_pu,
            rated_voltage_kV=rated_voltage_kV,
            base_MVA=self.base_MVA,
        )
        self.buses.append(b)
        return b

    def add_branch(
        self, from_bus: str, to_bus: str,
        R_pu: float = 0.0, X_pu: float = 0.1,
        B_pu: float = 0.0, tap_ratio: float = 1.0,
        description: str = "",
    ) -> PfBranch:
        """Adiciona uma linha ou transformador."""
        br = PfBranch(
            from_bus=from_bus, to_bus=to_bus,
            R_pu=R_pu, X_pu=X_pu, B_pu=B_pu,
            tap_ratio=tap_ratio, description=description,
        )
        self.branches.append(br)
        return br

    def solve(
        self, tolerance: float = 1e-6,
        max_iterations: int = 50,
        verbose: bool = False,
    ) -> PowerFlowSolution:
        """Resolve via Newton-Raphson."""
        return solve_power_flow(
            self.buses, self.branches,
            tolerance=tolerance,
            max_iterations=max_iterations,
            verbose=verbose,
        )

    def get_bus(self, bus_id: str) -> Optional[PfBus]:
        """Retorna a barra pelo ID."""
        for b in self.buses:
            if b.id == bus_id:
                return b
        return None

    # ------------------------------------------------------------------
    # v3.8.1 (closes SKIPPED_BACKLOG C.4) — PV→PQ Q-limit switching
    # ------------------------------------------------------------------

    def solve_with_q_limits(
        self,
        tolerance: float = 1e-6,
        max_iterations: int = 50,
        max_switching_iterations: int = 5,
        verbose: bool = False,
    ) -> "PowerFlowSolution":
        """Resolve PF com PV→PQ switching para enforcement de Q-limits.

        Algoritmo (IEEE 399 §5.3.4):
        1. Resolve via Newton-Raphson
        2. Para cada PV bus, verifica se ``Q_solved > Q_max`` ou
           ``Q_solved < Q_min``. Se viola:
           - Switch type to PQ
           - Pin Q_pu_set ao limite violado
        3. Re-resolve até convergência ou max_switching_iterations.

        Bus tem ``original_type`` preservado para auditoria.

        Returns
        -------
        PowerFlowSolution
            Solução final + ``q_limit_violations`` populado com
            mensagens descritivas das mudanças.

        Reference
        ---------
        IEEE Std 399-1997 §5.3.4 (PV→PQ enforcement).
        """
        violations: list[str] = []
        # Save original types for auditability
        for b in self.buses:
            if b.original_type is None:
                b.original_type = b.type

        for sw_iter in range(max_switching_iterations + 1):
            sol = self.solve(
                tolerance=tolerance,
                max_iterations=max_iterations,
                verbose=verbose,
            )
            if not sol.converged:
                violations.append(
                    f"NR did not converge at switching iter {sw_iter}"
                )
                break
            # Check PV buses for Q violations
            switched_any = False
            for b in self.buses:
                if b.original_type == BusType.PV and b.type == BusType.PV:
                    q = b.Q_pu_solved
                    if q > b.Q_max_pu:
                        b.type = BusType.PQ
                        b.Q_pu_set = b.Q_max_pu
                        violations.append(
                            f"Bus {b.id}: Q={q:.4f} > Q_max={b.Q_max_pu:.4f} "
                            f"→ switched to PQ at Q_max"
                        )
                        switched_any = True
                    elif q < b.Q_min_pu:
                        b.type = BusType.PQ
                        b.Q_pu_set = b.Q_min_pu
                        violations.append(
                            f"Bus {b.id}: Q={q:.4f} < Q_min={b.Q_min_pu:.4f} "
                            f"→ switched to PQ at Q_min"
                        )
                        switched_any = True
            if not switched_any:
                # No more violations — converged
                break
        # Attach violations to solution (frozen dataclass — use __setattr__)
        try:
            object.__setattr__(sol, "q_limit_violations", violations)
        except (AttributeError, NameError):
            pass
        return sol
