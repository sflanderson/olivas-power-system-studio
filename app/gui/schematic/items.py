"""Custom QGraphicsItem classes for the schematic editor.

Provides:
    - NodeItem: draggable circle representing a named ATP node
    - ComponentEdge: branch or switch drawn as an electrical symbol
      between two NodeItems
    - SourceItem: source component attached to a single NodeItem
"""
from __future__ import annotations

import math
from typing import Any, Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsSimpleTextItem,
)

# ── Geometry constants ──────────────────────────────────────────────
NODE_RADIUS = 12
SYMBOL_W = 42
SYMBOL_H = 14

# ── Semantic → symbol mapping ───────────────────────────────────────
SEMANTIC_TO_SYMBOL: dict[str, str] = {
    # Branches
    "resistor": "resistor",
    "inductor": "inductor",
    "capacitor": "capacitor",
    "RC": "capacitor",
    "RL": "inductor",
    "LC": "capacitor",
    "RLC": "resistor",
    "snubber": "capacitor",
    "transformer": "transformer",
    "line": "line",
    "branch": "generic",
    # Switches
    "vcb": "switch",
    "tacs_controlled": "switch",
    "time_controlled": "switch",
    "measuring": "switch",
    "systematic": "switch",
    "switch": "switch",
    # Sources
    "ac": "source_ac",
    "dc": "source_dc",
    "ramp": "source_dc",
    "source": "source_ac",
}


# ════════════════════════════════════════════════════════════════════
# NodeItem
# ════════════════════════════════════════════════════════════════════
class NodeItem(QGraphicsEllipseItem):
    """Draggable, selectable node in the schematic."""

    Type = QGraphicsItem.UserType + 1

    def __init__(
        self,
        name: str,
        color: QColor,
        text_color: QColor,
        tooltip: str = "",
    ) -> None:
        r = NODE_RADIUS
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.node_name = name
        self._edges: list["ComponentEdge"] = []
        self._sources: list["SourceItem"] = []

        self._base_color = color
        self.setPen(QPen(color.darker(130), 2))
        self.setBrush(QBrush(color))
        self.setToolTip(tooltip)

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setZValue(10)

        # Label below
        self._label = QGraphicsSimpleTextItem(name, self)
        self._label.setFont(QFont("Consolas", 7))
        self._label.setBrush(QBrush(text_color))
        br = self._label.boundingRect()
        self._label.setPos(-br.width() / 2, r + 2)

    def type(self) -> int:  # noqa: A003
        return NodeItem.Type

    def add_edge(self, edge: "ComponentEdge") -> None:
        if edge not in self._edges:
            self._edges.append(edge)

    def add_source(self, source: "SourceItem") -> None:
        if source not in self._sources:
            self._sources.append(source)

    def edge_count(self) -> int:
        return len(self._edges)

    def source_count(self) -> int:
        return len(self._sources)

    def itemChange(self, change, value):  # type: ignore[override]
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self._edges:
                edge.update_geometry()
            for src in self._sources:
                src.update_geometry()
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            if value:
                self.setPen(QPen(self._base_color.lighter(170), 3))
            else:
                self.setPen(QPen(self._base_color.darker(130), 2))
        return super().itemChange(change, value)


# ════════════════════════════════════════════════════════════════════
# ComponentEdge
# ════════════════════════════════════════════════════════════════════
class ComponentEdge(QGraphicsItem):
    """Component (branch/switch) drawn as electrical symbol between two nodes."""

    Type = QGraphicsItem.UserType + 2

    def __init__(
        self,
        node1: NodeItem,
        node2: NodeItem,
        symbol: str,
        label: str,
        color: QColor,
        data: Any = None,
    ) -> None:
        super().__init__()
        self.node1 = node1
        self.node2 = node2
        self.symbol = symbol
        self.label_text = label
        self.color = color
        self.component_data = data

        node1.add_edge(self)
        node2.add_edge(self)

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)
        self.setToolTip(f"{label}\n{node1.node_name} ↔ {node2.node_name}")

    def type(self) -> int:  # noqa: A003
        return ComponentEdge.Type

    def update_geometry(self) -> None:
        self.prepareGeometryChange()
        self.update()

    def boundingRect(self) -> QRectF:  # noqa: N802
        p1 = self.node1.scenePos()
        p2 = self.node2.scenePos()
        m = SYMBOL_H + 24
        return QRectF(
            min(p1.x(), p2.x()) - m,
            min(p1.y(), p2.y()) - m,
            abs(p2.x() - p1.x()) + 2 * m,
            abs(p2.y() - p1.y()) + 2 * m,
        )

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        p1 = self.node1.scenePos()
        p2 = self.node2.scenePos()
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy)
        if length < 1:
            return path
        hw = 10
        nx = -dy / length * hw
        ny = dx / length * hw
        poly = QPolygonF(
            [
                QPointF(p1.x() + nx, p1.y() + ny),
                QPointF(p2.x() + nx, p2.y() + ny),
                QPointF(p2.x() - nx, p2.y() - ny),
                QPointF(p1.x() - nx, p1.y() - ny),
            ]
        )
        path.addPolygon(poly)
        path.closeSubpath()
        return path

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: ARG002
        p1 = self.node1.scenePos()
        p2 = self.node2.scenePos()
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy)
        if length < 1:
            return

        selected = self.isSelected()
        pen_color = self.color.lighter(160) if selected else self.color
        pen_width = 2.8 if selected else 1.8
        painter.setPen(QPen(pen_color, pen_width))
        painter.setBrush(Qt.NoBrush)
        painter.setRenderHint(QPainter.Antialiasing)

        angle = math.degrees(math.atan2(dy, dx))
        sw = min(SYMBOL_W, max(length * 0.35, 20))
        lead = (length - sw) / 2

        painter.save()
        painter.translate(p1)
        painter.rotate(angle)

        # Lead-in and lead-out
        painter.drawLine(QPointF(NODE_RADIUS, 0), QPointF(lead, 0))
        painter.drawLine(QPointF(lead + sw, 0), QPointF(length - NODE_RADIUS, 0))

        # Symbol
        _draw_symbol(painter, self.symbol, lead, sw, SYMBOL_H)

        painter.restore()

        # Label (horizontal, perpendicular to the line)
        if self.label_text:
            mid_x = (p1.x() + p2.x()) / 2
            mid_y = (p1.y() + p2.y()) / 2
            nx = -dy / length
            ny = dx / length
            offset = SYMBOL_H + 4
            lpos_x = mid_x + nx * offset
            lpos_y = mid_y + ny * offset
            painter.setFont(QFont("Consolas", 6))
            painter.setPen(QPen(pen_color))
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(self.label_text)
            th = fm.height()
            painter.drawText(
                QPointF(lpos_x - tw / 2, lpos_y + th / 4),
                self.label_text,
            )


