"""Fail packaging if application, backend, frontend and lock versions diverge."""
import json
from pathlib import Path
import re
import tomllib

root = Path(__file__).resolve().parents[2]
version = json.loads((root / "package.json").read_text())["version"]
for file in ("package-lock.json", "frontend/package.json", "frontend/package-lock.json"):
    data = json.loads((root / file).read_text())
    assert data["version"] == version, file
    if "packages" in data:
        assert data["packages"][""]["version"] == version, file
assert tomllib.loads((root / "backend/pyproject.toml").read_text(encoding="utf-8"))["project"]["version"] == version
backend_version = re.search(r'__version__ = "([^"]+)"', (root / "backend/app/__init__.py").read_text(encoding="utf-8")).group(1)
assert backend_version == version
print(f"All versions match: {version}")
