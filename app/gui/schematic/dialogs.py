"""Dialogs for creating and editing schematic components.

All dialogs return data suitable for constructing or updating the
corresponding AtpProject component dataclass. None is returned on
cancel.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from app.core.project_model import (
    BranchComponent,
    SourceComponent,
    SwitchComponent,
)


# ════════════════════════════════════════════════════════════════════
# Node dialogs
# ════════════════════════════════════════════════════════════════════
class NodeDialog(QDialog):
    """Generic dialog to add or rename a node."""

    def __init__(
        self,
        parent=None,
        title: str = "Adicionar nó",
        initial: str = "",
        taken: Optional[set[str]] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(280)
        self._taken = taken or set()

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name_edit = QLineEdit(initial)
        self._name_edit.setMaxLength(6)  # ATP column-width limit
        self._name_edit.setPlaceholderText("até 6 caracteres")
        form.addRow("Nome do nó:", self._name_edit)

        self._hint = QLabel("<small>ATP permite até 6 caracteres, sem espaços.</small>")
        self._hint.setWordWrap(True)
        form.addRow(self._hint)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._try_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._name_edit.setFocus()

    def _try_accept(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._hint.setText(
                "<span style='color:#e57373'>Nome não pode ficar vazio.</span>"
            )
            return
        if " " in name or "\t" in name:
            self._hint.setText(
                "<span style='color:#e57373'>Nome não pode conter espaços.</span>"
            )
            return
        if name in self._taken:
            self._hint.setText(
                f"<span style='color:#e57373'>Nó '{name}' já existe.</span>"
            )
            return
        self.accept()

    def node_name(self) -> str:
        return self._name_edit.text().strip()


# ════════════════════════════════════════════════════════════════════
# Branch dialog
# ════════════════════════════════════════════════════════════════════
class BranchDialog(QDialog):
    """Dialog to create or edit a Branch (BranchComponent)."""

    SEMANTIC_TYPES = [
        "resistor",
        "inductor",
        "capacitor",
        "RC",
        "RL",
        "LC",
        "RLC",
        "snubber",
        "transformer",
        "line",
        "branch",
    ]

    def __init__(
        self,
        parent=None,
        node1: str = "",
        node2: str = "",
        branch: Optional[BranchComponent] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar branch" if branch else "Adicionar branch")
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._n1 = QLineEdit(branch.node1 if branch else node1)
        self._n1.setMaxLength(6)
        self._n2 = QLineEdit(branch.node2 if branch else node2)
        self._n2.setMaxLength(6)

        self._type = QComboBox()
        self._type.addItems(self.SEMANTIC_TYPES)
        if branch:
            idx = self._type.findText(branch.semantic_type)
            if idx >= 0:
                self._type.setCurrentIndex(idx)

        self._r = QLineEdit(branch.resistance.strip() if branch and branch.resistance else "")
        self._l = QLineEdit(branch.inductance.strip() if branch and branch.inductance else "")
        self._c = QLineEdit(branch.capacitance.strip() if branch and branch.capacitance else "")

        form.addRow("Nó 1:", self._n1)
        form.addRow("Nó 2:", self._n2)
        form.addRow("Tipo:", self._type)
        form.addRow("R (Ω):", self._r)
        form.addRow("L (mH):", self._l)
        form.addRow("C (µF):", self._c)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> dict:
        return {
            "node1": self._n1.text().strip(),
            "node2": self._n2.text().strip(),
            "semantic_type": self._type.currentText(),
            "resistance": self._r.text().strip() or None,
            "inductance": self._l.text().strip() or None,
            "capacitance": self._c.text().strip() or None,
        }


# ════════════════════════════════════════════════════════════════════
# Switch dialog
# ════════════════════════════════════════════════════════════════════
class SwitchDialog(QDialog):
    SEMANTIC_TYPES = [
        "switch",
        "vcb",
        "time_controlled",
        "tacs_controlled",
        "measuring",
        "systematic",
    ]

    def __init__(
        self,
        parent=None,
        node1: str = "",
        node2: str = "",
        switch: Optional[SwitchComponent] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar switch" if switch else "Adicionar switch")
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._n1 = QLineEdit(switch.node1 if switch else node1)
        self._n1.setMaxLength(6)
        self._n2 = QLineEdit(switch.node2 if switch else node2)
        self._n2.setMaxLength(6)

        self._type = QComboBox()
        self._type.addItems(self.SEMANTIC_TYPES)
        if switch:
            idx = self._type.findText(switch.semantic_type)
            if idx >= 0:
                self._type.setCurrentIndex(idx)

        self._tclose = QLineEdit(switch.t_close.strip() if switch and switch.t_close else "")
        self._topen = QLineEdit(switch.t_open.strip() if switch and switch.t_open else "")
        self._tacs = QLineEdit(switch.tacs_output if switch else "")
        self._tacs.setMaxLength(6)

        form.addRow("Nó 1:", self._n1)
        form.addRow("Nó 2:", self._n2)
        form.addRow("Tipo:", self._type)
        form.addRow("Tclose (s):", self._tclose)
        form.addRow("Topen (s):", self._topen)
        form.addRow("Saída TACS:", self._tacs)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> dict:
        return {
            "node1": self._n1.text().strip(),
            "node2": self._n2.text().strip(),
            "semantic_type": self._type.currentText(),
            "t_close": self._tclose.text().strip() or None,
            "t_open": self._topen.text().strip() or None,
            "tacs_output": self._tacs.text().strip(),
        }


# ════════════════════════════════════════════════════════════════════
# Source dialog
# ════════════════════════════════════════════════════════════════════
class SourceDialog(QDialog):
    SEMANTIC_TYPES = ["ac", "dc", "ramp", "source"]

    def __init__(
        self,
        parent=None,
        node: str = "",
        source: Optional[SourceComponent] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar fonte" if source else "Adicionar fonte")
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._node = QLineEdit(source.node if source else node)
        self._node.setMaxLength(6)

        self._type = QComboBox()
        self._type.addItems(self.SEMANTIC_TYPES)
        if source:
            idx = self._type.findText(source.semantic_type)
            if idx >= 0:
                self._type.setCurrentIndex(idx)

        self._amp = QLineEdit(source.amplitude.strip() if source and source.amplitude else "")
        self._freq = QLineEdit(source.frequency.strip() if source and source.frequency else "")
        self._phase = QLineEdit(source.phase.strip() if source and source.phase else "")
        self._tstart = QLineEdit(source.t_start.strip() if source and source.t_start else "")
        self._tstop = QLineEdit(source.t_stop.strip() if source and source.t_stop else "")

        form.addRow("Nó:", self._node)
        form.addRow("Tipo:", self._type)
        form.addRow("Amplitude (V):", self._amp)
        form.addRow("Frequência (Hz):", self._freq)
        form.addRow("Fase (°):", self._phase)
        form.addRow("T início (s):", self._tstart)
        form.addRow("T fim (s):", self._tstop)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> dict:
        return {
            "node": self._node.text().strip(),
            "semantic_type": self._type.currentText(),
            "amplitude": self._amp.text().strip() or None,
            "frequency": self._freq.text().strip() or None,
            "phase": self._phase.text().strip() or None,
            "t_start": self._tstart.text().strip() or None,
            "t_stop": self._tstop.text().strip() or None,
        }
