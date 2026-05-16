"""
tests/test_pp_v0_33_0_examples.py — v0.33.0:
Exemplos executáveis das normas.

Cobre:

* ExampleResult dataclass + helpers
* Cada exemplo: run() retorna ExampleResult VÁLIDO
* Cada exemplo: PASSED == True (dentro da tolerância)
* Registry populado com 6 exemplos
* GUI menu Exemplos populado
"""

from __future__ import annotations

import pytest

from app.examples import ExampleResult, _check_tolerance


# ---------------------------------------------------------------------------
# ExampleResult dataclass
# ---------------------------------------------------------------------------


class TestExampleResult:

    def test_basic_result(self):
        r = ExampleResult(
            title="Test",
            reference="Ref",
            expected={"x": 10.0},
            computed={"x": 10.0},
            tolerance_pct=5.0,
            passed=True,
            narrative="ok",
        )
        assert r.title == "Test"
        assert r.passed

    def test_summary_includes_status(self):
        r = ExampleResult(
            title="Test",
            reference="Ref",
            expected={"v": 1.0},
            computed={"v": 1.001},
            tolerance_pct=5.0,
            passed=True,
            narrative="ok",
        )
        text = r.summary()
        assert "PASS" in text
        assert "Test" in text
        assert "Ref" in text


class TestCheckTolerance:

    def test_within_tolerance(self):
        assert _check_tolerance(
            {"v": 100.0}, {"v": 102.0}, 5.0,
        ) is True

    def test_exceeds_tolerance(self):
        assert _check_tolerance(
            {"v": 100.0}, {"v": 110.0}, 5.0,
        ) is False

    def test_missing_key(self):
        assert _check_tolerance(
            {"x": 1.0}, {}, 5.0,
        ) is False

    def test_zero_expected(self):
        assert _check_tolerance(
            {"v": 0.0}, {"v": 0.001}, 5.0,
        ) is True


# ---------------------------------------------------------------------------
# Each example runs and PASSes
# ---------------------------------------------------------------------------


class TestExamplesRun:

    def test_stevenson_pf_3bus(self):
        np = pytest.importorskip("numpy")
        from app.examples.stevenson_pf_3bus import run
        result = run()
        assert isinstance(result, ExampleResult)
        assert result.passed, (
            f"Stevenson PF 3-bus FAIL:\n{result.summary()}"
        )

    def test_stevenson_sequential(self):
        from app.examples.stevenson_sequential import run
        result = run()
        assert isinstance(result, ExampleResult)
        assert result.passed, (
            f"Stevenson Sequential FAIL:\n{result.summary()}"
        )

    def test_iec60909_annex_c(self):
        from app.examples.iec60909_annex_c import run
        result = run()
        assert isinstance(result, ExampleResult)
        assert result.passed, (
            f"IEC 60909 Annex C FAIL:\n{result.summary()}"
        )

    def test_ieee1584_ex_d2(self):
        from app.examples.ieee1584_ex_d2 import run
        result = run()
        assert isinstance(result, ExampleResult)
        assert result.passed, (
            f"IEEE 1584 D.2 FAIL:\n{result.summary()}"
        )

    def test_ieee399_motor_starting(self):
        from app.examples.ieee399_motor_starting import run
        result = run()
        assert isinstance(result, ExampleResult)
        assert result.passed, (
            f"IEEE 399 Motor Starting FAIL:\n{result.summary()}"
        )

    def test_nbr17227_example(self):
        from app.examples.nbr17227_example import run
        result = run()
        assert isinstance(result, ExampleResult)
        assert result.passed, (
            f"NBR 17227 FAIL:\n{result.summary()}"
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:

    def test_registry_has_six_examples(self):
        from app.examples.registry import EXAMPLES
        assert len(EXAMPLES) == 6

    def test_all_entries_have_required_fields(self):
        from app.examples.registry import EXAMPLES
        for ex in EXAMPLES:
            assert ex.id
            assert ex.label
            assert ex.description
            assert ex.reference
            assert callable(ex.runner)

    def test_get_example_by_id(self):
        from app.examples.registry import (
            EXAMPLES, get_example_by_id,
        )
        first = EXAMPLES[0]
        retrieved = get_example_by_id(first.id)
        assert retrieved is first

    def test_get_example_unknown_returns_none(self):
        from app.examples.registry import get_example_by_id
        assert get_example_by_id("__xyz__") is None

    def test_each_example_id_unique(self):
        from app.examples.registry import EXAMPLES
        ids = [ex.id for ex in EXAMPLES]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# GUI menu Examples
# ---------------------------------------------------------------------------


class TestExamplesMenuInGui:

    def test_examples_menu_present(self):
        PySide6 = pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QApplication, QMenu
        app = QApplication.instance() or QApplication([])
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            menus = mw.menuBar().findChildren(QMenu)
            ex_menu = next(
                (m for m in menus if m.title() == "Exemplos"), None,
            )
            assert ex_menu is not None
            # Deve ter 6 actions (uma por exemplo)
            actions = [a for a in ex_menu.actions() if a.text()]
            assert len(actions) == 6
        finally:
            mw.close()
