"""Agent memory records: parsing, writing, reconciliation, kind-aware decay.

Wave 1ro44 (change 1p8gy). Records are repo-visible markdown under
``docs/agents/memory/`` — the docs-lint rules (``check_memory_docs``) are the
schema contract; this module is the runtime reader/writer the ``memory_*``
MCP tools stand on.

Design posture: the record FILES are the source of truth (live filesystem —
few, small, always current); the semantic index is an optional retrieval
assist. Decay affects ranking and briefing inclusion only — status and
supersession are the only lifecycle mechanisms, and nothing here ever deletes
or rewrites history.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Optional

sys.dont_write_bytecode = True

_scripts_dir = str(Path(__file__).resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

MEMORY_DIR = "docs/agents/memory"

# Memory-id grammar (security boundary, delivery-review finding 2026-07-13):
# ids are PATH COMPONENTS (`docs/agents/memory/<id>.md`), and the MCP tools
# accept caller-supplied ids — every filesystem access validates against this
# grammar FIRST, then enforces resolved-path containment as defense in depth.
MEMORY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

MEMORY_KINDS = (
    "failed_attempt",
    "successful_pattern",
    "review_finding",
    "operator_preference",
    "environment_gotcha",
    "fragile_file",
    "decision",
    "dependency_gotcha",
)
MEMORY_STATUSES = ("candidate", "active", "stale", "superseded", "rejected")
# Statuses that may surface as advisories/briefings by default. Candidates are
# included so freshly-proposed lessons are visible before the close-time
# distillation checkpoint promotes or rejects them (they are labeled).
DEFAULT_SURFACED_STATUSES = ("active", "candidate")

# --- Kind-aware decay constants (1p8gy Req 13) ---
# Churn-decayed kinds: confidence multiplier = 1 / (1 + commits_since_created
# / CHURN_DECAY_HALVING_COMMITS). At the halving count the record ranks at
# half strength; it never reaches zero (decay orders, status retires).
CHURN_DECAY_HALVING_COMMITS = 10
CHURN_DECAYED_KINDS = ("failed_attempt", "review_finding", "successful_pattern")
# Time-decayed kinds: same hyperbolic shape in days. 180 days ≈ the ecosystem
# cadence of tool/dependency releases the gotchas describe.
TIME_DECAY_HALVING_DAYS = 180
TIME_DECAYED_KINDS = ("environment_gotcha", "dependency_gotcha")
# Briefing exclusion floor for churn-decayed kinds only (1p8gy AC-13: a
# heavily-churned failed_attempt can drop OUT of briefings). fragile_file is
# exempt by council amendment: churn is ambiguous evidence there, so it sets
# needs_reverification instead and never drops below inclusion.
BRIEFING_CONFIDENCE_FLOOR = 0.2

_ID_RE = re.compile(r"^Memory ID:\s*`([a-z0-9][a-z0-9-]*)`\s*$", re.MULTILINE)
_KIND_RE = re.compile(r"^Kind:\s*`([a-z_]+)`\s*$", re.MULTILINE)
_STATUS_RE = re.compile(r"^Status:\s+(\S+)\s*$", re.MULTILINE)
# Confidence grammar mirrors the lint (`MEMORY_CONFIDENCE_PATTERN`): any
# non-space token, then a `float()` + range check below (delivery-review
# parity finding — the old `[0-9.]+` rejected lint-valid `1e-1`/`+0.5`).
_CONFIDENCE_RE = re.compile(r"^Confidence:\s*(\S+)\s*$", re.MULTILINE)
_CREATED_RE = re.compile(r"^Created:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
_UPDATED_RE = re.compile(r"^Updated:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
_SUPERSEDES_RE = re.compile(r"^Supersedes:\s*`([a-z0-9][a-z0-9-]*)`\s*$", re.MULTILINE)
_SUPERSEDED_BY_RE = re.compile(r"^Superseded by:\s*`([a-z0-9][a-z0-9-]*)`\s*$", re.MULTILINE)
# Optional 1stwk metadata: the measured consumed-token cost of the wave that
# produced an evidence-derived candidate (grounds the 1svuk avoided estimate).
_SOURCE_COST_RE = re.compile(r"^Source exploration cost:\s*(\d+)\s*$", re.MULTILINE)
_SOURCE_EVENT_RE = re.compile(r"^Source event:\s*`([^`\r\n]+)`\s*$", re.MULTILINE)
_VALIDATION_RE = re.compile(
    r"^Validation:\s*(pending|promote|retain|reject|rewrite)\s*$", re.MULTILINE
)
_VALIDATED_BY_RE = re.compile(r"^Validated by:\s*([^\r\n]+)\s*$", re.MULTILINE)
_ACTION_DELTA_RE = re.compile(r"^Action delta:\s*([^\r\n]+)\s*$", re.MULTILINE)
_VALIDATION_RATIONALE_RE = re.compile(
    r"^Validation rationale:\s*([^\r\n]+)\s*$", re.MULTILINE
)
_EVIDENCE_VERIFIED_RE = re.compile(
    r"^Evidence verified:\s*(true|false)\s*$", re.MULTILINE
)
_CURRENT_TARGET_VERIFIED_RE = re.compile(
    r"^Current target verified:\s*(true|false)\s*$", re.MULTILINE
)
_CANONICAL_OVERLAP_RE = re.compile(
    r"^Canonical overlap:\s*(none|supplements|duplicates)\s*$", re.MULTILINE
)
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_BACKTICK_RE = re.compile(r"`([^`]+)`")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    start += len(heading)
    nxt = text.find("\n## ", start)
    return text[start:nxt] if nxt >= 0 else text[start:]


def _section_has_bullet(body: str) -> bool:
    """EXACT mirror of the lint's `_section_has_bullets`
    (`wave_lint_lib/helpers.py`): a line whose first non-whitespace is ``- ``.

    Must match the lint character-for-character (delivery-review parity
    finding): the lint accepts ONLY ``- `` (dash + space), not ``*`` markers
    or a tab after the dash. A looser reader would let a lint-invalid record
    surface as a live advisory.
    """
    return any(line.lstrip().startswith("- ") for line in (body or "").splitlines())


def _date_ts(value: str) -> Optional[int]:
    try:
        return int(time.mktime(time.strptime(value, "%Y-%m-%d")))
    except (ValueError, OverflowError):
        return None


def parse_memory_record(path: Path, text: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Parse one record file → dict, or None when the record is not valid.

    FAIL CLOSED (delivery-review finding 2026-07-13): a record is returned
    only when EVERY required field/section is present and valid — matching
    id (equal to the filename stem), known kind, valid status enum, in-range
    confidence, well-formed created/updated dates, and non-empty
    summary/evidence/targets. A malformed record parses to None and never
    surfaces as an advisory (the tolerant defaulting that let a status-less
    record surface as `candidate` is gone). Never raises — surfacing must not
    crash on a bad file.
    """
    if text is None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    mem_id = _ID_RE.search(text)
    kind = _KIND_RE.search(text)
    if not mem_id or not kind or kind.group(1) not in MEMORY_KINDS:
        return None
    # id must be grammar-valid AND agree with the filename stem — a record
    # whose id disagrees with its path is not trustworthy.
    if not MEMORY_ID_RE.fullmatch(mem_id.group(1)) or mem_id.group(1) != path.stem:
        return None
    status = _STATUS_RE.search(text)
    if not status or status.group(1) not in MEMORY_STATUSES:
        return None
    confidence = _CONFIDENCE_RE.search(text)
    if not confidence:
        return None
    try:
        conf_value = float(confidence.group(1))
    except ValueError:
        return None
    if not 0.0 <= conf_value <= 1.0:
        return None
    created = _CREATED_RE.search(text)
    updated = _UPDATED_RE.search(text)
    if not created or _date_ts(created.group(1)) is None:
        return None
    if not updated or _date_ts(updated.group(1)) is None:
        return None
    # Status-dependent link rule (mirrors check_memory_docs): a superseded
    # record MUST carry `Superseded by:`.
    if status.group(1) == "superseded" and not _SUPERSEDED_BY_RE.search(text):
        return None
    summary = _section(text, "## Summary").strip()
    evidence_body = _section(text, "## Evidence")
    targets_body = _section(text, "## Targets")
    evidence_refs = _BACKTICK_RE.findall(evidence_body)
    target_refs = _BACKTICK_RE.findall(targets_body)
    # Evidence/Targets must have BULLETS carrying backticked refs — matching
    # the lint's `_section_has_bullets` + backtick rule, so a lint-invalid
    # record (backticks but no bullet) is also reader-invalid.
    if not summary or not evidence_refs or not target_refs:
        return None
    if not _section_has_bullet(evidence_body) or not _section_has_bullet(targets_body):
        return None
    title = _TITLE_RE.search(text)
    return {
        "memory_id": mem_id.group(1),
        "path": str(path),
        "title": title.group(1).strip() if title else mem_id.group(1),
        "kind": kind.group(1),
        "status": status.group(1),
        "confidence": conf_value,
        "created_at": created.group(1),
        "updated_at": updated.group(1),
        "supersedes": (m.group(1) if (m := _SUPERSEDES_RE.search(text)) else None),
        "superseded_by": (m.group(1) if (m := _SUPERSEDED_BY_RE.search(text)) else None),
        "source_exploration_cost": (
            int(m.group(1)) if (m := _SOURCE_COST_RE.search(text)) else None
        ),
        "source_event": (
            m.group(1).strip() if (m := _SOURCE_EVENT_RE.search(text)) else None
        ),
        "validation": (
            m.group(1) if (m := _VALIDATION_RE.search(text)) else None
        ),
        "validated_by": (
            m.group(1).strip() if (m := _VALIDATED_BY_RE.search(text)) else None
        ),
        "action_delta": (
            m.group(1).strip() if (m := _ACTION_DELTA_RE.search(text)) else None
        ),
        "validation_rationale": (
            m.group(1).strip()
            if (m := _VALIDATION_RATIONALE_RE.search(text))
            else None
        ),
        "evidence_verified": (
            m.group(1) == "true" if (m := _EVIDENCE_VERIFIED_RE.search(text)) else None
        ),
        "current_target_verified": (
            m.group(1) == "true"
            if (m := _CURRENT_TARGET_VERIFIED_RE.search(text))
            else None
        ),
        "canonical_overlap": (
            m.group(1) if (m := _CANONICAL_OVERLAP_RE.search(text)) else None
        ),
        "summary": summary,
        "evidence_refs": evidence_refs,
        "target_refs": target_refs,
    }


