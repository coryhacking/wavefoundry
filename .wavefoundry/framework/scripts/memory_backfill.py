#!/usr/bin/env python3
"""Durable, Git-independent historical-memory backfill coordination.

Mechanical extraction is deliberately separate from agent judgment.  This
module inventories locally present closed waves, checkpoints bounded extraction
in the existing ``memory-state.sqlite`` authority, and exposes short random
claim tokens.  It never creates review ledgers or promotes memory records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MAX_WAVES_PER_CALL = 10
MAX_CANDIDATES_PER_CALL = 20
MAX_RESPONSE_BYTES = 64 * 1024
ACTION_REQUIRED_EXIT = 4
RUN_STATES = (
    "inventory_pending",
    "awaiting_validation",
    "ready_for_index",
    "publishing_index",
    "indexed",
)
_CLOSED_STATES = {"closed", "complete", "completed"}
ENTRY_PATHS = frozenset({"manual", "setup", "upgrade"})
INDEX_PUBLICATION_RUN_ENV = "WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path(root: Path) -> Path:
    return root / ".wavefoundry" / "index" / "memory-state.sqlite"


def _connect(root: Path) -> sqlite3.Connection:
    path = _db_path(root)
    root_real = root.resolve(strict=True)
    framework_dir = root / ".wavefoundry"
    index_dir = framework_dir / "index"
    for directory in (framework_dir, index_dir):
        if directory.is_symlink():
            raise OSError(
                f"historical-memory state directory may not be a symlink: {directory}"
            )
        directory.mkdir(exist_ok=True)
        if not directory.resolve(strict=True).is_relative_to(root_real):
            raise OSError(
                f"historical-memory state directory escapes repository root: {directory}"
            )
    if path.is_symlink():
        raise OSError("memory-state.sqlite may not be a symlink")
    if path.exists() and not path.resolve(strict=True).is_relative_to(
        index_dir.resolve(strict=True)
    ):
        raise OSError("memory-state.sqlite escapes its canonical index directory")
    conn = sqlite3.connect(str(path), timeout=10.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS memory_backfill_runs (
          run_id TEXT PRIMARY KEY,
          entry_path TEXT NOT NULL,
          state TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          last_failure TEXT NOT NULL DEFAULT '',
          publication_attempt_id TEXT NOT NULL DEFAULT '',
          publication_generation INTEGER NOT NULL DEFAULT 0,
          publication_inventory_digest TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS memory_backfill_runs_entry
          ON memory_backfill_runs(entry_path, updated_at);
        CREATE UNIQUE INDEX IF NOT EXISTS memory_backfill_one_active_run
          ON memory_backfill_runs(entry_path) WHERE state!='indexed';
        CREATE TABLE IF NOT EXISTS memory_backfill_waves (
          run_id TEXT NOT NULL,
          wave_id TEXT NOT NULL,
          source_fingerprint TEXT NOT NULL,
          state TEXT NOT NULL,
          claim_token TEXT NOT NULL DEFAULT '',
          candidate_count INTEGER NOT NULL DEFAULT 0,
          outcome TEXT NOT NULL DEFAULT '',
          last_failure TEXT NOT NULL DEFAULT '',
          updated_at TEXT NOT NULL,
          PRIMARY KEY (run_id, wave_id)
        );
        CREATE TABLE IF NOT EXISTS memory_backfill_sources (
          run_id TEXT NOT NULL,
          wave_id TEXT NOT NULL,
          source_event TEXT NOT NULL,
          memory_id TEXT NOT NULL DEFAULT '',
          PRIMARY KEY (run_id, source_event)
        );
        """
    )
    run_columns = {
        str(row[1]) for row in conn.execute("PRAGMA table_info(memory_backfill_runs)")
    }
    for name, declaration in (
        ("publication_attempt_id", "TEXT NOT NULL DEFAULT ''"),
        ("publication_generation", "INTEGER NOT NULL DEFAULT 0"),
        ("publication_inventory_digest", "TEXT NOT NULL DEFAULT ''"),
    ):
        if name not in run_columns:
            conn.execute(
                f"ALTER TABLE memory_backfill_runs ADD COLUMN {name} {declaration}"
            )
    return conn


