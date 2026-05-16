"""
tests/test_pp_chat_panel.py — v0.23.1: widget de chat do editor
de esquemático.

Cobre:

* ``estimate_cost``: cálculo correto de USD por modelo.
* ``PpChatPanel`` construção: sem API key → desabilitado; com
  API key → habilitado.
* ``ChatReply`` acumula tokens na sessão e atualiza status.
* Rendering de tool_calls e final_text no histórico.
* Integração no ``PpEditor`` layout (chat no splitter vertical
  direito).

Não cobre (out of scope v0.23.1):
* Chamadas reais à API Anthropic.
* Execução do ChatWorker em thread real (em CI é rápido demais
  para validar QThread start/stop sem flakiness).
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QSplitter

from app.gui.schematic_pp.chat_panel import (
    DEFAULT_PRICING,
    MODEL_PRICING_USD_PER_MTOK,
    PpChatPanel,
    estimate_cost,
)
from app.gui.schematic_pp.editor import PpEditor
from app.llm.claude_client import ChatReply


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


# ---------------------------------------------------------------------------
# Cost estimator
# ---------------------------------------------------------------------------


class TestEstimateCost:
    def test_sonnet_pricing_applies(self):
        # Sonnet: $3/MTok in, $15/MTok out
        cost = estimate_cost("claude-sonnet-4-5-20250929", 1_000_000, 1_000_000)
        assert cost == pytest.approx(3.0 + 15.0)

    def test_haiku_is_cheapest(self):
        # Haiku: $1/MTok in, $5/MTok out
        cost = estimate_cost("claude-haiku-4-5-20251001", 1_000_000, 1_000_000)
        assert cost == pytest.approx(1.0 + 5.0)

    def test_opus_is_premium(self):
        # Opus: $15/MTok in, $75/MTok out
        cost = estimate_cost("claude-opus-4-5", 1_000_000, 1_000_000)
        assert cost == pytest.approx(15.0 + 75.0)

    def test_unknown_model_falls_back_to_default(self):
        """Modelo desconhecido usa pricing default (Sonnet)."""
        cost_unknown = estimate_cost("claude-mystery-model", 1_000, 1_000)
        cost_sonnet = estimate_cost("claude-sonnet-4-5", 1_000, 1_000)
        assert cost_unknown == cost_sonnet

    def test_zero_tokens_zero_cost(self):
        assert estimate_cost("claude-sonnet-4-5", 0, 0) == 0.0

    def test_default_pricing_matches_sonnet(self):
        """DEFAULT_PRICING é o Sonnet (seguro/conservador)."""
        sonnet = MODEL_PRICING_USD_PER_MTOK["claude-sonnet-4-5"]
        assert DEFAULT_PRICING.input_per_mtok == sonnet.input_per_mtok
        assert DEFAULT_PRICING.output_per_mtok == sonnet.output_per_mtok


# ---------------------------------------------------------------------------
# PpChatPanel construção
# ---------------------------------------------------------------------------


class TestPpChatPanelConstruction:
    def test_disabled_without_api_key(self, qapp):
        ed = PpEditor()
        panel = PpChatPanel(ed, api_key=None)
        assert panel.is_ready is False

    def test_enabled_with_api_key(self, qapp):
        ed = PpEditor()
        panel = PpChatPanel(ed, api_key="sk-test-key")
        assert panel.is_ready is True

    def test_initial_session_cost_is_zero(self, qapp):
        ed = PpEditor()
        panel = PpChatPanel(ed, api_key="sk-test-key")
        assert panel.session_cost_usd == 0.0
        assert panel._session_input_tokens == 0
        assert panel._session_output_tokens == 0

    def test_reset_session_clears_state(self, qapp):
        ed = PpEditor()
        panel = PpChatPanel(ed, api_key="sk-test-key")
        panel._session_input_tokens = 1000
        panel._session_output_tokens = 500
        panel.reset_session()
        assert panel._session_input_tokens == 0
        assert panel._session_output_tokens == 0
        assert panel.session_cost_usd == 0.0

    def test_status_shows_warning_without_api_key(self, qapp):
        ed = PpEditor()
        panel = PpChatPanel(ed, api_key=None)
        status_text = panel._status.text()
        assert "ANTHROPIC_API_KEY" in status_text or "desabilit" in status_text.lower()


# ---------------------------------------------------------------------------
# Rendering + accumulator
# ---------------------------------------------------------------------------


class TestReplyRendering:
    def test_reply_accumulates_tokens(self, qapp):
        ed = PpEditor()
        panel = PpChatPanel(ed, api_key="sk-test-key")
        reply = ChatReply(
            final_text="Adicionado.",
            tool_calls=[],
            rounds=1,
            input_tokens=1000,
            output_tokens=500,
        )
        panel._on_reply_ready(reply)
        assert panel._session_input_tokens == 1000
        assert panel._session_output_tokens == 500
        expected_cost = estimate_cost(
            "claude-sonnet-4-5-20250929", 1000, 500
        )
        assert panel.session_cost_usd == pytest.approx(expected_cost)

    def test_reply_with_tool_calls_appends_to_history(self, qapp):
        ed = PpEditor()
        panel = PpChatPanel(ed, api_key="sk-test-key")
        reply = ChatReply(
            final_text="R1 adicionado em (100, 100).",
            tool_calls=[{
                "name": "add_R",
                "input": {"name": "R1", "x": 100, "y": 100, "R": 100.0},
                "result": {
                    "success": True,
                    "name": "R1",
                    "code": "R",
                    "position": [100, 100],
                },
            }],
            rounds=2,
            input_tokens=800,
            output_tokens=200,
        )
        panel._on_reply_ready(reply)
        history_text = panel._history.toPlainText()
        # Menciona add_R, R1, e o final_text
        assert "add_R" in history_text
        assert "R1" in history_text
        assert "adicionado" in history_text.lower()

    def test_reply_with_failed_tool_shows_error(self, qapp):
        ed = PpEditor()
        panel = PpChatPanel(ed, api_key="sk-test-key")
        reply = ChatReply(
            final_text="",
            tool_calls=[{
                "name": "add_UNKNOWN",
                "input": {"name": "X"},
                "result": {"success": False, "error": "Código não existe"},
            }],
            rounds=1,
            input_tokens=500,
            output_tokens=100,
        )
        panel._on_reply_ready(reply)
        html = panel._history.toHtml()
        # Deve aparecer o ícone ✗ ou a mensagem de erro
        assert "✗" in html or "não existe" in html or "nao existe" in html

    def test_reply_emits_signal(self, qapp):
        ed = PpEditor()
        panel = PpChatPanel(ed, api_key="sk-test-key")
        captured = []
        panel.reply_received.connect(lambda r: captured.append(r))
        reply = ChatReply(final_text="ok", input_tokens=100, output_tokens=50)
        panel._on_reply_ready(reply)
        assert len(captured) == 1
        assert captured[0] is reply


# ---------------------------------------------------------------------------
# Editor layout integration
# ---------------------------------------------------------------------------


class TestEditorLayoutIntegration:
    def test_editor_has_chat_panel_attribute(self, qapp):
        ed = PpEditor()
        assert hasattr(ed, "chat_panel")
        assert isinstance(ed.chat_panel, PpChatPanel)

    def test_editor_layout_has_two_splitters(self, qapp):
        """Horizontal (palette|view|right) + vertical (properties|chat)."""
        ed = PpEditor()
        splitters = ed.findChildren(QSplitter)
        # Pelo menos 2: horizontal geral + vertical do lado direito.
        # Qt pode retornar os mesmos 2 em qualquer ordem.
        assert len(splitters) >= 2

    def test_chat_panel_parent_is_editor(self, qapp):
        ed = PpEditor()
        # O parent pode ser o splitter (após addWidget), não o ed.
        # Mas o chat_panel deve estar presente no childTree do editor.
        all_children = ed.findChildren(PpChatPanel)
        assert ed.chat_panel in all_children


# ---------------------------------------------------------------------------
# Input → send flow (sem worker real)
# ---------------------------------------------------------------------------


class TestInputSendFlow:
    def test_empty_message_is_noop(self, qapp):
        ed = PpEditor()
        panel = PpChatPanel(ed, api_key="sk-test-key")
        panel._input.setText("   ")  # só espaços
        initial_worker = panel._worker
        panel._on_send()
        # Não cria worker com mensagem vazia
        assert panel._worker is initial_worker

    def test_send_without_api_key_is_noop(self, qapp):
        ed = PpEditor()
        panel = PpChatPanel(ed, api_key=None)
        panel._input.setText("hello")
        panel._on_send()
        # Sem client, nada é criado
        assert panel._client is None
        assert panel._worker is None
