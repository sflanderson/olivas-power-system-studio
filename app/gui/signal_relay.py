"""
app.gui.signal_relay — marshalling thread-safe de eventos
de Python threads para o main thread Qt (v0.91.7).

Problema canônico
==================

Em PySide6, ``signal.emit()`` de uma ``threading.Thread``
não-Qt para um slot em widget do main thread é ESPECIFICAMENTE
PROBLEMÁTICO:

1. ``Qt.AutoConnection`` resolve o tipo no EMIT TIME baseado
   em ``QThread::currentThread()``. De Python thread sem
   wrapper QThread, a detecção é unreliable — pode cair em
   ``DirectConnection`` → slot roda no thread errado.

2. ``Qt.QueuedConnection`` explícito **DEVERIA** funcionar
   mas em PySide6 6.x há edge cases onde o emit de Python
   thread para slot Qt não enfileira corretamente (depende
   da versão e da plataforma).

3. Crash típico:

   ::

       QObject: Cannot create children for a parent that is
       in a different thread.
       (Parent is QLabel(...), parent's thread is QThread(A),
       current thread is QThread(B)

Solução canônica (Qt C++ pattern)
===================================

Use ``QMetaObject.invokeMethod`` com ``Qt.QueuedConnection``
explícito. Diferente de ``signal.emit()``, ``invokeMethod``
**SEMPRE** posta um event na thread queue do receiver,
independente de onde o caller estiver. É o equivalente C++
de "marshall this call to the receiver's thread".

::

    QMetaObject.invokeMethod(
        receiver,
        "method_name",        # método decorado com @Slot
        Qt.QueuedConnection,
        Q_ARG(str, value),
    )

Padrão SignalRelay
====================

``SignalRelay`` é um QObject leve que **vive no main thread**.
Reader threads (Python threads) chamam ``post_*()`` que
internamente usa ``invokeMethod`` para chamar slots @Slot.
Esses slots executam no main thread (graças ao
``QueuedConnection``) e ali emitem signals tradicionais.
Slots conectados aos signals do relay rodam normalmente em
DirectConnection (mesma thread = main).

Uso
====

::

    relay = SignalRelay()                  # main thread
    relay.stdout_chunk.connect(view.append)
    relay.phase_changed.connect(view.set_phase)

    # De qualquer thread (Python, QThread, etc.):
    relay.post_stdout("line of output\\n")
    relay.post_phase("running")

    # → view.append e view.set_phase rodam no main thread.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QMetaObject,
    QObject,
    Q_ARG,
    Qt,
    Signal,
    Slot,
)


class SignalRelay(QObject):
    """
    v0.91.7: marshall thread-safe de callbacks → main-thread
    Qt signals.

    O relay deve ser criado no main thread. Reader threads
    (Python threads, QThreads, etc.) chamam os métodos
    ``post_*()``, que usam ``QMetaObject.invokeMethod`` com
    ``Qt.QueuedConnection`` para postar a chamada na queue
    do main thread. O slot @Slot decorado executa no main,
    emitindo o signal correspondente.

    Slots conectados aos signals do relay (em widgets) rodam
    sempre no main thread.

    Signals
    --------

    * ``stdout_chunk(str)`` — chunk de stdout do subprocess.
    * ``stderr_chunk(str)`` — chunk de stderr.
    * ``phase_changed(str)`` — fase do runner mudou.
    * ``run_finished(object)`` — RunResult do final.
    * ``run_cancelled()`` — usuário cancelou.
    """

    stdout_chunk = Signal(str)
    stderr_chunk = Signal(str)
    phase_changed = Signal(str)
    run_finished = Signal(object)
    run_cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        # v0.91.7: ``run_finished`` carrega um ``RunResult`` que
        # não é um Qt meta-type registrado. ``Q_ARG(object, ...)``
        # falha em PySide6 com "Unable to find a QMetaType for
        # 'object'". Workaround: armazena pending result em self
        # (sob lock) e ``_emit_finished`` lê + emite localmente.
        # Apenas 1 finished por run, então o "fila" de tamanho 1
        # é suficiente.
        import threading
        self._pending_lock = threading.Lock()
        self._pending_result = None

    # ---- Slots @Slot — invocados via QMetaObject.invokeMethod ---------------

    @Slot(str)
    def _emit_stdout(self, chunk: str) -> None:
        """Roda no main thread (queued). Emite signal local."""
        self.stdout_chunk.emit(chunk)

    @Slot(str)
    def _emit_stderr(self, chunk: str) -> None:
        self.stderr_chunk.emit(chunk)

    @Slot(str)
    def _emit_phase(self, phase: str) -> None:
        self.phase_changed.emit(phase)

    @Slot()
    def _emit_finished(self) -> None:
        """v0.91.7: lê o pending result e emite. Sem Q_ARG."""
        with self._pending_lock:
            result = self._pending_result
            self._pending_result = None
        self.run_finished.emit(result)

    @Slot()
    def _emit_cancelled(self) -> None:
        self.run_cancelled.emit()

    # ---- Thread-safe entry points (chamáveis de qualquer thread) -----------

    def post_stdout(self, chunk: str) -> None:
        """v0.91.7: post chunk de stdout para main thread.

        Pode ser chamado de qualquer thread (Python, QThread).
        ``QMetaObject.invokeMethod`` posta o evento na queue
        do main thread; quando processado, ``_emit_stdout``
        roda lá e emite o signal.
        """
        QMetaObject.invokeMethod(
            self,
            "_emit_stdout",
            Qt.QueuedConnection,
            Q_ARG(str, str(chunk)),
        )

    def post_stderr(self, chunk: str) -> None:
        QMetaObject.invokeMethod(
            self,
            "_emit_stderr",
            Qt.QueuedConnection,
            Q_ARG(str, str(chunk)),
        )

    def post_phase(self, phase: str) -> None:
        QMetaObject.invokeMethod(
            self,
            "_emit_phase",
            Qt.QueuedConnection,
            Q_ARG(str, str(phase)),
        )

    def post_finished(self, result) -> None:
        """v0.91.7: armazena result em pending slot + invoca
        slot sem args. ``_emit_finished`` lê e emite — evita
        passar object via Q_ARG (não-Qt meta-type)."""
        with self._pending_lock:
            self._pending_result = result
        QMetaObject.invokeMethod(
            self,
            "_emit_finished",
            Qt.QueuedConnection,
        )

    def post_cancelled(self) -> None:
        QMetaObject.invokeMethod(
            self,
            "_emit_cancelled",
            Qt.QueuedConnection,
        )