def _canonical_waves_dir(root: Path) -> Path | None:
    """Return the contained physical waves root, rejecting parent escapes."""

    waves_dir = root / "docs" / "waves"
    if not waves_dir.exists() and not waves_dir.is_symlink():
        return None
    try:
        root_real = root.resolve(strict=True)
        waves_real = waves_dir.resolve(strict=True)
        if (
            not waves_dir.is_dir()
            or not waves_real.is_relative_to(root_real)
        ):
            raise OSError(
                "historical-memory waves directory escapes the repository root"
            )
        return waves_real
    except RuntimeError as exc:
        raise OSError(
            "historical-memory waves directory could not be resolved safely"
        ) from exc


def _contained_source_file(root: Path, wave_dir: Path, path: Path) -> bool:
    """Accept only ordinary files physically contained by this project wave."""

    try:
        waves_real = _canonical_waves_dir(root)
        if waves_real is None:
            return False
        wave_real = wave_dir.resolve(strict=True)
        path_real = path.resolve(strict=True)
        return (
            not wave_dir.is_symlink()
            and not path.is_symlink()
            and wave_real.is_relative_to(waves_real)
            and path_real.is_relative_to(wave_real)
            and path.is_file()
        )
    except (OSError, RuntimeError):
        return False


def _wave_status(root: Path, path: Path) -> tuple[str, str]:
    wave_md = path / "wave.md"
    if not _contained_source_file(root, path, wave_md):
        return "unsupported", "wave.md is not an ordinary contained wave source"
    try:
        text = wave_md.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return "unreadable", str(exc)
    for line in text.splitlines():
        if line.lower().startswith("status:"):
            return line.split(":", 1)[1].strip().lower(), ""
    return "unsupported", "wave.md has no Status field"


def inventory_closed_waves(root: Path) -> tuple[dict[str, Any], ...]:
    """Return a deterministic local-only inventory; Git is never consulted."""

    waves_dir = _canonical_waves_dir(root)
    if waves_dir is None:
        return ()
    rows: list[dict[str, Any]] = []
    for wave_dir in sorted(
        (
            path
            for path in waves_dir.iterdir()
            if path.is_dir() and not path.is_symlink()
        ),
        key=lambda path: path.name,
    ):
        status, error = _wave_status(root, wave_dir)
        if status not in _CLOSED_STATES and status not in {"unreadable", "unsupported"}:
            continue
        rows.append(
            {
                "wave_id": wave_dir.name,
                "path": wave_dir,
                "status": status,
                "error": error,
                "fingerprint": source_fingerprint(root, wave_dir),
            }
        )
    return tuple(rows)


