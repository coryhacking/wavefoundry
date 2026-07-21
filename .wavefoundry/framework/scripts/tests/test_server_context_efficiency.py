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
from types import SimpleNamespace
from unittest.mock import patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import context_efficiency as ce
import index_state_store
import review_evidence
import server_impl as srv
import score_context_efficiency_pairs as pair_scorer


RETRIEVAL_TOOLS = {
    "code_ask",
    "code_search",
    "code_lexical",
    "docs_search",
    "code_keyword",
    "code_pattern",
    "code_constants",
    "code_read",
    "code_outline",
    "code_definition",
    "code_references",
    "code_callhierarchy",
    "code_impact",
    "code_dependencies",
    "code_callgraph",
    "code_graph_path",
    "code_graph_community",
    "code_commit_provenance",
    "code_hover",
    "code_risk_score",
}
LIFECYCLE_TOOLS = {
    "wf_create_wave",
    "wf_prepare_wave",
    "wf_implement_wave",
    "wf_review_wave",
    "wf_close_wave",
}
SERIALIZED_WAVE_WRITERS = {
    "wf_create_wave",
    "wf_add_change",
    "wf_remove_change",
    "wf_prepare_wave",
    "wf_pause_wave",
    "wf_implement_wave",
    "wf_reopen_wave",
    "wf_close_wave",
    "wf_garden_docs",
}


def _repo(root: Path) -> None:
    (root / "docs" / "workflow-config.json").parent.mkdir(
        parents=True, exist_ok=True
    )
    (root / "docs" / "workflow-config.json").write_text(
        json.dumps(
            {
                "lifecycle_id_policy": {
                    "epoch_utc": "2020-01-01T00:00:00Z",
                    "hour_offset": 0,
                }
            }
        ),
        encoding="utf-8",
    )


