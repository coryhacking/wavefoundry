"""Change 1z8or: onnxruntime telemetry is disabled by default.

AC-1: ``venv_bootstrap`` defaults ``ORT_DISABLE_TELEMETRY=1`` when unset or empty, keeps
any other value (``"0"`` opts back in), and child processes inherit it.
AC-3: every non-test onnxruntime/fastembed import site calls
``venv_bootstrap.disable_onnxruntime_telemetry`` (a stubbed onnxruntime records the call),
and a stub without ``disable_telemetry_events`` does not raise.
DEL-F5 repair: ``ORT_DISABLE_TELEMETRY=0`` also makes the helper skip the API call.
AC-4: a standing AST scan fails on an import site that does not call the helper; a planted
scratch module proves the scan detects it (mutation control).
"""
from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

# Imported before any patch.dict(sys.modules): a C-extension package first imported inside the
# patched block would be dropped on exit and could not be imported again in this process.
import numpy  # noqa: F401

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import venv_bootstrap  # noqa: E402

ENV = venv_bootstrap.ORT_TELEMETRY_ENV
HELPER = "disable_onnxruntime_telemetry"
TELEMETRY_MODULES = {"onnxruntime", "fastembed"}


# ---------------------------------------------------------------------------
# AC-4: the standing scan
# ---------------------------------------------------------------------------

def _imported_telemetry_module(node: ast.AST) -> str | None:
    """The onnxruntime/fastembed module an AST node imports, or None.

    Predicate: ``import onnxruntime[...]`` / ``import fastembed[...]`` (any alias or submodule),
    absolute ``from onnxruntime|fastembed[...] import ...``, and ``importlib.import_module`` /
    ``__import__`` calls whose first argument is such a string constant.
    """
    if isinstance(node, ast.Import):
        for alias in node.names:
            top = alias.name.split(".")[0]
            if top in TELEMETRY_MODULES:
                return top
    elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        top = node.module.split(".")[0]
        if top in TELEMETRY_MODULES:
            return top
    elif isinstance(node, ast.Call) and node.args:
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        arg = node.args[0]
        if name in ("import_module", "__import__") and isinstance(arg, ast.Constant) \
                and isinstance(arg.value, str):
            top = arg.value.split(".")[0]
            if top in TELEMETRY_MODULES:
                return top
    return None


def _is_helper_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    return name == HELPER


def _scope_nodes(scope: ast.AST):
    """Every node in ``scope`` without descending into nested function/class scopes."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        stack.extend(ast.iter_child_nodes(node))


def scan_file(path: Path) -> tuple[list[str], list[str]]:
    """Return ``(sites, violations)`` for one file.

    A site is ``<qualified scope>:<line>``. It is a violation unless the same function (or
    module) scope contains a call to the helper on a later line.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    sites: list[str] = []
    violations: list[str] = []

    def visit(scope: ast.AST, qual: str) -> None:
        nodes = list(_scope_nodes(scope))
        helper_lines = [n.lineno for n in nodes if _is_helper_call(n)]
        for node in nodes:
            if _imported_telemetry_module(node) is not None:
                site = f"{qual or '<module>'}:{node.lineno}"
                sites.append(site)
                if not any(line > node.lineno for line in helper_lines):
                    violations.append(site)
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                visit(node, f"{qual}.{node.name}" if qual else node.name)

    visit(tree, "")
    return sites, violations


def scan_tree(root: Path) -> tuple[dict[str, list[str]], list[str]]:
    """Scan every non-test ``.py`` under ``root`` (``tests/`` and ``venv_bootstrap.py`` excluded)."""
    sites: dict[str, list[str]] = {}
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if rel.parts[0] == "tests" or "__pycache__" in rel.parts or rel.as_posix() == "venv_bootstrap.py":
            continue
        file_sites, file_violations = scan_file(path)
        if file_sites:
            sites[rel.as_posix()] = file_sites
        violations.extend(f"{rel.as_posix()}::{v}" for v in file_violations)
    return sites, sorted(violations)


# Scope census the dynamic AC-3 tests below cover, one entry per import site. The scan pins
# this set so a new import site also needs a stubbed-onnxruntime test.
EXPECTED_SCOPES = {
    "accel_embedder.py": [
        "_ensure_fastembed_model_cached", "StaticShapeEmbedder.__init__", "_available_gpu_providers",
        "make_embedder", "StaticShapeReranker.__init__", "make_reranker",
    ],
    "provider_policy.py": ["available_onnx_providers", "diagnostic_report"],
    "setup_index.py": ["_warm_model_inner", "_measure_embedding_provider"],
    "indexer.py": ["_get_embedder"],
    "wf_server/server_impl.py": ["_ensure_model_cached", "WaveIndex._get_embedder"],
    "benchmarks/embed_bench.py": ["_truncation_rate"],
}


