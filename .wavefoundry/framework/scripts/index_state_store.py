#!/usr/bin/env python3
"""Semantic-index SQLite state store (wave 1rsh9 / 1rq4h).

One derived-only relational store for semantic-index sidecar state, at
``.wavefoundry/index/index-state.sqlite``. First resident schema: the
freshness/attribution tables consumed by the churn-aware retrieval decay work
(``1ro43``) and the memory layer (``1p8gy``). Follow-on residents: FTS5
lexical tables + per-path bookkeeping (``1rrr0``) and the secret-scan cache
(``1rsha``).

Extracted ALONGSIDE the graph state store (``GraphStateStore`` in
``graph_indexer.py``) rather than by refactoring it — the graph store is
landed, reviewed machinery whose build-path behavior must stay untouched
(1rq4h AC-7). This module generalizes its proven posture: WAL journaling +
``synchronous=NORMAL``, ``busy_timeout``, version-gated whole-store
invalidation, and reset-and-recreate on a corrupted open.

**Derived-only rule (the operational safety property):** every table must be
rebuildable from git, Lance, and the repo itself (1sed6: the store IS the
sole build-state authority — there is no meta.json). A missing, corrupt,
or schema-mismatched store is a rebuild with a loud diagnostic — never data
loss, never a hard failure, never silent data invention.

**Maintenance posture (1rq4h Req 9):** ``auto_vacuum=INCREMENTAL`` at store
creation; ``wal_checkpoint(TRUNCATE)`` + ``incremental_vacuum`` at the end of
each build pass (the long-lived MCP server reads this store on the query
path, so a pinned reader could otherwise starve WAL autocheckpoint);
``PRAGMA optimize`` at connection close. Full ``VACUUM`` is reserved for the
on-demand ``index_optimize`` path (``optimize_state_stores``).

**Integrity posture (1rq4h Req 11):** two-layer probe. Physical/structural —
``PRAGMA quick_check`` at open and in routine maintenance, full
``PRAGMA integrity_check`` on the on-demand optimize path. Logical/staleness —
resident schemas bind their derived tables to a source-of-truth fingerprint
(git HEAD for freshness; Lance chunk-set / rules-hash for later residents)
recorded in ``meta``, so a structurally-sound-but-stale store is detected
too. Any failure routes to the derived-only drop-and-rebuild.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Optional

sys.dont_write_bytecode = True

_scripts_dir = str(Path(__file__).resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)
import subprocess_util  # shared subprocess isolation (wave 1p8gu)  # noqa: E402

STATE_STORE_FILENAME = "index-state.sqlite"

# Store schema version. Whole-store invalidation on mismatch (the graph
# store's proven semantics): bump when any resident table's shape changes.
# Resident-schema bumps are SEQUENCED, not concurrent (wave 1rsh9 watchpoint):
# 1rq4h shipped "1" (freshness/attribution); 1rrr0 bumped to "2" (FTS5 lexical
# tables + per-path bookkeeping + chunk registry); 1rsha bumped to "3"
# (per-file secret-scan cache + Tier-2-ready rule catalog); 1sauc bumped to
# "4" (FTS tables gain language/tags UNINDEXED columns for the code_search
# filter-parity contract after the Lance/Tantivy FTS retirement); 1sek8
# bumped to "5" (per-layer last-embedded hash state — the content-scope
# change-detection substrate; the reset this bump forces is intentionally
# also the fleet-wide freshness heal, since empty layer state reads as
# all-stale and the first build reconverges with vector reuse); 1sed6
# bumped to "6" (build_state epoch row — the SQLite-only authority contract:
# attempt-ID fenced builds, completed-generation reader tokens; the reset
# doubles as legacy convergence since an uninitialized epoch fails readers
# closed until the first completed build).
STATE_STORE_SCHEMA_VERSION = "6"

# Freshness extraction tuning (1ro43 Req 1: "commit count touching the file
# over a trailing window, normalized"; window + normalization are named
# constants per 1ro43 Req 8).
FRESHNESS_CHURN_WINDOW_DAYS = 180   # trailing git-log window for churn counting
FRESHNESS_CHURN_NORMALIZE_COMMITS = 30  # churn_score = min(1.0, commits_in_window / this)
# Cap on the single batched git-log pass. Beyond the cap (very deep
# histories), unresolved files fall back to filesystem mtime with
# source='mtime' — honest, and refreshed once HEAD moves again.
FRESHNESS_GIT_LOG_MAX_COMMITS = 50000

# Meta keys for the logical-staleness binding (integrity layer 2). The
# freshness schema binds to git HEAD: churn/last_modified derive from commit
# history, so a stored fingerprint equal to the current HEAD means the tables
# are current by construction.
META_FRESHNESS_FINGERPRINT = "freshness_fingerprint"
META_FRESHNESS_PATHS_HASH = "freshness_paths_hash"
META_FRESHNESS_UPDATED_AT = "freshness_updated_at"

# --- Doc-code drift + wave attribution (1ro43) ---
# Drift threshold: distinct commits touching a doc's referenced code paths
# after the doc's anchor before the doc is drift-flagged. One or two commits
# is routine churn (format sweeps, rename fallout) that rarely invalidates
# prose; three distinct commits is sustained divergence worth an agent's
# suspicion. Drift is a proposal, never a verdict — the census (AC-8) records
# this repository's calibration evidence before any ranking use.
DRIFT_COMMITS_THRESHOLD = 3
META_DRIFT_FINGERPRINT = "drift_fingerprint"
META_DRIFT_UPDATED_AT = "drift_updated_at"

# Verification stamp (1ro43 Req 10): a frontmatter-adjacent line recording the
# commit a doc was deliberately reviewed against. Written only by an agentic
# verification pass or the operator; ``docs_gardener`` cannot touch it by
# construction (its only edit is the ``Last verified:`` date substitution).
# Abbreviated hex (>= 7 chars) is accepted and resolved against local history;
# an unresolvable stamp degrades to the content-change anchor.
VERIFICATION_STAMP_FIELD = "Verified against"
VERIFICATION_STAMP_PATTERN = re.compile(
    r"^Verified against:\s*([0-9a-fA-F]{7,40})\s*$", re.MULTILINE
)
VERIFICATION_STAMP_LINE = re.compile(r"^Verified against:.*$", re.MULTILINE)

# Wave-id token for landing-commit derivation: five base36 chars, digit-led,
# with at least one letter. Rejects bare numbers ("2026") and can never match
# dotted versions ("Land 1.8.0:") since "." is outside the class — version-only
# landing subjects therefore degrade to plain churn by construction.
WAVE_ID_TOKEN = re.compile(r"\b(?=[0-9]*[a-z])[0-9][a-z0-9]{4}\b")

# --- FTS5 lexical layer (1rrr0) ---
# One FTS5 table per Lance content table, keyed by chunk id. Mode decision
# (recorded in the change doc's Decision Log): CONTENTFUL — a plain fts5
# table storing the chunk text. Contentless tables cannot delete rows without
# ``contentless_delete`` (SQLite >= 3.43), which field interpreters cannot be
# assumed to have; the second text copy is anticipated and posture-tested
# (1rrr0 Req 11/AC-8), and display text always comes from Lance regardless.
# Tokenizer: unicode61 with ``_`` as a token character — the lexical layer
# exists for the documented dense-retrieval weak patterns (exact identifiers,
# rare tokens, error strings), so compound identifiers must stay whole
# tokens; concept/sub-word queries are the dense layer's job.
FTS_TABLES = {"docs": "fts_docs", "code": "fts_code"}
FTS_TOKENIZER = "unicode61 tokenchars '_'"
# In-build segment-merge gate (the FTS analog of LANCEDB_COMPACT_THRESHOLD):
# when cumulative insert+delete churn since the last merge exceeds this, a
# bounded ``('merge', N)`` runs in-build; the full ``'optimize'`` runs on the
# on-demand/setup/upgrade path (sqlite_store_maintenance).
FTS_MERGE_CHURN_THRESHOLD = 2000
FTS_MERGE_PAGES = 64
META_FTS_AVAILABLE = "fts5_available"
META_FTS_CHURN_PREFIX = "fts_churn_"          # + table_name → cumulative churn counter
META_FTS_FINGERPRINT_PREFIX = "fts_fingerprint_"  # + table_name → chunk-id-set fingerprint
# Set at store creation/reset; cleared by the first reconcile. Marks the
# rebuild-from-Lance as expected provisioning (install/upgrade/schema bump),
# not a crash repair — even when partial in-build deltas preceded it.
META_CHUNK_INDEX_COLD = "chunk_index_cold"
# Recorded at every successful reconcile (1sbfj): the Lance RAW row count and
# the registry's unique-id count at sync time, per table. Lance ids are not
# unique (incremental churn leaves duplicate-id rows), so a raw-vs-registry
# compare misreads a fully-synced store as under-covered; exact comparison
# against these sync-time counts is both cheaper and correct. Absent on
# stores that have not reconciled under this code yet — consumers fall back
# to the proportional raw-vs-registry threshold.
META_CHUNK_SYNC_RAW_PREFIX = "chunk_sync_raw_"        # + table_name
META_CHUNK_SYNC_UNIQUE_PREFIX = "chunk_sync_unique_"  # + table_name

# --- Persisted store log (1sbfj) ---
# The store's one-time diagnostics (cold-store provisioning, crash-window
# reconciliation, reconcile skips, legacy-FTS drops) previously went to raw
# stdout/stderr only — unrecoverable once the build process exited, which
# blinded a field investigation twice. They are now ALSO appended here,
# best-effort and bounded. Lives beside upgrade.log under .wavefoundry/logs/.
STORE_LOG_FILENAME = "index-state.log"
STORE_LOG_MAX_BYTES = 512 * 1024

# Path of the graph state store relative to the index dir. Duplicated from
# graph_indexer's GRAPH_DIRNAME/GRAPH_STORE_FILENAMES rather than imported —
# importing graph_indexer pulls its tree-sitter machinery into every store
# consumer. A wiring test asserts this stays in sync with graph_indexer.
GRAPH_STATE_STORE_RELPATH = "graph/project-graph-state.sqlite"

_VERSION_KEYS = ("store_schema_version",)


def state_store_path(index_dir: Path) -> Path:
    return Path(index_dir) / STATE_STORE_FILENAME


def store_log_path(index_dir: Path) -> Path:
    """Persisted store-log path: ``.wavefoundry/logs/index-state.log``."""
    return Path(index_dir).parent / "logs" / STORE_LOG_FILENAME


def store_log(index_dir: Path, message: str) -> bool:
    """Append one timestamped line to the persisted store log (1sbfj).

    Best-effort by contract: never raises, never fails a build. Bounded:
    when the log exceeds ``STORE_LOG_MAX_BYTES`` the newest half is kept
    (truncate-and-continue — concurrent writers at worst interleave lines,
    they cannot fail each other). Callers keep their stdout/stderr prints;
    this is the persistence layer, not a replacement.

    Returns ``True`` when the line durably appended, ``False`` on any
    swallowed filesystem failure (release-review fix: callers that gate
    retry/dedup state on persistence must check the return — a swallowed
    failure previously read as success and suppressed the retry forever).
    """
    try:
        log_path = store_log_path(index_dir)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if log_path.is_file() and log_path.stat().st_size > STORE_LOG_MAX_BYTES:
                tail = log_path.read_bytes()[-(STORE_LOG_MAX_BYTES // 2):]
                # Cut at a line boundary so the kept tail starts clean.
                newline = tail.find(b"\n")
                if 0 <= newline < len(tail) - 1:
                    tail = tail[newline + 1:]
                log_path.write_bytes(tail)
        except OSError:
            pass
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"{stamp} {message}\n")
        return True
    except Exception:  # noqa: BLE001 - logging must never fail the caller
        return False


_FTS5_AVAILABLE: Optional[bool] = None


def fts5_available() -> bool:
    """One-time probe: does this interpreter's SQLite ship FTS5?

    Cached per process. Absence degrades cleanly (1rrr0 Req 1): no lexical
    tables are created, queries stay vector-only, no errors anywhere.
    """
    global _FTS5_AVAILABLE
    if _FTS5_AVAILABLE is None:
        try:
            probe = sqlite3.connect(":memory:")
            try:
                probe.execute("CREATE VIRTUAL TABLE fts5_probe USING fts5(t)")
                _FTS5_AVAILABLE = True
            finally:
                probe.close()
        except sqlite3.Error:
            _FTS5_AVAILABLE = False
    return _FTS5_AVAILABLE


def _store_sidecar_paths(path: Path) -> list[Path]:
    return [Path(f"{path}{suffix}") for suffix in ("", "-wal", "-shm")]


def _delete_store_files(path: Path) -> None:
    for p in _store_sidecar_paths(path):
        try:
            os.unlink(p)
        except OSError:
            pass


def _store_size_bytes(path: Path) -> int:
    """Total on-disk size of the store including -wal/-shm sidecars."""
    total = 0
    for p in _store_sidecar_paths(path):
        try:
            total += p.stat().st_size
        except OSError:
            pass
    return total


def _quick_check_ok(conn: "sqlite3.Connection") -> bool:
    row = conn.execute("PRAGMA quick_check").fetchone()
    return bool(row) and str(row[0]).lower() == "ok"


class IndexStateStore:
    """The semantic-index state store: substrate + resident schemas.

    Durability and error posture mirror the graph state store: WAL +
    ``synchronous=NORMAL`` (atomic commit; an OS crash can at worst lose the
    last commit — a re-buildable build, never a torn store); a corrupted or
    structurally-damaged database at open time is loudly deleted and
    recreated (derived-only: the next build repopulates); a schema-version
    mismatch resets the whole store.
    """

    def __init__(self, index_dir: Path, *, read_only: bool = False) -> None:
        self.index_dir = Path(index_dir)
        self.path = state_store_path(self.index_dir)
        self.read_only = read_only
        if read_only:
            # Read-only open never creates or repairs; callers get None-ish
            # behavior via `open_read_only` instead. Kept for API symmetry.
            self._conn = sqlite3.connect(
                f"file:{self.path.as_posix()}?mode=ro", uri=True, timeout=10.0
            )
            self._conn.execute("PRAGMA busy_timeout=10000")
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = self._open()
        except sqlite3.Error:
            # Corrupted/unreadable database file (or quick_check structural
            # failure): loudly delete and recreate. Derived-only — the empty
            # store forces repopulation on this and later builds.
            print(
                f"index-state-store: store unreadable or corrupt at {self.path} — "
                "resetting store (derived-only; tables repopulate on rebuild)",
                file=sys.stderr,
                flush=True,
            )
            _delete_store_files(self.path)
            self._conn = self._open()

    def _open(self) -> "sqlite3.Connection":
        creating = not self.path.exists()
        conn = sqlite3.connect(str(self.path), timeout=10.0)
        try:
            if creating:
                # Must be set before the first table is created to take
                # effect without a full VACUUM (1rq4h Req 9 / AC-8).
                conn.execute("PRAGMA auto_vacuum=INCREMENTAL")
            journal_mode = str(
                (conn.execute("PRAGMA journal_mode=WAL").fetchone() or [""])[0]
            )
            if journal_mode.lower() != "wal":
                print(
                    f"[index-state-store] WARNING: journal_mode=WAL refused "
                    f"(got {journal_mode!r}); store at {self.path} may be on a "
                    f"filesystem with unreliable locking",
                    file=sys.stderr,
                )
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=10000")
            if not creating and not _quick_check_ok(conn):
                # Proactive structural probe at open (1rq4h Req 11): upgrade
                # from the reactive "reset when a read raises" posture.
                raise sqlite3.DatabaseError("quick_check failed")
            self._create_tables(conn)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            raise
        return conn

    def _create_tables(self, conn: "sqlite3.Connection") -> None:
        with conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            # --- Freshness/attribution resident schema (1rq4h, consumed by 1ro43/1p8gy) ---
            conn.execute(
                "CREATE TABLE IF NOT EXISTS file_freshness ("
                "path TEXT PRIMARY KEY, "
                "last_modified INTEGER, "            # unix ts: last git commit touching path (mtime fallback)
                "churn_score REAL NOT NULL DEFAULT 0.0, "
                "commit_count INTEGER NOT NULL DEFAULT 0, "  # raw commits in the trailing window
                "source TEXT NOT NULL DEFAULT 'git', "       # 'git' | 'mtime'
                "updated_at INTEGER NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS file_commits ("
                "path TEXT NOT NULL, "
                "commit_sha TEXT NOT NULL, "
                "commit_ts INTEGER NOT NULL, "
                "PRIMARY KEY (path, commit_sha))"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_file_commits_path_ts "
                "ON file_commits (path, commit_ts)"
            )
            # Wave→landing-commit attribution (shapes per 1ro43 Req 12; the
            # derivation logic lands with 1ro43 — this change ships storage).
            conn.execute(
                "CREATE TABLE IF NOT EXISTS wave_landing ("
                "wave_id TEXT NOT NULL, "
                "commit_sha TEXT NOT NULL, "
                "landed_at INTEGER, "
                "PRIMARY KEY (wave_id, commit_sha))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS wave_change_files ("
                "wave_id TEXT NOT NULL, "
                "path TEXT NOT NULL, "
                "PRIMARY KEY (wave_id, path))"
            )
            # Per-doc drift summaries (shapes per 1ro43 Req 3 + Req 13; the
            # drift computation lands with 1ro43 — this change ships storage).
            conn.execute(
                "CREATE TABLE IF NOT EXISTS doc_drift ("
                "path TEXT PRIMARY KEY, "
                "drifted INTEGER NOT NULL DEFAULT 0, "
                "drift_refs TEXT NOT NULL DEFAULT '[]', "     # JSON array of referenced paths
                "commits_since INTEGER NOT NULL DEFAULT 0, "
                "anchor_kind TEXT NOT NULL DEFAULT 'content', "  # 'content' | 'verification'
                "historical INTEGER NOT NULL DEFAULT 0, "
                "waves_behind INTEGER NOT NULL DEFAULT 0, "
                "updated_at INTEGER NOT NULL)"
            )
            # --- Per-path bookkeeping + chunk registry resident schema (1rrr0) ---
            # The store is the working source of truth for per-path build
            # state; the snapshot readers reconstruct the dict shape from
            # exported, reader-contract-compatible snapshot.
            conn.execute(
                "CREATE TABLE IF NOT EXISTS build_file_meta ("
                "path TEXT PRIMARY KEY, "
                "hash TEXT NOT NULL DEFAULT '', "
                "mtime REAL, "
                "size INTEGER, "
                "inode INTEGER, "
                "chunks_emitted INTEGER)"     # NULL = unknown (legacy entry)
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS build_layer_meta ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS chunk_registry ("
                "table_name TEXT NOT NULL, "
                "chunk_id TEXT NOT NULL, "
                "path TEXT NOT NULL, "
                "chunk_hash TEXT NOT NULL DEFAULT '', "
                "PRIMARY KEY (table_name, chunk_id))"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunk_registry_path "
                "ON chunk_registry (table_name, path)"
            )
            # --- FTS5 lexical resident schema (1rrr0) — capability-gated ---
            fts_ok = fts5_available()
            prev_fts = self._get_meta(conn, META_FTS_AVAILABLE)
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (META_FTS_AVAILABLE, "1" if fts_ok else "0"),
            )
            if prev_fts == "0" and fts_ok:
                # Capability upgrade (interpreter gained FTS5): the fresh FTS
                # tables are empty while the registry may be populated — the
                # id-set reconcile could not see that. Clear the registry so
                # the next reconciliation rebuilds BOTH from Lance.
                conn.execute("DELETE FROM chunk_registry")
            if fts_ok:
                for fts_name in FTS_TABLES.values():
                    conn.execute(
                        f"CREATE VIRTUAL TABLE IF NOT EXISTS {fts_name} USING fts5("
                        f"chunk_id UNINDEXED, path UNINDEXED, kind UNINDEXED, "
                        f"language UNINDEXED, tags UNINDEXED, "
                        f"start_line UNINDEXED, end_line UNINDEXED, text, "
                        f"tokenize = \"{FTS_TOKENIZER}\")"
                    )
            # --- Secret-scan cache resident schema (1rsha, Tier 1) ---
            # Per-file content+rules fingerprint cache: a file is skipped only
            # when BOTH match. finding_refs holds derived references into
            # docs/scan-findings.json (the findings record stays authoritative).
            conn.execute(
                "CREATE TABLE IF NOT EXISTS secret_scan_cache ("
                "path TEXT PRIMARY KEY, "
                "content_hash TEXT NOT NULL, "
                "rules_fingerprint TEXT NOT NULL, "
                "scanned_at INTEGER NOT NULL, "
                "clean INTEGER NOT NULL DEFAULT 1, "
                "finding_refs TEXT NOT NULL DEFAULT '[]')"
            )
            # Tier-2-ready decomposed rule catalog (1rsha Req 4): rule_id →
            # rule_hash per aggregate fingerprint, derived by parse/hash only
            # (no per-rule execution). Tier 1 skip decisions use ONLY the
            # aggregate rules_fingerprint; the catalog exists so a future
            # Tier 2 can compute added/removed/modified rule deltas without a
            # schema migration.
            conn.execute(
                "CREATE TABLE IF NOT EXISTS secret_rule_catalog ("
                "rules_fingerprint TEXT NOT NULL, "
                "rule_id TEXT NOT NULL, "
                "rule_hash TEXT NOT NULL, "
                "PRIMARY KEY (rules_fingerprint, rule_id))"
            )
            # --- Per-layer last-embedded hash state (1sek8) ---
            # The change-detection source of truth for each SEMANTIC layer
            # ("docs"/"code"): the walk hash a layer last successfully
            # embedded per path. Content-scoped builds previously shared one
            # broad walk-state hash (the historical meta.json file_meta), so a docs-only build stamped
            # a changed code file's fresh hash without embedding it and the
            # next code build skipped it forever. Comparing each layer
            # against ITS OWN state makes any build scope correct by
            # construction. An empty table (fresh store, post-bump reset, or
            # pre-1sek8 upgrade) reads as "everything stale for this layer" —
            # one rechunk pass with chunk-hash vector reuse converges it,
            # which is also the fleet-wide heal for previously poisoned
            # repos. Derived-only: rebuildable from the repo + a build pass.
            conn.execute(
                "CREATE TABLE IF NOT EXISTS layer_path_state ("
                "layer TEXT NOT NULL, "
                "path TEXT NOT NULL, "
                "hash TEXT NOT NULL, "
                "PRIMARY KEY (layer, path))"
            )
            # --- Build-state epoch (1sed6) ---
            # THE semantic-index readiness authority: a single typed row.
            # Fresh/reset store starts `uninitialized` (readers fail closed);
            # `begin_build_epoch` durably marks `building` BEFORE the first
            # Lance/FTS mutation (FULL-synchronous fence — a crash can never
            # leave partially mutated Lance data behind an apparently valid
            # completed generation); only `finalize_build_epoch`'s attempt-ID
            # compare-and-set advances `generation` and restores `complete`.
            # A `building` row whose owning build lock is gone reads as
            # interrupted/dirty — derived at read time, never stored as a
            # separate authority.
            conn.execute(
                "CREATE TABLE IF NOT EXISTS build_state ("
                "id INTEGER PRIMARY KEY CHECK (id = 1), "
                "attempt_id TEXT NOT NULL DEFAULT '', "
                "scope TEXT NOT NULL DEFAULT '', "
                "status TEXT NOT NULL DEFAULT 'uninitialized' "
                "CHECK (status IN ('uninitialized', 'building', 'complete')), "
                "generation INTEGER NOT NULL DEFAULT 0, "
                "started_at REAL, "
                "completed_at REAL)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO build_state (id) VALUES (1)"
            )
            if self._get_meta(conn, "store_schema_version") is None:
                conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    ("store_schema_version", STATE_STORE_SCHEMA_VERSION),
                )
                # Fresh store (creation or post-reset): the chunk index is
                # cold — the next reconcile's rebuild-from-Lance is expected
                # provisioning, not a crash repair. The flag survives partial
                # in-build deltas (which make the registry non-empty before
                # the reconcile runs) and is cleared by the reconcile itself.
                conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    (META_CHUNK_INDEX_COLD, "1"),
                )

    @staticmethod
    def _get_meta(conn: "sqlite3.Connection", key: str) -> Optional[str]:
        try:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        except sqlite3.Error:
            return None
        return None if row is None else str(row[0])

    # -- version gate (whole-store invalidation, graph-store semantics) --

    def meta_all(self) -> dict[str, str]:
        try:
            rows = self._conn.execute("SELECT key, value FROM meta").fetchall()
        except sqlite3.Error:
            return {}
        return {str(k): str(v) for k, v in rows}

    def _expected_versions(self) -> dict[str, str]:
        return {"store_schema_version": STATE_STORE_SCHEMA_VERSION}

    def versions_current(self) -> bool:
        meta = self.meta_all()
        expected = self._expected_versions()
        return all(meta.get(key) == expected[key] for key in _VERSION_KEYS)

    def ensure_current(self) -> bool:
        """Reset the whole store when the schema version mismatches.

        Returns True when the store was already current. A mismatch (older or
        unknown version) drops every resident table's rows — derived-only, so
        the next build repopulates — with a loud diagnostic.
        """
        if self.versions_current():
            return True
        print(
            f"index-state-store: schema version mismatch at {self.path} "
            f"(found {self.meta_all().get('store_schema_version')!r}, expected "
            f"{STATE_STORE_SCHEMA_VERSION!r}) — resetting store (derived-only)",
            file=sys.stderr,
            flush=True,
        )
        self.reset()
        return False

    def reset(self) -> None:
        """Drop every resident table and recreate the current schema.

        Drop-and-recreate (rather than per-table DELETEs) so a version bump
        that changes table SHAPES converges to the new schema; virtual (FTS)
        tables drop first so their shadow tables go with them.

        1sed6 note: since the build epoch is a resident, a reset ERASES any
        in-flight fence — a build whose store is reset underneath it fails
        its finalization CAS (fail-closed, heals on the next run). Every
        reset is therefore persisted to the store log with a traceback-tail
        so a field CAS-miss is diagnosable after the fact.
        """
        import traceback
        _caller = "".join(traceback.format_stack(limit=6)[:-1]).strip().splitlines()
        _caller_tail = " <- ".join(
            ln.strip().split(",")[1].strip() for ln in _caller if ln.strip().startswith("File")
        )[-300:]
        store_log(
            self.index_dir,
            f"store RESET (drop-and-recreate all residents; any in-flight build fence is erased) [{_caller_tail}]",
        )
        with self._conn:
            rows = self._conn.execute(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            virtual = [n for n, s in rows if s and "VIRTUAL" in str(s).upper()]
            for name in virtual:
                self._conn.execute(f"DROP TABLE IF EXISTS {name}")
            remaining = self._conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            for (name,) in remaining:
                self._conn.execute(f"DROP TABLE IF EXISTS {name}")
        self._create_tables(self._conn)

    # -- meta helpers --

    def get_meta(self, key: str) -> Optional[str]:
        return self._get_meta(self._conn, key)

    def set_meta(self, updates: dict[str, str]) -> None:
        with self._conn:
            for key, value in updates.items():
                self._conn.execute(
                    "INSERT INTO meta (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )

    # -- freshness/attribution write path (single transaction per build pass) --

    def apply_freshness(
        self,
        *,
        rows: dict[str, dict[str, Any]],
        commits: Iterable[tuple[str, str, int]] = (),
        fingerprint: str = "",
        paths_hash: str = "",
    ) -> None:
        """Replace the freshness tables' content in one transaction.

        ``rows`` maps rel-path → ``{last_modified, churn_score, commit_count,
        source}``. ``commits`` is the (path, sha, ts) set within the trailing
        window. The whole pass is one transaction (1rq4h Req 4): everything
        commits atomically or not at all.
        """
        now = int(time.time())
        with self._conn:
            self._conn.execute("DELETE FROM file_freshness")
            self._conn.execute("DELETE FROM file_commits")
            self._conn.executemany(
                "INSERT INTO file_freshness "
                "(path, last_modified, churn_score, commit_count, source, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        path,
                        entry.get("last_modified"),
                        float(entry.get("churn_score") or 0.0),
                        int(entry.get("commit_count") or 0),
                        str(entry.get("source") or "git"),
                        now,
                    )
                    for path, entry in rows.items()
                ],
            )
            self._conn.executemany(
                "INSERT OR IGNORE INTO file_commits (path, commit_sha, commit_ts) "
                "VALUES (?, ?, ?)",
                [(p, sha, int(ts)) for p, sha, ts in commits],
            )
            self._conn.executemany(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [
                    (META_FRESHNESS_FINGERPRINT, fingerprint),
                    (META_FRESHNESS_PATHS_HASH, paths_hash),
                    (META_FRESHNESS_UPDATED_AT, str(now)),
                ],
            )

    def replace_wave_attribution(
        self,
        *,
        landings: Iterable[tuple[str, str, Optional[int]]],
        change_files: Iterable[tuple[str, str]],
    ) -> None:
        """Replace wave→landing-commit and wave→change-set rows (one transaction)."""
        with self._conn:
            self._conn.execute("DELETE FROM wave_landing")
            self._conn.execute("DELETE FROM wave_change_files")
            self._conn.executemany(
                "INSERT OR IGNORE INTO wave_landing (wave_id, commit_sha, landed_at) "
                "VALUES (?, ?, ?)",
                [(w, sha, ts) for w, sha, ts in landings],
            )
            self._conn.executemany(
                "INSERT OR IGNORE INTO wave_change_files (wave_id, path) VALUES (?, ?)",
                [(w, p) for w, p in change_files],
            )

    def upsert_doc_drift(self, entries: dict[str, dict[str, Any]]) -> None:
        """Upsert per-doc drift summaries (one transaction)."""
        now = int(time.time())
        with self._conn:
            self._conn.executemany(
                "INSERT INTO doc_drift "
                "(path, drifted, drift_refs, commits_since, anchor_kind, historical, "
                "waves_behind, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(path) DO UPDATE SET drifted=excluded.drifted, "
                "drift_refs=excluded.drift_refs, commits_since=excluded.commits_since, "
                "anchor_kind=excluded.anchor_kind, historical=excluded.historical, "
                "waves_behind=excluded.waves_behind, updated_at=excluded.updated_at",
                [
                    (
                        path,
                        1 if entry.get("drifted") else 0,
                        json.dumps(list(entry.get("drift_refs") or []), separators=(",", ":")),
                        int(entry.get("commits_since") or 0),
                        str(entry.get("anchor_kind") or "content"),
                        1 if entry.get("historical") else 0,
                        int(entry.get("waves_behind") or 0),
                        now,
                    )
                    for path, entry in entries.items()
                ],
            )

    def replace_doc_drift(
        self, entries: dict[str, dict[str, Any]], *, fingerprint: str = ""
    ) -> None:
        """Replace ALL per-doc drift rows in one transaction (1ro43).

        Full replace mirrors ``apply_freshness``: rows for deleted or
        no-longer-indexed docs must not linger, and the build-tail pass always
        computes the complete current doc set. ``upsert_doc_drift`` remains for
        targeted single-doc refreshes.
        """
        now = int(time.time())
        with self._conn:
            self._conn.execute("DELETE FROM doc_drift")
            self._conn.executemany(
                "INSERT INTO doc_drift "
                "(path, drifted, drift_refs, commits_since, anchor_kind, historical, "
                "waves_behind, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        path,
                        1 if entry.get("drifted") else 0,
                        json.dumps(list(entry.get("drift_refs") or []), separators=(",", ":")),
                        int(entry.get("commits_since") or 0),
                        str(entry.get("anchor_kind") or "content"),
                        1 if entry.get("historical") else 0,
                        int(entry.get("waves_behind") or 0),
                        now,
                    )
                    for path, entry in entries.items()
                ],
            )
            self._conn.executemany(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [
                    (META_DRIFT_FINGERPRINT, fingerprint),
                    (META_DRIFT_UPDATED_AT, str(now)),
                ],
            )

    def replace_attribution_and_drift(
        self,
        *,
        landings: Iterable[tuple[str, str, Optional[int]]],
        change_files: Iterable[tuple[str, str]],
        entries: dict[str, dict[str, Any]],
        fingerprint: str = "",
    ) -> None:
        """Replace wave attribution + all drift rows + the fingerprint in ONE
        transaction (delivery-review torn-write finding: the two replaces were
        separate transactions, so a crash between them left attribution
        advanced while drift/fingerprint stayed stale). All-or-nothing: either
        the whole drift/attribution state advances together or none of it does.
        """
        now = int(time.time())
        with self._conn:
            self._conn.execute("DELETE FROM wave_landing")
            self._conn.execute("DELETE FROM wave_change_files")
            self._conn.executemany(
                "INSERT OR IGNORE INTO wave_landing (wave_id, commit_sha, landed_at) "
                "VALUES (?, ?, ?)",
                [(w, sha, ts) for w, sha, ts in landings],
            )
            self._conn.executemany(
                "INSERT OR IGNORE INTO wave_change_files (wave_id, path) VALUES (?, ?)",
                [(w, p) for w, p in change_files],
            )
            self._conn.execute("DELETE FROM doc_drift")
            self._conn.executemany(
                "INSERT INTO doc_drift "
                "(path, drifted, drift_refs, commits_since, anchor_kind, historical, "
                "waves_behind, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        path,
                        1 if entry.get("drifted") else 0,
                        json.dumps(list(entry.get("drift_refs") or []), separators=(",", ":")),
                        int(entry.get("commits_since") or 0),
                        str(entry.get("anchor_kind") or "content"),
                        1 if entry.get("historical") else 0,
                        int(entry.get("waves_behind") or 0),
                        now,
                    )
                    for path, entry in entries.items()
                ],
            )
            self._conn.executemany(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [
                    (META_DRIFT_FINGERPRINT, fingerprint),
                    (META_DRIFT_UPDATED_AT, str(now)),
                ],
            )

    def clear_attribution_and_drift(self) -> int:
        """Remove ALL git-derived wave attribution + doc drift rows + the drift
        fingerprint in ONE transaction. Used when a build runs in a root with
        NO git authority (delivery-review finding: a git-built index copied into
        — or a repo that dropped git under — a now-non-git root must not keep
        serving stale git-derived drift/attribution). Idempotent: returns the
        total number of rows/fingerprints removed (0 when already clean, so the
        caller can skip re-clearing every non-git build)."""
        with self._conn:
            n_land = self._conn.execute("SELECT COUNT(*) FROM wave_landing").fetchone()[0]
            n_files = self._conn.execute("SELECT COUNT(*) FROM wave_change_files").fetchone()[0]
            n_drift = self._conn.execute("SELECT COUNT(*) FROM doc_drift").fetchone()[0]
            n_fp = self._conn.execute(
                "SELECT COUNT(*) FROM meta WHERE key IN (?, ?)",
                (META_DRIFT_FINGERPRINT, META_DRIFT_UPDATED_AT),
            ).fetchone()[0]
            total = int(n_land) + int(n_files) + int(n_drift) + int(n_fp)
            if total:
                self._conn.execute("DELETE FROM wave_landing")
                self._conn.execute("DELETE FROM wave_change_files")
                self._conn.execute("DELETE FROM doc_drift")
                self._conn.execute(
                    "DELETE FROM meta WHERE key IN (?, ?)",
                    (META_DRIFT_FINGERPRINT, META_DRIFT_UPDATED_AT),
                )
            return total

    # -- maintenance (1rq4h Req 9) --

    def end_of_build_maintenance(self) -> None:
        """Bounded end-of-build maintenance: WAL truncate + incremental vacuum.

        Runs while the build still holds the index-build lock (writers done).
        Keeps the ``-wal`` bounded under the long-lived MCP server, whose
        query-path reads could otherwise starve autocheckpoint.
        """
        try:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self._conn.execute("PRAGMA incremental_vacuum")
        except sqlite3.Error as exc:
            print(
                f"index-state-store: end-of-build maintenance skipped ({exc})",
                file=sys.stderr,
            )

    def close(self) -> None:
        try:
            if not self.read_only:
                self._conn.execute("PRAGMA optimize")
        except sqlite3.Error:
            pass
        try:
            self._conn.close()
        except sqlite3.Error:
            pass

    def __del__(self):  # pragma: no cover - GC timing dependent
        try:
            self._conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Read-only query-path access (MCP server)
# ---------------------------------------------------------------------------


def open_read_only(index_dir: Path) -> Optional["sqlite3.Connection"]:
    """Read-only URI open with busy_timeout; None when absent or unreadable.

    Server-side reads must open/close per operation (1rq4h Req 9): a pinned
    long-lived reader would starve WAL autocheckpoint between builds.
    """
    path = state_store_path(index_dir)
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10.0)
        conn.execute("PRAGMA busy_timeout=10000")
        return conn
    except sqlite3.Error:
        return None


def freshness_for_path(
    index_dir: Path, path: str, since_ts: Optional[int] = None
) -> Optional[dict[str, Any]]:
    """Per-path freshness read primitive — the 1ro43 Req 6 / 1p8gy seam.

    Returns ``{age_days, churn_score, commits_since}`` or None when the store
    or the row is absent (callers degrade silently — absence is a normal
    not-yet-built state, 1rq4h AC-2/AC-6).

    ``commits_since``: with ``since_ts``, the number of commits touching the
    path after that timestamp (within the trailing churn window the store
    carries); without it, the raw commit count over the whole window.
    """
    conn = open_read_only(index_dir)
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT last_modified, churn_score, commit_count FROM file_freshness "
            "WHERE path = ?",
            (path,),
        ).fetchone()
        if row is None:
            return None
        last_modified, churn_score, commit_count = row
        age_days: Optional[float] = None
        if last_modified is not None:
            age_days = max(0.0, (time.time() - float(last_modified)) / 86400.0)
        if since_ts is not None:
            commits_since = int(
                conn.execute(
                    "SELECT COUNT(*) FROM file_commits WHERE path = ? AND commit_ts > ?",
                    (path, int(since_ts)),
                ).fetchone()[0]
            )
        else:
            commits_since = int(commit_count or 0)
        return {
            "age_days": None if age_days is None else round(age_days, 2),
            "churn_score": float(churn_score or 0.0),
            "commits_since": commits_since,
        }
    except sqlite3.Error:
        return None
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def wave_attribution_for_path(index_dir: Path, path: str) -> list[dict[str, Any]]:
    """Waves whose change set contains ``path``, with their landing commits."""
    conn = open_read_only(index_dir)
    if conn is None:
        return []
    try:
        rows = conn.execute(
            "SELECT wcf.wave_id, wl.commit_sha, wl.landed_at "
            "FROM wave_change_files wcf "
            "LEFT JOIN wave_landing wl ON wl.wave_id = wcf.wave_id "
            "WHERE wcf.path = ? ORDER BY wcf.wave_id",
            (path,),
        ).fetchall()
        return [
            {"wave_id": str(w), "commit_sha": None if sha is None else str(sha),
             "landed_at": None if ts is None else int(ts)}
            for w, sha, ts in rows
        ]
    except sqlite3.Error:
        return []
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def doc_drift_for_path(index_dir: Path, path: str) -> Optional[dict[str, Any]]:
    """Per-doc drift summary row, decoded; None when absent."""
    conn = open_read_only(index_dir)
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT drifted, drift_refs, commits_since, anchor_kind, historical, "
            "waves_behind FROM doc_drift WHERE path = ?",
            (path,),
        ).fetchone()
        if row is None:
            return None
        drifted, drift_refs, commits_since, anchor_kind, historical, waves_behind = row
        try:
            refs = json.loads(drift_refs or "[]")
        except Exception:
            refs = []
        return {
            "drifted": bool(drifted),
            "drift_refs": refs if isinstance(refs, list) else [],
            "commits_since": int(commits_since or 0),
            "anchor_kind": str(anchor_kind or "content"),
            "historical": bool(historical),
            "waves_behind": int(waves_behind or 0),
        }
    except sqlite3.Error:
        return None
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def freshness_for_paths(
    index_dir: Path, paths: Iterable[str]
) -> dict[str, dict[str, Any]]:
    """Batched per-path freshness + drift read for retrieval annotation (1ro43).

    One read-only connection, two queries, for a whole response's citation
    set — the retrieval path must never call ``freshness_for_path`` per
    citation. Returns rel-path → merged ``freshness`` annotation dict
    (``age_days``/``churn_score`` from ``file_freshness``; ``drifted``/
    ``commits_since_verified``/``historical``/``waves_behind`` from
    ``doc_drift`` when a row exists). Paths without rows are simply absent —
    callers omit the annotation (silent degrade on metadata-free stores).
    """
    wanted = sorted({str(p) for p in paths if p})
    if not wanted:
        return {}
    conn = open_read_only(index_dir)
    if conn is None:
        return {}
    try:
        out: dict[str, dict[str, Any]] = {}
        now = time.time()
        marks = ",".join("?" for _ in wanted)
        for path, last_modified, churn_score in conn.execute(
            f"SELECT path, last_modified, churn_score FROM file_freshness "
            f"WHERE path IN ({marks})",
            wanted,
        ):
            entry: dict[str, Any] = {"churn_score": float(churn_score or 0.0)}
            if last_modified is not None:
                entry["age_days"] = round(
                    max(0.0, (now - float(last_modified)) / 86400.0), 2
                )
            out[str(path)] = entry
        for path, drifted, commits_since, historical, waves_behind in conn.execute(
            f"SELECT path, drifted, commits_since, historical, waves_behind "
            f"FROM doc_drift WHERE path IN ({marks})",
            wanted,
        ):
            entry = out.setdefault(str(path), {})
            if historical:
                entry["historical"] = True
                entry["waves_behind"] = int(waves_behind or 0)
            else:
                entry["drifted"] = bool(drifted)
                entry["commits_since_verified"] = int(commits_since or 0)
        return out
    except sqlite3.Error:
        return {}
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


# ---------------------------------------------------------------------------
# Agent-memory invalidation seqlock (dedicated store; delivery-review round 4)
# ---------------------------------------------------------------------------
#
# The advisory cache's cross-process coherence cannot rest on in-process
# eviction: if the durable write that other processes read fails, a second MCP
# process keeps serving a stale advisory. So invalidation is a DURABLE SEQLOCK
# in a dedicated store (never the canonical index-state.sqlite, so a memory
# write can't reset freshness/FTS/epoch):
#   - ``epoch``      — a random nonce minted ONCE at store creation. Defeats the
#                      delete/recreate ABA: a rebuilt store gets a new epoch, so
#                      a key from the old store can never alias the new one.
#   - ``generation`` — monotonic counter; advances on every mutation/invalidate.
#   - ``memory_writers`` — one WRITER-OWNED token row per in-flight mutation
#                      (round-4 re-review: a single shared ``dirty`` flag let one
#                      writer's finalize clear a concurrent writer's fence — A
#                      fence, B fence, A finalize → cleared while B still
#                      mutating). Each fence INSERTs a unique token BEFORE the
#                      filesystem write; each finalize DELETEs ONLY its own token
#                      (so B's fence survives A's finalize) and advances the
#                      generation. Readers BYPASS the cache while any *live*
#                      token exists. A crashed writer's token is bounded by a TTL
#                      (``_MEMORY_WRITER_TTL_SECONDS``): readers stop bypassing on
#                      tokens older than the TTL (self-heal), and the rw paths
#                      lazily reap them. A mutation that cannot register a token
#                      is REFUSED. ``read_memory_state`` still returns a synthetic
#                      ``dirty`` (1 iff a live token exists) so the reader key
#                      contract is unchanged.
MEMORY_STATE_FILENAME = "memory-state.sqlite"

# A record filesystem write completes in milliseconds; a fence held past this is
# presumed crashed, so readers stop bypassing on it (bounded fail-closed) and it
# is lazily reaped. Generous margin over any real add/reconcile latency.
_MEMORY_WRITER_TTL_SECONDS = 300


def _memory_state_path(index_dir: Path) -> Path:
    return index_dir / MEMORY_STATE_FILENAME


def _memory_state_rw(index_dir: Path) -> "sqlite3.Connection":
    path = _memory_state_path(index_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS memory_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS memory_writers "
        "(token TEXT PRIMARY KEY, started_at INTEGER NOT NULL)"
    )
    return conn


def _reap_stale_writers(conn: "sqlite3.Connection", now: int) -> None:
    """Drop writer tokens older than the TTL (crashed/abandoned mutations)."""
    conn.execute(
        "DELETE FROM memory_writers WHERE started_at < ?",
        (now - _MEMORY_WRITER_TTL_SECONDS,),
    )


def read_memory_state(index_dir: Path) -> Optional[dict[str, Any]]:
    """``{epoch, generation, dirty}`` or None when the durable store is
    UNREADABLE (the reader then BYPASSES the cache — never trusts a bogus
    clean/zero). An absent store is the valid never-initialized state
    (empty epoch, generation 0, not dirty). ``dirty`` is synthesized: 1 iff a
    LIVE writer token exists (a mutation is in flight); tokens older than the
    TTL are ignored (self-heal for a crashed writer)."""
    path = _memory_state_path(index_dir)
    if not path.exists():
        return {"epoch": "", "generation": 0, "dirty": 0}
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10.0)
        try:
            rows = dict(conn.execute("SELECT key, value FROM memory_meta").fetchall())
            live = 0
            try:
                # Read-only: cannot reap, but a stale token is simply not counted
                # as live (bounded by the TTL). Table may be absent on an old store.
                cutoff = int(time.time()) - _MEMORY_WRITER_TTL_SECONDS
                live = conn.execute(
                    "SELECT COUNT(*) FROM memory_writers WHERE started_at >= ?", (cutoff,)
                ).fetchone()[0]
            except sqlite3.Error:
                live = 0
        finally:
            conn.close()
        return {
            "epoch": str(rows.get("epoch", "")),
            "generation": int(rows.get("generation", "0")),
            "dirty": 1 if live else 0,
        }
    except (sqlite3.Error, ValueError, OSError):
        return None


def memory_fence(index_dir: Path) -> Optional[str]:
    """Register a WRITER-OWNED token (minting epoch/generation if absent) BEFORE
    a record filesystem mutation. Returns the token string on success; None
    means the fence could not be established and the caller MUST refuse the
    mutation. Each writer owns its token; ``memory_finalize`` removes ONLY that
    token, so a concurrent writer cannot clear another's fence."""
    try:
        conn = _memory_state_rw(index_dir)
        try:
            token = secrets.token_hex(16)
            now = int(time.time())
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT OR IGNORE INTO memory_meta (key, value) VALUES ('epoch', ?)",
                (secrets.token_hex(16),),
            )
            conn.execute("INSERT OR IGNORE INTO memory_meta (key, value) VALUES ('generation', '0')")
            _reap_stale_writers(conn, now)
            conn.execute(
                "INSERT INTO memory_writers (token, started_at) VALUES (?, ?)", (token, now)
            )
            conn.execute("COMMIT")
            return token
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return None


