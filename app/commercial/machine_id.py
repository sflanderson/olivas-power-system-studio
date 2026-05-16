"""
app.commercial.machine_id — Hardware fingerprint
(v4.1.0 commercial Sprint 1).

Filosofia
=========

* **Determinístico**: mesma máquina → mesma fingerprint entre execuções.
* **Anti-pirataria casual**: combina MAC + hostname + cpuid + plataforma.
  Não é à prova de virtualização ou clone profissional — é gate
  contra compartilhamento entre amigos/colegas.
* **Sem PII em rede**: o que sai da máquina é apenas SHA256 hex
  (64 chars), não os dados brutos.
* **Cache em QSettings**: evita recomputar a cada inicialização e
  evita falsos negativos em caso de troca de adaptador de rede
  temporária (Wi-Fi vs Ethernet).

Anti-alucinação
===============

* Sem libs externas (sem ``py-machineid``, ``psutil``).
* ``uuid.getnode()`` retorna MAC do primeiro adaptador disponível —
  pode variar entre Wi-Fi e Ethernet. Por isso o cache em QSettings
  congela a primeira leitura.
"""

from __future__ import annotations

import hashlib
import platform
import sys
import uuid
from typing import Optional


_CACHED_MACHINE_ID: Optional[str] = None
_QSETTINGS_KEY = "commercial/machine_id"


def _read_qsettings() -> Optional[str]:
    """Lê machine_id congelado de QSettings, se disponível."""
    try:
        from PySide6.QtCore import QSettings
        settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
        v = settings.value(_QSETTINGS_KEY, None)
        if v:
            return str(v)
    except ImportError:
        pass
    return None


def _write_qsettings(machine_id: str) -> None:
    """Persiste machine_id em QSettings."""
    try:
        from PySide6.QtCore import QSettings
        settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
        settings.setValue(_QSETTINGS_KEY, machine_id)
        settings.sync()
    except ImportError:
        pass


def _gather_hardware_signature() -> str:
    """
    Coleta os componentes da fingerprint em ordem determinística.

    Retorna string crua (antes do hash) com os 4 componentes
    separados por ``|``. Não logar, não enviar em rede.
    """
    try:
        mac = uuid.getnode()
        if (mac >> 40) & 0x1:
            mac_str = "no-mac"
        else:
            mac_str = f"{mac:012x}"
    except Exception:
        mac_str = "no-mac"

    hostname = platform.node() or "no-host"
    processor = platform.processor() or "no-cpu"
    plat = sys.platform or "no-plat"

    return f"{mac_str}|{hostname}|{processor}|{plat}"


def get_machine_id(*, force_refresh: bool = False) -> str:
    """
    Retorna fingerprint SHA256 hex da máquina atual.

    Hierarquia:

    1. Cache em memória (após primeira chamada na sessão).
    2. QSettings (congelado da primeira execução com sucesso).
    3. Recomputa de MAC + hostname + cpuid + plataforma, hashea
       e persiste em QSettings.

    Parameters
    ----------
    force_refresh:
        Se True, ignora cache e recomputa do zero (sobrescreve
        QSettings). Útil para testes e suporte ao cliente.

    Returns
    -------
    str
        SHA256 hex (64 chars).
    """
    global _CACHED_MACHINE_ID

    if not force_refresh and _CACHED_MACHINE_ID is not None:
        return _CACHED_MACHINE_ID

    if not force_refresh:
        cached = _read_qsettings()
        if cached:
            _CACHED_MACHINE_ID = cached
            return cached

    raw = _gather_hardware_signature()
    fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    _write_qsettings(fingerprint)
    _CACHED_MACHINE_ID = fingerprint
    return fingerprint


def masked_machine_id() -> str:
    """Retorna fingerprint mascarada para exibição na GUI."""
    mid = get_machine_id()
    return f"{mid[:8]}...{mid[-8:]}"


def reset_machine_id_cache() -> None:
    """Reset apenas o cache em memória — não toca QSettings."""
    global _CACHED_MACHINE_ID
    _CACHED_MACHINE_ID = None
