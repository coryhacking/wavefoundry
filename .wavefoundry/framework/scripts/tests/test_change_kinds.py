"""Declared extra change kinds (wave 1zimf, change 1zimp).

The change-kind token of a change id comes from one source,
``vocabulary_profile.CHANGE_KINDS`` (the fixed core kinds plus the
distribution-declared ``EXTRA_CHANGE_KINDS``). Docs-lint, the server and the
``lifecycle_id`` CLI derive from it.

The default-grammar (AC-1) and undeclared-kind (AC-4) cases run in a scratch
copy of the scripts tree with the shipped vocabulary and
``EXTRA_CHANGE_KINDS = ()``, and the declared-kind case (AC-3) in one with
``("decision",)``, so each holds under any test profile.

Wave 1zli8 (change 1zlhx) retires ``feat`` for new change docs: the default
grammar keeps it (AC-3, existing ``-feat`` ids lint unchanged), and
``RETIRED_CHANGE_KINDS`` is the one source of the retired set (AC-6, a scratch
tree retiring ``bug`` instead).
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from record_layout_support import (
    DOCS_LINT_FIXTURE,
    SCRIPTS_DIR,
    SHIPPED_DEFAULTS,
    apply_profile,
    copy_scripts_tree,
    localized_docs_lint_fixture,
    shipped_default_profile,
)
import test_docs_lint as docs_lint_tests  # the fixture's record-reference localizer
import vocabulary_profile

# Today's kinds, frozen: the default grammar must stay exactly this.
FROZEN_KINDS = ("bug", "feat", "enh", "change", "doc", "debt", "ref", "task", "maint", "ops")
# The kinds no creation path mints (wave 1zli8), frozen.
FROZEN_RETIRED = ("feat",)
FROZEN_KIND_PATTERN = r"(?:bug|feat|enh|change|doc|debt|ref|task|maint|ops)"

FIXTURE_CHANGE = "00059-enh fixture-follow-up"
FEAT_CHANGE = "00059-feat fixture-follow-up"
FEAT_PLAN = "00060-feat fixture-plan"
DECISION_CHANGE = "00059-decision fixture-follow-up"
DECISION_PLAN = "00060-decision fixture-plan"


_RETIRED_LINE = re.compile(r"^RETIRED_CHANGE_KINDS(?:[ \t]*:[^=\n]*)?[ \t]*=[ \t]*[^\n]*$", re.MULTILINE)


def _scratch_scripts(tmp: Path, extra_kinds: list, retired_kinds: "tuple | None" = None) -> Path:
    """A copied scripts tree on the shipped vocabulary and layout with
    ``EXTRA_CHANGE_KINDS`` set, whatever profile this run uses. With
    ``retired_kinds``, the fixed ``RETIRED_CHANGE_KINDS`` line is rewritten too
    (it is not a profile constant, so a fork edits source to change it)."""
    profile = shipped_default_profile()
    profile["modules"]["vocabulary_profile"]["EXTRA_CHANGE_KINDS"] = list(extra_kinds)
    scripts = copy_scripts_tree(tmp / "framework")
    apply_profile(scripts, profile, modules=("vocabulary_profile", "record_paths"))
    if retired_kinds is not None:
        path = scripts / "vocabulary_profile.py"
        source = path.read_text(encoding="utf-8")
        assignment = f"RETIRED_CHANGE_KINDS: tuple[str, ...] = {tuple(retired_kinds)!r}"
        rewritten, count = _RETIRED_LINE.subn(lambda _m: assignment, source)
        if count != 1:
            raise AssertionError(f"RETIRED_CHANGE_KINDS is assigned {count} times, expected once")
        path.write_text(rewritten, encoding="utf-8")
    return scripts


def _run_in(scripts: Path, code: str, *args: str, cwd: "Path | None" = None, env: "dict | None" = None) -> dict:
    environ = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    environ.update(env or {})
    environ["PYTHONDONTWRITEBYTECODE"] = "1"
    done = subprocess.run(
        [sys.executable, "-B", "-c", code, str(scripts), *args],
        cwd=str(cwd or scripts), env=environ, capture_output=True, text=True, timeout=300,
    )
    if done.returncode != 0:
        raise AssertionError(f"scratch driver failed:\n{done.stdout[-3000:]}\n{done.stderr[-6000:]}")
    return json.loads(done.stdout.strip().splitlines()[-1])


_PLAN_TEXT = (
    "# Fixture Plan\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-03-21\n\n"
    "Change ID: `{change_id}`\n\n## Rationale\n\nFixture plan for the change-kind checks.\n"
)


def _plant(root: Path, *, old: str, new: str, plan_id: "str | None", waves_dir: Path) -> None:
    """Rename the fixture's follow-up change to ``new`` everywhere, and add a plan."""
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if old in text:
            path.write_text(text.replace(old, new), encoding="utf-8")
    for path in sorted(waves_dir.rglob(f"{old}.md")):
        path.rename(path.with_name(f"{new}.md"))
    if plan_id is not None:
        plans = root / "docs" / "plans"
        plans.mkdir(parents=True, exist_ok=True)
        (plans / f"{plan_id}.md").write_text(_PLAN_TEXT.format(change_id=plan_id), encoding="utf-8")


