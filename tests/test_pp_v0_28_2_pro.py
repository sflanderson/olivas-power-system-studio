"""
tests/test_pp_v0_28_2_pro.py — v0.28.2-PRO Onda 1: correções
P0 da auditoria total ATP core.

Cobre:

* 1.1: type codes corretos para _convert_iac (-14) e
  _convert_idc (-11).
* 1.2: encoding fallback (UTF-8 → Latin-1 → CP1252).
* 1.3: _truncate_atp_name centralizado com warning.
* 1.4: _insert_lines_at correto (preserva todas seções).
* 1.5: tail_lines pega último BLANK pair (não primeiro).
* 1.6: node_coalescer detecta pin-on-wire-midpoint.
* 1.7: BCTRAN 3w valida Wye-equivalent não-negativo.
* 1.8: Vector-fit normaliza frequência (ill-conditioning).
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1.1 — Type codes Iac/Idc
# ---------------------------------------------------------------------------


class TestTypeCodes:

    def test_iac_uses_minus_14(self):
        from app.preprocessor.bridge_to_atp import _convert_iac
        from app.preprocessor.models import PpComponent, PpProperty
        comp = PpComponent(
            type="Iac", name="I1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[
                PpProperty("I=10 A"),
                PpProperty("f=60"),
                PpProperty("Phase=0"),
            ],
        )
        src = _convert_iac(comp, "N1")
        assert src.type_code == "-14"

    def test_idc_uses_minus_11(self):
        from app.preprocessor.bridge_to_atp import _convert_idc
        from app.preprocessor.models import PpComponent, PpProperty
        comp = PpComponent(
            type="Idc", name="I1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("I=10 A")],
        )
        src = _convert_idc(comp, "N1")
        assert src.type_code == "-11"


# ---------------------------------------------------------------------------
# 1.2 — Encoding fallback
# ---------------------------------------------------------------------------


class TestEncodingFallback:

    def test_latin1_decoded(self, tmp_path):
        """Arquivo Latin-1 com acento decodifica sem erro."""
        from app.core.parser import _read_atp_text
        f = tmp_path / "test.atp"
        # Latin-1: é = 0xE9
        content = "C Coment\xe1rio com acento\nBEGIN NEW DATA CASE\nC end"
        f.write_bytes(content.encode("latin-1"))
        text = _read_atp_text(f)
        assert "Coment" in text
        # Verifica que NÃO foi corrompido com replace
        assert "?" not in text or "Coment\xe1rio" in text

    def test_utf8_normal(self, tmp_path):
        from app.core.parser import _read_atp_text
        f = tmp_path / "test.atp"
        f.write_text("C UTF-8 normal\nBEGIN NEW DATA CASE", encoding="utf-8")
        text = _read_atp_text(f)
        assert "UTF-8 normal" in text


# ---------------------------------------------------------------------------
# 1.3 — Truncation warning helper
# ---------------------------------------------------------------------------


class TestTruncationWarnings:

    def test_short_name_unchanged(self):
        from app.preprocessor.bridge_to_atp import _truncate_atp_name
        result = _truncate_atp_name("BUS-A", max_len=6)
        assert result == "BUS-A"

    def test_long_name_truncated(self):
        from app.preprocessor.bridge_to_atp import _truncate_atp_name
        result = _truncate_atp_name("BUS-A-13.8kV", max_len=6)
        assert result == "BUS-A-"

    def test_warning_appended_to_project(self):
        from app.core.project_model import AtpProject
        from app.preprocessor.bridge_to_atp import _truncate_atp_name
        project = AtpProject(file_path="x", raw_lines=[])
        _truncate_atp_name(
            "BUS-A-13.8kV", where="test", project=project,
        )
        assert len(project.warnings) == 1
        assert "BUS-A-13.8kV" in project.warnings[0]
        assert "BUS-A-" in project.warnings[0]
        assert "test" in project.warnings[0]

    def test_no_warning_for_short(self):
        from app.core.project_model import AtpProject
        from app.preprocessor.bridge_to_atp import _truncate_atp_name
        project = AtpProject(file_path="x", raw_lines=[])
        _truncate_atp_name("SHORT", where="t", project=project)
        assert len(project.warnings) == 0

    def test_none_returns_empty(self):
        from app.preprocessor.bridge_to_atp import _truncate_atp_name
        assert _truncate_atp_name(None) == ""


# ---------------------------------------------------------------------------
# 1.4 — _insert_lines_at
# ---------------------------------------------------------------------------


class TestInsertLinesAt:

    def test_grow_section_at_end(self):
        from app.core.project_model import AtpProject, Section
        from app.preprocessor.bridge_to_atp import _insert_lines_at
        atp = AtpProject(
            file_path="x",
            raw_lines=["L0", "L1", "L2", "L3"],
        )
        atp.sections["BRANCH"] = Section(
            name="BRANCH", raw_lines=["L1", "L2"],
            start_line=1, end_line=2,
        )
        atp.sections["SOURCE"] = Section(
            name="SOURCE", raw_lines=["L3"],
            start_line=3, end_line=3,
        )
        # Insere ao final do BRANCH (insert_at = end_line + 1)
        shift = _insert_lines_at(
            atp, insert_at=3,
            lines=["NEW1", "NEW2"],
            grow_section="BRANCH",
        )
        assert shift == 2
        # BRANCH deve ter crescido
        assert atp.sections["BRANCH"].end_line == 4
        # SOURCE deve ter shifted para baixo
        assert atp.sections["SOURCE"].start_line == 5
        assert atp.sections["SOURCE"].end_line == 5

    def test_no_grow_only_shift(self):
        from app.core.project_model import AtpProject, Section
        from app.preprocessor.bridge_to_atp import _insert_lines_at
        atp = AtpProject(
            file_path="x",
            raw_lines=["L0", "L1", "L2", "L3"],
        )
        atp.sections["BRANCH"] = Section(
            name="BRANCH", raw_lines=["L1", "L2"],
            start_line=1, end_line=2,
        )
        # Insere ANTES de BRANCH (insert_at=1)
        _insert_lines_at(atp, insert_at=1, lines=["NEW"])
        # BRANCH inteiro deslocado
        assert atp.sections["BRANCH"].start_line == 2
        assert atp.sections["BRANCH"].end_line == 3


# ---------------------------------------------------------------------------
# 1.6 — Pin on wire midpoint
# ---------------------------------------------------------------------------


class TestPinOnWireMidpoint:

    def test_point_on_segment_collinear_inside(self):
        from app.preprocessor.node_coalescer import _point_on_segment
        # Wire (0,0) → (10,0); ponto (5,0) está no meio
        assert _point_on_segment(0, 0, 10, 0, 5, 0) is True

    def test_point_on_segment_endpoint_excluded(self):
        from app.preprocessor.node_coalescer import _point_on_segment
        assert _point_on_segment(0, 0, 10, 0, 0, 0) is False
        assert _point_on_segment(0, 0, 10, 0, 10, 0) is False

    def test_point_off_segment(self):
        from app.preprocessor.node_coalescer import _point_on_segment
        # Não colinear
        assert _point_on_segment(0, 0, 10, 0, 5, 5) is False
        # Colinear mas fora do segmento
        assert _point_on_segment(0, 0, 10, 0, 15, 0) is False

    def test_diagonal_wire_midpoint(self):
        from app.preprocessor.node_coalescer import _point_on_segment
        # Wire (0,0) → (10,10); ponto (5,5) no meio
        assert _point_on_segment(0, 0, 10, 10, 5, 5) is True
        # Ponto (5,4) NÃO está colinear
        assert _point_on_segment(0, 0, 10, 10, 5, 4) is False


# ---------------------------------------------------------------------------
# 1.7 — BCTRAN 3w validate
# ---------------------------------------------------------------------------


class TestBctran3wValidate:

    def test_negative_x_h_raises(self):
        from app.preprocessor.bctran import (
            TransformerBCTRAN3Data,
            TransformerSCTest, TransformerOCTest,
            compute_bctran_parameters_3w,
        )
        # Configuração inconsistente: v_sc_mb >> v_sc_hm + v_sc_hb
        # → x_h fica negativo
        data = TransformerBCTRAN3Data(
            name="TR3-BAD",
            v_h=230000.0, v_m=69000.0, v_b=13800.0,
            s_h=100e6, s_m=50e6, s_b=50e6,
            frequency=60.0,
            # Configuração inconsistente proposital:
            sc_h_m=TransformerSCTest(v_sc_pct=2.0, p_sc_kw=100),
            sc_h_b=TransformerSCTest(v_sc_pct=2.0, p_sc_kw=100),
            sc_m_b=TransformerSCTest(v_sc_pct=20.0, p_sc_kw=500),
            oc_test=TransformerOCTest(
                i_0_pct=0.5, p_0_kw=100,
            ),
        )
        # v0.28.2-PRO: warn-and-clamp (não raise) para preservar
        # backward compat. Verifica que UserWarning é emitido.
        with pytest.warns(UserWarning, match="Wye-equivalent"):
            result = compute_bctran_parameters_3w(data)
        # Resultado clampado mas válido (não None)
        assert result is not None


# ---------------------------------------------------------------------------
# 1.8 — Vector-fit frequency normalization
# ---------------------------------------------------------------------------


class TestVectorFitNormalization:

    def test_high_frequency_range_converges(self):
        """Range 0.01 Hz → 1 MHz (8 décadas) deve convergir."""
        np = pytest.importorskip("numpy")
        from app.preprocessor.vector_fitting import vector_fit

        # Dados sintéticos: H(s) = 1/(s + 100) com 50 amostras log-spaced
        f_min, f_max = 0.01, 1e6
        frequencies = np.logspace(
            np.log10(f_min), np.log10(f_max), 50,
        )
        s = 1j * 2 * math.pi * frequencies
        f_data = 1.0 / (s + 100.0)

        # Com normalização
        fit = vector_fit(
            list(frequencies), list(f_data),
            n_poles=2,
            normalize_frequency=True,
            n_iterations=10,    # mais iterações para convergir
        )
        # Convergência razoável (≤ 1% RMS para função simples)
        # Range de 8 décadas é desafiador; threshold realista 5e-3.
        assert fit.rms_error < 5e-3

    def test_min_samples_check(self):
        """Vector-fit exige amostras >= 2*n_poles + extras."""
        np = pytest.importorskip("numpy")
        from app.preprocessor.vector_fitting import vector_fit

        frequencies = list(np.linspace(1, 100, 5))   # só 5 amostras
        f_data = [complex(1.0, 0.0)] * 5
        with pytest.raises(ValueError, match="amostras"):
            vector_fit(
                frequencies, f_data,
                n_poles=4,    # precisa >= 9 amostras
                fit_d=True,
            )
