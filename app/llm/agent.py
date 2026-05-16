"""Olivas ATP Studio LLM Agent — dispatches natural language to ProjectAPI.

This module provides:
1. AgentDispatcher: maps intent names to ProjectAPI method calls
2. Tool definitions for Claude API tool_use format
3. process_tool_call: executes a tool call and returns structured result

The agent can be connected to any LLM that supports tool/function calling.
The Claude API integration is done at the application level — this module
provides the tool definitions and execution layer.
"""
from __future__ import annotations

from typing import Any, Optional

from app.llm.intents import INTENTS, Intent, IntentCategory
from app.llm.parametric import SweepParameter, format_sweep_report, linspace_values, run_parametric_sweep
from app.llm.project_api import ProjectAPI


# ======================================================================
# Tool definitions for Claude API tool_use
# ======================================================================


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return tool definitions in Claude API tool_use format.

    These can be passed directly to the Anthropic API's `tools` parameter.
    """
    return [
        {
            "name": "open_file",
            "description": "Open and parse an ATP file. Returns project summary.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the .atp file"},
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "save_file",
            "description": "Save the current project to an ATP file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Output file path"},
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "project_summary",
            "description": "Get a structured summary of the loaded ATP project (models, uses, components, nodes).",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "list_models",
            "description": "List all MODEL definitions with input/output/data counts.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "list_uses",
            "description": "List all USE instances with their parameters.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_model_info",
            "description": "Get detailed information about a specific MODEL (inputs, outputs, data defaults, variables, code).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "model_name": {"type": "string", "description": "Name of the MODEL"},
                },
                "required": ["model_name"],
            },
        },
        {
            "name": "get_use_info",
            "description": "Get detailed information about a specific USE instance (inputs, data values, outputs).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "model_name": {"type": "string", "description": "Name of the MODEL the USE references"},
                },
                "required": ["model_name"],
            },
        },
        {
            "name": "list_components",
            "description": "List circuit components (branches, switches, sources) with optional filtering by section or semantic type.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["BRANCH", "SWITCH", "SOURCE"],
                        "description": "Filter by section",
                    },
                    "semantic_type": {
                        "type": "string",
                        "description": "Filter by semantic type (e.g. 'resistor', 'vcb', 'snubber', 'ac')",
                    },
                },
            },
        },
        {
            "name": "list_nodes",
            "description": "List all circuit nodes with their connection sources.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_header",
            "description": "Get simulation header parameters (delta_t, t_max, frequency).",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "set_data_param",
            "description": "Change a DATA parameter value in a USE instance.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "model_name": {"type": "string", "description": "USE model name"},
                    "param_name": {"type": "string", "description": "Parameter name"},
                    "new_value": {"type": "string", "description": "New value"},
                },
                "required": ["model_name", "param_name", "new_value"],
            },
        },
        {
            "name": "set_model_default",
            "description": "Change a default value in a MODEL DATA definition.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "model_name": {"type": "string", "description": "MODEL name"},
                    "param_name": {"type": "string", "description": "Parameter name"},
                    "new_value": {"type": "string", "description": "New default value"},
                },
                "required": ["model_name", "param_name", "new_value"],
            },
        },
        {
            "name": "set_input_mapping",
            "description": "Change an INPUT mapping in a USE instance.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "model_name": {"type": "string", "description": "USE model name"},
                    "local_name": {"type": "string", "description": "Local input name"},
                    "mapped_to": {"type": "string", "description": "Signal to map to"},
                },
                "required": ["model_name", "local_name", "mapped_to"],
            },
        },
        {
            "name": "validate_all",
            "description": "Run all validations (structural, physics, VCB domain) and return results.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "run_simulation",
            "description": "Execute the ATP simulation on the loaded project.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "parametric_sweep",
            "description": "Run a parametric sweep varying one parameter across multiple values.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "model_name": {"type": "string", "description": "USE model name"},
                    "param_name": {"type": "string", "description": "Parameter to sweep"},
                    "start": {"type": "number", "description": "Start value"},
                    "end": {"type": "number", "description": "End value"},
                    "steps": {"type": "integer", "description": "Number of steps", "default": 5},
                },
                "required": ["model_name", "param_name", "start", "end"],
            },
        },
        {
            "name": "export_csv",
            "description": "Export simulation results to CSV. Mode 'metrics' exports transient metrics summary; 'waveforms' exports raw time-domain data.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "Output CSV file path"},
                    "mode": {
                        "type": "string",
                        "enum": ["metrics", "waveforms"],
                        "description": "Export mode",
                        "default": "metrics",
                    },
                },
                "required": ["output_path"],
            },
        },
        {
            "name": "export_report",
            "description": "Generate a complete HTML report with logo, project summary, validation results, component breakdown, USE DATA parameters, and transient metrics.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "Output HTML file path"},
                },
                "required": ["output_path"],
            },
        },
        {
            "name": "export_pdf",
            "description": "Generate a PDF report with project summary, validation results, component breakdown, USE DATA parameters, and transient metrics.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "Output PDF file path"},
                },
                "required": ["output_path"],
            },
        },
    ]


# ======================================================================
# Agent Dispatcher
# ======================================================================


class AgentDispatcher:
    """Dispatches tool calls to the ProjectAPI.

    Usage:
        api = ProjectAPI()
        dispatcher = AgentDispatcher(api)

        # From Claude API tool_use response:
        result = dispatcher.process_tool_call("list_models", {})
        result = dispatcher.process_tool_call("set_data_param", {
            "model_name": "VCB_RR",
            "param_name": "T_OPEN",
            "new_value": "0.05",
        })
    """

    def __init__(self, api: ProjectAPI) -> None:
        self.api = api

    def process_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call and return structured result."""
        dispatch = {
            "open_file": lambda: self.api.open_file(tool_input["file_path"]),
            "save_file": lambda: self.api.save_file(tool_input["file_path"]),
            "project_summary": lambda: self.api.project_summary(),
            "list_models": lambda: self.api.list_models(),
            "list_uses": lambda: self.api.list_uses(),
            "get_model_info": lambda: self.api.get_model_info(tool_input["model_name"]),
            "get_use_info": lambda: self.api.get_use_info(tool_input["model_name"]),
            "list_components": lambda: self.api.list_components(
                section=tool_input.get("section"),
                semantic_type=tool_input.get("semantic_type"),
            ),
            "list_nodes": lambda: self.api.list_nodes(),
            "get_header": lambda: self.api.get_header(),
            "set_data_param": lambda: self.api.set_data_param(
                tool_input["model_name"],
                tool_input["param_name"],
                tool_input["new_value"],
            ),
            "set_model_default": lambda: self.api.set_model_default(
                tool_input["model_name"],
                tool_input["param_name"],
                tool_input["new_value"],
            ),
            "set_input_mapping": lambda: self.api.set_input_mapping(
                tool_input["model_name"],
                tool_input["local_name"],
                tool_input["mapped_to"],
            ),
            "validate_all": lambda: self.api.validate_all(),
            "run_simulation": lambda: self.api.run_simulation(),
            "parametric_sweep": lambda: self._run_sweep(tool_input),
            "export_csv": lambda: self.api.export_csv(
                tool_input["output_path"],
                tool_input.get("mode", "metrics"),
            ),
            "export_report": lambda: self.api.export_report(
                tool_input["output_path"],
            ),
            "export_pdf": lambda: self.api.export_pdf(
                tool_input["output_path"],
            ),
        }

        handler = dispatch.get(tool_name)
        if handler is None:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        try:
            return handler()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_sweep(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Execute parametric sweep from tool call."""
        if self.api.project is None:
            return {"success": False, "error": "No project loaded"}

        model_name = tool_input["model_name"]
        param_name = tool_input["param_name"]
        start = float(tool_input["start"])
        end = float(tool_input["end"])
        steps = int(tool_input.get("steps", 5))

        values = linspace_values(start, end, steps)
        params = [SweepParameter(model_name, param_name, values)]

        result = run_parametric_sweep(
            self.api.project.file_path,
            params,
            self.api.runner,
        )

        return {
            "success": True,
            "total_cases": result.total_cases,
            "completed": result.completed,
            "failed": result.failed,
            "output_dir": result.output_dir,
            "report": format_sweep_report(result),
        }

    def get_system_prompt(self) -> str:
        """Return a system prompt describing the Olivas ATP Studio agent capabilities."""
        return (
            "You are an Olivas ATP Studio assistant — an expert in electromagnetic "
            "transient simulation using ATP/EMTP. You help users analyze, edit, "
            "validate, and simulate ATP circuit files.\n\n"
            "You have access to tools for:\n"
            "- Opening and saving ATP files\n"
            "- Querying project structure (models, uses, components, nodes)\n"
            "- Editing DATA parameters and INPUT/OUTPUT mappings\n"
            "- Running validations (structural, physical, VCB domain)\n"
            "- Executing ATP simulations\n"
            "- Running parametric sweeps\n\n"
            "Always explain what you find in terms the user can understand. "
            "When modifying parameters, confirm the change was applied. "
            "When running validations, summarize the most critical issues first."
        )
