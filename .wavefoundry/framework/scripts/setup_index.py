#!/usr/bin/env python3
"""Check index dependencies and build the Wavefoundry semantic index."""
from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import importlib.util
import json
import os
import queue
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True

FASTEMBED_CACHE_DEFAULT = Path.home() / ".wavefoundry" / "cache" / "fastembed"
if not os.environ.get("FASTEMBED_CACHE_PATH"):
    os.environ["FASTEMBED_CACHE_PATH"] = str(FASTEMBED_CACHE_DEFAULT)

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)
import provider_policy
import subprocess_util  # shared subprocess isolation (wave 1p8gu)
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)

# Wave 1p8gv: setup is a direct CLI entry (`wf update-indexes`, setup_wavefoundry step 1) that prints
# non-ASCII; reconfigure stdout/stderr to UTF-8 so it never raises on a cp1252 Windows console.
cli_stdio.configure_utf8_stdio()

TIMESTAMP_LOGS_ENV = "WAVEFOUNDRY_TIMESTAMP_LOGS"
# Wave 1p95j: pin lancedb to a validated version so every install site (setup + indexer auto-install)
# resolves the same build. 0.33.0 validated on this repo — clean single-FTS/single-vector index,
# retrieval parity with 0.30.2, full suite green, pyarrow unchanged. Single source of truth for both
# the setup dependency check below and indexer._auto_install_lancedb.
LANCEDB_REQUIREMENT = "lancedb==0.33.0"
REQUIRED_IMPORTS = {
    "fastembed": "fastembed",
    "httpx[socks]": "socksio",
    "igraph>=0.11": "igraph",
    "leidenalg>=0.10": "leidenalg",
    "numpy": "numpy",
    "mcp[cli]": "mcp",
    # Tree-sitter grammars for AST-accurate code chunking. chunker.py falls back to regex /
    # line-window chunkers when a grammar is absent.
    "tree-sitter>=0.24,<0.26": "tree_sitter",
    "tree-sitter-typescript": "tree_sitter_typescript",
    "tree-sitter-javascript": "tree_sitter_javascript",
    "tree-sitter-go": "tree_sitter_go",
    "tree-sitter-rust": "tree_sitter_rust",
    "tree-sitter-java": "tree_sitter_java",
    "tree-sitter-c": "tree_sitter_c",
    "tree-sitter-cpp": "tree_sitter_cpp",
    "tree-sitter-c-sharp": "tree_sitter_c_sharp",
    "tree-sitter-bash": "tree_sitter_bash",
    "tree-sitter-kotlin": "tree_sitter_kotlin",
    "tree-sitter-sql": "tree_sitter_sql",
    "tree-sitter-swift": "tree_sitter_swift",
    "tree-sitter-objc": "tree_sitter_objc",
    "tree-sitter-hcl": "tree_sitter_hcl",
    "tree-sitter-scss": "tree_sitter_scss",
    "tree-sitter-make": "tree_sitter_make",
    "tree-sitter-scala": "tree_sitter_scala",
    "tree-sitter-html": "tree_sitter_html",
    "tree-sitter-xml": "tree_sitter_xml",
    "tree-sitter-ruby": "tree_sitter_ruby",
    "tree-sitter-php": "tree_sitter_php",
    "tree-sitter-yaml": "tree_sitter_yaml",
    "tree-sitter-toml": "tree_sitter_toml",
    "tree-sitter-json": "tree_sitter_json",
    "tree-sitter-css": "tree_sitter_css",
    "tree-sitter-powershell": "tree_sitter_powershell",
    LANCEDB_REQUIREMENT: "lancedb",
    "networkx>=3.0": "networkx",
}
CUDA_DEPENDENCY_IMPORTS = {
    "fastembed-gpu": "fastembed",
}
# Wave 1p517/1p52p: `onnx` pins model input dims to a static shape. GPU embedders need it for the
# FP16 acceleration path; the CPU INT8 reranker also needs it to build its static 64x512 graph.
GPU_ACCEL_IMPORTS = {
    "onnx": "onnx",
}


class _TimestampedStream:
    """Line-buffering stream wrapper for log files."""

    def __init__(self, wrapped):
        self._wrapped = wrapped
        self._buffer = ""

    def write(self, text: str) -> int:
        if not text:
            return 0
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._wrapped.write(f"{_utc_log_timestamp()} {line}\n")
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            self._wrapped.write(f"{_utc_log_timestamp()} {self._buffer}")
            self._buffer = ""
        self._wrapped.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._wrapped, "isatty", lambda: False)())

    def __getattr__(self, name: str):
        return getattr(self._wrapped, name)


def _utc_log_timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def _enable_timestamped_stdio() -> None:
    sys.stdout = _TimestampedStream(sys.stdout)
    sys.stderr = _TimestampedStream(sys.stderr)

INDEXING_WORKFLOW_KEY = "indexing"
INCLUDE_FRAMEWORK_CODE_KEY = "include_framework_code_for_code_search"  # compatibility shim
PROJECT_INCLUDE_PREFIXES_KEY = "project_include_prefixes"
DOCS_PREFIXES_KEY = "docs"
CODE_PREFIXES_KEY = "code"


class ModelPrewarmError(RuntimeError):
    """Raised when a required model cache could not be prepared for setup."""


class ModelPrewarmTimeout(ModelPrewarmError):
    """Deadline abort of an in-process model warm (wave 1p9j0 DF-1). Distinct from a plain
    ``ModelPrewarmError`` because the abandoned warm thread may still be writing the model cache:
    the cache-corruption check would misread an in-flight download as corruption and the quarantine
    would move a directory with live open handles (a raw sharing violation on Windows). Callers
    that repair-and-retry on warm failure must let this propagate instead."""


def _tool_venv_python() -> Path:
    """Tool-venv Python path — delegates to the single resolver (wave 1p7pl)."""
    return venv_bootstrap.tool_venv_python()


def _rmtree_clearing_readonly(path: Path) -> None:
    """Wave 1p9hk: ``shutil.rmtree`` that clears the Windows read-only attribute and retries the failing
    op. On Windows a venv's pip-installed ``.pyd``/``.dll`` native extensions (onnxruntime/lancedb/
    fastembed) and mmap'd model artifacts are frequently read-only or held open, and ``os.remove`` raises
    ``PermissionError`` on a read-only file. Mirrors ``upgrade_wavefoundry._remove_deprecated_framework_
    index`` (wave 1p6d6). POSIX has no read-only-blocks-delete semantics, so the handler is a harmless
    no-op there. Unlike ``ignore_errors=True``, this does NOT hide a genuine failure: if a file is held
    open the handler swallows that single op, rmtree still returns, and the CALLER checks ``exists()``
    afterward to surface an actionable error rather than proceeding with a half-gutted venv."""
    def _clear_readonly_and_retry(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    _rm_kw = ({"onexc": _clear_readonly_and_retry} if sys.version_info >= (3, 12)
              else {"onerror": _clear_readonly_and_retry})
    shutil.rmtree(path, **_rm_kw)


def _bootstrap_venv(root: Path | None = None) -> Path:
    """Ensure the tool venv exists; return the path to its Python binary."""
    venv_python = _tool_venv_python()
    venv_dir = venv_python.parent.parent

    # Wave 1p9hk: track whether we attempted a recreate-triggering removal so we can distinguish a
    # healthy existing venv (leave it alone) from a venv we tried and FAILED to remove (surface an error).
    removal_attempted = False

    built_for = venv_bootstrap._venv_python_version(venv_dir)
    if venv_python.exists() and built_for is not None and built_for != sys.version_info[:2]:
        print(
            f"Tool venv at {venv_dir} was built for Python {built_for[0]}.{built_for[1]} "
            f"but setup is running on {sys.version_info[0]}.{sys.version_info[1]}; recreating ...",
            flush=True,
        )
        _rmtree_clearing_readonly(venv_dir)
        removal_attempted = True

    if venv_dir.exists() and not venv_python.exists():
        # Partial venv: directory present but Python binary absent — delete and recreate.
        print(f"Incomplete venv detected at {venv_dir}; recreating ...", flush=True)
        _rmtree_clearing_readonly(venv_dir)
        removal_attempted = True

    # Wave 1p9hk: if a removal was attempted but the directory is still present, rmtree could not fully
    # remove it — on Windows a running MCP host, IDE extension, or terminal commonly holds a .pyd/.dll
    # open (an unclearable lock, not just a read-only attribute). Previously ``ignore_errors=True`` hid
    # this, the ``if not venv_dir.exists()`` gate below was skipped, and _bootstrap_venv returned a
    # mismatched/half-gutted venv_python — the documented ``wf setup`` recovery path dead-ended silently.
    # Surface an actionable error instead of proceeding.
    if removal_attempted and venv_dir.exists():
        raise RuntimeError(
            f"Could not recreate the tool venv at {venv_dir}: a previous version could not be fully "
            f"removed. On Windows this usually means a running process is holding a file open — close "
            f"the MCP host (quit/restart your agent), any IDE extension using this project, and other "
            f"terminals, then rerun `wf setup`. If it persists, delete {venv_dir} manually and retry."
        )

    if not venv_dir.exists():
        print(f"Creating tool venv at {venv_dir} ...", flush=True)
        venv_timeout = _setup_deadlines(root)["venv_create_timeout_seconds"]
        try:
            subprocess_util.isolated_run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                check=True,
                timeout=venv_timeout,
            )
        except subprocess.TimeoutExpired:
            # Wave 1p9it: creating a venv is a LOCAL op, so a stall is almost always antivirus/endpoint
            # security scanning the new files, a slow/overloaded disk, or a filesystem lock — not the
            # network. Fail loud rather than hang.
            print(
                f"Tool-venv creation timed out after {venv_timeout:g}s (`python -m venv {venv_dir}`). "
                "A venv is a local operation, so a stall usually means realtime antivirus/endpoint "
                "security is scanning the new files, the disk is slow/overloaded, or a filesystem lock "
                "is held. Exclude the venv path from realtime AV / free the disk and rerun `wf setup`; "
                "raise `setup.venv_create_timeout_seconds` in docs/workflow-config.json if the machine "
                "is legitimately slow.",
                file=sys.stderr,
            )
            raise SystemExit(2)

    return venv_python


def _planned_required_imports() -> dict[str, str]:
    required = dict(REQUIRED_IMPORTS)
    if _should_plan_cuda_dependencies():
        required.update(CUDA_DEPENDENCY_IMPORTS)
    if _should_plan_gpu_accel_dependencies():
        required.update(GPU_ACCEL_IMPORTS)
    return required


def _should_plan_cuda_dependencies() -> bool:
    requested = os.environ.get(provider_policy.REQUESTED_PROVIDER_ENV, "auto").strip().lower()
    if requested in {"cpu", "coreml", "dml", "directml", "openvino", "migraphx", "rocm"}:
        return False
    return provider_policy.nvidia_gpu_present()


def _should_plan_gpu_accel_dependencies() -> bool:
    """Plan `onnx` when a static-shape model path can run.

    GPU embedders need it for CoreML/CUDA/ROCm/DirectML acceleration. Wave 1p52p also made the
    cross-encoder reranker hardware-selected: GPU uses FP16 and CPU uses INT8, but BOTH paths build a
    static ONNX graph. Therefore CPU-only installs still need `onnx` unless reranking is explicitly
    disabled.
    """
    if os.environ.get("WAVEFOUNDRY_DISABLE_RERANKER", "").strip().lower() in {"1", "true", "yes", "on"}:
        requested = os.environ.get(provider_policy.REQUESTED_PROVIDER_ENV, "auto").strip().lower()
        if requested == "cpu" or not (provider_policy.apple_silicon_present() or provider_policy.nvidia_gpu_present()):
            return False
    return True


