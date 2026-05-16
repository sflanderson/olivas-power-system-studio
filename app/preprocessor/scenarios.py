"""
app/preprocessor/scenarios.py — Scenario Manager.

v3.5.0 — paridade PTW Tutorial §Part 11 p.319-344 (Scenario Manager).

Permite branches paralelos no mesmo projeto (como "what-if scenarios"):

* **PpScenario** — snapshot de PpProject + metadata (name, base_id, color)
* **ScenarioManager** — gerencia coleção; clone / activate / promote / diff
* **PromotionMode** — UNMODIFIED_ONLY / ALL_FIELDS / DO_NOT_PROMOTE
  (PTW Tutorial §Part 11 p.342)

Distingue-se de CRDT (v3.0.0) — paradigmas complementares:
- **CRDT**: edição **sincronizada** entre múltiplos usuários no mesmo modelo
- **Scenario Manager**: branches **paralelos** dentro do mesmo arquivo
  com promote-to-base

Reference: PTW Tutorial §Part 11 p.319-347.
"""

from __future__ import annotations

import copy
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PromotionMode(str, Enum):
    """Modo de promoção scenario → base (PTW Tutorial §Part 11 p.342).

    * **UNMODIFIED_ONLY** — promove apenas campos onde base ainda tem
      valor original (não modificado em outro scenario)
    * **ALL_FIELDS** — promove todos os campos do scenario para base
      (overwrites)
    * **DO_NOT_PROMOTE** — bloqueia promotion (cenário read-only)
    """

    UNMODIFIED_ONLY = "unmodified_only"
    ALL_FIELDS = "all_fields"
    DO_NOT_PROMOTE = "do_not_promote"


# Cor padrão PTW para destaque de cenário ativo.
PTW_PEACH_COLOR: str = "#ffe5b4"


@dataclass
class PpScenario:
    """Um scenario (snapshot) do projeto.

    Reference: PTW Tutorial §Part 11 p.319-347.

    Attributes
    ----------
    id
        UUID único.
    name
        Nome user-friendly (ex: "Scenario A — sem PV").
    base_id
        UUID do scenario pai (None se for o BASE original).
    project_snapshot
        Deep-copy de PpProject (ou serialização equivalente).
    color
        Cor para diff highlight (default PTW peach).
    promotion_mode
        Default ALL_FIELDS.
    created_at
        Unix timestamp.
    notes
        Free-form.
    """

    id: str
    name: str
    project_snapshot: object  # PpProject (deep copy)
    base_id: Optional[str] = None
    color: str = PTW_PEACH_COLOR
    promotion_mode: PromotionMode = PromotionMode.ALL_FIELDS
    created_at: float = field(default_factory=time.time)
    notes: str = ""

    @classmethod
    def create_base(cls, project, name: str = "Base") -> "PpScenario":
        """Create the BASE scenario from a PpProject.

        Reference: PTW Tutorial §Part 11 p.320 (BASE is always the root).
        """
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            base_id=None,  # base has no parent
            project_snapshot=copy.deepcopy(project),
        )

    def clone(self, new_name: str) -> "PpScenario":
        """Clone this scenario as a new branch.

        Reference: PTW Tutorial §Part 11 p.320 (Clone Base/Clone clone).
        """
        return PpScenario(
            id=str(uuid.uuid4()),
            name=new_name,
            base_id=self.id,
            project_snapshot=copy.deepcopy(self.project_snapshot),
        )

    def is_base(self) -> bool:
        """True if this is the root BASE scenario."""
        return self.base_id is None


