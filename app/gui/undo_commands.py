"""
app.gui.undo_commands — QUndoCommand para edits no MainWindow
(v0.28.3-PRO Onda 3.3).

Antes: edits em data_table / input_table / output_table /
model_data_table mutavam dataclasses sem QUndoStack — ações
não-reversíveis. PpEditor já tinha QUndoStack, mas era
desconectado do resto.

Agora: classes ``CellEditCommand`` e seus parentes encapsulam
cada edit em QUndoCommand. ``MainWindow`` tem ``_undo_stack``
global wired para Ctrl+Z / Ctrl+Y (via QUndoStack signals
e QAction).
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from PySide6.QtGui import QUndoCommand


class CellEditCommand(QUndoCommand):
    """
    Comando de edit de uma célula em uma data_table.

    Constructor recebe ``getter`` e ``setter`` callables que
    leem/escrevem o valor da célula. Isso evita acoplamento
    forte ao dataclass específico — qualquer cell pode usar
    este comando passando lambdas apropriadas.

    Parameters
    ----------
    description:
        Texto do undo (mostrado em menu Edit).
    getter:
        ``() → Any`` — lê o valor atual.
    setter:
        ``(Any) → None`` — escreve o valor.
    new_value:
        Valor novo a aplicar.
    on_change:
        Opcional: callback chamado após aplicar (refresh UI,
        marcar modificado, etc).
    """

    def __init__(
        self,
        description: str,
        getter: Callable[[], Any],
        setter: Callable[[Any], None],
        new_value: Any,
        on_change: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(description)
        self._getter = getter
        self._setter = setter
        self._new_value = new_value
        self._old_value: Any = None
        self._on_change = on_change
        self._first_redo = True

    def redo(self) -> None:
        """Aplica novo valor (1ª vez registra old)."""
        if self._first_redo:
            self._old_value = self._getter()
            self._first_redo = False
        self._setter(self._new_value)
        if self._on_change is not None:
            self._on_change()

    def undo(self) -> None:
        """Restaura valor antigo."""
        self._setter(self._old_value)
        if self._on_change is not None:
            self._on_change()
