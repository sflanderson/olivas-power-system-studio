"""
tests/test_pp_bctran_bridge.py — v0.24.1: integração BCTRAN no
bridge_to_atp. ``Tr.ocomp`` com dados SC/OC preenchidos emite
cards tipo 51/52; sem eles, cai no placeholder legacy.

Cobre:

* Trafo com dados completos → 3 cards /BRANCH (tipo 51 + 2 tipo 52)
  + 1 comentário BCTRAN inseridos em raw_lines.
* Trafo sem dados → placeholder tipo 19 legacy (1 branch).
* Trafo com V_H/V_L/S_nom mas sem v_sc_pct → placeholder legacy
  (exige todos os campos críticos).
* Warning diferenciado: BCTRAN vs placeholder.
* Section indices de BRANCH/SWITCH/SOURCE ajustados após insert.
* Serializador final continua funcional.
"""

from __future__ import annotations

import pytest

from app.core.serializer import serialize_project
from app.preprocessor.bridge_to_atp import to_atp
from app.preprocessor.models import PpComponent, PpProject, PpProperty


def _make_tr_full(name: str = "TR_100MVA") -> PpComponent:
    """Trafo 100 MVA 230/69 kV com todos os dados BCTRAN."""
    return PpComponent(
        type="Tr", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[
            PpProperty("230:69"),
            PpProperty("1 mH"),
            PpProperty("230000"),
            PpProperty("69000"),
            PpProperty("100000000"),
            PpProperty("10.0"),
            PpProperty("400.0"),
            PpProperty("0.5"),
            PpProperty("50.0"),
        ],
    )


def _make_tr_empty(name: str = "TR_LEGACY") -> PpComponent:
    """Trafo sem dados BCTRAN — apenas 2 props legacy."""
    return PpComponent(
        type="Tr", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty("1:1"), PpProperty("1 mH")],
    )


def _make_tr_partial(name: str = "TR_PARTIAL") -> PpComponent:
    """Trafo com V_H/V_L/S_nom mas sem dados de teste."""
    return PpComponent(
        type="Tr", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[
            PpProperty("230:69"), PpProperty("1 mH"),
            PpProperty("230000"), PpProperty("69000"),
            PpProperty("100000000"),
            PpProperty("0"),  # v_sc_pct zerado
            PpProperty("0"), PpProperty("0"), PpProperty("0"),
        ],
    )


# ---------------------------------------------------------------------------
# Happy path: trafo com dados completos gera cards BCTRAN
# ---------------------------------------------------------------------------


class TestBCTranEmission:
    def test_trafo_full_emits_bctran_cards(self):
        tr = _make_tr_full()
        proj = PpProject(components=[tr], wires=[], diagrams=[])
        atp = to_atp(proj)

        # raw_lines devem conter os cards tipo 51 e 52
        joined = "\n".join(atp.raw_lines)
        assert "BCTRAN" in joined or "51" in joined
        # Pelo menos um tipo 51 e dois tipo 52
        assert any(ln.startswith("51") for ln in atp.raw_lines)
        type52_lines = [ln for ln in atp.raw_lines if ln.startswith("52")]
        assert len(type52_lines) == 2

    def test_warning_menciona_bctran(self):
        tr = _make_tr_full()
        proj = PpProject(components=[tr], wires=[], diagrams=[])
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "BCTRAN" in joined
        assert "TR_100MVA" in joined

    def test_no_branchcomponent_for_bctran_trafo(self):
        """Com BCTRAN, o retorno é None e não há BranchComponent legacy."""
        tr = _make_tr_full()
        proj = PpProject(components=[tr], wires=[], diagrams=[])
        atp = to_atp(proj)
        # Nenhum branch tipo "19" (placeholder)
        placeholders = [
            b for b in atp.branches
            if b.type_code == "19" and b.semantic_type == "transformer"
        ]
        assert len(placeholders) == 0

    def test_section_indices_adjusted_after_insert(self):
        tr = _make_tr_full()
        proj = PpProject(components=[tr], wires=[], diagrams=[])
        atp = to_atp(proj)
        # Após insert dos 4 cards (comment + 3 branches) a seção BRANCH
        # cresceu; SWITCH e SOURCE ficam adiante do ponto de inserção.
        branch = atp.sections["BRANCH"]
        # Linha start_line aponta para '/BRANCH' literal
        assert atp.raw_lines[branch.start_line] == "/BRANCH"
        # Linha end_line+1 aponta para 'BLANK BRANCH' literal
        assert atp.raw_lines[branch.end_line + 1].startswith("BLANK BRANCH")

    def test_serialize_project_still_works(self):
        tr = _make_tr_full()
        proj = PpProject(components=[tr], wires=[], diagrams=[])
        atp = to_atp(proj)
        text = serialize_project(atp)
        # Estrutura mínima presente
        assert "/BRANCH" in text
        assert "/SWITCH" in text
        assert "/SOURCE" in text
        # Cards BCTRAN no /BRANCH
        assert "51" in text


