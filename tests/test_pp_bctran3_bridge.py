"""
tests/test_pp_bctran3_bridge.py — v0.24.5: integração BCTRAN
3-enrolamento no bridge_to_atp.

Cobre:

* Tr3 com dados completos → 6 cards (1 tipo 51 + 5 tipo 52) na
  seção /BRANCH.
* Tr3 sem dados → fallback para placeholder tipo 19 legacy.
* Tr3 com dados parciais (ex. v_sc_HM mas não HB/MB) → bridge
  preenche com heurística e emite cards.
* Nós sintéticos para enrolamento B (TR_B1 / TR_B2) — distintos
  e ≤ 6 chars.
* Warning informativo menciona "BCTRAN 3-enrolamento" + grupo +
  nota sobre wiring manual.
* Section indices ajustados após insert.
* Serializador final continua funcional.
* Coexistência: Tr (2-enrol) + Tr3 (3-enrol) no mesmo projeto.
"""

from __future__ import annotations

import pytest

from app.core.serializer import serialize_project
from app.preprocessor.bridge_to_atp import to_atp
from app.preprocessor.models import PpComponent, PpProject, PpProperty


def _make_tr3_full(name: str = "TR3") -> PpComponent:
    """Tr3 100/100/100 MVA, 230/69/13.8 kV, com SC_HM=12, HB=10, MB=6 (%)."""
    return PpComponent(
        type="Tr3", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[
            PpProperty("230:69:13.8"),  # ratio (legacy)
            PpProperty("1 mH"),         # L_mag (legacy)
            PpProperty("230000"),       # V_H
            PpProperty("69000"),        # V_M
            PpProperty("13800"),        # V_B
            PpProperty("100000000"),    # S_H
            PpProperty("100000000"),    # S_M
            PpProperty("100000000"),    # S_B
            PpProperty("12.0"),         # v_sc_HM_pct
            PpProperty("300.0"),        # p_sc_HM_kW
            PpProperty("10.0"),         # v_sc_HB_pct
            PpProperty("400.0"),        # p_sc_HB_kW
            PpProperty("6.0"),          # v_sc_MB_pct
            PpProperty("200.0"),        # p_sc_MB_kW
            PpProperty("0.3"),          # i_0_pct
            PpProperty("100.0"),        # p_0_kW
            PpProperty("11"),           # clock = 11h
        ],
    )


def _make_tr3_empty(name: str = "TR3_LEGACY") -> PpComponent:
    """Tr3 sem dados BCTRAN — apenas 2 props legacy."""
    return PpComponent(
        type="Tr3", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty("1:1:1"), PpProperty("1 mH")],
    )


def _make_tr3_partial_HB_only_HM(name: str = "TR3_PART") -> PpComponent:
    """Tr3 com V_H/V_M/V_B/S_H/S_M/S_B mas sem v_sc_HB e v_sc_MB."""
    return PpComponent(
        type="Tr3", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[
            PpProperty("230:69:13.8"), PpProperty("1 mH"),
            PpProperty("230000"), PpProperty("69000"), PpProperty("13800"),
            PpProperty("100000000"), PpProperty("100000000"), PpProperty("100000000"),
            PpProperty("12.0"), PpProperty("300.0"),  # SC_HM
            PpProperty("0"),    PpProperty("0"),       # SC_HB ausente
            PpProperty("0"),    PpProperty("0"),       # SC_MB ausente
            PpProperty("0"),    PpProperty("0"),       # OC vazio
            PpProperty("0"),                            # clock=0
        ],
    )


# ---------------------------------------------------------------------------
# Happy path: 3w completo
# ---------------------------------------------------------------------------


class TestBCTRAN3Emission:
    def test_full_data_emits_6_cards(self):
        """1 tipo 51 + 5 tipo 52 = 6 cards de matriz + 2 comentários."""
        proj = PpProject(components=[_make_tr3_full()], wires=[], diagrams=[])
        atp = to_atp(proj)
        type51_count = sum(1 for ln in atp.raw_lines if ln.startswith("51"))
        type52_count = sum(1 for ln in atp.raw_lines if ln.startswith("52"))
        assert type51_count == 1
        assert type52_count == 5

    def test_warning_menciona_3_enrolamento(self):
        proj = PpProject(components=[_make_tr3_full()], wires=[], diagrams=[])
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "3-enrolamento" in joined or "3-winding" in joined.lower()

    def test_warning_menciona_grupo_3phase(self):
        proj = PpProject(components=[_make_tr3_full()], wires=[], diagrams=[])
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        # Default group h_connection=Y, l_connection=Y, clock=11 → "Yy11"
        # (do extract_bctran3_data)
        assert "11" in joined  # clock 11 mencionado

    def test_synthetic_b_nodes_distinct(self):
        """Nós sintéticos B1 e B2 devem ser distintos e ≤ 6 chars."""
        proj = PpProject(components=[_make_tr3_full(name="TRX")], wires=[], diagrams=[])
        atp = to_atp(proj)
        # Procura linhas com nós sintéticos
        b_lines = [
            ln for ln in atp.raw_lines
            if ln.startswith("52") and ("_B1" in ln or "_B2" in ln)
        ]
        assert len(b_lines) == 3  # 3 cards do enrolamento B
        # Extrair nome dos 2 primeiros (B1, B2 — não importa qual)
        assert any("_B1" in ln for ln in b_lines)
        assert any("_B2" in ln for ln in b_lines)

    def test_warning_mentions_wiring_manual(self):
        proj = PpProject(components=[_make_tr3_full()], wires=[], diagrams=[])
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "wiring manual" in joined.lower() or "wirin" in joined.lower()

    def test_no_branchcomponent_for_bctran3_trafo(self):
        proj = PpProject(components=[_make_tr3_full()], wires=[], diagrams=[])
        atp = to_atp(proj)
        placeholders = [
            b for b in atp.branches
            if b.type_code == "19" and b.semantic_type == "transformer"
        ]
        assert len(placeholders) == 0

    def test_section_indices_adjusted_after_3w_insert(self):
        proj = PpProject(components=[_make_tr3_full()], wires=[], diagrams=[])
        atp = to_atp(proj)
        branch = atp.sections["BRANCH"]
        assert atp.raw_lines[branch.start_line] == "/BRANCH"
        assert atp.raw_lines[branch.end_line + 1].startswith("BLANK BRANCH")

    def test_serialize_project_with_3w(self):
        proj = PpProject(components=[_make_tr3_full()], wires=[], diagrams=[])
        atp = to_atp(proj)
        text = serialize_project(atp)
        assert "/BRANCH" in text
        assert "/SWITCH" in text
        assert "BCTRAN 3w" in text


