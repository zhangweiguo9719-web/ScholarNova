"""Offline license-packaging checks: synthetic packages, no credentials or API calls."""
import importlib.util
import json
from email.message import Message
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("collect_notices", Path(__file__).with_name("collect_notices.py"))
notices = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(notices)


class FakeDistribution:
    def __init__(self, root, name, version="1.0", license_text=b"Original license text"):
        self.metadata = Message()
        self.metadata["Name"] = name
        self.metadata["License"] = "Example declaration"
        self.version = version
        self.root = root
        self.files = []
        if license_text is not None:
            filename = Path(f"{name}-{version}.dist-info/licenses/LICENSE")
            destination = root / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(license_text)
            self.files.append(filename)

    def locate_file(self, path):
        return self.root / path


class NoticeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "output"
        self.output.mkdir()

    def canonical(self):
        return {name: notices.write_notice(self.output, f"licenses/{name}", b"Full upstream license", "official:test")
                for name in ("AGPL-3.0.txt", "MPL-2.0.txt", "jiter-0.10.0-MIT.txt")}

    def required_distributions(self):
        return [FakeDistribution(self.root, "PyMuPDF", "1.26.3", b"Dual licensed; see AGPL"),
                FakeDistribution(self.root, "certifi", "2025.6.15", b"See MPL")]

    def package(self, name, version="1.0.0", license_text=b"Original MIT license", relative=None):
        relative = relative or f"node_modules/{name}"
        package = self.root / "frontend" / relative
        package.mkdir(parents=True)
        (package / "package.json").write_text(json.dumps({"name": name, "version": version, "license": "MIT"}))
        if license_text is not None:
            (package / "LICENSE").write_bytes(license_text)
        return relative, package

    def lock(self, entries):
        frontend = self.root / "frontend"
        frontend.mkdir(exist_ok=True)
        (frontend / "package-lock.json").write_text(json.dumps({"packages": {"": {"name": "app"}, **entries}}))

    def test_supplement_preserves_original_python_notices(self):
        distributions = self.required_distributions() + [FakeDistribution(self.root, "jiter", "0.10.0", None)]
        result = notices.python_notices(self.output, self.canonical(), distributions)
        mapping = {c["name"]: c for c in result}
        self.assertEqual(len(mapping["PyMuPDF"]["notices"]), 2)
        self.assertTrue(any(n["path"] == "licenses/AGPL-3.0.txt" for n in mapping["PyMuPDF"]["notices"]))
        original = next(n for n in mapping["PyMuPDF"]["notices"] if n["path"].startswith("python/"))
        self.assertEqual((self.output / original["path"]).read_bytes(), b"Dual licensed; see AGPL")
        self.assertEqual(mapping["jiter"]["notices"][0]["path"], "licenses/jiter-0.10.0-MIT.txt")

    def test_missing_python_notice_fails_and_fallback_is_version_pinned(self):
        for name, version in (("unknown", "1.0"), ("jiter", "0.11.0")):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Missing license text"):
                notices.python_notices(self.output, self.canonical(), self.required_distributions() + [FakeDistribution(self.root, name, version, None)])

    def test_wrong_build_interpreter_fails(self):
        with self.assertRaisesRegex(ValueError, "required PyMuPDF/certifi"):
            notices.python_notices(self.output, {}, [FakeDistribution(self.root, "ordinary")])

    def test_full_official_texts_are_hash_pinned(self):
        repo = notices.ROOT
        canonical = notices.canonical_notices(repo, self.output)
        self.assertGreater(canonical["AGPL-3.0.txt"]["bytes"], 30000)
        self.assertGreater(canonical["MPL-2.0.txt"]["bytes"], 15000)
        fake_repo = self.root / "repo"
        (fake_repo / "LICENSES").mkdir(parents=True)
        (fake_repo / "LICENSES/bad.txt").write_bytes(b"truncated")
        (fake_repo / "LICENSES/sources.json").write_text(json.dumps({"bad.txt": {"sha256": "0" * 64, "url": "official:test"}}))
        with self.assertRaisesRegex(ValueError, "changed or is incomplete"):
            notices.canonical_notices(fake_repo, self.output)

    def test_frontend_prod_transitive_tree_and_optional_omissions(self):
        direct, _ = self.package("direct")
        transitive, _ = self.package("child", relative="node_modules/direct/node_modules/child")
        self.lock({direct: {"version": "1.0.0"}, transitive: {"version": "1.0.0"},
                   "node_modules/dev-tool": {"version": "1.0.0", "dev": True},
                   "node_modules/other-platform": {"version": "1.0.0", "optional": True}})
        components, omitted = notices.frontend_notices(self.root, self.output)
        self.assertEqual({c["name"] for c in components}, {"direct", "child"})
        self.assertEqual(len(omitted), 1)
        self.assertEqual(len(next(c for c in components if c["name"] == "direct")["notices"]), 1)

    def test_frontend_missing_nonoptional_or_mismatched_version_fails(self):
        self.lock({"node_modules/missing": {"version": "1.0.0"}})
        with self.assertRaisesRegex(ValueError, "not installed"):
            notices.frontend_notices(self.root, self.output)
        relative, _ = self.package("present")
        self.lock({relative: {"version": "2.0.0"}})
        with self.assertRaisesRegex(ValueError, "version mismatch"):
            notices.frontend_notices(self.root, self.output)

    def test_full_readme_license_accepted_but_link_only_is_not(self):
        relative, package = self.package("readme-only", license_text=None)
        self.lock({relative: {"version": "1.0.0"}})
        (package / "README.md").write_text("License: MIT. See upstream website.")
        with self.assertRaisesRegex(ValueError, "Missing license text"):
            notices.frontend_notices(self.root, self.output)
        data = b"Readme intro\nPermission is hereby granted to use the Software. THE SOFTWARE IS PROVIDED AS IS.\n"
        (package / "README.md").write_bytes(data)
        components, _ = notices.frontend_notices(self.root, self.output)
        copied = self.output / components[0]["notices"][0]["path"]
        self.assertEqual(copied.read_bytes(), data)

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, "escapes"):
            notices.write_notice(self.output, "../private.txt", b"text", "test")
        self.lock({"../outside": {"version": "1.0.0"}})
        with self.assertRaisesRegex(ValueError, "escapes"):
            notices.frontend_notices(self.root, self.output)

    def test_html_escapes_dependency_metadata(self):
        manifest = {"components": [{"ecosystem": "frontend", "name": "<script>alert(1)</script>", "version": "1.0", "notices": [{"path": "folder/LICENSE.txt"}]}]}
        notices.write_indexes(self.output, manifest)
        page = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", page)
        self.assertIn("AGPL", page)

    def test_verify_detects_tampering_and_missing_critical_document(self):
        required = ("PROJECT_LICENSE.txt", "PROJECT_THIRD_PARTY_NOTICES.md", "licenses/AGPL-3.0.txt", "licenses/MPL-2.0.txt", "python-runtime/LICENSE.txt", "electron/LICENSE.electron.txt", "electron/LICENSES.chromium.html", "index.html", "THIRD_PARTY_NOTICES.md")
        documents = [notices.write_notice(self.output, path, f"original {path}".encode(), "test") for path in required]
        manifest = {"schema_version": 1, "documents": documents, "components": [{"name": "example", "notices": [documents[0]]}]}
        manifest_file = self.output / "manifest.json"
        manifest_file.write_text(json.dumps(manifest))
        notices.verify_notices(self.output)
        (self.output / "PROJECT_LICENSE.txt").write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "modified notice"):
            notices.verify_notices(self.output)
        (self.output / "PROJECT_LICENSE.txt").write_bytes(b"original PROJECT_LICENSE.txt")
        manifest["documents"] = documents[:-1]
        manifest_file.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "Critical"):
            notices.verify_notices(self.output)


if __name__ == "__main__":
    unittest.main()
