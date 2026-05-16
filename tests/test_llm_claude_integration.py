"""
tests/test_llm_claude_integration.py — v0.23.0: integração Claude API.

Cobre:

* ``catalog_tools.spec_to_tool``: forma do tool correspondente a um
  ``ComponentSpec`` (name, description, input_schema).
* ``catalog_to_tools``: filtros por categoria, excludes unsupported.
* ``dispatch_add_tool``: execução de um tool_use no editor — com
  propriedades aplicadas.
* ``system_prompt``: contém códigos do catálogo, convenções, guide.
* ``ClaudeClient``: com mock do SDK Anthropic, verifica o loop
  tool_use sem chamada de rede real.

Não cobre:
* Chamadas reais à API Anthropic (requer API key + rede).
"""

from __future__ import annotations

from typing import Any, Optional

import pytest

from app.llm.catalog_tools import (
    catalog_to_tools,
    dispatch_add_tool,
    spec_to_tool,
)
from app.llm.claude_client import ChatReply, ClaudeClient, EditorDispatcher
from app.llm.system_prompt import build_system_prompt
from app.preprocessor.spec import get_default_registry


# ---------------------------------------------------------------------------
# Tools: shape por componente
# ---------------------------------------------------------------------------


class TestSpecToTool:
    def test_R_tool_structure(self):
        spec = get_default_registry().require("R")
        tool = spec_to_tool(spec)
        assert tool["name"] == "add_R"
        assert "Resistor" in tool["description"] or "resistor" in tool["description"].lower()
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        # Propriedades de identidade (comuns a TODOS os tools)
        for key in ("name", "x", "y", "rotation", "mirror"):
            assert key in schema["properties"], f"key {key!r} ausente"
        # Propriedade específica do R
        assert "R" in schema["properties"]
        r_entry = schema["properties"]["R"]
        assert r_entry["type"] == "number"
        assert "ohm" in r_entry.get("description", "").lower()

    def test_VCB_tool_has_reignition_params(self):
        spec = get_default_registry().require("VCB")
        tool = spec_to_tool(spec)
        # 10 params específicos + 5 identidade
        props = tool["input_schema"]["properties"]
        for name in (
            "T_open", "T_close", "I_chop", "sigma_I_chop",
            "didt_crit", "k_dielec", "U0_dielec", "T_bounce", "Seed",
        ):
            assert name in props, f"VCB spec sem {name!r}"
        # Seed é integer
        assert props["Seed"]["type"] == "integer"
        # I_chop é number com mínimo 0
        assert props["I_chop"]["type"] == "number"
        assert props["I_chop"].get("minimum") == 0.0

    def test_C_tool_enum_polarity(self):
        """Capacitor tem prop 'polarity' que é ENUM."""
        spec = get_default_registry().require("C")
        tool = spec_to_tool(spec)
        props = tool["input_schema"]["properties"]
        # polarity deve ser enum
        polarity_entry = props["polarity"]
        assert polarity_entry["type"] == "string"
        assert "enum" in polarity_entry
        # Exatamente os choices declarados em C.ocomp
        assert set(polarity_entry["enum"]) == {"neutral", "positive", "negative"}

    def test_tool_input_schema_requires_name_only(self):
        """Apenas 'name' é required — demais campos têm default."""
        spec = get_default_registry().require("R")
        tool = spec_to_tool(spec)
        assert tool["input_schema"]["required"] == ["name"]

    def test_description_includes_typical_applications(self):
        spec = get_default_registry().require("VCB")
        tool = spec_to_tool(spec)
        desc = tool["description"]
        # Pelo menos uma das apps típicas deve aparecer
        apps = spec.llm_hints.typical_applications
        assert any(
            any(keyword in desc for keyword in app.lower().split()[:3])
            for app in apps
        ), f"Description não inclui typical_applications: {desc!r}"


# ---------------------------------------------------------------------------
# catalog_to_tools: filtros
# ---------------------------------------------------------------------------


