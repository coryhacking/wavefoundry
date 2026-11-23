"""Public lifecycle coverage for the disposable, owned wave workspace.

Fixtures use the real create/admit/readiness producers. Only unrelated docs,
index refresh, map generation and telemetry execution are replaced; lifecycle
guards, publication locks and workspace I/O remain live.
"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from server_tools_support import (
    _make_repo, close_container, create_container, declared_wave_doc_gates, integrity_checks,
    load_server, make_declared_wave, review_policy_config,
)
from declaration_support import RecordingFastMCP
import vocabulary_profile as vp


class WaveWorkLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name)).resolve()
        config_path = self.root / "docs/workflow-config.json"
        config = json.loads(config_path.read_text())
        config["wave_review"] = review_policy_config()
        config_path.write_text(json.dumps(config))
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stubs = {
            "run_validate": lambda *a, **k: {"passed": True, "errors": [], "warnings": [], "output": ""},
            "run_garden": lambda *a, **k: {"passed": True, "files_updated": 0, "updated": [], "output": ""},
            "_run_post_write_lint": lambda *a, **k: {"mode": "stubbed"},
            "_trigger_background_index_refresh_for_paths": lambda *a, **k: None,
        }
        self.stack.enter_context(declared_wave_doc_gates(self.srv, self.stubs))
        for name in ("_regenerate_codebase_map_safe", "_auto_populate_memory_for_wave", "_maybe_optimize_index_on_close"):
            self.stack.enter_context(patch.object(self.srv, name, return_value={}))
        # Real registered callables retain publication and lifecycle middleware.
        telemetry = MagicMock()
        telemetry.focus = SimpleNamespace(wave_id="", stage="general")
        telemetry.record_workflow.return_value = {}
        self.handler = SimpleNamespace(root=self.root, cache=None, telemetry=telemetry)
        self.mcp = RecordingFastMCP()
        self.srv.register_mcp_surface(self.mcp, lambda: self.handler)

    def call(self, name, **kwargs):
        return self.mcp._tool_manager._tools[name].fn(**kwargs)

    def ok(self, result):
        self.assertEqual(result["status"], "ok", result)
        return result["data"]

    def area(self, result):
        area = result["data"]["work_area"]
        self.assertIsInstance(area["available"], bool)
        return area

    def wave(self, slug="workspace", *, ready=True, parent=None):
        made = self.ok(self.srv._change_create_response(self.root, "enh", slug + "-child", mode="create"))
        cid = made["change_id"]
        # A small, explicit change avoids unrelated template placeholders.
        (self.root / made["path"]).write_text(
            f"# Workspace fixture\n\n{vp.MEMBER_ID_LABEL}: `{cid}`\n"
            f"{vp.MEMBER_STATUS_LABEL}: `planned`\nOwner: Engineering\nStatus: planned\n"
            "Last verified: 2026-10-25\n\n## Rationale\n\nLifecycle fixture.\n\n"
            "## Requirements\n\n1. Exercise workspace lifetime.\n\n## Scope\n\nTemporary repository.\n\n"
            "## Acceptance Criteria\n\n- [x] AC-1: Fixture is complete.\n\n"
            "## Tasks\n\n- [x] Complete fixture.\n\n## AC Priority\n\n"
            "| AC | Priority | Rationale |\n| --- | --- | --- |\n| AC-1 | required | Fixture. |\n",
            encoding="utf-8",
        )
        wid, wave_md = make_declared_wave(
            self.srv, self.root, slug, change_ids=(cid,), ready=ready, parent=parent,
            readiness_run=ready,
            approvals=("council-readiness", "code-reviewer") if ready else (), doc_gate_stubs=self.stubs,
        )
        if ready:
            self.ok(self.call("wf_prepare_wave", wave_id=wid, mode="ready"))
        return wid, wave_md, cid

    def work(self, wid):
        return self.root / ".wavefoundry/work" / wid.split()[0]

    def scratch(self, wid, content="disposable"):
        path = self.work(wid) / "scratch/result.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def finish(self, wid, cid, *, skip=(), observed="bounded workspace fixture"):
        self.ok(self.call("wf_implement_wave", wave_id=wid, mode="create"))
        # Implement wave opens the container; implementers maintain the member
        # status in the two documents as work completes (there is no status tool).
        wave_md = self.srv._find_wave_md(self.root, wid)
        for path in (wave_md, wave_md.parent / f"{cid}.md"):
            text = path.read_text()
            text = text.replace(f"{vp.MEMBER_STATUS_LABEL}: `planned`", f"{vp.MEMBER_STATUS_LABEL}: `implemented`")
            if path != wave_md:
                text = text.replace("Status: planned", "Status: implemented")
            path.write_text(text, encoding="utf-8")
        # Review and close producers derive their own required lane sets.
        review = self.call("wf_review_wave", wave_id=wid, phase="implementation")
        run = self.call("wf_review_event", wave_id=wid, event="run", actor="council-chair",
                        context_id="workspace-delivery", run_kind="initial_delivery", cycle=0, mode="create")
        self.ok(run)
        keys = [*review["data"].get("required_lanes", ()), *review["data"].get("required_council_signoffs", ()), "operator-signoff"]
        for key in dict.fromkeys(keys):
            if key in skip:
                continue
            actor = ("operator" if key == "operator-signoff" else
                     "council-chair" if key.startswith(("wave-council", "council-")) else key)
            self.ok(self.call(
                "wf_review_event", wave_id=wid, event="approval", actor=actor,
                context_id="workspace-delivery-" + key, signoff_key=key,
                approval_phase="delivery", fresh_context=True, independent=True, mode="create",
                evidence={"observed": observed, "artifact_or_test_id": self.id(),
                          **({"intent_fit": "establishes"} if "council" in key else {})},
                integrity_checks=integrity_checks(),
            ))
        self.ok(self.call("wf_close_change", wave_id=wid, change_id=cid, mode="create"))

    def test_registered_create_preview_does_not_create_and_paths_use_resolved_prefix(self):
        preview = create_container(self.call, self.root, "first", mode="dry_run")
        self.assertEqual(preview["status"], "dry_run", preview)
        self.assertFalse(self.area(preview)["available"])
        self.assertFalse((self.root / ".wavefoundry/work").exists())
        first = create_container(self.call, self.root, "first", mode="create")
        second = create_container(self.call, self.root, "second", mode="create")
        first_id, second_id = self.ok(first)["wave_id"], self.ok(second)["wave_id"]
        a, b = self.area(first), self.area(second)
        self.assertEqual(a["path"], f".wavefoundry/work/{first_id.split()[0]}")
        self.assertNotEqual(a["path"], b["path"])
        self.assertTrue(a["available"] and b["available"])
        current = self.ok(self.call("wf_current_wave"))["waves"]
        by_id = {entry["wave_id"]: entry["work_area"] for entry in current}
        self.assertEqual(by_id[first_id], a)
        self.assertEqual(by_id[second_id], b)
        self.assertEqual(self.work(first_id).parent, self.work(second_id).parent)

    def test_registered_reads_and_dry_runs_do_not_recreate_a_missing_area(self):
        wid, _, _ = self.wave()
        shutil.rmtree(self.work(wid))
        for tool, kwargs in (
            ("wf_prepare_wave", {"mode": "dry_run"}),
            ("wf_implement_wave", {"mode": "dry_run"}),
            ("wf_review_wave", {"phase": "implementation"}),
        ):
            with self.subTest(tool=tool):
                result = self.call(tool, wave_id=wid.split()[0], **kwargs)
                self.assertFalse(self.area(result)["available"], result)
                self.assertFalse(self.work(wid).exists())
        entries = self.ok(self.call("wf_current_wave"))["waves"]
        self.assertFalse(entries[0]["work_area"]["available"])
        self.assertFalse(self.work(wid).exists())

    def test_registered_prepare_and_implement_lazily_restore_missing_areas(self):
        wid, _, _ = self.wave()
        for tool, mode in (("wf_prepare_wave", "ready"), ("wf_implement_wave", "create")):
            with self.subTest(tool=tool):
                shutil.rmtree(self.work(wid))
                result = self.call(tool, wave_id=wid.split()[0], mode=mode)
                self.ok(result)
                self.assertTrue(self.area(result)["available"])
                self.assertTrue(self.work(wid).is_dir())
                self.assertTrue(self.area(result)["generation"])

    def test_registered_pause_and_reopen_retain_scratch_and_generation(self):
        wid, _, _ = self.wave()
        original = self.area(self.call("wf_implement_wave", wave_id=wid, mode="create"))
        scratch = self.scratch(wid)
        self.ok(self.call("wf_pause_wave", wave_id=wid, mode="create"))
        paused = self.ok(self.call("wf_current_wave"))["waves"][0]
        self.assertEqual(paused["work_area"]["generation"], original["generation"])
        reopened = self.call("wf_reopen_wave", wave_id=wid.split()[0], purpose="implement")
        self.ok(reopened)
        self.assertEqual(self.area(reopened)["generation"], original["generation"])
        self.assertEqual(scratch.read_text(), "disposable")

    def test_failed_and_preview_close_and_single_change_close_preserve_scratch(self):
        wid, wave_md, cid = self.wave()
        scratch = self.scratch(wid)
        blocked = close_container(self.call, self.root, wid, mode="create")
        self.assertEqual(blocked["status"], "error", blocked)
        self.assertTrue(scratch.exists())
        self.assertNotIn("Status: closed", wave_md.read_text())
        self.finish(wid, cid)
        self.assertTrue(scratch.exists(), "single-change close must preserve wave scratch")
        preview = close_container(self.call, self.root, wid, mode="dry_run")
        self.assertEqual(preview["status"], "dry_run", preview)
        self.assertTrue(scratch.exists())
        self.assertNotIn("Status: closed", wave_md.read_text())

    def test_registered_whole_wave_close_removes_only_owned_scratch(self):
        wid, wave_md, cid = self.wave()
        other = self.ok(create_container(self.call, self.root, "neighbor", mode="create"))["wave_id"]
        neighbor = self.scratch(other, "neighbor")
        scratch = self.scratch(wid)
        durable = wave_md.parent / "final-proof.txt"
        durable.write_text("unique durable proof")
        external = self.root / "external-proof.txt"
        external.write_text("outside owned area")
        self.finish(wid, cid)
        ledger = wave_md.parent / "events.jsonl"
        ledger_before = ledger.read_bytes()
        result = close_container(self.call, self.root, wid.split()[0], mode="create")
        self.ok(result)
        self.assertIn("work_cleanup", result["data"])
        self.assertIn("Status: closed", wave_md.read_text())
        self.assertFalse(scratch.exists())
        self.assertFalse(self.work(wid).exists())
        self.assertEqual(neighbor.read_text(), "neighbor")
        self.assertEqual(durable.read_text(), "unique durable proof")
        self.assertEqual(external.read_text(), "outside owned area")
        self.assertEqual(ledger.read_bytes(), ledger_before)

    def _close_while_another_wave_is_open(self, *, parent_scopes=False):
        import context_efficiency
        from record_layout_support import patch_layout

        self.handler.telemetry = context_efficiency.ProcessTelemetry(self.root)
        self.addCleanup(self.handler.telemetry.close)
        if parent_scopes:
            self.stack.enter_context(patch_layout(nested=True, max_depth=4, modules=(self.srv.record_paths,)))
            self.stack.enter_context(patch.object(self.srv.record_paths, "OPEN_CONTAINER_SCOPE", "parent"))
            for group in ("alpha", "beta", "gamma"):
                (self.srv.record_paths.load_record_roots(self.root).waves / group).mkdir(parents=True)
        delivered, target, member = self.wave("delivery", parent="alpha" if parent_scopes else None)
        current, active, _ = self.wave("current", parent="beta" if parent_scopes else None)
        if parent_scopes:
            self.assertNotEqual(self.srv.record_paths.open_container_scope(self.root, active),
                                self.srv.record_paths.open_container_scope(self.root, target))

        self.finish(delivered, member)
        self.ok(self.call("wf_pause_wave", wave_id=delivered, mode="create"))
        if parent_scopes:
            # Both parents can legitimately have OPEN records: workspace
            # authority remains ambiguous even with an explicit close target.
            third, _, _ = self.wave("parallel", parent="gamma")
            self.ok(self.call("wf_implement_wave", wave_id=third, mode="create"))
        self.ok(self.call("wf_implement_wave", wave_id=current, mode="create"))
        handoff = self.root / "docs/agents/session-handoff.md"
        self.ok(self.call("wf_set_handoff", content=self.srv._update_handoff_wave_ref(handoff.read_text(), current)))
        self.ok(self.call("wf_open_gate", gate="framework_edit_allowed"))
        gates = self.root / ".wavefoundry/guard-overrides.json"
        handoff_before, gates_before = handoff.read_bytes(), gates.read_bytes()
        focus_before = self.handler.telemetry.focus
        self.assertEqual((focus_before.wave_id, focus_before.stage), (current, "implement"))
        work = self.scratch(delivered)
        other_work = self.scratch(current)

        def close(mode):
            from wf_server.docs_handlers import run_garden
            with patch.object(self.srv, "run_garden", wraps=run_garden) as garden:
                result = close_container(self.call, self.root, delivered.split()[0], mode=mode)
                if mode != "dry_run":
                    garden.assert_called_once_with(self.root, preserve_handoff=True)
            self.assertEqual(handoff.read_bytes(), handoff_before)
            self.assertEqual(gates.read_bytes(), gates_before)
            self.assertEqual(self.handler.telemetry.focus, focus_before)
            self.assertTrue(other_work.exists())
            self.assertTrue(result["data"]["shared_workspace_preserved"], result)
            return result

        spec = target.parent / f"{member}.md"
        original = spec.read_text()
        spec.write_text(original.replace("- [x] AC-1:", "- [ ] AC-1:"))
        refused = close("create")
        self.assertEqual(refused["status"], "error", refused)
        self.assertIn("Status: paused", target.read_text())
        self.assertTrue(work.exists())
        spec.write_text(original)
        self.assertEqual(close("dry_run")["status"], "dry_run")
        closed = self.ok(close("apply"))
        self.assertTrue(closed["transitioned_to_closed"])
        self.assertTrue(closed["context_efficiency_persistence"]["sealed"])
        self.assertIn("Status: closed", target.read_text())
        self.assertFalse(work.exists())
        self.assertFalse(self.ok(close("create"))["transitioned_to_closed"])

        # A sibling whose status cannot be established can still own the
        # workspace, even when no other readable record is OPEN.
        if not parent_scopes:
            active.write_bytes(b"\xff")
            self.assertFalse(self.ok(close("create"))["transitioned_to_closed"])

    def test_registered_close_preserves_the_other_open_workspace(self):
        self._close_while_another_wave_is_open()

    def test_registered_close_preserves_workspace_across_parent_scopes(self):
        self._close_while_another_wave_is_open(parent_scopes=True)

    def test_registered_device_drift_reports_available_and_closes_owned_area(self):
        wid, wave_md, cid = self.wave()
        self.finish(wid, cid)
        marker = self.work(wid) / ".owner.json"
        owner = json.loads(marker.read_text())
        original_generation = owner["generation"]
        owner["directory"][0] += 1
        owner["repository_directory"][0] += 1
        marker.write_text(json.dumps(owner))
        before = marker.read_bytes()
        scratch = self.scratch(wid)
        entries = self.ok(self.call("wf_current_wave"))["waves"]
        current = next(entry for entry in entries if entry["wave_id"] == wid)
        self.assertTrue(current["work_area"]["available"], current)
        self.assertEqual(current["work_area"]["generation"], original_generation)
        self.assertEqual(marker.read_bytes(), before)
        result = close_container(self.call, self.root, wid, mode="create")
        self.ok(result)
        self.assertEqual(result["data"]["work_cleanup"]["outcome"], "removed", result)
        self.assertIn("Status: closed", wave_md.read_text())
        self.assertFalse(scratch.exists())
        self.assertFalse(self.work(wid).exists())

    def test_registered_root_rename_retains_generation_and_closes_owned_work(self):
        wid, wave_md, cid = self.wave()
        self.finish(wid, cid)
        scratch = self.scratch(wid)
        marker = self.work(wid) / ".owner.json"
        owner = json.loads(marker.read_text())
        owner["directory"][0] += 7
        owner["repository_directory"][0] += 9
        marker.write_text(json.dumps(owner))
        before = marker.read_bytes()
        old_root = self.root
        moved = old_root.with_name(old_root.name + "-renamed")
        self.addCleanup(shutil.rmtree, moved, ignore_errors=True)
        old_root.rename(moved)
        self.root = self.handler.root = moved
        current = next(entry for entry in self.ok(self.call("wf_current_wave"))["waves"]
                       if entry["wave_id"] == wid)
        self.assertTrue(current["work_area"]["available"], current)
        self.assertEqual(current["work_area"]["generation"], owner["generation"])
        self.assertEqual((moved / marker.relative_to(old_root)).read_bytes(), before)
        result = close_container(self.call, self.root, wid, mode="create")
        self.ok(result)
        self.assertEqual(result["data"]["work_cleanup"]["outcome"], "removed", result)
        self.assertFalse((moved / scratch.relative_to(old_root)).exists())
        self.assertIn("Status: closed", (moved / wave_md.relative_to(old_root)).read_text())

    def test_registered_foreign_root_preserves_moved_work(self):
        wid, _, cid = self.wave()
        self.finish(wid, cid)
        self.scratch(wid, "foreign must survive")
        old_root = self.root
        foreign = old_root.with_name(old_root.name + "-foreign")
        self.addCleanup(shutil.rmtree, foreign, ignore_errors=True)
        foreign.mkdir()
        shutil.copytree(old_root / "docs", foreign / "docs")
        destination = foreign / ".wavefoundry/work" / wid.split()[0]
        destination.parent.mkdir(parents=True)
        self.work(wid).rename(destination)
        marker = destination / ".owner.json"
        before = marker.read_bytes()
        self.root = self.handler.root = foreign
        current = next(entry for entry in self.ok(self.call("wf_current_wave"))["waves"]
                       if entry["wave_id"] == wid)
        self.assertFalse(current["work_area"]["available"], current)
        result = close_container(self.call, self.root, wid, mode="create")
        self.ok(result)
        self.assertEqual(result["data"]["work_cleanup"]["outcome"], "preserved", result)
        self.assertEqual((destination / "scratch/result.txt").read_text(), "foreign must survive")
        self.assertEqual(marker.read_bytes(), before)

    def test_registered_closed_reopen_adopts_device_drift_and_rotates_generation(self):
        import wave_work

        wid, _, cid = self.wave()
        self.finish(wid, cid)
        scratch = self.scratch(wid, "retained after close")
        marker = self.work(wid) / wave_work.OWNER_FILE
        owner = json.loads(marker.read_text())
        original_generation = owner["generation"]
        with patch.object(wave_work, "cleanup_work", side_effect=OSError("retain fixture")):
            self.ok(close_container(self.call, self.root, wid, mode="create"))
        owner["directory"][0] += 1
        marker.write_text(json.dumps(owner))
        reopened = self.call("wf_reopen_wave", wave_id=wid, purpose="implement")
        self.ok(reopened)
        self.assertTrue(self.area(reopened)["available"], reopened)
        self.assertNotEqual(self.area(reopened)["generation"], original_generation)
        self.assertEqual(scratch.read_text(), "retained after close")
        after = json.loads(marker.read_text())
        self.assertEqual(after, dict(owner, generation=self.area(reopened)["generation"]))

    def test_registered_close_preserves_each_invalid_directory_record(self):
        for case in range(15):
            with self.subTest(case=case):
                # Every case exercises the initial close transition, rather
                # than retrying an already-closed wave.
                wid, wave_md, cid = self.wave(slug=f"invalid-{case}")
                self.finish(wid, cid)
                scratch = self.scratch(wid, "must survive")
                marker = self.work(wid) / ".owner.json"
                owner = json.loads(marker.read_text())
                device, inode = owner["directory"]
                invalid = ([device, inode + 1], [device, 0], [0, 0], [], [device],
                           [device, inode, 1], None, {}, "directory", [True, inode],
                           [device, True], [-1, inode], [device, -1], [1.0, inode],
                           [device, str(inode)])
                value = invalid[case]
                owner["directory"] = value
                marker.write_text(json.dumps(owner))
                before = marker.read_bytes()
                entries = self.ok(self.call("wf_current_wave"))["waves"]
                current = next(entry for entry in entries if entry["wave_id"] == wid)
                self.assertFalse(current["work_area"]["available"], current)
                self.assertIn("work_ownership_unproven", current["work_area"]["notice"])
                result = close_container(self.call, self.root, wid, mode="create")
                self.ok(result)
                cleanup = result["data"]["work_cleanup"]
                self.assertEqual(cleanup["outcome"], "preserved", result)
                self.assertIn("work_ownership_unproven", cleanup["notice"])
                self.assertIn("Status: closed", wave_md.read_text())
                self.assertEqual(marker.read_bytes(), before)
                self.assertEqual(scratch.read_text(), "must survive")

    def test_cleanup_io_failure_keeps_closed_status_and_authorized_retry_cleans(self):
        import wave_work

        wid, wave_md, cid = self.wave()
        scratch = self.scratch(wid)
        self.finish(wid, cid)
        with patch.object(wave_work, "cleanup_work", side_effect=OSError("fixture I/O failure")):
            result = close_container(self.call, self.root, wid, mode="create")
        self.ok(result)
        self.assertIn("Status: closed", wave_md.read_text())
        self.assertTrue(scratch.exists())
        self.assertTrue(result["data"]["work_cleanup"]["notice"])
        self.ok(close_container(self.call, self.root, wid, mode="create"))
        self.assertFalse(self.work(wid).exists())

    def test_missing_work_area_is_an_idempotent_close_noop(self):
        wid, wave_md, cid = self.wave()
        self.finish(wid, cid)
        shutil.rmtree(self.work(wid))
        for attempt in range(2):
            with self.subTest(attempt=attempt):
                result = close_container(self.call, self.root, wid, mode="create")
                self.ok(result)
                self.assertIn("work_cleanup", result["data"])
                self.assertIn("Status: closed", wave_md.read_text())
                self.assertFalse(self.work(wid).exists())

    def test_registered_close_reopen_interleaving_protects_new_generation(self):
        import wave_work

        wid, wave_md, cid = self.wave()
        self.finish(wid, cid)
        old_generation = self.ok(self.call("wf_current_wave"))["waves"][0]["work_area"]["generation"]
        self.scratch(wid)
        entered, release = threading.Event(), threading.Event()
        results, errors = [], []
        cleanup = wave_work.cleanup_work

        def held_cleanup(*args, **kwargs):
            entered.set()
            if not release.wait(10):
                raise AssertionError("test did not release cleanup boundary")
            return cleanup(*args, **kwargs)

        def close():
            try:
                results.append(close_container(self.call, self.root, wid, mode="create"))
            except BaseException as exc:
                errors.append(exc)

        with patch.object(wave_work, "cleanup_work", held_cleanup):
            thread = threading.Thread(target=close, daemon=True)
            thread.start()
            try:
                self.assertTrue(entered.wait(10), "close did not reach cleanup")
                self.assertIn("Status: closed", wave_md.read_text())
                busy = self.call("wf_reopen_wave", wave_id=wid, purpose="implement")
                self.assertEqual(busy["status"], "error", busy)
                self.assertIn("lifecycle_mutation_locked", {d["code"] for d in busy["diagnostics"]})
            finally:
                release.set()
                thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors, errors)
        self.assertEqual(len(results), 1)
        self.ok(results[0])
        reopened = self.call("wf_reopen_wave", wave_id=wid, purpose="implement")
        self.ok(reopened)
        self.assertNotEqual(self.area(reopened)["generation"], old_generation)
        fresh = self.scratch(wid, "fresh generation")
        cleanup(self.root, wave_md, expected_generation=old_generation)
        self.assertEqual(fresh.read_text(), "fresh generation")

    def test_closed_reopen_retains_leftovers_but_rotates_generation_with_notice(self):
        import wave_work

        wid, wave_md, cid = self.wave()
        self.finish(wid, cid)
        old = self.ok(self.call("wf_current_wave"))["waves"][0]["work_area"]["generation"]
        scratch = self.scratch(wid, "left behind")
        with patch.object(wave_work, "cleanup_work", side_effect=OSError("cleanup unavailable")):
            self.ok(close_container(self.call, self.root, wid, mode="create"))
        reopened = self.call("wf_reopen_wave", wave_id=wid, purpose="implement")
        self.ok(reopened)
        self.assertNotEqual(self.area(reopened)["generation"], old)
        self.assertTrue(self.area(reopened)["notice"])
        self.assertEqual(scratch.read_text(), "left behind")
        wave_work.cleanup_work(self.root, wave_md, expected_generation=old)
        self.assertEqual(scratch.read_text(), "left behind")

    # --- Change 23phc: retained and leftover work reporting ------------------

    def codes(self, result):
        return [d["code"] for d in result["diagnostics"]]

    def diagnostic(self, result, code):
        found = [d for d in result["diagnostics"] if d["code"] == code]
        self.assertEqual(len(found), 1, result["diagnostics"])
        return found[0]

    def snapshot(self, top):
        return {p.relative_to(self.root).as_posix(): (p.read_bytes() if p.is_file() else None)
                for p in sorted(top.rglob("*"))}

    def unowned_closed_wave(self, slug="retained"):
        """A finished wave whose work folder has lost its owner file."""
        import wave_work

        wid, wave_md, cid = self.wave(slug=slug)
        self.finish(wid, cid)
        scratch = self.scratch(wid, "retained payload")
        (self.work(wid) / wave_work.OWNER_FILE).unlink()
        return wid, wave_md, scratch

    def test_unowned_close_returns_top_level_work_retained_and_dry_run_reports_nothing(self):
        wid, wave_md, scratch = self.unowned_closed_wave()
        # Runtime lock bookkeeping is not part of the records or the work root.
        before = (self.snapshot(self.root / "docs"), self.snapshot(self.root / ".wavefoundry/work"))
        preview = close_container(self.call, self.root, wid, mode="dry_run")
        self.assertEqual(preview["status"], "dry_run", preview)
        self.assertNotIn("work_retained", self.codes(preview))
        self.assertEqual((self.snapshot(self.root / "docs"), self.snapshot(self.root / ".wavefoundry/work")),
                         before, "dry-run close must leave records and work byte-identical")
        result = close_container(self.call, self.root, wid, mode="create")
        self.ok(result)
        retained = self.diagnostic(result, "work_retained")
        self.assertTrue(retained["advisory"])
        detail = retained["detail"]
        self.assertEqual(detail["path"], f".wavefoundry/work/{wid.split()[0]}")
        self.assertEqual(detail["reason"], "work_ownership_unproven")
        self.assertEqual(detail["outcome"], "preserved")
        # Independent oracle: a plain walk of the retained folder (prepare also
        # leaves its review snapshot there).
        walked = [Path(d) / n for d, dirs, files in os.walk(self.work(wid)) for n in dirs + files]
        self.assertEqual((detail["entries"], detail["complete"]), (len(walked), True))
        self.assertEqual(detail["bytes"], sum(p.stat().st_size for p in walked if p.is_file()))
        self.assertGreaterEqual(detail["bytes"], len("retained payload"))
        self.assertIn("wf_audit", retained["message"])
        self.assertNotIn("ACL", retained["message"])
        self.assertEqual(result["data"]["work_cleanup"]["reason"], "work_ownership_unproven")
        self.assertIn("Status: closed", wave_md.read_text())
        self.assertEqual(scratch.read_text(), "retained payload")
        self.assertFalse((self.work(wid) / ".owner.json").exists(), "close must not adopt unowned work")

    def test_unsupported_host_close_reports_safe_work_io_unsupported(self):
        import wave_work

        wid, wave_md, cid = self.wave(slug="unsupported")
        self.finish(wid, cid)
        scratch = self.scratch(wid, "kept on this host")
        with patch.object(wave_work, "_SAFE_DELETE", False):
            result = close_container(self.call, self.root, wid, mode="create")
        self.ok(result)
        retained = self.diagnostic(result, "work_retained")
        self.assertEqual(retained["detail"]["reason"], "safe_work_io_unsupported")
        self.assertNotIn(wave_work.CLEANUP_TOOL, retained["detail"]["next_action"])
        self.assertNotIn("ACL", retained["message"])
        self.assertEqual(scratch.read_text(), "kept on this host")
        self.assertIn("Status: closed", wave_md.read_text())

    def test_owned_removal_emits_no_work_retained(self):
        wid, _, cid = self.wave(slug="removed")
        self.finish(wid, cid)
        self.scratch(wid)
        result = close_container(self.call, self.root, wid, mode="create")
        self.ok(result)
        self.assertEqual(result["data"]["work_cleanup"]["outcome"], "removed")
        self.assertNotIn("work_retained", self.codes(result))

    def test_leftover_from_an_earlier_close_is_rediscovered_by_close_and_audit(self):
        earlier, _, _ = self.unowned_closed_wave(slug="earlier")
        self.ok(close_container(self.call, self.root, earlier, mode="create"))
        key = earlier.split()[0]
        later, _, cid = self.wave(slug="later")
        self.finish(later, cid)
        with self.subTest(surface="close"):
            for mode in ("dry_run", "create"):
                result = close_container(self.call, self.root, later, mode=mode)
                leftovers = self.diagnostic(result, "work_leftovers_present")
                self.assertIn(key, leftovers["detail"]["keys"])
                self.assertNotIn(later.split()[0], leftovers["detail"]["keys"])
                self.assertEqual(leftovers["recovery_usage"], "wf_audit()")
        with self.subTest(surface="audit"):
            work_root = self.root / ".wavefoundry/work"
            before = self.snapshot(work_root)
            audit = self.srv.wf_audit_response(self.root)
            self.assertEqual(self.snapshot(work_root), before, "audit must leave the work root byte-identical")
            listed = {item["key"]: item for item in audit["data"]["work_root"]["leftovers"]}
            self.assertEqual(listed[key]["state"], "closed")
            self.assertEqual(listed[key]["ownership"], "missing")
            self.assertGreater(listed[key]["bytes"], 0)
            self.assertIn("work_leftovers_present", self.codes(audit))
            moved = self.root / "moved-aside"
            (work_root / key).rename(moved)
            try:
                without = self.srv.wf_audit_response(self.root)
            finally:
                moved.rename(work_root / key)
            self.assertEqual(audit["data"]["ready"], without["data"]["ready"])
            self.assertNotIn("work_leftovers_present", self.codes(without))

    def test_close_reports_citations_of_its_own_work_folder_only(self):
        import wave_work

        wid, wave_md, cid = self.wave(slug="cited")
        self.finish(wid, cid)
        key = wid.split()[0]
        handoff = self.root / "docs/agents/session-handoff.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        with self.subTest(case="control"):
            handoff.write_text("# Handoff\n\nSee `.wavefoundry/work/zzz99/notes.md` and `.wavefoundry/work/`.\n")
            preview = close_container(self.call, self.root, wid, mode="dry_run")
            self.assertNotIn("work_path_cited", self.codes(preview))
        text = wave_md.read_text()
        citation = f"Notes: `.wavefoundry/work/{key}/notes.md`"
        wave_md.write_text(text.rstrip("\n") + f"\n\n{citation}\n")
        change_doc = wave_md.parent / f"{cid}.md"
        change_before = change_doc.read_bytes()
        real = wave_work.find_work_path_citations

        def unreadable_change(root, work_key, documents):
            # The close itself must read the change; only the citation reader is denied.
            os.chmod(change_doc, 0)
            try:
                return real(root, work_key, documents)
            finally:
                os.chmod(change_doc, 0o644)
        with self.subTest(case="cited"):
            result = close_container(self.call, self.root, wid, mode="create")
            self.ok(result)
            cited = self.diagnostic(result, "work_path_cited")
            rel = wave_md.relative_to(self.root).as_posix()
            # Close rewrites the record before reporting; the hit names the line now holding it.
            line = wave_md.read_text().splitlines().index(citation) + 1
            self.assertEqual(cited["detail"]["hits"], [{"path": rel, "line": line}])
            self.assertEqual(cited["detail"]["coverage"], "complete")
            self.assertIn("Status: closed", wave_md.read_text())
            self.assertIn(citation, wave_md.read_text())
            self.assertEqual(change_doc.read_bytes(), change_before)
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root reads files whatever their mode")
        with self.subTest(case="incomplete"), \
                patch.object(wave_work, "find_work_path_citations", side_effect=unreadable_change):
            again = close_container(self.call, self.root, wid, mode="dry_run")
            cited = self.diagnostic(again, "work_path_cited")
            self.assertEqual(cited["detail"]["coverage"], "incomplete")
            self.assertEqual(cited["detail"]["unreadable"], [change_doc.relative_to(self.root).as_posix()])

    # --- Change 23rzt: loose files directly in the work root ----------------

    LOOSE = {"23abc-reviewer-brief.md": 1200, "build.log": 40, ".DS_Store": 6}

    def loose(self, root=None):
        work_root = (root or self.root) / ".wavefoundry/work"
        work_root.mkdir(parents=True, exist_ok=True)
        for name, size in self.LOOSE.items():
            (work_root / name).write_bytes(b"x" * size)
        return {name: (work_root / name).read_bytes() for name in self.LOOSE}

    def loose_codes(self, result):
        return [d for d in result["diagnostics"] or () if d["code"] == "work_root_loose_files"]

    def assert_loose_advisory(self, result):
        found = self.loose_codes(result)
        self.assertEqual(len(found), 1, result["diagnostics"])
        diagnostic = found[0]
        self.assertIs(diagnostic["advisory"], True)
        self.assertEqual(diagnostic["recovery_tools"], ["wf_audit"])
        self.assertEqual(diagnostic["detail"]["count"], len(self.LOOSE))
        self.assertEqual(diagnostic["detail"]["names"], ["23abc-reviewer-brief.md", "build.log", ".DS_Store"])
        message = diagnostic["message"]
        self.assertTrue(message.startswith(f"{len(self.LOOSE)} loose file(s) or link(s) directly in "
                                           ".wavefoundry/work/: 23abc-reviewer-brief.md (1200 bytes), "
                                           "build.log (40 bytes), .DS_Store (6 bytes)."), message)
        self.assertNotIn("wf_cleanup_work", message, "the advisory names no deleting tool")
        return diagnostic

    def test_audit_reports_loose_files_without_changing_any_other_result(self):
        import wave_work

        wid, _, _ = self.wave(slug="audited")
        self.ok(self.call("wf_implement_wave", wave_id=wid, mode="create"))
        self.scratch(wid)
        # A ready control (open record, lint stubbed passing in setUp, a
        # healthy index snapshot as in test_vendored_integrity), so a change
        # of `ready` caused by the loose files can show.
        healthy = {"metadata_ready": True, "readiness_overview": "ready", "freshness": "unknown",
                   "freshness_checked": False, "freshness_verification_tool": "index_health"}
        self.stack.enter_context(patch.object(self.srv, "_audit_index_snapshot", return_value=healthy))
        without = self.srv.wf_audit_response(self.root)
        self.assertIs(without["data"]["ready"], True, without["diagnostics"])
        self.assertEqual(self.loose_codes(without), [])
        self.assertEqual(without["data"]["work_root"]["loose_count"], 0)
        before = self.loose()
        audit = self.srv.wf_audit_response(self.root)
        work_root = audit["data"]["work_root"]
        self.assertEqual(work_root["loose_count"], len(self.LOOSE))
        self.assertEqual({item["name"]: (item["kind"], item["bytes"]) for item in work_root["loose_entries"]},
                         {name: ("file", size) for name, size in self.LOOSE.items()})
        diagnostic = self.assert_loose_advisory(audit)
        self.assertEqual(diagnostic["detail"]["cap"], wave_work.LOOSE_ENTRY_LIST_CAP)
        self.assertEqual(audit["data"]["ready"], without["data"]["ready"])
        self.assertEqual([d["code"] for d in audit["diagnostics"] if d["code"] != "work_root_loose_files"],
                         [d["code"] for d in without["diagnostics"]])
        self.assertEqual(set(audit["data"]), set(without["data"]))
        keep = ("leftovers", "live_unowned", "unclassified", "live_owned", "totals", "present")
        self.assertEqual({k: work_root[k] for k in keep}, {k: without["data"]["work_root"][k] for k in keep})
        work_dir = self.root / ".wavefoundry/work"
        self.assertEqual({name: (work_dir / name).read_bytes() for name in self.LOOSE}, before)

    def test_audit_fallback_carries_an_empty_loose_report(self):
        import wave_work

        self.loose()
        with patch.object(wave_work, "inventory_work_root", side_effect=RuntimeError("boom")):
            audit = self.srv.wf_audit_response(self.root)
        work_root = audit["data"]["work_root"]
        self.assertEqual((work_root["loose_count"], work_root["loose_entries"]), (0, []))
        self.assertEqual(self.loose_codes(audit), [])

    def test_advisory_limits_action_to_the_author_and_leaves_other_files_to_the_operator(self):
        container = vp.tier_noun("container")
        self.loose()
        message = self.assert_loose_advisory(self.srv.wf_audit_response(self.root))["message"]
        for rule in (
            f"Files written for a {container} belong inside .wavefoundry/work/<{container}-id>/.",
            f"An agent that wrote one of these files for a {container} moves it into that {container}'s "
            f"folder while the {container} is open, or deletes it.",
            "Any other file, including one the agent is not sure it wrote",
            "is left in place and reported to the operator, who decides.",
            f"An agent never moves a file it did not write into a {container}'s folder: close removes "
            "that folder with everything in it.",
        ):
            self.assertIn(rule, message)

    def test_close_carries_the_advisory_in_both_modes_and_changes_nothing_else(self):
        wid, wave_md, cid = self.wave(slug="loose")
        blocked = close_container(self.call, self.root, wid, mode="dry_run")
        self.assertEqual(blocked["status"], "error", blocked)
        self.finish(wid, cid)
        twin = Path(self.tmp.name) / "twin-loose"
        shutil.copytree(self.root, twin, symlinks=True)
        # Ownership is bound to the original folder's identity; the twin has no
        # work area, as in test_report_never_changes_the_close_result.
        shutil.rmtree(twin / ".wavefoundry/work" / wid.split()[0], ignore_errors=True)
        twin = twin.resolve()
        before = self.loose()

        def blockers(result):
            return sorted(d["code"] for d in result["diagnostics"] or () if not d.get("advisory"))

        def others(result):
            return [d["code"] for d in result["diagnostics"] or ()
                    if d["code"] not in ("work_root_loose_files", "record_extras_present")]

        preview = close_container(self.call, self.root, wid, mode="dry_run")
        self.assertEqual(preview["status"], "dry_run", preview)
        codes = [d["code"] for d in preview["diagnostics"]]
        self.assert_loose_advisory(preview)
        closed = close_container(self.call, self.root, wid, mode="create")
        self.ok(closed)
        self.assert_loose_advisory(closed)
        self.handler.root = twin
        try:
            twin_preview = close_container(self.call, twin, wid, mode="dry_run")
            twin_closed = close_container(self.call, twin, wid, mode="create")
        finally:
            self.handler.root = self.root
        for ours, theirs in ((preview, twin_preview), (closed, twin_closed)):
            self.assertEqual(self.loose_codes(theirs), [])
            self.assertEqual((ours["status"], blockers(ours), others(ours)),
                             (theirs["status"], blockers(theirs), others(theirs)))
        self.assertIn("Status: closed", wave_md.read_text())
        self.assertEqual(wave_md.read_text(), (twin / wave_md.relative_to(self.root)).read_text(),
                         "the written record is identical")
        work_dir = self.root / ".wavefoundry/work"
        self.assertEqual({name: (work_dir / name).read_bytes() for name in self.LOOSE}, before,
                         "close leaves the loose files in place, byte-identical")
        self.assertFalse(self.work(wid).exists(), "close still removes its own owned folder")
        self.assertEqual(self.loose_codes(blocked), [])
        self.assertNotIn("work_leftovers_present", codes)
        # Placed with the leftover-folder report: an earlier record-less folder
        # is a leftover, and the loose advisory follows its report directly.
        (work_dir / "zzq99").mkdir()
        reported, _ = self.srv._close_work_reporting(self.root, wave_md, wave_md.read_text(), None)
        reported_codes = [d["code"] for d in reported]
        self.assertEqual(reported_codes[:2], ["work_leftovers_present", "work_root_loose_files"], reported_codes)

    def test_a_close_that_returns_before_the_work_report_does_not_carry_it(self):
        wid, _, _ = self.wave(slug="early")
        self.loose()
        blocked = close_container(self.call, self.root, wid, mode="dry_run")
        self.assertEqual(blocked["status"], "error", blocked)
        self.assertNotIn("work_leftovers_present", self.codes(blocked))
        self.assertEqual(self.loose_codes(blocked), [])

    def test_cleanup_refuses_a_loose_file_for_both_reasons(self):
        work_dir = self.root / ".wavefoundry/work"
        work_dir.mkdir(parents=True, exist_ok=True)
        cases = {"notes.md": "work_key_invalid", "abcde12": "work_entry_not_directory"}
        for name, reason in cases.items():
            (work_dir / name).write_bytes(b"loose payload")
            for kwargs in ({}, {"mode": "apply", "confirmation": "0" * 64}):
                with self.subTest(name=name, **{k: v for k, v in kwargs.items() if k == "mode"}):
                    result = self.cleanup_tool(work_key=name, **kwargs)
                    self.assertEqual(result["status"], "error", result)
                    self.assertEqual(result["data"]["reason"], reason, result)
                    self.assertEqual((work_dir / name).read_bytes(), b"loose payload")

    def test_pause_prepare_and_review_do_not_carry_the_advisory(self):
        wid, _, _ = self.wave(slug="quiet")
        self.loose()
        prepared = self.call("wf_prepare_wave", wave_id=wid, mode="ready")
        self.ok(prepared)
        self.ok(self.call("wf_implement_wave", wave_id=wid, mode="create"))
        reviewed = self.call("wf_review_wave", wave_id=wid, phase="implementation")
        paused = self.call("wf_pause_wave", wave_id=wid, mode="create")
        self.ok(paused)
        for name, result in (("prepare", prepared), ("review", reviewed), ("pause", paused)):
            with self.subTest(tool=name):
                self.assertEqual(self.loose_codes(result), [])
                self.assertNotIn("work_root_loose_files", json.dumps(result.get("data")))

    # --- Change 23q0s: explicit cleanup through the registered tool ----------

    def cleanup_tool(self, **kwargs):
        return self.call("wf_cleanup_work", **kwargs)

    def retained_closed_wave(self, slug):
        wid, wave_md, scratch = self.unowned_closed_wave(slug=slug)
        self.ok(close_container(self.call, self.root, wid, mode="create"))
        self.assertTrue(scratch.exists(), "close must have retained the unowned folder")
        return wid, wave_md

    def test_registered_cleanup_replays_the_incident(self):
        import wave_work

        wid, wave_md = self.retained_closed_wave("incident")
        other, other_md = self.retained_closed_wave("other")
        key = wid.split()[0]
        outside = self.root / "outside.txt"
        outside.write_text("outside the work root")
        work_root = self.root / ".wavefoundry/work"
        before = (self.snapshot(self.root / "docs"), self.snapshot(work_root))
        previews = [self.ok(self.cleanup_tool(work_key=key)),
                    self.ok(self.cleanup_tool(work_key=key, mode="dry_run"))]
        self.assertEqual((self.snapshot(self.root / "docs"), self.snapshot(work_root)), before,
                         "a preview must leave records and work byte-identical")
        for preview in previews:
            self.assertEqual((preview["outcome"], preview["state"], preview["ownership"]),
                             ("preview", "closed", "missing"))
            self.assertIn("scratch", [child["name"] for child in preview["children"]])
            self.assertTrue(preview["apply_possible"])
            self.assertIn("operator", preview["next_action"])
        self.assertEqual(previews[0]["confirmation"], previews[1]["confirmation"])
        keep = (self.snapshot(self.work(other)), wave_md.read_bytes(), other_md.read_bytes(), outside.read_bytes())
        removed = self.ok(self.cleanup_tool(work_key=key, mode="apply", confirmation=previews[0]["confirmation"]))
        self.assertEqual(removed["outcome"], "removed", removed)
        self.assertFalse(os.path.lexists(self.work(wid)))
        self.assertEqual((self.snapshot(self.work(other)), wave_md.read_bytes(), other_md.read_bytes(),
                          outside.read_bytes()), keep)
        self.assertEqual(list(work_root.rglob(wave_work.OWNER_FILE)), [], "no owner file is ever written")
        # Normal policy is unchanged: automatic cleanup still preserves the
        # other unowned folder of a closed record.
        self.assertEqual(wave_work.cleanup_work(self.root, other_md, expected_generation=None)["outcome"],
                         "preserved")
        self.assertTrue(self.work(other).exists())

    def test_registered_cleanup_of_a_record_less_folder_reports_the_handoff_citation(self):
        folder = self.root / ".wavefoundry/work/zzq99"
        (folder / "notes").mkdir(parents=True)
        (folder / "notes/result.txt").write_text("record-less")
        handoff = self.root / "docs/agents/session-handoff.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text("# Handoff\n\nScratch: `.wavefoundry/work/zzq99/`\nAlso .wavefoundry/work/zzq99\n"
                           "Not this one: .wavefoundry/work/zzq990/\n")
        result = self.cleanup_tool(work_key="zzq99")
        preview = self.ok(result)
        self.assertEqual(preview["state"], "not_found_in_checkout")
        self.assertIn("another branch or checkout", preview["state_note"])
        cited = self.diagnostic(result, "work_path_cited")
        self.assertEqual(cited["detail"]["hits"], [{"path": "docs/agents/session-handoff.md", "line": 3},
                                                    {"path": "docs/agents/session-handoff.md", "line": 4}])
        removed = self.ok(self.cleanup_tool(work_key="zzq99", mode="apply", confirmation=preview["confirmation"]))
        self.assertEqual(removed["outcome"], "removed")
        self.assertFalse(folder.exists())

    def test_registered_cleanup_refuses_bad_modes_and_keys(self):
        wid, _ = self.retained_closed_wave("modes")
        key = wid.split()[0]
        token = self.ok(self.cleanup_tool(work_key=key))["confirmation"]
        os.symlink(self.work(wid), self.root / ".wavefoundry/work/lnk12")
        before = self.snapshot(self.root / ".wavefoundry/work")
        for kwargs in ({"work_key": key, "mode": "create", "confirmation": token},
                       {"work_key": key, "mode": "delete"},
                       {"work_key": "../x", "mode": "apply", "confirmation": token},
                       {"work_key": f"{key}/scratch", "mode": "apply", "confirmation": token},
                       {"work_key": "lnk12", "mode": "apply", "confirmation": token},
                       {"work_key": key, "mode": "apply", "confirmation": token, "force": True}):
            with self.subTest(**{k: v for k, v in kwargs.items() if k != "confirmation"}):
                result = self.cleanup_tool(**kwargs)
                self.assertEqual(result["status"], "error", result)
        self.assertEqual(self.snapshot(self.root / ".wavefoundry/work"), before)

    def test_registered_cleanup_refuses_a_live_folder(self):
        wid, _, _ = self.wave(slug="live")
        self.ok(self.call("wf_implement_wave", wave_id=wid, mode="create"))
        scratch = self.scratch(wid, "live work")
        preview = self.ok(self.cleanup_tool(work_key=wid.split()[0]))
        self.assertFalse(preview["apply_possible"])
        self.assertIsNone(preview["confirmation"])
        result = self.cleanup_tool(work_key=wid.split()[0], mode="apply", confirmation="0" * 64)
        self.assertEqual(result["status"], "error")
        self.assertEqual(self.diagnostic(result, "work_state_not_cleanable")["code"], "work_state_not_cleanable")
        self.assertNotIn(result["data"]["state"], ("closed", "completed", "archived", "not_found_in_checkout"))
        self.assertEqual(scratch.read_text(), "live work")

    def test_registered_cleanup_is_write_tier_destructive_locked_and_upgrade_guarded(self):
        import mcp_tool_roster
        import publication_control

        name = "wf_cleanup_work"
        self.assertEqual(mcp_tool_roster.TOOL_TIERS[name], mcp_tool_roster.TIER_WRITE)
        self.assertIn(name, self.srv._LIFECYCLE_MUTATION_LOCK_TOOLS)
        self.assertIn(name, publication_control.registered_publication_tool_names())
        writer = {w.tool_name: w for w in publication_control.PUBLICATION_WRITER_REGISTRY}[name]
        self.assertEqual((writer.producer, writer.contention_policy), ("lifecycle", "fail_fast"))
        rule = mcp_tool_roster.MCP_RULE_PREFIX + name
        self.assertNotIn(rule, mcp_tool_roster.allow_rules(), "absent from the default allowlist")
        self.assertIn(rule, mcp_tool_roster.allow_rules(include_write=True))
        golden = json.loads((Path(__file__).resolve().parent / "fixtures/tool-surface-golden.json")
                            .read_text(encoding="utf-8"))["tools"][name]
        self.assertEqual(golden["tier"], "write")
        self.assertIs(golden["annotations"]["destructiveHint"], True)
        tool = self.mcp._tool_manager._tools[name]
        self.assertIs(tool.annotations.destructiveHint, True)
        self.assertTrue(getattr(tool.fn, "_wf_mutation_locked", False))
        self.assertTrue(getattr(tool.fn, "_wf_upgrade_guarded", False))

    def test_registered_cleanup_refuses_while_the_lifecycle_lock_is_held(self):
        wid, _ = self.retained_closed_wave("busy")
        key = wid.split()[0]
        token = self.ok(self.cleanup_tool(work_key=key))["confirmation"]
        held, release = threading.Event(), threading.Event()

        def holder():
            with self.srv._lifecycle_mutation_lock(self.root):
                held.set()
                release.wait(timeout=10)
        thread = threading.Thread(target=holder)
        thread.start()
        try:
            self.assertTrue(held.wait(timeout=10))
            result = self.cleanup_tool(work_key=key, mode="apply", confirmation=token)
        finally:
            release.set()
            thread.join(timeout=10)
        self.assertEqual(result["status"], "error", result)
        self.assertTrue(result["data"].get("busy"), result)
        self.assertTrue(self.work(wid).exists())

    def test_registered_cleanup_refuses_while_an_upgrade_checkpoint_is_present(self):
        wid, _ = self.retained_closed_wave("upgrade")
        key = wid.split()[0]
        token = self.ok(self.cleanup_tool(work_key=key))["confirmation"]
        checkpoint = self.root / ".wavefoundry/upgrade-in-progress.json"
        checkpoint.write_text(json.dumps({"current_phase": "apply_framework"}))
        self.addCleanup(lambda: checkpoint.unlink(missing_ok=True))
        before = self.snapshot(self.work(wid))
        for mode in ("apply", "dry_run"):
            with self.subTest(mode=mode):
                result = self.cleanup_tool(work_key=key, mode=mode, confirmation=token)
                self.assertEqual(result["status"], "error", result)
                self.assertIn("upgrade_in_progress", json.dumps(result))
        self.assertEqual(self.snapshot(self.work(wid)), before)
        checkpoint.unlink()
        self.assertEqual(self.ok(self.cleanup_tool(work_key=key, mode="apply", confirmation=token))["outcome"],
                         "removed")

    # --- Change 23p9t: extra files in the record folder at Close -------------

    LEDGER_NOTE = ("Proof kept in evidence/ledger-cited.json; the sole baseline is named-only.txt; "
                   "raw captures under raw/ only.")

    def write(self, path, size, char="x"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(char * size, encoding="utf-8")
        return path

    def extras(self, result):
        found = [d for d in result["diagnostics"] or () if d["code"] == "record_extras_present"]
        return found

    def extras_detail(self, result):
        found = self.extras(result)
        self.assertEqual(len(found), 1, result["diagnostics"])
        self.assertIs(found[0]["advisory"], True)
        return found[0]["detail"]

    def citing_wave(self, slug="extras", *, skip=()):
        """A finished record whose ledger, record and folder hold the citation cases."""
        wid, wave_md, cid = self.wave(slug=slug)
        self.finish(wid, cid, skip=skip, observed=self.LEDGER_NOTE)
        folder = wave_md.parent
        rel_folder = folder.relative_to(self.root).as_posix()
        record_note = (
            "\n\nEvidence notes: evidence/record-cited.md holds the reviewer draft. "
            f"The repository form is {rel_folder}/evidence/repo-form.json and the "
            "sentence ends with evidence/full-stop.json. Only evidence/a.json.bak and "
            "data.json are named, and the notes/ folder holds scratch.\n")
        wave_md.write_text(wave_md.read_text().rstrip("\n") + record_note, encoding="utf-8")
        sizes = {
            "evidence/ledger-cited.json": 900, "evidence/named-only.txt": 800, "raw/one.log": 700,
            "evidence/record-cited.md": 600, "evidence/repo-form.json": 500, "evidence/full-stop.json": 400,
            "evidence/a.json": 300, "a.json": 200, "notes/n1.txt": 100, "nowhere.bin": 50, ".DS_Store": 10,
        }
        for rel, size in sizes.items():
            self.write(folder / rel, size)
        return wid, wave_md, cid, sizes

    EXPECTED_STATES = {
        # path: (citation, name_in_ledger, name_in_record, directory_in_ledger, directory_in_record)
        # A path citation also names the file as the tail of a path, so the
        # name boolean of the citing text is true for every cited file.
        "evidence/ledger-cited.json": ("cited_in_ledger", True, False, False, False),
        "evidence/named-only.txt": ("not_cited", True, False, False, False),
        "raw/one.log": ("not_cited", False, False, True, False),
        "evidence/record-cited.md": ("cited_in_record", False, True, False, False),
        "evidence/repo-form.json": ("cited_in_record", False, True, False, False),
        "evidence/full-stop.json": ("cited_in_record", False, True, False, False),
        "evidence/a.json": ("not_cited", False, False, False, False),
        "a.json": ("not_cited", False, False, False, False),
        "notes/n1.txt": ("not_cited", False, False, False, True),
        "nowhere.bin": ("not_cited", False, False, False, False),
        ".DS_Store": ("not_cited", False, False, False, False),
    }

    def test_close_reports_record_extras_with_citation_state_in_both_modes(self):
        wid, wave_md, _, sizes = self.citing_wave()
        folder = wave_md.parent
        # Independent oracle: a plain walk of the folder minus the recognized set.
        recognized = {wave_md.name, "events.jsonl", *(p.name for p in folder.glob("*.md") if p != wave_md)}
        walked = {p.relative_to(folder).as_posix(): p.stat().st_size for p in folder.rglob("*")
                  if p.is_file() and not (p.parent == folder and p.name in recognized)}
        self.assertEqual(walked, sizes)
        for mode in ("dry_run", "create"):
            with self.subTest(mode=mode):
                result = close_container(self.call, self.root, wid, mode=mode)
                self.assertEqual(result["status"], "dry_run" if mode == "dry_run" else "ok", result)
                detail = self.extras_detail(result)
                self.assertEqual((detail["files"], detail["bytes"], detail["complete"], detail["reason"]),
                                 (len(sizes), sum(sizes.values()), True, None))
                self.assertEqual(detail["folder"], folder.relative_to(self.root).as_posix())
                listed = detail["listed"]
                self.assertEqual([item["path"] for item in listed],
                                 sorted(sizes, key=lambda rel: (-sizes[rel], rel)), "largest first")
                for item in listed:
                    self.assertEqual(item["bytes"], sizes[item["path"]])
                    self.assertEqual(
                        (item["citation"], item["name_in_ledger"], item["name_in_record"],
                         item["directory_in_ledger"], item["directory_in_record"]),
                        self.EXPECTED_STATES[item["path"]], item["path"])
                states = [state[0] for state in self.EXPECTED_STATES.values()]
                self.assertEqual((detail["cited_in_ledger"], detail["cited_in_record"], detail["not_cited"]),
                                 (states.count("cited_in_ledger"), states.count("cited_in_record"),
                                  states.count("not_cited")))
                self.assertEqual(detail["directories"], [
                    {"path": "evidence/", "files": 6, "bytes": 3500, "not_cited": 2},
                    {"path": "raw/", "files": 1, "bytes": 700, "not_cited": 1},
                    {"path": "notes/", "files": 1, "bytes": 100, "not_cited": 1},
                ])
                message = self.extras(result)[0]["message"]
                self.assertIn(f"{len(sizes)} extra file(s)", message)
                self.assertIn(f"{sum(sizes.values())} logical bytes", message)
                self.assertIn(f"{states.count('not_cited')} not cited by path", message)
                self.assertIn(f"{states.count('cited_in_ledger')} cited in the ledger;", message)
                self.assertNotIn("not listed", message, "every file is listed below the cap")
                self.assertIn("folder-cleanup step", message)
        self.assertIn("Status: closed", wave_md.read_text())
        self.assertEqual({p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
                         - recognized, set(sizes), "the report removes nothing")

    def test_record_holding_only_the_recognized_set_reports_no_extras(self):
        wid, wave_md, cid = self.wave(slug="tidy")
        self.finish(wid, cid)
        for mode in ("dry_run", "create"):
            with self.subTest(mode=mode):
                result = close_container(self.call, self.root, wid, mode=mode)
                self.assertIn(result["status"], ("dry_run", "ok"), result)
                self.assertEqual(self.extras(result), [])

    def test_blocked_dry_run_before_operator_signoff_carries_the_report(self):
        wid, wave_md, _ = self.wave(slug="unsigned")
        self.finish(wid, _, skip=("operator-signoff",))
        self.write(wave_md.parent / "evidence/probe.txt", 42)
        result = close_container(self.call, self.root, wid, mode="dry_run")
        self.assertEqual(result["status"], "error", result)
        blockers = {d["code"]: d["message"] for d in result["diagnostics"] if not d.get("advisory")}
        # Both blockers name the one missing approval: the operator's.
        self.assertEqual(set(blockers), {"missing_operator_signoff", "missing_executable_approval_evidence"},
                         result["diagnostics"])
        self.assertIn("operator-signoff=pending", blockers["missing_executable_approval_evidence"])
        detail = self.extras_detail(result)
        self.assertEqual((detail["files"], detail["bytes"]), (1, 42))
        self.assertEqual(detail["listed"][0]["path"], "evidence/probe.txt")

    def test_listing_cap_keeps_the_largest_and_states_the_total(self):
        import wave_work

        wid, wave_md, cid = self.wave(slug="many")
        self.finish(wid, cid)
        count = wave_work.RECORD_EXTRAS_LIST_CAP + 5
        for index in range(count):
            self.write(wave_md.parent / f"raw/f{index:03d}.log", index + 1)
        result = close_container(self.call, self.root, wid, mode="dry_run")
        detail = self.extras_detail(result)
        self.assertEqual((detail["files"], detail["not_listed"], len(detail["listed"])),
                         (count, 5, wave_work.RECORD_EXTRAS_LIST_CAP))
        message = self.extras(result)[0]["message"]
        self.assertIn(f"{count} extra file(s), {count * (count + 1) // 2} logical bytes, {count} not cited by path "
                      f"and 0 cited in the ledger, 5 not listed;", message)
        self.assertEqual(min(item["bytes"] for item in detail["listed"]), 6, "the cap drops the smallest")
        self.assertEqual(detail["directories"], [{"path": "raw/", "files": count,
                                                  "bytes": count * (count + 1) // 2, "not_cited": count}])

    def test_recognized_set_follows_the_admitted_specs(self):
        wid, wave_md, first = self.wave(slug="members", ready=False)
        made = self.ok(self.srv._change_create_response(self.root, "enh", "members-second", mode="create"))
        second = made["change_id"]
        self.ok(self.call("wf_add_change", wave_id=wid, change_id=second, mode="create"))
        folder = wave_md.parent
        admitted = folder / f"{second}.md"
        self.assertTrue(admitted.is_file())
        result = close_container(self.call, self.root, wid, mode="dry_run")
        self.assertEqual(self.extras(result), [], "admitted specs, the record and the ledger are not extras")
        spec_bytes = admitted.read_bytes()
        self.ok(self.call("wf_remove_change", wave_id=wid, change_id=second, mode="create"))
        self.assertNotIn(second, wave_md.read_text())
        # The same file, left in the folder after it leaves the admitted set.
        admitted.write_bytes(spec_bytes)
        detail = self.extras_detail(close_container(self.call, self.root, wid, mode="dry_run"))
        self.assertEqual([item["path"] for item in detail["listed"]], [admitted.name])
        paths = {item["path"] for item in detail["listed"]}
        self.assertTrue({wave_md.name, "events.jsonl", f"{first}.md"}.isdisjoint(paths))
        self.assertTrue((folder / "events.jsonl").is_file())

    def comparable(self, result):
        diagnostics = [d for d in result["diagnostics"] or () if d["code"] != "record_extras_present"]
        data = {k: v for k, v in result["data"].items() if k not in ("wave_summary", "lint", "scanner_skips")}
        return result["status"], diagnostics, data

    def test_report_never_changes_the_close_result(self):
        wid, wave_md, cid = self.wave(slug="same")
        self.finish(wid, cid)
        without = close_container(self.call, self.root, wid, mode="dry_run")
        self.assertEqual(self.extras(without), [])
        twin = Path(self.tmp.name) / "twin"
        shutil.copytree(self.root, twin, symlinks=True)
        # Work ownership is bound to the original folder's identity; the twin
        # closes with no work area so only the record folder differs.
        shutil.rmtree(twin / ".wavefoundry/work" / wid.split()[0], ignore_errors=True)
        self.write(wave_md.parent / "evidence/probe.json", 64)
        with_extras = close_container(self.call, self.root, wid, mode="dry_run")
        self.assertEqual(len(self.extras(with_extras)), 1)
        self.assertEqual(self.comparable(with_extras), self.comparable(without))
        closed = close_container(self.call, self.root, wid, mode="create")
        self.handler.root = twin.resolve()
        try:
            twin_closed = close_container(self.call, twin.resolve(), wid, mode="create")
        finally:
            self.handler.root = self.root
        self.assertEqual(self.extras(twin_closed), [])
        self.assertEqual(len(self.extras(closed)), 1)
        self.assertEqual((closed["status"], [d["code"] for d in closed["diagnostics"] or ()
                                             if d["code"] != "record_extras_present"]),
                         (twin_closed["status"], [d["code"] for d in twin_closed["diagnostics"] or ()]))
        twin_md = twin.resolve() / wave_md.relative_to(self.root)
        self.assertEqual(wave_md.read_text(), twin_md.read_text(), "the written record is identical")

    def test_entry_limit_and_unreadable_entries_yield_incomplete_coverage(self):
        import wave_work

        wid, wave_md, cid = self.wave(slug="bounded")
        self.finish(wid, cid)
        for index in range(5):
            self.write(wave_md.parent / f"raw/f{index}.log", 10)
        baseline = close_container(self.call, self.root, wid, mode="dry_run")
        with self.subTest(case="entry_limit"), patch.object(wave_work, "RECORD_EXTRAS_ENTRY_LIMIT", 3):
            result = close_container(self.call, self.root, wid, mode="dry_run")
            detail = self.extras_detail(result)
            self.assertEqual((detail["complete"], detail["reason"], detail["entry_limit"]),
                             (False, "entry_limit", 3))
            self.assertLess(detail["files"], 5)
            self.assertIn("coverage incomplete: entry_limit", self.extras(result)[0]["message"])
            self.assertEqual(self.comparable(result), self.comparable(baseline))
        if os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0):
            self.skipTest("permission bits do not deny reads here")
        locked = wave_md.parent / "raw"
        os.chmod(locked, 0)
        self.addCleanup(os.chmod, locked, 0o755)
        with self.subTest(case="unreadable"):
            result = close_container(self.call, self.root, wid, mode="dry_run")
            detail = self.extras_detail(result)
            self.assertEqual((detail["complete"], detail["reason"]), (False, "unreadable:EACCES"))
            self.assertEqual(detail["unreadable"], [locked.relative_to(self.root).as_posix()])
            self.assertEqual(self.comparable(result), self.comparable(baseline))
        os.chmod(locked, 0o755)

    def test_unreadable_text_inputs_keep_their_own_result_and_report_incomplete(self):
        wid, wave_md, cid = self.wave(slug="inputs")
        self.finish(wid, cid)
        self.write(wave_md.parent / "evidence/probe.json", 64)
        ledger = wave_md.parent / "events.jsonl"
        spec = wave_md.parent / f"{cid}.md"
        # Wave 244in (244fj): Close reads the record raw through the sibling
        # seam ``_read_wave_record_original``, so that is the read denied here.
        with self.subTest(input="record"), \
                patch.object(self.srv, "_read_wave_record_original", return_value=(None, "PermissionError")) as denied:
            result = close_container(self.call, self.root, wid, mode="dry_run")
            denied.assert_called()
            self.assertEqual(result["status"], "error")
            self.assertIn("wave_record_unreadable", self.codes(result))
            detail = self.extras_detail(result)
            self.assertEqual((detail["complete"], detail["reason"], detail["files"], detail["listed"]),
                             (False, "record_unreadable", 0, []))
            self.assertEqual(detail["unreadable"], [wave_md.relative_to(self.root).as_posix()])
        if os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0):
            self.skipTest("permission bits do not deny reads here")
        real_read = self.srv._read_wave_record_text
        for path, name in ((ledger, "ledger"), (spec, "spec")):
            before = close_container(self.call, self.root, wid, mode="dry_run")
            real_report = self.srv._close_record_extras

            def denied_report(root, md, text, _path=path):
                # Only the report's own read is denied; the close reads as it did.
                os.chmod(_path, 0)
                try:
                    return real_report(root, md, text)
                finally:
                    os.chmod(_path, 0o644)
            with self.subTest(input=name), patch.object(self.srv, "_close_record_extras", side_effect=denied_report):
                result = close_container(self.call, self.root, wid, mode="dry_run")
                self.assertEqual(self.comparable(result), self.comparable(before))
                detail = self.extras_detail(result)
                self.assertEqual((detail["complete"], detail["reason"]), (False, "input_unreadable"))
                self.assertEqual(detail["unreadable"], [path.relative_to(self.root).as_posix()])
                self.assertEqual(detail["files"], 1)
        self.assertIs(self.srv._read_wave_record_text, real_read)
        with self.subTest(input="ledger, whole close"):
            os.chmod(ledger, 0)
            try:
                result = close_container(self.call, self.root, wid, mode="dry_run")
            finally:
                os.chmod(ledger, 0o644)
            self.assertEqual(result["status"], "error", "an unreadable ledger blocks through review authority")
            detail = self.extras_detail(result)
            self.assertFalse(detail["complete"])
            self.assertIn(ledger.relative_to(self.root).as_posix(), detail["unreadable"])

    def test_summary_and_projection_failure_returns_carry_the_report(self):
        wid, wave_md, cid = self.wave(slug="failures")
        self.finish(wid, cid)
        self.write(wave_md.parent / "evidence/probe.json", 64)
        cases = (
            ("change_doc_unreadable", "dry_run", "_generate_wf_close_wave_summary", OSError("denied")),
            ("review_projection_failed", "create", "_project_current_review_status", ValueError("projection")),
        )
        for code, mode, producer, error in cases:
            with self.subTest(code=code), patch.object(self.srv, producer, side_effect=error) as failing:
                result = close_container(self.call, self.root, wid, mode=mode)
                failing.assert_called()
                self.assertEqual(result["status"], "error", result)
                blockers = [d["code"] for d in result["diagnostics"] if not d.get("advisory")]
                self.assertEqual(blockers[:1], [code], result["diagnostics"])
                detail = self.extras_detail(result)
                self.assertEqual([item["path"] for item in detail["listed"]], ["evidence/probe.json"])

    def test_ledger_path_after_a_json_escape_is_cited(self):
        wid, wave_md, cid = self.wave(slug="escaped")
        # The real review-event writer stores the newline as the two characters `\n`.
        self.finish(wid, cid, observed="Run log follows:\nevidence/after-newline.json")
        folder = wave_md.parent
        self.write(folder / "evidence/after-newline.json", 30)
        self.assertIn("\\nevidence/after-newline.json", (folder / "events.jsonl").read_text(encoding="utf-8"))
        detail = self.extras_detail(close_container(self.call, self.root, wid, mode="dry_run"))
        self.assertEqual([(item["path"], item["citation"]) for item in detail["listed"]],
                         [("evidence/after-newline.json", "cited_in_ledger")])

    def test_walk_reports_a_link_without_traversing_it(self):
        wid, wave_md, cid = self.wave(slug="linked")
        self.finish(wid, cid)
        outside = Path(self.tmp.name) / "outside"
        self.write(outside / "secret.bin", 5000)
        self.write(outside / "deep/more.bin", 7000)
        link = wave_md.parent / "evidence"
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symbolic links cannot be created here: {exc}")
        detail = self.extras_detail(close_container(self.call, self.root, wid, mode="dry_run"))
        self.assertEqual([(item["path"], item["kind"]) for item in detail["listed"]], [("evidence", "link")])
        self.assertEqual(detail["files"], 1)
        self.assertEqual(detail["bytes"], os.lstat(link).st_size)
        self.assertLess(detail["bytes"], 5000)
        self.assertEqual(detail["directories"], [])
        self.assertTrue(detail["complete"])

    def test_report_is_close_only(self):
        wid, wave_md, cid = self.wave(slug="scope")
        self.write(wave_md.parent / "evidence/probe.json", 64)
        self.ok(self.call("wf_implement_wave", wave_id=wid, mode="create"))
        responses = {
            "wf_review_wave": self.call("wf_review_wave", wave_id=wid, phase="implementation"),
            "wf_prepare_wave": self.call("wf_prepare_wave", wave_id=wid, mode="dry_run"),
            "wf_audit": self.srv.wf_audit_response(self.root),
            "wf_close_change": self.call("wf_close_change", wave_id=wid, change_id=cid, mode="dry_run"),
            "wf_cleanup_work": self.cleanup_tool(work_key=wid.split()[0]),
            "wf_pause_wave": self.call("wf_pause_wave", wave_id=wid, mode="create"),
        }
        for name, response in responses.items():
            with self.subTest(tool=name):
                self.assertNotIn("record_extras_present", json.dumps(response, default=str))
        control = close_container(self.call, self.root, wid, mode="dry_run")
        self.assertEqual(len(self.extras(control)), 1, "the same fixture reports at Close")


class RecordCitationRuleTests(unittest.TestCase):
    """The stated name-character set and exact-match limits (change 23p9t)."""

    FOLDER = "abc12 sample"

    def state(self, rel, *, ledger="", record=""):
        import wave_work

        return wave_work.record_citation_state(rel, self.FOLDER, ledger, [record])

    def test_name_characters_bound_a_path(self):
        for text in ("x_a.json", "x-a.json", "xa.json", "9a.json", "a.json_x", "a.json-x", "a.jsonl",
                     "a.json.bak", "dir/a.json", "a.json.x"):
            with self.subTest(text=text):
                self.assertEqual(self.state("a.json", record=text)["citation"], "not_cited")
        for text in ("a.json", "see a.json.", "(a.json)", "`a.json`", "a.json, b", "a.json:3", "a.json/",
                     '"a.json"', "a.json. Next", "a.json.\n"):
            with self.subTest(text=text):
                self.assertEqual(self.state("a.json", record=text)["citation"], "cited_in_record")

    def test_repository_relative_form_and_ledger_precedence(self):
        rel = "evidence/a.json"
        # The prefix rule anchors on the folder's own name and `/`, so any
        # records root in front of it reads as the repository-relative form.
        self.assertEqual(self.state(rel, record=f"records/root/{self.FOLDER}/{rel}")["citation"], "cited_in_record")
        self.assertEqual(self.state(rel, record=f"other/{rel}")["citation"], "not_cited")
        self.assertEqual(self.state(rel, ledger=json.dumps({"observed": rel}), record=rel)["citation"],
                         "cited_in_ledger")

    def test_exact_comparison_limits(self):
        rel = "evidence/a.json"
        # Backslashes and letter case stay limits, raw or JSON-encoded.
        for text in ("evidence\\a.json", "Evidence/a.json", "EVIDENCE/A.JSON"):
            for ledger in (text, json.dumps({"observed": text})):
                with self.subTest(ledger=ledger):
                    self.assertEqual(self.state(rel, ledger=ledger)["citation"], "not_cited")

    def test_ledger_is_matched_on_decoded_json_values(self):
        rel = "evidence/a.json"
        cited = (
            json.dumps({"observed": "first line\nevidence/a.json"}),
            json.dumps({"observed": "col\tevidence/a.json"}),
            json.dumps({"observed": 'the "evidence/a.json" file'}),
            '{"observed": "evidence\\/a.json"}',
            '{"observed": "evidence\\u002fa.json"}',
            '{"observed": "evidence/a.json"}',
            json.dumps({"outer": [{"inner": "x\nevidence/a.json"}]}),
            json.dumps("bare string line\nevidence/a.json"),
            "not json: evidence/a.json",
        )
        for ledger in cited:
            with self.subTest(ledger=ledger):
                self.assertEqual(self.state(rel, ledger=ledger)["citation"], "cited_in_ledger")
        # A line that does not parse is matched raw, so its escape still hides the path.
        for ledger in ('{"observed": "x\\nevidence/a.json"', "not json \\nevidence/a.json"):
            with self.subTest(raw=ledger):
                self.assertEqual(self.state(rel, ledger=ledger)["citation"], "not_cited")
        # Lines are decoded independently; one bad line does not hide the others.
        mixed = "{broken\n" + json.dumps({"observed": "x\nevidence/a.json"})
        self.assertEqual(self.state(rel, ledger=mixed)["citation"], "cited_in_ledger")
        # The record and spec texts stay raw.
        self.assertEqual(self.state(rel, record="first\\nevidence/a.json")["citation"], "not_cited")

    def test_ledger_decoding_never_raises(self):
        import wave_work

        deep = "[" * 100_000 + "]" * 100_000
        for ledger in (deep, '{"n": ' + "9" * 5000 + "}", "\x00\udcff", "{}", "[]", "null"):
            with self.subTest(ledger=ledger[:20]):
                self.assertIsInstance(wave_work.ledger_strings(ledger), list)
                self.assertEqual(self.state("a.json", ledger=ledger)["citation"], "not_cited")
        # Some interpreters (3.11) raise RecursionError for deep nesting; the line is then matched raw.
        with patch.object(wave_work.json, "loads", side_effect=RecursionError):
            self.assertEqual(wave_work.ledger_strings('{"o": "a.json"}'), ['{"o": "a.json"}'])

    def test_file_name_as_the_tail_of_another_path(self):
        rel = "evidence/a.json"
        for text in ("/tmp/x/a.json", "C:\\tmp\\a.json", "see /tmp/a.json."):
            with self.subTest(text=text):
                ledger_state = self.state(rel, ledger=json.dumps({"command_or_fixture": text}))
                self.assertEqual((ledger_state["citation"], ledger_state["name_in_ledger"]), ("not_cited", True))
                record_state = self.state(rel, record=text)
                self.assertEqual((record_state["citation"], record_state["name_in_record"]), ("not_cited", True))
        for text in ("data.json", "/tmp/data.json", "/tmp/a.json.bak", "/tmp/x.a.json"):
            with self.subTest(text=text):
                self.assertFalse(self.state(rel, ledger=json.dumps({"observed": text}))["name_in_ledger"])
                self.assertFalse(self.state(rel, record=text)["name_in_record"])

    def test_loose_mentions_never_make_a_file_cited(self):
        state = self.state("evidence/sub/a.json", ledger="the evidence/ folder and a.json",
                           record="see evidence/sub/ and a.json")
        self.assertEqual(state, {"citation": "not_cited", "name_in_ledger": True, "name_in_record": True,
                                 "directory_in_ledger": True, "directory_in_record": True})
        # A sibling's path is not a mention of the directory.
        sibling = self.state("evidence/a.json", ledger="evidence/b.json")
        self.assertFalse(sibling["directory_in_ledger"])


if __name__ == "__main__":
    unittest.main()