# ════════════════════════════════════════════════════════════════════
# SourceItem
# ════════════════════════════════════════════════════════════════════
class SourceItem(QGraphicsItem):
    """Source component attached to a single node (drawn as symbol + ground)."""

    Type = QGraphicsItem.UserType + 3

    def __init__(
        self,
        node: NodeItem,
        symbol: str,
        label: str,
        color: QColor,
        data: Any = None,
        side_offset: float = 0.0,
    ) -> None:
        super().__init__()
        self.node = node
        self.symbol = symbol
        self.label_text = label
        self.color = color
        self.component_data = data
        self._side_offset = side_offset

        node.add_source(self)

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)
        self.setToolTip(f"{label}\nnó: {node.node_name}")

    def type(self) -> int:  # noqa: A003
        return SourceItem.Type

    def update_geometry(self) -> None:
        self.prepareGeometryChange()
        self.update()

    def boundingRect(self) -> QRectF:  # noqa: N802
        p = self.node.scenePos()
        return QRectF(
            p.x() + self._side_offset - 26,
            p.y() + NODE_RADIUS - 4,
            52,
            78,
        )

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        p = self.node.scenePos()
        cx = p.x() + self._side_offset
        cy = p.y() + NODE_RADIUS + 14 + 12
        path.addEllipse(QPointF(cx, cy), 16, 16)
        return path

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: ARG002
        p = self.node.scenePos()
        x = p.x() + self._side_offset
        y0 = p.y() + NODE_RADIUS

        selected = self.isSelected()
        pen_color = self.color.lighter(160) if selected else self.color
        pen_width = 2.5 if selected else 1.7
        painter.setPen(QPen(pen_color, pen_width))
        painter.setBrush(Qt.NoBrush)
        painter.setRenderHint(QPainter.Antialiasing)

        # Lead from node down to circle
        lead = 12
        painter.drawLine(QPointF(p.x(), y0), QPointF(x, y0 + lead))

        # Source circle
        r = 12
        cy = y0 + lead + r
        painter.drawEllipse(QPointF(x, cy), r, r)

        if self.symbol == "source_ac":
            path = QPainterPath()
            sw = r * 0.65
            path.moveTo(x - sw, cy)
            path.cubicTo(
                QPointF(x - sw * 0.4, cy - r * 0.6),
                QPointF(x - sw * 0.1, cy - r * 0.6),
                QPointF(x, cy),
            )
            path.cubicTo(
                QPointF(x + sw * 0.1, cy + r * 0.6),
                QPointF(x + sw * 0.4, cy + r * 0.6),
                QPointF(x + sw, cy),
            )
            painter.drawPath(path)
        elif self.symbol == "source_dc":
            painter.drawLine(QPointF(x - 5, cy - 4), QPointF(x + 5, cy - 4))
            painter.drawLine(QPointF(x, cy - 8), QPointF(x, cy))
            painter.drawLine(QPointF(x - 5, cy + 5), QPointF(x + 5, cy + 5))

        # Ground below
        bottom = cy + r
        painter.drawLine(QPointF(x, bottom), QPointF(x, bottom + 8))
        gy = bottom + 8
        for i, w in enumerate([9, 6, 3]):
            painter.drawLine(
                QPointF(x - w, gy + i * 3),
                QPointF(x + w, gy + i * 3),
            )

        # Label
        if self.label_text:
            painter.setFont(QFont("Consolas", 6))
            painter.setPen(QPen(pen_color))
            painter.drawText(QPointF(x + r + 3, cy + 3), self.label_text)