class TestCatalogToTools:
    def test_returns_tools_for_all_atp_supported(self):
        tools = catalog_to_tools()
        names = {t["name"] for t in tools}
        # Todos os componentes com atp_supported=True devem estar
        for code in ("R", "L", "C", "VCB", "VCB3", "Diode", "Tr", "TLIN"):
            assert f"add_{code}" in names

    def test_excludes_unsupported_by_default(self):
        """Sim directives (.TR/.DC/.AC/etc., atp_supported=False) não entram."""
        tools = catalog_to_tools()
        names = {t["name"] for t in tools}
        for code in (".TR", ".DC", ".AC", ".SW", ".SP", "Eqn"):
            assert f"add_{code}" not in names, (
                f"Tool add_{code} não deveria existir "
                "(atp_supported=False)"
            )

    def test_filter_by_categories(self):
        tools = catalog_to_tools(categories=["passive"])
        names = {t["name"] for t in tools}
        assert {"add_R", "add_L", "add_C", "add_GND"}.issubset(names)
        # VCB não é passivo
        assert "add_VCB" not in names

    def test_include_unsupported(self):
        """Se exclude_unsupported=False, aparecem também sim directives."""
        tools = catalog_to_tools(exclude_unsupported=False)
        names = {t["name"] for t in tools}
        assert "add_.TR" in names or "add_Eqn" in names


# ---------------------------------------------------------------------------
# dispatch_add_tool: executa via editor
# ---------------------------------------------------------------------------