_LINT_DRIVER = r"""
import json, os, shutil, subprocess, sys
from pathlib import Path
scripts = Path(sys.argv[1])
fixture, root = Path(sys.argv[2]), Path(sys.argv[3])
shutil.copytree(fixture, root)
plant = json.loads(sys.argv[4])
for path in sorted(root.rglob("*.md")):
    text = path.read_text(encoding="utf-8")
    if plant["old"] in text:
        path.write_text(text.replace(plant["old"], plant["new"]), encoding="utf-8")
for path in sorted(root.rglob(plant["old"] + ".md")):
    path.rename(path.with_name(plant["new"] + ".md"))
plans = root / "docs" / "plans"
plans.mkdir(parents=True, exist_ok=True)
for plan_id, text in plant["plans"].items():
    (plans / (plan_id + ".md")).write_text(text, encoding="utf-8")
env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
env["PROJECT_ROOT"] = str(root)
lint = subprocess.run([sys.executable, "-B", str(scripts / "docs_lint.py")], cwd=str(root), env=env,
                      capture_output=True, text=True, timeout=300)
sys.path.insert(0, str(scripts))
os.environ["PROJECT_ROOT"] = str(root)
import vocabulary_profile
from wave_lint_lib import constants
from wave_lint_lib import wave_validators
event = "Source event: `decision-log:" + plant["new"] + ":0123456789abcdef`"
mint = subprocess.run([sys.executable, "-B", str(scripts / "lifecycle_id.py"), "--kind", "decision", "--slug", "minted"],
                      cwd=str(root), env=env, capture_output=True, text=True, timeout=120)
from wf_server import server_impl
created = server_impl.change_doc_response(root, "decision", "made-here")
refused = server_impl.change_doc_response(root, "decison", "typo")
upper = server_impl.change_doc_response(root, "DECISION", "upper")
core = server_impl.change_doc_response(root, "enh", "core-kind")
retired = server_impl.change_doc_response(root, "feat", "retired-kind")
print(json.dumps({
    "kinds": list(vocabulary_profile.CHANGE_KINDS),
    "lint_rc": lint.returncode,
    "lint_out": lint.stdout[-8000:] + lint.stderr[-2000:],
    "event_exempt": bool(wave_validators._DECISION_LOG_SOURCE_EVENT_RE.match(event)),
    "reference": constants.CHANGE_REFERENCE_PATTERN.findall("Change ID: `" + plant["new"] + "`"),
    "mint_rc": mint.returncode,
    "mint_out": mint.stdout.strip(),
    "mint_err": mint.stderr[-2000:],
    "created": created,
    "created_exists": (root / created.get("data", {}).get("path", "missing")).is_file(),
    "refused": refused,
    "upper": upper,
    "core": core,
    "retired": retired,
    "feat_files": sorted(p.name for p in plans.glob("*-feat retired-kind.md")),
}, default=str))
"""


class DefaultGrammarTests(unittest.TestCase):
    """AC-1: with ``EXTRA_CHANGE_KINDS = ()`` the grammar is byte-for-byte today's."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        scripts = _scratch_scripts(Path(cls._tmp.name), [])
        cls.out = _run_in(scripts, r"""