def source_fingerprint(root: Path, wave_dir: Path) -> str:
    """Hash only stable local backfill sources, in deterministic path order."""

    digest = hashlib.sha256()
    paths = [wave_dir / "wave.md", wave_dir / "events.jsonl"]
    paths.extend(
        path
        for path in sorted(wave_dir.glob("*.md"))
        if path.name != "wave.md"
    )
    for path in paths:
        digest.update(path.name.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        if not _contained_source_file(root, wave_dir, path):
            digest.update(b"<unsafe-or-missing-source>")
            digest.update(b"\0")
            continue
        try:
            digest.update(path.read_bytes())
        except OSError as exc:
            digest.update(f"<unreadable:{type(exc).__name__}>".encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def ensure_run(root: Path, entry_path: str = "manual") -> str:
    """Return the durable run for ``entry_path`` or create its first one."""

    entry = str(entry_path or "manual").strip() or "manual"
    if entry not in ENTRY_PATHS:
        raise ValueError(
            "entry_path must be one of " + ", ".join(sorted(ENTRY_PATHS))
        )
    conn = _connect(root)
    try:
        # Lifecycle entry points may race before any run exists.  Serialize the
        # active-run lookup and insert in SQLite itself; callers cannot rely on
        # the public MCP lock because setup/upgrade invoke this primitive
        # directly and may run in separate processes.
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT run_id FROM memory_backfill_runs "
            "WHERE entry_path=? ORDER BY created_at DESC LIMIT 1",
            (entry,),
        ).fetchone()
        if row:
            conn.execute("COMMIT")
            return str(row["run_id"])
        run_id = secrets.token_hex(16)
        now = _now()
        conn.execute(
            "INSERT INTO memory_backfill_runs"
            "(run_id,entry_path,state,created_at,updated_at) VALUES(?,?,?,?,?)",
            (run_id, entry, "inventory_pending", now, now),
        )
        conn.execute("COMMIT")
        return run_id
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def latest_run_id(root: Path, entry_path: str) -> str | None:
    """Return the newest run for an entry path, including terminal runs."""

    entry = str(entry_path or "").strip()
    if entry not in ENTRY_PATHS:
        raise ValueError(
            "entry_path must be one of " + ", ".join(sorted(ENTRY_PATHS))
        )
    conn = _connect(root)
    try:
        row = conn.execute(
            "SELECT run_id FROM memory_backfill_runs WHERE entry_path=? "
            "ORDER BY created_at DESC LIMIT 1",
            (entry,),
        ).fetchone()
        return str(row["run_id"]) if row is not None else None
    finally:
        conn.close()


def _inventory_digest(inventory: Iterable[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for item in inventory:
        for value in (
            str(item["wave_id"]),
            str(item["status"]),
            str(item["fingerprint"]),
        ):
            digest.update(value.encode("utf-8", errors="surrogateescape"))
            digest.update(b"\0")
    return digest.hexdigest()


def sync_inventory(
    root: Path,
    run_id: str,
    *,
    inventory: Iterable[dict[str, Any]] | None = None,
) -> dict[str, int]:
    inventory_rows = tuple(
        inventory_closed_waves(root) if inventory is None else inventory
    )
    conn = _connect(root)
    now = _now()
    try:
        conn.execute("BEGIN IMMEDIATE")
        run = conn.execute(
            "SELECT state FROM memory_backfill_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if run is None:
            raise ValueError(f"unknown memory backfill run {run_id}")
        inventory_changed = False
        for item in inventory_rows:
            wave_id = str(item["wave_id"])
            fingerprint = str(item["fingerprint"])
            prior = conn.execute(
                "SELECT source_fingerprint,state FROM memory_backfill_waves "
                "WHERE run_id=? AND wave_id=?",
                (run_id, wave_id),
            ).fetchone()
            if prior is None:
                inventory_changed = True
                state = (
                    "failed"
                    if item["status"] == "unreadable"
                    else ("unsupported" if item["status"] == "unsupported" else "pending")
                )
                conn.execute(
                    "INSERT INTO memory_backfill_waves"
                    "(run_id,wave_id,source_fingerprint,state,outcome,last_failure,updated_at) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (
                        run_id,
                        wave_id,
                        fingerprint,
                        state,
                        state if state in {"failed", "unsupported"} else "",
                        str(item["error"]),
                        now,
                    ),
                )
            elif str(prior["source_fingerprint"]) != fingerprint:
                inventory_changed = True
                conn.execute(
                    "UPDATE memory_backfill_waves SET source_fingerprint=?,state='pending',"
                    "claim_token='',outcome='',last_failure='',updated_at=? "
                    "WHERE run_id=? AND wave_id=?",
                    (fingerprint, now, run_id, wave_id),
                )
            elif str(prior["state"]) == "failed":
                # A new bounded call is the retry boundary. Preserve the last
                # failure for diagnosis while requeueing the wave; no elapsed
                # lease or PID authorizes recovery.
                conn.execute(
                    "UPDATE memory_backfill_waves SET state='pending',claim_token='',"
                    "updated_at=? WHERE run_id=? AND wave_id=?",
                    (now, run_id, wave_id),
                )
        if inventory_changed and str(run["state"]) in {"indexed", "publishing_index"}:
            conn.execute(
                "UPDATE memory_backfill_runs SET state='awaiting_validation',"
                "publication_attempt_id='',publication_generation=0,"
                "publication_inventory_digest='',updated_at=? WHERE run_id=?",
                (now, run_id),
            )
        conn.execute(
            "UPDATE memory_backfill_runs SET state='awaiting_validation',updated_at=? "
            "WHERE run_id=? AND state='inventory_pending'",
            (now, run_id),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return run_summary(root, run_id)


def claim_next(root: Path, run_id: str) -> dict[str, str] | None:
    """Claim the next deterministic wave. Caller already owns the OS lock."""

    conn = _connect(root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT wave_id,source_fingerprint FROM memory_backfill_waves "
            "WHERE run_id=? AND state IN ('pending','claimed') "
            "ORDER BY wave_id LIMIT 1",
            (run_id,),
        ).fetchone()
        if row is None:
            conn.execute("COMMIT")
            return None
        token = secrets.token_hex(16)
        conn.execute(
            "UPDATE memory_backfill_waves SET state='claimed',claim_token=?,updated_at=? "
            "WHERE run_id=? AND wave_id=?",
            (token, _now(), run_id, row["wave_id"]),
        )
        conn.execute("COMMIT")
        return {
            "wave_id": str(row["wave_id"]),
            "source_fingerprint": str(row["source_fingerprint"]),
            "claim_token": token,
        }
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def complete_claim(
    root: Path,
    run_id: str,
    wave_id: str,
    claim_token: str,
    *,
    outcome: str,
    candidate_count: int,
    source_records: Iterable[dict[str, Any]] = (),
    exhausted: bool,
) -> None:
    """Complete only the random token currently owning the short claim."""

    conn = _connect(root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        terminal_state = (
            outcome
            if exhausted and outcome in {"no_source", "unsupported"}
            else ("complete" if exhausted else "pending")
        )
        updated = conn.execute(
            "UPDATE memory_backfill_waves SET state=?,claim_token='',"
            "outcome=?,last_failure='',updated_at=? "
            "WHERE run_id=? AND wave_id=? AND claim_token=?",
            (
                terminal_state,
                outcome,
                _now(),
                run_id,
                wave_id,
                claim_token,
            ),
        ).rowcount
        if updated != 1:
            raise RuntimeError("backfill claim token no longer owns this wave")
        for source in source_records:
            source_event = str(source.get("source_event") or "")
            if not source_event:
                continue
            conn.execute(
                "INSERT INTO memory_backfill_sources(run_id,wave_id,source_event,memory_id) "
                "VALUES(?,?,?,?) ON CONFLICT(run_id,source_event) DO UPDATE SET "
                "memory_id=CASE WHEN memory_id='' THEN excluded.memory_id ELSE memory_id END",
                (run_id, wave_id, source_event, str(source.get("memory_id") or "")),
            )
        exact_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM memory_backfill_sources "
                "WHERE run_id=? AND wave_id=?",
                (run_id, wave_id),
            ).fetchone()[0]
        )
        conn.execute(
            "UPDATE memory_backfill_waves SET candidate_count=? "
            "WHERE run_id=? AND wave_id=?",
            (exact_count, run_id, wave_id),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def fail_claim(
    root: Path, run_id: str, wave_id: str, claim_token: str, message: str
) -> None:
    conn = _connect(root)
    try:
        conn.execute(
            "UPDATE memory_backfill_waves SET state='failed',claim_token='',"
            "outcome='failed',last_failure=?,updated_at=? "
            "WHERE run_id=? AND wave_id=? AND claim_token=?",
            (str(message), _now(), run_id, wave_id, claim_token),
        )
        conn.execute(
            "UPDATE memory_backfill_runs SET last_failure=?,updated_at=? WHERE run_id=?",
            (str(message), _now(), run_id),
        )
    finally:
        conn.close()


def _memory_outcomes(root: Path, run_id: str) -> dict[str, int]:
    """Count current dispositions for source events created by this run."""

    try:
        import memory_records

        records = memory_records.load_memory_records(root)
    except (ImportError, OSError):
        records = []
    statuses = {
        str(record.get("memory_id") or ""): (
            str(record.get("status") or ""),
            str(record.get("validation") or ""),
        )
        for record in records
        if record.get("memory_id")
    }
    conn = _connect(root)
    try:
        sources = conn.execute(
            "SELECT memory_id FROM memory_backfill_sources WHERE run_id=?", (run_id,)
        ).fetchall()
    finally:
        conn.close()
    result = {
        "candidates_pending": 0,
        "promoted": 0,
        "retained": 0,
        "rejected": 0,
        "rewritten": 0,
    }
    for row in sources:
        status, validation = statuses.get(str(row["memory_id"]), ("missing", "pending"))
        if validation == "pending" or status == "missing":
            result["candidates_pending"] += 1
        elif validation == "promote":
            result["promoted"] += 1
        elif validation == "retain":
            result["retained"] += 1
        elif validation == "reject":
            result["rejected"] += 1
        elif validation == "rewrite":
            result["rewritten"] += 1
        else:
            result["candidates_pending"] += 1
    return result


def validation_worklist(
    root: Path,
    run_id: str,
    *,
    limit: int = MAX_CANDIDATES_PER_CALL,
) -> dict[str, Any]:
    """Return the next deterministic, run-scoped pending validation page."""

    try:
        import memory_records

        records = {
            str(record.get("memory_id") or ""): record
            for record in memory_records.load_memory_records(root)
            if record.get("memory_id")
        }
    except (ImportError, OSError):
        records = {}
    conn = _connect(root)
    try:
        sources = conn.execute(
            "SELECT wave_id,source_event,memory_id FROM memory_backfill_sources "
            "WHERE run_id=? ORDER BY wave_id,source_event",
            (run_id,),
        ).fetchall()
    finally:
        conn.close()
    pending: list[dict[str, str]] = []
    for row in sources:
        source_event = str(row["source_event"])
        memory_id = str(row["memory_id"] or "")
        record = records.get(memory_id)
        if record is not None and str(record.get("validation") or "") != "pending":
            continue
        pending.append(
            {
                "wave_id": str(row["wave_id"]),
                "source_event": source_event,
                "memory_id": (
                    str(record.get("memory_id") or memory_id)
                    if record is not None
                    else memory_id
                ),
                "state": "pending" if record is not None else "missing",
            }
        )
    page_limit = max(1, min(int(limit), MAX_CANDIDATES_PER_CALL))
    page = pending[:page_limit]
    return {
        "validation_worklist": page,
        "validation_worklist_count": len(pending),
        "validation_worklist_remaining": max(0, len(pending) - len(page)),
    }


def run_summary(root: Path, run_id: str) -> dict[str, Any]:
    conn = _connect(root)
    try:
        run = conn.execute(
            "SELECT * FROM memory_backfill_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if run is None:
            raise ValueError(f"unknown memory backfill run {run_id}")
        grouped = {
            str(row["state"]): int(row["n"])
            for row in conn.execute(
                "SELECT state,COUNT(*) AS n FROM memory_backfill_waves "
                "WHERE run_id=? GROUP BY state",
                (run_id,),
            )
        }
        candidates = int(
            conn.execute(
                "SELECT COALESCE(SUM(candidate_count),0) FROM memory_backfill_waves "
                "WHERE run_id=?",
                (run_id,),
            ).fetchone()[0]
        )
    finally:
        conn.close()
    outcomes = _memory_outcomes(root, run_id)
    remaining_waves = grouped.get("pending", 0) + grouped.get("claimed", 0)
    failures = grouped.get("failed", 0)
    pending = remaining_waves + outcomes["candidates_pending"] + failures
    state = str(run["state"])
    if state not in {"indexed", "publishing_index"}:
        state = "ready_for_index" if pending == 0 else "awaiting_validation"
        conn = _connect(root)
        try:
            conn.execute(
                "UPDATE memory_backfill_runs SET state=?,updated_at=? WHERE run_id=?",
                (state, _now(), run_id),
            )
        finally:
            conn.close()
    return {
        "run_id": run_id,
        "entry_path": str(run["entry_path"]),
        "state": state,
        "eligible_waves": sum(grouped.values()),
        "remaining_waves": remaining_waves,
        "waves_complete": grouped.get("complete", 0),
        "waves_no_source": grouped.get("no_source", 0),
        "waves_unsupported": grouped.get("unsupported", 0),
        "failures": failures,
        "candidates_drafted": candidates,
        **outcomes,
        "last_failure": str(run["last_failure"]),
    }


@contextmanager
def index_publication_scope(run_id: str):
    """Bind one lifecycle-owned backfill run to the indexer's final CAS."""

    previous = os.environ.get(INDEX_PUBLICATION_RUN_ENV)
    os.environ[INDEX_PUBLICATION_RUN_ENV] = str(run_id)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(INDEX_PUBLICATION_RUN_ENV, None)
        else:
            os.environ[INDEX_PUBLICATION_RUN_ENV] = previous


def authorize_index_finalize(
    root: Path,
    run_id: str,
    attempt_id: str,
    expected_generation: int,
) -> bool:
    """Freeze the current zero-pending census immediately before epoch publish."""

    inventory = inventory_closed_waves(root)
    summary = sync_inventory(root, run_id, inventory=inventory)
    if summary["state"] != "ready_for_index":
        return False
    digest = _inventory_digest(inventory)
    conn = _connect(root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT state FROM memory_backfill_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if row is None or str(row["state"]) != "ready_for_index":
            conn.execute("ROLLBACK")
            return False
        conn.execute(
            "UPDATE memory_backfill_runs SET state='publishing_index',"
            "publication_attempt_id=?,publication_generation=?,"
            "publication_inventory_digest=?,last_failure='',updated_at=? "
            "WHERE run_id=?",
            (
                str(attempt_id),
                int(expected_generation),
                digest,
                _now(),
                run_id,
            ),
        )
        conn.execute("COMMIT")
        return True
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def run_state(root: Path, run_id: str) -> str | None:
    """Light state read for the finalize gate; ``None`` for an unknown run."""

    conn = _connect(root)
    try:
        row = conn.execute(
            "SELECT state FROM memory_backfill_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        return str(row["state"]) if row else None
    finally:
        conn.close()


def record_publication_success(root: Path, run_id: str, attempt_id: str) -> bool:
    """Mark the run indexed at CAS time, for the AUTHORIZED attempt only.

    The last-build row is legitimately overwritten by trailing passes
    (graph-only, FTS derived rebuild, optimize), so success is recorded at
    the one moment it is known with certainty — immediately after the epoch
    compare-and-set — instead of being re-derived later from that row.
    """

    conn = _connect(root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            "UPDATE memory_backfill_runs SET state='indexed',last_failure='',"
            "updated_at=? WHERE run_id=? AND state='publishing_index' "
            "AND publication_attempt_id=?",
            (_now(), run_id, str(attempt_id)),
        )
        conn.execute("COMMIT")
        return cur.rowcount == 1
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def reconcile_index_publication(root: Path, run_id: str) -> dict[str, Any]:
    """Recover a publication/checkpoint split without repeating the index pass."""

    summary = sync_inventory(root, run_id)
    if summary["state"] != "publishing_index":
        return summary
    conn = _connect(root)
    try:
        row = conn.execute(
            "SELECT publication_attempt_id,publication_generation,"
            "publication_inventory_digest FROM memory_backfill_runs WHERE run_id=?",
            (run_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValueError(f"unknown memory backfill run {run_id}")

    inventory = inventory_closed_waves(root)
    if _inventory_digest(inventory) != str(row["publication_inventory_digest"]):
        return sync_inventory(root, run_id, inventory=inventory)

    import index_state_store

    state = index_state_store.read_build_state(root / ".wavefoundry" / "index")
    published = bool(
        state
        and state.get("status") == "complete"
        and str(state.get("attempt_id") or "")
        == str(row["publication_attempt_id"])
        and int(state.get("generation") or 0)
        == int(row["publication_generation"])
    )
    conn = _connect(root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        if published:
            conn.execute(
                "UPDATE memory_backfill_runs SET state='indexed',last_failure='',"
                "updated_at=? WHERE run_id=? AND state='publishing_index'",
                (_now(), run_id),
            )
        else:
            conn.execute(
                "UPDATE memory_backfill_runs SET state='ready_for_index',"
                "publication_attempt_id='',publication_generation=0,"
                "publication_inventory_digest='',updated_at=? "
                "WHERE run_id=? AND state='publishing_index'",
                (_now(), run_id),
            )
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    result = run_summary(root, run_id)
    result["publication_recovered"] = published
    return result


def complete_index_publication(root: Path, run_id: str) -> None:
    summary = reconcile_index_publication(root, run_id)
    if summary["state"] != "indexed":
        raise RuntimeError(
            "index publication did not produce a recoverable completed epoch"
        )


def mark_indexed(root: Path, run_id: str) -> None:
    """Legacy direct checkpoint helper; lifecycle publication uses the epoch receipt."""

    summary = run_summary(root, run_id)
    if summary["state"] != "ready_for_index":
        raise RuntimeError("memory backfill remains awaiting validation")
    conn = _connect(root)
    try:
        conn.execute(
            "UPDATE memory_backfill_runs SET state='indexed',updated_at=? WHERE run_id=?",
            (_now(), run_id),
        )
    finally:
        conn.close()


def paused_run_for_source(root: Path, source_event: str) -> str | None:
    """Return the awaiting lifecycle run owning ``source_event``, if any."""

    if not source_event:
        return None
    conn = _connect(root)
    try:
        row = conn.execute(
            "SELECT s.run_id FROM memory_backfill_sources s "
            "JOIN memory_backfill_runs r ON r.run_id=s.run_id "
            "WHERE s.source_event=? AND r.state='awaiting_validation' "
            "ORDER BY r.created_at DESC LIMIT 1",
            (source_event,),
        ).fetchone()
        return str(row["run_id"]) if row else None
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    import repo_root

    parser = argparse.ArgumentParser(description="Historical Wavefoundry memory backfill")
    parser.add_argument("--root", default=None, help="Repository root (default: discovered from the script's install location, not cwd)")
    parser.add_argument("--entry-path", default="manual")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    root = repo_root.discover_root(args.root)
    run_id = ensure_run(root, args.entry_path)
    summary = sync_inventory(root, run_id)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return ACTION_REQUIRED_EXIT if summary["state"] == "awaiting_validation" else 0


if __name__ == "__main__":
    raise SystemExit(main())
