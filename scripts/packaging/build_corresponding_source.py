"""Build a versioned source companion from a Git commit and pinned upstream sources.

Only Git-tracked files from --ref enter project/. No working-directory snapshot,
user configuration, database, virtualenv, or Git credentials are copied.
Downloads can be reused through --cache-dir; --offline forbids network access.
"""
from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = "scripts/packaging/corresponding-source-lock.json"
LEGAL_NAME = re.compile(r"^(?:licen[cs]e|copying|notice|copyright)(?:[._-].*)?$", re.I)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(*args: str, root: Path = ROOT) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args])


def fetch_source(artifact: dict, cache: Path, offline: bool) -> Path:
    target = cache / artifact["filename"]
    if target.exists():
        if target.stat().st_size == artifact["size"] and digest(target) == artifact["sha256"]:
            return target
        raise ValueError(f"Cached source checksum mismatch: {target.name}; remove it and retry")
    if offline:
        raise ValueError(f"Offline source missing: {target.name}")
    if not artifact["url"].startswith("https://"):
        raise ValueError("Upstream source URLs must use HTTPS")
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=cache, prefix=target.name + ".", suffix=".part", delete=False) as temp:
        partial = Path(temp.name)
    try:
        request = urllib.request.Request(artifact["url"], headers={"User-Agent": "ScholarNova-source-release/1"})
        with urllib.request.urlopen(request, timeout=90) as response, partial.open("wb") as output:
            if not response.url.startswith("https://"):
                raise ValueError("Source download redirected away from HTTPS")
            shutil.copyfileobj(response, output, 1024 * 1024)
        if partial.stat().st_size != artifact["size"] or digest(partial) != artifact["sha256"]:
            raise ValueError(f"Downloaded source checksum mismatch: {target.name}")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    return target


def inspect_source(path: Path, artifact: dict) -> dict:
    """Inspect archive members without extracting or executing upstream code."""
    with tarfile.open(path, "r:gz") as archive:
        members = [item for item in archive.getmembers() if item.isfile()]
        for member in members:
            parts = PurePosixPath(member.name)
            if parts.is_absolute() or ".." in parts.parts:
                raise ValueError(f"Unsafe upstream archive member: {member.name}")
        names = [item.name for item in members]
        license_members = [name for name in names if LEGAL_NAME.match(PurePosixPath(name).name)]
        if not license_members:
            raise ValueError(f"Source archive has no license files: {path.name}")
        thirdparty = {}
        omitted_submodules = []
        if artifact["name"] == "MuPDF":
            if not any(name.endswith("/source/fitz/document.c") for name in names):
                raise ValueError("MuPDF archive is missing core C source")
            for name in names:
                parts = PurePosixPath(name).parts
                if "thirdparty" in parts:
                    index = parts.index("thirdparty")
                    if len(parts) > index + 2:
                        dependency = parts[index + 1]
                        thirdparty[dependency] = thirdparty.get(dependency, 0) + 1
            if len(thirdparty) < 10 or sum(thirdparty.values()) < 1000:
                raise ValueError("MuPDF source lacks populated thirdparty dependencies")
            known_omissions = {item["path"]: item for item in artifact.get("omitted_nested_submodules", [])}
            for name in names:
                if PurePosixPath(name).name != ".gitmodules":
                    continue
                config = configparser.ConfigParser()
                config.read_string(archive.extractfile(name).read().decode())
                for section in config.sections():
                    subdir = PurePosixPath(name).parent / config[section]["path"]
                    if not any(member.startswith(str(subdir) + "/") for member in names):
                        relative = str(PurePosixPath(*subdir.parts[1:]))
                        if relative not in known_omissions:
                            raise ValueError(f"Undocumented missing MuPDF submodule: {relative}")
                        omitted_submodules.append(known_omissions[relative])
        return {"files": len(names), "license_members": license_members, "thirdparty_files": thirdparty,
                "omitted_nested_submodules": omitted_submodules}


def verify_project_archive(archive: zipfile.ZipFile) -> None:
    for entry in archive.namelist():
        parts = PurePosixPath(entry).parts
        leaf = parts[-1].lower() if parts else ""
        private_env = (leaf == ".env" or leaf.startswith(".env.") or leaf.endswith(".env")) and leaf not in {
            ".env.example", ".env.sample", ".env.template",
        }
        if ".git" in parts or private_env or leaf in {".git-credentials", "model_config.json", "network_config.json"}:
            raise ValueError(f"Ref contains forbidden private file: {entry}")
        if leaf.endswith((".db", ".sqlite", ".sqlite3", ".pem", ".key")):
            raise ValueError(f"Ref contains a database or credential file: {entry}")
    required = [
        "LICENSE", "THIRD_PARTY_NOTICES.md", "LICENSES/AGPL-3.0.txt",
        "requirements-lock.txt", "package-lock.json", "frontend/package-lock.json",
        "scripts/packaging/ScholarNovaBackend.spec", LOCK_PATH,
    ]
    missing = [name for name in required if "project/" + name not in archive.namelist()]
    if missing:
        raise ValueError(f"Commit is missing release source/legal files: {', '.join(missing)}")


