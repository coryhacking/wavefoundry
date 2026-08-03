"""Executable-review event authority, validation, and projection helpers.

Runtime state lives only in a wave's fixed sibling ``events.jsonl``, the sole
machine authority for review evidence. The validator is semantic-fact agnostic:
it does not decide whether a finding is true or approve a wave; it validates
canonical bytes and relationships, derives actionability from the moderator's
finite facts, and renders the rebuildable Markdown current-state view.

There is deliberately no receipt ledger, checkpoint record, or hash chain: a
checksum stored alongside (or inside) the same local log cannot prove that its
own tail was not deleted, so restoring a complete older but internally valid
ledger is not locally detectable. Git or backups are the appropriate optional
historical authority when rollback investigation matters; ordinary corruption,
interruption, and concurrency are covered by canonical parsing, schema and
relationship validation, atomic replacement, cross-process locking, and
idempotent exact replay. Unmarked pre-protocol consumer waves remain prose-only
legacy records and are not rewritten by upgrade.
"""

from __future__ import annotations

import json
import hashlib
import re
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from runtime_lock import RuntimeFileLock, RuntimeLockBusy, RuntimeLockError
from review_policy import (
    GENESIS_RECEIPT_PARENT,
    REVIEW_POLICY_RECEIPT_RECORD_TYPE,
    current_policy_receipt,
    derive_receipt_id,
    normalize_wave_review_policy,
    receipt_semantic_fields,
    validate_policy_receipt,
)


PROTOCOL_VERSION = 1


class ProjectPublicationUnavailable(RuntimeError):
    """The project publication boundary could not be owned immediately."""
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
# Wave 1tb4z: the `<details>` wrapper survives ONLY on legacy inline-authority
# projections in ARCHIVES, where it collapses an embedded ```jsonl fence of
# machine records in rendered views. External-ledger projections (records in
# events.jsonl) emit a plain italic summary line instead — no HTML in a
# human-first document. Nothing renders the inline form anymore (wave 1to78
# deleted that machinery); the begin constant survives solely so the
# canonicalizer can normalize the legacy `wavefoundry-` class spelling on
# archived bodied blocks without rewriting them.
REVIEW_EVIDENCE_DETAILS_BEGIN = '<details class="wave-review-evidence">'
_LEGACY_REVIEW_EVIDENCE_DETAILS_BEGIN = '<details class="wavefoundry-review-evidence">'
# A BODYLESS details block (summary-close immediately followed by
# details-close, whitespace only) is the retired external-projection form;
# collapse it to the plain line. A bodied inline block always carries the
# jsonl fence between the two closes and is never matched.
_BODYLESS_DETAILS_RE = re.compile(
    r"<details class=\"wave(?:foundry)?-review-evidence\">\s*\n"
    r"<summary>(?P<summary>[^\n]*)</summary>\s*\n\s*</details>"
)
_LEGACY_REVIEW_SUMMARY_RE = re.compile(
    r"Machine review evidence — \d+ records; \d+ runs; "
    r"(?P<findings>\d+) findings; current: "
    r"(?P<current>do_now \d+, maybe_later \d+, dont_do_later \d+, not_issue \d+)"
)
# The adoption-shaped basename is an opaque compatibility ABI: 1.14+ processes
# coordinate on this exact path, so renaming it would silently break same-path
# cross-process serialization during upgrade. The symbol describes what the
# lock actually guards: project-global lifecycle/state publication.
PROJECT_STATE_PUBLICATION_LOCK_REL = Path(
    ".wavefoundry/locks/review-evidence-adoptions.lock"
)
EVENTS_FILENAME = "events.jsonl"
REVIEW_EVIDENCE_SOURCE = EVENTS_FILENAME
REVIEW_EVIDENCE_SOURCE_DECLARATION = f"review-evidence-source: {REVIEW_EVIDENCE_SOURCE}"
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

    text = text.replace(
        _LEGACY_FINDING_SYNTHESIS_MARKER_BEGIN,
        FINDING_SYNTHESIS_MARKER_BEGIN,
    ).replace(
        _LEGACY_FINDING_SYNTHESIS_MARKER_END,
        FINDING_SYNTHESIS_MARKER_END,
    )
    # Wave 1tb4z: collapse the retired bodyless-details external form to the
    # plain summary line, and normalize the legacy class spelling on bodied
    # inline blocks — archives validate as-is, never rewritten on disk.
    text = _BODYLESS_DETAILS_RE.sub(
        lambda m: review_evidence_plain_summary(m.group("summary")), text
    )
    # The former summary exposed record/run bookkeeping. It is equivalent to
    # the current-state-only form when the derived finding/disposition values
    # agree, so archived projections stay valid without a historical rewrite.
    text = _LEGACY_REVIEW_SUMMARY_RE.sub(
        lambda m: f"Machine review state — {m.group('findings')} findings; current: {m.group('current')}",
        text,
    )
    return text.replace(
        _LEGACY_REVIEW_EVIDENCE_DETAILS_BEGIN, REVIEW_EVIDENCE_DETAILS_BEGIN
    )


def review_evidence_plain_summary(summary_text: str) -> str:
    """The external-ledger projection's summary form (wave 1tb4z): plain markdown."""

    return f"*{summary_text}*"


def canonicalize_finding_synthesis_markers(text: str) -> str:
    """Normalize legacy presentation forms for validation without rewriting history."""

    return _canonicalize_finding_synthesis_markers(text)

REVIEW_EVENT_TYPES = ("approval", "finding", "run", "list")
REVIEW_WRITE_EVENT_TYPES = frozenset(REVIEW_EVENT_TYPES[:-1])
REVIEW_LIST_EVENT = REVIEW_EVENT_TYPES[-1]
RUN_KINDS = frozenset(
    {"readiness", "initial_delivery", "repair_start", "reverification", "convergence_checkpoint"}
)
EVIDENCE_PHASES = frozenset({"readiness", "delivery"})
APPROVAL_PHASES = EVIDENCE_PHASES
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
    {"approval_phase", "policy_receipt_id", "census", EVENT_IDENTITY_FIELD, REQUEST_DIGEST_FIELD}
)
INTEGRITY_CHECK_BOOLEAN_FIELDS = (
    "test_ran_without_unintended_skip",
    "public_path_reached",
    "boundary_values_realistic",
    "assertions_non_vacuous",
    "known_bad_detected",
)
INTEGRITY_CHECK_METHOD_FIELD = "known_bad_detection_method"
INTEGRITY_CHECK_FIELDS = frozenset(
    (*INTEGRITY_CHECK_BOOLEAN_FIELDS, INTEGRITY_CHECK_METHOD_FIELD)
)
# Wave 1tvbs: one exported vocabulary for guided review actions.  The action
# model contains only state-derived arguments; every judgment-bearing value
# remains an explicit caller input to wf_review_event.
REVIEW_FINDING_CORE_JUDGMENT_FIELDS = (
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
)
REVIEW_FINDING_REPAIR_JUDGMENT_FIELDS = (
    "fix_risk",
    "optional_value",
    "repair_scope_bounded",
    "repair_safety",
    "benefit_vs_fix_risk",
    "rejection_basis",
)
REVIEW_FINDING_REQUIRED_EVIDENCE_FIELDS = (
    "proposition",
    "failure_condition",
    "public_path",
    "command_or_fixture",
    "expected",
    "observed",
    "artifact_or_test_id",
    "limitations",
    "safety_and_authorization",
    "disposition_rationale",
)
REVIEW_APPROVAL_REQUIRED_EVIDENCE_FIELDS = (
    "observed",
    "artifact_or_test_id",
)
REVIEW_ACTION_CAP = 50
REVIEW_ACTION_KINDS = ("repair_start", "reverification", "approval")
REVIEW_ACTION_FIELDS = (
    "action_id",
    "action_kind",
    "actor_role",
    "phase",
    "state_args",
    "required_caller_inputs",
    "legal_alternatives",
    "reinspect_after_success",
)
REVIEW_ACTION_STATE_FIELDS = {
    "repair_start": (
        "event", "finding_id", "run_kind", "cycle", "source_lanes",
        "blocking_required_lanes", "approval_recheck_lanes",
    ),
    "reverification": (
        "event", "finding_id", "run_kind", "cycle", "source_lanes",
        "blocking_required_lanes", "approval_recheck_lanes",
    ),
    "approval": ("event", "signoff_key", "approval_phase"),
}
REVIEW_ACTION_CALLER_INPUTS = {
    "repair_start": ("context_id", "judgment", "evidence", "integrity_checks"),
    "reverification": (
        "context_id", "judgment", "evidence", "integrity_checks",
        "fresh_context", "independent",
    ),
    "approval": (
        "context_id", "evidence", "integrity_checks", "fresh_context", "independent",
    ),
}
REVIEW_ACTION_TRUNCATED_DIAGNOSTIC = "review_actions_truncated"


def _review_action_state_args(
    action_kind: str, values: Mapping[str, Any]
) -> dict[str, Any]:
    """Return one action's state arguments in canonical registry order."""

    fields = REVIEW_ACTION_STATE_FIELDS[action_kind]
    missing = [field for field in fields if field not in values]
    extra = [field for field in values if field not in fields]
    if missing or extra:
        raise ValueError(
            f"{action_kind} state args do not match REVIEW_ACTION_STATE_FIELDS "
            f"(missing={missing}, extra={extra})"
        )
    return {field: values[field] for field in fields}


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


