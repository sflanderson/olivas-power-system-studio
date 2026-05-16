"""Chat widget for interacting with the Olivas Power System Studio LLM agent.

Provides a local command interface that dispatches to the ProjectAPI
via the AgentDispatcher. Works without an API key — commands are
parsed locally and mapped to tool calls.

If an Anthropic API key is configured, enables full natural language
interaction via Claude.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Optional

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.llm.agent import AgentDispatcher, get_tool_definitions
from app.llm.project_api import ProjectAPI
from app.gui.theme import DARK

MONO_FONT = "Consolas"
MONO_SIZE = 10


# ======================================================================
# Local command parser (no LLM required)
# ======================================================================

# Maps simple commands to (tool_name, required_args)
_COMMANDS: dict[str, tuple[str, list[str]]] = {
    "abrir": ("open_file", ["file_path"]),
    "open": ("open_file", ["file_path"]),
    "salvar": ("save_file", ["file_path"]),
    "save": ("save_file", ["file_path"]),
    "resumo": ("project_summary", []),
    "summary": ("project_summary", []),
    "modelos": ("list_models", []),
    "models": ("list_models", []),
    "uses": ("list_uses", []),
    "modelo": ("get_model_info", ["model_name"]),
    "model": ("get_model_info", ["model_name"]),
    "use": ("get_use_info", ["model_name"]),
    "componentes": ("list_components", []),
    "components": ("list_components", []),
    "nos": ("list_nodes", []),
    "nodes": ("list_nodes", []),
    "header": ("get_header", []),
    "validar": ("validate_all", []),
    "validate": ("validate_all", []),
    "executar": ("run_simulation", []),
    "run": ("run_simulation", []),
    "simular": ("run_simulation", []),
    "help": ("_help", []),
    "ajuda": ("_help", []),
    "exportar": ("export_csv", ["output_path"]),
    "export": ("export_csv", ["output_path"]),
    "relatorio": ("export_report", ["output_path"]),
    "report": ("export_report", ["output_path"]),
    "pdf": ("export_pdf", ["output_path"]),
}


def parse_local_command(text: str) -> tuple[str | None, dict[str, Any]]:
    """Parse a local command into (tool_name, tool_input).

    Supports:
      resumo
      modelos
      modelo VCB_RR
      set VCB_RR T_OPEN 0.05
      componentes BRANCH resistor
      sweep VCB_RR T_OPENr 0.01 0.05 5
    """
    parts = text.strip().split()
    if not parts:
        return None, {}

    cmd = parts[0].lower()

    # Special: export command — exportar <path> [metrics|waveforms]
    if cmd in ("exportar", "export") and len(parts) >= 2:
        mode = parts[2] if len(parts) >= 3 else "metrics"
        return "export_csv", {"output_path": parts[1], "mode": mode}

    # Special: set command
    if cmd == "set" and len(parts) >= 4:
        return "set_data_param", {
            "model_name": parts[1],
            "param_name": parts[2],
            "new_value": parts[3],
        }

    # Special: sweep command
    if cmd == "sweep" and len(parts) >= 5:
        steps = int(parts[5]) if len(parts) > 5 else 5
        return "parametric_sweep", {
            "model_name": parts[1],
            "param_name": parts[2],
            "start": float(parts[3]),
            "end": float(parts[4]),
            "steps": steps,
        }

    # Special: componentes with filters
    if cmd in ("componentes", "components") and len(parts) >= 2:
        tool_input: dict[str, Any] = {}
        if parts[1].upper() in ("BRANCH", "SWITCH", "SOURCE"):
            tool_input["section"] = parts[1].upper()
            if len(parts) >= 3:
                tool_input["semantic_type"] = parts[2]
        else:
            tool_input["semantic_type"] = parts[1]
        return "list_components", tool_input

    # Standard command lookup
    if cmd in _COMMANDS:
        tool_name, required_args = _COMMANDS[cmd]
        tool_input = {}
        for i, arg_name in enumerate(required_args):
            if i + 1 < len(parts):
                tool_input[arg_name] = parts[i + 1]
            else:
                return None, {"error": f"Falta argumento: {arg_name}"}
        return tool_name, tool_input

    return None, {}


def format_result(result: dict[str, Any]) -> str:
    """Format a tool call result as readable text."""
    if not result.get("success", True):
        return f"Erro: {result.get('error', 'desconhecido')}"

    # Remove success key for cleaner display
    display = {k: v for k, v in result.items() if k != "success"}

    # Special formatting for common results
    if "messages" in display:
        # Validation result
        lines = [f"Validacao: {display.get('errors', 0)} erros, {display.get('warnings', 0)} avisos, {display.get('info', 0)} info"]
        for msg in display["messages"][:20]:
            lines.append(f"  [{msg['severity']}] {msg['code']}: {msg['message']}")
        if len(display["messages"]) > 20:
            lines.append(f"  ... +{len(display['messages']) - 20} mensagens")
        return "\n".join(lines)

    if "models" in display and isinstance(display["models"], list):
        if display["models"] and isinstance(display["models"][0], dict):
            lines = [f"Models ({len(display['models'])}):"]
            for m in display["models"]:
                lines.append(f"  {m.get('name', '?')}: {m.get('inputs', '?')}in {m.get('outputs', '?')}out {m.get('data', '?')}data")
            return "\n".join(lines)

    if "report" in display:
        return display["report"]

    # Generic JSON-like display
    return json.dumps(display, indent=2, ensure_ascii=False, default=str)


# v0.28.3-PRO Onda 3.5: pt-BR com acentos corretos
_HELP_TEXT = """Comandos disponíveis:
  resumo / summary        — resumo do projeto
  resumo / summary        — resumo do projeto
  componentes [tipo]      — listar componentes do esquemático
  nós / nodes             — listar nós elétricos
  analisar curto / sc     — análise de curto-circuito IEC 60909
  analisar coord          — coordenação 50/51 IEEE 242
  analisar arc-flash / af — energia incidente NBR 17227 / IEEE 1584
  analisar pf             — fluxo de potência IEEE 399
  laudo <bus>             — gerar laudo técnico (HTML/PDF)
  relatório <path>        — gerar relatório HTML
  pdf <path>              — gerar relatório PDF
  abrir <caminho.sch>     — abrir esquemático
  salvar <caminho.sch>    — salvar esquemático
  ajuda / help            — esta mensagem

