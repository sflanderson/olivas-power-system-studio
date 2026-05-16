"""
app.preprocessor.symbols — biblioteca visual dos símbolos do
pré-processador.

Cada `SymbolRenderer` sabe:

* seu *bounding rect* em coordenadas locais (anchor em 0,0);
* como se *desenhar* num `QPainter` já configurado;
* suas *posições de pino* em coordenadas locais (consistentes
  com `node_coalescer._PIN_GEOMETRY`).

O editor visual (sprint v0.21.3) delega para estes renderers
via o `registry` no fim do arquivo. Os símbolos seguem o padrão
**IEEE 315** (EUA / ATPDraw) — zigzag para R, espiral para L,
placas paralelas para C.

Projeto intencionalmente minimalista: traços finos, sem
sombreamento nem preenchimentos decorativos. O objetivo da v1
é *funcional e reconhecível*, não arte.

Convenções
----------

* Âncora em (0, 0); pinos ficam nas direções cardinais.
* Todas as coordenadas em pixels; compatíveis com o grid
  Qucs de 10px.
* Componentes 2-terminais verticais têm pinos em (0,-30) e
  (0,30) por default (caminho mais comum no Qucs).
* Diodos/IGBTs/MOSFETs são horizontais por default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF


# ---------------------------------------------------------------------------
# Estilo compartilhado
# ---------------------------------------------------------------------------


_LINE_COLOR = QColor(30, 30, 30)
_FILL_COLOR = QColor(255, 255, 255)
_TEXT_COLOR = QColor(0, 0, 0)

# Hierarquia visual em 2 níveis (v0.21.8.d):
# - ``_PEN_LEAD``  (1.3 px) — fios externos (terminais); secundários na
#   leitura visual, subordinados ao corpo do símbolo.
# - ``_PEN_NORMAL`` (1.5 px) — corpo do símbolo em si (zigzag do resistor,
#   arcos do indutor, placas do capacitor, círculo da fonte, etc.). O
#   ``paint()`` de cada subclasse pode trocar entre os dois para dar
#   destaque.
# - ``_PEN_THICK`` (2.0 px) — reservado para contornos de destaque ou
#   componentes que precisam de presença visual extra.
#
# RoundCap + RoundJoin garantem que junções não "serrem" e cantos
# zigzag ficam suavemente arredondados em vez de pontiagudos.
_PEN_LEAD = QPen(_LINE_COLOR, 1.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
_PEN_NORMAL = QPen(_LINE_COLOR, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
_PEN_THICK = QPen(_LINE_COLOR, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
_BRUSH_FILL = QBrush(_FILL_COLOR)
_BRUSH_HOLLOW = QBrush(Qt.NoBrush)


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class SymbolRenderer:
    """Interface comum a todos os símbolos."""

    #: pinos em (dx, dy) relativos ao anchor, rotation 0.
    PINS: tuple[tuple[int, int], ...] = ((0, -30), (0, 30))

    #: raio do bounding rect (quadrado). Sobrescrito se não for simétrico.
    SIZE: int = 60

    #: rótulo humano (para tooltips na paleta). Default derivado do __name__.
    LABEL: str = ""

    def bounding_rect(self) -> QRectF:
        """Rect local, centralizado na âncora."""
        h = self.SIZE / 2
        return QRectF(-h, -h, self.SIZE, self.SIZE)

    def pin_positions(self) -> list[tuple[int, int]]:
        """Pinos em coordenadas locais (rotation 0, mirror 0)."""
        return list(self.PINS)

    def paint(self, painter: QPainter) -> None:  # pragma: no cover - interface
        """Desenha o símbolo na pose neutra (rotation 0, anchor em 0,0)."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Utilitário de desenho
# ---------------------------------------------------------------------------


def _draw_pin_dot(painter: QPainter, x: int, y: int, r: float = 1.5) -> None:
    """Bolinha pequena no pino — ajuda debug visual."""
    painter.save()
    painter.setPen(QPen(_LINE_COLOR, 1.0))
    painter.setBrush(_BRUSH_FILL)
    painter.drawEllipse(QPointF(x, y), r, r)
    painter.restore()


# ---------------------------------------------------------------------------
# Passivos
# ---------------------------------------------------------------------------


class ResistorSymbol(SymbolRenderer):
    """IEEE 315 zigzag (3 peaks) vertical.

    Proporções após v0.21.8.d:
    - Leads: y=[-30, -14] e y=[14, 30] (16 px cada).
    - Corpo zigzag: y=[-14, 14] (28 px), 3 picos, amplitude ±5 px.
    - A amplitude mais enxuta (antes 6 px) evita que o zigzag "encoste"
      nos bounding rects laterais e dá a leitura mais canônica de
      "resistor" em diagramas publicados.
    """

    PINS = ((0, -30), (0, 30))
    SIZE = 60
    LABEL = "Resistor"

    def paint(self, painter: QPainter) -> None:
        # leads — pen mais fina (hierarquia visual).
        painter.setPen(_PEN_LEAD)
        painter.drawLine(0, -30, 0, -14)
        painter.drawLine(0, 14, 0, 30)
        # corpo zigzag — pen normal.
        painter.setPen(_PEN_NORMAL)
        path = QPainterPath()
        path.moveTo(0, -14)
        # 3 picos simétricos em y ∈ {-10, -2, 6, 10} com amplitude ±5.
        # Padrão IEEE 315: 6 segmentos alternados em lados opostos.
        peaks = [
            (5, -10), (-5, -6), (5, -2), (-5, 2), (5, 6), (-5, 10),
        ]
        for x, y in peaks:
            path.lineTo(x, y)
        path.lineTo(0, 14)
        painter.drawPath(path)


