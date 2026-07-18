"""Executable contract tests for context-efficiency telemetry (wave 1stwj)."""

from __future__ import annotations

import ast
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import context_efficiency as ce  # noqa: E402
import score_context_efficiency_pairs as scorer  # noqa: E402


class TempRootTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def child_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(SCRIPTS_DIR)
        return env


def _metric(
    *,
    source_id: str = "source-a",
    version_id: str = "version-a",
    source_tokens: int = 100,
    request_tokens: int = 5,
    response_tokens: int = 10,
    kind: str = "content",
) -> dict[str, object]:
    return {
        "estimated_request_tokens": request_tokens,
        "estimated_returned_tokens": response_tokens,
        "estimated_source_tokens": source_tokens,
        "estimated_avoided_tokens": max(
            0, source_tokens - request_tokens - response_tokens
        ),
        "source_files_counted": 1,
        "source_files_verified": 1,
        "source_files_estimated": 0,
        "captured": True,
        "persistence": "pending",
        "method": ce.RETRIEVAL_METHOD,
        "_source_credits": [
            {
                "source_id": source_id,
                "version_id": version_id,
                "tokens": source_tokens,
                "classification": "verified",
                "credit_kind": kind,
            }
        ],
    }


def _quality(value: int = 3) -> dict[str, int]:
    return {
        "correctness": value,
        "completeness": value,
        "evidence": value,
        "maintainability": value,
    }


def _artifact(
    applicability: dict[str, str],
    *,
    evaluation_id: str = "eval-1",
    supersedes: str | None = None,
    assisted_quality: int = 3,
) -> dict[str, object]:
    pairs = []
    for index in range(5):
        pairs.append(
            {
                "pair_id": f"pair-{index}",
                "baseline": {
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "tool_calls": 20,
                    "completed": True,
                    "usage_source": "provider_reported",
                    "quality_scored_blind": True,
                    "quality": _quality(3),
                },
                "assisted": {
                    "input_tokens": 700,
                    "output_tokens": 300,
                    "tool_calls": 9,
                    "completed": True,
                    "usage_source": "provider_reported",
                    "quality_scored_blind": True,
                    "quality": _quality(assisted_quality),
                },
                "assisted_direct_net": 250,
            }
        )
    return {
        "schema_version": 1,
        "evaluation_id": evaluation_id,
        "supersedes_evaluation_id": supersedes,
        "applicability": applicability,
        "pairs": pairs,
    }


class EstimatorAndProofTests(TempRootTest):
    def test_utf8_estimator_is_deterministic(self) -> None:
        self.assertEqual(ce.estimate_tokens_utf8(""), 0)
        self.assertEqual(ce.estimate_tokens_utf8("abcde"), 2)
        self.assertEqual(ce.estimate_tokens_utf8("😀a"), 2)
        self.assertEqual(
            ce.canonical_core_json({"z": "😀", "a": 1}),
            '{"a":1,"z":"😀"}',
        )

    def test_proofs_return_opaque_phase_credit_candidates(self) -> None:
        source = self.root / "src.py"
        source.write_text("x" * 80, encoding="utf-8")
        version = ce.contained_stat_signature(self.root, source)
        assert version is not None
        measured = ce.measure_source_proofs(
            self.root,
            [
                ce.indexed_source_proof(
                    source, version, epoch_stable=True
                ),
                ce.SourceProof(
                    source,
                    "indexed",
                    version,
                    epoch_stable=True,
                    credit_kind="structural",
                ),
            ],
        )
        self.assertEqual(measured.estimated_source_tokens, 20)
        self.assertEqual(measured.source_files_verified, 1)
        self.assertEqual(len(measured.candidates), 1)
        candidate = measured.candidates[0]
        self.assertEqual(candidate.credit_kind, "structural")
        self.assertNotIn("src.py", candidate.source_id)

    def test_retrieval_ledger_includes_request_and_complete_response(self) -> None:
        source = self.root / "large.md"
        source.write_text("a" * 400, encoding="utf-8")
        version = ce.contained_stat_signature(self.root, source)
        assert version is not None
        response = {"results": [{"path": "large.md", "text": "small"}]}
        request = {"query": "small"}
        metric = ce.retrieval_context_avoided(
            response,
            self.root,
            [
                ce.indexed_source_proof(
                    source, version, epoch_stable=True
                )
            ],
            request_arguments=request,
        )
        self.assertEqual(
            metric["estimated_avoided_tokens"],
            100
            - ce.estimate_tokens_utf8(ce.canonical_core_json(request))
            - ce.estimate_tokens_utf8(ce.canonical_core_json(response)),
        )

    def test_workflow_noop_keeps_debits_but_gets_no_prompt_credit(self) -> None:
        prompt = self.root / ce.LIFECYCLE_PROMPT_MAP["wave_prepare"]
        prompt.parent.mkdir(parents=True)
        prompt.write_text("p" * 200, encoding="utf-8")
        noop = ce.workflow_instruction_proxy(
            {"status": "ready"},
            self.root,
            "wave_prepare",
            request_arguments={"mode": "dry_run"},
            milestone_completed=False,
        )
        completed = ce.workflow_instruction_proxy(
            {"status": "ready"},
            self.root,
            "wave_prepare",
            request_arguments={"mode": "ready"},
            milestone_completed=True,
        )
        self.assertTrue(noop["captured"])
        self.assertGreater(noop["estimated_request_tokens"], 0)
        self.assertGreater(noop["estimated_returned_tokens"], 0)
        self.assertEqual(noop["prompt_surface_tokens"], 0)
        self.assertEqual(completed["prompt_surface_tokens"], 50)


