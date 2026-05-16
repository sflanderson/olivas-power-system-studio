"""Interactive waveform viewer for Olivas ATP Studio.

Displays .pl4 simulation results as time-domain plots using matplotlib
embedded in PySide6. Supports multi-variable selection, zoom, pan,
cursor readout and grid toggle.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.simulation.results_reader import AtpResults
from app.gui.theme import DARK

MONO_FONT = "Consolas"


class WaveformWidget(QWidget):
    """Interactive waveform viewer with variable selector and matplotlib canvas."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: Optional[AtpResults] = None
        self._palette = DARK
        self._build_ui()

    def apply_theme(self, palette: dict[str, str]) -> None:
        """Update palette and re-render if results are loaded."""
        self._palette = palette
        if self._results is not None:
            self._on_plot()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # --- Left: variable selector ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        left_layout.addWidget(QLabel("Variáveis:"))

        self.var_list = QListWidget()
        self.var_list.setFont(QFont(MONO_FONT, 9))
        self.var_list.setSelectionMode(QListWidget.ExtendedSelection)
        left_layout.addWidget(self.var_list)

        # Controls
        btn_row = QHBoxLayout()
        self.btn_plot = QPushButton("Plotar")
        self.btn_plot.clicked.connect(self._on_plot)
        btn_row.addWidget(self.btn_plot)

        self.btn_clear = QPushButton("Limpar")
        self.btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(self.btn_clear)
        left_layout.addLayout(btn_row)

        self.chk_grid = QCheckBox("Grade")
        self.chk_grid.setChecked(True)
        self.chk_grid.stateChanged.connect(self._on_plot)
        left_layout.addWidget(self.chk_grid)

        self.chk_legend = QCheckBox("Legenda")
        self.chk_legend.setChecked(True)
        self.chk_legend.stateChanged.connect(self._on_plot)
        left_layout.addWidget(self.chk_legend)

        self.cursor_label = QLabel("")
        self.cursor_label.setFont(QFont(MONO_FONT, 9))
        left_layout.addWidget(self.cursor_label)

        self.info_label = QLabel("Nenhum resultado carregado.")
        self.info_label.setWordWrap(True)
        self.info_label.setFont(QFont(MONO_FONT, 8))
        left_layout.addWidget(self.info_label)

        left.setMaximumWidth(220)
        splitter.addWidget(left)

        # --- Right: matplotlib canvas ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.figure.set_facecolor(self._palette["mpl_face"])
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

        self.toolbar = NavigationToolbar2QT(self.canvas, right)
        right_layout.addWidget(self.toolbar)
        right_layout.addWidget(self.canvas)

        splitter.addWidget(right)
        splitter.setSizes([200, 800])

    def load_results(self, results: AtpResults) -> None:
        """Load PL4 results and populate variable list."""
        self._results = results
        self.var_list.clear()

        for var_name in results.variables:
            item = QListWidgetItem(var_name)
            self.var_list.addItem(item)

        t0, t1 = results.get_time_range()
        self.info_label.setText(
            f"{len(results.variables)} variáveis\n"
            f"{results.n_steps} passos\n"
            f"dt = {results.delta_t:.2e} s\n"
            f"t = [{t0:.6f}, {t1:.6f}] s"
        )

        # Auto-select first variable and plot
        if self.var_list.count() > 0:
            self.var_list.item(0).setSelected(True)
            self._on_plot()

    def clear_results(self) -> None:
        """Clear all data and plots."""
        self._results = None
        self.var_list.clear()
        self.info_label.setText("Nenhum resultado carregado.")
        self._on_clear()

    def _get_selected_vars(self) -> list[str]:
        return [item.text() for item in self.var_list.selectedItems()]

    def _on_plot(self) -> None:
        if self._results is None:
            return

        selected = self._get_selected_vars()
        if not selected:
            return

        p = self._palette
        self.figure.clear()
        self.figure.set_facecolor(p["mpl_face"])
        ax = self.figure.add_subplot(111)

        # Apply theme to axes
        ax.set_facecolor(p["mpl_axes"])
        ax.tick_params(colors=p["mpl_text"], labelsize=8)
        ax.xaxis.label.set_color(p["mpl_text"])
        ax.yaxis.label.set_color(p["mpl_text"])
        ax.title.set_color(p["mpl_title"])
        for spine in ax.spines.values():
            spine.set_color(p["mpl_spine"])

        time = self._results.time
        for var_name in selected:
            data = self._results.data.get(var_name, [])
            if data and len(data) == len(time):
                ax.plot(time, data, linewidth=0.8, label=var_name)

        ax.set_xlabel("Tempo (s)", fontsize=9)
        ax.set_ylabel("Valor", fontsize=9)

        if len(selected) == 1:
            ax.set_title(selected[0], fontsize=10)
        else:
            ax.set_title(f"{len(selected)} variáveis", fontsize=10)

        if self.chk_grid.isChecked():
            ax.grid(True, color=p["mpl_grid"], linewidth=0.5, alpha=0.7)

        if self.chk_legend.isChecked() and len(selected) > 1:
            ax.legend(fontsize=7, loc="upper right", framealpha=0.7,
                      facecolor=p["mpl_legend_face"], edgecolor=p["mpl_legend_edge"],
                      labelcolor=p["mpl_text"])

        self.figure.tight_layout()
        self.canvas.draw()

    def _on_clear(self) -> None:
        self.figure.clear()
        self.canvas.draw()
        self.cursor_label.setText("")

    def _on_mouse_move(self, event) -> None:
        if event.inaxes is not None:
            self.cursor_label.setText(
                f"t = {event.xdata:.6e}\ny = {event.ydata:.4e}"
            )
