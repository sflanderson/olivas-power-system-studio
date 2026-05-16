from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.gui.theme import get_palette, get_qcolor, get_stylesheet
from app.core.diff_util import compute_context_diff, has_changes
from app.core.parser import parse_file
from app.core.project_model import (
    AtpProject,
    BranchComponent,
    ModelDefinition,
    Section,
    SourceComponent,
    SwitchComponent,
    UseInstance,
)
from app.core.serializer import serialize_project
from app.gui.chat_widget import ChatWidget
from app.gui.compare_widget import CompareWidget
from app.gui.schematic import SchematicEditor
from app.gui.schematic_pp import PpEditor
from app.gui.topology_widget import TopologyWidget
from app.gui.waveform_widget import WaveformWidget
from app.preprocessor.bridge_from_atp import from_atp
from app.preprocessor.qucs_sch_parser import parse_sch_file
from app.preprocessor.qucs_sch_serializer import serialize_sch_file
from app.analysis.csv_export import export_metrics_csv, export_waveforms_csv
from app.analysis.report_export import export_html_report, export_pdf_report
from app.analysis.transient_metrics import (
    compute_transient_metrics,
    format_transient_report,
)
from app.simulation.results_reader import AtpResults, find_result_files, read_lis, read_pl4
from app.simulation.runner import AtpRunner
from app.validation.validator_models import Severity, validate_project
from app.validation.validator_physics import validate_physics
from app.validation.validator_vcb import validate_vcb

MONO_FONT = "Consolas"
MONO_SIZE = 10


# ======================================================================
# Preview / Diff dialog
# ======================================================================


class DiffPreviewDialog(QDialog):
    def __init__(self, diff_lines: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preview — Alterações antes de salvar")
        self.resize(820, 520)

        layout = QVBoxLayout(self)

        info = QLabel(f"{len([l for l in diff_lines if l.startswith('+') and not l.startswith('+++')])} linha(s) adicionada(s), "
                      f"{len([l for l in diff_lines if l.startswith('-') and not l.startswith('---')])} linha(s) removida(s)")
        layout.addWidget(info)

        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setLineWrapMode(QPlainTextEdit.NoWrap)
        font = QFont(MONO_FONT, MONO_SIZE)
        text.setFont(font)
        text.setPlainText("\n".join(diff_lines))
        layout.addWidget(text)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Save).setText("Salvar")
        buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


# ======================================================================
# Main Window
# ======================================================================


