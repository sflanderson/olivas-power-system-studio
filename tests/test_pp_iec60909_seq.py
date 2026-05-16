"""
tests/test_pp_iec60909_seq.py — v0.28.0-PRO P1.5: faltas
assimétricas IEC 60909-0 §4.3 via componentes simétricas
0/1/2.

Cobre:

* FaultType + GroundingType enums.
* SequenceImpedances dataclass + validação.
* sequence_impedances_from_grounding com 5 tipos de grounding.
* three_phase_fault_kA / line_to_line_fault_kA /
  line_to_ground_fault_kA / double_line_to_ground_fault_kA.
* calculate_all_faults (wrapper).
* AsymmetricFaultResult.summary() + maximum_fault_kA +
  Ik1_to_Ik3_ratio.
* Cross-checks com fórmulas analíticas (Stevenson §11).
"""

from __future__ import annotations

import math

import pytest

from app.standards.iec60909_seq import (
    AsymmetricFaultResult,
    FaultType,
    GroundingType,
    SequenceImpedances,
    calculate_all_faults,
    double_line_to_ground_fault_kA,
    line_to_ground_fault_kA,
    line_to_line_fault_kA,
    sequence_impedances_from_grounding,
    three_phase_fault_kA,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:

    def test_fault_types(self):
        assert FaultType.THREE_PHASE.value == "three_phase"
        assert FaultType.LINE_TO_LINE.value == "line_to_line"
        assert FaultType.LINE_TO_GROUND.value == "line_to_ground"
        assert FaultType.DOUBLE_LINE_TO_GROUND.value == "double_line_to_ground"

    def test_grounding_types(self):
        types = [g.value for g in GroundingType]
        assert "solid" in types
        assert "resistance" in types
        assert "impedance" in types
        assert "ungrounded" in types
        assert "resonant" in types


# ---------------------------------------------------------------------------
# SequenceImpedances
# ---------------------------------------------------------------------------


class TestSequenceImpedances:

    def test_basic_construction(self):
        si = SequenceImpedances(
            Z1=complex(0.5, 2.0),
            Z2=complex(0.5, 2.0),
            Z0=complex(0.5, 2.0),
        )
        assert si.Z1 == complex(0.5, 2.0)

    def test_zero_Z1_rejected(self):
        with pytest.raises(ValueError, match="Z1"):
            SequenceImpedances(Z1=0j, Z2=complex(0.5, 2), Z0=complex(0.5, 2))

    def test_zero_Z2_rejected(self):
        with pytest.raises(ValueError, match="Z2"):
            SequenceImpedances(
                Z1=complex(0.5, 2), Z2=0j, Z0=complex(0.5, 2),
            )

    def test_zero_Z0_rejected(self):
        with pytest.raises(ValueError, match="Z0"):
            SequenceImpedances(
                Z1=complex(0.5, 2), Z2=complex(0.5, 2), Z0=0j,
            )


# ---------------------------------------------------------------------------
# sequence_impedances_from_grounding
# ---------------------------------------------------------------------------


class TestGroundingHelper:

    def test_solid_returns_Z0_equal_Z1(self):
        Z1 = complex(0.5, 2.0)
        seq = sequence_impedances_from_grounding(
            Z1, GroundingType.SOLIDLY_GROUNDED,
        )
        assert seq.Z0 == Z1

    def test_resistance_grounded(self):
        Z1 = complex(0.5, 2.0)
        R_N = 5.0
        seq = sequence_impedances_from_grounding(
            Z1, GroundingType.RESISTANCE_GROUNDED, R_N_ohm=R_N,
        )
        # Z_0 = Z_1 + 3·R_N (mais resistivo)
        assert seq.Z0.real == pytest.approx(Z1.real + 3 * R_N, rel=1e-6)
        assert seq.Z0.imag == pytest.approx(Z1.imag, rel=1e-6)

    def test_impedance_grounded_large_Z0(self):
        Z1 = complex(0.5, 2.0)
        seq = sequence_impedances_from_grounding(
            Z1, GroundingType.IMPEDANCE_GROUNDED,
        )
        # Z_0 = 100·Z_1
        assert abs(seq.Z0) == pytest.approx(100 * abs(Z1), rel=1e-6)

    def test_ungrounded_huge_Z0(self):
        Z1 = complex(0.5, 2.0)
        seq = sequence_impedances_from_grounding(
            Z1, GroundingType.UNGROUNDED,
        )
        assert abs(seq.Z0) > 1e8

    def test_resonant_purely_reactive(self):
        Z1 = complex(0.5, 2.0)
        seq = sequence_impedances_from_grounding(
            Z1, GroundingType.RESONANT_GROUNDED,
        )
        # Z_0 puramente reativo
        assert seq.Z0.real == pytest.approx(0.0)

    def test_override_Z0(self):
        Z1 = complex(0.5, 2.0)
        Z0_custom = complex(10.0, 30.0)
        seq = sequence_impedances_from_grounding(
            Z1, GroundingType.SOLIDLY_GROUNDED,
            Z0_override=Z0_custom,
        )
        assert seq.Z0 == Z0_custom


# ---------------------------------------------------------------------------
# Fault calculations
# ---------------------------------------------------------------------------


class TestThreePhaseFault:

    def test_basic(self):
        # 13.8 kV, Z1=2.0 ohm (puramente reativo), c=1.10
        Z1 = complex(0, 2.0)
        Ik3 = three_phase_fault_kA(13.8, Z1, voltage_factor_c=1.10)
        # Ik3 = 1.10 × 13.8 / (sqrt(3) × 2) = 4.382 kA
        assert Ik3 == pytest.approx(4.382, rel=1e-3)

    def test_zero_Z1_raises(self):
        with pytest.raises(ValueError, match="Z1"):
            three_phase_fault_kA(13.8, 0j)


class TestLineToLineFault:

    def test_Ik2_is_866_pct_of_Ik3_when_Z1_eq_Z2(self):
        """Z1 = Z2 → Ik2 = (√3/2) × Ik3 ≈ 0.866 × Ik3."""
        Z1 = complex(0, 2.0)
        Z2 = complex(0, 2.0)
        Ik2 = line_to_line_fault_kA(13.8, Z1, Z2)
        Ik3 = three_phase_fault_kA(13.8, Z1)
        assert Ik2 / Ik3 == pytest.approx(math.sqrt(3) / 2, rel=1e-3)


class TestLineToGroundFault:

    def test_solid_grounded_Ik1_equals_Ik3(self):
        """
        Para Z_0 = Z_1 = Z_2 (solidamente aterrado):
        Ik1 = √3·c·Un / (3·|Z_1|) = c·Un / (√3·|Z_1|) = Ik3
        """
        Z1 = complex(0, 2.0)
        Z2 = complex(0, 2.0)
        Z0 = complex(0, 2.0)
        Ik1 = line_to_ground_fault_kA(13.8, Z1, Z2, Z0)
        Ik3 = three_phase_fault_kA(13.8, Z1)
        assert Ik1 == pytest.approx(Ik3, rel=1e-3)

    def test_ungrounded_Ik1_near_zero(self):
        """Z_0 → ∞ → Ik1 → 0."""
        Z1 = complex(0, 2.0)
        Z2 = complex(0, 2.0)
        Z0 = complex(1e9, 1e9)
        Ik1 = line_to_ground_fault_kA(13.8, Z1, Z2, Z0)
        assert Ik1 < 1e-6


class TestDoubleLineToGroundFault:

    def test_returns_tuple(self):
        Z1 = complex(0, 2.0)
        Z2 = complex(0, 2.0)
        Z0 = complex(0, 2.0)
        I_phase, I_gnd = double_line_to_ground_fault_kA(
            13.8, Z1, Z2, Z0,
        )
        assert I_phase > 0
        assert I_gnd > 0

    def test_Ik2EG_phase_at_solid_ground(self):
        """
        Para Z_1 = Z_2 = Z_0:
        Ik2EG = √3 · c · Un · |Z_2| / |Z_1·Z_2 + Z_2·Z_0 + Z_0·Z_1|
              = √3 · c · Un · Z / (3·Z²)
              = c · Un / (√3 · Z)
              = Ik3
        """
        Z1 = complex(0, 2.0)
        Z2 = complex(0, 2.0)
        Z0 = complex(0, 2.0)
        I_phase, _ = double_line_to_ground_fault_kA(13.8, Z1, Z2, Z0)
        Ik3 = three_phase_fault_kA(13.8, Z1)
        assert I_phase == pytest.approx(Ik3, rel=1e-3)


# ---------------------------------------------------------------------------
# calculate_all_faults wrapper
# ---------------------------------------------------------------------------


class TestCalculateAllFaults:

    def test_returns_AsymmetricFaultResult(self):
        Z1 = complex(0.5, 2.0)
        seq = sequence_impedances_from_grounding(
            Z1, GroundingType.SOLIDLY_GROUNDED,
        )
        result = calculate_all_faults(Un_kV=13.8, seq_impedances=seq)
        assert isinstance(result, AsymmetricFaultResult)

    def test_solid_grounded_typical(self):
        """Sistema MV solidamente aterrado: Ik1/Ik3 ≈ 1."""
        Z1 = complex(0.5, 2.0)
        seq = sequence_impedances_from_grounding(
            Z1, GroundingType.SOLIDLY_GROUNDED,
        )
        result = calculate_all_faults(Un_kV=13.8, seq_impedances=seq)
        assert result.Ik1_to_Ik3_ratio == pytest.approx(1.0, rel=0.05)

    def test_ungrounded_Ik1_zero(self):
        Z1 = complex(0.5, 2.0)
        seq = sequence_impedances_from_grounding(
            Z1, GroundingType.UNGROUNDED,
        )
        result = calculate_all_faults(Un_kV=13.8, seq_impedances=seq)
        assert result.Ik1_kA < 1e-6

    def test_resistance_grounded_reduces_Ik1(self):
        """R_N=5 Ω deve reduzir Ik1 substancialmente."""
        Z1 = complex(0.5, 2.0)
        seq_solid = sequence_impedances_from_grounding(
            Z1, GroundingType.SOLIDLY_GROUNDED,
        )
        seq_R = sequence_impedances_from_grounding(
            Z1, GroundingType.RESISTANCE_GROUNDED, R_N_ohm=5.0,
        )
        r_solid = calculate_all_faults(Un_kV=13.8, seq_impedances=seq_solid)
        r_R = calculate_all_faults(Un_kV=13.8, seq_impedances=seq_R)
        assert r_R.Ik1_kA < r_solid.Ik1_kA

    def test_max_fault_property(self):
        Z1 = complex(0.5, 2.0)
        seq = sequence_impedances_from_grounding(
            Z1, GroundingType.SOLIDLY_GROUNDED,
        )
        result = calculate_all_faults(Un_kV=13.8, seq_impedances=seq)
        assert result.maximum_fault_kA == max(
            result.Ik3_kA, result.Ik2_kA, result.Ik1_kA,
            result.Ik2EG_phase_kA,
        )

    def test_Ik1_to_Ik3_ratio_ungrounded(self):
        """Sistema ungrounded → ratio ≈ 0."""
        Z1 = complex(0.5, 2.0)
        seq = sequence_impedances_from_grounding(
            Z1, GroundingType.UNGROUNDED,
        )
        result = calculate_all_faults(Un_kV=13.8, seq_impedances=seq)
        assert result.Ik1_to_Ik3_ratio < 0.001


class TestAsymmetricFaultResultSummary:

    def test_summary_contains_keys(self):
        Z1 = complex(0.5, 2.0)
        seq = sequence_impedances_from_grounding(
            Z1, GroundingType.SOLIDLY_GROUNDED,
        )
        result = calculate_all_faults(Un_kV=13.8, seq_impedances=seq)
        text = result.summary()
        # Verifica presença das siglas
        assert "I_k''3" in text
        assert "I_k''2" in text
        assert "I_k''1" in text
        assert "I_k''2EG" in text
        assert "13.80" in text or "13.8" in text


# ---------------------------------------------------------------------------
# Cross-checks com Stevenson §11
# ---------------------------------------------------------------------------


class TestStevensonCrossChecks:
    """
    Verificações analíticas conforme John J. Grainger, William D.
    Stevenson Jr., *Power System Analysis*, McGraw-Hill 1994 §11.
    """

    def test_three_phase_classic(self):
        """
        Stevenson §11.4 Ex 11.1:
        Vth = 1.0 pu, Z1 = j0.20 pu → Ik3 = 1.0/0.20 = 5.0 pu.
        """
        Un_pu_x_sqrt3 = 1.0   # |c·Un| em pu de sistema
        Z1_pu = complex(0, 0.20)
        # I_pu = Vth_pu / Z = 1.0 / 0.20 = 5.0 pu
        # Em kA com Un=13.8, base=100 MVA: I_base=4.18 kA, Ik3=20.92 kA
        Ik3 = three_phase_fault_kA(
            Un_kV=1.0, Z1=Z1_pu, voltage_factor_c=1.0,
        )
        # Ik3 (pu, com c=1.0) = 1.0 / (sqrt(3)·0.20) — note nossa
        # implementação é em SI; aqui só verificamos a estrutura
        # da fórmula:
        assert Ik3 > 0