class InductorSymbol(SymbolRenderer):
    """Quatro semicírculos ("bumps") empilhados, convenção IEEE.

    v0.21.8.d: migrou de 3 para 4 arcos — a aparência passa a lembrar
    uma bobina enrolada de verdade, em vez de 3 "arcos soltos". Cada
    arco tem 9 px de diâmetro (antes 12 px), mantendo o corpo total em
    36 px (-18 a +18) — mesmo espaço, mais densidade de espiras.
    """

    PINS = ((0, -30), (0, 30))
    SIZE = 60
    LABEL = "Indutor"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_LEAD)
        painter.drawLine(0, -30, 0, -18)
        painter.drawLine(0, 18, 0, 30)
        painter.setPen(_PEN_NORMAL)
        # 4 arcos de 9 px de diâmetro, empilhados de -18 a +18.
        # Cada arco desenha semicírculo superior (abre para a direita).
        for y in (-18, -9, 0, 9):
            painter.drawArc(QRectF(-4.5, y, 9, 9), 90 * 16, -180 * 16)


class CapacitorSymbol(SymbolRenderer):
    """Duas placas paralelas horizontais — capacitor não-polarizado.

    v0.21.8.d: placas mais largas (±14 vs ±12) e gap interno menor
    (±3 vs ±4) com pen mais grossa — a "silhueta" do capacitor fica
    mais reconhecível mesmo em zoom baixo.
    """

    PINS = ((0, -30), (0, 30))
    SIZE = 60
    LABEL = "Capacitor"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_LEAD)
        painter.drawLine(0, -30, 0, -3)
        painter.drawLine(0, 3, 0, 30)
        # placas — pen grossa (_PEN_THICK) para destacar como "massa
        # metálica" entre dielétricos, convenção em ATPDraw / PSCAD.
        painter.setPen(_PEN_THICK)
        painter.drawLine(-14, -3, 14, -3)
        painter.drawLine(-14, 3, 14, 3)


class GroundSymbol(SymbolRenderer):
    """Terra IEEE 315 — 3 linhas horizontais decrescentes.

    v0.21.8.d: primeira barra em pen THICK (marca "o" terra principal),
    segunda/terceira em pen normal (convenção IEEE-canônica). Lead
    vertical em pen LEAD. Proporções 12/8/4 (antes 10/7/4) — mais
    harmônicas (2:1 entre cada nível).
    """

    PINS = ((0, 0),)
    SIZE = 24
    LABEL = "Terra"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_LEAD)
        painter.drawLine(0, 0, 0, 6)
        # Barra principal — espessa, largura 12.
        painter.setPen(_PEN_THICK)
        painter.drawLine(-12, 6, 12, 6)
        # Barras secundárias — pen normal, larguras 8 e 4 (razão 2:1).
        painter.setPen(_PEN_NORMAL)
        painter.drawLine(-8, 10, 8, 10)
        painter.drawLine(-4, 14, 4, 14)


# ---------------------------------------------------------------------------
# Fontes
# ---------------------------------------------------------------------------


def _draw_source_circle(painter: QPainter, r: int = 12) -> None:
    """Desenha o círculo-fonte em pen NORMAL, fill branco."""
    painter.setPen(_PEN_NORMAL)
    painter.setBrush(_BRUSH_FILL)
    painter.drawEllipse(QPointF(0, 0), r, r)


class VdcSymbol(SymbolRenderer):
    """Fonte DC — círculo com "+" em cima e "−" embaixo.

    v0.21.8.d: marcadores ``+``/``−`` em pen THICK (mais visíveis),
    braços de 4 px (antes 3) para melhor reconhecimento em zoom baixo.
    """

    PINS = ((0, -30), (0, 30))
    SIZE = 60
    LABEL = "Fonte DC de tensão"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_LEAD)
        painter.drawLine(0, -30, 0, -12)
        painter.drawLine(0, 12, 0, 30)
        _draw_source_circle(painter)
        # Marcadores "+" e "−" em pen THICK — leitura rápida da
        # polaridade (convenção IEEE, mesma em ATPDraw).
        painter.setPen(_PEN_THICK)
        # + em cima
        painter.drawLine(-4, -6, 4, -6)
        painter.drawLine(0, -10, 0, -2)
        # − embaixo
        painter.drawLine(-4, 6, 4, 6)