RECENT_FILES_KEY = "recent_files"
RECENT_FILES_MAX = 10


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Olivas Power System Studio")
        self.resize(1280, 800)

        self._cases: dict[str, AtpProject] = {}  # path -> project
        self._active_case: Optional[str] = None
        self._settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
        saved_timeout = int(self._settings.value("atp_timeout", 120))
        self.runner = AtpRunner(
            executable_path=self._settings.value("atp_executable_path", None),
            timeout=saved_timeout,
        )
        self._current_use: Optional[UseInstance] = None
        self._current_model: Optional[ModelDefinition] = None
        # v0.28.2-PRO Onda 2.5: tracking de modificações
        self._modified_paths: set[str] = set()
        # v0.28.3-PRO Onda 3.3: QUndoStack global para edits
        # nas data tables. Ctrl+Z / Ctrl+Y wired no menu.
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(200)

        self._build_menu()
        self._build_toolbar()   # v0.28.2-PRO Onda 2.2
        self._build_ui()
        self._build_status_bar()
        # v0.28.3-PRO Onda 3.2: console dockable panel
        self._build_console_panel()
        self.apply_theme()

        # v1.4.1: removido status "ATP configurado" — não relevante
        # para reposicionamento Power System Studio. Status bar
        # default ("Pronto — abra um esquemático .sch...") fica.

        # v1.5.0: auto-load plugins habilitados no startup. Plugins
        # builtin sem state explícito ficam disabled por default
        # (opt-in via Marketplace). Builtin de exemplo NÃO é
        # carregado até o usuário habilitar — princípio
        # "privacy/segurança first" do design doc v1.5.0.
        try:
            from app.plugins import auto_load_enabled_plugins
            loaded = auto_load_enabled_plugins()
            if loaded:
                if hasattr(self, "_console_panel"):
                    self._console_panel.append_info(
                        f"v1.5.0: {len(loaded)} plugin(s) carregado(s) "
                        f"automaticamente: {', '.join(loaded)}"
                    )
        except Exception as exc:
            log.warning(
                "v1.5.0 auto-load falhou (não-fatal): %s", exc,
            )

        # v2.1.1: Restore locale persistido (default PT). Anti-crash
        # defensivo: falha em ler settings → mantém PT.
        try:
            saved_locale = self._settings.value("locale", "pt")
            if saved_locale and saved_locale != "pt":
                from app.i18n import set_locale
                set_locale(saved_locale)
                if hasattr(self, "_console_panel"):
                    self._console_panel.append_info(
                        f"v2.1.1: locale restaurado de QSettings: "
                        f"{saved_locale}"
                    )
        except Exception as exc:
            log.warning(
                "v2.1.1 locale restore falhou (não-fatal): %s", exc,
            )

    @property
    def project(self) -> Optional[AtpProject]:
        if self._active_case and self._active_case in self._cases:
            return self._cases[self._active_case]
        return None

    @project.setter
    def project(self, value: Optional[AtpProject]) -> None:
        if value is None:
            if self._active_case:
                self._cases.pop(self._active_case, None)
                self._active_case = None
        else:
            key = value.file_path or "untitled"
            self._cases[key] = value
            self._active_case = key

    # ------------------------------------------------------------------
    # v0.28.2-PRO Onda 2.4: Recent files (QSettings persistence)
    # ------------------------------------------------------------------

    def _load_recent_files(self) -> list[str]:
        raw = self._settings.value(RECENT_FILES_KEY, [])
        if isinstance(raw, str):
            return [raw] if raw else []
        if isinstance(raw, list):
            return [str(p) for p in raw if p]
        return []

    def _save_recent_files(self, paths: list[str]) -> None:
        self._settings.setValue(
            RECENT_FILES_KEY, paths[:RECENT_FILES_MAX],
        )

    def _add_to_recent(self, path: str) -> None:
        """Adiciona path ao topo da lista de recentes."""
        if not path:
            return
        path = str(Path(path).resolve())
        recent = self._load_recent_files()
        # Remove se já existe (move para topo)
        recent = [p for p in recent if p != path]
        recent.insert(0, path)
        self._save_recent_files(recent[:RECENT_FILES_MAX])
        # Re-popula menu se já existe
        self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        if not hasattr(self, "_recent_menu"):
            return
        self._recent_menu.clear()
        recent = self._load_recent_files()
        if not recent:
            empty_action = self._recent_menu.addAction(
                "(nenhum arquivo recente)",
            )
            empty_action.setEnabled(False)
            return
        for path in recent:
            label = f"{Path(path).name}  —  {path}"
            action = self._recent_menu.addAction(label)
            action.triggered.connect(
                lambda checked=False, p=path: self._open_recent(p),
            )
        self._recent_menu.addSeparator()
        clear_action = self._recent_menu.addAction("Limpar lista")
        clear_action.triggered.connect(self._clear_recent_files)

    def _open_recent(self, path: str) -> None:
        """Abre arquivo recente. Suporta .atp e .sch."""
        p = Path(path)
        if not p.exists():
            QMessageBox.warning(
                self, "Arquivo não encontrado",
                f"O arquivo {path} não existe mais. "
                "Removendo da lista de recentes.",
            )
            recent = [
                rp for rp in self._load_recent_files() if rp != path
            ]
            self._save_recent_files(recent)
            self._refresh_recent_menu()
            return
        if p.suffix.lower() == ".sch":
            self._on_pp_open_sch_path(path)
        else:
            self._open_atp_path(path)

    def _open_atp_path(self, path: str) -> None:
        """Abre um .atp dado o path (extraído de _on_open)."""
        try:
            project = parse_file(path)
            self._cases[path] = project
            self._active_case = path
            self._add_to_recent(path)
            self._refresh_case_combo()
            self._refresh_views()
            self._update_window_title()
        except Exception as e:
            QMessageBox.critical(
                self, "Erro ao abrir", f"Falha ao parsear:\n{e}",
            )

    def _on_pp_open_sch_path(self, path: str) -> None:
        """Abre um .sch dado o path."""
        try:
            project = parse_sch_file(path)
            self.schematic_pp.scene.load_project(project)
            self._add_to_recent(path)
        except Exception as e:
            QMessageBox.critical(
                self, "Erro .sch", f"Falha ao parsear .sch:\n{e}",
            )

    def _clear_recent_files(self) -> None:
        self._save_recent_files([])
        self._refresh_recent_menu()

    # ------------------------------------------------------------------
    # v0.28.2-PRO Onda 2.5: Modified-state indicator + Ctrl+S
    # ------------------------------------------------------------------

    def _mark_modified(self, path: str) -> None:
        """Marca um caso como modificado e atualiza title/combo."""
        self._modified_paths.add(path)
        self._update_window_title()
        self._refresh_case_combo_marks()

    def _mark_clean(self, path: str) -> None:
        self._modified_paths.discard(path)
        self._update_window_title()
        self._refresh_case_combo_marks()

    def _is_modified(self, path: Optional[str]) -> bool:
        return path is not None and path in self._modified_paths

    def _update_window_title(self) -> None:
        """
        Atualiza o título da janela com indicador `*` se há
        modificações no caso ativo.

        v0.91: também mostra `*` se o ``PpEditor`` (esquemático
        visual) está dirty (mudanças não salvas no .sch). O
        título prioriza o ATP case ativo se houver, senão
        mostra o .sch carregado.
        """
        title = "Olivas Power System Studio"
        # ATP case
        if self._active_case:
            name = Path(self._active_case).name
            mark = "*" if self._is_modified(self._active_case) else ""
            title = f"{name}{mark} — {title}"
        # PpEditor (.sch) — adiciona segundo segmento se houver
        try:
            sch_path = self.schematic_pp.current_sch_path
            sch_dirty = self.schematic_pp.is_dirty()
        except Exception:
            sch_path = None
            sch_dirty = False
        if sch_path:
            sch_name = Path(sch_path).name
            sch_mark = "*" if sch_dirty else ""
            title = f"{sch_name}{sch_mark} — {title}"
        elif sch_dirty:
            # Untitled mas com mudanças
            title = f"(untitled)* — {title}"
        self.setWindowTitle(title)

    def _refresh_case_combo_marks(self) -> None:
        """Atualiza marks `*` em items do combo."""
        if not hasattr(self, "case_combo"):
            return
        for i in range(self.case_combo.count()):
            path = self.case_combo.itemData(i)
            if not path:
                continue
            name = Path(path).name
            mark = "*" if self._is_modified(path) else ""
            self.case_combo.setItemText(i, f"{name}{mark}")

    def _on_save_current(self) -> None:
        """
        v0.28.2-PRO Onda 2.5: Ctrl+S = salvar no path existente.
        Se untitled, cai para Save As.
        """
        if self._active_case is None:
            QMessageBox.information(
                self, "Salvar", "Nenhum caso aberto.",
            )
            return
        path = self._active_case
        try:
            self._commit_table_edits()
            project = self._cases[path]
            content = serialize_project(project)
            Path(path).write_text(content, encoding="utf-8")
            self._mark_clean(path)
            self.status.showMessage(f"Salvo: {path}", 5000)
        except Exception as e:
            QMessageBox.critical(
                self, "Erro ao salvar", f"Falha:\n{e}",
            )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = menu_bar.addMenu("Arquivo")
        file_menu.addAction("Abrir...", self._on_open, "Ctrl+O")
        # v0.28.2-PRO Onda 2.5: Ctrl+S = save in-place; Save As = Ctrl+Shift+S
        file_menu.addAction("Salvar", self._on_save_current, "Ctrl+S")
        file_menu.addAction("Salvar como...", self._on_save_as, "Ctrl+Shift+S")
        # v0.28.2-PRO Onda 2.4: Recent files
        self._recent_menu = file_menu.addMenu("Recentes")
        self._refresh_recent_menu()
        file_menu.addSeparator()

        # v1.0.2 — Limpeza: itens de IO movidos para nível
        # superior (era submenu "Esquemático visual" que poluía
        # com import/export ATP). Manter ATP IO em
        # Ferramentas → ATP/EMTP (submenu secundário).
        file_menu.addAction(
            "Abrir esquemático (.sch)...", self._on_pp_open_sch,
        )
        file_menu.addAction(
            "Salvar esquemático (.sch)...", self._on_pp_save_sch,
        )

        file_menu.addSeparator()
        file_menu.addAction("Fechar caso", self._on_close_case, "Ctrl+W")
        file_menu.addSeparator()
        file_menu.addAction("Sair", self.close, "Ctrl+Q")

        # v0.28.3-PRO Onda 3.3: Edit menu com Undo/Redo
        edit_menu = menu_bar.addMenu("Editar")
        undo_action = self._undo_stack.createUndoAction(self, "Desfazer")
        undo_action.setShortcut(QKeySequence.Undo)  # Ctrl+Z
        edit_menu.addAction(undo_action)
        redo_action = self._undo_stack.createRedoAction(self, "Refazer")
        redo_action.setShortcut(QKeySequence.Redo)  # Ctrl+Y / Ctrl+Shift+Z
        edit_menu.addAction(redo_action)

        # v0.92 — REPOSITIONING: Análise é o menu principal. ATP foi
        # movido para submenu "Ferramentas → ATP/EMTP", refletindo
        # que o software é um especialista em análise elétrica
        # (curto-circuito, fluxo de potência, coordenação, arc-flash,
        # balanço de carga) — ATP é tooling secundário.
        analysis_menu = menu_bar.addMenu("Análise")
        act_full = analysis_menu.addAction(
            "📊 Estudo completo do barramento...",
            self._on_analyze_bus_pipeline,
        )
        act_full.setShortcut("F8")
        act_full.setStatusTip(
            "Pipeline consolidado: SC + Arc-flash + Coordenação "
            "(IEC 60909 / NBR 17227 / IEEE 242) — laudo auditável (F8)"
        )
        analysis_menu.addSeparator()
        # v0.94.0 — Estudos modulares estilo PTW (cada um standalone
        # com cache de pré-requisitos). Atalhos F5/F6/F7/F8.
        act_sc = analysis_menu.addAction(
            "⚡ Curto-circuito (IEC 60909-0:2016)...",
            self._on_run_analysis_dialog,
        )
        act_sc.setShortcut("F5")
        act_sc.setStatusTip(
            "Ik'', ip, Ib, Ik (IEC 60909-0 §4) — standalone (F5)"
        )
        # v3.1.0 Track B-1 — ANSI SC Dialog (backfill GUI sob 7ª garantia)
        act_ansi_sc = analysis_menu.addAction(
            "🇺🇸 ANSI Short Circuit (C37.5 / C37.010)...",
            self._on_show_ansi_sc_dialog,
        )
        act_ansi_sc.setShortcut("Ctrl+Shift+A")
        act_ansi_sc.setStatusTip(
            "ANSI/IEEE C37.5 / C37.010 — NACD, MF tables, asym withstand "
            "(SKM PTW A_Fault §1.2-§1.4) — Ctrl+Shift+A"
        )
        # v3.1.0 Track B-2 — Pre-Fault Voltage Settings
        act_prefault = analysis_menu.addAction(
            "⚙️ Pre-Fault Voltage Settings...",
            self._on_show_pre_fault_voltage_dialog,
        )
        act_prefault.setStatusTip(
            "Configurar Pre-Fault Voltage (4 modes) + tolerâncias "
            "Util/Cable/TX (PTW Tutorial §Part 5 p. 131-135)"
        )
        # v3.1.0 Track B-4 — Fault Decay temporal dialog
        act_decay = analysis_menu.addAction(
            "📉 Fault Current Decay (temporal)...",
            self._on_show_fault_decay_dialog,
        )
        act_decay.setStatusTip(
            "Decay exponencial Gen/Sync/Induction over time "
            "(PTW Tutorial §Part 5 p. 136-138)"
        )
        # v3.3.0 Sprint 1 — Unbalanced PF Dialog (FECHA violação 7ª garantia)
        act_unb_pf = analysis_menu.addAction(
            "⚖ Análise unbalanced (3-φ + sequências 0/1/2)...",
            self._on_show_unbalanced_pf_dialog,
        )
        act_unb_pf.setStatusTip(
            "Power Flow unbalanced (Fortescue) + open-phase scenarios "
            "(PTW Tutorial §Part 9 p.238-258 + IEEE 1159-2019)"
        )
        # v3.1.0 Track B-5 — Run > Balanced System Studies (orquestrado)
        act_balanced = analysis_menu.addAction(
            "🏃 Run > Balanced System Studies (DAPPER + LF + Comp SC)...",
            self._on_show_balanced_system_studies,
        )
        act_balanced.setStatusTip(
            "Orquestrador estilo PTW Tutorial §Part 2 p. 63-64 — "
            "executa DAPPER + Load Flow + ANSI Comp SC em sequência"
        )
        act_coord = analysis_menu.addAction(
            "🛡️ Coordenação e seletividade (IEEE 242)...",
            self._on_run_analysis_dialog,
        )
        act_coord.setShortcut("F6")
        act_coord.setStatusTip(
            "Sugestões 50/51 — auto-roda SC se necessário (F6)"
        )
        # v1.0.2 — Coordenograma TCC interativo (estilo PTW CAPTOR)
        act_tcc = analysis_menu.addAction(
            "📊 Coordenograma TCC (curvas tempo-corrente)...",
            self._on_show_tcc_coordinogram,
        )
        act_tcc.setShortcut("Ctrl+T")
        act_tcc.setStatusTip(
            "Coordenograma TCC interativo — arraste curvas com "
            "mouse para ajustar TMS (estilo SKM PTW CAPTOR). "
            "Atalho Ctrl+T."
        )
        # v3.6.0 — Reliability indices (Tier 1 PTW Tutorial §Part 10)
        act_reliability = analysis_menu.addAction(
            "📊 Reliability Indices (IEEE 1366-2012)...",
            self._on_show_reliability,
        )
        act_reliability.setStatusTip(
            "Calcula SAIFI/SAIDI/CAIDI/ASAI a partir de eventos de "
            "interrupção. Paridade PTW Tutorial §Part 10."
        )
        # v1.3.1 G.1 — Equipment Evaluation Dashboard (paridade
        # SKM PTW Equipment Evaluation, 9 critérios automatizados)
        act_eq_eval = analysis_menu.addAction(
            "📋 Avaliar equipamentos (9 critérios PTW)...",
            self._on_show_equipment_eval,
        )
        act_eq_eval.setShortcut("Ctrl+E")
        act_eq_eval.setStatusTip(
            "Equipment Evaluation Dashboard — IEEE 242 §15 + NBR 5410. "
            "Voltage Rating, Interrupt Duty, Asym, Load Flow, V-drop, "
            "etc. Paridade PTW. Atalho Ctrl+E."
        )
        # v1.3.1 G.2 — Coordination Rules check
        act_coord_rules = analysis_menu.addAction(
            "🛡️ Verificar regras de coordenação (NEC + IEEE 242)...",
            self._on_show_coord_rules_check,
        )
        act_coord_rules.setStatusTip(
            "Coordination Rule Engine — aplica regras NEC 110.10 + "
            "IEEE 242 + NBR a TCCDevices do projeto. Pluginnable."
        )
        # v1.4.0 — Custom Label Designer (último P0 do roadmap PTW)
        act_label_designer = analysis_menu.addAction(
            "🏷️ Designer de Label Arc-Flash (NFPA 70E / NBR 17227)...",
            self._on_show_label_designer,
        )
        act_label_designer.setShortcut("Ctrl+L")
        act_label_designer.setStatusTip(
            "Custom Label Designer arc-flash — 30 campos editáveis, "
            "3 estilos (NFPA 70E 2024 / NESC 2023 / NBR 17227). "
            "Paridade SKM PTW Custom Label Designer. Atalho Ctrl+L."
        )
        act_af = analysis_menu.addAction(
            "🔥 Energia incidente / Arc-flash (NBR 17227 / IEEE 1584)...",
            self._on_run_analysis_dialog,
        )
        act_af.setShortcut("F7")
        act_af.setStatusTip(
            "E (cal/cm²) + DLA + PPE — auto-roda SC + Coord (F7)"
        )
        analysis_menu.addSeparator()
        act_pf = analysis_menu.addAction(
            "🔌 Fluxo de potência (IEEE 399)...",
            self._on_analyze_power_flow,
        )
        act_pf.setStatusTip(
            "Newton-Raphson / Gauss-Seidel — Stevenson §9 / IEEE 399"
        )
        # v0.92: balanço de carga (motor starting + load flow combinado)
        act_lb = analysis_menu.addAction(
            "📈 Balanço de carga / partida de motor (IEEE 141)...",
            self._on_analyze_motor_starting,
        )
        act_lb.setStatusTip(
            "Voltage dip + recovery em partida de motor (IEEE 141 Red Book)"
        )
        # v0.93.0: análise de saturação de TC (3 níveis)
        act_ctsat = analysis_menu.addAction(
            "🔍 Saturação de TC (IEEE C57.13 / IEC 61869-2 / CIGRÉ)...",
            self._on_analyze_ct_saturation,
        )
        act_ctsat.setStatusTip(
            "Análise em 3 níveis: ANSI estático, IEC joelho, "
            "Dinâmico (RK4 com DC offset + remanência)"
        )

        # v1.5.1: DAPPER Demand Load Study (22 categorias NEC + sectors)
        act_demand = analysis_menu.addAction(
            "⚡ Demand Load Study (DAPPER, 22 categorias NEC)...",
            self._on_analyze_demand_load,
        )
        act_demand.setStatusTip(
            "Connected → Demand → Design (NEC 220 + sectors BR). "
            "Paridade PTW DAPPER + vantagem competitiva."
        )

        # v1.6.0: Arc-Flash Multi-Standard Comparison
        # (IEEE 1584 + NBR + EPRI + Doughty-Neal + NESC + CSA + DC)
        act_afcomp = analysis_menu.addAction(
            "⚖ Comparar Standards de Arc-Flash (7 normas)...",
            self._on_compare_arc_flash_standards,
        )
        act_afcomp.setStatusTip(
            "Roda 7 standards simultaneamente: IEEE 1584-2018, "
            "NBR 17227-2025, EPRI 2011, Doughty-Neal-Floyd 2000, "
            "NESC 2023 §410, CSA Z462, NFPA 70E §D.5 DC. "
            "Vantagem competitiva sobre PTW/EasyPower/ETAP."
        )
        analysis_menu.addSeparator()

        # v1.0.1 — Estudos novos do roadmap v0.95→v1.0
        # exposição na GUI (antes só accessíveis via API Python)
        act_cable = analysis_menu.addAction(
            "📐 Dimensionamento de cabo (NBR 5410)...",
            self._on_analyze_cable_sizing,
        )
        act_cable.setStatusTip(
            "Auto-dimensionamento Iz·FC ≥ Ib + V-drop ≤ 4% + "
            "estresse térmico SC (NBR 5410 §6)"
        )
        act_vdrop = analysis_menu.addAction(
            "📉 Queda de tensão por bus (NBR 5410 §6.2.7)...",
            self._on_analyze_voltage_drop,
        )
        act_vdrop.setStatusTip(
            "ΔV cumulativa por barramento. Limites: 4% regime, "
            "7% partida motor (NBR 5410)"
        )
        act_harm = analysis_menu.addAction(
            "〽️ Harmônicos / V-THD (IEEE 519-2014)...",
            self._on_analyze_harmonics,
        )
        act_harm.setStatusTip(
            "VFD/Rectifier/Arc Furnace/UPS spectra. Limites "
            "V-THD 5% LV/MV, 2.5% HV"
        )
        act_reaccel = analysis_menu.addAction(
            "🔄 Re-aceleração de motor (IEEE 399 §10.5)...",
            self._on_analyze_motor_reaccel,
        )
        act_reaccel.setStatusTip(
            "V-dip + tempo de recuperação após distúrbio. "
            "Cenários: dip / black-start / bus-transfer"
        )
        act_grid = analysis_menu.addAction(
            "🌐 Malha de aterramento (IEEE 80)...",
            self._on_analyze_ground_grid,
        )
        act_grid.setStatusTip(
            "R_grid + touch/step voltage + GPR (Schwarz/Sverak)"
        )
        analysis_menu.addSeparator()
        act_ai = analysis_menu.addAction(
            "🤖 Gerar laudo com IA (Claude AI)...",
            self._on_generate_ai_laudo,
        )
        act_ai.setStatusTip(
            "Geração automática de narrativa técnica em PT-BR "
            "para o laudo (offline OU via Claude API)"
        )
        analysis_menu.addSeparator()
        act_rep = analysis_menu.addAction(
            "📄 Relatório completo (HTML / PDF)...",
            self._on_export_pipeline_report,
        )
        act_rep.setStatusTip(
            "Gera laudo auditável (SHA256 + responsável + citações + "
            "limitações declaradas) — ISO 9001 / NR-10"
        )

        # v1.4.2: menu "Validação" REMOVIDO. Era orfão após v1.4.1
        # (tab Validação removida). Funcionalidade equivalente segue
        # disponível via:
        # - menu Análise > Verificar regras de coordenação (NEC + IEEE)
        # - menu Análise > Avaliar equipamentos (Ctrl+E)
        # Os 2 dialogs cobrem 95% dos casos de "validação" do projeto.

        # v1.0.2: Ferramentas — integrações + utilitários.
        # Toda a integração ATP/EMTP foi DESVINCULADA do app
        # principal (v0.92.1); módulos ``app.simulation`` e
        # bridges permanecem disponíveis APENAS via API Python
        # como projeto secundário, sem entry-point na UI.
        tools_menu = menu_bar.addMenu("Ferramentas")
        # v1.4.1: Ctrl+B atalho para acesso rápido à biblioteca
        # de equipamentos (issue #8 do user audit v1.4.0).
        act_library = tools_menu.addAction(
            "📚 Biblioteca de equipamentos (vendor)...",
            self._on_show_equipment_library,
        )
        act_library.setShortcut("Ctrl+B")
        act_library.setStatusTip(
            "Browse vendor catalog (SEL, ABB, Siemens, WEG, GE) — "
            "relés, motores, transformadores, disjuntores. Ctrl+B."
        )
        # v1.5.0: Plugin Marketplace (substitui dialog read-only
        # "Plugins instalados" da v1.0.2). Mantém o handler
        # legacy via _on_show_plugins_legacy para Ctrl+Shift+P.
        act_marketplace = tools_menu.addAction(
            "🧩 Plugin Marketplace...",
            self._on_show_plugin_marketplace,
        )
        act_marketplace.setStatusTip(
            "Gerenciar plugins (Instalar / Habilitar / Desinstalar)"
        )
        tools_menu.addSeparator()
        # v3.5.0 — Scenario Manager (PTW Tutorial §Part 11 p.319-347)
        act_scenarios = tools_menu.addAction(
            "🌳 Scenario Manager (branches paralelos)...",
            self._on_show_scenario_manager,
        )
        act_scenarios.setStatusTip(
            "Gerenciar scenarios (Clone / Activate / Promote to Base) — "
            "PTW Tutorial §Part 11 p.319-347"
        )
        # v3.1.0 Track B-3 — ANSI Utilities (Mis-coord / Conversion / TX Tap)
        act_ansi_util = tools_menu.addAction(
            "🛠 ANSI Utilities (Mis-coord / Conversion / TX Tap)...",
            self._on_show_ansi_utilities,
        )
        act_ansi_util.setStatusTip(
            "Mis-coordination + C37.5↔C37.010 conversion + Transformer Tap "
            "(SKM PTW A_Fault §1.3.7, §1.4.2 + Tutorial §Part 5 p. 144)"
        )
        tools_menu.addSeparator()
        # v2.1.1: Locale picker (idioma da UI)
        act_locale = tools_menu.addAction(
            "🌐 Idioma (PT/EN/ES)...",
            self._on_locale_picker,
        )
        act_locale.setStatusTip(
            "Trocar idioma da interface (Português, English, Español)"
        )
        tools_menu.addAction(
            "Configurar API Key Claude...",
            self._on_configure_api_key,
        )

        # v0.82: Menu Ajuda — guia "Como executar?" via F1
        help_menu = menu_bar.addMenu("Ajuda")
        howto_action = help_menu.addAction(
            "Como executar um estudo? (F1)",
            self._on_show_howto,
        )
        howto_action.setShortcut("F1")
        # v0.91: shortcuts dialog (?  ou Shift+/)
        shortcuts_action = help_menu.addAction(
            "Atalhos do teclado (?)",
            self._on_show_shortcuts,
        )
        shortcuts_action.setShortcut("?")
        help_menu.addSeparator()
        # v4.1.0 commercial Sprint 2: ativação de licença
        license_action = help_menu.addAction(
            "Ativar Licença...",
            self._on_configure_license,
        )
        license_action.setShortcut("Ctrl+L")
        help_menu.addSeparator()
        help_menu.addAction(
            "Sobre o Olivas Power System Studio...",
            self._on_show_about,
        )

        # v0.33.0: Menu Exemplos — exemplos executáveis das normas
        examples_menu = menu_bar.addMenu("Exemplos")
        from app.examples.registry import EXAMPLES
        for ex in EXAMPLES:
            action = examples_menu.addAction(ex.label)
            action.setStatusTip(f"{ex.description} [{ex.reference}]")
            # Captura ex_id para o lambda
            action.triggered.connect(
                lambda checked=False, ex_id=ex.id:
                    self._on_run_example(ex_id),
            )

        view_menu = menu_bar.addMenu("Visualizar")
        view_menu.addAction("Atualizar diff", self._on_update_diff, "Ctrl+D")
        view_menu.addSeparator()
        # v0.93.2 — Toggles do PpEditor migrados da toolbar para o
        # menu Visualizar (UM SÓ menu no topo da tela). Cada toggle
        # delega para o método correspondente do PpEditor.
        self._action_toggle_palette = QAction(
            "📋 Paleta de componentes", self,
        )
        self._action_toggle_palette.setCheckable(True)
        self._action_toggle_palette.setChecked(True)
        self._action_toggle_palette.setShortcut("F9")
        self._action_toggle_palette.setStatusTip(
            "Mostra/oculta a paleta lateral (F9)"
        )
        self._action_toggle_palette.toggled.connect(
            lambda checked: self.schematic_pp.toggle_palette_panel(checked),
        )
        view_menu.addAction(self._action_toggle_palette)

        self._action_toggle_properties = QAction(
            "⚙ Painel de propriedades", self,
        )
        self._action_toggle_properties.setCheckable(True)
        self._action_toggle_properties.setChecked(True)
        self._action_toggle_properties.setShortcut("F10")
        self._action_toggle_properties.setStatusTip(
            "Mostra/oculta o painel de propriedades (F10)"
        )
        self._action_toggle_properties.toggled.connect(
            lambda checked: self.schematic_pp.toggle_properties_panel(checked),
        )
        view_menu.addAction(self._action_toggle_properties)

        self._action_compact_mode = QAction(
            "⛶ Tela cheia (modo zen)", self,
        )
        self._action_compact_mode.setCheckable(True)
        self._action_compact_mode.setShortcut("F11")
        self._action_compact_mode.setStatusTip(
            "Modo tela cheia: oculta toda a chrome (F11)"
        )
        self._action_compact_mode.toggled.connect(
            lambda checked: self.schematic_pp.set_compact_mode(checked),
        )
        view_menu.addAction(self._action_compact_mode)
        view_menu.addSeparator()
        # v1.1.0: Modo Online (single-line diagram com resultados
        # sobrepostos ao esquemático ativo, estilo PTW Online View).
        self._action_online_view = QAction(
            "📡 Modo Online (resultados sobre o esquemático)", self,
        )
        self._action_online_view.setCheckable(True)
        self._action_online_view.setChecked(False)
        self._action_online_view.setShortcut("Ctrl+Shift+O")
        self._action_online_view.setStatusTip(
            "Sobrepõe Ik''/V/loading dos resultados de SC/PF "
            "diretamente no esquemático (estilo PTW Online View). "
            "Atalho Ctrl+Shift+O."
        )
        self._action_online_view.toggled.connect(
            self._on_toggle_online_view,
        )
        view_menu.addAction(self._action_online_view)
        view_menu.addSeparator()
        # v0.93.1: toggle barra de ferramentas (oculta por default)
        self._toggle_main_toolbar_action = QAction(
            "Mostrar barra de ferramentas", self,
        )
        self._toggle_main_toolbar_action.setCheckable(True)
        self._toggle_main_toolbar_action.setChecked(False)
        self._toggle_main_toolbar_action.setShortcut("Ctrl+Alt+T")
        self._toggle_main_toolbar_action.setStatusTip(
            "Mostra/oculta a barra de ícones do topo (Ctrl+Alt+T) "
            "— duplica ações do menu Análise."
        )
        self._toggle_main_toolbar_action.toggled.connect(
            self._on_toggle_main_toolbar,
        )
        view_menu.addAction(self._toggle_main_toolbar_action)
        # v0.28.3-PRO Onda 3.2: toggle console
        self._toggle_console_action = QAction("Console", self)
        self._toggle_console_action.setCheckable(True)
        self._toggle_console_action.setChecked(True)
        self._toggle_console_action.setShortcut("Ctrl+`")
        self._toggle_console_action.setStatusTip(
            "Mostra/oculta painel de console (Ctrl+`)"
        )
        self._toggle_console_action.toggled.connect(
            self._on_toggle_console,
        )
        view_menu.addAction(self._toggle_console_action)
        view_menu.addSeparator()
        # v0.35: plot widgets dockable
        # v1.4.5 — Renomeado "Gráficos" → "Resultados (gráficos das
        # análises)". Cada dock abre com empty state explicativo
        # quando o estudo prerequisito ainda não rodou (paridade
        # PTW Datablock Reports). Feedback do user gate v1.4.4:
        # "menu Visualizar > Gráficos pouco intuitivo".
        plots_menu = view_menu.addMenu("Resultados (gráficos das análises)")
        act_pf = plots_menu.addAction(
            "📊 Perfil de Tensão (Power Flow)",
            lambda: self._ensure_plot_dock("pf_voltage"),
        )
        act_pf.setStatusTip(
            "Disponível após Power Flow (F5 → Power Flow)"
        )
        act_sc = plots_menu.addAction(
            "🥧 Contribuição das Fontes (Curto-Circuito)",
            lambda: self._ensure_plot_dock("sc_pie"),
        )
        act_sc.setStatusTip(
            "Disponível após Curto-circuito (F5 → IEC 60909)"
        )
        act_tcc = plots_menu.addAction(
            "📉 Curvas de Coordenação (TCC)",
            lambda: self._ensure_plot_dock("tcc_overlay"),
        )
        act_tcc.setStatusTip(
            "Disponível após Coordenação (F5 → IEEE 242)"
        )
        act_mc = plots_menu.addAction(
            "🎲 Histograma Monte Carlo (Arc-Flash)",
            lambda: self._ensure_plot_dock("mc_hist"),
        )
        act_mc.setStatusTip(
            "Disponível após Monte Carlo Reliability"
        )
        view_menu.addSeparator()
        self._dark_mode_action = QAction("Modo escuro", self)
        self._dark_mode_action.setCheckable(True)
        # v0.27.6: default LIGHT (industrial gray ATPDraw-style).
        # Usuário pode trocar via menu Visualizar → Modo escuro.
        self._dark_mode_action.setChecked(
            self._settings.value("dark_mode", "false") == "true"
        )
        self._dark_mode_action.toggled.connect(self._on_toggle_dark_mode)
        view_menu.addAction(self._dark_mode_action)

        # v0.92: Validação foi movida para perto de Análise no topo do
        # menu bar (uso freqüente antes de gerar laudo). Mantemos só
        # o atalho global Ctrl+Shift+V via QShortcut implícito da
        # action declarada acima.

        # v0.93.2 — UM SÓ menu no topo. Botão verde "▶ Executar
        # Análise" colocado no canto direito do menu bar via
        # cornerWidget. Visível sem ocupar nova linha. Esta é a
        # ação MAIS frequente do app (atalho F5 também).
        from PySide6.QtWidgets import QPushButton
        self._menu_run_button = QPushButton("▶ Executar Análise")
        self._menu_run_button.setShortcut("F5")
        self._menu_run_button.setToolTip(
            "Executar análises do esquemático (F5):\n"
            "• Curto-circuito (IEC 60909)\n"
            "• Fluxo de potência (IEEE 399)\n"
            "• Coordenação e seletividade (IEEE 242)\n"
            "• Arc-flash (NBR 17227 / IEEE 1584)\n"
            "• Estudo completo do barramento"
        )
        self._menu_run_button.setStyleSheet(
            "QPushButton { "
            "  background-color: #2ca02c; color: white; "
            "  font-weight: bold; padding: 4px 14px; "
            "  border-radius: 3px; margin: 2px; "
            "}"
            "QPushButton:hover { background-color: #208a20; }"
            "QPushButton:pressed { background-color: #186818; }"
        )
        # Conecta ao mesmo handler do botão antigo da PpEditor toolbar
        self._menu_run_button.clicked.connect(
            self._on_run_analysis_dialog,
        )
        menu_bar.setCornerWidget(
            self._menu_run_button, Qt.TopRightCorner,
        )

    def _on_toggle_console(self, checked: bool) -> None:
        """v0.28.3-PRO Onda 3.2: mostra/oculta console panel."""
        if hasattr(self, "_console_panel"):
            self._console_panel.setVisible(checked)

    def _on_toggle_main_toolbar(self, checked: bool) -> None:
        """v0.93.1: mostra/oculta a barra de ferramentas do topo
        (Ctrl+Alt+T). Oculta por default — duplica menu Análise."""
        if hasattr(self, "_main_toolbar"):
            self._main_toolbar.setVisible(checked)

    # ------------------------------------------------------------------
    # v1.1.0 — Modo Online (single-line diagram online overlay)
    # ------------------------------------------------------------------

    def _online_overlay(self):
        """v1.1.0: lazy ``OnlineOverlayManager`` associado ao
        MainWindow. Vive enquanto o projeto estiver aberto."""
        from app.gui.schematic_pp.online_overlay import (
            OnlineOverlayManager,
        )
        if not hasattr(self, "_online_overlay_mgr"):
            self._online_overlay_mgr = OnlineOverlayManager()
        return self._online_overlay_mgr

    def _on_toggle_online_view(self, checked: bool) -> None:
        """v1.1.0: liga/desliga o modo Online (Ctrl+Shift+O).

        Quando ON, anota cada BUS visível com Ik''/ip do cache
        de SC se houver. Cor verde/amarelo/vermelho conforme
        utilization vs. rating do bus.

        Quando OFF, limpa todas as anotações.
        """
        overlay = self._online_overlay()
        overlay.set_enabled(checked)
        if checked:
            self._refresh_online_overlay()
            if hasattr(self, "_console_panel"):
                self._console_panel.append_info(
                    "Modo Online ATIVO — resultados sobre o esquemático "
                    "(Ctrl+Shift+O para desativar)."
                )
        else:
            if hasattr(self, "_console_panel"):
                self._console_panel.append_info(
                    "Modo Online desativado."
                )

    def _refresh_online_overlay(self) -> None:
        """v1.1.0: re-aplica anotações Online a partir do cache
        atual. Chamado ao final de cada análise para manter
        o overlay sincronizado.
        """
        overlay = self._online_overlay()
        if not overlay.is_enabled():
            return
        try:
            scene = self.schematic_pp.scene
        except AttributeError:
            return
        cache = self._study_cache()
        n = overlay.refresh(scene, cache)
        if hasattr(self, "_console_panel") and n > 0:
            self._console_panel.append_info(
                f"Online: {n} componente(s) anotado(s)."
            )

    def _on_pp_compact_mode_changed(self, enabled: bool) -> None:
        """v0.93.1: modo "tela cheia" total — quando o PpEditor
        entra em compact mode (F11), também oculta a menu bar
        + tab bar do MainWindow para máximo espaço de canvas.

        Esc ou F11 saem. Modo zen para apresentações ou
        modelagem em sistemas com pouca tela.
        """
        # Ocultar menu bar
        if self.menuBar() is not None:
            self.menuBar().setVisible(not enabled)
        # Tab bar — ocultar SOMENTE o tab bar (mantém o widget
        # ativo visível). Em PySide6, o tab bar é acessível via
        # ``tabBar()`` do QTabWidget.
        if hasattr(self, "tabs") and self.tabs is not None:
            self.tabs.tabBar().setVisible(not enabled)
        # Status bar (rodapé) — também oculta para máxima zen
        if self.statusBar() is not None:
            self.statusBar().setVisible(not enabled)

    # ------------------------------------------------------------------
    # v0.35: Plot widgets (lazy created)
    # ------------------------------------------------------------------

    def _ensure_plot_dock(self, kind: str):
        """
        Lazy-create plot dock por kind:
          'pf_voltage', 'sc_pie', 'tcc_overlay', 'mc_hist'

        Retorna o widget pronto (já adicionado ao MainWindow).
        """
        attr = f"_plot_dock_{kind}"
        existing = getattr(self, attr, None)
        if existing is not None:
            existing.show()
            return existing

        from app.gui.plot_widgets import (
            MonteCarloHistogramDock, PowerFlowVoltageProfileDock,
            ScContributionPieDock, TccCurveOverlayDock,
        )
        if kind == "pf_voltage":
            w = PowerFlowVoltageProfileDock(self)
        elif kind == "sc_pie":
            w = ScContributionPieDock(self)
        elif kind == "tcc_overlay":
            w = TccCurveOverlayDock(self)
        elif kind == "mc_hist":
            w = MonteCarloHistogramDock(self)
        else:
            raise ValueError(f"kind desconhecido: {kind!r}")

        self.addDockWidget(Qt.RightDockWidgetArea, w)
        setattr(self, attr, w)
        # Aplica tema atual
        if hasattr(self, "_dark_mode_action"):
            w.apply_theme(self._dark_mode_action.isChecked())
        # v1.7.0 Sprint C: tenta popular do study cache se houver
        # análise rodada — assim dock abre **com dados** ao invés de
        # ficar em empty state quando o estudo já rodou.
        try:
            if hasattr(w, "populate_from_cache"):
                w.populate_from_cache(self._study_cache())
        except Exception:
            # Anti-crash: se cache vazio ou populate falha, mantém
            # empty state (compor de modo defensivo).
            pass
        return w

    def _build_console_panel(self) -> None:
        """
        v0.28.3-PRO Onda 3.2: console dockable na parte de baixo.

        Mostrável/ocultável via View menu. Recebe:
        * Output do AtpRunner (async)
        * Warnings de bus_pipeline / bridge_to_atp
        * Logs de validação
        """
        from app.gui.console_panel import ConsolePanel
        self._console_panel = ConsolePanel(self)
        self.addDockWidget(
            Qt.BottomDockWidgetArea, self._console_panel,
        )
        # Console começa visível mas pode ser fechado pelo usuário
        self._console_panel.show()
        self._console_panel.append_info(
            "Console pronto. Logs de simulação e análises "
            "aparecerão aqui."
        )

    def _build_toolbar(self) -> None:
        """
        v0.28.2-PRO Onda 2.2: Toolbar primária do MainWindow.

        Antes não havia QToolBar no MainWindow — apenas menu.
        Adiciona ações de uso frequente com ícones nativos do Qt
        (QStyle.StandardPixmap) para feel ATPDraw-style.
        """
        tb = QToolBar("Principal", self)
        tb.setObjectName("toolbar_main")
        tb.setMovable(True)
        tb.setIconSize(tb.iconSize() * 0.8)
        self.addToolBar(Qt.TopToolBarArea, tb)
        style = self.style()

        # Arquivo
        act_open = QAction(
            style.standardIcon(QStyle.SP_DialogOpenButton), "Abrir", self,
        )
        act_open.setShortcut("Ctrl+O")
        act_open.setStatusTip("Abrir arquivo .atp (Ctrl+O)")
        act_open.triggered.connect(self._on_open)
        tb.addAction(act_open)

        # v0.28.2-PRO followup: Save (Ctrl+S) primeiro, depois
        # Save As (Ctrl+Shift+S) como ação secundária.
        act_save = QAction(
            style.standardIcon(QStyle.SP_DialogSaveButton),
            "Salvar", self,
        )
        act_save.setShortcut("Ctrl+S")
        act_save.setStatusTip("Salvar caso atual (Ctrl+S)")
        act_save.triggered.connect(self._on_save_current)
        tb.addAction(act_save)

        act_save_as = QAction(
            style.standardIcon(QStyle.SP_DialogSaveButton),
            "Salvar como…", self,
        )
        act_save_as.setShortcut("Ctrl+Shift+S")
        act_save_as.setStatusTip("Salvar caso atual como… (Ctrl+Shift+S)")
        act_save_as.triggered.connect(self._on_save_as)
        tb.addAction(act_save_as)

        tb.addSeparator()

        # Validação + Diff
        act_validate = QAction(
            style.standardIcon(QStyle.SP_DialogApplyButton),
            "Validar", self,
        )
        act_validate.setShortcut("Ctrl+Shift+V")
        act_validate.setStatusTip("Validar projeto (Ctrl+Shift+V)")
        act_validate.triggered.connect(self._on_validate)
        tb.addAction(act_validate)

        act_diff = QAction(
            style.standardIcon(QStyle.SP_FileDialogContentsView),
            "Diff", self,
        )
        act_diff.setShortcut("Ctrl+D")
        act_diff.setStatusTip("Ver diff (Ctrl+D)")
        act_diff.triggered.connect(self._on_update_diff)
        tb.addAction(act_diff)

        tb.addSeparator()

        # v0.92.1: ATP run button removido. Análise é o foco.
        # F5 reaproveitado para "Estudo completo do barramento".
        act_analysis = QAction(
            style.standardIcon(QStyle.SP_FileDialogDetailedView),
            "Estudo do barramento", self,
        )
        act_analysis.setShortcut("F5")
        act_analysis.setStatusTip(
            "Estudo completo do barramento — SC + arc-flash + "
            "coordenação (F5)"
        )
        act_analysis.triggered.connect(self._on_analyze_bus_pipeline)
        tb.addAction(act_analysis)

        act_sc = QAction(
            style.standardIcon(QStyle.SP_BrowserReload),
            "SC", self,
        )
        act_sc.setShortcut("F6")
        act_sc.setStatusTip("Curto-circuito IEC 60909-0 (F6)")
        act_sc.triggered.connect(self._on_analyze_short_circuit)
        tb.addAction(act_sc)

        # v0.92.1: arc-flash + relatório também na toolbar
        act_af = QAction(
            style.standardIcon(QStyle.SP_DialogApplyButton),
            "Arc-Flash", self,
        )
        act_af.setShortcut("F7")
        act_af.setStatusTip(
            "Energia incidente NBR 17227 / IEEE 1584 (F7)"
        )
        act_af.triggered.connect(self._on_analyze_arc_flash)
        tb.addAction(act_af)

        act_rep = QAction(
            style.standardIcon(QStyle.SP_FileDialogContentsView),
            "Laudo", self,
        )
        act_rep.setShortcut("F9")
        act_rep.setStatusTip(
            "Relatório técnico auditável (HTML/PDF) (F9)"
        )
        act_rep.triggered.connect(self._on_export_pipeline_report)
        tb.addAction(act_rep)

        self._main_toolbar = tb
        # v0.93.1: ocultar por default — duplica menu Análise.
        # Toggle via Visualizar → Mostrar toolbar (Ctrl+Alt+T).
        self._main_toolbar.setVisible(False)

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # v0.92.1: case selector + tree "Estrutura ATP" foram
        # OCULTOS (eram exclusivos da integração ATP). Os widgets
        # ainda existem para compatibilidade com handlers legacy,
        # mas não ocupam mais espaço na UI principal.

        # Construído mas escondido (handlers legacy referenciam
        # self.case_combo / self.tree).
        self.case_combo = QComboBox()
        self.case_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.case_combo.setMinimumWidth(200)
        self.case_combo.currentIndexChanged.connect(self._on_case_changed)
        self.case_combo.hide()

        # --- Splitter ---
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)

        # --- Left: tree (oculto em v0.92.1) ---
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Estrutura ATP")
        self.tree.currentItemChanged.connect(self._on_tree_selection)
        # v0.92.1: tree não vai para o splitter — fica órfão
        # (parent ainda é MainWindow, então não é GC-ed). Os
        # tabs principais ocupam toda a largura útil.

        # --- Right: tabs ---
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)

        # v0.92.1 — REORGANIZAÇÃO: tabs ATP-only foram retiradas
        # da UI principal para liberar área de modelagem. Os
        # widgets ainda são construídos (handlers existentes usam
        # self.raw_text, self.topology, etc.) mas NÃO entram em
        # self.tabs. Para um projeto secundário ATP no futuro,
        # basta re-adicionar as linhas ``self.tabs.addTab(...)``.

        # Tab principal: Esquemático Visual (PpEditor) — modelagem
        # do unifilar elétrico, foco do produto.
        self.schematic_pp = PpEditor()
        self.tabs.addTab(
            self.schematic_pp,
            "Esquemático Visual",
        )
        self.schematic_pp.export_requested.connect(self._on_pp_export_project)
        # v0.82: botão verde "▶ Executar Análise" na toolbar PpEditor
        self.schematic_pp.run_analysis_requested.connect(
            self._on_run_analysis_dialog
        )
        # v3.1.3 Sub-sprint B: Link Tag click → navegar entre docs
        self.schematic_pp.link_tag_navigate.connect(
            self._on_link_tag_navigate
        )
        # v3.5.2 (closes SKIPPED_BACKLOG A.2) — registry de one-line
        # documents. Default: schematic_pp registrado como "Main".
        # Per PTW Tutorial §Part 1 p.30-34 (multi-document navigation).
        self._documents_registry: dict[str, "QWidget"] = {}
        self.register_document("Main", self.schematic_pp)
        # v0.93.1: ⛶ Tela cheia REAL — oculta menu bar + tab bar
        # do MainWindow quando o PpEditor entra em modo compacto.
        # Esc ou F11 sai. Modo "zen" total: apenas canvas visível.
        self.schematic_pp.compact_mode_changed.connect(
            self._on_pp_compact_mode_changed,
        )
        # v0.90: auto-save manager + cleanup de recoveries antigas.
        try:
            from app.gui.auto_save import (
                AutoSaveManager, cleanup_old_recoveries,
            )
            cleanup_old_recoveries(max_age_days=30)
            self.auto_save = AutoSaveManager(
                editor=self.schematic_pp,
                interval_seconds=60,
                parent=self,
            )
            self.auto_save.saved.connect(self._on_autosave_saved)
            self.auto_save.start()
        except ImportError:
            self.auto_save = None
        # v0.91: title bar reflete dirty state do PpEditor.
        self.schematic_pp.undo_stack.cleanChanged.connect(
            self._on_pp_clean_changed,
        )

        # v1.4.1: Tabs "Detalhes" e "Validação" REMOVIDAS por
        # estarem orfãs após o reposicionamento v0.92.2 (sem ATP).
        # - "Detalhes" usava QTreeWidget de modelos ATP que foi
        #   retirado em v0.92.1 → ficava sempre "Selecione um item
        #   na árvore" sem árvore.
        # - "Validação" populava de validators ATP-specific →
        #   ficava sempre vazia.
        # As funcionalidades equivalentes seguem disponíveis:
        # - Propriedades de componente: painel direito do PpEditor
        # - Validação NBR/IEC: menu Validação > Validar projeto
        #
        # Os widgets `self.details_widget` e `self.val_list` são
        # mantidos como atributos para backward compat com handlers
        # que possam referenciá-los, mas NÃO são adicionados ao
        # TabWidget (não aparecem na UI).
        self._build_details_tab()  # cria widget orfão (não usado)
        self.val_list = QListWidget()
        self.val_list.setFont(QFont(MONO_FONT, MONO_SIZE))

        # Tab 2: Agente Claude (assistente de análise)
        self.chat = ChatWidget()
        self.tabs.addTab(self.chat, "Agente")

        # --- Widgets ATP-only (instanciados para compatibilidade
        # com handlers legacy, mas NÃO adicionados a self.tabs) ---
        self.raw_text = QPlainTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.raw_text.setFont(QFont(MONO_FONT, MONO_SIZE))

        self.topology = TopologyWidget()

        # SchematicEditor (legacy ATP) — instanciado mas oculto.
        self.schematic = SchematicEditor()
        self.schematic.project_created.connect(
            self._on_schematic_new_project,
        )

        self.diff_text = QPlainTextEdit()
        self.diff_text.setReadOnly(True)
        self.diff_text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.diff_text.setFont(QFont(MONO_FONT, MONO_SIZE))

        self.results_text = QPlainTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.results_text.setFont(QFont(MONO_FONT, MONO_SIZE))

        self.waveform = WaveformWidget()
        self.compare = CompareWidget()

        # Default tab: Esquemático Visual (índice 0)
        self.tabs.setCurrentIndex(0)

        splitter.setSizes([300, 980])

    def _build_details_tab(self) -> None:
        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout(self.details_widget)
        self.details_layout.setSpacing(8)

        # Info label (top)
        self.details_label = QLabel("Selecione um item na árvore.")
        self.details_label.setWordWrap(True)
        self.details_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.details_label.setFont(QFont(MONO_FONT, MONO_SIZE))
        self.details_layout.addWidget(self.details_label)

        # INPUT table (USE)
        self.input_group = QGroupBox("INPUT")
        input_lay = QVBoxLayout(self.input_group)
        self.input_table = QTableWidget()
        self.input_table.setColumnCount(2)
        self.input_table.setHorizontalHeaderLabels(["Local", "Mapeado para"])
        self.input_table.horizontalHeader().setStretchLastSection(True)
        input_lay.addWidget(self.input_table)
        self.input_group.hide()
        self.details_layout.addWidget(self.input_group)

        # DATA table (USE — editable)
        self.data_group = QGroupBox("DATA (editável)")
        data_lay = QVBoxLayout(self.data_group)
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(3)
        self.data_table.setHorizontalHeaderLabels(["Parâmetro", "Valor", "Default"])
        self.data_table.horizontalHeader().setStretchLastSection(True)
        data_lay.addWidget(self.data_table)
        self.data_group.hide()
        self.details_layout.addWidget(self.data_group)

        # OUTPUT table (USE)
        self.output_group = QGroupBox("OUTPUT")
        output_lay = QVBoxLayout(self.output_group)
        self.output_table = QTableWidget()
        self.output_table.setColumnCount(2)
        self.output_table.setHorizontalHeaderLabels(["Global", "Local"])
        self.output_table.horizontalHeader().setStretchLastSection(True)
        output_lay.addWidget(self.output_table)
        self.output_group.hide()
        self.details_layout.addWidget(self.output_group)

        # MODEL DATA table (editable defaults) — GUI-010
        self.model_data_group = QGroupBox("MODEL DATA (editar defaults)")
        mdata_lay = QVBoxLayout(self.model_data_group)
        self.model_data_table = QTableWidget()
        self.model_data_table.setColumnCount(2)
        self.model_data_table.setHorizontalHeaderLabels(["Parâmetro", "Default"])
        self.model_data_table.horizontalHeader().setStretchLastSection(True)
        mdata_lay.addWidget(self.model_data_table)
        self.model_data_group.hide()
        self.details_layout.addWidget(self.model_data_group)

        self.details_layout.addStretch()
        # v1.4.1: NÃO adiciona ao TabWidget (tab "Detalhes" foi
        # removida por estar orfã sem ATP). Widget criado apenas
        # para backward compat — handlers legacy podem referenciá-lo.

    def _build_status_bar(self) -> None:
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self.status.showMessage(
            "Pronto — abra um esquemático .sch ou crie um novo "
            "via paleta de componentes."
        )

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    @property
    def is_dark(self) -> bool:
        return self._dark_mode_action.isChecked()

    def apply_theme(self) -> None:
        """Apply the current theme to the entire application."""
        dark = self.is_dark
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_stylesheet(dark))
        palette = get_palette(dark)

        # Update topology widget
        self.topology.apply_theme(palette)

        # Update schematic editor
        self.schematic.apply_theme(palette)

        # Update waveform widget
        self.waveform.apply_theme(palette)

        # Update chat widget
        self.chat.apply_theme(palette)

        # Update compare widget
        self.compare.apply_theme(palette)

        # Re-run validation to apply new colors
        if self.project is not None:
            self._on_validate()

    def _on_toggle_dark_mode(self, checked: bool) -> None:
        self._settings.setValue("dark_mode", "true" if checked else "false")
        self.apply_theme()
        self.status.showMessage(f"Tema: {'escuro' if checked else 'claro'}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _hide_use_tables(self) -> None:
        self.input_group.hide()
        self.data_group.hide()
        self.output_group.hide()
        self.model_data_group.hide()
        self.input_table.setRowCount(0)
        self.data_table.setRowCount(0)
        self.output_table.setRowCount(0)
        self.model_data_table.setRowCount(0)
        self._current_use = None
        self._current_model = None

    # ------------------------------------------------------------------
    # File actions
    # ------------------------------------------------------------------

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir arquivo ATP", "", "ATP files (*.atp);;All files (*)"
        )
        if not path:
            return
        self._load_file(path)

    def _load_file(self, path: str) -> None:
        try:
            proj = parse_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao ler arquivo:\n{e}")
            return

        # Register in multi-case dict
        self._cases[path] = proj
        self._active_case = path

        # v0.28.2-PRO Onda 2.4: adiciona aos recentes
        self._add_to_recent(path)

        # Update combo — block signals to avoid re-entrant _on_case_changed
        self.case_combo.blockSignals(True)
        existing = [self.case_combo.itemData(i) for i in range(self.case_combo.count())]
        if path not in existing:
            self.case_combo.addItem(Path(path).name, path)
        idx = [self.case_combo.itemData(i) for i in range(self.case_combo.count())].index(path)
        self.case_combo.setCurrentIndex(idx)
        self.case_combo.blockSignals(False)

        self._refresh_views()

    def _on_schematic_new_project(self, project) -> None:
        """Register an empty project created from the schematic toolbar.

        A synthetic path key ``<novo-projeto-N>`` is used until the user
        saves the file via *Save As*, at which point _load_file / _on_save_as
        replace the key with the real path.
        """
        # Find a unique synthetic key
        n = 1
        while f"<novo-projeto-{n}>" in self._cases:
            n += 1
        synthetic = f"<novo-projeto-{n}>"

        project.file_path = synthetic
        self._cases[synthetic] = project
        self._active_case = synthetic

        self.case_combo.blockSignals(True)
        self.case_combo.addItem(synthetic, synthetic)
        idx = [self.case_combo.itemData(i) for i in range(self.case_combo.count())].index(synthetic)
        self.case_combo.setCurrentIndex(idx)
        self.case_combo.blockSignals(False)

        self._refresh_views()

    # ------------------------------------------------------------------
    # Visual preprocessor (Qucs-like) integration
    # ------------------------------------------------------------------

    def _on_pp_open_sch(self) -> None:
        """Open a Qucs ``.sch`` file into the visual preprocessor."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir esquemático Qucs",
            "", "Esquemáticos Qucs (*.sch);;Todos os arquivos (*)",
        )
        if not path:
            return
        try:
            project = parse_sch_file(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(
                self, "Erro ao abrir .sch", f"Falha ao ler o arquivo:\n{e}"
            )
            return
        self.schematic_pp.scene.load_project(project)
        # v0.28.2-PRO Onda 2.4: adiciona aos recentes
        self._add_to_recent(path)
        # Bring tab into focus so the user immediately sees the result.
        self.tabs.setCurrentWidget(self.schematic_pp)
        # v0.82: hint contextual baseado no conteúdo do schematic
        bus_count = sum(
            1 for c in project.components if c.type == "BUS"
        )
        if bus_count > 0:
            hint = (
                f"Esquemático carregado ({bus_count} BUS) — "
                "clique ▶ Executar Análise para iniciar estudos"
            )
        else:
            hint = (
                "Esquemático carregado (sem BUS) — adicione um "
                "BUS via Paleta para habilitar análises completas"
            )
        self.status.showMessage(hint, 8000)
        if hasattr(self, "_console_panel"):
            self._console_panel.append_info(
                f"Esquemático: {path} | {bus_count} BUS"
            )

    def _on_pp_new_project(self) -> None:
        """v0.28.2-PRO Onda 2.3: novo projeto vazio no PP editor."""
        from app.preprocessor.models import PpProject
        self.schematic_pp.scene.load_project(PpProject())
        self.tabs.setCurrentWidget(self.schematic_pp)
        self.status.showMessage("Novo projeto PP criado")

    # v0.90 — Auto-save handlers
    # ------------------------------------------------------------------

    def _on_pp_clean_changed(self, _is_clean: bool) -> None:
        """v0.91: cleanChanged do undo_stack do PpEditor →
        atualiza title bar."""
        self._update_window_title()

    def _on_autosave_saved(self, target_path: str) -> None:
        """v0.90: status bar atualiza após cada autosave."""
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            self.status.showMessage(
                f"💾 Auto-save: {ts}", 3000,
            )
        except Exception:
            pass

    def offer_recovery_if_available(self) -> bool:
        """
        v0.90: chamado pelo entry-point após criar MainWindow.
        Varre recents e ``~/.olivas/recovery/`` em busca de
        autosaves elegíveis. Se encontrar, oferece dialog
        de recuperação.

        Retorna True se algo foi recuperado, False se não havia
        nada ou o usuário descartou.
        """
        try:
            from app.gui.auto_save import (
                autosave_path_for, find_untitled_recoveries,
                is_autosave_newer_than_original, remove_autosave_for,
            )
        except ImportError:
            return False

        # 1) Autosaves de recents (.sch.autosave > .sch)
        candidates: list[str] = []
        recents = self._load_recent_files()
        for sch_path in recents:
            autosave = autosave_path_for(sch_path)
            if is_autosave_newer_than_original(
                str(autosave), sch_path,
            ):
                candidates.append(str(autosave))

        # 2) Untitled recoveries
        for p in find_untitled_recoveries():
            candidates.append(str(p))

        if not candidates:
            return False

        # Pega o primeiro (mais recente OR primeiro de recents).
        # MVP: mostra apenas 1 dialog de cada vez. Usuário pode
        # rodar de novo para recuperar outros.
        most_recent = max(
            candidates,
            key=lambda p: Path(p).stat().st_mtime,
        )
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Recuperar trabalho não salvo?",
            f"Foi encontrado um arquivo de recuperação:\n\n"
            f"{most_recent}\n\n"
            f"Deseja recuperar este trabalho?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Ignore,
        )
        if reply == QMessageBox.Yes:
            try:
                self.schematic_pp.load_from_sch(most_recent)
                self.tabs.setCurrentWidget(self.schematic_pp)
                self.status.showMessage(
                    f"Trabalho recuperado de {Path(most_recent).name}",
                )
                # Limpa o autosave após carregar.
                if most_recent.endswith(".autosave"):
                    remove_autosave_for(most_recent[:-len(".autosave")])
                else:
                    Path(most_recent).unlink(missing_ok=True)
                return True
            except Exception as e:
                QMessageBox.critical(
                    self, "Erro na recuperação",
                    f"Falha ao carregar:\n{e}",
                )
                return False
        elif reply == QMessageBox.No:
            # Descartar — remove o autosave
            try:
                if most_recent.endswith(".autosave"):
                    remove_autosave_for(most_recent[:-len(".autosave")])
                else:
                    Path(most_recent).unlink(missing_ok=True)
            except OSError:
                pass
            return False
        # Ignore: deixa pra próxima vez.
        return False

    def _on_pp_new_from_template(self, template_id: str) -> None:
        """
        v0.89: cria novo projeto PP a partir de um template
        pré-pronto (welcome dialog).

        Builders ficam em :mod:`app.preprocessor.templates`.
        Mensagem de status menciona o template carregado.
        """
        try:
            from app.preprocessor.templates import (
                build_template, get_template_builder, TEMPLATES,
            )
        except ImportError:
            QMessageBox.warning(
                self, "Templates",
                "Módulo de templates não disponível.",
            )
            return
        builder = get_template_builder(template_id)
        if builder is None:
            QMessageBox.warning(
                self, "Template desconhecido",
                f"Template {template_id!r} não existe. "
                f"Disponíveis: "
                + ", ".join(t[0] for t in TEMPLATES),
            )
            return
        try:
            project = build_template(template_id)
        except Exception as e:
            QMessageBox.critical(
                self, "Erro ao construir template",
                f"Template {template_id!r} falhou:\n{e}",
            )
            return
        self.schematic_pp.scene.load_project(project)
        self.tabs.setCurrentWidget(self.schematic_pp)
        # Sumário do template para status bar
        label = next(
            (t[1] for t in TEMPLATES if t[0] == template_id),
            template_id,
        )
        self.status.showMessage(
            f"Template carregado: {label} "
            f"({len(project.components)} componentes, "
            f"{len(project.wires)} fios)",
        )

    def _on_pp_save_sch(self) -> None:
        """Serialize the current preprocessor scene to a ``.sch`` file."""
        project = self.schematic_pp.scene.to_project()
        if not project.components and not project.wires:
            QMessageBox.information(
                self, "Esquemático vazio",
                "Não há componentes ou fios para salvar."
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar esquemático Qucs",
            "", "Esquemáticos Qucs (*.sch);;Todos os arquivos (*)",
        )
        if not path:
            return
        try:
            serialize_sch_file(project, path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(
                self, "Erro ao salvar .sch", f"Falha ao escrever o arquivo:\n{e}"
            )
            return
        self.status.showMessage(f"Esquemático salvo: {path}")

    def _on_pp_import_atp(self) -> None:
        """Import the currently active ATP case into the visual preprocessor.

        Uses :func:`app.preprocessor.bridge_from_atp.from_atp` to generate
        placeholder component positions so the user can reorganize the
        layout before re-exporting.
        """
        if self.project is None:
            QMessageBox.information(
                self, "Nenhum caso ativo",
                "Abra ou crie um projeto ATP antes de importar para o PP."
            )
            return
        try:
            pp_project = from_atp(self.project)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(
                self, "Erro ao importar",
                f"Falha ao converter o projeto ATP para o PP:\n{e}"
            )
            return
        self.schematic_pp.scene.load_project(pp_project)
        self.tabs.setCurrentWidget(self.schematic_pp)
        self.status.showMessage(
            f"Projeto ATP importado para o PP: "
            f"{len(pp_project.components)} componente(s), "
            f"{len(pp_project.wires)} fio(s)."
        )

    def _on_pp_export_project(self, project: Optional[AtpProject] = None) -> None:
        """Export the PP scene to a brand-new ATP case.

        May be called two ways:

        * triggered directly from the File menu (``project`` is None), in
          which case we ask the editor to build the AtpProject;
        * connected to :attr:`PpEditor.export_requested`, where the
          ``AtpProject`` is already delivered as the signal payload.
        """
        if project is None:
            try:
                project = self.schematic_pp.export_to_atp()
            except Exception as e:  # noqa: BLE001
                QMessageBox.critical(
                    self, "Erro ao exportar",
                    f"Falha ao gerar o projeto ATP a partir do PP:\n{e}"
                )
                return

        if project is None:
            QMessageBox.information(
                self, "Nada a exportar",
                "O esquemático visual está vazio."
            )
            return

        # Register as a synthetic new case (same pattern as schematic editor).
        n = 1
        while f"<pp-export-{n}>" in self._cases:
            n += 1
        synthetic = f"<pp-export-{n}>"
        project.file_path = synthetic
        self._cases[synthetic] = project
        self._active_case = synthetic

        self.case_combo.blockSignals(True)
        self.case_combo.addItem(synthetic, synthetic)
        idx = [
            self.case_combo.itemData(i)
            for i in range(self.case_combo.count())
        ].index(synthetic)
        self.case_combo.setCurrentIndex(idx)
        self.case_combo.blockSignals(False)

        self._refresh_views()
        self.status.showMessage(
            f"PP exportado para novo caso ATP: {synthetic} "
            f"({len(project.branches)} branch, {len(project.sources)} source, "
            f"{len(project.switches)} switch)."
        )

    def _on_case_changed(self, index: int) -> None:
        if index < 0:
            return
        path = self.case_combo.itemData(index)
        if path and path in self._cases:
            self._active_case = path
            self._refresh_views()

    def _on_close_case(self) -> None:
        if self._active_case is None:
            return
        # v0.28.2-PRO Onda 2.5 followup: confirma se há mudanças
        if self._is_modified(self._active_case):
            reply = QMessageBox.question(
                self,
                "Mudanças não salvas",
                f"O caso {Path(self._active_case).name!r} tem "
                "alterações não salvas. Fechar mesmo assim?\n\n"
                "Use Cancelar para voltar e salvar (Ctrl+S).",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if reply != QMessageBox.Yes:
                return
        self._modified_paths.discard(self._active_case)
        self._cases.pop(self._active_case, None)
        idx = self.case_combo.currentIndex()
        self.case_combo.removeItem(idx)
        self.compare.update_cases(self._cases)
        if self.case_combo.count() > 0:
            self._active_case = self.case_combo.itemData(0)
            self.case_combo.setCurrentIndex(0)
        else:
            self._active_case = None
            self._clear_views()
        self._update_window_title()

    def _clear_views(self) -> None:
        self.tree.clear()
        self.raw_text.clear()
        self.results_text.clear()
        self.diff_text.clear()
        self.val_list.clear()
        self.waveform.clear_results()
        self.setWindowTitle("Olivas Power System Studio")
        self.status.showMessage("Nenhum caso aberto.")

    def _refresh_views(self) -> None:
        """Refresh all views for the active case."""
        if self.project is None:
            self._clear_views()
            return
        self._populate_tree()
        self.raw_text.setPlainText("\n".join(self.project.raw_lines))
        self.topology.load_project(self.project)
        self.schematic.load_project(self.project)
        self.chat.sync_project(self.project)
        self.chat._api.runner = self.runner
        self.compare.update_cases(self._cases)
        self._load_results()
        path = self.project.file_path
        self.status.showMessage(f"Caso ativo: {path}")
        # v0.92.2: rebrand
        self.setWindowTitle(
            f"Olivas Power System Studio — {Path(path).name}"
        )
        self._on_validate()

    def _on_save_as(self) -> None:
        if self.project is None:
            QMessageBox.information(self, "Info", "Nenhum projeto aberto.")
            return

        self._commit_table_edits()

        content = serialize_project(self.project)
        original = "\n".join(self.project.raw_lines)

        # Show preview if there are changes
        if has_changes(original, content):
            diff_lines = compute_context_diff(original, content)
            dialog = DiffPreviewDialog(diff_lines, self)
            if dialog.exec() != QDialog.Accepted:
                self.status.showMessage("Salvamento cancelado pelo usuário.")
                return
        else:
            reply = QMessageBox.question(
                self,
                "Salvar como",
                "Nenhuma alteração detectada. Salvar mesmo assim?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar como", "", "ATP files (*.atp);;All files (*)"
        )
        if not path:
            return

        try:
            Path(path).write_text(content, encoding="utf-8")
            self.status.showMessage(f"Arquivo salvo: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar:\n{e}")

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def _on_configure_license(self) -> None:
        """v4.1.0 commercial Sprint 2: dialog de ativação de licença Pro."""
        from app.gui.license_dialog import LicenseDialog
        dlg = LicenseDialog(self)
        dlg.exec()
        # Após fechar, refresh do menu de features (best-effort)
        try:
            self.status.showMessage(
                "Licença atualizada — features podem ter mudado.", 5000,
            )
        except Exception:
            pass

    def _on_configure_api_key(self) -> None:
        """v0.81: dialog para configurar API key Claude."""
        from app.gui.api_key_dialog import ApiKeyDialog
        dlg = ApiKeyDialog(self)
        if dlg.exec():
            # Reinicializa client do chat global se já criado
            if hasattr(self, "chat") and hasattr(self.chat, "_init_claude"):
                try:
                    self.chat._init_claude()
                except Exception:
                    pass
            self.status.showMessage(
                "API Key configurada — chat ativo.", 5000,
            )

    def _on_configure_atp(self) -> None:
        current = self.runner.executable_path or ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar executável ATP", current,
            "Executáveis (*.exe *.bat *.cmd);;Todos os arquivos (*)",
        )
        if path:
            self.runner.executable_path = path
            self._settings.setValue("atp_executable_path", path)
            self.status.showMessage(f"ATP configurado: {path}")

    def _on_configure_timeout(self) -> None:
        current = self.runner.timeout
        value, ok = QInputDialog.getInt(
            self, "Configurar Timeout", "Timeout de execução (segundos):",
            value=current, min=10, max=3600,
        )
        if ok:
            self.runner.timeout = value
            self._settings.setValue("atp_timeout", value)
            self.status.showMessage(f"Timeout configurado: {value}s")

    def _resolve_atp_run_path(self) -> Optional[str]:
        """
        v0.91.8: resolve um path real (disk file) para o ATP rodar.

        Comportamento:

        * Se ``self.project.file_path`` é um arquivo real no
          disco → retorna o path direto.
        * Se é sintético (``<pp-export-N>``, ``<scratch>``, etc.)
          → serializa o ``AtpProject`` para arquivo temporário
          ``%TEMP%/olivas_run/<safe_name>.atp`` e retorna esse
          path.
        * Se serialização falhar → mostra QMessageBox.warning e
          retorna ``None``.

        UX: usuário não precisa "salvar como" só para rodar
        uma simulação rápida. O temp file fica no diretório
        de runs e a próxima execução overwrite no mesmo lugar.
        """
        if self.project is None:
            return None
        path = self.project.file_path
        # Caso 1: path real no disco
        try:
            if path and Path(path).is_file():
                return str(Path(path).resolve())
        except (OSError, ValueError):
            pass

        # Caso 2: in-memory / synthetic — serializa para temp.
        try:
            from app.core.serializer import serialize_project
            text = serialize_project(self.project)
        except Exception as e:
            QMessageBox.warning(
                self, "Erro ao preparar ATP",
                f"Falha ao serializar o projeto in-memory para "
                f"execução:\n{e}",
            )
            return None
        # Nome seguro a partir do file_path sintético
        import re
        import tempfile
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(path or "scratch"))
        safe = safe.strip("_") or "scratch"
        run_dir = Path(tempfile.gettempdir()) / "olivas_run"
        run_dir.mkdir(parents=True, exist_ok=True)
        target = run_dir / f"{safe}.atp"
        try:
            target.write_text(text, encoding="utf-8")
        except OSError as e:
            QMessageBox.warning(
                self, "Erro ao gravar temp",
                f"Falha ao gravar arquivo temporário em "
                f"{target}:\n{e}",
            )
            return None
        # Mensagem informativa no console
        if hasattr(self, "_console_panel"):
            try:
                self._console_panel.append_info(
                    f"Projeto in-memory serializado para "
                    f"{target} (não persistente)."
                )
            except Exception:
                pass
        return str(target)

    def _on_run_atp(self) -> None:
        """
        v0.28.3-PRO Onda 3.1: execução ASSÍNCRONA do ATP em
        QThread, com progress dialog + cancel.

        Antes: bloqueava UI inteira por todo tempo da simulação.

        v0.91.8: detecta projetos in-memory (file_path
        sintético tipo ``<pp-export-N>``) e serializa para
        arquivo temporário antes de rodar. Antes, o runner
        falhava com "ATP file not found" porque o
        ``file_path`` não era um arquivo real no disco.
        """
        if self.project is None:
            QMessageBox.information(self, "Info", "Nenhum projeto aberto.")
            return

        if not self.runner.is_configured():
            QMessageBox.warning(
                self, "ATP não configurado",
                "Configure o caminho do executável ATP primeiro.\n"
                "Menu: Simulação → Configurar caminho ATP",
            )
            return

        # v0.91.8: resolve path real para o ATP. Se for in-memory
        # (sintético), serializa para temp file. Se save manual
        # falhar (disco cheio etc.), aborta com mensagem clara.
        atp_run_path = self._resolve_atp_run_path()
        if atp_run_path is None:
            return    # mensagem já mostrada
        # v0.91.8: armazena para _load_results encontrar .pl4/.lis
        # quando o original file_path for sintético.
        self._last_atp_run_path = atp_run_path

        # v0.91.5: dialog rico com fases + output ao vivo.
        # v0.91.7: SignalRelay para thread-safety entre Python
        # readers do runner e widgets Qt do main thread.
        from app.gui.atp_progress_dialog import AtpProgressDialog
        from app.gui.signal_relay import SignalRelay
        # v0.91.8: usa atp_run_path (real disk file) para nome
        # exibido + execução. ``self.project.file_path`` pode
        # ser sintético "<pp-export-N>" para projetos in-memory.
        atp_filename = Path(atp_run_path).name
        progress = AtpProgressDialog(self, atp_filename)
        progress.setWindowModality(Qt.WindowModal)

        # SignalRelay vive no main thread. Reader threads do
        # runner chamam relay.post_*() (canonical
        # QMetaObject.invokeMethod), que posta evento na queue
        # do main thread → slot @Slot roda no main → emite
        # signal local → handlers conectados rodam no main.
        # Resolve crash "Cannot create children for parent in
        # different thread".
        relay = SignalRelay()
        # Mantém ref para gc não coletar enquanto thread roda.
        self._atp_relay = relay

        # Setup async worker (com relay para marshalling thread-safe)
        # v0.91.8: usa atp_run_path (resolved disk file).
        from app.gui.async_runner import make_run_thread
        thread, worker = make_run_thread(
            self.runner, atp_run_path, relay=relay,
        )
        self._atp_thread = thread
        self._atp_worker = worker

        # Cancel button → request kill (signal cross-thread:
        # progress no main, worker no QThread; AutoConnection ok
        # pois worker é QThread real, não Python thread).
        progress.cancel_requested.connect(worker.request_cancel)
        # Append to console panel for live feedback
        if hasattr(self, "_console_panel"):
            self._console_panel.append_info(
                f"=== Executando ATP: {atp_filename} ==="
            )

        def _on_finished(result):
            # v0.91.5: marca dialog como done; usuário fecha
            # quando quiser ler o output.
            progress.mark_done(result.success, result.message)
            log_info = f"\nLog: {result.log_file}" if result.log_file else ""
            if hasattr(self, "_console_panel"):
                if result.success:
                    self._console_panel.append_info(
                        f"ATP OK. {result.message}"
                    )
                else:
                    self._console_panel.append_error(
                        f"ATP falhou: {result.message}"
                    )
                if result.stderr.strip():
                    self._console_panel.append_log(result.stderr[:1000])
            if result.success:
                QMessageBox.information(
                    self, "Execução ATP",
                    f"ATP executado com sucesso.\n\n"
                    f"{result.stdout[:500]}{log_info}",
                )
                self._load_results()
            else:
                QMessageBox.warning(
                    self, "Execução ATP",
                    f"{result.message}\n\n"
                    f"{result.stderr[:500]}{log_info}",
                )
            self.status.showMessage(result.message)
            self._atp_thread.wait()
            self._atp_thread.deleteLater()
            self._atp_worker.deleteLater()
            self._atp_relay.deleteLater()

        def _on_cancelled():
            progress.mark_cancelled()
            if hasattr(self, "_console_panel"):
                self._console_panel.append_warn(
                    "Simulação ATP cancelada pelo usuário."
                )
            self.status.showMessage("Simulação ATP cancelada.")
            self._atp_thread.wait()
            self._atp_thread.deleteLater()
            self._atp_worker.deleteLater()
            self._atp_relay.deleteLater()

        # v0.91.7: TODAS as conexões via relay (no main thread).
        # AutoConnection é seguro porque tanto emitter (relay)
        # quanto receiver (widgets) estão no main thread.
        relay.run_finished.connect(_on_finished)
        relay.run_cancelled.connect(_on_cancelled)
        relay.phase_changed.connect(progress.set_phase)
        relay.stdout_chunk.connect(progress.append_output)
        relay.stderr_chunk.connect(progress.append_output)
        if hasattr(self, "_console_panel"):
            relay.stdout_chunk.connect(self._console_panel.append_log)
            relay.stderr_chunk.connect(self._console_panel.append_warn)

        self.status.showMessage("Executando ATP em background...")
        progress.show()
        thread.start()

    def _load_results(self) -> None:
        """Try to load result files (.lis, .pl4) associated with the ATP file.

        v0.91.8: usa ``self._last_atp_run_path`` (path real em
        disco, possivelmente um temp file de
        ``_resolve_atp_run_path``) quando disponível. Fallback
        para ``self.project.file_path`` se não houve run prévio.
        """
        self.results_text.clear()
        self.waveform.clear_results()
        if self.project is None:
            return

        # v0.91.8: prefere o path real do último run (pode ser
        # temp file para in-memory project).
        lookup_path = getattr(
            self, "_last_atp_run_path", None,
        ) or self.project.file_path
        found = find_result_files(lookup_path)

        if not found:
            self.results_text.setPlainText(
                "Nenhum arquivo de resultados encontrado (.pl4, .lis).\n\n"
                "Execute a simulação ATP para gerar resultados."
            )
            return

        parts = [f"Arquivos de resultados encontrados: {len(found)}", ""]

        # --- PL4: binary results with transient metrics ---
        if "pl4" in found:
            parts.append(f"PL4: {found['pl4']}")
            try:
                pl4 = read_pl4(found["pl4"])
                parts.append(pl4.summary())
                parts.append("")
                parts.append("=" * 60)
                parts.append("MÉTRICAS DE TRANSITÓRIO POR VARIÁVEL")
                parts.append("=" * 60)

                # Load waveform viewer
                self.waveform.load_results(pl4)

                for var_name in pl4.variables[:30]:
                    var_data = pl4.data.get(var_name, [])
                    if var_data and pl4.time:
                        metrics = compute_transient_metrics(pl4.time, var_data, var_name)
                        parts.append("")
                        parts.append(format_transient_report(metrics))

                if len(pl4.variables) > 30:
                    parts.append(f"\n... (+{len(pl4.variables) - 30} variáveis não exibidas)")

            except Exception as e:
                parts.append(f"Erro ao ler .pl4: {e}")
            parts.append("")

        # --- LIS: text output ---
        if "lis" in found:
            parts.append(f"LIS: {found['lis']}")
            parts.append("=" * 60)
            try:
                lis_content = read_lis(found["lis"])
                lis_lines = lis_content.splitlines()
                parts.extend(lis_lines[:500])
                if len(lis_lines) > 500:
                    parts.append(f"\n... (+{len(lis_lines) - 500} linhas)")
            except Exception as e:
                parts.append(f"Erro ao ler .lis: {e}")

        self.results_text.setPlainText("\n".join(parts))

    def _get_pl4_results(self) -> "AtpResults | None":
        """Try to load PL4 results for the current project."""
        if self.project is None:
            QMessageBox.information(self, "Info", "Nenhum projeto aberto.")
            return None
        found = find_result_files(self.project.file_path)
        if "pl4" not in found:
            QMessageBox.information(
                self, "Info",
                "Nenhum arquivo .pl4 encontrado.\nExecute a simulação primeiro."
            )
            return None
        try:
            return read_pl4(found["pl4"])
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao ler .pl4:\n{e}")
            return None

    def _on_export_waveforms(self) -> None:
        pl4 = self._get_pl4_results()
        if pl4 is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar formas de onda", "", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            out = export_waveforms_csv(pl4, path)
            self.status.showMessage(f"Formas de onda exportadas: {out}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha na exportação:\n{e}")

    def _on_export_metrics(self) -> None:
        pl4 = self._get_pl4_results()
        if pl4 is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar métricas", "", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            out = export_metrics_csv(pl4, path)
            self.status.showMessage(f"Métricas exportadas: {out}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha na exportação:\n{e}")

    def _on_export_report(self) -> None:
        if self.project is None:
            QMessageBox.information(self, "Info", "Nenhum projeto aberto.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar relatório", "", "HTML (*.html)"
        )
        if not path:
            return
        try:
            out = export_html_report(self.project, path)
            self.status.showMessage(f"Relatório exportado: {out}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha na exportação:\n{e}")

    def _on_export_pdf(self) -> None:
        if self.project is None:
            QMessageBox.information(self, "Info", "Nenhum projeto aberto.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar relatório PDF", "", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            out = export_pdf_report(self.project, path)
            self.status.showMessage(f"Relatório PDF exportado: {out}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha na exportação PDF:\n{e}")

    # ------------------------------------------------------------------
    # Análise (v0.28.2-PRO Onda 2.1) — expõe postprocessor na GUI
    # ------------------------------------------------------------------

    def _current_pp_project(self):
        """
        Retorna o PpProject ativo no editor visual (se existir),
        para os estudos que precisam de schematic.

        Usa ``self.schematic_pp.scene.to_project()`` (PpEditor →
        PpScene → PpProject).
        """
        try:
            scene = self.schematic_pp.scene
            return scene.to_project()
        except Exception:
            return None

    # v0.84.1: ``*_qt_args`` absorve o bool ``checked`` que ``QAction.
    # triggered`` injeta como argumento posicional quando esses
    # métodos são conectados via ``addAction(text, slot)`` ou
    # ``triggered.connect(slot)``. Sem isso, o bool sobrescreve
    # ``project`` e o ``isinstance(project, PpProject)`` quebra
    # downstream com "AttributeError: 'bool' object has no
    # attribute 'components'". Callers internos (``_dispatch_
    # analysis``, RunAnalysisDialog) sempre passam ``project=`` /
    # ``bus_id=`` por keyword e não são afetados.

    def _on_analyze_short_circuit(
        self, *_qt_args, project=None, bus_id: str = "",
    ) -> None:
        from app.gui.analysis_dialogs import run_short_circuit_analysis
        if project is None:
            project = self._current_pp_project()
        run_short_circuit_analysis(self, project=project, bus_id=bus_id)

    def _on_analyze_power_flow(self, *_qt_args, project=None) -> None:
        from app.gui.analysis_dialogs import run_power_flow_analysis
        if project is None:
            project = self._current_pp_project()
        run_power_flow_analysis(self, project=project)

    def _on_analyze_motor_starting(
        self, *_qt_args, project=None, bus_id: str = "",
    ) -> None:
        from app.gui.analysis_dialogs import run_motor_starting_analysis
        if project is None:
            project = self._current_pp_project()
        run_motor_starting_analysis(self, project=project, bus_id=bus_id)

    def _on_analyze_arc_flash(
        self, *_qt_args, project=None, bus_id: str = "",
    ) -> None:
        from app.gui.analysis_dialogs import run_arc_flash_analysis
        if project is None:
            project = self._current_pp_project()
        run_arc_flash_analysis(self, project=project, bus_id=bus_id)

    def _on_compare_arc_flash_standards(self, *_qt_args) -> None:
        """
        v1.6.0: abre dialog de comparação multi-standard arc-flash.

        Roda IEEE 1584 + NBR 17227 + EPRI + Doughty-Neal +
        NESC 2023 + CSA Z462 + NFPA 70E §D.5 DC para o mesmo
        caso e mostra side-by-side. Útil para auditoria reglatória.
        """
        from app.gui.arc_flash_comparison_dialog import (
            ArcFlashComparisonDialog,
        )
        dlg = ArcFlashComparisonDialog(parent=self)
        dlg.exec()

    def _on_analyze_demand_load(self, *_qt_args) -> None:
        """
        v1.5.1: abre DAPPER Demand Load Study dialog.

        Estudo orientado ao sistema (não exige seleção de
        componente). Em release futura pode integrar com BUS
        selecionado ou pegar entries do projeto automaticamente.
        """
        from app.gui.demand_load_dialog import DemandLoadDialog
        dlg = DemandLoadDialog(parent=self)
        dlg.exec()

    def _on_analyze_ct_saturation(self, *_qt_args) -> None:
        """v1.4.1 Sprint C + v1.4.5 Sprint C: análise de saturação de
        TC em 3 níveis.

        v1.4.5 (user gate v1.4.4): a análise SÓ é invocável quando
        o usuário **seleciona um TC no canvas**. Sem TC selecionado,
        mostra QMessageBox explicando o workflow PTW-style.

        Modo didático (sem selection) ainda é acessível via
        Ctrl+Shift+T → modo "exploração" (sem persistência).
        """
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        from app.postprocessor.ct_saturation_io import CTSelection
        from PySide6.QtWidgets import QMessageBox

        # Detecta TC selecionado no canvas (PpEditor scene)
        selection = self._get_selected_ct_for_saturation()

        if selection is None:
            # Sem TC selecionado: oferece modo didático (escape hatch)
            ans = QMessageBox.question(
                self,
                "Selecione um TC primeiro",
                "<b>Análise de Saturação de TC requer um TC selecionado.</b>"
                "<br><br>"
                "Para análise real:<br>"
                "1. Ative o <b>Modo Online</b> (Ctrl+Shift+O)<br>"
                "2. <b>Selecione um TC</b> no canvas<br>"
                "3. Volte aqui (Análise → Saturação de TC)<br><br>"
                "Deseja abrir o dialog em <b>modo didático</b> "
                "(defaults pré-populados, sem TC do projeto)?",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if ans != QMessageBox.Yes:
                return
            # Modo didático
            dlg = CTSaturationDialog(parent=self)
        else:
            # Modo real: passa selection ao dialog
            dlg = CTSaturationDialog(parent=self, selection=selection)
        dlg.exec()

    def _get_selected_ct_for_saturation(self):
        """
        v1.4.5: Retorna :class:`CTSelection` extraído do TC
        selecionado no canvas (PpEditor scene), ou None.

        Padrão alinhado com PTW Userguide §4 — análise gateada
        por seleção do componente.
        """
        try:
            from app.postprocessor.ct_saturation_io import CTSelection
            scene = self.schematic_pp.scene
        except (AttributeError, ImportError):
            return None
        for item in scene.selectedItems():
            comp = getattr(item, "component", None)
            if comp is not None and comp.type == "CT":
                try:
                    return CTSelection.from_pp_component(comp)
                except Exception:
                    return None
        return None

        # === Código legacy preservado para referência ===
        # === (não é mais executado a partir de v1.4.1) ===
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Saturação de TC — em desenvolvimento",
            "<h3>Análise de Saturação de TC (v0.93.0)</h3>"
            "<p>O módulo está implementado e disponível via "
            "API Python:</p>"
            "<pre style='background:#f0f0f0;padding:8px;'>"
            "from app.postprocessor.ct_saturation import (\n"
            "    CTSpec, CTFaultContext,\n"
            "    typical_magnetization_curve,\n"
            "    analyze_full,\n"
            ")\n\n"
            "fault = CTFaultContext(\n"
            "    bus_id='BUS-MAIN',\n"
            "    rated_voltage_kV=13.8,\n"
            "    I_fault_rms_kA=20.0,\n"
            "    X_over_R=10.0,\n"
            ")\n"
            "ct = CTSpec(\n"
            "    tag='CT-1',\n"
            "    tipo_TC='IEC_PR',\n"
            "    I_pri_nom_tap=2000,\n"
            "    I_pri_nom_full=2000,\n"
            "    I_sn=5,\n"
            "    CT_Rating_C=400.0,\n"
            "    R_s=0.5, R_b=0.3,\n"
            "    curve=typical_magnetization_curve(400.0),\n"
            "    Kr=0.1,\n"
            ")\n"
            "report = analyze_full(ct, fault)\n"
            "print(report.summary())</pre>"
            "<p>Cobertura: <b>IEEE C57.13.1-2017</b>, "
            "<b>IEC 61869-2:2012</b>, "
            "<b>CIGRÉ WG 23-15</b>.</p>"
            "<p><i>Dialog GUI completo: v0.93.1 (próximo).</i></p>"
        )

    # ------------------------------------------------------------------
    # v1.0.1 — Handlers para os módulos do roadmap v0.95→v1.0
    # ------------------------------------------------------------------

    def _on_analyze_cable_sizing(self, *_qt_args) -> None:
        """v1.0.1: dialog de dimensionamento de cabo (NBR 5410)."""
        from PySide6.QtWidgets import (
            QComboBox, QDialog, QDialogButtonBox,
            QDoubleSpinBox, QFormLayout, QLabel, QSpinBox,
        )
        from app.postprocessor.cable_sizing import (
            ConductorMaterial, Insulation, InstallationMethod,
            dimension_cable,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Dimensionamento de Cabo — NBR 5410")
        dlg.setMinimumWidth(420)
        form = QFormLayout(dlg)

        sb_I = QDoubleSpinBox()
        sb_I.setRange(1, 5000)
        sb_I.setValue(100)
        sb_I.setSuffix(" A")
        form.addRow("Corrente de carga:", sb_I)

        sb_V = QDoubleSpinBox()
        sb_V.setRange(100, 35000)
        sb_V.setValue(380)
        sb_V.setSuffix(" V")
        form.addRow("Tensão (V LL):", sb_V)

        sb_L = QDoubleSpinBox()
        sb_L.setRange(1, 5000)
        sb_L.setValue(50)
        sb_L.setSuffix(" m")
        form.addRow("Comprimento:", sb_L)

        cb_mat = QComboBox()
        cb_mat.addItems(["Cu", "Al"])
        form.addRow("Material:", cb_mat)

        cb_ins = QComboBox()
        cb_ins.addItems(["PVC", "EPR", "XLPE"])
        form.addRow("Isolação:", cb_ins)

        cb_inst = QComboBox()
        cb_inst.addItems(["B1", "A1"])
        form.addRow("Instalação:", cb_inst)

        sb_temp = QSpinBox()
        sb_temp.setRange(10, 60)
        sb_temp.setValue(30)
        sb_temp.setSuffix(" °C")
        form.addRow("Temperatura ambiente:", sb_temp)

        sb_circuits = QSpinBox()
        sb_circuits.setRange(1, 20)
        sb_circuits.setValue(1)
        form.addRow("Circuitos agrupados:", sb_circuits)

        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
        )
        bb.button(QDialogButtonBox.Ok).setText("▶ Dimensionar")
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)

        if dlg.exec() != QDialog.Accepted:
            return

        try:
            result = dimension_cable(
                load_current_A=sb_I.value(),
                rated_voltage_V=sb_V.value(),
                length_m=sb_L.value(),
                material=ConductorMaterial(cb_mat.currentText()),
                insulation=Insulation(cb_ins.currentText()),
                installation=InstallationMethod(cb_inst.currentText()),
                ambient_temp_C=float(sb_temp.value()),
                n_circuits=sb_circuits.value(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Inputs inválidos", str(exc))
            return

        from app.gui.analysis_dialogs import show_result_dialog
        show_result_dialog(
            self, "Dimensionamento de Cabo (NBR 5410)",
            result.summary(),
        )

    def _on_analyze_voltage_drop(self, *_qt_args) -> None:
        """v1.0.1: queda de tensão por bus."""
        pp_project = self._current_pp_project()
        if pp_project is None:
            QMessageBox.warning(
                self, "Sem projeto",
                "Carregue um projeto antes de analisar V-drop."
            )
            return
        from app.postprocessor.studies.voltage_drop import run
        result = run(pp_project)
        from app.gui.analysis_dialogs import show_result_dialog
        show_result_dialog(
            self, "Queda de Tensão por Bus (NBR 5410 §6.2.7)",
            result.summary(),
        )

    def _on_analyze_harmonics(self, *_qt_args) -> None:
        """v1.0.1: análise harmônicos com loads default (VFD)."""
        pp_project = self._current_pp_project()
        if pp_project is None:
            QMessageBox.warning(self, "Sem projeto", "Carregue um projeto.")
            return
        # v1.0.1 simplificado: aplica 1 VFD 6-pulse 500 kVA em
        # cada BUS encontrado. v1.0.2 adicionará dialog de
        # configuração de cargas não-lineares.
        from app.postprocessor.harmonics import (
            LoadType, NonLinearLoad, analyze_harmonics,
        )
        loads = [
            NonLinearLoad(
                bus_id=(c.get(0, "") or c.name),
                load_type=LoadType.VFD_6_PULSE,
                S_kVA=500.0,
            )
            for c in pp_project.components
            if c.type == "BUS"
        ]
        if not loads:
            QMessageBox.warning(
                self, "Sem buses",
                "Projeto sem componentes BUS para análise."
            )
            return
        result = analyze_harmonics(pp_project, loads)
        from app.gui.analysis_dialogs import show_result_dialog
        show_result_dialog(
            self, "Análise de Harmônicos (IEEE 519-2014)",
            result.summary(),
        )

    def _on_analyze_motor_reaccel(self, *_qt_args) -> None:
        """v1.0.1: simulação re-aceleração com motors do projeto."""
        pp_project = self._current_pp_project()
        if pp_project is None:
            QMessageBox.warning(self, "Sem projeto", "Carregue um projeto.")
            return
        from app.postprocessor.motor_reaccel import (
            MotorState, ReaccelScenario, simulate_reaccel,
        )
        # Coleta motors do projeto. v1.0.2 lerá as props
        # detalhadas; v1.0.1 usa defaults.
        motors = []
        for c in pp_project.components:
            if c.type == "MOTOR":
                motors.append(MotorState(
                    motor_id=c.name or f"M_{len(motors)}",
                    rated_power_kW=200.0,
                    rated_voltage_V=4160.0,
                ))
        if not motors:
            QMessageBox.warning(
                self, "Sem motores",
                "Projeto sem componentes MOTOR para análise."
            )
            return
        result = simulate_reaccel(motors)
        from app.gui.analysis_dialogs import show_result_dialog
        show_result_dialog(
            self, "Re-aceleração de Motor (IEEE 399 §10.5)",
            result.summary(),
        )

    def _on_analyze_ground_grid(self, *_qt_args) -> None:
        """v1.0.1: malha de aterramento com defaults editáveis."""
        from PySide6.QtWidgets import (
            QDialog, QDialogButtonBox, QDoubleSpinBox,
            QFormLayout, QSpinBox,
        )
        from app.postprocessor.ground_grid import (
            GroundGridSpec, analyze_ground_grid,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Malha de Aterramento — IEEE 80")
        form = QFormLayout(dlg)

        sb_area = QDoubleSpinBox()
        sb_area.setRange(50, 100000); sb_area.setValue(1000)
        sb_area.setSuffix(" m²")
        form.addRow("Área da malha:", sb_area)

        sb_L = QDoubleSpinBox()
        sb_L.setRange(50, 50000); sb_L.setValue(500)
        sb_L.setSuffix(" m")
        form.addRow("Comprimento total cond.:", sb_L)

        sb_rho = QDoubleSpinBox()
        sb_rho.setRange(10, 10000); sb_rho.setValue(100)
        sb_rho.setSuffix(" Ω·m")
        form.addRow("Resistividade do solo:", sb_rho)

        sb_If = QDoubleSpinBox()
        sb_If.setRange(0.1, 100); sb_If.setValue(10)
        sb_If.setSuffix(" kA")
        form.addRow("Corrente de falta:", sb_If)

        sb_t = QDoubleSpinBox()
        sb_t.setRange(0.05, 5.0); sb_t.setValue(0.5)
        sb_t.setSingleStep(0.1)
        sb_t.setSuffix(" s")
        form.addRow("Tempo de extinção:", sb_t)

        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
        )
        bb.button(QDialogButtonBox.Ok).setText("▶ Analisar")
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        if dlg.exec() != QDialog.Accepted:
            return

        spec = GroundGridSpec(
            area_m2=sb_area.value(),
            length_total_m=sb_L.value(),
            soil_resistivity_ohm_m=sb_rho.value(),
            fault_current_kA=sb_If.value(),
            fault_clearing_time_s=sb_t.value(),
        )
        result = analyze_ground_grid(spec)
        from app.gui.analysis_dialogs import show_result_dialog
        show_result_dialog(
            self, "Malha de Aterramento (IEEE 80)",
            result.summary(),
        )

    def _on_show_tcc_coordinogram(self, *_qt_args) -> None:
        """v1.0.2: abre coordenograma TCC interativo (estilo
        PTW CAPTOR) com curvas demo OU do projeto carregado."""
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        dlg = TCCCoordinogramDialog(parent=self)
        dlg.exec()

    def _on_show_ansi_sc_dialog(self, *_qt_args) -> None:
        """v3.1.0 Track B-1: abre ANSI Short Circuit Dialog (C37.5/C37.010).

        Backfill GUI sob 7ª garantia — expõe ao usuário todos os módulos
        backend de v3.0.2-v3.0.5 que estavam órfãos:

        * NACD ratio + 3 modes (ALL_REMOTE/PREDOMINANT/INTERPOLATED)
        * MF tables (Figs 1-1..1-15)
        * Asymmetrical Withstand (Phase A worst + average 3-φ)
        * Transformer tap (TAPS YES/NO)
        * Solution Method (E/Z vs E/X)
        * AnsiFaultReport export (TXT/MD/CSV)

        Reference: SKM PTW Reference-A_Fault.pdf §1.2-§1.4.
        Atalho: Ctrl+Shift+A.
        """
        from app.gui.ansi_sc_dialog import AnsiShortCircuitDialog
        dlg = AnsiShortCircuitDialog(parent=self)
        dlg.exec()

    def _on_show_pre_fault_voltage_dialog(self, *_qt_args) -> None:
        """v3.1.0 Track B-2: abre Pre-Fault Voltage Settings dialog.

        Backfill GUI para `app.postprocessor.pre_fault_voltage`:
        * 4 modos PreFaultMode (LOAD_FLOW/PU_ALL/PU_PER_BUS/NO_LOAD_WITH_TAP)
        * Tolerâncias Min/Reg/Max por equipamento (Util/Cable/TX)
        * Combined worst-case calculator

        Reference: PTW Tutorial §Part 5 p. 131-135.
        """
        from app.gui.pre_fault_voltage_dialog import PreFaultVoltageDialog
        dlg = PreFaultVoltageDialog(parent=self)
        dlg.exec()

    def _on_show_scenario_manager(self, *_qt_args) -> None:
        """v3.5.0: abre Scenario Manager Dialog (PTW Tutorial §Part 11 p.319-347).

        Cria/reusa ScenarioManager por sessão. Project ativo é Base scenario.
        """
        from app.gui.scenario_manager_dialog import ScenarioManagerDialog
        # Reusar manager existente se houver
        manager = getattr(self, "_scenario_manager", None)
        # Try to get current project from schematic_pp
        project = None
        try:
            if hasattr(self, "schematic_pp") and self.schematic_pp is not None:
                project = self.schematic_pp.scene.project
        except Exception:  # noqa: BLE001
            project = None
        dlg = ScenarioManagerDialog(
            parent=self, manager=manager, project=project,
        )
        dlg.exec()
        # Persist manager for next invocation
        self._scenario_manager = dlg.manager

    def _on_show_ansi_utilities(self, *_qt_args) -> None:
        """v3.1.0 Track B-3: abre ANSI Utilities dialog (3 utilitários).

        Backfill GUI para 3 módulos órfãos v3.0.3-v3.0.4:
        * Mis-coordination Detection (`mis_coordination`)
        * C37.5 ↔ C37.010 conversion (`solution_method`)
        * Transformer Tap + SLG vs 3-φ ratio (`transformer_tap`)
        """
        from app.gui.ansi_utilities_dialog import AnsiUtilitiesDialog
        dlg = AnsiUtilitiesDialog(parent=self)
        dlg.exec()

    def _on_show_fault_decay_dialog(self, *_qt_args) -> None:
        """v3.1.0 Track B-4: abre Fault Decay temporal dialog.

        Backfill GUI para `app.postprocessor.fault_decay`:
        * Generator/sync exponential decay (subtransient → steady)
        * Induction motor exclude rule (hp threshold + cycles)
        * Decay table with 10 time points

        Reference: PTW Tutorial §Part 5 p. 136-138.
        """
        from app.gui.fault_decay_dialog import FaultDecayDialog
        dlg = FaultDecayDialog(parent=self)
        dlg.exec()

    def _on_show_unbalanced_pf_dialog(self, *_qt_args) -> None:
        """v3.3.0 Sprint 1: abre Unbalanced Power Flow Dialog.

        Backfill 7ª garantia: módulo `app.postprocessor.power_flow_unbalanced`
        era órfão GUI antes de v3.3.0 (audit `v3.3.0_TIER1_AUDIT.md` §B.3).
        Reference: PTW Tutorial §Part 9 p.238-258.
        """
        from app.gui.unbalanced_pf_dialog import UnbalancedPowerFlowDialog
        # Pass current project if pp editor has one open
        project = None
        try:
            if hasattr(self, "schematic_pp") and self.schematic_pp is not None:
                project = self.schematic_pp.scene.project
        except Exception:  # noqa: BLE001
            project = None
        dlg = UnbalancedPowerFlowDialog(parent=self, project=project)
        dlg.exec()

    def _on_show_balanced_system_studies(self, *_qt_args) -> None:
        """v3.1.0 Track B-5: abre Balanced System Studies orquestrador.

        Permite ao usuário rodar DAPPER + LF + ANSI Comp SC em sequência
        num único click (estilo PTW Tutorial §Part 2 p. 63-64).
        """
        from app.gui.balanced_system_studies_dialog import (
            BalancedSystemStudiesDialog,
        )
        dlg = BalancedSystemStudiesDialog(parent=self)
        dlg.exec()

    # ------------------------------------------------------------------
    # v3.5.2 (closes SKIPPED_BACKLOG A.2) — Multi-document navigation
    # ------------------------------------------------------------------

    def register_document(self, name: str, widget) -> None:
        """Register a one-line document by name for Link Tag navigation.

        After registration, ``oneline:<name>`` Link Tags navigate to the
        widget's tab. Default: the main ``schematic_pp`` is registered
        as ``"Main"`` at MainWindow init.

        Reference: PTW Tutorial §Part 1 p.30-34.
        """
        self._documents_registry[name] = widget

    def unregister_document(self, name: str) -> None:
        """Remove a document from the registry."""
        self._documents_registry.pop(name, None)

    def list_documents(self) -> list[str]:
        """Return list of registered document names."""
        return sorted(self._documents_registry.keys())

    def navigate_to_document(self, name: str) -> bool:
        """Navigate to registered document. Returns True if found."""
        widget = self._documents_registry.get(name)
        if widget is None:
            return False
        # If widget is a tab page → switch tab
        if hasattr(self, "tabs") and self.tabs is not None:
            idx = self.tabs.indexOf(widget)
            if idx >= 0:
                self.tabs.setCurrentIndex(idx)
                return True
        # Otherwise just raise/show
        widget.show()
        widget.raise_()
        return True

    def _on_link_tag_navigate(self, target: str) -> None:
        """v3.1.3 Sub-sprint B: navega para o documento referenciado por
        Link Tag (PTW Tutorial §Part 1 p.35-42).

        Schemes suportados:
        * ``oneline:DocName`` — abre named one-line document (ainda
          single-document em v3.1.x; mostra status mensagem).
        * ``tcc:CoordName`` — abre TCC coordinogram (Ctrl+T equivalente).
        * ``report:RPT_Name`` — gera/abre relatório completo.
        * ``pdf:path/to/file.pdf`` — abre PDF externo via QDesktopServices.

        v3.1.3 implementa **roteamento básico**; navegação completa
        para multi-document é deferred v3.2.0+.
        """
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtWidgets import QMessageBox

        if ":" not in target:
            QMessageBox.warning(
                self, "Link Tag inválido",
                f"Target sem prefixo: {target!r}\n\n"
                "Formato esperado: oneline:Doc / tcc:Coord / report:RPT / pdf:path",
            )
            return

        scheme, _, payload = target.partition(":")
        scheme = scheme.lower().strip()
        payload = payload.strip()

        if scheme == "tcc":
            # TCC coordinogram (Ctrl+T existing handler)
            self._on_show_tcc_coordinogram()
            self.statusBar().showMessage(
                f"Link Tag → TCC: {payload}", 4000,
            )
        elif scheme == "report":
            # Trigger pipeline report export
            self._on_export_pipeline_report()
            self.statusBar().showMessage(
                f"Link Tag → Report: {payload}", 4000,
            )
        elif scheme == "pdf":
            # Open external PDF
            url = QUrl.fromLocalFile(payload)
            opened = QDesktopServices.openUrl(url)
            if not opened:
                QMessageBox.warning(
                    self, "PDF não abriu",
                    f"Não foi possível abrir:\n{payload}",
                )
            else:
                self.statusBar().showMessage(
                    f"Link Tag → PDF: {payload}", 4000,
                )
        elif scheme == "oneline":
            # v3.5.2 (closes SKIPPED_BACKLOG A.2) — registry-based nav.
            # See `register_document`/`navigate_to_document`. Reference:
            # PTW Tutorial §Part 1 p.30-34.
            ok = self.navigate_to_document(payload)
            if ok:
                self.statusBar().showMessage(
                    f"Link Tag → One-line: {payload}", 4000,
                )
            else:
                # Document not registered — show available list
                known = ", ".join(self.list_documents()) or "(nenhum)"
                QMessageBox.information(
                    self, "Documento não encontrado",
                    f"Document '{payload}' não está registrado.\n\n"
                    f"Documentos registrados: {known}\n\n"
                    "Use ``MainWindow.register_document(name, widget)`` "
                    "para adicionar novos one-line drawings.",
                )
        else:
            QMessageBox.information(
                self, "Link Tag scheme desconhecido",
                f"Scheme '{scheme}' ainda não implementado.\n\n"
                "Reference: PTW Tutorial §Part 1 p.35-42.",
            )

    def _on_show_reliability(self, *_qt_args) -> None:
        """v3.6.0: abre ReliabilityDialog (IEEE 1366-2012 indices).

        Per PTW Tutorial §Part 10 — calcula SAIFI/SAIDI/CAIDI/ASAI a
        partir de eventos de interrupção definidos pelo usuário.

        Acessibilidade: Master Protocol garantia 7ª (GUI obrigatória).
        """
        from app.gui.reliability_dialog import ReliabilityDialog
        dlg = ReliabilityDialog(parent=self)
        dlg.exec()

    def _on_show_equipment_eval(self, *_qt_args) -> None:
        """v1.3.1 G.1: abre Equipment Evaluation Dashboard
        (9 critérios IEEE 242 §15 + NBR 5410 §6.2.7).

        v3.3.1 Sub-sprint B: tenta auto-load EquipmentInstance da topologia
        do PpProject ativo (`build_equipment_from_project`) — fecha gap
        §C.3 do audit `v3.3.0_TIER1_AUDIT.md` (dialog usava só demo data).
        """
        from app.gui.equipment_eval_dialog import EquipmentEvalDialog
        dlg = EquipmentEvalDialog(parent=self)
        # v3.3.1: auto-load do projeto ativo
        try:
            if hasattr(self, "schematic_pp") and self.schematic_pp is not None:
                project = self.schematic_pp.scene.project
                if project and getattr(project, "components", []):
                    from app.postprocessor.equipment_eval import (
                        build_equipment_from_project,
                    )
                    extracted = build_equipment_from_project(project)
                    if extracted:
                        dlg.set_equipments(extracted)
        except Exception:  # noqa: BLE001
            # Falha silenciosa: dialog cai em demo data padrão
            pass
        dlg.exec()

    def _on_show_coord_rules_check(self, *_qt_args) -> None:
        """v1.3.1 G.2: abre Coord Rules dialog (Rule Engine
        aplicando NEC 110.10 + IEEE 242 + NBR a devices)."""
        from app.gui.coord_rules_dialog import CoordRulesDialog
        dlg = CoordRulesDialog(parent=self)
        dlg.exec()

    def _on_show_label_designer(self, *_qt_args) -> None:
        """v1.4.0: abre Custom Label Designer arc-flash
        (NFPA 70E / NBR 17227). Último P0 do roadmap PTW."""
        from app.gui.arc_flash_label_dialog import LabelDesignerDialog
        dlg = LabelDesignerDialog(parent=self)
        dlg.exec()

    def _on_show_equipment_library(self, *_qt_args) -> None:
        """v1.4.2: dialog completo com Apply workflow.

        Browse vendor library (5 vendors, 33 entries) +
        botão 'Aplicar ao dispositivo selecionado' que detecta
        componente selecionado no canvas e copia specs do
        datasheet para as properties.
        """
        from app.gui.equipment_library_dialog import (
            EquipmentLibraryDialog,
        )
        dlg = EquipmentLibraryDialog(main_window=self, parent=self)
        dlg.exec()
        return  # nunca chega ao código legacy abaixo

        # === Código legacy preservado para referência ===
        from PySide6.QtWidgets import (
            QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
            QListWidget, QListWidgetItem, QTabWidget,
            QTextEdit, QVBoxLayout,
        )
        from app.equipment import library

        dlg = QDialog(self)
        dlg.setWindowTitle(
            "📚 Biblioteca de Equipamentos — "
            "Olivas Power System Studio"
        )
        dlg.resize(900, 600)

        layout = QVBoxLayout(dlg)
        stats = library.stats()
        layout.addWidget(QLabel(
            f"<b>{stats['total']} equipamentos</b> de "
            f"<b>{len(library.list_vendors())} fabricantes</b> "
            f"({', '.join(library.list_vendors())})"
        ))

        tabs = QTabWidget()

        # Relés
        relays_w = QListWidget()
        for r in library.list_relays():
            item_text = (
                f"{r.model_id}  ·  {r.full_name}\n"
                f"    {r.application.value}  ·  "
                f"{r.voltage_class.value}  ·  "
                f"ANSI: {', '.join(r.ansi_devices[:6])}…  "
                f"{'IEC 61850' if r.iec_61850 else ''}"
            )
            relays_w.addItem(QListWidgetItem(item_text))
        tabs.addTab(relays_w, f"🛡️ Relés ({stats['relays']})")

        # Motores
        motors_w = QListWidget()
        for m in library.list_motors():
            motors_w.addItem(QListWidgetItem(
                f"{m.model_id}  ·  {m.full_name}\n"
                f"    {m.rated_power_kW} kW @ "
                f"{m.rated_voltage_V} V, "
                f"η={m.full_load_efficiency:.1%}, "
                f"{m.ie_class}"
            ))
        tabs.addTab(motors_w, f"⚙️ Motores ({stats['motors']})")

        # Transformadores
        trafos_w = QListWidget()
        for t in library.list_transformers():
            trafos_w.addItem(QListWidgetItem(
                f"{t.model_id}  ·  {t.full_name}\n"
                f"    {t.rated_S_kVA} kVA, "
                f"{t.primary_kV}/{t.secondary_kV} kV, "
                f"Z={t.impedance_pct}%, "
                f"X/R={t.x_over_r:.1f}"
            ))
        tabs.addTab(
            trafos_w, f"🔄 Transformadores ({stats['transformers']})",
        )

        # Disjuntores
        breakers_w = QListWidget()
        for b in library.list_breakers():
            breakers_w.addItem(QListWidgetItem(
                f"{b.model_id}  ·  {b.full_name}\n"
                f"    {b.rated_voltage_kV} kV, "
                f"{b.rated_current_A} A, "
                f"Iccs={b.breaking_capacity_kA} kA, "
                f"{b.arc_quenching}"
            ))
        tabs.addTab(
            breakers_w, f"🔌 Disjuntores ({stats['breakers']})",
        )

        layout.addWidget(tabs, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText("Fechar")
        bb.rejected.connect(dlg.reject)
        layout.addWidget(bb)
        dlg.exec()

    def _on_show_plugin_marketplace(self, *_qt_args) -> None:
        """
        v1.5.0: abre o Plugin Marketplace com 3 tabs (Instalados,
        Disponíveis, Configurações). Substitui o read-only dialog
        v1.0.2 (preservado em ``_on_show_plugins`` para legacy).
        """
        from app.gui.plugin_marketplace_dialog import (
            PluginMarketplaceDialog,
        )
        dlg = PluginMarketplaceDialog(parent=self)
        dlg.exec()

    def _on_locale_picker(self, *_qt_args) -> None:
        """
        v2.1.1: abre LocalePickerDialog para troca de idioma
        (Português / English / Español).

        Locale escolhido é persistido em QSettings e aplicado em
        diálogos novos imediatamente. Menus principais aplicam
        no próximo restart.
        """
        from app.gui.locale_picker_dialog import LocalePickerDialog
        dlg = LocalePickerDialog(parent=self)
        dlg.exec()

    def _on_show_plugins(self, *_qt_args) -> None:
        """v1.0.2 (legacy): lista read-only de plugins instalados.
        Preservado para backward compat — mas o Marketplace v1.5.0
        é a interface preferida (acesso via Ferramentas → 🧩 Plugin
        Marketplace)."""
        from PySide6.QtWidgets import (
            QDialog, QDialogButtonBox, QLabel, QListWidget,
            QListWidgetItem, QVBoxLayout,
        )
        from app.plugins import (
            discover_plugins, get_registered_studies,
            get_registered_equipment,
        )

        plugins = discover_plugins()
        studies = get_registered_studies()
        eq = get_registered_equipment()

        dlg = QDialog(self)
        dlg.setWindowTitle("🧩 Plugins — Olivas Power System Studio")
        dlg.resize(700, 500)
        layout = QVBoxLayout(dlg)

        layout.addWidget(QLabel(
            f"<b>{len(plugins)} plugins descobertos</b><br>"
            f"<small>"
            f"Estudos custom: {len(studies)}  ·  "
            f"Vendors registrados: {len(eq)}"
            f"</small>"
        ))

        if not plugins:
            layout.addWidget(QLabel(
                "<i>Nenhum plugin encontrado em "
                "<code>~/.olivas/plugins/</code> ou "
                "<code>./plugins/</code></i>"
            ))
            layout.addWidget(QLabel(
                "<small>Para criar um plugin, veja "
                "<code>app/plugins/__init__.py</code> "
                "para a API <code>@register_study</code> e "
                "<code>@register_equipment</code>.</small>"
            ))
        else:
            lw = QListWidget()
            for p in plugins:
                lw.addItem(QListWidgetItem(
                    f"{p.name} v{p.version}\n"
                    f"  Path: {p.module_path}\n"
                    f"  Estudos: {p.studies or '-'}\n"
                    f"  Vendors: {p.equipment_vendors or '-'}"
                ))
            layout.addWidget(lw, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.reject)
        layout.addWidget(bb)
        dlg.exec()

    def _on_generate_ai_laudo(self, *_qt_args) -> None:
        """v1.0.1: gera narrativa de laudo via IA (offline ou Claude)."""
        pp_project = self._current_pp_project()
        if pp_project is None:
            QMessageBox.warning(self, "Sem projeto", "Carregue um projeto.")
            return
        # Encontra um bus para gerar narrativa
        bus = None
        for c in pp_project.components:
            if c.type == "BUS":
                bus = c
                break
        if bus is None:
            QMessageBox.warning(
                self, "Sem BUS",
                "Adicione um componente BUS antes de gerar laudo."
            )
            return
        # Mock report (v1.0.1 simplificado — v1.0.2 puxa do
        # cache real de estudos)
        from dataclasses import dataclass

        @dataclass
        class _MockReport:
            bus_id: str
            rated_voltage_kV: float = 13.8
            Ik_pp_kA: float = 12.5
            ip_kA: float = 31.7
            kappa: float = 1.78
            incident_energy_cal_cm2: float = 8.4
            arc_flash_boundary_mm: float = 1240.0
            ppe_category: str = "2"

        report = _MockReport(
            bus_id=bus.get(0, "") or bus.name,
        )
        from app.llm.laudo_generator import generate_audit_narrative
        narrative = generate_audit_narrative(
            report, use_offline_template=True,
        )
        from app.gui.analysis_dialogs import show_result_dialog
        show_result_dialog(
            self, "Laudo gerado por IA — Preview",
            narrative.full_text(),
        )

    def _on_analyze_bus_pipeline(
        self, *_qt_args, project=None, bus_id: str = "",
    ) -> None:
        from app.gui.analysis_dialogs import run_bus_pipeline_analysis
        if project is None:
            project = self._current_pp_project()
        run_bus_pipeline_analysis(self, project=project, bus_id=bus_id)

    def _on_export_pipeline_report(self) -> None:
        from app.gui.analysis_dialogs import run_pipeline_report_export
        pp_project = self._current_pp_project()
        run_pipeline_report_export(self, project=pp_project)

    # ------------------------------------------------------------------
    # v0.33.0: Examples runner — exemplos executáveis das normas
    # ------------------------------------------------------------------

    def _on_show_howto(self) -> None:
        """v0.82: dialog F1 'Como executar?'"""
        from app.gui.howto_dialog import HowToDialog
        HowToDialog(self).exec()

    def _on_show_shortcuts(self) -> None:
        """v0.91: dialog '?' com atalhos do teclado."""
        from app.gui.shortcuts_dialog import ShortcutsDialog
        ShortcutsDialog(self).exec()

    def _on_show_about(self) -> None:
        """v0.82: dialog Sobre. v0.92.2: rebrand."""
        from app.core.version import VERSION
        QMessageBox.about(
            self, "Sobre Olivas Power System Studio",
            f"<h3>Olivas Power System Studio</h3>"
            f"<p><b>Versão {VERSION}</b></p>"
            "<p style='color:#5C4D3C;font-style:italic;'>"
            "Software profissional de análise elétrica — "
            "alternativa nacional a SKM PTW / ETAP / EasyPower.</p>"
            "<p>Análises especializadas:"
            "<ul>"
            "<li>Curto-circuito (IEC 60909-0:2016)</li>"
            "<li>Fluxo de potência (IEEE 399 / Stevenson)</li>"
            "<li>Coordenação e seletividade (IEEE 242)</li>"
            "<li>Energia incidente / Arc-flash (NBR 17227 / IEEE 1584)</li>"
            "<li>Balanço de carga (IEEE 141)</li>"
            "</ul></p>"
            "<p>Laudos auditáveis (ISO 9001 / NR-10) com "
            "rastreabilidade norma → resultado.</p>"
            "<p>Doutorado UFMG — Engenharia Elétrica.</p>"
            "<p><i>Pressione F1 para o guia 'Como executar?'.</i></p>",
        )

    def _on_run_analysis_dialog(self) -> None:
        """
        v0.82: handler do botão verde ▶ "Executar Análise"
        na toolbar do PpEditor. Abre RunAnalysisDialog.
        """
        from app.gui.run_analysis_dialog import RunAnalysisDialog

        # Pega projeto atual
        try:
            pp_project = self.schematic_pp.scene.to_project()
        except Exception as e:
            QMessageBox.warning(
                self, "Erro",
                f"Não foi possível ler esquemático:\n{e}",
            )
            return

        dlg = RunAnalysisDialog(pp_project=pp_project, parent=self)
        dlg.analysis_requested.connect(
            lambda kind, bus_id: self._dispatch_analysis(
                kind, bus_id, pp_project,
            ),
        )
        dlg.exec()

    def _dispatch_analysis(
        self, kind: str, bus_id: str, pp_project,
    ) -> None:
        """
        v0.94.0: dispatcher modular PTW-style.
        kind ∈ {sc, coord, arc_flash, pf, motor, ct_sat, pipeline}.

        Studies usam StudyCache compartilhado para auto-cachear
        pré-requisitos (Coord auto-roda SC; Arc-flash auto-roda
        SC + Coord se ainda não computados).
        """
        if hasattr(self, "_console_panel"):
            self._console_panel.append_info(
                f"Análise solicitada: kind={kind}, bus={bus_id!r}"
            )
        try:
            if kind == "pipeline":
                self._on_analyze_bus_pipeline(
                    project=pp_project, bus_id=bus_id,
                )
            elif kind == "sc":
                self._on_analyze_short_circuit_modular(
                    pp_project, bus_id,
                )
            elif kind == "coord":
                # v0.94.0 — Coord standalone (auto-roda SC)
                self._on_analyze_coordination_modular(
                    pp_project, bus_id,
                )
            elif kind == "arc_flash":
                # v0.94.0 — Arc-flash modular (auto-roda SC+Coord)
                self._on_analyze_arc_flash_modular(
                    pp_project, bus_id,
                )
            elif kind == "pf":
                self._on_analyze_power_flow(project=pp_project)
            elif kind == "motor":
                self._on_analyze_motor_starting(
                    project=pp_project, bus_id=bus_id,
                )
            elif kind == "ct_sat":
                self._on_analyze_ct_saturation()
            else:
                QMessageBox.warning(
                    self, "Tipo desconhecido",
                    f"Tipo de análise {kind!r} não suportado.",
                )
            # v1.7.5: após estudo bem-sucedido, refresh plot docks
            # abertos (Vis>Gráficos populam automaticamente). Anti-
            # perda: try/except defensivo — refresh nunca derruba
            # fluxo principal.
            try:
                from app.gui.plot_dock_refresh import (
                    refresh_open_plot_docks,
                )
                n = refresh_open_plot_docks(self)
                if n > 0 and hasattr(self, "_console_panel"):
                    self._console_panel.append_info(
                        f"v1.7.5: {n} plot dock(s) atualizado(s) "
                        f"automaticamente após análise."
                    )
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(
                self, "Erro na análise",
                f"Análise {kind!r} falhou:\n{e}",
            )
            if hasattr(self, "_console_panel"):
                self._console_panel.append_error(
                    f"Análise {kind!r}: {e}"
                )

    # --- v0.94.0 — Modular study handlers (PTW-style) ----------------

    def _study_cache(self):
        """v0.94.0: lazy StudyCache associado ao MainWindow.
        Vive enquanto o projeto estiver aberto. Reset via
        _reset_study_cache (em _on_close_case)."""
        from app.postprocessor.studies import StudyCache
        if not hasattr(self, "_studies_cache"):
            self._studies_cache = StudyCache()
        return self._studies_cache

    def _reset_study_cache(self) -> None:
        """v0.94.0: invalida todos os estudos (chamado ao
        fechar/abrir projeto OU ao salvar mudanças)."""
        if hasattr(self, "_studies_cache"):
            self._studies_cache.invalidate_all()

    def _refresh_plot_docks(self) -> None:
        """
        v1.7.2: re-popula docks de gráficos abertos a partir do
        study cache atual. Chamado após cada estudo (SC, Coord,
        Arc-Flash, etc) para que docks já visíveis atualizem
        automaticamente quando novos dados chegam.

        Endereça issue #3 do user gate v2.0.0 ("gráficos não
        populam"). Antes, populate_from_cache só rodava na criação
        do dock; agora também roda após cada estudo.

        Defensivo: ignora docks ausentes e exceptions individuais
        (anti-crash).
        """
        cache = getattr(self, "_studies_cache", None)
        if cache is None:
            return
        for attr in (
            "_plot_dock_pf_voltage",
            "_plot_dock_sc_pie",
            "_plot_dock_tcc_overlay",
            "_plot_dock_mc_hist",
        ):
            dock = getattr(self, attr, None)
            if dock is None:
                continue
            try:
                if hasattr(dock, "populate_from_cache"):
                    dock.populate_from_cache(cache)
            except Exception:
                # Anti-crash: cache vazio ou populate falha não
                # impede outros docks de atualizarem
                pass

    def _on_analyze_short_circuit_modular(
        self, pp_project, bus_id: str,
    ) -> None:
        """v0.94.0: SC modular usando o módulo studies.short_circuit.

        v1.1.0: chama ``_refresh_online_overlay()`` ao final para
        sincronizar o overlay Online se estiver ativo.
        """
        from app.postprocessor.studies import short_circuit
        cache = self._study_cache()
        result = short_circuit.run(
            pp_project, bus_id, cache=cache,
        )
        text = self._format_sc_result(result)
        from app.gui.analysis_dialogs import show_result_dialog
        show_result_dialog(
            self, f"Curto-circuito — {bus_id}", text,
        )
        # v1.1.0: refresh Online overlay (no-op se modo desligado)
        self._refresh_online_overlay()
        # v1.7.2: refresh plot docks abertos (issue #3 user gate v2.0.0)
        self._refresh_plot_docks()
        if hasattr(self, "_console_panel"):
            self._console_panel.append_info(
                f"SC OK: Ik''={result.Ik_pp_kA:.2f} kA "
                f"(cached={cache.has_sc(bus_id)})"
            )

    def _on_analyze_coordination_modular(
        self, pp_project, bus_id: str,
    ) -> None:
        """v0.94.0: Coordenação modular — auto-roda SC."""
        from app.postprocessor.studies import coordination
        cache = self._study_cache()
        result = coordination.run(
            pp_project, bus_id, cache=cache,
        )
        text = self._format_coord_result(result)
        from app.gui.analysis_dialogs import show_result_dialog
        show_result_dialog(
            self, f"Coordenação e Seletividade — {bus_id}", text,
        )
        # v1.7.2: refresh plot docks (issue #3 user gate v2.0.0)
        self._refresh_plot_docks()

    def _on_analyze_arc_flash_modular(
        self, pp_project, bus_id: str,
    ) -> None:
        """v0.94.0: Arc-flash modular — auto-roda SC + Coord."""
        from app.postprocessor.studies import arc_flash_study
        cache = self._study_cache()
        result = arc_flash_study.run(
            pp_project, bus_id, cache=cache,
        )
        text = self._format_arc_flash_result(result)
        from app.gui.analysis_dialogs import show_result_dialog
        show_result_dialog(
            self, f"Arc-Flash — {bus_id}", text,
        )
        # v1.7.2: refresh plot docks (issue #3 user gate v2.0.0)
        self._refresh_plot_docks()

    def _format_sc_result(self, r) -> str:
        return (
            f"=== Curto-Circuito (IEC 60909-0:2016) ===\n"
            f"Bus:        {r.bus_id} ({r.rated_voltage_kV:.2f} kV)\n"
            f"Ik''     :  {r.Ik_pp_kA:.3f} kA  (subtransitória)\n"
            f"ip       :  {r.ip_kA:.3f} kA   (peak assimétrico)\n"
            f"Ib       :  {r.Ib_kA:.3f} kA  (breaking)\n"
            f"Ik       :  {r.Ik_steady_kA:.3f} kA  (regime)\n"
            f"κ        :  {r.kappa:.4f}\n"
            f"R/X      :  {r.r_over_x:.4f}\n"
            f"c-factor :  {r.voltage_factor_c:.2f}\n"
            f"Z_thev   :  {r.z_thevenin_real_ohm:.4f} + "
            f"j{r.z_thevenin_imag_ohm:.4f} Ω\n"
            f"Sources  :  {r.n_sc_sources} ({', '.join(r.sources_summary[:2])}…)\n"
            f"Method   :  κ por {r.kappa_method_used}\n"
            + ("\n" + "\n".join(f"  ⚠ {w}" for w in r.warnings)
               if r.warnings else "")
        )

    def _format_coord_result(self, r) -> str:
        sugg_text = "\n".join(
            f"  • {s.relay_model_id} ({s.application}): "
            f"pickup={s.pickup_51_A:.0f}A, TMS={s.tms_51:.3f}"
            for s in r.relay_suggestions
        ) if r.relay_suggestions else "  (nenhuma sugestão gerada)"
        return (
            f"=== Coordenação e Seletividade (IEEE 242) ===\n"
            f"Bus:                       {r.bus_id}\n"
            f"Ik'' usado (do SC):       {r.sc_input_Ik_pp_kA:.3f} kA\n"
            f"Coord clearing time:       {r.coordination_clearing_time_ms:.0f} ms\n"
            f"Effective clearing:        {r.effective_clearing_time_ms:.0f} ms\n"
            f"AFD ativo:                 {'sim' if r.has_AFD else 'não'}\n"
            f"\n"
            f"Sugestões 50/51:\n{sugg_text}\n"
        )

    def _format_arc_flash_result(self, r) -> str:
        if r.status == "out_of_scope":
            return (
                f"=== Arc-Flash — {r.bus_id} ===\n"
                f"⚠ STATUS: out-of-scope\n"
                f"\n"
                f"Motivo: {r.out_of_scope_reason}\n"
                f"\n"
                f"Sistemas HV (>15 kV) não estão no escopo da NBR\n"
                f"17227 / IEEE 1584. SC e Coordenação são válidos\n"
                f"e foram cacheados para uso em laudo.\n"
                f"\n"
                f"Inputs (referência):\n"
                f"  Ibf (do SC):           {r.sc_input_Ibf_kA:.3f} kA\n"
                f"  Clearing (do Coord):   {r.coord_clearing_time_ms:.0f} ms\n"
            )
        return (
            f"=== Arc-Flash (NBR 17227 / IEEE 1584-2018) ===\n"
            f"Bus:                       {r.bus_id}\n"
            f"\n"
            f"Energia incidente:         {r.incident_energy_cal_cm2:.3f} cal/cm²\n"
            f"DLA (arc-flash boundary):  {r.arc_flash_boundary_mm:.0f} mm\n"
            f"PPE Category:              Cat {r.ppe_category}\n"
            f"\n"
            f"Inputs:\n"
            f"  Ibf (do SC cache):       {r.sc_input_Ibf_kA:.3f} kA\n"
            f"  Clearing (do Coord):     {r.coord_clearing_time_ms:.0f} ms\n"
        )

    def _on_run_example(self, example_id: str) -> None:
        """
        Roda um exemplo da norma e:

        v0.81: ALÉM do relatório modal, carrega o ESQUEMÁTICO
        .sch correspondente no PpEditor (tab "Esquemático
        Visual ★") para o usuário visualizar o sistema.

        Os exemplos são (Stevenson PF, Stevenson seq, IEC
        60909 Annex C, IEEE 1584, IEEE 399, NBR 17227).
        """
        from app.examples.registry import get_example_by_id
        from app.examples.schematics import schematic_path_for
        from app.gui.analysis_dialogs import show_result_dialog

        entry = get_example_by_id(example_id)
        if entry is None:
            QMessageBox.warning(
                self, "Exemplo desconhecido",
                f"Exemplo {example_id!r} não encontrado.",
            )
            return

        try:
            self.status.showMessage(f"Executando: {entry.label}...")
            QApplication.processEvents()

            # v0.81: carrega .sch no PpEditor PRIMEIRO
            sch_path = schematic_path_for(example_id)
            if sch_path is not None and sch_path.is_file():
                try:
                    pp_project = parse_sch_file(str(sch_path))
                    self.schematic_pp.scene.load_project(pp_project)
                    # Força tab para o editor visual
                    self.tabs.setCurrentWidget(self.schematic_pp)
                    if hasattr(self, "_console_panel"):
                        self._console_panel.append_info(
                            f"Esquemático carregado: {sch_path.name}"
                        )
                except Exception as sch_err:
                    if hasattr(self, "_console_panel"):
                        self._console_panel.append_warn(
                            f"Falha ao carregar .sch: {sch_err}"
                        )

            # Roda o cálculo
            result = entry.runner()
            text = result.summary()
            if hasattr(self, "_console_panel"):
                self._console_panel.append_info(
                    f"Exemplo executado: {entry.label} "
                    f"({'PASS' if result.passed else 'FAIL'})"
                )
            show_result_dialog(
                self,
                f"Exemplo: {entry.label}",
                text,
                width=900, height=700,
            )
            self.status.showMessage(
                f"{entry.label}: "
                f"{'OK' if result.passed else 'fora da tolerância'}",
                5000,
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Erro no exemplo",
                f"{entry.label} falhou:\n{e}",
            )
            self.status.showMessage(f"Erro: {e}")

    # ------------------------------------------------------------------
    # Diff
    # ------------------------------------------------------------------

    def _on_update_diff(self) -> None:
        if self.project is None:
            self.diff_text.setPlainText("Nenhum projeto aberto.")
            return

        self._commit_table_edits()
        content = serialize_project(self.project)
        original = "\n".join(self.project.raw_lines)

        if not has_changes(original, content):
            self.diff_text.setPlainText("Nenhuma alteração detectada.")
            return

        diff_lines = compute_context_diff(original, content)
        self.diff_text.setPlainText("\n".join(diff_lines))

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _on_validate(self) -> None:
        if self.project is None:
            return

        messages = validate_project(self.project)
        messages.extend(validate_physics(self.project))
        messages.extend(validate_vcb(self.project))
        self.val_list.clear()

        if not messages:
            item = QListWidgetItem("Nenhum problema encontrado.")
            self.val_list.addItem(item)
            self.status.showMessage("Validação: OK")
            return

        palette = get_palette(self.is_dark)
        for msg in messages:
            prefix = msg.severity.value
            text = f"[{prefix}] {msg.code}: {msg.message}"
            item = QListWidgetItem(text)
            if msg.severity == Severity.ERROR:
                item.setForeground(QColor(palette["val_error"]))
            elif msg.severity == Severity.WARNING:
                item.setForeground(QColor(palette["val_warning"]))
            elif msg.severity == Severity.INFO:
                item.setForeground(QColor(palette["val_info"]))
            self.val_list.addItem(item)

        errors = sum(1 for m in messages if m.severity == Severity.ERROR)
        warns = sum(1 for m in messages if m.severity == Severity.WARNING)
        self.status.showMessage(f"Validação: {errors} erro(s), {warns} aviso(s)")

    # ------------------------------------------------------------------
    # Tree
    # ------------------------------------------------------------------

    def _populate_tree(self) -> None:
        self.tree.clear()
        self._hide_use_tables()
        if self.project is None:
            return

        # Header
        h = QTreeWidgetItem(self.tree, ["Header"])
        h.setData(0, Qt.UserRole, ("header", None))

        # Models
        if self.project.models:
            mr = QTreeWidgetItem(self.tree, ["MODELS"])
            mr.setData(0, Qt.UserRole, ("models_root", None))
            for model in self.project.models:
                c = QTreeWidgetItem(mr, [f"MODEL {model.name}"])
                c.setData(0, Qt.UserRole, ("model", model))

        # Uses
        if self.project.uses:
            ur = QTreeWidgetItem(self.tree, ["USES"])
            ur.setData(0, Qt.UserRole, ("uses_root", None))
            for use in self.project.uses:
                c = QTreeWidgetItem(ur, [f"USE {use.model_name}"])
                c.setData(0, Qt.UserRole, ("use", use))

        # Sections with component counts and individual children
        sec_counts = {
            "BRANCH": len(self.project.branches),
            "SWITCH": len(self.project.switches),
            "SOURCE": len(self.project.sources),
        }
        for name in ("BRANCH", "SWITCH", "SOURCE", "OUTPUT"):
            if name not in self.project.sections:
                continue
            count = sec_counts.get(name, 0)
            label = f"{name} ({count})" if count else name
            s = QTreeWidgetItem(self.tree, [label])
            s.setData(0, Qt.UserRole, ("section", self.project.sections[name]))

            # Add individual components as children [GUI-011]
            if name == "BRANCH":
                for b in self.project.branches:
                    tag = f" [{b.semantic_type}]" if b.semantic_type else ""
                    clbl = f"{b.node1}–{b.node2}{tag}" if b.node2 else f"{b.node1}{tag}"
                    child = QTreeWidgetItem(s, [clbl])
                    child.setData(0, Qt.UserRole, ("branch_comp", b))
            elif name == "SWITCH":
                for sw in self.project.switches:
                    tag = f" [{sw.semantic_type}]" if sw.semantic_type else ""
                    clbl = f"{sw.node1}–{sw.node2}{tag}"
                    child = QTreeWidgetItem(s, [clbl])
                    child.setData(0, Qt.UserRole, ("switch_comp", sw))
            elif name == "SOURCE":
                for src in self.project.sources:
                    tag = f" [{src.semantic_type}]" if src.semantic_type else ""
                    child = QTreeWidgetItem(s, [f"{src.node}{tag}"])
                    child.setData(0, Qt.UserRole, ("source_comp", src))

        # Nodes
        if self.project.nodes:
            nr = QTreeWidgetItem(self.tree, [f"NODES ({len(self.project.nodes)})"])
            nr.setData(0, Qt.UserRole, ("nodes_root", None))

        self.tree.expandAll()

    # ------------------------------------------------------------------
    # Details panel
    # ------------------------------------------------------------------

    def _on_tree_selection(self, current: QTreeWidgetItem, _previous) -> None:
        if current is None:
            return
        data = current.data(0, Qt.UserRole)
        if data is None:
            return

        kind, obj = data
        self._hide_use_tables()

        if kind == "header":
            self._show_header_details()
        elif kind == "model":
            self._show_model_details(obj)
        elif kind == "use":
            self._show_use_details(obj)
        elif kind == "section":
            self._show_section_details(obj)
        elif kind == "models_root":
            self._show_models_global()
        elif kind == "uses_root":
            self._show_uses_summary()
        elif kind == "nodes_root":
            self._show_nodes_summary()
        elif kind == "branch_comp":
            self._show_branch_properties(obj)
        elif kind == "switch_comp":
            self._show_switch_properties(obj)
        elif kind == "source_comp":
            self._show_source_properties(obj)
        else:
            self.details_label.setText("Selecione um item.")

    def _show_header_details(self) -> None:
        h = self.project.header
        parts = ["HEADER DO CASO ATP", ""]
        if h.frequency is not None:
            parts.append(f"Frequência:  {h.frequency} Hz")
        if h.delta_t is not None:
            parts.append(f"Δt:          {h.delta_t} s")
        if h.t_max is not None:
            parts.append(f"Tmax:        {h.t_max} s")
        parts.append(f"Linhas:      {len(h.raw_lines)}")
        parts.append("")
        parts.append("Linhas brutas do header:")
        for line in h.raw_lines:
            parts.append(f"  {line}")
        self.details_label.setText("\n".join(parts))

    def _show_models_global(self) -> None:
        gio = self.project.models_global_io
        parts = [
            "MODELS — I/O GLOBAL",
            f"{'─' * 40}",
            f"Inputs globais: {len(gio.inputs)}",
        ]
        for inp in gio.inputs:
            parts.append(f"  {inp.local_name:<10} ← {inp.mapped_to}")
        parts.append(f"\nOutputs globais: {len(gio.outputs)}")
        for out in gio.outputs:
            parts.append(f"  {out}")
        self.details_label.setText("\n".join(parts))

    def _show_model_details(self, model: ModelDefinition) -> None:
        self._current_model = model

        parts = [
            f"MODEL: {model.name}",
            f"Linhas: {model.start_line + 1} – {model.end_line + 1}",
            f"{'─' * 40}",
        ]
        if model.comment:
            parts.append(f"\n{model.comment.strip()}\n")

        parts.append(f"INPUT ({len(model.inputs)}):")
        for i in model.inputs:
            parts.append(f"  {i}")

        parts.append(f"\nOUTPUT ({len(model.outputs)}):")
        for o in model.outputs:
            parts.append(f"  {o}")

        parts.append(f"\nVAR ({len(model.variables)}):")
        for v in model.variables:
            parts.append(f"  {v}")

        if model.init_code:
            parts.append(f"\nINIT:")
            for line in model.init_code.splitlines()[:10]:
                parts.append(f"  {line}")
            total = len(model.init_code.splitlines())
            if total > 10:
                parts.append(f"  ... (+{total - 10} linhas)")

        if model.exec_code:
            parts.append(f"\nEXEC:")
            for line in model.exec_code.splitlines()[:20]:
                parts.append(f"  {line}")
            total = len(model.exec_code.splitlines())
            if total > 20:
                parts.append(f"  ... (+{total - 20} linhas)")

        self.details_label.setText("\n".join(parts))

        # --- MODEL DATA table (editable defaults) [GUI-010] ---
        if model.data:
            self.model_data_table.blockSignals(True)
            self.model_data_table.setRowCount(len(model.data))
            for row, param in enumerate(model.data):
                name_item = QTableWidgetItem(param.name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self.model_data_table.setItem(row, 0, name_item)

                dflt_item = QTableWidgetItem(param.default_value or "")
                self.model_data_table.setItem(row, 1, dflt_item)
            self.model_data_table.blockSignals(False)

            try:
                self.model_data_table.cellChanged.disconnect()
            except RuntimeError:
                pass
            self.model_data_table.cellChanged.connect(self._on_model_data_cell_changed)
            self.model_data_group.show()

    def _show_use_details(self, use: UseInstance) -> None:
        self._current_use = use

        # Find matching MODEL for default values
        model = self.project.find_model(use.model_name)

        parts = [
            f"USE: {use.model_name} AS {use.instance_name}",
            f"Linhas: {use.start_line + 1} – {use.end_line + 1}",
        ]
        if model:
            parts.append(f"MODEL correspondente: {model.name}")
        else:
            parts.append("MODEL correspondente: NÃO ENCONTRADO")
        self.details_label.setText("\n".join(parts))

        # --- INPUT table ---
        self.input_table.blockSignals(True)
        self.input_table.setRowCount(len(use.inputs))
        for row, inp in enumerate(use.inputs):
            local_item = QTableWidgetItem(inp.local_name)
            mapped_item = QTableWidgetItem(inp.mapped_to)
            self.input_table.setItem(row, 0, local_item)
            self.input_table.setItem(row, 1, mapped_item)
        self.input_table.blockSignals(False)
        if use.inputs:
            self.input_group.show()

        # --- DATA table (editable values) ---
        defaults = {}
        if model:
            defaults = {d.name.upper(): d.default_value for d in model.data}

        self.data_table.blockSignals(True)
        self.data_table.setRowCount(len(use.data))
        for row, param in enumerate(use.data):
            name_item = QTableWidgetItem(param.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.data_table.setItem(row, 0, name_item)

            val_item = QTableWidgetItem(param.assigned_value or "")
            self.data_table.setItem(row, 1, val_item)

            dflt = defaults.get(param.name.upper(), "")
            dflt_item = QTableWidgetItem(dflt or "")
            dflt_item.setFlags(dflt_item.flags() & ~Qt.ItemIsEditable)
            dflt_item.setForeground(QColor(get_palette(self.is_dark)["fg_dim"]))
            self.data_table.setItem(row, 2, dflt_item)
        self.data_table.blockSignals(False)

        try:
            self.data_table.cellChanged.disconnect()
        except RuntimeError:
            pass
        self.data_table.cellChanged.connect(self._on_data_cell_changed)

        if use.data:
            self.data_group.show()

        # --- INPUT table editing ---
        try:
            self.input_table.cellChanged.disconnect()
        except RuntimeError:
            pass
        self.input_table.cellChanged.connect(self._on_input_cell_changed)

        # --- OUTPUT table ---
        self.output_table.blockSignals(True)
        self.output_table.setRowCount(len(use.outputs))
        for row, out in enumerate(use.outputs):
            global_item = QTableWidgetItem(out.global_name)
            local_item = QTableWidgetItem(out.local_name)
            self.output_table.setItem(row, 0, global_item)
            self.output_table.setItem(row, 1, local_item)
        self.output_table.blockSignals(False)

        try:
            self.output_table.cellChanged.disconnect()
        except RuntimeError:
            pass
        self.output_table.cellChanged.connect(self._on_output_cell_changed)

        if use.outputs:
            self.output_group.show()

    def _show_uses_summary(self) -> None:
        parts = ["USES — Resumo", f"{'─' * 40}", ""]
        for use in self.project.uses:
            model = self.project.find_model(use.model_name)
            status = "OK" if model else "MODEL NÃO ENCONTRADO"
            mod_flag = " [modificado]" if use.modified else ""
            parts.append(
                f"USE {use.model_name:<14} → {status}{mod_flag}"
            )
            parts.append(
                f"  {len(use.inputs)} input(s), "
                f"{len(use.data)} data, "
                f"{len(use.outputs)} output(s)"
            )
            parts.append("")
        self.details_label.setText("\n".join(parts))

    def _show_section_details(self, section: Section) -> None:
        parts = [
            f"Seção: /{section.name}",
            f"Linhas: {section.start_line + 1} – {section.end_line + 1}",
            f"Total: {len(section.raw_lines)} linhas",
            f"{'─' * 50}",
        ]

        # Show parsed components
        if section.name == "BRANCH" and self.project.branches:
            parts.append(f"\nComponentes parseados: {len(self.project.branches)}")
            parts.append(f"{'─' * 50}")
            parts.append(f"{'Tipo':<5} {'Nó 1':<8} {'Nó 2':<8} {'R':>10} {'L':>10} {'C':>10}")
            for b in self.project.branches[:40]:
                r = b.resistance or ""
                l = b.inductance or ""
                c = b.capacitance or ""
                parts.append(f"{b.type_code:<5} {b.node1:<8} {b.node2:<8} {r:>10} {l:>10} {c:>10}")
            if len(self.project.branches) > 40:
                parts.append(f"... (+{len(self.project.branches) - 40} componentes)")

        elif section.name == "SWITCH" and self.project.switches:
            parts.append(f"\nComponentes parseados: {len(self.project.switches)}")
            parts.append(f"{'─' * 50}")
            parts.append(f"{'Tipo':<5} {'Nó 1':<8} {'Nó 2':<8} {'Tipo SW':<12} {'TACS Out'}")
            for s in self.project.switches:
                parts.append(f"{s.type_code:<5} {s.node1:<8} {s.node2:<8} {s.switch_type:<12} {s.tacs_output}")

        elif section.name == "SOURCE" and self.project.sources:
            parts.append(f"\nComponentes parseados: {len(self.project.sources)}")
            parts.append(f"{'─' * 50}")
            parts.append(f"{'Tipo':<5} {'Nó':<8} {'Amplitude':>12} {'Freq':>8} {'Fase':>8}")
            for s in self.project.sources:
                amp = s.amplitude or ""
                freq = s.frequency or ""
                phase = s.phase or ""
                parts.append(f"{s.type_code:<5} {s.node:<8} {amp:>12} {freq:>8} {phase:>8}")

        else:
            parts.append("")
            limit = 50
            for line in section.raw_lines[:limit]:
                parts.append(line)
            if len(section.raw_lines) > limit:
                parts.append(f"\n... (+{len(section.raw_lines) - limit} linhas restantes)")

        self.details_label.setText("\n".join(parts))

    def _show_nodes_summary(self) -> None:
        nodes = self.project.nodes
        parts = [
            f"NODES — {len(nodes)} nós identificados",
            f"{'─' * 50}",
            "",
            f"{'Nó':<10} {'Origem'}",
            f"{'─' * 50}",
        ]
        for name, node in nodes.items():
            sources = ", ".join(node.sources)
            parts.append(f"{name:<10} {sources}")
        self.details_label.setText("\n".join(parts))

    # ------------------------------------------------------------------
    # Component properties [GUI-011]
    # ------------------------------------------------------------------

    def _show_branch_properties(self, b: BranchComponent) -> None:
        parts = [
            f"BRANCH: {b.node1} – {b.node2}",
            f"{'─' * 40}",
            f"Classificação: {b.semantic_type or '—'}",
            f"Tipo código:  {b.type_code or '—'}",
            f"Nó 1:         {b.node1}",
            f"Nó 2:         {b.node2}",
            f"Ref 1:        {b.ref1 or '—'}",
            f"Ref 2:        {b.ref2 or '—'}",
            f"Resistência:  {b.resistance or '—'}",
            f"Indutância:   {b.inductance or '—'}",
            f"Capacitância: {b.capacitance or '—'}",
            f"Linha:        {b.line_number + 1}",
            f"{'─' * 40}",
            f"Raw: {b.raw_line}",
        ]
        self.details_label.setText("\n".join(parts))

    def _show_switch_properties(self, sw: SwitchComponent) -> None:
        parts = [
            f"SWITCH: {sw.node1} – {sw.node2}",
            f"{'─' * 40}",
            f"Classificação: {sw.semantic_type or '—'}",
            f"Tipo código:  {sw.type_code or '—'}",
            f"Nó 1:         {sw.node1}",
            f"Nó 2:         {sw.node2}",
            f"T close:      {sw.t_close or '—'}",
            f"T open:       {sw.t_open or '—'}",
            f"Ie:           {sw.ie or '—'}",
            f"Tipo switch:  {sw.switch_type or '—'}",
            f"TACS output:  {sw.tacs_output or '—'}",
            f"Linha:        {sw.line_number + 1}",
            f"{'─' * 40}",
            f"Raw: {sw.raw_line}",
        ]
        self.details_label.setText("\n".join(parts))

    def _show_source_properties(self, src: SourceComponent) -> None:
        parts = [
            f"SOURCE: {src.node}",
            f"{'─' * 40}",
            f"Classificação: {src.semantic_type or '—'}",
            f"Tipo código:  {src.type_code or '—'}",
            f"Nó:           {src.node}",
            f"Amplitude:    {src.amplitude or '—'}",
            f"Frequência:   {src.frequency or '—'}",
            f"Fase:         {src.phase or '—'}",
            f"T start:      {src.t_start or '—'}",
            f"T stop:       {src.t_stop or '—'}",
            f"Linha:        {src.line_number + 1}",
            f"{'─' * 40}",
            f"Raw: {src.raw_line}",
        ]
        self.details_label.setText("\n".join(parts))

    # ------------------------------------------------------------------
    # Editing callbacks
    # ------------------------------------------------------------------

    def _on_model_data_cell_changed(self, row: int, col: int) -> None:
        model = self._current_model
        if model is None or col != 1 or row >= len(model.data):
            return
        new_value = self.model_data_table.item(row, 1).text().strip()
        model.data[row].default_value = new_value
        # v0.28.2-PRO Onda 2.5 followup: marca caso modificado
        if self._active_case:
            self._mark_modified(self._active_case)
        self.status.showMessage(
            f"MODEL DATA editado: {model.data[row].name} default={new_value}  (MODEL {model.name})"
        )

    def _on_data_cell_changed(self, row: int, col: int) -> None:
        use = self._current_use
        if use is None or col != 1 or row >= len(use.data):
            return
        new_value = self.data_table.item(row, 1).text().strip()
        # v0.28.3-PRO Onda 3.3: registra no QUndoStack
        # Skip self-edit loop (apenas se diferente)
        old_value = use.data[row].assigned_value
        if new_value == old_value:
            return
        from app.gui.undo_commands import CellEditCommand

        d = use.data[row]

        def _set(v):
            d.assigned_value = v
            # Re-renderiza célula (ignora signals re-entrantes)
            self.data_table.blockSignals(True)
            self.data_table.item(row, 1).setText(str(v))
            self.data_table.blockSignals(False)

        def _on_change():
            use.modified = True
            if self._active_case:
                self._mark_modified(self._active_case)

        cmd = CellEditCommand(
            description=f"Editar {d.name}",
            getter=lambda: old_value,
            setter=_set,
            new_value=new_value,
            on_change=_on_change,
        )
        self._undo_stack.push(cmd)
        self.status.showMessage(
            f"DATA editado: {d.name} = {new_value}  (USE {use.model_name})"
        )

    def _on_input_cell_changed(self, row: int, col: int) -> None:
        use = self._current_use
        if use is None or row >= len(use.inputs):
            return
        if col == 0:
            use.inputs[row].local_name = self.input_table.item(row, 0).text().strip()
        elif col == 1:
            use.inputs[row].mapped_to = self.input_table.item(row, 1).text().strip()
        use.modified = True
        # v0.28.2-PRO Onda 2.5 followup: marca caso modificado
        if self._active_case:
            self._mark_modified(self._active_case)
        self.status.showMessage(
            f"INPUT editado: {use.inputs[row].local_name} := {use.inputs[row].mapped_to}  (USE {use.model_name})"
        )

    def _on_output_cell_changed(self, row: int, col: int) -> None:
        use = self._current_use
        if use is None or row >= len(use.outputs):
            return
        if col == 0:
            use.outputs[row].global_name = self.output_table.item(row, 0).text().strip()
        elif col == 1:
            use.outputs[row].local_name = self.output_table.item(row, 1).text().strip()
        use.modified = True
        # v0.28.2-PRO Onda 2.5 followup: marca caso modificado
        if self._active_case:
            self._mark_modified(self._active_case)
        self.status.showMessage(
            f"OUTPUT editado: {use.outputs[row].global_name} := {use.outputs[row].local_name}  (USE {use.model_name})"
        )

    def _commit_table_edits(self) -> None:
        # Commit MODEL DATA edits
        model = self._current_model
        if model is not None:
            for row in range(self.model_data_table.rowCount()):
                val_item = self.model_data_table.item(row, 1)
                if val_item and row < len(model.data):
                    model.data[row].default_value = val_item.text().strip()

        # Commit USE edits
        use = self._current_use
        if use is None:
            return
        for row in range(self.data_table.rowCount()):
            val_item = self.data_table.item(row, 1)
            if val_item and row < len(use.data):
                use.data[row].assigned_value = val_item.text().strip()
        for row in range(self.input_table.rowCount()):
            if row < len(use.inputs):
                it0 = self.input_table.item(row, 0)
                it1 = self.input_table.item(row, 1)
                if it0:
                    use.inputs[row].local_name = it0.text().strip()
                if it1:
                    use.inputs[row].mapped_to = it1.text().strip()
        for row in range(self.output_table.rowCount()):
            if row < len(use.outputs):
                it0 = self.output_table.item(row, 0)
                it1 = self.output_table.item(row, 1)
                if it0:
                    use.outputs[row].global_name = it0.text().strip()
                if it1:
                    use.outputs[row].local_name = it1.text().strip()
