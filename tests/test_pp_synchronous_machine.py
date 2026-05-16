"""
tests/test_pp_synchronous_machine.py — v0.27.0: máquina síncrona
ATP MACHINE-59/58.

Cobre:

* Conversões base: Z_base, n_s rpm, omega_s, operational
  parameters (Tdo', Tdo'').
* Validador: hierarquia Xd > Xd' > Xd'' > xL, q-axis tipo
  58 vs 59, ratings, n_poles par, time constants positivas.
* Curto-circuito 3φ simétrico — I'' / I' / Iss e decaimento
  exponencial (com valores reais para um gerador típico).
* Emissão MACHINE-59 e MACHINE-58 (cartão e comentários "C ").
* Helpers ``make_default_hydro_generator`` / ``make_default_
  thermal_generator`` (templates típicos).
* Bridge SM.ocomp → cards injetados antes de /SOURCE.
"""

from __future__ import annotations

import math

import pytest

from app.preprocessor.bridge_to_atp import (
    _convert_synchronous_machine, to_atp,
)
from app.preprocessor.models import PpComponent, PpProject, PpProperty
from app.preprocessor.synchronous_machine import (
    SynchronousMachineParameters,
    base_impedance_ohm,
    emit_sm_cards, emit_sm_text,
    make_default_hydro_generator,
    make_default_thermal_generator,
    operational_parameters,
    short_circuit_currents,
    synchronous_speed_rpm,
    validate_sm,
)


# ---------------------------------------------------------------------------
# Conversões base
# ---------------------------------------------------------------------------


class TestBaseConversions:
    def test_z_base_typical(self):
        """Z_base de 13.8 kV / 100 MVA = 1.9044 Ω."""
        z = base_impedance_ohm(13.8, 100.0)
        assert z == pytest.approx(1.9044, abs=0.001)

    def test_z_base_500mva(self):
        """Z_base de 500 kV / 1000 MVA."""
        z = base_impedance_ohm(500.0, 1000.0)
        assert z == pytest.approx(250.0, abs=0.1)

    def test_z_base_zero_rejected(self):
        with pytest.raises(ValueError):
            base_impedance_ohm(0.0, 100.0)
        with pytest.raises(ValueError):
            base_impedance_ohm(13.8, 0.0)

    def test_synchronous_speed_2pole(self):
        """60 Hz, 2 polos = 3600 rpm."""
        assert synchronous_speed_rpm(60.0, 2) == pytest.approx(3600.0)

    def test_synchronous_speed_4pole(self):
        """60 Hz, 4 polos = 1800 rpm."""
        assert synchronous_speed_rpm(60.0, 4) == pytest.approx(1800.0)


class TestOperationalParameters:
    def test_open_circuit_time_const_d(self):
        """Tdo' = Td' · Xd / Xd' = 0.8 · 1.8 / 0.3 = 4.8 s."""
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        op = operational_parameters(p)
        assert op["Tdo_prime"] == pytest.approx(4.8, abs=0.01)

    def test_subtransient_open_circuit_time(self):
        """Tdo'' = Td'' · Xd' / Xd'' = 0.030 · 0.3 / 0.2 = 0.045 s."""
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        op = operational_parameters(p)
        assert op["Tdo_pp"] == pytest.approx(0.045, abs=0.001)

    def test_type_59_detected(self):
        """Xq' > 0 ⇒ tipo 59."""
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        op = operational_parameters(p)
        assert op["is_type_59"] is True

    def test_type_58_detected(self):
        """Xq' = 0 ⇒ tipo 58 (salient-pole)."""
        p = make_default_hydro_generator("H", "A", "B", "C", 18.0, 700.0)
        op = operational_parameters(p)
        assert op["is_type_59"] is False

    def test_omega_s_60hz(self):
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        op = operational_parameters(p)
        assert op["omega_s"] == pytest.approx(2 * math.pi * 60.0)


# ---------------------------------------------------------------------------
# Validador
# ---------------------------------------------------------------------------


