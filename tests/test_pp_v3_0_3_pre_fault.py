"""
tests/test_pp_v3_0_3_pre_fault.py — v3.0.3 Sprint B.3.

Pre-Fault Voltage tolerance handling — PTW Tutorial §Part 5 p. 131-135
(Pre-Fault Voltage options + Utility/Cable/TX Tolerance Min/Reg/Max).

Cobre:
* `PreFaultMode` enum — 4 modos: LOAD_FLOW, PU_ALL, PU_PER_BUS, NO_LOAD_WITH_TAP
* `VoltageTolerance` dataclass — min/regular/max para Utility/Cable/TX
* `voltage_with_tolerance()` — aplica tolerâncias conforme modo
* `pre_fault_voltage_pu()` — retorna voltagem pré-falta efetiva

Anti-alucinação: cita PTW Tutorial §Part 5 p. 131-135 + A_Fault §1.3.3 p. 1-10.
Anti-simplismo: cobre 4 modos PreFault + tolerâncias multi-equipamento.

Reference: PTW Tutorial PDF §Part 5 p. 131-135; A_Fault §1.3.3 p. 1-10.
"""

from __future__ import annotations

import pytest


# ===========================================================================
# Sprint B.3.A — PreFaultMode enum
# ===========================================================================


class TestPreFaultMode:

    def test_four_modes_exist(self):
        """§Tutorial Part 5 p. 131-132: 4 modos pre-fault voltage."""
        from app.postprocessor.pre_fault_voltage import PreFaultMode
        assert {m.value for m in PreFaultMode} == {
            "load_flow", "pu_all", "pu_per_bus", "no_load_with_tap"
        }

    def test_default_is_pu_all_at_unity(self):
        """A_Fault §1.3.3 p. 1-10 linha 558: default Pre-Fault V = 1.0 pu."""
        from app.postprocessor.pre_fault_voltage import (
            PreFaultMode, DEFAULT_PRE_FAULT_MODE,
        )
        assert DEFAULT_PRE_FAULT_MODE == PreFaultMode.PU_ALL


# ===========================================================================
# Sprint B.3.B — VoltageTolerance dataclass
# ===========================================================================


class TestVoltageTolerance:

    def test_construction_with_three_values(self):
        """§Tutorial Part 5 p. 131-135: tolerâncias min/reg/max por equipamento."""
        from app.postprocessor.pre_fault_voltage import VoltageTolerance
        t = VoltageTolerance(min_pu=0.95, regular_pu=1.00, max_pu=1.05)
        assert t.min_pu == 0.95
        assert t.regular_pu == 1.00
        assert t.max_pu == 1.05

    def test_invalid_ordering_raises(self):
        """min ≤ regular ≤ max é invariante físico."""
        from app.postprocessor.pre_fault_voltage import VoltageTolerance
        with pytest.raises(ValueError):
            VoltageTolerance(min_pu=1.10, regular_pu=1.00, max_pu=1.05)
        with pytest.raises(ValueError):
            VoltageTolerance(min_pu=0.95, regular_pu=1.10, max_pu=1.05)

    def test_negative_voltage_raises(self):
        """Voltagem negativa não tem sentido físico."""
        from app.postprocessor.pre_fault_voltage import VoltageTolerance
        with pytest.raises(ValueError):
            VoltageTolerance(min_pu=-0.5, regular_pu=1.00, max_pu=1.05)

    def test_default_ansi_tolerance(self):
        """Tolerância padrão ANSI: ±5% (NEMA + IEEE 141)."""
        from app.postprocessor.pre_fault_voltage import DEFAULT_ANSI_TOLERANCE
        assert DEFAULT_ANSI_TOLERANCE.min_pu == 0.95
        assert DEFAULT_ANSI_TOLERANCE.regular_pu == 1.00
        assert DEFAULT_ANSI_TOLERANCE.max_pu == 1.05


# ===========================================================================
# Sprint B.3.C — voltage_with_tolerance() dispatcher
# ===========================================================================


