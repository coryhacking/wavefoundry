"""Vocabulary-derived lifecycle prompt names (wave 1zyb4, change 1zxnw).

``vocabulary_profile.PROMPT_NAME_OVERRIDES`` renames the eleven tier-named
lifecycle prompts; every consumer reads the derived names, and the renderer
moves already-rendered prompts, recording the applied names under
``prompt_names`` in the prompt-surface manifest.

Default pins (AC-1, AC-3, the per-template identity of AC-4) are marked
default-profile-only. Every profile test copies the scripts tree, applies the
``prompt-names`` asset to the copy the way a fork does, and runs a fresh
interpreter over it, so the module-level derived constants are the profile's.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from record_layout_support import (
    DOCS_LINT_FIXTURE,
    apply_profile,
    copy_scripts_tree,
    default_profile_only,
    load_profile,
    shipped_default_profile,
)

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPTS_DIR.parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import vocabulary_profile  # noqa: E402

PROFILE = load_profile("prompt-names")
OVERRIDES = PROFILE["modules"]["vocabulary_profile"]["PROMPT_NAME_OVERRIDES"]

# The pre-change literal table (AC-1).
DEFAULT_TABLE = {
    "plan-change": ("plan-change", "Plan change", ()),
    "create-wave": ("create-wave", "Create wave", ()),
    "add-change-to-wave": ("add-change-to-wave", "Add change to wave", ()),
    "remove-change-from-wave": ("remove-change-from-wave", "Remove change from wave", ()),
    "prepare-wave": ("prepare-wave", "Prepare wave", ("Ready wave",)),
    "implement-wave": ("implement-wave", "Implement wave", ()),
    "implement-change": ("implement-change", "Implement change", ()),
    "pause-wave": ("pause-wave", "Pause wave", ()),
    "review-wave": ("review-wave", "Review wave", ()),
    "close-wave": ("close-wave", "Close wave", ()),
    "close-change": ("close-change", "Close change", ()),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_digest(root: Path) -> "dict[str, str]":
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(root).parts:
            out[path.relative_to(root).as_posix()] = _sha(path)
    return out


def _scripts_tree(dest: Path, profile: "dict | None") -> Path:
    scripts = copy_scripts_tree(dest, with_support=False)
    apply_profile(scripts, shipped_default_profile())
    if profile is not None:
        apply_profile(scripts, profile)
    return scripts


# One child interpreter per call: ``sys.argv[1]`` the scripts tree, then a JSON
# job list. Each job names an action and a root; the output is one JSON line.
DRIVER = r'''
import json, os, shutil, subprocess, sys
from pathlib import Path
scripts = Path(sys.argv[1])
sys.path.insert(0, str(scripts))
import render_agent_surfaces as ras
import vocabulary_profile as vp

class Crash(BaseException):
    pass

def digest(root):
    import hashlib
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out

def render(root):
    try:
        return {"written": ras.render_agent_surfaces(root)}
    except RuntimeError as exc:
        return {"error": str(exc)}

def crashing(root, point, index):
    """Render with an interruption at ``point`` number ``index``; True when it fired."""
    count = {"n": 0}
    fired = {"v": False}
    def hit():
        count["n"] += 1
        if count["n"] == index:
            fired["v"] = True
            raise Crash()
    patches = []
    if point == "after_copy":
        original = ras._write_review_carrier_text
        def wrapper(path, content, *, exclusive=False):
            original(path, content, exclusive=exclusive)
            if exclusive and isinstance(content, bytes):
                hit()
        patches.append(("_write_review_carrier_text", wrapper))
    elif point == "after_move":
        original_move = ras._move_prompt_pair
        def wrapper(repo_root, pair):
            done = original_move(repo_root, pair)
            if done:
                hit()
            return done
        patches.append(("_move_prompt_pair", wrapper))
    elif point == "before_record":
        original_record = ras._record_applied_prompt_name
        def wrapper(repo_root, key, applied_slug):
            hit()
            return original_record(repo_root, key, applied_slug)
        patches.append(("_record_applied_prompt_name", wrapper))
    saved = {name: getattr(ras, name) for name, _ in patches}
    for name, value in patches:
        setattr(ras, name, value)
    try:
        ras.render_agent_surfaces(root)
    except Crash:
        pass
    finally:
        for name, value in saved.items():
            setattr(ras, name, value)
    return fired["v"]

jobs = json.loads(sys.argv[2])
out = []
for job in jobs:
    root = Path(job["root"])
    action = job["action"]
    if action == "render":
        out.append(render(root))
    elif action == "migrate":
        try:
            result = ras.migrate_profile_prompt_names(root)
            out.append({"written": list(result.written), "links": list(result.link_report),
                        "diagnostics": list(result.diagnostics)})
        except RuntimeError as exc:
            out.append({"error": str(exc)})
    elif action == "crash_sweep":
        base = Path(job["base"])
        results = []
        for point in ("after_copy", "after_move", "before_record"):
            index = 1
            while True:
                work = Path(job["work"]) / f"{point}-{index}"
                shutil.copytree(base, work, symlinks=True)
                fired = crashing(work, point, index)
                if not fired:
                    shutil.rmtree(work)
                    break
                rerun = render(work)
                results.append({"point": point, "index": index, "rerun": rerun,
                                "digest": digest(work), "root": str(work)})
                index += 1
        out.append({"results": results})
    elif action == "constants":
        import context_efficiency, reconcile_scan, review_policy, review_policy_reconcile
        from wave_lint_lib import constants as lint_constants
        out.append({
            "names": vp.PROMPT_NAMES,
            "context_destination": ras.CONTEXT_EFFICIENCY_DESTINATION,
            "baselines": [list(row) for row in ras.LIFECYCLE_PROMPT_BASELINES],
            "close_change": [ras.CLOSE_CHANGE_PROMPT, ras.CLOSE_CHANGE_SHORTCUT],
            "skills": {skill.name: [skill.description, skill.body] for skill in ras.SKILL_REGISTRY},
            "stale": list(ras.stale_skill_paths()),
            "blocks": review_policy.REVIEW_POLICY_SURFACE_BLOCKS,
            "carriers": sorted({c.destination for c in review_policy.REVIEW_POLICY_CARRIER_REGISTRY}),
            "known": sorted(review_policy_reconcile.KNOWN_SECTION_REPLACEMENTS),
            "known_text": json.dumps(review_policy_reconcile.KNOWN_SECTION_REPLACEMENTS),
            "lifecycle_map": {k: str(v).replace(os.sep, "/") for k, v in context_efficiency.LIFECYCLE_PROMPT_MAP.items()},
            "surface_files": list(lint_constants.PROMPT_SURFACE_FILES),
            "finalize": reconcile_scan._RETIRED_FINALIZE_PROMPT_SUGGESTION,
            "close_or_wave": reconcile_scan._CLOSE_CHANGE_OR_WAVE_SUGGESTION,
            "change_patterns": [[r, s] for _p, r, s in reconcile_scan._RETIRED_CHANGE_PROMPT_PATTERNS],
            "cursor": ras.CURSOR_AUTO_GURU_MDC,
            "guru": ras.CLAUDE_GURU_AGENT,
            "localized": {key: vp.localize_prompt_template(key, "# Heading\n\nOwner: x\nShortcut: **`Old`**\nBody.\n")
                          for key in vp.DEFAULT_PROMPT_NAMES},
        })
    elif action == "unlink_fail":
        # The first prompt-file unlink (a move's source) raises, as a locked
        # file does on Windows; every later unlink (the rollback) succeeds.
        import pathlib
        original_unlink = pathlib.Path.unlink
        failed = []
        def failing_unlink(self, *args, **kwargs):
            if not failed and self.name.endswith(".prompt.md"):
                failed.append(self.relative_to(root.resolve()).as_posix())
                raise PermissionError(13, "locked by another process", str(self))
            return original_unlink(self, *args, **kwargs)
        pathlib.Path.unlink = failing_unlink
        try:
            result = render(root)
        finally:
            pathlib.Path.unlink = original_unlink
        out.append({"result": result, "failed": failed})
    elif action == "scan":
        import reconcile_scan
        out.append([[f.file, f.line, f.retired_surface, f.matched, f.suggested]
                    for f in reconcile_scan.scan_repo(root)])
    elif action == "lint":
        env = dict(os.environ, PROJECT_ROOT=str(root), PYTHONPATH=str(scripts))
        lint = subprocess.run([sys.executable, "-B", str(scripts / "docs_lint.py")], env=env,
                              text=True, capture_output=True, check=False)
        from wave_lint_lib.core_validators import check_prompt_name_migration
        out.append({"rc": lint.returncode, "output": lint.stdout + lint.stderr,
                    "pending": check_prompt_name_migration(root)})
print(json.dumps(out))
'''


def _drive(scripts: Path, jobs: list) -> "tuple[list, str]":
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-B", "-c", DRIVER, str(scripts), json.dumps(jobs)],
        env=env, text=True, capture_output=True, check=False, timeout=900,
    )
    if result.returncode != 0:
        raise AssertionError(f"driver failed ({result.returncode}):\n{result.stderr[-6000:]}")
    return json.loads(result.stdout.strip().splitlines()[-1]), result.stderr


MANIFEST_DOCS = (
    "plan-change", "create-wave", "add-change-to-wave", "remove-change-from-wave", "prepare-wave",
    "implement-wave", "implement-change", "pause-wave", "review-wave", "memory-review", "close-wave",
    "close-change", "review-plan",
)
AGENT_BODIES = ("plan-change", "implement-change", "implement-wave", "prepare-wave", "close-wave")
LINK_DOC = "docs/references/prompt-links.md"
# Authored prose, not baselines: CRLF line endings on the item implement prompt.
IMPLEMENT_CHANGE_BYTES = (
    b"# Implement Change\r\n\r\nOwner: Local team\r\nStatus: active\r\nLast verified: 2026-01-01\r\n\r\n"
    b"Shortcut: **`Implement change`**\r\n\r\nProject single-change implementation prose.\r\n"
)


def _authored(title: str) -> str:
    return (f"# {title}\n\nOwner: Local team\nStatus: active\nLast verified: 2026-01-01\n\n"
            f"Project prose for {title}.\n")


def build_fixture(default_scripts: Path, root: Path, *, close_change: bool = True) -> Path:
    """A lint-clean target rendered under the defaults, with every mapped
    public prompt, five agent bodies, a manifest and a link to the container
    implement prompt. ``close_change=False`` drops the Close change prompt and
    its manifest entry (the 1zyc5 repair case)."""
    shutil.copytree(DOCS_LINT_FIXTURE, root)
    for host in (".claude", ".codex", ".agents"):
        (root / host).mkdir()
    (out,), _stderr = _drive(default_scripts, [{"action": "render", "root": str(root)}])
    assert "error" not in out, out
    prompts = root / "docs" / "prompts"
    for slug, title in (("add-change-to-wave", "Add Change To Wave"),
                        ("remove-change-from-wave", "Remove Change From Wave"),
                        ("pause-wave", "Pause Wave")):
        (prompts / f"{slug}.prompt.md").write_text(_authored(title), encoding="utf-8")
    (prompts / "implement-change.prompt.md").write_bytes(IMPLEMENT_CHANGE_BYTES)
    for slug in AGENT_BODIES:
        (prompts / "agents").mkdir(exist_ok=True)
        (prompts / "agents" / f"{slug}.prompt.md").write_text(
            _authored(f"Agent body {slug}"), encoding="utf-8")
    link = root / LINK_DOC
    link.write_text(_authored("Prompt Links").replace(
        "Project prose for Prompt Links.",
        "See [the implement prompt](../prompts/implement-wave.prompt.md) for the steps."),
        encoding="utf-8")
    manifest_path = prompts / "prompt-surface-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = list(manifest["public_prompt_surface"])
    known = {entry["doc"] for entry in entries}
    shortcuts = {key: shortcut for key, (_slug, shortcut, _aliases) in DEFAULT_TABLE.items()}
    shortcuts.update({"memory-review": "Review memories", "review-plan": "Review plan"})
    for slug in MANIFEST_DOCS:
        doc = f"docs/prompts/{slug}.prompt.md"
        if doc not in known:
            entries.append({"doc": doc, "shortcut": shortcuts[slug]})
    if not close_change:
        entries = [e for e in entries if e["doc"] != "docs/prompts/close-change.prompt.md"]
        (prompts / "close-change.prompt.md").unlink()
    manifest["public_prompt_surface"] = entries
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return root


class _Trees:
    """Shared scratch trees: the shipped defaults and the prompt-names asset."""

    tmp: "tempfile.TemporaryDirectory | None" = None

    @classmethod
    def get(cls) -> "tuple[Path, Path, Path]":
        if cls.tmp is None:
            cls.tmp = tempfile.TemporaryDirectory()
            base = Path(cls.tmp.name)
            cls.default = _scripts_tree(base / "default", None)
            cls.profiled = _scripts_tree(base / "profiled", PROFILE)
            cls.base = base
        return cls.default, cls.profiled, cls.base


# ---------------------------------------------------------------------------
# AC-1: default literal pins
# ---------------------------------------------------------------------------

@default_profile_only("pins the shipped prompt names and their pre-change consumer literals")
class DefaultNamePinTests(unittest.TestCase):
    def test_prompt_names_equal_the_literal_table(self) -> None:
        self.assertEqual(vocabulary_profile.PROMPT_NAME_OVERRIDES, {})
        self.assertEqual(
            {key: (e["slug"], e["shortcut"], tuple(e["aliases"])) for key, e in vocabulary_profile.PROMPT_NAMES.items()},
            DEFAULT_TABLE)
        self.assertEqual(list(vocabulary_profile.PROMPT_NAMES), list(DEFAULT_TABLE))

    def test_consumers_equal_their_pre_change_literals(self) -> None:
        import context_efficiency
        import reconcile_scan
        import render_agent_surfaces as ras
        import review_policy
        import review_policy_reconcile
        from wave_lint_lib import constants as lint_constants

        self.assertEqual(ras.CONTEXT_EFFICIENCY_DESTINATION, "docs/prompts/create-wave.prompt.md")
        self.assertEqual(ras.LIFECYCLE_PROMPT_BASELINES, (
            ("docs/prompts/create-wave.prompt.md", "create-wave.prompt.md"),
            ("docs/prompts/implement-wave.prompt.md", "implement-wave.prompt.md"),
            ("docs/prompts/memory-review.prompt.md", "memory-review.prompt.md"),
            ("docs/prompts/prepare-wave.prompt.md", "prepare-wave.prompt.md"),
            ("docs/prompts/review-wave.prompt.md", "review-wave.prompt.md"),
            ("docs/prompts/close-wave.prompt.md", "close-wave.prompt.md"),
            ("docs/prompts/review-plan.prompt.md", "review-plan.prompt.md"),
            ("docs/prompts/close-change.prompt.md", "close-change.prompt.md"),
        ))
        self.assertEqual((ras.CLOSE_CHANGE_PROMPT, ras.CLOSE_CHANGE_SHORTCUT),
                         ("docs/prompts/close-change.prompt.md", "Close change"))
        self.assertEqual([s.name for s in ras.SKILL_REGISTRY], [
            "wf-plan-change", "wf-prepare-wave", "wf-implement-wave", "wf-review-wave", "wf-close-wave",
            "wf-close-change", "wf-review-plan", "wf-evaluate-decision", "wf-memory-review", "wf-pause-wave",
            "wf-council", "wf-guru", "wf-upgrade", "wf-package", "wf-code-cleanup", "wf-techdocs",
        ])
        self.assertEqual(ras.stale_skill_paths(), ras.STALE_SKILL_PATHS)
        self.assertIn("The Prepare wave / Ready wave workflow.", ras.SKILL_REGISTRY[1].description)
        self.assertIn("Single-change variant: Implement change (`docs/prompts/implement-change.prompt.md`).",
                      ras.SKILL_REGISTRY[2].body)
        self.assertIn("(**Plan change**, **Implement wave**, **Close wave**, etc.)", ras.CURSOR_AUTO_GURU_MDC)
        self.assertIn("(Plan change, Implement wave, Close wave, Prepare wave, etc.)", ras.CLAUDE_GURU_AGENT)
        self.assertEqual(list(review_policy.REVIEW_POLICY_SURFACE_BLOCKS)[:5], [
            "docs/prompts/prepare-wave.prompt.md", "docs/prompts/review-wave.prompt.md",
            "docs/prompts/close-wave.prompt.md", "docs/prompts/implement-wave.prompt.md",
            "docs/prompts/agents/review-wave.prompt.md",
        ])
        blocks = review_policy.REVIEW_POLICY_SURFACE_BLOCKS
        self.assertIn("\nPrepare Wave is the single readiness authority. It evaluates",
                      blocks["docs/prompts/prepare-wave.prompt.md"])
        self.assertIn("\nReview Wave consumes the shared", blocks["docs/prompts/review-wave.prompt.md"])
        self.assertIn("\nClose Wave consumes the same", blocks["docs/prompts/close-wave.prompt.md"])
        self.assertIn("\nPrepare Wave is the single readiness authority. Implementation",
                      blocks["docs/prompts/implement-wave.prompt.md"])
        destinations = [c.destination for c in review_policy.REVIEW_POLICY_CARRIER_REGISTRY]
        self.assertEqual(destinations[:12], [
            "docs/prompts/prepare-wave.prompt.md", "docs/prompts/review-wave.prompt.md",
            "docs/prompts/close-wave.prompt.md", "docs/prompts/upgrade-wavefoundry.prompt.md",
            "docs/prompts/implement-wave.prompt.md", "docs/prompts/review-wave.prompt.md",
            "docs/prompts/agents/review-wave.prompt.md", "docs/prompts/council-review.prompt.md",
            "docs/prompts/prepare-wave.prompt.md", "docs/prompts/implement-wave.prompt.md",
            "docs/prompts/agents/review-wave.prompt.md", "docs/prompts/council-review.prompt.md",
        ])
        self.assertEqual(destinations[-4:-1], [
            "docs/prompts/review-wave.prompt.md", "docs/prompts/agents/review-wave.prompt.md",
            "docs/prompts/create-wave.prompt.md",
        ])
        self.assertEqual(review_policy.REVIEW_POLICY_OBLIGATION_ANCHORS["single_prepare"],
                         ("is the single readiness authority", "prepare is the single"))
        self.assertEqual(list(review_policy_reconcile.KNOWN_SECTION_REPLACEMENTS), [
            "docs/prompts/implement-wave.prompt.md", "docs/prompts/review-wave.prompt.md",
            "docs/prompts/agents/review-wave.prompt.md", "docs/prompts/council-review.prompt.md",
            "docs/prompts/prepare-wave.prompt.md", "docs/prompts/upgrade-wavefoundry.prompt.md",
        ])
        implement = review_policy_reconcile.KNOWN_SECTION_REPLACEMENTS["docs/prompts/implement-wave.prompt.md"]
        self.assertTrue(implement[0][1].endswith("run afterward through **Review wave**."))
        self.assertIn("**Prepare wave** owns the one pre-code critique", implement[2][1])
        self.assertIn("participates during **Review wave** after", implement[3][1])
        prepare = review_policy_reconcile.KNOWN_SECTION_REPLACEMENTS["docs/prompts/prepare-wave.prompt.md"]
        self.assertIn("`Prepare wave` (failure-first critique, packet completeness, current readiness approval)"
                      " → `Implement wave` → first code edit.", prepare[1][1])
        self.assertEqual({k: v.as_posix() for k, v in context_efficiency.LIFECYCLE_PROMPT_MAP.items()}, {
            "wf_create_wave": "docs/prompts/create-wave.prompt.md",
            "wf_prepare_wave": "docs/prompts/prepare-wave.prompt.md",
            "wf_implement_wave": "docs/prompts/implement-wave.prompt.md",
            "wf_review_wave": "docs/prompts/review-wave.prompt.md",
            "wf_close_wave": "docs/prompts/close-wave.prompt.md",
        })
        self.assertEqual(lint_constants.PROMPT_SURFACE_FILES, (
            "docs/prompts/index.md", "docs/prompts/plan-change.prompt.md",
            "docs/prompts/implement-change.prompt.md", "docs/prompts/close-change.prompt.md",
            "docs/prompts/agent-routing-concurrency.prompt.md",
        ))
        self.assertEqual(reconcile_scan._RETIRED_FINALIZE_PROMPT_SUGGESTION, (
            "merge unique guidance into docs/prompts/close-wave.prompt.md or "
            "docs/prompts/close-change.prompt.md, then remove the retired prompt"))
        self.assertEqual(reconcile_scan._CLOSE_CHANGE_OR_WAVE_SUGGESTION,
                         "Close change (one change) or Close wave (the wave)")
        suggestions = {retired: suggestion for _p, retired, suggestion in reconcile_scan._RETIRED_CHANGE_PROMPT_PATTERNS}
        self.assertEqual(suggestions["wf-plan-feature"], "wf-plan-change")
        self.assertEqual(suggestions["docs/prompts/agents/implement-feature.prompt.md"],
                         "docs/prompts/agents/implement-change.prompt.md")
        self.assertEqual(suggestions["Plan feature"], "Plan change")
        self.assertEqual(suggestions["Implement feature"], "Implement change")
        self.assertEqual(reconcile_scan._PROFILE_PROMPT_NAME_PATTERNS, ())
        self.assertEqual(reconcile_scan._PROFILE_GURU_DESCRIPTION_PHRASES, ())

    def test_carrier_check_reports_nothing_on_this_repository(self) -> None:
        from wave_lint_lib.core_validators import check_prompt_name_migration, check_review_policy_carriers

        self.assertEqual(check_review_policy_carriers(REPO_ROOT), [])
        self.assertEqual(check_prompt_name_migration(REPO_ROOT), [])
        manifest = json.loads((REPO_ROOT / "docs/prompts/prompt-surface-manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn("prompt_names", manifest)


# ---------------------------------------------------------------------------
# AC-2: validation and the fixed copies
# ---------------------------------------------------------------------------

class ValidationTests(unittest.TestCase):
    def _refused(self, overrides: dict, key: str) -> str:
        with mock.patch.object(vocabulary_profile, "PROMPT_NAME_OVERRIDES", overrides):
            with self.assertRaises(vocabulary_profile.VocabularyProfileInvalid) as ctx:
                vocabulary_profile.validate()
        message = str(ctx.exception)
        self.assertIn("PROMPT_NAME_OVERRIDES", message)
        self.assertIn(repr(key), message)
        return message

    def test_each_rule_is_refused(self) -> None:
        good = {"slug": "plan-set", "shortcut": "Plan set"}
        cases = {
            "unknown key": ({"plan-feature": good}, "plan-feature"),
            "not a dict": ({"plan-change": "plan-set"}, "plan-change"),
            "missing shortcut": ({"plan-change": {"slug": "plan-set"}}, "plan-change"),
            "unknown field": ({"plan-change": {**good, "title": "x"}}, "plan-change"),
            "slug pattern": ({"plan-change": {"slug": "Plan_Set", "shortcut": "Plan set"}}, "plan-change"),
            "slug length": ({"plan-change": {"slug": "p" + "-x" * 40, "shortcut": "Plan set"}}, "plan-change"),
            "duplicate slug": ({"plan-change": {"slug": "pause-wave", "shortcut": "Plan set"}}, "plan-change"),
            "fixed slug": ({"plan-change": {"slug": "review-plan", "shortcut": "Plan set"}}, "plan-change"),
            "fixed skill": ({"plan-change": {"slug": "council", "shortcut": "Plan set"}}, "plan-change"),
            "retired skill": ({"plan-change": {"slug": "interrogate-plan", "shortcut": "Plan set"}}, "plan-change"),
            "empty shortcut": ({"plan-change": {"slug": "plan-set", "shortcut": ""}}, "plan-change"),
            "multi-line shortcut": ({"plan-change": {"slug": "plan-set", "shortcut": "Plan\nset"}}, "plan-change"),
            "padded shortcut": ({"plan-change": {"slug": "plan-set", "shortcut": " Plan set"}}, "plan-change"),
            "long shortcut": ({"plan-change": {"slug": "plan-set", "shortcut": "P" * 65}}, "plan-change"),
            "backtick": ({"plan-change": {"slug": "plan-set", "shortcut": "Plan `set`"}}, "plan-change"),
            "star": ({"plan-change": {"slug": "plan-set", "shortcut": "Plan *set*"}}, "plan-change"),
            "pipe": ({"plan-change": {"slug": "plan-set", "shortcut": "Plan | set"}}, "plan-change"),
            "bracket": ({"plan-change": {"slug": "plan-set", "shortcut": "Plan [set]"}}, "plan-change"),
            "bad alias": ({"plan-change": {**good, "aliases": ["ok", "bad]"]}}, "plan-change"),
            "aliases not a list": ({"plan-change": {**good, "aliases": "Plan it"}}, "plan-change"),
            "shortcut clash": ({"plan-change": {"slug": "plan-set", "shortcut": "Pause wave"}}, "plan-change"),
            "alias clash": ({"plan-change": {**good, "aliases": ["Plan SET"]}}, "plan-change"),
            "fixed shortcut, case-insensitive": (
                {"plan-change": {"slug": "plan-set", "shortcut": "review PLAN"}}, "plan-change"),
            "two-key cycle": ({
                "implement-wave": {"slug": "implement-change", "shortcut": "Implement set"},
                "implement-change": {"slug": "implement-wave", "shortcut": "Implement wave"},
            }, "implement-wave"),
        }
        for name, (overrides, key) in cases.items():
            with self.subTest(rule=name):
                message = self._refused(overrides, key)
                if name == "two-key cycle":
                    self.assertIn("rename cycle", message)
                if name == "fixed shortcut, case-insensitive":
                    self.assertIn("fixed framework shortcut", message)

    def test_a_set_wave_chain_validates(self) -> None:
        self.assertEqual(vocabulary_profile.prompt_name_errors(OVERRIDES), [])
        chain = vocabulary_profile.derive_prompt_names(OVERRIDES)
        self.assertEqual(chain["implement-change"]["slug"], "implement-wave")
        self.assertEqual(chain["implement-wave"]["slug"], "implement-set")
        self.assertEqual(chain["prepare-wave"]["aliases"], ("Ready set",))

    def test_fixed_skill_names_match_the_registry(self) -> None:
        import render_agent_surfaces as ras

        mapped = {vocabulary_profile.skill_name(key) for key in ras.SKILL_PROMPT_KEYS}
        self.assertEqual(set(vocabulary_profile.FIXED_SKILL_NAMES),
                         {skill.name for skill in ras.SKILL_REGISTRY} - mapped)
        stale = {Path(rel).parent.name for rel in ras.STALE_SKILL_PATHS if rel.endswith("/SKILL.md")}
        self.assertEqual(set(vocabulary_profile.FIXED_STALE_SKILL_NAMES), stale)
        self.assertEqual(set(ras.SKILL_PROMPT_KEYS) <= set(vocabulary_profile.DEFAULT_PROMPT_NAMES), True)

    @default_profile_only("reads this repository's own manifest and prompt files")
    def test_fixed_shortcuts_and_slugs_match_this_repository(self) -> None:
        manifest = json.loads((REPO_ROOT / "docs/prompts/prompt-surface-manifest.json").read_text(encoding="utf-8"))
        mapped_docs = {vocabulary_profile.prompt_doc(key) for key in vocabulary_profile.DEFAULT_PROMPT_NAMES}
        self.assertEqual(
            set(vocabulary_profile.FIXED_PROMPT_SHORTCUTS),
            {e["shortcut"] for e in manifest["public_prompt_surface"] if e["doc"] not in mapped_docs})
        stems = {p.name[: -len(".prompt.md")] for d in ("docs/prompts", "docs/prompts/agents")
                 for p in (REPO_ROOT / d).glob("*.prompt.md")}
        retired = {"interrogate-plan", "plan-feature", "implement-feature", "finalize-feature", "index"}
        self.assertEqual(set(vocabulary_profile.FIXED_PROMPT_SLUGS) - retired,
                         stems - set(vocabulary_profile.DEFAULT_PROMPT_NAMES))

    def test_applied_record_problems(self) -> None:
        self.assertEqual(vocabulary_profile.applied_prompt_slugs(None)["close-change"], "close-change")
        for record in ([], {"bogus": "x"}, {"close-change": "Close Wave"}):
            with self.subTest(record=record), self.assertRaises(ValueError):
                vocabulary_profile.applied_prompt_slugs(record)


# ---------------------------------------------------------------------------
# AC-4: consumers under the profile, and per-template identity under defaults
# ---------------------------------------------------------------------------

class ProfileConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _default, profiled, _base = _Trees.get()
        (cls.out,), _ = _drive(profiled, [{"action": "constants", "root": "."}])

    def test_names_and_paths_follow_the_profile(self) -> None:
        out = self.out
        self.assertEqual(out["context_destination"], "docs/prompts/create-set.prompt.md")
        self.assertEqual(out["baselines"][0], ["docs/prompts/create-set.prompt.md", "create-wave.prompt.md"])
        self.assertIn(["docs/prompts/close-wave.prompt.md", "close-change.prompt.md"], out["baselines"])
        self.assertIn(["docs/prompts/close-set.prompt.md", "close-wave.prompt.md"], out["baselines"])
        self.assertEqual(out["close_change"], ["docs/prompts/close-wave.prompt.md", "Close wave"])
        self.assertEqual(sorted(out["carriers"]) , sorted(set(out["carriers"])))
        for path in ("docs/prompts/prepare-set.prompt.md", "docs/prompts/review-set.prompt.md",
                     "docs/prompts/agents/review-set.prompt.md", "docs/prompts/create-set.prompt.md"):
            self.assertIn(path, out["carriers"])
        self.assertNotIn("docs/prompts/prepare-wave.prompt.md", out["carriers"])
        self.assertIn("docs/prompts/implement-set.prompt.md", out["known"])
        self.assertIn("**Review set**", out["known_text"])
        self.assertIn("`Prepare set`", out["known_text"])
        self.assertEqual(out["lifecycle_map"]["wf_close_wave"], "docs/prompts/close-set.prompt.md")
        self.assertEqual(out["surface_files"][1:4], [
            "docs/prompts/plan-wave.prompt.md", "docs/prompts/implement-wave.prompt.md",
            "docs/prompts/close-wave.prompt.md"])
        self.assertEqual(out["close_or_wave"], "Close wave (one change) or Close set (the wave)")
        self.assertIn("docs/prompts/close-set.prompt.md", out["finalize"])
        self.assertIn(["wf-plan-feature", "wf-plan-wave"], out["change_patterns"])
        self.assertIn("(**Plan wave**, **Implement set**, **Close set**, etc.)", out["cursor"])
        self.assertIn("(Plan wave, Implement set, Close set, Prepare set, etc.)", out["guru"])
        blocks = out["blocks"]
        self.assertIn("\nPrepare Set is the single readiness authority.", blocks["docs/prompts/prepare-set.prompt.md"])
        self.assertIn("\nClose Set consumes", blocks["docs/prompts/close-set.prompt.md"])
        self.assertIn("docs/prompts/agents/review-set.prompt.md", blocks)

    def test_skill_registry_renders_derived_names(self) -> None:
        skills = self.out["skills"]
        for name in ("wf-plan-wave", "wf-prepare-set", "wf-implement-set", "wf-review-set",
                     "wf-close-set", "wf-close-wave", "wf-pause-set"):
            self.assertIn(name, skills)
        for name in ("wf-plan-change", "wf-prepare-wave", "wf-implement-wave", "wf-close-change"):
            self.assertNotIn(name, skills)
        self.assertIn("The Prepare set / Ready set workflow.", skills["wf-prepare-set"][0])
        self.assertIn("`docs/prompts/prepare-set.prompt.md`", skills["wf-prepare-set"][1])
        self.assertIn("Single-change variant: Implement wave (`docs/prompts/implement-wave.prompt.md`).",
                      skills["wf-implement-set"][1])
        self.assertIn("The Close wave workflow.", skills["wf-close-wave"][0])
        self.assertIn("Close set (`wf-close-set`) remains the only wave close", skills["wf-close-wave"][1])
        self.assertIn("use `wf-review-set` for", skills["wf-review-plan"][1])
        self.assertIn("(`wf-review-set`)", skills["wf-council"][1])
        stale = set(self.out["stale"])
        self.assertIn(".claude/skills/wf-prepare-wave/SKILL.md", stale)
        self.assertIn(".codex/skills/wf-implement-wave/SKILL.md", stale)
        self.assertNotIn(".claude/skills/wf-close-wave/SKILL.md", stale)  # reused by the chain

    def test_localized_heading_and_shortcut_line(self) -> None:
        localized = self.out["localized"]
        self.assertEqual(localized["prepare-wave"],
                         "# Prepare Set\n\nOwner: x\nShortcut: **`Prepare set`** | Alias: **`Ready set`**\nBody.\n")
        self.assertEqual(localized["close-change"], "# Close Wave\n\nOwner: x\nShortcut: **`Close wave`**\nBody.\n")


@default_profile_only("materializes the shipped templates with the shipped names")
class DefaultTemplateIdentityTests(unittest.TestCase):
    def test_each_lifecycle_template_materializes_byte_identical(self) -> None:
        import time

        import render_agent_surfaces as ras

        template_root = SCRIPTS_DIR.parent / "install" / "lifecycle-prompts"
        for destination, template in ras.LIFECYCLE_PROMPT_BASELINES:
            with self.subTest(template=template), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                with mock.patch.object(ras, "LIFECYCLE_PROMPT_BASELINES", ((destination, template),)):
                    ras.reconcile_lifecycle_prompt_baselines(root)
                with (template_root / template).open("r", encoding="utf-8", newline="") as handle:
                    expected = handle.read().replace("{{generated_at}}", time.strftime("%Y-%m-%d"))
                self.assertEqual((root / destination).read_bytes(), expected.encode("utf-8"))
        prepare = (template_root / "prepare-wave.prompt.md").read_text(encoding="utf-8")
        self.assertIn("Shortcut: **`Prepare wave`** | Alias: **`Ready wave`**", prepare)
        for key in vocabulary_profile.DEFAULT_PROMPT_NAMES:
            path = template_root / f"{key}.prompt.md"
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                self.assertEqual(vocabulary_profile.localize_prompt_template(key, text), text)


# ---------------------------------------------------------------------------
# AC-5 to AC-9: migration, crash and retry, conflicts, lint, scan
# ---------------------------------------------------------------------------

class ProfileMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.default, cls.profiled, base = _Trees.get()
        cls.work = Path(tempfile.mkdtemp(dir=base))
        cls.fixture = build_fixture(cls.default, cls.work / "fixture")
        cls.no_close = build_fixture(cls.default, cls.work / "no-close", close_change=False)

    def _copy(self, source: Path, name: str) -> Path:
        dest = self.work / name
        shutil.copytree(source, dest, symlinks=True)
        return dest

    def _manifest(self, root: Path) -> dict:
        return json.loads((root / "docs/prompts/prompt-surface-manifest.json").read_text(encoding="utf-8"))

    def test_migration_moves_byte_for_byte_and_records_names(self) -> None:
        root = self._copy(self.fixture, "migrate-only")
        before = {rel: (root / rel).read_bytes() for rel in (
            "docs/prompts/plan-change.prompt.md", "docs/prompts/implement-wave.prompt.md",
            "docs/prompts/implement-change.prompt.md", "docs/prompts/close-wave.prompt.md",
            "docs/prompts/close-change.prompt.md", "docs/prompts/agents/implement-wave.prompt.md",
            "docs/prompts/agents/implement-change.prompt.md", "docs/prompts/prepare-wave.prompt.md")}
        (out,), _ = _drive(self.profiled, [{"action": "migrate", "root": str(root)}])
        self.assertNotIn("error", out)
        prompts = root / "docs" / "prompts"
        self.assertEqual((prompts / "plan-wave.prompt.md").read_bytes(), before["docs/prompts/plan-change.prompt.md"])
        self.assertEqual((prompts / "implement-set.prompt.md").read_bytes(),
                         before["docs/prompts/implement-wave.prompt.md"])
        # The chain: the item prompt (CRLF) now holds the container's old name.
        self.assertEqual((prompts / "implement-wave.prompt.md").read_bytes(), IMPLEMENT_CHANGE_BYTES)
        self.assertEqual((prompts / "close-set.prompt.md").read_bytes(), before["docs/prompts/close-wave.prompt.md"])
        self.assertEqual((prompts / "close-wave.prompt.md").read_bytes(), before["docs/prompts/close-change.prompt.md"])
        self.assertEqual((prompts / "prepare-set.prompt.md").read_bytes(), before["docs/prompts/prepare-wave.prompt.md"])
        self.assertEqual((prompts / "agents/implement-set.prompt.md").read_bytes(),
                         before["docs/prompts/agents/implement-wave.prompt.md"])
        self.assertEqual((prompts / "agents/implement-wave.prompt.md").read_bytes(),
                         before["docs/prompts/agents/implement-change.prompt.md"])
        for gone in ("plan-change", "implement-change", "close-change", "prepare-wave", "pause-wave"):
            self.assertFalse((prompts / f"{gone}.prompt.md").exists(), gone)
        manifest = self._manifest(root)
        self.assertEqual(manifest["prompt_names"], {key: spec["slug"] for key, spec in OVERRIDES.items()})
        entries = {e["doc"]: e["shortcut"] for e in manifest["public_prompt_surface"]}
        self.assertEqual(entries["docs/prompts/implement-wave.prompt.md"], "Implement wave")
        self.assertEqual(entries["docs/prompts/implement-set.prompt.md"], "Implement set")
        self.assertEqual(entries["docs/prompts/close-set.prompt.md"], "Close set")
        self.assertEqual(entries["docs/prompts/close-wave.prompt.md"], "Close wave")
        self.assertEqual(entries["docs/prompts/prepare-set.prompt.md"], "Prepare set")
        self.assertEqual(len(manifest["public_prompt_surface"]), len(self._manifest(self.fixture)["public_prompt_surface"]))
        self.assertEqual(out["links"], [f"{LINK_DOC}:7"])

    def test_render_converges_and_reports_links(self) -> None:
        root = self._copy(self.fixture, "render")
        link_before = (root / LINK_DOC).read_bytes()
        (first, second, lint), stderr = _drive(self.profiled, [
            {"action": "render", "root": str(root)}, {"action": "render", "root": str(root)},
            {"action": "lint", "root": str(root)}])
        self.assertNotIn("error", first)
        self.assertEqual(second, {"written": []})
        self.assertIn(f"{LINK_DOC}:7", stderr)
        self.assertEqual((root / LINK_DOC).read_bytes(), link_before)
        for host in (".claude", ".codex", ".agents"):
            skills = root / host / "skills"
            for gone in ("wf-plan-change", "wf-prepare-wave", "wf-implement-wave", "wf-review-wave",
                         "wf-close-change", "wf-pause-wave"):
                self.assertFalse((skills / gone).exists(), f"{host} {gone}")
            for present in ("wf-plan-wave", "wf-prepare-set", "wf-implement-set", "wf-close-set", "wf-pause-set"):
                self.assertTrue((skills / present / "SKILL.md").is_file(), f"{host} {present}")
            reused = (skills / "wf-close-wave" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("name: wf-close-wave", reused)
            self.assertIn("# Close a change", reused)
        # No baseline over a moved prompt: the item prompts keep their moved bytes.
        self.assertEqual((root / "docs/prompts/implement-wave.prompt.md").read_bytes(), IMPLEMENT_CHANGE_BYTES)
        self.assertEqual((root / "docs/prompts/close-wave.prompt.md").read_bytes(),
                         (self.fixture / "docs/prompts/close-change.prompt.md").read_bytes())
        # AC-8: lint passes after the render; the pending check is silent.
        self.assertEqual(lint["pending"], [])
        self.assertEqual(lint["rc"], 0, lint["output"][-3000:])

    def test_missing_close_change_ends_with_one_entry_at_the_derived_name(self) -> None:
        root = self._copy(self.no_close, "no-close-render")
        (out,), _ = _drive(self.profiled, [{"action": "render", "root": str(root)}])
        self.assertNotIn("error", out)
        entries = self._manifest(root)["public_prompt_surface"]
        close = [e for e in entries if e["doc"] == "docs/prompts/close-wave.prompt.md"]
        self.assertEqual(close, [{"doc": "docs/prompts/close-wave.prompt.md", "shortcut": "Close wave"}])
        self.assertEqual(len([e for e in entries if e["shortcut"] == "Close wave"]), 1)
        import time

        template = (SCRIPTS_DIR.parent / "install/lifecycle-prompts/close-change.prompt.md").read_text(
            encoding="utf-8").replace("{{generated_at}}", time.strftime("%Y-%m-%d"))
        text = (root / "docs/prompts/close-wave.prompt.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Close Wave\n"))
        self.assertIn("\nShortcut: **`Close wave`**\n", text)
        self.assertEqual(text.split("\n")[1:6], template.split("\n")[1:6])
        self.assertEqual(text.split("\n")[7:], template.split("\n")[7:])

    def test_every_interruption_converges(self) -> None:
        reference = self._copy(self.fixture, "reference")
        (ref,), _ = _drive(self.profiled, [{"action": "render", "root": str(reference)}])
        self.assertNotIn("error", ref)
        ref_digest = _tree_digest(reference)
        for fixture, name in ((self.fixture, "close-present"), (self.no_close, "close-missing")):
            if fixture is self.no_close:
                expected_root = self._copy(self.no_close, "reference-no-close")
                _drive(self.profiled, [{"action": "render", "root": str(expected_root)}])
                expected = _tree_digest(expected_root)
            else:
                expected = ref_digest
            sweep_dir = self.work / f"sweep-{name}"
            sweep_dir.mkdir()
            (out,), _ = _drive(self.profiled, [{"action": "crash_sweep", "base": str(fixture),
                                                "work": str(sweep_dir), "root": str(fixture)}])
            points = {r["point"] for r in out["results"]}
            self.assertEqual(points, {"after_copy", "after_move", "before_record"})
            self.assertGreaterEqual(len(out["results"]), 20)
            for result in out["results"]:
                with self.subTest(fixture=name, point=result["point"], index=result["index"]):
                    self.assertNotIn("error", result["rerun"])
                    self.assertEqual(result["digest"], expected)
                    entries = self._manifest(Path(result["root"]))["public_prompt_surface"]
                    self.assertEqual(
                        len([e for e in entries if e["doc"] == "docs/prompts/close-wave.prompt.md"]), 1)

    def test_reverting_to_the_defaults_drops_the_record(self) -> None:
        """A render under the defaults moves the prompts back, drops each key
        at its default and removes the emptied ``prompt_names`` object; a
        second render writes nothing."""
        root = self._copy(self.fixture, "revert")
        (profiled,), _ = _drive(self.profiled, [{"action": "render", "root": str(root)}])
        self.assertNotIn("error", profiled)
        self.assertIn("prompt_names", self._manifest(root))
        (first, second), _ = _drive(self.default, [
            {"action": "render", "root": str(root)}, {"action": "render", "root": str(root)}])
        self.assertNotIn("error", first)
        self.assertIn("docs/prompts/prompt-surface-manifest.json", first["written"])
        self.assertNotIn("prompt_names", self._manifest(root))
        self.assertEqual(second, {"written": []})
        prompts = root / "docs" / "prompts"
        self.assertEqual((prompts / "implement-change.prompt.md").read_bytes(), IMPLEMENT_CHANGE_BYTES)
        for gone in ("plan-wave", "implement-set", "close-set", "prepare-set"):
            self.assertFalse((prompts / f"{gone}.prompt.md").exists(), gone)

    def test_a_locked_source_rolls_the_copy_back(self) -> None:
        """When removing a move's source fails (a locked file on Windows), the
        copy is removed, the source kept, and no key is recorded."""
        root = self._copy(self.fixture, "locked-source")
        before = _tree_digest(root)
        (out,), _ = _drive(self.profiled, [{"action": "unlink_fail", "root": str(root)}])
        self.assertEqual(len(out["failed"]), 1)
        source = out["failed"][0]
        self.assertTrue(source.startswith("docs/prompts/"), source)
        error = out["result"]["error"]
        self.assertIn(f"prompt name migration blocked while removing {source}", error)
        self.assertIn("was removed", error)
        self.assertTrue((root / source).is_file())
        self.assertNotIn("prompt_names", self._manifest(root))
        # Nothing else changed: no target copy and no temporary file remains.
        self.assertEqual(_tree_digest(root), before)
        (rerun,), _ = _drive(self.profiled, [{"action": "render", "root": str(root)}])
        self.assertNotIn("error", rerun)
        self.assertEqual(self._manifest(root)["prompt_names"],
                         {key: spec["slug"] for key, spec in OVERRIDES.items()})

    def test_conflicts_write_nothing(self) -> None:
        cases = {}
        root = self._copy(self.fixture, "conflict-target")
        (root / "docs/prompts/plan-wave.prompt.md").write_text(_authored("Plan Wave"), encoding="utf-8")
        cases["target exists"] = (root, ["docs/prompts/plan-change.prompt.md -> docs/prompts/plan-wave.prompt.md"])
        root = self._copy(self.fixture, "conflict-cycle")
        (root / "docs/prompts/implement-set.prompt.md").write_text(_authored("Implement Set"), encoding="utf-8")
        manifest = self._manifest(root)
        manifest["prompt_names"] = {"implement-change": "implement-set"}
        (root / "docs/prompts/prompt-surface-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                                                         encoding="utf-8")
        cases["cycle"] = (root, ["rename cycle"])
        for name, (root, needles) in cases.items():
            with self.subTest(case=name):
                before = _tree_digest(root)
                (out,), _ = _drive(self.profiled, [{"action": "render", "root": str(root)}])
                self.assertIn("prompt name migration blocked", out["error"])
                self.assertIn("All files were preserved and nothing was written", out["error"])
                for needle in needles:
                    self.assertIn(needle, out["error"])
                self.assertEqual(_tree_digest(root), before)

    def test_lint_reports_a_pending_migration(self) -> None:
        root = self._copy(self.fixture, "lint-pending")
        (lint,), _ = _drive(self.profiled, [{"action": "lint", "root": str(root)}])
        self.assertNotEqual(lint["rc"], 0)
        self.assertEqual(len(lint["pending"]), 1)
        self.assertIn("migration pending", lint["pending"][0])
        for key in OVERRIDES:
            self.assertIn(f"`{key}`", lint["pending"][0])
        self.assertIn("wf render-surfaces", lint["pending"][0])
        self.assertIn("docs/prompts/plan-wave.prompt.md", lint["output"])  # required at the derived path
        (default_lint,), _ = _drive(self.default, [{"action": "lint", "root": str(self.fixture)}])
        self.assertEqual(default_lint["pending"], [])

    def test_scan_reports_default_tokens_but_not_chain_tokens(self) -> None:
        root = self._copy(self.fixture, "scan")
        (root / "docs/references/names.md").write_text(
            _authored("Names") + "\nRun **Prepare wave**, then `Implement wave`, then **Close wave**.\n"
            "Use `wf-prepare-wave` and see docs/prompts/agents/prepare-wave.prompt.md.\n",
            encoding="utf-8")
        guru = root / ".claude/agents/guru.md"
        guru.parent.mkdir(parents=True, exist_ok=True)
        guru.write_text("---\nname: guru\ndescription: Not for Plan change or Implement wave.\n---\n\nBody.\n",
                        encoding="utf-8")
        (out,), _ = _drive(self.profiled, [{"action": "scan", "root": str(root)}])
        names = [row for row in out if row[0] == "docs/references/names.md"]
        self.assertIn(["docs/references/names.md", 9, "Prepare wave", "**Prepare wave**", "Prepare set"], names)
        self.assertIn(["docs/references/names.md", 10, "wf-prepare-wave", "wf-prepare-wave", "wf-prepare-set"], names)
        self.assertIn(["docs/references/names.md", 10, "docs/prompts/agents/prepare-wave.prompt.md",
                       "docs/prompts/agents/prepare-wave.prompt.md", "docs/prompts/agents/prepare-set.prompt.md"],
                      names)
        matched = {row[3] for row in names}
        self.assertNotIn("`Implement wave`", matched)  # a chain token: the item's current name
        self.assertNotIn("**Close wave**", matched)
        guru_rows = [row for row in out if row[0] == ".claude/agents/guru.md"]
        self.assertEqual(guru_rows, [[".claude/agents/guru.md", 3, "Plan change (guru agent description)",
                                      "Plan change", "Plan wave"]])
        (default_out,), _ = _drive(self.default, [{"action": "scan", "root": str(root)}])
        self.assertEqual([row for row in default_out if row[0] in ("docs/references/names.md",
                                                                   ".claude/agents/guru.md")], [])


class AtomicPromptCopyTests(unittest.TestCase):
    """The prompt moves publish their copy whole or not at all."""

    def setUp(self) -> None:
        import render_agent_surfaces as ras

        self.ras = ras
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name) / "prompts"
        self.target = self.folder / "plan-wave.prompt.md"

    def test_an_interrupted_copy_leaves_no_target_and_no_temporary_file(self) -> None:
        with mock.patch.object(os, "fsync", side_effect=OSError(28, "No space left on device")):
            with self.assertRaises(OSError):
                self.ras._write_review_carrier_text(self.target, b"prompt\r\nbody\r\n", exclusive=True)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_the_copy_is_exact_and_refuses_an_existing_target(self) -> None:
        self.ras._write_review_carrier_text(self.target, b"prompt\r\nbody\r\n", exclusive=True)
        self.assertEqual(self.target.read_bytes(), b"prompt\r\nbody\r\n")
        with self.assertRaises(RuntimeError):
            self.ras._write_review_carrier_text(self.target, b"other\n", exclusive=True)
        self.assertEqual(self.target.read_bytes(), b"prompt\r\nbody\r\n")
        self.assertEqual([p.name for p in self.folder.iterdir()], ["plan-wave.prompt.md"])

    def test_without_hard_links_the_copy_still_refuses_an_existing_target(self) -> None:
        with mock.patch.object(os, "link", side_effect=OSError(1, "Operation not permitted")):
            self.ras._write_review_carrier_text(self.target, b"prompt\n", exclusive=True)
            self.assertEqual(self.target.read_bytes(), b"prompt\n")
            with self.assertRaises(RuntimeError):
                self.ras._write_review_carrier_text(self.target, b"other\n", exclusive=True)
        self.assertEqual(self.target.read_bytes(), b"prompt\n")
        self.assertEqual([p.name for p in self.folder.iterdir()], ["plan-wave.prompt.md"])

    def test_without_hard_links_a_failed_direct_copy_leaves_no_target(self) -> None:
        """The no-hard-link fallback writes the target directly; when that
        write fails after creating it, the partial target is removed (a
        leftover would block every later run) and the move source stays."""
        repo = self.folder.parent
        pair = self.ras._PromptMovePair("plan", "prompts/old.prompt.md", "prompts/plan-wave.prompt.md")
        self.folder.mkdir(parents=True)
        source = repo / pair.source
        source.write_bytes(b"prompt\r\nbody\r\n")
        real_open, real_fdopen = os.open, os.fdopen
        target_fds: set = set()

        def tracking_open(path, flags, *args, **kwargs):
            fd = real_open(path, flags, *args, **kwargs)
            if os.path.realpath(path) == os.path.realpath(self.target):
                target_fds.add(fd)
            return fd

        class _FailingWrite:
            def __init__(self, handle):
                self.handle = handle

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.handle.close()
                return False

            def write(self, data):
                self.handle.write(data[:3])
                self.handle.flush()
                raise OSError(28, "No space left on device")

        def failing_fdopen(fd, *args, **kwargs):
            handle = real_fdopen(fd, *args, **kwargs)
            return _FailingWrite(handle) if fd in target_fds else handle

        with mock.patch.object(os, "link", side_effect=OSError(1, "Operation not permitted")), \
                mock.patch.object(os, "open", tracking_open), \
                mock.patch.object(os, "fdopen", failing_fdopen):
            with self.assertRaises(OSError):
                self.ras._move_prompt_pair(repo, pair)
        self.assertTrue(target_fds, "the direct fallback write was not exercised")
        self.assertFalse(os.path.lexists(self.target))
        self.assertEqual(source.read_bytes(), b"prompt\r\nbody\r\n")
        self.assertEqual([p.name for p in self.folder.iterdir()], ["old.prompt.md"])


class RetiredNameScanAliasTests(unittest.TestCase):
    """A live alias is current: the scan never reports it as retired."""

    def test_a_default_phrase_kept_as_an_alias_is_not_reported(self) -> None:
        import reconcile_scan

        names = {key: dict(spec, aliases=list(spec["aliases"]))
                 for key, spec in vocabulary_profile.DEFAULT_PROMPT_NAMES.items()}
        names["prepare-wave"] = {"slug": "prepare-set", "shortcut": "Prepare set",
                                 "aliases": ["Prepare wave", "Ready wave"]}
        with mock.patch.object(vocabulary_profile, "PROMPT_NAMES", names):
            patterns, guru = reconcile_scan._profile_prompt_name_tables()
        tokens = {token for _pattern, token, _suggestion in patterns}
        self.assertNotIn("Prepare wave", tokens)
        self.assertNotIn("Prepare wave", {token for _pattern, token, _suggestion in guru})
        # The retired path and skill name are still reported.
        self.assertIn("docs/prompts/prepare-wave.prompt.md", tokens)
        self.assertIn("wf-prepare-wave", tokens)


# ---------------------------------------------------------------------------
# AC-10: the installing upgrade runs the migration
# ---------------------------------------------------------------------------

class ProfileInstallingUpgradeTests(unittest.TestCase):
    def test_installing_upgrade_moves_prompts_and_records_names(self) -> None:
        default, _profiled, base = _Trees.get()
        work = Path(tempfile.mkdtemp(dir=base))
        root = build_fixture(default, work / "target")
        framework = root / ".wavefoundry" / "framework"
        scripts = copy_scripts_tree(framework, with_support=False)
        apply_profile(scripts, shipped_default_profile())
        apply_profile(scripts, PROFILE)
        shutil.copytree(SCRIPTS_DIR.parent / "seeds", framework / "seeds")
        spec = importlib.util.spec_from_file_location("upgrade_wavefoundry_1zxnw", SCRIPTS_DIR / "upgrade_wavefoundry.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import venv_bootstrap

        with mock.patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                mock.patch.object(mod, "SCRIPTS_DIR", scripts), \
                mock.patch.object(mod, "_preferred_python", return_value=sys.executable), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            mod.phase_surface_rendering(root)
        prompts = root / "docs" / "prompts"
        self.assertEqual((prompts / "implement-wave.prompt.md").read_bytes(), IMPLEMENT_CHANGE_BYTES)
        self.assertTrue((prompts / "implement-set.prompt.md").is_file())
        self.assertFalse((prompts / "implement-change.prompt.md").exists())
        manifest = json.loads((prompts / "prompt-surface-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["prompt_names"], {key: spec["slug"] for key, spec in OVERRIDES.items()})
        self.assertTrue((root / ".codex/skills/wf-prepare-set/SKILL.md").is_file())
        self.assertFalse((root / ".codex/skills/wf-prepare-wave").exists())


@default_profile_only("renders this repository's own surfaces with the shipped names")
class DefaultRenderIdentityTests(unittest.TestCase):
    """AC-3: under the defaults a render of this repository's surfaces writes nothing."""

    COPIED = (".claude", ".codex", ".agents", ".cursor", "CLAUDE.md", "AGENTS.md", ".github",
              ".junie", "WARP.md")

    def test_render_of_this_repository_writes_nothing(self) -> None:
        import render_agent_surfaces as ras

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in self.COPIED:
                source = REPO_ROOT / name
                if source.is_dir():
                    shutil.copytree(source, root / name, symlinks=True)
                elif source.is_file():
                    shutil.copy2(source, root / name)
            shutil.copytree(REPO_ROOT / "docs", root / "docs", symlinks=True,
                            ignore=shutil.ignore_patterns("waves", "memory", "history", "reports"))
            before = _tree_digest(root)
            with contextlib.redirect_stderr(io.StringIO()) as err:
                written = ras.render_agent_surfaces(root)
            self.assertEqual(written, [], err.getvalue())
            self.assertEqual(_tree_digest(root), before)
            manifest = json.loads((root / "docs/prompts/prompt-surface-manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("prompt_names", manifest)


def tearDownModule() -> None:  # noqa: N802 (unittest name)
    if _Trees.tmp is not None:
        _Trees.tmp.cleanup()
        _Trees.tmp = None


if __name__ == "__main__":
    unittest.main()
