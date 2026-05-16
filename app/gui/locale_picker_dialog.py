"""
app.gui.locale_picker_dialog — Dialog para troca de idioma
(v2.1.1).

Endereça gap deferred desde v2.1.0: agora usuário pode trocar
idioma via UI (sem necessidade de chamar `set_locale()` em código).

API
====

::

    from app.gui.locale_picker_dialog import LocalePickerDialog

    dlg = LocalePickerDialog(parent=main_window)
    dlg.exec()
    # Após apply, locale ativo persistido em QSettings

Persistência
=============

Locale escolhido é salvo em ``QSettings("OlivasATPStudio",
"OlivasATPStudio")`` chave ``"locale"``. MainWindow.__init__
deve ler essa chave no startup e chamar set_locale() — fica
para v2.1.2 (escopo travado v2.1.1: apenas dialog).

Princípios
===========

* Combo lista todas as locales via :func:`app.i18n.get_locale_choices`
* Selection inicial = locale atual (via get_locale)
* Apply chama set_locale + persiste QSettings
* setWindowTitle feedback (paridade lições anteriores: sem
  QMessageBox bloqueante em fluxos testes)
* Anti-crash: try/except em apply
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.i18n import (
    _, get_locale, get_locale_choices, set_locale,
)


class LocalePickerDialog(QDialog):
    """
    Dialog simples para troca de idioma.

    Layout:
    * Header (label explicativo)
    * Combo de locale (PT/EN/ES)
    * Aviso de restart (mudanças em menus exigem restart)
    * Botões Apply / Close
    """

    SETTINGS_KEY_LOCALE = "locale"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "🌐 Idioma — Olivas Power System Studio"
        )
        self.resize(480, 240)
        self.setMinimumWidth(420)

        # v1.7.0 Sprint A: maximize/minimize controls (paridade)
        try:
            from app.gui.window_state_mixin import enable_window_controls
            enable_window_controls(self, settings_key="locale_picker")
        except Exception:
            pass

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(
            "<h2>🌐 Selecione o idioma</h2>"
            "<p><i>Olivas suporta Português (default), Inglês e "
            "Espanhol. A escolha é persistida entre sessões.</i></p>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Combo
        combo_row = QHBoxLayout()
        combo_row.addWidget(QLabel("<b>Idioma:</b>"))
        self.locale_combo = QComboBox()
        for code, label in get_locale_choices():
            self.locale_combo.addItem(label, code)
        # Default selection = locale atual
        current = get_locale()
        for i in range(self.locale_combo.count()):
            if self.locale_combo.itemData(i) == current:
                self.locale_combo.setCurrentIndex(i)
                break
        combo_row.addWidget(self.locale_combo, 1)
        layout.addLayout(combo_row)

        # Aviso restart
        warning = QLabel(
            "<small><i>⚠ Mudanças em menus principais aplicam-se "
            "no próximo abrir do Olivas. Diálogos novos já abrem "
            "no idioma escolhido.</i></small>"
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "QLabel { background-color: #FFF8DC; "
            "border-left: 3px solid #FFA000; "
            "padding: 6px 10px; }"
        )
        layout.addWidget(warning)

        # Action buttons
        actions = QHBoxLayout()
        self.btn_apply = QPushButton("✓ Aplicar")
        self.btn_apply.setStyleSheet(
            "QPushButton { background-color: #2ca02c; "
            "color: white; font-weight: bold; padding: 6px 16px; }"
        )
        self.btn_apply.clicked.connect(self._on_apply)
        actions.addWidget(self.btn_apply)

        actions.addStretch()

        self.btn_close = QPushButton("Fechar")
        self.btn_close.clicked.connect(self.reject)
        actions.addWidget(self.btn_close)

        layout.addLayout(actions)

    def _on_apply(self) -> None:
        """Aplica locale selecionado + persiste QSettings."""
        try:
            new_locale = self.locale_combo.currentData()
            if not new_locale:
                return
            set_locale(new_locale)
            # Persiste
            settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
            settings.setValue(self.SETTINGS_KEY_LOCALE, new_locale)
            # Status feedback (sem QMessageBox bloqueante)
            self.setWindowTitle(
                f"🌐 Idioma aplicado: {new_locale.upper()} — "
                "reinicie para aplicar em todos os menus"
            )
        except Exception as e:
            self.setWindowTitle(
                f"🌐 Erro ao aplicar idioma: {type(e).__name__}"
            )
