#!/usr/bin/env python3
"""Persist phase-aware context-efficiency accounting and wave checkpoints.

Eligible retrieval and lifecycle events write through to a host-local SQLite
ledger. Source versions are credited once per wave phase, request and response
tokens are always debited, and saved output/tool-loop residuals require a
quality-gated paired evaluation. Lifecycle, reload, and upgrade barriers project
pending durable generations into the marker-owned ``wave.md`` checkpoint.

Read helpers and ``ProcessTelemetry`` construction do not create files. The
store is created lazily by the first eligible event, focus transition, evaluation
registration, or explicit projection mutation.
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
import time
import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional


STORE_RELATIVE_PATH = Path(".wavefoundry/logs/context-efficiency.sqlite")
GENERAL_ASSOCIATION_NOTE = (
    "associated unattributed context at successful wave creation or "
    "preparation; may include exploration not exclusive to this wave."
)

LIFECYCLE_PROMPT_MAP: Mapping[str, Path] = {
    "wave_create_wave": Path("docs/prompts/create-wave.prompt.md"),
    "wave_prepare": Path("docs/prompts/prepare-wave.prompt.md"),
    "wave_implement": Path("docs/prompts/implement-wave.prompt.md"),
    "wave_review": Path("docs/prompts/review-wave.prompt.md"),
    "wave_close": Path("docs/prompts/close-wave.prompt.md"),
}

CONTEXT_EFFICIENCY_MARKER_BEGIN = (
    "<!-- wave:context-efficiency begin -->"
)
CONTEXT_EFFICIENCY_MARKER_END = "<!-- wave:context-efficiency end -->"
_CHECKPOINT_STATE_PREFIX = "<!-- wave:context-efficiency-state "
_CHECKPOINT_STATE_SUFFIX = " -->"

CONTEXT_EFFICIENCY_CARRIER_MARKER_BEGIN = (
    "<!-- wave:context-efficiency-carrier begin -->"
)
CONTEXT_EFFICIENCY_CARRIER_MARKER_END = (
    "<!-- wave:context-efficiency-carrier end -->"
)
_LEGACY_CONTEXT_EFFICIENCY_MARKERS = {
    "<!-- wavefoundry:context-efficiency begin -->": CONTEXT_EFFICIENCY_MARKER_BEGIN,
    "<!-- wavefoundry:context-efficiency end -->": CONTEXT_EFFICIENCY_MARKER_END,
    "<!-- wavefoundry:context-efficiency-state ": _CHECKPOINT_STATE_PREFIX,
    "<!-- wavefoundry:context-efficiency-carrier begin -->": (
        CONTEXT_EFFICIENCY_CARRIER_MARKER_BEGIN
    ),
    "<!-- wavefoundry:context-efficiency-carrier end -->": (
        CONTEXT_EFFICIENCY_CARRIER_MARKER_END
    ),
}
def estimate_tokens_utf8(value: str | bytes) -> int:
    """Return ``ceil(UTF-8 byte length / 4)``.

    Bytes are already an encoded representation and are counted directly.
    The integer expression avoids floating-point behavior for large values.
    """

    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    return estimate_tokens_from_byte_count(len(raw))


def estimate_tokens_from_byte_count(byte_count: int) -> int:
    """Return the estimator for an already-known non-negative byte size."""

    size = int(byte_count)
    if size < 0:
        raise ValueError("byte_count must be non-negative")
    return (size + 3) // 4


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def canonical_core_json(core_response: Any) -> str:
    """Encode a complete pre-telemetry response deterministically and compactly."""

    return json.dumps(
        core_response,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )


@dataclass(frozen=True)
class FileVersion:
    """A cheap per-path version signature already used by the serving path."""

    size: int
    mtime: float
    inode: int
    device: int

    @classmethod
    def from_stat(cls, stat_result: os.stat_result) -> "FileVersion":
        return cls(
            size=int(stat_result.st_size),
            mtime=float(stat_result.st_mtime),
            inode=int(stat_result.st_ino),
            device=int(stat_result.st_dev),
        )

    @classmethod
    def from_index_meta(cls, metadata: Mapping[str, Any]) -> "FileVersion":
        """Adapt one ``build_file_meta`` row without another filesystem stat.

        The index stores ``mtime`` (float seconds), ``size``, and ``inode``.
        Device is unavailable there and is represented by zero, which
        :func:`_file_version_matches` treats as a wildcard. Likewise inode
        zero is the existing Windows/FAT "unsupported" sentinel.
        """

        return cls(
            size=int(metadata["size"]),
            mtime=float(metadata["mtime"]),
            inode=int(metadata.get("inode", 0) or 0),
            device=0,
        )


@dataclass(frozen=True)
class SourceProof:
    """Same-version proof for one content-bearing response source.

    ``live`` callers capture ``before`` and ``after`` around the content read.
    ``indexed`` callers pass the indexed per-path signature and confirm that
    the captured completed epoch remained stable through the operation.
    ``stronger_same_version`` is only for an already-computed hash proof; this
    module never reads or hashes a whole file to manufacture one.
    """

    path: str | Path
    kind: str
    expected: Optional[FileVersion]
    content_bearing: bool = True
    boundary_stable: bool = False
    epoch_stable: bool = False
    stronger_same_version: bool = False
    credit_kind: str = "content"


def live_source_proof(
    path: str | Path,
    before: Optional[FileVersion],
    after: Optional[FileVersion],
    *,
    content_bearing: bool = True,
) -> SourceProof:
    """Build a live-read proof from a caller's read-bracketing signatures."""

    return SourceProof(
        path=path,
        kind="live",
        expected=after,
        content_bearing=content_bearing,
        boundary_stable=before is not None and before == after,
    )


def indexed_source_proof(
    path: str | Path,
    indexed_version: Optional[FileVersion],
    *,
    epoch_stable: bool,
    content_bearing: bool = True,
    stronger_same_version: bool = False,
) -> SourceProof:
    """Build an indexed proof without performing telemetry-only content I/O."""

    return SourceProof(
        path=path,
        kind="indexed",
        expected=indexed_version,
        content_bearing=content_bearing,
        epoch_stable=bool(epoch_stable),
        stronger_same_version=bool(stronger_same_version),
    )


def _file_version_matches(expected: FileVersion, current: FileVersion) -> bool:
    if expected.size != current.size or expected.mtime != current.mtime:
        return False
    if expected.inode and current.inode and expected.inode != current.inode:
        return False
    if expected.device and current.device and expected.device != current.device:
        return False
    return True


def contained_stat_signature(
    root: Path, path: str | Path
) -> Optional[FileVersion]:
    """Stat one contained regular file, returning ``None`` on uncertainty.

    This helper does not create files and never reads file contents.
    """

    try:
        resolved_root = Path(root).resolve(strict=True)
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = resolved_root / candidate
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(resolved_root) or not resolved.is_file():
            return None
        return FileVersion.from_stat(resolved.stat())
    except (OSError, RuntimeError, ValueError):
        return None



def _contained_prompt(root: Path, relative: Path) -> Optional[Path]:
    try:
        resolved_root = Path(root).resolve(strict=True)
        prompt = (resolved_root / relative).resolve(strict=True)
        if not prompt.is_relative_to(resolved_root) or not prompt.is_file():
            return None
        return prompt
    except (OSError, RuntimeError, ValueError):
        return None


@dataclass(frozen=True)
class FlushResult:
    success: bool
    persistence: str
    credited_keys: frozenset[tuple[str, str]] = frozenset()
    duplicate_keys: frozenset[tuple[str, str]] = frozenset()
    touched_waves: frozenset[str] = frozenset()
    error: Optional[str] = None


def store_path(root: Path) -> Path:
    return Path(root) / STORE_RELATIVE_PATH



def _open_read_store(root: Path) -> Optional[sqlite3.Connection]:
    path = store_path(root)
    if not path.is_file():
        return None
    try:
        conn = sqlite3.connect(
            f"file:{path.as_posix()}?mode=ro",
            uri=True,
            timeout=2.0,
        )
        conn.execute("PRAGMA busy_timeout=2000")
        return conn
    except sqlite3.Error:
        return None



