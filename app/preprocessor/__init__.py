"""
app.preprocessor — pré-processador gráfico do Olivas ATP Studio.

Este pacote contém:

* `models`               — dataclasses do esquemático no estilo Qucs
                          (componentes, fios, propriedades, paintings).
* `qucs_sch_parser`      — leitor do formato textual `.sch` do Qucs.
                          O *formato* é um dado público — ler/escrever
                          o `.sch` NÃO vincula a licença GPL do Qucs.
* `qucs_sch_serializer`  — escritor do mesmo formato (round-trip).
* `catalog`              — catálogo dos tipos de componentes que o
                          pré-processador reconhece (foco em potência
                          e eletrônica de potência).

Estratégia:
  Re-implementamos o *editor visual* em PySide6 dentro do Olivas,
  inspirado na UX do Qucs/ATPDraw, mas com símbolos próprios
  (padrão IEEE 315 / IEC 60617). Não distribuímos binários do Qucs
  nem linkamos contra `libqucs-0.dll` ou `include/qucs-core/`.
  Apenas o *formato de arquivo* é compartilhado.

Sprint v0.21.0:
  Apenas modelos + parser + serializer + testes de round-trip.
  Catálogo é um stub a ser expandido na v0.21.1.
"""

from .models import (
    PpProperty,
    PpComponent,
    PpWire,
    PpDiagram,
    PpPainting,
    PpProject,
)

from .qucs_sch_parser import parse_sch, parse_sch_file
from .qucs_sch_serializer import serialize_sch, serialize_sch_file

from .units import parse_value, format_atp_str, format_atp_value, is_numeric
from .node_coalescer import NodeMap, coalesce_nodes, pin_positions
from .bridge_to_atp import to_atp
from .bridge_from_atp import from_atp

__all__ = [
    # Modelos
    "PpProperty",
    "PpComponent",
    "PpWire",
    "PpDiagram",
    "PpPainting",
    "PpProject",
    # Parser/Serializer
    "parse_sch",
    "parse_sch_file",
    "serialize_sch",
    "serialize_sch_file",
    # Units
    "parse_value",
    "format_atp_str",
    "format_atp_value",
    "is_numeric",
    # Node coalescer
    "NodeMap",
    "coalesce_nodes",
    "pin_positions",
    # Bridge
    "to_atp",
    "from_atp",
]
