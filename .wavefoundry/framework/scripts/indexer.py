#!/usr/bin/env python3
"""Build and maintain the Wavefoundry semantic index at .wavefoundry/index/."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

sys.dont_write_bytecode = True
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)
import subprocess_util  # shared subprocess isolation (wave 1p8gu)
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)

# Activate the shared tool venv IN-PROCESS before any heavy import (wave 1p7pl/1p802). No-op when
# already in the venv or when it does not exist yet (fresh bootstrap).
venv_bootstrap.activate_tool_venv()
# Wave 1p8gv: indexer is spawned as a child by setup_index — reconfigure its OWN stdout/stderr to
# UTF-8 so its `→`/em-dash progress prints never raise UnicodeEncodeError on a cp1252 Windows console
# (which silently failed the index build). Belt-and-suspenders with the PYTHONUTF8 child env.
cli_stdio.configure_utf8_stdio()

FASTEMBED_CACHE_DEFAULT = Path.home() / ".wavefoundry" / "cache" / "fastembed"
if not os.environ.get("FASTEMBED_CACHE_PATH"):
    os.environ["FASTEMBED_CACHE_PATH"] = str(FASTEMBED_CACHE_DEFAULT)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

INDEX_DIR_NAME = ".wavefoundry/index"
META_JSON = "meta.json"
INDEX_BUILD_LOCK_NAME = "index-build.lock"
# Wave 1p99o: the OS lock is taken on this single sentinel byte (both POSIX and Windows), kept far off
# the byte-0 metadata region so the JSON `{pid, started_at, ended_at, cmdline}` is always readable/
# writable regardless of lock state (status reads owner/ended_at; finalize writes ended_at while still
# holding the lock). Byte-range locks beyond EOF are legal and do not extend the file.
INDEX_BUILD_LOCK_SENTINEL = 1 << 20
TABLE_LOCK_NAME = ".lock"   # written inside docs.lance/ and code.lance/
LOCK_STALE_SECONDS = 60 * 60
TIMESTAMP_LOGS_ENV = "WAVEFOUNDRY_TIMESTAMP_LOGS"

# Wave 1p4wx: docs/code embedding-model split. Docs use the asymmetric
# arctic-embed-xs (best on the 45-query docs bake-off: 82% vs bge-small 67%);
# code stays on the symmetric bge-small (unbeaten on the 62-query code set).
# Both are 384-d, so there is no vector-dimension ripple. The model name stored
# in ``model_versions["docs"]`` IS the version — changing it auto-forces a
# docs-only re-embed (see ``build_index``); the code layer reuses its vectors.
DOCS_MODEL = "Snowflake/snowflake-arctic-embed-xs"
CODE_MODEL = "BAAI/bge-small-en-v1.5"

# Instruction prefixes required by asymmetric embedding models.
# Values include a trailing space/separator so that ``prefix + text`` produces
# correctly formatted input. Empty strings mean no prefix (symmetric models such
# as bge-small/base). The pipeline embeds via fastembed ``.embed()`` (which does
# NOT auto-apply prefixes), so the QUERY prefix is applied explicitly at query
# time (``server_impl._embed_query`` via ``query_embedding_prefix``) and the
# DOCUMENT prefix at index time. arctic-embed is asymmetric: queries carry the
# "Represent this sentence…" instruction; documents carry none.
EMBEDDING_PREFIXES: dict[str, dict[str, str]] = {
    "nomic-ai/nomic-embed-text-v1.5-Q": {
        "document": "search_document: ",
        "query": "search_query: ",
    },
    "Snowflake/snowflake-arctic-embed-xs": {
        "document": "",
        "query": "Represent this sentence for searching relevant passages: ",
    },
    "BAAI/bge-base-en-v1.5": {
        "document": "",
        "query": "",
    },
    "BAAI/bge-small-en-v1.5": {
        "document": "",
        "query": "",
    },
    "jinaai/jina-embeddings-v2-base-code": {
        "document": "",
        "query": "",
    },
    "jinaai/jina-embeddings-v2-small-en": {
        "document": "",
        "query": "",
    },
}


def query_embedding_prefix(model_name: str) -> str:
    """Instruction prefix to prepend to a QUERY before embedding with ``model_name``.

    Empty for symmetric models. Asymmetric models (e.g. arctic-embed) require it
    at query time — the pipeline embeds via fastembed ``.embed()``, which does not
    apply prefixes automatically.
    """
    return EMBEDDING_PREFIXES.get(model_name, {}).get("query", "")


def document_embedding_prefix(model_name: str) -> str:
    """Instruction prefix to prepend to a DOCUMENT/passage before embedding.

    Empty for every model currently in use (arctic-embed documents take no
    prefix). The build path embeds passages without a prefix; this invariant is
    enforced by ``_assert_active_models_have_empty_document_prefix`` so a future
    asymmetric-document model can't silently regress the index.
    """
    return EMBEDDING_PREFIXES.get(model_name, {}).get("document", "")


def _assert_active_models_have_empty_document_prefix() -> None:
    """Guard: the index build embeds passages without a prefix, which is only
    correct while every active model's document prefix is empty."""
    for model_name in (DOCS_MODEL, CODE_MODEL):
        if document_embedding_prefix(model_name):
            raise AssertionError(
                f"Active model {model_name!r} declares a non-empty document prefix, "
                "but the index build does not apply document prefixes. Wire the "
                "document prefix into the embed path before using this model."
            )


_assert_active_models_have_empty_document_prefix()

# LanceDB vector index constants
# Tables are stored directly inside the index directory (e.g. .wavefoundry/index/docs.lance/).
LANCEDB_INDEX_THRESHOLD = 1000   # rows; below: flat scan; at/above: IVF_HNSW_SQ index
LANCEDB_COMPACT_THRESHOLD = 20   # fragment count threshold; triggers optimize() after add/delete
EMBED_BATCH_SIZE = 256           # chunks per embedding batch
SORT_WINDOW_SIZE = 2048          # sliding sort buffer size (8× EMBED_BATCH_SIZE)
LANCEDB_NPROBES = 20             # ANN search probes (recall vs latency)
LANCEDB_REFINE_FACTOR = 10       # reranking candidates multiplier
# Wave 1p52p: cross-encoder reranker. ms-marco-MiniLM-L-6-v2 (6-layer, 22M) via its Xenova FP16 export
# (resolved in accel_embedder.CLEAN_ONNX_SOURCES). Chosen over bge-reranker-base after a head-to-head:
# better known-answer recall (mean rank 1.07 vs 1.67), ~4-5x faster, ~8x less memory, and the only one
# whose CoreML compile cache speeds up restarts. Runs on either hardware: GPU FP16, or CPU INT8 (no
# ranking loss); reranking is skipped only when explicitly disabled (WAVEFOUNDRY_DISABLE_RERANKER).
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CONTENT_CHOICES = ("docs", "code", "all", "graph")

try:
    import provider_policy
except ImportError:  # pragma: no cover - defensive when loaded from an unusual path
    provider_policy = None

try:
    import accel_embedder  # Wave 1p517: GPU static-shape ONNX embedder
except ImportError:  # pragma: no cover - defensive
    accel_embedder = None


class _TimestampedStream:
    """Line-buffering stream wrapper that prefixes complete log lines."""

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


class IndexBuildAlreadyRunning(RuntimeError):
    """Raised when another process already holds the whole-index build lock."""


# Wave 1p9am: raised 2.0 -> 45.0. On Claude the post-edit hook no longer spawns a reindex per edit — it
# marks a `reindex-pending` sentinel and the turn-end Stop hook flushes it once per turn. This debounce
# now only governs the leading-edge flush on non-Stop hosts (Cursor/Copilot/…), which have no turn-end
# signal, so a longer window is the churn cut there.
HOOK_REINDEX_DEBOUNCE_SECONDS = 45.0
HOOK_REINDEX_LAST_SPAWN_NAME = "hook-reindex.last-spawn"
# Wave 1p9am: the turn-end coalescing sentinel. Written by the post-edit hook on an index-worthy edit;
# consumed (atomically cleared) by the Claude Stop hook, or by the staleness monitor's quiet-period
# safety net if a turn ends without the Stop hook flushing it.
HOOK_REINDEX_PENDING_NAME = "reindex-pending"

# Wave 1p9bg: generous default timeout (seconds) for the post-edit docs-lint hook subprocess — well
# above the 30s that was too short in the field, and configurable via docs/workflow-config.json.
DOCS_LINT_HOOK_TIMEOUT_DEFAULT = 120.0


def docs_lint_hook_timeout_seconds(root: Path) -> float:
    """Timeout (seconds) for the post-edit docs-lint hook subprocess. Wave 1p9bg. Reads
    ``docs/workflow-config.json`` ``docs_lint.hook_timeout_seconds``; defaults to
    ``DOCS_LINT_HOOK_TIMEOUT_DEFAULT`` (120s). Fail-safe: any error / missing / non-positive value falls
    back to the default and never raises. Keeps the docs-lint hook from either failing early on a large
    repo or hanging the post-edit hook unbounded."""
    try:
        cfg = json.loads((root / "docs" / "workflow-config.json").read_text(encoding="utf-8"))
        val = (cfg.get("docs_lint") or {}).get("hook_timeout_seconds")
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    except Exception:
        pass
    return DOCS_LINT_HOOK_TIMEOUT_DEFAULT


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            result = subprocess_util.isolated_run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in result.stdout
        except OSError:
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    # Wave 1p98u: os.kill(pid, 0) keeps succeeding for a zombie/defunct process until its parent
    # reaps it, which made a finished-but-unreaped index build read as "live" and block every
    # later build. A defunct process has already exited (its OS flock is released), so treat it as
    # not running — mirrors the background-build/dashboard zombie guards (waves 1p654/1p6d6).
    if _process_is_zombie(pid):
        return False
    return True


# Wave 1p98u: index-build-lock liveness hardening. A recorded owner PID can be a zombie/defunct
# process (os.kill still succeeds) or a recycled PID now running an unrelated program — both made the
# lock read as a live build and skipped/blocked index updates. These helpers reconcile against the
# real process state + cmdline, mirroring the dashboard 1p654 reconciliation. Every probe routes
# through subprocess_util.isolated_run (windowless on Windows — no console flash) and degrades to a
# safe default on any failure (never reclaim a possibly-live build; the OS flock stays the authority).
_INDEX_BUILDER_MARKERS = ("indexer.py", "setup_index.py")


def _process_is_zombie(pid: int) -> bool:
    """POSIX: True iff ``pid`` is in ``Z``/defunct state. Windows / any failure: False.

    Windows has no zombie concept, so this is a no-op there and never spawns a console."""
    if os.name == "nt" or pid <= 0:
        return False
    try:
        result = subprocess_util.isolated_run(
            ["ps", "-o", "state=", "-p", str(int(pid))],
            capture_output=True, text=True, check=False,
        )
    except Exception:  # noqa: BLE001 — best-effort; any failure → not-zombie (safe: no reclaim)
        return False
    if result.returncode != 0:
        return False
    return (result.stdout or "").strip()[:1] == "Z"


def _process_cmdline(pid: int) -> Optional[str]:
    """Best-effort full command line for ``pid`` — cross-OS and windowless. None if unavailable.

    POSIX: ``ps -o args=``. Windows: ``powershell.exe`` + CIM (the only built-in exposing the full
    CommandLine), invoked EXPLICITLY through the windowless ``isolated_run`` — no ``shell=True`` and
    no reliance on the parent shell, so it behaves identically whether the operator runs cmd or
    PowerShell, and no console window flashes. Any failure (incl. PowerShell absent) → None so the
    caller keeps today's behavior."""
    if pid <= 0:
        return None
    try:
        if os.name == "nt":
            ps_script = (
                f"Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}' "
                "| ForEach-Object { $_.CommandLine }"
            )
            result = subprocess_util.isolated_run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True, text=True, check=False, timeout=10,
            )
        else:
            result = subprocess_util.isolated_run(
                ["ps", "-o", "args=", "-p", str(int(pid))],
                capture_output=True, text=True, check=False,
            )
    except Exception:  # noqa: BLE001 — best-effort; any failure → None (caller falls back)
        return None
    if result.returncode != 0:
        return None
    out = (result.stdout or "").strip()
    return out or None


def _pid_is_index_builder(pid: int) -> bool:
    """True when ``pid``'s live cmdline is an index build (indexer.py / setup_index.py).

    Returns True when the cmdline cannot be read (scan unavailable) — an unverifiable owner must NOT
    be reclaimed out from under a possibly-live build, so we keep today's behavior and let the OS
    flock remain the authority (avoids a double-build)."""
    cmdline = _process_cmdline(pid)
    if cmdline is None:
        return True
    return any(marker in cmdline for marker in _INDEX_BUILDER_MARKERS)


def read_index_build_lock_metadata(lock_path: Path) -> Optional[dict]:
    if not lock_path.exists():
        return None
    try:
        loaded = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def classify_index_build_lock_owner(metadata: Optional[dict]) -> str:
    """Return ``live``, ``stale``, ``completed``, or ``unknown`` for index-build.lock metadata.

    ``completed`` means the recorded owner pid is no longer running but ``started_at`` is
    recent — a normal finished build, not an abandoned lock marker.
    """
    if not metadata:
        return "unknown"
    pid = metadata.get("pid")
    started_at = metadata.get("started_at")
    if isinstance(pid, int) and _pid_is_running(pid):
        # Wave 1p98u: os.kill/tasklist liveness alone accepts a recycled PID now running an unrelated
        # program. Only an actual index-builder process is a live build; a recycled PID (its cmdline
        # is not an indexer) falls through to the age-based stale/completed branch so the lock can be
        # reclaimed. When the cmdline scan is unavailable, _pid_is_index_builder returns True, so an
        # unverifiable owner stays "live" (never reclaimed out from under a possibly-live build).
        if _pid_is_index_builder(pid):
            return "live"
    if isinstance(started_at, (int, float)):
        age = time.time() - float(started_at)
        if age >= LOCK_STALE_SECONDS:
            return "stale"
        if isinstance(pid, int):
            return "completed"
    if isinstance(pid, int):
        return "stale"
    return "unknown"


def format_index_build_lock_conflict(index_dir: Path, *, lock_path: Optional[Path] = None) -> str:
    lock_path = lock_path or (index_dir / INDEX_BUILD_LOCK_NAME)
    metadata = read_index_build_lock_metadata(lock_path)
    owner = classify_index_build_lock_owner(metadata)
    pid = metadata.get("pid") if metadata else None
    base = (
        f"Another index build is already running for {index_dir}; "
        f"lock file busy: {lock_path}"
    )
    if owner == "live":
        detail = f"live build in progress (owner pid {pid})"
    elif owner == "stale":
        detail = (
            f"recorded owner pid {pid} appears stale — the OS lock is held by another "
            f"process (possible inherited lock descriptor); wait for the holder to exit or "
            f"remove {lock_path} after confirming no build is active"
        )
    elif owner == "completed":
        detail = (
            f"recorded owner pid {pid} finished recently — the OS lock is held by another "
            f"process; wait for the active build to finish"
        )
    else:
        detail = "lock holder could not be classified from metadata"
    return f"{base} — {detail}"


def should_coalesce_hook_reindex(index_dir: Path) -> bool:
    """Return True when a hook-triggered reindex spawn should be skipped."""
    lock_path = index_dir / INDEX_BUILD_LOCK_NAME
    if classify_index_build_lock_owner(read_index_build_lock_metadata(lock_path)) == "live":
        return True
    debounce_path = index_dir / HOOK_REINDEX_LAST_SPAWN_NAME
    if not debounce_path.exists():
        return False
    try:
        last_spawn = float(debounce_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    return (time.time() - last_spawn) < HOOK_REINDEX_DEBOUNCE_SECONDS


def record_hook_reindex_spawn(index_dir: Path) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / HOOK_REINDEX_LAST_SPAWN_NAME).write_text(
        str(time.time()),
        encoding="utf-8",
    )


def mark_reindex_pending(index_dir: Path) -> None:
    """Wave 1p9am: record that an index-worthy edit happened this turn. The turn-end Stop hook (or the
    staleness monitor's quiet-period safety net) consumes this marker and runs ONE coalesced incremental
    reindex — instead of spawning a reindex per edit. Cheap (a single write); never raises."""
    try:
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / HOOK_REINDEX_PENDING_NAME).write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def reindex_pending_age(index_dir: Path) -> "Optional[float]":
    """Seconds since the reindex-pending marker was last refreshed, or None if no marker is pending.
    Lets the staleness monitor tell a FRESH marker (the turn-end hook owns the next reindex — defer)
    from a STALE one (a turn ended without the Stop hook flushing — the monitor takes over)."""
    try:
        mtime = (index_dir / HOOK_REINDEX_PENDING_NAME).stat().st_mtime
    except OSError:
        return None
    return max(0.0, time.time() - mtime)


def consume_reindex_pending(index_dir: Path) -> bool:
    """Atomically check-and-clear the reindex-pending marker. Returns True iff a marker was pending (and
    was cleared by this call). ``unlink`` is the atomic primitive — if the Stop hook and the monitor race,
    only one unlink succeeds, so only one reindex is spawned. Never raises."""
    try:
        (index_dir / HOOK_REINDEX_PENDING_NAME).unlink()
        return True
    except OSError:
        return False


SOURCE_CODE_EXTENSIONS = {
    ".py",
    ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs", ".mts", ".cts",
    ".go", ".rs", ".java", ".kt", ".swift", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".rb", ".php", ".sh", ".bash", ".zsh", ".fish",
    ".yaml", ".yml", ".toml", ".json", ".jsonc",
    ".html", ".css", ".scss", ".sass",
    ".xml", ".graphql", ".gql", ".proto", ".sql",
    ".psql", ".pgsql", ".ddl", ".dml", ".tsql", ".hql",
    ".ps1", ".psm1",
    ".bat", ".cmd",
    ".tf", ".tfvars", ".hcl",
    ".tpl",
}

# Extensionless filenames treated as documentation (routed to chunk_plain_text in chunker).
# Keep in sync with chunker.py:DOCS_EXTENSIONLESS_NAMES.
DOCS_EXTENSIONLESS_NAMES = {"README", "LICENSE", "CHANGELOG", "CONTRIBUTING", "NOTICE"}

# Extensionless filenames treated as code (routed to chunk_line_window in chunker).
# Keep in sync with chunker.py:CODE_EXTENSIONLESS_NAMES.
CODE_EXTENSIONLESS_NAMES = {
    "Jenkinsfile", "Makefile", "Dockerfile", "Vagrantfile", "Brewfile",
    "Fastfile", "Appfile", "Podfile", "Gemfile", "Procfile",
}

# Plain-text extensions indexed as documentation (not code).
DOCS_TEXT_EXTENSIONS = {".txt"}
GENERATED_CODE_PREFIXES = (
    ".claude/hooks/",
    ".cursor/hooks/",
    ".github/hooks/",
    ".windsurf/",
)
FRAMEWORK_TEST_PREFIXES = (
    ".wavefoundry/framework/scripts/tests/",
)
FRAMEWORK_PACK_ARTIFACT_NAMES = {"MANIFEST", "VERSION"}
FRAMEWORK_PACK_ARTIFACT_PREFIXES = ("MANIFEST.pre-",)
# Transient/runtime artifact extensions excluded from the framework layer's
# walk so they never appear in framework meta.json (and never get shipped via
# build_pack — which applies an equivalent filter in build_pack.py).
FRAMEWORK_TRANSIENT_ARTIFACT_EXTENSIONS = (".lock", ".log", ".bak", ".swp", ".tmp", ".orig", ".rej")
# Dev-only framework paths not shipped in the distribution zip.
# These are excluded from framework/index/ so wave_index_build and build_pack
# always produce the same file set — eliminating the dev/pack index conflict.
# These files remain indexed in .wavefoundry/index/ (project layer).
FRAMEWORK_DEV_ONLY_PREFIXES = (
    ".wavefoundry/framework/scripts/benchmarks/",
)
FRAMEWORK_DEV_ONLY_EXACT_PATHS = frozenset({
    ".wavefoundry/framework/scripts/run_tests.py",
    ".wavefoundry/framework/test-cache.json",
})
TEST_DIR_NAMES = {"test", "tests", "__tests__"}