@dataclass
class ScenarioManager:
    """Container e operações de cenários.

    Reference: PTW Tutorial §Part 11 p.319-347.
    """

    scenarios: list[PpScenario] = field(default_factory=list)
    active_id: Optional[str] = None

    def add(self, scenario: PpScenario) -> None:
        """Add a scenario to the manager."""
        self.scenarios.append(scenario)
        if self.active_id is None:
            self.active_id = scenario.id

    def find(self, scenario_id: str) -> Optional[PpScenario]:
        """Find scenario by id; None if missing."""
        for s in self.scenarios:
            if s.id == scenario_id:
                return s
        return None

    def get_base(self) -> Optional[PpScenario]:
        """Return the BASE scenario (base_id is None) or None if absent."""
        for s in self.scenarios:
            if s.is_base():
                return s
        return None

    def get_active(self) -> Optional[PpScenario]:
        """Return the currently active scenario."""
        if self.active_id is None:
            return None
        return self.find(self.active_id)

    def activate(self, scenario_id: str) -> bool:
        """Set scenario_id as active. True on success, False if not found."""
        if self.find(scenario_id) is None:
            return False
        self.active_id = scenario_id
        return True

    def clone_active(self, new_name: str) -> Optional[PpScenario]:
        """Clone the active scenario as a new branch.

        Reference: PTW Tutorial §Part 11 p.320 (Clone Base / Clone clone).
        """
        active = self.get_active()
        if active is None:
            return None
        new_scenario = active.clone(new_name)
        self.add(new_scenario)
        return new_scenario

    def promote_to_base(self, scenario_id: str) -> bool:
        """Promote a scenario's changes to the BASE per its promotion_mode.

        Per PTW Tutorial §Part 11 p.342:
        * UNMODIFIED_ONLY — only fields where base still has original
        * ALL_FIELDS — overwrite base with scenario
        * DO_NOT_PROMOTE — blocked

        Returns True on success, False otherwise (mode blocked, scenario
        not found, or no base).
        """
        scenario = self.find(scenario_id)
        if scenario is None:
            return False
        if scenario.is_base():
            return False  # base cannot be promoted to itself
        if scenario.promotion_mode == PromotionMode.DO_NOT_PROMOTE:
            return False
        base = self.get_base()
        if base is None:
            return False

        if scenario.promotion_mode == PromotionMode.ALL_FIELDS:
            # Overwrite base with scenario
            base.project_snapshot = copy.deepcopy(scenario.project_snapshot)
            return True

        if scenario.promotion_mode == PromotionMode.UNMODIFIED_ONLY:
            # Heuristic: copy fields only if base appears unchanged.
            # Implementation deferred to a smarter diff in v3.5.x.
            # For now: copy components that are NEW in scenario (not in base).
            base_proj = base.project_snapshot
            sc_proj = scenario.project_snapshot
            base_names = {
                getattr(c, "name", None) for c in getattr(base_proj, "components", [])
            }
            for comp in getattr(sc_proj, "components", []):
                name = getattr(comp, "name", None)
                if name not in base_names:
                    base_proj.components.append(copy.deepcopy(comp))
            return True

        return False

    def diff_with_base(self, scenario_id: str) -> dict:
        """Compute simple diff (added/removed/modified) vs base.

        Returns a dict with keys: ``added``, ``removed``, ``modified``,
        each a list of component names.

        Reference: PTW Tutorial §Part 11 p.336-337 (diff color highlight).
        """
        scenario = self.find(scenario_id)
        if scenario is None or scenario.is_base():
            return {"added": [], "removed": [], "modified": []}
        base = self.get_base()
        if base is None:
            return {"added": [], "removed": [], "modified": []}

        base_components = {
            getattr(c, "name", None): c
            for c in getattr(base.project_snapshot, "components", [])
            if getattr(c, "name", None) is not None
        }
        sc_components = {
            getattr(c, "name", None): c
            for c in getattr(scenario.project_snapshot, "components", [])
            if getattr(c, "name", None) is not None
        }

        added = [n for n in sc_components if n not in base_components]
        removed = [n for n in base_components if n not in sc_components]
        modified: list[str] = []
        for name in sc_components:
            if name in base_components:
                # Compare type + property values (shallow)
                if (
                    sc_components[name].type != base_components[name].type
                    or len(sc_components[name].properties)
                       != len(base_components[name].properties)
                ):
                    modified.append(name)
                    continue
                # Compare property values
                for sc_p, base_p in zip(
                    sc_components[name].properties,
                    base_components[name].properties,
                ):
                    if sc_p.value != base_p.value:
                        modified.append(name)
                        break

        return {"added": added, "removed": removed, "modified": modified}


__all__ = [
    "PromotionMode",
    "PTW_PEACH_COLOR",
    "PpScenario",
    "ScenarioManager",
]
