"""
tests/test_pp_editor_v0_27_6.py — v0.27.6: organização visual da
GUI (toggles de painel + right-click context menu + theme light
default).

Cobre:

* Toggle de palette (F9): show/hide do painel da paleta.
* Toggle de properties (F10): show/hide do splitter direito.
* Compact mode (F11): oculta tudo simultaneamente.
* Right-click em área vazia do canvas: menu contextual com
  submenu "Adicionar componente" agrupado por categoria.
* Sinal ``request_add_component_at`` é emitido com
  type_code + scene_pos snapado.
* Theme padrão LIGHT (cinza industrial).
* Paleta industrial (LIGHT): cores corretas (border, bg_panel
  visíveis, contraste alto).
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

from app.gui.schematic_pp.editor import PpEditor
from app.gui.theme import LIGHT, get_palette, get_stylesheet


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------------------------------------------------------------------------
# Theme — padrão LIGHT "Oliveira" (v0.83)
# Substituiu paleta industrial-gray pela paleta brand olive tree.
# ---------------------------------------------------------------------------


class TestThemeIndustrialLight:
    def test_light_palette_has_olive_cream_bg(self):
        """v0.83: fundo OLIVE_CREAM (logo bg) em vez de
        cinza industrial."""
        assert LIGHT["bg"] == "#FAFAF5"
        # Painel cream-sage muito sutil
        assert LIGHT["bg_panel"] == "#EFF0E8"

    def test_light_palette_has_olive_border(self):
        """v0.83: bordas OLIVE_PALE (sage suave) em vez de
        cinza industrial #a0a0a0."""
        assert LIGHT["border"] == "#B5D4A8"

    def test_light_palette_high_contrast_fg(self):
        """v0.83: texto warm-black #2A2D24 (era #202020 puro)."""
        assert LIGHT["fg"] == "#2A2D24"

    def test_get_palette_light_returns_industrial(self):
        p = get_palette(dark=False)
        assert p == LIGHT

    def test_stylesheet_light_renders(self):
        """get_stylesheet(False) gera QSS válido sem exceção."""
        qss = get_stylesheet(dark=False)
        assert "QPushButton" in qss
        # cor do bg_panel aparece no QSS
        assert LIGHT["bg_panel"] in qss


# ---------------------------------------------------------------------------
# Toggles de painel
# ---------------------------------------------------------------------------


