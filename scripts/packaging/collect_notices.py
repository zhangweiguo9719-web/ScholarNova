"""Collect build-environment notices; no model calls, user data, or heavy dependencies.

Run using the same Python interpreter that runs PyInstaller. The Python inventory
is deliberately a build-environment superset, not a claim of exact binary linkage.
The frontend inventory is the installed, non-dev npm lock tree before tree shaking.
Collection is a packaging safeguard, not a legal opinion or complete binary SBOM.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import tempfile
from urllib.parse import quote
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
NOTICE = re.compile(r"^(?:licen[sc]es?|copying|notice|copyright|authors|unlicense)(?:[._-].*|$)", re.I)
SUPPLEMENTS = {("pymupdf", None): "AGPL-3.0.txt", ("certifi", None): "MPL-2.0.txt", ("jiter", "0.10.0"): "jiter-0.10.0-MIT.txt"}
SCOPE = {
    "python": "All installed third-party Python distributions in the build interpreter, including build/dev tools: conservative superset, not exact frozen binary contents.",
    "frontend": "Installed non-dev entries of frontend/package-lock.json, including transitive dependencies before Vite tree shaking; optional platform omissions are recorded.",
    "runtime": "CPython license and the original Electron LICENSE / Chromium aggregated notices from the runtime distribution.",
    "limits": "Not a legal opinion, license compatibility certification, exact binary SBOM, or replacement for corresponding-source distribution obligations. Native subcomponents not declared by package metadata require upstream/source review.",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", value)


def inside(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Notice path escapes its permitted root: {path.name}")
    return resolved


def write_notice(output: Path, relative: str, data: bytes, source: str) -> dict:
    if not data.strip():
        raise ValueError(f"Empty notice: {relative}")
    destination = inside(output / relative, output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return {"path": relative, "sha256": digest(data), "bytes": len(data), "source": source}


def canonical_notices(repo: Path, output: Path) -> dict[str, dict]:
    source_file = repo / "LICENSES/sources.json"
    sources = json.loads(source_file.read_text(encoding="utf-8"))
    notices = {}
    for name, source in sorted(sources.items()):
        data = inside(repo / "LICENSES" / name, repo / "LICENSES").read_bytes()
        if digest(data) != source["sha256"]:
            raise ValueError(f"Official license text changed or is incomplete: {name}")
        notices[name] = write_notice(output, f"licenses/{name}", data, source["url"])
    for required in ("AGPL-3.0.txt", "MPL-2.0.txt"):
        if required not in notices:
            raise ValueError(f"Missing full critical license: {required}")
    notices["sources.json"] = write_notice(output, "licenses/sources.json", source_file.read_bytes(), "repository:LICENSES/sources.json")
    return notices


def python_notices(output: Path, canonical: dict[str, dict], distributions=None) -> list[dict]:
    components = []
    distributions = metadata.distributions() if distributions is None else distributions
    for distribution in sorted(distributions, key=lambda d: d.metadata["Name"].lower()):
        name = distribution.metadata["Name"]
        normalized = re.sub(r"[-_.]+", "-", name.lower())
        if normalized == "scholar-agent-backend":
            continue  # Our own license is copied separately without changing it.
        version = distribution.version
        prefix = f"python/{slug(normalized)}-{slug(version)}"
        notices = []
        installation = Path(distribution.locate_file("")).resolve()
        for file in sorted(distribution.files or [], key=str):
            if not NOTICE.match(file.name):
                continue
            source = inside(Path(distribution.locate_file(file)), installation)
            relative = source.relative_to(installation).as_posix()
            notices.append(write_notice(output, f"{prefix}/{relative}", source.read_bytes(), f"installed-distribution:{relative}"))
        supplement = SUPPLEMENTS.get((normalized, version)) or SUPPLEMENTS.get((normalized, None))
        if supplement:
            notices.append(canonical[supplement])
        if not notices or not any(NOTICE.match(Path(n["path"]).name) and not Path(n["path"]).name.lower().startswith("authors") for n in notices):
            # Known supplemental filenames contain an SPDX label rather than LICENSE.
            if not supplement:
                raise ValueError(f"Missing license text for Python dependency {name} {version}")
        declaration = distribution.metadata.get("License-Expression") or distribution.metadata.get("License")
        if not declaration or declaration == "UNKNOWN":
            declaration = "; ".join(v for v in distribution.metadata.get_all("Classifier", []) if v.startswith("License ::")) or "See collected upstream notices"
        components.append({"ecosystem": "python", "name": name, "version": version,
                           "license_declaration": declaration, "notices": notices})
    names = {re.sub(r"[-_.]+", "-", c["name"].lower()) for c in components}
    if not {"pymupdf", "certifi"}.issubset(names):
        raise ValueError("Build interpreter is missing required PyMuPDF/certifi distributions")
    return components


def npm_notice_files(package: Path) -> list[Path]:
    result = []
    for folder, directories, filenames in os.walk(package, followlinks=False):
        directories[:] = [d for d in directories if d not in ("node_modules", ".git")]
        for filename in sorted(filenames):
            if NOTICE.match(filename):
                candidate = Path(folder) / filename
                result.append(inside(candidate, package))
    if not result:
        # Some npm tarballs carry the entire MIT license only in their README.
        for candidate in sorted(package.glob("README*")):
            if not candidate.is_file():
                continue
            data = candidate.read_bytes().lower()
            if b"permission is hereby granted" in data and b"the software" in data and b"as is" in data:
                result.append(inside(candidate, package))
                break
    return result


def frontend_notices(repo: Path, output: Path) -> tuple[list[dict], list[dict]]:
    frontend = repo / "frontend"
    lock = json.loads((frontend / "package-lock.json").read_text(encoding="utf-8"))
    components, omitted = [], []
    for lock_path, entry in sorted(lock["packages"].items()):
        if not lock_path or entry.get("dev"):
            continue
        package = inside(frontend / lock_path, frontend / "node_modules")
        if not package.is_dir():
            if entry.get("optional"):
                omitted.append({"lock_path": lock_path, "version": entry.get("version"), "reason": "Optional dependency absent on this build platform"})
                continue
            raise ValueError(f"Production frontend dependency not installed: {lock_path}")
        info = json.loads((package / "package.json").read_text(encoding="utf-8"))
        if info["version"] != entry.get("version"):
            raise ValueError(f"Frontend lock/install version mismatch: {lock_path}")
        files = npm_notice_files(package)
        if not files:
            raise ValueError(f"Missing license text for frontend dependency: {lock_path}")
        suffix = digest(lock_path.encode())[:8]
        prefix = f"frontend/{slug(info['name'])}-{slug(info['version'])}-{suffix}"
        notices = []
        for file in files:
            relative = file.relative_to(package).as_posix()
            notices.append(write_notice(output, f"{prefix}/{relative}", file.read_bytes(), f"installed-npm:{lock_path}/{relative}"))
        components.append({"ecosystem": "frontend", "name": info["name"], "version": info["version"],
                           "lock_path": lock_path, "license_declaration": info.get("license", entry.get("license", "See upstream notices")), "notices": notices})
    if not components:
        raise ValueError("No production frontend notices were collected")
    return components, omitted


def python_runtime_notice(output: Path) -> dict:
    base = Path(sys.base_prefix)
    candidates = [base / "LICENSE.txt", base / "LICENSE", base / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "LICENSE.txt"]
    found = next((p for p in candidates if p.is_file()), None)
    source = f"CPython {platform.python_version()} runtime distribution LICENSE"
    if found:
        data = found.read_bytes()
    else:
        # Exact CPython release tag; never follow a package-supplied arbitrary URL.
        source = f"https://raw.githubusercontent.com/python/cpython/v{platform.python_version()}/LICENSE"
        with urlopen(source, timeout=30) as response:
            data = response.read(2_000_000)
    if len(data) < 2000 or b"PYTHON SOFTWARE FOUNDATION LICENSE" not in data:
        raise ValueError("CPython runtime license is missing or incomplete")
    return {"ecosystem": "runtime", "name": "CPython", "version": platform.python_version(),
            "license_declaration": "PSF license and historical / bundled component notices",
            "notices": [write_notice(output, "python-runtime/LICENSE.txt", data, source)]}


def electron_notices(repo: Path, output: Path, runtime: Path) -> dict:
    info = json.loads((repo / "node_modules/electron/package.json").read_text(encoding="utf-8"))
    declared = json.loads((repo / "package.json").read_text(encoding="utf-8"))["devDependencies"]["electron"]
    if info["version"] != declared:
        raise ValueError("Installed Electron does not match the exact package.json version")
    result = []
    for target, names in {"LICENSE.electron.txt": ("LICENSE", "LICENSE.electron.txt"), "LICENSES.chromium.html": ("LICENSES.chromium.html",)}.items():
        found = next((runtime / name for name in names if (runtime / name).is_file()), None)
        if not found:
            raise ValueError(f"Missing original Electron runtime notice: {target}; use --electron-dist")
        data = found.read_bytes()
        if target.endswith("chromium.html") and (len(data) < 100_000 or b"license" not in data.lower()):
            raise ValueError("Chromium aggregated license file is incomplete")
        result.append(write_notice(output, f"electron/{target}", data, f"Electron {info['version']} runtime distribution:{found.name}"))
    return {"ecosystem": "runtime", "name": "Electron / Chromium", "version": info["version"],
            "license_declaration": "Electron MIT; Chromium and bundled components retain their own licenses", "notices": result}


def write_indexes(output: Path, manifest: dict):
    rows = []
    for component in manifest["components"]:
        label = f"{component['ecosystem']}: {component['name']} {component['version']}"
        links = " · ".join(f'<a href="{quote(n["path"], safe="/")}">{html.escape(Path(n["path"]).name)}</a>' for n in component["notices"])
        rows.append(f"<tr><td>{html.escape(label)}</td><td>{links}</td></tr>")
    summary = "# Bundled third-party notices / 随包第三方许可\n\n"
    summary += "This package is not entirely MIT. The original project LICENSE is retained separately. / 本应用包含不同许可的第三方组件，不能将整个安装包描述为仅 MIT。\n\n"
    summary += "\n\n".join(f"- **{key}**: {value}" for key, value in SCOPE.items())
    summary += "\n\nSee [manifest.json](manifest.json) for names, versions, source locations and SHA256 digests; [index.html](index.html) for an offline browser.\n\n"
    summary += "Project distribution notes: [PROJECT_THIRD_PARTY_NOTICES.md](PROJECT_THIRD_PARTY_NOTICES.md). Full AGPL/MPL: [AGPL v3](licenses/AGPL-3.0.txt), [MPL 2.0](licenses/MPL-2.0.txt).\n"
    (output / "THIRD_PARTY_NOTICES.md").write_text(summary, encoding="utf-8")
    page = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ScholarNova · Third-party notices</title>'
    page += '<style>body{font:16px/1.6 system-ui;margin:2rem auto;max-width:1100px;padding:0 1rem;color:#19273b}table{width:100%;border-collapse:collapse}td{border-bottom:1px solid #ddd;padding:.7rem;vertical-align:top;overflow-wrap:anywhere}a{color:#235bbc}p{max-width:90ch}</style>'
    page += '<h1>第三方许可 / Third-party notices</h1><p>安装包包含不同许可的第三方组件。原文按实际构建环境收集，不能将所有组件描述为仅 MIT。</p>'
    page += '<p><a href="PROJECT_LICENSE.txt">Project LICENSE</a> · <a href="PROJECT_THIRD_PARTY_NOTICES.md">Distribution notes</a> · <a href="manifest.json">Manifest</a> · <a href="licenses/AGPL-3.0.txt">AGPL v3</a> · <a href="licenses/MPL-2.0.txt">MPL 2.0</a></p>'
    page += ''.join(f'<p><strong>{html.escape(key)}</strong>: {html.escape(value)}</p>' for key, value in SCOPE.items())
    page += '<table><thead><tr><th>Component / 组件</th><th>Original notices / 原始许可文本</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></html>'
    (output / "index.html").write_text(page, encoding="utf-8")


def verify_notices(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or not manifest.get("components"):
        raise ValueError("Invalid or empty notices manifest")
    files = list(manifest["documents"])
    for component in manifest["components"]:
        if not component.get("notices"):
            raise ValueError(f"Component has no notices: {component['name']}")
        files.extend(component["notices"])
    for notice in files:
        data = inside(folder / notice["path"], folder).read_bytes()
        if len(data) != notice["bytes"] or digest(data) != notice["sha256"]:
            raise ValueError(f"Missing or modified notice: {notice['path']}")
    required = {"PROJECT_LICENSE.txt", "PROJECT_THIRD_PARTY_NOTICES.md", "licenses/AGPL-3.0.txt", "licenses/MPL-2.0.txt", "python-runtime/LICENSE.txt", "electron/LICENSE.electron.txt", "electron/LICENSES.chromium.html", "index.html", "THIRD_PARTY_NOTICES.md"}
    if not required.issubset({n["path"] for n in files}):
        raise ValueError("Critical project/runtime/license files absent from manifest")
    return manifest


def collect(repo: Path, destination: Path, electron_dist: Path) -> dict:
    destination = inside(destination, repo / "desktop/release")
    if destination == (repo / "desktop/release").resolve():
        raise ValueError("Output must be a dedicated directory within desktop/release")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".legal-stage-", dir=destination.parent) as directory:
        output = Path(directory)
        canonical = canonical_notices(repo, output)
        documents = list(canonical.values())
        for name, target in (("LICENSE", "PROJECT_LICENSE.txt"), ("THIRD_PARTY_NOTICES.md", "PROJECT_THIRD_PARTY_NOTICES.md")):
            documents.append(write_notice(output, target, (repo / name).read_bytes(), f"repository:{name}"))
        python_components = python_notices(output, canonical)
        frontend_components, omitted = frontend_notices(repo, output)
        components = python_components + frontend_components + [python_runtime_notice(output), electron_notices(repo, output, electron_dist)]
        manifest = {"schema_version": 1, "app_version": json.loads((repo / "package.json").read_text(encoding="utf-8"))["version"],
                    "platform": sys.platform, "architecture": platform.machine(), "scope": SCOPE,
                    "components": components, "omitted_optional_frontend": omitted, "documents": documents}
        write_indexes(output, manifest)
        for name in ("index.html", "THIRD_PARTY_NOTICES.md"):
            data = (output / name).read_bytes()
            documents.append({"path": name, "sha256": digest(data), "bytes": len(data), "source": "generated index"})
        (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        verify_notices(output)
        if destination.exists():
            shutil.rmtree(destination)  # Resolved and contained within desktop/release above.
        shutil.copytree(output, destination)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "desktop/release/legal")
    parser.add_argument("--electron-dist", type=Path, default=ROOT / "node_modules/electron/dist")
    parser.add_argument("--verify", type=Path, help="Verify collected files after packaging without reading local configs")
    args = parser.parse_args()
    manifest = verify_notices(args.verify.resolve()) if args.verify else collect(ROOT, args.output, args.electron_dist.resolve())
    counts = {group: sum(c["ecosystem"] == group for c in manifest["components"]) for group in ("python", "frontend", "runtime")}
    print(json.dumps({"success": True, "app_version": manifest["app_version"], "counts": counts, "optional_frontend_omitted": len(manifest["omitted_optional_frontend"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