import argparse, json, re, sys
from pathlib import Path
scripts = Path(sys.argv[1])
sys.path.insert(0, str(scripts))
import vocabulary_profile as v
from wave_lint_lib import constants as c
import lifecycle_id
frozen = re.compile(rf"^{v.MEMBER_ID_LABEL_RE}:\s+`({c.LIFECYCLE_PREFIX_PATTERN}-(?:bug|feat|enh|change|doc|debt|ref|task|maint|ops) {c.SLUG_PATTERN})`$", re.MULTILINE)
corpus = [f"{v.MEMBER_ID_LABEL}: `{body}`" for body in (
    "1abcd-feat a", "1abcd-bug x-y", "00000-change z", "1abcde-ops 9", "1abcd-ref r", "1abcd-task t",
    "1abcd-maint m", "1abcd-debt d", "1abcd-doc d", "1abcd-enh e",
    "1abcd-decision a", "1abcd-feature a", "1abcd-Feat a", "1abcd-feat A", "1abcd-feat", "1abc-feat a",
    "1abcd-wave a", "1abcd-mem a", "1abcd-sec a", "1abcd-adr a", "1abcd-feat  a", "1abcd--feat a",
    "1abcd-featx a", "1abcd-xfeat a", "1abcd-feat a b", "1abcd-feat a-", "1abcd-feat\ta",
)] + ["Change ID: `1abcd-feat a`", "Item ID: `1abcd-feat a`", f"{v.MEMBER_ID_LABEL}:  `1abcd-feat a`"]
def accepts(pattern):
    return [bool(pattern.match(line)) for line in corpus]
choices = []
for kind in list(v.CORE_CHANGE_KINDS) + ["wave", "decision"]:
    try:
        lifecycle_id.parse_args(["--kind", kind, "--slug", "s"])
        choices.append(kind)
    except SystemExit:
        pass
