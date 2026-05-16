"""Schematic editor widget for interactive circuit visualization and editing.

Layout:
    ┌──────────────────── toolbar ──────────────────────────┐
    ├─────────┬────────────────────┬──────────────┤
    │ Palette │  Schematic view    │  Properties  │
    │ (types) │  (QGraphicsScene)  │  (QTextEdit) │
    └─────────┴────────────────────┴──────────────┘

Interactive features (Phase 3 — v0.19.0):
    - Draggable nodes with edges that track the move
    - Mouse-wheel zoom, Ctrl+F fit-to-view, Ctrl+0 reset zoom
    - Toolbar buttons to enter placement modes:
        * Add node (click on empty area to place)
        * Add branch/switch/source (click on 1-2 nodes to place)
    - Delete key removes selected components/nodes
    - F2 / double-click renames a node (propagates to all references)
    - Context menus on nodes, components, and empty scene area
    - All edits mark dataclasses with `modified`, `deleted`, `is_new`
      flags so a future serializer (Phase 4) can write them back to ATP.
"""
from __future__ import annotations

from collections import defaultdict
from enum import Enum, auto
from typing import Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QCursor,
    QFont,
    QKeySequence,
    QPainter,
    QShortcut,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.core.project_model import (
    AtpProject,
    BranchComponent,
    HeaderInfo,
    Node,
    Section,
    SourceComponent,
    SwitchComponent,
)
from app.gui.schematic.dialogs import (
    BranchDialog,
    NodeDialog,
    SourceDialog,
    SwitchDialog,
)
from app.gui.schematic.items import (
    SEMANTIC_TO_SYMBOL,
    ComponentEdge,
    NodeItem,
    SourceItem,
)
from app.gui.theme import DARK


# ════════════════════════════════════════════════════════════════════
# Placement mode state machine
# ════════════════════════════════════════════════════════════════════
class PlacementMode(Enum):
    IDLE = auto()
    PLACE_NODE = auto()
    PLACE_BRANCH = auto()
    PLACE_SWITCH = auto()
    PLACE_SOURCE = auto()


# ════════════════════════════════════════════════════════════════════
# View with mouse-wheel zoom
# ════════════════════════════════════════════════════════════════════
class SchematicView(QGraphicsView):
    """QGraphicsView with mouse-wheel zoom and pan-on-drag."""

    def __init__(self, scene: QGraphicsScene, parent: Optional[QWidget] = None) -> None:
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self._zoom_level = 0

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if event.angleDelta().y() > 0:
            factor = 1.2
            self._zoom_level += 1
        else:
            factor = 1 / 1.2
            self._zoom_level -= 1
        if -15 < self._zoom_level < 20:
            self.scale(factor, factor)
        else:
            self._zoom_level = max(-14, min(self._zoom_level, 19))

    def reset_zoom(self) -> None:
        self.resetTransform()
        self._zoom_level = 0


