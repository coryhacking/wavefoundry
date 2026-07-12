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
rebuildable from git, Lance, the repo, or ``meta.json``. A missing, corrupt,
or schema-mismatched store is a rebuild with a loud diagnostic — never data
loss, never a hard failure, never silent data invention.

**Maintenance posture (1rq4h Req 9):** ``auto_vacuum=INCREMENTAL`` at store
creation; ``wal_checkpoint(TRUNCATE)`` + ``incremental_vacuum`` at the end of
each build pass (the long-lived MCP server reads this store on the query
path, so a pinned reader could otherwise starve WAL autocheckpoint);
``PRAGMA optimize`` at connection close. Full ``VACUUM`` is reserved for the
on-demand ``wave_index_optimize`` path (``optimize_state_stores``).

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
# filter-parity contract after the Lance/Tantivy FTS retirement).
STATE_STORE_SCHEMA_VERSION = "4"

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


def store_log(index_dir: Path, message: str) -> None:
    """Append one timestamped line to the persisted store log (1sbfj).

    Best-effort by contract: never raises, never fails a build. Bounded:
    when the log exceeds ``STORE_LOG_MAX_BYTES`` the newest half is kept
    (truncate-and-continue — concurrent writers at worst interleave lines,
    they cannot fail each other). Callers keep their stdout/stderr prints;
    this is the persistence layer, not a replacement.
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
    except Exception:  # noqa: BLE001 - logging must never fail the caller
        pass


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
            # state; ``meta.json`` is generated from these tables as an
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
        """
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
    if store_ids is not None and store_ids == lance_ids:
        # In sync — record the sync-time counts (and clear a cold flag left
        # by e.g. the full-rebuild path having already repopulated everything).
        _record_chunk_sync_counts(
            index_dir, table_name, raw_rows, len(store_ids), clear_cold=cold
        )
        return {"reconciled": False, "in_sync": True}
    if cold or not store_ids:
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
# Per-path build bookkeeping + meta.json snapshot export (1rrr0)
# ---------------------------------------------------------------------------

_LAYER_META_JSON_KEYS = ("model_versions", "chunker_versions", "content")
_LAYER_META_STR_KEYS = ("built_at", "walker_version")


def write_build_bookkeeping(index_dir: Path, meta: dict[str, Any]) -> None:
    """Persist one build's ``meta.json``-shaped state into the store.

    The store is the working source of truth for per-path build state
    (1rrr0 Req 6); ``meta.json`` is exported from it afterwards via
    ``export_meta_snapshot``. One transaction.
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


def export_meta_snapshot(index_dir: Path) -> Optional[dict[str, Any]]:
    """Reconstruct the ``meta.json`` dict from the store's bookkeeping tables.

    Reader-contract compatible (readiness-council amendment): parsed content
    is semantically identical to what the legacy writer produced; key order
    and formatting may differ. Returns None when the store is absent or the
    bookkeeping tables are empty (caller falls back to the direct write).
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


# ---------------------------------------------------------------------------
# Build-time freshness extraction (batched local git; mtime fallback)
# ---------------------------------------------------------------------------


def _git_head(root: Path) -> str:
    try:
        result = subprocess_util.isolated_run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


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
        result = subprocess_util.isolated_run(
            [
                "git", "-C", str(root), "-c", "core.quotepath=off", "log",
                f"--max-count={FRESHNESS_GIT_LOG_MAX_COMMITS}",
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

    Used by the unified ``wave_index_optimize`` path for every reachable
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
    by ``wave_index_optimize`` and at the end of setup/upgrade, under the
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
