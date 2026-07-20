"""Executable-review event authority, validation, proof, and projection helpers.

Runtime state lives only in a wave's fixed sibling ``events.jsonl``. The validator is
semantic-fact agnostic: it does not decide whether a finding is true or approve a wave;
it validates canonical bytes and relationships, derives actionability from the
moderator's finite facts, and renders the rebuildable Markdown current-state view.

The inline protocol parser remains only for the one-time pre-release self-host
migration. Runtime lifecycle callers never fall back to it. Unmarked pre-protocol
consumer waves remain prose-only legacy records and are not rewritten by upgrade.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from runtime_lock import RuntimeFileLock


PROTOCOL_VERSION = 1
FINDING_SYNTHESIS_MARKER_BEGIN = "<!-- wave:finding-synthesis begin -->"
FINDING_SYNTHESIS_MARKER_END = "<!-- wave:finding-synthesis end -->"
REVIEW_STATUS_MARKER_BEGIN = "<!-- wave:review-status begin -->"
REVIEW_STATUS_MARKER_END = "<!-- wave:review-status end -->"
_LEGACY_FINDING_SYNTHESIS_MARKER_BEGIN = (
    "<!-- waveframework:finding-synthesis begin -->"
)
_LEGACY_FINDING_SYNTHESIS_MARKER_END = (
    "<!-- waveframework:finding-synthesis end -->"
)
REVIEW_EVIDENCE_DETAILS_BEGIN = '<details class="wavefoundry-review-evidence">'
REVIEW_EVIDENCE_DETAILS_END = "</details>"
ADOPTION_LEDGER_REL = Path("docs/waves/review-evidence-adoptions.json")
ADOPTION_LOCK_REL = Path(".wavefoundry/locks/review-evidence-adoptions.lock")
EVENTS_FILENAME = "events.jsonl"
REVIEW_EVIDENCE_SOURCE = EVENTS_FILENAME
REVIEW_EVIDENCE_SOURCE_DECLARATION = f"review-evidence-source: {REVIEW_EVIDENCE_SOURCE}"
REVIEW_EVENT_HASH_DOMAIN = b"wavefoundry-review-events\0"
EVENT_IDENTITY_FIELD = "event_identity"
REQUEST_DIGEST_FIELD = "request_digest"

_WRITE_THREAD_LOCK = threading.RLock()
_WRITE_LOCK_STATE = threading.local()

_MARKER_RE = re.compile(
    r"(?mi)^review-evidence-protocol:\s*`?(?P<version>\d+)`?\s*$"
)
_SOURCE_LINE_RE = re.compile(
    r"(?mi)^review-evidence-source:[ \t]*(?P<source>[^ \t\r\n]+)[ \t]*$"
)
_LIFECYCLE_PREFIX_RE = re.compile(r"^(?P<prefix>[0-9a-z]{5,6})(?:[-\s])")
_SECTION_RE = re.compile(
    r"(?ms)^## Finding Synthesis\s*$\n(?P<body>.*?)(?=^##\s|\Z)"
)
_JSONL_FENCE_RE = re.compile(
    r"(?ms)^```jsonl\s*$\n(?P<body>.*?)^```\s*$"
)


def _canonicalize_finding_synthesis_markers(text: str) -> str:
    """Accept legacy projections while emitting only the canonical namespace."""

    return text.replace(
        _LEGACY_FINDING_SYNTHESIS_MARKER_BEGIN,
        FINDING_SYNTHESIS_MARKER_BEGIN,
    ).replace(
        _LEGACY_FINDING_SYNTHESIS_MARKER_END,
        FINDING_SYNTHESIS_MARKER_END,
    )


def canonicalize_finding_synthesis_markers(text: str) -> str:
    """Normalize marker spelling for validation without rewriting historical files."""

    return _canonicalize_finding_synthesis_markers(text)

RUN_KINDS = frozenset(
    {"readiness", "initial_delivery", "repair_start", "reverification", "convergence_checkpoint"}
)
EVIDENCE_PHASES = frozenset({"readiness", "delivery"})
EVIDENCE_STATUSES = frozenset({"executed", "inferred", "unverified", "not_applicable"})
EVIDENCE_CLAIM_KINDS = frozenset(
    {"finding", "approval", "dedup", "lane_reassessment", "census"}
)
PROBE_CLASSES = frozenset({"local_safe", "external_or_destructive", "none"})
AUTHORIZATION_STATUSES = frozenset({"authorized", "not_authorized", "not_required"})
VALIDATION_STATUSES = frozenset({"invalid", "conforming", "real"})
SCOPE_RELATIONS = frozenset({"admitted", "adjacent", "outside"})
CONTRACT_RELEVANCES = frozenset({"none", "important_ac", "required_ac", "public_contract"})
TRISTATE = frozenset({False, True, "unverified"})
AUTHORITY_DOMAINS = frozenset(
    {"none", "confidentiality", "integrity", "availability", "privilege", "unverified"}
)
AUTHORITY_DELTAS = frozenset({"none", "low", "material", "critical", "unverified"})
OBSERVABLE_IMPACTS = frozenset({"none", "low", "material", "critical", "unverified"})
CONTAINMENTS = frozenset({"preventive", "impact_bounding", "detect_only", "none", "unverified"})
FIX_RISKS = frozenset({"lower", "comparable", "higher", "unverified"})
OPTIONAL_VALUES = frozenset({"none", "positive", "unverified"})
REPAIR_SCOPE_BOUNDED = TRISTATE
REPAIR_SAFETIES = frozenset({"safe", "unsafe", "unverified"})
BENEFIT_VS_FIX_RISKS = frozenset({"greater", "equal", "less", "unverified"})
REJECTION_BASES = frozenset(
    {"none", "categorical", "insufficient_evidence", "unsupported_reachability", "disproportionate_repair"}
)
DISPOSITIONS = frozenset({"do_now", "maybe_later", "dont_do_later", "not_issue"})
DECISION_AUTHORITIES = frozenset({"moderator", "required_specialist", "operator"})
REVIEW_DEPTHS = frozenset({"none", "focused", "full"})
REPAIR_EXECUTION_STATES = frozenset({"not_required", "pending", "completed", "operator_waived"})

FULL_COUNCIL_TRIGGERS = (
    "contract_or_required_ac_semantics_changed",
    "trust_boundary_changed",
    "architecture_or_ownership_changed",
    "cross_component_protocol_or_state_changed",
    "failure_or_readiness_semantics_changed",
)

_RUN_REQUIRED = frozenset(
    {
        "record_type",
        "review_run_id",
        "run_kind",
        "cycle",
        "candidate_finding_ids",
        "source_record_ids",
        "dedup_evidence_id",
    }
)
_RUN_OPTIONAL = frozenset(
    {
        "frozen_boundary",
        "deviation_ids",
        "reopened_finding_ids",
        "verification_context",
        EVENT_IDENTITY_FIELD,
        REQUEST_DIGEST_FIELD,
    }
)

_EVIDENCE_REQUIRED = frozenset(
    {
        "record_type",
        "evidence_record_id",
        "claim_id",
        "claim_kind",
        "required_for_approval",
        "phase",
        "proposition",
        "counterexample_or_failure_condition",
        "execution_status",
        "public_path",
        "command_or_fixture",
        "expected",
        "observed",
        "artifact_or_test_id",
        "adjacent_controls",
        "test_ran_without_unintended_skip",
        "public_path_reached",
        "boundary_values_realistic",
        "assertions_non_vacuous",
        "known_bad_detected",
        "known_bad_detection_method",
        "limitations",
        "safety_and_authorization",
        "probe_class",
        "authorization_status",
        "safe_boundary",
        "unexecuted_remainder_prohibited",
        "universal_claim",
        "verification_context",
    }
)
_EVIDENCE_OPTIONAL = frozenset(
    {"census", EVENT_IDENTITY_FIELD, REQUEST_DIGEST_FIELD}
)
_VERIFICATION_CONTEXT_REQUIRED = frozenset(
    {"actor", "context_id", "fresh_context", "independent"}
)
_CENSUS_REQUIRED = frozenset(
    {
        "claim",
        "boundary",
        "inclusion_policy",
        "tools_and_queries",
        "enumerated_sites",
        "total_count",
        "registration_checks",
        "exclusions",
        "result_truncated",
        "index_freshness",
        "tool_errors",
        "residual_uncertainty",
        "residual_uncertainty_status",
        "universe_closed",
    }
)

_SYNTHESIS_REQUIRED = frozenset(
    {
        "record_type",
        "record_id",
        "review_run_id",
        "cycle",
        "finding_id",
        "validation_status",
        "scope_relation",
        "introduced_or_worsened_by_wave",
        "contract_relevance",
        "supported_reachability",
        "attacker_reachability",
        "authority_domain",
        "authority_delta",
        "observable_impact",
        "containment",
        "fix_risk",
        "optional_value",
        "repair_scope_bounded",
        "repair_safety",
        "benefit_vs_fix_risk",
        "rejection_basis",
        "disposition",
        "blocking",
        "source_lanes",
        "blocking_required_lanes",
        *FULL_COUNCIL_TRIGGERS,
        "review_depth",
        "repair_execution_state",
        "evidence_record_id",
        "decision_authority",
        "disposition_rationale",
    }
)
_SYNTHESIS_OPTIONAL = frozenset(
    {
        "supersedes_record_id",
        "lane_reassessment_evidence_id",
        "approval_recheck_lanes",
        "promotion_trigger",
        "waiver_id",
        "waiver_scope",
        "waiver_reason",
        "waiver_risk",
        "follow_on_id",
    }
)

CENSUS_FRESHNESS = frozenset({"current", "stale", "unknown"})
CENSUS_UNCERTAINTY = frozenset({"none", "bounded", "unresolved"})


@dataclass(frozen=True)
class ReviewEvidenceValidation:
    marker_version: int | None
    records: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]
    authority_errors: tuple[str, ...] = ()
    projection_errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors


class _DuplicateJSONKey(ValueError):
    pass


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateJSONKey(f"duplicate object key {key!r}")
        value[key] = item
    return value


def canonical_review_event_bytes(record: Mapping[str, Any]) -> bytes:
    """Return the one canonical UTF-8 JSONL record representation."""

    if not isinstance(record, Mapping):
        raise TypeError("review event record must be an object")
    return (
        json.dumps(
            dict(record),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_review_events_bytes(records: Iterable[Mapping[str, Any]]) -> bytes:
    """Serialize an ordered event ledger without materializing another format."""

    return b"".join(canonical_review_event_bytes(record) for record in records)


def parse_review_event_bytes(data: bytes) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    """Parse canonical ledger bytes, rejecting every non-canonical representation."""

    errors: list[str] = []
    if data.startswith(b"\xef\xbb\xbf"):
        return (), ("events.jsonl must not contain a UTF-8 BOM",)
    if b"\r" in data:
        return (), ("events.jsonl must use LF line endings; CR/CRLF bytes are forbidden",)
    if data and not data.endswith(b"\n"):
        return (), ("events.jsonl must end with a final LF",)
    physical_lines = data.split(b"\n")
    if physical_lines and physical_lines[-1] == b"":
        physical_lines.pop()
    records: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(physical_lines, 1):
        if not raw_line:
            errors.append(f"events.jsonl line {line_number}: blank physical lines are forbidden")
            continue
        try:
            line = raw_line.decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"events.jsonl line {line_number}: invalid UTF-8 ({exc.reason})")
            continue
        try:
            value = json.loads(
                line,
                object_pairs_hook=_object_without_duplicate_keys,
                parse_constant=lambda token: (_ for _ in ()).throw(
                    ValueError(f"non-finite number {token}")
                ),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"events.jsonl line {line_number}: invalid JSON ({exc})")
            continue
        if not isinstance(value, dict):
            errors.append(f"events.jsonl line {line_number}: record must be an object")
            continue
        try:
            canonical = canonical_review_event_bytes(value)
        except (TypeError, ValueError) as exc:
            errors.append(f"events.jsonl line {line_number}: invalid canonical value ({exc})")
            continue
        if canonical != raw_line + b"\n":
            errors.append(
                f"events.jsonl line {line_number}: record is not in canonical JSON serialization"
            )
            continue
        records.append(value)
    if errors:
        return (), tuple(errors)
    return tuple(records), ()


def review_event_path(wave_path: Path) -> Path:
    """Resolve the fixed sibling authority from a wave directory or ``wave.md``."""

    path = Path(wave_path)
    if path.name == "wave.md":
        return path.parent / EVENTS_FILENAME
    if path.suffix:
        raise ValueError("review event authority is resolved only from a wave directory or wave.md")
    return path / EVENTS_FILENAME


def _review_authority_path_error(wave_path: Path) -> str | None:
    """Reject symlinked/out-of-wave review authority before any read or write."""

    wave_md = Path(wave_path)
    if wave_md.name != "wave.md":
        wave_md = wave_md / "wave.md"
    wave_dir = wave_md.parent
    ledger = wave_dir / EVENTS_FILENAME
    try:
        if wave_dir.is_symlink():
            return "wave directory may not be a symlink"
        wave_real = wave_dir.resolve(strict=True)
        if wave_md.is_symlink():
            return "wave.md may not be a symlink"
        if wave_md.exists() and not wave_md.resolve(strict=True).is_relative_to(wave_real):
            return "wave.md escapes its wave directory"
        if ledger.is_symlink():
            return "events.jsonl may not be a symlink"
        if ledger.exists() and not ledger.resolve(strict=True).is_relative_to(wave_real):
            return "events.jsonl escapes its wave directory"
    except (OSError, RuntimeError) as exc:
        return f"review authority path is not safely resolvable: {exc}"
    return None


def parse_review_evidence_source(text: str) -> tuple[str | None, tuple[str, ...]]:
    """Read the exact unversioned source declaration from the wave header."""

    header_end = text.find("\n## ")
    header = text if header_end < 0 else text[:header_end]
    matches = list(_SOURCE_LINE_RE.finditer(header))
    if not matches:
        return None, ()
    if len(matches) != 1:
        return None, ("review evidence source declaration must appear exactly once",)
    source = matches[0].group("source")
    if source != REVIEW_EVIDENCE_SOURCE:
        return source, (
            f"review evidence source must be exactly `{REVIEW_EVIDENCE_SOURCE_DECLARATION}`",
        )
    if matches[0].group(0) != REVIEW_EVIDENCE_SOURCE_DECLARATION:
        return source, (
            f"review evidence source must be exactly `{REVIEW_EVIDENCE_SOURCE_DECLARATION}`",
        )
    return source, ()


def review_event_prefix_proof(
    records: Iterable[Mapping[str, Any]], count: int | None = None
) -> dict[str, Any]:
    """Return the bounded count/hash proof over an exact canonical prefix."""

    rows = tuple(dict(record) for record in records)
    if count is None:
        count = len(rows)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > len(rows):
        raise ValueError("prefix proof count must be between zero and the record count")
    prefix = canonical_review_events_bytes(rows[:count])
    return {
        "record_count": count,
        "prefix_sha256": hashlib.sha256(REVIEW_EVENT_HASH_DOMAIN + prefix).hexdigest(),
    }


def _lifecycle_prefix(wave_key: str) -> str:
    match = _LIFECYCLE_PREFIX_RE.match(wave_key)
    if match is None:
        raise ValueError("wave key must begin with a canonical 5- or 6-character lifecycle ID")
    return match.group("prefix")


def derive_review_event_identity(wave_key: str, event: Mapping[str, Any]) -> dict[str, Any]:
    """Derive the delimiter-safe idempotency identity for one compact event."""

    event_kind = event.get("event")
    actor = event.get("actor")
    context_id = event.get("context_id")
    if event_kind not in {"approval", "finding", "run"}:
        raise ValueError("event must be one of: approval, finding, run")
    if not _nonempty_string(actor) or not _nonempty_string(context_id):
        raise ValueError("actor and context_id must be non-empty strings")
    identity: dict[str, Any] = {
        "wave_id": _lifecycle_prefix(wave_key),
        "event": event_kind,
        "actor": actor,
        "context_id": context_id,
    }
    if event_kind == "approval":
        if not _nonempty_string(event.get("signoff_key")):
            raise ValueError("approval event requires signoff_key")
        identity["signoff_key"] = event["signoff_key"]
    elif event_kind == "finding":
        if not _nonempty_string(event.get("finding_id")):
            raise ValueError("finding event requires finding_id")
        identity.update(
            finding_id=event["finding_id"],
            run_kind=event.get("run_kind"),
            cycle=event.get("cycle"),
        )
    else:
        identity.update(run_kind=event.get("run_kind"), cycle=event.get("cycle"))
    return identity


_SEMANTIC_SET_FIELDS = frozenset(
    {
        "source_lanes",
        "blocking_required_lanes",
        "approval_recheck_lanes",
        "review_boundaries_changed",
        "frozen_boundary",
    }
)


def normalize_review_event_request(event: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize compact semantic input for stable response-loss comparison."""

    normalized = dict(event)
    normalized.pop("mode", None)
    normalized.setdefault("fresh_context", False)
    normalized.setdefault("independent", False)
    event_kind = normalized.get("event")
    if event_kind in {"approval", "finding"}:
        normalized.setdefault("adjacent_controls", [])
    if event_kind == "approval":
        signoff_key = normalized.get("signoff_key")
        artifact = normalized.get("artifact_or_test_id")
        normalized.setdefault(
            "proposition", f"{signoff_key} approves the current affected scope"
        )
        normalized.setdefault(
            "failure_condition",
            "the approval predates an affected repair or is not independently grounded",
        )
        normalized.setdefault("public_path", "wave_record_review_evidence")
        normalized.setdefault("command_or_fixture", artifact)
        normalized.setdefault(
            "expected", "the approving actor independently verifies the current affected scope"
        )
        normalized.setdefault(
            "known_bad_detection_method",
            "approval evidence and affected-lane chronology were checked",
        )
        normalized.setdefault(
            "limitations",
            "Approval remains scoped to the recorded actor and affected review boundary.",
        )
        normalized.setdefault(
            "safety_and_authorization",
            "Local review evidence only; no external side effects.",
        )
    if event_kind == "finding":
        normalized.setdefault("execution_status", "executed")
        normalized.setdefault("probe_class", "local_safe")
        normalized.setdefault("authorization_status", "not_required")
        normalized.setdefault("safe_boundary", False)
        normalized.setdefault("unexecuted_remainder_prohibited", False)
        normalized.setdefault("universal_claim", False)
    for field in _SEMANTIC_SET_FIELDS:
        value = normalized.get(field)
        if isinstance(value, list):
            normalized[field] = sorted(set(value))
    return normalized


