"""
tests/test_pp_v0_28_3_pro_onda3.py — v0.28.3-PRO Onda 3:
Quality of Life GUI features.

Cobre:

* 3.1: Async ATP runner (worker + thread + cancel)
* 3.2: ConsolePanel append_info/warn/error/log + filter
* 3.3: Undo/Redo global (QUndoStack + CellEditCommand)
* 3.4: Tab labels diferenciados (legacy vs visual)
* 3.5: i18n consistency (Diferenças, acentos)
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import QObject
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication, QMenu


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def main_window(qapp):
    from app.gui.main_window import MainWindow
    mw = MainWindow()
    yield mw
    mw.close()


# ---------------------------------------------------------------------------
# 3.1 — Async runner
# ---------------------------------------------------------------------------


class TestAsyncRunner:

    def test_worker_instantiable(self, qapp):
        from app.gui.async_runner import AtpRunWorker
        from app.simulation.runner import AtpRunner
        runner = AtpRunner()
        worker = AtpRunWorker(runner, "fake.atp")
        assert isinstance(worker, QObject)

    def test_make_run_thread(self, qapp):
        from app.gui.async_runner import make_run_thread
        from app.simulation.runner import AtpRunner
        thread, worker = make_run_thread(
            AtpRunner(), "fake.atp", timeout=10,
        )
        assert thread is not None
        assert worker is not None
        # No need to start() for unit test

    def test_request_cancel_no_active_process(self, qapp):
        """request_cancel sem processo ativo não deve crashar."""
        from app.gui.async_runner import AtpRunWorker
        from app.simulation.runner import AtpRunner
        worker = AtpRunWorker(AtpRunner(), "fake.atp")
        # Não deve raise
        worker.request_cancel()
        assert worker._cancelled is True

    def test_runner_kill_process_returns_false_when_no_active(self):
        from app.simulation.runner import AtpRunner
        r = AtpRunner()
        assert r.kill_process() is False

    def test_worker_exception_path_creates_valid_RunResult(self, qapp):
        """
        v0.28.4-PRO followup blocker #1: o except path do
        AtpRunWorker.run() construía RunResult com kwargs
        errados (returncode/duration_s/lis_file/pl4_file)
        que não existem no dataclass — qualquer exceção do
        runner crashava a GUI.

        Agora o except path constrói RunResult com kwargs
        corretos (return_code, run_dir, log_file).
        """
        from app.gui.async_runner import AtpRunWorker

        # Mock de runner que SEMPRE lança exceção
        class FailingRunner:
            def run(self, *args, **kwargs):
                raise RuntimeError("boom")

        worker = AtpRunWorker(FailingRunner(), "fake.atp")
        # Captura o sinal finished
        results = []
        worker.finished.connect(lambda r: results.append(r))
        # Executa síncrono (não em thread) — testa só a lógica
        worker.run()
        assert len(results) == 1
        rr = results[0]
        # Não deve ser None nem ter kwarg inválido
        assert rr is not None
        assert rr.success is False
        assert "boom" in rr.message


# ---------------------------------------------------------------------------
# 3.2 — Console panel
# ---------------------------------------------------------------------------


class TestConsolePanel:

    def test_panel_in_main_window(self, main_window):
        assert hasattr(main_window, "_console_panel")
        assert main_window._console_panel is not None

    def test_append_info_visible(self, qapp):
        from app.gui.console_panel import ConsolePanel
        panel = ConsolePanel()
        panel.append_info("Operação OK")
        plain = panel._text.toPlainText()
        assert "Operação OK" in plain
        assert "INFO" in plain

    def test_append_warn(self, qapp):
        from app.gui.console_panel import ConsolePanel
        panel = ConsolePanel()
        panel.append_warn("Default usado")
        assert "WARN" in panel._text.toPlainText()

    def test_append_error(self, qapp):
        from app.gui.console_panel import ConsolePanel
        panel = ConsolePanel()
        panel.append_error("ATP crashou")
        assert "ERROR" in panel._text.toPlainText()

    def test_append_log_multiline(self, qapp):
        from app.gui.console_panel import ConsolePanel
        panel = ConsolePanel()
        panel.append_log("linha 1\nlinha 2\nlinha 3")
        plain = panel._text.toPlainText()
        # 3 LOG entries
        assert plain.count("LOG") == 3

    def test_clear(self, qapp):
        from app.gui.console_panel import ConsolePanel
        panel = ConsolePanel()
        panel.append_info("test")
        assert panel._text.toPlainText() != ""
        panel.clear()
        assert panel._text.toPlainText() == ""
        assert panel._lines == []

    def test_filter_show_warn_only(self, qapp):
        from app.gui.console_panel import ConsolePanel
        panel = ConsolePanel()
        panel.append_log("log msg")
        panel.append_info("info msg")
        panel.append_warn("warn msg")
        panel.append_error("err msg")
        # Filter index 2 = WARN+ → mostra WARN e ERROR
        panel._filter_combo.setCurrentIndex(2)
        plain = panel._text.toPlainText()
        assert "warn msg" in plain
        assert "err msg" in plain
        assert "info msg" not in plain
        assert "log msg" not in plain


# ---------------------------------------------------------------------------
# 3.3 — Undo/Redo global
# ---------------------------------------------------------------------------


class TestUndoRedo:

    def test_undo_stack_in_main_window(self, main_window):
        assert hasattr(main_window, "_undo_stack")
        assert isinstance(main_window._undo_stack, QUndoStack)

    def test_edit_menu_has_undo_redo(self, main_window):
        menus = main_window.menuBar().findChildren(QMenu)
        edit_menu = next(
            (m for m in menus if m.title() == "Editar"), None,
        )
        assert edit_menu is not None
        action_texts = [a.text() for a in edit_menu.actions()]
        assert any("Desfazer" in t for t in action_texts)
        assert any("Refazer" in t for t in action_texts)

    def test_cell_edit_command_redo_undo(self, qapp):
        from app.gui.undo_commands import CellEditCommand

        # Mock dataclass
        class Mock:
            def __init__(self):
                self.value = "old"

        m = Mock()

        cmd = CellEditCommand(
            description="edit",
            getter=lambda: m.value,
            setter=lambda v: setattr(m, "value", v),
            new_value="new",
        )
        # 1ª redo aplica
        cmd.redo()
        assert m.value == "new"
        # undo restaura
        cmd.undo()
        assert m.value == "old"
        # redo reaplica
        cmd.redo()
        assert m.value == "new"

    def test_cell_edit_on_change_callback(self, qapp):
        from app.gui.undo_commands import CellEditCommand

        called = [0]

        class M:
            def __init__(self):
                self.value = 0

        m = M()
        cmd = CellEditCommand(
            description="x",
            getter=lambda: m.value,
            setter=lambda v: setattr(m, "value", v),
            new_value=42,
            on_change=lambda: called.__setitem__(0, called[0] + 1),
        )
        cmd.redo()   # +1
        cmd.undo()   # +1
        cmd.redo()   # +1
        assert called[0] == 3


# ---------------------------------------------------------------------------
# 3.4 — Tabs differentiated
# ---------------------------------------------------------------------------


class TestTabsConsolidated:

    def test_legacy_widget_still_available(self, main_window):
        """v0.92.1: tab 'Esquemático (legacy)' foi removida da UI
        (ATP desvinculado), mas o widget continua sendo
        instanciado para handlers legacy. Verifica que o
        atributo ainda existe."""
        # Tab visível foi removido em v0.92.1. Widget continua
        # construído (handlers legacy referenciam-no).
        assert hasattr(main_window, "schematic"), (
            "Widget self.schematic deveria continuar existindo "
            "(handlers legacy o referenciam mesmo sem tab)"
        )
        # Confirmação adicional: NÃO deve mais aparecer no
        # tabs visíveis (foi removido em v0.92.1)
        legacy_visible = any(
            "legacy" in main_window.tabs.tabText(i).lower()
            for i in range(main_window.tabs.count())
        )
        assert not legacy_visible, (
            "v0.92.1: Tab 'legacy' foi REMOVIDA da UI principal"
        )

    def test_visual_is_default_tab(self, main_window):
        """v0.92.1: Esquemático Visual é a aba PRIMÁRIA (sem
        marcação ★ — agora é a default, não precisa destacar)."""
        for i in range(main_window.tabs.count()):
            text = main_window.tabs.tabText(i)
            if "Esquemático Visual" in text:
                return
        pytest.fail(
            "Tab 'Esquemático Visual' não encontrada"
        )


# ---------------------------------------------------------------------------
# 3.5 — i18n cleanup
# ---------------------------------------------------------------------------


class TestI18n:

    def test_diff_widget_still_available(self, main_window):
        """v0.92.1: tab 'Diferenças' foi removida da UI principal
        (ATP-only), mas widget self.diff_text continua
        instanciado para handlers legacy."""
        # Tab visível foi removido. Widget continua existindo.
        assert hasattr(main_window, "diff_text"), (
            "Widget self.diff_text deveria continuar existindo"
        )
        # Confirmação: NÃO está mais visível
        diff_visible = any(
            "Diferen" in main_window.tabs.tabText(i)
            for i in range(main_window.tabs.count())
        )
        assert not diff_visible, (
            "v0.92.1: Tab 'Diferenças' foi REMOVIDA da UI principal"
        )

    def test_chat_help_has_accents(self):
        from app.gui.chat_widget import _HELP_TEXT
        # Verifica que não há mais "disponiveis" sem acento
        assert "disponíveis" in _HELP_TEXT
        assert "disponiveis" not in _HELP_TEXT
        assert "parâmetros" in _HELP_TEXT
        assert "simulação" in _HELP_TEXT
