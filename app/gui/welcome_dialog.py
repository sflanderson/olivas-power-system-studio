"""
app.gui.welcome_dialog — Welcome dialog (empty state) para
o Olivas ATP Studio.

v0.92 — REPOSITIONING: o Olivas é especialista em **análise
elétrica**:

1. Curto-circuito (IEC 60909-0)
2. Fluxo de potência (IEEE 399 Brown Book / Stevenson §9)
3. Coordenação e seletividade (IEEE 242 Buff Book §15)
4. Energia incidente / Arc-flash (NBR 17227 / IEEE 1584)
5. Balanço de carga (IEEE 141 Red Book)

Os relatórios são auditáveis (SHA256 + responsável + normas
+ limitações declaradas) — adequados para ISO 9001 / NR-10.

A integração ATP/EMTP é **secundária e opcional** — apenas
ferramenta de simulação, não o foco do produto.

Layout do dialog:

* Header com 5 análises destacadas (paleta Oliveira).
* Linha de ações (Novo projeto / Abrir .sch / Abrir caso ATP).
* Linha de templates de onboarding rápido.
* Recent files (até 10).
* Checkbox "não mostrar novamente".
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QStyle, QVBoxLayout, QWidget,
)


SETTINGS_KEY_SHOW_WELCOME = "show_welcome"


class _ActionCard(QFrame):
    """Card clicável com ícone, título e descrição."""

    clicked = Signal()

    def __init__(
        self,
        icon_pixmap_role: QStyle.StandardPixmap,
        title: str,
        description: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(120)
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            "QFrame {"
            "  background: #f7f7f9;"
            "  border: 1px solid #cccccc;"
            "  border-radius: 6px;"
            "}"
            "QFrame:hover {"
            "  background: #e6f0fa;"
            "  border: 1px solid #5599cc;"
            "}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        # Ícone
        icon = self.style().standardIcon(icon_pixmap_role)
        pixmap = icon.pixmap(48, 48)
        icon_label = QLabel(self)
        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)

        # Título
        t_label = QLabel(f"<b>{title}</b>", self)
        t_font = QFont()
        t_font.setPointSize(11)
        t_font.setBold(True)
        t_label.setFont(t_font)
        layout.addWidget(t_label)

        # Descrição
        d_label = QLabel(description, self)
        d_label.setWordWrap(True)
        d_label.setStyleSheet("color: #555555;")
        layout.addWidget(d_label, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _TemplateCard(QFrame):
    """
    v0.89: card menor para a fileira "Iniciar com template".

    Diferente de ``_ActionCard``:
    * Sem ícone (espaço dedicado a título + descrição).
    * Tonalidade Oliveira (cream + olive border).
    * Emite ``clicked(template_id: str)`` em vez de
      ``clicked()`` sem argumentos.
    """

    clicked = Signal(str)   # template_id

    def __init__(
        self,
        template_id: str,
        title: str,
        description: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._template_id = template_id
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(96)
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Paleta Oliveira (cream + olive)
        self.setStyleSheet(
            "QFrame {"
            "  background: #FAFAF5;"
            "  border: 1px solid #87A96B;"
            "  border-radius: 6px;"
            "}"
            "QFrame:hover {"
            "  background: #EFF0E8;"
            "  border: 1.5px solid #556B2F;"
            "}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Título (com 📋 emoji discreto)
        t_label = QLabel(f"📋 <b>{title}</b>", self)
        t_font = QFont()
        t_font.setPointSize(10)
        t_font.setBold(True)
        t_label.setFont(t_font)
        layout.addWidget(t_label)

        # Descrição
        d_label = QLabel(description, self)
        d_label.setWordWrap(True)
        d_label.setStyleSheet("color: #5C4D3C; font-size: 9pt;")
        layout.addWidget(d_label, 1)

    @property
    def template_id(self) -> str:
        return self._template_id

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._template_id)
        super().mousePressEvent(event)


class _AnalysisCard(QFrame):
    """
    v0.92: card pequeno para uma das 5 análises especializadas
    no Welcome dialog. Apenas informativo (não navega) — propósito
    é comunicar o foco do produto ao usuário recém-chegado.

    Paleta Oliveira (cream + olive). Largura mais estreita
    que ``_ActionCard`` para caber 5 numa linha.
    """

    def __init__(
        self,
        emoji: str,
        title: str,
        norm: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(78)
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            "QFrame {"
            "  background: #EFF0E8;"
            "  border: 1px solid #87A96B;"
            "  border-left: 4px solid #556B2F;"
            "  border-radius: 4px;"
            "}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        title_lbl = QLabel(f"{emoji} <b>{title}</b>", self)
        title_lbl.setStyleSheet("color:#2A2D24; font-size:10pt;")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        norm_lbl = QLabel(f"<i>{norm}</i>", self)
        norm_lbl.setStyleSheet("color:#5C4D3C; font-size:8pt;")
        norm_lbl.setWordWrap(True)
        layout.addWidget(norm_lbl, 1)


class WelcomeDialog(QDialog):
    """
    Welcome dialog com cards de ação + recent files.

    Uso:

    ::

        from app.gui.welcome_dialog import WelcomeDialog
        dlg = WelcomeDialog(parent, recent_files=...)
        dlg.open_atp_requested.connect(handler)
        dlg.open_sch_requested.connect(handler)
        dlg.new_pp_requested.connect(handler)
        dlg.recent_clicked.connect(handler)
        dlg.exec()
    """

    open_atp_requested = Signal()
    open_sch_requested = Signal()
    new_pp_requested = Signal()
    recent_clicked = Signal(str)    # path
    # v0.89: usuário clicou num template card. Argumento: template_id.
    template_requested = Signal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        recent_files: Optional[List[str]] = None,
    ) -> None:
        super().__init__(parent)
        # v0.92.2 — Brand: "Olivas Power System Studio"
        self.setWindowTitle(
            "Bem-vindo ao Olivas Power System Studio",
        )
        self.setModal(True)
        self.resize(880, 720)

        layout = QVBoxLayout(self)

        # Header (v0.92.2 — repositioning + rebrand)
        header = QLabel(
            "<h2 style='color:#556B2F;margin:0;'>"
            "Olivas Power System Studio</h2>"
            "<p style='color:#5C4D3C;margin:4px 0 0 0;font-size:11pt;'>"
            "<b>Software profissional de análise elétrica</b> "
            "— alternativa nacional a SKM PTW / ETAP / EasyPower. "
            "Laudos auditáveis (ISO 9001 / NR-10) com "
            "rastreabilidade total norma → resultado."
            "</p>",
            self,
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # v0.92: bloco com as 5 análises especializadas (destaque)
        self._add_analyses_section(layout)

        # Cards de ações (criação de projeto / abertura de arquivo)
        actions_label = QLabel(
            "<b>🗂  Iniciar trabalho</b>", self,
        )
        actions_label.setStyleSheet("color:#556B2F;margin-top:6px;")
        layout.addWidget(actions_label)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        # v0.92.1 — apenas 2 cards primários. Card "Abrir caso
        # ATP" foi REMOVIDO: a integração ATP foi desvinculada
        # do app principal nesta versão.
        card_new = _ActionCard(
            QStyle.SP_FileDialogNewFolder,
            "Novo projeto",
            "Criar unifilar vazio. Adicione barramentos, "
            "transformadores, motores e fontes para análise.",
            self,
        )
        card_new.clicked.connect(self._on_new_pp)
        cards_row.addWidget(card_new, 1)

        card_sch = _ActionCard(
            QStyle.SP_FileDialogContentsView,
            "Abrir esquemático (.sch)",
            "Editor visual de unifilar elétrico. Componentes "
            "drag-and-drop com auto-validação NBR/IEC.",
            self,
        )
        card_sch.clicked.connect(self._on_open_sch)
        cards_row.addWidget(card_sch, 1)

        layout.addLayout(cards_row)

        # v0.89: cards de templates (segunda linha) — onboarding
        # rápido para o usuário ver algo funcional sem construir
        # do zero.
        self._add_templates_section(layout)

        # Recent files
        if recent_files:
            layout.addSpacing(10)
            recent_label = QLabel("<b>Arquivos recentes:</b>", self)
            layout.addWidget(recent_label)
            self.recent_list = QListWidget(self)
            self.recent_list.setMaximumHeight(180)
            for path in recent_files:
                item = QListWidgetItem(Path(path).name, self.recent_list)
                item.setData(Qt.UserRole, path)
                item.setToolTip(path)
                self.recent_list.addItem(item)
            self.recent_list.itemDoubleClicked.connect(
                self._on_recent_double_clicked,
            )
            layout.addWidget(self.recent_list, 1)
        else:
            layout.addStretch(1)

        # Footer com checkbox + Close
        footer = QHBoxLayout()
        self.cb_dont_show = QCheckBox(
            "Não mostrar novamente ao iniciar", self,
        )
        footer.addWidget(self.cb_dont_show)
        footer.addStretch(1)
        btn_close = QPushButton("Fechar", self)
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        layout.addLayout(footer)

    def _on_open_atp(self) -> None:
        self.open_atp_requested.emit()
        self.accept()

    def _on_open_sch(self) -> None:
        self.open_sch_requested.emit()
        self.accept()

    def _on_new_pp(self) -> None:
        self.new_pp_requested.emit()
        self.accept()

    def _on_recent_double_clicked(
        self, item: QListWidgetItem,
    ) -> None:
        path = item.data(Qt.UserRole)
        if path:
            self.recent_clicked.emit(path)
            self.accept()

    # ---- Análises (v0.92) — 5 estudos especializados ------------------

    def _add_analyses_section(self, layout: QVBoxLayout) -> None:
        """
        v0.92: bloco principal do welcome — comunica que o
        Olivas é especialista em análise elétrica. Os 5 estudos
        são apresentados com norma de referência.

        Cards são meramente informativos (não navegam).
        Acesso real às análises via menu **Análise →** (após
        criar/abrir projeto).
        """
        layout.addSpacing(8)
        section_label = QLabel(
            "<b style='color:#556B2F;'>🔬 Análises especializadas</b>"
            " <span style='color:#5C4D3C;font-size:9pt;'>"
            "(disponíveis no menu <b>Análise</b> após carregar projeto)"
            "</span>", self,
        )
        layout.addWidget(section_label)

        analyses = [
            ("⚡", "Curto-circuito",
             "IEC 60909-0:2016"),
            ("🔌", "Fluxo de potência",
             "IEEE 399 / Stevenson §9"),
            ("🛡️", "Coordenação e seletividade",
             "IEEE 242 Buff Book §15"),
            ("🔥", "Energia incidente / Arc-flash",
             "ABNT NBR 17227:2025 / IEEE 1584-2018"),
            ("📈", "Balanço de carga",
             "IEEE 141 Red Book"),
            ("🔍", "Saturação de TC",
             "IEEE C57.13.1 / IEC 61869-2 / CIGRÉ"),
        ]

        analyses_row = QHBoxLayout()
        analyses_row.setSpacing(8)
        for emoji, title, norm in analyses:
            card = _AnalysisCard(emoji, title, norm, self)
            analyses_row.addWidget(card, 1)
        layout.addLayout(analyses_row)

        # Audit trail tagline
        audit_tag = QLabel(
            "<i style='color:#7E2BA8;font-size:9pt;'>"
            "Todos os relatórios incluem audit trail "
            "(SHA256 + responsável técnico + citações + "
            "limitações declaradas) — adequados para auditorias "
            "ISO 9001 / NR-10 e defesa técnica em tribunais."
            "</i>", self,
        )
        audit_tag.setWordWrap(True)
        audit_tag.setStyleSheet(
            "padding: 6px 10px; background: #FAFAF5; "
            "border-left: 3px solid #7E2BA8; "
            "margin: 4px 0;"
        )
        layout.addWidget(audit_tag)

    # ---- Templates (v0.89) ------------------------------------------------

    def _add_templates_section(self, layout: QVBoxLayout) -> None:
        """
        v0.89: seção 'Iniciar com template' — cards menores,
        em uma linha. Cada card emite ``template_requested(id)``.

        Templates carregados de :mod:`app.preprocessor.templates`
        (lazy import — evita ciclo + permite o módulo ser
        opcional em testes).
        """
        try:
            from app.preprocessor.templates import TEMPLATES
        except ImportError:
            return
        layout.addSpacing(14)
        section_label = QLabel(
            "<b>📋 Iniciar com template</b>", self,
        )
        layout.addWidget(section_label)
        hint = QLabel(
            "<i>Clique para abrir um esquemático funcional pré-pronto. "
            "Útil para experimentar análises sem montar do zero.</i>",
            self,
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555;")
        layout.addWidget(hint)

        templates_row = QHBoxLayout()
        templates_row.setSpacing(10)
        for tid, label_pt, description, _builder in TEMPLATES:
            card = _TemplateCard(tid, label_pt, description, self)
            card.clicked.connect(self._on_template_clicked)
            templates_row.addWidget(card, 1)
        layout.addLayout(templates_row)

    def _on_template_clicked(self, template_id: str) -> None:
        self.template_requested.emit(template_id)
        self.accept()

    @property
    def dont_show_again(self) -> bool:
        return self.cb_dont_show.isChecked()


def should_show_welcome(settings: QSettings) -> bool:
    """
    Lê QSettings para saber se o welcome deve aparecer.
    Retorna True se ainda não foi suprimido pelo usuário.
    """
    val = settings.value(SETTINGS_KEY_SHOW_WELCOME, "true")
    if isinstance(val, bool):
        return val
    return str(val).lower() not in ("false", "0", "no")


def remember_dont_show(settings: QSettings) -> None:
    settings.setValue(SETTINGS_KEY_SHOW_WELCOME, "false")
