from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import types
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, call, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
SETUP_INDEX_PATH = SCRIPTS_ROOT / "setup_index.py"
PYPROJECT_PATH = SCRIPTS_ROOT.parents[2] / "pyproject.toml"

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


class VersionAwareDependencyTests(unittest.TestCase):
    """Wave 1p95u — `_missing_in_venv` flags a dependency whose installed version violates its pin,
    not only an absent one, so a pinned version bump reaches existing installs on setup/upgrade.

    The version-logic cases run the REAL probe against the current interpreter (`sys.executable` — the
    tool venv under run_tests.py, which has `packaging` + the deps), so they exercise the actual
    subprocess probe rather than a mock. The degradation/install/chokepoint cases are mocked.
    """

    def setUp(self):
        self.mod = load_setup_index()
        self.interp = Path(sys.executable)

    def _installed(self, dist: str) -> str:
        import importlib.metadata as m
        return m.version(dist)

    def test_violated_exact_pin_flagged(self):
        # AC-1: an installed dep pinned to a version it does not match is flagged, with the full spec.
        result = self.mod._missing_in_venv(self.interp, {"lancedb==999.0.0": "lancedb"})
        self.assertIn("lancedb==999.0.0", result)

    def test_satisfied_exact_pin_not_flagged(self):
        # AC-1/AC-2: an installed dep pinned to exactly its installed version is NOT flagged.
        spec = f"lancedb=={self._installed('lancedb')}"
        self.assertEqual(self.mod._missing_in_venv(self.interp, {spec: "lancedb"}), [])

    def test_satisfied_range_pin_not_flagged(self):
        # AC-2: a range pin that the installed version satisfies is NOT flagged (no churn).
        self.assertEqual(
            self.mod._missing_in_venv(self.interp, {"lancedb>=0.1,<9999": "lancedb"}), []
        )

    def test_unpinned_present_not_flagged(self):
        # AC-2: an installed, unpinned dep keeps presence-only behavior (not flagged).
        self.assertEqual(self.mod._missing_in_venv(self.interp, {"numpy": "numpy"}), [])

    def test_unpinned_absent_flagged(self):
        # AC-2: an absent dep is still flagged (presence check preserved).
        result = self.mod._missing_in_venv(
            self.interp, {"totally-not-real-pkg-xyz": "totally_not_real_pkg_xyz"}
        )
        self.assertEqual(result, ["totally-not-real-pkg-xyz"])

    def test_unparseable_spec_degrades_to_presence_only(self):
        # AC-3: a spec `packaging` cannot parse falls back to presence-only for that dep — the present
        # package is NOT flagged and the probe never raises. This is the same fallback path taken when
        # `packaging` itself is unimportable in the venv.
        self.assertEqual(
            self.mod._missing_in_venv(self.interp, {"lancedb ??? not a spec": "lancedb"}), []
        )

    def test_real_required_imports_no_false_positives(self):
        # AC-5: with the REAL REQUIRED_IMPORTS and versions that satisfy every pin (incl. lancedb==0.33.0),
        # the probe returns no false positives — guards against reinstall churn on the real dep set.
        self.assertEqual(self.mod._missing_in_venv(self.interp), [])

    def test_probe_failure_returns_all_required_keys(self):
        # AC-3: if the probe subprocess fails, degrade to "reinstall everything" rather than raise.
        with patch.object(self.mod.subprocess_util, "isolated_run",
                          return_value=MagicMock(returncode=1, stdout="")):
            result = self.mod._missing_in_venv(FAKE_VENV_PYTHON, {"lancedb==0.33.0": "lancedb"})
        self.assertEqual(result, ["lancedb==0.33.0"])

    def test_install_deps_carries_pinned_spec(self):
        # AC-4: the flagged spec (e.g. lancedb==0.33.0) reaches the installer command verbatim, so an
        # existing older lancedb resolves to the pinned version.
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with redirect_stdout(io.StringIO()):
                self.mod._install_deps(["lancedb==0.33.0"], FAKE_VENV_PYTHON)
        cmds = [c[0][0] for c in mock_run.call_args_list]
        self.assertTrue(any("lancedb==0.33.0" in cmd for cmd in cmds),
                        f"pinned spec not found in any install command: {cmds}")

    def test_main_calls_ensure_deps_chokepoint(self):
        # AC-6: setup_index.main runs ensure_deps on every invocation — the chokepoint the upgrade's
        # phase-4 setup_index calls ride on, so the version-aware check propagates on upgrade with no
        # upgrade wiring. Locked so a refactor can't silently drop it off the upgrade path.
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.mod, "ensure_deps") as mock_ensure, \
                 patch.object(self.mod, "_reexec_with_venv_if_needed"), \
                 patch.object(self.mod, "_workflow_project_include_prefixes", return_value={}), \
                 patch.object(self.mod, "_run_indexer"):
                with redirect_stdout(io.StringIO()):
                    rc = self.mod.main(["--root", tmp, "--graph-only"])
        self.assertEqual(rc, 0)
        mock_ensure.assert_called_once()


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
        """_bootstrap_venv deletes and recreates a partial venv (dir exists but Python binary absent).

        Wave 1p9hk: removal now routes through _rmtree_clearing_readonly (read-only-safe) instead of
        shutil.rmtree(ignore_errors=True); after a successful removal the recreate proceeds. Uses a real
        temp dir so exists() reflects the actual removal (the new post-removal guard checks exists())."""
        with tempfile.TemporaryDirectory() as tmp:
            venv_dir = Path(tmp) / "venv"
            venv_python = venv_dir / "bin" / "python"
            venv_dir.mkdir(parents=True)  # dir exists, python binary absent → partial

            with patch.object(self.mod, "_tool_venv_python", return_value=venv_python):
                with patch("subprocess.run") as run:
                    run.return_value = subprocess.CompletedProcess([], 0)
                    with redirect_stdout(io.StringIO()):
                        result = self.mod._bootstrap_venv()

        self.assertEqual(result, venv_python)
        self.assertFalse(venv_dir.exists(), "partial venv should be removed before recreation")
        self.assertEqual(run.call_args[0][0], [sys.executable, "-m", "venv", str(venv_dir)])

    def test_bootstrap_venv_surfaces_error_when_removal_fails(self):
        """Wave 1p9hk (AC-2/AC-3): when the recreate-triggering rmtree cannot fully remove the venv
        (Windows: a .pyd/.dll held open by a running MCP host / IDE extension), _bootstrap_venv must
        raise an actionable error naming `wf setup` — NOT silently return a half-gutted venv_python
        (the old ignore_errors=True + `if not exists` gate dead-ended silently)."""
        with tempfile.TemporaryDirectory() as tmp:
            venv_dir = Path(tmp) / "venv"
            venv_python = venv_dir / "bin" / "python"
            venv_dir.mkdir(parents=True)  # partial venv: dir present, python absent

            with patch.object(self.mod, "_tool_venv_python", return_value=venv_python):
                # Simulate held-open files: the robust rmtree runs but cannot remove the directory.
                with patch.object(self.mod, "_rmtree_clearing_readonly"):  # no-op
                    with patch("subprocess.run") as run:
                        with redirect_stdout(io.StringIO()):
                            with self.assertRaises(RuntimeError) as ctx:
                                self.mod._bootstrap_venv()
        msg = str(ctx.exception)
        self.assertIn("wf setup", msg)
        self.assertIn(str(venv_dir), msg)
        run.assert_not_called()  # never proceeds to venv creation with a broken venv

    def test_rmtree_clearing_readonly_removes_readonly_tree(self):
        """Wave 1p9hk (AC-1/AC-4): _rmtree_clearing_readonly removes a tree containing a read-only file
        (the Windows failure mode) without raising."""
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            (tree / "sub").mkdir(parents=True)
            ro_file = tree / "sub" / "readonly.pyd"
            ro_file.write_text("x", encoding="utf-8")
            os.chmod(ro_file, 0o444)  # read-only
            try:
                self.mod._rmtree_clearing_readonly(tree)
            finally:
                # Best-effort restore if the removal did not complete (POSIX removes it fine).
                if ro_file.exists():
                    os.chmod(ro_file, 0o644)
            self.assertFalse(tree.exists(), "read-only tree must be fully removed")

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

        # Wave 1p9it: ensure_deps threads root through to _install_deps (root=None here — direct call).
        mock_install.assert_called_once_with(missing, FAKE_VENV_PYTHON, None)

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
        # Wave 1p95j: lancedb is pinned to a validated version via LANCEDB_REQUIREMENT.
        self.assertEqual(self.mod.LANCEDB_REQUIREMENT, "lancedb==0.33.0")
        self.assertIn(self.mod.LANCEDB_REQUIREMENT, self.mod.REQUIRED_IMPORTS)
        self.assertEqual(self.mod.REQUIRED_IMPORTS[self.mod.LANCEDB_REQUIREMENT], "lancedb")

    def test_required_imports_include_httpx_socks(self):
        self.assertIn("httpx[socks]", self.mod.REQUIRED_IMPORTS)
        self.assertEqual(self.mod.REQUIRED_IMPORTS["httpx[socks]"], "socksio")

    def test_pyproject_includes_httpx_socks(self):
        with PYPROJECT_PATH.open("rb") as fh:
            metadata = tomllib.load(fh)
        self.assertIn("httpx[socks]", metadata["project"]["dependencies"])

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
        prewarm.assert_called_once_with(include_code=True, code_only=False)
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


class SetupLayerSchedulingTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_setup_index()

    def _runtime_patches(self):
        stack = ExitStack()
        stack.enter_context(patch.object(self.mod, "ensure_deps"))
        stack.enter_context(patch.object(self.mod, "_reexec_with_venv_if_needed"))
        stack.enter_context(patch.object(self.mod, "report_embedding_provider_decision"))
        stack.enter_context(patch.object(self.mod, "_prewarm_gpu_accel"))
        return stack

    def test_default_setup_builds_docs_and_code_synchronously(self):
        """Default setup must treat docs and code the same: one foreground docs+code build."""
        with self._runtime_patches():
            with patch.object(self.mod, "prewarm_models") as prewarm:
                with patch.object(self.mod, "build_index") as build_index:
                    with patch.object(self.mod, "_spawn_background_code_build") as spawn:
                        with patch.object(self.mod, "_spawn_background_docs_build") as docs_spawn:
                            with redirect_stdout(io.StringIO()):
                                self.mod.main(["--root", "/tmp/repo"])
        prewarm.assert_called_once_with(include_code=True, code_only=False)
        _, kwargs = build_index.call_args
        self.assertTrue(kwargs.get("include_code", False))
        self.assertFalse(kwargs.get("code_only", False))
        spawn.assert_not_called()
        docs_spawn.assert_not_called()

    def test_background_code_prewarms_docs_only(self):
        """--background-code must not prewarm the code model in the foreground."""
        with self._runtime_patches():
            with patch.object(self.mod, "prewarm_models") as prewarm:
                with patch.object(self.mod, "build_index"):
                    with patch.object(self.mod, "_spawn_background_code_build"):
                        with redirect_stdout(io.StringIO()):
                            self.mod.main(["--root", "/tmp/repo", "--background-code"])
        prewarm.assert_called_once_with(include_code=False, code_only=False)

    def test_background_code_builds_docs_only_in_foreground(self):
        """--background-code must call build_index with include_code=False and code_only=False."""
        with self._runtime_patches():
            with patch.object(self.mod, "prewarm_models"):
                with patch.object(self.mod, "build_index") as build_index:
                    with patch.object(self.mod, "_spawn_background_code_build"):
                        with redirect_stdout(io.StringIO()):
                            self.mod.main(["--root", "/tmp/repo", "--background-code"])
        _, kwargs = build_index.call_args
        self.assertFalse(kwargs.get("include_code", True))
        self.assertFalse(kwargs.get("code_only", True))

    def test_background_code_spawns_background_process(self):
        """--background-code must call _spawn_background_code_build after docs build."""
        with self._runtime_patches():
            with patch.object(self.mod, "prewarm_models"):
                with patch.object(self.mod, "build_index"):
                    with patch.object(self.mod, "_spawn_background_code_build") as spawn:
                        with redirect_stdout(io.StringIO()):
                            self.mod.main(["--root", "/tmp/repo", "--background-code"])
        spawn.assert_called_once()

    def test_detached_layer_does_not_inherit_memory_publication_receipt(self):
        args = MagicMock(
            full=False,
            rechunk=False,
            include_tests=False,
            include_generated=False,
            verbose=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath(".wavefoundry", "index").mkdir(parents=True)
            with patch.dict(
                os.environ,
                {"WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID": "run-receipt"},
            ), patch.object(
            self.mod.subprocess_util,
            "windowless_pythonw",
            return_value=None,
            ), patch.object(
            self.mod,
            "_tool_venv_python",
            return_value=Path(sys.executable),
            ), patch.object(
            self.mod.subprocess_util,
            "isolated_popen",
            return_value=MagicMock(pid=123),
            ) as popen:
                self.mod._spawn_background_semantic_build(root, args, "code")
        child_env = popen.call_args.kwargs["env"]
        self.assertNotIn("WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID", child_env)

    def test_include_code_takes_precedence_over_background_code(self):
        """--include-code with --background-code should behave as --include-code (synchronous)."""
        with self._runtime_patches():
            with patch.object(self.mod, "prewarm_models") as prewarm:
                with patch.object(self.mod, "build_index") as build_index:
                    with patch.object(self.mod, "_spawn_background_code_build") as spawn:
                        with redirect_stdout(io.StringIO()):
                            self.mod.main(["--root", "/tmp/repo", "--include-code", "--background-code"])
        prewarm.assert_called_once_with(include_code=True, code_only=False)
        _, kwargs = build_index.call_args
        self.assertTrue(kwargs.get("include_code", False))
        self.assertFalse(kwargs.get("code_only", False))
        spawn.assert_not_called()

    def test_background_docs_prewarms_code_model_only(self):
        """--background-docs must not prewarm the docs model in the foreground."""
        with self._runtime_patches():
            with patch.object(self.mod, "prewarm_models") as prewarm:
                with patch.object(self.mod, "build_index"):
                    with patch.object(self.mod, "_spawn_background_docs_build"):
                        with redirect_stdout(io.StringIO()):
                            self.mod.main(["--root", "/tmp/repo", "--background-docs"])
        prewarm.assert_called_once_with(include_code=True, code_only=True)

    def test_background_docs_builds_code_only_in_foreground(self):
        """--background-docs must build only the code layer before spawning docs."""
        with self._runtime_patches():
            with patch.object(self.mod, "prewarm_models"):
                with patch.object(self.mod, "build_index") as build_index:
                    with patch.object(self.mod, "_spawn_background_docs_build"):
                        with redirect_stdout(io.StringIO()):
                            self.mod.main(["--root", "/tmp/repo", "--background-docs"])
        _, kwargs = build_index.call_args
        self.assertTrue(kwargs.get("include_code", False))
        self.assertTrue(kwargs.get("code_only", False))

    def test_background_docs_spawns_background_process(self):
        """--background-docs must call _spawn_background_docs_build after the code build."""
        with self._runtime_patches():
            with patch.object(self.mod, "prewarm_models"):
                with patch.object(self.mod, "build_index"):
                    with patch.object(self.mod, "_spawn_background_docs_build") as spawn:
                        with redirect_stdout(io.StringIO()):
                            self.mod.main(["--root", "/tmp/repo", "--background-docs"])
        spawn.assert_called_once()

    def test_docs_and_code_only_flags_are_mutually_exclusive(self):
        with self._runtime_patches():
            with patch.object(self.mod, "prewarm_models") as prewarm:
                with patch.object(self.mod, "build_index") as build_index:
                    stderr = io.StringIO()
                    with redirect_stderr(stderr):
                        rc = self.mod.main(["--root", "/tmp/repo", "--docs-only", "--code-only"])
        self.assertEqual(rc, 2)
        self.assertIn("mutually exclusive", stderr.getvalue())
        prewarm.assert_not_called()
        build_index.assert_not_called()

    def test_background_layer_flags_are_mutually_exclusive(self):
        with self._runtime_patches():
            with patch.object(self.mod, "prewarm_models") as prewarm:
                with patch.object(self.mod, "build_index") as build_index:
                    stderr = io.StringIO()
                    with redirect_stderr(stderr):
                        rc = self.mod.main(["--root", "/tmp/repo", "--background-code", "--background-docs"])
        self.assertEqual(rc, 2)
        self.assertIn("cannot be combined", stderr.getvalue())
        prewarm.assert_not_called()
        build_index.assert_not_called()


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


class UvSslCertFileIsolationTests(unittest.TestCase):
    """Wave 1p8tf: uv must not inherit SSL_CERT_FILE (its exclusive trust anchor); pip consumers
    get a merged superset; a plain environment is unchanged; the per-store ladder is untouched."""

    def setUp(self):
        self.mod = load_setup_index()

    def _clear_ca_env(self):
        for var in ("CODEX_CA_CERTIFICATE", "CLAUDE_CODE_CERT_STORE", "NODE_EXTRA_CA_CERTS",
                    "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "SSL_CERT_DIR", "UV_NATIVE_TLS"):
            os.environ.pop(var, None)

    def test_uv_env_scrubs_cert_vars_and_sets_native_tls(self):
        # AC-1: uv child env drops the exclusive-anchor vars and sets UV_NATIVE_TLS; os.environ intact.
        with patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            os.environ["SSL_CERT_FILE"] = "/corp/root.pem"
            os.environ["REQUESTS_CA_BUNDLE"] = "/corp/root.pem"
            os.environ["SSL_CERT_DIR"] = "/corp/certs"
            env = self.mod._uv_install_env()
            self.assertIsNotNone(env)
            self.assertNotIn("SSL_CERT_FILE", env)
            self.assertNotIn("REQUESTS_CA_BUNDLE", env)
            self.assertNotIn("SSL_CERT_DIR", env)
            self.assertEqual(env.get("UV_NATIVE_TLS"), "1")
            # os.environ is not mutated by building the scoped env
            self.assertEqual(os.environ.get("SSL_CERT_FILE"), "/corp/root.pem")

    def test_uv_env_none_when_no_cert_vars(self):
        # AC-2/AC-5: a plain environment is left untouched (inherit), not forced through native-TLS.
        with patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            self.assertIsNone(self.mod._uv_install_env())

    def test_merged_bundle_is_superset_and_dedupes(self):
        # AC-3: union of multiple stores, deduped by certificate block.
        cert_a = "-----BEGIN CERTIFICATE-----\nAAAAcorp\n-----END CERTIFICATE-----"
        cert_b = "-----BEGIN CERTIFICATE-----\nBBBBpublic\n-----END CERTIFICATE-----"
        with tempfile.TemporaryDirectory() as d:
            fa = Path(d) / "a.pem"; fa.write_text(cert_a + "\n", encoding="utf-8")
            fb = Path(d) / "b.pem"; fb.write_text(cert_b + "\n", encoding="utf-8")
            fdup = Path(d) / "dup.pem"; fdup.write_text(cert_a + "\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=False):
                self._clear_ca_env()
                os.environ["SSL_CERT_FILE"] = str(fa)  # signals a corp/proxy trust setup
                with patch.object(self.mod, "_os_trust_store_candidates",
                                  return_value=[str(fa), str(fb), str(fdup)]):
                    merged = self.mod._merged_trust_bundle()
                    self.assertIsNotNone(merged)
                    text = Path(merged).read_text(encoding="utf-8")
                    self.assertIn("AAAAcorp", text)
                    self.assertIn("BBBBpublic", text)
                    self.assertEqual(text.count("AAAAcorp"), 1, "duplicate cert must be deduped")

    def test_merged_bundle_tolerates_unreadable_candidate(self):
        # AC-3: an unreadable/missing candidate is skipped, not fatal.
        cert_a = "-----BEGIN CERTIFICATE-----\nAAAA1\n-----END CERTIFICATE-----"
        cert_b = "-----BEGIN CERTIFICATE-----\nBBBB1\n-----END CERTIFICATE-----"
        with tempfile.TemporaryDirectory() as d:
            fa = Path(d) / "a.pem"; fa.write_text(cert_a + "\n", encoding="utf-8")
            fb = Path(d) / "b.pem"; fb.write_text(cert_b + "\n", encoding="utf-8")
            missing = str(Path(d) / "does-not-exist.pem")
            with patch.dict(os.environ, {}, clear=False):
                self._clear_ca_env()
                os.environ["CODEX_CA_CERTIFICATE"] = str(fa)
                with patch.object(self.mod, "_os_trust_store_candidates",
                                  return_value=[str(fa), missing, str(fb)]):
                    merged = self.mod._merged_trust_bundle()
                    self.assertIsNotNone(merged)
                    text = Path(merged).read_text(encoding="utf-8")
                    self.assertIn("AAAA1", text)
                    self.assertIn("BBBB1", text)

    def test_merged_bundle_none_in_plain_env(self):
        # AC-5: no corp/host-agent material → no merged bundle (default certifi/OS path unchanged).
        with patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            self.assertIsNone(self.mod._merged_trust_bundle())

    def test_pip_env_points_at_merged_superset(self):
        # AC-3/Req 1: pip is pointed at the merged superset so it reaches PyPI in either topology.
        with patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            os.environ["SSL_CERT_FILE"] = "/corp/root.pem"
            with patch.object(self.mod, "_merged_trust_bundle", return_value="/cache/merged.pem"):
                env = self.mod._pip_tls_env()
                self.assertIsNotNone(env)
                self.assertEqual(env.get("SSL_CERT_FILE"), "/cache/merged.pem")
                self.assertEqual(env.get("REQUESTS_CA_BUNDLE"), "/cache/merged.pem")

    def test_pip_env_none_in_plain_env(self):
        # AC-5: plain env → pip inherits unchanged.
        with patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            with patch.object(self.mod, "_merged_trust_bundle", return_value=None):
                self.assertIsNone(self.mod._pip_tls_env())

    def test_warm_model_ladder_functions_unchanged(self):
        # AC-4: the prior per-store ladder accessors are preserved (not reworked by this change).
        src = SETUP_INDEX_PATH.read_text(encoding="utf-8")
        self.assertIn("def _os_trust_store_candidates(", src)
        self.assertIn("def _os_trust_store_bundle(", src)
        self.assertIn("def _warm_model(", src)


class CaBundleProactiveApplyTests(unittest.TestCase):
    """Wave 1p939: ``ensure_ca_bundle_applied`` / ``raise_with_ca_bundle_diagnostic`` — the
    proactive CA-bundle path used by non-setup launchers (accel_embedder, server_impl) that don't
    go through ``_warm_model``'s full retry ladder."""

    def setUp(self):
        self.mod = load_setup_index()
        self.mod._ca_bundle_apply_attempted = False

    def _clear_ca_env(self):
        for var in ("CODEX_CA_CERTIFICATE", "CLAUDE_CODE_CERT_STORE", "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
            os.environ.pop(var, None)

    def test_applies_host_agent_bundle_when_stack_env_unset(self):
        # AC-1: a host-agent CA var present + no operator stack env → applied.
        with tempfile.NamedTemporaryFile(suffix=".crt") as codex, \
             patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            os.environ["CODEX_CA_CERTIFICATE"] = codex.name
            self.mod.ensure_ca_bundle_applied()
            self.assertEqual(os.environ.get("SSL_CERT_FILE"), codex.name)
            self.assertEqual(os.environ.get("REQUESTS_CA_BUNDLE"), codex.name)

    def test_no_op_in_plain_env(self):
        # AC-3: no host-agent/operator CA var set → no mutation, no candidate resolution attempted.
        with patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            with patch.object(self.mod, "_apply_ca_bundle") as apply_mock:
                self.mod.ensure_ca_bundle_applied()
                apply_mock.assert_not_called()
            self.assertNotIn("SSL_CERT_FILE", os.environ)

    def test_idempotent_single_application_per_process(self):
        # AC-3: only the first call does real work; later calls in the same process are no-ops,
        # even if the env changes between calls.
        with tempfile.NamedTemporaryFile(suffix=".crt") as codex, \
             patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            os.environ["CODEX_CA_CERTIFICATE"] = codex.name
            with patch.object(self.mod, "_apply_ca_bundle") as apply_mock:
                self.mod.ensure_ca_bundle_applied()
                self.mod.ensure_ca_bundle_applied()
                self.mod.ensure_ca_bundle_applied()
                apply_mock.assert_called_once()

    def test_operator_stack_env_always_wins(self):
        # Operator-set SSL_CERT_FILE must never be overridden by a host-agent var.
        with tempfile.NamedTemporaryFile(suffix=".crt") as codex, \
             tempfile.NamedTemporaryFile(suffix=".crt") as operator, \
             patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            os.environ["CODEX_CA_CERTIFICATE"] = codex.name
            os.environ["SSL_CERT_FILE"] = operator.name
            self.mod.ensure_ca_bundle_applied()
            self.assertEqual(os.environ.get("SSL_CERT_FILE"), operator.name)

    def test_raise_with_ca_bundle_diagnostic_wraps_cert_verify_error(self):
        # AC-4: a persisting CERTIFICATE_VERIFY_FAILED is wrapped with operator CA-var guidance.
        exc = Exception("SSLError: certificate verify failed: unable to get local issuer certificate")
        with self.assertRaises(self.mod.ModelPrewarmError) as ctx:
            self.mod.raise_with_ca_bundle_diagnostic("BAAI/bge-small-en-v1.5", exc)
        self.assertIn("CERTIFICATE_VERIFY_FAILED", str(ctx.exception))
        self.assertIn("NODE_EXTRA_CA_CERTS", str(ctx.exception))
        self.assertIs(ctx.exception.__cause__, exc)

    def test_raise_with_ca_bundle_diagnostic_passes_through_other_errors(self):
        # A non-cert error must be re-raised unchanged, not wrapped.
        exc = ConnectionError("connection reset by peer")
        with self.assertRaises(ConnectionError) as ctx:
            self.mod.raise_with_ca_bundle_diagnostic("BAAI/bge-small-en-v1.5", exc)
        self.assertIs(ctx.exception, exc)

    def test_apply_lock_exists_for_thread_safety(self):
        # Wave 1p939 (delivery-phase fix, code-reviewer finding): the check-then-set on
        # _ca_bundle_apply_attempted is lock-protected — two threads in the long-lived MCP server
        # process must not both pass the early-return check before either sets the flag.
        self.assertIsInstance(self.mod._ca_bundle_apply_lock, type(threading.Lock()))


class RetryWithCaBundleLadderTests(unittest.TestCase):
    """Wave 1p939 (delivery-phase fix): ``retry_with_ca_bundle_ladder`` — the REACTIVE candidate
    ladder (host-agent -> operator -> platform OS-bundle paths -> certifi default) that
    ``ensure_ca_bundle_applied()`` alone does not cover. Closes the delivery-phase council's
    strongest_challenge: the proactive-only helper left non-setup launchers broken in any
    corporate-proxy environment whose only working trust rung is an OS-bundle file."""

    def setUp(self):
        self.mod = load_setup_index()
        self.mod._ca_bundle_apply_attempted = False

    def _clear_ca_env(self):
        for var in ("CODEX_CA_CERTIFICATE", "CLAUDE_CODE_CERT_STORE", "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
            os.environ.pop(var, None)

    def test_returns_on_first_success_no_candidates_tried(self):
        calls = []

        def attempt():
            calls.append(1)
            return "ok"

        with patch.object(self.mod, "_os_trust_store_candidates") as candidates:
            result = self.mod.retry_with_ca_bundle_ladder(attempt, "BAAI/bge-small-en-v1.5")
        self.assertEqual(result, "ok")
        self.assertEqual(len(calls), 1)
        candidates.assert_not_called()

    def test_passes_through_non_cert_error_without_retry(self):
        def attempt():
            raise ConnectionError("connection reset by peer")

        with patch.object(self.mod, "_os_trust_store_candidates") as candidates:
            with self.assertRaises(ConnectionError):
                self.mod.retry_with_ca_bundle_ladder(attempt, "BAAI/bge-small-en-v1.5")
        candidates.assert_not_called()

    def test_retries_candidates_on_cert_failure_until_success(self):
        cert_exc = Exception("certificate verify failed: unable to get local issuer certificate")
        calls = []

        def attempt():
            calls.append(1)
            if len(calls) < 3:
                raise cert_exc
            return "resolved"

        with tempfile.NamedTemporaryFile(suffix=".crt") as c1, \
             tempfile.NamedTemporaryFile(suffix=".crt") as c2, \
             patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            with patch.object(self.mod, "_os_trust_store_candidates", return_value=[c1.name, c2.name]):
                result = self.mod.retry_with_ca_bundle_ladder(attempt, "BAAI/bge-small-en-v1.5")
            self.assertEqual(os.environ.get("SSL_CERT_FILE"), c2.name, "last applied candidate stuck (no restore)")
        self.assertEqual(result, "resolved")
        self.assertEqual(len(calls), 3, "initial attempt + 2 candidate retries")

    def test_raises_diagnostic_when_all_candidates_exhausted(self):
        cert_exc = Exception("certificate verify failed: unable to get local issuer certificate")

        def attempt():
            raise cert_exc

        with tempfile.NamedTemporaryFile(suffix=".crt") as c1, patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            with patch.object(self.mod, "_os_trust_store_candidates", return_value=[c1.name]):
                with self.assertRaises(self.mod.ModelPrewarmError) as ctx:
                    self.mod.retry_with_ca_bundle_ladder(attempt, "BAAI/bge-small-en-v1.5")
        self.assertIn("CERTIFICATE_VERIFY_FAILED", str(ctx.exception))
        self.assertIs(ctx.exception.__cause__, cert_exc)

    def test_skips_candidate_already_applied_via_stack_env(self):
        # The proactive step (ensure_ca_bundle_applied) may already have set SSL_CERT_FILE to the
        # host-agent bundle before the first attempt; the reactive ladder must not retry that exact
        # candidate redundantly.
        cert_exc = Exception("certificate verify failed: unable to get local issuer certificate")
        calls = []

        def attempt():
            calls.append(1)
            raise cert_exc

        with tempfile.NamedTemporaryFile(suffix=".crt") as already_tried, \
             tempfile.NamedTemporaryFile(suffix=".crt") as untried, \
             patch.dict(os.environ, {}, clear=False):
            self._clear_ca_env()
            os.environ["SSL_CERT_FILE"] = already_tried.name
            with patch.object(self.mod, "_os_trust_store_candidates", return_value=[already_tried.name, untried.name]):
                with self.assertRaises(self.mod.ModelPrewarmError):
                    self.mod.retry_with_ca_bundle_ladder(attempt, "BAAI/bge-small-en-v1.5")
        self.assertEqual(len(calls), 2, "initial attempt (against already_tried) + 1 retry (untried only)")


class GpuDoctorProbeSerialTests(unittest.TestCase):
    """Wave 1p8vc AC-4: the in-server `_probe_embedding_provider` must stay serial — fastembed's
    parallel path spawns workers that re-load ORT and would write to the inherited MCP stdout fd."""

    def _probe_body(self) -> str:
        src = SETUP_INDEX_PATH.read_text(encoding="utf-8")
        start = src.index("def _probe_embedding_provider(")
        # body runs until the next top-level `def `/`class ` at column 0
        rest = src[start + 1:]
        m = re.search(r"\n(?=def |class )", rest)
        return rest[: m.start()] if m else rest

    def test_probe_does_not_enable_fastembed_parallelism(self):
        body = self._probe_body()
        # Strip comment text so the assertion checks CODE, not the explanatory comment (which
        # deliberately mentions `parallel=` as the thing NOT to do).
        code = "\n".join(line.split("#", 1)[0] for line in body.splitlines())
        self.assertIn(".embed(", code, "sanity: the probe calls embed()")
        self.assertNotIn("parallel=", code,
                         "the in-server probe must not pass parallel= to fastembed (spawn workers "
                         "would re-load ORT against the inherited MCP stdout fd — wave 1p8vc)")


class SetupPhase1DeadlineTests(unittest.TestCase):
    """Wave 1p9it — every `wf setup` Phase-1 child is bounded by a per-step deadline / no-progress
    watchdog; a stall fails loud with stage-specific guidance instead of hanging, defaults ship in code,
    and each deadline is overridable via docs/workflow-config.json `setup.<key>`."""

    def setUp(self):
        self.mod = load_setup_index()

    # --- AC-4: config loader (override honored; missing/malformed -> defaults, never raises) ----------

    def _write_config(self, root: Path, setup_block: object) -> None:
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "workflow-config.json").write_text(
            json.dumps({"setup": setup_block}), encoding="utf-8"
        )

    def test_setup_deadlines_reads_config_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, {"venv_create_timeout_seconds": 42, "model_warm_timeout_seconds": 99.5})
            d = self.mod._setup_deadlines(root)
        self.assertEqual(d["venv_create_timeout_seconds"], 42.0)
        self.assertEqual(d["model_warm_timeout_seconds"], 99.5)
        # unspecified keys keep their shipped defaults
        self.assertEqual(d["dep_install_timeout_seconds"], self.mod.DEP_INSTALL_TIMEOUT_DEFAULT)
        self.assertEqual(d["index_build_stall_timeout_seconds"], self.mod.INDEX_BUILD_STALL_TIMEOUT_DEFAULT)

    def test_setup_deadlines_none_root_returns_all_defaults(self):
        self.assertEqual(self.mod._setup_deadlines(None), dict(self.mod._SETUP_DEADLINE_KEYS))

    def test_setup_deadlines_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self.mod._setup_deadlines(Path(tmp))
        self.assertEqual(d, dict(self.mod._SETUP_DEADLINE_KEYS))

    def test_setup_deadlines_malformed_and_nonpositive_fall_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "workflow-config.json").write_text("{ not valid json", encoding="utf-8")
            self.assertEqual(self.mod._setup_deadlines(root), dict(self.mod._SETUP_DEADLINE_KEYS))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # non-positive, non-numeric, and boolean values must all fall back to the default
            self._write_config(root, {
                "venv_create_timeout_seconds": -5,
                "dep_install_timeout_seconds": "soon",
                "model_warm_timeout_seconds": True,
            })
            d = self.mod._setup_deadlines(root)
        self.assertEqual(d["venv_create_timeout_seconds"], self.mod.VENV_CREATE_TIMEOUT_DEFAULT)
        self.assertEqual(d["dep_install_timeout_seconds"], self.mod.DEP_INSTALL_TIMEOUT_DEFAULT)
        self.assertEqual(d["model_warm_timeout_seconds"], self.mod.MODEL_WARM_TIMEOUT_DEFAULT)

    # --- AC-1: venv / uv / dep-install spawn timeouts (loud, stage-named) -----------------------------

    def test_bootstrap_venv_timeout_fails_loud(self):
        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="venv", timeout=1)):
                    err = io.StringIO()
                    with redirect_stderr(err), redirect_stdout(io.StringIO()):
                        with self.assertRaises(SystemExit) as raised:
                            self.mod._bootstrap_venv()
        self.assertEqual(raised.exception.code, 2)
        msg = err.getvalue().lower()
        self.assertIn("venv", msg)
        self.assertIn("timed out", msg)

    def test_bootstrap_uv_timeout_falls_back_with_loud_message(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="pip install uv", timeout=1)):
            err = io.StringIO()
            with redirect_stderr(err), redirect_stdout(io.StringIO()):
                result = self.mod._bootstrap_uv(FAKE_VENV_PYTHON)
        # uv is optional: a stalled bootstrap is loud but returns None so the caller falls back to pip.
        self.assertIsNone(result)
        msg = err.getvalue().lower()
        self.assertIn("uv", msg)
        self.assertIn("timed out", msg)
        self.assertIn("pypi", msg)

    def test_install_deps_timeout_fails_loud_with_network_guidance(self):
        with patch.object(self.mod, "_uv_bin", return_value=None):
            with patch.object(self.mod, "_bootstrap_uv", return_value=None):  # force the plain-pip path
                with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="pip", timeout=1)):
                    err = io.StringIO()
                    with redirect_stderr(err), redirect_stdout(io.StringIO()):
                        with self.assertRaises(SystemExit) as raised:
                            self.mod._install_deps(["fastembed"], FAKE_VENV_PYTHON)
        self.assertEqual(raised.exception.code, 2)
        msg = err.getvalue().lower()
        self.assertIn("timed out", msg)
        self.assertIn("pypi", msg)  # names network/proxy/TLS reachability

    def test_bootstrap_venv_forwards_configured_timeout(self):
        # AC-1 + AC-4: the configured venv deadline reaches the spawn as `timeout=`.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, {"venv_create_timeout_seconds": 7})
            with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
                with patch("pathlib.Path.exists", return_value=False):
                    with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
                        with redirect_stdout(io.StringIO()):
                            self.mod._bootstrap_venv(root)
        self.assertEqual(run.call_args.kwargs.get("timeout"), 7.0)

    def test_bootstrap_uv_forwards_configured_timeout(self):
        # Delivery-review binding gap: the uv spawn must carry the configured deadline as
        # `timeout=` — the timeout-path test alone would still pass if the kwarg were dropped.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, {"uv_bootstrap_timeout_seconds": 11})
            with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.mod._bootstrap_uv(FAKE_VENV_PYTHON, root)
        self.assertEqual(run.call_args_list[0].kwargs.get("timeout"), 11.0)

    def test_install_deps_forwards_configured_timeout(self):
        # Delivery-review binding gap: the dep-install spawn must carry the configured deadline.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, {"dep_install_timeout_seconds": 13})
            with patch.object(self.mod, "_uv_bin", return_value=None):
                with patch.object(self.mod, "_bootstrap_uv", return_value=None):  # plain-pip path
                    with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
                        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                            self.mod._install_deps(["fastembed"], FAKE_VENV_PYTHON, root)
        self.assertEqual(run.call_args_list[0].kwargs.get("timeout"), 13.0)

    # --- AC-2: in-process model-warm wall-clock deadline ----------------------------------------------

    def test_warm_model_aborts_over_deadline(self):
        def slow_inner(model_name, *, local_files_only):
            time.sleep(2)  # still running when the tiny deadline elapses; daemon thread, self-terminating

        with patch.object(self.mod, "_warm_model_inner", side_effect=slow_inner):
            with self.assertRaises(self.mod.ModelPrewarmError) as raised:
                self.mod._warm_model("bge-small", local_files_only=False, deadline_seconds=0.05)
        msg = str(raised.exception)
        self.assertIn("model_warm_timeout_seconds", msg)
        self.assertIn("network", msg.lower())

    def test_warm_model_within_deadline_runs_inner(self):
        seen = {}

        def fast_inner(model_name, *, local_files_only):
            seen["args"] = (model_name, local_files_only)

        with patch.object(self.mod, "_warm_model_inner", side_effect=fast_inner):
            self.mod._warm_model("bge-small", local_files_only=True, deadline_seconds=5.0)
        self.assertEqual(seen["args"], ("bge-small", True))

    def test_warm_model_propagates_inner_error_within_deadline(self):
        def boom_inner(model_name, *, local_files_only):
            raise RuntimeError("cache miss")

        with patch.object(self.mod, "_warm_model_inner", side_effect=boom_inner):
            with self.assertRaises(RuntimeError):
                self.mod._warm_model("bge-small", local_files_only=False, deadline_seconds=5.0)

    def test_warm_model_uses_active_run_deadline_when_arg_default(self):
        captured = {}

        def _fake_deadline(fn, *, deadline_seconds, timeout_error):
            captured["deadline"] = deadline_seconds

        prior = self.mod._ACTIVE_MODEL_WARM_DEADLINE_SECONDS
        try:
            self.mod._ACTIVE_MODEL_WARM_DEADLINE_SECONDS = 123.0
            with patch.object(self.mod, "_run_in_process_with_deadline", side_effect=_fake_deadline):
                self.mod._warm_model("bge-small", local_files_only=False)
        finally:
            self.mod._ACTIVE_MODEL_WARM_DEADLINE_SECONDS = prior
        self.assertEqual(captured["deadline"], 123.0)

    def test_prewarm_timeout_skips_quarantine_and_propagates(self):
        # Delivery-review DF-1: a deadline abort must NOT run the corruption-check/quarantine/retry —
        # the abandoned warm thread may still be writing the cache, so the corruption check would
        # misread the in-flight download and the quarantine would move a directory with live open
        # handles (raw sharing violation on Windows). The timeout propagates unchanged, single attempt.
        timeout_exc = self.mod.ModelPrewarmTimeout("model warm exceeded the deadline")
        calls = {"warm": 0}

        def timing_out_warm(model_name, *, local_files_only):
            calls["warm"] += 1
            raise timeout_exc

        with patch.object(self.mod, "_model_cache_corruption_reason") as corruption:
            with patch.object(self.mod, "_quarantine_model_cache") as quarantine:
                with self.assertRaises(self.mod.ModelPrewarmTimeout) as raised:
                    self.mod._prewarm_required_model(
                        "bge-small", model_kind="docs embedding", action="setup",
                        warm_fn=timing_out_warm,
                    )
        self.assertIs(raised.exception, timeout_exc)  # propagated unwrapped, message intact
        self.assertEqual(calls["warm"], 1)  # no retry attempt
        corruption.assert_not_called()
        quarantine.assert_not_called()

    def test_prewarm_timeout_is_a_prewarm_error_for_mains_handler(self):
        # main's `except ModelPrewarmError` must catch the timeout subtype (clean exit 2 path).
        self.assertTrue(issubclass(self.mod.ModelPrewarmTimeout, self.mod.ModelPrewarmError))

    # --- AC-3: index-build no-progress watchdog terminates + reaps a stalled child --------------------

    def test_run_indexer_stalled_child_terminated_and_reaped(self):
        class _BlockingStdout:
            """Stdout that never yields a line and never hits EOF until `event` is set — a child that
            produces no output and does not exit."""

            def __init__(self, event):
                self._event = event

            def __iter__(self):
                return self

            def __next__(self):
                self._event.wait()  # unblocks only when the child is 'killed' (event set below)
                raise StopIteration

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, {"index_build_stall_timeout_seconds": 0.1})
            event = threading.Event()
            proc = MagicMock()
            proc.stdout = _BlockingStdout(event)
            proc.kill.side_effect = lambda: event.set()  # kill closes the pipe -> reader hits EOF
            wait_calls = {"n": 0}

            def fake_wait(timeout=None):
                wait_calls["n"] += 1
                if wait_calls["n"] == 1:
                    # terminate() did not stop it within the grace window -> force escalation to kill()
                    raise subprocess.TimeoutExpired(cmd="idx", timeout=timeout)
                return 0

            proc.wait.side_effect = fake_wait

            with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
                with patch("subprocess.Popen", return_value=proc):
                    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                        with self.assertRaises(TimeoutError) as raised:
                            self.mod._run_indexer(
                                root,
                                full=False,
                                content="docs",
                                verbose=False,
                                include_tests=False,
                                include_generated=False,
                                project_include_prefixes=(),
                            )

        proc.terminate.assert_called_once()
        proc.kill.assert_called_once()
        message = str(raised.exception)
        self.assertIn("no output", message.lower())
        self.assertIn("index_build_stall_timeout_seconds", message)

    # --- AC-5: within-deadline (normal) index build is behaviorally unchanged --------------------------

    def test_run_indexer_within_deadline_streams_all_lines_in_order(self):
        root = Path("/tmp/wavefoundry-test-root")
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = iter(["a\n", "b\n", "c\n"])
        proc.wait.return_value = None
        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("subprocess.Popen", return_value=proc):
                out = io.StringIO()
                with redirect_stdout(out):
                    self.mod._run_indexer(
                        root,
                        full=False,
                        content="docs",
                        verbose=False,
                        include_tests=False,
                        include_generated=False,
                        project_include_prefixes=(),
                    )
        self.assertEqual(out.getvalue(), "a\nb\nc\n")
        proc.wait.assert_called_once()
        # Hardening (b): the post-loop reap is BOUNDED — a reader-thread failure is
        # indistinguishable from EOF, so an unbounded wait could hang on a live silent child.
        self.assertIsNotNone(proc.wait.call_args.kwargs.get("timeout"))
        proc.terminate.assert_not_called()
        proc.kill.assert_not_called()

    def test_run_indexer_post_eof_nonexiting_child_terminated(self):
        # Hardening (b) expiry branch: EOF arrives but the child never exits (reader-death /
        # grandchild-holds-pipe shape) → bounded wait expires → terminate/kill + loud TimeoutError.
        root = Path("/tmp/wavefoundry-test-root")
        proc = MagicMock()
        proc.returncode = None
        proc.stdout = iter(["a\n"])
        proc.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="indexer", timeout=1),  # post-loop bounded wait
            None,  # grace wait inside _terminate_and_reap after terminate()
            None,  # reap wait inside _terminate_and_reap
        ]
        with patch.object(self.mod, "_tool_venv_python", return_value=FAKE_VENV_PYTHON):
            with patch("subprocess.Popen", return_value=proc):
                with redirect_stdout(io.StringIO()):
                    with self.assertRaises(TimeoutError) as raised:
                        self.mod._run_indexer(
                            root,
                            full=False,
                            content="docs",
                            verbose=False,
                            include_tests=False,
                            include_generated=False,
                            project_include_prefixes=(),
                        )
        self.assertIn("did not exit", str(raised.exception))
        proc.terminate.assert_called_once()

    def test_main_graph_only_stall_timeout_exits_2_with_message(self):
        # Hardening (a): a stall-watchdog TimeoutError from the indexer surfaces as a clean,
        # stage-named exit 2 from main — not a raw traceback with exit 1.
        stall = TimeoutError(
            "Index build produced no output for 1s and was terminated as stalled."
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(self.mod, "ensure_deps"), \
                 patch.object(self.mod, "_reexec_with_venv_if_needed"), \
                 patch.object(self.mod, "_workflow_project_include_prefixes", return_value={}), \
                 patch.object(self.mod, "_run_indexer", side_effect=stall):
                err = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(err):
                    rc = self.mod.main(["--root", tmp, "--graph-only"])
        self.assertEqual(rc, 2)
        self.assertIn("terminated as stalled", err.getvalue())


class HfHubSocketTimeoutScopeTests(unittest.TestCase):
    """Change 1p9p9 (wave 1p9pe) — scoped HF Hub socket timeouts around the model warm.

    The scope patches ``huggingface_hub.constants.HF_HUB_DOWNLOAD_TIMEOUT`` /
    ``HF_HUB_ETAG_TIMEOUT`` module attributes directly — an ``os.environ`` set after import is a
    no-op because huggingface_hub reads the env once at import — applies config/default values with
    an operator-set env var winning as the source, restores on every exit (success, inner failure,
    deadline timeout), and complements (never replaces) the DF-1 wall-clock deadline. Tests use a
    fake ``huggingface_hub`` package injected via ``sys.modules`` so they are hermetic whether or
    not the real hub is installed."""

    DOWNLOAD_KEY = "hf_hub_download_timeout_seconds"
    ETAG_KEY = "hf_hub_etag_timeout_seconds"

    def setUp(self):
        self.mod = load_setup_index()

    def _fake_hub(self, download=10, etag=10, omit_etag=False):
        pkg = types.ModuleType("huggingface_hub")
        constants = types.ModuleType("huggingface_hub.constants")
        constants.HF_HUB_DOWNLOAD_TIMEOUT = download
        if not omit_etag:
            constants.HF_HUB_ETAG_TIMEOUT = etag
        pkg.constants = constants
        return pkg, constants

    def _scope_env(self, pkg, constants, active=None, env=None):
        """ExitStack installing the fake hub modules, a clean HF timeout env (plus ``env``
        overrides), and the per-run active timeout values."""
        stack = ExitStack()
        stack.enter_context(patch.dict(sys.modules, {
            "huggingface_hub": pkg,
            "huggingface_hub.constants": constants,
        }))
        stack.enter_context(patch.dict(os.environ))
        os.environ.pop("HF_HUB_DOWNLOAD_TIMEOUT", None)
        os.environ.pop("HF_HUB_ETAG_TIMEOUT", None)
        for key, value in (env or {}).items():
            os.environ[key] = value
        stack.enter_context(patch.object(self.mod, "_ACTIVE_HF_HUB_SOCKET_TIMEOUTS", active))
        return stack

    # --- AC-1: effectiveness — the CONSTANTS reflect the configured values DURING the warm ----------

    def test_constants_reflect_configured_values_during_warm(self):
        # The value the HF download actually consumes at call time (the module constant, NOT
        # os.environ) equals the configured value inside the warm body, and restores after.
        pkg, constants = self._fake_hub()
        seen = {}

        def inner(model_name, *, local_files_only):
            seen["download"] = constants.HF_HUB_DOWNLOAD_TIMEOUT
            seen["etag"] = constants.HF_HUB_ETAG_TIMEOUT

        active = {self.DOWNLOAD_KEY: 77.0, self.ETAG_KEY: 33.0}
        with self._scope_env(pkg, constants, active=active):
            with patch.object(self.mod, "_warm_model_inner", side_effect=inner):
                self.mod._warm_model("bge-small", local_files_only=False, deadline_seconds=5.0)
        self.assertEqual(seen, {"download": 77.0, "etag": 33.0})
        self.assertEqual(constants.HF_HUB_DOWNLOAD_TIMEOUT, 10)  # restored (AC-3)
        self.assertEqual(constants.HF_HUB_ETAG_TIMEOUT, 10)

    def test_defaults_apply_when_no_run_config(self):
        # Direct scope entry with no per-run config (e.g. an explicit-deadline caller): the shipped
        # defaults apply to the constants.
        pkg, constants = self._fake_hub()
        with self._scope_env(pkg, constants, active=None):
            with self.mod._hf_hub_timeout_scope():
                self.assertEqual(
                    constants.HF_HUB_DOWNLOAD_TIMEOUT, self.mod.HF_HUB_DOWNLOAD_TIMEOUT_DEFAULT
                )
                self.assertEqual(
                    constants.HF_HUB_ETAG_TIMEOUT, self.mod.HF_HUB_ETAG_TIMEOUT_DEFAULT
                )
        self.assertEqual(constants.HF_HUB_DOWNLOAD_TIMEOUT, 10)
        self.assertEqual(constants.HF_HUB_ETAG_TIMEOUT, 10)

    # --- AC-3: scoped restore + operator env value honored as the source -----------------------------

    def test_operator_env_value_wins_over_config(self):
        # An operator-set HF_HUB_*_TIMEOUT env var is the SOURCE of the applied value — a lower
        # config/default never overrides an explicit operator choice.
        pkg, constants = self._fake_hub()
        active = {self.DOWNLOAD_KEY: 30.0, self.ETAG_KEY: 30.0}
        env = {"HF_HUB_DOWNLOAD_TIMEOUT": "120", "HF_HUB_ETAG_TIMEOUT": "45.5"}
        with self._scope_env(pkg, constants, active=active, env=env):
            with self.mod._hf_hub_timeout_scope():
                self.assertEqual(constants.HF_HUB_DOWNLOAD_TIMEOUT, 120.0)
                self.assertEqual(constants.HF_HUB_ETAG_TIMEOUT, 45.5)
        self.assertEqual(constants.HF_HUB_DOWNLOAD_TIMEOUT, 10)
        self.assertEqual(constants.HF_HUB_ETAG_TIMEOUT, 10)

    def test_malformed_or_nonpositive_env_falls_back_to_config(self):
        pkg, constants = self._fake_hub()
        active = {self.DOWNLOAD_KEY: 44.0, self.ETAG_KEY: 55.0}
        env = {"HF_HUB_DOWNLOAD_TIMEOUT": "soon", "HF_HUB_ETAG_TIMEOUT": "-1"}
        with self._scope_env(pkg, constants, active=active, env=env):
            with self.mod._hf_hub_timeout_scope():
                self.assertEqual(constants.HF_HUB_DOWNLOAD_TIMEOUT, 44.0)
                self.assertEqual(constants.HF_HUB_ETAG_TIMEOUT, 55.0)

    def test_scope_restores_constants_on_exception(self):
        pkg, constants = self._fake_hub()
        with self._scope_env(pkg, constants):
            with self.assertRaises(RuntimeError):
                with self.mod._hf_hub_timeout_scope():
                    self.assertEqual(
                        constants.HF_HUB_DOWNLOAD_TIMEOUT, self.mod.HF_HUB_DOWNLOAD_TIMEOUT_DEFAULT
                    )
                    raise RuntimeError("boom")
        self.assertEqual(constants.HF_HUB_DOWNLOAD_TIMEOUT, 10)
        self.assertEqual(constants.HF_HUB_ETAG_TIMEOUT, 10)

    def test_warm_failure_restores_constants(self):
        pkg, constants = self._fake_hub()

        def boom(model_name, *, local_files_only):
            raise RuntimeError("cache miss")

        with self._scope_env(pkg, constants):
            with patch.object(self.mod, "_warm_model_inner", side_effect=boom):
                with self.assertRaises(RuntimeError):
                    self.mod._warm_model("bge-small", local_files_only=False, deadline_seconds=5.0)
        self.assertEqual(constants.HF_HUB_DOWNLOAD_TIMEOUT, 10)
        self.assertEqual(constants.HF_HUB_ETAG_TIMEOUT, 10)

    # --- AC-4/AC-5: deadline untouched; healthy warm unchanged; default ordering ---------------------

    def test_deadline_timeout_still_raises_and_restores(self):
        # The DF-1 wall-clock deadline is untouched: it still fires with the same error type, and
        # because the scope wraps the deadline runner on the joining thread, the constants restore
        # even on the abandoned-thread timeout path.
        pkg, constants = self._fake_hub()

        def slow(model_name, *, local_files_only):
            time.sleep(2)  # daemon worker; still running when the tiny deadline elapses

        with self._scope_env(pkg, constants):
            with patch.object(self.mod, "_warm_model_inner", side_effect=slow):
                with self.assertRaises(self.mod.ModelPrewarmTimeout):
                    self.mod._warm_model("bge-small", local_files_only=False, deadline_seconds=0.05)
        self.assertEqual(constants.HF_HUB_DOWNLOAD_TIMEOUT, 10)
        self.assertEqual(constants.HF_HUB_ETAG_TIMEOUT, 10)

    def test_healthy_warm_success_path_unchanged(self):
        # A healthy within-timeout warm behaves exactly as today: same inner call, same success.
        pkg, constants = self._fake_hub()
        seen = {}

        def fast(model_name, *, local_files_only):
            seen["args"] = (model_name, local_files_only)

        with self._scope_env(pkg, constants):
            with patch.object(self.mod, "_warm_model_inner", side_effect=fast):
                self.mod._warm_model("bge-small", local_files_only=True, deadline_seconds=5.0)
        self.assertEqual(seen["args"], ("bge-small", True))

    def test_default_socket_timeouts_below_wall_clock_deadline(self):
        # AC-5: the socket timeout must be able to fire BEFORE the wall-clock deadline.
        self.assertLess(self.mod.HF_HUB_DOWNLOAD_TIMEOUT_DEFAULT, self.mod.MODEL_WARM_TIMEOUT_DEFAULT)
        self.assertLess(self.mod.HF_HUB_ETAG_TIMEOUT_DEFAULT, self.mod.MODEL_WARM_TIMEOUT_DEFAULT)

    # --- import-guard / forward-compat no-ops ---------------------------------------------------------

    def test_scope_noop_when_huggingface_hub_absent(self):
        # sys.modules[name] = None makes `from huggingface_hub import constants` raise ImportError:
        # the scope must yield as a clean no-op, never break the warm.
        with patch.dict(sys.modules, {"huggingface_hub": None, "huggingface_hub.constants": None}):
            with self.mod._hf_hub_timeout_scope():
                pass

    def test_scope_skips_renamed_constant(self):
        # A future hub release renaming one constant: the other is still patched; the missing one is
        # skipped (never created), and nothing raises.
        pkg, constants = self._fake_hub(omit_etag=True)
        with self._scope_env(pkg, constants):
            with self.mod._hf_hub_timeout_scope():
                self.assertEqual(
                    constants.HF_HUB_DOWNLOAD_TIMEOUT, self.mod.HF_HUB_DOWNLOAD_TIMEOUT_DEFAULT
                )
                self.assertFalse(hasattr(constants, "HF_HUB_ETAG_TIMEOUT"))
        self.assertEqual(constants.HF_HUB_DOWNLOAD_TIMEOUT, 10)
        self.assertFalse(hasattr(constants, "HF_HUB_ETAG_TIMEOUT"))

    # --- AC-2: config surface (loader + main wiring) --------------------------------------------------

    def test_setup_deadlines_reads_hf_hub_timeout_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "workflow-config.json").write_text(
                json.dumps({"setup": {self.DOWNLOAD_KEY: 45, self.ETAG_KEY: "soon"}}),
                encoding="utf-8",
            )
            d = self.mod._setup_deadlines(root)
        self.assertEqual(d[self.DOWNLOAD_KEY], 45.0)  # override honored
        self.assertEqual(d[self.ETAG_KEY], self.mod.HF_HUB_ETAG_TIMEOUT_DEFAULT)  # malformed -> default

    def test_main_resolves_active_socket_timeouts_from_config(self):
        # The per-run channel `_ACTIVE_HF_HUB_SOCKET_TIMEOUTS` is populated by main from the same
        # workflow-config block as the model-warm deadline.
        prior = self.mod._ACTIVE_HF_HUB_SOCKET_TIMEOUTS
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "docs").mkdir(parents=True, exist_ok=True)
                (root / "docs" / "workflow-config.json").write_text(
                    json.dumps({"setup": {self.DOWNLOAD_KEY: 61, self.ETAG_KEY: 12}}),
                    encoding="utf-8",
                )
                with patch.object(self.mod, "ensure_deps"), \
                     patch.object(self.mod, "_reexec_with_venv_if_needed"), \
                     patch.object(self.mod, "_workflow_project_include_prefixes", return_value={}), \
                     patch.object(self.mod, "_run_indexer"):
                    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                        rc = self.mod.main(["--root", tmp, "--graph-only"])
            self.assertEqual(rc, 0)
            self.assertEqual(
                self.mod._ACTIVE_HF_HUB_SOCKET_TIMEOUTS,
                {self.DOWNLOAD_KEY: 61.0, self.ETAG_KEY: 12.0},
            )
        finally:
            self.mod._ACTIVE_HF_HUB_SOCKET_TIMEOUTS = prior


