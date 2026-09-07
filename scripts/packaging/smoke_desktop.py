"""Launch the actual packaged app with an isolated, empty user profile."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    executable = Path(sys.argv[1]).resolve()
    if not executable.is_file():
        raise SystemExit(f"Missing desktop executable: {executable}")
    with tempfile.TemporaryDirectory(prefix="scholarnova-smoke-") as directory:
        env = {k: v for k, v in os.environ.items()
               if not any(word in k.upper() for word in ("API_KEY", "TOKEN", "ELECTRON_RUN_AS_NODE"))}
        env["SCHOLARNOVA_SMOKE_DIR"] = directory
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        completed = subprocess.run(
            [str(executable), "--smoke-test"], cwd=directory, env=env,
            timeout=120, creationflags=flags,
        )
        result = Path(directory) / "smoke-result.json"
        if completed.returncode or not result.exists():
            for log in (Path(directory) / "logs").glob("*.log"):
                print(log.read_text(encoding="utf-8", errors="replace")[-4000:])
            raise SystemExit("Packaged application smoke test failed")
        payload = json.loads(result.read_text(encoding="utf-8"))
        assert payload["success"] and len(payload["pages"]) == 5
        if len(sys.argv) > 2:
            report_dir = Path(sys.argv[2]).resolve()
            report_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(result, report_dir / "smoke-result.json")
            shutil.copytree(Path(directory) / "smoke-pages", report_dir / "screenshots", dirs_exist_ok=True)
        print(json.dumps(payload))


if __name__ == "__main__":
    main()
