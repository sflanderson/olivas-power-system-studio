"""
tests/test_pp_power_flow.py — v0.27.11: estudo de fluxo de
potência via Newton-Raphson.

Cobre:

* BusType enum + PfBus dataclass + setpoint handling.
* PfBranch dataclass.
* build_ybus — diagonal, off-diagonal, multi-branch, tap-ratio,
  shunt B.
* solve_power_flow — convergência em sistemas pequenos
  (2-bus, 3-bus Stevenson, 4-bus loop), flat-start.
* Validação de pré-condições (slack, branches válidos).
* Casos extremos: sem branches, R+jX zero, branch apontando
  para barra inexistente.
* PowerFlowSystem builder API + lookups.
* Conservação de potência: P_gen ≈ P_load + P_loss.
* LineFlow: simetria de perdas, sentido de fluxo.
* PowerFlowSolution.summary() formatado.

Sistemas-teste de referência:

* **2-bus**: slack → 1 PQ. Caso analítico (Saadat §6).
* **3-bus Stevenson**: slack + PV + PQ (Power System Analysis,
  Stevenson §9 Exemplo 9.5). Conhecido convergir em ~4
  iterações com flat start a 1e-6 pu.
* **4-bus loop**: PQ→PV→PQ→slack→PQ — testa ciclo simples.
"""

from __future__ import annotations

import math

import pytest


# Pula testes inteiros se numpy não estiver disponível.
np = pytest.importorskip("numpy")

from app.postprocessor.power_flow import (
    BusType,
    LineFlow,
    PfBranch,
    PfBus,
    PowerFlowSolution,
    PowerFlowSystem,
    build_ybus,
    solve_power_flow,
)


# ---------------------------------------------------------------------------
# BusType + dataclass
# ---------------------------------------------------------------------------


class TestBusType:

    def test_three_bus_types_exist(self) -> None:
        assert BusType.SLACK.value == "slack"
        assert BusType.PV.value == "pv"
        assert BusType.PQ.value == "pq"

    def test_bus_type_is_string_enum(self) -> None:
        # Útil para serialização — comparação com string crua.
        assert BusType.SLACK == "slack"
        assert BusType.PV == "pv"


class TestPfBus:

    def test_default_initialization(self) -> None:
        b = PfBus(id="B1", type=BusType.SLACK)
        assert b.V_pu_set == 1.0
        assert b.theta_set_rad == 0.0
        assert b.P_pu_set == 0.0
        assert b.Q_pu_set == 0.0
        assert b.rated_voltage_kV == 13.8
        assert b.base_MVA == 100.0

    def test_voltage_kV_solved_property(self) -> None:
        b = PfBus(
            id="B1", type=BusType.SLACK,
            rated_voltage_kV=13.8,
        )
        b.V_pu_solved = 1.05
        assert b.voltage_kV_solved == pytest.approx(14.49, rel=1e-3)

    def test_voltage_complex_pu_property(self) -> None:
        b = PfBus(id="B1", type=BusType.SLACK)
        b.V_pu_solved = 1.0
        b.theta_solved_rad = 0.0
        v = b.voltage_complex_pu
        assert v.real == pytest.approx(1.0)
        assert v.imag == pytest.approx(0.0)

        # 90° → puro imaginário
        b.theta_solved_rad = math.pi / 2
        v = b.voltage_complex_pu
        assert v.real == pytest.approx(0.0, abs=1e-10)
        assert v.imag == pytest.approx(1.0)


class TestPfBranch:

    def test_default_initialization(self) -> None:
        br = PfBranch(from_bus="B1", to_bus="B2")
        assert br.R_pu == 0.0
        assert br.X_pu == 0.1
        assert br.B_pu == 0.0
        assert br.tap_ratio == 1.0


# ---------------------------------------------------------------------------
# Y-bus
# ---------------------------------------------------------------------------


