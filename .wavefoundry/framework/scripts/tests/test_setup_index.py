from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, call, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
SETUP_INDEX_PATH = SCRIPTS_ROOT / "setup_index.py"

FAKE_VENV_PYTHON = Path("/fake/venv/bin/python")


def load_setup_index():
    spec = importlib.util.spec_from_file_location("setup_index", SETUP_INDEX_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["setup_index"] = mod
    spec.loader.exec_module(mod)
    return mod


def load_indexer():
    indexer_path = SCRIPTS_ROOT / "indexer.py"
    spec = importlib.util.spec_from_file_location("wavefoundry_indexer", indexer_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wavefoundry_indexer"] = mod
    spec.loader.exec_module(mod)
    return mod


class VenvBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_setup_index()

    def test_bootstrap_venv_creates_venv_when_absent(self):
        """_bootstrap_venv creates the venv when the directory does not exist.

        Wave 1p8gu: venv creation now routes through subprocess_util.isolated_run (stdin+no-window),
        which delegates to subprocess.run — so patch subprocess.run and assert on it."""
        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("subprocess.run") as run:
                    run.return_value = subprocess.CompletedProcess([], 0)
                    with redirect_stdout(io.StringIO()):
                        result = self.mod._bootstrap_venv()

        run.assert_called_once()
        cmd = run.call_args[0][0]
        self.assertIn("-m", cmd)
        self.assertIn("venv", cmd)
        self.assertEqual(result, FAKE_VENV_PYTHON)

    def test_bootstrap_venv_skips_creation_when_python_exists(self):
        """_bootstrap_venv does not call venv when the Python binary already exists."""
        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("subprocess.run") as run:
                    with redirect_stdout(io.StringIO()):
                        result = self.mod._bootstrap_venv()

        run.assert_not_called()
        self.assertEqual(result, FAKE_VENV_PYTHON)

    def test_bootstrap_venv_recreates_partial_venv(self):
        """_bootstrap_venv deletes and recreates a partial venv (dir exists but Python binary absent)."""
        venv_dir = FAKE_VENV_PYTHON.parent.parent

        def exists_side_effect(self_path):
            # venv_dir.exists() → True; venv_python.exists() → False (binary absent)
            return self_path == venv_dir

        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("pathlib.Path.exists", exists_side_effect):
                with patch("shutil.rmtree") as rmtree:
                    with patch("subprocess.run") as run:
                        run.return_value = subprocess.CompletedProcess([], 0)
                        with redirect_stdout(io.StringIO()):
                            self.mod._bootstrap_venv()

        rmtree.assert_called_once_with(venv_dir, ignore_errors=True)

    def test_bootstrap_venv_recreates_python_version_mismatch(self):
        """A stale tool venv built for another Python minor is deleted and recreated."""
        with tempfile.TemporaryDirectory() as tmp:
            venv_dir = Path(tmp) / "venv"
            venv_python = venv_dir / "bin" / "python"
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text("", encoding="utf-8")
            other = f"{sys.version_info[0]}.{sys.version_info[1] + 1}.0"
            (venv_dir / "pyvenv.cfg").write_text(f"version = {other}\n", encoding="utf-8")

            with patch.object(self.mod, "_tool_venv_python", return_value=venv_python):
                with patch("subprocess.run") as run:
                    run.return_value = subprocess.CompletedProcess([], 0)
                    with redirect_stdout(io.StringIO()) as out:
                        result = self.mod._bootstrap_venv()

            self.assertEqual(result, venv_python)
            self.assertFalse(venv_dir.exists(), "stale venv should be removed before recreation")
            self.assertEqual(run.call_args[0][0], [sys.executable, "-m", "venv", str(venv_dir)])
            self.assertIn("was built for Python", out.getvalue())
            self.assertIn("recreating", out.getvalue())


class SetupIndexTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_setup_index()
        # Wave 1p52p: never run the REAL GPU-accel prewarm inside unit tests — it downloads the
        # Xenova FP16 reranker, pays the CoreML compile, and imports the heavy `onnx` package
        # (slow + real-hardware + protobuf/onnx import surface). `main()` calls it; the orchestration
        # tests assert on prewarm_models/build_index, not the GPU prewarm.
        _gpu = patch.object(self.mod, "_prewarm_gpu_accel")
        _gpu.start()
        self.addCleanup(_gpu.stop)

    def test_fastembed_cache_dir_defaults_under_wavefoundry_cache(self):
        default_cache = Path("/tmp/home/.wavefoundry/cache/fastembed")
        with patch.object(self.mod, "FASTEMBED_CACHE_DEFAULT", default_cache):
            with patch.dict(os.environ, {}, clear=True):
                cache_dir = self.mod._fastembed_cache_dir()
        self.assertEqual(cache_dir, default_cache)

    def test_arctic_docs_model_cache_alias_resolves_lowercase_dir(self):
        # 1p4wx: arctic-embed-xs (DOCS_MODEL) — fastembed downloads to the lowercase
        # ``models--snowflake--…`` dir, so the offline cache resolution must include it.
        default_cache = Path("/tmp/home/.wavefoundry/cache/fastembed")
        with patch.object(self.mod, "FASTEMBED_CACHE_DEFAULT", default_cache):
            with patch.dict(os.environ, {}, clear=True):
                names = {
                    p.name
                    for p in self.mod._model_cache_dir_candidates("Snowflake/snowflake-arctic-embed-xs")
                }
        self.assertIn("models--snowflake--snowflake-arctic-embed-xs", names)

    def test_ensure_deps_installs_missing_packages(self):
        """ensure_deps calls _install_deps for missing packages then rechecks."""
        with patch.object(self.mod, "_bootstrap_venv", return_value=FAKE_VENV_PYTHON):
            with patch.object(self.mod, "_missing_in_venv", return_value=["fastembed", "numpy"]):
                with patch.object(self.mod, "_install_deps"):
                    with self.assertRaises(SystemExit) as raised:
                        # Second call to _missing_in_venv still returns packages → exits 2
                        self.mod.ensure_deps()
        self.assertEqual(raised.exception.code, 2)

    def test_ensure_deps_succeeds_when_all_installed(self):
        with patch.object(self.mod, "_bootstrap_venv", return_value=FAKE_VENV_PYTHON):
            with patch.object(self.mod, "_missing_in_venv", return_value=[]):
                with redirect_stdout(io.StringIO()):
                    self.mod.ensure_deps()  # must not raise

    def test_ensure_deps_calls_install_with_missing_list(self):
        """ensure_deps passes the missing list from _missing_in_venv to _install_deps."""
        missing = ["fastembed", "lancedb"]
        call_count = [0]

        def missing_side_effect(venv_python, required_imports=None):
            call_count[0] += 1
            return missing if call_count[0] == 1 else []

        with patch.object(self.mod, "_bootstrap_venv", return_value=FAKE_VENV_PYTHON):
            with patch.object(self.mod, "_missing_in_venv", side_effect=missing_side_effect):
                with patch.object(self.mod, "_install_deps") as mock_install:
                    with redirect_stdout(io.StringIO()):
                        self.mod.ensure_deps()

        mock_install.assert_called_once_with(missing, FAKE_VENV_PYTHON)

    def test_install_deps_invokes_pip_via_venv_python(self):
        """_install_deps uses the venv Python, not sys.executable."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with redirect_stdout(io.StringIO()):
                self.mod._install_deps(["fastembed", "mcp[cli]", "tree-sitter>=0.24,<0.26"], FAKE_VENV_PYTHON)

        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], str(FAKE_VENV_PYTHON))
        self.assertIn("-m", cmd)
        self.assertIn("pip", cmd)
        # Raw dep strings passed to subprocess — no shell quoting
        self.assertIn("fastembed", cmd)
        self.assertIn("mcp[cli]", cmd)
        self.assertIn("tree-sitter>=0.24,<0.26", cmd)
        # Shell-quoted forms must NOT appear in the subprocess cmd
        self.assertNotIn('"mcp[cli]"', cmd)
        self.assertNotIn('"tree-sitter>=0.24,<0.26"', cmd)
        # Must not use sys.executable
        self.assertNotEqual(cmd[0], sys.executable)

    def test_install_deps_does_not_use_break_system_packages(self):
        """_install_deps never passes --break-system-packages."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            with redirect_stderr(io.StringIO()):
                with redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        self.mod._install_deps(["fastembed"], FAKE_VENV_PYTHON)

        all_calls = mock_run.call_args_list
        for c in all_calls:
            cmd = c[0][0]
            self.assertNotIn("--break-system-packages", cmd)

    def test_install_deps_exits_on_pip_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            with redirect_stderr(io.StringIO()):
                with redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        self.mod._install_deps(["fastembed"], FAKE_VENV_PYTHON)
        self.assertEqual(raised.exception.code, 2)

    def _make_popen_mock(self, returncode: int = 0, lines: list[str] | None = None) -> MagicMock:
        proc = MagicMock()
        proc.returncode = returncode
        proc.stdout = iter(lines or [])
        proc.wait.return_value = None
        return proc

    def test_build_index_uses_venv_python(self):
        root = Path("/tmp/wavefoundry-test-root")

        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("subprocess.Popen", return_value=self._make_popen_mock()) as popen_mock:
                with redirect_stdout(io.StringIO()):
                    self.mod.build_index(
                        root,
                        full=True,
                        include_code=True,
                        verbose=True,
                        include_tests=True,
                        include_generated=True,
                        project_include_prefixes_for_docs=(),
                        project_include_prefixes_for_code=(),
                    )

        calls = [c.args[0] for c in popen_mock.call_args_list]
        self.assertEqual(len(calls), 1)
        cmd = calls[0]
        self.assertEqual(cmd[0], str(FAKE_VENV_PYTHON))
        self.assertNotEqual(cmd[0], sys.executable)
        self.assertIn(str(SCRIPTS_ROOT / "indexer.py"), cmd)
        self.assertIn("--content", cmd)
        self.assertIn("all", cmd)
        self.assertIn("--include-tests", cmd)
        self.assertIn("--include-generated", cmd)
        self.assertIn("--full", cmd)
        self.assertIn("--verbose", cmd)
        self.assertNotIn("--project-include-prefix", cmd)

    def test_build_index_can_forward_project_include_prefixes_for_code_pass(self):
        root = Path("/tmp/wavefoundry-test-root")
        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("subprocess.Popen", return_value=self._make_popen_mock()) as popen_mock:
                with redirect_stdout(io.StringIO()):
                    self.mod.build_index(
                        root,
                        full=False,
                        include_code=True,
                        verbose=False,
                        project_include_prefixes_for_docs=("docs/external",),
                        project_include_prefixes_for_code=(".wavefoundry/framework/scripts", "vendor/docs"),
                    )
        calls = [c.args[0] for c in popen_mock.call_args_list]
        self.assertEqual(len(calls), 1)
        cmd = calls[0]
        self.assertIn("--content", cmd)
        self.assertIn("all", cmd)
        self.assertIn("--project-include-prefix", cmd)
        self.assertIn("docs/external", cmd)
        self.assertIn(".wavefoundry/framework/scripts", cmd)
        self.assertIn("vendor/docs", cmd)

    def test_run_indexer_lock_busy_prints_friendly_message(self):
        root = Path("/tmp/wavefoundry-test-root")
        lock_line = (
            "build_index: Another index build is already running for /tmp/wavefoundry-test-root/.wavefoundry/index; "
            "lock file busy: /tmp/wavefoundry-test-root/.wavefoundry/index/index-build.lock\n"
        )
        proc = self._make_popen_mock(returncode=1, lines=[lock_line])

        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("subprocess.Popen", return_value=proc) as popen_mock:
                stdout = io.StringIO()
                stderr = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    self.mod._run_indexer(
                        root,
                        full=False,
                        content="docs",
                        verbose=False,
                        include_tests=False,
                        include_generated=False,
                        project_include_prefixes=(),
                    )

        popen_mock.assert_called_once()
        self.assertIn("Index update skipped:", stderr.getvalue())
        self.assertIn("lock file busy", stderr.getvalue())

    def test_tool_venv_python_default_path(self):
        """Default venv path is ~/.wavefoundry/venv."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WAVEFOUNDRY_TOOL_VENV", None)
            result = self.mod._tool_venv_python()
        expected_dir = Path("~/.wavefoundry/venv").expanduser()
        self.assertEqual(result.parent.parent, expected_dir)

    def test_tool_venv_python_env_override(self):
        """WAVEFOUNDRY_TOOL_VENV overrides the default venv path."""
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": tmp}):
                result = self.mod._tool_venv_python()
        self.assertTrue(str(result).startswith(tmp))

    def test_required_imports_include_sql_tree_sitter(self):
        self.assertIn("tree-sitter-sql", self.mod.REQUIRED_IMPORTS)
        self.assertEqual(self.mod.REQUIRED_IMPORTS["tree-sitter-sql"], "tree_sitter_sql")

    def test_required_imports_include_lancedb(self):
        self.assertIn("lancedb", self.mod.REQUIRED_IMPORTS)
        self.assertEqual(self.mod.REQUIRED_IMPORTS["lancedb"], "lancedb")

    def test_required_imports_include_leiden(self):
        self.assertIn("igraph>=0.11", self.mod.REQUIRED_IMPORTS)
        self.assertEqual(self.mod.REQUIRED_IMPORTS["igraph>=0.11"], "igraph")
        self.assertIn("leidenalg>=0.10", self.mod.REQUIRED_IMPORTS)
        self.assertEqual(self.mod.REQUIRED_IMPORTS["leidenalg>=0.10"], "leidenalg")

    def test_planned_required_imports_adds_cuda_package_for_nvidia(self):
        with patch.object(self.mod.provider_policy, "nvidia_gpu_present", return_value=True):
            with patch.dict(os.environ, {"WAVEFOUNDRY_EMBED_PROVIDER": "auto"}, clear=False):
                required = self.mod._planned_required_imports()
        self.assertIn("fastembed-gpu", required)
        self.assertEqual(required["fastembed-gpu"], "fastembed")

    def test_planned_required_imports_respects_forced_cpu(self):
        with patch.object(self.mod.provider_policy, "nvidia_gpu_present", return_value=True):
            with patch.dict(os.environ, {"WAVEFOUNDRY_EMBED_PROVIDER": "cpu", "WAVEFOUNDRY_DISABLE_RERANKER": ""}, clear=False):
                required = self.mod._planned_required_imports()
        self.assertNotIn("fastembed-gpu", required)
        self.assertIn("onnx", required, "CPU INT8 reranker still needs onnx for the static-shape graph")

    def test_planned_required_imports_omits_onnx_only_when_reranker_disabled_and_no_gpu(self):
        with patch.object(self.mod.provider_policy, "nvidia_gpu_present", return_value=False), \
             patch.object(self.mod.provider_policy, "apple_silicon_present", return_value=False):
            with patch.dict(os.environ, {
                "WAVEFOUNDRY_EMBED_PROVIDER": "cpu",
                "WAVEFOUNDRY_DISABLE_RERANKER": "1",
            }, clear=False):
                required = self.mod._planned_required_imports()
        self.assertNotIn("fastembed-gpu", required)
        self.assertNotIn("onnx", required)

    def test_report_embedding_provider_decision_selects_cuda(self):
        result = self.mod.provider_policy.ProviderProbeResult(
            "CUDAExecutionProvider",
            True,
            "CUDA probe ok",
        )
        with patch.object(
            self.mod.provider_policy,
            "available_onnx_providers",
            return_value=("CUDAExecutionProvider", "CPUExecutionProvider"),
        ):
            with patch.object(self.mod, "_probe_embedding_provider", return_value=result) as probe:
                with patch.dict(os.environ, {}, clear=True):
                    stdout = io.StringIO()
                    with redirect_stdout(stdout):
                        decision = self.mod.report_embedding_provider_decision()
        self.assertEqual(decision.selected_provider, "CUDAExecutionProvider")
        probe.assert_not_called()
        self.assertIn("selected=CUDAExecutionProvider", stdout.getvalue())

    def test_report_embedding_provider_decision_selects_coreml_after_passing_probe(self):
        result = self.mod.provider_policy.ProviderProbeResult(
            "CoreMLExecutionProvider",
            True,
            "CoreML passed benchmark",
            candidate_seconds=0.5,
            cpu_seconds=1.0,
        )
        with patch.object(
            self.mod.provider_policy,
            "available_onnx_providers",
            return_value=("CoreMLExecutionProvider", "CPUExecutionProvider"),
        ):
            with patch.object(self.mod, "_probe_embedding_provider", return_value=result):
                with patch.dict(os.environ, {}, clear=True):
                    decision = self.mod.report_embedding_provider_decision()
        self.assertEqual(decision.selected_provider, "CoreMLExecutionProvider")
        self.assertEqual(decision.providers, ("CoreMLExecutionProvider", "CPUExecutionProvider"))

    def test_report_embedding_provider_decision_falls_back_when_coreml_probe_fails(self):
        result = self.mod.provider_policy.ProviderProbeResult(
            "CoreMLExecutionProvider",
            False,
            "candidate did not beat CPU by 1.25x",
        )
        with patch.object(
            self.mod.provider_policy,
            "available_onnx_providers",
            return_value=("CoreMLExecutionProvider", "CPUExecutionProvider"),
        ):
            with patch.object(self.mod, "_probe_embedding_provider", return_value=result):
                with patch.dict(os.environ, {}, clear=True):
                    stdout = io.StringIO()
                    with redirect_stdout(stdout):
                        decision = self.mod.report_embedding_provider_decision()
        self.assertEqual(decision.selected_provider, "CPUExecutionProvider")
        self.assertIn("candidate did not beat CPU", stdout.getvalue())

    def test_provider_policy_selects_named_secondary_provider_after_probe(self):
        def probe(provider: str):
            return self.mod.provider_policy.ProviderProbeResult(provider, True, f"{provider} ok")

        with patch.dict(os.environ, {}, clear=True):
            decision = self.mod.provider_policy.select_embedding_providers(
                available_providers=("OpenVINOExecutionProvider", "CPUExecutionProvider"),
                provider_probe=probe,
            )
        self.assertEqual(decision.selected_provider, "OpenVINOExecutionProvider")
        self.assertNotIn("Generic", decision.reason)

    def test_provider_policy_reports_nvidia_remediation_when_cuda_missing(self):
        with patch.object(self.mod.provider_policy, "nvidia_gpu_present", return_value=True):
            with patch.dict(os.environ, {}, clear=True):
                decision = self.mod.provider_policy.select_embedding_providers(
                    available_providers=("CPUExecutionProvider",),
                    provider_probe=lambda provider: self.mod.provider_policy.ProviderProbeResult(provider, False, "nope"),
                )
        self.assertEqual(decision.selected_provider, "CPUExecutionProvider")
        self.assertIsNotNone(decision.remediation)
        assert decision.remediation is not None
        self.assertIn("NVIDIA GPU detected", decision.remediation)

    def test_coreml_probe_accepts_on_correctness_without_speedup_gate(self):
        """Wave 1p4u1: CoreML passes the embedding probe on correctness alone — it is NOT required to
        beat CPU by the 1.25x speedup margin (CoreML partitions unsupported ops to CPU; a tiny probe
        is unrepresentative). Other probed providers (e.g. OpenVINO) STILL require the speedup gate."""
        import time as _t
        import fastembed

        class _FakeEmbed:
            def __init__(self, *a, **k):
                pass

            def embed(self, texts):
                return [[0.1, 0.2] for _ in texts]

        # 4 perf_counter calls per probe: cpu(start,end)=0.0,0.9 → 0.9s; candidate(start,end)=0.0,1.0
        # → 1.0s (SLOWER than CPU, ratio 0.9 < 1.25). Two probes → 8 values.
        seq = [0.0, 0.9, 0.0, 1.0, 0.0, 0.9, 0.0, 1.0]
        with patch.object(fastembed, "TextEmbedding", _FakeEmbed), \
                patch.object(_t, "perf_counter", side_effect=seq), \
                patch.dict(os.environ, {}, clear=True):
            coreml = self.mod._probe_embedding_provider(
                self.mod.provider_policy.COREML_PROVIDER, model_name="m")
            other = self.mod._probe_embedding_provider("OpenVINOExecutionProvider", model_name="m")
        self.assertTrue(coreml.ok, coreml.reason)
        self.assertIn("not a speedup gate", coreml.reason)
        self.assertIn("micro-benchmark", coreml.reason)  # 1p6et: timing labelled non-representative
        self.assertFalse(other.ok, other.reason)
        self.assertIn("did not beat CPU", other.reason)

    def test_prewarm_models_warms_then_verifies_offline(self):
        # Wave 1p52p: prewarm_models warms only the embedding models. The reranker is the GPU-only
        # FP16 accel reranker, prewarmed in _prewarm_gpu_accel (not via fastembed _warm_reranker,
        # which was removed) — so it is NOT warmed here.
        with patch.object(self.mod, "_indexer_models", return_value=["model-a", "model-b"]):
            with patch.object(self.mod, "_warm_model") as warm:
                with redirect_stdout(io.StringIO()):
                    self.mod.prewarm_models(include_code=True)

        self.assertEqual(
            warm.call_args_list,
            [
                call("model-a", local_files_only=False),
                call("model-a", local_files_only=True),
                call("model-b", local_files_only=False),
                call("model-b", local_files_only=True),
            ],
        )

    def test_prewarm_models_restores_offline_env(self):
        os.environ.pop("HF_HUB_OFFLINE", None)
        with patch.object(self.mod, "_indexer_models", return_value=["model-a"]):
            with patch.object(self.mod, "_warm_model"):
                with redirect_stdout(io.StringIO()):
                    self.mod.prewarm_models(include_code=False)
        self.assertNotIn("HF_HUB_OFFLINE", os.environ)

    def test_prewarm_required_model_quarantines_corrupt_cache_and_retries_once(self):
        calls: list[tuple[str, bool]] = []

        def warm(model_name, *, local_files_only):
            calls.append((model_name, local_files_only))
            if len(calls) == 1:
                raise RuntimeError("broken cache")

        with patch.object(self.mod, "_model_cache_corruption_reason", side_effect=["broken symlink", None]):
            with patch.object(self.mod, "_quarantine_model_cache", return_value=Path("/tmp/cache.broken")) as quarantine:
                with redirect_stdout(io.StringIO()):
                    self.mod._prewarm_required_model(
                        "model-a",
                        model_kind="embedding",
                        action="semantic index setup",
                        warm_fn=warm,
                    )

        quarantine.assert_called_once_with("model-a")
        self.assertEqual(
            calls,
            [
                ("model-a", False),
                ("model-a", False),
                ("model-a", True),
            ],
        )

    def test_prewarm_required_model_raises_clean_error_on_network_failure(self):
        def warm(model_name, *, local_files_only):
            raise RuntimeError("httpx.ConnectError: nodename nor servname provided, or not known")

        with patch.object(self.mod, "_model_cache_corruption_reason", return_value=None):
            with self.assertRaises(self.mod.ModelPrewarmError) as raised:
                self.mod._prewarm_required_model(
                    "model-a",
                    model_kind="embedding",
                    action="semantic index setup",
                    warm_fn=warm,
                )

        message = str(raised.exception)
        self.assertIn("Required embedding model 'model-a' could not be prepared", message)
        self.assertIn("network or download host unavailable", message)
        self.assertIn("Underlying error:", message)

    def test_main_returns_2_on_model_prewarm_error(self):
        with patch.object(self.mod, "_reexec_with_venv_if_needed"):
            with patch.object(self.mod, "ensure_deps"):
                with patch.object(self.mod, "prewarm_models", side_effect=self.mod.ModelPrewarmError("boom")):
                    with patch.object(self.mod, "build_index") as build_index:
                        with redirect_stdout(io.StringIO()):
                            with redirect_stderr(io.StringIO()):
                                rc = self.mod.main(["--root", "/tmp/repo"])
        self.assertEqual(rc, 2)
        build_index.assert_not_called()

    def test_model_cache_corruption_reason_detects_incomplete_blob_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_root = Path(tmp)
            model_dir = cache_root / "models--org--model"
            onnx_dir = model_dir / "snapshots" / "rev1" / "onnx"
            blobs_dir = model_dir / "blobs"
            onnx_dir.mkdir(parents=True, exist_ok=True)
            blobs_dir.mkdir(parents=True, exist_ok=True)
            target = blobs_dir / "abc123.incomplete"
            target.write_bytes(b"")
            (onnx_dir / "model.onnx").symlink_to(Path("../../../blobs/abc123.incomplete"))

            with patch.dict(os.environ, {"FASTEMBED_CACHE_PATH": str(cache_root)}):
                reason = self.mod._model_cache_corruption_reason("org/model")

        self.assertIsNotNone(reason)
        self.assertIn("incomplete", reason)

    def test_model_cache_corruption_reason_detects_embedding_alias_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_root = Path(tmp)
            model_dir = cache_root / "models--qdrant--bge-small-en-v1.5-onnx-q"
            onnx_dir = model_dir / "snapshots" / "rev1" / "onnx"
            blobs_dir = model_dir / "blobs"
            onnx_dir.mkdir(parents=True, exist_ok=True)
            blobs_dir.mkdir(parents=True, exist_ok=True)
            target = blobs_dir / "abc123.incomplete"
            target.write_bytes(b"")
            (onnx_dir / "model.onnx").symlink_to(Path("../../../blobs/abc123.incomplete"))

            with patch.dict(os.environ, {"FASTEMBED_CACHE_PATH": str(cache_root)}):
                reason = self.mod._model_cache_corruption_reason("BAAI/bge-small-en-v1.5")

        self.assertIsNotNone(reason)
        self.assertIn("incomplete", reason)

    def test_quarantine_model_cache_uses_existing_embedding_alias_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_root = Path(tmp)
            model_dir = cache_root / "models--qdrant--bge-small-en-v1.5-onnx-q"
            model_dir.mkdir(parents=True, exist_ok=True)
            (model_dir / "marker.txt").write_text("ok", encoding="utf-8")

            with patch.dict(os.environ, {"FASTEMBED_CACHE_PATH": str(cache_root)}):
                quarantined = self.mod._quarantine_model_cache("BAAI/bge-small-en-v1.5")
                self.assertIsNotNone(quarantined)
                self.assertFalse(model_dir.exists())
                assert quarantined is not None
                self.assertTrue(quarantined.exists())
                self.assertTrue(quarantined.name.startswith("models--qdrant--bge-small-en-v1.5-onnx-q.broken."))

    def test_model_cache_corruption_reason_ignores_missing_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"FASTEMBED_CACHE_PATH": tmp}):
                reason = self.mod._model_cache_corruption_reason("org/model")
        self.assertIsNone(reason)

    def test_model_cache_corruption_reason_detects_missing_onnx_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_root = Path(tmp)
            model_dir = cache_root / "models--org--model"
            (model_dir / "snapshots" / "rev1" / "onnx").mkdir(parents=True, exist_ok=True)
            with patch.dict(os.environ, {"FASTEMBED_CACHE_PATH": str(cache_root)}):
                reason = self.mod._model_cache_corruption_reason("org/model")
        self.assertIsNotNone(reason)
        self.assertIn("missing onnx model artifact", reason)

    def test_model_cache_corruption_reason_detects_zero_byte_plain_onnx(self):
        # 1p6d6: Windows COPIES the HF cache (symlinks need Developer Mode / admin), so a truncated
        # artifact is a PLAIN zero-byte .onnx — the symlink-gated zero-byte checks never fire. The
        # snapshot check must validate plain files too, else a corrupt cache passes on Windows.
        with tempfile.TemporaryDirectory() as tmp:
            cache_root = Path(tmp)
            onnx_dir = cache_root / "models--org--model" / "snapshots" / "rev1" / "onnx"
            onnx_dir.mkdir(parents=True, exist_ok=True)
            (onnx_dir / "model.onnx").write_bytes(b"")  # plain zero-byte file, NOT a symlink
            with patch.dict(os.environ, {"FASTEMBED_CACHE_PATH": str(cache_root)}):
                reason = self.mod._model_cache_corruption_reason("org/model")
        self.assertIsNotNone(reason)
        self.assertIn("zero-byte onnx model artifact", reason)

    def test_model_cache_corruption_reason_accepts_nonempty_plain_onnx(self):
        # No false positive: a real (non-empty) plain-file .onnx cache is clean.
        with tempfile.TemporaryDirectory() as tmp:
            cache_root = Path(tmp)
            onnx_dir = cache_root / "models--org--model" / "snapshots" / "rev1" / "onnx"
            onnx_dir.mkdir(parents=True, exist_ok=True)
            (onnx_dir / "model.onnx").write_bytes(b"onnxdata")
            with patch.dict(os.environ, {"FASTEMBED_CACHE_PATH": str(cache_root)}):
                reason = self.mod._model_cache_corruption_reason("org/model")
        self.assertIsNone(reason)

    def test_prewarm_required_model_quarantines_and_retries_once(self):
        calls = {"count": 0}

        def warm_fn(model_name, local_files_only):
            calls["count"] += 1
            if calls["count"] == 1 and not local_files_only:
                raise RuntimeError("missing onnx model.onnx")

        with patch.object(self.mod, "_model_cache_corruption_reason", return_value="missing onnx model artifact"):
            with patch.object(self.mod, "_quarantine_model_cache", return_value=Path("/tmp/quarantine")) as quarantine:
                self.mod._prewarm_required_model(
                    "Snowflake/snowflake-arctic-embed-xs",
                    model_kind="embedding",
                    action="semantic index setup",
                    warm_fn=warm_fn,
                )

        quarantine.assert_called_once_with("Snowflake/snowflake-arctic-embed-xs")
        self.assertEqual(calls["count"], 3)

    def test_main_prewarms_before_building_index(self):
        with patch.object(self.mod, "_reexec_with_venv_if_needed"):
            with patch.object(self.mod, "ensure_deps") as ensure_deps:
                with patch.object(self.mod, "prewarm_models") as prewarm:
                    with patch.object(self.mod, "build_index") as build_index:
                        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
                            stdout = io.StringIO()
                            with redirect_stdout(stdout):
                                rc = self.mod.main(["--root", "/tmp/repo", "--include-code"])

        self.assertEqual(rc, 0)
        ensure_deps.assert_called_once()
        prewarm.assert_called_once_with(include_code=True)
        build_index.assert_called_once()
        self.assertIn("Done. Project index update complete.", stdout.getvalue())
        self.assertIn("MCP handoff:", stdout.getvalue())
        # Wave 1p7tz: the bin/mcp-server wrapper was retired; the handoff now points at the committed
        # config (`python3 .wavefoundry/framework/scripts/server.py`).
        self.assertIn(".wavefoundry/framework/scripts/server.py", stdout.getvalue())
        self.assertNotIn("bin/mcp-server", stdout.getvalue())
        self.assertNotIn("python3 ", stdout.getvalue())

    def test_workflow_project_include_prefixes_defaults_empty(self):
        root = Path("/tmp/wavefoundry-missing-config")
        with patch.object(Path, "exists", return_value=False):
            result = self.mod._workflow_project_include_prefixes(root)
        self.assertEqual(result["docs"], ())
        self.assertEqual(result["code"], ())

    def test_workflow_project_include_prefixes_reads_generic_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = root / "docs" / "workflow-config.json"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(
                '{"indexing":{"project_include_prefixes":{"docs":["docs/external"],"code":[".wavefoundry/framework/scripts","vendor/docs"]}}}',
                encoding="utf-8",
            )
            result = self.mod._workflow_project_include_prefixes(root)
        self.assertEqual(result["docs"], ("docs/external",))
        self.assertEqual(result["code"], (".wavefoundry/framework/scripts", "vendor/docs"))

    def test_workflow_project_include_prefixes_accepts_list_shorthand(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = root / "docs" / "workflow-config.json"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(
                '{"indexing":{"project_include_prefixes":[".wavefoundry/framework/scripts","vendor/docs"]}}',
                encoding="utf-8",
            )
            result = self.mod._workflow_project_include_prefixes(root)
        self.assertEqual(result["docs"], (".wavefoundry/framework/scripts", "vendor/docs"))
        self.assertEqual(result["code"], (".wavefoundry/framework/scripts", "vendor/docs"))

    def test_workflow_project_include_prefixes_supports_legacy_boolean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = root / "docs" / "workflow-config.json"
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(
                '{"indexing":{"include_framework_code_for_code_search":true}}',
                encoding="utf-8",
            )
            result = self.mod._workflow_project_include_prefixes(root)
        self.assertEqual(result["docs"], ())
        self.assertEqual(result["code"], (".wavefoundry/framework/scripts",))


class IndexerToolVenvTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_indexer()

    def test_auto_install_lancedb_uses_tool_venv_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv_root = Path(tmp)
            venv_python = venv_root / "bin" / "python"
            venv_python.parent.mkdir(parents=True, exist_ok=True)
            venv_python.write_text("", encoding="utf-8")
            with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_root)}):
                with patch("subprocess.run", return_value=MagicMock(returncode=0)) as run_mock:
                    with redirect_stdout(io.StringIO()):
                        self.mod._auto_install_lancedb()
        cmd = run_mock.call_args.args[0]
        self.assertEqual(cmd[0], str(venv_python))
        self.assertNotEqual(cmd[0], sys.executable)

    def test_auto_install_lancedb_requires_bootstrapped_venv(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": tmp}):
                with self.assertRaises(ImportError) as raised:
                    self.mod._auto_install_lancedb()
        self.assertIn("tool venv is not bootstrapped", str(raised.exception))


class BackgroundCodeTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_setup_index()

    def test_background_code_prewarms_docs_only(self):
        """--background-code must not prewarm the code model in the foreground."""
        with patch.object(self.mod, "ensure_deps"):
            with patch.object(self.mod, "_reexec_with_venv_if_needed"):
                with patch.object(self.mod, "prewarm_models") as prewarm:
                    with patch.object(self.mod, "build_index"):
                        with patch.object(self.mod, "_spawn_background_code_build"):
                            with redirect_stdout(io.StringIO()):
                                self.mod.main(["--root", "/tmp/repo", "--background-code"])
        prewarm.assert_called_once_with(include_code=False)

    def test_background_code_builds_docs_only_in_foreground(self):
        """--background-code must call build_index with include_code=False."""
        with patch.object(self.mod, "ensure_deps"):
            with patch.object(self.mod, "_reexec_with_venv_if_needed"):
                with patch.object(self.mod, "prewarm_models"):
                    with patch.object(self.mod, "build_index") as build_index:
                        with patch.object(self.mod, "_spawn_background_code_build"):
                            with redirect_stdout(io.StringIO()):
                                self.mod.main(["--root", "/tmp/repo", "--background-code"])
        _, kwargs = build_index.call_args
        self.assertFalse(kwargs.get("include_code", True))

    def test_background_code_spawns_background_process(self):
        """--background-code must call _spawn_background_code_build after docs build."""
        with patch.object(self.mod, "ensure_deps"):
            with patch.object(self.mod, "_reexec_with_venv_if_needed"):
                with patch.object(self.mod, "prewarm_models"):
                    with patch.object(self.mod, "build_index"):
                        with patch.object(self.mod, "_spawn_background_code_build") as spawn:
                            with redirect_stdout(io.StringIO()):
                                self.mod.main(["--root", "/tmp/repo", "--background-code"])
        spawn.assert_called_once()

    def test_include_code_takes_precedence_over_background_code(self):
        """--include-code with --background-code should behave as --include-code (synchronous)."""
        with patch.object(self.mod, "ensure_deps"):
            with patch.object(self.mod, "_reexec_with_venv_if_needed"):
                with patch.object(self.mod, "prewarm_models") as prewarm:
                    with patch.object(self.mod, "build_index") as build_index:
                        with patch.object(self.mod, "_spawn_background_code_build") as spawn:
                            with redirect_stdout(io.StringIO()):
                                self.mod.main(["--root", "/tmp/repo", "--include-code", "--background-code"])
        prewarm.assert_called_once_with(include_code=True)
        _, kwargs = build_index.call_args
        self.assertTrue(kwargs.get("include_code", False))
        spawn.assert_not_called()


class TlsTrustStoreFallbackTests(unittest.TestCase):
    """1p7iu: model-fetch OS-trust-store fallback on CERTIFICATE_VERIFY_FAILED (verification stays ON)."""

    def setUp(self):
        self.mod = load_setup_index()

    def test_is_cert_verify_error_detects_chain(self):
        inner = Exception("certificate verify failed: unable to get local issuer certificate")
        outer = RuntimeError("model download failed")
        outer.__cause__ = inner
        self.assertTrue(self.mod._is_cert_verify_error(outer))
        self.assertFalse(self.mod._is_cert_verify_error(RuntimeError("connection reset by peer")))

    def test_os_trust_store_bundle_honors_preset_env(self):
        with tempfile.NamedTemporaryFile(suffix=".crt") as f:
            with patch.dict(os.environ, {"SSL_CERT_FILE": f.name}, clear=False):
                for var in ("CODEX_CA_CERTIFICATE", "CLAUDE_CODE_CERT_STORE", "NODE_EXTRA_CA_CERTS", "REQUESTS_CA_BUNDLE"):
                    os.environ.pop(var, None)
                self.assertEqual(self.mod._os_trust_store_bundle(), f.name)

    # ── Wave 1p7s6: host-agent CA-bundle discovery ─────────────────────────────

    def _clear_ca_env(self):
        for var in ("CODEX_CA_CERTIFICATE", "CLAUDE_CODE_CERT_STORE", "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
            os.environ.pop(var, None)

    def test_each_ca_env_var_honored(self):
        # 1p7s6 AC-1/AC-4: every CA env var is a recognized candidate when it points at a real file.
        for var in ("CODEX_CA_CERTIFICATE", "CLAUDE_CODE_CERT_STORE", "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
            with self.subTest(var=var), tempfile.NamedTemporaryFile(suffix=".crt") as f:
                with patch.dict(os.environ, {}, clear=False):
                    self._clear_ca_env()
                    os.environ[var] = f.name
                    self.assertIn(f.name, self.mod._os_trust_store_candidates(),
                                  f"{var} should be a recognized CA candidate")

    def test_codex_var_takes_precedence_over_ssl_cert_file(self):
        # 1p7s6 AC-1/AC-4: CODEX_CA_CERTIFICATE beats a set SSL_CERT_FILE; SSL_CERT_FILE is PRESERVED
        # as a later candidate (operator's value is never silently discarded).
        with tempfile.NamedTemporaryFile(suffix=".crt") as codex, tempfile.NamedTemporaryFile(suffix=".crt") as ssl_:
            with patch.dict(os.environ, {}, clear=False):
                self._clear_ca_env()
                os.environ["CODEX_CA_CERTIFICATE"] = codex.name
                os.environ["SSL_CERT_FILE"] = ssl_.name
                candidates = self.mod._os_trust_store_candidates()
                self.assertEqual(self.mod._os_trust_store_bundle(), codex.name)  # codex wins
                self.assertLess(candidates.index(codex.name), candidates.index(ssl_.name))  # codex first
                self.assertIn(ssl_.name, candidates)  # operator SSL_CERT_FILE preserved as a candidate

    def test_node_extra_ca_certs_is_host_candidate_before_generic_ca_vars(self):
        with tempfile.NamedTemporaryFile(suffix=".crt") as node, tempfile.NamedTemporaryFile(suffix=".crt") as ssl_:
            with patch.dict(os.environ, {}, clear=False):
                self._clear_ca_env()
                os.environ["NODE_EXTRA_CA_CERTS"] = node.name
                os.environ["SSL_CERT_FILE"] = ssl_.name
                candidates = self.mod._os_trust_store_candidates()
                self.assertEqual(self.mod._os_trust_store_bundle(), node.name)
                self.assertLess(candidates.index(node.name), candidates.index(ssl_.name))

    def test_candidates_end_with_certifi_default(self):
        # 1p7s6 Req 5: certifi default is the LAST resort.
        with patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            certifi_default = self.mod._certifi_default_bundle()
            candidates = self.mod._os_trust_store_candidates()
            if certifi_default is not None:
                self.assertIn(certifi_default, candidates)
                self.assertEqual(candidates[-1], certifi_default, "certifi default must be the last candidate")

    def test_warm_model_proactive_preconfig_skips_failed_first_attempt(self):
        # 1p7s6 AC-2: a host-agent var set + stack CA unset → the bundle is configured BEFORE the first
        # attempt, so the first _build() succeeds (no guaranteed-fail certifi round-trip).
        good = MagicMock()
        good.embed.return_value = iter([[0.1, 0.2]])
        te = MagicMock(return_value=good)  # first attempt succeeds (proactive bundle already applied)
        hf = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".crt") as codex, \
             patch.dict(os.environ, {}, clear=False), \
             patch.object(self.mod, "_embedding_providers_for_setup", return_value=["CPUExecutionProvider"]), \
             patch.dict(sys.modules, {"fastembed": MagicMock(TextEmbedding=te), "huggingface_hub": hf}):
            self._clear_ca_env()
            os.environ["CODEX_CA_CERTIFICATE"] = codex.name
            self.mod._warm_model("BAAI/bge-small-en-v1.5", local_files_only=False)
            self.assertEqual(te.call_count, 1, "proactive pre-config must make the first attempt succeed")
            # Configured from the host-agent bundle BEFORE the first attempt.
            self.assertEqual(os.environ.get("SSL_CERT_FILE"), codex.name)
            self.assertEqual(os.environ.get("REQUESTS_CA_BUNDLE"), codex.name)
            hf.close_session.assert_called()  # session rebuilt for the proactive bundle

    def test_warm_model_iterates_to_platform_store_when_host_bundle_fails(self):
        # 1p7s6 AC-2/Req 5: a host-agent bundle that ITSELF fails cert-verify degrades to the next
        # candidate (the platform store) rather than hard-failing.
        cert_exc = Exception("SSLError: certificate verify failed: unable to get local issuer certificate")
        good = MagicMock()
        good.embed.return_value = iter([[0.1, 0.2]])
        # proactive attempt (host bundle) fails cert; iteration to platform store succeeds.
        te = MagicMock(side_effect=[cert_exc, good])
        hf = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".crt") as codex, \
             patch.dict(os.environ, {}, clear=False), \
             patch.object(self.mod, "_os_trust_store_candidates",
                          return_value=[codex.name, "/etc/ssl/certs/platform.crt"]), \
             patch.object(self.mod, "_host_agent_ca_bundle", return_value=codex.name), \
             patch.object(self.mod, "_embedding_providers_for_setup", return_value=["CPUExecutionProvider"]), \
             patch.dict(sys.modules, {"fastembed": MagicMock(TextEmbedding=te), "huggingface_hub": hf}):
            self._clear_ca_env()
            os.environ["CODEX_CA_CERTIFICATE"] = codex.name
            self.mod._warm_model("BAAI/bge-small-en-v1.5", local_files_only=False)
            self.assertEqual(te.call_count, 2, "host bundle fails → iterate to platform store")
            # Winning (platform) bundle left in place (operator stack env was unset).
            self.assertEqual(os.environ.get("SSL_CERT_FILE"), "/etc/ssl/certs/platform.crt")

    def test_warm_model_iterates_to_certifi_default_last(self):
        # 1p7s6 Req 5/AC-4: when host + platform candidates fail, the certifi default is the last resort.
        cert_exc = Exception("SSLError: certificate verify failed: unable to get local issuer certificate")
        good = MagicMock()
        good.embed.return_value = iter([[0.1, 0.2]])
        # certifi-default is the last candidate; host + platform fail, certifi succeeds.
        te = MagicMock(side_effect=[cert_exc, cert_exc, good])
        hf = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".crt") as codex, \
             patch.dict(os.environ, {}, clear=False), \
             patch.object(self.mod, "_os_trust_store_candidates",
                          return_value=[codex.name, "/etc/ssl/certs/platform.crt", "/certifi/cacert.pem"]), \
             patch.object(self.mod, "_host_agent_ca_bundle", return_value=codex.name), \
             patch.object(self.mod, "_certifi_default_bundle", return_value="/certifi/cacert.pem"), \
             patch.object(self.mod, "_embedding_providers_for_setup", return_value=["CPUExecutionProvider"]), \
             patch.dict(sys.modules, {"fastembed": MagicMock(TextEmbedding=te), "huggingface_hub": hf}):
            self._clear_ca_env()
            os.environ["CODEX_CA_CERTIFICATE"] = codex.name
            self.mod._warm_model("BAAI/bge-small-en-v1.5", local_files_only=False)
            self.assertEqual(te.call_count, 3, "iterate host → platform → certifi default last")
            self.assertEqual(os.environ.get("SSL_CERT_FILE"), "/certifi/cacert.pem")

    def test_warm_model_retries_with_os_bundle_on_cert_failure(self):
        # 1p7s6: reactive path (no host-agent var) — first attempt (certifi) fails, candidate iteration
        # tries the resolved OS bundle and succeeds.
        cert_exc = Exception("SSLError: certificate verify failed: unable to get local issuer certificate")
        good = MagicMock()
        good.embed.return_value = iter([[0.1, 0.2]])
        te = MagicMock(side_effect=[cert_exc, good])  # first ctor raises cert error, retry returns good
        hf = MagicMock()
        with patch.dict(os.environ, {}, clear=False), \
             patch.object(self.mod, "_os_trust_store_candidates", return_value=["/os/ca.crt"]), \
             patch.object(self.mod, "_certifi_default_bundle", return_value=None), \
             patch.object(self.mod, "_embedding_providers_for_setup", return_value=["CPUExecutionProvider"]), \
             patch.dict(sys.modules, {"fastembed": MagicMock(TextEmbedding=te), "huggingface_hub": hf}):
            self._clear_ca_env()
            self.mod._warm_model("BAAI/bge-small-en-v1.5", local_files_only=False)
            self.assertEqual(te.call_count, 2, "should retry once after the cert failure")
            self.assertEqual(os.environ.get("SSL_CERT_FILE"), "/os/ca.crt")
            self.assertEqual(os.environ.get("REQUESTS_CA_BUNDLE"), "/os/ca.crt")
            # CRITICAL: hf_hub caches a global httpx.Client whose SSL context is built once against
            # certifi — without resetting it, the env change is a no-op and the retry fails identically.
            hf.close_session.assert_called()

    def test_warm_model_restores_operator_env_after_run(self):
        # 1p7s6 Req 2/3: a set operator SSL_CERT_FILE is never silently discarded — per-attempt env
        # mutation is scoped and the operator's original value survives the function.
        cert_exc = Exception("SSLError: certificate verify failed: unable to get local issuer certificate")
        good = MagicMock()
        good.embed.return_value = iter([[0.1, 0.2]])
        te = MagicMock(side_effect=[cert_exc, good])
        hf = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".crt") as operator_ca, \
             patch.dict(os.environ, {}, clear=False), \
             patch.object(self.mod, "_os_trust_store_candidates",
                          return_value=[operator_ca.name, "/etc/ssl/certs/platform.crt"]), \
             patch.object(self.mod, "_certifi_default_bundle", return_value=None), \
             patch.object(self.mod, "_embedding_providers_for_setup", return_value=["CPUExecutionProvider"]), \
             patch.dict(sys.modules, {"fastembed": MagicMock(TextEmbedding=te), "huggingface_hub": hf}):
            self._clear_ca_env()
            os.environ["SSL_CERT_FILE"] = operator_ca.name  # operator's explicit setting
            self.mod._warm_model("BAAI/bge-small-en-v1.5", local_files_only=False)
            # Operator's original SSL_CERT_FILE survives (restored after the iteration swapped it).
            self.assertEqual(os.environ.get("SSL_CERT_FILE"), operator_ca.name)

    def test_warm_model_restores_operator_env_on_all_candidates_fail(self):
        # 1p7s6 pre-close (security): operator sets SSL_CERT_FILE; EVERY candidate fails cert-verify →
        # ModelPrewarmError, AND the operator's original SSL_CERT_FILE must be restored (never left
        # clobbered with a last-tried bundle — a leaked trust anchor).
        cert_exc = Exception("SSLError: certificate verify failed: unable to get local issuer certificate")
        te = MagicMock(side_effect=cert_exc)  # every attempt fails cert-verify
        hf = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".crt") as operator_ca, \
             patch.dict(os.environ, {}, clear=False), \
             patch.object(self.mod, "_os_trust_store_candidates",
                          return_value=[operator_ca.name, "/etc/ssl/certs/platform.crt", "/certifi/cacert.pem"]), \
             patch.object(self.mod, "_certifi_default_bundle", return_value=None), \
             patch.object(self.mod, "_embedding_providers_for_setup", return_value=["CPUExecutionProvider"]), \
             patch.dict(sys.modules, {"fastembed": MagicMock(TextEmbedding=te), "huggingface_hub": hf}):
            self._clear_ca_env()
            os.environ["SSL_CERT_FILE"] = operator_ca.name
            with self.assertRaises(self.mod.ModelPrewarmError):
                self.mod._warm_model("BAAI/bge-small-en-v1.5", local_files_only=False)
            self.assertEqual(os.environ.get("SSL_CERT_FILE"), operator_ca.name,
                             "operator SSL_CERT_FILE must survive an all-candidates-fail exit")

    def test_warm_model_restores_operator_env_on_non_cert_error_mid_retry(self):
        # 1p7s6 pre-close (security): operator sets SSL_CERT_FILE; first attempt cert-fails, a retry
        # candidate raises a NON-cert error (re-raised) → the operator's original env is still restored.
        cert_exc = Exception("SSLError: certificate verify failed: unable to get local issuer certificate")
        non_cert = RuntimeError("disk full")
        te = MagicMock(side_effect=[cert_exc, non_cert])  # first cert-fails, retry hits a non-cert error
        hf = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".crt") as operator_ca, \
             patch.dict(os.environ, {}, clear=False), \
             patch.object(self.mod, "_os_trust_store_candidates",
                          return_value=[operator_ca.name, "/etc/ssl/certs/platform.crt"]), \
             patch.object(self.mod, "_certifi_default_bundle", return_value=None), \
             patch.object(self.mod, "_embedding_providers_for_setup", return_value=["CPUExecutionProvider"]), \
             patch.dict(sys.modules, {"fastembed": MagicMock(TextEmbedding=te), "huggingface_hub": hf}):
            self._clear_ca_env()
            os.environ["SSL_CERT_FILE"] = operator_ca.name
            with self.assertRaises(RuntimeError):
                self.mod._warm_model("BAAI/bge-small-en-v1.5", local_files_only=False)
            self.assertEqual(os.environ.get("SSL_CERT_FILE"), operator_ca.name,
                             "operator SSL_CERT_FILE must survive a non-cert-error retry exit")

    def test_warm_model_does_not_retry_non_cert_error(self):
        te = MagicMock(side_effect=RuntimeError("disk full"))
        with patch.object(self.mod, "_embedding_providers_for_setup", return_value=["CPUExecutionProvider"]), \
             patch.dict(sys.modules, {"fastembed": MagicMock(TextEmbedding=te)}):
            with self.assertRaises(RuntimeError):
                self.mod._warm_model("m", local_files_only=False)
            self.assertEqual(te.call_count, 1, "non-cert errors must not trigger the OS-bundle retry")

    def test_no_path_disables_tls_verification(self):
        # 1p7iu AC-3: the fallback only swaps the CA bundle — it must NEVER disable verification.
        src = SETUP_INDEX_PATH.read_text(encoding="utf-8")
        self.assertNotIn("_create_unverified_context", src)
        self.assertNotIn("CERT_NONE", src)
        self.assertNotIn("verify=False", src)


if __name__ == "__main__":
    unittest.main()
