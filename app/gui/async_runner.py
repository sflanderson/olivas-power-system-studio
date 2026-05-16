"""
app.gui.async_runner — execução assíncrona de simulações ATP
em QThread (v0.28.3-PRO Onda 3.1).

Antes: ``MainWindow._on_run_atp`` chamava ``runner.run()``
sincronamente, bloqueando a UI por todo o tempo da simulação
(às vezes minutos), com apenas ``QApplication.processEvents()``
para repintar.

Agora:

* Worker em ``QThread``.
* ``QProgressDialog`` indeterminado com botão **Cancelar**.
* ``runner.kill_process()`` chamado no cancel.
* Sinal ``run_finished(RunResult)`` ao término.
* Timeout do runner respeitado (process kill).

v0.91.2 — throttle de stdout/stderr
=====================================

Sintoma: ATP em simulações longas (ex: ``trt_all_motors_dt_ea
.atp``) emitia centenas de linhas/segundo. Cada linha virava
um cross-thread signal emit → main thread acumulava milhares
de eventos → GUI ficava "Not Responding".

Fix: agregamos linhas no worker thread em chunks de até
``_THROTTLE_INTERVAL_MS`` ms (default 100) ou
``_THROTTLE_MAX_LINES`` (default 50), e emitimos um único
chunk por flush. Reduz signals de centenas/s para ~10/s
sem perder informação.

v0.91.6 — thread-safety lock
==============================

Bug: ``_LineBatcher.push`` é chamado de Python threads
(``threading.Thread`` em ``runner._stream_subprocess``).
Buffer manipulation + emit não eram thread-safe. Resultado:
Qt erros tipo "Cannot create children for a parent that
is in a different thread" durante ``QLabel.setText`` /
``QPlainTextEdit.appendPlainText``.

Fix: ``threading.Lock`` em ``_LineBatcher`` protege buffer
+ emit; conexões em ``main_window`` forçadas a
``Qt.QueuedConnection`` (slot SEMPRE roda no thread do
receiver).
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal


# v0.91.2 — parâmetros do throttle.
# 100 ms é imperceptível para olho humano (10 fps de log) e dá
# ~10 emits/s mesmo com saída maciça do ATP.
_THROTTLE_INTERVAL_MS = 100
_THROTTLE_MAX_LINES = 50


class _LineBatcher:
    """
    v0.91.2: acumula linhas e libera em chunks via callback
    (emit Qt signal).

    v0.91.6: thread-safe via ``threading.Lock``. Push é chamado
    de Python threads (readers de ``runner._stream_subprocess``)
    enquanto flush final é chamado pela worker thread no fim
    de ``run()``. Lock evita race no buffer + serializa emits.
    """

    def __init__(
        self, emit_fn,
        interval_ms: int = _THROTTLE_INTERVAL_MS,
        max_lines: int = _THROTTLE_MAX_LINES,
    ) -> None:
        self._emit = emit_fn
        self._interval_s = interval_ms / 1000.0
        self._max_lines = max_lines
        self._buffer: list[str] = []
        self._last_flush = time.monotonic()
        # v0.91.6: lock para thread-safety entre reader threads
        # + worker thread (flush final).
        self._lock = threading.Lock()

    def push(self, line: str) -> None:
        chunk_to_emit: Optional[str] = None
        with self._lock:
            self._buffer.append(line)
            if (
                len(self._buffer) >= self._max_lines
                or (time.monotonic() - self._last_flush)
                >= self._interval_s
            ):
                chunk_to_emit = "".join(self._buffer)
                self._buffer.clear()
                self._last_flush = time.monotonic()
        # Emit FORA do lock — Qt signal emit é thread-safe e
        # pode bloquear (queued connections em main thread).
        # Manter o lock segurado durante emit poderia gerar
        # deadlock se o slot tentar push() de novo (improvável,
        # mas defesa em profundidade).
        if chunk_to_emit is not None:
            self._safe_emit(chunk_to_emit)

    def flush(self) -> None:
        chunk_to_emit: Optional[str] = None
        with self._lock:
            if not self._buffer:
                return
            chunk_to_emit = "".join(self._buffer)
            self._buffer.clear()
            self._last_flush = time.monotonic()
        if chunk_to_emit is not None:
            self._safe_emit(chunk_to_emit)

    def _safe_emit(self, chunk: str) -> None:
        try:
            self._emit(chunk)
        except Exception:
            # Slot pode ter sido desconectado durante teardown.
            pass


class AtpRunWorker(QObject):
    """
    Worker QObject para execução do AtpRunner em thread
    separada.

    Emite signals:

    * ``finished(RunResult)`` — execução terminou (sucesso ou
      falha).
    * ``cancelled()`` — usuário cancelou.
    * ``stdout_line(str)`` — v0.60: linha stdout em tempo real.
      v0.91.2: agora pode ser CHUNK de várias linhas
      concatenadas (throttling). Receivers que processam
      linha-por-linha devem dividir com ``splitlines()``.
    * ``stderr_line(str)`` — idem.
    """

    finished = Signal(object)   # RunResult
    cancelled = Signal()
    stdout_line = Signal(str)   # v0.60 / v0.91.2: chunk
    stderr_line = Signal(str)   # v0.60 / v0.91.2: chunk
    # v0.91.5: notifica fase atual do runner para o UI mostrar
    # progresso visual + permitir diagnosticar onde freezou.
    phase_changed = Signal(str)   # phase_id

    def __init__(
        self, runner, atp_file_path: str,
        timeout: Optional[int] = None,
        relay=None,
    ) -> None:
        """
        v0.91.7: ``relay`` é um ``SignalRelay`` (criado no main
        thread) que marshalliza eventos vindos de Python threads
        do runner. Quando fornecido, o worker delega TODOS os
        emits (stdout/stderr/phase/finished/cancelled) ao relay
        em vez de emitir signals próprios — evita o crash
        cross-thread.

        Modo legacy (sem relay): worker emite signals próprios
        diretamente. Funciona se TODOS os callbacks vierem do
        QThread do worker — caso de tests com mocks.
        """
        super().__init__()
        self._runner = runner
        self._path = atp_file_path
        self._timeout = timeout
        self._cancelled = False
        self._relay = relay

    def request_cancel(self) -> None:
        """Solicita cancelamento — kill do subprocess se ativo."""
        self._cancelled = True
        try:
            self._runner.kill_process()
        except Exception:
            # Runner pode não ter kill_process; tudo bem
            pass

    def _on_runner_phase(self, phase: str) -> None:
        """v0.91.5: callback chamado no thread do runner;
        re-emite via Qt signal (cross-thread → main thread)."""
        try:
            self.phase_changed.emit(str(phase))
        except Exception:
            pass

    def run(self) -> None:
        """
        Executa em background thread.

        v0.60: forward de stdout/stderr line-by-line para signals.
        v0.91.2: linhas agregadas via ``_LineBatcher`` para evitar
        flooding do main thread. Flush final garante que linhas
        residuais não se percam quando o subprocess termina.
        v0.91.7: rota emits via ``self._relay`` (SignalRelay
        no main thread) para garantir thread-safety entre Python
        readers e Qt main-thread widgets. Sem relay, fallback
        legacy direct emit (suficiente para tests onde callbacks
        vêm do QThread do worker).
        """
        # Emit functions: usam relay (v0.91.7 padrão) ou signals
        # diretos (legacy/test fallback).
        if self._relay is not None:
            emit_stdout = self._relay.post_stdout
            emit_stderr = self._relay.post_stderr
            emit_phase = self._relay.post_phase
            emit_finished = self._relay.post_finished
            emit_cancelled = self._relay.post_cancelled
        else:
            emit_stdout = self.stdout_line.emit
            emit_stderr = self.stderr_line.emit
            emit_phase = self.phase_changed.emit
            emit_finished = self.finished.emit
            emit_cancelled = self.cancelled.emit

        out_batcher = _LineBatcher(emit_stdout)
        err_batcher = _LineBatcher(emit_stderr)

        # v0.91.5: emite "starting" antes do runner.run() para o
        # UI saber que o worker tomou o thread.
        try:
            emit_phase("starting")
        except Exception:
            pass
        try:
            result = self._runner.run(
                self._path, timeout=self._timeout,
                stdout_callback=out_batcher.push,
                stderr_callback=err_batcher.push,
                phase_callback=emit_phase,
            )
            # Flush residual antes de emitir finished (UX: não
            # perde as últimas linhas).
            out_batcher.flush()
            err_batcher.flush()
            if self._cancelled:
                emit_cancelled()
            else:
                emit_finished(result)
        except Exception as e:
            out_batcher.flush()
            err_batcher.flush()
            # v0.28.4-PRO followup (code-review blocker #1):
            # construct RunResult with kwargs matching its
            # ACTUAL dataclass schema (return_code, sem
            # duration_s/lis_file/pl4_file inexistentes).
            from app.simulation.runner import RunResult
            err_result = RunResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Exception: {e}",
                message=f"Erro: {e}",
                run_dir="",
                log_file="",
            )
            emit_finished(err_result)


def make_run_thread(
    runner, atp_file_path: str,
    timeout: Optional[int] = None,
    relay=None,
) -> tuple[QThread, AtpRunWorker]:
    """
    Cria thread + worker para execução assíncrona do ATP.

    O caller é responsável por:

    * conectar ``worker.finished`` e ``worker.cancelled``
      (ou ``relay.run_finished`` / ``relay.run_cancelled``)
    * chamar ``thread.start()``
    * limpar (``thread.quit()`` + ``thread.wait()``) ao final.

    v0.91.7: ``relay`` opcional (SignalRelay) para thread-safety
    quando há reader threads (Python ``threading.Thread``).
    Quando fornecido, todos os emits são rotados via
    ``QMetaObject.invokeMethod`` para o main thread. Sem relay,
    funciona em modo legacy (ok para tests com callbacks
    sintéticos do QThread).

    Returns
    -------
    tuple[QThread, AtpRunWorker]
    """
    thread = QThread()
    worker = AtpRunWorker(
        runner, atp_file_path, timeout=timeout, relay=relay,
    )
    worker.moveToThread(thread)
    # Quando thread iniciar → executa worker.run()
    thread.started.connect(worker.run)
    # Quando worker terminar → quit thread.
    # v0.91.7: se há relay, hook em relay.run_finished/cancelled
    # (que são emitidos no main thread após invokeMethod). Senão,
    # legacy hook em worker.finished/cancelled.
    if relay is not None:
        relay.run_finished.connect(thread.quit)
        relay.run_cancelled.connect(thread.quit)
    else:
        worker.finished.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
    return thread, worker