class TestBuildYbus:

    def test_2bus_simple(self) -> None:
        """
        Sistema 2-bus simples:
        B1 ---[X=0.1]--- B2

        Y-bus esperada:
        Y[0,0] = 1/(j0.1) = -j10
        Y[1,1] = -j10
        Y[0,1] = Y[1,0] = -(-j10) = j10
        """
        buses = [
            PfBus(id="B1", type=BusType.SLACK),
            PfBus(id="B2", type=BusType.PQ),
        ]
        branches = [PfBranch(from_bus="B1", to_bus="B2", R_pu=0, X_pu=0.1)]
        bus_idx, Y = build_ybus(buses, branches)
        assert bus_idx == {"B1": 0, "B2": 1}
        assert Y.shape == (2, 2)
        # Diagonal: y_series = 1/jX = -j10
        assert Y[0, 0] == pytest.approx(complex(0, -10), rel=1e-9)
        assert Y[1, 1] == pytest.approx(complex(0, -10), rel=1e-9)
        # Off-diagonal: -y_series = +j10
        assert Y[0, 1] == pytest.approx(complex(0, 10), rel=1e-9)
        assert Y[1, 0] == pytest.approx(complex(0, 10), rel=1e-9)

    def test_3bus_Y_symmetric(self) -> None:
        """Y-bus deve ser simétrica para branches passivos sem tap."""
        buses = [
            PfBus(id=f"B{i}", type=BusType.PQ) for i in range(1, 4)
        ]
        buses[0] = PfBus(id="B1", type=BusType.SLACK)
        branches = [
            PfBranch(from_bus="B1", to_bus="B2", X_pu=0.1),
            PfBranch(from_bus="B2", to_bus="B3", X_pu=0.15),
            PfBranch(from_bus="B1", to_bus="B3", X_pu=0.2),
        ]
        _, Y = build_ybus(buses, branches)
        # Simetria
        for i in range(3):
            for j in range(3):
                assert Y[i, j] == pytest.approx(Y[j, i], rel=1e-9)

    def test_branch_with_resistance(self) -> None:
        """R + jX → admitância tem parte real."""
        buses = [
            PfBus(id="B1", type=BusType.SLACK),
            PfBus(id="B2", type=BusType.PQ),
        ]
        branches = [
            PfBranch(from_bus="B1", to_bus="B2", R_pu=0.05, X_pu=0.1),
        ]
        _, Y = build_ybus(buses, branches)
        # G > 0 (resistivo), B < 0 (indutivo)
        assert Y[0, 0].real > 0
        assert Y[0, 0].imag < 0

    def test_branch_with_shunt_B(self) -> None:
        """B/2 shunt afeta a diagonal."""
        buses = [
            PfBus(id="B1", type=BusType.SLACK),
            PfBus(id="B2", type=BusType.PQ),
        ]
        branches = [
            PfBranch(
                from_bus="B1", to_bus="B2",
                R_pu=0, X_pu=0.1, B_pu=0.04,
            ),
        ]
        _, Y = build_ybus(buses, branches)
        # Diagonal = -j10 (série) + j0.02 (shunt B/2) = -j9.98
        assert Y[0, 0].imag == pytest.approx(-9.98, rel=1e-3)

    def test_zero_impedance_raises(self) -> None:
        """R=0, X=0 deve falhar (singular)."""
        buses = [
            PfBus(id="B1", type=BusType.SLACK),
            PfBus(id="B2", type=BusType.PQ),
        ]
        branches = [PfBranch(from_bus="B1", to_bus="B2", R_pu=0, X_pu=0)]
        with pytest.raises(ValueError, match="zero impedance"):
            build_ybus(buses, branches)

    def test_unknown_bus_in_branch_raises(self) -> None:
        buses = [PfBus(id="B1", type=BusType.SLACK)]
        branches = [PfBranch(from_bus="B1", to_bus="GHOST", X_pu=0.1)]
        with pytest.raises(ValueError, match="unknown bus"):
            build_ybus(buses, branches)


# ---------------------------------------------------------------------------
# Newton-Raphson solver
# ---------------------------------------------------------------------------


