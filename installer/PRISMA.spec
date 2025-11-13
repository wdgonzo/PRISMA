# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification File for PRISMA
==========================================
Builds standalone PRISMA.exe from run_prisma.py

Usage:
    pyinstaller PRISMA.spec

Output:
    dist/PRISMA.exe - Standalone executable (~50-100MB)

Requirements:
    - PyInstaller installed: pip install pyinstaller
    - All PRISMA dependencies installed
    - Run from PRISMA root directory

Author: William Gonzalez
Date: November 2025
Version: Beta 0.3
"""

import sys
from pathlib import Path

# Determine paths
spec_root = Path(SPECPATH).parent  # PRISMA root directory
xrd_path = spec_root / 'XRD'

# Collect all XRD package modules
xrd_modules = []
for subdir in ['core', 'gui', 'hpc', 'processing', 'tools', 'utils', 'visualization']:
    module_path = xrd_path / subdir
    if module_path.exists():
        xrd_modules.append((str(module_path), f'XRD/{subdir}'))

# Hidden imports (modules not detected by PyInstaller)
hidden_imports = [
    # XRD subpackages
    'XRD.core.gsas_processing',
    'XRD.core.image_loader',
    'XRD.gui.main_launcher',
    'XRD.gui.batch_processor_widget',
    'XRD.gui.workspace_dialog',
    'XRD.gui.recipe_builder',
    'XRD.gui.data_analyzer',
    'XRD.hpc.cluster',
    'XRD.processing.data_generator',
    'XRD.processing.batch_processor',
    'XRD.processing.recipes',
    'XRD.utils.config_manager',
    'XRD.utils.update_checker',
    'XRD.utils.path_manager',
    'XRD.visualization.data_visualization',
    'XRD.tools.verify_installation',

    # PyQt5 plugins
    'PyQt5.QtPrintSupport',
    'PyQt5.QtSvg',

    # Dask distributed
    'dask.distributed',
    'distributed',
    'distributed.protocol',
    'distributed.protocol.serialize',
    'distributed.protocol.pickle',

    # Zarr and compression
    'zarr',
    'zarr.storage',
    'zarr.codecs',
    'numcodecs',
    'numcodecs.blosc',

    # Scientific libraries
    'numpy',
    'pandas',
    'scipy',
    'scipy.special',
    'scipy.optimize',
    'matplotlib',
    'matplotlib.backends.backend_qt5agg',
    'seaborn',

    # Image processing
    'fabio',
    'imageio',

    # Utilities
    'tqdm',
    'openpyxl',
    'pybaselines',
    'bokeh',
    'psutil',
    'threadpoolctl',
]

# Data files to include
datas = [
    # Documentation
    (str(spec_root / 'README.md'), '.'),
    (str(spec_root / 'CHANGELOG.md'), '.'),
    (str(spec_root / 'LICENSE'), '.'),  # Temporary license (now exists)

    # Configuration files
    (str(spec_root / 'requirements.txt'), '.'),
]

# Add docs if they exist
docs_dir = spec_root / 'docs'
if docs_dir.exists():
    datas.append((str(docs_dir), 'docs'))

# Binary dependencies to exclude (reduce size)
excludes = [
    # Test frameworks
    'pytest',
    'unittest',

    # Development tools
    'black',
    'flake8',
    'mypy',

    # Jupyter
    'jupyter',
    'ipython',
    'notebook',

    # Unused backends
    'tkinter',
    'PySide2',
    'PySide6',
    'PyQt6',
]

# Analysis
a = Analysis(
    [str(spec_root / 'run_prisma.py')],
    pathex=[str(spec_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# PYZ (Python zip archive)
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None
)

# EXE (Windows executable)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PRISMA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress with UPX
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed mode (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(spec_root / 'installer' / 'prisma_icon.ico'),  # Application icon
    version_file=None,  # Can add version info resource later
)

# Optional: Create COLLECT for one-dir mode (uncomment if needed)
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='PRISMA',
# )