class ImportSiteScanTests(unittest.TestCase):
    def test_every_framework_import_site_calls_the_helper(self):
        sites, violations = scan_tree(SCRIPTS)
        self.assertEqual(violations, [], "onnxruntime/fastembed import without "
                         f"venv_bootstrap.{HELPER}() in the same scope: {violations}")
        scopes = {f: sorted(s.rsplit(":", 1)[0] for s in v) for f, v in sites.items()}
        self.assertEqual(scopes, {f: sorted(v) for f, v in EXPECTED_SCOPES.items()},
                         "import-site census changed: add a stubbed-onnxruntime test for the new site")

    def test_scan_detects_a_planted_site_without_the_helper(self):
        # Mutation control: a scratch tree with one compliant and one non-compliant site.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / "tests" / "test_x.py").write_text("import onnxruntime\n", encoding="utf-8")
            (root / "good.py").write_text(
                "import venv_bootstrap\n"
                "def f():\n"
                "    import onnxruntime as ort\n"
                "    venv_bootstrap.disable_onnxruntime_telemetry(ort)\n",
                encoding="utf-8",
            )
            (root / "planted.py").write_text(
                "import venv_bootstrap\n"
                "def g():\n"
                "    venv_bootstrap.disable_onnxruntime_telemetry()\n"
                "    from fastembed import TextEmbedding\n"   # helper BEFORE the import: violation
                "def h():\n"
                "    import importlib\n"
                "    return importlib.import_module('onnxruntime')\n"
                "def k():\n"
                "    def inner():\n"
                "        disable_onnxruntime_telemetry()\n"    # nested scope does not count
                "    import onnxruntime\n"
                "    inner()\n",
                encoding="utf-8",
            )
            sites, violations = scan_tree(root)
            self.assertEqual(sorted(sites), ["good.py", "planted.py"])
            self.assertEqual(violations, ["planted.py::g:4", "planted.py::h:7", "planted.py::k:11"])
            # Repair the planted file: the scan goes clean.
            (root / "planted.py").write_text(
                "import venv_bootstrap\n"
                "def g():\n"
                "    from fastembed import TextEmbedding\n"
                "    venv_bootstrap.disable_onnxruntime_telemetry()\n",
                encoding="utf-8",
            )
            self.assertEqual(scan_tree(root)[1], [])


# ---------------------------------------------------------------------------
# AC-1: the environment default
# ---------------------------------------------------------------------------

_CHILD_PROBE = (
    "import os, subprocess, sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import venv_bootstrap\n"
    "child = subprocess.run([sys.executable, '-c', \"import os; print(repr(os.environ.get('%s')))\"],\n"
    "                       capture_output=True, text=True, check=True).stdout.strip()\n"
    "print(repr(os.environ.get('%s')) + '|' + child)\n"
) % (ENV, ENV)


class EnvironmentDefaultTests(unittest.TestCase):
    def _run(self, value: str | None) -> str:
        env = {k: v for k, v in os.environ.items() if k != ENV}
        if value is not None:
            env[ENV] = value
        out = subprocess.run([sys.executable, "-B", "-c", _CHILD_PROBE, str(SCRIPTS)],
                             env=env, capture_output=True, text=True, check=True, timeout=60)
        return out.stdout.strip()

    def test_unset_and_empty_default_to_one_and_children_inherit(self):
        self.assertEqual(self._run(None), "'1'|'1'")
        self.assertEqual(self._run(""), "'1'|'1'")

    def test_explicit_values_are_kept(self):
        self.assertEqual(self._run("0"), "'0'|'0'")   # the documented opt back in
        self.assertEqual(self._run("1"), "'1'|'1'")
        self.assertEqual(self._run("false"), "'false'|'false'")


# ---------------------------------------------------------------------------
# AC-3: the helper and every import site
# ---------------------------------------------------------------------------

class _Stop(Exception):
    """Raised by a patched downstream call so a site stops right after its import."""


def _stub_ort(calls: list | None) -> types.ModuleType:
    ort = types.ModuleType("onnxruntime")
    ort.__version__ = "0.0-stub"
    ort.get_available_providers = lambda: ["CPUExecutionProvider"]
    if calls is not None:
        ort.disable_telemetry_events = lambda: calls.append("disable_telemetry_events")
    return ort


def _stub_fastembed() -> types.ModuleType:
    fe = types.ModuleType("fastembed")

    class TextEmbedding:
        def __init__(self, *args, **kwargs):
            pass

        @staticmethod
        def list_supported_models():
            return []

        def embed(self, texts, *args, **kwargs):
            return iter([[0.0, 1.0] for _ in texts])

    fe.TextEmbedding = TextEmbedding
    return fe


