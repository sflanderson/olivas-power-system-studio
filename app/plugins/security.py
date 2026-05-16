"""
app.plugins.security — security primitives para plugins
(v1.5.0 Sprint C).

Camada de segurança **obrigatória** entre discovery e load:

1. **SHA256 hash** — manifest pode declarar ``content_sha256``
   do entry_point.py. Se hash não bate, plugin é recusado
   (detecta tampering pós-install).

2. **Permissions whitelist** — plugin declara `permissions: [...]`
   no manifest. Whitelist é fechada (enum em ``manifest.py``);
   permissões fora da whitelist são recusadas no parse.

3. **Install/Uninstall workflow** — copy seguro de plugin para
   `~/.olivas/plugins/<name>/` com:
   - validação manifest
   - check version compat com Olivas atual
   - check permissões na whitelist
   - copy atômico (escreve em tmp + rename)

**Não** implementa sandbox real (Python sandboxing é hard e quebra
casos legítimos como `import math`). Em vez disso, exibe disclaimer
explícito na UI: "este plugin roda como você; instale apenas de
fontes confiáveis".
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Union

from app.core.logging_config import get_logger
from app.plugins.manifest import (
    PluginManifest, PluginPermission, load_manifest_from_path,
)

log = get_logger(__name__)

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# SHA256 hash
# ---------------------------------------------------------------------------


def compute_sha256(path: PathLike, *, chunk_size: int = 65536) -> str:
    """
    Compute SHA256 hex digest de um arquivo (chunked para arquivos
    grandes).
    """
    h = hashlib.sha256()
    p = Path(path)
    with p.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def verify_sha256(path: PathLike, expected_hex: str) -> bool:
    """
    True se SHA256(path) == expected_hex (case-insensitive).
    """
    if not expected_hex:
        return False
    actual = compute_sha256(path)
    return actual.lower() == expected_hex.lower()


# ---------------------------------------------------------------------------
# Permissions whitelist check
# ---------------------------------------------------------------------------


_KNOWN_PERMISSIONS: frozenset[str] = frozenset(
    p.value for p in PluginPermission
)


def check_permissions_supported(
    permissions: Iterable[str],
) -> tuple[bool, str]:
    """
    Verifica se TODAS as permissões pedidas estão na whitelist
    fechada (enum :class:`PluginPermission`).

    Returns
    -------
    (ok, message)
        ``ok=True, message=''`` se tudo OK.
        ``ok=False, message='Permissão desconhecida: X'`` caso
        contrário.
    """
    unknown = [
        p for p in permissions
        if str(p) not in _KNOWN_PERMISSIONS
    ]
    if unknown:
        return False, (
            f"Permissão(ões) desconhecida(s): {unknown}. "
            f"Suportadas: {sorted(_KNOWN_PERMISSIONS)}"
        )
    return True, ""


# ---------------------------------------------------------------------------
# Install / Uninstall workflow
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InstallResult:
    """Resultado de install/uninstall — usado pela UI marketplace."""

    success: bool
    message: str
    installed_path: Optional[Path] = None
    manifest: Optional[PluginManifest] = None


def install_plugin(
    *,
    source_dir: PathLike,
    target_root: PathLike,
    olivas_version: str,
    verify_sha: bool = True,
) -> InstallResult:
    """
    Instala plugin de ``source_dir`` para
    ``target_root/<plugin_name>/``.

    Validações antes de copiar:

    1. ``manifest.yaml`` existe e é válido
    2. ``entry_point`` (default plugin.py) existe
    3. Versão Olivas está em ``[min, max]``
    4. Permissões estão na whitelist
    5. Se manifest tem ``content_sha256``: hash bate (verify_sha=True)

    Copy é **atômico**: escreve em ``target_root/.tmp_<name>/`` e
    move para ``target_root/<name>/`` (substituindo se existir).

    Parameters
    ----------
    source_dir:
        Diretório do plugin a instalar (já com manifest.yaml +
        plugin.py).
    target_root:
        Raiz dos plugins instalados (ex: ~/.olivas/plugins/).
    olivas_version:
        Versão atual do Olivas (para check de compat).
    verify_sha:
        Se True e manifest tem content_sha256, valida hash do
        entry_point antes de instalar.

    Returns
    -------
    InstallResult
    """
    src = Path(source_dir)
    target = Path(target_root)

    manifest_file = src / "manifest.yaml"
    if not manifest_file.is_file():
        return InstallResult(
            success=False,
            message=f"manifest.yaml não encontrado em {src}",
        )

    # 1. Parse + validação Pydantic
    try:
        manifest = load_manifest_from_path(manifest_file)
    except Exception as exc:
        return InstallResult(
            success=False,
            message=f"Manifest inválido: {exc}",
        )

    # 2. Entry point existe
    entry_point = src / manifest.entry_point
    if not entry_point.is_file():
        return InstallResult(
            success=False,
            message=(
                f"entry_point '{manifest.entry_point}' não "
                f"encontrado em {src}"
            ),
            manifest=manifest,
        )

    # 3. Compatibilidade de versão
    if not manifest.is_compatible_with_olivas(olivas_version):
        return InstallResult(
            success=False,
            message=(
                f"Plugin '{manifest.name}' v{manifest.version} "
                f"não compatível com Olivas {olivas_version}. "
                f"Requer [{manifest.min_olivas_version}, "
                f"{manifest.max_olivas_version or '∞'}]."
            ),
            manifest=manifest,
        )

    # 4. Whitelist de permissões
    ok, msg = check_permissions_supported(
        [p.value for p in manifest.permissions],
    )
    if not ok:
        return InstallResult(
            success=False,
            message=f"Permissões inválidas: {msg}",
            manifest=manifest,
        )

    # 5. SHA256 (opcional)
    if verify_sha and manifest.content_sha256:
        if not verify_sha256(entry_point, manifest.content_sha256):
            return InstallResult(
                success=False,
                message=(
                    f"Hash SHA256 do entry_point não bate com "
                    f"o declarado no manifest — possível tampering."
                ),
                manifest=manifest,
            )

    # ---- Copy atômico ----
    target.mkdir(parents=True, exist_ok=True)
    final_dir = target / manifest.name
    tmp_dir = target / f".tmp_{manifest.name}"

    # Limpa tmp residual de tentativas anteriores
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    try:
        shutil.copytree(src, tmp_dir)
        # Substitui final atomicamente (move + rmtree old se existir)
        if final_dir.exists():
            shutil.rmtree(final_dir)
        tmp_dir.rename(final_dir)
    except Exception as exc:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return InstallResult(
            success=False,
            message=f"Falha ao copiar: {type(exc).__name__}: {exc}",
            manifest=manifest,
        )

    log.info(
        "Plugin '%s' v%s instalado em %s",
        manifest.name, manifest.version, final_dir,
    )
    return InstallResult(
        success=True,
        message=(
            f"Plugin '{manifest.display_name}' v{manifest.version} "
            f"instalado com sucesso. "
            f"Habilite-o no Marketplace para começar a usar."
        ),
        installed_path=final_dir,
        manifest=manifest,
    )


def uninstall_plugin(
    *,
    name: str,
    target_root: PathLike,
) -> InstallResult:
    """
    Remove o diretório ``target_root/<name>/`` recursivamente.

    Não toca em state.json — caller (UI marketplace) deve chamar
    :meth:`LifecycleState.remove(name)` separadamente.
    """
    target = Path(target_root) / name
    if not target.exists():
        return InstallResult(
            success=False,
            message=f"Plugin '{name}' não encontrado em {target_root}",
        )

    try:
        shutil.rmtree(target)
    except Exception as exc:
        return InstallResult(
            success=False,
            message=f"Falha ao remover: {type(exc).__name__}: {exc}",
        )

    log.info("Plugin '%s' desinstalado de %s", name, target)
    return InstallResult(
        success=True,
        message=f"Plugin '{name}' removido.",
    )
