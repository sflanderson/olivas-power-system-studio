"""
app.gui.update_checker — verificador de updates remotos
(v0.50).

Verifica em servidor remoto (URL configurável) se há
versão mais recente disponível. Não baixa nem instala
automaticamente — apenas notifica o usuário.

Estratégia:

* Endpoint retorna JSON ``{"version": "X.Y.Z", "url": "..."}``.
* Default endpoint: ``https://atp-studio.olivas.dev/version.json``
  (configurável via QSettings).
* Check em background via ``QThread`` para não bloquear GUI.
* Cache: 1 check por 24h por default.

Comportamento sem rede:
* Falha silenciosa (logs no console mas não modal).
* Não impede uso do app.
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal


# URL default — pode ser sobrescrito por QSettings
DEFAULT_UPDATE_URL = "https://atp-studio.olivas.dev/version.json"

# TTL do cache (segundos): 24h
UPDATE_CHECK_TTL_S = 24 * 3600


class UpdateInfo:
    """Info de uma versão remota disponível."""

    def __init__(
        self,
        version: str,
        url: str = "",
        notes: str = "",
    ):
        self.version = version
        self.url = url
        self.notes = notes


class UpdateCheckWorker(QObject):
    """
    Worker QObject para verificar update remoto em
    background. Emite signals:

    * ``update_available(UpdateInfo)`` — versão remota maior.
    * ``up_to_date()`` — versão atual está atualizada.
    * ``check_failed(str)`` — erro de rede / parse.
    """

    update_available = Signal(object)   # UpdateInfo
    up_to_date = Signal()
    check_failed = Signal(str)

    def __init__(
        self,
        url: str = DEFAULT_UPDATE_URL,
        timeout_s: float = 5.0,
    ):
        super().__init__()
        self._url = url
        self._timeout_s = timeout_s

    def run(self) -> None:
        """Executa o check (chamado via QThread.started)."""
        try:
            from app.core.version import is_newer, VERSION
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": f"OlivasATPStudio/{VERSION}"},
            )
            with urllib.request.urlopen(
                req, timeout=self._timeout_s,
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            remote_version = str(data.get("version", ""))
            if not remote_version:
                self.check_failed.emit("Resposta sem campo 'version'")
                return
            if is_newer(remote_version):
                info = UpdateInfo(
                    version=remote_version,
                    url=str(data.get("url", "")),
                    notes=str(data.get("notes", "")),
                )
                self.update_available.emit(info)
            else:
                self.up_to_date.emit()
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            self.check_failed.emit(f"Network error: {e}")
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.check_failed.emit(f"Parse error: {e}")
        except Exception as e:
            self.check_failed.emit(f"Unexpected: {e}")


def make_update_check_thread(
    url: str = DEFAULT_UPDATE_URL,
    timeout_s: float = 5.0,
) -> tuple[QThread, UpdateCheckWorker]:
    """
    Cria thread + worker para verificar update.

    Caller é responsável por:
    * Conectar signals (update_available, up_to_date, check_failed).
    * Chamar thread.start().
    """
    thread = QThread()
    worker = UpdateCheckWorker(url, timeout_s)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.update_available.connect(thread.quit)
    worker.up_to_date.connect(thread.quit)
    worker.check_failed.connect(thread.quit)
    return thread, worker


def should_check_now(last_check_timestamp: Optional[float]) -> bool:
    """
    Retorna True se a última verificação foi há mais de
    ``UPDATE_CHECK_TTL_S`` (24h default).
    """
    if last_check_timestamp is None:
        return True
    return (time.time() - last_check_timestamp) > UPDATE_CHECK_TTL_S
