"""
app.gui.demand_load_dialog — UI do estudo Demand Load (DAPPER)
(v1.5.1 Sprint D).

Dialog Qt nativo para invocar o estudo:

* **Tabela de entries** (top): nome, categoria (ComboBox com 22
  opções), connected kVA, PF override
* **Botões**: Adicionar entry, Calcular, Salvar TXT, Salvar XLSX
* **3 tabs de resultado**:
  - 📋 Sumário (texto consolidado)
  - 📊 Por Categoria (QTableWidget)
  - 📈 Detalhe (entries originais)

Princípios (paridade lessons learned v1.4.5 + v1.5.0):

* Sem QMessageBox bloqueante em testes (status feedback via
  setWindowTitle)
* Empty state explicativo
* Defaults didáticos pré-populados (auto-run no init)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.postprocessor.dapper_catalog import (
    DAPPER_CATALOG, get_category,
)
from app.postprocessor.studies.demand_load import (
    LoadEntry, compute_demand,
)


# Defaults didáticos (auto-populated)
_DEMO_ENTRIES = [
    ("Iluminação geral edifício A", "NEC_220_42_LIGHTING", 50.0),
    ("Motor processo M1", "NEC_220_50_MOTORS", 75.0),
    ("Tomadas escritório", "RECEPTACLES_GENERAL", 25.0),
    ("Banco capacitor BC1", "CAPACITOR_BANK", 100.0),
    ("Sala TI / DC", "DATA_CENTER", 30.0),
]


class DemandLoadDialog(QDialog):
    """
    Dialog para invocar o estudo Demand Load (DAPPER).

    Não exige seleção de componente no canvas (paridade PTW
    DAPPER que opera sobre o sistema todo). Em release futura
    (v1.6+), pode integrar com BUS selecionado.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "⚡ Demand Load Study (DAPPER) — Olivas Power System Studio"
        )
        self.resize(1200, 850)
        self.setMinimumWidth(1100)

        # v1.7.0 Sprint A: maximize/minimize controls
        from app.gui.window_state_mixin import enable_window_controls
        enable_window_controls(self, settings_key="demand_load")

        self._last_report = None
        self._setup_ui()
        self._populate_demo_entries()
        # Auto-run com defaults
        self._on_calculate()

    # -----------------------------------------------------------------
    # UI build
    # -----------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(
            "<h2>⚡ Demand Load Study (DAPPER)</h2>"
            "<i>Cálculo Connected → Demand → Design com 22 categorias "
            "NEC 220 + sectors industriais/comerciais BR.</i>"
        )
        layout.addWidget(header)

        # Banner explicativo
        banner = QLabel(
            "📚 <b>Como usar:</b> Adicione entries (cargas), atribua "
            "categoria, informe kVA conectado e clique <b>Calcular</b>. "
            "Se PF for None, usa o típico da categoria."
        )
        banner.setWordWrap(True)
        banner.setStyleSheet(
            "QLabel { background-color: #E3F2FD; "
            "border-left: 3px solid #1976D2; "
            "padding: 6px 10px; }"
        )
        layout.addWidget(banner)

        # ----- Tabela de entries -----
        layout.addWidget(QLabel("<b>Cargas (Load Entries):</b>"))
        self.entries_table = QTableWidget(0, 4)
        self.entries_table.setHorizontalHeaderLabels(
            ["Nome", "Categoria", "Connected (kVA)", "PF override"]
        )
        header_view = self.entries_table.horizontalHeader()
        header_view.setSectionResizeMode(
            0, QHeaderView.Stretch,
        )
        header_view.setSectionResizeMode(
            1, QHeaderView.Stretch,
        )
        layout.addWidget(self.entries_table, 1)

        # Action row
        actions = QHBoxLayout()
        self.btn_add_entry = QPushButton("➕ Adicionar entry")
        self.btn_add_entry.clicked.connect(self._on_add_entry)
        actions.addWidget(self.btn_add_entry)

        self.btn_remove_entry = QPushButton("➖ Remover selecionada")
        self.btn_remove_entry.clicked.connect(self._on_remove_entry)
        actions.addWidget(self.btn_remove_entry)

        self.btn_calculate = QPushButton("▶ Calcular")
        self.btn_calculate.setStyleSheet(
            "QPushButton { background-color: #2ca02c; "
            "color: white; font-weight: bold; padding: 4px 14px; }"
        )
        self.btn_calculate.clicked.connect(self._on_calculate)
        actions.addWidget(self.btn_calculate)

        actions.addStretch()

        self.btn_save_txt = QPushButton("💾 Salvar TXT")
        self.btn_save_txt.clicked.connect(self._on_save_txt)
        actions.addWidget(self.btn_save_txt)

        self.btn_save_xlsx = QPushButton("💾 Salvar XLSX")
        self.btn_save_xlsx.clicked.connect(self._on_save_xlsx)
        actions.addWidget(self.btn_save_xlsx)

        layout.addLayout(actions)

        # ----- Tabs de resultado -----
        self.tabs = QTabWidget()
        self._build_summary_tab()
        self._build_by_category_tab()
        layout.addWidget(self.tabs, 1)

        # Close
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText("Fechar")
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _build_summary_tab(self) -> None:
        page = QWidget()
        v = QVBoxLayout(page)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Consolas", 10))
        v.addWidget(self.summary_text)
        self.tabs.addTab(page, "📋 Sumário")

    def _build_by_category_tab(self) -> None:
        page = QWidget()
        v = QVBoxLayout(page)
        self.cat_table = QTableWidget(0, 7)
        self.cat_table.setHorizontalHeaderLabels([
            "Categoria", "NEC §",
            "Connected (kVA)", "Demand (kVA)", "Design (kVA)",
            "PF", "LCL",
        ])
        self.cat_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch,
        )
        v.addWidget(self.cat_table)
        self.tabs.addTab(page, "📊 Por Categoria")

    # -----------------------------------------------------------------
    # Entries table population
    # -----------------------------------------------------------------

    def _make_category_combo(
        self, default_code: Optional[str] = None,
    ) -> QComboBox:
        combo = QComboBox()
        for cat in DAPPER_CATALOG:
            tag = cat.nec_section or "sector"
            text = f"[{tag}] {cat.label_pt}"
            combo.addItem(text, cat.code)
        if default_code:
            for i in range(combo.count()):
                if combo.itemData(i) == default_code:
                    combo.setCurrentIndex(i)
                    break
        return combo

    def _add_entry_row(
        self,
        name: str = "Nova carga",
        category_code: str = "NEC_220_42_LIGHTING",
        connected_kVA: float = 10.0,
        pf: Optional[float] = None,
    ) -> int:
        row = self.entries_table.rowCount()
        self.entries_table.insertRow(row)

        # Coluna 0: nome
        self.entries_table.setItem(row, 0, QTableWidgetItem(name))

        # Coluna 1: ComboBox categoria
        combo = self._make_category_combo(default_code=category_code)
        self.entries_table.setCellWidget(row, 1, combo)

        # Coluna 2: SpinBox connected
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 100000.0)
        spin.setValue(connected_kVA)
        spin.setSuffix(" kVA")
        spin.setDecimals(1)
        self.entries_table.setCellWidget(row, 2, spin)

        # Coluna 3: PF override (line edit)
        pf_edit = QLineEdit()
        if pf is not None:
            pf_edit.setText(f"{pf:.2f}")
        pf_edit.setPlaceholderText("auto")
        self.entries_table.setCellWidget(row, 3, pf_edit)

        return row

    def _populate_demo_entries(self) -> None:
        for name, code, kVA in _DEMO_ENTRIES:
            self._add_entry_row(
                name=name, category_code=code, connected_kVA=kVA,
            )

    def _read_entries_from_table(self) -> list:
        """Lê tabela GUI → lista de :class:`LoadEntry`."""
        entries = []
        for row in range(self.entries_table.rowCount()):
            name_item = self.entries_table.item(row, 0)
            name = name_item.text() if name_item else f"Row {row+1}"

            combo = self.entries_table.cellWidget(row, 1)
            code = combo.currentData() if combo else ""

            spin = self.entries_table.cellWidget(row, 2)
            connected = spin.value() if spin else 0.0

            pf_edit = self.entries_table.cellWidget(row, 3)
            pf = None
            if pf_edit:
                txt = pf_edit.text().strip()
                if txt:
                    try:
                        pf = float(txt.replace(",", "."))
                    except ValueError:
                        pf = None

            if connected > 0 and code:
                entries.append(LoadEntry(
                    name=name,
                    category_code=code,
                    connected_kVA=connected,
                    pf=pf,
                ))
        return entries

    # -----------------------------------------------------------------
    # Slots
    # -----------------------------------------------------------------

    def _on_add_entry(self) -> None:
        self._add_entry_row()

    def _on_remove_entry(self) -> None:
        rows = sorted(
            {idx.row() for idx in self.entries_table.selectedIndexes()},
            reverse=True,
        )
        for r in rows:
            self.entries_table.removeRow(r)

    def _on_calculate(self) -> None:
        """Lê entries → roda compute_demand → atualiza tabs."""
        try:
            entries = self._read_entries_from_table()
            if not entries:
                self.summary_text.setPlainText(
                    "Sem entries com kVA > 0. "
                    "Adicione cargas e clique Calcular."
                )
                return
            report = compute_demand(entries)
            self._last_report = report

            # Tab Sumário
            self.summary_text.setPlainText(report.summary())

            # Tab Por Categoria
            self.cat_table.setRowCount(0)
            for cr in report.by_category:
                row = self.cat_table.rowCount()
                self.cat_table.insertRow(row)
                self.cat_table.setItem(
                    row, 0, QTableWidgetItem(cr.category_label_pt),
                )
                self.cat_table.setItem(
                    row, 1, QTableWidgetItem(cr.nec_section or "—"),
                )
                self.cat_table.setItem(
                    row, 2,
                    QTableWidgetItem(f"{cr.connected_kVA:.1f}"),
                )
                self.cat_table.setItem(
                    row, 3,
                    QTableWidgetItem(f"{cr.demand_kVA:.1f}"),
                )
                self.cat_table.setItem(
                    row, 4,
                    QTableWidgetItem(f"{cr.design_kVA:.1f}"),
                )
                self.cat_table.setItem(
                    row, 5,
                    QTableWidgetItem(f"{cr.pf:.3f}"),
                )
                self.cat_table.setItem(
                    row, 6,
                    QTableWidgetItem(f"{cr.lcl_factor:.2f}"),
                )

            self.setWindowTitle(
                f"⚡ Demand Load: "
                f"{report.total_connected_kVA:.0f} → "
                f"{report.total_demand_kVA:.0f} → "
                f"{report.total_design_kVA:.0f} kVA "
                f"(PF {report.weighted_pf:.2f})"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Erro no cálculo",
                f"{type(e).__name__}: {e}",
            )

    def _on_save_txt(self) -> None:
        if self._last_report is None:
            self.setWindowTitle(
                "⚡ Calcule antes de salvar TXT"
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar relatório TXT",
            "Demand_Load_Study.txt", "Texto (*.txt)",
        )
        if not path:
            return
        from app.postprocessor.dapper_io import write_demand_report_txt
        write_demand_report_txt(self._last_report, Path(path))
        self.setWindowTitle(f"⚡ TXT salvo: {Path(path).name}")

    def _on_save_xlsx(self) -> None:
        if self._last_report is None:
            self.setWindowTitle(
                "⚡ Calcule antes de salvar XLSX"
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar datasheet XLSX",
            "Demand_Load_Study.xlsx", "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            from app.postprocessor.dapper_io import (
                write_demand_report_xlsx,
            )
            write_demand_report_xlsx(self._last_report, Path(path))
            self.setWindowTitle(f"⚡ XLSX salvo: {Path(path).name}")
        except ImportError:
            QMessageBox.warning(
                self, "openpyxl ausente",
                "Instale openpyxl: pip install openpyxl",
            )
