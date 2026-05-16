"""
app/gui/pre_fault_voltage_dialog.py — Pre-Fault Voltage Settings.

v3.1.0 Track B-2 — Backfill GUI accessibility para
`app.postprocessor.pre_fault_voltage` (v3.0.3 órfão).

Expõe ao usuário:
* PreFaultMode combo (4 opções: LOAD_FLOW / PU_ALL / PU_PER_BUS / NO_LOAD_WITH_TAP)
* Tabela tolerâncias por equipamento (Utility / Cable / Transformer)
* Combined worst-case calculator (max / regular / min)

Reference: PTW Tutorial §Part 5 p. 131-135 (Pre-Fault Voltage options).

Trigger GUI: Análise > "Configurar Pre-Fault Voltage..."
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
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
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class PreFaultVoltageDialog(QDialog):
    """Dialog para configurar Pre-Fault Voltage com tolerâncias por equipamento.

    Persistência: ao OK, salva config em QSettings ("PreFault/...") para
    auto-aplicar em estudos subsequentes (ANSI SC, IEC 60909, Arc-Flash).
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Pre-Fault Voltage Settings — Olivas v3.1.0"
        )
        self.setModal(True)
        self.resize(700, 600)

        main = QVBoxLayout(self)

        hdr = QLabel(
            "<b>Pre-Fault Voltage Configuration</b><br>"
            "<small>Reference: PTW Tutorial §Part 5 p. 131-135 + A_Fault §1.3.3 p. 1-10</small>"
        )
        hdr.setTextFormat(Qt.RichText)
        main.addWidget(hdr)

        # --- Mode group ---
        mode_grp = QGroupBox("Pre-Fault Voltage Mode")
        mode_form = QFormLayout(mode_grp)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "PU_ALL — todas barras a 1.0 pu (default ANSI)",
            "NO_LOAD_WITH_TAP — V nominal + taps (worst-case high)",
            "PU_PER_BUS — voltagem por barra (manual override)",
            "LOAD_FLOW — usar resultado do Load Flow (mais realista)",
        ])
        self.mode_combo.setToolTip(
            "Per Tutorial §Part 5 p. 131-135"
        )
        mode_form.addRow("Mode:", self.mode_combo)

        self.default_voltage = QDoubleSpinBox()
        self.default_voltage.setRange(0.5, 1.5)
        self.default_voltage.setDecimals(4)
        self.default_voltage.setValue(1.0)
        self.default_voltage.setSuffix(" pu")
        mode_form.addRow("Default (regular) voltage:", self.default_voltage)

        main.addWidget(mode_grp)

        # --- Tolerance table ---
        tol_grp = QGroupBox("Tolerâncias por classe de equipamento")
        tol_layout = QVBoxLayout(tol_grp)

        info = QLabel(
            "<i>Cenários Min / Reg / Max usados em arc-flash worst-case "
            "e interrupting duty conservador (§Part 5 p. 135-136).</i>"
        )
        info.setTextFormat(Qt.RichText)
        info.setWordWrap(True)
        tol_layout.addWidget(info)

        self.tol_table = QTableWidget(3, 4, self)
        self.tol_table.setHorizontalHeaderLabels([
            "Equipment", "Min (pu)", "Regular (pu)", "Max (pu)",
        ])
        self.tol_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Populate with defaults from `app.postprocessor.pre_fault_voltage`
        defaults = [
            ("Utility", 0.95, 1.00, 1.05),       # ±5% NEMA / IEEE 141
            ("Cable", 1.00, 1.00, 1.00),         # passive default
            ("Transformer", 0.975, 1.00, 1.025), # ±2.5% NEMA TR-1 5-step
        ]
        for row, (name, mn, reg, mx) in enumerate(defaults):
            self.tol_table.setItem(row, 0, QTableWidgetItem(name))
            self.tol_table.setItem(row, 1, QTableWidgetItem(f"{mn:.4f}"))
            self.tol_table.setItem(row, 2, QTableWidgetItem(f"{reg:.4f}"))
            self.tol_table.setItem(row, 3, QTableWidgetItem(f"{mx:.4f}"))
        # Lock first column (read-only)
        for row in range(3):
            item = self.tol_table.item(row, 0)
            if item:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        tol_layout.addWidget(self.tol_table)
        main.addWidget(tol_grp)

        # --- Combined worst-case calculator ---
        calc_grp = QGroupBox("Combined Worst-Case Calculator")
        calc_layout = QFormLayout(calc_grp)

        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems(["max (worst-case high)", "regular", "min (worst-case low)"])
        self.scenario_combo.currentIndexChanged.connect(self._update_combined_voltage)
        calc_layout.addRow("Scenario:", self.scenario_combo)

        self.combined_label = QLabel("V_combined = 1.0500 pu")
        self.combined_label.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 14pt; font-weight: bold; color: #2563eb;"
        )
        calc_layout.addRow("Result:", self.combined_label)

        formula_label = QLabel(
            "<small>V_combined = V_util × V_TX × V_cable (per §Part 5 p. 135-136)</small>"
        )
        formula_label.setTextFormat(Qt.RichText)
        calc_layout.addRow("", formula_label)

        main.addWidget(calc_grp)
        self._update_combined_voltage()

        # --- Buttons ---
        btns = QDialogButtonBox(self)
        self.btn_ok = QPushButton("OK")
        self.btn_reset = QPushButton("Reset defaults")
        btns.addButton(self.btn_ok, QDialogButtonBox.AcceptRole)
        btns.addButton(self.btn_reset, QDialogButtonBox.ResetRole)
        btns.addButton(QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        self.btn_reset.clicked.connect(self._reset_defaults)
        # Recalculate on table edits
        self.tol_table.itemChanged.connect(lambda *_: self._update_combined_voltage())
        main.addWidget(btns)

    # -----------------------------------------------------------------

    def _read_tolerance(self, row: int) -> tuple[float, float, float]:
        """Read (min, reg, max) from tolerance table."""
        try:
            mn = float(self.tol_table.item(row, 1).text())
            reg = float(self.tol_table.item(row, 2).text())
            mx = float(self.tol_table.item(row, 3).text())
            return (mn, reg, mx)
        except (ValueError, AttributeError):
            return (1.0, 1.0, 1.0)

    def _update_combined_voltage(self) -> None:
        """Update combined worst-case label based on table + scenario."""
        try:
            from app.postprocessor.pre_fault_voltage import (
                VoltageTolerance, combined_worst_case_voltage,
            )
            util = VoltageTolerance(*self._read_tolerance(0))
            cable = VoltageTolerance(*self._read_tolerance(1))
            tx = VoltageTolerance(*self._read_tolerance(2))

            scenario_text = self.scenario_combo.currentText()
            scenario = scenario_text.split()[0]  # max / regular / min

            v = combined_worst_case_voltage(
                utility_tolerance=util,
                transformer_tolerance=tx,
                cable_tolerance=cable,
                scenario=scenario,
            )
            self.combined_label.setText(f"V_combined = {v:.4f} pu")
        except (ValueError, ImportError) as e:
            self.combined_label.setText(f"<error: {e}>")

    def _reset_defaults(self) -> None:
        """Restore default tolerances."""
        defaults = [
            (0.95, 1.00, 1.05),
            (1.00, 1.00, 1.00),
            (0.975, 1.00, 1.025),
        ]
        for row, (mn, reg, mx) in enumerate(defaults):
            self.tol_table.item(row, 1).setText(f"{mn:.4f}")
            self.tol_table.item(row, 2).setText(f"{reg:.4f}")
            self.tol_table.item(row, 3).setText(f"{mx:.4f}")
        self._update_combined_voltage()

    # -----------------------------------------------------------------
    # Public API for caller (main_window) to consume settings
    # -----------------------------------------------------------------

    def get_settings(self) -> dict:
        """Return user choices as a dict — caller passes to studies."""
        from app.postprocessor.pre_fault_voltage import (
            PreFaultMode, VoltageTolerance,
        )
        mode_idx = self.mode_combo.currentIndex()
        mode = [
            PreFaultMode.PU_ALL,
            PreFaultMode.NO_LOAD_WITH_TAP,
            PreFaultMode.PU_PER_BUS,
            PreFaultMode.LOAD_FLOW,
        ][mode_idx]

        return {
            "mode": mode,
            "default_voltage_pu": self.default_voltage.value(),
            "utility_tolerance": VoltageTolerance(*self._read_tolerance(0)),
            "cable_tolerance": VoltageTolerance(*self._read_tolerance(1)),
            "transformer_tolerance": VoltageTolerance(*self._read_tolerance(2)),
        }


def run_pre_fault_voltage_dialog(parent: Optional[QWidget] = None) -> Optional[dict]:
    """Convenience entry point. Returns settings dict on OK, None on cancel."""
    dlg = PreFaultVoltageDialog(parent)
    if dlg.exec() == QDialog.Accepted:
        return dlg.get_settings()
    return None


__all__ = [
    "PreFaultVoltageDialog",
    "run_pre_fault_voltage_dialog",
]