# Directories and patterns always excluded regardless of .gitignore/.aiignore
# Single directory names excluded wherever they appear in the path tree.
HARDCODED_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".tox", ".venv", "venv", ".env", "env",
    "dist", "build", "target", "out", ".next", ".nuxt",
}

# Path prefixes (relative to repo root, forward slashes) that are always excluded.
HARDCODED_EXCLUDE_PREFIXES = (
    ".wavefoundry/index/",
    ".wavefoundry/framework/index/",
    ".wavefoundry/logs/",
)
HARDCODED_EXCLUDE_PATHS = frozenset({
    ".wavefoundry/dashboard-server.lock",  # 1p64x: merged lock + startup-metadata sidecar
    ".wavefoundry/guard-overrides.json",
})
# Wave 1p2q3 (1p2qd): consumer project indexes exclude `.wavefoundry/` blanket.
# Framework infrastructure (framework/, bin/, dist/, logs/, CHANGELOG.md, etc.)
# is not consumer product code and shouldn't appear in the consumer's project
# graph or semantic index by default. The wavefoundry repository's own
# self-hosting case is preserved via `project_include_prefixes.code` in
# `docs/workflow-config.json`, which lists the framework subpaths that THIS
# repo's project layer needs (e.g. `.wavefoundry/framework/scripts`,
# `.wavefoundry/framework/dashboard`). Matching files bypass this blanket via
# the existing escape-hatch path in `_filter_project_index_excludes`.
PROJECT_INDEX_EXCLUDE_PREFIXES = (
    ".wavefoundry/",
)

# 1p4ww: the separate shipped framework index is eliminated. Only the framework
# SEEDS + README are folded into the PROJECT docs index by default — they describe
# the framework's methodology/overview and are useful in any consumer project. The
# rest of `.wavefoundry/framework/` (scripts, operational docs, dashboard,
# install/release) is framework-internal; the self-hosting repo already covers its
# own scripts via workflow-config and its docs via the project `docs/` tree. Both
# folded prefixes are docs-kind, so no framework code is added and no dedup is needed.
FRAMEWORK_FOLD_DOCS_PREFIXES = (
    ".wavefoundry/framework/seeds",
    ".wavefoundry/framework/README.md",
)

# Canonical home (moved from dashboard_server.py). Paths that should never mark
# the project index stale even though they live under ``.wavefoundry/`` and may
# be churned by the running tooling itself.
_PROJECT_STALE_IGNORE_PATHS = {
    ".wavefoundry/dashboard-server.lock",  # 1p64x: merged lock + startup-metadata sidecar
    ".wavefoundry/guard-overrides.json",
    ".wavefoundry/logs/dashboard.log",
    # Wave 1p601: the generated codebase map is a regenerated artifact written at
    # lifecycle/on-demand/on-read moments. It must NOT drive index staleness, or
    # writing it (at prepare/close/upgrade/resource-read) would trigger a reindex —
    # the write→reindex coupling the decoupling is meant to eliminate.
    "docs/references/codebase-map.md",
}

BINARY_EXTENSIONS = frozenset({
    # Compiled / native
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".bin", ".a", ".o", ".elf",
    # Archives
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar",
    # Office / presentation
    ".pdf", ".pptx", ".docx", ".xlsx", ".xls", ".ppt", ".doc",
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".webp", ".tiff", ".tif",
    # Vector / design — SVG excluded from code index (no code semantics)
    ".svg", ".eps", ".ai", ".sketch", ".acorn",
    # Fonts
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    # Media
    ".mp3", ".mp4", ".wav", ".ogg", ".avi", ".mov", ".mkv", ".flv",
    # Data / ML artifacts
    ".npy", ".npz", ".pkl", ".parquet", ".h5", ".hdf5",
    # Databases / locks
    ".db", ".sqlite", ".lock",
    # Installers / packages
    ".dmg", ".pkg", ".msi", ".deb", ".rpm",
})

# Exact filenames excluded regardless of extension (generated/machine-written files).
HARDCODED_EXCLUDE_FILENAMES = frozenset({
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "prompt-surface-manifest.json",  # machine-generated metadata artifact, not useful for search
})

# Extensions for machine-generated files that are valid text but have no code semantics.
_GENERATED_EXCLUDE_EXTENSIONS = frozenset({
    ".snap",        # Vitest / Jest snapshot files
    ".excalidraw",  # Excalidraw diagram JSON
})

# All extensions we treat as known text — no null-byte sniff needed.
_KNOWN_TEXT_EXTENSIONS = frozenset(SOURCE_CODE_EXTENSIONS) | {
    ".md", ".markdown",
    ".txt",
    ".graphql", ".gql", ".proto",
    ".psql", ".pgsql", ".ddl", ".dml", ".tsql", ".hql",
    ".tf", ".tfvars", ".hcl", ".tpl",
    ".ps1", ".psm1",
    ".bat", ".cmd",
}

# Dot-directories that are always excluded from the walk.
# The blanket rule (name starts with ".") handles new tools automatically;
# only paths under .wavefoundry/ are permitted through the dot-dir filter.
_DOT_DIR_ALLOWLIST = ".wavefoundry"
_DOT_DIR_ALLOWLIST_PREFIX = ".wavefoundry/"

# Bump when walk_repo() filter logic changes (binary exclusions, generated file exclusions,
# null-byte/magic-byte sniff changes) OR when the project-index include set changes. A version
# mismatch forces a full rebuild so existing indexes pick up newly-included / drop newly-excluded
# files automatically.
# 5 -> 6 (1p4ww): framework seeds + README are now folded into the project docs index by default;
# existing indexes must re-walk to pull them in. The deprecated shipped framework/index/ is NOT
# removed by manifest-prune (its `.lance` artifacts were never in any MANIFEST, so prune can't see
# them) — it is removed by an explicit step in upgrade_wavefoundry.py's prune phase (wave 1p5ik).
WALKER_VERSION = "6"

# Environment variable used by the MCP server to tell the background indexer
# which state file to remove once the process exits.
INDEX_BUILD_STATE_PATH_ENV = "WAVEFOUNDRY_INDEX_BUILD_STATE_PATH"

# ---------------------------------------------------------------------------
# Ignore file parsing
# ---------------------------------------------------------------------------

def _load_ignore_patterns(root: Path) -> list[str]:
    patterns: list[str] = []
    for name in (".gitignore", ".aiignore"):
        p = root / name
        if p.is_file():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    return patterns


def _matches_ignore(rel_path: str, patterns: list[str]) -> bool:
    """Simple gitignore-style pattern matching (covers common cases)."""
    import fnmatch
    parts = rel_path.replace("\\", "/").split("/")
    for pattern in patterns:
        pattern = pattern.rstrip("/")
        # Directory-only pattern (ends with /) already stripped above
        if fnmatch.fnmatch(parts[-1], pattern):
            return True
        if fnmatch.fnmatch(rel_path.replace("\\", "/"), pattern):
            return True
        # Match any path component
        for part in parts[:-1]:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


# ---------------------------------------------------------------------------
# File walker
# ---------------------------------------------------------------------------

# Wave 1p5c4: indexing size guards. The hard cap drops a file from the index entirely (no read,
# no parse); the tree-sitter cap (pushed to the chunker/graph extractor via env) skips only the AST
# parse for large-but-under-hard-cap code files. Both overridable via docs/workflow-config.json.
MAX_INDEX_FILE_BYTES_DEFAULT = 5_000_000
MAX_TREESITTER_PARSE_BYTES_DEFAULT = 2_000_000


def _resolve_index_size_limits(root: Path) -> tuple[int, int]:
    """Return (max_file_bytes, max_treesitter_parse_bytes), reading optional overrides from
    `indexing.max_file_bytes` / `indexing.max_treesitter_parse_bytes` in docs/workflow-config.json.
    Falls back to the module defaults; a non-int / negative override is ignored. 0 means "no cap"."""
    max_file = MAX_INDEX_FILE_BYTES_DEFAULT
    max_ts = MAX_TREESITTER_PARSE_BYTES_DEFAULT
    cfg = root / "docs" / "workflow-config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            indexing = data.get("indexing", {}) if isinstance(data, dict) else {}
            if isinstance(indexing, dict):
                mf = indexing.get("max_file_bytes")
                mt = indexing.get("max_treesitter_parse_bytes")
                if isinstance(mf, int) and mf >= 0:
                    max_file = mf
                if isinstance(mt, int) and mt >= 0:
                    max_ts = mt
        except (OSError, json.JSONDecodeError):
            pass
    return max_file, max_ts


def _resolve_max_file_bytes(root: Path) -> int:
    return _resolve_index_size_limits(root)[0]


def walk_repo(root: Path, *, respect_ignore: bool = True) -> list[Path]:
    """Return all indexable files under root, respecting ignore rules.

    Wave 1p5c4: files larger than the hard size cap (`indexing.max_file_bytes`, default 5 MB) are
    skipped entirely — a multi-GB blob (e.g. a SQL backup) would otherwise be read and
    tree-sitter-parsed, spinning the indexer."""
    ignore_patterns = _load_ignore_patterns(root) if respect_ignore else []
    max_file_bytes = _resolve_max_file_bytes(root)
    result: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dir_path = Path(dirpath)
        try:
            rel_dir = dir_path.relative_to(root)
        except ValueError:
            continue

        dirnames.sort()
        filenames.sort()

        rel_dir_str = str(rel_dir).replace("\\", "/")
        keep_dirnames: list[str] = []
        for dirname in dirnames:
            if dirname in HARDCODED_EXCLUDE_DIRS:
                continue
            child_rel = dirname if rel_dir_str == "." else f"{rel_dir_str}/{dirname}"
            if not (
                child_rel == _DOT_DIR_ALLOWLIST
                or child_rel.startswith(_DOT_DIR_ALLOWLIST_PREFIX)
            ) and dirname.startswith("."):
                continue
            # Wave 1p5c4: prune gitignored DIRECTORIES during the walk so we never descend into
            # generated/binary trees — most importantly `.wavefoundry/index/` (LanceDB shards),
            # `.wavefoundry/logs/`, and `.wavefoundry/framework/index/`. Previously these were walked
            # and dropped per-file, which stat'd hundreds of large index shards and spammed the
            # oversized-file skip log. (Per-file ignore matching still runs as a backstop below.)
            if ignore_patterns and _matches_ignore(child_rel, ignore_patterns):
                continue
            keep_dirnames.append(dirname)
        dirnames[:] = keep_dirnames

        for filename in filenames:
            path = dir_path / filename
            if not path.is_file():
                continue

            try:
                rel = path.relative_to(root)
            except ValueError:
                continue

            rel_str = str(rel).replace("\\", "/")

            if rel_str in HARDCODED_EXCLUDE_PATHS:
                continue

            # Check hardcoded prefix excludes
            if any(rel_str.startswith(prefix) for prefix in HARDCODED_EXCLUDE_PREFIXES):
                continue

            parts = rel_str.split("/")

            # Blanket dot-dir exclusion: skip any path component that starts with "."
            # unless the entire prefix starts with the .wavefoundry allowlist.
            if not rel_str.startswith(_DOT_DIR_ALLOWLIST_PREFIX):
                if any(part.startswith(".") for part in parts[:-1]):
                    continue

            # Check remaining hardcoded dir-name excludes (non-dot dirs like node_modules).
            # Only check directory components (parts[:-1]) so filenames like ".env" aren't
            # blocked by the ".env" virtualenv dir entry.
            if any(part in HARDCODED_EXCLUDE_DIRS for part in parts[:-1]):
                continue

            filename = parts[-1]
            suffix = path.suffix.lower()

            # .env files: allow through — chunker redacts all values, indexes variable names only.
            # Must be checked before the gitignore check and binary sniff since .env has no
            # recognised extension and is typically listed in .gitignore.
            if filename == ".env" or (filename.startswith(".env.") and len(filename) > 5):
                result.append(path)
                continue

            # Exact-filename exclusions (generated lock files)
            if filename in HARDCODED_EXCLUDE_FILENAMES:
                continue

            # Binary extensions
            if suffix in BINARY_EXTENSIONS:
                continue

            # Generated-file extension exclusions (snapshots, diagrams)
            if suffix in _GENERATED_EXCLUDE_EXTENSIONS:
                continue

            # Allow extensionless docs files (README, LICENSE, etc.) before extension check
            if not path.suffix and filename in DOCS_EXTENSIONLESS_NAMES:
                result.append(path)
                continue

            # Allow extensionless code files (Jenkinsfile, Makefile, etc.) before extension check
            if not path.suffix and filename in CODE_EXTENSIONLESS_NAMES:
                result.append(path)
                continue

            # Binary sniff for extensionless files and files with unrecognized extensions.
            # Checks magic-byte signatures first (ELF, Mach-O, PE, class files), then falls
            # back to a null-byte scan which catches most binary formats not covered above.
            if not suffix or suffix not in _KNOWN_TEXT_EXTENSIONS:
                try:
                    header = path.read_bytes()[:8192]
                    if (
                        header[:4] == b"\x7fELF"           # ELF (Linux/ARM executables)
                        or header[:4] in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf",
                                          b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe")  # Mach-O
                        or header[:2] == b"MZ"             # PE/COFF (.exe, .dll)
                        or header[:4] == b"\xca\xfe\xba\xbe"  # Java .class / fat Mach-O
                        or b"\x00" in header
                    ):
                        continue
                except OSError:
                    continue

            # .gitignore / .aiignore
            if _matches_ignore(rel_str, ignore_patterns):
                continue

            # Wave 1p5c4: hard size guard — skip pathologically large files (e.g. a multi-GB SQL
            # backup) so they are never read or tree-sitter-parsed. Checked AFTER the ignore filters
            # so generated/ignored blobs (e.g. index shards) don't trigger the skip log. Logged once.
            if max_file_bytes > 0:
                try:
                    if path.stat().st_size > max_file_bytes:
                        # Wave 1p9io: stderr, not stdout — walk_repo runs in-process from the MCP
                        # server (navigation tools + index-health) where stdout is the JSON-RPC
                        # channel. This skip notice is unconditional, so stdout would corrupt the frame.
                        print(
                            f"build_index: skipping oversized file "
                            f"({path.stat().st_size // 1_000_000} MB > {max_file_bytes // 1_000_000} MB cap): {rel_str}",
                            file=sys.stderr,
                            flush=True,
                        )
                        continue
                except OSError:
                    continue

            result.append(path)

    return sorted(result)


# ---------------------------------------------------------------------------
# Hashing and stat-cache change detection
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _build_file_hashes(files: list[Path], root: Path) -> dict[str, str]:
    """Return {relative_path: sha256_hex} for every file in *files*."""
    return {str(f.relative_to(root)).replace("\\", "/"): _sha256(f) for f in files}


def _stat_entry(path: Path) -> tuple[float, int, int]:
    """Return (mtime, size, inode) for a file.

    inode is 0 on Windows/FAT where st_ino is unsupported; callers treat 0 as
    "don't use inode in cache comparison".
    """
    st = path.stat()
    return (st.st_mtime, st.st_size, st.st_ino)


def _stat_matches(old: dict, mtime: float, size: int, inode: int) -> bool:
    """True if stored stat entry matches current stat — no read needed."""
    if old.get("mtime") != mtime or old.get("size") != size:
        return False
    # If inodes are available on this filesystem, also check inode
    old_ino = old.get("inode", 0)
    if inode and old_ino and inode != old_ino:
        return False
    return True


def _detect_changes(
    files: list[Path],
    root: Path,
    old_meta: dict[str, dict],
) -> tuple[dict[str, dict], set[str], set[str]]:
    """Return (current_file_meta, changed_paths, removed_paths).

    Uses mtime+size+inode as a cheap pre-filter: only files whose stat differs
    from stored values are read and hashed. Files that pass the stat check are
    treated as unchanged without any file I/O.

    old_meta maps rel_path -> {"hash": str, "mtime": float, "size": int, "inode": int}.
    """
    current: dict[str, dict] = {}
    changed: set[str] = set()

    for f in files:
        rel = str(f.relative_to(root)).replace("\\", "/")
        mtime, size, inode = _stat_entry(f)
        old = old_meta.get(rel)

        # Cache hit: stat matches — skip read entirely
        if old is not None and isinstance(old, dict) and _stat_matches(old, mtime, size, inode):
            current[rel] = old
            continue

        # Cache miss: read and hash
        digest = _sha256(f)
        entry: dict = {"hash": digest, "mtime": mtime, "size": size, "inode": inode}
        current[rel] = entry

        # Changed if hash differs from stored (or no prior entry)
        old_hash = old.get("hash") if old is not None else None
        if old_hash != digest:
            changed.add(rel)

    removed = set(old_meta.keys()) - set(current.keys())
    return current, changed, removed



def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _filter_by_prefixes(files: list[Path], root: Path, prefixes: tuple[str, ...]) -> list[Path]:
    if not prefixes:
        return files
    normalized = tuple(prefix.strip("/").replace("\\", "/") for prefix in prefixes)
    return [
        path for path in files
        if any(
            str(path.relative_to(root)).replace("\\", "/").startswith(prefix + "/")
            or str(path.relative_to(root)).replace("\\", "/") == prefix
            for prefix in normalized
        )
    ]


def _filter_project_index_excludes(
    files: list[Path],
    root: Path,
    include_prefixes: tuple[str, ...],
    *,
    project_include_prefixes: tuple[str, ...] = (),
) -> list[Path]:
    """Exclude framework source from the default project-local index layer."""
    if include_prefixes:
        return files
    normalized_includes = tuple(
        prefix.strip("/").replace("\\", "/")
        for prefix in project_include_prefixes
        if prefix.strip()
    )

    def _allowed_by_project_include_prefixes(rel_path: str) -> bool:
        return any(rel_path == prefix or rel_path.startswith(prefix + "/") for prefix in normalized_includes)

    return [
        path for path in files
        if _allowed_by_project_include_prefixes(str(path.relative_to(root)).replace("\\", "/"))
        or not any(
            str(path.relative_to(root)).replace("\\", "/").startswith(prefix)
            for prefix in PROJECT_INDEX_EXCLUDE_PREFIXES
        )
    ]


def _filter_framework_pack_artifacts(files: list[Path], root: Path) -> list[Path]:
    """Exclude packaging artifacts and dev-only files from the framework layer index.

    Keeps framework/index/ in sync with the distribution zip file set so that
    wave_index_build and build_pack never fight over different file sets.
    Dev-only files remain indexed in .wavefoundry/index/ (project layer).
    """
    filtered: list[Path] = []
    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        name = path.name
        if name in FRAMEWORK_PACK_ARTIFACT_NAMES:
            continue
        if any(name.startswith(prefix) for prefix in FRAMEWORK_PACK_ARTIFACT_PREFIXES):
            continue
        if name.endswith(FRAMEWORK_TRANSIENT_ARTIFACT_EXTENSIONS):
            continue
        if _is_framework_test_path(rel):
            continue
        if rel.startswith(FRAMEWORK_DEV_ONLY_PREFIXES):
            continue
        if rel in FRAMEWORK_DEV_ONLY_EXACT_PATHS:
            continue
        filtered.append(path)
    return filtered


