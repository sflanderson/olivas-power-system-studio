"""
app.gui.schematic_pp — editor visual do pré-processador (Qucs-like).

Uso típico:

.. code-block:: python

    from PySide6.QtWidgets import QApplication
    from app.gui.schematic_pp import PpEditor

    app = QApplication([])
    editor = PpEditor()
    editor.resize(1200, 700)
    editor.show()
    editor.add_component_by_type("R")
    app.exec()

Componentes públicos:

* :class:`PpEditor` — widget top-level
* :class:`PpScene` / :class:`PpView` — Qt scene graph
* :class:`ComponentItem` / :class:`WireItem` — QGraphicsItem
  adapters que delegam ao :class:`SymbolRenderer`
* :class:`PpPalette` / :class:`PpPropertiesPanel` — sub-widgets
* :func:`snap` — snap-to-grid utilitário
"""

from __future__ import annotations

from . import commands
from .commands import (
    AddComponentCommand,
    AddWireCommand,
    EditNameCommand,
    EditPropertyCommand,
    EditVisibilityCommand,
    MirrorComponentCommand,
    MoveComponentCommand,
    RemoveComponentCommand,
    RemoveSelectionCommand,
    RemoveWireCommand,
    RotateComponentCommand,
)
from .editor import (
    PpEditor,
    PpPalette,
    PpPropertiesPanel,
)
from .items import ComponentItem, WireItem
from .scene import GRID_SIZE, PpScene, snap, snap_point
from .view import PpView

__all__ = [
    "PpEditor",
    "PpPalette",
    "PpPropertiesPanel",
    "PpScene",
    "PpView",
    "ComponentItem",
    "WireItem",
    "snap",
    "snap_point",
    "GRID_SIZE",
    "commands",
    "AddComponentCommand",
    "AddWireCommand",
    "EditNameCommand",
    "EditPropertyCommand",
    "EditVisibilityCommand",
    "MirrorComponentCommand",
    "MoveComponentCommand",
    "RemoveComponentCommand",
    "RemoveSelectionCommand",
    "RemoveWireCommand",
    "RotateComponentCommand",
]
