"""Profile-portable test infrastructure (wave 1zim5, change 1zim1).

* AC-1: the builders and the localized docs-lint fixture lint clean under the
  shipped default profile and under the shared second profile, including the
  archive in the default vocabulary; an unlocalized fixture does not.
* AC-2: the default-profile-only marker runs its test when the loaded
  constants match the frozen shipped defaults and skips it otherwise,
  including when ``vocabulary_profile`` itself was edited on disk.
* AC-3: the second-profile run copies the listed tree into a temporary git
  repository, applies the asset, runs the copy's runner as a focused run,
  reports per file, and leaves this tree's receipt byte-identical.
* The shared apply function: exactly-once replacement and import validation.
* Change 1zima: the expected profile (the active asset, else the shipped
  defaults, with the run-mode asset named by ``WAVEFOUNDRY_TEST_PROFILE`` over
  it) and the exact guards against it, in scratch trees; a receipt-writing
  run refuses while the variable is set.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import record_layout_support
import record_paths
import vocabulary_profile
from record_layout_support import (
    PROFILES_DIR,
    SHIPPED_DECLARATION,
    SHIPPED_DEFAULTS,
    TEST_PROFILE_ENV,
    ProfileInvalid,
    apply_profile,
    copy_scripts_tree,
    default_profile_only,
    expected_profile,
    expected_profile_mismatch,
    load_profile,
    localize_record_text,
    localized_docs_lint_fixture,
    profile_differences,
    shipped_default_profile,
    waves_dir,
    waves_rel,
)

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
# The shipped vocabulary as an archive profile: equal in value to the live
# names, but still a difference from the shipped ``ARCHIVE_PROFILE = None``.
SHIPPED_VOCABULARY = {k: v for k, v in SHIPPED_DEFAULTS["vocabulary_profile"].items()
                      if k not in ("ARCHIVE_PROFILE", "EXTRA_CHANGE_KINDS")}

_spec = importlib.util.spec_from_file_location("run_tests", SCRIPTS_DIR / "run_tests.py")
run_tests = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_tests)

# The framework's own profile assets (change 1zima): copied into a temporary
# directory, so a test that resolves the expected profile from them holds
# whatever asset a distribution marks active beside them.
FRAMEWORK_ASSETS = ("second", "declared")
# The second profile's live vocabulary, read from its asset.
SECOND_VOCABULARY = load_profile("second")["modules"]["vocabulary_profile"]


@contextlib.contextmanager
def framework_profiles(**extra: dict):
    """A temporary profiles directory holding the framework's own assets plus
    ``extra`` (``name=asset``), for the resolver's ``profiles_dir``."""
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        for name in FRAMEWORK_ASSETS:
            shutil.copy2(PROFILES_DIR / f"{name}.json", directory / f"{name}.json")
        for name, asset in extra.items():
            (directory / f"{name}.json").write_text(json.dumps(asset), encoding="utf-8")
        yield directory


