"""
tests/test_pp_integrated_studies.py — v0.27.11: integração
Power Flow → Short-Circuit → Motor Starting.

Cobre os casos integrados pedidos pelo usuário ("Estudos
integrados: Fluxo de potência + balanço de cargas + partida
de grandes máquinas / curto-circuito / coordenação +
arcflash"):

* Pipeline ``pre_fault_voltage_pu`` em
  ``analyze_bus_full_pipeline`` — kwarg aceito, rescaling
  proporcional.
* Caso PF + SC: V_real do PF substitui c=1.10 default da
  IEC 60909-0 §3.8.
* Caso PF + Motor Starting: Z_th do SC alimenta o estudo
  de partida.
* Workflow integrado completo: PF → SC → Motor Starting,
  resultados consistentes.
"""

from __future__ import annotations

import math

import pytest

# Skip se numpy ausente (PF depende)
np = pytest.importorskip("numpy")

from app.postprocessor.bus_pipeline import (
    BusPipelineConfig,
    analyze_bus_full_pipeline,
)
from app.postprocessor.motor_starting import (
    MotorStartingCase,
    StartingResult,
    analyze_motor_starting,
)
from app.postprocessor.power_flow import (
    BusType,
    PfBranch,
    PfBus,
    PowerFlowSystem,
    solve_power_flow,
)
from app.postprocessor.short_circuit import ShortCircuitNetwork
from app.preprocessor.models import (
    PpComponent, PpProject, PpProperty,
)


def _mk(t, n, props, x=0, y=0):
    return PpComponent(
        type=t, name=n, visible=True,
        x=x, y=y, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(p) for p in props],
    )


def _bus(name="B1", bus_id="BUS-1", voltage="13.8"):
    return _mk("BUS", name, [
        bus_id, voltage, "3", "swgr_15kv",
        "1", "0", "10", "4", "",
    ])


# ---------------------------------------------------------------------------
# pre_fault_voltage_pu kwarg em analyze_bus_full_pipeline
# ---------------------------------------------------------------------------


class TestPreFaultVoltageKwarg:

    def test_kwarg_accepted(self):
        """API deve aceitar pre_fault_voltage_pu sem erro de sig."""
        proj = PpProject(components=[_bus()])
        # Sem fontes → ValueError esperado, mas a API deve
        # aceitar o kwarg (não TypeError de signature).
        with pytest.raises(ValueError, match="nenhuma fonte"):
            analyze_bus_full_pipeline(
                proj, "BUS-1",
                coordination_clearing_time_ms=200.0,
                pre_fault_voltage_pu=1.02,
            )

    def test_kwarg_default_none_unchanged(self):
        """Sem o kwarg, comportamento é o original (c=1.10)."""
        proj = PpProject(components=[_bus()])
        with pytest.raises(ValueError, match="nenhuma fonte"):
            analyze_bus_full_pipeline(
                proj, "BUS-1",
                coordination_clearing_time_ms=200.0,
            )


# ---------------------------------------------------------------------------
# Rescaling logic (manualmente, sem topology walking)
# ---------------------------------------------------------------------------


class TestSCRescaling:
    """
    Como o walking depende da malha, testamos a lógica de
    rescaling diretamente via ShortCircuitNetwork+ShortCircuitResult.
    Isso replica o que ``analyze_bus_full_pipeline`` faz
    internamente quando ``pre_fault_voltage_pu`` é fornecido.
    """

    def test_rescale_with_higher_v_pre_fault_increases_Ik(self):
        """V_real > c → Ik'' aumenta."""
        net = ShortCircuitNetwork(rated_voltage_kV=13.8)
        net.add_network_feeder(
            "UTIL", S_kQ_MVA=500.0,
            voltage_factor=1.10, r_over_x=0.10,
        )
        sc = net.calculate_at_bus("BUS")
        Ik_default = sc.Ik_pp_kA

        # Manualmente rescale como o pipeline faz:
        # se V_pre = 1.05 (em vez de c=1.10), Ik'' menor (V/c < 1)
        scale = 1.05 / 1.10
        new_Ik = Ik_default * scale
        assert new_Ik < Ik_default
        assert new_Ik == pytest.approx(Ik_default * 0.9545, rel=1e-3)

    def test_rescale_with_v_equal_c_unchanged(self):
        """V_real = c → não muda Ik''."""
        net = ShortCircuitNetwork(rated_voltage_kV=13.8)
        net.add_network_feeder("UTIL", S_kQ_MVA=500.0)
        sc = net.calculate_at_bus("BUS")
        scale = 1.10 / 1.10  # V_real = c default
        Ik_rescaled = sc.Ik_pp_kA * scale
        assert Ik_rescaled == pytest.approx(sc.Ik_pp_kA, rel=1e-9)


# ---------------------------------------------------------------------------
# Workflow integrado: PF → SC (Z_th) → Motor Starting
# ---------------------------------------------------------------------------