def load_memory_records(
    root: Path, *, statuses: Optional[Iterable[str]] = None
) -> list[dict[str, Any]]:
    """All parseable records, optionally filtered by status.

    ``statuses=None`` returns everything (history included); the surfacing
    default is ``DEFAULT_SURFACED_STATUSES`` — stale/superseded/rejected
    records never appear as advisories unless explicitly requested.
    """
    # Containment BEFORE traversal (delivery-review finding): a symlinked
    # memory dir/ancestor pointing outside the repo yields None here, so
    # external records are never read or surfaced.
    memory_root = canonical_memory_root(root)
    if memory_root is None or not memory_root.is_dir():
        return []
    resolved_root = memory_root.resolve()
    wanted = set(statuses) if statuses is not None else None
    records = []
    for path in sorted(memory_root.rglob("*.md")):
        if path.name == "README.md":
            continue
        # Per-record containment (delivery-review defense-in-depth): a
        # symlinked record file pointing outside the canonical memory root must
        # not be read/surfaced. Skip symlinks and any candidate whose resolved
        # path leaves the memory root — but ACCEPT records in real nested
        # subdirectories (`is_relative_to`, not `parent ==`), so a lint-valid
        # nested record surfaces (lint validates records at any depth; the
        # reader must agree — parity finding).
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(resolved_root):
                continue
        except OSError:
            continue
        record = parse_memory_record(path)
        if record is None:
            continue
        if wanted is not None and record["status"] not in wanted:
            continue
        records.append(record)
    return records


def slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug[:60] or "record"


def validate_memory_id(memory_id: Any) -> str:
    """Validate a memory id against the documented grammar; raise ValueError.

    Ids become path components under the memory root and arrive from the MCP
    surface — anything outside ``[a-z0-9][a-z0-9-]*`` (max 64 chars) is
    refused before any filesystem access. Applies equally to ``supersedes``/
    ``superseded_by`` references.
    """
    candidate = str(memory_id or "").strip()
    if not MEMORY_ID_RE.fullmatch(candidate):
        raise ValueError(
            f"invalid memory id {memory_id!r}: must match [a-z0-9][a-z0-9-]* "
            "(lowercase alphanumerics and dashes, max 64 chars)"
        )
    return candidate


def canonical_memory_root(root: Path) -> Optional[Path]:
    """The memory root IFF it resolves to its canonical in-repo location.

    THE single containment chokepoint (delivery-review finding): every read
    (load/search/advisory/signature) AND write (add/reconcile) path resolves
    the memory root through here BEFORE traversing or mutating it. A symlinked
    ``docs/agents/memory`` — or any symlinked ancestor — that redirects the
    canonical path outside the repo returns None (readers degrade to empty;
    writers raise). ``resolve()`` follows every existing symlink component and
    appends the non-existent tail, so a symlinked ancestor is caught even
    before the ``memory`` child exists. Both sides are resolved, so a
    legitimately symlinked repo root (macOS ``/var``→``/private/var``) is not a
    false reject. The RETURNED path is unresolved so callers' repo-relative
    math against the unresolved ``root`` is unaffected.
    """
    repo = root.resolve()
    expected = repo / MEMORY_DIR
    memory_root = root / MEMORY_DIR
    try:
        if memory_root.resolve() != expected:
            return None
    except OSError:
        return None
    return memory_root


