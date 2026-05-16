"""
app.preprocessor.ptw_symbols — Símbolos elétricos
profissionais estilo PTW Power*Tools / ETAP / EasyPower
(v1.1.0).

Filosofia
==========

Os símbolos atuais em ``symbols.py`` seguem convenção
QUCS / IEEE 315 — adequados para EMTP/ATP mas com "cara de
simulação acadêmica". PTW Power*Tools, ETAP e EasyPower
usam símbolos SLD (Single-Line Diagram) tradicionais
da engenharia elétrica de potência:

* **Disjuntor** — quadrado com cruz interna (estilo PTW
  Component Editor)
* **Fusível** — retângulo curto com mark (NEMA / IEC
  60617-7-3)
* **Contator** — diamante com bobina (símbolo IEC 60617)
* **TC** — círculo duplo concêntrico (símbolo IEC 60617-9)
* **Motor** — círculo com "M" (versão refinada com IEC code)
* **Transformador** — duplo círculo overlapping (não barras
  zigzag — convenção PTW SLD)

Estes symbols são instanciados via ``get_renderer(code)``
no módulo ``symbols.py`` quando o código corresponder.

Cobertura normativa
====================

* IEC 60617 — Graphical symbols for diagrams
* IEEE Std 315-1975 — Graphic symbols for electrical
  diagrams (referência)
* ANSI/IEEE C37.2 — Standard device function numbers
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF,
)

from app.preprocessor.symbols import SymbolRenderer


# ---------------------------------------------------------------------------
# Estilo PTW
# ---------------------------------------------------------------------------


_PTW_LINE = QColor(20, 50, 80)         # azul escuro corporativo
_PTW_FILL = QColor(245, 248, 252)      # azul muito claro
_PTW_ACCENT = QColor(0, 102, 153)      # azul PTW
_PTW_RED = QColor(192, 57, 43)         # vermelho de aviso
_PTW_GOLD = QColor(218, 165, 32)       # ouro fusível
_PTW_GREEN = QColor(46, 125, 50)       # verde ok

_PEN_PTW_THIN = QPen(_PTW_LINE, 1.5, Qt.SolidLine,
                      Qt.RoundCap, Qt.RoundJoin)
_PEN_PTW_NORMAL = QPen(_PTW_LINE, 2.0, Qt.SolidLine,
                        Qt.RoundCap, Qt.RoundJoin)
_PEN_PTW_THICK = QPen(_PTW_LINE, 2.5, Qt.SolidLine,
                       Qt.RoundCap, Qt.RoundJoin)
_PEN_PTW_ACCENT = QPen(_PTW_ACCENT, 2.0, Qt.SolidLine,
                        Qt.RoundCap, Qt.RoundJoin)
_BRUSH_PTW_FILL = QBrush(_PTW_FILL)
_BRUSH_PTW_HOLLOW = QBrush(Qt.NoBrush)


# ---------------------------------------------------------------------------
# Disjuntor (estilo PTW: quadrado com cruz)
# ---------------------------------------------------------------------------


class CircuitBreakerSymbol(SymbolRenderer):
    """
    Disjuntor SLD estilo PTW: quadrado 30×30 com cruz
    diagonal interna. **3 pinos** alinhados com BREAKER.ocomp:

    * T1 (-30, 0) — linha de entrada (lado esquerdo)
    * T2 (30, 0) — linha de saída (lado direito)
    * Trip_in (0, -25) — sinal de trip do relé (topo)

    Convenção IEC 60617-7-3 (variante para SLD).

    v1.7.4 (issue user gate v2.0.2): adicionado Trip_in pin para
    receber sinal do RELAY.Trip_out. Antes só tinha 2 pinos
    verticais — inconsistente com BREAKER.ocomp que sempre teve 3.
    """

    PINS = ((-30, 0), (30, 0), (0, -25))
    SIZE = 60
    LABEL = "Disjuntor"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_PTW_THIN)
        # Leads horizontais (T1 esq, T2 dir) — corrente principal
        painter.drawLine(-30, 0, -15, 0)
        painter.drawLine(15, 0, 30, 0)
        # Lead vertical Trip_in (topo) — sinal de trip do relé
        painter.drawLine(0, -25, 0, -15)
        # Quadrado central
        painter.setPen(_PEN_PTW_THICK)
        painter.setBrush(_BRUSH_PTW_FILL)
        painter.drawRect(-15, -15, 30, 30)
        # Cruz diagonal (IEC 60617)
        painter.setPen(_PEN_PTW_NORMAL)
        painter.drawLine(-12, -12, 12, 12)
        painter.drawLine(-12, 12, 12, -12)


# ---------------------------------------------------------------------------
# Fusível (estilo NEMA / IEC 60617-7-3)
# ---------------------------------------------------------------------------


class FuseSymbol(SymbolRenderer):
    """
    Fusível SLD: retângulo arredondado com pequena
    barra horizontal central. Versão IEC 60617-7-3.

    PINS verticais; cor laranja característica.
    """

    PINS = ((0, -30), (0, 30))
    SIZE = 60
    LABEL = "Fusível"

    def paint(self, painter: QPainter) -> None:
        # Leads finos
        painter.setPen(_PEN_PTW_THIN)
        painter.drawLine(0, -30, 0, -18)
        painter.drawLine(0, 18, 0, 30)
        # Retângulo arredondado (mais alto que largo)
        gold_pen = QPen(_PTW_GOLD, 2.0, Qt.SolidLine,
                         Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(gold_pen)
        painter.setBrush(QBrush(QColor(255, 248, 220)))
        painter.drawRoundedRect(QRectF(-7, -18, 14, 36), 3, 3)
        # Linha central (filamento)
        painter.setPen(QPen(_PTW_GOLD, 1.0))
        painter.drawLine(0, -15, 0, 15)


# ---------------------------------------------------------------------------
# Contator (diamante com bobina)
# ---------------------------------------------------------------------------


class ContactorSymbol(SymbolRenderer):
    """
    Contator SLD: contato curvo (NA) com bobina à direita.
    Estilo PTW — diferente de SwIdeal (chave de simulação).
    """

    PINS = ((0, -30), (0, 30), (30, -25), (30, -5))
    SIZE = 80
    LABEL = "Contator"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_PTW_THIN)
        # Lead superior
        painter.drawLine(0, -30, 0, -10)
        # Lead inferior (com pequeno offset para mostrar gap)
        painter.drawLine(0, 30, 0, 12)
        # Contato curvo (arco) — característica do contator
        painter.setPen(_PEN_PTW_THICK)
        path = QPainterPath()
        path.moveTo(0, -10)
        path.cubicTo(-10, -5, -10, 5, 0, 10)
        painter.drawPath(path)
        # Bobina à direita: retângulo pequeno + linhas
        painter.setPen(_PEN_PTW_THIN)
        painter.setBrush(_BRUSH_PTW_HOLLOW)
        painter.drawRect(20, -20, 14, 30)
        # Linha tracejada conectando contato ao centro da bobina
        dash_pen = QPen(_PTW_LINE, 0.8, Qt.DashLine)
        painter.setPen(dash_pen)
        painter.drawLine(0, 0, 20, -5)
        # Pequena letra K (contator)
        painter.setPen(_PEN_PTW_THIN)
        font = QFont("Arial", 7)
        painter.setFont(font)
        painter.drawText(QRectF(20, -19, 14, 28),
                          Qt.AlignCenter, "K")


# ---------------------------------------------------------------------------
# TC (Transformador de Corrente) — círculo duplo
# ---------------------------------------------------------------------------


class CTSymbol(SymbolRenderer):
    """
    TC SLD: dois círculos concêntricos (primário + janela
    secundária) com 4 pinos: 2 primários (esquerda/direita)
    e 2 secundários (embaixo).

    Convenção IEC 60617-9.
    """

    PINS = ((-30, 0), (30, 0), (0, 25), (15, 25))
    SIZE = 80
    LABEL = "TC"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_PTW_THIN)
        # Leads horizontais (primário)
        painter.drawLine(-30, 0, -16, 0)
        painter.drawLine(16, 0, 30, 0)
        # Círculo principal
        painter.setPen(_PEN_PTW_NORMAL)
        painter.setBrush(_BRUSH_PTW_FILL)
        painter.drawEllipse(QRectF(-15, -15, 30, 30))
        # Círculo secundário (mais pequeno, no centro)
        painter.setPen(_PEN_PTW_THIN)
        painter.drawEllipse(QRectF(-7, -7, 14, 14))
        # Leads secundários (vertical para baixo)
        painter.setPen(_PEN_PTW_THIN)
        painter.drawLine(0, 8, 0, 25)
        painter.drawLine(15, 8, 15, 25)
        # Letra "TC" no centro
        painter.setPen(_PEN_PTW_NORMAL)
        font = QFont("Arial", 6)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(-7, -7, 14, 14),
                          Qt.AlignCenter, "TC")


# ---------------------------------------------------------------------------
# Cabo (símbolo PTW: linha horizontal grossa com label)
# ---------------------------------------------------------------------------


class CableSymbol(SymbolRenderer):
    """
    Cabo SLD: linha horizontal com 2 nós no fim, contornado
    por brackets para indicar comprimento. Diferente de
    BERG/JMARTI/TLIN (linhas distribuídas).
    """

    PINS = ((-30, 0), (30, 0))
    SIZE = 60
    LABEL = "Cabo"

    def paint(self, painter: QPainter) -> None:
        # Leads
        painter.setPen(_PEN_PTW_THIN)
        painter.drawLine(-30, 0, -22, 0)
        painter.drawLine(22, 0, 30, 0)
        # Linha grossa central representando o cabo
        painter.setPen(QPen(_PTW_ACCENT, 4.0, Qt.SolidLine,
                              Qt.RoundCap))
        painter.drawLine(-22, 0, 22, 0)
        # Brackets nos extremos (sinal de extensão)
        painter.setPen(_PEN_PTW_THIN)
        painter.drawLine(-22, -5, -22, 5)
        painter.drawLine(22, -5, 22, 5)


# ---------------------------------------------------------------------------
# Motor (versão refinada estilo PTW)
# ---------------------------------------------------------------------------


class PTWMotorSymbol(SymbolRenderer):
    """
    Motor SLD: círculo duplo com letra "M" centralizada,
    com 3 pinos trifásicos no topo. Estilo PTW (mais
    profissional que o atual M com 4 setas).
    """

    PINS = ((-15, -30), (0, -30), (15, -30))
    SIZE = 70
    LABEL = "Motor PTW"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_PTW_THIN)
        # 3 leads top
        for x in (-15, 0, 15):
            painter.drawLine(x, -30, x, -22)
        # Círculo externo
        painter.setPen(_PEN_PTW_THICK)
        painter.setBrush(_BRUSH_PTW_FILL)
        painter.drawEllipse(QRectF(-22, -22, 44, 44))
        # Círculo interno
        painter.setPen(_PEN_PTW_THIN)
        painter.drawEllipse(QRectF(-18, -18, 36, 36))
        # Letra M
        painter.setPen(QPen(_PTW_ACCENT, 2))
        font = QFont("Arial Black", 16)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(-22, -22, 44, 44),
                          Qt.AlignCenter, "M")


# ---------------------------------------------------------------------------
# Registry de overrides PTW
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# v1.4.2 — RelaySymbol: relé de proteção PTW-style
# ---------------------------------------------------------------------------


class RelaySymbol(SymbolRenderer):
    """
    Relé de proteção (50/51/49/87) estilo PTW.

    **2 pinos** alinhados com RELAY.ocomp v1.7.4:

    * TC_link (0, -25) — entrada de medição (vem do TC secundário)
    * Trip_out (0, 25) — saída de trip (vai para BREAKER.Trip_in)

    v1.7.4 (issue user gate v2.0.2): **removidos pinos laterais
    T1/T2** — relé NÃO conecta à barra. Antes T1/T2 laterais
    sugeriam conexão de potência, errado: relé de proteção
    real (IED) só tem entrada de medição (TC) e saída de
    trip (contato seco para BREAKER).

    Distinto de RelaisSymbol (chave horizontal com alavanca)
    — RELAY é função de PROTEÇÃO, não de chaveamento.

    Convenção IEEE C37.2 (device function numbers).
    """

    PINS = ((0, -25), (0, 25))
    SIZE = 60
    LABEL = "Relé de proteção"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_PTW_THIN)
        # Lead superior (link ao TC) — entrada de medição
        painter.drawLine(0, -25, 0, -16)
        # Lead inferior (Trip out) — saída para disjuntor
        painter.drawLine(0, 16, 0, 25)
        # Círculo principal (corpo do relé)
        painter.setPen(_PEN_PTW_THICK)
        painter.setBrush(_BRUSH_PTW_FILL)
        painter.drawEllipse(QRectF(-16, -16, 32, 32))
        # Letra "R" central
        painter.setPen(QPen(_PTW_ACCENT, 1.5))
        font_R = QFont("Arial Black", 12)
        font_R.setBold(True)
        painter.setFont(font_R)
        painter.drawText(QRectF(-16, -16, 32, 32),
                         Qt.AlignCenter, "R")
        # Indicador ANSI superior (texto pequeno)
        painter.setPen(QPen(_PTW_LINE, 1.0))
        font_ansi = QFont("Arial", 6)
        font_ansi.setBold(True)
        painter.setFont(font_ansi)
        painter.drawText(QRectF(-15, -23, 30, 8),
                         Qt.AlignCenter, "51")


# ---------------------------------------------------------------------------
# Utility (concessionária) — v3.1.1 Sprint 2
# Símbolo PTW-style: trapézio com hash (∿∿∿) interna representando
# fonte de potência infinita. IEC 60617 estilo "tower of power".
# ---------------------------------------------------------------------------


class UtilitySymbol(SymbolRenderer):
    """Utility source PTW-style: trapezoid + hash + 'UTIL' label.

    Pin único T1 em (0, 25). Bounding box (-25, -25, 50, 50).
    """

    def paint(self, painter, comp, item):  # type: ignore[override]
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(_PEN_PTW_THICK)
        painter.setBrush(_BRUSH_PTW_FILL)

        # Trapezoid (top wider than bottom — tower silhouette)
        path = QPainterPath()
        path.moveTo(-20, -20)  # top-left
        path.lineTo(20, -20)   # top-right
        path.lineTo(15, 10)    # bottom-right
        path.lineTo(-15, 10)   # bottom-left
        path.closeSubpath()
        painter.drawPath(path)

        # Hash inside trapezoid (3 horizontal lines)
        painter.setPen(QPen(_PTW_ACCENT, 1.5))
        for i, y in enumerate((-12, -4, 4)):
            painter.drawLine(-13 + i, y, 13 - i, y)

        # Lead from bottom of trapezoid to pin T1 (0, 25)
        painter.setPen(_PEN_PTW_NORMAL)
        painter.drawLine(0, 10, 0, 25)

        # Label "UTIL" at top
        painter.setPen(QPen(_PTW_LINE, 1.0))
        font = QFont("Arial", 7)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(-25, -28, 50, 8),
                          Qt.AlignCenter, "UTIL")


# ---------------------------------------------------------------------------
# Load — v3.1.1 Sprint 2
# Símbolo PTW: seta para baixo (carga consumindo) + label kW/kVAR
# ---------------------------------------------------------------------------


class LoadSymbol(SymbolRenderer):
    """Load PTW-style: down-arrow with kW label.

    Pin único T1 em (0, -25). Bounding box (-20, -25, 40, 50).
    """

    def paint(self, painter, comp, item):  # type: ignore[override]
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(_PEN_PTW_NORMAL)
        painter.setBrush(_BRUSH_PTW_HOLLOW)

        # Lead from pin T1 (0, -25) to body top (0, -10)
        painter.drawLine(0, -25, 0, -10)

        # Down-arrow (load consumes power)
        arrow = QPolygonF([
            QPointF(0, 15),    # tip
            QPointF(-12, -10),  # top-left
            QPointF(12, -10),   # top-right
        ])
        painter.setBrush(QBrush(_PTW_FILL))
        painter.drawPolygon(arrow)

        # Inner "L" letter
        painter.setPen(QPen(_PTW_ACCENT, 1.5))
        font = QFont("Arial Black", 9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(-12, -8, 24, 18),
                          Qt.AlignCenter, "L")


# ---------------------------------------------------------------------------
# Filter (harmonic shunt) — v3.1.1 Sprint 2
# Símbolo PTW: capacitor (||) em série com indutor (~~) + label
# IEC 60617 representação shunt filter.
# ---------------------------------------------------------------------------


class FilterSymbol(SymbolRenderer):
    """Harmonic shunt filter PTW-style: L-C series.

    Pin T1 em (0, -30) e T2 em (0, 30). Bounding box (-25, -30, 50, 60).
    """

    def paint(self, painter, comp, item):  # type: ignore[override]
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(_PEN_PTW_NORMAL)
        painter.setBrush(_BRUSH_PTW_HOLLOW)

        # Lead from pin T1 (0, -30) → coil top
        painter.drawLine(0, -30, 0, -20)

        # Inductor coil (3 humps representing winding)
        coil = QPainterPath()
        coil.moveTo(-9, -20)
        for i, x_center in enumerate((-6, 0, 6)):
            coil.arcTo(QRectF(x_center - 4.5, -22, 9, 9),
                        180, -180)
        painter.drawPath(coil)

        # Lead between coil and capacitor
        painter.drawLine(0, -11, 0, -2)

        # Capacitor plates (|| horizontal)
        painter.setPen(_PEN_PTW_THICK)
        painter.drawLine(-12, -2, 12, -2)
        painter.drawLine(-12, 4, 12, 4)

        # Lead from cap to pin T2 (0, 30)
        painter.setPen(_PEN_PTW_NORMAL)
        painter.drawLine(0, 4, 0, 30)

        # Label "FLT" near top
        painter.setPen(QPen(_PTW_LINE, 1.0))
        font = QFont("Arial", 7)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(13, -8, 25, 10),
                          Qt.AlignLeft, "FLT")


def get_ptw_renderer(code: str) -> SymbolRenderer | None:
    """
    Retorna renderer PTW-style para ``code`` ou None se
    não houver override (caller deve fallback para o
    default em ``symbols.py``).

    Esta função é consultada por ``symbols.get_renderer()``
    ANTES do registry default — assim, novos componentes
    da v1.0.1+ (CABLE, CT, FUSE, CONTACTOR) e v1.4.2 (RELAY)
    renderizam corretamente com símbolos profissionais.
    """
    mapping = {
        "CABLE": CableSymbol,
        "CT": CTSymbol,
        "FUSE": FuseSymbol,
        "CONTACTOR": ContactorSymbol,
        # v1.4.2: RELAY (proteção 50/51/49/87) com símbolo PTW-style
        # — círculo + letra "R" + ANSI device number. Distinto do
        # legacy "Relais" (chave) que mantém visual de chave.
        "RELAY": RelaySymbol,
        # v1.4.3: BREAKER (disjuntor controlado por relé) usa
        # símbolo PTW de disjuntor (quadrado + cruz IEC 60617-7-3).
        "BREAKER": CircuitBreakerSymbol,
        # v3.1.1 Sprint 2 — paridade Tutorial PTW §Part 1 p.21-28
        "UTIL": UtilitySymbol,
        "LOAD": LoadSymbol,
        "FILTER": FilterSymbol,
        # Overrides opcionais (não força — apenas disponibiliza
        # estilo PTW se chamador escolher):
        # "MOTOR": PTWMotorSymbol,  ← deixar comentado por
        # ora; usuário pode preferir o motor IEEE atual.
    }
    cls = mapping.get(code)
    if cls is None:
        return None
    return cls()
