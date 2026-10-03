"""Lifecycle tools honour the record-layout constants (wave 1y0gz / 1y042).

The layout is the ``record_paths`` module constants (``WAVES_ROOT``,
``PLANS_ROOT``, ``NESTED``, ``MAX_DEPTH``); tests relocate by patching them
through ``record_layout_support``. Nothing is read from configuration
(``test_record_paths`` pins that).

AC-2: relocated roots drive every lifecycle tool. AC-3: an invalid layout is
refused fail-closed with ``record_layout_invalid`` by EVERY decorated tool
and nothing is written. AC-6: the eight touched tools keep their input
schemas and ``record_paths`` is evicted on reload.
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from record_layout_support import SHIPPED_DEFAULTS, apply_layout, default_profile_only, patch_layout
from server_tools_support import _make_repo, load_server, load_thin_runner

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import vocabulary_profile as vp  # noqa: E402

# The shipped default roots, which a relocated layout must leave untouched.
SHIPPED_WAVES_ROOT = SHIPPED_DEFAULTS["record_paths"]["WAVES_ROOT"]
SHIPPED_PLANS_ROOT = SHIPPED_DEFAULTS["record_paths"]["PLANS_ROOT"]
GOLDEN_PATH = TESTS_DIR / "fixtures" / "tool-surface-golden.json"

RELOCATED = {"waves_root": "project/records/waves", "plans_root": "project/records/plans"}
EIGHT_TOOLS = (
    "wf_create_wave", "wf_add_change", "wf_remove_change", "wf_list_waves",
    "wf_list_plans", "wf_get_change", "wf_current_wave", "wf_prepare_wave",
)


class _RepoCase(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _layout(self, **kwargs) -> None:
        apply_layout(self, modules=(self.srv.record_paths,), **kwargs)

    def _all_paths_under(self, payload, prefix: str) -> None:
        """Every ``path`` string in a response payload starts with ``prefix``."""
        if isinstance(payload, dict):
            for key, value in payload.items():
                if key == "path" and isinstance(value, str):
                    normalized = value.replace("\\", "/")
                    self.assertTrue(
                        normalized.startswith(prefix) or f"/{prefix}" in normalized,
                        f"{value!r} not under {prefix!r}",
                    )
                    self.assertNotIn(f"{SHIPPED_WAVES_ROOT}/", normalized)
                    self.assertNotIn(f"{SHIPPED_PLANS_ROOT}/", normalized)
                else:
                    self._all_paths_under(value, prefix)
        elif isinstance(payload, list):
            for item in payload:
                self._all_paths_under(item, prefix)


class RelocatedRootsLifecycleTests(_RepoCase):
    """AC-2."""

    def setUp(self):
        super().setUp()
        self._layout(**RELOCATED)

    def test_every_lifecycle_tool_operates_on_the_configured_roots(self):
        created = self.srv.wf_create_wave_response(self.root, "relocated-demo", mode="create")
        self.assertEqual(created["status"], "ok", created)
        wave_id = created["data"]["wave_id"]
        wave_md = self.root / "project" / "records" / "waves" / wave_id / vp.RECORD_FILENAME
        self.assertTrue(wave_md.is_file(), "wave record must be created under the configured waves root")
        self.assertFalse((self.root / SHIPPED_WAVES_ROOT).exists(), "nothing may be written under the default root")

        plan = self.srv.change_create(self.root, "enh", "relocated-change", mode="create")
        change_id = plan["id"]
        self.assertTrue((self.root / "project" / "records" / "plans" / f"{change_id}.md").is_file())
        self.assertFalse((self.root / "docs" / "plans").exists())

        listed_plans = self.srv.wf_list_plans_response(self.root)
        self.assertEqual(listed_plans["status"], "ok", listed_plans)
        self.assertIn(change_id, [p["id"] for p in listed_plans["data"]["plans"]])
        self._all_paths_under(listed_plans["data"], "project/records/plans/")

        added = self.srv.wf_add_change_response(self.root, wave_id, change_id, mode="create")
        self.assertEqual(added["status"], "ok", added)
        self.assertTrue((wave_md.parent / f"{change_id}.md").is_file(), "admission relocates the doc into the wave folder under the configured root")

        listed = self.srv.wf_list_waves_response(self.root)
        self.assertEqual(listed["status"], "ok", listed)
        self.assertIn(wave_id, [w["wave_id"] for w in listed["data"]["waves"]])
        self._all_paths_under(listed["data"], "project/records/waves/")

        got = self.srv.wf_get_change_response(self.root, change_id)
        self.assertEqual(got["status"], "ok", got)
        self.assertEqual(got["data"]["change_id"], change_id)
        self._all_paths_under(got["data"], "project/records/waves/")

        current = self.srv.wf_current_wave_response(self.root)
        self.assertEqual(current["status"], "ok", current)
        self._all_paths_under(current["data"].get("waves", []), "project/records/waves/")

        prepared = self.srv.wf_prepare_wave_response(self.root, wave_id, mode="dry_run")
        self.assertIn(prepared["status"], ("ok", "error"))
        self.assertNotIn(
            "record_layout_invalid", [d.get("code") for d in prepared.get("diagnostics", [])]
        )
        self._all_paths_under(prepared.get("data", {}), "project/records/")

        removed = self.srv.wf_remove_change_response(self.root, wave_id, change_id, mode="create")
        self.assertEqual(removed["status"], "ok", removed)
        self.assertFalse((wave_md.parent / f"{change_id}.md").exists())
        self.assertTrue((self.root / "project" / "records" / "plans" / f"{change_id}.md").is_file(),
                        "removal returns the doc to the configured plans root")

    def test_repo_cache_fingerprint_follows_the_configured_root(self):
        cache = self.srv.McpRepoCache(self.root)
        before = cache._wave_fingerprint()
        self.srv.wf_create_wave_response(self.root, "fingerprint-demo", mode="create")
        self.assertNotEqual(before, cache._wave_fingerprint(), "a wave under the relocated root must move the cache key")
        self.assertEqual(len(cache.list_waves_cached()), 1)

    def test_warm_plans_cache_follows_a_plans_root_change_with_an_equal_fingerprint(self):
        # Finding `plans-cache-layout-key`: the plans key mirrors the waves
        # key (fingerprint, constants, paths), so a plans root moved by the
        # constants onto a byte-identical copy re-reads instead of serving
        # the old root's paths.
        plan = self.srv.change_create(self.root, "enh", "cached-plan", mode="create")
        cache = self.srv.McpRepoCache(self.root)
        first = self.srv.wf_list_plans_response(self.root, cache=cache)
        self.assertEqual([p["id"] for p in first["data"]["plans"]], [plan["id"]])
        self._all_paths_under(first["data"], "project/records/plans/")
        src = self.root / "project" / "records" / "plans"
        dst = self.root / "elsewhere" / "plans"
        shutil.copytree(src, dst, copy_function=shutil.copy2)
        shutil.copystat(src, dst)
        fingerprint = lambda d: self.srv._dir_fingerprint(d, "*.md", skip={"plan-template.md"})  # noqa: E731
        self.assertEqual(fingerprint(src), fingerprint(dst), "the copy must carry an identical fingerprint")
        with patch_layout(modules=(self.srv.record_paths,), plans_root="elsewhere/plans"):
            second = self.srv.wf_list_plans_response(self.root, cache=cache)
        self.assertEqual(second["status"], "ok", second)
        self.assertEqual([p["id"] for p in second["data"]["plans"]], [plan["id"]])
        self._all_paths_under(second["data"], "elsewhere/plans/")


class DefaultLayoutUnchangedTests(_RepoCase):
    """AC-1: path identity on the shipped layout."""

    @default_profile_only("pins path identity on the shipped layout")
    def test_default_paths_are_byte_identical(self):
        roots = self.srv.record_paths.load_record_roots(self.root)
        self.assertEqual(roots.waves, self.root / "docs" / "waves")
        self.assertEqual(self.srv.lifecycle_gate_support._plan_change_doc_path(self.root, "1abcd-enh x"), self.root / "docs" / "plans" / "1abcd-enh x.md")
        cache = self.srv.McpRepoCache(self.root)
        self.assertEqual(cache._wave_fingerprint(), self.srv._dir_fingerprint(self.root / "docs" / "waves", "wave.md", recursive=True))

    def test_error_message_points_at_the_constants_not_a_config_key(self):
        exc = self.srv.record_paths.RecordLayoutInvalid(["record_layout_invalid: record_paths.WAVES_ROOT must not contain '..': 'x'"])
        result = self.srv._record_layout_error_response("wf_create_wave", exc)
        message = result["diagnostics"][0]["message"]
        self.assertIn("record_paths.py", message)
        self.assertIn("WAVES_ROOT", message)
        self.assertNotIn("workflow-config", message)
        self.assertNotIn("`record_layout`", message)


class InvalidLayoutFailsClosedTests(_RepoCase):
    """AC-3: every invalid-layout class is refused by every decorated lifecycle
    tool (finding ``fail-closed-not-universal``) and writes nothing."""

    CASES = {
        "absolute": {"waves_root": "/tmp/elsewhere"},
        "dotdot": {"waves_root": "docs/../../outside"},
        "empty": {"waves_root": "   "},
        "equal": {"waves_root": "records", "plans_root": "records"},
        "nested": {"waves_root": "records", "plans_root": "records/plans"},
        "nested_type": {"nested": "yes"},
        "max_depth_range": {"max_depth": 0},
        # `_make_repo` writes docs/workflow-config.json: a root naming a file.
        "file_as_root": {"waves_root": "docs/workflow-config.json"},
        # Finding `dangling-symlink-root-invisible`: `_prepare_case` links
        # `records/waves` to a target that does not exist.
        "dangling_symlink_root": {"waves_root": "records/waves", "plans_root": "records/plans"},
    }

    def _prepare_case(self, label: str) -> bool:
        """Fixture setup for the cases that need on-disk state; False = skip."""
        if label == "dangling_symlink_root":
            if os.name == "nt":
                return False
            (self.root / "records").mkdir(exist_ok=True)
            os.symlink(self.root / "records" / "missing-target", self.root / "records" / "waves")
        return True

    def _decorated_calls(self):
        srv, root = self.srv, self.root
        return (
            ("wf_create_wave", lambda: srv.wf_create_wave_response(root, "x", mode="create")),
            ("wf_list_waves", lambda: srv.wf_list_waves_response(root)),
            ("wf_list_plans", lambda: srv.wf_list_plans_response(root)),
            ("wf_current_wave", lambda: srv.wf_current_wave_response(root)),
            ("wf_get_change", lambda: srv.wf_get_change_response(root, "1abcd")),
            ("wf_add_change", lambda: srv.wf_add_change_response(root, "1abcd", "1abce", mode="create")),
            ("wf_remove_change", lambda: srv.wf_remove_change_response(root, "1abcd", "1abce", mode="create")),
            ("wf_prepare_wave", lambda: srv.wf_prepare_wave_response(root, "1abcd", mode="dry_run")),
            ("wf_new_change", lambda: srv._change_create_response(root, "enh", "refused-change", mode="create")),
            ("wf_review_event", lambda: srv.wf_review_event_response(
                root, "1abcd", "approval", "qa", "ctx-1", mode="create", signoff_key="qa",
            )),
            ("wf_close_wave", lambda: srv.wf_close_wave_response(root, "1abcd", mode="create")),
            ("wf_close_change", lambda: srv.wf_close_change_response(root, "1abcd", "1abce", mode="create")),
            ("wf_pause_wave", lambda: srv.wf_pause_wave_response(root, "1abcd", mode="create")),
            ("wf_implement_wave", lambda: srv.wf_implement_wave_response(root, "1abcd", mode="create")),
            ("wf_review_wave", lambda: srv.wf_review_wave_response(root, "1abcd")),
            ("wf_audit", lambda: srv.wf_audit_response(root)),
            ("wf_reopen_wave", lambda: srv.wf_reopen_wave_response(root, "1abcd")),
            # Finding `mark-item-decorator-unpinned`: both mark tools share the
            # `wf_mark_item`-decorated response path.
            ("wf_mark_item", lambda: srv._mark_change_item_response(
                root, "1abcd", "1abce", "AC-1", "x", target_section="Acceptance Criteria", mode="create",
            )),
            ("wf_mark_item", lambda: srv._mark_change_item_response(
                root, "1abcd", "1abce", "Task one", "x", target_section="Tasks", mode="create",
            )),
        )

    def _assert_refused(self, label: str) -> None:
        snapshot = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        for tool, call in self._decorated_calls():
            with self.subTest(case=label, tool=tool):
                result = call()
                self.assertEqual(result["status"], "error", result)
                self.assertEqual(result["diagnostics"][0]["code"], "record_layout_invalid", result)
                self.assertEqual(result["data"]["tool"], tool)
                self.assertIn("record_paths.py", result["diagnostics"][0]["message"])
        after = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        self.assertEqual(after, snapshot, f"{label}: an invalid layout must write nothing")

    def test_each_invalid_class_is_refused_by_every_decorated_tool(self):
        for label, layout in self.CASES.items():
            if not self._prepare_case(label):
                continue
            with patch_layout(modules=(self.srv.record_paths,), **layout):
                self._assert_refused(label)
        if os.name != "nt":
            self.assertFalse(
                (self.root / "records" / "missing-target").exists(),
                "nothing may be created through the dangling link",
            )

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_escaping_symlink_is_refused(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (self.root / "records").mkdir()
        os.symlink(outside.name, self.root / "records" / "waves")
        self._layout(waves_root="records/waves", plans_root="records/plans")
        self._assert_refused("escaping_symlink")
        self.assertEqual(os.listdir(outside.name), [], "nothing may be written through the link")

    def test_ranking_helpers_never_refuse(self):
        # Ranking is observational: an invalid layout degrades to the
        # unvalidated prefixes instead of raising.
        self._layout(waves_root="/abs")
        prefixes = self.srv._record_prefixes(self.root)
        self.assertEqual(len(prefixes), 2)
        self.assertTrue(all(isinstance(p, str) and p.endswith("/") for p in prefixes), prefixes)
        self.assertEqual(prefixes[1], "docs/plans/")
        self.assertEqual(
            self.srv._trust_label("docs/plans/1abcd-enh x.md", prefixes=prefixes),
            self.srv.TRUSTED_PROJECT_METADATA,
        )


class WrapperFailClosedTests(_RepoCase):
    """Finding `fail-closed-wrapper-telemetry`: the REGISTERED tools (the
    `mcp.tool` wrappers, which re-resolve the wave for telemetry after the
    response function returned) hand back the structured refusal and never
    raise, for an invalid layout and for a duplicated wave id."""

    NESTED_LAYOUT = {
        "waves_root": "project/records/waves", "plans_root": "project/records/plans",
        "nested": True, "max_depth": 4,
    }

    def setUp(self):
        super().setUp()
        self.runner = load_thin_runner()
        try:
            self.mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

    def _tool(self, name):
        return self.mcp._tool_manager._tools[name].fn

    def _calls(self, wave_id: str):
        return (
            ("wf_prepare_wave", lambda: self._tool("wf_prepare_wave")(wave_id, mode="dry_run")),
            ("wf_close_wave", lambda: self._tool("wf_close_wave")(wave_id, mode="dry_run")),
            ("wf_close_change", lambda: self._tool("wf_close_change")(wave_id, "1abce", mode="dry_run")),
            ("wf_implement_wave", lambda: self._tool("wf_implement_wave")(wave_id, mode="dry_run")),
            ("wf_review_wave", lambda: self._tool("wf_review_wave")(wave_id)),
            ("wf_mark_ac", lambda: self._tool("wf_mark_ac")(wave_id, "1abce", "AC-1", "x", mode="dry_run")),
            ("wf_mark_task", lambda: self._tool("wf_mark_task")(wave_id, "1abce", "Task one", "x", mode="dry_run")),
            ("wf_pause_wave", lambda: self._tool("wf_pause_wave")(wave_id, mode="dry_run")),
            ("wf_reopen_wave", lambda: self._tool("wf_reopen_wave")(wave_id, purpose="review")),
        )

    def _snapshot(self) -> list[str]:
        # Telemetry may legitimately persist under `.wavefoundry/`; the record
        # tree itself must be untouched.
        return sorted(
            str(p.relative_to(self.root)) for p in self.root.rglob("*")
            if ".wavefoundry" not in p.relative_to(self.root).parts
        )

    def _assert_every_wrapper_refuses(self, wave_id: str, code: str) -> None:
        before = self._snapshot()
        for tool, call in self._calls(wave_id):
            with self.subTest(tool=tool):
                try:
                    result = call()
                except Exception as exc:  # the defect: telemetry re-raising the refusal
                    self.fail(f"{tool} raised {type(exc).__name__}: {exc}")
                self.assertIsInstance(result, dict, (tool, result))
                self.assertEqual(result["status"], "error", (tool, result))
                self.assertEqual(result["diagnostics"][0]["code"], code, (tool, result))
        self.assertEqual(before, self._snapshot(), "a refusal must write nothing under the record tree")

    def test_invalid_layout_is_refused_by_every_registered_wrapper(self):
        self._layout(waves_root="../x")
        self._assert_every_wrapper_refuses("1abcd", "record_layout_invalid")

    def test_duplicated_wave_id_is_refused_by_every_registered_wrapper(self):
        self._layout(**self.NESTED_LAYOUT)
        created = self.srv.wf_create_wave_response(self.root, "dup", mode="create")
        self.assertEqual(created["status"], "ok", created)
        wave_id = created["data"]["wave_id"]
        waves = self.root / "project" / "records" / "waves"
        twin = waves / "team" / wave_id
        twin.parent.mkdir(parents=True)
        shutil.copytree(waves / wave_id, twin)
        self._assert_every_wrapper_refuses(wave_id, "ambiguous_wave_id")


def core_schema_drift(tool: str, golden: dict, live: dict) -> list[str]:
    """Change 1zltu: how a live ``inputSchema`` drifted from the golden core.

    Every golden property must exist live with an identical property schema
    (type or ``anyOf``, ``default`` presence and value, ``title``), and the
    live ``required`` set must equal the golden one. A live property the
    golden lacks is allowed only when it is optional (an override may add
    one); an added required parameter is drift. Returns one message per
    problem, empty when the core contract holds.
    """
    problems: list[str] = []
    golden_props = golden.get("properties", {})
    live_props = live.get("properties", {})
    golden_required = set(golden.get("required", []))
    live_required = set(live.get("required", []))
    for param, schema in sorted(golden_props.items()):
        if param not in live_props:
            problems.append(f"{tool}: core parameter {param!r} is missing")
        elif live_props[param] != schema:
            problems.append(f"{tool}: core parameter {param!r} changed: {live_props[param]!r} != {schema!r}")
    for param in sorted(set(live_props) - set(golden_props)):
        if param in live_required:
            problems.append(f"{tool}: added parameter {param!r} is required")
    if live_required != golden_required:
        problems.append(
            f"{tool}: required set drifted: {sorted(live_required)} != {sorted(golden_required)}")
    return problems


class CreateWaveParentTests(_RepoCase):
    """Wave 1zlu1 (change 1zlu3): `wf_create_wave(..., parent=...)` creates a
    wave inside an existing grouping folder of the nested layout."""

    NESTED = {**RELOCATED, "nested": True, "max_depth": 4}

    def setUp(self):
        super().setUp()
        self._layout(**self.NESTED)
        self.waves = self.root / "project" / "records" / "waves"
        self.waves.mkdir(parents=True, exist_ok=True)
        lint = unittest.mock.patch.object(self.srv, "_attach_lint_to_response", side_effect=lambda e, *a, **k: e)
        lint.start()
        self.addCleanup(lint.stop)

    def _snapshot(self) -> list[str]:
        return sorted(
            str(p.relative_to(self.root)) for p in self.root.rglob("*")
            if ".wavefoundry" not in p.relative_to(self.root).parts
        )

    def _next_prefix(self) -> str:
        return self.srv._lifecycle_module().build_id(
            "wave", "probe", legacy=False, commit=False, repo_root=self.root
        ).split(" ", 1)[0]

    def _create(self, parent, mode="create", slug="grouped"):
        return self.srv.wf_create_wave_response(self.root, slug, mode=mode, parent=parent)

    def test_creates_inside_an_existing_parent(self):
        (self.waves / "q4" / "auth").mkdir(parents=True)
        before = self._snapshot()
        dry = self._create("q4/auth", mode="dry_run")
        self.assertEqual(dry["status"], "dry_run", dry)
        self.assertEqual(self._snapshot(), before)
        created = self._create("q4/auth")
        self.assertEqual(created["status"], "ok", created)
        data = created["data"]
        self.assertEqual(data["parent"], "q4/auth")
        self.assertEqual(dry["data"]["parent"], "q4/auth")
        self.assertEqual(dry["data"]["path"], data["path"])
        self.assertTrue(data["path"].startswith("project/records/waves/q4/auth/"), data["path"])
        wave_dir = (self.root / data["path"]).parent
        self.assertTrue((wave_dir / vp.RECORD_FILENAME).is_file())
        self.assertTrue((wave_dir / "events.jsonl").is_file())
        listed = self.srv.wf_list_waves_response(self.root)["data"]["waves"]
        entry = next(w for w in listed if w["wave_id"] == data["wave_id"])
        self.assertEqual(entry["parent"], "q4/auth")
        current = self.srv.wf_current_wave_response(self.root)["data"]["waves"]
        self.assertIn(data["wave_id"], [w["wave_id"] for w in current])
        from wave_lint_lib import wave_validators
        failures = [f for f in wave_validators.check_wave_docs(self.root) if data["wave_id"] in f]
        self.assertEqual(failures, [])

    def test_direct_child_lists_a_null_parent(self):
        created = self.srv.wf_create_wave_response(self.root, "flat-child", mode="create")
        self.assertIsNone(created["data"]["parent"])
        listed = self.srv.wf_list_waves_response(self.root)["data"]["waves"]
        self.assertEqual([w["parent"] for w in listed], [None])

    def _assert_refused(self, parent, *, fragment: str = "") -> None:
        before, prefix = self._snapshot(), self._next_prefix()
        for mode in ("dry_run", "create"):
            with self.subTest(parent=parent, mode=mode):
                result = self._create(parent, mode=mode)
                self.assertEqual(result["status"], "error", result)
                self.assertEqual([d["code"] for d in result["diagnostics"]], ["invalid_arguments"], result)
                if fragment:
                    self.assertIn(fragment, result["diagnostics"][0]["message"])
                self.assertEqual(self._snapshot(), before, "a refused parent creates nothing")
                self.assertEqual(self._next_prefix(), prefix, "a refused parent consumes no prefix")

    def test_flat_layout_refuses_parent(self):
        self._layout(**{**RELOCATED, "nested": False})
        (self.waves / "q4").mkdir()
        self._assert_refused("q4", fragment="NESTED")

    def test_empty_values_are_refused(self):
        for value in ("", "   ", "///", "\\\\"):
            self._assert_refused(value, fragment="empty")

    def test_absolute_values_are_refused(self):
        # Each value names folders that exist once read as relative, so only
        # the absolute check can refuse it.
        (self.waves / "abs").mkdir()
        (self.waves / "server" / "share").mkdir(parents=True)
        self._assert_refused("/abs", fragment="absolute")
        self._assert_refused("\\\\server\\share", fragment="absolute")
        if os.name != "nt":
            (self.waves / "C:" / "x").mkdir(parents=True)
        self._assert_refused("C:\\x", fragment="absolute")

    def test_dot_dot_and_dot_prefixed_components_are_refused(self):
        for name in ("a", "b", ".hidden"):
            (self.waves / name).mkdir()
        self._assert_refused("a/../b", fragment="'..'")
        self._assert_refused(".hidden", fragment="'.hidden'")

    @unittest.skipIf(os.name == "nt", "creating a symlink needs a privilege on Windows")
    def test_symlinked_component_is_refused(self):
        (self.waves / "real").mkdir()
        os.symlink(self.waves / "real", self.waves / "link", target_is_directory=True)
        self._assert_refused("link", fragment="symlink")

    def test_folder_inside_a_wave_folder_is_refused(self):
        (self.waves / "w1" / "sub").mkdir(parents=True)
        (self.waves / "w1" / vp.RECORD_FILENAME).write_text("x\n", encoding="utf-8")
        self._assert_refused("w1", fragment="inside the wave folder")
        self._assert_refused("w1/sub", fragment="inside the wave folder")

    def test_parent_at_max_depth_is_refused(self):
        (self.waves / "a" / "b" / "c" / "d").mkdir(parents=True)
        self._assert_refused("a/b/c/d", fragment="discovery depth")
        created = self._create("a/b/c")
        self.assertEqual(created["status"], "ok", created)

    def test_missing_parent_and_file_parent_are_refused(self):
        (self.waves / "file.txt").write_text("x\n", encoding="utf-8")
        self._assert_refused("missing", fragment="does not exist")
        self._assert_refused("file.txt", fragment="does not exist")

    def test_depth_rule_matches_discovery(self):
        for max_depth in (1, 2):
            with self.subTest(max_depth=max_depth):
                self._layout(**{**self.NESTED, "max_depth": max_depth})
                (self.waves / f"g{max_depth}" / "h").mkdir(parents=True)
                deepest = "/".join([f"g{max_depth}", "h"][: max_depth - 1])
                if deepest:
                    created = self._create(deepest, slug=f"depth-{max_depth}")
                    self.assertEqual(created["status"], "ok", created)
                    found = [w["wave_id"] for w in self.srv.list_waves(self.root)]
                    self.assertIn(created["data"]["wave_id"], found)
                one_deeper = "/".join([f"g{max_depth}", "h"][:max_depth])
                self._assert_refused(one_deeper, fragment="discovery depth")

    def test_colliding_id_prefix_is_refused(self):
        (self.waves / "q4").mkdir()
        other = self.waves / "elsewhere" / "1abcd old"
        other.mkdir(parents=True)
        (other / vp.RECORD_FILENAME).write_text(f"{vp.RECORD_TITLE}\n\nStatus: planned\n", encoding="utf-8")
        before = self._snapshot()
        lifecycle = self.srv._lifecycle_module()
        with unittest.mock.patch.object(lifecycle, "build_id", return_value="1abcd new"):
            result = self._create("q4")
        self.assertEqual(result["status"], "error", result)
        self.assertEqual([d["code"] for d in result["diagnostics"]], ["ambiguous_wave_id"])
        self.assertEqual(self._snapshot(), before)

    @unittest.skipIf(os.name == "nt", "creating a symlink needs a privilege on Windows")
    def test_parent_swapped_for_a_symlink_after_validation_is_refused(self):
        (self.waves / "q4").mkdir()
        real = self.srv._wave_parent_parts

        def swap(roots, parent):
            parts = real(roots, parent)
            os.rename(self.waves / "q4", self.waves / "q4-real")
            os.symlink(self.waves / "q4-real", self.waves / "q4", target_is_directory=True)
            return parts

        with unittest.mock.patch.object(self.srv, "_wave_parent_parts", side_effect=swap):
            result = self._create("q4")
        self.assertEqual(result["status"], "error", result)
        self.assertIn("changed during creation", result["diagnostics"][0]["message"])
        self.assertEqual(list((self.waves / "q4-real").iterdir()), [])

    @unittest.skipIf(os.name == "nt", "creating a symlink needs a privilege on Windows")
    def test_parent_swapped_for_an_outside_symlink_after_the_recheck_writes_nothing_outside(self):
        """Delivery review F1: a swap after the in-lock re-check (here inside
        `wave_id_of`) must not let the record be written outside the repo."""
        (self.waves / "q4").mkdir()
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        outside_dir = Path(outside.name)
        real = self.srv.record_paths.wave_id_of
        swapped = []

        def swap(wave_dir):
            if not swapped:
                swapped.append(True)
                os.rename(self.waves / "q4", self.waves / "q4-real")
                os.symlink(outside_dir, self.waves / "q4", target_is_directory=True)
            return real(wave_dir)

        with unittest.mock.patch.object(self.srv.record_paths, "wave_id_of", side_effect=swap):
            result = self._create("q4")
        self.assertTrue(swapped)
        self.assertEqual(result["status"], "error", result)
        self.assertEqual([d["code"] for d in result["diagnostics"]], ["invalid_arguments"])
        self.assertEqual(list(outside_dir.iterdir()), [], "nothing is written or left outside the repo")
        self.assertEqual(list((self.waves / "q4-real").iterdir()), [])

    def test_parent_is_reported_as_spelled_on_disk(self):
        (self.waves / "Q4" / "Auth").mkdir(parents=True)
        if not (self.waves / "q4" / "auth").exists():
            self.skipTest("case-sensitive filesystem")
        created = self._create("q4/auth")
        self.assertEqual(created["status"], "ok", created)
        self.assertEqual(created["data"]["parent"], "Q4/Auth")

    def test_without_parent_the_result_is_unchanged(self):
        self._layout(**RELOCATED)
        dry = self.srv.wf_create_wave_response(self.root, "plain", mode="dry_run")
        created = self.srv.wf_create_wave_response(self.root, "plain", mode="create")
        self.assertIsNone(dry["data"]["parent"])
        self.assertIsNone(created["data"]["parent"])
        self.assertEqual(Path(created["data"]["path"]).parent.parent.as_posix(), RELOCATED["waves_root"])


class SchemaPinAndReloadTests(unittest.TestCase):
    """AC-6."""

    def test_core_schema_drift_on_synthetic_schemas(self):
        """Change 1zltu: identical and extra-optional pass; extra-required and a
        changed type or default on a core parameter fail."""
        golden = {
            "properties": {
                "change_id": {"title": "Change Id", "type": "string"},
                "mode": {"default": "dry_run", "title": "Mode", "type": "string"},
            },
            "required": ["change_id"],
        }

        def variant(**edits):
            live = json.loads(json.dumps(golden))
            for key, value in edits.items():
                if key == "required":
                    live["required"] = value
                else:
                    live["properties"][key] = value
            return live

        self.assertEqual(core_schema_drift("t", golden, variant()), [])
        self.assertEqual(core_schema_drift("t", golden, variant(extra={"default": None, "title": "Extra"})), [])
        added_required = core_schema_drift(
            "t", golden, variant(extra={"title": "Extra", "type": "string"}, required=["change_id", "extra"]))
        self.assertTrue(added_required)
        self.assertTrue(any("'extra'" in p and "required" in p and p.startswith("t:") for p in added_required))
        self.assertTrue(core_schema_drift("t", golden, variant(mode={"default": "dry_run", "title": "Mode", "type": "integer"})))
        self.assertTrue(core_schema_drift("t", golden, variant(mode={"default": "create", "title": "Mode", "type": "string"})))
        self.assertTrue(core_schema_drift("t", golden, variant(mode={"title": "Mode", "type": "string"})))
        self.assertTrue(core_schema_drift("t", golden, variant(required=[])))

    def test_eight_lifecycle_tool_schemas_match_the_golden_fixture(self):
        golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))["tools"]
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError:
            self.skipTest("mcp package not installed")
        srv = load_server()
        mcp = FastMCP("pin")
        srv.register_mcp_surface(mcp, lambda: None)
        for name in EIGHT_TOOLS:
            with self.subTest(tool=name):
                live = mcp._tool_manager._tools[name].parameters
                # Change 1zltu: compare the core contract fully (types,
                # defaults, titles, required), not only parameter names.
                self.assertEqual(core_schema_drift(name, golden[name]["inputSchema"], live), [],
                                 f"{name}: core schema drifted from the golden fixture")

    def test_record_paths_is_evicted_on_reload(self):
        srv = load_server()
        before = sys.modules["record_paths"]
        importlib.reload(srv)
        self.assertIsNot(sys.modules["record_paths"], before, "record_paths must be re-imported by the eviction block")
        self.assertIs(sys.modules["record_paths"], srv.record_paths)


if __name__ == "__main__":
    unittest.main()
