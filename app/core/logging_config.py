"""
app.core.logging_config — configuração central de logging do
**Olivas Power System Studio** (v0.92.2).

Filosofia
==========

Cálculos de engenharia (curto-circuito, arc-flash, fluxo de
potência, coordenação) **devem ser auditáveis** — toda decisão
crítica precisa deixar rastro: fallbacks aplicados, parâmetros
clamp, divergência de Newton-Raphson, limitações detectadas em
runtime.

Antes de v0.92.2: a maioria dos módulos usava ``print()`` ou
silenciava erros. Em laudo profissional, isso é inaceitável
(ISO 9001 §8.5.1 / NR-10 §10.2.4 / ABNT NBR 17227 §5.4.4
exigem rastreabilidade técnica).

API
====

* :func:`get_logger(name)` — retorna logger nomeado pronto
  para uso. Substituto canônico de ``import logging``.
* :func:`configure_logging(...)` — configura handlers (stdout
  + arquivo opcional) e níveis. Idempotente.
* :func:`log_engineering_event(...)` — helper estruturado para
  eventos críticos de cálculo (gera linha JSON-like que pode
  ser parseada para audit log).

Convenções de uso
==================

* **DEBUG**: passos do cálculo (ex. impedâncias intermediárias).
* **INFO**: eventos normais (ex. "Newton-Raphson convergiu em 5 iters").
* **WARNING**: fallbacks aplicados, limitações tocadas, parâmetros
  fora de range mas tolerados (ex. "tensão 7.2 kV fora da
  faixa NBR 17227 ≤15kV; aproximação aplicada").
* **ERROR**: cálculo falhou, retorno inválido.
* **CRITICAL**: dados inconsistentes (ex. R<0); recusar análise.

Exemplo
========

::

    from app.core.logging_config import get_logger
    log = get_logger(__name__)

    if Z_thevenin <= 0:
        log.warning(
            "Z_thevenin=%.4f <= 0 em bus=%s; aplicando fallback inf",
            Z_thevenin, bus_id,
        )
        return float("inf")
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


_DEFAULT_FORMAT = (
    "%(asctime)s [%(levelname)-7s] %(name)-32s | %(message)s"
)
_DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Flag para evitar reconfiguração múltipla (idempotência)
_CONFIGURED = False


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger nomeado. Configuração default é aplicada
    automaticamente na primeira chamada.

    Parameters
    ----------
    name:
        Nome do módulo (use ``__name__``).

    Returns
    -------
    logging.Logger
    """
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    fmt: str = _DEFAULT_FORMAT,
    date_fmt: str = _DEFAULT_DATE_FORMAT,
) -> None:
    """
    Configura o logging global do app — idempotente.

    Adiciona um StreamHandler para stderr e (opcionalmente) um
    FileHandler. Pode ser chamada múltiplas vezes — só aplica
    a primeira.

    Parameters
    ----------
    level:
        Nível mínimo (logging.DEBUG/INFO/WARNING/ERROR).
        Default INFO (DEBUG fica disponível mas não emitido).
    log_file:
        Caminho opcional para arquivo persistente. Útil para
        guardar audit trail entre execuções.
    fmt, date_fmt:
        Format strings (ver ``logging.Formatter``).
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger("app")   # namespace do app
    root.setLevel(level)
    root.propagate = False

    formatter = logging.Formatter(fmt, datefmt=date_fmt)

    # Console handler (stderr para não poluir stdout em testes)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # File handler opcional
    if log_file is not None:
        try:
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_h = logging.FileHandler(
                log_file, encoding="utf-8",
            )
            file_h.setLevel(level)
            file_h.setFormatter(formatter)
            root.addHandler(file_h)
        except OSError as exc:
            # Não derrubar o app por causa de log file
            root.warning(
                "Não foi possível abrir log_file=%s: %s",
                log_file, exc,
            )

    _CONFIGURED = True


def log_engineering_event(
    logger: logging.Logger,
    *,
    event: str,
    norm: str,
    bus: Optional[str] = None,
    fallback: Optional[str] = None,
    level: int = logging.WARNING,
    **kwargs,
) -> None:
    """
    Helper para emitir um evento estruturado de cálculo.

    Formato:

    ::

        EVT=<event> NORM=<norm> BUS=<bus> FALLBACK=<fallback>
        ...kwargs...

    Pode ser parseado por scripts pós-execução para gerar
    audit reports adicionais.

    Parameters
    ----------
    logger:
        Logger do módulo chamador.
    event:
        Identificador curto do evento (ex.: "z_thevenin_zero",
        "newton_raphson_diverged", "voltage_outside_nbr_range").
    norm:
        Norma referenciada (ex.: "IEC 60909-0 §4.3.1").
    bus:
        Barramento envolvido (opcional).
    fallback:
        Descrição da ação corretiva aplicada.
    level:
        Severidade (default WARNING).
    **kwargs:
        Pares chave=valor adicionais.
    """
    parts = [f"EVT={event}", f"NORM={norm}"]
    if bus is not None:
        parts.append(f"BUS={bus}")
    if fallback is not None:
        parts.append(f"FALLBACK={fallback}")
    for k, v in kwargs.items():
        parts.append(f"{k.upper()}={v}")
    logger.log(level, " ".join(parts))


def reset_for_tests() -> None:
    """
    Reseta o estado de configuração — usado por fixtures de teste
    que precisam reconfigurar o logging entre runs.
    """
    global _CONFIGURED
    _CONFIGURED = False
    root = logging.getLogger("app")
    for h in list(root.handlers):
        root.removeHandler(h)
