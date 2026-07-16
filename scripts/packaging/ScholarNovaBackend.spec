# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path.cwd()
BACKEND = ROOT / "backend"

hiddenimports = []
for package in [
    "app",
    "aiosqlite",
    "asyncpg",
    "greenlet",
    "orjson",
    "pydantic_settings",
    "sse_starlette",
    "uvicorn",
]:
    hiddenimports += collect_submodules(package)

a = Analysis(
    [str(BACKEND / "desktop_server.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff", "mypy", "IPython", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ScholarNovaBackend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ScholarNovaBackend",
    destdir=str(ROOT / "desktop" / "release" / "backend"),
)
