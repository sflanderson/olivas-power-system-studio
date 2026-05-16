"""Theme definitions for Olivas ATP Studio.

Provides dark and light QSS stylesheets and color palettes for
consistent theming across all widgets.

v0.83 — Brand palette "Oliveira"
=================================

Cores extraídas do logo + inspiração olive tree:

* LIME_BRIGHT (#BFFF00)  — Logo "Olivas" outline
* CYAN_BRIGHT (#00A8E8)  — Logo "Olivas" inner
* PURPLE_DEEP (#7E2BA8)  — Logo "ATP"
* OLIVE_DEEP (#556B2F)   — Olive leaf dark
* OLIVE_MEDIUM (#6B8E23) — Olive grove
* OLIVE_LIGHT (#87A96B)  — Young leaf
* OLIVE_PALE (#B5D4A8)   — Logo branch tone
* OLIVE_CREAM (#FAFAF5)  — Logo background
* OLIVE_BARK (#5C4D3C)   — Warm brown
"""
from __future__ import annotations

from PySide6.QtGui import QColor

# ======================================================================
# Brand palette "Oliveira" (v0.83)
# ======================================================================

# Logo colors (from app/resources/logo.png)
LIME_BRIGHT = "#BFFF00"
CYAN_BRIGHT = "#00A8E8"
PURPLE_DEEP = "#7E2BA8"
PURPLE_LIGHT = "#9B59B6"

# Olive tree natural palette
OLIVE_DEEP = "#556B2F"
OLIVE_MEDIUM = "#6B8E23"
OLIVE_LIGHT = "#87A96B"
OLIVE_PALE = "#B5D4A8"
OLIVE_CREAM = "#FAFAF5"
OLIVE_BARK = "#5C4D3C"
OLIVE_GOLD = "#D4AF37"   # azeitona madura

# Semantic shared accents (re-mapped to brand)
# Mantém nomes antigos para compat — agora apontam à paleta
# Oliveira.
ACCENT_BLUE = CYAN_BRIGHT          # antes: "#4fc3f7"
ACCENT_GREEN = OLIVE_LIGHT         # antes: "#81c784"
ACCENT_ORANGE = OLIVE_GOLD         # antes: "#ffb74d"
ACCENT_RED = "#C62828"             # mantém — vermelho para erro
ACCENT_PURPLE = PURPLE_LIGHT       # antes: "#ce93d8"
ACCENT_OLIVE = OLIVE_MEDIUM        # novo

# -- Dark palette ("Oliveira Dark" — bark + leaf accent) --
# v0.83: tema escuro com toques sutis das cores da marca para
# elementos interativos (selection, links, accent buttons).
DARK = {
    "bg": "#1c1f1a",            # quase-preto com tom oliveira
    "bg_alt": "#252820",         # painéis/listas
    "bg_panel": "#22251f",       # toolbar/menu
    "bg_input": "#2d3127",
    "fg": "#e8e6db",             # cream apagado
    "fg_dim": "#8a8d80",
    "fg_bright": "#ffffff",
    "border": "#4a4d3f",         # olive bark muted
    "selection_bg": "#556B2F",   # OLIVE_DEEP
    "selection_fg": "#ffffff",
    "header_bg": "#2d3127",
    # Validation
    "val_error": "#ef5350",
    "val_warning": "#D4AF37",    # OLIVE_GOLD
    "val_info": "#00A8E8",       # CYAN_BRIGHT (logo)
    # Topology
    "topo_bg": "#1c1f1a",
    "topo_text": "#e8e6db",
    "topo_node": "#00A8E8",      # CYAN_BRIGHT
    "topo_node_source": "#D4AF37",  # GOLD
    "topo_node_model": "#87A96B",   # OLIVE_LIGHT
    "topo_edge_branch": "#B5D4A8",  # OLIVE_PALE
    "topo_edge_switch": "#e57373",
    "topo_edge_snubber": "#9B59B6",  # PURPLE_LIGHT
    # Chat
    "chat_user": "#00A8E8",
    "chat_agent": "#e8e6db",
    "chat_system": "#87A96B",
    "chat_tool": "#D4AF37",
    # Compare
    "cmp_header": "#BFFF00",     # LIME_BRIGHT
    "cmp_model_data": "#9B59B6",
    "cmp_use_data": "#D4AF37",
    "cmp_component": "#87A96B",
    "cmp_default": "#e8e6db",
    "cmp_diff_a": "#ef5350",
    "cmp_diff_b": "#87A96B",
    # Matplotlib
    "mpl_face": "#1c1f1a",
    "mpl_axes": "#252820",
    "mpl_text": "#cccccc",
    "mpl_title": "#e8e6db",
    "mpl_spine": "#4a4d3f",
    "mpl_grid": "#3a3d30",
    "mpl_legend_face": "#2d3127",
    "mpl_legend_edge": "#4a4d3f",
}

