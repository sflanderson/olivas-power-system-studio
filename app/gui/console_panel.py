"""
app.gui.console_panel — painel dockable de console/log
(v0.28.3-PRO Onda 3.2).

Antes: stdout/stderr do ATP runner aparecia apenas em
QMessageBox de uma vez ao final. Warnings dos postprocessor
módulos não eram surfaceados.

Agora: ``ConsolePanel`` (QDockWidget) com 4 níveis de log:

* INFO (azul): operações bem-sucedidas
* WARN (amarelo): warnings de pipeline/coalescer/BCTRAN
* ERROR (vermelho): falhas de simulação
* LOG (cinza): saída crua de runner/parser

Inclui buttons:

* Limpar
* Copiar tudo
* Filtrar por nível
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDockWidget, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)


# Cores por nível de log
_LEVEL_COLORS = {
    "INFO":  "#0066cc",
    "WARN":  "#cc7700",
    "ERROR": "#cc0000",
    "LOG":   "#666666",
}


class ConsolePanel(QDockWidget):
    """
    Painel de console dockable para o MainWindow.

    Uso:

    ::

        console = ConsolePanel(parent)
        main_window.addDockWidget(Qt.BottomDockWidgetArea, console)
        # ...
        console.append_info("Operação iniciada.")
        console.append_warn("Default usado em S_kQ.")
        console.append_error("ATP crashou.")
        console.append_log("output do subprocess...")
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Console", parent)
        self.setObjectName("dock_console")
        self.setAllowedAreas(
            Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea,
        )

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Toolbar
        tb_row = QHBoxLayout()
        tb_row.setContentsMargins(2, 0, 2, 0)
        tb_row.addWidget(QLabel("Filtro:"))
        self._filter_combo = QComboBox()
        self._filter_combo.addItem("Todos")
        self._filter_combo.addItem("INFO+")
        self._filter_combo.addItem("WARN+")
        self._filter_combo.addItem("ERROR")
        self._filter_combo.currentIndexChanged.connect(self._refilter)
        tb_row.addWidget(self._filter_combo)
        tb_row.addStretch(1)
        btn_clear = QPushButton("Limpar")
        btn_clear.clicked.connect(self.clear)
        tb_row.addWidget(btn_clear)
        btn_copy = QPushButton("Copiar")
        btn_copy.clicked.connect(self._copy_all)
        tb_row.addWidget(btn_copy)
        layout.addLayout(tb_row)

        # Text area (read-only) — QTextEdit aceita HTML
        self._text = QTextEdit(container)
        self._text.setReadOnly(True)
        f = QFont("Consolas", 9)
        self._text.setFont(f)
        self._text.document().setMaximumBlockCount(5000)
        layout.addWidget(self._text, 1)

        self.setWidget(container)

        # Cache de lines para filtragem (level, text, html)
        self._lines: list[tuple[str, str]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append_info(self, msg: str) -> None:
        self._append("INFO", msg)

    def append_warn(self, msg: str) -> None:
        """
        v0.91.4: handle multi-line chunks (stderr de subprocess
        agora vem em batches throttled). Se o chunk tem
        múltiplas linhas, faz batch render como ``append_log``.
        """
        if "\n" in msg:
            lines = [ln for ln in msg.splitlines() if ln.strip()]
            if not lines:
                return
            self._render_lines_batch("WARN", lines)
        else:
            self._append("WARN", msg)

    def _render_lines_batch(self, level: str, lines: list[str]) -> None:
        """v0.91.4: helper genérico para batch render de chunks
        multi-linha (LOG, WARN). Chama ``insertHtml`` 1× por
        batch."""
        ts = datetime.now().strftime("%H:%M:%S")
        formatted = [
            f"[{ts}] {level:>5} | {line}" for line in lines
        ]
        for fl in formatted:
            self._lines.append((level, fl))
        if not self._show_level(level):
            return
        color = _LEVEL_COLORS.get(level, "#000000")
        safe_lines = [
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            for text in formatted
        ]
        html = "".join(
            f"<span style='color:{color};'>{s}</span><br>"
            for s in safe_lines
        )
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._text.setTextCursor(cursor)
        self._text.insertHtml(html)
        sb = self._text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def append_error(self, msg: str) -> None:
        self._append("ERROR", msg)

    def append_log(self, msg: str) -> None:
        """
        v0.91.4: append batch otimizado para logs multi-linha.

        Antes (v0.28.3..v0.91.3): cada linha → 1 chamada
        ``_render_line`` → 1 ``insertHtml`` (parser HTML
        custoso). Para chunks de 50 linhas vindos do worker
        throttled (v0.91.2), 50 invocações do parser por
        chunk × 10 chunks/s = ~50% CPU em renderização →
        GUI freezed durante simulações longas.

        Agora: constrói TODA a HTML do chunk numa string
        única, faz ``insertHtml`` UMA vez. Reduz N parses
        para 1 por chunk.
        """
        lines = [ln for ln in msg.splitlines() if ln.strip()]
        if not lines:
            return
        self._render_lines_batch("LOG", lines)

    def clear(self) -> None:
        self._text.clear()
        self._lines.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _append(self, level: str, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{ts}] {level:>5} | {msg}"
        self._lines.append((level, formatted))
        if self._show_level(level):
            self._render_line(level, formatted)

    def _render_line(self, level: str, text: str) -> None:
        color = _LEVEL_COLORS.get(level, "#000000")
        # Append como HTML pra colorizar
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._text.setTextCursor(cursor)
        # Escape HTML para evitar que '<' / '>' quebrem
        safe = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        html = f"<span style='color:{color};'>{safe}</span><br>"
        self._text.insertHtml(html)
        # Scroll to bottom
        sb = self._text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _show_level(self, level: str) -> bool:
        idx = self._filter_combo.currentIndex()
        # 0=Todos, 1=INFO+, 2=WARN+, 3=ERROR
        if idx == 0:
            return True
        order = {"LOG": 0, "INFO": 1, "WARN": 2, "ERROR": 3}
        thresh = idx
        return order.get(level, 0) >= thresh

    def _refilter(self) -> None:
        # Re-renderiza tudo respeitando o filtro
        self._text.clear()
        for lvl, txt in self._lines:
            if self._show_level(lvl):
                self._render_line(lvl, txt)

    def _copy_all(self) -> None:
        QApplication.clipboard().setText(self._text.toPlainText())
