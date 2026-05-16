"""
tests/test_pp_v0_60_streaming.py — v0.60 live stdout
streaming durante execução assíncrona ATP.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest


PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# AtpRunner stream support
# ---------------------------------------------------------------------------


class TestRunnerStreaming:

    def test_run_accepts_callbacks(self):
        """run(stdout_callback=, stderr_callback=) aceito."""
        from app.simulation.runner import AtpRunner
        runner = AtpRunner()  # sem executable
        # Sem ATP configurado → retorna RunResult com erro
        # mas a CHAMADA com callbacks não pode crashar
        result = runner.run(
            "fake.atp",
            stdout_callback=lambda line: None,
            stderr_callback=lambda line: None,
        )
        assert result.success is False

    def test_stream_subprocess_helper_exists(self):
        """_stream_subprocess método existe."""
        from app.simulation.runner import AtpRunner
        runner = AtpRunner()
        assert hasattr(runner, "_stream_subprocess")

    def test_stream_with_real_subprocess(self, tmp_path):
        """
        Smoke: subprocess que imprime 3 linhas → callback recebe 3.
        Usa Python como subprocess (sempre disponível).
        """
        import subprocess
        from app.simulation.runner import AtpRunner

        proc = subprocess.Popen(
            [sys.executable, "-u", "-c",
             "import sys; "
             "[sys.stdout.write(f'line {i}\\n') or sys.stdout.flush() "
             "for i in range(3)]"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # v0.91.2: removido bufsize=1 (não funciona em binário).
            # ``-u`` no python child + flush() já garantem
            # line-by-line output.
        )

        captured = []
        runner = AtpRunner()
        stdout_b, stderr_b = runner._stream_subprocess(
            proc, timeout=10,
            stdout_callback=lambda l: captured.append(l),
        )
        # 3 linhas devem ter sido capturadas
        assert len(captured) == 3
        assert captured[0] == "line 0"
        assert captured[2] == "line 2"


# ---------------------------------------------------------------------------
# AtpRunWorker streaming signals
# ---------------------------------------------------------------------------


class TestWorkerStreamingSignals:

    def test_stdout_line_signal_exists(self, qapp):
        from app.gui.async_runner import AtpRunWorker
        from app.simulation.runner import AtpRunner
        worker = AtpRunWorker(AtpRunner(), "fake.atp")
        # Signal stdout_line existe (Signal type)
        assert hasattr(worker, "stdout_line")
        assert hasattr(worker, "stderr_line")

    def test_signals_fire_on_run(self, qapp):
        """
        Mock runner que chama stdout_callback 2x → worker.run()
        emite stdout_line cobrindo as 2 linhas.

        v0.91.2: worker agora agrega linhas via ``_LineBatcher``
        (throttle 100 ms / max 50 linhas) antes do emit. Linhas
        consecutivas em rápida sucessão são concatenadas num
        único emit. Validamos que TODAS as linhas chegam,
        independente do batching.
        """
        from app.gui.async_runner import AtpRunWorker
        from app.simulation.runner import RunResult

        class MockRunner:
            def run(self, path, timeout=None, *,
                    stdout_callback=None, stderr_callback=None,
                    phase_callback=None):    # v0.91.5
                if stdout_callback:
                    # v0.91.2: lines com \n (production-like —
                    # readline() inclui o newline).
                    stdout_callback("line 1\n")
                    stdout_callback("line 2\n")
                if stderr_callback:
                    stderr_callback("warn 1\n")
                return RunResult(
                    success=True, return_code=0,
                    stdout="...", stderr="...",
                    message="OK", run_dir="", log_file="",
                )

        worker = AtpRunWorker(MockRunner(), "fake.atp")
        captured_out: list[str] = []
        captured_err: list[str] = []
        worker.stdout_line.connect(captured_out.append)
        worker.stderr_line.connect(captured_err.append)
        worker.run()
        # Após flush final: pelo menos 1 emit por stream contendo
        # TODAS as linhas (concatenadas em chunk(s)).
        joined_out = "".join(captured_out)
        assert "line 1" in joined_out
        assert "line 2" in joined_out
        joined_err = "".join(captured_err)
        assert "warn 1" in joined_err


# ---------------------------------------------------------------------------
# Console panel integration (signal forwarding)
# ---------------------------------------------------------------------------


class TestConsoleStreamingIntegration:

    def test_main_window_wires_streaming(self, qapp):
        """
        MainWindow conecta worker.stdout_line ao console.
        Validamos que o método _on_run_atp existe e que
        console panel está pronto.
        """
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            assert hasattr(mw, "_console_panel")
            assert hasattr(mw, "_on_run_atp")
        finally:
            mw.close()
