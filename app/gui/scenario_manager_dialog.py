"""
app/gui/scenario_manager_dialog.py — Scenario Manager Dialog.

v3.5.0 — paridade PTW Tutorial §Part 11 p.319-347.

Expõe ao usuário:
* Lista de scenarios + ativo destacado em PTW peach color
* Clone Base / Clone Active
* Activate
* Diff vs Base (added / removed / modified)
* Promote to Base (per PromotionMode)

Trigger GUI: Ferramentas > "Scenario Manager..."
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.preprocessor.scenarios import (
    PTW_PEACH_COLOR, PpScenario, PromotionMode, ScenarioManager,
)


class ScenarioManagerDialog(QDialog):
    """Dialog para gerenciar scenarios (PTW Tutorial §Part 11 p.319-347).

    Workflow básico:
    1. Project ativo no Olivas → Base scenario auto-criado
    2. User clica "Clone Active" → novo branch
    3. Edita schematic no novo branch (independente da base)
    4. "Diff vs Base" → mostra changes
    5. "Promote to Base" → merge changes back
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        manager: Optional[ScenarioManager] = None,
        project=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Scenario Manager — Olivas v3.5.0")
        self.setModal(True)
        self.resize(800, 600)

        # If no manager provided, create one with project as base
        if manager is None:
            manager = ScenarioManager()
            if project is not None:
                base = PpScenario.create_base(project, name="Base")
                manager.add(base)
        self._manager = manager

        main = QVBoxLayout(self)

        hdr = QLabel(
            "<b>Scenario Manager</b><br>"
            "<small>Reference: PTW Tutorial §Part 11 p.319-347 — "
            "branches paralelos do mesmo projeto</small>"
        )
        hdr.setTextFormat(Qt.RichText)
        main.addWidget(hdr)

        # ===== Scenarios list =====
        list_grp = QGroupBox("Scenarios")
        list_layout = QVBoxLayout(list_grp)

        self.scenarios_list = QListWidget()
        list_layout.addWidget(self.scenarios_list, 1)

        # Action buttons
        actions_row = QHBoxLayout()
        self.btn_clone = QPushButton("⎘ Clone Active")
        self.btn_clone.setToolTip("Clone the active scenario as a new branch")
        self.btn_clone.clicked.connect(self._on_clone)
        actions_row.addWidget(self.btn_clone)

        self.btn_activate = QPushButton("▶ Activate")
        self.btn_activate.clicked.connect(self._on_activate)
        actions_row.addWidget(self.btn_activate)

        self.btn_diff = QPushButton("⚖ Diff vs Base")
        self.btn_diff.clicked.connect(self._on_diff)
        actions_row.addWidget(self.btn_diff)

        self.btn_promote = QPushButton("⇧ Promote to Base")
        self.btn_promote.clicked.connect(self._on_promote)
        actions_row.addWidget(self.btn_promote)

        list_layout.addLayout(actions_row)
        main.addWidget(list_grp)

        # ===== Diff output =====
        diff_grp = QGroupBox("Diff result")
        diff_layout = QVBoxLayout(diff_grp)
        self.diff_text = QPlainTextEdit()
        self.diff_text.setReadOnly(True)
        self.diff_text.setFont(QFont("Consolas", 10))
        diff_layout.addWidget(self.diff_text)
        main.addWidget(diff_grp)

        # ===== Promotion mode selector =====
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Default promotion mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "ALL_FIELDS (overwrite base)",
            "UNMODIFIED_ONLY (additive)",
            "DO_NOT_PROMOTE (read-only)",
        ])
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch(1)
        main.addLayout(mode_row)

        # ===== Close button =====
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        main.addWidget(bb)

        self._refresh_list()

    def _refresh_list(self) -> None:
        """Repopulate the list widget from manager state."""
        self.scenarios_list.clear()
        for s in self._manager.scenarios:
            label = f"{s.name}"
            if s.is_base():
                label = f"📦 {label} (BASE)"
            elif s.id == self._manager.active_id:
                label = f"▶ {label} (active)"
            else:
                label = f"  {label}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, s.id)
            # Highlight active with peach color
            if s.id == self._manager.active_id:
                item.setBackground(QBrush(QColor(PTW_PEACH_COLOR)))
            self.scenarios_list.addItem(item)

    def _selected_scenario_id(self) -> Optional[str]:
        item = self.scenarios_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    # -----------------------------------------------------------------

    def _on_clone(self) -> None:
        """Clone the active scenario as a new branch."""
        active = self._manager.get_active()
        if active is None:
            QMessageBox.warning(
                self, "Sem scenario ativo",
                "Selecione um scenario para clonar.",
            )
            return
        name, ok = QInputDialog.getText(
            self, "Clone Scenario",
            f"Nome do novo branch (clone de '{active.name}'):",
            text=f"{active.name} — clone",
        )
        if not ok or not name.strip():
            return
        new_scenario = self._manager.clone_active(name.strip())
        if new_scenario is None:
            return
        self._refresh_list()

    def _on_activate(self) -> None:
        sid = self._selected_scenario_id()
        if sid is None:
            QMessageBox.warning(
                self, "Selecione",
                "Selecione um scenario na lista para ativar.",
            )
            return
        self._manager.activate(sid)
        self._refresh_list()

    def _on_diff(self) -> None:
        sid = self._selected_scenario_id()
        if sid is None:
            QMessageBox.warning(
                self, "Selecione",
                "Selecione um scenario para fazer diff vs Base.",
            )
            return
        diff = self._manager.diff_with_base(sid)
        scenario = self._manager.find(sid)
        lines = [
            "=" * 60,
            f" Diff: '{scenario.name if scenario else sid}' vs Base",
            f" Reference: PTW Tutorial §Part 11 p.336-337",
            "=" * 60,
            "",
            f"  Added ({len(diff['added'])}):",
        ]
        for n in diff["added"]:
            lines.append(f"    + {n}")
        lines.append(f"  Removed ({len(diff['removed'])}):")
        for n in diff["removed"]:
            lines.append(f"    - {n}")
        lines.append(f"  Modified ({len(diff['modified'])}):")
        for n in diff["modified"]:
            lines.append(f"    ~ {n}")
        self.diff_text.setPlainText("\n".join(lines))

    def _on_promote(self) -> None:
        sid = self._selected_scenario_id()
        if sid is None:
            QMessageBox.warning(
                self, "Selecione",
                "Selecione um scenario para promover.",
            )
            return
        scenario = self._manager.find(sid)
        if scenario is None or scenario.is_base():
            QMessageBox.information(
                self, "Sem ação",
                "Não é possível promover BASE.",
            )
            return
        # Apply mode from combo
        mode_idx = self.mode_combo.currentIndex()
        modes = [
            PromotionMode.ALL_FIELDS,
            PromotionMode.UNMODIFIED_ONLY,
            PromotionMode.DO_NOT_PROMOTE,
        ]
        scenario.promotion_mode = modes[mode_idx]
        ok = self._manager.promote_to_base(sid)
        if ok:
            QMessageBox.information(
                self, "Promotion OK",
                f"Scenario '{scenario.name}' promoted to Base "
                f"(mode: {scenario.promotion_mode.value}).",
            )
            self._refresh_list()
        else:
            QMessageBox.warning(
                self, "Promotion bloqueada",
                f"Scenario '{scenario.name}' não foi promovido "
                f"(mode: {scenario.promotion_mode.value}).",
            )

    @property
    def manager(self) -> ScenarioManager:
        return self._manager


def run_scenario_manager_dialog(
    parent: Optional[QWidget] = None,
    *,
    manager: Optional[ScenarioManager] = None,
    project=None,
) -> Optional[ScenarioManager]:
    """Convenience entry. Returns the manager (potentially modified)."""
    dlg = ScenarioManagerDialog(parent, manager=manager, project=project)
    dlg.exec()
    return dlg.manager


__all__ = [
    "ScenarioManagerDialog",
    "run_scenario_manager_dialog",
]
