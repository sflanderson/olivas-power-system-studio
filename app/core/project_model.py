from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DataParam:
    name: str
    default_value: Optional[str] = None
    assigned_value: Optional[str] = None
    raw_line: str = ""


@dataclass
class InputMapping:
    local_name: str
    mapped_to: str
    raw_line: str = ""


@dataclass
class OutputMapping:
    global_name: str
    local_name: str
    raw_line: str = ""


@dataclass
class ModelDefinition:
    name: str
    comment: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    data: list[DataParam] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    init_code: str = ""
    exec_code: str = ""
    raw_text: str = ""
    start_line: int = 0
    end_line: int = 0


@dataclass
class UseInstance:
    model_name: str
    instance_name: str = "DEFAULT"
    inputs: list[InputMapping] = field(default_factory=list)
    outputs: list[OutputMapping] = field(default_factory=list)
    data: list[DataParam] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    modified: bool = False


@dataclass
class ModelsGlobalIO:
    inputs: list[InputMapping] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)


@dataclass
class BranchComponent:
    node1: str
    node2: str
    type_code: str = ""
    ref1: str = ""
    ref2: str = ""
    resistance: Optional[str] = None
    inductance: Optional[str] = None
    capacitance: Optional[str] = None
    raw_line: str = ""
    line_number: int = 0
    semantic_type: str = ""  # e.g. "resistor", "inductor", "capacitor", "RLC", "snubber", "transformer", "line"
    # Editing flags (used by schematic editor and serializer)
    modified: bool = False
    deleted: bool = False
    is_new: bool = False


@dataclass
class SwitchComponent:
    node1: str
    node2: str
    type_code: str = ""
    t_close: Optional[str] = None
    t_open: Optional[str] = None
    ie: Optional[str] = None
    switch_type: str = ""
    tacs_output: str = ""
    raw_line: str = ""
    line_number: int = 0
    semantic_type: str = ""  # e.g. "vcb", "time_controlled", "tacs_controlled", "measuring", "systematic"
    # Editing flags (used by schematic editor and serializer)
    modified: bool = False
    deleted: bool = False
    is_new: bool = False


@dataclass
class SourceComponent:
    node: str
    type_code: str = ""
    amplitude: Optional[str] = None
    frequency: Optional[str] = None
    phase: Optional[str] = None
    t_start: Optional[str] = None
    t_stop: Optional[str] = None
    raw_line: str = ""
    line_number: int = 0
    semantic_type: str = ""  # e.g. "ac", "dc", "step", "ramp"
    # Editing flags (used by schematic editor and serializer)
    modified: bool = False
    deleted: bool = False
    is_new: bool = False


@dataclass
class Node:
    name: str
    sources: list[str] = field(default_factory=list)


@dataclass
class Section:
    name: str
    raw_lines: list[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0


@dataclass
class HeaderInfo:
    frequency: Optional[float] = None
    delta_t: Optional[float] = None
    t_max: Optional[float] = None
    raw_lines: list[str] = field(default_factory=list)


@dataclass
class AtpProject:
    file_path: str = ""
    header: HeaderInfo = field(default_factory=HeaderInfo)
    models_global_io: ModelsGlobalIO = field(default_factory=ModelsGlobalIO)
    models: list[ModelDefinition] = field(default_factory=list)
    uses: list[UseInstance] = field(default_factory=list)
    sections: dict[str, Section] = field(default_factory=dict)
    branches: list[BranchComponent] = field(default_factory=list)
    switches: list[SwitchComponent] = field(default_factory=list)
    sources: list[SourceComponent] = field(default_factory=list)
    nodes: dict[str, Node] = field(default_factory=dict)
    raw_lines: list[str] = field(default_factory=list)
    tail_lines: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def find_model(self, name: str) -> Optional[ModelDefinition]:
        for m in self.models:
            if m.name.upper() == name.upper():
                return m
        return None

    def find_use(self, model_name: str) -> Optional[UseInstance]:
        for u in self.uses:
            if u.model_name.upper() == model_name.upper():
                return u
        return None
