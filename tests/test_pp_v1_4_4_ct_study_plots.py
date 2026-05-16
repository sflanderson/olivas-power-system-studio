"""
tests.test_pp_v1_4_4_ct_study_plots — v1.4.4 Sprint A/B/C.

Cobre os 3 plots especializados do CT Saturation Study (paridade
MATLAB CT_STUDY/run_level{1,2,3}_*.m):

  Sprint A: plot_level1_ansi (barras condicionais V_tap vs V_req)
  Sprint B: plot_level2_iec  (log-log com joelho + zonas saturação)
  Sprint C: plot_level3_dynamic (2 subplots: fluxo + correntes)

Testes são headless (matplotlib Agg backend) — não exigem QApplication.
"""

from __future__ import annotations

import math

import pytest

# matplotlib é dependência forte do projeto (já em requirements.txt).
matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")

from matplotlib.figure import Figure  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def passing_report():
    """TC superdimensionado (deve PASSAR): C800 @ 1200:5 vs falta 10 kA."""
    from app.postprocessor.ct_saturation import (
        CTFaultContext, CTSpec, analyze_full,
        typical_magnetization_curve,
    )
    fault = CTFaultContext(
        bus_id="BUS-OK",
        rated_voltage_kV=13.8,
        I_fault_rms_kA=10.0,
        X_over_R=8.0,
    )
    ct = CTSpec(
        tag="CT-OK",
        tipo_TC="ANSI_C",
        I_pri_nom_tap=1200, I_pri_nom_full=1200,
        I_sn=5,
        CT_Rating_C=800.0,
        R_s=0.5, R_b=0.3,
        curve=typical_magnetization_curve(800.0),
        Kr=0.1,
    )
    return analyze_full(ct, fault)


@pytest.fixture
def failing_report():
    """TC subdimensionado (deve FALHAR): C100 @ 2000:5 vs falta 28 kA."""
    from app.postprocessor.ct_saturation import (
        CTFaultContext, CTSpec, analyze_full,
        typical_magnetization_curve,
    )
    fault = CTFaultContext(
        bus_id="BUS-FAIL",
        rated_voltage_kV=13.8,
        I_fault_rms_kA=28.0,
        X_over_R=13.0,
    )
    ct = CTSpec(
        tag="CT-FAIL",
        tipo_TC="ANSI_C",
        I_pri_nom_tap=2000, I_pri_nom_full=2000,
        I_sn=5,
        CT_Rating_C=100.0,
        R_s=0.5, R_b=0.3,
        curve=typical_magnetization_curve(100.0),
        Kr=0.8,
    )
    return analyze_full(ct, fault)


# ===========================================================================
# Sprint A — plot_level1_ansi
# ===========================================================================