def _contained_record_path(root: Path, memory_id: str) -> Path:
    """Grammar-validated id → record path, with full resolved containment.

    Raises ValueError when the id is invalid OR the memory root is not
    canonically in-repo (symlink escape) OR the resolved record path would sit
    outside the canonical root. NEVER creates directories — the caller does
    ``mkdir`` only after this returns.
    """
    memory_id = validate_memory_id(memory_id)
    memory_root = canonical_memory_root(root)
    if memory_root is None:
        raise ValueError(
            "memory root resolves outside its canonical repository location "
            "(symlinked memory directory or ancestor) — refusing"
        )
    repo = root.resolve()
    expected_root = repo / MEMORY_DIR
    path = memory_root / f"{memory_id}.md"
    resolved = path.resolve()
    if resolved.parent != expected_root or not resolved.is_relative_to(repo):
        raise ValueError(f"memory id {memory_id!r} escapes the memory root")
    return path


def render_memory_record(
    *,
    memory_id: str,
    kind: str,
    summary: str,
    evidence: list[str],
    targets: list[str],
    title: str = "",
    confidence: float = 0.6,
    status: str = "candidate",
    supersedes: str = "",
    source_exploration_cost: Optional[int] = None,
    source_event: str = "",
    validation: str = "",
    validated_by: str = "",
    action_delta: str = "",
    validation_rationale: str = "",
    evidence_verified: Optional[bool] = None,
    current_target_verified: Optional[bool] = None,
    canonical_overlap: str = "",
    date: Optional[str] = None,
) -> str:
    """Render the canonical record markdown (the README template shape).

    ``source_exploration_cost`` (wave 1stwk), when set, records the measured
    consumed-token cost of the wave/repair-cycle that produced this record. It
    is the grounding unit the 1svuk estimated-exploration-avoided category
    reads; it is optional metadata, absent on manually-authored records.
    """
    today = date or time.strftime("%Y-%m-%d")
    lines = [
        f"# {title or memory_id}",
        "",
        "Owner: Engineering",
        f"Status: {status}",
        f"Last verified: {today}",
        "",
        f"Memory ID: `{memory_id}`",
        f"Kind: `{kind}`",
        f"Confidence: {confidence}",
        f"Created: {today}",
        f"Updated: {today}",
    ]
    if source_exploration_cost is not None:
        lines.append(f"Source exploration cost: {int(source_exploration_cost)}")
    if source_event:
        if any(char in source_event for char in ("`", "\r", "\n")):
            raise ValueError("source_event must be a single line without backticks")
        lines.append(f"Source event: `{source_event}`")
        lines.append(f"Validation: {validation or 'pending'}")
    if validated_by:
        lines.append(f"Validated by: {validated_by}")
    if action_delta:
        lines.append(f"Action delta: {action_delta}")
    if validation_rationale:
        lines.append(f"Validation rationale: {validation_rationale}")
    if evidence_verified is not None:
        lines.append(f"Evidence verified: {str(bool(evidence_verified)).lower()}")
    if current_target_verified is not None:
        lines.append(
            f"Current target verified: {str(bool(current_target_verified)).lower()}"
        )
    if canonical_overlap:
        lines.append(f"Canonical overlap: {canonical_overlap}")
    if supersedes:
        lines.append(f"Supersedes: `{supersedes}`")
    lines += ["", "## Summary", "", summary.strip(), "", "## Evidence", ""]
    lines += [f"- {e}" if e.lstrip().startswith("`") else f"- `{e}`" for e in evidence]
    lines += ["", "## Targets", ""]
    lines += [f"- {t}" if t.lstrip().startswith("`") else f"- `{t}`" for t in targets]
    return "\n".join(lines) + "\n"


