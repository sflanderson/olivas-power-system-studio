"""
app.gui.schematic_pp.items — QGraphicsItem adapters that let the
headless ``SymbolRenderer`` family (see ``app.preprocessor.symbols``)
live inside a Qt scene.

Two kinds of items:

* :class:`ComponentItem` — draggable, selectable, rotatable,
  mirrorable. Wraps a :class:`app.preprocessor.models.PpComponent`
  and a :class:`app.preprocessor.symbols.SymbolRenderer`. The
  PpComponent is the source of truth for persistence (.sch); the
  QGraphicsItem is a *view* on it. Two-way sync happens via
  :meth:`ComponentItem.sync_from_model` (model → item) and
  :meth:`ComponentItem.sync_to_model` (item → model, called after
  drag/rotate/mirror).

* :class:`WireItem` — L-routed polyline between two scene points.
  Display-only in v0.21.3; wire editing is a v0.21.4 problem.

Coordinate conventions
----------------------

The scene uses the *same* integer pixel coordinates as a Qucs
``.sch`` file: 10 px grid, positive Y down, origin at top-left of
the canvas. This avoids any transform gymnastics between the
file format and the editor.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QStyleOptionGraphicsItem,
    QWidget,
)

from app.preprocessor.models import PpComponent, PpDataBlock, PpWire
from app.preprocessor.symbols import SymbolRenderer, get_renderer


# ---------------------------------------------------------------------------
# Estilo de seleção / hover
# ---------------------------------------------------------------------------


_SELECT_COLOR = QColor(0, 120, 215)
_SELECT_FILL = QColor(0, 120, 215, 28)   # Halo azul translúcido, leve.
_HOVER_COLOR = QColor(80, 160, 235)
_WIRE_COLOR = QColor(30, 30, 30)
_WIRE_SEL_COLOR = QColor(0, 120, 215)
_LABEL_COLOR = QColor(30, 30, 30)        # Igual ao traço do símbolo (harmonia).

# Label do componente ("R1", "L1", etc.) renderizado sob o símbolo.
# Mantido em módulo para permitir tuning global (fonte, tamanho) e ao mesmo
# tempo para poder usar ``QFontMetricsF`` no cálculo do ``boundingRect``.
#
# Fonte: preferimos "Segoe UI" (Windows 10/11 system font) quando disponível,
# senão fallback para "Sans" (Qt resolve para DejaVu/FreeSans/etc em Linux,
# Helvetica em macOS). Tamanho 8pt é o sweet-spot entre legível em 100% zoom
# e não poluir o canvas com texto grande.
_LABEL_FONT = QFont("Segoe UI, Sans", 8)
_LABEL_FONT.setStyleStrategy(QFont.PreferAntialias)

# Pen width máxima desenhada por qualquer renderer (_PEN_NORMAL=1.5,
# _PEN_THICK=2.0 em symbols.py). Meia-largura é o *halo* que sai fora
# das coordenadas geométricas da linha por causa do cap/join.
_MAX_PEN_HALF = 1.5

# Margem extra de segurança (halo de seleção + antialiasing residual).
_SELECTION_MARGIN = 4.0

# Raio do canto arredondado do halo de seleção (pixels de scene).
_SELECT_CORNER_RADIUS = 4.0

# v1.7.2: Pin dot rendering — visual hint de "onde clicar para
# iniciar/conectar uma wire". Endereça issue #1 do user gate v2.0.0
# (simbologia confusa, não fica claro onde conectar linhas).
_PIN_DOT_COLOR = QColor(80, 80, 80)              # Cinza escuro (default)
_PIN_DOT_COLOR_SELECTED = QColor(0, 120, 215)    # Azul (selected)
_PIN_DOT_COLOR_HOVER = QColor(46, 125, 50)       # Verde (hover, futuro)
_PIN_DOT_RADIUS = 2.5                            # Radius em pixels de scene
_PIN_DOT_FILL = QColor(255, 255, 255, 230)       # Branco (highlight do furo)


# ---------------------------------------------------------------------------
# ComponentItem
# ---------------------------------------------------------------------------


class ComponentItem(QGraphicsObject):
    """
    Adapter: exibe um ``PpComponent`` no ``QGraphicsScene``, delegando
    o desenho para o ``SymbolRenderer`` correspondente.
    """

    Type = QGraphicsItem.UserType + 101

    def __init__(self, component: PpComponent,
                 renderer: Optional[SymbolRenderer] = None,
                 parent: Optional[QGraphicsItem] = None) -> None:
        super().__init__(parent)
        self.component = component
        if renderer is None:
            renderer = get_renderer(component.type)
        if renderer is None:
            # fallback genérico: pinta um retângulo com o tipo dentro.
            renderer = _FallbackRenderer(component.type)
        self.renderer: SymbolRenderer = renderer

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        # Posição do componente no início do drag; usado pelo
        # mouseReleaseEvent para empilhar um MoveComponentCommand
        # no :class:`QUndoStack` da cena (quando o editor tiver
        # conectado um).
        self._press_pos: Optional[tuple[int, int]] = None

        # v0.84: wire anchoring.
        # Lista de (wire_item, endpoint_idx, pin_idx) capturada no
        # mousePress: identifica quais fios estão "fixados" a este
        # componente naquele instante. Durante o drag, cada
        # endpoint segue o pino correspondente (translation +
        # rotation/mirror via mapToScene). No release, um único
        # MoveComponentCommand undoable carrega tanto o componente
        # quanto os deltas dos endpoints.
        self._anchor_snapshot: list[tuple["WireItem", int, int]] = []
        # Snapshot dos endpoints (PpWire.x1/y1/x2/y2) ANTES do drag
        # — usado para construir o command no release com os
        # valores antigos para undo.
        self._anchor_before_endpoints: list[
            tuple["WireItem", int, int, int]
        ] = []

        # v0.92.1: handles de redimensionamento (Bus PTW).
        # Criados sob demanda em ``_install_resize_handles_if_supported``.
        # Lista de (BusResizeHandle, "left"|"right").
        self._resize_handles: list[tuple["BusResizeHandle", str]] = []
        self._install_resize_handles_if_supported()

        # v1.1.0: anotação Online (single-line diagram online mode).
        # None = não há anotação visível. Setada via
        # set_online_annotation() pelo OnlineOverlayManager.
        self._online_annotation = None  # type: Optional["OnlineAnnotation"]

        self.sync_from_model()

    # ---- v1.1.0: Online annotation API ------------------------------------

    def set_online_annotation(self, ann) -> None:  # OnlineAnnotation | None
        """
        Anexa (ou limpa) uma ``OnlineAnnotation`` ao componente.

        Quando setada (não-None), o ``paint()`` desenha um badge
        ao lado direito do símbolo com as linhas da anotação,
        colorido conforme severidade ('info'/'ok'/'warn'/
        'violation'). Quando ``None``, nenhuma annotation é
        desenhada.

        Chama ``prepareGeometryChange()`` antes de mudar para
        invalidar o boundingRect anterior — caso contrário Qt
        deixa pixels do badge antigo na cena.
        """
        if self._online_annotation is ann:
            return
        self.prepareGeometryChange()
        self._online_annotation = ann
        self.update()

    def online_annotation(self):
        """Retorna a anotação atual ou None."""
        return self._online_annotation

    # ---- Qt overrides ------------------------------------------------------

    def type(self) -> int:  # noqa: A003 (shadowing builtin by Qt convention)
        return ComponentItem.Type

    def _label_text(self) -> str:
        """Texto do label ("R1", "L1") — vazio se invisível ou ausente."""
        c = self.component
        if not c.visible or not c.name or c.name == "*":
            return ""
        return c.name

    def _label_rect(self) -> QRectF:
        """
        Rect do label em coords locais. Retorna rect vazio se o label
        não deve ser desenhado.

        A largura é medida com ``QFontMetricsF`` — crucial para que o
        ``boundingRect`` cubra labels longos ("VCB3", "MOSFET", "GND").
        Sem isso, ``MinimalViewportUpdate`` deixa pixels do label
        grudados em posições antigas durante o drag.
        """
        text = self._label_text()
        if not text:
            return QRectF()
        metrics = QFontMetricsF(_LABEL_FONT)
        tight = metrics.tightBoundingRect(text)
        # Linha baseline fica em ``br.bottom() + 10``; tightBoundingRect
        # retorna rect relativo à origem (ascent acima, descent abaixo).
        br = self.renderer.bounding_rect()
        baseline_y = br.bottom() + 10
        left = br.left()
        # tight.top() é negativo (acima da baseline), tight.bottom() positivo.
        return QRectF(
            left + tight.left(),
            baseline_y + tight.top(),
            tight.width(),
            tight.height(),
        ).normalized()

    def _online_badge_rect(self) -> QRectF:
        """
        v1.1.0: Rect do badge Online (PTW-style) ao lado direito
        do símbolo. Vazio se não há anotação anexada.

        O badge é desenhado verticalmente: uma linha por elemento
        de ``ann.lines``. A largura é calculada com
        ``QFontMetricsF`` para acomodar a maior linha.
        """
        ann = self._online_annotation
        if ann is None:
            return QRectF()
        font = QFont("Segoe UI, Sans", 8, QFont.Bold)
        metrics = QFontMetricsF(font)
        max_w = 0.0
        for line in ann.lines:
            tw = metrics.horizontalAdvance(line)
            if tw > max_w:
                max_w = tw
        line_h = metrics.height()
        n = max(1, len(ann.lines))
        # Padding interno do badge: 4px horizontal, 2px vertical
        pad_x, pad_y = 4.0, 2.0
        w = max_w + 2 * pad_x
        h = line_h * n + 2 * pad_y
        # Posicionamento: à direita do símbolo, com 4px de gap
        symbol = self.renderer.bounding_rect()
        x = symbol.right() + 4.0
        # Centralizado verticalmente no símbolo
        y = -h / 2.0
        return QRectF(x, y, w, h)

    def boundingRect(self) -> QRectF:
        """
        Bounding rect que DEVE conter tudo que ``paint()`` desenha.

        Inclui, em ordem:

        1. ``renderer.bounding_rect()`` — o símbolo em si.
        2. Pen halo (``_MAX_PEN_HALF``) — metade da pen width que sai
           fora do path geométrico por conta de ``RoundCap`` /
           ``RoundJoin``.
        3. Selection halo (``_SELECTION_MARGIN``) — a pen de 1 px do
           retângulo pontilhado + folga anti-aliasing.
        4. Label rect — medido com ``QFontMetricsF`` (largura real do
           texto, não uma constante).
        5. v1.1.0: Online annotation badge se ``_online_annotation``
           não for None.

        Qt usa este rect para:

        * Detecção de colisão (hit-test).
        * Invalidação de região durante o repaint (se apertar o rect,
          sobram pixels "sujos" quando o item se move — exatamente o
          bug de rastro de drag).
        * Clipping do painter (QPainter recusa desenhos fora do rect).
        """
        symbol = self.renderer.bounding_rect()
        halo = _MAX_PEN_HALF + _SELECTION_MARGIN
        expanded = symbol.adjusted(-halo, -halo, halo, halo)
        label = self._label_rect()
        if label.isValid() and not label.isEmpty():
            expanded = expanded.united(label)
        # v1.1.0: incluir badge Online se houver
        badge = self._online_badge_rect()
        if not badge.isEmpty():
            expanded = expanded.united(badge)
        # Pequena folga adicional para o antialiasing pintar fora do
        # inteiro (Qt arredonda subpixels).
        return expanded.adjusted(-1.0, -1.0, 1.0, 1.0)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem,
              widget: Optional[QWidget] = None) -> None:
        # 1. Halo de seleção PRIMEIRO (fundo) — translúcido, arredondado.
        #    Desenhar antes do símbolo faz o halo funcionar como "glow"
        #    em vez de overlay que tingiria o símbolo de azul.
        if self.isSelected():
            symbol = self.renderer.bounding_rect()
            halo = symbol.adjusted(
                -_SELECTION_MARGIN, -_SELECTION_MARGIN,
                _SELECTION_MARGIN, _SELECTION_MARGIN,
            )
            painter.save()
            painter.setPen(QPen(_SELECT_COLOR, 1.0))
            painter.setBrush(QBrush(_SELECT_FILL))
            painter.drawRoundedRect(
                halo, _SELECT_CORNER_RADIUS, _SELECT_CORNER_RADIUS,
            )
            painter.restore()
        # 2. Símbolo em si (zigzag, bumps, círculo de fonte, etc.).
        self.renderer.paint(painter)
        # 3. Label abaixo do símbolo ("R1", "L1", ...).
        text = self._label_text()
        if text:
            painter.save()
            painter.setPen(QPen(_LABEL_COLOR, 1.0))
            painter.setFont(_LABEL_FONT)
            br = self.renderer.bounding_rect()
            label_y = br.bottom() + 10
            painter.drawText(QPointF(br.left(), label_y), text)
            painter.restore()
        # 4. v1.1.0: Online annotation badge — ao lado direito
        #    do símbolo. Estilo PTW: caixa colorida com texto.
        ann = self._online_annotation
        if ann is not None:
            self._paint_online_badge(painter, ann)
        # 5. v1.7.1: Inactive overlay (componente desativado) —
        #    overlay translúcido cinza por cima do símbolo. Activado
        #    via component.is_active=False. Não afeta hit-testing.
        comp = getattr(self, "component", None)
        if comp is not None and getattr(comp, "is_active", True) is False:
            self._paint_inactive_overlay(painter)
        # 6. v1.7.2: Pin dots — círculos pequenos nas posições dos
        #    pinos para sinalizar visualmente "onde conectar wires"
        #    (endereça issue #1 user gate v2.0.0). Cor varia conforme
        #    seleção. Sempre por cima do símbolo (último a desenhar).
        # v1.7.3: cores por categoria (power/signal/trip) +
        #    pin labels visíveis quando selecionado.
        try:
            self._paint_pin_dots(painter)
            self._paint_pin_labels(painter)
        except Exception:
            # Anti-crash defensivo (nunca deve impedir o paint
            # principal de funcionar)
            pass

    def _paint_online_badge(self, painter: QPainter, ann) -> None:
        """
        v1.1.0: desenha o badge Online (estilo PTW) ao lado direito.

        Cores conforme severidade ('info'/'ok'/'warn'/'violation').
        """
        from app.gui.schematic_pp.online_overlay import severity_colors

        rect = self._online_badge_rect()
        if rect.isEmpty():
            return
        text_color, bg_color = severity_colors(ann.severity)
        # Borda da mesma cor do texto, mais suave (alpha)
        border_color = QColor(text_color)
        border_color.setAlpha(180)

        painter.save()
        # Fundo
        painter.setPen(QPen(border_color, 1.2))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 3.0, 3.0)
        # Texto
        font = QFont("Segoe UI, Sans", 8, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(text_color, 1.0))
        metrics = QFontMetricsF(font)
        line_h = metrics.height()
        pad_x, pad_y = 4.0, 2.0
        ascent = metrics.ascent()
        # Desenha cada linha empilhada verticalmente
        for i, line in enumerate(ann.lines):
            x = rect.left() + pad_x
            y = rect.top() + pad_y + ascent + i * line_h
            painter.drawText(QPointF(x, y), line)
        painter.restore()

    def _paint_pin_dots(self, painter: QPainter) -> None:
        """
        v1.7.2: desenha um círculo pequeno em cada pin position do
        renderer. Endereça issue #1 do user gate v2.0.0 (simbologia
        confusa — "não é possível identificar onde conectar wires").

        v1.7.3: cores **categorizadas por função** (power/signal/
        trip/unknown) baseado em ``pin_categories.pin_category``:

        * Power (corrente principal): azul
        * Signal (medição): verde
        * Trip (proteção): laranja
        * Unknown (default): cinza

        Categorização lê name+label do spec via
        ``_pin_specs_aligned()``.

        Selected: dot maior + ring azul ao redor.

        Posições vêm de ``renderer.pin_positions()`` em coordenadas
        locais ao item (não scene). Painter já está no espaço local.
        """
        from app.gui.schematic_pp.pin_categories import (
            color_for_category,
        )
        try:
            pin_positions = self.renderer.pin_positions()
        except Exception:
            return
        if not pin_positions:
            return

        pin_specs = self._pin_specs_aligned()
        is_selected = self.isSelected()
        radius = _PIN_DOT_RADIUS * (1.4 if is_selected else 1.0)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        for i, p in enumerate(pin_positions):
            x = p.x() if hasattr(p, "x") else float(p[0])
            y = p.y() if hasattr(p, "y") else float(p[1])
            # Categoria → cor da borda (v1.7.3)
            if i < len(pin_specs):
                _, _, cat = pin_specs[i]
                edge = color_for_category(cat)
            else:
                edge = _PIN_DOT_COLOR
            # Selected: ring azul extra ao redor (v1.7.3)
            if is_selected:
                ring_pen = QPen(_PIN_DOT_COLOR_SELECTED, 1.0)
                painter.setPen(ring_pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(
                    QPointF(x, y), radius + 1.5, radius + 1.5,
                )
            # Dot principal — cor por categoria
            painter.setPen(QPen(edge, 1.2))
            painter.setBrush(QBrush(_PIN_DOT_FILL))
            painter.drawEllipse(
                QPointF(x, y), radius, radius,
            )
        painter.restore()

    def _pin_specs_aligned(self):
        """
        v1.7.3: retorna lista paralela a renderer.pin_positions()
        com tuplas (name, label, category).

        Anti-perda: lê do registry ComponentSpec quando disponível;
        fallback para names genéricos se spec ausente.
        """
        from app.gui.schematic_pp.pin_categories import (
            pin_category, PinCategory,
        )
        try:
            pin_positions = self.renderer.pin_positions()
        except Exception:
            return []
        if not pin_positions:
            return []

        spec_pins = []
        try:
            from app.preprocessor.spec import get_default_registry
            spec = get_default_registry().get(self.component.type)
            if spec is not None:
                spec_pins = list(spec.pins)
        except Exception:
            spec_pins = []

        result = []
        for i, _ in enumerate(pin_positions):
            if i < len(spec_pins):
                ps = spec_pins[i]
                name = getattr(ps, "name", f"pin{i+1}")
                label = getattr(ps, "label", "") or ""
            else:
                name = f"pin{i+1}"
                label = ""
            cat = pin_category(name, label)
            result.append((name, label, cat))
        return result

    def _paint_pin_labels(self, painter: QPainter) -> None:
        """
        v1.7.3: desenha labels (name) ao lado de cada pin position
        APENAS quando o componente está selecionado.

        Endereça pedido user gate v2.0.1: "ainda não é possível
        identificar qual o pino correto" — agora ao selecionar um
        componente o usuário vê o nome de cada pino diretamente
        no canvas.

        Posicionamento: offset 6px na direção oposta ao centro
        do bounding rect (evita sobreposição com símbolo).
        """
        if not self.isSelected():
            return
        try:
            pin_positions = self.renderer.pin_positions()
        except Exception:
            return
        if not pin_positions:
            return
        pin_specs = self._pin_specs_aligned()
        if not pin_specs:
            return

        try:
            br = self.renderer.bounding_rect()
            cx = br.center().x()
            cy = br.center().y()
        except Exception:
            cx = cy = 0.0

        font = QFont(_LABEL_FONT)
        font.setPointSize(7)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setFont(font)
        painter.setPen(QPen(_PIN_DOT_COLOR_SELECTED, 1.0))
        for i, p in enumerate(pin_positions):
            if i >= len(pin_specs):
                continue
            name, _label, _cat = pin_specs[i]
            if not name:
                continue
            x = p.x() if hasattr(p, "x") else float(p[0])
            y = p.y() if hasattr(p, "y") else float(p[1])
            dx = 6.0 if x >= cx else -6.0
            dy = -2.0 if y < cy else 8.0
            painter.drawText(QPointF(x + dx, y + dy), name)
        painter.restore()

    def _paint_inactive_overlay(self, painter: QPainter) -> None:
        """
        v1.7.1: desenha overlay cinza translúcido sobre o símbolo
        para indicar componente desativado/out-of-service.

        Usa a bounding rect do renderer (não interfere com label/
        badge). Anti-perda: método novo, não modifica código
        existente além do hook em paint().
        """
        try:
            from PySide6.QtCore import Qt
            br = self.renderer.bounding_rect()
            painter.save()
            painter.setPen(Qt.NoPen)
            # Cinza translúcido — paridade PTW Out of Service
            painter.setBrush(QBrush(QColor(160, 160, 160, 130)))
            painter.drawRect(br)
            painter.restore()
        except Exception:
            # Anti-crash defensivo: se algo der errado no overlay,
            # não impede o resto do paint
            pass

    def itemChange(self, change, value):
        # Apenas mantemos o model sincronizado quando a posição muda
        # *e* estamos numa cena viva. Isso garante que drag-and-drop
        # atualiza o PpComponent sem precisar de save explícito.
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            pos = self.pos()
            self.component.x = int(round(pos.x()))
            self.component.y = int(round(pos.y()))
            # v0.84: wires anexados seguem o componente.
            # ``pin_positions_scene()`` já reflete a nova pos via
            # ``mapToScene``; basta reposicionar os endpoints
            # capturados no mousePress.
            if self._anchor_snapshot:
                self._sync_anchored_wires()
        # v0.92.1: handles de redimensionamento seguem o estado
        # de seleção do componente (Bus PTW).
        if (
            change == QGraphicsItem.ItemSelectedHasChanged
            and self._resize_handles
        ):
            for handle, _side in self._resize_handles:
                handle.setVisible(bool(value))
        return super().itemChange(change, value)

    # ---- Mouse: drag → MoveComponentCommand --------------------------------

    def mousePressEvent(self, event):  # type: ignore[override]
        # Memoriza a posição de início do drag para comparar no
        # release. Se nada mudar, nenhum comando é empilhado.
        self._press_pos = (self.component.x, self.component.y)
        # v0.84: snapshot dos fios fixados a pinos deste componente.
        self._anchor_snapshot = self._capture_attached_anchors()
        # Snapshot dos endpoints atuais para construir o undo no
        # release sem precisar consultar a cena novamente (as
        # coords podem ter mudado durante o drag).
        self._anchor_before_endpoints = [
            (
                wire_item,
                endpoint_idx,
                wire_item.wire.x1 if endpoint_idx == 1 else wire_item.wire.x2,
                wire_item.wire.y1 if endpoint_idx == 1 else wire_item.wire.y2,
            )
            for (wire_item, endpoint_idx, _pin_idx) in self._anchor_snapshot
        ]
        # v1.7.2: Multi-drag fix — quando vários componentes estão
        # selected, Qt move TODOS juntos via selection-driven movement.
        # Cada item recebe ItemPositionHasChanged, que chama
        # _sync_anchored_wires(). Mas esse helper só funciona se o
        # item tiver _anchor_snapshot capturado. Como mousePressEvent
        # é chamado APENAS no item clicado, os demais ficam com
        # snapshot vazio → wires não acompanham. Fix: propagar
        # capture para todos os selected ComponentItems.
        scene = self.scene()
        if scene is not None and self.isSelected():
            for item in scene.selectedItems():
                if item is self:
                    continue
                if not isinstance(item, ComponentItem):
                    continue
                if item._anchor_snapshot:
                    continue   # já capturado (defensivo)
                item._press_pos = (
                    item.component.x, item.component.y,
                )
                item._anchor_snapshot = item._capture_attached_anchors()
                item._anchor_before_endpoints = [
                    (
                        wi,
                        ep,
                        wi.wire.x1 if ep == 1 else wi.wire.x2,
                        wi.wire.y1 if ep == 1 else wi.wire.y2,
                    )
                    for (wi, ep, _pi) in item._anchor_snapshot
                ]
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        super().mouseReleaseEvent(event)
        if self._press_pos is None:
            return
        old_x, old_y = self._press_pos
        self._press_pos = None
        new_x, new_y = self.component.x, self.component.y

        # v0.84: snapshot dos endpoints DEPOIS do drag e limpa o
        # buffer de anchors (não vale para o próximo press).
        wire_after = [
            (
                wire_item,
                endpoint_idx,
                wire_item.wire.x1 if endpoint_idx == 1 else wire_item.wire.x2,
                wire_item.wire.y1 if endpoint_idx == 1 else wire_item.wire.y2,
            )
            for (wire_item, endpoint_idx, _pin_idx) in self._anchor_snapshot
        ]
        wire_before = self._anchor_before_endpoints
        self._anchor_snapshot = []
        self._anchor_before_endpoints = []

        if (old_x, old_y) == (new_x, new_y):
            return
        scene = self.scene()
        stack = getattr(scene, "undo_stack", None) if scene is not None else None
        if stack is None:
            # Sem undo stack anexada: drag simples preserva a nova
            # posição (itemChange já atualizou o model + wires).
            return
        # Rebobina a posição para old, então empilha o comando — o
        # primeiro redo re-aplica a posição nova, mantendo o
        # histórico consistente.
        self.component.x = old_x
        self.component.y = old_y
        # Rebobina endpoints dos wires anexados também (o command
        # vai re-aplicá-los no primeiro redo).
        for (wire_item, endpoint_idx, ox, oy) in wire_before:
            if endpoint_idx == 1:
                wire_item.wire.x1 = ox
                wire_item.wire.y1 = oy
            else:
                wire_item.wire.x2 = ox
                wire_item.wire.y2 = oy
            wire_item.sync_from_model()
        self.sync_from_model()
        # Constroi a lista de (PpWire, idx, ox, oy, nx, ny) por wire
        # — o command só precisa do PpWire (referência durável).
        wire_anchors = [
            (
                wire_item.wire,
                idx,
                ox, oy,
                wire_after[i][2], wire_after[i][3],
            )
            for i, (wire_item, idx, ox, oy) in enumerate(wire_before)
        ]
        # Import local: items.py é importado por commands.py, então
        # não podemos importar cedo sem criar ciclo.
        from .commands import MoveComponentCommand
        stack.push(
            MoveComponentCommand(
                scene, self.component,
                old_x, old_y, new_x, new_y,
                wire_anchors=wire_anchors,
            )
        )

    # ---- Wire anchoring ---------------------------------------------------

    def _capture_attached_anchors(
        self,
    ) -> list[tuple["WireItem", int, int]]:
        """
        Identifica fios cuja extremidade coincide com algum pino
        deste componente.

        Retorna lista de tuplas ``(wire_item, endpoint_idx, pin_idx)``
        onde ``endpoint_idx`` é 1 (x1,y1) ou 2 (x2,y2) e ``pin_idx``
        é o índice no ``renderer.pin_positions()``.

        Usado em ``mousePressEvent`` (drag), ``RotateComponentCommand``
        e ``MirrorComponentCommand`` para "fixar" wires aos pinos
        antes da transformação.
        """
        scene = self.scene()
        if scene is None:
            return []
        pins = self.pin_positions_scene()
        # Indexa pinos por (x_int, y_int) para lookup O(1).
        # Um pino pode coincidir com vários endpoints — guardamos
        # *o primeiro* índice para cada (x,y).
        pin_to_idx: dict[tuple[int, int], int] = {}
        for i, p in enumerate(pins):
            key = (int(round(p.x())), int(round(p.y())))
            pin_to_idx.setdefault(key, i)
        anchors: list[tuple["WireItem", int, int]] = []
        wire_items = getattr(scene, "_wires", None) or []
        for wire_item in wire_items:
            w = wire_item.wire
            key1 = (w.x1, w.y1)
            key2 = (w.x2, w.y2)
            if key1 in pin_to_idx:
                anchors.append((wire_item, 1, pin_to_idx[key1]))
            if key2 in pin_to_idx:
                anchors.append((wire_item, 2, pin_to_idx[key2]))
        return anchors

    def _sync_anchored_wires(self) -> None:
        """
        Reposiciona endpoints dos wires capturados em
        ``self._anchor_snapshot`` para a posição atual do pino
        correspondente.
        """
        if not self._anchor_snapshot:
            return
        pins = self.pin_positions_scene()
        for wire_item, endpoint_idx, pin_idx in self._anchor_snapshot:
            if pin_idx >= len(pins):
                continue
            p = pins[pin_idx]
            nx = int(round(p.x()))
            ny = int(round(p.y()))
            w = wire_item.wire
            if endpoint_idx == 1:
                w.x1 = nx
                w.y1 = ny
            else:
                w.x2 = nx
                w.y2 = ny
            wire_item.sync_from_model()

    # ---- API ---------------------------------------------------------------

    def sync_from_model(self) -> None:
        """Aplica o estado do :class:`PpComponent` ao item Qt."""
        c = self.component
        self.setPos(QPointF(c.x, c.y))
        self.setRotation(c.rotation * 90)
        # Espelho horizontal: inverte eixo X.
        self.setTransformOriginPoint(0, 0)
        # QGraphicsObject não tem setScale para X/Y separados antes de 6.x,
        # então usamos transform raw para mirror.
        from PySide6.QtGui import QTransform
        t = QTransform()
        if c.mirror:
            t.scale(-1, 1)
        self.setTransform(t)
        # v0.92.1: renderers que dependem de propriedades do
        # PpComponent (ex.: BusSymbol.length) podem implementar
        # ``update_from_component`` para se sincronizar antes
        # do paint. boundingRect também muda — invalidamos.
        update_fn = getattr(
            self.renderer, "update_from_component", None,
        )
        if callable(update_fn):
            self.prepareGeometryChange()
            try:
                update_fn(c)
            except Exception:
                pass
            # Sincroniza handles de redimensionamento (Bus PTW)
            self._sync_resize_handles()

    def sync_to_model(self) -> None:
        """
        Espelha o estado visual de volta para :class:`PpComponent`.

        Chamado após operações do editor (rotate, mirror) que não
        disparam ``ItemPositionHasChanged``.
        """
        pos = self.pos()
        self.component.x = int(round(pos.x()))
        self.component.y = int(round(pos.y()))
        deg = int(round(self.rotation())) % 360
        self.component.rotation = (deg // 90) % 4
        self.component.mirror = 1 if self.transform().m11() < 0 else 0

    def pin_positions_scene(self) -> list[QPointF]:
        """Pinos no sistema de coordenadas da *scene* (pós-transform)."""
        out: list[QPointF] = []
        for px, py in self.renderer.pin_positions():
            out.append(self.mapToScene(QPointF(px, py)))
        return out

    def rotate_cw(self) -> None:
        """Gira 90° no sentido horário (rotation -= 1 mod 4).

        v0.84: fios fixados aos pinos seguem a rotação.
        """
        anchors = self._capture_attached_anchors()
        self.component.rotation = (self.component.rotation - 1) % 4
        self.sync_from_model()
        self._snap_wires_to_anchors(anchors)

    def rotate_ccw(self) -> None:
        """Gira 90° no sentido anti-horário (rotation += 1 mod 4).

        v0.84: fios fixados aos pinos seguem a rotação.
        """
        anchors = self._capture_attached_anchors()
        self.component.rotation = (self.component.rotation + 1) % 4
        self.sync_from_model()
        self._snap_wires_to_anchors(anchors)

    def mirror_x(self) -> None:
        """Inverte o espelho horizontal.

        v0.84: fios fixados aos pinos seguem o mirror.
        """
        anchors = self._capture_attached_anchors()
        self.component.mirror = 0 if self.component.mirror else 1
        self.sync_from_model()
        self._snap_wires_to_anchors(anchors)

    def _snap_wires_to_anchors(
        self, anchors: list[tuple["WireItem", int, int]]
    ) -> None:
        """
        v0.84: reposiciona endpoints dos fios (anchors capturados
        ANTES de uma transformação) para a posição atual do pino
        correspondente. Análogo de ``_sync_anchored_wires`` mas
        para anchors externos (não ``self._anchor_snapshot``).
        """
        if not anchors:
            return
        pins = self.pin_positions_scene()
        for wire_item, endpoint_idx, pin_idx in anchors:
            if pin_idx >= len(pins):
                continue
            p = pins[pin_idx]
            nx = int(round(p.x()))
            ny = int(round(p.y()))
            w = wire_item.wire
            if endpoint_idx == 1:
                w.x1 = nx
                w.y1 = ny
            else:
                w.x2 = nx
                w.y2 = ny
            wire_item.sync_from_model()

    # ---- v0.92.1: drag-resize handles (Bus PTW) ---------------------------

    def _install_resize_handles_if_supported(self) -> None:
        """
        Instala 2 handles (left/right) se o renderer expõe
        ``endpoint_positions()`` (estilo Bus PTW).
        """
        endpoint_fn = getattr(
            self.renderer, "endpoint_positions", None,
        )
        if not callable(endpoint_fn):
            return
        for side in ("left", "right"):
            handle = BusResizeHandle(side, parent_item=self)
            self._resize_handles.append((handle, side))
        self._sync_resize_handles()

    def _sync_resize_handles(self) -> None:
        """
        Reposiciona os handles para coincidir com os endpoints
        atuais do renderer. Chamado após mudanças de length.
        """
        if not self._resize_handles:
            return
        endpoint_fn = getattr(
            self.renderer, "endpoint_positions", None,
        )
        if not callable(endpoint_fn):
            return
        try:
            (lx, ly), (rx, ry) = endpoint_fn()
        except Exception:
            return
        for handle, side in self._resize_handles:
            if side == "left":
                handle.set_position_silent(lx, ly)
            else:
                handle.set_position_silent(rx, ry)
            # Visíveis só quando o componente está selecionado.
            handle.setVisible(self.isSelected())

    def itemChange_handle_selection(self, change, value):
        """
        v0.92.1: gancho complementar — quando ``ItemSelectedChange``
        dispara, mostra/oculta os handles. Chamado dentro de
        ``itemChange`` existente.
        """
        if not self._resize_handles:
            return
        if change == QGraphicsItem.ItemSelectedHasChanged:
            for handle, _side in self._resize_handles:
                handle.setVisible(bool(value))


# ---------------------------------------------------------------------------
# v0.92.1: Bus resize handle (PTW Power*Tools-style)
# ---------------------------------------------------------------------------


_HANDLE_FILL = QColor(255, 255, 255)
_HANDLE_OUTLINE = QColor(0, 120, 215)
_HANDLE_HOVER = QColor(80, 160, 235)
_HANDLE_SIZE = 8   # px (lado do quadrado)


class BusResizeHandle(QGraphicsObject):
    """
    Handle de redimensionamento do barramento (Bus PTW).

    v0.92.1 — child item de :class:`ComponentItem`. Quando o
    bus está selecionado, dois handles aparecem nos endpoints
    da barra (left + right) e arrastar um deles redimensiona
    o ``BusSymbol.length``.

    v0.92.2 — drag dos handles ``"left"``/``"right"`` agora
    preserva o endpoint OPOSTO (estilo PTW Power*Tools): puxar
    o handle direito por +50 px estende a barra para a direita
    sem mover o endpoint esquerdo (``length += 50``,
    ``component.x += 25``). O modo simétrico em torno do centro
    foi mantido como branch ``side == "center"`` para um
    eventual handle central futuro — ``ComponentItem`` ainda só
    instala left+right.

    Snap automático para múltiplo de 10 px (grid do schematic).

    Mecânica (v0.92.2):

    * ``mousePressEvent``: captura length, x e o anchor scene
      (endpoint oposto, que será preservado), além dos
      endpoints de wires conectados ao bus — base para o
      :class:`ResizeBusCommand` empilhado no release.
    * ``mouseMoveEvent``: roteia para resize assimétrico
      (left/right) ou simétrico (center). Em ambos persiste em
      ``PpComponent.properties[length]`` e clampa endpoints de
      wires conectados que ficaram fora do novo range.
    * ``mouseReleaseEvent``: empilha :class:`ResizeBusCommand`
      no ``QUndoStack`` se houve mudança (length, x ou wire
      endpoints).
    """

    def __init__(
        self,
        side: str,
        *,
        parent_item: "ComponentItem",
    ) -> None:
        super().__init__(parent_item)
        if side not in ("left", "right", "center"):
            raise ValueError(
                f"side deve ser 'left', 'right' ou 'center', got {side!r}"
            )
        self.side = side
        self._parent_item = parent_item
        self._hover = False

        # Handles ficam ACIMA do componente (z-order)
        self.setZValue(10)
        self.setFlag(QGraphicsItem.ItemIgnoresParentOpacity, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.SizeHorCursor)
        # Handles iniciam ocultos; ComponentItem mostra quando selecionado.
        self.setVisible(False)

        # Posição inicial (sincronizada por ComponentItem).
        self._suppress_change = False

        # v0.92.2: estado capturado no mousePress para resize
        # assimétrico + undo. Resetado no release.
        # ``_press_anchor_scene`` = posição em scene coords do
        # endpoint OPOSTO ao handle (preservado durante o drag).
        self._press_length: Optional[int] = None
        self._press_x: Optional[int] = None
        self._press_y: Optional[int] = None
        self._press_anchor_scene: Optional[tuple[int, int]] = None
        # Wires anexados aos pinos do bus no momento do press;
        # endpoints serão clampados ao novo range a cada move.
        self._press_attached_wires: list[
            tuple["WireItem", int, int]
        ] = []
        # Snapshot ANTES do drag dos endpoints anexados, para
        # construir ``ResizeBusCommand.wire_anchors`` no release.
        self._press_wire_snapshot: list[
            tuple["WireItem", int, int, int]
        ] = []

    # ---- Qt overrides -----------------------------------------------------

    def boundingRect(self) -> QRectF:
        s = _HANDLE_SIZE
        return QRectF(-s, -s, 2 * s, 2 * s)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        s = _HANDLE_SIZE / 2
        outline = _HANDLE_HOVER if self._hover else _HANDLE_OUTLINE
        painter.setPen(QPen(outline, 1.5))
        painter.setBrush(QBrush(_HANDLE_FILL))
        painter.drawRect(QRectF(-s, -s, _HANDLE_SIZE, _HANDLE_SIZE))

    def hoverEnterEvent(self, event):
        self._hover = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hover = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        # Não delegar ao parent — queremos drag DO HANDLE.
        if event.button() == Qt.LeftButton:
            self._suppress_change = False
            self._capture_press_state()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return super().mouseMoveEvent(event)
        if self.side == "center":
            self._resize_symmetric(event)
        else:
            self._resize_asymmetric(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        # v0.92.2: empilha ResizeBusCommand se houve mudança.
        parent = self._parent_item
        old_length = self._press_length
        old_x = self._press_x
        if old_length is None or old_x is None:
            self._reset_press_state()
            return
        new_length = int(getattr(parent.renderer, "length", old_length))
        new_x = int(parent.component.x)
        # Constrói wire_anchors a partir do snapshot capturado no
        # press + estado atual dos PpWire (já mutados pelos clamps).
        wire_anchors_for_command: list[
            tuple[PpWire, int, int, int, int, int]
        ] = []
        for (wire_item, idx, ox, oy) in self._press_wire_snapshot:
            w = wire_item.wire
            nx = w.x1 if idx == 1 else w.x2
            ny = w.y1 if idx == 1 else w.y2
            wire_anchors_for_command.append(
                (w, idx, ox, oy, nx, ny)
            )
        moved_wires = any(
            (ox, oy) != (nx, ny)
            for (_w, _i, ox, oy, nx, ny) in wire_anchors_for_command
        )
        if old_length == new_length and old_x == new_x and not moved_wires:
            self._reset_press_state()
            return
        scene = parent.scene()
        stack = (
            getattr(scene, "undo_stack", None)
            if scene is not None else None
        )
        if stack is None:
            # Sem undo stack: drag direto preserva o estado novo.
            self._reset_press_state()
            return
        # Rebobina o estado para "old" — o redo do command re-aplica
        # o novo, deixando o histórico consistente.
        self._restore_state_to_press()
        from .commands import ResizeBusCommand
        stack.push(
            ResizeBusCommand(
                scene, parent.component,
                old_length, new_length,
                old_x, new_x,
                wire_anchors=wire_anchors_for_command,
            )
        )
        self._reset_press_state()
        event.accept()

    # ---- Helpers ---------------------------------------------------------

    def set_position_silent(self, x: int, y: int) -> None:
        """Reposiciona o handle sem disparar itemChange feedback."""
        self._suppress_change = True
        self.setPos(QPointF(x, y))
        self._suppress_change = False

    def _capture_press_state(self) -> None:
        """
        v0.92.2: captura o estado do componente no início do drag —
        usado pelo resize assimétrico (anchor scene) e pelo
        :class:`ResizeBusCommand` (old_length, old_x, wire snapshot).

        Para ``side`` ∈ {"left", "right"}, o anchor é o endpoint
        OPOSTO em scene coords — preservado durante o drag. Para
        ``"center"`` (TBD), nenhum anchor é capturado (resize
        simétrico em torno do centro).
        """
        parent = self._parent_item
        renderer = parent.renderer
        self._press_length = int(getattr(renderer, "length", 0))
        self._press_x = int(parent.component.x)
        self._press_y = int(parent.component.y)
        endpoint_fn = getattr(renderer, "endpoint_positions", None)
        if not callable(endpoint_fn) or self.side == "center":
            self._press_anchor_scene = None
            self._press_attached_wires = []
            self._press_wire_snapshot = []
            return
        try:
            (lx, ly), (rx, ry) = endpoint_fn()
        except Exception:
            self._press_anchor_scene = None
            self._press_attached_wires = []
            self._press_wire_snapshot = []
            return
        if self.side == "right":
            anchor_local = QPointF(lx, ly)
        else:  # "left"
            anchor_local = QPointF(rx, ry)
        anchor_scene = parent.mapToScene(anchor_local)
        self._press_anchor_scene = (
            int(round(anchor_scene.x())),
            int(round(anchor_scene.y())),
        )
        # Captura wires anexados ao bus para clamping no move + undo.
        self._press_attached_wires = parent._capture_attached_anchors()
        self._press_wire_snapshot = [
            (wi, idx,
             wi.wire.x1 if idx == 1 else wi.wire.x2,
             wi.wire.y1 if idx == 1 else wi.wire.y2)
            for (wi, idx, _pin_idx) in self._press_attached_wires
        ]

    def _reset_press_state(self) -> None:
        self._press_length = None
        self._press_x = None
        self._press_y = None
        self._press_anchor_scene = None
        self._press_attached_wires = []
        self._press_wire_snapshot = []

    def _restore_state_to_press(self) -> None:
        """
        Rebobina o componente, length e endpoints de wires para
        o estado capturado em :meth:`_capture_press_state`.

        Chamado no :meth:`mouseReleaseEvent` ANTES de empilhar
        ``ResizeBusCommand`` — o primeiro redo do command
        re-aplica o estado novo, mantendo o histórico
        consistente com o padrão de :class:`MoveComponentCommand`.
        """
        parent = self._parent_item
        if self._press_length is None or self._press_x is None:
            return
        if hasattr(parent.renderer, "set_length"):
            parent.prepareGeometryChange()
            parent.renderer.set_length(self._press_length)
        parent.component.x = int(self._press_x)
        parent.setPos(QPointF(parent.component.x, parent.component.y))
        self._persist_length(int(parent.renderer.length))
        for (wire_item, idx, ox, oy) in self._press_wire_snapshot:
            w = wire_item.wire
            if idx == 1:
                w.x1 = ox
                w.y1 = oy
            else:
                w.x2 = ox
                w.y2 = oy
            wire_item.sync_from_model()
        parent._sync_resize_handles()
        parent.update()

    def _resize_symmetric(self, event) -> None:
        """
        v0.92.1: resize simétrico em torno do centro (mantém
        ``component.x`` fixo). Mantido como fallback para um
        eventual handle ``"center"`` — ``ComponentItem`` em
        v0.92.2 instala apenas left/right, então este branch só
        executa via testes ou extensões.
        """
        scene_pos = event.scenePos()
        parent_pos = self._parent_item.mapFromScene(scene_pos)
        x = round(parent_pos.x() / 10) * 10
        renderer = self._parent_item.renderer
        new_length = max(
            getattr(renderer, "MIN_LENGTH", 60),
            min(
                getattr(renderer, "MAX_LENGTH", 4000),
                2 * abs(int(x)),
            ),
        )
        if hasattr(renderer, "set_length"):
            self._parent_item.prepareGeometryChange()
            renderer.set_length(new_length)
            self._persist_length(int(renderer.length))
            self._parent_item._sync_resize_handles()
            self._parent_item.update()

    def _resize_asymmetric(self, event) -> None:
        """
        v0.92.2: resize que preserva o endpoint OPOSTO ao handle
        (estilo PTW Power*Tools).

        Drag do handle ``right``: o endpoint esquerdo (anchor)
        permanece fixo em scene coords; o endpoint direito segue
        o mouse. ``length = mouse_x − anchor_x`` (clamped a
        [MIN, MAX]); ``component.x = anchor + length/2``. Para
        o handle ``left``, simétrico.

        Wires conectados ao bus que ficaram fora do novo range
        têm seus endpoints clampados via :meth:`_clamp_attached_wires`.
        """
        parent = self._parent_item
        renderer = parent.renderer
        if not hasattr(renderer, "set_length"):
            return
        if self._press_anchor_scene is None:
            # Press não foi capturado (testes que pulam mousePress
            # ou eventos sintéticos). Captura agora — o estado
            # atual serve como referência inicial.
            self._capture_press_state()
        if self._press_anchor_scene is None:
            return
        scene_pos = event.scenePos()
        mouse_x = int(round(scene_pos.x() / 10)) * 10
        anchor_x, _anchor_y = self._press_anchor_scene
        if self.side == "right":
            new_length = mouse_x - anchor_x
        else:
            new_length = anchor_x - mouse_x
        min_len = getattr(renderer, "MIN_LENGTH", 60)
        max_len = getattr(renderer, "MAX_LENGTH", 4000)
        new_length = max(min_len, min(max_len, int(new_length)))
        parent.prepareGeometryChange()
        renderer.set_length(new_length)
        eff_length = int(renderer.length)
        if self.side == "right":
            new_center_x = anchor_x + eff_length // 2
        else:
            new_center_x = anchor_x - eff_length // 2
        comp = parent.component
        comp.x = int(new_center_x)
        parent.setPos(QPointF(comp.x, comp.y))
        self._persist_length(eff_length)
        self._clamp_attached_wires()
        parent._sync_resize_handles()
        parent.update()

    def _clamp_attached_wires(self) -> None:
        """
        v0.92.2: clamp endpoints dos wires anexados (capturados
        no press) ao novo range scene da barra. Wires fora do
        range são puxados ao endpoint mais próximo; wires dentro
        permanecem onde estavam (a barra ainda passa por eles).
        Snap a múltiplo de 10 px para alinhar aos pinos sintéticos.
        """
        if not self._press_attached_wires:
            return
        parent = self._parent_item
        renderer = parent.renderer
        endpoint_fn = getattr(renderer, "endpoint_positions", None)
        if not callable(endpoint_fn):
            return
        try:
            (lx, ly), (rx, ry) = endpoint_fn()
        except Exception:
            return
        left_scene = parent.mapToScene(QPointF(lx, ly))
        right_scene = parent.mapToScene(QPointF(rx, ry))
        x_min = min(int(round(left_scene.x())),
                    int(round(right_scene.x())))
        x_max = max(int(round(left_scene.x())),
                    int(round(right_scene.x())))
        bus_y = int(round((left_scene.y() + right_scene.y()) / 2))
        for (wire_item, endpoint_idx, _pin_idx) in self._press_attached_wires:
            w = wire_item.wire
            old_x = w.x1 if endpoint_idx == 1 else w.x2
            new_x = max(x_min, min(x_max, old_x))
            new_x = int(round(new_x / 10)) * 10
            new_x = max(x_min, min(x_max, new_x))
            if endpoint_idx == 1:
                w.x1 = new_x
                w.y1 = bus_y
            else:
                w.x2 = new_x
                w.y2 = bus_y
            wire_item.sync_from_model()

    def _persist_length(self, new_length: int) -> None:
        """
        Atualiza ``PpComponent.properties[idx].value`` para o
        slot ``"length"`` (definido em BUS.ocomp). Idempotente
        — se a propriedade não existe, não faz nada.
        """
        comp = self._parent_item.component
        try:
            from app.preprocessor.spec import get_default_registry
        except ImportError:
            return
        spec = get_default_registry().get(comp.type)
        if spec is None:
            return
        for idx, prop_spec in enumerate(spec.properties):
            if prop_spec.name == "length":
                if idx < len(comp.properties):
                    comp.properties[idx].value = str(int(new_length))
                return


# ---------------------------------------------------------------------------
# Fallback renderer (componente de tipo desconhecido)
# ---------------------------------------------------------------------------


class _FallbackRenderer(SymbolRenderer):
    """Render genérico para type_code sem símbolo registrado."""

    PINS = ((0, -30), (0, 30))
    SIZE = 60

    def __init__(self, type_code: str) -> None:
        self._text = type_code or "?"

    def paint(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor(160, 0, 0), 1.5, Qt.DashLine))
        painter.setBrush(QBrush(QColor(255, 245, 245)))
        painter.drawRect(QRectF(-20, -12, 40, 24))
        painter.setPen(QPen(QColor(80, 0, 0), 1.0))
        painter.setFont(QFont("Sans", 7, QFont.Bold))
        painter.drawText(QRectF(-20, -12, 40, 24), Qt.AlignCenter, self._text)
        # leads
        painter.setPen(QPen(QColor(160, 0, 0), 1.0))
        painter.drawLine(QPointF(0, -30), QPointF(0, -12))
        painter.drawLine(QPointF(0, 12), QPointF(0, 30))


# ---------------------------------------------------------------------------
# WireItem
# ---------------------------------------------------------------------------


class WireItem(QGraphicsPathItem):
    """
    Fio entre dois pontos da cena, roteado em L (primeiro horizontal,
    depois vertical) quando não for alinhado. Wires ortogonais
    ficam como uma reta única.

    A âncora é a *scene*: `wire.x1/y1/x2/y2` são coordenadas absolutas
    no mesmo sistema do Qucs .sch.
    """

    Type = QGraphicsItem.UserType + 102

    def __init__(self, wire: PpWire,
                 parent: Optional[QGraphicsItem] = None) -> None:
        super().__init__(parent)
        self.wire = wire
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setPen(QPen(_WIRE_COLOR, 1.5, Qt.SolidLine,
                         Qt.RoundCap, Qt.RoundJoin))
        self._rebuild()

    def type(self) -> int:  # noqa: A003
        return WireItem.Type

    def _rebuild(self) -> None:
        w = self.wire
        path = QPainterPath(QPointF(w.x1, w.y1))
        if w.x1 == w.x2 or w.y1 == w.y2:
            # colinear — reta única.
            path.lineTo(QPointF(w.x2, w.y2))
        else:
            # L-route: primeiro horizontal, depois vertical.
            path.lineTo(QPointF(w.x2, w.y1))
            path.lineTo(QPointF(w.x2, w.y2))
        self.setPath(path)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem,
              widget: Optional[QWidget] = None) -> None:
        if self.isSelected():
            pen = QPen(_WIRE_SEL_COLOR, 2.5, Qt.SolidLine,
                       Qt.RoundCap, Qt.RoundJoin)
        else:
            pen = self.pen()
        painter.setPen(pen)
        painter.drawPath(self.path())
        if self.wire.label:
            painter.save()
            painter.setPen(QPen(_LABEL_COLOR, 1.0))
            painter.setFont(QFont("Sans", 7, QFont.Bold))
            painter.drawText(QPointF(self.wire.label_x + 4,
                                     self.wire.label_y - 4),
                             self.wire.label)
            painter.restore()

    def sync_from_model(self) -> None:
        """Reconstrói o path a partir do :class:`PpWire`."""
        self._rebuild()

    @staticmethod
    def endpoints(wire: PpWire) -> tuple[QPointF, QPointF]:
        """Conveniência: ``QPointF`` das duas pontas."""
        return (QPointF(wire.x1, wire.y1), QPointF(wire.x2, wire.y2))


# ---------------------------------------------------------------------------
# DataBlockItem — v0.86 (PTW Equipment-style)
# ---------------------------------------------------------------------------


# Estilo do datablock (paleta Oliveira aplicada).
_DATABLOCK_BG = QColor(255, 255, 240)        # creme (post-it)
_DATABLOCK_BORDER = QColor(85, 107, 47)      # OLIVE_DEEP
_DATABLOCK_TEXT = QColor(42, 45, 36)         # quase preto (legível)
_DATABLOCK_SEL = QColor(0, 168, 232)         # CYAN_BRIGHT (selection)
_DATABLOCK_RADIUS = 4.0
_DATABLOCK_PAD = 6.0
_DATABLOCK_LINE_HEIGHT = 13.0
_DATABLOCK_FONT = QFont("Segoe UI, Sans", 8)
_DATABLOCK_FONT.setStyleStrategy(QFont.PreferAntialias)


class DataBlockItem(QGraphicsObject):
    """
    Datablock textual — caixa flutuante próxima a um componente
    com resultados/observações de análises (PTW Equipment-style).

    Implementação:

    * **Pai = ``ComponentItem``** — assim o datablock segue
      automaticamente o componente em qualquer transformação
      do pai (drag, rotate, mirror).
    * **Movível independente** — usuário pode arrastar o
      datablock para reposicionar; ``itemChange`` atualiza
      ``PpDataBlock.dx/dy`` (sempre relativo ao pai).
    * **Seleção visual** — borda highlighted ao selecionar.

    Não tem ``ItemSendsScenePositionChanges`` — só posições
    locais relativas ao pai. A scene não vê coordenadas
    absolutas do datablock até ``mapToScene`` ser chamado.
    """

    Type = QGraphicsItem.UserType + 103

    def __init__(self, datablock: PpDataBlock,
                 host: ComponentItem) -> None:
        super().__init__(host)   # parent = host (auto-follow)
        self._datablock = datablock
        self._host = host
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        # Z-value alto para ficar acima de outros items.
        self.setZValue(50)
        # Não herda transformação do componente (rotate/mirror) — o
        # texto deve ficar sempre legível na orientação canvas.
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
        self.setFlag(
            QGraphicsItem.ItemIgnoresParentOpacity, True
        )
        self.sync_from_model()

    # ---- Qt overrides -----------------------------------------------------

    def type(self) -> int:  # noqa: A003
        return DataBlockItem.Type

    @property
    def datablock(self) -> PpDataBlock:
        return self._datablock

    def boundingRect(self) -> QRectF:
        """
        Rect calculado dinamicamente a partir das linhas de texto
        + padding. ``QFontMetricsF`` mede a largura da linha mais
        comprida.
        """
        lines = self._datablock.lines or [""]
        metrics = QFontMetricsF(_DATABLOCK_FONT)
        max_w = max(
            (metrics.horizontalAdvance(ln) for ln in lines),
            default=0.0,
        )
        h = _DATABLOCK_LINE_HEIGHT * len(lines)
        rect = QRectF(
            0, 0,
            max_w + 2 * _DATABLOCK_PAD,
            h + 2 * _DATABLOCK_PAD,
        )
        # Margem para halo de seleção
        return rect.adjusted(-2, -2, 2, 2)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem,
              widget: Optional[QWidget] = None) -> None:
        rect = self.boundingRect().adjusted(2, 2, -2, -2)
        # Borda destacada quando selecionado
        if self.isSelected():
            border_color = _DATABLOCK_SEL
            pen_w = 1.6
        else:
            border_color = _DATABLOCK_BORDER
            pen_w = 1.0
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(QBrush(_DATABLOCK_BG))
        painter.setPen(QPen(border_color, pen_w))
        painter.drawRoundedRect(
            rect, _DATABLOCK_RADIUS, _DATABLOCK_RADIUS,
        )
        # Texto
        painter.setPen(QPen(_DATABLOCK_TEXT, 1.0))
        painter.setFont(_DATABLOCK_FONT)
        y = _DATABLOCK_PAD + _DATABLOCK_LINE_HEIGHT - 3
        x = _DATABLOCK_PAD
        for line in (self._datablock.lines or []):
            painter.drawText(QPointF(x, y), line)
            y += _DATABLOCK_LINE_HEIGHT
        painter.restore()

    def itemChange(self, change, value):
        # Quando o usuário arrasta o datablock, sincroniza dx/dy
        # com o model. Posição é LOCAL (relativa ao parent).
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            pos = self.pos()
            self._datablock.dx = int(round(pos.x()))
            self._datablock.dy = int(round(pos.y()))
        return super().itemChange(change, value)

    # ---- API --------------------------------------------------------------

    def sync_from_model(self) -> None:
        """
        Aplica o estado do :class:`PpDataBlock` ao item visual.
        ``setPos`` aciona ``ItemPositionChanged`` mas o callback
        já checa identidade do delta — não loop.
        """
        db = self._datablock
        self.setPos(QPointF(db.dx, db.dy))
        self.setVisible(db.visible)
        self.update()  # repaint para refletir lines novas

    def mouseDoubleClickEvent(self, event):  # type: ignore[override]
        """Duplo-clique abre dialog de edição."""
        # Lazy import — evita ciclo
        try:
            from app.gui.datablock_dialog import DataBlockEditDialog
        except ImportError:
            return super().mouseDoubleClickEvent(event)
        dlg = DataBlockEditDialog(
            None,
            initial_lines=list(self._datablock.lines),
        )
        from PySide6.QtWidgets import QDialog
        if dlg.exec() == QDialog.Accepted:
            self._datablock.lines = dlg.lines()
            self.prepareGeometryChange()  # bbox pode ter mudado
            self.sync_from_model()
