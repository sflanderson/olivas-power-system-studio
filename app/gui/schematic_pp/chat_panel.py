"""
app.gui.schematic_pp.chat_panel — widget de chat do editor de
esquemático, integrado com :class:`app.llm.claude_client.ClaudeClient`.

Diferencia-se do ``app.gui.chat_widget.ChatWidget`` existente:

* ``ChatWidget`` (antigo) — foca na manipulação de ``AtpProject``
  (open_file, list_models, set_data_param, run_simulation, ...).
* ``PpChatPanel`` (novo, v0.23.1) — foca no editor de esquemático,
  usa :class:`EditorDispatcher` para expor ``add_<CODE>`` tools
  derivados do catálogo ``.ocomp``. Ideal para "Adicione um
  resistor de 100 Ω entre N1 e GND".

Os dois podem coexistir na UI — cada um no seu contexto.

Componentes
-----------

* :class:`PpChatPanel` — o widget em si (history + input + cost).
* :class:`ChatWorker` (``QThread``) — executa ``client.chat`` em
  background para não bloquear a UI durante chamadas à API
  (latência típica 1-5 s).
* :func:`estimate_cost` — helper usando a tabela
  :data:`MODEL_PRICING_USD_PER_MTOK` com preços vigentes (late
  2025). Output separado de input; cache read é 10× mais barato
  que input não-cacheado.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.llm.claude_client import ChatReply, ClaudeClient, EditorDispatcher


# ---------------------------------------------------------------------------
# Pricing table (USD por 1M tokens) — Anthropic, valores de 2025/Q1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelPricing:
    """Preços em USD por 1M tokens."""
    input_per_mtok: float
    output_per_mtok: float


MODEL_PRICING_USD_PER_MTOK: dict[str, ModelPricing] = {
    # Sonnet 4.5
    "claude-sonnet-4-5-20250929": ModelPricing(3.0, 15.0),
    # Aliases sem data
    "claude-sonnet-4-5": ModelPricing(3.0, 15.0),
    # Opus 4.5
    "claude-opus-4-5-20251101": ModelPricing(15.0, 75.0),
    "claude-opus-4-5": ModelPricing(15.0, 75.0),
    # Haiku 4.5 (mais barato)
    "claude-haiku-4-5-20251001": ModelPricing(1.0, 5.0),
    "claude-haiku-4-5": ModelPricing(1.0, 5.0),
    # Fallback — default=Sonnet preços
}


DEFAULT_PRICING = ModelPricing(3.0, 15.0)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Retorna custo estimado em USD para ``input_tokens`` + ``output_tokens``
    no modelo ``model``.

    Parameters
    ----------
    model:
        Identificador do modelo (ex: ``"claude-sonnet-4-5-20250929"``).
    input_tokens, output_tokens:
        Contagens (inteiros).

    Returns
    -------
    float
        Custo em USD.
    """
    pricing = MODEL_PRICING_USD_PER_MTOK.get(model, DEFAULT_PRICING)
    return (
        input_tokens * pricing.input_per_mtok / 1_000_000
        + output_tokens * pricing.output_per_mtok / 1_000_000
    )


# ---------------------------------------------------------------------------
# ChatWorker: executa client.chat em thread background
# ---------------------------------------------------------------------------


