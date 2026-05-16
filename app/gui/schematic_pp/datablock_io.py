"""
app.gui.schematic_pp.datablock_io — persistência de
:class:`PpDataBlock` em sidecar JSON (v0.86).

Por que sidecar e não inline no `.sch`?
* O formato Qucs `.sch` é estabilizado pela upstream e não tem
  pseudo-section para "annotations elétricas". Adicionar
  comentários quebraria a fidelidade de round-trip que mantemos.
* Datablocks são metadata da nossa ferramenta, não do circuito.
  Manter separado preserva interoperabilidade com Qucs original.

Convenção:
* Schema: ``<schematic.sch>.datablocks.json``
* Formato JSON simples (lista de objetos), com schema_version=1
  para futura migração se precisarmos.

Robustez:
* Se o sidecar não existe → retorna lista vazia (silencioso).
* Se está corrompido → retorna lista vazia + log de warning
  no console (UX prefere abrir o esquemático sem datablocks
  do que bloquear o usuário).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.preprocessor.models import PpDataBlock


SIDECAR_SUFFIX = ".datablocks.json"
SCHEMA_VERSION = 1


def sidecar_path(sch_path: str) -> Path:
    """Path do sidecar correspondente a um .sch."""
    return Path(sch_path).with_suffix(
        Path(sch_path).suffix + ".datablocks.json"
    )


def save_datablocks_sidecar(
    sch_path: str,
    datablocks: Iterable[PpDataBlock],
) -> None:
    """
    Grava ``datablocks`` no sidecar JSON ``<sch_path>.datablocks.json``.

    Se a lista for vazia, REMOVE o sidecar existente (manter um
    arquivo vazio é confuso). Falhas silenciosas: I/O exceptions
    não derrubam o save do .sch principal.
    """
    target = sidecar_path(sch_path)
    db_list = list(datablocks)
    if not db_list:
        # Limpa sidecar antigo se existir.
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        return
    payload = {
        "schema_version": SCHEMA_VERSION,
        "datablocks": [
            {
                "component_name": db.component_name,
                "dx": int(db.dx),
                "dy": int(db.dy),
                "lines": list(db.lines),
                # v0.88: template_lines preservado para sticky
                # placeholders. Empty = legacy (lines IS template).
                "template_lines": list(db.template_lines),
                "visible": bool(db.visible),
            }
            for db in db_list
        ],
    }
    try:
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def load_datablocks_sidecar(sch_path: str) -> list[PpDataBlock]:
    """
    Lê ``<sch_path>.datablocks.json`` e retorna a lista de
    :class:`PpDataBlock`. Retorna ``[]`` se ausente ou corrompido.
    """
    target = sidecar_path(sch_path)
    if not target.is_file():
        return []
    try:
        text = target.read_text(encoding="utf-8")
        payload = json.loads(text)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    raw_list = payload.get("datablocks", [])
    if not isinstance(raw_list, list):
        return []
    result: list[PpDataBlock] = []
    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        try:
            # v0.88: aceita template_lines opcional.
            # Datablocks pré-v0.88 não têm o campo → []
            # (vai ser preenchido na primeira refresh via
            # migração em refresh_datablocks_from_cache).
            template_raw = raw.get("template_lines", [])
            template_lines = (
                [str(s) for s in template_raw]
                if isinstance(template_raw, list)
                else []
            )
            result.append(
                PpDataBlock(
                    component_name=str(raw.get("component_name", "")),
                    dx=int(raw.get("dx", 50)),
                    dy=int(raw.get("dy", -10)),
                    lines=[str(s) for s in raw.get("lines", [])],
                    template_lines=template_lines,
                    visible=bool(raw.get("visible", True)),
                )
            )
        except (TypeError, ValueError):
            continue
    return result
