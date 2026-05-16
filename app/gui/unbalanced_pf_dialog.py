"""
app/gui/unbalanced_pf_dialog.py — Unbalanced Power Flow Dialog.

v3.3.0 Sprint 1 — fecha violação 7ª garantia identificada no audit
`docs/v3.3.0_TIER1_AUDIT.md` §B.3 (módulo
`app/postprocessor/power_flow_unbalanced.py` era órfão GUI).

Expõe ao usuário:
* PpProject input com lista de buses
* Unbalance limit configurável (default 2.0% per IEEE 1159-2019)
* Per-bus typical_unbalance configurable (default 0.5%)
* Resultado: V_a/V_b/V_c por bus + unbalance factor + violations
* Open-phase scenario simulator (PTW Tutorial §Part 9 p.241-242)

Reference: PTW Tutorial §Part 9 p.238-258; IEEE Std 1159-2019.

Trigger GUI: Análise > "Análise unbalanced (3-φ + sequências 0/1/2)..."
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
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
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class UnbalancedPowerFlowDialog(QDialog):
    """Dialog para análise unbalanced PF + open-phase scenarios.

    Reference: PTW Tutorial §Part 9 p.238-258; IEEE 1159-2019.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        project=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Unbalanced Power Flow (3-φ + sequências 0/1/2) — Olivas v3.3.0"
        )
        self.setModal(True)
        self.resize(820, 700)

        self._project = project

        main = QVBoxLayout(self)

        # Header citing reference (anti-alucinação visible to user)
        hdr = QLabel(
            "<b>Unbalanced Power Flow — Three-Phase Analysis</b><br>"
            "<small>Reference: PTW Tutorial §Part 9 p.238-258 · "
            "IEEE Std 1159-2019 · IEEE Std 399 §6 · Stevenson §11</small>"
        )
        hdr.setTextFormat(Qt.RichText)
        main.addWidget(hdr)

        # ===== Input parameters =====
        params_grp = QGroupBox("Parâmetros")
        form = QFormLayout(params_grp)

        self.unbalance_limit = QDoubleSpinBox()
        self.unbalance_limit.setRange(0.1, 10.0)
        self.unbalance_limit.setDecimals(2)
        self.unbalance_limit.setValue(2.0)
        self.unbalance_limit.setSuffix(" %")
        self.unbalance_limit.setToolTip(
            "Limite de unbalance steady-state per IEEE 1159-2019 = 2.0%"
        )
        form.addRow("Unbalance limit (V_neg/V_pos):", self.unbalance_limit)

        self.base_voltage = QDoubleSpinBox()
        self.base_voltage.setRange(0.5, 1.5)
        self.base_voltage.setDecimals(4)
        self.base_voltage.setValue(1.0)
        self.base_voltage.setSuffix(" pu")
        form.addRow("Base voltage (V_pos):", self.base_voltage)

        self.typical_unbalance = QDoubleSpinBox()
        self.typical_unbalance.setRange(0.0, 5.0)
        self.typical_unbalance.setDecimals(3)
        self.typical_unbalance.setValue(0.5)
        self.typical_unbalance.setSuffix(" %")
        self.typical_unbalance.setToolTip(
            "V_neg típico aplicado por bus (default 0.5% — sistema BR típico)"
        )
        form.addRow("Typical V_neg per bus:", self.typical_unbalance)

        main.addWidget(params_grp)

        # ===== Open-phase scenario =====
        op_grp = QGroupBox(
            "Open-phase scenario (PTW Tutorial §Part 9 p.241-242)"
        )
        op_layout = QFormLayout(op_grp)

        self.cb_open_phase = QCheckBox("Simular fase aberta")
        self.cb_open_phase.setToolTip(
            "Quando marcado, a fase selecionada é tratada como aberta "
            "(V_phase = 0); aumenta significativamente o unbalance."
        )
        op_layout.addRow(self.cb_open_phase)

        ph_box = QWidget()
        ph_lay = QHBoxLayout(ph_box)
        ph_lay.setContentsMargins(0, 0, 0, 0)
        self.rb_phase_a = QRadioButton("Phase A")
        self.rb_phase_b = QRadioButton("Phase B")
        self.rb_phase_c = QRadioButton("Phase C")
        self.rb_phase_a.setChecked(True)
        ph_lay.addWidget(self.rb_phase_a)
        ph_lay.addWidget(self.rb_phase_b)
        ph_lay.addWidget(self.rb_phase_c)
        op_layout.addRow("Fase aberta:", ph_box)

        main.addWidget(op_grp)

        # ===== Results table =====
        self.results_table = QTableWidget(0, 5, self)
        self.results_table.setHorizontalHeaderLabels([
            "Bus ID", "|V_a| (pu)", "|V_b| (pu)", "|V_c| (pu)", "UF (%)",
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        main.addWidget(self.results_table, 1)

        # ===== Summary =====
        self.summary_text = QPlainTextEdit(self)
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Consolas", 10))
        self.summary_text.setMaximumHeight(140)
        main.addWidget(self.summary_text)

        # ===== Buttons =====
        btns = QDialogButtonBox(self)
        self.btn_run = QPushButton("Calcular")
        self.btn_run.setStyleSheet(
            "QPushButton { background-color: #16a34a; color: white; "
            "font-weight: bold; padding: 6px 14px; }"
        )
        btns.addButton(self.btn_run, QDialogButtonBox.ActionRole)
        btns.addButton(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        self.btn_run.clicked.connect(self._on_calculate)
        main.addWidget(btns)

    # ----------------------------------------------------------------

    def _on_calculate(self) -> None:
        """Run analyze_unbalanced_pf + populate table + summary."""
        try:
            from app.postprocessor.power_flow_unbalanced import (
                analyze_unbalanced_pf, phase_to_sequence, sequence_to_phase,
                BusUnbalancedVoltage,
            )

            # If project provided, run real analysis
            self.results_table.setRowCount(0)
            if self._project is not None and getattr(self._project, "components", []):
                # Filter BUS components
                bus_components = [
                    c for c in self._project.components if c.type == "BUS"
                ]
                if not bus_components:
                    self.summary_text.setPlainText(
                        "Nenhum BUS encontrado no projeto. "
                        "Adicione buses ao schematic e tente novamente."
                    )
                    return

                result = analyze_unbalanced_pf(
                    self._project,
                    unbalance_limit_pct=self.unbalance_limit.value(),
                    base_voltage_pu=self.base_voltage.value(),
                    typical_unbalance_per_bus_pct=self.typical_unbalance.value(),
                )
                self._populate_results(result)
            else:
                # Demo mode: 3 buses synthetic
                self._populate_demo_results()
        except Exception as e:  # noqa: BLE001
            self.summary_text.setPlainText(
                f"Erro ao processar análise unbalanced:\n\n{type(e).__name__}: {e}"
            )

    def _populate_results(self, result) -> None:
        """Fill table from real UnbalancedPFResult."""
        for v in result.per_bus:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(v.bus_id))
            self.results_table.setItem(
                row, 1, QTableWidgetItem(f"{v.V_a_magnitude:.4f}"),
            )
            self.results_table.setItem(
                row, 2, QTableWidgetItem(f"{v.V_b_magnitude:.4f}"),
            )
            self.results_table.setItem(
                row, 3, QTableWidgetItem(f"{v.V_c_magnitude:.4f}"),
            )
            uf = v.unbalance_factor_pct
            uf_item = QTableWidgetItem(f"{uf:.3f}")
            if uf > result.unbalance_limit_pct:
                from PySide6.QtGui import QBrush, QColor
                uf_item.setForeground(QBrush(QColor("red")))
                uf_item.setText(f"{uf:.3f} ⚠")
            self.results_table.setItem(row, 4, uf_item)

        # Summary
        lines = [
            "=" * 70,
            f" Unbalanced PF Result — {len(result.per_bus)} bus(es) analisados",
            f" Reference: {result.citation}",
            f" Limit: {result.unbalance_limit_pct:.2f}% (IEEE 1159-2019)",
            "=" * 70,
            "",
            f"Violations: {len(result.violations)}",
        ]
        if result.violations:
            for v in result.violations:
                lines.append(
                    f"  ⚠ {v.bus_id}: UF = {v.unbalance_factor_pct:.3f}%"
                )
        else:
            lines.append("  ✅ Todos buses dentro do limite.")
        if result.warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in result.warnings:
                lines.append(f"  • {w}")
        self.summary_text.setPlainText("\n".join(lines))

    def _populate_demo_results(self) -> None:
        """Demo mode: 3 buses synthetic to show how dialog works."""
        from app.postprocessor.power_flow_unbalanced import (
            phase_to_sequence, sequence_to_phase,
        )
        import cmath
        import math

        # Synthetic: 3 buses with unbalance
        unb_pct = self.typical_unbalance.value() / 100.0
        v_pos = self.base_voltage.value()
        # Apply open-phase if checked (forces large unbalance)
        if self.cb_open_phase.isChecked():
            unb_pct = 0.50  # 50% — extremely high (open phase)

        v_neg = v_pos * unb_pct
        v_zero = 0.0

        bus_demo = [
            ("BUS-1", v_pos * 1.00, v_neg, v_zero),
            ("BUS-2", v_pos * 0.98, v_neg * 1.5, v_zero),
            ("BUS-3", v_pos * 0.95, v_neg * 2.0, v_zero),
        ]

        violations = []
        for row, (bus_id, vp, vn, vz) in enumerate(bus_demo):
            # Convert sequence → phase
            V0 = complex(vz, 0)
            V1 = complex(vp, 0)
            V2 = complex(vn, 0)
            Va, Vb, Vc = sequence_to_phase(V0, V1, V2)
            if self.cb_open_phase.isChecked():
                # Force selected phase to 0
                if self.rb_phase_a.isChecked():
                    Va = complex(0, 0)
                elif self.rb_phase_b.isChecked():
                    Vb = complex(0, 0)
                elif self.rb_phase_c.isChecked():
                    Vc = complex(0, 0)

            uf_pct = (vn / vp) * 100 if vp > 0 else 0.0

            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(bus_id))
            self.results_table.setItem(
                row, 1, QTableWidgetItem(f"{abs(Va):.4f}"),
            )
            self.results_table.setItem(
                row, 2, QTableWidgetItem(f"{abs(Vb):.4f}"),
            )
            self.results_table.setItem(
                row, 3, QTableWidgetItem(f"{abs(Vc):.4f}"),
            )
            limit = self.unbalance_limit.value()
            uf_text = f"{uf_pct:.3f}"
            if uf_pct > limit:
                uf_text += " ⚠"
                violations.append((bus_id, uf_pct))
            self.results_table.setItem(row, 4, QTableWidgetItem(uf_text))

        # Summary
        lines = [
            "=" * 70,
            " Unbalanced PF Result (DEMO mode — 3 synthetic buses)",
            " Reference: IEEE Std 1159-2019; PTW Tutorial §Part 9",
            f" Limit: {self.unbalance_limit.value():.2f}%",
        ]
        if self.cb_open_phase.isChecked():
            phase = (
                "A" if self.rb_phase_a.isChecked()
                else "B" if self.rb_phase_b.isChecked() else "C"
            )
            lines.append(f" OPEN-PHASE simulation: Phase {phase} = 0")
        lines.append("=" * 70)
        lines.append("")
        if violations:
            lines.append(f"Violations: {len(violations)}")
            for bus_id, uf in violations:
                lines.append(f"  ⚠ {bus_id}: UF = {uf:.3f}%")
        else:
            lines.append("✅ Todos buses dentro do limite.")
        lines.append("")
        lines.append(
            "Nota: para análise real, abra um projeto com buses .sch."
        )
        self.summary_text.setPlainText("\n".join(lines))


def run_unbalanced_pf_dialog(
    parent: Optional[QWidget] = None,
    *,
    project=None,
) -> None:
    """Convenience entry point for menus."""
    dlg = UnbalancedPowerFlowDialog(parent, project=project)
    dlg.exec()


__all__ = [
    "UnbalancedPowerFlowDialog",
    "run_unbalanced_pf_dialog",
]