class VacSymbol(SymbolRenderer):
    """Fonte AC — círculo com senoide interna.

    v0.21.8.d: senoide refeita como dois arcos via QPainterPath —
    amplitude ±5, largura total ±8 (antes ~8 e ~6). Mais fiel a uma
    senoide real e simétrica em relação à vertical.
    """

    PINS = ((0, -30), (0, 30))
    SIZE = 60
    LABEL = "Fonte AC de tensão"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_LEAD)
        painter.drawLine(0, -30, 0, -12)
        painter.drawLine(0, 12, 0, 30)
        _draw_source_circle(painter)
        # Senoide — pen normal; usa arcTo para um meio-período superior
        # e um meio-período inferior de amplitude simétrica.
        painter.setPen(_PEN_NORMAL)
        path = QPainterPath()
        path.moveTo(-8, 0)
        # Meio-período de cima (pico em y=-5 em x=-4)
        path.cubicTo(-6, -7, -2, -7, 0, 0)
        # Meio-período de baixo (vale em y=5 em x=4)
        path.cubicTo(2, 7, 6, 7, 8, 0)
        painter.drawPath(path)


class IdcSymbol(VdcSymbol):
    LABEL = "Fonte DC de corrente"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_NORMAL)
        painter.drawLine(0, -30, 0, -12)
        painter.drawLine(0, 12, 0, 30)
        _draw_source_circle(painter)
        # seta ↑ no centro
        painter.drawLine(0, 8, 0, -8)
        painter.drawLine(0, -8, -3, -4)
        painter.drawLine(0, -8, 3, -4)


class IacSymbol(VacSymbol):
    LABEL = "Fonte AC de corrente"


# ---------------------------------------------------------------------------
# Chaves / eletrônica de potência
# ---------------------------------------------------------------------------


class SwitchIdealSymbol(SymbolRenderer):
    """Chave ideal aberta — haste inclinada para cima.

    v0.21.8.d: contatos com raio 2.5 px (antes 2), alavanca em pen
    NORMAL (destaque). A alavanca vai de (-12, 0) a (10, -10) — chave
    visualmente aberta, convenção ATPDraw/IEEE.
    """

    PINS = ((-30, 0), (30, 0))
    SIZE = 60
    LABEL = "Chave ideal"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_LEAD)
        painter.drawLine(-30, 0, -12, 0)
        painter.drawLine(12, 0, 30, 0)
        # Alavanca — pen normal para destaque.
        painter.setPen(_PEN_NORMAL)
        painter.drawLine(-12, 0, 10, -10)
        # Contatos — discos pequenos preenchidos (raio 2.5).
        painter.setPen(_PEN_NORMAL)
        painter.setBrush(QBrush(_LINE_COLOR))
        painter.drawEllipse(QPointF(-12, 0), 2.5, 2.5)
        painter.drawEllipse(QPointF(12, 0), 2.5, 2.5)


class RelaisSymbol(SwitchIdealSymbol):
    """Relé / disjuntor — chave com leads longos (Qucs Relais)."""

    PINS = ((-50, 0), (50, 0))
    SIZE = 100
    LABEL = "Relé controlado"

    def bounding_rect(self) -> QRectF:
        return QRectF(-50, -30, 100, 60)

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_NORMAL)
        # leads longos (±50 em vez de ±30)
        painter.drawLine(-50, 0, -12, 0)
        painter.drawLine(12, 0, 50, 0)
        # alavanca
        painter.drawLine(-12, 0, 10, -10)
        # círculos dos contatos
        painter.setBrush(_BRUSH_FILL)
        painter.drawEllipse(QPointF(-12, 0), 2, 2)
        painter.drawEllipse(QPointF(12, 0), 2, 2)


class VCB3PhaseSymbol(SymbolRenderer):
    """Disjuntor a vácuo trifásico (VCB 3φ).

    Três chaves horizontais empilhadas (uma por fase A/B/C), com leads
    estendidos a ±40 e envoltas por um retângulo tracejado indicando
    a câmara de vácuo. Cada chave tem Topen/Tclose *independentes* —
    a modelagem estatística de reignição é compartilhada pelo pólo
    (mesmos parâmetros Ichop, di/dt, k_dielec).

    Layout dos pinos (12 slots = 6 fios externos):
      0: A_in  (-40, -30)   1: A_out (40, -30)
      2: B_in  (-40,   0)   3: B_out (40,   0)
      4: C_in  (-40,  30)   5: C_out (40,  30)
    """

    PINS = (
        (-40, -30), (40, -30),   # fase A
        (-40,   0), (40,   0),   # fase B
        (-40,  30), (40,  30),   # fase C
    )
    SIZE = 80
    LABEL = "Disjuntor a vácuo 3φ"

    def bounding_rect(self) -> QRectF:
        # -40..+40 horizontal, -40..+40 vertical (para acomodar rótulo "3φ")
        return QRectF(-40, -40, 80, 80)

    def paint(self, painter: QPainter) -> None:
        # v0.21.8.d: hierarquia visual leads/corpo, contatos filled,
        # câmara a vácuo com cantos arredondados (mais moderno).
        # Três chaves horizontais (y = -30, 0, 30) — uma por fase.
        for y in (-30, 0, 30):
            painter.setPen(_PEN_LEAD)
            painter.drawLine(-40, y, -12, y)
            painter.drawLine(12, y, 40, y)
            # Alavanca inclinada (chave aberta).
            painter.setPen(_PEN_NORMAL)
            painter.drawLine(-12, y, 10, y - 10)
            # Contatos preenchidos (raio 2.5).
            painter.setPen(_PEN_NORMAL)
            painter.setBrush(QBrush(_LINE_COLOR))
            painter.drawEllipse(QPointF(-12, y), 2.5, 2.5)
            painter.drawEllipse(QPointF(12, y), 2.5, 2.5)
        # Câmara a vácuo — retângulo com cantos arredondados (r=3)
        # + borda tracejada. Indica que as 3 chaves estão num mesmo
        # invólucro físico.
        vac_pen = QPen(
            _LINE_COLOR, 1.0, Qt.DashLine, Qt.RoundCap, Qt.RoundJoin
        )
        painter.setPen(vac_pen)
        painter.setBrush(_BRUSH_HOLLOW)
        painter.drawRoundedRect(QRectF(-20, -38, 40, 76), 3.0, 3.0)
        # Rótulo "3φ" no canto superior direito.
        painter.setPen(QPen(_TEXT_COLOR, 1.0))
        painter.setFont(QFont("Segoe UI, Sans", 7, QFont.Bold))
        painter.drawText(QPointF(22, -22), "3\u03c6")


