"""
app.examples.registry — registro central dos exemplos
executáveis disponíveis na GUI.

A GUI consome ``EXAMPLES`` para popular o menu Exemplos.
Cada entry tem id, label localizado, função run, e ícone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.examples import ExampleResult


@dataclass(frozen=True)
class ExampleEntry:
    """Entry no menu Exemplos."""
    id: str
    label: str
    description: str
    reference: str
    runner: Callable[[], ExampleResult]


def _example_runner(module_name: str) -> Callable[[], ExampleResult]:
    """Lazy-import wrapper para evitar carregamento upfront."""
    def _run() -> ExampleResult:
        import importlib
        module = importlib.import_module(
            f"app.examples.{module_name}",
        )
        return module.run()
    return _run


# Registro central
EXAMPLES: tuple[ExampleEntry, ...] = (
    ExampleEntry(
        id="stevenson_pf_3bus",
        label="Stevenson — Power Flow 3-bus",
        description=(
            "Newton-Raphson PF com SLACK + PV + PQ. "
            "Convergência em 4 iterações."
        ),
        reference="Stevenson §9 Ex 9.5",
        runner=_example_runner("stevenson_pf_3bus"),
    ),
    ExampleEntry(
        id="stevenson_sequential",
        label="Stevenson — Faltas Assimétricas (0/1/2)",
        description=(
            "Faltas LG/LL/LLG via componentes simétricas. "
            "Característica TN: Ik1 > Ik3."
        ),
        reference="Stevenson §11",
        runner=_example_runner("stevenson_sequential"),
    ),
    ExampleEntry(
        id="iec60909_annex_c",
        label="IEC 60909-0 Annex C — SC com TR",
        description=(
            "Concessionária 1500 MVA + TR 110/20 kV 25 MVA. "
            "Ik''3 no secundário."
        ),
        reference="IEC 60909-0:2016 Annex C",
        runner=_example_runner("iec60909_annex_c"),
    ),
    ExampleEntry(
        id="ieee1584_ex_d2",
        label="IEEE 1584 — Arc-flash 480V VCB",
        description=(
            "480V/20kA/200ms VCB. Cat 3 (~8.8 cal/cm²)."
        ),
        reference="IEEE Std 1584-2018 Annex D",
        runner=_example_runner("ieee1584_ex_d2"),
    ),
    ExampleEntry(
        id="ieee399_motor_starting",
        label="IEEE 399 — Partida Motor 1500 kW",
        description=(
            "Voltage dip + tempo de aceleração. "
            "Aceitação IEEE 399 §10."
        ),
        reference="IEEE Std 399-1997 (Brown Book) §10",
        runner=_example_runner("ieee399_motor_starting"),
    ),
    ExampleEntry(
        id="nbr17227_example",
        label="NBR 17227 — Arc-flash 13.8 kV switchgear",
        description=(
            "Industrial brasileiro. 13.8kV/18kA → Cat 3."
        ),
        reference="ABNT NBR 17227:2025",
        runner=_example_runner("nbr17227_example"),
    ),
)


def get_example_by_id(example_id: str) -> ExampleEntry | None:
    """Retorna entry pelo id."""
    for ex in EXAMPLES:
        if ex.id == example_id:
            return ex
    return None
