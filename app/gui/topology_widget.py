from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QVBoxLayout,
    QWidget,
)

from app.core.project_model import AtpProject, Node
from app.gui.theme import DARK, get_palette

NODE_RADIUS = 14


class TopologyWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._palette = DARK
        self._project: Optional[AtpProject] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor(self._palette["topo_bg"])))

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        layout.addWidget(self.view)

    def apply_theme(self, palette: dict[str, str]) -> None:
        """Re-apply colors from the given palette and redraw."""
        self._palette = palette
        self.scene.setBackgroundBrush(QBrush(QColor(palette["topo_bg"])))
        if self._project is not None:
            self.load_project(self._project)

    def load_project(self, project: AtpProject) -> None:
        self._project = project
        self.scene.clear()
        if not project.nodes:
            return

        p = self._palette
        clr_node = QColor(p["topo_node"])
        clr_node_source = QColor(p["topo_node_source"])
        clr_node_model = QColor(p["topo_node_model"])
        clr_edge_branch = QColor(p["topo_edge_branch"])
        clr_edge_switch = QColor(p["topo_edge_switch"])
        clr_edge_snubber = QColor(p["topo_edge_snubber"])
        clr_text = QColor(p["topo_text"])

        positions = _layout_nodes(project)
        node_items: dict[str, QGraphicsEllipseItem] = {}

        # Draw nodes
        for name, pos in positions.items():
            node = project.nodes.get(name)
            if node is None:
                continue

            color = clr_node
            if "SOURCE" in node.sources:
                color = clr_node_source
            elif "MODELS" in node.sources and len(node.sources) == 1:
                color = clr_node_model

            ellipse = self.scene.addEllipse(
                pos.x() - NODE_RADIUS,
                pos.y() - NODE_RADIUS,
                NODE_RADIUS * 2,
                NODE_RADIUS * 2,
                QPen(color.darker(130), 2),
                QBrush(color),
            )
            ellipse.setToolTip(f"{name}\n{', '.join(node.sources)}")

            label = self.scene.addSimpleText(name, QFont("Consolas", 7))
            label.setBrush(QBrush(clr_text))
            label.setPos(pos.x() - label.boundingRect().width() / 2, pos.y() + NODE_RADIUS + 2)

            node_items[name] = ellipse

        # Draw edges from branches
        for branch in project.branches:
            n1, n2 = branch.node1, branch.node2
            if n1 in positions and n2 in positions:
                p1, p2 = positions[n1], positions[n2]
                pen = QPen(clr_edge_branch, 1.5)
                self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)

        # Draw edges from switches
        for switch in project.switches:
            n1, n2 = switch.node1, switch.node2
            if n1 in positions and n2 in positions:
                p1, p2 = positions[n1], positions[n2]
                is_snubber = switch.type_code.strip() == "11"
                pen = QPen(clr_edge_snubber if is_snubber else clr_edge_switch, 2, Qt.DashLine)
                self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)

        # Legend
        _draw_legend(self.scene, project, self._palette)

        # Fit to view
        self.view.fitInView(self.scene.sceneRect().adjusted(-40, -40, 40, 40), Qt.KeepAspectRatio)


def _layout_nodes(project: AtpProject) -> dict[str, QPointF]:
    """Force-directed-like layout, grouping by phase and function."""
    positions: dict[str, QPointF] = {}
    nodes = project.nodes

    # Classify nodes by phase suffix
    phase_a: list[str] = []
    phase_b: list[str] = []
    phase_c: list[str] = []
    neutral: list[str] = []

    for name in nodes:
        upper = name.upper()
        if upper.endswith("A") or "001A" in upper or "002A" in upper or "0020" in upper or "0021" in upper or "0022" in upper or "0027" in upper or "0042" in upper:
            phase_a.append(name)
        elif upper.endswith("B") or "001B" in upper or "002B" in upper or "0012" in upper or "0013" in upper or "0014" in upper or "0019" in upper or "0035" in upper:
            phase_b.append(name)
        elif upper.endswith("C") or "001C" in upper or "002C" in upper or "0004" in upper or "0005" in upper or "0006" in upper or "0011" in upper or "0034" in upper:
            phase_c.append(name)
        else:
            neutral.append(name)

    # Layout each group as a column
    col_spacing = 200
    row_spacing = 80

    def place_group(group: list[str], col_x: float) -> None:
        group.sort()
        start_y = -(len(group) * row_spacing) / 2
        for i, name in enumerate(group):
            positions[name] = QPointF(col_x, start_y + i * row_spacing)

    place_group(phase_a, 0)
    place_group(phase_b, col_spacing)
    place_group(phase_c, col_spacing * 2)
    place_group(neutral, col_spacing * 3)

    return positions


def _draw_legend(scene: QGraphicsScene, project: AtpProject, palette: dict[str, str]) -> None:
    """Draw a small legend in the top-left corner."""
    rect = scene.sceneRect()
    x0 = rect.left() + 10
    y0 = rect.top() + 10
    clr_text = QColor(palette["topo_text"])

    font = QFont("Consolas", 8)
    items = [
        (QColor(palette["topo_node"]), "Nó genérico"),
        (QColor(palette["topo_node_source"]), "Nó com fonte"),
        (QColor(palette["topo_node_model"]), "Nó só MODELS"),
        (QColor(palette["topo_edge_branch"]), "Branch (RLC)"),
        (QColor(palette["topo_edge_switch"]), "Switch (VCB)"),
        (QColor(palette["topo_edge_snubber"]), "Switch (Snubber)"),
    ]

    for i, (color, label) in enumerate(items):
        y = y0 + i * 18
        scene.addRect(x0, y + 2, 12, 12, QPen(Qt.NoPen), QBrush(color))
        txt = scene.addSimpleText(label, font)
        txt.setBrush(QBrush(clr_text))
        txt.setPos(x0 + 18, y)

    # Stats
    stats_y = y0 + len(items) * 18 + 10
    stats = scene.addSimpleText(
        f"Nós: {len(project.nodes)}  |  "
        f"Branches: {len(project.branches)}  |  "
        f"Switches: {len(project.switches)}  |  "
        f"Sources: {len(project.sources)}",
        font,
    )
    stats.setBrush(QBrush(clr_text))
    stats.setPos(x0, stats_y)
