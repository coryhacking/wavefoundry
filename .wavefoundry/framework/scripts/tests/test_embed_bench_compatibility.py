"""Offline benchmark/report controls for hosts without Unix resource APIs."""
from __future__ import annotations

import builtins
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
BENCH = SCRIPTS / "benchmarks" / "embed_bench.py"


def load_benchmark(*, missing="resource"):
    real_import = builtins.__import__

    def import_without_resource(name, *args, **kwargs):
        if name == "resource":
            raise ModuleNotFoundError(f"No module named '{missing}'", name=missing)
        return real_import(name, *args, **kwargs)

    spec = importlib.util.spec_from_file_location("_benchmark_compatibility", BENCH)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.object(builtins, "__import__", side_effect=import_without_resource):
        spec.loader.exec_module(module)
    return module


class BenchmarkCompatibilityTests(unittest.TestCase):
    def test_help_without_resource(self):
        bench = load_benchmark()
        self.assertIsNone(bench.resource)
        output = io.StringIO()
        with mock.patch.object(sys, "argv", [str(BENCH), "--help"]), \
                contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as exit_:
            bench.main()
        self.assertEqual(exit_.exception.code, 0)
        self.assertIn("--models", output.getvalue())
        self.assertIn("JSON null", " ".join(output.getvalue().split()))

    def test_unrelated_import_failure_is_not_hidden(self):
        with self.assertRaises(ModuleNotFoundError) as error:
            load_benchmark(missing="unrelated_dependency")
        self.assertEqual(error.exception.name, "unrelated_dependency")

    def run_report(self, bench):
        # Use the real workload measurements, retrieval scoring and report writer;
        # only model/index access and tokenizer metadata are replaced with fixtures.
        chunks = [{"text": "document", "path": "docs/example.md"},
                  {"text": "code", "path": "src/example.py"}]
        embeds = []

        def embed(model, texts):
            embeds.append((model, list(texts)))
            return np.array([[0., 1.] if text == "code" else [1., 0.] for text in texts])

        indexer = SimpleNamespace(_get_embedder=lambda name: name, _embed_texts=embed)
        quality = bench.measure_retrieval_quality
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evaluation = root / "evaluation.json"
            evaluation.write_text(json.dumps({"queries": [
                {"id": "docs", "kind": "docs", "query": "document", "expected_paths": ["docs/example.md"]},
                {"id": "code", "kind": "code", "query": "code", "expected_paths": ["src/example.py"]},
            ]}), encoding="utf-8")
            report_path = root / "report.json"
            output = io.StringIO()
            with mock.patch.object(sys, "argv", [str(BENCH), "--root", str(root), "--models", "base,candidate", "--report", str(report_path)]), \
                    mock.patch.object(bench, "_load_indexer", return_value=indexer), \
                    mock.patch.object(bench, "_load_chunks", return_value=(chunks[:1], chunks[1:])), \
                    mock.patch.object(bench, "_truncation_rate", return_value={"truncated_count": 0, "total_count": 2, "truncation_rate": 0., "max_tokens": 512}), \
                    mock.patch.object(bench, "measure_retrieval_quality", side_effect=lambda *a, **kw: quality(*a, **kw, eval_path=evaluation)), \
                    contextlib.redirect_stdout(output):
                bench.main()
            report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual([m["model"] for m in report["models"]], ["base", "candidate"])
        for model in report["models"]:
            self.assertNotIn("error", model)
            self.assertEqual(model["full_rebuild"]["chunks"], 2)
            self.assertGreaterEqual(model["full_rebuild"]["elapsed_s"], 0)
            self.assertGreater(model["full_rebuild"]["chunks_per_sec"], 0)
            self.assertGreater(model["query_latency"]["n_reps"], 0)
            self.assertEqual(model["retrieval_quality"]["overall_accuracy"], 1.)
            self.assertEqual(model["retrieval_quality"]["total_queries"], 2)
        self.assertTrue(embeds)
        self.assertNotIn("ERROR", output.getvalue())
        self.assertIn("SUMMARY", output.getvalue())
        return report["models"], output.getvalue()

    def test_full_report_without_resource(self):
        models, output = self.run_report(load_benchmark())
        for model in models:
            self.assertIsNone(model["full_rebuild"]["peak_rss_mb"])
            self.assertIsNone(model["full_rebuild"]["rss_delta_mb"])
            self.assertIn("resource", model["full_rebuild"]["memory_unavailable_reason"])
        self.assertIsNone(models[1]["vs_baseline"]["memory_ok"])
        self.assertIn("unavailable", models[1]["vs_baseline"]["memory_unavailable_reason"])
        self.assertEqual(models[1]["vs_baseline"]["quality_delta"], 0.)
        self.assertIn("RSS unavailable", output)
        self.assertIn("unavailable", output.split("SUMMARY", 1)[1])
        self.assertNotIn("NoneMB", output)

    def test_either_missing_memory_operand_keeps_comparison_unknown(self):
        for readings in ([None, None, 10., 20.], [10., 20., None, None]):
            with self.subTest(readings=readings):
                bench = load_benchmark()
                with mock.patch.object(bench, "_peak_rss_mb", side_effect=readings):
                    models, _ = self.run_report(bench)
                self.assertIsNone(models[1]["vs_baseline"]["memory_ok"])
                self.assertIn("unavailable", models[1]["vs_baseline"]["memory_unavailable_reason"])

    def test_supported_memory_units_delta_and_comparison(self):
        for platform, unit in (("darwin", 1024 * 1024), ("linux", 1024)):
            for candidate, expected in ((30., True), (50., False)):
                with self.subTest(platform=platform, candidate=candidate):
                    bench = load_benchmark()
                    usage = SimpleNamespace(RUSAGE_SELF=0, getrusage=mock.Mock(side_effect=[
                        SimpleNamespace(ru_maxrss=value * unit) for value in (10., 20., 25., candidate)
                    ]))
                    with mock.patch.object(bench, "resource", usage), \
                            mock.patch.object(bench, "sys", SimpleNamespace(platform=platform)):
                        models, output = self.run_report(bench)
                    self.assertEqual(models[0]["full_rebuild"]["peak_rss_mb"], 20.)
                    self.assertEqual(models[0]["full_rebuild"]["rss_delta_mb"], 10.)
                    self.assertEqual(models[1]["full_rebuild"]["peak_rss_mb"], candidate)
                    self.assertEqual(models[1]["full_rebuild"]["rss_delta_mb"], candidate - 25.)
                    self.assertIs(models[1]["vs_baseline"]["memory_ok"], expected)
                    self.assertNotIn("memory_unavailable_reason", models[1]["vs_baseline"])
                    self.assertNotIn("memory_unavailable_reason", models[0]["full_rebuild"])
                    self.assertNotIn("unavailable", output)


if __name__ == "__main__":
    unittest.main()
