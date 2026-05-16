"""
build/build_distribution.py — script de build dual da distribuição
binária do Olivas Power System Studio (v4.1.0 commercial Sprint 3).

Uso:
    python build/build_distribution.py --edition pro
    python build/build_distribution.py --edition community
    python build/build_distribution.py --edition both    # ambos

Pre-requisitos:
    pip install pyinstaller

Saída:
    dist/OlivasPSS-Pro/         (edição Pro)
    dist/OlivasPSS-Community/   (edição Community)

Garantias clean-room:
* Após o build, o script valida que diretórios proibidos
  (GNUATP, pre-processor, LIB/PTW_MANUAL, etc) não estão
  presentes no bundle. Aborta com exit 2 se encontrar.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


EDITIONS = {
    "pro": ("build/olivas_pro.spec", "OlivasPSS-Pro"),
    "community": ("build/olivas_community.spec", "OlivasPSS-Community"),
}


FORBIDDEN_IN_BUNDLE = [
    "GNUATP",
    "pre-processor",
    "_tmp_ptw",
    "PTW_MANUAL",
    "LIBRARY",
    "library_relay/SEL",
    "restore_points",
    "runs",
]


def _verify_bundle_clean(bundle_dir: Path) -> list[str]:
    """
    Verifica que diretórios/arquivos proibidos não estão no bundle.
    Retorna lista de violações encontradas.
    """
    violations: list[str] = []
    if not bundle_dir.is_dir():
        return [f"bundle_dir não existe: {bundle_dir}"]

    for path in bundle_dir.rglob("*"):
        rel = path.relative_to(bundle_dir).as_posix()
        for forbidden in FORBIDDEN_IN_BUNDLE:
            if forbidden in rel:
                violations.append(rel)
                break
    return violations


def _run_edition(
    project_root: Path,
    edition: str,
    clean: bool,
) -> int:
    spec_rel, bundle_name = EDITIONS[edition]
    spec = project_root / spec_rel
    if not spec.is_file():
        print(f"ERRO: spec não encontrado: {spec}")
        return 1

    if clean:
        for d in ("build", "dist"):
            target = project_root / d
            if target.is_dir() and d == "dist":
                shutil.rmtree(target / bundle_name, ignore_errors=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        str(spec),
    ]
    print(f"\n=== Building edition: {edition} ===")
    print(f"Spec: {spec}")
    result = subprocess.run(cmd, cwd=str(project_root))
    if result.returncode != 0:
        print(f"FALHA build {edition}: returncode {result.returncode}")
        return result.returncode

    dist = project_root / "dist" / bundle_name
    violations = _verify_bundle_clean(dist)
    if violations:
        print(f"\n!!! VIOLAÇÕES CLEAN-ROOM em {bundle_name}:")
        for v in violations[:20]:
            print(f"  - {v}")
        if len(violations) > 20:
            print(f"  ... e mais {len(violations) - 20}")
        print(
            "\nAbortando: bundle contém artefatos proibidos.\n"
            "Revisar exclusões em build/olivas_<edition>.spec."
        )
        return 2

    size_mb = sum(
        f.stat().st_size for f in dist.rglob("*") if f.is_file()
    ) / (1024 * 1024)
    print(f"\nBuild {edition} OK: {dist}")
    print(f"Tamanho total: {size_mb:.1f} MB")
    print(f"Clean-room: OK (zero violações)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Olivas Power System Studio binary distribution",
    )
    parser.add_argument(
        "--edition",
        choices=["pro", "community", "both"],
        required=True,
        help="Qual edição buildar",
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Limpa dist/<edition>/ antes",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print(
            "ERRO: pyinstaller não instalado.\n"
            "Execute: pip install pyinstaller"
        )
        return 1

    editions = (
        ["pro", "community"] if args.edition == "both" else [args.edition]
    )
    for ed in editions:
        rc = _run_edition(project_root, ed, args.clean)
        if rc != 0:
            return rc

    print("\n=== Todos os builds OK ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
