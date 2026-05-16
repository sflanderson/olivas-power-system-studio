"""Tests for LLM agent — dispatcher, tools, and chat parser."""
from __future__ import annotations

from app.gui.chat_widget import format_result, parse_local_command
from app.llm.agent import AgentDispatcher, get_tool_definitions
from app.llm.project_api import ProjectAPI
from tests.conftest import REF_FILE


class TestToolDefinitions:
    def test_tool_count(self):
        tools = get_tool_definitions()
        assert len(tools) == 19

    def test_tool_names(self):
        tools = get_tool_definitions()
        names = {t["name"] for t in tools}
        expected = {
            "open_file", "save_file", "project_summary",
            "list_models", "list_uses", "get_model_info", "get_use_info",
            "list_components", "list_nodes", "get_header",
            "set_data_param", "set_model_default", "set_input_mapping",
            "validate_all", "run_simulation", "parametric_sweep",
            "export_csv", "export_report", "export_pdf",
        }
        assert names == expected

    def test_tools_have_input_schema(self):
        for tool in get_tool_definitions():
            assert "input_schema" in tool
            assert "name" in tool
            assert "description" in tool


class TestAgentDispatcher:
    def test_open_file(self):
        api = ProjectAPI()
        dispatcher = AgentDispatcher(api)
        result = dispatcher.process_tool_call("open_file", {"file_path": REF_FILE})
        assert result["success"] is True
        assert result["models"] == 4

    def test_project_summary(self):
        api = ProjectAPI()
        api.open_file(REF_FILE)
        dispatcher = AgentDispatcher(api)
        result = dispatcher.process_tool_call("project_summary", {})
        assert result["success"] is True
        assert "models" in result

    def test_list_models(self):
        api = ProjectAPI()
        api.open_file(REF_FILE)
        dispatcher = AgentDispatcher(api)
        result = dispatcher.process_tool_call("list_models", {})
        assert result["success"] is True
        assert len(result["models"]) == 4

    def test_get_header(self):
        api = ProjectAPI()
        api.open_file(REF_FILE)
        dispatcher = AgentDispatcher(api)
        result = dispatcher.process_tool_call("get_header", {})
        assert result["success"] is True
        assert result["delta_t"] == 1e-6

    def test_validate_all(self):
        api = ProjectAPI()
        api.open_file(REF_FILE)
        dispatcher = AgentDispatcher(api)
        result = dispatcher.process_tool_call("validate_all", {})
        assert result["success"] is True
        assert "total" in result

    def test_set_data_param(self):
        api = ProjectAPI()
        api.open_file(REF_FILE)
        dispatcher = AgentDispatcher(api)
        result = dispatcher.process_tool_call("set_data_param", {
            "model_name": "VCB_RR",
            "param_name": "T_OPENR",
            "new_value": "0.05",
        })
        assert result["success"] is True
        assert result["new_value"] == "0.05"

    def test_unknown_tool(self):
        api = ProjectAPI()
        dispatcher = AgentDispatcher(api)
        result = dispatcher.process_tool_call("nonexistent", {})
        assert result["success"] is False

    def test_no_project_loaded(self):
        api = ProjectAPI()
        dispatcher = AgentDispatcher(api)
        result = dispatcher.process_tool_call("list_models", {})
        assert result["success"] is False


class TestChatParser:
    def test_resumo(self):
        assert parse_local_command("resumo") == ("project_summary", {})

    def test_modelos(self):
        assert parse_local_command("modelos") == ("list_models", {})

    def test_modelo_with_name(self):
        assert parse_local_command("modelo VCB_RR") == ("get_model_info", {"model_name": "VCB_RR"})

    def test_set_command(self):
        name, params = parse_local_command("set VCB_RR T_OPEN 0.05")
        assert name == "set_data_param"
        assert params["model_name"] == "VCB_RR"
        assert params["param_name"] == "T_OPEN"
        assert params["new_value"] == "0.05"

    def test_sweep_command(self):
        name, params = parse_local_command("sweep VCB_RR T_OPEN 0.01 0.05 5")
        assert name == "parametric_sweep"
        assert params["steps"] == 5

    def test_export_csv(self):
        name, params = parse_local_command("exportar out.csv waveforms")
        assert name == "export_csv"
        assert params["mode"] == "waveforms"

    def test_report(self):
        assert parse_local_command("relatorio out.html") == ("export_report", {"output_path": "out.html"})

    def test_help(self):
        assert parse_local_command("ajuda") == ("_help", {})

    def test_unknown_command(self):
        name, params = parse_local_command("xyz")
        assert name is None

    def test_empty_input(self):
        name, params = parse_local_command("")
        assert name is None

    def test_componentes_with_section(self):
        name, params = parse_local_command("componentes BRANCH resistor")
        assert name == "list_components"
        assert params["section"] == "BRANCH"
        assert params["semantic_type"] == "resistor"


class TestFormatResult:
    def test_error_result(self):
        text = format_result({"success": False, "error": "test error"})
        assert "test error" in text

    def test_validation_result(self):
        text = format_result({
            "success": True,
            "errors": 1, "warnings": 2, "info": 3,
            "messages": [{"severity": "ERRO", "code": "E1", "message": "test"}],
        })
        assert "1 erros" in text