def review_event_request_digest(event: Mapping[str, Any]) -> str:
    normalized = normalize_review_event_request(event)
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_identified_review_event(
    records: Iterable[Mapping[str, Any]],
    wave_key: str,
    event: Mapping[str, Any],
) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    """Build a new bundle and put retry metadata on its leading row only.

    Historical migration deliberately bypasses this function and writes parsed
    rows unchanged.  Runtime compact authoring uses this function, making the
    metadata required by construction for every newly generated bundle.
    """

    rows, errors = build_compact_review_event(records, event)
    if errors:
        return (), errors
    try:
        identity = derive_review_event_identity(wave_key, event)
        digest = review_event_request_digest(event)
    except (TypeError, ValueError) as exc:
        return (), (str(exc),)
    identified = [dict(record) for record in rows]
    identified[0][EVENT_IDENTITY_FIELD] = identity
    identified[0][REQUEST_DIGEST_FIELD] = digest
    return tuple(identified), ()


@contextmanager
def _adoption_write_lock(repo_root: Path):
    """Serialize cross-process adoption ledger read/validate/write cycles."""

    path = repo_root / ADOPTION_LOCK_REL
    with RuntimeFileLock(path, blocking=True):
        yield


@contextmanager
def review_event_write_lock(repo_root: Path):
    """Public re-entrant project-global lock for wave/event/projection writes.

    Public lifecycle handlers may hold this lock across a wave.md mutation and
    the telemetry projection that follows it. Existing event/adoption helpers
    also acquire the same lock internally, so same-thread nesting must not
    deadlock while other threads and processes remain serialized.
    """

    with _WRITE_THREAD_LOCK:
        depth = int(getattr(_WRITE_LOCK_STATE, "depth", 0))
        if depth:
            _WRITE_LOCK_STATE.depth = depth + 1
            try:
                yield
            finally:
                _WRITE_LOCK_STATE.depth = depth
            return
        with _adoption_write_lock(repo_root):
            _WRITE_LOCK_STATE.depth = 1
            try:
                yield
            finally:
                _WRITE_LOCK_STATE.depth = 0


def _read_adoption_ledger(repo_root: Path) -> tuple[dict[str, Any], str | None]:
    path = repo_root / ADOPTION_LEDGER_REL
    path_error = _adoption_ledger_path_error(repo_root, path)
    if path_error:
        return {}, path_error
    if not path.exists():
        return {"protocol_version": PROTOCOL_VERSION, "waves": {}}, None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, f"review evidence adoption ledger is unreadable: {exc}"
    if (
        not isinstance(value, dict)
        or value.get("protocol_version") != PROTOCOL_VERSION
        or not isinstance(value.get("waves"), dict)
    ):
        return {}, "review evidence adoption ledger has an unsupported shape/version"
    return value, None


def _write_adoption_ledger_atomic(repo_root: Path, ledger: Mapping[str, Any]) -> None:
    path = repo_root / ADOPTION_LEDGER_REL
    path_error = _adoption_ledger_path_error(repo_root, path)
    if path_error:
        raise OSError(path_error)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, path)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def _adoption_ledger_path_error(repo_root: Path, path: Path) -> str | None:
    """Keep migration/adoption authority inside the configured repository."""

    try:
        root_real = repo_root.resolve(strict=True)
        waves_dir = repo_root / "docs" / "waves"
        if waves_dir.is_symlink():
            return "review evidence adoption directory may not be a symlink"
        if waves_dir.exists():
            waves_real = waves_dir.resolve(strict=True)
            if not waves_real.is_relative_to(root_real):
                return "review evidence adoption directory escapes repository root"
        else:
            # Reads must not materialize the authority directory.  The writer
            # creates it only after the configured repository boundary has
            # been proven from its nearest existing ancestor.
            ancestor = waves_dir
            while not ancestor.exists() and ancestor != repo_root:
                if ancestor.is_symlink():
                    return "review evidence adoption directory may not traverse a symlink"
                ancestor = ancestor.parent
            ancestor_real = ancestor.resolve(strict=True)
            if not ancestor_real.is_relative_to(root_real):
                return "review evidence adoption directory escapes repository root"
            waves_real = root_real / "docs" / "waves"
        if path.is_symlink():
            return "review evidence adoption ledger may not be a symlink"
        if path.exists() and not path.resolve(strict=True).is_relative_to(waves_real):
            return "review evidence adoption ledger escapes its canonical directory"
    except (OSError, RuntimeError) as exc:
        return f"review evidence adoption path is not safely resolvable: {exc}"
    return None


def _write_bytes_atomic(path: Path, payload: bytes, label: str) -> None:
    """Replace one authority file without exposing a partially written body."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.{label}.tmp")
    try:
        temp.write_bytes(payload)
        os.replace(temp, path)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def externalize_adopted_inline_wave_locked(
    repo_root: Path,
    wave_key: str,
    wave_path: Path,
) -> tuple[tuple[dict[str, Any], ...] | None, str | None]:
    """One-way externalize a lossless adopted inline ledger.

    The caller holds ``review_event_write_lock``.  Writes intentionally follow
    the recoverable authority order ``events.jsonl`` → ``wave.md`` → adoption
    proof.  A retry can therefore converge after interruption at either file
    boundary without consulting prose as authority.
    """

    wave_md = Path(wave_path)
    if wave_md.name != "wave.md":
        wave_md = wave_md / "wave.md"
    path_error = _review_authority_path_error(wave_md)
    if path_error:
        return None, path_error
    ledger, error = _read_adoption_ledger(repo_root)
    if error:
        return None, error
    state = ledger["waves"].get(wave_key)
    if state is None:
        return None, None
    if not isinstance(state, dict):
        return None, f"review evidence adoption state for `{wave_key}` is malformed"
    if isinstance(state.get("records"), list):
        expected = tuple(dict(record) for record in state["records"])
    else:
        adopted, adopted_error = adopted_protocol_state(repo_root, wave_key)
        if adopted_error:
            return None, adopted_error
        if adopted is None:
            return None, None
        result = validate_external_review_evidence(wave_md)
        if result.errors:
            return None, "; ".join(result.errors)
        return tuple(dict(record) for record in result.records), None

    try:
        text = wave_md.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return None, f"legacy inline wave is unreadable: {exc}"
    source, source_errors = parse_review_evidence_source(text)
    if source_errors:
        return None, "; ".join(source_errors)
    if source is None:
        legacy = validate_review_evidence(text)
        if legacy.marker_version != PROTOCOL_VERSION or legacy.errors:
            return None, (
                "lossless typed-inline review evidence is invalid: "
                + "; ".join(legacy.errors or ("protocol marker missing",))
            )
        records = tuple(dict(record) for record in legacy.records)
        if records != expected:
            return None, "typed-inline records do not equal the retained adoption history"
        markers = list(_MARKER_RE.finditer(text))
        if len(markers) != 1:
            return None, "legacy wave must contain exactly one review-evidence protocol marker"
        external = _MARKER_RE.sub(
            REVIEW_EVIDENCE_SOURCE_DECLARATION,
            text,
            count=1,
        )
        external = render_review_evidence_projection(external, records)
        try:
            _write_bytes_atomic(
                review_event_path(wave_md),
                canonical_review_events_bytes(records),
                "inline-adoption-events",
            )
            _write_bytes_atomic(
                wave_md,
                external.encode("utf-8"),
                "inline-adoption-wave",
            )
        except OSError as exc:
            return None, f"could not externalize typed-inline review evidence: {exc}"
    elif source == REVIEW_EVIDENCE_SOURCE:
        resumed = validate_external_review_evidence(wave_md)
        if resumed.errors:
            return None, "partially externalized review evidence is invalid: " + "; ".join(
                resumed.errors
            )
        records = tuple(dict(record) for record in resumed.records)
        if records != expected:
            return None, "external records do not equal the retained inline adoption history"
    else:
        return None, f"unsupported review evidence source `{source}`"

    proof = review_event_prefix_proof(records)
    ledger["waves"][wave_key] = {
        "version": PROTOCOL_VERSION,
        "source": REVIEW_EVIDENCE_SOURCE,
        **proof,
    }
    try:
        _write_adoption_ledger_atomic(repo_root, ledger)
    except OSError as exc:
        return None, f"could not persist external review evidence adoption: {exc}"
    final = validate_external_review_evidence(wave_md)
    retained_errors = validate_adopted_protocol_state(repo_root, wave_key, wave_md)
    if final.errors or retained_errors or tuple(final.records) != records:
        return None, "external review evidence reread failed after adoption"
    return records, None


def adopted_protocol_state(repo_root: Path, wave_key: str) -> tuple[dict[str, Any] | None, str | None]:
    """Return the bounded external-ledger proof for a wave, if adopted."""

    ledger, error = _read_adoption_ledger(repo_root)
    if error:
        return None, error
    state = ledger["waves"].get(wave_key)
    if state is None:
        return None, None
    required = {"version", "source", "record_count", "prefix_sha256"}
    if (
        not isinstance(state, dict)
        or set(state) != required
        or state.get("version") != PROTOCOL_VERSION
        or state.get("source") != REVIEW_EVIDENCE_SOURCE
        or isinstance(state.get("record_count"), bool)
        or not isinstance(state.get("record_count"), int)
        or state.get("record_count", -1) < 0
        or not isinstance(state.get("prefix_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", state.get("prefix_sha256", "")) is None
    ):
        return None, f"review evidence adoption state for `{wave_key}` is malformed"
    return state, None


def record_protocol_state_locked(
    repo_root: Path, wave_key: str, wave_path: Path
) -> str | None:
    """Advance one external proof while the caller holds ``review_event_write_lock``."""

    result = validate_external_review_evidence(wave_path)
    if not result.ok:
        return "cannot record review evidence adoption from an invalid external ledger: " + "; ".join(result.errors)
    try:
        ledger, error = _read_adoption_ledger(repo_root)
        if error:
            return error
        prior_raw = ledger["waves"].get(wave_key)
        if prior_raw is not None:
            prior, state_error = adopted_protocol_state(repo_root, wave_key)
            if state_error:
                return state_error
            assert prior is not None
            count = int(prior["record_count"])
            if count > len(result.records):
                return "review evidence adoption proof is ahead of the canonical ledger"
            if review_event_prefix_proof(result.records, count)["prefix_sha256"] != prior["prefix_sha256"]:
                return "review evidence adopted prefix hash does not match the canonical ledger"
        proof = review_event_prefix_proof(result.records)
        ledger["waves"][wave_key] = {
            "version": PROTOCOL_VERSION,
            "source": REVIEW_EVIDENCE_SOURCE,
            **proof,
        }
        _write_adoption_ledger_atomic(repo_root, ledger)
    except OSError as exc:
        return f"could not persist review evidence adoption state: {exc}"
    return None


def record_protocol_state(repo_root: Path, wave_key: str, wave_path: Path) -> str | None:
    """Lock and advance one external-ledger count/hash adoption proof."""

    try:
        with review_event_write_lock(repo_root):
            return record_protocol_state_locked(repo_root, wave_key, wave_path)
    except OSError as exc:
        return f"could not persist review evidence adoption state: {exc}"


def validate_adopted_protocol_state(
    repo_root: Path, wave_key: str, wave_path: Path
) -> tuple[str, ...]:
    """Validate exact external authority against retained count/hash proof."""

    state, error = adopted_protocol_state(repo_root, wave_key)
    if error:
        return (error,)
    if state is None:
        return ()
    wave_md = Path(wave_path)
    if wave_md.name != "wave.md":
        wave_md = wave_md / "wave.md"
    try:
        text = wave_md.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return (f"adopted wave record is unreadable: {exc}",)
    source, source_errors = parse_review_evidence_source(text)
    if source_errors:
        return source_errors
    if source != REVIEW_EVIDENCE_SOURCE:
        return ("review evidence source declaration may not be removed after durable adoption",)
    event_path = review_event_path(wave_md)
    if not event_path.is_file():
        return ("adopted canonical review event ledger is missing",)
    records, parse_errors = read_review_event_ledger(wave_md)
    if parse_errors:
        return parse_errors
    count = int(state["record_count"])
    if count > len(records):
        return ("review evidence adoption proof is ahead of the canonical ledger",)
    proof = review_event_prefix_proof(records, count)
    if proof["prefix_sha256"] != state["prefix_sha256"]:
        return ("review evidence adopted prefix hash does not match the canonical ledger",)
    if len(records) > count:
        return ("canonical review event ledger has an unadopted suffix",)
    return ()


def adopted_legacy_inline_protocol_state_for_migration(
    repo_root: Path, wave_key: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Read the temporary inline full-record state solely for self-host migration."""

    ledger, error = _read_adoption_ledger(repo_root)
    if error:
        return None, error
    state = ledger["waves"].get(wave_key)
    if state is None:
        return None, None
    if not isinstance(state, dict) or state.get("version") != PROTOCOL_VERSION or not isinstance(state.get("records"), list):
        return None, f"legacy inline adoption state for `{wave_key}` is malformed"
    return state, None