Texto livre requer ANTHROPIC_API_KEY configurada.
Para análise transitória ATP/EMTP, use API Python (legacy)."""


# ======================================================================
# Claude API worker (runs in background thread)
# ======================================================================


class _ClaudeSignals(QObject):
    """Signals emitted from the Claude API background thread."""
    response_ready = Signal(str)  # final text response
    tool_call = Signal(str, str)  # tool_name, formatted result
    error = Signal(str)


class _ClaudeWorker(threading.Thread):
    """Runs a Claude API conversation turn in background."""

    def __init__(
        self,
        client: "anthropic.Anthropic",
        messages: list[dict],
        tools: list[dict],
        system_prompt: str,
        dispatcher: AgentDispatcher,
        signals: _ClaudeSignals,
    ) -> None:
        super().__init__(daemon=True)
        self._client = client
        self._messages = messages
        self._tools = tools
        self._system = system_prompt
        self._dispatcher = dispatcher
        self._signals = signals

    def run(self) -> None:
        try:
            self._agentic_loop()
        except Exception as e:
            self._signals.error.emit(str(e))

    def _agentic_loop(self) -> None:
        messages = list(self._messages)
        max_turns = 10

        for _ in range(max_turns):
            response = self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=self._system,
                tools=self._tools,
                messages=messages,
            )

            # Collect text and tool_use blocks
            text_parts = []
            tool_uses = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)

            # If there are tool calls, execute them
            if tool_uses:
                # Add assistant message
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for tu in tool_uses:
                    result = self._dispatcher.process_tool_call(tu.name, tu.input)
                    self._signals.tool_call.emit(
                        tu.name,
                        format_result(result),
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })

                messages.append({"role": "user", "content": tool_results})

                # If stop_reason is end_turn (text + tools), emit text
                if text_parts and response.stop_reason == "end_turn":
                    self._signals.response_ready.emit("\n".join(text_parts))
                    return

                # Continue loop for more tool calls
                continue

            # No tool calls — emit final text
            if text_parts:
                self._signals.response_ready.emit("\n".join(text_parts))
            return

        self._signals.error.emit("Limite de turnos atingido (10).")


# ======================================================================
# Chat Widget
# ======================================================================


class ChatWidget(QWidget):
    """Chat interface for the Olivas Power System Studio agent."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._api = ProjectAPI()
        self._dispatcher = AgentDispatcher(self._api)
        self._claude_client = None
        self._conversation: list[dict] = []
        self._signals = _ClaudeSignals()
        # v0.91.7: Qt.QueuedConnection EXPLÍCITO porque
        # _ClaudeWorker é ``threading.Thread`` (não QThread).
        # Emit de Python thread sem queued connection causa
        # "Cannot create children for a parent that is in a
        # different thread" quando slot manipula widgets.
        # Padrão alinhado com v0.91.7 SignalRelay no async_runner.
        self._signals.response_ready.connect(
            self._on_claude_response, Qt.QueuedConnection,
        )
        self._signals.tool_call.connect(
            self._on_claude_tool_call, Qt.QueuedConnection,
        )
        self._signals.error.connect(
            self._on_claude_error, Qt.QueuedConnection,
        )
        self._worker: Optional[_ClaudeWorker] = None
        self._palette = DARK

        self._init_claude()
        self._build_ui()

    def _init_claude(self) -> None:
        """
        v0.81: usa centralized api_key_manager — checa
        QSettings primeiro, depois env, depois .env file,
        depois ~/.olivas_atp_studio/api_keys.json.
        """
        from app.core.api_key_manager import get_anthropic_api_key
        api_key = get_anthropic_api_key() or ""
        if api_key:
            try:
                import anthropic
                self._claude_client = anthropic.Anthropic(api_key=api_key)
            except Exception:
                self._claude_client = None

    def apply_theme(self, palette: dict[str, str]) -> None:
        """Update palette colors."""
        self._palette = palette

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Chat history
        self.history = QPlainTextEdit()
        self.history.setReadOnly(True)
        self.history.setFont(QFont(MONO_FONT, MONO_SIZE))
        self.history.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        layout.addWidget(self.history)

        # Input row
        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setFont(QFont(MONO_FONT, MONO_SIZE))
        self.input_field.returnPressed.connect(self._on_send)
        input_row.addWidget(self.input_field)

        self.send_btn = QPushButton("Enviar")
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.send_btn)

        layout.addLayout(input_row)

        # Welcome message
        mode = "Claude API" if self._claude_client else "comandos locais"
        self.input_field.setPlaceholderText(
            "Pergunte algo ou digite um comando (ajuda)..."
            if self._claude_client
            else "Digite um comando (ajuda para ver opcoes)..."
        )
        self._append_system(
            f"Olivas Power System Studio — modo: {mode}\n"
            "Digite 'ajuda' para ver os comandos disponíveis.\n"
            "Abra um esquemático .sch ou crie um novo via paleta."
        )

    def sync_project(self, project) -> None:
        """Sync the chat API with the main window's project."""
        self._api.project = project

    def _on_send(self) -> None:
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self._append_user(text)

        # Try local command first
        tool_name, tool_input = parse_local_command(text)

        if tool_name == "_help":
            self._append_system(_HELP_TEXT)
            return

        if tool_name is not None:
            result = self._dispatcher.process_tool_call(tool_name, tool_input)
            formatted = format_result(result)
            self._append_agent(formatted)
            return

        if "error" in tool_input:
            self._append_system(tool_input["error"])
            return

        # Not a local command — try Claude API
        if self._claude_client is None:
            self._append_system(
                f"Comando nao reconhecido: '{text.split()[0]}'\n"
                "Modo local: apenas comandos estruturados.\n"
                "Configure ANTHROPIC_API_KEY para conversa livre."
            )
            return

        self._send_to_claude(text)

    def _send_to_claude(self, text: str) -> None:
        """Send message to Claude API in background thread."""
        self._conversation.append({"role": "user", "content": text})

        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)
        self._append_system("Pensando...")

        self._worker = _ClaudeWorker(
            client=self._claude_client,
            messages=list(self._conversation),
            tools=get_tool_definitions(),
            system_prompt=self._dispatcher.get_system_prompt(),
            dispatcher=self._dispatcher,
            signals=self._signals,
        )
        self._worker.start()

    def _on_claude_response(self, text: str) -> None:
        """Handle final text response from Claude."""
        self._conversation.append({"role": "assistant", "content": text})
        self._append_agent(text)
        self._enable_input()

    def _on_claude_tool_call(self, tool_name: str, result: str) -> None:
        """Show tool call execution in chat."""
        self._append_colored(f"[tool: {tool_name}]", QColor(self._palette["chat_tool"]))
        self._append_agent(result)

    def _on_claude_error(self, error: str) -> None:
        """Handle Claude API error."""
        self._append_system(f"Erro Claude API: {error}")
        self._enable_input()

    def _enable_input(self) -> None:
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def _append_user(self, text: str) -> None:
        self._append_colored(f"> {text}", QColor(self._palette["chat_user"]))

    def _append_agent(self, text: str) -> None:
        self._append_colored(text, QColor(self._palette["chat_agent"]))

    def _append_system(self, text: str) -> None:
        self._append_colored(text, QColor(self._palette["chat_system"]))

    def _append_colored(self, text: str, color: QColor) -> None:
        cursor = self.history.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor.insertText(text + "\n", fmt)

        self.history.setTextCursor(cursor)
        self.history.ensureCursorVisible()