def write_rebuild(version: str, commit: str) -> str:
    return f"""ScholarNova {version}: corresponding source / 对应源码
Git commit: {commit}

project/ contains the exact committed application source, lockfiles, packaging
scripts, project MIT license, desktop distribution notice and license texts.
upstream/ contains byte-for-byte source distributions with pinned SHA-256.
SOURCE_MANIFEST.json records versions, source origins and archive contents.
SHA256SUMS covers every payload file except itself. Verify it before rebuilding.

Rebuild the application (Python 3.12, Node 22, platform native toolchain):
  cd project
  python -m venv .venv
  Activate .venv (Windows: .venv\\Scripts\\activate; macOS: source .venv/bin/activate)
  python -m pip install -r requirements-lock.txt
  python -m pip install -e backend --no-deps
  python -m pip install pyinstaller
  npm ci
  npm --prefix frontend ci
  npm run build:frontend
  python -m PyInstaller scripts/packaging/ScholarNovaBackend.spec --noconfirm --clean
  python scripts/packaging/stage_backend.py
  python scripts/packaging/collect_notices.py
  Windows: npx electron-builder --win nsis portable --publish never
  macOS: npx electron-builder --mac --publish never
See project/docs/desktop-release.zh-CN.md for the complete platform workflow.
Signing requires your own certificate; none is supplied. General build tools
and other dependencies are installed from the repositories named by lockfiles.
This is a source rebuild recipe, not a claim of bit-for-bit reproducible binaries.

Rebuild the included PyMuPDF/MuPDF instead of downloading a wheel:
  Extract upstream/mupdf-1.26.3-source.tar.gz and pymupdf-1.26.3.tar.gz.
  MuPDF's official source tar includes populated thirdparty sources and their
  original notices; do not replace it with a GitHub archive lacking submodules.
  Set PYMUPDF_SETUP_MUPDF_BUILD to the absolute extracted MuPDF directory.
  Run python -m pip wheel --no-deps /absolute/path/to/pymupdf-1.26.3
  Install the generated wheel before freezing the backend.
PyMuPDF setup.py and its bundled build helpers describe required C/C++ tools,
SWIG, MuPDF configuration overrides and Windows/macOS build options. Preserve
those defaults when reproducing the wheel. Build tools may require downloads.
The release uses upstream wheels without local patches to PyMuPDF or MuPDF.

The official MuPDF tar has four EMPTY nested submodules, recorded with exact
upstream repositories, Git commits and purpose in SOURCE_MANIFEST.json:
FreeType's optional FT_DEBUG_LOGGING dlg, Tesseract's test data/googletest,
and ZXing's nested zint (MuPDF builds against its populated top-level zint).
These are not used by MuPDF's normal bundled library build. For those optional
standalone/debug/test builds, read each omitted_nested_submodules entry and run:
  git clone --no-checkout <repository> <extracted-MuPDF>/<path>
  git -C <extracted-MuPDF>/<path> checkout --detach <commit>
Do not substitute a moving main branch. Build configurations not exercised by
the packaged upstream wheels may need additional upstream development tools.

certifi's original MPL source, CA bundle and license are in its included sdist.
Electron's upstream distribution includes LICENSE.electron.txt and
LICENSES.chromium.html; retain them. This companion specifically carries the
application, PyMuPDF/MuPDF and certifi sources; it is not a mirror of all Electron,
Chromium, Python, Node or operating-system sources. See THIRD_PARTY_NOTICES.md
and the installed package's notices for those components and source locations.

中文说明：项目源码按指定 Git 提交导出，不包含未跟踪的用户数据、API KEY、
数据库或本地环境。第三方源码使用原始固定版本归档并核验 SHA-256，MuPDF
自带默认构建的 thirdparty 子依赖源码；四个未随官方归档附带的可选嵌套
子模块已逐项注明用途及固定提交复取方式。源码仍保留各自许可证，发行说明见
project/THIRD_PARTY_NOTICES.md。本包不提供用户配置、签名证书或商业授权。
"""


def check_runtime(lock: dict, executable: str) -> dict:
    installed = json.loads(subprocess.check_output([
        executable, "-I", "-c",
        "import json,importlib.metadata as m,pymupdf; print(json.dumps({"
        "'PyMuPDF':m.version('PyMuPDF'),'MuPDF':pymupdf.VersionFitz,'certifi':m.version('certifi')}))",
    ]))
    for artifact in lock["artifacts"]:
        if installed.get(artifact["name"]) != artifact["version"]:
            raise ValueError(f"Runtime/source version mismatch: {artifact['name']}")
    return installed


