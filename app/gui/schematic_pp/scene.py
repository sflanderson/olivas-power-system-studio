"""
app.gui.schematic_pp.scene — a ``QGraphicsScene`` that hosts the
preprocessor editor.

Responsibilities
----------------

* **Grid**: draw a dotted 10-px background grid (matches Qucs).
* **Snap**: round any incoming placement to the grid.
* **Model sync**: owns the backing :class:`PpProject`. The scene
  is always authoritative for the *current* edit state; the
  ``PpProject`` is the serializable snapshot.
* **Selection API**: exposes :meth:`selected_components` and
  :meth:`selected_wires` so the properties panel can query
  what's selected.

This class is Qt-only; it knows nothing about tools, palette,
or keyboard shortcuts — those live in :mod:`.view` and
:mod:`.editor`.
"""

from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene

from app.preprocessor.models import (
    PpComponent, PpDataBlock, PpLegendTag, PpLinkTag, PpProject, PpWire,
)
from app.preprocessor.symbols import get_renderer

from .items import ComponentItem, DataBlockItem, WireItem


GRID_SIZE = 10
_GRID_COLOR = QColor(210, 215, 220)
_GRID_MAJOR_COLOR = QColor(180, 185, 195)

# v0.85: connection markers (dots em pinos conectados + junctions)
_DOT_COLOR = QColor(30, 30, 30)         # mesmo tom dos wires
_DOT_RADIUS = 3.5                       # px (escala 1:1 do grid)
_JUNCTION_MIN_ENDPOINTS = 3             # 3+ endpoints num ponto = junção


def snap(value: float, grid: int = GRID_SIZE) -> int:
    """Rouda ``value`` ao múltiplo mais próximo de ``grid``."""
    return int(round(value / grid)) * grid


def snap_point(pt: QPointF, grid: int = GRID_SIZE) -> QPointF:
    return QPointF(snap(pt.x(), grid), snap(pt.y(), grid))


