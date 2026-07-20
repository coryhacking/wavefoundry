from __future__ import annotations

import json
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import memory_backfill
import memory_cli
import memory_records
import index_state_store
import server_impl
import setup_wavefoundry


class HistoricalMemoryBackfillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs" / "waves").mkdir(parents=True)
        (self.root / "foo.py").write_text("VALUE = 1\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _wave(
        self,
        name: str,
        *,
        status: str = "closed",
        decision: bool = True,
        change_id: str = "1abc-enh historical-decision",
    ) -> Path:
        wave = self.root / "docs" / "waves" / name
        wave.mkdir()
        wave.joinpath("wave.md").write_text(
            "# Wave\n\n"
            f"Status: {status}\n\n"
            f"Change ID: `{change_id}`\n",
            encoding="utf-8",
        )
        if decision:
            wave.joinpath(f"{change_id}.md").write_text(
                "# Change\n\n## Decision Log\n\n"
                "| Date | Decision | Reason | Alternatives |\n"
                "| --- | --- | --- | --- |\n"
                "| 2026-01-01 | Keep `foo.py` local | Avoid remote authority | none |\n",
                encoding="utf-8",
            )
        return wave

    def _add_decisions(self, wave: Path, count: int, *, prefix: str = "1b") -> None:
        wave_md = wave / "wave.md"
        admitted: list[str] = []
        for index in range(count):
            change_id = f"{prefix}{index:03d}-enh decision-{index}"
            admitted.append(f"Change ID: `{change_id}`")
            wave.joinpath(f"{change_id}.md").write_text(
                "# Change\n\n## Decision Log\n\n"
                "| Date | Decision | Reason | Alternatives |\n"
                "| --- | --- | --- | --- |\n"
                f"| 2026-01-01 | Keep `foo.py` local for case {index} | "
                f"Durable reason {index} | none |\n",
                encoding="utf-8",
            )
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + "\n"
            + "\n".join(admitted)
            + "\n",
            encoding="utf-8",
        )

    def test_inventory_is_git_independent_and_closed_only(self):
        self._wave("1aaa closed")
        self._wave("1aab active", status="implementing")
        with mock.patch("subprocess.run", side_effect=AssertionError("git must not run")):
            inventory = memory_backfill.inventory_closed_waves(self.root)
        self.assertEqual([row["wave_id"] for row in inventory], ["1aaa closed"])

    def test_inventory_and_resolver_ignore_symlinked_wave_directories(self):
        with tempfile.TemporaryDirectory() as outside_tmp:
            outside = Path(outside_tmp) / "1zzz outside"
            outside.mkdir()
            outside.joinpath("wave.md").write_text(
                "# Outside\n\nStatus: closed\n", encoding="utf-8"
            )
            link = self.root / "docs" / "waves" / "1zzz outside"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")
            self.assertEqual(memory_backfill.inventory_closed_waves(self.root), ())
            supply = server_impl._load_script("memory_supply")
            self.assertEqual(
                supply.resolve_wave_dir(self.root, "1zzz"),
                (None, "wave_not_found"),
            )

    def test_inventory_rejects_symlinked_waves_parent(self):
        with tempfile.TemporaryDirectory() as outside_tmp:
            outside = Path(outside_tmp)
            wave = outside / "1zzz external"
            wave.mkdir()
            wave.joinpath("wave.md").write_text(
                "# Outside\n\nStatus: closed\n", encoding="utf-8"
            )
            waves_dir = self.root / "docs" / "waves"
            waves_dir.rmdir()
            try:
                waves_dir.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")
            with self.assertRaises(OSError):
                memory_backfill.inventory_closed_waves(self.root)
            response = server_impl.wave_memory_backfill_response(
                self.root, mode="create", entry_path="upgrade"
            )
            self.assertEqual(response["status"], "error")
            self.assertEqual(
                response["diagnostics"][0]["code"],
                "historical_memory_inventory_failed",
            )

    def test_inventory_rejects_symlinked_wave_sources_inside_real_directory(self):
        wave = self.root / "docs" / "waves" / "1zzz outside-source"
        wave.mkdir()
        outside = self.root.parent / f"{self.root.name}-outside-wave.md"
        outside.write_text("# Outside\n\nStatus: closed\n", encoding="utf-8")
        try:
            wave.joinpath("wave.md").symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"file symlinks unavailable: {exc}")
        try:
            inventory = memory_backfill.inventory_closed_waves(self.root)
            self.assertEqual(len(inventory), 1)
            self.assertEqual(inventory[0]["status"], "unsupported")
            response = server_impl.wave_memory_backfill_response(
                self.root, mode="create", entry_path="upgrade"
            )
            self.assertEqual(response["data"]["waves_unsupported"], 1)
            self.assertEqual(memory_records.load_memory_records(self.root), [])
        finally:
            outside.unlink(missing_ok=True)

    def test_public_backfill_rejects_unbounded_or_unknown_entry_path(self):
        response = server_impl.wave_memory_backfill_response(
            self.root,
            mode="create",
            entry_path="x" * 70000,
        )
        self.assertEqual(response["status"], "error")
        self.assertEqual(
            response["data"]["valid_entry_paths"],
            ["manual", "setup", "upgrade"],
        )
        self.assertLess(len(json.dumps(response)), 2048)

    def test_public_create_inventories_history_once(self):
        self._wave("1aaa closed")
        original = memory_backfill.inventory_closed_waves
        original_loader = server_impl._load_script
        with mock.patch.object(
            memory_backfill,
            "inventory_closed_waves",
            wraps=original,
        ) as inventory, mock.patch.object(
            server_impl,
            "_load_script",
            side_effect=lambda name: (
                memory_backfill
                if name == "memory_backfill"
                else original_loader(name)
            ),
        ):
            response = server_impl.wave_memory_backfill_response(
                self.root, mode="create", entry_path="manual"
            )
        self.assertEqual(response["status"], "ok")
        self.assertEqual(inventory.call_count, 1)

    def test_concurrent_first_run_creation_is_atomic_across_processes(self):
        barrier = self.root / "release-workers"
        child = r"""
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import memory_backfill
root = Path(sys.argv[2])
barrier = Path(sys.argv[3])
deadline = time.monotonic() + 15
while not barrier.exists():
    if time.monotonic() >= deadline:
        raise SystemExit("barrier timeout")
    time.sleep(0.005)
print(memory_backfill.ensure_run(root, "setup"), flush=True)
"""
        workers = [
            subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    child,
                    str(SCRIPTS),
                    str(self.root),
                    str(barrier),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(16)
        ]
        barrier.write_text("go\n", encoding="utf-8")
        run_ids: list[str] = []
        for worker in workers:
            stdout, stderr = worker.communicate(timeout=30)
            self.assertEqual(worker.returncode, 0, stderr)
            run_ids.append(stdout.strip())
        self.assertEqual(len(set(run_ids)), 1, run_ids)

    def test_sqlite_authority_rejects_symlink_target_outside_root(self):
        index = self.root / ".wavefoundry" / "index"
        index.mkdir(parents=True)
        outside = self.root.parent / f"{self.root.name}-outside.sqlite"
        outside.write_bytes(b"")
        try:
            index.joinpath("memory-state.sqlite").symlink_to(outside)
        except OSError as exc:
            outside.unlink(missing_ok=True)
            self.skipTest(f"file symlinks unavailable: {exc}")
        try:
            with self.assertRaises(OSError):
                memory_backfill.ensure_run(self.root, "manual")
            self.assertEqual(outside.stat().st_size, 0)
        finally:
            outside.unlink(missing_ok=True)

    def test_random_claim_replaces_crashed_owner_under_next_os_lock(self):
        self._wave("1aaa closed")
        run_id = memory_backfill.ensure_run(self.root, "upgrade")
        memory_backfill.sync_inventory(self.root, run_id)
        first = memory_backfill.claim_next(self.root, run_id)
        second = memory_backfill.claim_next(self.root, run_id)
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first["wave_id"], second["wave_id"])
        self.assertNotEqual(first["claim_token"], second["claim_token"])
        with self.assertRaises(RuntimeError):
            memory_backfill.complete_claim(
                self.root,
                run_id,
                first["wave_id"],
                first["claim_token"],
                outcome="no_source",
                candidate_count=0,
                exhausted=True,
            )

    def test_real_child_death_releases_lock_and_claim_is_recovered(self):
        self._wave("1aaa closed")
        barrier = self.root / "start-child"
        child = r"""
import os, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import memory_backfill
from review_evidence import review_event_write_lock
root = Path(sys.argv[2])
barrier = Path(sys.argv[3])
while not barrier.exists():
    time.sleep(0.01)
with review_event_write_lock(root):
    run_id = memory_backfill.ensure_run(root, "upgrade")
    memory_backfill.sync_inventory(root, run_id)
    claim = memory_backfill.claim_next(root, run_id)
    if claim is None:
        raise SystemExit(3)
    os._exit(19)
"""
        proc = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-c",
                child,
                str(SCRIPTS),
                str(self.root),
                str(barrier),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        barrier.write_text("go\n", encoding="utf-8")
        stdout, stderr = proc.communicate(timeout=20)
        self.assertEqual(proc.returncode, 19, (stdout, stderr))

        recovered = server_impl.wave_memory_backfill_response(
            self.root, mode="create", entry_path="upgrade"
        )
        self.assertEqual(recovered["status"], "ok", recovered)
        self.assertEqual(recovered["data"]["failures"], 0)
        self.assertEqual(len(memory_records.load_memory_records(self.root)), 1)

    def test_two_real_processes_serialize_without_duplicate_candidates(self):
        self._wave("1aaa closed")
        barrier = self.root / "start-two"
        child = r"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import server_impl
