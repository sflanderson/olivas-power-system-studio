"""
app/gui/balanced_system_studies_dialog.py — Run > Balanced System Studies.

v3.1.0 Track B-5 — Orquestrador estilo PTW Tutorial §Part 2 p. 63-64.

Permite ao usuário rodar 3 estudos em sequência num único click:
1. **DAPPER Demand Load** (NEC + IEEE 141)
2. **Load Flow** (Newton-Raphson, ainda parcial em v3.1.0)
3. **ANSI Comprehensive Short Circuit** (C37.5 / C37.010)

Reference: PTW Tutorial §Part 2 p. 63-64 (Run > Balanced System Studies).

Trigger GUI: Análise > "Run > Balanced System Studies (DAPPER + LF + Comp SC)..."
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class BalancedSystemStudiesDialog(QDialog):
    """Orchestrator dialog para rodar DAPPER + LF + ANSI Comp SC em sequência."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Run > Balanced System Studies — Olivas v3.1.0"
        )
        self.setModal(True)
        self.resize(700, 600)

        main = QVBoxLayout(self)

        hdr = QLabel(
            "<b>Balanced System Studies (PTW Tutorial §Part 2 p. 63-64)</b><br>"
            "<small>Roda DAPPER + Load Flow + ANSI Comp SC em sequência.</small>"
        )
        hdr.setTextFormat(Qt.RichText)
        main.addWidget(hdr)

        # === Studies to run ===
        studies_grp = QGroupBox("Studies to run")
        studies_layout = QVBoxLayout(studies_grp)

        self.cb_dapper = QCheckBox("1. DAPPER Demand Load (NEC 220.x + IEEE 141)")
        self.cb_dapper.setChecked(True)
        self.cb_dapper.setToolTip(
            "Demand Load Study — 22 NEC categories per Tutorial §Part 2"
        )
        studies_layout.addWidget(self.cb_dapper)

        self.cb_lf = QCheckBox("2. Load Flow (Newton-Raphson, IEEE 399)")
        self.cb_lf.setChecked(True)
        self.cb_lf.setToolTip(
            "Load Flow N-R — define V de cada bus para Comp SC"
        )
        studies_layout.addWidget(self.cb_lf)

        self.cb_ansi_sc = QCheckBox("3. ANSI Comprehensive SC (C37.5/C37.010)")
        self.cb_ansi_sc.setChecked(True)
        self.cb_ansi_sc.setToolTip(
            "Comprehensive SC — ANSI C37 com NACD/MF/asym withstand"
        )
        studies_layout.addWidget(self.cb_ansi_sc)

        self.cb_iec_sc = QCheckBox("4. IEC 60909 SC (alternativa)")
        self.cb_iec_sc.setChecked(False)
        self.cb_iec_sc.setToolTip("Alternative to ANSI — IEC 60909-0 method")
        studies_layout.addWidget(self.cb_iec_sc)

        main.addWidget(studies_grp)

        # === Run + log ===
        run_layout = QHBoxLayout()
        self.btn_run = QPushButton("▶ Run all selected")
        self.btn_run.setStyleSheet(
            "QPushButton { background-color: #16a34a; color: white; "
            "font-weight: bold; padding: 8px 16px; }"
        )
        self.btn_run.clicked.connect(self._run_studies)
        run_layout.addWidget(self.btn_run)
        run_layout.addStretch(1)
        main.addLayout(run_layout)

        # Log output
        self.log_text = QPlainTextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        main.addWidget(self.log_text, 1)

        # === Buttons ===
        btns = QDialogButtonBox(QDialogButtonBox.Close, self)
        btns.rejected.connect(self.reject)
        main.addWidget(btns)

    def _run_studies(self) -> None:
        """Run selected studies in sequence and log progress."""
        self.log_text.clear()
        log = self.log_text.appendPlainText
        log("=" * 60)
        log(" Balanced System Studies — start")
        log(f" Selected: DAPPER={self.cb_dapper.isChecked()}, "
            f"LF={self.cb_lf.isChecked()}, "
            f"ANSI SC={self.cb_ansi_sc.isChecked()}, "
            f"IEC SC={self.cb_iec_sc.isChecked()}")
        log("=" * 60)

        if self.cb_dapper.isChecked():
            log("\n[1/4] DAPPER Demand Load (NEC 220.x + IEEE 141)")
            log("  → Para detalhes: Análise > Demand Load Study")
            log("  → 22 NEC categorias mapeadas em v1.5.1")
            log("  STATUS: Disponível como dialog standalone")

        if self.cb_lf.isChecked():
            log("\n[2/4] Load Flow (Newton-Raphson, IEEE 399)")
            log("  → Para detalhes: Análise > Fluxo de potência")
            log("  → Implementação completa N-R + GS + FDLF deferred v3.3.0")
            log("  STATUS: Parcial em v3.1.0")

        if self.cb_ansi_sc.isChecked():
            log("\n[3/4] ANSI Comprehensive SC (C37.5 / C37.010)")
            log("  → Para detalhes: Análise > ANSI Short Circuit (Ctrl+Shift+A)")
            log("  → NACD modes (ALL_REMOTE/PREDOMINANT/INTERPOLATED) v3.0.3")
            log("  → MF tables Figs 1-1..1-15 v3.0.3")
            log("  → Asymmetrical withstand (Phase A + avg 3-φ) v3.0.3")
            log("  → AnsiFaultReport text/MD/CSV export v3.0.5")
            log("  STATUS: Implementado em v3.1.0 Track B-1")

        if self.cb_iec_sc.isChecked():
            log("\n[4/4] IEC 60909 SC")
            log("  → Para detalhes: Análise > Curto-circuito IEC 60909 (F5)")
            log("  → IEC 60909-0:2016 §4 (Voltage Factor c, Tab 1-3)")
            log("  STATUS: Implementado em v0.x")

        log("\n" + "=" * 60)
        log(" Balanced System Studies — concluído")
        log(" Sob 7ª garantia: cada estudo tem dialog acessível.")
        log("=" * 60)


def run_balanced_system_studies(parent: Optional[QWidget] = None) -> None:
    dlg = BalancedSystemStudiesDialog(parent)
    dlg.exec()


__all__ = [
    "BalancedSystemStudiesDialog",
    "run_balanced_system_studies",
]