# -- Light palette ("Oliveira Light" — cream + olive accents) --
# v0.83: tons cream/oliveira, alto contraste profissional para
# uso industrial em ambiente bem iluminado. Inspirado no fundo
# do logo (cream off-white).
LIGHT = {
    "bg": "#FAFAF5",            # OLIVE_CREAM (logo bg)
    "bg_alt": "#ffffff",         # branco puro para tabelas
    "bg_panel": "#EFF0E8",       # cream-sage muito sutil
    "bg_input": "#ffffff",
    "fg": "#2A2D24",             # quase-preto warm
    "fg_dim": "#5C4D3C",         # OLIVE_BARK
    "fg_bright": "#000000",
    "border": "#B5D4A8",         # OLIVE_PALE — borda suave brand
    "selection_bg": "#556B2F",   # OLIVE_DEEP
    "selection_fg": "#ffffff",
    "header_bg": "#E5EBDA",      # cream-sage para header
    # Validation
    "val_error": "#C62828",
    "val_warning": "#A77B00",    # gold escurecido para LM legível
    "val_info": "#0077B5",       # cyan escurecido para LM legível
    # Topology
    "topo_bg": "#FAFAF5",
    "topo_text": "#2A2D24",
    "topo_node": "#0077B5",      # cyan logo (escurecido)
    "topo_node_source": "#A77B00",
    "topo_node_model": "#556B2F",  # OLIVE_DEEP
    "topo_edge_branch": "#5C4D3C",  # OLIVE_BARK
    "topo_edge_switch": "#C62828",
    "topo_edge_snubber": "#7E2BA8",  # PURPLE_DEEP (logo)
    # Chat
    "chat_user": "#0077B5",
    "chat_agent": "#2A2D24",
    "chat_system": "#556B2F",
    "chat_tool": "#A77B00",
    # Compare
    "cmp_header": "#7E2BA8",     # PURPLE_DEEP (logo)
    "cmp_model_data": "#7E2BA8",
    "cmp_use_data": "#A77B00",
    "cmp_component": "#556B2F",
    "cmp_default": "#2A2D24",
    "cmp_diff_a": "#C62828",
    "cmp_diff_b": "#556B2F",
    # Matplotlib
    "mpl_face": "#FAFAF5",
    "mpl_axes": "#ffffff",
    "mpl_text": "#333333",
    "mpl_title": "#2A2D24",
    "mpl_spine": "#B5D4A8",
    "mpl_grid": "#E5EBDA",
    "mpl_legend_face": "#ffffff",
    "mpl_legend_edge": "#B5D4A8",
}


def get_palette(dark: bool = True) -> dict[str, str]:
    """Return the color palette dict for the given theme."""
    return DARK if dark else LIGHT


def get_qcolor(palette: dict[str, str], key: str) -> QColor:
    """Return a QColor from the palette."""
    return QColor(palette[key])


# ======================================================================
# QSS Stylesheets
# ======================================================================

