"""
tests/test_pp_motor.py — v0.27.7.9: motores elétricos com
contribuição de SC conforme IEC 60909-0 §6.5 e NBR 17227 §4.2.2.

Cobre:

* MotorType enum (induction, synchronous).
* MotorParameters frozen dataclass + validação.
* Cálculos: rated_current, locked_rotor_current, base_impedance,
  subtransient_reactance/impedance, contribution_factor_at_time.
* motor_to_sc_source — geração de ScSource.
* emit_motor_metadata_lines — comentários ATP.
* Helpers: make_default_induction_motor,
  make_large_synchronous_motor.
* Bridge: MOTOR.ocomp → MotorParameters + metadata em /BRANCH.
* Integração: classify_sc_source recognizes MOTOR; multihop
  walker treats motor as ultimate source.
"""

from __future__ import annotations

import math

import pytest

from app.preprocessor.bridge_to_atp import _convert_motor, to_atp
from app.preprocessor.models import PpComponent, PpProject, PpProperty
from app.preprocessor.motor import (
    MotorParameters, MotorType,
    base_impedance_ohm,
    contribution_factor_at_time,
    emit_motor_metadata_lines,
    initial_sc_contribution_kA,
    locked_rotor_current_A,
    make_default_induction_motor,
    make_large_synchronous_motor,
    motor_to_sc_source,
    rated_apparent_power_kVA,
    rated_current_A,
    subtransient_impedance_ohm,
    subtransient_reactance_pu,
    validate_motor,
)


# ---------------------------------------------------------------------------
# MotorType
# ---------------------------------------------------------------------------


class TestMotorType:
    def test_induction_value(self):
        assert MotorType.INDUCTION.value == "induction"

    def test_synchronous_value(self):
        assert MotorType.SYNCHRONOUS.value == "synchronous"


# ---------------------------------------------------------------------------
# Cálculos básicos
# ---------------------------------------------------------------------------


class TestRatedQuantities:
    def test_rated_apparent_power(self):
        """S = P / (η · cosφ)."""
        m = make_default_induction_motor(
            "M", "A", "B", "C", voltage_kV=0.480, power_kW=100.0,
        )
        # S = 100 / (0.95 · 0.85) ≈ 123.84 kVA
        assert rated_apparent_power_kVA(m) == pytest.approx(123.84, abs=0.5)

    def test_rated_current(self):
        """I = S / (√3 · V)."""
        m = make_default_induction_motor(
            "M", "A", "B", "C", voltage_kV=0.480, power_kW=100.0,
        )
        # 123.84 / (√3 · 0.480) ≈ 149 A
        assert rated_current_A(m) == pytest.approx(149.0, abs=1.0)

    def test_locked_rotor_current(self):
        """I_LR = I_rM · I_LR_rel."""
        m = make_default_induction_motor(
            "M", "A", "B", "C", voltage_kV=0.480, power_kW=100.0,
            locked_rotor_pu=6.0,
        )
        # 149 · 6 = 894 A
        assert locked_rotor_current_A(m) == pytest.approx(894, abs=2)

    def test_base_impedance(self):
        """Z_base = V² / S."""
        m = make_default_induction_motor(
            "M", "A", "B", "C", voltage_kV=0.480, power_kW=100.0,
        )
        # 480² / 123840 ≈ 1.86 Ω
        assert base_impedance_ohm(m) == pytest.approx(1.86, abs=0.05)

    def test_zero_efficiency_rejected(self):
        m = MotorParameters(
            name="X", node_a="A", node_b="B", node_c="C",
            efficiency=0.0,
        )
        with pytest.raises(ValueError):
            rated_apparent_power_kVA(m)


# ---------------------------------------------------------------------------
# Reatância subtransitória
# ---------------------------------------------------------------------------


class TestSubtransient:
    def test_X_pu_is_inverse_of_locked_rotor_pu(self):
        """X''_M = 1 / I_LR_rel."""
        m = make_default_induction_motor(
            "M", "A", "B", "C",
            locked_rotor_pu=6.0,
        )
        assert subtransient_reactance_pu(m) == pytest.approx(1/6, abs=0.001)

    def test_subtransient_impedance_complex(self):
        m = make_default_induction_motor(
            "M", "A", "B", "C",
            voltage_kV=0.480, power_kW=100.0,
        )
        z = subtransient_impedance_ohm(m)
        # X imag > 0
        assert z.imag > 0
        # R real > 0 (starting_pf = 0.30)
        assert z.real > 0
        # X >> R (sentido físico)
        assert z.imag > z.real


# ---------------------------------------------------------------------------
# Decay temporal (NBR 17227 §4.2.2)
# ---------------------------------------------------------------------------