def _normalize_prefixes(prefixes: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw in prefixes:
        token = raw.strip().replace("\\", "/").strip("/")
        if token and token not in normalized:
            normalized.append(token)
    return tuple(normalized)


def _workflow_project_include_prefixes(root: Path) -> dict[str, tuple[str, ...]]:
    """Read docs/code project include-prefix lists from workflow-config.json."""
    cfg = root / "docs" / "workflow-config.json"
    if not cfg.exists():
        return {"docs": (), "code": ()}
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"docs": (), "code": ()}
    if not isinstance(data, dict):
        return {"docs": (), "code": ()}
    indexing = data.get("indexing", {})
    if not isinstance(indexing, dict):
        return {"docs": (), "code": ()}
    configured = indexing.get("project_include_prefixes", {})
    docs_prefixes: tuple[str, ...] = ()
    code_prefixes: tuple[str, ...] = ()
    if isinstance(configured, list):
        merged = _normalize_prefixes(tuple(configured))
        docs_prefixes = merged
        code_prefixes = merged
    elif isinstance(configured, dict):
        docs_prefixes = _normalize_prefixes(tuple(configured.get("docs") or ()))
        code_prefixes = _normalize_prefixes(tuple(configured.get("code") or ()))
    # Legacy boolean: index framework scripts under the code layer when the
    # explicit code prefix list is empty.
    if not code_prefixes and bool(indexing.get("include_framework_code_for_code_search", False)):
        code_prefixes = (".wavefoundry/framework/scripts",)
    return {"docs": docs_prefixes, "code": code_prefixes}


def _effective_project_include_prefixes(
    root: Path,
    index_dir: Path,
    content_for_filter: str,
    override: tuple[str, ...],
) -> tuple[str, ...]:
    """Resolve project-layer semantic include-prefixes for this run.

    Explicit ``override`` (a CLI ``--project-include-prefix`` or a direct call
    argument) selects the configured surface. Otherwise, for the project layer,
    the indexer reads ``docs/workflow-config.json`` itself and selects the prefix
    list matching this run's content — so launchers (hooks, dashboard, background
    refresh) no longer have to read the config and forward prefixes on every
    invocation.

    The 1p4ww framework-seed fold is a project-DOCS invariant: it must survive
    even when an ``override`` is present. setup_index forwards the merged
    docs+code workflow prefixes as ``override`` (non-empty whenever a project
    configures self-hosting code prefixes like ``.wavefoundry/framework/scripts``),
    so an unconditional ``override`` short-circuit silently drops the folded seeds
    from the docs index. We therefore append ``FRAMEWORK_FOLD_DOCS_PREFIXES`` for
    docs/all content on the project layer regardless of override.
    """
    is_project = _graph_layer_for_index_dir(index_dir) == "project"
    folds_seeds = is_project and content_for_filter in ("docs", "all")
    if override:
        base = _normalize_prefixes(override)
        if folds_seeds:
            return _normalize_prefixes((*base, *FRAMEWORK_FOLD_DOCS_PREFIXES))
        return base
    if not is_project:
        return ()
    wf = _workflow_project_include_prefixes(root)
    # 1p4ww: fold the framework seeds + README into the PROJECT docs index by default.
    if content_for_filter == "docs":
        selected: tuple[str, ...] = (*wf["docs"], *FRAMEWORK_FOLD_DOCS_PREFIXES)
    elif content_for_filter == "code":
        selected = wf["code"]
    else:  # "all"
        selected = (*wf["docs"], *wf["code"], *FRAMEWORK_FOLD_DOCS_PREFIXES)
    return _normalize_prefixes(selected)


