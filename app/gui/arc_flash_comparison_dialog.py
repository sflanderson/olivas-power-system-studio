"""
app.gui.arc_flash_comparison_dialog — Comparison Dialog 7-standard
arc-flash (v1.6.0 Sprint F).

UI dialog para invocar :func:`compare_all_standards` e mostrar
resultados side-by-side.

Padrões (paridade lessons learned v1.4.5 + v1.5.0 + v1.5.1):

* Sem QMessageBox bloqueante em testes (status via setWindowTitle)
* Auto-run com defaults didáticos no init
* Empty state explicativo quando aplicável
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.postprocessor.arc_flash_comparison import (
    compare_all_standards, ArcFlashComparison,
)


class ArcFlashComparisonDialog(QDialog):
    """
    Dialog para comparação multi-standard arc-flash.

    Inputs: V (kV), Ibf (kA), t (ms), D (mm), DC checkbox.
    Output: tabela com 7+ standards + most/least conservative +
    divergence %.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "⚖ Arc-Flash Multi-Standard Comparison — Olivas v1.6.0"
        )
        self.resize(1100, 700)
        self.setMinimumWidth(1000)

        # v1.7.0 Sprint A: maximize/minimize controls
        from app.gui.window_state_mixin import enable_window_controls
        enable_window_controls(self, settings_key="arc_flash_comparison")

        self._last_comparison: Optional[ArcFlashComparison] = None
        self._setup_ui()
        self._on_compare()   # auto-run com defaults

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(
            "<h2>⚖ Arc-Flash 7-Standard Comparison</h2>"
            "<i>Roda IEEE 1584 + NBR 17227 + EPRI + Doughty-Neal + "
            "NESC + CSA Z462 + DC para o mesmo caso. Útil para "
            "auditoria reglatória US/CA/BR.</i>"
        )
        layout.addWidget(header)

        # Inputs
        inputs_box = QGroupBox("Caso a comparar")
        f = QFormLayout(inputs_box)

        self.voltage_kV = QDoubleSpinBox()
        self.voltage_kV.setRange(0.05, 800.0)
        self.voltage_kV.setValue(0.480)
        self.voltage_kV.setSuffix(" kV (LL)")
        f.addRow("Tensão LL:", self.voltage_kV)

        self.Ibf_kA = QDoubleSpinBox()
        self.Ibf_kA.setRange(0.1, 200.0)
        self.Ibf_kA.setValue(25.0)
        self.Ibf_kA.setSuffix(" kA")
        f.addRow("I_bf (RMS):", self.Ibf_kA)

        self.clearing_time_ms = QSpinBox()
        self.clearing_time_ms.setRange(1, 10000)
        self.clearing_time_ms.setValue(200)
        self.clearing_time_ms.setSuffix(" ms")
        f.addRow("t arc clearing:", self.clearing_time_ms)

        self.working_distance_mm = QDoubleSpinBox()
        self.working_distance_mm.setRange(50.0, 5000.0)
        self.working_distance_mm.setValue(455.0)
        self.working_distance_mm.setSuffix(" mm")
        f.addRow("Distância trabalho:", self.working_distance_mm)

        self.dc_checkbox = QCheckBox("Sistema DC (in vez de AC)")
        f.addRow("", self.dc_checkbox)

        layout.addWidget(inputs_box)

        # Action buttons
        actions = QHBoxLayout()
        self.btn_compare = QPushButton("▶ Comparar todos os standards")
        self.btn_compare.setStyleSheet(
            "QPushButton { background-color: #2ca02c; "
            "color: white; font-weight: bold; padding: 4px 14px; }"
        )
        self.btn_compare.clicked.connect(self._on_compare)
        actions.addWidget(self.btn_compare)

        actions.addStretch()

        self.btn_save_txt = QPushButton("💾 Salvar TXT")
        self.btn_save_txt.clicked.connect(self._on_save_txt)
        actions.addWidget(self.btn_save_txt)

        layout.addLayout(actions)

        # Results table
        layout.addWidget(QLabel("<b>Resultados side-by-side:</b>"))
        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels([
            "Standard", "E (cal/cm²)", "AFB (mm)", "PPE/Risk", "Notas",
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.Stretch,
        )
        layout.addWidget(self.results_table, 1)

        # Footer with stats
        self.footer_label = QLabel("")
        self.footer_label.setWordWrap(True)
        layout.addWidget(self.footer_label)

        # Close
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText("Fechar")
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    # -----------------------------------------------------------------
    # Slots
    # -----------------------------------------------------------------

    def _on_compare(self) -> None:
        try:
            comparison = compare_all_standards(
                voltage_kV=self.voltage_kV.value(),
                Ibf_kA=self.Ibf_kA.value(),
                arc_clearing_time_ms=float(self.clearing_time_ms.value()),
                working_distance_mm=self.working_distance_mm.value(),
                is_dc=self.dc_checkbox.isChecked(),
            )
            self._last_comparison = comparison
            self._populate_table(comparison)
            self._update_footer(comparison)
            self.setWindowTitle(
                f"⚖ Comparison: {comparison.most_conservative} "
                f"é o mais conservador "
                f"(div {comparison.divergence_pct:.0f}%)"
            )
        except Exception as e:
            self.setWindowTitle(f"⚖ Erro: {type(e).__name__}: {e}")

    def _populate_table(self, comp: ArcFlashComparison) -> None:
        self.results_table.setRowCount(0)
        for r in comp.results:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)

            # Coluna 0: Standard
            self.results_table.setItem(
                row, 0, QTableWidgetItem(r.standard_name),
            )

            # Coluna 1: E
            E_str = (
                f"{r.incident_energy_cal_cm2:.2f}"
                if (r.applicable and r.incident_energy_cal_cm2 is not None)
                else "N/A"
            )
            self.results_table.setItem(
                row, 1, QTableWidgetItem(E_str),
            )

            # Coluna 2: AFB
            AFB_str = (
                f"{r.arc_flash_boundary_mm:.0f}"
                if (r.applicable and r.arc_flash_boundary_mm is not None)
                else "N/A"
            )
            self.results_table.setItem(
                row, 2, QTableWidgetItem(AFB_str),
            )

            # Coluna 3: PPE
            self.results_table.setItem(
                row, 3, QTableWidgetItem(r.ppe_category or "—"),
            )

            # Coluna 4: notas
            self.results_table.setItem(
                row, 4, QTableWidgetItem(r.notes or ""),
            )

    def _update_footer(self, comp: ArcFlashComparison) -> None:
        applicable_count = sum(1 for r in comp.results if r.applicable)
        warn = ""
        if comp.divergence_pct > 50.0:
            warn = (
                "<br><span style='color:red;'>⚠ Divergência > 50% — "
                "investigar qual método é mais aplicável ao caso.</span>"
            )
        self.footer_label.setText(
            f"<b>{applicable_count}/{len(comp.results)} standards aplicáveis.</b><br>"
            f"Mais conservador: <b>{comp.most_conservative}</b><br>"
            f"Menos conservador: {comp.least_conservative}<br>"
            f"Divergência: {comp.divergence_pct:.1f}%{warn}"
        )

    def _on_save_txt(self) -> None:
        if self._last_comparison is None:
            self.setWindowTitle(
                "⚖ Compare antes de salvar"
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar comparison TXT",
            "ArcFlash_Comparison.txt", "Texto (*.txt)",
        )
        if not path:
            return
        Path(path).write_text(
            self._last_comparison.summary(), encoding="utf-8",
        )
        self.setWindowTitle(f"⚖ TXT salvo: {Path(path).name}")