def _build_qss(p: dict[str, str]) -> str:
    """Build a full QSS stylesheet from a palette dict."""
    return f"""
/* ---- Global ---- */
QMainWindow, QDialog {{
    background-color: {p['bg']};
    color: {p['fg']};
}}

QWidget {{
    background-color: {p['bg']};
    color: {p['fg']};
}}

/* ---- Menu ---- */
QMenuBar {{
    background-color: {p['bg_panel']};
    color: {p['fg']};
    border-bottom: 1px solid {p['border']};
}}
QMenuBar::item:selected {{
    background-color: {p['selection_bg']};
    color: {p['selection_fg']};
}}
QMenu {{
    background-color: {p['bg_panel']};
    color: {p['fg']};
    border: 1px solid {p['border']};
}}
QMenu::item:selected {{
    background-color: {p['selection_bg']};
    color: {p['selection_fg']};
}}

/* ---- Tabs ---- */
QTabWidget::pane {{
    border: 1px solid {p['border']};
    background-color: {p['bg']};
}}
QTabBar::tab {{
    background-color: {p['bg_panel']};
    color: {p['fg']};
    padding: 6px 14px;
    border: 1px solid {p['border']};
    border-bottom: none;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {p['bg']};
    color: {p['fg_bright']};
    border-bottom: 2px solid {p['selection_bg']};
}}
QTabBar::tab:hover {{
    background-color: {p['bg_alt']};
}}

/* ---- Tree ---- */
QTreeWidget {{
    background-color: {p['bg_alt']};
    color: {p['fg']};
    border: 1px solid {p['border']};
    alternate-background-color: {p['bg']};
}}
QTreeWidget::item:selected {{
    background-color: {p['selection_bg']};
    color: {p['selection_fg']};
}}

/* ---- List ---- */
QListWidget {{
    background-color: {p['bg_alt']};
    color: {p['fg']};
    border: 1px solid {p['border']};
}}
QListWidget::item:selected {{
    background-color: {p['selection_bg']};
    color: {p['selection_fg']};
}}

/* ---- Table ---- */
QTableWidget {{
    background-color: {p['bg_alt']};
    color: {p['fg']};
    gridline-color: {p['border']};
    border: 1px solid {p['border']};
}}
QTableWidget::item:selected {{
    background-color: {p['selection_bg']};
    color: {p['selection_fg']};
}}
QHeaderView::section {{
    background-color: {p['header_bg']};
    color: {p['fg']};
    padding: 4px;
    border: 1px solid {p['border']};
}}

/* ---- Text editors ---- */
QPlainTextEdit, QTextEdit {{
    background-color: {p['bg_alt']};
    color: {p['fg']};
    border: 1px solid {p['border']};
    selection-background-color: {p['selection_bg']};
    selection-color: {p['selection_fg']};
}}

/* ---- Input ---- */
QLineEdit {{
    background-color: {p['bg_input']};
    color: {p['fg']};
    border: 1px solid {p['border']};
    padding: 4px;
}}
QLineEdit:focus {{
    border: 1px solid {p['selection_bg']};
}}

/* ---- Combo ---- */
QComboBox {{
    background-color: {p['bg_input']};
    color: {p['fg']};
    border: 1px solid {p['border']};
    padding: 4px;
}}
QComboBox:hover {{
    border: 1px solid {p['selection_bg']};
}}
QComboBox QAbstractItemView {{
    background-color: {p['bg_alt']};
    color: {p['fg']};
    selection-background-color: {p['selection_bg']};
    selection-color: {p['selection_fg']};
}}

/* ---- Buttons ---- */
QPushButton {{
    background-color: {p['bg_panel']};
    color: {p['fg']};
    border: 1px solid {p['border']};
    padding: 5px 12px;
    border-radius: 3px;
}}
QPushButton:hover {{
    background-color: {p['bg_alt']};
    border: 1px solid {p['selection_bg']};
}}
QPushButton:pressed {{
    background-color: {p['selection_bg']};
    color: {p['selection_fg']};
}}

/* ---- GroupBox ---- */
QGroupBox {{
    color: {p['fg']};
    border: 1px solid {p['border']};
    margin-top: 8px;
    padding-top: 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 4px;
    color: {p['fg_bright']};
}}

/* ---- Splitter ---- */
QSplitter::handle {{
    background-color: {p['border']};
}}

/* ---- Status bar ---- */
QStatusBar {{
    background-color: {p['bg_panel']};
    color: {p['fg']};
    border-top: 1px solid {p['border']};
}}

/* ---- Scrollbar ---- */
QScrollBar:vertical {{
    background-color: {p['bg']};
    width: 12px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {p['border']};
    min-height: 20px;
    border-radius: 4px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {p['fg_dim']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {p['bg']};
    height: 12px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {p['border']};
    min-width: 20px;
    border-radius: 4px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {p['fg_dim']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ---- Label ---- */
QLabel {{
    background-color: transparent;
    color: {p['fg']};
}}

/* ---- CheckBox ---- */
QCheckBox {{
    color: {p['fg']};
    background-color: transparent;
}}

/* ---- Toolbar (matplotlib) ---- */
QToolBar {{
    background-color: {p['bg_panel']};
    border: none;
    spacing: 2px;
}}
"""


def get_stylesheet(dark: bool = True) -> str:
    """Return the full QSS stylesheet for dark or light theme."""
    return _build_qss(DARK if dark else LIGHT)
