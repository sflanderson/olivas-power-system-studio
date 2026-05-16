"""
app.gui.schematic_pp.pin_categories — Categorização de pinos por
função elétrica (v1.7.3).

Endereça issue do user gate v2.0.1: "pinos foram atribuídos mas
ainda não é possível identificar qual o pino correto".

Princípio (anti-perda)
=======================

Heurística baseada em **name + label** dos pinos do spec YAML —
**não modifica nenhum YAML**. Os 56 component specs continuam
intactos; apenas adicionamos lógica visual baseada nos nomes
canônicos já existentes.

Categorias
==========

* **POWER** (azul): pinos que conduzem corrente nominal/falta
  - CT: P1/P2 (primário)
  - BREAKER/CONTACTOR/FUSE/SWITCH: T1/T2 (linha)
  - MOTOR/TR: T1/T2 (terminais de potência)
  - Default para qualquer "Tn" ou "Pn"

* **SIGNAL** (verde): pinos de medição/comunicação
  - CT: S1/S2 (secundário — saída de medição)
  - RELAY: TC_link (entrada de medição do TC)
  - Sensor outputs em geral

* **TRIP** (laranja): pinos de lógica de proteção
  - BREAKER: Trip_in (recebe sinal de trip)
  - RELAY: Trip_out (envia sinal para disjuntor)
  - Qualquer name ou label contendo "trip"

* **UNKNOWN** (cinza, default): pinos não classificados

Convenção de cores (paridade IEEE/PTW)
========================================

* Power: azul `#1976D2` (consistência com IEEE 802 + PTW
  one-line color)
* Signal: verde `#2E7D32` (medição/instrumentação)
* Trip: laranja `#E65100` (alarme/proteção)
* Unknown: cinza `#505050`

API
===

::

    from app.gui.schematic_pp.pin_categories import (
        pin_category, color_for_category, PinCategory,
    )

    cat = pin_category("S1", "Secundário 1")  # PinCategory.SIGNAL
    color = color_for_category(cat)            # QColor verde
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from PySide6.QtGui import QColor


class PinCategory(str, Enum):
    """Categoria funcional do pino."""

    POWER = "power"      # Corrente nominal/falta
    SIGNAL = "signal"    # Medição/comunicação
    TRIP = "trip"        # Lógica de proteção
    UNKNOWN = "unknown"  # Não classificado


# ---------------------------------------------------------------------------
# Cores (paridade IEEE/PTW one-line conventions)
# ---------------------------------------------------------------------------


_COLOR_POWER = QColor(25, 118, 210)      # Azul (corrente principal)
_COLOR_SIGNAL = QColor(46, 125, 50)      # Verde (medição)
_COLOR_TRIP = QColor(230, 81, 0)         # Laranja (proteção)
_COLOR_UNKNOWN = QColor(80, 80, 80)      # Cinza (default)


def color_for_category(category: PinCategory) -> QColor:
    """QColor para a categoria do pino."""
    return {
        PinCategory.POWER: _COLOR_POWER,
        PinCategory.SIGNAL: _COLOR_SIGNAL,
        PinCategory.TRIP: _COLOR_TRIP,
        PinCategory.UNKNOWN: _COLOR_UNKNOWN,
    }.get(category, _COLOR_UNKNOWN)


# ---------------------------------------------------------------------------
# Heurística de classificação
# ---------------------------------------------------------------------------


# Patterns reconhecidos como TRIP (case-insensitive em name OU label)
_TRIP_PATTERNS = (
    "trip", "ts_", "trip_in", "trip_out", "trip_signal",
)

# Patterns reconhecidos como SIGNAL
_SIGNAL_NAME_PATTERNS = (
    "S1", "S2", "S3", "S4",      # secundário CT
    "TC_link", "tc_link",
    "Aux", "aux",                 # auxiliares
    "Sense", "sense",
    "Comm", "comm",
)
_SIGNAL_LABEL_PATTERNS = (
    "secund", "secondary",
    "medição", "medicao", "measurement",
    "link",
    "auxiliar", "auxiliary",
)

# Patterns reconhecidos como POWER (default para terminais primários)
_POWER_NAME_PATTERNS = (
    "T1", "T2", "T3", "T4",      # terminal lines
    "P1", "P2", "P3", "P4",      # primário CT/transformer
    "L1", "L2", "L3",            # phase lines
    "T_LEFT", "T_RIGHT", "T_CENTER",
    "L", "N",                     # mains
    "A", "B", "C",                # 3-phase
)
_POWER_LABEL_PATTERNS = (
    "linha", "line",
    "primário", "primario", "primary",
    "terminal",
    "fase", "phase",
)


def _matches_any(text: str, patterns) -> bool:
    """Case-insensitive substring match contra lista de patterns."""
    if not text:
        return False
    text_lower = text.lower()
    for p in patterns:
        if p.lower() in text_lower:
            return True
    return False


def pin_category(
    name: str, label: Optional[str] = None,
) -> PinCategory:
    """
    Classifica um pino por categoria baseado em ``name`` (sempre
    presente) e ``label`` opcional.

    Ordem de precedência:
    1. **TRIP**: se name OU label contém "trip"
    2. **SIGNAL**: se name é Sn/TC_link/Aux/etc OR label menciona
       "secundário"/"medição"/etc
    3. **POWER**: se name é Tn/Pn/Ln/etc OR label menciona
       "linha"/"primário"/etc
    4. **UNKNOWN** (fallback)

    Parameters
    ----------
    name:
        Nome canônico do pino (ex: "P1", "Trip_in", "S2").
    label:
        Label humano-legível (ex: "Primário lado 1"). Opcional.

    Returns
    -------
    :class:`PinCategory`
    """
    name = (name or "").strip()
    label = (label or "").strip()

    # 1. TRIP tem maior prioridade (contém é checado em ambos)
    if _matches_any(name, _TRIP_PATTERNS):
        return PinCategory.TRIP
    if _matches_any(label, ("trip",)):
        return PinCategory.TRIP

    # 2. SIGNAL — checa nome canônico primeiro
    for pattern in _SIGNAL_NAME_PATTERNS:
        # Match exato OU prefixo do name (ex: "S1", "S12")
        if name == pattern or (
            len(pattern) <= 3 and name.startswith(pattern)
            and (len(name) == len(pattern) or name[len(pattern)].isdigit())
        ):
            return PinCategory.SIGNAL
    if _matches_any(label, _SIGNAL_LABEL_PATTERNS):
        return PinCategory.SIGNAL

    # 3. POWER — checa nome canônico
    for pattern in _POWER_NAME_PATTERNS:
        if name == pattern or (
            len(pattern) <= 3 and name.startswith(pattern)
            and (len(name) == len(pattern) or name[len(pattern)].isdigit())
        ):
            return PinCategory.POWER
    if _matches_any(label, _POWER_LABEL_PATTERNS):
        return PinCategory.POWER

    # 4. Fallback
    return PinCategory.UNKNOWN


def category_label_pt(category: PinCategory) -> str:
    """Label humano-legível da categoria (PT)."""
    return {
        PinCategory.POWER: "Potência",
        PinCategory.SIGNAL: "Sinal",
        PinCategory.TRIP: "Trip",
        PinCategory.UNKNOWN: "—",
    }.get(category, "—")
