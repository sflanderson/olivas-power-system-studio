"""
app.gui.ct_saturation_dialog — CT Saturation **STUDY** completo
(v1.4.4 — paridade total MATLAB CT_STUDY + Olivas).

Replica o workflow completo do MATLAB ``main_CT_Analysis.m`` com:

* Form de inputs (CTSpec + CTFaultContext) + auto-run
* Botão **Importar dados de TCs (JSON)** — lê listas de TCs em formato
  JSON (compatível com export de SKM PTW, ETAP, EasyPower; sem
  integração ativa)
* Botão **Re-dimensionar** (próxima classe ANSI quando FALHOU)
* 4 Tabs:
    1. 📋 Sumário texto (CTSaturationReport.summary())
    2. 📊 Nível 1 (ANSI estático): barras condicionais V_tap vs V_req
    3. 🎯 Nível 2 (IEC joelho): log-log com marcadores + zonas
    4. ⚡ Nível 3 (Dinâmico): fluxo λ(t) + correntes ideal vs real
* Botões de exportação **TXT** e **XLSX** (paridade ``generate_reports.m``)

Cobertura normativa
====================

* IEEE C37.13.1-2017 (ANSI estático)
* IEEE C37.110-2007 (CT for Relaying)
* IEC 61869-2:2012 (curva 10/50)
* CIGRÉ WG 23-15 (saturação dinâmica)
* ABNT NBR 6856:2015
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
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def _build_demo_inputs():
    """Defaults didáticos (TC 2000:5 ANSI C400 @ 13.8 kV, Icc 20 kA, X/R 10)."""
    return {
        "bus_id": "BUS-MAIN",
        "rated_voltage_kV": 13.8,
        "I_fault_rms_kA": 20.0,
        "X_over_R": 10.0,
        "tag": "CT-1",
        "tipo_TC": "ANSI_C",
        "I_pri_nom_tap": 2000,
        "I_pri_nom_full": 2000,
        "I_sn": 5,
        "CT_Rating_C": 400.0,
        "R_s": 0.5,
        "R_b": 0.3,
        "Kr": 0.1,
    }


class CTSaturationDialog(QDialog):
    """
    Dialog GUI completo para CT Saturation Study (3 níveis + IO + workflow).

    Public attributes
    -----------------
    * ``_last_report`` — último :class:`CTSaturationReport` gerado
    * ``results_tabs`` — QTabWidget com 4 tabs
    * ``btn_load_json``, ``btn_save_txt``, ``btn_save_xlsx``,
      ``btn_redimension`` — botões de ação
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        selection=None,   # CTSelection | None
    ) -> None:
        """
        v1.4.5: aceita ``selection: CTSelection`` para popular
        o form a partir de um TC selecionado no canvas
        (workflow PTW-style — ver design doc v1.4.5).

        Sem selection → modo didático (defaults pré-populados).
        """
        super().__init__(parent)
        self.setWindowTitle(
            "🔍 Análise de Saturação de TC — "
            "Olivas Power System Studio"
        )
        # v1.4.5: aumentado para 1280×900 — feedback user gate v1.4.4
        # ("janelas e gráficos mal dimensionados"). Largura mínima
        # garante espaço para os 2 GroupBoxes lado a lado + tabs.
        self.resize(1280, 900)
        self.setMinimumWidth(1280)

        # v1.7.0 Sprint A: maximize/minimize controls + remember size
        from app.gui.window_state_mixin import enable_window_controls
        enable_window_controls(self, settings_key="ct_saturation")

        self._last_report = None
        self._json_table = []   # cache da tabela list_cts_table
        self._selection = selection

        self._setup_ui()

        # v1.4.5: se selection presente, popula form ANTES do analyze
        if selection is not None:
            self._apply_selection(selection)

        # Auto-run com defaults (ou com selection já aplicada)
        self._on_analyze()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ---------- v1.4.5 — Banner contextual (selection vs didático) ----------
        self._banner = QLabel()
        self._banner.setWordWrap(True)
        self._banner.setStyleSheet(
            "QLabel { background-color: #E3F2FD; "
            "border-left: 3px solid #1976D2; "
            "padding: 6px 10px; font-size: 11px; }"
        )
        if self._selection is not None:
            self._banner.setText(
                f"🎯 <b>Analisando TC '{self._selection.tag}' do esquemático</b> — "
                f"properties carregadas do canvas. "
                f"Ajuste contexto da falta abaixo se necessário."
            )
        else:
            self._banner.setText(
                "📚 <b>Modo didático</b> — defaults pré-populados (TC C400 @ "
                "2000:5, falta 20 kA, X/R 10).<br>"
                "Para análise real, selecione um TC no canvas (Modo Online) "
                "e use Análise → Saturação de TC."
            )
        layout.addWidget(self._banner)

        # ---------- Title + JSON loader ----------
        header = QHBoxLayout()
        title = QLabel(
            "Análise de Saturação de TC — 3 níveis (ANSI / IEC / Dinâmico)"
        )
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()

        self.btn_load_json = QPushButton("📂 Importar dados de TCs (JSON)")
        self.btn_load_json.setToolTip(
            "Importa lista de TCs de arquivo JSON.\n"
            "Formato compatível com export de SKM PTW Power*Tools, "
            "ETAP e EasyPower."
        )
        self.btn_load_json.clicked.connect(self._on_load_json)
        header.addWidget(self.btn_load_json)
        layout.addLayout(header)

        # ---------- JSON list (escondida por default; aparece após load) ----------
        self.json_list = QListWidget()
        self.json_list.setVisible(False)
        self.json_list.setMaximumHeight(120)
        self.json_list.itemDoubleClicked.connect(self._on_json_select)
        layout.addWidget(self.json_list)

        # ---------- Form (Bus + CT) ----------
        form_layout = QHBoxLayout()
        form_layout.addWidget(self._build_fault_box())
        form_layout.addWidget(self._build_ct_box())
        layout.addLayout(form_layout)

        # ---------- Action row ----------
        actions = QHBoxLayout()
        self.btn_analyze = QPushButton("▶ Analisar Saturação")
        self.btn_analyze.clicked.connect(self._on_analyze)
        actions.addWidget(self.btn_analyze)

        self.btn_redimension = QPushButton(
            "⚙ Re-dimensionar (próxima classe)"
        )
        self.btn_redimension.clicked.connect(self._on_redimension)
        actions.addWidget(self.btn_redimension)

        actions.addStretch()

        self.btn_save_txt = QPushButton("💾 Salvar TXT")
        self.btn_save_txt.clicked.connect(self._on_save_txt)
        actions.addWidget(self.btn_save_txt)

        self.btn_save_xlsx = QPushButton("💾 Salvar XLSX")
        self.btn_save_xlsx.clicked.connect(self._on_save_xlsx)
        actions.addWidget(self.btn_save_xlsx)

        layout.addLayout(actions)

        # ---------- Result tabs (4) ----------
        self.results_tabs = QTabWidget()

        # Tab 1: Sumário
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Consolas", 9))
        self.results_tabs.addTab(self.summary_text, "📋 Sumário")

        # Tab 2: Nível 1 ANSI
        self.plot1_widget = QWidget()
        self.plot1_layout = QVBoxLayout(self.plot1_widget)
        self.results_tabs.addTab(self.plot1_widget, "📊 Nível 1 (ANSI)")

        # Tab 3: Nível 2 IEC
        self.plot2_widget = QWidget()
        self.plot2_layout = QVBoxLayout(self.plot2_widget)
        self.results_tabs.addTab(self.plot2_widget, "🎯 Nível 2 (IEC)")

        # Tab 4: Nível 3 Dinâmico
        self.plot3_widget = QWidget()
        self.plot3_layout = QVBoxLayout(self.plot3_widget)
        self.results_tabs.addTab(self.plot3_widget, "⚡ Nível 3 (Dinâmico)")

        layout.addWidget(self.results_tabs, stretch=1)

        # Close button
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText("Fechar")
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    # -----------------------------------------------------------------
    # Form builders
    # -----------------------------------------------------------------

    def _build_fault_box(self) -> QGroupBox:
        defaults = _build_demo_inputs()
        box = QGroupBox("Contexto da Falta (CTFaultContext)")
        f = QFormLayout(box)

        self.bus_id = QComboBox()
        self.bus_id.setEditable(True)
        self.bus_id.addItem(defaults["bus_id"])
        f.addRow("Bus ID:", self.bus_id)

        self.rated_kV = QDoubleSpinBox()
        self.rated_kV.setRange(0.1, 800.0)
        self.rated_kV.setValue(defaults["rated_voltage_kV"])
        self.rated_kV.setSuffix(" kV")
        f.addRow("Tensão LL:", self.rated_kV)

        self.I_fault = QDoubleSpinBox()
        self.I_fault.setRange(0.1, 200.0)
        self.I_fault.setValue(defaults["I_fault_rms_kA"])
        self.I_fault.setSuffix(" kA")
        f.addRow("I fault (RMS):", self.I_fault)

        self.xr_ratio = QDoubleSpinBox()
        self.xr_ratio.setRange(0.5, 60.0)
        self.xr_ratio.setValue(defaults["X_over_R"])
        f.addRow("X/R:", self.xr_ratio)
        return box

    def _build_ct_box(self) -> QGroupBox:
        defaults = _build_demo_inputs()
        box = QGroupBox("Especificação do TC (CTSpec)")
        f = QFormLayout(box)

        self.tag = QComboBox()
        self.tag.setEditable(True)
        self.tag.addItem(defaults["tag"])
        f.addRow("TAG:", self.tag)

        self.tipo_TC = QComboBox()
        self.tipo_TC.addItems(["ANSI_C", "IEC_PR", "IEC_P"])
        f.addRow("Tipo TC:", self.tipo_TC)

        self.I_pri_nom_tap = QSpinBox()
        self.I_pri_nom_tap.setRange(50, 10000)
        self.I_pri_nom_tap.setValue(defaults["I_pri_nom_tap"])
        self.I_pri_nom_tap.setSuffix(" A")
        f.addRow("I pri nom tap:", self.I_pri_nom_tap)

        self.I_pri_nom_full = QSpinBox()
        self.I_pri_nom_full.setRange(50, 10000)
        self.I_pri_nom_full.setValue(defaults["I_pri_nom_full"])
        self.I_pri_nom_full.setSuffix(" A")
        f.addRow("I pri nom full:", self.I_pri_nom_full)

        self.I_sn = QSpinBox()
        self.I_sn.setRange(1, 5)
        self.I_sn.setValue(defaults["I_sn"])
        self.I_sn.setSuffix(" A")
        f.addRow("I sec nom:", self.I_sn)

        self.CT_Rating_C = QDoubleSpinBox()
        self.CT_Rating_C.setRange(50.0, 3200.0)
        self.CT_Rating_C.setValue(defaults["CT_Rating_C"])
        self.CT_Rating_C.setSuffix(" V")
        f.addRow("Rating C (Vk):", self.CT_Rating_C)

        self.R_s = QDoubleSpinBox()
        self.R_s.setRange(0.0, 50.0)
        self.R_s.setValue(defaults["R_s"])
        self.R_s.setSuffix(" Ω")
        f.addRow("R secundário:", self.R_s)

        self.R_b = QDoubleSpinBox()
        self.R_b.setRange(0.0, 50.0)
        self.R_b.setValue(defaults["R_b"])
        self.R_b.setSuffix(" Ω")
        f.addRow("R burden:", self.R_b)

        self.Kr = QDoubleSpinBox()
        self.Kr.setRange(0.0, 0.95)
        self.Kr.setValue(defaults["Kr"])
        self.Kr.setSingleStep(0.1)
        self.Kr.setDecimals(2)
        f.addRow("Kr (remanência):", self.Kr)
        return box

    # -----------------------------------------------------------------
    # Slots
    # -----------------------------------------------------------------

    def _apply_selection(self, sel) -> None:
        """
        v1.4.5: Popula o form a partir de um :class:`CTSelection`
        construído de um PpComponent (type='CT') selecionado no canvas.

        Bloqueia edição da TAG (read-only) — o usuário não pode
        renomear o TC do canvas pelo dialog (anti-pattern PTW).
        """
        # CTSpec form
        self.tag.setEditText(sel.tag)
        self.tag.setEnabled(False)   # TAG read-only para selection
        self.tipo_TC.setCurrentText(sel.classe)
        self.I_pri_nom_tap.setValue(int(sel.ratio_pri_A))
        self.I_pri_nom_full.setValue(int(sel.ratio_pri_A))
        self.I_sn.setValue(int(sel.ratio_sec_A))
        self.CT_Rating_C.setValue(sel.c_rating_V)
        self.R_s.setValue(sel.rs_ohm)
        self.R_b.setValue(sel.rb_ohm)
        self.Kr.setValue(sel.kr)

        # CTFaultContext form
        self.bus_id.setEditText(sel.bus_id)
        self.rated_kV.setValue(sel.rated_voltage_kV)
        self.I_fault.setValue(sel.I_fault_rms_kA)
        self.xr_ratio.setValue(sel.X_over_R)

    def _on_analyze(self) -> None:
        """Coleta inputs + roda analyze_full + atualiza 4 tabs."""
        try:
            from app.postprocessor.ct_saturation import (
                CTFaultContext, CTSpec, analyze_full,
                typical_magnetization_curve,
            )
            fault = CTFaultContext(
                bus_id=self.bus_id.currentText() or "BUS-?",
                rated_voltage_kV=self.rated_kV.value(),
                I_fault_rms_kA=self.I_fault.value(),
                X_over_R=self.xr_ratio.value(),
            )
            ct = CTSpec(
                tag=self.tag.currentText() or "CT-?",
                tipo_TC=self.tipo_TC.currentText(),
                I_pri_nom_tap=self.I_pri_nom_tap.value(),
                I_pri_nom_full=self.I_pri_nom_full.value(),
                I_sn=self.I_sn.value(),
                CT_Rating_C=self.CT_Rating_C.value(),
                R_s=self.R_s.value(),
                R_b=self.R_b.value(),
                curve=typical_magnetization_curve(self.CT_Rating_C.value()),
                Kr=self.Kr.value(),
            )
            report = analyze_full(ct, fault)
            self._last_report = report
            self._update_summary(report)
            self._update_plot(self.plot1_layout, "level1", report)
            self._update_plot(self.plot2_layout, "level2", report)
            self._update_plot(self.plot3_layout, "level3", report)
        except Exception as e:
            QMessageBox.critical(
                self, "Erro na análise",
                f"Falha ao rodar analyze_full:\n{type(e).__name__}: {e}",
            )

    def _on_redimension(self) -> None:
        """
        Sprint D — workflow refinamento: aumenta CT_Rating_C para
        próxima classe ANSI padrão e re-roda análise.

        Equivalente ao loop ``while true`` de ``main_CT_Analysis.m``.
        Atualiza a barra de status (não usa QMessageBox para não
        bloquear testes headless).
        """
        try:
            from app.postprocessor.ct_saturation_io import next_ansi_class
            cur_C = self.CT_Rating_C.value()
            new_C = next_ansi_class(cur_C)
            if new_C <= cur_C:
                self.setWindowTitle(
                    f"🔍 Já no topo da escala padrão (C{cur_C:.0f}) — "
                    f"Olivas Power System Studio"
                )
                return
            self.CT_Rating_C.setValue(new_C)
            self._on_analyze()
            self.setWindowTitle(
                f"🔍 Re-dimensionado C{cur_C:.0f} → C{new_C:.0f} — "
                f"Olivas Power System Studio"
            )
        except Exception as e:
            QMessageBox.warning(
                self, "Erro",
                f"Falha ao re-dimensionar: {type(e).__name__}: {e}",
            )

    def _on_load_json(self) -> None:
        """Sprint E — carrega lista de TCs de arquivo JSON (compatível com
        formato export do SKM PTW, ETAP, EasyPower).
        Olivas NÃO integra ativamente com PTW — apenas lê o JSON."""
        # Sugere o arquivo padrão MATLAB CT_STUDY se existir
        default_path = (
            Path("D:/000 - UFMG - DOUTORADO/MVP/LIB/LIB/CT_STUDY")
            / "ct_system_data.json"
        )
        start = (
            str(default_path) if default_path.exists()
            else str(Path.cwd())
        )
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecione ct_system_data.json",
            start, "JSON (*.json);;Todos (*.*)",
        )
        if not path:
            return
        try:
            from app.postprocessor.ct_saturation_io import list_cts_table
            self._json_table = list_cts_table(path)
            self.json_list.clear()
            for row in self._json_table:
                txt = (
                    f"[{row['index']}] {row['CT_TAG']}  ·  "
                    f"Bus={row['Bus_in']}  ·  "
                    f"Rel={row['CT_Ratio']}  ·  "
                    f"Icc={row['I_fault_rms_kA']:.1f} kA  ·  "
                    f"X/R={row['X_over_R']:.1f}"
                )
                item = QListWidgetItem(txt)
                item.setData(Qt.UserRole, row)
                self.json_list.addItem(item)
            self.json_list.setVisible(True)
            QMessageBox.information(
                self, "JSON carregado",
                f"{len(self._json_table)} TCs carregados.\n"
                f"Duplo-clique em um item para popular o formulário."
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Erro ao carregar JSON",
                f"{type(e).__name__}: {e}",
            )

    def _on_json_select(self, item: QListWidgetItem) -> None:
        """Popular form com dados do TC escolhido na lista."""
        row = item.data(Qt.UserRole)
        if row is None:
            return
        # Popula form
        self.bus_id.setEditText(str(row.get("Bus_in", "")))
        self.tag.setEditText(str(row.get("CT_TAG", "")))
        self.rated_kV.setValue(float(row.get("V_LL_kV") or 13.8))
        self.I_fault.setValue(float(row.get("I_fault_rms_kA") or 1.0))
        self.xr_ratio.setValue(
            max(float(row.get("X_over_R") or 1.0), 0.5)
        )
        # Tenta extrair I_pri_nom de "600 / 5"
        ratio_str = str(row.get("CT_Ratio", ""))
        try:
            if "/" in ratio_str:
                parts = ratio_str.split("/")
                ipri = int(float(parts[0].strip()))
                isec = int(float(parts[1].strip()))
                self.I_pri_nom_tap.setValue(ipri)
                self.I_pri_nom_full.setValue(ipri)
                self.I_sn.setValue(isec)
        except (ValueError, IndexError):
            pass
        # Re-roda
        self._on_analyze()

    def _on_save_txt(self) -> None:
        """Sprint F — exporta TXT do report atual."""
        if self._last_report is None:
            QMessageBox.warning(
                self, "Sem análise",
                "Rode a análise primeiro antes de exportar.",
            )
            return
        from app.postprocessor.ct_saturation_io import (
            write_report_txt, _safe_filename,
        )
        tag_safe = _safe_filename(self._last_report.ct.tag)
        default_name = f"Relatorio_{tag_safe}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar relatório TXT",
            default_name, "Texto (*.txt)",
        )
        if not path:
            return
        try:
            write_report_txt(self._last_report, Path(path))
            QMessageBox.information(
                self, "TXT salvo",
                f"Relatório salvo em:\n{path}",
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Erro",
                f"Falha ao salvar TXT: {type(e).__name__}: {e}",
            )

    def _on_save_xlsx(self) -> None:
        """Sprint F — exporta XLSX do report atual."""
        if self._last_report is None:
            QMessageBox.warning(
                self, "Sem análise",
                "Rode a análise primeiro antes de exportar.",
            )
            return
        from app.postprocessor.ct_saturation_io import (
            write_report_xlsx, _safe_filename,
        )
        tag_safe = _safe_filename(self._last_report.ct.tag)
        default_name = f"Datasheet_{tag_safe}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar datasheet XLSX",
            default_name, "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            write_report_xlsx(self._last_report, Path(path))
            QMessageBox.information(
                self, "XLSX salvo",
                f"Datasheet salvo em:\n{path}",
            )
        except ImportError:
            QMessageBox.warning(
                self, "openpyxl ausente",
                "Instale openpyxl para exportar XLSX:\n"
                "  pip install openpyxl",
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Erro",
                f"Falha ao salvar XLSX: {type(e).__name__}: {e}",
            )

    # -----------------------------------------------------------------
    # Tab updaters
    # -----------------------------------------------------------------

    def _update_summary(self, report) -> None:
        try:
            text = report.summary()
        except Exception:
            text = repr(report)
        self.summary_text.setPlainText(text)

    def _update_plot(self, layout, level: str, report) -> None:
        """
        Limpa layout e adiciona o plot apropriado para o nível.

        level ∈ {'level1', 'level2', 'level3'}.
        """
        # Limpa layout anterior
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        try:
            import matplotlib
            # Set backend before importing FigureCanvas (idempotent)
            try:
                matplotlib.use("QtAgg", force=False)
            except Exception:
                pass
            from matplotlib.backends.backend_qtagg import (
                FigureCanvasQTAgg as FigureCanvas,
            )
            from app.gui.ct_saturation_plots import (
                plot_level1_ansi, plot_level2_iec, plot_level3_dynamic,
            )
            plot_funcs = {
                "level1": plot_level1_ansi,
                "level2": plot_level2_iec,
                "level3": plot_level3_dynamic,
            }
            fig = plot_funcs[level](report)
            canvas = FigureCanvas(fig)
            # Toolbar opcional (em headless tests pode falhar);
            # tenta mas não derruba se falhar.
            try:
                from matplotlib.backends.backend_qtagg import (
                    NavigationToolbar2QT as NavigationToolbar,
                )
                toolbar = NavigationToolbar(canvas, self.results_tabs)
                layout.addWidget(toolbar)
            except Exception:
                pass
            layout.addWidget(canvas)
        except Exception as e:
            err_lbl = QLabel(
                f"Erro ao plotar {level}: {type(e).__name__}: {e}"
            )
            err_lbl.setWordWrap(True)
            layout.addWidget(err_lbl)