def _missing_in_venv(venv_python: Path, required_imports: dict[str, str] | None = None) -> list[str]:
    """Return dist specs for packages that are absent OR whose installed version violates their pin.

    Wave 1p95u: the check is version-aware, not presence-only. A dependency is flagged when it is not
    importable (as before) OR when it carries a version constraint (e.g. ``lancedb==0.33.0``,
    ``tree-sitter>=0.24,<0.26``) and the version installed in the tool venv falls outside that
    specifier — so a pinned version bump reaches existing installs on ``wf setup`` / ``wave_upgrade``,
    not just fresh installs. The returned spec IS the ``REQUIRED_IMPORTS`` key, so ``_install_deps``
    resolves the venv to exactly the pinned version (an ``==`` pin downgrades a newer build; a range
    pin leaves any satisfying version untouched — see the change doc's Decision Log). Version checking
    uses ``packaging`` in the venv; if ``packaging`` is unavailable or a spec/version cannot be parsed,
    that dependency falls back to presence-only behavior (never raises, never spuriously reinstalls)."""
    required_imports = required_imports or _planned_required_imports()
    mod_to_dist = {mod: dist for dist, mod in required_imports.items()}
    gpu_dists = [dist for dist in CUDA_DEPENDENCY_IMPORTS if dist in required_imports]
    # Wave 1p95u: version-aware probe. Emits the dist spec (the REQUIRED_IMPORTS key) for anything
    # absent OR pin-violating, so _install_deps installs exactly the pinned version. GPU dists keep the
    # dist-name presence check (their import name collides with the CPU package, so find_spec can't tell
    # them apart). packaging is used for specifier satisfaction; any parse/metadata failure degrades to
    # presence-only for that dep (never raises, never spuriously reinstalls).
    probe_source = f'''\
import importlib.util
import importlib.metadata as metadata
mod_to_dist = {mod_to_dist!r}
gpu_dists = {gpu_dists!r}
try:
    from packaging.requirements import Requirement
    _HAVE_PACKAGING = True
except Exception:
    _HAVE_PACKAGING = False


def _violates(spec):
    if not _HAVE_PACKAGING:
        return False
    try:
        req = Requirement(spec)
        if not str(req.specifier):
            return False
        return not req.specifier.contains(metadata.version(req.name), prereleases=True)
    except Exception:
        return False


missing = []
for _mod, _dist in mod_to_dist.items():
    if importlib.util.find_spec(_mod) is None or _violates(_dist):
        if _dist not in missing:
            missing.append(_dist)
for _dist in gpu_dists:
    try:
        _name = Requirement(_dist).name if _HAVE_PACKAGING else _dist
    except Exception:
        _name = _dist
    try:
        metadata.version(_name)
        _present = True
    except metadata.PackageNotFoundError:
        _present = False
    if not _present or _violates(_dist):
        if _dist not in missing:
            missing.append(_dist)
print("\\n".join(missing))
'''
    # Wave 1p8pe: prefer the console-free tool-venv pythonw.exe on Windows for this captured import probe
    # so it does not flash a window; pythonw shares the same venv site-packages, so the probe result is
    # identical. Falls back to the passed-in venv Python (POSIX returns None).
    probe_interp = subprocess_util.windowless_pythonw() or str(venv_python)
    result = subprocess_util.isolated_run([probe_interp, "-c", probe_source], capture_output=True, text=True)
    if result.returncode != 0:
        return list(required_imports.keys())
    missing: list[str] = []
    for dist in (line.strip() for line in result.stdout.strip().splitlines()):
        if dist and dist not in missing:
            missing.append(dist)
    return missing


def _exclude_newer_cutoff(days: int = 21) -> str:
    """Return an ISO-8601 UTC timestamp for ``days`` ago — used as the uv --exclude-newer cutoff."""
    import datetime
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def _uv_bin(venv_python: Path) -> Path | None:
    """Return the path to a uv binary usable from the tool venv, or None if unavailable."""
    # Prefer uv installed inside the venv so it uses the same Python.
    venv_dir = venv_python.parent.parent
    candidates = [
        venv_dir / ("Scripts" if os.name == "nt" else "bin") / ("uv.exe" if os.name == "nt" else "uv"),
    ]
    # Fall back to uv on PATH.
    path_uv = shutil.which("uv")
    if path_uv:
        candidates.append(Path(path_uv))
    for candidate in candidates:
        # On Windows, os.X_OK doesn't test execute permission (the concept
        # doesn't exist); is_file() is sufficient since we look for uv.exe.
        if candidate.is_file() and (os.name == "nt" or os.access(candidate, os.X_OK)):
            return candidate
    return None


def _bootstrap_uv(venv_python: Path, root: Path | None = None) -> Path | None:
    """Install uv into the tool venv via pip and return its path, or None on failure."""
    print("uv not found — installing uv for package age enforcement ...", flush=True)
    uv_timeout = _setup_deadlines(root)["uv_bootstrap_timeout_seconds"]
    try:
        result = subprocess_util.isolated_run(
            [str(venv_python), "-m", "pip", "install", "uv"],
            check=False,
            env=_pip_tls_env(),
            timeout=uv_timeout,
        )
    except subprocess.TimeoutExpired:
        # Wave 1p9it: uv is an OPTIONAL supply-chain age guard; a stalled `pip install uv` (hung PyPI
        # fetch behind a corp MITM / flaky proxy) must not hang setup. Fail loud for THIS stage and fall
        # back to plain pip for the actual dependency install (which is itself deadline-bounded).
        print(
            f"Installing uv timed out after {uv_timeout:g}s (`pip install uv`). This is almost always a "
            "stalled PyPI fetch — check network/proxy/TLS reachability to https://pypi.org (corp MITM / "
            "flaky proxy). Falling back to plain pip without the package-age guard; raise "
            "`setup.uv_bootstrap_timeout_seconds` in docs/workflow-config.json if the network is "
            "legitimately slow.",
            file=sys.stderr,
        )
        return None
    if result.returncode != 0:
        return None
    return _uv_bin(venv_python)


