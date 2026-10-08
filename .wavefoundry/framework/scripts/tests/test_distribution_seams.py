"""Wave 200ey (change 200ew): distribution seams and the neutral council role.

Literal reconcile keys (AC-1), the renamed council actor read and written
under every earlier name (AC-3, AC-5, AC-6), the role-doc move (AC-7), the
actor-token census over the shipped framework tree (AC-8), the ``lifecycle_id``
reload (AC-9) and the council display name (AC-12 to AC-15).

The earlier actor name is never written literally in this file: it is read
from ``review_evidence.LEGACY_COUNCIL_ACTORS`` or assembled, so the census
below does not have to list this file.
"""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import reconcile_scan
import render_agent_surfaces as ras
import review_evidence
import review_policy
import vocabulary_profile
from test_review_evidence import executable_evidence
from record_layout_support import waves_dir

SCRIPTS = Path(__file__).resolve().parents[1]
FRAMEWORK = SCRIPTS.parent
TESTS = SCRIPTS / "tests"
LEGACY_ACTOR = review_evidence.LEGACY_COUNCIL_ACTORS[0]
ACTOR = review_evidence.COUNCIL_ACTOR
# The council display name the seeds are written with, assembled so this file
# holds no literal the display-name census would count.
SHIPPED_NAME = vocabulary_profile.SHIPPED_COUNCIL_DISPLAY_NAME


# ---------------------------------------------------------------------------
# AC-1: literal reconcile keys
# ---------------------------------------------------------------------------

NAME_FUNCTIONS = frozenset({"prompt_slug", "prompt_doc", "agent_prompt_doc", "skill_name", "shortcut"})


def _name_function_aliases(tree: ast.AST) -> set[str]:
    """Module-level names bound to a profile name function (``_vp_doc = vocabulary_profile.prompt_doc``)."""
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute):
            if node.value.attr in NAME_FUNCTIONS:
                aliases.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return aliases


