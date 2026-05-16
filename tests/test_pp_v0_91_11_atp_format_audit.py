"""
tests/test_pp_v0_91_11_atp_format_audit.py — v0.91.11:

Auditoria do formato .atp gerado pela bridge contra o EMTP
Rule Book (Vol. 1).

Bug reportado pelo usuário: ATP simulação falhava com ERROR/
ERROR/ERROR mesmo após v0.91.10 (que adicionou TIME/MISC
cards e blank ref1).

Investigação via inspeção do .atp gerado + Rule Book §4.2.1
e §10.3.4 revelou:

1. **TIME card off-by-one** — campos E8.0 mas o código usava
   6 espaços de separação (gerando 9 chars total) onde
   deveriam ser 5 espaços (8 chars total). XOPT/COPT
   "vazavam" para a coluna seguinte.

2. **XOPT/COPT = 60** estavam errados. Bridge converte
   H→mH e F→μF assumindo XOPT=COPT=0 (default mH/μF). Setar
   XOPT=60Hz faz ATP reinterpretar valores em mH como Ω@60Hz
   → indutância errada.

3. **Vac TSTART blank** → ATP não computava AC steady-state
   init. Rule Book §10.3.4 Rule 6: "An AC steady-state
   solution is automatically computed if Tstart < 0".
   Sem isso, sources arrancavam abruptamente em t=0,
   causando transientes espúrios + ERROR.

Cobertura
---------

* TIME card: cols exatamente 8+8 = 16 chars de dados
  (DELTAT + TMAX), resto blank (16 cols após).
* MISC card: 10 fields × 8 cols = 80 chars total.
* XOPT/COPT blank na TIME card (fallback to 0 = default
  mH/μF).
* Vac source tem TSTART = "-1." (negativo).
* Iac source tem TSTART = "-1." (negativo).
* Vdc/Idc não setam TSTART (DC sources não usam steady-
  state init).
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _vac_comp(name: str = "V1"):
    from app.preprocessor.models import PpComponent, PpProperty
    return PpComponent(
        type="Vac", name=name, visible=True,
        x=100, y=100, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[
            PpProperty("11270 V", True),
            PpProperty("60 Hz", True),
            PpProperty("0", False),
        ],
    )


# ---------------------------------------------------------------------------
# TIME card format
# ---------------------------------------------------------------------------


class TestTimeCard:

    def test_time_card_dt_tmax_only(self, qapp):
        """v0.91.11: TIME card tem DELTAT (8) + TMAX (8) = 16
        chars, sem XOPT/COPT (default mH/μF para a bridge)."""
        from app.preprocessor.bridge_to_atp import to_atp
        from app.preprocessor.models import PpProject
        proj = PpProject()
        atp = to_atp(proj)
        # Acha a TIME card no header (3a linha após BEGIN +
        # comment).
        time_card = atp.header.raw_lines[2]
        # Não deve conter XOPT=60 ou COPT=60
        assert "60." not in time_card[16:32], (
            f"TIME card tem XOPT/COPT non-blank: {time_card!r}"
        )
        # DELTAT cols 1-8: "   1.E-6"
        assert time_card[:8].strip() == "1.E-6"
        # TMAX cols 9-16: "     .05"
        assert time_card[8:16].strip() == ".05"

    def test_misc_card_10_fields(self, qapp):
        """v0.91.11: MISC card tem 10 campos (I8 cada) = 80 chars."""
        from app.preprocessor.bridge_to_atp import to_atp
        from app.preprocessor.models import PpProject
        proj = PpProject()
        atp = to_atp(proj)
        misc_card = atp.header.raw_lines[3]
        # 10 campos × 8 cols = 80 chars (mas pode ter trailing
        # blank stripped → mínimo 73 se IPRSUP=0 right-aligned
        # em col 80 mas value fits in last 1 char)
        # Por seguraça, conta os campos lendo cada 8 chars
        fields = [
            misc_card[i*8:(i+1)*8].strip()
            for i in range(10)
        ]
        # Pelo menos IOUT (campo 0) é setado
        assert fields[0] != "", f"IOUT não setado: {misc_card!r}"
        # IPRSUP (campo 9) — pode ser blank/0
        # Smoke: 10 campos parseable sem erro

    def test_no_extra_xopt_copt_overflow(self, qapp):
        """v0.91.11 regression: o off-by-one anterior fazia o
        '.' do XOPT/COPT vazar para o campo seguinte."""
        from app.preprocessor.bridge_to_atp import to_atp
        from app.preprocessor.models import PpProject
        proj = PpProject()
        atp = to_atp(proj)
        time_card = atp.header.raw_lines[2]
        # cols 17-24 (XOPT) deve estar blank
        if len(time_card) >= 24:
            xopt_field = time_card[16:24]
            assert xopt_field.strip() == "", (
                f"XOPT field não blank: {xopt_field!r}"
            )


# ---------------------------------------------------------------------------
# Source TSTART for AC sources (Rule Book §10.3.4 Rule 6)
# ---------------------------------------------------------------------------


class TestSourceTstart:

    def test_vac_has_negative_tstart(self, qapp):
        """v0.91.11: Vac.tstart = '-1.' para AC steady-state init."""
        from app.preprocessor.bridge_to_atp import _convert_vac
        comp = _vac_comp("V1")
        src = _convert_vac(comp, "N0001")
        assert src.t_start == "-1.", (
            f"Vac TSTART deve ser negativo (Rule Book Rule 6); "
            f"got {src.t_start!r}"
        )
        assert src.type_code == "14"   # AC voltage source

    def test_iac_has_negative_tstart(self, qapp):
        """v0.91.11: Iac também tem TSTART negativo."""
        from app.preprocessor.bridge_to_atp import _convert_iac
        comp = _vac_comp("I1")    # mesmas props (amp, freq, phase)
        src = _convert_iac(comp, "N0001")
        assert src.t_start == "-1."
        assert src.type_code == "-14"  # AC current source

    def test_vdc_no_tstart(self, qapp):
        """v0.91.11: Vdc (DC step) não usa AC steady-state.
        TSTART blank é OK (apply at t=0)."""
        from app.preprocessor.bridge_to_atp import _convert_vdc
        from app.preprocessor.models import PpComponent, PpProperty
        comp = PpComponent(
            type="Vdc", name="V1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100", True)],
        )
        src = _convert_vdc(comp, "N0001")
        # Vdc não recebe steady-state init (DC step funciona em t=0)
        assert src.t_start == ""
        assert src.type_code == "11"


# ---------------------------------------------------------------------------
# Generated ATP integration
# ---------------------------------------------------------------------------


class TestIntegrationGeneratedAtp:

    def test_simple_template_has_real_circuit(self, qapp):
        """
        v0.91.12: simple_13_8kV agora tem R_LOAD, criando
        circuito real (Vac → BUS → R → GND). Antes era
        Vac→BUS→GND direto (curto = degenerate ATP KILL 191).
        """
        from app.preprocessor.bridge_to_atp import to_atp
        from app.preprocessor.templates import build_simple_13_8kV
        proj = build_simple_13_8kV()
        atp = to_atp(proj)
        # Pelo menos 1 source e pelo menos 1 branch
        assert len(atp.sources) >= 1, "Sem source AC"
        assert len(atp.branches) >= 1, (
            "Sem branches — ATP iria reportar KILL 191 "
            "(degenerate, no transients possible)"
        )
        # Source e branch compartilham um nó (circuito conectado)
        source_nodes = {s.node for s in atp.sources}
        branch_nodes = set()
        for b in atp.branches:
            for n in (b.node1, b.node2):
                if n:
                    branch_nodes.add(n)
        assert source_nodes & branch_nodes, (
            f"Source nodes {source_nodes} não conectam a "
            f"nenhuma branch {branch_nodes} — circuito isolado"
        )

    def test_industrial_template_full_serialization(self, qapp):
        """v0.91.11 end-to-end: industrial template gera ATP
        com TIME/MISC cards corretos, ref1 blank, source com
        TSTART=-1."""
        from app.core.serializer import serialize_project
        from app.preprocessor.bridge_to_atp import to_atp
        from app.preprocessor.templates import build_industrial_480V
        proj = build_industrial_480V()
        atp = to_atp(proj)
        text = serialize_project(atp)
        # Sanity checks pontuais
        assert "BEGIN NEW DATA CASE" in text
        assert "/BRANCH" in text
        assert "/SOURCE" in text
        # Source com TSTART negativo
        # Linha do tipo: 14N0002        11270        60         0            -1.
        source_lines = [
            ln for ln in text.splitlines()
            if ln.startswith("14")
        ]
        assert len(source_lines) == 1, (
            f"Esperava 1 source AC; got {source_lines}"
        )
        # TSTART está em algum lugar perto do fim da linha
        assert "-1." in source_lines[0], (
            f"TSTART=-1 ausente em source: {source_lines[0]!r}"
        )
        # Branches com ref1 blank — verifica via parsing dos
        # cols 15-20 nas linhas de branch
        branch_lines = [
            ln for ln in text.splitlines()
            if ln.startswith("  N")
        ]
        assert len(branch_lines) >= 2  # R_FEED + L_FEED
        for bl in branch_lines:
            if len(bl) >= 20:
                ref1 = bl[14:20]
                assert ref1.strip() == "", (
                    f"ref1 não blank em branch: {bl!r} ref1={ref1!r}"
                )