def memory_finalize(index_dir: Path, token: Optional[str] = None) -> Optional[int]:
    """Remove THIS writer's token and advance ``generation`` after a mutation
    completes. Deleting only ``token`` means a concurrent in-flight writer's
    fence survives (no cross-writer clear). Best-effort: on failure the token
    remains and readers keep bypassing (safe) until the next successful mutation
    or the TTL self-heals it."""
    try:
        conn = _memory_state_rw(index_dir)
        try:
            conn.execute("BEGIN IMMEDIATE")
            if token:
                conn.execute("DELETE FROM memory_writers WHERE token = ?", (token,))
            _reap_stale_writers(conn, int(time.time()))
            conn.execute(
                "INSERT INTO memory_meta (key, value) VALUES ('generation', '1') "
                "ON CONFLICT(key) DO UPDATE SET value = CAST(value AS INTEGER) + 1"
            )
            row = conn.execute("SELECT value FROM memory_meta WHERE key = 'generation'").fetchone()
            conn.execute("COMMIT")
            return int(row[0]) if row else None
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return None


def memory_advance(index_dir: Path) -> Optional[int]:
    """Advance ``generation`` WITHOUT registering a writer token — the indexer's
    invalidation signal when a memory record changed on disk (a raw/hook edit).
    A generation bump alone invalidates every reader's cache key."""
    try:
        conn = _memory_state_rw(index_dir)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT OR IGNORE INTO memory_meta (key, value) VALUES ('epoch', ?)",
                (secrets.token_hex(16),),
            )
            _reap_stale_writers(conn, int(time.time()))
            conn.execute(
                "INSERT INTO memory_meta (key, value) VALUES ('generation', '1') "
                "ON CONFLICT(key) DO UPDATE SET value = CAST(value AS INTEGER) + 1"
            )
            row = conn.execute("SELECT value FROM memory_meta WHERE key = 'generation'").fetchone()
            conn.execute("COMMIT")
            return int(row[0]) if row else None
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return None