class TestPlotLevel1Ansi:

    def test_returns_figure_passing(self, passing_report):
        from app.gui.ct_saturation_plots import plot_level1_ansi
        fig = plot_level1_ansi(passing_report)
        assert isinstance(fig, Figure)
        assert len(fig.axes) >= 1

    def test_returns_figure_failing(self, failing_report):
        from app.gui.ct_saturation_plots import plot_level1_ansi
        fig = plot_level1_ansi(failing_report)
        assert isinstance(fig, Figure)

    def test_has_two_bars(self, passing_report):
        from app.gui.ct_saturation_plots import plot_level1_ansi
        fig = plot_level1_ansi(passing_report)
        ax = fig.axes[0]
        # 2 bars: V_tap + V_req
        bars = [
            p for p in ax.patches
            if hasattr(p, "get_height")
        ]
        assert len(bars) >= 2

    def test_bar_color_pass_when_passed(self, passing_report):
        """Barra 2 (requerido) deve ser VERDE quando passou."""
        from app.gui.ct_saturation_plots import plot_level1_ansi, COLOR_PASS
        fig = plot_level1_ansi(passing_report)
        ax = fig.axes[0]
        bars = [
            p for p in ax.patches
            if hasattr(p, "get_height") and hasattr(p, "get_facecolor")
        ]
        # Encontra barra do requerido (segunda barra ordenada por x)
        bars_sorted = sorted(bars, key=lambda b: b.get_x())
        req_bar = bars_sorted[1]
        rgba = req_bar.get_facecolor()
        for ref, got in zip(COLOR_PASS, rgba[:3]):
            assert abs(ref - got) < 0.05, (
                f"COLOR_PASS mismatch: ref={COLOR_PASS} got={rgba[:3]}"
            )

    def test_bar_color_fail_when_failed(self, failing_report):
        """Barra 2 (requerido) deve ser VERMELHA quando falhou."""
        from app.gui.ct_saturation_plots import plot_level1_ansi, COLOR_FAIL
        fig = plot_level1_ansi(failing_report)
        ax = fig.axes[0]
        bars = [
            p for p in ax.patches
            if hasattr(p, "get_height") and hasattr(p, "get_facecolor")
        ]
        bars_sorted = sorted(bars, key=lambda b: b.get_x())
        req_bar = bars_sorted[1]
        rgba = req_bar.get_facecolor()
        for ref, got in zip(COLOR_FAIL, rgba[:3]):
            assert abs(ref - got) < 0.05

    def test_has_tape_limit_line(self, passing_report):
        """yline(V_tap, 'k--') tracejada deve estar presente."""
        from app.gui.ct_saturation_plots import plot_level1_ansi
        fig = plot_level1_ansi(passing_report)
        ax = fig.axes[0]
        # axhline cria uma Line2D em ax.lines
        dashed_lines = [
            ln for ln in ax.lines
            if ln.get_linestyle() in ("--", "dashed")
        ]
        assert len(dashed_lines) >= 1, (
            "Esperava pelo menos 1 linha tracejada (limite tape)"
        )


# ===========================================================================
# Sprint B — plot_level2_iec
# ===========================================================================


class TestPlotLevel2Iec:

    def test_returns_figure(self, passing_report):
        from app.gui.ct_saturation_plots import plot_level2_iec
        fig = plot_level2_iec(passing_report)
        assert isinstance(fig, Figure)

    def test_axes_are_loglog(self, passing_report):
        from app.gui.ct_saturation_plots import plot_level2_iec
        fig = plot_level2_iec(passing_report)
        ax = fig.axes[0]
        assert ax.get_xscale() == "log"
        assert ax.get_yscale() == "log"

    def test_has_excitation_curve(self, passing_report):
        """Curva preta sólida da magnetização presente."""
        from app.gui.ct_saturation_plots import plot_level2_iec
        fig = plot_level2_iec(passing_report)
        ax = fig.axes[0]
        # Pelo menos 1 Line2D com vários pontos
        curve_lines = [
            ln for ln in ax.lines
            if len(ln.get_xdata()) > 3
        ]
        assert len(curve_lines) >= 1

    def test_has_knee_marker(self, passing_report):
        """Marcador joelho deve estar presente (verde 'o')."""
        from app.gui.ct_saturation_plots import plot_level2_iec
        fig = plot_level2_iec(passing_report)
        ax = fig.axes[0]
        # Procura por Line2D com marker 'o' (single point representado)
        markers = [
            ln for ln in ax.lines
            if ln.get_marker() in ("o", "x") and len(ln.get_xdata()) <= 2
        ]
        assert len(markers) >= 1, "Esperava marcador (joelho ou requerido)"

    def test_has_required_voltage_line(self, passing_report):
        """yline(Ek_req) — linha tracejada horizontal."""
        from app.gui.ct_saturation_plots import plot_level2_iec
        fig = plot_level2_iec(passing_report)
        ax = fig.axes[0]
        dashed = [
            ln for ln in ax.lines
            if ln.get_linestyle() in ("--", "dashed")
        ]
        assert len(dashed) >= 1


