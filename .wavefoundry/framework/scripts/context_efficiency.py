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

import codecs
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
from typing import Any, Callable, Iterable, Mapping, Optional
from runtime_lock import RuntimeFileLock, RuntimeLockBusy, RuntimeLockError
import record_paths  # record roots (wave 1y0gz)


STORE_RELATIVE_PATH = Path(".wavefoundry/logs/context-efficiency.sqlite")
PRODUCER_LEASE_RELATIVE_DIR = Path(
    ".wavefoundry/locks/producers"
)
GENERAL_ASSOCIATION_NOTE = (
    "associated unattributed context at successful wave creation or "
    "preparation; may include exploration not exclusive to this wave."
)

LIFECYCLE_PROMPT_MAP: Mapping[str, Path] = {
    "wf_create_wave": Path("docs/prompts/create-wave.prompt.md"),
    "wf_prepare_wave": Path("docs/prompts/prepare-wave.prompt.md"),
    "wf_implement_wave": Path("docs/prompts/implement-wave.prompt.md"),
    "wf_review_wave": Path("docs/prompts/review-wave.prompt.md"),
    "wf_close_wave": Path("docs/prompts/close-wave.prompt.md"),
    # Exact-item tracking tools (wf_mark_ac / wf_mark_task) deliberately have NO
    # entry here. Their saving is not a one-time procedure lookup: it recurs on
    # every call and is measured per write via
    # `workflow_instruction_proxy(avoided_authoring_tokens=...)`. They also earn
    # no content-source credit, because they return no change-doc content and
    # `_context_source_paths` credits only content that is in the envelope.
}

# Wave 1t3gt (1t3ld): the ONLY stage values the accounting layer ever writes.
# Lifecycle mapping: create/prepare -> plan, implement -> implement,
# review/close -> review; adopted unattributed telemetry lands in plan.
# There is deliberately no legacy read-side mapping — history was cleaned up
# once, by hand, and the code never recognizes the old names.
CANONICAL_STAGES = ("plan", "implement", "review")
_CANONICAL_STAGE_ORDER = {name: i for i, name in enumerate(CANONICAL_STAGES)}

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
    from path_containment import contained_resolved_path

    try:
        resolved_root = Path(root).resolve(strict=True)
        prompt = (resolved_root / relative).resolve(strict=True)
        if contained_resolved_path(resolved_root, prompt) is None or not prompt.is_file():
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


def implement_stage_retrieval_calls(
    root: Path, wave_id: str, tool_names: Optional[Iterable[str]] = None
) -> int | None:
    """Read-only count of instrumented retrieval events under the wave's
    ``implement`` stage — the retrieval-posture sensor signal (wave 1t3ek /
    1t230). Returns ``None`` when the store is absent or unreadable so the
    sensor stays silent rather than firing on missing data.

    Wave 1t72b (1t67p): since the full-surface wrapper, ``event_kind
    ='retrieval'`` covers every wrapped first-party call, so an incidental
    lifecycle probe could mask a code-exploration drought. Pass ``tool_names``
    (the code-retrieval census) to count only those tools; None keeps the
    unfiltered total for telemetry summaries."""
    path = store_path(root)
    if not path.is_file():
        return None
    names = sorted(set(str(n) for n in tool_names)) if tool_names else None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            query = (
                "SELECT COUNT(*) FROM telemetry_event "
                "WHERE wave_id=? AND stage='implement' AND event_kind='retrieval'"
            )
            params: list = [wave_id]
            if names is not None:
                query += (
                    " AND tool_name IN ("
                    + ",".join("?" for _ in names)
                    + ")"
                )
                params.extend(names)
            row = conn.execute(query, params).fetchone()
            return int(row[0])
        finally:
            conn.close()
    except sqlite3.Error:
        return None



# --- Open-wave attribution (wave 1t3ek / 1t3el) -----------------------------
# Multi-agent sessions run their own server processes; only the gate-running
# process has lifecycle focus. A focus-less producer resolves the single OPEN
# wave (the single-OPEN invariant makes this unambiguous) and attributes its
# instrumented work there instead of the general bucket. Any failure or
# ambiguity falls through to the general bucket unchanged.

_OPEN_WAVE_CACHE_TTL_SECONDS = 10.0
_open_wave_cache_lock = threading.Lock()
_open_wave_cache: dict[str, tuple[float, Optional[tuple[str, str]]]] = {}
_OPEN_WAVE_STATUSES = ("active", "implementing")
_DELIVERY_RUN_KINDS = frozenset(
    {"initial_delivery", "repair_start", "reverification", "convergence_checkpoint"}
)


def _reset_open_wave_cache() -> None:
    """Test seam: drop the TTL cache so state changes resolve immediately."""
    with _open_wave_cache_lock:
        _open_wave_cache.clear()


