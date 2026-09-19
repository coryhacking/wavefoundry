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
from pathlib import Path

from record_layout_support import apply_layout, patch_layout
from server_tools_support import _make_repo, load_server, load_thin_runner

TESTS_DIR = Path(__file__).resolve().parent
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
                    self.assertNotIn("docs/waves/", normalized)
                    self.assertNotIn("docs/plans/", normalized)
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
        wave_md = self.root / "project" / "records" / "waves" / wave_id / "wave.md"
        self.assertTrue(wave_md.is_file(), "wave record must be created under the configured waves root")
        self.assertFalse((self.root / "docs" / "waves").exists(), "nothing may be written under the default root")

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


class SchemaPinAndReloadTests(unittest.TestCase):
    """AC-6."""

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
                self.assertEqual(
                    sorted(live["properties"]), sorted(golden[name]["inputSchema"]["properties"]),
                    f"{name}: parameter set drifted from the golden fixture",
                )

    def test_record_paths_is_evicted_on_reload(self):
        srv = load_server()
        before = sys.modules["record_paths"]
        importlib.reload(srv)
        self.assertIsNot(sys.modules["record_paths"], before, "record_paths must be re-imported by the eviction block")
        self.assertIs(sys.modules["record_paths"], srv.record_paths)


if __name__ == "__main__":
    unittest.main()
