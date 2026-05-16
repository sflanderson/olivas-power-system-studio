"""
app.gui.schematic_pp.commands — comandos :class:`QUndoCommand` para
o editor visual do pré-processador.

Filosofia
---------

Todas as mutações do :class:`PpProject` / :class:`PpScene` passam
por um único lugar: a :class:`QUndoStack` hospedada pelo
:class:`PpEditor`. Cada comando conhece:

* como aplicar a mutação (``redo``);
* como desfazer (``undo``);
* um texto curto para a UI (*"Adicionar R1"*, *"Rotacionar R1"*,
  *"Editar propriedade"*).

Nenhum comando mantém referência direta a objetos Qt que podem
virar *dangling* — em vez disso, referenciamos ``PpComponent`` /
``PpWire`` (dataclasses puras) por identidade e, quando
necessário, recriamos os :class:`ComponentItem` / :class:`WireItem`
correspondentes no ``redo``. Isso evita bugs comuns de *use after
delete*.

Comandos fornecidos
-------------------

* :class:`AddComponentCommand`, :class:`RemoveComponentCommand`
* :class:`AddWireCommand`, :class:`RemoveWireCommand`
* :class:`MoveComponentCommand`
* :class:`RotateComponentCommand`, :class:`MirrorComponentCommand`
* :class:`EditPropertyCommand`, :class:`EditNameCommand`
* :class:`RemoveSelectionCommand` — agrupa remoção de múltiplos
  itens em uma única operação para o histórico.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QUndoCommand

from app.preprocessor.models import (
    PpComponent, PpDataBlock, PpLegendTag, PpLinkTag, PpProperty, PpWire,
)

from .items import ComponentItem, DataBlockItem, WireItem
from .scene import PpScene


# ---------------------------------------------------------------------------
# Add / remove
# ---------------------------------------------------------------------------


class AddComponentCommand(QUndoCommand):
    """Adiciona um :class:`PpComponent` à cena.

    O nome único é resolvido no *primeiro* redo (pela
    :meth:`PpScene.add_component`) e memorizado para que redos
    subsequentes (após um undo) preservem exatamente o mesmo
    nome — consistência crítica para o histórico.
    """

    def __init__(self, scene: PpScene, component: PpComponent,
                 text: Optional[str] = None) -> None:
        super().__init__(text or f"Adicionar {component.type}")
        self._scene = scene
        self._component = component
        self._name_resolved = False

    def redo(self) -> None:  # pragma: no cover - exercised via tests
        self._scene.add_component(self._component)
        if not self._name_resolved:
            self.setText(f"Adicionar {self._component.name or self._component.type}")
            self._name_resolved = True

    def undo(self) -> None:  # pragma: no cover
        item = self._scene.find_component_item(self._component)
        if item is not None:
            self._scene.remove_component(item)


class RemoveComponentCommand(QUndoCommand):
    """Remove um :class:`PpComponent`; undo restaura o mesmo objeto
    (mantém identidade de referência)."""

    def __init__(self, scene: PpScene, component: PpComponent,
                 text: Optional[str] = None) -> None:
        super().__init__(text or f"Remover {component.name or component.type}")
        self._scene = scene
        self._component = component

    def redo(self) -> None:  # pragma: no cover
        item = self._scene.find_component_item(self._component)
        if item is not None:
            self._scene.remove_component(item)

    def undo(self) -> None:  # pragma: no cover
        self._scene.add_component(self._component)


class AddWireCommand(QUndoCommand):
    """Adiciona um :class:`PpWire` à cena."""

    def __init__(self, scene: PpScene, wire: PpWire,
                 text: Optional[str] = None) -> None:
        super().__init__(text or "Adicionar fio")
        self._scene = scene
        self._wire = wire

    def redo(self) -> None:  # pragma: no cover
        self._scene.add_wire(self._wire)

    def undo(self) -> None:  # pragma: no cover
        item = self._scene.find_wire_item(self._wire)
        if item is not None:
            self._scene.remove_wire(item)


class RemoveWireCommand(QUndoCommand):
    """Remove um :class:`PpWire`."""

    def __init__(self, scene: PpScene, wire: PpWire,
                 text: Optional[str] = None) -> None:
        super().__init__(text or "Remover fio")
        self._scene = scene
        self._wire = wire

    def redo(self) -> None:  # pragma: no cover
        item = self._scene.find_wire_item(self._wire)
        if item is not None:
            self._scene.remove_wire(item)

    def undo(self) -> None:  # pragma: no cover
        self._scene.add_wire(self._wire)


class AddSeriesComponentCommand(QUndoCommand):
    """Insere componente em série quebrando um fio existente.

    v3.1.2 Sub-sprint C — fecha deferred de v3.1.1 Sprint 1.
    Reproduz auto-bus-node em série do PTW Tutorial §Part 1 p.27.

    Comportamento atômico (single redo / single undo):
    1. Remove o fio original ``original_wire``
    2. Adiciona ``new_component`` em ``component_pos``
    3. Adiciona dois novos fios:
       * ``wire_in``: original_wire.start → component pin esquerdo
       * ``wire_out``: component pin direito → original_wire.end

    O comando é atômico — Ctrl+Z desfaz tudo numa única operação.

    References
    ----------
    PTW Tutorial v8.0 §Part 1 p.27 (auto-bus-node em série).
    """

    def __init__(
        self,
        scene: PpScene,
        original_wire: PpWire,
        new_component: PpComponent,
        wire_in: PpWire,
        wire_out: PpWire,
        text: Optional[str] = None,
    ) -> None:
        super().__init__(text or f"Inserir {new_component.type} em série")
        self._scene = scene
        self._orig_wire = original_wire
        self._comp = new_component
        self._wire_in = wire_in
        self._wire_out = wire_out
        self._name_resolved = False

    def redo(self) -> None:  # pragma: no cover
        # 1. Remove o wire original
        item = self._scene.find_wire_item(self._orig_wire)
        if item is not None:
            self._scene.remove_wire(item)
        # 2. Adiciona o componente
        self._scene.add_component(self._comp)
        if not self._name_resolved:
            self.setText(
                f"Inserir {self._comp.name or self._comp.type} em série"
            )
            self._name_resolved = True
        # 3. Adiciona os 2 wires novos
        self._scene.add_wire(self._wire_in)
        self._scene.add_wire(self._wire_out)

    def undo(self) -> None:  # pragma: no cover
        # Inverso: remove os 2 wires + componente, restaura wire original
        for w in (self._wire_in, self._wire_out):
            it = self._scene.find_wire_item(w)
            if it is not None:
                self._scene.remove_wire(it)
        comp_item = self._scene.find_component_item(self._comp)
        if comp_item is not None:
            self._scene.remove_component(comp_item)
        self._scene.add_wire(self._orig_wire)


# ---------------------------------------------------------------------------
# Move / rotate / mirror
# ---------------------------------------------------------------------------


class MoveComponentCommand(QUndoCommand):
    """Move um componente de ``old_pos`` para ``new_pos``.

    Coalesce automaticamente (mesmo componente, movidos em sequência)
    via :meth:`QUndoCommand.mergeWith` para não poluir o histórico
    com uma entrada por pixel.

    v0.84: agora aceita ``wire_anchors`` — lista de tuplas
    ``(PpWire, endpoint_idx, old_x, old_y, new_x, new_y)`` para
    mover endpoints de fios fixados aos pinos do componente
    em conjunto com o movimento (sem fios = lista vazia, comportamento
    pré-v0.84). Quando presente, ``mergeWith`` é desativado para
    preservar fielmente os deltas de cada drag separado.
    """

    MERGE_ID = 1001

    def __init__(self, scene: PpScene, component: PpComponent,
                 old_x: int, old_y: int, new_x: int, new_y: int,
                 wire_anchors: Optional[
                     list[tuple[PpWire, int, int, int, int, int]]
                 ] = None) -> None:
        super().__init__(f"Mover {component.name or component.type}")
        self._scene = scene
        self._component = component
        self._old = (old_x, old_y)
        self._new = (new_x, new_y)
        self._wire_anchors = list(wire_anchors or [])

    def id(self) -> int:  # noqa: A003 - Qt override
        return self.MERGE_ID

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, MoveComponentCommand):
            return False
        if other._component is not self._component:
            return False
        # v0.84: comandos com wire_anchors não fazem merge. Cada
        # drag de um componente conectado é uma operação atômica
        # do ponto de vista do undo. Merging só é seguro quando
        # ambos não tocam fios.
        if self._wire_anchors or other._wire_anchors:
            return False
        # Preserva o ponto de partida original e adota o destino novo.
        self._new = other._new
        return True

    def _apply_wires(self, use_new: bool) -> None:
        for (wire, idx, ox, oy, nx, ny) in self._wire_anchors:
            x, y = (nx, ny) if use_new else (ox, oy)
            if idx == 1:
                wire.x1 = x
                wire.y1 = y
            else:
                wire.x2 = x
                wire.y2 = y
            wire_item = self._scene.find_wire_item(wire)
            if wire_item is not None:
                wire_item.sync_from_model()

    def _apply(self, x: int, y: int, use_new_wires: bool) -> None:
        self._component.x = x
        self._component.y = y
        item = self._scene.find_component_item(self._component)
        if item is not None:
            item.sync_from_model()
        self._apply_wires(use_new_wires)

    def redo(self) -> None:  # pragma: no cover
        self._apply(*self._new, use_new_wires=True)

    def undo(self) -> None:  # pragma: no cover
        self._apply(*self._old, use_new_wires=False)


class RotateComponentCommand(QUndoCommand):
    """Rotaciona em torno de si mesmo em múltiplos de 90°.

    v0.84: fios fixados aos pinos seguem a rotação — endpoints são
    snapped para a nova posição do pino correspondente após o
    transform.
    """

    def __init__(self, scene: PpScene, component: PpComponent,
                 direction: int) -> None:
        """
        direction: +1 (horário) ou -1 (anti-horário).
        """
        super().__init__(
            f"Rotacionar {component.name or component.type} "
            f"({'CW' if direction > 0 else 'CCW'})"
        )
        self._scene = scene
        self._component = component
        self._direction = 1 if direction > 0 else -1

    def _rotate(self, step: int) -> None:
        # v0.84: captura anchors *antes* da rotação. Pin_idx é
        # estável pré/pós rotação (a renderer.pin_positions() é
        # uma lista fixa em coords locais do componente). O que
        # muda é o mapToScene após o setRotation.
        item = self._scene.find_component_item(self._component)
        anchors = (
            item._capture_attached_anchors() if item is not None else []
        )
        self._component.rotation = (self._component.rotation + step) % 4
        if item is not None:
            item.sync_from_model()
            _snap_wires_to_pins(item, anchors)

    def redo(self) -> None:  # pragma: no cover
        self._rotate(self._direction)

    def undo(self) -> None:  # pragma: no cover
        self._rotate(-self._direction)


class MirrorComponentCommand(QUndoCommand):
    """Aplica / desfaz espelho horizontal.

    v0.84: fios fixados aos pinos seguem o mirror.
    """

    def __init__(self, scene: PpScene, component: PpComponent) -> None:
        super().__init__(f"Espelhar {component.name or component.type}")
        self._scene = scene
        self._component = component

    def _toggle(self) -> None:
        item = self._scene.find_component_item(self._component)
        anchors = (
            item._capture_attached_anchors() if item is not None else []
        )
        self._component.mirror = 0 if self._component.mirror else 1
        if item is not None:
            item.sync_from_model()
            _snap_wires_to_pins(item, anchors)

    def redo(self) -> None:  # pragma: no cover
        self._toggle()

    def undo(self) -> None:  # pragma: no cover
        self._toggle()


class ResizeBusCommand(QUndoCommand):
    """
    v0.92.2: redimensiona um Bus PTW (length + position).

    Diferente de :class:`MoveComponentCommand`, este comando captura
    três coisas ao mesmo tempo:

    * ``length`` — propriedade ``"length"`` do PpComponent + estado
      do renderer ``BusSymbol.length``.
    * ``component.x`` — o centro da barra muda em resize assimétrico
      (drag preserva o endpoint oposto, então o centro desloca pela
      metade do delta).
    * ``wire_anchors`` — endpoints de wires conectados ao bus que
      foram clampados ao novo range em scene coords.

    Não merge — cada drag completo do handle é uma operação atômica
    no histórico.
    """

    def __init__(
        self,
        scene: PpScene,
        component: PpComponent,
        old_length: int,
        new_length: int,
        old_x: int,
        new_x: int,
        wire_anchors: Optional[
            list[tuple[PpWire, int, int, int, int, int]]
        ] = None,
    ) -> None:
        super().__init__(
            f"Redimensionar {component.name or component.type}"
        )
        self._scene = scene
        self._component = component
        self._old_length = int(old_length)
        self._new_length = int(new_length)
        self._old_x = int(old_x)
        self._new_x = int(new_x)
        self._wire_anchors = list(wire_anchors or [])

    def _set_length_property(self, length: int) -> None:
        try:
            from app.preprocessor.spec import get_default_registry
        except ImportError:
            return
        try:
            spec = get_default_registry().get(self._component.type)
        except Exception:
            return
        if spec is None:
            return
        for idx, prop_spec in enumerate(spec.properties):
            if prop_spec.name == "length":
                if idx < len(self._component.properties):
                    self._component.properties[idx].value = str(int(length))
                return

    def _apply_wires(self, use_new: bool) -> None:
        for (wire, idx, ox, oy, nx, ny) in self._wire_anchors:
            x, y = (nx, ny) if use_new else (ox, oy)
            if idx == 1:
                wire.x1 = x
                wire.y1 = y
            else:
                wire.x2 = x
                wire.y2 = y
            wire_item = self._scene.find_wire_item(wire)
            if wire_item is not None:
                wire_item.sync_from_model()

    def _apply(self, length: int, x: int, use_new_wires: bool) -> None:
        # Atualiza length na propriedade ANTES do sync_from_model do
        # item — sync_from_model lê a property via update_from_component.
        self._set_length_property(length)
        self._component.x = int(x)
        item = self._scene.find_component_item(self._component)
        if item is not None:
            item.prepareGeometryChange()
            item.sync_from_model()
        self._apply_wires(use_new_wires)

    def redo(self) -> None:  # pragma: no cover
        self._apply(self._new_length, self._new_x, use_new_wires=True)

    def undo(self) -> None:  # pragma: no cover
        self._apply(self._old_length, self._old_x, use_new_wires=False)


def _snap_wires_to_pins(
    comp_item: ComponentItem,
    anchors: list[tuple[WireItem, int, int]],
) -> None:
    """
    Reposiciona endpoints dos fios capturados em ``anchors`` para a
    posição atual do pino (``comp_item.pin_positions_scene()[pin_idx]``)
    no espaço da cena.

    Helper compartilhado por ``RotateComponentCommand`` e
    ``MirrorComponentCommand`` — não duplicamos a lógica de
    ``ComponentItem._sync_anchored_wires`` porque os comandos
    operam com ``anchors`` capturados ANTES da transformação,
    enquanto ``_sync_anchored_wires`` é estado interno do drag.
    """
    pins = comp_item.pin_positions_scene()
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


# ---------------------------------------------------------------------------
# Edit properties
# ---------------------------------------------------------------------------


class EditPropertyCommand(QUndoCommand):
    """Altera o valor de uma :class:`PpProperty` de um componente."""

    MERGE_ID = 1002

    def __init__(self, scene: PpScene, component: PpComponent,
                 prop_index: int, new_value: str) -> None:
        if not (0 <= prop_index < len(component.properties)):
            raise IndexError(
                f"prop_index {prop_index} fora do intervalo "
                f"(componente {component.name} tem {len(component.properties)} props)"
            )
        self._component = component
        self._scene = scene
        self._index = prop_index
        self._old = component.properties[prop_index].value
        self._new = new_value
        super().__init__(
            f"Editar {component.name or component.type}."
            f"prop#{prop_index + 1} → {new_value}"
        )

    def id(self) -> int:  # noqa: A003
        return self.MERGE_ID

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, EditPropertyCommand):
            return False
        if (other._component is not self._component
                or other._index != self._index):
            return False
        self._new = other._new
        return True

    def _apply(self, value: str) -> None:
        self._component.properties[self._index].value = value
        item = self._scene.find_component_item(self._component)
        if item is not None:
            item.update()

    def redo(self) -> None:  # pragma: no cover
        self._apply(self._new)

    def undo(self) -> None:  # pragma: no cover
        self._apply(self._old)


class EditVisibilityCommand(QUndoCommand):
    """
    Alterna o flag ``visible`` de uma :class:`PpProperty` — controla
    se o valor da propriedade aparece abaixo do símbolo no canvas.

    Introduzido em v0.22.2.b para que o toggle do checkbox "exibir"
    do painel de propriedades entre no histórico de undo/redo, em
    paridade com as edições de valor (``EditPropertyCommand``).
    """

    MERGE_ID = 1004

    def __init__(self, scene: PpScene, component: PpComponent,
                 prop_index: int, new_visible: bool) -> None:
        if not (0 <= prop_index < len(component.properties)):
            raise IndexError(
                f"prop_index {prop_index} fora do intervalo "
                f"(componente {component.name} tem "
                f"{len(component.properties)} props)"
            )
        self._component = component
        self._scene = scene
        self._index = prop_index
        self._old = component.properties[prop_index].visible
        self._new = new_visible
        action = "exibir" if new_visible else "ocultar"
        super().__init__(
            f"{action.capitalize()} {component.name or component.type}."
            f"prop#{prop_index + 1}"
        )

    def id(self) -> int:  # noqa: A003
        return self.MERGE_ID

    def mergeWith(self, other: QUndoCommand) -> bool:
        """Colapsa edições em sequência da MESMA property do MESMO comp."""
        if not isinstance(other, EditVisibilityCommand):
            return False
        if (other._component is not self._component
                or other._index != self._index):
            return False
        self._new = other._new
        return True

    def _apply(self, visible: bool) -> None:
        self._component.properties[self._index].visible = visible
        item = self._scene.find_component_item(self._component)
        if item is not None:
            item.update()

    def redo(self) -> None:  # pragma: no cover
        self._apply(self._new)

    def undo(self) -> None:  # pragma: no cover
        self._apply(self._old)


class EditNameCommand(QUndoCommand):
    """Renomeia um componente."""

    MERGE_ID = 1003

    def __init__(self, scene: PpScene, component: PpComponent,
                 new_name: str) -> None:
        self._component = component
        self._scene = scene
        self._old = component.name
        self._new = new_name
        super().__init__(f"Renomear → {new_name}")

    def id(self) -> int:  # noqa: A003
        return self.MERGE_ID

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, EditNameCommand):
            return False
        if other._component is not self._component:
            return False
        self._new = other._new
        return True

    def _apply(self, name: str) -> None:
        self._component.name = name
        item = self._scene.find_component_item(self._component)
        if item is not None:
            item.update()

    def redo(self) -> None:  # pragma: no cover
        self._apply(self._new)

    def undo(self) -> None:  # pragma: no cover
        self._apply(self._old)


# ---------------------------------------------------------------------------
# Grouped removals (multi-selection delete)
# ---------------------------------------------------------------------------


class RemoveSelectionCommand(QUndoCommand):
    """Remove uma seleção mista de componentes e fios em uma só operação."""

    def __init__(self, scene: PpScene, components: list[PpComponent],
                 wires: list[PpWire]) -> None:
        total = len(components) + len(wires)
        super().__init__(f"Remover {total} item(s)")
        self._scene = scene
        self._components = list(components)
        self._wires = list(wires)

    def redo(self) -> None:  # pragma: no cover
        for comp in self._components:
            item = self._scene.find_component_item(comp)
            if item is not None:
                self._scene.remove_component(item)
        for wire in self._wires:
            item = self._scene.find_wire_item(wire)
            if item is not None:
                self._scene.remove_wire(item)

    def undo(self) -> None:  # pragma: no cover
        for comp in self._components:
            self._scene.add_component(comp)
        for wire in self._wires:
            self._scene.add_wire(wire)


# ---------------------------------------------------------------------------
# Datablocks (v0.86 — PTW Equipment-style)
# ---------------------------------------------------------------------------


class AddDataBlockCommand(QUndoCommand):
    """v0.86: adiciona um :class:`PpDataBlock` à cena (undoable)."""

    def __init__(self, scene: PpScene, datablock: PpDataBlock) -> None:
        super().__init__(
            f"Adicionar datablock em {datablock.component_name}"
        )
        self._scene = scene
        self._datablock = datablock

    def redo(self) -> None:  # pragma: no cover
        self._scene.add_datablock(self._datablock)

    def undo(self) -> None:  # pragma: no cover
        item = self._scene.find_datablock_item(self._datablock)
        if item is not None:
            self._scene.remove_datablock(item)


class RemoveDataBlockCommand(QUndoCommand):
    """v0.86: remove um datablock (undoable)."""

    def __init__(self, scene: PpScene, datablock: PpDataBlock) -> None:
        super().__init__(
            f"Remover datablock de {datablock.component_name}"
        )
        self._scene = scene
        self._datablock = datablock

    def redo(self) -> None:  # pragma: no cover
        item = self._scene.find_datablock_item(self._datablock)
        if item is not None:
            self._scene.remove_datablock(item)

    def undo(self) -> None:  # pragma: no cover
        self._scene.add_datablock(self._datablock)


class EditDataBlockLinesCommand(QUndoCommand):
    """
    v0.86: substitui as ``lines`` de um datablock (undoable).

    v0.88: usado pelo binder para atualizar APENAS lines a
    partir do template + values. ``template_lines`` permanece
    intocado (sticky). Para edits do usuário (que devem
    atualizar template + lines), use
    :class:`EditDataBlockTemplateCommand`.
    """

    def __init__(
        self, scene: PpScene, datablock: PpDataBlock,
        new_lines: list[str],
    ) -> None:
        super().__init__(
            f"Editar datablock de {datablock.component_name}"
        )
        self._scene = scene
        self._datablock = datablock
        self._old_lines = list(datablock.lines)
        self._new_lines = list(new_lines)

    def _apply(self, lines: list[str]) -> None:
        self._datablock.lines = list(lines)
        item = self._scene.find_datablock_item(self._datablock)
        if item is not None:
            item.prepareGeometryChange()
            item.sync_from_model()

    def redo(self) -> None:  # pragma: no cover
        self._apply(self._new_lines)

    def undo(self) -> None:  # pragma: no cover
        self._apply(self._old_lines)


class EditDataBlockTemplateCommand(QUndoCommand):
    """
    v0.88: substitui ``template_lines`` E ``lines`` (sincronizados)
    de um datablock — usado quando o usuário edita via dialog.

    Após este comando o datablock fica em estado "raw" (lines
    iguais ao template, placeholders visíveis). O próximo refresh
    re-renderiza lines com valores cacheados.

    Undoable: armazena snapshot das duas listas.
    """

    def __init__(
        self, scene: PpScene, datablock: PpDataBlock,
        new_template: list[str],
    ) -> None:
        super().__init__(
            f"Editar template de {datablock.component_name}"
        )
        self._scene = scene
        self._datablock = datablock
        self._old_template = list(datablock.template_lines)
        self._old_lines = list(datablock.lines)
        self._new = list(new_template)

    def _apply(
        self, template: list[str], lines: list[str],
    ) -> None:
        self._datablock.template_lines = list(template)
        self._datablock.lines = list(lines)
        item = self._scene.find_datablock_item(self._datablock)
        if item is not None:
            item.prepareGeometryChange()
            item.sync_from_model()

    def redo(self) -> None:  # pragma: no cover
        # Após edit: template = lines = novo texto.
        self._apply(self._new, self._new)

    def undo(self) -> None:  # pragma: no cover
        self._apply(self._old_template, self._old_lines)


# ---------------------------------------------------------------------------
# v3.1.3 Sub-sprint A — Tag commands (PTW Tutorial §Part 1 p.35-52)
# ---------------------------------------------------------------------------


class AddLinkTagCommand(QUndoCommand):
    """Adiciona :class:`PpLinkTag` ao projeto.

    v3.1.3 Sub-sprint A. PpLinkTag persistido em project.link_tags;
    QGraphicsItem rendering via :class:`LinkTagGraphicsItem` (separate).

    References
    ----------
    PTW Tutorial v8.0 §Part 1 p.35-42.
    """

    def __init__(
        self,
        scene: PpScene,
        tag: PpLinkTag,
        text: Optional[str] = None,
    ) -> None:
        super().__init__(text or f"Adicionar Link Tag '{tag.label}'")
        self._scene = scene
        self._tag = tag

    def redo(self) -> None:  # pragma: no cover
        self._scene.add_link_tag(self._tag)

    def undo(self) -> None:  # pragma: no cover
        self._scene.remove_link_tag(self._tag)


class RemoveLinkTagCommand(QUndoCommand):
    """Remove :class:`PpLinkTag` do projeto."""

    def __init__(
        self,
        scene: PpScene,
        tag: PpLinkTag,
        text: Optional[str] = None,
    ) -> None:
        super().__init__(text or f"Remover Link Tag '{tag.label}'")
        self._scene = scene
        self._tag = tag

    def redo(self) -> None:  # pragma: no cover
        self._scene.remove_link_tag(self._tag)

    def undo(self) -> None:  # pragma: no cover
        self._scene.add_link_tag(self._tag)


class AddLegendTagCommand(QUndoCommand):
    """Adiciona :class:`PpLegendTag` ao projeto.

    References
    ----------
    PTW Tutorial v8.0 §Part 1 p.43-52.
    """

    def __init__(
        self,
        scene: PpScene,
        tag: PpLegendTag,
        text: Optional[str] = None,
    ) -> None:
        super().__init__(text or f"Adicionar Legend Tag '{tag.text}'")
        self._scene = scene
        self._tag = tag

    def redo(self) -> None:  # pragma: no cover
        self._scene.add_legend_tag(self._tag)

    def undo(self) -> None:  # pragma: no cover
        self._scene.remove_legend_tag(self._tag)


class RemoveLegendTagCommand(QUndoCommand):
    """Remove :class:`PpLegendTag` do projeto."""

    def __init__(
        self,
        scene: PpScene,
        tag: PpLegendTag,
        text: Optional[str] = None,
    ) -> None:
        super().__init__(text or f"Remover Legend Tag '{tag.text}'")
        self._scene = scene
        self._tag = tag

    def redo(self) -> None:  # pragma: no cover
        self._scene.remove_legend_tag(self._tag)

    def undo(self) -> None:  # pragma: no cover
        self._scene.add_legend_tag(self._tag)
