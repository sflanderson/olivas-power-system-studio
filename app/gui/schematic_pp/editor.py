"""
app.gui.schematic_pp.editor — top-level widget do editor
visual do pré-processador.

Combina três áreas:

+----------+------------------------------+----------------+
| Palette  | Canvas (PpView + PpScene)    | Properties     |
| (left)   |                              | (right)        |
+----------+------------------------------+----------------+

API pública mínima:

* :class:`PpEditor` — ``QWidget`` que você pode jogar num
  ``QMainWindow`` ou num ``QTabWidget``.
* :meth:`PpEditor.load_from_sch` / :meth:`PpEditor.save_to_sch`
  — I/O com o formato Qucs .sch.
* :meth:`PpEditor.export_to_atp` — gera ``AtpProject`` via
  :func:`app.preprocessor.bridge_to_atp.to_atp`.
* :meth:`PpEditor.add_component_by_type` — helper para placement
  programático (usado em testes).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QMimeData, QPointF, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QDrag,
    QIcon,
    QKeySequence,
    QPainter,
    QPixmap,
    QShortcut,
    QUndoStack,
)
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.core.project_model import AtpProject
from app.preprocessor import catalog
from app.preprocessor.bridge_to_atp import to_atp
from app.preprocessor.models import PpComponent, PpProject, PpProperty, PpWire
from app.preprocessor.qucs_sch_parser import parse_sch_file
from app.preprocessor.qucs_sch_serializer import serialize_sch_file
from app.preprocessor.symbols import get_renderer

from . import commands as cmd
from .items import ComponentItem, WireItem
from .scene import PpScene, snap
from .view import PpView


_PP_MIME_TYPE = "application/x-atp-studio-pp-type"


# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------


class PpPalette(QListWidget):
    """
    Lista de tipos de componente agrupados por categoria.
    Clicar no item e apertar "Add" (ou duplo clique) coloca o
    componente no centro da view. Também suporta drag-and-drop:
    arraste um item para o canvas e solte — o :class:`PpView`
    pega o type_code via mime-type ``application/x-atp-studio-pp-type``.

    v0.91: ``filter_text(text)`` esconde itens que não contêm o
    texto (case-insensitive) no código ou label. Headers de
    categoria sumem se nenhum item da seção bate com o filtro.
    """

    #: emitido quando o usuário pede adicionar o tipo selecionado.
    request_add = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.CopyAction)
        self._populate()
        self.itemDoubleClicked.connect(self._on_double_clicked)

    # v1.0.1: ordem de display da paleta — mais usados em
    # protection / análise NBR no topo, depois ATP/transitórios
    # no fim. Antes (v0.91) usava ordem alfabética de categoria.
    _CATEGORY_ORDER: tuple[str, ...] = (
        "passive",      # R, L, C, BUS, GND, CABLE
        "source",       # Vac, Vdc, Iac, Idc
        "machine",      # MOTOR, SM
        "coupled",      # Tr, Tr3, sTr, XFMR, MUT
        "switch",       # Relais, CT, VCB, SwIdeal, SwTACS
        "line",         # BERG, JMARTI, TLIN
        "meter",        # IProbe, VProbe
        "nonlinear",    # RNL, LNL, ZnO
        "power_el",     # Diode, GTO, IGBT, MOSFET, Thyr
        "control",      # Eqn, Integrator, PID, etc.
        "sim",          # .AC, .DC, .SP, .SW, .TR
    )

    # Display labels em PT-BR para cada categoria
    _CATEGORY_LABELS: dict[str, str] = {
        "passive":   "🔧 Passivos (R, L, C, BUS, Cabo, GND)",
        "source":    "⚡ Fontes (Vac, Vdc, Iac, Idc)",
        "machine":   "⚙️ Máquinas (Motor, Síncrono)",
        "coupled":   "🔄 Transformadores (Tr, sTr, XFMR)",
        "switch":    "🛡️ Proteção (Relé, TC, Disjuntor)",
        "line":      "📏 Linhas de transmissão",
        "meter":     "📊 Medidores (V, I)",
        "nonlinear": "📈 Não-linear (RNL, ZnO)",
        "power_el":  "⚡ Eletrônica de potência",
        "control":   "🎛️ Controle (TACS)",
        "sim":       "▶️ Diretivas de simulação",
    }

    def _populate(self) -> None:
        # v1.0.1: ordena por _CATEGORY_ORDER (passivo no topo)
        # e mostra TODOS os componentes do catálogo (ATP-supported
        # e não-supported como CABLE, CT — usados só em análise).
        # v1.1.0: filtra items sem SymbolRenderer (Eqn TACS block +
        # diretivas .TR/.DC/.SW/.AC/.SP) — eles não são arrastáveis
        # pois não têm visual e não fazem sentido na paleta.
        from app.preprocessor.symbols import get_renderer
        all_entries = [
            e for e in catalog.all_entries()
            if get_renderer(e.code) is not None
        ]
        by_cat: dict[str, list] = {}
        for entry in all_entries:
            by_cat.setdefault(entry.category, []).append(entry)

        for cat in self._CATEGORY_ORDER:
            if cat not in by_cat:
                continue
            entries = sorted(by_cat[cat], key=lambda e: e.code)
            label = self._CATEGORY_LABELS.get(cat, f"── {cat} ──")
            header = QListWidgetItem(label)
            header.setFlags(Qt.NoItemFlags)
            self.addItem(header)
            for entry in entries:
                # v1.0.1: badge "(análise)" para componentes
                # não-ATP — sinaliza que servem só em estudos
                # (não em simulação ATP).
                if not entry.atp_supported:
                    item_label = (
                        f"  {entry.code}  ·  {entry.label_pt}  "
                        f"(análise)"
                    )
                else:
                    item_label = (
                        f"  {entry.code}  ·  {entry.label_pt}"
                    )
                it = QListWidgetItem(item_label)
                it.setData(Qt.UserRole, entry.code)
                self.addItem(it)

        # Se houver categorias não listadas em _CATEGORY_ORDER,
        # adiciona ao final (defensivo)
        listed = set(self._CATEGORY_ORDER)
        for cat in sorted(by_cat.keys()):
            if cat in listed:
                continue
            entries = sorted(by_cat[cat], key=lambda e: e.code)
            label = self._CATEGORY_LABELS.get(cat, f"── {cat} ──")
            header = QListWidgetItem(label)
            header.setFlags(Qt.NoItemFlags)
            self.addItem(header)
            for entry in entries:
                item_label = f"  {entry.code}  ·  {entry.label_pt}"
                it = QListWidgetItem(item_label)
                it.setData(Qt.UserRole, entry.code)
                self.addItem(it)

    def _on_double_clicked(self, item: QListWidgetItem) -> None:
        code = item.data(Qt.UserRole)
        if code:
            self.request_add.emit(str(code))

    # ---- Filter (v0.91) -----------------------------------------------------

    def filter_text(self, text: str) -> int:
        """
        v0.91: aplica filtro case-insensitive. Retorna # de itens
        de componente visíveis (excluindo headers).

        * Texto vazio → mostra tudo.
        * Match no label (code + label_pt) → mostra item.
        * Header de categoria fica visível APENAS se algum item
          da seção match o filtro (ou se o filtro é vazio).
        """
        text_norm = text.strip().lower()
        n_items_visible = 0
        # Primeira passada: mostra/oculta items, conta visíveis
        # por header. Como Qt não nos dá acesso a "items entre
        # headers" diretamente, fazemos uma passada linear
        # acumulando.
        groups: list[list[QListWidgetItem]] = []
        current: list[QListWidgetItem] = []
        for i in range(self.count()):
            it = self.item(i)
            data = it.data(Qt.UserRole)
            is_header = data is None
            if is_header:
                if current:
                    groups.append(current)
                current = [it]    # primeiro item do grupo = header
            else:
                current.append(it)
        if current:
            groups.append(current)

        for group in groups:
            header = group[0]
            items = group[1:]
            any_match = False
            for it in items:
                if text_norm == "":
                    matches = True
                else:
                    label = it.text().lower()
                    matches = text_norm in label
                it.setHidden(not matches)
                if matches:
                    any_match = True
                    n_items_visible += 1
            # Header fica visível se algum item bate ou se filtro vazio
            header.setHidden(not (any_match or text_norm == ""))
        return n_items_visible

    # ---- Drag start (QMimeData) -----------------------------------------

    def startDrag(self, supportedActions) -> None:  # pragma: no cover
        items = self.selectedItems()
        if not items:
            return
        code = items[0].data(Qt.UserRole)
        if not code:
            return
        self.build_drag(str(code)).exec(supportedActions)

    def build_drag(self, code: str) -> QDrag:
        """
        Cria o :class:`QDrag` para o ``code`` fornecido.

        Separado do :meth:`startDrag` para permitir teste sem
        loop de eventos (basta instanciar e chamar
        :meth:`QDrag.mimeData` / ``pixmap``).

        O :class:`QDrag` recebe um :class:`QPixmap` de preview
        renderizado pelo :class:`SymbolRenderer` do ``code`` (o
        mesmo usado no canvas). Assim o cursor durante o drag
        mostra o símbolo de fato — não um pseudo-genérico do Qt.
        """
        mime = QMimeData()
        mime.setData(_PP_MIME_TYPE, code.encode("utf-8"))
        # Também inclui texto plano para debug.
        mime.setText(code)
        drag = QDrag(self)
        drag.setMimeData(mime)
        pm = _render_drag_preview(code)
        if pm is not None:
            drag.setPixmap(pm)
            drag.setHotSpot(pm.rect().center())
        return drag


# ---------------------------------------------------------------------------
# Propriedades
# ---------------------------------------------------------------------------


class PpPropertiesPanel(QScrollArea):
    """
    Formulário contextual: mostra nome/tipo/rotação e lista de
    properties do componente selecionado (um por vez).
    """

    #: emitido quando o usuário edita um campo; o editor é esperado
    #: chamar :meth:`PpScene.update` e sincronizar.
    value_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self._placeholder_text = "Nada selecionado"
        self._current: Optional[ComponentItem] = None
        # Opcional: quando setado via set_command_sink, os handlers
        # de edição delegam ao editor (que empilha QUndoCommands)
        # em vez de mutar PpComponent diretamente.
        self._command_sink = None
        self._build_empty()

    def set_command_sink(self, sink) -> None:
        """
        Conecta o panel a um *sink* de comandos. O sink deve
        expor ``push_edit_property(comp, index, value)`` e
        ``push_edit_name(comp, new_name)``. Normalmente é o
        próprio :class:`PpEditor`.
        """
        self._command_sink = sink

    def _build_empty(self) -> None:
        w = QWidget(self)
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel(self._placeholder_text))
        lay.addStretch(1)
        self.setWidget(w)

    def bind_component(self, item: Optional[ComponentItem]) -> None:
        """
        Popula o painel com as propriedades do componente selecionado.

        v0.22.2: Se o componente tem ``.ocomp`` no registry, usa o painel
        rico (widget por tipo, agrupamento por PropertyGroup, unit inline,
        tooltip, visible checkbox, botão restaurar). Caso contrário, cai
        no fallback ``QLineEdit``-por-slot da v0.21.x.
        """
        self._current = item
        if item is None:
            self._build_empty()
            return

        # Local import: property_editor depende de .ocomp registry, e
        # propperty_editor pode importar coisas de editor.py no futuro —
        # mantém o import local para evitar ciclos.
        from app.gui.schematic_pp.property_editor import (
            ComponentPropertyDialog,
            PropertyGroupBox,
            build_property_rows,
            resolve_spec,
        )
        from app.preprocessor.spec import PropertyGroup

        c = item.component
        spec = resolve_spec(c.type)

        w = QWidget(self)
        root = QVBoxLayout(w)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── Identificação ─────────────────────────────────────────
        id_box = QGroupBox("Identificação", w)
        id_form = QFormLayout(id_box)
        name_edit = QLineEdit(c.name, id_box)
        name_edit.editingFinished.connect(
            lambda: self._on_name_changed(name_edit.text())
        )
        id_form.addRow("Nome:", name_edit)
        label_pt = spec.label_pt if spec is not None else c.type
        id_form.addRow("Tipo:", QLabel(f"{c.type} — {label_pt}"))
        id_form.addRow("Rotação:", QLabel(f"{c.rotation * 90}°"))
        id_form.addRow("Espelho:", QLabel("sim" if c.mirror else "não"))
        id_form.addRow("Posição:", QLabel(f"({c.x}, {c.y})"))
        root.addWidget(id_box)

        # ── Propriedades ──────────────────────────────────────────
        if spec is not None and spec.properties:
            # Painel rico baseado no .ocomp schema
            rows_by_group = build_property_rows(spec, c, parent=w)
            for group in PropertyGroup:
                if group not in rows_by_group:
                    continue
                box = PropertyGroupBox(group, rows_by_group[group], parent=w)
                box.row_changed.connect(self._on_row_changed)
                root.addWidget(box)

            # Botão "Editar em dialog…" — abre modal ATPDraw-style
            edit_dlg_btn = QPushButton("Editar em dialog…", w)
            edit_dlg_btn.setToolTip(
                "Abrir diálogo modal com abas (Parâmetros / Descrição) "
                "— útil para componentes com muitos parâmetros."
            )
            edit_dlg_btn.clicked.connect(
                lambda: self._open_modal_dialog(item)
            )
            root.addWidget(edit_dlg_btn)

        elif c.properties:
            # Fallback legacy: QLineEdit por slot (componentes sem .ocomp)
            props_box = QGroupBox("Propriedades", w)
            props_form = QFormLayout(props_box)
            labels = catalog.property_labels(c.type)
            for idx, p in enumerate(c.properties):
                edit = QLineEdit(p.value, props_box)
                edit.editingFinished.connect(
                    lambda i=idx, e=edit: self._on_prop_changed(i, e.text())
                )
                if idx < len(labels):
                    label_text = f"{labels[idx]}:"
                else:
                    label_text = f"#{idx + 1}:"
                props_form.addRow(label_text, edit)
            root.addWidget(props_box)

        root.addStretch(1)
        self.setWidget(w)

    def _open_modal_dialog(self, item: ComponentItem) -> None:
        """Abre o dialog modal rico (ATPDraw-style) para edição focada.

        v3.2.0: dialog agora é multi-tab (uma tab por PropertyGroup) +
        tab "📊 Datablocks" se o componente tem datablocks anexados.
        """
        from app.gui.schematic_pp.property_editor import (
            ComponentPropertyDialog, resolve_spec,
        )
        spec = resolve_spec(item.component.type)
        if spec is None:
            return  # componente sem .ocomp; dialog não suportado
        dlg = ComponentPropertyDialog(spec, item.component, self)
        dlg.property_changed.connect(self._on_row_changed)
        # v3.2.0 Sprint 3: anexar tab Datablocks se houver
        # datablocks no project apontando para este componente.
        attached_dbs = self._datablocks_for_component(item)
        if attached_dbs:
            dlg.attach_datablock_tab(attached_dbs)
        dlg.exec()
        # Refresh do painel lateral para refletir mudanças
        self.bind_component(item)

    def _datablocks_for_component(self, item: "ComponentItem") -> list:
        """v3.2.0: return list of PpDataBlock attached to ``item``.

        Datablocks são child-items do ComponentItem na cena (anchored).
        Esta função retorna os PpDataBlock cujo host é este componente
        no project model. Accesso via ``self._command_sink`` (que é
        o PpEditor) para chegar ao scene/project.
        """
        if self._command_sink is None:
            return []
        try:
            scene = self._command_sink.scene
            target_name = item.component.name
            return [
                db for db in scene.project.datablocks
                if db.component_name == target_name
            ]
        except Exception:  # noqa: BLE001
            return []

    # ---- callbacks --------------------------------------------------------

    def _on_name_changed(self, new_name: str) -> None:
        if self._current is None:
            return
        new_name = new_name.strip()
        if not new_name:
            return
        comp = self._current.component
        if self._command_sink is not None:
            self._command_sink.push_edit_name(comp, new_name)
        else:
            comp.name = new_name
        self._current.update()
        self.value_changed.emit()

    def _on_prop_changed(self, index: int, new_value: str) -> None:
        """Handler legacy (QLineEdit) — apenas valor."""
        if self._current is None:
            return
        props = self._current.component.properties
        if 0 <= index < len(props):
            comp = self._current.component
            if self._command_sink is not None:
                self._command_sink.push_edit_property(comp, index, new_value)
            else:
                props[index].value = new_value
            self._current.update()
            self.value_changed.emit()

    def _on_row_changed(
        self, index: int, new_value: str, new_visible: bool,
    ) -> None:
        """
        Handler v0.22.2 para ``PropertyRow.value_changed``.

        Propaga value via ``push_edit_property`` e visibility via
        ``push_edit_visibility`` (v0.22.2.b) — AMBOS passam pelo
        QUndoStack agora. Ctrl+Z desfaz tanto edição de valor quanto
        toggle de label no canvas.
        """
        if self._current is None:
            return
        props = self._current.component.properties
        if not (0 <= index < len(props)):
            return
        comp = self._current.component
        old_value = props[index].value
        old_visible = props[index].visible

        if new_value != old_value:
            if self._command_sink is not None:
                self._command_sink.push_edit_property(comp, index, new_value)
            else:
                props[index].value = new_value
        if bool(new_visible) != bool(old_visible):
            if self._command_sink is not None and hasattr(
                self._command_sink, "push_edit_visibility"
            ):
                self._command_sink.push_edit_visibility(
                    comp, index, bool(new_visible)
                )
            else:
                # Fallback defensivo — sink antigo sem push_edit_visibility.
                props[index].visible = bool(new_visible)
        self._current.update()
        self.value_changed.emit()


# ---------------------------------------------------------------------------
# Editor (widget principal)
# ---------------------------------------------------------------------------


class PpEditor(QWidget):
    """
    Widget completo do editor Qucs-like. Encapsula view + scene +
    paleta + painel de propriedades + toolbar mínima + QUndoStack.

    Undo / redo
    -----------

    Todas as ações de usuário que mutam o :class:`PpProject`
    passam pelo :attr:`undo_stack`. Shortcuts ``Ctrl+Z`` /
    ``Ctrl+Y`` estão registrados no próprio widget. As mutações
    *programáticas* feitas diretamente em :class:`PpScene` (por
    exemplo no carregamento de um .sch) não geram comandos — são
    transições de estado "externas" ao histórico; a stack é
    limpa em :meth:`new_project` / :meth:`load_from_sch` /
    :meth:`PpScene.load_project`.
    """

    #: emitido quando o usuário clica em "Exportar ATP" (para que
    #: a MainWindow possa abrir o editor ATP com o resultado).
    export_requested = Signal(AtpProject)

    #: v0.82: emitido quando o usuário clica em "▶ Executar Análise"
    #: na toolbar — MainWindow conecta para abrir RunAnalysisDialog.
    run_analysis_requested = Signal()

    #: v3.1.3 Sub-sprint B: emitido quando o usuário clica em uma
    #: :class:`LinkTagGraphicsItem` no canvas. O ``MainWindow`` conecta
    #: para abrir o documento referenciado pelo target URI
    #: (``oneline:`` / ``tcc:`` / ``report:`` / ``pdf:``).
    link_tag_navigate = Signal(str)

    #: v0.93.1: emitido quando o "⛶ Tela cheia" toggle muda. O
    #: MainWindow conecta para ocultar/mostrar menu bar + tab bar
    #: (modo "zen" total). True = entrar em tela cheia.
    compact_mode_changed = Signal(bool)

    def __init__(self, project: Optional[PpProject] = None,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.scene = PpScene(project)
        self.view = PpView(self.scene, self)
        self.palette = PpPalette(self)
        self.properties = PpPropertiesPanel(self)

        # v0.23.1: chat panel (Claude API) — lazy-instanciado se a
        # API key estiver disponível; caso contrário, o widget
        # aparece desabilitado com mensagem orientadora.
        # Import local para evitar ciclo se alguém importar
        # schematic_pp.editor sem querer o módulo llm.
        from app.gui.schematic_pp.chat_panel import PpChatPanel
        self.chat_panel = PpChatPanel(self, parent=self)

        self.undo_stack = QUndoStack(self)

        # v0.90: tracking do path atual (None = untitled). Atualizado
        # por load_from_sch / save_to_sch. Usado pelo auto-save para
        # decidir o destino do snapshot.
        self._current_sch_path: Optional[str] = None

        # Permite que interações nativas de QGraphicsItem (drag de
        # ComponentItem) empilhem comandos sem precisar de referência
        # circular ao editor.
        self.scene.undo_stack = self.undo_stack

        self._build_toolbar()
        self._build_layout()
        self._wire_signals()
        self._install_undo_shortcuts()

    # ---- Construção -------------------------------------------------------

    def _build_toolbar(self) -> None:
        self.toolbar = QToolBar("Pp editor", self)
        self.toolbar.setMovable(False)

        self.act_new = QPushButton("Novo", self.toolbar)
        self.act_open = QPushButton("Abrir .sch", self.toolbar)
        self.act_save = QPushButton("Salvar .sch", self.toolbar)
        # v0.92.1+: botão "Exportar ATP" REMOVIDO da toolbar — a
        # integração ATP foi desvinculada do app principal.
        # Mantemos o atributo (com QPushButton oculto) para
        # preservar a API: handlers externos ainda conectam ao
        # signal export_requested via self.act_export.clicked.
        self.act_export = QPushButton("Exportar ATP", self.toolbar)
        self.act_export.setVisible(False)
        # v0.82: botão de execução de análise — gera quick action
        self.act_run_analysis = QPushButton("▶ Executar Análise", self.toolbar)
        self.act_run_analysis.setToolTip(
            "Executa estudos no esquemático carregado:\n"
            "• Curto-circuito (IEC 60909)\n"
            "• Fluxo de potência\n"
            "• Partida de motor (IEEE 399)\n"
            "• Arc-flash (NBR 17227 / IEEE 1584)\n"
            "• Estudo completo do barramento (todos)\n"
            "\n"
            "Requer um componente BUS no esquemático.\n"
            "Pressione F1 para guia rápido."
        )
        self.act_run_analysis.setStyleSheet(
            "QPushButton { background-color: #2ca02c; color: white; "
            "font-weight: bold; padding: 4px 12px; }"
            "QPushButton:hover { background-color: #208a20; }"
        )
        # Tool buttons (select vs wire). Checkable para indicar o
        # modo corrente; um grupo de exclusão mútua é mantido em
        # _on_tool_changed via setChecked.
        self.act_tool_select = QPushButton("Selecionar", self.toolbar)
        self.act_tool_select.setCheckable(True)
        self.act_tool_select.setChecked(True)
        self.act_tool_wire = QPushButton("Fio (W)", self.toolbar)
        self.act_tool_wire.setCheckable(True)
        self.act_undo = QPushButton("Desfazer", self.toolbar)
        self.act_redo = QPushButton("Refazer", self.toolbar)
        self.act_zoom_reset = QPushButton("Zoom 100%", self.toolbar)

        # v0.87: refresh datablocks com últimos resultados de análise
        # cacheados (PTW Equipment auto-binding).
        self.act_refresh_datablocks = QPushButton(
            "🔄 Atualizar datablocks", self.toolbar,
        )
        self.act_refresh_datablocks.setToolTip(
            "Substitui placeholders {nome:fmt} nas datablocks "
            "pelos valores da última análise pipeline executada.\n"
            "Datablocks sem placeholders ou sem análise prévia "
            "permanecem inalterados."
        )

        # v0.27.6: toggles de visibilidade dos painéis para maximizar
        # a área de modelagem. Estado persistido na instância (não em
        # QSettings — basta ser durável dentro da sessão).
        self.act_toggle_palette = QPushButton("◀ Paleta", self.toolbar)
        self.act_toggle_palette.setCheckable(True)
        self.act_toggle_palette.setChecked(True)
        self.act_toggle_palette.setToolTip(
            "Mostrar/ocultar paleta de componentes (F9). "
            "Quando oculta, use o botão direito do mouse no canvas "
            "para adicionar componentes."
        )

        self.act_toggle_properties = QPushButton("Propriedades ▶", self.toolbar)
        self.act_toggle_properties.setCheckable(True)
        self.act_toggle_properties.setChecked(True)
        self.act_toggle_properties.setToolTip(
            "Mostrar/ocultar painel de propriedades (F10)"
        )

        self.act_compact_mode = QPushButton("⛶ Tela cheia", self.toolbar)
        self.act_compact_mode.setCheckable(True)
        self.act_compact_mode.setToolTip(
            "Modo compacto: oculta paleta + propriedades + chat "
            "para máximo espaço de modelagem (F11)"
        )

        # v0.93.1 — TOOLBAR COMPACTA (design-critique).
        # Apenas 5 ações primárias visíveis. Restante migrou
        # para o menu hamburger "≡ Mais" (acesso rápido via
        # popup, libera ~60% do espaço horizontal).
        #
        # Ações primárias (sempre visíveis):
        #   1. Salvar .sch — preserva trabalho
        #   2. ▶ Executar Análise — ação principal (verde)
        #   3. ◀ Paleta — toggle
        #   4. Propriedades ▶ — toggle
        #   5. ⛶ Tela cheia — modo zen
        #
        # Ações secundárias (no menu ≡ Mais):
        #   Novo, Abrir, Selecionar, Fio (W), Desfazer, Refazer,
        #   Zoom 100%, Atualizar datablocks
        #
        # Atalhos Ctrl+N/O/S/Z/Y permanecem ativos via QShortcut.

        # Salvar — mantém ícone original (texto curto, alta freq.)
        self.toolbar.addWidget(self.act_save)
        self.toolbar.addSeparator()
        # ▶ Executar Análise — botão verde primário
        self.toolbar.addWidget(self.act_run_analysis)
        self.toolbar.addSeparator()
        # Hamburger "≡ Mais" — popup com ações secundárias
        self.act_more_menu = QPushButton("≡ Mais", self.toolbar)
        self.act_more_menu.setToolTip(
            "Mais ações:\n"
            "• Novo (Ctrl+N)\n"
            "• Abrir .sch (Ctrl+O)\n"
            "• Selecionar (S) / Fio (W)\n"
            "• Desfazer (Ctrl+Z) / Refazer (Ctrl+Y)\n"
            "• Zoom 100% (Ctrl+0)\n"
            "• Atualizar datablocks"
        )
        self.act_more_menu.clicked.connect(self._show_more_menu)
        self.toolbar.addWidget(self.act_more_menu)
        self.toolbar.addSeparator()
        # Toggles finais — paleta, propriedades, tela cheia
        for btn in (self.act_toggle_palette, self.act_toggle_properties,
                    self.act_compact_mode):
            self.toolbar.addWidget(btn)
        # NOTE: os botões "ocultos" (act_new, act_open, act_tool_select,
        # act_tool_wire, act_undo, act_redo, act_zoom_reset,
        # act_refresh_datablocks) NÃO são adicionados ao toolbar mas
        # continuam parented ao toolbar (e seus signals continuam
        # conectados). São acessados via popup do "≡ Mais".

    def _build_layout(self) -> None:
        splitter = QSplitter(Qt.Horizontal, self)

        palette_panel = QWidget(splitter)
        pal_lay = QVBoxLayout(palette_panel)
        pal_lay.setContentsMargins(4, 4, 4, 4)
        pal_lay.addWidget(QLabel("<b>Paleta</b>"))

        # v0.91: campo de busca para filtrar paleta. Foca a
        # conveniência de digitação rápida em catálogos grandes
        # (~40 componentes ATP-supported).
        self.palette_search = QLineEdit(self)
        self.palette_search.setPlaceholderText(
            "🔍 Filtrar (digite código ou nome)…"
        )
        self.palette_search.setClearButtonEnabled(True)
        self.palette_search.textChanged.connect(self.palette.filter_text)
        pal_lay.addWidget(self.palette_search)

        pal_lay.addWidget(self.palette, stretch=1)
        add_btn = QPushButton("Adicionar")
        add_btn.clicked.connect(self._on_palette_add_clicked)
        pal_lay.addWidget(add_btn)
        self._palette_add_btn = add_btn

        # v0.23.1: coluna direita vira splitter vertical —
        # propriedades em cima, chat Claude embaixo.
        right_splitter = QSplitter(Qt.Vertical, splitter)
        right_splitter.addWidget(self.properties)
        right_splitter.addWidget(self.chat_panel)
        right_splitter.setSizes([500, 300])  # mais espaço para propriedades

        splitter.addWidget(palette_panel)
        splitter.addWidget(self.view)
        splitter.addWidget(right_splitter)
        splitter.setSizes([180, 800, 280])

        # v0.27.6: refs guardadas para os toggles de visibilidade.
        self._palette_panel = palette_panel
        self._right_splitter = right_splitter
        self._main_splitter = splitter

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.toolbar)
        root.addWidget(splitter, stretch=1)
        # v0.93.2 — UM SÓ MENU NO TOPO. PpEditor toolbar oculta
        # por default. Suas ações migram para:
        # * Menu bar (Arquivo / Editar / Visualizar) do MainWindow
        # * cornerWidget no menu bar (▶ Executar Análise verde)
        # * Atalhos de teclado (Ctrl+S, Ctrl+Z, F5, F9-F11)
        # * Right-click menu no canvas (palette/zoom/etc)
        # Os botões continuam parented (signals/handlers ativos)
        # mas não consomem espaço vertical.
        self.toolbar.setVisible(False)

    # ---- Toggles de painel (v0.27.6) -------------------------------------

    def toggle_palette_panel(self, visible: bool) -> None:
        """
        Mostra ou oculta a paleta lateral. Quando oculta, o usuário
        pode adicionar componentes via botão direito no canvas
        (menu contextual).
        """
        self._palette_panel.setVisible(visible)
        # Sincroniza estado do botão (caso chamado externamente)
        if self.act_toggle_palette.isChecked() != visible:
            self.act_toggle_palette.blockSignals(True)
            self.act_toggle_palette.setChecked(visible)
            self.act_toggle_palette.blockSignals(False)

    def toggle_properties_panel(self, visible: bool) -> None:
        """Mostra ou oculta o painel de propriedades + chat (coluna direita)."""
        self._right_splitter.setVisible(visible)
        if self.act_toggle_properties.isChecked() != visible:
            self.act_toggle_properties.blockSignals(True)
            self.act_toggle_properties.setChecked(visible)
            self.act_toggle_properties.blockSignals(False)

    def set_compact_mode(self, enabled: bool) -> None:
        """
        v0.93.1 — Modo "tela cheia" REAL: oculta toolbar +
        paleta + propriedades + chat para máxima área de
        modelagem (canvas + tabs + menu bar apenas).

        Toggle através do botão "⛶ Tela cheia" na toolbar ou
        tecla F11. Emite ``compact_mode_changed`` para o
        MainWindow ocultar também menu bar/tab bar se
        desejado.
        """
        self.toggle_palette_panel(not enabled)
        self.toggle_properties_panel(not enabled)
        # v0.93.1+v0.93.2: toolbar do PpEditor é oculta SEMPRE
        # (UM SÓ menu no topo da tela — ações migraram para o
        # menu bar do MainWindow + cornerWidget). Não tocamos
        # a visibilidade aqui — fica permanentemente hidden.
        if self.act_compact_mode.isChecked() != enabled:
            self.act_compact_mode.blockSignals(True)
            self.act_compact_mode.setChecked(enabled)
            self.act_compact_mode.blockSignals(False)
        # v0.93.1: notifica MainWindow para sincronizar
        # menu bar / tab bar (opcional).
        self.compact_mode_changed.emit(enabled)

    def _wire_signals(self) -> None:
        # v3.1.1 Sprint 1: palette click enters PIN MODE (PTW Tutorial §Part 1
        # p.21-24 push-pin placement) instead of placing single instance at
        # canvas center. Context menu add and drag-drop still use the legacy
        # path via add_component_by_type.
        self.palette.request_add.connect(self._on_palette_request_add)
        self.scene.selection_changed.connect(self._on_selection_changed)
        self.view.item_double_clicked.connect(self._on_item_double_clicked)
        self.view.component_dropped.connect(self._on_component_dropped)
        self.view.wire_drawn.connect(self._on_wire_drawn)
        self.view.tool_changed.connect(self._on_tool_changed)
        self.act_zoom_reset.clicked.connect(self.view.zoom_reset)
        self.act_new.clicked.connect(self.new_project)
        self.act_save.clicked.connect(self._prompt_save)
        self.act_open.clicked.connect(self._prompt_open)
        self.act_export.clicked.connect(self._emit_export)
        # v0.82: emit signal para MainWindow abrir dialog Run Analysis
        self.act_run_analysis.clicked.connect(
            self.run_analysis_requested.emit,
        )
        self.act_tool_select.clicked.connect(
            lambda: self.view.set_tool(PpView.TOOL_SELECT)
        )
        self.act_tool_wire.clicked.connect(
            lambda: self.view.set_tool(PpView.TOOL_WIRE)
        )
        self.act_undo.clicked.connect(self.undo_stack.undo)
        self.act_redo.clicked.connect(self.undo_stack.redo)
        # v0.87: refresh datablocks
        self.act_refresh_datablocks.clicked.connect(
            self._on_refresh_datablocks
        )
        # v0.27.6: toggles de visibilidade dos painéis.
        self.act_toggle_palette.toggled.connect(self.toggle_palette_panel)
        self.act_toggle_properties.toggled.connect(
            self.toggle_properties_panel
        )
        self.act_compact_mode.toggled.connect(self.set_compact_mode)
        # v0.27.6: o canvas avisa quando precisa do menu de adição
        # (right-click em área vazia → emite request_add_at).
        self.view.request_add_component_at.connect(
            self._on_request_add_component_at
        )
        # v0.86: datablocks (PTW Equipment-style) — handlers
        self.view.request_add_datablock.connect(
            self._on_request_add_datablock
        )
        self.view.request_edit_datablock.connect(
            self._on_request_edit_datablock
        )
        # v3.1.3 Sub-sprint A: Tag insertion handlers
        self.view.request_add_link_tag.connect(self._on_add_link_tag)
        self.view.request_add_legend_tag.connect(self._on_add_legend_tag)
        # v3.1.3 Sub-sprint B: Link tag clicks bubble up to MainWindow
        self.scene.link_tag_clicked.connect(self._on_link_tag_clicked)
        # v3.1.3 Sub-sprint C: drop on wire → auto-bus-node em série
        self.view.component_dropped_on_wire.connect(
            self._on_component_dropped_on_wire
        )
        # Propriedades: QLineEdit.editingFinished já emite via panel;
        # aqui damos ao panel uma referência ao editor para empilhar
        # comandos em vez de mutar diretamente.
        self.properties.set_command_sink(self)

    def _show_more_menu(self) -> None:
        """v0.93.1: popup do hamburger "≡ Mais" — agrupa ações
        secundárias da toolbar (mantém ações primárias visíveis
        para reduzir chrome density)."""
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        # Agrupado em seções para legibilidade
        menu.addAction(
            "📄 Novo (Ctrl+N)",
            self.act_new.click,
        )
        menu.addAction(
            "📂 Abrir .sch (Ctrl+O)",
            self.act_open.click,
        )
        menu.addSeparator()
        menu.addAction(
            "🖱️ Modo Selecionar",
            self.act_tool_select.click,
        )
        menu.addAction(
            "🔌 Modo Fio (W)",
            self.act_tool_wire.click,
        )
        menu.addSeparator()
        menu.addAction(
            "↶ Desfazer (Ctrl+Z)",
            self.act_undo.click,
        )
        menu.addAction(
            "↷ Refazer (Ctrl+Y)",
            self.act_redo.click,
        )
        menu.addSeparator()
        menu.addAction(
            "🔍 Zoom 100% (Ctrl+0)",
            self.act_zoom_reset.click,
        )
        menu.addAction(
            "🔄 Atualizar datablocks",
            self.act_refresh_datablocks.click,
        )
        # Posiciona o popup logo abaixo do botão "≡ Mais"
        button_pos = self.act_more_menu.mapToGlobal(
            self.act_more_menu.rect().bottomLeft(),
        )
        menu.exec(button_pos)

    def _install_undo_shortcuts(self) -> None:
        """Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y via QShortcut (funcionam
        sem precisar de QAction no menu).

        v0.27.6: também instala F9/F10/F11 para toggles de painel.
        """
        undo_sc = QShortcut(QKeySequence.Undo, self)
        undo_sc.activated.connect(self.undo_stack.undo)
        redo_sc = QShortcut(QKeySequence.Redo, self)
        redo_sc.activated.connect(self.undo_stack.redo)
        # Alguns sistemas mapeiam Ctrl+Y para Redo; dobra de segurança.
        redo_sc2 = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_sc2.activated.connect(self.undo_stack.redo)
        # v0.27.6: panel toggles
        sc_palette = QShortcut(QKeySequence("F9"), self)
        sc_palette.activated.connect(
            lambda: self.act_toggle_palette.toggle()
        )
        sc_props = QShortcut(QKeySequence("F10"), self)
        sc_props.activated.connect(
            lambda: self.act_toggle_properties.toggle()
        )
        sc_compact = QShortcut(QKeySequence("F11"), self)
        sc_compact.activated.connect(
            lambda: self.act_compact_mode.toggle()
        )

    # ---- Ações -----------------------------------------------------------

    def new_project(self) -> None:
        """Descarta o projeto atual e cria um novo vazio. Limpa o histórico.

        v0.90: limpa também ``_current_sch_path`` (untitled).
        """
        self.scene.load_project(PpProject())
        self.properties.bind_component(None)
        self.undo_stack.clear()
        self._current_sch_path = None

    def _on_palette_request_add(self, type_code: str) -> None:
        """v3.1.1 Sprint 1: palette click → enter PIN MODE for that type.

        Per PTW Tutorial §Part 1 p.21-24 (push-pin placement): clicking
        a type in the palette turns the cursor into a cross; successive
        canvas clicks place instances of that component. Esc / V returns
        to TOOL_SELECT.

        BUS is special-cased: still uses the dialog-then-place flow because
        BUS has required quick-info (ID/V/n_phases) to be entered up-front.
        """
        if type_code == "BUS":
            # BUS has BusInfoDialog quick-add — no pin mode for it.
            self.add_component_by_type(type_code)
            return
        # All other types: enter pin mode
        self.view.enter_pin_mode(type_code)

    def add_component_by_type(
        self, type_code: str,
        scene_pos: Optional[QPointF] = None,
    ) -> Optional[ComponentItem]:
        """
        Cria um ``PpComponent`` do tipo solicitado e o posiciona no
        centro visível da view (ou em ``scene_pos`` se fornecido).
        A ação é empilhada no undo stack.

        v0.85: para ``type_code == "BUS"``, abre
        :class:`BusInfoDialog` ANTES de criar — usuário preenche
        ID/V/n_phases/panel/lineside e o BUS já nasce com
        propriedades válidas. Cancelar o dialog devolve ``None``
        (nenhum componente é criado).
        """
        if scene_pos is None:
            center = self.view.mapToScene(self.view.viewport().rect().center())
        else:
            center = scene_pos
        x = snap(center.x())
        y = snap(center.y())

        # v0.85: BUS tem dialog de quick-add (PTW Equipment Tab style).
        bus_name: Optional[str] = None
        if type_code == "BUS":
            props_or_none = self._prompt_bus_info()
            if props_or_none is None:
                # Usuário cancelou.
                return None
            props, bus_name = props_or_none
        else:
            props = _default_properties_for(type_code)

        comp = PpComponent(
            type=type_code,
            name=(
                "*" if type_code == "GND"
                else (bus_name or "")
            ),
            visible=True,
            x=x, y=y,
            label_dx=15, label_dy=-26, mirror=0, rotation=0,
            properties=props,
        )
        self.undo_stack.push(cmd.AddComponentCommand(self.scene, comp))
        item = self.scene.find_component_item(comp)
        assert item is not None
        return item

    # ---- BUS quick-add dialog (v0.85) -----------------------------------

    def _prompt_bus_info(
        self,
    ) -> Optional[tuple[list, str]]:
        """
        Abre :class:`BusInfoDialog` e retorna ``(properties, bus_id)``
        se o usuário aceitar, ou ``None`` se cancelar.

        Separado do ``add_component_by_type`` para permitir
        monkeypatch em testes.
        """
        from app.gui.bus_info_dialog import BusInfoDialog
        from PySide6.QtWidgets import QDialog
        from app.preprocessor.models import PpProperty

        # Coleta IDs de BUSes existentes para evitar colisão.
        existing_ids = {
            ci.component.name
            for ci in self.scene.component_items()
            if ci.component.type == "BUS" and ci.component.name
        }
        # Sugere próximo nome BUS-N.
        suggested = self._suggest_bus_id(existing_ids)
        dlg = BusInfoDialog(
            self,
            suggested_id=suggested,
            existing_ids=existing_ids,
        )
        if dlg.exec() != QDialog.Accepted:
            return None
        # Constroi PpProperty list a partir dos valores do dialog.
        # Visibilidade segue padrão BUS.ocomp (bus_id, V, panel,
        # lineside e has_AFD são visíveis por default).
        values = dlg.to_property_values()
        # 9 props no .ocomp; visibilidade conforme spec:
        #   bus_id(T), V(T), n_phases(F), panel(T), lineside(T),
        #   has_AFD(T), AFD_clearing(F), n_taps(F), description(F)
        visibility = [True, True, False, True, True, True, False, False, False]
        props = [
            PpProperty(value=v, visible=vis)
            for v, vis in zip(values, visibility)
        ]
        return props, dlg.bus_id()

    def _suggest_bus_id(self, existing: set[str]) -> str:
        """Próximo ``BUS-<n>`` que não colida."""
        i = 1
        while True:
            candidate = f"BUS-{i}"
            if candidate not in existing:
                return candidate
            i += 1

    def load_from_sch(self, path: str | Path) -> None:
        """Lê um .sch de disco e carrega na cena. Limpa o histórico.

        v0.86: também carrega sidecar ``<path>.datablocks.json`` se
        existir, populando ``project.datablocks`` antes do
        ``load_project`` para que os :class:`DataBlockItem` sejam
        criados ancorados aos componentes corretos.

        v0.90: armazena ``_current_sch_path`` para uso do auto-save
        + marca undo_stack como clean (estado salvo).
        """
        project = parse_sch_file(str(path))
        # v0.86: carrega datablocks do sidecar (silencioso se ausente
        # ou corrompido — UX prefere não bloquear).
        try:
            from app.gui.schematic_pp.datablock_io import (
                load_datablocks_sidecar,
            )
            project.datablocks = load_datablocks_sidecar(str(path))
        except Exception:
            project.datablocks = []
        # v3.1.3 Sub-sprint D: carrega link_tags + legend_tags +
        # linked_properties do sidecar JSON ``<path>.olivas.json``.
        try:
            from app.gui.schematic_pp.sidecar_io import load_sidecar
            load_sidecar(project, str(path))
        except Exception:
            pass
        self.scene.load_project(project)
        self.properties.bind_component(None)
        self.undo_stack.clear()
        # v0.90: tracking do path para auto-save / status bar.
        self._current_sch_path = str(path)
        self.undo_stack.setClean()

    def save_to_sch(self, path: str | Path) -> None:
        """Serializa a cena atual para um .sch.

        v0.86: também grava sidecar ``<path>.datablocks.json`` se
        houver datablocks no project.

        v0.90: atualiza ``_current_sch_path`` + clean undo_stack +
        remove autosave correspondente (limpa estado de "tem
        recuperação pendente").
        """
        proj = self.scene.to_project()
        serialize_sch_file(proj, str(path))
        # v0.86: persiste datablocks no sidecar JSON.
        try:
            from app.gui.schematic_pp.datablock_io import (
                save_datablocks_sidecar,
            )
            save_datablocks_sidecar(str(path), proj.datablocks)
        except Exception:
            pass
        # v3.1.3 Sub-sprint D: persiste link_tags + legend_tags +
        # linked_properties no sidecar JSON ``<path>.olivas.json``.
        # Skip-write se sem extensões (não polui filesystem).
        try:
            from app.gui.schematic_pp.sidecar_io import save_sidecar
            save_sidecar(proj, str(path))
        except Exception:
            pass
        # v0.90: track path + clean state + remove autosave.
        self._current_sch_path = str(path)
        self.undo_stack.setClean()
        try:
            from app.gui.auto_save import remove_autosave_for
            remove_autosave_for(str(path))
        except Exception:
            pass

    @property
    def current_sch_path(self) -> Optional[str]:
        """v0.90: path atual do .sch (None se untitled)."""
        return getattr(self, "_current_sch_path", None)

    def is_dirty(self) -> bool:
        """v0.90: True se há mudanças não salvas (undo_stack
        != clean state)."""
        return not self.undo_stack.isClean()

    def export_to_atp(self) -> AtpProject:
        """Gera um :class:`AtpProject` equivalente à cena atual."""
        proj = self.scene.to_project()
        return to_atp(proj)

    # ---- Command-sink API para o panel de propriedades -----------------

    def push_edit_property(self, component: PpComponent, index: int,
                           new_value: str) -> None:
        old = component.properties[index].value
        if old == new_value:
            return
        self.undo_stack.push(
            cmd.EditPropertyCommand(self.scene, component, index, new_value)
        )

    def push_edit_name(self, component: PpComponent, new_name: str) -> None:
        if component.name == new_name:
            return
        self.undo_stack.push(
            cmd.EditNameCommand(self.scene, component, new_name)
        )

    def push_edit_visibility(
        self, component: PpComponent, index: int, new_visible: bool,
    ) -> None:
        """
        v0.22.2.b: toggle do checkbox "exibir" entra no histórico
        undo/redo via :class:`EditVisibilityCommand`.
        """
        if not (0 <= index < len(component.properties)):
            return
        old = component.properties[index].visible
        if old == bool(new_visible):
            return
        self.undo_stack.push(
            cmd.EditVisibilityCommand(
                self.scene, component, index, bool(new_visible)
            )
        )

    # ---- Slots -----------------------------------------------------------

    def _on_palette_add_clicked(self) -> None:
        items = self.palette.selectedItems()
        if not items:
            return
        code = items[0].data(Qt.UserRole)
        if code:
            self.add_component_by_type(str(code))

    def _on_selection_changed(self) -> None:
        selected = self.scene.selected_components()
        if len(selected) == 1:
            self.properties.bind_component(selected[0])
        else:
            self.properties.bind_component(None)

    def _on_item_double_clicked(self, item) -> None:
        """
        v0.22.2: duplo-clique em componente abre o diálogo modal rico
        (ATPDraw-style) em vez de apenas focar no painel lateral.
        Se o componente não tem ``.ocomp`` no registry, cai no painel
        lateral (fallback v0.21.x).
        """
        if isinstance(item, ComponentItem):
            # Seleciona o item no painel lateral ANTES de abrir o modal,
            # para que o modal possa consumir o mesmo state.
            self.properties.bind_component(item)
            # Abre o modal somente se existe spec — evita dialog vazio
            # para componentes legacy-only.
            self.properties._open_modal_dialog(item)

    def _on_component_dropped(self, type_code: str, scene_pos: QPointF) -> None:
        """Paleta → canvas (drag-drop). Empilha AddComponentCommand."""
        self.add_component_by_type(type_code, scene_pos=scene_pos)

    def _on_component_dropped_on_wire(
        self, type_code: str, scene_pos: QPointF, wire_item,
    ) -> None:
        """v3.1.3 Sub-sprint C: drop em wire → auto-bus-node em série.

        Per PTW Tutorial §Part 1 p.27. Atomic operation:
        1. Remove o wire original
        2. Add componente em scene_pos
        3. Add 2 wires (in: start→component, out: component→end)

        Undoable como uma única operação via :class:`AddSeriesComponentCommand`.
        """
        from . import commands as cmd
        from app.preprocessor.models import PpWire
        from .items import WireItem
        from .scene import snap

        if not isinstance(wire_item, WireItem):
            # Fallback: drop normal
            self._on_component_dropped(type_code, scene_pos)
            return

        original_wire = wire_item.wire

        # Special-case BUS: BusInfoDialog flow doesn't fit AddSeries
        # (we'd need to know the bus name before splitting). Skip the
        # auto-bus-node path for BUS — fall back to regular drop.
        if type_code == "BUS":
            self._on_component_dropped(type_code, scene_pos)
            return

        # Build component at drop pos (snapped). Use defaults.
        x = snap(scene_pos.x())
        y = snap(scene_pos.y())
        props = _default_properties_for(type_code)
        new_comp = PpComponent(
            type=type_code,
            name=("*" if type_code == "GND" else ""),
            visible=True,
            x=x, y=y,
            label_dx=15, label_dy=-26, mirror=0, rotation=0,
            properties=props,
        )

        # Build 2 wires: original_wire.start → comp_pos and comp_pos → original_wire.end
        wire_in = PpWire(
            x1=original_wire.x1, y1=original_wire.y1,
            x2=x, y2=y, label="",
        )
        wire_out = PpWire(
            x1=x, y1=y,
            x2=original_wire.x2, y2=original_wire.y2, label="",
        )

        self.undo_stack.push(cmd.AddSeriesComponentCommand(
            self.scene, original_wire, new_comp, wire_in, wire_out,
        ))

    def _on_request_add_component_at(
        self, type_code: str, scene_pos: QPointF,
    ) -> None:
        """
        v0.27.6: usuário escolheu componente no menu contextual
        do canvas (right-click em área vazia). Usa o mesmo fluxo
        do drag-drop — AddComponentCommand undoable.
        """
        self.add_component_by_type(type_code, scene_pos=scene_pos)

    def _on_wire_drawn(self, wire: PpWire) -> None:
        """Ferramenta *wire*: dois cliques geraram um fio. Undoable."""
        self.undo_stack.push(cmd.AddWireCommand(self.scene, wire))

    # ---- Datablocks (v0.86 — PTW Equipment) ----------------------------

    # ------------------------------------------------------------------
    # v3.1.3 Sub-sprint A — Tag handlers
    # ------------------------------------------------------------------

    def _on_add_link_tag(self, scene_pos) -> None:
        """v3.5.2 (closes SKIPPED_BACKLOG A.1) — unified dialog.

        Substitui os 2 ``QInputDialog`` originais (v3.1.3) por
        :class:`AddLinkTagDialog` com browser de schemes, preview live,
        toggles ``visible``/``closed_arrow`` e Browse para PDFs.

        Per PTW Tutorial §Part 1 p.35-42: link tags navigate to other
        documents (oneline/tcc/report/pdf) via URI-style target.
        """
        from PySide6.QtWidgets import QDialog
        from app.gui.add_link_tag_dialog import AddLinkTagDialog
        from app.preprocessor.models import PpLinkTag
        from . import commands as cmd

        dialog = AddLinkTagDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        data = dialog.form_data()
        if not data.label or not data.target.split(":", 1)[-1].strip():
            return

        tag = PpLinkTag(
            label=data.label,
            target=data.target,
            x=int(scene_pos.x()),
            y=int(scene_pos.y()),
            visible=data.visible,
            closed_arrow=data.closed_arrow,
        )
        self.undo_stack.push(cmd.AddLinkTagCommand(self.scene, tag))

    def _on_add_legend_tag(self, shape: str, scene_pos) -> None:
        """v3.1.3 Sub-sprint A: prompt user for legend text, push
        :class:`AddLegendTagCommand` with chosen shape.

        Per PTW Tutorial §Part 1 p.43-52.
        """
        from PySide6.QtWidgets import QInputDialog
        from app.preprocessor.models import PpLegendTag
        from . import commands as cmd

        text, ok = QInputDialog.getText(
            self, f"Inserir Legend Tag ({shape})",
            "Texto interno:",
            text=f"Z-{shape[:3].upper()}",
        )
        if not ok or not text.strip():
            return

        tag = PpLegendTag(
            text=text.strip(),
            shape=shape,
            x=int(scene_pos.x()),
            y=int(scene_pos.y()),
        )
        self.undo_stack.push(cmd.AddLegendTagCommand(self.scene, tag))

    # ------------------------------------------------------------------
    # v3.1.3 Sub-sprint B — Link tag click → MainWindow navigation
    # ------------------------------------------------------------------

    def _on_link_tag_clicked(self, target: str) -> None:
        """v3.1.3 Sub-sprint B: re-emit link click for MainWindow handle.

        Target URI scheme (PTW Tutorial §Part 1 p.35):
        * ``oneline:DocName`` → open named one-line document
        * ``tcc:CoordName`` → open TCC coordinogram
        * ``report:RPT_Name`` → open report viewer
        * ``pdf:path/to/file.pdf`` → open external PDF
        """
        self.link_tag_navigate.emit(target)

    def _on_request_add_datablock(self, host_item) -> None:
        """
        Right-click em componente → 'Adicionar datablock'. Abre
        :class:`DataBlockEditDialog` para o usuário preencher
        as linhas. Aceitar empilha :class:`AddDataBlockCommand`.

        Cancelar = nenhum datablock criado.

        v0.88: ``template_lines`` é inicializado igual a ``lines``
        (o usuário acabou de editar — texto é o template).
        """
        from app.preprocessor.models import PpDataBlock
        from app.gui.datablock_dialog import DataBlockEditDialog
        from PySide6.QtWidgets import QDialog
        if not hasattr(host_item, "component"):
            return
        dlg = DataBlockEditDialog(
            self,
            initial_lines=[],
            title=(
                f"Datablock — "
                f"{host_item.component.name or host_item.component.type}"
            ),
        )
        if dlg.exec() != QDialog.Accepted:
            return
        lines = dlg.lines()
        if not lines:
            return  # vazio = sem datablock
        db = PpDataBlock(
            component_name=host_item.component.name or "*",
            dx=50, dy=-10,
            lines=list(lines),
            template_lines=list(lines),  # v0.88: sticky template
            visible=True,
        )
        self.undo_stack.push(cmd.AddDataBlockCommand(self.scene, db))

    def _on_request_edit_datablock(self, db_item) -> None:
        """
        Editar datablock existente — undoable via
        :class:`EditDataBlockTemplateCommand` (v0.88).

        v0.88 UX: o dialog mostra o ``template_lines`` (com
        ``{placeholders}`` visíveis). Save atualiza tanto
        ``template_lines`` quanto ``lines`` (zerando o cache
        de render — próximo refresh repopula).
        """
        from app.gui.datablock_dialog import DataBlockEditDialog
        from PySide6.QtWidgets import QDialog
        db = db_item.datablock
        # Mostra o template (preserva placeholders editáveis).
        # Para datablocks legacy sem template, exibe lines.
        initial = list(db.effective_template())
        dlg = DataBlockEditDialog(
            self,
            initial_lines=initial,
            title=f"Datablock — {db.component_name}",
        )
        if dlg.exec() != QDialog.Accepted:
            return
        new_template = dlg.lines()
        # No-op se o usuário só abriu/fechou.
        if new_template == initial:
            return
        self.undo_stack.push(
            cmd.EditDataBlockTemplateCommand(
                self.scene, db, new_template,
            )
        )

    def _on_refresh_datablocks(self) -> None:
        """
        v0.87: aplica resultados cacheados em
        ``scene.results_cache`` aos placeholders dos datablocks.

        Mostra mensagem de status (ou warning se não houver
        resultados/datablocks). Cada datablock atualizado vira
        um command undoable separado, agrupado por uma macro.
        """
        from PySide6.QtWidgets import QMessageBox
        from app.gui.schematic_pp.datablock_binder import (
            refresh_datablocks_from_cache,
        )
        cache = getattr(self.scene, "results_cache", None)
        if cache is None or not cache.all_bus_ids():
            QMessageBox.information(
                self, "Atualizar datablocks",
                "Nenhum resultado de análise em cache. "
                "Rode 'Estudo do barramento' (▶ Executar Análise) "
                "primeiro.",
            )
            return
        if not self.scene.datablock_items():
            QMessageBox.information(
                self, "Atualizar datablocks",
                "Nenhum datablock no esquemático para atualizar.",
            )
            return
        # Agrupa numa macro para que Ctrl+Z desfaça todas as
        # atualizações em uma única operação de undo.
        self.undo_stack.beginMacro("Atualizar datablocks")
        try:
            n = refresh_datablocks_from_cache(self.scene, cache)
        finally:
            self.undo_stack.endMacro()
        if n == 0:
            QMessageBox.information(
                self, "Atualizar datablocks",
                "Nenhum datablock tinha placeholders cobertos "
                "pelos resultados em cache.",
            )
        else:
            try:
                self.statusBar().showMessage(
                    f"✓ {n} datablock(s) atualizado(s).", 4000,
                )
            except Exception:
                pass

    def _on_tool_changed(self, tool: str) -> None:
        """Mantém os botões de tool em sync com o estado da view."""
        self.act_tool_select.setChecked(tool == PpView.TOOL_SELECT)
        self.act_tool_wire.setChecked(tool == PpView.TOOL_WIRE)

    def _emit_export(self) -> None:
        self.export_requested.emit(self.export_to_atp())

    # ---- Diálogos --------------------------------------------------------
    # Separados para permitir override em testes (monkeypatch).

    def _prompt_save(self) -> None:  # pragma: no cover - triggers dialog
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar esquemático", "", "Qucs schematic (*.sch)")
        if path:
            self.save_to_sch(path)

    def _prompt_open(self) -> None:  # pragma: no cover - triggers dialog
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir esquemático", "", "Qucs schematic (*.sch)")
        if path:
            self.load_from_sch(path)


# ---------------------------------------------------------------------------
# Propriedades default por tipo
# ---------------------------------------------------------------------------


_DEFAULT_PROPS: dict[str, list[tuple[str, bool]]] = {
    # Cada entry: (valor default, visible?). A ordem é relevante.
    "R":       [("1k",     True), ("26.85",   False), ("european", False)],
    "L":       [("1 mH",   True), ("0",       False), ("26.85",    False)],
    "C":       [("1 uF",   True), ("0",       False), ("neutral",  False)],
    "GND":     [],
    "Vdc":     [("12 V",   True)],
    "Vac":     [("220 V",  True), ("60 Hz",   True),  ("0", False), ("0", False)],
    "Idc":     [("1 A",    True)],
    "Iac":     [("1 A",    True), ("60 Hz",   True),  ("0", False), ("0", False)],
    "Vrect":   [("100 V",  True), ("10 ms",   True)],
    "Vsurge":  [("10 kV",  True)],
    "SwIdeal": [("0",      True), ("1e9",     True)],
    "Relais":  [("0",      True), ("1e9",     True)],
    "SwTACS":  [("trigger", True)],
    # VCB 1φ — chave a vácuo com modelo estatístico completo.
    # Defaults: corte com chopping 5 A, σ=1 A, di/dt crítico típico
    # de câmara média tensão (16 A/µs), recuperação dielétrica
    # 17 kV/ms (EPRI 1989).
    "VCB": [
        ("0",      True),   # T_open [s]
        ("1e9",    True),   # T_close [s]
        ("5",      True),   # I_chop [A]
        ("1",      False),  # σ(I_chop) [A]
        ("16",     True),   # di/dt_crit [A/µs]
        ("0.034",  False),  # d(di/dt) [A/µs²]
        ("17",     True),   # k_dielec [V/µs]
        ("0.69e3", False),  # U0_dielec [V]
        ("5e-4",   False),  # T_bounce [s]
        ("1",      False),  # Seed
    ],
    # VCB 3φ — 3 chaves com T_open/T_close independentes por fase
    # + parâmetros de reignição compartilhados (mesmo pólo).
    # Defaults: abertura simultânea em 50 ms (típico disjuntor MT).
    "VCB3": [
        ("50e-3",  True),   # T_open_A  [s]
        ("1e9",    True),   # T_close_A [s]
        ("50e-3",  True),   # T_open_B  [s]
        ("1e9",    True),   # T_close_B [s]
        ("50e-3",  True),   # T_open_C  [s]
        ("1e9",    True),   # T_close_C [s]
        ("5",      True),   # I_chop [A]
        ("1",      False),  # σ(I_chop) [A]
        ("16",     True),   # di/dt_crit [A/µs]
        ("0.034",  False),  # d(di/dt) [A/µs²]
        ("17",     True),   # k_dielec [V/µs]
        ("0.69e3", False),  # U0_dielec [V]
        ("5e-4",   False),  # T_bounce [s]
        ("1",      False),  # Seed
    ],
    "Diode":   [("0.7",    True), ("1e-3",    False)],
    "Thyr":    [("0.7",    True), ("1e-3",    False)],
    "GTO":     [("0.7",    True), ("1e-3",    False)],
    "IGBT":    [("2.5",    True), ("1e-3",    False)],
    "MOSFET":  [("0.05",   True), ("1e-3",    False)],
    "Tr":      [("1:1",    True), ("1 mH",    True)],
    "sTr":     [("1:1",    True), ("1 mH",    True)],
    "Tr3":     [("1:1:1",  True), ("1 mH",    True)],
    "MUT":     [("1 mH",   True), ("1 mH",    True), ("0.5",       True)],
    "TLIN":    [("100 km", True), ("0.05 Ohm/km", False)],
    "BERG":    [("100 km", True), ("500 Ohm", False)],
    "JMARTI":  [("model.pch", True)],
    "ZnO":     [("200 V",  True)],
    "RNL":     [("lookup.dat", True)],
    "LNL":     [("sat.dat", True)],
    "VProbe":  [],
    "IProbe":  [],
    "TACS":    [("f(t)",   True)],
    "MODEL":   [("model.mod", True)],
}


def _default_properties_for(type_code: str) -> list[PpProperty]:
    """
    Gera a lista default de properties para um tipo novo.

    v0.24.1 (registry-first com fallback): consulta o registry de
    .ocomp primeiro. Se há spec, usa ``spec.properties[i].default``
    e ``.visible`` (convertendo valores numéricos para string com
    sufixo de unidade quando apropriado). Caso contrário, cai no
    ``_DEFAULT_PROPS`` legacy.

    Mudança motivada: Tr/sTr/Tr3 ganharam campos BCTRAN extras em
    v0.24.1 (V_H/V_L/S_nom/v_sc_pct/...) — o ``_DEFAULT_PROPS``
    legacy tem só 2 entradas, o que causaria mismatch com o
    bridge que espera props 2-8.
    """
    from app.preprocessor.spec import get_default_registry, PropertyType

    spec = get_default_registry().get(type_code)
    if spec is not None:
        props: list[PpProperty] = []
        for prop_spec in spec.properties:
            val = _format_default_value(prop_spec)
            props.append(PpProperty(value=val, visible=prop_spec.visible))
        return props

    # Fallback legacy
    legacy = _DEFAULT_PROPS.get(type_code, [])
    return [PpProperty(value=v, visible=vis) for v, vis in legacy]


def _format_default_value(prop_spec) -> str:
    """
    Converte ``prop_spec.default`` para string compatível com o
    campo ``PpProperty.value``. Preserva unidade quando já embutida
    no valor default (ex: string "1 mH").
    """
    default = prop_spec.default
    if default is None:
        return ""
    if isinstance(default, str):
        return default
    # Numérico — formata sem sufixo de unidade (a unidade aparece
    # no label do painel, não no value cru).
    if isinstance(default, float):
        # Preserva notação científica para valores muito grandes/
        # pequenos (1e9 → "1000000000.0"). Usa repr para estabilidade.
        return repr(default)
    return str(default)


# ---------------------------------------------------------------------------
# Drag preview (palette → canvas)
# ---------------------------------------------------------------------------


def _render_drag_preview(type_code: str,
                         padding: int = 6) -> Optional[QPixmap]:
    """Renderiza um :class:`QPixmap` do símbolo para usar como drag cursor.

    Retorna ``None`` se o tipo não tem renderer — nesse caso o Qt
    usa o preview default (do QListWidgetItem). O pixmap é gerado
    chamando diretamente o :class:`SymbolRenderer`, fora de qualquer
    :class:`QGraphicsScene` — assim não polui a cena real e pode
    rodar em testes sem event loop visual.
    """
    renderer = get_renderer(type_code)
    if renderer is None:
        return None
    br = renderer.bounding_rect()
    w = max(int(br.width()) + 2 * padding, 32)
    h = max(int(br.height()) + 2 * padding, 32)
    pm = QPixmap(w, h)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    try:
        painter.setRenderHint(QPainter.Antialiasing, True)
        # Translada para que o bounding_rect caiba centrado no pixmap.
        painter.translate(-br.left() + padding, -br.top() + padding)
        renderer.paint(painter)
    finally:
        painter.end()
    return pm
