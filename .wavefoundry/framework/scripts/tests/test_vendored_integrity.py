"""The shipped offline vendored-script check and its wf_audit finding (wave 1zyb2, change 1zxnt).

Every assertion here is about the contract visible through the function: a listed file that
matches, differs, or is missing. Nothing opens a network connection: the audit tests patch
``urllib.request.urlopen``, ``socket.create_connection`` and ``socket.socket.connect`` to raise
and assert none of them was reached.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import shutil
import socket
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import vendored_integrity as vi  # noqa: E402

REAL_VENDOR = SCRIPTS_ROOT.parent / "dashboard" / "vendor"
CONTENT = b"/* demo bundle */\nconsole.log(1);\n"
# Shipped leaf modules the moved code may import besides the standard library.
ALLOWED_FRAMEWORK_IMPORTS = frozenset({"path_containment"})


def _readme(sha256: str) -> str:
    return (
        "# Vendored\n\n"
        "| File | Package | Source in the tarball | Licence | SHA-256 |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"| `demo/demo.js` | `demo@1.0.0` | `package/dist/demo.js` | MIT (`demo/LICENSE`) | `{sha256}` |\n\n"
        "## Registry integrity\n\n"
        "| Package | Tarball | `dist.integrity` |\n"
        "| --- | --- | --- |\n"
        "| `demo@1.0.0` | `https://registry.npmjs.org/demo/-/demo-1.0.0.tgz` | `sha512-AAAA` |\n"
    )


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            names.add((node.module or "").split(".")[0])
    return names


class RelocationTests(unittest.TestCase):
    """AC-9b and AC-12."""

    def setUp(self) -> None:
        self.vendor = Path(tempfile.mkdtemp(prefix="wf-vi-"))
        self.addCleanup(shutil.rmtree, self.vendor, ignore_errors=True)
        (self.vendor / "demo").mkdir()
        (self.vendor / "demo" / "demo.js").write_bytes(CONTENT)
        (self.vendor / "README.md").write_text(_readme(hashlib.sha256(CONTENT).hexdigest()), encoding="utf-8")

    def test_matching_file_has_no_problem(self):
        self.assertEqual(vi.offline_problems(self.vendor), [])

    def test_differing_file_is_named(self):
        (self.vendor / "demo" / "demo.js").write_bytes(CONTENT + b"x")
        problems = vi.offline_problems(self.vendor)
        self.assertEqual(len(problems), 1, problems)
        self.assertTrue(problems[0].startswith("demo/demo.js: "), problems)

    def test_missing_file_is_named(self):
        (self.vendor / "demo" / "demo.js").unlink()
        problems = vi.offline_problems(self.vendor)
        self.assertEqual(len(problems), 1, problems)
        self.assertTrue(problems[0].startswith("demo/demo.js: "), problems)

    def test_unparsable_readme_raises_readme_error(self):
        (self.vendor / "README.md").write_text("# nothing here\n", encoding="utf-8")
        with self.assertRaises(vi.ReadmeError):
            vi.offline_problems(self.vendor)

    def test_real_vendor_folder_matches(self):
        self.assertEqual(vi.offline_problems(REAL_VENDOR), [])

    def test_imports_only_stdlib_and_allowlisted_leaf_modules(self):
        names = _imports(SCRIPTS_ROOT / "vendored_integrity.py") - {"__future__"}
        self.assertTrue(names)
        extra = sorted(n for n in names if n not in sys.stdlib_module_names and n not in ALLOWED_FRAMEWORK_IMPORTS)
        self.assertEqual(extra, [])

    def test_shipped_not_excluded_and_listed(self):
        import build_pack
        import mcp_tool_extensions

        self.assertNotIn("scripts/vendored_integrity.py", build_pack.EXCLUDED_REL_PATHS)
        self.assertIs(build_pack.should_exclude("scripts/vendored_integrity.py", "vendored_integrity.py"), False)
        self.assertIs(build_pack.should_exclude("scripts/verify_vendored_scripts.py", "verify_vendored_scripts.py"), True)
        self.assertIn("vendored_integrity", mcp_tool_extensions.FRAMEWORK_SCRIPT_MODULE_NAMES)

    def test_one_definition_each(self):
        patterns = ("def offline_problems", "def read_vendored_file", "def _read_regular",
                    "def parse_readme", "MAX_VENDORED_FILE_BYTES =")
        for pattern in patterns:
            hits = [
                path.relative_to(SCRIPTS_ROOT).as_posix()
                for path in sorted(SCRIPTS_ROOT.rglob("*.py"))
                if path.relative_to(SCRIPTS_ROOT).parts[0] != "tests"
                and any(line.lstrip().startswith(pattern) for line in path.read_text(encoding="utf-8").splitlines())
            ]
            self.assertEqual(hits, ["vendored_integrity.py"], pattern)

    def test_the_network_verifier_reexports_the_shipped_names(self):
        import verify_vendored_scripts as vvs

        for name in ("parse_readme", "offline_problems", "ReadmeError", "VendoredFile", "RegistryEntry",
                     "read_vendored_file", "_read_regular", "VendoredFileRefused"):
            self.assertIs(getattr(vvs, name), getattr(vi, name), name)
        self.assertTrue(callable(vvs.verify))


class AuditVendoredScriptsTests(unittest.TestCase):
    """AC-9, AC-10, AC-11 (no handler change) and AC-12."""

    @classmethod
    def setUpClass(cls):
        from server_tools_support import load_server

        cls.srv = load_server()

    def setUp(self) -> None:
        from server_tools_support import _make_repo

        self.tmp = Path(tempfile.mkdtemp(prefix="wf-vi-audit-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = _make_repo(self.tmp / "target")
        self.vendor = self.root / ".wavefoundry" / "framework" / "dashboard" / "vendor"
        # The audited root is not where the server's scripts live.
        self.assertFalse(Path(self.srv.SCRIPTS_DIR).resolve().is_relative_to(self.root.resolve()))

    def _copy_real_vendor(self) -> None:
        shutil.copytree(REAL_VENDOR, self.vendor)

    def _audit(self, load_script=None):
        def no_network(*args, **kwargs):
            raise AssertionError("network opened by wf_audit")

        wave = {"id": "w1", "status": "active", "changes": [], "title": "Wave", "path": ""}
        healthy = {"metadata_ready": True, "readiness_overview": "ready", "freshness": "unknown",
                   "freshness_checked": False, "freshness_verification_tool": "index_health"}
        with contextlib.ExitStack() as stack:
            urlopen = stack.enter_context(mock.patch.object(urllib.request, "urlopen", side_effect=no_network))
            create = stack.enter_context(mock.patch.object(socket, "create_connection", side_effect=no_network))
            connect = stack.enter_context(mock.patch.object(socket.socket, "connect", side_effect=no_network))
            stack.enter_context(mock.patch.object(self.srv, "current_wave", return_value=wave))
            stack.enter_context(mock.patch.object(
                self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}))
            stack.enter_context(mock.patch.object(self.srv, "_audit_index_snapshot", return_value=healthy))
            if load_script is not None:
                stack.enter_context(mock.patch.object(self.srv, "_load_script", side_effect=load_script))
            result = self.srv.wf_audit_response(self.root)
        self.assertFalse(urlopen.called or create.called or connect.called)
        return result

    @staticmethod
    def _codes(result) -> list[str]:
        return [d["code"] for d in result.get("diagnostics", []) if d["code"].startswith("vendored_scripts")]

    def test_five_outcomes_and_ready_is_unchanged(self):
        readies = {}

        self._copy_real_vendor()
        ok = self._audit()
        self.assertEqual(ok["data"]["vendored_scripts"]["status"], "ok")
        self.assertEqual(self._codes(ok), [])
        readies["ok"] = ok["data"]["ready"]

        target = self.vendor / "react" / "react.production.min.js"
        data = bytearray(target.read_bytes())
        data[100] ^= 0x01
        target.write_bytes(bytes(data))
        mismatch = self._audit()
        block = mismatch["data"]["vendored_scripts"]
        self.assertEqual(block["status"], "mismatch")
        self.assertEqual(len(block["problems"]), 1, block)
        self.assertTrue(block["problems"][0].startswith("react/react.production.min.js: "), block)
        self.assertEqual(self._codes(mismatch), ["vendored_scripts_mismatch"])
        [diagnostic] = [d for d in mismatch["diagnostics"] if d["code"] == "vendored_scripts_mismatch"]
        message = diagnostic["message"]
        for forbidden in (".py", ".js", "python", "verify_vendored", str(self.tmp), str(self.root)):
            self.assertNotIn(forbidden, message)
        readies["mismatch"] = mismatch["data"]["ready"]

        def no_module(name, _real=self.srv._load_script):
            if name == "vendored_integrity":
                raise ImportError("not importable")
            return _real(name)

        unimportable = self._audit(load_script=no_module)
        self.assertEqual(unimportable["data"]["vendored_scripts"]["status"], "unavailable")
        self.assertEqual(self._codes(unimportable), [])
        readies["unimportable"] = unimportable["data"]["ready"]

        (self.vendor / "README.md").write_text("# not a table\n", encoding="utf-8")
        unreadable = self._audit()
        self.assertEqual(unreadable["data"]["vendored_scripts"]["status"], "unreadable")
        self.assertEqual(self._codes(unreadable), ["vendored_scripts_unreadable"])
        [diagnostic] = [d for d in unreadable["diagnostics"] if d["code"] == "vendored_scripts_unreadable"]
        for forbidden in (".py", ".js", "python", "verify_vendored", str(self.tmp), str(self.root)):
            self.assertNotIn(forbidden, diagnostic["message"])
        readies["unreadable"] = unreadable["data"]["ready"]

        # A malformed row is reported by line number and cause only: no raw row text,
        # control characters included, reaches the audit data.
        row = "| `demo/\x1b[2Jrow-text.js` | broken \x07 SECRET-ROW-TEXT |"
        (self.vendor / "README.md").write_text(
            "# Vendored\n\n| File | Package | Source in the tarball | Licence | SHA-256 |\n"
            "| --- | --- | --- | --- | --- |\n" + row + "\n", encoding="utf-8")
        malformed = self._audit()
        block = malformed["data"]["vendored_scripts"]
        self.assertEqual(block["status"], "unreadable")
        self.assertEqual(block["reason"], "line 5: malformed file table row")
        for fragment in ("SECRET-ROW-TEXT", "row-text.js", "\x1b", "\x07", "broken"):
            self.assertNotIn(fragment, block["reason"])
        readies["malformed"] = malformed["data"]["ready"]

        shutil.rmtree(self.vendor)
        absent = self._audit()
        self.assertEqual(absent["data"]["vendored_scripts"]["status"], "unavailable")
        self.assertEqual(self._codes(absent), [])
        readies["absent"] = absent["data"]["ready"]

        self.assertEqual(len(set(readies.values())), 1, readies)

    def test_the_audit_reads_the_audited_roots_vendor_folder(self):
        # The audited root's folder differs from the server's own (real) one.
        (self.vendor / "demo").mkdir(parents=True)
        (self.vendor / "demo" / "demo.js").write_bytes(CONTENT)
        (self.vendor / "README.md").write_text(_readme("0" * 64), encoding="utf-8")
        result = self._audit()
        block = result["data"]["vendored_scripts"]
        self.assertEqual(block["status"], "mismatch")
        self.assertTrue(block["problems"][0].startswith("demo/demo.js: "), block)

    def test_the_audit_helper_is_ok_for_this_repository(self):
        repo_root = SCRIPTS_ROOT.parents[2]
        self.assertEqual(self.srv._audit_vendored_scripts(repo_root), {"status": "ok", "problems": []})



def _two_table_readme(package: str = "demo@1.0.0", source: str = "package/dist/demo.js",
                      url: str = "https://registry.npmjs.org/demo/-/demo-1.0.0.tgz",
                      path: str = "demo/demo.js", registry_package: str | None = None,
                      extra_registry: str = "") -> str:
    reg = package if registry_package is None else registry_package
    return (
        "# Vendored\n\n"
        "| File | Package | Source in the tarball | Licence | SHA-256 |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"| `{path}` | `{package}` | `{source}` | MIT (`demo/LICENSE`) | `{'a' * 64}` |\n\n"
        "## Registry integrity\n\n"
        "| Package | Tarball | `dist.integrity` |\n"
        "| --- | --- | --- |\n"
        f"| `{reg}` | `{url}` | `sha512-AAAA` |\n"
        f"{extra_registry}"
    )


# One of each class Requirement 6 names: a C0 control, a C1 control, and three
# category ``Cf`` characters (a bidirectional override, a bidirectional
# isolate and a zero-width joiner).
_UNSAFE_SAMPLES = {
    "C0": "\x1b",
    "DEL": "\x7f",
    "C1": "\x9b",
    "Cf bidirectional override": "‮",
    "Cf bidirectional isolate": "⁦",
    "Cf zero-width": "‍",
}


class ReadmeFieldCheckTests(unittest.TestCase):
    """Wave 200xy, change 200v1 (AC-7, AC-9): README fields with control or
    format characters are refused by row and field, never echoed."""

    def _refused(self, text: str) -> str:
        with self.assertRaises(vi.ReadmeError) as ctx:
            vi.parse_readme(text)
        return str(ctx.exception)

    def test_every_field_refuses_every_unsafe_class_without_echo(self):
        marker = "FIELDTEXT"
        for label, ch in _UNSAFE_SAMPLES.items():
            cases = {
                ("file", "package"): _two_table_readme(package=f"{marker}{ch}x@1.0.0",
                                                       registry_package="demo@1.0.0"),
                ("file", "source"): _two_table_readme(source=f"package/{marker}{ch}.js"),
                ("registry", "package"): _two_table_readme(registry_package=f"{marker}{ch}x@1.0.0",
                                                           package="demo@1.0.0"),
                ("registry", "url"): _two_table_readme(
                    url=f"https://registry.npmjs.org/{marker}{ch}.tgz"),
            }
            for (table, field), text in cases.items():
                with self.subTest(cls=label, table=table, field=field):
                    message = self._refused(text)
                    self.assertEqual(
                        message, f"{table} row 1: {field} contains a control or format character")
                    self.assertNotIn(marker, message)
                    self.assertNotIn(ch, message)

    def test_a_clean_readme_still_parses(self):
        files, registry = vi.parse_readme(_two_table_readme())
        self.assertEqual([f.package for f in files], ["demo@1.0.0"])
        self.assertEqual(list(registry), ["demo@1.0.0"])

    def test_row_path_problem_refuses_each_format_class(self):
        for label, ch in _UNSAFE_SAMPLES.items():
            with self.subTest(cls=label):
                self.assertEqual(vi._row_path_problem(f"demo/de{ch}mo.js"),
                                 "path contains a control character")

    def test_offline_problems_labels_a_format_character_path_by_row(self):
        vendor = Path(tempfile.mkdtemp(prefix="wf-vi-cf-"))
        self.addCleanup(shutil.rmtree, vendor, ignore_errors=True)
        for label in ("Cf bidirectional override", "Cf zero-width"):
            ch = _UNSAFE_SAMPLES[label]
            with self.subTest(cls=label):
                (vendor / "README.md").write_text(
                    _two_table_readme(path=f"demo/PATHTEXT{ch}.js"), encoding="utf-8")
                problems = vi.offline_problems(vendor)
                self.assertEqual(len(problems), 1, problems)
                self.assertTrue(problems[0].startswith("row 1: "), problems)
                self.assertNotIn("PATHTEXT", problems[0])
                self.assertNotIn(ch, problems[0])


class RegistryMessagePinTests(unittest.TestCase):
    """Wave 200xy, change 200v1 (AC-9, Requirement 8): the two registry
    messages are pinned exactly and never carry the package value."""

    def test_duplicate_package_message_is_exact(self):
        package = "PKGVALUE@1.0.0"
        text = _two_table_readme(
            package=package,
            extra_registry=f"| `{package}` | `https://registry.npmjs.org/x.tgz` | `sha512-BBBB` |\n")
        with self.assertRaises(vi.ReadmeError) as ctx:
            vi.parse_readme(text)
        self.assertEqual(str(ctx.exception), "registry row 2: duplicate package")
        self.assertNotIn("PKGVALUE", str(ctx.exception))

    def test_missing_registry_row_message_is_exact(self):
        text = _two_table_readme(package="PKGVALUE@1.0.0", registry_package="other@1.0.0")
        with self.assertRaises(vi.ReadmeError) as ctx:
            vi.parse_readme(text)
        self.assertEqual(str(ctx.exception), "row 1: package has no registry row")
        self.assertNotIn("PKGVALUE", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