def memory_invalidate(index_dir: Path) -> bool:
    """Indexer-side invalidation for a raw/hook memory-record edit. Returns True
    ONLY when the generation DURABLY advanced — the sole durable invalidation for
    a raw content edit, which does not move ``dir_mtime`` so an un-advanced
    generation would leave the reader key identical and serve the pre-edit
    advisory.

    On failure it registers a best-effort short-lived fence token (so readers
    bypass during the failure WINDOW, TTL-bounded) and returns False. The caller
    (indexer) MUST then fail the build BEFORE recording file metadata, so the
    edited record's old file_meta is preserved and the recovered retry
    re-detects the edit and advances the generation — otherwise a "clean" build
    would record the new hash and the retry would see no change, permanently
    stranding the stale advisory."""
    if memory_advance(index_dir) is not None:
        return True
    memory_fence(index_dir)  # best-effort temporary bypass; not durable on its own
    return False


def file_commit_times(index_dir: Path, paths: Iterable[str]) -> dict[str, list[int]]:
    """Batched per-path windowed commit timestamps — ONE read-only query.

    For the memory-decay hot path (delivery-review perf finding): a whole
    advisory batch's churn is computed in Python from one store read instead
    of a per-target store open. Returns ``{path: [commit_ts, ...]}`` (only
    paths with rows appear). Empty on absent/unreadable store.
    """
    wanted = sorted({str(p) for p in paths if p})
    if not wanted:
        return {}
    conn = open_read_only(index_dir)
    if conn is None:
        return {}
    try:
        marks = ",".join("?" for _ in wanted)
        out: dict[str, list[int]] = {}
        for path, ts in conn.execute(
            f"SELECT path, commit_ts FROM file_commits WHERE path IN ({marks})",
            wanted,
        ):
            out.setdefault(str(path), []).append(int(ts))
        return out
    except sqlite3.Error:
        return {}
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def drift_worklist(index_dir: Path, *, limit: int = 20) -> dict[str, Any]:
    """Drift worklist read (1ro43 Req 7/11): flagged living docs, worst first.

    Historical (``docs/waves/``) rows are excluded by construction — they are
    never verified, amended, or disposed. Ordering is the documented consumer
    contract: ``commits_since`` descending, then path for determinism.
    """
    conn = open_read_only(index_dir)
    if conn is None:
        return {"available": False, "flagged_count": 0, "entries": []}
    try:
        # Exempt prefixes are filtered at read time too, so a store written
        # by an older pass heals immediately (no fingerprint-change wait).
        exempt_sql = " AND ".join(
            "path NOT LIKE ?" for _ in DRIFT_EXEMPT_PREFIXES
        )
        exempt_args = [f"{p}%" for p in DRIFT_EXEMPT_PREFIXES]
        flagged = int(
            conn.execute(
                "SELECT COUNT(*) FROM doc_drift WHERE drifted = 1 AND historical = 0 "
                f"AND {exempt_sql}",
                exempt_args,
            ).fetchone()[0]
        )
        rows = conn.execute(
            "SELECT path, drift_refs, commits_since, anchor_kind FROM doc_drift "
            "WHERE drifted = 1 AND historical = 0 "
            f"AND {exempt_sql} "
            "ORDER BY commits_since DESC, path ASC LIMIT ?",
            exempt_args + [int(limit)],
        ).fetchall()
        entries = []
        for path, drift_refs, commits_since, anchor_kind in rows:
            try:
                refs = json.loads(drift_refs or "[]")
            except Exception:
                refs = []
            entries.append(
                {
                    "path": str(path),
                    "commits_since": int(commits_since or 0),
                    "anchor_kind": str(anchor_kind or "content"),
                    "drift_refs": refs if isinstance(refs, list) else [],
                }
            )
        return {"available": True, "flagged_count": flagged, "entries": entries}
    except sqlite3.Error:
        return {"available": False, "flagged_count": 0, "entries": []}
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


# ---------------------------------------------------------------------------
# Chunk index: FTS5 lexical tables + chunk registry (1rrr0)
# ---------------------------------------------------------------------------
#
# Ordered-consistency model (readiness-council amendment): Lance is
# authoritative for chunk existence; these derived tables commit in a single
# SQLite transaction ORDERED AFTER the corresponding Lance writes; the
# reconciliation pass (chunk-id set comparison → derived-only rebuild on
# mismatch, loud diagnostic) repairs any crash window between the engines.
# Cross-engine atomicity is explicitly not claimed.

# Max whitespace tokens taken from a user query when building the FTS MATCH
# expression — bounds pathological inputs without changing normal queries.
FTS_QUERY_MAX_TOKENS = 12


def _row_lines(row: dict[str, Any]) -> tuple[int, int]:
    lines = row.get("lines")
    if isinstance(lines, (list, tuple)) and len(lines) == 2:
        try:
            return int(lines[0]), int(lines[1])
        except (TypeError, ValueError):
            pass
    return 0, 0


def _row_tags(row: dict[str, Any]) -> str:
    """Normalize the tags field to the space-joined string Lance rows carry."""
    tags = row.get("tags")
    if isinstance(tags, (list, tuple)):
        return " ".join(str(t) for t in tags)
    return str(tags or "")


def _fts_enabled(store: "IndexStateStore") -> bool:
    return store.get_meta(META_FTS_AVAILABLE) == "1"


def _apply_chunk_deltas_locked(
    store: "IndexStateStore",
    table_name: str,
    *,
    delete_ids: Iterable[str] = (),
    delete_paths: Iterable[str] = (),
    add_rows: Iterable[dict[str, Any]] = (),
) -> None:
    fts_name = FTS_TABLES.get(table_name)
    fts_on = fts_name is not None and _fts_enabled(store)
    delete_ids = [str(i) for i in delete_ids]
    delete_paths = [str(p) for p in delete_paths]
    rows = list(add_rows)
    conn = store._conn
    churn = len(delete_ids) + len(delete_paths) + len(rows)
    with conn:
        if delete_ids:
            conn.executemany(
                "DELETE FROM chunk_registry WHERE table_name = ? AND chunk_id = ?",
                [(table_name, i) for i in delete_ids],
            )
            if fts_on:
                conn.executemany(
                    f"DELETE FROM {fts_name} WHERE chunk_id = ?",
                    [(i,) for i in delete_ids],
                )
        if delete_paths:
            conn.executemany(
                "DELETE FROM chunk_registry WHERE table_name = ? AND path = ?",
                [(table_name, p) for p in delete_paths],
            )
            if fts_on:
                conn.executemany(
                    f"DELETE FROM {fts_name} WHERE path = ?",
                    [(p,) for p in delete_paths],
                )
        if rows:
            # Replace-by-id: an add for an existing id supersedes it.
            conn.executemany(
                "INSERT INTO chunk_registry (table_name, chunk_id, path, chunk_hash) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(table_name, chunk_id) DO UPDATE SET "
                "path=excluded.path, chunk_hash=excluded.chunk_hash",
                [
                    (table_name, str(r.get("id") or ""), str(r.get("path") or ""),
                     str(r.get("chunk_hash") or ""))
                    for r in rows
                ],
            )
            if fts_on:
                conn.executemany(
                    f"DELETE FROM {fts_name} WHERE chunk_id = ?",
                    [(str(r.get("id") or ""),) for r in rows],
                )
                conn.executemany(
                    f"INSERT INTO {fts_name} "
                    f"(chunk_id, path, kind, language, tags, start_line, end_line, text) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        (str(r.get("id") or ""), str(r.get("path") or ""),
                         str(r.get("kind") or ""), str(r.get("language") or ""),
                         _row_tags(r), *_row_lines(r),
                         str(r.get("text") or ""))
                        for r in rows
                    ],
                )
        # Threshold-gated in-build segment merge (1rrr0 Req 12) — the FTS
        # analog of the fragment-gated Lance compact.
        if fts_on and churn:
            key = f"{META_FTS_CHURN_PREFIX}{table_name}"
            try:
                current = int(store.get_meta(key) or 0)
            except ValueError:
                current = 0
            current += churn
            if current > FTS_MERGE_CHURN_THRESHOLD:
                conn.execute(
                    f"INSERT INTO {fts_name}({fts_name}, rank) VALUES('merge', ?)",
                    (FTS_MERGE_PAGES,),
                )
                current = 0
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(current)),
            )


