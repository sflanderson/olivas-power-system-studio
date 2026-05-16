"""
app/gui/schematic_pp/tag_items.py — QGraphicsItem rendering para Tags.

v3.1.2 Sub-sprint B — fecha o deferred de v3.1.1 Sprint 4.

Implementa rendering visual no canvas para:

* :class:`LinkTagGraphicsItem` — Link Tag (PTW Tutorial §Part 1 p.35-42)
  - Texto + indicator triangular (closed_arrow) + click handler
  - Click emite signal `link_clicked(target)` que MainWindow trata
    abrindo o documento referenciado (oneline:/tcc:/report:/pdf:)

* :class:`LegendTagGraphicsItem` — Legend Tag (PTW Tutorial §Part 1 p.43-52)
  - Forma (Diamond / Hexagon / Circle / Rectangle) com texto interno
  - Cor de fundo configurável (default #fff7c0 PTW yellow)

Reference: PTW Tutorial v8.0 §Part 1 pp.35-52.
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF,
)
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsObject, QGraphicsSceneMouseEvent,
)

from app.preprocessor.models import PpLegendTag, PpLinkTag


# ---------------------------------------------------------------------------
# Color tokens (consistent with ptw_symbols.py)
# ---------------------------------------------------------------------------

_LINK_TAG_LINE = QColor(0, 102, 153)  # blue PTW accent
_LINK_TAG_FILL = QColor(220, 235, 255)  # very light blue
_LEGEND_DEFAULT_LINE = QColor(80, 80, 80)
_LEGEND_DEFAULT_FILL = QColor("#fff7c0")  # PTW yellow


# ---------------------------------------------------------------------------
# LinkTagGraphicsItem
# ---------------------------------------------------------------------------


class LinkTagGraphicsItem(QGraphicsObject):
    """Renders a :class:`PpLinkTag` on the canvas.

    Visual: rounded rectangle with text + closed-arrow triangle indicator
    (when ``closed_arrow=True``). Click emits :attr:`link_clicked` with
    the target URI string.

    The MainWindow connects the signal to navigation handlers:
    - ``oneline:DocName`` → open the named one-line document
    - ``tcc:CoordName`` → open TCC coordinogram
    - ``report:RPT_Name`` → open report viewer
    - ``pdf:path/to/file.pdf`` → open via QDesktopServices

    References
    ----------
    PTW Tutorial v8.0 §Part 1 p.35-42.
    """

    #: Emitted when the user clicks the tag.
    link_clicked = Signal(str)

    _ARROW_SIZE = 8.0
    _PADDING_X = 6.0
    _PADDING_Y = 3.0
    _MIN_WIDTH = 60.0

    def __init__(
        self,
        tag: PpLinkTag,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)
        self._tag = tag
        self.setPos(tag.x, tag.y)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setVisible(tag.visible)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)

    @property
    def tag(self) -> PpLinkTag:
        """Underlying :class:`PpLinkTag` model."""
        return self._tag

    def boundingRect(self) -> QRectF:
        # Estimate text width with default font
        font = QFont("Arial", 9)
        font.setBold(True)
        # Rough estimation: 6.5 px per char + paddings
        text_width = max(self._MIN_WIDTH, 6.5 * len(self._tag.label) + 2 * self._PADDING_X)
        height = 18.0
        if self._tag.closed_arrow:
            text_width += self._ARROW_SIZE + 4
        return QRectF(0, 0, text_width, height)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.boundingRect()
        font = QFont("Arial", 9)
        font.setBold(True)
        painter.setFont(font)

        # Background — rounded rectangle, light blue fill
        painter.setPen(QPen(_LINK_TAG_LINE, 1.2))
        painter.setBrush(QBrush(_LINK_TAG_FILL))
        painter.drawRoundedRect(rect, 4, 4)

        # Selection halo
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 153, 204), 2.0, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 5, 5)

        # Text
        painter.setPen(QPen(_LINK_TAG_LINE, 1.0))
        text_rect = rect.adjusted(self._PADDING_X, self._PADDING_Y,
                                    -self._PADDING_X, -self._PADDING_Y)
        if self._tag.closed_arrow:
            text_rect.adjust(0, 0, -self._ARROW_SIZE - 2, 0)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft,
                          self._tag.label)

        # Closed-arrow triangle (right side, pointing right)
        if self._tag.closed_arrow:
            arrow_x = rect.right() - self._ARROW_SIZE - 2
            arrow_y = rect.center().y()
            triangle = QPolygonF([
                QPointF(arrow_x, arrow_y - self._ARROW_SIZE / 2),
                QPointF(arrow_x + self._ARROW_SIZE, arrow_y),
                QPointF(arrow_x, arrow_y + self._ARROW_SIZE / 2),
            ])
            painter.setBrush(QBrush(_LINK_TAG_LINE))
            painter.drawPolygon(triangle)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Click → emit link_clicked."""
        if event.button() == Qt.LeftButton:
            # Only emit if mouse hasn't dragged significantly
            self.link_clicked.emit(self._tag.target)
        super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------------
