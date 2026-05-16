"""
tests/test_pp_v0_91_6_thread_safety.py — v0.91.6:

Hotfix de thread-safety nas conexões worker → progress dialog.

Sintoma reportado pelo usuário (logs do app):

::

    QObject: Cannot create children for a parent that is in
    a different thread.
    (Parent is QLabel(0x...), parent's thread is QThread(...),
    current thread is QThread(...)
    QObject::setParent: Cannot set parent, new parent is in a
    different thread

Causa raiz
============

``runner._stream_subprocess`` cria 2 ``threading.Thread`` (NÃO
``QThread``) para drenar stdout/stderr do subprocess. Esses
readers chamam callbacks que disparam Qt signals.

``Qt.AutoConnection`` decide o tipo NO CONNECT TIME baseado em
``emitter.thread()`` (a QThread do worker). Mas no EMIT TIME,
vindo de Python thread não-Qt, Qt pode cair pra
``DirectConnection`` → slot roda no reader thread → modifica
widgets no thread errado → Qt erro acima.

Fix
====

1. ``_LineBatcher`` ganha ``threading.Lock`` para serializar
   buffer + emit entre push (reader thread) e flush (worker
   thread no fim de run()).

2. ``main_window._on_run_atp`` usa ``Qt.QueuedConnection``
   explícito em TODAS as conexões worker → main-thread
   widgets. Garante slot rodando no thread do receiver,
   independente do thread emissor.

Cobertura
---------

* ``_LineBatcher`` thread-safe sob push concorrente de
  multiple threads (smoke teste).
* Buffer não corrompe + todas as linhas eventualmente
  emitidas.
* Connections em main_window usam Qt.QueuedConnection
  explícito (verificado via inspecção do source).
"""

from __future__ import annotations

import threading
import time

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# _LineBatcher thread-safety
# ---------------------------------------------------------------------------


