"""
app.gui.atp_progress_dialog — diálogo rico de progresso da
simulação ATP (v0.91.5).

Filosofia
==========

Usuário reportou que o app "trava" (Qt: "Not Responding")
durante simulações ATP de exemplos pesados. O diagnóstico
indireto era difícil — o ``QProgressDialog`` indeterminate
da v0.28.3 não dava nenhuma indicação de ONDE o código
estava preso.

Este dialog resolve isso com:

1. **Indicador de fase** (lifecycle do runner):
   ``Iniciando → Validando → Lançando ATP → Rodando →
   Coletando outputs → Salvando log → Pronto``.
   Quando freezar, o usuário VÊ qual fase está ativa.

2. **Output stream ao vivo** (últimas N linhas):
   stdout/stderr do ATP em tempo real (com throttle do
   v0.91.2 + batch HTML do v0.91.4 — não enrosca a UI).

3. **Progress bar indeterminate** + **Cancel** (kill do
   subprocess).

4. **Phase log compacto** (debug): ao final, mostra a
   sequência completa de fases que rodaram.

UX:

::

    ┌─ Simulação ATP — meu_caso.atp ──────────────────────┐
    │ 🔄 ATP rodando — aguardando convergência            │
    │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ (indeterminate)         │
    │                                                     │
    │ ┌── Saída ATP (últimas linhas) ───────────────────┐ │
    │ │ Step 0.025 ms  V_BUS = 13.78 kV                 │ │
    │ │ Step 0.050 ms  V_BUS = 13.79 kV                 │ │
    │ │ Step 0.075 ms  V_BUS = 13.81 kV                 │ │
    │ │ ...                                              │ │
    │ └─────────────────────────────────────────────────┘ │
    │                                                     │
    │ Fases: validating ✓  copying ✓  launching ✓  …      │
    │                                                     │
    │                                       [ Cancelar ]  │
    └─────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


# Mapeamento phase_id → (icon, label_pt) para exibição.
PHASE_LABELS: dict[str, tuple[str, str]] = {
    "starting":            ("⏳", "Iniciando worker..."),
    "validating":          ("🔍", "Validando paths (exe + .atp)"),
    "creating_run_dir":    ("📁", "Criando diretório de execução"),
    "copying_atp":         ("📋", "Copiando .atp para diretório do ATP"),
    "launching":           ("🚀", "Lançando ATP (subprocess.Popen)"),
    "running":             ("🔄", "ATP rodando — aguardando convergência"),
    "collecting_outputs":  ("📥", "Coletando outputs (.pl4, .lis, ...)"),
    "saving_log":          ("💾", "Salvando execution.log"),
    "done":                ("✅", "Pronto"),
    "cancelled":           ("⛔", "Cancelado pelo usuário"),
    "failed":              ("❌", "Falhou"),
}

# Quantas últimas linhas mostrar no output view (rolling buffer).
_OUTPUT_MAX_LINES = 200


class AtpProgressDialog(QDialog):
    """
    Dialog de progresso da simulação ATP com fases + output
    ao vivo + cancel.

    Sinais
    --------

    * ``cancel_requested()`` — usuário clicou em Cancelar.

    API
    ====

    * ``set_phase(phase_id)`` — atualiza fase corrente.
    * ``append_output(text)`` — adiciona linhas (multi-OK).
    * ``mark_done(success, message)`` — final state.
    * ``is_cancelled()`` — query.
    """

    cancel_requested = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        atp_filename: str = "ATP",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Simulação ATP — {atp_filename}")
        self.setMinimumSize(640, 480)
        self.setModal(True)
        # Permite redimensionar (default WA_FixedSize não set)
        self._cancelled = False
        self._phases_seen: list[str] = []
        self._build_ui(atp_filename)

    # ---- UI ---------------------------------------------------------------

    def _build_ui(self, atp_filename: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header
        header = QLabel(
            f"<b>Simulação ATP</b>: <code>{atp_filename}</code>",
            self,
        )
        header.setStyleSheet("font-size: 11pt;")
        layout.addWidget(header)

        # Phase indicator (grande, destaque)
        self._phase_label = QLabel("⏳ Iniciando worker...", self)
        self._phase_label.setStyleSheet(
            "QLabel { color: #556B2F; font-size: 12pt; "
            "padding: 6px 10px; "
            "background: #FAFAF5; border: 1px solid #B5D4A8; "
            "border-radius: 4px; }"
        )
        self._phase_label.setWordWrap(True)
        layout.addWidget(self._phase_label)

        # Progress bar (indeterminate até mark_done)
        self._progress = QProgressBar(self)
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(8)
        self._progress.setStyleSheet(
            "QProgressBar { background: #2A2D24; border-radius: 4px; }"
            "QProgressBar::chunk { "
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "    stop:0 #BFFF00, stop:1 #00A8E8); "
            "  border-radius: 3px; "
            "}"
        )
        layout.addWidget(self._progress)

        # Output view label
        layout.addWidget(QLabel("<b>Saída ATP (últimas linhas):</b>", self))

        # Output view (plain text, rolling buffer)
        self._output_view = QPlainTextEdit(self)
        self._output_view.setReadOnly(True)
        self._output_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._output_view.setFont(QFont("Consolas", 9))
        # Rolling buffer: drop linhas antigas após N
        self._output_view.document().setMaximumBlockCount(_OUTPUT_MAX_LINES)
        self._output_view.setStyleSheet(
            "QPlainTextEdit { background: #1c1f1a; color: #E8E5D8; "
            "border: 1px solid #87A96B; border-radius: 4px; "
            "padding: 4px; }"
        )
        layout.addWidget(self._output_view, stretch=1)

        # Phase trail (compact)
        self._phase_trail = QLabel("Fases: ", self)
        self._phase_trail.setWordWrap(True)
        self._phase_trail.setStyleSheet(
            "QLabel { color: #6B8E23; font-size: 8pt; "
            "padding: 2px 6px; }"
        )
        layout.addWidget(self._phase_trail)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self._cancel_btn = QPushButton("Cancelar", self)
        self._cancel_btn.setStyleSheet(
            "QPushButton { padding: 6px 18px; }"
        )
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

    # ---- API --------------------------------------------------------------

    def set_phase(self, phase_id: str) -> None:
        """v0.91.5: atualiza a fase visível."""
        icon, label = PHASE_LABELS.get(phase_id, ("⏳", phase_id))
        self._phase_label.setText(f"{icon} {label}")
        self._phases_seen.append(phase_id)
        # Atualiza phase trail (compact)
        trail = " → ".join(
            f"{PHASE_LABELS.get(p, ('•', p))[0]} {p}"
            for p in self._phases_seen
        )
        self._phase_trail.setText(f"<b>Fases:</b> {trail}")

    def append_output(self, text: str) -> None:
        """v0.91.5: adiciona linhas ao output view.

        Aceita texto multi-linha (chunk). Plain text — sem
        HTML parser (mais leve que console_panel).
        """
        # Strip trailing newline (appendPlainText adiciona um
        # newline implícito).
        if text.endswith("\n"):
            text = text[:-1]
        if text:
            self._output_view.appendPlainText(text)
        # Auto-scroll to bottom
        sb = self._output_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def mark_done(self, success: bool, message: str = "") -> None:
        """
        v0.91.5: indica conclusão. Troca progress bar para
        determinate + 100%, troca botão Cancelar por Fechar.
        """
        if success:
            self.set_phase("done")
        else:
            self.set_phase("failed")
            if message:
                self._phase_label.setText(
                    f"❌ {message}"
                )
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._cancel_btn.setText("Fechar")
        try:
            self._cancel_btn.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self._cancel_btn.clicked.connect(self.accept)

    def mark_cancelled(self) -> None:
        """v0.91.5: indica cancelamento confirmado."""
        self.set_phase("cancelled")
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._cancel_btn.setText("Fechar")
        try:
            self._cancel_btn.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self._cancel_btn.clicked.connect(self.accept)

    def is_cancelled(self) -> bool:
        return self._cancelled

    # ---- Internals --------------------------------------------------------

    def _on_cancel_clicked(self) -> None:
        if self._cancelled:
            return
        self._cancelled = True
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setText("Cancelando...")
        self.cancel_requested.emit()