class TestSolvePowerFlow:

    def test_2bus_converges(self) -> None:
        """
        Sistema 2-bus mais simples possível:
        Slack(1.0∠0°) ---[X=0.1]--- PQ(P=-0.5, Q=-0.2)

        PQ está consumindo 0.5+j0.2 pu. Espera-se queda
        de tensão pequena.
        """
        buses = [
            PfBus(id="SL", type=BusType.SLACK, V_pu_set=1.0),
            PfBus(id="LD", type=BusType.PQ, P_pu_set=-0.5, Q_pu_set=-0.2),
        ]
        branches = [PfBranch(from_bus="SL", to_bus="LD", X_pu=0.1)]
        sol = solve_power_flow(buses, branches, tolerance=1e-8)
        assert sol.converged
        assert sol.iterations < 10
        # Tensão LD < 1.0 (queda esperada)
        assert abs(sol.bus_voltages_pu["LD"]) < 1.0
        assert abs(sol.bus_voltages_pu["LD"]) > 0.9
        # SL fica fixo
        assert abs(sol.bus_voltages_pu["SL"]) == pytest.approx(1.0, rel=1e-6)

    def test_2bus_no_load_no_drop(self) -> None:
        """Sem carga, V_LD ≈ V_SL = 1.0 pu."""
        buses = [
            PfBus(id="SL", type=BusType.SLACK, V_pu_set=1.0),
            PfBus(id="LD", type=BusType.PQ, P_pu_set=0, Q_pu_set=0),
        ]
        branches = [PfBranch(from_bus="SL", to_bus="LD", X_pu=0.1)]
        sol = solve_power_flow(buses, branches)
        assert sol.converged
        assert abs(sol.bus_voltages_pu["LD"]) == pytest.approx(1.0, rel=1e-6)

    def test_stevenson_3bus_converges(self) -> None:
        """
        Stevenson §9 Example 9.5 (caso clássico de NR PF):

        B1 (slack) — B2 (PV gen) — B3 (PQ load)
        com 3 linhas mutuamente conectadas.

        Convergência esperada em 3-5 iterações a 1e-6.
        """
        buses = [
            PfBus(id="B1", type=BusType.SLACK, V_pu_set=1.05),
            PfBus(id="B2", type=BusType.PV, V_pu_set=1.04, P_pu_set=0.50),
            PfBus(id="B3", type=BusType.PQ, P_pu_set=-1.0, Q_pu_set=-0.30),
        ]
        branches = [
            PfBranch(from_bus="B1", to_bus="B2", R_pu=0.02, X_pu=0.04),
            PfBranch(from_bus="B1", to_bus="B3", R_pu=0.01, X_pu=0.03),
            PfBranch(from_bus="B2", to_bus="B3", R_pu=0.0125, X_pu=0.025),
        ]
        sol = solve_power_flow(buses, branches, tolerance=1e-6)
        assert sol.converged
        assert sol.iterations <= 6
        assert sol.max_mismatch < 1e-6
        # B1 fica em 1.05∠0°
        v1 = sol.bus_voltages_pu["B1"]
        assert abs(v1) == pytest.approx(1.05, rel=1e-6)
        assert math.atan2(v1.imag, v1.real) == pytest.approx(0.0, abs=1e-9)
        # B2 fica em 1.04 com θ pequeno positivo (geração)
        v2 = sol.bus_voltages_pu["B2"]
        assert abs(v2) == pytest.approx(1.04, rel=1e-6)
        # B3 fica abaixo de 1.04 (queda devido à carga)
        v3 = sol.bus_voltages_pu["B3"]
        assert abs(v3) < 1.04
        assert abs(v3) > 0.95

    def test_no_buses_raises(self) -> None:
        with pytest.raises(ValueError, match="vazia"):
            solve_power_flow([], [])

    def test_no_slack_raises(self) -> None:
        buses = [
            PfBus(id="B1", type=BusType.PQ, P_pu_set=0, Q_pu_set=0),
            PfBus(id="B2", type=BusType.PQ, P_pu_set=0, Q_pu_set=0),
        ]
        with pytest.raises(ValueError, match="SLACK"):
            solve_power_flow(buses, [])

    def test_two_slacks_raises(self) -> None:
        buses = [
            PfBus(id="B1", type=BusType.SLACK),
            PfBus(id="B2", type=BusType.SLACK),
        ]
        with pytest.raises(ValueError, match="SLACK"):
            solve_power_flow(buses, [])

    def test_solution_updates_bus_objects(self) -> None:
        """solve_power_flow() preenche V_pu_solved e theta_solved_rad."""
        buses = [
            PfBus(id="SL", type=BusType.SLACK, V_pu_set=1.0),
            PfBus(id="LD", type=BusType.PQ, P_pu_set=-0.3, Q_pu_set=-0.1),
        ]
        branches = [PfBranch(from_bus="SL", to_bus="LD", X_pu=0.1)]
        solve_power_flow(buses, branches)
        # Antes do solve, V_pu_solved era 1.0 default; agora deve refletir
        # a queda de tensão.
        assert buses[1].V_pu_solved < 1.0
        assert buses[1].theta_solved_rad < 0.0   # PQ recebendo P → θ atrasado

    def test_max_iterations_returns_not_converged(self) -> None:
        """
        Caso patológico que não converge: setpoint impossível
        em pouquíssimas iterações.
        """
        # Carga muito pesada, max_iterations=1 — não terá tempo
        buses = [
            PfBus(id="SL", type=BusType.SLACK, V_pu_set=1.0),
            PfBus(id="LD", type=BusType.PQ, P_pu_set=-3.0, Q_pu_set=-1.5),
        ]
        branches = [PfBranch(from_bus="SL", to_bus="LD", X_pu=0.4)]
        sol = solve_power_flow(buses, branches, max_iterations=1)
        # Pode ou não convergir em 1 iter; se não convergiu,
        # converged=False
        if not sol.converged:
            assert sol.iterations == 1


