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


def _missing_in_venv(venv_python: Path) -> list[str]:
    """Return distribution names for packages not importable from the venv Python."""
    mod_to_dist = {mod: dist for dist, mod in REQUIRED_IMPORTS.items()}
    script = (
        "import importlib.util\n"
        f"mods = {list(mod_to_dist)!r}\n"
        "print('\\n'.join(m for m in mods if importlib.util.find_spec(m) is None))"
    )
    result = subprocess.run([str(venv_python), "-c", script], capture_output=True, text=True)
    if result.returncode != 0:
        return list(REQUIRED_IMPORTS.keys())
    missing_mods = [m.strip() for m in result.stdout.strip().splitlines() if m.strip()]
    return [mod_to_dist[m] for m in missing_mods if m in mod_to_dist]


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
    missing = _missing_in_venv(venv_python)
    if not missing:
        print(f"Dependencies satisfied ({', '.join(REQUIRED_IMPORTS)})", flush=True)
        return
    _install_deps(missing, venv_python)
    still_missing = _missing_in_venv(venv_python)
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


def _warm_model(model_name: str, *, local_files_only: bool) -> None:
    from fastembed import TextEmbedding

    embedding = TextEmbedding(model_name=model_name, local_files_only=local_files_only)
    next(iter(embedding.embed(["wavefoundry cache verification"])))


def _warm_reranker(model_name: str, *, local_files_only: bool) -> None:
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    try:
        reranker = TextCrossEncoder(model_name=model_name, local_files_only=local_files_only)
    except TypeError:
        reranker = TextCrossEncoder(model_name=model_name)
    list(reranker.rerank("verification query", ["verification document"]))


def _fastembed_cache_dir() -> Path:
    cache_path = Path(os.getenv("FASTEMBED_CACHE_PATH") or str(FASTEMBED_CACHE_DEFAULT))
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


_MODEL_CACHE_DIR_ALIASES: dict[str, tuple[str, ...]] = {
    # FastEmbed stores the current BAAI embedding presets under Qdrant-hosted
    # ONNX repo directories, not the public model IDs used by indexer.py.
    "BAAI/bge-small-en-v1.5": ("qdrant/bge-small-en-v1.5-onnx-q",),
    "BAAI/bge-base-en-v1.5": ("qdrant/bge-base-en-v1.5-onnx-q",),
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
                    if not any(onnx_dir.rglob("*.onnx")):
                        return f"missing onnx model artifact: {snapshot_dir.relative_to(model_dir)}"
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

    reranker_model = _indexer_reranker_model()
    print(f"Prewarming reranker model cache: {reranker_model}", flush=True)
    _prewarm_required_model(
        reranker_model,
        model_kind="reranker",
        action="semantic index setup",
        warm_fn=_warm_reranker,
    )
    print(f"Verified offline reranker model cache: {reranker_model}", flush=True)


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
) -> None:
    cmd = [str(_tool_venv_python()), str(SCRIPTS_DIR / "indexer.py"), "--root", str(root), "--content", content]
    if full:
        cmd.append("--full")
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
        lock_path = root / ".wavefoundry" / "index" / "index-build.lock"
        print(
            f"Index update skipped: another project index build is already running for {root / '.wavefoundry' / 'index'}.\n"
            f"The existing build holds {lock_path}; wait for it to finish, then rerun update-indexes if you still need a refresh.",
            file=sys.stderr,
        )
        return
    if proc.returncode == 0:
        return

    if proc.returncode < 0:
        signal_number = -proc.returncode
        print(
            f"Index build was killed by signal {signal_number}. "
            "If this happened during code embedding, rerun without --include-code.",
            file=sys.stderr,
        )
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
    )


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
    try:
        prewarm_models(include_code=not background_code and args.include_code)
    except ModelPrewarmError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    build_index(
        root,
        full=args.full,
        include_code=not background_code and args.include_code,
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
