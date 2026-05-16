"""
app/gui/schematic_pp/sidecar_io.py — Sidecar JSON I/O for Olivas extensions.

v3.1.2 Sub-sprint D — fecha deferred de v3.1.1 Sprints 3+4.

Persistência de campos Olivas-only que NÃO cabem no formato Qucs `.sch`
canônico, mantendo backward-compatibility:

* :func:`save_sidecar` — escreve `<project>.olivas.json` com:
  - linked_library por property (PpProperty.linked_library)
  - link_tags (list[PpLinkTag])
  - legend_tags (list[PpLegendTag])

* :func:`load_sidecar` — lê o sidecar e popula PpProject + properties

Formato do sidecar é versionado (``"olivas_version": 1``) para evolução
futura sem quebrar parsers antigos.

Backward-compat:
* Se sidecar não existe → projeto carrega normalmente (sem extensões)
* Se .sch antigo é salvo no Olivas → sidecar é gerado se houver extensões
* Se .sch é editado em Qucs externo (sem sidecar) → linked + tags são preservadas no sidecar do Olivas

Reference: técnica padrão de "extension files" — usada por GIMP (.xcf
metadata), Inkscape (Inkscape namespace em SVG), etc.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.preprocessor.models import (
    PpComponent, PpLegendTag, PpLinkTag, PpProject, PpProperty,
)


SIDECAR_VERSION = 1
SIDECAR_EXTENSION = ".olivas.json"


def sidecar_path_for(sch_path: str | Path) -> Path:
    """Compute the sidecar path for a given .sch file.

    Examples
    --------
    ``project.sch`` → ``project.olivas.json``
    ``a/b/c.sch`` → ``a/b/c.olivas.json``
    """
    p = Path(sch_path)
    return p.with_suffix(SIDECAR_EXTENSION)


def project_to_sidecar_dict(project: PpProject) -> dict[str, Any]:
    """Build the sidecar dict from a project.

    Returns
    -------
    dict
        JSON-serializable dict with version, link_tags, legend_tags,
        and per-component linked properties.
    """
    sidecar: dict[str, Any] = {
        "olivas_version": SIDECAR_VERSION,
        "link_tags": [
            {
                "label": t.label,
                "target": t.target,
                "x": t.x,
                "y": t.y,
                "visible": t.visible,
                "closed_arrow": t.closed_arrow,
            }
            for t in project.link_tags
        ],
        "legend_tags": [
            {
                "text": t.text,
                "shape": t.shape,
                "x": t.x,
                "y": t.y,
                "color": t.color,
                "visible": t.visible,
            }
            for t in project.legend_tags
        ],
        # linked properties: keyed by component name (not type), nested by property index
        "linked_properties": {},
    }
    for comp in project.components:
        comp_links: dict[str, str] = {}
        for idx, prop in enumerate(comp.properties):
            if prop.linked_library is not None:
                comp_links[str(idx)] = prop.linked_library
        if comp_links:
            sidecar["linked_properties"][comp.name] = comp_links
    return sidecar


def populate_project_from_sidecar(
    project: PpProject,
    sidecar: dict[str, Any],
) -> None:
    """Apply sidecar data to a project (mutates project in-place).

    Tolerates missing / extra fields (forward-compat via version).
    """
    version = sidecar.get("olivas_version", 0)
    if version > SIDECAR_VERSION:
        # Future version — load what we understand, skip unknown fields
        pass

    # Link tags
    project.link_tags.clear()
    for d in sidecar.get("link_tags", []):
        project.link_tags.append(PpLinkTag(
            label=d.get("label", ""),
            target=d.get("target", ""),
            x=d.get("x", 0),
            y=d.get("y", 0),
            visible=d.get("visible", True),
            closed_arrow=d.get("closed_arrow", True),
        ))

    # Legend tags
    project.legend_tags.clear()
    for d in sidecar.get("legend_tags", []):
        try:
            project.legend_tags.append(PpLegendTag(
                text=d.get("text", ""),
                shape=d.get("shape", "Diamond"),
                x=d.get("x", 0),
                y=d.get("y", 0),
                color=d.get("color", "#fff7c0"),
                visible=d.get("visible", True),
            ))
        except ValueError:
            # Invalid shape — skip (tolerant load)
            pass

    # Linked properties
    by_name = {c.name: c for c in project.components}
    for comp_name, idx_to_lib in sidecar.get("linked_properties", {}).items():
        comp = by_name.get(comp_name)
        if comp is None:
            continue
        for idx_str, library in idx_to_lib.items():
            try:
                idx = int(idx_str)
            except ValueError:
                continue
            if 0 <= idx < len(comp.properties):
                comp.properties[idx].linked_library = library


def save_sidecar(project: PpProject, sch_path: str | Path) -> Path | None:
    """Write the sidecar JSON next to ``sch_path``.

    Returns the sidecar path on success, None if there are no
    extensions to persist (caller can skip writing in that case).
    """
    sidecar = project_to_sidecar_dict(project)
    has_extensions = (
        sidecar["link_tags"]
        or sidecar["legend_tags"]
        or sidecar["linked_properties"]
    )
    if not has_extensions:
        # Don't pollute filesystem with empty sidecars
        return None

    path = sidecar_path_for(sch_path)
    path.write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def load_sidecar(project: PpProject, sch_path: str | Path) -> bool:
    """Load sidecar JSON if it exists; populate ``project`` in-place.

    Returns True if a sidecar was loaded, False otherwise.
    """
    path = sidecar_path_for(sch_path)
    if not path.exists():
        return False
    try:
        sidecar = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    populate_project_from_sidecar(project, sidecar)
    return True


__all__ = [
    "SIDECAR_VERSION",
    "SIDECAR_EXTENSION",
    "sidecar_path_for",
    "project_to_sidecar_dict",
    "populate_project_from_sidecar",
    "save_sidecar",
    "load_sidecar",
]