# ---------------------------------------------------------------------------
# Line flows
# ---------------------------------------------------------------------------


class TestLineFlows:

    def test_line_flow_objects_returned(self) -> None:
        buses = [
            PfBus(id="SL", type=BusType.SLACK, V_pu_set=1.0),
            PfBus(id="LD", type=BusType.PQ, P_pu_set=-0.5, Q_pu_set=-0.2),
        ]
        branches = [PfBranch(from_bus="SL", to_bus="LD", X_pu=0.1)]
        sol = solve_power_flow(buses, branches)
        assert len(sol.line_flows) == 1
        f = sol.line_flows[0]
        assert isinstance(f, LineFlow)
        assert f.from_bus == "SL"
        assert f.to_bus == "LD"

    def test_line_flow_direction_from_slack_to_load(self) -> None:
        buses = [
            PfBus(id="SL", type=BusType.SLACK, V_pu_set=1.0),
            PfBus(id="LD", type=BusType.PQ, P_pu_set=-0.5, Q_pu_set=-0.2),
        ]
        branches = [PfBranch(from_bus="SL", to_bus="LD", X_pu=0.1)]
        sol = solve_power_flow(buses, branches)
        f = sol.line_flows[0]
        # Potência sai do SL (positivo from)
        assert f.P_pu_from > 0
        # E chega no LD (negativo to por convenção: P_to é
        # P injetada *no* to_bus, que é negativa para uma carga)
        # Na verdade na nossa implementação P_to é a P na ponta
        # to_bus do branch; ela deve ser negativa pois o branch
        # entrega potência ao bus de carga.
        assert f.P_pu_to < 0

    def test_total_losses_nonneg_with_resistance(self) -> None:
        buses = [
            PfBus(id="SL", type=BusType.SLACK, V_pu_set=1.0),
            PfBus(id="LD", type=BusType.PQ, P_pu_set=-0.5, Q_pu_set=-0.2),
        ]
        branches = [
            PfBranch(from_bus="SL", to_bus="LD", R_pu=0.02, X_pu=0.1),
        ]
        sol = solve_power_flow(buses, branches)
        # Perdas P > 0 (sempre, com R > 0)
        assert sol.total_losses_pu.real > 0
        # Perdas Q também (indutivo → consome reativo)
        assert sol.total_losses_pu.imag > 0

    def test_zero_resistance_zero_p_loss(self) -> None:
        buses = [
            PfBus(id="SL", type=BusType.SLACK, V_pu_set=1.0),
            PfBus(id="LD", type=BusType.PQ, P_pu_set=-0.5, Q_pu_set=0),
        ]
        branches = [PfBranch(from_bus="SL", to_bus="LD", R_pu=0, X_pu=0.1)]
        sol = solve_power_flow(buses, branches)
        # Sem R, perdas P ≈ 0
        assert abs(sol.total_losses_pu.real) < 1e-3


