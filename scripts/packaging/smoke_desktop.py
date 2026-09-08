"""Launch the actual packaged app with an isolated, empty user profile."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


class ProcessTree:
    """Own only the smoke run's processes, including portable launchers' children."""

    def __init__(self):
        self.process = None
        self.job = None
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class BasicLimits(ctypes.Structure):
                _fields_ = [
                    ("PerProcessUserTimeLimit", ctypes.c_longlong),
                    ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD),
                ]

            class ExtendedLimits(ctypes.Structure):
                _fields_ = [
                    ("BasicLimitInformation", BasicLimits),
                    ("IoInfo", ctypes.c_ulonglong * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t),
                ]

            self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            for name, arguments in {
                "CreateJobObjectW": [ctypes.c_void_p, wintypes.LPCWSTR],
                "SetInformationJobObject": [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD],
                "AssignProcessToJobObject": [wintypes.HANDLE, wintypes.HANDLE],
                "CloseHandle": [wintypes.HANDLE],
            }.items():
                function = getattr(self.kernel, name)
                function.argtypes = arguments
                function.restype = wintypes.HANDLE if name == "CreateJobObjectW" else wintypes.BOOL
            self.job = self.kernel.CreateJobObjectW(None, None)
            if not self.job:
                raise ctypes.WinError(ctypes.get_last_error())
            limits = ExtendedLimits()
            limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not self.kernel.SetInformationJobObject(self.job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                error = ctypes.WinError(ctypes.get_last_error())
                self.kernel.CloseHandle(self.job)
                self.job = None
                raise error

    def start(self, arguments, **kwargs):
        self.process = subprocess.Popen(
            arguments, start_new_session=sys.platform != "win32", **kwargs,
        )
        if self.job:
            # Popen retains the Windows process handle until wait/cleanup.
            if not self.kernel.AssignProcessToJobObject(self.job, int(self.process._handle)):
                import ctypes

                error = ctypes.WinError(ctypes.get_last_error())
                subprocess.run(["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                raise error
        return self.process

    def close(self):
        if self.job:
            self.kernel.CloseHandle(self.job)
            self.job = None
        elif self.process and sys.platform != "win32":
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
                time.sleep(0.2)
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if self.process:
            self.process.wait(timeout=10)


def save_report(directory, destination):
    if not destination:
        return
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("smoke-result.json", "runner.log"):
        source = directory / name
        if source.exists():
            shutil.copy2(source, destination / name)
    for source_name, target_name in (("smoke-pages", "screenshots"), ("logs", "logs")):
        if (directory / source_name).is_dir():
            shutil.copytree(directory / source_name, destination / target_name, dirs_exist_ok=True)


def main():
    executable = Path(sys.argv[1]).resolve()
    if not executable.is_file():
        raise SystemExit(f"Missing desktop executable: {executable}")
    report_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    with tempfile.TemporaryDirectory(prefix="scholarnova-smoke-") as directory:
        directory = Path(directory)
        env = {k: v for k, v in os.environ.items()
               if not any(word in k.upper() for word in ("API_KEY", "TOKEN", "ELECTRON_RUN_AS_NODE"))}
        env["SCHOLARNOVA_SMOKE_DIR"] = str(directory)
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        tree = ProcessTree()
        started = time.monotonic()
        try:
            with (directory / "runner.log").open("w", encoding="utf-8") as log:
                process = tree.start(
                    [str(executable), "--smoke-test"], cwd=directory, env=env,
                    creationflags=flags, stdout=log, stderr=subprocess.STDOUT,
                )
                completed_at = None
                while process.poll() is None:
                    now = time.monotonic()
                    if completed_at is None and (directory / "smoke-result.json").exists():
                        completed_at = now
                    if completed_at is not None and now - completed_at > 20:
                        raise RuntimeError("Smoke pages passed, but app/portable launcher did not exit within 20s")
                    if now - started > 120:
                        raise RuntimeError("Smoke timed out during startup/pages after 120s")
                    time.sleep(0.25)
                code = process.returncode
            result = directory / "smoke-result.json"
            if code or not result.exists():
                raise RuntimeError(f"Packaged application smoke failed (exit code {code})")
            payload = json.loads(result.read_text(encoding="utf-8"))
            if not payload.get("success") or payload.get("pages") != ["/", "/search", "/knowledge", "/assistant", "/settings"]:
                raise RuntimeError("Incomplete packaged application smoke result")
            if not payload.get("legal_notices") or not payload.get("source_download_entry"):
                raise RuntimeError("Packaged application license/source entry missing")
            print(json.dumps({**payload, "elapsed_seconds": round(time.monotonic() - started, 2)}))
        except Exception:
            for log in (directory / "logs").glob("*.log"):
                print(log.read_text(encoding="utf-8", errors="replace")[-4000:])
            raise
        finally:
            # Kill only this job/session tree before cleaning its temporary profile.
            # subprocess.run(timeout=...) kills only the launcher, leaking Electron.
            tree.close()
            save_report(directory, report_dir)


if __name__ == "__main__":
    main()