class CoremlProbeTempdirRetryTests(unittest.TestCase):
    """Wave 1p9lj: CoreML probe temp-working-directory failure gets one bounded repair+retry inside
    the probe/decision window; every other failure shape stays fail-safe CPU with no retry."""

    TEMPDIR_ERROR = RuntimeError(
        "Error compiling model: Failed to create a working directory appropriate for URL: "
        "file:///var/folders/ab/xyz/T/"
    )

    def setUp(self):
        self.mod = load_setup_index()

    def _fake_embed_factory(self, fail_attempts: int, calls: list):
        """TextEmbedding stand-in that raises the temp-dir error for the first `fail_attempts`
        CANDIDATE constructions (provider list longer than 1), succeeding afterwards."""
        outer = self

        class _FakeEmbed:
            def __init__(self, *a, **k):
                providers = k.get("providers") or []
                is_candidate = len(providers) > 1
                if is_candidate:
                    calls.append(providers[0])
                    if len(calls) <= fail_attempts:
                        raise outer.TEMPDIR_ERROR

            def embed(self, texts):
                return [[0.1, 0.2] for _ in texts]

        return _FakeEmbed

    def test_tempdir_failure_repairs_and_retries_then_selects_coreml(self):
        # AC-1 + AC-2: first CoreML attempt fails with the working-directory shape → repair runs,
        # one retry succeeds → the probe accepts CoreML (correctness acceptance path).
        import fastembed

        calls: list = []
        with patch.object(fastembed, "TextEmbedding", self._fake_embed_factory(1, calls)), \
                patch.object(self.mod, "_repair_probe_tempdir", return_value="temp directory present") as repair, \
                redirect_stdout(io.StringIO()) as out:
            probe = self.mod._probe_embedding_provider(
                self.mod.provider_policy.COREML_PROVIDER, model_name="m")
        self.assertTrue(probe.ok, probe.reason)
        self.assertEqual(len(calls), 2)  # exactly one retry
        repair.assert_called_once()
        self.assertIn("retrying once", out.getvalue())

    def test_retry_success_records_coreml_decision_and_providers(self):
        # AC-2: with the retried probe passing, the setup decision selects CoreML, records it in
        # the setup env cache, and heads the provider list with CoreML.
        import fastembed

        calls: list = []
        with patch.object(fastembed, "TextEmbedding", self._fake_embed_factory(1, calls)), \
                patch.object(self.mod, "_repair_probe_tempdir", return_value="temp directory present"), \
                patch.object(self.mod.provider_policy, "available_onnx_providers",
                             return_value=("CoreMLExecutionProvider", "CPUExecutionProvider")), \
                patch.object(self.mod, "_indexer_models", return_value=["m"]), \
                patch.dict(os.environ, {}, clear=True), \
                redirect_stdout(io.StringIO()):
            decision = self.mod.report_embedding_provider_decision()
            recorded = os.environ.get(self.mod.provider_policy.SETUP_SELECTED_ENV)
        self.assertEqual(decision.selected_provider, "CoreMLExecutionProvider")
        self.assertEqual(decision.providers[0], "CoreMLExecutionProvider")
        self.assertEqual(recorded, "CoreMLExecutionProvider")
        self.assertEqual(decision.provenance, "fresh-probe")

    def test_persistent_tempdir_failure_falls_back_with_actionable_reason(self):
        # AC-3: both attempts fail → fail-safe CPU with a reason naming the temp-dir failure and
        # the recovery path; exactly two attempts (retry bound 1).
        import fastembed

        calls: list = []
        with patch.object(fastembed, "TextEmbedding", self._fake_embed_factory(99, calls)), \
                patch.object(self.mod, "_repair_probe_tempdir", return_value="temp directory present"), \
                redirect_stdout(io.StringIO()):
            probe = self.mod._probe_embedding_provider(
                self.mod.provider_policy.COREML_PROVIDER, model_name="m")
        self.assertFalse(probe.ok)
        self.assertEqual(len(calls), 2)  # bounded: initial + one retry, never more
        self.assertIn("working directory", probe.reason)
        self.assertIn("wf setup", probe.reason)  # recovery guidance present

    def test_non_tempdir_failure_gets_no_retry_or_repair(self):
        # AC-5: a non-temp-dir failure shape is not retried and not repaired — fail-safe CPU.
        import fastembed

        class _BoomEmbed:
            count = 0

            def __init__(self, *a, **k):
                providers = k.get("providers") or []
                if len(providers) > 1:
                    type(self).count += 1
                    raise RuntimeError("some unrelated compile failure")

            def embed(self, texts):
                return [[0.1, 0.2] for _ in texts]

        with patch.object(fastembed, "TextEmbedding", _BoomEmbed), \
                patch.object(self.mod, "_repair_probe_tempdir") as repair:
            probe = self.mod._probe_embedding_provider(
                self.mod.provider_policy.COREML_PROVIDER, model_name="m")
        self.assertFalse(probe.ok)
        self.assertEqual(_BoomEmbed.count, 1)  # single attempt, no retry
        repair.assert_not_called()
        self.assertIn("unrelated compile failure", probe.reason)
        self.assertNotIn("wf setup", probe.reason)  # temp-dir guidance not misapplied

    def test_tempdir_failure_on_other_provider_gets_no_retry(self):
        # AC-5 guard: the retry is CoreML-scoped; the same error text on another provider is not retried.
        import fastembed

        calls: list = []
        with patch.object(fastembed, "TextEmbedding", self._fake_embed_factory(99, calls)), \
                patch.object(self.mod, "_repair_probe_tempdir") as repair:
            probe = self.mod._probe_embedding_provider("OpenVINOExecutionProvider", model_name="m")
        self.assertFalse(probe.ok)
        self.assertEqual(len(calls), 1)
        repair.assert_not_called()

    def test_repair_probe_tempdir_recreates_missing_dir_and_never_raises(self):
        import tempfile as _tf

        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "reaped-temp"
            with patch.object(_tf, "gettempdir", return_value=str(missing)):
                note = self.mod._repair_probe_tempdir()
            self.assertTrue(missing.exists())
            self.assertIn("recreated", note)
        with patch.object(_tf, "gettempdir", side_effect=RuntimeError("boom")):
            note = self.mod._repair_probe_tempdir()
        self.assertIn("repair failed", note)

    def test_repair_probe_tempdir_recreates_stale_tmpdir_env_path(self):
        # Delta-review finding: `gettempdir()` silently SKIPS an unusable TMPDIR candidate and
        # falls back to /tmp, so repairing only gettempdir()'s answer is a no-op in the
        # fresh-process stale-TMPDIR scenario. The TMPDIR tier repairs the directory CoreML
        # actually resolves there — derived from process env only, never from error text.
        with tempfile.TemporaryDirectory() as tmp:
            reaped = Path(tmp) / "var-folders-reaped" / "T"
            with patch.dict(os.environ, {"TMPDIR": str(reaped)}):
                note = self.mod._repair_probe_tempdir()
            self.assertTrue(reaped.exists())
            self.assertIn("recreated missing TMPDIR", note)
            if os.name != "nt":
                # Private perms on EVERY created level (cross-platform posture, not macOS-only):
                # Path.mkdir(parents=True, mode=...) would leave umask-default intermediates,
                # so _mkdir_private pins 0o700 on the leaf AND the created ancestor.
                self.assertEqual(reaped.stat().st_mode & 0o777, 0o700)
                self.assertEqual(reaped.parent.stat().st_mode & 0o777, 0o700)


