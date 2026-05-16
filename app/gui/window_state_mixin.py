"""
app.gui.window_state_mixin — Helper para habilitar
maximize/minimize/restore em QDialogs (v1.7.0 Sprint A).

Por default, ``QDialog`` no Qt6 só tem botão de fechar — não
maximize nem minimize. Esta funcão adiciona os hints corretos +
remember size via QSettings.

Uso
====

::

    from app.gui.window_state_mixin import enable_window_controls

    class MyDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            enable_window_controls(self, settings_key="my_dialog")

Funcionalidades
================

* Botão **Maximize** (canto superior direito)
* Botão **Minimize** (canto superior direito)
* Botão **Close** (mantido)
* Tamanho persistido entre sessões (via QSettings) — opcional
* Helper ``restore_default_size()`` para reset

Anti-regressão
===============

* Não modifica behavior bloqueante de ``exec()`` — apenas adiciona
  controles visuais
* Se ``settings_key`` é None, não persiste nada
* Compatível com Qt5 e Qt6 (mesmas window flags)
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QDialog, QWidget


def enable_window_controls(
    dialog: QDialog,
    *,
    settings_key: Optional[str] = None,
) -> None:
    """
    Habilita maximize, minimize, close + memory de tamanho.

    Parameters
    ----------
    dialog:
        QDialog (ou subclasse) já construído.
    settings_key:
        Se fornecido, salva/restaura geometria via
        ``QSettings("OlivasATPStudio", "OlivasATPStudio")``
        com chave ``"window_geometry/<settings_key>"``.
        Se None, não persiste.

    Side effects
    ------------

    Modifica ``dialog.windowFlags()`` adicionando:
        * ``Qt.WindowMaximizeButtonHint``
        * ``Qt.WindowMinimizeButtonHint``
        * ``Qt.WindowCloseButtonHint`` (já presente por default)
    """
    # Qt window flags — adiciona maximize + minimize
    flags = dialog.windowFlags()
    flags |= Qt.WindowMaximizeButtonHint
    flags |= Qt.WindowMinimizeButtonHint
    flags |= Qt.WindowCloseButtonHint
    dialog.setWindowFlags(flags)

    # Persistência opcional
    if settings_key:
        _attach_geometry_persistence(dialog, settings_key)


def _attach_geometry_persistence(
    dialog: QDialog, settings_key: str,
) -> None:
    """
    Salva geometria ao fechar, restaura ao abrir.

    Hooks into:
    * ``dialog.showEvent`` (restore)
    * ``dialog.closeEvent`` (save)
    """
    settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
    geom_key = f"window_geometry/{settings_key}"

    # Restore — só na primeira show
    saved = settings.value(geom_key)
    if saved is not None:
        try:
            dialog.restoreGeometry(saved)
        except Exception:
            # Settings corrupto / Qt version mismatch → ignora
            pass

    # Hook closeEvent
    original_close = dialog.closeEvent

    def _close_with_save(event):
        try:
            settings.setValue(geom_key, dialog.saveGeometry())
        except Exception:
            pass
        return original_close(event)

    dialog.closeEvent = _close_with_save


def restore_default_size(
    dialog: QDialog, *, settings_key: Optional[str] = None,
) -> None:
    """
    Reset geometria para o default (chamado por menu "View →
    Reset Window Size" se desejado).
    """
    if settings_key:
        settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
        settings.remove(f"window_geometry/{settings_key}")
    # Voltar para sizeHint
    dialog.adjustSize()