from wf_server import server_impl
print(json.dumps({
    "core": list(v.CORE_CHANGE_KINDS), "extra": list(v.EXTRA_CHANGE_KINDS), "kinds": list(v.CHANGE_KINDS),
    "kind_re": v.CHANGE_KIND_RE, "kind_pattern": c.CHANGE_KIND_PATTERN,
    "valid": sorted(server_impl.VALID_CHANGE_KINDS), "valid_type": type(server_impl.VALID_CHANGE_KINDS).__name__,
    "cli_choices": list(lifecycle_id.KIND_CHOICES), "cli_accepts": choices,
    "retired": list(v.RETIRED_CHANGE_KINDS), "mintable": list(v.MINTABLE_CHANGE_KINDS),
    "accepts": accepts(c.CHANGE_ID_PATTERN), "frozen_accepts": accepts(frozen),
    "reference_is_id": c.CHANGE_REFERENCE_PATTERN is c.CHANGE_ID_PATTERN,
    "corpus_size": len(corpus),
}))
""")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_core_kinds_are_todays_kinds_and_extra_is_empty(self):
        self.assertEqual(self.out["core"], list(FROZEN_KINDS))
        self.assertEqual(self.out["extra"], [])
        self.assertEqual(self.out["kinds"], list(FROZEN_KINDS))

    def test_consumers_equal_todays_sets(self):
        self.assertEqual(self.out["kind_pattern"], FROZEN_KIND_PATTERN)
        self.assertEqual(self.out["kind_re"], FROZEN_KIND_PATTERN)
        self.assertEqual(self.out["valid"], sorted(FROZEN_KINDS))
        self.assertEqual(self.out["valid_type"], "frozenset")
        self.assertEqual(self.out["cli_choices"], list(FROZEN_KINDS) + ["wave"])
        self.assertEqual(self.out["cli_accepts"], list(FROZEN_KINDS) + ["wave"])

    def test_the_retired_kinds_are_frozen_and_stay_in_the_grammar(self):
        self.assertEqual(self.out["retired"], list(FROZEN_RETIRED))
        self.assertEqual(self.out["mintable"], [k for k in FROZEN_KINDS if k not in FROZEN_RETIRED])
        for kind in FROZEN_RETIRED:
            self.assertIn(kind, self.out["kinds"])
            self.assertIn(kind, self.out["valid"])

    def test_change_id_pattern_matches_the_frozen_pattern_on_a_fixed_corpus(self):
        self.assertEqual(self.out["accepts"], self.out["frozen_accepts"])
        self.assertGreaterEqual(sum(self.out["frozen_accepts"]), 10)
        self.assertGreaterEqual(self.out["frozen_accepts"].count(False), 15)
        self.assertGreaterEqual(self.out["corpus_size"], 30)
        self.assertTrue(self.out["reference_is_id"])


class ExtraKindValidationTests(unittest.TestCase):
    """AC-2: a bad ``EXTRA_CHANGE_KINDS`` fails closed at import."""

    BAD = {
        "non-tuple": (["decision"], "must be a tuple"),
        "non-string": ((5,), "must be a string"),
        "uppercase": (("Decision",), "must match"),
        "hyphenated": (("my-kind",), "must match"),
        "spaced": (("my kind",), "must match"),
        "one character": (("d",), "must match"),
        "seventeen characters": (("a" * 17,), "must match"),
        "core kind": (("feat",), "is a core change kind"),
        "duplicate": (("decision", "decision"), "is declared twice"),
        "wave": (("wave",), "is reserved"),
        "mem": (("mem",), "is reserved"),
        "sec": (("sec",), "is reserved"),
        "adr": (("adr",), "is reserved"),
        "jrnl": (("jrnl",), "is reserved"),
        "trailing newline": (("decision\n",), "must match"),
    }

    def test_valid_declarations_pass(self):
        for value in ((), ("decision",), ("ab",), ("a" * 16,), ("decision", "spike2")):
            with self.subTest(value=value), mock.patch.object(vocabulary_profile, "EXTRA_CHANGE_KINDS", value):
                self.assertEqual(vocabulary_profile.validation_errors(), [])

    def test_each_bad_declaration_is_refused_naming_the_constant(self):
        for label, (value, needle) in self.BAD.items():
            with self.subTest(case=label), mock.patch.object(vocabulary_profile, "EXTRA_CHANGE_KINDS", value):
                errors = vocabulary_profile.validation_errors()
                self.assertTrue(errors, label)
                self.assertTrue(all("EXTRA_CHANGE_KINDS" in e for e in errors), errors)
                self.assertTrue(any(needle in e for e in errors), errors)

    def test_the_archive_profile_ignores_change_kinds(self):
        archive = {name: getattr(vocabulary_profile, name) for name in vocabulary_profile.FIELD_NAMES}
        self.assertEqual(vocabulary_profile.validation_errors(archive), [])
        self.assertIn("unknown field(s): EXTRA_CHANGE_KINDS",
                      vocabulary_profile.validation_errors({**archive, "EXTRA_CHANGE_KINDS": ()}))

    def test_importing_a_bad_declaration_raises(self):
        source = (SCRIPTS_DIR / "vocabulary_profile.py").read_text(encoding="utf-8")
        pattern = re.compile(r"^EXTRA_CHANGE_KINDS(?:[ \t]*:[^=\n]*)?[ \t]*=[ \t]*[^\n]*$", re.MULTILINE)
        self.assertEqual(len(pattern.findall(source)), 1, "EXTRA_CHANGE_KINDS is assigned on one line")
        for label, (value, needle) in self.BAD.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "vocabulary_profile_copy.py"
                # A function replacement: a string replacement would turn a repr's
                # backslash-n escape into a real newline.
                assignment = f"EXTRA_CHANGE_KINDS = {value!r}"
                path.write_text(pattern.sub(lambda _m: assignment, source), encoding="utf-8")
                spec = importlib.util.spec_from_file_location("vocabulary_profile_copy", path)
                module = importlib.util.module_from_spec(spec)
                with self.assertRaises(Exception) as raised:
                    spec.loader.exec_module(module)
                self.assertEqual(type(raised.exception).__name__, "VocabularyProfileInvalid")
                self.assertIn("EXTRA_CHANGE_KINDS", str(raised.exception))
                self.assertIn(needle, str(raised.exception))


class DeclaredKindTests(unittest.TestCase):
    """AC-3: a declared kind works end to end in a scratch tree."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        scripts = _scratch_scripts(base, ["decision"])
        plant = {"old": FIXTURE_CHANGE, "new": DECISION_CHANGE,
                 "plans": {DECISION_PLAN: _PLAN_TEXT.format(change_id=DECISION_PLAN)}}
        cls.out = _run_in(scripts, _LINT_DRIVER, str(DOCS_LINT_FIXTURE), str(base / "repo"), json.dumps(plant))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_kinds_include_the_declared_kind(self):
        self.assertEqual(self.out["kinds"], list(FROZEN_KINDS) + ["decision"])

    def test_a_plan_and_a_wave_record_using_it_lint_clean(self):
        self.assertEqual(self.out["lint_rc"], 0, self.out["lint_out"])
        self.assertIn("docs-lint: ok", self.out["lint_out"])

    def test_the_decision_log_source_event_exemption_and_references_accept_it(self):
        self.assertTrue(self.out["event_exempt"])
        self.assertEqual(self.out["reference"], [DECISION_CHANGE])

    def test_the_cli_mints_an_id_of_the_declared_kind(self):
        self.assertEqual(self.out["mint_rc"], 0, self.out["mint_err"])
        self.assertRegex(self.out["mint_out"], r"^[0-9a-z]{5,6}-decision minted$")

    def test_change_doc_response_creates_the_doc_with_the_wf_new_envelope(self):
        created = self.out["created"]
        self.assertEqual(created["status"], "ok", created)
        self.assertTrue({"change_id", "created", "exists", "kind", "mode", "path", "slug"} <= set(created["data"]))
        self.assertEqual(created["data"]["kind"], "decision")
        self.assertTrue(created["data"]["change_id"].endswith("-decision made-here"))
        self.assertTrue(created["data"]["created"])
        self.assertTrue(self.out["created_exists"])
        self.assertEqual(self.out["core"]["status"], "ok")
        self.assertEqual(self.out["core"]["data"]["kind"], "enh")
        self.assertEqual(sorted(self.out["core"]["data"]), sorted(created["data"]))

    def test_change_doc_response_refuses_the_retired_core_kind(self):
        retired = self.out["retired"]
        self.assertEqual(retired["status"], "error", retired)
        self.assertEqual([d["code"] for d in retired["diagnostics"]], ["change_kind_retired"])
        self.assertEqual(self.out["feat_files"], [])

    def test_other_kinds_are_refused_with_invalid_arguments(self):
        for label in ("refused", "upper"):
            with self.subTest(case=label):
                result = self.out[label]
                self.assertEqual(result["status"], "error")
                self.assertEqual([d["code"] for d in result["diagnostics"]], ["invalid_arguments"])