class PpScene(QGraphicsScene):
    """Scene editável do pré-processador."""

    #: emitido quando o conjunto de seleção muda (para bindings do
    #: painel de propriedades).
    selection_changed = Signal()

    #: emitido quando a lista de componentes/fios muda (adição,
    #: remoção, importação). Útil para barra de status.
    topology_changed = Signal()

    def __init__(self, project: Optional[PpProject] = None,
                 parent=None) -> None:
        super().__init__(parent)
        self._project: PpProject = project or PpProject()
        self._components_by_name: dict[str, ComponentItem] = {}
        self._wires: list[WireItem] = []
        # v0.86: datablocks indexados por id() do PpDataBlock para
        # permitir múltiplos no mesmo componente (raro mas válido).
        self._datablocks: list[DataBlockItem] = []
        # v0.87: cache de resultados de análises por bus_id, usado
        # para auto-popular datablocks via DataBlockBinder.
        # Lazy import dentro do __init__ evita ciclo
        # scene → binder → models é OK mas binder importa items
        # indiretamente; isolamos aqui.
        from .datablock_binder import DataBlockResultCache
        self.results_cache = DataBlockResultCache()

        # Slot opcional: quando o :class:`PpEditor` anexa seu
        # :class:`QUndoStack` aqui, interações *do item* (drag com
        # o mouse, hot-keys que nascem dentro do QGraphicsItem)
        # podem empilhar comandos sem precisar de uma referência
        # circular ao editor. Veja
        # :meth:`ComponentItem.mouseReleaseEvent`.
        self.undo_stack = None  # type: ignore[assignment]

        # scene grande o suficiente para circuitos típicos.
        self.setSceneRect(-100, -100, 2000, 1500)
        self.setBackgroundBrush(QColor(250, 250, 252))

        # Re-emite o sinal built-in do Qt em nome próprio (conveniência
        # para o editor sem precisar de lambda).
        self.selectionChanged.connect(self.selection_changed)  # type: ignore[attr-defined]

        self.load_project(self._project)

    # ---- Grid --------------------------------------------------------------

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawBackground(painter, rect)
        # grid de pontos a cada 10 px; linhas maiores a cada 50.
        left = int(rect.left()) - (int(rect.left()) % GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % GRID_SIZE)
        pen_minor = QPen(_GRID_COLOR, 0.5)
        pen_major = QPen(_GRID_MAJOR_COLOR, 0.7)

        painter.setPen(pen_minor)
        for x in range(left, int(rect.right()) + 1, GRID_SIZE):
            for y in range(top, int(rect.bottom()) + 1, GRID_SIZE):
                if x % (GRID_SIZE * 5) == 0 and y % (GRID_SIZE * 5) == 0:
                    painter.setPen(pen_major)
                    painter.drawPoint(x, y)
                    painter.setPen(pen_minor)
                else:
                    painter.drawPoint(x, y)

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        """
        v0.85: pinta dots de conexão sobre os items (foreground).

        Regras:
        * Endpoint de wire que coincide com um pino de componente
          → dot (deixa visível "este wire ESTÁ conectado").
        * 3+ endpoints de wires no mesmo ponto → junction (dot
          maior, convenção elétrica clássica).
        * 2 endpoints sozinhos (sem componente) → SEM dot (é
          continuação visual).
        """
        super().drawForeground(painter, rect)
        self._paint_connection_dots(painter)

    def _paint_connection_dots(self, painter: QPainter) -> None:
        """
        Detecta pontos que merecem marcador visual e pinta.

        Single-pass O(N_wires + N_pins) — barato para esquemáticos
        típicos. Sem clipping ao ``rect`` (custo desprezível).
        """
        if not self._wires and not self._components_by_name:
            return
        # Contagem de endpoints por (x,y) inteiro.
        endpoint_counts: dict[tuple[int, int], int] = {}
        for wi in self._wires:
            w = wi.wire
            k1 = (w.x1, w.y1)
            k2 = (w.x2, w.y2)
            endpoint_counts[k1] = endpoint_counts.get(k1, 0) + 1
            endpoint_counts[k2] = endpoint_counts.get(k2, 0) + 1
        # Set de pinos (scene coords, int).
        pin_set: set[tuple[int, int]] = set()
        for ci in self._components_by_name.values():
            try:
                pins = ci.pin_positions_scene()
            except Exception:
                continue
            for pin in pins:
                pin_set.add((int(round(pin.x())), int(round(pin.y()))))
        # Determinação dos pontos com dot.
        dot_points: set[tuple[int, int]] = set()
        for pt, count in endpoint_counts.items():
            if pt in pin_set:
                # Endpoint conectado a pino
                dot_points.add(pt)
            elif count >= _JUNCTION_MIN_ENDPOINTS:
                # Junção (3+ wires no mesmo ponto sem componente)
                dot_points.add(pt)
        if not dot_points:
            return
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(_DOT_COLOR)
        painter.setPen(Qt.NoPen)
        for x, y in dot_points:
            painter.drawEllipse(QPointF(x, y), _DOT_RADIUS, _DOT_RADIUS)
        painter.restore()

    # ---- Project I/O -------------------------------------------------------

    @property
    def project(self) -> PpProject:
        """O :class:`PpProject` que reflete o estado atual da cena."""
        return self._project

    def load_project(self, project: PpProject) -> None:
        """Troca o projeto (limpa cena e recarrega). Não altera GRID."""
        # limpar cena
        self.clear()
        self._components_by_name.clear()
        self._wires.clear()
        self._datablocks.clear()
        self._project = project
        for comp in project.components:
            self._add_component_item(comp)
        for wire in project.wires:
            self._add_wire_item(wire)
        # v0.86: datablocks resolvidos após componentes (precisam
        # do host pronto na cena).
        for db in project.datablocks:
            self._add_datablock_item(db)
        self.topology_changed.emit()

    def to_project(self) -> PpProject:
        """
        Garante que o :class:`PpProject` interno reflete a cena e o
        retorna. Útil antes de serializar.
        """
        for item in self._components_by_name.values():
            item.sync_to_model()
        for wire_item in self._wires:
            # wires são imutáveis na v0.21.3; nada a fazer.
            pass
        return self._project

    # ---- Add / remove -----------------------------------------------------

    def add_component(self, component: PpComponent) -> ComponentItem:
        """
        Adiciona ``component`` ao project *e* à cena. Atribui nome
        único se ``component.name`` estiver vazio ou colidir com
        outro já presente.

        GND usa nome ``*`` (convenção Qucs); permitimos múltiplos
        GNDs com o mesmo nome ``*`` — a chave interna vira
        sintética via id() para desambiguar.
        """
        needs_name = (
            component.name == ""
            or (component.name != "*"
                and component.name in self._components_by_name)
        )
        if needs_name:
            component.name = self._unique_name(component.type)
        self._project.components.append(component)
        item = self._add_component_item(component)
        self.topology_changed.emit()
        return item

    def add_wire(self, wire: PpWire) -> WireItem:
        self._project.wires.append(wire)
        item = self._add_wire_item(wire)
        self.topology_changed.emit()
        return item

    def add_datablock(self, db: PpDataBlock) -> Optional[DataBlockItem]:
        """
        v0.86: adiciona um :class:`PpDataBlock` ao project + cena.
        Retorna ``None`` se o componente host não existe (não há
        a quem o datablock se ancorar).
        """
        if db not in self._project.datablocks:
            self._project.datablocks.append(db)
        item = self._add_datablock_item(db)
        self.topology_changed.emit()
        return item

    def remove_component(self, item: ComponentItem) -> None:
        if item.component.name in self._components_by_name:
            del self._components_by_name[item.component.name]
        if item.component in self._project.components:
            self._project.components.remove(item.component)
        self.removeItem(item)
        self.topology_changed.emit()

    def remove_wire(self, item: WireItem) -> None:
        if item in self._wires:
            self._wires.remove(item)
        if item.wire in self._project.wires:
            self._project.wires.remove(item.wire)
        self.removeItem(item)
        self.topology_changed.emit()

    def remove_datablock(self, item: DataBlockItem) -> None:
        """v0.86: remove um datablock da cena + project."""
        if item in self._datablocks:
            self._datablocks.remove(item)
        if item.datablock in self._project.datablocks:
            self._project.datablocks.remove(item.datablock)
        # Item é children do host — removeItem(item) cuida disso.
        self.removeItem(item)
        self.topology_changed.emit()

    # ------------------------------------------------------------------
    # v3.1.3 Sub-sprint A — Tag management (PTW Tutorial §Part 1 p.35-52)
    # ------------------------------------------------------------------

    def add_link_tag(self, tag: PpLinkTag) -> "LinkTagGraphicsItem":
        """Add a Link Tag to project + canvas.

        Per PTW Tutorial §Part 1 p.35-42.
        """
        from .tag_items import LinkTagGraphicsItem
        if tag not in self._project.link_tags:
            self._project.link_tags.append(tag)
        item = LinkTagGraphicsItem(tag)
        self.addItem(item)
        # Attach to scene tracking dict (for find_link_tag_item)
        if not hasattr(self, "_link_tag_items"):
            self._link_tag_items = {}
        self._link_tag_items[id(tag)] = item
        # Reemit link_clicked from the scene level for Editor/MainWindow wiring
        item.link_clicked.connect(self._on_link_tag_clicked)
        self.topology_changed.emit()
        return item

    def remove_link_tag(self, tag: PpLinkTag) -> None:
        """Remove a Link Tag from project + canvas."""
        if tag in self._project.link_tags:
            self._project.link_tags.remove(tag)
        if hasattr(self, "_link_tag_items"):
            item = self._link_tag_items.pop(id(tag), None)
            if item is not None:
                self.removeItem(item)
        self.topology_changed.emit()

    def add_legend_tag(self, tag: PpLegendTag) -> "LegendTagGraphicsItem":
        """Add a Legend Tag to project + canvas.

        Per PTW Tutorial §Part 1 p.43-52.
        """
        from .tag_items import LegendTagGraphicsItem
        if tag not in self._project.legend_tags:
            self._project.legend_tags.append(tag)
        item = LegendTagGraphicsItem(tag)
        self.addItem(item)
        if not hasattr(self, "_legend_tag_items"):
            self._legend_tag_items = {}
        self._legend_tag_items[id(tag)] = item
        self.topology_changed.emit()
        return item

    def remove_legend_tag(self, tag: PpLegendTag) -> None:
        """Remove a Legend Tag from project + canvas."""
        if tag in self._project.legend_tags:
            self._project.legend_tags.remove(tag)
        if hasattr(self, "_legend_tag_items"):
            item = self._legend_tag_items.pop(id(tag), None)
            if item is not None:
                self.removeItem(item)
        self.topology_changed.emit()

    #: Emitido quando o usuário clica em um LinkTagGraphicsItem.
    #: O argumento é o ``target`` URI (oneline:/tcc:/report:/pdf:).
    #: O :class:`PpEditor` propaga adiante para o :class:`MainWindow`,
    #: que abre o documento referenciado.
    link_tag_clicked = Signal(str)

    def _on_link_tag_clicked(self, target: str) -> None:
        """Re-emit link click at scene level."""
        self.link_tag_clicked.emit(target)

    def remove_selected(self) -> int:
        """Remove todos os itens selecionados. Retorna quantidade."""
        n = 0
        for it in list(self.selectedItems()):
            if isinstance(it, ComponentItem):
                self.remove_component(it)
                n += 1
            elif isinstance(it, WireItem):
                self.remove_wire(it)
                n += 1
            elif isinstance(it, DataBlockItem):
                self.remove_datablock(it)
                n += 1
        return n

    # ---- Queries -----------------------------------------------------------

    def component_items(self) -> list[ComponentItem]:
        return list(self._components_by_name.values())

    def wire_items(self) -> list[WireItem]:
        return list(self._wires)

    def datablock_items(self) -> list[DataBlockItem]:
        """v0.86: lista de DataBlockItems atualmente na cena."""
        return list(self._datablocks)

    def find_datablock_item(self, db: PpDataBlock) -> Optional[DataBlockItem]:
        """v0.86: localiza o DataBlockItem que envolve ``db``."""
        for item in self._datablocks:
            if item.datablock is db:
                return item
        return None

    def selected_components(self) -> list[ComponentItem]:
        return [it for it in self.selectedItems()
                if isinstance(it, ComponentItem)]

    def selected_wires(self) -> list[WireItem]:
        return [it for it in self.selectedItems()
                if isinstance(it, WireItem)]

    def find_component_item(self, comp: PpComponent) -> Optional[ComponentItem]:
        """Retorna o :class:`ComponentItem` que envolve ``comp`` (ou ``None``).

        Compara por identidade (``is``) — não por nome — porque durante
        undo/redo podemos ter o mesmo PpComponent com rename aplicado.
        """
        for item in self._components_by_name.values():
            if item.component is comp:
                return item
        return None

    def find_wire_item(self, wire: PpWire) -> Optional[WireItem]:
        """Retorna o :class:`WireItem` que envolve ``wire`` (ou ``None``)."""
        for item in self._wires:
            if item.wire is wire:
                return item
        return None

    # ---- Helpers internos --------------------------------------------------

    def _add_component_item(self, comp: PpComponent) -> ComponentItem:
        item = ComponentItem(comp)
        self.addItem(item)
        key = comp.name if comp.name != "*" else f"*{id(comp)}"
        self._components_by_name[key] = item
        return item

    def _add_wire_item(self, wire: PpWire) -> WireItem:
        item = WireItem(wire)
        self.addItem(item)
        self._wires.append(item)
        return item

    def _add_datablock_item(
        self, db: PpDataBlock,
    ) -> Optional[DataBlockItem]:
        """v0.86: cria DataBlockItem se houver host válido."""
        host = self._find_component_by_name(db.component_name)
        if host is None:
            return None
        # DataBlockItem se anexa ao host como QGraphicsItem child;
        # não chamamos addItem (já está na cena via parent).
        item = DataBlockItem(db, host)
        self._datablocks.append(item)
        return item

    def _find_component_by_name(self, name: str) -> Optional[ComponentItem]:
        """Lookup por nome (suficiente para datablock host).

        Para GND (nome = "*"), retorna o primeiro encontrado —
        datablocks em GND com múltiplas instâncias podem ficar
        ambíguos (limitação aceita na v0.86).
        """
        if not name:
            return None
        if name in self._components_by_name:
            return self._components_by_name[name]
        # Fallback: iterar (cobre GND "*" e nomes não-indexados)
        for ci in self._components_by_name.values():
            if ci.component.name == name:
                return ci
        return None

    def _unique_name(self, type_code: str) -> str:
        """Gera um nome único baseado no tipo (R1, R2, ...)."""
        prefix = type_code if type_code.isalpha() else "X"
        i = 1
        while True:
            candidate = f"{prefix}{i}"
            if candidate not in self._components_by_name:
                return candidate
            i += 1
