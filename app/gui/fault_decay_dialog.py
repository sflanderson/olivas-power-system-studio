"""
app/gui/fault_decay_dialog.py — Fault Current Decay over time.

v3.1.0 Track B-4 — Backfill GUI accessibility para
`app.postprocessor.fault_decay` (v3.0.3 órfão).

Expõe ao usuário:
* Generator/Sync motor exponential decay (subtransient → steady-state)
* Induction motor exclude after N cycles + hp threshold
* Recalculate trip time using time-decayed current

Reference: PTW Tutorial §Part 5 p. 136-138.

Trigger GUI: Análise > "Decay temporal de falta..."
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class FaultDecayDialog(QDialog):
    """Dialog para análise temporal de fault current decay.

    Reference: PTW Tutorial §Part 5 p. 136-138.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Fault Current Decay (Gen/Sync/Induction) — Olivas v3.1.0")
        self.setModal(True)
        self.resize(750, 700)

        main = QVBoxLayout(self)

        hdr = QLabel(
            "<b>Fault Current Decay over time</b><br>"
            "<small>Reference: PTW Tutorial §Part 5 p. 136-138 + IEEE Std 141 §4.6</small>"
        )
        hdr.setTextFormat(Qt.RichText)
        main.addWidget(hdr)

        # === Source Type ===
        src_grp = QGroupBox("Fault current source")
        src_form = QFormLayout(src_grp)

        self.source_combo = QComboBox()
        self.source_combo.addItems([
            "Generator (synchronous decay sub→steady)",
            "Sync motor (similar to generator)",
            "Induction motor (1-2 cycles flux loss)",
        ])
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        src_form.addRow("Source:", self.source_combo)

        main.addWidget(src_grp)

        # === Decay parameters (gen/sync only) ===
        self.decay_grp = QGroupBox("Exponential decay (generator/sync)")
        decay_form = QFormLayout(self.decay_grp)

        self.i_subtransient = QDoubleSpinBox()
        self.i_subtransient.setRange(0.0, 10000.0)
        self.i_subtransient.setDecimals(2)
        self.i_subtransient.setValue(1000.0)
        self.i_subtransient.setSuffix(" %")
        self.i_subtransient.setToolTip("Subtransient as % of rated (e.g., 1000% = 10×)")
        decay_form.addRow("I_subtransient:", self.i_subtransient)

        self.i_steady = QDoubleSpinBox()
        self.i_steady.setRange(0.0, 10000.0)
        self.i_steady.setDecimals(2)
        self.i_steady.setValue(300.0)
        self.i_steady.setSuffix(" %")
        decay_form.addRow("I_steady:", self.i_steady)

        self.tau_cycles = QDoubleSpinBox()
        self.tau_cycles.setRange(0.1, 100.0)
        self.tau_cycles.setDecimals(2)
        self.tau_cycles.setValue(10.0)
        self.tau_cycles.setSuffix(" cycles")
        self.tau_cycles.setToolTip("Decay time constant (5-15 typical)")
        decay_form.addRow("τ (decay constant):", self.tau_cycles)

        main.addWidget(self.decay_grp)

        # === Induction motor parameters ===
        self.ind_grp = QGroupBox("Induction motor exclude rule")
        ind_form = QFormLayout(self.ind_grp)

        self.ind_hp = QDoubleSpinBox()
        self.ind_hp.setRange(0.1, 100000.0)
        self.ind_hp.setDecimals(1)
        self.ind_hp.setValue(100.0)
        self.ind_hp.setSuffix(" hp")
        ind_form.addRow("Motor hp:", self.ind_hp)

        self.ind_hp_threshold = QDoubleSpinBox()
        self.ind_hp_threshold.setRange(0.1, 1000.0)
        self.ind_hp_threshold.setDecimals(1)
        self.ind_hp_threshold.setValue(50.0)
        self.ind_hp_threshold.setSuffix(" hp")
        self.ind_hp_threshold.setToolTip(
            "Per A_Fault §1.2.5 p. 1-8: < 50 hp neglected first-cycle"
        )
        ind_form.addRow("hp threshold:", self.ind_hp_threshold)

        self.ind_cycle = QDoubleSpinBox()
        self.ind_cycle.setRange(0.0, 1000.0)
        self.ind_cycle.setDecimals(1)
        self.ind_cycle.setValue(5.0)
        self.ind_cycle.setSuffix(" cycles")
        ind_form.addRow("Time after fault:", self.ind_cycle)

        self.ind_grp.setVisible(False)
        main.addWidget(self.ind_grp)

        # === Decay table ===
        layout_btn = QHBoxLayout()
        btn_table = QPushButton("Generate decay table (10 points)")
        btn_table.clicked.connect(self._generate_table)
        layout_btn.addWidget(btn_table)
        layout_btn.addStretch(1)
        main.addLayout(layout_btn)

        self.decay_table = QTableWidget(0, 3, self)
        self.decay_table.setHorizontalHeaderLabels([
            "Time (cycles)", "I (% rated)", "Note",
        ])
        self.decay_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.decay_table.setMaximumHeight(280)
        main.addWidget(self.decay_table, 1)

        # === Buttons ===
        btns = QDialogButtonBox(QDialogButtonBox.Close, self)
        btns.rejected.connect(self.reject)
        main.addWidget(btns)

        self._on_source_changed(0)
        self._generate_table()

    def _on_source_changed(self, idx: int) -> None:
        """Show/hide groups based on source type."""
        is_induction = (idx == 2)
        self.decay_grp.setVisible(not is_induction)
        self.ind_grp.setVisible(is_induction)
        self._generate_table()

    def _generate_table(self) -> None:
        """Generate 10-point decay table for the selected source."""
        from app.postprocessor.fault_decay import (
            gen_sync_decay_step, induction_motor_excluded,
        )
        idx = self.source_combo.currentIndex()
        is_induction = (idx == 2)
        self.decay_table.setRowCount(0)

        if is_induction:
            # Induction motor table — show pass/fail at various cycle marks
            cycle_points = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
            for c in cycle_points:
                excluded = induction_motor_excluded(
                    hp=self.ind_hp.value(),
                    cycles_after_fault=c,
                    hp_threshold=self.ind_hp_threshold.value(),
                )
                row = self.decay_table.rowCount()
                self.decay_table.insertRow(row)
                self.decay_table.setItem(row, 0, QTableWidgetItem(f"{c:.1f}"))
                self.decay_table.setItem(row, 1, QTableWidgetItem(
                    "0.0 (excluded)" if excluded else "100.0 (included)"
                ))
                self.decay_table.setItem(row, 2, QTableWidgetItem(
                    "EXCLUDED" if excluded else "Active"
                ))
        else:
            # Gen/Sync exponential decay
            i_sub = self.i_subtransient.value()
            i_ss = self.i_steady.value()
            tau = self.tau_cycles.value()
            cycle_points = [0.0, 1.0, 2.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0, 100.0]
            for c in cycle_points:
                try:
                    i_pct = gen_sync_decay_step(
                        i_subtransient_pct=i_sub,
                        i_steady_pct=i_ss,
                        decay_time_constant_cycles=tau,
                        current_cycle=c,
                    )
                    note = ""
                    if c == 0.0:
                        note = "Initial (subtransient)"
                    elif c >= tau * 5:
                        note = "≈ steady-state"
                    elif abs(c - tau) < 0.01:
                        note = "1 time constant (1/e decay)"
                    row = self.decay_table.rowCount()
                    self.decay_table.insertRow(row)
                    self.decay_table.setItem(row, 0, QTableWidgetItem(f"{c:.1f}"))
                    self.decay_table.setItem(row, 1, QTableWidgetItem(f"{i_pct:.2f}"))
                    self.decay_table.setItem(row, 2, QTableWidgetItem(note))
                except ValueError:
                    pass


def run_fault_decay_dialog(parent: Optional[QWidget] = None) -> None:
    dlg = FaultDecayDialog(parent)
    dlg.exec()


__all__ = [
    "FaultDecayDialog",
    "run_fault_decay_dialog",
]
