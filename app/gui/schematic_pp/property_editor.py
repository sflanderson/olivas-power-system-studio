"""
app.gui.schematic_pp.property_editor — painel rico de edição de
propriedades baseado em ``ComponentSpec`` (.ocomp).

Responsabilidades
-----------------

* Widget factory: dado um :class:`PropertySpec` e um valor atual
  (string), retorna o widget Qt apropriado (``QDoubleSpinBox`` para
  FLOAT, ``QComboBox`` para ENUM, ``QCheckBox`` para BOOL, etc.).
* ``PropertyRow``: uma linha de formulário auto-contida com:
    - label com unidade;
    - widget de edição (tipo apropriado);
    - checkbox "visível no canvas";
    - botão de restaurar default;
    - tooltip com ``description`` e ``example``.
* ``PropertyGroupBox``: ``QGroupBox`` com várias ``PropertyRow`` —
  uma por ``PropertyGroup``. Colapsa se o grupo for "advanced".
* ``ComponentPropertyDialog``: diálogo modal com tabs — aberto
  ao duplo-clique no canvas.

Por que um módulo separado em vez de crescer ``editor.py``?

* ``editor.py`` já passa de 650 linhas e contém o widget principal.
* As classes aqui são reutilizáveis (painel lateral + modal usam os
  mesmos ``PropertyGroupBox`` / ``PropertyRow``).
* Facilita teste unitário (uma ``PropertyRow`` isolada pode ser
  instanciada sem subir o editor inteiro).

Compatibilidade (v0.22.2)
-------------------------

Se o componente NÃO tem ``.ocomp`` no registry (improvável após
v0.22.0, mas possível em import de .sch exóticos), cai no fallback
``_FallbackEditor`` que usa ``QLineEdit`` texto livre — comportamento
equivalente ao painel pré-v0.22.2.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.preprocessor.models import PpComponent
from app.preprocessor.spec import (
    ComponentSpec,
    PropertyGroup,
    PropertySpec,
    PropertyType,
    get_default_registry,
)


# ---------------------------------------------------------------------------
# Widget factory
# ---------------------------------------------------------------------------


def make_value_editor(
    prop_spec: PropertySpec,
    current_value: str,
) -> tuple[QWidget, Callable[[], str], Callable[[], None]]:
    """
    Constrói o widget de edição apropriado para ``prop_spec``.

    Parameters
    ----------
    prop_spec:
        Schema da propriedade (de ``spec.properties[i]``).
    current_value:
        Valor atual em formato string (vindo de ``PpProperty.value``).

    Returns
    -------
    (widget, get_value, connect_finish)
        - ``widget``: ``QWidget`` a inserir no layout.
        - ``get_value()``: callable que retorna o valor atual do widget
          como string (compatível com ``PpProperty.value``).
        - ``connect_finish(cb)``: conecta o callback ``cb`` ao evento
          "usuário terminou de editar" — ``editingFinished`` para
          QLineEdit/SpinBox, ``currentIndexChanged`` para Combo,
          ``toggled`` para Checkbox.

    Tipo → widget (v0.22.2):
        FLOAT      → QDoubleSpinBox com min/max/unit suffix
        INT        → QSpinBox
        BOOL       → QCheckBox (texto do label ao lado)
        ENUM       → QComboBox (items de ``prop_spec.choices``)
        FILE       → QLineEdit + botão "…" (QFileDialog)
        EXPRESSION → QLineEdit monospace
        STRING     → QLineEdit (fallback)
        TABLE      → QLineEdit + botão "editar…" (placeholder, v0.22.x)

    widget_hint (v0.24.3) — tem precedência sobre o type:
        "saturation_curve" → SaturationCurveEditor (QTableWidget +
                             preview matplotlib opcional)
    """
    ptype = prop_spec.type

    # ----- widget_hint: saturation_curve (v0.24.3) -----
    # Tem precedência sobre o type porque é especialização de UX.
    hint = getattr(prop_spec, "widget_hint", None)
    if hint == "saturation_curve":
        from app.gui.schematic_pp.saturation_curve_editor import (
            SaturationCurveEditor,
        )
        editor = SaturationCurveEditor(
            initial_csv=current_value or "",
        )
        # Signal mapping: value_changed(str) é o novo valor CSV
        return (
            editor,
            lambda: editor.get_value(),
            lambda cb: editor.value_changed.connect(lambda _v=None: cb()),
        )

    # ----- FLOAT -----
    if ptype == PropertyType.FLOAT:
        sb = QDoubleSpinBox()
        sb.setDecimals(6)
        # Range conservador se spec não define
        low = prop_spec.min if prop_spec.min is not None else -1.0e12
        high = prop_spec.max if prop_spec.max is not None else 1.0e12
        sb.setRange(low, high)
        if prop_spec.unit:
            sb.setSuffix(f" {prop_spec.unit}")
        # Converte string para float — aceita "1k", "1e3", "1.5", etc.
        try:
            sb.setValue(_parse_float_lenient(current_value))
        except (TypeError, ValueError):
            # valor não-numérico: usa default do spec (se numérico) ou 0
            try:
                sb.setValue(float(prop_spec.default))
            except (TypeError, ValueError):
                sb.setValue(0.0)
        return (
            sb,
            lambda: _strip_unit_suffix(str(sb.value()), prop_spec.unit),
            lambda cb: sb.editingFinished.connect(cb),
        )

    # ----- INT -----
    if ptype == PropertyType.INT:
        sb = QSpinBox()
        low = (
            int(prop_spec.min) if prop_spec.min is not None else -(2**31)
        )
        high = (
            int(prop_spec.max) if prop_spec.max is not None else (2**31 - 1)
        )
        sb.setRange(low, high)
        if prop_spec.unit:
            sb.setSuffix(f" {prop_spec.unit}")
        try:
            sb.setValue(int(float(current_value)))
        except (TypeError, ValueError):
            try:
                sb.setValue(int(float(prop_spec.default)))
            except (TypeError, ValueError):
                sb.setValue(0)
        return (
            sb,
            lambda: str(sb.value()),
            lambda cb: sb.editingFinished.connect(cb),
        )

    # ----- BOOL -----
    if ptype == PropertyType.BOOL:
        cb_box = QCheckBox()
        normalized = (current_value or "").strip().lower()
        cb_box.setChecked(normalized in ("1", "true", "sim", "yes", "on"))
        return (
            cb_box,
            lambda: "true" if cb_box.isChecked() else "false",
            lambda cb: cb_box.toggled.connect(lambda _=None: cb()),
        )

    # ----- ENUM -----
    if ptype == PropertyType.ENUM:
        combo = QComboBox()
        for choice in prop_spec.choices or []:
            combo.addItem(str(choice))
        # Seleciona item correspondente ao current_value, senão o default
        idx = combo.findText(current_value)
        if idx < 0:
            idx = combo.findText(str(prop_spec.default))
        if idx >= 0:
            combo.setCurrentIndex(idx)
        return (
            combo,
            lambda: combo.currentText(),
            lambda cb: combo.currentIndexChanged.connect(lambda _i: cb()),
        )

    # ----- FILE -----
    if ptype == PropertyType.FILE:
        container = QWidget()
        hl = QHBoxLayout(container)
        hl.setContentsMargins(0, 0, 0, 0)
        line = QLineEdit(current_value)
        btn = QPushButton("…")
        btn.setMaximumWidth(30)
        btn.setToolTip("Escolher arquivo…")

        def _pick_file() -> None:
            filename, _ = QFileDialog.getOpenFileName(
                container, "Selecionar arquivo", line.text()
            )
            if filename:
                line.setText(filename)
                line.editingFinished.emit()

        btn.clicked.connect(_pick_file)
        hl.addWidget(line)
        hl.addWidget(btn)
        return (
            container,
            lambda: line.text(),
            lambda cb: line.editingFinished.connect(cb),
        )

    # ----- EXPRESSION -----
    if ptype == PropertyType.EXPRESSION:
        le = QLineEdit(current_value)
        le.setFont(QFont("Consolas, Courier New, monospace"))
        return (
            le,
            lambda: le.text(),
            lambda cb: le.editingFinished.connect(cb),
        )

    # ----- STRING / TABLE / fallback -----
    le = QLineEdit(current_value)
    return (
        le,
        lambda: le.text(),
        lambda cb: le.editingFinished.connect(cb),
    )


# ---------------------------------------------------------------------------
# Helpers numéricos
# ---------------------------------------------------------------------------


_SI_SUFFIXES: dict[str, float] = {
    "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6,
    "m": 1e-3,  "k": 1e3,   "M": 1e6,  "G": 1e9,  "T": 1e12,
}


def _parse_float_lenient(text: str) -> float:
    """
    Parseia string com suporte a sufixos SI (``"1k"`` = 1000,
    ``"1 uF"`` = 1e-6). Se não reconhecer, tenta ``float()``
    diretamente. ``""`` → 0.0 para não travar o spinbox.
    """
    s = (text or "").strip()
    if not s:
        return 0.0
    # Tenta float direto
    try:
        return float(s)
    except ValueError:
        pass
    # Tenta SI prefix na primeira letra não-numérica
    for i, ch in enumerate(s):
        if ch in _SI_SUFFIXES:
            head = s[:i].strip()
            try:
                return float(head) * _SI_SUFFIXES[ch]
            except ValueError:
                continue
    # Desiste — lança
    return float(s)   # vai gerar ValueError


def _strip_unit_suffix(text: str, unit: str) -> str:
    """Se ``text`` termina com `` {unit}``, remove."""
    if unit and text.endswith(f" {unit}"):
        return text[: -(len(unit) + 1)]
    return text


# ---------------------------------------------------------------------------
# PropertyRow: uma linha do formulário
# ---------------------------------------------------------------------------


class PropertyRow(QWidget):
    """
    Uma linha completa: label + editor + checkbox visible + botão restore.

    v3.1.2 Sub-sprint A: suporte a Library link/unlink (PTW Tutorial §Part 1
    p.55) — quando ``linked_library is not None``, o editor + checkbox visible
    ficam read-only e cinza-claro, e um botão "🔗" aparece para Unlink.

    Emite:
        value_changed(index, new_value, new_visible) quando o usuário
        edita o valor ou toggle visibility.
        unlink_requested(index) quando o usuário clica em "🔗" para
        desvincular da library.
    """

    value_changed = Signal(int, str, bool)
    # v3.1.2: emitido quando o usuário pede para desvincular esta property
    # de uma library vendor (clique no botão "🔗").
    unlink_requested = Signal(int)

    def __init__(
        self,
        index: int,
        prop_spec: PropertySpec,
        current_value: str,
        current_visible: bool,
        parent: Optional[QWidget] = None,
        *,
        linked_library: Optional[str] = None,  # v3.1.2 Sub-sprint A
    ) -> None:
        super().__init__(parent)
        self._index = index
        self._spec = prop_spec
        self._linked_library = linked_library  # v3.1.2

        # Widget de edição
        self._editor, self._get_value, connect_finish = make_value_editor(
            prop_spec, current_value
        )
        connect_finish(self._emit_changed)

        # Checkbox "visível no canvas"
        self._vis = QCheckBox("exibir", self)
        self._vis.setToolTip(
            "Se marcado, o valor deste parâmetro aparece abaixo do "
            "símbolo no esquemático."
        )
        self._vis.setChecked(current_visible)
        self._vis.toggled.connect(lambda _=None: self._emit_changed())

        # Botão restaurar default
        self._restore = QPushButton("⟲", self)
        self._restore.setMaximumWidth(28)
        self._restore.setToolTip(
            f"Restaurar valor default ({prop_spec.default!r})"
        )
        self._restore.clicked.connect(self._on_restore)

        # v3.1.2 Sub-sprint A — Library link button (visível só se linked)
        self._unlink_btn = QPushButton("🔗", self)
        self._unlink_btn.setMaximumWidth(28)
        self._unlink_btn.clicked.connect(
            lambda: self.unlink_requested.emit(self._index)
        )

        # Layout: [editor] [visible] [⟲] [🔗 if linked]
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self._editor, stretch=1)
        lay.addWidget(self._vis)
        lay.addWidget(self._restore)
        lay.addWidget(self._unlink_btn)

        # Tooltip combinado (descrição + exemplo) no editor
        tip_parts: list[str] = []
        if prop_spec.description:
            tip_parts.append(prop_spec.description)
        if prop_spec.example is not None:
            tip_parts.append(f"Exemplo: {prop_spec.example}")
        if tip_parts:
            self._editor.setToolTip("\n\n".join(tip_parts))

        # v3.1.2 Sub-sprint A — apply linked-library visual state
        self._apply_linked_state()

    def _apply_linked_state(self) -> None:
        """Apply gray-out + read-only state if linked_library is set.

        Per PTW Tutorial §Part 1 p.55: linked properties show as gray-out
        + cannot be edited. User must click "🔗" to unlink first.
        """
        is_linked = self._linked_library is not None
        # Editor: enabled iff not linked
        self._editor.setEnabled(not is_linked)
        # Visible checkbox: also disabled when linked (não controla um valor próprio)
        self._vis.setEnabled(not is_linked)
        # Restore button hidden when linked (não tem default próprio)
        self._restore.setVisible(not is_linked)
        # Unlink button only visible when linked
        self._unlink_btn.setVisible(is_linked)
        if is_linked:
            self._unlink_btn.setToolTip(
                f"Vinculado à library: {self._linked_library}\n"
                f"Click para desvincular e editar manualmente."
            )
            # Visual hint: light gray background on editor
            self._editor.setStyleSheet(
                "QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { "
                "background-color: #e8e8e8; color: #707070; }"
            )
        else:
            self._editor.setStyleSheet("")

    def set_linked_library(self, library: Optional[str]) -> None:
        """Update the linked_library state and re-apply visual.

        Call this when the link is added/removed dynamically (e.g., user
        clicks Unlink → caller sets to None and refreshes).
        """
        self._linked_library = library
        self._apply_linked_state()

    @property
    def linked_library(self) -> Optional[str]:
        """Current linked library identifier or None if unlinked."""
        return self._linked_library

    @property
    def label_text(self) -> str:
        """Label formatado: 'Label [unit]' ou só 'Label'."""
        if self._spec.unit:
            return f"{self._spec.label} [{self._spec.unit}]"
        return self._spec.label

    def get_value(self) -> str:
        """Valor atual como string (compatível com PpProperty.value)."""
        return self._get_value()

    def is_visible_on_canvas(self) -> bool:
        """Estado do checkbox 'exibir'."""
        return self._vis.isChecked()

    def _emit_changed(self) -> None:
        try:
            v = self.get_value()
        except (ValueError, TypeError):
            # widget em estado inválido — não emite
            return
        self.value_changed.emit(self._index, v, self._vis.isChecked())

    def _on_restore(self) -> None:
        """Reseta o editor para o default do spec."""
        default_str = str(self._spec.default) if self._spec.default is not None else ""
        # Recria o editor — mais simples que tentar setValue genérico
        self._replace_editor_with_default(default_str)
        self._vis.setChecked(self._spec.visible)
        self._emit_changed()

    def _replace_editor_with_default(self, default_str: str) -> None:
        """Substitui o widget editor in-place com um novo inicializado com default."""
        lay = self.layout()
        # Remove e destroi o editor antigo
        lay.removeWidget(self._editor)
        self._editor.deleteLater()
        # Cria novo
        self._editor, self._get_value, connect_finish = make_value_editor(
            self._spec, default_str
        )
        connect_finish(self._emit_changed)
        if self._spec.description or self._spec.example is not None:
            parts = []
            if self._spec.description:
                parts.append(self._spec.description)
            if self._spec.example is not None:
                parts.append(f"Exemplo: {self._spec.example}")
            self._editor.setToolTip("\n\n".join(parts))
        lay.insertWidget(0, self._editor, stretch=1)


# ---------------------------------------------------------------------------
# PropertyGroupBox: várias PropertyRow agrupadas por PropertyGroup
# ---------------------------------------------------------------------------


_GROUP_LABELS: dict[PropertyGroup, str] = {
    PropertyGroup.MAIN:        "Principal",
    PropertyGroup.TIMING:      "Timing",
    PropertyGroup.ELECTRICAL:  "Elétrico",
    PropertyGroup.THERMAL:     "Térmico",
    PropertyGroup.NONLINEAR:   "Não-linear",
    PropertyGroup.REIGNITION:  "Reignição",
    PropertyGroup.GEOMETRY:    "Geometria",
    PropertyGroup.ADVANCED:    "Avançado",
    PropertyGroup.METADATA:    "Metadata",
}


# Grupos que começam RECOLHIDOS por default — reduz poluição visual em
# componentes com muitos parâmetros secundários. Usuário pode expandir
# clicando no título.
_DEFAULT_COLLAPSED_GROUPS: frozenset[PropertyGroup] = frozenset({
    PropertyGroup.ADVANCED,
    PropertyGroup.METADATA,
})


class PropertyGroupBox(QGroupBox):
    """
    QGroupBox com todas as PropertyRow de um mesmo PropertyGroup.

    v0.22.3: é **checkable/colapsível**. Clique no título expande ou
    recolhe o conteúdo. Grupos ``ADVANCED`` e ``METADATA`` iniciam
    recolhidos (reduzem poluição visual quando há muitos parâmetros
    secundários — ex: T_bounce, U0_dielec, didt_sigma no VCB).

    Emite ``row_changed(index, value, visible)`` propagando o sinal
    de cada row filha.
    """

    row_changed = Signal(int, str, bool)

    def __init__(
        self,
        group: PropertyGroup,
        rows: list[PropertyRow],
        parent: Optional[QWidget] = None,
        *,
        collapsed: Optional[bool] = None,
    ) -> None:
        """
        Parameters
        ----------
        group:
            O PropertyGroup identificador — usado para o label e o
            default de collapsed.
        rows:
            Lista de PropertyRow a incluir no formulário interno.
        parent:
            Parent widget (típico: QWidget do painel).
        collapsed:
            Se True, começa recolhido; False, expandido; None (default),
            usa o padrão — ``True`` para ``ADVANCED``/``METADATA``,
            ``False`` para os outros.
        """
        title = _GROUP_LABELS.get(group, group.value.title())
        super().__init__(title, parent)
        self._group = group

        # Checkable — o "check" representa "expandido" (checked=True =
        # expandido; checked=False = recolhido).
        self.setCheckable(True)

        # Content widget — containerizado para permitir hide/show sem
        # perder o layout interno.
        self._content = QWidget(self)
        form = QFormLayout(self._content)
        form.setContentsMargins(8, 8, 8, 8)
        form.setSpacing(4)
        for row in rows:
            row.value_changed.connect(self._on_row_changed)
            form.addRow(row.label_text + ":", row)

        # Layout externo que apenas "hospeda" o content. Usamos QVBoxLayout
        # em vez de QFormLayout aqui para que o content widget seja um
        # único filho que podemos esconder.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._content)

        # Estado inicial
        if collapsed is None:
            collapsed = group in _DEFAULT_COLLAPSED_GROUPS
        self.setChecked(not collapsed)  # checked=True → expandido
        self._content.setVisible(not collapsed)

        # Liga toggle → show/hide do content
        self.toggled.connect(self._content.setVisible)

    @property
    def group(self) -> PropertyGroup:
        return self._group

    def is_expanded(self) -> bool:
        """True se o groupbox está expandido (check = True)."""
        return self.isChecked()

    def _on_row_changed(self, index: int, value: str, visible: bool) -> None:
        self.row_changed.emit(index, value, visible)


# ---------------------------------------------------------------------------
# build_property_rows: helper para construir PropertyRows a partir de um
# componente + seu spec
# ---------------------------------------------------------------------------


def build_property_rows(
    spec: ComponentSpec,
    component: PpComponent,
    parent: Optional[QWidget] = None,
) -> dict[PropertyGroup, list[PropertyRow]]:
    """
    Retorna {group → [PropertyRow, ...]} já construídos.

    Itera ``spec.properties`` em ordem. Para cada um, lê o valor atual
    em ``component.properties[i].value`` (ou default do spec se o
    componente tem menos props que o spec — migração de versão antiga).
    """
    by_group: dict[PropertyGroup, list[PropertyRow]] = {}
    for idx, prop_spec in enumerate(spec.properties):
        # Pega valor atual do componente (fallback para default do spec)
        if idx < len(component.properties):
            cur_value = component.properties[idx].value
            cur_visible = component.properties[idx].visible
            # v3.2.0: propaga linked_library do PpProperty (v3.1.1) para
            # o PropertyRow (UI gray-out v3.1.2). Antes da v3.2.0 isto
            # estava desconectado — backend tinha o flag mas UI ignorava.
            cur_linked = component.properties[idx].linked_library
        else:
            cur_value = (
                str(prop_spec.default) if prop_spec.default is not None else ""
            )
            cur_visible = prop_spec.visible
            cur_linked = None
        row = PropertyRow(
            idx, prop_spec, cur_value, cur_visible, parent,
            linked_library=cur_linked,
        )
        by_group.setdefault(prop_spec.group, []).append(row)
    return by_group


# ---------------------------------------------------------------------------
# ComponentPropertyDialog: modal ATPDraw-style (tabs Parâmetros/Descrição)
# ---------------------------------------------------------------------------


# PTW Tutorial §Part 1 p.52-60 ordem canônica de tabs no Component Editor.
# Cada PropertyGroup é uma tab separada. Mantém ADVANCED + METADATA por
# último (default colapsados). Tab "Descrição" sempre por último.
_TAB_ORDER: tuple[PropertyGroup, ...] = (
    PropertyGroup.MAIN,
    PropertyGroup.ELECTRICAL,
    PropertyGroup.NONLINEAR,
    PropertyGroup.GEOMETRY,
    PropertyGroup.TIMING,
    PropertyGroup.REIGNITION,
    PropertyGroup.THERMAL,
    PropertyGroup.ADVANCED,
    PropertyGroup.METADATA,
)

# Ícones unicode-only para legibilidade visual das tabs (sem assets externos).
# Cada PropertyGroup tem um ícone canônico (PTW-style mapping).
_TAB_ICON: dict[PropertyGroup, str] = {
    PropertyGroup.MAIN:        "📋",  # principal
    PropertyGroup.ELECTRICAL:  "⚡",  # elétrico
    PropertyGroup.NONLINEAR:   "📈",  # não-linear
    PropertyGroup.GEOMETRY:    "📐",  # geometria
    PropertyGroup.TIMING:      "⏱",  # timing
    PropertyGroup.REIGNITION:  "🔥",  # reignição
    PropertyGroup.THERMAL:     "🌡",  # térmico
    PropertyGroup.ADVANCED:    "⚙",  # avançado
    PropertyGroup.METADATA:    "🏷",  # metadata
}


class ComponentPropertyDialog(QDialog):
    """
    v3.2.0 Component Editor multipanel — paridade PTW Tutorial §Part 1 p.52-60.

    Dialog modal com **uma tab por PropertyGroup** (em vez do single-tab
    "Parâmetros"+"Descrição" pré-v3.2.0). Cada tab mostra apenas as
    properties do grupo correspondente, organizadas em PropertyGroupBox.

    Tabs visíveis:
    - 📋 Principal (MAIN) — sempre visível (mesmo se vazio)
    - ⚡ Elétrico (ELECTRICAL) — só se há props elétricas
    - 📈 Não-linear (NONLINEAR), 📐 Geometria, ⏱ Timing, 🔥 Reignição,
      🌡 Térmico, ⚙ Avançado, 🏷 Metadata — só se há props no grupo
    - 📄 Descrição — sempre visível (description + llm_hints)

    Tabs sem properties NÃO são adicionadas (clean UX). PropertyGroup MAIN
    é mostrada mesmo se vazio (ancora visual).

    v3.2.0 backward-compat: API pública (signal `property_changed`,
    constructor) preservada. Apenas rendering interno mudou.

    References
    ----------
    PTW Tutorial v8.0 §Part 1 p.52-60 (Component Editor with subviews).
    """

    property_changed = Signal(int, str, bool)

    def __init__(
        self,
        spec: ComponentSpec,
        component: PpComponent,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            f"{spec.label_pt} — {component.name or component.type}"
        )
        self.resize(560, 640)

        self._spec = spec
        self._component = component

        root = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget(self)
        tabs.setDocumentMode(True)  # cleaner look (PTW-style)
        # Track tabs created (for tests + 7ª garantia verification)
        self._tabs = tabs
        self._created_tabs: list[str] = []

        # v3.2.0: build all property rows once, then split per group
        groups = build_property_rows(spec, component, self)

        # ── One tab per PropertyGroup (canonical order) ─────────────
        for group in _TAB_ORDER:
            rows = groups.get(group)
            # MAIN tab always shown (even empty); others only if non-empty
            if not rows and group != PropertyGroup.MAIN:
                continue
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            tab_layout.setContentsMargins(8, 8, 8, 8)
            tab_layout.setSpacing(8)
            if rows:
                box = PropertyGroupBox(group, rows, parent=tab_widget)
                box.row_changed.connect(self._on_row_changed)
                tab_layout.addWidget(box)
            else:
                # Empty MAIN tab — show placeholder
                placeholder = QLabel(
                    "<i>Nenhuma propriedade neste grupo.</i>",
                    tab_widget,
                )
                placeholder.setTextFormat(Qt.RichText)
                tab_layout.addWidget(placeholder)
            tab_layout.addStretch(1)

            icon = _TAB_ICON.get(group, "")
            label = _GROUP_LABELS.get(group, group.value.title())
            tab_title = f"{icon} {label}".strip()
            tabs.addTab(tab_widget, tab_title)
            self._created_tabs.append(tab_title)

        # ── Last tab: Descrição (always present) ─────────────────────
        desc_tab = QWidget()
        desc_layout = QVBoxLayout(desc_tab)
        desc_layout.setContentsMargins(8, 8, 8, 8)

        desc_text = QTextEdit()
        desc_text.setReadOnly(True)
        desc_text.setHtml(self._build_description_html())
        desc_layout.addWidget(desc_text)
        tabs.addTab(desc_tab, "📄 Descrição")
        self._created_tabs.append("📄 Descrição")

        # ── Datablock tab if component has datablocks ────────────────
        # v3.2.0 Sprint 3 — integração visual de datablocks anexados.
        # Lazy import (PpDataBlock) — datablocks vivem no PpProject,
        # não no ComponentSpec. Lookup feito no caller (editor.py)
        # via `_attach_datablock_tab` API se houver. Por ora, placeholder.

        root.addWidget(tabs)

        # OK / Cancel
        bb = QDialogButtonBox(QDialogButtonBox.Close, self)
        bb.rejected.connect(self.accept)
        bb.accepted.connect(self.accept)
        root.addWidget(bb)

    def _on_row_changed(self, index: int, value: str, visible: bool) -> None:
        # Re-emite imediatamente para o editor tratar via QUndoStack
        self.property_changed.emit(index, value, visible)

    def attach_datablock_tab(self, datablocks: list) -> None:
        """v3.2.0 Sprint 3: add a 📊 Datablock tab listing attached datablocks.

        Caller (editor.py) passes the list of :class:`PpDataBlock` instances
        attached to this component. If the list is empty, no tab is added.

        Per PTW Tutorial §Part 1 p.60-62 (Datablock display Input Data).

        References
        ----------
        PTW Tutorial v8.0 §Part 1 p.60-62.
        """
        if not datablocks:
            return

        db_tab = QWidget()
        db_layout = QVBoxLayout(db_tab)
        db_layout.setContentsMargins(8, 8, 8, 8)

        info = QLabel(
            f"<i>Este componente tem <b>{len(datablocks)}</b> "
            f"datablock(s) anexado(s). Edição via canvas (duplo-clique no datablock).</i>"
        )
        info.setTextFormat(Qt.RichText)
        info.setWordWrap(True)
        db_layout.addWidget(info)

        # List each datablock by its first line (or template if no lines)
        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        lst = QListWidget(db_tab)
        for db in datablocks:
            preview_lines = db.lines or db.template_lines or []
            preview = (preview_lines[0] if preview_lines else "<vazio>")
            if len(preview) > 60:
                preview = preview[:57] + "..."
            n_lines = len(preview_lines)
            item = QListWidgetItem(f"📊  {preview}  ({n_lines} linhas)")
            lst.addItem(item)
        db_layout.addWidget(lst, 1)

        # Insert before "Descrição" tab (which is the last)
        n = self._tabs.count()
        # The Descrição tab is the LAST one we added; insert datablocks
        # immediately before it.
        desc_idx = n - 1
        self._tabs.insertTab(desc_idx, db_tab, "📊 Datablocks")
        # Update tracking
        self._created_tabs.insert(desc_idx, "📊 Datablocks")

    def _build_description_html(self) -> str:
        """Monta um HTML com description + llm_hints para a tab Descrição."""
        s = self._spec
        parts: list[str] = []
        parts.append(f"<h2>{s.label_pt}</h2>")
        parts.append(f"<p><b>Código:</b> <code>{s.code}</code></p>")
        parts.append(f"<p><b>Categoria:</b> {s.category}</p>")
        if s.description:
            parts.append(f"<h3>Descrição</h3><p>{s.description.replace(chr(10), '<br>')}</p>")
        hints = s.llm_hints
        if hints.typical_applications:
            parts.append("<h3>Aplicações típicas</h3><ul>")
            for item in hints.typical_applications:
                parts.append(f"<li>{item}</li>")
            parts.append("</ul>")
        if hints.common_mistakes:
            parts.append("<h3>Erros comuns</h3><ul>")
            for item in hints.common_mistakes:
                parts.append(f"<li>{item}</li>")
            parts.append("</ul>")
        if hints.alternatives:
            parts.append("<h3>Alternativas</h3><ul>")
            for item in hints.alternatives:
                parts.append(f"<li>{item}</li>")
            parts.append("</ul>")
        if hints.references:
            parts.append("<h3>Referências</h3><ul>")
            for item in hints.references:
                parts.append(f"<li>{item}</li>")
            parts.append("</ul>")
        return "".join(parts)


# ---------------------------------------------------------------------------
# Helper público usado por editor.py: resolve o spec de um componente
# ---------------------------------------------------------------------------


def resolve_spec(type_code: str) -> Optional[ComponentSpec]:
    """
    Retorna o ``ComponentSpec`` do registry para ``type_code``, ou
    ``None`` se não houver ``.ocomp`` correspondente (fallback legacy).
    """
    return get_default_registry().get(type_code)
