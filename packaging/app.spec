# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 6.x spec for the single-file Windows build of Inventory.

Authored now (task 12) and executed later by task 13 once
``backend/launcher.py`` exists. Nothing here runs at authoring time; the
build command is:

    pyinstaller --clean --noconfirm packaging/app.spec

The spec is written for onefile mode: ``a.binaries``/``a.datas`` are passed
directly to ``EXE``. A commented onedir variant is kept at the bottom for
future reference; it is not built.

Notes:
- ``SPECPATH`` is injected by PyInstaller and points at this spec's directory
  (``<repo>/packaging``), so ``PROJECT_ROOT`` is the repository root even when
  invoked from a different working directory.
- The SPA build (``frontend/dist``) is bundled as a data directory, so the
  frozen app can serve it from ``sys._MEIPASS/frontend/dist``.
- Runtime ``data/`` and ``static/images/`` are NOT bundled; the app creates
  them next to the executable on first run.
- ``uvicorn[standard]`` extras that only exist on POSIX are intentionally
  excluded from ``hiddenimports``; the mirror modules of the installed
  websockets/http packages are listed explicitly instead.
"""

from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata

# PyInstaller injects SPECPATH into the spec namespace at execution time.
PROJECT_ROOT = Path(SPECPATH).resolve().parent
BACKEND = PROJECT_ROOT / "backend"
SPA = PROJECT_ROOT / "frontend" / "dist"

hiddenimports = [
    # uvicorn loads its implementation modules dynamically through import
    # strings, so static analysis cannot see them.
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    # anyio selects its async backend via a dynamically imported module.
    "anyio._backends._asyncio",
    # SQLAlchemy dialect/plugin discovery.
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.pysqlite",
    "sqlalchemy.sql.default_comparator",
    # Pydantic v2 compiled core and FastAPI form parsing support.
    "pydantic",
    "pydantic_core",
    "multipart",
    "h11",
    "greenlet",
]

datas = [(str(SPA), "frontend/dist")]

# FastAPI/Starlette/uvicorn/pydantic expose entry-point metadata that is read
# at runtime (e.g. version lookups); copy the dist-info folders into the bundle.
datas += copy_metadata("fastapi")
datas += copy_metadata("starlette")
datas += copy_metadata("uvicorn")
datas += copy_metadata("pydantic")

a = Analysis(
    [str(BACKEND / "launcher.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Inventory",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(PROJECT_ROOT / "packaging/version_info.txt"),
)

# ---------------------------------------------------------------------------
# onedir variant (NOT built; kept for future reference)
#
# To switch to onedir, comment out the onefile EXE above and enable this block.
# It produces dist/Inventory/Inventory.exe plus sidecar files, which starts
# faster and makes missing-module debugging easier.
#
# exe = EXE(
#     pyz,
#     a.scripts,
#     [],
#     exclude_binaries=True,
#     name="Inventory",
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=False,
#     console=True,
#     disable_windowed_traceback=False,
#     argv_emulation=False,
#     target_arch=None,
#     codesign_identity=None,
#     entitlements_file=None,
#     version=str(PROJECT_ROOT / "packaging/version_info.txt"),
# )
#
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.datas,
#     strip=False,
#     upx=False,
#     upx_exclude=[],
#     name="Inventory",
# )
# ---------------------------------------------------------------------------