def _canonicalize_context_efficiency_markers(markdown: str) -> str:
    """Map legacy owned-region markers to the one canonical ``wave:`` namespace."""

    for legacy, canonical in _LEGACY_CONTEXT_EFFICIENCY_MARKERS.items():
        markdown = markdown.replace(legacy, canonical)
    return markdown



def replace_carrier_block(markdown: str) -> str:
    """Replace or append the canonical Create-wave carrier region."""

    markdown = _canonicalize_context_efficiency_markers(markdown)
    begin_count = markdown.count(CONTEXT_EFFICIENCY_CARRIER_MARKER_BEGIN)
    end_count = markdown.count(CONTEXT_EFFICIENCY_CARRIER_MARKER_END)
    if begin_count != end_count or begin_count > 1:
        raise ValueError("malformed Context Efficiency carrier ownership")
    if begin_count == 0:
        separator = "" if not markdown or markdown.endswith("\n") else "\n"
        return (
            markdown
            + separator
            + "\n"
            + CONTEXT_EFFICIENCY_CARRIER_BLOCK
            + "\n"
        )
    begin = markdown.index(CONTEXT_EFFICIENCY_CARRIER_MARKER_BEGIN)
    end = markdown.index(CONTEXT_EFFICIENCY_CARRIER_MARKER_END, begin)
    end += len(CONTEXT_EFFICIENCY_CARRIER_MARKER_END)
    return markdown[:begin] + CONTEXT_EFFICIENCY_CARRIER_BLOCK + markdown[end:]


__all__ = [
    "CONTEXT_EFFICIENCY_CARRIER_BLOCK",
    "CONTEXT_EFFICIENCY_CARRIER_MARKER_BEGIN",
    "CONTEXT_EFFICIENCY_CARRIER_MARKER_END",
    "CONTEXT_EFFICIENCY_MARKER_BEGIN",
    "CONTEXT_EFFICIENCY_MARKER_END",
    "FileVersion",
    "FlushResult",
    "Focus",
    "GENERAL_ASSOCIATION_NOTE",
    "LIFECYCLE_PROMPT_MAP",
    "ProcessTelemetry",
    "RETRIEVAL_METHOD",
    "RETRIEVAL_METHOD_LABEL",
    "SourceMeasurement",
    "SourceProof",
    "WORKFLOW_PROXY_LIMITATION",
    "WORKFLOW_PROXY_METHOD",
    "WORKFLOW_PROXY_METHOD_LABEL",
    "canonical_core_json",
    "checkpoint_validation_errors",
    "contained_stat_signature",
    "empty_checkpoint",
    "estimate_tokens_utf8",
    "estimate_tokens_from_byte_count",
    "indexed_source_proof",
    "live_source_proof",
    "mark_checkpoint_published",
    "measure_source_proofs",
    "parse_checkpoint_block",
    "read_general_totals",
    "read_store_health",
    "read_wave_snapshot",
    "render_checkpoint_block",
    "replace_carrier_block",
    "replace_checkpoint_block",
    "retrieval_context_avoided",
    "store_path",
    "workflow_instruction_proxy",
    "workflow_proxy_after_flush",
]

__all__.extend(
    [
        "attach_evaluation",
        "gap_path",
        "pending_wave_ids",
        "poison_accounting_gap",
        "reconcile_checkpoint_authority",
    ]
)


# ---------------------------------------------------------------------------
# Write-through, phase-aware accounting
# ---------------------------------------------------------------------------

STORE_SCHEMA_VERSION = 1
GAP_RELATIVE_PATH = Path(".wavefoundry/logs/context-efficiency.gap")
MAX_PHASE_SOURCE_CREDITS = 100_000
_PRE_RELEASE_TABLES = frozenset(
    {
        "aggregate",
        "retrieval_aggregate",
        "lifecycle_credit",
        "lifecycle_event",
        "general_aggregate",
    }
)

RETRIEVAL_METHOD = "utf8_bytes_div_4_phase_source_ledger"
RETRIEVAL_METHOD_LABEL = (
    "estimated token savings — gross contained source-file baseline minus "
    "the canonical request and complete response, with each source version "
    "credited once per wave phase."
)
WORKFLOW_PROXY_METHOD = "utf8_bytes_div_4_workflow_closed_ledger"
WORKFLOW_PROXY_METHOD_LABEL = (
    "estimated workflow contribution — one mapped project prompt gross credit "
    "minus the canonical request and complete response."
)
WORKFLOW_PROXY_LIMITATION = (
    "Instruction-surface estimate only; saved model output and avoided tool "
    "loops require a quality-equivalent paired evaluation."
)
CONTEXT_EFFICIENCY_CARRIER_BLOCK = f"""\
{CONTEXT_EFFICIENCY_CARRIER_MARKER_BEGIN}
### Context-efficiency checkpoint

New wave records reserve one marker-owned `## Context Efficiency` snapshot.
It shows one conservative per-stage estimated-token-savings total. Runtime
telemetry is written through to the host-local SQLite authority; lifecycle,
reload, and upgrade boundaries project durable totals into `wave.md`.
Gross source and workflow-prompt credits are reduced by every recorded request
and complete response. Saved output or avoided tool loops count only through a
quality-equivalent paired evaluation. Runtime lifecycle tools own projection;
manual/non-MCP creation may omit the snapshot until a projection boundary.
{CONTEXT_EFFICIENCY_CARRIER_MARKER_END}"""


@dataclass(frozen=True)
class SourceCreditCandidate:
    source_id: str
    version_id: str
    tokens: int
    classification: str
    credit_kind: str


@dataclass(frozen=True)
class SourceMeasurement:
    estimated_source_tokens: int
    source_files_verified: int
    source_files_estimated: int
    candidates: tuple[SourceCreditCandidate, ...] = ()

    @property
    def source_files_counted(self) -> int:
        return self.source_files_verified + self.source_files_estimated


def _opaque_source_id(root: Path, resolved: Path) -> str:
    relative = resolved.relative_to(root).as_posix()
    return hashlib.sha256(relative.encode("utf-8")).hexdigest()


def _opaque_version_id(version: FileVersion, stronger: bool) -> str:
    payload = {
        "inode": int(version.inode),
        "mtime_ns": int(round(float(version.mtime) * 1_000_000_000)),
        "size": int(version.size),
        "stronger_same_version": bool(stronger),
    }
    return hashlib.sha256(canonical_core_json(payload).encode("utf-8")).hexdigest()


def measure_source_proofs(
    root: Path, proofs: Iterable[SourceProof]
) -> SourceMeasurement:
    """Measure distinct contained sources and return opaque credit candidates."""

    resolved_root = Path(root).resolve()
    grouped: dict[str, list[SourceProof]] = {}
    for proof in proofs:
        if not proof.content_bearing:
            continue
        candidate = Path(proof.path)
        if not candidate.is_absolute():
            candidate = resolved_root / candidate
        try:
            resolved = candidate.resolve(strict=False)
        except (OSError, RuntimeError):
            continue
        if not resolved.is_relative_to(resolved_root):
            continue
        grouped.setdefault(resolved.as_posix(), []).append(proof)

    credits: list[SourceCreditCandidate] = []
    verified = 0
    estimated = 0
    for key, candidates in grouped.items():
        resolved = Path(key)
        current = contained_stat_signature(resolved_root, resolved)
        selected: FileVersion | None = current
        classification = "estimated"
        stronger = False
        if current is not None:
            for proof in candidates:
                signature_matches = proof.expected is not None and _file_version_matches(
                    proof.expected, current
                )
                stable = (
                    proof.kind == "live"
                    and proof.boundary_stable
                    and signature_matches
                ) or (
                    proof.kind == "indexed"
                    and proof.epoch_stable
                    and (signature_matches or proof.stronger_same_version)
                )
                if stable:
                    classification = "verified"
                    stronger = proof.stronger_same_version
                    break
        else:
            selected = next(
                (proof.expected for proof in candidates if proof.expected is not None),
                None,
            )
        if selected is None:
            continue
        kind = (
            "structural"
            if any(proof.credit_kind == "structural" for proof in candidates)
            else "content"
        )
        token_count = estimate_tokens_from_byte_count(selected.size)
        credits.append(
            SourceCreditCandidate(
                source_id=_opaque_source_id(resolved_root, resolved),
                version_id=_opaque_version_id(selected, stronger),
                tokens=token_count,
                classification=classification,
                credit_kind=kind,
            )
        )
        if classification == "verified":
            verified += 1
        else:
            estimated += 1
    return SourceMeasurement(
        sum(candidate.tokens for candidate in credits),
        verified,
        estimated,
        tuple(credits),
    )


