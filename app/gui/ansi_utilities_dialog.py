"""
app/gui/ansi_utilities_dialog.py — ANSI C37 utility tools.

v3.1.0 Track B-3 — Backfill GUI accessibility para 3 módulos órfãos:

* Mis-coordination Detection (`app.postprocessor.mis_coordination`)
* Solution Method + ANSI Standard conversion (`app.standards.solution_method`)
* Transformer Tap (TAPS YES/NO scenario) (`app.standards.transformer_tap`)

Trigger GUI: Ferramentas > "ANSI Utilities (Mis-coord / Conversion / TX Tap)..."
"""

from __future__ import annotations

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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class AnsiUtilitiesDialog(QDialog):
    """3 utilitários ANSI numa única janela tab-based."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ANSI Utilities — Olivas v3.1.0")
        self.setModal(True)
        self.resize(800, 700)

        main = QVBoxLayout(self)

        hdr = QLabel(
            "<b>ANSI C37 Utilities</b><br>"
            "<small>Mis-coordination Detection · Standard Conversion · Transformer Tap</small>"
        )
        hdr.setTextFormat(Qt.RichText)
        main.addWidget(hdr)

        tabs = QTabWidget(self)
        main.addWidget(tabs, 1)

        tabs.addTab(self._build_mis_coord_tab(), "Mis-Coordination")
        tabs.addTab(self._build_conversion_tab(), "C37.5 ↔ C37.010")
        tabs.addTab(self._build_tap_tab(), "Transformer Tap")

        btns = QDialogButtonBox(QDialogButtonBox.Close, self)
        btns.rejected.connect(self.reject)
        main.addWidget(btns)

    # -----------------------------------------------------------------
    # Tab 1 — Mis-Coordination Detection
    # -----------------------------------------------------------------

    def _build_mis_coord_tab(self) -> QWidget:
        w = QWidget(self)
        layout = QVBoxLayout(w)

        info = QLabel(
            "<i>Detecta pares de devices com coordenação inadequada.<br>"
            "Reference: PTW Tutorial §Part 5 p. 144-145.</i>"
        )
        info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        # Settings
        settings_grp = QGroupBox("Settings")
        settings_form = QFormLayout(settings_grp)

        self.mc_threshold = QDoubleSpinBox()
        self.mc_threshold.setRange(0.0, 1.0)
        self.mc_threshold.setDecimals(2)
        self.mc_threshold.setValue(0.80)
        self.mc_threshold.setToolTip("Default 0.80 per §Part 5 p. 144")
        settings_form.addRow("Cleared Fault Threshold:", self.mc_threshold)

        self.mc_levels = QSpinBox()
        self.mc_levels.setRange(1, 10)
        self.mc_levels.setValue(3)
        self.mc_levels.setToolTip("Default 3 per §Part 5 p. 145")
        settings_form.addRow("Levels to Search upstream:", self.mc_levels)

        layout.addWidget(settings_grp)

        # Pair test
        pair_grp = QGroupBox("Test Pair (Main vs Backup)")
        pair_form = QFormLayout(pair_grp)

        self.t_main = QDoubleSpinBox()
        self.t_main.setRange(0.001, 60.0)
        self.t_main.setDecimals(3)
        self.t_main.setValue(0.05)
        self.t_main.setSuffix(" s")
        pair_form.addRow("t_main_trip:", self.t_main)

        self.t_backup = QDoubleSpinBox()
        self.t_backup.setRange(0.001, 60.0)
        self.t_backup.setDecimals(3)
        self.t_backup.setValue(0.20)
        self.t_backup.setSuffix(" s")
        pair_form.addRow("t_backup_trip:", self.t_backup)

        self.i_main = QDoubleSpinBox()
        self.i_main.setRange(0.001, 1000.0)
        self.i_main.setDecimals(3)
        self.i_main.setValue(9.0)
        self.i_main.setSuffix(" kA")
        pair_form.addRow("I_main:", self.i_main)

        self.i_total = QDoubleSpinBox()
        self.i_total.setRange(0.001, 1000.0)
        self.i_total.setDecimals(3)
        self.i_total.setValue(10.0)
        self.i_total.setSuffix(" kA")
        pair_form.addRow("I_total:", self.i_total)

        btn_check = QPushButton("Check coordination")
        btn_check.clicked.connect(self._mc_check)
        pair_form.addRow("", btn_check)

        layout.addWidget(pair_grp)

        # Result
        self.mc_result = QPlainTextEdit(w)
        self.mc_result.setReadOnly(True)
        self.mc_result.setFont(QFont("Consolas", 10))
        self.mc_result.setMaximumHeight(160)
        layout.addWidget(self.mc_result, 1)

        return w

    def _mc_check(self) -> None:
        from app.postprocessor.mis_coordination import (
            is_main_cleared, mis_coordination_ratio,
        )
        try:
            cleared = is_main_cleared(
                i_main_kA=self.i_main.value(),
                i_total_kA=self.i_total.value(),
                threshold=self.mc_threshold.value(),
            )
            ratio = mis_coordination_ratio(
                t_main_trip_s=self.t_main.value(),
                t_backup_trip_s=self.t_backup.value(),
            )
            verdict_clear = "✅ CLEARED" if cleared else "❌ NOT CLEARED"
            verdict_coord = (
                "✅ COORDINATED" if ratio < 1.0
                else "⚠️ BORDERLINE" if ratio == 1.0
                else "❌ MIS-COORDINATION"
            )
            text = (
                f"=== Mis-Coordination Analysis ===\n\n"
                f"I_main / I_total = {self.i_main.value():.3f} / {self.i_total.value():.3f} "
                f"= {self.i_main.value()/self.i_total.value():.4f}\n"
                f"Threshold:        {self.mc_threshold.value():.2f}\n"
                f"Main clears?      {verdict_clear}\n\n"
                f"t_main / t_backup = {self.t_main.value():.3f} / "
                f"{self.t_backup.value():.3f} = {ratio:.4f}\n"
                f"Coordination:     {verdict_coord}\n\n"
                f"(Reference: PTW Tutorial §Part 5 p. 144-145)"
            )
            self.mc_result.setPlainText(text)
        except (ValueError, ZeroDivisionError) as e:
            self.mc_result.setPlainText(f"Erro: {e}")

    # -----------------------------------------------------------------
    # Tab 2 — Standard Conversion (C37.5 ↔ C37.010)
    # -----------------------------------------------------------------

    def _build_conversion_tab(self) -> QWidget:
        w = QWidget(self)
        layout = QVBoxLayout(w)

        info = QLabel(
            "<i>Converte ratings entre C37.5 (Total Rated) e C37.010 (Symmetrical Rated).<br>"
            "Reference: A_Fault §1.3.7 p. 1-19/1-20.</i>"
        )
        info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        sm_grp = QGroupBox("Solution Method")
        sm_form = QFormLayout(sm_grp)

        self.sm_combo = QComboBox()
        self.sm_combo.addItems([
            "E/Z (complex impedance, default)",
            "E/X (reactance only, legacy)",
        ])
        self.sm_combo.setToolTip("Per §1.3.3 p. 1-9/1-11")
        sm_form.addRow("Method:", self.sm_combo)

        layout.addWidget(sm_grp)

        # Complex Z → X/R
        zxr_grp = QGroupBox("X/R from complex Z (E/Z method)")
        zxr_form = QFormLayout(zxr_grp)

        self.r_input = QDoubleSpinBox()
        self.r_input.setRange(0.0, 1000.0)
        self.r_input.setDecimals(4)
        self.r_input.setValue(0.065)
        zxr_form.addRow("R:", self.r_input)

        self.x_input = QDoubleSpinBox()
        self.x_input.setRange(0.0, 1000.0)
        self.x_input.setDecimals(4)
        self.x_input.setValue(0.922)
        zxr_form.addRow("X:", self.x_input)

        btn_xr = QPushButton("Compute X/R")
        btn_xr.clicked.connect(self._compute_xr)
        zxr_form.addRow("", btn_xr)

        self.xr_result = QLabel("X/R = ?")
        self.xr_result.setStyleSheet("font-family: Consolas; font-weight: bold; color: #2563eb;")
        zxr_form.addRow("Result:", self.xr_result)

        layout.addWidget(zxr_grp)

        # Total ↔ Symmetrical conversion
        conv_grp = QGroupBox("C37.5 (Total) ↔ C37.010 (Symmetrical) conversion")
        conv_form = QFormLayout(conv_grp)

        self.conv_direction = QComboBox()
        self.conv_direction.addItems([
            "Total → Symmetrical (i_symm = i_total / asym_factor)",
            "Symmetrical → Total (i_total = i_symm × asym_factor)",
        ])
        conv_form.addRow("Direction:", self.conv_direction)

        self.conv_input = QDoubleSpinBox()
        self.conv_input.setRange(0.001, 10000.0)
        self.conv_input.setDecimals(3)
        self.conv_input.setValue(16.0)
        self.conv_input.setSuffix(" kA")
        conv_form.addRow("Input current:", self.conv_input)

        self.conv_factor = QDoubleSpinBox()
        self.conv_factor.setRange(0.5, 3.0)
        self.conv_factor.setDecimals(2)
        self.conv_factor.setValue(1.6)
        self.conv_factor.setToolTip(
            "Per §1.3.6: ~1.5 (X/R=15), ~1.6 (X/R=25), ~1.7 (X/R≥50)"
        )
        conv_form.addRow("Asym factor:", self.conv_factor)

        btn_conv = QPushButton("Convert")
        btn_conv.clicked.connect(self._convert_standard)
        conv_form.addRow("", btn_conv)

        self.conv_result = QLabel("Result = ?")
        self.conv_result.setStyleSheet("font-family: Consolas; font-weight: bold; color: #2563eb;")
        conv_form.addRow("", self.conv_result)

        layout.addWidget(conv_grp)
        layout.addStretch(1)
        return w

    def _compute_xr(self) -> None:
        from app.standards.solution_method import x_over_r_from_complex_impedance
        try:
            xr = x_over_r_from_complex_impedance(
                r=self.r_input.value(), x=self.x_input.value(),
            )
            self.xr_result.setText(f"X/R = {xr:.4f}")
        except ValueError as e:
            self.xr_result.setText(f"Erro: {e}")

    def _convert_standard(self) -> None:
        from app.standards.solution_method import (
            convert_symmetrical_to_total, convert_total_to_symmetrical,
        )
        try:
            i = self.conv_input.value()
            f = self.conv_factor.value()
            if self.conv_direction.currentIndex() == 0:
                out = convert_total_to_symmetrical(i_total_kA=i, asym_factor=f)
                self.conv_result.setText(
                    f"Symm = {out:.3f} kA  (i_total {i:.3f} ÷ {f:.2f})"
                )
            else:
                out = convert_symmetrical_to_total(i_symm_kA=i, asym_factor=f)
                self.conv_result.setText(
                    f"Total = {out:.3f} kA  (i_symm {i:.3f} × {f:.2f})"
                )
        except ValueError as e:
            self.conv_result.setText(f"Erro: {e}")

    # -----------------------------------------------------------------
    # Tab 3 — Transformer Tap
    # -----------------------------------------------------------------

    def _build_tap_tab(self) -> QWidget:
        w = QWidget(self)
        layout = QVBoxLayout(w)

        info = QLabel(
            "<i>TX primary tap modeling (TAPS YES/NO scenarios) + SLG vs 3-φ ratio.<br>"
            "Reference: A_Fault §1.4.2 p. 1-31 a 1-33.</i>"
        )
        info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        # Tap → V_secondary
        tap_grp = QGroupBox("Tap → Secondary voltage")
        tap_form = QFormLayout(tap_grp)

        self.tap_combo = QComboBox()
        self.tap_combo.addItems([
            "-5.0%  (NEMA step -2)",
            "-2.5%  (NEMA step -1)",
            "0.0%   (NEMA step 0, nominal)",
            "+2.5%  (NEMA step +1)",
            "+5.0%  (NEMA step +2)",
        ])
        self.tap_combo.setCurrentIndex(2)  # default 0%
        tap_form.addRow("Tap (NEMA TR-1):", self.tap_combo)

        self.tap_v_pri = QDoubleSpinBox()
        self.tap_v_pri.setRange(0.5, 1.5)
        self.tap_v_pri.setDecimals(4)
        self.tap_v_pri.setValue(1.0)
        self.tap_v_pri.setSuffix(" pu")
        tap_form.addRow("V_primary:", self.tap_v_pri)

        btn_tap = QPushButton("Compute V_secondary")
        btn_tap.clicked.connect(self._compute_tap)
        tap_form.addRow("", btn_tap)

        self.tap_result = QLabel("V_sec = ?")
        self.tap_result.setStyleSheet("font-family: Consolas; font-weight: bold; color: #2563eb;")
        tap_form.addRow("Result:", self.tap_result)

        layout.addWidget(tap_grp)

        # SLG vs 3-φ
        slg_grp = QGroupBox("SLG vs 3-φ ratio (delta-wye-grounded near TX)")
        slg_form = QFormLayout(slg_grp)

        self.slg_z0_z1 = QDoubleSpinBox()
        self.slg_z0_z1.setRange(0.0, 100.0)
        self.slg_z0_z1.setDecimals(3)
        self.slg_z0_z1.setValue(0.85)
        self.slg_z0_z1.setToolTip("Z0/Z1 typical 0.5-1.0 for delta-wye-grounded")
        slg_form.addRow("Z0 / Z1:", self.slg_z0_z1)

        btn_slg = QPushButton("Compute SLG/3-φ")
        btn_slg.clicked.connect(self._compute_slg)
        slg_form.addRow("", btn_slg)

        self.slg_result = QLabel("SLG/3-φ = ?")
        self.slg_result.setStyleSheet("font-family: Consolas; font-weight: bold; color: #2563eb;")
        slg_form.addRow("Result:", self.slg_result)

        layout.addWidget(slg_grp)
        layout.addStretch(1)
        return w

    def _compute_tap(self) -> None:
        from app.standards.transformer_tap import voltage_with_tap
        tap_text = self.tap_combo.currentText()
        tap_pct = float(tap_text.split("%")[0])
        v = voltage_with_tap(
            v_nominal_pu=self.tap_v_pri.value(),
            tap_percent=tap_pct,
        )
        self.tap_result.setText(
            f"V_sec = {v:.4f} pu  ({tap_pct:+.1f}% tap)"
        )

    def _compute_slg(self) -> None:
        from app.standards.transformer_tap import slg_vs_3ph_ratio
        try:
            ratio = slg_vs_3ph_ratio(z0_over_z1=self.slg_z0_z1.value())
            verdict = "I_SLG > I_3φ ⚠" if ratio > 1.0 else "I_SLG ≤ I_3φ"
            self.slg_result.setText(f"Ratio = {ratio:.4f} ({verdict})")
        except ValueError as e:
            self.slg_result.setText(f"Erro: {e}")


def run_ansi_utilities_dialog(parent: Optional[QWidget] = None) -> None:
    dlg = AnsiUtilitiesDialog(parent)
    dlg.exec()


__all__ = [
    "AnsiUtilitiesDialog",
    "run_ansi_utilities_dialog",
]
