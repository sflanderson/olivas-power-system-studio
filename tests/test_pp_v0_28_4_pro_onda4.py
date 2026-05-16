"""
tests/test_pp_v0_28_4_pro_onda4.py — v0.28.4-PRO Onda 4:
Card formats strict.

Cobre:

* atp_format helpers (fmt_node, fmt_num, card_line, set_field).
* MACHINE-58/59 strict format (sem inline comments).
* BCTRAN cards 51/52 column-precise (10-char fields).
* VCB MEASURING + TACS SOURCE auto-wire.
"""

from __future__ import annotations

import math

import pytest


# ---------------------------------------------------------------------------
# atp_format helpers
# ---------------------------------------------------------------------------


class TestFmtNode:

    def test_padded_to_width(self):
        from app.preprocessor.atp_format import fmt_node
        result = fmt_node("ND", 6)
        assert result == "ND    "
        assert len(result) == 6

    def test_truncated_when_too_long(self):
        from app.preprocessor.atp_format import fmt_node
        result = fmt_node("VERYLONGNAME", 6)
        assert result == "VERYLO"
        assert len(result) == 6

    def test_warning_via_project(self):
        from app.core.project_model import AtpProject
        from app.preprocessor.atp_format import fmt_node
        proj = AtpProject(file_path="x", raw_lines=[])
        fmt_node("LONGNAME", 6, project=proj, where="test")
        assert len(proj.warnings) >= 1
        assert "LONGNAME" in proj.warnings[0]

    def test_none_returns_padded(self):
        from app.preprocessor.atp_format import fmt_node
        result = fmt_node(None, 6)
        assert result == "      "
        assert len(result) == 6


class TestFmtNum:

    def test_zero(self):
        from app.preprocessor.atp_format import fmt_num
        assert fmt_num(0.0, 10).strip() == "0"
        assert len(fmt_num(0.0, 10)) == 10

    def test_decimal(self):
        from app.preprocessor.atp_format import fmt_num
        result = fmt_num(123.456, 10)
        assert len(result) == 10
        assert "123" in result

    def test_scientific_for_huge(self):
        from app.preprocessor.atp_format import fmt_num
        result = fmt_num(1e10, 10, scientific=True)
        assert "E" in result
        assert len(result) == 10

    def test_scientific_for_tiny(self):
        from app.preprocessor.atp_format import fmt_num
        result = fmt_num(1e-9, 10, scientific=True)
        assert "E" in result

    def test_nan_returns_zero(self):
        from app.preprocessor.atp_format import fmt_num
        result = fmt_num(float("nan"), 10)
        assert result.strip() == "0"

    def test_inf_returns_zero(self):
        from app.preprocessor.atp_format import fmt_num
        assert fmt_num(float("inf"), 10).strip() == "0"


class TestCardLine:

    def test_card_line_creates_80_chars(self):
        from app.preprocessor.atp_format import (
            ATP_LINE_MAX_WIDTH, card_line,
        )
        line = card_line("51")
        assert len(line) == ATP_LINE_MAX_WIDTH
        assert line.startswith("51")

    def test_set_field(self):
        from app.preprocessor.atp_format import card_line, set_field
        line = card_line("51")
        line = set_field(line, 2, "BUS-A", 6)
        assert line[2:8] == "BUS-A "

    def test_validate_card_width_trims(self):
        from app.preprocessor.atp_format import (
            ATP_LINE_MAX_WIDTH, validate_card_width,
        )
        too_long = "X" * (ATP_LINE_MAX_WIDTH + 10)
        assert len(validate_card_width(too_long)) == ATP_LINE_MAX_WIDTH


# ---------------------------------------------------------------------------
# MACHINE-58/59 strict
# ---------------------------------------------------------------------------


class TestMachineStrict:

    def test_main_card_starts_with_59(self):
        from app.preprocessor.synchronous_machine import (
            emit_sm_cards, make_default_thermal_generator,
        )
        p = make_default_thermal_generator(
            "G", "A", "B", "C", 13.8, 100.0,
        )
        lines = emit_sm_cards(p)
        main = next((l for l in lines if l.startswith("59")), None)
        assert main is not None

    def test_main_card_in_volts_va(self):
        """v0.28.4-PRO: rated agora em V (não kV) e VA (não MVA)."""
        from app.preprocessor.synchronous_machine import (
            emit_sm_cards, make_default_thermal_generator,
        )
        p = make_default_thermal_generator(
            "G", "A", "B", "C", 13.8, 100.0,
        )
        lines = emit_sm_cards(p)
        main = next(l for l in lines if l.startswith("59"))
        # 13800 V deve aparecer (decimal ou scientific)
        assert "13800" in main or "1.380" in main

    def test_no_inline_comments_in_data(self):
        """Cards de dados não têm comentários inline (strict)."""
        from app.preprocessor.synchronous_machine import (
            emit_sm_cards, make_default_thermal_generator,
        )
        p = make_default_thermal_generator(
            "G", "A", "B", "C", 13.8, 100.0,
        )
        lines = emit_sm_cards(p)
        # Linhas de dados (não-comentário) não têm "; "
        data_lines = [
            l for l in lines
            if not l.startswith("C")
            and not l.startswith("BLANK")
        ]
        for l in data_lines:
            assert "; d-axis" not in l
            assert "; q-axis" not in l


# ---------------------------------------------------------------------------
# BCTRAN column-precise
# ---------------------------------------------------------------------------


