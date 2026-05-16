"""
app.gui.plugin_marketplace_dialog — UI Marketplace (v1.5.0 Sprint D).

Dialog Qt nativo com 3 tabs:

  Tab 1 — 📦 Instalados:
    Lista de plugins descobertos (builtin + user), com:
    * Status (🟢 enabled / ⚪ disabled)
    * Ações: Enable/Disable, Uninstall (apenas user-installed),
      Detalhes (manifest)

  Tab 2 — 🛒 Disponíveis:
    No MVP v1.5.0, mostra plugins de um catálogo ESTÁTICO embutido
    (futuro: catálogo remoto). Plugins já instalados são filtrados.
    Ação: Install (com confirmação de permissões).

  Tab 3 — ⚙ Configurações:
    Caminhos (builtin_dir, user_dir, project_dir), opções de
    auto-load, links para documentação.

Princípios de UX (paridade PTW + lição v1.4.5):

* Empty states explicativos em cada tab (nunca lista vazia sem
  contexto)
* Ações destrutivas (Uninstall) com QMessageBox de confirmação
* Sem QMessageBox bloqueante em fluxos de teste (usa
  setWindowTitle para feedback de status)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.logging_config import get_logger
from app.plugins.lifecycle import (
    DiscoveredPlugin, LifecycleState, discover_plugins_v2,
)

log = get_logger(__name__)


class PluginMarketplaceDialog(QDialog):
    """
    Marketplace dialog para gerenciar plugins (v1.5.0).

    Constructor não exige parâmetros — popula tudo via discovery
    automática. Estado de lifecycle (enable/disable) persiste em
    ``~/.olivas/plugins/state.json``.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "🧩 Plugin Marketplace — Olivas Power System Studio"
        )
        self.resize(1100, 720)
        self.setMinimumWidth(900)

        # v1.7.0 Sprint A: maximize/minimize controls
        from app.gui.window_state_mixin import enable_window_controls
        enable_window_controls(self, settings_key="plugin_marketplace")

        self._state = LifecycleState()
        self._discovered: list[DiscoveredPlugin] = []

        self._setup_ui()
        self._refresh_discovery()

    # -----------------------------------------------------------------
    # UI build
    # -----------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(
            "<h2>🧩 Plugin Marketplace</h2>"
            "<i>Estenda o Olivas com estudos custom, equipamentos "
            "vendor-specific, exporters e validators.</i>"
        )
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self._build_installed_tab()
        self._build_available_tab()
        self._build_settings_tab()
        layout.addWidget(self.tabs, 1)

        # Action row
        actions = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Atualizar")
        self.btn_refresh.clicked.connect(self._on_refresh)
        actions.addWidget(self.btn_refresh)
        actions.addStretch()

        self.btn_close = QPushButton("Fechar")
        self.btn_close.clicked.connect(self.reject)
        actions.addWidget(self.btn_close)

        layout.addLayout(actions)

    def _build_installed_tab(self) -> None:
        page = QWidget()
        v = QVBoxLayout(page)

        info = QLabel(
            "<b>Plugins descobertos no sistema</b> "
            "(🟢 = enabled, ⚪ = disabled)"
        )
        v.addWidget(info)

        self.installed_list = QListWidget()
        self.installed_list.itemSelectionChanged.connect(
            self._on_installed_selection,
        )
        v.addWidget(self.installed_list, 1)

        # Action buttons row
        btn_row = QHBoxLayout()
        self.btn_enable = QPushButton("✅ Habilitar")
        self.btn_enable.clicked.connect(self._on_enable)
        btn_row.addWidget(self.btn_enable)

        self.btn_disable = QPushButton("⏸ Desabilitar")
        self.btn_disable.clicked.connect(self._on_disable)
        btn_row.addWidget(self.btn_disable)

        self.btn_details = QPushButton("📋 Detalhes")
        self.btn_details.clicked.connect(self._on_details)
        btn_row.addWidget(self.btn_details)

        self.btn_uninstall = QPushButton("🗑 Desinstalar")
        self.btn_uninstall.clicked.connect(self._on_uninstall)
        btn_row.addWidget(self.btn_uninstall)

        btn_row.addStretch()
        v.addLayout(btn_row)

        # Disclaimer
        disclaimer = QLabel(
            "<small><i>⚠ Plugins rodam com seus privilégios. "
            "Habilite apenas plugins de fontes confiáveis. "
            "Builtin plugins são auditados pelo Olivas Team.</i></small>"
        )
        disclaimer.setWordWrap(True)
        v.addWidget(disclaimer)

        self.tabs.addTab(page, "📦 Instalados")

    def _build_available_tab(self) -> None:
        page = QWidget()
        v = QVBoxLayout(page)

        info = QLabel(
            "<b>Plugins disponíveis no catálogo Olivas</b><br>"
            "<small>Catálogo remoto será adicionado em v1.5.1. Por "
            "ora, todos os plugins builtin já estão na aba "
            "'Instalados'.</small>"
        )
        info.setWordWrap(True)
        v.addWidget(info)

        # Empty state — paridade Datablock Reports do PTW (lição v1.4.5)
        empty = QLabel(
            "<center><br><br>"
            "<h3>🛒 Catálogo remoto chegará em v1.5.1</h3>"
            "<p>Hoje, plugins são descobertos automaticamente em:</p>"
            "<ul style='text-align:left;'>"
            "<li><code>app/plugins/builtin/</code> "
            "(shipped com Olivas)</li>"
            "<li><code>~/.olivas/plugins/</code> "
            "(instalados pelo usuário)</li>"
            "<li><code>./plugins/</code> "
            "(plugins do projeto atual)</li>"
            "</ul>"
            "<p>Para criar um plugin, veja "
            "<code>docs/v1.5.0_DESIGN.md</code> §2.</p>"
            "</center>"
        )
        empty.setWordWrap(True)
        empty.setStyleSheet(
            "QLabel { background-color: #FAFAFA; "
            "border: 1px dashed #BDBDBD; padding: 20px; }"
        )
        v.addWidget(empty, 1)

        self.tabs.addTab(page, "🛒 Disponíveis")

    def _build_settings_tab(self) -> None:
        page = QWidget()
        v = QVBoxLayout(page)

        # Plugin paths
        v.addWidget(QLabel("<b>Diretórios de plugins:</b>"))
        builtin_path = (
            Path(__file__).parent.parent / "plugins" / "builtin"
        )
        user_path = Path.home() / ".olivas" / "plugins"
        project_path = Path.cwd() / "plugins"

        for label, path in [
            ("📦 Builtin (read-only)", builtin_path),
            ("👤 Usuário (~/.olivas/plugins/)", user_path),
            ("📁 Projeto atual (./plugins/)", project_path),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{label}</b>:"))
            row.addWidget(QLabel(f"<code>{path}</code>"))
            row.addStretch()
            v.addLayout(row)

        v.addWidget(QLabel("<br>"))

        # Options
        v.addWidget(QLabel("<b>Opções:</b>"))

        self.cb_auto_load = QCheckBox(
            "Carregar plugins habilitados automaticamente no startup"
        )
        self.cb_auto_load.setChecked(True)
        self.cb_auto_load.setEnabled(False)   # MVP: sempre on
        v.addWidget(self.cb_auto_load)

        self.cb_confirm_perms = QCheckBox(
            "Pedir confirmação de permissões antes de habilitar"
        )
        self.cb_confirm_perms.setChecked(True)
        self.cb_confirm_perms.setEnabled(False)   # MVP: sempre on
        v.addWidget(self.cb_confirm_perms)

        v.addWidget(QLabel("<br>"))

        # Stats
        self.stats_label = QLabel()
        v.addWidget(self.stats_label)

        v.addStretch()

        self.tabs.addTab(page, "⚙ Configurações")

    # -----------------------------------------------------------------
    # Discovery + UI population
    # -----------------------------------------------------------------

    def _refresh_discovery(self) -> None:
        """Re-roda discovery e popula a lista de instalados."""
        self._discovered = discover_plugins_v2()
        self.installed_list.clear()
        for d in self._discovered:
            enabled = self._state.is_enabled(d.manifest.name)
            icon = "🟢" if enabled else "⚪"
            source_tag = {
                "builtin": "📦 builtin",
                "installed": "👤 user",
                "project": "📁 project",
            }.get(d.source, d.source)
            text = (
                f"{icon}  {d.manifest.display_name}  "
                f"(v{d.manifest.version})  ·  {source_tag}\n"
                f"    name={d.manifest.name}  ·  "
                f"by {d.manifest.author}  ·  "
                f"{d.manifest.license}\n"
                f"    {d.manifest.description.strip()[:120]}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, d)
            self.installed_list.addItem(item)

        # Stats label
        if hasattr(self, "stats_label"):
            n_total = len(self._discovered)
            n_enabled = sum(
                1 for d in self._discovered
                if self._state.is_enabled(d.manifest.name)
            )
            self.stats_label.setText(
                f"<b>Estatísticas:</b><br>"
                f"Plugins descobertos: {n_total}<br>"
                f"Habilitados: {n_enabled}<br>"
                f"Desabilitados: {n_total - n_enabled}"
            )

    # -----------------------------------------------------------------
    # Slots
    # -----------------------------------------------------------------

    def _on_refresh(self) -> None:
        self._refresh_discovery()
        self.setWindowTitle(
            f"🧩 Plugin Marketplace — {len(self._discovered)} "
            f"plugins descobertos"
        )

    def _selected_plugin(self) -> Optional[DiscoveredPlugin]:
        item = self.installed_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _on_installed_selection(self) -> None:
        """Atualiza enabled/disabled buttons conforme seleção."""
        d = self._selected_plugin()
        has_sel = d is not None
        is_enabled = (
            has_sel and self._state.is_enabled(d.manifest.name)
        )
        is_user = has_sel and d.source == "installed"

        self.btn_enable.setEnabled(has_sel and not is_enabled)
        self.btn_disable.setEnabled(has_sel and is_enabled)
        self.btn_details.setEnabled(has_sel)
        self.btn_uninstall.setEnabled(is_user)

    def _on_enable(self) -> None:
        d = self._selected_plugin()
        if d is None:
            return

        # Confirmação de permissões (MVP: sempre confirma)
        perms_str = (
            ", ".join(p.value for p in d.manifest.permissions)
            or "(nenhuma adicional)"
        )
        ans = QMessageBox.question(
            self,
            f"Habilitar '{d.manifest.display_name}'?",
            f"<b>{d.manifest.display_name}</b> "
            f"v{d.manifest.version}<br>"
            f"<i>by {d.manifest.author} · {d.manifest.license}</i>"
            f"<br><br>"
            f"<b>Permissões solicitadas:</b><br>"
            f"<code>{perms_str}</code><br><br>"
            f"<b>Descrição:</b><br>"
            f"{d.manifest.description}<br><br>"
            f"⚠ Plugins rodam com seus privilégios. "
            f"Confiar e habilitar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return

        self._state.enable(
            d.manifest.name,
            source=d.source,
            approved_permissions=[
                p.value for p in d.manifest.permissions
            ],
        )
        self._state.save()
        self._refresh_discovery()
        self.setWindowTitle(
            f"🧩 Habilitado: {d.manifest.name}"
        )

    def _on_disable(self) -> None:
        d = self._selected_plugin()
        if d is None:
            return
        self._state.disable(d.manifest.name)
        self._state.save()
        self._refresh_discovery()
        self.setWindowTitle(
            f"🧩 Desabilitado: {d.manifest.name}"
        )

    def _on_details(self) -> None:
        d = self._selected_plugin()
        if d is None:
            return
        # Mostra manifest YAML em dialog read-only
        dlg = QDialog(self)
        dlg.setWindowTitle(
            f"Manifest — {d.manifest.display_name}"
        )
        dlg.resize(800, 600)
        v = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("Consolas", 9))
        # Renderiza manifest via Pydantic.model_dump_json
        try:
            content = d.manifest.model_dump_json(indent=2)
        except Exception:
            content = repr(d.manifest)
        text.setPlainText(content)
        v.addWidget(text, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        dlg.exec()

    def _on_uninstall(self) -> None:
        d = self._selected_plugin()
        if d is None:
            return
        if d.source != "installed":
            QMessageBox.warning(
                self, "Não é possível desinstalar",
                f"Plugin '{d.manifest.name}' é {d.source}; "
                f"apenas plugins instalados pelo usuário podem ser "
                f"removidos por aqui.",
            )
            return

        ans = QMessageBox.question(
            self,
            f"Desinstalar '{d.manifest.name}'?",
            f"Remover permanentemente <b>{d.manifest.display_name}</b> "
            f"de <code>{d.plugin_dir}</code>?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return

        from app.plugins.security import uninstall_plugin
        result = uninstall_plugin(
            name=d.manifest.name,
            target_root=d.plugin_dir.parent,
        )
        if result.success:
            self._state.remove(d.manifest.name)
            self._state.save()
            self._refresh_discovery()
            self.setWindowTitle(
                f"🧩 Desinstalado: {d.manifest.name}"
            )
        else:
            QMessageBox.warning(self, "Erro", result.message)
