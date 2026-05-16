"""
tests/test_pp_type98_bridge.py — v0.24.2: integração Type-98 no
bridge_to_atp. ``LNL.ocomp`` com ``sat_curve_csv`` preenchido
emite cards Type-98 reais; sem ele, cai no placeholder tipo 92.

Cobre:

* LNL com CSV válido → cards inseridos em /BRANCH + warning
  educativo.
* LNL sem CSV → placeholder tipo 92 + warning com dica.
* LNL com CSV inválido → placeholder + warning de erro de parsing.
* i_ss e flux_ss populados no header.
* Múltiplos LNL no mesmo projeto coexistem.
* ZnO/RNL (sem integração v0.24.2) continuam como placeholder.
* Section indices ajustados após insert.
"""

from __future__ import annotations

import pytest

from app.core.serializer import serialize_project
from app.preprocessor.bridge_to_atp import to_atp
from app.preprocessor.models import PpComponent, PpProject, PpProperty


def _lnl(name: str = "LNL1",
         csv: str = "",
         i_ss: str = "0",
         flux_ss: str = "0") -> PpComponent:
    """LNL com layout de props v0.24.2: [lookup_file, csv, i_ss, flux_ss]."""
    return PpComponent(
        type="LNL", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[
            PpProperty(""),            # [0] lookup_file
            PpProperty(csv),           # [1] sat_curve_csv
            PpProperty(i_ss),          # [2] i_ss
            PpProperty(flux_ss),       # [3] flux_ss
        ],
    )


def _r(name: str = "R1") -> PpComponent:
    """R simples p/ garantir topologia mínima."""
    return PpComponent(
        type="R", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[
            PpProperty("100"),
            PpProperty("26.85"),
            PpProperty("european"),
        ],
    )


# ---------------------------------------------------------------------------
# Happy path: CSV preenchido → Type-98
# ---------------------------------------------------------------------------


class TestType98Emission:
    def test_csv_present_emits_type98_cards(self):
        lnl = _lnl(csv="0,0; 1,0.95; 5,1.05; 20,1.10")
        proj = PpProject(components=[_r(), lnl], wires=[], diagrams=[])
        atp = to_atp(proj)
        # Pelo menos 1 linha começando com "98" em raw_lines
        assert any(ln.startswith("98") for ln in atp.raw_lines)
        # Terminador 9999 presente
        assert "9999" in atp.raw_lines

    def test_warning_mentions_type98(self):
        lnl = _lnl(name="L_core", csv="0,0; 1,1; 5,1.1")
        proj = PpProject(components=[lnl], wires=[], diagrams=[])
        atp = to_atp(proj)
        joined = " | ".join(atp.warnings)
        assert "Type-98" in joined
        assert "L_core" in joined

    def test_no_branchcomponent_for_type98_lnl(self):
        """Quando Type-98 é emitido, não há BranchComponent placeholder."""
        lnl = _lnl(csv="0,0; 1,1; 5,1.1")
        proj = PpProject(components=[lnl], wires=[], diagrams=[])
        atp = to_atp(proj)
        placeholders = [
            b for b in atp.branches
            if b.type_code == "92" and b.semantic_type == "nonlinear"
        ]
        assert len(placeholders) == 0

    def test_all_csv_points_in_output(self):
        lnl = _lnl(csv="0,0; 1,0.95; 5,1.05; 20,1.10; 200,1.15")
        proj = PpProject(components=[lnl], wires=[], diagrams=[])
        atp = to_atp(proj)
        joined = "\n".join(atp.raw_lines)
        # Os 5 valores de i devem aparecer em notação científica
        assert "0.0000E+00" in joined
        assert "1.0000E+00" in joined
        assert "5.0000E+00" in joined
        assert "2.0000E+01" in joined
        assert "2.0000E+02" in joined

    def test_ss_values_in_header(self):
        lnl = _lnl(
            csv="0,0; 1,1",
            i_ss="0.5",
            flux_ss="0.9",
        )
        proj = PpProject(components=[lnl], wires=[], diagrams=[])
        atp = to_atp(proj)
        # Header (linha com "98") deve conter 0.5 e 0.9
        header_line = next(ln for ln in atp.raw_lines if ln.startswith("98"))
        assert "5.0000E-01" in header_line
        assert "9.0000E-01" in header_line

    def test_section_indices_adjusted_after_type98(self):
        lnl = _lnl(csv="0,0; 1,1")
        proj = PpProject(components=[lnl], wires=[], diagrams=[])
        atp = to_atp(proj)
        branch = atp.sections["BRANCH"]
        # start_line aponta para "/BRANCH"
        assert atp.raw_lines[branch.start_line] == "/BRANCH"
        # end_line+1 aponta para "BLANK BRANCH"
        assert atp.raw_lines[branch.end_line + 1].startswith("BLANK BRANCH")

    def test_serialize_project_still_works_with_type98(self):
        lnl = _lnl(csv="0,0; 1,1; 5,1.1")
        proj = PpProject(components=[_r(), lnl], wires=[], diagrams=[])
        atp = to_atp(proj)
        text = serialize_project(atp)
        # Seções mantidas + Type-98 presente
        assert "/BRANCH" in text
        assert "/SWITCH" in text
        assert "9999" in text   # terminador do Type-98