class DiodeSymbol(SymbolRenderer):
    """Diodo — triângulo preenchido apontando para a direita + cátodo.

    v0.21.8.d: linha de cátodo em pen THICK (destaca a "barra
    bloqueante") e triângulo com ``antialiasing`` pelo default do
    painter.
    """

    PINS = ((-30, 0), (30, 0))
    SIZE = 60
    LABEL = "Diodo"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_LEAD)
        painter.drawLine(-30, 0, -10, 0)
        painter.drawLine(10, 0, 30, 0)
        # Triângulo do anodo — contorno pen normal + fill da cor da
        # linha (convenção IEEE para diodo sólido).
        painter.setPen(_PEN_NORMAL)
        painter.setBrush(QBrush(_LINE_COLOR))
        tri = QPolygonF([QPointF(-10, -8), QPointF(-10, 8), QPointF(10, 0)])
        painter.drawPolygon(tri)
        # Cátodo — pen THICK enfatiza a barra (assimetria anodo/cátodo
        # é a característica visual definidora do diodo).
        painter.setPen(_PEN_THICK)
        painter.drawLine(10, -8, 10, 8)


class ThyristorSymbol(DiodeSymbol):
    """Diodo + gate (terceiro terminal, cima)."""

    PINS = ((-30, 0), (30, 0), (10, -20))
    LABEL = "Tiristor"

    def paint(self, painter: QPainter) -> None:
        super().paint(painter)
        painter.setPen(_PEN_NORMAL)
        painter.drawLine(10, -20, 10, -8)


class GTOSymbol(ThyristorSymbol):
    """Tiristor + segunda seta no gate (turn-off)."""

    LABEL = "GTO"

    def paint(self, painter: QPainter) -> None:
        super().paint(painter)
        # pequena seta dupla no gate
        painter.setPen(_PEN_NORMAL)
        painter.drawLine(10, -14, 14, -18)
        painter.drawLine(14, -18, 11, -17)
        painter.drawLine(14, -18, 13, -14)


class IGBTSymbol(SymbolRenderer):
    """Gate isolado + coletor/emissor com seta."""

    PINS = ((-30, 0), (30, 0), (0, 20))
    SIZE = 60
    LABEL = "IGBT"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_NORMAL)
        painter.drawLine(-30, 0, -10, 0)
        painter.drawLine(10, 0, 30, 0)
        # "corpo" vertical
        painter.drawLine(-4, -12, -4, 12)
        # coletor / emissor (linhas até os leads)
        painter.drawLine(-4, -6, 10, 0)
        painter.drawLine(-4, 6, 10, 0)
        # seta no emissor (direita, para fora)
        painter.drawLine(6, 2, 10, 0)
        painter.drawLine(10, 0, 6, -2)
        # gate isolado (traço separado antes do corpo)
        painter.drawLine(-10, -6, -10, 6)
        painter.drawLine(0, 20, 0, 0)


class MOSFETSymbol(IGBTSymbol):
    """MOSFET: como IGBT mas sem seta no emissor."""

    LABEL = "MOSFET"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_NORMAL)
        painter.drawLine(-30, 0, -10, 0)
        painter.drawLine(10, 0, 30, 0)
        painter.drawLine(-4, -12, -4, 12)
        painter.drawLine(-4, -6, 10, 0)
        painter.drawLine(-4, 6, 10, 0)
        painter.drawLine(-10, -6, -10, 6)
        painter.drawLine(0, 20, 0, 0)


# ---------------------------------------------------------------------------
# Acoplados
# ---------------------------------------------------------------------------


