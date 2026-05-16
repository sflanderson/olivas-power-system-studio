"""
scripts/migrate_sch_wires.py — v0.93.3:

Migration tool para corrigir wires desconectados em arquivos
``.sch`` salvos antes da v0.92.1 (Bus PTW + renderer changes).

Sintoma: BUS reporta "0 vizinhos" e o pipeline SC falha com
"nenhuma fonte de SC encontrada" mesmo com Vac/SM/Tr aparente
no canvas.

Causa raiz: wires foram salvos com endpoints que não batem
com os pin positions ATUAIS dos renderers (alguns pinos
mudaram em sprints anteriores; a Bus PTW substituiu os
4 pinos T1_A..T4_C por 21 pinos sintéticos a cada 10 px).

Solução: para cada wire, snap o endpoint mais próximo de
qualquer pino componente (rotation/mirror aplicados) dentro
de tolerância configurável (default 30 px). Wires com
endpoints fora da tolerância de qualquer pino são deixados
intactos (provavelmente intencional — wire-to-wire).

Uso CLI::

    python -m scripts.migrate_sch_wires \\
        app/examples/schematics/ieee399_motor_starting.sch

    # Em batch:
    python -m scripts.migrate_sch_wires \\
        app/examples/schematics/*.sch

Após migração, executa o pipeline de cada BUS para confirmar
conectividade.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from app.preprocessor.models import PpProject, PpWire
from app.preprocessor.qucs_sch_parser import parse_sch_file
from app.preprocessor.qucs_sch_serializer import serialize_sch_file
from app.preprocessor.symbols import BusSymbol, get_renderer


# Distância máxima de snap (em px). Pinos a essa distância
# do endpoint do wire serão considerados o alvo. Acima disso,
# wire é deixado intacto (provavelmente segmento livre).
DEFAULT_SNAP_TOLERANCE = 30


def _rotate_pin(dx: int, dy: int, rotation: int) -> tuple[int, int]:
    """Aplica rotação Qucs (0..3 = 0/90/180/270 degrees CCW)."""
    if rotation == 0:
        return dx, dy
    if rotation == 1:
        return -dy, dx
    if rotation == 2:
        return -dx, -dy
    if rotation == 3:
        return dy, -dx
    return dx, dy


def _mirror_pin(dx: int, dy: int, mirror: int) -> tuple[int, int]:
    """Aplica espelhamento Qucs (1 = horizontal flip)."""
    if mirror:
        return -dx, dy
    return dx, dy


def collect_all_pin_positions(
    project: PpProject,
) -> list[tuple[int, int]]:
    """
    Retorna todas as posições de pinos absolutas no projeto,
    aplicando rotation + mirror de cada componente.
    """
    pins_abs: list[tuple[int, int]] = []
    for comp in project.components:
        renderer = get_renderer(comp.type)
        if renderer is None:
            continue
        # BusSymbol é stateful — precisa update_from_component
        if isinstance(renderer, BusSymbol):
            renderer = BusSymbol()
            renderer.update_from_component(comp)
        local_pins = renderer.pin_positions()
        for dx, dy in local_pins:
            mx, my = _mirror_pin(dx, dy, comp.mirror)
            rx, ry = _rotate_pin(mx, my, comp.rotation)
            pins_abs.append((comp.x + rx, comp.y + ry))
    return pins_abs


def snap_endpoint(
    x: int, y: int,
    pins: list[tuple[int, int]],
    tolerance: int,
) -> tuple[int, int]:
    """
    Snap (x, y) ao pino mais próximo dentro de ``tolerance`` px.
    Se não houver, retorna (x, y) intacto.
    """
    best: Optional[tuple[int, int]] = None
    best_d2 = tolerance * tolerance + 1
    for px, py in pins:
        d2 = (px - x) ** 2 + (py - y) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best = (px, py)
    if best is None:
        return x, y
    return best


def migrate_project_wires(
    project: PpProject,
    tolerance: int = DEFAULT_SNAP_TOLERANCE,
) -> tuple[int, int]:
    """
    Snap todos os wire endpoints aos pinos mais próximos.

    Returns
    -------
    tuple[int, int]
        (n_wires_modificados, n_endpoints_snappados)
    """
    pins = collect_all_pin_positions(project)
    if not pins:
        return 0, 0

    n_modified = 0
    n_snapped = 0
    new_wires = []
    for w in project.wires:
        nx1, ny1 = snap_endpoint(w.x1, w.y1, pins, tolerance)
        nx2, ny2 = snap_endpoint(w.x2, w.y2, pins, tolerance)
        modified = False
        if (nx1, ny1) != (w.x1, w.y1):
            n_snapped += 1
            modified = True
        if (nx2, ny2) != (w.x2, w.y2):
            n_snapped += 1
            modified = True
        if modified:
            n_modified += 1
        new_wires.append(PpWire(
            x1=nx1, y1=ny1, x2=nx2, y2=ny2, label=w.label,
        ))
    project.wires = new_wires
    return n_modified, n_snapped


def verify_connectivity(project: PpProject) -> dict[str, int]:
    """
    Para cada BUS no projeto, retorna o número de vizinhos.
    Útil para confirmar que a migração restaurou conectividade.
    """
    from app.postprocessor.bus_pipeline import find_neighbors_of_bus
    out: dict[str, int] = {}
    for c in project.components:
        if c.type == "BUS":
            try:
                neighbors = find_neighbors_of_bus(project, c.name)
                out[c.name] = len(neighbors)
            except Exception:
                out[c.name] = -1
    return out


def migrate_file(path: Path, tolerance: int = DEFAULT_SNAP_TOLERANCE,
                 dry_run: bool = False) -> dict:
    """
    Migra um único arquivo .sch. Salva in-place se dry_run=False.

    Returns
    -------
    dict
        Estatísticas: file, n_wires, n_modified, n_snapped,
        before (conectividade pré), after (conectividade pós).
    """
    project = parse_sch_file(str(path))
    before = verify_connectivity(project)
    n_wires = len(project.wires)
    n_mod, n_snap = migrate_project_wires(project, tolerance)
    after = verify_connectivity(project)

    if not dry_run and n_mod > 0:
        serialize_sch_file(project, str(path))

    return {
        "file": path.name,
        "n_wires": n_wires,
        "n_modified": n_mod,
        "n_snapped": n_snap,
        "before": before,
        "after": after,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Snap wire endpoints aos pinos mais próximos para "
            "corrigir .sch files com pinos desalinhados."
        )
    )
    parser.add_argument(
        "files", nargs="+", help="Arquivos .sch para migrar.",
    )
    parser.add_argument(
        "--tolerance", type=int, default=DEFAULT_SNAP_TOLERANCE,
        help=(
            f"Distância máxima de snap (px). Default "
            f"{DEFAULT_SNAP_TOLERANCE}."
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Não salva, só imprime o que seria modificado.",
    )
    args = parser.parse_args(argv)

    print(f"Snap tolerance: {args.tolerance} px")
    print(f"Dry run: {args.dry_run}")
    print()

    all_ok = True
    for f in args.files:
        path = Path(f)
        if not path.is_file():
            print(f"  ⚠ skipping (not found): {f}")
            continue
        result = migrate_file(path, args.tolerance, args.dry_run)
        before = result["before"]
        after = result["after"]
        before_str = ", ".join(
            f"{k}={v}" for k, v in before.items()
        ) or "-"
        after_str = ", ".join(
            f"{k}={v}" for k, v in after.items()
        ) or "-"
        any_zero_before = any(v == 0 for v in before.values())
        any_zero_after = any(v == 0 for v in after.values())
        status = "✅" if not any_zero_after else "⚠"
        print(
            f"{status} {result['file']}: "
            f"{result['n_modified']}/{result['n_wires']} wires modificados, "
            f"{result['n_snapped']} endpoints snapped"
        )
        print(f"   before: {before_str}")
        print(f"   after:  {after_str}")
        if any_zero_before and not any_zero_after:
            print("   📈 conectividade restaurada!")
        if any_zero_after:
            all_ok = False
        print()

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
