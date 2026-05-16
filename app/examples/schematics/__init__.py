"""
app.examples.schematics — diretório dos arquivos .sch
correspondentes a cada exemplo executável.

Helper ``schematic_path_for(example_id)`` retorna o caminho
do .sch para um dado exemplo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


_SCHEMATIC_DIR = Path(__file__).resolve().parent


_MAP: dict[str, str] = {
    "stevenson_pf_3bus": "stevenson_pf_3bus.sch",
    "stevenson_sequential": "stevenson_sequential.sch",
    "iec60909_annex_c": "iec60909_annex_c.sch",
    "ieee1584_ex_d2": "ieee1584_ex_d2.sch",
    "ieee399_motor_starting": "ieee399_motor_starting.sch",
    "nbr17227_example": "nbr17227_example.sch",
}


def schematic_path_for(example_id: str) -> Optional[Path]:
    """
    Retorna o Path do .sch para o ``example_id`` ou None
    se não houver schematic associado.
    """
    name = _MAP.get(example_id)
    if name is None:
        return None
    p = _SCHEMATIC_DIR / name
    if not p.is_file():
        return None
    return p