def _driver(code: str, *args: str) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-B", "-c", code, *args], env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False, timeout=300,
    )
    if result.returncode != 0:
        raise AssertionError(f"driver failed ({result.returncode}):\n{result.stderr[-4000:]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


# Runs in a fresh interpreter over a copied scripts tree with a profile applied.
BUILDER_DRIVER = r'''
import json, os, shutil, subprocess, sys
from pathlib import Path
scripts, base = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(scripts / "tests"))
sys.path.insert(0, str(scripts))
import record_layout_support as s, record_paths, vocabulary_profile

def lint(root):
    env = dict(os.environ, PROJECT_ROOT=str(root), PYTHONPATH=str(scripts))
    run = subprocess.run([sys.executable, "-B", str(scripts / "docs_lint.py")],
                         env=env, text=True, capture_output=True, check=False)
    return run.returncode, (run.stdout + run.stderr)[-3000:]

def rel(root, paths):
    return sorted("/".join(p.relative_to(root).parts) for p in paths)

out = {}
localized = s.localized_docs_lint_fixture(base / "localized")
out["localized_rc"], out["localized_out"] = lint(localized)
raw = base / "raw"
shutil.copytree(s.DOCS_LINT_FIXTURE, raw)
out["raw_rc"], out["raw_out"] = lint(raw)

built = s.localized_docs_lint_fixture(base / "built")
b = s.RecordTreeBuilder(built)
group = "2026" if record_paths.NESTED else ""
folder = b.container("00070 built-wave", "00070 built-wave", group=group, members=[
    ("00071-enh built-member", "complete"),
    ("00072-bug built-other", "planned", "00071-enh built-member"),
])
plan = b.plan("00073-enh built-plan")
archived = None
if b.archive_dir is not None:
    archived = b.container("00060 archived-wave", "00060 archived-wave", status="completed",
                           archive=True, members=[("00061-enh archived-member", "complete")])
out["built_rc"], out["built_out"] = lint(built)
out["live"] = rel(built, record_paths.discover_wave_dirs(built))
out["archive"] = rel(built, record_paths.discover_archive_dirs(built))
out["record_files"] = sorted(p.name for p in folder.iterdir())
out["record_text"] = (folder / vocabulary_profile.RECORD_FILENAME).read_text(encoding="utf-8")
out["member_text"] = (folder / "00071-enh built-member.md").read_text(encoding="utf-8")
out["plan_text"] = plan.read_text(encoding="utf-8")
out["readme"] = (b.waves_dir / "README.md").is_file()
if archived is not None:
    out["archive_files"] = sorted(p.name for p in archived.iterdir())
    out["archive_text"] = (archived / "wave.md").read_text(encoding="utf-8")
    out["archive_member_text"] = (archived / "00061-enh archived-member.md").read_text(encoding="utf-8")
print(json.dumps(out))
'''


class BuilderLintTests(unittest.TestCase):
    """AC-1: builders and the localized fixture under both profiles."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        cls.runs = {}
        for name, profile in (("default", shipped_default_profile()), ("second", load_profile("second"))):
            scripts = copy_scripts_tree(base / name / "tree")
            apply_profile(scripts, profile)
            work = base / name / "work"
            work.mkdir()
            cls.runs[name] = _driver(BUILDER_DRIVER, str(scripts), str(work))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_builders_lint_clean_under_both_profiles(self) -> None:
        for name, run in self.runs.items():
            with self.subTest(profile=name):
                self.assertEqual(run["built_rc"], 0, run["built_out"])
                self.assertTrue(run["readme"])

    def test_localized_fixture_lints_clean_and_the_raw_one_does_not_under_the_second_profile(self) -> None:
        second = self.runs["second"]
        self.assertEqual(second["localized_rc"], 0, second["localized_out"])
        self.assertNotEqual(second["raw_rc"], 0)
        # Under the default profile localization is the identity.
        self.assertEqual(self.runs["default"]["localized_rc"], 0, self.runs["default"]["localized_out"])
        self.assertEqual(self.runs["default"]["raw_rc"], 0, self.runs["default"]["raw_out"])

    def test_second_profile_records_follow_the_profile(self) -> None:
        run = self.runs["second"]
        v = SECOND_VOCABULARY
        root = load_profile("second")["modules"]["record_paths"]["WAVES_ROOT"]
        self.assertEqual(run["live"], [f"{root}/2026/00070 built-wave", f"{root}/change-2026-03"])
        self.assertIn(v["RECORD_FILENAME"], run["record_files"])
        self.assertNotIn("wave.md", run["record_files"])
        self.assertIn(f"{v['ID_KEY']}: `00070 built-wave`", run["record_text"])
        self.assertIn(f"{v['MEMBER_HEADING']}\n", run["record_text"])
        self.assertIn(f"{v['MEMBER_ID_LABEL']}: `00071-enh built-member`", run["record_text"])
        self.assertIn(f"{v['MEMBER_STATUS_LABEL']}: `complete`", run["record_text"])
        self.assertIn(f"{v['MEMBER_ID_LABEL']}: `00071-enh built-member`", run["member_text"])
        self.assertIn(f"{v['BACKREF_LABEL']}: 00070 built-wave", run["member_text"])
        self.assertIn(f"{v['BACKREF_LABEL']}: TBD", run["plan_text"])
        self.assertNotIn("Change ID", run["record_text"] + run["member_text"] + run["plan_text"])

    def test_second_profile_archive_is_in_the_default_vocabulary(self) -> None:
        run = self.runs["second"]
        self.assertEqual(run["archive"], ["docs/waves/00060 archived-wave"])
        self.assertIn("wave.md", run["archive_files"])
        self.assertIn("wave-id: `00060 archived-wave`", run["archive_text"])
        self.assertIn("Change ID: `00061-enh archived-member`", run["archive_text"])
        self.assertIn("Change ID: `00061-enh archived-member`", run["archive_member_text"])
        self.assertIn("Wave: 00060 archived-wave", run["archive_member_text"])

    def test_default_profile_records_follow_the_shipped_names(self) -> None:
        run = self.runs["default"]
        self.assertEqual(run["live"], ["docs/waves/00070 built-wave", "docs/waves/change-2026-03"])
        self.assertIn("wave.md", run["record_files"])
        self.assertIn("Change ID: `00071-enh built-member`", run["record_text"])
        self.assertEqual(run["archive"], [])


# Runs a marked test in a fresh interpreter over a copied scripts tree.
MARKER_DRIVER = r'''
import io, json, sys, unittest
sys.path.insert(0, sys.argv[1] + "/tests")
sys.path.insert(0, sys.argv[1])
from record_layout_support import default_profile_only, profile_differences
ran = []

class Marked(unittest.TestCase):
    @default_profile_only("the subject is the shipped default profile")
    def test_marked(self):
        ran.append("marked")

result = unittest.TextTestRunner(stream=io.StringIO()).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(Marked))
print(json.dumps({"ran": ran, "skipped": [reason for _test, reason in result.skipped],
                  "differ": profile_differences()}))
'''


class DefaultProfileOnlyMarkerTests(unittest.TestCase):
    """AC-2: the verdict comes from the frozen snapshot of shipped defaults."""

    def _run_marked(self, target) -> unittest.TestResult:
        return unittest.TextTestRunner(stream=io.StringIO()).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(target))

    @contextlib.contextmanager
    def _loaded(self, **overrides):
        """Every loaded copy of both modules set to the shipped defaults, with
        ``overrides`` (``module__NAME=value``) on top."""
        with contextlib.ExitStack() as stack:
            for module_name, defaults in SHIPPED_DEFAULTS.items():
                values = dict(defaults)
                for key, value in overrides.items():
                    owner, name = key.split("__", 1)
                    if owner == module_name:
                        values[name] = value
                for key, module in list(sys.modules.items()):
                    if module is not None and (key == module_name or key.endswith("." + module_name)):
                        for name, value in values.items():
                            stack.enter_context(mock.patch.object(module, name, value))
            yield

    def _method_case(self, ran: list):
        class Marked(unittest.TestCase):
            @default_profile_only("pins a shipped default")
            def test_marked(self):
                ran.append("method")

            def test_unmarked(self):
                ran.append("unmarked")

        return Marked

    def test_method_runs_under_the_shipped_defaults(self) -> None:
        ran: list = []
        with self._loaded():
            self.assertEqual(profile_differences(), [])
            result = self._run_marked(self._method_case(ran))
        self.assertEqual(sorted(ran), ["method", "unmarked"])
        self.assertEqual(result.skipped, [])

    def test_method_skips_when_a_constant_differs(self) -> None:
        for override in ({"vocabulary_profile__RECORD_FILENAME": "set.md"},
                         {"record_paths__WAVES_ROOT": "docs/delivery/sets"},
                         {"vocabulary_profile__ARCHIVE_PROFILE": SHIPPED_VOCABULARY}):
            with self.subTest(override=sorted(override)):
                ran: list = []
                with self._loaded(**override):
                    result = self._run_marked(self._method_case(ran))
                self.assertEqual(ran, ["unmarked"])
                self.assertEqual(len(result.skipped), 1)
                reason = result.skipped[0][1]
                self.assertIn("default-profile-only: pins a shipped default", reason)
                self.assertIn(next(iter(override)).replace("__", "."), reason)

    def test_class_marker_skips_set_up_class_too(self) -> None:
        calls: list = []

        @default_profile_only("a golden output of the shipped profile")
        class Marked(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                calls.append("setUpClass")

            def test_one(self):
                calls.append("one")

        with self._loaded():
            self._run_marked(Marked)
        self.assertEqual(calls, ["setUpClass", "one"])
        calls.clear()
        with self._loaded(record_paths__NESTED=True):
            result = self._run_marked(Marked)
        self.assertEqual(calls, [])
        self.assertEqual(len(result.skipped), 1)
        self.assertEqual(Marked.__default_profile_only__, "a golden output of the shipped profile")

    def test_method_marker_skips_before_set_up(self) -> None:
        calls: list = []

        class Marked(unittest.TestCase):
            def setUp(self):
                calls.append("setUp:" + self._testMethodName)

            @default_profile_only("a profile-dependent setUp")
            def test_marked(self):
                calls.append("marked")

            def test_unmarked(self):
                calls.append("unmarked")

        with self._loaded(vocabulary_profile__RECORD_FILENAME="set.md"):
            result = self._run_marked(Marked)
        self.assertEqual(calls, ["setUp:test_unmarked", "unmarked"])
        self.assertEqual(len(result.skipped), 1)
        calls.clear()
        with self._loaded():
            self._run_marked(Marked)
        self.assertEqual(calls, ["setUp:test_marked", "marked", "setUp:test_unmarked", "unmarked"])

    def test_marker_reads_every_loaded_copy_of_a_module(self) -> None:
        import types

        copy = types.ModuleType("elsewhere.vocabulary_profile")
        for name, value in SHIPPED_DEFAULTS["vocabulary_profile"].items():
            setattr(copy, name, value)
        copy.RECORD_FILENAME = "set.md"
        with framework_profiles() as profiles_dir:
            shipped = expected_profile({}, profiles_dir)
        with self._loaded(), mock.patch.dict(sys.modules, {"elsewhere.vocabulary_profile": copy}):
            self.assertEqual(profile_differences(), ["vocabulary_profile.RECORD_FILENAME"])
            self.assertIn("vocabulary_profile.RECORD_FILENAME is 'set.md'", expected_profile_mismatch(shipped))

    def test_loaded_constants_are_the_expected_profile(self) -> None:
        # The loaded constants are exactly the expected profile: the shipped
        # defaults, or the asset marked active, with the run mode's asset
        # (WAVEFOUNDRY_TEST_PROFILE) over it. A shipped default changed
        # without SHIPPED_DEFAULTS, or a tree left on another profile, fails
        # here loudly rather than silently skipping marked tests.
        try:
            expected = expected_profile()
        except ProfileInvalid as exc:
            self.fail(str(exc))
        problem = expected_profile_mismatch(expected)
        self.assertIsNone(problem, problem)

    def test_declared_profile_match(self) -> None:
        with framework_profiles() as profiles_dir:
            shipped = expected_profile({}, profiles_dir)
            run_second = expected_profile({TEST_PROFILE_ENV: "second"}, profiles_dir)
        with self._loaded():
            self.assertIsNone(expected_profile_mismatch(shipped))
            self.assertIn("'second' from WAVEFOUNDRY_TEST_PROFILE", expected_profile_mismatch(run_second))
        second = {f"{module}__{name}": value
                  for module, values in load_profile("second")["modules"].items() for name, value in values.items()}
        with self._loaded(**second):
            self.assertIsNone(expected_profile_mismatch(run_second))
            # The second profile's values with no marker and no run mode: named, never matched.
            message = expected_profile_mismatch(shipped)
            self.assertIn("(the shipped defaults)", message)
            self.assertIn(f"vocabulary_profile.ITEM_NAME is {SECOND_VOCABULARY['ITEM_NAME']!r}, expected 'Change'",
                          message)
        with self._loaded(**dict(second, record_paths__MAX_DEPTH=3)):
            self.assertIn("record_paths.MAX_DEPTH is 3, expected 4", expected_profile_mismatch(run_second))
        with self._loaded(record_paths__PLANS_ROOT="docs/proposals"):
            self.assertIn("record_paths.PLANS_ROOT", expected_profile_mismatch(shipped))

    def test_tuple_constants_match_their_json_form(self) -> None:
        # Wave 1zimf (1zimp): a profile asset writes a tuple constant as a JSON
        # list, and apply_profile edits it in as a tuple; both are the same value.
        with framework_profiles() as profiles_dir:
            run_second = expected_profile({TEST_PROFILE_ENV: "second"}, profiles_dir)
        second = {f"{module}__{name}": value
                  for module, values in load_profile("second")["modules"].items() for name, value in values.items()}
        self.assertEqual(second["vocabulary_profile__EXTRA_CHANGE_KINDS"], ["decision"])
        with self._loaded(**dict(second, vocabulary_profile__EXTRA_CHANGE_KINDS=("decision",))):
            self.assertIsNone(expected_profile_mismatch(run_second))
        with self._loaded(**dict(second, vocabulary_profile__EXTRA_CHANGE_KINDS=("decision", "spike"))):
            self.assertIn("vocabulary_profile.EXTRA_CHANGE_KINDS is ('decision', 'spike'), expected ['decision']",
                          expected_profile_mismatch(run_second))

    def test_reason_is_required_and_recorded(self) -> None:
        for bad in ("", "   ", "two\nlines", None):
            with self.subTest(reason=bad), self.assertRaises(ValueError):
                default_profile_only(bad)
        marked = default_profile_only("one line")(lambda self: None)
        self.assertEqual(marked.__default_profile_only__, "one line")

    def test_declaration_snapshot_covers_every_declaration_constant(self) -> None:
        # Change 1zim4: every EXTENSION_* constant is in the frozen declaration.
        import ast
        tree = ast.parse((SCRIPTS_DIR / "mcp_tool_extensions.py").read_text(encoding="utf-8"))
        names = {node.target.id if isinstance(node, ast.AnnAssign) else node.targets[0].id
                 for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))}
        self.assertEqual(set(SHIPPED_DECLARATION), {n for n in names if n.startswith("EXTENSION_")})

    def test_a_declaration_leaves_the_marker_and_the_match_alone(self) -> None:
        # A declaration changes the tool surface, not the record profile.
        import mcp_tool_extensions
        with framework_profiles() as profiles_dir:
            shipped = expected_profile({}, profiles_dir)
        with mock.patch.object(mcp_tool_extensions, "EXTENSION_TOOL_ALIASES", {"wf_alias_help": "wf_help"}), \
                self._loaded():
            self.assertEqual(profile_differences(), [])
            self.assertIsNone(expected_profile_mismatch(shipped))

    def test_snapshot_covers_every_editable_constant(self) -> None:
        # Names are not edited by a fork, so this pin holds under any profile.
        self.assertEqual(set(SHIPPED_DEFAULTS["vocabulary_profile"]),
                         set(vocabulary_profile.FIELD_NAMES) | {"ARCHIVE_PROFILE", "EXTRA_CHANGE_KINDS"})
        self.assertEqual(set(SHIPPED_DEFAULTS["record_paths"]),
                         set(record_paths.CONSTANT_NAMES) | {"ARCHIVE_ROOT"})

    def test_edited_modules_on_disk_make_the_marker_skip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            runs = {}
            for name, profile, modules in (
                ("shipped", shipped_default_profile(), None),
                ("second", load_profile("second"), None),
                ("vocabulary-only", load_profile("second"), ("vocabulary_profile",)),
            ):
                scripts = copy_scripts_tree(base / name)
                apply_profile(scripts, shipped_default_profile())
                apply_profile(scripts, profile, modules=modules)
                runs[name] = _driver(MARKER_DRIVER, str(scripts))
        self.assertEqual(runs["shipped"], {"ran": ["marked"], "skipped": [], "differ": []})
        self.assertEqual(runs["second"]["ran"], [])
        self.assertEqual(len(runs["second"]["skipped"]), 1)
        self.assertIn("record_paths.WAVES_ROOT", runs["second"]["differ"])
        self.assertIn("vocabulary_profile.RECORD_FILENAME", runs["second"]["differ"])
        # vocabulary_profile itself edited: the marker reads the frozen
        # snapshot, not the edited module, so it still skips.
        self.assertEqual(runs["vocabulary-only"]["ran"], [])
        self.assertTrue(runs["vocabulary-only"]["differ"])
        self.assertTrue(all(d.startswith("vocabulary_profile.") for d in runs["vocabulary-only"]["differ"]))


class LocalizationHelperTests(unittest.TestCase):
    SECOND = load_profile("second")["modules"]

    def test_localize_record_text_rewrites_markers_labels_and_back_references(self) -> None:
        text = ("# Wave Record\nwave-id: `w`\n\n## Wave Summary\n\n## Changes\n\nChange ID: `x`\n"
                "Previous Change Status: `planned`\nChange Status: `complete`\nWave: w\nA Wave: stays\n")
        v = self.SECOND["vocabulary_profile"]
        self.assertEqual(localize_record_text(text, vocabulary=v), (
            f"{v['RECORD_TITLE']}\n{v['ID_KEY']}: `w`\n\n{v['SUMMARY_HEADING']}\n\n{v['MEMBER_HEADING']}\n\n"
            f"{v['MEMBER_ID_LABEL']}: `x`\nPrevious {v['MEMBER_STATUS_LABEL']}: `planned`\n"
            f"{v['MEMBER_STATUS_LABEL']}: `complete`\n{v['BACKREF_LABEL']}: w\nA Wave: stays\n"))
        self.assertEqual(localize_record_text(text, vocabulary=SHIPPED_VOCABULARY), text)

    def test_localized_fixture_readme_follows_the_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            second = localized_docs_lint_fixture(Path(tmp) / "second", vocabulary=self.SECOND["vocabulary_profile"],
                                                 layout=self.SECOND["record_paths"])
            readme = (second / self.SECOND["record_paths"]["WAVES_ROOT"] / "README.md").read_text(encoding="utf-8")
            shipped = localized_docs_lint_fixture(Path(tmp) / "shipped", vocabulary=SHIPPED_VOCABULARY,
                                                  layout=SHIPPED_DEFAULTS["record_paths"])
            same = ((shipped / "docs" / "waves" / "README.md").read_bytes()
                    == (record_layout_support.DOCS_LINT_FIXTURE / "docs" / "waves" / "README.md").read_bytes())
        self.assertIn(f"# {self.SECOND['vocabulary_profile']['CONTAINER_NAME_PLURAL']}", readme)
        self.assertNotIn("Wave", readme)
        self.assertTrue(same)

    def test_waves_dir_and_rel_follow_the_loaded_layout(self) -> None:
        # Change 1zltu: patch through sys.modules. server_impl evicts and
        # re-imports record_paths, and the helpers import it at call time, so
        # patching the object this module bound at import would patch a stale
        # module once any test in the process has loaded the server.
        with mock.patch("record_paths.WAVES_ROOT", "docs/delivery/sets"):
            self.assertEqual(waves_dir(Path("/r")), Path("/r/docs/delivery/sets"))
            self.assertEqual(waves_rel("a b", "set.md"), "docs/delivery/sets/a b/set.md")

    def test_waves_helpers_follow_the_patch_after_the_server_evicts_record_paths(self) -> None:
        """Change 1zltu: the leaking pair in one interpreter. Reloading the
        server runs its eviction block, so ``record_paths`` in ``sys.modules``
        is no longer the object this module bound at import; the patch above
        must still reach the module the helpers read."""
        import importlib

        from server_tools_support import load_server

        srv = load_server()
        importlib.reload(srv)
        self.assertIsNot(sys.modules["record_paths"], record_paths,
                         "precondition: the eviction block must have replaced record_paths")
        self.test_waves_dir_and_rel_follow_the_loaded_layout()


class ApplyProfileTests(unittest.TestCase):
    """The one shared apply function."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.scripts = copy_scripts_tree(Path(self._tmp.name), with_support=False)
        # The suite may itself run under a profile: start from the shipped defaults.
        apply_profile(self.scripts, shipped_default_profile())

    def test_applies_every_constant_and_returns_the_loaded_values(self) -> None:
        profile = load_profile("second")
        loaded = apply_profile(self.scripts, profile)
        self.assertEqual(loaded["vocabulary_profile"]["RECORD_FILENAME"], "set.md")
        self.assertEqual(loaded["vocabulary_profile"]["ARCHIVE_PROFILE"]["RECORD_FILENAME"], "wave.md")
        self.assertEqual(loaded["record_paths"]["WAVES_ROOT"], "docs/delivery/sets")
        self.assertIs(loaded["record_paths"]["NESTED"], True)
        self.assertEqual(loaded["record_paths"]["PLANS_ROOT"], "docs/plans")

    def test_modules_limits_the_edit(self) -> None:
        loaded = apply_profile(self.scripts, load_profile("second"), modules=("record_paths",))
        self.assertEqual(loaded["vocabulary_profile"]["RECORD_FILENAME"], "wave.md")
        self.assertEqual(loaded["record_paths"]["WAVES_ROOT"], "docs/delivery/sets")

    def test_an_assignment_must_match_exactly_once(self) -> None:
        path = self.scripts / "vocabulary_profile.py"
        text = path.read_text(encoding="utf-8")
        line = re.search(r"(?m)^RECORD_FILENAME = .*\n", text).group(0)
        path.write_text(text.replace(line, line + line), encoding="utf-8")
        with self.assertRaisesRegex(ProfileInvalid, r"RECORD_FILENAME: 2 assignments"):
            apply_profile(self.scripts, load_profile("second"))
        path.write_text(text.replace(line, ""), encoding="utf-8")
        with self.assertRaisesRegex(ProfileInvalid, r"RECORD_FILENAME: 0 assignments"):
            apply_profile(self.scripts, load_profile("second"))

    def test_the_edited_modules_must_import(self) -> None:
        profile = {"modules": {"vocabulary_profile": {"RECORD_FILENAME": "README.md"}}}
        with self.assertRaisesRegex(ProfileInvalid, "do not import"):
            apply_profile(self.scripts, profile)

    def test_the_layout_is_validated_against_a_repository(self) -> None:
        profile = {"modules": {"record_paths": {"WAVES_ROOT": "docs/plans/waves"}}}
        with self.assertRaisesRegex(ProfileInvalid, "must not nest"):
            apply_profile(self.scripts, profile, repo_root=Path(self._tmp.name))

    def test_unknown_constants_and_modules_are_refused(self) -> None:
        with self.assertRaisesRegex(ProfileInvalid, "not a fork-editable constant"):
            apply_profile(self.scripts, {"modules": {"record_paths": {"MAX_DEPTH_RANGE": [1, 2]}}})
        with self.assertRaisesRegex(ProfileInvalid, "unknown module"):
            apply_profile(self.scripts, {"modules": {"server_impl": {"X": 1}}})

    def test_never_edits_the_canonical_tree(self) -> None:
        # The copy stands in for the canonical tree, so a regression of the
        # refusal edits only this temporary copy, never the repository.
        before = (self.scripts / "vocabulary_profile.py").read_bytes()
        with mock.patch.object(record_layout_support, "SCRIPTS_DIR", self.scripts), \
                self.assertRaisesRegex(ProfileInvalid, "never the canonical"):
            apply_profile(self.scripts, load_profile("second"))
        self.assertEqual((self.scripts / "vocabulary_profile.py").read_bytes(), before)

    def test_crlf_modules_keep_their_line_endings(self) -> None:
        for name in ("vocabulary_profile.py", "record_paths.py"):
            path = self.scripts / name
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        loaded = apply_profile(self.scripts, load_profile("second"))
        self.assertEqual(loaded["vocabulary_profile"]["RECORD_FILENAME"], "set.md")
        self.assertEqual(loaded["record_paths"]["WAVES_ROOT"], "docs/delivery/sets")
        data = (self.scripts / "vocabulary_profile.py").read_bytes()
        self.assertIn(b"RECORD_FILENAME = 'set.md'\r\n", data)
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))

    # ---- Declarations (change 1zim4) ---------------------------------------

    def _shipped_declaration(self) -> None:
        # The running tree may itself carry a declaration: start from the empty one.
        apply_profile(self.scripts, {"modules": {"mcp_tool_extensions": json.loads(json.dumps(SHIPPED_DECLARATION))}})

    def test_the_declared_asset_applies_a_plain_and_a_parameter_mapped_alias(self) -> None:
        self._shipped_declaration()
        profile = load_profile("declared")
        loaded = apply_profile(self.scripts, profile)
        declared = loaded["mcp_tool_extensions"]
        aliases = declared["EXTENSION_TOOL_ALIASES"]
        parameters = declared["EXTENSION_TOOL_PARAMETERS"]
        self.assertEqual(aliases, profile["modules"]["mcp_tool_extensions"]["EXTENSION_TOOL_ALIASES"])
        plain = [alias for alias in aliases if alias not in parameters]
        mapped = [alias for alias, spec in parameters.items() if spec.get("rename") and spec.get("fixed")]
        self.assertEqual(len(plain), 1)
        self.assertEqual(len(mapped), 1)
        # The record profile is untouched, so the default-profile-only marker still runs.
        # The loaded constants come back in JSON form (tuples as lists).
        self.assertEqual(loaded["vocabulary_profile"], json.loads(json.dumps(SHIPPED_DEFAULTS["vocabulary_profile"])))
        self.assertEqual(loaded["record_paths"], SHIPPED_DEFAULTS["record_paths"])
        self.assertNotIn("mcp_tool_extensions", SHIPPED_DEFAULTS)

    def test_tuple_declarations_stay_tuples(self) -> None:
        self._shipped_declaration()
        apply_profile(self.scripts, {"modules": {"mcp_tool_extensions": {
            "EXTENSION_TOOL_ALIASES": {"wf_alias_help": "wf_help"},
            "EXTENSION_HIDDEN_TOOLS": ["wf_help"]}}})
        text = (self.scripts / "mcp_tool_extensions.py").read_text(encoding="utf-8")
        self.assertIn("EXTENSION_HIDDEN_TOOLS: tuple[str, ...] = ('wf_help',)\n", text)

    def test_an_invalid_declaration_is_refused(self) -> None:
        self._shipped_declaration()
        with self.assertRaisesRegex(ProfileInvalid, "invalid tool declaration: alias 'wf_alias_x' targets 'wf_nope'"):
            apply_profile(self.scripts, {"modules": {"mcp_tool_extensions": {
                "EXTENSION_TOOL_ALIASES": {"wf_alias_x": "wf_nope"}}}})

    def test_a_declaration_assignment_must_match_exactly_once(self) -> None:
        path = self.scripts / "mcp_tool_extensions.py"
        text = path.read_text(encoding="utf-8")
        line = re.search(r"(?m)^EXTENSION_TOOL_ALIASES: .*\n", text).group(0)
        path.write_text(text.replace(line, line + line), encoding="utf-8")
        with self.assertRaisesRegex(ProfileInvalid, r"EXTENSION_TOOL_ALIASES: 2 assignments"):
            apply_profile(self.scripts, load_profile("declared"))

    def test_unknown_declaration_constants_are_refused(self) -> None:
        with self.assertRaisesRegex(ProfileInvalid, "mcp_tool_extensions.EDIT_GATE_TOOLS is not a fork-editable"):
            apply_profile(self.scripts, {"modules": {"mcp_tool_extensions": {"EDIT_GATE_TOOLS": []}}})

    def test_profile_names_are_validated(self) -> None:
        for bad in ("../second", "Second", "", "missing"):
            with self.subTest(name=bad), self.assertRaises(ProfileInvalid):
                load_profile(bad)


