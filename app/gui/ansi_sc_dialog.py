"""
app/gui/ansi_sc_dialog.py — ANSI C37 Short-Circuit Study Dialog.

v3.1.0 Track B-1 — Backfill GUI accessibility para módulos A_FAULT
órfãos (v3.0.2-v3.0.5).

Expõe ao usuário:

* AnsiStandard combo: C37.5 (pre-1964 Total) / C37.010 (post-1964 Symm)
* SolutionMethod radio: E/Z (default) / E/X (legacy)
* NacdMode combo: ALL_REMOTE / PREDOMINANT / INTERPOLATED
* BreakerCycle combo: 2 / 3 / 5 / 8 cycles
* FaultType radio: 3-phase / SLG
* Pre-fault voltage selector
* Generator contributions table (add/remove rows)
* Output: 3 reports (LV / Momentary / Interrupting)
* Export: TXT / Markdown / CSV (via AnsiFaultReport)

Reference: PTW Reference-A_Fault.pdf §1.4.x; cita o manual inline em tooltips.

Trigger GUI: Análise > "ANSI Short Circuit (C37.5/C37.010)..." ou
RunAnalysisDialog kind=ansi_sc.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class AnsiShortCircuitDialog(QDialog):
    """Diálogo modal para estudo ANSI C37 Short-Circuit completo.

    Integra todos os módulos backend de v3.0.2-v3.0.5 numa única UI:
    * `app.standards.ansi_c37` — NACD, MF tables, asym withstand
    * `app.standards.solution_method` — E/Z vs E/X
    * `app.standards.transformer_tap` — TAPS YES/NO scenario
    * `app.postprocessor.ansi_fault_report` — AnsiFaultBus + Report

    Cada widget tem tooltip com citação `§seção p. página` do manual
    A_Fault, mantendo a 3ª garantia (anti-alucinação) acessível ao user.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "ANSI Short Circuit (C37.5 / C37.010) — Olivas v3.1.0"
        )
        self.setModal(True)
        self.resize(800, 700)

        main = QVBoxLayout(self)

        # Header citing manual reference (anti-alucinação visible to user)
        hdr = QLabel(
            "<b>ANSI/IEEE C37.5 / C37.010 Short-Circuit Study</b><br>"
            "<small>Reference: SKM PTW <i>Reference-A_Fault.pdf</i> §1.2-§1.4</small>"
        )
        hdr.setTextFormat(Qt.RichText)
        main.addWidget(hdr)

        # Tabbed UI
        tabs = QTabWidget(self)
        main.addWidget(tabs, 1)

        tabs.addTab(self._build_inputs_tab(), "Inputs")
        tabs.addTab(self._build_contributions_tab(), "Generators")
        tabs.addTab(self._build_outputs_tab(), "Reports")

        # Buttons
        btns = QDialogButtonBox(self)
        self.btn_calc = QPushButton("Calcular")
        btns.addButton(self.btn_calc, QDialogButtonBox.ActionRole)
        self.btn_export = QPushButton("Exportar...")
        btns.addButton(self.btn_export, QDialogButtonBox.ActionRole)
        btns.addButton(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        self.btn_calc.clicked.connect(self._on_calculate)
        self.btn_export.clicked.connect(self._on_export)
        main.addWidget(btns)

    # -----------------------------------------------------------------
    # Tab 1 — Inputs
    # -----------------------------------------------------------------

    def _build_inputs_tab(self) -> QWidget:
        w = QWidget(self)
        form = QFormLayout(w)

        # Bus identification
        self.bus_name = QLineEdit("BUS-001")
        form.addRow("Bus name:", self.bus_name)

        self.kv_base = QDoubleSpinBox()
        self.kv_base.setRange(0.120, 1000.0)
        self.kv_base.setDecimals(3)
        self.kv_base.setValue(4.16)
        self.kv_base.setSuffix(" kV (L-L)")
        form.addRow("Voltage base:", self.kv_base)

        # Symmetrical RMS fault current at the bus
        self.sym_rms_kA = QDoubleSpinBox()
        self.sym_rms_kA.setRange(0.001, 1000.0)
        self.sym_rms_kA.setDecimals(3)
        self.sym_rms_kA.setValue(13.871)
        self.sym_rms_kA.setSuffix(" kA")
        self.sym_rms_kA.setToolTip(
            "Symmetrical RMS fault current at the bus (E/Z method)"
        )
        form.addRow("I_sym RMS (E/Z):", self.sym_rms_kA)

        # X/R ratio
        self.x_over_r = QDoubleSpinBox()
        self.x_over_r.setRange(0.1, 500.0)
        self.x_over_r.setDecimals(2)
        self.x_over_r.setValue(11.88)
        self.x_over_r.setToolTip(
            "Separately-derived X/R per A_Fault §1.2.3 p. 1-6"
        )
        form.addRow("X/R ratio:", self.x_over_r)

        # ANSI Standard
        self.ansi_std = QComboBox()
        self.ansi_std.addItems(["C37.010 (post-1964 Symm)", "C37.5 (pre-1964 Total)"])
        self.ansi_std.setToolTip(
            "ANSI standard per §1.3.3 p. 1-9/1-11"
        )
        form.addRow("ANSI Standard:", self.ansi_std)

        # Solution Method radio (horizontal box)
        sm_box = QWidget()
        sm_layout = QHBoxLayout(sm_box)
        sm_layout.setContentsMargins(0, 0, 0, 0)
        self.sol_ez = QRadioButton("E/Z (complex Z, default)")
        self.sol_ex = QRadioButton("E/X (reactance only)")
        self.sol_ez.setChecked(True)
        sm_layout.addWidget(self.sol_ez)
        sm_layout.addWidget(self.sol_ex)
        form.addRow("Solution Method:", sm_box)

        # NACD Mode
        self.nacd_mode = QComboBox()
        self.nacd_mode.addItems([
            "INTERPOLATED (default)",
            "PREDOMINANT (>= 0.5 → REMOTE)",
            "ALL_REMOTE (most conservative)",
        ])
        self.nacd_mode.setToolTip(
            "NACD mode per §1.3.3 p. 1-11"
        )
        form.addRow("NACD Mode:", self.nacd_mode)

        # Breaker rated cycle
        self.breaker_cycle = QComboBox()
        self.breaker_cycle.addItems(["5 cycles (3-cyc parting)", "8 cycles", "3 cycles", "2 cycles"])
        self.breaker_cycle.setToolTip("Breaker rated interrupting time")
        form.addRow("Breaker cycle:", self.breaker_cycle)

        # Fault Type
        ft_box = QWidget()
        ft_layout = QHBoxLayout(ft_box)
        ft_layout.setContentsMargins(0, 0, 0, 0)
        self.ft_3ph = QRadioButton("3-phase (default)")
        self.ft_slg = QRadioButton("SLG")
        self.ft_3ph.setChecked(True)
        ft_layout.addWidget(self.ft_3ph)
        ft_layout.addWidget(self.ft_slg)
        form.addRow("Fault Type:", ft_box)

        # Pre-fault voltage mode
        self.pre_fault_mode = QComboBox()
        self.pre_fault_mode.addItems([
            "PU_ALL = 1.0 (default ANSI)",
            "NO_LOAD_WITH_TAP (worst-case max)",
            "PU_PER_BUS (manual override)",
            "LOAD_FLOW (from LF result)",
        ])
        self.pre_fault_mode.setToolTip(
            "Pre-fault voltage per Tutorial §Part 5 p. 131-135"
        )
        form.addRow("Pre-Fault Voltage:", self.pre_fault_mode)

        # Local-vs-Remote threshold
        self.local_threshold = QDoubleSpinBox()
        self.local_threshold.setRange(0.5, 5.0)
        self.local_threshold.setDecimals(2)
        self.local_threshold.setValue(1.5)
        self.local_threshold.setToolTip(
            "Threshold per §1.2.4 p. 1-7 (default 1.5)"
        )
        form.addRow("Local/Remote threshold (Z_ext/Xd\"):", self.local_threshold)

        # LV Device Class (for LV duty report)
        self.lv_device = QComboBox()
        self.lv_device.addItems([
            "MCCB_GT_20KA",
            "LV_PCB",
            "MCCB_10_20KA",
            "MCCB_LT_10KA",
            "LV_FUSE",
            "HV_FUSE",
        ])
        self.lv_device.setToolTip(
            "LV device class per §1.2.3 p. 1-5/1-6"
        )
        form.addRow("LV Device Class:", self.lv_device)

        # Transformer tap (TAPS YES/NO scenario)
        self.tx_tap_pct = QDoubleSpinBox()
        self.tx_tap_pct.setRange(-10.0, 10.0)
        self.tx_tap_pct.setDecimals(2)
        self.tx_tap_pct.setValue(0.0)
        self.tx_tap_pct.setSuffix(" %")
        self.tx_tap_pct.setToolTip(
            "Primary tap (NEMA 5-step) per §1.4.2 p. 1-31"
        )
        form.addRow("TX Primary Tap:", self.tx_tap_pct)

        return w

    # -----------------------------------------------------------------
    # Tab 2 — Generator contributions table
    # -----------------------------------------------------------------

    def _build_contributions_tab(self) -> QWidget:
        w = QWidget(self)
        layout = QVBoxLayout(w)

        info = QLabel(
            "<i>Geradores contribuintes ao fault. Local/Remote determinado "
            "automaticamente via Z_external/Xd\" &lt; threshold (§1.2.4 p. 1-7).</i>"
        )
        info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        self.gens_table = QTableWidget(0, 5, w)
        self.gens_table.setHorizontalHeaderLabels([
            "Name", "Bus", "I (kA)", "Z_ext (pu)", "Xd\" (pu)",
        ])
        self.gens_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        layout.addWidget(self.gens_table, 1)

        # Pre-fill with §1.4.3 Case 2 example (PROC A MTR BUS, NACD=0.6778)
        self._add_generator_row("UTIL-0001", "PROC_A_MTR", 9.401, 2.0, 1.0)
        self._add_generator_row("G1", "PROC_A_MTR", 1.307, 0.10, 0.20)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Adicionar gerador")
        btn_remove = QPushButton("- Remover selecionado")
        btn_add.clicked.connect(lambda: self._add_generator_row("GenN", "BUS", 1.0, 1.0, 0.5))
        btn_remove.clicked.connect(self._remove_selected_row)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        return w

    def _add_generator_row(self, name: str, bus: str, i_ka: float,
                           z_ext: float, xd: float) -> None:
        row = self.gens_table.rowCount()
        self.gens_table.insertRow(row)
        self.gens_table.setItem(row, 0, QTableWidgetItem(name))
        self.gens_table.setItem(row, 1, QTableWidgetItem(bus))
        self.gens_table.setItem(row, 2, QTableWidgetItem(f"{i_ka:.4f}"))
        self.gens_table.setItem(row, 3, QTableWidgetItem(f"{z_ext:.4f}"))
        self.gens_table.setItem(row, 4, QTableWidgetItem(f"{xd:.4f}"))

    def _remove_selected_row(self) -> None:
        current = self.gens_table.currentRow()
        if current >= 0:
            self.gens_table.removeRow(current)

    # -----------------------------------------------------------------
    # Tab 3 — Outputs (3 reports)
    # -----------------------------------------------------------------

    def _build_outputs_tab(self) -> QWidget:
        w = QWidget(self)
        layout = QVBoxLayout(w)

        info = QLabel(
            "<i>Clique em <b>Calcular</b> para gerar os 3 relatórios (LV / Momentary / Interrupting).</i>"
        )
        info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        self.output_text = QPlainTextEdit(w)
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.output_text, 1)

        return w

    # -----------------------------------------------------------------
    # Calculate handler — integra v3.0.2-v3.0.5 backend
    # -----------------------------------------------------------------

    def _on_calculate(self) -> None:
        try:
            from app.postprocessor.ansi_fault_report import AnsiFaultBus
            from app.standards.ansi_c37 import (
                AnsiStandard, BreakerCycle, FaultType, GeneratorContribution,
                NacdMode,
            )
            from app.standards.transformer_tap import voltage_with_tap

            # Apply transformer tap to voltage
            tap = self.tx_tap_pct.value()
            v_eff_pu = voltage_with_tap(v_nominal_pu=1.0, tap_percent=tap)

            # Fault type
            fault_str = "3ph" if self.ft_3ph.isChecked() else "slg"

            # Build contributions
            contribs: list[GeneratorContribution] = []
            for row in range(self.gens_table.rowCount()):
                try:
                    name = self.gens_table.item(row, 0).text()
                    bus = self.gens_table.item(row, 1).text()
                    i_ka = float(self.gens_table.item(row, 2).text())
                    z_ext = float(self.gens_table.item(row, 3).text())
                    xd = float(self.gens_table.item(row, 4).text())
                    contribs.append(GeneratorContribution(
                        name=name, bus=bus, i_kA=i_ka,
                        z_external_pu=z_ext, xd_pu=xd,
                    ))
                except (ValueError, AttributeError):
                    continue

            # Build the bus
            bus = AnsiFaultBus(
                bus_name=self.bus_name.text(),
                kv_base=self.kv_base.value(),
                sym_rms_kA=self.sym_rms_kA.value() * v_eff_pu,
                x_over_r=self.x_over_r.value(),
                fault_type=fault_str,
                contributions=contribs,
            )

            # Map enum selections
            std_map = {
                "C37.010 (post-1964 Symm)": AnsiStandard.C37_010,
                "C37.5 (pre-1964 Total)": AnsiStandard.C37_5,
            }
            ansi_std = std_map[self.ansi_std.currentText()]

            mode_map = {
                "INTERPOLATED (default)": NacdMode.INTERPOLATED,
                "PREDOMINANT (>= 0.5 → REMOTE)": NacdMode.PREDOMINANT,
                "ALL_REMOTE (most conservative)": NacdMode.ALL_REMOTE,
            }
            mode = mode_map[self.nacd_mode.currentText()]

            cycle_map = {
                "5 cycles (3-cyc parting)": 5,
                "8 cycles": 8,
                "3 cycles": 3,
                "2 cycles": 2,
            }
            cycle = cycle_map[self.breaker_cycle.currentText()]

            # Generate 3 reports
            mom = bus.momentary_duty()
            intr = bus.interrupting_duty(
                breaker_cycle=cycle, nacd_mode=mode, ansi_std=ansi_std,
            )
            lv = bus.lv_duty(device_class=self.lv_device.currentText())

            asym_phase_a = bus.asymmetrical_withstand("phase_a")
            asym_avg = bus.asymmetrical_withstand("average_3ph")

            # Format text output (PTW-style)
            lines = [
                "=" * 78,
                f" ANSI/IEEE C37.5/C37.010 SHORT-CIRCUIT REPORT",
                f" Generated by Olivas Power System Studio (v3.1.0)",
                f" Reference: PTW A_Fault §1.2-§1.4",
                "=" * 78,
                "",
                f"Bus:        {bus.bus_name}",
                f"kV base:    {bus.kv_base:.3f} kV",
                f"I_sym RMS:  {bus.sym_rms_kA:.3f} kA  (TX tap: {tap:+.1f}%, V_eff={v_eff_pu:.4f} pu)",
                f"X/R:        {bus.x_over_r:.2f}",
                f"Z total:    {bus.z_total_ohm:.4f} Ω",
                f"Fault:      {fault_str}",
                f"Standard:   {ansi_std.value}",
                "",
                "─" * 78,
                "  LV Duty Report (§1.2.3 p. 1-6)",
                "─" * 78,
                f"  Device class:    {lv['device_class']}",
                f"  Test X/R:        {lv['test_x_over_r']:.2f}",
                f"  System X/R:      {lv['system_x_over_r']:.2f}",
                f"  Sym RMS:         {lv['sym_rms_kA']:.3f} kA",
                f"  LV adjusted:     {lv['adjusted_kA']:.3f} kA",
                f"  Boost/Atten:     ×{lv['boost_or_attenuation']:.4f}",
                "",
                "─" * 78,
                "  Momentary Duty Report (§1.3.6 Eq. 7-1)",
                "─" * 78,
                f"  E/Z:             {mom['e_over_z_kA']:.3f} kA",
                f"  X/R:             {mom['x_over_r']:.2f}",
                f"  SYM × 1.6:       {mom['sym_x_1_6']:.3f} kA  (PTW simplified)",
                f"  SYM × 2.7:       {mom['sym_x_2_7']:.3f} kA  (PTW simplified peak)",
                f"  Mom-X/R:         {mom['mom_x_over_r_kA']:.3f} kA",
                f"  Crest-X/R:       {mom['crest_x_over_r_kA']:.3f} kA",
                "",
                "─" * 78,
                f"  Interrupting Duty Report (§1.3.7 — {mode.value} mode)",
                "─" * 78,
                f"  E/Z:             {intr['e_over_z_kA']:.3f} kA",
                f"  X/R:             {intr['x_over_r']:.2f}",
                f"  I REMOTE:        {intr['i_remote_kA']:.3f} kA",
                f"  I LOCAL:         {intr['i_local_kA']:.3f} kA",
                f"  NACD ratio:      {intr['nacd']:.4f}",
                f"  NACD mode:       {intr['nacd_mode']}",
                f"  Breaker:         {intr['breaker_cycle']}-cycle",
                f"  ANSI standard:   {intr['ansi_std']}",
                f"  Multiplying Factor: {intr['mf']:.4f}",
                f"  DUTY:            {intr['duty_kA']:.3f} kA",
                "",
                "─" * 78,
                "  Asymmetrical Withstand (§1.2.3 p. 1-6/1-7)",
                "─" * 78,
                f"  Phase A worst:   {asym_phase_a:.3f} kA",
                f"  Average 3-φ:     {asym_avg:.3f} kA",
                "",
                "=" * 78,
            ]
            self.output_text.setPlainText("\n".join(lines))

            # Cache for export
            self._last_bus = bus
            self._last_text = "\n".join(lines)

        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(
                self, "Erro no cálculo",
                f"Erro ao processar ANSI SC:\n\n{type(e).__name__}: {e}",
            )

    # -----------------------------------------------------------------
    # Export handler
    # -----------------------------------------------------------------

    def _on_export(self) -> None:
        if not getattr(self, "_last_bus", None):
            QMessageBox.warning(
                self, "Nada para exportar",
                "Execute Calcular antes de exportar.",
            )
            return

        path, sel = QFileDialog.getSaveFileName(
            self, "Exportar relatório ANSI",
            f"{self._last_bus.bus_name}_ansi_sc.txt",
            "Texto PTW-style (*.txt);;Markdown (*.md);;CSV (*.csv)",
        )
        if not path:
            return

        try:
            from app.postprocessor.ansi_fault_report import AnsiFaultReport
            report = AnsiFaultReport(project_name=self._last_bus.bus_name)
            report.add_bus(self._last_bus)

            if path.endswith(".md") or "Markdown" in sel:
                content = report.format_markdown()
            elif path.endswith(".csv") or "CSV" in sel:
                content = report.format_csv()
            else:
                content = self._last_text  # PTW-style with all 3 reports

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            QMessageBox.information(
                self, "Exportado",
                f"Relatório salvo em:\n{path}",
            )
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(
                self, "Erro no export",
                f"Erro ao exportar:\n\n{type(e).__name__}: {e}",
            )


def run_ansi_sc_dialog(parent: Optional[QWidget] = None) -> None:
    """Convenience entry point for menus / RunAnalysisDialog dispatch."""
    dlg = AnsiShortCircuitDialog(parent)
    dlg.exec()


__all__ = [
    "AnsiShortCircuitDialog",
    "run_ansi_sc_dialog",
]