def _merged_project_include_prefixes_for_graph(
    root: Path,
    configured_prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    """Union of workflow-config docs+code prefixes for graph extraction.

    Graph runs on every index pass (including docs-only). Semantic layers still
    scope prefixes by content mode; the graph must always see the full configured
    project surface (e.g. ``.wavefoundry/framework/scripts`` under code prefixes).
    """
    if configured_prefixes:
        return _normalize_prefixes(configured_prefixes)
    wf = _workflow_project_include_prefixes(root)
    return _normalize_prefixes((*wf["docs"], *wf["code"]))


def _project_meta_include_prefixes(
    root: Path,
    configured_prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    """Include-prefixes for project ``file_meta`` eligibility — the docs+code
    graph surface PLUS the framework docs folded into the project docs index
    (Wave 1p4ww: ``FRAMEWORK_FOLD_DOCS_PREFIXES``).

    ``files_for_meta`` is computed once and reused by both the docs-content and
    code-content filters, so the folded framework seeds/README must survive into
    it — otherwise they are stripped here (they live under the ``.wavefoundry/``
    blanket exclusion) before the docs-content filter, which DOES allow them, ever
    runs, and the fold never reaches the index. The graph surface
    (``_merged_project_include_prefixes_for_graph``) intentionally omits these
    docs-only prefixes.
    """
    # The fold is a project-DOCS invariant and must reach ``file_meta`` whether or
    # not the project also configures explicit prefixes (self-hosting code
    # prefixes make ``configured_prefixes`` non-empty). An early ``return base``
    # on a non-empty config silently strips the folded seeds before the
    # docs-content filter — which DOES allow them — ever runs.
    base = _merged_project_include_prefixes_for_graph(root, configured_prefixes)
    return _normalize_prefixes((*base, *FRAMEWORK_FOLD_DOCS_PREFIXES))


def _is_generated_code_path(rel_path: str) -> bool:
    return rel_path.startswith(GENERATED_CODE_PREFIXES)


def _is_test_code_path(rel_path: str) -> bool:
    parts = rel_path.split("/")
    if any(part in TEST_DIR_NAMES for part in parts[:-1]):
        return True
    filename = parts[-1]
    return filename.startswith("test_") or filename.endswith("_test.py")


def _is_framework_test_path(rel_path: str) -> bool:
    return rel_path.startswith(FRAMEWORK_TEST_PREFIXES)


def _filter_code_files(
    files: list[Path],
    root: Path,
    *,
    include_tests: bool,
    include_generated: bool,
) -> list[Path]:
    result: list[Path] = []
    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        if path.suffix.lower() not in SOURCE_CODE_EXTENSIONS:
            continue
        if _is_framework_test_path(rel):
            continue
        if not include_generated and _is_generated_code_path(rel):
            continue
        if not include_tests and _is_test_code_path(rel):
            continue
        result.append(path)
    return result


# ---------------------------------------------------------------------------
# Meta I/O
# ---------------------------------------------------------------------------

def _load_meta(index_dir: Path) -> dict:
    meta_path = index_dir / META_JSON
    if meta_path.is_file():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_meta(index_dir: Path, meta: dict) -> None:
    _atomic_write_text(index_dir / META_JSON, json.dumps(meta, indent=2))


def project_index_inputs_stale(root: Path, meta: dict | None = None) -> bool | None:
    """Cheap stat-fast-path staleness check for the project index.

    Returns True/False when a determination is possible, or ``None`` when it
    cannot be made (no built index / no ``file_meta`` snapshot, or any error).
    Canonical home for the check previously inlined in
    ``dashboard_server.py::_project_index_inputs_stale``.

    Uses the same primitives as the indexer build: walk the repo, filter to the
    project-index include set, then ``_detect_changes`` (mtime+size+inode
    pre-filter, hashing only on stat mismatch). No full SHA256 walk per call.
    """
    try:
        index_dir = root / ".wavefoundry" / "index"
        if meta is None:
            meta = _load_meta(index_dir)
        file_meta = meta.get("file_meta") if isinstance(meta, dict) else None
        if not isinstance(file_meta, dict) or not file_meta:
            return None
        # Read configured include prefixes so the staleness check matches what
        # the indexer actually indexes.
        code_prefixes: tuple[str, ...] = ()
        try:
            wf_cfg = json.loads((root / "docs" / "workflow-config.json").read_text(encoding="utf-8"))
            raw = (wf_cfg.get("indexing") or {}).get("project_include_prefixes", {})
            if isinstance(raw, dict):
                raw = raw.get("code") or []
            if isinstance(raw, list):
                code_prefixes = tuple(str(p) for p in raw if p)
        except Exception:
            pass
        files = walk_repo(root, respect_ignore=True)
        files = [path for path in files if not _is_relative_to(path, index_dir)]
        # The project docs index folds the framework seeds + README, so they
        # must survive the ``.wavefoundry/`` blanket exclusion here too.
        include_prefixes = (*code_prefixes, *FRAMEWORK_FOLD_DOCS_PREFIXES)
        files = _filter_project_index_excludes(files, root, (), project_include_prefixes=include_prefixes)
        files = [
            path
            for path in files
            if str(path.relative_to(root)).replace("\\", "/") not in _PROJECT_STALE_IGNORE_PATHS
        ]
        filtered_file_meta = {
            rel_path: entry
            for rel_path, entry in file_meta.items()
            if rel_path not in _PROJECT_STALE_IGNORE_PATHS
        }
        _, changed, removed = _detect_changes(files, root, filtered_file_meta)
        return bool(changed or removed)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Atomic file write helper
# ---------------------------------------------------------------------------

# Wave 1p9iw: bounded retry for the atomic meta.json swap on native Windows. Only the os.replace
# (a MoveFileEx rename) can sharing-violate — WinError 32 (ERROR_SHARING_VIOLATION) or WinError 5
# (ERROR_ACCESS_DENIED) — when a concurrent framework reader (wave_index_health,
# wave_index_build_status, an MCP freshness check, or the dashboard watcher) has meta.json open at the
# instant of the swap. A small fixed bound covers that brief read window; on genuine persistence the
# last exception re-raises (the failure surface is unchanged, not masked).
_META_REPLACE_MAX_ATTEMPTS = 5
_META_REPLACE_BACKOFF_SECONDS = 0.1


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    # Wave 1p9iw: Windows-only bounded retry-with-backoff around the os.replace swap. Mirrors the
    # "Windows-only, bounded retry, POSIX untouched" shape of setup_index._rmtree_clearing_readonly /
    # _clear_readonly_and_retry (waves 1p9hk / 1p6d6): retry ONLY the WinError 5/32 sharing-violation
    # transient on ``os.name == "nt"``, re-raise the last exception once the small bound is exhausted so
    # a persistent lock still surfaces (mirrors the setup_index caller-checks-afterward discipline), and
    # re-raise any other error immediately so a genuinely different failure is not masked or delayed.
    # On POSIX os.replace is atomic and never sharing-violates, so this reduces to a single call — the
    # original path is behaviorally unchanged there.
    for attempt in range(_META_REPLACE_MAX_ATTEMPTS):
        try:
            os.replace(tmp, path)
            return
        except OSError as exc:  # PermissionError is an OSError subclass — both are covered
            if (
                os.name != "nt"
                or getattr(exc, "winerror", None) not in (5, 32)
                or attempt >= _META_REPLACE_MAX_ATTEMPTS - 1
            ):
                raise
            time.sleep(_META_REPLACE_BACKOFF_SECONDS)


# ---------------------------------------------------------------------------
# LanceDB vector index helpers
# ---------------------------------------------------------------------------

def _auto_install_lancedb() -> None:
    """Install lancedb into the shared Wavefoundry tool venv when missing.

    Wave 1p93v: applies the same pip TLS-conflict mitigation (`setup_index._pip_tls_env()`) used at
    every other pip/uv install call site in this codebase, so this one doesn't inherit a corp-only
    `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` unchanged and fail against PyPI behind a TLS-intercepting
    proxy."""
    venv_python = venv_bootstrap.tool_venv_python()  # the single venv resolver (wave 1p7pl)
    if not venv_python.exists():
        raise ImportError(
            "lancedb is not installed and the Wavefoundry tool venv is not bootstrapped yet. "
            "Run manually: python3 .wavefoundry/framework/scripts/setup_index.py"
        )
    print("build_index: lancedb not installed — installing into Wavefoundry tool venv ...", flush=True)
    import setup_index  # wave 1p93v: function-local import, mirrors the established direction-safety pattern
    cmd = [str(venv_python), "-m", "pip", "install", setup_index.LANCEDB_REQUIREMENT]  # wave 1p95j: pinned spec
    result = subprocess_util.isolated_run(cmd, check=False, env=setup_index._pip_tls_env())
    if result.returncode != 0:
        raise ImportError(
            "lancedb auto-install into the Wavefoundry tool venv failed. "
            "Run manually: python3 .wavefoundry/framework/scripts/setup_index.py"
        )
    print("build_index: lancedb installed successfully in the Wavefoundry tool venv.", flush=True)


def _get_lance_db(db_path: Path):
    try:
        import lancedb
    except ImportError:
        _auto_install_lancedb()
        import lancedb  # retry after install
    db_path.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(db_path))


# Wave 1p5ch: streaming full-rebuild. Files are chunked into a bounded buffer that flushes
# (embed → create/append) once it fills, so the full chunk list for a layer is never held in
# memory — peak memory is bounded by the buffer, independent of corpus size. Rows are produced with
# `_embed_texts` + `_make_lance_rows` and the vector + FTS index is built once at the end; the
# produced table is independent of the buffer size (verified by a buffer-invariance test). This
# replaced an earlier `_stream_embed_write` whose caller pre-materialized the whole chunk list.
EMBED_BUFFER_CHUNKS_DEFAULT = 1024  # max chunks buffered before a flush. 1024 = best build
# throughput in the 1p7it on-machine benchmark (M2 Max: fastest + lowest of 64/128/256/1024/2048);
# peak RSS is buffer-invariant on both GPU and CPU, so this is purely a throughput default (see the
# 1p7it Progress Log). Decoupled from SORT_WINDOW_SIZE (the sort window) — different concern.


def _resolve_embed_buffer_chunks(root: Path) -> int:
    """Streaming flush threshold (chunks) — overridable via `indexing.embed_buffer_chunks` in
    docs/workflow-config.json. Floored at EMBED_BATCH_SIZE so GPU batches stay full; defaults to
    EMBED_BUFFER_CHUNKS_DEFAULT."""
    cfg = root / "docs" / "workflow-config.json"
    val = EMBED_BUFFER_CHUNKS_DEFAULT
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            indexing = data.get("indexing", {}) if isinstance(data, dict) else {}
            raw = indexing.get("embed_buffer_chunks") if isinstance(indexing, dict) else None
            if isinstance(raw, int) and raw > 0:
                val = raw
        except (OSError, json.JSONDecodeError):
            pass
    return max(val, EMBED_BATCH_SIZE)


# Per-model forward-pass batch width (1p7iv). The onnxruntime CPU forward pass materializes
# activation tensors that scale with this batch (attention ~ batch x heads x seq^2), so it is the
# dominant CPU-embedding memory lever — on-machine benchmark: bge-small (code) 256->32 cut peak RSS
# ~3.5x, arctic-xs (docs) ~3.8x, both at equal-or-better throughput. Per model because DOCS_MODEL and
# CODE_MODEL differ in size/chunk-length; the GPU static-shape embedder ignores this (uses STATIC_BATCH).
# Default 32 (down from 256): the benchmark's lowest-memory AND fastest CPU point — ~3.5–3.8x less peak
# RSS at equal-or-better throughput (onnxruntime parallelizes each forward pass across cores regardless
# of batch, so a small batch still fills cores). Raise per-model via workflow-config for bigger batches.
_DEFAULT_EMBED_BATCH = 32
_EMBED_BATCH_DEFAULTS = {DOCS_MODEL: _DEFAULT_EMBED_BATCH, CODE_MODEL: _DEFAULT_EMBED_BATCH}
_EMBED_BATCH_CONFIG_KEYS = {DOCS_MODEL: "docs_embed_batch_size", CODE_MODEL: "code_embed_batch_size"}


def _resolve_embed_batch_size(model_name: str, root: Path) -> int:
    """Forward-pass batch width for ``model_name`` — overridable via ``docs/workflow-config.json``:
    per-model ``indexing.{docs,code}_embed_batch_size`` wins, then global ``indexing.embed_batch_size``,
    then the per-model default. A CPU-path memory lever (the GPU static-shape embedder ignores it);
    smaller batch = less onnxruntime activation memory, at equal-or-better CPU throughput."""
    default = _EMBED_BATCH_DEFAULTS.get(model_name, EMBED_BATCH_SIZE)
    cfg = root / "docs" / "workflow-config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            indexing = data.get("indexing", {}) if isinstance(data, dict) else {}
            if isinstance(indexing, dict):
                for key in (_EMBED_BATCH_CONFIG_KEYS.get(model_name), "embed_batch_size"):
                    if key:
                        raw = indexing.get(key)
                        if isinstance(raw, int) and raw > 0:
                            return raw
        except (OSError, json.JSONDecodeError):
            pass
    return default


class _StreamingLayerWriter:
    """Wave 1p5ch: incremental writer for one layer's full rebuild. ``add(chunks)`` embeds a buffer
    and creates-or-appends to the Lance table (the first ``add`` creates it with ``mode="overwrite"``);
    ``finalize()`` builds the vector + FTS index once, after all rows are written. Feeding every chunk
    in a single ``add`` is exactly the batch write, so the produced table is independent of how the
    input is chunked across ``add`` calls — buffering bounds memory without changing output."""

    def __init__(self, db, table_name: str, embedder, label: str, lock_dir: "Optional[Path]" = None,
                 batch_size: int = EMBED_BATCH_SIZE) -> None:
        self.db = db
        self.table_name = table_name
        self.embedder = embedder
        self.label = label
        self.lock_dir = lock_dir
        self.batch_size = batch_size  # forward-pass batch width (per-model; 1p7iv)
        self.table = None
        self.written = 0
        self._lock = None  # ExitStack holding the per-table lock; acquired lazily on first write

    def add(self, chunks: list[dict]) -> None:
        if not chunks:
            return
        vecs = _embed_texts(self.embedder, [c["text"] for c in chunks], batch_size=self.batch_size)
        rows = _make_lance_rows(chunks, vecs)
        if self.table is None:
            # Acquire the per-table lock (which creates the Lance dir) ONLY on the first real write —
            # a layer that produces 0 chunks never locks, so its dir stays absent and the incremental
            # path's "table absent" guard fires correctly (wave 1p5ch).
            if self.lock_dir is not None and self._lock is None:
                import contextlib as _ctx
                self._lock = _ctx.ExitStack()
                self._lock.enter_context(_table_lock(self.lock_dir, create_dir=True))
            self.table = self.db.create_table(self.table_name, data=rows, mode="overwrite")
        else:
            self.table.add(rows)
        self.written += len(chunks)
        # Watchdog heartbeat (wave 1p9j0): one unconditional line per embed flush so the setup
        # stall watchdog's no-progress window keeps resetting during long/thrashing embed
        # stretches between the per-50-file progress prints.
        print(f"build_index: embedded {self.written} chunks ({self.label})", flush=True)

    def finalize(self, verbose: bool = False) -> int:
        # Watchdog heartbeat (wave 1p9j0): the finalize tail (optimize/compact, vector-index and
        # FTS builds) printed only under verbose, leaving a minutes-long silent window at "99%"
        # that could trip the setup stall watchdog on a slow host — announce it unconditionally.
        print(f"build_index: finalizing {self.label} index ({self.written} chunks)", flush=True)
        try:
            return self._finalize_inner(verbose)
        finally:
            self.release_lock()

    def release_lock(self) -> None:
        """Release the per-table lock without building any index. ``finalize`` calls this on the
        success path; the runner calls it in a ``finally`` so a mid-stream exception (before
        ``finalize``) still frees the lock in-process rather than relying on subprocess exit."""
        if self._lock is not None:
            self._lock.close()
            self._lock = None

    def _finalize_inner(self, verbose: bool = False) -> int:
        if self.table is None:
            return 0
        # Wave 1p95j: compact + clean FIRST — the streaming append leaves ~26 small data fragments,
        # and `create_table(mode="overwrite")` on a rebuild over a non-empty dir leaves the prior
        # build's data versions behind. `optimize(cleanup_older_than=0)` compacts the fragments and
        # reclaims stale versions. This MUST run BEFORE the index builds: running it after would
        # compact the data out from under a just-built FTS/vector index, invalidating it and forcing
        # a duplicate rebuild whose stale copy can't be GC'd without `pylance` (a naive
        # optimize-after-index left TWO ~40 MB FTS copies). Mirrors the incremental path's order
        # (compact → build indexes). Best-effort; never fails the build.
        if not _optimize_lance_table(self.table):
            # Wave 1p9aj: optimize() failed (e.g. the Lance list-offset corruption bug) — self-heal by
            # compacting via a fresh rewrite so the table reclaims instead of growing unbounded. The
            # rewrite rebuilds the vector + FTS indices itself, so return early on success. Never raise
            # out of finalize: on a rewrite failure, warn and fall through to a best-effort normal index
            # build over the (still readable) un-reclaimed table.
            try:
                self.table = _compact_by_rewrite(self.db, self.table_name)
                if verbose:
                    print(
                        f"build_index: reclaimed '{self.table_name}' via compact-by-rewrite (optimize failed)",
                        flush=True,
                    )
                return self.written
            except Exception as exc:
                print(
                    f"build_index: reclaim of '{self.table_name}' skipped ({exc})",
                    file=sys.stderr,
                )
        if self.written >= LANCEDB_INDEX_THRESHOLD:
            try:
                self.table.create_index(metric="cosine", index_type="IVF_HNSW_SQ", replace=True)
                if verbose:
                    print(
                        f"build_index: LanceDB IVF_HNSW_SQ index created for '{self.table_name}' ({self.written} rows)",
                        flush=True,
                    )
            except Exception as exc:
                print(
                    f"build_index: LanceDB index creation for '{self.table_name}' skipped ({exc})",
                    file=sys.stderr,
                )
        # replace=True (was False) — a full rebuild over a non-empty dir replaces the FTS index
        # rather than stacking a second ~40 MB copy. Built AFTER the compaction so it indexes the
        # final compacted data.
        _create_fts_index(self.table, self.table_name, replace=True)
        return self.written


def _run_streaming_full_rebuild(
    *,
    db_path: Path,
    files_to_index: list,
    root: Path,
    build_docs: bool,
    build_code: bool,
    docs_embedder,
    code_embedder,
    chunks_emitted_by_file: dict,
    buffer_chunks: int,
    verbose: bool,
    docs_elapsed: list,
    code_elapsed: list,
) -> None:
    """Wave 1p5ch: full rebuild as a bounded-buffer stream. Chunks each file ONCE (recording
    ``chunks_emitted_by_file``), routes doc/code chunks to per-layer buffers, and flushes a buffer
    (embed → create/append) once it reaches ``buffer_chunks``; the vector + FTS index is built once
    per layer at the end. Peak memory is bounded by the buffers, independent of corpus size.
    Progress is reported per file (``file N / M``) — no total-chunk pre-count."""
    db = _get_lance_db(db_path)
    # Each writer acquires its per-table lock lazily on first write (see _StreamingLayerWriter.add),
    # so a layer that produces 0 chunks never creates its Lance dir — matching the old full path and
    # keeping the incremental "table absent" guard correct.
    docs_writer = _StreamingLayerWriter(db, "docs", docs_embedder, "doc", lock_dir=db_path / "docs.lance",
                                        batch_size=_resolve_embed_batch_size(DOCS_MODEL, root)) if build_docs else None
    code_writer = _StreamingLayerWriter(db, "code", code_embedder, "code", lock_dir=db_path / "code.lance",
                                        batch_size=_resolve_embed_batch_size(CODE_MODEL, root)) if build_code else None
    docs_buf: list[dict] = []
    code_buf: list[dict] = []
    t_docs = 0.0
    t_code = 0.0
    total = len(files_to_index)

    try:
        for i, file_path in enumerate(files_to_index, 1):
            rel = str(file_path.relative_to(root)).replace("\\", "/")
            try:
                source_text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            dc, cc = _chunks_for_file(rel, source_text)
            chunks_emitted_by_file[rel] = len(dc) + len(cc)
            if build_docs and dc:
                docs_buf.extend(dc)
                if len(docs_buf) >= buffer_chunks:
                    _t = time.monotonic(); docs_writer.add(docs_buf); t_docs += time.monotonic() - _t
                    docs_buf = []
            if build_code and cc:
                code_buf.extend(cc)
                if len(code_buf) >= buffer_chunks:
                    _t = time.monotonic(); code_writer.add(code_buf); t_code += time.monotonic() - _t
                    code_buf = []
            if i == total or i % 50 == 0:
                print(f"build_index: indexed file {i}/{total} files", flush=True)

        if build_docs and docs_buf:
            _t = time.monotonic(); docs_writer.add(docs_buf); t_docs += time.monotonic() - _t
        if build_code and code_buf:
            _t = time.monotonic(); code_writer.add(code_buf); t_code += time.monotonic() - _t
        if docs_writer is not None:
            _t = time.monotonic(); docs_writer.finalize(verbose); t_docs += time.monotonic() - _t
        if code_writer is not None:
            _t = time.monotonic(); code_writer.finalize(verbose); t_code += time.monotonic() - _t
    finally:
        # finalize() releases the lock on the success path; this frees it if the loop or a flush
        # raised before finalize ran (no-op once finalize has nulled the lock).
        for _w in (docs_writer, code_writer):
            if _w is not None:
                _w.release_lock()

    docs_elapsed.append(t_docs)
    code_elapsed.append(t_code)


def _optimize_lance_table(table) -> bool:
    """Compact a LanceDB table, swallowing errors (advisory).

    Returns ``True`` when ``optimize()`` succeeded, ``False`` when it raised (e.g. the Lance list-offset
    corruption bug — ``Max offset … exceeds length of values``, lance-format/lance #7538 — where in-place
    compaction cannot decode the corrupted pages). Callers that hold ``db`` + ``table_name`` context can
    escalate a ``False`` to ``_compact_by_rewrite`` / ``reclaim_lance_table`` to reclaim the table."""
    try:
        from datetime import timedelta
        table.optimize(cleanup_older_than=timedelta(seconds=0))
        return True
    except Exception as exc:
        print(f"build_index: LanceDB optimize failed ({exc})", file=sys.stderr)
        return False


def _compact_by_rewrite(db, table_name: str):
    """Reclaim a LanceDB table whose in-place ``optimize()`` fails by rewriting it fresh.

    Wave 1p9aj. When ``optimize()`` cannot compact a table because of the Lance list-offset corruption
    bug (lance-format/lance #7538; unbounded on-disk bloat, no in-place recovery), normal *reads* still
    succeed — only the compaction/decode path fails. So read the live rows with ``to_arrow()`` and write
    them to a fresh table via ``create_table(mode="overwrite")``: a fresh write recomputes the
    list-column offsets from the clean in-memory Arrow data, sidestepping the append-time offset-rebasing
    bug (this is why the rewrite reclaims — proven ``docs.lance`` 1.6 GB → 55 MB, zero re-embed — where
    ``optimize()`` cannot). Then rebuild the vector + FTS indices and compact.

    The swap uses ``create_table(mode="overwrite")`` and **never** ``db.rename_table`` — the latter raises
    ``NotImplementedError: rename_table is not supported in LanceDB OSS``, and a drop-then-rename would
    leave the table missing if the rename failed. ``to_arrow()`` raising (the data itself is unreadable,
    not just the compaction path) propagates so the caller can fall back to a full re-embed rebuild.

    Returns the new table handle."""
    src = db.open_table(table_name)
    data = src.to_arrow()  # propagates on a real read failure -> caller falls back to full rebuild
    row_count = data.num_rows
    new_table = db.create_table(table_name, data=data, mode="overwrite")
    if row_count >= LANCEDB_INDEX_THRESHOLD:
        try:
            new_table.create_index(metric="cosine", index_type="IVF_HNSW_SQ", replace=True)
        except Exception as exc:
            print(
                f"build_index: reclaim vector-index rebuild for '{table_name}' skipped ({exc})",
                file=sys.stderr,
            )
    _create_fts_index(new_table, table_name, replace=True)
    _optimize_lance_table(new_table)
    return new_table


def reclaim_lance_table(db, table_name: str) -> dict:
    """Tiered reclaim of a bloated LanceDB table. Wave 1p9aj.

    Tier 1: ``optimize()`` in place (the normal, non-corrupt case). Tier 2 (on an ``optimize()``
    failure): compact by rewrite via ``_compact_by_rewrite`` — no re-embed. Tier 3 (only when the
    ``to_arrow()`` read itself fails — true data loss, not just compaction corruption): signal the caller
    to full-rebuild via ``needs_rebuild``. Never raises. Returns
    ``{tier, rows, needs_rebuild, error}``."""
    result = {"tier": 0, "rows": 0, "needs_rebuild": False, "error": None}
    try:
        table = db.open_table(table_name)
    except Exception as exc:
        result["tier"] = 3
        result["needs_rebuild"] = True
        result["error"] = f"open failed: {exc}"
        return result
    if _optimize_lance_table(table):
        result["tier"] = 1
        try:
            result["rows"] = table.count_rows()
        except Exception:
            pass
        return result
    # optimize() failed -> Tier 2 compact by rewrite (or Tier 3 if the read/rewrite itself fails).
    try:
        new_table = _compact_by_rewrite(db, table_name)
        result["tier"] = 2
        try:
            result["rows"] = new_table.count_rows()
        except Exception:
            pass
        return result
    except Exception as exc:
        result["tier"] = 3
        result["needs_rebuild"] = True
        result["error"] = f"rewrite failed: {exc}"
        return result


# Wave 1p9aj: semantic Lance tables and their on-disk directories under .wavefoundry/index/.
_LANCE_TABLE_FILES = {"docs": "docs.lance", "code": "code.lance"}


def _lance_dir_bytes(path: Path) -> int:
    """Best-effort sum of file sizes under a ``.lance`` table directory; 0 on any error."""
    total = 0
    try:
        for dirpath, _dirs, files in os.walk(path):
            for name in files:
                try:
                    total += (Path(dirpath) / name).stat().st_size
                except OSError:
                    pass
    except Exception:
        return total
    return total


def optimize_index_tables(index_dir: Path, tables: "tuple[str, ...]" = ("docs", "code")) -> dict:
    """Run the tiered reclaim (``reclaim_lance_table``) over the given Lance tables under the whole-index
    build lock. Wave 1p9aj. Returns ``{table: {tier, rows, needs_rebuild, error, bytes_before,
    bytes_after}}`` for each **existing** table (absent tables are skipped). Reclaim-only — it never
    re-embeds; a Tier-3 (unreadable) table is reported via ``needs_rebuild`` for the caller to rebuild.

    Shared by ``wave_index_optimize`` and the automatic end-of-``setup``/``upgrade`` optimize pass. May
    raise ``IndexBuildAlreadyRunning`` if another build holds the lock; callers handle that."""
    results: dict = {}
    existing = [t for t in tables if t in _LANCE_TABLE_FILES and (index_dir / _LANCE_TABLE_FILES[t]).exists()]
    if not existing:
        return results
    with _index_build_lock(index_dir):
        db = _get_lance_db(index_dir)
        for t in existing:
            tdir = index_dir / _LANCE_TABLE_FILES[t]
            before = _lance_dir_bytes(tdir)
            res = reclaim_lance_table(db, t)
            res["bytes_before"] = before
            res["bytes_after"] = _lance_dir_bytes(tdir)
            results[t] = res
    return results


def _create_fts_index(table, table_name: str, replace: bool = False) -> None:
    """Create (or rebuild) a lance-index full-text search index on the 'text' column.

    ``replace=True`` should be used after incremental writes so that newly
    added rows are included in the FTS index.  ``optimize()`` alone does NOT
    refresh Tantivy indexes; an explicit rebuild is required.

    Tokenizer: ``simple`` (splits on whitespace and punctuation) with stemming
    and stop-word removal disabled, ``max_token_length=80``, and
    ``with_position=False``.

    Why ``simple``:  punctuation like ``.`` and ``(`` acts as a token boundary,
    so ``build_pack.version`` indexes as ``build_pack`` and ``version`` — both
    independently searchable.  ``whitespace`` would keep the whole dotted string
    as one token (bad for component matching); ``raw`` treats the entire text as
    a single token (useless for search).

    Why ``stem=False, remove_stop_words=False``:  stemming mangles identifiers
    (``chunks`` → ``chunk``); stop-word removal silently drops name components
    like ``is`` or ``a`` that legitimately appear in variable names.
    ``lower_case=True`` preserves case-insensitive query matching.

    Note: underscores are punctuation under ``simple``, so compound identifiers
    (``SORT_WINDOW_SIZE``) are indexed as individual tokens (``sort``, ``window``,
    ``size``).  The dense retrieval path compensates: exact identifier queries
    that produce noisy BM25 hits are rescored by the cross-encoder reranker.

    Why ``with_position=False``: Wavefoundry uses FTS for candidate recall in
    hybrid docs/code retrieval, not exact phrase/proximity search. Dropping
    positions substantially reduces FTS storage; server-side query shaping must
    avoid phrase queries that require positions.
    """
    try:
        table.create_fts_index(
            "text",
            replace=replace,
            base_tokenizer="simple",
            stem=False,
            remove_stop_words=False,
            lower_case=True,
            max_token_length=80,
            with_position=False,
        )
    except Exception as exc:
        print(
            f"build_index: FTS index creation for '{table_name}' skipped ({exc})",
            file=sys.stderr,
        )


def _lance_fragment_count(table) -> int:
    """Best-effort fragment count; returns 0 on failure."""
    try:
        stats = table.stats()
        if isinstance(stats, dict):
            return int(stats.get("num_fragments", 0))
    except Exception:
        pass
    try:
        return len(table.list_versions())
    except Exception:
        pass
    return 0


def _update_lance_table(db_path: Path, table_name: str, file_path: str, new_rows: list) -> None:
    """Delete existing rows for file_path and add new_rows; compact if needed."""
    db = _get_lance_db(db_path)
    table = db.open_table(table_name)
    safe_path = file_path.replace("'", "''")
    table.delete(f"path = '{safe_path}'")
    if new_rows:
        table.add(new_rows)
    if _lance_fragment_count(table) > LANCEDB_COMPACT_THRESHOLD:
        _optimize_lance_table(table)


def _delete_lance_chunks(db_path: Path, table_name: str, file_path: str) -> None:
    """Delete all rows for file_path from a LanceDB table; compact if needed."""
    db = _get_lance_db(db_path)
    table = db.open_table(table_name)
    safe_path = file_path.replace("'", "''")
    table.delete(f"path = '{safe_path}'")
    if _lance_fragment_count(table) > LANCEDB_COMPACT_THRESHOLD:
        _optimize_lance_table(table)


def _chunk_hash(chunk: dict) -> str:
    """Return a stable fingerprint for the chunk content that affects retrieval."""
    payload = {
        "kind": str(chunk.get("kind") or ""),
        "language": str(chunk.get("language") or ""),
        "section": str(chunk.get("section") or ""),
        "text": str(chunk.get("text") or ""),
        "tags": chunk.get("tags") or [],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _normalize_chunk_row_metadata(row: dict) -> dict:
    """Normalize row metadata so freshly chunked rows compare cleanly to Lance rows."""
    normalized = {
        "id": str(row.get("id") or ""),
        "path": str(row.get("path") or ""),
        "kind": str(row.get("kind") or ""),
        "language": str(row.get("language") or ""),
        "section": str(row.get("section") or ""),
        "text": str(row.get("text") or ""),
        "chunk_hash": str(row.get("chunk_hash") or ""),
    }
    tags = row.get("tags")
    if isinstance(tags, list):
        normalized["tags"] = " ".join(str(t) for t in tags)
    else:
        normalized["tags"] = str(tags or "")
    lines = row.get("lines")
    if hasattr(lines, "tolist"):
        lines = lines.tolist()
    if isinstance(lines, tuple):
        lines = list(lines)
    normalized["lines"] = [int(v) for v in lines] if isinstance(lines, list) else []
    return normalized


def _row_metadata_matches_current(existing: dict, current: dict) -> bool:
    return _normalize_chunk_row_metadata(existing) == _normalize_chunk_row_metadata(current)


def _make_lance_rows(chunks: list[dict], vecs: "np.ndarray | list") -> list[dict]:
    """Convert chunk dicts + vector array into LanceDB row dicts."""
    rows = []
    for chunk, vec in zip(chunks, vecs):
        row = dict(chunk)
        if isinstance(row.get("tags"), list):
            row["tags"] = " ".join(str(t) for t in row["tags"])
        row["chunk_hash"] = _chunk_hash(chunk)
        # Normalize nullable string fields to "" so LanceDB always sees a non-null
        # string column type. If the first batch is all-None (e.g. Markdown-only), 
        # LanceDB infers the column as Null; a later batch with a real string value
        # then raises: ValueError: cannot cast field 'language' from Utf8 to Null.
        for _nullable_str in ("language", "section"):
            if row.get(_nullable_str) is None:
                row[_nullable_str] = ""
        row["vector"] = vec.tolist() if hasattr(vec, "tolist") else list(vec)
        rows.append(row)
    return rows


def _read_lance_rows_for_paths(db_path: Path, table_name: str, paths: set[str]) -> list[dict]:
    """Return existing LanceDB rows, including vectors, for the given paths."""
    if not paths or not (db_path / f"{table_name}.lance").is_dir():
        return []
    try:
        db = _get_lance_db(db_path)
        table = db.open_table(table_name)
        escaped = [p.replace("'", "''") for p in paths]
        in_clause = ", ".join(f"'{p}'" for p in escaped)
        return table.search().where(f"path IN ({in_clause})", prefilter=True).limit(None).to_arrow().to_pylist()
    except Exception:
        return []


def _delete_lance_rows_by_ids(table, ids: set[str]) -> None:
    if not ids:
        return
    ordered = sorted(ids)
    # Keep delete predicates compact; very large updates can otherwise create
    # unwieldy SQL strings for LanceDB's filter parser.
    for idx in range(0, len(ordered), 100):
        batch = [item.replace("'", "''") for item in ordered[idx:idx + 100]]
        in_clause = ", ".join(f"'{item}'" for item in batch)
        table.delete(f"id IN ({in_clause})")


def _detect_lance_drift(
    db_path: Path,
    file_meta: dict[str, dict],
    *,
    tables: tuple[str, ...] = ("docs", "code"),
    verbose: bool = False,
) -> set[str]:
    """Wave 1p3b9 (1p399) + 1p3iv (1p3iw): return the set of paths in
    ``file_meta`` that have ZERO rows in any of the configured Lance tables,
    EXCLUDING paths the indexer previously recorded as legitimately emitting
    zero chunks.

    These paths are "drifted" — ``meta.json`` claims they're indexed at a
    known hash, but the Lance chunks table has no rows for them. The
    incremental indexer's skip-on-hash-match optimization perpetuates the
    missing state indefinitely until something forces the file's mtime to
    change. This helper surfaces drifted paths so the caller can force
    them through the re-chunk + re-embed path.

    Empty-file exclusion (1p3iw): entries with explicit ``chunks_emitted == 0``
    are skipped — the prior indexing run recorded that this file legitimately
    produces no chunks (empty file, all-whitespace, marker-region-dominated
    content). Re-chunking would produce zero chunks again and the next
    incremental update would flag it again — silent thrash. Entries with
    ``chunks_emitted`` absent (legacy ``meta.json`` from before this field
    existed, or a fresh stat-mismatch entry built in ``_detect_changes``)
    fall through to the drift check unchanged — one repair learns the true
    count and populates the field; subsequent updates skip silently if it
    landed at zero.

    Implementation: pulls just the ``path`` column from each Lance table
    (cheap on large tables — single column read, no vector data fetched),
    unions the path sets, and returns the file_meta paths absent from the
    union. Lance's columnar engine makes DISTINCT-on-string near-O(rows)
    per AC-9 (sub-second on 10K rows, <200ms on 100K rows).

    Returns empty set when:
    - LanceDB cannot be opened (table missing, db unavailable)
    - No Lance tables exist yet (fresh layer)
    - All considered paths have rows in at least one table (happy path)
    """
    if not file_meta:
        return set()
    # Wave 1p3iw: exclude paths previously recorded as legitimately empty.
    # Missing ``chunks_emitted`` (legacy entries / fresh stat-mismatch entries)
    # falls through to the drift check unchanged.
    file_meta_paths = {
        path for path, entry in file_meta.items()
        if not (isinstance(entry, dict) and entry.get("chunks_emitted") == 0)
    }
    if not file_meta_paths:
        return set()
    if not any((db_path / f"{t}.lance").is_dir() for t in tables):
        return set()
    try:
        db = _get_lance_db(db_path)
    except Exception as exc:
        if verbose:
            print(f"build_index: drift-detect skipped — could not open LanceDB ({exc})", flush=True)
        return set()
    lance_paths: set[str] = set()
    for table_name in tables:
        if not (db_path / f"{table_name}.lance").is_dir():
            continue
        try:
            table = db.open_table(table_name)
            # Single-column read; cheap on large tables.
            path_arrow = table.to_arrow().column("path")
            lance_paths.update(p for p in path_arrow.to_pylist() if p)
        except Exception as exc:
            if verbose:
                print(
                    f"build_index: drift-detect {table_name} failed ({exc})",
                    flush=True,
                )
            continue
    return file_meta_paths - lance_paths


def _reap_stranded_lance_rows(
    db_path: Path,
    eligible_paths: set[str],
    *,
    tables: tuple[str, ...] = ("docs", "code"),
    verbose: bool = False,
) -> dict[str, int]:
    """Delete LanceDB rows whose ``path`` is not in the current eligible set.

    Closes the workflow-config-evolution blind spot: when ``workflow-config.json``
    narrows include-prefixes, the next incremental update drops the now-ineligible
    paths from ``meta.json`` (via ``_detect_changes``), but only paths that were
    *still in old_meta when the narrowing was detected* get evicted from LanceDB.
    Subsequent incrementals never see those paths in ``old_meta`` again, so their
    LanceDB rows orphan silently until a full rebuild.

    This reaper reconciles the *current* LanceDB row set against the *current*
    eligible set on every incremental update, regardless of meta state. It is
    set-difference + a single batched DELETE per table — no file I/O for
    ineligible paths.

    Returns ``{"docs": N, "code": M, "total": N+M}`` row counts reaped per table.
    """
    reaped: dict[str, int] = {"docs": 0, "code": 0, "total": 0}
    if not (db_path / "docs.lance").is_dir() and not (db_path / "code.lance").is_dir():
        return reaped
    try:
        db = _get_lance_db(db_path)
    except Exception as exc:
        if verbose:
            print(f"build_index: reaper skipped — could not open LanceDB ({exc})", flush=True)
        return reaped
    for table_name in tables:
        if not (db_path / f"{table_name}.lance").is_dir():
            continue
        try:
            table = db.open_table(table_name)
            # Pull just the path column to keep the read cheap on large tables.
            path_arrow = table.to_arrow().column("path")
            lance_paths = {p for p in path_arrow.to_pylist() if p}
            stranded = lance_paths - eligible_paths
            if not stranded:
                continue
            # Count rows-to-delete (not unique paths) for accurate operator signal.
            count_pre = table.count_rows()
            ordered = sorted(stranded)
            for idx in range(0, len(ordered), 100):
                batch = [p.replace("'", "''") for p in ordered[idx:idx + 100]]
                in_clause = ", ".join(f"'{p}'" for p in batch)
                table.delete(f"path IN ({in_clause})")
            count_post = table.count_rows()
            reaped_here = max(count_pre - count_post, 0)
            reaped[table_name] = reaped_here
            reaped["total"] += reaped_here
            if verbose:
                print(
                    f"build_index: reaper {table_name} — {len(stranded)} stranded path(s), "
                    f"{reaped_here} row(s) reaped",
                    flush=True,
                )
        except Exception as exc:
            if verbose:
                print(f"build_index: reaper {table_name} failed ({exc})", flush=True)
            continue
    return reaped


def _embed_chunks_for_incremental(label: str, chunks: list[dict], embedder) -> "Optional[np.ndarray]":
    """Embed only the chunks that changed during the incremental path."""
    if not chunks:
        return None
    total = len(chunks)
    order = sorted(range(total), key=lambda i: len(chunks[i]["text"]))
    inverse = [0] * total
    for new_pos, old_pos in enumerate(order):
        inverse[old_pos] = new_pos
    sorted_texts = [chunks[i]["text"] for i in order]
    import numpy as _np
    sorted_vecs = _embed_texts(embedder, sorted_texts)
    return sorted_vecs[inverse]


def _log_semantic_file_delta(path: str, table_name: str, stats: dict[str, int], *, fallback: bool = False) -> None:
    note = " fallback=file-replace" if fallback else ""
    print(
        "build_index: semantic file update "
        f"path={path} table={table_name} "
        f"written={stats.get('written', 0)} "
        f"removed={stats.get('removed', 0)} "
        f"unchanged={stats.get('unchanged', 0)}{note}",
        flush=True,
    )


def _plan_lance_delta_rows(
    *,
    existing_rows: list[dict],
    new_chunks: list[dict],
    embedder,
    label: str,
) -> tuple[set[str], list[dict], bool, dict[str, int]]:
    """Plan row deletes/adds for a table and embed only changed/new chunks.

    Returns (delete_ids, rows_to_add, fallback_required, stats).
    """
    new_by_id = {str(chunk.get("id") or ""): chunk for chunk in new_chunks if chunk.get("id")}
    if not new_by_id:
        delete_ids = {str(row.get("id") or "") for row in existing_rows if row.get("id")}
        return delete_ids, [], False, {"written": 0, "removed": len(delete_ids), "unchanged": 0}
    # Table-wide chunk_hash homogeneity preflight: if any existing row lacks a
    # usable chunk_hash (missing key OR present-but-empty value), the delta plan
    # cannot reliably match content, so force a full table rebuild rather than
    # silently retaining stale rows.
    if any(not str(row.get("chunk_hash") or "").strip() for row in existing_rows):
        return set(), [], True, {"written": 0, "removed": 0, "unchanged": 0}

    existing_by_id = {str(row.get("id") or ""): row for row in existing_rows if row.get("id")}
    existing_by_hash: dict[str, list[dict]] = {}
    for row in existing_rows:
        chunk_hash = str(row.get("chunk_hash") or "")
        if chunk_hash:
            existing_by_hash.setdefault(chunk_hash, []).append(row)

    delete_ids: set[str] = set()
    rows_to_add: list[dict] = []
    chunks_to_embed: list[dict] = []
    chunk_positions: list[int] = []
    reused_vectors = 0
    unchanged = 0

    for chunk_id, chunk in new_by_id.items():
        current_row = dict(chunk)
        current_row["chunk_hash"] = _chunk_hash(chunk)
        current_hash = current_row["chunk_hash"]
        existing = existing_by_id.get(chunk_id)
        if existing is not None and str(existing.get("chunk_hash") or "") == current_hash:
            if not _row_metadata_matches_current(existing, current_row):
                delete_ids.add(chunk_id)
                vector = existing.get("vector")
                rows_to_add.append(_make_lance_rows([chunk], [vector])[0])
                reused_vectors += 1
            else:
                unchanged += 1
            continue

        if existing is not None:
            delete_ids.add(chunk_id)

        # If a line-window or fallback chunk got a new id but the text fingerprint
        # is unique, reuse the vector while writing the current metadata.
        hash_matches = existing_by_hash.get(current_hash) or []
        if len(hash_matches) == 1:
            matched = hash_matches[0]
            matched_id = str(matched.get("id") or "")
            if matched_id and matched_id not in new_by_id:
                delete_ids.add(matched_id)
                vector = matched.get("vector")
                rows_to_add.append(_make_lance_rows([chunk], [vector])[0])
                reused_vectors += 1
                continue
        elif len(hash_matches) > 1:
            chunks_to_embed.append(chunk)
            chunk_positions.append(len(rows_to_add))
            rows_to_add.append({})
            continue

        chunks_to_embed.append(chunk)
        chunk_positions.append(len(rows_to_add))
        rows_to_add.append({})

    for old_id in set(existing_by_id) - set(new_by_id):
        old_hash = str(existing_by_id[old_id].get("chunk_hash") or "")
        if len(existing_by_hash.get(old_hash, [])) == 1 and any(_chunk_hash(c) == old_hash for c in new_chunks):
            continue
        delete_ids.add(old_id)

    if chunks_to_embed:
        vecs = _embed_chunks_for_incremental(label, chunks_to_embed, embedder)
        embedded_rows = _make_lance_rows(chunks_to_embed, vecs)
        for pos, row in zip(chunk_positions, embedded_rows):
            rows_to_add[pos] = row

    rows_to_add = [row for row in rows_to_add if row]
    return delete_ids, rows_to_add, False, {
        "written": len(rows_to_add),
        "removed": len(delete_ids),
        "unchanged": unchanged,
    }


def _count_chunks_for_paths(db_path: Path, table_name: str, paths: set[str]) -> int:
    """Return the number of existing chunks in table_name belonging to the given paths."""
    if not paths or not (db_path / f"{table_name}.lance").is_dir():
        return 0
    try:
        db = _get_lance_db(db_path)
        table = db.open_table(table_name)
        escaped = [p.replace("'", "''") for p in paths]
        in_clause = ", ".join(f"'{p}'" for p in escaped)
        return table.search().where(f"path IN ({in_clause})", prefilter=True).limit(None).to_pandas().shape[0]
    except Exception:
        return 0


def _lance_incremental_write(
    db_path: Path,
    stale: set[str],
    new_doc_chunks: list[dict],
    docs_embedder,
    new_code_chunks: list[dict],
    code_embedder,
    build_docs: bool,
    build_code: bool,
    verbose: bool = False,
) -> None:
    """Apply incremental row deltas, embedding only changed/new chunks."""
    db = _get_lance_db(db_path)
    for table_name, build_flag, chunks, embedder, label in (
        ("docs", build_docs, new_doc_chunks, docs_embedder, "doc"),
        ("code", build_code, new_code_chunks, code_embedder, "code"),
    ):
        if not build_flag:
            continue
        table_dir = db_path / f"{table_name}.lance"
        with _table_lock(table_dir):
            if not table_dir.is_dir():
                # Table absent — create with new rows only (shouldn't happen after upgrade guard).
                vecs = _embed_chunks_for_incremental(label, chunks, embedder) if chunks else None
                if chunks and vecs is not None:
                    tbl = db.create_table(table_name, data=_make_lance_rows(chunks, vecs), mode="create")
                    _create_fts_index(tbl, table_name, replace=False)
                    chunks_by_path: dict[str, list[dict]] = {}
                    for chunk in chunks:
                        chunks_by_path.setdefault(str(chunk.get("path") or ""), []).append(chunk)
                    for file_path, path_chunks in sorted(chunks_by_path.items()):
                        _log_semantic_file_delta(
                            file_path,
                            table_name,
                            {"written": len(path_chunks), "removed": 0, "unchanged": 0},
                        )
                continue
            table = db.open_table(table_name)
            chunks_by_path: dict[str, list[dict]] = {}
            for chunk in chunks:
                chunks_by_path.setdefault(str(chunk.get("path") or ""), []).append(chunk)
            existing_rows = _read_lance_rows_for_paths(db_path, table_name, stale)
            existing_by_path: dict[str, list[dict]] = {}
            for row in existing_rows:
                existing_by_path.setdefault(str(row.get("path") or ""), []).append(row)

            rows_to_add: list[dict] = []
            ids_to_delete: set[str] = set()
            fallback_paths: set[str] = set()

            for file_path in stale:
                path_existing = existing_by_path.get(file_path, [])
                path_chunks = chunks_by_path.get(file_path, [])
                delete_ids, add_rows, fallback_required, stats = _plan_lance_delta_rows(
                    existing_rows=path_existing,
                    new_chunks=path_chunks,
                    embedder=embedder,
                    label=label,
                )
                if fallback_required:
                    fallback_paths.add(file_path)
                    continue
                ids_to_delete.update(delete_ids)
                rows_to_add.extend(add_rows)
                if path_existing or path_chunks:
                    _log_semantic_file_delta(file_path, table_name, stats)

            _delete_lance_rows_by_ids(table, ids_to_delete)

            for file_path in sorted(fallback_paths):
                safe_path = file_path.replace("'", "''")
                table.delete(f"path = '{safe_path}'")
                path_chunks = chunks_by_path.get(file_path, [])
                vecs = _embed_chunks_for_incremental(label, path_chunks, embedder) if path_chunks else None
                if path_chunks and vecs is not None:
                    rows_to_add.extend(_make_lance_rows(path_chunks, vecs))
                _log_semantic_file_delta(
                    file_path,
                    table_name,
                    {"written": len(path_chunks), "removed": len(existing_by_path.get(file_path, [])), "unchanged": 0},
                    fallback=True,
                )

            if rows_to_add:
                table.add(rows_to_add)
            reclaimed = False
            if _lance_fragment_count(table) > LANCEDB_COMPACT_THRESHOLD:
                if verbose:
                    print(f"build_index: compacting {table_name} table", flush=True)
                if not _optimize_lance_table(table):
                    # Wave 1p9aj: self-heal a compaction failure (the Lance list-offset corruption bug)
                    # by rewriting the table fresh — reclaims instead of growing unbounded. The rewrite
                    # rebuilds the vector + FTS indices, so re-point `table` and skip the redundant
                    # index builds below. Never raise: on a rewrite failure, warn and continue.
                    try:
                        table = _compact_by_rewrite(db, table_name)
                        reclaimed = True
                        if verbose:
                            print(
                                f"build_index: reclaimed '{table_name}' via compact-by-rewrite (optimize failed)",
                                flush=True,
                            )
                    except Exception as exc:
                        print(
                            f"build_index: reclaim of '{table_name}' skipped ({exc})",
                            file=sys.stderr,
                        )
                if not reclaimed:
                    try:
                        row_count = table.count_rows()
                    except Exception:
                        row_count = 0
                    if row_count >= LANCEDB_INDEX_THRESHOLD:
                        try:
                            table.create_index(metric="cosine", index_type="IVF_HNSW_SQ", replace=True)
                            if verbose:
                                print(
                                    f"build_index: LanceDB IVF_HNSW_SQ index rebuilt for '{table_name}' ({row_count} rows)",
                                    flush=True,
                                )
                        except Exception as exc:
                            print(
                                f"build_index: LanceDB index rebuild for '{table_name}' skipped ({exc})",
                                file=sys.stderr,
                            )
            # Wave 1p95j: only rebuild the FTS index when this table actually changed. Previously the
            # FTS index (~40 MB) was rebuilt (replace=True) on EVERY incremental pass — even a no-op
            # pass that produced no adds/deletes for this table (e.g. the post-edit hook firing for a
            # file in the OTHER layer) — needlessly re-materializing an identical index and churning
            # artifacts. Gating on real change removes that waste, cutting the reindex rate that
            # drove the observed `_indices/` growth. (A cleanup is NOT run here: `optimize` recompacts
            # the data, which would invalidate this just-built FTS and force a duplicate whose stale
            # copy can't be GC'd without `pylance` — the fragment-gated `optimize` above already
            # compacts BEFORE the indexes when it fires, which is the correct order.)
            table_changed = bool(rows_to_add) or bool(ids_to_delete) or bool(fallback_paths)
            if table_changed and not reclaimed:
                # When reclaimed above, _compact_by_rewrite already rebuilt the FTS index.
                _create_fts_index(table, table_name, replace=True)


# Wave 1p99o: `struct flock` field order differs between Linux and macOS/BSD; there is no portable
# Python helper. Build/parse it per-platform for the non-destructive F_GETLK probe.
_FLOCK_STRUCT = {
    # Linux (asm-generic, x86-64/arm64): short l_type; short l_whence; off_t l_start; off_t l_len; pid_t l_pid;
    "linux": ("@hhqqi", ("l_type", "l_whence", "l_start", "l_len", "l_pid")),
    # macOS/BSD: off_t l_start; off_t l_len; pid_t l_pid; short l_type; short l_whence;
    "darwin": ("@qqihh", ("l_start", "l_len", "l_pid", "l_type", "l_whence")),
}


def _index_build_lock_held(index_dir: Path) -> "tuple[Optional[bool], Optional[int]]":
    """Non-destructively test whether the whole-index build lock is currently held.

    Returns ``(held, holder_pid)``. ``held`` is ``None`` when the state cannot be determined (probe
    error / unknown platform) — the acquire-time lock remains the ultimate authority, so status callers
    treat ``None`` as not-held. POSIX uses ``fcntl`` ``F_GETLK`` (queries without acquiring and returns
    the holder PID); native Windows uses a momentary non-blocking ``msvcrt`` lock on the sentinel byte
    (Windows has no F_GETLK; it also has no defunct-owner problem, so the microsecond acquire is safe)."""
    lock_path = index_dir / INDEX_BUILD_LOCK_NAME
    if not lock_path.exists():
        return (False, None)
    try:
        if os.name == "nt":
            import msvcrt
            with open(lock_path, "r+b") as fh:
                fh.seek(INDEX_BUILD_LOCK_SENTINEL)
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    return (True, None)  # could not lock -> a builder holds it
                fh.seek(INDEX_BUILD_LOCK_SENTINEL)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)  # got it -> not held; release at once
                return (False, None)
        import fcntl
        import struct as _struct
        plat = "darwin" if sys.platform == "darwin" else ("linux" if sys.platform.startswith("linux") else None)
        if plat is None:
            return (None, None)  # unknown flock struct layout — undetermined
        fmt, fields = _FLOCK_STRUCT[plat]
        vals = {"l_type": fcntl.F_WRLCK, "l_whence": 0, "l_start": INDEX_BUILD_LOCK_SENTINEL, "l_len": 1, "l_pid": 0}
        packed = _struct.pack(fmt, *(vals[name] for name in fields))
        fd = os.open(str(lock_path), os.O_RDONLY)
        try:
            res = fcntl.fcntl(fd, fcntl.F_GETLK, packed)
        finally:
            os.close(fd)
        out = dict(zip(fields, _struct.unpack(fmt, res)))
        if out["l_type"] == fcntl.F_UNLCK:
            return (False, None)  # no conflicting lock -> not held
        return (True, out["l_pid"] or None)
    except Exception:  # noqa: BLE001 — probe failure -> undetermined; acquire-time lock is the authority
        return (None, None)


@contextmanager
def _index_build_lock(index_dir: Path):
    """Acquire the whole-index build lock for ``index_dir``.

    The file is metadata only; the OS-held lock is the authority. Keeping the
    file in place lets status tools inspect the last owner without making
    cleanup correctness depend on unlinking after a crash.
    """
    lock_path = index_dir / INDEX_BUILD_LOCK_NAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    prior_owner = classify_index_build_lock_owner(read_index_build_lock_metadata(lock_path))
    # Wave 1p2q3 (1p2w5): proactively unlink lock-file metadata that records a
    # dead PID. The OS-held `flock()` is released when its holding process
    # exits, so a fresh acquire below will succeed regardless — but leaving
    # the stale metadata on disk causes downstream tools that read it (status
    # surfaces, diagnostic messages) to keep surfacing the dead PID. Unlink
    # races are safe: POSIX `unlink` does not affect file descriptors already
    # open in other processes, and concurrent unlink callers see
    # FileNotFoundError which we ignore.
    if prior_owner == "stale" and lock_path.exists():
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            # Permission or filesystem issue — fall through and let the
            # `open()` below surface the underlying error.
            pass
    fh = lock_path.open("a+", encoding="utf-8")
    acquired = False
    lock_meta: Optional[dict] = None
    try:
        if os.name == "nt":
            import msvcrt
            try:
                fh.seek(INDEX_BUILD_LOCK_SENTINEL)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                acquired = True
            except OSError as exc:
                raise IndexBuildAlreadyRunning(
                    format_index_build_lock_conflict(index_dir, lock_path=lock_path)
                ) from exc
        else:
            import fcntl
            try:
                # Wave 1p99o: a fcntl record lock on the sentinel byte (was `flock`) — so status can
                # probe it non-destructively via F_GETLK, and it is not fork-inherited (a pool worker
                # can't hold it out from under a finished parent).
                fcntl.lockf(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB, 1, INDEX_BUILD_LOCK_SENTINEL, 0)
                acquired = True
            except OSError as exc:  # BlockingIOError (EAGAIN/EACCES) when another builder holds it
                raise IndexBuildAlreadyRunning(
                    format_index_build_lock_conflict(index_dir, lock_path=lock_path)
                ) from exc

        if prior_owner == "stale":
            print(
                f"build_index: reclaimed stale {INDEX_BUILD_LOCK_NAME} at {lock_path}",
                file=sys.stderr,
            )
        # Wave 1p98u/1p99o: metadata lives at byte 0 (off the sentinel lock byte) so it stays readable
        # while the lock is held. `ended_at` is added best-effort in `finally` on clean exit — its
        # absence (with the lock not held) is how status detects an interrupted build.
        lock_meta = {
            "pid": os.getpid(),
            "started_at": time.time(),
            "cmdline": " ".join(sys.argv),
        }
        fh.seek(0)
        fh.truncate()
        fh.write(json.dumps(lock_meta))
        fh.flush()
        yield
    finally:
        if acquired:
            if lock_meta is not None:
                try:  # best-effort ended_at; a hard kill skips it → status sees an interrupted build
                    lock_meta["ended_at"] = time.time()
                    fh.seek(0)
                    fh.truncate()
                    fh.write(json.dumps(lock_meta))
                    fh.flush()
                except Exception:  # noqa: BLE001
                    pass
            try:
                if os.name == "nt":
                    import msvcrt
                    fh.seek(INDEX_BUILD_LOCK_SENTINEL)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.lockf(fh.fileno(), fcntl.LOCK_UN, 1, INDEX_BUILD_LOCK_SENTINEL, 0)
            except OSError:
                pass
        fh.close()


@contextmanager
def _table_lock(table_dir: Path, *, create_dir: bool = False):
    """Acquire a per-table build lock at ``table_dir/.lock``.

    ``table_dir`` is the Lance table directory (e.g. ``index_dir/docs.lance``).
    Set ``create_dir=True`` for the full-rebuild path where the directory may not
    exist yet.  The incremental path should leave it False so that the caller's
    "table absent" guard still fires when the Lance dir is missing.

    The lock file contains the owning process PID; its mtime is used by server.py
    to detect stale locks older than LOCK_STALE_SECONDS.  Using ``O_CREAT | O_EXCL``
    provides the same atomic-create guarantee as ``mkdir()`` on POSIX.
    Readers see ``docs.lance/.lock`` only while their specific table is being
    written — the other table remains unlocked and fully readable.
    """
    if create_dir:
        table_dir.mkdir(parents=True, exist_ok=True)
    lock_path = table_dir / TABLE_LOCK_NAME
    # If the table directory doesn't exist and create_dir wasn't requested, skip locking —
    # the caller's "table absent" guard will handle this case.
    if not table_dir.exists():
        yield
        return
    acquired = False
    while not acquired:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode())
            finally:
                os.close(fd)
            acquired = True
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
            except OSError:
                age = 0
            if age > LOCK_STALE_SECONDS:
                lock_path.unlink(missing_ok=True)
                continue
            time.sleep(0.2)
    try:
        yield
    finally:
        lock_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _onnx_providers() -> list[str]:
    """Return the best available ONNX Runtime execution providers for this machine."""
    if provider_policy is None:
        return ["CPUExecutionProvider"]
    decision = provider_policy.select_embedding_providers()
    return list(decision.providers)