def _wave_status_from_text(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("Status:"):
            return line.split(":", 1)[1].strip().lower()
    return ""


def _derive_open_wave_stage(wave_dir: Path) -> str:
    """`review` once the canonical ledger holds a delivery run, else `implement`.

    Parses ledger lines as JSON rather than substring-matching serialized
    text — the canonical writer emits compact JSON, and a marker string with
    different whitespace silently never matches (a live-caught 1t3el defect;
    the original fixture echoed the spaced assumption). Unparseable lines are
    skipped; only the shape of the parsed record matters.
    """
    events = wave_dir / "events.jsonl"
    try:
        if events.is_file():
            for line in events.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(record, dict):
                    continue
                if record.get("run_kind") in _DELIVERY_RUN_KINDS or (
                    isinstance(record.get("event_identity"), dict)
                    and record["event_identity"].get("run_kind") in _DELIVERY_RUN_KINDS
                ):
                    return "review"
    except OSError:
        pass
    return "implement"


def resolve_open_wave(root: Path) -> Optional[tuple[str, str]]:
    """Return ``(wave_id, stage)`` for the single OPEN wave, else ``None``.

    TTL-cached per root; zero OPEN waves, more than one, or any read failure
    resolves to ``None`` (the caller keeps today's general-bucket behavior).
    """
    key = str(root)
    now = time.monotonic()
    with _open_wave_cache_lock:
        cached = _open_wave_cache.get(key)
        if cached is not None and now - cached[0] < _OPEN_WAVE_CACHE_TTL_SECONDS:
            return cached[1]
    resolved: Optional[tuple[str, str]] = None
    try:
        open_dirs: list[Path] = []
        if record_paths.load_record_roots(Path(root)).waves.is_dir():
            # Wave 1y043: the shared discovery walk (flat or nested).
            for entry in record_paths.discover_wave_dirs(Path(root)):
                wave_md = entry / "wave.md"
                try:
                    head = wave_md.read_text(encoding="utf-8", errors="replace")[:2048]
                except OSError:
                    continue
                if _wave_status_from_text(head) in _OPEN_WAVE_STATUSES:
                    open_dirs.append(entry)
                    if len(open_dirs) > 1:
                        break
        if len(open_dirs) == 1:
            resolved = (open_dirs[0].name, _derive_open_wave_stage(open_dirs[0]))
    except Exception:
        resolved = None
    with _open_wave_cache_lock:
        _open_wave_cache[key] = (now, resolved)
    return resolved


# --- Effective attribution (wave 1tmb3) --------------------------------------
# ONE resolver, owned by this telemetry authority layer, answers "where would
# instrumented work land right now": usable explicit focus first; a sealed
# destination redirects to the general bucket; with no explicit focus the
# unique OPEN-wave fallback applies; otherwise general/unattributed.
# ``_commit_event`` and lifecycle reporting both go through
# ``resolve_attribution`` so the two can never drift.


@dataclass(frozen=True)
class AttributionResolution:
    """Resolved destination for instrumented work.

    ``wave_id`` is ``None`` for the general bucket. ``attribution`` keeps the
    commit-column vocabulary (``focus`` / ``open_wave``) exactly as before the
    resolver was extracted; ``sealed_redirect`` records that a sealed
    destination was redirected to general.
    """

    wave_id: Optional[str]
    stage: str
    attribution: str
    sealed_redirect: bool = False


def resolve_attribution(
    focus_wave: Optional[str],
    focus_stage: Optional[str],
    open_wave: Optional[tuple[str, str]],
    is_sealed: Callable[[str], bool],
) -> AttributionResolution:
    """Pure attribution policy shared by commit and lifecycle reporting."""

    wave_id = focus_wave or None
    stage = focus_stage or "general"
    attribution = "focus"
    if not wave_id and open_wave is not None:
        wave_id, stage = open_wave
        attribution = "open_wave"
    if wave_id and is_sealed(wave_id):
        return AttributionResolution(None, "general", attribution, True)
    return AttributionResolution(wave_id, stage, attribution)


def _wave_sealed_readonly(root: Optional[Path], wave_id: str) -> bool:
    """Best-effort sealed check outside a write transaction."""

    if root is None:
        return False
    conn = _open_read_store(root)
    if conn is None:
        return False
    try:
        row = conn.execute(
            "SELECT sealed FROM wave_state WHERE wave_id=?", (wave_id,)
        ).fetchone()
        return row is not None and bool(row[0])
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def resolve_effective_attribution(
    root: Optional[Path], focus: "Focus"
) -> dict[str, Any]:
    """Report where instrumented work would be attributed right now.

    Returns ``{"destination": <wave_id>|"general", "stage": str|None,
    "source": "focus"|"focus_sealed_general"|"open_wave"|
    "open_wave_sealed_general"|"general"}``. Best-effort and read-only —
    reporting must never mutate telemetry state.
    """

    open_wave = None
    if not focus.wave_id and root is not None:
        open_wave = resolve_open_wave(root)
    resolution = resolve_attribution(
        focus.wave_id,
        focus.stage,
        open_wave,
        lambda wave_id: _wave_sealed_readonly(root, wave_id),
    )
    if resolution.wave_id is None:
        if resolution.sealed_redirect:
            source = f"{resolution.attribution}_sealed_general"
        else:
            source = "general"
        return {"destination": "general", "stage": None, "source": source}
    return {
        "destination": resolution.wave_id,
        "stage": resolution.stage,
        "source": resolution.attribution,
    }


def producer_lease_path(root: Path, producer_id: str) -> Path:
    return Path(root) / PRODUCER_LEASE_RELATIVE_DIR / f"{producer_id}.lock"


def _try_lock_lease(path: Path, *, create: bool) -> tuple[Any | None, bool]:
    """Try to hold one producer lease without waiting.

    Missing probe files are deliberately indeterminate rather than abandoned:
    only a persisted, unlocked lease is positive crash evidence.
    """

    if not create and not path.is_file():
        return None, False
    try:
        lock = RuntimeFileLock(path, blocking=False)
        lock.acquire()
        return lock, True
    except (RuntimeLockBusy, RuntimeLockError):
        return None, False


def _unlock_lease(handle: Any | None) -> None:
    if handle is None:
        return
    try:
        handle.release()
    except RuntimeLockError:
        pass



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


def latest_phase_id(root: Path, wave_id: str, stage: str) -> Optional[str]:
    """Return the newest durable phase for one wave-stage without creating state."""

    conn = _open_read_store(root)
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT phase_id FROM phase_state WHERE wave_id=? AND stage=? "
            "ORDER BY ordinal DESC LIMIT 1",
            (str(wave_id), str(stage)),
        ).fetchone()
        return str(row[0]) if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()



def _canonicalize_context_efficiency_markers(markdown: str) -> str:
    """Normalize legacy marker names and the exact historical checkpoint layout."""

    for legacy, canonical in _LEGACY_CONTEXT_EFFICIENCY_MARKERS.items():
        markdown = markdown.replace(legacy, canonical)
    return markdown.replace(
        CONTEXT_EFFICIENCY_MARKER_BEGIN + "\n## Context Efficiency\n\n",
        "## Context Efficiency\n\n" + CONTEXT_EFFICIENCY_MARKER_BEGIN + "\n\n",
    )



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
    "compact_published_wave",
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
    "unseal_wave",
    "workflow_instruction_proxy",
    "workflow_proxy_after_flush",
]

__all__.extend(
    [
        "attach_evaluation",
        "CLEAR_GAP_COMMAND",
        "clear_accounting_gap",
        "gap_path",
        "pending_wave_ids",
        "poison_accounting_gap",
        "read_gap_reason",
        "replay_spool",
        "spooled_events_affecting",
        "mark_wave_accounting_gap",
        "reconcile_checkpoint_authority",
    ]
)


# ---------------------------------------------------------------------------
# Write-through, phase-aware accounting
# ---------------------------------------------------------------------------

STORE_SCHEMA_VERSION = 1
GAP_RELATIVE_PATH = Path(".wavefoundry/logs/context-efficiency.gap")
# Wave 1z2ma: a failed event commit is kept as one file here and replayed later.
SPOOL_RELATIVE_DIR = Path(".wavefoundry/logs/context-efficiency-spool")
SPOOL_MAX_EVENTS = 1000
_SPOOL_SUFFIX = ".json"
_SPOOL_METRIC_FIELDS = (
    "estimated_request_tokens",
    "estimated_returned_tokens",
    "prompt_surface_tokens",
    "derived_artifact_tokens",
)
_SPOOL_CREDIT_FIELDS = ("source_id", "version_id", "tokens", "credit_kind")
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
    "estimated context avoided — whole eligible text-file baseline minus "
    "the canonical request and complete response, with each source version "
    "credited once per wave phase; not measured model-token savings."
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
It shows one per-stage Estimated context avoided total. Runtime
telemetry is written through to the host-local SQLite authority; lifecycle,
reload, and upgrade boundaries project durable totals into `wave.md`.
Whole eligible text-file, workflow-prompt and derived-artifact credits are reduced
by every recorded request and complete response. This baseline does not prove
what an agent otherwise would have read or spent. Saved output or avoided tool
loops count only through quality-equivalent paired evidence, recorded separately
in the checkpoint state. Runtime lifecycle tools own projection;
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


_SOURCE_PREFIX_BYTES = 4096
_BINARY_SOURCE_SUFFIXES = frozenset({
    ".sqlite", ".sqlite3", ".db", ".db3", ".lance", ".bin",
    ".zip", ".gz", ".bz2", ".xz", ".7z", ".tar", ".tgz", ".zst",
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".o", ".a",
    ".class", ".jar", ".wasm", ".pdf", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".woff", ".woff2", ".onnx", ".safetensors",
})


