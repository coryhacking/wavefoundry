"""Nested wave discovery through the lifecycle tools (wave 1y0gz / 1y043).

The layout is the ``record_paths`` module constants; tests patch them
through ``record_layout_support``.

AC-2: waves at depth one, two, and three resolve through every listed tool
and through docs-lint's wave validators, and are tagged ``wave``.
AC-3: a duplicate id at two depths is refused with ``ambiguous_wave_id`` by
EVERY lifecycle tool that resolves a wave id (finding
``ambiguous-id-not-universal``), reported identically by docs-lint, and no
mutation runs.
AC-4c: one lifecycle invocation walks once, on a cold AND a warm cache; the
warm cache re-reads after a layout flip or a moved wave folder (finding
``warm-cache-layout-flip``).
AC-5: moving a wave folder deeper leaves every lookup by id working.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from record_layout_support import apply_layout, patch_layout
from server_tools_support import _make_repo, load_server, load_thin_runner

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

WAVES_REL = "project/records/waves"
PLANS_REL = "project/records/plans"
NESTED_LAYOUT = {"waves_root": WAVES_REL, "plans_root": PLANS_REL, "nested": True, "max_depth": 4}


class _NestedRepo(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        self._layout(**NESTED_LAYOUT)
        self.waves = self.root / "project" / "records" / "waves"

    def tearDown(self):
        self.tmp.cleanup()

    def _layout(self, **kwargs) -> None:
        apply_layout(self, modules=(self.srv.record_paths,), **kwargs)

    def _patched(self, **kwargs):
        return patch_layout(modules=(self.srv.record_paths,), **kwargs)

    def _snapshot(self) -> list[str]:
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))

    def _create_wave(self, slug: str, group: str = "") -> tuple[str, Path]:
        created = self.srv.wf_create_wave_response(self.root, slug, mode="create")
        self.assertEqual(created["status"], "ok", created)
        wave_id = created["data"]["wave_id"]
        src = self.waves / wave_id
        if group:
            dst = self.waves.joinpath(*group.split("/")) / wave_id
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return wave_id, dst
        return wave_id, src

    def _counting_walk(self):
        """``(patch context, calls)`` counting ``record_paths.discover_wave_dirs``."""
        real = self.srv.record_paths.discover_wave_dirs
        calls: list[Path] = []

        def counting(root, roots=None):
            calls.append(root)
            return real(root, roots)

        return patch.object(self.srv.record_paths, "discover_wave_dirs", counting), calls


class NestedLifecycleTests(_NestedRepo):
    def test_every_tool_resolves_waves_at_three_depths(self):
        w1, d1 = self._create_wave("depth-one")
        w2, d2 = self._create_wave("depth-two", "team")
        w3, d3 = self._create_wave("depth-three", "team/feature")
        listed = self.srv.wf_list_waves_response(self.root)
        self.assertEqual(listed["status"], "ok", listed)
        self.assertEqual(sorted(w["wave_id"] for w in listed["data"]["waves"]), sorted([w1, w2, w3]))
        current = self.srv.wf_current_wave_response(self.root)
        self.assertEqual(current["status"], "ok", current)
        self.assertEqual(sorted(w["wave_id"] for w in current["data"]["waves"]), sorted([w1, w2, w3]))

        plan = self.srv.change_create(self.root, "enh", "nested-change", mode="create")
        change_id = plan["id"]
        added = self.srv.wf_add_change_response(self.root, w3, change_id, mode="create")
        self.assertEqual(added["status"], "ok", added)
        self.assertTrue((d3 / f"{change_id}.md").is_file(), "admission lands in the depth-three wave folder")
        got = self.srv.wf_get_change_response(self.root, change_id[:5])
        self.assertEqual(got["status"], "ok", got)
        self.assertIn(f"{WAVES_REL}/team/feature/{w3}/{change_id}.md", json.dumps(got["data"]))
        prepared = self.srv.wf_prepare_wave_response(self.root, w3, mode="dry_run")
        self.assertIn(prepared["status"], ("ok", "error"))
        self.assertNotIn("ambiguous_wave_id", [d.get("code") for d in prepared.get("diagnostics", [])])
        removed = self.srv.wf_remove_change_response(self.root, w3, change_id, mode="create")
        self.assertEqual(removed["status"], "ok", removed)
        self.assertFalse((d3 / f"{change_id}.md").exists())

        # docs-lint's wave validators see every wave and report nothing about depth.
        from wave_lint_lib import wave_validators as wv

        # The minimal fixture lacks unrelated required paths; only wave-shaped
        # findings matter here.
        self.assertEqual([l for l in wv.check_wave_roots(self.root) if "ambiguous" in l], [])
        self.assertEqual(wv.check_orphan_wave_ledgers(self.root), [])
        state, _records = wv._collect_wave_state(self.root)
        self.assertEqual(sorted(state), sorted([w1, w2, w3]))

        # The indexer's wave classification is depth independent, on the
        # chunker binding and on the server's live path (which derives the
        # prefix from the repository root).
        import chunker

        prefix = self.srv.record_paths.load_record_roots(self.root).waves_prefix
        deep = f"{WAVES_REL}/team/feature/{w3}/wave.md"
        self.assertIn("wave", chunker._infer_tags(deep, waves_prefix=prefix))
        self.assertIn("wave", self.srv._infer_tags(deep, root=self.root))

    def test_relocating_a_wave_deeper_keeps_every_lookup_working(self):
        # AC-5
        w1, d1 = self._create_wave("moves-later")
        plan = self.srv.change_create(self.root, "enh", "moving-change", mode="create")
        change_id = plan["id"]
        self.assertEqual(self.srv.wf_add_change_response(self.root, w1, change_id, mode="create")["status"], "ok")
        deep = self.waves / "a" / "b" / w1
        deep.parent.mkdir(parents=True)
        shutil.move(str(d1), str(deep))
        self.assertEqual(self.srv._find_wave_md(self.root, w1), deep / "wave.md")
        got = self.srv.wf_get_change_response(self.root, change_id)
        self.assertEqual(got["status"], "ok", got)
        current = self.srv.wf_current_wave_response(self.root)
        self.assertEqual([w["wave_id"] for w in current["data"]["waves"]], [w1])
        self.assertIn(f"{WAVES_REL}/a/b/{w1}/wave.md", current["data"]["waves"][0]["path"])

    def test_flat_layout_default_ignores_nested_folders(self):
        # AC-1: with NESTED false, a wave placed one level deeper is invisible.
        self._layout(nested=False)
        w1, _ = self._create_wave("flat-one")
        w2, _ = self._create_wave("flat-two", "group")
        listed = self.srv.wf_list_waves_response(self.root)
        self.assertEqual([w["wave_id"] for w in listed["data"]["waves"]], [w1])


class AmbiguousWaveIdTests(_NestedRepo):
    def _duplicate(self) -> tuple[str, Path, Path]:
        w1, d1 = self._create_wave("dup")
        twin = self.waves / "team" / w1
        twin.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(d1, twin)
        return w1, d1, twin

    def _assert_ambiguous(self, tool: str, result: dict, w1: str) -> None:
        self.assertEqual(result["status"], "error", (tool, result))
        self.assertEqual(result["diagnostics"][0]["code"], "ambiguous_wave_id", (tool, result))
        self.assertEqual(result["data"]["tool"], tool, result)
        message = result["diagnostics"][0]["message"]
        self.assertIn(f"{WAVES_REL}/{w1}", message)
        self.assertIn(f"{WAVES_REL}/team/{w1}", message)

    def test_current_wave_and_lint_report_both_paths_and_no_mutation_proceeds(self):
        w1, d1, twin = self._duplicate()
        current = self.srv.wf_current_wave_response(self.root)
        self._assert_ambiguous("wf_current_wave", current, w1)

        from wave_lint_lib import wave_validators as wv

        lint_lines = [l for l in wv.check_wave_roots(self.root) if l.startswith("ambiguous_wave_id:")]
        self.assertEqual(len(lint_lines), 1)
        self.assertTrue(lint_lines[0].startswith(f"ambiguous_wave_id: {w1.split(' ', 1)[0]} at "))
        self.assertEqual(lint_lines[0], current["data"]["ambiguous_wave_ids"][0])

        plan = self.srv.change_create(self.root, "enh", "blocked-change", mode="create")
        before = self._snapshot()
        added = self.srv.wf_add_change_response(self.root, w1, plan["id"], mode="create")
        self._assert_ambiguous("wf_add_change", added, w1)
        self.assertEqual(before, self._snapshot(), "an ambiguous id must not move or write anything")

    def test_every_wave_resolving_tool_refuses_the_duplicate_identically(self):
        # Finding `ambiguous-id-not-universal`: the refusal is raised by the
        # resolver, so every decorated tool emits the same code and message.
        w1, d1, twin = self._duplicate()
        plan = self.srv.change_create(self.root, "enh", "blocked-change", mode="create")
        cache = self.srv.McpRepoCache(self.root)
        srv, root = self.srv, self.root
        calls = (
            ("wf_prepare_wave", lambda: srv.wf_prepare_wave_response(root, w1, mode="dry_run")),
            ("wf_add_change", lambda: srv.wf_add_change_response(root, w1, plan["id"], mode="create")),
            # DC-C: removal resolves the wave the same way admission does.
            ("wf_remove_change", lambda: srv.wf_remove_change_response(root, w1, plan["id"], mode="create")),
            ("wf_review_event", lambda: srv.wf_review_event_response(
                root, w1, "approval", "qa", "ctx-1", mode="dry_run", signoff_key="qa",
            )),
            ("wf_close_wave", lambda: srv.wf_close_wave_response(root, w1, mode="dry_run")),
            ("wf_pause_wave", lambda: srv.wf_pause_wave_response(root, w1, mode="dry_run")),
            ("wf_list_waves", lambda: srv.wf_list_waves_response(root, cache=cache)),
            ("wf_current_wave", lambda: srv.wf_current_wave_response(root, cache)),
            # Finding `audit-wave-snapshot-picks-one-twin`: the audit's wave
            # snapshot refuses instead of reporting one twin (its lint
            # subprocess runs unpatched, so only the refusal fields matter).
            ("wf_audit", lambda: srv.wf_audit_response(root, cache=cache)),
            ("wf_audit", lambda: srv.wf_audit_response(root, wave_id=w1)),
            # Finding `cycle2-adjacent-gaps` (a): bulk change lookup by wave id.
            ("wf_get_change", lambda: srv.wf_get_change_response(root, wave_id=w1)),
            # Finding `mark-item-decorator-unpinned`: both mark tools.
            ("wf_mark_item", lambda: srv._mark_change_item_response(
                root, w1, plan["id"], "AC-1", "x", target_section="Acceptance Criteria", mode="dry_run",
            )),
            ("wf_mark_item", lambda: srv._mark_change_item_response(
                root, w1, plan["id"], "Task one", "x", target_section="Tasks", mode="dry_run",
            )),
        )
        before = self._snapshot()
        for tool, call in calls:
            with self.subTest(tool=tool):
                self._assert_ambiguous(tool, call(), w1)
        self.assertEqual(before, self._snapshot(), "no ambiguous-id refusal may write or move anything")

    def test_a_prefix_matching_distinct_ids_is_not_ambiguous_wave_id(self):
        # Two DIFFERENT ids sharing a prefix keep the plain multiple-match
        # ValueError; only one id at two paths is `ambiguous_wave_id`.
        w1, _ = self._create_wave("one")
        w2, _ = self._create_wave("two", "team")
        common = ""
        for a, b in zip(w1, w2):
            if a != b:
                break
            common += a
        if not common:
            self.skipTest("generated ids share no prefix")
        with self.assertRaises(ValueError) as ctx:
            self.srv._find_wave_md_detailed(self.root, common)
        self.assertNotIsInstance(ctx.exception, self.srv.record_paths.AmbiguousWaveId)


class AmbiguousWaveResourceTests(_NestedRepo):
    """Finding `wave-current-resource-serves-one-twin`: the read-only
    `wave/current` and `waves` resources refuse a duplicated wave id with the
    `# Ambiguous Wave` shape (naming both paths) instead of serving one twin."""

    RESOURCES = ("wavefoundry://wave/current", "wavefoundry://waves")

    def _read(self, uri: str) -> str:
        import asyncio

        try:
            mcp = load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        result = asyncio.run(mcp.read_resource(uri))
        for item in result:
            content = getattr(item, "content", None) or getattr(item, "text", None) or ""
            if content:
                return str(content)
        return ""

    def _activate(self, wave_dir: Path) -> None:
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace("Status: planned", "Status: active"),
            encoding="utf-8",
        )

    def test_both_resources_report_the_duplicate_and_name_both_paths(self):
        w1, d1 = self._create_wave("dup")
        self._activate(d1)
        twin = self.waves / "team" / w1
        twin.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(d1, twin)
        wid = w1.split(" ", 1)[0]
        before = self._snapshot()
        for uri in self.RESOURCES:
            with self.subTest(resource=uri):
                text = self._read(uri)
                self.assertTrue(text.startswith("# Ambiguous Wave\n"), text)
                self.assertIn(f"ambiguous_wave_id: {wid} at ", text)
                self.assertIn(f"{WAVES_REL}/{w1}", text)
                self.assertIn(f"{WAVES_REL}/team/{w1}", text)
                self.assertNotIn("Wave Record", text, "one twin must not be served as the wave")
                self.assertNotIn(f"## {w1}", text)
        self.assertEqual(before, self._snapshot(), "a read-only resource writes nothing")

    def test_without_a_duplicate_both_resources_serve_the_normal_content(self):
        w1, d1 = self._create_wave("solo")
        w2, d2 = self._create_wave("deep", "team")
        self._activate(d2)
        current = self._read("wavefoundry://wave/current")
        self.assertIn("Wave Record", current)
        self.assertNotIn("Ambiguous Wave", current)
        listing = self._read("wavefoundry://waves")
        self.assertTrue(listing.startswith("# Waves"), listing)
        self.assertNotIn("Ambiguous Wave", listing)
        self.assertIn(f"## {w1}", listing)
        self.assertIn(f"## {w2}", listing)

    def test_no_waves_message_names_the_resolved_root(self):
        listing = self._read("wavefoundry://waves")
        self.assertIn(f"No wave records found in `{WAVES_REL}/`.", listing)
        self.assertNotIn("docs/waves", listing)


class NestedStateSourcesTests(_NestedRepo):
    """Finding `commit-provenance-nested-wave-dir` (server half): the
    memory-propose state-source resolver locates a change doc inside a wave
    folder grouped below the waves root."""

    def test_memory_propose_state_sources_find_a_nested_change_doc(self):
        w1, d1 = self._create_wave("flat")
        w2, d2 = self._create_wave("deep", "team")
        plan = self.srv.change_create(self.root, "enh", "deep-change", mode="create")
        change_id = plan["id"]
        added = self.srv.wf_add_change_response(self.root, w2, change_id, mode="create")
        self.assertEqual(added["status"], "ok", added)
        self.assertTrue((d2 / f"{change_id}.md").is_file())
        result = {
            "status": "ok",
            "data": {"written": [{"source_event": f"decision-log:{change_id}:row-1"}]},
        }
        paths = self.srv._state_sources_memory_propose(self.root, result)
        self.assertEqual(paths, [f"{WAVES_REL}/team/{w2}/{change_id}.md"])
        # The flat sibling is still found on the same walk.
        plan2 = self.srv.change_create(self.root, "enh", "flat-change", mode="create")
        added = self.srv.wf_add_change_response(self.root, w1, plan2["id"], mode="create")
        self.assertEqual(added["status"], "ok", added)
        result["data"]["written"].append({"source_event": f"decision-log:{plan2['id']}:row-1"})
        paths = self.srv._state_sources_memory_propose(self.root, result)
        self.assertEqual(
            sorted(paths),
            sorted([f"{WAVES_REL}/team/{w2}/{change_id}.md", f"{WAVES_REL}/{w1}/{plan2['id']}.md"]),
        )


class FlatDepthRuleTests(_NestedRepo):
    def test_flat_layout_allows_only_a_direct_child_wave_folder(self):
        # Finding `cycle2-adjacent-gaps` (d): the containment guard keeps the
        # direct-child rule (`allowed_depth = 1`) when NESTED is false, so a
        # depth-two wave.md is refused even though it exists.
        w1, deep = self._create_wave("deep", "team")
        with self._patched(nested=False):
            with self.assertRaises(ValueError) as ctx:
                self.srv._contained_wave_review_paths(self.root, deep / "wave.md")
            self.assertIn("within 1 level(s) of", str(ctx.exception))
            direct, _events = self.srv._contained_wave_review_paths(self.root, self.waves / "x" / "wave.md")
            self.assertEqual(direct, (self.waves / "x" / "wave.md").resolve())
        # The same path is accepted under the nested layout.
        accepted, _events = self.srv._contained_wave_review_paths(self.root, deep / "wave.md")
        self.assertEqual(accepted, (deep / "wave.md").resolve())


class NestedPlanDocsTests(_NestedRepo):
    def test_plan_docs_nested_under_the_plans_root_are_found_in_both_modes(self):
        # Requirement 5: change-doc lookup keeps its recursive behaviour.
        plan = self.srv.change_create(self.root, "enh", "grouped-plan", mode="create")
        change_id = plan["id"]
        plans = self.root / "project" / "records" / "plans"
        grouped = plans / "grouped"
        grouped.mkdir()
        shutil.move(str(plans / f"{change_id}.md"), str(grouped / f"{change_id}.md"))
        for nested in (True, False):
            with self.subTest(nested=nested), self._patched(nested=nested):
                got = self.srv.wf_get_change_response(self.root, change_id)
                self.assertEqual(got["status"], "ok", got)
                self.assertIn(f"{PLANS_REL}/grouped/{change_id}.md", json.dumps(got["data"]))


class SingleWalkTests(_NestedRepo):
    def test_cached_lookup_never_fingerprints_outside_discovery_boundary(self):
        w1, d1 = self._create_wave("visible")
        self._create_wave("too-deep", "a/b/c/d/e")
        self._create_wave("hidden", ".hidden")
        evidence = d1 / "evidence" / "nested"
        evidence.mkdir(parents=True)
        (evidence / "wave.md").write_text("# Evidence, not a wave", encoding="utf-8")
        real_rglob = Path.rglob
        waves_root = self.waves.resolve()

        def no_recursive_wave_scan(directory, *args, **kwargs):
            if directory.resolve().is_relative_to(waves_root):
                self.fail("cache fingerprint performed an unbounded second wave walk")
            return real_rglob(directory, *args, **kwargs)

        cache = self.srv.McpRepoCache(self.root)
        with self._patched(max_depth=1), patch.object(Path, "rglob", no_recursive_wave_scan):
            for _ in range(2):  # cold and warm paths
                counting, calls = self._counting_walk()
                with counting:
                    result = self.srv.wf_current_wave_response(self.root, cache)
                self.assertEqual(result["status"], "ok", result)
                self.assertEqual([w["wave_id"] for w in result["data"]["waves"]], [w1])
                self.assertEqual(len(calls), 1)
            self.assertEqual(cache._wave_fingerprint()[0], 1)

    def test_current_wave_on_a_cold_cache_discovers_exactly_once(self):
        # AC-4c
        self._create_wave("one")
        self._create_wave("two", "team")
        cache = self.srv.McpRepoCache(self.root)
        counting, calls = self._counting_walk()
        with counting:
            result = self.srv.wf_current_wave_response(self.root, cache)
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(len(calls), 1, "one wf_current_wave invocation on a cold cache must walk once")

    def test_current_wave_on_a_warm_cache_discovers_exactly_once(self):
        w1, _ = self._create_wave("one")
        w2, _ = self._create_wave("two", "team")
        cache = self.srv.McpRepoCache(self.root)
        self.assertEqual(self.srv.wf_current_wave_response(self.root, cache)["status"], "ok")
        counting, calls = self._counting_walk()
        with counting:
            result = self.srv.wf_current_wave_response(self.root, cache)
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(sorted(w["wave_id"] for w in result["data"]["waves"]), sorted([w1, w2]))
        self.assertEqual(len(calls), 1, "one wf_current_wave invocation on a warm cache must walk exactly once")

    def _warm(self) -> tuple[str, str, "object"]:
        w1, _ = self._create_wave("one")
        w2, _ = self._create_wave("two", "team")
        cache = self.srv.McpRepoCache(self.root)
        warm = self.srv.wf_current_wave_response(self.root, cache)
        self.assertEqual(sorted(w["wave_id"] for w in warm["data"]["waves"]), sorted([w1, w2]))
        return w1, w2, cache

    def test_warm_cache_follows_a_nested_flip(self):
        # Finding `warm-cache-layout-flip`: the fingerprint is unchanged, the
        # constants are not.
        w1, w2, cache = self._warm()
        with self._patched(nested=False):
            flat = self.srv.wf_current_wave_response(self.root, cache)
        self.assertEqual(flat["status"], "ok", flat)
        self.assertEqual([w["wave_id"] for w in flat["data"]["waves"]], [w1])
        back = self.srv.wf_current_wave_response(self.root, cache)
        self.assertEqual(sorted(w["wave_id"] for w in back["data"]["waves"]), sorted([w1, w2]))

    def test_warm_cache_follows_a_max_depth_reduction(self):
        w1, w2, cache = self._warm()
        with self._patched(max_depth=1):
            shallow = self.srv.wf_current_wave_response(self.root, cache)
        self.assertEqual(shallow["status"], "ok", shallow)
        self.assertEqual([w["wave_id"] for w in shallow["data"]["waves"]], [w1])

    def test_warm_cache_serves_the_new_path_after_a_wave_moves_deeper(self):
        w1, w2, cache = self._warm()
        fingerprint_before = cache._wave_fingerprint()
        deep = self.waves / "a" / "b" / w1
        deep.parent.mkdir(parents=True)
        shutil.move(str(self.waves / w1), str(deep))
        # A rename keeps wave.md's mtime and the count: the old key alone
        # cannot see the move.
        self.assertEqual(cache._wave_fingerprint(), fingerprint_before)
        moved = self.srv.wf_current_wave_response(self.root, cache)
        self.assertEqual(moved["status"], "ok", moved)
        paths = {w["wave_id"]: w["path"].replace("\\", "/") for w in moved["data"]["waves"]}
        self.assertIn(f"{WAVES_REL}/a/b/{w1}/wave.md", paths[w1])
        self.assertEqual(self.srv._find_wave_md(self.root, w1, cache.wave_dirs_cached()), deep / "wave.md")


if __name__ == "__main__":
    unittest.main()