def _precision_class_from_version(value: Optional[str]) -> str:
    """Parse the precision class suffix from a recorded ``model_versions`` value (wave 1p936):
    ``"name@class"`` -> ``class``. A legacy bare model-name value (no ``"@"``) -> ``"full"``
    (indexes built before this wave predate the precision split and are full-precision)."""
    if not value or "@" not in value:
        return "full"
    return value.rsplit("@", 1)[1]


def _predicted_precision_class(model_name: str, providers: list[str]) -> str:
    """The precision class the embedder pipeline resolves for ``model_name`` on the CURRENT machine
    (wave 1p936). Provider AVAILABILITY only, no ONNX session build — a full resolve-and-probe here
    would defeat the 1p5d6/1p938 lazy-load optimizations by forcing a ~40s CoreML compile on every
    incremental build just to check precision.

    Both the ``model_versions`` COMPARE site (has the class changed → re-embed?) and the WRITE site
    (record the class) call THIS function, so they are consistent by construction — critical, or a
    same-machine incremental build would perpetually re-embed. ``make_embedder`` is built to resolve
    exactly what this reports, so the recorded class stays truthful about the stored vectors:

    - GPU available -> ``"full"``. A GPU machine runs FP16 end-to-end (ADR 1p92d); a model whose
      graph doesn't offload falls back to fastembed FULL (``make_embedder`` returns None → caller's
      fastembed path), NOT INT8 — so "GPU available" always means "full" here.
    - no GPU + this model has an INT8 clean-export source -> ``"int8"`` (the CPU-bound pipeline).
    - otherwise (no GPU, no INT8 source) -> ``"full"`` (fastembed-resident).

    Note FP16 and FP32 both collapse to ``"full"`` (cos 1.0, interchangeable per 1p517 AC-8); only
    INT8 actually shifts vectors, so it is the only distinct class."""
    if accel_embedder is None:
        return "full"
    provider_list = list(providers)
    gpu = [p for p in provider_list if p in accel_embedder.GPU_PROVIDERS]
    if not gpu:
        gpu = accel_embedder._available_gpu_providers()
    if gpu:
        return "full"
    if model_name in accel_embedder.CLEAN_ONNX_SOURCES:
        return "int8"
    return "full"