class TestBctranColumnPrecise:

    def test_card_51_uses_10_char_fields(self):
        from app.preprocessor.bctran import (
            TransformerBCTRANData, TransformerSCTest,
            TransformerOCTest, compute_bctran_parameters,
        )
        data = TransformerBCTRANData(
            name="T1",
            v_h=138e3, v_l=13.8e3,
            s_nom=25e6, frequency=60.0,
            sc_test=TransformerSCTest(v_sc_pct=10.0, p_sc_kw=100.0),
            oc_test=TransformerOCTest(i_0_pct=0.5, p_0_kw=50.0),
        )
        params = compute_bctran_parameters(data)
        cards = params.to_atp_cards("HA", "HB", "LA", "LB")
        line51 = next(l for l in cards if l.startswith("51"))
        # Estrutura: 51 + 6 + 6 + 4spc + 10 + 10 = 38 chars total
        # Verifica que é >= 36 (sem trailing whitespace pode ser menor)
        assert len(line51.rstrip()) >= 36

    def test_node_truncation_via_helper(self):
        """Nomes longos truncam usando fmt_node + ATP_NODE_FIELD_WIDTH."""
        from app.preprocessor.bctran import (
            TransformerBCTRANData, TransformerSCTest,
            TransformerOCTest, compute_bctran_parameters,
        )
        data = TransformerBCTRANData(
            name="T1",
            v_h=138e3, v_l=13.8e3,
            s_nom=25e6, frequency=60.0,
            sc_test=TransformerSCTest(v_sc_pct=10.0, p_sc_kw=100.0),
            oc_test=TransformerOCTest(i_0_pct=0.5, p_0_kw=50.0),
        )
        params = compute_bctran_parameters(data)
        cards = params.to_atp_cards(
            "VERYLONGNAME", "ALSOLONG", "L1", "L2",
        )
        line51 = next(l for l in cards if l.startswith("51"))
        # Cada nó truncado em 6 chars
        # Layout: 51VERYLONG ALSOLO    ...
        assert "VERYLO" in line51
        assert "ALSOLO" in line51


# ---------------------------------------------------------------------------
# VCB MEASURING auto-wire
# ---------------------------------------------------------------------------


class TestVcbMeasuringWiring:

    def test_emits_two_tacs_cards(self):
        from app.preprocessor.models import PpComponent, PpProperty
        from app.preprocessor.vcb_model_emitter import (
            build_vcb_tacs_wiring,
        )
        comp = PpComponent(
            type="VCB", name="DJ1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[],
        )
        lines = build_vcb_tacs_wiring(
            comp, "DJ1", "BUS_A", "BUS_B",
        )
        # 1 comentário + 2 cards TACS
        non_comment = [l for l in lines if not l.startswith("C")]
        assert len(non_comment) == 2
        # Card 90 (current measure)
        assert any(l.startswith("90") for l in non_comment)
        # Card 91 (voltage measure)
        assert any(l.startswith("91") for l in non_comment)

    def test_includes_node_names(self):
        from app.preprocessor.models import PpComponent
        from app.preprocessor.vcb_model_emitter import (
            build_vcb_tacs_wiring,
        )
        comp = PpComponent(
            type="VCB", name="DJ1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[],
        )
        # Nomes ≤ 6 chars (ATP limit)
        lines = build_vcb_tacs_wiring(
            comp, "DJ1", "BUSA", "BUSB",
        )
        text = "\n".join(lines)
        assert "BUSA" in text
        assert "BUSB" in text

    def test_phase_label_in_comment(self):
        from app.preprocessor.models import PpComponent
        from app.preprocessor.vcb_model_emitter import (
            build_vcb_tacs_wiring,
        )
        comp = PpComponent(
            type="VCB3", name="DJ1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[],
        )
        # Nomes ≤ 6 chars (BUS_A=5, OUT_A=5)
        lines = build_vcb_tacs_wiring(
            comp, "DJ1_A", "BUSA", "OUTA", phase="A",
        )
        text = "\n".join(lines)
        assert "fase A" in text

    def test_measurement_names_unique_per_instance(self):
        """
        v0.28.4-PRO followup blocker #2: VCBs distintos devem
        gerar nomes de medição DIFERENTES (antes era sempre
        TACS_I/TACS_V — colisão silenciosa).
        """
        from app.preprocessor.vcb_model_emitter import (
            measurement_node_names,
        )
        i1, v1 = measurement_node_names("DJ1")
        i2, v2 = measurement_node_names("DJ2")
        i3, v3 = measurement_node_names("DJ1_A")
        i4, v4 = measurement_node_names("DJ1_B")
        # Cada instância tem seu par de nomes distintos
        names = {i1, i2, i3, i4, v1, v2, v3, v4}
        # 4 instâncias × 2 (I/V) = 8 nomes
        assert len(names) == 8

    def test_use_block_references_same_tacs_names(self):
        """
        build_use_block e build_vcb_tacs_wiring devem usar os
        MESMOS nomes (consistência INPUT vs node emitido).
        """
        from app.preprocessor.models import PpComponent
        from app.preprocessor.vcb_model_emitter import (
            build_use_block, build_vcb_tacs_wiring,
            measurement_node_names,
        )
        comp = PpComponent(
            type="VCB", name="DJ1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=["0.005"],
        )
        # USE block referencia i_branch e v_branch
        use_lines = build_use_block(comp, "DJ1", "0.005")
        use_text = "\n".join(use_lines)

        # Nomes esperados
        i_name, v_name = measurement_node_names("DJ1")
        # USE block deve referenciar EXATAMENTE esses nomes
        assert f":= {i_name}" in use_text
        assert f":= {v_name}" in use_text

        # Wiring emite os MESMOS nomes
        wiring = build_vcb_tacs_wiring(comp, "DJ1", "BUSA", "BUSB")
        wire_text = "\n".join(wiring)
        assert i_name in wire_text
        assert v_name in wire_text