# ---------------------------------------------------------------------------
# Fallback: CSV ausente ou inválido → placeholder
# ---------------------------------------------------------------------------


class TestFallbackPlaceholder:
    def test_empty_csv_falls_back_to_placeholder(self):
        lnl = _lnl(csv="")
        proj = PpProject(components=[lnl], wires=[], diagrams=[])
        atp = to_atp(proj)
        placeholders = [
            b for b in atp.branches
            if b.type_code == "92" and b.semantic_type == "nonlinear"
        ]
        assert len(placeholders) == 1
        # Warning com dica de como preencher
        joined = " | ".join(atp.warnings)
        assert "sat_curve_csv" in joined

    def test_no_type98_cards_when_empty(self):
        lnl = _lnl(csv="")
        proj = PpProject(components=[lnl], wires=[], diagrams=[])
        atp = to_atp(proj)
        assert not any(ln.startswith("98") for ln in atp.raw_lines)
        assert "9999" not in atp.raw_lines

    def test_invalid_csv_falls_back_with_error_warning(self):
        """CSV não-monotônico → placeholder, warning menciona erro."""
        lnl = _lnl(csv="0,0; 10,1.0; 5,1.2")
        proj = PpProject(components=[lnl], wires=[], diagrams=[])
        atp = to_atp(proj)
        placeholders = [
            b for b in atp.branches
            if b.type_code == "92"
        ]
        # Cai no placeholder porque a curva é inválida
        assert len(placeholders) == 1
        joined = " | ".join(atp.warnings)
        # Warning do parser deve ter sido propagado
        assert "inválida" in joined or "invalida" in joined or "não-monotônico" in joined


# ---------------------------------------------------------------------------
# Multi + outros não-lineares
# ---------------------------------------------------------------------------


class TestMultiAndOtherNonlinear:
    def test_multiple_lnl_with_type98(self):
        l1 = _lnl(name="L1", csv="0,0; 1,1")
        l2 = _lnl(name="L2", csv="0,0; 2,2; 5,2.5")
        proj = PpProject(components=[l1, l2], wires=[], diagrams=[])
        atp = to_atp(proj)
        # 2 headers Type-98
        type98_headers = [ln for ln in atp.raw_lines if ln.startswith("98")]
        assert len(type98_headers) == 2
        # 2 terminadores
        terminators = [ln for ln in atp.raw_lines if ln == "9999"]
        assert len(terminators) == 2

    def test_zno_remains_placeholder(self):
        """ZnO não foi integrado em v0.24.2 — deve seguir como placeholder."""
        zno = PpComponent(
            type="ZnO", name="ZNO1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("200 V")],
        )
        proj = PpProject(components=[zno], wires=[], diagrams=[])
        atp = to_atp(proj)
        placeholders = [
            b for b in atp.branches
            if b.type_code == "92"
        ]
        assert len(placeholders) == 1

    def test_rnl_remains_placeholder(self):
        """RNL idem — sem integração Type-99 ainda."""
        rnl = PpComponent(
            type="RNL", name="RNL1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("lookup.dat")],
        )
        proj = PpProject(components=[rnl], wires=[], diagrams=[])
        atp = to_atp(proj)
        placeholders = [
            b for b in atp.branches
            if b.type_code == "92"
        ]
        assert len(placeholders) == 1

    def test_mixed_lnl_bctran_trafo(self):
        """LNL+Type-98 convive com Tr+BCTRAN sem quebrar indices."""
        lnl = _lnl(csv="0,0; 1,1; 5,1.1")
        tr = PpComponent(
            type="Tr", name="TR1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[
                PpProperty("230:69"), PpProperty("1 mH"),
                PpProperty("230000"), PpProperty("69000"),
                PpProperty("100000000"),
                PpProperty("10.0"), PpProperty("400.0"),
                PpProperty("0.5"), PpProperty("50.0"),
            ],
        )
        proj = PpProject(components=[tr, lnl], wires=[], diagrams=[])
        atp = to_atp(proj)
        # Type-98 presente
        assert any(ln.startswith("98") for ln in atp.raw_lines)
        # Cards BCTRAN (tipo 51/52) presentes
        assert any(ln.startswith("51") for ln in atp.raw_lines)
        assert any(ln.startswith("52") for ln in atp.raw_lines)
        # Serializer roda sem erro
        text = serialize_project(atp)
        assert "/BRANCH" in text
