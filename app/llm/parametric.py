"""Parametric study automation for Olivas ATP Studio.

LLM-011: Sweep one or more DATA parameters, run simulations,
and collect results/metrics for each combination.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.core.parser import parse_file
from app.core.project_model import AtpProject
from app.core.serializer import serialize_project
from app.simulation.runner import AtpRunner
from app.validation.validator_models import validate_project


@dataclass
class SweepParameter:
    """A parameter to sweep in a parametric study."""
    model_name: str
    param_name: str
    values: list[str]


@dataclass
class SweepCase:
    """One case in a parametric sweep."""
    index: int
    params: dict[str, str]  # "model.param" -> value
    atp_file: str = ""
    success: bool = False
    message: str = ""
    log_file: str = ""


@dataclass
class SweepResult:
    """Result of a full parametric study."""
    total_cases: int = 0
    completed: int = 0
    failed: int = 0
    cases: list[SweepCase] = field(default_factory=list)
    output_dir: str = ""


def generate_sweep_cases(
    base_project: AtpProject,
    parameters: list[SweepParameter],
) -> list[dict[str, str]]:
    """Generate all combinations of parameter values.

    For a single parameter, returns one dict per value.
    For multiple parameters, returns the Cartesian product.
    """
    if not parameters:
        return [{}]

    # Build list of (key, values) tuples
    param_specs = []
    for p in parameters:
        key = f"{p.model_name}.{p.param_name}"
        param_specs.append((key, p.model_name, p.param_name, p.values))

    # Cartesian product
    combinations: list[dict[str, str]] = [{}]
    for key, model_name, param_name, values in param_specs:
        new_combos = []
        for combo in combinations:
            for val in values:
                new_combo = dict(combo)
                new_combo[key] = val
                new_combos.append(new_combo)
        combinations = new_combos

    return combinations


def run_parametric_sweep(
    base_file: str,
    parameters: list[SweepParameter],
    runner: AtpRunner,
    output_dir: Optional[str] = None,
) -> SweepResult:
    """Execute a parametric sweep.

    1. Parse the base file
    2. For each parameter combination:
       a. Clone the project
       b. Set parameters
       c. Serialize to a new file
       d. Run ATP
       e. Collect results
    """
    base_project = parse_file(base_file)
    base_path = Path(base_file)

    if output_dir is None:
        output_dir = str(base_path.parent / "parametric" / base_path.stem)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    combinations = generate_sweep_cases(base_project, parameters)

    result = SweepResult(
        total_cases=len(combinations),
        output_dir=str(out_path),
    )

    for idx, combo in enumerate(combinations):
        case = SweepCase(index=idx, params=combo)

        # Clone project
        project = parse_file(base_file)

        # Apply parameter changes
        for key, value in combo.items():
            model_name, param_name = key.split(".", 1)
            use = project.find_use(model_name)
            if use is None:
                case.message = f"USE '{model_name}' not found"
                result.cases.append(case)
                result.failed += 1
                continue

            param_found = False
            for d in use.data:
                if d.name.upper() == param_name.upper():
                    d.assigned_value = value
                    use.modified = True
                    param_found = True
                    break

            if not param_found:
                case.message = f"Parameter '{param_name}' not found in USE '{model_name}'"
                result.cases.append(case)
                result.failed += 1
                continue

        # Serialize to file
        suffix = "_".join(f"{v}" for v in combo.values())
        case_name = f"case_{idx:03d}_{suffix}"
        case_file = out_path / f"{case_name}.atp"
        content = serialize_project(project)
        case_file.write_text(content, encoding="utf-8")
        case.atp_file = str(case_file)

        # Run simulation if runner is configured
        if runner.is_configured():
            run_result = runner.run(str(case_file))
            case.success = run_result.success
            case.message = run_result.message
            case.log_file = run_result.log_file
            if run_result.success:
                result.completed += 1
            else:
                result.failed += 1
        else:
            case.message = "ATP runner not configured — file generated only"
            result.completed += 1  # file was generated successfully

        result.cases.append(case)

    return result


def format_sweep_report(result: SweepResult) -> str:
    """Format parametric sweep results as readable text."""
    parts = [
        "Estudo Paramétrico — Relatório",
        f"{'═' * 50}",
        f"Total de casos:  {result.total_cases}",
        f"Concluídos:      {result.completed}",
        f"Falhas:          {result.failed}",
        f"Diretório:       {result.output_dir}",
        f"{'═' * 50}",
        "",
    ]

    for case in result.cases:
        status = "OK" if case.success else "FALHA"
        param_str = ", ".join(f"{k}={v}" for k, v in case.params.items())
        parts.append(f"[{status}] Caso {case.index:03d}: {param_str}")
        if case.message and not case.success:
            parts.append(f"        {case.message}")

    return "\n".join(parts)


def linspace_values(start: float, end: float, n: int) -> list[str]:
    """Generate n linearly spaced values as strings."""
    if n <= 1:
        return [str(start)]
    step = (end - start) / (n - 1)
    return [str(start + i * step) for i in range(n)]
