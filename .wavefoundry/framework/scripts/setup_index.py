#!/usr/bin/env python3
"""Check index dependencies and build the Wavefoundry semantic index."""
from __future__ import annotations

import argparse
import contextlib
import datetime
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True

FASTEMBED_CACHE_DEFAULT = Path.home() / ".wavefoundry" / "cache" / "fastembed"
if not os.environ.get("FASTEMBED_CACHE_PATH"):
    os.environ["FASTEMBED_CACHE_PATH"] = str(FASTEMBED_CACHE_DEFAULT)

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import provider_policy

TIMESTAMP_LOGS_ENV = "WAVEFOUNDRY_TIMESTAMP_LOGS"
REQUIRED_IMPORTS = {
    "fastembed": "fastembed",
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
    "lancedb": "lancedb",
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


def _tool_venv_python() -> Path:
    base = Path(os.environ.get("WAVEFOUNDRY_TOOL_VENV", "~/.wavefoundry/venv"))
    venv = base.expanduser()
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _bootstrap_venv() -> Path:
    """Ensure the tool venv exists; return the path to its Python binary."""
    venv_python = _tool_venv_python()
    venv_dir = venv_python.parent.parent

    if venv_dir.exists() and not venv_python.exists():
        # Partial venv: directory present but Python binary absent — delete and recreate.
        print(f"Incomplete venv detected at {venv_dir}; recreating ...", flush=True)
        shutil.rmtree(venv_dir, ignore_errors=True)

    if not venv_dir.exists():
        print(f"Creating tool venv at {venv_dir} ...", flush=True)
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])

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
    """Return distribution names for packages not importable from the venv Python."""
    required_imports = required_imports or _planned_required_imports()
    mod_to_dist = {mod: dist for dist, mod in required_imports.items()}
    gpu_dists = [dist for dist in CUDA_DEPENDENCY_IMPORTS if dist in required_imports]
    script = (
        "import importlib.util\n"
        "import importlib.metadata as metadata\n"
        f"mods = {list(mod_to_dist)!r}\n"
        f"gpu_dists = {gpu_dists!r}\n"
        "missing = [m for m in mods if importlib.util.find_spec(m) is None]\n"
        "for dist in gpu_dists:\n"
        "    try:\n"
        "        metadata.version(dist)\n"
        "    except metadata.PackageNotFoundError:\n"
        "        missing.append('__dist__:' + dist)\n"
        "print('\\n'.join(missing))"
    )
    result = subprocess.run([str(venv_python), "-c", script], capture_output=True, text=True)
    if result.returncode != 0:
        return list(required_imports.keys())
    missing_mods = [m.strip() for m in result.stdout.strip().splitlines() if m.strip()]
    missing: list[str] = []
    for item in missing_mods:
        if item.startswith("__dist__:"):
            dist = item.split(":", 1)[1]
        else:
            dist = mod_to_dist.get(item)
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


def _bootstrap_uv(venv_python: Path) -> Path | None:
    """Install uv into the tool venv via pip and return its path, or None on failure."""
    print("uv not found — installing uv for package age enforcement ...", flush=True)
    result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "uv"],
        check=False,
    )
    if result.returncode != 0:
        return None
    return _uv_bin(venv_python)


def _install_deps(missing: list[str], venv_python: Path) -> None:
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

    uv = _uv_bin(venv_python) or _bootstrap_uv(venv_python)

    if uv is not None:
        cutoff = _exclude_newer_cutoff(days=21)
        print(f"Using uv with --exclude-newer {cutoff} (21-day package age guard)", flush=True)
        cmd = [
            str(uv), "pip", "install",
            "--python", str(venv_python),
            "--exclude-newer", cutoff,
        ] + missing
    else:
        print(
            "WARNING: uv not available and could not be installed. "
            "Falling back to pip without package age enforcement. "
            "Install uv (https://docs.astral.sh/uv/) for supply-chain age checks.",
            file=sys.stderr,
        )
        cmd = [str(venv_python), "-m", "pip", "install"] + missing

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        installer = "uv" if uv is not None else "pip"
        print(
            f"{installer} install failed (exit {result.returncode}). "
            "Check the output above and install manually, then rerun setup_index.py.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    print("Dependencies installed successfully.", flush=True)


def ensure_deps() -> None:
    venv_python = _bootstrap_venv()
    required_imports = _planned_required_imports()
    missing = _missing_in_venv(venv_python, required_imports)
    if not missing:
        print(f"Dependencies satisfied ({', '.join(required_imports)})", flush=True)
        return
    _install_deps(missing, venv_python)
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
    """Re-exec this script under the venv Python if we are not already running from it.

    On a fresh install the caller is the system Python, which does not have the
    framework packages. Once ``ensure_deps()`` has populated the venv, this
    function replaces the current process (via ``os.execv``) with the venv Python
    running the same script and arguments, so that ``prewarm_models()`` and the
    index build can import framework packages directly.

    No-ops when already running from the venv or when the venv does not exist.
    """
    venv_python = _tool_venv_python()
    if not venv_python.exists():
        return
    # Use sys.prefix rather than sys.executable to detect venv membership.
    # On macOS/Homebrew, venv Python is a symlink to the same underlying
    # binary as the system Python, so executable path comparison gives false
    # positives. sys.prefix is set to the venv directory when inside a venv
    # and to the interpreter's installation prefix otherwise.
    try:
        if Path(sys.prefix).resolve() == venv_python.parent.parent.resolve():
            return  # Already running inside the venv — nothing to do.
    except Exception:
        pass
    if os.name == "nt":
        # os.execv on Windows spawns a child and exits the parent with code 0,
        # so the child's exit code is lost. Use subprocess to preserve it.
        result = subprocess.run([str(venv_python)] + sys.argv, check=False)
        sys.exit(result.returncode)
    else:
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)


