"""
tests/test_pp_tacs_interface.py — v0.26.4: interface TACS↔EMTP.

Cobre:

* ``TacsMeasuring``: V/I, GND válido em node2, validate (vazio,
  >6 chars, type inválido, I com node1==node2), helpers
  ``make_voltage_probe`` / ``make_current_probe``.
* ``TacsControlledSource``: V (TYPE-13) e I (TYPE-14), validate
  (vazio, >6, type inválido, t_start>=t_stop), helpers
  ``make_voltage_source_tacs`` / ``make_current_source_tacs``.
* ``TacsControlledSwitch``: validate (vazio, >6, node1==node2,
  initial_state default).
* Despacho via ``emit_tacs_section`` para os 3 novos tipos.
* Bridge ``_convert_sw_tacs``: SwTACS.ocomp gera
  ``SwitchComponent`` com switch_type="TACS", type_code="13",
  semantic_type contendo o trigger_signal.
"""

from __future__ import annotations

import pytest

from app.preprocessor.bridge_to_atp import _convert_sw_tacs, to_atp
from app.preprocessor.models import PpComponent, PpProject, PpProperty
from app.preprocessor.tacs import emit_tacs_section
from app.preprocessor.tacs_interface import (
    TacsControlledSource, TacsControlledSwitch, TacsMeasuring,
    emit_controlled_source_lines, emit_controlled_switch_lines,
    emit_measuring_lines,
    make_current_probe, make_current_source_tacs,
    make_voltage_probe, make_voltage_source_tacs,
    validate_controlled_source, validate_controlled_switch,
    validate_measuring,
)


# ---------------------------------------------------------------------------
# TacsMeasuring
# ---------------------------------------------------------------------------


class TestMeasuring:
    def test_voltage_probe(self):
        m = make_voltage_probe("mv", "meas", "vm")
        assert m.measurement_type == "V"
        assert m.node2 == ""    # GND implícito
        assert validate_measuring(m) == []

    def test_current_probe(self):
        m = make_current_probe("mi", "n1", "n2", "im")
        assert m.measurement_type == "I"
        assert validate_measuring(m) == []

    def test_validate_invalid_type(self):
        m = TacsMeasuring(
            name="mv", node1="n", node2="",
            output_signal="vm", measurement_type="X",
        )
        errs = validate_measuring(m)
        assert any("measurement_type" in e for e in errs)

    def test_validate_current_same_nodes(self):
        m = TacsMeasuring(
            name="mi", node1="n1", node2="n1",
            output_signal="im", measurement_type="I",
        )
        errs = validate_measuring(m)
        assert any("node1 != node2" in e for e in errs)

    def test_validate_voltage_same_nodes_ok(self):
        """Para V, node1 == node2 é estranho mas não rejeitamos
        explicitamente (ATP retorna 0)."""
        m = TacsMeasuring(
            name="mv", node1="n", node2="n",
            output_signal="vm", measurement_type="V",
        )
        # Não há erro específico; só normais (vazios/longos).
        errs = validate_measuring(m)
        assert not any("node1 != node2" in e for e in errs)

    def test_validate_long_output(self):
        m = TacsMeasuring(
            name="m", node1="n1", node2="",
            output_signal="abcdefgh", measurement_type="V",
        )
        errs = validate_measuring(m)
        assert any("> 6 chars" in e for e in errs)

    def test_emit_voltage_card(self):
        m = make_voltage_probe("mv", "meas", "vm")
        lines = emit_measuring_lines(m)
        cards = [l for l in lines if l.startswith("90")]
        assert len(cards) == 1
        assert "vm" in cards[0]
        assert "meas" in cards[0]

    def test_emit_current_card(self):
        m = make_current_probe("mi", "n1", "n2", "im")
        lines = emit_measuring_lines(m)
        cards = [l for l in lines if l.startswith("91")]
        assert len(cards) == 1


# ---------------------------------------------------------------------------
# TacsControlledSource
# ---------------------------------------------------------------------------