class WriteThroughLedgerTests(TempRootTest):
    def test_public_telemetry_definitions_are_unique(self) -> None:
        tree = ast.parse(
            (SCRIPTS_DIR / "context_efficiency.py").read_text(encoding="utf-8")
        )
        names = [
            node.name
            for node in tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            )
        ]
        duplicates = sorted(
            {name for name in names if names.count(name) > 1}
        )
        self.assertEqual(duplicates, [])

    def test_recognized_pre_release_store_is_reset_not_migrated(self) -> None:
        path = ce.store_path(self.root)
        path.parent.mkdir(parents=True)
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE aggregate(secret_payload TEXT)")
        conn.execute("INSERT INTO aggregate VALUES('do-not-retain')")
        conn.execute("CREATE TABLE abandoned_extension(value TEXT)")
        conn.execute("INSERT INTO abandoned_extension VALUES('also-drop')")
        conn.execute("PRAGMA user_version=1")
        conn.commit()
        conn.close()

        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("1wave", "review")
        result = telemetry.record_retrieval(_metric(), event_id="first-shipped")
        self.assertEqual(result["persistence"], "durable")

        conn = sqlite3.connect(path)
        tables = {
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        }
        self.assertEqual(
            tables,
            {
                "meta",
                "phase_state",
                "telemetry_event",
                "source_credit",
                "wave_state",
                "evaluation_scope",
                "evaluation_attachment",
            },
        )
        self.assertEqual(
            int(conn.execute("PRAGMA user_version").fetchone()[0]),
            ce.STORE_SCHEMA_VERSION,
        )
        conn.close()

    def test_construction_and_reads_do_not_create_store(self) -> None:
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.buffered_snapshot()
        ce.read_wave_snapshot(self.root, "1wave")
        ce.read_general_totals(self.root)
        self.assertFalse(ce.store_path(self.root).exists())

    def test_write_through_closed_ledger_and_event_replay(self) -> None:
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("1wave", "implement", new_phase=True)
        first = telemetry.record_retrieval(
            _metric(), tool_name="code_ask", event_id="event-1"
        )
        replay = telemetry.record_retrieval(
            _metric(), tool_name="code_ask", event_id="event-1"
        )
        snapshot = ce.read_wave_snapshot(self.root, "1wave")
        stage = snapshot["stages"]["implement"]
        self.assertEqual(first["persistence"], "durable")
        self.assertEqual(replay["persistence"], "duplicate")
        self.assertEqual(stage["calls"], 1)
        self.assertEqual(stage["content_source_credit"], 100)
        self.assertEqual(stage["request_debit"], 5)
        self.assertEqual(stage["response_debit"], 10)
        self.assertEqual(stage["direct_net"], 85)
        self.assertEqual(stage["estimated_tokens_saved"], 85)

    def test_source_is_credited_once_across_content_and_structural_paths(self) -> None:
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("1wave", "review", new_phase=True)
        telemetry.record_retrieval(
            _metric(kind="content"), tool_name="code_read", event_id="content"
        )
        telemetry.record_retrieval(
            _metric(kind="structural"),
            tool_name="code_callgraph",
            event_id="structural",
        )
        stage = ce.read_wave_snapshot(self.root, "1wave")["stages"]["review"]
        self.assertEqual(stage["source_credit_count"], 1)
        self.assertEqual(
            stage["content_source_credit"] + stage["structural_source_credit"],
            100,
        )
        self.assertEqual(stage["calls"], 2)
        self.assertEqual(stage["direct_net"], 70)

    def test_same_source_recredits_in_new_phase_and_new_version(self) -> None:
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("1wave", "implement", new_phase=True)
        first_phase = telemetry.focus.phase_id
        telemetry.record_retrieval(_metric(), event_id="a")
        telemetry.set_focus("1wave", "implement", new_phase=True)
        self.assertNotEqual(first_phase, telemetry.focus.phase_id)
        telemetry.record_retrieval(_metric(), event_id="b")
        telemetry.record_retrieval(
            _metric(version_id="version-b"), event_id="c"
        )
        stage = ce.read_wave_snapshot(self.root, "1wave")["stages"]["implement"]
        self.assertEqual(stage["source_credit_count"], 3)
        self.assertEqual(stage["content_source_credit"], 300)

    def test_two_processes_share_event_and_source_uniqueness(self) -> None:
        script = r"""
import sys
from pathlib import Path
import context_efficiency as ce
root = Path(sys.argv[1])
t = ce.ProcessTelemetry(root)
t.set_focus("1wave", "review")
t.record_retrieval({
    "estimated_request_tokens": 5,
    "estimated_returned_tokens": 10,
    "estimated_source_tokens": 100,
    "estimated_avoided_tokens": 85,
    "source_files_counted": 1,
    "source_files_verified": 1,
    "source_files_estimated": 0,
    "captured": True,
    "persistence": "pending",
    "method": ce.RETRIEVAL_METHOD,
    "_source_credits": [{
        "source_id": "source-a", "version_id": "version-a",
        "tokens": 100, "classification": "verified",
        "credit_kind": "content"
    }],
}, event_id="shared-event")
"""
        children = [
            subprocess.Popen(
                [sys.executable, "-c", script, str(self.root)],
                env=self.child_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(2)
        ]
        for child in children:
            stdout, stderr = child.communicate(timeout=20)
            self.assertEqual(child.returncode, 0, stdout + stderr)
        stage = ce.read_wave_snapshot(self.root, "1wave")["stages"]["review"]
        self.assertEqual(stage["calls"], 1)
        self.assertEqual(stage["source_credit_count"], 1)

    def test_failed_transaction_poison_suppresses_positive_projection(self) -> None:
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("1wave", "implement")
        ce.store_path(self.root).unlink()
        ce.store_path(self.root).mkdir()
        result = telemetry.record_retrieval(_metric(), event_id="failure")
        self.assertEqual(result["persistence"], "poisoned")
        self.assertTrue(ce.gap_path(self.root).exists())
        self.assertEqual(
            ce.read_store_health(self.root)["status"], "accounting_gap"
        )

    def test_gap_sentinel_suppresses_existing_positive_wave_and_general_totals(self) -> None:
        wave = ce.ProcessTelemetry(self.root)
        wave.set_focus("1wave", "review")
        wave.record_retrieval(_metric(), event_id="wave")
        general = ce.ProcessTelemetry(self.root)
        general.record_retrieval(_metric(), event_id="general")
        self.assertGreater(
            ce.read_wave_snapshot(self.root, "1wave")["totals"][
                "estimated_tokens_saved"
            ],
            0,
        )
        self.assertGreater(
            ce.read_general_totals(self.root)["estimated_tokens_saved"], 0
        )
        self.assertTrue(ce._write_gap_sentinel(self.root))
        snapshot = ce.read_wave_snapshot(self.root, "1wave")
        self.assertEqual(snapshot["measurement_status"], "accounting_gap")
        self.assertEqual(snapshot["totals"]["estimated_tokens_saved"], 0)
        self.assertEqual(
            ce.read_general_totals(self.root)["estimated_tokens_saved"], 0
        )

    def test_source_cap_reports_dropped_credit_while_retaining_debits(self) -> None:
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("1wave", "review")
        metric = _metric()
        metric["_source_credits"].append(
            {
                "source_id": "source-b",
                "version_id": "version-b",
                "tokens": 200,
                "classification": "verified",
                "credit_kind": "content",
            }
        )
        with patch.object(ce, "MAX_PHASE_SOURCE_CREDITS", 1):
            public = telemetry.record_retrieval(metric, event_id="capped")
        self.assertEqual(public["source_files_credited"], 1)
        self.assertEqual(public["source_credits_dropped"], 1)
        stage = ce.read_wave_snapshot(self.root, "1wave")["stages"]["review"]
        self.assertEqual(stage["source_credit_count"], 1)
        self.assertEqual(stage["source_credit_drop_count"], 1)
        self.assertEqual(stage["request_debit"], 5)
        self.assertEqual(stage["response_debit"], 10)

    def test_source_cap_promotes_existing_provenance_without_false_drop(self) -> None:
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("1wave", "review")
        telemetry.record_retrieval(
            _metric(kind="content"), event_id="content"
        )
        with patch.object(ce, "MAX_PHASE_SOURCE_CREDITS", 1):
            public = telemetry.record_retrieval(
                _metric(kind="structural"), event_id="structural"
            )
        self.assertEqual(public["source_credits_dropped"], 0)
        conn = sqlite3.connect(ce.store_path(self.root))
        row = conn.execute(
            "SELECT credit_kind,provenance FROM source_credit"
        ).fetchone()
        conn.close()
        self.assertEqual(row, ("content", "both"))

    def test_wave_total_applies_nonnegative_floor_once_across_stages(self) -> None:
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("1wave", "prepare", new_phase=True)
        telemetry.record_retrieval(
            _metric(
                source_id="none",
                source_tokens=0,
                request_tokens=100,
                response_tokens=0,
            ),
            event_id="negative",
        )
        telemetry.set_focus("1wave", "review", new_phase=True)
        telemetry.record_retrieval(
            _metric(
                source_id="positive",
                source_tokens=300,
                request_tokens=100,
                response_tokens=0,
            ),
            event_id="positive",
        )
        snapshot = ce.read_wave_snapshot(self.root, "1wave")
        self.assertEqual(
            snapshot["stages"]["prepare"]["estimated_tokens_saved"], 0
        )
        self.assertEqual(
            snapshot["stages"]["review"]["estimated_tokens_saved"], 200
        )
        self.assertEqual(snapshot["totals"]["direct_net"], 100)
        self.assertEqual(snapshot["totals"]["estimated_tokens_saved"], 100)

    def test_double_persistence_failure_is_explicitly_fatal(self) -> None:
        logs = self.root / ".wavefoundry" / "logs"
        logs.parent.mkdir(parents=True)
        logs.write_text("not a directory", encoding="utf-8")
        telemetry = ce.ProcessTelemetry(self.root)
        public = telemetry.record_retrieval(_metric(), event_id="fatal")
        self.assertEqual(public["persistence"], "failed")
        self.assertTrue(public["fatal_persistence_failure"])

    def test_candidate_scale_p95_budgets(self) -> None:
        budgets = ((10, 10.0), (50, 25.0), (1_000, 75.0), (10_000, 250.0))
        for count, budget_ms in budgets:
            with self.subTest(count=count):
                telemetry = ce.ProcessTelemetry(self.root)
                candidates = [
                    {
                        "source_id": f"source-{count}-{index}",
                        "version_id": "v1",
                        "tokens": 1,
                        "classification": "verified",
                        "credit_kind": "content",
                    }
                    for index in range(count)
                ]
                samples: list[float] = []
                for sample in range(6):
                    telemetry.set_focus(
                        f"1wave-{count}", "review", new_phase=True
                    )
                    metric = _metric(
                        source_tokens=count,
                        request_tokens=0,
                        response_tokens=0,
                    )
                    metric["_source_credits"] = candidates
                    started = time.perf_counter()
                    public = telemetry.record_retrieval(
                        metric, event_id=f"{count}-{sample}"
                    )
                    samples.append((time.perf_counter() - started) * 1000)
                    self.assertEqual(public["persistence"], "durable")
                p95 = sorted(samples[1:])[-1]
                self.assertLessEqual(
                    p95,
                    budget_ms,
                    f"{count}-candidate warm p95 {p95:.3f}ms",
                )

    def test_competing_writer_fails_closed_within_one_second(self) -> None:
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("1wave", "review")
        blocker = sqlite3.connect(ce.store_path(self.root), timeout=0)
        blocker.execute("BEGIN IMMEDIATE")
        try:
            started = time.perf_counter()
            public = telemetry.record_retrieval(
                _metric(), event_id="contended"
            )
            elapsed = time.perf_counter() - started
        finally:
            blocker.rollback()
            blocker.close()
        self.assertEqual(public["persistence"], "poisoned")
        self.assertLess(elapsed, 1.0)

    def test_pending_wave_census_fails_closed_on_missing_state_table(self) -> None:
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("1wave", "review")
        telemetry.record_retrieval(_metric(), event_id="seed")
        conn = sqlite3.connect(ce.store_path(self.root))
        conn.execute("DROP TABLE wave_state")
        conn.commit()
        conn.close()
        result = ce.pending_wave_ids(self.root)
        self.assertFalse(result["ok"])
        self.assertEqual(result["pending"], [])
        self.assertIn("wave_state", result["error"])


class CheckpointTests(TempRootTest):
    def sample(self) -> dict[str, object]:
        stage = {
            "calls": 2,
            "content_source_credit": 100,
            "structural_source_credit": 0,
            "workflow_prompt_credit": 20,
            "request_debit": 10,
            "response_debit": 20,
            "matched_pair_residual": 30,
            "paired_evaluation_count": 1,
            "direct_net": 90,
            "estimated_tokens_saved": 120,
            "source_credit_count": 1,
            "source_credit_drop_count": 0,
        }
        return {
            "schema_version": ce.STORE_SCHEMA_VERSION,
            "wave_id": "1wave",
            "generation": 7,
            "pending": False,
            "store_instance_id": "store-a",
            "measurement_status": "healthy",
            "stages": {"review": stage},
            "totals": dict(stage),
        }

    def test_single_owned_block_round_trips_and_preserves_prose(self) -> None:
        block = ce.render_checkpoint_block(self.sample())
        self.assertIn("| review | 2 | 120 |", block)
        self.assertNotIn("Retrieval tools", block)
        self.assertEqual(ce.parse_checkpoint_block(block), self.sample())
        original = "# Wave\n\nOperator prose.\n"
        inserted = ce.replace_checkpoint_block(original, self.sample())
        self.assertIn("Operator prose.", inserted)
        self.assertEqual(inserted.count(ce.CONTEXT_EFFICIENCY_MARKER_BEGIN), 1)

    def test_malformed_and_tampered_blocks_fail_closed(self) -> None:
        canonical = ce.render_checkpoint_block(self.sample())
        cases = [
            canonical + "\n" + canonical,
            canonical.replace(ce.CONTEXT_EFFICIENCY_MARKER_END, ""),
            canonical.replace("| review | 2 | 120 |", "| review | 9 | 999 |"),
            canonical.replace(
                ce.CONTEXT_EFFICIENCY_MARKER_END,
                canonical[
                    canonical.index("<!-- wave:context-efficiency-state ") :
                    canonical.index(" -->", canonical.index("<!-- wave:context-efficiency-state "))
                    + 4
                ]
                + "\n"
                + ce.CONTEXT_EFFICIENCY_MARKER_END,
            ),
        ]
        for text in cases:
            with self.subTest(text=text[:60]):
                self.assertTrue(ce.checkpoint_validation_errors(text))
                self.assertIsNone(ce.parse_checkpoint_block(text))

    def test_store_identity_mismatch_freezes_credit_history(self) -> None:
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("1wave", "implement")
        telemetry.record_retrieval(_metric(), event_id="a")
        published = ce.read_wave_snapshot(self.root, "1wave")
        ce.store_path(self.root).unlink()
        self.assertFalse(
            ce.reconcile_checkpoint_authority(self.root, "1wave", published)
        )
        current = ce.read_wave_snapshot(self.root, "1wave")
        self.assertEqual(
            current["measurement_status"], "credit_history_unavailable"
        )
        self.assertEqual(current["totals"]["estimated_tokens_saved"], 0)


class PairedEvaluationTests(TempRootTest):
    def setUp(self) -> None:
        super().setUp()
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("1wave", "review", new_phase=True)
        telemetry.record_retrieval(
            _metric(source_tokens=265), event_id="seed"
        )
        self.phase_id = telemetry.focus.phase_id
        assert self.phase_id is not None
        self.applicability = {
            "wave_id": "1wave",
            "phase_id": self.phase_id,
            "stage": "review",
            "task_spec_digest": "task",
            "repository_snapshot_digest": "repo",
            "model_id": "model",
            "model_version": "version",
            "tool_configuration_digest": "tools",
        }

    def test_scorer_requires_five_quality_equivalent_pairs(self) -> None:
        report = scorer.score_pairs(_artifact(self.applicability))
        self.assertTrue(report["quality_gate_passed"])
        self.assertEqual(report["matched_pair_residual"], 250)
        weak = _artifact(self.applicability, assisted_quality=2)
        weak_report = scorer.score_pairs(weak)
        self.assertFalse(weak_report["quality_gate_passed"])
        self.assertEqual(weak_report["matched_pair_residual"], 0)
        short = _artifact(self.applicability)
        short["pairs"] = short["pairs"][:4]
        self.assertEqual(
            scorer.score_pairs(short)["matched_pair_residual"], 0
        )
        empty = _artifact(self.applicability)
        empty["pairs"] = []
        with self.assertRaisesRegex(ValueError, "non-empty"):
            scorer.score_pairs(empty)
        blank_supersedes = _artifact(self.applicability)
        blank_supersedes["supersedes_evaluation_id"] = ""
        with self.assertRaisesRegex(ValueError, "non-empty"):
            scorer.score_pairs(blank_supersedes)

    def test_attachment_rejects_underpowered_or_wrong_ledger_report(self) -> None:
        ce.attach_evaluation(
            self.root,
            "1wave",
            self.phase_id,
            mode="register",
            applicability=self.applicability,
        )
        short = _artifact(self.applicability)
        short["pairs"] = short["pairs"][:4]
        with self.assertRaisesRegex(ValueError, "five-pair"):
            ce.attach_evaluation(
                self.root,
                "1wave",
                self.phase_id,
                mode="attach",
                report=scorer.score_pairs(short),
            )
        wrong = scorer.score_pairs(_artifact(self.applicability))
        wrong["pairs"][0]["assisted_direct_net"] = 249
        with self.assertRaisesRegex(ValueError, "authoritative phase ledger"):
            ce.attach_evaluation(
                self.root,
                "1wave",
                self.phase_id,
                mode="attach",
                report=wrong,
            )

    def test_registration_requires_exact_authoritative_applicability_key(self) -> None:
        incomplete = {
            key: value
            for key, value in self.applicability.items()
            if key not in {"wave_id", "phase_id", "stage"}
        }
        with self.assertRaisesRegex(ValueError, "incomplete"):
            ce.attach_evaluation(
                self.root,
                "1wave",
                self.phase_id,
                mode="register",
                applicability=incomplete,
            )
        mismatched = dict(self.applicability)
        mismatched.update(
            wave_id="other-wave",
            phase_id="other-phase",
            stage="implement",
        )
        with self.assertRaisesRegex(ValueError, "authoritative phase"):
            ce.attach_evaluation(
                self.root,
                "1wave",
                self.phase_id,
                mode="register",
                applicability=mismatched,
            )

    def test_pair_schema_matches_runtime_nonempty_contract(self) -> None:
        schema = json.loads(
            (
                SCRIPTS_DIR.parent
                / "evals"
                / "context-efficiency-pairs.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(schema["properties"]["pairs"]["minItems"], 1)
        self.assertEqual(
            schema["properties"]["supersedes_evaluation_id"]["minLength"],
            1,
        )

    def test_register_attach_replay_replace_and_revoke(self) -> None:
        registered = ce.attach_evaluation(
            self.root,
            "1wave",
            self.phase_id,
            mode="register",
            applicability=self.applicability,
        )
        self.assertTrue(registered["registered"])
        first = scorer.score_pairs(_artifact(self.applicability))
        attached = ce.attach_evaluation(
            self.root,
            "1wave",
            self.phase_id,
            mode="attach",
            report=first,
        )
        self.assertTrue(attached["attached"])
        replay = ce.attach_evaluation(
            self.root,
            "1wave",
            self.phase_id,
            mode="attach",
            report=first,
        )
        self.assertTrue(replay["replayed"])
        replacement = scorer.score_pairs(
            _artifact(
                self.applicability,
                evaluation_id="eval-2",
                supersedes="eval-1",
            )
        )
        ce.attach_evaluation(
            self.root,
            "1wave",
            self.phase_id,
            mode="replace",
            report=replacement,
        )
        stage = ce.read_wave_snapshot(self.root, "1wave")["stages"]["review"]
        self.assertEqual(stage["matched_pair_residual"], 250)
        self.assertEqual(stage["paired_evaluation_count"], 1)
        revoked = ce.attach_evaluation(
            self.root, "1wave", self.phase_id, mode="revoke"
        )
        self.assertTrue(revoked["revoked"])
        stage = ce.read_wave_snapshot(self.root, "1wave")["stages"]["review"]
        self.assertEqual(stage["matched_pair_residual"], 0)
        self.assertEqual(stage["paired_evaluation_count"], 0)

    def test_evaluation_only_stage_is_included_in_snapshot(self) -> None:
        telemetry = ce.ProcessTelemetry(self.root)
        telemetry.set_focus("empty-wave", "implement", new_phase=True)
        phase_id = telemetry.focus.phase_id
        assert phase_id is not None
        applicability = {
            "wave_id": "empty-wave",
            "phase_id": phase_id,
            "stage": "implement",
            "task_spec_digest": "task-empty",
            "repository_snapshot_digest": "repo-empty",
            "model_id": "model",
            "model_version": "version",
            "tool_configuration_digest": "tools",
        }
        ce.attach_evaluation(
            self.root,
            "empty-wave",
            phase_id,
            mode="register",
            applicability=applicability,
        )
        artifact = _artifact(applicability, evaluation_id="evaluation-only")
        for pair in artifact["pairs"]:
            pair["assisted_direct_net"] = 0
        report = scorer.score_pairs(artifact)
        self.assertGreater(report["matched_pair_residual"], 0)
        ce.attach_evaluation(
            self.root,
            "empty-wave",
            phase_id,
            mode="attach",
            report=report,
        )

        snapshot = ce.read_wave_snapshot(self.root, "empty-wave")
        stage = snapshot["stages"]["implement"]
        self.assertEqual(
            stage["matched_pair_residual"],
            report["matched_pair_residual"],
        )
        self.assertEqual(stage["paired_evaluation_count"], 1)
        self.assertEqual(
            snapshot["totals"]["estimated_tokens_saved"],
            report["matched_pair_residual"],
        )

    def test_concurrent_attachment_is_single_active_and_replay_safe(self) -> None:
        ce.attach_evaluation(
            self.root,
            "1wave",
            self.phase_id,
            mode="register",
            applicability=self.applicability,
        )
        report = scorer.score_pairs(_artifact(self.applicability))
        barrier = threading.Barrier(8)
        results: list[dict[str, object]] = []
        errors: list[BaseException] = []
        lock = threading.Lock()

        def attach() -> None:
            try:
                barrier.wait(timeout=5)
                result = ce.attach_evaluation(
                    self.root,
                    "1wave",
                    self.phase_id,
                    mode="attach",
                    report=report,
                )
                with lock:
                    results.append(result)
            except BaseException as exc:  # pragma: no cover - asserted below
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=attach) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(errors)
        self.assertEqual(len(results), 8)
        self.assertEqual(
            sum(result.get("attached") is True for result in results), 1
        )
        self.assertEqual(
            sum(result.get("replayed") is True for result in results), 7
        )
        stage = ce.read_wave_snapshot(self.root, "1wave")["stages"]["review"]
        self.assertEqual(stage["matched_pair_residual"], 250)


if __name__ == "__main__":
    unittest.main()