def record_legacy_inline_protocol_state_for_migration(
    repo_root: Path, wave_key: str, text: str
) -> str | None:
    """Migration-only writer retained until the pre-release self-host cutover."""

    result = validate_review_evidence(text)
    if result.marker_version != PROTOCOL_VERSION or not result.ok:
        return "cannot record legacy inline adoption from an invalid or unmarked wave"
    try:
        with review_event_write_lock(repo_root):
            ledger, error = _read_adoption_ledger(repo_root)
            if error:
                return error
            prior = ledger["waves"].get(wave_key)
            records = [dict(record) for record in result.records]
            if prior is not None:
                if not isinstance(prior, dict) or not isinstance(prior.get("records"), list):
                    return f"legacy inline adoption state for `{wave_key}` is malformed"
                if records[: len(prior["records"])] != prior["records"]:
                    return "legacy inline review evidence records were removed or changed"
            ledger["waves"][wave_key] = {"version": PROTOCOL_VERSION, "records": records}
            _write_adoption_ledger_atomic(repo_root, ledger)
    except OSError as exc:
        return f"could not persist legacy inline adoption state: {exc}"
    return None


def empty_finding_synthesis_section() -> str:
    """Canonical marker-owned empty section for a newly-created wave."""

    return (
        "## Finding Synthesis\n\n"
        f"{FINDING_SYNTHESIS_MARKER_BEGIN}\n"
        f"{review_evidence_human_table(())}\n\n"
        f"{REVIEW_EVIDENCE_DETAILS_BEGIN}\n"
        f"<summary>{review_evidence_summary_line(())}</summary>\n\n"
        "```jsonl\n```\n"
        f"{REVIEW_EVIDENCE_DETAILS_END}\n"
        f"{FINDING_SYNTHESIS_MARKER_END}\n"
    )


def _is_true(value: object) -> bool:
    return value is True


def derive_action_required(record: Mapping[str, Any]) -> bool:
    """Return Requirement 14's exact action-required predicate."""
    if record.get("validation_status") != "real":
        return False
    supported = record.get("supported_reachability") is True
    return bool(
        record.get("contract_relevance") in {"required_ac", "public_contract"}
        or (_is_true(record.get("introduced_or_worsened_by_wave")) and supported)
        or (
            supported
            and record.get("observable_impact") in {"material", "critical"}
            and record.get("containment") in {"detect_only", "none", "unverified"}
        )
        or (
            supported
            and record.get("attacker_reachability") is True
            and record.get("authority_delta") in {"material", "critical"}
            and record.get("containment") != "preventive"
        )
    )


def derive_disposition(record: Mapping[str, Any]) -> str:
    """Apply the ordered four-way actionability state machine."""
    if record.get("validation_status") in {"invalid", "conforming"}:
        return "not_issue"
    if derive_action_required(record):
        return "do_now"
    if (
        record.get("validation_status") == "real"
        and record.get("optional_value") == "positive"
        and record.get("repair_scope_bounded") is True
        and record.get("repair_safety") == "safe"
        and record.get("scope_relation") == "admitted"
        and record.get("benefit_vs_fix_risk") == "greater"
    ):
        return "maybe_later"
    return "dont_do_later"


def derive_blocking(record: Mapping[str, Any]) -> bool:
    """Derive blocking independently of repair difficulty or proposed repair quality."""
    if derive_disposition(record) != "do_now":
        return False
    supported = record.get("supported_reachability") is True
    material_impact = record.get("observable_impact") in {"material", "critical"}
    return bool(
        record.get("contract_relevance") in {"required_ac", "public_contract"}
        or (
            _is_true(record.get("introduced_or_worsened_by_wave"))
            and supported
            and material_impact
        )
        or (
            supported
            and material_impact
            and record.get("containment") in {"detect_only", "none", "unverified"}
        )
        or (
            supported
            and record.get("attacker_reachability") is True
            and record.get("authority_delta") in {"material", "critical"}
            and record.get("containment") != "preventive"
        )
    )


def derive_review_depth(record: Mapping[str, Any]) -> str:
    if any(record.get(name) is True for name in FULL_COUNCIL_TRIGGERS):
        return "full"
    if derive_disposition(record) in {"do_now", "maybe_later"}:
        return "focused"
    return "none"


def current_synthesis_heads(records: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Return the append-order current synthesis head for each finding."""

    heads: dict[str, Mapping[str, Any]] = {}
    for record in records:
        if record.get("record_type") == "finding_synthesis" and isinstance(record.get("finding_id"), str):
            heads[str(record["finding_id"])] = record
    return heads


def review_evidence_summary(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Produce the compact human-facing summary for the detailed machine ledger."""

    rows = tuple(records)
    heads = current_synthesis_heads(rows)
    dispositions = {name: 0 for name in ("do_now", "maybe_later", "dont_do_later", "not_issue")}
    for head in heads.values():
        disposition = str(head.get("disposition", ""))
        if disposition in dispositions:
            dispositions[disposition] += 1
    return {
        "records": len(rows),
        "runs": sum(row.get("record_type") == "review_run" for row in rows),
        "findings": len(heads),
        "current_dispositions": dispositions,
    }


def review_evidence_summary_line(records: Iterable[Mapping[str, Any]]) -> str:
    summary = review_evidence_summary(records)
    dispositions = summary["current_dispositions"]
    current = ", ".join(f"{name} {dispositions[name]}" for name in dispositions)
    return (
        f"Machine review evidence — {summary['records']} records; {summary['runs']} runs; "
        f"{summary['findings']} findings; current: {current}"
    )


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def review_evidence_human_table(records: Iterable[Mapping[str, Any]]) -> str:
    """Render a concise current-head table; JSONL remains the canonical store."""

    heads = current_synthesis_heads(records)
    lines = [
        "| Current finding | Disposition | Open block | Repair | Approval recheck |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not heads:
        lines.append("| — | — | — | — | — |")
        return "\n".join(lines)
    for finding_id in sorted(heads):
        head = heads[finding_id]
        affected = head.get("approval_recheck_lanes")
        if not isinstance(affected, list):
            affected = list(
                dict.fromkeys(
                    [
                        *head.get("source_lanes", []),
                        *head.get("blocking_required_lanes", []),
                    ]
                )
            )
        repair_state = head.get("repair_execution_state")
        open_block = bool(head.get("blocking_required_lanes")) or bool(
            head.get("blocking") is True
            and repair_state not in {"completed", "operator_waived"}
        )
        values = (
            finding_id,
            head.get("disposition", "—"),
            "yes" if open_block else "no",
            repair_state or "—",
            ", ".join(str(item) for item in affected) or "—",
        )
        lines.append("| " + " | ".join(_markdown_cell(value) for value in values) + " |")
    return "\n".join(lines)


def _approval_rows(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, tuple[int, Mapping[str, Any]]]:
    return {
        str(record.get("claim_id")): (position, record)
        for position, record in enumerate(records)
        if record.get("record_type") == "executable_evidence"
        and record.get("claim_kind") == "approval"
        and record.get("required_for_approval") is True
        and record.get("phase") == "delivery"
        and record.get("execution_status") == "executed"
    }


def _finding_affects_signoff(head: Mapping[str, Any], signoff_key: str) -> bool:
    explicit = head.get("approval_recheck_lanes")
    affected = (
        {str(lane) for lane in explicit}
        if isinstance(explicit, list)
        else {
            str(lane)
            for lane in [
                *head.get("source_lanes", []),
                *head.get("blocking_required_lanes", []),
            ]
        }
    )
    if signoff_key == "operator-signoff":
        return True
    if signoff_key == "wave-council-readiness":
        return False
    if signoff_key.startswith("wave-council-"):
        return (
            signoff_key in affected
            or "wave-council" in affected
            or head.get("review_depth") == "full"
        )
    return signoff_key in affected


def review_status_rows(
    records: Iterable[Mapping[str, Any]],
    required_signoff_keys: Iterable[str],
) -> tuple[dict[str, Any], ...]:
    """Derive one causal current-state row per canonical signoff key.

    ``events.jsonl`` remains the only history.  These rows are a bounded view:
    current finding heads plus the latest applicable approval.  Readiness is a
    crossed historical gate and is deliberately not invalidated by delivery
    repairs.
    """

    rows = tuple(dict(record) for record in records)
    approvals = _approval_rows(rows)
    heads = current_synthesis_heads(rows)
    positions = {id(record): position for position, record in enumerate(rows)}
    result: list[dict[str, Any]] = []
    for key in dict.fromkeys(str(item) for item in required_signoff_keys if str(item)):
        approval = approvals.get(f"approval:{key}")
        approval_position = approval[0] if approval is not None else -1
        approval_record = approval[1] if approval is not None else None
        context = (
            approval_record.get("verification_context")
            if isinstance(approval_record, Mapping)
            else None
        )
        expected_actor = (
            "operator"
            if key == "operator-signoff"
            else ("wave-council" if key.startswith("wave-council-") else key)
        )
        approval_valid = bool(
            approval_record is not None
            and isinstance(context, Mapping)
            and context.get("actor") == expected_actor
            and (
                key == "operator-signoff"
                or (
                    context.get("fresh_context") is True
                    and context.get("independent") is True
                )
            )
        )
        blocking: list[tuple[str, Mapping[str, Any]]] = []
        for finding_id, head in heads.items():
            if head.get("blocking") is not True:
                continue
            if not _finding_affects_signoff(head, key):
                continue
            head_position = positions.get(id(head), -1)
            if approval_position < head_position:
                blocking.append((str(finding_id), head))
        if blocking:
            finding_ids = [finding_id for finding_id, _head in blocking]
            unresolved = sorted(
                {
                    str(lane)
                    for _finding_id, head in blocking
                    for lane in head.get("blocking_required_lanes", [])
                    if str(lane)
                }
            )
            why = "blocking findings: " + ", ".join(finding_ids[:8])
            if len(finding_ids) > 8:
                why += f" (+{len(finding_ids) - 8} more; see events.jsonl)"
            if unresolved:
                why += "; unresolved lanes: " + ", ".join(unresolved)
                next_action = (
                    "record independent reverification for "
                    + ", ".join(unresolved)
                    + ", then re-approve "
                    + key
                )
            else:
                next_action = f"record a fresh independent approval for {key}"
            state = "withheld"
        elif approval_valid:
            state = "approved"
            why = "current executed approval follows every affected repair"
            next_action = "none"
        else:
            state = "pending"
            why = (
                "approval evidence has invalid actor or independence"
                if approval_record is not None
                else "no current executed approval"
            )
            next_action = f"record approval evidence for {key}"
        result.append(
            {
                "signoff_key": key,
                "state": state,
                "why": why,
                "next_action": next_action,
            }
        )
    return tuple(result)


def review_status_human_table(
    records: Iterable[Mapping[str, Any]],
    required_signoff_keys: Iterable[str],
) -> str:
    lines = [
        "| Signoff | State | Why | Next action |",
        "| --- | --- | --- | --- |",
    ]
    status_rows = review_status_rows(records, required_signoff_keys)
    if not status_rows:
        lines.append("| — | — | — | — |")
    for row in status_rows:
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(row[name])
                for name in ("signoff_key", "state", "why", "next_action")
            )
            + " |"
        )
    return "\n".join(lines)


def review_status_signoff_keys(
    records: Iterable[Mapping[str, Any]],
    base_keys: Iterable[str] = (),
) -> tuple[str, ...]:
    """Return canonical status-row identities from caller policy + ledger facts."""

    rows = tuple(dict(record) for record in records)
    keys = [str(key) for key in base_keys if str(key)]
    for record in rows:
        claim_id = str(record.get("claim_id") or "")
        if claim_id.startswith("approval:"):
            keys.append(claim_id.removeprefix("approval:"))
    for head in current_synthesis_heads(rows).values():
        lanes = head.get("approval_recheck_lanes")
        if isinstance(lanes, list):
            keys.extend(str(lane) for lane in lanes if str(lane))
    return tuple(dict.fromkeys(keys))


