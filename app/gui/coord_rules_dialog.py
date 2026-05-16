"""
app.gui.coord_rules_dialog — Coordination Rules Engine GUI
dialog (v1.3.1 G.2).

Filosofia
==========

PTW Power*Tools "Coordination Evaluation" mostra dashboard
tabular de regras NEC 110.10 + IEEE 242 aplicadas a cada
dispositivo de proteção. Olivas v1.3.0 entregou o Rule Engine
(`coord_rules.py` + `coord_rules_builtin.py`) com 8 rules em
4 RuleSets, mas sem GUI.

Esta sub-sprint G.2 entrega o dialog que:
1. Mostra os 4 RuleSets disponíveis com checkboxes
2. Carrega TCCDevices/DamageCurves demo (ou do projeto)
3. Aplica RuleSets selecionados via RuleEngine
4. Renderiza resultados em QTreeWidget colored

Cobertura normativa
====================

* NEC 110.10 (proteção upstream rules)
* IEEE 242:2001 §9, §11, §15
* NBR 5410:2004 §5.7.5 (cable damage 80%)
* IEC C57.109 (XFMR through-fault)
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.postprocessor.coord_rules import RuleEngine, RuleSeverity
from app.postprocessor.coord_rules_builtin import (
    ALL_BUILTIN_RULESETS,
    BEST_PRACTICES,
    NBR_CABLE_RULES,
    NEC_MOTOR_PROTECTION,
    NEC_TRANSFORMER_PROTECTION,
)
from app.postprocessor.tcc_curves import CurveType
from app.postprocessor.tcc_damage import (
    CableDamageCurve, CableMaterial,
    MotorThermalCurve,
    TransformerThroughFaultCurve, XfmrFaultCategory,
)
from app.postprocessor.tcc_devices import MultiFunctionRelay


# ---------------------------------------------------------------------------
# Cores semantic (paleta PTW Olivas)
# ---------------------------------------------------------------------------


_SEVERITY_COLORS = {
    RuleSeverity.PASS: QColor("#2E7D32"),
    RuleSeverity.WARN: QColor("#F9A825"),
    RuleSeverity.FAIL: QColor("#C0392B"),
    RuleSeverity.NOT_APPLICABLE: QColor("#9E9E9E"),
}

_SEVERITY_LABELS = {
    RuleSeverity.PASS: "✓ PASS",
    RuleSeverity.WARN: "⚠ WARN",
    RuleSeverity.FAIL: "✗ FAIL",
    RuleSeverity.NOT_APPLICABLE: "— N/A",
}


# ---------------------------------------------------------------------------
# Demo targets
# ---------------------------------------------------------------------------


def _build_demo_targets_with_context() -> list:
    """
    Constrói lista de (target, context_dict) demo com mix de
    devices + damage curves cobrindo cenários PASS/WARN/FAIL.

    Returns
    -------
    list[tuple[target, context_dict]]
    """
    motor_relay_good = MultiFunctionRelay.relay_51_50_49(
        device_id="R-MOT-1",
        curve_type=CurveType.IEC_STANDARD_INVERSE,
        pickup_51_A=120,    # 120% FLA (no range 115-125%) → PASS
        tms_51=0.20,
        pickup_50_A=600,    # 6× FLA → PASS
        pickup_49_A=150, delay_49_s=8.0,  # 150% FLA → PASS
        manufacturer="SEL", model="751",
    )
    motor_relay_bad = MultiFunctionRelay.relay_51_50_49(
        device_id="R-MOT-BAD",
        curve_type=CurveType.IEC_STANDARD_INVERSE,
        pickup_51_A=200,   # 200% FLA → FAIL
        tms_51=0.20,
        pickup_50_A=200,   # 2× FLA → FAIL (trip em starting)
        pickup_49_A=300, delay_49_s=8.0,  # 300% FLA → FAIL
    )
    cable = CableDamageCurve(
        cable_id="C-FEEDER-50mm2",
        section_mm2=50,
        material=CableMaterial.Cu_XLPE,
    )
    xfmr = TransformerThroughFaultCurve(
        xfmr_id="T1-13.8/0.48",
        rated_current_A=100,
        category=XfmrFaultCategory.FREQUENT,
    )
    motor_thermal = MotorThermalCurve(
        motor_id="M-PUMP-1", fla_A=100,
    )

    return [
        (motor_relay_good, {"fla_A": 100.0}),
        (motor_relay_bad, {"fla_A": 100.0}),
        (cable, {
            "protection_device": motor_relay_good,
            "fault_current_A": 5000,
        }),
        (xfmr, {
            "protection_device": motor_relay_good,
            "fault_current_A": 1000,
        }),
        (motor_thermal, {
            "protection_device": motor_relay_good,
        }),
    ]


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


class CoordRulesDialog(QDialog):
    """
    Dialog QDialog para Coord Rule Engine.

    Layout:
    [Title]
    [RuleSet selector (horizontal checkboxes)]
    [Action buttons: Apply / Demo]
    [Results tree: Target → Rule → Severity / Message]
    [Close]

    Public API:
    * load_demo() — carrega 5 targets demo
    * apply_selected_rulesets() — aplica RuleSets selecionados
    * results (list[RuleResult]) — últimos resultados
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "🛡️ Coordination Rules Engine — "
            "Olivas Power System Studio"
        )
        self.resize(1100, 700)

        self.targets_with_ctx: list = []
        self.results: list = []
        self._engine = RuleEngine()

        self._setup_ui()
        self.load_demo()
        self.apply_selected_rulesets()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(
            "Coordination Rule Engine — "
            "NEC 110.10 + IEEE 242 + NBR + Best Practices"
        )
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        # RuleSet selector
        layout.addWidget(QLabel("RuleSets a aplicar:"))
        rs_layout = QHBoxLayout()
        self._ruleset_checkboxes = {}
        for rs in ALL_BUILTIN_RULESETS:
            cb = QCheckBox(f"{rs.name} ({len(rs)} rules)")
            cb.setChecked(True)
            cb.setToolTip(rs.norm_reference)
            self._ruleset_checkboxes[rs.name] = (rs, cb)
            rs_layout.addWidget(cb)
        rs_layout.addStretch()
        layout.addLayout(rs_layout)

        # Toolbar buttons
        btn_layout = QHBoxLayout()
        self.status_label = QLabel("Pronto.")
        btn_layout.addWidget(self.status_label)
        btn_layout.addStretch()

        self.btn_demo = QPushButton("🎲 Recarregar Demo")
        self.btn_demo.clicked.connect(self._on_demo_and_apply)
        btn_layout.addWidget(self.btn_demo)

        self.btn_apply = QPushButton("▶ Aplicar regras")
        self.btn_apply.clicked.connect(self.apply_selected_rulesets)
        btn_layout.addWidget(self.btn_apply)

        layout.addLayout(btn_layout)

        # Results tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            "Target / Rule", "Severity", "Message", "Citation",
        ])
        self.tree.setColumnWidth(0, 280)
        self.tree.setColumnWidth(1, 90)
        self.tree.setColumnWidth(2, 400)
        layout.addWidget(self.tree, stretch=1)

        # Close
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    def load_demo(self) -> None:
        """Carrega 5 targets demo + contexts."""
        self.targets_with_ctx = _build_demo_targets_with_context()

    def _on_demo_and_apply(self) -> None:
        self.load_demo()
        self.apply_selected_rulesets()

    def selected_rulesets(self) -> list:
        """Lista de RuleSets selecionados (checkbox ativo)."""
        return [
            rs for rs, cb in self._ruleset_checkboxes.values()
            if cb.isChecked()
        ]

    def apply_selected_rulesets(self) -> None:
        """
        Aplica RuleSets selecionados a todos os targets demo.
        Atualiza o tree.
        """
        if not self.targets_with_ctx:
            return
        rulesets = self.selected_rulesets()
        if not rulesets:
            self.tree.clear()
            self.status_label.setText("Nenhum RuleSet selecionado.")
            return

        all_results = []
        # Para cada (target, ctx): aplica todos os RuleSets selecionados
        for target, ctx in self.targets_with_ctx:
            for rs in rulesets:
                results = self._engine.apply_ruleset(rs, [target], ctx)
                all_results.extend(results)
        self.results = all_results
        self._populate_tree()

        # Status summary
        counts = self._engine.count_by_severity(all_results)
        self.status_label.setText(
            f"{len(self.targets_with_ctx)} targets · "
            f"{len(all_results)} verificações · "
            f"PASS={counts[RuleSeverity.PASS]} · "
            f"WARN={counts[RuleSeverity.WARN]} · "
            f"FAIL={counts[RuleSeverity.FAIL]} · "
            f"N/A={counts[RuleSeverity.NOT_APPLICABLE]}"
        )

    def _populate_tree(self) -> None:
        """Popula QTreeWidget com results agrupados por target."""
        self.tree.clear()
        # Agrupa por target_id
        by_target: dict = {}
        for r in self.results:
            by_target.setdefault(r.target_id, []).append(r)

        for target_id, target_results in by_target.items():
            target_item = QTreeWidgetItem([
                target_id, "", "", "",
            ])
            font = QFont()
            font.setBold(True)
            target_item.setFont(0, font)
            # Determina severity overall do target
            has_fail = any(r.is_fail() for r in target_results)
            has_warn = any(r.is_warn() for r in target_results)
            if has_fail:
                overall = RuleSeverity.FAIL
            elif has_warn:
                overall = RuleSeverity.WARN
            elif any(r.is_pass() for r in target_results):
                overall = RuleSeverity.PASS
            else:
                overall = RuleSeverity.NOT_APPLICABLE
            target_item.setText(1, _SEVERITY_LABELS[overall])
            color = _SEVERITY_COLORS[overall]
            target_item.setForeground(1, QBrush(color))

            # Rule rows como children
            for r in target_results:
                child = QTreeWidgetItem([
                    f"  {r.rule_id}",
                    _SEVERITY_LABELS[r.severity],
                    r.message,
                    r.citation,
                ])
                child.setForeground(
                    1, QBrush(_SEVERITY_COLORS[r.severity]),
                )
                target_item.addChild(child)

            self.tree.addTopLevelItem(target_item)
            target_item.setExpanded(True)