def write_memory_record(root: Path, content: str, memory_id: str) -> Path:
    """Create a record with EXCLUSIVE creation (delivery-review finding).

    ``open(..., "x")`` is atomic O_EXCL — two concurrent adds that pick the
    same id cannot both succeed, so the TOCTOU window between an ``exists()``
    check and ``write_text`` is closed. A collision raises ``FileExistsError``
    (callers retry generated ids and surface the conflict for explicit ids).
    """
    # Validate containment BEFORE any mkdir (delivery-review finding): a
    # `mkdir(parents=True)` that ran first could materialize an external
    # `memory` directory through a symlinked ancestor even when the write is
    # ultimately refused. `_contained_record_path` proves canonical in-repo
    # containment and raises without touching the filesystem.
    path = _contained_record_path(root, memory_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "x", encoding="utf-8", newline="") as fh:
            fh.write(content)
    except FileExistsError:
        raise FileExistsError(f"memory record already exists: {path}")
    return path


def create_memory_record(
    root: Path, content_for_id, base_id: str, *, explicit: bool
) -> tuple[Path, str]:
    """Write a record, retrying generated-id collisions atomically.

    ``content_for_id`` is a callable ``id -> rendered_markdown`` (the content
    embeds the id, so it is re-rendered per attempt). For an ``explicit`` id a
    collision is a hard ``FileExistsError``; for a generated id the collision
    is resolved by suffixing ``-2``, ``-3``, … and retrying the exclusive
    create — no pre-check, so concurrent creators converge on distinct files.
    Returns ``(path, memory_id)``.
    """
    if explicit:
        memory_id = validate_memory_id(base_id)
        return write_memory_record(root, content_for_id(memory_id), memory_id), memory_id
    base = validate_memory_id(base_id)
    memory_id = base
    n = 2
    while True:
        try:
            return write_memory_record(root, content_for_id(memory_id), memory_id), memory_id
        except FileExistsError:
            memory_id = f"{base[:60]}-{n}"
            n += 1
            if n > 1000:  # pathological; never expected
                raise


_STATUS_LINE_RE = re.compile(r"^(Status:\s+)\S+\s*$", re.MULTILINE)
_UPDATED_LINE_RE = re.compile(r"^(Updated:\s*)\d{4}-\d{2}-\d{2}\s*$", re.MULTILINE)


def _replace_or_insert_metadata(text: str, pattern: re.Pattern[str], line: str) -> str:
    """Replace one frontmatter line or insert it before the first section."""
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    marker = "\n## Summary"
    if marker not in text:
        raise ValueError("memory record has no Summary section")
    return text.replace(marker, f"\n{line}{marker}", 1)


