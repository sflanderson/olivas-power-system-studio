"""v3.6.2 — Categoria D TCC visual polish (D.1 + D.2) tests.

Closes SKIPPED_BACKLOG D.1 (C-lines paint real) + D.2 (multi-protection
plot Phase/Ground). Reference: PTW Tutorial §Part 5 p.163-165 (D.1) +
§Part 11 p.357-360 (D.2).

Tests cobrem:
* D.1.1 — set_c_lines() armazena lista
* D.1.2 — get_c_lines() retorna cópia
* D.1.3 — _draw_c_lines() converte kA → A (axis consistency)
* D.1.4 — empty c_lines não causa erro
* D.2.1 — set_protection_filter() valida modo
* D.2.2 — get_protection_filter() retorna estado atual
* D.2.3 — _curve_matches_protection heurística (phase/ground/all)
* D.2.4 — Combo na GUI dialog wires _on_protection_filter_changed
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    return app


# ---------------------------------------------------------------------------
# Stub minimal CLineCurve (avoids import dependencies)
# ---------------------------------------------------------------------------


@dataclass
class _StubCLine:
    """Minimal CLineCurve stub (matches duck-typed API)."""
    incident_energy_cal_cm2: float
    points: tuple
    ppe_category: Optional[int] = None
    color_hint: str = "#ff8c00"


@dataclass
class _StubCurveWithFunction:
    """Stub curve with `function` attribute for protection filter test."""
    function: str
    name: str = "TestCurve"


# ---------------------------------------------------------------------------
# D.1 — C-lines API
# ---------------------------------------------------------------------------


class TestCLinesAPI:
    """v3.6.2 D.1 closure — set_c_lines/get_c_lines/_draw_c_lines."""

    def test_set_c_lines_stores_list(self, qapp) -> None:
        from app.gui.tcc_coordinogram import TCCCoordinogramWidget
        from app.postprocessor.tcc_curves import TCCCurve, CurveType
        w = TCCCoordinogramWidget(
            curves=[TCCCurve("X", CurveType.IEC_STANDARD_INVERSE,
                             pickup_A=100, tms=0.1)],
        )
        c = _StubCLine(1.2, ((1.0, 0.5), (10.0, 0.05)), ppe_category=1)
        w.set_c_lines([c])
        assert len(w.get_c_lines()) == 1
        assert w.get_c_lines()[0].incident_energy_cal_cm2 == 1.2

    def test_get_c_lines_returns_copy(self, qapp) -> None:
        from app.gui.tcc_coordinogram import TCCCoordinogramWidget
        from app.postprocessor.tcc_curves import TCCCurve, CurveType
        w = TCCCoordinogramWidget(
            curves=[TCCCurve("X", CurveType.IEC_STANDARD_INVERSE,
                             pickup_A=100, tms=0.1)],
        )
        w.set_c_lines([_StubCLine(4.0, ((2.0, 0.3),))])
        copy = w.get_c_lines()
        copy.append("garbage")
        # Internal state untouched
        assert len(w.get_c_lines()) == 1

    def test_set_c_lines_empty_clears(self, qapp) -> None:
        from app.gui.tcc_coordinogram import TCCCoordinogramWidget
        from app.postprocessor.tcc_curves import TCCCurve, CurveType
        w = TCCCoordinogramWidget(
            curves=[TCCCurve("X", CurveType.IEC_STANDARD_INVERSE,
                             pickup_A=100, tms=0.1)],
        )
        w.set_c_lines([_StubCLine(1.2, ((1.0, 0.5),))])
        w.set_c_lines([])
        assert w.get_c_lines() == []

    def test_set_c_lines_none_safe(self, qapp) -> None:
        from app.gui.tcc_coordinogram import TCCCoordinogramWidget
        from app.postprocessor.tcc_curves import TCCCurve, CurveType
        w = TCCCoordinogramWidget(
            curves=[TCCCurve("X", CurveType.IEC_STANDARD_INVERSE,
                             pickup_A=100, tms=0.1)],
        )
        w.set_c_lines(None)  # type: ignore[arg-type]
        assert w.get_c_lines() == []

    def test_draw_c_lines_converts_ka_to_a(self, qapp) -> None:
        """C-lines points are in kA; verify _draw_c_lines multiplies by 1000."""
        from app.gui.tcc_coordinogram import TCCCoordinogramWidget
        from app.postprocessor.tcc_curves import TCCCurve, CurveType
        w = TCCCoordinogramWidget(
            curves=[TCCCurve("X", CurveType.IEC_STANDARD_INVERSE,
                             pickup_A=100, tms=0.1)],
        )
        # 1 kA at 0.5s
        c = _StubCLine(1.2, ((1.0, 0.5), (10.0, 0.05)), ppe_category=1)
        w.set_c_lines([c])
        # set_c_lines triggers _draw_all → _draw_c_lines
        # No exception → conversion working. We can also inspect the
        # axis lines manually:
        ax = w._ax
        # Filter to dashed lines (C-lines style)
        dashed_lines = [
            ln for ln in ax.get_lines()
            if ln.get_linestyle() in ("--", "dashed")
        ]
        # Confirm at least one C-line line was drawn
        assert len(dashed_lines) >= 1
        # First C-line x[0] should be 1.0 kA × 1000 = 1000 A
        x_data = dashed_lines[0].get_xdata()
        assert abs(x_data[0] - 1000.0) < 0.01


# ---------------------------------------------------------------------------
# D.2 — Protection filter API
# ---------------------------------------------------------------------------


class TestProtectionFilter:
    """v3.6.2 D.2 closure — set_protection_filter + heuristic."""

    def test_set_protection_filter_valid_modes(self, qapp) -> None:
        from app.gui.tcc_coordinogram import TCCCoordinogramWidget
        from app.postprocessor.tcc_curves import TCCCurve, CurveType
        w = TCCCoordinogramWidget(
            curves=[TCCCurve("X", CurveType.IEC_STANDARD_INVERSE,
                             pickup_A=100, tms=0.1)],
        )
        for mode in ("all", "phase", "ground"):
            w.set_protection_filter(mode)
            assert w.get_protection_filter() == mode

    def test_set_protection_filter_invalid_raises(self, qapp) -> None:
        from app.gui.tcc_coordinogram import TCCCoordinogramWidget
        from app.postprocessor.tcc_curves import TCCCurve, CurveType
        w = TCCCoordinogramWidget(
            curves=[TCCCurve("X", CurveType.IEC_STANDARD_INVERSE,
                             pickup_A=100, tms=0.1)],
        )
        with pytest.raises(ValueError, match="mode must be"):
            w.set_protection_filter("invalid")

    def test_curve_matches_all_always_true(self, qapp) -> None:
        from app.gui.tcc_coordinogram import TCCCoordinogramWidget
        c = _StubCurveWithFunction(function="50/51")
        assert TCCCoordinogramWidget._curve_matches_protection(c, "all") is True

    def test_curve_matches_phase_excludes_ground(self, qapp) -> None:
        from app.gui.tcc_coordinogram import TCCCoordinogramWidget
        c_phase = _StubCurveWithFunction(function="50/51")
        c_ground = _StubCurveWithFunction(function="50N/51N")
        assert TCCCoordinogramWidget._curve_matches_protection(c_phase, "phase") is True
        assert TCCCoordinogramWidget._curve_matches_protection(c_ground, "phase") is False

    def test_curve_matches_ground_includes_neutral(self, qapp) -> None:
        from app.gui.tcc_coordinogram import TCCCoordinogramWidget
        c_neutral = _StubCurveWithFunction(function="Neutral OC")
        c_terra = _StubCurveWithFunction(function="Terra")
        assert TCCCoordinogramWidget._curve_matches_protection(c_neutral, "ground") is True
        assert TCCCoordinogramWidget._curve_matches_protection(c_terra, "ground") is True

    def test_curve_no_function_info_always_shown(self, qapp) -> None:
        """Curves without function/ansi/name/label info default to visible
        (anti-data-loss: don't hide silently)."""
        from app.gui.tcc_coordinogram import TCCCoordinogramWidget

        class BareStub:
            pass

        c = BareStub()
        assert TCCCoordinogramWidget._curve_matches_protection(c, "phase") is True
        assert TCCCoordinogramWidget._curve_matches_protection(c, "ground") is True


# ---------------------------------------------------------------------------
# Acessibilidade GUI (Master Protocol garantia 7ª)
# ---------------------------------------------------------------------------


def test_dialog_wires_protection_filter_combo() -> None:
    """Verify TCCCoordinogramDialog wires combo to handler."""
    import inspect
    from app.gui import tcc_coordinogram

    src = inspect.getsource(tcc_coordinogram)
    assert "_cmb_protection_filter" in src
    assert "_on_protection_filter_changed" in src
    assert "Phase (50/51)" in src
    assert "Ground (50N/51N)" in src


def test_widget_init_default_filter_is_all(qapp) -> None:
    from app.gui.tcc_coordinogram import TCCCoordinogramWidget
    from app.postprocessor.tcc_curves import TCCCurve, CurveType
    w = TCCCoordinogramWidget(
        curves=[TCCCurve("X", CurveType.IEC_STANDARD_INVERSE,
                         pickup_A=100, tms=0.1)],
    )
    assert w.get_protection_filter() == "all"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