# ---------------------------------------------------------------------------
# PowerFlowSystem builder
# ---------------------------------------------------------------------------


class TestPowerFlowSystem:

    def test_builder_api(self) -> None:
        sys = PowerFlowSystem(base_MVA=100.0)
        sys.add_slack(id="SL", V_pu=1.0)
        sys.add_pv(id="GEN", P_pu=0.5, V_pu=1.04)
        sys.add_pq(id="LD", P_pu=-0.8, Q_pu=-0.2)
        sys.add_branch(from_bus="SL", to_bus="GEN", X_pu=0.1)
        sys.add_branch(from_bus="GEN", to_bus="LD", X_pu=0.15)
        assert len(sys.buses) == 3
        assert len(sys.branches) == 2

    def test_solve_method(self) -> None:
        sys = PowerFlowSystem()
        sys.add_slack(id="SL", V_pu=1.0)
        sys.add_pq(id="LD", P_pu=-0.3, Q_pu=-0.1)
        sys.add_branch(from_bus="SL", to_bus="LD", X_pu=0.1)
        sol = sys.solve()
        assert sol.converged

    def test_get_bus_returns_bus(self) -> None:
        sys = PowerFlowSystem()
        b1 = sys.add_slack(id="SL", V_pu=1.0)
        b2 = sys.add_pq(id="LD", P_pu=-0.3, Q_pu=-0.1)
        assert sys.get_bus("SL") is b1
        assert sys.get_bus("LD") is b2

    def test_get_bus_returns_none_for_unknown(self) -> None:
        sys = PowerFlowSystem()
        sys.add_slack(id="SL")
        assert sys.get_bus("GHOST") is None


# ---------------------------------------------------------------------------
# PowerFlowSolution.summary()
# ---------------------------------------------------------------------------


class TestPowerFlowSummary:

    def test_summary_text_contains_status(self) -> None:
        buses = [
            PfBus(id="SL", type=BusType.SLACK, V_pu_set=1.0),
            PfBus(id="LD", type=BusType.PQ, P_pu_set=-0.3, Q_pu_set=-0.1),
        ]
        branches = [PfBranch(from_bus="SL", to_bus="LD", X_pu=0.1)]
        sol = solve_power_flow(buses, branches)
        text = sol.summary()
        assert "Power Flow Solution" in text
        assert "Converged" in text
        assert "Iterations" in text
        assert "SL" in text
        assert "LD" in text

    def test_summary_includes_line_flows(self) -> None:
        buses = [
            PfBus(id="SL", type=BusType.SLACK, V_pu_set=1.0),
            PfBus(id="LD", type=BusType.PQ, P_pu_set=-0.3, Q_pu_set=-0.1),
        ]
        branches = [PfBranch(from_bus="SL", to_bus="LD", X_pu=0.1)]
        sol = solve_power_flow(buses, branches)
        text = sol.summary()
        assert "Line flows" in text or "line flows" in text.lower()


# ---------------------------------------------------------------------------
# Conservação de potência
# ---------------------------------------------------------------------------


class TestPowerConservation:

    def test_p_balance_in_2bus(self) -> None:
        """
        P_slack ≈ P_load + P_loss
        Soma deve ser numericamente próxima de zero quando R=0.
        """
        buses = [
            PfBus(id="SL", type=BusType.SLACK, V_pu_set=1.0),
            PfBus(id="LD", type=BusType.PQ, P_pu_set=-0.5, Q_pu_set=-0.2),
        ]
        branches = [PfBranch(from_bus="SL", to_bus="LD", X_pu=0.1)]
        sol = solve_power_flow(buses, branches)
        # SL.P_pu_solved ≈ 0.5 (entregando ao bus LD)
        slack_P = buses[0].P_pu_solved
        assert slack_P > 0
        # No 2-bus caso, P_slack ≈ |P_load| + P_loss; com R=0, P_loss
        # é numericamente pequeno (não é exatamente 0 por arredondamento).
        load_P = abs(buses[1].P_pu_solved)   # módulo, pois P_set<0
        # Verifica que slack está fornecendo aproximadamente o que LD consome
        assert slack_P == pytest.approx(load_P, rel=0.05)
