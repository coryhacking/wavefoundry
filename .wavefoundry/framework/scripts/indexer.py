#!/usr/bin/env python3
"""Build and maintain the Wavefoundry semantic index at .wavefoundry/index/."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
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
import model_bundle

# Activate the shared tool venv IN-PROCESS before any heavy import (wave 1p7pl/1p802). No-op when
# already in the venv or when it does not exist yet (fresh bootstrap).
venv_bootstrap.activate_tool_venv()
import sqlite_vector_store as vector_store
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
LOCK_STALE_SECONDS = 60 * 60
TIMESTAMP_LOGS_ENV = "WAVEFOUNDRY_TIMESTAMP_LOGS"

# Documents and code remain independently configurable. Model set v2 selects
# Arctic S for both layers; equal names share one per-process instance, while a
# future reviewed split can still assign different IDs without new plumbing.
DOCS_MODEL = "Snowflake/snowflake-arctic-embed-s"
CODE_MODEL = "Snowflake/snowflake-arctic-embed-s"
EMBEDDING_MODEL_SET_FINGERPRINT = model_bundle.EMBEDDING_COMPATIBILITY_FINGERPRINT

# Instruction prefixes required by asymmetric embedding models.
# Values include a trailing space/separator so that ``prefix + text`` produces
# correctly formatted input. Empty strings mean no prefix for symmetric models.
# The pipeline embeds via fastembed ``.embed()`` (which does
# NOT auto-apply prefixes), so the QUERY prefix is applied explicitly at query
# time (``server_impl._embed_query`` via ``query_embedding_prefix``) and the
# DOCUMENT prefix at index time. arctic-embed is asymmetric: queries carry the
# "Represent this sentence…" instruction; documents carry none.
EMBEDDING_PREFIXES: dict[str, dict[str, str]] = {
    "nomic-ai/nomic-embed-text-v1.5-Q": {
        "document": "search_document: ",
        "query": "search_query: ",
    },
    "Snowflake/snowflake-arctic-embed-s": {
        "document": "",
        "query": "Represent this sentence for searching relevant passages: ",
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

# Exact SQLite vector scans require no ANN index maintenance.
EMBED_BATCH_SIZE = 256           # chunks per embedding batch
SORT_WINDOW_SIZE = 2048          # sliding sort buffer size (8× EMBED_BATCH_SIZE)
# Wave 1p52p: cross-encoder reranker. ms-marco-MiniLM-L-6-v2 (6-layer, 22M) via its Xenova FP16 export
# (resolved in accel_embedder.CLEAN_ONNX_SOURCES). Chosen over bge-reranker-base after a head-to-head:
# better known-answer recall (mean rank 1.07 vs 1.67), ~4-5x faster, ~8x less memory, and the only one
# whose CoreML compile cache speeds up restarts. Runs on either hardware: GPU FP16, or CPU INT8 (no
# ranking loss); reranking is skipped only when explicitly disabled (WAVEFOUNDRY_DISABLE_RERANKER).
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# Wave 1seax (1seau): derived from the canonical public-contract module so the
# CLI subset and the public MCP vocabulary cannot drift independently.
from public_contract import INDEXER_CLI_CONTENT_CHOICES as CONTENT_CHOICES

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
# Ignore files (wave 1seaw, 1seas): the direct-artifact exemption pins the named
# file at rank one, which is hollow unless the file is indexed; the same seven
# names carry the low-information prior when a query does not name them.
CODE_EXTENSIONLESS_NAMES = {
    "Jenkinsfile", "Makefile", "Dockerfile", "Vagrantfile", "Brewfile",
    "Fastfile", "Appfile", "Podfile", "Gemfile", "Procfile",
    ".aiignore", ".dockerignore", ".eslintignore", ".gitignore", ".ignore",
    ".npmignore", ".prettierignore",
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
# walk so they never appear in framework build state (and never get shipped via
# build_pack — which applies an equivalent filter in build_pack.py).
FRAMEWORK_TRANSIENT_ARTIFACT_EXTENSIONS = (".lock", ".log", ".bak", ".swp", ".tmp", ".orig", ".rej")
# Dev-only framework paths not shipped in the distribution zip.
# These are excluded from framework/index/ so index_build and build_pack
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

# ---------------------------------------------------------------------------
# CORPUS EXCLUSION STORY (wave 1wfsl / 1wfsn) — the ONE place that documents
# every mechanism that keeps a file out of the retrieval corpora. All three
# retrieval corpora (semantic docs, semantic code + lexical, graph) derive from
# the single `walk_repo()` pass plus `_filter_code_files()`, so these layers
# apply uniformly. In application order inside `walk_repo()`:
#
#   1. Directory pruning       — `HARDCODED_EXCLUDE_DIRS` (any component),
#                                the blanket dot-directory rule (allowlist:
#                                `_DOT_DIR_ALLOWLIST`), gitignore dir pruning.
#   2. Exact-path exclusions   — `HARDCODED_EXCLUDE_PATHS`.
#   3. Machine-authority paths — predicate family, NEVER re-includable:
#                                `_is_canonical_wave_events_path` (per-wave
#                                events.jsonl ledgers), `_is_memory_archive_body_path`,
#                                `_is_legacy_memory_pointer_path`,
#                                `_is_secret_scan_findings_path` (the committed
#                                secret-scan findings ledger). Also re-enforced
#                                on the `files=` build seam that bypasses the walk.
#   4. Prefix exclusions       — `HARDCODED_EXCLUDE_PREFIXES` (index/logs/locks).
#   5. Name layer              — `HARDCODED_EXCLUDE_FILENAMES` (exact names) and
#                                `HARDCODED_EXCLUDE_FILENAME_SUFFIXES` (bounded
#                                generated patterns, e.g. minified assets). This
#                                is the ONLY layer the per-project re-include
#                                hatch (`indexing.walk_reinclude_filenames` in
#                                docs/workflow-config.json) can subtract from.
#   6. Extension layers        — `BINARY_EXTENSIONS` (includes `.lock`, so every
#                                *.lock lockfile is excluded here even if a name
#                                entry is re-included) and
#                                `_GENERATED_EXCLUDE_EXTENSIONS`.
#   7. Content sniff           — magic-byte/null-byte scan for unknown
#                                extensions (catches e.g. `bun.lockb`).
#   8. Ignore files + size cap — .gitignore/.aiignore patterns, `indexing.max_file_bytes`.
#
# After the walk, `_filter_code_files()` gates the CODE corpus on
# `SOURCE_CODE_EXTENSIONS` (drops walked-but-not-code files such as `go.sum`,
# `gradle.lockfile`, `*.map`), and per-layer include-prefixes scope membership.
# Executed per-name census evidence: wave 1wfsl, 1wfsn-enh
# (docs/waves/ evidence census_results.json).
# ---------------------------------------------------------------------------

# Directories and patterns always excluded regardless of .gitignore/.aiignore
# Single directory names excluded wherever they appear in the path tree.
# (Exclusion story layer 1 — see the banner above.)
HARDCODED_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".tox", ".venv", "venv", ".env", "env",
    "dist", "build", "target", "out", "graphify-out", ".next", ".nuxt",
}

# Path prefixes (relative to repo root, forward slashes) that are always excluded.
from machine_authority import HARDCODED_EXCLUDE_PATHS, HARDCODED_EXCLUDE_PREFIXES
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
    ".wavefoundry/locks/dashboard-server.lock",  # merged lock + startup-metadata sidecar
    ".wavefoundry/guard-overrides.json",
    ".wavefoundry/logs/dashboard.log",
    # Wave 1p601: the generated codebase map is a derived artifact, refreshed by
    # create-mode prepare-and-open/close, upgrade, forced map-only MCP regeneration,
    # the change-only generator CLI, or the missing-file resource fallback. It must
    # NOT drive index staleness, or those regenerations
    # would trigger a redundant reindex for a derived artifact whose source inputs are
    # already tracked. (A normal resource read does NOT regenerate it — 1sq9h:
    # resource_codebase_map only writes the map when the file is missing.)
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
# Exclusion story layer 5 (name layer) — the re-include hatch
# (`indexing.walk_reinclude_filenames`) subtracts from this layer ONLY; note
# `yarn.lock` is double-covered by the `.lock` binary extension, so re-including
# it by name has no effect (the extension layer is not overridable).
HARDCODED_EXCLUDE_FILENAMES = frozenset({
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "npm-shrinkwrap.json",   # 1wfsn: npm publish-shape lockfile, machine-written
    "packages.lock.json",    # 1wfsn: NuGet lockfile, machine-written
    "prompt-surface-manifest.json",  # machine-generated metadata artifact, not useful for search
})

# Bounded generated-name patterns excluded at the same name layer (1wfsn):
# minified assets are machine-generated single-line blobs whose chunks embed as
# noise. Matched by filename suffix; the re-include hatch can subtract an exact
# filename from this layer too.
HARDCODED_EXCLUDE_FILENAME_SUFFIXES = (".min.js", ".min.css")

# Extensions for machine-generated files that are valid text but have no code semantics.
# .drawio and .excalidraw LEFT this set in wave 1wl7w (1wl7v): their earlier
# exclusions (the 1wl7u census-grounded .drawio decision and the original
# .excalidraw entry) were correct while the files shipped zero rows, and are
# SUPERSEDED now that the chunker extracts their labels into docs-routed
# doc-code units — the files return only WITH retrieval value.
_GENERATED_EXCLUDE_EXTENSIONS = frozenset({
    ".snap",        # Vitest / Jest snapshot files
})

# All extensions we treat as known text — no null-byte sniff needed.
_KNOWN_TEXT_EXTENSIONS = frozenset(SOURCE_CODE_EXTENSIONS) | {
    ".md", ".markdown",
    ".txt",
    ".rst", ".adoc", ".asciidoc",  # 1wfsm: prose docs formats, section-chunked doc-kind
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
# 6 -> 7 (1slep): canonical per-wave ``docs/waves/<wave>/events.jsonl``
# ledgers are machine authority, not retrieval content.  Generated ``wave.md``
# projections remain indexable; unrelated same-named JSONL files remain eligible.
# 7 -> 8 (1t8la): physical memory archive bodies are historical storage, not
# default docs/graph retrieval content. The compact archive register remains
# searchable so it can route an explicit history lookup without indexing bodies.
# 8 -> 9 (1u8r2): one compact archive register replaces per-record pointers.
# 9 -> 10 (1u8r2): exclude the repo-visible hash-only purge disposition authority.
# 10 -> 11 (1u8r2): exclude retired per-record memory pointers during upgrade
# transition, even before the lifecycle migration removes their directory.
# 11 -> 12 (1wfsl / 1wfsn): filter-logic change — straggler generated files are
# excluded at the name layer (`npm-shrinkwrap.json`, `packages.lock.json` exact;
# `*.min.js`/`*.min.css` by suffix), the committed secret-scan findings ledger
# joins the machine-authority path exclusions, and the per-project
# `indexing.walk_reinclude_filenames` hatch can subtract exact names from the
# name layer only. Existing indexes must re-walk to drop the newly-excluded files.
# 12 -> 13 (1wfsl / 1wfsm): filter-logic-change clause — `.rst`/`.adoc`/`.asciidoc`
# join `_KNOWN_TEXT_EXTENSIONS` (sniff skipped; walk membership itself is
# unchanged since these text files already passed the sniff). The bump rides the
# same clause so consumer indexes re-walk and re-chunk them through the new
# doc-kind section chunkers (paired with the CHUNKER_VERSION 33 bump).
# 13 -> 14 (1wh1b, wave 1wl7u): `.drawio` joins `_GENERATED_EXCLUDE_EXTENSIONS`
# (the `.excalidraw` precedent). Census-grounded decision closing the 1whuq
# open question: a text-XML .drawio passes the content sniff, WALKS in, chunks
# as one code-kind line window, and ships zero rows in either table (not
# code-eligible; kind never docs-routed) — all cost, no value. Existing
# indexes must re-walk to drop the files. The reinclude hatch cannot override
# the generated-extension layer (by design, pinned by
# test_reinclude_hatch_cannot_override_extension_or_sniff), and nothing is
# lost: a re-included .drawio would still ship zero rows; surfacing .drawio
# content would be a future CHUNKER decision, not a walk hatch.
# 14 -> 15 (1wl7v, wave 1wl7w): that future chunker decision is now taken —
# `.drawio` AND `.excalidraw` leave `_GENERATED_EXCLUDE_EXTENSIONS`, an
# executable SUPERSESSION of the 14 rationale above ("still ship zero rows")
# and of the original `.excalidraw` exclusion: the chunker now extracts their
# node/edge/frame labels into docs-routed doc-code units, so the files return
# WITH retrieval value (paired with the CHUNKER_VERSION 39 bump). Existing
# indexes must re-walk to pick both extensions up.
# 15 -> 16 (1seas, wave 1seaw): the seven ignore-file names join
# CODE_EXTENSIONLESS_NAMES / CODE_EXTENSIONLESS_SOURCE_NAMES. A direct question
# that names an ignore file pins that file at rank one only when the file is
# indexed; before this bump `.aiignore` was walked but never eligible, so the
# documented exemption had nothing to pin. Existing indexes must re-walk to
# admit the files; the low-information prior keeps them down-weighted unless
# the query names them.
WALKER_VERSION = "16"
from machine_authority import (
    MEMORY_ARCHIVE_PREFIX as _MEMORY_ARCHIVE_PREFIX,
    MEMORY_LEGACY_POINTER_PREFIX as _MEMORY_LEGACY_POINTER_PREFIX,
)

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


def _resolve_spec_chunking_override(root: Path) -> Optional[bool]:
    """Read `indexing.spec_aware_chunking` (1wfr8) from docs/workflow-config.json.
    Returns the boolean when present, None when absent/invalid (chunker default)."""
    cfg = root / "docs" / "workflow-config.json"
    if not cfg.exists():
        return None
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    indexing = data.get("indexing", {}) if isinstance(data, dict) else {}
    value = indexing.get("spec_aware_chunking") if isinstance(indexing, dict) else None
    return value if isinstance(value, bool) else None


def _resolve_walk_reinclude_filenames(root: Path) -> frozenset[str]:
    """Per-project re-include hatch (1wfsn): exact filenames subtracted from the
    NAME layer of the walk exclusions (`HARDCODED_EXCLUDE_FILENAMES` +
    `HARDCODED_EXCLUDE_FILENAME_SUFFIXES`) via `indexing.walk_reinclude_filenames`
    in docs/workflow-config.json. Default empty. It cannot override the
    binary-extension, generated-extension, or content-sniff layers, and never
    reaches the machine-authority path exclusions, which the walk applies
    before the name layer. Non-list / non-string entries are ignored."""
    cfg = root / "docs" / "workflow-config.json"
    if not cfg.exists():
        return frozenset()
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return frozenset()
    indexing = data.get("indexing", {}) if isinstance(data, dict) else {}
    if not isinstance(indexing, dict):
        return frozenset()
    raw = indexing.get("walk_reinclude_filenames")
    if not isinstance(raw, list):
        return frozenset()
    return frozenset(
        entry for entry in raw
        if isinstance(entry, str) and entry and "/" not in entry and "\\" not in entry
    )


# Wave 1to78: the structural wave-ledger predicate relocated to
# review_evidence.py so the docs-lint orphan-ledger guard and this retrieval
# exclusion share one definition of the fixed wave-folder role. The
# underscore alias keeps internal callers and test seams stable.
from machine_authority import is_canonical_wave_events_path as _is_canonical_wave_events_path


def _filter_canonical_wave_event_ledgers(files: list[Path], root: Path) -> list[Path]:
    """Drop only canonical wave event ledgers from a candidate file list."""
    return [
        path for path in files
        if not _is_canonical_wave_events_path(
            str(path.relative_to(root)).replace("\\", "/"), root
        )
    ]


from machine_authority import (
    is_memory_archive_body_path as _is_memory_archive_body_path,
    is_legacy_memory_pointer_path as _is_legacy_memory_pointer_path,
)


def _filter_memory_archive_bodies(files: list[Path], root: Path) -> list[Path]:
    return [
        path for path in files
        if not _is_memory_archive_body_path(
            str(path.relative_to(root)).replace("\\", "/")
        )
    ]


def _filter_legacy_memory_pointers(files: list[Path], root: Path) -> list[Path]:
    return [
        path for path in files
        if not _is_legacy_memory_pointer_path(
            str(path.relative_to(root)).replace("\\", "/")
        )
    ]


# 1wfsn: the committed secret-scan FINDINGS ledger is machine authority (finding
# records with status/disposition), never retrieval content — the same class as
# the wave event ledgers above. The path is imported from wave_lint_lib so the
# scanner and this exclusion share one definition.
from wave_lint_lib.constants import SCAN_FINDINGS_PATH as _SCAN_FINDINGS_REL_PATH
from machine_authority import is_secret_scan_findings_path as _is_secret_scan_findings_path


def _filter_secret_scan_findings(files: list[Path], root: Path) -> list[Path]:
    return [
        path for path in files
        if not _is_secret_scan_findings_path(
            str(path.relative_to(root)).replace("\\", "/")
        )
    ]


def walk_repo(
    root: Path,
    *,
    respect_ignore: bool = True,
    unreadable_dirs: "set[str] | None" = None,
) -> list[Path]:
    """Return all indexable files under root, respecting ignore rules.

    Wave 1p5c4: files larger than the hard size cap (`indexing.max_file_bytes`, default 5 MB) are
    skipped entirely — a multi-GB blob (e.g. a SQL backup) would otherwise be read and
    tree-sitter-parsed, spinning the indexer.

    Wave 1x54z (1u8o3): a directory ``os.walk`` cannot read is no longer dropped in
    silence. ``os.walk``'s default ``onerror=None`` skips any directory whose ``scandir``
    raises (permissions, EIO, a vanished mount), so every path under it simply vanishes
    from the result and, to a caller reconciling stored state against the walk, reads as
    deleted. The failures are collected through ``onerror`` instead: each affected
    directory (root-relative, ``"."`` for the root itself) is added to ``unreadable_dirs``
    when the caller passes a set, and the condition is printed to stderr either way, so a
    consumer can tell "not walked" from "not there". The walk's FILTER logic is
    unchanged (no ``WALKER_VERSION`` bump)."""
    ignore_patterns = _load_ignore_patterns(root) if respect_ignore else []
    max_file_bytes = _resolve_max_file_bytes(root)
    reinclude_names = _resolve_walk_reinclude_filenames(root)
    result: list[Path] = []
    unreadable: set[str] = set()

    def _on_walk_error(exc: OSError) -> None:
        raw = getattr(exc, "filename", None)
        rel_failed: "str | None" = None
        if raw is not None:
            try:
                rel_failed = str(Path(os.fsdecode(raw)).relative_to(root)).replace("\\", "/")
            except (ValueError, TypeError):
                rel_failed = None
        # An unmappable failure is recorded as the root: the conservative reading
        # (every stored path is under it) beats guessing which subtree was lost.
        unreadable.add(rel_failed if rel_failed is not None else ".")

    for dirpath, dirnames, filenames in os.walk(root, onerror=_on_walk_error):
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
            # generated/binary trees — most importantly `.wavefoundry/index/` (generated index files),
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

            # Wave 1slep: raw append-only review history is canonical machine
            # state.  Search the generated wave.md current-head projection,
            # never the ledger (which also contains superseded findings).
            if _is_canonical_wave_events_path(rel_str, root):
                continue
            if _is_memory_archive_body_path(rel_str):
                continue
            if _is_legacy_memory_pointer_path(rel_str):
                continue
            # 1wfsn: committed secret-scan findings ledger — machine authority,
            # applied BEFORE the name layer so the re-include hatch can't reach it.
            if _is_secret_scan_findings_path(rel_str):
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

            # Name layer (exclusion story layer 5): exact generated filenames plus
            # bounded generated-name suffix patterns. The ONLY layer the
            # per-project re-include hatch subtracts from; the extension and
            # sniff layers below still apply to anything re-included here.
            if filename not in reinclude_names:
                if filename in HARDCODED_EXCLUDE_FILENAMES:
                    continue
                if filename.endswith(HARDCODED_EXCLUDE_FILENAME_SUFFIXES):
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

    if unreadable:
        if unreadable_dirs is not None:
            unreadable_dirs.update(unreadable)
        # Wave 1p9io posture: stderr, never stdout — walk_repo runs in-process
        # from the MCP server where stdout is the JSON-RPC channel.
        print(
            f"build_index: walk skipped {len(unreadable)} unreadable director"
            f"{'y' if len(unreadable) == 1 else 'ies'} (os.walk could not scan "
            f"{'it' if len(unreadable) == 1 else 'them'}; paths under "
            f"{'it' if len(unreadable) == 1 else 'them'} were NOT walked): "
            + _describe_unreadable_dirs(unreadable),
            file=sys.stderr,
            flush=True,
        )
    return sorted(result)


def _shadowed_by_unreadable(rel: str, unreadable_dirs: "set[str] | None") -> bool:
    """True when ``rel`` sits under a directory the walk reported unreadable
    (wave 1x54z / 1u8o3). ``"."`` shadows every path; otherwise a normalized
    prefix match on the root-relative directory."""
    if not unreadable_dirs:
        return False
    for d in unreadable_dirs:
        if d == ".":
            return True
        d = d.replace("\\", "/").rstrip("/")
        if rel == d or rel.startswith(d + "/"):
            return True
    return False


def _deferred_summary(deferred_by_table: "dict[str, dict] | None") -> dict:
    """Build-result projection of the reap's deferral record (wave 1x54z,
    delivery review RED-DEL-2): the per-table counts without the path sets,
    so a build that deferred a reap never reports ``up_to_date`` silently."""
    out: dict = {}
    for table, entry in (deferred_by_table or {}).items():
        if not isinstance(entry, dict):
            continue
        out[table] = {
            "would_reap": int(entry.get("would_reap", 0) or 0),
            "table_paths": int(entry.get("table_paths", 0) or 0),
        }
    return out


def _preserved_summary(preserved_by_table: "dict[str, set] | None") -> dict:
    """Build-result projection of the reap's preserved (unreadable) paths per
    table (wave 1x54z, delivery review SEC-DEL-1): counts only, so a build
    that kept unconfirmed rows says so in its envelope."""
    return {
        table: len(paths)
        for table, paths in (preserved_by_table or {}).items()
        if paths
    }


def _record_reap_state(
    index_dir: Path,
    *,
    deferred: "dict | None",
    preserved: "dict | None",
    dry_run: bool,
    verbose: bool = False,
) -> bool:
    """Persist the reap's deferral / preservation summaries in the index-state
    store's ``meta`` table (wave 1x6ti, 1x551) so ``index_build_status`` and
    ``index_health`` can surface them; remove the record when neither applies.

    Called at every summary-carrying return of ``_build_index_locked``. Skips
    ``dry_run`` builds (the preflight is reachable unlocked there and a dry
    run must not write). Epoch-free, and it NEVER fails the build
    (``_record_drift_failure``'s posture): every exception is caught, the
    failure goes to the store log, and the build result still carries the
    summaries. Returns True when the store now reflects the summaries."""
    if dry_run:
        return False
    iss = _get_index_state_store()
    if iss is None or not hasattr(iss, "write_reap_state"):
        return False
    try:
        return bool(iss.write_reap_state(index_dir, deferred=deferred, preserved=preserved))
    except Exception as exc:  # noqa: BLE001 - a visibility aid never fails a build
        msg = (
            "build_index: reap state record not written "
            f"(deferred={bool(deferred)} preserved={bool(preserved)}): {exc}"
        )
        _store_log_safe(index_dir, msg)
        if verbose:
            print(msg, file=sys.stderr, flush=True)
        return False


def _describe_unreadable_dirs(unreadable_dirs: "set[str] | None") -> str:
    """Operator-facing rendering of the walk's unreadable directories: the
    root is named as such rather than printed as a bare dot (SEC-DEL-1)."""
    names = sorted(unreadable_dirs or ())
    return ", ".join("the repository root" if d == "." else d for d in names)


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
    selected_paths: set[str] | None = None,
) -> tuple[dict[str, dict], set[str], set[str]]:
    """Return (current_file_meta, changed_paths, removed_paths).

    Uses mtime+size+inode as a cheap pre-filter: only files whose stat differs
    from stored values are read and hashed. Files that pass the stat check are
    treated as unchanged without any file I/O.

    old_meta maps rel_path -> {"hash": str, "mtime": float, "size": int, "inode": int}.
    """
    current: dict[str, dict] = ({rel: entry for rel, entry in old_meta.items()
                                if rel not in selected_paths}
                               if selected_paths is not None else {})
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
    index_build and build_pack never fight over different file sets.
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


# 1sek8: extensionless files the chunker code-chunks by NAME. Duplicated from
# chunker.CODE_EXTENSIONLESS_NAMES + MAKEFILE_NAMES rather than imported (the
# filter runs before the chunker module loads); a wiring test keeps them in
# sync. Without this, unifying the code corpus on _filter_code_files would
# silently drop Makefiles/Dockerfiles that content=all builds always indexed.
CODE_EXTENSIONLESS_SOURCE_NAMES = {
    "Jenkinsfile", "Makefile", "GNUmakefile", "Dockerfile", "Vagrantfile",
    "Brewfile", "Fastfile", "Appfile", "Podfile", "Gemfile", "Procfile",
    ".aiignore", ".dockerignore", ".eslintignore", ".gitignore", ".ignore",
    ".npmignore", ".prettierignore",
}


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
        _known_extensionless = not path.suffix and path.name in CODE_EXTENSIONLESS_SOURCE_NAMES
        if path.suffix.lower() not in SOURCE_CODE_EXTENSIONS and not _known_extensionless:
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
    """Build-state read — SQLITE ONLY (1sed6).

    Reconstructs the build-state dict (file_meta, model/chunker/walker
    versions, content) from the index-state store's bookkeeping tables.
    A legacy ``meta.json`` on disk is NEVER read as authority: an
    installation with JSON but no current store converges by full
    reconstruction from repository/git/canonical chunks (empty dict here means
    "everything is new" — the derived-only convergence path), and the stale
    file is removed after the next successful build.
    """
    iss = _get_index_state_store()
    if iss is None:
        return {}
    try:
        snapshot = iss.export_meta_snapshot(index_dir)
    except Exception:  # noqa: BLE001 - unreadable store == no prior state
        return {}
    return snapshot or {}


def _build_failed_result(files: list, reason: str) -> dict:
    """Structured build failure (1sed6 Req 2): the build did NOT complete —
    the epoch stays un-finalized (readers fail closed) and the caller must
    not treat the index as current. Printed loudly and store-logged where
    possible."""
    print(f"build_index: FAILED — {reason}", file=sys.stderr, flush=True)
    return {
        "files_indexed": 0,
        "files_total": len(files or []),
        "up_to_date": False,
        "failed": True,
        "failure": reason,
    }


def _remove_legacy_meta_json(index_dir: Path) -> bool:
    """Delete a stale legacy ``meta.json`` AFTER a verified successful build
    (1sed6 Req 7). Non-fatal but LOUD on failure (review fix): a surviving
    legacy file must be visible — stderr plus the persisted store log — so a
    permissions problem cannot silently leave a second state surface on disk.
    Returns True when a file was removed."""
    meta_path = index_dir / META_JSON
    try:
        if meta_path.is_file():
            meta_path.unlink()
            return True
    except OSError as exc:
        msg = (f"legacy meta.json could not be removed ({exc}) — it is IGNORED as state "
               "but remove it manually; SQLite is the only authority")
        print(f"build_index: WARNING — {msg}", file=sys.stderr, flush=True)
        try:
            iss = _get_index_state_store()
            if iss is not None:
                iss.store_log(index_dir, msg)
        except Exception:
            pass
    return False


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


def project_layer_freshness(root: Path) -> "dict[str, Any]":
    """Cheap per-layer freshness signal for the search hot path (wave 1seav / 1sbxq).

    ONE stat-fast-path walk (no per-call corpus hashing) feeding three cheap
    comparisons:

    1. **Walk vs broad snapshot** (``_detect_changes``): edits, additions,
       and deletions since the LAST BUILD of any kind.
    2. **Per-layer hash compare, SYMMETRIC:** each layer's last-embedded
       hashes (``layer_path_state``) against the CURRENT walk hashes — a
       layer is stale when a recorded path's content moved past it (the
       1sek8 layer-crossing case), when a recorded path is gone, **or when
       an eligible path was never processed by the layer at all** (a file
       ADDED and stamped into the broad snapshot by another layer's build).
       Eligibility mirrors the build's own per-layer sets.
    3. **Chunker-version mismatch** (store scalars vs the module constant).

    Honesty rules: ``current`` requires the walk pass to have POSITIVELY
    determined no changes; an undeterminable walk, an unreadable layer state
    for a REQUIRED layer (non-empty eligible set), or any exception reads
    ``None`` (= unknown), never ``False``.
    """
    try:
        index_dir = root / ".wavefoundry" / "index"
        iss = _get_index_state_store()
        if iss is None:
            return {"stale": None, "layers": {}, "chunker_stale": None, "reason": "store module unavailable"}
        summary = iss.read_build_summary(index_dir)
        meta = _load_meta(index_dir)
        file_meta = meta.get("file_meta") if isinstance(meta, dict) else None
        if not summary or not isinstance(file_meta, dict) or not file_meta:
            return {"stale": None, "layers": {}, "chunker_stale": None, "reason": "no build snapshot"}

        current_cv = str(getattr(_get_chunker(), "CHUNKER_VERSION", ""))
        stored_cv = summary.get("chunker_versions") or {}
        chunker_stale = bool(stored_cv) and any(
            str(v) != current_cv for v in stored_cv.values()
        )

        # --- ONE walk, the build's own filter discipline ---
        files = walk_repo(root, respect_ignore=True)
        files = [path for path in files if not _is_relative_to(path, index_dir)]
        meta_includes = _project_meta_include_prefixes(root, ())
        walk_files = _filter_project_index_excludes(files, root, (), project_include_prefixes=meta_includes)
        walk_files = [
            path for path in walk_files
            if str(path.relative_to(root)).replace("\\", "/") not in _PROJECT_STALE_IGNORE_PATHS
        ]
        filtered_file_meta = {
            rel: entry for rel, entry in file_meta.items()
            if rel not in _PROJECT_STALE_IGNORE_PATHS
        }
        walk_stale: "bool | None"
        try:
            current_meta, changed, removed = _detect_changes(walk_files, root, filtered_file_meta)
            walk_stale = bool(changed or removed)
        except Exception:  # noqa: BLE001 - undeterminable, never current
            current_meta = {}
            walk_stale = None

        # --- Per-layer eligibility, mirroring the build ---
        docs_includes = _effective_project_include_prefixes(root, index_dir, "docs", ())
        docs_eligible: set[str] = {
            str(f.relative_to(root)).replace("\\", "/")
            for f in _filter_project_index_excludes(files, root, (), project_include_prefixes=docs_includes)
        }
        code_includes = _effective_project_include_prefixes(root, index_dir, "code", ())
        code_eligible: set[str] = {
            str(f.relative_to(root)).replace("\\", "/")
            for f in _filter_code_files(
                _filter_project_index_excludes(files, root, (), project_include_prefixes=code_includes),
                root,
                include_tests=False,
                include_generated=False,
            )
        }
        docs_eligible |= code_eligible  # 1sek8 dual-output union
        # 1sq9h: keep the ignore discipline uniform across every comparison input.
        # walk_files and filtered_file_meta already drop _PROJECT_STALE_IGNORE_PATHS
        # above; drop them here too so an ignore-listed path cannot drive the symmetric
        # "eligible path not in state" branch.
        docs_eligible -= _PROJECT_STALE_IGNORE_PATHS
        code_eligible -= _PROJECT_STALE_IGNORE_PATHS

        layers: dict = {}
        required_layer_unreadable = False
        for layer, eligible in (("docs", docs_eligible), ("code", code_eligible)):
            state = iss.layer_hashes(index_dir, layer)
            if state is None:
                layers[layer] = None
                if eligible:
                    required_layer_unreadable = True
                continue
            layer_stale = False
            for rel, embedded_hash in state.items():
                # 1sq9h: ignore-listed paths (e.g. the generated codebase map)
                # are filtered out of walk_files and filtered_file_meta above; apply the
                # same filter here so a recorded-but-ignored path is not read as
                # "recorded path gone" (both maps lack it by construction) → the
                # permanent false-stale that stuck every repo with a codebase map.
                if rel in _PROJECT_STALE_IGNORE_PATHS:
                    continue
                entry = current_meta.get(rel) or filtered_file_meta.get(rel)
                if entry is None:
                    layer_stale = True  # recorded path gone (or excluded)
                    break
                if str(entry.get("hash", "")) != str(embedded_hash):
                    layer_stale = True  # content moved past the layer
                    break
            if not layer_stale:
                # Symmetric direction (review fix): an eligible path the
                # layer never processed — e.g. ADDED, then stamped into the
                # broad snapshot by another layer's build.
                for rel in eligible:
                    if rel not in state:
                        layer_stale = True
                        break
            layers[layer] = layer_stale

        if chunker_stale:
            stale: "bool | None" = True
            reason = "chunker version mismatch"
        elif walk_stale:
            stale = True
            reason = "inputs changed since last build"
        elif any(v for v in layers.values() if v):
            stale = True
            reason = "layer behind broad snapshot"
        elif walk_stale is None:
            stale = None
            reason = "walk undeterminable"
        elif required_layer_unreadable:
            stale = None
            reason = "required layer state unreadable"
        else:
            stale = False
            reason = "current"
        return {"stale": stale, "layers": layers, "chunker_stale": chunker_stale, "reason": reason}
    except Exception as exc:  # noqa: BLE001 - honesty rule: undeterminable, never silently current
        return {"stale": None, "layers": {}, "chunker_stale": None, "reason": f"error: {exc}"}


# ---------------------------------------------------------------------------
# SQLite vector storage helpers
# ---------------------------------------------------------------------------







# Wave 1p5ch: streaming full-rebuild. Files are chunked into a bounded buffer that flushes
# (embed → create/append) once it fills, so the full chunk list for a layer is never held in
# memory — peak memory is bounded by the buffer, independent of corpus size. Rows are produced with
# `_embed_texts` + `_make_vector_rows` and the vector + FTS index is built once at the end; the
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


# Per-layer forward-pass batch width (1p7iv). The onnxruntime CPU forward pass materializes
# activation tensors that scale with this batch (attention ~ batch x heads x seq^2), so it is the
# dominant CPU-embedding memory lever. Keep the layer selectors independent even when both layers
# currently use Arctic S: an operator may still tune docs/code batching separately, and a future
# divergent model assignment must not require restoring a coupled configuration mechanism. The GPU
# static-shape embedder ignores this setting (it uses STATIC_BATCH).
# Default 32 (down from 256): the benchmark's lowest-memory AND fastest CPU point — ~3.5–3.8x less peak
# RSS at equal-or-better throughput (onnxruntime parallelizes each forward pass across cores regardless
# of batch, so a small batch still fills cores). Raise per-model via workflow-config for bigger batches.
_DEFAULT_EMBED_BATCH = 32
_EMBED_BATCH_CONFIG_KEYS = {
    "docs": "docs_embed_batch_size",
    "code": "code_embed_batch_size",
}


def _resolve_embed_batch_size(model_name: str, root: Path, *, layer: Optional[str] = None) -> int:
    """Forward-pass batch width for a model/layer — overridable via ``docs/workflow-config.json``:
    per-model ``indexing.{docs,code}_embed_batch_size`` wins, then global ``indexing.embed_batch_size``,
    then the per-model default. A CPU-path memory lever (the GPU static-shape embedder ignores it);
    smaller batch = less onnxruntime activation memory, at equal-or-better CPU throughput.

    ``layer`` is the configuration authority. It is intentionally not derived from ``model_name``:
    DOCS_MODEL and CODE_MODEL may be equal while their operator overrides remain independent.
    ``model_name`` remains in the API because callers and diagnostics identify the selected model.
    """
    del model_name
    default = _DEFAULT_EMBED_BATCH
    cfg = root / "docs" / "workflow-config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            indexing = data.get("indexing", {}) if isinstance(data, dict) else {}
            if isinstance(indexing, dict):
                for key in (_EMBED_BATCH_CONFIG_KEYS.get(layer), "embed_batch_size"):
                    if key:
                        raw = indexing.get(key)
                        if isinstance(raw, int) and raw > 0:
                            return raw
        except (OSError, json.JSONDecodeError):
            pass
    return default


class _StreamingLayerWriter:
    """Embed bounded buffers into an unpublished spool, outside the index transaction."""
    def __init__(self, prepared, table_name: str, embedder, label: str,
                 batch_size: int = EMBED_BATCH_SIZE):
        self.prepared, self.table_name = prepared, table_name
        self.embedder, self.label = embedder, label
        self.batch_size, self.written = batch_size, 0
        self.prepared.add(table_name, replace=True)

    def add(self, chunks: list[dict]) -> None:
        if not chunks:
            return
        vectors = _embed_texts(self.embedder, [c['text'] for c in chunks], batch_size=self.batch_size)
        self.prepared.add(self.table_name, rows=_make_vector_rows(chunks, vectors))
        self.written += len(chunks)
        print(f"build_index: embedded {self.written} chunks ({self.label})", flush=True)

    def finalize(self, verbose=False):
        print(f"build_index: prepared {self.label} index ({self.written} chunks)", flush=True)
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
    docs_eligible_rel: "set[str] | None" = None,
    code_eligible_rel: "set[str] | None" = None,
    prepared=None,
    strict_reads: bool = False,
) -> None:
    """Wave 1p5ch: full rebuild as a bounded-buffer stream. Chunks each file ONCE (recording
    ``chunks_emitted_by_file``), routes doc/code chunks to per-layer buffers, and flushes a buffer
    (embed → create/append) once it reaches ``buffer_chunks``; the vector + FTS index is built once
    per layer at the end. Peak memory is bounded by the buffers, independent of corpus size.
    Progress is reported per file (``file N / M``) — no total-chunk pre-count."""
    docs_writer = _StreamingLayerWriter(prepared, "docs", docs_embedder, "doc",
        batch_size=_resolve_embed_batch_size(DOCS_MODEL, root, layer="docs")) if build_docs else None
    code_writer = _StreamingLayerWriter(prepared, "code", code_embedder, "code",
        batch_size=_resolve_embed_batch_size(CODE_MODEL, root, layer="code")) if build_code else None
    docs_buf: list[dict] = []
    code_buf: list[dict] = []
    t_docs = 0.0
    t_code = 0.0
    total = len(files_to_index)

    for i, file_path in enumerate(files_to_index, 1):
        rel = str(file_path.relative_to(root)).replace("\\", "/")
        try:
            source_text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            if strict_reads:
                raise
            continue
        dc, cc = _chunks_for_file(rel, source_text)
        # 1sek8: per-layer eligibility gates the routing — one corpus
        # definition per table under every content scope (a test file
        # reachable through the docs walk must not feed the code table).
        # The emitted count is recorded AFTER gating so the drift
        # detector never sees a claimed-but-ineligible contribution.
        if docs_eligible_rel is not None and rel not in docs_eligible_rel:
            dc = []
        if code_eligible_rel is not None and rel not in code_eligible_rel:
            cc = []
        # A layer this rebuild is not writing must not be CLAIMED either
        # (a docs-only full build recording code-chunk counts would
        # drift-flag every code file until a code build ran).
        if not build_docs:
            dc = []
        if not build_code:
            cc = []
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

    docs_elapsed.append(t_docs)
    code_elapsed.append(t_code)











# Semantic docs/code layer names within the project-local SQLite store.






def optimize_index_tables(index_dir: Path, tables=("docs", "code")) -> dict:
    """Maintain the shared semantic/graph file once, without re-embedding."""
    iss = _get_index_state_store()
    if not (index_dir / vector_store.FILENAME).exists():
        return {}
    with _index_build_lock(index_dir):
        prior = iss.read_build_state(index_dir)
        if not prior or prior.get("status") != "complete":
            return {"error": "no completed build epoch — run index_build first"}
        attempt = iss.begin_build_epoch(index_dir, "optimize")
        stores = iss.optimize_state_stores(index_dir, full_vacuum=False)
        result = {"stores": stores}
        if any(r.get("error") or r.get("integrity") not in (None, "ok")
               for r in stores.values()):
            result["finalize"] = {"error": "SQLite maintenance failed; epoch NOT finalized"}
            return result
        counts = vector_store.layer_counts(index_dir)
        for layer in tables:
            if layer in counts:
                result[layer] = {"tier": 1, "rows": counts[layer], "needs_rebuild": False,
                                 "error": None, "bytes_before": 0, "bytes_after": 0}
        if not iss.finalize_build_epoch(index_dir, attempt):
            result["error"] = "epoch finalization CAS miss"
        return result





def _store_log_safe(index_dir: "Optional[Path]", message: str) -> None:
    """Persist a build diagnostic to the index-state store log (1sbfj).

    Best-effort wrapper: silently a no-op when ``index_dir`` is unknown at the
    call site or the store module is unavailable — persistence is additive,
    the stdout/stderr print remains the primary channel.
    """
    if index_dir is None:
        return
    try:
        iss = _get_index_state_store()
        if iss is not None:
            iss.store_log(index_dir, message)
    except Exception:  # noqa: BLE001 - logging must never fail the caller
        pass











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
    """Normalize row metadata so freshly chunked rows compare cleanly to stored rows."""
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


def _make_vector_rows(chunks: list[dict], vecs: "np.ndarray | list") -> list[dict]:
    """Combine canonical chunk payloads with their float32 vectors."""
    rows = []
    for chunk, vec in zip(chunks, vecs):
        row = dict(chunk)
        if isinstance(row.get("tags"), list):
            row["tags"] = " ".join(str(t) for t in row["tags"])
        row["chunk_hash"] = _chunk_hash(chunk)
        # Preserve the existing non-null string payload/filter contract across
        # Markdown-only and mixed-language batches.
        for _nullable_str in ("language", "section"):
            if row.get(_nullable_str) is None:
                row[_nullable_str] = ""
        row["vector"] = vec.tolist() if hasattr(vec, "tolist") else list(vec)
        rows.append(row)
    return rows


def _read_vector_rows_for_paths(db_path: Path, table_name: str, paths: set[str]) -> list[dict]:
    result = []
    ordered = sorted(paths)
    for start in range(0,len(ordered),100):
        clause = ",".join("'" + p.replace("'", "''") + "'" for p in ordered[start:start+100])
        result.extend(vector_store.payload_rows(db_path, table_name, f"path IN ({clause})", include_vector=True))
    return result





def _detect_vector_drift(
    db_path: Path,
    file_meta: dict[str, dict],
    *,
    chunk_eligible_rel_paths: set[str],
    tables: tuple[str, ...] = ("docs", "code"),
    verbose: bool = False,
) -> set[str]:
    """Find eligible source paths whose expected canonical/vector rows are absent.

    Respect explicit zero-chunk provenance and the current build's writable
    corpus, avoiding retries for empty or excluded files. Registry-backed holes
    are checked per layer: surviving code rows must not hide missing docs rows
    from the same source file. Only path/ID columns are read, never vectors.
    Unknown/missing state is handled by the build's schema/provenance gate.
    """
    if not file_meta:
        return set()
    # 1rmaf: drift candidacy is gated on current-build chunk eligibility —
    # a path the current build would never chunk can never be "drifted"
    # (the repair path could not reach it, so flagging it loops forever).
    if verbose:
        ineligible_count = sum(1 for path in file_meta if path not in chunk_eligible_rel_paths)
        if ineligible_count:
            print(
                f"build_index: drift-detect skipped {ineligible_count} path(s) as chunk-ineligible "
                "(outside this build's content filters)",
                flush=True,
            )
    # Wave 1p3iw: exclude paths previously recorded as legitimately empty.
    # Missing ``chunks_emitted`` (legacy entries / fresh stat-mismatch entries)
    # falls through to the drift check unchanged.
    file_meta_paths = {
        path for path, entry in file_meta.items()
        if path in chunk_eligible_rel_paths
        and not (isinstance(entry, dict) and entry.get("chunks_emitted") == 0)
    }
    if not file_meta_paths:
        return set()
    conn = _get_index_state_store().open_read_only(db_path)
    if conn is None:
        return set()
    try:
        canonical_paths = set()
        missing_vectors = set()
        for table_name in tables:
            vector_store._layer(table_name)
            canonical_paths.update(r[0] for r in conn.execute(f"SELECT DISTINCT path FROM chunks_{table_name}"))
            missing_vectors.update(r[0] for r in conn.execute(
                f"SELECT DISTINCT c.path FROM chunks_{table_name} c LEFT JOIN vectors_{table_name} v "
                "ON c.id=v.chunk_id WHERE v.chunk_id IS NULL"))
            missing_vectors.update(r[0] for r in conn.execute(
                f"SELECT DISTINCT r.path FROM chunk_registry r LEFT JOIN chunks_{table_name} c "
                f"ON c.chunk_id=r.chunk_id LEFT JOIN vectors_{table_name} v ON v.chunk_id=c.id "
                "WHERE r.table_name=? AND (c.id IS NULL OR v.chunk_id IS NULL)", (table_name,)))

    finally:
        conn.close()
    return (file_meta_paths - canonical_paths) | (missing_vectors & file_meta_paths)


def _reap_stranded_vector_rows(
    db_path: Path,
    eligible_paths: set[str],
    *,
    root: Path,
    tables: tuple[str, ...] = ("docs", "code"),
    verbose: bool = False,
    eligible_by_table: "dict[str, set[str]] | None" = None,
    plan_only: bool = False,
    precomputed_stranded: "dict[str, set[str]] | None" = None,
    unreadable_dirs: "set[str] | None" = None,
    prepared=None,
) -> dict:
    """Delete canonical rows whose ``path`` is not in the current eligible set.

    Closes the workflow-config-evolution blind spot: when ``workflow-config.json``
    narrows include-prefixes, the next incremental update drops the now-ineligible
    paths from the build snapshot (via ``_detect_changes``), but only paths that were
    *still in old_meta when the narrowing was detected* get evicted from canonical storage.
    Subsequent incrementals never see those paths in ``old_meta`` again, so their
    canonical rows orphan silently until a full rebuild.

    This reaper reconciles the *current* canonical row set against the *current*
    eligible set on every incremental update, regardless of meta state. It is
    set-difference + a single batched DELETE per table, plus (1u8o3) one
    ``stat`` per stranded candidate the walk did not already explain.

    Wave 1x54z (1u8o3) — absence guards. Every stranded candidate is classified
    before it is deleted, through the seam the ``1u8nz`` orphan reconciliation
    already uses (``_classify_orphan_path`` / ``_orphan_path_stat``):
    ``absent`` (ENOENT/ENOTDIR) and ``present`` (on disk but out of scope, the
    narrowing case this reap exists for) reap as before; ``unreadable`` (any
    other OSError) preserves the rows AND, because callers clean layer state
    only for what was reaped, the layer hashes. A candidate under a directory
    the walk reported unreadable (``unreadable_dirs``, from ``walk_repo``) is
    ``unreadable`` without a stat, and that is the correctness path rather than
    a shortcut: a directory with search-but-no-read permission fails
    ``scandir`` while ``stat`` on its children still succeeds, so stat-only
    classification would read them as ``present`` and reap them as a scope
    departure. The ``absent`` remainder then passes the ``1u8nz`` mass-removal
    breaker, same constants, same unit (distinct paths): at least
    ``ORPHAN_RECONCILE_BREAKER_MIN_ROWS`` absent paths AND more than
    ``ORPHAN_RECONCILE_BREAKER_FRACTION`` of the table's distinct paths defers
    those absent paths loudly, so a transiently invisible subtree (an
    unmounted volume reads as ENOENT) cannot cascade into wholesale deletion
    and a forced re-embed; ``present`` candidates never count toward the
    breaker and reap whatever their number, because a stat-confirmed scope
    departure is positive evidence, not transient invisibility (delivery
    review RED-DEL-2). Both guards live in the scanning branch, which is what
    the zero-change preflight (``plan_only=True``) and the build-path seam
    run; the zero-change execute step replays the preflight's
    ``paths_by_table`` (``precomputed_stranded``), so it cannot reap what the
    plan refused. Boundary: at the build-path seam the incremental semantic write
    deletes the ``removed`` set before this reap runs, so a first-time mass
    absence with no walk error (an unmounted volume on its first build) is
    removed there and never reaches the breaker; the breaker protects rows
    whose bookkeeping an earlier build already dropped, at either seam.
    Deferred rows stay searchable until newly indexed files dilute the
    fraction under the breaker or the operator rebuilds once the volume is
    readable again (``index_build(content='all', mode='rebuild')``; a rebuild
    during the outage drops the subtree); the deferral is reported to the
    caller as ``stranded_reap_deferred``. The same accepted posture as the
    sidecar breaker, recorded in the change doc.

    Returns ``{"docs": N, "code": M, "total": N+M, "paths_by_table": {...},
    "preserved_by_table": {...}, "deferred_by_table": {...}}``: row counts
    reaped per table, the distinct paths reaped (or planned), the distinct
    paths preserved as unreadable, and per deferred table
    ``{"would_reap", "table_paths", "paths"}``.
    """
    reaped: dict[str, int] = {"docs": 0, "code": 0, "total": 0}
    reaped_paths: dict[str, set[str]] = {"docs": set(), "code": set()}
    preserved_paths: dict[str, set[str]] = {"docs": set(), "code": set()}
    deferred_by_table: dict[str, dict] = {}
    reaped["paths_by_table"] = reaped_paths
    reaped["preserved_by_table"] = preserved_paths
    reaped["deferred_by_table"] = deferred_by_table
    # One classification per distinct candidate, shared across tables (the
    # same path can hold rows in both), mirroring the 1u8nz reconciliation.
    classification: dict[str, str] = {}
    if not (db_path / vector_store.FILENAME).exists():
        return reaped
    for table_name in tables:
        vector_store._layer(table_name)
        try:
            if precomputed_stranded is not None:
                # 1sed6: execute a previously planned reap without re-scanning
                # (the zero-change path plans read-only FIRST, opens the build
                # epoch only when work exists, then executes).
                stranded = set(precomputed_stranded.get(table_name) or set())
            else:
                # Pull just the path column to keep the read cheap on large tables.
                conn = _get_index_state_store().open_read_only(db_path)
                try:
                    canonical_paths = {r[0] for r in conn.execute(f"SELECT DISTINCT path FROM chunks_{table_name}") if r[0]}
                finally:
                    conn.close()
                # 1sek8: per-table eligibility when provided — one corpus
                # definition per table (the migration reap of previously-included
                # test chunks flows through here, loudly).
                _eligible = eligible_paths
                if eligible_by_table is not None and table_name in eligible_by_table:
                    _eligible = eligible_by_table[table_name]
                stranded = canonical_paths - _eligible
                if stranded:
                    # 1u8o3 guard 1: classify before deleting; unreadable preserves.
                    for rel in stranded:
                        if rel in classification:
                            continue
                        if _shadowed_by_unreadable(rel, unreadable_dirs):
                            classification[rel] = "unreadable"
                        else:
                            classification[rel] = _classify_orphan_path(root, rel)
                    unreadable_here = {rel for rel in stranded if classification[rel] == "unreadable"}
                    if unreadable_here:
                        preserved_paths[table_name] = unreadable_here
                        stranded = stranded - unreadable_here
                        msg = (
                            f"build_index: reaper {table_name} — preserved {len(unreadable_here)} "
                            "unreadable path(s) (an unreadable parent directory or an IO error at "
                            "the stat seam, not evidence of deletion); rows and layer hashes kept "
                            "until the path is readable or provably gone"
                        )
                        print(msg, file=sys.stderr, flush=True)
                        _store_log_safe(db_path, msg)
                if stranded:
                    # 1u8o3 guard 2: the 1u8nz mass-removal breaker, in distinct
                    # paths, over the ABSENT candidates only (delivery review
                    # RED-DEL-2). ``present`` is a stat-confirmed scope departure,
                    # the case this reap exists for, and reaps whatever its
                    # count; ``absent`` is the only class an unmounted volume or
                    # a torn walk can produce in bulk, so it alone can trip the
                    # breaker. A deferred table keeps its absent rows searchable
                    # until the fraction dilutes or the operator rebuilds.
                    absent_here = {rel for rel in stranded if classification[rel] == "absent"}
                    table_paths = len(canonical_paths)
                    would_reap = len(absent_here)
                    if (
                        would_reap >= ORPHAN_RECONCILE_BREAKER_MIN_ROWS
                        and would_reap > ORPHAN_RECONCILE_BREAKER_FRACTION * table_paths
                    ):
                        deferred_by_table[table_name] = {
                            "would_reap": would_reap,
                            "table_paths": table_paths,
                            "paths": set(absent_here),
                        }
                        msg = (
                            f"build_index: reaper DEFERRED for {table_name}: {would_reap} of "
                            f"{table_paths} indexed path(s) are absent from disk, over the "
                            f"mass-removal circuit breaker (>{ORPHAN_RECONCILE_BREAKER_FRACTION:.0%} "
                            f"and >={ORPHAN_RECONCILE_BREAKER_MIN_ROWS}); their rows are kept this "
                            "build so a transiently invisible subtree (an unmounted volume, a torn "
                            "walk) cannot cascade into wholesale deletion and a forced re-embed, and "
                            "they stay searchable until newly indexed files dilute the fraction "
                            "under the breaker. If the paths really are gone, rebuild from the "
                            "current corpus once every directory and volume is readable again: "
                            "index_build(content='all', mode='rebuild') (a rebuild during the "
                            "outage drops the subtree and re-embeds it on recovery). The deferral "
                            "is reported as stranded_reap_deferred in the build result."
                        )
                        print(msg, file=sys.stderr, flush=True)
                        _store_log_safe(db_path, msg)
                        stranded = stranded - absent_here
            if not stranded:
                continue
            if plan_only:
                # Read-only preflight (1sed6 Req 8): report what WOULD reap;
                # no deletion, no epoch required.
                reaped_paths[table_name] = set(stranded)
                continue
            # Count rows-to-delete (not unique paths) for accurate operator signal.
            reaped_here = _count_chunks_for_paths(db_path, table_name, stranded)
            if prepared is not None:
                prepared.add(table_name, paths=stranded)
            else:
                store = _get_index_state_store().IndexStateStore(db_path)
                try:
                    with store._conn:
                        _get_index_state_store()._apply_chunk_deltas_locked(store, table_name, delete_paths=stranded)
                        store._conn.executemany("DELETE FROM layer_path_state WHERE layer=? AND path=?",
                                                ((table_name,p) for p in stranded))
                finally:
                    store.close()
            reaped[table_name] = reaped_here
            reaped["total"] += reaped_here
            reaped_paths[table_name] = set(stranded)
            if verbose:
                print(
                    f"build_index: reaper {table_name} — {len(stranded)} stranded path(s), "
                    f"{reaped_here} row(s) reaped",
                    flush=True,
                )
            if reaped_here:
                # 1sek8: persist the reap — corpus-migration reaps (e.g.
                # previously-included test chunks after unification) must be
                # auditable after the build process exits.
                _store_log_safe(
                    db_path,
                    f"build_index: reaper {table_name} — {len(stranded)} stranded path(s), "
                    f"{reaped_here} row(s) reaped",
                )
        except Exception as exc:
            raise RuntimeError(f"Canonical reaper {table_name} failed; previous data preserved: {exc}") from exc
    return reaped


def _cleanup_layer_state_for_reaped(index_dir: Path, reaped_paths: "dict[str, set[str]]") -> None:
    """Drop layer-state rows for paths whose canonical rows were just reaped (1sek8).

    Without this, a path reaped by eligibility narrowing that later becomes
    eligible again with an UNCHANGED hash would compare current against its
    stale layer state and be skipped — indexed-per-state but missing canonical rows.
    Best-effort: a miss is caught by the drift detector on a later build.
    """
    if not reaped_paths:
        return
    iss = _get_index_state_store()
    if iss is None:
        return
    for layer, paths in reaped_paths.items():
        if not paths:
            continue
        try:
            iss.update_layer_hashes(index_dir, layer, remove_paths=paths)
        except Exception:  # noqa: BLE001 - drift detection is the backstop
            pass


# --- 1u8nz: orphan-store reconciliation at the reap seam ---
# Store rows orphaned from the registry (out-of-band deletions, older-pack
# residue) were never reconciled on incremental builds for the graph store and
# the file_freshness / secret_scan_cache sidecars: graph removal only ran when
# a build had real merge work, and the sidecars had no store-minus-authority
# pass at all. The reconciliation below runs inside the build epoch at the
# existing reap seam (read-only plan first, mutations only under the epoch).
#
# Mass-removal circuit breaker: a reconcile defers (does nothing, loudly) when
# it would remove MORE than ORPHAN_RECONCILE_BREAKER_FRACTION of a store's
# rows AND at least ORPHAN_RECONCILE_BREAKER_MIN_ROWS rows, because a transiently
# invisible subtree (unmounted volume, torn walk) must not cascade into
# wholesale retirement. Small stores stay under the floor so ordinary
# deletions on small repos reconcile normally.
ORPHAN_RECONCILE_BREAKER_FRACTION = 0.5
ORPHAN_RECONCILE_BREAKER_MIN_ROWS = 8

_ORPHAN_RECONCILE_STORES = ("file_freshness", "secret_scan_cache", "graph")


def _orphan_path_stat(path: Path):
    """The stat seam for orphan classification.

    A discrete injection point: tests exercise the EACCES/EIO preservation
    branch by patching this function (error injection at the stat seam), never
    by filesystem chmod, which is vacuous under root and flaky across
    platforms.
    """
    return os.stat(path)


def _classify_orphan_path(root: Path, rel: str) -> str:
    """Classify one candidate orphan path: 'present' | 'absent' | 'unreadable'.

    ENOENT (and ENOTDIR, its path-prefix variant) is positive evidence of
    deletion; every other OSError (EACCES, EIO, ...) reads as 'unreadable'
    and PRESERVES the row (conservative on IO errors).
    """
    try:
        _orphan_path_stat(root / rel)
        return "present"
    except (FileNotFoundError, NotADirectoryError):
        return "absent"
    except OSError:
        return "unreadable"


def _plan_orphan_store_reconcile(
    root: Path,
    index_dir: Path,
    authority: set[str],
    *,
    verbose: bool = False,
    unreadable_dirs: "set[str] | None" = None,
) -> dict:
    """Read-only reconciliation plan (no epoch, no mutation) for the orphan stores.

    ``authority`` is the same registry/walk state the canonical reap uses
    (``current_file_meta`` keys: on-disk AND in-scope, or, since wave 1x54z,
    previously indexed and shadowed by a directory the walk could not read
    this build, which change detection carries forward as unchanged). A
    candidate under such a directory (``unreadable_dirs``, from ``walk_repo``)
    classifies ``unreadable`` without a stat, so this plan and the canonical reap
    apply one policy to the same paths (1x54z delivery review RED-DEL-3).
    Removal semantics per store:

    - ``file_freshness`` and ``graph``: rows exist only for corpus paths, so a
      row outside the authority retires whether the file is deleted OR still
      present but scope-departed, parity with the shipped canonical eligibility
      reap (scope-narrowing config changes then delete on the next build,
      which is the documented corpus-membership semantics).
    - ``secret_scan_cache``: the standalone secrets scanner's candidate set is
      ALL tracked files, intentionally wider than the index corpus, so a
      present-but-out-of-index-scope row is a LEGITIMATE cache entry. Only
      disk-absent ('absent') rows retire.
    - 'unreadable' always preserves.

    Structural cost: one set-membership check per store row, then at most ONE
    ``os.stat`` per unique candidate (shared classification cache across
    stores); no directory traversal of any kind.
    """
    plan: dict = {
        "file_freshness": set(),
        "secret_scan_cache": set(),
        "graph": set(),
        "deferred": {},
        "stat_calls": 0,
    }
    iss = _get_index_state_store()
    if iss is None or not hasattr(iss, "orphan_store_paths"):
        return plan
    try:
        store_paths = iss.orphan_store_paths(index_dir)
    except Exception:  # noqa: BLE001 - unreadable store means no candidates
        return plan
    candidates_by_store = {
        store: set(store_paths.get(store) or set()) - authority
        for store in _ORPHAN_RECONCILE_STORES
    }
    classification: dict[str, str] = {}
    for store, candidates in candidates_by_store.items():
        for rel in candidates:
            if rel in classification:
                continue
            if _shadowed_by_unreadable(rel, unreadable_dirs):
                classification[rel] = "unreadable"
                continue
            classification[rel] = _classify_orphan_path(root, rel)
            plan["stat_calls"] += 1
    for store, candidates in candidates_by_store.items():
        allowed = ("absent",) if store == "secret_scan_cache" else ("absent", "present")
        removable = {rel for rel in candidates if classification[rel] in allowed}
        if not removable:
            continue
        store_rows = len(store_paths.get(store) or set())
        would_remove = len(removable)
        if (
            would_remove >= ORPHAN_RECONCILE_BREAKER_MIN_ROWS
            and would_remove > ORPHAN_RECONCILE_BREAKER_FRACTION * store_rows
        ):
            plan["deferred"][store] = {
                "would_remove": would_remove,
                "store_rows": store_rows,
            }
            # Operator consequence (accepted, recorded in the 1u8nz change
            # doc): secret_scan_cache has no alternative healer, so a
            # mass-orphaned cache defers indefinitely on a static corpus;
            # deferral is loud and has no silent data effect.
            msg = (
                f"build_index: orphan reconcile DEFERRED for {store}: would remove "
                f"{would_remove} of {store_rows} row(s), over the mass-removal "
                f"circuit breaker (>{ORPHAN_RECONCILE_BREAKER_FRACTION:.0%} and "
                f">={ORPHAN_RECONCILE_BREAKER_MIN_ROWS}); leaving the store "
                "untouched this build; this deferral repeats each build until "
                "newly indexed files dilute the would-remove fraction under the "
                "breaker, and for secret_scan_cache (no alternative healer) a "
                "mass-orphaned cache defers indefinitely on a static corpus"
            )
            print(msg, file=sys.stderr, flush=True)
            _store_log_safe(index_dir, msg)
            continue
        plan[store] = removable
    return plan


def _execute_orphan_store_reconcile(
    root: Path,
    index_dir: Path,
    plan: dict,
    *,
    files_for_graph: "list[Path] | None" = None,
    current_file_meta: "dict[str, dict] | None" = None,
    graph_layer: str = "project",
    chunker_version: str = "",
    verbose: bool = False,
    unreadable_dirs: "set[str] | None" = None,
    state_conn=None,
) -> dict:
    """Execute a previously planned orphan-store reconciliation.

    MUST run inside an open build epoch (both call sites in
    ``_build_index_locked`` are after ``begin_build_epoch``). Best-effort per
    store, same posture as the freshness resident: a failed removal logs and
    leaves the orphans for the next build's plan to re-detect.
    """
    stats = {"file_freshness": 0, "secret_scan_cache": 0, "graph": 0}
    iss = _get_index_state_store()
    fresh = set(plan.get("file_freshness") or set())
    secret = set(plan.get("secret_scan_cache") or set())
    if iss is not None and (fresh or secret):
        try:
            deleted = iss.remove_sidecar_paths(index_dir, freshness_paths=fresh, secret_scan_paths=secret)
            stats["file_freshness"] = deleted.get("file_freshness", 0)
            stats["secret_scan_cache"] = deleted.get("secret_scan_cache", 0)
            removed_total = stats["file_freshness"] + stats["secret_scan_cache"]
            if removed_total:
                msg = (
                    "build_index: orphan reconcile removed sidecar rows: "
                    f"file_freshness={stats['file_freshness']} "
                    f"secret_scan_cache={stats['secret_scan_cache']}"
                )
                if verbose:
                    print(msg, flush=True)
                _store_log_safe(index_dir, msg)
        except Exception as exc:  # noqa: BLE001 - next build's plan re-detects
            print(
                f"build_index: orphan reconcile sidecar removal failed ({exc}); "
                "rows preserved; the next build re-plans",
                file=sys.stderr,
                flush=True,
            )
    graph_orphans = set(plan.get("graph") or set())
    if graph_orphans and files_for_graph is not None and current_file_meta is not None:
        try:
            graph_indexer = _get_graph_indexer()
            graph_cluster = _get_graph_cluster()
            payload = graph_indexer.retire_orphaned_graph_paths(
                root=root,
                index_dir=index_dir,
                layer=graph_layer,
                files=files_for_graph,
                current_file_meta=current_file_meta,
                walker_version=WALKER_VERSION,
                chunker_version=chunker_version,
                unreadable_dirs=unreadable_dirs,
                verbose=verbose,
                state_conn=state_conn,
            )
            if isinstance(payload, dict):
                payload.pop("merge_stats", None)
                publication = payload.pop("_publication", None)
                cluster_payload = graph_cluster.update_graph_clusters(
                    root=root,
                    index_dir=index_dir,
                    layer=graph_layer,
                    graph_payload=payload,
                    verbose=verbose,
                    state_conn=state_conn,
                )
                cluster_publication = (
                    cluster_payload.pop("_publication", None)
                    if isinstance(cluster_payload, dict) else None
                )
                if publication is not None:
                    # Retirement rows join the CALLER's publication
                    # transaction rather than committing on their own.
                    if cluster_publication is not None:
                        publication.community = cluster_publication
                    stats["graph_publication"] = {
                        "publication": publication,
                        "graph_payload": payload,
                        "cluster_payload": cluster_payload,
                        "cluster_recomputed": cluster_publication is not None,
                    }
            # stats["graph"] reports the PLANNED count (the plan's graph set);
            # the walk-parity merge may prune more store-minus-walk paths.
            stats["graph"] = len(graph_orphans)
            msg = (
                f"build_index: orphan reconcile retired {len(graph_orphans)} planned "
                "graph path(s) through the merge (the walk-parity merge may prune more)"
            )
            if verbose:
                print(msg, flush=True)
            _store_log_safe(index_dir, msg)
        except Exception as exc:  # noqa: BLE001 - next build's plan re-detects
            print(
                f"build_index: orphan reconcile graph retirement failed ({exc}); "
                "rows preserved; the next build re-plans",
                file=sys.stderr,
                flush=True,
            )
    return stats


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


def _plan_vector_delta_rows(
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
                rows_to_add.append(_make_vector_rows([chunk], [vector])[0])
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
                rows_to_add.append(_make_vector_rows([chunk], [vector])[0])
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
        embedded_rows = _make_vector_rows(chunks_to_embed, vecs)
        for pos, row in zip(chunk_positions, embedded_rows):
            rows_to_add[pos] = row

    rows_to_add = [row for row in rows_to_add if row]
    return delete_ids, rows_to_add, False, {
        "written": len(rows_to_add),
        "removed": len(delete_ids),
        "unchanged": unchanged,
    }


def _count_chunks_for_paths(db_path: Path, table_name: str, paths: set[str]) -> int:
    vector_store._layer(table_name)
    if not paths:
        return 0
    conn = _get_index_state_store().open_read_only(db_path)
    if conn is None:
        return 0
    try:
        return sum(conn.execute(f"SELECT COUNT(*) FROM chunks_{table_name} WHERE path=?", (p,)).fetchone()[0] for p in paths)
    finally:
        conn.close()


def _prepare_incremental_vectors(db_path: Path, stale: set[str], new_doc_chunks: list[dict],
        docs_embedder, new_code_chunks: list[dict], code_embedder, build_docs: bool,
        build_code: bool, verbose=False, skip_exempt=None, written_paths=None, prepared=None):
    """Prepare per-file deltas and reuse unchanged embeddings; publication is caller-owned."""
    if prepared is None:
        raise ValueError("Semantic updates require a prepared publication spool")
    for layer, enabled, chunks, embedder, label in (
        ("docs",build_docs,new_doc_chunks,docs_embedder,"doc"),
        ("code",build_code,new_code_chunks,code_embedder,"code")):
        if not enabled:
            continue
        by_path = {}
        for chunk in chunks:
            by_path.setdefault(str(chunk.get("path") or ""), []).append(chunk)
        registry = _get_index_state_store().registry_map_for_paths(db_path, layer, stale)
        for path in sorted(stale):
            fresh = by_path.get(path, [])
            new_map = {str(c.get("id") or ""): _chunk_hash(c) for c in fresh}
            if (new_map and registry.get(path) == new_map and not (skip_exempt and path in skip_exempt)
                    and not os.environ.get("WAVEFOUNDRY_DISABLE_REGISTRY_INCREMENTAL")):
                _log_semantic_file_delta(path,layer,{"written":0,"removed":0,"unchanged":len(new_map)})
                continue
            existing = _read_vector_rows_for_paths(db_path, layer, {path})
            ids, rows, fallback, stats = _plan_vector_delta_rows(
                existing_rows=existing, new_chunks=fresh, embedder=embedder, label=label)
            if fallback:
                vectors = _embed_chunks_for_incremental(label, fresh, embedder) if fresh else []
                prepared.add(layer, paths=[path], rows=_make_vector_rows(fresh, vectors))
            else:
                prepared.add(layer, ids=ids, rows=rows)
            _log_semantic_file_delta(path, layer, stats)
        if written_paths is not None:
            written_paths[layer] = set(stale)


def rebuild_derived_chunk_state(index_dir: Path, verbose: bool = False) -> dict:
    """Repair FTS5 and registry from canonical chunks without altering vectors.

    The operator-facing from-scratch recovery behind
    ``index_build(content='fts')``: drops and repopulates each table's
    FTS/registry rows from the canonical chunk tables, records fresh sync counts, and clears the
    cold flag. Derived-only and embedding-free — seconds, not minutes.
    Caller holds the index-build lock.
    """
    iss = _get_index_state_store()
    if iss is None:
        return {"error": "index-state store module unavailable"}
    # Review fix: this is a derived-state maintenance verb — it may only
    # restore readiness a real build already published. On an uninitialized,
    # building, or reset store, finalizing here would manufacture a
    # `complete` epoch around empty/unknown canonical state (the reproduced
    # empty-FTS false completion). Refuse; a real build owns first readiness.
    _prior = iss.read_build_state(index_dir)
    if not _prior or _prior.get("status") != "complete":
        return {"error": (
            "no completed build epoch — the derived FTS rebuild can only run over "
            "a published index; run a build first (index_build)"
        )}
    attempt = iss.begin_build_epoch(index_dir, "fts:derived-rebuild")
    stats = _sync_chunk_derived_state(index_dir, expected=True, verbose=verbose, force=True)
    errors = {k: v.get("error") for k, v in stats.items() if isinstance(v, dict) and v.get("error")}
    if errors:
        # Leave the epoch un-finalized: readers fail closed rather than
        # trusting a half-rebuilt derived layer (1sed6 Req 2).
        return stats
    if not iss.finalize_build_epoch(index_dir, attempt):
        stats["finalize"] = {"error": "epoch finalization CAS miss"}
        return stats
    _remove_legacy_meta_json(index_dir)
    return stats


def _chunk_index_needs_heal(index_dir: Path) -> bool:
    if not (index_dir / vector_store.FILENAME).exists():
        return False
    iss = _get_index_state_store()
    if iss.chunk_index_is_cold(index_dir):
        return True
    for layer, count in vector_store.layer_counts(index_dir).items():
        if count != iss.registry_chunk_count(index_dir,layer):
            return True
        verdict = iss.fts_state_verdict(index_dir,layer)
        if not verdict.get("ok"):
            return True
    return False


def _sync_chunk_derived_state(index_dir: Path, *, expected=False, verbose=False, force=False) -> dict:
    iss = _get_index_state_store()
    stats = {}
    for layer in ("docs", "code"):
        try:
            count = vector_store.layer_counts(index_dir)[layer]
            store = iss.IndexStateStore(index_dir)
            try:
                store._conn.execute("BEGIN IMMEDIATE")
                verdict = iss.fts_state_verdict(index_dir, layer, _writer_conn=store._conn)
                needs_repair = force or not verdict.get("ok")
                if needs_repair:
                    store._conn.execute("ROLLBACK")
                    iss.rebuild_chunk_index(index_dir, layer, [])
                    store._conn.execute("BEGIN IMMEDIATE")
                with store._conn:
                    store.set_meta({iss.META_CHUNK_INDEX_COLD: "0"})
                    if needs_repair and not verdict.get("ok"):
                        epoch = store._conn.execute("SELECT attempt_id FROM build_state WHERE id=1").fetchone()
                        if epoch:
                            store.set_meta({iss.META_FTS_HEAL_ATTEMPT_PREFIX + layer: epoch[0]})
                    # Compatibility metadata for the public coverage report, now one engine.
                    store.set_meta({iss.META_CHUNK_SYNC_RAW_PREFIX + layer: str(count)})
                    store.set_meta({iss.META_CHUNK_SYNC_UNIQUE_PREFIX + layer: str(count)})
                store._conn.execute("COMMIT")
            finally:
                store.close()
            stats[layer] = {"reconciled": bool(needs_repair), "rows_written": count if needs_repair else 0,
                            "fts_repaired": bool(needs_repair and not verdict.get("ok")),
                            "fts_reason": verdict.get("reason")}
        except Exception as exc:
            stats[layer] = {"error": str(exc)}
    return stats


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
            from runtime_lock import probe_runtime_lock

            probe = probe_runtime_lock(
                lock_path,
                offset=INDEX_BUILD_LOCK_SENTINEL,
                style="record",
            )
            return (probe.held, None)
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


# Wave 1t72b (1t727, TOCTOU repair revised): defense-in-depth exclusion
# against the framework test suite. A build requested while run_tests.py holds
# test-run.lock DEFERS (bounded wait) instead of racing the suite. Atomicity
# discipline: the test-lock check runs while HOLDING the build lock (so the
# suite's post-acquire re-probe always observes a committed build), but the
# build never WAITS while holding — a deferring build must not present as
# running to status tools or other waiters (live-caught: a deferring
# hook-spawned build made unit tests wait 600s on a phantom build). On a held
# test lock the build releases, waits unlocked, and retries; the final cycle
# proceeds regardless — deferral is never cancellation.
_TEST_RUN_WAIT_SECONDS = 900
_TEST_RUN_POLL_SECONDS = 3.0
_TEST_RUN_MAX_YIELD_CYCLES = 3
_TEST_RUN_PROBE = None  # test seam; defaults to the runtime_lock probe
_TEST_RUN_LOCK_SENTINEL = 1 << 30  # mirrors run_tests._LOCK_BYTE_OFFSET


def _test_run_lock_path(index_dir: Path) -> Path:
    return index_dir.parent.parent / ".wavefoundry" / "framework" / "test-run.lock"


def _test_run_lock_held(index_dir: Path) -> bool:
    """One non-destructive probe; undetermined resolves to not-held."""
    probe = _TEST_RUN_PROBE
    if probe is None:
        def probe(path: Path):
            from runtime_lock import probe_runtime_lock

            if os.name == "nt":
                return probe_runtime_lock(
                    path, offset=_TEST_RUN_LOCK_SENTINEL, style="record"
                ).held
            return probe_runtime_lock(path, style="flock").held
    try:
        return bool(probe(_test_run_lock_path(index_dir)))
    except Exception:  # noqa: BLE001 — the guard must never break a build
        return False


def _wait_for_test_run_release(index_dir: Path) -> None:
    """Bounded UNLOCKED wait for the suite to finish; always returns."""
    deadline = time.monotonic() + _TEST_RUN_WAIT_SECONDS
    print(
        "build_index: deferred — the framework test suite is running "
        f"(test-run.lock held at {_test_run_lock_path(index_dir)}); waiting "
        f"up to {_TEST_RUN_WAIT_SECONDS}s without holding the build lock …",
        file=sys.stderr,
    )
    while time.monotonic() < deadline:
        if not _test_run_lock_held(index_dir):
            return
        time.sleep(_TEST_RUN_POLL_SECONDS)
    print(
        "build_index: test run still active after "
        f"{_TEST_RUN_WAIT_SECONDS}s; proceeding (deferral is not "
        "cancellation; the OS build lock remains the authority)",
        file=sys.stderr,
    )


@contextmanager
def _index_build_lock(index_dir: Path):
    """Acquire the whole-index build lock for ``index_dir``.

    The file is metadata only; the OS-held lock is the authority. Keeping the
    file in place lets status tools inspect the last owner without making
    cleanup correctness depend on unlinking after a crash.
    """
    lock_path = index_dir / INDEX_BUILD_LOCK_NAME
    from runtime_lock import RuntimeFileLock, RuntimeLockBusy

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
    lock = None
    lock_meta: Optional[dict] = None
    try:
        for _yield_cycle in range(_TEST_RUN_MAX_YIELD_CYCLES + 1):
            lock = RuntimeFileLock(
                lock_path,
                blocking=False,
                offset=INDEX_BUILD_LOCK_SENTINEL,
                style="record",
            )
            try:
                lock.acquire()
            except RuntimeLockBusy as exc:
                raise IndexBuildAlreadyRunning(
                    format_index_build_lock_conflict(index_dir, lock_path=lock_path)
                ) from exc
            # Wave 1t72b (1t727 TOCTOU repair, revised): the test-lock check
            # happens while HOLDING the build lock (atomic with ownership),
            # but the build never waits while holding — on a held test lock it
            # releases, waits UNLOCKED, and retries. The final cycle proceeds
            # regardless (deferral is never cancellation).
            if _yield_cycle >= _TEST_RUN_MAX_YIELD_CYCLES or not _test_run_lock_held(
                index_dir
            ):
                break
            lock.release()
            lock = None
            _wait_for_test_run_release(index_dir)

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
        lock.write_metadata(lock_meta)
        yield
    finally:
        if lock is not None and lock.acquired:
            if lock_meta is not None:
                try:  # best-effort ended_at; a hard kill skips it → status sees an interrupted build
                    lock_meta["ended_at"] = time.time()
                    lock.write_metadata(lock_meta)
                except Exception:  # noqa: BLE001
                    pass
            try:
                lock.release()
            except OSError:
                pass


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
    return value.split("@", 2)[1]


def _model_set_fingerprint_from_version(value: Optional[str]) -> str:
    return value.split("@", 2)[2] if value and value.count("@") >= 2 else ""


# Wave 1v454: the INT8 encoding policy is part of what a stored int8 vector MEANS. Single-row
# encoding changed those vectors (the old batched path let a row's per-tensor activation scale
# depend on its batch neighbours), so an existing int8 index must re-embed exactly once.
# A full-class index must NOT: the FP graphs carry no quantization ops and were measured
# composition-invariant, so their vectors did not move. EMBEDDING_MODEL_SET_FINGERPRINT is
# deliberately an ALL-LAYER compatibility boundary (see the scoped-update guard in build_index),
# so bumping it would re-embed every GPU host for a defect they never had. Scoping the revision to
# the int8 class keeps the one-time cost on the pipeline that actually changed.
INT8_ENCODING_REVISION = "int8enc2"


def _identity_fingerprint_for_class(precision_class: str) -> str:
    """Return the model-set fingerprint recorded for a layer at ``precision_class``.

    Compare sites and the write site MUST both route through this helper, or a same-machine
    incremental build would perpetually re-embed (the compare would keep seeing a mismatch it
    just wrote) -- the same invariant `_predicted_precision_class` documents for the class token.
    """
    if precision_class == "int8":
        return f"{EMBEDDING_MODEL_SET_FINGERPRINT}-{INT8_ENCODING_REVISION}"
    return EMBEDDING_MODEL_SET_FINGERPRINT


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


def _resolve_build_embedders(
    *,
    build_docs: bool,
    build_code: bool,
    full: bool,
    docs_chunk_count: int,
    code_chunk_count: int,
) -> tuple[Any, Any]:
    """Resolve per-layer embedders, sharing only when configured IDs match."""
    docs_need = build_docs and (full or docs_chunk_count > 0)
    code_need = build_code and (full or code_chunk_count > 0)
    docs_embedder = None
    code_embedder = None
    if docs_need and code_need and DOCS_MODEL == CODE_MODEL:
        shared_count = None if full else max(docs_chunk_count, code_chunk_count)
        docs_embedder = _get_embedder(DOCS_MODEL, n_chunks=shared_count)
        code_embedder = docs_embedder
        return docs_embedder, code_embedder
    if docs_need:
        docs_embedder = _get_embedder(
            DOCS_MODEL, n_chunks=None if full else docs_chunk_count
        )
    if code_need:
        code_embedder = _get_embedder(
            CODE_MODEL, n_chunks=None if full else code_chunk_count
        )
    return docs_embedder, code_embedder

# Wave 1p938: route an incremental embed run smaller than one full GPU batch to the full-precision
# CPU fastembed path instead of constructing the 32x512 GPU accel session — the GPU only amortizes
# its fixed dispatch cost over a large batch (measurement B, ADR 1p92d); a handful of chunks padded
# into a 32-row batch loses to plain CPU. Default = accel_embedder.STATIC_BATCH (one full GPU
# batch), so a bulk/full build (>= threshold chunks) still uses GPU unchanged (AC-2).
INCREMENTAL_GPU_MIN_CHUNKS = accel_embedder.STATIC_BATCH if accel_embedder is not None else 32


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
        if accel_embedder._coreml_static_probe_cache.get(
            ("embedder", model_name)
        ) is False:
            # The exact production static graph crashed or failed in its
            # isolated child. Keep the full-precision fallback, but force its
            # ONNX provider to CPU so the rejected CoreML provider cannot be
            # re-entered through fastembed in this process.
            providers = ["CPUExecutionProvider"]
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
        # 1v4mu: worded as a deliberate optimization. Field-reported: read next to
        # the CoreML degradation WARNING, the previous phrasing looked like a
        # second GPU fault, and the reporter conflated the two.
        print(f"build_index: OPTIMIZATION (not a failure): {n_chunks} chunk(s) is below the "
              f"one-full-batch threshold ({INCREMENTAL_GPU_MIN_CHUNKS}), so this small run "
              f"deliberately uses the CPU embedder for {model_name}. Constructing a GPU accel "
              "session costs more than it saves at this size; GPU use is unchanged for "
              "larger runs.", flush=True)
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
    literal token) — and it is the path every named launcher (MCP ``index_build``, the dashboard
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
    # doc-code (1whup): extracted fences/directive bodies from doc-family files
    # route to the DOCS table — docs files are never code-eligible, so without
    # this membership the per-table eligibility gate drops them from BOTH tables.
    return kind in ("doc", "seed", "prompt", "doc-summary", "doc-code")


_MEMORY_RECORD_PREFIX = "docs/agents/memory/"


def _memory_record_touched(changed: Iterable[str], removed: Iterable[str]) -> bool:
    """True iff this build actually CHANGED or REMOVED an agent-memory record.

    Gates the memory-generation bump (wave 1ro44 / 1p8gy) on the changed/
    removed sets — never all indexed files — so unrelated or zero-change builds
    do not needlessly advance the generation and force an advisory reparse
    (delivery-review efficiency finding). The `docs/agents/memory/README.md`
    schema doc is not a record and is ignored.
    """
    for p in list(changed) + list(removed):
        s = str(p).replace("\\", "/")
        if s.startswith(_MEMORY_RECORD_PREFIX) and not s.endswith("/README.md"):
            return True
    return False


# We cache the chunker module after first load
_chunker_mod = None
_graph_indexer_mod = None
_graph_cluster_mod = None
_secrets_scanner_mod = None
_index_state_store_mod = None

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


def _get_index_state_store():
    """Load the index-state store module (wave 1rsh9 / 1rq4h) — cached, optional.

    Returns None when the module file is absent (older extracted pack) so the
    build degrades to no-freshness-sidecar without errors.
    """
    global _index_state_store_mod
    if _index_state_store_mod is None:
        import importlib.util
        store_path = Path(__file__).resolve().parent / "index_state_store.py"
        if not store_path.exists():
            return None
        spec = importlib.util.spec_from_file_location("index_state_store", store_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["index_state_store"] = mod
        spec.loader.exec_module(mod)
        _index_state_store_mod = mod
    return _index_state_store_mod



# Per-layer publication statuses recorded by ``build_layer_state``.
LAYER_PUBLISHED = "published"
LAYER_STALE = "stale"


def _layer_publication_state(
    *,
    build_docs: bool,
    build_code: bool,
    graph_published: bool,
    graph_sources_changed: bool,
) -> "dict[str, str]":
    """Which layers this build publishes, and which it must mark stale.

    The rule the change doc states, encoded once so both build paths and the
    tests read the same function:

    * a layer this build published gets ``published`` at this generation;
    * a layer it did NOT publish gets no row written at all, so it keeps the
      generation it was actually published under -- a graph-only build must
      not advertise semantic freshness, and a semantic-only build must not
      advertise graph freshness;
    * the one exception is the graph on a semantic-only build whose SOURCE
      inputs changed: leaving that row untouched would let it read as current
      against a corpus it no longer describes, so it is marked ``stale``.
    """
    state: dict[str, str] = {}
    if build_docs:
        state["docs"] = LAYER_PUBLISHED
    if build_code:
        state["code"] = LAYER_PUBLISHED
    if graph_published:
        state["graph"] = LAYER_PUBLISHED
    elif graph_sources_changed:
        state["graph"] = LAYER_STALE
    return state


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
    unreadable_dirs: "set[str] | None" = None,
    doc_link_repair_plan: "dict | None" = None,
    state_conn=None,
    selected_paths: set[str] | None = None,
) -> dict[str, Any]:
    """Extract, merge and cluster the graph, PREPARING its publication rows.

    Wave 1xny6 (``1xny5-ref``): with ``state_conn`` nothing here writes. The
    graph, extraction and community rows are prepared against the caller's
    index connection and returned under ``publication`` so the coordinator
    applies them inside the SINGLE publication transaction that also carries
    the semantic rows. The former pre-transaction writes -- a graph payload
    file, a cluster payload file and an independent graph-store commit, all
    landing before ``BEGIN IMMEDIATE`` and none of them rolled back by a
    failed publication -- are gone, and lane L6b retired the two transitional
    derived writers with them, so an ordinary build writes no graph files at
    all.
    """
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
        unreadable_dirs=unreadable_dirs,
        verbose=verbose,
        state_conn=state_conn,
        **({"selected_paths": selected_paths} if selected_paths is not None else {}),
        **({"doc_link_repair_plan": doc_link_repair_plan} if doc_link_repair_plan is not None else {}),
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
    # The prepared graph rows travel separately from the payload: the payload
    # is graph CONTENT (and is handed to the cluster pass), the publication is
    # SQL. Wave 1xny6 lane L6b retired the post-commit derived artifact writer
    # this payload also used to feed.
    publication = graph_payload.pop("_publication", None) if isinstance(graph_payload, dict) else None
    cluster_payload = graph_cluster.update_graph_clusters(
        root=root,
        index_dir=index_dir,
        layer=layer,
        graph_payload=graph_payload,
        verbose=verbose,
        state_conn=state_conn,
    )
    cluster_publication = (
        cluster_payload.pop("_publication", None)
        if isinstance(cluster_payload, dict) else None
    )
    if publication is not None and cluster_publication is not None:
        publication.community = cluster_publication
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
            f" | dangling: dropped={merge_stats.get('edges_dropped_dangling', 0)}"
        )
    print(
        f"build_index: finished graph: {len(changed)} changed, {len(removed)} removed"
        f" | nodes: {counts.get('nodes', 0)} | edges: {counts.get('edges', 0)}"
        f"{merge_suffix}"
        f" in {elapsed:.1f}s",
        file=sys.stderr,
        flush=True,
    )
    return {
        "graph_payload": graph_payload,
        "cluster_payload": cluster_payload,
        "publication": publication,
        # False when the fingerprint gate reused the previous generation's
        # communities: there is nothing new to write, and rewriting the
        # derived artifact would move its mtime for no content change.
        "cluster_recomputed": cluster_publication is not None,
    }


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


def preflight_rebuild_sources(root: Path, index_dir: Path | None = None, *,
                              respect_ignore: bool = True, include_prefixes=(),
                              project_include_prefixes=(), include_tests=False,
                              include_generated=False) -> dict:
    """Strict current-source census for receipt-owned rebuilds, without embeddings."""
    root = Path(root)
    index_dir = index_dir or root / INDEX_DIR_NAME
    unreadable = set()
    files = walk_repo(root, respect_ignore=respect_ignore, unreadable_dirs=unreadable)
    if unreadable:
        raise RuntimeError("storage_rebuild_source_unreadable: " + _describe_unreadable_dirs(unreadable))
    files = _filter_by_prefixes([p for p in files if not _is_relative_to(p, index_dir)], root, include_prefixes)
    files = _filter_project_index_excludes(files, root, include_prefixes,
        project_include_prefixes=_project_meta_include_prefixes(root, project_include_prefixes))
    code = _filter_code_files(_filter_project_index_excludes(files, root, include_prefixes,
        project_include_prefixes=_effective_project_include_prefixes(root,index_dir,"code",project_include_prefixes)),
        root, include_tests=include_tests, include_generated=include_generated)
    docs = _filter_project_index_excludes(files, root, include_prefixes,
        project_include_prefixes=_effective_project_include_prefixes(root,index_dir,"docs",project_include_prefixes))
    layers = {"docs": set(docs) | set(code), "code": set(code)}
    hashes = {p: _sha256(p) for p in layers["docs"] | layers["code"]}
    return {layer: {str(p.relative_to(root)).replace("\\", "/"): hashes[p]
                    for p in sorted(paths)} for layer, paths in layers.items()}


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
    # 1wfr8: publish the per-project spec-chunking override (indexing.spec_aware_chunking,
    # a boolean) when the key is present; absent = the chunker's shipped default.
    spec_override = _resolve_spec_chunking_override(root)
    if spec_override is not None:
        os.environ["WAVEFOUNDRY_SPEC_CHUNKING"] = "1" if spec_override else "0"
    else:
        os.environ.pop("WAVEFOUNDRY_SPEC_CHUNKING", None)
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
    with _index_build_lock(index_dir), vector_store.PreparedUpdates(index_dir) as prepared:
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
            prepared=prepared,
        )


def _validate_prepared_removals(
    root, index_dir, removed_meta, removed_by_layer, *, requested_files,
    respect_ignore, include_prefixes, project_include_prefixes, include_tests, include_generated,
):
    """Recheck destructive membership decisions against the current source census.

    A deleted source can reappear while another file embeds. Existing excluded
    files must still be removable, so existence alone is not the desired-state
    test. Only builds actually removing paths pay for this second census.
    """
    removals = set(removed_meta).union(*removed_by_layer.values())
    if not removals:
        return
    unreadable = set()
    if requested_files is None:
        current = walk_repo(root, respect_ignore=respect_ignore, unreadable_dirs=unreadable)
        current = [path for path in current if not _is_relative_to(path, index_dir)]
        current = _filter_by_prefixes(current, root, include_prefixes)
    else:
        current = [path if path.is_absolute() else root / path for path in requested_files]
        current = [path for path in current if _is_relative_to(path, root) and path.is_file()]
        for exclude in (_filter_canonical_wave_event_ledgers, _filter_memory_archive_bodies,
                        _filter_legacy_memory_pointers, _filter_secret_scan_findings):
            current = exclude(current, root)
    if str(index_dir).replace("\\", "/").endswith("/.wavefoundry/framework/index"):
        current = _filter_framework_pack_artifacts(current, root)
    if _graph_layer_for_index_dir(index_dir) == "project":
        current = _filter_project_index_excludes(
            current, root, include_prefixes,
            project_include_prefixes=_project_meta_include_prefixes(root, project_include_prefixes))
    def relative(paths):
        return {str(path.relative_to(root)).replace("\\", "/") for path in paths}
    code = _filter_code_files(_filter_project_index_excludes(
        current, root, include_prefixes,
        project_include_prefixes=_effective_project_include_prefixes(root, index_dir, "code", project_include_prefixes)),
        root, include_tests=include_tests, include_generated=include_generated)
    code_paths = relative(code)
    docs_paths = relative(_filter_project_index_excludes(
        current, root, include_prefixes,
        project_include_prefixes=_effective_project_include_prefixes(root, index_dir, "docs", project_include_prefixes))) | code_paths
    invalid = (set(removed_meta) & relative(current)) | (removed_by_layer.get("docs", set()) & docs_paths) | (
        removed_by_layer.get("code", set()) & code_paths)
    invalid |= {path for path in removals if _shadowed_by_unreadable(path, unreadable)}
    if invalid:
        raise RuntimeError("Removal source changed during embedding or became unreadable: "
                           + ", ".join(sorted(invalid)[:5]) + "; retry indexing")


def _close_owned_build_store(store) -> None:
    """Release an owned writer without replacing its active failure."""
    failing = sys.exc_info()[0] is not None
    try:
        store.close()
    except Exception:
        if not failing:
            raise


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
    prepared=None,
) -> dict:
    """Build or incrementally update the index at root/.wavefoundry/index/.

    Returns a summary dict with counts.
    """
    requested_files = tuple(files) if files is not None else None
    selected_paths = None
    if requested_files is not None:
        selected_paths = set()
        for path in requested_files:
            candidate = Path(os.path.normpath(path if path.is_absolute() else root / path))
            if _is_relative_to(candidate, root):
                selected_paths.add(candidate.relative_to(root).as_posix())
        files = [root / rel for rel in sorted(selected_paths)]
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

    import sqlite_storage_migration
    try:
        sqlite_storage_migration.require_ready(index_dir)
    except sqlite_storage_migration.MigrationRequired as exc:
        return _build_failed_result(files or [], str(exc))
    storage_receipt = sqlite_storage_migration.read_receipt(index_dir)
    storage_rebuild = (sqlite_storage_migration.rebuild_requested(storage_receipt)
                       and storage_receipt["state"] != "complete")
    rebuild_inventory = None
    rebuild_options = dict(respect_ignore=respect_ignore, include_prefixes=include_prefixes,
        project_include_prefixes=project_include_prefixes, include_tests=include_tests,
        include_generated=include_generated)
    if storage_rebuild:
        if requested_files is not None:
            return _build_failed_result(files, "storage_rebuild_requires_complete_source_walk: run a complete walk with files=None")
        if content != "graph":
            content, full = "all", True
        rebuild_inventory = preflight_rebuild_sources(root, index_dir, **rebuild_options)

    prepared_identity = (DOCS_MODEL, CODE_MODEL, WALKER_VERSION,
                         getattr(_get_chunker(), "CHUNKER_VERSION", ""))
    config_path = root / "docs" / "workflow-config.json"
    prepared_config_hash = _sha256(config_path) if config_path.is_file() else None

    policy_identity = json.dumps({
        "options": rebuild_options,
        "inputs": {name: (prepared_config_hash if name == "docs/workflow-config.json" else
                          _sha256(root / name) if (root / name).is_file() else None)
                   for name in ("docs/workflow-config.json", ".gitignore", ".aiignore", ".gitattributes", ".git/info/exclude")},
    }, sort_keys=True)
    policy_needs_refresh = False
    prior_layer_paths = {"docs": set(), "code": set()}
    if selected_paths is not None:
        reason = "explicit full rebuild" if full else None
        iss = _get_index_state_store()
        conn = None
        try:
            conn = iss.open_read_only(index_dir)
            if conn is None and (index_dir / vector_store.FILENAME).exists():
                reason = reason or "existing storage schema/currency is unreadable"
            if conn is not None:
                conn.execute("BEGIN")
                prior_meta = _load_meta(index_dir)
                if not prior_meta:
                    reason = reason or "existing storage provenance is unproven"
                prior_policy = conn.execute("SELECT value FROM meta WHERE key='targeted_corpus_policy'").fetchone()
                if prior_meta:
                    if prior_policy != (policy_identity,):
                        reason = reason or "corpus policy changed or is unproven"
                    if prior_meta.get("walker_version") != WALKER_VERSION:
                        reason = reason or "walker version changed"
                    for layer, model in (("docs", DOCS_MODEL), ("code", CODE_MODEL)):
                        present = layer in prior_meta.get("content", [])
                        if not present and content in (layer, "all"):
                            reason = reason or f"{layer} index currency is unproven"
                        if present:
                            precision = _predicted_precision_class(model, _onnx_providers())
                            expected = f"{model}@{precision}@{_identity_fingerprint_for_class(precision)}"
                            if (prior_meta.get("model_versions", {}).get(layer) != expected
                                    or prior_meta.get("chunker_versions", {}).get(layer) != prepared_identity[3]):
                                reason = reason or f"{layer} model/chunker identity changed"
                        prior_layer_paths[layer] = {row[0] for row in conn.execute(f"SELECT DISTINCT path FROM chunks_{layer}")}
                        prior_layer_paths[layer] |= {row[0] for row in conn.execute("SELECT path FROM layer_path_state WHERE layer=?", (layer,))}
                    graph_store = _get_graph_indexer().GraphStateStore(conn, layer=_graph_layer_for_index_dir(index_dir),
                        walker_version=WALKER_VERSION, chunker_version=prepared_identity[3])
                    if not graph_store.versions_current():
                        reason = reason or "graph builder/schema identity changed"
        except Exception as exc:
            reason = reason or f"storage currency cannot be established: {exc}"
        finally:
            if conn is not None:
                conn.close()
        if reason:
            return _build_failed_result(files, f"Targeted indexing refused: {reason}; run a complete walk with files=None (wf setup --full when rebuilding).")

    # --- 1sed6 review fix (reset-before-decisions): settle store schema
    # currency FIRST. The version-gated reset used to fire lazily at the
    # first WRITE (begin_build_epoch), i.e. AFTER the front gate and
    # staleness reads had already consumed the outdated store's (readable)
    # pre-reset state — so a schema-bumped store skipped mandatory all-layer
    # convergence and idled straight to a complete epoch over erased state.
    # Forcing ensure_current here makes every decision below read the
    # POST-reset truth: an actually-reset store presents empty provenance
    # (front gate escalates) and empty layer state (everything stale).
    # Dry runs skip it — they must not mutate the store.
    if not dry_run:
        _iss_pre = _get_index_state_store()
        if _iss_pre is not None:
            try:
                _pre_store = _iss_pre.IndexStateStore(index_dir)
                try:
                    _pre_store.ensure_current()
                    policy_needs_refresh = (_pre_store._conn.execute(
                        "SELECT value FROM meta WHERE key='targeted_corpus_policy'").fetchone() != (policy_identity,))
                    if not full:
                        for layer in ("docs", "code"):
                            if _pre_store._conn.execute(
                                    f"PRAGMA foreign_key_check(vectors_{layer})").fetchone():
                                return _build_failed_result(files or [],
                                    f"{layer}: orphan vector references require an explicit "
                                    "all-layer rebuild; run wf setup --full. Canonical data retained.")
                finally:
                    _pre_store.close()
            except vector_store.runtime.CorruptionError as exc:
                return _build_failed_result(files or [],
                    "Canonical SQLite index is corrupt. Stop all Wavefoundry database-owning "
                    "hosts; preserve index.sqlite and any sibling -wal/-shm files "
                    "outside .wavefoundry/index, then run wf setup --full. Keep the separate "
                    "memory store and any migration receipt/rollback intact. "
                    f"If migration is pending, resume its recorded recovery first. Detail: {exc}")
            except Exception as exc:  # noqa: BLE001 - store must be decidable before any mutation
                return _build_failed_result(
                    files or [], f"index-state store could not be brought current: {exc}"
                )

    # Load existing state first: graph-only and content-scoped runs preserve
    # the other layers' chunker_versions/model_versions/content provenance;
    # only a full ALL-layer rebuild starts from a clean slate. (Review fix:
    # a full scoped build previously erased the untouched layer's provenance
    # and still published a complete epoch over its surviving canonical chunk layer.)
    meta = {} if (full and content == "all") else _load_meta(index_dir)

    # --- 1sed6 reset escalation (Req 8 / review fix) ---
    # After a whole-store reset (or on any store that lost its bookkeeping),
    # a canonical chunk layer can exist with NO provenance in the canonical state. A
    # scoped build must not publish `complete` around that hole: escalate to
    # all-layer convergence. Cost is reset-shape-dependent: a whole-store
    # reset (content list empty too) converges as one re-chunk pass with
    # vector reuse, while a partial wipe that leaves a layer listed in
    # `content` trips the model-changed full rebuild — a full re-embed, which
    # is the SAFE posture (vectors from an unknown model must not be reused).
    # A fresh install (no tables) is NOT a reset and stays scoped. This also
    # applies to graph-only runs (they publish a completion epoch): on a
    # reset store a graph refresh first converges semantic state — a
    # deliberate integrity-over-latency trade, documented in the tool spec.
    if content != "all" and index_dir is not None:
        _known_models = meta.get("model_versions") or {}
        _unprovenanced = [
            layer for layer in ("docs", "code")
            if vector_store.layer_available(index_dir, layer)
            and not _known_models.get(layer)
            and not (content == layer)  # this run rebuilds that layer's provenance itself
        ]
        if _unprovenanced:
            print(
                "build_index: canonical state is missing provenance for "
                f"{', '.join(_unprovenanced)} (store reset or legacy install) — "
                f"escalating content={content!r} to all-layer convergence",
                file=sys.stderr,
                flush=True,
            )
            content = "all"

    build_docs = content in ("docs", "all")
    build_code = content in ("code", "all")
    old_file_meta: dict[str, dict] = meta.get("file_meta", {})
    old_model_versions: dict[str, str] = meta.get("model_versions", {})

    # A model-set fingerprint is an all-layer compatibility boundary. A scoped
    # update may preserve an untouched layer only while every existing semantic
    # layer already carries the active model, precision class, and fingerprint.
    # Otherwise publishing the selected layer would create a completed mixed
    # epoch (for example docs=v2 beside code=v1), so converge both layers in one
    # build epoch instead.
    if content != "all" and index_dir is not None:
        _active_providers = _onnx_providers()
        _expected_models = {"docs": DOCS_MODEL, "code": CODE_MODEL}
        _stale_model_layers: list[str] = []
        for _layer, _expected_model in _expected_models.items():
            _layer_present = (
                vector_store.layer_available(index_dir, _layer)
                or _layer in set(meta.get("content", []))
            )
            if not _layer_present:
                continue
            _value = old_model_versions.get(_layer)
            _fingerprint_stale = (
                _model_set_fingerprint_from_version(_value)
                != _identity_fingerprint_for_class(
                    _predicted_precision_class(_expected_model, _active_providers)
                )
            )
            _untouched_identity_stale = _layer != content and (
                (_value or "").split("@", 1)[0] != _expected_model
                or _precision_class_from_version(_value)
                != _predicted_precision_class(_expected_model, _active_providers)
            )
            if _fingerprint_stale or _untouched_identity_stale:
                _stale_model_layers.append(_layer)
        if _stale_model_layers:
            print(
                "build_index: semantic model-set identity is stale for "
                f"{', '.join(_stale_model_layers)} — escalating content={content!r} "
                "to one all-layer convergence epoch",
                file=sys.stderr,
                flush=True,
            )
            content = "all"
            build_docs = True
            build_code = True
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
        model_changed = model_changed or _model_set_fingerprint_from_version(old_docs_value) != (
            _identity_fingerprint_for_class(_predicted_precision_class(DOCS_MODEL, _onnx_providers()))
        )
        docs_index_exists = (
            vector_store.layer_available(index_dir, "docs")
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
        model_changed = model_changed or _model_set_fingerprint_from_version(old_code_value) != (
            _identity_fingerprint_for_class(_predicted_precision_class(CODE_MODEL, _onnx_providers()))
        )
        code_index_exists = (
            vector_store.layer_available(index_dir, "code")
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

    # Drift-flagged paths (populated by the incremental change-detection branch
    # below). Consumed by the registry-skip exemption in the incremental write
    # (wave 1rsh9): drift repair must always read canonical chunks, the authority.
    drifted: set[str] = set()

    # Wave 1x54z (1u8o3): directories ``os.walk`` could not read this build
    # (root-relative; empty on the explicit ``files=`` seam, which never walks).
    _unreadable_dirs: set[str] = set()

    if files is None:
        # Walk repo
        files = walk_repo(root, respect_ignore=respect_ignore, unreadable_dirs=_unreadable_dirs)
        if storage_rebuild and _unreadable_dirs:
            raise RuntimeError("storage_rebuild_source_unreadable: " + _describe_unreadable_dirs(_unreadable_dirs))
        files = [path for path in files if not _is_relative_to(path, index_dir)]
        files = _filter_by_prefixes(files, root, include_prefixes)
        if str(index_dir).replace("\\", "/").endswith("/.wavefoundry/framework/index"):
            files = _filter_framework_pack_artifacts(files, root)
        # files_for_meta must be stable across docs-run and code-run on the same layer
        # (otherwise consecutive runs alternately add/remove each other's files in
        # build state — the original 93-files-added / 93-files-removed cycle this block
        # was introduced to prevent).  For the project layer we still must keep
        # framework-prefixed files out of the project layer's build state — those belong
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
        # ``files=`` is a public build seam used by targeted/incremental callers
        # and bypasses walk_repo(), so enforce the same corpus boundary here.
        files = _filter_canonical_wave_event_ledgers(files, root)
        files = _filter_memory_archive_bodies(files, root)
        files = _filter_legacy_memory_pointers(files, root)
        files = _filter_secret_scan_findings(files, root)
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
    # --- 1sek8: per-layer eligibility (ONE corpus definition per table) ---
    # Each semantic table's membership is computed the same way under EVERY
    # content scope: the layer's effective include-prefixes, plus (code only)
    # the tests/generated source filter. Previously `content=all` skipped
    # `_filter_code_files` entirely, so the code table's membership depended
    # on which content flag last ran (setup's `all` builds chunked test files
    # that `content=code` builds then reaped).
    _docs_includes = _effective_project_include_prefixes(root, index_dir, "docs", project_include_prefixes)
    docs_eligible_rel: set[str] = {
        str(f.relative_to(root)).replace("\\", "/")
        for f in _filter_project_index_excludes(
            files_for_meta, root, include_prefixes, project_include_prefixes=_docs_includes
        )
    }
    _code_includes = _effective_project_include_prefixes(root, index_dir, "code", project_include_prefixes)
    code_eligible_rel: set[str] = {
        str(f.relative_to(root)).replace("\\", "/")
        for f in _filter_code_files(
            _filter_project_index_excludes(
                files_for_meta, root, include_prefixes, project_include_prefixes=_code_includes
            ),
            root,
            include_tests=include_tests,
            include_generated=include_generated,
        )
    }
    # Dual-output files (live-verified on this repo, 1sek8): every code
    # chunker emits kind="doc" docstring/comment chunks that route to the
    # DOCS table, so the docs layer's eligibility is the UNION of the docs
    # prefixes and the code corpus — prefix-only docs eligibility would (and
    # briefly did) reap every code file's docstring rows from the docs table
    # and leave their doc chunks permanently unmaintained. The PRE-union
    # prefix set is kept separately: drift candidacy and the emitted-count
    # claims stay prefix-scoped (a docs-only build must not drift-flag code
    # files whose code rows it cannot write — the 1rmaf contract; dual-output
    # docstring drift was never detectable pre-1sek8 either, a documented
    # limitation, not a regression).
    docs_prefix_eligible_rel: set[str] = set(docs_eligible_rel)
    docs_eligible_rel |= code_eligible_rel
    if selected_paths is not None:
        docs_eligible_rel |= prior_layer_paths["docs"] - selected_paths
        code_eligible_rel |= prior_layer_paths["code"] - selected_paths
    # Full replacement also removes previously indexed paths absent from its
    # captured census. Preserve those decisions for the same publication guard.
    _full_removed_by_layer = {"docs": set(), "code": set()}
    if full:
        prior_conn = _get_index_state_store().open_read_only(index_dir)
        if prior_conn is not None:
            try:
                for layer, enabled, eligible in (("docs", build_docs, docs_eligible_rel),
                                                  ("code", build_code, code_eligible_rel)):
                    if enabled:
                        _full_removed_by_layer[layer] = {
                            row[0] for row in prior_conn.execute(f"SELECT DISTINCT path FROM chunks_{layer}")
                        } - eligible
            finally:
                prior_conn.close()
    # Hash the broad file set so the build snapshot captures every walkable file regardless
    # of which content type (docs/code/graph) this run is building. The snapshot is
    # the WALK-STATE snapshot (stat cache, graph/reap/freshness input) — since
    # 1sek8 it is no longer the semantic layers' change-detection authority:
    # each layer compares the walk hash against its own last-embedded hash in
    # the index-state store, so a scoped build can never erase another layer's
    # change signal by stamping a hash it did not embed.
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
        current_file_meta, changed_broad, removed_broad = _detect_changes(files_for_meta, root, old_file_meta, selected_paths)
        # Wave 1x54z (1u8o3): a path the walk could not SEE is not a removal.
        # ``os.walk`` skips a directory whose ``scandir`` fails, so every path
        # under it drops out of ``files_for_meta`` and would read as removed:
        # the incremental write deletes its rows, the layer-hash commit drops
        # its hash, the reap and the orphan reconcile lose it from their
        # authority, the secrets ledger forgets its findings, and the next
        # readable build re-embeds the whole subtree. Neutralise the omission
        # at its source: carry the prior bookkeeping entry forward (it is what
        # the stat cache would have confirmed) and take the path out of the
        # removal set, so every downstream consumer sees "unchanged". The reap
        # still receives ``_unreadable_dirs`` because its per-table eligibility
        # is walk-derived and would otherwise strand these paths.
        _walk_shadowed = {
            rel for rel in removed_broad if _shadowed_by_unreadable(rel, _unreadable_dirs)
        }
        if _walk_shadowed:
            removed_broad = removed_broad - _walk_shadowed
            for _rel in _walk_shadowed:
                current_file_meta[_rel] = old_file_meta[_rel]
            _shadow_msg = (
                f"build_index: {len(_walk_shadowed)} indexed path(s) sit under a directory the walk "
                f"could not read ({_describe_unreadable_dirs(_unreadable_dirs)}); treating them as unchanged, "
                "not removed: rows, layer hashes and bookkeeping are kept until the directory is "
                "readable again"
            )
            print(_shadow_msg, file=sys.stderr, flush=True)
            _store_log_safe(index_dir, _shadow_msg)
        # Wave 1p3b9 (1p399): drift detection. Cross-check `file_meta` against
        # canonical chunks: paths claimed indexed in file_meta but with zero rows in any
        # canonical chunk layer are "drifted" — they need re-chunk + re-embed regardless
        # of hash match. The historic cause was the chunker mega-chunk bug
        # (closed by 1p397) that produced zero chunks for some files; the
        # incremental loop's skip-on-hash-match optimization perpetuated the
        # missing-rows state forever. This check makes incremental update
        # self-repairing for ANY future drift source.
        #
        # 1rmaf: drift candidacy is scoped to the paths this build can
        # actually re-chunk (`files_for_content` — the same set the chunk
        # loop below consumes, one source of truth), and skipped outright
        # when the build writes no semantic rows (`content="graph"`:
        # `build_docs` and `build_code` both False). Gate on the BOOLEANS,
        # not the content string: in graph-only mode `files_for_content` is
        # the UNFILTERED code walk (`_filter_code_files` is skipped when
        # `build_code` is False) while nothing is ever written, so an
        # eligibility intersection would be a no-op and the repair loop
        # would survive in that mode. The set is computed per build and
        # never persisted, so include-flag transitions stay sound. Named
        # distinctly from the idle reap's `eligible_paths` (the wider meta
        # union) — see _detect_vector_drift's docstring.
        if build_docs or build_code:
            # 1sek8: drift candidacy = the PRE-union eligibility of the layers
            # being BUILT — a docs-only build can only repair docs-prefix
            # files (it cannot write code rows, so a zero-code-row code file
            # must not flag), and code-ineligible test files that content=all
            # used to include must not flag once the corpus is unified.
            chunk_eligible_rel_paths = (
                (docs_prefix_eligible_rel if build_docs else set())
                | (code_eligible_rel if build_code else set())
            )
            if selected_paths is not None:
                chunk_eligible_rel_paths &= selected_paths
            drifted = _detect_vector_drift(
                index_dir,
                current_file_meta,
                chunk_eligible_rel_paths=chunk_eligible_rel_paths,
                verbose=verbose,
            )
        else:
            drifted = set()
            if verbose:
                print(
                    "build_index: drift-detect skipped — no semantic writes this build "
                    "(graph-only)",
                    flush=True,
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
    # `updated` (not `added`) → existing canonical rows are fetched and the delta planner reuses
    # vectors for content-unchanged chunks; only genuinely new/changed chunks re-embed.
    if rechunk_all:
        changed_broad |= set(current_file_meta.keys())
    # Wave 1ro44 (1p8gy) — memory invalidation FIRST (delivery-review round 4):
    # advance the memory generation as soon as the changed/removed path sets are
    # known, BEFORE any optional vector / FTS / freshness / drift work, so a
    # later structured build failure cannot leave a raw-edited memory record's
    # advisory stale. Gated on actual changed/removed memory records.
    #
    # Round-4 re-review P1: a failed `memory_advance` must NOT be swallowed and
    # the build must NOT proceed to record file metadata. A raw content edit
    # leaves `dir_mtime` unchanged, so an un-advanced generation keeps warm
    # readers in OTHER processes authoritative on the pre-edit advisory — and if
    # this build then records the edited file's hash, the recovered retry sees
    # "no change" and NEVER re-invalidates, permanently stranding the stale
    # advisory. `memory_invalidate` returns True only when the generation
    # DURABLY advanced; on failure it sets a best-effort short-lived bypass and
    # returns False, and we FAIL THE BUILD BEFORE bookkeeping so the old
    # file_meta is preserved and the next build re-detects the edit.
    if _memory_record_touched(changed_broad, removed_broad):
        _iss_mem = _get_index_state_store()
        if _iss_mem is not None:
            invalidated = False
            try:
                invalidated = _iss_mem.memory_invalidate(index_dir)
            except Exception:
                invalidated = False
            if not invalidated:
                return _build_failed_result(
                    files,
                    "memory record(s) changed but the durable memory seqlock "
                    "could not advance the generation (memory-state.sqlite "
                    "unwritable) — failing the build BEFORE bookkeeping so old "
                    "file metadata is preserved and the next build retries "
                    "invalidation (recorded a clean build would strand the stale "
                    "advisory)",
                )
    # removed: use the broad result directly — a file absent from files_for_meta is
    # truly deleted from disk (not merely filtered out), so its chunks must be evicted
    # regardless of which content type's run discovers the deletion.
    files_rel = {str(f.relative_to(root)).replace("\\", "/") for f in files}
    files_for_graph_rel = {str(f.relative_to(root)).replace("\\", "/") for f in files_for_graph}
    changed_for_graph = changed_broad & files_for_graph_rel
    if selected_paths is not None:
        files_for_graph_rel |= set(current_file_meta) - selected_paths
    # --- 1sek8: per-layer change detection ---
    # Each SEMANTIC layer compares the current walk hash against the hash it
    # last embedded (index-state store `layer_path_state`), scoped to its own
    # eligibility set. The broad meta hash is no longer the semantic change
    # signal — a docs-only build stamping a changed code file's fresh hash
    # (the 1sek8 poison: docs+code edits interleaved, then `content=code`
    # reported "up to date" forever) cannot erase the code layer's staleness,
    # because the code layer never embedded that hash. An EMPTY layer state
    # (fresh store, schema bump, pre-1sek8 repo) makes everything eligible
    # stale — one rechunk pass with chunk-hash vector reuse converges it,
    # which is also the heal for previously poisoned repos.
    _iss_layer = _get_index_state_store()
    layer_stale: dict[str, set[str]] = {"docs": set(), "code": set()}
    if not full:
        for _layer, _flag, _eligible in (
            ("docs", build_docs, docs_eligible_rel),
            ("code", build_code, code_eligible_rel),
        ):
            if not _flag:
                continue
            if _iss_layer is None:
                # Store module unavailable (older extracted pack): legacy
                # broad-meta detection for this layer — degraded, no worse
                # than the pre-1sek8 behavior.
                layer_stale[_layer] = changed_broad & _eligible
                continue
            # Unreadable/absent/pre-1sek8 store state reads as EMPTY (not
            # legacy): everything eligible is stale, one rechunk pass with
            # vector reuse converges — the migration heal runs on the FIRST
            # post-upgrade build, not the second.
            _state = _iss_layer.layer_hashes(index_dir, _layer) or {}
            if rechunk_all:
                layer_stale[_layer] = set(_eligible) if selected_paths is None else _eligible & selected_paths
                continue
            _stale_set: set[str] = set()
            for _rel in (_eligible if selected_paths is None else _eligible & selected_paths):
                _cur = current_file_meta.get(_rel, {}).get("hash")
                if _cur is None or _cur != _state.get(_rel):
                    _stale_set.add(_rel)
            # Drift-flagged paths re-process regardless of layer-hash match
            # (canonical rows vanished out-of-band; canonical chunks are the authority).
            _stale_set |= drifted & _eligible
            layer_stale[_layer] = _stale_set
    changed = (changed_broad & files_rel) if full else (layer_stale["docs"] | layer_stale["code"])
    removed = removed_broad
    added = changed - set(old_file_meta.keys()) if not full else changed
    updated = changed & set(old_file_meta.keys()) if not full else set()
    stale = changed | removed

    if not full and not stale:
        # Even when no files changed, canonical rows for paths now excluded by
        # workflow-config narrowing must still be reaped — build-state drift is
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
        # 1sed6: read-only preflight FIRST — a true no-op must not open the
        # build epoch or advance the generation (Req 8); mutations (reap,
        # heal) require the durable fence before they touch canonical/FTS.
        _reap_plan = _reap_stranded_vector_rows(
            index_dir,
            set(current_file_meta.keys()),
            root=root,
            tables=("docs", "code"),
            verbose=verbose,
            eligible_by_table={"docs": docs_eligible_rel, "code": code_eligible_rel},
            plan_only=True,
            unreadable_dirs=_unreadable_dirs,
        )
        _planned_stranded = _reap_plan.get("paths_by_table", {})
        _reap_deferred_summary = _deferred_summary(_reap_plan.get("deferred_by_table"))
        _reap_preserved_summary = _preserved_summary(_reap_plan.get("preserved_by_table"))
        _needs_reap = any(_planned_stranded.get(k) for k in ("docs", "code"))
        # 1sbfj: an under-covered or cold derived chunk index must still heal
        # on zero-change builds — the field-retest scenario is upgrade-then-
        # idle. Cheap probe; the reconcile only runs on a detected gap.
        _needs_heal = _chunk_index_needs_heal(index_dir)
        # 1u8nz: read-only orphan-store plan for graph/file_freshness/
        # secret_scan_cache rows whose path the current authority no longer
        # knows. Zero-change builds are the ONLY builds that never ran the
        # graph merge, so this seam is where orphaned graph rows previously
        # survived forever (sidecars additionally leak on ordinary builds and
        # are reconciled at the build-path reap seam too).
        _orphan_plan = _plan_orphan_store_reconcile(
            root, index_dir, set(current_file_meta.keys()), verbose=verbose,
            unreadable_dirs=_unreadable_dirs,
        )
        if selected_paths is not None:
            _orphan_plan = {k: (set(v) & selected_paths if k in _ORPHAN_RECONCILE_STORES else v)
                            for k, v in _orphan_plan.items()}
        _needs_orphan_reconcile = any(
            _orphan_plan.get(k) for k in _ORPHAN_RECONCILE_STORES
        )
        # Review fix (dirty-epoch unchanged-retry lockout): a true no-op may
        # short-circuit ONLY over a completed epoch. If a prior builder died
        # between fence and finalize, the walk can legitimately see zero
        # changes (per-layer hashes committed before the crash) while readers
        # are failed closed on `building` — an unchanged retry must repair
        # that epoch (reconcile + refreshed bookkeeping + finalize), not
        # report up_to_date over a permanently dirty store.
        _iss_epoch = _get_index_state_store()
        if _iss_epoch is None:
            return _build_failed_result(files, "index-state store module unavailable — refusing idle maintenance without the build epoch")
        _prior_state = _iss_epoch.read_build_state(index_dir)
        _epoch_dirty = not (_prior_state and _prior_state.get("status") == "complete")
        # 1x8e1: an unchanged doc can still owe a link into a now-current
        # target. Planning opens SQLite read-only; never create a graph
        # session here, since dry runs bypass the lock. A real repair reuses
        # this merge-state snapshot inside the existing build epoch.
        _doc_link_plan = _get_graph_indexer().read_pending_doc_link_repairs(
            index_dir=index_dir,
            current_paths=files_for_graph_rel,
            walker_version=WALKER_VERSION,
            chunker_version=current_chunker_version,
            layer=graph_layer,
            unreadable_dirs=_unreadable_dirs,
        )
        _needs_graph_recovery = bool(_doc_link_plan and (
            _doc_link_plan.get("pending_docs") or _doc_link_plan.get("rebuild_required")
        ))
        # 1x81w: this branch is also reached by the UNLOCKED public dry run.
        # Finish read-only planning and return before drift reconciliation,
        # lost-layer hash resets, or any idle-maintenance epoch/writer.
        if dry_run:
            _drift_state = "not_needed"
            if _iss_epoch.has_drift_state(index_dir):
                _drift_state, _head = _iss_epoch._git_authority(root)
            _pending_maintenance = {
                "drift_clear": _drift_state == _iss_epoch._GIT_AUTHORITY_NON_GIT,
                "stranded_reap": _needs_reap,
                "chunk_heal": _needs_heal,
                "dirty_epoch": _epoch_dirty,
                "orphan_reconcile": _needs_orphan_reconcile,
                "graph_recovery": _needs_graph_recovery,
            }
            _pending = any(_pending_maintenance.values())
            print(
                "build_index: dry-run — "
                + ("pending maintenance: " + ", ".join(
                    key for key, needed in _pending_maintenance.items() if needed
                ) if _pending else "index is up to date"),
                file=sys.stderr, flush=True,
            )
            return {
                "files_indexed": 0,
                "files_total": len(files),
                "up_to_date": not _pending,
                "dry_run": True,
                "pending_maintenance": _pending_maintenance,
                "drift_probe": _drift_state,
                "stranded_paths_pending": {
                    k: len(_planned_stranded.get(k, ())) for k in ("docs", "code")
                },
                "orphan_paths_pending": {
                    k: len(_orphan_plan.get(k, ())) for k in _ORPHAN_RECONCILE_STORES
                },
                "stranded_rows_reaped": 0,
                "stranded_rows_reaped_by_table": {"docs": 0, "code": 0, "total": 0},
                "stranded_reap_deferred": _reap_deferred_summary,
                "stranded_reap_preserved": _reap_preserved_summary,
                "orphan_rows_reconciled": {"file_freshness": 0, "secret_scan_cache": 0, "graph": 0},
            }
        # Round-4 re-review P1: the tail drift pass is skipped on this no-op
        # return, so an unchanged copied index — or a repo that lost .git with
        # no other edits — would keep serving stale git-derived drift. Reconcile
        # a CONFIRMED git→non-git transition here too (preserved on probe
        # failure / real git). Cheap gate: only probe git when the store
        # actually holds drift state, so a normal git repo pays nothing extra.
        #
        # The result MUST be captured: if the clear fails on a confirmed
        # transition (`drift_clear_failed`/`error`, or a raised exception), a
        # `up_to_date: True` return would report a clean build over a stale
        # `drifted: true` row that no reader would ever re-clear on the next
        # no-op. FAIL the build instead so the retry re-attempts the clear.
        try:
            if _iss_epoch.has_drift_state(index_dir):
                _reconcile = _iss_epoch.reconcile_non_git_drift(
                    root, index_dir, verbose=verbose
                )
                if _reconcile.get("drift_clear_failed") or _reconcile.get("error"):
                    return _build_failed_result(
                        files,
                        "confirmed git→non-git transition could not clear stale "
                        f"drift ({_reconcile.get('error', 'clear failed')}) — "
                        "failing the build so the stale drift is not served behind "
                        "an up_to_date result; the next build retries the clear",
                    )
        except Exception as _exc:
            return _build_failed_result(
                files, f"no-op drift reconcile failed: {_exc}"
            )
        if not _needs_reap and not _needs_heal and not _epoch_dirty and not _needs_orphan_reconcile and not _needs_graph_recovery and not policy_needs_refresh:
            if verbose:
                print("build_index: index is up to date", flush=True)
            # Wave 1x6ti (1x551): a deferral here opens no epoch, so the
            # record is stamped with the last completed build's generation.
            _record_reap_state(
                index_dir, deferred=_reap_deferred_summary, preserved=_reap_preserved_summary,
                dry_run=dry_run, verbose=verbose,
            )
            return {
                "files_indexed": 0,
                "files_total": len(files),
                "up_to_date": True,
                "stranded_rows_reaped": 0,
                "stranded_rows_reaped_by_table": {"docs": 0, "code": 0, "total": 0},
                "stranded_reap_deferred": _reap_deferred_summary,
                "stranded_reap_preserved": _reap_preserved_summary,
                "orphan_rows_reconciled": {"file_freshness": 0, "secret_scan_cache": 0, "graph": 0},
            }
        if _epoch_dirty:
            print(
                "build_index: prior build epoch is incomplete "
                f"(status={(_prior_state or {}).get('status', 'absent')!r}) — running "
                "zero-change recovery (reconcile + bookkeeping refresh + finalize)",
                file=sys.stderr,
                flush=True,
            )
        # Recovery guard (independent-review F1 — the inverse of the
        # publication rear guard): a dirty-epoch recovery may only republish
        # state it can actually serve. A layer whose chunk REGISTRY holds
        # rows (content was published) but whose canonical chunk layer is gone cannot
        # be repaired here — recovery never re-embeds. Checked BEFORE the
        # reap/heal (which would resync the registry down to the absent table
        # and erase the loss signal), keyed on the registry rather than bare
        # provenance so a legitimately empty layer (zero chunks, no table)
        # never trips it. Reset the lost layer's last-embedded hashes so the
        # next ordinary build sees everything stale and reconstructs the
        # table; fail this run visibly (epoch stays incomplete, readers stay
        # closed).
        if _epoch_dirty:
            _claimed_missing = []
            for _layer in ("docs", "code"):
                if vector_store.layer_available(index_dir, _layer):
                    continue
                _reg_rows = _iss_epoch.registry_chunk_count(index_dir, _layer)
                if _reg_rows:
                    _claimed_missing.append(_layer)
            if _claimed_missing:
                for _layer in _claimed_missing:
                    try:
                        _iss_epoch.replace_layer_hashes(index_dir, _layer, {})
                    except Exception:
                        pass
                return _build_failed_result(
                    files,
                    "zero-change recovery cannot republish: the chunk registry holds rows for "
                    f"layer(s) {', '.join(_claimed_missing)} but its vector layer is missing — "
                    "layer state reset; run index_build(content='all') to reconstruct",
                )
        try:
            _idle_attempt = _iss_epoch.begin_build_epoch(index_dir, f"{content}:idle-maintenance")
        except Exception as exc:  # noqa: BLE001 - fence failure fails the build
            return _build_failed_result(files, f"could not open the build epoch: {exc}")
        reap_idle = {"docs": 0, "code": 0, "total": 0}
        if _needs_reap:
            reap_idle = _reap_stranded_vector_rows(
                index_dir,
                set(current_file_meta.keys()),
                root=root,
                tables=("docs", "code"),
                verbose=verbose,
                precomputed_stranded=_planned_stranded,
            )
            _reap_idle_paths = reap_idle.pop("paths_by_table", {})
            reap_idle.pop("preserved_by_table", None)
            reap_idle.pop("deferred_by_table", None)
            _cleanup_layer_state_for_reaped(index_dir, _reap_idle_paths)
        _graph_orphans_reconciled = 0
        # Wave 1xny6: the idle pass publishes through the same participant
        # contract as the build path -- one connection, one transaction. Its
        # participant set is smaller (there are no semantic rows on a
        # zero-change pass), but a graph recovery or an orphan retirement is
        # still applied inside a transaction and finalized by the same CAS.
        try:
            _idle_store = _iss_epoch.IndexStateStore(index_dir)
        except Exception as exc:  # noqa: BLE001
            return _build_failed_result(files, f"could not open the index store: {exc}")
        try:
            _idle_graph_publication = None
            if _needs_graph_recovery:
                try:
                    _idle_artifacts = _build_graph_artifacts(
                        root=root, index_dir=index_dir, layer=graph_layer,
                        state_conn=_idle_store._conn,
                        **({"selected_paths": selected_paths} if selected_paths is not None else {}),
                        files=files_for_graph, current_file_meta=current_file_meta,
                        changed=changed_for_graph, removed=removed,
                        walker_version=WALKER_VERSION,
                        chunker_version=current_chunker_version,
                        unreadable_dirs=_unreadable_dirs, verbose=verbose,
                        doc_link_repair_plan=_doc_link_plan,
                    )
                    _idle_graph_publication = _idle_artifacts.get("publication")
                except Exception as exc:  # noqa: BLE001 - preserve dirty epoch for retry
                    return _build_failed_result(files, f"idle graph recovery failed: {exc}")
                # The same merge already retires graph orphans. Reconcile only
                # the sidecars below, preserving the existing planned-count result
                # and avoiding a second graph merge over an outdated snapshot.
                _graph_orphans_reconciled = len(_orphan_plan.get("graph") or ())
                _orphan_plan = dict(_orphan_plan, graph=set())
            # 1u8nz: execute the orphan-store reconciliation INSIDE the epoch. A
            # removal-only pass is not a no-op: it opens and finalizes this epoch
            # (the generation advance is what publishes the removals to readers).
            _orphan_stats = {"file_freshness": 0, "secret_scan_cache": 0, "graph": 0}
            if _needs_orphan_reconcile:
                _orphan_stats = _execute_orphan_store_reconcile(
                    root,
                    index_dir,
                    _orphan_plan,
                    files_for_graph=files_for_graph,
                    current_file_meta=current_file_meta,
                    graph_layer=graph_layer,
                    unreadable_dirs=_unreadable_dirs,
                    chunker_version=current_chunker_version,
                    verbose=verbose,
                    state_conn=_idle_store._conn,
                )
                _retirement = _orphan_stats.pop("graph_publication", None)
                if _retirement is not None:
                    _idle_graph_publication = _retirement.get("publication")
            _orphan_stats["graph"] += _graph_orphans_reconciled
            # The one publication transaction of the idle pass.
            if _idle_graph_publication is not None or policy_needs_refresh:
                _conn = _idle_store._conn
                try:
                    _conn.execute("BEGIN IMMEDIATE")
                    try:
                        _epoch = _conn.execute(
                            "SELECT attempt_id,status FROM build_state WHERE id=1"
                        ).fetchone()
                        if _epoch != (_idle_attempt, "building"):
                            raise RuntimeError("Prepared index attempt is no longer current")
                        if _idle_graph_publication is not None:
                            _idle_graph_publication.apply(_conn)
                            _iss_epoch.write_build_layer_state_locked(
                                _conn, {"graph": LAYER_PUBLISHED}, attempt_id=_idle_attempt,
                            )
                        _conn.execute("INSERT INTO meta(key,value) VALUES('targeted_corpus_policy',?) "
                                      "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (policy_identity,))
                        _conn.execute("COMMIT")
                    except BaseException:
                        _conn.execute("ROLLBACK")
                        raise
                except Exception as exc:  # noqa: BLE001
                    return _build_failed_result(
                        files, f"idle graph publication failed: {exc}"
                    )
        finally:
            _close_owned_build_store(_idle_store)
        _idle_heal_stats: dict = {}
        if _needs_heal or _epoch_dirty or reap_idle.get("total", 0):
            _idle_heal_stats = _sync_chunk_derived_state(
                index_dir, expected=bool(reap_idle.get("total", 0)), verbose=verbose
            )
        if _epoch_dirty or _needs_graph_recovery:
            # Refresh the walk-state bookkeeping under the recovery epoch: the
            # crashed build never wrote its own; graph-only target additions
            # also need their current walk recorded. The stat cache and
            # provenance scalars are re-recorded from the CURRENT walk merged
            # over the surviving snapshot scalars.
            _recovery_meta = {
                "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "model_versions": meta.get("model_versions", {}),
                "chunker_versions": meta.get("chunker_versions", {}),
                "walker_version": meta.get("walker_version", "") or WALKER_VERSION,
                "content": meta.get("content", []),
                "file_meta": current_file_meta,
            }
            try:
                _iss_epoch.write_build_bookkeeping(index_dir, _recovery_meta)
            except Exception as exc:  # noqa: BLE001 - converted to a structured failure
                return _build_failed_result(files, f"zero-change recovery bookkeeping write failed: {exc}")
        _idle_errors = {k: v.get("error") for k, v in _idle_heal_stats.items()
                        if isinstance(v, dict) and v.get("error")}
        if _idle_errors:
            return _build_failed_result(files, f"idle-maintenance reconcile failed: {_idle_errors}")
        if not _iss_epoch.finalize_build_epoch(index_dir, _idle_attempt):
            return _build_failed_result(files, "idle-maintenance epoch finalization CAS miss")
        _remove_legacy_meta_json(index_dir)
        if verbose:
            print("build_index: index is up to date", flush=True)
        # Wave 1x6ti (1x551): after the idle epoch finalized, so the stamp is
        # the generation that published this pass.
        _record_reap_state(
            index_dir, deferred=_reap_deferred_summary, preserved=_reap_preserved_summary,
            dry_run=dry_run, verbose=verbose,
        )
        return {
            "files_indexed": 0,
            "files_total": len(files),
            "up_to_date": True,
            "stranded_rows_reaped": reap_idle.get("total", 0),
            "stranded_rows_reaped_by_table": reap_idle,
            "stranded_reap_deferred": _reap_deferred_summary,
            "stranded_reap_preserved": _reap_preserved_summary,
            "orphan_rows_reconciled": _orphan_stats,
            "graph_recovery_attempted": _needs_graph_recovery,
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

    # If no canonical chunk tables exist yet (first build or upgrade from legacy), force a full rebuild
    # so tables are created from the complete corpus.
    if not full:
        has_vector_layers = vector_store.layer_available(index_dir, "docs") or vector_store.layer_available(index_dir, "code")
        if not has_vector_layers:
            print(
                "build_index: no initialized vector layers found — full rebuild to create index",
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
    # 1sek8: iterate the BROAD walk filtered by the per-layer stale union —
    # eligibility is already encoded in each layer's stale set, and a path can
    # be stale for one layer while current for the other (dual-output files,
    # overlapping prefixes).
    files_to_index = [
        f for f in files_for_meta
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
            # 1sek8: the emitted count reflects what the file CAN contribute
            # under the corpus definition — a code-ineligible file (e.g. a
            # test without --include-tests) contributes zero code chunks, so
            # counting its raw output would make the drift detector flag it
            # as claimed-but-empty forever.
            chunks_emitted_by_file[rel] = (
                (len(dc) if rel in docs_prefix_eligible_rel else 0)
                + (len(cc) if rel in code_eligible_rel else 0)
            )
            # 1sek8: route each chunk kind ONLY to the layer that is stale for
            # this path — a dual-output file changed for one layer must not
            # rewrite the other layer's rows (and its other-layer stale set
            # entry, if any, keeps it queued for that layer's next build).
            if build_docs and rel in layer_stale["docs"]:
                new_doc_chunks.extend(dc)
            if build_code and rel in layer_stale["code"]:
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
    # spares a docs-only edit the shared Arctic S CoreML session init for the code layer (and vice versa). Safe because
    # `_prepare_incremental_vectors` only touches the embedder when chunks are present (delete-only /
    # no-op writes never embed), so a layer with no new chunks correctly receives `None`.
    if build_docs or build_code:
        _progress(verbose, "build_index: resolving configured docs/code embedders")
    docs_embedder, code_embedder = _resolve_build_embedders(
        build_docs=build_docs,
        build_code=build_code,
        full=full,
        docs_chunk_count=len(new_doc_chunks),
        code_chunk_count=len(new_code_chunks),
    )

    # Prepare the sole SQLite semantic format.
    semantic_db_path = index_dir

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
        doc_chunks_removed = _count_chunks_for_paths(semantic_db_path, "docs", removed_files_set | updated_files_set) if build_docs else 0
        code_chunks_removed = _count_chunks_for_paths(semantic_db_path, "code", removed_files_set | updated_files_set) if build_code else 0
        doc_chunks_updated_old = _count_chunks_for_paths(semantic_db_path, "docs", updated_files_set) if build_docs else 0
        code_chunks_updated_old = _count_chunks_for_paths(semantic_db_path, "code", updated_files_set) if build_code else 0
        # removed = old chunks for removed files; updated shows net change
        doc_chunks_removed_net = doc_chunks_removed - doc_chunks_updated_old
        code_chunks_removed_net = code_chunks_removed - code_chunks_updated_old
    else:
        doc_chunks_removed_net = 0
        code_chunks_removed_net = 0

    # --- 1sed6: durable pre-mutation fence ---
    # Every path past this point mutates canonical/FTS/derived state; the FULL-
    # durable `building` epoch must exist FIRST so a crash can never leave
    # partially mutated data behind an apparently valid completed generation.
    # Readers fail closed (no complete token) until finalization.
    _iss_epoch = _get_index_state_store()
    if _iss_epoch is None:
        return _build_failed_result(files, "index-state store module unavailable — refusing to mutate without the build epoch")
    try:
        _build_attempt = _iss_epoch.begin_build_epoch(index_dir, f"{content}{':full' if full else ''}")
    except Exception as exc:  # noqa: BLE001 - fence failure fails the build
        return _build_failed_result(files, f"could not open the build epoch: {exc}")

    # Wave 1xny6: ONE connection carries this build from graph preparation to
    # the publication commit. The graph pass reads its state through it (the
    # single-binding rule: no second SQLite library on the shared file), and
    # the same connection runs `BEGIN IMMEDIATE` below, so the prepared graph
    # rows commit with the semantic rows instead of ahead of them.
    try:
        store = _iss_epoch.IndexStateStore(index_dir)
    except Exception as exc:  # noqa: BLE001 - a store that will not open fails the build
        return _build_failed_result(files, f"could not open the index store: {exc}")
    try:
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
            # it just exposed the hazard. Docs/code embedding and preparation use
            # threads; semantic writes are serialized later in one SQLite transaction.
            # Secrets scan runs as a threadpool future (project layer only).
            # CORRECTION (wave 1p8gu review MP-4): the secrets scanner DOES use a
            # ProcessPoolExecutor (spawn) internally when the changed-file set is
            # >= 50 files (wave_lint_lib/secrets_validators.check_hardcoded_secrets) —
            # the earlier "no ProcessPoolExecutor" claim here was wrong. That pool is
            # routed through subprocess_util.windowless_mp_context so its workers are
            # console-free on Windows (cross-ref MP-1), and it falls back to a serial
            # scan when a window-free context cannot be guaranteed.
            # The scanner may escalate to a complete scan (missing ledger or
            # changed rules), so it cannot respect an explicit selection.
            # Leave its content-addressed cache for the next ordinary walk.
            _run_secrets = graph_layer == "project" and selected_paths is None
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
                    # Wave 1rsh9: drift-flagged paths are exempt from the registry
                    # skip inside the incremental write — their registry rows
                    # mirror the PRE-drift canonical state and would wrongly report
                    # "unchanged", silently defeating the drift repair.
                    _skip_exempt = set(drifted)
                    # 1sek8: each table's writer receives ITS layer's stale set
                    # (plus removals) — a stale path with zero new chunks means
                    # "delete this path's rows in this table", so handing one
                    # layer's changes to the other's writer would destroy content.
                    # _layer_written collects per-table completion for the
                    # end-of-build layer-hash commit.
                    _layer_written: dict[str, set[str]] = {}
                    if build_docs:
                        def _write_docs_incr(
                            _db_path=semantic_db_path,
                            _stale=(layer_stale["docs"] | removed),
                            _doc_chunks=new_doc_chunks,
                            _docs_emb=docs_embedder,
                            _verbose=verbose,
                            _elapsed=_docs_elapsed,
                            _exempt=_skip_exempt,
                            _written=_layer_written,
                        ) -> None:
                            _t0 = time.monotonic()
                            _prepare_incremental_vectors(_db_path, _stale, _doc_chunks, _docs_emb, [], None, True, False, _verbose, skip_exempt=_exempt, written_paths=_written, prepared=prepared)
                            _elapsed.append(time.monotonic() - _t0)
                        futures.append(executor.submit(_write_docs_incr))
                    if build_code:
                        def _write_code_incr(
                            _db_path=semantic_db_path,
                            _stale=(layer_stale["code"] | removed),
                            _code_chunks=new_code_chunks,
                            _code_emb=code_embedder,
                            _verbose=verbose,
                            _elapsed=_code_elapsed,
                            _exempt=_skip_exempt,
                            _written=_layer_written,
                        ) -> None:
                            _t0 = time.monotonic()
                            _prepare_incremental_vectors(_db_path, _stale, [], None, _code_chunks, _code_emb, False, True, _verbose, skip_exempt=_exempt, written_paths=_written, prepared=prepared)
                            _elapsed.append(time.monotonic() - _t0)
                        futures.append(executor.submit(_write_code_incr))
                # Secrets scan runs as a future (project layer) — concurrent with graph.
                # Uses ThreadPoolExecutor internally for file-read parallelism so it is
                # safe to submit from here (no ProcessPoolExecutor spawn inside).
                if _run_secrets:
                    # Wave 1x4ol (1x4oj): `full` here means "rebuild the GRAPH from
                    # scratch"; it says nothing about whether any file's CONTENT
                    # changed, which is the only thing secret detection depends on.
                    # Passing it through as a full SCAN bypassed the per-file
                    # content-hash cache and re-read every tracked file on every
                    # graph rebuild (198.5 s of a 203 s command on this repository,
                    # 0 cache-skipped). A graph-only build now takes the scanner's
                    # incremental path: `changed_broad` still names every file, so
                    # every file is a candidate, and the cache skips exactly those
                    # whose content hash AND rules fingerprint match. The scanner's
                    # own escalations (rules hash, SCANNER_VERSION, missing ledger)
                    # are untouched and still force a real full scan on their own.
                    _secrets_full = bool(full) and content != "graph"
                    def _write_secrets(
                        _root=root,
                        _index_dir=index_dir,
                        _changed=changed_broad,
                        _removed=removed_broad,
                        _full=_secrets_full,
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
                        db_path=semantic_db_path,
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
                        docs_eligible_rel=docs_eligible_rel if build_docs else None,
                        code_eligible_rel=code_eligible_rel if build_code else None,
                        prepared=prepared,
                        strict_reads=storage_rebuild,
                    )
                # Wave 1p2q3 (1p2wd post-ship 1.3.22 / Bug 4 part 2): graph
                # extraction runs synchronously on the main thread, concurrently
                # with the in-flight docs/code/secrets futures above. This is the
                # load-bearing fix for the field-reported hang — see the long comment at the
                # top of this try-block.
                _graph_artifacts = _build_graph_artifacts(
                    root=root,
                    index_dir=index_dir,
                    layer=graph_layer,
                    state_conn=store._conn,
                    **({"selected_paths": selected_paths} if selected_paths is not None else {}),
                    files=files_for_graph,
                    current_file_meta=current_file_meta,
                    changed=changed_for_graph,
                    removed=removed,
                    # Wave 1x54z (1u8o3): on an incremental build the merge keeps
                    # known paths under a directory the walk could not read (they
                    # are carried forward as unchanged everywhere else); a FULL
                    # rebuild prepares graph state from the current corpus. The
                    # semantic removal guard below refuses publication if omitted
                    # prior paths are unreadable; the global epoch stays unavailable.
                    unreadable_dirs=(_unreadable_dirs if not full else None),
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
            # incremental drift check sees the truth once the bookkeeping is written below.
            for rel, count in chunks_emitted_by_file.items():
                entry = current_file_meta.get(rel)
                if isinstance(entry, dict):
                    entry["chunks_emitted"] = count

            # Counts are computed after the prepared transaction publishes below.
            total_doc_chunks = total_code_chunks = 0
        except Exception as exc:
            print(f"build_index: index update failed: {exc}", file=sys.stderr)
            raise
        _graph_publication = _graph_artifacts.get("publication")

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
            new_model_versions["docs"] = (
                f"{DOCS_MODEL}@{docs_class}@{_identity_fingerprint_for_class(docs_class)}"
            )
        if build_code:
            code_class = (
                _predicted_precision_class(CODE_MODEL, build_providers)
                if code_embedder is not None
                else _precision_class_from_version(old_model_versions.get("code"))
            )
            new_model_versions["code"] = (
                f"{CODE_MODEL}@{code_class}@{_identity_fingerprint_for_class(code_class)}"
            )
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
        # Wave 1rsh9 (1rrr0) established the store as the working source of truth
        # for per-path build state; 1sed6 made it the ONLY truth (meta.json retired).
        # --- 1sed6: canonical build metadata is a MANDATORY store resident ---
        # No JSON export, no fallback: a bookkeeping failure fails the build
        # visibly (the epoch is never finalized, readers stay failed-closed, and
        # the next build retries from durable state). The silent
        # JSON-success/SQLite-failure mode this replaced could publish an index
        # state the system cannot actually serve.
        _state_store = _get_index_state_store()
        if _state_store is None:
            return _build_failed_result(
                files, "index-state store module unavailable — cannot record canonical build state"
            )
        # Reap canonical rows whose path is no longer in the current eligible set.
        # Runs on every incremental update across both tables — the workflow-
        # config-evolution blind spot is invisible from the build snapshot alone (the
        # narrowing already updated meta), so the reaper must reconcile canonical chunks
        # directly. Reaping both tables regardless of ``content`` arg keeps the
        # cross-content failure mode closed: a docs-only update reaps code-table
        # orphans (and vice versa). Full rebuilds drop the tables entirely so
        # this pass is a no-op there. Runs BEFORE the chunk-index reconcile below
        # so the FTS/registry never retain reaped (excluded) content between builds.
        stranded_rows_reaped = 0
        stranded_rows_reaped_by_table: dict[str, int] = {"docs": 0, "code": 0, "total": 0}
        orphan_rows_reconciled: dict[str, int] = {"file_freshness": 0, "secret_scan_cache": 0, "graph": 0}
        _reap_deferred_build: dict = {}
        _reap_preserved_build: dict = {}
        _reap_paths_by_table: dict = {}
        if not full:
            reap_result = _reap_stranded_vector_rows(
                semantic_db_path,
                set(current_file_meta.keys()),
                root=root,
                tables=("docs", "code"),
                verbose=verbose,
                eligible_by_table={"docs": docs_eligible_rel, "code": code_eligible_rel},
                unreadable_dirs=_unreadable_dirs,
                prepared=prepared,
            )
            _reap_paths_by_table = reap_result.pop("paths_by_table", {})
            _reap_preserved_build = _preserved_summary(reap_result.pop("preserved_by_table", None))
            _reap_deferred_build = _deferred_summary(reap_result.pop("deferred_by_table", None))
            stranded_rows_reaped_by_table = reap_result
            stranded_rows_reaped = reap_result.get("total", 0)
            # 1u8nz: orphan-store reconciliation at the build-path reap seam (same
            # epoch). By this point the ordinary graph merge above already pruned
            # store-minus-walk, so the plan's graph set is normally empty here;
            # the sidecars (file_freshness / secret_scan_cache) are the stores
            # that leak on ordinary incrementals and get reconciled now.
            _orphan_plan_build = _plan_orphan_store_reconcile(
                root, index_dir, set(current_file_meta.keys()), verbose=verbose,
                unreadable_dirs=_unreadable_dirs,
            )
            # Wave 1xny6: the graph merge above ran with full walk parity and its
            # prepared publication already retires every known-minus-current path
            # — but it has not COMMITTED yet, so the plan (which reads published
            # rows) still lists them. Running a second merge here would prepare a
            # rival plan from pre-publication state and overwrite the first. Take
            # the retirement count from the plan that is actually publishing.
            if selected_paths is not None:
                _orphan_plan_build = {k: (set(v) & selected_paths if k in _ORPHAN_RECONCILE_STORES else v)
                                      for k, v in _orphan_plan_build.items()}
            _planned_graph_orphans = set(_orphan_plan_build.get("graph") or ())
            if _graph_publication is not None and _planned_graph_orphans:
                orphan_rows_reconciled["graph"] = len(
                    _planned_graph_orphans & set(_graph_publication.file_deletes)
                )
                _orphan_plan_build = dict(_orphan_plan_build, graph=set())
            if any(_orphan_plan_build.get(k) for k in _ORPHAN_RECONCILE_STORES):
                _sidecar_stats = _execute_orphan_store_reconcile(
                    root,
                    index_dir,
                    _orphan_plan_build,
                    files_for_graph=files_for_graph,
                    current_file_meta=current_file_meta,
                    graph_layer=graph_layer,
                    unreadable_dirs=_unreadable_dirs,
                    chunker_version=current_chunker_version,
                    verbose=verbose,
                    state_conn=store._conn,
                )
                # Only reachable when the graph pass published nothing this build
                # (its zero-change fast path). There is then no rival plan, so the
                # retirement becomes THE graph participant of this transaction.
                _retirement = _sidecar_stats.pop("graph_publication", None)
                if _retirement is not None:
                    _graph_publication = _retirement.get("publication")
                _sidecar_stats["graph"] += orphan_rows_reconciled["graph"]
                orphan_rows_reconciled = _sidecar_stats

        # One native writer transaction publishes vectors, text, FTS, the graph,
        # extraction and community rows, and all indexing state (wave 1xny6). The
        # connection is the one the graph pass already read through.
        _publication_held_ms = 0.0
        _graph_rows_written: dict = {}
        try:
            conn = store._conn
            conn.execute("BEGIN IMMEDIATE")
            _held_t0 = time.monotonic()
            try:
                epoch = conn.execute("SELECT attempt_id,status FROM build_state WHERE id=1").fetchone()
                if epoch != (_build_attempt,"building"):
                    raise RuntimeError("Prepared index attempt is no longer current")
                def validate_sources():
                    if storage_rebuild and preflight_rebuild_sources(root, index_dir, **rebuild_options) != rebuild_inventory:
                        raise RuntimeError("storage_rebuild_source_changed: retry the complete rebuild")
                    current_identity = (DOCS_MODEL, CODE_MODEL, WALKER_VERSION,
                                        getattr(_get_chunker(), "CHUNKER_VERSION", ""))
                    current_config = _sha256(config_path) if config_path.is_file() else None
                    if current_identity != prepared_identity or current_config != prepared_config_hash:
                        raise RuntimeError("Model/chunker/configuration changed during embedding; retry indexing")
                    for rel in chunks_emitted_by_file:
                        expected = current_file_meta.get(rel,{}).get("hash")
                        if expected and _sha256(root / rel) != expected:
                            raise RuntimeError(f"Source changed during embedding: {rel}; retry indexing")
                    _validate_prepared_removals(
                        root, index_dir, removed_broad,
                        {layer: set(_reap_paths_by_table.get(layer, ())) | _full_removed_by_layer[layer]
                         for layer in ("docs", "code")}, requested_files=requested_files,
                        respect_ignore=respect_ignore, include_prefixes=include_prefixes,
                        project_include_prefixes=project_include_prefixes,
                        include_tests=include_tests, include_generated=include_generated)
                validate_sources()
                prepared.apply(store)
                _state_store.write_build_bookkeeping_locked(conn,new_meta)
                conn.execute("INSERT INTO meta(key,value) VALUES('targeted_corpus_policy',?) "
                             "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (policy_identity,))
                if full:
                    for layer, enabled, eligible in (("docs",build_docs,docs_eligible_rel),("code",build_code,code_eligible_rel)):
                        if enabled:
                            conn.execute("DELETE FROM layer_path_state WHERE layer=?", (layer,))
                            conn.executemany("INSERT INTO layer_path_state(layer,path,hash) VALUES(?,?,?)",
                                ((layer,r,current_file_meta[r]['hash']) for r in eligible if r in current_file_meta))
                else:
                    for layer, written in _layer_written.items():
                        conn.executemany("INSERT INTO layer_path_state(layer,path,hash) VALUES(?,?,?) "
                            "ON CONFLICT(layer,path) DO UPDATE SET hash=excluded.hash",
                            ((layer,r,current_file_meta[r]['hash']) for r in written if r in current_file_meta))
                        conn.executemany("DELETE FROM layer_path_state WHERE layer=? AND path=?",
                            ((layer,r) for r in set(removed_broad) | set(_reap_paths_by_table.get(layer,()))))
                for layer in ("docs", "code"):
                    integrity = vector_store.vector_integrity(conn, layer)
                    if integrity['missing_vectors'] or integrity['orphan_vectors']:
                        raise RuntimeError(f"{layer}: vector integrity failed "
                                           f"({integrity['missing_vectors']} missing, "
                                           f"{integrity['orphan_vectors']} orphaned); explicit full rebuild required")
                if storage_rebuild and build_docs and build_code:
                    sqlite_storage_migration.record_rebuild_proof(
                        conn, storage_receipt, rebuild_inventory, rebuild_options, new_meta, _build_attempt)
                # Per-layer publication state: which generation and attempt each
                # layer was last published under. A layer this build did not
                # publish keeps its own row, so a graph-only build never advertises
                # semantic freshness it did not establish, and vice versa. The
                # scalar build_state.generation stays THE reader token; these rows
                # describe layers relative to it.
                _state_store.write_build_layer_state_locked(
                    conn,
                    _layer_publication_state(
                        build_docs=build_docs,
                        build_code=build_code,
                        graph_published=_graph_publication is not None,
                        graph_sources_changed=bool(changed_for_graph or removed),
                    ),
                    attempt_id=_build_attempt,
                )
                validate_sources()
                # Graph, extraction and community rows join the semantic rows as
                # participants. Everything expensive already happened outside this
                # lock; `apply` does a cheap (size, mtime_ns) recheck and a
                # change-sized set of writes. It runs AFTER the trailing
                # `validate_sources` so the broad content-hash gate reports a
                # source that moved during embedding; the graph's stat recheck is
                # the last-mile guard for the window this gate does not cover
                # (files the graph indexes that emitted no semantic chunks).
                if _graph_publication is not None:
                    _graph_rows_written = _graph_publication.apply(conn)
                    _graph_rows_written["planned_total"] = _graph_publication.row_count()
                conn.execute("COMMIT")
                # The lock-held segment: BEGIN IMMEDIATE to COMMIT. Reported on
                # every build so the incremental publication cost is observable in
                # the field, not only under a benchmark.
                _publication_held_ms = (time.monotonic() - _held_t0) * 1000.0
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        except Exception as exc:
            return _build_failed_result(files, f"Atomic semantic publication failed: {exc}")
        # Wave 1xny6 lane L6b: the transitional graph and cluster JSON writers that
        # ran here are retired. The committed rows are the graph's only authority
        # and every reader is on them, so ordinary indexing no longer recreates the
        # retired `.wavefoundry/index/graph/` directory.
    finally:
        _close_owned_build_store(store)
    _counts = vector_store.layer_counts(index_dir)
    total_doc_chunks, total_code_chunks = _counts["docs"], _counts["code"]

    # Verify derived FTS/registry state against the canonical rows just
    # committed. Repair derived damage without replacing vectors or text.
    _reconcile_stats = _sync_chunk_derived_state(
        index_dir,
        expected=bool(full or rechunk_all or stranded_rows_reaped),
        verbose=verbose,
    )
    _reconcile_errors = {k: v.get("error") for k, v in _reconcile_stats.items()
                         if isinstance(v, dict) and v.get("error")}
    if _reconcile_errors:
        # 1sed6 Req 2: chunk registry + FTS are mandatory residents — a
        # failed reconcile leaves the epoch un-finalized (readers stay
        # failed-closed) instead of publishing an index the lexical layer
        # cannot serve.
        return _build_failed_result(files, f"chunk-index reconcile failed: {_reconcile_errors}")

    # Wave 1rsh9 (1rq4h): refresh the index-state store's freshness/attribution
    # tables in one transaction per build pass — still inside the index-build
    # lock. Zero-change builds skip on the git-HEAD + path-set fingerprint;
    # end-of-build maintenance (passive WAL checkpoint + bounded incremental reclamation) keeps the
    # store bounded under the long-lived MCP server. Never fails the build.
    # These optional derived summaries recompute the whole corpus; a targeted
    # patch must not rewrite unselected freshness/attribution rows.
    if _state_store is not None and selected_paths is None:
        _state_store.update_freshness_from_build(
            root, index_dir, current_file_meta.keys(), verbose=verbose
        )
        # Wave 1ro44 (1ro43): wave→files attribution + doc-code drift, the
        # second optional resident sharing the freshness posture. Skips on a
        # git-HEAD + docs-path-set + verification-stamp fingerprint (stamps
        # move drift anchors without moving HEAD, so they participate).
        _drift_summary = _state_store.update_drift_from_build(
            root,
            index_dir,
            [p for p in current_file_meta if p.endswith((".md", ".markdown"))],
            current_file_meta.keys(),
            verbose=verbose,
        )
        # Round-4 re-review (4) P1: drift COMPUTATION failures stay optional (the
        # attribution/drift table is a ranking-decay resident, not readiness) —
        # but a `drift_clear_failed` is DIFFERENT: a CONFIRMED git→non-git
        # transition whose stale-drift clear could not complete. Publishing the
        # epoch would report success while serving a stale `drifted: true` row
        # no reader re-clears. FAIL before finalize so the retry re-attempts.
        if isinstance(_drift_summary, dict) and _drift_summary.get("drift_clear_failed"):
            return _build_failed_result(
                files,
                "confirmed git→non-git transition could not clear stale drift "
                f"({_drift_summary.get('error', 'clear failed')}) — failing before "
                "epoch publish so the stale drift is not served behind a successful "
                "build; the next build retries the clear",
            )

    # --- 1sed6: finalize the build epoch (attempt-ID compare-and-set) ---
    # Every mandatory resident succeeded above (canonical bookkeeping, layer
    # hashes, chunk registry + FTS via the gated reconcile); freshness/
    # attribution is the enumerated OPTIONAL resident (its consumer is
    # ranking decay, not readiness). Only this CAS advances the generation
    # readers trust; a miss means a newer attempt superseded this build.
    # Rear guard (review fix): completion may only publish when every PRESENT
    # canonical chunk layer has provenance in the canonical state just written. The
    # front gate escalates scoped builds around the hole; this catches any
    # path that slipped through so `complete` can be trusted globally.
    _unprovenanced_at_publish = [
        layer for layer in ("docs", "code")
        if vector_store.layer_available(index_dir, layer)
        and not (new_meta.get("model_versions") or {}).get(layer)
    ]
    if _unprovenanced_at_publish:
        return _build_failed_result(
            files,
            "refusing to publish completion: no provenance recorded for present "
            f"table(s): {', '.join(_unprovenanced_at_publish)} — run index_build(content='all')",
        )
    if not _iss_epoch.finalize_build_epoch(index_dir, _build_attempt):
        return _build_failed_result(files, "build epoch finalization CAS miss (superseded attempt)")
    if _remove_legacy_meta_json(index_dir) and verbose:
        print("build_index: removed legacy meta.json (SQLite is the state authority)", flush=True)
    # Wave 1x6ti (1x551): after `finalize_build_epoch` succeeded, so the stamp
    # is the generation that published the state the record describes. A full
    # rebuild defers and preserves nothing (both reap seams sit behind
    # `not full`), so this call REMOVES the record on the full path.
    _record_reap_state(
        index_dir, deferred=_reap_deferred_build, preserved=_reap_preserved_build,
        dry_run=dry_run, verbose=verbose,
    )

    summary = {
        "files_indexed": len(files_to_index),
        "files_total": len(files),
        "doc_chunks": total_doc_chunks,
        "code_chunks": total_code_chunks,
        "up_to_date": False,
        "stranded_rows_reaped": stranded_rows_reaped,
        "stranded_rows_reaped_by_table": stranded_rows_reaped_by_table,
        "stranded_reap_deferred": _reap_deferred_build,
        "stranded_reap_preserved": _reap_preserved_build,
        "orphan_rows_reconciled": orphan_rows_reconciled,
        "publication_held_ms": round(_publication_held_ms, 3),
        "graph_rows_written": _graph_rows_written,
    }
    files_summary = f"{len(added)} added, {len(updated)} updated, {len(removed)} removed"
    if build_docs:
        if full:
            # Wave 1p5ch: the streaming rebuild never materializes new_doc_chunks,
            # so report the rows actually written (from the canonical chunk layer count above).
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
    # build creates a self-referential write→reindex loop. Regeneration belongs to
    # create-mode prepare-and-open/close, upgrade, forced index_build content="map",
    # the direct change-only CLI, and the resource's missing-file fallback. Ready-only
    # and dry-run lifecycle modes and reads of an existing map do not regenerate it.

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

        result = build_index(
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
        # Review fix: a structured build failure must reach subprocess callers
        # (setup, MCP index_build, hooks) as a non-zero exit — the epoch
        # was deliberately left incomplete and success reporting would mask it.
        if isinstance(result, dict) and result.get("failed"):
            print(f"build_index: exiting 1 — {result.get('failure', 'build failed')}", file=sys.stderr, flush=True)
            return 1
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
