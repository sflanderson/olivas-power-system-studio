"""
app.gui.run_analysis_dialog — dialog "Executar Análise" (v0.82).

Acessível via botão verde ▶ na toolbar do PpEditor ou via
menu Análise → Executar análise...

Mostra ao usuário:
* Status do esquemático (com BUS / sem BUS).
* Lista de análises disponíveis (radio buttons).
* Bus selector (se múltiplos BUSes).
* Botão "Executar".

Quando o esquemático NÃO tem BUS, exibe instrução
explicando como adicionar um (Paleta → BUS).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QDialogButtonBox,
    QFrame, QHBoxLayout, QLabel, QPushButton, QRadioButton,
    QVBoxLayout, QWidget,
)


class RunAnalysisDialog(QDialog):
    """
    Dialog para escolher e executar análise sobre o
    PpProject carregado.

    Emit ``analysis_requested(kind, bus_id)`` quando o
    usuário confirmar:
    * kind ∈ {"sc", "pf", "motor", "arc_flash", "pipeline"}
    * bus_id: ID do barramento selecionado (ou "" para PF
      que não precisa).
    """

    # v0.94.0: kind ∈ {"sc", "coord", "arc_flash", "pf",
    #                   "motor", "ct_sat", "pipeline"}
    # Note: "coord" e "arc_flash" auto-rodam pré-requisitos
    # via StudyCache (modular).
    analysis_requested = Signal(str, str)   # (kind, bus_id)

    def __init__(
        self,
        pp_project=None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Executar Análise")
        self.setMinimumWidth(580)
        self._project = pp_project
        self._bus_ids: list[str] = []
        self._has_bus = False
        self._scan_project()
        self._build_ui()

    def _scan_project(self) -> None:
        """Detecta BUSes no projeto."""
        if self._project is None:
            return
        for comp in self._project.components:
            if comp.type == "BUS":
                bus_id = (comp.get(0, "") or "").strip()
                if bus_id:
                    self._bus_ids.append(bus_id)
                else:
                    # Fallback para nome
                    self._bus_ids.append(comp.name or "BUS")
        self._has_bus = len(self._bus_ids) > 0

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header
        header = QLabel("<b>Selecione a análise a executar</b>")
        layout.addWidget(header)

        # Status do esquemático
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)
        self._update_status()

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # Radio buttons das análises
        self._radio_group = QButtonGroup(self)
        self._radios: dict[str, QRadioButton] = {}

        layout.addWidget(QLabel("<b>Análise:</b>"))

        # v0.94.0 — Estudos modulares estilo PTW Power*Tools:
        # cada estudo é independente. Coord e Arc-flash têm
        # pré-requisitos (auto-rodam SC/Coord se necessário,
        # ou usam cache se já computados).
        analyses = [
            (
                "sc", "⚡ Curto-circuito (IEC 60909)",
                "Calcula Ik'', ip, κ, Ib no bus selecionado. "
                "Standalone — não requer outros estudos. (F5)",
            ),
            (
                "coord", "🛡️ Coordenação e seletividade (IEEE 242)",
                "Sugestões 50/51 multi-vendor. "
                "REQUIRES Curto-circuito — auto-roda se necessário. (F6)",
            ),
            (
                "arc_flash", "🔥 Arc-flash (NBR 17227 / IEEE 1584)",
                "Energia incidente + DLA + categoria PPE. "
                "REQUIRES SC + Coordenação — auto-roda se necessário. (F7)",
            ),
            (
                "pf", "🔌 Fluxo de potência (IEEE 399)",
                "Newton-Raphson — não requer BUS, só topologia.",
            ),
            (
                "motor", "📈 Partida de motor (IEEE 399)",
                "Voltage dip + tempo de aceleração para o "
                "motor selecionado.",
            ),
            (
                "ct_sat", "🔍 Saturação de TC (IEEE C57.13 / IEC 61869-2)",
                "Análise em 3 níveis: ANSI / IEC joelho / Dinâmico.",
            ),
            (
                "pipeline", "📊 Estudo completo (todos)",
                "Roda SC + Coord + Arc-flash + Sugestões em "
                "sequência. Equivalente a PTW Run All Studies. (F8)",
            ),
        ]
        for i, (kind, label, tooltip) in enumerate(analyses):
            radio = QRadioButton(label)
            radio.setToolTip(tooltip)
            self._radio_group.addButton(radio, i)
            self._radios[kind] = radio
            layout.addWidget(radio)
            # Hint inline
            hint = QLabel(f"<i><small>  {tooltip}</small></i>")
            hint.setStyleSheet("color: #666;")
            hint.setWordWrap(True)
            layout.addWidget(hint)

        # v0.94.0: pre-select Curto-circuito (estudo base PTW-style)
        # — usuário roda SC primeiro, depois encadeia Coord e
        # Arc-flash via mesmo dialog usando o cache.
        self._radios["sc"].setChecked(True)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        layout.addWidget(sep2)

        # Bus selector
        bus_row = QHBoxLayout()
        bus_row.addWidget(QLabel("Barramento:"))
        self._bus_combo = QComboBox()
        if self._has_bus:
            for bus_id in self._bus_ids:
                self._bus_combo.addItem(bus_id)
        else:
            self._bus_combo.addItem("(nenhum BUS encontrado)")
            self._bus_combo.setEnabled(False)
        bus_row.addWidget(self._bus_combo, 1)
        layout.addLayout(bus_row)

        # Hint quando sem BUS
        if not self._has_bus:
            hint = QLabel(
                "<small>⚠ <b>Adicione um componente BUS</b> "
                "no esquemático (Paleta → BUS) e configure suas "
                "propriedades (V_LL, classe). Apenas Power Flow "
                "funciona sem BUS.</small>"
            )
            hint.setWordWrap(True)
            hint.setStyleSheet(
                "QLabel { color: #d93025; padding: 6px; "
                "background: #fce8e6; border-radius: 3px; }"
            )
            layout.addWidget(hint)

        # Buttons
        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
        )
        ok_btn = bb.button(QDialogButtonBox.Ok)
        ok_btn.setText("▶ Executar")
        ok_btn.setStyleSheet(
            "QPushButton { background-color: #2ca02c; color: white; "
            "font-weight: bold; padding: 6px 16px; }"
        )
        bb.button(QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self._on_accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _update_status(self) -> None:
        if self._has_bus:
            n = len(self._bus_ids)
            self._status_label.setText(
                f"<small>✓ Esquemático com <b>{n} BUS{'es' if n>1 else ''}</b>: "
                f"{', '.join(self._bus_ids)}</small>"
            )
            self._status_label.setStyleSheet(
                "QLabel { color: #1e8e3e; padding: 4px; "
                "background: #e6f4ea; border-radius: 3px; }"
            )
        else:
            self._status_label.setText(
                "<small>⚠ Esquemático <b>sem BUS</b> — "
                "apenas Power Flow funciona sem barramento.</small>"
            )
            self._status_label.setStyleSheet(
                "QLabel { color: #ea8600; padding: 4px; "
                "background: #fef7e0; border-radius: 3px; }"
            )

    def _selected_kind(self) -> str:
        for kind, radio in self._radios.items():
            if radio.isChecked():
                return kind
        return "pipeline"

    def _on_accept(self) -> None:
        kind = self._selected_kind()
        # PF não precisa de BUS
        if kind == "pf":
            bus_id = ""
        else:
            if not self._has_bus:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, "Sem BUS",
                    "Esta análise requer um componente BUS no\n"
                    "esquemático. Adicione via Paleta → BUS.",
                )
                return
            bus_id = self._bus_combo.currentText()
        self.analysis_requested.emit(kind, bus_id)
        self.accept()