class TestControlledSource:
    def test_voltage_source(self):
        s = make_voltage_source_tacs("vs", "n1", "ulim")
        assert s.source_type == "V"
        assert validate_controlled_source(s) == []

    def test_current_source(self):
        s = make_current_source_tacs("is_", "n1", "iref")
        assert s.source_type == "I"
        assert validate_controlled_source(s) == []

    def test_validate_invalid_type(self):
        s = TacsControlledSource(
            name="x", node="n1", control_signal="u", source_type="X",
        )
        errs = validate_controlled_source(s)
        assert any("source_type" in e for e in errs)

    def test_validate_t_start_ge_stop(self):
        s = TacsControlledSource(
            name="x", node="n1", control_signal="u", source_type="V",
            t_start=2.0, t_stop=1.0,
        )
        errs = validate_controlled_source(s)
        assert any("t_start" in e for e in errs)

    def test_validate_long_node(self):
        s = TacsControlledSource(
            name="x", node="abcdefgh", control_signal="u",
            source_type="V",
        )
        errs = validate_controlled_source(s)
        assert any("node" in e and "> 6 chars" in e for e in errs)

    def test_validate_empty_control_signal(self):
        s = TacsControlledSource(
            name="x", node="n1", control_signal="", source_type="V",
        )
        errs = validate_controlled_source(s)
        assert any("control_signal vazio" in e for e in errs)

    def test_emit_type_13_voltage(self):
        s = make_voltage_source_tacs("vs", "n1", "ulim")
        lines = emit_controlled_source_lines(s)
        cards = [l for l in lines if l.startswith("13")]
        assert len(cards) == 1

    def test_emit_type_14_current(self):
        s = make_current_source_tacs("is_", "n1", "iref")
        lines = emit_controlled_source_lines(s)
        cards = [l for l in lines if l.startswith("14")]
        assert len(cards) == 1


# ---------------------------------------------------------------------------
# TacsControlledSwitch
# ---------------------------------------------------------------------------


class TestControlledSwitch:
    def test_basic(self):
        sw = TacsControlledSwitch(
            name="sw", node1="a", node2="b", control_signal="ena",
        )
        assert validate_controlled_switch(sw) == []
        assert sw.threshold == 0.5
        assert sw.initial_state is False

    def test_validate_same_nodes(self):
        sw = TacsControlledSwitch(
            name="sw", node1="a", node2="a", control_signal="ena",
        )
        errs = validate_controlled_switch(sw)
        assert any("degenerada" in e for e in errs)

    def test_validate_empty_control(self):
        sw = TacsControlledSwitch(
            name="sw", node1="a", node2="b", control_signal="",
        )
        errs = validate_controlled_switch(sw)
        assert any("control_signal vazio" in e for e in errs)

    def test_validate_empty_node(self):
        sw = TacsControlledSwitch(
            name="sw", node1="", node2="b", control_signal="ena",
        )
        errs = validate_controlled_switch(sw)
        assert any("node1 vazio" in e for e in errs)

    def test_emit_card_13(self):
        sw = TacsControlledSwitch(
            name="sw", node1="a", node2="b", control_signal="ena",
        )
        lines = emit_controlled_switch_lines(sw)
        cards = [l for l in lines if l.startswith("13")]
        assert len(cards) == 1
        assert "ena" in cards[0]

    def test_emit_initial_state_in_comment(self):
        sw_open = TacsControlledSwitch(
            name="sw", node1="a", node2="b", control_signal="ena",
            initial_state=False,
        )
        sw_closed = TacsControlledSwitch(
            name="sw", node1="a", node2="b", control_signal="ena",
            initial_state=True,
        )
        text_open = "\n".join(emit_controlled_switch_lines(sw_open))
        text_closed = "\n".join(emit_controlled_switch_lines(sw_closed))
        assert "initial_state = open" in text_open
        assert "initial_state = closed" in text_closed


# ---------------------------------------------------------------------------
# Despacho via emit_tacs_section
# ---------------------------------------------------------------------------