class TestValidator:
    def test_valid_thermal(self):
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        assert validate_sm(p) == []

    def test_valid_hydro(self):
        p = make_default_hydro_generator("H", "A", "B", "C", 18.0, 700.0)
        assert validate_sm(p) == []

    def test_d_axis_hierarchy_violated(self):
        """Xd' > Xd é não-físico."""
        p = SynchronousMachineParameters(
            name="G", node_a="A", node_b="B", node_c="C",
            Xd=0.3, Xd_prime=1.8, Xd_pp=0.2,
            Td_prime=0.8, Td_pp=0.030,
            Xq=1.7, Xq_pp=0.20, Tq_pp=0.05,
        )
        errs = validate_sm(p)
        assert any("d-axis" in e for e in errs)

    def test_xL_above_Xd_pp(self):
        """xL > Xd'' viola física."""
        p = SynchronousMachineParameters(
            name="G", node_a="A", node_b="B", node_c="C",
            Xd=1.8, Xd_prime=0.3, Xd_pp=0.10, xL=0.20,
            Td_prime=0.8, Td_pp=0.030,
            Xq=1.7, Xq_pp=0.20, Tq_pp=0.05,
        )
        errs = validate_sm(p)
        assert any("d-axis" in e for e in errs)

    def test_td_prime_must_be_greater_than_td_pp(self):
        p = SynchronousMachineParameters(
            name="G", node_a="A", node_b="B", node_c="C",
            Td_prime=0.030, Td_pp=0.8,  # invertido
        )
        errs = validate_sm(p)
        assert any("Td'" in e and "Td''" in e for e in errs)

    def test_q_axis_hierarchy_type59(self):
        p = SynchronousMachineParameters(
            name="G", node_a="A", node_b="B", node_c="C",
            Xq=1.7, Xq_prime=0.10, Xq_pp=0.55,  # Xq'' > Xq'
            Tq_prime=0.4, Tq_pp=0.05,
        )
        errs = validate_sm(p)
        assert any("q-axis" in e for e in errs)

    def test_q_axis_hierarchy_type58(self):
        """Tipo 58: só Xq > Xq''."""
        p = SynchronousMachineParameters(
            name="G", node_a="A", node_b="B", node_c="C",
            Xq=0.20, Xq_prime=0.0, Xq_pp=0.65,   # Xq < Xq''
            Tq_pp=0.05,
        )
        errs = validate_sm(p)
        assert any("tipo 58" in e for e in errs)

    def test_zero_voltage_rejected(self):
        p = SynchronousMachineParameters(
            name="G", node_a="A", node_b="B", node_c="C",
            rated_voltage_kV=0.0,
        )
        errs = validate_sm(p)
        assert any("rated_voltage_kV" in e for e in errs)

    def test_odd_n_poles_rejected(self):
        p = SynchronousMachineParameters(
            name="G", node_a="A", node_b="B", node_c="C",
            n_poles=3,
        )
        errs = validate_sm(p)
        assert any("n_poles" in e for e in errs)

    def test_empty_node_rejected(self):
        p = SynchronousMachineParameters(
            name="G", node_a="", node_b="B", node_c="C",
        )
        errs = validate_sm(p)
        assert any("node_a vazio" in e for e in errs)

    def test_long_name_rejected(self):
        p = SynchronousMachineParameters(
            name="GENERATOR1", node_a="A", node_b="B", node_c="C",
        )
        errs = validate_sm(p)
        assert any("> 6 chars" in e for e in errs)

    def test_negative_inertia_rejected(self):
        p = SynchronousMachineParameters(
            name="G", node_a="A", node_b="B", node_c="C", H=-1.0,
        )
        errs = validate_sm(p)
        assert any("H" in e for e in errs)


# ---------------------------------------------------------------------------
# Curto-circuito
# ---------------------------------------------------------------------------