def build_bundle(ref: str, output: Path, cache: Path, offline: bool, runtime_python: str | None) -> Path:
    commit = git("rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
    package = json.loads(git("show", f"{commit}:package.json"))
    version = package["version"]
    if not re.fullmatch(r"[0-9A-Za-z.+-]+", version):
        raise ValueError("Invalid release version")
    lock = json.loads(git("show", f"{commit}:{LOCK_PATH}"))
    requirements = git("show", f"{commit}:requirements-lock.txt").decode()
    for artifact in lock["artifacts"]:
        if artifact["name"] != "MuPDF" and not re.search(
            rf"^{re.escape(artifact['name'])}=={re.escape(artifact['version'])}\s*$",
            requirements, re.I | re.M,
        ):
            raise ValueError(f"Dependency lock/source version mismatch: {artifact['name']}")
    installed = check_runtime(lock, runtime_python) if runtime_python else None
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"ScholarNova-{version}-corresponding-source.zip"
    manifest = {"schema_version": 1, "project_version": version, "git_commit": commit,
                "runtime_versions_checked": installed, "upstream": [], "payload_files": {}}
    with tempfile.TemporaryDirectory(prefix="scholarnova-source-") as temp:
        project_archive = Path(temp) / "project.zip"
        git("archive", "--format=zip", "--prefix=project/", f"--output={project_archive}", commit)
        with zipfile.ZipFile(project_archive) as project:
            verify_project_archive(project)
        sources = []
        for artifact in lock["artifacts"]:
            source = fetch_source(artifact, cache, offline)
            details = inspect_source(source, artifact)
            manifest["upstream"].append({**artifact, **details})
            sources.append((source, artifact))
        staged = Path(temp) / destination.name
        with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
            def add_bytes(name: str, data: bytes) -> None:
                bundle.writestr(name, data)
                manifest["payload_files"][name] = hashlib.sha256(data).hexdigest()

            with zipfile.ZipFile(project_archive) as project:
                for item in project.infolist():
                    if not item.is_dir():
                        add_bytes(item.filename, project.read(item))
            for source, artifact in sources:
                name = "upstream/" + source.name
                bundle.write(source, name, compress_type=zipfile.ZIP_STORED)
                manifest["payload_files"][name] = artifact["sha256"]
                with tarfile.open(source, "r:gz") as archive:
                    for member in archive.getmembers():
                        if member.isfile() and LEGAL_NAME.match(PurePosixPath(member.name).name):
                            stream = archive.extractfile(member)
                            if stream:
                                add_bytes("upstream-licenses/" + artifact["name"] + "/" + member.name, stream.read())
            add_bytes("REBUILD.txt", write_rebuild(version, commit).encode())
            manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
            bundle.writestr("SOURCE_MANIFEST.json", manifest_bytes)
            checksums = {**manifest["payload_files"], "SOURCE_MANIFEST.json": hashlib.sha256(manifest_bytes).hexdigest()}
            bundle.writestr("SHA256SUMS", "".join(f"{sha}  {name}\n" for name, sha in sorted(checksums.items())))
        shutil.copyfile(staged, destination)
    print(f"Built {destination.name}: {destination.stat().st_size:,} bytes; commit {commit}")
    print(f"SHA256 {digest(destination)}")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD", help="Exact committed release ref (working tree is never copied)")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "desktop/dist")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "outputs/source-cache")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--runtime-python", help="Optional packaged-runtime Python for exact version verification")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-only", action="store_true", help="Download/verify current source lock before committing")
    mode.add_argument("--check-runtime-only", action="store_true", help="Verify installed runtime versions; no downloads or Git archive")
    args = parser.parse_args()
    if args.check_runtime_only:
        lock = json.loads((ROOT / LOCK_PATH).read_text(encoding="utf-8"))
        print(json.dumps(check_runtime(lock, args.runtime_python or sys.executable)))
        return
    if args.prepare_only:
        lock = json.loads((ROOT / LOCK_PATH).read_text(encoding="utf-8"))
        for artifact in lock["artifacts"]:
            print(f"Preparing {artifact['filename']} ({artifact['size']:,} bytes)", flush=True)
            source = fetch_source(artifact, args.cache_dir, args.offline)
            print(json.dumps({"name": artifact["name"], **inspect_source(source, artifact)}), flush=True)
        return
    build_bundle(args.ref, args.output_dir, args.cache_dir, args.offline, args.runtime_python)


if __name__ == "__main__":
    main()