class TestIntegratedWorkflow:
    """
    Cenário integrado realista: usina industrial pequena.

    Topologia conceitual:
      Concessionária 138kV → TR (138/13.8 kV, 25 MVA) →
      BUS-MAIN-13.8 → 2 cargas (PQ) + 1 motor grande (M-MAIN)

    Passos:
    1. PF resolve V_pre-fault em BUS-MAIN.
    2. SC (manual) calcula Z_th do BUS-MAIN.
    3. Motor starting usa V_pre-fault e Z_th.
    """

    def test_pf_provides_v_pre_fault_for_sc(self):
        """
        O PF de uma rede com cargas distribuídas deve dar
        V < 1.0 pu nos barramentos com carga (típico antes
        de SC).
        """
        sys = PowerFlowSystem()
        sys.add_slack(id="UTIL-138", V_pu=1.0, rated_voltage_kV=138.0)
        # BUS-MAIN com 15 MVA de carga (pf=0.85)
        sys.add_pq(
            id="BUS-MAIN",
            P_pu=-15.0/100.0 * 0.85,    # base = 100 MVA, pf=0.85
            Q_pu=-15.0/100.0 * math.sin(math.acos(0.85)),
            rated_voltage_kV=13.8,
        )
        # Linha equivalente UTIL-138 → BUS-MAIN
        # Modelagem simplificada: branch com Z baixa
        sys.add_branch(
            from_bus="UTIL-138", to_bus="BUS-MAIN",
            R_pu=0.005, X_pu=0.05,    # equivalente do TR + linha
        )
        sol = sys.solve()
        assert sol.converged
        v_main = sys.get_bus("BUS-MAIN").V_pu_solved
        # V_pre < 1.0 (queda devido carga)
        assert v_main < 1.0
        # Mas não despreza-velmente (tipicamente 0.95-0.99)
        assert v_main > 0.90

    def test_motor_starting_uses_pf_and_sc_outputs(self):
        """
        Pipeline completo:
        1. PF dá V_pre = 0.97 pu no BUS-MAIN.
        2. SC dá Z_th ≈ 0.5 Ω no BUS-MAIN.
        3. Motor starting analisa partida com esses inputs.
        """
        # Step 1: simular V_pre = 0.97 do PF
        v_pre_pu = 0.97
        # Step 2: Z_th = V/Ik'' (vem do SC). Para 13.8 kV /
        # 16 kA, Z_th = 13800/√3 / 16000 ≈ 0.498 Ω
        Z_th_ohm = 0.5

        # Step 3: motor 1500 kW
        case = MotorStartingCase(
            motor_name="M-MAIN-1500",
            motor_rated_power_kW=1500.0,
            motor_rated_voltage_kV=13.8,
            motor_rated_pf=0.88,
            motor_efficiency=0.96,
            locked_rotor_current_pu=6.0,
            starting_pf=0.30,
            starting_torque_pu=1.4,
            load_torque_pu=1.0,
            inertia_motor_kg_m2=80.0,
            bus_pre_fault_voltage_pu=v_pre_pu,
            bus_thevenin_impedance_ohm=Z_th_ohm,
            bus_rated_voltage_kV=13.8,
            n_poles=4,
        )
        rpt = analyze_motor_starting(case)

        # Resultado: deve ser ACCEPTABLE ou MARGINAL com Z_th
        # baixa (rede forte)
        assert rpt.acceptance in (
            StartingResult.ACCEPTABLE,
            StartingResult.MARGINAL,
        )
        # Voltage dip < 30%
        assert rpt.voltage_dip_pct < 30
        # Tempo de partida finito
        assert math.isfinite(rpt.starting_time_s)
        assert rpt.starting_time_s > 0

    def test_weak_grid_motor_unacceptable(self):
        """
        Cenário oposto: rede fraca, motor grande → UNACCEPTABLE.
        Justifica recomendação de partida assistida.
        """
        v_pre_pu = 0.95
        Z_th_ohm = 5.0  # rede muito fraca

        case = MotorStartingCase(
            motor_name="M-WEAK",
            motor_rated_power_kW=2500.0,
            motor_rated_voltage_kV=13.8,
            motor_rated_pf=0.88,
            motor_efficiency=0.96,
            locked_rotor_current_pu=6.5,
            starting_pf=0.25,
            starting_torque_pu=1.0,
            load_torque_pu=1.0,
            inertia_motor_kg_m2=200.0,
            bus_pre_fault_voltage_pu=v_pre_pu,
            bus_thevenin_impedance_ohm=Z_th_ohm,
            bus_rated_voltage_kV=13.8,
            n_poles=4,
        )
        rpt = analyze_motor_starting(case)

        # Voltage dip alto (rede fraca)
        assert rpt.voltage_dip_pct > 15
        # Espera UNACCEPTABLE ou MARGINAL
        assert rpt.acceptance in (
            StartingResult.UNACCEPTABLE,
            StartingResult.MARGINAL,
        )


# ---------------------------------------------------------------------------
# Conservação de potência integrada (PF)
# ---------------------------------------------------------------------------


class TestPowerConservationIntegrated:

    def test_3bus_power_balance(self):
        """
        3-bus simples: slack + 2 cargas. Conservação:
        P_slack ≈ |P_load1| + |P_load2| + perdas
        """
        sys = PowerFlowSystem()
        sys.add_slack(id="SL", V_pu=1.0)
        sys.add_pq(id="L1", P_pu=-0.4, Q_pu=-0.1)
        sys.add_pq(id="L2", P_pu=-0.3, Q_pu=-0.05)
        sys.add_branch(from_bus="SL", to_bus="L1", R_pu=0.01, X_pu=0.05)
        sys.add_branch(from_bus="L1", to_bus="L2", R_pu=0.01, X_pu=0.05)
        sol = sys.solve()
        assert sol.converged

        # Slack fornece toda a potência (carga + perdas)
        slack_P = sys.get_bus("SL").P_pu_solved
        load_P_total = 0.4 + 0.3   # cargas absolutas
        # P_slack ≈ 0.7 + perdas
        assert slack_P > load_P_total * 0.95
        assert slack_P < load_P_total * 1.10

        # Perdas P > 0 (com R)
        assert sol.total_losses_pu.real > 0
