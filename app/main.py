"""
Olivas ATP Studio — entry point.

v0.83 — Splash screen + Window icon (favicon):
* Splash com logo + barra de progresso + tagline
* App icon (favicon) configurado em todas janelas
* Welcome dialog após splash (preserva v0.28.2-PRO)
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication


# Paths
_APP_RESOURCES = Path(__file__).resolve().parent / "resources"
_LOGO_PATH_ICO = _APP_RESOURCES / "logo.ico"
_LOGO_PATH_PNG = _APP_RESOURCES / "logo.png"
# v1.4.2: prioriza .ico (multi-resolução nativo Windows) sobre .png.
# .ico contém múltiplas resoluções (16/32/48/64/128px) que Windows
# usa diretamente em title bar / taskbar / Alt-Tab. PNG era escalado
# mal para resoluções pequenas (16/32px da title bar).
_LOGO_PATH = _LOGO_PATH_ICO if _LOGO_PATH_ICO.is_file() else _LOGO_PATH_PNG


def _setup_application_icon(app: QApplication) -> None:
    """
    v0.83: configura ícone global do aplicativo (favicon).
    v1.4.2: prefere .ico multi-resolução para visibilidade
    correta em title bar Windows.

    Usado em:
    * Title bar de todas as janelas (Windows)
    * Dock/taskbar icon
    * Alt-Tab thumbnail
    """
    if _LOGO_PATH.is_file():
        icon = QIcon(str(_LOGO_PATH))
        app.setWindowIcon(icon)


def main() -> None:
    app = QApplication(sys.argv)

    # v0.83: ícone global (favicon)
    _setup_application_icon(app)

    # v0.83: splash screen
    from app.gui.splash_screen import OlivasSplashScreen
    splash = OlivasSplashScreen()
    splash.show()
    splash.set_progress(5, "Iniciando Olivas Power System Studio...")

    # Carregamento incremental com progress updates
    splash.set_progress(20, "Carregando módulos do core...")
    from app.gui.main_window import MainWindow

    splash.set_progress(45, "Carregando preprocessor + standards...")
    from app.gui.welcome_dialog import (
        WelcomeDialog, should_show_welcome, remember_dont_show,
    )

    splash.set_progress(70, "Inicializando interface gráfica...")
    window = MainWindow()
    # v0.83: garante que MainWindow também tem o ícone
    if _LOGO_PATH.is_file():
        window.setWindowIcon(QIcon(str(_LOGO_PATH)))

    splash.set_progress(90, "Pronto.")

    # Pequeno delay para o usuário ver "Pronto" antes do dismiss
    import time
    time.sleep(0.3)
    splash.set_progress(100, "")

    splash.finish(window)
    window.show()

    # v0.90: oferece recovery de autosaves órfãos antes do welcome.
    # Se o usuário recuperar, pulamos o welcome (já tem trabalho).
    recovered = False
    try:
        recovered = window.offer_recovery_if_available()
    except Exception:
        pass

    # Mostra welcome dialog se ainda não suprimido E nada foi recuperado.
    if not recovered and should_show_welcome(window._settings):
        recent = window._load_recent_files()
        dlg = WelcomeDialog(window, recent_files=recent)
        # Conectar sinais aos métodos do MainWindow
        dlg.open_atp_requested.connect(window._on_open)
        dlg.open_sch_requested.connect(window._on_pp_open_sch)
        dlg.new_pp_requested.connect(window._on_pp_new_project)
        dlg.recent_clicked.connect(window._open_recent)
        # v0.89: template cards
        dlg.template_requested.connect(window._on_pp_new_from_template)
        dlg.exec()
        if dlg.dont_show_again:
            remember_dont_show(window._settings)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