def required_review_status_keys(
    root: Path,
    wave_text: str,
    records: Iterable[Mapping[str, Any]] = (),
) -> tuple[str, ...]:
    """Return every signoff row required by the wave and project policy.

    This is the single key-derivation path used by lifecycle writes, lint, and
    upgrade.  A required lane is represented even before it has an approval
    event, so absence is rendered explicitly as ``pending`` rather than being
    omitted from the current-state projection.
    """

    lanes: list[str] = []
    in_participants = False
    for raw in wave_text.splitlines():
        line = raw.strip()
        if line.startswith("## Participants"):
            in_participants = True
            continue
        if in_participants and line.startswith("## "):
            break
        if not in_participants:
            continue
        match = re.match(
            r"^-\s*Required review lanes\s*:\s*(?P<lanes>.+?)\s*$",
            line,
            re.IGNORECASE,
        )
        if match:
            lanes.extend(
                value.strip().strip("`").strip()
                for value in match.group("lanes").split(",")
                if value.strip().strip("`").strip()
            )
            continue
        if not line.startswith("|") or line.startswith("|------"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[0].lower() != "role" and "review" in cells[1].lower():
            lanes.append(cells[0])

    config: dict[str, Any] = {}
    try:
        loaded = json.loads((root / "docs" / "workflow-config.json").read_text("utf-8"))
        if isinstance(loaded, dict):
            config = loaded
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass
    project_lanes = config.get("required_review_lanes", [])
    if isinstance(project_lanes, list):
        lanes.extend(str(value).strip() for value in project_lanes if str(value).strip())

    council_keys = ["wave-council-readiness", "wave-council-delivery"]
    council = config.get("wave_review")
    if isinstance(council, dict) and bool(council.get("enabled")):
        phases = council.get("phases", {})
        if isinstance(phases, dict):
            for phase in ("prepare", "review"):
                value = phases.get(phase, {})
                if isinstance(value, dict):
                    key = str(value.get("signoff_key") or "").strip()
                    if key:
                        council_keys.append(key)

    return review_status_signoff_keys(
        records,
        (*council_keys, *lanes, "operator-signoff"),
    )


_REVIEW_EVIDENCE_SECTION_RE = re.compile(
    r"(?ms)^## Review Evidence[ \t]*$\n(?P<body>.*?)(?=^##\s|\Z)"
)
_GENERATED_SIGNOFF_LINE_RE = re.compile(
    r"(?m)^\s*-\s*(?P<key>[a-z0-9-]+):\s*"
    r"(?P<state>approved|withdrawn)\s+—\s+.*$\n?"
)


def render_review_status_projection(
    text: str,
    records: Iterable[Mapping[str, Any]],
    required_signoff_keys: Iterable[str],
) -> str:
    """Replace the bounded current review-status block.

    Historical transitions remain solely in ``events.jsonl``.  Exact generated
    approval/withdrawal lines are removed only for signoff keys represented by
    typed ledger state; placeholders and human prose are preserved.
    """

    rows = tuple(dict(record) for record in records)
    keys = tuple(dict.fromkeys(str(key) for key in required_signoff_keys if str(key)))
    matches = list(_REVIEW_EVIDENCE_SECTION_RE.finditer(text))
    if len(matches) != 1:
        raise ValueError("external wave must contain exactly one Review Evidence section")
    body = matches[0].group("body")
    begin_count = body.count(REVIEW_STATUS_MARKER_BEGIN)
    end_count = body.count(REVIEW_STATUS_MARKER_END)
    if begin_count != end_count or begin_count > 1:
        raise ValueError("Review Evidence status markers are malformed or duplicated")
    if begin_count:
        begin = body.find(REVIEW_STATUS_MARKER_BEGIN)
        end = body.find(REVIEW_STATUS_MARKER_END, begin)
        if end < begin:
            raise ValueError("Review Evidence status markers are out of order")
        body = (
            body[:begin].rstrip()
            + "\n"
            + body[end + len(REVIEW_STATUS_MARKER_END):].lstrip("\n")
        )
    typed_keys = {
        str(record.get("claim_id", "")).removeprefix("approval:")
        for record in rows
        if str(record.get("claim_id", "")).startswith("approval:")
    }
    for head in current_synthesis_heads(rows).values():
        affected = head.get("approval_recheck_lanes")
        if isinstance(affected, list):
            typed_keys.update(str(lane) for lane in affected)

    def preserve_generated(match: re.Match[str]) -> str:
        return "" if match.group("key") in typed_keys else match.group(0)

    body = _GENERATED_SIGNOFF_LINE_RE.sub(preserve_generated, body).strip("\r\n")
    owned = (
        f"{REVIEW_STATUS_MARKER_BEGIN}\n"
        f"{review_status_human_table(rows, keys)}\n"
        f"{REVIEW_STATUS_MARKER_END}"
    )
    # ``_REVIEW_EVIDENCE_SECTION_RE`` consumes the heading's terminating LF.
    # One leading LF therefore produces exactly one Markdown blank line.
    new_body = "\n" + owned
    if body:
        new_body += "\n\n" + body
    new_body += "\n\n"
    return text[: matches[0].start("body")] + new_body + text[matches[0].end("body") :]


def render_review_evidence_records(text: str, records: Iterable[Mapping[str, Any]]) -> str:
    """Render records under a collapsed summary without changing surrounding wave prose."""

    text = _canonicalize_finding_synthesis_markers(text)
    rows = tuple(dict(record) for record in records)
    section_matches = list(_SECTION_RE.finditer(text))
    if len(section_matches) != 1:
        raise ValueError("marked wave must contain exactly one Finding Synthesis section")
    body = section_matches[0].group("body")
    marker_begin = body.find(FINDING_SYNTHESIS_MARKER_BEGIN)
    marker_end = body.find(FINDING_SYNTHESIS_MARKER_END)
    if marker_begin < 0 or marker_end < marker_begin:
        raise ValueError("Finding Synthesis owned markers are missing or out of order")
    rendered_rows = "\n".join(json.dumps(row, sort_keys=True) for row in rows)
    if rendered_rows:
        rendered_rows += "\n"
    owned = (
        f"{FINDING_SYNTHESIS_MARKER_BEGIN}\n"
        f"{review_evidence_human_table(rows)}\n\n"
        f"{REVIEW_EVIDENCE_DETAILS_BEGIN}\n"
        f"<summary>{review_evidence_summary_line(rows)}</summary>\n\n"
        f"```jsonl\n{rendered_rows}```\n"
        f"{REVIEW_EVIDENCE_DETAILS_END}\n"
        f"{FINDING_SYNTHESIS_MARKER_END}"
    )
    body_start = section_matches[0].start("body")
    absolute_begin = body_start + marker_begin
    absolute_end = body_start + marker_end + len(FINDING_SYNTHESIS_MARKER_END)
    return text[:absolute_begin] + owned + text[absolute_end:]


def empty_external_finding_synthesis_section() -> str:
    """Canonical generated projection for a newly-created external ledger wave."""

    return (
        "## Finding Synthesis\n\n"
        f"{FINDING_SYNTHESIS_MARKER_BEGIN}\n"
        f"{review_evidence_human_table(())}\n\n"
        f"{REVIEW_EVIDENCE_DETAILS_BEGIN}\n"
        f"<summary>{review_evidence_summary_line(())}</summary>\n"
        f"{REVIEW_EVIDENCE_DETAILS_END}\n"
        f"{FINDING_SYNTHESIS_MARKER_END}\n"
    )


def render_review_evidence_projection(
    text: str, records: Iterable[Mapping[str, Any]]
) -> str:
    """Rebuild the marker-owned Markdown projection without embedding authority."""

    text = _canonicalize_finding_synthesis_markers(text)
    rows = tuple(dict(record) for record in records)
    section_matches = list(_SECTION_RE.finditer(text))
    if len(section_matches) != 1:
        raise ValueError("external wave must contain exactly one Finding Synthesis section")
    body = section_matches[0].group("body")
    marker_begin = body.find(FINDING_SYNTHESIS_MARKER_BEGIN)
    marker_end = body.find(FINDING_SYNTHESIS_MARKER_END)
    if marker_begin < 0 or marker_end < marker_begin:
        raise ValueError("Finding Synthesis owned markers are missing or out of order")
    owned = (
        f"{FINDING_SYNTHESIS_MARKER_BEGIN}\n"
        f"{review_evidence_human_table(rows)}\n\n"
        f"{REVIEW_EVIDENCE_DETAILS_BEGIN}\n"
        f"<summary>{review_evidence_summary_line(rows)}</summary>\n"
        f"{REVIEW_EVIDENCE_DETAILS_END}\n"
        f"{FINDING_SYNTHESIS_MARKER_END}"
    )
    body_start = section_matches[0].start("body")
    absolute_begin = body_start + marker_begin
    absolute_end = body_start + marker_end + len(FINDING_SYNTHESIS_MARKER_END)
    return text[:absolute_begin] + owned + text[absolute_end:]


def _compact_id(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned[:48] or "record"


def _unique_record_id(records: Iterable[Mapping[str, Any]], prefix: str, base: str) -> str:
    used = {
        str(record.get(field))
        for record in records
        for field in ("evidence_record_id", "review_run_id", "record_id")
        if record.get(field)
    }
    stem = f"{prefix}-{_compact_id(base)}"
    candidate = stem
    suffix = 2
    while candidate in used:
        candidate = f"{stem}-{suffix}"
        suffix += 1
    return candidate


_COMPACT_CORE_JUDGMENT_FIELDS = frozenset(
    {
        "validation_status",
        "scope_relation",
        "introduced_or_worsened_by_wave",
        "contract_relevance",
        "supported_reachability",
        "attacker_reachability",
        "authority_domain",
        "authority_delta",
        "observable_impact",
        "containment",
    }
)
_COMPACT_OPTIONAL_REPAIR_FIELDS = frozenset(
    {"fix_risk", "optional_value", "repair_scope_bounded", "repair_safety", "benefit_vs_fix_risk", "rejection_basis"}
)


def build_compact_review_event(
    records: Iterable[Mapping[str, Any]],
    event: Mapping[str, Any],
) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    """Expand a compact semantic event into canonical append-only protocol rows."""

    prior = tuple(dict(record) for record in records)
    errors: list[str] = []
    event_type = event.get("event")
    if event_type not in {"approval", "finding", "run"}:
        return (), ("event must be one of: approval, finding, run",)
    actor = event.get("actor")
    context_id = event.get("context_id")
    if not _nonempty_string(actor) or not _nonempty_string(context_id):
        errors.append("actor and context_id must be non-empty strings")

    if event_type == "run":
        run_kind = event.get("run_kind")
        cycle = event.get("cycle")
        if run_kind not in {"readiness", "initial_delivery"} or cycle != 0:
            errors.append("empty lightweight run requires run_kind readiness/initial_delivery and cycle 0")
        if errors:
            return (), tuple(errors)
        run_id = _unique_record_id(prior, "run", str(run_kind))
        return (
            {
                "record_type": "review_run",
                "review_run_id": run_id,
                "run_kind": run_kind,
                "cycle": 0,
                "candidate_finding_ids": [],
                "source_record_ids": [],
                "dedup_evidence_id": None,
                "verification_context": {
                    "actor": actor,
                    "context_id": context_id,
                    "fresh_context": bool(event.get("fresh_context")),
                    "independent": bool(event.get("independent")),
                },
            },
        ), ()

    if event_type == "approval":
        signoff_key = event.get("signoff_key")
        if not _nonempty_string(signoff_key):
            errors.append("approval event requires signoff_key")
        else:
            expected_actor = (
                "operator"
                if signoff_key == "operator-signoff"
                else "wave-council"
                if str(signoff_key).startswith("wave-council-")
                else signoff_key
            )
            if actor != expected_actor:
                errors.append(
                    f"approval actor must be `{expected_actor}` for signoff `{signoff_key}`"
                )
            if expected_actor != "operator" and (
                event.get("fresh_context") is not True
                or event.get("independent") is not True
            ):
                errors.append(
                    "specialist and council approvals require fresh_context=true and independent=true"
                )
        if event.get("integrity_confirmed") is not True:
            errors.append("approval event requires integrity_confirmed=true")
        for field in ("observed", "artifact_or_test_id"):
            if not _nonempty_string(event.get(field)):
                errors.append(f"approval event requires {field}")
        if errors:
            return (), tuple(errors)
        evidence_id = _unique_record_id(prior, "ev-approval", str(signoff_key))
        observed = str(event["observed"])
        return (
            {
                "record_type": "executable_evidence",
                "evidence_record_id": evidence_id,
                "claim_id": f"approval:{signoff_key}",
                "claim_kind": "approval",
                "required_for_approval": True,
                "phase": "delivery",
                "proposition": str(event.get("proposition") or f"{signoff_key} approves the current affected scope"),
                "counterexample_or_failure_condition": str(event.get("failure_condition") or "the approval predates an affected repair or is not independently grounded"),
                "execution_status": "executed",
                "public_path": str(event.get("public_path") or "wave_record_review_evidence"),
                "command_or_fixture": str(event.get("command_or_fixture") or event["artifact_or_test_id"]),
                "expected": str(event.get("expected") or "the approving actor independently verifies the current affected scope"),
                "observed": observed,
                "artifact_or_test_id": str(event["artifact_or_test_id"]),
                "adjacent_controls": list(event.get("adjacent_controls") or []),
                "test_ran_without_unintended_skip": True,
                "public_path_reached": True,
                "boundary_values_realistic": True,
                "assertions_non_vacuous": True,
                "known_bad_detected": True,
                "known_bad_detection_method": str(event.get("known_bad_detection_method") or "approval evidence and affected-lane chronology were checked"),
                "limitations": str(event.get("limitations") or "Approval remains scoped to the recorded actor and affected review boundary."),
                "safety_and_authorization": str(event.get("safety_and_authorization") or "Local review evidence only; no external side effects."),
                "probe_class": "none",
                "authorization_status": "not_required",
                "safe_boundary": False,
                "unexecuted_remainder_prohibited": False,
                "universal_claim": False,
                "verification_context": {
                    "actor": actor,
                    "context_id": context_id,
                    "fresh_context": bool(event.get("fresh_context")),
                    "independent": bool(event.get("independent")),
                },
            },
        ), ()

    finding_id = event.get("finding_id")
    run_kind = event.get("run_kind")
    cycle = event.get("cycle")
    judgment = event.get("judgment")
    if not _nonempty_string(finding_id):
        errors.append("finding event requires finding_id")
    if run_kind not in RUN_KINDS:
        errors.append("finding event requires a valid run_kind")
    if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 0:
        errors.append("finding event requires a non-negative integer cycle")
    if not isinstance(judgment, dict):
        errors.append("finding event requires a judgment object")
        judgment = {}
    missing_core = sorted(_COMPACT_CORE_JUDGMENT_FIELDS - judgment.keys())
    if missing_core:
        errors.append("finding judgment missing load-bearing fields: " + ", ".join(missing_core))
    for field in ("proposition", "failure_condition", "public_path", "command_or_fixture", "expected", "observed", "artifact_or_test_id", "known_bad_detection_method", "limitations", "safety_and_authorization", "disposition_rationale"):
        if not _nonempty_string(event.get(field)):
            errors.append(f"finding event requires {field}")
    # Credible-threat gate — the requirement that a material/critical authority delta
    # NAMES the specific capability/asset in `disposition_rationale` is a reviewer-owned
    # SEMANTIC judgment stated in the security seeds (209/213/229), not a validator check.
    # A prose-length heuristic here would be both bypassable (generic filler passes) and
    # over-strict (a valid concise basis like "read API keys" is short), so no machine
    # check is added; `disposition_rationale` remains required non-empty above.
    if event.get("integrity_confirmed") is not True and event.get("execution_status", "executed") == "executed":
        errors.append("executed finding evidence requires integrity_confirmed=true")
    triggers = event.get("review_boundaries_changed")
    if not isinstance(triggers, list) or len(triggers) != len(set(triggers)) or any(item not in FULL_COUNCIL_TRIGGERS for item in triggers):
        errors.append("review_boundaries_changed must be a duplicate-free list of canonical trigger names")
    for field in ("source_lanes", "blocking_required_lanes", "approval_recheck_lanes"):
        value = event.get(field)
        if not _string_list(value, allow_empty=field != "source_lanes"):
            errors.append(f"finding event requires duplicate-free {field}")
    if errors:
        return (), tuple(errors)

    provisional: dict[str, Any] = dict(judgment)
    provisional.update(
        {
            "optional_value": "none",
            "repair_scope_bounded": "unverified",
            "repair_safety": "unverified",
            "benefit_vs_fix_risk": "unverified",
            "fix_risk": "unverified",
            "rejection_basis": "none",
        }
    )
    action_required = derive_action_required(provisional)
    validation_status = provisional.get("validation_status")
    if validation_status == "real" and not action_required:
        missing_optional = sorted(_COMPACT_OPTIONAL_REPAIR_FIELDS - judgment.keys())
        if missing_optional:
            return (), ("non-action-required real finding judgment missing repair/disposition fields: " + ", ".join(missing_optional),)
        provisional.update({field: judgment[field] for field in _COMPACT_OPTIONAL_REPAIR_FIELDS})
    elif validation_status in {"invalid", "conforming"}:
        provisional["rejection_basis"] = "none"
    promotion_trigger = event.get("promotion_trigger")
    if provisional.get("rejection_basis") in {"insufficient_evidence", "unsupported_reachability", "disproportionate_repair"} and not _nonempty_string(promotion_trigger):
        return (), ("selected rejection_basis requires promotion_trigger",)

    source_lanes = list(event["source_lanes"])
    blocking_lanes = list(event["blocking_required_lanes"])
    recheck_lanes = list(event["approval_recheck_lanes"])
    heads = current_synthesis_heads(prior)
    prior_head = heads.get(str(finding_id))
    if run_kind in {"readiness", "initial_delivery"} and prior_head is not None:
        return (), (
            "readiness/initial_delivery may introduce only a new finding; "
            "use repair_start or reverification for an existing finding",
        )
    if run_kind in {"repair_start", "reverification"} and prior_head is None:
        return (), (
            f"{run_kind} requires an earlier finding synthesis for `{finding_id}`",
        )
    evidence_id = _unique_record_id(prior, "ev", str(finding_id))
    run_id = _unique_record_id(prior, "run", f"{run_kind}-{cycle}-{finding_id}")
    synthesis_id = _unique_record_id(prior, "syn", f"{finding_id}-{cycle}")
    integrity = event.get("integrity_confirmed") is True
    execution_status = str(event.get("execution_status", "executed"))
    evidence: dict[str, Any] = {
        "record_type": "executable_evidence",
        "evidence_record_id": evidence_id,
        "claim_id": finding_id,
        "claim_kind": "finding",
        "required_for_approval": False,
        "phase": "readiness" if run_kind == "readiness" else "delivery",
        "proposition": event["proposition"],
        "counterexample_or_failure_condition": event["failure_condition"],
        "execution_status": execution_status,
        "public_path": event["public_path"],
        "command_or_fixture": event["command_or_fixture"],
        "expected": event["expected"],
        "observed": event["observed"],
        "artifact_or_test_id": event["artifact_or_test_id"],
        "adjacent_controls": list(event.get("adjacent_controls") or []),
        "test_ran_without_unintended_skip": integrity,
        "public_path_reached": integrity,
        "boundary_values_realistic": integrity,
        "assertions_non_vacuous": integrity,
        "known_bad_detected": integrity,
        "known_bad_detection_method": event["known_bad_detection_method"],
        "limitations": event["limitations"],
        "safety_and_authorization": event["safety_and_authorization"],
        "probe_class": event.get("probe_class", "local_safe"),
        "authorization_status": event.get("authorization_status", "not_required"),
        "safe_boundary": bool(event.get("safe_boundary")),
        "unexecuted_remainder_prohibited": bool(event.get("unexecuted_remainder_prohibited")),
        "universal_claim": bool(event.get("universal_claim")),
        "verification_context": {
            "actor": actor,
            "context_id": context_id,
            "fresh_context": bool(event.get("fresh_context")),
            "independent": bool(event.get("independent")),
        },
    }
    if event.get("census") is not None:
        evidence["census"] = event["census"]
    run: dict[str, Any] = {
        "record_type": "review_run",
        "review_run_id": run_id,
        "run_kind": run_kind,
        "cycle": cycle,
        "candidate_finding_ids": [finding_id],
        "source_record_ids": [evidence_id],
        "dedup_evidence_id": evidence_id,
    }
    frozen_boundary: set[str] | None = None
    for prior_run in prior:
        if (
            prior_run.get("record_type") == "review_run"
            and prior_run.get("run_kind") == "convergence_checkpoint"
        ):
            frozen_boundary = set(_string_items(prior_run.get("frozen_boundary", [])))
    if frozen_boundary is not None and str(finding_id) not in frozen_boundary:
        # A post-convergence review may discover a genuinely new deviation.
        # Derive this mechanically so callers do not hand-author protocol
        # bookkeeping merely to continue a bounded review/fix/review loop.
        run["deviation_ids"] = [str(finding_id)]
    for field in ("frozen_boundary", "deviation_ids", "reopened_finding_ids"):
        if event.get(field) is not None:
            run[field] = list(event[field])
    synthesis: dict[str, Any] = {
        "record_type": "finding_synthesis",
        "record_id": synthesis_id,
        "review_run_id": run_id,
        "cycle": cycle,
        "finding_id": finding_id,
        **provisional,
        "source_lanes": source_lanes,
        "blocking_required_lanes": blocking_lanes,
        "approval_recheck_lanes": recheck_lanes,
        **{name: name in triggers for name in FULL_COUNCIL_TRIGGERS},
        "repair_execution_state": (
            "not_required"
            if derive_disposition(provisional) in {"not_issue", "dont_do_later"}
            else "completed"
            if run_kind in {"reverification", "convergence_checkpoint"}
            else "pending"
        ),
        "evidence_record_id": evidence_id,
        "decision_authority": "moderator",
        "disposition_rationale": event["disposition_rationale"],
    }
    synthesis["disposition"] = derive_disposition(synthesis)
    synthesis["blocking"] = derive_blocking(synthesis)
    synthesis["review_depth"] = derive_review_depth(synthesis)
    terminal_reverification = (
        run_kind == "reverification"
        and not blocking_lanes
        and (
            (
                synthesis["disposition"] in {"do_now", "maybe_later"}
                and synthesis["repair_execution_state"] == "completed"
            )
            or (
                synthesis["disposition"] in {"not_issue", "dont_do_later"}
                and synthesis["repair_execution_state"] == "not_required"
            )
        )
    )
    if terminal_reverification and (
        event.get("fresh_context") is not True
        or event.get("independent") is not True
    ):
        return (), (
            "terminal reverification requires fresh_context=true and "
            "independent=true unless a distinct operator waiver is recorded",
        )
    if prior_head is not None:
        synthesis["supersedes_record_id"] = prior_head["record_id"]
    if _nonempty_string(promotion_trigger):
        synthesis["promotion_trigger"] = promotion_trigger

    rows: list[dict[str, Any]] = [evidence]
    if prior_head is not None:
        cleared = set(prior_head.get("blocking_required_lanes", [])) - set(blocking_lanes)
        if cleared:
            if cleared != {actor} or event.get("fresh_context") is not True or event.get("independent") is not True:
                return (), ("clearing a required lane requires the same fresh independent actor",)
            reassessment_id = _unique_record_id([*prior, *rows], "ev-reassess", str(finding_id))
            reassessment = dict(evidence)
            reassessment.update(
                {
                    "evidence_record_id": reassessment_id,
                    "claim_kind": "lane_reassessment",
                    "required_for_approval": False,
                    "proposition": f"{actor} independently reassessed {finding_id} after repair",
                }
            )
            rows.append(reassessment)
            synthesis["lane_reassessment_evidence_id"] = reassessment_id
    rows.extend([run, synthesis])
    if (
        run_kind == "reverification"
        and cycle == 2
        and not any(
            record.get("record_type") == "review_run"
            and record.get("run_kind") == "convergence_checkpoint"
            for record in prior
        )
    ):
        combined = (*prior, *rows)
        completed_cycles, _cycle_errors = _repair_cycle_progress(combined)
        if {1, 2}.issubset(completed_cycles):
            checkpoint_id = _unique_record_id(
                combined, "run", f"convergence-{cycle}"
            )
            rows.append(
                {
                    "record_type": "review_run",
                    "review_run_id": checkpoint_id,
                    "run_kind": "convergence_checkpoint",
                    "cycle": cycle,
                    "candidate_finding_ids": [],
                    "source_record_ids": [],
                    "dedup_evidence_id": None,
                    "frozen_boundary": sorted(current_synthesis_heads(combined)),
                    "verification_context": {
                        "actor": actor,
                        "context_id": context_id,
                        "fresh_context": bool(event.get("fresh_context")),
                        "independent": bool(event.get("independent")),
                    },
                }
            )
    return tuple(rows), ()


def _marker_version(text: str) -> tuple[int | None, list[str]]:
    # Applicability is a wave-header declaration, not a phrase that prose,
    # examples, or archived evidence can accidentally activate.
    header_end = text.find("\n## ")
    header = text if header_end < 0 else text[:header_end]
    matches = list(_MARKER_RE.finditer(header))
    if not matches:
        return None, []
    if len(matches) != 1:
        return None, ["review evidence marker must appear exactly once"]
    return int(matches[0].group("version")), []


def _parse_records(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    text = _canonicalize_finding_synthesis_markers(text)
    errors: list[str] = []
    section_matches = list(_SECTION_RE.finditer(text))
    if len(section_matches) != 1:
        return [], ["marked wave must contain exactly one `## Finding Synthesis` section"]
    body = section_matches[0].group("body")
    marker_begin = body.find(FINDING_SYNTHESIS_MARKER_BEGIN)
    marker_end = body.find(FINDING_SYNTHESIS_MARKER_END)
    if body.count(FINDING_SYNTHESIS_MARKER_BEGIN) != 1 or body.count(FINDING_SYNTHESIS_MARKER_END) != 1:
        errors.append("Finding Synthesis must contain exactly one canonical owned marker pair")
    elif marker_begin > marker_end:
        errors.append("Finding Synthesis owned markers are out of order")
    fences = list(_JSONL_FENCE_RE.finditer(body))
    if len(fences) != 1:
        return [], ["Finding Synthesis must contain exactly one fenced `jsonl` block"]
    if (
        marker_begin >= 0
        and marker_end >= 0
        and not (
            marker_begin + len(FINDING_SYNTHESIS_MARKER_BEGIN) <= fences[0].start()
            and fences[0].end() <= marker_end
        )
    ):
        errors.append("Finding Synthesis `jsonl` block must be enclosed by the canonical owned marker pair")
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(fences[0].group("body").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"Finding Synthesis JSONL line {line_number}: invalid JSON ({exc.msg})")
            continue
        if not isinstance(value, dict):
            errors.append(f"Finding Synthesis JSONL line {line_number}: record must be an object")
            continue
        records.append(value)
    return records, errors


def _require_fields(record: Mapping[str, Any], required: frozenset[str], optional: frozenset[str], label: str) -> list[str]:
    errors: list[str] = []
    missing = sorted(required - record.keys())
    unknown = sorted(record.keys() - required - optional)
    if missing:
        errors.append(f"{label}: missing fields: {', '.join(missing)}")
    if unknown:
        errors.append(f"{label}: unknown fields: {', '.join(unknown)}")
    return errors


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: object, *, allow_empty: bool = True) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_nonempty_string(item) for item in value)
        and len(value) == len(set(value))
    )


