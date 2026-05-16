"""
app.gui.arc_flash_label_dialog — Custom Label Designer GUI
(v1.4.0 sub-sprint B).

Filosofia
==========

PTW Power*Tools "Custom Label Designer" oferece editor visual
drag-drop dos 30+ fields. Olivas v1.4.0 entrega versão
funcional simplificada:

* Tabela editable (QTableWidget) com 30 rows × 2 cols
  (field_name + value)
* Combo "Estilo" com 3 templates
  (NFPA_70E_2024 / NESC_2023_TYPE_4_5 / MINIMAL_BR)
* Preview HTML live em QTextBrowser
* Botões: Carregar Demo / Save HTML / Imprimir

Drag-drop visual de campos fica para v1.4.2+.

Cobertura normativa
====================

* NFPA 70E:2024 §130.5(H) (campos obrigatórios do label)
* IEEE Std 1584-2018 (cálculos arc-flash subjacentes)
* NBR 17227:2025 (versão brasileira)
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.postprocessor.arc_flash_label import (
    ArcFlashLabel,
    LabelStyle,
    render_html_label,
)


# Friendly display names para cada field (PT-BR)
_FIELD_LABELS_PT = {
    "bus_name": "Bus / Equipamento",
    "bus_kV": "Tensão nominal (kV)",
    "label_number": "Label #",
    "equipment_owner": "Proprietário equipamento",
    "Ibf_kA": "Bolted Fault Current (kA)",
    "Iarc_kA": "Arcing Fault Current (kA)",
    "arc_duration_ms": "Duração do arco (ms)",
    "equipment_type": "Tipo equipamento",
    "gap_mm": "Gap (mm)",
    "working_distance_mm": "Distância trabalho (mm)",
    "electrode_config": "Config. eletrodos",
    "incident_energy_cal_cm2": "Energia incidente (cal/cm²)",
    "arc_flash_boundary_mm": "Limite arc-flash DLA (mm)",
    "ppe_category": "PPE Category",
    "ppe_description": "PPE descrição",
    "ppe_arc_rating_min_cal_cm2": "Min arc-rating EPI (cal/cm²)",
    "limited_approach_mm": "Aproximação limitada (mm)",
    "restricted_approach_mm": "Aproximação restrita (mm)",
    "glove_class": "Classe luva",
    "glove_voltage_V": "Tensão luva (V)",
    "shock_hazard_voltage_V": "Tensão choque (V)",
    "flash_hazard_range": "Flash hazard range",
    "head_eye_hearing_protection": "EPI cabeça/olhos/audição",
    "hand_arm_protection": "EPI mãos/braços",
    "foot_protection": "EPI pés",
    "notes": "Notas",
    "date_computed": "Data cálculo",
    "computed_by": "Calculado por",
    "project_title": "Projeto",
    "audit_sha256": "Audit SHA256",
}


def _build_demo_label() -> ArcFlashLabel:
    """
    Constrói label demo via cálculo arc-flash real (BUS 13.8 kV,
    25 kA fault). Engenheiro vê o dialog populated logo de cara.
    """
    from app.postprocessor.arc_flash import (
        ArcFlashCase, ElectrodeConfig, EquipmentClass,
        calculate_arc_flash,
    )
    case = ArcFlashCase(
        bus_name="BUS-MAIN-13.8kV",
        rated_voltage_kV=13.8,
        bolted_fault_current_kA=25.0,
        arc_clearing_time_ms=200.0,
        gap_mm=153.0,
        working_distance_mm=914.0,
        electrode_config=ElectrodeConfig.VCB,
        equipment_class=EquipmentClass.SWITCHGEAR_15KV,
    )
    report = calculate_arc_flash(case)
    return ArcFlashLabel.from_arc_flash_report(
        report,
        label_number="AF-DEMO-001",
        equipment_owner="Subestação Demo",
        project_title="Olivas Power System Studio — Demo",
        date_computed="2026-04-28",
        computed_by="Engenheiro Demo",
        notes="Cenário demo — substitua por valores reais do "
              "seu projeto.",
        audit_sha256="(demo — sem audit real)",
    )


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


class LabelDesignerDialog(QDialog):
    """
    Custom Label Designer dialog.

    Layout
    -------

    Splitter horizontal:
    * Esquerda: Tabela editable (30 rows × 2 cols)
    * Direita: Preview HTML live (QTextBrowser)

    Top toolbar: Style combo + Load Demo + Save HTML + Print

    Public API
    -----------

    * ``label`` (ArcFlashLabel) — label atual
    * ``style`` (LabelStyle) — estilo selecionado
    * ``set_label(label)`` — popula campos da tabela a partir
      de um label
    * ``current_label_from_table()`` — lê tabela e constrói
      ArcFlashLabel
    * ``refresh_preview()`` — atualiza HTML browser
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "🏷️ Custom Label Designer (Arc-Flash) — "
            "Olivas Power System Studio"
        )
        self.resize(1300, 800)

        self.label: ArcFlashLabel = ArcFlashLabel()
        self.style: LabelStyle = LabelStyle.NFPA_70E_2024

        # Debounce timer: re-render preview 300ms após último edit
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(300)
        self._refresh_timer.timeout.connect(self.refresh_preview)

        self._setup_ui()
        # Load demo automaticamente ao abrir
        self.set_label(_build_demo_label())

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(
            "Designer de Label Arc-Flash — "
            "30 campos editáveis, 3 estilos (NFPA 70E / NESC / NBR)"
        )
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Estilo:"))
        self.style_combo = QComboBox()
        for st in LabelStyle:
            self.style_combo.addItem(st.value, st)
        self.style_combo.currentIndexChanged.connect(self._on_style_changed)
        toolbar.addWidget(self.style_combo)
        toolbar.addStretch()

        self.btn_demo = QPushButton("🎲 Carregar Demo")
        self.btn_demo.clicked.connect(self._on_load_demo)
        toolbar.addWidget(self.btn_demo)

        self.btn_save_html = QPushButton("💾 Salvar HTML")
        self.btn_save_html.clicked.connect(self._on_save_html)
        toolbar.addWidget(self.btn_save_html)

        layout.addLayout(toolbar)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, stretch=1)

        # Left: Table
        self.table = QTableWidget()
        # 30 fields → 30 rows
        fields = list(ArcFlashLabel.__dataclass_fields__)
        self.table.setRowCount(len(fields))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Campo", "Valor"])
        self.table.verticalHeader().setVisible(False)
        for i, fname in enumerate(fields):
            display = _FIELD_LABELS_PT.get(fname, fname)
            name_item = QTableWidgetItem(display)
            name_item.setFlags(Qt.ItemIsEnabled)  # não editable
            name_item.setData(Qt.UserRole, fname)
            self.table.setItem(i, 0, name_item)
            value_item = QTableWidgetItem("")
            self.table.setItem(i, 1, value_item)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents,
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch,
        )
        self.table.itemChanged.connect(self._on_table_edit)
        splitter.addWidget(self.table)

        # Right: HTML preview
        self.html_browser = QTextBrowser()
        self.html_browser.setOpenExternalLinks(True)
        splitter.addWidget(self.html_browser)
        splitter.setSizes([550, 750])

        # Close button
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    def set_label(self, label: ArcFlashLabel) -> None:
        """Popula tabela + atualiza preview a partir de um label."""
        self.label = label
        # Bloqueia signals para não disparar refresh por edit
        self.table.blockSignals(True)
        for i in range(self.table.rowCount()):
            name_item = self.table.item(i, 0)
            fname = name_item.data(Qt.UserRole)
            value = getattr(label, fname, "")
            value_item = self.table.item(i, 1)
            value_item.setText(value)
        self.table.blockSignals(False)
        self.refresh_preview()

    def current_label_from_table(self) -> ArcFlashLabel:
        """Lê tabela e constrói ArcFlashLabel."""
        kwargs = {}
        for i in range(self.table.rowCount()):
            fname = self.table.item(i, 0).data(Qt.UserRole)
            value = self.table.item(i, 1).text()
            kwargs[fname] = value
        return ArcFlashLabel(**kwargs)

    def refresh_preview(self) -> None:
        """Re-renderiza HTML preview com label + style atuais."""
        self.label = self.current_label_from_table()
        html = render_html_label(self.label, self.style)
        self.html_browser.setHtml(html)

    # ---------------------------------------------------------------
    # Slots
    # ---------------------------------------------------------------

    def _on_table_edit(self, item) -> None:
        """Edit numa célula → debounce 300ms → refresh."""
        # Só dispara se foi a coluna de valores (col 1)
        if item.column() != 1:
            return
        self._refresh_timer.start()

    def _on_style_changed(self, idx: int) -> None:
        """Style combo mudou → re-render imediato."""
        self.style = self.style_combo.itemData(idx)
        self.refresh_preview()

    def _on_load_demo(self) -> None:
        """Botão Demo: re-popula com label demo."""
        self.set_label(_build_demo_label())

    def _on_save_html(self) -> None:
        """Salva HTML via QFileDialog."""
        # Garante que label está sincronizado
        self.refresh_preview()
        html = render_html_label(self.label, self.style)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Label Arc-Flash HTML",
            "arc_flash_label.html",
            "HTML files (*.html)",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        QMessageBox.information(
            self, "Label salvo",
            f"Label HTML salvo em:\n{path}\n\n"
            "Abra no browser e use Ctrl+P para imprimir "
            "(modo paisagem A6 recomendado).",
        )
