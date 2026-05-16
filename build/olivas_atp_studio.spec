# -*- mode: python ; coding: utf-8 -*-
"""
olivas_atp_studio.spec — PyInstaller spec para gerar
distribuição standalone Windows/Linux/macOS.

Uso:
    pyinstaller build/olivas_atp_studio.spec --clean

Saída:
    dist/OlivasATPStudio/  (folder onefile alternativo: --onefile)
    dist/OlivasATPStudio.exe (Windows)

Configuração:
    * Coleta automaticamente templates ATP (.mod), library_relay,
      catalog_specs, e ícones.
    * Incluí PySide6 + matplotlib + numpy.
    * Exclui pacotes desnecessários (tkinter, test, unittest)
      para reduzir tamanho.
"""

from pathlib import Path

import sys

# Project root (assumed: this file is build/olivas_atp_studio.spec)
project_root = Path(SPECPATH).resolve().parent

block_cipher = None

# Resources to bundle (relative to project_root, dest in build)
datas = []

# ATP templates
atp_templates = project_root / "app" / "preprocessor" / "atp_templates"
if atp_templates.is_dir():
    datas.append((str(atp_templates), "app/preprocessor/atp_templates"))

# Catalog specs (.ocomp)
catalog_specs = project_root / "app" / "preprocessor" / "catalog_specs"
if catalog_specs.is_dir():
    datas.append((str(catalog_specs), "app/preprocessor/catalog_specs"))

# Library de relés (manuais SEL/ABB/Schneider)
library_relay = project_root / "library_relay"
if library_relay.is_dir():
    datas.append((str(library_relay), "library_relay"))

# Resources (icons, etc)
resources = project_root / "app" / "resources"
if resources.is_dir():
    datas.append((str(resources), "app/resources"))

# Hidden imports — força inclusão de módulos descobertos via lazy import
hiddenimports = [
    # PySide6 components
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtPrintSupport",   # para PDF export
    "PySide6.QtSvg",
    # Matplotlib backends
    "matplotlib.backends.backend_qt5agg",
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.backend_pdf",
    # Numpy + scipy core
    "numpy",
    # App modules que podem ser lazy-importados via examples/registry
    "app.examples.stevenson_pf_3bus",
    "app.examples.stevenson_sequential",
    "app.examples.iec60909_annex_c",
    "app.examples.ieee1584_ex_d2",
    "app.examples.ieee399_motor_starting",
    "app.examples.nbr17227_example",
]

# Excluir pesos desnecessários
excludes = [
    "tkinter", "tcl", "tk",
    "unittest", "test",
    "PySide6.QtNetwork",   # não usado
    "PySide6.QtMultimedia",
    "PySide6.QtWebEngine",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.QtCharts",   # usamos matplotlib
    "PySide6.QtOpenGL",
    "PySide6.QtQml",
    "PySide6.QtQuick",
]

a = Analysis(
    [str(project_root / "app" / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Ícone — opcional. Path relativo ao project_root.
icon_path = project_root / "app" / "resources" / "icon.ico"
icon_arg = str(icon_path) if icon_path.is_file() else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OlivasATPStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,    # UPX comprime mas pode dar antivirus false-positive
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
    name="OlivasATPStudio",
)