class TestShortCircuit:
    def test_subtransient_at_t0(self):
        """Em t=0, I = V/Xd'' = 1/0.20 = 5.0 pu."""
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        sc = short_circuit_currents(p)
        assert sc["I_subtransient_pu"] == pytest.approx(5.0, abs=0.01)
        assert sc["I_at_t_pu"] == pytest.approx(5.0, abs=0.01)

    def test_transient_value(self):
        """I' = V/Xd' = 1/0.30 = 3.33 pu."""
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        sc = short_circuit_currents(p)
        assert sc["I_transient_pu"] == pytest.approx(3.33, abs=0.01)

    def test_steady_state_value(self):
        """Iss = V/Xd = 1/1.8 = 0.556 pu."""
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        sc = short_circuit_currents(p)
        assert sc["I_steady_state_pu"] == pytest.approx(0.556, abs=0.01)

    def test_decay_at_5_seconds(self):
        """Em t=5s, deve estar próximo de Iss (decay completo)."""
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        sc = short_circuit_currents(p, time_s=5.0)
        # Td' = 0.8s, então 5s ≈ 6 time constants ⇒ decay completo
        assert sc["I_at_t_pu"] == pytest.approx(0.561, abs=0.01)

    def test_decay_monotonic(self):
        """Corrente decresce monotonicamente após o subtransitório."""
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        I_values = [
            short_circuit_currents(p, time_s=t)["I_at_t_pu"]
            for t in [0.0, 0.1, 0.5, 1.0, 5.0]
        ]
        for i in range(len(I_values) - 1):
            assert I_values[i] >= I_values[i + 1], \
                f"Não-monotônico: I({i}) = {I_values[i]}"

    def test_kA_conversion(self):
        """100 MVA / sqrt(3) / 13.8 kV = 4.184 kA base, * 5 = 20.9 kA pico."""
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        sc = short_circuit_currents(p)
        assert sc["I_subtransient_kA"] == pytest.approx(20.92, abs=0.05)
        assert sc["I_base_A"] == pytest.approx(4184, abs=10)

    def test_negative_time_rejected(self):
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        with pytest.raises(ValueError):
            short_circuit_currents(p, time_s=-0.1)

    def test_v_prefault_scaling(self):
        """Reduzir tensão pré-falta reduz proporcionalmente I''."""
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        sc1 = short_circuit_currents(p, v_prefault_pu=1.0)
        sc05 = short_circuit_currents(p, v_prefault_pu=0.5)
        assert sc05["I_subtransient_pu"] == pytest.approx(
            0.5 * sc1["I_subtransient_pu"], abs=0.001
        )


# ---------------------------------------------------------------------------
# Emissão MACHINE-59 / MACHINE-58
# ---------------------------------------------------------------------------


class TestEmit:
    def test_type_59_emitted(self):
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        lines = emit_sm_cards(p)
        # Cartão principal deve começar com "59"
        card_lines = [l for l in lines if l.startswith("59")]
        assert len(card_lines) == 1
        # v0.28.4-PRO: rated voltage agora em V (13800), não kV
        assert "13800" in card_lines[0] or "1.3800E+04" in card_lines[0]
        # S em VA (100e6), pode aparecer scientific ou decimal
        assert "100000000" in card_lines[0] or "1.0000E+08" in card_lines[0]

    def test_type_58_emitted_for_hydro(self):
        p = make_default_hydro_generator("H", "A", "B", "C", 18.0, 700.0)
        lines = emit_sm_cards(p)
        card_lines = [l for l in lines if l.startswith("58")]
        assert len(card_lines) == 1

    def test_metadata_in_comments(self):
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        text = emit_sm_text(p)
        assert "C MACHINE 59" in text
        assert "Synchronous Machine G" in text
        assert "13.800 kV" in text
        assert "100.000 MVA" in text
        assert "Z_base" in text

    def test_d_axis_continuation(self):
        """
        v0.28.4-PRO Onda 4.1: cards agora em strict fixed-format
        ATP. Comentários inline removidos para conformidade com
        column-precise. Verificações ajustadas para a estrutura
        agregada.
        """
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        text = emit_sm_text(p)
        # Estrutura documentada em comentário separado
        assert "d-axis" in text
        assert "q-axis" in text
        # Linhas com valores Xd/Xq presentes
        assert "MACHINE-" in text   # comentário documentação

    def test_blank_card_terminates(self):
        p = make_default_thermal_generator("G", "A", "B", "C", 13.8, 100.0)
        lines = emit_sm_cards(p)
        assert lines[-1].strip().startswith("BLANK")

    def test_invalid_raises(self):
        p = SynchronousMachineParameters(
            name="", node_a="A", node_b="B", node_c="C",  # name vazio
        )
        with pytest.raises(ValueError, match="inválida"):
            emit_sm_cards(p)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


class TestTemplates:
    def test_thermal_uses_type_59(self):
        p = make_default_thermal_generator("T", "A", "B", "C", 13.8, 100.0)
        op = operational_parameters(p)
        assert op["is_type_59"] is True

    def test_hydro_uses_type_58(self):
        p = make_default_hydro_generator("H", "A", "B", "C", 18.0, 700.0)
        op = operational_parameters(p)
        assert op["is_type_59"] is False

    def test_thermal_subtransient_5pu(self):
        """Thermal típico: I'' = 1/0.20 = 5 pu."""
        p = make_default_thermal_generator("T", "A", "B", "C", 13.8, 100.0)
        sc = short_circuit_currents(p)
        assert sc["I_subtransient_pu"] == pytest.approx(5.0, abs=0.01)

    def test_hydro_lower_subtransient(self):
        """Hydro tem Xd menor (1.0 pu) ⇒ Iss maior."""
        p = make_default_hydro_generator("H", "A", "B", "C", 18.0, 700.0)
        sc = short_circuit_currents(p)
        assert sc["I_steady_state_pu"] == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# Bridge integration