class ContextEfficiencyServerIntegrationTests(unittest.TestCase):
    @staticmethod
    def _p95(samples: list[float]) -> float:
        ordered = sorted(samples)
        return ordered[max(0, ((95 * len(ordered) + 99) // 100) - 1)]

    def test_registered_envelope_census_is_exact(self):
        tree = ast.parse(
            (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        )
        register = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "register_mcp_surface"
        )
        nested = {
            node.name: node
            for node in register.body
            if isinstance(node, ast.FunctionDef)
        }

        wired_retrieval = set()
        wired_lifecycle = set()
        milestone_gated = set()
        serialized_writers = set()
        observational_annotations = set()
        for name, node in nested.items():
            calls = [
                call
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
            ]
            if any(
                call.func.id == "_record_retrieval_context" for call in calls
            ):
                wired_retrieval.add(name)
            if any(
                call.func.id == "_lifecycle_context_result" for call in calls
            ):
                wired_lifecycle.add(name)
            if any(
                call.func.id == "_lifecycle_milestone_completed"
                for call in calls
            ):
                milestone_gated.add(name)
            if any(
                call.func.id == "review_event_write_lock" for call in calls
            ):
                serialized_writers.add(name)
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                for keyword in decorator.keywords:
                    if (
                        keyword.arg == "annotations"
                        and isinstance(keyword.value, ast.Name)
                        and keyword.value.id == "_OBSERVATIONAL_TOOL"
                    ):
                        observational_annotations.add(name)

        self.assertEqual(wired_retrieval, RETRIEVAL_TOOLS)
        self.assertEqual(wired_lifecycle, LIFECYCLE_TOOLS)
        self.assertEqual(
            milestone_gated,
            {
                "wf_create_wave",
                "wf_prepare_wave",
                "wf_implement_wave",
                "wf_close_wave",
            },
        )
        self.assertEqual(
            serialized_writers & SERIALIZED_WAVE_WRITERS,
            SERIALIZED_WAVE_WRITERS,
        )
        self.assertEqual(
            observational_annotations,
            RETRIEVAL_TOOLS | {"wf_review_wave"},
        )

    def test_mcp_reload_evicts_context_efficiency_dependency(self):
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '{"review_evidence", "context_efficiency"}',
            source,
        )

    def test_reload_and_upgrade_both_enforce_projection_barrier(self):
        runner = (SCRIPTS_ROOT / "server.py").read_text(encoding="utf-8")
        implementation = (SCRIPTS_ROOT / "server_impl.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "projection = server_impl.project_pending_context_efficiency(_get_handler())",
            runner,
        )
        self.assertIn(
            "projection = project_pending_context_efficiency(handler)",
            implementation,
        )
        self.assertIn(
            "context_efficiency_projection_failed",
            runner,
        )
        self.assertIn(
            "context_efficiency_projection_failed",
            implementation,
        )

    def test_projection_barrier_publishes_all_pending_waves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            telemetry = ce.ProcessTelemetry(root)
            for wave_id in ("1aaaa first", "1aaab second"):
                wave_md = root / "docs" / "waves" / wave_id / "wave.md"
                wave_md.parent.mkdir(parents=True)
                wave_md.write_text(
                    f"# Wave\n\nwave-id: {wave_id}\n\noperator prose\n",
                    encoding="utf-8",
                )
                telemetry.set_focus(wave_id, "review", new_phase=True)
                telemetry.record_retrieval(
                    {
                        "estimated_request_tokens": 1,
                        "estimated_returned_tokens": 2,
                        "estimated_source_tokens": 0,
                        "estimated_avoided_tokens": 0,
                        "source_files_counted": 0,
                        "source_files_verified": 0,
                        "source_files_estimated": 0,
                        "captured": True,
                        "persistence": "pending",
                        "method": ce.RETRIEVAL_METHOD,
                    },
                    event_id=f"event-{wave_id}",
                )
            handler = SimpleNamespace(root=root, telemetry=telemetry)
            projected = srv.project_pending_context_efficiency(handler)
            self.assertTrue(projected["ok"])
            self.assertEqual(
                projected["projected"], ["1aaaa first", "1aaab second"]
            )
            for wave_id in projected["projected"]:
                wave_md = root / "docs" / "waves" / wave_id / "wave.md"
                text = wave_md.read_text(encoding="utf-8")
                self.assertIn("operator prose", text)
                self.assertIn("## Context Efficiency", text)
                self.assertFalse(
                    ce.read_wave_snapshot(root, wave_id)["pending"]
                )

    def test_public_paired_evaluation_authority_recomputes_contained_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            telemetry = ce.ProcessTelemetry(root)
            telemetry.set_focus("1wave", "review", new_phase=True)
            phase_id = telemetry.focus.phase_id
            assert phase_id is not None
            telemetry.record_retrieval(
                {
                    "estimated_request_tokens": 5,
                    "estimated_returned_tokens": 10,
                    "estimated_source_tokens": 265,
                    "estimated_avoided_tokens": 250,
                    "source_files_counted": 1,
                    "source_files_verified": 1,
                    "source_files_estimated": 0,
                    "captured": True,
                    "persistence": "pending",
                    "method": ce.RETRIEVAL_METHOD,
                    "_source_credits": [
                        {
                            "source_id": "evaluation-source",
                            "version_id": "v1",
                            "tokens": 265,
                            "classification": "verified",
                            "credit_kind": "content",
                        }
                    ],
                },
                event_id="evaluation-ledger",
            )
            applicability = {
                "wave_id": "1wave",
                "phase_id": phase_id,
                "stage": "review",
                "task_spec_digest": "task",
                "repository_snapshot_digest": "repo",
                "model_id": "model",
                "model_version": "version",
                "tool_configuration_digest": "tools",
            }
            incomplete = {
                key: value
                for key, value in applicability.items()
                if key not in {"wave_id", "phase_id", "stage"}
            }
            rejected = srv.wf_context_efficiency_eval_response(
                root,
                "1wave",
                phase_id,
                mode="register",
                applicability=incomplete,
            )
            self.assertEqual(rejected["status"], "error")
            self.assertIn("incomplete", rejected["data"]["error"])
            mismatched = dict(applicability)
            mismatched.update(
                wave_id="other-wave",
                phase_id="other-phase",
                stage="implement",
            )
            rejected = srv.wf_context_efficiency_eval_response(
                root,
                "1wave",
                phase_id,
                mode="register",
                applicability=mismatched,
            )
            self.assertEqual(rejected["status"], "error")
            self.assertIn("authoritative phase", rejected["data"]["error"])
            registered = srv.wf_context_efficiency_eval_response(
                root,
                "1wave",
                phase_id,
                mode="register",
                applicability=applicability,
            )
            self.assertEqual(registered["status"], "ok")
            pairs = []
            quality = {
                "correctness": 3,
                "completeness": 3,
                "evidence": 3,
                "maintainability": 3,
            }
            for index in range(pair_scorer.MIN_QUALIFYING_PAIRS):
                arm = {
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "tool_calls": 20,
                    "completed": True,
                    "usage_source": "provider_reported",
                    "quality_scored_blind": True,
                    "quality": quality,
                }
                assisted = dict(arm)
                assisted.update(
                    input_tokens=700, output_tokens=300, tool_calls=9
                )
                pairs.append(
                    {
                        "pair_id": f"pair-{index}",
                        "baseline": arm,
                        "assisted": assisted,
                        "assisted_direct_net": 250,
                    }
                )
            artifact = root / "evaluation.json"
            artifact.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "evaluation_id": "eval-1",
                        "supersedes_evaluation_id": None,
                        "applicability": applicability,
                        "pairs": pairs,
                    }
                ),
                encoding="utf-8",
            )
            attached = srv.wf_context_efficiency_eval_response(
                root,
                "1wave",
                phase_id,
                mode="attach",
                report_path="evaluation.json",
            )
            self.assertEqual(attached["status"], "ok")
            self.assertEqual(
                attached["data"]["scorer"]["matched_pair_residual"], 250
            )

    def test_review_evidence_tool_description_names_repeatable_terminal_states(self):
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        self.assertIn("truthful ``not_issue`` /", source)
        self.assertIn("``dont_do_later`` reclassification", source)
        self.assertIn(
            "Repeat same-cycle lane reverifications and later aggregate repair cycles",
            source,
        )

    def test_index_metadata_reader_is_one_bounded_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.sqlite"
            conn = sqlite3.connect(db)
            conn.execute(
                "CREATE TABLE build_file_meta("
                "path TEXT PRIMARY KEY, hash TEXT, mtime REAL, size INTEGER, "
                "inode INTEGER, chunks_emitted INTEGER)"
            )
            conn.executemany(
                "INSERT INTO build_file_meta VALUES(?,?,?,?,?,?)",
                [
                    ("a.py", "a", 1.0, 10, 11, 1),
                    ("b.py", "b", 2.0, 20, 22, 1),
                    ("c.py", "c", 3.0, 30, 33, 1),
                ],
            )
            conn.commit()
            conn.close()
            with patch.object(
                index_state_store,
                "open_read_only",
                side_effect=lambda _index_dir: sqlite3.connect(db),
            ):
                rows = index_state_store.read_build_file_meta(
                    Path(tmp), ["b.py", "a.py", "a.py"]
                )
            self.assertEqual(
                rows,
                {
                    "a.py": {"mtime": 1.0, "size": 10, "inode": 11},
                    "b.py": {"mtime": 2.0, "size": 20, "inode": 22},
                },
            )

    def test_retrieval_metric_is_written_through_and_visible_immediately(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            source = root / "src" / "thing.py"
            source.parent.mkdir(parents=True)
            source.write_text("answer = 42\n", encoding="utf-8")
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry(root)
            )
            core = {
                "status": "ok",
                "data": {
                    "results": [
                        {"path": "src/thing.py", "text": "answer = 42"}
                    ]
                },
            }

            result = srv._record_retrieval_context(
                handler, "code_keyword", core
            )
            state = srv._context_efficiency_state(handler, [])

            metric = result["data"]["context_avoided"]
            self.assertTrue(metric["captured"])
            self.assertEqual(metric["persistence"], "durable")
            self.assertEqual(metric["source_files_counted"], 1)
            self.assertEqual(metric["source_files_verified"], 0)
            self.assertEqual(metric["source_files_estimated"], 1)
            self.assertEqual(state["current_process"]["pending_events"], 0)
            self.assertEqual(state["durable_general"]["calls"], 1)
            self.assertTrue(ce.store_path(root).exists())

    def test_retrieval_rejections_keep_contract_without_buffering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry(root)
            )

            invalid = srv._ensure_no_extra_args(
                "code_keyword", {"unsupported": True}
            )
            rebuilding = srv._index_rebuilding_response(
                "code_search", {"query": "thing"}
            )
            assert invalid is not None
            for response in (invalid, rebuilding):
                metric = response["data"]["context_avoided"]
                self.assertFalse(metric["captured"])
                self.assertEqual(metric["persistence"], "failed")
                self.assertEqual(metric["estimated_avoided_tokens"], 0)

            ordinary_error = {
                "status": "error",
                "data": {"query": ""},
                "diagnostics": [],
            }
            result = srv._record_retrieval_context(
                handler, "code_keyword", ordinary_error
            )
            failure_metric = result["data"]["context_avoided"]
            self.assertTrue(failure_metric["captured"])
            self.assertEqual(failure_metric["persistence"], "durable")
            self.assertEqual(failure_metric["source_files_counted"], 0)
            self.assertEqual(ce.read_general_totals(root)["calls"], 1)

    def test_undurable_event_and_poison_failure_withholds_core_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            logs = root / ".wavefoundry" / "logs"
            logs.parent.mkdir(parents=True)
            logs.write_text("not a directory", encoding="utf-8")
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry(root)
            )
            result = srv._record_retrieval_context(
                handler,
                "code_keyword",
                {
                    "status": "ok",
                    "data": {"results": []},
                    "diagnostics": [],
                },
                request_arguments={"queries": ["needle"]},
            )
            self.assertEqual(result["status"], "error")
            self.assertEqual(
                result["data"]["error_code"],
                "telemetry_persistence_failed",
            )

    def test_retrieval_exception_poison_or_fatal_is_never_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            core = {
                "status": "ok",
                "data": {"results": []},
                "diagnostics": [],
            }
            telemetry = SimpleNamespace(
                record_retrieval=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    RuntimeError("forced precommit failure")
                )
            )
            handler = SimpleNamespace(root=root, telemetry=telemetry)
            with patch.object(
                srv.context_efficiency,
                "poison_accounting_gap",
                return_value=True,
            ):
                poisoned = srv._record_retrieval_context(
                    handler, "code_keyword", dict(core)
                )
            self.assertEqual(poisoned["status"], "ok")
            self.assertEqual(
                poisoned["data"]["context_avoided"]["persistence"],
                "poisoned",
            )
            with patch.object(
                srv.context_efficiency,
                "poison_accounting_gap",
                return_value=False,
            ):
                fatal = srv._record_retrieval_context(
                    handler, "code_keyword", dict(core)
                )
            self.assertEqual(fatal["status"], "error")
            self.assertEqual(
                fatal["data"]["error_code"], "telemetry_persistence_failed"
            )

    def test_retrieval_metric_builder_failure_is_poisoned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            handler = SimpleNamespace(
                root=root,
                telemetry=ce.ProcessTelemetry(root),
            )
            core = {
                "status": "ok",
                "data": {"results": []},
                "diagnostics": [],
            }
            failed_metric = srv._retrieval_failure_metric(core)
            with (
                patch.object(
                    srv.context_efficiency,
                    "retrieval_context_avoided",
                    return_value=failed_metric,
                ),
                patch.object(
                    srv.context_efficiency,
                    "poison_accounting_gap",
                    return_value=True,
                ),
            ):
                result = srv._record_retrieval_context(
                    handler, "code_keyword", core
                )
            self.assertEqual(
                result["data"]["context_avoided"]["persistence"],
                "poisoned",
            )

    def test_workflow_exception_poison_or_fatal_is_never_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa lifecycle"
            telemetry = SimpleNamespace(
                record_workflow=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    RuntimeError("forced workflow precommit failure")
                )
            )
            handler = SimpleNamespace(root=root, telemetry=telemetry)
            core = {
                "status": "ok",
                "data": {"wave_id": wave_id},
                "diagnostics": [],
            }
            with patch.object(
                srv.context_efficiency,
                "poison_accounting_gap",
                return_value=True,
            ):
                poisoned = srv._record_workflow_context(
                    handler,
                    "wf_prepare_wave",
                    wave_id,
                    dict(core),
                    milestone_completed=True,
                )
            self.assertEqual(poisoned["status"], "ok")
            self.assertEqual(
                poisoned["data"]["workflow_instruction_proxy"]["persistence"],
                "poisoned",
            )
            with patch.object(
                srv.context_efficiency,
                "poison_accounting_gap",
                return_value=False,
            ):
                fatal = srv._record_workflow_context(
                    handler,
                    "wf_prepare_wave",
                    wave_id,
                    dict(core),
                    milestone_completed=True,
                )
            self.assertEqual(fatal["status"], "error")
            self.assertEqual(
                fatal["data"]["error_code"], "telemetry_persistence_failed"
            )

    def test_workflow_metric_builder_failure_is_poisoned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            handler = SimpleNamespace(
                root=root,
                telemetry=ce.ProcessTelemetry(root),
            )
            wave_id = "1aaaa lifecycle"
            core = {
                "status": "ok",
                "data": {"wave_id": wave_id},
                "diagnostics": [],
            }
            failed_metric = srv._workflow_failure_metric(core)
            with (
                patch.object(
                    srv.context_efficiency,
                    "workflow_instruction_proxy",
                    return_value=failed_metric,
                ),
                patch.object(
                    srv.context_efficiency,
                    "poison_accounting_gap",
                    return_value=True,
                ),
            ):
                result = srv._record_workflow_context(
                    handler,
                    "wf_prepare_wave",
                    wave_id,
                    core,
                    milestone_completed=True,
                )
            self.assertEqual(
                result["data"]["workflow_instruction_proxy"]["persistence"],
                "poisoned",
            )

    def test_indexed_tool_uses_one_batched_metadata_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            source = root / "src" / "thing.py"
            source.parent.mkdir(parents=True)
            source.write_text("answer = 42\n", encoding="utf-8")
            graph_only = root / "src" / "large-neighbor.py"
            graph_only.write_text("x" * 200_000, encoding="utf-8")
            stat = source.stat()
            calls: list[list[str]] = []

            def read_meta(_index_dir: Path, paths: list[str]):
                calls.append(list(paths))
                return {
                    "src/thing.py": {
                        "mtime": stat.st_mtime,
                        "size": stat.st_size,
                        "inode": stat.st_ino,
                    }
                }

            fake_store = SimpleNamespace(read_build_file_meta=read_meta)
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry()
            )
            core = {
                "status": "ok",
                "data": {
                    "results": [
                        {"path": "src/thing.py", "text": "answer = 42"},
                        {"path": "src/thing.py", "text": "duplicate chunk"},
                    ],
                    "graph_neighbors": [
                        {
                            "source_file": "src/large-neighbor.py",
                            "label": "reference-only",
                        }
                    ],
                },
            }
            with patch.object(srv, "_load_script", return_value=fake_store):
                result = srv._record_retrieval_context(
                    handler,
                    "code_search",
                    core,
                    indexed_epoch_stable=True,
                )

            metric = result["data"]["context_avoided"]
            self.assertEqual(calls, [["src/thing.py"]])
            self.assertEqual(metric["source_files_counted"], 1)
            self.assertEqual(metric["source_files_verified"], 1)
            self.assertEqual(metric["source_files_estimated"], 0)
            self.assertLess(metric["estimated_source_tokens"], 100)

    def test_missing_indexed_source_uses_captured_size_estimate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            metadata = {
                "src/removed.py": {
                    "mtime": 1.0,
                    "size": 400,
                    "inode": 0,
                }
            }
            fake_store = SimpleNamespace(
                read_build_file_meta=lambda _index_dir, _paths: metadata
            )
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry()
            )
            core = {
                "status": "ok",
                "data": {
                    "results": [
                        {
                            "path": "src/removed.py",
                            "text": "captured indexed chunk",
                        }
                    ]
                },
            }
            with patch.object(srv, "_load_script", return_value=fake_store):
                result = srv._record_retrieval_context(
                    handler,
                    "code_search",
                    core,
                    indexed_epoch_stable=True,
                )

            metric = result["data"]["context_avoided"]
            self.assertEqual(metric["estimated_source_tokens"], 100)
            self.assertEqual(metric["source_files_counted"], 1)
            self.assertEqual(metric["source_files_verified"], 0)
            self.assertEqual(metric["source_files_estimated"], 1)
            self.assertNotIn("source_files_unavailable", metric)
            self.assertNotIn("source_files_unmeasured", metric)

    def test_content_source_census_is_explicit_and_graph_metadata_is_inert(self):
        cases = {
            "code_ask": (
                {"citations": [{"path": "a.py", "excerpt": "x"}]},
                ["a.py"],
            ),
            "code_pattern": (
                {"matches": [{"file": "b.py", "text": "match"}]},
                ["b.py"],
            ),
            "code_constants": (
                {"results": [{"file": "c.py", "value": 0}]},
                ["c.py"],
            ),
            "code_read": ({"path": "d.py", "content": ""}, ["d.py"]),
            "code_hover": (
                {"file": "hv.py", "symbol": {"name": "f", "kind": "function"}},
                ["hv.py"],
            ),
            "code_outline": (
                {"file": "e.py", "symbols": [{"name": "E"}]},
                ["e.py"],
            ),
            "code_definition": (
                {"definitions": [{"path": "f.py", "snippet": "def f"}]},
                ["f.py"],
            ),
            "code_references": (
                {"references": [{"path": "g.py", "snippet": "f()"}]},
                ["g.py"],
            ),
            "code_callhierarchy": (
                {
                    "definition_file": "metadata-only.py",
                    "context": [{"source_file": "context-only.py"}],
                    "incoming": [
                        {"file": "h.py", "snippet": "caller()"},
                        {"file": "no-snippet.py", "snippet": None},
                    ],
                },
                ["h.py"],
            ),
            "code_commit_provenance": (
                {
                    "provenance": [
                        {"path": "wave.md", "rationale": "why"},
                        {"path": "change.md", "excerpt": "decision"},
                        {"path": "empty.md", "relevance": "wave_level"},
                    ]
                },
                ["change.md", "wave.md"],
            ),
        }
        for tool_name, (data, expected) in cases.items():
            with self.subTest(tool=tool_name):
                data["graph_neighbors"] = [
                    {"source_file": "graph-only.py", "path": "also-graph.py"}
                ]
                self.assertEqual(
                    srv._context_source_paths(
                        tool_name, {"status": "ok", "data": data}
                    ),
                    expected,
                )

    def test_structural_source_census_uses_only_documented_fields(self):
        cases = {
            "code_dependencies": (
                {"path": "seed.py", "dependencies": [{"path": "ignored.py"}]},
                ["seed.py"],
            ),
            "code_impact": (
                {
                    "path": "seed.py",
                    "importers": [{"file": "importer.py"}],
                    "affected": [{"source_file": "affected.py"}],
                    "graph_neighbors": [{"source_file": "ignored.py"}],
                },
                ["affected.py", "importer.py", "seed.py"],
            ),
            "code_callgraph": (
                {
                    "nodes": [{"source_file": "caller.py"}],
                    "edges": [{"source_file": "ignored.py"}],
                },
                ["caller.py"],
            ),
            "code_graph_path": (
                {
                    "path_nodes": [{"source_file": "path.py"}],
                    "nodes": [{"source_file": "ignored.py"}],
                },
                ["path.py"],
            ),
            "code_graph_community": (
                {
                    "nodes": [{"source_file": "community.py"}],
                    "members": [{"source_file": "ignored.py"}],
                },
                ["community.py"],
            ),
            "code_risk_score": (
                {
                    "results": [
                        {"source_file": "risky.py", "score": 0.9},
                        {"source_file": "also.py", "score": 0.4},
                    ],
                    "scope": "ignored-scope",
                },
                ["also.py", "risky.py"],
            ),
        }
        for tool_name, (data, expected) in cases.items():
            with self.subTest(tool=tool_name):
                self.assertEqual(
                    srv._context_structural_paths(
                        tool_name, {"status": "ok", "data": data}
                    ),
                    expected,
                )

    def test_mutating_boundary_flushes_general_and_projects_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa context-telemetry"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            wave_md.write_text(
                "# Wave Record\n\nStatus: planned\n\n## Notes\n\nkeep-me\n",
                encoding="utf-8",
            )
            prompt = root / "docs" / "prompts" / "prepare-wave.prompt.md"
            prompt.parent.mkdir(parents=True)
            prompt.write_text("prepare instructions " * 200, encoding="utf-8")
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry(root)
            )
            handler.telemetry.record_retrieval(
                {
                    "estimated_request_tokens": 1,
                    "estimated_returned_tokens": 5,
                    "estimated_source_tokens": 105,
                    "estimated_avoided_tokens": 99,
                    "source_files_counted": 1,
                    "source_files_verified": 1,
                    "source_files_estimated": 0,
                    "captured": True,
                    "persistence": "pending",
                    "method": ce.RETRIEVAL_METHOD,
                    "_source_credits": [
                        {
                            "source_id": "general-source",
                            "version_id": "v1",
                            "tokens": 105,
                            "classification": "verified",
                            "credit_kind": "content",
                        }
                    ],
                }
            )
            core = {
                "status": "ok",
                "data": {"wave_id": wave_id, "mode": "ready"},
                "diagnostics": [],
            }

            result = srv._lifecycle_context_result(
                handler,
                "wf_prepare_wave",
                wave_id,
                core,
                focus_stage="plan",
                flush=True,
                transfer_general=True,
            )

            proxy = result["data"]["workflow_instruction_proxy"]
            self.assertTrue(proxy["credited"])
            self.assertEqual(proxy["persistence"], "durable")
            snapshot = ce.read_wave_snapshot(root, wave_id)
            self.assertEqual(
                snapshot["stages"]["plan"]["content_source_credit"], 105
            )
            # 1t3ld: the adopted general event and the prepare-tool proxy event
            # now share the single canonical `plan` stage.
            self.assertEqual(snapshot["stages"]["plan"]["calls"], 2)
            second_core = {
                "status": "ok",
                "data": {"wave_id": wave_id, "mode": "ready"},
                "diagnostics": [],
            }
            second_result = srv._lifecycle_context_result(
                handler,
                "wf_prepare_wave",
                wave_id,
                second_core,
                focus_stage="plan",
                credit=True,
                flush=True,
            )
            second_proxy = second_result["data"]["workflow_instruction_proxy"]
            self.assertTrue(second_proxy["credited"])
            self.assertNotEqual(
                second_proxy["invocation_id"], proxy["invocation_id"]
            )
            snapshot = ce.read_wave_snapshot(root, wave_id)
            self.assertEqual(snapshot["stages"]["plan"]["calls"], 3)
            rendered = wave_md.read_text(encoding="utf-8")
            self.assertIn("keep-me", rendered)
            self.assertIn("## Context Efficiency", rendered)
            self.assertNotIn("Combined savings", rendered)
            self.assertIn("| **Total** | **3** |", rendered)
            self.assertFalse(snapshot["pending"])

    def test_dry_run_and_incomplete_review_set_focus_without_credit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa lifecycle-credit"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            wave_md.write_text("# Wave\n", encoding="utf-8")
            prompt = root / "docs" / "prompts" / "prepare-wave.prompt.md"
            prompt.parent.mkdir(parents=True)
            prompt.write_text("prepare " * 100, encoding="utf-8")
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry(root)
            )
            dry = {
                "status": "dry_run",
                "data": {"wave_id": wave_id, "mode": "dry_run"},
                "diagnostics": [],
            }
            result = srv._lifecycle_context_result(
                handler,
                "wf_prepare_wave",
                wave_id,
                dry,
                focus_stage="plan",
                credit=False,
                flush=False,
            )
            self.assertEqual(handler.telemetry.focus.stage, "plan")
            proxy = result["data"]["workflow_instruction_proxy"]
            self.assertTrue(proxy["captured"])
            self.assertEqual(proxy["prompt_surface_tokens"], 0)
            self.assertEqual(proxy["persistence"], "durable")
            self.assertEqual(
                ce.read_wave_snapshot(root, wave_id)["stages"]["plan"][
                    "calls"
                ],
                1,
            )

            incomplete = {
                "status": "ok",
                "data": {
                    "phase": "implementation",
                    "lint_passed": True,
                    "lane_results": [
                        {"lane": "operator", "recorded_signoff": False}
                    ],
                    "council_results": [],
                },
            }
            complete = {
                "status": "ok",
                "data": {
                    "phase": "implementation",
                    "lint_passed": True,
                    "lane_results": [
                        {"lane": "operator", "recorded_signoff": True}
                    ],
                    "council_results": [
                        {
                            "signoff_key": "wave-council-delivery",
                            "recorded_signoff": True,
                        }
                    ],
                },
            }
            self.assertFalse(srv._implementation_review_complete(incomplete))
            self.assertTrue(srv._implementation_review_complete(complete))

    def test_failed_mutating_lifecycle_does_not_transfer_general(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa failed"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            wave_md.write_text(
                "# Wave Record\n\nStatus: planned\n", encoding="utf-8"
            )
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry(root)
            )
            handler.telemetry.record_retrieval(
                {
                    "estimated_request_tokens": 1,
                    "estimated_returned_tokens": 1,
                    "estimated_source_tokens": 10,
                    "estimated_avoided_tokens": 8,
                    "source_files_counted": 0,
                    "source_files_verified": 0,
                    "source_files_estimated": 0,
                    "captured": True,
                    "persistence": "pending",
                    "method": ce.RETRIEVAL_METHOD,
                },
                event_id="general",
            )
            failed = {
                "status": "error",
                "data": {"wave_id": wave_id, "failed": True},
                "diagnostics": [],
            }
            srv._lifecycle_context_result(
                handler,
                "wf_prepare_wave",
                wave_id,
                failed,
                focus_stage="plan",
                credit=False,
                flush=True,
                transfer_general=True,
            )
            self.assertEqual(
                ce.read_general_totals(root, handler.telemetry.producer_id)[
                    "calls"
                ],
                1,
            )
            # 1t3ld: the failed call's own proxy event lands in `plan`; the
            # unattributed general event must NOT have been transferred, so the
            # stage holds exactly one call.
            self.assertEqual(
                ce.read_wave_snapshot(root, wave_id)["stages"]["plan"]["calls"], 1
            )
            handler.telemetry.close()

    def test_incomplete_error_review_still_sets_review_focus_without_credit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa review-focus"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            wave_md.write_text("# Wave\n", encoding="utf-8")
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry(root)
            )
            response = {
                "status": "error",
                "data": {
                    "wave_id": wave_id,
                    "phase": "implementation",
                    "lane_results": [
                        {"lane": "qa-reviewer", "recorded_signoff": False}
                    ],
                },
                "diagnostics": [],
            }
            result = srv._lifecycle_context_result(
                handler,
                "wf_review_wave",
                wave_id,
                response,
                focus_stage="review",
                credit=False,
                flush=False,
            )
            self.assertEqual(handler.telemetry.focus.stage, "review")
            proxy = result["data"]["workflow_instruction_proxy"]
            self.assertEqual(proxy["prompt_surface_tokens"], 0)
            self.assertEqual(proxy["persistence"], "durable")

    def test_implementation_review_that_ran_publishes_checkpoint(self):
        """Wave 1t3ek (1t22z) AC-1/AC-2: an implementation-phase review that RAN
        (structured lane summary present) publishes the checkpoint even when its
        status is error with pending signoffs — the normal pre-close state."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa review-flush"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            wave_md.write_text(
                "# Wave Record\n\nStatus: implementing\n", encoding="utf-8"
            )
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry(root)
            )
            handler.telemetry.set_focus(wave_id, "implement", new_phase=True)
            handler.telemetry.record_retrieval(
                {
                    "estimated_request_tokens": 2,
                    "estimated_returned_tokens": 5,
                    "estimated_source_tokens": 100,
                    "estimated_avoided_tokens": 93,
                    "source_files_counted": 1,
                    "source_files_verified": 1,
                    "source_files_estimated": 0,
                    "captured": True,
                    "persistence": "pending",
                    "method": ce.RETRIEVAL_METHOD,
                    "_source_credits": [
                        {
                            "source_id": "impl-src",
                            "version_id": "v1",
                            "tokens": 100,
                            "classification": "verified",
                            "credit_kind": "content",
                        }
                    ],
                },
                event_id="impl-work",
            )
            response = {
                "status": "error",
                "data": {
                    "wave_id": wave_id,
                    "phase": "implementation",
                    "lane_results": [
                        {"lane": "operator", "recorded_signoff": False}
                    ],
                },
                "diagnostics": [],
            }
            before_events = (wave_md.parent / "events.jsonl")
            result = srv._lifecycle_context_result(
                handler,
                "wf_review_wave",
                wave_id,
                response,
                focus_stage="review",
                credit=False,
                flush=True,
            )
            rendered = wave_md.read_text(encoding="utf-8")
            self.assertIn("## Context Efficiency", rendered)
            self.assertIn("| implement |", rendered)
            self.assertEqual(
                result["data"]["context_efficiency_persistence"]["projection"],
                "published",
            )
            # AC-3: no wave-state mutation beyond the checkpoint blocks.
            self.assertIn("Status: implementing", rendered)
            self.assertFalse(before_events.exists())
            handler.telemetry.close()

    def test_review_that_could_not_run_does_not_publish(self):
        """Wave 1t3ek (1t22z) AC-2: an error response with no structured lane
        summary (review never ran) publishes nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa review-norun"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            wave_md.write_text(
                "# Wave Record\n\nStatus: implementing\n", encoding="utf-8"
            )
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry(root)
            )
            response = {
                "status": "error",
                "data": {"wave_id": wave_id},
                "diagnostics": [],
            }
            srv._lifecycle_context_result(
                handler,
                "wf_review_wave",
                wave_id,
                response,
                focus_stage="review",
                credit=False,
                flush=True,
            )
            self.assertNotIn(
                "## Context Efficiency", wave_md.read_text(encoding="utf-8")
            )
            handler.telemetry.close()

    def test_review_registration_flushes_only_implementation_phase(self):
        """Wave 1t3ek (1t22z): the wf_review_wave registration passes
        flush=is_implementation_phase — prepare-phase reviews stay
        non-publishing. Verified structurally against the registration source."""
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        idx = source.index('_ensure_no_extra_args("wf_review_wave"')
        window = source[idx : idx + 1800]
        self.assertIn("flush=is_implementation_phase", window)
        self.assertIn("transfer_general=is_implementation_phase", window)
        self.assertIn(
            'is_implementation_phase = (phase or "").strip().lower() == "implementation"',
            window,
        )

    def _posture_repo(self, tmp, *, wave_id="1aaaa posture-wave"):
        root = Path(tmp)
        _repo(root)
        wave_md = root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.parent.mkdir(parents=True)
        wave_md.write_text(
            "# Wave Record\n\nStatus: implementing\n\n"
            "## Review Evidence\n\n- operator-signoff: approved\n",
            encoding="utf-8",
        )
        return root, wave_id, wave_md

    def test_retrieval_posture_directive_is_self_contained(self):
        """Wave 1t3ek (1t230) AC-1: the activation envelope carries the rule,
        the Gapfill escape hatch, and the advisory it clears."""
        directive = srv._RETRIEVAL_POSTURE_DIRECTIVE
        self.assertIn("code_*", directive)
        self.assertIn("Gapfill:", directive)
        self.assertIn("retrieval_posture_gap", directive)
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        idx = source.index("def wf_implement_wave_response")
        self.assertIn(
            '"retrieval_posture": _RETRIEVAL_POSTURE_DIRECTIVE',
            source[idx : idx + 16000],
        )

    def test_retrieval_posture_gap_fires_on_zero_retrieval_with_footprint(self):
        """Wave 1t3ek (1t230) AC-2: zero implement-stage retrieval + non-trivial
        footprint fires the advisory at implementation review without changing
        the review status computation."""
        with tempfile.TemporaryDirectory() as tmp:
            root, wave_id, wave_md = self._posture_repo(tmp)
            telemetry = ce.ProcessTelemetry(root)
            telemetry.set_focus(wave_id, "implement", new_phase=True)
            telemetry.close()  # store exists; zero retrieval events recorded
            srv._FOOTPRINT_PROVIDER = lambda _root: 12
            try:
                with patch.object(srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                    result = srv.wf_review_wave_response(root, wave_id, phase="implementation")
            finally:
                srv._FOOTPRINT_PROVIDER = None
            codes = [d.get("code") for d in result.get("diagnostics", [])]
            self.assertIn("retrieval_posture_gap", codes)
            gap = result["data"]["retrieval_posture_gap"]
            self.assertEqual(gap["implement_stage_retrieval_calls"], 0)
            self.assertEqual(gap["changed_non_docs_files"], 12)

    def test_retrieval_posture_gap_cleared_by_gapfill_and_by_retrieval(self):
        """Wave 1t3ek (1t230) AC-3: a recorded Gapfill entry clears the advisory;
        healthy retrieval or a trivial footprint never fires it."""
        with tempfile.TemporaryDirectory() as tmp:
            root, wave_id, wave_md = self._posture_repo(tmp)
            telemetry = ce.ProcessTelemetry(root)
            telemetry.set_focus(wave_id, "implement", new_phase=True)
            telemetry.close()
            # Gapfill note clears it.
            (wave_md.parent / "notes.md").write_text(
                "## Progress Log\n\nGapfill: bulk-mechanical rename; scripted edits were the right instrument.\n",
                encoding="utf-8",
            )
            srv._FOOTPRINT_PROVIDER = lambda _root: 12
            try:
                self.assertIsNone(srv._retrieval_posture_gap(root, wave_md))
                # Trivial footprint never fires, even without the note.
                (wave_md.parent / "notes.md").unlink()
                srv._FOOTPRINT_PROVIDER = lambda _root: 2
                self.assertIsNone(srv._retrieval_posture_gap(root, wave_md))
            finally:
                srv._FOOTPRINT_PROVIDER = None

    def test_retrieval_posture_gap_silent_without_store(self):
        """Wave 1t3ek (1t230): sensor stays silent when the store is absent
        (missing data must not fire the advisory)."""
        with tempfile.TemporaryDirectory() as tmp:
            root, wave_id, wave_md = self._posture_repo(tmp)
            srv._FOOTPRINT_PROVIDER = lambda _root: 50
            try:
                self.assertIsNone(srv._retrieval_posture_gap(root, wave_md))
            finally:
                srv._FOOTPRINT_PROVIDER = None

    def test_retrieval_posture_thresholds_configurable(self):
        """Wave 1t3ek (1t230) AC-5: workflow-config sensors.retrieval_posture
        overrides the conservative defaults."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            self.assertEqual(srv._retrieval_posture_thresholds(root), (0, 5))
            cfg_path = root / "docs" / "workflow-config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg["sensors"] = {"retrieval_posture": {"max_retrieval_calls": 2, "min_changed_files": 10}}
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            self.assertEqual(srv._retrieval_posture_thresholds(root), (2, 10))

    def test_implementation_review_reports_implement_stage_telemetry(self):
        """Wave 1t3ek (1t230) AC-4: the implementation-phase review response
        carries the implement-stage totals and retrieval-call count."""
        with tempfile.TemporaryDirectory() as tmp:
            root, wave_id, wave_md = self._posture_repo(tmp)
            telemetry = ce.ProcessTelemetry(root)
            telemetry.set_focus(wave_id, "implement", new_phase=True)
            telemetry.record_retrieval(
                {
                    "estimated_request_tokens": 3,
                    "estimated_returned_tokens": 7,
                    "estimated_source_tokens": 90,
                    "estimated_avoided_tokens": 80,
                    "source_files_counted": 1,
                    "source_files_verified": 1,
                    "source_files_estimated": 0,
                    "captured": True,
                    "persistence": "pending",
                    "method": ce.RETRIEVAL_METHOD,
                    "_source_credits": [
                        {
                            "source_id": "posture-src",
                            "version_id": "v1",
                            "tokens": 90,
                            "classification": "verified",
                            "credit_kind": "content",
                        }
                    ],
                },
                event_id="posture-work",
            )
            telemetry.close()
            srv._FOOTPRINT_PROVIDER = lambda _root: 12
            try:
                with patch.object(srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                    result = srv.wf_review_wave_response(root, wave_id, phase="implementation")
            finally:
                srv._FOOTPRINT_PROVIDER = None
            summary = result["data"]["implement_stage_telemetry"]
            self.assertEqual(summary["retrieval_calls"], 1)
            self.assertEqual(summary["stage_totals"].get("calls"), 1)
            codes = [d.get("code") for d in result.get("diagnostics", [])]
            self.assertNotIn("retrieval_posture_gap", codes)

    def _wrapped_registry(self, root, tool_name, fn):
        """Install fn into a fake FastMCP registry and run the 1t3s7 cost
        wrapping pass against it."""
        class _Tool:
            pass
        class _TM:
            pass
        class _MCP:
            pass
        tool = _Tool(); tool.fn = fn
        tm = _TM(); tm._tools = {tool_name: tool}
        mcp = _MCP(); mcp._tool_manager = tm
        handler = SimpleNamespace(root=root, telemetry=ce.ProcessTelemetry(root))
        srv._wrap_first_party_tool_costs(mcp, lambda: handler)
        return tool.fn, handler

    def test_review_evidence_artifact_credit_and_replay_dedup(self):
        """Wave 1t3ek (1t3s7) AC-1/AC-2: a create-mode wf_review_evidence result
        credits the derived persisted records minus the caller request, and an
        identical replay derives nothing new."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            records = [{"record_type": "executable_evidence", "request_digest": "d1", "derived": "x" * 400}]
            canned = {"status": "ok", "data": {"mode": "create", "replayed": False, "appended_records": records}}
            def fake_tool(wave_id="1aaaa w", kwargs=None):
                return canned
            wrapped, handler = self._wrapped_registry(root, "wf_review_evidence", fake_tool)
            wrapped(wave_id="1aaaa w")
            wrapped(wave_id="1aaaa w")  # replay: same artifact event id
            handler.telemetry.close()
            conn = sqlite3.connect(ce.store_path(root))
            rows = conn.execute(
                "SELECT event_id, derived_artifact_tokens, request_tokens FROM telemetry_event "
                "WHERE tool_name='wf_review_evidence'"
            ).fetchall()
            conn.close()
            self.assertEqual(len(rows), 1)
            event_id, artifact, request = rows[0]
            self.assertEqual(event_id, "artifact:d1")
            expected_records = ce.estimate_tokens_utf8(json.dumps(records, sort_keys=True, default=str))
            self.assertEqual(artifact, max(0, expected_records - request))
            self.assertGreater(artifact, 0)

    def test_uninstrumented_tool_records_debit_only(self):
        """Wave 1t3ek (1t3s7) AC-3: a tool without an extractor records
        request/response debits and zero credit."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            def fake_tool(kwargs=None):
                return {"status": "ok", "data": {"passed": True}}
            wrapped, handler = self._wrapped_registry(root, "wf_validate_docs", fake_tool)
            wrapped()
            handler.telemetry.close()
            conn = sqlite3.connect(ce.store_path(root))
            row = conn.execute(
                "SELECT derived_artifact_tokens, response_tokens FROM telemetry_event "
                "WHERE tool_name='wf_validate_docs'"
            ).fetchone()
            conn.close()
            self.assertEqual(row[0], 0)
            self.assertGreater(row[1], 0)

    def test_scaffold_artifact_credit_without_prompt_double_count(self):
        """Wave 1t3ek (1t3s7) AC-4: a wf_new_* result credits the generated
        document body with no workflow prompt credit involved."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            doc = root / "docs" / "plans" / "1x-bug sample.md"
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text("y" * 800, encoding="utf-8")
            def fake_tool(slug="sample", kwargs=None):
                return {"status": "ok", "data": {"path": "docs/plans/1x-bug sample.md"}}
            wrapped, handler = self._wrapped_registry(root, "wf_new_bug", fake_tool)
            wrapped(slug="sample")
            handler.telemetry.close()
            conn = sqlite3.connect(ce.store_path(root))
            row = conn.execute(
                "SELECT derived_artifact_tokens, workflow_prompt_tokens FROM telemetry_event "
                "WHERE tool_name='wf_new_bug'"
            ).fetchone()
            conn.close()
            self.assertGreater(row[0], 150)
            self.assertEqual(row[1], 0)

    def test_lifecycle_and_retrieval_tools_are_exempt_from_wrapping(self):
        """Wave 1t3ek (1t3s7): already-instrumented tools keep their original
        functions (no double accounting)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            def fake_tool(kwargs=None):
                return {"status": "ok", "data": {}}
            wrapped, handler = self._wrapped_registry(root, "wf_close_wave", fake_tool)
            self.assertIs(wrapped, fake_tool)
            wrapped2, handler2 = self._wrapped_registry(root, "code_read", fake_tool)
            self.assertIs(wrapped2, fake_tool)
            # 1t15a: newly native-instrumented code tools joined the exempt set.
            wrapped3, handler3 = self._wrapped_registry(root, "code_hover", fake_tool)
            self.assertIs(wrapped3, fake_tool)
            wrapped4, handler4 = self._wrapped_registry(root, "code_risk_score", fake_tool)
            self.assertIs(wrapped4, fake_tool)
            handler.telemetry.close(); handler2.telemetry.close()
            handler3.telemetry.close(); handler4.telemetry.close()

    def test_review_evidence_state_file_source_credit_with_dedup(self):
        """Wave 1t3ek (1t2zq) AC-1/AC-2: a committed create credits the ledger
        and wave record as verified content sources, once per file version; a
        grown ledger earns a fresh credit."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa credit-wave"
            wave_dir = root / "docs" / "waves" / wave_id
            wave_dir.mkdir(parents=True)
            (wave_dir / "wave.md").write_text("# Wave\n\nStatus: implementing\n" + "w" * 400, encoding="utf-8")
            events = wave_dir / "events.jsonl"
            events.write_text('{"seed": 1}\n' + "e" * 400 + "\n", encoding="utf-8")
            canned = {"status": "ok", "data": {
                "mode": "create", "replayed": False,
                "appended_records": [{"request_digest": "s1", "body": "x" * 200}],
                "events_path": f"docs/waves/{wave_id}/events.jsonl",
                "path": f"docs/waves/{wave_id}/wave.md",
            }}
            calls = {"n": 0}
            def fake_tool(wave_id="w", kwargs=None):
                calls["n"] += 1
                out = json.loads(json.dumps(canned))
                out["data"]["appended_records"][0]["request_digest"] = f"s{calls['n']}"
                return out
            wrapped, handler = self._wrapped_registry(root, "wf_review_evidence", fake_tool)
            handler.telemetry.set_focus(wave_id, "review", new_phase=True)
            wrapped(wave_id=wave_id)
            # Second call, files unchanged: source credits dedupe to zero new rows.
            wrapped(wave_id=wave_id)
            # Ledger grows: a new version earns a fresh credit.
            events.write_text(events.read_text(encoding="utf-8") + "g" * 800 + "\n", encoding="utf-8")
            wrapped(wave_id=wave_id)
            handler.telemetry.close()
            conn = sqlite3.connect(ce.store_path(root))
            rows = conn.execute(
                "SELECT source_id, version_id, tokens, credit_kind FROM source_credit "
                "WHERE wave_key=? ORDER BY tokens",
                (wave_id,),
            ).fetchall()
            conn.close()
            # wave.md once + events.jsonl v1 once + events.jsonl v2 once = 3 rows,
            # with two distinct versions sharing the ledger's source_id.
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(r[3] == "content" for r in rows))
            by_source = {}
            for source_id, version_id, tokens, _ in rows:
                by_source.setdefault(source_id, set()).add(version_id)
            self.assertEqual(sorted(len(v) for v in by_source.values()), [1, 2])

    def test_no_read_tools_credit_no_sources(self):
        """Wave 1t3ek (1t2zq) AC-3/AC-4: memory_add and wf_new_* credit no
        sources; unresolvable paths credit nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            def add_tool(kwargs=None):
                return {"status": "ok", "data": {"written": True, "record": {"path": "/outside/etc/passwd"}}}
            wrapped, handler = self._wrapped_registry(root, "memory_add", add_tool)
            wrapped()
            def validate_tool(kwargs=None):
                return {"status": "ok", "data": {"record": {"path": "../escape.md"}}}
            wrapped2, handler2 = self._wrapped_registry(root, "memory_validate", validate_tool)
            wrapped2()
            handler.telemetry.close(); handler2.telemetry.close()
            conn = sqlite3.connect(ce.store_path(root))
            count = conn.execute("SELECT COUNT(*) FROM source_credit").fetchone()[0]
            conn.close()
            self.assertEqual(count, 0)

    def test_code_hover_census_matches_canonical_producer(self):
        """Wave 1t3ek (1t15a, live-caught): the hover envelope names its file
        under "file", not "path" — the census must credit the canonical
        builder's real output, not a hand-modeled shape."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "mod.py"
            src.write_text("def f():\n    \"\"\"doc\"\"\"\n    return 1\n", encoding="utf-8")
            response = srv.code_hover_response(root, "mod.py", 1)
            self.assertEqual(response.get("status"), "ok")
            self.assertEqual(
                srv._context_source_paths("code_hover", response), ["mod.py"]
            )

    def test_get_change_credits_only_conveyed_content(self):
        """Wave 1t3ek (1t15a) AC-2: wf_get_change credits exactly the change
        docs whose content the response conveys — the single-change doc and
        untruncated bulk rows — never truncated or content-less rows, and a
        replay with unchanged files dedupes to zero new credits."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa get-change"
            plans = root / "docs" / "plans"
            plans.mkdir(parents=True, exist_ok=True)
            (plans / "1x1-enh full.md").write_text("f" * 600, encoding="utf-8")
            (plans / "1x2-enh capped.md").write_text("c" * 600, encoding="utf-8")
            (plans / "1x3-enh bare.md").write_text("b" * 600, encoding="utf-8")
            canned = {"status": "ok", "data": {
                "change": {"change_id": "1x1", "path": "docs/plans/1x1-enh full.md", "content": "f" * 600},
                "changes": [
                    {"id": "1x2", "path": "docs/plans/1x2-enh capped.md", "content": "c" * 100, "truncated": True},
                    {"id": "1x3", "path": "docs/plans/1x3-enh bare.md", "content": None, "truncated": False},
                ],
            }}
            def fake_tool(change_id="1x1", kwargs=None):
                return json.loads(json.dumps(canned))
            wrapped, handler = self._wrapped_registry(root, "wf_get_change", fake_tool)
            handler.telemetry.set_focus(wave_id, "implement", new_phase=True)
            wrapped(change_id="1x1")
            wrapped(change_id="1x1")  # unchanged files: dedup, no new rows
            handler.telemetry.close()
            conn = sqlite3.connect(ce.store_path(root))
            rows = conn.execute(
                "SELECT source_id, credit_kind FROM source_credit WHERE wave_key=?",
                (wave_id,),
            ).fetchall()
            conn.close()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][1], "content")

    def test_wave_listings_credit_live_working_set_only(self):
        """Wave 1t3ek (1t15a, operator-directed middle ground): wave listings
        credit exactly the non-closed rows they enumerate — the live working
        set — never the closed-history tail, so credit is bounded by work in
        flight rather than repository age."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            live_dir = root / "docs" / "waves" / "1aaaa live"
            live_dir.mkdir(parents=True)
            (live_dir / "wave.md").write_text("Status: active\n" + "w" * 900, encoding="utf-8")
            closed_dir = root / "docs" / "waves" / "1aaab closed"
            closed_dir.mkdir(parents=True)
            (closed_dir / "wave.md").write_text("Status: closed\n" + "z" * 900, encoding="utf-8")
            wave_id = "1aaaa listing-credit"
            def fake_tool(kwargs=None):
                return {"status": "ok", "data": {"waves": [
                    {"wave_id": "1aaaa", "status": "active",
                     "path": "docs/waves/1aaaa live/wave.md"},
                    {"wave_id": "1aaab", "status": "closed",
                     "path": "docs/waves/1aaab closed/wave.md"},
                ], "total": 2, "has_more": False}}
            wrapped, handler = self._wrapped_registry(root, "wf_list_waves", fake_tool)
            handler.telemetry.set_focus(wave_id, "plan", new_phase=True)
            wrapped()
            wrapped()  # unchanged files: once-only dedup, no new rows
            handler.telemetry.close()
            conn = sqlite3.connect(ce.store_path(root))
            rows = conn.execute(
                "SELECT COUNT(*) FROM source_credit WHERE wave_key=?",
                (wave_id,),
            ).fetchone()
            conn.close()
            self.assertEqual(rows[0], 1)  # the live wave only, once

    def test_map_credits_resolved_doc_only_when_it_exists(self):
        """Wave 1t3ek (1t15a): wf_map credits exactly its one resolved existing
        document; an unresolved address credits nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            doc = root / "docs" / "README.md"
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text("d" * 800, encoding="utf-8")
            def fake_map(address="doc:docs/README.md", kwargs=None):
                return {"status": "ok", "data": {
                    "address": address, "path": "docs/README.md",
                    "file_exists": True, "excerpt": "d" * 100,
                }}
            wrapped, handler = self._wrapped_registry(root, "wf_map", fake_map)
            handler.telemetry.set_focus("1aaaa map-credit", "plan", new_phase=True)
            wrapped()
            def fake_missing(address="doc:docs/none.md", kwargs=None):
                return {"status": "ok", "data": {
                    "address": address, "path": "docs/none.md",
                    "file_exists": False, "excerpt": "",
                }}
            wrapped2, handler2 = self._wrapped_registry(root, "wf_map", fake_missing)
            handler2.telemetry.set_focus("1aaaa map-credit", "plan")
            wrapped2()
            handler.telemetry.close(); handler2.telemetry.close()
            conn = sqlite3.connect(ce.store_path(root))
            count = conn.execute(
                "SELECT COUNT(*) FROM source_credit WHERE wave_key='1aaaa map-credit'"
            ).fetchone()[0]
            conn.close()
            self.assertEqual(count, 1)  # the resolved doc only

    def test_memory_views_credit_surfaced_record_files(self):
        """Wave 1t3ek (1t15a, operator-directed): memory views credit the
        record files they surface — an agent without the tool would open each
        surfaced record — with the once-only dedup intact."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            mem_dir = root / "docs" / "memory"
            mem_dir.mkdir(parents=True, exist_ok=True)
            (mem_dir / "mem-a.md").write_text("a" * 700, encoding="utf-8")
            (mem_dir / "mem-b.md").write_text("b" * 700, encoding="utf-8")
            wave_id = "1aaaa memory-views"
            def fake_brief(kwargs=None):
                return {"status": "ok", "data": {"advisories": [
                    {"memory_id": "mem-a", "path": "docs/memory/mem-a.md"},
                ], "community_scoped": [
                    {"memory_id": "mem-b", "path": "docs/memory/mem-b.md"},
                ], "count": 2}}
            wrapped, handler = self._wrapped_registry(root, "memory_brief", fake_brief)
            handler.telemetry.set_focus(wave_id, "implement", new_phase=True)
            wrapped()
            wrapped()  # unchanged records: dedup, no new rows
            handler.telemetry.close()
            conn = sqlite3.connect(ce.store_path(root))
            count = conn.execute(
                "SELECT COUNT(*) FROM source_credit WHERE wave_key=?",
                (wave_id,),
            ).fetchone()[0]
            conn.close()
            self.assertEqual(count, 2)  # both surfaced records, once each

    def test_memory_backfill_artifact_credit(self):
        """Wave 1t3ek (1t15a) AC-3: memory_backfill credits the written record
        files as derived artifacts through the shared written-paths extractor."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            rec = root / "docs" / "memory" / "mem-1a.md"
            rec.parent.mkdir(parents=True, exist_ok=True)
            rec.write_text("m" * 900, encoding="utf-8")
            def fake_tool(kwargs=None):
                return {"status": "ok", "data": {"written": [
                    {"memory_id": "mem-1a", "path": "docs/memory/mem-1a.md"},
                ]}}
            wrapped, handler = self._wrapped_registry(root, "memory_backfill", fake_tool)
            wrapped()
            handler.telemetry.close()
            conn = sqlite3.connect(ce.store_path(root))
            row = conn.execute(
                "SELECT derived_artifact_tokens FROM telemetry_event "
                "WHERE tool_name='memory_backfill'"
            ).fetchone()
            conn.close()
            self.assertGreater(row[0], 150)

    def test_artifact_credit_floors_per_artifact_not_aggregate(self):
        """Operator review 2026-07-20 (P1): the 1t3s7 contract floors credit at
        zero PER ARTIFACT — a request larger than each individual output must
        credit nothing even when the outputs sum higher."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            plans = root / "docs" / "plans"
            plans.mkdir(parents=True, exist_ok=True)
            (plans / "a.md").write_text("a" * 400, encoding="utf-8")  # 100 tokens
            (plans / "b.md").write_text("b" * 400, encoding="utf-8")  # 100 tokens
            # Request serializes to > 100 tokens but < 200 combined.
            big_arg = "x" * 600
            def fake_tool(payload=big_arg, kwargs=None):
                return {"status": "ok", "data": {"written": [
                    "docs/plans/a.md", "docs/plans/b.md",
                ]}}
            wrapped, handler = self._wrapped_registry(root, "memory_backfill", fake_tool)
            wrapped(payload=big_arg)
            handler.telemetry.close()
            conn = sqlite3.connect(ce.store_path(root))
            row = conn.execute(
                "SELECT derived_artifact_tokens, request_tokens FROM telemetry_event "
                "WHERE tool_name='memory_backfill'"
            ).fetchone()
            conn.close()
            self.assertGreater(row[1], 100)
            self.assertLess(row[1], 200)
            self.assertEqual(row[0], 0)  # per-artifact floor: 0 + 0, not sum-request

    def test_artifact_replay_without_operation_digest_dedupes(self):
        """Operator review 2026-07-20 (P1): artifact tools without their own
        operation digest get a stable request+response identity — an identical
        replay records once, while a different outcome records its debits."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            rec = root / "docs" / "memory" / "mem-r.md"
            rec.parent.mkdir(parents=True, exist_ok=True)
            rec.write_text("m" * 900, encoding="utf-8")
            written = {"status": "ok", "data": {"written": [
                {"memory_id": "mem-r", "path": "docs/memory/mem-r.md"},
            ]}}
            empty = {"status": "ok", "data": {"written": []}}
            responses = [written, written, empty]
            def fake_tool(kwargs=None):
                return json.loads(json.dumps(responses.pop(0)))
            wrapped, handler = self._wrapped_registry(root, "memory_backfill", fake_tool)
            wrapped()  # first write: credited
            wrapped()  # identical replay: same event id, no second row
            wrapped()  # idempotent second run wrote nothing: new row, zero credit
            handler.telemetry.close()
            conn = sqlite3.connect(ce.store_path(root))
            rows = conn.execute(
                "SELECT derived_artifact_tokens FROM telemetry_event "
                "WHERE tool_name='memory_backfill' ORDER BY derived_artifact_tokens DESC"
            ).fetchall()
            conn.close()
            self.assertEqual(len(rows), 2)
            self.assertGreater(rows[0][0], 150)
            self.assertEqual(rows[1][0], 0)

    def test_risk_score_registration_records_complete_request_arguments(self):
        """Operator review 2026-07-20 (P2): the recorded request must reflect
        the actual invocation — layer and include_tests included."""
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        start = source.index('def code_risk_score(')
        window = source[start:start + 8000]
        for arg in ('"scope": scope', '"top": top', '"max_hops": max_hops',
                    '"layer": layer', '"include_tests": include_tests'):
            self.assertIn(arg, window)

    def test_pending_projection_reports_corrupt_authority_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            telemetry = ce.ProcessTelemetry(root)
            telemetry.set_focus("1aaaa corrupt", "review")
            telemetry.record_retrieval(
                {
                    "estimated_request_tokens": 1,
                    "estimated_returned_tokens": 1,
                    "estimated_source_tokens": 0,
                    "estimated_avoided_tokens": 0,
                    "source_files_counted": 0,
                    "source_files_verified": 0,
                    "source_files_estimated": 0,
                    "captured": True,
                    "persistence": "pending",
                    "method": ce.RETRIEVAL_METHOD,
                },
                event_id="seed",
            )
            conn = sqlite3.connect(ce.store_path(root))
            conn.execute("DROP TABLE wave_state")
            conn.commit()
            conn.close()
            result = srv.project_pending_context_efficiency(
                SimpleNamespace(root=root, telemetry=telemetry)
            )
            self.assertFalse(result["ok"])
            self.assertEqual(
                result["detail"]["projection"], "unavailable"
            )
            self.assertIn("wave_state", result["detail"]["error"])

    def test_wedged_focus_does_not_change_successful_lifecycle_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa wedged-focus"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            wave_md.write_text("# Wave\n", encoding="utf-8")

            def fail_focus(*_args, **_kwargs):
                raise RuntimeError("forced focus failure")

            handler = SimpleNamespace(
                root=root,
                telemetry=SimpleNamespace(set_focus=fail_focus),
            )
            core = {
                "status": "ok",
                "data": {"wave_id": wave_id, "mode": "ready"},
                "diagnostics": [],
            }
            result = srv._lifecycle_context_result(
                handler,
                "wf_prepare_wave",
                wave_id,
                core,
                focus_stage="plan",
                credit=False,
                flush=False,
            )
            self.assertIs(result, core)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["data"]["wave_id"], wave_id)
            proxy = result["data"]["workflow_instruction_proxy"]
            self.assertFalse(proxy["captured"])
            self.assertEqual(proxy["persistence"], "poisoned")

    def test_wedged_buffer_operations_do_not_change_public_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa wedged-buffer"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            wave_md.write_text("# Wave\n", encoding="utf-8")

            def fail(*_args, **_kwargs):
                raise RuntimeError("forced telemetry failure")

            telemetry = SimpleNamespace(
                buffered_snapshot=fail,
                pause_focus=fail,
                reopen_focus=fail,
            )
            handler = SimpleNamespace(root=root, cache={}, telemetry=telemetry)
            state = srv._context_efficiency_state(handler, [wave_id])
            self.assertFalse(state["current_process"]["available"])
            self.assertEqual(state["current_process"]["persistence"], "failed")

            class FakeMcp:
                def __init__(self):
                    self.tools = {}

                def tool(self, **_kwargs):
                    def register(fn):
                        self.tools[fn.__name__] = fn
                        return fn

                    return register

                def resource(self, *_args, **_kwargs):
                    def register(fn):
                        return fn

                    return register

            mcp = FakeMcp()
            srv.register_mcp_surface(mcp, lambda: handler)
            pause_core = {
                "status": "ok",
                "data": {"wave_id": wave_id, "paused": True},
                "diagnostics": [],
            }
            reopen_core = {
                "status": "ok",
                "data": {"wave_id": wave_id, "reopened": True},
                "diagnostics": [],
            }
            failed_projection = ({"persistence": "failed"}, None)
            with (
                patch.object(srv, "wf_pause_wave_response", return_value=pause_core),
                patch.object(srv, "wf_reopen_wave_response", return_value=reopen_core),
                patch.object(
                    srv,
                    "_flush_context_efficiency",
                    return_value=failed_projection,
                ),
            ):
                paused = mcp.tools["wf_pause_wave"](wave_id, mode="create")
                reopened = mcp.tools["wf_reopen_wave"](wave_id)
            self.assertIs(paused, pause_core)
            self.assertIs(reopened, reopen_core)
            self.assertEqual(
                paused["data"]["context_efficiency_persistence"],
                {"persistence": "failed"},
            )
            self.assertEqual(
                reopened["data"]["context_efficiency_persistence"],
                {"persistence": "failed"},
            )

    def test_lifecycle_credit_requires_a_new_milestone_not_a_noop_retry(self):
        cases = [
            ("wf_create_wave", {"created": True}, True, True),
            ("wf_create_wave", {"created": False}, True, False),
            (
                "wf_prepare_wave",
                {"mode": "create", "transitioned_to_active": True},
                True,
                True,
            ),
            (
                "wf_prepare_wave",
                {"mode": "create", "transitioned_to_active": False},
                True,
                False,
            ),
            (
                "wf_prepare_wave",
                {"mode": "ready", "readied": True},
                True,
                True,
            ),
            (
                "wf_implement_wave",
                {"transitioned_to_implementing": True},
                True,
                True,
            ),
            (
                "wf_implement_wave",
                {
                    "already_implementing": True,
                    "transitioned_to_implementing": False,
                },
                True,
                False,
            ),
            (
                "wf_close_wave",
                {"updated": True, "transitioned_to_closed": True},
                True,
                True,
            ),
            (
                "wf_close_wave",
                {"updated": False, "transitioned_to_closed": False},
                True,
                False,
            ),
            (
                "wf_implement_wave",
                {"transitioned_to_implementing": True},
                False,
                False,
            ),
        ]
        for tool_name, data, mutating, expected in cases:
            with self.subTest(tool=tool_name, data=data, mutating=mutating):
                self.assertEqual(
                    srv._lifecycle_milestone_completed(
                        tool_name,
                        {"status": "ok", "data": data},
                        mutating=mutating,
                    ),
                    expected,
                )

        self.assertFalse(
            srv._lifecycle_milestone_completed(
                "wf_close_wave",
                {
                    "status": "error",
                    "data": {"transitioned_to_closed": True},
                },
                mutating=True,
            )
        )

    def test_corrupt_sidecar_reports_failed_health_not_authoritative_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa corrupt"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            checkpoint = ce.empty_checkpoint(wave_id)
            checkpoint["generation"] = 7
            wave_md.write_text(
                ce.replace_checkpoint_block("# Wave\n", checkpoint),
                encoding="utf-8",
            )
            sidecar = ce.store_path(root)
            sidecar.parent.mkdir(parents=True)
            sidecar.write_bytes(b"not sqlite")
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry()
            )

            state = srv._context_efficiency_state(handler, [wave_id])

            self.assertEqual(
                state["persistence_health"]["status"], "failed"
            )
            self.assertIsNotNone(
                state["persistence_health"]["diagnostic"]
            )
            self.assertEqual(
                state["durable_source"], "published_checkpoint_floor"
            )
            self.assertFalse(state["durable_general_available"])
            self.assertEqual(
                state["durable_waves"][wave_id]["generation"], 7
            )

    def test_mutating_garden_waits_for_shared_writer_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            entered = threading.Event()
            completed = threading.Event()

            def fake_garden(_root: Path) -> dict:
                entered.set()
                return {
                    "passed": True,
                    "files_updated": 0,
                    "updated": [],
                    "output": "",
                }

            def invoke() -> None:
                srv.wf_garden_docs_response(root, mode="run")
                completed.set()

            with patch.object(srv, "run_garden", side_effect=fake_garden):
                with review_evidence.review_event_write_lock(root):
                    thread = threading.Thread(target=invoke)
                    thread.start()
                    self.assertFalse(entered.wait(0.1))
                self.assertTrue(completed.wait(2.0))
                thread.join(timeout=2.0)
                self.assertFalse(thread.is_alive())

    def test_two_process_projection_preserves_both_deltas_and_prose(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa concurrent"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            wave_md.write_text(
                "# Wave Record\n\nStatus: active\n\n## Notes\n\nkeep-me\n",
                encoding="utf-8",
            )
            script = """
