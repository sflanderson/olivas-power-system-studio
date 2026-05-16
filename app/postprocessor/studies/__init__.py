"""
app.postprocessor.studies — estudos elétricos modulares
(v0.94.0).

Cada estudo é um módulo independente, com **pré-requisitos
declarados** e **cache automático** via
:class:`app.postprocessor.study_cache.StudyCache`.

Hierarquia (PTW Power*Tools):

* :mod:`short_circuit` — standalone (sem prereqs)
* :mod:`coordination` — REQUIRES SC
* :mod:`arc_flash_study` — REQUIRES SC + COORD

Cada módulo expõe ``run(project, bus_id, *, cache=None,
config=None, auto_run_prereqs=True)`` que:

1. Verifica cache — retorna se hit válido.
2. Verifica prereqs — auto-roda se ``auto_run_prereqs=True``,
   senão raises :class:`PrerequisiteError`.
3. Computa o estudo.
4. Grava em cache.
5. Retorna o resultado tipado.

Convention: prefer importar via ``app.postprocessor.studies``
não via cada submódulo:

::

    from app.postprocessor.studies import short_circuit, coordination
    sc = short_circuit.run(project, "BUS-MAIN")
    coord = coordination.run(project, "BUS-MAIN")  # auto-roda SC
"""

from __future__ import annotations

from app.postprocessor.study_cache import (
    PrerequisiteError, StudyCache, hash_study_inputs,
)
from app.postprocessor.studies import (
    arc_flash_study,
    coordination,
    short_circuit,
)
from app.postprocessor.studies.arc_flash_study import (
    ArcFlashStudyResult,
)
from app.postprocessor.studies.coordination import (
    CoordinationStudyResult,
)
from app.postprocessor.studies.short_circuit import (
    ShortCircuitStudyResult,
)

__all__ = [
    # Modules
    "short_circuit",
    "coordination",
    "arc_flash_study",
    # Result types
    "ShortCircuitStudyResult",
    "CoordinationStudyResult",
    "ArcFlashStudyResult",
    # Cache + errors
    "PrerequisiteError",
    "StudyCache",
    "hash_study_inputs",
]
