"""Programmatic API for LLM agent interaction with Olivas ATP Studio.

LLM-002: Maps intents to concrete operations on the project.
LLM-010: Connects agent to the internal project API.

This API is designed to be called by an LLM agent (or any automation)
and returns structured results as dicts, making it easy to serialize
for LLM consumption.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from app.analysis.csv_export import export_metrics_csv, export_waveforms_csv
from app.analysis.report_export import export_html_report, export_pdf_report
from app.core.parser import parse_file
from app.core.project_model import AtpProject
from app.core.serializer import serialize_project
from app.simulation.results_reader import find_result_files, read_pl4
from app.simulation.runner import AtpRunner, RunResult
from app.validation.validator_models import validate_project
from app.validation.validator_physics import validate_physics
from app.validation.validator_vcb import validate_vcb


class ProjectAPI:
    """High-level API for interacting with an ATP project programmatically."""

    def __init__(self) -> None:
        self.project: Optional[AtpProject] = None
        self.runner = AtpRunner()
        self._last_run: Optional[RunResult] = None

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def open_file(self, file_path: str) -> dict[str, Any]:
        """Open and parse an ATP file."""
        path = Path(file_path)
        if not path.is_file():
            return {"success": False, "error": f"File not found: {file_path}"}
        self.project = parse_file(str(path))
        return {
            "success": True,
            "file": str(path),
            "models": len(self.project.models),
            "uses": len(self.project.uses),
            "branches": len(self.project.branches),
            "switches": len(self.project.switches),
            "sources": len(self.project.sources),
            "nodes": len(self.project.nodes),
        }

    def save_file(self, file_path: str) -> dict[str, Any]:
        """Serialize and save the project to a file."""
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        content = serialize_project(self.project)
        Path(file_path).write_text(content, encoding="utf-8")
        return {"success": True, "file": file_path, "lines": content.count("\n") + 1}

    def project_summary(self) -> dict[str, Any]:
        """Return a structured summary of the loaded project."""
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        p = self.project
        return {
            "success": True,
            "file": p.file_path,
            "header": {
                "frequency": p.header.frequency,
                "delta_t": p.header.delta_t,
                "t_max": p.header.t_max,
            },
            "models": [m.name for m in p.models],
            "uses": [f"{u.model_name} AS {u.instance_name}" for u in p.uses],
            "branches": len(p.branches),
            "switches": len(p.switches),
            "sources": len(p.sources),
            "nodes": len(p.nodes),
            "sections": list(p.sections.keys()),
        }

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    def list_models(self) -> dict[str, Any]:
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        return {
            "success": True,
            "models": [
                {
                    "name": m.name,
                    "inputs": len(m.inputs),
                    "outputs": len(m.outputs),
                    "data": len(m.data),
                    "variables": len(m.variables),
                }
                for m in self.project.models
            ],
        }

    def list_uses(self) -> dict[str, Any]:
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        return {
            "success": True,
            "uses": [
                {
                    "model_name": u.model_name,
                    "instance_name": u.instance_name,
                    "inputs": len(u.inputs),
                    "data": len(u.data),
                    "outputs": len(u.outputs),
                    "modified": u.modified,
                }
                for u in self.project.uses
            ],
        }

    def get_model_info(self, model_name: str) -> dict[str, Any]:
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        model = self.project.find_model(model_name)
        if model is None:
            return {"success": False, "error": f"MODEL '{model_name}' not found"}
        return {
            "success": True,
            "name": model.name,
            "inputs": model.inputs,
            "outputs": model.outputs,
            "data": [
                {"name": d.name, "default": d.default_value}
                for d in model.data
            ],
            "variables": model.variables,
            "lines": f"{model.start_line + 1}–{model.end_line + 1}",
        }

    def get_use_info(self, model_name: str) -> dict[str, Any]:
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        use = self.project.find_use(model_name)
        if use is None:
            return {"success": False, "error": f"USE '{model_name}' not found"}
        return {
            "success": True,
            "model_name": use.model_name,
            "instance_name": use.instance_name,
            "inputs": [
                {"local": i.local_name, "mapped_to": i.mapped_to}
                for i in use.inputs
            ],
            "data": [
                {"name": d.name, "value": d.assigned_value, "default": d.default_value}
                for d in use.data
            ],
            "outputs": [
                {"global": o.global_name, "local": o.local_name}
                for o in use.outputs
            ],
            "modified": use.modified,
        }

    def list_components(
        self, section: Optional[str] = None, semantic_type: Optional[str] = None
    ) -> dict[str, Any]:
        if self.project is None:
            return {"success": False, "error": "No project loaded"}

        result: dict[str, Any] = {"success": True}

        if section is None or section.upper() == "BRANCH":
            branches = self.project.branches
            if semantic_type:
                branches = [b for b in branches if b.semantic_type == semantic_type]
            result["branches"] = [
                {"node1": b.node1, "node2": b.node2, "type": b.semantic_type,
                 "R": b.resistance, "L": b.inductance, "C": b.capacitance}
                for b in branches
            ]

        if section is None or section.upper() == "SWITCH":
            switches = self.project.switches
            if semantic_type:
                switches = [s for s in switches if s.semantic_type == semantic_type]
            result["switches"] = [
                {"node1": s.node1, "node2": s.node2, "type": s.semantic_type,
                 "switch_type": s.switch_type, "tacs_output": s.tacs_output}
                for s in switches
            ]

        if section is None or section.upper() == "SOURCE":
            sources = self.project.sources
            if semantic_type:
                sources = [s for s in sources if s.semantic_type == semantic_type]
            result["sources"] = [
                {"node": s.node, "type": s.semantic_type,
                 "amplitude": s.amplitude, "frequency": s.frequency}
                for s in sources
            ]

        return result

    def list_nodes(self) -> dict[str, Any]:
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        return {
            "success": True,
            "count": len(self.project.nodes),
            "nodes": [
                {"name": n.name, "sources": n.sources}
                for n in self.project.nodes.values()
            ],
        }

    def get_header(self) -> dict[str, Any]:
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        h = self.project.header
        return {
            "success": True,
            "frequency": h.frequency,
            "delta_t": h.delta_t,
            "t_max": h.t_max,
        }

    # ------------------------------------------------------------------
    # Edit operations
    # ------------------------------------------------------------------

    def set_data_param(self, model_name: str, param_name: str, new_value: str) -> dict[str, Any]:
        """Change a DATA parameter in a USE instance."""
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        use = self.project.find_use(model_name)
        if use is None:
            return {"success": False, "error": f"USE '{model_name}' not found"}

        for d in use.data:
            if d.name.upper() == param_name.upper():
                old_value = d.assigned_value
                d.assigned_value = new_value
                use.modified = True
                return {
                    "success": True,
                    "model_name": model_name,
                    "param": param_name,
                    "old_value": old_value,
                    "new_value": new_value,
                }
        return {"success": False, "error": f"Parameter '{param_name}' not found in USE '{model_name}'"}

    def set_model_default(self, model_name: str, param_name: str, new_value: str) -> dict[str, Any]:
        """Change a default value in a MODEL DATA definition."""
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        model = self.project.find_model(model_name)
        if model is None:
            return {"success": False, "error": f"MODEL '{model_name}' not found"}

        for d in model.data:
            if d.name.upper() == param_name.upper():
                old_value = d.default_value
                d.default_value = new_value
                return {
                    "success": True,
                    "model_name": model_name,
                    "param": param_name,
                    "old_value": old_value,
                    "new_value": new_value,
                }
        return {"success": False, "error": f"Parameter '{param_name}' not found in MODEL '{model_name}'"}

    def set_input_mapping(self, model_name: str, local_name: str, mapped_to: str) -> dict[str, Any]:
        """Change an INPUT mapping in a USE instance."""
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        use = self.project.find_use(model_name)
        if use is None:
            return {"success": False, "error": f"USE '{model_name}' not found"}

        for inp in use.inputs:
            if inp.local_name.upper() == local_name.upper():
                old_mapped = inp.mapped_to
                inp.mapped_to = mapped_to
                use.modified = True
                return {
                    "success": True,
                    "model_name": model_name,
                    "local_name": local_name,
                    "old_mapped_to": old_mapped,
                    "new_mapped_to": mapped_to,
                }
        return {"success": False, "error": f"INPUT '{local_name}' not found in USE '{model_name}'"}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_all(self) -> dict[str, Any]:
        """Run all validations and return results."""
        if self.project is None:
            return {"success": False, "error": "No project loaded"}

        msgs = validate_project(self.project)
        msgs.extend(validate_physics(self.project))
        msgs.extend(validate_vcb(self.project))

        return {
            "success": True,
            "total": len(msgs),
            "errors": sum(1 for m in msgs if m.severity.value == "ERRO"),
            "warnings": sum(1 for m in msgs if m.severity.value == "AVISO"),
            "info": sum(1 for m in msgs if m.severity.value == "INFO"),
            "messages": [
                {"severity": m.severity.value, "code": m.code, "message": m.message}
                for m in msgs
            ],
        }

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def configure_atp(self, executable_path: str, timeout: int = 120) -> dict[str, Any]:
        """Configure the ATP executable path and timeout."""
        self.runner.executable_path = executable_path
        self.runner.timeout = timeout
        return {
            "success": True,
            "executable": executable_path,
            "timeout": timeout,
            "is_configured": self.runner.is_configured(),
        }

    def run_simulation(self) -> dict[str, Any]:
        """Run ATP simulation on the loaded project."""
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        if not self.runner.is_configured():
            return {"success": False, "error": "ATP executable not configured"}

        result = self.runner.run(self.project.file_path)
        self._last_run = result
        return {
            "success": result.success,
            "return_code": result.return_code,
            "message": result.message,
            "run_dir": result.run_dir,
            "log_file": result.log_file,
            "stdout_preview": result.stdout[:500] if result.stdout else "",
            "stderr_preview": result.stderr[:500] if result.stderr else "",
        }

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_csv(self, output_path: str, mode: str = "metrics") -> dict[str, Any]:
        """Export results to CSV. mode: 'metrics' or 'waveforms'."""
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        found = find_result_files(self.project.file_path)
        if "pl4" not in found:
            return {"success": False, "error": "No .pl4 results found"}
        try:
            pl4 = read_pl4(found["pl4"])
        except Exception as e:
            return {"success": False, "error": f"Failed to read .pl4: {e}"}

        try:
            if mode == "waveforms":
                path = export_waveforms_csv(pl4, output_path)
            else:
                path = export_metrics_csv(pl4, output_path)
            return {"success": True, "file": path, "mode": mode}
        except Exception as e:
            return {"success": False, "error": f"Export failed: {e}"}

    def export_report(self, output_path: str) -> dict[str, Any]:
        """Generate and save HTML report with logo, summary, validation and metrics."""
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        try:
            path = export_html_report(self.project, output_path)
            return {"success": True, "file": path}
        except Exception as e:
            return {"success": False, "error": f"Report failed: {e}"}

    def export_pdf(self, output_path: str) -> dict[str, Any]:
        """Generate and save PDF report via Qt printing."""
        if self.project is None:
            return {"success": False, "error": "No project loaded"}
        try:
            path = export_pdf_report(self.project, output_path)
            return {"success": True, "file": path}
        except Exception as e:
            return {"success": False, "error": f"PDF export failed: {e}"}
