"""Stage PyInstaller backend output into desktop/release/backend (cross-platform)."""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "dist", "ScholarNovaBackend")
DST = os.path.join(ROOT, "desktop", "release", "backend", "ScholarNovaBackend")

if not os.path.exists(SRC):
    raise SystemExit(f"PyInstaller output not found: {SRC}")

if os.path.exists(DST):
    shutil.rmtree(DST)
os.makedirs(os.path.dirname(DST), exist_ok=True)
shutil.copytree(SRC, DST)
print(f"staged backend -> {DST}")