_EMBEDDER_CACHE: dict[str, Any] = {}

# Wave 1p938: route an incremental embed run smaller than one full GPU batch to the full-precision
# CPU fastembed path instead of constructing the 64x512 GPU accel session — the GPU only amortizes
# its fixed dispatch cost over a large batch (measurement B, ADR 1p92d); a handful of chunks padded
# into a 64-row batch loses to plain CPU. Default = accel_embedder.STATIC_BATCH (one full GPU
# batch), so a bulk/full build (>= threshold chunks) still uses GPU unchanged (AC-2).
INCREMENTAL_GPU_MIN_CHUNKS = accel_embedder.STATIC_BATCH if accel_embedder is not None else 64


def _get_embedder(model_name: str, n_chunks: Optional[int] = None):
    """Return an embedder (accel GPU/CPU-INT8, or fastembed) for model_name.

    Wave 1p4wy: cached per process so the ONNX/CoreML session (and its ~40s compile
    on the GPU path) is built once, not re-created if the same model is requested
    again within a build.

    Wave 1p938: when ``n_chunks`` is given, below ``INCREMENTAL_GPU_MIN_CHUNKS``, AND this machine
    would otherwise use GPU acceleration, route straight to the full-precision fastembed-resident
    path instead of the GPU accel session — see the module-level constant's docstring for why. Does
    NOT affect a CPU-bound machine (no GPU to skip in the first place; AC-3) — that machine's normal
    dispatch already correctly resolves the INT8-CPU accel embedder (wave 1p935) regardless of run
    size. Precision-safe on a GPU machine: this is the SAME full-precision embedder the GPU machine
    already falls back to when accel is unavailable for any other reason — cos 1.0 with the FP16
    index, a "full"-class no-op under wave 1p936's re-embed guard. Cached under a distinct key so a
    later bulk/full run in the same process still resolves (and caches) the real GPU embedder.
    """
    providers = _onnx_providers()
    has_gpu = accel_embedder is not None and (
        any(p in accel_embedder.GPU_PROVIDERS for p in providers) or accel_embedder._available_gpu_providers()
    )
    small_run = has_gpu and n_chunks is not None and n_chunks < INCREMENTAL_GPU_MIN_CHUNKS
    cache_key = f"{model_name}::small_run_cpu" if small_run else model_name
    cached = _EMBEDDER_CACHE.get(cache_key)
    if cached is not None:
        return cached
    # Wave 1p517: when a GPU provider is selected, use the static-shape ONNX embedder
    # (CoreML/CUDA) if this model's graph actually runs on the GPU; else fall back to fastembed.
    # Wave 1p935: make_embedder also tries a static-shape CPU-INT8 path before giving up to
    # fastembed, so `accel` here may be either a GPU-FP16 or a CPU-INT8 StaticShapeEmbedder.
    # The accel path resolves its model files cached-first internally (see accel_embedder).
    if accel_embedder is not None and not small_run:
        try:
            accel = accel_embedder.make_embedder(model_name, providers)
        except Exception:
            accel = None
        if accel is not None:
            provider = getattr(accel, "provider", "?")
            kind = "CPU-INT8" if provider == "CPUExecutionProvider" else "GPU-accelerated"
            print(f"build_index: using {kind} embedder for {model_name} "
                  f"({provider}, static {accel_embedder.STATIC_BATCH}x"
                  f"{accel_embedder.STATIC_SEQ})", flush=True)
            _EMBEDDER_CACHE[cache_key] = accel
            return accel
    try:
        from fastembed import TextEmbedding
    except ImportError:
        print(
            "build_index: fastembed is not installed.\n"
            "  Run: python3 .wavefoundry/framework/scripts/setup_index.py",
            file=sys.stderr,
        )
        sys.exit(1)
    if small_run:
        print(f"build_index: {n_chunks} chunk(s) on a GPU machine — below the batch threshold "
              f"({INCREMENTAL_GPU_MIN_CHUNKS}), using the CPU embedder for {model_name} "
              "(skips the GPU accel session for this small run)", flush=True)
    embedder = _text_embedding_cached_first(TextEmbedding, model_name, providers)
    _EMBEDDER_CACHE[cache_key] = embedder
    return embedder


def _text_embedding_cached_first(text_embedding_cls, model_name: str, providers):
    """Construct a fastembed ``TextEmbedding`` from the local cache first (``local_files_only=True``),
    downloading only on a genuine cache miss.

    Wave 1p5cx: ``setup_index`` already provisions the models, so the reindex path should load them
    with no network — a plain construct makes a Hub round-trip on every build (the per-process
    ``unauthenticated requests to the HF Hub`` warning + latency). ``local_files_only=True`` returns
    the cached model with no request; only if it isn't cached do we fall back to an online download
    (which then caches it). Vectors are identical either way — no parity impact. This mirrors the
    cached-first download in ``accel_embedder`` so both the GPU and CPU embedder paths stay offline
    on a warm cache.

    Wave 1p939 (delivery-phase fix): this is the embedder-construction fallback reached whenever
    ``accel_embedder.make_embedder()`` returns ``None`` (no GPU/CoreML/CUDA/ROCm/DML offload — the
    common case on CPU-only/Linux/WSL2/CI hosts, and the fallback even on GPU-capable hosts). It was
    a fourth raw model-download call site missed by this wave's original literal ``TextEmbedding(``
    token sweep (the constructor here is invoked via the ``text_embedding_cls`` parameter, not the
    literal token) — and it is the path every named launcher (MCP ``wave_index_build``, the dashboard
    watcher, background refresh) actually hits on that hardware class. It now applies the same CA
    ladder the GPU-path call sites use before the online attempt."""
    try:
        return text_embedding_cls(model_name=model_name, providers=providers, local_files_only=True)
    except Exception:
        pass
    import setup_index
    setup_index.ensure_ca_bundle_applied()
    return setup_index.retry_with_ca_bundle_ladder(
        lambda: text_embedding_cls(model_name=model_name, providers=providers), model_name,
    )


def _embed_texts(embedder, texts: list[str], batch_size: int = 256) -> "np.ndarray":
    """Embed a list of texts and return as a float32 numpy array (n, dim).

    Callers are responsible for pre-sorting inputs by text length for padding
    efficiency (ONNX pads every sequence in a batch to the longest). The full
    rebuild path uses a sliding sort buffer; the incremental path sorts per-file.
    """
    import numpy as _np
    return _np.array(
        list(embedder.embed(texts, batch_size=batch_size)),
        dtype=_np.float32,
    )


def _progress(verbose: bool, message: str) -> None:
    if verbose:
        print(message, flush=True)


# ---------------------------------------------------------------------------
# Index build helpers
# ---------------------------------------------------------------------------

def _is_docs_kind(kind: str) -> bool:
    return kind in ("doc", "seed", "prompt", "doc-summary")


# We cache the chunker module after first load
_chunker_mod = None
_graph_indexer_mod = None
_graph_cluster_mod = None
_secrets_scanner_mod = None