class TestVoltageWithTolerance:

    def test_pu_all_returns_regular_voltage(self):
        """PU_ALL mode: aplica tolerância 'regular' (PTW default)."""
        from app.postprocessor.pre_fault_voltage import (
            PreFaultMode, VoltageTolerance, voltage_with_tolerance,
        )
        tol = VoltageTolerance(min_pu=0.95, regular_pu=1.00, max_pu=1.05)
        v = voltage_with_tolerance(
            nominal_pu=1.00, tolerance=tol, mode=PreFaultMode.PU_ALL,
        )
        assert v == 1.00

    def test_no_load_with_tap_uses_max(self):
        """NO_LOAD_WITH_TAP mode: pior caso = tolerância max (mais conservador)."""
        from app.postprocessor.pre_fault_voltage import (
            PreFaultMode, VoltageTolerance, voltage_with_tolerance,
        )
        tol = VoltageTolerance(min_pu=0.95, regular_pu=1.00, max_pu=1.05)
        v = voltage_with_tolerance(
            nominal_pu=1.00, tolerance=tol, mode=PreFaultMode.NO_LOAD_WITH_TAP,
        )
        assert v == 1.05

    def test_pu_per_bus_with_explicit_voltage_uses_it(self):
        """PU_PER_BUS mode + bus_voltage explícito: usa o valor dado."""
        from app.postprocessor.pre_fault_voltage import (
            PreFaultMode, VoltageTolerance, voltage_with_tolerance,
        )
        tol = VoltageTolerance(min_pu=0.95, regular_pu=1.00, max_pu=1.05)
        v = voltage_with_tolerance(
            nominal_pu=1.00, tolerance=tol, mode=PreFaultMode.PU_PER_BUS,
            bus_voltage_pu=1.025,
        )
        assert v == 1.025

    def test_load_flow_mode_requires_lf_result(self):
        """LOAD_FLOW mode requer resultado de Load Flow (LF result)."""
        from app.postprocessor.pre_fault_voltage import (
            PreFaultMode, VoltageTolerance, voltage_with_tolerance,
        )
        tol = VoltageTolerance(min_pu=0.95, regular_pu=1.00, max_pu=1.05)
        # Sem lf_voltage_pu → erro
        with pytest.raises(ValueError):
            voltage_with_tolerance(
                nominal_pu=1.00, tolerance=tol, mode=PreFaultMode.LOAD_FLOW,
            )
        # Com lf_voltage_pu → ok
        v = voltage_with_tolerance(
            nominal_pu=1.00, tolerance=tol, mode=PreFaultMode.LOAD_FLOW,
            lf_voltage_pu=0.98,
        )
        assert v == 0.98

    def test_min_max_voltage_clamping(self):
        """Para min/max scenarios, valores estão dentro da tolerância."""
        from app.postprocessor.pre_fault_voltage import (
            PreFaultMode, VoltageTolerance, voltage_with_tolerance,
        )
        tol = VoltageTolerance(min_pu=0.95, regular_pu=1.00, max_pu=1.05)
        # Worst-case high (NO_LOAD_WITH_TAP) = max
        v_high = voltage_with_tolerance(
            nominal_pu=1.00, tolerance=tol, mode=PreFaultMode.NO_LOAD_WITH_TAP,
        )
        assert v_high == 1.05


# ===========================================================================
# Sprint B.3.D — Per-equipment tolerance scenarios (Util / Cable / TX)
# ===========================================================================


class TestEquipmentTolerances:

    def test_utility_tolerance_default_values(self):
        """Default Utility tolerance: ±5% (típico ANSI)."""
        from app.postprocessor.pre_fault_voltage import (
            DEFAULT_UTILITY_TOLERANCE,
        )
        assert DEFAULT_UTILITY_TOLERANCE.min_pu == 0.95
        assert DEFAULT_UTILITY_TOLERANCE.max_pu == 1.05

    def test_cable_tolerance_default_values(self):
        """Default Cable tolerance: muito apertada (±0% pré-falta, ABNT)."""
        from app.postprocessor.pre_fault_voltage import (
            DEFAULT_CABLE_TOLERANCE,
        )
        # Cable é passive — tolerância 0% é canônica (não muda V)
        assert DEFAULT_CABLE_TOLERANCE.min_pu == 1.00
        assert DEFAULT_CABLE_TOLERANCE.max_pu == 1.00

    def test_transformer_tolerance_default_values(self):
        """Default TX tolerance: ±2.5% (taps típicos)."""
        from app.postprocessor.pre_fault_voltage import (
            DEFAULT_TRANSFORMER_TOLERANCE,
        )
        assert DEFAULT_TRANSFORMER_TOLERANCE.min_pu == pytest.approx(0.975)
        assert DEFAULT_TRANSFORMER_TOLERANCE.max_pu == pytest.approx(1.025)

    def test_combined_worst_case_max_voltage(self):
        """
        Cenário pior-caso ALTO: combinar Util.max × TX.max × Cable.max.
        Conservativo para arc-flash incident energy.
        """
        from app.postprocessor.pre_fault_voltage import (
            combined_worst_case_voltage,
            DEFAULT_UTILITY_TOLERANCE,
            DEFAULT_TRANSFORMER_TOLERANCE,
            DEFAULT_CABLE_TOLERANCE,
        )
        v = combined_worst_case_voltage(
            utility_tolerance=DEFAULT_UTILITY_TOLERANCE,
            transformer_tolerance=DEFAULT_TRANSFORMER_TOLERANCE,
            cable_tolerance=DEFAULT_CABLE_TOLERANCE,
            scenario="max",
        )
        # 1.05 × 1.025 × 1.00 = 1.07625
        assert v == pytest.approx(1.05 * 1.025 * 1.00, rel=1e-9)

    def test_combined_worst_case_min_voltage(self):
        """Cenário pior-caso BAIXO: combinar tolerâncias min."""
        from app.postprocessor.pre_fault_voltage import (
            combined_worst_case_voltage,
            DEFAULT_UTILITY_TOLERANCE,
            DEFAULT_TRANSFORMER_TOLERANCE,
            DEFAULT_CABLE_TOLERANCE,
        )
        v = combined_worst_case_voltage(
            utility_tolerance=DEFAULT_UTILITY_TOLERANCE,
            transformer_tolerance=DEFAULT_TRANSFORMER_TOLERANCE,
            cable_tolerance=DEFAULT_CABLE_TOLERANCE,
            scenario="min",
        )
        # 0.95 × 0.975 × 1.00 = 0.92625
        assert v == pytest.approx(0.95 * 0.975 * 1.00, rel=1e-9)
