"""Source-release safety tests; no downloads, credentials or repository writes."""
import hashlib
import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "source_builder", Path(__file__).with_name("build_corresponding_source.py"),
)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class SourceReleaseTests(unittest.TestCase):
    def test_corrupt_cached_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp)
            (cache / "source.tar.gz").write_bytes(b"changed")
            artifact = {"filename": "source.tar.gz", "size": 7, "sha256": "0" * 64}
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                builder.fetch_source(artifact, cache, offline=True)

    def test_offline_missing_source_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "Offline source missing"):
                builder.fetch_source({"filename": "missing.tar.gz"}, Path(temp), offline=True)

    def test_snapshot_without_mupdf_core_c_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "incomplete.tar.gz"
            with tarfile.open(path, "w:gz") as archive:
                member = tarfile.TarInfo("mupdf/COPYING")
                member.size = 4
                archive.addfile(member, io.BytesIO(b"AGPL"))
            with self.assertRaisesRegex(ValueError, "core C source"):
                builder.inspect_source(path, {"name": "MuPDF"})

    def test_tracked_private_configuration_is_rejected(self):
        for name in [".env", ".env.local", ".env.production", "production.env",
                     "backend/model_config.json", "backend/private.db", ".git/config"]:
            with self.subTest(name=name), io.BytesIO() as buffer:
                with zipfile.ZipFile(buffer, "w") as archive:
                    archive.writestr("project/" + name, "fake")
                    with self.assertRaisesRegex(ValueError, "private|credential|database"):
                        builder.verify_project_archive(archive)

    def test_runtime_version_mismatch_fails_closed(self):
        lock = {"artifacts": [{"name": "MuPDF", "version": "1.26.3"}]}
        with patch.object(builder.subprocess, "check_output", return_value=b'{"MuPDF":"1.27.0"}'):
            with self.assertRaisesRegex(ValueError, "Runtime/source version mismatch: MuPDF"):
                builder.check_runtime(lock, "python")

    def test_check_runtime_only_never_downloads_or_archives(self):
        with patch.object(builder.sys, "argv", ["builder", "--check-runtime-only"]), \
             patch.object(builder, "check_runtime", return_value={"MuPDF": "1.26.3"}) as check, \
             patch.object(builder, "fetch_source") as download, \
             patch.object(builder, "git") as git:
            builder.main()
        check.assert_called_once()
        download.assert_not_called()
        git.assert_not_called()

    def test_unknown_missing_nested_submodule_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "incomplete.tar.gz"
            contents = {"mupdf/COPYING": b"AGPL", "mupdf/source/fitz/document.c": b"source",
                        "mupdf/thirdparty/dep0/.gitmodules": b'[submodule "missing"]\npath=missing\nurl=https://example.org/repo.git\n'}
            contents.update({f"mupdf/thirdparty/dep{dep}/file{num}.c": b""
                             for dep in range(10) for num in range(100)})
            with tarfile.open(path, "w:gz") as archive:
                for name, data in contents.items():
                    member = tarfile.TarInfo(name)
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
            with self.assertRaisesRegex(ValueError, "Undocumented missing MuPDF submodule"):
                builder.inspect_source(path, {"name": "MuPDF"})
            omitted = {"path": "thirdparty/dep0/missing", "commit": "a" * 40}
            result = builder.inspect_source(path, {"name": "MuPDF", "omitted_nested_submodules": [omitted]})
            self.assertEqual(result["omitted_nested_submodules"], [omitted])

    def test_bundle_only_uses_commit_archive_and_hashes_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work / ".env").write_text("untracked-private-placeholder")
            commit = "a" * 40
            source = work / "cache" / "certifi-1.tar.gz"
            source.parent.mkdir()
            with tarfile.open(source, "w:gz") as archive:
                member = tarfile.TarInfo("certifi-1/LICENSE")
                member.size = 3
                archive.addfile(member, io.BytesIO(b"MPL"))
            lock = {"artifacts": [{"name": "certifi", "version": "1", "filename": source.name,
                                   "size": source.stat().st_size, "sha256": builder.digest(source)}]}

            def fake_git(*args):
                if args[0] == "rev-parse":
                    return commit.encode()
                if args[0] == "show":
                    name = args[1].split(":", 1)[1]
                    if name == "package.json":
                        return b'{"version":"1.2.3"}'
                    if name == "requirements-lock.txt":
                        return b"certifi==1\n"
                    return json.dumps(lock).encode()
                self.assertEqual(args[0], "archive")
                output = next(arg.split("=", 1)[1] for arg in args if arg.startswith("--output="))
                with zipfile.ZipFile(output, "w") as archive:
                    for name in ["LICENSE", "THIRD_PARTY_NOTICES.md", "LICENSES/AGPL-3.0.txt",
                                 "requirements-lock.txt", "package-lock.json", "frontend/package-lock.json",
                                 "scripts/packaging/ScholarNovaBackend.spec", builder.LOCK_PATH,
                                 ".env.example", "backend.env.example"]:
                        archive.writestr("project/" + name, "committed")
                return b""

            with patch.object(builder, "git", side_effect=fake_git):
                output = builder.build_bundle("release", work / "out", source.parent, True, None)
            with zipfile.ZipFile(output) as archive:
                self.assertNotIn("project/.env", archive.namelist())
                self.assertIn("project/.env.example", archive.namelist())
                manifest = json.loads(archive.read("SOURCE_MANIFEST.json"))
                self.assertEqual(manifest["git_commit"], commit)
                for name, sha in manifest["payload_files"].items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), sha)
                sums = archive.read("SHA256SUMS").decode()
                self.assertIn("SOURCE_MANIFEST.json", sums)
                self.assertIn("upstream/certifi-1.tar.gz", sums)


if __name__ == "__main__":
    unittest.main()
