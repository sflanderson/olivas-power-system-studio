"""LLM Agent intent definitions for Olivas ATP Studio.

LLM-001: Structured intents that the agent can recognize and execute.

Each intent maps a user's natural language request to a structured
action that the ProjectAPI can execute.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IntentCategory(Enum):
    """High-level categories of agent intents."""
    FILE = "file"               # Open, save, info about files
    QUERY = "query"             # Read-only queries about the project
    EDIT = "edit"               # Modify parameters, mappings
    VALIDATE = "validate"       # Run validations
    SIMULATE = "simulate"       # Run ATP, analyze results
    ANALYZE = "analyze"         # Transient metrics, TRV
    PARAMETRIC = "parametric"   # Parametric studies


@dataclass
class Intent:
    """A structured intent that the LLM agent can dispatch."""
    name: str
    category: IntentCategory
    description: str
    required_params: list[str] = field(default_factory=list)
    optional_params: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


# ======================================================================
# Intent catalog
# ======================================================================

INTENTS: list[Intent] = [
    # --- FILE ---
    Intent(
        name="open_file",
        category=IntentCategory.FILE,
        description="Open and parse an ATP file",
        required_params=["file_path"],
        examples=[
            "Abra o arquivo trt_all_motors_dt_ea.atp",
            "Carregue o caso de teste",
        ],
    ),
    Intent(
        name="save_file",
        category=IntentCategory.FILE,
        description="Save the current project to a file",
        required_params=["file_path"],
        examples=[
            "Salve como caso_modificado.atp",
            "Grave as alterações",
        ],
    ),
    Intent(
        name="project_summary",
        category=IntentCategory.FILE,
        description="Get a summary of the loaded project",
        examples=[
            "Resuma o projeto",
            "Quantos componentes tem?",
        ],
    ),

    # --- QUERY ---
    Intent(
        name="list_models",
        category=IntentCategory.QUERY,
        description="List all MODEL definitions",
        examples=["Liste os modelos", "Quais MODELs existem?"],
    ),
    Intent(
        name="list_uses",
        category=IntentCategory.QUERY,
        description="List all USE instances",
        examples=["Liste os USEs", "Quais instâncias existem?"],
    ),
    Intent(
        name="get_model_info",
        category=IntentCategory.QUERY,
        description="Get details of a specific MODEL",
        required_params=["model_name"],
        examples=["Mostre o modelo VCB_RR", "Detalhes do MODEL VCB_RR"],
    ),
    Intent(
        name="get_use_info",
        category=IntentCategory.QUERY,
        description="Get details of a specific USE instance",
        required_params=["model_name"],
        examples=["Mostre o USE do VCB_RR", "Parâmetros do USE VCB_RR"],
    ),
    Intent(
        name="list_components",
        category=IntentCategory.QUERY,
        description="List components by section or type",
        optional_params=["section", "semantic_type"],
        examples=[
            "Liste os branches",
            "Quais switches são VCB?",
            "Mostre os snubbers",
        ],
    ),
    Intent(
        name="list_nodes",
        category=IntentCategory.QUERY,
        description="List all circuit nodes",
        examples=["Liste os nós", "Quantos nós tem?"],
    ),
    Intent(
        name="get_header",
        category=IntentCategory.QUERY,
        description="Get simulation header (dt, tmax, frequency)",
        examples=["Qual o delta-t?", "Mostre o header"],
    ),

    # --- EDIT ---
    Intent(
        name="set_data_param",
        category=IntentCategory.EDIT,
        description="Change a DATA parameter value in a USE instance",
        required_params=["model_name", "param_name", "new_value"],
        examples=[
            "Mude T_OPEN para 0.05 no VCB_RR",
            "Altere I_CHOP para 5.0",
        ],
    ),
    Intent(
        name="set_model_default",
        category=IntentCategory.EDIT,
        description="Change a default value in a MODEL DATA definition",
        required_params=["model_name", "param_name", "new_value"],
        examples=["Mude o default de RRDS_A para 1e6 no MODEL VCB_RR"],
    ),
    Intent(
        name="set_input_mapping",
        category=IntentCategory.EDIT,
        description="Change an INPUT mapping in a USE instance",
        required_params=["model_name", "local_name", "mapped_to"],
        examples=["Mapeie V_POS para v(BUSA) no USE VCB_RR"],
    ),

    # --- VALIDATE ---
    Intent(
        name="validate_all",
        category=IntentCategory.VALIDATE,
        description="Run all validations (structural, physics, VCB)",
        examples=["Valide o projeto", "Tem erros?"],
    ),
    Intent(
        name="validate_physics",
        category=IntentCategory.VALIDATE,
        description="Run only physical validations",
        examples=["Verifique a física dos componentes"],
    ),

    # --- SIMULATE ---
    Intent(
        name="run_simulation",
        category=IntentCategory.SIMULATE,
        description="Execute the ATP simulation",
        examples=["Rode a simulação", "Execute o ATP"],
    ),
    Intent(
        name="show_results",
        category=IntentCategory.SIMULATE,
        description="Show simulation results summary",
        examples=["Mostre os resultados", "O que deu a simulação?"],
    ),

    # --- ANALYZE ---
    Intent(
        name="transient_metrics",
        category=IntentCategory.ANALYZE,
        description="Compute transient metrics for a variable",
        required_params=["variable_name"],
        examples=[
            "Calcule as métricas de V_BUS",
            "Qual o pico de tensão?",
        ],
    ),
    Intent(
        name="trv_analysis",
        category=IntentCategory.ANALYZE,
        description="Compute TRV/RRRV for a VCB opening",
        optional_params=["rated_voltage_kv", "current_zero_time"],
        examples=[
            "Analise o TRV",
            "Qual o RRRV?",
            "A TRV excede a norma IEC?",
        ],
    ),

    # --- PARAMETRIC ---
    Intent(
        name="parametric_sweep",
        category=IntentCategory.PARAMETRIC,
        description="Run parametric sweep varying one or more parameters",
        required_params=["model_name", "param_name", "values"],
        optional_params=["metric"],
        examples=[
            "Varie T_OPEN de 0.01 a 0.1 em 10 passos",
            "Estudo paramétrico de I_CHOP",
        ],
    ),
]


def find_intent(name: str) -> Optional[Intent]:
    """Find an intent by name."""
    for intent in INTENTS:
        if intent.name == name:
            return intent
    return None


def get_intent_names() -> list[str]:
    """Return all available intent names."""
    return [i.name for i in INTENTS]


def get_intents_by_category(category: IntentCategory) -> list[Intent]:
    """Return intents filtered by category."""
    return [i for i in INTENTS if i.category == category]