def _indexer_models(include_code: bool) -> list[str]:
    indexer_path = SCRIPTS_DIR / "indexer.py"
    spec = importlib.util.spec_from_file_location("wavefoundry_indexer_for_setup", indexer_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
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
_OS_CA_BUNDLE_CANDIDATES = (
    "/etc/ssl/certs/ca-certificates.crt",   # Debian/Ubuntu/WSL2
    "/etc/pki/tls/certs/ca-bundle.crt",     # RHEL/CentOS/Fedora
    "/etc/ssl/ca-bundle.pem",               # OpenSUSE
    "/etc/ssl/cert.pem",                    # Alpine / macOS LibreSSL
)


def _os_trust_store_bundle() -> "str | None":
    """An OS CA bundle for the TLS fallback. Honors a preset SSL_CERT_FILE/REQUESTS_CA_BUNDLE first
    (operator override), then known platform locations; ``None`` if none exist. Verification stays ON —
    this only selects WHICH trusted CA bundle to verify against, never disables verification."""
    for env in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        val = os.environ.get(env)
        if val and os.path.isfile(val):
            return val
    for path in _OS_CA_BUNDLE_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


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


def _warm_model(model_name: str, *, local_files_only: bool) -> None:
    from fastembed import TextEmbedding

    def _build() -> None:
        embedding = TextEmbedding(
            model_name=model_name,
            local_files_only=local_files_only,
            providers=_embedding_providers_for_setup(),
        )
        next(iter(embedding.embed(["wavefoundry cache verification"])))

    try:
        _build()
        return
    except Exception as exc:  # noqa: BLE001
        # Only intervene on a genuine cert-verify failure during an ONLINE fetch — never a cache miss
        # (local_files_only) or any other error.
        if local_files_only or not _is_cert_verify_error(exc):
            raise
        bundle = _os_trust_store_bundle()
        already_tried = (
            os.environ.get("SSL_CERT_FILE") == bundle
            and os.environ.get("REQUESTS_CA_BUNDLE") == bundle
        )
        if not bundle or already_tried:
            raise ModelPrewarmError(
                f"Model '{model_name}' download failed TLS verification (CERTIFICATE_VERIFY_FAILED) and the "
                "OS trust store did not resolve it. Behind a TLS-inspecting proxy, point the CA bundle at your "
                "OS store and retry: export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt "
                "REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt"
            ) from exc
        print(
            f"Model download for '{model_name}' failed certifi TLS verification; retrying against the OS "
            f"trust store ({bundle}). TLS verification stays ON.",
            flush=True,
        )
        os.environ["SSL_CERT_FILE"] = bundle
        os.environ["REQUESTS_CA_BUNDLE"] = bundle
        # huggingface_hub (which fastembed's snapshot_download uses) caches a GLOBAL httpx.Client whose
        # SSL context is built ONCE against certifi — so setting the env after the first attempt is a
        # no-op against the already-built client. Reset it so the retry rebuilds the client against the
        # OS bundle we just set. (close_session is documented for exactly "an SSL certificate updated".)
        try:
            import huggingface_hub
            huggingface_hub.close_session()
        except Exception:  # noqa: BLE001
            pass
        _build()  # verification still on, now trusting the OS bundle


def _probe_embedding_provider(provider: str, *, model_name: str | None = None) -> provider_policy.ProviderProbeResult:
    """Bounded correctness/performance probe for providers that need model proof."""
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
    try:
        # Run one unmeasured warm pass for each provider, then time the second pass.
        # FastEmbed and ONNX Runtime both do lazy setup that would otherwise dominate
        # a tiny benchmark and make CoreML look better than a full-corpus rebuild.
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
    except Exception as exc:
        return provider_policy.ProviderProbeResult(provider, False, f"{type(exc).__name__}: {exc}")

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


def prewarm_models(*, include_code: bool) -> None:
    models = _indexer_models(include_code)
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
    """Wave 1p517: on a GPU machine, build each model's static-shape CoreML session once at setup —
    downloads + caches any clean ONNX (offline-ready) and pays the CoreML compile here (cached via
    ``ModelCacheDirectory``), so the first index build doesn't. No-op on CPU machines / without onnx.
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

    # The EMBEDDER accel is GPU-only (CPU embedders stay on fastembed). make_embedder falls back to
    # AVAILABLE GPU providers if the selection lacks one, so don't short-circuit on the (possibly
    # flaky) decision — let it decide. No-op without a GPU.
    if not (any(p in accel_embedder.GPU_PROVIDERS for p in providers) or accel_embedder._available_gpu_providers()):
        return
    for model_name in models:
        try:
            embedder = accel_embedder.make_embedder(model_name, providers)
        except Exception as exc:  # noqa: BLE001 - prewarm is best-effort
            print(f"GPU embedder prewarm skipped for {model_name}: {exc}", flush=True)
            continue
        if embedder is not None:
            print(f"Prewarmed GPU embedder ({embedder.provider}, CoreML compile cached): {model_name}", flush=True)
        else:
            print(f"GPU embedder not used for {model_name} (graph not GPU-friendly) — fastembed path", flush=True)


def _spawn_background_code_build(root: Path, args: argparse.Namespace) -> None:
    """Spawn a detached background process to build the code index."""
    cmd = [str(_tool_venv_python()), __file__, "--root", str(root), "--include-code"]
    if args.full:
        cmd.append("--full")
    if args.include_tests:
        cmd.append("--include-tests")
    if args.include_generated:
        cmd.append("--include-generated")
    if args.verbose:
        cmd.append("--verbose")
    log_path = root / ".wavefoundry" / "logs" / "project-background-build.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "w", encoding="utf-8")  # noqa: SIM115
    try:
        kwargs: dict = {
            "stdout": log_file,
            "stderr": log_file,
            "stdin": subprocess.DEVNULL,
            "env": {**os.environ, TIMESTAMP_LOGS_ENV: "1"},
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(cmd, **kwargs)
    finally:
        log_file.close()
    pid_path = root / ".wavefoundry" / "index" / "background-build.pid"
    pid_path.write_text(str(proc.pid), encoding="utf-8")
    print(
        f"Code index build started in background (PID {proc.pid}).\n"
        f"Progress: {log_path}\n"
        f"MCP is available now — docs index is ready.",
        flush=True,
    )


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
    cmd = [str(_tool_venv_python()), str(SCRIPTS_DIR / "indexer.py"), "--root", str(root), "--content", content]
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
    # indexer.py always timestamps its own output.  Pass the env through unchanged
    # so no env manipulation is needed.  Stream line-by-line and write to the raw
    # underlying stream so the parent's _TimestampedWriter doesn't double-stamp.
    child_env = {**os.environ}
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=child_env,
    )
    collected: list[str] = []
    assert proc.stdout is not None
    raw_out = getattr(sys.stdout, "_wrapped", sys.stdout)
    for line in proc.stdout:
        collected.append(line)
        raw_out.write(line)
        raw_out.flush()
    proc.wait()
    combined_output = "".join(collected)
    if "Another index build is already running" in combined_output or "lock file busy" in combined_output:
        index_dir = root / ".wavefoundry" / "index"
        lock_path = index_dir / "index-build.lock"
        detail = f"The existing build holds {lock_path}; wait for it to finish, then rerun update-indexes if you still need a refresh."
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
) -> None:
    if include_code:
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Set up the Wavefoundry semantic index")
    p.add_argument("--root", default=None, help="Repository root (default: current directory)")
    p.add_argument("--full", action="store_true", help="Force full rebuild")
    p.add_argument("--rechunk", action="store_true", help="Re-chunk every file but reuse embeddings by content hash (no version change; only new/changed chunks re-embed)")
    p.add_argument("--include-code", action="store_true", help="Also build semantic code embeddings (slower and more memory-intensive)")
    p.add_argument("--background-code", action="store_true", help="Build docs index synchronously (unblocks MCP immediately), then spawn a detached background process for code embedding")
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
    ensure_deps()
    _reexec_with_venv_if_needed()
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
        _run_indexer(
            root,
            full=args.full,
            content="graph",
            verbose=args.verbose,
            include_tests=False,
            include_generated=False,
            project_include_prefixes=graph_prefixes,
        )
        print("\nDone. Graph index rebuild complete.", flush=True)
        return 0

    background_code = args.background_code and not args.include_code
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
    _include_code = not background_code and args.include_code
    try:
        # Download/verify the models BEFORE the provider probe — the probe loads with
        # local_files_only and would transiently fail on a fresh/cleared cache (model absent),
        # silently dropping the whole build to CPU. Order: download → probe → GPU accel prewarm.
        prewarm_models(include_code=_include_code)
    except ModelPrewarmError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    report_embedding_provider_decision()
    _prewarm_gpu_accel(_indexer_models(include_code=_include_code))
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
    )
    if background_code:
        _spawn_background_code_build(root, args)
    print(
        f"\nDone. Project index update complete.\n"
        f"MCP handoff: .wavefoundry/bin/mcp-server",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
