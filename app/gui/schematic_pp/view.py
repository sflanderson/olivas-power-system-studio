"""
app.gui.schematic_pp.view — ``QGraphicsView`` com zoom, pan, drag-drop
e atalhos de teclado do pré-processador.

Atalhos
-------

* ``+`` / ``-`` / ``Ctrl+Wheel``: zoom in / out
* ``0`` (zero): reset de zoom
* ``R``: rotaciona seleção 90° no sentido anti-horário
* ``Shift+R``: rotaciona sentido horário
* ``E``: espelho horizontal (mirror X)
* ``Del`` / ``Backspace``: remove seleção
* ``W``: entra em modo *wire*
* ``V`` / ``Esc``: volta para modo *select* (Esc também cancela fio
  em progresso)
* ``Middle-drag`` ou ``Space+drag``: pan

Ferramentas
-----------

O view mantém um atributo :attr:`tool` com os valores
:attr:`TOOL_SELECT` (default) e :attr:`TOOL_WIRE`. Em modo
``TOOL_WIRE``, dois cliques colocam um :class:`PpWire` no
`PpProject`; o primeiro ponto define a ponta de origem, o
segundo (com snap para grid ou pino) fecha o fio. Um fio
*fantasma* acompanha o cursor entre os cliques.

Drag-drop
---------

``PpView`` aceita drops com mime-type
``application/x-atp-studio-pp-type`` gerados pela
:class:`PpPalette`. O payload é o ``type_code`` (``"R"``,
``"Vdc"``, etc.). O view emite
:attr:`component_dropped(type_code, scene_pos)` para que o
:class:`PpEditor` crie o componente via comando undoable.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QPointF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QContextMenuEvent,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPalette,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsView,
    QMenu,
)

from app.preprocessor.models import PpWire

from .items import ComponentItem, DataBlockItem, WireItem
from .scene import PpScene, snap


_ZOOM_STEP = 1.15
_ZOOM_MIN = 0.2
_ZOOM_MAX = 8.0

_PP_MIME_TYPE = "application/x-atp-studio-pp-type"

# v0.85: distância máxima (px de scene) para snap do mouse a um pino
# em modo TOOL_WIRE. Maior = mais "magnético", mas atrapalha posicionar
# em pontos vazios próximos. 8 px é suficiente para grid de 10 px.
_PIN_SNAP_DIST = 8.0


class PpView(QGraphicsView):
    """View com interação básica do editor."""

    TOOL_SELECT = "select"
    TOOL_WIRE = "wire"
    # v3.1.1 Sprint 1 — Push-pin mode (PTW Tutorial §Part 1 p.21-24).
    # Usuário seleciona tipo na paleta e clica sucessivamente no canvas
    # para colocar N instâncias do mesmo componente. Esc volta ao SELECT.
    TOOL_PIN = "pin"

    #: emitido quando o usuário clica duplo em um item (o editor abre
    #: o diálogo de propriedades correspondente).
    item_double_clicked = Signal(object)

    #: emitido quando o modo de ferramenta muda (para UI externa).
    tool_changed = Signal(str)

    #: emitido quando o usuário solta um tipo vindo da paleta em um
    #: ponto da cena. O editor cria o componente dentro de um
    #: comando undoable.
    component_dropped = Signal(str, QPointF)

    #: emitido quando dois cliques completam um fio em modo wire.
    wire_drawn = Signal(PpWire)

    #: v0.27.6: emitido quando o usuário clica direito numa área vazia
    #: do canvas E pede um componente do menu contextual. Argumentos:
    #: ``(type_code, scene_pos)``. O ``PpEditor`` recebe e cria via
    #: command undoable.
    request_add_component_at = Signal(str, QPointF)

    #: v0.86: emitido quando o usuário pede "Adicionar Datablock"
    #: no menu contextual de um componente. Argumento: o
    #: :class:`ComponentItem` host.
    request_add_datablock = Signal(object)

    #: v0.86: emitido quando o usuário pede "Editar..." em um
    #: datablock no menu contextual. Argumento: o ``DataBlockItem``.
    request_edit_datablock = Signal(object)

    #: v3.1.3 Sub-sprint A: emitido quando o usuário pede "Inserir
    #: Link Tag..." no menu contextual da área vazia. Argumento:
    #: scene_pos onde inserir.
    request_add_link_tag = Signal(QPointF)

    #: v3.1.3 Sub-sprint A: emitido quando o usuário pede "Inserir
    #: Legend Tag..." no menu contextual da área vazia. Argumentos:
    #: shape (Diamond/Hexagon/Circle/Rectangle), scene_pos.
    request_add_legend_tag = Signal(str, QPointF)

    #: v3.1.3 Sub-sprint C: emitido quando o usuário arrasta um tipo
    #: da paleta e solta sobre um WireItem existente. PTW Tutorial
    #: §Part 1 p.27 (auto-bus-node em série).
    #: Argumentos: ``(type_code, scene_pos, wire_item)``. Editor cria
    #: AddSeriesComponentCommand que quebra o wire + insere componente.
    component_dropped_on_wire = Signal(str, QPointF, object)

    def __init__(self, scene: PpScene, parent=None) -> None:
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setMouseTracking(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setAcceptDrops(True)

        # --- Correção de artefatos de drag (rastro) -----------------------
        # Default ``MinimalViewportUpdate`` confia no ``boundingRect()`` dos
        # items para invalidar regiões; um bounding rect apertado (comum
        # quando há labels, pen-width ≥ 1.5, selection halo) deixa pixels
        # "grudados" nas posições antigas durante o drag.
        #
        # ``BoundingRectViewportUpdate`` força Qt a invalidar a união dos
        # bounding rects sujos — ainda é barato (não repinta a viewport
        # inteira), mas é robusto a bounding rects ligeiramente apertados.
        #
        # Fallback defensivo: se ainda vier rastro em cenários específicos
        # (zoom extremo, rotation + mirror), troque para
        # ``FullViewportUpdate``. O custo é desprezível para cenas típicas
        # (< 200 items).
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)

        self._zoom: float = 1.0
        self._panning = False
        self._last_pan_pos: Optional[QPointF] = None

        # Tool state
        self._tool: str = self.TOOL_SELECT
        self._wire_start: Optional[QPointF] = None
        self._ghost_wire: Optional[QGraphicsPathItem] = None
        # v3.1.1 Sprint 1 — push-pin mode state
        self._pin_type_code: Optional[str] = None  # type to place in pin mode

    # ---- Tool -------------------------------------------------------------

    @property
    def tool(self) -> str:
        return self._tool

    def set_tool(self, tool: str) -> None:
        if tool not in (self.TOOL_SELECT, self.TOOL_WIRE, self.TOOL_PIN):
            raise ValueError(f"Unknown tool: {tool}")
        if tool == self._tool:
            return
        self._cancel_wire()
        # Leaving PIN mode clears the pin type
        if self._tool == self.TOOL_PIN and tool != self.TOOL_PIN:
            self._pin_type_code = None
        self._tool = tool
        if tool == self.TOOL_WIRE:
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(Qt.CrossCursor)
        elif tool == self.TOOL_PIN:
            # v3.1.1 Sprint 1: push-pin mode — disable rubberband, cross cursor
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(Qt.CrossCursor)
        else:
            self.setDragMode(QGraphicsView.RubberBandDrag)
            self.unsetCursor()
        self.tool_changed.emit(tool)

    def enter_pin_mode(self, type_code: str) -> None:
        """v3.1.1 Sprint 1: enter push-pin mode for given component type.

        Per PTW Tutorial §Part 1 p.21-24, after selecting a type from
        the palette, the cursor turns into a cross and successive clicks
        place instances of that component. Esc or pressing 'V' returns
        to TOOL_SELECT.
        """
        self._pin_type_code = type_code
        self.set_tool(self.TOOL_PIN)

    # ---- Zoom --------------------------------------------------------------

    def zoom_in(self) -> None:
        self._set_zoom(self._zoom * _ZOOM_STEP)

    def zoom_out(self) -> None:
        self._set_zoom(self._zoom / _ZOOM_STEP)

    def zoom_reset(self) -> None:
        self._set_zoom(1.0)

    def _set_zoom(self, value: float) -> None:
        value = max(_ZOOM_MIN, min(_ZOOM_MAX, value))
        factor = value / self._zoom
        self._zoom = value
        self.scale(factor, factor)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    # ---- Drag-drop ---------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(_PP_MIME_TYPE):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasFormat(_PP_MIME_TYPE):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        mime = event.mimeData()
        if mime.hasFormat(_PP_MIME_TYPE):
            raw = bytes(mime.data(_PP_MIME_TYPE)).decode("utf-8", errors="ignore")
            code = raw.strip()
            if code:
                # pos() é QPointF em Qt6.
                view_pt = event.position().toPoint()
                scene_pt = self.mapToScene(view_pt)
                snapped = QPointF(snap(scene_pt.x()), snap(scene_pt.y()))

                # v3.1.3 Sub-sprint C: detect drop on wire → auto-bus-node
                # em série (PTW Tutorial §Part 1 p.27)
                wire_item = self._find_wire_at(scene_pt)
                if wire_item is not None and code != "BUS":
                    # BUS dropping on wire is special-cased to avoid
                    # double-bus-insertion (BUS already has its own quick-add)
                    self.component_dropped_on_wire.emit(
                        code, snapped, wire_item,
                    )
                    event.acceptProposedAction()
                    return

                # Default path: drop em área vazia
                self.component_dropped.emit(code, snapped)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def _find_wire_at(self, scene_pt: QPointF, tolerance: float = 8.0):
        """Return WireItem near ``scene_pt`` (within ``tolerance`` px) or None.

        v3.5.1 (closes SKIPPED_BACKLOG A.3): usa **distância perpendicular**
        ao segmento L-routed do wire (em vez de bbox simples). Reduz falsos
        positivos em wires longos diagonais ou que cruzam regiões vazias
        do bounding rect.

        Algoritmo:
        1. Filtro inicial via bbox (fast path) — descarta wires longe
        2. Para cada candidato, calcula L-route (h-then-v ou v-then-h)
        3. Distância perpendicular ao segmento mais próximo
        4. Retorna o wire com menor distância ≤ tolerance

        Reference: SKIPPED_BACKLOG A.3 (registered v3.1.3, closed v3.5.1).
        """
        sc = self.scene()
        if sc is None:
            return None
        # Fast filter: bbox search around the point (with extra margin
        # to capture L-routed wires whose bbox exceeds segment area)
        from PySide6.QtCore import QRectF
        search_rect = QRectF(
            scene_pt.x() - tolerance * 4, scene_pt.y() - tolerance * 4,
            tolerance * 8, tolerance * 8,
        )
        candidates = [
            it for it in sc.items(search_rect)
            if isinstance(it, WireItem)
        ]
        if not candidates:
            return None

        best = None
        best_dist = float("inf")
        for w_item in candidates:
            wire = w_item.wire
            dist = _point_to_l_route_distance(
                scene_pt.x(), scene_pt.y(),
                wire.x1, wire.y1, wire.x2, wire.y2,
            )
            if dist < best_dist and dist <= tolerance:
                best = w_item
                best_dist = dist
        return best

    # ---- Mouse -------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._last_pan_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if self._tool == self.TOOL_WIRE and event.button() == Qt.LeftButton:
            scene_pt = self._snapped_scene_pos(event.position())
            if self._wire_start is None:
                self._wire_start = scene_pt
                self._update_ghost_wire(scene_pt)
            else:
                end = scene_pt
                if end != self._wire_start:
                    wire = PpWire(
                        x1=int(self._wire_start.x()),
                        y1=int(self._wire_start.y()),
                        x2=int(end.x()),
                        y2=int(end.y()),
                        label="",
                    )
                    self.wire_drawn.emit(wire)
                self._cancel_wire()
            event.accept()
            return

        # v3.1.1 Sprint 1 — Push-pin mode click places component
        if (self._tool == self.TOOL_PIN
                and event.button() == Qt.LeftButton
                and self._pin_type_code is not None):
            scene_pt = self.mapToScene(event.position().toPoint())
            snapped = QPointF(snap(scene_pt.x()), snap(scene_pt.y()))
            # Reuse existing signal — editor.py creates undoable command
            self.request_add_component_at.emit(self._pin_type_code, snapped)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning and self._last_pan_pos is not None:
            delta = event.position() - self._last_pan_pos
            self._last_pan_pos = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return

        if self._tool == self.TOOL_WIRE:
            # v0.85: cursor change quando hover sobre pino (affordance).
            raw_scene = self.mapToScene(event.position().toPoint())
            pin = self._closest_pin(raw_scene, _PIN_SNAP_DIST)
            if pin is not None:
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.setCursor(Qt.CrossCursor)
            # Atualiza ghost (já snapado ao pino se houver).
            if self._wire_start is not None:
                self._update_ghost_wire(self._snapped_scene_pos(event.position()))

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self._last_pan_pos = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.pos())
        if isinstance(item, (ComponentItem, WireItem)):
            self.item_double_clicked.emit(item)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    # ---- Context menu ---------------------------------------------------

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Right-click: menu contextual.

        * Sobre :class:`ComponentItem`: propriedades, rotacionar,
          espelhar, excluir.
        * Sobre :class:`WireItem`: apenas excluir.
        * Sobre área vazia (v0.27.6): menu de adição com submenu
          por categoria — replica a paleta lateral, permitindo
          fluxo "right-click → add" estilo ATPDraw, fundamental
          quando a paleta está oculta (modo compacto).

        Todas as ações passam pelo :attr:`PpScene.undo_stack` (quando
        anexo) para entrar no histórico de undo/redo.
        """
        scene = self.scene()
        item = self.itemAt(event.pos())
        # Garante que o item sob o cursor esteja selecionado para
        # que o comportamento seja previsível (o menu age sobre a
        # seleção corrente).
        if isinstance(item, (ComponentItem, WireItem, DataBlockItem)):
            if not item.isSelected():
                scene.clearSelection()
                item.setSelected(True)
            menu = self._build_context_menu(item, scene)
            if menu is None:
                super().contextMenuEvent(event)
                return
            menu.exec(event.globalPos())
            event.accept()
            return

        # v0.27.6: área vazia — menu de adição por categoria.
        empty_menu = self._build_empty_canvas_menu(event.pos())
        if empty_menu is not None:
            empty_menu.exec(event.globalPos())
            event.accept()
            return

        super().contextMenuEvent(event)

    def _build_context_menu(self, item, scene) -> Optional["QMenu"]:
        """Constrói e retorna o :class:`QMenu` apropriado para o item.

        Retorna ``None`` se o item não é reconhecido. A construção é
        separada da exibição para permitir teste (chamar o método,
        inspecionar as :class:`QAction` sem precisar de event loop
        que mostre o popup).
        """
        if not isinstance(item, (ComponentItem, WireItem, DataBlockItem)):
            return None
        menu = QMenu(self)
        if isinstance(item, ComponentItem):
            act_props = menu.addAction("Propriedades…")
            act_props.triggered.connect(
                lambda: self.item_double_clicked.emit(item)
            )
            menu.addSeparator()
            act_rot_ccw = menu.addAction("Rotacionar (R)")
            act_rot_ccw.triggered.connect(
                lambda: self._rotate_selection_undoable(scene, +1)
            )
            act_rot_cw = menu.addAction("Rotacionar inverso (Shift+R)")
            act_rot_cw.triggered.connect(
                lambda: self._rotate_selection_undoable(scene, -1)
            )
            act_mirror = menu.addAction("Espelhar (E)")
            act_mirror.triggered.connect(
                lambda: self._mirror_selection_undoable(scene)
            )
            menu.addSeparator()
            # v0.86: datablock (PTW Equipment)
            act_add_db = menu.addAction("📋 Adicionar datablock…")
            act_add_db.triggered.connect(
                lambda: self.request_add_datablock.emit(item)
            )
            menu.addSeparator()
        elif isinstance(item, DataBlockItem):
            act_edit_db = menu.addAction("Editar datablock…")
            act_edit_db.triggered.connect(
                lambda: self.request_edit_datablock.emit(item)
            )
            menu.addSeparator()
        act_delete = menu.addAction("Excluir (Del)")
        act_delete.triggered.connect(
            lambda: self._delete_selection_undoable(scene)
        )
        return menu

    def _build_empty_canvas_menu(
        self, view_pos
    ) -> Optional["QMenu"]:
        """
        v0.27.6: menu contextual em área vazia do canvas.

        Estrutura (ATPDraw-style):

        ::

            ▸ Adicionar componente
                ▸ passive
                    R · Resistor
                    L · Indutor
                    ...
                ▸ source
                    Vdc · Fonte de tensão DC
                    ...
                ▸ ...
            ───────────────
            Selecionar tudo (Ctrl+A)
            Modo Selecionar (V)
            Modo Fio (W)

        A posição da scene é capturada em ``view_pos`` (em
        coordenadas da view) e convertida para scene pos no
        snapping antes de emitir ``request_add_component_at``.
        """
        # Lazy import — evita ciclo (preprocessor.catalog não
        # depende de Qt e o view só precisa de catalog em
        # runtime de menu).
        from app.preprocessor import catalog

        snapped = self._snapped_scene_pos(QPointF(view_pos))
        menu = QMenu(self)

        # Submenu "Adicionar componente" agrupado por categoria.
        add_menu = menu.addMenu("Adicionar componente")
        last_cat: Optional[str] = None
        cat_menu = None
        for entry in catalog.all_entries():
            if not entry.atp_supported:
                continue
            if entry.category != last_cat:
                cat_menu = add_menu.addMenu(entry.category)
                last_cat = entry.category
            label = f"{entry.code}  ·  {entry.label_pt}"
            act = cat_menu.addAction(label)
            # Closure captura code + posição clicada
            act.triggered.connect(
                lambda checked=False, c=entry.code, p=snapped:
                self.request_add_component_at.emit(c, p)
            )

        # v3.1.3 Sub-sprint A — Inserir Tags (PTW Tutorial §Part 1 p.35-52)
        menu.addSeparator()
        act_link_tag = menu.addAction("🔗 Inserir Link Tag...")
        act_link_tag.triggered.connect(
            lambda checked=False, p=snapped: self.request_add_link_tag.emit(p)
        )
        legend_menu = menu.addMenu("⬥ Inserir Legend Tag")
        for shape, glyph in (
            ("Diamond", "◆"),
            ("Hexagon", "⬢"),
            ("Circle", "●"),
            ("Rectangle", "▭"),
        ):
            act = legend_menu.addAction(f"{glyph} {shape}")
            act.triggered.connect(
                lambda checked=False, s=shape, p=snapped:
                self.request_add_legend_tag.emit(s, p)
            )

        menu.addSeparator()
        act_select_all = menu.addAction("Selecionar tudo (Ctrl+A)")
        act_select_all.triggered.connect(self._select_all_items)

        menu.addSeparator()
        act_tool_select = menu.addAction("Modo Selecionar (V)")
        act_tool_select.triggered.connect(
            lambda: self.set_tool(self.TOOL_SELECT)
        )
        act_tool_wire = menu.addAction("Modo Fio (W)")
        act_tool_wire.triggered.connect(
            lambda: self.set_tool(self.TOOL_WIRE)
        )
        return menu

    def _select_all_items(self) -> None:
        """Seleciona todos os ComponentItem e WireItem do scene."""
        scene = self.scene()
        for it in scene.items():
            if isinstance(it, (ComponentItem, WireItem)):
                it.setSelected(True)

    # ---- Wire ghost --------------------------------------------------------

    def _snapped_scene_pos(self, view_pos) -> QPointF:
        """
        Snapping com 2 estágios (v0.85):

        1. **Pin snap** — se o cursor estiver dentro de
           ``_PIN_SNAP_DIST`` (8 px) de algum pino de componente,
           snap para a posição EXATA do pino (mesmo que não esteja
           no grid). Evita "ficar 1 pixel fora do pino" quando o
           pino está em coords não-grid.
        2. **Grid snap** — fallback para múltiplos de
           :data:`GRID_SIZE` (10 px).
        """
        pt = self.mapToScene(view_pos.toPoint() if hasattr(view_pos, "toPoint")
                             else view_pos)
        pin = self._closest_pin(pt, _PIN_SNAP_DIST)
        if pin is not None:
            return QPointF(int(round(pin.x())), int(round(pin.y())))
        return QPointF(snap(pt.x()), snap(pt.y()))

    def _closest_pin(self, scene_pt: QPointF,
                     max_dist: float) -> Optional[QPointF]:
        """
        v0.85: retorna a posição (em scene coords) do pino mais
        próximo a ``scene_pt`` dentro de ``max_dist`` (em px), ou
        ``None`` se nenhum pino estiver dentro do raio.

        Usado para snap-to-pin (ghost wire) e cursor change.
        """
        sc = self.scene()
        if sc is None:
            return None
        best: Optional[QPointF] = None
        best_d2 = max_dist * max_dist
        for ci in sc.component_items():
            try:
                pins = ci.pin_positions_scene()
            except Exception:
                continue
            for pin in pins:
                dx = pin.x() - scene_pt.x()
                dy = pin.y() - scene_pt.y()
                d2 = dx * dx + dy * dy
                if d2 < best_d2:
                    best_d2 = d2
                    best = pin
        return best

    def _update_ghost_wire(self, end: QPointF) -> None:
        if self._wire_start is None:
            return
        sc = self.scene()
        if self._ghost_wire is None:
            self._ghost_wire = QGraphicsPathItem()
            # Respeita o tema: pega a cor de highlight do QPalette
            # e aplica um alpha para o tracejado ficar sutil.
            hi = self.palette().color(QPalette.Highlight)
            if not hi.isValid() or hi.alpha() == 0:
                hi = QColor(0, 120, 215)
            hi.setAlpha(160)
            pen = QPen(hi, 1.5, Qt.DashLine)
            self._ghost_wire.setPen(pen)
            self._ghost_wire.setZValue(1000)
            sc.addItem(self._ghost_wire)
        # Reuse WireItem's L-route geometry.
        from PySide6.QtGui import QPainterPath
        path = QPainterPath(self._wire_start)
        if self._wire_start.x() == end.x() or self._wire_start.y() == end.y():
            path.lineTo(end)
        else:
            path.lineTo(QPointF(end.x(), self._wire_start.y()))
            path.lineTo(end)
        self._ghost_wire.setPath(path)

    def _cancel_wire(self) -> None:
        self._wire_start = None
        if self._ghost_wire is not None:
            sc = self.scene()
            if sc is not None:
                sc.removeItem(self._ghost_wire)
            self._ghost_wire = None

    # ---- Keyboard ---------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        mods = event.modifiers()
        scene = self.scene()
        assert isinstance(scene, PpScene)

        if key in (Qt.Key_Plus, Qt.Key_Equal):
            self.zoom_in()
            return
        if key == Qt.Key_Minus:
            self.zoom_out()
            return
        if key == Qt.Key_0:
            self.zoom_reset()
            return
        if key == Qt.Key_Escape:
            if self._tool == self.TOOL_WIRE and self._wire_start is not None:
                self._cancel_wire()
                return
            self.set_tool(self.TOOL_SELECT)
            return
        if key == Qt.Key_W:
            self.set_tool(self.TOOL_WIRE)
            return
        if key == Qt.Key_V:
            self.set_tool(self.TOOL_SELECT)
            return
        if key in (Qt.Key_Delete, Qt.Key_Backspace):
            self._delete_selection_undoable(scene)
            return
        if key == Qt.Key_R:
            # R = rotate_ccw (rotation += 1), Shift+R = rotate_cw
            # (rotation -= 1). Consistente com o binding pré-v0.21.6.
            direction = -1 if (mods & Qt.ShiftModifier) else +1
            self._rotate_selection_undoable(scene, direction)
            return
        if key == Qt.Key_E:
            self._mirror_selection_undoable(scene)
            return
        super().keyPressEvent(event)

    # ---- Helpers: atalhos de teclado que empilham comandos -----------

    def _rotate_selection_undoable(self, scene: PpScene, direction: int) -> None:
        items = scene.selected_components()
        if not items:
            return
        stack = getattr(scene, "undo_stack", None)
        if stack is None:
            # Fallback: mutação direta (compat).
            for item in items:
                if direction > 0:
                    item.rotate_ccw()
                else:
                    item.rotate_cw()
            return
        # Import local: commands.py importa items/scene que importam view
        # indiretamente através de editor.py.
        from .commands import RotateComponentCommand
        stack.beginMacro(
            f"Rotacionar seleção ({len(items)})"
        )
        try:
            for item in items:
                stack.push(RotateComponentCommand(scene, item.component, direction))
        finally:
            stack.endMacro()

    def _mirror_selection_undoable(self, scene: PpScene) -> None:
        items = scene.selected_components()
        if not items:
            return
        stack = getattr(scene, "undo_stack", None)
        if stack is None:
            for item in items:
                item.mirror_x()
            return
        from .commands import MirrorComponentCommand
        stack.beginMacro(f"Espelhar seleção ({len(items)})")
        try:
            for item in items:
                stack.push(MirrorComponentCommand(scene, item.component))
        finally:
            stack.endMacro()

    def _delete_selection_undoable(self, scene: PpScene) -> None:
        comp_items = scene.selected_components()
        wire_items = scene.selected_wires()
        if not comp_items and not wire_items:
            return
        stack = getattr(scene, "undo_stack", None)
        if stack is None:
            scene.remove_selected()
            return
        from .commands import RemoveSelectionCommand
        comps = [it.component for it in comp_items]
        wires = [it.wire for it in wire_items]
        stack.push(RemoveSelectionCommand(scene, comps, wires))