def record_memory_validation(
    root: Path,
    memory_id: str,
    *,
    verdict: str,
    action_delta: str,
    rationale: str,
    evidence_verified: bool,
    current_target_verified: bool,
    canonical_overlap: str,
    validated_by: str = "agent",
    superseded_by: str = "",
    date: Optional[str] = None,
) -> Path:
    """Persist a compact semantic validation judgment on a generated record."""
    if verdict not in ("promote", "retain", "reject", "rewrite"):
        raise ValueError("verdict must be promote, retain, reject, or rewrite")
    if canonical_overlap not in ("none", "supplements", "duplicates"):
        raise ValueError("canonical_overlap must be none, supplements, or duplicates")
    for label, value in (
        ("action_delta", action_delta),
        ("rationale", rationale),
        ("validated_by", validated_by),
    ):
        if not str(value or "").strip() or any(c in str(value) for c in ("\r", "\n")):
            raise ValueError(f"{label} must be a non-empty single line")
    path = _contained_record_path(root, memory_id)
    if not path.is_file():
        raise FileNotFoundError(f"memory record not found: {memory_id}")
    text = path.read_text(encoding="utf-8")
    parsed = parse_memory_record(path, text)
    if parsed is None:
        raise ValueError(f"{memory_id}: malformed memory record")
    if not parsed.get("source_event"):
        raise ValueError(f"{memory_id}: only evidence-derived records can be validated")
    if verdict in ("promote", "retain", "rewrite"):
        if not evidence_verified or not current_target_verified:
            raise ValueError(
                f"{verdict} requires evidence_verified and current_target_verified"
            )
        if canonical_overlap == "duplicates":
            raise ValueError(
                f"{verdict} cannot use canonical_overlap='duplicates'; reject the draft"
            )
    new_status = {
        "promote": "active",
        "retain": "candidate",
        "reject": "rejected",
        "rewrite": "superseded",
    }[verdict]
    if verdict == "rewrite":
        superseded_by = validate_memory_id(superseded_by)
    today = date or time.strftime("%Y-%m-%d")
    text = _STATUS_LINE_RE.sub(rf"\g<1>{new_status}", text, count=1)
    text = _UPDATED_LINE_RE.sub(rf"\g<1>{today}", text, count=1)
    replacements = (
        (_VALIDATION_RE, f"Validation: {verdict}"),
        (_VALIDATED_BY_RE, f"Validated by: {validated_by.strip()}"),
        (_ACTION_DELTA_RE, f"Action delta: {action_delta.strip()}"),
        (_VALIDATION_RATIONALE_RE, f"Validation rationale: {rationale.strip()}"),
        (_EVIDENCE_VERIFIED_RE, f"Evidence verified: {str(bool(evidence_verified)).lower()}"),
        (
            _CURRENT_TARGET_VERIFIED_RE,
            f"Current target verified: {str(bool(current_target_verified)).lower()}",
        ),
        (_CANONICAL_OVERLAP_RE, f"Canonical overlap: {canonical_overlap}"),
    )
    for pattern, line in replacements:
        text = _replace_or_insert_metadata(text, pattern, line)
    if superseded_by:
        text = _replace_or_insert_metadata(
            text, _SUPERSEDED_BY_RE, f"Superseded by: `{superseded_by}`"
        )
    path.write_text(text, encoding="utf-8", newline="")
    return path


def reconcile_memory_record(
    root: Path,
    memory_id: str,
    new_status: str,
    *,
    superseded_by: str = "",
    date: Optional[str] = None,
) -> Path:
    """Status transition preserving history — never deletes, never rewrites
    content. A ``superseded`` transition requires ``superseded_by``."""
    if new_status not in MEMORY_STATUSES:
        raise ValueError(f"unknown memory status: {new_status!r}")
    if new_status == "superseded" and not superseded_by:
        raise ValueError("a superseded record requires superseded_by")
    if superseded_by:
        superseded_by = validate_memory_id(superseded_by)
    path = _contained_record_path(root, memory_id)
    if not path.is_file():
        raise FileNotFoundError(f"memory record not found: {memory_id}")
    text = path.read_text(encoding="utf-8")
    today = date or time.strftime("%Y-%m-%d")
    text, n = _STATUS_LINE_RE.subn(rf"\g<1>{new_status}", text, count=1)
    if n == 0:
        raise ValueError(f"{memory_id}: no Status line to update")
    if _UPDATED_LINE_RE.search(text):
        text = _UPDATED_LINE_RE.sub(rf"\g<1>{today}", text, count=1)
    if superseded_by and not _SUPERSEDED_BY_RE.search(text):
        text = text.replace(
            f"Kind: `", f"Superseded by: `{superseded_by}`\nKind: `", 1
        )
    path.write_text(text, encoding="utf-8", newline="")
    return path