def _load(name: str, rel: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return sys.modules[name]


class HelperTests(unittest.TestCase):
    def setUp(self):
        # These cases exercise the default; an operator's own opt-in must not leak in.
        patcher = patch.dict(os.environ, {ENV: "1"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_calls_disable_on_the_given_module(self):
        calls: list = []
        venv_bootstrap.disable_onnxruntime_telemetry(_stub_ort(calls))
        self.assertEqual(calls, ["disable_telemetry_events"])

    def test_uses_the_loaded_module_when_none_is_given(self):
        calls: list = []
        with patch.dict(sys.modules, {"onnxruntime": _stub_ort(calls)}):
            venv_bootstrap.disable_onnxruntime_telemetry()
        self.assertEqual(calls, ["disable_telemetry_events"])

    def test_tolerates_missing_function_missing_module_and_errors(self):
        venv_bootstrap.disable_onnxruntime_telemetry(_stub_ort(None))  # no function
        with patch.dict(sys.modules, {"onnxruntime": None}):
            venv_bootstrap.disable_onnxruntime_telemetry()  # module not loadable
        saved = sys.modules.pop("onnxruntime", None)
        try:
            venv_bootstrap.disable_onnxruntime_telemetry()  # never loaded: nothing imported
            self.assertNotIn("onnxruntime", sys.modules)
        finally:
            if saved is not None:
                sys.modules["onnxruntime"] = saved
        broken = _stub_ort(None)

        def boom():
            raise RuntimeError("telemetry api changed")

        broken.disable_telemetry_events = boom
        venv_bootstrap.disable_onnxruntime_telemetry(broken)


class OptInTests(unittest.TestCase):
    """DEL-F5: ``ORT_DISABLE_TELEMETRY=0`` opts back in to the API-controlled events too."""

    def _calls(self, value: str | None) -> list:
        calls: list = []
        env = {k: v for k, v in os.environ.items() if k != ENV}
        if value is not None:
            env[ENV] = value
        with patch.dict(os.environ, env, clear=True):
            venv_bootstrap.disable_onnxruntime_telemetry(_stub_ort(calls))
            with patch.dict(sys.modules, {"onnxruntime": _stub_ort(calls)}):
                venv_bootstrap.disable_onnxruntime_telemetry()
        return calls

    def test_unset_empty_and_one_call_the_api(self):
        for value in (None, "", "1"):
            with self.subTest(value=value):
                self.assertEqual(self._calls(value), ["disable_telemetry_events"] * 2)

    def test_zero_opts_back_in_and_skips_the_api(self):
        for value in ("0", " 0 "):
            with self.subTest(value=value):
                self.assertEqual(self._calls(value), [])

    def test_a_real_caller_honours_the_opt_in(self):
        # Through provider_policy.available_onnx_providers in a fresh process, with a recording
        # onnxruntime stub package first on sys.path. The bootstrap import defaults unset and
        # empty to "1" before the caller runs.
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "onnxruntime"
            stub.mkdir()
            record = Path(tmp) / "calls.txt"
            (stub / "__init__.py").write_text(
                "import os\n"
                "__version__ = '0.0-stub'\n"
                "def get_available_providers():\n"
                "    return ['CPUExecutionProvider']\n"
                "def disable_telemetry_events():\n"
                "    with open(os.environ['WF_TELEMETRY_RECORD'], 'a', encoding='utf-8') as fh:\n"
                "        fh.write('disable\\n')\n",
                encoding="utf-8",
            )
            probe = (
                "import sys\n"
                "sys.path[:0] = [sys.argv[1], sys.argv[2]]\n"
                "import provider_policy, onnxruntime\n"
                "assert onnxruntime.__version__ == '0.0-stub', onnxruntime.__file__\n"
                "print(provider_policy.available_onnx_providers())\n"
            )
            for value, expected in ((None, 1), ("", 1), ("1", 1), ("0", 0)):
                with self.subTest(value=value):
                    record.write_text("", encoding="utf-8")
                    env = {k: v for k, v in os.environ.items() if k != ENV}
                    env["WF_TELEMETRY_RECORD"] = str(record)
                    if value is not None:
                        env[ENV] = value
                    out = subprocess.run([sys.executable, "-B", "-c", probe, tmp, str(SCRIPTS)],
                                         env=env, capture_output=True, text=True, timeout=60)
                    self.assertEqual(out.returncode, 0, out.stderr)
                    self.assertIn("CPUExecutionProvider", out.stdout)
                    self.assertEqual(record.read_text(encoding="utf-8").count("disable"), expected)


class ImportSiteCallTests(unittest.TestCase):
    """Each site, driven with a stubbed onnxruntime: the recording stub sees the call, and a
    stub without ``disable_telemetry_events`` gives the same outcome (the helper never raises)."""

    @classmethod
    def setUpClass(cls):
        cls.ae = _load("_tele_accel_embedder", "accel_embedder.py")
        cls.pp = _load("_tele_provider_policy", "provider_policy.py")
        cls.si = _load("_tele_setup_index", "setup_index.py")
        cls.ix = _load("_tele_indexer", "indexer.py")
        cls.bench = _load("_tele_embed_bench", "benchmarks/embed_bench.py")
        from server_tools_support import load_server
        cls.srv = load_server()

    def _drive(self, run) -> None:
        outcomes = []
        for calls in ([], None):
            env = {k: v for k, v in os.environ.items()
                   if k not in ("WAVEFOUNDRY_EMBED_PROVIDER", "WAVEFOUNDRY_EMBED_PROVIDER_SELECTED")}
            env["WAVEFOUNDRY_DISABLE_RERANKER"] = ""
            env[ENV] = "1"  # the default; "0" would skip the call by design
            with patch.dict(os.environ, env, clear=True), patch.dict(sys.modules, {
                "onnxruntime": _stub_ort(calls),
                "fastembed": _stub_fastembed(),
                "onnx": types.ModuleType("onnx"),
                "tokenizers": None,  # stops the static-shape paths right after the helper
            }):
                try:
                    run()
                    outcomes.append("returned")
                except BaseException as exc:  # noqa: BLE001 — SystemExit included
                    outcomes.append(type(exc).__name__)
            if calls is not None:
                self.assertEqual(calls, ["disable_telemetry_events"], "the site did not call the helper")
        self.assertEqual(outcomes[0], outcomes[1], "a missing disable_telemetry_events changed the outcome")
        self.assertNotIn(outcomes[1], ("AttributeError", "TypeError"))

    # accel_embedder (6)
    def test_accel_ensure_fastembed_model_cached(self):
        self._drive(lambda: self.ae._ensure_fastembed_model_cached("stub/model"))

    def test_accel_static_shape_embedder_init(self):
        self._drive(lambda: self.ae.StaticShapeEmbedder("stub/model", ["CPUExecutionProvider"]))

    def test_accel_available_gpu_providers(self):
        self._drive(self.ae._available_gpu_providers)

    def test_accel_make_embedder(self):
        with patch.object(self.ae, "_available_gpu_providers", return_value=[]), \
             patch.object(self.ae, "_warn_cuda12_gap_if_present", return_value=None):
            self._drive(lambda: self.ae.make_embedder("stub/model", ["CPUExecutionProvider"]))

    def test_accel_static_shape_reranker_init(self):
        self._drive(lambda: self.ae.StaticShapeReranker("stub/model", ["CPUExecutionProvider"]))

    def test_accel_make_reranker(self):
        with patch.object(self.ae, "_available_gpu_providers", return_value=[]):
            self._drive(lambda: self.ae.make_reranker("stub/model", ["CPUExecutionProvider"]))

    # provider_policy (2)
    def test_provider_policy_available_onnx_providers(self):
        self._drive(self.pp.available_onnx_providers)

    def test_provider_policy_diagnostic_report(self):
        with patch.object(self.pp, "select_embedding_providers", side_effect=_Stop):
            self._drive(self.pp.diagnostic_report)

    # setup_index (2)
    def test_setup_index_warm_model_inner(self):
        self._drive(lambda: self.si._warm_model_inner("stub/model", local_files_only=True))

    def test_setup_index_measure_embedding_provider(self):
        # Wave 1zime (1zimk): the measurement runs in the probe child; this is its import site.
        with patch.object(self.si, "_indexer_models", side_effect=_Stop):
            self._drive(lambda: self.si._measure_embedding_provider("stub", model_name=None))

    # indexer (1)
    def test_indexer_get_embedder(self):
        with patch.object(self.ix, "accel_embedder", None), \
             patch.object(self.ix, "_onnx_providers", return_value=["CPUExecutionProvider"]), \
             patch.object(self.ix, "_text_embedding_cached_first", side_effect=_Stop), \
             patch.dict(self.ix._EMBEDDER_CACHE, {}, clear=True):
            self._drive(lambda: self.ix._get_embedder("stub/model"))

    # wf_server/server_impl (2)
    def test_server_ensure_model_cached(self):
        self._drive(lambda: self.srv._ensure_model_cached("stub/model", "embedding"))

    def test_server_wave_index_get_embedder(self):
        index = self.srv.WaveIndex.__new__(self.srv.WaveIndex)
        index._embedders = {}

        def constant(name):
            if name == "_precision_class_from_version":
                return lambda _version: "full"
            return "not-this-model"

        with patch.object(index, "_indexer_constant", side_effect=constant):
            self._drive(lambda: (index._embedders.clear(), index._get_embedder("stub/model")))

    # benchmarks/embed_bench.py (1)
    def test_embed_bench_truncation_rate(self):
        self._drive(lambda: self.bench._truncation_rate([], "stub/model"))


if __name__ == "__main__":
    unittest.main()
