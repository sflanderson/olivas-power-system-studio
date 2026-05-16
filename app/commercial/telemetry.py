"""
app.commercial.telemetry — Opt-in anonymous usage stats
(v2.0.0 Sprint D).

Princípios (privacy first)
===========================

* **Default OFF**: usuário precisa explicitamente opt-in via
  `enable_telemetry()`
* **Anônimo**: não armazena user_id, IP, hostname, paths
* **Local-only**: eventos ficam em memória durante a sessão;
  não são enviados em rede em v2.0.0 (v2.1+ adiciona endpoint
  opcional)
* **Reset anytime**: `reset_telemetry()` limpa estado

Eventos rastreados (quando OFF, todos no-op)
==============================================

* `study_run` — qualquer estudo executado
* `dialog_opened` — dialog principal aberto
* `version_started` — Olivas iniciou (sessão)

NUNCA rastreado: nomes de projetos, paths, dados elétricos.

Anti-alucinação
================

* Sem libs externas (analytics, etc) — implementação puramente
  local em v2.0.0
* Sem network IO neste módulo
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


# Estado global
_enabled: bool = False
_events: List[Dict] = []


def enable_telemetry() -> None:
    """Opt-in para coleta de eventos."""
    global _enabled
    _enabled = True


def disable_telemetry() -> None:
    """Opt-out (default)."""
    global _enabled
    _enabled = False


def is_telemetry_enabled() -> bool:
    return _enabled


def reset_telemetry() -> None:
    """Reset estado completo (off + events vazios)."""
    global _enabled
    _enabled = False
    _events.clear()


def record_event(name: str, **metadata) -> None:
    """
    Registra um evento. No-op se telemetry está OFF.

    Parameters
    ----------
    name:
        Nome do evento (snake_case curto).
    metadata:
        Kwargs com dados anônimos (NUNCA PII).

    Anti-PII (anti-alucinação): este módulo NÃO valida que
    `metadata` está livre de PII — caller precisa garantir.
    Recomendação: passar apenas valores categóricos curtos.
    """
    if not _enabled:
        return
    event = {
        "name": name,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        **metadata,
    }
    _events.append(event)


def get_recent_events(limit: int = 100) -> List[Dict]:
    """Retorna eventos recentes (cópia)."""
    return list(_events[-limit:])


def event_count() -> int:
    return len(_events)
