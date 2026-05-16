"""
app.gui.crash_reporter — captura de exceções não-tratadas
+ dump em arquivo (v0.50).

Estratégia:

1. ``install_crash_handler()`` registra ``sys.excepthook``.
2. Em caso de exceção não-tratada, captura traceback +
   info do sistema + estado do projeto.
3. Salva crash dump em ``~/.olivas_atp_studio/crashes/
   crash_YYYYMMDD_HHMMSS.json``.
4. Mostra dialog ao usuário com:
   * Resumo do erro.
   * Path do dump.
   * Botão "Abrir pasta" / "Copiar".

Não enviamos nada automaticamente (privacidade).
Usuário pode anexar manualmente em report ao desenvolvedor.

Para testes: ``install_crash_handler(silent=True)`` desabilita
QMessageBox.
"""

from __future__ import annotations

import json
import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional


_HANDLER_INSTALLED = False
_ORIGINAL_HOOK = None


def crash_dir() -> Path:
    """
    Retorna o diretório onde crash dumps são salvos.

    Default: ``~/.olivas_atp_studio/crashes/``.
    Cria automaticamente se não existir.
    """
    p = Path.home() / ".olivas_atp_studio" / "crashes"
    p.mkdir(parents=True, exist_ok=True)
    return p


def system_info() -> dict:
    """Coleta info do sistema para o crash dump."""
    try:
        from app.core.version import VERSION
    except ImportError:
        VERSION = "unknown"
    return {
        "atp_studio_version": VERSION,
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "executable": sys.executable,
    }


def write_crash_dump(
    exc_type, exc_value, exc_tb,
    extra_context: Optional[dict] = None,
) -> Path:
    """
    Escreve dump em ``crash_dir()/crash_<timestamp>.json``.

    Returns
    -------
    Path
        Caminho do arquivo criado.
    """
    dump_dir = crash_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = dump_dir / f"crash_{ts}.json"

    tb_str = "".join(traceback.format_exception(
        exc_type, exc_value, exc_tb,
    ))

    payload = {
        "timestamp": datetime.now().isoformat(),
        "exception_type": exc_type.__name__ if exc_type else "Unknown",
        "exception_message": str(exc_value),
        "traceback": tb_str,
        "system": system_info(),
    }
    if extra_context:
        payload["context"] = extra_context

    try:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        # Fallback: tenta /tmp ou cwd
        fallback = Path.cwd() / f"crash_{ts}.json"
        fallback.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return fallback
    return path


def show_crash_dialog(
    dump_path: Path, exception_message: str,
) -> None:
    """
    Mostra QMessageBox com resumo + path do dump + botão
    abrir pasta.

    Silencia exceções (não pode crashar o crash handler).
    """
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        if QApplication.instance() is None:
            return  # Sem app — só dump no disco
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Erro inesperado")
        msg.setText(
            "O ATP Studio encontrou um erro inesperado.\n\n"
            f"Detalhe: {exception_message[:200]}\n\n"
            f"Crash dump salvo em:\n{dump_path}\n\n"
            "Por favor, anexe esse arquivo ao reportar o bug."
        )
        copy_btn = msg.addButton(
            "Copiar caminho", QMessageBox.ActionRole,
        )
        msg.addButton(QMessageBox.Close)
        msg.exec()
        if msg.clickedButton() is copy_btn:
            QApplication.clipboard().setText(str(dump_path))
    except Exception:
        # Crash handler nunca deve crashar
        pass


def _crash_hook(exc_type, exc_value, exc_tb):
    """sys.excepthook customizado: dump + dialog."""
    # SystemExit / KeyboardInterrupt: deixa propagação normal
    if issubclass(exc_type, (SystemExit, KeyboardInterrupt)):
        if _ORIGINAL_HOOK is not None:
            _ORIGINAL_HOOK(exc_type, exc_value, exc_tb)
        return

    try:
        path = write_crash_dump(exc_type, exc_value, exc_tb)
        show_crash_dialog(path, str(exc_value))
    except Exception:
        pass    # silenciar para não criar loop de crash

    # Chama original também (stderr trace)
    if _ORIGINAL_HOOK is not None:
        _ORIGINAL_HOOK(exc_type, exc_value, exc_tb)


def install_crash_handler(*, silent: bool = False) -> None:
    """
    Instala o crash handler global.

    Parameters
    ----------
    silent:
        Se True, não mostra QMessageBox (apenas escreve dump).
        Útil para testes automatizados.
    """
    global _HANDLER_INSTALLED, _ORIGINAL_HOOK
    if _HANDLER_INSTALLED:
        return
    _ORIGINAL_HOOK = sys.excepthook
    if silent:
        sys.excepthook = lambda t, v, tb: write_crash_dump(t, v, tb)
    else:
        sys.excepthook = _crash_hook
    _HANDLER_INSTALLED = True


def uninstall_crash_handler() -> None:
    """Remove o crash handler (volta ao default)."""
    global _HANDLER_INSTALLED, _ORIGINAL_HOOK
    if _HANDLER_INSTALLED and _ORIGINAL_HOOK is not None:
        sys.excepthook = _ORIGINAL_HOOK
        _HANDLER_INSTALLED = False


def list_recent_crashes(*, limit: int = 10) -> list[Path]:
    """Lista os N crash dumps mais recentes."""
    dump_dir = crash_dir()
    files = sorted(
        dump_dir.glob("crash_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[:limit]