def apply_chunk_deltas(
    index_dir: Path,
    table_name: str,
    *,
    delete_ids: Iterable[str] = (),
    delete_paths: Iterable[str] = (),
    add_rows: Iterable[dict[str, Any]] = (),
) -> None:
    """Apply one build pass's chunk deltas to the registry + FTS tables.

    One transaction, opened per call (build futures for docs/code run
    concurrently in threads — each call owns its own connection; WAL +
    busy_timeout serialize the writers). Ordered AFTER the Lance writes by
    the caller. Never raises to the caller's build loop — the reconciliation
    pass self-heals any missed sync.
    """
    store = IndexStateStore(index_dir)
    try:
        store.ensure_current()
        _apply_chunk_deltas_locked(
            store, table_name,
            delete_ids=delete_ids, delete_paths=delete_paths, add_rows=add_rows,
        )
    finally:
        store.close()


def rebuild_chunk_index(index_dir: Path, table_name: str, rows: Iterable[dict[str, Any]]) -> int:
    """Full derived-only rebuild of one table's registry + FTS rows from Lance.

    On a sqlite error mid-rebuild (e.g. a corrupt FTS shadow table) the whole
    store is reset (drop-and-recreate, loud) and the rebuild retried once —
    everything resident is derived, so recovery is free.

    Rows are deduped by chunk id (last wins): Lance's ``id`` column is not
    unique — incremental churn can leave duplicate-id rows (observed live:
    +300 on this repo) — while the registry PK and the FTS delete-by-id
    contract both assume one row per id.
    """
    deduped: dict[str, dict[str, Any]] = {}
    for r in rows:
        deduped[str(r.get("id") or "")] = r
    rows = list(deduped.values())

    def _write(store: "IndexStateStore") -> int:
        conn = store._conn
        fts_name = FTS_TABLES.get(table_name)
        fts_on = fts_name is not None and _fts_enabled(store)
        with conn:
            conn.execute("DELETE FROM chunk_registry WHERE table_name = ?", (table_name,))
            if fts_on:
                conn.execute(f"DELETE FROM {fts_name}")
            conn.executemany(
                "INSERT OR REPLACE INTO chunk_registry (table_name, chunk_id, path, chunk_hash) "
                "VALUES (?, ?, ?, ?)",
                [
                    (table_name, str(r.get("id") or ""), str(r.get("path") or ""),
                     str(r.get("chunk_hash") or ""))
                    for r in rows
                ],
            )
            if fts_on:
                conn.executemany(
                    f"INSERT INTO {fts_name} "
                    f"(chunk_id, path, kind, language, tags, start_line, end_line, text) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        (str(r.get("id") or ""), str(r.get("path") or ""),
                         str(r.get("kind") or ""), str(r.get("language") or ""),
                         _row_tags(r), *_row_lines(r),
                         str(r.get("text") or ""))
                        for r in rows
                    ],
                )
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (f"{META_FTS_CHURN_PREFIX}{table_name}", "0"),
            )
        return len(rows)

    store = IndexStateStore(index_dir)
    try:
        store.ensure_current()
        try:
            return _write(store)
        except sqlite3.Error as exc:
            print(
                f"index-state-store: chunk-index rebuild for '{table_name}' hit a store "
                f"error ({exc}) — resetting store and retrying (derived-only)",
                file=sys.stderr,
                flush=True,
            )
            store.reset()
            return _write(store)
    finally:
        store.close()


# Above this many requested paths, one full-table scan grouped in Python beats
# per-path SELECT round-trips (rechunk-all passes request every path at once).
_REGISTRY_BULK_FETCH_THRESHOLD = 50


def registry_map_for_paths(
    index_dir: Path, table_name: str, paths: Iterable[str]
) -> dict[str, dict[str, str]]:
    """Per-path ``{chunk_id: chunk_hash}`` maps from the registry (read-only)."""
    result: dict[str, dict[str, str]] = {}
    path_set = {str(p) for p in paths}
    if not path_set:
        return result
    conn = open_read_only(index_dir)
    if conn is None:
        return result
    try:
        if len(path_set) > _REGISTRY_BULK_FETCH_THRESHOLD:
            rows = conn.execute(
                "SELECT path, chunk_id, chunk_hash FROM chunk_registry "
                "WHERE table_name = ?",
                (table_name,),
            ).fetchall()
            for path, chunk_id, chunk_hash in rows:
                path_s = str(path)
                if path_s in path_set:
                    result.setdefault(path_s, {})[str(chunk_id)] = str(chunk_hash)
        else:
            for path in path_set:
                rows = conn.execute(
                    "SELECT chunk_id, chunk_hash FROM chunk_registry "
                    "WHERE table_name = ? AND path = ?",
                    (table_name, path),
                ).fetchall()
                if rows:
                    result[path] = {str(i): str(h) for i, h in rows}
    except sqlite3.Error:
        return {}
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass
    return result


def registry_chunk_ids(index_dir: Path, table_name: str) -> Optional[set[str]]:
    """All registered chunk ids for a table; None when the store is absent/unreadable."""
    conn = open_read_only(index_dir)
    if conn is None:
        return None
    try:
        rows = conn.execute(
            "SELECT chunk_id FROM chunk_registry WHERE table_name = ?", (table_name,)
        ).fetchall()
        return {str(r[0]) for r in rows}
    except sqlite3.Error:
        return None
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def layer_hashes(index_dir: Path, layer: str) -> Optional[dict[str, str]]:
    """The last-embedded walk hash per path for one semantic layer (1sek8).

    ``None`` when the store is absent/unreadable (callers treat that the same
    as an empty layer: everything in scope is stale). An EMPTY dict is the
    normal cold state — fresh store, post-bump reset, or a pre-1sek8 repo —
    and means the layer's first build re-chunks everything in scope (vectors
    reused by chunk content hash), which is also the poisoned-repo heal.
    """
    conn = open_read_only(index_dir)
    if conn is None:
        return None
    try:
        rows = conn.execute(
            "SELECT path, hash FROM layer_path_state WHERE layer = ?", (layer,)
        ).fetchall()
        return {str(p): str(h) for p, h in rows}
    except sqlite3.Error:
        return None
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def update_layer_hashes(
    index_dir: Path,
    layer: str,
    *,
    set_hashes: "dict[str, str] | None" = None,
    remove_paths: Iterable[str] = (),
) -> None:
    """Commit one build pass's layer-state deltas in a single transaction (1sek8).

    Called AFTER the layer's Lance writes succeed (same ordered-consistency
    posture as the chunk deltas): ``set_hashes`` records the walk hash each
    written path was embedded at; ``remove_paths`` drops deleted/no-longer-
    eligible paths. Never raises to the build loop — a missed update just
    means the next build re-processes those paths (idempotent, vectors
    reused).
    """
    set_hashes = set_hashes or {}
    remove_list = [str(p) for p in remove_paths]
    if not set_hashes and not remove_list:
        return
    store = IndexStateStore(index_dir)
    try:
        store.ensure_current()
        conn = store._conn
        with conn:
            if remove_list:
                conn.executemany(
                    "DELETE FROM layer_path_state WHERE layer = ? AND path = ?",
                    [(layer, p) for p in remove_list],
                )
            if set_hashes:
                conn.executemany(
                    "INSERT INTO layer_path_state (layer, path, hash) VALUES (?, ?, ?) "
                    "ON CONFLICT(layer, path) DO UPDATE SET hash=excluded.hash",
                    [(layer, str(p), str(h)) for p, h in set_hashes.items()],
                )
    finally:
        store.close()


def replace_layer_hashes(index_dir: Path, layer: str, hashes: dict[str, str]) -> None:
    """Full replacement of one layer's state (full-rebuild path, 1sek8)."""
    store = IndexStateStore(index_dir)
    try:
        store.ensure_current()
        conn = store._conn
        with conn:
            conn.execute("DELETE FROM layer_path_state WHERE layer = ?", (layer,))
            conn.executemany(
                "INSERT INTO layer_path_state (layer, path, hash) VALUES (?, ?, ?)",
                [(layer, str(p), str(h)) for p, h in hashes.items()],
            )
    finally:
        store.close()


def registry_chunk_count(index_dir: Path, table_name: str) -> Optional[int]:
    """Cheap read-only registry row count for one table (1sbfj).

    ``None`` when the store is absent/unreadable — distinct from 0 (an empty
    registry on an existing store, the field defect's signature). One
    ``count(*)`` against the PK index; used by the zero-change coverage probe
    and the health summary, so it must stay cheap.
    """
    conn = open_read_only(index_dir)
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT count(*) FROM chunk_registry WHERE table_name = ?", (table_name,)
        ).fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return None
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def chunk_index_is_cold(index_dir: Path) -> bool:
    """Read-only probe of the cold-provisioning flag (1sbfj).

    True when the store was created/reset and the first reconcile has not yet
    completed — the zero-change build path uses this to fall through to the
    reconcile instead of taking the fast exit.
    """
    conn = open_read_only(index_dir)
    if conn is None:
        return False
    try:
        return IndexStateStore._get_meta(conn, META_CHUNK_INDEX_COLD) == "1"
    except sqlite3.Error:
        return False
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def chunk_sync_counts(index_dir: Path, table_name: str) -> "tuple[Optional[int], Optional[int]]":
    """Read-only ``(raw_rows, unique_ids)`` recorded at the last successful
    reconcile for one table, or ``(None, None)`` when never recorded (1sbfj).

    The exact-comparison basis for the zero-change heal probe and the health
    coverage flag: Lance ids are not unique, so live raw-vs-registry compares
    misread duplicate-id rows as under-coverage.
    """
    conn = open_read_only(index_dir)
    if conn is None:
        return None, None
    try:
        raw = IndexStateStore._get_meta(conn, META_CHUNK_SYNC_RAW_PREFIX + table_name)
        unique = IndexStateStore._get_meta(conn, META_CHUNK_SYNC_UNIQUE_PREFIX + table_name)
        return (
            int(raw) if raw is not None else None,
            int(unique) if unique is not None else None,
        )
    except (sqlite3.Error, ValueError):
        return None, None
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def _record_chunk_sync_counts(
    index_dir: Path, table_name: str, raw_rows: Optional[int], unique_ids: int,
    *, clear_cold: bool = False,
) -> None:
    """Persist the sync-time counts (and optionally clear the cold flag) in
    one store open. Best-effort — a failure just leaves the fallback compare."""
    try:
        store = IndexStateStore(index_dir)
        try:
            values = {META_CHUNK_SYNC_UNIQUE_PREFIX + table_name: str(int(unique_ids))}
            if raw_rows is not None:
                values[META_CHUNK_SYNC_RAW_PREFIX + table_name] = str(int(raw_rows))
            if clear_cold:
                values[META_CHUNK_INDEX_COLD] = "0"
            store.set_meta(values)
        finally:
            store.close()
    except Exception:
        pass


def reconcile_chunk_index(
    index_dir: Path,
    table_name: str,
    lance_ids: set[str],
    fetch_rows,
    *,
    expected: bool = False,
    raw_rows: Optional[int] = None,
    force: bool = False,
) -> dict[str, Any]:
    """Chunk-id set comparison between Lance (authoritative) and the store.

    On mismatch, the derived tables for ``table_name`` are rebuilt from
    ``fetch_rows()`` (full Lance row fetch, vectors excluded by the caller).
    ``expected=True`` marks a rebuild that is anticipated (fresh store, full
    rebuild) so the diagnostic is informational rather than a repair warning.
    ``raw_rows`` is the Lance RAW row count when the caller has it (the id
    fetch's row total, dup-id rows included) — recorded with the unique count
    at every successful reconcile as the exact-comparison basis for the
    zero-change heal probe and the health coverage flag (1sbfj).
    """
    store_ids = registry_chunk_ids(index_dir, table_name)
    cold = False
    conn = open_read_only(index_dir)
    if conn is not None:
        try:
            cold = IndexStateStore._get_meta(conn, META_CHUNK_INDEX_COLD) == "1"
        finally:
            try:
                conn.close()
            except sqlite3.Error:
                pass
    if force:
        # Operator-requested from-scratch rebuild of the derived state
        # (index_build content='fts', 1sek8): skip the in-sync early
        # return AND the crash-window messaging — this is intentional
        # maintenance, not a repair.
        msg = (
            f"index-state-store: rebuilding derived chunk index for '{table_name}' "
            f"from Lance ({len(lance_ids)} chunks — operator-requested)"
        )
        print(msg, flush=True)
        store_log(index_dir, msg)
    elif store_ids is not None and store_ids == lance_ids:
        # In sync — record the sync-time counts (and clear a cold flag left
        # by e.g. the full-rebuild path having already repopulated everything).
        _record_chunk_sync_counts(
            index_dir, table_name, raw_rows, len(store_ids), clear_cold=cold
        )
        return {"reconciled": False, "in_sync": True}
    if force:
        pass  # message already printed above
    elif cold or not store_ids:
        # Cold start: a just-created or just-reset store (install, upgrade,
        # schema bump) is EXPECTED to need the backfill from Lance — routine
        # provisioning, not a crash repair, even when partial in-build deltas
        # already populated some rows. Say so calmly; the loud crash-window
        # diagnostic below is reserved for a warm store that genuinely
        # diverged from Lance.
        msg = (
            f"build_index: building derived chunk index for '{table_name}' from Lance "
            f"({len(lance_ids)} chunks — provisioning this store)"
        )
        print(msg, flush=True)
        store_log(index_dir, msg)
    elif not expected:
        msg = (
            f"index-state-store: chunk-index for '{table_name}' out of sync with Lance "
            f"(store={len(store_ids)} ids, "
            f"lance={len(lance_ids)} ids) — rebuilding derived tables from Lance "
            f"(crash-window reconciliation)"
        )
        print(msg, file=sys.stderr, flush=True)
        store_log(index_dir, msg)
    written = rebuild_chunk_index(index_dir, table_name, fetch_rows())
    store_log(
        index_dir,
        f"index-state-store: chunk-index for '{table_name}' rebuilt from Lance "
        f"({written} rows written)",
    )
    # A successful rebuild-from-Lance IS provisioning complete — clear the
    # cold flag unconditionally and record the sync-time counts (1sbfj).
    # The prior ``if cold:`` guard leaked a permanently-cold store when the
    # reconcile itself CREATED the store: the flag was read before the store
    # existed (False), set during creation inside the rebuild, and then never
    # cleared — so every later divergence logged as calm provisioning and the
    # zero-change heal probe re-reconciled a healthy store once per build.
    _record_chunk_sync_counts(index_dir, table_name, raw_rows, written, clear_cold=True)
    return {"reconciled": True, "in_sync": False, "rows_written": written}


def _fts_match_expression(query: str) -> str:
    """Build a safe FTS5 MATCH expression from arbitrary user query text.

    Every whitespace token is double-quoted (with embedded quotes doubled) so
    FTS operators/syntax in the input are treated as literals; tokens are
    OR-joined for BM25 candidate recall. The expression itself is bound as a
    parameter — user text never reaches the SQL string.
    """
    tokens = [t for t in query.split() if t][:FTS_QUERY_MAX_TOKENS]
    quoted = ['"' + t.replace('"', '""') + '"' for t in tokens]
    return " OR ".join(quoted)


