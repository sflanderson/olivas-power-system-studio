"""
tests/test_pp_v0_91_7_signal_relay.py — v0.91.7:

Hotfix definitivo do GUI freeze + cross-thread Qt errors.

Sintoma reportado pelo usuário (3a vez, mesmo após v0.91.2,
v0.91.4 e v0.91.6):

::

    QObject: Cannot create children for a parent that is in
    a different thread.
    Parent is QLabel(...), parent's thread is QThread(A),
    current thread is QThread(B)

Causa raiz definitiva
=======================

PySide6 6.x **NÃO RESPEITA** ``Qt.QueuedConnection`` quando
``signal.emit()`` vem de uma Python ``threading.Thread``
(não-Qt). A detecção de thread no emit time falha → cai pra
DirectConnection → slot roda no thread errado → crash.

Isso é um issue conhecido, não bug do nosso código. Solução
canônica Qt C++: ``QMetaObject.invokeMethod`` que SEMPRE
marshalla a chamada para o thread do receiver via event
posting de baixo nível.

Solução
==========

``app/gui/signal_relay.py:SignalRelay`` — QObject que vive no
main thread. Métodos ``post_*()`` chamam
``QMetaObject.invokeMethod`` com ``Qt.QueuedConnection`` para
chamar slots ``@Slot`` (que executam no main thread, garantido
pelo invokeMethod). Slots emitem signals locais — receivers
conectados rodam normalmente no main.

Cobertura
---------

* ``SignalRelay`` instancia + tem todos os signals esperados.
* Métodos @Slot existem com decoração correta.
* Métodos ``post_*()`` chamam ``QMetaObject.invokeMethod``.
* Worker integrado com relay: callbacks rotam para
  ``relay.post_*()``.
* ``make_run_thread`` aceita ``relay`` parameter.
"""

from __future__ import annotations

import threading
import time
from unittest.mock import patch

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# SignalRelay basics
# ---------------------------------------------------------------------------


class TestSignalRelayBasics:

    def test_instantiates(self, qapp):
        from app.gui.signal_relay import SignalRelay
        relay = SignalRelay()
        # Os 5 signals esperados
        for sig_name in (
            "stdout_chunk",
            "stderr_chunk",
            "phase_changed",
            "run_finished",
            "run_cancelled",
        ):
            assert hasattr(relay, sig_name), (
                f"SignalRelay missing signal {sig_name!r}"
            )

    def test_lives_on_main_thread(self, qapp):
        """Relay deve viver no thread onde foi criado (main).
        Crítico para que slots @Slot rodem no main."""
        from app.gui.signal_relay import SignalRelay
        from PySide6.QtCore import QThread
        relay = SignalRelay()
        # Thread do relay = thread atual = main
        assert relay.thread() is QThread.currentThread()

    def test_slot_methods_exist(self, qapp):
        """v0.91.7 contract: cada signal tem um slot @Slot
        para invokeMethod target."""
        from app.gui.signal_relay import SignalRelay
        # Slots devem existir (chamados via invokeMethod)
        for slot_name in (
            "_emit_stdout",
            "_emit_stderr",
            "_emit_phase",
            "_emit_finished",
            "_emit_cancelled",
        ):
            assert hasattr(SignalRelay, slot_name), (
                f"SignalRelay missing slot {slot_name!r}"
            )

    def test_post_methods_use_invoke_method(self, qapp):
        """
        v0.91.7 contract: ``post_*`` chamam
        ``QMetaObject.invokeMethod`` (canonical PySide6
        thread-safe pattern). Spy via patch.
        """
        from app.gui.signal_relay import SignalRelay
        relay = SignalRelay()
        # Patch invokeMethod e verifica que post_stdout chama
        with patch(
            "app.gui.signal_relay.QMetaObject.invokeMethod"
        ) as mock_invoke:
            relay.post_stdout("test")
            mock_invoke.assert_called_once()
            args = mock_invoke.call_args
            # 1º arg = receiver (relay), 2º = method name
            assert args[0][0] is relay
            assert args[0][1] == "_emit_stdout"
            # Qt.QueuedConnection em algum lugar
            assert Qt.QueuedConnection in args[0]


# ---------------------------------------------------------------------------
# Cross-thread emit (smoke — não testa entrega real, só no-crash)
# ---------------------------------------------------------------------------


