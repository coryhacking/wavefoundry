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
}
LIFECYCLE_TOOLS = {
    "wave_create_wave",
    "wave_prepare",
    "wave_implement",
    "wave_review",
    "wave_close",
}
SERIALIZED_WAVE_WRITERS = {
    "wave_create_wave",
    "wave_add_change",
    "wave_remove_change",
    "wave_prepare",
    "wave_pause",
    "wave_implement",
    "wave_reopen",
    "wave_close",
    "wave_garden",
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
                "wave_create_wave",
                "wave_prepare",
                "wave_implement",
                "wave_close",
            },
        )
        self.assertEqual(
            serialized_writers & SERIALIZED_WAVE_WRITERS,
            SERIALIZED_WAVE_WRITERS,
        )
        self.assertEqual(
            observational_annotations,
            RETRIEVAL_TOOLS | {"wave_review"},
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
            rejected = srv.wave_context_efficiency_attach_evaluation_response(
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
            rejected = srv.wave_context_efficiency_attach_evaluation_response(
                root,
                "1wave",
                phase_id,
                mode="register",
                applicability=mismatched,
            )
            self.assertEqual(rejected["status"], "error")
            self.assertIn("authoritative phase", rejected["data"]["error"])
            registered = srv.wave_context_efficiency_attach_evaluation_response(
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
            attached = srv.wave_context_efficiency_attach_evaluation_response(
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
                    "wave_prepare",
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
                    "wave_prepare",
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
                    "wave_prepare",
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
                "wave_prepare",
                wave_id,
                core,
                focus_stage="prepare",
                flush=True,
                transfer_general=True,
            )

            proxy = result["data"]["workflow_instruction_proxy"]
            self.assertTrue(proxy["credited"])
            self.assertEqual(proxy["persistence"], "durable")
            snapshot = ce.read_wave_snapshot(root, wave_id)
            self.assertEqual(
                snapshot["stages"]["pre-wave"]["content_source_credit"], 105
            )
            self.assertEqual(snapshot["stages"]["pre-wave"]["calls"], 1)
            self.assertEqual(snapshot["stages"]["prepare"]["calls"], 1)
            second_core = {
                "status": "ok",
                "data": {"wave_id": wave_id, "mode": "ready"},
                "diagnostics": [],
            }
            second_result = srv._lifecycle_context_result(
                handler,
                "wave_prepare",
                wave_id,
                second_core,
                focus_stage="prepare",
                credit=True,
                flush=True,
            )
            second_proxy = second_result["data"]["workflow_instruction_proxy"]
            self.assertTrue(second_proxy["credited"])
            self.assertNotEqual(
                second_proxy["invocation_id"], proxy["invocation_id"]
            )
            snapshot = ce.read_wave_snapshot(root, wave_id)
            self.assertEqual(snapshot["stages"]["prepare"]["calls"], 2)
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
                "wave_prepare",
                wave_id,
                dry,
                focus_stage="prepare",
                credit=False,
                flush=False,
            )
            self.assertEqual(handler.telemetry.focus.stage, "prepare")
            proxy = result["data"]["workflow_instruction_proxy"]
            self.assertTrue(proxy["captured"])
            self.assertEqual(proxy["prompt_surface_tokens"], 0)
            self.assertEqual(proxy["persistence"], "durable")
            self.assertEqual(
                ce.read_wave_snapshot(root, wave_id)["stages"]["prepare"][
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
                "wave_review",
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
                "wave_prepare",
                wave_id,
                core,
                focus_stage="prepare",
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
                patch.object(srv, "wave_pause_response", return_value=pause_core),
                patch.object(srv, "wave_reopen_response", return_value=reopen_core),
                patch.object(
                    srv,
                    "_flush_context_efficiency",
                    return_value=failed_projection,
                ),
            ):
                paused = mcp.tools["wave_pause"](wave_id, mode="create")
                reopened = mcp.tools["wave_reopen"](wave_id)
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
            ("wave_create_wave", {"created": True}, True, True),
            ("wave_create_wave", {"created": False}, True, False),
            (
                "wave_prepare",
                {"mode": "create", "transitioned_to_active": True},
                True,
                True,
            ),
            (
                "wave_prepare",
                {"mode": "create", "transitioned_to_active": False},
                True,
                False,
            ),
            (
                "wave_prepare",
                {"mode": "ready", "readied": True},
                True,
                True,
            ),
            (
                "wave_implement",
                {"transitioned_to_implementing": True},
                True,
                True,
            ),
            (
                "wave_implement",
                {
                    "already_implementing": True,
                    "transitioned_to_implementing": False,
                },
                True,
                False,
            ),
            (
                "wave_close",
                {"updated": True, "transitioned_to_closed": True},
                True,
                True,
            ),
            (
                "wave_close",
                {"updated": False, "transitioned_to_closed": False},
                True,
                False,
            ),
            (
                "wave_implement",
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
                "wave_close",
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
                srv.wave_garden_response(root, mode="run")
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

    def test_wave_review_source_is_read_only(self):
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        fn = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "wave_review_response"
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


if __name__ == "__main__":
    unittest.main()
