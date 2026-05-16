"""
tests/test_pp_tacs_bridge.py — v0.26.0: integração TACS no bridge.

Cobre:

* TACS.ocomp com expressão válida → seção ``/TACS HYBRID`` injetada
  em ``atp.raw_lines`` antes de ``/BRANCH``.
* Inputs auto-detectados via ``collect_variables`` (excluem ``pi``,
  ``e``).
* Expressão vazia / inválida → bloco descartado + warning.
* Múltiplos componentes TACS → todos viram cartões 88.
* Sem componente TACS → projeto não recebe seção.
* Sections /BRANCH, /SWITCH, /SOURCE têm os ``start_line`` /
  ``end_line`` ajustados pelo shift.
"""

from __future__ import annotations

import pytest

from app.preprocessor.bridge_to_atp import (
    _extract_tacs_blocks, to_atp,
)
from app.preprocessor.models import PpComponent, PpProject, PpProperty


def _make_tacs(name: str, expression: str) -> PpComponent:
    return PpComponent(
        type="TACS", name=name, visible=True,
        x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(expression)],
    )


# ---------------------------------------------------------------------------
# _extract_tacs_blocks
# ---------------------------------------------------------------------------


class TestExtractTacsBlocks:
    def test_no_tacs_returns_empty(self):
        proj = PpProject(components=[])
        blocks, warns = _extract_tacs_blocks(proj)
        assert blocks == []
        assert warns == []

    def test_single_block_inputs_detected(self):
        comp = _make_tacs("ctrl1", "sin(omega * t)")
        proj = PpProject(components=[comp])
        blocks, warns = _extract_tacs_blocks(proj)
        assert len(blocks) == 1
        blk = blocks[0]
        assert blk.name == "ctrl1"
        assert blk.output == "ctrl1"
        assert set(blk.inputs) == {"omega", "t"}

    def test_pi_e_not_in_inputs(self):
        comp = _make_tacs("c1", "pi * r ^ 2 + e")
        proj = PpProject(components=[comp])
        blocks, _ = _extract_tacs_blocks(proj)
        assert blocks[0].inputs == ("r",)

    def test_empty_expression_warned(self):
        comp = _make_tacs("c1", "")
        proj = PpProject(components=[comp])
        blocks, warns = _extract_tacs_blocks(proj)
        assert blocks == []
        assert any("vazia" in w for w in warns)

    def test_invalid_syntax_warned(self):
        comp = _make_tacs("c1", "sin(((")
        proj = PpProject(components=[comp])
        blocks, warns = _extract_tacs_blocks(proj)
        assert blocks == []
        assert any("inválida" in w for w in warns)

    def test_unknown_function_warned(self):
        comp = _make_tacs("c1", "foo_bar(x)")
        proj = PpProject(components=[comp])
        blocks, warns = _extract_tacs_blocks(proj)
        assert blocks == []
        assert any("foo_bar" in w for w in warns)

    def test_long_name_truncated(self):
        comp = _make_tacs("controller_pid", "x")
        proj = PpProject(components=[comp])
        blocks, _ = _extract_tacs_blocks(proj)
        assert len(blocks[0].name) <= 6
        assert blocks[0].name == "contro"

    def test_multiple_blocks(self):
        c1 = _make_tacs("b1", "a + b")
        c2 = _make_tacs("b2", "c * d")
        proj = PpProject(components=[c1, c2])
        blocks, _ = _extract_tacs_blocks(proj)
        assert len(blocks) == 2

    def test_only_tacs_filtered(self):
        c_tacs = _make_tacs("tac1", "x")
        c_other = PpComponent(
            type="R", name="R1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100")],
        )
        proj = PpProject(components=[c_tacs, c_other])
        blocks, _ = _extract_tacs_blocks(proj)
        assert len(blocks) == 1
        assert blocks[0].name == "tac1"


# ---------------------------------------------------------------------------
# to_atp integration
# ---------------------------------------------------------------------------


class TestToAtpTacsIntegration:
    def test_tacs_section_injected(self):
        comp = _make_tacs("c1", "sin(omega * t)")
        atp = to_atp(PpProject(components=[comp]))
        text = "\n".join(atp.raw_lines)
        assert "/TACS HYBRID" in text
        assert "BLANK CARD ENDING TACS" in text

    def test_card_88_in_raw_lines(self):
        comp = _make_tacs("c1", "a + b")
        atp = to_atp(PpProject(components=[comp]))
        card_88 = [ln for ln in atp.raw_lines if ln.startswith("88")]
        assert len(card_88) == 1
        assert "c1" in card_88[0]

    def test_no_tacs_no_section(self):
        comp_r = PpComponent(
            type="R", name="R1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100")],
        )
        atp = to_atp(PpProject(components=[comp_r]))
        text = "\n".join(atp.raw_lines)
        assert "/TACS HYBRID" not in text

    def test_section_indices_shifted(self):
        comp = _make_tacs("c1", "x")
        atp = to_atp(PpProject(components=[comp]))
        # /BRANCH agora está depois das linhas /TACS, mas o
        # section.start_line deve apontar para a linha correta
        branch = atp.sections["BRANCH"]
        idx = branch.start_line
        assert atp.raw_lines[idx] == "/BRANCH"
        switch = atp.sections["SWITCH"]
        assert atp.raw_lines[switch.start_line] == "/SWITCH"
        source = atp.sections["SOURCE"]
        assert atp.raw_lines[source.start_line] == "/SOURCE"

    def test_warning_emitted(self):
        comp = _make_tacs("c1", "x")
        atp = to_atp(PpProject(components=[comp]))
        assert any("/TACS HYBRID" in w for w in atp.warnings)

    def test_invalid_block_warning(self):
        comp = _make_tacs("c1", "foo(x)")  # foo desconhecida
        atp = to_atp(PpProject(components=[comp]))
        # bloco descartado, sem seção
        text = "\n".join(atp.raw_lines)
        assert "/TACS HYBRID" not in text
        assert any("foo" in w for w in atp.warnings)

    def test_multiple_blocks_all_emitted(self):
        c1 = _make_tacs("b1", "x + y")
        c2 = _make_tacs("b2", "p * q")
        atp = to_atp(PpProject(components=[c1, c2])
        )
        cards_88 = [ln for ln in atp.raw_lines if ln.startswith("88")]
        assert len(cards_88) == 2

    def test_tacs_with_other_components(self):
        """TACS coexiste com componentes elétricos sem conflito."""
        c_tacs = _make_tacs("ct1", "a + b")
        c_r = PpComponent(
            type="R", name="R1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100 Ohm")],
        )
        atp = to_atp(PpProject(components=[c_tacs, c_r]))
        text = "\n".join(atp.raw_lines)
        assert "/TACS HYBRID" in text
        assert len(atp.branches) == 1   # R1 emitido
