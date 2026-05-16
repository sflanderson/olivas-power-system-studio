# -*- mode: python ; coding: utf-8 -*-
"""
olivas_community.spec — PyInstaller spec para a edição COMMUNITY.

Características:
* Mesmo conjunto de exclusões legais que olivas_pro.spec.
* Adiciona runtime hook que força tier=educational independente
  do estado do license server.
* Nome do executável: ``OlivasPSS-Community``.
* Distribuição: gratuita via GitHub Releases, sob Apache 2.0.

Uso:
    pyinstaller build/olivas_community.spec --clean --noconfirm
"""

from pathlib import Path

project_root = Path(SPECPATH).resolve().parent

block_cipher = None

datas = []

atp_templates = project_root / "app" / "preprocessor" / "atp_templates"
if atp_templates.is_dir():
    datas.append((str(atp_templates), "app/preprocessor/atp_templates"))

catalog_specs = project_root / "app" / "preprocessor" / "catalog_specs"
if catalog_specs.is_dir():
    datas.append((str(catalog_specs), "app/preprocessor/catalog_specs"))

resources = project_root / "app" / "resources"
if resources.is_dir():
    datas.append((str(resources), "app/resources"))

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtPrintSupport",
    "PySide6.QtSvg",
    "matplotlib.backends.backend_qt5agg",
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.backend_pdf",
    "numpy",
    "app.commercial.feature_gates",
    "app.examples.stevenson_pf_3bus",
    "app.examples.stevenson_sequential",
    "app.examples.iec60909_annex_c",
    "app.examples.ieee1584_ex_d2",
    "app.examples.ieee399_motor_starting",
    "app.examples.nbr17227_example",
]

excludes = [
    "tkinter", "tcl", "tk",
    "unittest", "test",
    "PySide6.QtMultimedia",
    "PySide6.QtWebEngine",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.QtCharts",
    "PySide6.QtOpenGL",
    "PySide6.QtQml",
    "PySide6.QtQuick",
]

FORBIDDEN_PATHS_IN_BUNDLE = [
    "app/core/GNUATP",
    "pre-processor",
    "_tmp_ptw",
    "LIB/PTW_MANUAL",
    "LIB/LIB",
    "LIBRARY",
    "library_relay/SEL",
    "restore_points",
    "runs",
]


# Runtime hook que força tier educational na inicialização
runtime_hooks = [str(project_root / "build" / "runtime_hook_community.py")]


a = Analysis(
    [str(project_root / "app" / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)


def _is_forbidden(src_path: str) -> bool:
    norm = src_path.replace("\\", "/")
    for forbidden in FORBIDDEN_PATHS_IN_BUNDLE:
        if forbidden in norm:
            return True
    return False


a.datas = [(dest, src, kind) for (dest, src, kind) in a.datas
           if not _is_forbidden(src) and not _is_forbidden(dest)]
a.binaries = [(dest, src, kind) for (dest, src, kind) in a.binaries
              if not _is_forbidden(src) and not _is_forbidden(dest)]


pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon_path = project_root / "app" / "resources" / "logo.ico"
icon_arg = str(icon_path) if icon_path.is_file() else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OlivasPSS-Community",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_arg,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="OlivasPSS-Community",
)