class TransformerSymbol(SymbolRenderer):
    """Dois indutores em paralelo com "||" de núcleo entre eles."""

    PINS = ((-30, -20), (-30, 20), (30, -20), (30, 20))
    SIZE = 80
    LABEL = "Transformador 2-enrol."

    def bounding_rect(self) -> QRectF:
        return QRectF(-40, -30, 80, 60)

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_NORMAL)
        # primário (esq): 3 bumps
        for y in (-20, -8, 4):
            painter.drawArc(QRectF(-20, y, 12, 12), 90 * 16, -180 * 16)
        # secundário (dir)
        for y in (-20, -8, 4):
            painter.drawArc(QRectF(8, y, 12, 12), 90 * 16, 180 * 16)
        # núcleo central
        painter.drawLine(-3, -22, -3, 22)
        painter.drawLine(3, -22, 3, 22)
        # leads
        painter.drawLine(-30, -20, -14, -20)
        painter.drawLine(-30, 20, -14, 20)
        painter.drawLine(14, -20, 30, -20)
        painter.drawLine(14, 20, 30, 20)


# ---------------------------------------------------------------------------
# Linhas
# ---------------------------------------------------------------------------


class _LineBox(SymbolRenderer):
    """Base para símbolos de linha: retângulo com rótulo."""

    PINS = ((-30, 0), (30, 0))
    SIZE = 60
    _RECT_LABEL = "TLINE"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_NORMAL)
        painter.drawLine(-30, 0, -18, 0)
        painter.drawLine(18, 0, 30, 0)
        painter.setBrush(_BRUSH_FILL)
        painter.drawRect(QRectF(-18, -8, 36, 16))
        painter.setPen(QPen(_TEXT_COLOR, 1.0))
        f = QFont("Sans", 7)
        painter.setFont(f)
        painter.drawText(QRectF(-18, -8, 36, 16), Qt.AlignCenter, self._RECT_LABEL)


class LinePISymbol(_LineBox):
    LABEL = "Linha PI nominal"
    _RECT_LABEL = "PI"


class LineBergeronSymbol(_LineBox):
    LABEL = "Linha Bergeron"
    _RECT_LABEL = "BERG"


class LineJMartiSymbol(_LineBox):
    LABEL = "Linha J. Marti"
    _RECT_LABEL = "Z(ω)"


# ---------------------------------------------------------------------------
# Não-lineares
# ---------------------------------------------------------------------------


class ZnOSymbol(SymbolRenderer):
    """Para-raios ZnO: resistor com seta diagonal sobreposta."""

    PINS = ((0, -30), (0, 30))
    SIZE = 60
    LABEL = "Para-raios ZnO"

    def paint(self, painter: QPainter) -> None:
        # zigzag base (como R)
        ResistorSymbol().paint(painter)
        # seta diagonal
        painter.setPen(_PEN_THICK)
        painter.drawLine(-14, 8, 14, -8)
        painter.drawLine(14, -8, 9, -8)
        painter.drawLine(14, -8, 14, -3)


class NonLinearRSymbol(ResistorSymbol):
    """Resistor com 'N' sobrescrito (R(I))."""

    LABEL = "Resistor não-linear R(I)"

    def paint(self, painter: QPainter) -> None:
        super().paint(painter)
        painter.setPen(QPen(_TEXT_COLOR, 1.0))
        painter.setFont(QFont("Sans", 6, QFont.Bold))
        painter.drawText(QPointF(10, -14), "R(I)")


class NonLinearLSymbol(InductorSymbol):
    """Indutor com 'L(i)' sobrescrito (saturação)."""

    LABEL = "Indutor saturável L(i)"

    def paint(self, painter: QPainter) -> None:
        super().paint(painter)
        painter.setPen(QPen(_TEXT_COLOR, 1.0))
        painter.setFont(QFont("Sans", 6, QFont.Bold))
        painter.drawText(QPointF(10, -14), "L(i)")


# ---------------------------------------------------------------------------
# Medidores
# ---------------------------------------------------------------------------


class VProbeSymbol(SymbolRenderer):
    """Círculo com 'V' — probe de tensão."""

    PINS = ((0, -30), (0, 30))
    SIZE = 60
    LABEL = "Voltímetro"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_NORMAL)
        painter.drawLine(0, -30, 0, -12)
        painter.drawLine(0, 12, 0, 30)
        _draw_source_circle(painter)
        painter.setPen(QPen(_TEXT_COLOR, 1.0))
        painter.setFont(QFont("Sans", 9, QFont.Bold))
        painter.drawText(QRectF(-12, -12, 24, 24), Qt.AlignCenter, "V")


class IProbeSymbol(SymbolRenderer):
    """Círculo com 'A' — probe de corrente."""

    PINS = ((-30, 0), (30, 0))
    SIZE = 60
    LABEL = "Amperímetro"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_NORMAL)
        painter.drawLine(-30, 0, -12, 0)
        painter.drawLine(12, 0, 30, 0)
        _draw_source_circle(painter)
        painter.setPen(QPen(_TEXT_COLOR, 1.0))
        painter.setFont(QFont("Sans", 9, QFont.Bold))
        painter.drawText(QRectF(-12, -12, 24, 24), Qt.AlignCenter, "A")