root = Path(sys.argv[2])
barrier = Path(sys.argv[3])
while not barrier.exists():
    time.sleep(0.01)
result = server_impl.wave_memory_backfill_response(
    root, mode="create", entry_path="upgrade"
)
print(json.dumps({"status": result["status"], "data": result["data"]}))
"""
        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    child,
                    str(SCRIPTS),
                    str(self.root),
                    str(barrier),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(2)
        ]
        barrier.write_text("go\n", encoding="utf-8")
        outputs = [proc.communicate(timeout=30) for proc in processes]
        for proc, (stdout, stderr) in zip(processes, outputs):
            self.assertEqual(proc.returncode, 0, stderr)
            self.assertEqual(json.loads(stdout)["status"], "ok")
        records = memory_records.load_memory_records(self.root)
        self.assertEqual(len(records), 1)
        self.assertEqual(
            len({record["source_event"] for record in records}),
            1,
        )

    def test_two_real_processes_advance_different_waves_with_exact_pages(self):
        self._wave("1aaa closed")
        self._wave("1aab closed", change_id="1abd-enh second-decision")
        barrier = self.root / "start-different-waves"
        child = r"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import server_impl
root = Path(sys.argv[2])
barrier = Path(sys.argv[3])
while not barrier.exists():
    time.sleep(0.01)
result = server_impl.wave_memory_backfill_response(
    root, mode="create", limit=1, entry_path="upgrade"
)
print(json.dumps({
    "status": result["status"],
    "processed": [row["wave_id"] for row in result["data"]["processed"]],
}))
"""
        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    child,
                    str(SCRIPTS),
                    str(self.root),
                    str(barrier),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(2)
        ]
        barrier.write_text("go\n", encoding="utf-8")
        outputs = [proc.communicate(timeout=30) for proc in processes]
        payloads = []
        for proc, (stdout, stderr) in zip(processes, outputs):
            self.assertEqual(proc.returncode, 0, stderr)
            payloads.append(json.loads(stdout))
        self.assertEqual([item["status"] for item in payloads], ["ok", "ok"])
        self.assertEqual(
            {wave for item in payloads for wave in item["processed"]},
            {"1aaa closed", "1aab closed"},
        )
        self.assertEqual(len(memory_records.load_memory_records(self.root)), 2)

    def test_public_batch_creates_candidate_then_validation_releases_gate(self):
        self._wave("1aaa closed")
        with mock.patch.object(
            server_impl, "_trigger_background_index_refresh_for_paths"
        ) as refresh:
            response = server_impl.wave_memory_backfill_response(
                self.root, mode="create", entry_path="upgrade"
            )
        self.assertEqual(response["status"], "ok", response)
        self.assertEqual(response["data"]["state"], "awaiting_validation")
        self.assertEqual(response["data"]["candidates_drafted"], 1)
        self.assertEqual(response["data"]["validation_worklist_count"], 1)
        self.assertEqual(
            response["data"]["validation_worklist"][0]["memory_id"],
            memory_records.load_memory_records(self.root)[0]["memory_id"],
        )
        refresh.assert_not_called()
        records = memory_records.load_memory_records(self.root)
        self.assertEqual(len(records), 1)
        candidate = records[0]
        self.assertEqual(candidate["status"], "candidate")

        with mock.patch.object(
            server_impl, "_trigger_background_index_refresh_for_paths"
        ) as validation_refresh:
            validated = server_impl.wave_memory_validate_response(
                self.root,
                candidate["memory_id"],
                "promote",
                "Reuse the local decision.",
                "The historical decision still matches foo.py.",
                True,
                True,
                "none",
            )
        self.assertEqual(validated["status"], "ok", validated)
        validation_refresh.assert_not_called()
        run_id = response["data"]["run_id"]
        summary = memory_backfill.run_summary(self.root, run_id)
        self.assertEqual(summary["state"], "ready_for_index")
        memory_backfill.mark_indexed(self.root, run_id)
        self.assertEqual(memory_backfill.run_summary(self.root, run_id)["state"], "indexed")

    def test_validation_worklist_is_run_scoped_and_pages_exact_candidate_ids(self):
        wave = self._wave("1aaa closed", decision=False)
        self._add_decisions(wave, 25)
        first = server_impl.wave_memory_backfill_response(
            self.root, mode="create", limit=20, entry_path="upgrade"
        )
        self.assertEqual(first["data"]["validation_worklist_count"], 20)
        self.assertEqual(len(first["data"]["validation_worklist"]), 20)
        self.assertEqual(
            {
                row["memory_id"] for row in first["data"]["validation_worklist"]
            },
            {
                record["memory_id"]
                for record in memory_records.load_memory_records(self.root)
            },
        )
        second = server_impl.wave_memory_backfill_response(
            self.root, mode="create", limit=20, entry_path="upgrade"
        )
        self.assertEqual(second["data"]["validation_worklist_count"], 25)
        self.assertEqual(len(second["data"]["validation_worklist"]), 20)
        self.assertEqual(second["data"]["validation_worklist_remaining"], 5)

    def test_rewrite_outcome_tracks_original_candidate_not_replacement_order(self):
        self._wave("1aaa closed")
        batch = server_impl.wave_memory_backfill_response(
            self.root, mode="create", entry_path="upgrade"
        )
        candidate = memory_records.load_memory_records(self.root)[0]
        rewritten = server_impl.wave_memory_validate_response(
            self.root,
            candidate["memory_id"],
            "rewrite",
            "Use the corrected rule.",
            "The historical decision is useful after correction.",
            True,
            True,
            "none",
            rewrite_kind="decision",
            rewrite_title="Zzz corrected rule",
            rewrite_summary="Use the corrected local decision.",
            rewrite_evidence=["1aaa", "foo.py"],
            rewrite_targets=["foo.py"],
            rewrite_confidence=0.9,
        )
        self.assertEqual(rewritten["status"], "ok", rewritten)

        summary = memory_backfill.run_summary(
            self.root, batch["data"]["run_id"]
        )

        self.assertEqual(summary["rewritten"], 1)
        self.assertEqual(summary["promoted"], 0)
        self.assertEqual(summary["candidates_pending"], 0)

    def test_cli_rewrite_forwards_complete_correction_contract(self):
        response = {"status": "ok", "data": {"state": "awaiting_validation"}}
        with mock.patch.object(
            memory_cli.server_impl,
            "wave_memory_validate_response",
            return_value=response,
        ) as validate, mock.patch("builtins.print"):
            exit_code = memory_cli.main(
                [
                    "validate",
                    "--root",
                    str(self.root),
                    "--memory-id",
                    "1abc-memory",
                    "--verdict",
                    "rewrite",
                    "--action-delta",
                    "Use the corrected rule.",
                    "--rationale",
                    "Current evidence supports the correction.",
                    "--canonical-overlap",
                    "none",
                    "--evidence-verified",
                    "--current-target-verified",
                    "--rewrite-kind",
                    "constraint",
                    "--rewrite-title",
                    "Corrected",
                    "--rewrite-summary",
                    "Use the corrected implementation.",
                    "--rewrite-evidence",
                    "docs/spec.md",
                    "--rewrite-target",
                    "foo.py",
                    "--rewrite-confidence",
                    "0.9",
                ]
            )
        self.assertEqual(exit_code, memory_backfill.ACTION_REQUIRED_EXIT)
        self.assertEqual(validate.call_args.kwargs["rewrite_kind"], "constraint")
        self.assertEqual(validate.call_args.kwargs["rewrite_evidence"], ["docs/spec.md"])
        self.assertEqual(validate.call_args.kwargs["rewrite_targets"], ["foo.py"])

    def test_candidate_committed_before_checkpoint_is_recovered_on_retry(self):
        self._wave("1aaa closed")
        backfill_impl = server_impl._load_script("memory_backfill")
        original = backfill_impl.complete_claim
        calls = 0

        def crash_after_file(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("simulated death after candidate write")
            return original(*args, **kwargs)

        with mock.patch.object(backfill_impl, "complete_claim", side_effect=crash_after_file):
            first = server_impl.wave_memory_backfill_response(
                self.root, mode="create", entry_path="upgrade"
            )
        self.assertEqual(first["data"]["failures"], 1)
        self.assertEqual(len(memory_records.load_memory_records(self.root)), 1)
        second = server_impl.wave_memory_backfill_response(
            self.root, mode="create", entry_path="upgrade"
        )
        self.assertEqual(second["data"]["failures"], 0)
        self.assertEqual(second["data"]["candidates_pending"], 1)
        self.assertEqual(second["data"]["candidates_drafted"], 1)
        self.assertEqual(len(memory_records.load_memory_records(self.root)), 1)

    def test_process_death_after_completed_batch_replays_as_noop(self):
        self._wave("1aaa closed")
        child = r"""
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import server_impl
result = server_impl.wave_memory_backfill_response(
    Path(sys.argv[2]), mode="create", entry_path="upgrade"
)
if result["status"] != "ok" or result["data"]["remaining_waves"] != 0:
    raise SystemExit(3)
os._exit(23)
"""
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                child,
                str(SCRIPTS),
                str(self.root),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 23, (proc.stdout, proc.stderr))
        retry = server_impl.wave_memory_backfill_response(
            self.root, mode="create", entry_path="upgrade"
        )
        self.assertEqual(retry["status"], "ok", retry)
        self.assertEqual(retry["data"]["processed"], [])
        self.assertEqual(retry["data"]["remaining_waves"], 0)
        self.assertEqual(len(memory_records.load_memory_records(self.root)), 1)

    def test_source_fingerprint_change_requeues_completed_wave(self):
        wave = self._wave("1aaa closed", decision=False)
        run_id = memory_backfill.ensure_run(self.root, "upgrade")
        memory_backfill.sync_inventory(self.root, run_id)
        claim = memory_backfill.claim_next(self.root, run_id)
        self.assertIsNotNone(claim)
        memory_backfill.complete_claim(
            self.root,
            run_id,
            claim["wave_id"],
            claim["claim_token"],
            outcome="no_source",
            candidate_count=0,
            exhausted=True,
        )
        self.assertEqual(
            memory_backfill.run_summary(self.root, run_id)["remaining_waves"],
            0,
        )
        wave.joinpath("1abc-enh added-decision.md").write_text(
            "# Change\n\n## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n"
            "| --- | --- | --- | --- |\n"
            "| 2026-01-02 | Keep `foo.py` local | Durable reason | none |\n",
            encoding="utf-8",
        )
        changed = memory_backfill.sync_inventory(self.root, run_id)
        self.assertEqual(changed["remaining_waves"], 1)
        self.assertEqual(changed["state"], "awaiting_validation")

    def test_fingerprint_requeue_preserves_exact_durable_candidate_census(self):
        wave = self._wave("1aaa closed")
        first = server_impl.wave_memory_backfill_response(
            self.root, mode="create", entry_path="upgrade"
        )
        candidate = memory_records.load_memory_records(self.root)[0]
        server_impl.wave_memory_validate_response(
            self.root,
            candidate["memory_id"],
            "promote",
            "Keep the verified historical decision.",
            "The target still implements it.",
            True,
            True,
            "none",
        )
        wave.joinpath("wave.md").write_text(
            wave.joinpath("wave.md").read_text(encoding="utf-8")
            + "\n<!-- local source update -->\n",
            encoding="utf-8",
        )

        changed = memory_backfill.sync_inventory(
            self.root, first["data"]["run_id"]
        )

        self.assertEqual(changed["candidates_drafted"], 1)
        self.assertEqual(changed["promoted"], 1)
        self.assertEqual(changed["remaining_waves"], 1)

    def test_malformed_ledger_is_unsupported_not_empty_success(self):
        wave = self._wave("1aaa closed", decision=False)
        wave.joinpath("events.jsonl").write_text("{bad json}\n", encoding="utf-8")
        response = server_impl.wave_memory_backfill_response(
            self.root, mode="create", entry_path="upgrade"
        )
        self.assertEqual(response["status"], "ok", response)
        self.assertEqual(response["data"]["waves_unsupported"], 1)
        self.assertEqual(response["data"]["waves_no_source"], 0)

    def test_large_history_obeys_named_wave_and_candidate_bounds(self):
        for index in range(12):
            self._wave(
                f"1a{index:02d} closed",
                change_id=f"1b{index:02d}-enh decision-{index}",
            )
        response = server_impl.wave_memory_backfill_response(
            self.root, mode="create", limit=20, entry_path="manual"
        )
        self.assertLessEqual(len(response["data"]["processed"]), 10)
        self.assertLessEqual(response["data"]["candidates_drafted"], 20)
        self.assertGreater(response["data"]["remaining_waves"], 0)

    def test_repeated_batches_exhaust_after_disposition_filtering(self):
        wave = self._wave("1aaa closed", decision=False)
        self._add_decisions(wave, 25)

        first = server_impl.wave_memory_backfill_response(
            self.root, mode="create", limit=20, entry_path="manual"
        )
        self.assertEqual(first["data"]["candidates_drafted"], 20)
        self.assertEqual(first["data"]["remaining_waves"], 1)
        self.assertEqual(first["data"]["processed"][0]["exhausted"], False)

        second = server_impl.wave_memory_backfill_response(
            self.root, mode="create", limit=20, entry_path="manual"
        )
        self.assertEqual(second["data"]["candidates_drafted"], 25)
        self.assertEqual(second["data"]["remaining_waves"], 0)
        self.assertEqual(second["data"]["processed"][0]["candidates_written"], 5)
        self.assertEqual(second["data"]["processed"][0]["exhausted"], True)

        third = server_impl.wave_memory_backfill_response(
            self.root, mode="create", limit=20, entry_path="manual"
        )
        self.assertEqual(third["data"]["processed"], [])
        self.assertEqual(len(memory_records.load_memory_records(self.root)), 25)

    def test_response_size_is_bounded_even_when_failure_text_is_huge(self):
        self._wave("1aaa closed")
        huge = "x" * (memory_backfill.MAX_RESPONSE_BYTES * 2)
        failed = {
            "status": "error",
            "data": {},
            "diagnostics": [{"code": "query_failed", "message": huge}],
        }
        with mock.patch.object(
            server_impl,
            "_wave_memory_propose_response_locked",
            return_value=failed,
        ):
            response = server_impl.wave_memory_backfill_response(
                self.root, mode="create", entry_path="manual"
            )
        encoded = json.dumps(response["data"], ensure_ascii=False).encode("utf-8")
        self.assertLessEqual(len(encoded), memory_backfill.MAX_RESPONSE_BYTES)
        self.assertTrue(response["data"]["response_truncated"])

    def test_empty_project_is_ready_without_materializing_wave_work(self):
        run_id = memory_backfill.ensure_run(self.root, "setup")
        summary = memory_backfill.sync_inventory(self.root, run_id)
        self.assertEqual(summary["eligible_waves"], 0)
        self.assertEqual(summary["state"], "ready_for_index")

    def test_ready_backfill_routes_to_owning_lifecycle_without_setup_tool(self):
        setup = server_impl.wave_memory_backfill_response(
            self.root, mode="create", entry_path="setup"
        )
        self.assertEqual(setup["data"]["state"], "ready_for_index")
        self.assertEqual(setup["next_tools"], [])
        self.assertIn("wf setup", setup["usage"])

        upgrade = server_impl.wave_memory_backfill_response(
            self.root, mode="create", entry_path="upgrade"
        )
        self.assertEqual(upgrade["data"]["state"], "ready_for_index")
        self.assertEqual(upgrade["next_tools"], ["wave_upgrade"])
        self.assertIn("resume_after_memory", upgrade["usage"])

    def test_setup_pauses_then_ordinary_rerun_owns_first_index_publication(self):
        self._wave("1aaa closed")
        (self.root / ".wavefoundry" / "framework").mkdir(parents=True)
        config = self.root / "docs" / "workflow-config.json"
        config.write_text(
            '{"lifecycle_id_policy":{"scheme_version":"v2"}}\n',
            encoding="utf-8",
        )
        calls: list[list[str] | None] = []

        class FakeSetup:
            @staticmethod
            def main(argv=None):
                calls.append(argv)
                if argv is not None and "--deps-only" not in argv:
                    index_dir = self.root / ".wavefoundry" / "index"
                    attempt = index_state_store.begin_build_epoch(index_dir, "all")
                    return 0 if index_state_store.finalize_build_epoch(
                        index_dir, attempt
                    ) else 1
                return 0

        with mock.patch.object(
            setup_wavefoundry, "_load_setup_index", return_value=FakeSetup
        ), mock.patch.object(
            setup_wavefoundry, "_run_render_platform_surfaces", return_value=0
        ), mock.patch.object(
            setup_wavefoundry, "_run_mcp_server_dry_run", return_value=0
        ), mock.patch.object(
            setup_wavefoundry.venv_bootstrap,
            "ensure_python_resolves",
            return_value="ok",
        ):
            first = setup_wavefoundry.main(["--root", str(self.root)])
        self.assertEqual(first, memory_backfill.ACTION_REQUIRED_EXIT)
        self.assertEqual(len(calls), 1)
        self.assertIn("--deps-only", calls[0])

        batch = server_impl.wave_memory_backfill_response(
            self.root, mode="create", entry_path="setup"
        )
        candidate = memory_records.load_memory_records(self.root)[0]
        server_impl.wave_memory_validate_response(
            self.root,
            candidate["memory_id"],
            "promote",
            "Reuse the local decision.",
            "The target remains current.",
            True,
            True,
            "none",
        )
        with mock.patch.object(
            setup_wavefoundry, "_load_setup_index", return_value=FakeSetup
        ), mock.patch.object(
            setup_wavefoundry, "_run_render_platform_surfaces", return_value=0
        ), mock.patch.object(
            setup_wavefoundry, "_run_mcp_server_dry_run", return_value=0
        ), mock.patch.object(
            setup_wavefoundry.venv_bootstrap,
            "ensure_python_resolves",
            return_value="ok",
        ):
            resumed = setup_wavefoundry.main(
                ["--root", str(self.root), "--background-code"]
            )
        self.assertEqual(resumed, 0, batch)
        self.assertEqual(len(calls), 3)
        self.assertIn("--deps-only", calls[1])
        self.assertNotIn("--deps-only", calls[2])
        self.assertNotIn("--background-code", calls[2])
        self.assertEqual(
            memory_backfill.latest_run_id(self.root, "setup"),
            batch["data"]["run_id"],
        )
        with mock.patch.object(
            setup_wavefoundry, "_load_setup_index", return_value=FakeSetup
        ), mock.patch.object(
            setup_wavefoundry, "_run_render_platform_surfaces", return_value=0
        ), mock.patch.object(
            setup_wavefoundry, "_run_mcp_server_dry_run", return_value=0
        ), mock.patch.object(
            setup_wavefoundry.venv_bootstrap,
            "ensure_python_resolves",
            return_value="ok",
        ):
            unchanged = setup_wavefoundry.main(["--root", str(self.root)])
        self.assertEqual(unchanged, 0)
        self.assertEqual(len(calls), 5)
        self.assertEqual(
            memory_backfill.latest_run_id(self.root, "setup"),
            batch["data"]["run_id"],
        )

    def test_setup_retry_recovers_published_epoch_without_second_index_pass(self):
        self._wave("1aaa closed")
        (self.root / ".wavefoundry" / "framework").mkdir(parents=True)
        (self.root / "docs" / "workflow-config.json").write_text(
            '{"lifecycle_id_policy":{"scheme_version":"v2"}}\n',
            encoding="utf-8",
        )
        index_calls = 0
        server_impl.wave_memory_backfill_response(
            self.root, mode="create", entry_path="setup"
        )
        candidate = memory_records.load_memory_records(self.root)[0]
        server_impl.wave_memory_validate_response(
            self.root,
            candidate["memory_id"],
            "promote",
            "Reuse the local decision.",
            "The target remains current.",
            True,
            True,
            "none",
        )

        class FakeSetup:
            @staticmethod
            def main(argv=None):
                nonlocal index_calls
                if argv is not None and "--deps-only" not in argv:
                    index_calls += 1
                    index_dir = self.root / ".wavefoundry" / "index"
                    attempt = index_state_store.begin_build_epoch(index_dir, "all")
                    return 0 if index_state_store.finalize_build_epoch(
                        index_dir, attempt
                    ) else 1
                return 0

        patches = (
            mock.patch.object(setup_wavefoundry, "_load_setup_index", return_value=FakeSetup),
            mock.patch.object(setup_wavefoundry, "_run_render_platform_surfaces", return_value=0),
            mock.patch.object(setup_wavefoundry, "_run_mcp_server_dry_run", return_value=0),
            mock.patch.object(
                setup_wavefoundry.venv_bootstrap,
                "ensure_python_resolves",
                return_value="ok",
            ),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        with mock.patch.object(
            memory_backfill,
            "complete_index_publication",
            side_effect=RuntimeError("checkpoint unavailable"),
        ):
            self.assertEqual(
                setup_wavefoundry.main(["--root", str(self.root)]),
                1,
            )
        self.assertEqual(index_calls, 1)
        self.assertEqual(
            setup_wavefoundry.main(["--root", str(self.root)]),
            0,
        )
        self.assertEqual(index_calls, 1)
        run_id = memory_backfill.latest_run_id(self.root, "setup")
        self.assertIsNotNone(run_id)
        self.assertEqual(
            memory_backfill.run_summary(self.root, str(run_id))["state"],
            "indexed",
        )

    def test_receipt_does_not_alias_a_later_unrelated_generation(self):
        self._wave("1aaa closed")
        batch = server_impl.wave_memory_backfill_response(
            self.root, mode="create", entry_path="setup"
        )
        candidate = memory_records.load_memory_records(self.root)[0]
        validated = server_impl.wave_memory_validate_response(
            self.root,
            candidate["memory_id"],
            "promote",
            "Reuse the local decision.",
            "The target remains current.",
            True,
            True,
            "none",
        )
        self.assertEqual(validated["status"], "ok")
        run_id = batch["data"]["run_id"]
        index_dir = self.root / ".wavefoundry" / "index"
        with memory_backfill.index_publication_scope(run_id):
            receipt_attempt = index_state_store.begin_build_epoch(index_dir, "all")
            self.assertTrue(
                index_state_store.finalize_build_epoch(index_dir, receipt_attempt)
            )
        unrelated_attempt = index_state_store.begin_build_epoch(index_dir, "code")
        self.assertTrue(
            index_state_store.finalize_build_epoch(index_dir, unrelated_attempt)
        )

        summary = memory_backfill.reconcile_index_publication(self.root, run_id)
        self.assertEqual(summary["state"], "ready_for_index")
        self.assertFalse(summary["publication_recovered"])

    def test_setup_requeues_history_changed_at_index_finalize(self):
        wave = self._wave("1aaa closed")
        (self.root / ".wavefoundry" / "framework").mkdir(parents=True)
        (self.root / "docs" / "workflow-config.json").write_text(
            '{"lifecycle_id_policy":{"scheme_version":"v2"}}\n',
            encoding="utf-8",
        )
        server_impl.wave_memory_backfill_response(
            self.root, mode="create", entry_path="setup"
        )
        candidate = memory_records.load_memory_records(self.root)[0]
        server_impl.wave_memory_validate_response(
            self.root,
            candidate["memory_id"],
            "promote",
            "Reuse the local decision.",
            "The target remains current.",
            True,
            True,
            "none",
        )

        class MutatingSetup:
            @staticmethod
            def main(argv=None):
                if argv is not None and "--deps-only" not in argv:
                    index_dir = self.root / ".wavefoundry" / "index"
                    attempt = index_state_store.begin_build_epoch(index_dir, "all")
                    wave.joinpath("wave.md").write_text(
                        wave.joinpath("wave.md").read_text(encoding="utf-8")
                        + "\nchanged during publication\n",
                        encoding="utf-8",
                    )
                    return 0 if index_state_store.finalize_build_epoch(
                        index_dir, attempt
                    ) else 1
                return 0

        with mock.patch.object(
            setup_wavefoundry, "_load_setup_index", return_value=MutatingSetup
        ), mock.patch.object(
            setup_wavefoundry, "_run_render_platform_surfaces", return_value=0
        ), mock.patch.object(
            setup_wavefoundry, "_run_mcp_server_dry_run", return_value=0
        ), mock.patch.object(
            setup_wavefoundry.venv_bootstrap,
            "ensure_python_resolves",
            return_value="ok",
        ):
            self.assertEqual(
                setup_wavefoundry.main(["--root", str(self.root)]),
                memory_backfill.ACTION_REQUIRED_EXIT,
            )
        run_id = memory_backfill.latest_run_id(self.root, "setup")
        self.assertIsNotNone(run_id)
        self.assertEqual(
            memory_backfill.run_summary(self.root, str(run_id))["state"],
            "awaiting_validation",
        )
        state = index_state_store.read_build_state(
            self.root / ".wavefoundry" / "index"
        )
        self.assertIsNotNone(state)
        self.assertNotEqual(state["status"], "complete")

    def test_setup_help_is_observational(self):
        with mock.patch.object(
            setup_wavefoundry,
            "_provision_lifecycle_policy_if_absent",
            side_effect=AssertionError("help must not provision"),
        ), mock.patch.object(
            setup_wavefoundry,
            "_run_render_platform_surfaces",
            side_effect=AssertionError("help must not render"),
        ), mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertEqual(setup_wavefoundry.main(["--help"]), 0)
        help_text = stdout.getvalue()
        self.assertIn("show this help without changing the project", help_text)
        self.assertIn(
            "gate on agent-owned historical-memory validation", help_text
        )
        self.assertIn(
            "candidate-bearing historical-memory publication", help_text
        )
        self.assertIn(
            "--background-code and --background-docs are intentionally ignored",
            help_text,
        )

    def test_setup_resume_has_no_one_purpose_public_surface(self):
        setup_source = (SCRIPTS / "setup_wavefoundry.py").read_text(encoding="utf-8")
        server_source = (SCRIPTS / "server_impl.py").read_text(encoding="utf-8")
        self.assertNotIn("wave_setup_resume_after_memory", server_source)
        self.assertNotIn("setup --resume-after-memory", setup_source)


if __name__ == "__main__":
    unittest.main()
