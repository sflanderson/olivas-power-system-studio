"""
app.gui.license_dialog — Dialog de ativação de licença
(v4.1.0 commercial Sprint 2).

Usado via menu Ajuda → Ativar Licença...

UI:
* Status atual (tier + dias até expirar + machine_id mascarado).
* Field para colar chave (formato OLV-TIER-...).
* Botões:
  - Ativar (chama license_server_client.activate)
  - Renovar (chama try_refresh)
  - Remover licença (chama clear_local_license)
* Erros HTTP traduzidos para mensagens amigáveis.
* Link para página de compra/renovação (a definir).
"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)


_PURCHASE_URL = "https://olivas.com.br/comprar"  # placeholder W12


_ERROR_MESSAGES = {
    "server_not_configured": (
        "URL do servidor de licença não configurada. "
        "Verifique a variável OLIVAS_LICENSE_SERVER_URL."
    ),
    "empty_key": "Cole a chave no campo antes de ativar.",
    "invalid_key": (
        "Chave inválida — verifique se copiou a chave completa "
        "(formato OLV-...)."
    ),
    "key_not_found_or_revoked": (
        "Chave não encontrada ou foi revogada. "
        "Entre em contato com o suporte se essa compra foi recente."
    ),
    "key_expired": (
        "Esta chave expirou. Renove sua assinatura em "
        f"{_PURCHASE_URL}."
    ),
    "max_activations_exceeded": (
        "Esta chave já foi ativada no máximo permitido de máquinas. "
        "Use a opção 'Remover licença' nas outras máquinas ou entre "
        "em contato com o suporte."
    ),
    "network_error": (
        "Não foi possível alcançar o servidor de licença. "
        "Verifique sua conexão e tente novamente."
    ),
    "no_local_token": (
        "Nenhuma licença ativa local — ative uma chave primeiro."
    ),
}


def _human_error(code: str | None, message: str | None) -> str:
    if code and code in _ERROR_MESSAGES:
        return _ERROR_MESSAGES[code]
    if code and code.startswith("http_"):
        return (
            f"O servidor recusou a operação ({code}). "
            f"Detalhe: {message or 'sem mensagem'}."
        )
    return message or "Falha desconhecida."


class LicenseDialog(QDialog):
    """
    Dialog para ativar / renovar / remover licença comercial.

    Em sucesso, atualiza QSettings via license_server_client e
    invalida cache de feature_gates.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ativar Licença — Olivas Power System Studio")
        self.setMinimumWidth(540)
        self._build_ui()
        self._refresh_status()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        header = QLabel(
            "<b>Licença do Olivas Power System Studio</b><br>"
            "Cole a chave recebida por e-mail após a compra para "
            "destravar features Pro (audit trail SHA256, relatórios "
            "profissionais, análises Monte Carlo, AI laudos)."
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Status atual
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(
            "QLabel { padding: 8px; background: #f4f4f4; "
            "border: 1px solid #ccc; border-radius: 4px; }"
        )
        layout.addWidget(self._status_label)

        # Machine id (info útil para suporte)
        self._machine_label = QLabel()
        self._machine_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self._machine_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # Campo da chave
        layout.addWidget(QLabel("Chave de licença:"))
        self._key_field = QLineEdit()
        self._key_field.setPlaceholderText("OLV-COMM-AA001234-20270101-ABCD1234")
        layout.addWidget(self._key_field)

        # Botões de ação
        actions = QHBoxLayout()
        self._activate_btn = QPushButton("Ativar")
        self._activate_btn.setDefault(True)
        self._activate_btn.clicked.connect(self._on_activate)
        actions.addWidget(self._activate_btn)

        self._refresh_btn = QPushButton("Renovar token")
        self._refresh_btn.clicked.connect(self._on_refresh)
        actions.addWidget(self._refresh_btn)

        self._clear_btn = QPushButton("Remover licença")
        self._clear_btn.clicked.connect(self._on_clear)
        actions.addWidget(self._clear_btn)

        actions.addStretch(1)
        purchase_btn = QPushButton("Comprar / renovar online...")
        purchase_btn.setFlat(True)
        purchase_btn.clicked.connect(self._on_open_purchase)
        actions.addWidget(purchase_btn)
        layout.addLayout(actions)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        layout.addWidget(sep2)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText("Fechar")
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        layout.addWidget(bb)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _refresh_status(self) -> None:
        from app.commercial.feature_gates import current_tier
        from app.commercial.license_server_client import (
            check_active_license, days_until_expiry,
        )
        from app.commercial.machine_id import (
            get_machine_id, masked_machine_id,
        )

        tier = current_tier()
        license = check_active_license()
        days = days_until_expiry()

        if tier == "educational":
            self._status_label.setText(
                "<b>Status:</b> nenhuma licença ativa "
                "(tier <code>educational</code>). "
                "Features Pro estão bloqueadas."
            )
            self._status_label.setStyleSheet(
                "QLabel { padding: 8px; background: #fff4e0; "
                "border: 1px solid #f5a623; border-radius: 4px; }"
            )
        elif license is not None:
            self._status_label.setText(
                f"<b>Status:</b> ✓ ativa<br>"
                f"<b>Tier:</b> <code>{license.tier}</code><br>"
                f"<b>Cliente:</b> <code>{license.customer_id}</code><br>"
                f"<b>Token expira em:</b> {days} dias"
            )
            self._status_label.setStyleSheet(
                "QLabel { padding: 8px; background: #e6f4ea; "
                "border: 1px solid #34a853; border-radius: 4px; }"
            )
        else:
            self._status_label.setText(
                f"<b>Status:</b> tier <code>{tier}</code> "
                "(via fallback legacy)."
            )

        # Garante que machine_id existe (gera+persiste se 1ª vez)
        get_machine_id()
        self._machine_label.setText(
            f"ID da máquina (anônimo, enviado ao servidor): "
            f"<code>{masked_machine_id()}</code>"
        )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_activate(self) -> None:
        key = self._key_field.text().strip()
        if not key:
            QMessageBox.warning(
                self, "Vazia",
                "Cole a chave no campo antes de ativar.",
            )
            return
        if not key.startswith("OLV-"):
            confirm = QMessageBox.question(
                self, "Formato suspeito",
                "Chaves do Olivas começam com 'OLV-'. "
                "Tentar mesmo assim?",
            )
            if confirm != QMessageBox.Yes:
                return

        from app.commercial.license_server_client import activate
        from app.commercial.machine_id import get_machine_id

        machine_id = get_machine_id()
        result = activate(key, machine_id)

        if result.ok and result.license is not None:
            QMessageBox.information(
                self, "Licença ativada",
                f"Tier <b>{result.license.tier}</b> ativado.<br>"
                f"Reinicie operações de relatório/análise para usar "
                f"as features Pro destravadas.",
            )
            self._key_field.clear()
            self._refresh_status()
        else:
            QMessageBox.warning(
                self, "Falha na ativação",
                _human_error(result.error_code, result.error_message),
            )

    def _on_refresh(self) -> None:
        from app.commercial.license_server_client import try_refresh

        result = try_refresh()
        if result.ok and result.license is not None:
            QMessageBox.information(
                self, "Token renovado",
                f"Token válido até "
                f"{result.license.expiry_unix} (unix).",
            )
            self._refresh_status()
        else:
            QMessageBox.warning(
                self, "Falha ao renovar",
                _human_error(result.error_code, result.error_message),
            )

    def _on_clear(self) -> None:
        confirm = QMessageBox.question(
            self, "Confirmar",
            "Remover licença local desta máquina?\n\n"
            "Você precisará ativar novamente para usar features Pro.",
        )
        if confirm != QMessageBox.Yes:
            return

        from app.commercial.license_server_client import clear_local_license
        clear_local_license()
        QMessageBox.information(
            self, "Removida",
            "Licença local removida. Tier voltou para 'educational'.",
        )
        self._refresh_status()

    def _on_open_purchase(self) -> None:
        QDesktopServices.openUrl(QUrl(_PURCHASE_URL))