# ---------------------------------------------------------------------------
# Fallback: trafo sem dados → placeholder legacy
# ---------------------------------------------------------------------------


class TestLegacyPlaceholder:
    def test_empty_trafo_emits_placeholder(self):
        tr = _make_tr_empty()
        proj = PpProject(components=[tr], wires=[], diagrams=[])
        atp = to_atp(proj)
        # Exatamente 1 branch (placeholder tipo 19)
        placeholders = [
            b for b in atp.branches
            if b.type_code == "19" and b.semantic_type == "transformer"
        ]
        assert len(placeholders) == 1

    def test_empty_trafo_no_bctran_cards(self):
        """Sem dados, não insere cards BCTRAN em raw_lines."""
        tr = _make_tr_empty()
        proj = PpProject(components=[tr], wires=[], diagrams=[])
        atp = to_atp(proj)
        # Não há linhas tipo 51/52 inseridas em raw_lines
        type51 = [ln for ln in atp.raw_lines if ln.startswith("51")]
        type52 = [ln for ln in atp.raw_lines if ln.startswith("52")]
        assert len(type51) == 0
        assert len(type52) == 0

    def test_empty_trafo_warning_pede_dados(self):
        tr = _make_tr_empty()
        proj = PpProject(components=[tr], wires=[], diagrams=[])
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "placeholder" in joined.lower()
        # Warning educativo: menciona V_H/V_L/S_nom ou SC/OC
        assert "BCTRAN" in joined or "V_H" in joined or "SC" in joined

    def test_partial_trafo_falls_back_to_placeholder(self):
        """V_H/V_L/S_nom preenchidos mas v_sc_pct = 0 → placeholder."""
        tr = _make_tr_partial()
        proj = PpProject(components=[tr], wires=[], diagrams=[])
        atp = to_atp(proj)
        placeholders = [
            b for b in atp.branches
            if b.type_code == "19" and b.semantic_type == "transformer"
        ]
        assert len(placeholders) == 1


# ---------------------------------------------------------------------------
# Múltiplos trafos no mesmo projeto
# ---------------------------------------------------------------------------


class TestMultipleTrafos:
    def test_multiple_bctran_trafos(self):
        """2 trafos BCTRAN → 2 blocos de cards na seção /BRANCH."""
        tr1 = _make_tr_full(name="TR1")
        tr2 = _make_tr_full(name="TR2")
        proj = PpProject(components=[tr1, tr2], wires=[], diagrams=[])
        atp = to_atp(proj)
        type51_count = sum(1 for ln in atp.raw_lines if ln.startswith("51"))
        type52_count = sum(1 for ln in atp.raw_lines if ln.startswith("52"))
        # Cada trafo: 1 tipo-51 + 2 tipo-52
        assert type51_count == 2
        assert type52_count == 4

    def test_mixed_bctran_and_placeholder(self):
        """BCTRAN + placeholder coexistem."""
        tr1 = _make_tr_full(name="TR_BCTRAN")
        tr2 = _make_tr_empty(name="TR_LEGACY")
        proj = PpProject(components=[tr1, tr2], wires=[], diagrams=[])
        atp = to_atp(proj)
        # 1 placeholder legacy + 3 cards BCTRAN em raw_lines
        assert len([b for b in atp.branches if b.type_code == "19"]) == 1
        assert any(ln.startswith("51") for ln in atp.raw_lines)


# ---------------------------------------------------------------------------
# Dados inválidos: bridge não explode
# ---------------------------------------------------------------------------


class TestInvalidData:
    def test_v_sc_pct_excess_falls_back(self):
        """v_sc_pct > 100 viola validação → placeholder."""
        tr = PpComponent(
            type="Tr", name="TR_BAD", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[
                PpProperty("1:1"), PpProperty("1 mH"),
                PpProperty("230000"), PpProperty("69000"),
                PpProperty("100000000"),
                PpProperty("150"),  # v_sc_pct > 100!
                PpProperty("400.0"),
                PpProperty("0.5"), PpProperty("50.0"),
            ],
        )
        proj = PpProject(components=[tr], wires=[], diagrams=[])
        # Deve NÃO levantar exceção
        atp = to_atp(proj)
        # Cai no placeholder legacy
        placeholders = [
            b for b in atp.branches
            if b.type_code == "19" and b.semantic_type == "transformer"
        ]
        assert len(placeholders) == 1
