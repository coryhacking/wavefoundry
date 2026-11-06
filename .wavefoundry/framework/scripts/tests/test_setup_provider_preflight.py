"""Public setup controls with real published SQLite state and inert model leaves."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "tests"))

import inference_provider
import inference_profile
import model_bundle
import setup_index
import tensorwell_client
import test_indexer as indexer_tests


class SetupProviderPreflightTests(unittest.TestCase):
    def pin_modules(self, modules):
        missing = object()
        previous = {name: sys.modules.get(name, missing) for name in modules}

        def restore():
            for name, value in previous.items():
                if value is missing:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = value

        self.addCleanup(restore)
        sys.modules.update(modules)

    def setUp(self):
        # Other framework test loaders deliberately replace these sys.modules
        # entries. Pin this fixture's patched objects for dynamic imports too.
        self.real_select_embedder = inference_provider.select_embedder
        self.pin_modules({
            "setup_index": setup_index, "inference_provider": inference_provider,
            "inference_profile": inference_profile, "tensorwell_client": tensorwell_client,
            "model_bundle": model_bundle,
        })
        # Existing fixture publishes real deterministic vectors through build_index.
        self.fixture = indexer_tests.ExplicitPrecisionRebuildTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture._seed("full")
        self.indexer = self.fixture.bi
        self.root = self.fixture.root
        # Most boundary controls require actual work; no-work controls reseed.
        self.source = self.root / "docs/guide.md"
        self.source.write_text(self.source.read_text() + "\nPending setup update.\n")
        self.before = self.fixture._snapshot()
        self.real_setup_build = setup_index.build_index
        self.events = []
        self.gpu = ["CoreMLExecutionProvider"]
        self.covered = True
        self.reason = "discovery_unavailable"
        self.selections = 0
        self.choose = None
        self.adapter = types.SimpleNamespace(provider="fixture-service")
        self.accel = types.SimpleNamespace(
            GPU_PROVIDERS=("CoreMLExecutionProvider", "CUDAExecutionProvider"),
            CLEAN_ONNX_SOURCES={self.indexer.DOCS_MODEL, self.indexer.CODE_MODEL},
            _available_gpu_providers=lambda: list(self.gpu),
            _coreml_static_probe_cache={},
            make_embedder=lambda model, providers: self.leaf("compile", model),
            make_reranker=lambda model, providers: self.leaf("reranker", model),
        )
        self.enterContext(patch.dict(os.environ, {
            "WAVEFOUNDRY_DISABLE_TENSORWELL": "0", "WAVEFOUNDRY_EMBED_PROVIDER": "auto",
            "WAVEFOUNDRY_EMBED_PROVIDER_SELECTED": "", "WAVEFOUNDRY_DISABLE_RERANKER": "0",
        }))
        self.enterContext(patch.object(inference_profile, "PROVIDER", "tensorwell"))
        self.enterContext(patch.object(inference_profile, "ADAPTER_MODULE", ""))
        self.enterContext(patch.object(inference_provider, "select_embedder", side_effect=self.select))
        self.enterContext(patch.object(inference_provider, "select_reranker", side_effect=self.select_reranker))
        self.enterContext(patch.object(self.indexer, "accel_embedder", self.accel))
        self.pin_modules({"accel_embedder": self.accel})
        self.enterContext(patch.object(self.indexer, "_onnx_providers", side_effect=lambda: self.gpu or ["CPUExecutionProvider"]))
        self.enterContext(patch.object(setup_index, "_load_indexer_module", return_value=self.indexer))
        self.enterContext(patch.object(setup_index, "_indexer_models", side_effect=self.models))
        self.enterContext(patch.object(setup_index, "_indexer_reranker_model", return_value="fixture-reranker"))
        self.enterContext(patch.object(setup_index, "ensure_deps"))
        self.enterContext(patch.object(setup_index, "_reexec_with_venv_if_needed"))
        self.enterContext(patch.object(model_bundle, "find_local_bundle", return_value=None))
        self.enterContext(patch.object(model_bundle, "local_model_set_status", return_value="current"))
        self.enterContext(patch.object(model_bundle, "attest_online_cache", return_value=False))
        self.enterContext(patch.object(setup_index, "_prewarm_required_model", side_effect=lambda model, **kw: self.leaf("warm", model)))
        self.enterContext(patch.object(setup_index, "report_embedding_provider_decision", side_effect=lambda **kw: self.leaf("probe", kw["model_name"])))
        self.enterContext(patch.object(setup_index.provider_policy, "select_embedding_providers", side_effect=lambda: types.SimpleNamespace(providers=self.gpu or ["CPUExecutionProvider"])))
        self.enterContext(patch.object(setup_index, "build_index", side_effect=self.build))
        self.enterContext(patch.object(setup_index, "_optimize_after_build"))
        self.enterContext(patch.object(setup_index, "_spawn_background_code_build"))
        self.enterContext(patch.object(setup_index, "_spawn_background_docs_build"))

    def models(self, include_code, code_only=False):
        models = [] if code_only else [self.indexer.DOCS_MODEL]
        if include_code or code_only:
            models.append(self.indexer.CODE_MODEL)
        return list(dict.fromkeys(models))

    def leaf(self, kind, model):
        self.events.append((kind, model))
        return None

    def select(self, model, precision_class="full", *, diagnostic=None):
        self.selections += 1
        selected = self.choose(model, self.selections) if self.choose else self.covered
        self.events.append(("select", selected))
        return tensorwell_client._selection_result(self.adapter if selected else None,
            "qualified_pair" if selected else self.reason, diagnostic)

    def select_reranker(self, model, *, diagnostic=None):
        return tensorwell_client._selection_result(self.adapter, "qualified_pair", diagnostic)

    def build(self, root, **kwargs):
        self.events.append(("build", kwargs["full"]))
        if not kwargs["full"]:
            refused = self.indexer._implicit_precision_refusal(self.fixture.index_dir, None)
            if refused:
                print(refused["failure"], file=sys.stderr)
                raise subprocess.CalledProcessError(2, "fixture indexer")

    def run_setup(self, *args):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(out):
            code = setup_index.main(["--root", str(self.root), *args])
        self.assertEqual(self.fixture._snapshot(), self.before, "published vectors and bookkeeping changed")
        return code, out.getvalue()

    def prepared(self):
        return [event for event in self.events if event[0] in {"warm", "probe", "compile", "reranker"}]

    def test_unavailable_cpu_refuses_before_any_preparation_and_qualified_control_skips(self):
        self.covered = False
        self.gpu = []
        code, output = self.run_setup()
        self.assertEqual(code, 2)
        self.assertIn("recorded full, requested int8", output)
        self.assertIn("discovery_unavailable", output)
        self.assertEqual(self.prepared(), [])
        self.assertFalse(any(e[0] == "build" for e in self.events))
        self.events.clear()
        self.covered = True
        self.gpu = ["CoreMLExecutionProvider"]
        code, output = self.run_setup()
        self.assertEqual(code, 0)
        self.assertEqual(self.prepared(), [])
        self.assertIn("selection only", output)
        self.assertNotIn("executed inference", output)

    def test_absent_service_uses_compatible_automatic_local_preparation(self):
        self.covered = False
        code, output = self.run_setup()
        self.assertEqual(code, 0)
        self.assertTrue(any(kind == "warm" for kind, _ in self.prepared()))
        self.assertTrue(any(kind == "probe" for kind, _ in self.prepared()))
        self.assertTrue(any(kind == "compile" for kind, _ in self.prepared()))
        self.assertNotIn("compatibility unverified", output)
        self.assertEqual(os.environ["WAVEFOUNDRY_EMBED_PROVIDER"], "auto")

    def test_fresh_legacy_unknown_compatible_local_and_full_rebuild_controls(self):
        self.covered = False
        self.gpu = []
        for prior in ({}, {"model_versions": {"docs": "legacy-model"}, "content": ["docs"]},
                      {"model_versions": {"docs": "model@unknown"}, "content": ["docs"]}):
            with self.subTest(prior=prior), patch.object(self.indexer, "_load_meta", return_value=prior):
                self.events.clear()
                self.assertEqual(self.run_setup()[0], 0)
                self.assertTrue(self.prepared())
        # Explicit local policy preserves preparation under availability prediction.
        self.gpu = ["CoreMLExecutionProvider"]
        with patch.object(inference_profile, "PROVIDER", "local"):
            self.events.clear()
            self.assertEqual(self.run_setup()[0], 0)
            self.assertTrue(self.prepared())
        self.gpu = []
        self.events.clear()
        self.assertEqual(self.run_setup("--full")[0], 0)
        self.assertTrue(self.prepared())
        self.assertIn(("build", True), self.events)
        # Recognized compatible INT8 still supports ordinary local setup.
        meta = self.indexer._load_meta(self.fixture.index_dir)
        meta["model_versions"] = {layer: "model@int8@fixture" for layer in ("docs", "code")}
        with patch.object(self.indexer, "_load_meta", return_value=meta):
            self.events.clear()
            self.assertEqual(self.run_setup()[0], 0)
            self.assertTrue(self.prepared())

    def test_mixed_coverage_prepares_only_uncovered_compatible_model(self):
        self.enterContext(patch.object(self.indexer, "CODE_MODEL", "fixture-code"))
        self.accel.CLEAN_ONNX_SOURCES.add("fixture-code")
        self.choose = lambda model, count: model != "fixture-code"
        with patch.object(self.indexer, "_load_meta", return_value={}):
            self.assertEqual(self.run_setup()[0], 0)
        prepared = self.prepared()
        self.assertIn(("warm", "fixture-code"), prepared)
        self.assertIn(("compile", "fixture-code"), prepared)
        self.assertTrue(all(model == "fixture-code" for kind, model in prepared))
        # Requested detached layers are assessed before foreground preparation.
        for flag in ("--background-code", "--background-docs"):
            with self.subTest(flag=flag):
                self.events.clear()
                self.assertEqual(self.run_setup(flag)[0], 0)
                if flag == "--background-code":
                    self.assertEqual(self.prepared(), [])  # uncovered work is detached
                else:
                    self.assertTrue(self.prepared())

    def test_changed_selection_allows_compatible_local_work(self):
        for vanish_at in (2, 3, 4):
            with self.subTest(vanish_at=vanish_at):
                self.events.clear()
                self.selections = 0
                self.choose = lambda model, count: count < vanish_at
                code, output = self.run_setup()
                self.assertEqual(code, 0)
                self.assertTrue(self.prepared())
                self.assertIn("discovery_unavailable", output)

    def test_provider_probe_rejection_rechecks_precision_before_native_accel(self):
        self.covered = False
        def reject_probe(**kwargs):
            self.leaf("probe", kwargs["model_name"])
            self.gpu = []
        with patch.object(setup_index, "report_embedding_provider_decision", side_effect=reject_probe):
            code, output = self.run_setup()
        self.assertEqual(code, 2)
        self.assertIn("recorded full, requested int8", output)
        self.assertTrue(any(kind == "warm" for kind, _ in self.prepared()))
        self.assertFalse(any(kind in {"compile", "reranker"} for kind, _ in self.prepared()))
        self.assertFalse(any(event[0] == "build" for event in self.events))

    def test_loss_after_preflight_still_hits_direct_indexer_guard(self):
        def change_at_build(root, **kwargs):
            self.gpu = []
            return self.build(root, **kwargs)
        with patch.object(setup_index, "build_index", side_effect=change_at_build):
            code, output = self.run_setup()
        self.assertEqual(code, 2)
        self.assertIn("Implicit precision conversion refused", output)
        self.assertEqual(self.prepared(), [])
        # Exercise the actual public indexer entry, not the setup wrapper.
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = self.indexer.build_index(self.root, content="all")
        self.assertTrue(result["failed"])
        self.assertIn("precision_changes", result)
        self.assertEqual(self.fixture._snapshot(), self.before)

    def test_bounded_diagnostics_and_explicit_controls(self):
        self.covered = False
        self.gpu = []
        for reason in ("unsupported_model", "index_precision_mismatch", "provider_policy", "disabled",
                       "incompatible_profiles", "capabilities_unsupported", "discovery_unavailable"):
            with self.subTest(reason=reason):
                self.reason = reason
                code, output = self.run_setup()
                self.assertEqual(code, 2)
                self.assertIn(reason, output)
                self.assertNotIn("Tensorwell is stopped", output)
                self.assertIn("compatible", output)
        private = "Authorization: Bearer private-token http://private-discovery"
        with patch.object(inference_provider, "select_embedder", side_effect=RuntimeError(private)):
            code, output = self.run_setup()
        self.assertEqual(code, 2)
        self.assertIn("selection_unknown", output)
        self.assertNotIn(private, output)
        self.assertNotIn("private-token", output)
        # An explicit CPU request must still hit a known precision mismatch.
        with patch.dict(os.environ, {"WAVEFOUNDRY_EMBED_PROVIDER": "cpu"}):
            self.assertEqual(self.run_setup()[0], 2)

    def test_early_and_repeated_guard_mutants_expose_unwanted_preparation(self):
        self.covered = False
        self.gpu = []
        with patch.object(setup_index, "_check_setup_precision"):
            code, _ = self.run_setup()
        self.assertEqual(code, 2)
        self.assertTrue(any(kind == "warm" for kind, _ in self.prepared()))
        # A probe can alter local precision after the initial compatible check.
        self.events.clear()
        self.gpu = ["CoreMLExecutionProvider"]
        original = setup_index._check_setup_precision
        calls = []
        def once(*args):
            calls.append(1)
            if len(calls) == 1:
                original(*args)
        def reject_probe(**kwargs):
            self.leaf("probe", kwargs["model_name"])
            self.gpu = []
        with patch.object(setup_index, "_check_setup_precision", side_effect=once), \
             patch.object(setup_index, "report_embedding_provider_decision", side_effect=reject_probe):
            self.assertEqual(self.run_setup()[0], 2)
        self.assertTrue(any(kind == "compile" for kind, _ in self.prepared()))

    def use_real_index_build(self, before_build=None):
        self.results = []
        def run_indexer(root, **kwargs):
            if before_build is not None:
                before_build()
            result = self.indexer.build_index(root, **kwargs)
            self.results.append(result)
            if result.get("failed"):
                raise subprocess.CalledProcessError(2, "fixture indexer")
        self.enterContext(patch.object(setup_index, "build_index", side_effect=self.real_setup_build))
        self.enterContext(patch.object(setup_index, "_run_indexer", side_effect=run_indexer))

    def settle_source(self):
        self.fixture._seed("full")
        self.before = self.fixture._snapshot()
        self.events.clear()

    def test_current_plan_skips_preparation_but_reaches_real_build(self):
        self.settle_source()
        self.covered = False
        self.use_real_index_build()
        with patch.object(self.indexer, "_get_embedder", side_effect=AssertionError("unexpected embedding")):
            code, output = self.run_setup()
        self.assertEqual(code, 0)
        self.assertIn("Normal index validation continues", output)
        self.assertEqual(self.prepared(), [])
        self.assertEqual(len(self.results), 1)
        self.assertTrue(self.results[0]["up_to_date"])
        self.assertEqual(self.results[0]["files_indexed"], 0)

    def test_changed_work_uses_local_preparation_and_real_build(self):
        self.covered = False
        self.use_real_index_build()
        with patch.object(self.indexer, "_get_embedder", return_value=self.fixture.embedder):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = setup_index.main(["--root", str(self.root)])
        self.assertEqual(code, 0)
        self.assertTrue(self.prepared())
        self.assertFalse(self.results[0]["up_to_date"])
        self.assertGreater(self.results[0]["files_indexed"], 0)
        self.assertTrue(self.fixture.calls)

    def test_invalid_extension_cannot_gain_no_work_exemption(self):
        self.settle_source()
        with patch.object(inference_profile, "PROVIDER", "extension"), \
             patch.object(inference_provider, "select_embedder", side_effect=self.real_select_embedder):
            code, output = self.run_setup()
        self.assertEqual(code, 2)
        self.assertEqual(self.prepared(), [])
        self.assertIn("Declared inference provider is unavailable", output)

    def test_nonsemantic_special_paths_do_not_use_no_work_assessment(self):
        for flag in ("--deps-only", "--graph-only", "--prewarm-only"):
            with self.subTest(flag=flag), \
                 patch.object(setup_index, "_setup_semantic_work_is_current", side_effect=AssertionError("unexpected planning")), \
                 patch.object(setup_index, "_run_indexer"):
                self.assertEqual(self.run_setup(flag)[0], 0)

    def test_source_change_after_current_plan_is_indexed_by_real_build(self):
        self.settle_source()
        self.covered = False
        def change_source():
            self.source.write_text(self.source.read_text() + "\nArrived after planning.\n")
        self.use_real_index_build(change_source)
        with patch.object(self.indexer, "_get_embedder", return_value=self.fixture.embedder):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = setup_index.main(["--root", str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(self.prepared(), [])
        self.assertFalse(self.results[0]["up_to_date"])
        self.assertGreater(self.results[0]["files_indexed"], 0)
        self.assertTrue(self.fixture.calls)

    def test_provider_change_after_current_plan_retains_published_snapshot(self):
        self.settle_source()
        self.covered = False
        self.use_real_index_build(lambda: self.gpu.clear())
        with patch.object(self.indexer, "_get_embedder", side_effect=AssertionError("incompatible embedding")):
            code, output = self.run_setup()
        self.assertEqual(code, 2)
        self.assertIn("Implicit precision conversion refused", output)
        self.assertEqual(self.prepared(), [])
        self.assertTrue(self.results[0]["failed"])

    def test_uncertain_plan_preserves_normal_preparation_without_exception_text(self):
        self.covered = False
        for result in (None, {}, {"up_to_date": "true"}, {"up_to_date": True, "failed": True}):
            with self.subTest(result=result), patch.object(self.indexer, "build_index", return_value=result):
                self.events.clear()
                self.assertEqual(self.run_setup()[0], 0)
                self.assertTrue(self.prepared())
        with patch.object(self.indexer, "build_index", side_effect=ValueError("private diagnostic")):
            self.events.clear()
            code, output = self.run_setup()
        self.assertEqual(code, 0)
        self.assertTrue(self.prepared())
        self.assertNotIn("private diagnostic", output)

    def test_planner_matches_scope_and_flags_and_does_not_override_rebuild(self):
        for flag, content in (("--docs-only", "docs"), ("--code-only", "code"),
                              ("--background-code", "all"), ("--background-docs", "all")):
            with self.subTest(flag=flag), patch.object(self.indexer, "build_index", wraps=self.indexer.build_index) as plan:
                self.assertEqual(self.run_setup(flag, "--include-tests", "--include-generated")[0], 0)
                self.assertEqual(plan.call_args.kwargs, dict(content=content, include_tests=True,
                                                           include_generated=True, dry_run=True))
        self.covered = False
        for flag in ("--full", "--rechunk"):
            with self.subTest(flag=flag), patch.object(self.indexer, "build_index") as plan:
                self.events.clear()
                self.assertEqual(self.run_setup(flag)[0], 0)
                plan.assert_not_called()
                self.assertTrue(self.prepared())

    def test_canonical_plan_observes_self_hosted_sources_and_identity_changes(self):
        code = self.root / ".wavefoundry/framework/scripts/example.py"
        code.parent.mkdir(parents=True, exist_ok=True)
        code.write_text("def example(): return 1\n")
        config = self.root / "docs/workflow-config.json"
        config.write_text('{"indexing":{"project_include_prefixes":{"code":[".wavefoundry/framework/scripts"]}}}')
        self.settle_source()
        self.covered = False
        code.write_text("def example(): return 2\n")
        self.assertEqual(self.run_setup()[0], 0)
        self.assertTrue(self.prepared())
        self.settle_source()
        for owner, field in ((self.indexer, "WALKER_VERSION"), (self.indexer._get_chunker(), "CHUNKER_VERSION")):
            with self.subTest(field=field), patch.object(owner, field, str(getattr(owner, field)) + "-changed"):
                self.events.clear()
                self.assertEqual(self.run_setup()[0], 0)
                self.assertTrue(self.prepared())


if __name__ == "__main__":
    unittest.main()