_ID_SHAPED_WAVE_DIR_RE = re.compile(r"^[0-9a-z]{5,6}[- ].+")


def is_id_shaped_wave_dir_name(name: str) -> bool:
    """Return whether a wave-folder NAME follows the minted-id spelling.

    MESSAGE HINT ONLY.  This is deliberately not a role test: nothing about
    authority, exclusion, or lint scope may be derived from it.  Its single
    job is letting the orphan-ledger failure text add "the folder name is not
    id-shaped, so this may also be a renamed wave directory" when that is
    worth telling the operator.

    It exists as a separate symbol precisely so the name shape cannot be
    re-borrowed as a role predicate.  That conflation is what let a directory
    rename evade the orphan guard, and then kept a renamed wave's raw ledger
    index-eligible until ``is_canonical_wave_events_path`` below became
    content-driven.
    """
    return _ID_SHAPED_WAVE_DIR_RE.match(name) is not None


def is_canonical_wave_events_path(rel_path: str, root: Path | None = None) -> bool:
    """Return whether *rel_path* is a canonical per-wave event ledger.

    The exclusion is structural: the fixed sibling
    ``docs/waves/<one wave directory>/events.jsonl`` occupies the machine
    authority role, and that fixed wave-folder role alone decides exclusion.
    No wave.md declaration or retained state is consulted, so a tampered or
    removed declaration never admits a raw ledger into semantic retrieval.  A
    root-level file, a deeper nested file, or any unrelated file with the same
    basename remains eligible for indexing.  Callers pass normalized
    repo-relative paths in production; accepting backslashes keeps the
    predicate platform-neutral.

    The role is decided by POSITION, not by how the folder is spelled: any
    direct child directory of ``docs/waves/`` holding the fixed sibling
    basename qualifies.  The earlier id-shape clause meant renaming a wave
    directory (underscore separator, non-id prefix, uppercase) admitted that
    wave's raw ledger into semantic retrieval while the wave stayed fully
    live and resolvable, since both lifecycle lookup and the docs-lint
    orphan guard resolve waves by content rather than folder spelling.  The
    surviving name-shape test is ``is_id_shaped_wave_dir_name``, a lint
    message hint that decides nothing.

    Wave 1to78 relocated this predicate here from the indexer so the docs-lint
    orphan-ledger guard and the indexer's retrieval exclusion share ONE
    definition of the fixed wave-folder role (lint must never import the
    indexer, which activates the venv at import time). ``root`` is accepted
    for caller-signature stability and is not consulted.
    """
    normalized = rel_path.replace("\\", "/")
    parts = normalized.split("/")
    return (
        len(parts) == 4
        and parts[0] == "docs"
        and parts[1] == "waves"
        and bool(parts[2])
        and parts[3] == "events.jsonl"
    )


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
        normalized.setdefault("public_path", "wf_review_event")
        normalized.setdefault("command_or_fixture", artifact)
        normalized.setdefault(
            "expected", "the approving actor independently verifies the current affected scope"
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
def project_state_publication_lock(repo_root: Path, *, wait: bool = True):
    """Blocking, re-entrant, cross-process project-global publication lock.

    Serializes every project-state publication: wave lifecycle mutations,
    review event/projection writes, context-efficiency publication, memory
    add/propose/backfill/validate/reconcile, docs gardening, index
    finalization/publication fencing, and upgrade. Public lifecycle handlers
    may hold this lock across a wave.md mutation and the telemetry projection
    that follows it; helpers also acquire it internally, so same-thread
    nesting must not deadlock while other threads and processes remain
    serialized. Lock order with the distinct outer advisory lifecycle lock is
    fixed: ``lifecycle-mutation.lock`` → this lock; never invert it.
    """

    thread_lock_acquired = _WRITE_THREAD_LOCK.acquire(blocking=wait)
    if not thread_lock_acquired:
        raise ProjectPublicationUnavailable(
            "project publication lock is busy in this process"
        )
    try:
        depth = int(getattr(_WRITE_LOCK_STATE, "depth", 0))
        if depth:
            _WRITE_LOCK_STATE.depth = depth + 1
            try:
                yield
            finally:
                _WRITE_LOCK_STATE.depth = depth
            return
        lock = RuntimeFileLock(
            repo_root / PROJECT_STATE_PUBLICATION_LOCK_REL, blocking=False
        )
        try:
            lock.acquire()
        except RuntimeLockBusy as exc:
            if not wait:
                raise ProjectPublicationUnavailable(
                    f"project publication lock is busy: {exc}"
                ) from exc
            # Ordinary publishers preserve their historical serialization.
            # Upgrade is different: it owns the outer lifecycle lock before
            # publication, so probing that lock distinguishes the race window
            # before its durable checkpoint exists and keeps callers fail-fast.
            lifecycle_probe = RuntimeFileLock(
                repo_root / ".wavefoundry/lifecycle-mutation.lock",
                blocking=False,
                offset=1 << 30,
                style="record",
            )
            try:
                lifecycle_probe.acquire()
            except (RuntimeLockBusy, RuntimeLockError) as lifecycle_exc:
                raise ProjectPublicationUnavailable(
                    f"project publication lock is unavailable during lifecycle mutation: {lifecycle_exc}"
                ) from lifecycle_exc
            else:
                lifecycle_probe.release()
            lock = RuntimeFileLock(
                repo_root / PROJECT_STATE_PUBLICATION_LOCK_REL, blocking=True
            )
            try:
                lock.acquire()
            except RuntimeLockError as blocking_exc:
                raise ProjectPublicationUnavailable(
                    f"project publication lock is unavailable: {blocking_exc}"
                ) from blocking_exc
        except RuntimeLockError as exc:
            raise ProjectPublicationUnavailable(
                f"project publication lock is unavailable: {exc}"
            ) from exc
        try:
            _WRITE_LOCK_STATE.depth = 1
            try:
                yield
            finally:
                _WRITE_LOCK_STATE.depth = 0
        finally:
            lock.release()
    finally:
        _WRITE_THREAD_LOCK.release()


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
    return f"Machine review state — {summary['findings']} findings; current: {current}"


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


def approval_record_phase(record: Mapping[str, Any]) -> str:
    """Return phase currency for new and immutable historical approvals."""

    explicit = record.get("approval_phase")
    if explicit in APPROVAL_PHASES:
        return str(explicit)
    return (
        "readiness"
        if record.get("claim_id") == "approval:wave-council-readiness"
        else "delivery"
    )


def _approval_rows(
    records: Iterable[Mapping[str, Any]],
    *,
    approval_phase: str | None = None,
) -> dict[str, tuple[int, Mapping[str, Any]]]:
    return {
        str(record.get("claim_id")): (position, record)
        for position, record in enumerate(records)
        if record.get("record_type") == "executable_evidence"
        and record.get("claim_kind") == "approval"
        and record.get("required_for_approval") is True
        and record.get("phase") == "delivery"
        and record.get("execution_status") == "executed"
        and (
            approval_phase is None
            or approval_record_phase(record) == approval_phase
        )
    }


def _finding_affects_signoff(
    head: Mapping[str, Any],
    signoff_key: str,
    *,
    origin_phase: str | None = None,
) -> bool:
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
    # Delivery-born findings cannot reopen the crossed readiness gate. An
    # unknown phase retains the explicit lane relation for old/synthetic rows;
    # canonical ledgers always provide the executable finding phase.
    if signoff_key == "wave-council-readiness" and origin_phase == "delivery":
        return False
    if signoff_key.startswith("wave-council-"):
        return (
            signoff_key in affected
            or "wave-council" in affected
            or head.get("review_depth") == "full"
        )
    return signoff_key in affected


def _finding_origin_phases(records: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    """Return each finding's phase from its linked root synthesis and run.

    The sealing run is the phase authority. Raw finding evidence is not
    authoritative until a synthesis seals it, and its mutable ``phase`` field
    cannot relabel a delivery finding as readiness-origin.
    """

    rows = tuple(records)
    runs_by_id = {
        str(record.get("review_run_id")): record
        for record in rows
        if record.get("record_type") == "review_run"
        and isinstance(record.get("review_run_id"), str)
    }
    result: dict[str, str] = {}
    for record in rows:
        if record.get("record_type") != "finding_synthesis":
            continue
        if record.get("supersedes_record_id") is not None:
            continue
        finding_id = record.get("finding_id")
        if not isinstance(finding_id, str) or finding_id in result:
            continue
        run = runs_by_id.get(str(record.get("review_run_id")))
        run_kind = run.get("run_kind") if run else None
        if run_kind == "readiness":
            result[finding_id] = "readiness"
        elif run_kind in {
            "initial_delivery",
            # Historical ledgers could introduce a delivery finding directly
            # in a repair/checkpoint run. The current builder requires an
            # existing head, but those closed chains remain delivery-origin.
            "repair_start",
            "reverification",
            "convergence_checkpoint",
        }:
            result[finding_id] = "delivery"
    return result


def finding_origin_phase(
    records: Iterable[Mapping[str, Any]], finding_id: str
) -> str | None:
    """Return the canonical sealed origin phase for one finding."""

    return _finding_origin_phases(records).get(str(finding_id))


def _guided_repair_cycle(records: Iterable[Mapping[str, Any]]) -> int:
    """Return the one wave-global cycle a new repair_start may legally join."""

    rows = tuple(dict(record) for record in records)
    repair_cycles = {
        int(record["cycle"])
        for record in rows
        if record.get("record_type") == "review_run"
        and record.get("run_kind") in {"repair_start", "reverification"}
        and isinstance(record.get("cycle"), int)
        and not isinstance(record.get("cycle"), bool)
        and int(record["cycle"]) >= 1
    }
    if not repair_cycles:
        return 1
    completed, _errors = _repair_cycle_progress(rows)
    highest = max(repair_cycles)
    return highest + 1 if highest in completed else highest


def review_authority_projection(
    records: Iterable[Mapping[str, Any]],
    required_signoff_keys: Iterable[str],
    *,
    approval_phase: str | None = None,
    required_run_kind: str | None = None,
) -> dict[str, Any]:
    """Derive the canonical structured current-state and guided actions.

    This is the single structured projection consumed by the legacy status/list
    presentations and the guided review surface.  It deliberately owns the
    approval-affect relation so callers never parse ``why`` prose or reproduce
    ``_finding_affects_signoff``.
    """

    rows = tuple(dict(record) for record in records)
    if approval_phase is not None and approval_phase not in APPROVAL_PHASES:
        raise ValueError("approval_phase must be readiness or delivery")
    selected_projection_phase = approval_phase or "delivery"
    heads = current_synthesis_heads(rows)
    finding_origin_phases = _finding_origin_phases(rows)
    current_receipt = current_policy_receipt(rows)
    guided_repair_cycle = _guided_repair_cycle(rows)
    positions = {id(record): position for position, record in enumerate(rows)}
    runs_by_id = {
        str(record.get("review_run_id")): record
        for record in rows
        if record.get("record_type") == "review_run"
    }
    evidence_by_id = {
        str(record.get("evidence_record_id")): record
        for record in rows
        if record.get("record_type") == "executable_evidence"
    }
    required_run_present = bool(
        required_run_kind is None
        or any(
            record.get("record_type") == "review_run"
            and record.get("run_kind") == required_run_kind
            for record in rows
        )
    )
    signoff_keys = tuple(
        dict.fromkeys(str(item) for item in required_signoff_keys if str(item))
    )

    finding_facts: list[dict[str, Any]] = []
    for order, (finding_id, head) in enumerate(heads.items()):
        unresolved = tuple(
            str(lane)
            for lane in head.get("blocking_required_lanes", [])
            if str(lane)
        )
        disposition = derive_disposition(head)
        repair_state = head.get("repair_execution_state")
        run = runs_by_id.get(str(head.get("review_run_id")))
        run_kind = str(run.get("run_kind")) if isinstance(run, Mapping) else ""
        head_evidence = evidence_by_id.get(str(head.get("evidence_record_id")))
        verification_context = (
            head_evidence.get("verification_context")
            if isinstance(head_evidence, Mapping)
            else None
        )
        head_actor = (
            str(verification_context.get("actor"))
            if isinstance(verification_context, Mapping)
            and verification_context.get("actor")
            else ""
        )
        origin_phase = finding_origin_phases.get(str(finding_id))
        terminal = bool(
            disposition in {"not_issue", "dont_do_later"}
            or (
                repair_state in {"completed", "operator_waived", "not_required"}
                and not unresolved
            )
        )
        explicit_recheck = head.get("approval_recheck_lanes")
        approval_recheck_lanes = tuple(
            str(lane)
            for lane in (
                explicit_recheck
                if isinstance(explicit_recheck, list)
                else [
                    *head.get("source_lanes", []),
                    *head.get("blocking_required_lanes", []),
                ]
            )
            if str(lane)
        )
        finding_facts.append(
            {
                "finding_id": str(finding_id),
                "first_seen_order": order,
                "head_record_id": str(head.get("record_id") or ""),
                "cycle": head.get("cycle"),
                "run_kind": run_kind,
                "head_actor": head_actor,
                "origin_phase": origin_phase,
                "disposition": disposition,
                "blocking": head.get("blocking") is True,
                "repair_execution_state": repair_state,
                "source_lanes": tuple(
                    str(lane) for lane in head.get("source_lanes", []) if str(lane)
                ),
                "unresolved_required_lanes": unresolved,
                "approval_recheck_lanes": tuple(dict.fromkeys(approval_recheck_lanes)),
                "affected_signoff_keys": tuple(
                    key
                    for key in signoff_keys
                    if _finding_affects_signoff(
                        head, key, origin_phase=origin_phase
                    )
                ),
                "terminal": terminal,
            }
        )

    approval_facts: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    for key in signoff_keys:
        selected_phase = approval_phase or (
            "readiness" if key == "wave-council-readiness" else "delivery"
        )
        approvals = _approval_rows(rows, approval_phase=selected_phase)
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
            and (
                approval_record_phase(approval_record) != "readiness"
                or "approval_phase" not in approval_record
                or (
                    current_receipt is not None
                    and approval_record.get("policy_receipt_id")
                    == current_receipt.get("receipt_id")
                )
            )
        )
        blocking: list[dict[str, Any]] = []
        for fact in finding_facts:
            if fact["blocking"] is not True:
                continue
            if key not in fact["affected_signoff_keys"]:
                continue
            head = heads[fact["finding_id"]]
            head_position = positions.get(id(head), -1)
            unresolved_head = not fact["terminal"]
            # An approval cannot paper over a still-open current head merely
            # by appearing later in the ledger. A terminal repair, however,
            # only stales approvals that predate that repair.
            if unresolved_head or approval_position < head_position:
                blocking.append(fact)
        if blocking:
            finding_ids = [fact["finding_id"] for fact in blocking]
            unresolved = sorted(
                {
                    lane
                    for fact in blocking
                    for lane in fact["unresolved_required_lanes"]
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
        status_row = {
            "signoff_key": key,
            "state": state,
            "why": why,
            "next_action": next_action,
        }
        status_rows.append(status_row)
        approval_facts.append(
            {
                "signoff_key": key,
                "approval_phase": selected_phase,
                "expected_actor": expected_actor,
                "approval_recorded": approval_record is not None,
                "approval_current": state == "approved",
                "state": state,
                "blocking_finding_ids": tuple(
                    fact["finding_id"] for fact in blocking
                ),
                "has_unresolved_blocking_findings": any(
                    not fact["terminal"] for fact in blocking
                ),
                "unresolved_required_lanes": tuple(unresolved if blocking else ()),
            }
        )

    actions: list[dict[str, Any]] = []
    continuation = {
        "source": "wf_review_event.create_response.data.review_actions",
        "fallback": "wf_review_wave",
        "fallback_when": "write_failed_or_state_became_stale",
    }
    for fact in finding_facts:
        if fact["origin_phase"] != selected_projection_phase:
            continue
        if fact["terminal"] or fact["blocking"] is not True:
            continue
        common_state = {
            "event": "finding",
            "finding_id": fact["finding_id"],
            "source_lanes": list(fact["source_lanes"]),
            "approval_recheck_lanes": list(fact["approval_recheck_lanes"]),
        }
        if fact["run_kind"] in {"readiness", "initial_delivery"}:
            kind = "repair_start"
            actor = "implementer"
            state_args = _review_action_state_args(kind, {
                **common_state,
                "run_kind": kind,
                "cycle": guided_repair_cycle,
                "blocking_required_lanes": list(fact["unresolved_required_lanes"]),
            })
            actions.append(
                {
                    "action_id": f"{kind}:{fact['finding_id']}",
                    "action_kind": kind,
                    "actor_role": actor,
                    "phase": selected_projection_phase,
                    "state_args": state_args,
                    "required_caller_inputs": list(REVIEW_ACTION_CALLER_INPUTS[kind]),
                    "legal_alternatives": [],
                    "reinspect_after_success": dict(continuation),
                }
            )
        elif fact["run_kind"] in {"repair_start", "reverification"}:
            # Historical and direct callers may have authored an actionable
            # zero-lane head. Preserve that accepted ledger shape, but give it
            # a real terminal route: one originating reviewer independently
            # reverifies the repair without pretending a lane was cleared.
            actors = fact["unresolved_required_lanes"]
            if not actors:
                actors = tuple(
                    lane
                    for lane in fact["source_lanes"]
                    if lane not in {fact["head_actor"], "implementer"}
                )
            if not actors:
                actors = tuple(
                    key
                    for key in signoff_keys
                    if key not in {
                        fact["head_actor"], "implementer", "operator-signoff"
                    }
                    and not key.startswith("wave-council-")
                )
            if not actors:
                # Compatibility route for previously accepted malformed
                # zero-lane history whose only source was the implementer.
                # The validator still enforces distinct fresh context; this
                # merely names a real reviewer role that can satisfy it.
                actors = (
                    "qa-reviewer"
                    if fact["head_actor"] == "code-reviewer"
                    else "code-reviewer"
                ,)
            for actor in actors:
                kind = "reverification"
                state_args = _review_action_state_args(kind, {
                    **common_state,
                    "run_kind": kind,
                    "cycle": fact["cycle"],
                    "blocking_required_lanes": [
                        lane
                        for lane in fact["unresolved_required_lanes"]
                        if lane != actor
                    ],
                })
                actions.append(
                    {
                        "action_id": f"{kind}:{fact['finding_id']}:{actor}",
                        "action_kind": kind,
                        "actor_role": actor,
                        "phase": selected_projection_phase,
                        "state_args": state_args,
                        "required_caller_inputs": list(REVIEW_ACTION_CALLER_INPUTS[kind]),
                        "legal_alternatives": [],
                        "reinspect_after_success": dict(continuation),
                    }
                )

    for fact in approval_facts:
        if fact["approval_phase"] != selected_projection_phase:
            continue
        if (
            not required_run_present
            or fact["approval_current"]
            or fact["has_unresolved_blocking_findings"]
        ):
            continue
        kind = "approval"
        caller_inputs = list(REVIEW_ACTION_CALLER_INPUTS[kind])
        if fact["expected_actor"] == "operator":
            caller_inputs = [
                name for name in caller_inputs
                if name not in {"fresh_context", "independent"}
            ]
        actions.append(
            {
                "action_id": f"{kind}:{fact['signoff_key']}",
                "action_kind": kind,
                "actor_role": fact["expected_actor"],
                "phase": selected_projection_phase,
                "state_args": _review_action_state_args(kind, {
                    "event": kind,
                    "signoff_key": fact["signoff_key"],
                    "approval_phase": selected_projection_phase,
                }),
                "required_caller_inputs": caller_inputs,
                "legal_alternatives": [],
                "reinspect_after_success": dict(continuation),
            }
        )

    total = len(actions)
    visible = actions[:REVIEW_ACTION_CAP]
    for action in visible:
        if action["action_kind"] == "reverification":
            action["legal_alternatives"] = [
                candidate["action_id"]
                for candidate in visible
                if candidate["action_kind"] == "reverification"
                and candidate["state_args"].get("finding_id")
                == action["state_args"].get("finding_id")
                and candidate["action_id"] != action["action_id"]
            ]
        elif action["action_kind"] == "approval":
            action["legal_alternatives"] = [
                candidate["action_id"]
                for candidate in visible
                if candidate["action_kind"] == "approval"
                and candidate["action_id"] != action["action_id"]
            ]
    return {
        "phase": selected_projection_phase,
        "finding_facts": tuple(finding_facts),
        "approval_facts": tuple(approval_facts),
        "status_rows": tuple(status_rows),
        "next_actions": tuple(visible),
        "recommended_next_action": visible[0] if visible else None,
        "total_current_actions": total,
        "returned_current_actions": len(visible),
        "omitted_current_actions": total - len(visible),
        "truncated": total > REVIEW_ACTION_CAP,
        "action_cap": REVIEW_ACTION_CAP,
        "required_run_kind": required_run_kind,
        "required_run_present": required_run_present,
    }


def review_status_rows(
    records: Iterable[Mapping[str, Any]],
    required_signoff_keys: Iterable[str],
    *,
    approval_phase: str | None = None,
) -> tuple[dict[str, Any], ...]:
    """Preserve the historical presentation over the structured authority."""

    projection = review_authority_projection(
        records, required_signoff_keys, approval_phase=approval_phase
    )
    return tuple(projection["status_rows"])


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
    *,
    config_override: Mapping[str, Any] | None = None,
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
                and value.strip().strip("`").strip().lower() not in {"none", "—", "-"}
            )
            continue
        if not line.startswith("|") or line.startswith("|------"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[0].lower() != "role" and "review" in cells[1].lower():
            lanes.append(cells[0])

    config: dict[str, Any] = dict(config_override or {})
    if config_override is None:
        try:
            loaded = json.loads((root / "docs" / "workflow-config.json").read_text("utf-8"))
            if isinstance(loaded, dict):
                config = loaded
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
    project_lanes = config.get("required_review_lanes", [])
    if isinstance(project_lanes, list):
        lanes.extend(str(value).strip() for value in project_lanes if str(value).strip())

    council_keys: list[str] = []
    council = config.get("wave_review")
    normalized_policy, policy_errors = normalize_wave_review_policy(council)
    if policy_errors:
        # A malformed policy cannot weaken the rendered gate.  Lint reports
        # the configuration error separately; projection retains both keys.
        council_keys.extend(
            ["wave-council-readiness", "wave-council-delivery"]
        )
    elif normalized_policy is not None and normalized_policy["enabled"]:
        phases = council.get("phases", {})
        prepare_key = "wave-council-readiness"
        review_key = "wave-council-delivery"
        if isinstance(phases, dict):
            for phase, default_key in (
                ("prepare", prepare_key),
                ("review", review_key),
            ):
                value = phases.get(phase, {})
                if isinstance(value, dict):
                    key = str(value.get("signoff_key") or default_key).strip()
                    if phase == "prepare":
                        prepare_key = key
                    else:
                        review_key = key
        council_keys.append(prepare_key)
        mode = normalized_policy["delivery_mode"]
        receipt = current_policy_receipt(records)
        targeted_required = bool(
            receipt is None or receipt.get("delivery_council_required") is True
        )
        if mode == "universal" or (mode == "targeted" and targeted_required):
            council_keys.append(review_key)

    return review_status_signoff_keys(
        records,
        (*council_keys, *lanes, "operator-signoff"),
    )


# ---------------------------------------------------------------------------
# Single authority-resolution facade for lifecycle gate reads (wave 1to78).
#
# Every lifecycle gate read of review-evidence CONTENT — operator-signoff
# presence, per-lane signoff currency, council-signoff currency, and max
# severity — resolves through ``resolve_review_authority``. On a wave whose
# header carries the exact ``review-evidence-source: events.jsonl``
# declaration (or a malformed attempt at it, which fails closed) the facade
# derives exclusively from typed ``events.jsonl`` records and their
# chronology; prose signoff lines are narrative in both directions: removing
# them changes nothing and adding them satisfies nothing. On legacy
# (undeclared) waves the facade preserves the historical prose parsing
# unchanged, because prose is those waves' only signoff mechanism and their
# records are never rewritten.
#
# Required-lane ROSTER parsing (the ``## Participants`` section plus
# workflow-config) is configuration, not evidence, and deliberately stays at
# the call sites.
# ---------------------------------------------------------------------------

REVIEW_EVIDENCE_PROSE_MARKERS = ("## Review Evidence", "## Review Signoff Evidence")
PREPARE_REVIEW_EVIDENCE_MARKER = "## Prepare Review Evidence"
SIGNOFF_TOKENS = ("sign-off", "signoff", "approved", "passed", "acceptance", "complete")
SIGNOFF_POSITIVE_STATES = ("approved", "passed", "complete")


def combined_review_evidence(wave_text: str) -> str:
    """Return raw text (preserves case) of all Review Evidence / Signoff sections."""
    parts: list[str] = []
    for marker in REVIEW_EVIDENCE_PROSE_MARKERS:
        idx = wave_text.find(marker)
        if idx == -1:
            continue
        start = idx + len(marker)
        nl = wave_text.find("\n", start)
        if nl != -1:
            start = nl + 1
        tail = wave_text[start:]
        m_end = re.search(r"\n(?=## )", tail)
        body = tail[: m_end.start()] if m_end else tail
        parts.append(body)
    return "\n".join(parts)


def prepare_review_evidence(wave_text: str) -> str:
    """Return raw text of the ## Prepare Review Evidence section (prepare-phase signoffs)."""
    marker = PREPARE_REVIEW_EVIDENCE_MARKER
    idx = wave_text.find(marker)
    if idx == -1:
        return ""
    start = idx + len(marker)
    nl = wave_text.find("\n", start)
    if nl != -1:
        start = nl + 1
    tail = wave_text[start:]
    m_end = re.search(r"\n(?=## )", tail)
    return tail[: m_end.start()] if m_end else tail


def _normalize_signoff_line(raw: str) -> str:
    line = raw.strip()
    line = line.lstrip("-*+ ")
    for emphasis in ("**", "__", "`"):
        line = line.replace(emphasis, "")
    return line.strip()


def _signoff_key_matches_lane(key: str, lane_l: str) -> bool:
    """Exact-key matching (release-review round 4 P0): the normalized key must
    BE the lane, or the lane's ``-signoff`` form. Never a prefix match —
    ``qa`` must not match ``qa-reviewer``; ``operator-signoff`` must not
    match ``operator-signoff-notes``."""
    return key == lane_l or key == f"{lane_l}-signoff" or f"{key}-signoff" == lane_l


def lane_has_signoff_in_evidence(evidence_text: str, lane: str, *, authorization: "bool | None" = None) -> bool:
    """True when the lane's signoff is recorded, current, and explicitly positive.

    Release-review round 4 P0 — FAIL-CLOSED structured parsing:

    - A STATE LINE is one whose text (markdown bullets/emphasis stripped)
      begins with the lane's exact key before the first ``:`` (the lane
      itself or its ``-signoff`` form; never a prefix collision).
    - Parenthesized historical keys (``lane(superseded):``) are bookkeeping
      and never contribute — neither to state nor to prose evidence.
    - Among state lines, ONLY THE LAST governs. Its value must BEGIN with an
      explicit canonical positive state (``approved``/``passed``/``complete``).
      Everything else — ``not approved``, ``pending``, ``blocked``,
      ``rejected``, ``denied``, ``failed``, ``withdrawn``, ``revoked``,
      ``rescinded``, placeholders, unknown wording — is unapproved, and a
      positive word appearing ELSEWHERE in the value never authorizes
      ("blocked because previous checks passed" is blocked).
    - AUTHORIZATION lanes (operator and wave-council signoffs — auto-detected
      unless ``authorization`` is passed explicitly) require a state line:
      prose evidence never authorizes lifecycle closure. Reviewer-seat lanes
      keep prose-line compatibility for their per-seat evidence.

    This is the LEGACY prose branch of the review authority facade (wave
    1to78): on declared waves, gate reads never consult it.
    """
    lane_l = lane.strip().lower()
    if not lane_l or not evidence_text.strip():
        return False
    if authorization is None:
        authorization = (
            lane_l in ("operator", "operator-signoff")
            or lane_l.startswith("wave-council")
        )
    # The bounded current-state projection is authoritative for keys it
    # contains.  It deliberately appears before prose/history parsing so an
    # older approval line cannot override a current withheld/pending row.
    for raw in evidence_text.splitlines():
        stripped = raw.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [cell.strip().lower() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == lane_l:
            return cells[1] == "approved"
    state_values: list[str] = []
    any_prose_signoff = False
    for raw in evidence_text.splitlines():
        low = raw.strip().lower()
        if not low or low.startswith("#"):
            continue
        norm = _normalize_signoff_line(low)
        key, sep, value = norm.partition(":")
        if sep:
            key_clean = key.strip()
            # Historical parenthesized variant — the parenthesis abuts the
            # lane key directly ("lane(superseded):"). A SPACED parenthesis
            # ("red-team (delivery):") is a seat descriptor, not bookkeeping.
            paren = key_clean.find("(")
            if paren > 0 and key_clean[paren - 1] != " " and _signoff_key_matches_lane(
                key_clean[:paren].strip(), lane_l
            ):
                continue  # historical variant: never counts
            if _signoff_key_matches_lane(key_clean, lane_l):
                state_values.append(value.strip())
                continue
        # Prose evidence (reviewer seats only): the lane must appear as a
        # WHOLE word — "qa" never matches inside "qa-reviewer" — and
        # placeholders never count.
        if ("<" not in low
                and re.search(rf"(?<![a-z0-9-]){re.escape(lane_l)}(?![a-z0-9-])", low)
                and any(tok in low for tok in SIGNOFF_TOKENS)):
            any_prose_signoff = True
    if state_values:
        current = state_values[-1]
        if not current or current.startswith("<"):
            return False
        first_word = re.match(r"[a-z][a-z-]*", current)
        return bool(first_word and first_word.group(0) in SIGNOFF_POSITIVE_STATES)
    if authorization:
        return False  # fail closed: no state line = not authorized
    return any_prose_signoff


def review_evidence_has_any_signoff_line(wave_text: str) -> bool:
    """When there are no participant review lanes, still require some recorded signoff in evidence."""
    evidence = combined_review_evidence(wave_text)
    if not evidence.strip():
        return False
    el = evidence.lower()
    for raw in el.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "<" in line:
            continue
        if any(tok in line for tok in SIGNOFF_TOKENS):
            return True
    return False


SEVERITY_ORDER = ["none", "low", "medium", "high", "critical"]
# Wave 1p45s: match severity levels as whole words, not substrings. A bare ``sev in line``
# test fires on ordinary prose ("highest-salience" -> high, "below"/"allow"/"flow" -> low,
# "criticality" -> critical), producing phantom close-time findings. ``\b`` word boundaries
# match genuine standalone severity words while ignoring severity strings embedded inside
# larger words. ("none" is the rank-0 default and is intentionally not matched.)
_SEVERITY_WORD_RE = re.compile(r"\b(" + "|".join(s for s in SEVERITY_ORDER if s != "none") + r")\b")


def prose_max_severity(wave_text: str) -> str:
    """Scan Review Evidence signoff lines for severity annotations; return the highest found.

    Severity words are matched as whole tokens (wave 1p45s) so substrings inside larger
    words (e.g. "high" in "highest") do not register. Position-independent: a standalone
    severity word ranks the same wherever it appears in the line.

    LEGACY prose branch only (wave 1to78): declared waves derive max severity
    from typed finding heads, so a standalone severity word in prose trips
    nothing there.
    """
    evidence = combined_review_evidence(wave_text)
    max_rank = 0
    for raw in evidence.splitlines():
        line = raw.strip().lower()
        if not line or line.startswith("#") or "<" in line:
            continue
        for word in _SEVERITY_WORD_RE.findall(line):
            rank = SEVERITY_ORDER.index(word)
            if rank > max_rank:
                max_rank = rank
    return SEVERITY_ORDER[max_rank]


# Typed severity projection: the ledger schema has no severity words; the two
# graded impact facts on a current finding head are the honest source. A
# ``material`` impact is the "prioritise operator review" tier (high) and
# ``critical`` maps to critical; ``low`` stays low. ``none``/``unverified``
# contribute nothing — an unverified impact must not synthesize a phantom
# finding tier. Superseded heads never contribute (only current heads are
# read), matching the causal current-state model of ``review_status_rows``.
_TYPED_SEVERITY_BY_IMPACT = {"low": "low", "material": "high", "critical": "critical"}


def _typed_max_severity(records: Iterable[Mapping[str, Any]]) -> str:
    max_rank = 0
    for head in current_synthesis_heads(tuple(records)).values():
        if head.get("validation_status") == "invalid":
            continue
        if head.get("disposition") == "not_issue":
            continue
        for field in ("authority_delta", "observable_impact"):
            severity = _TYPED_SEVERITY_BY_IMPACT.get(str(head.get(field)))
            if severity is not None:
                max_rank = max(max_rank, SEVERITY_ORDER.index(severity))
    return SEVERITY_ORDER[max_rank]


@dataclass(frozen=True)
class ReviewAuthority:
    """Resolved review-evidence authority for one wave (wave 1to78).

    ``typed`` selects the branch every read dispatches on:

    - typed (declared wave): reads derive from validated ``events.jsonl``
      records via the same chronology rules the approval-evidence gate uses
      (``review_status_rows``: executed delivery approvals, exact actor
      binding, freshness/independence for non-operator keys, staleness
      against affected repairs). An unreadable or invalid ledger yields zero
      records, so every read fails closed.
    - prose (legacy wave): reads preserve the historical prose parsing
      unchanged.
    """

    typed: bool
    wave_text: str
    records: tuple[Mapping[str, Any], ...] = ()
    ledger_errors: tuple[str, ...] = ()

    def _typed_state(self, key: str, approval_phase: str) -> str:
        rows = review_status_rows(
            self.records, (key,), approval_phase=approval_phase
        )
        return rows[0]["state"] if rows else "pending"

    def signoff_current(
        self,
        key: str,
        *,
        section: str = "review",
        approval_phase: str | None = None,
    ) -> bool:
        """Current positive signoff/approval state for one canonical key.

        ``section`` names the prose section the LEGACY branch reads and is the
        compatibility default for typed phase selection (prepare=readiness,
        review=delivery). Typed lifecycle callers should pass
        ``approval_phase`` explicitly.
        (``"review"`` = combined Review Evidence, ``"prepare"`` = Prepare
        Review Evidence).
        """
        if self.typed:
            selected_phase = approval_phase or (
                "readiness" if section == "prepare" else "delivery"
            )
            return self._typed_state(key, selected_phase) == "approved"
        if section == "prepare":
            evidence = prepare_review_evidence(self.wave_text)
        else:
            evidence = combined_review_evidence(self.wave_text)
        return lane_has_signoff_in_evidence(evidence, key)

    def signoff_recorded(
        self,
        key: str,
        *,
        section: str = "review",
        approval_phase: str | None = None,
    ) -> bool:
        """Whether an approval/signoff exists, regardless of current currency.

        The typed branch deliberately distinguishes an absent approval from a
        recorded approval made stale by later affected work. Legacy prose has
        no chronology model, so its historical signoff predicate is both
        presence and currency.
        """
        if self.typed:
            selected_phase = approval_phase or (
                "readiness" if section == "prepare" else "delivery"
            )
            return f"approval:{key}" in _approval_rows(
                self.records, approval_phase=selected_phase
            )
        return self.signoff_current(
            key, section=section, approval_phase=approval_phase
        )

    def operator_signoff_present(self) -> bool:
        """True if the operator's closure approval is currently recorded."""
        return self.signoff_current(
            "operator-signoff", approval_phase="delivery"
        )

    def evidence_present(self) -> bool:
        """Whether any review evidence exists at all (typed: any validated records)."""
        if self.typed:
            return bool(self.records)
        return bool(combined_review_evidence(self.wave_text).strip())

    def any_signoff_evidence(self) -> bool:
        """No-roster fallback: is at least one signoff recorded anywhere?

        Typed branch: at least one executed delivery approval claim exists
        (approved or not — presence mirrors the prose "some signoff line"
        check, which never validated positivity either).
        """
        if self.typed:
            return bool(_approval_rows(self.records, approval_phase="delivery"))
        return review_evidence_has_any_signoff_line(self.wave_text)

    def max_severity(self) -> str:
        """Highest current finding severity: typed heads or legacy prose scan."""
        if self.typed:
            return _typed_max_severity(self.records)
        return prose_max_severity(self.wave_text)


def resolve_review_authority(
    root: Path | None,
    wave_path: Path | None,
    *,
    wave_text: str | None = None,
) -> ReviewAuthority:
    """Resolve the single review-evidence authority for one wave identity.

    Args:
        root: Repository root the wave belongs to. Part of the wave identity
            contract; derivation itself is wave-local (the ledger is the
            fixed sibling of ``wave.md``) and roster/config parsing stays at
            the call sites.
        wave_path: The wave directory or its ``wave.md`` path. ``None`` is
            tolerated only for text-only legacy probes; a declared wave
            without a path fails closed (no records).
        wave_text: Optional already-read ``wave.md`` text; when omitted it is
            read from ``wave_path``.
    """

    del root  # identity anchor only; derivation is wave-local (see docstring)
    wave_md: Path | None = None
    if wave_path is not None:
        wave_md = Path(wave_path)
        if wave_md.name != "wave.md":
            wave_md = wave_md / "wave.md"
    if wave_text is None:
        wave_text = ""
        if wave_md is not None:
            try:
                wave_text = wave_md.read_text(encoding="utf-8")
            except OSError:
                wave_text = ""
    source, source_errors = parse_review_evidence_source(wave_text)
    typed = source is not None or bool(source_errors)
    if not typed:
        return ReviewAuthority(typed=False, wave_text=wave_text)
    records: tuple[Mapping[str, Any], ...] = ()
    errors: tuple[str, ...] = tuple(source_errors)
    if wave_md is not None:
        result = validate_external_review_evidence(wave_md)
        errors = (*errors, *result.errors)
        if not result.errors:
            records = result.records
    return ReviewAuthority(
        typed=True, wave_text=wave_text, records=records, ledger_errors=errors
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


def empty_external_finding_synthesis_section() -> str:
    """Canonical generated projection for a newly-created external ledger wave."""

    return (
        "## Finding Synthesis\n\n"
        f"{FINDING_SYNTHESIS_MARKER_BEGIN}\n"
        f"{review_evidence_human_table(())}\n\n"
        f"{review_evidence_plain_summary(review_evidence_summary_line(()))}\n"
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
        f"{review_evidence_plain_summary(review_evidence_summary_line(rows))}\n"
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


# Wave 1tmb2: chain-aware repair/reverification independence.  These names are
# both the leading token of the validator error string and the public
# diagnostic code emitted by the append boundary.
REVERIFICATION_CONTEXT_NOT_FRESH = "reverification_context_not_fresh"
REVERIFICATION_ACTOR_NOT_DISTINCT = "reverification_actor_not_distinct"
REVERIFICATION_ANCHOR_UNRESOLVED = "reverification_anchor_unresolved"
REVIEW_EVIDENCE_INDEPENDENCE_INVALID = "review_evidence_independence_invalid"
INDEPENDENCE_DIAGNOSTIC_CODES = frozenset(
    {
        REVERIFICATION_CONTEXT_NOT_FRESH,
        REVERIFICATION_ACTOR_NOT_DISTINCT,
        REVERIFICATION_ANCHOR_UNRESOLVED,
    }
)


def _resolving_repair_start_context(
    records: Iterable[Mapping[str, Any]],
    finding_id: str,
    cycle: int,
) -> Mapping[str, Any] | None:
    """Return the verification context of the repair_start a reverification resolves.

    Matching is by exact ``finding_id`` and ``cycle`` — another finding or an
    earlier cycle sharing a context never controls the current chain.  The
    latest matching repair_start in append order wins.  The context lives on
    the synthesis row's executable evidence, which covers both the compact
    single-finding path and batch repair_start runs.
    """

    rows = [record for record in records]
    repair_run_ids = {
        str(record.get("review_run_id"))
        for record in rows
        if record.get("record_type") == "review_run"
        and record.get("run_kind") == "repair_start"
        and record.get("cycle") == cycle
    }
    evidence_by_id = {
        str(record.get("evidence_record_id")): record
        for record in rows
        if record.get("record_type") == "executable_evidence"
    }
    context: Mapping[str, Any] | None = None
    for record in rows:
        if (
            record.get("record_type") != "finding_synthesis"
            or record.get("finding_id") != finding_id
            or record.get("cycle") != cycle
            or str(record.get("review_run_id")) not in repair_run_ids
        ):
            continue
        evidence = evidence_by_id.get(str(record.get("evidence_record_id")))
        if isinstance(evidence, Mapping):
            candidate = evidence.get("verification_context")
            if isinstance(candidate, Mapping):
                context = candidate
    return context


def _reverification_independence_defect(
    records: Iterable[Mapping[str, Any]],
    finding_id: str,
    cycle: int,
    actor: Any,
    context_id: Any,
    fresh_context: Any,
) -> str | None:
    """Classify a reverification against the repair_start it resolves.

    Three decidable-from-the-ledger policies, in fixed precedence order:

    1. The exact ``(finding_id, cycle)`` repair-start anchor must resolve. An
       absent or cycle-mismatched anchor is invalid rather than silently clean.
    2. Same context declaring ``fresh_context=true`` is self-contradictory —
       two records sharing a ``context_id`` are by definition the same
       context.  This carries no trust assumption.
    3. Same actor is rejected as forward protocol policy, regardless of the
       context declaration.  Actor equality is NOT proof of shared caller
       identity (the validator sees strings, not callers); the policy exists
       because the repairer-reverifies-itself shape is the observed accidental
       failure.

    When both fire, only the decidable contradiction is returned; actor
    policy is evaluated whenever the higher-precedence fresh-context
    contradiction did not fire (1to7k finding
    same-actor-same-context-nonfresh-reverification-accepted: the
    same-context/non-fresh path must not bypass the actor policy).  A
    DISTINCT-actor same-context reverification that honestly declares
    ``fresh_context=false`` passes here but can never clear a lane or
    terminalize a chain — those paths already require a fresh independent
    declaration.

    Returns the diagnostic code, or ``None`` when the chain is clean.
    """

    start_context = _resolving_repair_start_context(records, finding_id, cycle)
    if start_context is None:
        return REVERIFICATION_ANCHOR_UNRESOLVED
    if start_context.get("context_id") == context_id and fresh_context is True:
        return REVERIFICATION_CONTEXT_NOT_FRESH
    if start_context.get("actor") == actor:
        return REVERIFICATION_ACTOR_NOT_DISTINCT
    return None


def _independence_defect_description(
    code: str, finding_id: str, cycle: int, actor: Any, context_id: Any
) -> str:
    if code == REVERIFICATION_ANCHOR_UNRESOLVED:
        return (
            f"reverification for `{finding_id}` cycle {cycle} has no resolvable "
            "repair_start anchor for the exact (finding_id, cycle) chain; "
            "record the canonical repair_start before reverification"
        )
    if code == REVERIFICATION_CONTEXT_NOT_FRESH:
        return (
            f"reverification for `{finding_id}` cycle {cycle} shares its "
            f"repair_start context `{context_id}` while declaring "
            "fresh_context=true; a context cannot be fresh with respect to "
            "work it performed itself"
        )
    return (
        f"reverification for `{finding_id}` cycle {cycle} carries the same "
        f"actor `{actor}` as the repair_start it resolves; this is protocol "
        "policy — actor equality is not proof of shared caller identity, and "
        "independence remains a declaration — but the repairing role must "
        "not be the reverifying role"
    )


def repair_independence_violations(
    records: Iterable[Mapping[str, Any]],
) -> tuple[str, ...]:
    """Audit each finding's current/latest repair chain for independence.

    Close-gate companion to the append-time rejection: ledgers appended by
    older code may already contain chains whose reverification shares its
    repair_start's actor or context.  Only the LATEST chain per finding is
    audited — a new legal repair cycle (``repair_start`` at the next cycle
    followed by a distinct-role/context reverification) supersedes an invalid
    terminal chain and clears the audit.  Callers decide when to run this;
    generic validation never does, so sealed/closed archives stay passing.
    """

    rows = [dict(record) for record in records]
    runs_by_id = {
        str(record.get("review_run_id")): record
        for record in rows
        if record.get("record_type") == "review_run"
    }
    evidence_by_id = {
        str(record.get("evidence_record_id")): record
        for record in rows
        if record.get("record_type") == "executable_evidence"
    }
    latest_reverification: dict[str, dict[str, Any]] = {}
    for record in rows:
        if record.get("record_type") != "finding_synthesis":
            continue
        finding_id = record.get("finding_id")
        if not isinstance(finding_id, str):
            continue
        run = runs_by_id.get(str(record.get("review_run_id")))
        if not isinstance(run, Mapping) or run.get("run_kind") != "reverification":
            continue
        latest_reverification[finding_id] = record
    violations: list[str] = []
    for finding_id in sorted(latest_reverification):
        row = latest_reverification[finding_id]
        cycle = row.get("cycle")
        if not isinstance(cycle, int) or isinstance(cycle, bool):
            continue
        evidence = evidence_by_id.get(str(row.get("evidence_record_id")))
        context = (
            evidence.get("verification_context")
            if isinstance(evidence, Mapping)
            else None
        )
        if not isinstance(context, Mapping):
            continue
        code = _reverification_independence_defect(
            rows,
            finding_id,
            cycle,
            context.get("actor"),
            context.get("context_id"),
            context.get("fresh_context"),
        )
        if code is None:
            continue
        description = _independence_defect_description(
            code, finding_id, cycle, context.get("actor"), context.get("context_id")
        )
        violations.append(
            f"current chain for `{finding_id}` fails the repair/"
            f"reverification independence audit: {description}. Recovery: "
            f"record repair_start at cycle {cycle + 1}, then a distinct-role "
            "and distinct-context reverification; that new legal chain "
            "supersedes this one and makes the close audit eligible to clear."
        )
    return tuple(violations)


def build_compact_review_event(
    records: Iterable[Mapping[str, Any]],
    event: Mapping[str, Any],
) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    """Expand a compact semantic event into canonical append-only protocol rows."""

    prior = tuple(dict(record) for record in records)
    errors: list[str] = []
    event_type = event.get("event")
    if event_type not in REVIEW_WRITE_EVENT_TYPES:
        return (), ("event must be one of: approval, finding, run",)
    actor = event.get("actor")
    context_id = event.get("context_id")
    if not _nonempty_string(actor) or not _nonempty_string(context_id):
        errors.append("actor and context_id must be non-empty strings")

    if event_type == "run":
        run_kind = event.get("run_kind")
        cycle = event.get("cycle")
        if run_kind not in {"readiness", "initial_delivery"} or cycle != 0:
            # Self-correcting (wave 1tis9): the natural guess for a "run kind"
            # is event="run", but repair_start/reverification carry evidence
            # and a judgment, so they are recorded as FINDING events. Name the
            # corrective call instead of only restating the constraint.
            hint = ""
            if run_kind in {"repair_start", "reverification", "convergence_checkpoint"}:
                hint = (
                    f"; `{run_kind}` is recorded as a finding event, not a run "
                    f'event — call event="finding" with run_kind="{run_kind}" '
                    "(plus finding_id, judgment and evidence)"
                )
            errors.append(
                "empty lightweight run requires run_kind "
                f"readiness/initial_delivery and cycle 0{hint}"
            )
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
        approval_phase = event.get("approval_phase")
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
        if approval_phase not in APPROVAL_PHASES:
            errors.append("approval event requires approval_phase readiness or delivery")
        elif signoff_key == "wave-council-readiness" and approval_phase != "readiness":
            errors.append("wave-council-readiness approval requires approval_phase=readiness")
        elif signoff_key in {"wave-council-delivery", "operator-signoff"} and approval_phase != "delivery":
            errors.append(f"{signoff_key} approval requires approval_phase=delivery")
        if approval_phase == "readiness" and not _nonempty_string(
            event.get("policy_receipt_id")
        ):
            errors.append("readiness approval requires server-derived policy_receipt_id")
        integrity_checks, integrity_errors = _validated_integrity_checks(
            event.get("integrity_checks"), executed=True, label="approval event"
        )
        errors.extend(integrity_errors)
        for field in REVIEW_APPROVAL_REQUIRED_EVIDENCE_FIELDS:
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
                "approval_phase": approval_phase,
                **(
                    {"policy_receipt_id": event["policy_receipt_id"]}
                    if approval_phase == "readiness"
                    else {}
                ),
                "proposition": str(event.get("proposition") or f"{signoff_key} approves the current affected scope"),
                "counterexample_or_failure_condition": str(event.get("failure_condition") or "the approval predates an affected repair or is not independently grounded"),
                "execution_status": "executed",
                "public_path": str(event.get("public_path") or "wf_review_event"),
                "command_or_fixture": str(event.get("command_or_fixture") or event["artifact_or_test_id"]),
                "expected": str(event.get("expected") or "the approving actor independently verifies the current affected scope"),
                "observed": observed,
                "artifact_or_test_id": str(event["artifact_or_test_id"]),
                "adjacent_controls": list(event.get("adjacent_controls") or []),
                **{
                    field: integrity_checks[field]
                    for field in INTEGRITY_CHECK_BOOLEAN_FIELDS
                },
                "known_bad_detection_method": integrity_checks[INTEGRITY_CHECK_METHOD_FIELD],
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
    missing_core = sorted(
        set(REVIEW_FINDING_CORE_JUDGMENT_FIELDS) - judgment.keys()
    )
    if missing_core:
        errors.append("finding judgment missing load-bearing fields: " + ", ".join(missing_core))
    for field in REVIEW_FINDING_REQUIRED_EVIDENCE_FIELDS:
        if not _nonempty_string(event.get(field)):
            errors.append(f"finding event requires {field}")
    # Credible-threat gate — the requirement that a material/critical authority delta
    # NAMES the specific capability/asset in `disposition_rationale` is a reviewer-owned
    # SEMANTIC judgment stated in the security seeds (209/213/229), not a validator check.
    # A prose-length heuristic here would be both bypassable (generic filler passes) and
    # over-strict (a valid concise basis like "read API keys" is short), so no machine
    # check is added; `disposition_rationale` remains required non-empty above.
    execution_status = str(event.get("execution_status", "executed"))
    integrity_checks, integrity_errors = _validated_integrity_checks(
        event.get("integrity_checks"),
        executed=execution_status == "executed",
        label="finding event",
    )
    errors.extend(integrity_errors)
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
        missing_optional = sorted(
            set(REVIEW_FINDING_REPAIR_JUDGMENT_FIELDS) - judgment.keys()
        )
        if missing_optional:
            return (), ("non-action-required real finding judgment missing repair/disposition fields: " + ", ".join(missing_optional),)
        provisional.update(
            {field: judgment[field] for field in REVIEW_FINDING_REPAIR_JUDGMENT_FIELDS}
        )
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
    if run_kind == "repair_start" and actor in blocking_lanes:
        return (), (
            "repair_start actor cannot also remain in blocking_required_lanes; "
            "the repair actor cannot independently clear its own reviewer lane. "
            "Derive the current phase-correct repair action through wf_review_wave "
            "before retrying.",
        )
    if run_kind == "reverification":
        prior_blocking_lanes = set(
            _string_items(prior_head.get("blocking_required_lanes", []))
        )
        added_blocking_lanes = set(blocking_lanes) - prior_blocking_lanes
        if added_blocking_lanes:
            return (), (
                "stale reverification cannot add previously cleared "
                "blocking_required_lanes: "
                + ", ".join(sorted(added_blocking_lanes))
                + ". Nothing was appended; derive the current phase-correct "
                "lane action through wf_review_wave before retrying.",
            )
        # Wave 1tmb2: evaluate the exact finding/cycle chain BEFORE building
        # any terminal synthesis.  A rejected attempt appends nothing, so the
        # prior synthesis remains the single current-state authority.
        defect = _reverification_independence_defect(
            prior, str(finding_id), int(cycle), actor, context_id,
            event.get("fresh_context"),
        )
        if defect is not None:
            description = _independence_defect_description(
                defect, str(finding_id), int(cycle), actor, context_id
            )
            return (), (
                f"{defect}: {description}. Nothing was appended; the prior "
                "synthesis remains current. Recovery: submit the "
                "reverification from a distinct acting role and a distinct "
                "context (the implementer records repair_start; the blocking "
                "reviewer lane reverifies). The repair waiver has different "
                "semantics and is not an independence bypass.",
            )
    origin_phase = _finding_origin_phases(prior).get(str(finding_id))
    evidence_phase = (
        "readiness"
        if run_kind == "readiness"
        or (
            run_kind in {"repair_start", "reverification"}
            and origin_phase == "readiness"
        )
        else "delivery"
    )
    evidence_id = _unique_record_id(prior, "ev", str(finding_id))
    run_id = _unique_record_id(prior, "run", f"{run_kind}-{cycle}-{finding_id}")
    synthesis_id = _unique_record_id(prior, "syn", f"{finding_id}-{cycle}")
    evidence: dict[str, Any] = {
        "record_type": "executable_evidence",
        "evidence_record_id": evidence_id,
        "claim_id": finding_id,
        "claim_kind": "finding",
        "required_for_approval": False,
        "phase": evidence_phase,
        "proposition": event["proposition"],
        "counterexample_or_failure_condition": event["failure_condition"],
        "execution_status": execution_status,
        "public_path": event["public_path"],
        "command_or_fixture": event["command_or_fixture"],
        "expected": event["expected"],
        "observed": event["observed"],
        "artifact_or_test_id": event["artifact_or_test_id"],
        "adjacent_controls": list(event.get("adjacent_controls") or []),
        **{
            field: integrity_checks[field]
            for field in INTEGRITY_CHECK_BOOLEAN_FIELDS
        },
        "known_bad_detection_method": integrity_checks[INTEGRITY_CHECK_METHOD_FIELD],
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
                return (), (
                    "clearing a required lane requires the same fresh independent actor. "
                    "Derive the current phase-correct lane action through wf_review_wave "
                    "before retrying.",
                )
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


def _validated_integrity_checks(
    value: object,
    *,
    executed: bool,
    label: str,
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    """Validate the exact caller-owned integrity assertion object.

    Executed approvals and findings must affirm every boolean.  Non-executed
    findings still use the same exact, typed shape, but may honestly carry a
    false check.  The builder copies these values verbatim; it never expands a
    single confirmation into several claims.
    """

    if not isinstance(value, dict):
        return None, (f"{label} requires an exact integrity_checks object",)
    keys = frozenset(value)
    missing = sorted(INTEGRITY_CHECK_FIELDS - keys)
    extra = sorted(keys - INTEGRITY_CHECK_FIELDS)
    errors: list[str] = []
    if missing:
        errors.append(f"{label} integrity_checks missing fields: " + ", ".join(missing))
    if extra:
        errors.append(f"{label} integrity_checks has unsupported fields: " + ", ".join(extra))
    for field in INTEGRITY_CHECK_BOOLEAN_FIELDS:
        field_value = value.get(field)
        if not isinstance(field_value, bool):
            errors.append(f"{label} integrity_checks.{field} must be boolean")
        elif executed and field_value is not True:
            errors.append(
                f"executed {label} requires integrity_checks.{field}=true"
            )
    method = value.get(INTEGRITY_CHECK_METHOD_FIELD)
    if not _nonempty_string(method):
        errors.append(
            f"{label} integrity_checks.{INTEGRITY_CHECK_METHOD_FIELD} "
            "must be a non-empty string"
        )
    return (dict(value) if not errors else None), tuple(errors)


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
    if "approval_phase" in record:
        enum_error = _enum_error(
            record, "approval_phase", APPROVAL_PHASES, label
        )
        if enum_error:
            errors.append(enum_error)
        if record.get("claim_kind") != "approval":
            errors.append(f"{label}: `approval_phase` is valid only for approval evidence")
    if "policy_receipt_id" in record:
        if not _nonempty_string(record.get("policy_receipt_id")):
            errors.append(f"{label}: `policy_receipt_id` must be a non-empty string")
        if record.get("approval_phase") != "readiness":
            errors.append(
                f"{label}: `policy_receipt_id` is valid only for readiness approval evidence"
            )
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
        if record.get("execution_status") != "executed":
            errors.append(f"{label}: lane reassessment evidence must be executed")
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
    origin_kind_by_finding: dict[str, str] = {}
    for run in runs:
        kind = run.get("run_kind")
        for row in by_run.get(str(run.get("review_run_id")), []):
            finding_id = row.get("finding_id")
            if isinstance(finding_id, str) and isinstance(kind, str):
                origin_kind_by_finding.setdefault(finding_id, kind)
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
            requires_initial_delivery = not actionable or any(
                origin_kind_by_finding.get(str(row.get("finding_id"))) != "readiness"
                for row in actionable
            )
            if requires_initial_delivery and (
                not initial_delivery_positions or initial_delivery_positions[0] >= position
            ):
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
                    # Self-correcting (wave 1tis9): name the corrective call.
                    # A repair cycle opens with a repair_start recorded BEFORE
                    # the mutation; the reverification then clears the lane.
                    errors.append(
                        f"reverification cycle {cycle} for `{finding_id}` has no "
                        "preceding repair_start — record one first: "
                        'event="finding", run_kind="repair_start", '
                        f'cycle={cycle}, finding_id="{finding_id}" (the '
                        "implementer records it before repairing; the blocking "
                        "reviewer lane then submits this reverification)"
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
    finding_origin_phases = _finding_origin_phases(records)
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
                    origin_phase = finding_origin_phases.get(finding_id)
                    reassessment_phase = reassessment.get("phase") if reassessment else None
                    # Readiness findings historically completed during delivery review.
                    # Keep those valid while allowing the new same-phase readiness path;
                    # delivery findings must never be cleared by an earlier phase.
                    phase_is_valid = (
                        reassessment_phase in {"readiness", "delivery"}
                        if origin_phase == "readiness"
                        else reassessment_phase == origin_phase
                    )
                    reassessed = bool(
                        reassessment
                        and reassessment.get("claim_kind") == "lane_reassessment"
                        and reassessment.get("claim_id") == finding_id
                        and reassessment.get("execution_status") == "executed"
                        and phase_is_valid
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
                    f"current synthesis `{record_id}` for `{finding_id}` retains unresolved required lanes. "
                    "Derive the current phase-correct lane action through wf_review_wave "
                    "before retrying."
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
        elif record_type == REVIEW_POLICY_RECEIPT_RECORD_TYPE:
            errors.extend(
                f"review_policy_receipt[{index}]: {error}"
                for error in validate_policy_receipt(record)
            )
        else:
            errors.append(f"record[{index}]: unknown record_type {record_type!r}")
    receipts = [
        record
        for record in rows
        if record.get("record_type") == REVIEW_POLICY_RECEIPT_RECORD_TYPE
    ]
    receipt_ids: set[str] = set()
    for position, receipt in enumerate(receipts):
        receipt_id = str(receipt.get("receipt_id") or "")
        if receipt_id in receipt_ids:
            errors.append(f"review_policy_receipt duplicate receipt_id: {receipt_id}")
        if position == 0:
            if "supersedes_receipt_id" in receipt:
                errors.append("genesis review_policy_receipt may not supersede a receipt")
        else:
            parent = str(receipt.get("supersedes_receipt_id") or "")
            expected_parent = str(receipts[position - 1].get("receipt_id") or "")
            if parent != expected_parent:
                errors.append(
                    "review_policy_receipt chain must supersede the immediately "
                    f"previous receipt ({expected_parent})"
                )
        parent_id = (
            GENESIS_RECEIPT_PARENT
            if position == 0
            else str(receipts[position - 1].get("receipt_id") or "")
        )
        try:
            expected_id = derive_receipt_id(
                receipt_semantic_fields(receipt), parent_id
            )
        except (KeyError, TypeError, ValueError):
            expected_id = ""
        if expected_id and receipt_id != expected_id:
            errors.append(
                "review_policy_receipt receipt_id does not match its semantic fields and parent"
            )
        receipt_ids.add(receipt_id)
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
        legacy_marker, legacy_marker_errors = _marker_version(text)
        if legacy_marker is not None or legacy_marker_errors:
            # Retired 1.13-era inline-authority wave: fail closed with the
            # manual migration path. The inline reader was deleted (wave
            # 1to78); this wave never silently reclassifies as legacy prose.
            errors.append(
                "legacy inline review-evidence wave is no longer readable; "
                "migrate manually: move each record line from the fenced "
                "`jsonl` block into a sibling `events.jsonl` ledger (one JSON "
                "object per line, LF-terminated), replace the "
                "`review-evidence-protocol:` header line with "
                f"`{REVIEW_EVIDENCE_SOURCE_DECLARATION}`, and regenerate the "
                "Finding Synthesis projection by replaying the last typed "
                "review event"
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


__all__ = [
    "EVENTS_FILENAME",
    "EVENT_IDENTITY_FIELD",
    "FINDING_SYNTHESIS_MARKER_BEGIN",
    "FINDING_SYNTHESIS_MARKER_END",
    "FULL_COUNCIL_TRIGGERS",
    "PROJECT_STATE_PUBLICATION_LOCK_REL",
    "PROTOCOL_VERSION",
    "ProjectPublicationUnavailable",
    "REQUEST_DIGEST_FIELD",
    "REVIEW_STATUS_MARKER_BEGIN",
    "REVIEW_STATUS_MARKER_END",
    "SEVERITY_ORDER",
    "REVIEW_EVIDENCE_SOURCE",
    "REVIEW_EVIDENCE_SOURCE_DECLARATION",
    "ReviewAuthority",
    "ReviewEvidenceValidation",
    "build_compact_review_event",
    "combined_review_evidence",
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
    "is_canonical_wave_events_path",
    "is_id_shaped_wave_dir_name",
    "lane_has_signoff_in_evidence",
    "normalize_review_event_request",
    "parse_review_event_bytes",
    "parse_review_evidence_source",
    "prepare_review_evidence",
    "project_state_publication_lock",
    "prose_max_severity",
    "read_review_event_ledger",
    "resolve_review_authority",
    "review_evidence_has_any_signoff_line",
    "render_review_evidence_projection",
    "render_review_status_projection",
    "review_event_path",
    "review_event_request_digest",
    "review_evidence_human_table",
    "review_evidence_summary",
    "review_evidence_summary_line",
    "review_status_human_table",
    "required_review_status_keys",
    "review_status_rows",
    "review_status_signoff_keys",
    "validate_external_review_evidence",
    "validate_review_evidence_records",
]