def _eligible_source_text(root: Path, path: Path, size: int) -> bool:
    """Conservatively recognize source text; never scan a whole file for credit."""
    parts = tuple(part.casefold() for part in path.relative_to(root).parts)
    if (
        parts[:2] in {(".wavefoundry", "index"), (".wavefoundry", "logs"),
                      (".wavefoundry", "locks")}
        or any(part.endswith(".lance") or part in {".git", "__pycache__"}
               for part in parts)
        or path.suffix.casefold() in _BINARY_SOURCE_SUFFIXES
        or path.name.casefold().endswith(("-wal", "-shm", "-journal"))
    ):
        return False
    try:
        with path.open("rb") as source:
            prefix = source.read(_SOURCE_PREFIX_BYTES)
        if b"\0" in prefix:
            return False
        # A valid multibyte character may straddle the bounded sample's end.
        codecs.getincrementaldecoder("utf-8")().decode(
            prefix, final=len(prefix) >= size or len(prefix) < _SOURCE_PREFIX_BYTES
        )
        return True
    except (OSError, UnicodeError, ValueError):
        return False


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
        if current is None or not _eligible_source_text(resolved_root, resolved, current.size):
            continue
        classification = "estimated"
        stronger = False
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
        kind = (
            "structural"
            if any(proof.credit_kind == "structural" for proof in candidates)
            else "content"
        )
        token_count = estimate_tokens_from_byte_count(current.size)
        credits.append(
            SourceCreditCandidate(
                source_id=_opaque_source_id(resolved_root, resolved),
                version_id=_opaque_version_id(current, stronger),
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
    avoided_authoring_tokens: int | None = None,
) -> dict[str, Any]:
    """Build one workflow ledger candidate; no-op calls retain both debits.

    ``avoided_authoring_tokens`` replaces the prompt-surface baseline for tools
    whose saving RECURS per call rather than happening once. An exact-item
    tracking tool is the case: performing the same edit by hand costs the item's
    full text TWICE (the match string and the replacement), every time, so the
    saving scales with item count and item length rather than with a one-time
    procedure lookup. Measured on wave 1ui1d's own 41 items, hand-editing would
    have cost 4,084 tokens against 791 for the tool calls; acceptance criteria
    saved 121 tokens each and short task lines only 16, which is exactly the
    per-item variation a single aggregate credit cannot express. The caller
    supplies the measurement because only it knows which block matched.
    """

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
        if avoided_authoring_tokens is not None:
            prompt_tokens = max(0, int(avoided_authoring_tokens))
        else:
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


CLEAR_GAP_COMMAND = "./.wavefoundry/bin/wf clear-accounting-gap"
CLEAR_GAP_COMMAND_WINDOWS = ".\\.wavefoundry\\bin\\wf.cmd clear-accounting-gap"
# Busy/locked writes are retried as whole attempts within this budget before
# the barrier is written (wave 1z2m4). Module constants so tests can shorten them.
BUSY_RETRY_BUDGET_SECONDS = 10.0
BUSY_RETRY_DELAYS = (0.01, 0.025, 0.05, 0.1, 0.2, 0.4, 0.8)
_BUSY_CODES = frozenset(
    {getattr(sqlite3, "SQLITE_BUSY", 5), getattr(sqlite3, "SQLITE_LOCKED", 6)}
)


def _is_busy_error(exc: BaseException) -> bool:
    if not isinstance(exc, sqlite3.OperationalError):
        return False
    code = getattr(exc, "sqlite_errorcode", None)
    if isinstance(code, int):
        return (code & 0xFF) in _BUSY_CODES
    message = str(exc).lower()
    return "locked" in message or "busy" in message


def _with_busy_retry(attempt: Callable[[], Any]) -> Any:
    """Run ``attempt`` again after a busy/locked error until the budget ends."""

    deadline = time.monotonic() + BUSY_RETRY_BUDGET_SECONDS
    delays = iter(BUSY_RETRY_DELAYS)
    delay = 0.0
    while True:
        try:
            return attempt()
        except sqlite3.OperationalError as exc:
            if not _is_busy_error(exc):
                raise
            delay = next(delays, delay)
            if time.monotonic() + delay > deadline:
                raise
            time.sleep(delay)


# Windows refuses to rename a file another process has open (WinError 32: a
# reader of the gap reason, or an antivirus scan). The clear retries that
# briefly; it holds the store's write lock meanwhile, so the budget stays short
# enough not to push other writers past their own busy budget.
SHARING_RETRY_BUDGET_SECONDS = 2.0
_SHARING_VIOLATION_RETRY = os.name == "nt"


def _replace_with_retry(src: Path, dst: Path) -> None:
    deadline = time.monotonic() + SHARING_RETRY_BUDGET_SECONDS
    delays = iter(BUSY_RETRY_DELAYS)
    delay = 0.0
    while True:
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if not _SHARING_VIOLATION_RETRY:
                raise
            delay = next(delays, delay)
            if time.monotonic() + delay > deadline:
                raise
            time.sleep(delay)


def _write_exclusive(path: Path, payload: bytes) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_gap_sentinel(
    root: Path, operation: str = "unknown", error: object = None
) -> bool:
    """Durably poison positive publication, recording why but no call content.

    The first writer wins, so a later failure never hides the original cause;
    an existing sentinel still means the barrier holds.
    """

    path = gap_path(root)
    if isinstance(error, BaseException):
        error_type = type(error).__name__
        # An instrumentation exception can echo response values; keep only
        # SQLite messages, which never carry call content.
        message = str(error) if isinstance(error, sqlite3.Error) else ""
    else:
        error_type, message = "", str(error or "")
    record = {
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "operation": str(operation),
        "error_type": error_type,
        "message": message[:500],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return True
        # Write a private temp file, then link it into place: the link fails
        # when a sentinel already exists (first writer wins) and a reader never
        # sees a half-written reason.
        payload = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
        temp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
        _write_exclusive(temp, payload)
        try:
            try:
                os.link(temp, path)
            except FileExistsError:
                pass
            except OSError:
                # No hard links on this filesystem: exclusive create instead.
                try:
                    _write_exclusive(path, payload)
                except FileExistsError:
                    pass
        finally:
            try:
                temp.unlink()
            except OSError:
                pass
        return True
    except OSError:
        return path.exists()


def read_gap_reason(root: Path) -> Optional[dict[str, str]]:
    """Return the recorded gap reason, ``{}`` when unrecorded, None without a sentinel."""

    path = gap_path(root)
    if not path.exists():
        return None
    record = _read_reason_file(path)
    if not record:
        return {}
    return {
        key: record.get(key, "")
        for key in ("recorded_at", "operation", "error_type", "message")
    }


def _gap_diagnostic(reason: Optional[Mapping[str, str]]) -> str:
    text = "positive projection suppressed by durable accounting gap"
    if reason and reason.get("recorded_at"):
        cause = reason.get("error_type") or "error"
        if reason.get("message"):
            cause += f": {reason['message']}"
        text += (
            f" (recorded {reason['recorded_at']} during"
            f" {reason.get('operation') or 'unknown'}; {cause})"
        )
    else:
        text += " (reason not recorded)"
    return (
        f"{text}; clear it with `{CLEAR_GAP_COMMAND}`"
        f" (native Windows: `{CLEAR_GAP_COMMAND_WINDOWS}`)"
    )


def poison_accounting_gap(
    root: Path, *, operation: str = "instrumentation", error: object = None
) -> bool:
    """Persist the fail-closed barrier when telemetry cannot reach its event commit."""

    return _write_gap_sentinel(root, operation, error)


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

    return _with_busy_retry(lambda: _open_write_store_once(root))


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
        "event_tombstone",
        "source_credit",
        "producer_state",
        "wave_state",
        "evaluation_scope",
        "evaluation_attachment",
        "exploration_credit_event",
    }.issubset(
        {
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    )
    if schema_ready:
        # Every additive column MUST appear here: the fast path skips the
        # migration block entirely, so a column missing from this check never
        # gets ALTERed onto an already-current store (wave 1t3ek / 1t3el found
        # this the hard way — the INSERT then fails and poisons the store).
        schema_ready = (
            {
                "source_credits_dropped",
                "attribution",
                "derived_artifact_tokens",
            }.issubset(_column_names(conn, "telemetry_event"))
            and {
                "floor_json",
                "compacted_generation",
                "sealed",
            }.issubset(_column_names(conn, "wave_state"))
        )
    if schema_ready:
        if gap_path(root).exists():
            conn.execute("BEGIN IMMEDIATE")
            try:
                # Re-check under the write lock: a clear that committed while
                # this open waited must not have its flag copied back.
                if gap_path(root).exists():
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
            "attribution TEXT NOT NULL DEFAULT 'focus',"
            "derived_artifact_tokens INTEGER NOT NULL DEFAULT 0,"
            "created_at REAL NOT NULL)"
        )
        event_columns = _column_names(conn, "telemetry_event")
        if "source_credits_dropped" not in event_columns:
            conn.execute(
                "ALTER TABLE telemetry_event ADD COLUMN "
                "source_credits_dropped INTEGER NOT NULL DEFAULT 0"
            )
        if "attribution" not in event_columns:
            # Wave 1t3ek (1t3el): additive provenance — 'focus' (direct
            # lifecycle focus), 'open_wave' (attributed to the single OPEN
            # wave), or 'adopted' (boundary adoption of a general bucket).
            conn.execute(
                "ALTER TABLE telemetry_event ADD COLUMN "
                "attribution TEXT NOT NULL DEFAULT 'focus'"
            )
        if "derived_artifact_tokens" not in event_columns:
            # Wave 1t3ek (1t3s7): avoided-writing credit — the size of textual
            # artifacts a tool persisted that the caller did not supply.
            conn.execute(
                "ALTER TABLE telemetry_event ADD COLUMN "
                "derived_artifact_tokens INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS telemetry_event_wave_stage "
            "ON telemetry_event(wave_id,stage)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS event_tombstone("
            "event_id TEXT PRIMARY KEY, wave_id TEXT NOT NULL) WITHOUT ROWID"
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
            "CREATE TABLE IF NOT EXISTS producer_state("
            "producer_id TEXT PRIMARY KEY, reclaimable INTEGER NOT NULL,"
            "updated_at REAL NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS wave_state("
            "wave_id TEXT PRIMARY KEY, generation INTEGER NOT NULL DEFAULT 0,"
            "pending INTEGER NOT NULL DEFAULT 0, published_json TEXT,"
            "store_instance_id TEXT, measurement_status TEXT NOT NULL DEFAULT 'healthy',"
            "floor_json TEXT, compacted_generation INTEGER NOT NULL DEFAULT 0,"
            "sealed INTEGER NOT NULL DEFAULT 0)"
        )
        columns = _column_names(conn, "wave_state")
        if "store_instance_id" not in columns:
            conn.execute("ALTER TABLE wave_state ADD COLUMN store_instance_id TEXT")
        if "measurement_status" not in columns:
            conn.execute(
                "ALTER TABLE wave_state ADD COLUMN measurement_status TEXT"
                " NOT NULL DEFAULT 'healthy'"
            )
        if "floor_json" not in columns:
            conn.execute("ALTER TABLE wave_state ADD COLUMN floor_json TEXT")
        if "compacted_generation" not in columns:
            conn.execute(
                "ALTER TABLE wave_state ADD COLUMN compacted_generation INTEGER"
                " NOT NULL DEFAULT 0"
            )
        if "sealed" not in columns:
            conn.execute(
                "ALTER TABLE wave_state ADD COLUMN sealed INTEGER NOT NULL DEFAULT 0"
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
        conn.execute(
            "CREATE TABLE IF NOT EXISTS exploration_credit_event("
            "event_key TEXT PRIMARY KEY, wave_id TEXT NOT NULL,"
            "phase_id TEXT NOT NULL, stage TEXT NOT NULL,"
            "origin_id TEXT NOT NULL, memory_id TEXT NOT NULL,"
            "context_key TEXT NOT NULL, cited INTEGER NOT NULL,"
            "source_cost INTEGER NOT NULL, match_confidence REAL NOT NULL,"
            "credit INTEGER NOT NULL, created_at REAL NOT NULL)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS exploration_credit_wave_stage "
            "ON exploration_credit_event(wave_id,stage)"
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
    producer_reclaimable: bool,
    focus: Focus,
    tool_name: str,
    event_kind: str,
    metric: Mapping[str, Any],
    *,
    event_id: str,
) -> tuple[str, int, int, int]:
    # A rolled-back attempt is replayed whole; event_id dedupe keeps it exact.
    try:
        return _with_busy_retry(
            lambda: _commit_event_once(
                root,
                producer_id,
                producer_reclaimable,
                focus,
                tool_name,
                event_kind,
                metric,
                event_id=event_id,
            )
        )
    except Exception as exc:
        # Wave 1z2ma: keep the event and replay it later; the gap is written only
        # when the spool itself cannot take it.
        spooled, reason = _spool_event(
            root,
            producer_id,
            producer_reclaimable,
            focus,
            tool_name,
            event_kind,
            metric,
            event_id=event_id,
        )
        if spooled:
            return "spooled", 0, 0, 0
        if reason:
            reason = f"{reason}; last failure {type(exc).__name__}"
        return (
            "poisoned"
            if _write_gap_sentinel(root, "event_commit", reason or exc)
            else "failed",
            0,
            0,
            0,
        )


_RESOLVE_OPEN_WAVE = object()


def _commit_event_once(
    root: Path,
    producer_id: str,
    producer_reclaimable: bool,
    focus: Focus,
    tool_name: str,
    event_kind: str,
    metric: Mapping[str, Any],
    *,
    event_id: str,
    open_wave: Any = _RESOLVE_OPEN_WAVE,
) -> tuple[str, int, int, int]:
    conn: sqlite3.Connection | None = None
    try:
        conn = _open_write_store_once(root)
        conn.execute("BEGIN IMMEDIATE")
        if _accounting_gap(conn):
            conn.rollback()
            return "poisoned", 0, 0, 0
        # Wave 1tmb3: attribution policy lives in the shared resolver so
        # commit and lifecycle reporting can never drift. Wave 1t3ek (1t3el):
        # a focus-less producer attributes to the single OPEN wave;
        # none/ambiguity/failure keeps the general bucket.
        def _conn_sealed(candidate: str) -> bool:
            sealed = conn.execute(
                "SELECT sealed FROM wave_state WHERE wave_id=?", (candidate,)
            ).fetchone()
            return sealed is not None and bool(sealed[0])

        if conn.execute(
            "SELECT 1 FROM event_tombstone WHERE event_id=?", (event_id,)
        ).fetchone():
            conn.commit()
            return "duplicate", 0, 0, 0
        # A replayed spool event carries the open wave resolved when it failed,
        # so its attribution does not drift to whatever is open at replay time.
        if focus.wave_id:
            open_wave_now = None
        elif open_wave is _RESOLVE_OPEN_WAVE:
            open_wave_now = resolve_open_wave(root)
        else:
            open_wave_now = open_wave
        resolution = resolve_attribution(
            focus.wave_id,
            focus.stage,
            open_wave_now,
            _conn_sealed,
        )
        wave_id = resolution.wave_id
        stage = resolution.stage
        attribution = resolution.attribution
        if wave_id is None:
            phase_id = f"general:{producer_id}" if resolution.sealed_redirect else (
                focus.phase_id or f"general:{producer_id}"
            )
        elif attribution == "open_wave":
            phase_id = stage
        else:
            phase_id = focus.phase_id or f"general:{producer_id}"
        conn.execute(
            "INSERT INTO producer_state("
            "producer_id,reclaimable,updated_at"
            ") VALUES(?,?,?) ON CONFLICT(producer_id) DO UPDATE SET "
            "reclaimable=excluded.reclaimable,"
            "updated_at=excluded.updated_at",
            (producer_id, int(producer_reclaimable), time.time()),
        )
        inserted = conn.execute(
            "INSERT OR IGNORE INTO telemetry_event("
            "event_id,producer_id,wave_id,phase_id,stage,tool_name,event_kind,"
            "request_tokens,response_tokens,workflow_prompt_tokens,attribution,"
            "derived_artifact_tokens,created_at"
            ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                attribution,
                int(metric.get("derived_artifact_tokens", 0)),
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
        raise
    finally:
        if conn is not None:
            conn.close()


def spool_dir(root: Path) -> Path:
    return Path(root) / SPOOL_RELATIVE_DIR


def _spool_files(root: Path) -> list[Path]:
    """Published spool files, oldest first (names start with a UTC timestamp)."""

    directory = spool_dir(root)
    try:
        entries = list(directory.iterdir())
    except OSError:
        return []
    return sorted(
        entry for entry in entries
        if entry.name.endswith(_SPOOL_SUFFIX) and not entry.name.startswith(".")
    )


def _spool_name(event_id: str) -> str:
    safe = "".join(ch for ch in str(event_id) if ch.isalnum() or ch in "-_")
    if not safe or len(safe) > 64:
        safe = hashlib.sha256(str(event_id).encode("utf-8")).hexdigest()[:32]
    # No ':' anywhere: it is invalid in Windows file names.
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return f"{stamp}-{time.time_ns() % 1_000_000_000:09d}-{safe}{_SPOOL_SUFFIX}"


def _spool_event(
    root: Path,
    producer_id: str,
    producer_reclaimable: bool,
    focus: Focus,
    tool_name: str,
    event_kind: str,
    metric: Mapping[str, Any],
    *,
    event_id: str,
) -> tuple[bool, Optional[str]]:
    """Publish one failed event as a spool file; return (spooled, gap reason)."""

    directory = spool_dir(root)
    if len(_spool_files(root)) >= SPOOL_MAX_EVENTS:
        return False, f"spool_full: {SPOOL_MAX_EVENTS} events are waiting to replay"
    open_wave = None
    if not focus.wave_id:
        try:
            resolved = resolve_open_wave(root)
        except Exception:
            resolved = None
        open_wave = list(resolved) if resolved else None
    credits = [
        {key: raw.get(key) for key in _SPOOL_CREDIT_FIELDS}
        for raw in metric.get("_source_credits", ()) or ()
        if isinstance(raw, Mapping)
    ]
    record = {
        "schema": 1,
        "event_id": str(event_id),
        "producer_id": str(producer_id),
        "reclaimable": bool(producer_reclaimable),
        "focus": asdict(focus),
        "open_wave": open_wave,
        "tool_name": str(tool_name),
        "event_kind": str(event_kind),
        "metric": {
            **{key: int(metric.get(key, 0) or 0) for key in _SPOOL_METRIC_FIELDS},
            "_source_credits": credits,
        },
        "spooled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    payload = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / _spool_name(event_id)
        temp = directory / f".{path.name}.{uuid.uuid4().hex}.tmp"
        _write_exclusive(temp, payload)
        try:
            try:
                os.link(temp, path)
            except FileExistsError:
                pass
            except OSError:
                try:
                    _write_exclusive(path, payload)
                except FileExistsError:
                    pass
        finally:
            try:
                temp.unlink()
            except OSError:
                pass
        return True, None
    except OSError as exc:
        return False, f"spool_unwritable: {type(exc).__name__}"


def replay_spool(root: Path) -> dict[str, int]:
    """Commit spooled events oldest first; never spools or poisons for a retry.

    Safe to run from several processes at once: event-id deduplication turns a
    second commit of the same event into ``duplicate``.
    """

    result = {"replayed": 0, "kept": 0, "unreadable": 0}
    for path in _spool_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except OSError:
            result["kept"] += 1
            continue
        try:
            record = json.loads(text)
            focus = Focus(**record["focus"])
            open_wave = tuple(record["open_wave"]) if record.get("open_wave") else None
            args = (
                str(record["producer_id"]),
                bool(record.get("reclaimable")),
                focus,
                str(record["tool_name"]),
                str(record["event_kind"]),
                dict(record["metric"]),
            )
            event_id = str(record["event_id"])
        except (ValueError, KeyError, TypeError):
            # Files are published whole, so this is damage, not a torn write:
            # set it aside and fail closed.
            try:
                os.replace(path, path.with_name(path.name + ".unreadable"))
            except OSError:
                pass
            _write_gap_sentinel(root, "spool_replay", f"unreadable spool file {path.name}")
            result["unreadable"] += 1
            continue
        try:
            status = _commit_event_once(
                root, *args, event_id=event_id, open_wave=open_wave
            )[0]
        except Exception:
            result["kept"] += 1
            continue
        if status in {"durable", "duplicate"}:
            try:
                path.unlink()
            except OSError:
                # Already removed, or held open by another replayer on Windows;
                # the next pass sees a duplicate and removes it.
                pass
            result["replayed"] += 1
        else:
            result["kept"] += 1
    return result


def _spool_targets(record: Mapping[str, Any]) -> Optional[str]:
    focus = record.get("focus") or {}
    if isinstance(focus, Mapping) and focus.get("wave_id"):
        return str(focus["wave_id"])
    open_wave = record.get("open_wave")
    if open_wave:
        return str(open_wave[0])
    return None


def spooled_events_affecting(root: Path, wave_id: str) -> int:
    """Spooled events for ``wave_id``, or with no wave (general-bucket work a close adopts).

    An unreadable file counts, since its wave cannot be known.
    """

    count = 0
    for path in _spool_files(root):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            target = _spool_targets(record)
        except FileNotFoundError:
            continue
        except (OSError, ValueError, TypeError, AttributeError):
            count += 1
            continue
        if target is None or target == str(wave_id):
            count += 1
    return count


def mark_wave_accounting_gap(root: Path, wave_id: str) -> None:
    """Mark one wave's totals incomplete; creates its row when it has none."""

    def _attempt() -> None:
        conn = _open_write_store_once(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO wave_state("
                "wave_id,generation,pending,published_json,store_instance_id,"
                "measurement_status) VALUES(?,1,1,NULL,?,'accounting_gap')"
                " ON CONFLICT(wave_id) DO UPDATE SET "
                "measurement_status='accounting_gap',"
                "generation=generation+1,pending=1",
                (str(wave_id), _store_instance_id(conn)),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    _with_busy_retry(_attempt)


def _spool_health(root: Path) -> dict[str, Any]:
    files = _spool_files(root)
    oldest = None
    if files:
        stamp = files[0].name[:16]
        try:
            oldest = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.strptime(stamp, "%Y%m%dT%H%M%SZ")
            )
        except ValueError:
            oldest = None
    return {"spooled_events": len(files), "oldest_spooled_at": oldest}


class ProcessTelemetry:
    """Process focus plus write-through durable telemetry."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root).resolve() if root is not None else None
        self.producer_id = secrets.token_hex(16)
        self._lock = threading.RLock()
        self._focus = Focus()
        self._lease_handle: Any | None = None
        self._lease_attempted = False
        self._lease_reclaimable = False
        # Compatibility-only buffers for direct unit callers that do not bind a
        # root. The production ImplHandler always binds one.
        self._compat_retrieval: list[dict[str, Any]] = []
        self._compat_workflow: list[tuple[str, str, str, dict[str, Any]]] = []

    @property
    def focus(self) -> Focus:
        with self._lock:
            return self._focus

    def _ensure_lease(self) -> bool:
        if self.root is None:
            return False
        if not self._lease_attempted:
            self._lease_attempted = True
            handle, locked = _try_lock_lease(
                producer_lease_path(self.root, self.producer_id), create=True
            )
            self._lease_handle = handle
            self._lease_reclaimable = bool(locked)
        return self._lease_reclaimable

    def set_focus(
        self, wave_id: str, stage: str, *, new_phase: bool = False
    ) -> None:
        if str(stage) not in CANONICAL_STAGES:
            raise ValueError(
                f"stage must be one of {CANONICAL_STAGES}, got {stage!r}"
            )
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

    # Wave 1tmb3: ``pause_focus``/``reopen_focus`` (the retained "paused"
    # stage) were retired — a mutating pause's desired end state is NO focus,
    # so it uses ``clear_focus``; reopen mints fresh focus via ``set_focus``
    # with an explicit purpose-derived stage. Neither had another production
    # consumer.

    def clear_focus(self) -> None:
        with self._lock:
            self._focus = Focus()

    def close(self) -> None:
        with self._lock:
            _unlock_lease(self._lease_handle)
            self._lease_handle = None
            self._lease_reclaimable = False

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def record_tool_cost(
        self,
        tool_name: str,
        *,
        request_tokens: int,
        response_tokens: int,
        derived_artifact_tokens: int = 0,
        source_proofs: Optional[Iterable[SourceProof]] = None,
        focus_override: Focus | None = None,
        event_id: str,
    ) -> dict[str, Any]:
        """Wave 1t3ek (1t3s7/1t2zq): record a first-party tool call's cost, with
        optional avoided-writing credit (textual artifacts the tool persisted
        that the caller did not supply) and avoided-reading credit (state files
        the tool demonstrably read on the caller's behalf, measured through the
        canonical source-proof machinery with its once-only dedup). Never
        counterfactual: no proofs and zero artifact tokens means debit-only.
        Replays dedupe via ``event_id``."""
        metric: dict[str, Any] = {
            "estimated_request_tokens": int(max(0, request_tokens)),
            "estimated_returned_tokens": int(max(0, response_tokens)),
            "estimated_source_tokens": 0,
            "estimated_avoided_tokens": 0,
            "source_files_counted": 0,
            "source_files_verified": 0,
            "source_files_estimated": 0,
            "derived_artifact_tokens": int(max(0, derived_artifact_tokens)),
            "captured": True,
            "persistence": "pending",
            "method": RETRIEVAL_METHOD,
        }
        if source_proofs is not None and self.root is not None:
            try:
                measured = measure_source_proofs(self.root, source_proofs)
                metric["estimated_source_tokens"] = measured.estimated_source_tokens
                metric["source_files_counted"] = len(measured.candidates)
                metric["source_files_verified"] = measured.source_files_verified
                metric["source_files_estimated"] = measured.source_files_estimated
                metric["_source_credits"] = [
                    asdict(candidate) for candidate in measured.candidates
                ]
            except Exception:
                pass
        return self.record_retrieval(
            metric,
            tool_name=tool_name,
            focus_override=focus_override,
            event_id=event_id,
        )

    def record_retrieval(
        self,
        metric: Mapping[str, Any],
        *,
        tool_name: str = "retrieval",
        focus_override: Focus | None = None,
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
            reclaimable = self._ensure_lease()
            event_focus = (
                focus_override if focus_override is not None else self._focus
            )
            status, credited_tokens, credited_files, dropped_credits = _commit_event(
                self.root,
                self.producer_id,
                reclaimable,
                event_focus,
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
            reclaimable = self._ensure_lease()
            focus = self._focus
            if focus.wave_id != str(wave_id) or focus.stage != str(stage):
                phase_id = focus.phase_id or f"{stage}-1"
                focus = Focus(str(wave_id), str(stage), phase_id)
            status, _tokens, _files, _dropped = _commit_event(
                self.root,
                self.producer_id,
                reclaimable,
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
        transfer_stage: str = "plan",
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
                with self._lock:
                    self._ensure_lease()
                def _transfer_once() -> None:
                    conn = _open_write_store_once(self.root)
                    orphan_leases: dict[str, Any] = {}
                    claimed_orphans: set[str] = set()
                    committed = False
                    try:
                        for row in conn.execute(
                            "SELECT producer_id FROM producer_state "
                            "WHERE reclaimable=1 AND producer_id<>?",
                            (self.producer_id,),
                        ):
                            candidate = str(row[0])
                            handle, abandoned = _try_lock_lease(
                                producer_lease_path(self.root, candidate),
                                create=False,
                            )
                            if abandoned:
                                orphan_leases[candidate] = handle
                        conn.execute("BEGIN IMMEDIATE")
                        target = str(transfer_general_to)
                        moved = 0
                        for producer_id in (
                            self.producer_id,
                            *sorted(orphan_leases),
                        ):
                            if producer_id != self.producer_id:
                                eligible = conn.execute(
                                    "SELECT 1 FROM producer_state WHERE producer_id=? "
                                    "AND reclaimable=1",
                                    (producer_id,),
                                ).fetchone()
                                if eligible is None:
                                    continue
                            general_key = f"general:{producer_id}"
                            source_count = int(
                                conn.execute(
                                    "SELECT COUNT(*) FROM source_credit WHERE wave_key=?",
                                    (general_key,),
                                ).fetchone()[0]
                            )
                            conn.execute(
                                "INSERT OR IGNORE INTO source_credit("
                                "wave_key,phase_id,stage,source_id,version_id,tokens,"
                                "credit_kind,provenance) "
                                "SELECT ?,?,?,source_id,version_id,"
                                "tokens,credit_kind,provenance FROM source_credit "
                                "WHERE wave_key=?",
                                (target, transfer_stage, transfer_stage, general_key),
                            )
                            conn.execute(
                                "UPDATE source_credit SET provenance='both' "
                                "WHERE wave_key=? AND phase_id=? AND EXISTS("
                                "SELECT 1 FROM source_credit AS incoming "
                                "WHERE incoming.wave_key=? "
                                "AND incoming.source_id=source_credit.source_id "
                                "AND incoming.version_id=source_credit.version_id "
                                "AND incoming.credit_kind<>source_credit.credit_kind)",
                                (target, transfer_stage, general_key),
                            )
                            conn.execute(
                                "DELETE FROM source_credit WHERE wave_key=?",
                                (general_key,),
                            )
                            moved += source_count
                            moved += conn.execute(
                                "UPDATE telemetry_event SET wave_id=?,"
                                "phase_id=?,stage=?,attribution='adopted' "
                                "WHERE wave_id IS NULL AND producer_id=?",
                                (target, transfer_stage, transfer_stage, producer_id),
                            ).rowcount
                            if producer_id != self.producer_id:
                                conn.execute(
                                    "DELETE FROM producer_state WHERE producer_id=?",
                                    (producer_id,),
                                )
                                claimed_orphans.add(producer_id)
                        if moved:
                            _touch_wave(conn, target)
                            touched.add(target)
                        conn.commit()
                        committed = True
                    except Exception:
                        conn.rollback()
                        raise
                    finally:
                        conn.close()
                        for producer_id, handle in orphan_leases.items():
                            _unlock_lease(handle)
                            if committed and producer_id in claimed_orphans:
                                try:
                                    producer_lease_path(
                                        self.root, producer_id
                                    ).unlink()
                                except OSError:
                                    pass
                _with_busy_retry(_transfer_once)
            return FlushResult(
                True, "durable", touched_waves=frozenset(touched)
            )
        except Exception as exc:
            poisoned = _write_gap_sentinel(Path(root), "flush", exc)
            return FlushResult(
                False,
                "poisoned" if poisoned else "failed",
                error=f"{type(exc).__name__}: {exc}",
            )


def _gap_health(reason: Optional[Mapping[str, str]]) -> dict[str, Optional[str]]:
    health: dict[str, Optional[str]] = {
        "status": "accounting_gap",
        "diagnostic": _gap_diagnostic(reason),
    }
    for key in ("recorded_at", "operation", "error_type", "message"):
        health[f"gap_{key}"] = (reason or {}).get(key) or None
    return health


def read_store_health(root: Path) -> dict[str, Any]:
    """Store health; spooled events are reported beside the status, never as one."""

    health: dict[str, Any] = dict(_read_store_health_core(root))
    health.update(_spool_health(root))
    return health


def _read_store_health_core(root: Path) -> dict[str, Optional[str]]:
    path = store_path(root)
    reason = read_gap_reason(root)
    if reason is not None:
        return _gap_health(reason)
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
            return _gap_health(None)
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
    "derived_artifact_credit",
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
        "SELECT generation,pending,measurement_status,floor_json,"
        "compacted_generation,sealed FROM wave_state"
        " WHERE wave_id=?",
        (wave_id,),
    ).fetchone()
    if state:
        if state[3]:
            try:
                floor = json.loads(str(state[3]))
                snapshot = _normalized_checkpoint_state(floor)
                snapshot["wave_id"] = wave_id
            except (TypeError, ValueError, json.JSONDecodeError):
                snapshot["measurement_status"] = "failed"
        snapshot["generation"] = int(state[0])
        snapshot["pending"] = bool(state[1])
        snapshot["measurement_status"] = str(state[2] or "healthy")
        snapshot["store_instance_id"] = _store_instance_id(conn)
    if _accounting_gap(conn):
        snapshot["measurement_status"] = "accounting_gap"
    elif not state:
        snapshot["measurement_status"] = "healthy"
    stages: set[str] = set(snapshot["stages"])
    stages.update({
        str(row[0])
        for row in conn.execute(
            "SELECT DISTINCT stage FROM telemetry_event WHERE wave_id=?",
            (wave_id,),
        )
    })
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
    for stage_name in sorted(
        stages, key=lambda s: (_CANONICAL_STAGE_ORDER.get(s, len(CANONICAL_STAGES)), s)
    ):
        values = dict(
            snapshot["stages"].get(stage_name, _empty_stage_totals())
        )
        event_row = conn.execute(
            "SELECT COUNT(*),COALESCE(SUM(request_tokens),0),"
            "COALESCE(SUM(response_tokens),0),"
            "COALESCE(SUM(workflow_prompt_tokens),0),"
            "COALESCE(SUM(source_credits_dropped),0),"
            "COALESCE(SUM(derived_artifact_tokens),0) "
            "FROM telemetry_event WHERE wave_id=? AND stage=?",
            (wave_id, stage_name),
        ).fetchone()
        values["calls"] += int(event_row[0])
        values["request_debit"] += int(event_row[1])
        values["response_debit"] += int(event_row[2])
        values["workflow_prompt_credit"] += int(event_row[3])
        values["source_credit_drop_count"] += int(event_row[4])
        values["derived_artifact_credit"] += int(event_row[5])
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
        values["matched_pair_residual"] += int(residual[0]) if residual else 0
        values["paired_evaluation_count"] += int(residual[1]) if residual else 0
        values["direct_net"] = (
            values["content_source_credit"]
            + values["structural_source_credit"]
            + values["workflow_prompt_credit"]
            + values["derived_artifact_credit"]
            - values["request_debit"]
            - values["response_debit"]
        )
        if snapshot["measurement_status"] == "healthy":
            values["estimated_tokens_saved"] = max(
                0, values["direct_net"] + values["matched_pair_residual"]
            )
        snapshot["stages"][stage_name] = values
    snapshot["totals"] = _empty_stage_totals()
    for values in snapshot["stages"].values():
        for key in _STAGE_KEYS:
            snapshot["totals"][key] += int(values[key])
    totals = snapshot["totals"]
    totals["direct_net"] = (
        totals["content_source_credit"]
        + totals["structural_source_credit"]
        + totals["workflow_prompt_credit"]
        + totals["derived_artifact_credit"]
        - totals["request_debit"]
        - totals["response_debit"]
    )
    # Reconcile the total with the displayed rows (1sx2f): the total savings is
    # the SUM of the per-stage floored savings (each already max(0, ...) above),
    # which `totals["estimated_tokens_saved"]` accumulated in the stage loop, so
    # a net-negative stage counts as 0 and the stages always add up to the total.
    # Zero it when measurement is not healthy.
    if snapshot["measurement_status"] != "healthy":
        totals["estimated_tokens_saved"] = 0
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
                    "SELECT wave_id FROM wave_state WHERE pending=1 "
                    "OR (sealed=1 AND compacted_generation<generation) "
                    "ORDER BY wave_id"
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
    root: Path,
    wave_id: str,
    checkpoint: Mapping[str, Any],
    *,
    sealed: bool = False,
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
                if sealed:
                    restored = _normalized_checkpoint_state(checkpoint)
                    restored["store_instance_id"] = current
                    restored["pending"] = False
                    generation = max(0, int(restored.get("generation", 0)))
                    payload = canonical_core_json(restored)
                    conn.execute(
                        "INSERT INTO wave_state("
                        "wave_id,generation,pending,published_json,store_instance_id,"
                        "measurement_status,floor_json,compacted_generation,sealed"
                        ") VALUES(?,?,0,?,?,'healthy',?,?,1)"
                        " ON CONFLICT(wave_id) DO UPDATE SET "
                        "generation=excluded.generation,pending=0,"
                        "published_json=excluded.published_json,"
                        "store_instance_id=excluded.store_instance_id,"
                        "measurement_status='healthy',floor_json=excluded.floor_json,"
                        "compacted_generation=excluded.compacted_generation,sealed=1",
                        (
                            str(wave_id),
                            generation,
                            payload,
                            current,
                            payload,
                            generation,
                        ),
                    )
                else:
                    conn.execute(
                        "INSERT INTO wave_state("
                        "wave_id,generation,pending,published_json,store_instance_id,"
                        "measurement_status) "
                        "VALUES(?,0,0,NULL,?,'credit_history_unavailable')"
                        " ON CONFLICT(wave_id) DO UPDATE SET "
                        "measurement_status='credit_history_unavailable'",
                        (str(wave_id), current),
                    )
            conn.commit()
            return current == published_instance or sealed
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
    seal: bool = False,
) -> bool:
    try:
        conn = _open_write_store(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            changed = conn.execute(
                "UPDATE wave_state SET pending=0,published_json=?,"
                "store_instance_id=?,sealed=? WHERE wave_id=? AND generation=?",
                (
                    canonical_core_json(dict(snapshot)),
                    str(snapshot.get("store_instance_id", "")),
                    int(seal),
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


def compact_published_wave(
    root: Path, wave_id: str, *, expected_generation: int
) -> bool:
    """Replace a sealed wave's raw ledger with its cumulative published floor."""

    conn: sqlite3.Connection | None = None
    try:
        conn = _open_write_store(root)
        conn.execute("BEGIN IMMEDIATE")
        state = conn.execute(
            "SELECT generation,pending,published_json,sealed "
            "FROM wave_state WHERE wave_id=?",
            (str(wave_id),),
        ).fetchone()
        if (
            state is None
            or int(state[0]) != int(expected_generation)
            or bool(state[1])
            or not state[2]
            or not bool(state[3])
        ):
            conn.rollback()
            return False
        conn.execute(
            "UPDATE wave_state SET floor_json=published_json,"
            "compacted_generation=generation WHERE wave_id=?",
            (str(wave_id),),
        )
        conn.execute(
            "INSERT OR IGNORE INTO event_tombstone(event_id,wave_id) "
            "SELECT event_id,? FROM telemetry_event WHERE wave_id=?",
            (str(wave_id), str(wave_id)),
        )
        conn.execute("DELETE FROM telemetry_event WHERE wave_id=?", (str(wave_id),))
        conn.execute("DELETE FROM source_credit WHERE wave_key=?", (str(wave_id),))
        conn.execute(
            "DELETE FROM evaluation_attachment WHERE wave_id=?", (str(wave_id),)
        )
        conn.execute("DELETE FROM evaluation_scope WHERE wave_id=?", (str(wave_id),))
        # Exploration-credit rows are the durable authority for the separately
        # labeled estimate and its event/origin idempotency.  They are not raw
        # retrieval telemetry, so retain them across wave compaction.
        conn.execute("DELETE FROM phase_state WHERE wave_id=?", (str(wave_id),))
        conn.commit()
        return True
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
        return False
    finally:
        if conn is not None:
            conn.close()


def unseal_wave(root: Path, wave_id: str) -> bool:
    """Allow a reopened wave to accept a new raw phase above its compacted floor."""

    conn: sqlite3.Connection | None = None
    try:
        conn = _open_write_store(root)
        conn.execute("BEGIN IMMEDIATE")
        changed = conn.execute(
            "UPDATE wave_state SET sealed=0 WHERE wave_id=?",
            (str(wave_id),),
        ).rowcount
        conn.commit()
        return bool(changed)
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
        return False
    finally:
        if conn is not None:
            conn.close()


def _normalized_checkpoint_state(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    state = empty_checkpoint(str(snapshot.get("wave_id", "")))
    state["generation"] = max(0, int(snapshot.get("generation", 0)))
    state["pending"] = bool(snapshot.get("pending", False))
    state["store_instance_id"] = str(snapshot.get("store_instance_id", ""))
    status = str(snapshot.get("measurement_status", "unmeasured"))
    state["measurement_status"] = status
    stages = snapshot.get("stages", {})
    if isinstance(stages, Mapping):
        for name in sorted(
            stages,
            key=lambda s: (_CANONICAL_STAGE_ORDER.get(s, len(CANONICAL_STAGES)), s),
        ):
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
        + totals["derived_artifact_credit"]
        - totals["request_debit"]
        - totals["response_debit"]
    )
    # See 1sx2f: the total savings is the sum of the per-stage floored savings
    # (accumulated in the stage loop above), so the stages reconcile with the
    # total and a net-negative stage counts as 0. Zero when not healthy.
    if state["measurement_status"] != "healthy":
        totals["estimated_tokens_saved"] = 0
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


_CHECKPOINT_ESTIMATE_NOTE = (
    "Estimated context avoided uses whole eligible text-file, workflow-prompt "
    "and derived-artifact credits, minus recorded request and response tokens. "
    "This baseline does not prove what an agent otherwise would have read or "
    "spent. Any quality-equivalent paired-evaluation residual is recorded "
    "separately in the checkpoint state and included in the total."
)
_LEGACY_CHECKPOINT_ESTIMATE_NOTE = (
    "Estimated token savings use phase-unique returned source versions "
    "and mapped workflow prompts, minus recorded request and response "
    "tokens. Saved model output or avoided tool loops count only through "
    "quality-equivalent paired evidence."
)


def render_checkpoint_block(snapshot: Mapping[str, Any]) -> str:
    state = _normalized_checkpoint_state(snapshot)
    status = state["measurement_status"]
    lines = [
        "## Context Efficiency",
        "",
        CONTEXT_EFFICIENCY_MARKER_BEGIN,
        "",
        _CHECKPOINT_ESTIMATE_NOTE,
        "",
        "| Stage | Tool calls | Estimated context avoided |",
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
        expected = render_checkpoint_block(state)
        # Accept the exact prior presentation without rewriting archived waves
        # or weakening the state/numeric consistency check.
        legacy = expected.replace(
            _CHECKPOINT_ESTIMATE_NOTE, _LEGACY_CHECKPOINT_ESTIMATE_NOTE
        ).replace(
            "| Stage | Tool calls | Estimated context avoided |",
            "| Stage | Tool calls | Estimated token savings |",
        )
        if expected not in canonical and legacy not in canonical:
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
    heading = "## Context Efficiency\n\n"
    heading_start = start - len(heading)
    if (
        heading_start >= 0
        and canonical[heading_start:start] == heading
        and (heading_start == 0 or canonical[heading_start - 1] == "\n")
    ):
        start = heading_start
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
        "COALESCE(SUM(workflow_prompt_tokens),0),"
        "COALESCE(SUM(derived_artifact_tokens),0) "
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
        + int(event[3] if event else 0)
        - int(event[0] if event else 0)
        - int(event[1] if event else 0)
    )


def registered_applicability(
    root: Path, wave_id: str, phase_id: str
) -> Optional[dict[str, str]]:
    """Read-only: the applicability registered for (wave, phase), or None."""
    path = store_path(root)
    if not Path(path).exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT applicability_json FROM evaluation_scope"
                " WHERE wave_id=? AND phase_id=?",
                (str(wave_id), str(phase_id)),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    if not row:
        return None
    try:
        loaded = json.loads(row[0])
    except ValueError:
        return None
    return loaded if isinstance(loaded, dict) else None


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
        sealed = conn.execute(
            "SELECT sealed FROM wave_state WHERE wave_id=?", (str(wave_id),)
        ).fetchone()
        if sealed is not None and bool(sealed[0]):
            raise ValueError("closed wave telemetry is sealed; reopen the wave first")
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


def _non_closed_wave_ids(root: Path) -> list[str]:
    """Wave folder names whose ``Status:`` is not closed; unreadable counts as open."""

    if not record_paths.load_record_roots(Path(root)).waves.is_dir():
        return []
    wave_ids: list[str] = []
    for entry in record_paths.discover_wave_dirs(Path(root)):
        try:
            head = (entry / "wave.md").read_text(encoding="utf-8", errors="replace")[:2048]
        except OSError:
            head = ""
        if _wave_status_from_text(head) != "closed":
            wave_ids.append(entry.name)
    return sorted(wave_ids)


def clear_accounting_gap(root: Path) -> dict[str, Any]:
    """Operator action: lift the store-wide gap, keeping affected waves marked.

    Every unsealed wave, and every wave folder that is not closed (its first
    telemetry may have been refused during the gap, leaving no row), is marked
    ``accounting_gap`` so its published totals never read as complete. The
    sentinel is set aside and the meta flag deleted in one write transaction;
    a failure recorded after the set-aside writes a fresh sentinel that stays.
    Events that failed without being spooled are not backfilled; events still
    in the spool replay after the clear. The general running total
    resumes from the clear.
    """

    root = Path(root)
    sentinel = gap_path(root)
    aside = sentinel.with_name(sentinel.name + ".clearing")
    store = store_path(root)
    # What was present before anything is opened for writing: a write open
    # copies the gap file into the store flag, so it cannot tell them apart.
    result: dict[str, Any] = {
        "cleared": False,
        "found": {
            "gap_file": sentinel.exists(),
            "store_flag": _read_store_gap_flag(root),
        },
        "reason": None,
        "marked_waves": [],
        "new_gap_recorded": False,
    }
    if not (sentinel.exists() or aside.exists() or store.is_file()):
        return result
    wave_ids = _non_closed_wave_ids(root)

    def _set_aside(gap_in_store: bool) -> bool:
        if sentinel.exists():
            _replace_with_retry(sentinel, aside)
            return True
        # A set-aside file with no live flag is left over from a clear that
        # already committed; it is not a gap.
        return aside.exists() and gap_in_store

    def _attempt() -> None:
        if not store.is_file():
            if _set_aside(False):
                result["reason"] = _read_reason_file(aside)
                result["cleared"] = True
            return
        conn = _open_write_store_once(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            flag = _accounting_gap(conn)
            had_sentinel = _set_aside(flag)
            if not (flag or had_sentinel):
                conn.rollback()
                return
            result["reason"] = _read_reason_file(aside) if had_sentinel else None
            for wave_id in wave_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO wave_state("
                    "wave_id,generation,pending,published_json,store_instance_id,"
                    "measurement_status) VALUES(?,0,0,NULL,?,'healthy')",
                    (wave_id, _store_instance_id(conn)),
                )
            marked = [
                str(row[0])
                for row in conn.execute(
                    "SELECT wave_id FROM wave_state WHERE sealed=0 ORDER BY wave_id"
                )
            ]
            conn.execute(
                "UPDATE wave_state SET measurement_status='accounting_gap',"
                "generation=generation+1,pending=1 WHERE sealed=0"
            )
            conn.execute("DELETE FROM meta WHERE key='accounting_gap'")
            conn.commit()
            result["cleared"] = True
            result["marked_waves"] = marked
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    try:
        _with_busy_retry(_attempt)
    except Exception:
        # Put an uncleared reason back unless a newer failure already wrote one.
        if aside.exists() and not sentinel.exists():
            _replace_with_retry(aside, sentinel)
        raise
    try:
        aside.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass  # the clear committed; a leftover set-aside file is ignored later
    # A failure recorded while the clear ran leaves a fresh gap in force.
    result["new_gap_recorded"] = sentinel.exists()
    return result


def _read_store_gap_flag(root: Path) -> bool:
    """Read the store's gap flag without the write open's sentinel copy."""

    conn = _open_read_store(root)
    if conn is None:
        return False
    try:
        return _accounting_gap(conn)
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def _read_reason_file(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8").strip()
        record = json.loads(text.splitlines()[0]) if text else {}
    except (OSError, ValueError, IndexError):
        return {}
    if not isinstance(record, dict):
        return {}
    return {key: str(value) for key, value in record.items()}


def _default_root() -> Path:
    """The repository containing this framework: <repo>/.wavefoundry/framework/scripts/."""

    return Path(__file__).resolve().parents[3]


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Context-efficiency telemetry maintenance."
    )
    parser.add_argument(
        "--root",
        default=None,
        help="repository root (default: the repository containing this framework)",
    )
    parser.add_argument(
        "--clear-gap",
        action="store_true",
        required=True,
        help="clear the durable accounting gap; waves it affected stay marked",
    )
    args = parser.parse_args(argv)
    try:
        root = Path(args.root) if args.root else _default_root()
        result = clear_accounting_gap(root.resolve())
    except Exception as exc:
        print(json.dumps({"cleared": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 1
    if result.get("new_gap_recorded"):
        result["note"] = (
            "A new accounting gap was recorded while clearing; it remains in"
            " force. Check its reason before clearing again."
        )
    elif result["cleared"]:
        result["note"] = (
            "Marked waves keep an accounting_gap projection; events that failed"
            " without being spooled are not backfilled (spooled ones replay), and"
            " the general running total resumes now."
        )
    else:
        result["note"] = "No accounting gap was present; nothing changed."
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