def apply_decay(
    record: dict[str, Any],
    *,
    index_dir: Optional[Path] = None,
    now: Optional[float] = None,
    churn_provider: Optional[Any] = None,
) -> dict[str, Any]:
    """Kind-aware effective confidence (1p8gy Req 13 / AC-13).

    Returns ``{effective_confidence, decay_basis, needs_reverification,
    briefing_included}``. Decay never mutates the record — it is a ranking
    view. ``fragile_file`` never attenuates from churn (council amendment):
    churn sets ``needs_reverification`` and the record never drops below
    briefing inclusion from churn alone. Absent stores degrade to no decay.

    ``churn_provider`` (optional) is a callable ``(path, since_ts) -> int``
    that hot-path callers inject so a whole advisory batch's churn is served
    from ONE store read instead of a per-target store open (delivery-review
    perf finding). When absent, the standalone per-path store read is used
    (correct, used by tests and single-record calls).
    """
    now = now or time.time()
    kind = record["kind"]
    base = float(record.get("confidence") or 0.5)
    out = {
        "effective_confidence": base,
        "decay_basis": "none",
        "needs_reverification": False,
        "briefing_included": True,
    }
    created_ts = _date_ts(record.get("created_at") or "") if record.get("created_at") else None

    def _max_target_churn(since_ts: Optional[int]) -> int:
        file_targets = [
            ref for ref in (record.get("target_refs") or [])
            if not ref.startswith(("symbol:", "community:"))
        ]
        if not file_targets:
            return 0
        if churn_provider is not None:
            return max((int(churn_provider(ref, since_ts)) for ref in file_targets), default=0)
        if index_dir is None:
            return 0
        try:
            import index_state_store as iss
        except ImportError:
            return 0
        worst = 0
        for ref in file_targets:
            fresh = iss.freshness_for_path(index_dir, ref, since_ts=since_ts)
            if fresh:
                worst = max(worst, int(fresh.get("commits_since") or 0))
        return worst

    if kind in CHURN_DECAYED_KINDS:
        churn = _max_target_churn(created_ts)
        if churn:
            out["effective_confidence"] = base / (1.0 + churn / float(CHURN_DECAY_HALVING_COMMITS))
            out["decay_basis"] = f"target_churn:{churn}"
        out["briefing_included"] = out["effective_confidence"] >= BRIEFING_CONFIDENCE_FLOOR
    elif kind in TIME_DECAYED_KINDS and created_ts:
        age_days = max(0.0, (now - created_ts) / 86400.0)
        if age_days > 0:
            out["effective_confidence"] = base / (1.0 + age_days / float(TIME_DECAY_HALVING_DAYS))
            out["decay_basis"] = f"age_days:{round(age_days)}"
        out["briefing_included"] = out["effective_confidence"] >= BRIEFING_CONFIDENCE_FLOOR
    elif kind == "fragile_file":
        churn = _max_target_churn(created_ts)
        if churn:
            out["needs_reverification"] = True
            out["decay_basis"] = f"target_churn:{churn} (flag only)"
        # briefing_included stays True — only reconciliation retires it.
    # operator_preference / decision: no decay of any basis.
    return out


def match_targets(record: dict[str, Any], path: str = "", symbol: str = "") -> bool:
    """Does this record target the given file path or symbol?"""
    for ref in record.get("target_refs") or []:
        if ref.startswith("symbol:"):
            if symbol and ref[len("symbol:"):] in (symbol, symbol.split(".")[-1]):
                return True
        elif ref.startswith("community:"):
            continue  # community scope resolves via the graph, not here
        elif path:
            norm = path.replace("\\", "/")
            if norm == ref or norm.endswith("/" + ref) or ref.endswith("/" + norm):
                return True
    return False


