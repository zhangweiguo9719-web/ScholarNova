"""Stage PyInstaller backend output into desktop/release/backend (cross-platform)."""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "dist", "ScholarNovaBackend")
DST = os.path.join(ROOT, "desktop", "release", "backend", "ScholarNovaBackend")

if not os.path.exists(SRC):
    raise SystemExit(f"PyInstaller output not found: {SRC}")

if os.path.exists(DST):
    if not os.path.realpath(DST).startswith(os.path.realpath(os.path.join(ROOT, "desktop", "release")) + os.sep):
        raise SystemExit("Refusing to replace a path outside desktop/release")
    shutil.rmtree(DST)
os.makedirs(os.path.dirname(DST), exist_ok=True)
# PyInstaller's macOS framework bundles require their relative symlinks intact.
shutil.copytree(SRC, DST, symlinks=True)
print(f"staged backend -> {DST}")
