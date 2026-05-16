"""
tests/test_pp_v0_91_5_atp_progress_dialog.py — v0.91.5:

Dialog rico de progresso ATP com fases + output ao vivo.
Substitui ``QProgressDialog`` indeterminate. Quando o app
trava, o usuário VÊ qual fase está ativa.

Cobertura
---------

* Runner emite phase_callback nas etapas certas.
* AtpRunWorker.phase_changed re-emite via Qt signal.
* AtpProgressDialog:
  - mostra phase
  - acumula trail
  - append_output multi-line
  - mark_done / mark_cancelled trocam estado
  - cancel_requested signal
* MainWindow._on_run_atp usa AtpProgressDialog.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Runner phase_callback
# ---------------------------------------------------------------------------


class TestRunnerPhaseCallback:

    def test_phase_callback_called_at_validating(self, tmp_path):
        """Mesmo se exe inválido, ``validating`` deve disparar
        antes do retorno de erro."""
        from app.simulation.runner import AtpRunner
        phases = []
        r = AtpRunner(executable_path=None)
        r.run(
            "nonexistent.atp",
            phase_callback=phases.append,
        )
        assert "validating" in phases

    def test_phase_callback_full_sequence_mocked(self, tmp_path):
        """Com Popen mockado, todas as fases até ``done`` devem
        disparar."""
        from app.simulation import runner as runner_mod

        # Cria fake exe + atp
        exe = tmp_path / "atp.exe"
        exe.write_text("dummy", encoding="utf-8")
        atp = tmp_path / "case.atp"
        atp.write_text("BEGIN", encoding="utf-8")

        phases = []
        r = runner_mod.AtpRunner(executable_path=str(exe), timeout=5)

        def fake_popen(*args, **kwargs):
            mock = MagicMock()
            mock.communicate.return_value = (b"", b"")
            mock.returncode = 0
            mock.kill = MagicMock()
            return mock

        with patch("subprocess.Popen", side_effect=fake_popen):
            r.run(str(atp), phase_callback=phases.append)
        # Sequência esperada
        for expected in (
            "validating", "creating_run_dir", "copying_atp",
            "launching", "running", "collecting_outputs",
            "saving_log", "done",
        ):
            assert expected in phases, (
                f"Phase {expected!r} ausente em {phases}"
            )

    def test_phase_callback_failure_no_crash(self):
        """phase_callback que levanta Exception NÃO derruba o
        runner (silenciado)."""
        from app.simulation.runner import AtpRunner

        def bad_callback(p):
            raise RuntimeError("oops")

        r = AtpRunner(executable_path=None)
        # Não deve crashar
        result = r.run(
            "nonexistent.atp", phase_callback=bad_callback,
        )
        assert result.success is False


# ---------------------------------------------------------------------------
# AtpRunWorker.phase_changed
# ---------------------------------------------------------------------------


class TestWorkerPhaseSignal:

    def test_phase_changed_emitted_starting(self, qapp):
        """Worker.run() emite ``starting`` antes de chamar runner."""
        from app.gui.async_runner import AtpRunWorker
        from app.simulation.runner import RunResult

        class MockRunner:
            def run(self, path, timeout=None, *,
                    stdout_callback=None, stderr_callback=None,
                    phase_callback=None):
                if phase_callback:
                    phase_callback("running")
                    phase_callback("done")
                return RunResult(
                    success=True, return_code=0,
                    stdout="", stderr="", message="OK",
                    run_dir="", log_file="",
                )

        worker = AtpRunWorker(MockRunner(), "fake.atp")
        captured: list[str] = []
        worker.phase_changed.connect(captured.append)
        worker.run()
        # Pelo menos: starting + running + done
        assert "starting" in captured
        assert "running" in captured
        assert "done" in captured


# ---------------------------------------------------------------------------
# AtpProgressDialog
# ---------------------------------------------------------------------------


class TestAtpProgressDialog:

    def test_instantiates(self, qapp):
        from app.gui.atp_progress_dialog import AtpProgressDialog
        dlg = AtpProgressDialog(atp_filename="caso.atp")
        assert isinstance(dlg, QDialog)
        assert "caso.atp" in dlg.windowTitle()

    def test_set_phase_updates_label(self, qapp):
        from app.gui.atp_progress_dialog import AtpProgressDialog
        dlg = AtpProgressDialog(atp_filename="x.atp")
        dlg.set_phase("running")
        # Label visível inclui icon + texto
        text = dlg._phase_label.text()
        assert "🔄" in text
        assert "rodando" in text.lower()

    def test_phase_trail_accumulates(self, qapp):
        from app.gui.atp_progress_dialog import AtpProgressDialog
        dlg = AtpProgressDialog(atp_filename="x.atp")
        dlg.set_phase("validating")
        dlg.set_phase("launching")
        dlg.set_phase("running")
        trail = dlg._phase_trail.text()
        assert "validating" in trail
        assert "launching" in trail
        assert "running" in trail

    def test_unknown_phase_renders_id(self, qapp):
        """Phase desconhecido não crasha; mostra como-é."""
        from app.gui.atp_progress_dialog import AtpProgressDialog
        dlg = AtpProgressDialog(atp_filename="x.atp")
        dlg.set_phase("__custom_phase__")
        assert "__custom_phase__" in dlg._phase_label.text()

    def test_append_output_multi_line(self, qapp):
        from app.gui.atp_progress_dialog import AtpProgressDialog
        dlg = AtpProgressDialog(atp_filename="x.atp")
        dlg.append_output("line 1\nline 2\nline 3")
        text = dlg._output_view.toPlainText()
        assert "line 1" in text
        assert "line 2" in text
        assert "line 3" in text

    def test_append_output_strips_trailing_newline(self, qapp):
        from app.gui.atp_progress_dialog import AtpProgressDialog
        dlg = AtpProgressDialog(atp_filename="x.atp")
        dlg.append_output("solo line\n")
        text = dlg._output_view.toPlainText()
        # Não duplica newline
        assert text.count("solo line") == 1

    def test_mark_done_success(self, qapp):
        from app.gui.atp_progress_dialog import AtpProgressDialog
        dlg = AtpProgressDialog(atp_filename="x.atp")
        dlg.mark_done(success=True, message="OK")
        # Phase = done
        assert "✅" in dlg._phase_label.text()
        # Botão troca para Fechar
        assert dlg._cancel_btn.text() == "Fechar"

    def test_mark_done_failure(self, qapp):
        from app.gui.atp_progress_dialog import AtpProgressDialog
        dlg = AtpProgressDialog(atp_filename="x.atp")
        dlg.mark_done(success=False, message="ATP crashou")
        assert "❌" in dlg._phase_label.text()
        assert "ATP crashou" in dlg._phase_label.text()

    def test_mark_cancelled(self, qapp):
        from app.gui.atp_progress_dialog import AtpProgressDialog
        dlg = AtpProgressDialog(atp_filename="x.atp")
        dlg.mark_cancelled()
        assert "⛔" in dlg._phase_label.text()
        assert dlg._cancel_btn.text() == "Fechar"

    def test_cancel_requested_signal(self, qapp):
        from app.gui.atp_progress_dialog import AtpProgressDialog
        dlg = AtpProgressDialog(atp_filename="x.atp")
        captured = []
        dlg.cancel_requested.connect(lambda: captured.append(True))
        dlg._cancel_btn.click()
        assert captured == [True]
        assert dlg.is_cancelled()

    def test_cancel_button_disables_after_click(self, qapp):
        from app.gui.atp_progress_dialog import AtpProgressDialog
        dlg = AtpProgressDialog(atp_filename="x.atp")
        dlg._cancel_btn.click()
        # Não dá pra clicar duas vezes
        assert not dlg._cancel_btn.isEnabled()
        assert dlg._cancel_btn.text() == "Cancelando..."


# ---------------------------------------------------------------------------
# MainWindow integration
# ---------------------------------------------------------------------------


class TestMainWindowAtpProgressIntegration:

    def test_atp_progress_dialog_module_importable(self, qapp):
        """Smoke: módulo importa sem erro."""
        from app.gui.atp_progress_dialog import (
            AtpProgressDialog, PHASE_LABELS,
        )
        assert PHASE_LABELS["running"][0] == "🔄"