def retrieval_context_avoided(
    core_response: Any,
    root: Path,
    proofs: Iterable[SourceProof],
    *,
    request_arguments: Any = None,
) -> dict[str, Any]:
    """Build a write-through ledger candidate from one public response."""

    try:
        returned = estimate_tokens_utf8(canonical_core_json(core_response))
        requested = estimate_tokens_utf8(
            canonical_core_json({} if request_arguments is None else request_arguments)
        )
    except Exception:
        return {
            "estimated_request_tokens": 0,
            "estimated_returned_tokens": 0,
            "estimated_source_tokens": 0,
            "estimated_avoided_tokens": 0,
            "source_files_counted": 0,
            "source_files_verified": 0,
            "source_files_estimated": 0,
            "captured": False,
            "persistence": "failed",
            "method": RETRIEVAL_METHOD,
        }
    sources = measure_source_proofs(root, proofs)
    return {
        "estimated_request_tokens": requested,
        "estimated_returned_tokens": returned,
        "estimated_source_tokens": sources.estimated_source_tokens,
        "estimated_avoided_tokens": max(
            0, sources.estimated_source_tokens - requested - returned
        ),
        "source_files_counted": sources.source_files_counted,
        "source_files_verified": sources.source_files_verified,
        "source_files_estimated": sources.source_files_estimated,
        "captured": True,
        "persistence": "pending",
        "method": RETRIEVAL_METHOD,
        "_source_credits": [asdict(candidate) for candidate in sources.candidates],
    }


def workflow_instruction_proxy(
    core_response: Any,
    root: Path,
    tool_name: str,
    *,
    request_arguments: Any = None,
    milestone_completed: bool = True,
) -> dict[str, Any]:
    """Build one workflow ledger candidate; no-op calls retain both debits."""

    try:
        returned = estimate_tokens_utf8(canonical_core_json(core_response))
        requested = estimate_tokens_utf8(
            canonical_core_json({} if request_arguments is None else request_arguments)
        )
    except Exception:
        return {
            "estimated_request_tokens": 0,
            "estimated_returned_tokens": 0,
            "prompt_surface_tokens": 0,
            "estimated_compaction_tokens": 0,
            "credited": False,
            "captured": False,
            "persistence": "failed",
            "method": WORKFLOW_PROXY_METHOD,
            "limitation": WORKFLOW_PROXY_LIMITATION,
        }
    prompt_tokens = 0
    if milestone_completed:
        relative = LIFECYCLE_PROMPT_MAP.get(tool_name)
        prompt = _contained_prompt(root, relative) if relative is not None else None
        if prompt is not None:
            try:
                prompt_tokens = estimate_tokens_utf8(prompt.read_bytes())
            except OSError:
                prompt_tokens = 0
    return {
        "estimated_request_tokens": requested,
        "estimated_returned_tokens": returned,
        "prompt_surface_tokens": prompt_tokens,
        "estimated_compaction_tokens": max(
            0, prompt_tokens - requested - returned
        ),
        "credited": False,
        "captured": True,
        "persistence": "pending",
        "method": WORKFLOW_PROXY_METHOD,
        "limitation": WORKFLOW_PROXY_LIMITATION,
    }


@dataclass(frozen=True)
class Focus:
    wave_id: Optional[str] = None
    stage: Optional[str] = None
    phase_id: Optional[str] = None
    paused_stage: Optional[str] = None
    paused_phase_id: Optional[str] = None


def gap_path(root: Path) -> Path:
    return Path(root) / GAP_RELATIVE_PATH


def _write_gap_sentinel(root: Path) -> bool:
    """Durably poison positive publication without retaining call content."""

    path = gap_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return True
    except OSError:
        return False


def poison_accounting_gap(root: Path) -> bool:
    """Persist the fail-closed barrier when telemetry cannot reach its event commit."""

    return _write_gap_sentinel(root)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        is not None
    )


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(conn, table):
        return set()
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _open_write_store(root: Path) -> sqlite3.Connection:
    """Open the current store with bounded contention recovery."""

    last_error: Exception | None = None
    for delay in (0.0, 0.01, 0.025, 0.05, 0.1, 0.2):
        if delay:
            time.sleep(delay)
        try:
            return _open_write_store_once(root)
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            last_error = exc
    assert last_error is not None
    raise last_error