# ===========================================================================
# Sprint C — plot_level3_dynamic
# ===========================================================================


class TestPlotLevel3Dynamic:

    def test_returns_figure(self, passing_report):
        from app.gui.ct_saturation_plots import plot_level3_dynamic
        fig = plot_level3_dynamic(passing_report)
        assert isinstance(fig, Figure)

    def test_has_two_subplots(self, passing_report):
        """Subplot 1 (fluxo) + Subplot 2 (correntes)."""
        from app.gui.ct_saturation_plots import plot_level3_dynamic
        fig = plot_level3_dynamic(passing_report)
        assert len(fig.axes) == 2

    def test_subplot1_has_flux_curve(self, passing_report):
        """Curva de fluxo λ(t) preta sólida."""
        from app.gui.ct_saturation_plots import plot_level3_dynamic
        fig = plot_level3_dynamic(passing_report)
        ax1 = fig.axes[0]
        flux_lines = [
            ln for ln in ax1.lines
            if len(ln.get_xdata()) > 100   # curva ODE com muitos pontos
        ]
        assert len(flux_lines) >= 1

    def test_subplot2_has_two_current_lines(self, failing_report):
        """Subplot 2 deve ter ideal (vermelho tracejado) + real (azul sólido)."""
        from app.gui.ct_saturation_plots import plot_level3_dynamic
        fig = plot_level3_dynamic(failing_report)
        ax2 = fig.axes[1]
        long_lines = [
            ln for ln in ax2.lines
            if len(ln.get_xdata()) > 100
        ]
        assert len(long_lines) >= 2

    def test_subplot1_has_safe_zone_for_passing(self, passing_report):
        """Zona segura verde clara (axvspan = Polygon patch)."""
        from app.gui.ct_saturation_plots import plot_level3_dynamic
        fig = plot_level3_dynamic(passing_report)
        ax1 = fig.axes[0]
        polys = [
            p for p in ax1.patches
            if type(p).__name__ in ("Polygon", "Rectangle")
        ]
        assert len(polys) >= 1, "Esperava pelo menos 1 zona axvspan"

    def test_skipped_when_no_curve(self):
        """Se backend retornar status 'PULADO', plot mostra texto."""
        from app.gui.ct_saturation_plots import plot_level3_dynamic
        from app.postprocessor.ct_saturation import (
            CTSaturationReport, CTFaultContext, CTSpec, MagnetizationCurve,
            Level1AnsiResult, Level3DynamicResult,
        )
        # Curva mínima válida (apenas 2 pontos exigidos pelo dataclass)
        # mas Level3 retorna PULADO via construção manual.
        fault = CTFaultContext(
            bus_id="X", rated_voltage_kV=13.8,
            I_fault_rms_kA=20.0, X_over_R=10.0,
        )
        ct = CTSpec(
            tag="X", tipo_TC="ANSI_C",
            I_pri_nom_tap=1000, I_pri_nom_full=1000, I_sn=5,
            CT_Rating_C=400.0, R_s=0.5, R_b=0.3,
            curve=MagnetizationCurve(Ie=(0.01, 1.0), Ve=(40.0, 400.0)),
        )
        l1 = Level1AnsiResult(
            V_tap=400.0, V_req=200.0, passed=True,
            recommended_class_C="C200",
        )
        l3_skip = Level3DynamicResult(
            t_sat_ms=float("inf"),
            sat_at_trip_pct=0.0,
            sat_peak_pct=0.0,
            margin_ms=0.0,
            status="PULADO (curva ausente)",
        )
        report = CTSaturationReport(
            ct=ct, fault=fault,
            level1=l1, level2=None, level3=l3_skip,
            final_status="PULADO",
            final_detail="teste",
        )
        # Não deve crashar mesmo com PULADO
        fig = plot_level3_dynamic(report)
        assert isinstance(fig, Figure)