def _symlink_or_skip(testcase: unittest.TestCase, target: Path, link: Path, *, directory: bool = False) -> None:
    """Make ``link`` point at ``target``, or skip where the platform refuses
    (Windows without the symlink privilege or developer mode)."""
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        testcase.skipTest(f"symlinks cannot be created here: {exc}")


def _remove_link(link: Path) -> None:
    """Remove a symlink (a directory link on Windows needs ``rmdir``)."""
    try:
        os.unlink(link)
    except OSError:
        os.rmdir(link)


class ProfileWritesStayInTheCopyTests(unittest.TestCase):
    """DEL-1ZIM5-PROFILE-SYMLINK-WRITE: a symlink in the copy never carries a
    profile write outside it."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.outside = base / "outside"
        self.outside.mkdir()
        self.copy = base / "copy"
        self.scripts = copy_scripts_tree(self.copy, with_support=False)
        # Start from the shipped defaults and the empty declaration, whatever the suite runs under.
        apply_profile(self.scripts, shipped_default_profile())
        apply_profile(self.scripts, {"modules": {"mcp_tool_extensions": json.loads(json.dumps(SHIPPED_DECLARATION))}})

    def _link_outside(self, name: str) -> Path:
        target = self.outside / name
        shutil.move(str(self.scripts / name), str(target))
        _symlink_or_skip(self, target, self.scripts / name)
        return target

    def test_symlinked_profile_modules_are_replaced_not_followed(self) -> None:
        names = ("vocabulary_profile.py", "record_paths.py", "mcp_tool_extensions.py")
        targets = {name: self._link_outside(name) for name in names}
        before = {name: target.read_bytes() for name, target in targets.items()}
        loaded = apply_profile(self.scripts, load_profile("second"), repo_root=self.copy)
        loaded.update(apply_profile(self.scripts, load_profile("declared")))
        for name, target in targets.items():
            with self.subTest(module=name):
                self.assertEqual(target.read_bytes(), before[name], f"{target} was written through the link")
                copied = self.scripts / name
                self.assertFalse(copied.is_symlink())
                self.assertTrue(copied.is_file())
        self.assertEqual(loaded["vocabulary_profile"]["RECORD_FILENAME"], "set.md")
        self.assertEqual(loaded["record_paths"]["WAVES_ROOT"], "docs/delivery/sets")
        self.assertIn("wf_alias_help", loaded["mcp_tool_extensions"]["EXTENSION_TOOL_ALIASES"])
        self.assertIn(b"RECORD_FILENAME = 'set.md'", (self.scripts / "vocabulary_profile.py").read_bytes())

    def test_a_module_in_a_directory_outside_the_copy_is_refused(self) -> None:
        moved = self.outside / "scripts"
        shutil.move(str(self.scripts), str(moved))
        _symlink_or_skip(self, moved, self.scripts, directory=True)
        before = (moved / "vocabulary_profile.py").read_bytes()
        with self.assertRaisesRegex(ProfileInvalid, "outside"):
            apply_profile(self.scripts, load_profile("second"), repo_root=self.copy)
        self.assertEqual((moved / "vocabulary_profile.py").read_bytes(), before)

    def _readme_args(self) -> dict:
        return {"vocabulary": SHIPPED_DEFAULTS["vocabulary_profile"], "layout": SHIPPED_DEFAULTS["record_paths"]}

    def test_a_symlinked_readme_is_replaced_not_followed(self) -> None:
        waves = self.copy / SHIPPED_DEFAULTS["record_paths"]["WAVES_ROOT"]
        waves.mkdir(parents=True)
        for case in ("existing", "dangling"):
            with self.subTest(target=case):
                target = self.outside / f"README-{case}.md"
                if case == "existing":
                    target.write_bytes(b"outside\n")
                link = waves / "README.md"
                if os.path.lexists(link):
                    os.unlink(link)
                _symlink_or_skip(self, target, link)
                readme = record_layout_support.write_waves_readme(self.copy, **self._readme_args())
                self.assertEqual(readme, link)
                self.assertFalse(link.is_symlink())
                self.assertIn("Owner: Engineering", link.read_text(encoding="utf-8"))
                if case == "existing":
                    self.assertEqual(target.read_bytes(), b"outside\n")
                else:
                    self.assertFalse(os.path.lexists(target), f"{target} was created through the link")

    def test_a_readme_under_a_symlinked_directory_is_refused(self) -> None:
        rel = Path(SHIPPED_DEFAULTS["record_paths"]["WAVES_ROOT"])
        for linked in (rel, Path(rel.parts[0])):
            with self.subTest(linked=linked.as_posix()):
                target = self.outside / f"dir-{len(linked.parts)}"
                target.mkdir()
                link = self.copy / linked
                if link.is_symlink():
                    _remove_link(link)
                elif link.exists():
                    shutil.rmtree(link)
                link.parent.mkdir(parents=True, exist_ok=True)
                _symlink_or_skip(self, target, link, directory=True)
                with self.assertRaisesRegex(ProfileInvalid, "outside"):
                    record_layout_support.write_waves_readme(self.copy, **self._readme_args())
                self.assertEqual(list(target.rglob("*")), [])
                _remove_link(link)

    def test_a_sibling_that_shares_the_root_prefix_is_outside(self) -> None:
        sibling = self.copy.parent / (self.copy.name + "-sibling")
        sibling.mkdir()
        with self.assertRaisesRegex(ProfileInvalid, "outside"):
            record_layout_support.replace_file_in(self.copy, sibling / "x.txt", b"x\n")
        self.assertFalse((sibling / "x.txt").exists())

    def test_the_copy_never_writes_through_a_directory_replaced_by_a_link(self) -> None:
        # A tracked directory replaced on disk by a relative link: git still
        # lists the files under it, and the copy must not follow the link.
        source = Path(self._tmp.name) / "a" / "b" / "src"
        (source / "d").mkdir(parents=True)
        (source / "d" / "x.txt").write_text("tracked\n", encoding="utf-8")
        env = run_tests._git_env()
        for args in (["init", "-q"], ["add", "-A"],
                     ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"]):
            subprocess.run(["git", "-C", str(source), *args], check=True, env=env, capture_output=True)
        shutil.rmtree(source / "d")
        # The link resolves to a/escape from the source and to escape from the copy.
        (Path(self._tmp.name) / "a" / "escape").mkdir()
        (Path(self._tmp.name) / "a" / "escape" / "x.txt").write_text("source side\n", encoding="utf-8")
        escape = Path(self._tmp.name) / "escape"
        escape.mkdir()
        _symlink_or_skip(self, Path("..") / ".." / "escape", source / "d", directory=True)
        dest = Path(self._tmp.name) / "w" / "repo"
        dest.mkdir(parents=True)
        copied, error = run_tests._copy_listed_tree(source, dest)
        self.assertIsNone(error)
        self.assertTrue(os.path.islink(dest / "d"))
        self.assertEqual(list(escape.iterdir()), [], "the copy wrote a listed file through a linked directory")


# The copy's runner, replaced in the tiny repository: it reports what it sees
# and writes a receipt in its own tree, as a full run of the real runner would.
STUB_RUNNER = r'''
import json, os, subprocess, sys
from pathlib import Path
here = Path(__file__).resolve().parent
repo = here.parents[2]
sys.path.insert(0, str(here))
import record_paths, vocabulary_profile
files = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--file"]
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True, text=True)
status = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo), capture_output=True, text=True)
facts = {
    "cwd": os.getcwd(), "repo": str(repo), "files": files, "head": head.returncode == 0,
    "clean": status.stdout.strip() == "",
    "present": sorted(n for n in ("tracked.txt", "untracked.txt", "ignored.txt") if (repo / n).exists()),
    "record": vocabulary_profile.RECORD_FILENAME, "waves_root": record_paths.WAVES_ROOT,
    "readme": (repo / record_paths.WAVES_ROOT / "README.md").is_file(),
    "git_env": sorted(k for k in os.environ if k.startswith("GIT_")),
    # The run-mode name the copy's guards resolve (change 1zima).
    "run_mode": os.environ.get("WAVEFOUNDRY_TEST_PROFILE"),
}
print("FACTS " + json.dumps(facts))
(here.parent / "test-cache.json").write_text('{"result": "ok", "written": "by the copy"}\n')
# Read-only entries, as git's object files are: the run must still remove them.
locked = repo / "locked"
locked.mkdir()
(locked / "object").write_text("x")
os.chmod(locked / "object", 0o444)
os.chmod(locked, 0o555)
os.chmod(repo / "tracked.txt", 0o444)
if (repo / "touch-receipt.txt").exists():
    Path((repo / "touch-receipt.txt").read_text().strip()).write_text("changed by the copy\n")
dash = "\u2014"
print(f"  [1/2] test_alpha.py {dash} 3 tests ok (0.1s)")
print(f"  [2/2] test_beta.py {dash} 4 tests FAIL (0.2s)")
print("\n" + "=" * 70 + "\nFAILED: test_beta.py\n" + "=" * 70)
print("  [9/9] test_quoted.py " + dash + " 1 tests FAIL (0.1s)")
print("-" * 70 + "\nRan 4 tests in 0.2s\n\nFAILED (failures=2, errors=1)")
print("\n" + "-" * 70 + "\nSlowest files (top 2 of 2):\nFAILED (test_beta.py)")
sys.exit(0 if (repo / "exit-zero").exists() else 1)
'''


class ProfileRunTests(unittest.TestCase):
    """AC-3: the run mode, against a tiny repository and a stubbed runner."""

    def _tiny_repo(self, base: Path) -> Path:
        repo = base / "tiny"
        scripts = repo / ".wavefoundry" / "framework" / "scripts"
        (scripts / "tests").mkdir(parents=True)
        for name in ("vocabulary_profile.py", "record_paths.py"):
            shutil.copy2(SCRIPTS_DIR / name, scripts / name)
        (scripts / "run_tests.py").write_text(STUB_RUNNER, encoding="utf-8")
        for name in ("test_alpha.py", "test_beta.py"):
            (scripts / "tests" / name).write_text("", encoding="utf-8")
        (repo / ".gitignore").write_text("ignored.txt\n.wavefoundry/framework/test-cache.json\n", encoding="utf-8")
        (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
        (repo / ".wavefoundry" / "framework" / "test-cache.json").write_bytes(b'{"result": "ok", "original": 1}\n')
        git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@localhost", "-c", "commit.gpgsign=false"]
        env = run_tests._git_env()
        for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "--no-verify", "-m", "tiny"]):
            subprocess.run(git + cmd, check=True, capture_output=True, env=env)
        (repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
        (repo / "ignored.txt").write_text("ignored\n", encoding="utf-8")
        return repo

    @staticmethod
    def _expected(name: str) -> str:
        # The canonical assets, as the run resolves them.
        return expected_profile({TEST_PROFILE_ENV: name}).describe()

    def _run(self, repo: Path, selectors=()) -> "tuple[int, str]":
        scripts = repo / ".wavefoundry" / "framework" / "scripts"
        out = io.StringIO()
        with mock.patch.object(run_tests, "_REPO_ROOT", repo), \
                mock.patch.object(run_tests, "_SCRIPT_DIR", scripts), \
                mock.patch.object(run_tests, "_CACHE_FILE", repo / ".wavefoundry" / "framework" / "test-cache.json"), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            rc = run_tests._run_profile("second", list(selectors))
        return rc, out.getvalue()

    def test_copies_applies_runs_reports_and_leaves_the_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._tiny_repo(Path(tmp))
            receipt = repo / ".wavefoundry" / "framework" / "test-cache.json"
            before = receipt.read_bytes()
            tree_before = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*") if ".git" not in p.parts)
            rc, output = self._run(repo)
            self.assertEqual(receipt.read_bytes(), before)
            self.assertEqual(
                sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*") if ".git" not in p.parts),
                tree_before)
        self.assertEqual(rc, 1)
        facts = json.loads(output.split("FACTS ", 1)[1].splitlines()[0])
        # A temporary git repository, not this tree, holding the listed files.
        self.assertNotEqual(facts["repo"], str(repo))
        self.assertEqual(Path(facts["cwd"]).resolve(), Path(facts["repo"]).resolve())
        self.assertTrue(facts["head"])
        self.assertTrue(facts["clean"])
        self.assertEqual(facts["present"], ["tracked.txt", "untracked.txt"])
        # The asset applied and the configured README written.
        self.assertEqual((facts["record"], facts["waves_root"]), ("set.md", "docs/delivery/sets"))
        self.assertTrue(facts["readme"])
        # All discovered files, as a focused run.
        self.assertEqual(facts["files"], ["test_alpha.py", "test_beta.py"])
        # Per-file report; a quoted progress line inside a failure block is not counted.
        # The run-mode name reaches the copy, and the report names the
        # expected profile's layers and sources beside the profile (change 1zima).
        self.assertEqual(facts["run_mode"], "second")
        self.assertIn(f"Expected profile: {self._expected('second')}.", output)
        self.assertIn(f"Second-profile per-file result (profile 'second'; expected profile: "
                      f"{self._expected('second')}): 1 of 2 files failed", output)
        self.assertIn("test_beta.py", output.split("Second-profile per-file result", 1)[1])
        self.assertIn("failures=2 errors=1", output)
        self.assertIn("Total failures and errors: 3 in 1 files; 1 files passed", output)
        self.assertNotIn("test_quoted.py", output.split("Second-profile per-file result", 1)[1])
        self.assertEqual(output.count("not delivery evidence"), 2)

    @contextlib.contextmanager
    def _work_dirs(self):
        """Record every temporary directory the run creates."""
        made: list = []
        real = tempfile.mkdtemp

        def recording(*args, **kwargs):
            path = real(*args, **kwargs)
            made.append(Path(path))
            return path

        with mock.patch.object(tempfile, "mkdtemp", recording):
            yield made

    def test_work_tree_is_removed_with_read_only_entries(self) -> None:
        for outcome in ("success", "failure"):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as tmp:
                repo = self._tiny_repo(Path(tmp))
                if outcome == "success":
                    (repo / "exit-zero").write_text("", encoding="utf-8")
                with self._work_dirs() as made:
                    rc, output = self._run(repo)
                self.assertEqual(rc, 0 if outcome == "success" else 1, output)
                work = [d for d in made if d.name.startswith("wf-profile-run-")]
                self.assertEqual(len(work), 1)
                self.assertFalse(os.path.lexists(work[0]), f"{work[0]} was left behind")

    def test_a_changed_receipt_fails_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._tiny_repo(Path(tmp))
            receipt = repo / ".wavefoundry" / "framework" / "test-cache.json"
            (repo / "exit-zero").write_text("", encoding="utf-8")
            (repo / "touch-receipt.txt").write_text(str(receipt), encoding="utf-8")
            rc, output = self._run(repo)
        self.assertEqual(rc, 1)
        self.assertIn("changed during the second-profile run", output)

    def test_the_copy_gets_no_git_variables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._tiny_repo(Path(tmp))
            elsewhere = Path(tmp) / "elsewhere.git"
            with mock.patch.dict(os.environ, {"GIT_DIR": str(elsewhere), "GIT_WORK_TREE": str(elsewhere)}):
                rc, output = self._run(repo)
        facts = json.loads(output.split("FACTS ", 1)[1].splitlines()[0])
        self.assertEqual(facts["git_env"], [])
        self.assertTrue(facts["head"])

    def test_malformed_selectors_are_refused_before_copying(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._tiny_repo(Path(tmp))
            with mock.patch.object(run_tests, "_copy_listed_tree", side_effect=AssertionError("copied")), \
                    self._work_dirs() as made:
                for bad in (["../test_x.py"], ["test_a.py", "test_a.py"], ["helper.py"]):
                    rc, output = self._run(repo, bad)
                    self.assertEqual(rc, 2, output)
        self.assertEqual(made, [])

    @unittest.skipIf(os.name == "nt", "SIGTERM is not delivered to Python this way on Windows")
    def test_sigterm_ends_the_child_and_removes_the_tree(self) -> None:
        import signal

        seen: dict = {}

        def interrupted(work, name, profile, profiles, scripts_rel, selectors, state):
            (work / "locked").mkdir()
            os.chmod(work / "locked", 0o555)
            state["proc"] = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                                             start_new_session=True)
            seen["proc"], seen["work"] = state["proc"], work
            seen["handler"] = signal.getsignal(signal.SIGTERM)
            os.kill(os.getpid(), signal.SIGTERM)
            raise AssertionError("SIGTERM did not interrupt the run")

        before = signal.getsignal(signal.SIGTERM)
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._tiny_repo(Path(tmp))
            with mock.patch.object(run_tests, "_profile_run_in", interrupted), \
                    self.assertRaises(KeyboardInterrupt):
                self._run(repo)
        self.assertIsNot(seen["handler"], before)
        self.assertIs(signal.getsignal(signal.SIGTERM), before)
        self.assertIsNotNone(seen["proc"].returncode)
        self.assertFalse(os.path.lexists(seen["work"]))

    def test_a_symlinked_profile_module_outside_the_repository_is_left_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._tiny_repo(Path(tmp))
            outside = Path(tmp) / "outside-vocabulary_profile.py"
            module = repo / ".wavefoundry" / "framework" / "scripts" / "vocabulary_profile.py"
            shutil.move(str(module), str(outside))
            _symlink_or_skip(self, outside, module)
            before = outside.read_bytes()
            rc, output = self._run(repo)
            self.assertEqual(outside.read_bytes(), before, "the profile run wrote through the symlink")
            self.assertTrue(module.is_symlink())
        facts = json.loads(output.split("FACTS ", 1)[1].splitlines()[0])
        # The copy still took the profile, in its own regular file.
        self.assertEqual(facts["record"], "set.md")

    def test_file_selectors_are_validated_against_the_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._tiny_repo(Path(tmp))
            rc, output = self._run(repo, ["test_beta.py"])
            self.assertEqual(json.loads(output.split("FACTS ", 1)[1].splitlines()[0])["files"], ["test_beta.py"])
            rc, output = self._run(repo, ["test_missing.py"])
        self.assertEqual(rc, 2)
        self.assertIn("not a discovered test file", output)

    def test_report_parser(self) -> None:
        dash = "\u2014"
        output = (
            f"  [1/3] test_a.py {dash} 5 tests ok (1.0s)\n"
            f"  [2/3] test_b.py {dash} 6 tests FAIL (1.0s)\n"
            f"  [3/3] test_c.py {dash} 0 tests FAIL (600.0s)\n"
            "\n" + "=" * 70 + "\nFAILED: test_b.py\n" + "=" * 70 + "\n"
            "Ran 6 tests in 1.0s\n\nFAILED (failures=1, errors=4, skipped=2)\n"
            "\n" + "=" * 70 + "\nFAILED: test_c.py\n" + "=" * 70 + "\nTIMEOUT: test_c.py exceeded\n"
            "\n" + "-" * 70 + "\nSlowest files (top 3 of 3):\nFAILED (test_b.py, test_c.py)\n"
        )
        rows = run_tests._profile_run_report(output)
        self.assertEqual([r["name"] for r in rows], ["test_b.py", "test_a.py", "test_c.py"])
        self.assertEqual((rows[0]["failures"], rows[0]["errors"], rows[0]["tests"]), (1, 4, 6))
        self.assertEqual(rows[1]["status"], "ok")
        self.assertIsNone(rows[2]["failures"])



# ---------------------------------------------------------------------------
# Change 1zima: the expected profile and the exact guards
# ---------------------------------------------------------------------------

# Runs the guards in a fresh interpreter over a copied scripts tree, once per
# case: ``[environ, profiles_dir]``. The resolver is injected, so no case
# reads this process's WAVEFOUNDRY_TEST_PROFILE.
GUARD_DRIVER = r"""
import json, sys
from pathlib import Path
scripts = Path(sys.argv[1])
sys.path.insert(0, str(scripts / "tests"))
sys.path.insert(0, str(scripts))
import record_layout_support as s
import declaration_support as d
results = []
for environ, profiles_dir in json.loads(sys.argv[2]):
    out = {}
    try:
        expected = s.expected_profile(environ, profiles_dir)
    except s.ProfileInvalid as exc:
        out["error"] = str(exc)
    else:
        out["layers"] = expected.describe()
        out["record"] = s.expected_profile_mismatch(expected)
        out["declaration"] = d.declaration_profile_mismatch(expected)
    results.append(out)