class TestLineBatcherThreadSafety:

    def test_concurrent_push_no_corruption(self):
        """
        4 threads pushing 250 linhas cada simultaneamente.
        Total 1000 linhas. Após flush final, todas devem
        estar emitidas (concatenadas).
        """
        from app.gui.async_runner import _LineBatcher

        emitted: list[str] = []
        lock = threading.Lock()

        def safe_emit(chunk: str) -> None:
            with lock:
                emitted.append(chunk)

        b = _LineBatcher(
            emit_fn=safe_emit,
            interval_ms=10,
            max_lines=20,
        )

        n_threads = 4
        per_thread = 250

        def pusher(thread_id: int) -> None:
            for i in range(per_thread):
                b.push(f"t{thread_id}_line{i}\n")

        threads = [
            threading.Thread(target=pusher, args=(i,))
            for i in range(n_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Flush residual
        b.flush()

        joined = "".join(emitted)
        # Total de linhas: 4 × 250 = 1000
        assert joined.count("\n") == n_threads * per_thread
        # Cada thread tem todas as suas linhas presentes
        for tid in range(n_threads):
            for i in range(per_thread):
                assert f"t{tid}_line{i}" in joined

    def test_push_during_flush_no_lost_lines(self):
        """
        Worker chama flush() após o subprocess terminar.
        Reader thread pode ainda estar pushing nesse momento.
        Validamos que NENHUMA linha é perdida na transição.
        """
        from app.gui.async_runner import _LineBatcher

        emitted: list[str] = []
        emit_lock = threading.Lock()

        def safe_emit(chunk: str) -> None:
            with emit_lock:
                emitted.append(chunk)

        b = _LineBatcher(
            emit_fn=safe_emit,
            interval_ms=100,    # nunca dispara por tempo
            max_lines=10_000,
        )

        # Pusher contínuo
        stop = threading.Event()
        push_count = [0]

        def pusher() -> None:
            i = 0
            while not stop.is_set():
                b.push(f"line {i}\n")
                push_count[0] += 1
                i += 1
                # Pequena pausa para não saturar CPU
                if i % 100 == 0:
                    time.sleep(0.0001)

        t = threading.Thread(target=pusher)
        t.start()
        # Deixa rodar 50 ms
        time.sleep(0.05)
        # Flush concorrente — não deve crashar
        b.flush()
        # Mais um período de push
        time.sleep(0.05)
        stop.set()
        t.join()
        b.flush()

        joined = "".join(emitted)
        actual_lines = joined.count("\n")
        # Todas as linhas pushed estão emitidas
        assert actual_lines == push_count[0], (
            f"Linhas perdidas: pushed {push_count[0]}, "
            f"emitidas {actual_lines}"
        )


# ---------------------------------------------------------------------------
# Conexões em main_window usam Qt.QueuedConnection
# ---------------------------------------------------------------------------


class TestMainWindowQueuedConnections:

    def test_run_atp_uses_signal_relay(self):
        """
        v0.91.7: ``_on_run_atp`` agora usa ``SignalRelay`` em
        vez de Qt.QueuedConnection direto. Relay é canonical
        PySide6 pattern: vive no main thread, recebe via
        ``QMetaObject.invokeMethod`` (canonical thread-safe),
        emite signals locais — slots conectados rodam SEMPRE
        no main thread.

        Critério: source de _on_run_atp menciona SignalRelay
        + relay.* connections.
        """
        import inspect
        from app.gui import main_window
        src = inspect.getsource(main_window.MainWindow._on_run_atp)
        assert "SignalRelay" in src, (
            "MainWindow._on_run_atp deve criar SignalRelay "
            "para marshalling thread-safe"
        )
        # Conexões via relay (não direto via worker.signal)
        for relay_sig in (
            "relay.run_finished",
            "relay.run_cancelled",
            "relay.phase_changed",
            "relay.stdout_chunk",
            "relay.stderr_chunk",
        ):
            assert relay_sig in src, (
                f"Connection {relay_sig!r} ausente"
            )


# ---------------------------------------------------------------------------
# AtpProgressDialog tolera append_output de threads diferentes (defensivo)
# ---------------------------------------------------------------------------


class TestProgressDialogThreadSafety:

    def test_append_output_main_thread_only_via_queued(self, qapp):
        """
        Smoke: dialog é criado em main thread, append_output
        é chamado em main thread. Não testa cross-thread aqui
        (precisaria de QThread real + event loop).
        Validamos que append_output não crasha com diversos
        formatos de input.
        """
        from app.gui.atp_progress_dialog import AtpProgressDialog
        dlg = AtpProgressDialog(atp_filename="x.atp")
        # Chunks variados
        dlg.append_output("")
        dlg.append_output("solo\n")
        dlg.append_output("multi\nline\nchunk\n")
        dlg.append_output("trailing\n\n\n")
        # Não crasha
        text = dlg._output_view.toPlainText()
        assert "solo" in text
        assert "multi" in text


# ---------------------------------------------------------------------------
# Integração worker + thread-safety (sem subprocess real)
# ---------------------------------------------------------------------------


class TestWorkerWithReaderThreads:

    def test_worker_with_reader_thread_no_crash(self, qapp):
        """
        Mock runner que SIMULA reader threads: spawn 2 Python
        threads que chamam stdout_callback / stderr_callback
        de fora do worker thread. Verifica que o worker NÃO
        CRASHA com race conditions.

        Emit de Qt signal de Python thread não-Qt para slot
        em main thread requer event loop ativo + processEvents
        para garantir delivery — não testamos delivery aqui
        (suficiente: nenhuma exception).
        """
        from app.gui.async_runner import AtpRunWorker
        from app.simulation.runner import RunResult

        class ThreadedMockRunner:
            def run(self, path, timeout=None, *,
                    stdout_callback=None, stderr_callback=None,
                    phase_callback=None):
                # Spawn threads similares ao runner real
                import threading

                def stdout_pusher():
                    if stdout_callback:
                        for i in range(100):
                            stdout_callback(f"out {i}\n")

                def stderr_pusher():
                    if stderr_callback:
                        for i in range(50):
                            stderr_callback(f"err {i}\n")

                t_out = threading.Thread(target=stdout_pusher)
                t_err = threading.Thread(target=stderr_pusher)
                t_out.start()
                t_err.start()
                t_out.join()
                t_err.join()
                return RunResult(
                    success=True, return_code=0,
                    stdout="", stderr="", message="OK",
                    run_dir="", log_file="",
                )

        worker = AtpRunWorker(ThreadedMockRunner(), "fake.atp")
        # NÃO conectamos signals (delivery cross-thread requer
        # event loop). Apenas validamos que worker.run() não
        # crasha nem deadlock com reader threads concorrentes.
        worker.run()
        # Smoke: chegou aqui sem exception