# ---------------------------------------------------------------------------
# Controle
# ---------------------------------------------------------------------------


class _TextBox(SymbolRenderer):
    """Caixa retangular com rótulo central — para blocos de controle."""

    PINS = ()
    SIZE = 60
    _BOX_TEXT = "???"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_NORMAL)
        painter.setBrush(_BRUSH_FILL)
        painter.drawRect(QRectF(-20, -12, 40, 24))
        painter.setPen(QPen(_TEXT_COLOR, 1.0))
        painter.setFont(QFont("Sans", 8, QFont.Bold))
        painter.drawText(QRectF(-20, -12, 40, 24), Qt.AlignCenter, self._BOX_TEXT)


class TACSSourceSymbol(_TextBox):
    LABEL = "Fonte TACS"
    _BOX_TEXT = "TACS"


class ModelUseSymbol(_TextBox):
    LABEL = "Bloco MODEL"
    _BOX_TEXT = "MODEL"


class TACSGenericSymbol(_TextBox):
    """Bloco TACS genérico — usado por PID, Integrator, LowPass,
    Limiter, TSum no MVP. Subclasses sobrescrevem ``_BOX_TEXT`` para
    indicar o tipo. v0.26.5."""
    LABEL = "Bloco TACS"
    _BOX_TEXT = "TACS"


class PIDSymbol(TACSGenericSymbol):
    LABEL = "Controlador PID"
    _BOX_TEXT = "PID"


class IntegratorSymbol(TACSGenericSymbol):
    LABEL = "Integrador"
    _BOX_TEXT = "1/s"


class LowPassSymbol(TACSGenericSymbol):
    LABEL = "Passa-baixa"
    _BOX_TEXT = "LPF"


class LimiterSymbol(TACSGenericSymbol):
    LABEL = "Limitador"
    _BOX_TEXT = "LIM"


class TSumSymbol(TACSGenericSymbol):
    LABEL = "Somador"
    _BOX_TEXT = "Σ"


class MotorSymbol(SymbolRenderer):
    """
    Motor elétrico (IM ou MS) — círculo com 'M' (cf. ANSI/IEEE
    standards). Conexão trifásica via 3 leads à direita. v0.27.7.9.
    """

    PINS = (
        (30, -20),  # A
        (30, 0),    # B
        (30, 20),   # C
    )
    SIZE = 60
    LABEL = "M"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_NORMAL)
        painter.setBrush(_BRUSH_FILL)
        # Círculo central (símbolo motor)
        painter.drawEllipse(QRectF(-25, -25, 50, 50))
        # Texto "M" no centro
        painter.setPen(QPen(_TEXT_COLOR, 1.0))
        painter.setFont(QFont("Sans", 14, QFont.Bold))
        painter.drawText(QRectF(-25, -25, 50, 50), Qt.AlignCenter, "M")
        # Leads para os 3 pinos
        painter.setPen(_PEN_NORMAL)
        for px, py in self.PINS:
            r = (px ** 2 + py ** 2) ** 0.5
            if r > 0:
                ux = 25 * px / r
                uy = 25 * py / r
                painter.drawLine(int(ux), int(uy), int(px), int(py))