class TestContributionDecay:
    def test_decay_at_t0_is_1(self):
        m = make_default_induction_motor("M", "A", "B", "C")
        assert contribution_factor_at_time(m, 0.0) == 1.0

    def test_decay_exponential(self):
        m = make_default_induction_motor("M", "A", "B", "C")
        # τ = 20 ms → t = 20: f = e^-1 = 0.368
        f = contribution_factor_at_time(m, 20.0)
        assert f == pytest.approx(math.exp(-1.0), abs=0.001)

    def test_decay_3_cycles_im(self):
        """3 ciclos a 60 Hz = 50 ms; IM Td=20ms → f ≈ 0.082."""
        m = make_default_induction_motor("M", "A", "B", "C")
        f = contribution_factor_at_time(m, 50.0)
        assert f == pytest.approx(0.082, abs=0.005)

    def test_decay_8_cycles_im(self):
        """8 ciclos = ~133 ms; IM ≈ 0 (limite NBR 17227)."""
        m = make_default_induction_motor("M", "A", "B", "C")
        f = contribution_factor_at_time(m, 133.0)
        assert f < 0.005

    def test_decay_synchronous_persists_longer(self):
        """MS Td=200 ms → decay muito mais lento."""
        m = make_large_synchronous_motor("M", "A", "B", "C")
        # Em 50 ms, IM ≈ 0.082 mas MS ≈ 0.78
        f = contribution_factor_at_time(m, 50.0)
        assert f > 0.5

    def test_negative_time_rejected(self):
        m = make_default_induction_motor("M", "A", "B", "C")
        with pytest.raises(ValueError):
            contribution_factor_at_time(m, -1.0)


# ---------------------------------------------------------------------------
# Validador
# ---------------------------------------------------------------------------


class TestValidator:
    def test_default_im_valid(self):
        m = make_default_induction_motor("M", "A", "B", "C")
        assert validate_motor(m) == []

    def test_default_ms_valid(self):
        m = make_large_synchronous_motor("M", "A", "B", "C")
        assert validate_motor(m) == []

    def test_empty_name(self):
        m = MotorParameters(name="", node_a="A", node_b="B", node_c="C")
        errs = validate_motor(m)
        assert any("name vazio" in e for e in errs)

    def test_long_name(self):
        m = MotorParameters(
            name="ABCDEFGH", node_a="A", node_b="B", node_c="C",
        )
        errs = validate_motor(m)
        assert any("> 6 chars" in e for e in errs)

    def test_zero_voltage(self):
        m = MotorParameters(
            name="X", node_a="A", node_b="B", node_c="C",
            rated_voltage_kV=0.0,
        )
        errs = validate_motor(m)
        assert any("rated_voltage_kV" in e for e in errs)

    def test_pf_out_of_range(self):
        m = MotorParameters(
            name="X", node_a="A", node_b="B", node_c="C",
            rated_pf=1.5,
        )
        errs = validate_motor(m)
        assert any("rated_pf" in e for e in errs)

    def test_locked_rotor_too_low(self):
        m = MotorParameters(
            name="X", node_a="A", node_b="B", node_c="C",
            locked_rotor_current_pu=0.5,
        )
        errs = validate_motor(m)
        assert any("locked_rotor_current_pu" in e for e in errs)

    def test_locked_rotor_anormal(self):
        m = MotorParameters(
            name="X", node_a="A", node_b="B", node_c="C",
            locked_rotor_current_pu=20.0,
        )
        errs = validate_motor(m)
        assert any("anormal" in e for e in errs)

    def test_odd_n_poles(self):
        m = MotorParameters(
            name="X", node_a="A", node_b="B", node_c="C",
            n_poles=3,
        )
        errs = validate_motor(m)
        assert any("n_poles" in e for e in errs)


# ---------------------------------------------------------------------------
# motor_to_sc_source
# ---------------------------------------------------------------------------


class TestMotorToScSource:
    def test_basic(self):
        m = make_default_induction_motor(
            "M1", "A", "B", "C", voltage_kV=0.480, power_kW=100.0,
        )
        src = motor_to_sc_source(m)
        assert src.name == "M1"
        # Z não-trivial
        assert abs(src.z_ohm) > 0
        # Description menciona motor
        assert "Motor" in src.description

    def test_initial_sc_contribution_equals_locked_rotor_kA(self):
        m = make_default_induction_motor(
            "M", "A", "B", "C", voltage_kV=0.480, power_kW=100.0,
        )
        # I_LR ≈ 894 A → 0.894 kA
        assert initial_sc_contribution_kA(m) == pytest.approx(0.894, abs=0.005)


# ---------------------------------------------------------------------------
# Emit metadata
# ---------------------------------------------------------------------------


class TestEmitMetadata:
    def test_basic_emit(self):
        m = make_default_induction_motor("M1", "A", "B", "C")
        text = "\n".join(emit_motor_metadata_lines(m))
        assert "MOTOR: M1" in text
        assert "induction" in text
        assert "I_rM" in text
        assert "I_LR" in text

    def test_synchronous_in_text(self):
        m = make_large_synchronous_motor("M2", "A", "B", "C")
        text = "\n".join(emit_motor_metadata_lines(m))
        assert "synchronous" in text

    def test_invalid_raises(self):
        m = MotorParameters(
            name="", node_a="A", node_b="B", node_c="C",
        )
        with pytest.raises(ValueError):
            emit_motor_metadata_lines(m)


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------