import sys
from pathlib import Path
from types import SimpleNamespace
import context_efficiency as ce
import server_impl as srv
root = Path(sys.argv[1])
wave = sys.argv[2]
handler = SimpleNamespace(root=root, telemetry=ce.ProcessTelemetry(root))
handler.telemetry.set_focus(wave, "implement")
handler.telemetry.record_retrieval({
    "estimated_request_tokens": 1,
    "estimated_returned_tokens": 1,
    "estimated_source_tokens": 11,
    "estimated_avoided_tokens": 9,
    "source_files_counted": 1,
    "source_files_verified": 1,
    "source_files_estimated": 0,
    "captured": True,
    "persistence": "pending",
    "method": ce.RETRIEVAL_METHOD,
    "_source_credits": [{
        "source_id": "shared-source",
        "version_id": "v1",
        "tokens": 11,
        "classification": "verified",
        "credit_kind": "content",
    }],
})
projection, flushed = srv._flush_context_efficiency(handler, wave)
if flushed is None or not flushed.success:
    print(projection, file=sys.stderr)
    raise SystemExit(2)
"""
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["PYTHONPATH"] = str(SCRIPTS_ROOT)
            children = [
                subprocess.Popen(
                    [sys.executable, "-c", script, str(root), wave_id],
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for _ in range(2)
            ]
            for child in children:
                stdout, stderr = child.communicate(timeout=30)
                self.assertEqual(child.returncode, 0, stdout + stderr)

            snapshot = ce.read_wave_snapshot(root, wave_id)
            stage = snapshot["stages"]["implement"]
            self.assertEqual(stage["calls"], 2)
            self.assertEqual(stage["content_source_credit"], 22)
            self.assertEqual(stage["estimated_tokens_saved"], 18)
            parsed = ce.parse_checkpoint_block(
                wave_md.read_text(encoding="utf-8")
            )
            self.assertIsNotNone(parsed)
            self.assertEqual(
                parsed["stages"]["implement"]["calls"], 2
            )
            self.assertIn(
                "keep-me", wave_md.read_text(encoding="utf-8")
            )

    def test_wf_review_wave_source_is_read_only(self):
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        fn = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "wf_review_wave_response"
        )
        segment = ast.get_source_segment(source, fn) or ""
        self.assertNotIn(
            "_trigger_background_index_refresh_for_paths", segment
        )
        self.assertIn("persist_adoption=False", segment)

    def test_shared_wave_writer_lock_is_same_thread_reentrant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            with review_evidence.review_event_write_lock(root):
                with review_evidence.review_event_write_lock(root):
                    marker = root / "inside-lock"
                    marker.write_text("ok", encoding="utf-8")
            self.assertEqual(marker.read_text(encoding="utf-8"), "ok")

    def test_repeated_warm_estimator_and_projection_budgets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            proofs: list[ce.SourceProof] = []
            for index in range(50):
                source = root / "src" / f"f{index}.py"
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("x" * 256, encoding="utf-8")
                stat = source.stat()
                proofs.append(
                    ce.indexed_source_proof(
                        source,
                        ce.FileVersion.from_index_meta(
                            {
                                "mtime": stat.st_mtime,
                                "size": stat.st_size,
                                "inode": stat.st_ino,
                            }
                        ),
                        epoch_stable=True,
                    )
                )
            core = {"status": "ok", "data": {"results": []}}

            for count, budget_ms in ((10, 10.0), (50, 25.0)):
                ce.retrieval_context_avoided(core, root, proofs[:count])
                samples: list[float] = []
                for _ in range(40):
                    started = time.perf_counter()
                    ce.retrieval_context_avoided(
                        core, root, proofs[:count]
                    )
                    samples.append((time.perf_counter() - started) * 1000)
                p95 = self._p95(samples)
                self.assertLessEqual(
                    p95,
                    budget_ms,
                    f"{count}-source warm p95 {p95:.3f}ms",
                )

            wave_id = "1aaaa performance"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            wave_md.write_text(
                "# Wave Record\n\nStatus: active\n", encoding="utf-8"
            )
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry(root)
            )
            flush_samples: list[float] = []
            for _ in range(30):
                handler.telemetry.set_focus(wave_id, "implement")
                handler.telemetry.record_retrieval(
                    {
                        "estimated_request_tokens": 1,
                        "estimated_returned_tokens": 1,
                        "estimated_source_tokens": 2,
                        "estimated_avoided_tokens": 0,
                        "source_files_counted": 1,
                        "source_files_verified": 1,
                        "source_files_estimated": 0,
                        "captured": True,
                        "persistence": "pending",
                        "method": ce.RETRIEVAL_METHOD,
                    }
                )
                started = time.perf_counter()
                projection, flushed = srv._flush_context_efficiency(
                    handler, wave_id
                )
                flush_samples.append(
                    (time.perf_counter() - started) * 1000
                )
                self.assertIsNotNone(flushed)
                self.assertEqual(projection["persistence"], "durable")
            flush_p95 = self._p95(flush_samples[5:])
            self.assertLessEqual(
                flush_p95,
                25.0,
                f"lifecycle flush/projection warm p95 {flush_p95:.3f}ms",
            )

    def test_closed_projection_seals_compacts_and_clears_process_focus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa closed"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            wave_md.write_text(
                "# Wave Record\n\nStatus: closed\n", encoding="utf-8"
            )
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry(root)
            )
            handler.telemetry.set_focus(wave_id, "review", new_phase=True)
            handler.telemetry.record_retrieval(
                {
                    "estimated_request_tokens": 1,
                    "estimated_returned_tokens": 1,
                    "estimated_source_tokens": 0,
                    "estimated_avoided_tokens": 0,
                    "source_files_counted": 0,
                    "source_files_verified": 0,
                    "source_files_estimated": 0,
                    "captured": True,
                    "persistence": "pending",
                    "method": ce.RETRIEVAL_METHOD,
                },
                event_id="close-event",
            )
            projection, flushed = srv._flush_context_efficiency(
                handler, wave_id
            )
            self.assertIsNotNone(flushed)
            self.assertEqual(projection["projection"], "published")
            self.assertTrue(projection["sealed"])
            self.assertTrue(projection["compacted"])
            self.assertIsNone(handler.telemetry.focus.wave_id)
            conn = sqlite3.connect(ce.store_path(root))
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM telemetry_event WHERE wave_id=?",
                    (wave_id,),
                ).fetchone()[0],
                0,
            )
            conn.close()
            handler.telemetry.close()

    def test_failed_close_compaction_stays_pending_and_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_id = "1aaaa retry"
            wave_md = root / "docs" / "waves" / wave_id / "wave.md"
            wave_md.parent.mkdir(parents=True)
            wave_md.write_text(
                "# Wave Record\n\nStatus: closed\n", encoding="utf-8"
            )
            handler = SimpleNamespace(
                root=root, telemetry=ce.ProcessTelemetry(root)
            )
            handler.telemetry.set_focus(wave_id, "review", new_phase=True)
            handler.telemetry.record_retrieval(
                {
                    "estimated_request_tokens": 1,
                    "estimated_returned_tokens": 1,
                    "estimated_source_tokens": 0,
                    "estimated_avoided_tokens": 0,
                    "source_files_counted": 0,
                    "source_files_verified": 0,
                    "source_files_estimated": 0,
                    "captured": True,
                    "persistence": "pending",
                    "method": ce.RETRIEVAL_METHOD,
                },
                event_id="close-event",
            )
            with patch.object(
                srv.context_efficiency,
                "compact_published_wave",
                return_value=False,
            ):
                first, _ = srv._flush_context_efficiency(handler, wave_id)
            self.assertEqual(first["projection"], "pending")
            self.assertIn(wave_id, ce.pending_wave_ids(root)["pending"])
            second, _ = srv._flush_context_efficiency(handler, wave_id)
            self.assertEqual(second["projection"], "published")
            self.assertTrue(second["compacted"])
            self.assertNotIn(wave_id, ce.pending_wave_ids(root)["pending"])
            handler.telemetry.close()


if __name__ == "__main__":
    unittest.main()