class TestPanelToggles:
    def test_palette_visible_by_default(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            assert editor.act_toggle_palette.isChecked() is True
            assert editor._palette_panel.isVisible()
        finally:
            editor.close()

    def test_toggle_palette_hides_panel(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            editor.toggle_palette_panel(False)
            assert editor.act_toggle_palette.isChecked() is False
            # isVisible reflete imediatamente em widgets pais que estão visíveis
            assert editor._palette_panel.isVisible() is False
        finally:
            editor.close()

    def test_toggle_palette_round_trip(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            editor.toggle_palette_panel(False)
            editor.toggle_palette_panel(True)
            assert editor.act_toggle_palette.isChecked() is True
            assert editor._palette_panel.isVisible()
        finally:
            editor.close()

    def test_toggle_properties_hides_right_splitter(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            editor.toggle_properties_panel(False)
            assert editor.act_toggle_properties.isChecked() is False
            assert editor._right_splitter.isVisible() is False
        finally:
            editor.close()

    def test_compact_mode_hides_everything(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            editor.set_compact_mode(True)
            assert editor.act_compact_mode.isChecked() is True
            assert editor._palette_panel.isVisible() is False
            assert editor._right_splitter.isVisible() is False
        finally:
            editor.close()

    def test_compact_mode_off_restores_panels(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            editor.set_compact_mode(True)
            editor.set_compact_mode(False)
            assert editor._palette_panel.isVisible()
            assert editor._right_splitter.isVisible()
        finally:
            editor.close()

    def test_button_click_triggers_toggle(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            # simula click via toggle()
            editor.act_toggle_palette.toggle()
            assert editor._palette_panel.isVisible() is False
            editor.act_toggle_palette.toggle()
            assert editor._palette_panel.isVisible() is True
        finally:
            editor.close()


# ---------------------------------------------------------------------------
# Right-click context menu — empty canvas
# ---------------------------------------------------------------------------


class TestEmptyCanvasContextMenu:
    def test_build_empty_menu_returns_menu(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            menu = editor.view._build_empty_canvas_menu(QPointF(100, 100))
            assert menu is not None
            actions = menu.actions()
            # Deve ter pelo menos: "Adicionar componente" submenu +
            # separator + "Selecionar tudo" + separator + 2 modos
            assert len(actions) >= 3
        finally:
            editor.close()

    def test_empty_menu_has_add_component_submenu(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            menu = editor.view._build_empty_canvas_menu(QPointF(100, 100))
            # Primeiro action deve ter texto "Adicionar componente"
            first = menu.actions()[0]
            assert "Adicionar" in first.text()
            # E deve ter um submenu (não None)
            assert first.menu() is not None
        finally:
            editor.close()

    def test_add_submenu_contains_categories(self, qapp):
        """Verifica que o submenu tem submenus por categoria.

        Inspeciona snapshot in-loop para evitar GC de Qt das
        QMenu filhas (sem manter ref local explícita, Qt as
        deleta).
        """
        editor = PpEditor()
        editor.show()
        try:
            menu = editor.view._build_empty_canvas_menu(QPointF(0, 0))
            # Capture refs imediatamente
            top_actions = list(menu.actions())
            assert len(top_actions) >= 1
            add_action = top_actions[0]
            add_menu = add_action.menu()
            assert add_menu is not None
            cat_titles = [a.text() for a in add_menu.actions()]
            # Pelo menos passive, source devem estar presentes
            assert any("passive" in t.lower() for t in cat_titles)
            assert any("source" in t.lower() for t in cat_titles)
            # Mantém refs até o final do escopo
            del menu, add_menu
        finally:
            editor.close()

    def test_add_submenu_contains_resistor_in_passive(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            # Cache imediatamente todas as refs no momento da criação
            menu = editor.view._build_empty_canvas_menu(QPointF(0, 0))
            top_actions = list(menu.actions())
            add_menu_ref = top_actions[0].menu()
            cat_actions = list(add_menu_ref.actions())
            passive_menu_ref = None
            for a in cat_actions:
                if "passive" in a.text().lower():
                    passive_menu_ref = a.menu()
                    break
            assert passive_menu_ref is not None
            passive_actions = list(passive_menu_ref.actions())
            resistor_action_texts = [
                a.text() for a in passive_actions if "Resistor" in a.text()
            ]
            assert len(resistor_action_texts) >= 1
            # Mantém refs vivas até o close (Qt parent ownership)
            del menu, add_menu_ref, passive_menu_ref
        finally:
            editor.close()

    def test_request_add_component_at_signal_emitted(self, qapp):
        """Trigger de uma action do submenu emite o signal correto."""
        editor = PpEditor()
        editor.show()
        try:
            received: list[tuple[str, QPointF]] = []
            editor.view.request_add_component_at.connect(
                lambda code, pos: received.append((code, pos))
            )
            menu = editor.view._build_empty_canvas_menu(QPointF(0, 0))
            top_actions = list(menu.actions())
            add_menu_ref = top_actions[0].menu()
            cat_actions = list(add_menu_ref.actions())
            passive_menu_ref = next(
                (a.menu() for a in cat_actions
                 if "passive" in a.text().lower()),
                None,
            )
            assert passive_menu_ref is not None
            passive_actions = list(passive_menu_ref.actions())
            r_action = next(
                (a for a in passive_actions if "Resistor" in a.text()),
                None,
            )
            assert r_action is not None
            r_action.trigger()
            assert len(received) == 1
            code, pos = received[0]
            assert code == "R"
            # Posição deve ser snapada para grid (múltiplos de 10)
            assert pos.x() % 10 == 0
            assert pos.y() % 10 == 0
            del menu, add_menu_ref, passive_menu_ref
        finally:
            editor.close()

    def test_signal_triggers_add_component(self, qapp):
        """End-to-end: signal → editor cria o componente."""
        editor = PpEditor()
        editor.show()
        try:
            initial_count = len(editor.scene.project.components)
            # Direct call ao handler (mesmo que o signal faria)
            editor._on_request_add_component_at("R", QPointF(50, 50))
            # Componente foi adicionado
            assert len(editor.scene.project.components) == initial_count + 1
        finally:
            editor.close()


# ---------------------------------------------------------------------------
# Toolbar buttons
# ---------------------------------------------------------------------------


class TestToolbarButtons:
    def test_toolbar_has_panel_toggle_buttons(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            # Checa que os 3 botões existem
            assert editor.act_toggle_palette is not None
            assert editor.act_toggle_properties is not None
            assert editor.act_compact_mode is not None
        finally:
            editor.close()

    def test_panel_toggle_buttons_are_checkable(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            assert editor.act_toggle_palette.isCheckable()
            assert editor.act_toggle_properties.isCheckable()
            assert editor.act_compact_mode.isCheckable()
        finally:
            editor.close()

    def test_compact_mode_button_default_off(self, qapp):
        editor = PpEditor()
        editor.show()
        try:
            assert editor.act_compact_mode.isChecked() is False
        finally:
            editor.close()