class BusSymbol(SymbolRenderer):
    """
    Barramento elétrico **estilo PTW Power*Tools** (v0.92.1).

    Renderização: **linha grossa contínua** (6 px) no eixo Y=0,
    horizontal, comprimento variável ``self.length`` (px).
    Sem leads verticais — fios conectam diretamente em qualquer
    ponto da barra (multi-conexão arbitrária).

    Estado por instância (não singleton):

    * ``length``: comprimento total em pixels. Default 200.
      Mín 60, máx 4000. Snap em múltiplo de 10 px (grid).
    * Pinos sintéticos: gerados dinamicamente pela
      :meth:`pin_positions` em cada grid step ao longo da barra
      (multi-conexão estilo PTW). Todos os pinos são do mesmo
      nó elétrico (zero-impedância).

    Atualização a partir do PpComponent: o item delega a
    :meth:`update_from_component` para ler a propriedade
    ``"length"`` da lista ``component.properties`` e fixar o
    comprimento atual.

    Antes de v0.92.1: 4 taps fixos × 3 fases = 12 pinos
    hardcoded em (-80, -30, 30, 80) × (-25, 0, 25). Os taps
    eram restritivos para topologias com muitas conexões.
    """

    SIZE = 200
    LABEL = "BUS"
    DEFAULT_LENGTH = 200
    MIN_LENGTH = 60
    MAX_LENGTH = 4000
    PIN_SPACING = 10        # px (mesmo grid)
    BAR_THICKNESS = 6       # px (linha grossa)

    def __init__(self) -> None:
        super().__init__()
        self.length: int = self.DEFAULT_LENGTH

    def set_length(self, length: int) -> None:
        """
        Ajusta o comprimento da barra (px). Clamp [MIN, MAX] e
        snap para múltiplo de PIN_SPACING (grid).
        """
        try:
            v = int(length)
        except (TypeError, ValueError):
            v = self.DEFAULT_LENGTH
        v = max(self.MIN_LENGTH, min(self.MAX_LENGTH, v))
        v = (v // self.PIN_SPACING) * self.PIN_SPACING
        self.length = v

    def update_from_component(self, component) -> None:
        """
        Lê a propriedade ``length`` do PpComponent (catálogo
        BUS.ocomp tem ``name=length`` em ``properties``).

        Se a propriedade existir e for parseável, aplica via
        :meth:`set_length`. Senão mantém o default.

        PpComponent.properties é uma lista de PpProperty(value,
        visible). O índice da propriedade ``length`` é
        determinado consultando o spec do catálogo.
        """
        try:
            from app.preprocessor.spec import get_default_registry
        except ImportError:
            return
        try:
            spec = get_default_registry().get(component.type)
        except Exception:
            return
        if spec is None:
            return
        for idx, prop_spec in enumerate(spec.properties):
            if prop_spec.name == "length":
                if idx < len(component.properties):
                    raw = component.properties[idx].value
                    try:
                        self.set_length(int(float(str(raw))))
                    except (TypeError, ValueError):
                        pass
                return

    def bounding_rect(self) -> QRectF:
        """Rect que cobre a barra + label + folga de pen halo."""
        half = self.length / 2.0
        # Folga vertical: label "BUS" acima (~16 px) + halo (~4)
        return QRectF(
            -half - 8, -22,
            self.length + 16, 38,
        )

    def pin_positions(self) -> list[tuple[int, int]]:
        """
        Pinos **sintéticos** ao longo da barra: um a cada
        ``PIN_SPACING`` px (10 px = 1 grid step). Permite ao
        editor de fios "snap" em qualquer ponto da barra com
        precisão de grid.

        Todos pertencem ao mesmo nó elétrico (a barra inteira
        é zero-impedância). O bridge para análise coalesce
        automaticamente — o usuário não vê diferença.
        """
        half = int(self.length // 2)
        # Garante alinhamento ao grid
        half = (half // self.PIN_SPACING) * self.PIN_SPACING
        pins: list[tuple[int, int]] = []
        x = -half
        while x <= half:
            pins.append((x, 0))
            x += self.PIN_SPACING
        return pins

    def endpoint_positions(self) -> tuple[tuple[int, int], tuple[int, int]]:
        """v0.92.1: posições dos dois endpoints (left, right)
        para ancorar handles de redimensionamento.

        v0.92.2: usa ``length // 2`` exato (sem snap a PIN_SPACING)
        — o endpoint pode ficar em meio-grid para length múltiplo de
        10 mas não 20 (e.g., length=450 → half=225). Isto preserva
        a simetria do bus em torno do centro e mantém o endpoint
        oposto verdadeiramente fixo durante resize assimétrico.
        Pinos sintéticos (que precisam estar em grid) continuam
        snapped via :meth:`pin_positions`.
        """
        half = int(self.length // 2)
        return (-half, 0), (half, 0)

    def paint(self, painter: QPainter) -> None:
        """Linha grossa contínua + label discreto acima."""
        half = self.length / 2.0
        # Barra horizontal grossa (estilo PTW Power*Tools)
        bus_pen = QPen(_PEN_NORMAL.color(), float(self.BAR_THICKNESS))
        bus_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bus_pen)
        painter.drawLine(int(-half), 0, int(half), 0)

        # Label "BUS" pequeno acima do centro (não interfere
        # nas conexões na barra)
        painter.setPen(QPen(_TEXT_COLOR, 1.0))
        painter.setFont(QFont("Sans", 8, QFont.Bold))
        painter.drawText(
            QRectF(-30, -20, 60, 14), Qt.AlignCenter, "BUS",
        )


class SynchronousMachineSymbol(SymbolRenderer):
    """
    Máquina síncrona — círculo com 'SM' e 3 terminais (A, B, C)
    + neutro. Representa MACHINE-59/58 do ATP. v0.27.0.
    """

    PINS = (
        (40, -20),  # A
        (40, 0),    # B
        (40, 20),   # C
        (40, 40),   # N (neutro)
    )
    SIZE = 80
    LABEL = "SM"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(_PEN_NORMAL)
        painter.setBrush(_BRUSH_FILL)
        # círculo central
        painter.drawEllipse(QRectF(-30, -30, 60, 60))
        # texto 'SM' no centro
        painter.setPen(QPen(_TEXT_COLOR, 1.0))
        painter.setFont(QFont("Sans", 10, QFont.Bold))
        painter.drawText(QRectF(-30, -30, 60, 60), Qt.AlignCenter, "SM")
        # leads para os pinos
        painter.setPen(_PEN_NORMAL)
        for px, py in self.PINS:
            # liga do círculo (raio 30) ao pino
            r = (px ** 2 + py ** 2) ** 0.5
            if r > 0:
                ux = 30 * px / r
                uy = 30 * py / r
                painter.drawLine(int(ux), int(uy), int(px), int(py))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


_REGISTRY: dict[str, type[SymbolRenderer]] = {
    # Passivos
    "R":       ResistorSymbol,
    "L":       InductorSymbol,
    "C":       CapacitorSymbol,
    "GND":     GroundSymbol,
    # Fontes
    "Vdc":     VdcSymbol,
    "Vac":     VacSymbol,
    "Idc":     IdcSymbol,
    "Iac":     IacSymbol,
    "Vrect":   VdcSymbol,             # rampa — mesmo desenho de DC por ora
    "Vsurge":  VdcSymbol,             # impulso — idem
    # Chaves
    "SwIdeal": SwitchIdealSymbol,
    "Relais":  RelaisSymbol,          # leads longos, pinos em ±50
    # v1.4.1: relé de PROTEÇÃO (50/51/49/87) — distinto de Relais
    # (chave controlada). Usa mesmo símbolo visual do Relais por
    # ora; v1.5+ pode ter símbolo dedicado com bobina + retângulo.
    "RELAY":   RelaisSymbol,
    # v1.4.3: disjuntor genérico controlado por relé.
    # Usa CircuitBreakerSymbol PTW-style (override por
    # ptw_symbols.get_ptw_renderer).
    "BREAKER": SwitchIdealSymbol,  # fallback; PTW override usa quadrado+cruz
    "SwTACS":  SwitchIdealSymbol,
    "VCB":     SwitchIdealSymbol,
    "VCB3":    VCB3PhaseSymbol,       # disjuntor a vácuo trifásico
    # Eletrônica de potência
    "Diode":   DiodeSymbol,
    "Thyr":    ThyristorSymbol,
    "GTO":     GTOSymbol,
    "IGBT":    IGBTSymbol,
    "MOSFET":  MOSFETSymbol,
    # Acoplados
    "Tr":      TransformerSymbol,
    "sTr":     TransformerSymbol,
    "Tr3":     TransformerSymbol,
    # v1.4.1: trafo trifásico para análise NBR/IEEE (não-ATP)
    "XFMR3":   TransformerSymbol,
    "MUT":     TransformerSymbol,     # indutores acoplados — mesmo desenho
    "XFMR":    TransformerSymbol,     # Hybrid Transformer (Mork) — mesmo símbolo
    # Linhas
    "TLIN":    LinePISymbol,
    "BERG":    LineBergeronSymbol,
    "JMARTI":  LineJMartiSymbol,
    # Não-lineares
    "ZnO":     ZnOSymbol,
    "RNL":     NonLinearRSymbol,
    "LNL":     NonLinearLSymbol,
    # Medidores
    "VProbe":  VProbeSymbol,
    "IProbe":  IProbeSymbol,
    # Controle
    "TACS":    TACSSourceSymbol,
    "MODEL":   ModelUseSymbol,
    # Controle TACS prebuilt (v0.26.5)
    "PID":         PIDSymbol,
    "Integrator":  IntegratorSymbol,
    "LowPass":     LowPassSymbol,
    "Limiter":     LimiterSymbol,
    "TSum":        TSumSymbol,
    # Máquinas (v0.27.0)
    "SM":          SynchronousMachineSymbol,
    # Motores (v0.27.7.9) — IM/MS para SC contribution
    "MOTOR":       MotorSymbol,
    # Barramentos (v0.27.7) — estilo SKM PTW
    "BUS":         BusSymbol,
}


def get_renderer(type_code: str) -> Optional[SymbolRenderer]:
    """
    Retorna uma instância do renderer para ``type_code``, ou None
    se o tipo não tem símbolo registrado (Eqn, .TR, .DC, .SW).

    **Ordem de consulta** (v1.1.0):

    1. ``ptw_symbols.get_ptw_renderer()`` — overrides PTW-style SLD
       para os componentes profissionais (CABLE, CT, FUSE, CONTACTOR).
       Se houver match, retorna direto (não consulta o registry IEEE).
    2. ``_REGISTRY`` (default IEEE 315 / Qucs) — fallback para os
       componentes legacy (R, L, C, Vdc, Vac, Tr, BUS, etc.) que
       ainda usam a convenção EMTP/ATPDraw.

    Esta dupla camada permite que componentes novos (v1.0.1+)
    apareçam com símbolos profissionais SLD (estilo PTW Power*Tools /
    ETAP / EasyPower) sem quebrar a aparência IEEE 315 dos legacy
    components.
    """
    # v1.1.0: PTW-style overrides têm precedência sobre o registry
    # default. Import lazy para evitar circular import (ptw_symbols
    # importa SymbolRenderer deste módulo).
    try:
        from app.preprocessor.ptw_symbols import get_ptw_renderer
    except ImportError:  # pragma: no cover - apenas em ambientes
        # sem PySide6 ou durante bootstrap parcial.
        get_ptw_renderer = None  # type: ignore[assignment]
    if get_ptw_renderer is not None:
        ptw = get_ptw_renderer(type_code)
        if ptw is not None:
            return ptw

    cls = _REGISTRY.get(type_code)
    if cls is None:
        return None
    return cls()


def all_renderers() -> dict[str, type[SymbolRenderer]]:
    """Cópia do registry completo (para introspecção / testes)."""
    return dict(_REGISTRY)