def fts_probe(index_dir: Path, table_name: str) -> bool:
    """Cheap FTS-layer liveness probe (1seaq review fix): True when the FTS5
    virtual table for ``table_name`` is queryable. Distinguishes a PARTIALLY
    corrupt store (build_state readable, FTS shadow tables broken/dropped)
    from a genuine zero-hit — ``fts_search`` itself fails soft to ``[]`` for
    the fusion hot path, which would otherwise mask infrastructure failure
    as an empty corpus."""
    if table_name not in ("docs", "code"):
        return False
    conn = open_read_only(index_dir)
    if conn is None:
        return False
    try:
        # Liveness = the REAL serving path works (release-review fix): a
        # bare row count passes with dropped/corrupt FTS5 shadow tables
        # (fts_*_idx / fts_*_docsize), which only a MATCH/bm25 query
        # exercises. Run one.
        conn.execute(
            f"SELECT bm25(fts_{table_name}) FROM fts_{table_name} "
            f"WHERE fts_{table_name} MATCH ? LIMIT 1",
            ('"__wf_probe_token__"',),
        ).fetchone()
        # Parity (release-review fix): registry and FTS commit in the same
        # reconcile transaction, so any row-count divergence — truncation,
        # partial damage, recreated-empty — means the lexical layer is NOT
        # the published one.
        fts_rows = int(conn.execute(f"SELECT count(*) FROM fts_{table_name}").fetchone()[0])
        reg_rows = int(conn.execute(
            "SELECT count(*) FROM chunk_registry WHERE table_name = ?", (table_name,)
        ).fetchone()[0])
        if fts_rows != reg_rows:
            return False
        # Shadow-table parity (release-review round 2): the miss-token MATCH
        # above never evaluates bm25 on a row, so a dropped/truncated
        # ``_docsize`` (or ``_content``) shadow table would still pass and
        # then break — or silently skew — real queries. Contentful FTS5
        # keeps one row per document in both; enforce exact parity
        # deterministically (no tokenizer dependence).
        for shadow in ("docsize", "content"):
            shadow_rows = int(conn.execute(
                f"SELECT count(*) FROM fts_{table_name}_{shadow}"
            ).fetchone()[0])
            if shadow_rows != fts_rows:
                return False
        return True
    except sqlite3.Error:
        return False
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def fts_search(
    index_dir: Path,
    table_name: str,
    query: str,
    limit: int = 20,
    *,
    kind: Optional[str] = None,
    tags_any: Optional[Iterable[str]] = None,
) -> list[dict[str, Any]]:
    """Top-``limit`` BM25 candidates from one FTS table (read-only).

    Returns ``[{id, path, kind, language, tags, lines, text, bm25}]``
    best-first. Optional filters mirror the ``search_code`` contract (1sauc):
    ``kind`` is an exact match; ``tags_any`` matches rows whose space-joined
    tags string contains ANY of the given tags (substring semantics, matching
    the Lance ``tags LIKE`` clause this replaced). All values are bound
    parameters. Degrades to ``[]`` on: absent store, FTS unavailable,
    FTS-hostile query (rejected syntax), or any sqlite error — the caller's
    retrieval stays vector-only with no error (1rrr0 Req 3).
    """
    fts_name = FTS_TABLES.get(table_name)
    if fts_name is None:
        return []
    match = _fts_match_expression(query)
    if not match:
        return []
    conn = open_read_only(index_dir)
    if conn is None:
        return []
    where = [f"{fts_name} MATCH ?"]
    params: list[Any] = [match]
    if kind:
        where.append("kind = ?")
        params.append(str(kind))
    tag_list = [str(t) for t in (tags_any or []) if t]
    if tag_list:
        where.append("(" + " OR ".join("tags LIKE ?" for _ in tag_list) + ")")
        params.extend(f"%{t}%" for t in tag_list)
    params.append(int(limit))
    try:
        rows = conn.execute(
            f"SELECT chunk_id, path, kind, language, tags, start_line, end_line, text, "
            f"bm25({fts_name}) AS score FROM {fts_name} "
            f"WHERE {' AND '.join(where)} ORDER BY score LIMIT ?",
            params,
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass
    return [
        {
            "id": str(cid), "path": str(path), "kind": str(kind_v or ""),
            "language": str(language or ""), "tags": str(tags or ""),
            "lines": [int(start or 0), int(end or 0)],
            "text": str(text or ""), "bm25": float(score),
        }
        for cid, path, kind_v, language, tags, start, end, text, score in rows
    ]


# ---------------------------------------------------------------------------
# Per-file secret-scan cache (1rsha, Tier 1 — Tier-2-ready schema)
# ---------------------------------------------------------------------------
#
# The cache is a SKIP OPTIMIZATION over the unchanged scanner, never a
# reinterpretation of it: a file is skipped only when its content hash AND
# the aggregate rules fingerprint both match its cached row; every failure
# mode (absent store, corrupt cache, hash error) fails TOWARD a full scan
# with a loud diagnostic — a cache defect must never become a missed secret.


def file_content_hash(path: Path) -> Optional[str]:
    """SHA-256 of file bytes; None when unreadable (→ never skipped)."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def secret_scan_filter(
    index_dir: Path, root: Path, rel_paths: Iterable[str], rules_fingerprint: str
) -> tuple[list[str], int, dict[str, str]]:
    """Partition candidates into (to_scan, skipped_count, content_hashes).

    A path is skipped only when its current content hash and the current
    rules fingerprint both match its cached row (1rsha Req 2 — content-
    addressed, so branch switches / whitespace-only touches / touch-and-
    revert skip correctly). Fail-safe: any store error returns every
    candidate for scanning with a diagnostic.
    """
    rel_list = [str(p) for p in rel_paths]
    hashes: dict[str, str] = {}
    conn = open_read_only(index_dir)
    if conn is None:
        return rel_list, 0, hashes
    try:
        cached = {
            str(p): (str(ch), str(rf))
            for p, ch, rf in conn.execute(
                "SELECT path, content_hash, rules_fingerprint FROM secret_scan_cache"
            ).fetchall()
        }
    except sqlite3.Error as exc:
        print(
            f"secret-scan-cache: unreadable ({exc}) — scanning all candidates "
            f"(fail-safe toward full scan)",
            file=sys.stderr,
            flush=True,
        )
        return rel_list, 0, hashes
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass
    to_scan: list[str] = []
    skipped = 0
    for rel in rel_list:
        row = cached.get(rel)
        content_hash = file_content_hash(Path(root) / rel)
        if content_hash is not None:
            hashes[rel] = content_hash
        if (
            row is not None
            and content_hash is not None
            and row[0] == content_hash
            and row[1] == rules_fingerprint
        ):
            skipped += 1
            continue
        to_scan.append(rel)
    return to_scan, skipped, hashes


def secret_scan_record(
    index_dir: Path,
    root: Path,
    *,
    scanned_rel_paths: Iterable[str],
    rules_fingerprint: str,
    findings_by_file: dict[str, list],
    content_hashes: Optional[dict[str, str]] = None,
    removed_rel_paths: Iterable[str] = (),
    rule_catalog: Optional[dict[str, str]] = None,
) -> None:
    """Record one scan pass's results in a single transaction (crash-safe).

    Upserts a cache row per scanned file (content hash, rules fingerprint,
    clean flag, derived finding refs), deletes rows for removed files, and
    persists the Tier-2-ready per-rule catalog for this fingerprint. Never
    raises — a failed record just means those files re-scan next time.
    """
    try:
        content_hashes = dict(content_hashes or {})
        now = int(time.time())
        rows = []
        for rel in scanned_rel_paths:
            rel = str(rel)
            content_hash = content_hashes.get(rel) or file_content_hash(Path(root) / rel)
            if content_hash is None:
                continue  # unreadable → no cache row → always re-scanned
            refs = findings_by_file.get(rel) or []
            rows.append((
                rel, content_hash, rules_fingerprint, now,
                0 if refs else 1,
                json.dumps(refs, separators=(",", ":"), default=str),
            ))
        store = IndexStateStore(index_dir)
        try:
            store.ensure_current()
            conn = store._conn
            with conn:
                conn.executemany(
                    "INSERT INTO secret_scan_cache "
                    "(path, content_hash, rules_fingerprint, scanned_at, clean, finding_refs) "
                    "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(path) DO UPDATE SET "
                    "content_hash=excluded.content_hash, "
                    "rules_fingerprint=excluded.rules_fingerprint, "
                    "scanned_at=excluded.scanned_at, clean=excluded.clean, "
                    "finding_refs=excluded.finding_refs",
                    rows,
                )
                conn.executemany(
                    "DELETE FROM secret_scan_cache WHERE path = ?",
                    [(str(p),) for p in removed_rel_paths],
                )
                if rule_catalog:
                    conn.execute(
                        "DELETE FROM secret_rule_catalog WHERE rules_fingerprint = ?",
                        (rules_fingerprint,),
                    )
                    conn.executemany(
                        "INSERT OR REPLACE INTO secret_rule_catalog "
                        "(rules_fingerprint, rule_id, rule_hash) VALUES (?, ?, ?)",
                        [(rules_fingerprint, rid, rh) for rid, rh in rule_catalog.items()],
                    )
        finally:
            store.close()
    except Exception as exc:  # noqa: BLE001 - cache write failure = re-scan next time
        print(
            f"secret-scan-cache: record skipped ({exc}) — affected files re-scan next pass",
            file=sys.stderr,
            flush=True,
        )


def secret_rule_catalog_for(index_dir: Path, rules_fingerprint: str) -> dict[str, str]:
    """The stored per-rule catalog for an aggregate fingerprint (Tier-2 delta input)."""
    conn = open_read_only(index_dir)
    if conn is None:
        return {}
    try:
        rows = conn.execute(
            "SELECT rule_id, rule_hash FROM secret_rule_catalog WHERE rules_fingerprint = ?",
            (rules_fingerprint,),
        ).fetchall()
        return {str(rid): str(rh) for rid, rh in rows}
    except sqlite3.Error:
        return {}
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


# ---------------------------------------------------------------------------
# Per-path build bookkeeping + snapshot readers (1rrr0; sole authority since 1sed6)
# ---------------------------------------------------------------------------

_LAYER_META_JSON_KEYS = ("model_versions", "chunker_versions", "content")
_LAYER_META_STR_KEYS = ("built_at", "walker_version")


def _full_durable_connection(index_dir: Path) -> "sqlite3.Connection":
    """A dedicated connection with FULL synchronous semantics (1sed6).

    Used ONLY for the two safety-critical boundary commits of a mutating
    build — the pre-mutation `building` fence and the finalization CAS. The
    store's ordinary ``synchronous=NORMAL`` can lose the most recent commit
    on power failure, which for the fence would recreate exactly the
    false-ready window the epoch exists to close. Everything else keeps
    NORMAL (performance posture unchanged).
    """
    path = state_store_path(index_dir)
    conn = sqlite3.connect(path.as_posix(), timeout=10.0)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA synchronous=FULL")
    return conn


def begin_build_epoch(index_dir: Path, scope: str) -> str:
    """Durably mark the store `building` BEFORE the first index mutation (1sed6).

    Returns the attempt id the caller must present to finalize. NOT
    fail-soft: a failure here must fail the build visibly (raising is the
    contract — the caller may not mutate Lance/FTS without the fence).
    Committed with FULL-synchronous durability so a power failure cannot
    lose the fence. Ensures the store exists/current first (creation or a
    version-gated reset both land `uninitialized`, which this immediately
    transitions).
    """
    store = IndexStateStore(index_dir)
    try:
        store.ensure_current()
    finally:
        store.close()
    import uuid
    attempt_id = uuid.uuid4().hex
    conn = _full_durable_connection(index_dir)
    try:
        with conn:
            conn.execute(
                "UPDATE build_state SET attempt_id = ?, scope = ?, status = 'building', "
                "started_at = ?, completed_at = NULL WHERE id = 1",
                (attempt_id, str(scope or ""), time.time()),
            )
    finally:
        conn.close()
    return attempt_id


def finalize_build_epoch(index_dir: Path, attempt_id: str) -> bool:
    """Attempt-ID compare-and-set completion: advance generation, mark complete.

    One FULL-durable transaction. Returns False when the CAS misses (a newer
    attempt superseded this build, or the epoch is not `building` for this
    attempt) — the caller must treat that as a failed publication, never as
    success. Only this function may advance `generation`.
    """
    backfill_run_id = os.environ.get("WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID", "").strip()

    def _finalize() -> bool:
        state = read_build_state(index_dir)
        if (
            state is None
            or state.get("status") != "building"
            or state.get("attempt_id") != str(attempt_id)
        ):
            return False
        authorized = False
        if backfill_run_id:
            import memory_backfill

            root = index_dir.parent.parent
            # The gate exists to stop publication while memory work is
            # pending. `publishing_index`/`indexed` mean the zero-pending
            # census was already frozen by this scope's authorized pass, so
            # trailing passes (graph, FTS derived rebuild, optimize)
            # finalize ungated instead of being refused and stranding the
            # epoch at `building`. Every other stored state routes through
            # authorize, which re-syncs the census before deciding (the
            # stored state may lag validation); an unknown run stays
            # fail-closed.
            gate_state = memory_backfill.run_state(root, backfill_run_id)
            if gate_state is None:
                return False
            if gate_state not in {"publishing_index", "indexed"}:
                if not memory_backfill.authorize_index_finalize(
                    root,
                    backfill_run_id,
                    str(attempt_id),
                    int(state["generation"]) + 1,
                ):
                    return False
                authorized = True
        conn = _full_durable_connection(index_dir)
        try:
            with conn:
                cur = conn.execute(
                    "UPDATE build_state SET status = 'complete', generation = generation + 1, "
                    "completed_at = ? WHERE id = 1 AND attempt_id = ? AND status = 'building'",
                    (time.time(), str(attempt_id)),
                )
                finalized = cur.rowcount == 1
        finally:
            conn.close()
        if finalized and authorized:
            import memory_backfill

            # Success is certain exactly here; the last-build row this CAS
            # just wrote is legitimately overwritten by trailing passes, so
            # the run is completed now rather than re-derived from it later.
            memory_backfill.record_publication_success(
                index_dir.parent.parent, backfill_run_id, str(attempt_id)
            )
        return finalized

    if not backfill_run_id:
        return _finalize()

    # Candidate creation/validation uses this same process-released lock. Hold
    # it across the last census and epoch CAS so no sanctioned memory writer
    # can create new pending work inside the publication boundary.
    import review_evidence

    with review_evidence.review_event_write_lock(index_dir.parent.parent):
        return _finalize()


def read_build_state(index_dir: Path) -> Optional[dict[str, Any]]:
    """Read-only build-state row: ``{attempt_id, scope, status, generation,
    started_at, completed_at}``; ``None`` when the store/row is absent or
    unreadable (readers treat None as fail-closed / not ready)."""
    conn = open_read_only(index_dir)
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT attempt_id, scope, status, generation, started_at, completed_at "
            "FROM build_state WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        return {
            "attempt_id": str(row[0]), "scope": str(row[1]), "status": str(row[2]),
            "generation": int(row[3]), "started_at": row[4], "completed_at": row[5],
        }
    except sqlite3.Error:
        return None
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def build_epoch_state_token(index_dir: Path) -> Optional[tuple[str, str, int]]:
    """The ABA-proof consistency token (1sed6 review fix): ``(attempt_id,
    status, generation)`` of the build-state row in ANY state, ``None`` only
    when the store/row is absent or unreadable. Unlike ``build_epoch_token``
    (complete-only; used for readiness gating), this token distinguishes
    different incomplete attempts — ``building A`` vs ``building B`` — so a
    reader that sanctions a degraded not-ready path can still detect that a
    publication (or a new fence) happened underneath the operation. Every
    state transition changes it: ``begin_build_epoch`` mints a fresh attempt
    id and ``finalize_build_epoch`` advances the generation.
    """
    state = read_build_state(index_dir)
    if state is None:
        return None
    return (state["attempt_id"], state["status"], state["generation"])


def build_epoch_token(index_dir: Path) -> Optional[tuple[str, int]]:
    """The reader validation token: ``(attempt_id, generation)`` — ONLY when
    the epoch is `complete`; ``None`` for uninitialized/building/absent/
    unreadable states (fail closed). Readers capture this before an indexed
    operation and re-read after; a changed or None token discards results.
    Cheap: one short read-only query, no state held across the operation.
    """
    state = read_build_state(index_dir)
    if state is None or state.get("status") != "complete":
        return None
    return (state["attempt_id"], state["generation"])


def write_build_bookkeeping(index_dir: Path, meta: dict[str, Any]) -> None:
    """Persist one build's canonical state into the store. One transaction.

    The store is the SOLE source of truth for per-path build state (1rrr0
    Req 6; exclusive since 1sed6 — nothing is exported to disk). Readers
    reconstruct the legacy dict shape via ``export_meta_snapshot`` /
    ``read_build_summary``.
    """
    file_meta = meta.get("file_meta") or {}
    store = IndexStateStore(index_dir)
    try:
        store.ensure_current()
        conn = store._conn
        with conn:
            conn.execute("DELETE FROM build_file_meta")
            conn.executemany(
                "INSERT INTO build_file_meta (path, hash, mtime, size, inode, chunks_emitted) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        path,
                        str(entry.get("hash") or ""),
                        entry.get("mtime"),
                        entry.get("size"),
                        entry.get("inode"),
                        entry.get("chunks_emitted"),
                    )
                    for path, entry in file_meta.items()
                    if isinstance(entry, dict)
                ],
            )
            conn.execute("DELETE FROM build_layer_meta")
            layer_rows = []
            for key in _LAYER_META_STR_KEYS:
                if key in meta:
                    layer_rows.append((key, str(meta.get(key) or "")))
            for key in _LAYER_META_JSON_KEYS:
                if key in meta:
                    layer_rows.append(
                        (key, json.dumps(meta.get(key), separators=(",", ":")))
                    )
            conn.executemany(
                "INSERT INTO build_layer_meta (key, value) VALUES (?, ?)", layer_rows
            )
    finally:
        store.close()


def read_build_file_meta(
    index_dir: Path, paths: Iterable[str]
) -> Optional[dict[str, dict[str, Any]]]:
    """Read one bounded batch of indexed per-path stat metadata.

    Context-efficiency telemetry uses this instead of exporting the complete
    build snapshot on every retrieval. The caller supplies only distinct
    response-source paths; one read-only query returns their existing
    build-version rows and never creates or upgrades the store.
    """

    requested = sorted({str(path).replace("\\", "/") for path in paths if path})
    if not requested:
        return {}
    conn = open_read_only(index_dir)
    if conn is None:
        return None
    try:
        placeholders = ",".join("?" for _ in requested)
        rows = conn.execute(
            "SELECT path,mtime,size,inode FROM build_file_meta "
            f"WHERE path IN ({placeholders})",
            requested,
        ).fetchall()
        return {
            str(path): {
                "mtime": mtime,
                "size": size,
                "inode": inode,
            }
            for path, mtime, size, inode in rows
        }
    except sqlite3.Error:
        return None
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def export_meta_snapshot(index_dir: Path) -> Optional[dict[str, Any]]:
    """Reconstruct the full per-path build-state dict from the bookkeeping tables.

    The dict shape matches what the retired meta.json used to carry (so
    every migrated consumer kept its parsing). Returns None when the store
    is absent or the bookkeeping tables are empty — callers treat that as
    not-built (there is no fallback surface). Use ``read_build_summary``
    unless the caller genuinely needs the per-file rows.
    """
    conn = open_read_only(index_dir)
    if conn is None:
        return None
    try:
        layer = dict(conn.execute("SELECT key, value FROM build_layer_meta").fetchall())
        if not layer:
            return None
        snapshot: dict[str, Any] = {}
        if "built_at" in layer:
            snapshot["built_at"] = str(layer["built_at"])
        for key in _LAYER_META_JSON_KEYS:
            if key in layer:
                try:
                    snapshot[key] = json.loads(layer[key])
                except Exception:
                    return None
        if "walker_version" in layer:
            snapshot["walker_version"] = str(layer["walker_version"])
        file_meta: dict[str, Any] = {}
        rows = conn.execute(
            "SELECT path, hash, mtime, size, inode, chunks_emitted FROM build_file_meta"
        ).fetchall()
        for path, digest, mtime, size, inode, chunks_emitted in rows:
            entry: dict[str, Any] = {
                "hash": str(digest), "mtime": mtime, "size": size, "inode": inode,
            }
            if chunks_emitted is not None:
                entry["chunks_emitted"] = int(chunks_emitted)
            file_meta[str(path)] = entry
        snapshot["file_meta"] = file_meta
        # Key order: match the legacy writer's literal order for reviewability.
        ordered_keys = ["built_at", "model_versions", "chunker_versions",
                        "walker_version", "content", "file_meta"]
        return {k: snapshot[k] for k in ordered_keys if k in snapshot}
    except sqlite3.Error:
        return None
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def read_build_summary(index_dir: Path) -> Optional[dict[str, Any]]:
    """Bounded build-state summary (1sed6 review fix): the snapshot scalars
    plus a COUNT of tracked files — never the per-file rows. This is the
    dashboard/status read; use ``export_meta_snapshot`` only when the caller
    genuinely needs per-path state (the indexer's own change detection).
    """
    conn = open_read_only(index_dir)
    if conn is None:
        return None
    try:
        layer = dict(conn.execute("SELECT key, value FROM build_layer_meta").fetchall())
        if not layer:
            return None
        summary: dict[str, Any] = {}
        if "built_at" in layer:
            summary["built_at"] = str(layer["built_at"])
        for key in _LAYER_META_JSON_KEYS:
            if key in layer:
                try:
                    summary[key] = json.loads(layer[key])
                except Exception:
                    return None
        if "walker_version" in layer:
            summary["walker_version"] = str(layer["walker_version"])
        summary["file_count"] = int(
            conn.execute("SELECT COUNT(*) FROM build_file_meta").fetchone()[0]
        )
        return summary
    except sqlite3.Error:
        return None
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


# ---------------------------------------------------------------------------
# Build-time freshness extraction (batched local git; mtime fallback)
# ---------------------------------------------------------------------------


def _git_head(root: Path) -> str:
    try:
        result = _run_git(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


# Typed git-authority states (round-4 re-review P1): `_git_head` conflated
# "timeout / git-missing / error" with "confirmed no repo" into a single empty
# string, so a transient probe FAILURE destructively cleared valid drift. Drift
# clearing must distinguish:
_GIT_AUTHORITY_GIT = "git"                    # a work tree with a resolvable HEAD
_GIT_AUTHORITY_NON_GIT = "confirmed_non_git"  # git ran and POSITIVELY reports no repo
_GIT_AUTHORITY_PROBE_FAILED = "probe_failed"  # git missing / timeout / ambiguous error

# The canonical, POSITIVE "there is no repository here" signal. Every OTHER
# completed-but-failing git invocation — dubious ownership, permission denied, a
# corrupt `.git`, a bad config — is an ERROR, NOT a confirmed non-git repo, and
# must NOT authorize destructive drift clearing (round-4 re-review P1: a
# `fatal: detected dubious ownership` mis-classified as confirmed_non_git). Match
# only this string, and force a C locale so the message is deterministic.
_GIT_NOT_A_REPO_MARKER = "not a git repository"


# Repository-LOCAL git env vars that redirect or reshape what a `-C <root>`
# command reads — discovery/location (GIT_DIR, GIT_WORK_TREE, …), object-graph
# INTERPRETATION (GIT_SHALLOW_FILE, GIT_GRAFT_FILE, GIT_REPLACE_REF_BASE,
# GIT_NO_REPLACE_OBJECTS), and CONFIG injection (GIT_CONFIG*, GIT_INDEX_VERSION).
# ANY of them, inherited ambiently, can silently change published TARGET-repo
# metadata (round-4 re-review (5): GIT_DIR redirected history; (6):
# GIT_SHALLOW_FILE silently truncated it). This hardcoded set is the FALLBACK;
# the authoritative census is `git rev-parse --local-env-vars` (see
# `_git_strip_vars`), so a git-version that adds a new local var is covered
# without a code change.
_GIT_DISCOVERY_ENV_OVERRIDES = frozenset({
    "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_NAMESPACE", "GIT_PREFIX", "GIT_IMPLICIT_WORK_TREE",
    "GIT_SHALLOW_FILE", "GIT_GRAFT_FILE",
    "GIT_REPLACE_REF_BASE", "GIT_NO_REPLACE_OBJECTS",
    "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT",
    "GIT_INDEX_VERSION",
})

# NOTE (scope decision): we deliberately do NOT neutralize the GLOBAL/SYSTEM
# config selectors (GIT_CONFIG_GLOBAL / GIT_CONFIG_SYSTEM / GIT_CONFIG_NOSYSTEM).
# An earlier revision pointed them at os.devnull to make rename detection
# deterministic — but that ALSO discarded protected config, and git only accepts
# `safe.directory` trust from protected (global/system) scope. Nuking it turned a
# normal shared/differently-owned checkout (containers, CI mounts, WSL, shared
# workspaces) into a "dubious ownership" failure → probe_failed → no git
# freshness/drift. A user's git config influencing behavior is normal git, not
# corruption. So instead: pass protected config through (safe.directory keeps
# working), and pin the ONE parser-critical setting — rename detection — with an
# explicit `--no-renames` command flag on the derivation walks (command flags
# outrank all config levels, so derivation stays deterministic without the
# sledgehammer). Broader deterministic git sandboxing is deferred to a future
# wave if field evidence warrants it.

# Cached authoritative strip-set (the census output is a static compiled-in list,
# independent of any ambient env, so it is safe to compute once).
_git_strip_vars_cache: Optional[frozenset] = None


def _git_strip_vars() -> frozenset:
    """The AUTHORITATIVE set of repository-local git env vars to strip.

    Primary source: ``git rev-parse --local-env-vars`` — git's own census of the
    vars it interprets as repository-local, so a newer git that adds a var is
    covered without a code change. Unioned with ``_GIT_DISCOVERY_ENV_OVERRIDES``
    (covers config-injection vars an older git's census may omit, and the case
    where the census call itself fails). Cached."""
    global _git_strip_vars_cache
    if _git_strip_vars_cache is not None:
        return _git_strip_vars_cache
    names: set[str] = set(_GIT_DISCOVERY_ENV_OVERRIDES)
    try:
        # Self-sanitized minimal env + a DIRECT isolated_run (not _run_git, which
        # would recurse). The census output is static, but strip the known set
        # anyway so nothing perturbs the call.
        base = dict(os.environ, LC_ALL="C", LANG="C")
        for v in _GIT_DISCOVERY_ENV_OVERRIDES:
            base.pop(v, None)
        res = subprocess_util.isolated_run(
            ["git", "rev-parse", "--local-env-vars"],
            capture_output=True, text=True, timeout=10, env=base,
        )
        if res.returncode == 0:
            for tok in res.stdout.split():
                tok = tok.strip()
                if tok.startswith("GIT_"):
                    names.add(tok)
    except Exception:
        pass  # census unavailable → the hardcoded fallback still applies
    _git_strip_vars_cache = frozenset(names)
    return _git_strip_vars_cache


def _sanitized_git_env(base: Optional[dict[str, str]] = None) -> dict[str, str]:
    """Env for EVERY git subprocess in the derivation chain: a forced C locale
    (stable English stderr) with ALL repository-local git vars STRIPPED (the
    authoritative ``_git_strip_vars`` census — discovery/location, object-graph
    interpretation, and config injection).

    Round-4 re-review P1s: an inherited ``GIT_DIR=/missing`` made a valid repo
    report 'not a git repository' (authority mis-read); an ambient ``GIT_DIR``
    pointing at a DECOY repo redirected downstream reads; and ``GIT_SHALLOW_FILE``
    silently truncated derived history. Protected GLOBAL/SYSTEM config is passed
    through UNCHANGED (so operator-configured ``safe.directory`` trust keeps
    working on shared/differently-owned checkouts); parser-critical rename
    detection is instead pinned per-command with ``--no-renames``."""
    env = dict(base if base is not None else os.environ)
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    for var in _git_strip_vars():
        env.pop(var, None)
    return env


def _run_git(cmd: list[str], **kwargs: Any):
    """The SINGLE sanctioned entry point for every git subprocess in the
    freshness / fingerprint / drift / gardener / blob-read derivation chain.

    Routes through ``subprocess_util.isolated_run`` with the sanitized git env
    (C locale + stripped repo/discovery overrides) always applied, so a future
    call site cannot silently omit sanitization and let an ambient
    ``GIT_DIR``/``GIT_WORK_TREE`` redirect a ``-C <root>`` command to a decoy.
    Any caller-supplied ``env`` is still sanitized (overrides re-stripped)."""
    kwargs["env"] = _sanitized_git_env(kwargs.get("env"))
    return subprocess_util.isolated_run(cmd, **kwargs)


def _git_marker_present(root: Path) -> bool:
    """True if ANY ``.git`` marker (dir / file / symlink, even broken or
    unreadable) exists at ``root`` or an ancestor. Distinguishes a genuinely
    non-git tree (NO marker anywhere → a confirmed non-git transition may clear)
    from a PRESENT-BUT-INVALID repo — an empty/corrupt ``.git/``, a broken
    ``.git`` worktree pointer file, an unreadable marker — where git also prints
    'not a git repository' but a destructive clear would be wrong (→ probe_failed).
    Walks to the filesystem root, ignoring ceilings, and errs toward 'present'
    (the safe, preserve direction) on any access error."""
    try:
        d = root.resolve()
    except OSError:
        return True  # cannot resolve the tree — ambiguous, preserve
    seen: set[Path] = set()
    while d not in seen:
        seen.add(d)
        try:
            if os.path.lexists(d / ".git"):  # lexists → catches broken symlinks
                return True
        except OSError:
            return True  # unreadable marker location — ambiguous, preserve
        parent = d.parent
        if parent == d:
            break
        d = parent
    return False


def _git_authority(root: Path) -> tuple[str, str]:
    """Typed git-authority probe → ``(state, head)``:

    - ``('git', <40-hex>)``      — a git work tree with a resolvable HEAD.
    - ``('git', '')``            — a git work tree whose HEAD is UNBORN (no
                                   commits yet): it IS a git repo, so drift must
                                   NOT clear (nothing to anchor, but no transition).
    - ``('confirmed_non_git','')`` — git POSITIVELY reports 'not a git repository'
                                   AND no ``.git`` marker exists at root/ancestors
                                   (a genuinely non-git tree). ONLY then may drift
                                   clear stale git-derived state.
    - ``('probe_failed','')``    — git binary missing, the probe timed out, ANY
                                   other completed-but-failing invocation (dubious
                                   ownership, permission, bad config, unexpected
                                   output), OR a present-but-invalid ``.git``
                                   marker (empty/corrupt dir, broken pointer,
                                   unreadable): authority is UNKNOWN, so callers
                                   PRESERVE last-good state (never clear).
    """
    try:
        head = _run_git(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return (_GIT_AUTHORITY_PROBE_FAILED, "")  # git missing / timeout / OSError
    if head.returncode == 0:
        sha = (head.stdout or "").strip()
        if _HEX40_RE.match(sha):
            return (_GIT_AUTHORITY_GIT, sha)
        return (_GIT_AUTHORITY_PROBE_FAILED, "")  # unexpected rev-parse output
    # Nonzero: an unborn HEAD (git, no commits), a non-repo, AND error states
    # (dubious ownership / permission / corrupt) all exit nonzero. Disambiguate
    # via the work-tree probe (timeouts/missing-binary already returned above).
    try:
        wt = _run_git(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return (_GIT_AUTHORITY_PROBE_FAILED, "")
    out = (wt.stdout or "").strip()
    if wt.returncode == 0 and out == "true":
        return (_GIT_AUTHORITY_GIT, "")            # git work tree, HEAD unborn
    # A CONFIRMED non-git result requires BOTH the positive 'not a git
    # repository' fatal AND the genuine ABSENCE of any `.git` marker. git prints
    # the same message for an empty/corrupt `.git/`, a broken worktree pointer,
    # or an inherited bad env — those are present-but-invalid REPOS, not non-git
    # trees, so the on-disk marker check forces probe_failed (preserve). Every
    # other nonzero exit (dubious ownership, permission, bad config) and any
    # non-"true" exit-0 result also preserves.
    stderr = (wt.stderr or "").lower()
    if wt.returncode != 0 and _GIT_NOT_A_REPO_MARKER in stderr:
        if _git_marker_present(root):
            return (_GIT_AUTHORITY_PROBE_FAILED, "")  # present-but-invalid repo
        return (_GIT_AUTHORITY_NON_GIT, "")
    return (_GIT_AUTHORITY_PROBE_FAILED, "")


def _paths_hash(paths: Iterable[str]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def _collect_git_freshness(
    root: Path, paths: set[str], *, window_days: int = FRESHNESS_CHURN_WINDOW_DAYS
) -> tuple[dict[str, dict[str, Any]], list[tuple[str, str, int]]]:
    """One batched ``git log`` pass → per-path freshness + window commit rows.

    Iterates newest→oldest: the first appearance of a path is its
    ``last_modified``; appearances with a timestamp inside the trailing
    window count toward churn. One subprocess per build (1ro43 Req 1:
    batched, local-only; no per-query git is ever spawned — this runs only
    on the build path). Returns ``({path: entry}, [(path, sha, ts), ...])``.
    """
    rows: dict[str, dict[str, Any]] = {}
    commits: list[tuple[str, str, int]] = []
    window_start = int(time.time()) - window_days * 86400
    try:
        result = _run_git(
            [
                "git", "-C", str(root), "-c", "core.quotepath=off", "log",
                f"--max-count={FRESHNESS_GIT_LOG_MAX_COMMITS}",
                # Pin rename detection OFF so derivation is deterministic
                # regardless of the user's `diff.renames` config (a command flag
                # outranks all config levels); consistent with the gardener pass.
                "--no-renames",
                "--name-only", "--pretty=format:\x01%H %ct",
            ],
            capture_output=True, text=True, timeout=120, errors="replace",
        )
        if result.returncode != 0:
            return rows, commits
    except Exception:
        return rows, commits

    counts: dict[str, int] = {}
    sha, ts = "", 0
    for line in result.stdout.splitlines():
        if line.startswith("\x01"):
            head = line[1:].split(" ", 1)
            sha = head[0]
            try:
                ts = int(head[1]) if len(head) > 1 else 0
            except ValueError:
                ts = 0
            continue
        rel = line.strip()
        if not rel or rel not in paths:
            continue
        entry = rows.get(rel)
        if entry is None:
            rows[rel] = {"last_modified": ts, "source": "git"}
        if ts >= window_start:
            counts[rel] = counts.get(rel, 0) + 1
            commits.append((rel, sha, ts))
    for rel, entry in rows.items():
        count = counts.get(rel, 0)
        entry["commit_count"] = count
        entry["churn_score"] = min(1.0, count / float(FRESHNESS_CHURN_NORMALIZE_COMMITS))
    return rows, commits


def update_freshness_from_build(
    root: Path,
    index_dir: Path,
    paths: Iterable[str],
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Refresh the freshness/attribution tables for one build pass.

    Called by the indexer at the end of a build, inside the index-build lock.
    Zero-change skip (1rq4h Req 4): when the git HEAD fingerprint AND the
    indexed path set both match the stored values, the write is skipped
    entirely. Non-git roots always rewrite (mtime fallback, cheap) since
    there is no fingerprint to bind to.

    Never raises: any failure is reported and swallowed — freshness is
    derived-only sidecar state and must not fail a build.
    """
    summary: dict[str, Any] = {"written": 0, "skipped": False}
    try:
        path_set = {str(p) for p in paths}
        current_fp = _git_head(root)
        current_paths_hash = _paths_hash(path_set)
        store = IndexStateStore(index_dir)
        try:
            store.ensure_current()
            if (
                current_fp
                and store.get_meta(META_FRESHNESS_FINGERPRINT) == current_fp
                and store.get_meta(META_FRESHNESS_PATHS_HASH) == current_paths_hash
            ):
                summary["skipped"] = True
                store.end_of_build_maintenance()
                return summary
            git_rows, commits = (
                _collect_git_freshness(root, path_set) if current_fp else ({}, [])
            )
            now = int(time.time())
            rows: dict[str, dict[str, Any]] = {}
            for rel in path_set:
                entry = git_rows.get(rel)
                if entry is None:
                    # Untracked / beyond the git-log cap / non-git root:
                    # filesystem mtime fallback, honestly labeled.
                    try:
                        mtime = int((root / rel).stat().st_mtime)
                    except OSError:
                        mtime = now
                    entry = {
                        "last_modified": mtime,
                        "churn_score": 0.0,
                        "commit_count": 0,
                        "source": "mtime",
                    }
                rows[rel] = entry
            store.apply_freshness(
                rows=rows,
                commits=commits,
                fingerprint=current_fp,
                paths_hash=current_paths_hash,
            )
            store.end_of_build_maintenance()
            summary["written"] = len(rows)
            if verbose:
                print(
                    f"build_index: index-state store freshness updated "
                    f"({len(rows)} paths, {len(commits)} window commits)",
                    flush=True,
                )
        finally:
            store.close()
    except Exception as exc:  # noqa: BLE001 - sidecar state must never fail a build
        print(
            f"build_index: index-state store freshness update skipped: {exc}",
            file=sys.stderr,
        )
        summary["error"] = str(exc)
    return summary


# ---------------------------------------------------------------------------
# Doc-code drift + wave→files attribution (1ro43): build-time derivation
# ---------------------------------------------------------------------------
#
# Optional resident, same posture as the freshness pass: runs at the build
# tail inside the index-build lock, after the mandatory residents and before
# epoch finalize; never fails a build; consumers degrade silently when rows
# are absent. Everything here is derived-only and rebuilds from git + the
# working tree on any mismatch.


def parse_verification_stamp(text: str) -> tuple[Optional[str], bool]:
    """Extract a doc's verification stamp: ``(sha_or_none, malformed)``.

    ``malformed`` is True when a ``Verified against:`` line exists but its
    value is not 7-40 hex chars — docs-lint flags that; drift computation
    ignores it (fail toward the content anchor, never toward false trust).
    """
    match = VERIFICATION_STAMP_PATTERN.search(text)
    if match:
        return match.group(1).lower(), False
    if VERIFICATION_STAMP_LINE.search(text):
        return None, True
    return None, False


_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")


def _collect_git_history(root: Path) -> tuple[bool, list[dict[str, Any]]]:
    """``(ok, commits)`` — one batched ``git log --name-only`` walk, newest→oldest.

    Each commit is ``{sha, ts, parents, subject, files}``. Build-path only.

    ``ok`` is False (delivery-review finding: the walk must not fail open) on:
    subprocess non-zero exit, timeout, exception, OR malformed output — a
    sentinel line whose ``%H``/``%P`` is not a 40-hex SHA, or non-empty stdout
    that parsed to zero commits (garbage/truncation). An empty repository makes
    ``git log`` exit non-zero → ``(False, [])``; that is harmless because the
    build caller gates on ``_git_head`` (empty repo → no HEAD → skipped) before
    ever reaching this walk.
    """
    try:
        result = _run_git(
            [
                "git", "-C", str(root), "-c", "core.quotepath=off", "log",
                f"--max-count={FRESHNESS_GIT_LOG_MAX_COMMITS}",
                # `-c` attributes a MERGE commit's own tree changes (evil-merge /
                # conflict-resolution edits that differ from ALL parents) to the
                # merge under --name-only; a clean merge lists nothing, so no
                # over-count. Without it, a file changed only inside a merge is
                # invisible to path_history and drift mis-counts (delivery-review
                # merge-DAG finding). Non-merge commits are unaffected.
                # `--no-renames`: pin rename detection OFF so path attribution is
                # deterministic regardless of the user's `diff.renames` config (a
                # command flag outranks all config levels); consistent with the
                # gardener pass and _collect_git_freshness.
                "-c", "--no-renames", "--name-only",
                "--pretty=format:\x01%H\x02%ct\x02%P\x02%s",
            ],
            capture_output=True, text=True, timeout=120, errors="replace",
        )
        if result.returncode != 0:
            return False, []
    except Exception:
        return False, []
    commits: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None
    seen_sha: set[str] = set()
    for line in result.stdout.splitlines():
        if line.startswith("\x01"):
            parts = line[1:].split("\x02", 3)
            if len(parts) < 4:
                return False, []  # truncated sentinel
            sha = parts[0].strip()
            if not _HEX40_RE.match(sha):
                return False, []  # malformed commit SHA
            if sha in seen_sha:
                return False, []  # duplicate SHA — malformed/truncated stream
            seen_sha.add(sha)
            parents = parts[2].split() if parts[2] else []
            if any(not _HEX40_RE.match(p) for p in parents):
                return False, []  # malformed parent SHA
            try:
                ts = int(parts[1])
            except ValueError:
                return False, []  # invalid timestamp — reject, do not coerce to 0
            current = {
                "sha": sha,
                "ts": ts,
                "parents": parents,  # full parent SHAs (ancestry, not %ct)
                "subject": parts[3],
                "files": [],
            }
            commits.append(current)
            continue
        if line.strip():
            if current is None:
                return False, []  # orphan content before any commit sentinel
            current["files"].append(line.strip())
    if result.stdout.strip() and not commits:
        return False, []  # non-empty stdout that yielded no commits — garbage
    return True, commits


# The canonical gardener metadata line is the DATE-form `Last verified:` in
# the header block only. Restricting to the date form (delivery-review
# finding) means a body/fenced lookalike such as ``Last verified: see
# `src/a.py` `` is NEVER treated as mechanical — it is real content, so a
# change to it invalidates the skip fingerprint and is material for the anchor.
_GARDENER_DATE_LINE_RE = re.compile(r"^Last verified:\s+\d{4}-\d{2}-\d{2}\s*$")
_GARDENER_DATE_LINE_MULTILINE = re.compile(
    r"^Last verified:\s+\d{4}-\d{2}-\d{2}\s*$", re.MULTILINE
)


# A leading-frontmatter line is blank, a `# Title`, or a `Key: value` metadata
# line — the region where the gardener's `Last verified:` lives. The scan stops
# at the first line that is none of these (a `## ` heading, a code fence, a
# bullet, or prose), so a body/fenced `Last verified: <date>` lookalike is
# NEVER stripped — even in a doc with no `## ` heading at all (delivery-review
# finding: `partition("\n## ")` treated a heading-less doc's whole body as
# header).
_FRONTMATTER_METADATA_RE = re.compile(r"^[A-Za-z][\w .()/-]*:\s")


def _strip_gardener_field(text: str) -> str:
    """Normalize out ONLY the canonical ``Last verified: <date>`` line in the
    leading metadata frontmatter. Body/fenced content is preserved verbatim."""
    out: list[str] = []
    in_frontmatter = True
    stripped = False
    for line in text.split("\n"):
        if in_frontmatter:
            if not stripped and _GARDENER_DATE_LINE_RE.match(line):
                stripped = True
                continue  # drop the single canonical header date line
            if line.strip() and not line.startswith("# ") and not _FRONTMATTER_METADATA_RE.match(line):
                in_frontmatter = False  # first non-metadata line ends frontmatter
        out.append(line)
    return "\n".join(out)


def _batch_git_blobs(root: Path, specs: list[str]) -> Optional[dict[str, tuple[bool, str]]]:
    """Fetch many ``<sha>:<path>`` blobs in ONE ``git cat-file --batch`` call.

    Returns ``{spec: (exists, text)}`` or None on any git failure. This both
    bounds the gardener confirmation to a SINGLE subprocess regardless of
    candidate count (delivery-review perf/DoS finding) AND fails closed on a
    real error while treating a ``missing`` object as legitimate absence — the
    two states the old per-candidate ``git show`` conflated (fail-open
    finding). Output is bytes so per-object sizes are honored exactly.
    """
    if not specs:
        return {}
    req = ("\n".join(specs) + "\n").encode("utf-8")
    try:
        # Route through the shared sanitized wrapper (round-4 re-review P1: this
        # was a DIRECT subprocess.run with no env sanitization, so an ambient
        # GIT_DIR could point cat-file at a DECOY repo's object store). Binary
        # I/O — isolated_run leaves non-text spawns untouched.
        result = _run_git(
            ["git", "-C", str(root), "cat-file", "--batch"],
            input=req, capture_output=True, timeout=120,
        )
        if result.returncode != 0:
            return None
    except Exception:
        return None
    data = result.stdout
    out: dict[str, tuple[bool, str]] = {}
    i, n = 0, len(data)
    for spec in specs:
        nl = data.find(b"\n", i)
        if nl < 0:
            return None  # truncated stream
        header = data[i:nl].decode("utf-8", "replace")
        i = nl + 1
        if header.endswith(" missing"):
            out[spec] = (False, "")
            continue
        parts = header.rsplit(" ", 2)
        if len(parts) != 3:
            return None
        try:
            size = int(parts[2])
        except ValueError:
            return None
        if i + size > n:
            return None  # truncated content
        content = data[i:i + size].decode("utf-8", "replace")
        i += size
        if i < n and data[i:i + 1] == b"\n":
            i += 1  # skip the record's trailing newline
        out[spec] = (True, content)
    return out


def _gardener_only_pairs(
    root: Path,
    commits: list[dict[str, Any]],
    doc_paths: Iterable[str],
) -> tuple[bool, set[tuple[str, str]]]:
    """``(ok, pairs)`` — (commit_sha, doc_path) pairs that were gardener-only.

    Two passes (delivery-review finding: classify by content, not line shape;
    validate patch structure; fail closed on malformed output):

    1. One batched ``git log -p -U0`` over the living-doc pathspec narrows to
       CANDIDATE (commit, doc) pairs whose every changed line is a canonical
       ``Last verified: <date>`` line. The patch stream is structurally
       validated — a ``+++``/hunk/content line with no preceding commit
       sentinel, or a malformed ``@@`` hunk header, returns ``ok=False``.
    2. Each candidate is CONFIRMED by comparing the doc's METADATA-SCOPED
       normalized content at the commit vs its first-parent version
       (``_strip_gardener_field`` removes only the header date line). A
       fenced/body ``Last verified: <date>`` edit therefore stays material
       (its body date survives normalization → content differs). The `new`
       version must exist; a git failure there returns ``ok=False``.

    ``ok`` is False on any subprocess non-zero exit, timeout, exception, or
    malformed output — never conflated with "success, no gardener commits".
    """
    paths = sorted({str(p) for p in doc_paths})
    if not paths:
        return True, set()
    try:
        result = _run_git(
            [
                "git", "-C", str(root), "-c", "core.quotepath=off", "log",
                f"--max-count={FRESHNESS_GIT_LOG_MAX_COMMITS}", "--no-color",
                # `--no-merges`: every listed commit is then a non-merge that
                # touched the pathspec, so it MUST carry a complete diff frame —
                # which lets the frame validator below distinguish a truncated
                # stream (sentinel-only / diff-only / header-only) from a real
                # empty result, without a bare-merge false positive.
                "--no-merges", "--no-renames", "-U0",
                "--pretty=format:\x01%H", "--", *paths,
            ],
            capture_output=True, text=True, timeout=120, errors="replace",
        )
        if result.returncode != 0:
            return False, set()
    except Exception:
        return False, set()

    first_parent = {
        str(c["sha"]): (c.get("parents") or [None])[0] for c in commits
    }
    changed: dict[tuple[str, str], bool] = {}   # saw a changed line
    all_date: dict[tuple[str, str], bool] = {}  # every changed line is date-form
    sha = ""
    cur_file: Optional[str] = None
    saw_sentinel = False
    # Frame state — a commit frame is `diff --git`+ `+++` + (`@@` + content)+;
    # each commit must contain at least one COMPLETE such frame. Any partial
    # frame (delivery-review round 4: sentinel-only / diff-only / header-only
    # truncation) fails closed.
    frame_open = f_plus = f_hunk = hunk_content = commit_has_frame = False

    def _frame_complete() -> bool:
        return (not frame_open) or (f_plus and f_hunk and hunk_content)

    for line in result.stdout.splitlines():
        if line.startswith("\x01"):
            if not _frame_complete():
                return False, set()
            if frame_open:
                commit_has_frame = True
            if saw_sentinel and not commit_has_frame:
                return False, set()  # previous commit carried no complete frame
            sha = line[1:].strip()
            if not _HEX40_RE.match(sha):
                return False, set()  # malformed commit sentinel
            saw_sentinel = True
            cur_file = None
            frame_open = f_plus = f_hunk = hunk_content = commit_has_frame = False
        elif line.startswith("diff --git"):
            if not sha:
                return False, set()  # file diff before any commit
            if not _frame_complete():
                return False, set()  # previous frame truncated
            if frame_open:
                commit_has_frame = True
            frame_open = True
            f_plus = f_hunk = hunk_content = False
            cur_file = None
        elif line.startswith("--- "):
            continue
        elif line.startswith("+++ "):
            if not frame_open:
                return False, set()  # +++ with no diff --git
            target = line[4:]
            cur_file = None if target == "/dev/null" else (
                target[2:] if target.startswith("b/") else target)
            f_plus = True
        elif line.startswith("@@"):
            if not frame_open or not f_plus:
                return False, set()  # hunk before its file header
            if not re.match(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@", line):
                return False, set()  # malformed hunk header
            if f_hunk and not hunk_content:
                return False, set()  # previous hunk had no content
            f_hunk = True
            hunk_content = False
        elif line and line[0] in "+-":
            if not sha or cur_file is None or not f_hunk:
                return False, set()  # content outside a well-formed hunk
            hunk_content = True
            key = (sha, cur_file)
            changed[key] = True
            if not _GARDENER_DATE_LINE_RE.match(line[1:]):
                all_date[key] = all_date.get(key, True) and False
            else:
                all_date.setdefault(key, True)
        # else: index/mode/`\ No newline` lines between the file header and
        # the hunk — ignored.

    # Close the final frame + commit (EOF).
    if not _frame_complete():
        return False, set()
    if frame_open:
        commit_has_frame = True
    if saw_sentinel and not commit_has_frame:
        return False, set()  # last commit carried no complete frame
    if result.stdout.strip() and not saw_sentinel:
        return False, set()

    candidates = [k for k in changed if all_date.get(k, False)]
    if not candidates:
        return True, set()
    # ONE batched blob read for every candidate's new + parent version. A git
    # error → None → fail closed; a `missing` parent (creation) → empty old.
    specs: list[str] = []
    for c_sha, rel in candidates:
        specs.append(f"{c_sha}:{rel}")
        parent = first_parent.get(c_sha)
        if parent:
            specs.append(f"{parent}:{rel}")
    blobs = _batch_git_blobs(root, specs)
    if blobs is None:
        return False, set()
    pairs: set[tuple[str, str]] = set()
    for c_sha, rel in candidates:
        new = blobs.get(f"{c_sha}:{rel}")
        if new is None or not new[0]:
            return False, set()  # the changed version MUST exist
        parent = first_parent.get(c_sha)
        old_text = ""
        if parent:
            old = blobs.get(f"{parent}:{rel}")
            if old is None:
                return False, set()
            old_text = old[1]  # (False, "") for a legitimately-absent parent
        if _strip_gardener_field(old_text) == _strip_gardener_field(new[1]):
            pairs.add((c_sha, rel))
    return True, pairs


def derive_wave_attribution(
    commits: list[dict[str, Any]],
) -> tuple[list[tuple[str, str, Optional[int]]], list[tuple[str, str]]]:
    """Landing-commit wave→files derivation (1ro43 Req 12), tolerant patterns.

    Rules calibrated against this repository's real history (censused at the
    2026-07-13 pre-implementation review):
    - ``Land …`` subjects attribute every wave-id token in the subject to the
      commit's diff (covers "Land wave X:", "Land waves X + Y:", "Land waves
      X, Y (1.10.0):", "Land X …", ids in trailing parens, no-colon variants).
      Bundle commits attribute coarsely — every bundled wave shares the change
      set (wave-set attribution, never silently per-wave).
    - Version-only subjects ("Land 1.8.0: …") carry no id token and are
      skipped — derivation degrades to plain churn.
    - ``Close wave <id>`` subjects are landing candidates ONLY for ids with no
      ``Land`` commit: sometimes the close commit carries the implementation
      (no separate landing), but when a Land commit exists the close commit is
      docs-only bookkeeping and counting it would double-attribute.
    - Everything else ("Advance wave", "Bump VERSION", "Plan/Ready wave",
      handoff updates) is excluded; mid-wave Advance commits mean landing-diff
      attribution stays coarse for such waves — accepted best-effort.
    """
    landings: list[tuple[str, str, Optional[int]]] = []
    change_files: dict[tuple[str, str], None] = {}
    landed_ids: set[str] = set()
    close_candidates: list[tuple[str, dict[str, Any]]] = []
    for commit in commits:
        subject = str(commit.get("subject") or "")
        if subject.startswith("Land "):
            ids = set(WAVE_ID_TOKEN.findall(subject))
            for wave_id in ids:
                landed_ids.add(wave_id)
                landings.append((wave_id, str(commit["sha"]), int(commit["ts"]) or None))
                for rel in commit.get("files") or []:
                    change_files[(wave_id, rel)] = None
        elif subject.startswith("Close wave "):
            ids = set(WAVE_ID_TOKEN.findall(subject))
            for wave_id in ids:
                close_candidates.append((wave_id, commit))
    for wave_id, commit in close_candidates:
        if wave_id in landed_ids:
            continue
        landings.append((wave_id, str(commit["sha"]), int(commit["ts"]) or None))
        for rel in commit.get("files") or []:
            change_files[(wave_id, rel)] = None
    return landings, sorted(change_files.keys())


# Candidate path-reference tokens in doc prose: must contain a separator and
# look path-shaped; matches are validated by exact membership in the indexed
# path set, so precision is governed by the repo itself (a token that is not
# an indexed file is never a drift ref).
_DOC_PATH_REF_TOKEN = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_./-]*/[A-Za-z0-9_./-]*[A-Za-z0-9]")

_HISTORICAL_DOC_PREFIX = "docs/waves/"

# Census finding (1ro43 AC-8, this repo): generated point-in-time artifacts
# under docs/reports/ dominated the false-positive tail — a dated reindex
# report can never be "verified against" current code; flagging it is
# meaningless. Annotation (age/churn) still rides via file_freshness; these
# prefixes are only exempt from the DRIFT flag and therefore the worklist.
DRIFT_EXEMPT_PREFIXES = ("docs/reports/",)


def _extract_doc_path_refs(text: str, known_paths: set[str], self_path: str) -> list[str]:
    refs: set[str] = set()
    for match in _DOC_PATH_REF_TOKEN.finditer(text):
        token = match.group(0)
        # Normalize an explicit relative prefix only — a bare leading dot is
        # meaningful (".wavefoundry/framework/…" is a real indexed prefix).
        while token.startswith("./"):
            token = token[2:]
        if token != self_path and token in known_paths:
            refs.add(token)
    return sorted(refs)


def _wave_id_for_historical_path(rel: str) -> Optional[str]:
    """Wave id from a ``docs/waves/<wave-id> <slug>/…`` path, if shaped so."""
    remainder = rel[len(_HISTORICAL_DOC_PREFIX):]
    top = remainder.split("/", 1)[0]
    first_token = top.split(" ", 1)[0]
    if WAVE_ID_TOKEN.fullmatch(first_token):
        return first_token
    return None


def compute_doc_drift(
    root: Path,
    docs_paths: Iterable[str],
    all_paths: Iterable[str],
    commits: list[dict[str, Any]],
    landings: list[tuple[str, str, Optional[int]]],
    change_files: list[tuple[str, str]],
    doc_texts: Optional[dict[str, str]] = None,
    gardener_pairs: Optional[set[tuple[str, str]]] = None,
) -> dict[str, dict[str, Any]]:
    """Per-doc drift rows (1ro43 Reqs 3 + 13) from one shared git walk.

    Living docs: anchor = the newer of the doc's last MATERIAL content change
    and its verification-stamp commit (gardener ``Last verified`` stamps are
    never an anchor). ``commits_since`` counts commits touching a referenced
    path in the ANCESTRY range ``anchor..HEAD`` — reachable from HEAD, not from
    the anchor — so merge-DAG siblings that appear after the anchor in log
    order are counted correctly (delivery-review finding: log position is not
    ancestry). Drift flags at ``DRIFT_COMMITS_THRESHOLD``.

    Historical docs (``docs/waves/``): anchored at their wave's landing
    commit; ``waves_behind`` counts other waves whose landing is a DESCENDANT
    of this wave's landing (landed later by ancestry) and whose change set
    intersects. Never drift-flagged, never worklisted.

    ``gardener_pairs`` (the ``_gardener_only_pairs`` result) is injected by the
    build path; when None it is computed best-effort here for direct callers.
    """
    known_paths = {str(p) for p in all_paths}
    sha_pos: dict[str, int] = {}          # sha → log position (0 = newest); pruning key only
    parents_by_sha: dict[str, list[str]] = {}
    path_history: dict[str, list[tuple[int, str]]] = {}  # rel → [(pos, sha)] newest-first
    for pos, commit in enumerate(commits):
        sha = str(commit["sha"])
        sha_pos.setdefault(sha, pos)
        parents_by_sha.setdefault(sha, [str(p) for p in commit.get("parents") or []])
        for rel in commit.get("files") or []:
            if rel in known_paths:
                path_history.setdefault(rel, []).append((pos, sha))

    def _resolve_stamp_sha(stamp: str) -> Optional[str]:
        if len(stamp) == 40:
            return stamp if stamp in sha_pos else None
        hits = [full for full in sha_pos if full.startswith(stamp)]
        return hits[0] if len(hits) == 1 else None

    def _ancestors(anchor_sha: str, max_pos: Optional[int]) -> set[str]:
        """Ancestors of ``anchor_sha`` (inclusive), pruning branches older than
        ``max_pos`` (they can contain no commit we are asking about)."""
        seen: set[str] = set()
        stack = [anchor_sha]
        while stack:
            s = stack.pop()
            if s in seen:
                continue
            seen.add(s)
            for p in parents_by_sha.get(s, ()):
                if p in seen:
                    continue
                pp = sha_pos.get(p)
                if pp is None:
                    seen.add(p)  # outside the log window — boundary, don't expand
                    continue
                if max_pos is not None and pp > max_pos:
                    seen.add(p)  # older than every commit of interest — prune
                    continue
                stack.append(p)
        return seen

    def _commits_after(refs: set[str], anchor_sha: str) -> int:
        # Distinct commits touching any ref in the ancestry range anchor..HEAD:
        # reachable from HEAD (all logged commits are) but NOT reachable from
        # the anchor. Position is used only to bound the ancestry walk.
        targets: set[str] = set()
        for rel in refs:
            for _pos, sha in path_history.get(rel, ()):
                targets.add(sha)
        targets.discard(anchor_sha)
        if not targets:
            return 0
        max_pos = max((sha_pos.get(t, 0) for t in targets), default=0)
        reachable = _ancestors(anchor_sha, max_pos)
        return sum(1 for t in targets if t not in reachable)

    # Newest landing SHA per wave (min position) + its full ancestor set, for
    # ancestry-based waves-behind (few landings — cheap to precompute).
    wave_landing_sha: dict[str, str] = {}
    wave_landing_pos: dict[str, int] = {}
    for wave_id, sha, _ts in landings:
        pos = sha_pos.get(str(sha))
        if pos is not None and pos < wave_landing_pos.get(wave_id, 1 << 62):
            wave_landing_pos[wave_id] = pos
            wave_landing_sha[wave_id] = str(sha)
    wave_landing_ancestors: dict[str, set[str]] = {
        w: _ancestors(sha, None) for w, sha in wave_landing_sha.items()
    }
    wave_files: dict[str, set[str]] = {}
    for wave_id, rel in change_files:
        wave_files.setdefault(wave_id, set()).add(rel)

    living_docs = [
        str(p) for p in docs_paths
        if not str(p).startswith(_HISTORICAL_DOC_PREFIX)
    ]
    if gardener_pairs is None:
        _ok, gardener_pairs = _gardener_only_pairs(root, commits, living_docs)

    def _material_content(rel: str) -> Optional[str]:
        """Newest commit SHA whose change to the doc was NOT gardener-only."""
        for _pos, sha in path_history.get(rel, ()):  # newest-first
            if (sha, rel) not in gardener_pairs:
                return sha
        hist = path_history.get(rel)
        return hist[-1][1] if hist else None  # all gardener-only → creation

    entries: dict[str, dict[str, Any]] = {}
    for rel in sorted({str(p) for p in docs_paths}):
        if rel.startswith(_HISTORICAL_DOC_PREFIX):
            wave_id = _wave_id_for_historical_path(rel)
            landing_sha = wave_landing_sha.get(wave_id or "")
            if wave_id and landing_sha:
                refs = wave_files.get(wave_id, set())
                # Y landed LATER than X iff X's landing is an ancestor of Y's
                # landing (X reachable from Y) — pure ancestry, not %ct/position.
                behind = sum(
                    1
                    for other, other_ancestors in wave_landing_ancestors.items()
                    if other != wave_id
                    and landing_sha in other_ancestors
                    and wave_files.get(other, set()) & refs
                )
                entries[rel] = {
                    "drifted": False,
                    "drift_refs": [],
                    "commits_since": _commits_after(refs, landing_sha),
                    "anchor_kind": "content",
                    "historical": True,
                    "waves_behind": behind,
                }
            else:
                entries[rel] = {
                    "drifted": False,
                    "drift_refs": [],
                    "commits_since": 0,
                    "anchor_kind": "content",
                    "historical": True,
                    "waves_behind": 0,
                }
            continue
        content_sha = _material_content(rel)
        if doc_texts is not None and rel in doc_texts:
            text = doc_texts[rel]
        else:
            try:
                text = (root / rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
        stamp, _malformed = parse_verification_stamp(text)
        stamp_sha = _resolve_stamp_sha(stamp) if stamp else None
        # Anchor = the NEWER of the material content change and the stamp
        # commit (smaller log position). A live, resolvable stamp governs the
        # KIND label. Ancestry counting is done from the chosen anchor SHA.
        anchor_sha = content_sha
        anchor_kind = "content"
        if stamp_sha is not None:
            if anchor_sha is None or sha_pos.get(stamp_sha, 1 << 62) <= sha_pos.get(anchor_sha, 1 << 62):
                anchor_sha = stamp_sha
            anchor_kind = "verification"
        refs = set(_extract_doc_path_refs(text, known_paths, rel))
        commits_since = (
            _commits_after(refs, anchor_sha) if (refs and anchor_sha is not None) else 0
        )
        drift_exempt = rel.startswith(DRIFT_EXEMPT_PREFIXES)
        entries[rel] = {
            "drifted": bool(refs) and not drift_exempt
            and commits_since >= DRIFT_COMMITS_THRESHOLD,
            "drift_refs": sorted(refs),
            "commits_since": commits_since,
            "anchor_kind": anchor_kind,
            "historical": False,
            "waves_behind": 0,
        }
    return entries


def has_drift_state(index_dir: Path) -> bool:
    """Cheap read-only probe: does the store hold ANY git-derived drift state
    (a drift fingerprint or a ``doc_drift`` row)? Used to gate the no-op-path
    non-git reconcile so a normal git repo does not pay a git probe on every
    zero-change build unless there is actually stale state to reconcile."""
    conn = open_read_only(index_dir)
    if conn is None:
        return False
    try:
        fp = conn.execute(
            "SELECT COUNT(*) FROM meta WHERE key = ?", (META_DRIFT_FINGERPRINT,)
        ).fetchone()
        if fp and int(fp[0]):
            return True
        rows = conn.execute("SELECT COUNT(*) FROM doc_drift").fetchone()
        return bool(rows and int(rows[0]))
    except sqlite3.Error:
        return False
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def _clear_git_derived_drift(index_dir: Path, *, verbose: bool = False) -> dict[str, Any]:
    """Transactionally clear git-derived attribution/drift/fingerprint for a
    CONFIRMED non-git transition. FAIL-CLOSED (round-4 re-review): if the clear
    fails, surface ``drift_clear_failed`` + an error (the atomic transaction
    means no partial clear) so the NEXT build retries rather than silently
    leaving a stale ``drifted: true`` row behind a clean-looking skip."""
    out: dict[str, Any] = {}
    if not state_store_path(index_dir).exists():
        return out
    try:
        store = IndexStateStore(index_dir)
        try:
            store.ensure_current()
            cleared = store.clear_attribution_and_drift()
            if cleared:
                out["cleared_git_derived"] = cleared
                if verbose:
                    print(
                        "build_index: doc drift — git authority confirmed absent; "
                        f"cleared {cleared} stale git-derived drift/attribution "
                        "row(s) so readers degrade cleanly.",
                        flush=True,
                    )
        finally:
            store.close()
    except Exception as exc:  # noqa: BLE001 - sidecar must never raise into the build
        out["drift_clear_failed"] = True
        out["error"] = str(exc)
        print(
            "build_index: WARNING — confirmed git→non-git transition could not "
            f"clear stale drift ({exc}); the stale rows persist and the next "
            "build will retry the clear.",
            file=sys.stderr,
            flush=True,
        )
    return out


def reconcile_non_git_drift(
    root: Path, index_dir: Path, *, verbose: bool = False
) -> dict[str, Any]:
    """No-op-build companion to ``update_drift_from_build`` (round-4 re-review
    P1): the tail drift pass is skipped when a build detects zero file changes,
    so an unchanged copied index — or a repo that lost ``.git`` with no other
    edits — would keep serving stale git-derived drift. This clears it when git
    authority is CONFIRMED absent, and PRESERVES last-good on a probe failure or
    a real git repo. Caller gates on ``has_drift_state`` to avoid a git probe on
    every no-op build in a normal repo."""
    summary: dict[str, Any] = {"skipped": True}
    try:
        git_state, _head = _git_authority(root)
        summary["git_state"] = git_state
        if git_state == _GIT_AUTHORITY_NON_GIT:
            summary.update(_clear_git_derived_drift(index_dir, verbose=verbose))
        # probe_failed / git → preserve, do nothing.
    except Exception as exc:  # noqa: BLE001
        summary["error"] = str(exc)
    return summary


def update_drift_from_build(
    root: Path,
    index_dir: Path,
    docs_paths: Iterable[str],
    all_paths: Iterable[str],
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Refresh wave attribution + doc drift for one build pass (1ro43).

    Same contract as ``update_freshness_from_build``: inside the index-build
    lock, optional resident, never raises. Zero-change skip fingerprints on
    git HEAD + the docs path set + a MATERIAL-CONTENT digest of every living
    doc (gardener ``Last verified:`` lines normalized out). The content digest
    (delivery-review finding) means an uncommitted reference edit at stable
    HEAD — adding, removing, or changing a `path` a doc points at — changes
    the fingerprint and forces recompute, while a mechanical gardener edit does
    not thrash it. The stamp text lives in the doc body, so stamp changes are
    also covered by the content digest.
    """
    summary: dict[str, Any] = {"written": 0, "skipped": False}
    try:
        docs_set = sorted({str(p) for p in docs_paths})
        all_set = {str(p) for p in all_paths}
        # Round-4 re-review P1: use the TYPED git-authority probe. A transient
        # probe failure (timeout / git missing / ambiguous error) must NEVER be
        # read as "non-git" and destructively clear valid last-good drift.
        git_state, head = _git_authority(root)
        if git_state == _GIT_AUTHORITY_PROBE_FAILED:
            # Authority UNKNOWN — preserve last-good drift, skip, retry next build.
            summary["skipped"] = True
            summary["git_probe_failed"] = True
            if verbose:
                print(
                    "build_index: doc drift skipped — git authority probe failed "
                    "(timeout / git missing / ambiguous); prior drift preserved.",
                    file=sys.stderr,
                )
            return summary
        if git_state != _GIT_AUTHORITY_GIT or not head:
            # CONFIRMED non-git (or a git work tree with an unborn HEAD): no
            # commit history, no anchors, no attribution. A fresh project has
            # nothing to do, but a git-built index copied into — or a repo that
            # dropped its git metadata under — a now-non-git root would keep
            # serving stale git-derived drift. Clear ONLY on a CONFIRMED non-git
            # transition (an unborn-HEAD git repo is still git — preserve).
            summary["skipped"] = True
            if git_state == _GIT_AUTHORITY_NON_GIT:
                summary.update(
                    _clear_git_derived_drift(index_dir, verbose=verbose)
                )
            return summary
        content_digest = hashlib.sha256()
        doc_texts: dict[str, str] = {}
        for rel in docs_set:
            try:
                text = (root / rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            doc_texts[rel] = text
            # Hash-prefixed (not delimiter-separated) so no crafted path/body
            # boundary can alias two distinct doc sets to one digest.
            content_digest.update(hashlib.sha256(rel.encode("utf-8")).digest())
            content_digest.update(
                hashlib.sha256(_strip_gardener_field(text).encode("utf-8")).digest()
            )
        fingerprint = f"{head}:{_paths_hash(docs_set)}:{content_digest.hexdigest()}"
        store = IndexStateStore(index_dir)
        try:
            store.ensure_current()
            if store.get_meta(META_DRIFT_FINGERPRINT) == fingerprint:
                summary["skipped"] = True
                return summary
            living_docs = [d for d in docs_set if not d.startswith(_HISTORICAL_DOC_PREFIX)]
            # BOTH git walks must succeed before ANY of attribution / drift
            # rows / fingerprint is replaced (delivery-review finding: neither
            # walk may fail open). A failure preserves the prior state — the
            # last-good drift rows and fingerprint stay untouched — and the
            # next build retries.
            hist_ok, commits = _collect_git_history(root)
            gardener_ok, gardener_pairs = (
                _gardener_only_pairs(root, commits, living_docs) if hist_ok else (False, set())
            )
            if not hist_ok or not gardener_ok:
                summary["skipped"] = True
                summary["drift_detect_failed"] = True
                which = "history walk" if not hist_ok else "gardener classifier"
                print(
                    f"build_index: doc drift update skipped — {which} failed "
                    "(git error/timeout/malformed output); prior drift state "
                    "preserved, will retry next build.",
                    file=sys.stderr,
                )
                return summary
            landings, change_files = derive_wave_attribution(commits)
            entries = compute_doc_drift(
                root, docs_set, all_set, commits, landings, change_files,
                doc_texts=doc_texts, gardener_pairs=gardener_pairs,
            )
            # Single transaction — attribution + drift + fingerprint advance
            # together or not at all (no torn write between two commits).
            store.replace_attribution_and_drift(
                landings=landings, change_files=change_files,
                entries=entries, fingerprint=fingerprint,
            )
            summary["written"] = len(entries)
            summary["waves_attributed"] = len({w for w, _s, _t in landings})
            if verbose:
                drifted = sum(1 for e in entries.values() if e.get("drifted"))
                print(
                    f"build_index: doc drift updated ({len(entries)} docs, "
                    f"{drifted} drift-flagged, "
                    f"{summary['waves_attributed']} waves attributed)",
                    flush=True,
                )
        finally:
            store.close()
    except Exception as exc:  # noqa: BLE001 - sidecar state must never fail a build
        print(
            f"build_index: doc drift update skipped: {exc}",
            file=sys.stderr,
        )
        summary["error"] = str(exc)
    return summary


# ---------------------------------------------------------------------------
# Integrity probe (1rq4h Req 11) and unified maintenance (Req 10)
# ---------------------------------------------------------------------------


def probe_state_store(root: Path, index_dir: Path, *, deep: bool = False) -> dict[str, Any]:
    """Two-layer integrity probe for the index-state store.

    Layer 1 (physical/structural): ``quick_check`` (or full
    ``integrity_check`` when ``deep``). Layer 2 (logical/staleness): the
    stored freshness fingerprint vs the current git HEAD — a
    structurally-sound-but-stale store is reported ``stale-fingerprint``
    (informational: the next build refreshes it; a structural failure routes
    to the derived-only drop-and-rebuild at the next open).

    Returns ``{status: 'ok'|'structural-fail'|'stale-fingerprint'|'absent',
    detail, schema_version}``.
    """
    path = state_store_path(index_dir)
    if not path.exists():
        return {"status": "absent", "detail": "store not yet built", "schema_version": None}
    conn = open_read_only(index_dir)
    if conn is None:
        return {"status": "structural-fail", "detail": "store unreadable", "schema_version": None}
    try:
        pragma = "integrity_check" if deep else "quick_check"
        try:
            check_rows = conn.execute(f"PRAGMA {pragma}").fetchall()
        except sqlite3.Error as exc:
            return {
                "status": "structural-fail",
                "detail": f"{pragma} raised: {exc}",
                "schema_version": None,
            }
        verdicts = [str(r[0]) for r in check_rows]
        if verdicts != ["ok"]:
            return {
                "status": "structural-fail",
                "detail": f"{pragma}: {'; '.join(verdicts[:3])}",
                "schema_version": None,
            }
        # FTS5 internal-consistency contribution (1rrr0 Req 13): the shadow
        # tables can pass quick_check while the FTS segment index is wrong.
        fts_verdict = _fts_integrity_verdict(path)
        if fts_verdict == "fail":
            return {
                "status": "structural-fail",
                "detail": "fts5 integrity-check failed",
                "schema_version": None,
            }
        schema_version = IndexStateStore._get_meta(conn, "store_schema_version")
        stored_fp = IndexStateStore._get_meta(conn, META_FRESHNESS_FINGERPRINT)
        if stored_fp:
            current_fp = _git_head(root)
            if current_fp and current_fp != stored_fp:
                return {
                    "status": "stale-fingerprint",
                    "detail": "freshness fingerprint behind git HEAD (refreshes on next build)",
                    "schema_version": schema_version,
                }
        return {"status": "ok", "detail": pragma, "schema_version": schema_version}
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def _fts5_table_names(conn: "sqlite3.Connection") -> list[str]:
    """Names of fts5 virtual tables in an open store (empty when none)."""
    try:
        rows = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    except sqlite3.Error:
        return []
    return [
        str(name) for name, sql in rows
        if sql and "USING FTS5" in str(sql).upper()
    ]


def _fts_integrity_verdict(path: Path) -> str:
    """Run FTS5's internal integrity-check on every fts5 table in a store.

    Returns ``'ok'`` (all pass or no FTS tables), ``'fail'`` (a check
    failed), or ``'skipped'`` (store could not be opened read-write — e.g.
    locked; the routine probe stays non-blocking). The check is an INSERT
    command, so it needs a write connection even though it mutates nothing.
    """
    try:
        conn = sqlite3.connect(str(path), timeout=2.0)
    except sqlite3.Error:
        return "skipped"
    try:
        conn.execute("PRAGMA busy_timeout=2000")
        for name in _fts5_table_names(conn):
            try:
                conn.execute(f"INSERT INTO {name}({name}) VALUES('integrity-check')")
            except sqlite3.Error:
                return "fail"
        return "ok"
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def sqlite_store_maintenance(
    path: Path, *, full_vacuum: bool = False, deep_integrity: bool = False
) -> dict[str, Any]:
    """Generic SQLite-store maintenance: checkpoint, reclaim, optimize, verify.

    Used by the unified ``index_optimize`` path for every reachable
    SQLite store (the index-state store AND the graph state store — closing
    the "graph index is not reclaimed this way" gap) without touching the
    graph store's own build-path code. On-demand only; the caller holds the
    index-build lock.
    """
    path = Path(path)
    result: dict[str, Any] = {
        "present": path.exists(),
        "size_before_bytes": 0,
        "size_after_bytes": 0,
        "reclaimed_bytes": 0,
        "integrity": None,
        "error": None,
    }
    if not path.exists():
        return result
    result["size_before_bytes"] = _store_size_bytes(path)
    try:
        conn = sqlite3.connect(str(path), timeout=10.0)
        try:
            conn.execute("PRAGMA busy_timeout=10000")
            pragma = "integrity_check" if deep_integrity else "quick_check"
            verdicts = [str(r[0]) for r in conn.execute(f"PRAGMA {pragma}").fetchall()]
            result["integrity"] = "ok" if verdicts == ["ok"] else "structural-fail"
            # FTS5 contributions (1rrr0 Req 12–13): internal integrity-check
            # plus the full segment-merge 'optimize' — this is the on-demand
            # arm of the FTS maintenance (the in-build arm is threshold-gated
            # in apply_chunk_deltas). Skipped naturally when no fts5 tables.
            for fts_name in _fts5_table_names(conn):
                try:
                    conn.execute(
                        f"INSERT INTO {fts_name}({fts_name}) VALUES('integrity-check')"
                    )
                    conn.execute(f"INSERT INTO {fts_name}({fts_name}) VALUES('optimize')")
                    conn.commit()
                except sqlite3.Error:
                    result["integrity"] = "structural-fail"
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            if full_vacuum:
                conn.execute("VACUUM")
            else:
                conn.execute("PRAGMA incremental_vacuum")
            conn.execute("PRAGMA optimize")
        finally:
            conn.close()
    except sqlite3.Error as exc:
        result["error"] = str(exc)
        if result["integrity"] is None:
            result["integrity"] = "structural-fail"
    result["size_after_bytes"] = _store_size_bytes(path)
    result["reclaimed_bytes"] = max(
        0, result["size_before_bytes"] - result["size_after_bytes"]
    )
    return result


def optimize_state_stores(
    index_dir: Path, *, full_vacuum: bool = True, deep_integrity: bool = True
) -> dict[str, dict[str, Any]]:
    """Run SQLite maintenance across every reachable store under the index dir.

    The on-demand arm of the unified maintenance verb (1rq4h Req 10): called
    by ``index_optimize`` and at the end of setup/upgrade, under the
    index-build lock (caller-held). Covers the index-state store and the
    graph state store; stores that don't exist are reported absent, never an
    error.
    """
    index_dir = Path(index_dir)
    stores = {
        "index-state": state_store_path(index_dir),
        "graph-state": index_dir / GRAPH_STATE_STORE_RELPATH,
    }
    return {
        name: sqlite_store_maintenance(
            path, full_vacuum=full_vacuum, deep_integrity=deep_integrity
        )
        for name, path in stores.items()
    }