# ===========================================================================
# v3.5.1 (closes SKIPPED_BACKLOG A.3) — wire path geometry helpers
# ===========================================================================


def _point_to_segment_distance(
    px: float, py: float,
    ax: float, ay: float, bx: float, by: float,
) -> float:
    """Return perpendicular distance from point P to segment AB.

    Standard algorithm: project P onto line AB, clamp t to [0, 1],
    return distance from P to clamped projection.
    """
    dx = bx - ax
    dy = by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0:
        # Degenerate segment (zero length) — distance to point A
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    # Projection parameter t in [0, 1]
    t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    # Closest point on segment
    cx = ax + t * dx
    cy = ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def _point_to_l_route_distance(
    px: float, py: float,
    x1: float, y1: float, x2: float, y2: float,
) -> float:
    """Return perpendicular distance from P to a wire's L-routed path.

    L-route: WireItem.paint usa first horizontal, depois vertical
    (per :class:`WireItem` painterPath logic em items.py:1392-1454).
    Para wires não-orthogonais (x1≠x2 e y1≠y2), 2 segmentos:
    (x1,y1)→(x2,y1) horizontal, depois (x2,y1)→(x2,y2) vertical.

    Para wires already orthogonal (x1=x2 ou y1=y2), 1 segmento direto.

    Reference: WireItem.paint (items.py L-route logic).
    """
    if x1 == x2 or y1 == y2:
        # Direct segment — no L-routing needed
        return _point_to_segment_distance(px, py, x1, y1, x2, y2)
    # L-route: corner at (x2, y1)
    d1 = _point_to_segment_distance(px, py, x1, y1, x2, y1)
    d2 = _point_to_segment_distance(px, py, x2, y1, x2, y2)
    return min(d1, d2)