def _open_write_store_once(root: Path) -> sqlite3.Connection:
    path = store_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=0.05)
    conn.execute("PRAGMA busy_timeout=50")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    user_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    existing_tables = {
        str(row[0])
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    }
    if existing_tables & _PRE_RELEASE_TABLES:
        # No released target consumed the experimental telemetry stores.
        # A recognized pre-release table makes the dedicated sidecar
        # non-authoritative: reset it in place instead of carrying payloads
        # into the first shipped schema under an ambiguous version number.
        conn.execute("BEGIN IMMEDIATE")
        try:
            for table in sorted(existing_tables):
                conn.execute(f'DROP TABLE "{table.replace(chr(34), chr(34) * 2)}"')
            conn.execute("PRAGMA user_version=0")
            conn.commit()
            user_version = 0
        except Exception:
            conn.rollback()
            conn.close()
            raise
    schema_ready = user_version == STORE_SCHEMA_VERSION and {
        "meta",
        "phase_state",
        "telemetry_event",
        "source_credit",
        "wave_state",
        "evaluation_scope",
        "evaluation_attachment",
    }.issubset(
        {
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    )
    if schema_ready:
        schema_ready = "source_credits_dropped" in _column_names(
            conn, "telemetry_event"
        )
    if schema_ready:
        if gap_path(root).exists():
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO meta(key,value)"
                    " VALUES('accounting_gap','1')"
                )
                conn.commit()
            except Exception:
                conn.rollback()
                conn.close()
                raise
        return conn
    if user_version not in {0, STORE_SCHEMA_VERSION}:
        conn.close()
        raise sqlite3.DatabaseError("unsupported context-efficiency schema")
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS meta "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        version_row = conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        if version_row is not None and str(version_row[0]) != str(
            STORE_SCHEMA_VERSION
        ):
            raise sqlite3.DatabaseError("unsupported context-efficiency schema")
        conn.execute(
            "INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)",
            (str(STORE_SCHEMA_VERSION),),
        )
        instance = conn.execute(
            "SELECT value FROM meta WHERE key='store_instance_id'"
        ).fetchone()
        if instance is None:
            conn.execute(
                "INSERT INTO meta(key,value) VALUES('store_instance_id',?)",
                (uuid.uuid4().hex,),
            )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS phase_state("
            "wave_id TEXT NOT NULL, phase_id TEXT NOT NULL, stage TEXT NOT NULL,"
            "ordinal INTEGER NOT NULL, created_at REAL NOT NULL,"
            "PRIMARY KEY(wave_id,phase_id), UNIQUE(wave_id,ordinal))"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS telemetry_event("
            "event_id TEXT PRIMARY KEY, producer_id TEXT NOT NULL,"
            "wave_id TEXT, phase_id TEXT NOT NULL, stage TEXT NOT NULL,"
            "tool_name TEXT NOT NULL, event_kind TEXT NOT NULL,"
            "request_tokens INTEGER NOT NULL, response_tokens INTEGER NOT NULL,"
            "workflow_prompt_tokens INTEGER NOT NULL DEFAULT 0,"
            "source_credits_dropped INTEGER NOT NULL DEFAULT 0,"
            "created_at REAL NOT NULL)"
        )
        event_columns = _column_names(conn, "telemetry_event")
        if "source_credits_dropped" not in event_columns:
            conn.execute(
                "ALTER TABLE telemetry_event ADD COLUMN "
                "source_credits_dropped INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS telemetry_event_wave_stage "
            "ON telemetry_event(wave_id,stage)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS source_credit("
            "wave_key TEXT NOT NULL, phase_id TEXT NOT NULL, stage TEXT NOT NULL,"
            "source_id TEXT NOT NULL, version_id TEXT NOT NULL,"
            "tokens INTEGER NOT NULL, credit_kind TEXT NOT NULL,"
            "provenance TEXT NOT NULL,"
            "PRIMARY KEY(wave_key,phase_id,source_id,version_id))"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS wave_state("
            "wave_id TEXT PRIMARY KEY, generation INTEGER NOT NULL DEFAULT 0,"
            "pending INTEGER NOT NULL DEFAULT 0, published_json TEXT,"
            "store_instance_id TEXT, measurement_status TEXT NOT NULL DEFAULT 'healthy')"
        )
        columns = _column_names(conn, "wave_state")
        if "store_instance_id" not in columns:
            conn.execute("ALTER TABLE wave_state ADD COLUMN store_instance_id TEXT")
        if "measurement_status" not in columns:
            conn.execute(
                "ALTER TABLE wave_state ADD COLUMN measurement_status TEXT"
                " NOT NULL DEFAULT 'healthy'"
            )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS evaluation_scope("
            "wave_id TEXT NOT NULL, phase_id TEXT NOT NULL, stage TEXT NOT NULL,"
            "scope_digest TEXT NOT NULL, applicability_json TEXT NOT NULL,"
            "created_at REAL NOT NULL, PRIMARY KEY(wave_id,phase_id))"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS evaluation_attachment("
            "evaluation_id TEXT PRIMARY KEY, wave_id TEXT NOT NULL,"
            "phase_id TEXT NOT NULL, stage TEXT NOT NULL,"
            "scope_digest TEXT NOT NULL, residual INTEGER NOT NULL,"
            "active INTEGER NOT NULL, supersedes_evaluation_id TEXT,"
            "report_digest TEXT NOT NULL, created_at REAL NOT NULL)"
        )
        if gap_path(root).exists():
            conn.execute(
                "INSERT OR REPLACE INTO meta(key,value)"
                " VALUES('accounting_gap','1')"
            )
        conn.execute(f"PRAGMA user_version={STORE_SCHEMA_VERSION}")
        conn.commit()
        return conn
    except Exception:
        conn.rollback()
        conn.close()
        raise


def _store_instance_id(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT value FROM meta WHERE key='store_instance_id'"
    ).fetchone()
    return str(row[0]) if row else ""


def _accounting_gap(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT value FROM meta WHERE key='accounting_gap'"
    ).fetchone()
    return row is not None and str(row[0]) == "1"


def _mint_phase(
    conn: sqlite3.Connection, wave_id: str, stage: str
) -> str:
    ordinal = int(
        conn.execute(
            "SELECT COALESCE(MAX(ordinal),0)+1 FROM phase_state WHERE wave_id=?",
            (wave_id,),
        ).fetchone()[0]
    )
    phase_id = f"{stage}-{ordinal}"
    conn.execute(
        "INSERT INTO phase_state(wave_id,phase_id,stage,ordinal,created_at)"
        " VALUES(?,?,?,?,?)",
        (wave_id, phase_id, stage, ordinal, time.time()),
    )
    return phase_id


def _touch_wave(conn: sqlite3.Connection, wave_id: str) -> None:
    conn.execute(
        "INSERT INTO wave_state("
        "wave_id,generation,pending,published_json,store_instance_id,measurement_status"
        ") VALUES(?,1,1,NULL,?,'healthy') "
        "ON CONFLICT(wave_id) DO UPDATE SET "
        "generation=generation+1,pending=1",
        (wave_id, _store_instance_id(conn)),
    )


def _public_metric(metric: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metric.items() if not key.startswith("_")}


def _commit_event(
    root: Path,
    producer_id: str,
    focus: Focus,
    tool_name: str,
    event_kind: str,
    metric: Mapping[str, Any],
    *,
    event_id: str,
) -> tuple[str, int, int, int]:
    conn: sqlite3.Connection | None = None
    try:
        conn = _open_write_store(root)
        conn.execute("BEGIN IMMEDIATE")
        if _accounting_gap(conn):
            conn.rollback()
            return "poisoned", 0, 0, 0
        wave_id = focus.wave_id
        stage = focus.stage or "general"
        phase_id = focus.phase_id or f"general:{producer_id}"
        inserted = conn.execute(
            "INSERT OR IGNORE INTO telemetry_event("
            "event_id,producer_id,wave_id,phase_id,stage,tool_name,event_kind,"
            "request_tokens,response_tokens,workflow_prompt_tokens,created_at"
            ") VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                event_id,
                producer_id,
                wave_id,
                phase_id,
                stage,
                tool_name,
                event_kind,
                int(metric.get("estimated_request_tokens", 0)),
                int(metric.get("estimated_returned_tokens", 0)),
                int(metric.get("prompt_surface_tokens", 0)),
                time.time(),
            ),
        ).rowcount
        credited_tokens = 0
        credited_files = 0
        dropped_credits = 0
        if inserted:
            wave_key = wave_id or f"general:{producer_id}"
            current_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM source_credit"
                    " WHERE wave_key=? AND phase_id=?",
                    (wave_key, phase_id),
                ).fetchone()[0]
            )
            for raw in metric.get("_source_credits", ()):
                if not isinstance(raw, Mapping):
                    continue
                source_id = str(raw.get("source_id", ""))
                version_id = str(raw.get("version_id", ""))
                kind = (
                    "structural"
                    if str(raw.get("credit_kind")) == "structural"
                    else "content"
                )
                if current_count >= MAX_PHASE_SOURCE_CREDITS:
                    existing_credit = conn.execute(
                        "SELECT provenance FROM source_credit WHERE wave_key=? "
                        "AND phase_id=? AND source_id=? AND version_id=?",
                        (wave_key, phase_id, source_id, version_id),
                    ).fetchone()
                    if existing_credit is None:
                        dropped_credits += 1
                    elif str(existing_credit[0]) != kind:
                        conn.execute(
                            "UPDATE source_credit SET provenance='both' "
                            "WHERE wave_key=? AND phase_id=? AND source_id=? "
                            "AND version_id=?",
                            (wave_key, phase_id, source_id, version_id),
                        )
                    continue
                was_inserted = conn.execute(
                    "INSERT OR IGNORE INTO source_credit("
                    "wave_key,phase_id,stage,source_id,version_id,tokens,"
                    "credit_kind,provenance) VALUES(?,?,?,?,?,?,?,?)",
                    (
                        wave_key,
                        phase_id,
                        stage,
                        source_id,
                        version_id,
                        max(0, int(raw.get("tokens", 0))),
                        kind,
                        kind,
                    ),
                ).rowcount
                if was_inserted:
                    credited_tokens += max(0, int(raw.get("tokens", 0)))
                    credited_files += 1
                    current_count += 1
                else:
                    conn.execute(
                        "UPDATE source_credit SET provenance='both' "
                        "WHERE wave_key=? AND phase_id=? AND source_id=?"
                        " AND version_id=? AND provenance<>?",
                        (
                            wave_key,
                            phase_id,
                            source_id,
                            version_id,
                            kind,
                        ),
                    )
            if dropped_credits:
                conn.execute(
                    "UPDATE telemetry_event SET source_credits_dropped=? "
                    "WHERE event_id=?",
                    (dropped_credits, event_id),
                )
            if wave_id:
                _touch_wave(conn, wave_id)
        conn.commit()
        return (
            "durable" if inserted else "duplicate",
            credited_tokens,
            credited_files,
            dropped_credits,
        )
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
        return (
            "poisoned" if _write_gap_sentinel(root) else "failed",
            0,
            0,
            0,
        )
    finally:
        if conn is not None:
            conn.close()