class ProviderDecisionProvenanceTests(unittest.TestCase):
    """Wave 1p9lj AC-4: every provider decision names its source — setup-cache vs fresh-probe vs
    operator-request — and identical probe outcomes yield identical decisions (parity)."""

    def setUp(self):
        self.mod = load_setup_index()
        self.pp = self.mod.provider_policy

    def test_cached_decision_reports_setup_cache_provenance(self):
        with patch.dict(os.environ,
                        {self.pp.SETUP_SELECTED_ENV: "CoreMLExecutionProvider"}, clear=True):
            decision = self.pp.select_embedding_providers(
                available_providers=("CoreMLExecutionProvider", "CPUExecutionProvider"))
        self.assertEqual(decision.selected_provider, "CoreMLExecutionProvider")
        self.assertEqual(decision.provenance, "setup-cache")
        with patch.dict(os.environ, {self.pp.SETUP_SELECTED_ENV: "CPUExecutionProvider"}, clear=True):
            decision = self.pp.select_embedding_providers(
                available_providers=("CoreMLExecutionProvider", "CPUExecutionProvider"))
        self.assertEqual(decision.selected_provider, "CPUExecutionProvider")
        self.assertEqual(decision.provenance, "setup-cache")

    def test_fresh_probe_and_operator_request_provenance(self):
        probe = lambda provider: self.pp.ProviderProbeResult(provider, True, f"{provider} ok")
        with patch.dict(os.environ, {}, clear=True):
            fresh = self.pp.select_embedding_providers(
                available_providers=("CoreMLExecutionProvider", "CPUExecutionProvider"),
                provider_probe=probe)
        self.assertEqual(fresh.provenance, "fresh-probe")
        with patch.dict(os.environ, {self.pp.REQUESTED_PROVIDER_ENV: "cpu"}, clear=True):
            forced = self.pp.select_embedding_providers(
                available_providers=("CoreMLExecutionProvider", "CPUExecutionProvider"))
        self.assertEqual(forced.provenance, "operator-request")

    def test_operator_forced_gpu_paths_report_operator_request(self):
        # Second delivery-council finding: forced-CUDA (availability path) and forced-CoreML
        # (probe-pass path) must ALSO report operator-request — previously only forced-CPU did,
        # contradicting the field docstring and the shipped architecture doc.
        probe = lambda provider: self.pp.ProviderProbeResult(provider, True, f"{provider} ok")
        with patch.dict(os.environ, {self.pp.REQUESTED_PROVIDER_ENV: "cuda"}, clear=True):
            forced_cuda = self.pp.select_embedding_providers(
                available_providers=("CUDAExecutionProvider", "CPUExecutionProvider"))
        self.assertEqual(forced_cuda.selected_provider, "CUDAExecutionProvider")
        self.assertEqual(forced_cuda.provenance, "operator-request")
        with patch.dict(os.environ, {self.pp.REQUESTED_PROVIDER_ENV: "coreml"}, clear=True):
            forced_coreml = self.pp.select_embedding_providers(
                available_providers=("CoreMLExecutionProvider", "CPUExecutionProvider"),
                provider_probe=probe)
        self.assertEqual(forced_coreml.selected_provider, "CoreMLExecutionProvider")
        self.assertEqual(forced_coreml.provenance, "operator-request")
        # The CPU FALLBACK after a failed forced-GPU probe stays fresh-probe: the probe failure,
        # not the operator, drove that outcome.
        failing = lambda provider: self.pp.ProviderProbeResult(provider, False, "nope")
        with patch.dict(os.environ, {self.pp.REQUESTED_PROVIDER_ENV: "coreml"}, clear=True):
            fell_back = self.pp.select_embedding_providers(
                available_providers=("CoreMLExecutionProvider", "CPUExecutionProvider"),
                provider_probe=failing)
        self.assertEqual(fell_back.selected_provider, "CPUExecutionProvider")
        self.assertEqual(fell_back.provenance, "fresh-probe")

    def test_identical_probe_outcomes_yield_identical_decisions(self):
        # Parity: the doctor and setup share this exact function; given the same availability and
        # probe outcome, two invocations decide identically.
        probe = lambda provider: self.pp.ProviderProbeResult(provider, True, f"{provider} ok")
        with patch.dict(os.environ, {}, clear=True):
            first = self.pp.select_embedding_providers(
                available_providers=("CoreMLExecutionProvider", "CPUExecutionProvider"),
                provider_probe=probe)
            second = self.pp.select_embedding_providers(
                available_providers=("CoreMLExecutionProvider", "CPUExecutionProvider"),
                provider_probe=probe)
        self.assertEqual(first, second)

    def test_diagnostic_report_carries_decision_provenance(self):
        with patch.object(self.pp, "available_onnx_providers", return_value=("CPUExecutionProvider",)), \
                patch.object(self.pp, "nvidia_gpu_present", return_value=False), \
                patch.dict(os.environ, {}, clear=True):
            report = self.pp.diagnostic_report()
        self.assertIn("decision_provenance", report)
        self.assertEqual(report["decision_provenance"], "fresh-probe")
        rendered = self.pp.format_diagnostic_report(report)
        self.assertIn("decision source", rendered)

    def test_format_provider_decision_names_source(self):
        decision = self.pp.select_embedding_providers(
            available_providers=("CPUExecutionProvider",))
        self.assertIn("decision-source=", self.pp.format_provider_decision(decision))


if __name__ == "__main__":
    unittest.main()
