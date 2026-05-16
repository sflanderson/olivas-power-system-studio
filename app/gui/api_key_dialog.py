"""
app.gui.api_key_dialog — dialog para configurar
ANTHROPIC_API_KEY persistente (v0.81).

Usado via menu Arquivo → Configurar API Key Claude.

UI:
* Field para inserir/colar API key (com toggle show/hide).
* Status atual (mascarado).
* Botão "Testar" — chama Anthropic API com modelo cheap +
  prompt curto para verificar key válida.
* Botão "Salvar" — persiste via api_key_manager.
* Link para anthropic.com/console (onde criar key).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout,
)


class ApiKeyDialog(QDialog):
    """
    Dialog para configurar e testar a Anthropic API key.

    Após salvar, chat panels reativam automaticamente
    (via api_key_manager cache invalidation).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar API Key Claude")
        self.setMinimumWidth(500)
        self._build_ui()
        self._refresh_status()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header com info
        header = QLabel(
            "<b>Anthropic API Key</b><br>"
            "Configure sua chave de API para habilitar o "
            "assistente Claude no editor visual e no chat."
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Status atual
        self._status_label = QLabel()
        self._status_label.setStyleSheet(
            "QLabel { padding: 6px; background: #f0f0f0; "
            "border: 1px solid #ccc; border-radius: 3px; }"
        )
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # Input field
        layout.addWidget(QLabel("API Key:"))
        self._key_field = QLineEdit()
        self._key_field.setEchoMode(QLineEdit.Password)
        self._key_field.setPlaceholderText("sk-ant-api03-...")
        layout.addWidget(self._key_field)

        # Show/hide toggle
        show_row = QHBoxLayout()
        show_chk = QCheckBox("Mostrar")
        show_chk.toggled.connect(self._on_toggle_show)
        show_row.addWidget(show_chk)
        show_row.addStretch(1)
        # Botão "Obter chave" → abre console.anthropic.com
        get_btn = QPushButton("Obter chave...")
        get_btn.setFlat(True)
        get_btn.clicked.connect(self._on_open_console)
        show_row.addWidget(get_btn)
        layout.addLayout(show_row)

        # Test button
        test_row = QHBoxLayout()
        test_btn = QPushButton("Testar conexão")
        test_btn.clicked.connect(self._on_test)
        test_row.addWidget(test_btn)
        # Botão "Limpar"
        clear_btn = QPushButton("Remover chave salva")
        clear_btn.clicked.connect(self._on_clear)
        test_row.addWidget(clear_btn)
        test_row.addStretch(1)
        layout.addLayout(test_row)

        # Save / Cancel
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        layout.addWidget(sep2)

        bb = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
        )
        bb.button(QDialogButtonBox.Save).setText("Salvar")
        bb.button(QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self._on_save)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _refresh_status(self) -> None:
        from app.core.api_key_manager import (
            is_configured, masked_key,
        )
        if is_configured():
            self._status_label.setText(
                f"<b>Status:</b> ✓ configurada "
                f"<code>{masked_key()}</code>"
            )
            self._status_label.setStyleSheet(
                "QLabel { padding: 6px; background: #e6f4ea; "
                "border: 1px solid #34a853; border-radius: 3px; }"
            )
        else:
            self._status_label.setText(
                "<b>Status:</b> ✗ não configurada — "
                "chat Claude desabilitado."
            )
            self._status_label.setStyleSheet(
                "QLabel { padding: 6px; background: #fce8e6; "
                "border: 1px solid #d93025; border-radius: 3px; }"
            )

    def _on_toggle_show(self, checked: bool) -> None:
        self._key_field.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password,
        )

    def _on_open_console(self) -> None:
        """Abre página da Anthropic onde se obtém a chave."""
        QDesktopServices.openUrl(QUrl("https://console.anthropic.com/"))

    def _on_test(self) -> None:
        """Testa a chave fazendo chamada simples à API."""
        key = self._key_field.text().strip()
        if not key:
            # Tenta key salva
            from app.core.api_key_manager import get_anthropic_api_key
            key = get_anthropic_api_key() or ""
        if not key:
            QMessageBox.warning(
                self, "Sem chave",
                "Cole a chave no campo ou salve uma primeiro.",
            )
            return
        if not key.startswith("sk-"):
            QMessageBox.warning(
                self, "Formato inválido",
                "Chaves Anthropic começam com 'sk-ant-...'.",
            )
            return

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            # Mensagem mínima — modelo cheap (Haiku) + 1 token
            resp = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            QMessageBox.information(
                self, "Conexão OK",
                f"Chave válida! Modelo respondeu: "
                f"{resp.content[0].text[:60] if resp.content else 'OK'}",
            )
        except ImportError:
            QMessageBox.critical(
                self, "Anthropic SDK ausente",
                "Pacote 'anthropic' não instalado.\n"
                "Execute: pip install anthropic",
            )
        except Exception as e:
            QMessageBox.warning(
                self, "Falha no teste",
                f"Erro ao chamar API:\n{e}",
            )

    def _on_clear(self) -> None:
        confirm = QMessageBox.question(
            self, "Confirmar",
            "Remover a chave API salva?\n"
            "O chat Claude será desabilitado.",
        )
        if confirm == QMessageBox.Yes:
            from app.core.api_key_manager import clear_anthropic_api_key
            clear_anthropic_api_key()
            self._key_field.clear()
            self._refresh_status()
            QMessageBox.information(
                self, "Removida", "Chave API removida.",
            )

    def _on_save(self) -> None:
        key = self._key_field.text().strip()
        if not key:
            QMessageBox.warning(
                self, "Vazia",
                "Insira uma chave para salvar (ou Cancelar).",
            )
            return
        if not key.startswith("sk-"):
            confirm = QMessageBox.question(
                self, "Formato suspeito",
                "Chaves Anthropic geralmente começam com 'sk-ant-'.\n"
                "Salvar mesmo assim?",
            )
            if confirm != QMessageBox.Yes:
                return
        from app.core.api_key_manager import set_anthropic_api_key
        set_anthropic_api_key(key)
        QMessageBox.information(
            self, "Salva",
            "Chave salva. Reabra os chats para reativar.",
        )
        self.accept()
