"""
app.gui.splash_screen — splash screen de inicialização do
Olivas ATP Studio (v0.83).

Tela preta com:
* Logo centralizado (480×479 px, ajustado para max 320 px).
* Barra de progresso animada abaixo do logo.
* Texto da versão + tagline da marca.
* Auto-dismiss quando MainWindow estiver pronto.

Uso típico (em ``app/main.py``):

::

    from app.gui.splash_screen import OlivasSplashScreen

    app = QApplication(sys.argv)
    splash = OlivasSplashScreen()
    splash.show()
    splash.set_progress(0, "Carregando módulos...")

    # ... carregar pesado ...
    splash.set_progress(50, "Inicializando GUI...")

    main_window = MainWindow()
    splash.set_progress(100, "Pronto.")

    splash.finish(main_window)
    main_window.show()

Design (Oliveira)
==================

* Fundo: preto puro #000000 (foco no logo)
* Progress bar:
  - chunk: gradiente lime (#BFFF00) → cyan (#00A8E8)
  - track: olive-deep escuro (#2A2D24)
* Texto: cream (#FAFAF5) com tagline em olive-pale.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication, QLabel, QProgressBar, QSplashScreen,
    QVBoxLayout, QWidget,
)


# Logo path
_LOGO_PATH = Path(__file__).resolve().parent.parent / "resources" / "logo.png"


# Splash dimensions
# v0.91.1: alturas recalculadas para evitar clipping do logo.
# Layout precisa: logo + 4×spacing(16) + tagline(20) + progress(8) +
# status(20) + version(15) + 2×margin(40) = ~520-560 px de altura.
SPLASH_WIDTH = 600
SPLASH_HEIGHT = 560
LOGO_MAX_DIM = 300


class OlivasSplashScreen(QWidget):
    """
    Splash screen padrão do Olivas ATP Studio.

    Implementação como ``QWidget`` frameless+top (em vez de
    ``QSplashScreen``) para permitir layout customizado com
    logo + título + progress bar + texto de status.

    API
    ====

    * ``set_progress(value: int, message: str = "")``: 0–100.
    * ``finish(window)``: fecha splash e foca window.
    * ``show()``: exibe centralizado na tela.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Frameless + always-on-top
        self.setWindowFlags(
            Qt.SplashScreen
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setFixedSize(SPLASH_WIDTH, SPLASH_HEIGHT)

        # Background: black (foco no logo)
        self.setStyleSheet(
            "QWidget { background-color: #000000; }"
        )

        self._build_ui()
        self._center_on_screen()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        # ---- Logo (centralizado) ----
        self._logo_label = QLabel(self)
        self._logo_label.setAlignment(Qt.AlignCenter)
        self._logo_label.setStyleSheet(
            "QLabel { background-color: transparent; }"
        )
        if _LOGO_PATH.is_file():
            pixmap = QPixmap(str(_LOGO_PATH))
            # Scale preservando aspect ratio
            scaled = pixmap.scaled(
                LOGO_MAX_DIM, LOGO_MAX_DIM,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._logo_label.setPixmap(scaled)
        else:
            self._logo_label.setText("OLIVAS")
            self._logo_label.setStyleSheet(
                "QLabel { color: #BFFF00; font-size: 48pt; "
                "font-weight: bold; background: transparent; }"
            )
        layout.addWidget(self._logo_label, alignment=Qt.AlignCenter)

        # ---- Tagline ----
        tagline = QLabel("ATP Power System Simulation", self)
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet(
            "QLabel { color: #B5D4A8; font-size: 11pt; "
            "font-style: italic; background: transparent; }"
        )
        layout.addWidget(tagline)

        # ---- Progress bar ----
        self._progress = QProgressBar(self)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(8)
        self._progress.setStyleSheet(
            "QProgressBar { "
            "  background-color: #2A2D24; "
            "  border: 1px solid #4a4d3f; "
            "  border-radius: 4px; "
            "} "
            "QProgressBar::chunk { "
            "  background: qlineargradient("
            "    x1:0, y1:0, x2:1, y2:0, "
            "    stop:0 #BFFF00, stop:1 #00A8E8); "
            "  border-radius: 3px; "
            "}"
        )
        layout.addWidget(self._progress)

        # ---- Status message ----
        self._status_label = QLabel("Iniciando...", self)
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setStyleSheet(
            "QLabel { color: #FAFAF5; font-size: 9pt; "
            "background: transparent; }"
        )
        layout.addWidget(self._status_label)

        # ---- Version footer ----
        try:
            from app.core.version import VERSION
            ver_text = f"versão {VERSION}"
        except ImportError:
            ver_text = ""
        if ver_text:
            ver_label = QLabel(ver_text, self)
            ver_label.setAlignment(Qt.AlignCenter)
            ver_label.setStyleSheet(
                "QLabel { color: #6B8E23; font-size: 8pt; "
                "background: transparent; }"
            )
            layout.addWidget(ver_label)

    def _center_on_screen(self) -> None:
        """Centraliza splash na tela primária."""
        try:
            screen = QApplication.primaryScreen()
            if screen is None:
                return
            geom = screen.availableGeometry()
            x = geom.center().x() - self.width() // 2
            y = geom.center().y() - self.height() // 2
            self.move(x, y)
        except Exception:
            pass

    def set_progress(
        self, value: int, message: str = "",
        *, process_events: bool = True,
    ) -> None:
        """
        Atualiza barra (0-100) + mensagem de status.

        Parameters
        ----------
        value:
            Progress 0-100 (clampado).
        message:
            Texto de status opcional.
        process_events:
            v0.83.4: se True (default), chama
            ``QApplication.processEvents()`` para repaint
            imediato durante carregamento pesado. Use
            ``False`` em testes para evitar side effects
            do event loop (eventos stale acumulados em
            suite com 3000+ testes podem alterar valores
            de widgets).
        """
        self._progress.setValue(max(0, min(100, value)))
        if message:
            self._status_label.setText(message)
        if process_events:
            QApplication.processEvents()

    def finish(self, target_widget: QWidget) -> None:
        """
        Fecha splash + transfere foco para ``target_widget``.

        Use após ``MainWindow`` estiver pronto.
        """
        self.close()
        try:
            target_widget.raise_()
            target_widget.activateWindow()
        except Exception:
            pass


def show_splash_with_callback(
    init_callback,
    *,
    min_duration_ms: int = 1500,
    parent: Optional[QWidget] = None,
) -> OlivasSplashScreen:
    """
    Helper: mostra splash + executa callback de inicialização
    com progress updates + retorna splash para finish() pelo
    caller.

    O ``init_callback(splash)`` é chamado com o splash como
    argumento, podendo invocar ``splash.set_progress(...)`` ao
    longo do trabalho de carregamento.

    Garante duração mínima de ``min_duration_ms`` mesmo se o
    callback for instantâneo (UX: usuário tem que ver o
    splash).
    """
    import time
    splash = OlivasSplashScreen(parent)
    splash.show()
    QApplication.processEvents()
    start = time.time()
    init_callback(splash)
    elapsed_ms = (time.time() - start) * 1000
    if elapsed_ms < min_duration_ms:
        # Cria delay residual com QTimer
        remaining = min_duration_ms - elapsed_ms
        QTimer.singleShot(int(remaining), lambda: None)
    return splash