# ════════════════════════════════════════════════════════════════════
# Main editor widget
# ════════════════════════════════════════════════════════════════════
class SchematicEditor(QWidget):
    """Interactive schematic editor."""

    #: Emitted when the selection changes (component data or None).
    selection_changed = Signal(object)

    #: Emitted when the project was modified (add/delete/rename).
    project_modified = Signal()

    #: Emitted when a new empty project was created from the editor.
    project_created = Signal(object)  # AtpProject

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._palette: dict[str, str] = DARK
        self._project: Optional[AtpProject] = None

        self._node_items: dict[str, NodeItem] = {}
        self._edge_items: list[ComponentEdge] = []
        self._source_items: list[SourceItem] = []

        # Preserved node positions across reloads (key: node name)
        self._node_positions: dict[str, QPointF] = {}

        # Placement-mode state
        self._mode = PlacementMode.IDLE
        self._pending_first_node: Optional[NodeItem] = None

        self._build_ui()
        self._install_shortcuts()
        # Start with toolbar reflecting "no project" state
        self._update_toolbar_enablement()
        self._status_label.setText(self._idle_status_message())

    # ────────────────────────────────────────────────────────────────
    # UI construction
    # ────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Toolbar ──
        self._toolbar = QToolBar()
        self._toolbar.setMovable(False)

        self._act_new_project = QAction("🗎 Novo projeto", self)
        self._act_new_project.setToolTip(
            "Iniciar um projeto vazio — canvas limpo com seções BRANCH/SWITCH/SOURCE prontas para edição"
        )
        self._act_new_project.triggered.connect(self._new_project)

        self._act_add_node = QAction("+ Nó", self)
        self._act_add_node.setCheckable(True)
        self._act_add_node.setToolTip(
            "Clique para ativar: depois clique na tela para adicionar um nó"
        )
        self._act_add_node.toggled.connect(
            lambda on: self._set_mode(
                PlacementMode.PLACE_NODE if on else PlacementMode.IDLE
            )
        )

        self._act_add_branch = QAction("+ Branch", self)
        self._act_add_branch.setCheckable(True)
        self._act_add_branch.setToolTip(
            "Clique para ativar: depois clique em 2 nós para conectá-los"
        )
        self._act_add_branch.toggled.connect(
            lambda on: self._set_mode(
                PlacementMode.PLACE_BRANCH if on else PlacementMode.IDLE
            )
        )

        self._act_add_switch = QAction("+ Switch", self)
        self._act_add_switch.setCheckable(True)
        self._act_add_switch.setToolTip(
            "Clique para ativar: depois clique em 2 nós"
        )
        self._act_add_switch.toggled.connect(
            lambda on: self._set_mode(
                PlacementMode.PLACE_SWITCH if on else PlacementMode.IDLE
            )
        )

        self._act_add_source = QAction("+ Fonte", self)
        self._act_add_source.setCheckable(True)
        self._act_add_source.setToolTip(
            "Clique para ativar: depois clique em um nó"
        )
        self._act_add_source.toggled.connect(
            lambda on: self._set_mode(
                PlacementMode.PLACE_SOURCE if on else PlacementMode.IDLE
            )
        )

        self._act_delete = QAction("🗑 Excluir", self)
        self._act_delete.setShortcut(QKeySequence.Delete)
        self._act_delete.setToolTip(
            "Excluir os itens selecionados (Delete)"
        )
        self._act_delete.triggered.connect(self._delete_selected)

        self._toolbar.addAction(self._act_new_project)
        self._toolbar.addSeparator()
        self._toolbar.addAction(self._act_add_node)
        self._toolbar.addAction(self._act_add_branch)
        self._toolbar.addAction(self._act_add_switch)
        self._toolbar.addAction(self._act_add_source)
        self._toolbar.addSeparator()
        self._toolbar.addAction(self._act_delete)

        outer.addWidget(self._toolbar)

        # ── Status label below toolbar ──
        self._status_label = QLabel("Pronto.")
        self._status_label.setStyleSheet(
            "padding: 2px 8px; font-size: 10px;"
        )
        outer.addWidget(self._status_label)

        # ── Main 3-column splitter ──
        splitter = QSplitter(Qt.Horizontal)

        # Left: palette
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left_layout.setSpacing(4)

        lbl = QLabel("Componentes presentes")
        lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        left_layout.addWidget(lbl)

        hint = QLabel("Clique para destacar\nno esquemático.")
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 10px;")
        left_layout.addWidget(hint)

        self._comp_list = QListWidget()
        self._comp_list.currentItemChanged.connect(self._on_palette_click)
        left_layout.addWidget(self._comp_list, 1)

        fit_btn = QPushButton("Ajustar à janela")
        fit_btn.clicked.connect(self._fit_to_view)
        left_layout.addWidget(fit_btn)

        zoom_btn = QPushButton("Zoom 1:1")
        zoom_btn.clicked.connect(self._reset_zoom)
        left_layout.addWidget(zoom_btn)

        splitter.addWidget(left)

        # Center: canvas
        self._scene = QGraphicsScene()
        self._scene.setBackgroundBrush(QBrush(QColor(self._palette["topo_bg"])))
        self._scene.selectionChanged.connect(self._on_selection_changed)

        self._view = SchematicView(self._scene)
        self._view.setContextMenuPolicy(Qt.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._on_view_context_menu)

        # Route mouse clicks on the scene through our handler
        self._view.mouseDoubleClickEvent = self._on_view_double_click  # type: ignore[method-assign]
        self._view.mousePressEvent = self._wrap_mouse_press(  # type: ignore[method-assign]
            self._view.mousePressEvent
        )

        splitter.addWidget(self._view)

        # Right: properties
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 6, 6, 6)
        right_layout.setSpacing(4)

        plbl = QLabel("Propriedades")
        plbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        right_layout.addWidget(plbl)

        self._prop_panel = QTextEdit()
        self._prop_panel.setReadOnly(True)
        self._prop_panel.setFont(QFont("Consolas", 8))
        right_layout.addWidget(self._prop_panel, 1)

        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([170, 700, 240])

        outer.addWidget(splitter, 1)

    def _install_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self._reset_zoom)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._fit_to_view)
        QShortcut(QKeySequence("Escape"), self, activated=self._cancel_mode)
        QShortcut(QKeySequence("F2"), self, activated=self._rename_selected_node)
        # Delete key is already bound via QAction shortcut

    # ────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────
    def apply_theme(self, palette: dict[str, str]) -> None:
        self._palette = palette
        self._scene.setBackgroundBrush(QBrush(QColor(palette["topo_bg"])))
        if self._project is not None:
            self.reload()

    def load_project(self, project: AtpProject) -> None:
        """Load a parsed ATP project into the schematic (clears positions)."""
        self._project = project
        self._node_positions.clear()
        self.reload()

    def reload(self) -> None:
        """Re-render the scene from the current project, preserving positions."""
        if self._project is None:
            self._scene.clear()
            self._node_items.clear()
            self._edge_items.clear()
            self._source_items.clear()
            self._prop_panel.clear()
            self._update_palette_list(None)
            self._update_toolbar_enablement()
            self._status_label.setText(self._idle_status_message())
            return

        project = self._project

        # Save current positions before clearing
        for name, item in self._node_items.items():
            self._node_positions[name] = item.pos()

        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()
        self._source_items.clear()
        self._prop_panel.clear()

        if not project.nodes:
            self._update_palette_list(project)
            self._draw_empty_canvas_hint()
            self._update_toolbar_enablement()
            if self._mode == PlacementMode.IDLE:
                self._status_label.setText(self._idle_status_message())
            return

        p = self._palette
        clr_node = QColor(p["topo_node"])
        clr_src = QColor(p["topo_node_source"])
        clr_model = QColor(p["topo_node_model"])
        clr_text = QColor(p["topo_text"])
        clr_branch = QColor(p["topo_edge_branch"])
        clr_switch = QColor(p["topo_edge_switch"])
        clr_snubber = QColor(p["topo_edge_snubber"])

        default_positions = _layout_nodes(project)

        # Nodes
        for name, default_pos in default_positions.items():
            node = project.nodes.get(name)
            if node is None:
                continue
            if "SOURCE" in node.sources:
                color = clr_src
            elif "MODELS" in node.sources and len(node.sources) == 1:
                color = clr_model
            else:
                color = clr_node
            item = NodeItem(
                name,
                color,
                clr_text,
                tooltip=f"{name}\n{', '.join(node.sources)}",
            )
            pos = self._node_positions.get(name, default_pos)
            item.setPos(pos)
            self._scene.addItem(item)
            self._node_items[name] = item

        # Branch edges (skip deleted)
        for branch in project.branches:
            if branch.deleted:
                continue
            n1 = branch.node1.strip()
            n2 = branch.node2.strip()
            if n1 in self._node_items and n2 in self._node_items:
                symbol = SEMANTIC_TO_SYMBOL.get(branch.semantic_type, "generic")
                label = _branch_label(branch)
                edge = ComponentEdge(
                    self._node_items[n1],
                    self._node_items[n2],
                    symbol,
                    label,
                    clr_branch,
                    data=branch,
                )
                self._scene.addItem(edge)
                self._edge_items.append(edge)

        # Switch edges (skip deleted)
        for switch in project.switches:
            if switch.deleted:
                continue
            n1 = switch.node1.strip()
            n2 = switch.node2.strip()
            if n1 in self._node_items and n2 in self._node_items:
                is_snub = switch.type_code.strip() == "11"
                color = clr_snubber if is_snub else clr_switch
                label = switch.semantic_type or "switch"
                edge = ComponentEdge(
                    self._node_items[n1],
                    self._node_items[n2],
                    "switch",
                    label,
                    color,
                    data=switch,
                )
                self._scene.addItem(edge)
                self._edge_items.append(edge)

        # Source items (skip deleted)
        by_node: dict[str, list[SourceComponent]] = defaultdict(list)
        for source in project.sources:
            if source.deleted:
                continue
            by_node[source.node.strip()].append(source)

        for node_name, srcs in by_node.items():
            if node_name not in self._node_items:
                continue
            n = len(srcs)
            spacing = 18
            for idx, source in enumerate(srcs):
                offset = (idx - (n - 1) / 2) * spacing
                symbol = SEMANTIC_TO_SYMBOL.get(source.semantic_type, "source_ac")
                label = _source_label(source)
                src_item = SourceItem(
                    self._node_items[node_name],
                    symbol,
                    label,
                    clr_src,
                    data=source,
                    side_offset=offset,
                )
                self._scene.addItem(src_item)
                self._source_items.append(src_item)

        self._update_palette_list(project)
        self._update_toolbar_enablement()
        if self._mode == PlacementMode.IDLE:
            self._status_label.setText(self._idle_status_message())
        # Only fit on first load, not on edits
        if not self._node_positions:
            self._fit_to_view()

    # ────────────────────────────────────────────────────────────────
    # Palette
    # ────────────────────────────────────────────────────────────────
    def _update_palette_list(self, project: Optional[AtpProject]) -> None:
        self._comp_list.blockSignals(True)
        self._comp_list.clear()
        counts: dict[str, int] = defaultdict(int)
        if project is not None:
            for b in project.branches:
                if not b.deleted:
                    counts[b.semantic_type or "branch"] += 1
            for s in project.switches:
                if not s.deleted:
                    counts[s.semantic_type or "switch"] += 1
            for s in project.sources:
                if not s.deleted:
                    counts[s.semantic_type or "source"] += 1

        p = self._palette
        type_to_color = {
            "resistor": p["topo_edge_branch"],
            "inductor": p["topo_edge_branch"],
            "capacitor": p["topo_edge_branch"],
            "RC": p["topo_edge_branch"],
            "RL": p["topo_edge_branch"],
            "LC": p["topo_edge_branch"],
            "RLC": p["topo_edge_branch"],
            "snubber": p["topo_edge_snubber"],
            "transformer": p["topo_edge_branch"],
            "line": p["topo_edge_branch"],
            "branch": p["topo_edge_branch"],
            "vcb": p["topo_edge_switch"],
            "tacs_controlled": p["topo_edge_switch"],
            "time_controlled": p["topo_edge_switch"],
            "measuring": p["topo_edge_switch"],
            "systematic": p["topo_edge_switch"],
            "switch": p["topo_edge_switch"],
            "ac": p["topo_node_source"],
            "dc": p["topo_node_source"],
            "ramp": p["topo_node_source"],
            "source": p["topo_node_source"],
        }
        for typ, cnt in sorted(counts.items()):
            item = QListWidgetItem(f"{typ}   ({cnt})")
            item.setData(Qt.UserRole, typ)
            color = type_to_color.get(typ, p["fg"])
            item.setForeground(QBrush(QColor(color)))
            self._comp_list.addItem(item)
        self._comp_list.blockSignals(False)

    def _on_palette_click(
        self, current: Optional[QListWidgetItem], _previous: Optional[QListWidgetItem]
    ) -> None:
        if current is None:
            return
        typ = current.data(Qt.UserRole)
        self._scene.clearSelection()
        for edge in self._edge_items:
            d = edge.component_data
            if d is not None and getattr(d, "semantic_type", "") == typ:
                edge.setSelected(True)
        for src in self._source_items:
            d = src.component_data
            if d is not None and getattr(d, "semantic_type", "") == typ:
                src.setSelected(True)

    # ────────────────────────────────────────────────────────────────
    # View helpers
    # ────────────────────────────────────────────────────────────────
    def _fit_to_view(self) -> None:
        rect = self._scene.itemsBoundingRect()
        if rect.isValid():
            self._view.fitInView(rect.adjusted(-60, -60, 60, 60), Qt.KeepAspectRatio)
            self._view._zoom_level = 0  # noqa: SLF001

    def _reset_zoom(self) -> None:
        self._view.reset_zoom()

    def _draw_empty_canvas_hint(self) -> None:
        """Render a centered hint on the canvas when there are no nodes.

        The hint is a plain ``QGraphicsTextItem`` — it is cleared automatically
        the next time ``reload`` wipes the scene.
        """
        p = self._palette
        hint = QGraphicsTextItem()
        hint.setHtml(
            "<div style='text-align:center;'>"
            "<span style='font-size:14pt;'>📐 Projeto vazio</span><br><br>"
            "<span style='font-size:10pt;'>"
            "Clique em <b>+ Nó</b> na barra de ferramentas<br>"
            "e depois em uma área vazia para adicionar o primeiro nó."
            "</span>"
            "</div>"
        )
        hint.setDefaultTextColor(QColor(p.get("fg_dim", p["fg"])))
        hint.setFont(QFont("Segoe UI", 10))
        # Center the text item at scene origin
        br = hint.boundingRect()
        hint.setPos(-br.width() / 2, -br.height() / 2)
        # Ignore zoom so the hint stays legible
        hint.setFlag(QGraphicsTextItem.ItemIgnoresTransformations, True)
        # Don't let the user select or drag the hint
        hint.setAcceptedMouseButtons(Qt.NoButton)
        hint.setZValue(-100)
        self._scene.addItem(hint)
        # Give the view a small scene rect so fit-to-view is sensible
        self._scene.setSceneRect(-200, -100, 400, 200)
        self._fit_to_view()

    # ────────────────────────────────────────────────────────────────
    # Placement mode
    # ────────────────────────────────────────────────────────────────
    def _set_mode(self, mode: PlacementMode) -> None:
        # Guard: modes that require existing nodes are only useful if there
        # are any. On an empty canvas, redirect the user to create a node first.
        requires_nodes = mode in (
            PlacementMode.PLACE_BRANCH,
            PlacementMode.PLACE_SWITCH,
            PlacementMode.PLACE_SOURCE,
        )
        if requires_nodes and not self._node_items:
            QMessageBox.information(
                self,
                "Projeto vazio",
                "Crie ao menos um nó antes.\n\n"
                "Clique em '+ Nó' e depois em uma área vazia do canvas.",
            )
            # Untoggle whichever button the user pressed
            mode = PlacementMode.IDLE

        self._mode = mode
        self._pending_first_node = None

        # Sync toolbar action check states
        for act, m in (
            (self._act_add_node, PlacementMode.PLACE_NODE),
            (self._act_add_branch, PlacementMode.PLACE_BRANCH),
            (self._act_add_switch, PlacementMode.PLACE_SWITCH),
            (self._act_add_source, PlacementMode.PLACE_SOURCE),
        ):
            if act.isChecked() != (mode == m):
                act.blockSignals(True)
                act.setChecked(mode == m)
                act.blockSignals(False)

        # Update cursor and status
        cur = Qt.ArrowCursor
        if mode == PlacementMode.IDLE:
            msg = self._idle_status_message()
        elif mode == PlacementMode.PLACE_NODE:
            cur = Qt.CrossCursor
            msg = "Clique em uma área vazia para adicionar um nó. (Esc cancela)"
        elif mode == PlacementMode.PLACE_BRANCH:
            cur = Qt.CrossCursor
            msg = "Clique no PRIMEIRO nó para iniciar o branch. (Esc cancela)"
        elif mode == PlacementMode.PLACE_SWITCH:
            cur = Qt.CrossCursor
            msg = "Clique no PRIMEIRO nó para iniciar o switch. (Esc cancela)"
        elif mode == PlacementMode.PLACE_SOURCE:
            cur = Qt.CrossCursor
            msg = "Clique em um nó para adicionar uma fonte. (Esc cancela)"
        else:
            msg = "Pronto."
        self._view.viewport().setCursor(QCursor(cur))
        self._status_label.setText(msg)

    def _idle_status_message(self) -> str:
        """Status message when no placement mode is active."""
        if self._project is None:
            return "Abra um .atp ou clique em '🗎 Novo projeto' para começar."
        if not self._node_items:
            return (
                "Projeto vazio — clique em '+ Nó' para adicionar o primeiro nó."
            )
        return "Pronto."

    def _update_toolbar_enablement(self) -> None:
        """Grey out buttons that don't make sense for the current project state."""
        has_project = self._project is not None
        has_nodes = bool(self._node_items)
        self._act_add_node.setEnabled(has_project)
        self._act_add_branch.setEnabled(has_nodes)
        self._act_add_switch.setEnabled(has_nodes)
        self._act_add_source.setEnabled(has_nodes)
        self._act_delete.setEnabled(has_nodes)

    def _cancel_mode(self) -> None:
        if self._mode != PlacementMode.IDLE:
            self._set_mode(PlacementMode.IDLE)

    def _wrap_mouse_press(self, original_handler):
        """Wrap QGraphicsView.mousePressEvent to catch placement clicks."""

        def handler(event):
            if event.button() == Qt.LeftButton and self._mode != PlacementMode.IDLE:
                scene_pos = self._view.mapToScene(event.pos())
                item = self._scene.itemAt(scene_pos, self._view.transform())
                # Walk up the parent chain to find a NodeItem
                node_item: Optional[NodeItem] = None
                cur = item
                while cur is not None:
                    if isinstance(cur, NodeItem):
                        node_item = cur
                        break
                    cur = cur.parentItem()

                if self._mode == PlacementMode.PLACE_NODE:
                    if node_item is None:
                        self._add_node_at(scene_pos)
                    # Consume the click
                    event.accept()
                    return
                elif self._mode in (
                    PlacementMode.PLACE_BRANCH,
                    PlacementMode.PLACE_SWITCH,
                ):
                    if node_item is not None:
                        self._handle_two_node_click(node_item)
                    event.accept()
                    return
                elif self._mode == PlacementMode.PLACE_SOURCE:
                    if node_item is not None:
                        self._add_source_on(node_item)
                    event.accept()
                    return
            return original_handler(event)

        return handler

    def _handle_two_node_click(self, node: NodeItem) -> None:
        if self._pending_first_node is None:
            self._pending_first_node = node
            self._status_label.setText(
                f"Primeiro nó: {node.node_name}. Clique no SEGUNDO nó. (Esc cancela)"
            )
            return
        if self._pending_first_node is node:
            self._status_label.setText(
                "Selecione um nó DIFERENTE do primeiro. (Esc cancela)"
            )
            return
        first = self._pending_first_node
        second = node
        mode = self._mode
        self._set_mode(PlacementMode.IDLE)
        if mode == PlacementMode.PLACE_BRANCH:
            self._add_branch_between(first.node_name, second.node_name)
        elif mode == PlacementMode.PLACE_SWITCH:
            self._add_switch_between(first.node_name, second.node_name)

    # ────────────────────────────────────────────────────────────────
    # Edit operations (mutate project in place, then reload)
    # ────────────────────────────────────────────────────────────────
    def _new_project(self) -> None:
        """Start an empty AtpProject from scratch (canvas cleared).

        If a project is already loaded and has edits, asks for confirmation.
        Emits ``project_created`` so the surrounding MainWindow can wire up
        a case entry for it.
        """
        if self._project is not None:
            has_edits = (
                any(getattr(b, "modified", False) or getattr(b, "is_new", False)
                    for b in self._project.branches)
                or any(getattr(s, "modified", False) or getattr(s, "is_new", False)
                       for s in self._project.switches)
                or any(getattr(s, "modified", False) or getattr(s, "is_new", False)
                       for s in self._project.sources)
            )
            if has_edits:
                reply = QMessageBox.question(
                    self,
                    "Novo projeto",
                    "O projeto atual tem edições não-salvas. Iniciar um novo projeto "
                    "irá descartá-las. Continuar?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

        fresh = _make_empty_project()
        self.load_project(fresh)
        self.project_created.emit(fresh)
        self.project_modified.emit()

    def _add_node_at(self, scene_pos: QPointF) -> None:
        if self._project is None:
            return
        taken = set(self._project.nodes.keys())
        dlg = NodeDialog(self, title="Adicionar nó", taken=taken)
        if dlg.exec() != NodeDialog.Accepted:
            return
        name = dlg.node_name()
        self._project.nodes[name] = Node(name=name, sources=[])
        self._node_positions[name] = scene_pos
        self.reload()
        self.project_modified.emit()

    def _add_branch_between(self, n1: str, n2: str) -> None:
        if self._project is None:
            return
        dlg = BranchDialog(self, node1=n1, node2=n2)
        if dlg.exec() != BranchDialog.Accepted:
            return
        data = dlg.get_data()
        if not data["node1"] or not data["node2"]:
            return
        branch = BranchComponent(
            node1=data["node1"],
            node2=data["node2"],
            semantic_type=data["semantic_type"],
            resistance=data["resistance"],
            inductance=data["inductance"],
            capacitance=data["capacitance"],
            is_new=True,
            modified=True,
        )
        self._project.branches.append(branch)
        self._ensure_node(data["node1"])
        self._ensure_node(data["node2"])
        self.reload()
        self.project_modified.emit()

    def _add_switch_between(self, n1: str, n2: str) -> None:
        if self._project is None:
            return
        dlg = SwitchDialog(self, node1=n1, node2=n2)
        if dlg.exec() != SwitchDialog.Accepted:
            return
        data = dlg.get_data()
        if not data["node1"] or not data["node2"]:
            return
        switch = SwitchComponent(
            node1=data["node1"],
            node2=data["node2"],
            semantic_type=data["semantic_type"],
            t_close=data["t_close"],
            t_open=data["t_open"],
            tacs_output=data["tacs_output"],
            is_new=True,
            modified=True,
        )
        self._project.switches.append(switch)
        self._ensure_node(data["node1"])
        self._ensure_node(data["node2"])
        self.reload()
        self.project_modified.emit()

    def _add_source_on(self, node: NodeItem) -> None:
        if self._project is None:
            return
        dlg = SourceDialog(self, node=node.node_name)
        if dlg.exec() != SourceDialog.Accepted:
            return
        data = dlg.get_data()
        if not data["node"]:
            return
        source = SourceComponent(
            node=data["node"],
            semantic_type=data["semantic_type"],
            amplitude=data["amplitude"],
            frequency=data["frequency"],
            phase=data["phase"],
            t_start=data["t_start"],
            t_stop=data["t_stop"],
            is_new=True,
            modified=True,
        )
        self._project.sources.append(source)
        self._ensure_node(data["node"])
        # Mark node as having a source
        if "SOURCE" not in self._project.nodes[data["node"]].sources:
            self._project.nodes[data["node"]].sources.append("SOURCE")
        self.reload()
        self.project_modified.emit()

    def _ensure_node(self, name: str) -> None:
        """Add the node to project if not already present."""
        if self._project is None or not name:
            return
        if name not in self._project.nodes:
            self._project.nodes[name] = Node(name=name, sources=[])

    def _delete_selected(self) -> None:
        if self._project is None:
            return
        items = self._scene.selectedItems()
        if not items:
            return
        # Count what will be deleted, ask confirmation
        n_nodes = sum(1 for i in items if isinstance(i, NodeItem))
        n_edges = sum(1 for i in items if isinstance(i, ComponentEdge))
        n_srcs = sum(1 for i in items if isinstance(i, SourceItem))
        parts = []
        if n_nodes:
            parts.append(f"{n_nodes} nó(s)")
        if n_edges:
            parts.append(f"{n_edges} componente(s)")
        if n_srcs:
            parts.append(f"{n_srcs} fonte(s)")
        if not parts:
            return
        reply = QMessageBox.question(
            self,
            "Confirmar exclusão",
            f"Excluir {', '.join(parts)}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        deleted_node_names: set[str] = set()
        for item in items:
            if isinstance(item, ComponentEdge):
                d = item.component_data
                if d is not None:
                    d.deleted = True
                    d.modified = True
            elif isinstance(item, SourceItem):
                d = item.component_data
                if d is not None:
                    d.deleted = True
                    d.modified = True
            elif isinstance(item, NodeItem):
                deleted_node_names.add(item.node_name)

        # Deleting a node cascades to all components touching it
        if deleted_node_names:
            for b in self._project.branches:
                if (
                    b.node1.strip() in deleted_node_names
                    or b.node2.strip() in deleted_node_names
                ):
                    b.deleted = True
                    b.modified = True
            for s in self._project.switches:
                if (
                    s.node1.strip() in deleted_node_names
                    or s.node2.strip() in deleted_node_names
                ):
                    s.deleted = True
                    s.modified = True
            for s in self._project.sources:
                if s.node.strip() in deleted_node_names:
                    s.deleted = True
                    s.modified = True
            for name in deleted_node_names:
                self._project.nodes.pop(name, None)
                self._node_positions.pop(name, None)

        self.reload()
        self.project_modified.emit()

    def _rename_selected_node(self) -> None:
        if self._project is None:
            return
        items = self._scene.selectedItems()
        node_items = [i for i in items if isinstance(i, NodeItem)]
        if len(node_items) != 1:
            return
        self._rename_node(node_items[0])

    def _rename_node(self, node_item: NodeItem) -> None:
        if self._project is None:
            return
        old = node_item.node_name
        taken = set(self._project.nodes.keys()) - {old}
        dlg = NodeDialog(
            self, title=f"Renomear nó '{old}'", initial=old, taken=taken
        )
        if dlg.exec() != NodeDialog.Accepted:
            return
        new = dlg.node_name()
        if new == old or not new:
            return

        # Update project.nodes dict
        node_obj = self._project.nodes.pop(old)
        node_obj.name = new
        self._project.nodes[new] = node_obj

        # Preserve position under the new key
        if old in self._node_positions:
            self._node_positions[new] = self._node_positions.pop(old)

        # Update all components referencing the old name
        for b in self._project.branches:
            changed = False
            if b.node1.strip() == old:
                b.node1 = new
                changed = True
            if b.node2.strip() == old:
                b.node2 = new
                changed = True
            if changed:
                b.modified = True
        for s in self._project.switches:
            changed = False
            if s.node1.strip() == old:
                s.node1 = new
                changed = True
            if s.node2.strip() == old:
                s.node2 = new
                changed = True
            if changed:
                s.modified = True
        for s in self._project.sources:
            if s.node.strip() == old:
                s.node = new
                s.modified = True

        self.reload()
        self.project_modified.emit()

    # ────────────────────────────────────────────────────────────────
    # Context menus
    # ────────────────────────────────────────────────────────────────
    def _on_view_context_menu(self, pos) -> None:
        scene_pos = self._view.mapToScene(pos)
        item = self._scene.itemAt(scene_pos, self._view.transform())
        # Walk up to find a meaningful item
        target = item
        while target is not None and not isinstance(
            target, (NodeItem, ComponentEdge, SourceItem)
        ):
            target = target.parentItem()

        menu = QMenu(self)
        if isinstance(target, NodeItem):
            act_rename = menu.addAction("Renomear nó (F2)")
            act_rename.triggered.connect(lambda: self._rename_node(target))
            act_del = menu.addAction("Excluir nó e conexões")
            act_del.triggered.connect(lambda: self._delete_node(target))
            menu.addSeparator()
            act_branch = menu.addAction("Adicionar branch a partir deste nó...")
            act_branch.triggered.connect(
                lambda: self._start_from_node(target, PlacementMode.PLACE_BRANCH)
            )
            act_switch = menu.addAction("Adicionar switch a partir deste nó...")
            act_switch.triggered.connect(
                lambda: self._start_from_node(target, PlacementMode.PLACE_SWITCH)
            )
            act_source = menu.addAction("Adicionar fonte neste nó...")
            act_source.triggered.connect(lambda: self._add_source_on(target))
        elif isinstance(target, ComponentEdge):
            act_edit = menu.addAction("Editar parâmetros...")
            act_edit.triggered.connect(lambda: self._edit_edge(target))
            act_del = menu.addAction("Excluir componente")
            act_del.triggered.connect(lambda: self._delete_edge(target))
        elif isinstance(target, SourceItem):
            act_edit = menu.addAction("Editar fonte...")
            act_edit.triggered.connect(lambda: self._edit_source(target))
            act_del = menu.addAction("Excluir fonte")
            act_del.triggered.connect(lambda: self._delete_source(target))
        else:
            act_add = menu.addAction("Adicionar nó aqui...")
            act_add.triggered.connect(lambda: self._add_node_at(scene_pos))

        menu.exec(self._view.viewport().mapToGlobal(pos))

    def _start_from_node(self, node: NodeItem, mode: PlacementMode) -> None:
        self._set_mode(mode)
        self._handle_two_node_click(node)

    def _delete_node(self, node: NodeItem) -> None:
        self._scene.clearSelection()
        node.setSelected(True)
        self._delete_selected()

    def _delete_edge(self, edge: ComponentEdge) -> None:
        d = edge.component_data
        if d is None:
            return
        d.deleted = True
        d.modified = True
        self.reload()
        self.project_modified.emit()

    def _delete_source(self, src: SourceItem) -> None:
        d = src.component_data
        if d is None:
            return
        d.deleted = True
        d.modified = True
        self.reload()
        self.project_modified.emit()

    def _edit_edge(self, edge: ComponentEdge) -> None:
        d = edge.component_data
        if isinstance(d, BranchComponent):
            dlg = BranchDialog(self, branch=d)
            if dlg.exec() != BranchDialog.Accepted:
                return
            data = dlg.get_data()
            d.node1 = data["node1"]
            d.node2 = data["node2"]
            d.semantic_type = data["semantic_type"]
            d.resistance = data["resistance"]
            d.inductance = data["inductance"]
            d.capacitance = data["capacitance"]
            d.modified = True
            self._ensure_node(d.node1)
            self._ensure_node(d.node2)
            self.reload()
            self.project_modified.emit()
        elif isinstance(d, SwitchComponent):
            dlg = SwitchDialog(self, switch=d)
            if dlg.exec() != SwitchDialog.Accepted:
                return
            data = dlg.get_data()
            d.node1 = data["node1"]
            d.node2 = data["node2"]
            d.semantic_type = data["semantic_type"]
            d.t_close = data["t_close"]
            d.t_open = data["t_open"]
            d.tacs_output = data["tacs_output"]
            d.modified = True
            self._ensure_node(d.node1)
            self._ensure_node(d.node2)
            self.reload()
            self.project_modified.emit()

    def _edit_source(self, src: SourceItem) -> None:
        d = src.component_data
        if isinstance(d, SourceComponent):
            dlg = SourceDialog(self, source=d)
            if dlg.exec() != SourceDialog.Accepted:
                return
            data = dlg.get_data()
            d.node = data["node"]
            d.semantic_type = data["semantic_type"]
            d.amplitude = data["amplitude"]
            d.frequency = data["frequency"]
            d.phase = data["phase"]
            d.t_start = data["t_start"]
            d.t_stop = data["t_stop"]
            d.modified = True
            self._ensure_node(d.node)
            self.reload()
            self.project_modified.emit()

    def _on_view_double_click(self, event) -> None:
        scene_pos = self._view.mapToScene(event.pos())
        item = self._scene.itemAt(scene_pos, self._view.transform())
        target = item
        while target is not None and not isinstance(
            target, (NodeItem, ComponentEdge, SourceItem)
        ):
            target = target.parentItem()
        if isinstance(target, NodeItem):
            self._rename_node(target)
        elif isinstance(target, ComponentEdge):
            self._edit_edge(target)
        elif isinstance(target, SourceItem):
            self._edit_source(target)
        else:
            QGraphicsView.mouseDoubleClickEvent(self._view, event)

    # ────────────────────────────────────────────────────────────────
    # Selection / property panel
    # ────────────────────────────────────────────────────────────────
    def _on_selection_changed(self) -> None:
        items = self._scene.selectedItems()
        if not items:
            self._prop_panel.clear()
            self.selection_changed.emit(None)
            return

        item = items[0]
        if isinstance(item, NodeItem):
            self._show_node_props(item)
            self.selection_changed.emit(
                self._project.nodes.get(item.node_name) if self._project else None
            )
        elif isinstance(item, ComponentEdge):
            self._show_edge_props(item)
            self.selection_changed.emit(item.component_data)
        elif isinstance(item, SourceItem):
            self._show_source_props(item)
            self.selection_changed.emit(item.component_data)

    def _show_node_props(self, item: NodeItem) -> None:
        node = (
            self._project.nodes.get(item.node_name)
            if self._project is not None
            else None
        )
        html = [f"<b>Nó:</b> <code>{item.node_name}</code><br><br>"]
        if node is not None:
            html.append(
                f"<b>Origens:</b> {', '.join(node.sources) or '—'}<br>"
            )
        html.append(
            f"<b>Componentes:</b> {item.edge_count()}<br>"
            f"<b>Fontes:</b> {item.source_count()}<br><br>"
            "<small>F2 ou duplo-clique para renomear.<br>"
            "Delete para excluir.</small>"
        )
        self._prop_panel.setHtml("".join(html))

    def _show_edge_props(self, item: ComponentEdge) -> None:
        d = item.component_data
        html: list[str] = []
        status = ""
        if d is not None:
            if getattr(d, "is_new", False):
                status = "  <span style='color:#81c784'>[novo]</span>"
            elif getattr(d, "modified", False):
                status = "  <span style='color:#ffb74d'>[modificado]</span>"
        if isinstance(d, BranchComponent):
            html.append(
                f"<b>Branch</b>{status}<br>"
                f"<b>Tipo:</b> {d.semantic_type or '—'}<br>"
                f"<b>Nó 1:</b> <code>{d.node1}</code><br>"
                f"<b>Nó 2:</b> <code>{d.node2}</code><br>"
            )
            if d.resistance and d.resistance.strip():
                html.append(f"<b>R:</b> {d.resistance.strip()} Ω<br>")
            if d.inductance and d.inductance.strip():
                html.append(f"<b>L:</b> {d.inductance.strip()} mH<br>")
            if d.capacitance and d.capacitance.strip():
                html.append(f"<b>C:</b> {d.capacitance.strip()} µF<br>")
            if d.ref1:
                html.append(f"<b>Ref 1:</b> <code>{d.ref1}</code><br>")
            if d.ref2:
                html.append(f"<b>Ref 2:</b> <code>{d.ref2}</code><br>")
            if d.raw_line:
                html.append(
                    f"<br><b>Linha {d.line_number}:</b><br>"
                    f"<code>{_esc(d.raw_line)}</code>"
                )
            html.append("<br><small>Duplo-clique para editar.</small>")
        elif isinstance(d, SwitchComponent):
            html.append(
                f"<b>Switch</b>{status}<br>"
                f"<b>Tipo:</b> {d.semantic_type or '—'}<br>"
                f"<b>Nó 1:</b> <code>{d.node1}</code><br>"
                f"<b>Nó 2:</b> <code>{d.node2}</code><br>"
            )
            if d.t_close:
                html.append(f"<b>Tclose:</b> {d.t_close}<br>")
            if d.t_open:
                html.append(f"<b>Topen:</b> {d.t_open}<br>")
            if d.tacs_output:
                html.append(f"<b>TACS out:</b> <code>{d.tacs_output}</code><br>")
            if d.raw_line:
                html.append(
                    f"<br><b>Linha {d.line_number}:</b><br>"
                    f"<code>{_esc(d.raw_line)}</code>"
                )
            html.append("<br><small>Duplo-clique para editar.</small>")
        self._prop_panel.setHtml("".join(html))

    def _show_source_props(self, item: SourceItem) -> None:
        d = item.component_data
        html: list[str] = []
        status = ""
        if d is not None:
            if getattr(d, "is_new", False):
                status = "  <span style='color:#81c784'>[novo]</span>"
            elif getattr(d, "modified", False):
                status = "  <span style='color:#ffb74d'>[modificado]</span>"
        if isinstance(d, SourceComponent):
            html.append(
                f"<b>Fonte</b>{status}<br>"
                f"<b>Tipo:</b> {d.semantic_type or '—'}<br>"
                f"<b>Nó:</b> <code>{d.node}</code><br>"
                f"<b>Tipo ATP:</b> {d.type_code or '—'}<br>"
            )
            if d.amplitude:
                html.append(f"<b>Amplitude:</b> {d.amplitude.strip()}<br>")
            if d.frequency:
                html.append(f"<b>Frequência:</b> {d.frequency.strip()} Hz<br>")
            if d.phase:
                html.append(f"<b>Fase:</b> {d.phase.strip()}°<br>")
            if d.t_start:
                html.append(f"<b>T início:</b> {d.t_start.strip()}<br>")
            if d.t_stop:
                html.append(f"<b>T fim:</b> {d.t_stop.strip()}<br>")
            if d.raw_line:
                html.append(
                    f"<br><b>Linha {d.line_number}:</b><br>"
                    f"<code>{_esc(d.raw_line)}</code>"
                )
            html.append("<br><small>Duplo-clique para editar.</small>")
        self._prop_panel.setHtml("".join(html))


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════
def _esc(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _branch_label(branch: BranchComponent) -> str:
    parts: list[str] = []
    for prefix, val in (
        ("R", branch.resistance),
        ("L", branch.inductance),
        ("C", branch.capacitance),
    ):
        if val and val.strip():
            try:
                f = float(val.strip())
                parts.append(f"{prefix}={f:g}")
            except ValueError:
                parts.append(f"{prefix}={val.strip()}")
    if parts:
        return " ".join(parts)
    return branch.semantic_type or "branch"


def _source_label(source: SourceComponent) -> str:
    if source.amplitude and source.amplitude.strip():
        try:
            a = float(source.amplitude.strip())
            return f"{a:g}"
        except ValueError:
            return source.amplitude.strip()
    return source.semantic_type or "src"


def _layout_nodes(project: AtpProject) -> dict[str, QPointF]:
    """Initial layout.

    Uses a phase-column layout (A / B / C / N) when the circuit looks
    three-phase (≥ 60% of nodes end in A, B or C) and falls back to a grid
    layout otherwise. Force-directed refinement can be added later.
    """
    if not project.nodes:
        return {}

    names = list(project.nodes.keys())
    phase_count = sum(
        1 for n in names if n.strip().upper()[-1:] in ("A", "B", "C")
    )
    is_three_phase = phase_count >= 0.6 * len(names)

    if is_three_phase:
        return _phase_column_layout(names)
    return _grid_layout(names)


def _phase_column_layout(names: list[str]) -> dict[str, QPointF]:
    """Three-phase columns: A (left) / B / C / N (right, includes misc)."""
    groups: dict[str, list[str]] = {"A": [], "B": [], "C": [], "N": []}
    for name in names:
        upper = name.strip().upper()
        if not upper:
            groups["N"].append(name)
        elif upper.endswith("A"):
            groups["A"].append(name)
        elif upper.endswith("B"):
            groups["B"].append(name)
        elif upper.endswith("C"):
            groups["C"].append(name)
        else:
            groups["N"].append(name)

    positions: dict[str, QPointF] = {}
    col_spacing = 320
    row_spacing = 110
    for col_idx, key in enumerate(["A", "B", "C", "N"]):
        group = sorted(groups[key])
        x = col_idx * col_spacing
        start_y = -(len(group) * row_spacing) / 2
        for row_idx, name in enumerate(group):
            positions[name] = QPointF(x, start_y + row_idx * row_spacing)
    return positions


def _grid_layout(names: list[str]) -> dict[str, QPointF]:
    """Square grid for non-three-phase circuits."""
    import math

    ordered = sorted(names)
    cols = max(1, int(math.ceil(math.sqrt(len(ordered)))))
    col_spacing = 220
    row_spacing = 140
    positions: dict[str, QPointF] = {}
    for idx, name in enumerate(ordered):
        col = idx % cols
        row = idx // cols
        positions[name] = QPointF(col * col_spacing, row * row_spacing)
    return positions


def _make_empty_project() -> AtpProject:
    """Build an empty AtpProject with a minimal skeleton so the serializer
    can append new BRANCH/SWITCH/SOURCE entries from the start.

    The resulting raw_lines are::

        BEGIN NEW DATA CASE
        /BRANCH
        BLANK BRANCH
        /SWITCH
        BLANK SWITCH
        /SOURCE
        BLANK SOURCE
        BLANK
        BEGIN NEW DATA CASE
        BLANK

    Section line numbers are wired to match this scaffold.
    """
    lines = [
        "BEGIN NEW DATA CASE",
        "/BRANCH",
        "BLANK BRANCH",
        "/SWITCH",
        "BLANK SWITCH",
        "/SOURCE",
        "BLANK SOURCE",
        "BLANK",
        "BEGIN NEW DATA CASE",
        "BLANK",
    ]
    project = AtpProject(
        file_path="",
        raw_lines=lines,
        header=HeaderInfo(raw_lines=[lines[0]]),
        tail_lines=lines[7:],
    )
    # Section boundaries: each header on line N, BLANK on line N+1,
    # end_line points at the header (last raw data line).
    project.sections["BRANCH"] = Section(
        name="BRANCH", raw_lines=[lines[1]], start_line=1, end_line=1,
    )
    project.sections["SWITCH"] = Section(
        name="SWITCH", raw_lines=[lines[3]], start_line=3, end_line=3,
    )
    project.sections["SOURCE"] = Section(
        name="SOURCE", raw_lines=[lines[5]], start_line=5, end_line=5,
    )
    return project