class TestDispatchAddTool:

    def _get_editor(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        return PpEditor()

    def test_dispatch_unknown_tool_returns_error(self, qapp):
        editor = self._get_editor(qapp)
        result = dispatch_add_tool("foo_bar", {"name": "X"}, editor)
        assert result["success"] is False

    def test_dispatch_add_R_creates_component(self, qapp):
        editor = self._get_editor(qapp)
        result = dispatch_add_tool(
            "add_R",
            {"name": "R_line", "x": 200, "y": 150, "R": 100.0},
            editor,
        )
        assert result["success"] is True
        assert result["code"] == "R"
        assert result["name"] == "R_line"
        assert result["position"] == [200, 150]
        # R aplicado na property 0 (do spec R)
        assert "R" in result["properties_applied"]

    def test_dispatch_unknown_code_returns_error(self, qapp):
        editor = self._get_editor(qapp)
        result = dispatch_add_tool(
            "add_XYZ_NOT_EXIST", {"name": "X"}, editor,
        )
        assert result["success"] is False
        assert "não existe" in result["error"] or "not" in result["error"].lower()


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_prompt_contains_main_codes(self):
        prompt = build_system_prompt()
        for code in ("R", "L", "C", "VCB", "Vac", "Tr", "TLIN", "Diode"):
            assert f"**{code}**" in prompt, (
                f"Prompt não menciona componente {code}"
            )

    def test_prompt_mentions_standards(self):
        prompt = build_system_prompt()
        assert "CIGRE" in prompt
        assert "IEEE 315" in prompt

    def test_prompt_mentions_add_tool_convention(self):
        prompt = build_system_prompt()
        assert "add_" in prompt or "add_<CODE>" in prompt

    def test_prompt_mentions_SI_units(self):
        prompt = build_system_prompt()
        assert "SI" in prompt
        # Deve mencionar pelo menos uma unidade SI básica
        assert "Ω" in prompt or "ohm" in prompt.lower()


# ---------------------------------------------------------------------------
# ClaudeClient com mock do SDK
# ---------------------------------------------------------------------------


class _MockBlock:
    """Simula um block do response.content (text ou tool_use)."""

    def __init__(self, type_: str, **kw) -> None:
        self.type = type_
        for k, v in kw.items():
            setattr(self, k, v)


class _MockUsage:
    def __init__(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _MockResponse:
    """Simula um response do messages.create."""

    def __init__(
        self,
        content: list,
        stop_reason: str = "end_turn",
        usage: Optional[_MockUsage] = None,
    ) -> None:
        self.content = content
        self.stop_reason = stop_reason
        self.usage = usage or _MockUsage(100, 50)


class _MockMessages:
    """Mock da subchain .messages."""

    def __init__(self, responses: list[_MockResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs) -> _MockResponse:
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("MockMessages: responses esgotadas")
        return self._responses.pop(0)


class _MockAnthropic:
    """Mock de anthropic.Anthropic."""

    def __init__(self, responses: list[_MockResponse]) -> None:
        self.messages = _MockMessages(responses)

    def __call__(self, *args, **kwargs):
        """Permite usar a classe como factory (ClaudeClient a chama)."""
        # Retorna self se usado via __init__
        return self


def _make_mock_cls(responses: list[_MockResponse]):
    """Retorna uma 'classe' que, ao ser instanciada, retorna um mock fixo."""
    mock_instance = _MockAnthropic(responses)

    class _FakeCls:
        def __init__(self, **kwargs):
            self.messages = mock_instance.messages

    return _FakeCls


class _CountingDispatcher:
    """Dispatcher que conta chamadas e retorna sucesso fixo."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def dispatch(
        self, name: str, inp: dict[str, Any]
    ) -> dict[str, Any]:
        self.calls.append((name, inp))
        return {
            "success": True, "name": inp.get("name", "?"),
            "code": name.replace("add_", ""),
        }


class TestClaudeClient:
    def test_chat_text_only_no_tool_use(self):
        """Se Claude responde apenas texto, final_text é preenchido."""
        responses = [
            _MockResponse(
                content=[_MockBlock("text", text="Olá, como posso ajudar?")],
                stop_reason="end_turn",
            ),
        ]
        dispatcher = _CountingDispatcher()
        client = ClaudeClient(
            dispatcher=dispatcher,
            api_key="test-key",
            anthropic_cls=_make_mock_cls(responses),
        )
        reply = client.chat("Oi")
        assert reply.final_text == "Olá, como posso ajudar?"
        assert reply.rounds == 1
        assert reply.tool_calls == []
        assert reply.stop_reason == "end_turn"
        assert reply.input_tokens > 0
        assert reply.output_tokens > 0

    def test_chat_with_single_tool_use(self):
        """Claude chama add_R, dispatcher executa, Claude finaliza."""
        responses = [
            _MockResponse(
                content=[
                    _MockBlock(
                        "tool_use",
                        id="toolu_001",
                        name="add_R",
                        input={"name": "R1", "x": 100, "y": 100, "R": 100},
                    ),
                ],
                stop_reason="tool_use",
            ),
            _MockResponse(
                content=[_MockBlock("text", text="Adicionado. R1 = 100 Ω.")],
                stop_reason="end_turn",
            ),
        ]
        dispatcher = _CountingDispatcher()
        client = ClaudeClient(
            dispatcher=dispatcher,
            api_key="test-key",
            anthropic_cls=_make_mock_cls(responses),
        )
        reply = client.chat("Adicione um R de 100 Ω")
        assert reply.rounds == 2
        assert len(reply.tool_calls) == 1
        assert reply.tool_calls[0]["name"] == "add_R"
        assert reply.tool_calls[0]["input"]["name"] == "R1"
        assert reply.tool_calls[0]["result"]["success"] is True
        assert "100" in reply.final_text or "R1" in reply.final_text
        # Dispatcher foi chamado uma vez
        assert len(dispatcher.calls) == 1

    def test_chat_respects_max_rounds(self):
        """Se Claude ficar em loop, para em max_rounds."""
        # Cria 10 respostas de tool_use consecutivas (Claude nunca para)
        responses = [
            _MockResponse(
                content=[
                    _MockBlock(
                        "tool_use",
                        id=f"toolu_{i:03d}",
                        name="add_R",
                        input={"name": f"R{i}"},
                    ),
                ],
                stop_reason="tool_use",
            )
            for i in range(20)
        ]
        dispatcher = _CountingDispatcher()
        client = ClaudeClient(
            dispatcher=dispatcher,
            api_key="test-key",
            max_rounds=3,
            anthropic_cls=_make_mock_cls(responses),
        )
        reply = client.chat("Loop infinito?")
        assert reply.rounds == 3
        assert reply.stop_reason == "max_rounds"
        assert len(dispatcher.calls) == 3

    def test_system_prompt_is_included_in_request(self):
        responses = [
            _MockResponse(
                content=[_MockBlock("text", text="ok")],
                stop_reason="end_turn",
            ),
        ]
        mock_cls = _make_mock_cls(responses)
        client = ClaudeClient(
            dispatcher=_CountingDispatcher(),
            api_key="test-key",
            anthropic_cls=mock_cls,
        )
        reply = client.chat("hi")
        # Primeira chamada deve ter system + tools
        last_call = client._client.messages.calls[0]
        assert "system" in last_call
        assert "tools" in last_call
        assert len(last_call["tools"]) > 0  # pelo menos 1 tool
        # System deve ser uma lista (formato novo) com cache_control
        system = last_call["system"]
        assert isinstance(system, list)
        assert system[0]["type"] == "text"
        assert "cache_control" in system[0]

    def test_editor_dispatcher_rejects_non_add_tool(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        editor = PpEditor()
        disp = EditorDispatcher(editor)
        result = disp.dispatch("list_models", {})
        assert result["success"] is False

    def test_editor_dispatcher_handles_add(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        editor = PpEditor()
        disp = EditorDispatcher(editor)
        result = disp.dispatch(
            "add_L", {"name": "L_src", "x": 100, "y": 100, "L": 0.001},
        )
        assert result["success"] is True
        assert result["code"] == "L"


# ---------------------------------------------------------------------------
# Fixture qapp para testes que precisam de PpEditor
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        pytest.skip("PySide6 não instalado")
    return QApplication.instance() or QApplication([])