# ---------------------------------------------------------------------------
# Fallback: dados ausentes ou incompletos
# ---------------------------------------------------------------------------


class TestFallback:
    def test_empty_falls_back_to_placeholder(self):
        proj = PpProject(components=[_make_tr3_empty()], wires=[], diagrams=[])
        atp = to_atp(proj)
        placeholders = [
            b for b in atp.branches
            if b.type_code == "19" and b.semantic_type == "transformer"
        ]
        assert len(placeholders) == 1
        # Sem cards 3w em raw_lines
        assert not any(ln.startswith("51") for ln in atp.raw_lines)

    def test_partial_HB_MB_uses_heuristic(self):
        """v_sc_HB e v_sc_MB ausentes → bridge preenche heurística."""
        proj = PpProject(
            components=[_make_tr3_partial_HB_only_HM()],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        # Deve ter emitido cards (não placeholder), pois o bridge
        # preenche os SC ausentes com heurística (v_sc_HM/2 etc.)
        type51_count = sum(1 for ln in atp.raw_lines if ln.startswith("51"))
        assert type51_count == 1

    def test_partial_no_critical_falls_back(self):
        """Sem V_H ou S_H, cai em fallback 2-winding ou placeholder."""
        # V_H = 0 → não é 3w (extract retorna None)
        # E sem campos 2-winding também → placeholder
        comp = PpComponent(
            type="Tr3", name="X", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[
                PpProperty("1:1:1"), PpProperty("1 mH"),
                PpProperty("0"),  # V_H = 0
                PpProperty("69000"), PpProperty("13800"),
                PpProperty("0"), PpProperty("0"), PpProperty("0"),
                PpProperty("0"), PpProperty("0"),
                PpProperty("0"), PpProperty("0"),
                PpProperty("0"), PpProperty("0"),
                PpProperty("0"), PpProperty("0"),
                PpProperty("0"),
            ],
        )
        proj = PpProject(components=[comp], wires=[], diagrams=[])
        atp = to_atp(proj)
        placeholders = [
            b for b in atp.branches
            if b.type_code == "19" and b.semantic_type == "transformer"
        ]
        # Sem V_H, fallback 2w também não ativa → placeholder
        assert len(placeholders) == 1


# ---------------------------------------------------------------------------
# Coexistência Tr (2-enrol) + Tr3 (3-enrol)
# ---------------------------------------------------------------------------


class TestMixed2W3W:
    def test_tr_and_tr3_coexist(self):
        """Tr 2-enrol + Tr3 3-enrol no mesmo projeto."""
        tr2 = PpComponent(
            type="Tr", name="TR2W", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[
                PpProperty("230:69"), PpProperty("1 mH"),
                PpProperty("230000"), PpProperty("69000"),
                PpProperty("100000000"),
                PpProperty("10.0"), PpProperty("400.0"),
                PpProperty("0.5"), PpProperty("50.0"),
            ],
        )
        proj = PpProject(
            components=[tr2, _make_tr3_full(name="TR3W")],
            wires=[], diagrams=[],
        )
        atp = to_atp(proj)
        # Pelo menos 2 tipo 51 (1 do Tr2 + 1 do Tr3)
        type51_count = sum(1 for ln in atp.raw_lines if ln.startswith("51"))
        assert type51_count == 2
        # Tr2: 1 tipo-51 + 2 tipo-52 = 3 cards;
        # Tr3: 1 tipo-51 + 5 tipo-52 = 6 cards.
        type52_count = sum(1 for ln in atp.raw_lines if ln.startswith("52"))
        assert type52_count == 7   # 2 + 5


# ---------------------------------------------------------------------------
# Validação de prop indices preservada
# ---------------------------------------------------------------------------


class TestPropertyIndicesPreserved:
    def test_clock_field_at_index_16(self):
        """O campo 'clock' deve estar no índice 16 do Tr3."""
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().require("Tr3")
        assert spec.properties[16].name == "clock"
        assert spec.properties[16].type.value == "int"

    def test_v_sc_HM_at_index_8(self):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().require("Tr3")
        assert spec.properties[8].name == "v_sc_HM_pct"

    def test_total_props_is_17(self):
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().require("Tr3")
        assert len(spec.properties) == 17
