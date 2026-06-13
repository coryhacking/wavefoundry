from __future__ import annotations

import importlib.util
import io
import os
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
        """_bootstrap_venv creates the venv when the directory does not exist."""
        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("subprocess.check_call") as check_call:
                    with redirect_stdout(io.StringIO()):
                        result = self.mod._bootstrap_venv()

        check_call.assert_called_once()
        cmd = check_call.call_args[0][0]
        self.assertIn("-m", cmd)
        self.assertIn("venv", cmd)
        self.assertEqual(result, FAKE_VENV_PYTHON)

    def test_bootstrap_venv_skips_creation_when_python_exists(self):
        """_bootstrap_venv does not call venv when the Python binary already exists."""
        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("subprocess.check_call") as check_call:
                    with redirect_stdout(io.StringIO()):
                        result = self.mod._bootstrap_venv()

        check_call.assert_not_called()
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
                    with patch("subprocess.check_call"):
                        with redirect_stdout(io.StringIO()):
                            self.mod._bootstrap_venv()

        rmtree.assert_called_once_with(venv_dir, ignore_errors=True)


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
        self.assertIn(".wavefoundry/bin/mcp-server", stdout.getvalue())
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


if __name__ == "__main__":
    unittest.main()