class ProcessTelemetry:
    """Process focus plus write-through durable telemetry."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root).resolve() if root is not None else None
        self.producer_id = secrets.token_hex(16)
        self._lock = threading.RLock()
        self._focus = Focus()
        # Compatibility-only buffers for direct unit callers that do not bind a
        # root. The production ImplHandler always binds one.
        self._compat_retrieval: list[dict[str, Any]] = []
        self._compat_workflow: list[tuple[str, str, str, dict[str, Any]]] = []

    @property
    def focus(self) -> Focus:
        with self._lock:
            return self._focus

    def set_focus(
        self, wave_id: str, stage: str, *, new_phase: bool = False
    ) -> None:
        with self._lock:
            previous = self._focus
            phase_id = previous.phase_id
            if (
                self.root is not None
                and (
                    new_phase
                    or previous.wave_id != str(wave_id)
                    or previous.stage != str(stage)
                    or phase_id is None
                )
            ):
                conn = _open_write_store(self.root)
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    phase_id = _mint_phase(conn, str(wave_id), str(stage))
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()
            elif phase_id is None:
                phase_id = f"{stage}-1"
            self._focus = Focus(str(wave_id), str(stage), phase_id)

    def pause_focus(self) -> None:
        with self._lock:
            if self._focus.wave_id and self._focus.stage != "paused":
                self._focus = Focus(
                    self._focus.wave_id,
                    "paused",
                    self._focus.phase_id,
                    self._focus.stage,
                    self._focus.phase_id,
                )

    def reopen_focus(self) -> None:
        with self._lock:
            if self._focus.wave_id and self._focus.paused_stage:
                self._focus = Focus(
                    self._focus.wave_id,
                    self._focus.paused_stage,
                    self._focus.paused_phase_id,
                )

    def record_retrieval(
        self,
        metric: Mapping[str, Any],
        *,
        tool_name: str = "retrieval",
        event_id: str | None = None,
    ) -> dict[str, Any]:
        payload = dict(metric)
        if not payload.get("captured"):
            return _public_metric(payload)
        if self.root is None:
            self._compat_retrieval.append(payload)
            public = _public_metric(payload)
            public["persistence"] = "buffered"
            return public
        with self._lock:
            status, credited_tokens, credited_files, dropped_credits = _commit_event(
                self.root,
                self.producer_id,
                self._focus,
                tool_name,
                "retrieval",
                payload,
                event_id=str(event_id or uuid.uuid4().hex),
            )
        public = _public_metric(payload)
        public["persistence"] = status
        public["captured"] = status in {"durable", "duplicate"}
        public["estimated_source_tokens"] = credited_tokens
        public["source_files_credited"] = credited_files
        public["source_credits_dropped"] = dropped_credits
        public["estimated_avoided_tokens"] = max(
            0,
            credited_tokens
            - int(public.get("estimated_request_tokens", 0))
            - int(public.get("estimated_returned_tokens", 0)),
        )
        if status == "failed":
            public["fatal_persistence_failure"] = True
        return public

    def record_workflow(
        self,
        wave_id: str,
        stage: str,
        tool_name: str,
        metric: Mapping[str, Any],
        *,
        invocation_id: Optional[str] = None,
    ) -> dict[str, Any]:
        payload = dict(metric)
        if not payload.get("captured"):
            return _public_metric(payload)
        event_id = str(invocation_id or uuid.uuid4().hex)
        if self.root is None:
            self._compat_workflow.append(
                (str(wave_id), str(stage), tool_name, payload)
            )
            public = _public_metric(payload)
            public.update(persistence="buffered", invocation_id=event_id)
            return public
        with self._lock:
            focus = self._focus
            if focus.wave_id != str(wave_id) or focus.stage != str(stage):
                phase_id = focus.phase_id or f"{stage}-1"
                focus = Focus(str(wave_id), str(stage), phase_id)
            status, _tokens, _files, _dropped = _commit_event(
                self.root,
                self.producer_id,
                focus,
                tool_name,
                "workflow",
                payload,
                event_id=event_id,
            )
        public = _public_metric(payload)
        public.update(
            persistence=status,
            credited=(
                status == "durable"
                and int(payload.get("prompt_surface_tokens", 0)) > 0
            ),
            invocation_id=event_id,
            captured=status in {"durable", "duplicate"},
        )
        if status == "failed":
            public["fatal_persistence_failure"] = True
        return public

    def buffered_snapshot(self) -> dict[str, Any]:
        return {
            "producer_id": self.producer_id,
            "focus": asdict(self.focus),
            "write_through": self.root is not None,
            "pending_events": len(self._compat_retrieval)
            + len(self._compat_workflow),
            "general_note": GENERAL_ASSOCIATION_NOTE,
        }

    def flush(
        self,
        root: Path,
        *,
        transfer_general_to: Optional[str] = None,
        checkpoint_floors: Optional[Mapping[str, Mapping[str, Any]]] = None,
    ) -> FlushResult:
        """Compatibility boundary for buffered tests and general-state transfer."""

        if self.root is None:
            self.root = Path(root).resolve()
            # Preserve old direct-test behavior by committing buffered candidates.
            for metric in list(self._compat_retrieval):
                self.record_retrieval(metric)
            self._compat_retrieval.clear()
            for wave_id, stage, tool_name, metric in list(self._compat_workflow):
                self.record_workflow(wave_id, stage, tool_name, metric)
            self._compat_workflow.clear()
        touched: set[str] = set()
        try:
            if transfer_general_to:
                conn = _open_write_store(self.root)
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    target = str(transfer_general_to)
                    general_key = f"general:{self.producer_id}"
                    conn.execute(
                        "INSERT OR IGNORE INTO source_credit("
                        "wave_key,phase_id,stage,source_id,version_id,tokens,"
                        "credit_kind,provenance) "
                        "SELECT ?,'pre-wave','pre-wave',source_id,version_id,"
                        "tokens,credit_kind,provenance FROM source_credit "
                        "WHERE wave_key=?",
                        (target, general_key),
                    )
                    conn.execute(
                        "DELETE FROM source_credit WHERE wave_key=?",
                        (general_key,),
                    )
                    moved = conn.execute(
                        "UPDATE telemetry_event SET wave_id=?,phase_id='pre-wave',"
                        "stage='pre-wave' WHERE wave_id IS NULL AND producer_id=?",
                        (target, self.producer_id),
                    ).rowcount
                    if moved:
                        _touch_wave(conn, target)
                        touched.add(target)
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()
            return FlushResult(
                True, "durable", touched_waves=frozenset(touched)
            )
        except Exception as exc:
            poisoned = _write_gap_sentinel(Path(root))
            return FlushResult(
                False,
                "poisoned" if poisoned else "failed",
                error=f"{type(exc).__name__}: {exc}",
            )


def read_store_health(root: Path) -> dict[str, Optional[str]]:
    path = store_path(root)
    if gap_path(root).exists():
        return {
            "status": "accounting_gap",
            "diagnostic": "positive projection suppressed by durable accounting gap",
        }
    if not path.exists():
        return {"status": "absent", "diagnostic": None}
    if not path.is_file():
        return {
            "status": "failed",
            "diagnostic": "context-efficiency store path is not a file",
        }
    conn: sqlite3.Connection | None = None
    try:
        conn = _open_read_store(root)
        if conn is None:
            raise sqlite3.DatabaseError("store is unreadable")
        version = conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        if version is None or str(version[0]) != str(STORE_SCHEMA_VERSION):
            raise sqlite3.DatabaseError("unsupported schema")
        conn.execute("SELECT 1 FROM telemetry_event LIMIT 1")
        conn.execute("SELECT 1 FROM source_credit LIMIT 1")
        if _accounting_gap(conn):
            return {
                "status": "accounting_gap",
                "diagnostic": "positive projection suppressed by durable accounting gap",
            }
        return {"status": "healthy", "diagnostic": None}
    except sqlite3.Error as exc:
        return {
            "status": "failed",
            "diagnostic": f"context-efficiency store is unreadable: {type(exc).__name__}: {exc}",
        }
    finally:
        if conn is not None:
            conn.close()


_STAGE_KEYS = (
    "calls",
    "content_source_credit",
    "structural_source_credit",
    "workflow_prompt_credit",
    "request_debit",
    "response_debit",
    "matched_pair_residual",
    "paired_evaluation_count",
    "direct_net",
    "estimated_tokens_saved",
    "source_credit_count",
    "source_credit_drop_count",
)


def _empty_stage_totals() -> dict[str, int]:
    return {key: 0 for key in _STAGE_KEYS}


def empty_checkpoint(wave_id: str = "") -> dict[str, Any]:
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "wave_id": str(wave_id),
        "generation": 0,
        "pending": False,
        "store_instance_id": "",
        "measurement_status": "unmeasured",
        "stages": {},
        "totals": _empty_stage_totals(),
    }


def _snapshot_from_conn(
    conn: sqlite3.Connection, wave_id: str
) -> dict[str, Any]:
    snapshot = empty_checkpoint(wave_id)
    snapshot["store_instance_id"] = _store_instance_id(conn)
    state = conn.execute(
        "SELECT generation,pending,measurement_status FROM wave_state"
        " WHERE wave_id=?",
        (wave_id,),
    ).fetchone()
    if state:
        snapshot["generation"] = int(state[0])
        snapshot["pending"] = bool(state[1])
        snapshot["measurement_status"] = str(state[2] or "healthy")
    if _accounting_gap(conn):
        snapshot["measurement_status"] = "accounting_gap"
    elif not state:
        snapshot["measurement_status"] = "healthy"
    stages: set[str] = {
        str(row[0])
        for row in conn.execute(
            "SELECT DISTINCT stage FROM telemetry_event WHERE wave_id=?",
            (wave_id,),
        )
    }
    stages.update(
        str(row[0])
        for row in conn.execute(
            "SELECT DISTINCT stage FROM source_credit WHERE wave_key=?",
            (wave_id,),
        )
    )
    stages.update(
        str(row[0])
        for row in conn.execute(
            "SELECT DISTINCT stage FROM evaluation_attachment "
            "WHERE wave_id=? AND active=1",
            (wave_id,),
        )
    )
    for stage_name in sorted(stages):
        values = _empty_stage_totals()
        event_row = conn.execute(
            "SELECT COUNT(*),COALESCE(SUM(request_tokens),0),"
            "COALESCE(SUM(response_tokens),0),"
            "COALESCE(SUM(workflow_prompt_tokens),0),"
            "COALESCE(SUM(source_credits_dropped),0) "
            "FROM telemetry_event WHERE wave_id=? AND stage=?",
            (wave_id, stage_name),
        ).fetchone()
        values["calls"] = int(event_row[0])
        values["request_debit"] = int(event_row[1])
        values["response_debit"] = int(event_row[2])
        values["workflow_prompt_credit"] = int(event_row[3])
        values["source_credit_drop_count"] = int(event_row[4])
        for kind, token_sum, count in conn.execute(
            "SELECT credit_kind,COALESCE(SUM(tokens),0),COUNT(*)"
            " FROM source_credit WHERE wave_key=? AND stage=? GROUP BY credit_kind",
            (wave_id, stage_name),
        ):
            key = (
                "structural_source_credit"
                if kind == "structural"
                else "content_source_credit"
            )
            values[key] += int(token_sum)
            values["source_credit_count"] += int(count)
        residual = conn.execute(
            "SELECT COALESCE(SUM(residual),0),COUNT(*) FROM evaluation_attachment"
            " WHERE wave_id=? AND stage=? AND active=1",
            (wave_id, stage_name),
        ).fetchone()
        values["matched_pair_residual"] = int(residual[0]) if residual else 0
        values["paired_evaluation_count"] = int(residual[1]) if residual else 0
        values["direct_net"] = (
            values["content_source_credit"]
            + values["structural_source_credit"]
            + values["workflow_prompt_credit"]
            - values["request_debit"]
            - values["response_debit"]
        )
        if snapshot["measurement_status"] == "healthy":
            values["estimated_tokens_saved"] = max(
                0, values["direct_net"] + values["matched_pair_residual"]
            )
        snapshot["stages"][stage_name] = values
    for values in snapshot["stages"].values():
        for key in _STAGE_KEYS:
            snapshot["totals"][key] += int(values[key])
    totals = snapshot["totals"]
    totals["direct_net"] = (
        totals["content_source_credit"]
        + totals["structural_source_credit"]
        + totals["workflow_prompt_credit"]
        - totals["request_debit"]
        - totals["response_debit"]
    )
    totals["estimated_tokens_saved"] = (
        max(0, totals["direct_net"] + totals["matched_pair_residual"])
        if snapshot["measurement_status"] == "healthy"
        else 0
    )
    return snapshot


def read_wave_snapshot(root: Path, wave_id: str) -> dict[str, Any]:
    conn = _open_read_store(root)
    if conn is None:
        return empty_checkpoint(str(wave_id))
    try:
        version = conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        if version is None or str(version[0]) != str(STORE_SCHEMA_VERSION):
            snapshot = empty_checkpoint(str(wave_id))
            snapshot["measurement_status"] = "failed"
            return snapshot
        snapshot = _snapshot_from_conn(conn, str(wave_id))
        if gap_path(root).exists():
            snapshot["measurement_status"] = "accounting_gap"
            for values in snapshot["stages"].values():
                values["estimated_tokens_saved"] = 0
            snapshot["totals"]["estimated_tokens_saved"] = 0
        return snapshot
    except sqlite3.Error:
        snapshot = empty_checkpoint(str(wave_id))
        snapshot["measurement_status"] = "failed"
        return snapshot
    finally:
        conn.close()


def read_general_totals(
    root: Path, producer_id: str | None = None
) -> dict[str, int]:
    empty = {
        "calls": 0,
        "request_debit": 0,
        "response_debit": 0,
        "source_credit": 0,
        "estimated_tokens_saved": 0,
    }
    conn = _open_read_store(root)
    if conn is None:
        return empty
    try:
        where = "wave_id IS NULL"
        params: tuple[Any, ...] = ()
        if producer_id:
            where += " AND producer_id=?"
            params = (producer_id,)
        event = conn.execute(
            "SELECT COUNT(*),COALESCE(SUM(request_tokens),0),"
            f"COALESCE(SUM(response_tokens),0) FROM telemetry_event WHERE {where}",
            params,
        ).fetchone()
        source = conn.execute(
            "SELECT COALESCE(SUM(tokens),0) FROM source_credit "
            + (
                "WHERE wave_key=?"
                if producer_id
                else "WHERE wave_key LIKE 'general:%'"
            ),
            ((f"general:{producer_id}",) if producer_id else ()),
        ).fetchone()
        empty.update(
            calls=int(event[0]),
            request_debit=int(event[1]),
            response_debit=int(event[2]),
            source_credit=int(source[0]),
        )
        empty["estimated_tokens_saved"] = max(
            0,
            empty["source_credit"]
            - empty["request_debit"]
            - empty["response_debit"],
        )
        if _accounting_gap(conn) or gap_path(root).exists():
            empty["estimated_tokens_saved"] = 0
        return empty
    except sqlite3.Error:
        return empty
    finally:
        conn.close()


def pending_wave_ids(root: Path) -> dict[str, Any]:
    """Return a typed pending-generation census without hiding authority failure."""

    health = read_store_health(root)
    if health["status"] == "absent":
        return {"ok": True, "pending": [], "status": "absent", "error": None}
    if health["status"] != "healthy":
        return {
            "ok": False,
            "pending": [],
            "status": str(health["status"]),
            "error": health.get("diagnostic") or "telemetry authority is unreadable",
        }
    conn = _open_read_store(root)
    if conn is None:
        return {
            "ok": False,
            "pending": [],
            "status": "failed",
            "error": "telemetry authority could not be opened",
        }
    try:
        if not _table_exists(conn, "wave_state"):
            return {
                "ok": False,
                "pending": [],
                "status": "failed",
                "error": "telemetry authority has no wave_state table",
            }
        return {
            "ok": True,
            "pending": [
                str(row[0])
                for row in conn.execute(
                    "SELECT wave_id FROM wave_state WHERE pending=1 ORDER BY wave_id"
                )
            ],
            "status": "healthy",
            "error": None,
        }
    except sqlite3.Error as exc:
        return {
            "ok": False,
            "pending": [],
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        conn.close()


def reconcile_checkpoint_authority(
    root: Path, wave_id: str, checkpoint: Mapping[str, Any]
) -> bool:
    """Freeze a measured wave when its published store identity is unavailable."""

    published_instance = str(checkpoint.get("store_instance_id", "") or "")
    if not published_instance:
        return True
    try:
        conn = _open_write_store(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            current = _store_instance_id(conn)
            if current != published_instance:
                conn.execute(
                    "INSERT INTO wave_state("
                    "wave_id,generation,pending,published_json,store_instance_id,"
                    "measurement_status) VALUES(?,0,0,NULL,?,'credit_history_unavailable')"
                    " ON CONFLICT(wave_id) DO UPDATE SET "
                    "measurement_status='credit_history_unavailable'",
                    (str(wave_id), current),
                )
            conn.commit()
            return current == published_instance
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception:
        return False


def mark_checkpoint_published(
    root: Path,
    wave_id: str,
    snapshot: Mapping[str, Any],
    *,
    expected_generation: int,
) -> bool:
    try:
        conn = _open_write_store(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            changed = conn.execute(
                "UPDATE wave_state SET pending=0,published_json=?,"
                "store_instance_id=? WHERE wave_id=? AND generation=?",
                (
                    canonical_core_json(dict(snapshot)),
                    str(snapshot.get("store_instance_id", "")),
                    str(wave_id),
                    int(expected_generation),
                ),
            ).rowcount
            conn.commit()
            return bool(changed)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception:
        return False


def _normalized_checkpoint_state(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    state = empty_checkpoint(str(snapshot.get("wave_id", "")))
    state["generation"] = max(0, int(snapshot.get("generation", 0)))
    state["pending"] = bool(snapshot.get("pending", False))
    state["store_instance_id"] = str(snapshot.get("store_instance_id", ""))
    status = str(snapshot.get("measurement_status", "unmeasured"))
    state["measurement_status"] = status
    stages = snapshot.get("stages", {})
    if isinstance(stages, Mapping):
        for name in sorted(stages):
            values = stages[name]
            if not isinstance(values, Mapping):
                continue
            state["stages"][str(name)] = {
                key: int(values.get(key, 0)) for key in _STAGE_KEYS
            }
    state["totals"] = _empty_stage_totals()
    for values in state["stages"].values():
        for key in _STAGE_KEYS:
            state["totals"][key] += int(values[key])
    totals = state["totals"]
    totals["direct_net"] = (
        totals["content_source_credit"]
        + totals["structural_source_credit"]
        + totals["workflow_prompt_credit"]
        - totals["request_debit"]
        - totals["response_debit"]
    )
    totals["estimated_tokens_saved"] = (
        max(0, totals["direct_net"] + totals["matched_pair_residual"])
        if state["measurement_status"] == "healthy"
        else 0
    )
    return state


def _checkpoint_state_errors(snapshot: Any) -> list[str]:
    if not isinstance(snapshot, dict):
        return ["state must be a JSON object"]
    expected = {
        "schema_version",
        "wave_id",
        "generation",
        "pending",
        "store_instance_id",
        "measurement_status",
        "stages",
        "totals",
    }
    errors: list[str] = []
    if set(snapshot) != expected:
        errors.append("state has non-canonical top-level keys")
    if snapshot.get("schema_version") != STORE_SCHEMA_VERSION:
        errors.append("schema_version is missing or unsupported")
    if not isinstance(snapshot.get("wave_id"), str):
        errors.append("wave_id must be a string")
    if type(snapshot.get("generation")) is not int or snapshot["generation"] < 0:
        errors.append("generation must be a non-negative integer")
    if type(snapshot.get("pending")) is not bool:
        errors.append("pending must be a boolean")
    if not isinstance(snapshot.get("store_instance_id"), str):
        errors.append("store_instance_id must be a string")
    if snapshot.get("measurement_status") not in {
        "healthy",
        "unmeasured",
        "accounting_gap",
        "credit_history_unavailable",
        "failed",
    }:
        errors.append("measurement_status is unsupported")
    stages = snapshot.get("stages")
    if not isinstance(stages, dict):
        errors.append("stages must be an object")
    else:
        for name, values in stages.items():
            if not isinstance(name, str) or not name:
                errors.append("stage names must be non-empty strings")
                continue
            if not isinstance(values, dict) or set(values) != set(_STAGE_KEYS):
                errors.append(f"stage {name!r} has non-canonical keys")
                continue
            for key, value in values.items():
                if type(value) is not int:
                    errors.append(f"stage {name!r} {key!r} must be an integer")
                elif key != "direct_net" and value < 0:
                    errors.append(
                        f"stage {name!r} {key!r} must be non-negative"
                    )
    return errors


def render_checkpoint_block(snapshot: Mapping[str, Any]) -> str:
    state = _normalized_checkpoint_state(snapshot)
    status = state["measurement_status"]
    lines = [
        CONTEXT_EFFICIENCY_MARKER_BEGIN,
        "## Context Efficiency",
        "",
        (
            "Estimated token savings use phase-unique returned source versions "
            "and mapped workflow prompts, minus recorded request and response "
            "tokens. Saved model output or avoided tool loops count only through "
            "quality-equivalent paired evidence."
        ),
        "",
        "| Stage | Tool calls | Estimated token savings |",
        "| --- | ---: | ---: |",
    ]
    if status in {"accounting_gap", "credit_history_unavailable", "failed"}:
        lines.append(f"| {status} | 0 | 0 |")
    elif state["stages"]:
        for stage, values in state["stages"].items():
            lines.append(
                f"| {stage} | {values['calls']:,} | "
                f"{values['estimated_tokens_saved']:,} |"
            )
        lines.append(
            f"| **Total** | **{state['totals']['calls']:,}** | "
            f"**{state['totals']['estimated_tokens_saved']:,}** |"
        )
    else:
        lines.append("| — | 0 | 0 |")
    lines.extend(
        [
            "",
            f"{_CHECKPOINT_STATE_PREFIX}{canonical_core_json(state)}"
            f"{_CHECKPOINT_STATE_SUFFIX}",
            CONTEXT_EFFICIENCY_MARKER_END,
        ]
    )
    return "\n".join(lines)


def _extract_checkpoint_state(text: str) -> dict[str, Any] | None:
    canonical = _canonicalize_context_efficiency_markers(text)
    if canonical.count(CONTEXT_EFFICIENCY_MARKER_BEGIN) != 1:
        return None
    if canonical.count(CONTEXT_EFFICIENCY_MARKER_END) != 1:
        return None
    if canonical.count(_CHECKPOINT_STATE_PREFIX) != 1:
        return None
    start = canonical.find(_CHECKPOINT_STATE_PREFIX)
    if start < 0:
        return None
    start += len(_CHECKPOINT_STATE_PREFIX)
    end = canonical.find(_CHECKPOINT_STATE_SUFFIX, start)
    if end < 0:
        return None
    try:
        value = json.loads(canonical[start:end])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def parse_checkpoint_block(text: str) -> Optional[dict[str, Any]]:
    if checkpoint_validation_errors(text):
        return None
    state = _extract_checkpoint_state(text)
    if state is None:
        return None
    if state.get("schema_version") == STORE_SCHEMA_VERSION:
        if _checkpoint_state_errors(state):
            return None
        return _normalized_checkpoint_state(state)
    return None


def checkpoint_validation_errors(text: str) -> list[str]:
    canonical = _canonicalize_context_efficiency_markers(text)
    begin_count = canonical.count(CONTEXT_EFFICIENCY_MARKER_BEGIN)
    end_count = canonical.count(CONTEXT_EFFICIENCY_MARKER_END)
    state_count = canonical.count(_CHECKPOINT_STATE_PREFIX)
    if begin_count == 0 and end_count == 0 and state_count == 0:
        return []
    if begin_count != 1 or end_count != 1 or state_count != 1:
        return ["context-efficiency checkpoint ownership is malformed"]
    state = _extract_checkpoint_state(canonical)
    if state is None:
        return ["context-efficiency checkpoint marker/state is malformed"]
    if state.get("schema_version") == STORE_SCHEMA_VERSION:
        errors = _checkpoint_state_errors(state)
        if errors:
            return errors
        if render_checkpoint_block(state) not in canonical:
            return ["context-efficiency checkpoint render does not match state"]
        return []
    return ["context-efficiency checkpoint schema is unsupported"]


def replace_checkpoint_block(text: str, snapshot: Mapping[str, Any]) -> str:
    canonical = _canonicalize_context_efficiency_markers(text)
    rendered = render_checkpoint_block(snapshot)
    start = canonical.find(CONTEXT_EFFICIENCY_MARKER_BEGIN)
    end = canonical.find(CONTEXT_EFFICIENCY_MARKER_END)
    if start < 0 and end < 0:
        separator = "" if not canonical or canonical.endswith("\n\n") else (
            "\n" if canonical.endswith("\n") else "\n\n"
        )
        return canonical + separator + rendered + "\n"
    if start < 0 or end < start:
        raise ValueError("malformed context-efficiency marker region")
    end += len(CONTEXT_EFFICIENCY_MARKER_END)
    return canonical[:start] + rendered + canonical[end:]


def workflow_proxy_after_flush(
    metric: Mapping[str, Any],
    wave_id: str,
    result: FlushResult,
) -> dict[str, Any]:
    payload = dict(metric)
    if result.success:
        payload["persistence"] = payload.get("persistence", "durable")
    elif result.persistence == "poisoned":
        payload["persistence"] = "poisoned"
        payload["credited"] = False
    else:
        payload["persistence"] = "failed"
        payload["credited"] = False
        payload["fatal_persistence_failure"] = True
    return payload


def _phase_direct_net(
    conn: sqlite3.Connection, wave_id: str, phase_id: str
) -> int:
    event = conn.execute(
        "SELECT COALESCE(SUM(request_tokens),0),"
        "COALESCE(SUM(response_tokens),0),"
        "COALESCE(SUM(workflow_prompt_tokens),0) "
        "FROM telemetry_event WHERE wave_id=? AND phase_id=?",
        (wave_id, phase_id),
    ).fetchone()
    source = conn.execute(
        "SELECT COALESCE(SUM(tokens),0) FROM source_credit "
        "WHERE wave_key=? AND phase_id=?",
        (wave_id, phase_id),
    ).fetchone()
    return (
        int(source[0] if source else 0)
        + int(event[2] if event else 0)
        - int(event[0] if event else 0)
        - int(event[1] if event else 0)
    )


def attach_evaluation(
    root: Path,
    wave_id: str,
    phase_id: str,
    *,
    mode: str,
    applicability: Mapping[str, Any] | None = None,
    report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Register, attach, replace, or revoke a phase-scoped paired evaluation."""

    mode = str(mode).strip().lower()
    if mode not in {"register", "attach", "replace", "revoke"}:
        raise ValueError("mode must be register, attach, replace, or revoke")
    conn = _open_write_store(root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        phase = conn.execute(
            "SELECT stage FROM phase_state WHERE wave_id=? AND phase_id=?",
            (str(wave_id), str(phase_id)),
        ).fetchone()
        if phase is None:
            raise ValueError("unknown phase_id")
        authoritative_stage = str(phase[0])
        if mode == "register":
            if not isinstance(applicability, Mapping):
                raise ValueError("applicability is required for register")
            required = {
                "wave_id",
                "phase_id",
                "stage",
                "task_spec_digest",
                "repository_snapshot_digest",
                "model_id",
                "model_version",
                "tool_configuration_digest",
            }
            expected = dict(applicability)
            if set(expected) != required or any(
                not isinstance(expected[key], str) or not expected[key]
                for key in required
            ):
                raise ValueError("applicability key is incomplete")
            if (
                expected["wave_id"] != str(wave_id)
                or expected["phase_id"] != str(phase_id)
                or expected["stage"] != authoritative_stage
            ):
                raise ValueError(
                    "applicability identity does not match the authoritative phase"
                )
            payload = canonical_core_json(expected)
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            existing = conn.execute(
                "SELECT scope_digest,applicability_json FROM evaluation_scope"
                " WHERE wave_id=? AND phase_id=?",
                (str(wave_id), str(phase_id)),
            ).fetchone()
            if existing and (str(existing[0]) != digest or str(existing[1]) != payload):
                raise ValueError("phase applicability is already registered")
            conn.execute(
                "INSERT OR IGNORE INTO evaluation_scope("
                "wave_id,phase_id,stage,scope_digest,applicability_json,created_at"
                ") VALUES(?,?,?,?,?,?)",
                (
                    str(wave_id),
                    str(phase_id),
                    authoritative_stage,
                    digest,
                    payload,
                    time.time(),
                ),
            )
            conn.commit()
            return {"registered": True, "scope_digest": digest}
        scope = conn.execute(
            "SELECT stage,scope_digest,applicability_json FROM evaluation_scope"
            " WHERE wave_id=? AND phase_id=?",
            (str(wave_id), str(phase_id)),
        ).fetchone()
        if scope is None:
            raise ValueError("evaluation applicability must be registered first")
        if mode == "revoke":
            changed = conn.execute(
                "UPDATE evaluation_attachment SET active=0 "
                "WHERE wave_id=? AND phase_id=? AND active=1",
                (str(wave_id), str(phase_id)),
            ).rowcount
            _touch_wave(conn, str(wave_id))
            conn.commit()
            return {"revoked": bool(changed), "matched_pair_residual": 0}
        if not isinstance(report, Mapping):
            raise ValueError("scorer report is required")
        if (
            report.get("quality_gate_passed") is not True
            or int(report.get("qualifying_pairs", 0)) < 5
        ):
            raise ValueError(
                "paired evaluation must pass the five-pair quality gate before attachment"
            )
        report_key = report.get("applicability")
        if not isinstance(report_key, Mapping):
            raise ValueError("report applicability is missing")
        if canonical_core_json(dict(report_key)) != str(scope[2]):
            raise ValueError("report applicability does not match registered scope")
        authoritative_direct_net = _phase_direct_net(
            conn, str(wave_id), str(phase_id)
        )
        pair_rows = report.get("pairs")
        if not isinstance(pair_rows, list) or not pair_rows:
            raise ValueError("scorer report pairs are missing")
        if any(
            not isinstance(pair, Mapping)
            or type(pair.get("assisted_direct_net")) is not int
            or int(pair["assisted_direct_net"]) != authoritative_direct_net
            for pair in pair_rows
        ):
            raise ValueError(
                "paired evaluation assisted_direct_net does not match "
                "the authoritative phase ledger"
            )
        evaluation_id = str(report.get("evaluation_id", ""))
        residual = report.get("matched_pair_residual")
        if not evaluation_id or type(residual) is not int or residual < 0:
            raise ValueError("report result is invalid")
        report_digest = hashlib.sha256(
            canonical_core_json(dict(report)).encode("utf-8")
        ).hexdigest()
        existing = conn.execute(
            "SELECT wave_id,phase_id,report_digest FROM evaluation_attachment"
            " WHERE evaluation_id=?",
            (evaluation_id,),
        ).fetchone()
        if existing:
            if (
                str(existing[0]),
                str(existing[1]),
                str(existing[2]),
            ) != (str(wave_id), str(phase_id), report_digest):
                raise ValueError("evaluation_id conflicts with existing attachment")
            conn.commit()
            return {
                "replayed": True,
                "evaluation_id": evaluation_id,
                "matched_pair_residual": int(residual),
            }
        supersedes = report.get("supersedes_evaluation_id")
        active = conn.execute(
            "SELECT evaluation_id FROM evaluation_attachment "
            "WHERE wave_id=? AND phase_id=? AND active=1",
            (str(wave_id), str(phase_id)),
        ).fetchone()
        if mode == "attach" and active is not None:
            raise ValueError("phase already has an active evaluation")
        if mode == "replace":
            if active is None or str(supersedes or "") != str(active[0]):
                raise ValueError("replacement must supersede the active evaluation")
            conn.execute(
                "UPDATE evaluation_attachment SET active=0 WHERE evaluation_id=?",
                (str(active[0]),),
            )
        conn.execute(
            "INSERT INTO evaluation_attachment("
            "evaluation_id,wave_id,phase_id,stage,scope_digest,residual,active,"
            "supersedes_evaluation_id,report_digest,created_at)"
            " VALUES(?,?,?,?,?,?,1,?,?,?)",
            (
                evaluation_id,
                str(wave_id),
                str(phase_id),
                authoritative_stage,
                str(scope[1]),
                int(residual),
                str(supersedes) if supersedes else None,
                report_digest,
                time.time(),
            ),
        )
        _touch_wave(conn, str(wave_id))
        conn.commit()
        return {
            "attached": True,
            "evaluation_id": evaluation_id,
            "matched_pair_residual": int(residual),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