print(json.dumps(results))
"""


def _asset(profile: dict, *, active: "bool | None" = None) -> dict:
    asset = {"description": "A distribution's own profile (test).", "modules": profile["modules"]}
    if active is not None:
        asset["active"] = active
    return asset


class ExpectedProfileTests(unittest.TestCase):
    """The active marker, the resolver and the report's source."""

    def test_active_must_be_a_boolean(self) -> None:
        modules = {"record_paths": {"MAX_DEPTH": 3}}
        for value in (True, False):
            self.assertEqual(record_layout_support._profile_errors({"active": value, "modules": modules}), [])
        for value in ("yes", 1, None, [True]):
            with self.subTest(active=value):
                errors = record_layout_support._profile_errors({"active": value, "modules": modules})
                self.assertEqual(len(errors), 1)
                self.assertIn("'active' must be true or false", errors[0])
        with framework_profiles(dist={"active": "true", "modules": modules}) as profiles_dir:
            with self.assertRaisesRegex(ProfileInvalid, "'active' must be true or false"):
                load_profile("dist", profiles_dir)
            # An invalid asset fails the resolution; it never falls back.
            with self.assertRaisesRegex(ProfileInvalid, "'active' must be true or false"):
                expected_profile({}, profiles_dir)

    def test_framework_assets_are_never_marked_active(self) -> None:
        for name in FRAMEWORK_ASSETS:
            with self.subTest(asset=name):
                self.assertNotIn("active", json.loads((PROFILES_DIR / f"{name}.json").read_text(encoding="utf-8")))

    def test_layers_and_sources(self) -> None:
        second = load_profile("second")
        with framework_profiles() as plain, framework_profiles(dist=_asset(second, active=True)) as active:
            shipped = expected_profile({}, plain)
            run_mode = expected_profile({TEST_PROFILE_ENV: "declared"}, plain)
            distribution = expected_profile({}, active)
            layered = expected_profile({TEST_PROFILE_ENV: "declared"}, active)
        self.assertEqual((shipped.source, shipped.describe()), ("shipped", "the shipped defaults"))
        self.assertEqual((run_mode.source, run_mode.describe()),
                         ("run mode", "the shipped defaults, then 'declared' from WAVEFOUNDRY_TEST_PROFILE"))
        self.assertEqual((distribution.source, distribution.describe()),
                         ("active asset", "'dist' from the active asset dist.json"))
        self.assertEqual(layered.describe(),
                         "'dist' from the active asset dist.json, then 'declared' from WAVEFOUNDRY_TEST_PROFILE")
        # The run mode overlays the base constant by constant, as apply_profile edits the copy.
        self.assertEqual(layered.constants()["vocabulary_profile"]["ITEM_NAME"], SECOND_VOCABULARY["ITEM_NAME"])
        self.assertEqual(layered.constants()["record_paths"]["PLANS_ROOT"], "docs/plans")
        self.assertEqual(layered.declaration()["EXTENSION_TOOL_ALIASES"],
                         load_profile("declared")["modules"]["mcp_tool_extensions"]["EXTENSION_TOOL_ALIASES"])
        self.assertEqual(shipped.constants(), SHIPPED_DEFAULTS)
        self.assertEqual(shipped.declaration(), SHIPPED_DECLARATION)

    def test_the_variable_is_read_from_the_given_environment(self) -> None:
        with framework_profiles() as plain, \
                mock.patch.dict(os.environ, {TEST_PROFILE_ENV: "second"}):
            self.assertIsNone(expected_profile({}, plain).run_mode)
            self.assertEqual(expected_profile(None, plain).run_mode.name, "second")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(TEST_PROFILE_ENV, None)
            self.assertIsNone(record_layout_support.run_mode_profile_name())
        self.assertEqual(record_layout_support.run_mode_profile_name({TEST_PROFILE_ENV: "x"}), "x")

    def test_the_report_states_the_expected_profile_and_its_source(self) -> None:
        with framework_profiles(dist=_asset(load_profile("second"), active=True)) as active:
            described = expected_profile({TEST_PROFILE_ENV: "declared"}, active).describe()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run_tests._print_profile_report("declared", [], described)
        self.assertIn("Second-profile per-file result (profile 'declared'; expected profile: 'dist' from the "
                      "active asset dist.json, then 'declared' from WAVEFOUNDRY_TEST_PROFILE): 0 of 0 files failed",
                      out.getvalue())

    def test_the_copy_runner_environment_names_the_run_mode(self) -> None:
        with mock.patch.dict(os.environ, {TEST_PROFILE_ENV: "stray", "GIT_DIR": "elsewhere"}):
            env = run_tests._child_runner_env({TEST_PROFILE_ENV: "second"})
        self.assertEqual(env[TEST_PROFILE_ENV], "second")
        self.assertNotIn("GIT_DIR", env)


