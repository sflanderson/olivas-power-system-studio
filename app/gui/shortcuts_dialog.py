"""
app.gui.shortcuts_dialog — diálogo "Atalhos do teclado"
(v0.91).

Sumário visual dos shortcuts do editor visual + main window.
Acessível via menu Ajuda → "Atalhos do teclado…" ou tecla
``?`` (Shift+/) no foco da MainWindow.

Filosofia
==========

Engenheiros experientes querem dominar o teclado para
edição rápida (rotate/mirror/wire mode). Um cheat-sheet
visível na hora resolve curva de aprendizado sem precisar
abrir a documentação.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


# Atalhos agrupados por categoria. Cada entry: (tecla, descrição).
# Adicionar novos atalhos aqui — o dialog renderiza
# automaticamente.
_SHORTCUTS = {
    "Arquivo": [
        ("Ctrl+O",        "Abrir .atp"),
        ("Ctrl+S",        "Salvar"),
        ("Ctrl+Shift+S",  "Salvar como…"),
        ("Ctrl+W",        "Fechar caso"),
    ],
    "Edição (canvas)": [
        ("Ctrl+Z",        "Desfazer"),
        ("Ctrl+Y",        "Refazer (ou Ctrl+Shift+Z)"),
        ("Del / Backspace", "Excluir seleção"),
        ("R",             "Rotacionar 90° anti-horário"),
        ("Shift+R",       "Rotacionar 90° horário"),
        ("E",             "Espelhar (mirror X)"),
        ("Ctrl+A",        "Selecionar tudo"),
    ],
    "Ferramentas (canvas)": [
        ("V",             "Modo selecionar"),
        ("W",             "Modo fio (desenhar wires)"),
        ("Esc",           "Cancelar wire em progresso / volta ao select"),
    ],
    "Zoom + navegação": [
        ("Ctrl+Wheel",    "Zoom in/out"),
        ("+ / =",         "Zoom in"),
        ("-",             "Zoom out"),
        ("0",             "Zoom 100%"),
        ("Middle-drag",   "Pan (arrastar)"),
        ("Space+drag",    "Pan alternativo"),
    ],
    "Painéis (PpEditor)": [
        ("F9",            "Mostrar/ocultar paleta"),
        ("F10",           "Mostrar/ocultar propriedades"),
        ("F11",           "Modo tela cheia (oculta tudo)"),
    ],
    "Análises": [
        ("F1",            "Como executar um estudo? (guia)"),
        ("F7",            "Estudo do barramento (pipeline)"),
    ],
    "Ajuda": [
        ("?  ou Shift+/", "Este diálogo de atalhos"),
    ],
}


class ShortcutsDialog(QDialog):
    """
    Diálogo modal listando atalhos de teclado do app.

    Uso::

        from app.gui.shortcuts_dialog import ShortcutsDialog
        ShortcutsDialog(parent=window).exec()
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Atalhos do teclado")
        self.setMinimumWidth(560)
        self.setMinimumHeight(540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel("<h2>⌨️ Atalhos do teclado</h2>", self)
        layout.addWidget(title)

        hint = QLabel(
            "<i>Domínio do teclado = edição mais rápida. "
            "Foque o canvas (clique nele) para que os atalhos "
            "do editor visual respondam.</i>",
            self,
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555;")
        layout.addWidget(hint)

        # Scroll area para suportar adição futura de mais
        # atalhos sem aumentar tamanho do dialog.
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 8, 4, 8)
        content_layout.setSpacing(12)

        for category, shortcuts in _SHORTCUTS.items():
            content_layout.addWidget(self._build_category(category, shortcuts))

        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        # Botão fechar
        btn_box = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        btn_box.rejected.connect(self.reject)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)

    def _build_category(
        self, category: str, shortcuts: list[tuple[str, str]],
    ) -> QWidget:
        """Renderiza uma seção: header + tabela teclas/descrições."""
        w = QWidget(self)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        header = QLabel(f"<b>{category}</b>", self)
        h_font = QFont()
        h_font.setPointSize(10)
        h_font.setBold(True)
        header.setFont(h_font)
        header.setStyleSheet("color: #556B2F; padding: 4px 0;")
        v.addWidget(header)

        for key, desc in shortcuts:
            row = QHBoxLayout()
            row.setContentsMargins(8, 0, 0, 0)
            row.setSpacing(12)
            key_lbl = QLabel(f"<code>{key}</code>", self)
            key_lbl.setFont(QFont("Consolas, Courier New, monospace", 10))
            key_lbl.setStyleSheet(
                "background: #F5F5DC; padding: 2px 6px; "
                "border: 1px solid #B5D4A8; border-radius: 3px; "
                "color: #2A2D24;"
            )
            key_lbl.setMinimumWidth(140)
            key_lbl.setMaximumWidth(180)
            row.addWidget(key_lbl, 0)
            desc_lbl = QLabel(desc, self)
            desc_lbl.setWordWrap(True)
            row.addWidget(desc_lbl, 1)
            v.addLayout(row)
        return w