# ════════════════════════════════════════════════════════════════════
# Symbol painters (drawn in rotated local coords; x-axis = p1→p2)
# ════════════════════════════════════════════════════════════════════
def _draw_symbol(painter: QPainter, symbol: str, x: float, w: float, h: float) -> None:
    fn = _SYMBOL_PAINTERS.get(symbol, _sym_generic)
    fn(painter, x, w, h)


def _sym_resistor(painter: QPainter, x: float, w: float, h: float) -> None:
    """Zigzag resistor symbol."""
    n = 6
    step = w / n
    path = QPainterPath()
    path.moveTo(x, 0)
    for i in range(n):
        y = h / 2 if i % 2 == 0 else -h / 2
        path.lineTo(x + (i + 0.5) * step, y)
    path.lineTo(x + w, 0)
    painter.drawPath(path)


def _sym_inductor(painter: QPainter, x: float, w: float, h: float) -> None:
    """Series of arcs (coils)."""
    n = 4
    aw = w / n
    path = QPainterPath()
    path.moveTo(x, 0)
    for i in range(n):
        x0 = x + i * aw
        path.cubicTo(
            QPointF(x0 + aw * 0.25, -h * 0.9),
            QPointF(x0 + aw * 0.75, -h * 0.9),
            QPointF(x0 + aw, 0),
        )
    painter.drawPath(path)


def _sym_capacitor(painter: QPainter, x: float, w: float, h: float) -> None:
    """Two parallel plates with a gap."""
    gap = max(w * 0.28, 6)
    px1 = x + w / 2 - gap / 2
    px2 = x + w / 2 + gap / 2
    painter.drawLine(QPointF(x, 0), QPointF(px1, 0))
    painter.drawLine(QPointF(px2, 0), QPointF(x + w, 0))
    painter.drawLine(QPointF(px1, -h * 0.9), QPointF(px1, h * 0.9))
    painter.drawLine(QPointF(px2, -h * 0.9), QPointF(px2, h * 0.9))


def _sym_switch(painter: QPainter, x: float, w: float, h: float) -> None:
    """Open switch: pivot at 30%, contact at 70%, angled arm between."""
    piv = x + w * 0.28
    con = x + w * 0.72
    painter.drawLine(QPointF(x, 0), QPointF(piv, 0))
    painter.drawLine(QPointF(piv, 0), QPointF(con, -h * 0.75))
    painter.drawEllipse(QPointF(piv, 0), 2, 2)
    painter.drawEllipse(QPointF(con, 0), 2, 2)
    painter.drawLine(QPointF(con, 0), QPointF(x + w, 0))


def _sym_transformer(painter: QPainter, x: float, w: float, h: float) -> None:
    """Two coils side by side with a vertical iron-core line."""
    mid = x + w / 2
    n = 3
    aw = (w / 2 - 2) / n

    # Left coil
    path = QPainterPath()
    path.moveTo(x, 0)
    for i in range(n):
        x0 = x + i * aw
        path.cubicTo(
            QPointF(x0 + aw * 0.25, -h * 0.85),
            QPointF(x0 + aw * 0.75, -h * 0.85),
            QPointF(x0 + aw, 0),
        )
    painter.drawPath(path)

    # Iron core
    painter.drawLine(QPointF(mid - 1.5, -h * 0.9), QPointF(mid - 1.5, h * 0.6))
    painter.drawLine(QPointF(mid + 1.5, -h * 0.9), QPointF(mid + 1.5, h * 0.6))

    # Right coil
    path2 = QPainterPath()
    x2 = mid + 2
    path2.moveTo(x2, 0)
    for i in range(n):
        x0 = x2 + i * aw
        path2.cubicTo(
            QPointF(x0 + aw * 0.25, -h * 0.85),
            QPointF(x0 + aw * 0.75, -h * 0.85),
            QPointF(x0 + aw, 0),
        )
    painter.drawPath(path2)


def _sym_line(painter: QPainter, x: float, w: float, h: float) -> None:
    """Distributed-parameter line: double line with direction marker."""
    painter.drawLine(QPointF(x, -h * 0.35), QPointF(x + w, -h * 0.35))
    painter.drawLine(QPointF(x, h * 0.35), QPointF(x + w, h * 0.35))
    painter.drawLine(QPointF(x, 0), QPointF(x + w * 0.15, 0))
    painter.drawLine(QPointF(x + w * 0.85, 0), QPointF(x + w, 0))


def _sym_generic(painter: QPainter, x: float, w: float, h: float) -> None:
    """Generic labeled box."""
    painter.drawRect(QRectF(x, -h / 2, w, h))


_SYMBOL_PAINTERS = {
    "resistor": _sym_resistor,
    "inductor": _sym_inductor,
    "capacitor": _sym_capacitor,
    "switch": _sym_switch,
    "transformer": _sym_transformer,
    "line": _sym_line,
    "generic": _sym_generic,
}