class ExpectedProfileScratchTreeTests(unittest.TestCase):
    """AC-3 (a) to (e) and (g): the guards in scratch canonical trees, each
    reset to the shipped defaults and the empty declaration first (the suite
    may itself run under a profile), with the resolver injected."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        second, declared = load_profile("second"), load_profile("declared")

        def tree(name: str, *profiles: dict) -> Path:
            scripts = copy_scripts_tree(base / name)
            apply_profile(scripts, shipped_default_profile())
            apply_profile(scripts, {"modules": {"mcp_tool_extensions": json.loads(json.dumps(SHIPPED_DECLARATION))}})
            for profile in profiles:
                apply_profile(scripts, profile)
            return scripts

        cls.trees = {"shipped": tree("shipped"), "second": tree("second", second),
                     "declared": tree("declared", declared), "layered": tree("layered", second, declared)}
        cls.dirs = {}
        for name, extra in (("plain", {}), ("active", {"dist": _asset(second, active=True)}),
                            ("two-active", {"dist": _asset(second, active=True),
                                            "dist2": _asset(declared, active=True)}),
                            ("inactive", {"dist": _asset(second, active=False)})):
            directory = base / "profiles" / name
            directory.mkdir(parents=True)
            for asset in FRAMEWORK_ASSETS:
                shutil.copy2(PROFILES_DIR / f"{asset}.json", directory / f"{asset}.json")
            for asset, data in extra.items():
                (directory / f"{asset}.json").write_text(json.dumps(data), encoding="utf-8")
            cls.dirs[name] = str(directory)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _guards(self, tree: str, *cases: "tuple[dict, str]") -> list:
        return _driver(GUARD_DRIVER, str(self.trees[tree]),
                       json.dumps([[environ, self.dirs[d]] for environ, d in cases]))

    def test_a_tree_with_the_second_vocabulary_and_no_marker_fails(self) -> None:
        # (a): no active asset, no run-mode name.
        (out,) = self._guards("second", ({}, "plain"))
        self.assertIn("(the shipped defaults)", out["record"])
        self.assertIn(f"vocabulary_profile.ITEM_NAME is {SECOND_VOCABULARY['ITEM_NAME']!r}, expected 'Change'",
                      out["record"])
        self.assertIn("record_paths.WAVES_ROOT", out["record"])
        self.assertIsNone(out["declaration"])
        # An asset present but not active is not a marker.
        (out,) = self._guards("second", ({}, "inactive"))
        self.assertIn("(the shipped defaults)", out["record"])

    def test_a_tree_with_the_declared_declaration_and_no_marker_fails(self) -> None:
        # (b)
        (out,) = self._guards("declared", ({}, "plain"))
        self.assertIsNone(out["record"])
        self.assertIn("(the shipped defaults)", out["declaration"])
        self.assertIn("mcp_tool_extensions.EXTENSION_TOOL_ALIASES is", out["declaration"])
        self.assertIn("mcp_tool_extensions.EXTENSION_TOOL_PARAMETERS is", out["declaration"])

    def test_an_active_asset_must_match_the_tree(self) -> None:
        # (c): fails when the tree differs from its active asset, passes when it matches.
        (differs,) = self._guards("shipped", ({}, "active"))
        self.assertIn("('dist' from the active asset dist.json)", differs["record"])
        self.assertIn("vocabulary_profile.ITEM_NAME is 'Change', expected "
                      f"{SECOND_VOCABULARY['ITEM_NAME']!r}", differs["record"])
        (matches,) = self._guards("second", ({}, "active"))
        self.assertEqual((matches["record"], matches["declaration"]), (None, None))

    def test_two_active_assets_fail(self) -> None:
        # (d)
        (out,) = self._guards("shipped", ({}, "two-active"))
        self.assertIn("more than one profile asset is marked active", out["error"])
        self.assertIn("dist.json, dist2.json", out["error"])
        # With a run mode named, the failure names that layer too.
        (out,) = self._guards("shipped", ({TEST_PROFILE_ENV: "second"}, "two-active"))
        self.assertIn("more than one profile asset is marked active", out["error"])
        self.assertIn("run-mode layer: 'second' from WAVEFOUNDRY_TEST_PROFILE", out["error"])

    def test_a_run_mode_name_with_no_asset_fails(self) -> None:
        # (e): never a fallback to any match.
        (out,) = self._guards("shipped", ({TEST_PROFILE_ENV: "absent"}, "plain"))
        self.assertIn("WAVEFOUNDRY_TEST_PROFILE='absent' names no usable profile asset", out["error"])
        self.assertIn("no profile asset named 'absent'", out["error"])
        self.assertIn("base layer: the shipped defaults", out["error"])

    def test_the_shipped_tree_and_each_run_mode_pass(self) -> None:
        for tree, environ in (("shipped", {}), ("second", {TEST_PROFILE_ENV: "second"}),
                              ("declared", {TEST_PROFILE_ENV: "declared"})):
            with self.subTest(tree=tree):
                (out,) = self._guards(tree, (environ, "plain"))
                self.assertEqual((out["record"], out["declaration"]), (None, None), out)
        # A run mode on the wrong tree fails, naming the run-mode layer.
        (out,) = self._guards("shipped", ({TEST_PROFILE_ENV: "second"}, "plain"))
        self.assertIn("'second' from WAVEFOUNDRY_TEST_PROFILE", out["record"])

    def test_an_active_asset_with_a_run_mode_is_the_layering(self) -> None:
        # (g): the copy equals the active asset with the run mode over it.
        run_mode = {TEST_PROFILE_ENV: "declared"}
        layered, unlayered = self._guards("layered", (run_mode, "active"), ({}, "active"))
        self.assertEqual((layered["record"], layered["declaration"]), (None, None), layered)
        self.assertEqual(layered["layers"],
                         "'dist' from the active asset dist.json, then 'declared' from WAVEFOUNDRY_TEST_PROFILE")
        self.assertIsNone(unlayered["record"])
        self.assertIn("EXTENSION_TOOL_ALIASES", unlayered["declaration"])
        (base_only,) = self._guards("second", (run_mode, "active"))
        self.assertIsNone(base_only["record"])
        self.assertIn("('dist' from the active asset dist.json, then 'declared' from WAVEFOUNDRY_TEST_PROFILE)",
                      base_only["declaration"])
        (run_only,) = self._guards("declared", (run_mode, "active"))
        self.assertIn("vocabulary_profile.ITEM_NAME is 'Change'", run_only["record"])


class ReceiptRunRefusalTests(unittest.TestCase):
    """AC-3 (f): a run that can write the receipt refuses while
    WAVEFOUNDRY_TEST_PROFILE is set, before anything runs. The runner under
    test is a scratch copy, so even a regression writes only the copy's
    receipt, never this tree's."""

    def test_a_receipt_writing_run_refuses_while_the_variable_is_set(self) -> None:
        real_receipt = SCRIPTS_DIR.parent / "test-cache.json"
        before = real_receipt.read_bytes() if real_receipt.exists() else None
        with tempfile.TemporaryDirectory() as tmp:
            framework = Path(tmp) / ".wavefoundry" / "framework"
            scripts = copy_scripts_tree(framework)
            ran = Path(tmp) / "ran"
            (scripts / "tests" / "test_planted.py").write_text(
                "import pathlib, unittest\n"
                f"pathlib.Path({str(ran)!r}).write_text('ran')\n"
                "class Planted(unittest.TestCase):\n"
                "    def test_planted(self):\n"
                "        pass\n", encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            env[TEST_PROFILE_ENV] = "second"
            for argv in ([], ["--no-cache"]):
                with self.subTest(argv=argv):
                    result = subprocess.run(
                        [sys.executable, "-B", str(scripts / "run_tests.py"), *argv], cwd=tmp, env=env,
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                    )
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertIn("WAVEFOUNDRY_TEST_PROFILE is set ('second')", result.stderr)
                    self.assertFalse((framework / "test-cache.json").exists())
                    self.assertFalse(ran.exists(), "a test ran before the refusal")
        after = real_receipt.read_bytes() if real_receipt.exists() else None
        self.assertEqual(after, before)

    def test_only_receipt_writing_runs_consult_the_variable(self) -> None:
        self.assertIsNone(run_tests._stray_profile_refusal({}))
        self.assertIn("Unset WAVEFOUNDRY_TEST_PROFILE", run_tests._stray_profile_refusal({TEST_PROFILE_ENV: "x"}))
        # Focused and help runs never reach the refusal.
        with mock.patch.object(run_tests, "_stray_profile_refusal", side_effect=AssertionError("consulted")), \
                mock.patch.object(run_tests, "_execute_files", return_value=(0, [])), \
                mock.patch.object(sys, "argv", ["run_tests.py", "--file", "test_profile_support.py"]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_tests.main(), 0)

    def test_the_refusal_comes_before_any_hashing(self) -> None:
        err = io.StringIO()
        with mock.patch.dict(os.environ, {TEST_PROFILE_ENV: "second"}), \
                mock.patch.object(run_tests, "_hash_inputs", side_effect=AssertionError("hashed")), \
                mock.patch.object(run_tests, "_execute_files", side_effect=AssertionError("ran")), \
                mock.patch.object(sys, "argv", ["run_tests.py"]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(run_tests.main(), 2)
        self.assertIn("WAVEFOUNDRY_TEST_PROFILE", err.getvalue())


class ProfileArgumentTests(unittest.TestCase):
    def _usage(self, *argv: str) -> str:
        with self.assertRaises(run_tests._UsageError) as ctx:
            run_tests._parse_args(["run_tests.py", *argv])
        return str(ctx.exception)

    def test_profile_parses_with_file_selectors(self) -> None:
        opts = run_tests._parse_args(["run_tests.py", "--profile", "second", "--file", "test_a.py"])
        self.assertEqual((opts["profile"], opts["files"]), ("second", ["test_a.py"]))

    def test_profile_is_exclusive_with_the_schedule_control_options(self) -> None:
        for extra in (["--no-cache"], ["--schedule-control", "timing", "--timings-file", "t"], ["--timings-file", "t"]):
            with self.subTest(extra=extra):
                self.assertIn("mutually exclusive", self._usage("--profile", "second", *extra))
        self.assertIn("requires a value", self._usage("--profile"))
        self.assertIn("only once", self._usage("--profile", "second", "--profile", "second"))

    def test_help_documents_the_profile_run(self) -> None:
        self.assertTrue(run_tests._parse_args(["run_tests.py", "--help"])["help"])
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["run_tests.py", "--help"]), contextlib.redirect_stdout(out):
            self.assertEqual(run_tests.main(), 0)
        self.assertIn("--profile NAME", out.getvalue())
        self.assertIn("is not delivery evidence", " ".join(out.getvalue().split()))

    def test_unknown_profile_exits_2(self) -> None:
        err = io.StringIO()
        with mock.patch.object(sys, "argv", ["run_tests.py", "--profile", "absent"]), \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_tests.main(), 2)
        self.assertIn("no profile asset named 'absent'", err.getvalue())


if __name__ == "__main__":
    unittest.main()