def _install_deps(missing: list[str], venv_python: Path, root: Path | None = None) -> None:
    """Install missing packages into the tool venv.

    Prefers ``uv`` with ``--exclude-newer`` (21-day package age guard) to reduce
    supply-chain risk from newly published packages.  Falls back to plain pip when
    uv is not available and cannot be bootstrapped, but prints a prominent warning.
    """
    display = " ".join(
        f'"{dep}"' if ("[" in dep or ">=" in dep or "<" in dep) else dep
        for dep in missing
    )
    print(f"Installing missing dependencies: {display}", flush=True)

    uv = _uv_bin(venv_python) or _bootstrap_uv(venv_python, root)

    if uv is not None:
        cutoff = _exclude_newer_cutoff(days=21)
        print(f"Using uv with --exclude-newer {cutoff} (21-day package age guard)", flush=True)
        cmd = [
            str(uv), "pip", "install",
            "--python", str(venv_python),
            "--exclude-newer", cutoff,
        ] + missing
        # uv treats SSL_CERT_FILE as its EXCLUSIVE trust anchor; scrub it + use native TLS so a
        # corp bundle set for the model download cannot break uv's PyPI verification (wave 1p8tf).
        run_env = _uv_install_env()
    else:
        print(
            "WARNING: uv not available and could not be installed. "
            "Falling back to pip without package age enforcement. "
            "Install uv (https://docs.astral.sh/uv/) for supply-chain age checks.",
            file=sys.stderr,
        )
        cmd = [str(venv_python), "-m", "pip", "install"] + missing
        # pip cannot portably use the OS store; point it at the merged-superset bundle when one
        # exists so it reaches PyPI whether PyPI is public or MITM-intercepted (wave 1p8tf).
        run_env = _pip_tls_env()

    deps_timeout = _setup_deadlines(root)["dep_install_timeout_seconds"]
    try:
        result = subprocess_util.isolated_run(cmd, check=False, env=run_env, timeout=deps_timeout)
    except subprocess.TimeoutExpired:
        # Wave 1p9it: a stalled dependency download/resolve (hung PyPI fetch behind a corp MITM / flaky
        # proxy) is a Phase-1 hang path. Fail loud with network/proxy/TLS guidance rather than blocking
        # setup forever.
        installer = "uv" if uv is not None else "pip"
        print(
            f"Dependency install timed out after {deps_timeout:g}s ({installer}). A stalled package "
            "download/resolve is almost always a network/proxy/TLS problem — check reachability to "
            "https://pypi.org (corp MITM / flaky proxy / offline). Fix connectivity and rerun "
            "`wf setup`; raise `setup.dep_install_timeout_seconds` in docs/workflow-config.json if a "
            "legitimately slow link needs longer.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if result.returncode != 0:
        installer = "uv" if uv is not None else "pip"
        print(
            f"{installer} install failed (exit {result.returncode}). "
            "Check the output above and install manually, then rerun setup_index.py.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    print("Dependencies installed successfully.", flush=True)


def ensure_deps(root: Path | None = None) -> None:
    venv_python = _bootstrap_venv(root)
    required_imports = _planned_required_imports()
    missing = _missing_in_venv(venv_python, required_imports)
    if not missing:
        print(f"Dependencies satisfied ({', '.join(required_imports)})", flush=True)
        return
    _install_deps(missing, venv_python, root)
    still_missing = _missing_in_venv(venv_python, required_imports)
    if still_missing:
        print(
            f"Dependencies installed but still not importable: {', '.join(still_missing)}\n"
            "This may mean pip installed into a different environment. "
            "Try running setup_index.py with the correct Python interpreter.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def _reexec_with_venv_if_needed() -> None:
    """Activate the tool venv in-process — delegates to the single bootstrap (wave 1p7pl/1p802).

    No-ops when already in the venv or when it does not exist yet (fresh install,
    before ``ensure_deps()`` builds it), so it never blocks venv creation. (Name kept
    for back-compat with callers/tests; the behavior is now activate, not re-exec.)
    """
    venv_bootstrap.activate_tool_venv()


def _indexer_models(include_code: bool, code_only: bool = False) -> list[str]:
    indexer_path = SCRIPTS_DIR / "indexer.py"
    spec = importlib.util.spec_from_file_location("wavefoundry_indexer_for_setup", indexer_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    if code_only:
        models = [mod.CODE_MODEL]
    else:
        models = [mod.DOCS_MODEL]
    if include_code:
        models.append(mod.CODE_MODEL)
    deduped: list[str] = []
    for model in models:
        if model not in deduped:
            deduped.append(model)
    return deduped


def _indexer_reranker_model() -> str:
    indexer_path = SCRIPTS_DIR / "indexer.py"
    spec = importlib.util.spec_from_file_location("wavefoundry_indexer_for_setup", indexer_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.RERANKER_MODEL


def _load_indexer_module():
    indexer_path = SCRIPTS_DIR / "indexer.py"
    spec = importlib.util.spec_from_file_location("wavefoundry_indexer_for_setup", indexer_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _optimize_after_build(root: Path) -> None:
    """Wave 1p9aj: reclaim accumulated Lance-table bloat after the synchronous build.

    Runs on BOTH install and upgrade — upgrade's index rebuild invokes ``setup_index``. Lock-safe by
    placement: it runs after ``build_index`` has released the build lock and BEFORE any background code
    build is spawned, so it never races an in-flight build. Reclaim-only (the tiered ladder without a
    re-embed); best-effort — a lock conflict or any error just skips. This reclaims version-bloat that
    the fragment-gated incremental optimize can miss, and self-heals the Lance offset corruption."""
    try:
        mod = _load_indexer_module()
        index_dir = root / ".wavefoundry" / "index"
        results = mod.optimize_index_tables(index_dir)
    except Exception as exc:  # noqa: BLE001 - reclaim is best-effort
        print(f"index optimize skipped: {exc}", flush=True)
        return
    for name, res in (results or {}).items():
        before = int(res.get("bytes_before") or 0)
        after = int(res.get("bytes_after") or 0)
        if before and after < before:
            print(
                f"index optimize: reclaimed {name}.lance "
                f"({before:,} -> {after:,} bytes, tier {res.get('tier')})",
                flush=True,
            )


@contextlib.contextmanager
def _offline_env():
    prior = os.environ.get("HF_HUB_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    try:
        yield
    finally:
        if prior is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = prior


def _embedding_providers_for_setup() -> list[str]:
    selected = os.environ.get(provider_policy.SETUP_SELECTED_ENV)
    if selected and selected != provider_policy.CPU_PROVIDER:
        return [selected, provider_policy.CPU_PROVIDER]
    return [provider_policy.CPU_PROVIDER]


# 1p7iu: TLS-inspecting corporate proxies put the root CA in the OS trust store but not in the venv's
# bundled certifi, so model downloads fail CERTIFICATE_VERIFY_FAILED while curl/system tools succeed.
# These are POSIX paths only — on native Windows this middle "platform" tier is effectively empty
# (the OS trust store is the registry cert store, not a PEM file). Windows corporate-proxy users
# therefore rely on the host-agent / operator env tiers (`CODEX_CA_CERTIFICATE` /
# `CLAUDE_CODE_CERT_STORE` / `NODE_EXTRA_CA_CERTS` / `SSL_CERT_FILE`, wave 1p7s6)
# and the certifi-default last resort.
_OS_CA_BUNDLE_CANDIDATES = (
    "/etc/ssl/certs/ca-certificates.crt",   # Debian/Ubuntu/WSL2
    "/etc/pki/tls/certs/ca-bundle.crt",     # RHEL/CentOS/Fedora
    "/etc/ssl/ca-bundle.pem",               # OpenSUSE
    "/etc/ssl/cert.pem",                    # Alpine / macOS LibreSSL
)


# Wave 1p7s6: host coding agents expose their OWN CA-bundle env vars for corporate-proxy / private-root-CA
# environments — when set, the host has already declared the authoritative bundle. Codex's
# CODEX_CA_CERTIFICATE explicitly "takes precedence over SSL_CERT_FILE", so host-agent vars go FIRST.
_HOST_AGENT_CA_ENV_VARS = ("CODEX_CA_CERTIFICATE", "CLAUDE_CODE_CERT_STORE", "NODE_EXTRA_CA_CERTS")
_GENERIC_CA_ENV_VARS = ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE")
# Operator-stack CA env vars the fallback may pre-configure (the ones the TLS stack actually reads).
_STACK_CA_ENV_VARS = ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE")


def _certifi_default_bundle() -> "str | None":
    """The certifi default CA bundle path (the TLS baseline), or ``None`` if certifi is unavailable."""
    try:
        import certifi
        path = certifi.where()
    except Exception:  # noqa: BLE001
        return None
    return path if path and os.path.isfile(path) else None


def _os_trust_store_candidates() -> "list[str]":
    """Ordered, de-duplicated list of trusted CA bundles to try, most-authoritative first (wave 1p7s6).

    Order (Req 1 / Req 5): host-agent vars (``CODEX_CA_CERTIFICATE`` → ``CLAUDE_CODE_CERT_STORE`` →
    ``NODE_EXTRA_CA_CERTS``) → operator vars (``SSL_CERT_FILE`` → ``REQUESTS_CA_BUNDLE``) → platform OS-trust-store locations →
    **the certifi default as the final fallback** (so a wrong/stale host-agent var can never make
    recovery worse than today's certifi-first baseline). Only existing files are included. Verification
    stays ON for every candidate — this only selects WHICH trusted bundle to verify against."""
    candidates: list[str] = []
    seen: set[str] = set()

    def _add(path: "str | None") -> None:
        if path and os.path.isfile(path) and path not in seen:
            seen.add(path)
            candidates.append(path)

    for env in (*_HOST_AGENT_CA_ENV_VARS, *_GENERIC_CA_ENV_VARS):
        _add(os.environ.get(env))
    for path in _OS_CA_BUNDLE_CANDIDATES:
        _add(path)
    _add(_certifi_default_bundle())
    return candidates


def _os_trust_store_bundle() -> "str | None":
    """First trusted CA bundle from the ordered candidate list (wave 1p7s6), or ``None``.

    Back-compat thin accessor over ``_os_trust_store_candidates`` (host-agent vars → operator vars →
    platform locations → certifi default). Verification stays ON — never disables verification."""
    candidates = _os_trust_store_candidates()
    return candidates[0] if candidates else None


_CA_MERGE_CACHE_DIR = Path.home() / ".wavefoundry" / "cache" / "ca"
_CERT_BLOCK_RE = re.compile(
    r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
    re.DOTALL,
)
# uv (and the rustls/reqwest stack under it) treats SSL_CERT_FILE as its EXCLUSIVE trust anchor — it
# loads ONLY that file and rejects the rest of the chain. A single corporate-root PEM (set so the
# certifi-based fastembed/HuggingFace model download trusts a TLS-intercepting proxy) therefore
# breaks `uv pip install` against PyPI. These are the vars that poison uv; scrub them from uv's
# child env and let uv use the OS/native store instead (wave 1p8tf).
_UV_TLS_SCRUB_VARS = ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "SSL_CERT_DIR")


def _merged_trust_bundle() -> "str | None":
    """A single merged-superset CA bundle: the union of every readable trust store the host already
    trusts (host-agent vars → operator vars → platform stores → certifi), deduped by certificate
    block (wave 1p8tf). Additive to the per-store ladder in ``_warm_model`` — that ladder is unchanged.

    Why a union: a consumer that reads ONE bundle file (pip points requests at a single
    ``SSL_CERT_FILE``; uv treats it as its exclusive anchor) can then validate BOTH a corporate-MITM
    host AND a public host like PyPI from the same file. Built only when the environment signals a
    corporate/proxy trust setup (a host-agent CA var or an operator ``SSL_CERT_FILE`` /
    ``REQUESTS_CA_BUNDLE`` is set) AND at least two stores contribute — a plain environment returns
    ``None`` so the default certifi/OS path is unchanged. Tolerates unreadable/malformed candidates
    (skipped). Verification stays ON — this only widens trust to the union the host already trusts."""
    has_corp_material = any(
        os.environ.get(v) for v in (*_HOST_AGENT_CA_ENV_VARS, *_GENERIC_CA_ENV_VARS)
    )
    if not has_corp_material:
        return None
    blocks: list[str] = []
    seen: set[str] = set()
    sources = 0
    for path in _os_trust_store_candidates():
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        added = False
        for block in _CERT_BLOCK_RE.findall(text):
            key = "".join(block.split())
            if key and key not in seen:
                seen.add(key)
                blocks.append(block.strip())
                added = True
        if added:
            sources += 1
    if not blocks or sources < 2:
        return None
    payload = "\n".join(blocks) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    out = _CA_MERGE_CACHE_DIR / f"merged-ca-{digest}.pem"
    try:
        _CA_MERGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if not out.exists():
            out.write_text(payload, encoding="utf-8")
    except OSError:
        return None
    return str(out)


def _uv_install_env() -> "dict[str, str] | None":
    """Child env for a ``uv`` invocation, or ``None`` to inherit unchanged (wave 1p8tf).

    Returns ``None`` (inherit) when no CA-file env var is set — the conflict only arises when
    ``SSL_CERT_FILE`` (or a peer) is present, so a plain environment is untouched. Otherwise copies
    ``os.environ`` (never mutates it), scrubs the vars uv treats as an exclusive anchor, and sets
    ``UV_NATIVE_TLS=1`` so uv verifies against the OS/platform trust store. Verification stays ON."""
    if not any(os.environ.get(v) for v in _UV_TLS_SCRUB_VARS):
        return None
    env = dict(os.environ)
    for var in _UV_TLS_SCRUB_VARS:
        env.pop(var, None)
    env["UV_NATIVE_TLS"] = "1"
    return env


def _pip_tls_env() -> "dict[str, str] | None":
    """Child env for a ``pip`` invocation, or ``None`` to inherit unchanged (wave 1p8tf).

    Unlike uv, pip cannot portably use the OS trust store, so point it at the merged-superset bundle
    (corp + certifi roots) when one exists so pip reaches PyPI whether PyPI is public or
    MITM-intercepted. Copies ``os.environ`` (never mutates it). Returns ``None`` (inherit) in a plain
    environment where no merged bundle is built. Verification stays ON."""
    merged = _merged_trust_bundle()
    if not merged:
        return None
    env = dict(os.environ)
    env["SSL_CERT_FILE"] = merged
    env["REQUESTS_CA_BUNDLE"] = merged
    return env


def _is_cert_verify_error(exc: BaseException) -> bool:
    """True if exc (or its cause/context chain) is a TLS CERTIFICATE_VERIFY_FAILED."""
    seen: set[int] = set()
    cur: "BaseException | None" = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if "certificate verify failed" in f"{type(cur).__name__}: {cur}".lower():
            return True
        cur = cur.__cause__ or cur.__context__
    return False


def _host_agent_ca_bundle() -> "str | None":
    """The first host-agent CA env var (``CODEX_CA_CERTIFICATE`` → ``CLAUDE_CODE_CERT_STORE`` →
    ``NODE_EXTRA_CA_CERTS``) that
    points at a real file (wave 1p7s6), or ``None``. A set one implies a TLS-intercepting environment."""
    for env in _HOST_AGENT_CA_ENV_VARS:
        val = os.environ.get(env)
        if val and os.path.isfile(val):
            return val
    return None


def _apply_ca_bundle(bundle: str) -> None:
    """Point the TLS stack's CA env vars at ``bundle`` and rebuild huggingface_hub's cached session.

    huggingface_hub (which fastembed's snapshot_download uses) caches a GLOBAL httpx.Client whose SSL
    context is built ONCE — setting the env after the client exists is a no-op against it. ``close_session``
    (documented for exactly "an SSL certificate updated") forces the next request to rebuild the client
    against ``bundle``. Verification stays ON — this only swaps WHICH trusted bundle is verified against."""
    os.environ["SSL_CERT_FILE"] = bundle
    os.environ["REQUESTS_CA_BUNDLE"] = bundle
    try:
        import huggingface_hub
        huggingface_hub.close_session()
    except Exception:  # noqa: BLE001
        pass


_ca_bundle_apply_attempted = False
_ca_bundle_apply_lock = threading.Lock()


def ensure_ca_bundle_applied() -> None:
    """Idempotent, process-wide proactive CA-bundle application for launchers that don't go through
    ``_warm_model``'s full retry ladder (wave 1p939: MCP ``wave_index_build``, the dashboard's
    file-watcher, the server's background index refresh, and the server's own model-cache/embedder
    paths). Mirrors ``_warm_model``'s proactive pre-config: an operator-set stack CA env
    (``SSL_CERT_FILE``/``REQUESTS_CA_BUNDLE``) always wins and is left untouched; otherwise, a
    host-agent CA var (``CODEX_CA_CERTIFICATE``/``CLAUDE_CODE_CERT_STORE``/``NODE_EXTRA_CA_CERTS``)
    pointing at a real file is applied. The module-level flag (lock-protected: the long-lived MCP
    server process can reach this from more than one worker thread, delivery-phase council finding)
    makes every call after the first a no-op (AC-3: zero added cost on a hot path that calls this on
    every download attempt). Unlike ``_warm_model``, this does NOT restore the mutated env on exit:
    the launcher processes that call it (short-lived indexer subprocesses, or the long-lived MCP
    server) never themselves shell out to ``uv``/``pip`` in the same process, so the env-leak risk
    that motivates ``_warm_model``'s try/finally restore does not apply here (change doc 1p92t
    Decision Log)."""
    global _ca_bundle_apply_attempted
    with _ca_bundle_apply_lock:
        if _ca_bundle_apply_attempted:
            return
        _ca_bundle_apply_attempted = True
        if any(os.environ.get(v) for v in _STACK_CA_ENV_VARS):
            return  # operator already configured their own trust anchor — never override it
        bundle = _host_agent_ca_bundle()
        if bundle is not None:
            _apply_ca_bundle(bundle)


def raise_with_ca_bundle_diagnostic(model_name: str, exc: BaseException) -> None:
    """Re-raise ``exc`` with operator CA-var guidance when it is a CERTIFICATE_VERIFY_FAILED that
    persisted after ``ensure_ca_bundle_applied()`` (wave 1p939); re-raises ``exc`` unchanged
    otherwise. Mirrors ``_warm_model``'s terminal diagnostic message so the operator gets the same
    actionable guidance regardless of which launcher hit the failure."""
    if not _is_cert_verify_error(exc):
        raise exc
    raise ModelPrewarmError(
        f"Model '{model_name}' download failed TLS verification (CERTIFICATE_VERIFY_FAILED). Behind a "
        "TLS-inspecting proxy or with a private root CA, point the CA bundle at the right store and "
        "retry — set your host agent's CA var (CODEX_CA_CERTIFICATE / CLAUDE_CODE_CERT_STORE / "
        "NODE_EXTRA_CA_CERTS) or the generic SSL_CERT_FILE / REQUESTS_CA_BUNDLE, e.g. "
        "export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt "
        "REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt"
    ) from exc


def retry_with_ca_bundle_ladder(attempt, model_name: str):
    """Call ``attempt()`` (a zero-arg callable performing one model-download attempt). On a
    CERTIFICATE_VERIFY_FAILED, walk the REACTIVE candidate ladder ``_warm_model`` already uses on a
    confirmed failure — ``_os_trust_store_candidates()`` (host-agent vars -> operator vars -> platform
    OS-bundle paths -> certifi default) — retrying ``attempt()`` once per untried candidate, applying
    each via ``_apply_ca_bundle`` first (wave 1p939 delivery-phase council finding:
    ``ensure_ca_bundle_applied()`` alone only covers the PROACTIVE host-agent-var rung, never this
    reactive ladder, so a corporate-proxy environment whose only working trust rung is an OS-bundle
    file remained broken for non-setup launchers even though ``wf setup`` succeeds there). Mirrors
    ``_warm_model``'s reactive loop minus its interactive ``print()`` progress messages and its
    restore-on-exit (already separately justified as unnecessary at these call sites, change doc
    1p92t Decision Log). Re-raises a non-cert-verify error unchanged. When every candidate also fails
    a cert-verify check, raises via ``raise_with_ca_bundle_diagnostic``. Returns ``attempt()``'s
    result on success."""
    try:
        return attempt()
    except Exception as exc:
        if not _is_cert_verify_error(exc):
            raise
        last_exc: BaseException = exc
    tried = {v for v in (os.environ.get(k) for k in _STACK_CA_ENV_VARS) if v}
    if not tried:
        certifi_default = _certifi_default_bundle()
        if certifi_default is not None:
            tried.add(certifi_default)
    for bundle in _os_trust_store_candidates():
        if bundle in tried:
            continue
        tried.add(bundle)
        _apply_ca_bundle(bundle)
        try:
            return attempt()
        except Exception as retry_exc:
            if not _is_cert_verify_error(retry_exc):
                raise
            last_exc = retry_exc
            continue
    raise_with_ca_bundle_diagnostic(model_name, last_exc)


def _warm_model(model_name: str, *, local_files_only: bool, deadline_seconds: float | None = None) -> None:
    """Bounded in-process model warm (wave 1p9it). Runs the reactive CA-retry warm ladder
    (``_warm_model_inner``) under a wall-clock deadline so a hung TLS model fetch behind a corp
    MITM/flaky proxy fails loud with model-download reachability guidance instead of stalling setup
    forever. The deadline is the explicit ``deadline_seconds`` when given, else the per-run value
    ``main`` set from workflow-config (``setup.model_warm_timeout_seconds``), else
    ``MODEL_WARM_TIMEOUT_DEFAULT``. Within the deadline this behaves exactly as before — the full
    CA-retry ladder runs inside the bounded attempt and its error semantics are preserved."""
    if deadline_seconds is None:
        deadline_seconds = _ACTIVE_MODEL_WARM_DEADLINE_SECONDS or MODEL_WARM_TIMEOUT_DEFAULT
    _run_in_process_with_deadline(
        lambda: _warm_model_inner(model_name, local_files_only=local_files_only),
        deadline_seconds=deadline_seconds,
        timeout_error=ModelPrewarmTimeout(
            f"Model '{model_name}' warm exceeded the {deadline_seconds:g}s deadline and was aborted. A "
            "hung model download is almost always a network/proxy/TLS problem — check reachability to "
            "the model host (Hugging Face) behind a corp MITM / flaky proxy, or point the CA bundle at "
            "the right store (SSL_CERT_FILE / REQUESTS_CA_BUNDLE / host-agent CA var). Raise "
            "`setup.model_warm_timeout_seconds` in docs/workflow-config.json if the link is legitimately "
            "slow. If the network is healthy, a corrupted model cache can also hang the warm — clear "
            "the fastembed cache directory (FASTEMBED_CACHE_PATH, default ~/.wavefoundry/cache/fastembed) "
            "and rerun."
        ),
    )


def _warm_model_inner(model_name: str, *, local_files_only: bool) -> None:
    from fastembed import TextEmbedding

    def _build() -> None:
        embedding = TextEmbedding(
            model_name=model_name,
            local_files_only=local_files_only,
            providers=_embedding_providers_for_setup(),
        )
        next(iter(embedding.embed(["wavefoundry cache verification"])))

    # Scope/restore the operator's original stack CA env (security finding, Req 2/3): per-attempt env
    # mutation must never silently discard a set SSL_CERT_FILE/REQUESTS_CA_BUNDLE. The TRUE original is
    # snapshotted ONCE here; when the operator HAD set their env, a try/finally restores it on EVERY exit
    # (success or failure) so a clobbered trust anchor can never leak out. When the operator left it
    # unset, the winning bundle is left in place on success (so the rest of the run reuses it).
    _orig_stack_env = {k: os.environ.get(k) for k in _STACK_CA_ENV_VARS}
    _operator_set_stack = any(v is not None for v in _orig_stack_env.values())
    _tried: set[str] = set()

    def _restore_stack_env() -> None:
        for k, v in _orig_stack_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    _succeeded = False
    try:
        # Proactive pre-config (Req 2): when a host-agent CA var points at a real file and the operator's
        # stack CA env is UNSET, configure the bundle from it BEFORE the first fetch — a set host-agent
        # var implies a TLS-intercepting env where the default certifi bundle fails anyway, so this skips
        # the guaranteed-fail certifi round-trip. (When the operator set their own, that always wins.)
        proactive = None
        if not _operator_set_stack:
            proactive = _host_agent_ca_bundle()
            if proactive is not None:
                print(
                    f"Host-agent CA bundle detected; configuring the model fetch for '{model_name}' "
                    f"against it before the first attempt ({proactive}). TLS verification stays ON.",
                    flush=True,
                )
                _apply_ca_bundle(proactive)
                _tried.add(proactive)

        try:
            _build()
            _succeeded = True
            return
        except Exception as exc:  # noqa: BLE001
            # Only intervene on a genuine cert-verify failure during an ONLINE fetch — never a cache
            # miss (local_files_only) or any other error.
            if local_files_only or not _is_cert_verify_error(exc):
                raise
            # Mark the bundle the FIRST attempt effectively used so the iteration does not re-run it:
            # if the operator set their own stack CA env, that bundle was used; otherwise the attempt
            # ran against the certifi default. (The proactive bundle, if any, is already in _tried.)
            if proactive is None:
                if _operator_set_stack:
                    for k in _STACK_CA_ENV_VARS:
                        v = _orig_stack_env.get(k)
                        if v and os.path.isfile(v):
                            _tried.add(v)
                else:
                    certifi_default = _certifi_default_bundle()
                    if certifi_default is not None:
                        _tried.add(certifi_default)

            # Candidate iteration (Req 5): host-agent → operator → platform → certifi-default last.
            # Each tried at most once; verification stays ON; rebuild the hf session between attempts.
            for bundle in _os_trust_store_candidates():
                if bundle in _tried:
                    continue
                _tried.add(bundle)
                print(
                    f"Model download for '{model_name}' failed TLS verification; retrying against the "
                    f"trust store ({bundle}). TLS verification stays ON.",
                    flush=True,
                )
                _apply_ca_bundle(bundle)
                try:
                    _build()
                    _succeeded = True
                    return
                except Exception as retry_exc:  # noqa: BLE001
                    if not _is_cert_verify_error(retry_exc):
                        raise
                    # cert-verify failed for this bundle too — degrade to the next candidate.
                    continue

            # Every candidate failed cert-verify — fail loud.
            raise ModelPrewarmError(
                f"Model '{model_name}' download failed TLS verification (CERTIFICATE_VERIFY_FAILED) and "
                "no trusted CA bundle resolved it. Behind a TLS-inspecting proxy or with a private root "
                "CA, point the CA bundle at the right store and retry — set your host agent's CA var "
                "(CODEX_CA_CERTIFICATE / CLAUDE_CODE_CERT_STORE / NODE_EXTRA_CA_CERTS) or the generic "
                "SSL_CERT_FILE / REQUESTS_CA_BUNDLE, e.g. export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt "
                "REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt"
            ) from exc
    finally:
        # Restore the operator's TRUE original stack CA env on EVERY exit when they had set it (a
        # clobbered trust anchor must never leak out — success or failure). When the operator left it
        # unset, leave the winning bundle in place on success, but restore (pop) on failure so a
        # non-working bundle is not left set.
        if _operator_set_stack or not _succeeded:
            _restore_stack_env()


# Wave 1p9lj: the Apple CoreML framework error raised when the model-compile working directory
# under the per-user temp root (/var/folders/.../T/) is unusable — the one transient failure shape
# the probe retries. The text is not a stable API contract, so the marker set stays narrow: an
# unrecognized failure shape falls back to CPU fail-safe (protects AC-5).
_COREML_TEMPDIR_ERROR_MARKERS: tuple[str, ...] = ("Failed to create a working directory",)


def _is_coreml_tempdir_error(exc: BaseException) -> bool:
    text = str(exc)
    return any(marker in text for marker in _COREML_TEMPDIR_ERROR_MARKERS)


def _mkdir_private(path: Path) -> None:
    """Create ``path`` and any missing ancestors, EACH with mode 0o700 — private per-user temp
    permissions on every platform (macOS ships /var/folders per-user dirs 0700; the same posture
    applies to Linux/WSL2 temp paths; the mode is a harmless no-op on Windows ACL filesystems).
    ``Path.mkdir(parents=True, mode=...)`` applies the mode only to the LEAF, leaving umask-default
    intermediates, so missing ancestors are created explicitly bottom-up. Existing directories are
    never touched or chmod'd."""
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        if current.parent == current:
            break
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700, exist_ok=True)


def _repair_probe_tempdir() -> str:
    """Cheap, bounded repair for the CoreML compile working-directory failure (wave 1p9lj): recreate
    the process temp directory if macOS periodic cleanup reaped it while a stale path lingered in
    TMPDIR. Two env-derived tiers (the repair target NEVER comes from error text — security
    boundary): (1) a set-but-absent ``TMPDIR`` path is recreated directly, because
    ``tempfile.gettempdir()`` silently skips an unusable candidate and falls back to ``/tmp`` —
    repairing the fallback would miss the directory CoreML actually resolves in a fresh process
    with a stale TMPDIR; (2) the ``gettempdir()`` answer is recreated when missing, covering the
    mid-process-reap window where the stale path is already cached in ``tempfile.tempdir``.
    Every created directory (including intermediates, on every platform) gets private 0o700 via
    ``_mkdir_private``. Best-effort — a failure to repair only means the single retry probes the
    unrepaired state. Never raises."""
    import tempfile

    try:
        notes: list[str] = []
        env_tmp = os.environ.get("TMPDIR")
        if env_tmp:
            env_path = Path(env_tmp)
            if not env_path.exists():
                _mkdir_private(env_path)
                notes.append(f"recreated missing TMPDIR {env_path}")
        tmp = Path(tempfile.gettempdir())
        if not tmp.exists():
            _mkdir_private(tmp)
            notes.append(f"recreated missing temp directory {tmp}")
        if not notes:
            notes.append(f"temp directory {tmp} present")
        return "; ".join(notes)
    except Exception as exc:  # noqa: BLE001 — repair is best-effort by contract
        return f"temp-directory repair failed ({type(exc).__name__}: {exc})"


_COREML_TEMPDIR_RECOVERY = (
    "CoreML could not create its model-compile working directory (macOS may have reaped the "
    "per-user temp dir under /var/folders while a stale path lingered in TMPDIR); a bounded "
    "repair+retry already ran. Recovery: open a fresh shell (re-resolves TMPDIR) or clear a stale "
    "TMPDIR override, then rerun `wf setup`. The build continues on CPU (slower, correct)."
)


def _probe_embedding_provider(provider: str, *, model_name: str | None = None) -> provider_policy.ProviderProbeResult:
    """Bounded correctness/performance probe for providers that need model proof.

    Wave 1p9lj: a CoreML failure matching the known temp-working-directory shape gets ONE bounded
    repair+retry INSIDE this probe — before any decision is recorded to
    ``WAVEFOUNDRY_EMBED_PROVIDER_SELECTED`` — so a transient temp-dir failure no longer pins the
    whole build to CPU while `wave_gpu_doctor` later accepts CoreML. The retry never applies to any
    other failure shape (shape mismatch, non-finite vectors, other compile errors stay fail-safe),
    and there is no post-decision re-enable (the cached-CPU decision remains the native-crash guard
    honored by ``accel_embedder``)."""
    import math
    import time as _time

    from fastembed import TextEmbedding

    model = model_name or _indexer_models(include_code=False)[0]
    sample = [
        "wavefoundry provider verification",
        "A short setup probe is not representative of a full semantic index rebuild.",
        "Provider selection should compare realistic embedding work across multiple chunks.",
        "The Wavefoundry framework index includes prompt docs, architecture docs, wave records, and code snippets.",
        "CoreMLExecutionProvider can be available while still partitioning meaningful work back to CPU.",
        "CUDA, CoreML, DirectML, OpenVINO, MIGraphX, ROCm, and CPU have different provider behavior.",
        "This bounded probe uses a mixed text batch so setup does not choose a provider based on one tiny input.",
        "If a provider cannot beat CPU by a material margin for the active model, CPU remains the default.",
    ]
    for attempt in range(2):
        try:
            # Run one unmeasured warm pass for each provider, then time the second pass.
            # FastEmbed and ONNX Runtime both do lazy setup that would otherwise dominate
            # a tiny benchmark and make CoreML look better than a full-corpus rebuild.
            # SERIAL ONLY (wave 1p8vc): every `embed()` below runs with the default `parallel=None`
            # (serial inline path). Do NOT pass `parallel=` here — this probe runs in-process inside the
            # MCP server (wave_gpu_doctor), and fastembed's parallel path spawns workers that re-load ORT
            # and would write cold-load diagnostics to the inherited MCP stdout fd, corrupting JSON-RPC.
            cpu_embedding = TextEmbedding(
                model_name=model,
                local_files_only=True,
                providers=[provider_policy.CPU_PROVIDER],
            )
            list(cpu_embedding.embed(sample))
            started = _time.perf_counter()
            cpu_vectors = [list(vector) for vector in cpu_embedding.embed(sample)]
            cpu_seconds = _time.perf_counter() - started

            candidate_embedding = TextEmbedding(
                model_name=model,
                local_files_only=True,
                providers=[provider, provider_policy.CPU_PROVIDER],
            )
            list(candidate_embedding.embed(sample))
            started = _time.perf_counter()
            candidate_vectors = [list(vector) for vector in candidate_embedding.embed(sample)]
            candidate_seconds = _time.perf_counter() - started
            break
        except Exception as exc:
            coreml_tempdir = (
                provider == provider_policy.COREML_PROVIDER and _is_coreml_tempdir_error(exc)
            )
            if coreml_tempdir and attempt == 0:
                repair_note = _repair_probe_tempdir()
                print(
                    f"CoreML probe hit a temp working-directory failure; {repair_note}; retrying once.",
                    flush=True,
                )
                continue
            reason = f"{type(exc).__name__}: {exc}"
            if coreml_tempdir:
                reason = f"{reason}. {_COREML_TEMPDIR_RECOVERY}"
            return provider_policy.ProviderProbeResult(provider, False, reason)

    if len(candidate_vectors) != len(cpu_vectors) or not candidate_vectors:
        return provider_policy.ProviderProbeResult(provider, False, "embedding shape mismatch")
    for candidate_vector, cpu_vector in zip(candidate_vectors, cpu_vectors):
        if len(candidate_vector) != len(cpu_vector):
            return provider_policy.ProviderProbeResult(provider, False, "embedding shape mismatch")
        if not all(math.isfinite(float(value)) for value in candidate_vector):
            return provider_policy.ProviderProbeResult(provider, False, "embedding contains non-finite values")
    # Wave 1p4u1: CoreML is accepted as the Apple Silicon provider path on CORRECTNESS alone — it is
    # NOT required to beat CPU by a benchmark margin. CoreML transparently partitions unsupported ops
    # back to CPU, so "CoreML selected, CPU still does meaningful work" is the intended local-setup
    # contract, not a failure. A tiny setup probe is also unrepresentative of a full-corpus rebuild
    # (observed: CoreML-selected docs rebuild 420.13s vs prior 422.08s — no material speedup), so a
    # speedup gate on it can spuriously reject (or over-favour) CoreML. Other probed providers
    # (DML/OpenVINO/…) keep the speedup gate below; CUDA bypasses the probe entirely.
    if provider == provider_policy.COREML_PROVIDER:
        return provider_policy.ProviderProbeResult(
            provider,
            True,
            f"{provider} accepted as the Apple Silicon provider path on correctness alone (valid "
            f"embeddings; unsupported ops fall back to CPU; not a speedup gate). NOTE: the times below are "
            f"a tiny correctness micro-benchmark, NOT representative throughput — the accelerated "
            f"FP16/static-shape path runs at index time (probe {candidate_seconds:.3f}s vs CPU {cpu_seconds:.3f}s)",
            candidate_seconds=candidate_seconds,
            cpu_seconds=cpu_seconds,
        )
    min_speedup = float(os.environ.get("WAVEFOUNDRY_EMBED_PROVIDER_MIN_SPEEDUP", "1.25"))
    if candidate_seconds <= 0 or (cpu_seconds / candidate_seconds) < min_speedup:
        return provider_policy.ProviderProbeResult(
            provider,
            False,
            f"candidate did not beat CPU by {min_speedup:.2f}x ({candidate_seconds:.3f}s vs {cpu_seconds:.3f}s)",
            candidate_seconds=candidate_seconds,
            cpu_seconds=cpu_seconds,
        )
    return provider_policy.ProviderProbeResult(
        provider,
        True,
        f"{provider} passed embedding probe ({candidate_seconds:.3f}s vs CPU {cpu_seconds:.3f}s)",
        candidate_seconds=candidate_seconds,
        cpu_seconds=cpu_seconds,
    )


def report_embedding_provider_decision() -> provider_policy.ProviderDecision:
    decision = provider_policy.select_embedding_providers(provider_probe=_probe_embedding_provider)
    os.environ[provider_policy.SETUP_SELECTED_ENV] = decision.selected_provider
    print(provider_policy.format_provider_decision(decision), flush=True)
    if decision.remediation:
        print(f"Embedding provider remediation: {decision.remediation}", flush=True)
    return decision


def _fastembed_cache_dir() -> Path:
    cache_path = Path(os.getenv("FASTEMBED_CACHE_PATH") or str(FASTEMBED_CACHE_DEFAULT))
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


_MODEL_CACHE_DIR_ALIASES: dict[str, tuple[str, ...]] = {
    # FastEmbed stores the current BAAI embedding presets under Qdrant-hosted
    # ONNX repo directories, not the public model IDs used by indexer.py.
    "BAAI/bge-small-en-v1.5": ("qdrant/bge-small-en-v1.5-onnx-q",),
    "BAAI/bge-base-en-v1.5": ("qdrant/bge-base-en-v1.5-onnx-q",),
    # Wave 1p4wx: arctic-embed-xs (docs model). fastembed normalizes the model
    # name to lowercase ``snowflake/…`` and downloads from that HF repo, so the
    # offline cache lives under ``models--snowflake--snowflake-arctic-embed-xs``.
    "Snowflake/snowflake-arctic-embed-xs": ("snowflake/snowflake-arctic-embed-xs",),
}


def _model_cache_dir_candidates(model_name: str) -> tuple[Path, ...]:
    names = [model_name, *_MODEL_CACHE_DIR_ALIASES.get(model_name, ())]
    deduped: list[Path] = []
    seen: set[str] = set()
    for name in names:
        repo_dir = f"models--{name.replace('/', '--')}"
        if repo_dir in seen:
            continue
        seen.add(repo_dir)
        deduped.append(_fastembed_cache_dir() / repo_dir)
    return tuple(deduped)


def _model_cache_dir(model_name: str) -> Path:
    for candidate in _model_cache_dir_candidates(model_name):
        if candidate.exists():
            return candidate
    return _model_cache_dir_candidates(model_name)[0]


def _iter_model_cache_paths(model_dir: Path):
    if not model_dir.exists():
        return
    yield model_dir
    for path in model_dir.rglob("*"):
        yield path


def _model_cache_corruption_reason(model_name: str) -> str | None:
    for model_dir in _model_cache_dir_candidates(model_name):
        if not model_dir.exists():
            continue
        for path in _iter_model_cache_paths(model_dir):
            if path.is_symlink():
                target = path.resolve(strict=False)
                if target.suffix == ".incomplete":
                    return f"cache symlink points at incomplete blob: {path.relative_to(model_dir)}"
                if not path.exists():
                    return f"cache symlink target missing: {path.relative_to(model_dir)}"
                try:
                    if target.is_file() and target.stat().st_size == 0:
                        return f"cache symlink target is zero-byte file: {path.relative_to(model_dir)}"
                except OSError:
                    return f"cache symlink target unreadable: {path.relative_to(model_dir)}"
            elif path.is_file() and path.suffix == ".incomplete":
                try:
                    if path.stat().st_size == 0:
                        return f"incomplete zero-byte blob present: {path.relative_to(model_dir)}"
                except OSError:
                    return f"incomplete blob unreadable: {path.relative_to(model_dir)}"
        snapshots_dir = model_dir / "snapshots"
        if snapshots_dir.is_dir():
            try:
                for snapshot_dir in snapshots_dir.iterdir():
                    onnx_dir = snapshot_dir / "onnx"
                    if not onnx_dir.is_dir():
                        continue
                    onnx_files = list(onnx_dir.rglob("*.onnx"))
                    if not onnx_files:
                        return f"missing onnx model artifact: {snapshot_dir.relative_to(model_dir)}"
                    # Wave 1p6d6: validate the artifact is non-empty even when it is a PLAIN file,
                    # not a symlink. HF materializes the cache as symlinks only with Developer Mode /
                    # admin on Windows; otherwise it COPIES real files, so the symlink-gated zero-byte
                    # checks above never fire — a truncated/zero-byte .onnx would slip through on a
                    # typical native-Windows cache.
                    for onnx_file in onnx_files:
                        try:
                            if onnx_file.is_file() and onnx_file.stat().st_size == 0:
                                return f"zero-byte onnx model artifact: {onnx_file.relative_to(model_dir)}"
                        except OSError:
                            return f"onnx model artifact unreadable: {onnx_file.relative_to(model_dir)}"
            except OSError:
                return "snapshot onnx directory unreadable"
    return None


def _quarantine_model_cache(model_name: str) -> Path | None:
    model_dir = _model_cache_dir(model_name)
    if not model_dir.exists():
        return None
    stamp = int(time.time())
    target = model_dir.with_name(f"{model_dir.name}.broken.{stamp}")
    suffix = 0
    while target.exists():
        suffix += 1
        target = model_dir.with_name(f"{model_dir.name}.broken.{stamp}.{suffix}")
    shutil.move(str(model_dir), str(target))
    return target


def _exception_chain_messages(exc: BaseException) -> str:
    parts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        text = str(current).strip()
        if text:
            parts.append(text)
        current = current.__cause__ or current.__context__
    return " | ".join(parts)


def _looks_like_network_failure(exc: BaseException) -> bool:
    text = _exception_chain_messages(exc).lower()
    markers = (
        "connecterror",
        "nodename nor servname provided",
        "temporary failure in name resolution",
        "name or service not known",
        "failed to resolve",
        "connection refused",
        "connection reset",
        "timed out",
        "timeout",
        "network is unreachable",
        "offline",
    )
    return any(marker in text for marker in markers)


def _model_failure_message(
    *,
    model_name: str,
    model_kind: str,
    action: str,
    exc: BaseException,
    corruption_reason: str | None = None,
    quarantined_to: Path | None = None,
) -> str:
    if _looks_like_network_failure(exc):
        cause = "network or download host unavailable"
    else:
        cause = "model initialization failed"
    details = [f"Required {model_kind} model '{model_name}' could not be prepared for {action}: {cause}."]
    if corruption_reason:
        details.append(f"Detected corrupted cache state: {corruption_reason}.")
    if quarantined_to is not None:
        details.append(f"Quarantined corrupted cache to: {quarantined_to}.")
    details.append(f"Underlying error: {_exception_chain_messages(exc)}")
    details.append(
        "Retry setup when network access is available. If the issue persists, inspect the FastEmbed cache under "
        f"{_fastembed_cache_dir()}."
    )
    return " ".join(details)


def _prewarm_required_model(
    model_name: str,
    *,
    model_kind: str,
    action: str,
    warm_fn,
) -> None:
    quarantined_to: Path | None = None
    repaired = False
    for attempt in range(2):
        try:
            warm_fn(model_name, local_files_only=False)
            with _offline_env():
                warm_fn(model_name, local_files_only=True)
            return
        except ModelPrewarmTimeout:
            # Deadline abort: the abandoned warm thread may still be writing this cache, so the
            # corruption check below would flag the in-flight download and the quarantine would
            # move a directory with live open handles. Propagate to main's handler; process exit
            # reaps the daemon worker.
            raise
        except Exception as exc:
            corruption_reason = _model_cache_corruption_reason(model_name)
            if attempt == 0 and corruption_reason:
                quarantined_to = _quarantine_model_cache(model_name)
                repaired = True
                print(
                    f"Detected corrupted {model_kind} cache for {model_name}: {corruption_reason}",
                    flush=True,
                )
                if quarantined_to is not None:
                    print(f"Quarantined cache to {quarantined_to}; retrying once.", flush=True)
                continue
            raise ModelPrewarmError(
                _model_failure_message(
                    model_name=model_name,
                    model_kind=model_kind,
                    action=action,
                    exc=exc,
                    corruption_reason=corruption_reason if repaired or corruption_reason else None,
                    quarantined_to=quarantined_to,
                )
            ) from exc


def prewarm_models(*, include_code: bool, code_only: bool = False) -> None:
    models = _indexer_models(include_code, code_only=code_only)
    for model_name in models:
        print(f"Prewarming semantic model cache: {model_name}", flush=True)
        _prewarm_required_model(
            model_name,
            model_kind="embedding",
            action="semantic index setup",
            warm_fn=_warm_model,
        )
        print(f"Verified offline semantic model cache: {model_name}", flush=True)

    # Wave 1p52p: the reranker (Xenova export via accel_embedder) is prewarmed in _prewarm_gpu_accel,
    # NOT here — it is no longer a fastembed model to download/verify. It runs on either hardware
    # (GPU FP16 / CPU INT8); search degrades to vector order only when reranking is explicitly disabled.


def _prewarm_gpu_accel(models: list[str]) -> None:
    """Wave 1p517 (extended 1p935): build each model's static-shape ONNX session once at setup —
    downloads + caches the clean ONNX (offline-ready) and pays the ONNX Runtime compile here (GPU
    CoreML sessions cache via ``ModelCacheDirectory``), so the first index build doesn't. On a GPU
    machine this prewarms the FP16 GPU path; on a CPU-bound machine it prewarms the INT8 CPU path
    (wave 1p935) instead of no-op'ing. No-op only without ``onnx``/``accel_embedder``.
    """
    try:
        import accel_embedder
    except ImportError:
        return
    providers = list(provider_policy.select_embedding_providers().providers)

    # Wave 1p52p: prewarm the cross-encoder reranker REGARDLESS of GPU — it runs FP16 on the GPU
    # (~350 ms) or INT8 on the CPU (~960 ms). Pays the download + compile once so the first server
    # query is fast. No-op when reranking is disabled (WAVEFOUNDRY_DISABLE_RERANKER).
    reranker_model = _indexer_reranker_model()
    try:
        reranker = accel_embedder.make_reranker(reranker_model, providers)
        if reranker is not None:
            print(f"Prewarmed reranker ({reranker.provider}, compile cached): {reranker_model}", flush=True)
        else:
            print(f"Reranker not used for {reranker_model} (disabled or unbuildable)", flush=True)
    except Exception as exc:  # noqa: BLE001 - prewarm is best-effort
        print(f"Reranker prewarm skipped for {reranker_model}: {exc}", flush=True)

    # Wave 1p935: make_embedder now handles BOTH precision paths internally — FP16 on a GPU that
    # offloads this model's graph, else INT8 on the CPU EP when an INT8 clean-export source exists
    # — so this loop runs regardless of GPU availability (mirrors the reranker block above), not
    # gated behind a GPU-availability early return. make_embedder falls back to AVAILABLE GPU
    # providers if the selection lacks one, so we don't short-circuit on a (possibly flaky) decision
    # either — let it decide.
    for model_name in models:
        try:
            embedder = accel_embedder.make_embedder(model_name, providers)
        except Exception as exc:  # noqa: BLE001 - prewarm is best-effort
            print(f"Embedder prewarm skipped for {model_name}: {exc}", flush=True)
            continue
        if embedder is not None:
            kind = "CPU-INT8" if embedder.provider == "CPUExecutionProvider" else "GPU"
            cache_note = "compile cached" if kind == "GPU" else "INT8 graph cached"
            print(f"Prewarmed {kind} embedder ({embedder.provider}, {cache_note}): {model_name}", flush=True)
        else:
            print(f"Embedder not accelerated for {model_name} (no GPU offload, no INT8 source) — "
                  "fastembed path", flush=True)


def _spawn_background_semantic_build(root: Path, args: argparse.Namespace, content: str) -> None:
    """Spawn a detached background process to build one semantic index layer."""
    if content not in {"docs", "code"}:
        raise ValueError(f"unsupported background semantic content: {content}")
    # Wave 1p8pe: prefer the console-free tool-venv pythonw.exe on Windows so this detached background
    # build (log-file stdout/stderr) never flashes a console window; falls back to the tool-venv Python
    # (POSIX returns None). The :134 _tool_venv_python resolver stays unchanged (it feeds venv path-math
    # + the console-streaming pip install).
    interp = subprocess_util.windowless_pythonw() or str(_tool_venv_python())
    layer_flag = "--code-only" if content == "code" else "--docs-only"
    cmd = [interp, __file__, "--root", str(root), layer_flag]
    if args.full:
        cmd.append("--full")
    if args.rechunk:
        cmd.append("--rechunk")
    if content == "code" and args.include_tests:
        cmd.append("--include-tests")
    if content == "code" and args.include_generated:
        cmd.append("--include-generated")
    if args.verbose:
        cmd.append("--verbose")
    log_name = "project-background-build.log" if content == "code" else "project-background-docs-build.log"
    log_path = root / ".wavefoundry" / "logs" / log_name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "w", encoding="utf-8")  # noqa: SIM115
    try:
        # Wave 1p8gu: shared isolated Popen — keeps the log-file stdout/stderr while supplying detached
        # stdin + the detached/no-window Windows creationflags (no flashing console on Windows).
        # Wave 1p8gv: force UTF-8 stdio in the spawned child so its non-ASCII prints (e.g. `→`) never
        # raise UnicodeEncodeError on a cp1252 Windows console and silently fail the background build.
        proc = subprocess_util.isolated_popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
            env=subprocess_util.utf8_child_env({**os.environ, TIMESTAMP_LOGS_ENV: "1"}),
        )
    finally:
        log_file.close()
    pid_path = root / ".wavefoundry" / "index" / "background-build.pid"
    pid_path.write_text(str(proc.pid), encoding="utf-8")
    label = "Code" if content == "code" else "Docs"
    print(
        f"{label} index build started in background (PID {proc.pid}).\n"
        f"Progress: {log_path}\n"
        f"Foreground index layer is ready.",
        flush=True,
    )


def _spawn_background_code_build(root: Path, args: argparse.Namespace) -> None:
    """Spawn a detached background process to build the code index."""
    _spawn_background_semantic_build(root, args, "code")


def _spawn_background_docs_build(root: Path, args: argparse.Namespace) -> None:
    """Spawn a detached background process to build the docs index."""
    _spawn_background_semantic_build(root, args, "docs")


def _run_indexer(
    root: Path,
    full: bool,
    content: str,
    verbose: bool,
    include_tests: bool,
    include_generated: bool,
    project_include_prefixes: tuple[str, ...],
    rechunk: bool = False,
) -> None:
    # Wave 1p8pe: prefer the console-free tool-venv pythonw.exe on Windows for this foreground indexer
    # spawn (one-way PIPE — the parent reads its stdout, the child never prints to a console) so it does
    # not flash a window; falls back to the tool-venv Python (POSIX returns None).
    interp = subprocess_util.windowless_pythonw() or str(_tool_venv_python())
    cmd = [interp, str(SCRIPTS_DIR / "indexer.py"), "--root", str(root), "--content", content]
    if full:
        cmd.append("--full")
    if rechunk:  # Wave 1p4n4: re-chunk all + reuse embeddings by hash (no version change)
        cmd.append("--rechunk")
    if include_tests:
        cmd.append("--include-tests")
    if include_generated:
        cmd.append("--include-generated")
    for prefix in project_include_prefixes:
        cmd.extend(["--project-include-prefix", prefix])
    if verbose:
        cmd.append("--verbose")
    # indexer.py always timestamps its own output.  Stream line-by-line and write to the raw
    # underlying stream so the parent's _TimestampedWriter doesn't double-stamp.
    # Wave 1p8gv: force UTF-8 stdio in the child so its `→`/em-dash prints never raise on a cp1252
    # console; AND decode the captured pipe as UTF-8 (errors=replace) so non-ASCII child output is
    # readable on the parent side regardless of OS.
    child_env = subprocess_util.utf8_child_env()
    # Wave 1p8gu: foreground streaming Popen — the parent reads this child's piped stdout line-by-line,
    # so it must NOT detach. Pass the no-window flag (suppress the console flash on Windows) inline and
    # keep the explicit stdin=DEVNULL / PIPE wiring; isolated_popen's detach default is wrong here.
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=child_env,
        creationflags=subprocess_util.no_window_creationflags(),
    )
    collected: list[str] = []
    assert proc.stdout is not None
    raw_out = getattr(sys.stdout, "_wrapped", sys.stdout)

    # Wave 1p9it: no-progress watchdog. A reader thread pushes each stdout line onto a queue; the main
    # loop waits up to `stall_timeout` for the next line. A bare `for line in proc.stdout:` would pin the
    # parent forever on a child that emits nothing and never exits (the ~4h stall-at-step-2.3 field
    # report). The stall window is RESET on every line, so a legit long large-repo build that keeps
    # emitting progress runs as long as it needs and only a genuinely silent/stalled child trips it. On
    # stall: terminate, escalate to kill, drain, and fail loud so the child is reaped (no orphan).
    stall_timeout = _setup_deadlines(root)["index_build_stall_timeout_seconds"]
    line_queue: queue.Queue = queue.Queue()

    def _pump() -> None:
        try:
            for line in proc.stdout:
                line_queue.put(line)
        finally:
            # Sentinel: stream reached EOF (child exited or was killed → pipe closed).
            line_queue.put(None)

    reader = threading.Thread(target=_pump, name="wavefoundry-indexer-reader", daemon=True)
    reader.start()
    while True:
        try:
            item = line_queue.get(timeout=stall_timeout)
        except queue.Empty:
            _terminate_and_reap(proc)
            reader.join(timeout=5)
            raise TimeoutError(
                f"Index build produced no output for {stall_timeout:g}s and was terminated as stalled. "
                "A hung index build is usually a resource problem — check free disk (the LanceDB store "
                "and temp files), CPU load, and available memory/swap (embedding is memory-heavy; a "
                "low-RAM or paused/frozen host can stall it). Free resources and rerun "
                "`wf update-indexes`; raise `setup.index_build_stall_timeout_seconds` in "
                "docs/workflow-config.json if a legitimately slow host needs a longer stall window."
            )
        if item is None:
            break
        collected.append(item)
        raw_out.write(item)
        raw_out.flush()
    reader.join(timeout=5)
    try:
        # Bounded: a reader-thread failure is indistinguishable from EOF via the sentinel, so an
        # unbounded wait here could hang on a live silent child with nobody draining its pipe.
        proc.wait(timeout=stall_timeout)
    except subprocess.TimeoutExpired:
        _terminate_and_reap(proc)
        raise TimeoutError(
            f"Index build reached end-of-output but the child did not exit within {stall_timeout:g}s "
            "and was terminated as stalled. A hung index build is usually a resource problem — check "
            "free disk, CPU load, and available memory/swap, then rerun `wf update-indexes`; raise "
            "`setup.index_build_stall_timeout_seconds` in docs/workflow-config.json if a legitimately "
            "slow host needs a longer window."
        ) from None
    combined_output = "".join(collected)
    if "Another index build is already running" in combined_output or "lock file busy" in combined_output:
        index_dir = root / ".wavefoundry" / "index"
        lock_path = index_dir / "index-build.lock"
        detail = f"The existing build holds {lock_path}; wait for it to finish, then rerun `wf update-indexes` if you still need a refresh."
        try:
            spec = importlib.util.spec_from_file_location(
                "wavefoundry_indexer_for_setup_lock",
                SCRIPTS_DIR / "indexer.py",
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                detail = mod.format_index_build_lock_conflict(index_dir, lock_path=lock_path)
        except Exception:
            pass
        print(f"Index update skipped: {detail}", file=sys.stderr)
        return
    if proc.returncode == 0:
        return

    if proc.returncode < 0:
        signal_number = -proc.returncode
        if signal_number == 9:  # SIGKILL — almost always the OS OOM-killer during embedding
            print(
                "Index build was OOM-KILLED (SIGKILL): the host ran out of memory during embedding. "
                "Remediation — lower the embedding footprint via docs/workflow-config.json "
                "(`indexing.code_embed_batch_size` / `docs_embed_batch_size`, default 32 — try 16/8), "
                "build layers sequentially (`--content docs` then `--content code`), or raise the host / "
                "WSL2 memory cap (`.wslconfig`).",
                file=sys.stderr,
            )
        else:
            print(f"Index build was killed by signal {signal_number}.", file=sys.stderr)
    raise subprocess.CalledProcessError(proc.returncode, cmd, output=combined_output)


def _merge_project_include_prefixes(
    docs_prefixes: tuple[str, ...],
    code_prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    """Stable union of docs and code workflow prefixes for a single ``indexer.py --content all`` pass."""
    merged: list[str] = []
    for group in (docs_prefixes, code_prefixes):
        for raw in group:
            token = raw.strip().replace("\\", "/").strip("/")
            if token and token not in merged:
                merged.append(token)
    return tuple(merged)


def build_index(
    root: Path,
    full: bool,
    include_code: bool,
    verbose: bool,
    include_tests: bool = False,
    include_generated: bool = False,
    project_include_prefixes_for_docs: tuple[str, ...] = (),
    project_include_prefixes_for_code: tuple[str, ...] = (),
    rechunk: bool = False,
    code_only: bool = False,
) -> None:
    if code_only:
        print("Building code semantic index...", flush=True)
        content = "code"
        prefixes = project_include_prefixes_for_code
    elif include_code:
        print("Building docs and code semantic index (single indexer pass)...", flush=True)
        content = "all"
        prefixes = _merge_project_include_prefixes(
            project_include_prefixes_for_docs,
            project_include_prefixes_for_code,
        )
    else:
        print("Building docs/seed semantic index...", flush=True)
        content = "docs"
        prefixes = project_include_prefixes_for_docs
    _run_indexer(
        root,
        full=full,
        content=content,
        verbose=verbose,
        include_tests=include_tests,
        include_generated=include_generated,
        project_include_prefixes=prefixes,
        rechunk=rechunk,
    )
    # Wave 1p601: the codebase map is decoupled from the index build (it lives in
    # the indexed docs/references/ tree, so regenerating on every build would
    # create a write→reindex loop). No map regen here. The map is refreshed at
    # lifecycle (prepare/close), on upgrade, on-demand (wave_index_build
    # content="map" / CLI), and lazily on resource read.


def _coerce_prefix_list(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        token = item.strip().replace("\\", "/").strip("/")
        if token and token not in out:
            out.append(token)
    return tuple(out)


def _workflow_project_include_prefixes(root: Path) -> dict[str, tuple[str, ...]]:
    cfg = root / "docs" / "workflow-config.json"
    if not cfg.exists():
        return {DOCS_PREFIXES_KEY: (), CODE_PREFIXES_KEY: ()}
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {DOCS_PREFIXES_KEY: (), CODE_PREFIXES_KEY: ()}
    if not isinstance(data, dict):
        return {DOCS_PREFIXES_KEY: (), CODE_PREFIXES_KEY: ()}
    indexing = data.get(INDEXING_WORKFLOW_KEY, {})
    if not isinstance(indexing, dict):
        return {DOCS_PREFIXES_KEY: (), CODE_PREFIXES_KEY: ()}

    configured = indexing.get(PROJECT_INCLUDE_PREFIXES_KEY, {})
    docs_prefixes: tuple[str, ...] = ()
    code_prefixes: tuple[str, ...] = ()
    if isinstance(configured, list):
        prefixes = _coerce_prefix_list(configured)
        docs_prefixes = prefixes
        code_prefixes = prefixes
    elif isinstance(configured, dict):
        docs_prefixes = _coerce_prefix_list(configured.get(DOCS_PREFIXES_KEY))
        code_prefixes = _coerce_prefix_list(configured.get(CODE_PREFIXES_KEY))

    # Backwards compatibility: old boolean opt-in maps to framework scripts code prefix.
    if not code_prefixes and bool(indexing.get(INCLUDE_FRAMEWORK_CODE_KEY, False)):
        code_prefixes = (".wavefoundry/framework/scripts",)
    return {DOCS_PREFIXES_KEY: docs_prefixes, CODE_PREFIXES_KEY: code_prefixes}


# ---------------------------------------------------------------------------
# Wave 1p9it: Phase-1 setup child deadlines
# ---------------------------------------------------------------------------
#
# Every `wf setup` Phase-1 child (venv create, uv bootstrap, dependency install, in-process model warm,
# index-build subprocess) is bounded by a per-step deadline / no-progress watchdog so a single stalled
# child fails loud with stage-specific guidance instead of hanging setup indefinitely (the native-
# Windows field defect: a reboot-needed post-Phase-1 hang and a ~4h stall). Defaults are conservative,
# sized for slow-but-legit environments (corp proxy, low-RAM WSL2); every value is overridable via
# docs/workflow-config.json `setup.<key>`. INDEX_BUILD_STALL is a NO-PROGRESS window (reset on each
# output line), NOT a total cap — a legit long large-repo build that keeps emitting progress never
# trips, only a genuinely silent/stalled child does. stdlib threading/subprocess/queue only; no new dep.
SETUP_WORKFLOW_KEY = "setup"
VENV_CREATE_TIMEOUT_DEFAULT = 300.0          # local `python -m venv`
UV_BOOTSTRAP_TIMEOUT_DEFAULT = 600.0         # `pip install uv` (network)
DEP_INSTALL_TIMEOUT_DEFAULT = 1800.0         # full dependency resolve + download (network, large wheels)
MODEL_WARM_TIMEOUT_DEFAULT = 1800.0          # in-process model download + load (network)
INDEX_BUILD_STALL_TIMEOUT_DEFAULT = 1800.0   # no-progress window for the index-build child stdout stream

_SETUP_DEADLINE_KEYS: dict[str, float] = {
    "venv_create_timeout_seconds": VENV_CREATE_TIMEOUT_DEFAULT,
    "uv_bootstrap_timeout_seconds": UV_BOOTSTRAP_TIMEOUT_DEFAULT,
    "dep_install_timeout_seconds": DEP_INSTALL_TIMEOUT_DEFAULT,
    "model_warm_timeout_seconds": MODEL_WARM_TIMEOUT_DEFAULT,
    "index_build_stall_timeout_seconds": INDEX_BUILD_STALL_TIMEOUT_DEFAULT,
}

# Set once per run by ``main`` from ``_setup_deadlines(root)`` before prewarm, then read by
# ``_warm_model`` when its ``deadline_seconds`` arg is left default. A module-level channel (rather than
# threading root through ``prewarm_models`` -> ``_prewarm_required_model`` -> ``warm_fn``) keeps the
# generic ``_prewarm_required_model`` warm_fn contract — ``(model_name, local_files_only)`` — unchanged.
_ACTIVE_MODEL_WARM_DEADLINE_SECONDS: float | None = None


def _setup_deadlines(root: Path | None) -> dict[str, float]:
    """Resolve Phase-1 setup child deadlines (seconds) from ``docs/workflow-config.json`` ``setup.<key>``
    (wave 1p9it). Analogous to ``_workflow_project_include_prefixes``. Fail-safe: a missing file,
    malformed JSON, missing block/key, or a non-positive/non-numeric value falls back to the shipped
    default for that key and never raises. ``root=None`` (e.g. a direct unit-test call) yields all
    defaults."""
    resolved = dict(_SETUP_DEADLINE_KEYS)
    if root is None:
        return resolved
    try:
        data = json.loads((root / "docs" / "workflow-config.json").read_text(encoding="utf-8"))
        block = data.get(SETUP_WORKFLOW_KEY) if isinstance(data, dict) else None
        if isinstance(block, dict):
            for key in _SETUP_DEADLINE_KEYS:
                val = block.get(key)
                if isinstance(val, (int, float)) and not isinstance(val, bool) and val > 0:
                    resolved[key] = float(val)
    except Exception:
        pass
    return resolved


def _run_in_process_with_deadline(fn, *, deadline_seconds: float, timeout_error: BaseException) -> None:
    """Run in-process ``fn()`` under a wall-clock deadline (wave 1p9it). Executes ``fn`` on a daemon
    worker thread joined with ``deadline_seconds``; if the thread is still alive at the deadline, raise
    ``timeout_error``. The daemon worker is then abandoned — a blocked native call (e.g. a hung fastembed
    TLS fetch) cannot be interrupted from outside, so the abort path fails loud and the process should be
    exited rather than resumed. On the within-deadline path this is behaviorally identical to calling
    ``fn()`` directly: any exception ``fn`` raised is re-raised here, preserving existing error semantics
    exactly."""
    box: dict[str, BaseException] = {}

    def _worker() -> None:
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 — surfaced on the joining thread
            box["exc"] = exc

    worker = threading.Thread(target=_worker, name="wavefoundry-model-warm", daemon=True)
    worker.start()
    worker.join(deadline_seconds)
    if worker.is_alive():
        raise timeout_error
    if "exc" in box:
        raise box["exc"]


def _terminate_and_reap(proc) -> None:
    """Terminate a stalled child, escalate to kill, and reap it so no orphan/zombie survives (wave
    1p9it). Best-effort at each step: ``terminate()``; if it does not exit within a short grace window,
    ``kill()``; then ``wait()`` to reap. A child that is already gone raises harmlessly and is ignored."""
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
        return
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
    except Exception:
        pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Set up the Wavefoundry semantic index")
    p.add_argument("--root", default=None, help="Repository root (default: current directory)")
    p.add_argument("--full", action="store_true", help="Force full rebuild")
    p.add_argument("--rechunk", action="store_true", help="Re-chunk every file but reuse embeddings by content hash (no version change; only new/changed chunks re-embed)")
    p.add_argument("--include-code", action="store_true", help="Build semantic code embeddings synchronously (default; kept for explicit CI/full-build callers)")
    p.add_argument("--background-code", action="store_true", help="Build docs index synchronously (unblocks MCP immediately), then spawn a detached background process for code embedding")
    p.add_argument("--background-docs", action="store_true", help="Build code index synchronously, then spawn a detached background process for docs embedding")
    p.add_argument("--docs-only", action="store_true", help="Build only docs/seed semantic embeddings in the foreground")
    p.add_argument("--code-only", action="store_true", help="Build only semantic code embeddings in the foreground")
    p.add_argument("--graph-only", action="store_true", help="Rebuild only the graph index without re-embedding semantic vectors")
    p.add_argument("--include-tests", action="store_true", help="Include target test files in semantic code indexing")
    p.add_argument("--include-generated", action="store_true", help="Include generated platform hook files in semantic code indexing")
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if os.environ.get(TIMESTAMP_LOGS_ENV) == "1":
        _enable_timestamped_stdio()
    args = parse_args(argv)
    root = Path(args.root).expanduser().resolve() if args.root else Path.cwd().resolve()

    print(f"Wavefoundry index setup: root={root}", flush=True)
    for ds in root.rglob(".DS_Store"):
        try:
            ds.unlink()
        except OSError:
            pass
    ensure_deps(root)
    _reexec_with_venv_if_needed()
    # Wave 1p9it: establish the in-process model-warm deadline for THIS run from workflow-config (the
    # default applies when unset). Read once here; `_warm_model` reads it when its `deadline_seconds`
    # arg is left default. This keeps the `prewarm_models`/`_prewarm_required_model` warm_fn contract
    # unchanged (see `_ACTIVE_MODEL_WARM_DEADLINE_SECONDS`).
    global _ACTIVE_MODEL_WARM_DEADLINE_SECONDS
    _ACTIVE_MODEL_WARM_DEADLINE_SECONDS = _setup_deadlines(root)["model_warm_timeout_seconds"]
    include_prefixes = _workflow_project_include_prefixes(root)
    docs_prefixes = include_prefixes.get(DOCS_PREFIXES_KEY, ())
    code_prefixes = include_prefixes.get(CODE_PREFIXES_KEY, ())
    if docs_prefixes or code_prefixes:
        print(
            "Workflow policy: project include-prefixes enabled "
            f"(docs={list(docs_prefixes)}, code={list(code_prefixes)})",
            flush=True,
        )
    if args.graph_only:
        graph_prefixes = tuple(dict.fromkeys((*docs_prefixes, *code_prefixes)))
        try:
            _run_indexer(
                root,
                full=args.full,
                content="graph",
                verbose=args.verbose,
                include_tests=False,
                include_generated=False,
                project_include_prefixes=graph_prefixes,
            )
        except TimeoutError as exc:
            # Stall watchdog abort: exit clean with the stage-named message, matching the
            # venv/deps/model-warm deadline convention (no raw traceback, exit code 2).
            print(str(exc), file=sys.stderr)
            return 2
        print("\nDone. Graph index rebuild complete.", flush=True)
        return 0

    if args.docs_only and args.code_only:
        print("ERROR: --docs-only and --code-only are mutually exclusive.", file=sys.stderr)
        return 2
    if args.background_docs and args.background_code:
        print("ERROR: --background-docs and --background-code cannot be combined; run separate commands for two detached layers.", file=sys.stderr)
        return 2
    if (args.docs_only or args.code_only) and (args.background_docs or args.background_code):
        print("ERROR: --docs-only/--code-only cannot be combined with background layer flags.", file=sys.stderr)
        return 2

    background_code = args.background_code and not args.include_code
    background_docs = args.background_docs
    if background_code:
        # H1 (Phase 4b reliability): stamp THIS process's pid into the background-build marker BEFORE
        # the synchronous docs build, so a crash here (prewarm / docs build) leaves a dead-pid record —
        # `wave_index_build_status` then reports `completed` (attempted-and-exited) instead of `none`
        # (never run), which is what masked the silent failure the JS/TS team hit. On success,
        # `_spawn_background_code_build` overwrites this with the detached code-build pid.
        try:
            _bg_pid = root / ".wavefoundry" / "index" / "background-build.pid"
            _bg_pid.parent.mkdir(parents=True, exist_ok=True)
            _bg_pid.write_text(str(os.getpid()), encoding="utf-8")
        except OSError:
            pass
    _code_only = args.code_only or background_docs
    _include_code = not background_code and not args.docs_only
    try:
        # Download/verify the models BEFORE the provider probe — the probe loads with
        # local_files_only and would transiently fail on a fresh/cleared cache (model absent),
        # silently dropping the whole build to CPU. Order: download → probe → GPU accel prewarm.
        prewarm_models(include_code=_include_code, code_only=_code_only)
    except ModelPrewarmError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    report_embedding_provider_decision()
    _prewarm_gpu_accel(_indexer_models(include_code=_include_code, code_only=_code_only))
    try:
        build_index(
            root,
            full=args.full,
            rechunk=args.rechunk,
            include_code=_include_code,
            verbose=args.verbose,
            include_tests=args.include_tests,
            include_generated=args.include_generated,
            project_include_prefixes_for_docs=docs_prefixes,
            project_include_prefixes_for_code=code_prefixes,
            code_only=_code_only,
        )
    except TimeoutError as exc:
        # Stall watchdog abort: exit clean with the stage-named message, matching the
        # venv/deps/model-warm deadline convention (no raw traceback, exit code 2).
        print(str(exc), file=sys.stderr)
        return 2
    # Wave 1p9aj: reclaim any accumulated table bloat now that the synchronous build has released the
    # build lock and before the background code build (if any) is spawned — so it never races a build.
    _optimize_after_build(root)
    if background_code:
        _spawn_background_code_build(root, args)
    if background_docs:
        _spawn_background_docs_build(root, args)
    print(
        f"\nDone. Project index update complete.\n"
        f"MCP handoff: restart your AI agent so the Wavefoundry MCP server attaches "
        f"(the committed config launches `python .wavefoundry/framework/scripts/server.py`).",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
