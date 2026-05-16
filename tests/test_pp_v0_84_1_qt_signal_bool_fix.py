"""
tests/test_pp_v0_84_1_qt_signal_bool_fix.py — v0.84.1:

Regression: ``QAction.triggered`` emits ``bool checked`` como
primeiro argumento posicional. Quando handlers ``_on_analyze_*``
são conectados via ``addAction(text, slot)`` ou
``triggered.connect(slot)``, esse bool antes sobrescrevia
``project=None`` → AttributeError ``'bool' object has no
attribute 'components'`` em ``run_*_analysis``.

Fix: ``*_qt_args`` absorve qualquer arg posicional que Qt
injetar; ``project``/``bus_id`` viram keyword-only.
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Os 5 handlers de _on_analyze_* aceitam o bool posicional do Qt
# sem que ele contamine o kwarg ``project``.
# ---------------------------------------------------------------------------


class TestQtSignalBoolAbsorption:

    def test_bus_pipeline_handles_qt_bool(self, qapp, monkeypatch):
        """Simula ``triggered.emit(False)`` chamando o handler com
        ``False`` como primeiro arg posicional. NÃO deve crashar
        com 'bool object has no attribute components'."""
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            # Mock run_bus_pipeline_analysis para capturar project
            captured = {}
            import app.gui.analysis_dialogs as ad
            monkeypatch.setattr(
                ad, "run_bus_pipeline_analysis",
                lambda *args, **kw: captured.update(kw),
            )
            # Simula Qt: handler recebe False posicional.
            mw._on_analyze_bus_pipeline(False)
            # Project deve ter sido resolvido via _current_pp_project,
            # NÃO ficou como False.
            assert captured.get("project") is not False
        finally:
            mw.close()

    def test_short_circuit_handles_qt_bool(self, qapp, monkeypatch):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            captured = {}
            import app.gui.analysis_dialogs as ad
            monkeypatch.setattr(
                ad, "run_short_circuit_analysis",
                lambda *args, **kw: captured.update(kw),
            )
            mw._on_analyze_short_circuit(False)
            assert captured.get("project") is not False
        finally:
            mw.close()

    def test_power_flow_handles_qt_bool(self, qapp, monkeypatch):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            captured = {}
            import app.gui.analysis_dialogs as ad
            monkeypatch.setattr(
                ad, "run_power_flow_analysis",
                lambda *args, **kw: captured.update(kw),
            )
            mw._on_analyze_power_flow(False)
            assert captured.get("project") is not False
        finally:
            mw.close()

    def test_motor_starting_handles_qt_bool(self, qapp, monkeypatch):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            captured = {}
            import app.gui.analysis_dialogs as ad
            monkeypatch.setattr(
                ad, "run_motor_starting_analysis",
                lambda *args, **kw: captured.update(kw),
            )
            mw._on_analyze_motor_starting(False)
            assert captured.get("project") is not False
        finally:
            mw.close()

    def test_arc_flash_handles_qt_bool(self, qapp, monkeypatch):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            captured = {}
            import app.gui.analysis_dialogs as ad
            monkeypatch.setattr(
                ad, "run_arc_flash_analysis",
                lambda *args, **kw: captured.update(kw),
            )
            mw._on_analyze_arc_flash(False)
            assert captured.get("project") is not False
        finally:
            mw.close()


# ---------------------------------------------------------------------------
# Callers internos via kwargs continuam funcionando (RunAnalysisDialog,
# _dispatch_analysis).
# ---------------------------------------------------------------------------


class TestKwargCallersStillWork:

    def test_dispatch_analysis_pipeline_with_kwarg(self, qapp, monkeypatch):
        """``_dispatch_analysis`` chama com ``project=`` por keyword;
        deve receber o project intacto (não o bool)."""
        from app.gui.main_window import MainWindow
        from app.preprocessor.models import PpProject
        mw = MainWindow()
        try:
            captured = {}
            import app.gui.analysis_dialogs as ad
            monkeypatch.setattr(
                ad, "run_bus_pipeline_analysis",
                lambda *args, **kw: captured.update(kw),
            )
            project = PpProject()
            mw._dispatch_analysis(
                kind="pipeline", bus_id="B1", pp_project=project,
            )
            assert captured.get("project") is project
            assert captured.get("bus_id") == "B1"
        finally:
            mw.close()

    def test_direct_handler_call_with_kwarg(self, qapp, monkeypatch):
        """Chamada direta com kwarg ``project=`` é honrada."""
        from app.gui.main_window import MainWindow
        from app.preprocessor.models import PpProject
        mw = MainWindow()
        try:
            captured = {}
            import app.gui.analysis_dialogs as ad
            monkeypatch.setattr(
                ad, "run_short_circuit_analysis",
                lambda *args, **kw: captured.update(kw),
            )
            project = PpProject()
            mw._on_analyze_short_circuit(
                project=project, bus_id="BUS-1",
            )
            assert captured.get("project") is project
            assert captured.get("bus_id") == "BUS-1"
        finally:
            mw.close()
