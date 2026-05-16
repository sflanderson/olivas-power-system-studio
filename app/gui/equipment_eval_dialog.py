"""
app.gui.equipment_eval_dialog — Equipment Evaluation Dashboard
GUI dialog (v1.3.1 G.1).

Filosofia
==========

PTW Power*Tools "Equipment Evaluation" mostra dashboard tabular
único Pass/Warn/Fail por equipamento × critério. Olivas v1.3.0
entregou o backend completo (`equipment_eval.py` +
`equipment_eval_rules.py` + `equipment_eval_dashboard.py`) mas
sem GUI — engenheiro precisava chamar via Python.

Esta sub-sprint G.1 entrega o **dialog QDialog** que:
1. Carrega lista demo de equipamentos (5 instances)
2. Aplica `PTW_EQUIPMENT_EVALUATION` RuleSet (9 critérios)
3. Renderiza HTML em QTextBrowser
4. Permite export CSV / save HTML

Sem deps externas adicionais (QTextBrowser nativo do Qt; sem
QWebEngineView).

Cobertura normativa
====================

* IEEE 242:2001 §15 (Equipment Evaluation criteria)
* NBR 5410:2004 §6.2.7 (V-drop limits)
* ANSI C37.04 (LV breaker ratings)
* Convenção PTW Equipment Evaluation tabular dashboard
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.postprocessor.equipment_eval import (
    EquipmentInstance,
    evaluate_project,
)
from app.postprocessor.equipment_eval_dashboard import (
    export_csv,
    generate_html_dashboard,
)
from app.postprocessor.equipment_eval_rules import (
    PTW_EQUIPMENT_EVALUATION,
)


def _build_demo_equipment() -> list:
    """
    Constrói 7 equipamentos demo cobrindo tipos diversos com mix
    de PASS/WARN/FAIL — útil para ENGENHEIRO ver o dashboard
    em ação sem precisar configurar projeto.

    Cenário: subestação 13.8 kV típica.
    """
    return [
        EquipmentInstance(
            equipment_id="BUS-MAIN-13.8kV",
            equipment_type="bus",
            rated_voltage_kV=13.8,
            rated_continuous_A=3000,
            duty={"V_drop_pct": 2.5},  # PASS
        ),
        EquipmentInstance(
            equipment_id="BRK-MAIN-15kV",
            equipment_type="breaker",
            rated_voltage_kV=15.0,
            rated_continuous_A=2000,
            rated_interrupt_kA=40.0,
            rated_asym_kA=104.0,
            bus_voltage_kV=13.8,
            duty={
                "I_load_A": 1500,    # 75% → WARN
                "I_fault_kA": 25.0,  # 62% → PASS
                "ip_kA": 65.0,       # 62% → PASS
                "V_drop_pct": 0.3,   # 30% → PASS
            },
        ),
        EquipmentInstance(
            equipment_id="BRK-FEEDER-1",
            equipment_type="breaker",
            rated_voltage_kV=15.0,
            rated_continuous_A=600,
            rated_interrupt_kA=20.0,
            rated_asym_kA=52.0,
            bus_voltage_kV=13.8,
            duty={
                "I_load_A": 580,
                "I_fault_kA": 18,
                "ip_kA": 47,
                "V_drop_pct": 0.5,
            },
        ),
        EquipmentInstance(
            equipment_id="CAB-FEEDER-50mm2",
            equipment_type="cable",
            rated_voltage_kV=1.0,
            rated_continuous_A=200,
            duty={
                "I_load_A": 150,     # 75% → WARN
                "I_design_A": 180,   # 90% → WARN
                "V_drop_pct": 3.5,   # 87% do limit 4% → WARN
            },
        ),
        EquipmentInstance(
            equipment_id="CAB-OVERSIZED",
            equipment_type="cable",
            rated_voltage_kV=1.0,
            rated_continuous_A=200,
            duty={
                "I_load_A": 250,    # 125% → FAIL
                "I_design_A": 270,  # 135% → FAIL
                "V_drop_pct": 5.0,  # 125% do limit → FAIL
            },
        ),
        EquipmentInstance(
            equipment_id="GEN-EMERGENCY",
            equipment_type="generator",
            rated_voltage_kV=13.8,
            rated_continuous_A=1000,
            duty={"gen_load_A": 700},  # 70% → WARN border
        ),
        EquipmentInstance(
            equipment_id="T1-13.8kV",
            equipment_type="transformer",
            rated_voltage_kV=13.8,
            rated_continuous_A=500,
            bus_voltage_kV=13.8,
            duty={
                "I_load_A": 400,    # 80% → WARN
                "I_design_A": 480,  # 96% → WARN
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


class EquipmentEvalDialog(QDialog):
    """
    Dialog QDialog para Equipment Evaluation.

    Layout
    -------

    ::

        [Title]
        [Status label] [Buttons: Demo | Export CSV | Save HTML]
        [QTextBrowser — HTML report]
        [Close]

    Public API para tests
    ----------------------

    * ``load_demo()`` — popula com 7 equipamentos demo
    * ``run_evaluation()`` — re-roda eval com equipamentos atuais
    * ``equipments`` (list) — lista atual de EquipmentInstances
    * ``last_html`` (str) — HTML do último report gerado
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "📋 Equipment Evaluation Dashboard — "
            "Olivas Power System Studio"
        )
        self.resize(1100, 700)

        self.equipments: list = []
        self.last_html: str = ""

        self._setup_ui()
        # Carrega demo automaticamente ao abrir (UX: usuário vê
        # algo logo de cara)
        self.load_demo()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(
            "Avaliação Automática de Equipamentos — "
            "9 critérios IEEE 242 §15 + NBR 5410 §6.2.7"
        )
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        # Status + buttons toolbar
        toolbar_layout = QHBoxLayout()
        self.status_label = QLabel("0 equipamentos carregados")
        toolbar_layout.addWidget(self.status_label)
        toolbar_layout.addStretch()

        self.btn_demo = QPushButton("🎲 Carregar Demo")
        self.btn_demo.clicked.connect(self.load_demo)
        toolbar_layout.addWidget(self.btn_demo)

        # v3.7.2 (closes SKIPPED_BACKLOG C.2) — hybrid mode toggle:
        # quando checked, demo benchmarks ficam ALONGSIDE do project.
        from PySide6.QtWidgets import QCheckBox as _QCheckBox
        self.chk_hybrid_demo = _QCheckBox("➕ Manter demo junto ao projeto")
        self.chk_hybrid_demo.setToolTip(
            "v3.7.2 — Quando carregar via projeto, mantém os 7 demos "
            "como benchmarks adjacentes (não sobrescreve)."
        )
        toolbar_layout.addWidget(self.chk_hybrid_demo)

        self.btn_export_csv = QPushButton("💾 Exportar CSV")
        self.btn_export_csv.clicked.connect(self._on_export_csv)
        toolbar_layout.addWidget(self.btn_export_csv)

        self.btn_save_html = QPushButton("💾 Salvar HTML")
        self.btn_save_html.clicked.connect(self._on_save_html)
        toolbar_layout.addWidget(self.btn_save_html)

        layout.addLayout(toolbar_layout)

        # Browser para HTML
        self.html_browser = QTextBrowser()
        self.html_browser.setOpenExternalLinks(True)
        layout.addWidget(self.html_browser, stretch=1)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    # ---------------------------------------------------------------
    # Public API (também usada por testes)
    # ---------------------------------------------------------------

    def load_demo(self) -> None:
        """Popula com 7 equipamentos demo + roda evaluation."""
        self.equipments = _build_demo_equipment()
        self.run_evaluation()

    def set_equipments(self, equipments: list) -> None:
        """Setter para equipamentos vindos de fora (testes / projeto).

        v3.7.2 (closes SKIPPED_BACKLOG C.2): se ``chk_hybrid_demo`` está
        marcado, mantém os 7 demos como benchmark adjacente.
        """
        if (hasattr(self, "chk_hybrid_demo")
                and self.chk_hybrid_demo.isChecked()):
            self.equipments = _build_demo_equipment() + list(equipments)
        else:
            self.equipments = list(equipments)
        self.run_evaluation()

    def run_evaluation(self) -> None:
        """Roda PTW_EQUIPMENT_EVALUATION + atualiza HTML browser."""
        if not self.equipments:
            self.html_browser.setHtml(
                "<p>Nenhum equipamento carregado.</p>"
            )
            self.status_label.setText("0 equipamentos")
            self.last_html = ""
            return

        reports = evaluate_project(
            self.equipments, PTW_EQUIPMENT_EVALUATION,
        )
        self.last_html = generate_html_dashboard(
            reports,
            project_title="Olivas Power System Studio — "
                          "Equipment Evaluation",
            norm_reference="IEEE 242 §15 + NBR 5410 §6.2.7 + "
                           "ANSI C37.04",
        )
        self.html_browser.setHtml(self.last_html)
        n_pass = sum(1 for r in reports if r.passes_all())
        n_fail = sum(1 for r in reports if r.has_failures())
        self.status_label.setText(
            f"{len(self.equipments)} equipamentos · "
            f"{n_pass} PASS · {n_fail} FAIL"
        )

    # ---------------------------------------------------------------
    # Slots dos botões
    # ---------------------------------------------------------------

    def _on_export_csv(self) -> None:
        """Salva CSV via QFileDialog."""
        if not self.equipments:
            QMessageBox.warning(
                self, "Nenhum equipamento",
                "Carregue equipamentos antes de exportar.",
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Equipment Evaluation CSV",
            "equipment_evaluation.csv",
            "CSV files (*.csv)",
        )
        if not path:
            return
        reports = evaluate_project(
            self.equipments, PTW_EQUIPMENT_EVALUATION,
        )
        csv = export_csv(reports)
        with open(path, "w", encoding="utf-8") as f:
            f.write(csv)
        QMessageBox.information(
            self, "Exportado",
            f"CSV salvo em:\n{path}",
        )

    def _on_save_html(self) -> None:
        """Salva HTML via QFileDialog."""
        if not self.last_html:
            QMessageBox.warning(
                self, "Sem report",
                "Rode a evaluation antes de salvar.",
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Equipment Evaluation Dashboard HTML",
            "equipment_evaluation.html",
            "HTML files (*.html)",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.last_html)
        QMessageBox.information(
            self, "Salvo",
            f"HTML salvo em:\n{path}",
        )
