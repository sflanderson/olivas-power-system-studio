"""Side-by-side case comparison widget for Olivas ATP Studio."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.analysis.case_compare import CompareResult, compare_cases
from app.core.project_model import AtpProject
from app.gui.theme import DARK

MONO_FONT = "Consolas"
MONO_SIZE = 10


class CompareWidget(QWidget):
    """Widget for side-by-side comparison of two ATP cases."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cases: dict[str, AtpProject] = {}
        self._palette = DARK
        self._build_ui()

    def apply_theme(self, palette: dict[str, str]) -> None:
        """Update palette and re-render any existing comparison."""
        self._palette = palette

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Selector row
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Caso A:"))
        self.combo_a = QComboBox()
        self.combo_a.setMinimumWidth(150)
        sel_row.addWidget(self.combo_a, 1)

        sel_row.addWidget(QLabel("Caso B:"))
        self.combo_b = QComboBox()
        self.combo_b.setMinimumWidth(150)
        sel_row.addWidget(self.combo_b, 1)

        self.btn_compare = QPushButton("Comparar")
        self.btn_compare.clicked.connect(self._on_compare)
        sel_row.addWidget(self.btn_compare)

        layout.addLayout(sel_row)

        # Summary labels
        self.summary_label = QLabel("")
        layout.addWidget(self.summary_label)

        # Diff table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Categoria", "Parâmetro", "Caso A", "Caso B"])
        self.table.setFont(QFont(MONO_FONT, MONO_SIZE))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

    def update_cases(self, cases: dict[str, AtpProject]) -> None:
        """Update available cases from MainWindow."""
        self._cases = cases
        current_a = self.combo_a.currentData()
        current_b = self.combo_b.currentData()

        self.combo_a.blockSignals(True)
        self.combo_b.blockSignals(True)
        self.combo_a.clear()
        self.combo_b.clear()

        for path, proj in cases.items():
            label = Path(path).name
            self.combo_a.addItem(label, path)
            self.combo_b.addItem(label, path)

        # Restore selection
        for i in range(self.combo_a.count()):
            if self.combo_a.itemData(i) == current_a:
                self.combo_a.setCurrentIndex(i)
                break
        for i in range(self.combo_b.count()):
            if self.combo_b.itemData(i) == current_b:
                self.combo_b.setCurrentIndex(i)
                break

        # Pre-select second case if two available
        if self.combo_b.count() >= 2 and self.combo_a.currentIndex() == self.combo_b.currentIndex():
            self.combo_b.setCurrentIndex(1)

        self.combo_a.blockSignals(False)
        self.combo_b.blockSignals(False)

    def _on_compare(self) -> None:
        path_a = self.combo_a.currentData()
        path_b = self.combo_b.currentData()

        if not path_a or not path_b:
            self.summary_label.setText("Abra pelo menos dois casos para comparar.")
            return

        if path_a == path_b:
            self.summary_label.setText("Selecione dois casos diferentes.")
            return

        proj_a = self._cases.get(path_a)
        proj_b = self._cases.get(path_b)

        if not proj_a or not proj_b:
            self.summary_label.setText("Caso não encontrado.")
            return

        result = compare_cases(proj_a, proj_b)
        self._show_result(result)

    def _show_result(self, result: CompareResult) -> None:
        name_a = Path(result.file_a).name
        name_b = Path(result.file_b).name
        p = self._palette

        if not result.has_diffs:
            self.summary_label.setText(f"Nenhuma diferença entre {name_a} e {name_b}.")
            self.table.setRowCount(0)
            return

        self.summary_label.setText(
            f"{len(result.diffs)} diferença(s) entre {name_a} e {name_b}"
        )

        colors = {
            "header": QColor(p["cmp_header"]),
            "model_data": QColor(p["cmp_model_data"]),
            "use_data": QColor(p["cmp_use_data"]),
            "component": QColor(p["cmp_component"]),
        }
        default_color = QColor(p["cmp_default"])

        self.table.setRowCount(len(result.diffs))
        for row, diff in enumerate(result.diffs):
            cat_item = QTableWidgetItem(diff.category)
            color = colors.get(diff.category, default_color)
            cat_item.setBackground(color)
            self.table.setItem(row, 0, cat_item)

            self.table.setItem(row, 1, QTableWidgetItem(diff.label))

            item_a = QTableWidgetItem(diff.value_a)
            item_b = QTableWidgetItem(diff.value_b)
            if diff.value_a != diff.value_b:
                item_a.setForeground(QColor(p["cmp_diff_a"]))
                item_b.setForeground(QColor(p["cmp_diff_b"]))
            self.table.setItem(row, 2, item_a)
            self.table.setItem(row, 3, item_b)

        self.table.resizeColumnsToContents()
