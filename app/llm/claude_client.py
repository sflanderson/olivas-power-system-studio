"""
app.llm.claude_client — cliente wrapper para a API Anthropic (Claude).

Responsabilidades
-----------------

* Inicializar ``anthropic.Anthropic`` com API key de variável de
  ambiente ``ANTHROPIC_API_KEY`` (fallback para arg do construtor).
* Combinar tools do catálogo (``catalog_to_tools``) com tools de
  projeto (``agent.get_tool_definitions``).
* Loop de tool_use: envia mensagem → Claude retorna tool_use →
  dispatcher executa → retorna resultado → Claude continua até
  ``stop_reason="end_turn"``.
* Logging básico de uso (tokens, rodadas).

Design de baixo acoplamento
---------------------------

* O cliente NÃO importa PySide6 (roda em processo separado, em
  CLI, ou em um worker Qt). Só precisa de um objeto "dispatcher"
  que implemente ``dispatch_tool(name, input) -> dict``.
* O cliente NÃO inicializa o registry — chama
  ``get_default_registry()`` via ``catalog_to_tools`` e
  ``build_system_prompt`` que sabem fazer lazy.

Uso típico (síncrono)
---------------------

.. code-block:: python

    from app.llm.claude_client import ClaudeClient

    client = ClaudeClient(dispatcher=my_editor_dispatcher)
    reply = client.chat(
        "Adicione um resistor de 100 Ω entre N1 e GND."
    )
    print(reply.final_text)
    print(reply.tool_calls)

Custo / Prompt caching
----------------------

O system prompt pode ter ~3-5KB (40 componentes + guides). Para
reduzir custo em sessões multi-turno, o cliente marca o system
prompt como ``cache_control={"type": "ephemeral"}`` quando
``enable_caching=True`` (default).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from app.llm.catalog_tools import catalog_to_tools, dispatch_add_tool
from app.llm.system_prompt import build_system_prompt


# ---------------------------------------------------------------------------
# Protocolos
# ---------------------------------------------------------------------------


class ToolDispatcher(Protocol):
    """Interface que o cliente espera para executar tools."""

    def dispatch(
        self, tool_name: str, tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        """Executa a tool e retorna dict com ``success`` + payload."""
        ...


# ---------------------------------------------------------------------------
# Dispatcher default: só catalog add_* (sem ProjectAPI)
# ---------------------------------------------------------------------------


class EditorDispatcher:
    """
    Dispatcher simples que rota ``add_<CODE>`` para
    :func:`app.llm.catalog_tools.dispatch_add_tool` via um editor
    PySide6 (ou equivalente duck-typed).

    Não lida com tools de projeto (open_file, list_models, etc.) —
    para isso, use :class:`FullDispatcher` (veja abaixo).
    """

    def __init__(self, editor) -> None:
        self._editor = editor

    def dispatch(
        self, tool_name: str, tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        if tool_name.startswith("add_"):
            return dispatch_add_tool(tool_name, tool_input, self._editor)
        return {
            "success": False,
            "error": f"Tool {tool_name!r} não suportada por EditorDispatcher.",
        }


# ---------------------------------------------------------------------------
# Resultado da conversa
# ---------------------------------------------------------------------------


@dataclass
class ChatReply:
    """Resultado de uma conversa com Claude."""

    final_text: str = ""
    """Texto final (após todos os tool uses) que o Claude produziu."""

    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    """Lista de dicts ``{"name": str, "input": dict, "result": dict}``."""

    rounds: int = 0
    """Quantas rodadas de tool_use foram feitas."""

    stop_reason: str = ""
    """Razão final do Claude: end_turn, max_tokens, stop_sequence, etc."""

    input_tokens: int = 0
    output_tokens: int = 0


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------


class ClaudeClient:
    """
    Wrapper sobre ``anthropic.Anthropic`` específico para Olivas.

    Parameters
    ----------
    dispatcher:
        Objeto que implementa ``dispatch(tool_name, tool_input)``.
        Em produção, normalmente um :class:`EditorDispatcher`.
    api_key:
        API key Anthropic. Default: ``os.environ["ANTHROPIC_API_KEY"]``.
    model:
        ID do modelo Claude. Default: ``claude-sonnet-4-5-20250929``
        (bom custo-benefício para tool use).
    max_rounds:
        Limite de rodadas de tool_use por ``chat()`` — evita loops
        infinitos se o modelo ficar preso chamando tools.
    max_tokens:
        Máximo de tokens de saída por request.
    enable_caching:
        Se True, marca o system prompt como cache_control ephemeral
        — reduz custo em sessões multi-turno. Default True.
    anthropic_cls:
        Classe para instanciar. Default: ``anthropic.Anthropic``.
        Override útil em testes (mock class).
    """

    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(
        self,
        dispatcher: ToolDispatcher,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_rounds: int = 8,
        max_tokens: int = 4096,
        enable_caching: bool = True,
        anthropic_cls: Optional[type] = None,
    ) -> None:
        if api_key is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        # Note: client pode ser criado sem API key para testes offline.
        # O erro aparece só na chamada real .messages.create.
        if anthropic_cls is None:
            try:
                import anthropic
                anthropic_cls = anthropic.Anthropic
            except ImportError as e:  # pragma: no cover
                raise ImportError(
                    "Pacote 'anthropic' não instalado — adicione ao "
                    "requirements.txt"
                ) from e
        self._client = anthropic_cls(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL
        self._dispatcher = dispatcher
        self._max_rounds = max_rounds
        self._max_tokens = max_tokens
        self._enable_caching = enable_caching

    def _build_tools(self) -> list[dict[str, Any]]:
        """Monta lista de tools combinando catálogo + project API."""
        return catalog_to_tools()

    def _build_system(self) -> list[dict[str, Any]]:
        """System prompt como lista (formato Anthropic v1+)."""
        text = build_system_prompt()
        block: dict[str, Any] = {"type": "text", "text": text}
        if self._enable_caching:
            block["cache_control"] = {"type": "ephemeral"}
        return [block]

    def chat(self, user_message: str) -> ChatReply:
        """
        Envia uma mensagem e processa o loop de tool_use.

        Loop:
        1. Envia messages + tools + system.
        2. Se ``stop_reason == "tool_use"``, executa cada tool_use
           via dispatcher, anexa resultados em ``tool_result`` blocks,
           e itera.
        3. Se ``stop_reason == "end_turn"`` (ou outro), para.

        Parameters
        ----------
        user_message:
            A mensagem do usuário em português natural.

        Returns
        -------
        ChatReply
            Com ``final_text`` (resposta textual final), ``tool_calls``
            (lista de tools executadas) e ``rounds``.
        """
        tools = self._build_tools()
        system = self._build_system()

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_message},
        ]

        reply = ChatReply()

        for round_idx in range(self._max_rounds):
            reply.rounds = round_idx + 1
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                tools=tools,
                messages=messages,
            )

            # Acumular uso
            usage = getattr(response, "usage", None)
            if usage is not None:
                reply.input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
                reply.output_tokens += int(getattr(usage, "output_tokens", 0) or 0)

            # Extrair texto e tool_use blocks
            assistant_blocks: list[dict[str, Any]] = []
            tool_uses: list[tuple[str, str, dict[str, Any]]] = []
            final_text_this_round: list[str] = []

            for block in response.content:
                btype = getattr(block, "type", None)
                if btype == "text":
                    final_text_this_round.append(block.text)
                    assistant_blocks.append(
                        {"type": "text", "text": block.text}
                    )
                elif btype == "tool_use":
                    assistant_blocks.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                    tool_uses.append((block.id, block.name, dict(block.input)))

            # Anexa resposta do assistant ao histórico
            messages.append({"role": "assistant", "content": assistant_blocks})

            stop = getattr(response, "stop_reason", "")
            reply.stop_reason = stop

            if not tool_uses:
                # Sem tool_use → fim
                reply.final_text = "\n".join(final_text_this_round)
                break

            # Executa tools e envia como tool_result
            tool_result_blocks: list[dict[str, Any]] = []
            for tool_use_id, name, tool_input in tool_uses:
                result = self._dispatcher.dispatch(name, tool_input)
                reply.tool_calls.append({
                    "name": name,
                    "input": tool_input,
                    "result": result,
                })
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": str(result),
                    "is_error": not result.get("success", True),
                })
            messages.append({"role": "user", "content": tool_result_blocks})
        else:
            # Atingiu max_rounds
            reply.stop_reason = "max_rounds"

        return reply