def runtime_key_calls(source: str, filename: str = "<module>") -> list[str]:
    """Calls to a profile name function whose key is built at run time.

    The census predicate: the key argument must be a string literal or a bare
    name (a loop variable over ``DEFAULT_PROMPT_NAMES`` or a parameter that
    carries one). A concatenation, f-string, call, subscript or any other
    expression builds a key at run time and is reported."""
    tree = ast.parse(source, filename)
    names = NAME_FUNCTIONS | _name_function_aliases(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        called = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None
        if called not in names:
            continue
        key = node.args[0]
        literal = isinstance(key, ast.Constant) and isinstance(key.value, str)
        if not (literal or isinstance(key, ast.Name)):
            found.append(f"{filename}:{node.lineno}")
    return found


@contextlib.contextmanager
def _patched_profile(name: str, value):
    """Patch a profile constant on every loaded copy of the profile module (a
    server load in an imported test module may have re-imported it)."""
    modules = {id(m): m for m in (vocabulary_profile, sys.modules.get("vocabulary_profile")) if m is not None}
    with contextlib.ExitStack() as stack:
        for module in modules.values():
            stack.enter_context(mock.patch.object(module, name, value))
        yield


def _exec_fresh(name: str, path: Path):
    """Execute ``path`` as a new module ``name`` (registered while it runs,
    as dataclasses need), then unregister it."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def _framework_scripts() -> list[Path]:
    return sorted(
        path for path in SCRIPTS.rglob("*.py")
        if "tests" not in path.relative_to(SCRIPTS).parts and "__pycache__" not in path.parts
    )


class LiteralReconcileKeyTests(unittest.TestCase):
    def _expected(self) -> list[tuple[str, str, str]]:
        # The pre-change formula: replacement paths built from verb + "-change".
        return [
            (
                rf"(?<![\w.-])docs/prompts/{agents}{verb}\-feature\.prompt\.md(?![\w.-])",
                f"docs/prompts/{agents}{verb}-feature.prompt.md",
                f"docs/prompts/{agents}{vocabulary_profile.prompt_slug(verb + '-change')}.prompt.md",
            )
            for agents in ("", "agents/")
            for verb in ("plan", "implement")
        ]

    def _actual(self, module) -> list[tuple[str, str, str]]:
        return [(p.pattern, retired, suggested) for p, retired, suggested in module._RETIRED_CHANGE_PROMPT_PATTERNS[1:5]]

    def test_patterns_are_unchanged_under_the_live_profile(self) -> None:
        self.assertEqual(self._actual(reconcile_scan), self._expected())

    def test_patterns_are_unchanged_under_the_prompt_names_profile(self) -> None:
        asset = json.loads((TESTS / "fixtures" / "profiles" / "prompt-names.json").read_text(encoding="utf-8"))
        overrides = asset["modules"]["vocabulary_profile"]["PROMPT_NAME_OVERRIDES"]
        names = vocabulary_profile.derive_prompt_names(overrides)
        with _patched_profile("PROMPT_NAMES", names):
            module = _exec_fresh("_reconcile_scan_profiled", SCRIPTS / "reconcile_scan.py")
            self.assertEqual(self._actual(module), self._expected())
            self.assertIn("docs/prompts/plan-task.prompt.md", [row[2] for row in self._actual(module)])

    def test_no_name_function_takes_a_key_built_at_run_time(self) -> None:
        found = [
            hit
            for path in _framework_scripts()
            for hit in runtime_key_calls(path.read_text(encoding="utf-8"), path.relative_to(SCRIPTS).as_posix())
        ]
        self.assertEqual(found, [])

    def test_the_census_reports_a_concatenated_key(self) -> None:
        scratch = (
            "import vocabulary_profile\n"
            "for verb in ('plan', 'implement'):\n"
            "    vocabulary_profile.prompt_slug(verb + '-change')\n"
            "vocabulary_profile.prompt_doc('plan-change')\n"
        )
        self.assertEqual(runtime_key_calls(scratch, "scratch.py"), ["scratch.py:3"])


# ---------------------------------------------------------------------------
# AC-3, AC-5, AC-6: the council actor and keys
# ---------------------------------------------------------------------------


def _approval(key: str, actor: str) -> dict:
    return executable_evidence(
        f"approval-{key}-{actor}", f"approval:{key}", claim_kind="approval",
        actor=actor, required_for_approval=True,
    )


@contextlib.contextmanager
def _pre_change_reader():
    """The status projection as it read before the rename: one actor name."""
    with mock.patch.object(review_evidence, "COUNCIL_ACTOR", LEGACY_ACTOR), \
            mock.patch.object(review_evidence, "COUNCIL_ACTORS", (LEGACY_ACTOR,)):
        yield


class CouncilActorReadTests(unittest.TestCase):
    FIELDS = ("signoff_key", "state", "why", "next_action")
    KEYS = (review_evidence.COUNCIL_DELIVERY_SIGNOFF_KEY,)

    def _ledgers(self) -> dict[str, list[dict]]:
        new = review_evidence.COUNCIL_DELIVERY_SIGNOFF_KEY
        [old] = review_evidence.legacy_signoff_key_spellings(new)[:1]
        return {"old-key": [_approval(old, LEGACY_ACTOR)], "new-key": [_approval(new, LEGACY_ACTOR)]}

    def _rows(self, records) -> list[dict]:
        return [{field: row[field] for field in self.FIELDS}
                for row in review_evidence.review_status_rows(records, self.KEYS)]

    def test_legacy_actor_approvals_project_as_before(self) -> None:
        for name, records in self._ledgers().items():
            with self.subTest(ledger=name):
                with _pre_change_reader():
                    before = self._rows(records)
                after = self._rows(records)
                self.assertEqual(json.dumps(after).encode(), json.dumps(before).encode())
                self.assertEqual(after[0]["state"], "approved", after)
                projection = review_evidence.review_authority_projection(records, self.KEYS)
                actions = [a for a in projection.get("actions", []) if a.get("actor_role")]
                for action in actions:
                    self.assertEqual(action["actor_role"], ACTOR)

    def test_an_approval_by_the_current_actor_is_valid(self) -> None:
        records = [_approval(review_evidence.COUNCIL_DELIVERY_SIGNOFF_KEY, ACTOR)]
        [row] = review_evidence.review_status_rows(records, self.KEYS)
        self.assertEqual(row["state"], "approved", row)

    def test_dropping_the_legacy_actor_from_the_read_check_breaks_the_projection(self) -> None:
        # Mutant: only the current name is a council actor. The legacy ledgers
        # then project differently, so the byte comparison above would fail.
        for name, records in self._ledgers().items():
            with self.subTest(ledger=name):
                with _pre_change_reader():
                    before = self._rows(records)
                with mock.patch.object(review_evidence, "COUNCIL_ACTORS", (ACTOR,)):
                    mutant = self._rows(records)
                self.assertNotEqual(mutant, before)

    def test_distinctness_treats_both_names_as_one_actor(self) -> None:
        self.assertEqual(review_evidence.canonical_council_actor(LEGACY_ACTOR), ACTOR)
        self.assertEqual(review_evidence.canonical_council_actor("qa-reviewer"), "qa-reviewer")
        self.assertEqual(review_evidence.legacy_council_actor_spellings(ACTOR), (LEGACY_ACTOR,))
        self.assertEqual(review_evidence.legacy_council_actor_spellings("qa-reviewer"), ())


class CouncilKeyTests(unittest.TestCase):
    def test_the_frozen_prefix_keeps_earlier_and_custom_keys(self) -> None:
        prefix = LEGACY_ACTOR + "-"
        self.assertEqual(review_evidence._LEGACY_COUNCIL_KEY_PREFIX, prefix)
        for key in (prefix + "readiness", prefix + "delivery", prefix + "x"):
            with self.subTest(key=key):
                self.assertTrue(review_evidence.is_council_signoff_key(key))
        self.assertFalse(review_evidence.is_council_signoff_key(ACTOR + "-x"))

    def _fresh_review_evidence(self, extra: dict):
        with _patched_profile("EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS", extra):
            return _exec_fresh("_review_evidence_extra", SCRIPTS / "review_evidence.py")

    def test_a_declared_earlier_spelling_maps_to_the_current_key(self) -> None:
        extra = {"board-readiness": "council-readiness", "Review Board Readiness": "council-readiness"}
        module = self._fresh_review_evidence(extra)
        for key in extra:
            with self.subTest(key=key):
                self.assertEqual(module.canonical_signoff_key(key), "council-readiness")
                self.assertIn(key, module.legacy_signoff_key_spellings("council-readiness"))
                self.assertTrue(module.is_council_signoff_key(key))
        self.assertNotIn("board-readiness", module.BUILTIN_LEGACY_COUNCIL_SIGNOFF_KEYS)
        # The digest maps only the built-in spellings, so a config naming the
        # declared key hashes that literal key, with or without the declaration.
        self.assertEqual(review_policy._DIGEST_COUNCIL_SIGNOFF_SPELLING,
                         {new: old for old, new in module.BUILTIN_LEGACY_COUNCIL_SIGNOFF_KEYS.items()})
        config = {"enabled": True, "delivery_mode": "universal",
                  "phases": {"prepare": {"signoff_key": "board-readiness", "moderator_role": ACTOR}}}
        self.assertEqual(review_policy._digest_wave_review(config)["phases"]["prepare"]["signoff_key"],
                         "board-readiness")

    def test_the_profile_copies_of_the_keys_match(self) -> None:
        self.assertEqual(vocabulary_profile._CURRENT_COUNCIL_SIGNOFF_KEYS, review_evidence.COUNCIL_SIGNOFF_KEYS)
        self.assertEqual(set(vocabulary_profile._BUILTIN_LEGACY_COUNCIL_SIGNOFF_KEYS),
                         set(review_evidence.BUILTIN_LEGACY_COUNCIL_SIGNOFF_KEYS))


class ModeratorRoleDigestTests(unittest.TestCase):
    KWARGS = dict(project_lanes=["code-reviewer"], review_policies={},
                  changes=[("1aaaa-enh pinned", "enh", b"# Pinned\n")], requested_lanes=[])

    def _config(self, role: str) -> dict:
        return {"enabled": True, "delivery_mode": "targeted", "phases": {
            "prepare": {"signoff_key": "council-readiness", "moderator_role": role},
            "review": {"signoff_key": "council-delivery", "moderator_role": role}}}

    def test_the_renamed_moderator_role_hashes_like_the_earlier_one(self) -> None:
        before = review_policy.policy_input_snapshot(wave_review=self._config(LEGACY_ACTOR), **self.KWARGS)
        after = review_policy.policy_input_snapshot(wave_review=self._config(ACTOR), **self.KWARGS)
        self.assertEqual(after[0], before[0])
        self.assertNotEqual(
            review_policy.policy_input_snapshot(wave_review=self._config("other-chair"), **self.KWARGS)[0],
            before[0],
        )

    def test_both_role_names_are_read_from_config(self) -> None:
        import lifecycle_gate_support
        for role in (ACTOR, LEGACY_ACTOR):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / "docs").mkdir()
                (root / "docs" / "workflow-config.json").write_text(
                    json.dumps({"wave_review": self._config(role)}), encoding="utf-8")
                policy = lifecycle_gate_support._read_wave_council_policy(root)
                self.assertEqual(policy["phases"]["prepare"]["moderator_role"], role)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "docs").mkdir()
            config = {"enabled": True, "delivery_mode": "targeted",
                      "phases": {"prepare": {"signoff_key": "council-readiness"}}}
            (root / "docs" / "workflow-config.json").write_text(json.dumps({"wave_review": config}), encoding="utf-8")
            policy = lifecycle_gate_support._read_wave_council_policy(root)
            self.assertEqual(policy["phases"]["prepare"]["moderator_role"], ACTOR)


# ---------------------------------------------------------------------------
# AC-7: the role-doc and native-wrapper move
# ---------------------------------------------------------------------------

ROLE_DOC = ("Owner: Engineering\nStatus: active\nRole: {role}\nCategory: specialist\n"
            "Last verified: 2026-10-07\n\n# Council\n\nProject prose kept byte-for-byte.\r\n")


class CouncilRoleMoveTests(unittest.TestCase):
    def _tree(self, temp: str, rel_old: str) -> Path:
        root = Path(temp)
        old = root / rel_old
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_bytes(ROLE_DOC.format(role=LEGACY_ACTOR).encode("utf-8"))
        if hasattr(os, "chmod"):
            os.chmod(old, 0o640)
        return root

    def test_each_pair_moves_byte_for_byte_and_converges(self) -> None:
        for old_rel, new_rel in ras.COUNCIL_ROLE_RENAMES:
            with self.subTest(old=old_rel), tempfile.TemporaryDirectory() as temp:
                root = self._tree(temp, old_rel)
                original = (root / old_rel).read_bytes()
                mode = stat.S_IMODE((root / old_rel).stat().st_mode)
                result = ras.migrate_council_role_renames(root)
                self.assertEqual(result.written, (old_rel, new_rel))
                self.assertFalse((root / old_rel).exists())
                self.assertEqual((root / new_rel).read_bytes(), original)
                if os.name != "nt":
                    self.assertEqual(stat.S_IMODE((root / new_rel).stat().st_mode), mode)
                if old_rel.startswith(".codex/"):
                    self.assertFalse((root / old_rel).parent.exists())
                self.assertEqual(ras.migrate_council_role_renames(root).written, ())

    def test_a_render_moves_the_role_doc_and_a_second_render_writes_nothing(self) -> None:
        for old_rel, new_rel in ras.COUNCIL_ROLE_RENAMES:
            with self.subTest(old=old_rel), tempfile.TemporaryDirectory() as temp:
                root = self._tree(temp, old_rel)
                mode = stat.S_IMODE((root / old_rel).stat().st_mode)
                first = ras.render_agent_surfaces(root)
                self.assertIn(new_rel, first)
                self.assertIn(old_rel, first)
                self.assertFalse((root / old_rel).exists())
                self.assertIn("Project prose kept byte-for-byte.", (root / new_rel).read_text(encoding="utf-8"))
                if os.name != "nt":
                    self.assertEqual(stat.S_IMODE((root / new_rel).stat().st_mode), mode)
                self.assertEqual(ras.render_agent_surfaces(root), [])

    def test_both_paths_present_is_a_conflict_that_changes_neither(self) -> None:
        for old_rel, new_rel in ras.COUNCIL_ROLE_RENAMES:
            with self.subTest(old=old_rel), tempfile.TemporaryDirectory() as temp:
                root = self._tree(temp, old_rel)
                (root / new_rel).parent.mkdir(parents=True, exist_ok=True)
                (root / new_rel).write_bytes(b"new\n")
                before = {rel: (root / rel).read_bytes() for rel in (old_rel, new_rel)}
                with self.assertRaises(RuntimeError) as raised:
                    ras.migrate_council_role_renames(root)
                self.assertIn("both exist", str(raised.exception))
                self.assertEqual({rel: (root / rel).read_bytes() for rel in (old_rel, new_rel)}, before)

    def test_links_to_the_moved_doc_are_reported_not_rewritten(self) -> None:
        old_rel, _new_rel = ras.COUNCIL_ROLE_RENAMES[0]
        with tempfile.TemporaryDirectory() as temp:
            root = self._tree(temp, old_rel)
            peer = root / "docs" / "agents" / "specialists" / "peer.md"
            text = f"See [the chair]({Path(old_rel).name}).\n"
            peer.write_text(text, encoding="utf-8")
            result = ras.migrate_council_role_renames(root)
            self.assertEqual(result.link_report, ("docs/agents/specialists/peer.md:1",))
            self.assertEqual(peer.read_text(encoding="utf-8"), text)

    def test_docs_lint_accepts_the_legacy_and_the_migrated_role_doc(self) -> None:
        from wave_lint_lib.wave_validators import _check_agent_category_metadata, _check_agent_role_metadata
        old_rel, _new_rel = ras.COUNCIL_ROLE_RENAMES[0]
        with tempfile.TemporaryDirectory() as temp:
            root = self._tree(temp, old_rel)
            self.assertEqual(_check_agent_role_metadata(root) + _check_agent_category_metadata(root), [])
            ras.migrate_council_role_renames(root)
            self.assertEqual(_check_agent_role_metadata(root) + _check_agent_category_metadata(root), [])
            new = root / ras.COUNCIL_ROLE_RENAMES[0][1]
            new.write_text(new.read_text(encoding="utf-8").replace(f"Role: {LEGACY_ACTOR}", "Role: someone-else"),
                           encoding="utf-8")
            self.assertTrue(_check_agent_role_metadata(root))


# ---------------------------------------------------------------------------
# AC-8: the actor-token census over the shipped framework tree
# ---------------------------------------------------------------------------

ACTOR_TOKEN_RE = re.compile(re.escape(LEGACY_ACTOR) + r"(?![-\w])")
_SUFFIXES = {".py", ".md", ".json", ".toml", ".txt", ".yaml", ".yml"}
# Every shipped file still holding the earlier actor token, with its exact
# occurrence count and why: a legacy acceptance (Requirements 4 to 9) or a
# historical comment. A new occurrence, or one removed without updating this
# table, fails the census.
ACTOR_TOKEN_ALLOWLIST: dict[str, tuple[int, str]] = {
    "scripts/review_evidence.py": (1, "LEGACY_COUNCIL_ACTORS"),
    "scripts/review_policy.py": (2, "the digest copy maps the renamed moderator role to the earlier name"),
    "scripts/dashboard_lib.py": (1, "_COORDINATE_STEMS keeps the earlier role name"),
    "scripts/lifecycle_gate_support.py": (1, "comment: a config naming the earlier role is read as written"),
    "scripts/render_agent_surfaces.py": (4, "COUNCIL_ROLE_RENAMES old paths and its comment"),
    "scripts/wave_lint_lib/wave_validators.py": (6, "the earlier role doc path, Role alias, stems and roster tolerance"),
    "scripts/wave_lint_lib/constants.py": (1, "historical comment (wave 1p5b4 role renames)"),
    "scripts/wf_server/server_impl.py": (1, "the write-side actor alias docstring"),
    "seeds/160-upgrade-wavefoundry.prompt.md": (8, "the council role rename upgrade note"),
    "seeds/209-agent-harness-core.prompt.md": (1, "approvals recorded under the earlier name stay valid"),
    "scripts/tests/fixtures/prepare_council/1p9pe-wave-pre-corrective.md": (5, "frozen historical wave record"),
    "scripts/tests/server_tools_support.py": (1, "earlier key prefix test"),
    "scripts/tests/test_council_signoff_keys.py": (2, "pinned historical digest input and a legacy-ledger evidence string"),
    "scripts/tests/test_dashboard_server.py": (2, "the earlier role name stays a coordinate stem"),
    "scripts/tests/test_docs_lint.py": (3, "the earlier moderator name stays tolerated"),
    "scripts/tests/test_lifecycle_gates.py": (1, "earlier key prefix test"),
    "scripts/tests/test_lifecycle_golden.py": (1, "earlier key prefix test"),
    "scripts/tests/test_render_agent_surfaces.py": (1, "the closed 1skt1 change doc names the earlier path"),
    "scripts/tests/test_review_evidence.py": (2, "historical ledger actor and earlier key prefix test"),
    "scripts/tests/test_server_tools_lifecycle.py": (3, "a frozen fingerprinted run and earlier key prefix tests"),
}


def actor_token_census(framework: Path) -> dict[str, int]:
    """``{path relative to framework: occurrences}`` of the earlier actor token."""
    counts: dict[str, int] = {}
    for path in sorted(framework.rglob("*")):
        rel = path.relative_to(framework)
        if (not path.is_file() or path.suffix not in _SUFFIXES or "__pycache__" in rel.parts
                or rel.parts[0] in {"index", "cache"} or rel.name == "test-cache.json"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        count = len(ACTOR_TOKEN_RE.findall(text))
        if count:
            counts[rel.as_posix()] = count
    return counts


def census_problems(counts: dict[str, int]) -> list[str]:
    problems = []
    for rel, count in sorted(counts.items()):
        allowed = ACTOR_TOKEN_ALLOWLIST.get(rel, (0, ""))[0]
        if count != allowed:
            problems.append(f"{rel}: {count} occurrence(s), {allowed} allowed")
    for rel, (allowed, _why) in sorted(ACTOR_TOKEN_ALLOWLIST.items()):
        if rel not in counts:
            problems.append(f"{rel}: 0 occurrence(s), {allowed} allowed (stale entry)")
    return problems


def live_actor_token_census(root: Path) -> dict[str, int]:
    """Audit an explicitly supplied repository surface; never the consuming repo.

    Historical plans, wave ledgers and reports remain outside this census.
    A caller assesses the returned sites against its documented legacy sites.
    """
    paths = [root / name for name in ("AGENTS.md", "README.md", "docs/workflow-config.json",
                                     "install/install-log.template.md")]
    for area in ("agents", "prompts", "contributing", "references", "specs"):
        folder = root / "docs" / area
        if folder.exists():
            paths.extend(p for p in folder.rglob("*") if p.is_file() and p.suffix in _SUFFIXES
                         and not {"journals", "snapshots"}.intersection(p.relative_to(folder).parts))
    counts = {}
    for path in paths:
        if path.is_file():
            count = len(ACTOR_TOKEN_RE.findall(path.read_text(encoding="utf-8")))
            if count:
                counts[path.relative_to(root).as_posix()] = count
    changelog = root / "CHANGELOG.md"
    if changelog.is_file():
        text = changelog.read_text(encoding="utf-8")
        current = re.search(r"^## \[1\.29\.0\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.M | re.S)
        count = len(ACTOR_TOKEN_RE.findall(current.group(1))) if current else 0
        if count:
            counts["CHANGELOG.md"] = count
    return counts


class ActorTokenCensusTests(unittest.TestCase):
    def test_the_shipped_tree_holds_only_listed_occurrences(self) -> None:
        self.assertEqual(census_problems(actor_token_census(FRAMEWORK)), [])

    def test_a_reintroduced_live_carrier_is_found_without_reading_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            history_paths = (waves_dir(root) / "old" / vocabulary_profile.RECORD_FILENAME,
                             root / "docs/plans/old.md", root / "docs/reports/old.md",
                             root / "docs/architecture/decisions/old.md",
                             root / "docs/agents/snapshots/old.md")
            for path in history_paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"Role: {LEGACY_ACTOR}\n", encoding="utf-8")
            (root / "CHANGELOG.md").write_text(
                f"## [1.29.0]\nRole: {ACTOR}\n## [1.28.0]\nRole: {LEGACY_ACTOR}\n",
                encoding="utf-8")
            self.assertEqual(live_actor_token_census(root), {})
            carrier = root / "docs/agents/specialists/chair.md"
            carrier.parent.mkdir(parents=True, exist_ok=True)
            carrier.write_text(f"Role: {LEGACY_ACTOR}\n", encoding="utf-8")
            self.assertEqual(live_actor_token_census(root), {"docs/agents/specialists/chair.md": 1})

    def test_a_reintroduced_token_in_a_seed_fails_the_census(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            scratch = Path(temp) / "framework"
            (scratch / "seeds").mkdir(parents=True)
            (scratch / "seeds" / "999-scratch.prompt.md").write_text(
                f"The `{LEGACY_ACTOR}` synthesizes findings.\n", encoding="utf-8")
            problems = census_problems(actor_token_census(scratch))
            self.assertIn("seeds/999-scratch.prompt.md: 1 occurrence(s), 0 allowed", problems)


# ---------------------------------------------------------------------------
# AC-9: lifecycle_id follows wf_reload_mcp
# ---------------------------------------------------------------------------

_RELOAD_PROBE = r'''
import importlib, json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
from server_tools_support import _make_repo, load_server, load_thin_runner
with tempfile.TemporaryDirectory() as temp:
    root = _make_repo(Path(temp))
    load_server()
    runner = load_thin_runner()
    runner.build_server(root)
    try:
        import wave_lint_lib.secrets_validators  # binds lifecycle_id at import
        assert "spike" not in sys.modules["lifecycle_id"].KIND_CHOICES
        source = Path("vocabulary_profile.py")
        text = source.read_text()
        old = "EXTRA_CHANGE_KINDS: tuple[str, ...] = ()"
        assert text.count(old) == 1
        source.write_text(text.replace(old, 'EXTRA_CHANGE_KINDS: tuple[str, ...] = ("spike",)'))
        result = runner.perform_mcp_reload()
        assert result["status"] == "ok", result
        validators = importlib.import_module("wave_lint_lib.secrets_validators")
        module = importlib.import_module("lifecycle_id")
        print(json.dumps({
            "kind_choices_fresh": "spike" in sys.modules["lifecycle_id"].KIND_CHOICES,
            "validators_bind_fresh": validators.lifecycle_id is module,
        }))
    finally:
        runner._get_handler().close()
'''


class LifecycleIdReloadTests(unittest.TestCase):
    def test_reload_refreshes_lifecycle_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            scratch = Path(temp) / "scripts"
            shutil.copytree(SCRIPTS, scratch, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            result = subprocess.run(
                [sys.executable, "-B", "-c", _RELOAD_PROBE], cwd=scratch,
                env=dict(os.environ, PYTHONPATH=str(scratch), PYTHONDONTWRITEBYTECODE="1"),
                capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stderr[-4000:])
        self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1]),
                         {"kind_choices_fresh": True, "validators_bind_fresh": True})


# ---------------------------------------------------------------------------
# AC-12 to AC-15: the council display name
# ---------------------------------------------------------------------------

CARRIER_SEEDS_WITH_THE_NAME = ("214", "215", "225", "236", "237")


def _fixture_tree(temp: str) -> Path:
    root = Path(temp)
    shutil.copytree(FRAMEWORK / "seeds", root / ".wavefoundry" / "framework" / "seeds")
    return root


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".wavefoundry" not in path.relative_to(root).parts
    }


@contextlib.contextmanager
def _display_name(name: str):
    modules = {id(m): m for m in (vocabulary_profile, sys.modules.get("vocabulary_profile")) if m is not None}
    with contextlib.ExitStack() as stack:
        for module in modules.values():
            stack.enter_context(mock.patch.object(module, "COUNCIL_DISPLAY_NAME", name))
        yield


def _skill_description(name: str) -> str:
    [skill] = [s for s in ras.SKILL_REGISTRY if s.name == "wf-council"]
    return skill.description


class CouncilDisplayNameRenderTests(unittest.TestCase):
    def _render(self, temp: str) -> dict[str, bytes]:
        root = _fixture_tree(temp)
        ras.render_agent_surfaces(root)
        return _tree_bytes(root)

    def test_the_default_profile_renders_byte_identically_without_the_substitution(self) -> None:
        self.assertEqual(vocabulary_profile.COUNCIL_DISPLAY_NAME, SHIPPED_NAME)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            live = self._render(a)
            with mock.patch.object(vocabulary_profile, "localize_council_name", lambda text: text):
                baseline = self._render(b)
        self.assertTrue(live)
        self.assertEqual(sorted(live), sorted(baseline))
        for rel in live:
            with self.subTest(path=rel):
                self.assertEqual(live[rel], baseline[rel])

    def test_fresh_carriers_follow_a_renamed_council(self) -> None:
        carriers = {c.source_seed[:3]: c for c in ras.REVIEW_PROTOCOL_CARRIER_REGISTRY
                    if c.source_seed[:3] in CARRIER_SEEDS_WITH_THE_NAME}
        self.assertTrue(set(CARRIER_SEEDS_WITH_THE_NAME) <= set(carriers), sorted(carriers))
        with tempfile.TemporaryDirectory() as temp, _display_name("Review Board"):
            root = _fixture_tree(temp)
            for number, carrier in sorted(carriers.items()):
                with self.subTest(seed=number):
                    text = ras._initial_review_carrier_text(root, carrier)
                    self.assertIn("Review Board", text)
                    self.assertNotIn(SHIPPED_NAME, text)

    def test_the_renderer_literal_mutant_is_caught(self) -> None:
        # Mutant: the renderer reads the seed without the substitution step.
        carrier = next(c for c in ras.REVIEW_PROTOCOL_CARRIER_REGISTRY if c.source_seed.startswith("215"))
        with tempfile.TemporaryDirectory() as temp, _display_name("Review Board"), \
                mock.patch.object(vocabulary_profile, "localize_council_name", lambda text: text):
            text = ras._initial_review_carrier_text(_fixture_tree(temp), carrier)
        self.assertIn(SHIPPED_NAME, text)

    def test_an_existing_carrier_keeps_its_bytes_outside_the_managed_region(self) -> None:
        carrier = next(c for c in ras.REVIEW_PROTOCOL_CARRIER_REGISTRY if c.source_seed.startswith("215"))
        with tempfile.TemporaryDirectory() as temp, _display_name("Review Board"):
            root = _fixture_tree(temp)
            target = root / carrier.destination
            target.parent.mkdir(parents=True, exist_ok=True)
            prose = f"Owner: Engineering\nStatus: active\nRole: {ACTOR}\n\n# {SHIPPED_NAME}\n\nProject prose.\n"
            target.write_text(prose, encoding="utf-8")
            ras.render_agent_surfaces(root)
            text = target.read_text(encoding="utf-8")
            self.assertTrue(text.startswith(prose), text[:400])
            begin = text.index(ras.REVIEW_PROTOCOL_MARKER_BEGIN)
            self.assertNotIn(SHIPPED_NAME, text[begin:])

    def test_the_council_skill_description_takes_the_name(self) -> None:
        self.assertIn(f"role-based {vocabulary_profile.COUNCIL_DISPLAY_NAME},", _skill_description("x"))
        with _display_name("Review Board"):
            module = _exec_fresh("_ras_board", SCRIPTS / "render_agent_surfaces.py")
        [skill] = [s for s in module.SKILL_REGISTRY if s.name == "wf-council"]
        self.assertIn("role-based Review Board,", skill.description)
        self.assertNotIn(SHIPPED_NAME, skill.description)


class CouncilDisplayNameRuntimeTests(unittest.TestCase):
    @contextlib.contextmanager
    def _runtime_name(self, impl, name):
        modules = {id(m): m for m in (vocabulary_profile, sys.modules["vocabulary_profile"],
                                     impl._vocab, impl.lifecycle_gates._vocab)}
        with contextlib.ExitStack() as stack:
            for module in modules.values():
                stack.enter_context(mock.patch.object(module, "COUNCIL_DISPLAY_NAME", name))
            yield

    def test_public_legacy_prepare_and_implement_verdict_messages_take_the_name(self) -> None:
        from test_server_tools_lifecycle import CouncilVerdictLocationHintTests, _prepare_council_verdict_line
        fixture = CouncilVerdictLocationHintTests()
        fixture.setUpClass()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        malformed = f"- **Prepare-phase {SHIPPED_NAME} [prepare-council] — 2026-10-07: PASS** (moderator: {ACTOR})\n"
        for name in (SHIPPED_NAME, "Review Board"):
            with self._runtime_name(fixture.srv, name):
                parsed = fixture.srv._prepare_council_verdict_info(
                    "## Review Checkpoints\n\n" + _prepare_council_verdict_line())
                self.assertTrue(parsed["valid"], parsed)
                for checkpoints, code in (("", "prepare_council_verdict_missing"),
                                          (malformed, "prepare_council_verdict_invalid")):
                    for label, tool, mode in fixture.CALLS:
                        with self.subTest(name=name, verdict=code, route=label):
                            fixture._write(checkpoints=checkpoints)
                            response = fixture._run(getattr(fixture.srv, tool), fixture.root,
                                                    fixture.WAVE_ID, mode=mode)
                            messages = [d["message"] for d in response["diagnostics"] if d["code"] == code]
                            self.assertEqual(len(messages), 1, response)
                            self.assertIn(f"prepare-phase {name}", messages[0])
                            if name != SHIPPED_NAME:
                                self.assertNotIn(SHIPPED_NAME, messages[0])
                            if label == "prepare:create" and not checkpoints:
                                self.assertEqual(response["status"], "ready_for_council_review", response)
                                self.assertIn(f"prepare-phase {name}", response["usage"])

    def test_public_prepare_missing_typed_signoff_message_takes_the_name(self) -> None:
        from test_server_tools_lifecycle import WavePrepareCouncilGateTests
        fixture = WavePrepareCouncilGateTests()
        fixture.setUpClass()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        wave_id = fixture._make_wave("display-missing-signoff")
        with self._runtime_name(fixture.srv, "Review Board"), \
                mock.patch.object(fixture.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}), \
                mock.patch.object(fixture.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}), \
                mock.patch.object(fixture.srv, "_trigger_background_index_refresh_for_paths"):
            response = fixture.srv.wf_prepare_wave_response(fixture.root, wave_id, mode="create")
        self.assertEqual(response["status"], "error", response)
        messages = [d["message"] for d in response["diagnostics"] if d["code"] == "missing_wave_council_signoff"]
        self.assertEqual(len(messages), 1, response)
        self.assertIn("Required Review Board signoff missing for prepare:", messages[0])
        self.assertNotIn(SHIPPED_NAME, messages[0])

    def test_the_typed_verdict_template_hint_takes_the_name(self) -> None:
        import lifecycle_gate_support as support
        with _display_name("Review Board"):
            typed = support._prepare_council_verdict_template(None, typed=True)
            legacy = support._prepare_council_verdict_template(None)
        self.assertIn("Prepare-phase Review Board PASS", typed)
        self.assertIn(f"actor='{ACTOR}'", typed)
        self.assertNotIn(SHIPPED_NAME, typed)
        # The legacy checkpoint line is a parsed record format: fixed.
        self.assertIn(f"Prepare-phase {SHIPPED_NAME} [prepare-council]", legacy)

    def test_the_missing_verdict_lint_message_takes_the_name(self) -> None:
        import wave_lint_lib.wave_validators as validators
        root_text = (
            "# Wave Record\n\nStatus: implementing\n" + vocabulary_profile.id_line("1aaaa sample") + "\n\n## Review Checkpoints\n\n- none\n"
        )
        with tempfile.TemporaryDirectory() as temp, contextlib.ExitStack() as stack:
            for module in {id(m): m for m in (vocabulary_profile, validators._vocab)}.values():
                stack.enter_context(mock.patch.object(module, "COUNCIL_DISPLAY_NAME", "Review Board"))
            root = Path(temp)
            wave = waves_dir(root) / "1aaaa sample" / vocabulary_profile.RECORD_FILENAME
            wave.parent.mkdir(parents=True)
            wave.write_text(root_text, encoding="utf-8")
            errors, _warnings = validators.check_prepare_council_verdict(root)
        [message] = [e for e in errors if "prepare-council" in e]
        self.assertIn("run the prepare-phase Review Board review", message)
        self.assertNotIn(SHIPPED_NAME, message)

    def test_the_implement_wave_description_takes_the_name(self) -> None:
        from server_tools_support import _make_repo, load_server, load_thin_runner
        with tempfile.TemporaryDirectory() as temp:
            root = _make_repo(Path(temp))
            impl = load_server()
            runner = load_thin_runner()
            descriptions = {}
            for name in (SHIPPED_NAME, "Review Board"):
                with contextlib.ExitStack() as stack:
                    for module in {id(m): m for m in (vocabulary_profile, impl._vocab,
                                                       sys.modules["vocabulary_profile"])}.values():
                        stack.enter_context(mock.patch.object(module, "COUNCIL_DISPLAY_NAME", name))
                    mcp = runner.build_server(root)
                    try:
                        descriptions[name] = mcp._tool_manager._tools["wf_implement_wave"].description
                    finally:
                        runner._get_handler().close()
            self.assertIn(f"prepare-phase {SHIPPED_NAME} verdict", descriptions[SHIPPED_NAME])
            self.assertIn("prepare-phase Review Board verdict", descriptions["Review Board"])
            self.assertNotIn(SHIPPED_NAME, descriptions["Review Board"])


def _module_with(constant_line: str, replacement: str):
    """Execute a copy of ``vocabulary_profile`` with one constant line replaced."""
    text = (SCRIPTS / "vocabulary_profile.py").read_text(encoding="utf-8")
    assert text.count(constant_line) == 1, constant_line
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "_vocabulary_profile_probe.py"
        path.write_text(text.replace(constant_line, replacement), encoding="utf-8")
        return _exec_fresh("_vocabulary_profile_probe", path)


@contextlib.contextmanager
def _refused_at_import(test: unittest.TestCase, constant: str):
    """The probe copy raises its own ``VocabularyProfileInvalid`` naming ``constant``."""
    try:
        yield
    except ValueError as exc:
        test.assertEqual(type(exc).__name__, "VocabularyProfileInvalid")
        test.assertIn(constant, str(exc))
    else:
        test.fail(f"{constant}: the invalid value was accepted at import")


class ProfileValidationTests(unittest.TestCase):
    NAME_LINE = f'COUNCIL_DISPLAY_NAME: str = "{SHIPPED_NAME}"'
    KEYS_LINE = 'EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS: "dict[str, str]" = {}'

    def test_invalid_display_names_are_refused_at_import(self) -> None:
        for value in ("1", '""', '"  Board"', '"Board\\nTwo"', '"' + "b" * 65 + '"', '"Board`"',
                      '"Board*"', '"Board|"', '"Board["', '"Board]"', '"archetype council"',
                      '"Red-team"', '"red-TEAM"'):
            with self.subTest(value=value), _refused_at_import(self, "COUNCIL_DISPLAY_NAME"):
                _module_with(self.NAME_LINE, f"COUNCIL_DISPLAY_NAME = {value}")
        module = _module_with(self.NAME_LINE, 'COUNCIL_DISPLAY_NAME: str = "Review Board"')
        self.assertEqual(module.COUNCIL_DISPLAY_NAME, "Review Board")
        self.assertEqual(module.localize_council_name(f"the {SHIPPED_NAME}"), "the Review Board")

    def test_invalid_extra_council_keys_are_refused_at_import(self) -> None:
        for value in ("[]", '{"board-readiness": "council-review"}', '{1: "council-readiness"}',
                      '{"council-readiness": "council-delivery"}',
                      '{"' + LEGACY_ACTOR + '-readiness": "council-delivery"}',
                      '{"board-readiness": 2}'):
            with self.subTest(value=value), _refused_at_import(self, "EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS"):
                _module_with(self.KEYS_LINE, f"EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS = {value}")
        for extra in ({"board-readiness": "council-readiness"},
                      {"Review Board Readiness": "council-readiness"},
                      {LEGACY_ACTOR + "-readiness": "council-readiness"}):
            with self.subTest(extra=extra):
                module = _module_with(self.KEYS_LINE, f'EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS = {extra!r}')
                self.assertEqual(module.EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS, extra)


# Requirement 15 fixed sites: the legacy checkpoint line format (its template
# and both parse regexes).
DISPLAY_NAME_FIXED_SITES = {
    ("lifecycle_gate_support.py", "Prepare-phase " + SHIPPED_NAME + " [prepare-council]"),
    ("wf_server/server_impl.py", "Prepare-phase " + SHIPPED_NAME + r" \[prepare-council\]"),
    ("wave_lint_lib/wave_validators.py", "Prepare-phase " + SHIPPED_NAME + r" \[prepare-council\]"),
}


def _docstring_nodes(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                ids.add(id(first.value))
    return ids


def display_name_literals(source: str, rel: str) -> list[tuple[str, str]]:
    """``(file, literal)`` for each string literal (docstrings excluded) holding the display name."""
    tree = ast.parse(source)
    docstrings = _docstring_nodes(tree)
    found = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and SHIPPED_NAME in node.value and id(node) not in docstrings):
            found.append((rel, node.value))
    return found


class DisplayNameLiteralCensusTests(unittest.TestCase):
    def _unlisted(self, literals) -> list[tuple[str, str]]:
        return [(rel, value) for rel, value in literals
                if not any(rel == site and fixed in value for site, fixed in DISPLAY_NAME_FIXED_SITES)]

    def test_only_the_fixed_sites_hold_the_literal(self) -> None:
        literals = [
            hit
            for path in _framework_scripts()
            if path.name != "vocabulary_profile.py"
            for hit in display_name_literals(path.read_text(encoding="utf-8"), path.relative_to(SCRIPTS).as_posix())
        ]
        self.assertEqual(self._unlisted(literals), [])
        self.assertEqual({rel for rel, _ in literals}, {site for site, _ in DISPLAY_NAME_FIXED_SITES})

    def test_a_new_literal_fails_the_census(self) -> None:
        scratch = f'MESSAGE = "Run the {SHIPPED_NAME} review"\n'
        self.assertEqual(self._unlisted(display_name_literals(scratch, "scratch.py")),
                         [("scratch.py", f"Run the {SHIPPED_NAME} review")])


if __name__ == "__main__":
    unittest.main()