def _get_chunker():
    global _chunker_mod
    if _chunker_mod is None:
        import importlib.util
        chunker_path = Path(__file__).resolve().parent / "chunker.py"
        spec = importlib.util.spec_from_file_location("chunker", chunker_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["chunker"] = mod
        spec.loader.exec_module(mod)
        _chunker_mod = mod
    return _chunker_mod


def _get_graph_indexer():
    global _graph_indexer_mod
    if _graph_indexer_mod is None:
        import importlib.util
        graph_indexer_path = Path(__file__).resolve().parent / "graph_indexer.py"
        spec = importlib.util.spec_from_file_location("graph_indexer", graph_indexer_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["graph_indexer"] = mod
        spec.loader.exec_module(mod)
        _graph_indexer_mod = mod
    return _graph_indexer_mod


def _get_graph_cluster():
    global _graph_cluster_mod
    if _graph_cluster_mod is None:
        import importlib.util
        graph_cluster_path = Path(__file__).resolve().parent / "graph_cluster.py"
        spec = importlib.util.spec_from_file_location("graph_cluster", graph_cluster_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["graph_cluster"] = mod
        spec.loader.exec_module(mod)
        _graph_cluster_mod = mod
    return _graph_cluster_mod


def _get_secrets_scanner():
    global _secrets_scanner_mod
    if _secrets_scanner_mod is None:
        import importlib.util
        scan_secrets_path = Path(__file__).resolve().parent / "scan_secrets.py"
        if not scan_secrets_path.exists():
            return None
        spec = importlib.util.spec_from_file_location("scan_secrets", scan_secrets_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["scan_secrets"] = mod
        spec.loader.exec_module(mod)
        _secrets_scanner_mod = mod
    return _secrets_scanner_mod


def _build_graph_artifacts(
    *,
    root: Path,
    index_dir: Path,
    layer: str,
    files: list[Path],
    current_file_meta: dict[str, dict[str, Any]],
    changed: set[str],
    removed: set[str],
    walker_version: str,
    chunker_version: str,
    verbose: bool = False,
) -> dict[str, Any]:
    graph_indexer = _get_graph_indexer()
    graph_cluster = _get_graph_cluster()
    _t0 = time.monotonic()
    if verbose:
        print(f"build_index: graph extraction starting ({layer} layer)", flush=True)
    graph_payload = graph_indexer.update_graph_index(
        root=root,
        index_dir=index_dir,
        layer=layer,
        files=files,
        current_file_meta=current_file_meta,
        changed=changed,
        removed=removed,
        walker_version=walker_version,
        chunker_version=chunker_version,
        verbose=verbose,
    )
    if verbose:
        counts = graph_payload.get("counts") or {}
        print(
            f"build_index: graph extraction complete ({layer} layer) — "
            f"{counts.get('nodes', 0)} nodes, {counts.get('edges', 0)} edges",
            flush=True,
        )
        print(f"build_index: graph clustering starting ({layer} layer)", flush=True)
    # Wave 1p9q3 (1p9q2): transient per-build merge stats attached by finalize
    # AFTER the payload write (returned to the caller, never persisted). Pop
    # before the cluster pass so downstream consumers see the pure payload.
    merge_stats = graph_payload.pop("merge_stats", None) if isinstance(graph_payload, dict) else None
    cluster_payload = graph_cluster.update_graph_clusters(
        root=root,
        index_dir=index_dir,
        layer=layer,
        graph_payload=graph_payload,
        verbose=verbose,
    )
    if verbose:
        print(
            f"build_index: graph phase complete ({layer} layer) — "
            f"{cluster_payload.get('community_count', 0)} communities via "
            f"{cluster_payload.get('cluster_algorithm') or 'unknown'}",
            flush=True,
        )
    elapsed = time.monotonic() - _t0
    counts = graph_payload.get("counts") or {}
    # Wave 1p9io: route to stderr — this progress line is unconditional (not verbose-gated) and
    # build_index runs IN-PROCESS from graph_query._ensure_graph_builder_current on the first graph
    # query after a builder-version bump, where sys.stdout IS the MCP JSON-RPC channel. stdout would
    # corrupt the protocol frame; stderr (fd 2) is left alone by the server's stdout isolation and
    # still reaches the terminal during a CLI build.
    # Wave 1p9q3 (1p9q2): merge-phase timing + delta sizes so field reports can
    # distinguish extraction cost from merge cost (Req-9).
    merge_suffix = ""
    if isinstance(merge_stats, dict):
        merge_suffix = (
            f" | merge[{merge_stats.get('mode', 'unknown')}]: "
            f"{(merge_stats.get('merge_ms') or 0) / 1000:.1f}s"
            f" | delta: files={merge_stats.get('files_changed', 0)}"
            f" removed={merge_stats.get('files_removed', 0)}"
            f" symbols={merge_stats.get('symbols_invalidated', 0)}"
            f" edges_reresolved={merge_stats.get('edges_reresolved', 0)}"
            f" | state io: reads={merge_stats.get('state_reads', 0)}"
            f" writes={merge_stats.get('state_writes', 0)}"
            f" | sidecar: reads={merge_stats.get('blob_reads', 0)}"
            f" writes={merge_stats.get('blob_writes', 0)}"
            f" bytes={merge_stats.get('blob_bytes', 0)}"
        )
    print(
        f"build_index: finished graph: {len(changed)} changed, {len(removed)} removed"
        f" | nodes: {counts.get('nodes', 0)} | edges: {counts.get('edges', 0)}"
        f"{merge_suffix}"
        f" in {elapsed:.1f}s",
        file=sys.stderr,
        flush=True,
    )
    return {"graph_payload": graph_payload, "cluster_payload": cluster_payload}


def _build_secrets_artifacts(
    *,
    root: Path,
    index_dir: Path,
    changed: set[str],
    removed: set[str],
    full: bool = False,
    verbose: bool = False,
) -> dict:
    scanner = _get_secrets_scanner()
    if scanner is None:
        return {}
    scan_dir = index_dir / "scan"
    try:
        return scanner.update_secrets_scan(
            root=root,
            scan_dir=scan_dir,
            changed=changed,
            removed=removed,
            full=full,
            verbose=verbose,
        )
    except Exception as exc:
        print(f"build_index: secrets scan failed: {exc}", file=sys.stderr)
        return {"error": str(exc)}


def _chunks_for_file(rel_path: str, content: str) -> tuple[list[dict], list[dict]]:
    chunker = _get_chunker()
    raw = chunker.chunk_file(content, rel_path)
    doc_chunks = [c.to_dict() for c in raw if _is_docs_kind(c.kind)]
    code_chunks = [c.to_dict() for c in raw if not _is_docs_kind(c.kind)]
    return doc_chunks, code_chunks


def _graph_layer_for_index_dir(index_dir: Path) -> str:
    # Wave 1p4ww: single project graph — the framework graph layer was removed,
    # so every index build extracts into the one project graph.
    return "project"


# ---------------------------------------------------------------------------
# Core build logic
# ---------------------------------------------------------------------------

def build_index(
    root: Path,
    *,
    full: bool = False,
    rechunk: bool = False,
    content: str = "docs",
    index_dir: Optional[Path] = None,
    include_prefixes: tuple[str, ...] = (),
    respect_ignore: bool = True,
    include_tests: bool = False,
    include_generated: bool = False,
    project_include_prefixes: tuple[str, ...] = (),
    files: Optional[list[Path]] = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> dict:
    index_dir = index_dir or (root / INDEX_DIR_NAME)
    if not index_dir.is_absolute():
        index_dir = root / index_dir
    index_dir.mkdir(parents=True, exist_ok=True)
    # Wave 1p5c4: publish the tree-sitter parse cap so the chunker and graph extractor (in-process
    # or subprocess) skip the AST on oversized files. Resolved from indexing.max_treesitter_parse_bytes.
    os.environ["WAVEFOUNDRY_MAX_TS_PARSE_BYTES"] = str(_resolve_index_size_limits(root)[1])
    if dry_run:
        return _build_index_locked(
            root,
            full=full,
            rechunk=rechunk,
            content=content,
            index_dir=index_dir,
            include_prefixes=include_prefixes,
            respect_ignore=respect_ignore,
            include_tests=include_tests,
            include_generated=include_generated,
            project_include_prefixes=project_include_prefixes,
            files=files,
            verbose=verbose,
            dry_run=True,
        )
    with _index_build_lock(index_dir):
        return _build_index_locked(
            root,
            full=full,
            rechunk=rechunk,
            content=content,
            index_dir=index_dir,
            include_prefixes=include_prefixes,
            respect_ignore=respect_ignore,
            include_tests=include_tests,
            include_generated=include_generated,
            project_include_prefixes=project_include_prefixes,
            files=files,
            verbose=verbose,
            dry_run=dry_run,
        )


def _build_index_locked(
    root: Path,
    *,
    full: bool = False,
    rechunk: bool = False,
    content: str = "docs",
    index_dir: Optional[Path] = None,
    include_prefixes: tuple[str, ...] = (),
    respect_ignore: bool = True,
    include_tests: bool = False,
    include_generated: bool = False,
    project_include_prefixes: tuple[str, ...] = (),
    files: Optional[list[Path]] = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> dict:
    """Build or incrementally update the index at root/.wavefoundry/index/.

    Returns a summary dict with counts.
    """
    try:
        import numpy as np
    except ImportError:
        print(
            "build_index: numpy is not installed.\n"
            "  Run: python3 .wavefoundry/framework/scripts/setup_index.py",
            file=sys.stderr,
        )
        sys.exit(1)

    if content not in CONTENT_CHOICES:
        raise ValueError(f"content must be one of: {', '.join(CONTENT_CHOICES)}")

    build_docs = content in ("docs", "all")
    build_code = content in ("code", "all")
    # Graph-only runs always load existing meta so docs/code chunker_versions,
    # model_versions, and content fields are preserved across graph rebuilds.
    meta = _load_meta(index_dir) if content == "graph" else ({} if full else _load_meta(index_dir))
    old_file_meta: dict[str, dict] = meta.get("file_meta", {})
    old_model_versions: dict[str, str] = meta.get("model_versions", {})
    # chunker_versions tracks per-content-layer chunker version so that a
    # docs-only update does not falsely stamp the code layer as current.
    old_chunker_versions: dict[str, str] = meta.get("chunker_versions", {})
    # Legacy: scalar chunker_version written by older builds — treat as applying
    # to both layers if the new per-layer key is absent.
    _legacy_cv: str = meta.get("chunker_version", "")
    if not old_chunker_versions and _legacy_cv:
        old_chunker_versions = {"docs": _legacy_cv, "code": _legacy_cv}
    current_chunker_version: str = getattr(_get_chunker(), "CHUNKER_VERSION", "")
    # walker_version is a scalar (walk_repo applies to all layers equally).
    # Absent key means a legacy index built before walker versioning — treat as mismatch.
    old_walker_version: str = meta.get("walker_version", "")

    # Force a selected-content rebuild if models changed, chunker changed for
    # this content layer, walker filter changed, or selected index files are absent.
    model_changed = False
    chunker_changed = False
    walker_changed = old_walker_version != WALKER_VERSION
    # meta["content"] records which layers were built last time (even if 0 chunks were produced).
    previously_built_content = set(meta.get("content", []))
    if build_docs:
        old_docs_value = old_model_versions.get("docs")
        model_changed = model_changed or (old_docs_value or "").split("@", 1)[0] != DOCS_MODEL
        # Wave 1p936: a precision-class change (full <-> int8) also forces a full re-embed — old
        # vectors are only interchangeable within the same class (FP16/FP32 collapse to "full").
        model_changed = model_changed or _precision_class_from_version(old_docs_value) != (
            _predicted_precision_class(DOCS_MODEL, _onnx_providers())
        )
        docs_index_exists = (
            (index_dir / "docs.lance").is_dir()
            or "docs" in previously_built_content
        )
        model_changed = model_changed or not docs_index_exists
        chunker_changed = chunker_changed or (
            current_chunker_version and old_chunker_versions.get("docs") != current_chunker_version
        )
    if build_code:
        old_code_value = old_model_versions.get("code")
        model_changed = model_changed or (old_code_value or "").split("@", 1)[0] != CODE_MODEL
        model_changed = model_changed or _precision_class_from_version(old_code_value) != (
            _predicted_precision_class(CODE_MODEL, _onnx_providers())
        )
        code_index_exists = (
            (index_dir / "code.lance").is_dir()
            or "code" in previously_built_content
        )
        model_changed = model_changed or not code_index_exists
        chunker_changed = chunker_changed or (
            current_chunker_version and old_chunker_versions.get("code") != current_chunker_version
        )
    # Wave 1p4n4: a CHUNKER-only version bump (model + walker unchanged) changes chunk
    # SHAPE, not the embedding MODEL — content-identical chunks keep valid vectors. Re-chunk
    # every file but reuse embeddings by content hash (the delta-write path) so only new/
    # changed chunks re-embed, instead of a full from-scratch re-encode. A model/walker change
    # (or an explicit --full) still rebuilds fully (old-model vectors are invalid).
    rechunk_all = False
    # Wave 1p4n4 (mode='rechunk'): an EXPLICIT operator rechunk request forces the re-chunk-all +
    # embedding-reuse path WITHOUT a version change — re-materialize chunks after a chunker-LOGIC
    # change that wasn't version-bumped (or to recover a same-version shape drift). Model/walker
    # changes still override to a full re-embed (old vectors are invalid under a new model).
    rechunk_requested = rechunk and not full and not model_changed and not walker_changed
    if model_changed or chunker_changed or walker_changed or rechunk_requested:
        chunker_only = chunker_changed and not model_changed and not walker_changed
        if not full and (chunker_only or rechunk_requested) and old_chunker_versions:
            _why = "chunker version changed" if chunker_only else "explicit rechunk requested"
            print(
                f"build_index: selected {content} index — {_why} "
                f"(chunker {old_chunker_versions.get('code') or old_chunker_versions.get('docs')} → "
                f"{current_chunker_version}) — incremental re-chunk with embedding reuse "
                "(only new/changed chunks re-embed)",
                flush=True,
            )
            rechunk_all = True
        else:
            if not full and (old_model_versions or old_chunker_versions or old_walker_version):
                if walker_changed:
                    reason = "walker version changed" if old_walker_version else "walker version unknown (legacy index)"
                elif chunker_changed:
                    reason = "chunker version changed"
                else:
                    reason = "model version changed or index missing"
                print(
                    f"build_index: selected {content} index missing or {reason} — "
                    "performing full rebuild",
                    flush=True,
                )
            full = True
            old_file_meta = {}

    if files is None:
        # Walk repo
        files = walk_repo(root, respect_ignore=respect_ignore)
        files = [path for path in files if not _is_relative_to(path, index_dir)]
        files = _filter_by_prefixes(files, root, include_prefixes)
        if str(index_dir).replace("\\", "/").endswith("/.wavefoundry/framework/index"):
            files = _filter_framework_pack_artifacts(files, root)
        # files_for_meta must be stable across docs-run and code-run on the same layer
        # (otherwise consecutive runs alternately add/remove each other's files in
        # meta.json — the original 93-files-added / 93-files-removed cycle this block
        # was introduced to prevent).  For the project layer we still must keep
        # framework-prefixed files out of the project layer's meta.json — those belong
        # to the framework layer's meta — so we filter by the docs+code UNION from
        # workflow-config.json, not by the per-run content type's include set.
        graph_layer = _graph_layer_for_index_dir(index_dir)
        if graph_layer == "project":
            meta_project_includes = _project_meta_include_prefixes(root, project_include_prefixes)
            files_for_meta = _filter_project_index_excludes(
                files,
                root,
                include_prefixes,
                project_include_prefixes=meta_project_includes,
            )
        else:
            files_for_meta = files
        content_for_filter = "all" if build_docs and build_code else ("docs" if build_docs else "code")
        resolved_project_includes = _effective_project_include_prefixes(
            root, index_dir, content_for_filter, project_include_prefixes
        )
        files = _filter_project_index_excludes(
            files_for_meta,
            root,
            include_prefixes,
            project_include_prefixes=resolved_project_includes,
        )
        if graph_layer == "project":
            graph_includes = _merged_project_include_prefixes_for_graph(root, project_include_prefixes)
            files_for_graph = _filter_project_index_excludes(
                files_for_meta,
                root,
                include_prefixes,
                project_include_prefixes=graph_includes,
            )
        else:
            files_for_graph = files
    else:
        normalized_files: list[Path] = []
        seen: set[str] = set()
        for path in files:
            candidate = path if path.is_absolute() else root / path
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
            if not candidate.is_file():
                continue
            rel = str(candidate.relative_to(root)).replace("\\", "/")
            if rel in seen:
                continue
            seen.add(rel)
            normalized_files.append(candidate)
        files = sorted(normalized_files, key=lambda p: str(p.relative_to(root)).replace("\\", "/"))
        if str(index_dir).replace("\\", "/").endswith("/.wavefoundry/framework/index"):
            files = _filter_framework_pack_artifacts(files, root)
        graph_layer = _graph_layer_for_index_dir(index_dir)
        # Project-layer meta must not contain framework files even when files= is
        # passed in explicitly.  See the walk-branch comment above for the rationale.
        if graph_layer == "project":
            meta_project_includes = _project_meta_include_prefixes(root, project_include_prefixes)
            files_for_meta = _filter_project_index_excludes(
                files,
                root,
                include_prefixes,
                project_include_prefixes=meta_project_includes,
            )
        else:
            files_for_meta = files
        if graph_layer == "project":
            graph_includes = _merged_project_include_prefixes_for_graph(root, project_include_prefixes)
            files_for_graph = _filter_project_index_excludes(
                files_for_meta,
                root,
                include_prefixes,
                project_include_prefixes=graph_includes,
            )
        else:
            files_for_graph = files
    files_for_content = files
    if build_code and not build_docs:
        files_for_content = _filter_code_files(
            files,
            root,
            include_tests=include_tests,
            include_generated=include_generated,
        )
    # Hash the broad file set so meta.json captures every walkable file regardless
    # of which content type (docs/code/graph) this run is building.  Then scope
    # changed/removed/stale to the content-type-filtered walk so LanceDB operations
    # only touch chunks that belong to the current run's scope.
    if full:
        # Full rebuild: hash everything, populate stat cache for future incremental updates
        current_file_meta = {}
        for f in files_for_meta:
            rel = str(f.relative_to(root)).replace("\\", "/")
            mtime, size, inode = _stat_entry(f)
            digest = _sha256(f)
            current_file_meta[rel] = {"hash": digest, "mtime": mtime, "size": size, "inode": inode}
        changed_broad: set[str] = set(current_file_meta.keys())
        removed_broad: set[str] = set()
    else:
        # Incremental: use stat cache — only read files with changed mtime/size/inode
        current_file_meta, changed_broad, removed_broad = _detect_changes(files_for_meta, root, old_file_meta)
        # Wave 1p3b9 (1p399): drift detection. Cross-check `file_meta` against
        # Lance: paths claimed indexed in file_meta but with zero rows in any
        # Lance table are "drifted" — they need re-chunk + re-embed regardless
        # of hash match. The historic cause was the chunker mega-chunk bug
        # (closed by 1p397) that produced zero chunks for some files; the
        # incremental loop's skip-on-hash-match optimization perpetuated the
        # missing-rows state forever. This check makes incremental update
        # self-repairing for ANY future drift source.
        drifted = _detect_lance_drift(
            index_dir, current_file_meta, verbose=verbose,
        )
        if drifted:
            # Show the first few paths inline; cap at 5 in the diagnostic to
            # keep it scannable when drift is widespread.
            shown = sorted(drifted)[:5]
            extra = len(drifted) - len(shown)
            tail = f", +{extra} more" if extra > 0 else ""
            print(
                f"build_index: repairing {len(drifted)} drifted file(s): "
                f"{', '.join(shown)}{tail}",
                file=sys.stderr,
                flush=True,
            )
            # Add to the changed set so they get re-chunked even though their
            # file_meta hash still matches. The downstream rebuild path checks
            # `changed` (not `changed_broad` alone), but `changed_broad` is the
            # set that flows through to `changed` after the files_rel filter.
            # Drifted paths are by definition already in `current_file_meta`
            # (we got them from file_meta), so adding them to changed_broad
            # is sufficient.
            changed_broad |= drifted
    # Wave 1p4n4: chunker-only re-index — force every file to re-chunk so the new chunk
    # SHAPE is produced. They are all already in old_file_meta, so they flow through below as
    # `updated` (not `added`) → existing Lance rows are fetched and the delta planner reuses
    # vectors for content-unchanged chunks; only genuinely new/changed chunks re-embed.
    if rechunk_all:
        changed_broad |= set(current_file_meta.keys())
    # changed: scope to the content-type-filtered walk — don't re-embed files that
    # are outside this run's scope (e.g. framework scripts for a docs-only run).
    # removed: use the broad result directly — a file absent from files_for_meta is
    # truly deleted from disk (not merely filtered out), so its chunks must be evicted
    # regardless of which content type's run discovers the deletion.
    files_rel = {str(f.relative_to(root)).replace("\\", "/") for f in files}
    changed = changed_broad & files_rel
    files_for_graph_rel = {str(f.relative_to(root)).replace("\\", "/") for f in files_for_graph}
    changed_for_graph = changed_broad & files_for_graph_rel
    removed = removed_broad
    added = changed - set(old_file_meta.keys()) if not full else changed
    updated = changed & set(old_file_meta.keys()) if not full else set()
    stale = changed | removed

    if not full and not stale:
        # Even when no files changed, LanceDB rows for paths now excluded by
        # workflow-config narrowing must still be reaped — meta.json drift is
        # invisible to ``stale`` once a prior build dropped those paths from
        # ``old_file_meta``. Reaping here ensures post-edit-hook triggers
        # (which fire incrementals with zero changes) still close the orphan
        # gap on the typical hot path.
        #
        # Reap both tables regardless of ``content`` arg: a docs-only update
        # must still reap code-table orphans (and vice versa), otherwise the
        # bug recurs whenever a docs-only incremental fires while the code
        # table has accumulated stranded rows. ``current_file_meta`` is the
        # union of all eligible paths for this layer, so checking both
        # tables against it is correct.
        reap_idle = _reap_stranded_lance_rows(
            index_dir,
            set(current_file_meta.keys()),
            tables=("docs", "code"),
            verbose=verbose,
        )
        if verbose:
            print("build_index: index is up to date", flush=True)
        return {
            "files_indexed": 0,
            "files_total": len(files),
            "up_to_date": True,
            "stranded_rows_reaped": reap_idle.get("total", 0),
            "stranded_rows_reaped_by_table": reap_idle,
        }

    if dry_run:
        scope = "full" if full else f"{len(changed)} changed, {len(removed)} removed"
        print(f"build_index: dry-run — rebuild needed ({scope})", flush=True)
        return {
            "files_indexed": 0,
            "files_total": len(files),
            "up_to_date": False,
            "dry_run": True,
            "stranded_rows_reaped": 0,
            "stranded_rows_reaped_by_table": {"docs": 0, "code": 0, "total": 0},
        }

    _index_label = {"docs": "docs/seed", "code": "code", "all": "docs/seed + code"}.get(content, content)
    # Wave 1p9io: route these unconditional (not verbose-gated) top-level progress lines to stderr.
    # build_index runs in-process from the MCP server's graph auto-rebuild path (full=True) where
    # sys.stdout is the JSON-RPC channel; stderr is safe there and still visible in a CLI build.
    if full:
        print(
            f"build_index: rebuilding {_index_label} index — {len(files_for_content)} source files\n"
            "  This may take several minutes to complete.",
            file=sys.stderr,
            flush=True,
        )
    else:
        print(
            f"build_index: updating {_index_label} index — "
            f"{len(changed)} file(s) changed, {len(removed)} removed",
            file=sys.stderr,
            flush=True,
        )
    if verbose:
        if content == "graph":
            print("build_index: graph-only mode — skipping semantic embedding", flush=True)
        elif not build_code:
            print("build_index: semantic code embedding disabled (use setup_index.py --include-code to enable)", flush=True)
        elif build_code and not build_docs:
            skipped = len(files) - len(files_for_content)
            if skipped:
                print(
                    f"build_index: skipped {skipped} non-source/test/generated files "
                    "(use --include-tests or --include-generated to include them)",
                    flush=True,
                )

    # If no Lance tables exist yet (first build or upgrade from legacy), force a full rebuild
    # so tables are created from the complete corpus.
    if not full:
        has_lance = (index_dir / "docs.lance").is_dir() or (index_dir / "code.lance").is_dir()
        if not has_lance:
            print(
                "build_index: no LanceDB tables found — full rebuild to create index",
                flush=True,
            )
            full = True
            current_file_meta = {}
            for f in files_for_meta:
                rel = str(f.relative_to(root)).replace("\\", "/")
                mtime, size, inode = _stat_entry(f)
                digest = _sha256(f)
                current_file_meta[rel] = {"hash": digest, "mtime": mtime, "size": size, "inode": inode}
            changed = files_rel & set(current_file_meta.keys())
            removed = set()
            stale = changed

    # Chunk new/changed files
    new_doc_chunks: list[dict] = []
    new_code_chunks: list[dict] = []
    files_to_index = [
        f for f in files_for_content
        if str(f.relative_to(root)).replace("\\", "/") in changed
    ] if not full else files_for_content

    # Wave 1p3iw: record chunks_emitted per file so the NEXT incremental
    # update's drift check can skip files that legitimately produce zero
    # chunks. Missing field on a file_meta entry → unknown, included in
    # drift check (one-shot repair learns the count); explicit 0 → skipped.
    chunks_emitted_by_file: dict[str, int] = {}
    # Wave 1p5ch: the FULL rebuild streams (chunk → buffer → embed → append) via
    # _run_streaming_full_rebuild below, so it does NOT pre-accumulate the whole chunk list here —
    # it chunks files and records chunks_emitted_by_file during the write, bounding memory. The
    # incremental path still materializes the changed files' chunks (it reuses vectors by content
    # hash and writes per-path).
    if not full:
        for file_path in files_to_index:
            rel = str(file_path.relative_to(root)).replace("\\", "/")
            try:
                source_text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            dc, cc = _chunks_for_file(rel, source_text)
            chunks_emitted_by_file[rel] = len(dc) + len(cc)
            if build_docs:
                new_doc_chunks.extend(dc)
            if build_code:
                new_code_chunks.extend(cc)

    # Wave 1p5ch: chunks_emitted_by_file is persisted into current_file_meta AFTER the write block
    # (below) — the full rebuild only populates it during the streaming write, so persistence must
    # wait until that has run (the incremental path populated it in the loop above).

    # Embed new chunks
    if full:
        _progress(verbose, f"build_index: streaming {len(files_to_index)} files into the docs/code index")
    else:
        _progress(
            verbose,
            f"build_index: chunked {len(files_to_index)} files "
            f"into {len(new_doc_chunks)} new doc chunks and {len(new_code_chunks)} new code chunks",
        )
    # Wave 1p5d6: load a layer's embedder only when it has embedding work — a full rebuild always
    # does, but an incremental update only needs the model for a layer with new/changed chunks. This
    # spares a docs-only edit the bge (code) CoreML session init (and vice versa). Safe because
    # `_lance_incremental_write` only touches the embedder when chunks are present (delete-only /
    # no-op writes never embed), so a layer with no new chunks correctly receives `None`.
    docs_embedder = None
    if build_docs and (full or new_doc_chunks):
        _progress(verbose, f"build_index: loading docs model {DOCS_MODEL}")
        # Wave 1p938: n_chunks lets _get_embedder route a SMALL INCREMENTAL run to CPU. It must be
        # None for a full rebuild: the streaming full-rebuild path produces chunks AFTER this load,
        # so new_doc_chunks is still empty here — passing len()==0 would wrongly route a bulk rebuild
        # of the entire corpus to the CPU fastembed path and defeat GPU acceleration. A full rebuild
        # is always a bulk run (→ GPU); the small-N optimization is only for the incremental
        # post-edit-hook path, where new_doc_chunks is already populated (the guard requires it).
        docs_embedder = _get_embedder(DOCS_MODEL, n_chunks=None if full else len(new_doc_chunks))
        _progress(verbose, f"build_index: loaded docs model {DOCS_MODEL}")
    code_embedder = None
    if build_code and (full or new_code_chunks):
        _progress(verbose, f"build_index: loading code model {CODE_MODEL}")
        code_embedder = _get_embedder(CODE_MODEL, n_chunks=None if full else len(new_code_chunks))
        _progress(verbose, f"build_index: loaded code model {CODE_MODEL}")

    # Write to LanceDB — the only index format.
    lance_db_path = index_dir

    # Compute chunk deltas before the write so we can count removed chunks.
    # added_files produced new chunks; updated_files replaced existing ones; removed files had theirs deleted.
    added_files_set = added if not full else set()
    updated_files_set = updated if not full else set()
    removed_files_set = removed if not full else set()
    doc_chunks_added = sum(1 for c in new_doc_chunks if c.get("path") in added_files_set)
    doc_chunks_updated_new = sum(1 for c in new_doc_chunks if c.get("path") in updated_files_set)
    code_chunks_added = sum(1 for c in new_code_chunks if c.get("path") in added_files_set)
    code_chunks_updated_new = sum(1 for c in new_code_chunks if c.get("path") in updated_files_set)
    if not full:
        doc_chunks_removed = _count_chunks_for_paths(lance_db_path, "docs", removed_files_set | updated_files_set) if build_docs else 0
        code_chunks_removed = _count_chunks_for_paths(lance_db_path, "code", removed_files_set | updated_files_set) if build_code else 0
        doc_chunks_updated_old = _count_chunks_for_paths(lance_db_path, "docs", updated_files_set) if build_docs else 0
        code_chunks_updated_old = _count_chunks_for_paths(lance_db_path, "code", updated_files_set) if build_code else 0
        # removed = old chunks for removed files; updated shows net change
        doc_chunks_removed_net = doc_chunks_removed - doc_chunks_updated_old
        code_chunks_removed_net = code_chunks_removed - code_chunks_updated_old
    else:
        doc_chunks_removed_net = 0
        code_chunks_removed_net = 0

    try:
        import numpy as _np
        graph_layer = _graph_layer_for_index_dir(index_dir)
        # Wave 1p2q3 (1p2wd post-ship 1.3.22 / Bug 4 part 2): graph extraction
        # runs on the main thread, NOT in the docs/code ThreadPoolExecutor.
        # A field session on 1.3.21 surfaced a deadlock: when
        # `_build_graph_artifacts` ran inside the threadpool's
        # `wavefoundry-index_0` worker thread, the graph layer's own
        # multi-process parallel extraction (`ProcessPoolExecutor` with spawn
        # start method) blocked indefinitely at `Process.start()`. macOS
        # Python 3.13 has a known hazard where `multiprocessing` spawn-mode
        # `Process.start()` from a non-main thread deadlocks on internal
        # signal-handler and pickle state. The graph layer already
        # parallelizes per-file extraction across multiple processes, so
        # threading the graph build added zero concurrency benefit anyway —
        # it just exposed the hazard. The docs/code writes stay in the
        # threadpool because they're I/O-bound on LanceDB and threads are
        # the correct tool for that workload.
        # Secrets scan runs as a threadpool future (project layer only).
        # CORRECTION (wave 1p8gu review MP-4): the secrets scanner DOES use a
        # ProcessPoolExecutor (spawn) internally when the changed-file set is
        # >= 50 files (wave_lint_lib/secrets_validators.check_hardcoded_secrets) —
        # the earlier "no ProcessPoolExecutor" claim here was wrong. That pool is
        # routed through subprocess_util.windowless_mp_context so its workers are
        # console-free on Windows (cross-ref MP-1), and it falls back to a serial
        # scan when a window-free context cannot be guaranteed.
        _run_secrets = graph_layer == "project"
        pool_workers = (1 if build_docs else 0) + (1 if build_code else 0) + (1 if _run_secrets else 0)
        _docs_elapsed: list[float] = []
        _code_elapsed: list[float] = []
        _secrets_elapsed: list[float] = []
        # pool_workers >= 1 whenever _run_secrets is True so ThreadPoolExecutor
        # is always constructed — nullcontext path only applies to graph-only
        # framework-layer runs where _run_secrets is False.
        if pool_workers > 0:
            _pool_cm = ThreadPoolExecutor(max_workers=pool_workers, thread_name_prefix="wavefoundry-index")
        else:
            import contextlib as _ctx_mod
            _pool_cm = _ctx_mod.nullcontext(None)
        with _pool_cm as executor:
            futures = []
            if verbose:
                layers = ", ".join(filter(None, [
                    "docs" if build_docs else "",
                    "code" if build_code else "",
                    "secrets" if _run_secrets else "",
                    "graph",
                ]))
                print(f"build_index: {layers} running concurrently ({graph_layer} layer)", flush=True)
            if full:
                # Wave 1p5ch: the full rebuild streams on the MAIN thread (see
                # _run_streaming_full_rebuild below, after the secrets future is submitted) so it
                # never materializes the whole chunk list. Nothing is submitted to the pool here;
                # the secrets scan still runs concurrently as its own future.
                pass
            else:
                if build_docs:
                    def _write_docs_incr(
                        _db_path=lance_db_path,
                        _stale=stale,
                        _doc_chunks=new_doc_chunks,
                        _docs_emb=docs_embedder,
                        _verbose=verbose,
                        _elapsed=_docs_elapsed,
                    ) -> None:
                        _t0 = time.monotonic()
                        _lance_incremental_write(_db_path, _stale, _doc_chunks, _docs_emb, [], None, True, False, _verbose)
                        _elapsed.append(time.monotonic() - _t0)
                    futures.append(executor.submit(_write_docs_incr))
                if build_code:
                    def _write_code_incr(
                        _db_path=lance_db_path,
                        _stale=stale,
                        _code_chunks=new_code_chunks,
                        _code_emb=code_embedder,
                        _verbose=verbose,
                        _elapsed=_code_elapsed,
                    ) -> None:
                        _t0 = time.monotonic()
                        _lance_incremental_write(_db_path, _stale, [], None, _code_chunks, _code_emb, False, True, _verbose)
                        _elapsed.append(time.monotonic() - _t0)
                    futures.append(executor.submit(_write_code_incr))
            # Secrets scan runs as a future (project layer) — concurrent with graph.
            # Uses ThreadPoolExecutor internally for file-read parallelism so it is
            # safe to submit from here (no ProcessPoolExecutor spawn inside).
            if _run_secrets:
                def _write_secrets(
                    _root=root,
                    _index_dir=index_dir,
                    _changed=changed_broad,
                    _removed=removed_broad,
                    _full=full,
                    _verbose=verbose,
                    _elapsed=_secrets_elapsed,
                ) -> None:
                    _t0 = time.monotonic()
                    _build_secrets_artifacts(
                        root=_root,
                        index_dir=_index_dir,
                        changed=_changed,
                        removed=_removed,
                        full=_full,
                        verbose=_verbose,
                    )
                    _elapsed.append(time.monotonic() - _t0)
                futures.append(executor.submit(_write_secrets))
            # Wave 1p5ch: the full rebuild streams the docs/code embed+write on the MAIN thread
            # (bounded buffer; never holds the whole chunk list), concurrently with the in-flight
            # secrets future. The incremental path used the docs/code futures submitted above.
            if full:
                _run_streaming_full_rebuild(
                    db_path=lance_db_path,
                    files_to_index=files_to_index,
                    root=root,
                    build_docs=build_docs,
                    build_code=build_code,
                    docs_embedder=docs_embedder,
                    code_embedder=code_embedder,
                    chunks_emitted_by_file=chunks_emitted_by_file,
                    buffer_chunks=_resolve_embed_buffer_chunks(root),
                    verbose=verbose,
                    docs_elapsed=_docs_elapsed,
                    code_elapsed=_code_elapsed,
                )
            # Wave 1p2q3 (1p2wd post-ship 1.3.22 / Bug 4 part 2): graph
            # extraction runs synchronously on the main thread, concurrently
            # with the in-flight docs/code/secrets futures above. This is the
            # load-bearing fix for the field-reported hang — see the long comment at the
            # top of this try-block.
            _build_graph_artifacts(
                root=root,
                index_dir=index_dir,
                layer=graph_layer,
                files=files_for_graph,
                current_file_meta=current_file_meta,
                changed=changed_for_graph,
                removed=removed,
                walker_version=WALKER_VERSION,
                chunker_version=current_chunker_version,
                verbose=verbose,
            )
            for f in futures:
                f.result()

        # Wave 1p5ch: persist chunks_emitted into current_file_meta AFTER the write — for the full
        # rebuild the streaming pass populated chunks_emitted_by_file during the write (the
        # incremental path populated it earlier). The cache-hit path in _detect_changes preserves
        # prior counts for unchanged files; this populates every file just chunked so the next
        # incremental drift check sees the truth once meta.json is written below.
        for rel, count in chunks_emitted_by_file.items():
            entry = current_file_meta.get(rel)
            if isinstance(entry, dict):
                entry["chunks_emitted"] = count

        # Get total chunk counts from Lance tables for the summary.
        total_doc_chunks = 0
        total_code_chunks = 0
        try:
            db = _get_lance_db(index_dir)
            if (index_dir / "docs.lance").is_dir():
                total_doc_chunks = db.open_table("docs").count_rows()
            if (index_dir / "code.lance").is_dir():
                total_code_chunks = db.open_table("code").count_rows()
        except Exception:
            total_doc_chunks = len(new_doc_chunks)
            total_code_chunks = len(new_code_chunks)
    except Exception as exc:
        print(f"build_index: index update failed: {exc}", file=sys.stderr)
        raise

    new_model_versions = dict(old_model_versions)
    # Wave 1p936: record the precision class for each built layer using the SAME predictor the
    # compare site uses (`_predicted_precision_class`), NOT the resolved-embedder class — the two
    # MUST agree or a same-machine incremental build would perpetually re-embed (the compare would
    # keep seeing a class mismatch it just wrote). `make_embedder` is constructed to resolve exactly
    # what the predictor reports (GPU→full incl. non-offload fastembed fallback; no-GPU + INT8
    # source→int8), so the recorded class stays truthful about the stored vectors on a real build.
    # A layer with no embedding work this run (embedder is None — e.g. an empty incremental update)
    # preserves whatever class was already recorded.
    build_providers = _onnx_providers()
    if build_docs:
        docs_class = (
            _predicted_precision_class(DOCS_MODEL, build_providers)
            if docs_embedder is not None
            else _precision_class_from_version(old_model_versions.get("docs"))
        )
        new_model_versions["docs"] = f"{DOCS_MODEL}@{docs_class}"
    if build_code:
        code_class = (
            _predicted_precision_class(CODE_MODEL, build_providers)
            if code_embedder is not None
            else _precision_class_from_version(old_model_versions.get("code"))
        )
        new_model_versions["code"] = f"{CODE_MODEL}@{code_class}"
    new_chunker_versions = dict(old_chunker_versions)
    if build_docs and current_chunker_version:
        new_chunker_versions["docs"] = current_chunker_version
    if build_code and current_chunker_version:
        new_chunker_versions["code"] = current_chunker_version
    available_content = set(meta.get("content", []))
    if build_docs:
        available_content.add("docs")
    if build_code:
        available_content.add("code")
    new_meta = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_versions": new_model_versions,
        "chunker_versions": new_chunker_versions,
        "walker_version": WALKER_VERSION,
        "content": sorted(available_content),
        "file_meta": current_file_meta,
    }
    _save_meta(index_dir, new_meta)

    # Reap LanceDB rows whose path is no longer in the current eligible set.
    # Runs on every incremental update across both tables — the workflow-
    # config-evolution blind spot is invisible from meta.json alone (the
    # narrowing already updated meta), so the reaper must reconcile LanceDB
    # directly. Reaping both tables regardless of ``content`` arg keeps the
    # cross-content failure mode closed: a docs-only update reaps code-table
    # orphans (and vice versa). Full rebuilds drop the tables entirely so
    # this pass is a no-op there.
    stranded_rows_reaped = 0
    stranded_rows_reaped_by_table: dict[str, int] = {"docs": 0, "code": 0, "total": 0}
    if not full:
        reap_result = _reap_stranded_lance_rows(
            lance_db_path,
            set(current_file_meta.keys()),
            tables=("docs", "code"),
            verbose=verbose,
        )
        stranded_rows_reaped_by_table = reap_result
        stranded_rows_reaped = reap_result.get("total", 0)

    summary = {
        "files_indexed": len(files_to_index),
        "files_total": len(files),
        "doc_chunks": total_doc_chunks,
        "code_chunks": total_code_chunks,
        "up_to_date": False,
        "stranded_rows_reaped": stranded_rows_reaped,
        "stranded_rows_reaped_by_table": stranded_rows_reaped_by_table,
    }
    files_summary = f"{len(added)} added, {len(updated)} updated, {len(removed)} removed"
    if build_docs:
        if full:
            # Wave 1p5ch: the streaming rebuild never materializes new_doc_chunks,
            # so report the rows actually written (from the Lance table count above).
            doc_chunk_summary = f"{total_doc_chunks} new"
        else:
            doc_chunk_summary = f"{doc_chunks_added} added, {doc_chunks_updated_new} updated, {doc_chunks_removed_net} removed"
        _docs_time = f" in {_docs_elapsed[0]:.1f}s" if _docs_elapsed else ""
        print(
            f"build_index: finished doc files: {files_summary} | chunks: {doc_chunk_summary}{_docs_time}",
            flush=True,
        )
    if build_code:
        if full:
            # Wave 1p5ch: see the docs branch above — report rows written, not the
            # (now-unused) eager chunk list.
            code_chunk_summary = f"{total_code_chunks} new"
        else:
            code_chunk_summary = f"{code_chunks_added} added, {code_chunks_updated_new} updated, {code_chunks_removed_net} removed"
        _code_time = f" in {_code_elapsed[0]:.1f}s" if _code_elapsed else ""
        print(
            f"build_index: finished code files: {files_summary} | chunks: {code_chunk_summary}{_code_time}",
            flush=True,
        )

    # Wave 1p601 (1p5x8): the codebase map is NOT regenerated here. The map lives
    # in the indexed docs/references/ tree, so regenerating it on every index
    # build creates a self-referential write→reindex loop. Map regen is decoupled
    # from the build and triggered at lifecycle (prepare/close), on upgrade,
    # on-demand (wave_index_build content="map" / CLI), and lazily on resource
    # read (regenerate-if-stale) instead.

    return summary


# ---------------------------------------------------------------------------
# Watch mode
# ---------------------------------------------------------------------------

def watch_index(root: Path, verbose: bool = False) -> None:
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print(
            "build_index --watch: watchdog is not installed.\n"
            "  Install with: pip install watchdog",
            file=sys.stderr,
        )
        sys.exit(1)

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if not event.is_directory:
                build_index(root, verbose=verbose)

        def on_created(self, event):
            if not event.is_directory:
                build_index(root, verbose=verbose)

        def on_deleted(self, event):
            if not event.is_directory:
                build_index(root, verbose=verbose)

    observer = Observer()
    observer.schedule(_Handler(), str(root), recursive=True)
    observer.start()
    print(f"build_index: watching {root} — press Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _discover_root() -> Path:
    """Walk up from CWD to find the repo root anchored by ``workflow-config.json``.

    Intentional differences from the copies in other scripts:
    - No ``override`` parameter (callers use ``--root`` CLI arg instead).
    - Never returns ``None`` — falls back to CWD.

    Cross-reference: ``server._discover_root``, ``lifecycle_id.discover_repo_root``,
    ``render_platform_surfaces.discover_repo_root``, ``docs_gardener.project_root``.
    A future consolidation task should unify these into a shared utility.
    """
    for env_key in ("PROJECT_ROOT", "REPO_ROOT"):
        raw = os.environ.get(env_key)
        if raw:
            candidate = Path(raw).expanduser().resolve()
            if (candidate / "docs" / "workflow-config.json").is_file():
                return candidate
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "docs" / "workflow-config.json").is_file():
            return candidate
    return cwd


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or update the Wavefoundry semantic index.")
    parser.add_argument("--root", type=Path, default=None, help="Repository root (default: auto-discover)")
    parser.add_argument("--full", action="store_true", help="Force a full rebuild even if index is current")
    parser.add_argument("--rechunk", action="store_true", help="Re-chunk every file (even unchanged) but reuse embeddings by content hash — only new/changed chunks re-embed. For a chunker LOGIC change that was not version-bumped (no full re-encode).")
    parser.add_argument(
        "--content",
        choices=CONTENT_CHOICES,
        default="docs",
        help=(
            "Content type to index (default: docs). "
            "`all` builds docs and code in one pass (used by setup_index.py --include-code). "
            "`code` indexes code only."
        ),
    )
    parser.add_argument("--index-dir", type=Path, default=None, help="Index output directory (default: <root>/.wavefoundry/index)")
    parser.add_argument(
        "--include-prefix",
        action="append",
        default=[],
        help="Only index files under this root-relative path prefix. Repeatable.",
    )
    parser.add_argument(
        "--no-ignore-files",
        action="store_true",
        help="Do not apply .gitignore/.aiignore patterns. Intended for framework packaging.",
    )
    parser.add_argument("--include-tests", action="store_true", help="Include target test files in semantic code indexing")
    parser.add_argument("--include-generated", action="store_true", help="Include generated platform hook files in semantic code indexing")
    parser.add_argument(
        "--project-include-prefix",
        action="append",
        default=[],
        help=(
            "Allow this repo-relative prefix to bypass default project index excludes "
            "(repeatable; applies to content=code)."
        ),
    )
    parser.add_argument("--watch", action="store_true", help="Watch for file changes and rebuild incrementally (requires watchdog)")
    parser.add_argument("--dry-run", action="store_true", help="Check whether a rebuild is needed without writing anything")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print progress")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _enable_timestamped_stdio()
    args = parse_args(argv)
    root = args.root.resolve() if args.root else _discover_root()

    try:
        if args.watch:
            watch_index(root, verbose=args.verbose)
            return 0

        build_index(
            root,
            full=args.full,
            rechunk=args.rechunk,
            content=args.content,
            index_dir=args.index_dir,
            include_prefixes=tuple(args.include_prefix),
            respect_ignore=not args.no_ignore_files,
            include_tests=args.include_tests,
            include_generated=args.include_generated,
            project_include_prefixes=tuple(args.project_include_prefix),
            verbose=args.verbose,
            dry_run=args.dry_run,
        )
        return 0
    except IndexBuildAlreadyRunning as exc:
        print(f"build_index: {exc}", file=sys.stderr)
        return 1
    finally:
        state_path = os.environ.get(INDEX_BUILD_STATE_PATH_ENV)
        if state_path:
            try:
                Path(state_path).unlink()
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