def _mk_motor_comp(name: str, props: list[str]) -> PpComponent:
    return PpComponent(
        type="MOTOR", name=name, visible=True,
        x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(p) for p in props],
    )


_DEFAULT_PROPS = [
    "induction",  # type
    "0.480",      # V
    "100",        # P kW
    "0.85",       # PF
    "0.95",       # eff
    "6.0",        # locked rotor
    "0.30",       # start PF
    "4",          # poles
    "20",         # Td_pp
]


class TestBridgeMotor:
    def test_motor_emits_metadata(self):
        comp = _mk_motor_comp("M1", _DEFAULT_PROPS)
        atp = to_atp(PpProject(components=[comp]))
        text = "\n".join(atp.raw_lines)
        assert "MOTOR: M1" in text
        assert "induction" in text

    def test_invalid_motor_type_falls_back(self):
        bad = list(_DEFAULT_PROPS)
        bad[0] = "INVALID"
        comp = _mk_motor_comp("M1", bad)
        atp = to_atp(PpProject(components=[comp]))
        # Warning + fallback induction
        assert any("motor_type" in w.lower() for w in atp.warnings)

    def test_invalid_voltage_warned(self):
        bad = list(_DEFAULT_PROPS)
        bad[1] = "abc"
        comp = _mk_motor_comp("M1", bad)
        atp = to_atp(PpProject(components=[comp]))
        assert any("rated_voltage_kV" in w for w in atp.warnings)

    def test_helper_direct_call(self):
        from app.preprocessor.node_coalescer import coalesce_nodes
        from app.core.project_model import AtpProject, HeaderInfo
        comp = _mk_motor_comp("M1", _DEFAULT_PROPS)
        proj = PpProject(components=[comp])
        node_map = coalesce_nodes(proj)
        atp = AtpProject(file_path="", raw_lines=[],
                         header=HeaderInfo(raw_lines=[]))
        m = _convert_motor(comp, "M1", node_map, atp)
        assert m is not None
        assert m.motor_type == MotorType.INDUCTION
        assert m.rated_power_kW == 100.0


# ---------------------------------------------------------------------------
# Integração: classify_sc_source + multihop walker
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    def test_classify_motor(self):
        from app.postprocessor.bus_pipeline import classify_sc_source
        comp = _mk_motor_comp("M1", _DEFAULT_PROPS)
        assert classify_sc_source(comp) == "motor"

    def test_motor_in_sc_source_types(self):
        from app.postprocessor.bus_pipeline import SC_SOURCE_TYPES
        assert "MOTOR" in SC_SOURCE_TYPES
        assert SC_SOURCE_TYPES["MOTOR"] == "motor"

    def test_motor_is_ultimate_source_in_walker(self):
        from app.postprocessor.multihop_walker import is_ultimate_source
        comp = _mk_motor_comp("M1", _DEFAULT_PROPS)
        assert is_ultimate_source(comp) is True

    def test_extract_motor_source_via_pipeline(self):
        """Helper interno _extract_motor_source via build."""
        from app.postprocessor.bus_pipeline import (
            _extract_motor_source,
        )
        comp = _mk_motor_comp("M1", _DEFAULT_PROPS)
        warnings: list[str] = []
        src = _extract_motor_source(comp, warnings)
        assert src is not None
        assert warnings == []
        assert "Motor" in src.description


# ---------------------------------------------------------------------------
# Cenários realistas
# ---------------------------------------------------------------------------


class TestRealisticScenarios:
    def test_im_500hp_at_4kV(self):
        """IM grande 500 HP / 4.16 kV — contribuição típica 5 kA."""
        m = MotorParameters(
            name="MOT", node_a="A", node_b="B", node_c="C",
            rated_voltage_kV=4.16, rated_power_kW=370.0,  # 500 HP
            rated_pf=0.92, efficiency=0.95,
            locked_rotor_current_pu=6.0,
        )
        I_LR = locked_rotor_current_A(m)
        # I_n ≈ 56 A; I_LR ≈ 336 A
        assert 50 < rated_current_A(m) < 70
        assert 300 < I_LR < 400

    def test_im_decay_3_8_cycles_per_NBR_17227(self):
        """NBR 17227: IM contribui em 3-8 ciclos.

        Em 3 ciclos (50 ms), contribuição ainda significativa.
        Em 8 ciclos (133 ms), praticamente zero.
        """
        m = make_default_induction_motor("M", "A", "B", "C")
        f_3cycles = contribution_factor_at_time(m, 50.0)
        f_8cycles = contribution_factor_at_time(m, 133.0)
        # 3 ciclos: ainda detectável
        assert f_3cycles > 0.05
        # 8 ciclos: praticamente zero
        assert f_8cycles < 0.01