# LegendTagGraphicsItem
# ---------------------------------------------------------------------------


class LegendTagGraphicsItem(QGraphicsObject):
    """Renders a :class:`PpLegendTag` shape (Diamond / Hexagon / Circle / Rect).

    References
    ----------
    PTW Tutorial v8.0 §Part 1 p.43-52.
    """

    _SIZE = 36.0  # default shape size in pixels (square bounding)

    def __init__(
        self,
        tag: PpLegendTag,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)
        self._tag = tag
        self.setPos(tag.x, tag.y)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setVisible(tag.visible)

    @property
    def tag(self) -> PpLegendTag:
        return self._tag

    def boundingRect(self) -> QRectF:
        return QRectF(-self._SIZE / 2, -self._SIZE / 2,
                      self._SIZE, self._SIZE)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.boundingRect()

        # Build shape path
        path = self._make_path(rect, self._tag.shape)

        # Fill + outline
        fill_color = QColor(self._tag.color)
        outline_color = _LEGEND_DEFAULT_LINE
        painter.setPen(QPen(outline_color, 1.5))
        painter.setBrush(QBrush(fill_color))
        painter.drawPath(path)

        # Selection halo
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 153, 204), 2.0, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            halo_path = self._make_path(rect.adjusted(-3, -3, 3, 3), self._tag.shape)
            painter.drawPath(halo_path)

        # Text inside shape
        painter.setPen(QPen(QColor(40, 40, 40), 1.0))
        font = QFont("Arial", 8)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self._tag.text)

    @staticmethod
    def _make_path(rect: QRectF, shape: str) -> QPainterPath:
        """Build a QPainterPath for the requested shape inside ``rect``."""
        path = QPainterPath()
        cx, cy = rect.center().x(), rect.center().y()
        w, h = rect.width(), rect.height()

        if shape == "Diamond":
            poly = QPolygonF([
                QPointF(cx, rect.top()),     # top
                QPointF(rect.right(), cy),   # right
                QPointF(cx, rect.bottom()),  # bottom
                QPointF(rect.left(), cy),    # left
            ])
            path.addPolygon(poly)
            path.closeSubpath()
        elif shape == "Hexagon":
            r = min(w, h) / 2
            pts = []
            for i in range(6):
                # flat-top hexagon
                ang = math.radians(60 * i)
                pts.append(QPointF(cx + r * math.cos(ang),
                                     cy + r * math.sin(ang)))
            poly = QPolygonF(pts)
            path.addPolygon(poly)
            path.closeSubpath()
        elif shape == "Circle":
            path.addEllipse(rect)
        elif shape == "Rectangle":
            path.addRoundedRect(rect, 3, 3)
        else:
            # Fallback (shouldn't happen — PpLegendTag validates shape)
            path.addRect(rect)
        return path


__all__ = [
    "LinkTagGraphicsItem",
    "LegendTagGraphicsItem",
]