# ---------------------------------------------------------------------------


def _mk_sm(name: str, props: list[str]) -> PpComponent:
    return PpComponent(
        type="SM", name=name, visible=True,
        x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(p) for p in props],
    )


_DEFAULT_THERMAL_PROPS = [
    "13.8", "100", "60", "2",            # ratings
    "1.8", "0.30", "0.20", "0.8", "0.030",  # d-axis
    "1.7", "0.55", "0.20", "0.4", "0.050",  # q-axis
    "0.003", "0.15", "0.05",                 # Ra, xL, X0
    "4.0", "0.0",                             # H, D
    "0", "0", "1.0", "0",                     # init
]


class TestBridgeSm:
    def test_sm_emits_machine_59(self):
        comp = _mk_sm("GEN1", _DEFAULT_THERMAL_PROPS)
        atp = to_atp(PpProject(components=[comp]))
        text = "\n".join(atp.raw_lines)
        assert "C MACHINE 59" in text
        assert "59" in text
        assert "GEN1" in text
        assert "BLANK card terminating MACHINE" in text

    def test_sm_card_before_source(self):
        """Cards SM devem ser injetados ANTES de /SOURCE."""
        comp = _mk_sm("GEN1", _DEFAULT_THERMAL_PROPS)
        atp = to_atp(PpProject(components=[comp]))
        idx_machine = next(
            i for i, l in enumerate(atp.raw_lines)
            if l.startswith("C MACHINE")
        )
        idx_source = next(
            i for i, l in enumerate(atp.raw_lines) if l == "/SOURCE"
        )
        assert idx_machine < idx_source

    def test_invalid_voltage_warned(self):
        bad_props = list(_DEFAULT_THERMAL_PROPS)
        bad_props[0] = "abc"  # V_LL não-numérico
        comp = _mk_sm("GEN1", bad_props)
        atp = to_atp(PpProject(components=[comp]))
        assert any("rated_voltage_kV" in w for w in atp.warnings)

    def test_hierarchy_violation_warned(self):
        """Xd < Xd' viola hierarquia."""
        bad_props = list(_DEFAULT_THERMAL_PROPS)
        bad_props[4] = "0.10"   # Xd = 0.10
        bad_props[5] = "0.30"   # Xd' = 0.30 > Xd → erro
        comp = _mk_sm("GEN1", bad_props)
        atp = to_atp(PpProject(components=[comp]))
        # SM descartada → sem MACHINE em raw_lines
        text = "\n".join(atp.raw_lines)
        assert "C MACHINE" not in text
        assert any("d-axis" in w for w in atp.warnings)

    def test_sm_with_other_components(self):
        """SM coexiste com R/L/C sem conflito."""
        sm = _mk_sm("GEN1", _DEFAULT_THERMAL_PROPS)
        r = PpComponent(
            type="R", name="R1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100 Ohm")],
        )
        atp = to_atp(PpProject(components=[sm, r]))
        text = "\n".join(atp.raw_lines)
        assert "C MACHINE 59" in text
        assert len(atp.branches) == 1   # R1

    def test_warning_summary_emitted(self):
        # v0.28.4-PRO: card count agora 17 (incluindo MACHINE-XX
        # documentation comment).
        comp = _mk_sm("GEN1", _DEFAULT_THERMAL_PROPS)
        atp = to_atp(PpProject(components=[comp]))
        assert any(
            "MACHINE-59" in w and "cards" in w for w in atp.warnings
        )

    def test_helper_direct_call(self):
        """Smoke do helper sem ir pelo to_atp."""
        from app.preprocessor.node_coalescer import coalesce_nodes
        from app.core.project_model import AtpProject, HeaderInfo
        comp = _mk_sm("GEN1", _DEFAULT_THERMAL_PROPS)
        proj = PpProject(components=[comp])
        node_map = coalesce_nodes(proj)
        atp = AtpProject(file_path="", raw_lines=[], header=HeaderInfo(raw_lines=[]))
        sm = _convert_synchronous_machine(comp, "GEN1", node_map, atp)
        assert sm is not None
        assert sm.rated_voltage_kV == 13.8
        assert sm.Xd == 1.8