# --- Exact/near-exact duplicate detection (wave 1stwm / change 1stwl) ---
# DETECTION ONLY. This never marks a record superseded/stale, never merges, and
# never deletes — reconciliation stays an explicit operator action, preserving
# the never-auto-rewrite invariant in this module's header. It exists so
# re-running candidate supply (`memory_propose`) is idempotent and so a
# manual add that echoes an existing record is surfaced, not silently
# duplicated. This is exact/normalized detection, NOT fuzzy similarity: no
# embeddings, no similarity model, so the same inputs always yield the same
# verdict.

def normalize_summary(summary: str) -> str:
    """Fixed, documented normalization for duplicate comparison.

    Unicode-casefold, replace every run of non-letter/number characters
    (whitespace, punctuation) with a single space, and trim. Deterministic: identical
    inputs always yield the same key (the AC-4 determinism contract). Used
    only for duplicate detection, never persisted.
    """
    folded = (summary or "").casefold()
    out: list[str] = []
    separating = False
    for char in folded:
        if char.isalnum():
            if separating and out:
                out.append(" ")
            out.append(char)
            separating = False
        else:
            separating = True
    return "".join(out).strip()


def _canonical_ref(value: Any) -> str:
    return str(value or "").strip().strip("`").strip()


def _evidence_identity(value: Any) -> str:
    """Typed originating evidence identity; generic wave/path refs are context."""
    ref = _canonical_ref(value)
    return ref if re.match(r"^(?:ev-|finding[:-]|syn-)", ref) else ""


def _dup_content_key(record: dict[str, Any]) -> tuple[str, tuple[str, ...], str]:
    """The normalized ``(kind, sorted targets, normalized summary)`` identity."""
    kind = record.get("kind") or ""
    targets = tuple(sorted(
        _canonical_ref(value) for value in (record.get("target_refs") or [])
        if _canonical_ref(value)
    ))
    return (kind, targets, normalize_summary(record.get("summary") or ""))


def find_duplicates(
    record: dict[str, Any], existing: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Existing non-history records that duplicate ``record`` — DETECTION ONLY.

    Two independent signals, reported and never auto-resolved:

    - ``evidence_ref``: the two records share at least one ``## Evidence`` ref
      (an originating event id, a wave/change id, or a path). The shared refs
      are returned so a caller (e.g. ``memory_propose``) can decide
      precisely — a re-draft of the same ledger event reproduces that event's
      id ref exactly, which is what makes candidate supply idempotent.
    - ``normalized_content``: the ``(kind, sorted targets, normalized summary)``
      identities are equal (summary compared after ``normalize_summary``).

    Only ``active``/``candidate`` records are compared — retired history
    (``stale``/``superseded``/``rejected``) is never a duplicate. The record's
    own id is skipped. Returns, per matched record,
    ``{memory_id, signals, shared_evidence}``; this function mutates nothing.
    """
    rec_id = record.get("memory_id") or ""
    rec_evidence = {
        identity for value in (record.get("evidence_refs") or [])
        if (identity := _evidence_identity(value))
    }
    rec_key = _dup_content_key(record)
    matches: list[dict[str, Any]] = []
    for other in existing:
        if other.get("status") not in ("active", "candidate"):
            continue
        other_id = other.get("memory_id") or ""
        if rec_id and other_id and other_id == rec_id:
            continue
        signals: list[str] = []
        shared = sorted(
            rec_evidence & {
                identity for value in (other.get("evidence_refs") or [])
                if (identity := _evidence_identity(value))
            }
        )
        if shared:
            signals.append("evidence_ref")
        other_key = _dup_content_key(other)
        if rec_key[2] and other_key[2] and other_key == rec_key:
            signals.append("normalized_content")
        if signals:
            matches.append({
                "memory_id": other_id,
                "signals": signals,
                "shared_evidence": shared,
            })
    return matches