def _string_items(value: object) -> list[str]:
    """Return safe string members after shape errors have already been recorded."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _enum_error(record: Mapping[str, Any], field: str, allowed: Iterable[object], label: str) -> str | None:
    if record.get(field) not in allowed:
        return f"{label}: `{field}` has unknown value {record.get(field)!r}"
    return None


def _validate_event_metadata(
    record: Mapping[str, Any], label: str, *, expected_event: str | None = None
) -> list[str]:
    errors: list[str] = []
    has_identity = EVENT_IDENTITY_FIELD in record
    has_digest = REQUEST_DIGEST_FIELD in record
    if has_identity != has_digest:
        return [f"{label}: event_identity and request_digest must appear together"]
    if not has_identity:
        return errors
    identity = record.get(EVENT_IDENTITY_FIELD)
    if not isinstance(identity, dict):
        return [f"{label}: event_identity must be an object"]
    event_kind = identity.get("event")
    required = {"wave_id", "event", "actor", "context_id"}
    if event_kind == "approval":
        required.add("signoff_key")
    elif event_kind == "finding":
        required.update({"finding_id", "run_kind", "cycle"})
    elif event_kind == "run":
        required.update({"run_kind", "cycle"})
    else:
        errors.append(f"{label}: event_identity has unknown event {event_kind!r}")
    if set(identity) != required:
        missing = sorted(required - identity.keys())
        unknown = sorted(identity.keys() - required)
        if missing:
            errors.append(f"{label}: event_identity missing fields: {', '.join(missing)}")
        if unknown:
            errors.append(f"{label}: event_identity unknown fields: {', '.join(unknown)}")
    if expected_event is not None and event_kind != expected_event:
        errors.append(f"{label}: event_identity event must be {expected_event!r}")
    if not isinstance(identity.get("wave_id"), str) or re.fullmatch(
        r"[0-9a-z]{5,6}", str(identity.get("wave_id", ""))
    ) is None:
        errors.append(f"{label}: event_identity wave_id must be a 5- or 6-character lifecycle ID")
    for field in ("actor", "context_id"):
        if not _nonempty_string(identity.get(field)):
            errors.append(f"{label}: event_identity {field} must be a non-empty string")
    if event_kind == "approval" and not _nonempty_string(identity.get("signoff_key")):
        errors.append(f"{label}: event_identity signoff_key must be a non-empty string")
    if event_kind == "finding" and not _nonempty_string(identity.get("finding_id")):
        errors.append(f"{label}: event_identity finding_id must be a non-empty string")
    if event_kind in {"finding", "run"}:
        if identity.get("run_kind") not in RUN_KINDS:
            errors.append(f"{label}: event_identity run_kind is invalid")
        cycle = identity.get("cycle")
        if isinstance(cycle, bool) or not isinstance(cycle, int) or cycle < 0:
            errors.append(f"{label}: event_identity cycle must be a non-negative integer")
    digest = record.get(REQUEST_DIGEST_FIELD)
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        errors.append(f"{label}: request_digest must be a lowercase SHA-256 hex digest")
    context = record.get("verification_context")
    if isinstance(context, dict):
        if identity.get("actor") != context.get("actor"):
            errors.append(f"{label}: event_identity actor must match verification_context")
        if identity.get("context_id") != context.get("context_id"):
            errors.append(f"{label}: event_identity context_id must match verification_context")
    if event_kind == "run":
        if identity.get("run_kind") != record.get("run_kind"):
            errors.append(f"{label}: event_identity run_kind must match its leading record")
        if identity.get("cycle") != record.get("cycle"):
            errors.append(f"{label}: event_identity cycle must match its leading record")
    if event_kind == "approval":
        expected_claim = f"approval:{identity.get('signoff_key')}"
        if record.get("claim_id") != expected_claim:
            errors.append(f"{label}: event_identity signoff_key must match claim_id")
    if event_kind == "finding" and record.get("claim_id") != identity.get("finding_id"):
        errors.append(f"{label}: event_identity finding_id must match claim_id")
    return errors


def _validate_run_shape(record: Mapping[str, Any], index: int) -> list[str]:
    label = f"review_run[{index}]"
    errors = _require_fields(record, _RUN_REQUIRED, _RUN_OPTIONAL, label)
    if not _nonempty_string(record.get("review_run_id")):
        errors.append(f"{label}: `review_run_id` must be a non-empty string")
    candidates = record.get("candidate_finding_ids")
    if candidates or record.get("dedup_evidence_id") is not None:
        if not _nonempty_string(record.get("dedup_evidence_id")):
            errors.append(f"{label}: `dedup_evidence_id` must be a non-empty string for a non-empty run")
    if not isinstance(record.get("cycle"), int) or isinstance(record.get("cycle"), bool) or record.get("cycle", -1) < 0:
        errors.append(f"{label}: `cycle` must be a non-negative integer")
    enum_error = _enum_error(record, "run_kind", RUN_KINDS, label)
    if enum_error:
        errors.append(enum_error)
    for field in ("candidate_finding_ids", "source_record_ids", "deviation_ids", "reopened_finding_ids"):
        if field in record and not _string_list(record.get(field)):
            errors.append(f"{label}: `{field}` must be a duplicate-free string list")
    if record.get("run_kind") == "convergence_checkpoint":
        if not _string_list(record.get("frozen_boundary")):
            errors.append(f"{label}: convergence_checkpoint requires duplicate-free `frozen_boundary`")
    elif "frozen_boundary" in record:
        errors.append(f"{label}: `frozen_boundary` is only valid on convergence_checkpoint")
    if "verification_context" in record:
        context = record.get("verification_context")
        if not isinstance(context, dict):
            errors.append(f"{label}: `verification_context` must be an object")
        else:
            errors.extend(
                _require_fields(
                    context,
                    _VERIFICATION_CONTEXT_REQUIRED,
                    frozenset(),
                    f"{label}.verification_context",
                )
            )
            for field in ("actor", "context_id"):
                if not _nonempty_string(context.get(field)):
                    errors.append(
                        f"{label}.verification_context: `{field}` must be a non-empty string"
                    )
            for field in ("fresh_context", "independent"):
                if not isinstance(context.get(field), bool):
                    errors.append(f"{label}.verification_context: `{field}` must be boolean")
    errors.extend(_validate_event_metadata(record, label, expected_event="run"))
    return errors


def _validate_evidence_shape(record: Mapping[str, Any], index: int) -> list[str]:
    label = f"executable_evidence[{index}]"
    errors = _require_fields(record, _EVIDENCE_REQUIRED, _EVIDENCE_OPTIONAL, label)
    for field in (
        "evidence_record_id",
        "claim_id",
        "proposition",
        "counterexample_or_failure_condition",
        "public_path",
        "command_or_fixture",
        "expected",
        "observed",
        "artifact_or_test_id",
        "known_bad_detection_method",
        "limitations",
        "safety_and_authorization",
    ):
        if not _nonempty_string(record.get(field)):
            errors.append(f"{label}: `{field}` must be a non-empty string")
    for field, allowed in (
        ("claim_kind", EVIDENCE_CLAIM_KINDS),
        ("phase", EVIDENCE_PHASES),
        ("execution_status", EVIDENCE_STATUSES),
        ("probe_class", PROBE_CLASSES),
        ("authorization_status", AUTHORIZATION_STATUSES),
    ):
        enum_error = _enum_error(record, field, allowed, label)
        if enum_error:
            errors.append(enum_error)
    for field in (
        "required_for_approval",
        "safe_boundary",
        "unexecuted_remainder_prohibited",
        "universal_claim",
        "test_ran_without_unintended_skip",
        "public_path_reached",
        "boundary_values_realistic",
        "assertions_non_vacuous",
        "known_bad_detected",
    ):
        if not isinstance(record.get(field), bool):
            errors.append(f"{label}: `{field}` must be boolean")
    if not _string_list(record.get("adjacent_controls")):
        errors.append(f"{label}: `adjacent_controls` must be a duplicate-free string list")

    context = record.get("verification_context")
    if not isinstance(context, dict):
        errors.append(f"{label}: `verification_context` must be an object")
    else:
        errors.extend(
            _require_fields(
                context,
                _VERIFICATION_CONTEXT_REQUIRED,
                frozenset(),
                f"{label}.verification_context",
            )
        )
        for field in ("actor", "context_id"):
            if not _nonempty_string(context.get(field)):
                errors.append(f"{label}.verification_context: `{field}` must be a non-empty string")
        for field in ("fresh_context", "independent"):
            if not isinstance(context.get(field), bool):
                errors.append(f"{label}.verification_context: `{field}` must be boolean")

    if record.get("required_for_approval") is True:
        if record.get("phase") != "delivery" or record.get("execution_status") != "executed":
            errors.append(
                f"{label}: required approval evidence must be executed in delivery"
            )
    if record.get("claim_kind") == "approval":
        if not str(record.get("claim_id", "")).startswith("approval:"):
            errors.append(f"{label}: approval evidence claim_id must use `approval:<signoff-key>`")
        if record.get("required_for_approval") is not True:
            errors.append(f"{label}: approval evidence must be required_for_approval")
    integrity_fields = (
        "test_ran_without_unintended_skip",
        "public_path_reached",
        "boundary_values_realistic",
        "assertions_non_vacuous",
        "known_bad_detected",
    )
    if record.get("execution_status") == "executed" and any(
        record.get(field) is not True for field in integrity_fields
    ):
        errors.append(
            f"{label}: executed evidence requires all five evidence-integrity checks"
        )
    if record.get("claim_kind") == "lane_reassessment":
        if record.get("phase") != "delivery" or record.get("execution_status") != "executed":
            errors.append(f"{label}: lane reassessment evidence must be executed in delivery")
        if not isinstance(context, dict) or context.get("fresh_context") is not True or context.get("independent") is not True:
            errors.append(f"{label}: lane reassessment evidence must be fresh and independent")
    if record.get("probe_class") == "external_or_destructive":
        if record.get("execution_status") == "executed" and record.get("authorization_status") != "authorized":
            errors.append(f"{label}: external/destructive execution requires explicit authorization")
    elif record.get("authorization_status") == "authorized":
        errors.append(f"{label}: authorization is only meaningful for external/destructive probes")
    if record.get("authorization_status") == "not_authorized" and record.get("execution_status") in {"executed", "not_applicable"}:
        errors.append(f"{label}: an unauthorized probe must remain inferred or unverified")
    if record.get("safe_boundary") is True:
        if record.get("execution_status") != "inferred" or record.get("unexecuted_remainder_prohibited") is not True:
            errors.append(
                f"{label}: safe-boundary evidence must be inferred with an explicitly prohibited unexecuted remainder"
            )
    elif record.get("unexecuted_remainder_prohibited") is True:
        errors.append(f"{label}: prohibited remainder is valid only for safe-boundary evidence")

    census = record.get("census")
    if record.get("universal_claim") is True and not isinstance(census, dict):
        errors.append(f"{label}: universal_claim requires a census object")
    if census is not None:
        if not isinstance(census, dict):
            errors.append(f"{label}: `census` must be an object")
        else:
            errors.extend(_require_fields(census, _CENSUS_REQUIRED, frozenset(), f"{label}.census"))
            for field in (
                "claim",
                "boundary",
                "inclusion_policy",
                "index_freshness",
                "residual_uncertainty",
            ):
                if not _nonempty_string(census.get(field)):
                    errors.append(f"{label}.census: `{field}` must be a non-empty string")
            for field in ("tools_and_queries", "enumerated_sites", "registration_checks", "exclusions", "tool_errors"):
                if not _string_list(census.get(field)):
                    errors.append(f"{label}.census: `{field}` must be a duplicate-free string list")
            if not isinstance(census.get("total_count"), int) or isinstance(census.get("total_count"), bool) or census.get("total_count", -1) < 0:
                errors.append(f"{label}.census: `total_count` must be a non-negative integer")
            for field in ("result_truncated", "universe_closed"):
                if not isinstance(census.get(field), bool):
                    errors.append(f"{label}.census: `{field}` must be boolean")
            for field, allowed in (
                ("index_freshness", CENSUS_FRESHNESS),
                ("residual_uncertainty_status", CENSUS_UNCERTAINTY),
            ):
                enum_error = _enum_error(census, field, allowed, f"{label}.census")
                if enum_error:
                    errors.append(enum_error)
            enumerated = census.get("enumerated_sites")
            total = census.get("total_count")
            if isinstance(enumerated, list) and isinstance(total, int) and total != len(enumerated):
                errors.append(f"{label}.census: total_count must equal the enumerated_sites count")
            closed = (
                census.get("universe_closed") is True
                and census.get("result_truncated") is False
                and not census.get("tool_errors")
                and census.get("index_freshness") == "current"
                and census.get("residual_uncertainty_status") == "none"
            )
            if not closed and record.get("execution_status") != "unverified":
                errors.append(f"{label}: an open, stale, uncertain, truncated, or tool-failed census must be unverified")
    expected_event = None
    if record.get("claim_kind") == "approval":
        expected_event = "approval"
    elif record.get("claim_kind") == "finding":
        expected_event = "finding"
    errors.extend(_validate_event_metadata(record, label, expected_event=expected_event))
    return errors


def _validate_synthesis_shape(record: Mapping[str, Any], index: int, *, closure: bool) -> list[str]:
    label = f"finding_synthesis[{index}]"
    errors = _require_fields(record, _SYNTHESIS_REQUIRED, _SYNTHESIS_OPTIONAL, label)
    for field in (
        "record_id", "review_run_id", "finding_id", "evidence_record_id", "disposition_rationale"
    ):
        if not _nonempty_string(record.get(field)):
            errors.append(f"{label}: `{field}` must be a non-empty string")
    if not isinstance(record.get("cycle"), int) or isinstance(record.get("cycle"), bool) or record.get("cycle", -1) < 0:
        errors.append(f"{label}: `cycle` must be a non-negative integer")

    enums = {
        "validation_status": VALIDATION_STATUSES,
        "scope_relation": SCOPE_RELATIONS,
        "contract_relevance": CONTRACT_RELEVANCES,
        "supported_reachability": TRISTATE,
        "attacker_reachability": TRISTATE,
        "authority_domain": AUTHORITY_DOMAINS,
        "authority_delta": AUTHORITY_DELTAS,
        "observable_impact": OBSERVABLE_IMPACTS,
        "containment": CONTAINMENTS,
        "fix_risk": FIX_RISKS,
        "optional_value": OPTIONAL_VALUES,
        "repair_scope_bounded": REPAIR_SCOPE_BOUNDED,
        "repair_safety": REPAIR_SAFETIES,
        "benefit_vs_fix_risk": BENEFIT_VS_FIX_RISKS,
        "rejection_basis": REJECTION_BASES,
        "disposition": DISPOSITIONS,
        "decision_authority": DECISION_AUTHORITIES,
        "review_depth": REVIEW_DEPTHS,
        "repair_execution_state": REPAIR_EXECUTION_STATES,
    }
    for field, allowed in enums.items():
        enum_error = _enum_error(record, field, allowed, label)
        if enum_error:
            errors.append(enum_error)
    for field in ("supported_reachability", "attacker_reachability", "repair_scope_bounded"):
        value = record.get(field)
        if not (isinstance(value, bool) or value == "unverified"):
            errors.append(f"{label}: `{field}` must be boolean or `unverified`")
    for field in ("introduced_or_worsened_by_wave", "blocking", *FULL_COUNCIL_TRIGGERS):
        if record.get(field) not in {False, True} or not isinstance(record.get(field), bool):
            errors.append(f"{label}: `{field}` must be boolean")
    for field in ("source_lanes", "blocking_required_lanes"):
        if not _string_list(record.get(field)):
            errors.append(f"{label}: `{field}` must be a duplicate-free string list")
    if "approval_recheck_lanes" in record and not _string_list(record.get("approval_recheck_lanes")):
        errors.append(f"{label}: `approval_recheck_lanes` must be a duplicate-free string list")
    if isinstance(record.get("source_lanes"), list) and isinstance(record.get("blocking_required_lanes"), list):
        unknown_lanes = set(_string_items(record["blocking_required_lanes"])) - set(
            _string_items(record["source_lanes"])
        )
        if unknown_lanes:
            errors.append(f"{label}: blocking required lanes must also appear in source_lanes")

    expected_disposition = derive_disposition(record)
    expected_blocking = derive_blocking(record)
    expected_depth = derive_review_depth(record)
    if record.get("disposition") != expected_disposition:
        errors.append(f"{label}: disposition must be derived as `{expected_disposition}`")
    if record.get("blocking") is not expected_blocking:
        errors.append(f"{label}: blocking must be derived as {str(expected_blocking).lower()}")
    if record.get("review_depth") != expected_depth:
        errors.append(f"{label}: review_depth must be derived as `{expected_depth}`")

    disposition = expected_disposition
    rejection_basis = record.get("rejection_basis")
    repair_state = record.get("repair_execution_state")
    if disposition in {"do_now", "maybe_later", "not_issue"} and rejection_basis != "none":
        errors.append(f"{label}: {disposition} requires rejection_basis `none`")
    if disposition == "dont_do_later" and rejection_basis == "none":
        errors.append(f"{label}: dont_do_later requires a non-none rejection_basis")
    if rejection_basis in {"insufficient_evidence", "unsupported_reachability", "disproportionate_repair"}:
        if not _nonempty_string(record.get("promotion_trigger")):
            errors.append(f"{label}: rejection basis `{rejection_basis}` requires promotion_trigger")
    elif "promotion_trigger" in record:
        errors.append(f"{label}: promotion_trigger is not valid for rejection basis `{rejection_basis}`")

    if disposition in {"not_issue", "dont_do_later"}:
        if repair_state != "not_required":
            errors.append(f"{label}: {disposition} requires repair_execution_state `not_required`")
        if "follow_on_id" in record:
            errors.append(f"{label}: {disposition} must not create follow-on debt")
    elif repair_state not in {"pending", "completed", "operator_waived"}:
        errors.append(f"{label}: actionable disposition requires pending, completed, or operator_waived repair state")
    waiver_fields = ("waiver_id", "waiver_scope", "waiver_reason", "waiver_risk")
    if repair_state == "operator_waived":
        if record.get("decision_authority") != "operator":
            errors.append(f"{label}: operator_waived requires decision_authority `operator`")
        for field in waiver_fields:
            if not _nonempty_string(record.get(field)):
                errors.append(f"{label}: operator_waived requires `{field}`")
    elif any(field in record for field in waiver_fields):
        errors.append(f"{label}: waiver fields are valid only for operator_waived state")

    if record.get("blocking_required_lanes") and not expected_blocking:
        errors.append(f"{label}: non-blocking synthesis cannot retain blocking_required_lanes")
    return errors


def _safe_material_blocker(record: Mapping[str, Any]) -> bool:
    return bool(
        derive_blocking(record)
        and record.get("supported_reachability") is True
        and record.get("observable_impact") in {"material", "critical"}
        and _nonempty_string(record.get("evidence_record_id"))
    )


def _repair_cycle_progress(
    records: Iterable[Mapping[str, Any]],
) -> tuple[frozenset[int], tuple[str, ...]]:
    """Derive aggregate repair-cycle completion across per-finding and batch runs."""

    rows = [dict(record) for record in records]
    runs = [record for record in rows if record.get("record_type") == "review_run"]
    by_run: dict[str, list[dict[str, Any]]] = {}
    evidence_by_id = {
        str(record.get("evidence_record_id")): record
        for record in rows
        if record.get("record_type") == "executable_evidence"
        and isinstance(record.get("evidence_record_id"), str)
    }
    for record in rows:
        if record.get("record_type") == "finding_synthesis":
            by_run.setdefault(str(record.get("review_run_id")), []).append(record)

    initial_delivery_positions: list[int] = []
    starts: dict[int, dict[str, int]] = {}
    terminal: dict[int, set[str]] = {}
    completed: set[int] = set()
    errors: list[str] = []

    for position, run in enumerate(runs):
        cycle = run.get("cycle")
        kind = run.get("run_kind")
        if not isinstance(cycle, int) or isinstance(cycle, bool):
            continue
        if kind == "initial_delivery":
            initial_delivery_positions.append(position)
            continue
        run_syntheses = by_run.get(str(run.get("review_run_id")), [])
        actionable = [
            row
            for row in run_syntheses
            if derive_disposition(row) in {"do_now", "maybe_later"}
        ]
        if kind == "repair_start":
            if cycle < 1:
                errors.append(
                    f"review run `{run.get('review_run_id')}` repair_start requires cycle >= 1"
                )
            if not initial_delivery_positions or initial_delivery_positions[0] >= position:
                errors.append(
                    f"review run `{run.get('review_run_id')}` repair_start requires preceding initial_delivery synthesis"
                )
            if cycle > 1 and cycle - 1 not in completed:
                errors.append(
                    f"repair cycle {cycle} starts before cycle {cycle - 1} completes"
                )
            if cycle in completed:
                errors.append(
                    f"repair cycle {cycle} cannot add a repair_start after aggregate completion"
                )
            if not actionable:
                errors.append(
                    f"review run `{run.get('review_run_id')}` repair_start requires an actionable synthesis row"
                )
            cycle_starts = starts.setdefault(cycle, {})
            for row in actionable:
                finding_id = row.get("finding_id")
                if not isinstance(finding_id, str):
                    continue
                if finding_id in cycle_starts:
                    errors.append(
                        f"repair cycle {cycle} has more than one repair_start for `{finding_id}`"
                    )
                else:
                    cycle_starts[finding_id] = position
        elif kind in {"reverification", "convergence_checkpoint"}:
            if kind == "reverification" and not run_syntheses:
                errors.append(
                    f"review run `{run.get('review_run_id')}` reverification requires a synthesis row"
                )
            cycle_starts = starts.get(cycle, {})
            cycle_terminal = terminal.setdefault(cycle, set())
            # A reverification may truthfully reclassify a started finding as
            # non-actionable. Convergence checkpoints, however, may also carry
            # newly observed non-actionable boundary rows that were never part
            # of the repair cycle; only their actionable rows participate.
            progress_rows = run_syntheses if kind == "reverification" else actionable
            for row in progress_rows:
                finding_id = row.get("finding_id")
                if not isinstance(finding_id, str):
                    continue
                start_position = cycle_starts.get(finding_id)
                if start_position is None or start_position >= position:
                    errors.append(
                        f"reverification cycle {cycle} for `{finding_id}` has no preceding repair_start"
                    )
                    continue
                if finding_id in cycle_terminal and kind == "reverification":
                    errors.append(
                        f"repair cycle {cycle} cannot reverify terminal finding `{finding_id}` again"
                    )
                    continue
                no_required_lanes = not _string_items(
                    row.get("blocking_required_lanes", [])
                )
                repair_state = row.get("repair_execution_state")
                disposition = derive_disposition(row)
                actionable_terminal = (
                    disposition in {"do_now", "maybe_later"}
                    and repair_state in {"completed", "operator_waived"}
                )
                reclassified_terminal = (
                    disposition in {"not_issue", "dont_do_later"}
                    and repair_state == "not_required"
                )
                if no_required_lanes and (
                    actionable_terminal or reclassified_terminal
                ):
                    if repair_state != "operator_waived":
                        evidence = evidence_by_id.get(
                            str(row.get("evidence_record_id"))
                        )
                        context = (
                            evidence.get("verification_context")
                            if isinstance(evidence, Mapping)
                            else None
                        )
                        if not isinstance(context, Mapping) or (
                            context.get("fresh_context") is not True
                            or context.get("independent") is not True
                        ):
                            errors.append(
                                f"terminal reverification cycle {cycle} for "
                                f"`{finding_id}` requires fresh independent evidence"
                            )
                            continue
                    cycle_terminal.add(finding_id)
            started_findings = set(cycle_starts)
            if started_findings and started_findings.issubset(cycle_terminal):
                completed.add(cycle)

    return frozenset(completed), tuple(errors)


def _validate_relationships(records: list[dict[str, Any]], *, closure: bool) -> list[str]:
    errors: list[str] = []
    runs: list[dict[str, Any]] = [record for record in records if record.get("record_type") == "review_run"]
    syntheses: list[dict[str, Any]] = [record for record in records if record.get("record_type") == "finding_synthesis"]
    evidence_rows: list[dict[str, Any]] = [
        record for record in records if record.get("record_type") == "executable_evidence"
    ]
    if not runs:
        # A newly-created planned wave opts into the protocol before any review
        # claim exists.  Its empty marker-owned JSONL block is valid; lifecycle
        # gates require the phase-appropriate run before readiness/review, and
        # closure always requires at least one sealed run.
        return ["marked wave requires at least one Review Run Record before closure"] if closure else []

    run_ids: dict[str, dict[str, Any]] = {}
    record_ids: dict[str, dict[str, Any]] = {}
    evidence_ids: dict[str, dict[str, Any]] = {}
    run_positions: dict[str, int] = {}
    for position, run in enumerate(runs):
        run_id = run.get("review_run_id")
        if isinstance(run_id, str):
            if run_id in run_ids:
                errors.append(f"duplicate review_run_id `{run_id}`")
            else:
                run_ids[run_id] = run
                run_positions[run_id] = position
    for synthesis in syntheses:
        record_id = synthesis.get("record_id")
        if isinstance(record_id, str):
            if record_id in record_ids:
                errors.append(f"duplicate synthesis record_id `{record_id}`")
            else:
                record_ids[record_id] = synthesis
    for evidence in evidence_rows:
        evidence_id = evidence.get("evidence_record_id")
        if isinstance(evidence_id, str):
            if evidence_id in evidence_ids:
                errors.append(f"duplicate executable evidence_record_id `{evidence_id}`")
            else:
                evidence_ids[evidence_id] = evidence

    if closure and not any(
        evidence.get("claim_kind") == "approval"
        and evidence.get("required_for_approval") is True
        and evidence.get("phase") == "delivery"
        and evidence.get("execution_status") == "executed"
        for evidence in evidence_rows
    ):
        errors.append("marked wave closure requires executed delivery evidence for a required approval")

    for run in runs:
        evidence_id = run.get("dedup_evidence_id")
        candidates = _string_items(run.get("candidate_finding_ids", []))
        if not candidates and evidence_id is None:
            continue
        evidence = evidence_ids.get(str(evidence_id))
        if evidence is None:
            errors.append(
                f"review run `{run.get('review_run_id')}` references missing dedup executable evidence `{evidence_id}`"
            )
        elif evidence.get("claim_kind") not in {"dedup", "census"} and not (
            len(candidates) == 1
            and evidence.get("claim_kind") == "finding"
            and evidence.get("claim_id") == candidates[0]
        ):
            errors.append(
                f"review run `{run.get('review_run_id')}` sealed-universe evidence must be dedup/census or its sole finding evidence"
            )
        elif evidence.get("execution_status") != "executed":
            errors.append(
                f"review run `{run.get('review_run_id')}` dedup evidence must be executed"
            )
        elif records.index(evidence) > records.index(run):
            errors.append(
                f"review run `{run.get('review_run_id')}` cannot be sealed before its dedup evidence"
            )
    for synthesis in syntheses:
        evidence_id = synthesis.get("evidence_record_id")
        evidence = evidence_ids.get(str(evidence_id))
        if evidence is None:
            errors.append(
                f"synthesis `{synthesis.get('record_id')}` references missing executable evidence `{evidence_id}`"
            )
        elif evidence.get("claim_id") != synthesis.get("finding_id"):
            errors.append(
                f"synthesis `{synthesis.get('record_id')}` evidence claim_id must equal finding_id"
            )
        elif evidence.get("claim_kind") != "finding":
            errors.append(
                f"synthesis `{synthesis.get('record_id')}` evidence must have claim_kind `finding`"
            )
        elif records.index(evidence) > records.index(synthesis):
            errors.append(
                f"synthesis `{synthesis.get('record_id')}` cannot precede its executable finding evidence"
            )
        elif evidence.get("execution_status") in {"unverified", "not_applicable"} and derive_blocking(synthesis):
            errors.append(
                f"blocking synthesis `{synthesis.get('record_id')}` cannot rely on unverified/not_applicable evidence"
            )

    by_run: dict[str, list[dict[str, Any]]] = {}
    for synthesis in syntheses:
        run_id = synthesis.get("review_run_id")
        by_run.setdefault(str(run_id), []).append(synthesis)
        run = run_ids.get(str(run_id))
        if run is None:
            errors.append(f"synthesis `{synthesis.get('record_id')}` references unknown review run `{run_id}`")
        elif synthesis.get("cycle") != run.get("cycle"):
            errors.append(f"synthesis `{synthesis.get('record_id')}` cycle does not match its review run")
        elif records.index(synthesis) < records.index(run):
            errors.append(f"synthesis `{synthesis.get('record_id')}` cannot precede its sealing review run")

    for run_id, run in run_ids.items():
        candidates = run.get("candidate_finding_ids")
        if not isinstance(candidates, list):
            continue
        safe_candidates = _string_items(candidates)
        found = [row.get("finding_id") for row in by_run.get(run_id, []) if isinstance(row.get("finding_id"), str)]
        missing = sorted(set(safe_candidates) - set(found))
        extra = sorted(set(found) - set(safe_candidates))
        duplicates = sorted(item for item in set(found) if found.count(item) > 1)
        if missing:
            errors.append(f"review run `{run_id}` missing synthesis rows for: {', '.join(missing)}")
        if extra:
            errors.append(f"review run `{run_id}` has synthesis rows outside sealed candidates: {', '.join(extra)}")
        if duplicates:
            errors.append(f"review run `{run_id}` has duplicate synthesis rows for: {', '.join(duplicates)}")

    heads: dict[str, str] = {}
    used_reassessments: set[str] = set()
    ordered_syntheses = sorted(
        syntheses,
        key=lambda row: (run_positions.get(str(row.get("review_run_id")), 10**9), records.index(row)),
    )
    for row in ordered_syntheses:
        finding_id = row.get("finding_id")
        record_id = row.get("record_id")
        if not isinstance(finding_id, str) or not isinstance(record_id, str):
            continue
        supersedes = row.get("supersedes_record_id")
        prior_head = heads.get(finding_id)
        if prior_head is None:
            if supersedes is not None:
                errors.append(f"synthesis `{record_id}` supersedes a record before its finding chain begins")
        elif supersedes != prior_head:
            errors.append(f"synthesis `{record_id}` must supersede current head `{prior_head}`")
        if supersedes is not None:
            prior = record_ids.get(str(supersedes))
            if prior is None:
                errors.append(f"synthesis `{record_id}` supersedes unknown record `{supersedes}`")
            elif prior.get("finding_id") != finding_id:
                errors.append(f"synthesis `{record_id}` crosses finding supersession chains")
            else:
                cleared = set(_string_items(prior.get("blocking_required_lanes", []))) - set(
                    _string_items(row.get("blocking_required_lanes", []))
                )
                downgraded = prior.get("blocking") is True and row.get("blocking") is not True
                if cleared or downgraded:
                    waived = row.get("repair_execution_state") == "operator_waived"
                    reassessment = evidence_ids.get(str(row.get("lane_reassessment_evidence_id")))
                    context = reassessment.get("verification_context") if reassessment else None
                    reassessed = bool(
                        reassessment
                        and reassessment.get("claim_kind") == "lane_reassessment"
                        and reassessment.get("claim_id") == finding_id
                        and reassessment.get("execution_status") == "executed"
                        and reassessment.get("phase") == "delivery"
                        and isinstance(context, dict)
                        and cleared == {context.get("actor")}
                        and context.get("fresh_context") is True
                        and context.get("independent") is True
                    )
                    reassessment_id = str(row.get("lane_reassessment_evidence_id"))
                    if reassessed and reassessment_id in used_reassessments:
                        reassessed = False
                    elif reassessed:
                        used_reassessments.add(reassessment_id)
                    if not (waived or reassessed):
                        errors.append(
                            f"synthesis `{record_id}` cannot clear a required-lane block without lane reassessment evidence or operator waiver"
                        )
        heads[finding_id] = record_id

    for current in record_ids.values():
        if (
            derive_disposition(current) in {"do_now", "maybe_later"}
            and current.get("repair_execution_state") == "completed"
            and run_ids.get(str(current.get("review_run_id")), {}).get("run_kind")
            not in {"reverification", "convergence_checkpoint"}
        ):
            errors.append(
                f"synthesis `{current.get('record_id')}` for `{current.get('finding_id')}` may be completed only by reverification"
            )

    if closure:
        for finding_id, record_id in heads.items():
            current = record_ids[record_id]
            if derive_disposition(current) in {"do_now", "maybe_later"} and current.get(
                "repair_execution_state"
            ) not in {"completed", "operator_waived"}:
                errors.append(
                    f"current synthesis `{record_id}` for `{finding_id}` must be completed or operator-waived before closure"
                )
            if current.get("blocking_required_lanes"):
                errors.append(
                    f"current synthesis `{record_id}` for `{finding_id}` retains unresolved required lanes"
                )

    last_cycle = -1
    completed_cycles, cycle_errors = _repair_cycle_progress(records)
    errors.extend(cycle_errors)
    frozen_boundary: set[str] | None = None
    for position, run in enumerate(runs):
        cycle = run.get("cycle")
        kind = run.get("run_kind")
        if not isinstance(cycle, int) or isinstance(cycle, bool):
            continue
        if kind not in {"readiness", "initial_delivery"}:
            if cycle < last_cycle:
                errors.append(f"review run `{run.get('review_run_id')}` decreases the wave cycle")
            last_cycle = max(last_cycle, cycle)
        if kind in {"readiness", "initial_delivery"} and cycle != 0:
            errors.append(f"review run `{run.get('review_run_id')}` kind `{kind}` requires cycle 0")
        if kind == "convergence_checkpoint":
            if cycle < 2 or not {1, 2}.issubset(completed_cycles):
                errors.append("convergence_checkpoint requires two completed repair cycles")
            frozen_boundary = set(_string_items(run.get("frozen_boundary", [])))

        candidates_for_run = set(_string_items(run.get("candidate_finding_ids", [])))
        deviations_for_run = set(_string_items(run.get("deviation_ids", [])))
        reopened_for_run = set(_string_items(run.get("reopened_finding_ids", [])))
        if deviations_for_run - candidates_for_run:
            errors.append(f"review run `{run.get('review_run_id')}` deviation_ids must be sealed candidates")
        if reopened_for_run - candidates_for_run:
            errors.append(f"review run `{run.get('review_run_id')}` reopened_finding_ids must be sealed candidates")
        prior_findings = {
            row.get("finding_id")
            for prior_run in runs[:position]
            for row in by_run.get(str(prior_run.get("review_run_id")), [])
            if isinstance(row.get("finding_id"), str)
        }
        unknown_reopens = reopened_for_run - prior_findings
        if unknown_reopens:
            errors.append(
                f"review run `{run.get('review_run_id')}` reopens unknown findings: {', '.join(sorted(unknown_reopens))}"
            )

        if frozen_boundary is not None and kind != "convergence_checkpoint":
            for finding_id in candidates_for_run - frozen_boundary - deviations_for_run:
                row = next(
                    (item for item in by_run.get(str(run.get("review_run_id")), []) if item.get("finding_id") == finding_id),
                    None,
                )
                evidence = evidence_ids.get(str(row.get("evidence_record_id"))) if row else None
                safely_evidenced = bool(
                    row is not None
                    and _safe_material_blocker(row)
                    and evidence is not None
                    and (
                        evidence.get("execution_status") == "executed"
                        or (
                            evidence.get("safe_boundary") is True
                            and evidence.get("execution_status") == "inferred"
                            and evidence.get("unexecuted_remainder_prohibited") is True
                        )
                    )
                )
                if not safely_evidenced:
                    errors.append(
                        f"review run `{run.get('review_run_id')}` exceeds frozen boundary with `{finding_id}` without acknowledged deviation or safely evidenced material blocker"
                    )
    if {1, 2}.issubset(completed_cycles) and frozen_boundary is None:
        errors.append("two completed repair cycles require a convergence_checkpoint")
    return errors


def validate_review_evidence_records(
    records: Iterable[Mapping[str, Any]],
    *,
    closure: bool = False,
) -> tuple[str, ...]:
    """Validate already-parsed canonical records independent of their container."""

    rows = [dict(record) for record in records]
    errors: list[str] = []
    for index, record in enumerate(rows):
        record_type = record.get("record_type")
        if record_type == "review_run":
            errors.extend(_validate_run_shape(record, index))
        elif record_type == "executable_evidence":
            errors.extend(_validate_evidence_shape(record, index))
        elif record_type == "finding_synthesis":
            errors.extend(_validate_synthesis_shape(record, index, closure=closure))
        else:
            errors.append(f"record[{index}]: unknown record_type {record_type!r}")
    errors.extend(_validate_relationships(rows, closure=closure))
    return tuple(errors)


def read_review_event_ledger(
    wave_path: Path,
) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    """Read the fixed sibling ledger and validate its canonical byte envelope."""

    path_error = _review_authority_path_error(wave_path)
    if path_error:
        return (), (f"canonical review event ledger path is unsafe: {path_error}",)
    path = review_event_path(wave_path)
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return (), (f"canonical review event ledger is missing: {path.name}",)
    except OSError as exc:
        return (), (f"canonical review event ledger is unreadable: {exc}",)
    return parse_review_event_bytes(data)


def validate_external_review_evidence(
    wave_path: Path,
    *,
    closure: bool = False,
) -> ReviewEvidenceValidation:
    """Validate one wave directly from its declaration and fixed sibling ledger."""

    wave_md = Path(wave_path)
    if wave_md.name != "wave.md":
        wave_md = wave_md / "wave.md"
    path_error = _review_authority_path_error(wave_md)
    if path_error:
        authority_errors = (f"review authority path is unsafe: {path_error}",)
        return ReviewEvidenceValidation(
            None, (), authority_errors, authority_errors=authority_errors
        )
    try:
        text = _canonicalize_finding_synthesis_markers(
            wave_md.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError) as exc:
        authority_errors = (f"wave record is unreadable: {exc}",)
        return ReviewEvidenceValidation(
            None, (), authority_errors, authority_errors=authority_errors
        )
    source, source_errors = parse_review_evidence_source(text)
    if source != REVIEW_EVIDENCE_SOURCE:
        errors = list(source_errors)
        if source is None and not errors:
            errors.append(
                f"wave header must declare `{REVIEW_EVIDENCE_SOURCE_DECLARATION}`"
            )
        authority_errors = tuple(errors)
        return ReviewEvidenceValidation(
            None, (), authority_errors, authority_errors=authority_errors
        )
    projection_errors: list[str] = []
    marker, marker_errors = _marker_version(text)
    projection_errors.extend(marker_errors)
    if marker is not None:
        projection_errors.append(
            "external review evidence wave must not retain review-evidence-protocol"
        )
    section_matches = list(_SECTION_RE.finditer(text))
    if len(section_matches) != 1:
        projection_errors.append(
            "external wave must contain exactly one `## Finding Synthesis` projection"
        )
    else:
        body = section_matches[0].group("body")
        if body.count(FINDING_SYNTHESIS_MARKER_BEGIN) != 1 or body.count(
            FINDING_SYNTHESIS_MARKER_END
        ) != 1:
            projection_errors.append(
                "Finding Synthesis projection must contain exactly one canonical owned marker pair"
            )
        if _JSONL_FENCE_RE.search(body):
            projection_errors.append(
                "external Finding Synthesis projection must not embed a jsonl authority"
            )
    records, parse_errors = read_review_event_ledger(wave_md)
    authority_errors = [*source_errors, *parse_errors]
    authority_errors.extend(validate_review_evidence_records(records, closure=closure))
    errors = (*authority_errors, *projection_errors)
    return ReviewEvidenceValidation(
        PROTOCOL_VERSION,
        records,
        tuple(errors),
        authority_errors=tuple(authority_errors),
        projection_errors=tuple(projection_errors),
    )


def validate_review_evidence(
    text: str,
    *,
    previous_text: str | None = None,
    closure: bool = False,
) -> ReviewEvidenceValidation:
    """Parse and validate a wave record's prospective review evidence.

    ``previous_text`` enables monotonic marker checks.  ``closure`` adds the
    completed-or-operator-waived requirement for actionable current state.
    """
    marker, errors = _marker_version(text)
    previous_marker: int | None = None
    if previous_text is not None:
        previous_marker, previous_errors = _marker_version(previous_text)
        errors.extend(f"previous record: {error}" for error in previous_errors)
        if previous_marker is not None and marker is None:
            errors.append("review evidence protocol marker may not be removed")
        if previous_marker is not None and marker is not None and marker < previous_marker:
            errors.append("review evidence protocol marker may not be downgraded")
    if marker is None:
        return ReviewEvidenceValidation(None, (), tuple(errors))
    if marker != PROTOCOL_VERSION:
        errors.append(f"unsupported review evidence protocol version {marker}; expected {PROTOCOL_VERSION}")

    records, parse_errors = _parse_records(text)
    errors.extend(parse_errors)
    if previous_text is not None and previous_marker is not None and marker is not None:
        previous_records, previous_parse_errors = _parse_records(previous_text)
        errors.extend(f"previous record: {error}" for error in previous_parse_errors)
        if not previous_parse_errors and records[: len(previous_records)] != previous_records:
            errors.append(
                "review evidence records are append-only; previous records may not be removed or changed"
            )
    errors.extend(validate_review_evidence_records(records, closure=closure))
    return ReviewEvidenceValidation(marker, tuple(records), tuple(errors))


__all__ = [
    "ADOPTION_LEDGER_REL",
    "ADOPTION_LOCK_REL",
    "EVENTS_FILENAME",
    "EVENT_IDENTITY_FIELD",
    "FINDING_SYNTHESIS_MARKER_BEGIN",
    "FINDING_SYNTHESIS_MARKER_END",
    "FULL_COUNCIL_TRIGGERS",
    "PROTOCOL_VERSION",
    "REQUEST_DIGEST_FIELD",
    "REVIEW_STATUS_MARKER_BEGIN",
    "REVIEW_STATUS_MARKER_END",
    "REVIEW_EVIDENCE_SOURCE",
    "REVIEW_EVIDENCE_SOURCE_DECLARATION",
    "REVIEW_EVENT_HASH_DOMAIN",
    "ReviewEvidenceValidation",
    "adopted_legacy_inline_protocol_state_for_migration",
    "adopted_protocol_state",
    "build_compact_review_event",
    "build_identified_review_event",
    "canonicalize_finding_synthesis_markers",
    "canonical_review_event_bytes",
    "canonical_review_events_bytes",
    "current_synthesis_heads",
    "derive_review_event_identity",
    "derive_action_required",
    "derive_blocking",
    "derive_disposition",
    "derive_review_depth",
    "empty_external_finding_synthesis_section",
    "empty_finding_synthesis_section",
    "externalize_adopted_inline_wave_locked",
    "normalize_review_event_request",
    "parse_review_event_bytes",
    "parse_review_evidence_source",
    "read_review_event_ledger",
    "record_legacy_inline_protocol_state_for_migration",
    "record_protocol_state",
    "record_protocol_state_locked",
    "render_review_evidence_projection",
    "render_review_evidence_records",
    "render_review_status_projection",
    "review_event_path",
    "review_event_prefix_proof",
    "review_event_request_digest",
    "review_event_write_lock",
    "review_evidence_human_table",
    "review_evidence_summary",
    "review_evidence_summary_line",
    "review_status_human_table",
    "required_review_status_keys",
    "review_status_rows",
    "review_status_signoff_keys",
    "validate_adopted_protocol_state",
    "validate_external_review_evidence",
    "validate_review_evidence",
    "validate_review_evidence_records",
]
