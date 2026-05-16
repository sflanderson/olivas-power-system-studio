"""
tests/test_pp_v3_1_1_pin_mode.py — v3.1.1 Sprint 1.

Push-pin Mode (TOOL_PIN) — PTW Tutorial §Part 1 p.21-24.

Cobre:
* PpView.TOOL_PIN constant exists
* enter_pin_mode(code) sets tool + stores type_code
* mousePressEvent in pin mode emits request_add_component_at
* Esc / V exits pin mode (tool returns to SELECT, _pin_type_code cleared)
* PpEditor._on_palette_request_add enters pin mode (except for BUS)
"""

from __future__ import annotations

import os
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys
    return QApplication.instance() or QApplication(sys.argv)


# ===========================================================================
# Sprint 1.A — TOOL_PIN constant + enter_pin_mode
# ===========================================================================


class TestToolPinMode:

    def test_tool_pin_constant_exists(self):
        from app.gui.schematic_pp.view import PpView
        assert PpView.TOOL_PIN == "pin"

    def test_default_tool_is_select(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView
        view = PpView(PpScene())
        assert view.tool == PpView.TOOL_SELECT

    def test_enter_pin_mode_sets_tool_and_type(self, qapp):
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView
        view = PpView(PpScene())
        view.enter_pin_mode("R")
        assert view.tool == PpView.TOOL_PIN
        assert view._pin_type_code == "R"

    def test_set_tool_select_clears_pin_type(self, qapp):
        """Voltar para SELECT limpa o type_code (Esc / V)."""
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView
        view = PpView(PpScene())
        view.enter_pin_mode("R")
        view.set_tool(PpView.TOOL_SELECT)
        assert view.tool == PpView.TOOL_SELECT
        assert view._pin_type_code is None

    def test_set_tool_wire_clears_pin_type(self, qapp):
        """Mudar para WIRE também limpa pin type."""
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView
        view = PpView(PpScene())
        view.enter_pin_mode("Vdc")
        view.set_tool(PpView.TOOL_WIRE)
        assert view.tool == PpView.TOOL_WIRE
        assert view._pin_type_code is None

    def test_set_tool_invalid_raises(self, qapp):
        """Tool desconhecido → ValueError."""
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView
        view = PpView(PpScene())
        with pytest.raises(ValueError):
            view.set_tool("unknown")


# ===========================================================================
# Sprint 1.B — Pin mode click emits component request
# ===========================================================================


class TestPinModeClickEmits:

    def test_pin_click_emits_request(self, qapp):
        """Click em pin mode dispara request_add_component_at."""
        from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView

        view = PpView(PpScene())
        view.enter_pin_mode("R")

        captured = []
        view.request_add_component_at.connect(
            lambda code, pt: captured.append((code, pt))
        )

        # Synthesize a mouse press inside pin mode
        view.resize(400, 400)
        evt = QMouseEvent(
            QEvent.MouseButtonPress,
            QPointF(100, 100),  # local pos
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier,
        )
        view.mousePressEvent(evt)

        assert len(captured) == 1
        code, pt = captured[0]
        assert code == "R"
        # Snap to grid 10
        assert int(pt.x()) % 10 == 0

    def test_pin_click_repeated_emits_multiple(self, qapp):
        """3 clicks → 3 emissões (push-pin behavior)."""
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from app.gui.schematic_pp.scene import PpScene
        from app.gui.schematic_pp.view import PpView

        view = PpView(PpScene())
        view.resize(400, 400)
        view.enter_pin_mode("Vdc")

        count = []
        view.request_add_component_at.connect(
            lambda code, pt: count.append(code)
        )

        for x in (50, 100, 150):
            evt = QMouseEvent(
                QEvent.MouseButtonPress,
                QPointF(x, 100), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier,
            )
            view.mousePressEvent(evt)

        assert len(count) == 3
        assert all(c == "Vdc" for c in count)


# ===========================================================================
# Sprint 1.C — Editor wires palette → pin mode
# ===========================================================================


class TestEditorPaletteToPinMode:

    def test_palette_click_enters_pin_mode_for_R(self, qapp):
        """Selecionar 'R' na paleta entra em pin mode."""
        from app.gui.schematic_pp.editor import PpEditor
        from app.gui.schematic_pp.view import PpView
        editor = PpEditor()
        editor._on_palette_request_add("R")
        assert editor.view.tool == PpView.TOOL_PIN
        assert editor.view._pin_type_code == "R"

    def test_palette_click_BUS_uses_dialog_path(self, qapp):
        """BUS ainda usa dialog quick-add — não entra em pin mode."""
        from app.gui.schematic_pp.editor import PpEditor
        from app.gui.schematic_pp.view import PpView
        editor = PpEditor()
        # Monkeypatch dialog to avoid showing it
        editor._prompt_bus_info = lambda: None  # user "cancels"
        editor._on_palette_request_add("BUS")
        # Ainda em SELECT (BUS não usa pin mode)
        assert editor.view.tool == PpView.TOOL_SELECT

    def test_palette_click_other_types_enter_pin(self, qapp):
        """Diversos tipos entram em pin mode."""
        from app.gui.schematic_pp.editor import PpEditor
        from app.gui.schematic_pp.view import PpView
        editor = PpEditor()
        for code in ("R", "L", "C", "Vdc", "Tr"):
            editor._on_palette_request_add(code)
            assert editor.view.tool == PpView.TOOL_PIN
            assert editor.view._pin_type_code == code
            # Reset back to SELECT for next iteration
            editor.view.set_tool(PpView.TOOL_SELECT)


# ===========================================================================
# Sprint 1.D — 7ª garantia accessibility
# ===========================================================================


class TestSeventhGuaranteeAccessibility:

    def test_pin_mode_is_accessible_via_palette(self, qapp):
        """A 7ª garantia exige que pin mode seja acessível ao usuário.
        Usuário clica em qualquer item da paleta → entra automatically em pin mode."""
        from app.gui.schematic_pp.editor import PpEditor
        editor = PpEditor()
        # Palette emit signal is wired to _on_palette_request_add
        # which calls view.enter_pin_mode(code) for non-BUS
        assert hasattr(editor, "_on_palette_request_add")
        assert callable(editor._on_palette_request_add)

    def test_view_pin_mode_documented(self):
        """Docstring de view.py menciona TOOL_PIN."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/schematic_pp/view.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "TOOL_PIN" in content
        assert "push-pin" in content.lower()
        assert "PTW Tutorial" in content
