"""
tests/test_pp_v0_91_2_atp_runner_hotfix.py — v0.91.2:

Hotfix do GUI freeze durante simulação ATP longa.

Sintoma original: Qt mostrava "Simulação ATP (Not Responding)"
durante simulações com saída maciça (centenas de linhas/seg
em ATP de portes industriais como ``trt_all_motors_dt_ea.atp``).
Causa: cada linha → cross-thread signal emit → main thread
saturado → progress dialog freezed.

Fix:

1. ``_LineBatcher`` agrega linhas no worker thread
   antes de emit (throttle 100 ms / max 50 linhas).
2. Removido ``bufsize=1`` no ``Popen`` (binário) → silencia
   ``RuntimeWarning``.

Cobertura
---------

* ``_LineBatcher`` agrega linhas até flush time / count.
* ``_LineBatcher.flush`` emite chunk único.
* ``_LineBatcher.flush`` em buffer vazio é no-op.
* Runner.Popen sem ``bufsize=1``.
* Worker emite chunk concatenando linhas mesmo com 1000 linhas
  rápidas (smoke / no flooding).
"""

from __future__ import annotations

import time

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# _LineBatcher
# ---------------------------------------------------------------------------


class TestLineBatcher:

    def test_batches_until_max_lines(self):
        from app.gui.async_runner import _LineBatcher
        emitted: list[str] = []
        b = _LineBatcher(
            emit_fn=emitted.append,
            interval_ms=100_000,    # nunca dispara por tempo
            max_lines=3,
        )
        b.push("a\n")
        b.push("b\n")
        # Não dispara ainda
        assert emitted == []
        b.push("c\n")
        # Dispara ao atingir max_lines
        assert emitted == ["a\nb\nc\n"]

    def test_batches_until_interval(self):
        from app.gui.async_runner import _LineBatcher
        emitted: list[str] = []
        b = _LineBatcher(
            emit_fn=emitted.append,
            interval_ms=50,
            max_lines=10_000,
        )
        b.push("first\n")
        # Antes do intervalo: nada emitido
        assert emitted == []
        # Espera mais que o intervalo
        time.sleep(0.08)
        b.push("after-sleep\n")
        # Push após sleep dispara flush
        assert len(emitted) == 1
        assert "first" in emitted[0]
        assert "after-sleep" in emitted[0]

    def test_flush_empty_is_noop(self):
        from app.gui.async_runner import _LineBatcher
        emitted: list[str] = []
        b = _LineBatcher(emit_fn=emitted.append)
        b.flush()
        assert emitted == []

    def test_flush_emits_pending(self):
        from app.gui.async_runner import _LineBatcher
        emitted: list[str] = []
        b = _LineBatcher(
            emit_fn=emitted.append,
            interval_ms=100_000,
            max_lines=10_000,
        )
        b.push("x\n")
        b.push("y\n")
        # Nada emitido ainda
        assert emitted == []
        b.flush()
        assert emitted == ["x\ny\n"]

    def test_emit_failure_silenced(self):
        """Se o slot Qt foi desconectado, emit pode raise. Não crash."""
        from app.gui.async_runner import _LineBatcher

        def _raising_emit(_chunk):
            raise RuntimeError("disconnected")

        b = _LineBatcher(
            emit_fn=_raising_emit,
            interval_ms=10,
            max_lines=10_000,
        )
        b.push("x\n")
        time.sleep(0.02)
        # Push triggers flush which calls _raising_emit; não crash
        b.push("y\n")


# ---------------------------------------------------------------------------
# Worker stdout/stderr aggregation
# ---------------------------------------------------------------------------


class TestWorkerThrottling:

    def test_thousand_lines_no_flood(self, qapp):
        """1000 linhas rapidamente → muito menos que 1000 emits."""
        from app.gui.async_runner import AtpRunWorker
        from app.simulation.runner import RunResult

        class MockRunner:
            def run(self, path, timeout=None, *,
                    stdout_callback=None, stderr_callback=None,
                    phase_callback=None):    # v0.91.5
                if stdout_callback:
                    for i in range(1000):
                        stdout_callback(f"line {i}\n")
                return RunResult(
                    success=True, return_code=0,
                    stdout="", stderr="",
                    message="OK", run_dir="", log_file="",
                )

        worker = AtpRunWorker(MockRunner(), "fake.atp")
        captured: list[str] = []
        worker.stdout_line.connect(captured.append)
        worker.run()
        # Throttle: max 50 linhas por chunk → mín 20 emits.
        # Mas todas as 1000 linhas devem estar presentes no
        # somatório.
        assert len(captured) <= 100, (
            f"emits demais ({len(captured)}) — throttle quebrado"
        )
        joined = "".join(captured)
        assert "line 0" in joined
        assert "line 999" in joined
        # Conta linhas no joined
        assert joined.count("\n") == 1000

    def test_lines_preserved_in_order(self, qapp):
        """Ordem das linhas preservada apesar do batching."""
        from app.gui.async_runner import AtpRunWorker
        from app.simulation.runner import RunResult

        class MockRunner:
            def run(self, path, timeout=None, *,
                    stdout_callback=None, stderr_callback=None,
                    phase_callback=None):    # v0.91.5
                if stdout_callback:
                    for s in ("alfa", "beta", "gamma", "delta"):
                        stdout_callback(s + "\n")
                return RunResult(
                    success=True, return_code=0,
                    stdout="", stderr="", message="",
                    run_dir="", log_file="",
                )

        worker = AtpRunWorker(MockRunner(), "fake.atp")
        captured: list[str] = []
        worker.stdout_line.connect(captured.append)
        worker.run()
        joined = "".join(captured)
        # Ordem preservada: alfa < beta < gamma < delta
        assert joined.index("alfa") < joined.index("beta")
        assert joined.index("beta") < joined.index("gamma")
        assert joined.index("gamma") < joined.index("delta")


# ---------------------------------------------------------------------------
# Runner Popen sem bufsize=1
# ---------------------------------------------------------------------------


class TestRunnerPopenBufsize:

    def test_runner_popen_no_line_buffer_in_binary(self):
        """v0.91.2: runner não passa bufsize=1 para Popen
        (binário). Verifica via call signature do método ``run``
        chamando com mock subprocess.
        """
        from unittest.mock import patch, MagicMock
        from app.simulation import runner as runner_mod

        captured_kwargs = {}

        def fake_popen(*args, **kwargs):
            captured_kwargs.update(kwargs)
            mock = MagicMock()
            mock.communicate.return_value = (b"", b"")
            mock.returncode = 0
            mock.kill = MagicMock()
            return mock

        # AtpRunner exige um executable_path válido + atp_path
        # válido para chegar até o Popen call. Mockamos esses
        # checks via tmp file.
        import tempfile
        with tempfile.NamedTemporaryFile(
            suffix=".exe", delete=False,
        ) as tf_exe, tempfile.NamedTemporaryFile(
            suffix=".atp", delete=False,
        ) as tf_atp:
            exe_path = tf_exe.name
            atp_path = tf_atp.name

        r = runner_mod.AtpRunner(executable_path=exe_path, timeout=10)
        with patch("subprocess.Popen", side_effect=fake_popen):
            r.run(atp_path, timeout=10)
        # bufsize=1 NÃO deve estar nos kwargs do Popen.
        assert captured_kwargs.get("bufsize") != 1, (
            f"Popen kwargs include bufsize=1 (binary mode warning): "
            f"{captured_kwargs}"
        )
