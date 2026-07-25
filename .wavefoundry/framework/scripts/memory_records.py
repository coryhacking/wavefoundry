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
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable, Optional

sys.dont_write_bytecode = True

_scripts_dir = str(Path(__file__).resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

MEMORY_DIR = "docs/agents/memory"
MEMORY_ARCHIVE_DIR = f"{MEMORY_DIR}/archive"
MEMORY_POINTER_DIR = f"{MEMORY_DIR}/pointers"

# Memory-id grammar (security boundary, delivery-review finding 2026-07-13):
# ids are PATH COMPONENTS (`docs/agents/memory/<id>.md`), and the MCP tools
# accept caller-supplied ids — every filesystem access validates against this
# grammar FIRST, then enforces resolved-path containment as defense in depth.
# Two-form union (wave 1t9w7): new mints carry the repository-wide lifecycle
# naming `<lifecycleId>-mem <slug>`; legacy bare-slug ids remain valid
# indefinitely because field stores reference them. The single space joins two
# independently validated segments and is never a path separator, so the
# containment boundary is unchanged.
_MEMORY_SLUG_PATTERN = r"[a-z0-9][a-z0-9-]{0,63}"
_MEMORY_ID_PATTERN = (
    rf"(?:[0-9a-z]{{5,6}}-mem {_MEMORY_SLUG_PATTERN}|{_MEMORY_SLUG_PATTERN})"
)
MEMORY_ID_RE = re.compile(rf"^{_MEMORY_ID_PATTERN}$")

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
MEMORY_STATUSES = (
    "candidate", "active", "stale", "superseded", "rejected", "archived",
)
ARCHIVE_ELIGIBLE_STATUSES = ("stale", "superseded", "rejected")
ARCHIVE_PROTECTED_KINDS = ("decision", "operator_preference", "fragile_file")
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
# Adaptive cadence calibration (wave 1tbt5). Seven days is the selected
# reference interval: a target changed weekly retains the established 10-commit
# half-life, faster targets receive more commit headroom, and slower targets
# receive less. Candidate reference intervals 3.5 and 14 days were rejected by
# the hermetic calibration as respectively over-eager and too permissive.
ADAPTIVE_CADENCE_MULTIPLIER_DAYS = 7.0
ADAPTIVE_CHURN_MIN_HALVING_COMMITS = 5
ADAPTIVE_CHURN_MAX_HALVING_COMMITS = 40
# Time-decayed kinds: same hyperbolic shape in days. 180 days ≈ the ecosystem
# cadence of tool/dependency releases the gotchas describe.
TIME_DECAY_HALVING_DAYS = 180
TIME_DECAYED_KINDS = ("environment_gotcha", "dependency_gotcha")
ADAPTIVE_TIME_CADENCE_MULTIPLIER = 6.0
ADAPTIVE_TIME_MIN_HALVING_DAYS = 30
ADAPTIVE_TIME_MAX_HALVING_DAYS = 365
# Briefing exclusion floor for churn-decayed kinds only (1p8gy AC-13: a
# heavily-churned failed_attempt can drop OUT of briefings). fragile_file is
# exempt by council amendment: churn is ambiguous evidence there, so it sets
# needs_reverification instead and never drops below inclusion.
BRIEFING_CONFIDENCE_FLOOR = 0.2

MEMORY_KIND_POLICY_FAMILY = {
    "failed_attempt": "tactical",
    "review_finding": "tactical",
    "successful_pattern": "tactical",
    "environment_gotcha": "time_sensitive",
    "dependency_gotcha": "time_sensitive",
    "decision": "protected",
    "operator_preference": "protected",
    "fragile_file": "fragile",
}
_MEMORY_STATUS_ORDER = {
    "active": 0, "candidate": 1, "stale": 2, "superseded": 3,
    "rejected": 4, "archived": 5,
}
_MEMORY_FAMILY_ORDER = {
    "protected": 0, "fragile": 1, "tactical": 2, "time_sensitive": 3,
    "other": 4,
}

_ID_RE = re.compile(rf"^Memory ID:\s*`({_MEMORY_ID_PATTERN})`\s*$", re.MULTILINE)
_KIND_RE = re.compile(r"^Kind:\s*`([a-z_]+)`\s*$", re.MULTILINE)
_STATUS_RE = re.compile(r"^Status:\s+(\S+)\s*$", re.MULTILINE)
# Confidence grammar mirrors the lint (`MEMORY_CONFIDENCE_PATTERN`): any
# non-space token, then a `float()` + range check below (delivery-review
# parity finding — the old `[0-9.]+` rejected lint-valid `1e-1`/`+0.5`).
_CONFIDENCE_RE = re.compile(r"^Confidence:\s*(\S+)\s*$", re.MULTILINE)
_CREATED_RE = re.compile(r"^Created:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
_UPDATED_RE = re.compile(r"^Updated:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
_ARCHIVED_RE = re.compile(r"^Archived:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
_ARCHIVE_REASON_RE = re.compile(r"^Archive reason:\s*(\S[^\r\n]*)$", re.MULTILINE)
_ARCHIVE_PATH_RE = re.compile(r"^Archive path:\s*`([^`\r\n]+)`\s*$", re.MULTILINE)
_POINTER_TO_RE = re.compile(
    rf"^Pointer to:\s*`({_MEMORY_ID_PATTERN})`\s*$", re.MULTILINE
)
_SUPERSEDES_RE = re.compile(
    rf"^Supersedes:\s*`({_MEMORY_ID_PATTERN})`\s*$", re.MULTILINE
)
_SUPERSEDED_BY_RE = re.compile(
    rf"^Superseded by:\s*`({_MEMORY_ID_PATTERN})`\s*$", re.MULTILINE
)
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
    archived = _ARCHIVED_RE.search(text)
    archive_reason = _ARCHIVE_REASON_RE.search(text)
    archive_path = _ARCHIVE_PATH_RE.search(text)
    pointer_to = _POINTER_TO_RE.search(text)
    if status.group(1) == "archived":
        if (
            not archived
            or _date_ts(archived.group(1)) is None
            or not archive_reason
            or not archive_path
            or archive_path.group(1)
            != f"{MEMORY_ARCHIVE_DIR}/{mem_id.group(1)}.md"
        ):
            return None
    elif any((archived, archive_reason, archive_path, pointer_to)):
        return None
    if pointer_to and pointer_to.group(1) != mem_id.group(1):
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
        "archived_at": archived.group(1) if archived else None,
        "archive_reason": archive_reason.group(1).strip() if archive_reason else None,
        "archive_path": archive_path.group(1).strip() if archive_path else None,
        "pointer_to": pointer_to.group(1) if pointer_to else None,
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
        try:
            rel_parts = path.relative_to(memory_root).parts
        except ValueError:
            continue
        if rel_parts and rel_parts[0] == "pointers":
            continue
        is_archive_body = bool(rel_parts and rel_parts[0] == "archive")
        if is_archive_body and wanted is not None and "archived" not in wanted:
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
        if is_archive_body:
            if record["status"] == "archived" and not record.get("pointer_to"):
                record["record_type"] = "archive_body"
            elif (
                wanted is None
                and record["status"] in ARCHIVE_ELIGIBLE_STATUSES
                and not any((
                    record.get("archived_at"),
                    record.get("archive_reason"),
                    record.get("archive_path"),
                    record.get("pointer_to"),
                ))
            ):
                # Rename-first archival intentionally creates this bounded
                # crash state. Keep it visible to unfiltered/history consumers
                # (proposal/backfill disposition census and include_history)
                # without ever surfacing it through default status filters.
                record["record_type"] = "pending_archive_body"
                record["pending_archive"] = True
            else:
                continue
        elif record["status"] == "archived":
            # An interrupted archive can leave an archived-status body at its
            # old path. Never surface it; retrying the archive operation moves
            # it based on current filesystem state.
            continue
        else:
            record["record_type"] = "memory"
        if wanted is not None and record["status"] not in wanted:
            continue
        records.append(record)
    return records


def load_memory_pointers(root: Path) -> list[dict[str, Any]]:
    """Parse compact active pointers without ever traversing archive bodies."""
    memory_root = canonical_memory_root(root)
    if memory_root is None:
        return []
    pointer_root = memory_root / "pointers"
    try:
        if pointer_root.resolve() != root.resolve() / MEMORY_POINTER_DIR:
            return []
    except OSError:
        return []
    if not pointer_root.is_dir() or pointer_root.is_symlink():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(pointer_root.glob("*.md")):
        try:
            if path.is_symlink() or path.resolve().parent != pointer_root.resolve():
                continue
        except OSError:
            continue
        record = parse_memory_record(path)
        expected_archive = f"{MEMORY_ARCHIVE_DIR}/{path.stem}.md"
        if (
            record is None
            or record["status"] != "archived"
            or record.get("pointer_to") != record["memory_id"]
            or record.get("archive_path") != expected_archive
        ):
            continue
        record["record_type"] = "archive_pointer"
        record["keywords"] = _BACKTICK_RE.findall(_section(
            path.read_text(encoding="utf-8", errors="replace"), "## Keywords"
        ))
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
            f"invalid memory id {memory_id!r}: must be a bare slug "
            "([a-z0-9][a-z0-9-]*, max 64 chars) or the lifecycle form "
            "'<lifecycleId>-mem <slug>'"
        )
    return candidate


def mint_memory_id(root: Path, slug_source: str, *, timestamp=None) -> str:
    """Mint a new-form memory id ``<lifecycleId>-mem <slug>`` (wave 1t9w7).

    The prefix is minted under the repository's own lifecycle policy —
    deterministic for a given (day, slug) via the v2 entropy hash, which
    makes backdated migration minting idempotent. There is no legacy
    fallback: a repository whose policy cannot resolve raises exactly as a
    wave or change mint would.
    """
    import lifecycle_id

    slug = slugify(slug_source)
    prefix = lifecycle_id.build_prefix(
        timestamp,
        policy=lifecycle_id.load_lifecycle_policy(root),
        kind="mem",
        slug=slug,
    )
    return f"{prefix}-mem {slug}"


# Migration scope (operator ruling on finding bare-legacy-id-references-
# stranded): only GENERATED legacy records — always `mem-*` — are renamed,
# so reference discovery is mem-prefixed by design. Non-mem bare ids remain
# contract-valid but frozen: never auto-renamed, so their references never
# go stale. A bare token is also indistinguishable from ordinary prose,
# which is why widening discovery was rejected.
_LEGACY_REF_TOKEN_RE = re.compile(r"`(mem-[a-z0-9][a-z0-9-]{0,60})`")


def _wave_dir_status(wave_dir: Path) -> Optional[str]:
    """The ``Status:`` value of a wave directory's wave.md; None when unreadable."""

    try:
        text = (wave_dir / "wave.md").read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"^Status:\s+(\S+)\s*$", text, re.MULTILINE)
    return match.group(1).lower() if match else None


def migrate_memory_ids_to_lifecycle_naming(root: Path) -> dict[str, Any]:
    """Rename generated legacy ``mem-*`` records to ``<lifecycleId>-mem <slug>``.

    Scope (wave 1t9w7, operator ruling): only generated legacy records —
    which are always ``mem-*`` — are renamed. Explicit bare-slug ids remain
    contract-valid but FROZEN: never auto-renamed, never half-migrated, and
    therefore never a source of stranded references.

    Deterministic (each prefix is minted from the record's own ``Created``
    date, and v2 entropy is a hash of kind+slug) and interruption-safe by
    construction (operator finding, delivery cycle 0): every pass derives its
    work from CURRENT on-disk state, never from an earlier pass's in-run
    bookkeeping, so a rerun after a crash in ANY window converges.

    - Rename pass: a new-form target that already exists with the SAME
      internal memory id is this rename's own crash residue (deterministic
      minting is injective over distinct legacy records), so the leftover
      legacy file is removed to complete the interrupted step; only a target
      whose internal id disagrees raises.
    - Reference passes: stale backticked ``mem-``-prefixed tokens are
      DISCOVERED by scanning and resolved to their migrated record by slug
      lookup against the directory — so references are repaired even when the
      rename happened in an earlier interrupted run. Scope: the memory root,
      every live doc surface (``docs/**/*.md`` plus repository-root
      markdown), and the ``memory_backfill_sources`` rows. Closed or
      unclassifiable wave directories are skipped silently — archives keep
      historical ids by policy — and only markdown is ever touched, so events
      ledgers and other append-only history are structurally out of reach.
    - A stale token on a live surface that cannot be resolved to a migrated
      record is returned in ``residual_references`` for loud reporting, never
      silently rewritten or dropped.

    Returns ``{"renamed", "skipped", "mapping", "references_repaired",
    "residual_references"}``.
    """
    from datetime import datetime as _dt
    from datetime import timezone as _tz

    memory_root = canonical_memory_root(root)
    if memory_root is None or not memory_root.is_dir():
        return {
            "renamed": 0,
            "skipped": 0,
            "mapping": {},
            "references_repaired": 0,
            "residual_references": [],
        }
    mapping: dict[str, str] = {}
    skipped = 0
    renamed = 0
    for path in sorted(memory_root.glob("*.md")):
        parsed = parse_memory_record(path)
        if not parsed:
            skipped += 1
            continue
        old_id = parsed["memory_id"]
        if " " in old_id or not old_id.startswith("mem-"):
            # New-form records AND non-mem bare ids are both left alone: the
            # migration renames only generated `mem-*` legacy records, so a
            # bare-id record is never half-migrated with stranded references
            # (operator scope ruling on the bare-id finding).
            skipped += 1
            continue
        slug_source = old_id[4:]
        timestamp = None
        created = str(parsed.get("created_at") or "")
        try:
            timestamp = _dt.strptime(created, "%Y-%m-%d").replace(tzinfo=_tz.utc)
        except ValueError:
            pass
        new_id = mint_memory_id(root, slug_source, timestamp=timestamp)
        new_path = _contained_record_path(root, new_id)
        if new_path.exists():
            existing = parse_memory_record(new_path)
            if existing and existing["memory_id"] == new_id:
                # Crash residue of this exact rename: the migrated copy is
                # already durable, so complete the interrupted step.
                path.unlink()
                mapping[old_id] = new_id
                renamed += 1
                continue
            raise ValueError(
                f"migration collision: {new_id!r} already exists with a "
                f"different internal id while renaming {old_id!r} — refusing"
            )
        text = path.read_text(encoding="utf-8")
        text = text.replace(f"Memory ID: `{old_id}`", f"Memory ID: `{new_id}`")
        new_path.write_text(text, encoding="utf-8")
        path.unlink()
        mapping[old_id] = new_id
        renamed += 1

    def _resolve_stale(token: str) -> Optional[str]:
        slug = token[4:]
        if len(slug) < 2:
            return None
        matches = list(memory_root.glob(f"*-mem {slug}.md"))
        if len(matches) == 1:
            return matches[0].stem
        return None

    def _repair_text_file(path: Path) -> tuple[int, list[str]]:
        text = original = path.read_text(encoding="utf-8")
        repaired = 0
        unresolved: list[str] = []
        for token in sorted(set(_LEGACY_REF_TOKEN_RE.findall(text))):
            new_id = _resolve_stale(token)
            if new_id is None:
                unresolved.append(token)
                continue
            text = text.replace(f"`{token}`", f"`{new_id}`")
            repaired += 1
        if text != original:
            path.write_text(text, encoding="utf-8")
        return repaired, unresolved

    references_repaired = 0
    residual_references: list[dict[str, str]] = []

    def _repair_and_record(path: Path) -> None:
        nonlocal references_repaired
        repaired, unresolved = _repair_text_file(path)
        references_repaired += repaired
        for token in unresolved:
            residual_references.append(
                {"path": str(path.relative_to(root)), "token": token}
            )

    for path in sorted(memory_root.glob("*.md")):
        _repair_and_record(path)
    docs_root = root / "docs"
    if docs_root.is_dir():
        for path in sorted(docs_root.rglob("*.md")):
            rel_parts = path.relative_to(root).parts
            if rel_parts[:3] == ("docs", "agents", "memory"):
                continue
            if rel_parts[:2] == ("docs", "waves"):
                if len(rel_parts) < 3:
                    continue
                status = _wave_dir_status(root / Path(*rel_parts[:3]))
                if status != "closed" and status is not None:
                    _repair_and_record(path)
                continue
            _repair_and_record(path)
    for path in sorted(root.glob("*.md")):
        _repair_and_record(path)

    db_path = root / ".wavefoundry" / "index" / "memory-state.sqlite"
    if db_path.exists():
        import sqlite3

        conn = sqlite3.connect(db_path)
        try:
            with conn:
                rows = conn.execute(
                    "SELECT DISTINCT memory_id FROM memory_backfill_sources "
                    "WHERE memory_id LIKE 'mem-%'"
                ).fetchall()
                for (stale_id,) in rows:
                    new_id = _resolve_stale(str(stale_id))
                    if new_id is None:
                        residual_references.append(
                            {"path": "memory-state.sqlite", "token": str(stale_id)}
                        )
                        continue
                    conn.execute(
                        "UPDATE memory_backfill_sources SET memory_id=? "
                        "WHERE memory_id=?",
                        (new_id, stale_id),
                    )
                    references_repaired += 1
        finally:
            conn.close()
    return {
        "renamed": renamed,
        "skipped": skipped,
        "mapping": mapping,
        "references_repaired": references_repaired,
        "residual_references": residual_references,
    }


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


def _contained_memory_subdir_path(root: Path, memory_id: str, subdir: str) -> Path:
    """Resolve one reserved memory subdirectory path without allowing escapes."""
    memory_id = validate_memory_id(memory_id)
    if subdir not in ("archive", "pointers"):
        raise ValueError(f"unknown memory subdirectory: {subdir!r}")
    memory_root = canonical_memory_root(root)
    if memory_root is None:
        raise ValueError(
            "memory root resolves outside its canonical repository location "
            "(symlinked memory directory or ancestor) — refusing"
        )
    repo = root.resolve()
    expected_parent = repo / MEMORY_DIR / subdir
    path = memory_root / subdir / f"{memory_id}.md"
    resolved = path.resolve()
    if resolved.parent != expected_parent or not resolved.is_relative_to(repo):
        raise ValueError(f"memory id {memory_id!r} escapes the {subdir} directory")
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
            # New-form ids suffix the SLUG segment only, so truncation can
            # never corrupt the lifecycle prefix or strand the separator.
            if " " in base:
                head, slug_part = base.split(" ", 1)
                memory_id = f"{head} {slug_part[:56].rstrip('-') or 'record'}-{n}"
            else:
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


def archive_eligibility(record: dict[str, Any]) -> dict[str, Any]:
    """Return explicit archive eligibility and the protected-kind review cue."""
    status = str(record.get("status") or "")
    kind = str(record.get("kind") or "")
    eligible = status in ARCHIVE_ELIGIBLE_STATUSES
    return {
        "eligible": eligible,
        "protected": kind in ARCHIVE_PROTECTED_KINDS,
        "reason": (
            "record status is archive-eligible"
            if eligible
            else "archive requires stale, superseded, or rejected status"
        ),
    }


def _render_archive_pointer(record: dict[str, Any]) -> str:
    memory_id = record["memory_id"]
    archived_at = record["archived_at"]
    archive_path = f"{MEMORY_ARCHIVE_DIR}/{memory_id}.md"
    summary = " ".join(str(record.get("summary") or "").split())
    evidence = list(record.get("evidence_refs") or [])
    targets = list(record.get("target_refs") or [])
    keyword_values = sorted({
        memory_id,
        str(record.get("title") or memory_id),
        str(record.get("kind") or ""),
        *(str(value) for value in targets),
    })
    lines = [
        f"# {record.get('title') or memory_id}",
        "",
        "Owner: Engineering",
        "Status: archived",
        f"Last verified: {archived_at}",
        "",
        f"Memory ID: `{memory_id}`",
        f"Kind: `{record['kind']}`",
        f"Confidence: {record.get('confidence', 0.0)}",
        f"Created: {record['created_at']}",
        f"Updated: {record['updated_at']}",
        f"Archived: {archived_at}",
        f"Archive reason: {record['archive_reason']}",
        f"Archive path: `{archive_path}`",
        f"Pointer to: `{memory_id}`",
    ]
    if record.get("superseded_by"):
        lines.append(f"Superseded by: `{record['superseded_by']}`")
    lines += [
        "",
        "## Summary",
        "",
        summary[:280],
        "",
        "## Evidence",
        "",
        *[f"- `{value}`" for value in evidence],
        "",
        "## Targets",
        "",
        *[f"- `{value}`" for value in targets],
        "",
        "## Keywords",
        "",
        *[f"- `{value}`" for value in keyword_values if value],
    ]
    return "\n".join(lines) + "\n"


def _atomic_replace_text(path: Path, content: str) -> None:
    """Publish one complete text file atomically in its destination directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    )
    tmp_path = Path(handle.name)
    try:
        with handle:
            handle.write(content)
            handle.flush()
        tmp_path.replace(path)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def archive_memory_record(
    root: Path,
    memory_id: str,
    *,
    reason: str,
    eligibility_confirmed: bool = False,
    date: Optional[str] = None,
    _interrupt_after: str = "",
) -> dict[str, Any]:
    """State-derived rename + compact pointer publication.

    The caller serializes this transaction with the shared cross-process
    memory/review lock and holds a writer-owned memory fence. Every retry
    re-derives progress from the active body, archive body, and pointer
    currently on disk. The body is renamed with ``Path.replace``; copy/delete
    is never used.
    """
    memory_id = validate_memory_id(memory_id)
    reason = str(reason or "").strip()
    if not reason or any(char in reason for char in ("\r", "\n")):
        raise ValueError("archive_reason must be a non-empty single line")
    active_path = _contained_record_path(root, memory_id)
    archive_path = _contained_memory_subdir_path(root, memory_id, "archive")
    pointer_path = _contained_memory_subdir_path(root, memory_id, "pointers")

    if active_path.exists() and archive_path.exists():
        raise ValueError(
            f"{memory_id}: both active and archived bodies exist; refusing to guess"
        )

    moved = False
    if archive_path.is_file():
        text = archive_path.read_text(encoding="utf-8")
        record = parse_memory_record(archive_path, text)
        if record is None:
            # The first transition deliberately moves the still-retired body
            # under the index-excluded archive path before rewriting metadata.
            # Parse it against its stable id so a retry can finish that state.
            record = parse_memory_record(active_path, text)
        if record is None:
            raise ValueError(f"{memory_id}: malformed archived memory body")
    elif active_path.is_file():
        text = active_path.read_text(encoding="utf-8")
        record = parse_memory_record(active_path, text)
        if record is None:
            raise ValueError(f"{memory_id}: malformed memory record")
        eligibility = archive_eligibility(record)
        if not eligibility["eligible"]:
            raise ValueError(f"{memory_id}: {eligibility['reason']}")
        if eligibility["protected"] and not eligibility_confirmed:
            raise ValueError(
                f"{memory_id}: {record['kind']} is protected; set "
                "eligibility_confirmed=true only after verifying it is no longer operational"
            )
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        active_path.replace(archive_path)
        moved = True
        if _interrupt_after == "body_rename":
            raise RuntimeError("injected interruption after body rename")
    else:
        raise FileNotFoundError(f"memory record not found: {memory_id}")

    if record["status"] != "archived":
        eligibility = archive_eligibility(record)
        if not eligibility["eligible"]:
            raise ValueError(f"{memory_id}: {eligibility['reason']}")
        if eligibility["protected"] and not eligibility_confirmed:
            raise ValueError(
                f"{memory_id}: {record['kind']} is protected; set "
                "eligibility_confirmed=true only after verifying it is no longer operational"
            )
        today = date or time.strftime("%Y-%m-%d")
        if _date_ts(today) is None:
            raise ValueError("archive date must be YYYY-MM-DD")
        text = _STATUS_LINE_RE.sub(r"\g<1>archived", text, count=1)
        text = _UPDATED_LINE_RE.sub(rf"\g<1>{today}", text, count=1)
        text = _replace_or_insert_metadata(text, _ARCHIVED_RE, f"Archived: {today}")
        text = _replace_or_insert_metadata(
            text, _ARCHIVE_REASON_RE, f"Archive reason: {reason}"
        )
        text = _replace_or_insert_metadata(
            text,
            _ARCHIVE_PATH_RE,
            f"Archive path: `{MEMORY_ARCHIVE_DIR}/{memory_id}.md`",
        )
        _atomic_replace_text(archive_path, text)
        if _interrupt_after == "status_rewrite":
            raise RuntimeError("injected interruption after status rewrite")
        record = parse_memory_record(archive_path)
        if record is None:
            raise ValueError(f"{memory_id}: archived body failed schema validation")

    record["record_type"] = "archive_body"
    pointer_text = _render_archive_pointer(record)
    no_op = not moved
    try:
        existing_pointer = pointer_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        existing_pointer = ""
    if existing_pointer != pointer_text:
        _atomic_replace_text(pointer_path, pointer_text)
        no_op = False
        if _interrupt_after == "pointer_publish":
            raise RuntimeError("injected interruption after pointer publication")
    pointer = parse_memory_record(pointer_path)
    if pointer is None or pointer.get("pointer_to") != memory_id:
        raise ValueError(f"{memory_id}: archive pointer failed schema validation")
    pointer["record_type"] = "archive_pointer"
    return {
        "archive_path": archive_path,
        "pointer_path": pointer_path,
        "record": record,
        "pointer": pointer,
        "moved": moved,
        "no_op": no_op,
    }


def _median_commit_interval_days(values: Iterable[int]) -> Optional[float]:
    times = sorted({int(ts) for ts in values if int(ts) > 0})
    ordered = sorted(
        newer - older for older, newer in zip(times, times[1:])
        if newer > older
    )
    if not ordered:
        return None
    middle = len(ordered) // 2
    median_gap = (
        float(ordered[middle])
        if len(ordered) % 2
        else (ordered[middle - 1] + ordered[middle]) / 2.0
    )
    return max(median_gap / 86400.0, 1.0 / 86400.0)


def _target_cadences(
    target_refs: Iterable[str],
    commit_times_by_path: Optional[dict[str, list[int]]],
) -> list[Optional[float]]:
    histories = commit_times_by_path or {}
    return [
        _median_commit_interval_days(histories.get(ref, []))
        for ref in target_refs
        if not ref.startswith(("symbol:", "community:"))
    ]


def adaptive_churn_halving_commits(
    target_refs: Iterable[str],
    commit_times_by_path: Optional[dict[str, list[int]]] = None,
) -> int:
    """Return the conservative cadence-derived tactical churn half-life."""
    candidates: list[int] = []
    for cadence_days in _target_cadences(target_refs, commit_times_by_path):
        if cadence_days is None:
            candidates.append(CHURN_DECAY_HALVING_COMMITS)
            continue
        derived = round(
            CHURN_DECAY_HALVING_COMMITS
            * ADAPTIVE_CADENCE_MULTIPLIER_DAYS
            / cadence_days
        )
        candidates.append(max(
            ADAPTIVE_CHURN_MIN_HALVING_COMMITS,
            min(ADAPTIVE_CHURN_MAX_HALVING_COMMITS, derived),
        ))
    return min(candidates, default=CHURN_DECAY_HALVING_COMMITS)


def adaptive_time_halving_days(
    target_refs: Iterable[str],
    commit_times_by_path: Optional[dict[str, list[int]]] = None,
) -> int:
    """Return the conservative cadence-derived time-sensitive half-life."""
    candidates: list[int] = []
    for cadence_days in _target_cadences(target_refs, commit_times_by_path):
        if cadence_days is None:
            candidates.append(TIME_DECAY_HALVING_DAYS)
            continue
        derived = round(cadence_days * ADAPTIVE_TIME_CADENCE_MULTIPLIER)
        candidates.append(max(
            ADAPTIVE_TIME_MIN_HALVING_DAYS,
            min(ADAPTIVE_TIME_MAX_HALVING_DAYS, derived),
        ))
    return min(candidates, default=TIME_DECAY_HALVING_DAYS)


def memory_comparability_partition(
    record: dict[str, Any], *, exact_target_match: bool = False
) -> tuple[Any, ...]:
    """Policy identity inside which freshness/relevance may reorder records."""
    return (
        round(float(record.get("confidence") or 0.5), 2),
        str(record.get("status") or ""),
        bool(exact_target_match),
        MEMORY_KIND_POLICY_FAMILY.get(str(record.get("kind") or ""), "other"),
    )


def memory_policy_sort_key(
    record: dict[str, Any],
    decay: dict[str, Any],
    *,
    exact_target_match: bool = False,
    relevance_rank: int = 0,
    centrality: float = 0.0,
) -> tuple[Any, ...]:
    """Canonical policy -> freshness -> relevance -> centrality ordering."""
    base_band, status, exact, family = memory_comparability_partition(
        record, exact_target_match=exact_target_match
    )
    return (
        0 if exact else 1,
        -base_band,
        _MEMORY_STATUS_ORDER.get(status, 99),
        _MEMORY_FAMILY_ORDER.get(family, 99),
        -round(float(decay.get("effective_confidence") or 0.0), 6),
        int(relevance_rank),
        -float(centrality),
        str(record.get("memory_id") or ""),
    )


def apply_decay(
    record: dict[str, Any],
    *,
    index_dir: Optional[Path] = None,
    now: Optional[float] = None,
    churn_provider: Optional[Any] = None,
    commit_times_by_path: Optional[dict[str, list[int]]] = None,
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
        halving = adaptive_churn_halving_commits(
            record.get("target_refs") or [], commit_times_by_path
        )
        out["halving_commits"] = halving
        if churn:
            out["effective_confidence"] = base / (1.0 + churn / float(halving))
            out["decay_basis"] = (
                f"target_churn:{churn};halving_commits:{halving}"
            )
        out["briefing_included"] = out["effective_confidence"] >= BRIEFING_CONFIDENCE_FLOOR
    elif kind in TIME_DECAYED_KINDS and created_ts:
        age_days = max(0.0, (now - created_ts) / 86400.0)
        halving_days = adaptive_time_halving_days(
            record.get("target_refs") or [], commit_times_by_path
        )
        out["halving_days"] = halving_days
        if age_days > 0:
            out["effective_confidence"] = base / (
                1.0 + age_days / float(halving_days)
            )
            out["decay_basis"] = (
                f"age_days:{round(age_days)};halving_days:{halving_days}"
            )
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