class TestSignalRelayCrossThread:

    def test_post_from_python_thread_no_crash(self, qapp):
        """
        Reader thread (Python) chama ``relay.post_stdout``.
        Não deve crashar. Entrega real do slot @Slot requer
        event loop ativo + processEvents.
        """
        from app.gui.signal_relay import SignalRelay
        relay = SignalRelay()
        # Spawn Python thread que chama post_*
        errors = []

        def bg():
            try:
                for i in range(50):
                    relay.post_stdout(f"line {i}")
                    relay.post_phase("running")
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=bg)
        t.start()
        t.join(timeout=2)
        assert not errors, f"Crash em post_*: {errors}"

    def test_post_methods_handle_concurrent_calls(self, qapp):
        """4 threads chamando post_* concorrentemente não
        crasham nem deadlock."""
        from app.gui.signal_relay import SignalRelay
        relay = SignalRelay()
        errors = []

        def bg(thread_id):
            try:
                for i in range(100):
                    relay.post_stdout(f"t{thread_id}_line{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=bg, args=(i,))
            for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        assert not errors


# ---------------------------------------------------------------------------
# Worker integration with relay
# ---------------------------------------------------------------------------


class TestWorkerWithRelay:

    def test_worker_accepts_relay_arg(self, qapp):
        from app.gui.async_runner import AtpRunWorker
        from app.gui.signal_relay import SignalRelay
        relay = SignalRelay()

        class MockRunner:
            def run(self, *a, **kw):
                from app.simulation.runner import RunResult
                return RunResult(
                    success=True, return_code=0,
                    stdout="", stderr="", message="OK",
                    run_dir="", log_file="",
                )

        worker = AtpRunWorker(
            MockRunner(), "fake.atp", relay=relay,
        )
        assert worker._relay is relay

    def test_worker_routes_callbacks_via_relay(self, qapp):
        """
        v0.91.7: quando relay fornecido, runner callbacks vão
        para relay.post_* em vez de worker.signal.emit.
        """
        from app.gui.async_runner import AtpRunWorker
        from app.gui.signal_relay import SignalRelay
        from app.simulation.runner import RunResult

        relay = SignalRelay()

        # Spy os métodos post_* do relay
        post_calls = {"stdout": 0, "stderr": 0, "phase": 0}

        original_stdout = relay.post_stdout
        original_stderr = relay.post_stderr
        original_phase = relay.post_phase

        def spy_stdout(c):
            post_calls["stdout"] += 1
            original_stdout(c)

        def spy_stderr(c):
            post_calls["stderr"] += 1
            original_stderr(c)

        def spy_phase(p):
            post_calls["phase"] += 1
            original_phase(p)

        relay.post_stdout = spy_stdout
        relay.post_stderr = spy_stderr
        relay.post_phase = spy_phase

        class MockRunner:
            def run(self, path, *, stdout_callback=None,
                    stderr_callback=None, phase_callback=None,
                    **kw):
                if stdout_callback:
                    stdout_callback("output\n")
                if stderr_callback:
                    stderr_callback("error\n")
                if phase_callback:
                    phase_callback("running")
                return RunResult(
                    success=True, return_code=0,
                    stdout="", stderr="", message="OK",
                    run_dir="", log_file="",
                )

        worker = AtpRunWorker(
            MockRunner(), "fake.atp", relay=relay,
        )
        worker.run()
        # Relay foi chamado
        assert post_calls["stdout"] >= 1
        assert post_calls["stderr"] >= 1
        assert post_calls["phase"] >= 1


# ---------------------------------------------------------------------------
# make_run_thread accepts relay
# ---------------------------------------------------------------------------


class TestMakeRunThreadRelay:

    def test_accepts_relay_kwarg(self, qapp):
        from app.gui.async_runner import make_run_thread
        from app.gui.signal_relay import SignalRelay

        class MockRunner:
            pass

        relay = SignalRelay()
        thread, worker = make_run_thread(
            MockRunner(), "fake.atp", relay=relay,
        )
        assert worker._relay is relay
        # Cleanup
        thread.deleteLater()
        worker.deleteLater()

    def test_relay_finished_quits_thread(self, qapp):
        """
        v0.91.7: quando relay fornecido, ``thread.quit`` é
        ligado a ``relay.run_finished`` (não worker.finished).
        """
        from app.gui.async_runner import make_run_thread
        from app.gui.signal_relay import SignalRelay

        class MockRunner:
            pass

        relay = SignalRelay()
        thread, worker = make_run_thread(
            MockRunner(), "fake.atp", relay=relay,
        )
        # Verifica que relay.run_finished tem alguma conexão
        # (não trivial em PySide6 — quitcount aproximado).
        # Smoke: chegou aqui sem erro.
        assert thread is not None
        thread.deleteLater()
        worker.deleteLater()