class ExistingFeatIdsTests(unittest.TestCase):
    """Wave 1zli8 AC-3: a plan, change doc and wave record using ``-feat`` lint
    clean under the default grammar, although ``feat`` is retired for new docs."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        scripts = _scratch_scripts(base, [])
        plant = {"old": FIXTURE_CHANGE, "new": FEAT_CHANGE,
                 "plans": {FEAT_PLAN: _PLAN_TEXT.format(change_id=FEAT_PLAN)}}
        cls.out = _run_in(scripts, _LINT_DRIVER, str(DOCS_LINT_FIXTURE), str(base / "repo"), json.dumps(plant))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_the_feat_plan_change_doc_and_wave_record_lint_clean(self):
        self.assertEqual(self.out["lint_rc"], 0, self.out["lint_out"])
        self.assertIn("docs-lint: ok", self.out["lint_out"])
        self.assertEqual(self.out["reference"], [FEAT_CHANGE])
        self.assertTrue(self.out["event_exempt"])


_RETIRED_DRIVER = r"""
import json, os, subprocess, sys
from pathlib import Path
scripts, root = Path(sys.argv[1]), Path(sys.argv[2])
(root / "docs").mkdir(parents=True)
(root / "docs" / "workflow-config.json").write_text(
    json.dumps({"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}), encoding="utf-8")
env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
mint = {kind: subprocess.run([sys.executable, "-B", str(scripts / "lifecycle_id.py"), "--kind", kind, "--slug", "x"],
                             cwd=str(root), env=env, capture_output=True, text=True, timeout=120)
        for kind in ("bug", "feat")}
sys.path.insert(0, str(scripts))
import vocabulary_profile
from wf_server import server_impl
helper = server_impl.change_doc_response(root, "bug", "via-helper")
plans = root / "docs" / "plans"
helper_files = sorted(p.name for p in plans.glob("*-bug *.md")) if plans.is_dir() else []
import server
mcp = server.build_server(root)
tools = mcp._tool_manager._tools
new_bug = tools["wf_new_bug"].fn(slug="via-tool")
new_feature = tools["wf_new_feature"].fn(slug="via-tool")
print(json.dumps({
    "retired": list(vocabulary_profile.RETIRED_CHANGE_KINDS),
    "mintable": list(vocabulary_profile.MINTABLE_CHANGE_KINDS),
    "message": vocabulary_profile.retired_kind_message("bug"),
    "mint": {k: [r.returncode, r.stdout.strip(), r.stderr[-2000:]] for k, r in mint.items()},
    "helper": helper, "helper_files": helper_files,
    "new_bug": new_bug, "new_feature": new_feature,
    "feature_exists": (root / new_feature.get("data", {}).get("path", "missing")).is_file(),
}, default=str))
"""


class RetiredKindsSingleSourceTests(unittest.TestCase):
    """Wave 1zli8 AC-6: every creation surface reads ``RETIRED_CHANGE_KINDS``;
    a scratch tree that retires ``bug`` instead refuses ``bug`` and mints ``feat``."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        scripts = _scratch_scripts(base, [], retired_kinds=("bug",))
        cls.out = _run_in(scripts, _RETIRED_DRIVER, str(base / "repo"))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_the_scratch_tree_retires_bug_only(self):
        self.assertEqual(self.out["retired"], ["bug"])
        self.assertEqual(self.out["mintable"], [k for k in FROZEN_KINDS if k != "bug"])

    def test_wf_new_bug_and_the_helper_refuse_bug(self):
        for label in ("new_bug", "helper"):
            with self.subTest(surface=label):
                result = self.out[label]
                self.assertEqual(result["status"], "error", result)
                self.assertEqual([d["code"] for d in result["diagnostics"]], ["change_kind_retired"])
                self.assertEqual(result["diagnostics"][0]["message"], self.out["message"])
        self.assertEqual(self.out["helper_files"], [])

    def test_the_cli_refuses_bug_and_mints_feat(self):
        rc, stdout, stderr = self.out["mint"]["bug"]
        self.assertEqual(rc, 2, stderr)
        self.assertEqual(stdout, "")
        self.assertIn(self.out["message"], stderr)
        rc, stdout, stderr = self.out["mint"]["feat"]
        self.assertEqual(rc, 0, stderr)
        self.assertRegex(stdout, r"^[0-9a-z]{5,6}-feat x$")

    def test_wf_new_feature_mints_again(self):
        result = self.out["new_feature"]
        self.assertEqual(result["status"], "ok", result)
        self.assertTrue(result["data"]["change_id"].endswith("-feat via-tool"))
        self.assertTrue(self.out["feature_exists"])


class UndeclaredKindTests(unittest.TestCase):
    """AC-4: an undeclared kind lints by name; other malformed ids keep today's messages."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        scripts = _scratch_scripts(base, [])
        plant = {"old": FIXTURE_CHANGE, "new": DECISION_CHANGE, "plans": {
            DECISION_PLAN: _PLAN_TEXT.format(change_id=DECISION_PLAN),
            "not-an-id": _PLAN_TEXT.format(change_id="not an id"),
        }}
        cls.out = _run_in(scripts, _LINT_DRIVER, str(DOCS_LINT_FIXTURE), str(base / "repo"), json.dumps(plant))
        # A wave record whose malformed member id is not change-id shaped.
        malformed = {"old": FIXTURE_CHANGE, "new": "00059-Enh Fixture", "plans": {}}
        cls.malformed = _run_in(scripts, _LINT_DRIVER, str(DOCS_LINT_FIXTURE), str(base / "malformed"),
                                json.dumps(malformed))
        # An uppercase kind with a valid slug is not change-id shaped either.
        upper = {"old": FIXTURE_CHANGE, "new": "00059-Feat fixture", "plans": {}}
        cls.upper = _run_in(scripts, _LINT_DRIVER, str(DOCS_LINT_FIXTURE), str(base / "upper"),
                            json.dumps(upper))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_the_change_doc_plan_and_wave_record_name_the_undeclared_kind(self):
        out = self.out["lint_out"]
        self.assertNotEqual(self.out["lint_rc"], 0)
        lines = [line for line in out.splitlines() if "uses undeclared change kind 'decision'" in line]
        self.assertTrue(any(f"plans/{DECISION_PLAN}.md" in line for line in lines), out)
        # The scratch tree is on the shipped vocabulary whatever the run profile.
        record = SHIPPED_DEFAULTS["vocabulary_profile"]["RECORD_FILENAME"]
        self.assertTrue(any(f"change-2026-03/{record}:" in line for line in lines), out)
        self.assertTrue(any(f"{DECISION_CHANGE}.md" in line for line in lines), out)
        for line in lines:
            self.assertIn("vocabulary_profile.EXTRA_CHANGE_KINDS", line)
            self.assertIn(", ".join(FROZEN_KINDS), line)

    def test_the_misleading_messages_are_gone_for_those_lines(self):
        out = self.out["lint_out"]
        self.assertNotIn(f"unstable Change ID `{DECISION_CHANGE}`", out)
        self.assertFalse([line for line in out.splitlines()
                          if f"plans/{DECISION_PLAN}.md" in line and "is missing a" in line], out)

    def test_a_malformed_id_that_is_not_change_shaped_keeps_todays_message(self):
        out = self.out["lint_out"]
        self.assertTrue([line for line in out.splitlines()
                         if "plans/not-an-id.md" in line and "plan is missing a `Change ID:`" in line], out)
        malformed = self.malformed["lint_out"]
        # Wave 1zxo0 (1zxns): the line number and reason class, never the value.
        self.assertRegex(malformed, r"unstable Change ID on line \d+ \(shape\)")
        self.assertNotIn("unstable Change ID `00059-Enh Fixture`", malformed)
        self.assertNotIn("undeclared change kind", malformed)
        upper = self.upper["lint_out"]
        self.assertRegex(upper, r"unstable Change ID on line \d+ \(shape\)")
        self.assertNotIn("00059-Feat fixture`", upper.split("unstable", 1)[-1].split("\n", 1)[0])
        self.assertNotIn("undeclared change kind", upper)

    def test_change_doc_response_refuses_the_undeclared_kind(self):
        refused = self.out["created"]
        self.assertEqual(refused["status"], "error")
        self.assertEqual([d["code"] for d in refused["diagnostics"]], ["invalid_arguments"])
        self.assertEqual(self.out["core"]["status"], "ok")


class LoadedProfileDecisionKindTests(unittest.TestCase):
    """Requirement 7: under the loaded profile (``--profile second`` declares
    ``decision``) a planted ``decision`` change doc lints clean; under a
    profile that does not declare it, it lints by name."""

    def test_planted_decision_change_doc_under_the_loaded_profile(self):
        import record_paths
        root = Path(tempfile.mkdtemp(prefix="wave-change-kinds-"))
        root.rmdir()
        try:
            localized_docs_lint_fixture(root)
            for rel in docs_lint_tests._FIXTURE_RECORD_REFERENCE_DOCS:
                doc = root / rel
                doc.write_text(docs_lint_tests._v(doc.read_text(encoding="utf-8")), encoding="utf-8")
            waves_dir = root / Path(record_paths.WAVES_ROOT)
            _plant(root, old=FIXTURE_CHANGE, new=DECISION_CHANGE, plan_id=None, waves_dir=waves_dir)
            planted = list(waves_dir.rglob(f"{DECISION_CHANGE}.md"))
            env = os.environ.copy()
            env["PROJECT_ROOT"] = str(root)
            env["PYTHONPATH"] = str(SCRIPTS_DIR) + os.pathsep + env.get("PYTHONPATH", "")
            result = subprocess.run([sys.executable, "-B", str(SCRIPTS_DIR / "docs_lint.py")],
                                    cwd=str(root), env=env, text=True, capture_output=True, timeout=300)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(len(planted), 1)
        if "decision" in vocabulary_profile.CHANGE_KINDS:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("docs-lint: ok", result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("uses undeclared change kind 'decision'", result.stdout + result.stderr)


# --- Census (AC-5) ------------------------------------------------------------

_CORE = frozenset(FROZEN_KINDS)
_ALTERNATION = re.compile(r"\b(?:" + "|".join(FROZEN_KINDS) + r")\|(?:" + "|".join(FROZEN_KINDS) + r")\b")
_JS_QUOTED = re.compile(r"""["'](""" + "|".join(FROZEN_KINDS) + r""")["']""")
# The one source of kinds; the per-kind wf_new_<kind> registrations name a
# single kind each and are not collections, so they never match.
CENSUS_ALLOWED = {"vocabulary_profile.py"}


def kind_list_sites(paths: "list[Path]", base: Path) -> "list[str]":
    """``path:line`` of every kind literal list (three or more core kinds as
    string elements of one tuple, list or set) or kind alternation in a
    string, in ``.py`` and ``.js`` files."""
    sites: list[str] = []
    for path in paths:
        rel = path.relative_to(base).as_posix()
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
                    kinds = {e.value for e in node.elts if isinstance(e, ast.Constant) and e.value in _CORE}
                    if len(kinds) >= 3:
                        sites.append(f"{rel}:{node.lineno}")
                elif isinstance(node, ast.Constant) and isinstance(node.value, str) and _ALTERNATION.search(node.value):
                    sites.append(f"{rel}:{node.lineno}")
        else:
            for match in _ALTERNATION.finditer(text):
                sites.append(f"{rel}:{text.count(chr(10), 0, match.start()) + 1}")
            hits = [(m.start(), m.group(1)) for m in _JS_QUOTED.finditer(text)]
            for i, (start, _kind) in enumerate(hits):
                window = {k for s, k in hits[i:] if s - start <= 200}
                if len(window) >= 3:
                    sites.append(f"{rel}:{text.count(chr(10), 0, start) + 1}")
                    break
    return sorted(set(sites))


def census_paths() -> "list[Path]":
    framework = SCRIPTS_DIR.parent
    scripts = [p for p in sorted(SCRIPTS_DIR.rglob("*.py"))
               if "tests" not in p.relative_to(SCRIPTS_DIR).parts
               and "__pycache__" not in p.parts and "benchmarks" not in p.relative_to(SCRIPTS_DIR).parts]
    dashboard = sorted((framework / "dashboard").glob("*.js"))
    return scripts + dashboard


class KindCensusTests(unittest.TestCase):
    """AC-5: one source of kinds stays one source."""

    def test_no_kind_list_outside_the_profile(self):
        framework = SCRIPTS_DIR.parent
        sites = kind_list_sites(census_paths(), framework)
        outside = [s for s in sites if s.split(":")[0].removeprefix("scripts/") not in CENSUS_ALLOWED]
        self.assertEqual(outside, [], "derive change kinds from vocabulary_profile.CHANGE_KINDS")
        self.assertTrue([s for s in sites if s.startswith("scripts/vocabulary_profile.py:")],
                        "the census must see the one allowed source, or it scans nothing")

    def test_the_census_scans_scripts_and_dashboard_assets_only(self):
        rels = {p.relative_to(SCRIPTS_DIR.parent).as_posix() for p in census_paths()}
        self.assertIn("scripts/wave_lint_lib/constants.py", rels)
        self.assertIn("scripts/wf_server/server_impl.py", rels)
        self.assertIn("dashboard/dashboard.js", rels)
        self.assertFalse([r for r in rels if r.startswith("scripts/tests/") or r.startswith("seeds/")])

    def test_the_census_detects_each_shape(self):
        samples = {
            "tuple.py": 'KINDS = ("bug", "feat", "enh")\n',
            "nested.py": 'def f():\n    return {"doc", "debt", "ref", "x"}\n',
            "multiline.py": 'K = [\n    "task",\n    "maint",\n    "ops",\n]\n',
            "alternation.py": 'P = r"(?:feat|bug)"\n',
            "array.js": 'const kinds = ["bug", "feat",\n  "enh"];\n',
            "regex.js": "const re = /-(?:feat|enh) /;\n",
        }
        clean = {
            "single.py": '_new("feat", slug)\n_new("bug", slug)\n',
            "prose.py": 'DOC = "Prefer feat, bug, enh, ref or doc first."\n',
            "tokens.py": 'LANES = ("-feat ", "-enh ", "-bug ")\n',
            "split.js": 'a("bug");\n// ' + "x" * 250 + '\nb("feat");\n// ' + "y" * 250 + '\nc("enh");\n',
        }
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name, text in {**samples, **clean}.items():
                (base / name).write_text(text, encoding="utf-8")
            found = {s.split(":")[0] for s in kind_list_sites(sorted(base.iterdir()), base)}
        self.assertEqual(found, set(samples))


if __name__ == "__main__":
    unittest.main()
