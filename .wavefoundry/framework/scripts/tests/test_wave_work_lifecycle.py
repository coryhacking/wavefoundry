"""Public lifecycle coverage for the disposable, owned wave workspace.

Fixtures use the real create/admit/readiness producers. Only unrelated docs,
index refresh, map generation and telemetry execution are replaced; lifecycle
guards, publication locks and workspace I/O remain live.
"""
from __future__ import annotations

import contextlib
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from server_tools_support import (
    _make_repo, declared_wave_doc_gates, integrity_checks, load_server,
    make_declared_wave, review_policy_config,
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

    def wave(self, slug="workspace", *, ready=True):
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
            self.srv, self.root, slug, change_ids=(cid,), ready=ready,
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

    def finish(self, wid, cid):
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
            actor = ("operator" if key == "operator-signoff" else
                     "council-chair" if key.startswith(("wave-council", "council-")) else key)
            self.ok(self.call(
                "wf_review_event", wave_id=wid, event="approval", actor=actor,
                context_id="workspace-delivery-" + key, signoff_key=key,
                approval_phase="delivery", fresh_context=True, independent=True, mode="create",
                evidence={"observed": "bounded workspace fixture", "artifact_or_test_id": self.id(),
                          **({"intent_fit": "establishes"} if "council" in key else {})},
                integrity_checks=integrity_checks(),
            ))
        self.ok(self.call("wf_close_change", wave_id=wid, change_id=cid, mode="create"))

    def test_registered_create_preview_does_not_create_and_paths_use_resolved_prefix(self):
        preview = self.call("wf_create_wave", slug="first", mode="dry_run")
        self.assertEqual(preview["status"], "dry_run", preview)
        self.assertFalse(self.area(preview)["available"])
        self.assertFalse((self.root / ".wavefoundry/work").exists())
        first = self.call("wf_create_wave", slug="first", mode="create")
        second = self.call("wf_create_wave", slug="second", mode="create")
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
        blocked = self.call("wf_close_wave", wave_id=wid, mode="create")
        self.assertEqual(blocked["status"], "error", blocked)
        self.assertTrue(scratch.exists())
        self.assertNotIn("Status: closed", wave_md.read_text())
        self.finish(wid, cid)
        self.assertTrue(scratch.exists(), "single-change close must preserve wave scratch")
        preview = self.call("wf_close_wave", wave_id=wid, mode="dry_run")
        self.assertEqual(preview["status"], "dry_run", preview)
        self.assertTrue(scratch.exists())
        self.assertNotIn("Status: closed", wave_md.read_text())

    def test_registered_whole_wave_close_removes_only_owned_scratch(self):
        wid, wave_md, cid = self.wave()
        other = self.ok(self.call("wf_create_wave", slug="neighbor", mode="create"))["wave_id"]
        neighbor = self.scratch(other, "neighbor")
        scratch = self.scratch(wid)
        durable = wave_md.parent / "final-proof.txt"
        durable.write_text("unique durable proof")
        external = self.root / "external-proof.txt"
        external.write_text("outside owned area")
        self.finish(wid, cid)
        ledger = wave_md.parent / "events.jsonl"
        ledger_before = ledger.read_bytes()
        result = self.call("wf_close_wave", wave_id=wid.split()[0], mode="create")
        self.ok(result)
        self.assertIn("work_cleanup", result["data"])
        self.assertIn("Status: closed", wave_md.read_text())
        self.assertFalse(scratch.exists())
        self.assertFalse(self.work(wid).exists())
        self.assertEqual(neighbor.read_text(), "neighbor")
        self.assertEqual(durable.read_text(), "unique durable proof")
        self.assertEqual(external.read_text(), "outside owned area")
        self.assertEqual(ledger.read_bytes(), ledger_before)

    def test_cleanup_io_failure_keeps_closed_status_and_authorized_retry_cleans(self):
        import wave_work

        wid, wave_md, cid = self.wave()
        scratch = self.scratch(wid)
        self.finish(wid, cid)
        with patch.object(wave_work, "cleanup_work", side_effect=OSError("fixture I/O failure")):
            result = self.call("wf_close_wave", wave_id=wid, mode="create")
        self.ok(result)
        self.assertIn("Status: closed", wave_md.read_text())
        self.assertTrue(scratch.exists())
        self.assertTrue(result["data"]["work_cleanup"]["notice"])
        self.ok(self.call("wf_close_wave", wave_id=wid, mode="create"))
        self.assertFalse(self.work(wid).exists())

    def test_missing_work_area_is_an_idempotent_close_noop(self):
        wid, wave_md, cid = self.wave()
        self.finish(wid, cid)
        shutil.rmtree(self.work(wid))
        for attempt in range(2):
            with self.subTest(attempt=attempt):
                result = self.call("wf_close_wave", wave_id=wid, mode="create")
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
                results.append(self.call("wf_close_wave", wave_id=wid, mode="create"))
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
            self.ok(self.call("wf_close_wave", wave_id=wid, mode="create"))
        reopened = self.call("wf_reopen_wave", wave_id=wid, purpose="implement")
        self.ok(reopened)
        self.assertNotEqual(self.area(reopened)["generation"], old)
        self.assertTrue(self.area(reopened)["notice"])
        self.assertEqual(scratch.read_text(), "left behind")
        wave_work.cleanup_work(self.root, wave_md, expected_generation=old)
        self.assertEqual(scratch.read_text(), "left behind")


if __name__ == "__main__":
    unittest.main()
