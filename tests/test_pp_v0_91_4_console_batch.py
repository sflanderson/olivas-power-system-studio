"""
tests/test_pp_v0_91_4_console_batch.py — v0.91.4:

Hotfix do GUI freeze durante simulação ATP longa (segunda
ocorrência reportada pelo usuário, mesmo após o throttle do
v0.91.2).

Problema residual: throttle reduziu emits para ~10/s mas
``console_panel.append_log`` chamava ``_render_line`` por
linha → ``insertHtml`` (parser HTML custoso) por linha. Para
chunks de 30-50 linhas: ~30 parser invocations × 10 chunks/s
= ~50% CPU em renderização → GUI freezed.

Fix v0.91.4: ``append_log`` agora chama ``insertHtml`` UMA
vez por chunk (concatena toda HTML antes). N parses → 1.

Cobertura
---------

* append_log com chunk multi-linha → todas linhas no cache.
* append_log com chunk multi-linha → 1 insertHtml call (não N).
* append_warn com multi-linha → mesmo batch.
* Linhas vazias filtradas.
* Empty msg = no-op.
* Filter level esconde renderização mas mantém cache.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Cache — todas as linhas ficam armazenadas
# ---------------------------------------------------------------------------


class TestAppendLogCache:

    def test_multi_line_chunk_all_cached(self, qapp):
        from app.gui.console_panel import ConsolePanel
        cp = ConsolePanel()
        cp.append_log("line A\nline B\nline C")
        # Todas as 3 linhas no cache, com level LOG
        log_lines = [t for lvl, t in cp._lines if lvl == "LOG"]
        assert len(log_lines) == 3
        assert any("line A" in t for t in log_lines)
        assert any("line B" in t for t in log_lines)
        assert any("line C" in t for t in log_lines)

    def test_empty_lines_filtered(self, qapp):
        """Linhas vazias entre conteúdo são removidas."""
        from app.gui.console_panel import ConsolePanel
        cp = ConsolePanel()
        cp.append_log("alpha\n\n\nbeta\n")
        log_lines = [t for lvl, t in cp._lines if lvl == "LOG"]
        assert len(log_lines) == 2
        assert any("alpha" in t for t in log_lines)
        assert any("beta" in t for t in log_lines)

    def test_empty_msg_noop(self, qapp):
        from app.gui.console_panel import ConsolePanel
        cp = ConsolePanel()
        cp.append_log("")
        cp.append_log("\n\n\n")
        assert len([t for lvl, t in cp._lines if lvl == "LOG"]) == 0


# ---------------------------------------------------------------------------
# Single insertHtml call per chunk (performance contract)
# ---------------------------------------------------------------------------


class TestSingleInsertHtmlPerChunk:

    def test_chunk_of_50_lines_one_insert_html(self, qapp):
        """v0.91.4 contract: 1 chunk → 1 insertHtml."""
        from app.gui.console_panel import ConsolePanel
        cp = ConsolePanel()
        chunk = "\n".join(f"line {i}" for i in range(50))
        # Patch insertHtml para contar chamadas
        with patch.object(
            cp._text, "insertHtml", wraps=cp._text.insertHtml,
        ) as spy:
            cp.append_log(chunk)
        assert spy.call_count == 1, (
            f"Esperava 1 insertHtml, obteve {spy.call_count} "
            f"— performance regression"
        )

    def test_warn_chunk_one_insert_html(self, qapp):
        """v0.91.4: append_warn multi-linha também batched."""
        from app.gui.console_panel import ConsolePanel
        cp = ConsolePanel()
        chunk = "warn 1\nwarn 2\nwarn 3"
        with patch.object(
            cp._text, "insertHtml", wraps=cp._text.insertHtml,
        ) as spy:
            cp.append_warn(chunk)
        assert spy.call_count == 1

    def test_warn_single_line_unchanged(self, qapp):
        """append_warn de 1 linha (sem \\n) usa path legacy."""
        from app.gui.console_panel import ConsolePanel
        cp = ConsolePanel()
        with patch.object(
            cp._text, "insertHtml", wraps=cp._text.insertHtml,
        ) as spy:
            cp.append_warn("solo warn")
        assert spy.call_count == 1
        log_lines = [
            t for lvl, t in cp._lines if lvl == "WARN"
        ]
        assert len(log_lines) == 1


# ---------------------------------------------------------------------------
# Filter respect — level oculto não renderiza mas mantém cache
# ---------------------------------------------------------------------------


class TestFilterRespect:

    def test_filter_hides_render_keeps_cache(self, qapp):
        """Se LOG está filtrado out, render skipped mas cache
        preserved (para refilter futuro)."""
        from app.gui.console_panel import ConsolePanel
        cp = ConsolePanel()
        # Filter para WARN+ (esconde LOG)
        cp._filter_combo.setCurrentIndex(2)   # WARN+
        with patch.object(
            cp._text, "insertHtml", wraps=cp._text.insertHtml,
        ) as spy:
            cp.append_log("hidden 1\nhidden 2")
        assert spy.call_count == 0, (
            "Render foi chamado apesar do filter"
        )
        # Mas cache PRESERVADO
        log_lines = [t for lvl, t in cp._lines if lvl == "LOG"]
        assert len(log_lines) == 2


# ---------------------------------------------------------------------------
# HTML escape (não quebra com chars especiais)
# ---------------------------------------------------------------------------


class TestHtmlEscape:

    def test_special_chars_escaped(self, qapp):
        from app.gui.console_panel import ConsolePanel
        cp = ConsolePanel()
        cp.append_log("<tag> & 'quote' \"double\"")
        # Conteúdo no _text deve não ter raw <tag> (escapado)
        text = cp._text.toPlainText()
        assert "<tag>" in text   # plain text preserva, mas
        # o que importa é que insertHtml não interpretou.
        # Validamos via substring presente.

    def test_html_injection_blocked(self, qapp):
        """Tentativa de injetar <script> não executa."""
        from app.gui.console_panel import ConsolePanel
        cp = ConsolePanel()
        cp.append_log("<script>alert(1)</script>")
        text = cp._text.toPlainText()
        assert "<script>" in text   # texto literal, não tag