class TestDispatchInterface:
    def test_dispatch_measuring(self):
        m = make_voltage_probe("mv", "meas", "vm")
        text = emit_tacs_section([m])
        assert "/TACS HYBRID" in text
        assert "90" in text   # device-90 = voltage measuring

    def test_dispatch_controlled_source(self):
        s = make_voltage_source_tacs("vs", "n1", "u")
        text = emit_tacs_section([s])
        assert "13" in text

    def test_dispatch_controlled_switch(self):
        sw = TacsControlledSwitch(
            name="sw", node1="a", node2="b", control_signal="ena",
        )
        text = emit_tacs_section([sw])
        assert "13" in text

    def test_invalid_measuring_raises(self):
        m = TacsMeasuring(
            name="", node1="n", node2="",
            output_signal="o", measurement_type="V",
        )
        with pytest.raises(ValueError, match="inválid"):
            emit_tacs_section([m])

    def test_full_closed_loop(self):
        """Pipeline closed-loop: probe V → erro → PID → clip →
        SOURCE TACS → SWITCH TACS."""
        from app.preprocessor.tacs_blocks import (
            TacsLimiter, make_subtractor,
        )
        from app.preprocessor.tacs_tf import make_pid
        items = [
            make_voltage_probe("mv", "meas", "vm"),
            make_subtractor("e", "err", "ref", "vm"),
            make_pid("pid", "err", "upid", Kp=2.0, Ki=10.0, Kd=0.001),
            TacsLimiter(
                name="clp", output="ulim", input_signal="upid",
                output_min=-1.0, output_max=1.0,
            ),
            make_voltage_source_tacs("gv", "gen", "ulim"),
            TacsControlledSwitch(
                name="tr", node1="l1", node2="l2",
                control_signal="ena",
            ),
        ]
        text = emit_tacs_section(items)
        # Cada device-type representativo
        for code in ("90", "98", "1upid", "54", "13gen", "13l1"):
            assert code in text, f"falta {code!r}"


# ---------------------------------------------------------------------------
# Bridge: SwTACS.ocomp → SwitchComponent type-13
# ---------------------------------------------------------------------------


def _make_sw_tacs(name: str = "sw1", trigger: str = "ena") -> PpComponent:
    return PpComponent(
        type="SwTACS", name=name, visible=True,
        x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(trigger)],
    )


class TestBridgeSwTACS:
    def test_sw_tacs_emits_type_13(self):
        comp = _make_sw_tacs("sw1", "ena")
        atp = to_atp(PpProject(components=[comp]))
        assert len(atp.switches) == 1
        sw = atp.switches[0]
        assert sw.type_code == "13"
        assert sw.switch_type == "TACS"
        assert "ena" in sw.semantic_type

    def test_sw_tacs_warning_emitted(self):
        comp = _make_sw_tacs("sw1", "trigger_x")
        atp = to_atp(PpProject(components=[comp]))
        # truncado a 6 chars
        assert any("trigger_signal" in w and "trigge" in w for w in atp.warnings)

    def test_sw_tacs_default_trigger(self):
        """Sem trigger_signal, usa default 'trigger'."""
        comp = PpComponent(
            type="SwTACS", name="sw1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[],
        )
        atp = to_atp(PpProject(components=[comp]))
        assert len(atp.switches) == 1

    def test_sw_tacs_long_trigger_truncated(self):
        comp = _make_sw_tacs("sw1", "very_long_trigger_name")
        atp = to_atp(PpProject(components=[comp]))
        sw = atp.switches[0]
        # semantic_type = "tacs_controlled:<truncated>"
        suffix = sw.semantic_type.split(":")[1]
        assert len(suffix) <= 6

    def test_sw_tacs_with_other_comp(self):
        """SwTACS coexiste com R/L/C sem conflito."""
        sw_tacs = _make_sw_tacs("sw1", "ena")
        r = PpComponent(
            type="R", name="R1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100 Ohm")],
        )
        atp = to_atp(PpProject(components=[sw_tacs, r]))
        assert len(atp.switches) == 1
        assert len(atp.branches) == 1

    def test_helper_function_direct(self):
        comp = _make_sw_tacs("sw1", "trig")
        from app.core.project_model import AtpProject, HeaderInfo
        proj = AtpProject(
            file_path="", raw_lines=[], header=HeaderInfo(raw_lines=[]),
        )
        sw = _convert_sw_tacs(comp, "n1", "n2", proj)
        assert sw.node1 == "n1"
        assert sw.node2 == "n2"
        assert sw.switch_type == "TACS"
        assert sw.type_code == "13"