class ChatWorker(QThread):
    """
    Thread que executa ``client.chat(message)`` em background.

    Signals
    -------
    reply_ready(ChatReply)
        Emitido quando a resposta está pronta (sucesso ou timeout
        interno — sempre via ChatReply).
    error(str)
        Emitido se ocorreu uma exceção não tratada. O UI deve exibir
        a mensagem ao usuário.
    """

    reply_ready = Signal(object)  # object = ChatReply (sem generics em signals)
    error = Signal(str)

    def __init__(
        self,
        client: ClaudeClient,
        message: str,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._message = message

    def run(self) -> None:  # pragma: no cover - executa em thread
        try:
            reply = self._client.chat(self._message)
            self.reply_ready.emit(reply)
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# PpChatPanel: widget de chat
# ---------------------------------------------------------------------------


class PpChatPanel(QWidget):
    """
    Painel de chat com Claude para manipular o esquemático via
    linguagem natural.

    Fluxo:

    1. Usuário digita ``"Adicione um R de 100 Ω"`` → pressiona Enter.
    2. Panel envia ao :class:`ClaudeClient` em :class:`ChatWorker`.
    3. Worker retorna ``ChatReply`` → panel renderiza histórico +
       tool_calls + custo.

    Se ``ANTHROPIC_API_KEY`` não está configurado, o panel fica
    desabilitado com mensagem orientadora.

    Parameters
    ----------
    editor:
        :class:`PpEditor` onde os componentes serão criados.
    parent:
        QWidget pai.
    api_key:
        Override opcional da API key. Default: env
        ``ANTHROPIC_API_KEY``.
    model:
        Override opcional do modelo. Default: Sonnet 4.5.
    """

    #: Emitido após cada ``ChatReply`` — útil para MainWindow
    #: atualizar contadores globais.
    reply_received = Signal(object)  # ChatReply

    def __init__(
        self,
        editor,
        parent: Optional[QWidget] = None,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self._editor = editor
        # v0.81: usa centralized api_key_manager (QSettings + env + .env)
        if api_key:
            self._api_key = api_key
        else:
            from app.core.api_key_manager import get_anthropic_api_key
            self._api_key = get_anthropic_api_key()
        self._model = model
        self._client: Optional[ClaudeClient] = None
        self._worker: Optional[ChatWorker] = None

        # Acumuladores de sessão
        self._session_input_tokens = 0
        self._session_output_tokens = 0

        self._build_ui()
        self._refresh_status()

    # ---- UI construction ---------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Header
        header = QLabel("<b>Chat — assistente Olivas</b>", self)
        root.addWidget(header)

        # History view (read-only)
        self._history = QTextEdit(self)
        self._history.setReadOnly(True)
        self._history.setAcceptRichText(True)
        self._history.setPlaceholderText(
            "Exemplos:\n"
            "  • Adicione um R de 100 Ω em (100, 100)\n"
            "  • Crie uma fonte AC 13.8 kV 60 Hz chamada Vfonte\n"
            "  • Inclua um VCB com I_chop=8A (reignição ativada)\n"
        )
        root.addWidget(self._history, stretch=1)

        # Status line (cost + state)
        self._status = QLabel("", self)
        self._status.setStyleSheet("color: #777; font-size: 11px;")
        root.addWidget(self._status)

        # Input line
        input_row = QHBoxLayout()
        self._input = QLineEdit(self)
        self._input.setPlaceholderText(
            "Descreva uma ação sobre o esquemático…"
        )
        self._input.returnPressed.connect(self._on_send)
        self._send_btn = QPushButton("Enviar", self)
        self._send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self._input, stretch=1)
        input_row.addWidget(self._send_btn)
        root.addLayout(input_row)

    # ---- Public API --------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """True se o panel pode enviar mensagens (API key presente)."""
        return bool(self._api_key)

    @property
    def session_cost_usd(self) -> float:
        """Custo acumulado na sessão, em USD."""
        model = self._model or ClaudeClient.DEFAULT_MODEL
        return estimate_cost(
            model, self._session_input_tokens, self._session_output_tokens,
        )

    def clear_history(self) -> None:
        """Limpa histórico visual (cost accumulators preservados)."""
        self._history.clear()

    def reset_session(self) -> None:
        """Zera cost accumulators e limpa histórico visual."""
        self._session_input_tokens = 0
        self._session_output_tokens = 0
        self._history.clear()
        self._refresh_status()

    # ---- Internals ---------------------------------------------------------

    def _ensure_client(self) -> Optional[ClaudeClient]:
        """Lazy-init do ClaudeClient (só quando o user envia 1ª mensagem)."""
        if self._client is not None:
            return self._client
        if not self._api_key:
            return None
        dispatcher = EditorDispatcher(self._editor)
        self._client = ClaudeClient(
            dispatcher=dispatcher,
            api_key=self._api_key,
            model=self._model,
        )
        return self._client

    def _refresh_status(self) -> None:
        if not self._api_key:
            self._status.setText(
                "⚠ ANTHROPIC_API_KEY não configurado. "
                "Chat desabilitado."
            )
            self._input.setEnabled(False)
            self._send_btn.setEnabled(False)
            return
        busy = self._worker is not None and self._worker.isRunning()
        if busy:
            self._status.setText(
                f"⏳ Aguardando resposta… | "
                f"Sessão: ${self.session_cost_usd:.4f}"
            )
        else:
            self._status.setText(
                f"✓ Pronto | "
                f"Tokens: {self._session_input_tokens} in / "
                f"{self._session_output_tokens} out | "
                f"Sessão: ${self.session_cost_usd:.4f}"
            )

    def _append_html(self, html: str) -> None:
        """Adiciona um bloco HTML ao histórico e rola para o final."""
        self._history.moveCursor(QTextCursor.End)
        self._history.insertHtml(html + "<br>")
        self._history.moveCursor(QTextCursor.End)

    def _on_send(self) -> None:
        text = (self._input.text() or "").strip()
        if not text:
            return
        # Ignora se já está processando
        if self._worker is not None and self._worker.isRunning():
            return
        client = self._ensure_client()
        if client is None:
            return

        # Renderiza mensagem do usuário
        self._append_html(
            f"<div style='margin:4px 0;'><b>Você:</b> "
            f"{_html_escape(text)}</div>"
        )
        self._input.clear()

        # Dispara worker
        self._worker = ChatWorker(client, text, parent=self)
        self._worker.reply_ready.connect(self._on_reply_ready)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()
        self._refresh_status()

    def _on_reply_ready(self, reply: ChatReply) -> None:
        # Acumula tokens
        self._session_input_tokens += reply.input_tokens
        self._session_output_tokens += reply.output_tokens

        # Renderiza tool_calls como bullet points
        if reply.tool_calls:
            tool_html_lines: list[str] = ["<ul style='margin:4px 0;'>"]
            for tc in reply.tool_calls:
                result = tc.get("result", {})
                ok = result.get("success", False)
                icon = "✓" if ok else "✗"
                inp_name = tc.get("input", {}).get("name", "?")
                tc_name = tc.get("name", "?")
                summary = (
                    f"{icon} <code>{_html_escape(tc_name)}</code> "
                    f"(name={_html_escape(inp_name)})"
                )
                if not ok:
                    err = result.get("error", "erro desconhecido")
                    summary += f" — <span style='color:#c00;'>{_html_escape(err)}</span>"
                tool_html_lines.append(f"<li>{summary}</li>")
            tool_html_lines.append("</ul>")
            self._append_html(
                f"<div style='color:#555;font-size:12px;'>"
                f"Ferramentas executadas:{''.join(tool_html_lines)}</div>"
            )

        # Renderiza texto final do assistant
        if reply.final_text:
            self._append_html(
                f"<div style='margin:4px 0;'><b>Claude:</b> "
                f"{_html_escape(reply.final_text)}</div>"
            )

        # Emite signal para ouvintes
        self.reply_received.emit(reply)
        self._refresh_status()

    def _on_error(self, message: str) -> None:
        self._append_html(
            f"<div style='color:#c00;'><b>Erro:</b> {_html_escape(message)}</div>"
        )
        self._refresh_status()

    def _on_worker_finished(self) -> None:
        # Evita dangling references
        self._worker = None
        self._refresh_status()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _html_escape(s: str) -> str:
    """Escape mínimo para renderização de HTML no QTextEdit."""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )
