from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterable

from .constants import (
    ALLOWED_CHANGE_STATUS_TRANSITIONS,
    ALLOWED_ITEM_STATUS_TRANSITIONS,
    BACKTICK_VALUE_PATTERN,
    CHANGE_ID_PATTERN,
    CHANGE_REFERENCE_PATTERN,
    CHANGE_STATUS_PATTERN,
    DEPENDS_ON_LINE_PATTERN,
    FACTOR_REVIEW_MARKERS,
    HYBRID_LEGACY_MARKERS,
    INDEX_REQUIRED_REFERENCES,
    ITEM_REFERENCE_PATTERN,
    ITEM_ID_PATTERN,
    ITEM_STATUS_PATTERN,
    JOURNAL_DISALLOWED_PATTERNS,
    JOURNAL_GOVERNANCE_MARKERS,
    JOURNAL_SALIENCE_MARKERS,
    JOURNAL_SIGNAL_MARKERS,
    JOURNAL_PATH_PATTERN,
    JOURNAL_REQUIRED_SECTIONS,
    LEGACY_MARKERS,
    MANIFEST_REQUIRED_GENERATED_ARTIFACTS,
    MARKDOWN_HEADING_PATTERN,
    PERSONA_REQUIRED_SECTIONS,
    PLAN_WAVE_OVERVIEW_PATTERN,
    PREVIOUS_ITEM_STATUS_PATTERN,
    PREVIOUS_CHANGE_STATUS_PATTERN,
    PROGRESSABLE_CHANGE_STATUSES,
    PROGRESSABLE_ITEM_STATUSES,
    TERMINAL_CHANGE_STATUSES,
    TERMINAL_ITEM_STATUSES,
    WAVE_WATCHPOINT_MARKERS,
    WAVE_REFERENCE_PATTERN,
    WAVE_ID_PATTERN,
    WAVE_REQUIRED_PATHS,
    WAVE_REQUIRED_SECTIONS,
)
from .helpers import load_json, read_text, relative_to_root


_H1_TITLE_RE = re.compile(r"^#\s+\S", re.MULTILINE)

_CHANGE_DOC_REQUIRED_SECTIONS = (
    "## Rationale",
    "## Acceptance Criteria",
    "## AC Priority",
)

def _extract_backtick_value(raw_line: str) -> str:
    if "`" not in raw_line:
        return raw_line
    return raw_line.split("`", 1)[-1].rsplit("`", 1)[0]


def _extract_sections(text: str) -> dict[str, str]:
    headings = list(MARKDOWN_HEADING_PATTERN.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(headings):
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        sections[match.group(1)] = text[start:end].strip()
    return sections


def _section_has_bullets(section_text: str) -> bool:
    return any(line.lstrip().startswith("- ") for line in section_text.splitlines())


def _contains_any(text: str, markers: Iterable[str]) -> bool:
    lowered = text.casefold()
    return any(marker in lowered for marker in markers)


def _metadata_value(text: str, key: str) -> str | None:
    prefix = f"{key}:"
    for raw_line in text.splitlines():
        if raw_line.startswith(prefix):
            return raw_line.split(":", 1)[1].strip()
    return None


def _is_activated_wave(text: str) -> bool:
    for raw_line in text.splitlines():
        if raw_line.startswith("Activated at:"):
            return raw_line.split(":", 1)[1].strip().casefold() != "not activated"
    return False


def _wave_requires_wave_owned_change_docs(text: str) -> bool:
    """Ready/active waves and activated waves must keep admitted change docs under the wave folder only."""
    status = (_metadata_value(text, "Status") or "").casefold()
    if status in {"active", "ready"}:
        return True
    if status in {"completed", "closed"}:
        return False
    return _is_activated_wave(text)


@dataclass(slots=True)
class WorkRecord:
    record_id: str
    status: str | None = None
    previous_status: str | None = None
    depends_on: list[str] = field(default_factory=list)
    path: str = ""
    wave_id: str | None = None
    anchor_type: str = "change"


@dataclass(slots=True)
class WaveRecord:
    wave_id: str
    path: str
    record_ids: list[str] = field(default_factory=list)


def _parse_change_records(text: str, rel: str) -> list[WorkRecord]:
    records: list[WorkRecord] = []
    lines = text.splitlines()
    current: WorkRecord | None = None
    current_wave_id = WAVE_ID_PATTERN.findall(text)
    wave_id = current_wave_id[0] if len(current_wave_id) == 1 else None
    for raw_line in lines:
        line = raw_line.strip()
        change_match = CHANGE_ID_PATTERN.match(line)
        if change_match:
            if current is not None:
                records.append(current)
            current = WorkRecord(record_id=change_match.group(1), path=rel, wave_id=wave_id, anchor_type="change")
            continue
        if current is None:
            continue
        status_match = CHANGE_STATUS_PATTERN.match(line)
        if status_match:
            current.status = status_match.group(1)
            continue
        previous_status_match = PREVIOUS_CHANGE_STATUS_PATTERN.match(line)
        if previous_status_match:
            current.previous_status = previous_status_match.group(1)
            continue
        depends_match = DEPENDS_ON_LINE_PATTERN.match(line)
        if depends_match:
            current.depends_on.extend(BACKTICK_VALUE_PATTERN.findall(depends_match.group(1)))
    if current is not None:
        records.append(current)
    if records and ("## Changes" in text or any(record.status is not None for record in records)):
        return records
    return []


def _parse_legacy_item_records(text: str, rel: str) -> list[WorkRecord]:
    records: list[WorkRecord] = []
    lines = text.splitlines()
    current: WorkRecord | None = None
    current_wave_id = WAVE_ID_PATTERN.findall(text)
    wave_id = current_wave_id[0] if len(current_wave_id) == 1 else None
    for raw_line in lines:
        line = raw_line.strip()
        item_match = ITEM_ID_PATTERN.match(line)
        if item_match:
            if current is not None:
                records.append(current)
            current = WorkRecord(record_id=item_match.group(1), path=rel, wave_id=wave_id, anchor_type="item")
            continue
        if current is None:
            continue
        status_match = ITEM_STATUS_PATTERN.match(line)
        if status_match:
            current.status = status_match.group(1)
            continue
        previous_status_match = PREVIOUS_ITEM_STATUS_PATTERN.match(line)
        if previous_status_match:
            current.previous_status = previous_status_match.group(1)
            continue
        depends_match = DEPENDS_ON_LINE_PATTERN.match(line)
        if depends_match:
            current.depends_on.extend(BACKTICK_VALUE_PATTERN.findall(depends_match.group(1)))
    if current is not None:
        records.append(current)
    return records


def _parse_work_records(text: str, rel: str) -> list[WorkRecord]:
    change_records = _parse_change_records(text, rel)
    if change_records:
        return change_records
    return _parse_legacy_item_records(text, rel)


def _collect_wave_state(root: Path) -> tuple[dict[str, WaveRecord], dict[str, WorkRecord]]:
    waves: dict[str, WaveRecord] = {}
    records: dict[str, WorkRecord] = {}
    wave_root = root / "docs/waves"
    for path in sorted(wave_root.rglob("*.md")):
        if path.name == "README.md":
            continue
        rel = relative_to_root(root, path)
        text = read_text(path)
        wave_matches = WAVE_ID_PATTERN.findall(text)
        wave_id = wave_matches[0] if len(wave_matches) == 1 else None
        if wave_id:
            work_records = _parse_work_records(text, rel)
            waves[wave_id] = WaveRecord(wave_id=wave_id, path=rel, record_ids=[record.record_id for record in work_records])
            for record in work_records:
                records[record.record_id] = record
    return waves, records


def _parse_required_reviewer_lanes(readiness_text: str) -> set[str]:
    required: set[str] = set()
    for raw_line in readiness_text.splitlines():
        normalized = raw_line.strip()
        if "required reviewer lanes:" not in normalized.casefold():
            continue
        lower = normalized.casefold()
        for lane in (
            "code-reviewer",
            "qa-reviewer",
            "architecture-reviewer",
            "security-reviewer",
            "performance-reviewer",
            "docs-contract-reviewer",
            "release-reviewer",
            "factor-09-disposability",
        ):
            if lane in lower:
                required.add(lane)
    return required


def _review_lane_markers() -> dict[str, tuple[str, ...]]:
    return {
        "code-reviewer": ("code review", "code-reviewer"),
        "qa-reviewer": ("qa review", "qa-reviewer"),
        "architecture-reviewer": ("architecture review", "architecture-reviewer"),
        "security-reviewer": ("security review", "security-reviewer"),
        "performance-reviewer": ("performance review", "performance-reviewer"),
        "docs-contract-reviewer": ("docs-contract review", "docs contract review", "docs-contract-reviewer"),
        "release-reviewer": ("release review", "release-reviewer"),
        "factor-09-disposability": ("factor-09-disposability", "disposability"),
    }


def check_closed_wave_requirements(root: Path) -> list[str]:
    failures: list[str] = []
    wave_root = root / "docs/waves"
    terminal_statuses = {"complete", "completed", "deferred", "moved", "superseded", "closed"}
    handoff_text = read_text(root / "docs/agents/session-handoff.md") if (root / "docs/agents/session-handoff.md").exists() else ""

    for path in sorted(wave_root.rglob("*.md")):
        if path.name == "README.md":
            continue
        rel = relative_to_root(root, path)
        text = read_text(path)
        if "wave-id:" not in text or ("## Changes" not in text and "## Items" not in text):
            continue
        status = (_metadata_value(text, "Status") or "").casefold()
        sections = _extract_sections(text)
        # Current state is prose in most waves; use direct text probe.
        is_closed_wave = status in {"completed", "closed"} and "**current state:** completed." in text.casefold()
        if not is_closed_wave:
            continue

        completed_at = _metadata_value(text, "Completed at")
        if not completed_at:
            failures.append(f"{rel}: closed wave must record `Completed at`")

        work_records = _parse_work_records(text, rel)
        if not work_records:
            failures.append(f"{rel}: closed wave must declare at least one change")
        for record in work_records:
            if record.status is None:
                status_label = "Change Status" if record.anchor_type == "change" else "Item Status"
                failures.append(f"{rel}: closed wave {record.anchor_type} `{record.record_id}` is missing `{status_label}`")
            elif record.status.casefold() not in terminal_statuses:
                failures.append(
                    f"{rel}: closed wave {record.anchor_type} `{record.record_id}` must be terminal, found `{record.status}`"
                )

        readiness = sections.get("## Readiness checkpoints", "")
        reviews = sections.get("## Review checkpoints", "")
        required_lanes = _parse_required_reviewer_lanes(readiness)
        review_markers = _review_lane_markers()
        lowered_reviews = reviews.casefold()
        for lane in sorted(required_lanes):
            markers = review_markers.get(lane, (lane,))
            if not any(marker in lowered_reviews for marker in markers):
                failures.append(
                    f"{rel}: closed wave is missing review checkpoint evidence for required reviewer lane `{lane}`"
                )

        if "wave-id:" in text:
            wave_ids = WAVE_REFERENCE_PATTERN.findall(text)
            if wave_ids:
                wave_id = wave_ids[0]
                if f"Active wave ID: `{wave_id}`" in handoff_text or f"Active wave ID: {wave_id}" in handoff_text:
                    failures.append(
                        f"{rel}: closed wave `{wave_id}` still appears as active in `docs/agents/session-handoff.md`"
                    )

    return failures


def check_plan_filenames(root: Path) -> list[str]:
    """Enforce that every `docs/plans/*.md` basename matches its `Change ID` (or `Wave:` for
    wave-level overview plans). Prevents slug-only plan filenames from slipping in during
    staging before wave readiness would normally fire the staging-vs-wave check."""
    failures: list[str] = []
    plans_root = root / "docs/plans"
    if not plans_root.is_dir():
        return failures

    skip_names = {"plan-template.md", "README.md"}

    for path in sorted(plans_root.iterdir()):
        if not path.is_file() or path.suffix != ".md":
            continue
        if path.name in skip_names:
            continue
        rel = relative_to_root(root, path)
        text = read_text(path)
        basename = path.stem

        change_ids = CHANGE_ID_PATTERN.findall(text)
        if change_ids:
            expected = change_ids[0]
            if basename != expected:
                failures.append(
                    f"{rel}: plan filename must match `Change ID` — rename to "
                    f"`docs/plans/{expected}.md` (see `docs/plans/plan-template.md` → "
                    f"**Change ID / Filename**; generate new IDs with "
                    f"`python3 .wavefoundry/framework/scripts/lifecycle_id.py`)"
                )
            if len(set(change_ids)) > 1:
                failures.append(
                    f"{rel}: plan declares multiple `Change ID` values "
                    f"({', '.join(f'`{cid}`' for cid in sorted(set(change_ids)))}); split into one plan per change"
                )
            continue

        wave_overview_ids = PLAN_WAVE_OVERVIEW_PATTERN.findall(text)
        if wave_overview_ids:
            expected = wave_overview_ids[0]
            if basename != expected:
                failures.append(
                    f"{rel}: wave-level plan filename must match `Wave:` identifier — rename to "
                    f"`docs/plans/{expected}.md`"
                )
            continue

        failures.append(
            f"{rel}: plan is missing a `Change ID:` or `Wave:` identifier line — "
            f"generate a change-id with "
            f"`python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>`, "
            f"record it as `Change ID: \\`<id>\\`` in the file, and ensure the filename matches "
            f"(see `docs/plans/plan-template.md` → **Change ID / Filename**)"
        )

    return failures


def check_wave_roots(root: Path) -> list[str]:
    failures: list[str] = []
    for relative in WAVE_REQUIRED_PATHS:
        path = root / relative
        if not path.exists():
            failures.append(f"{relative}: missing required Wavefoundry generated artifact")
    return failures


def check_wave_docs(root: Path) -> list[str]:
    failures: list[str] = []
    wave_root = root / "docs/waves"
    seen_wave_ids: dict[str, str] = {}
    seen_item_ids: set[str] = set()
    for path in sorted(wave_root.rglob("*.md")):
        rel = relative_to_root(root, path)
        if path.name == "README.md":
            continue
        text = read_text(path)
        if "wave-id:" not in text and "Item ID:" not in text:
            continue
        wave_matches = WAVE_ID_PATTERN.findall(text)
        if not wave_matches:
            failures.append(f"{rel}: missing stable `wave-id` declaration")
        elif len(wave_matches) > 1:
            failures.append(f"{rel}: multiple `wave-id` declarations found")
        else:
            wave_id = wave_matches[0]
            existing = seen_wave_ids.get(wave_id)
            if existing is not None:
                failures.append(f"{rel}: duplicate `wave-id` `{wave_id}` across wave artifacts (already declared in {existing})")
            else:
                seen_wave_ids[wave_id] = rel
        for section in WAVE_REQUIRED_SECTIONS:
            if section not in text:
                failures.append(f"{rel}: missing required section `{section}`")
        if not _metadata_value(text, "Title"):
            failures.append(f"{rel}: wave doc must declare `Title:` metadata (displayed in the dashboard wave card)")
        if "## Objective" not in text:
            failures.append(f"{rel}: wave doc must declare `## Objective` section (displayed in the dashboard wave card)")
        sections = _extract_sections(text)
        watchpoints = sections.get("## Journal Watchpoints", "")
        if watchpoints and not _section_has_bullets(watchpoints):
            failures.append(f"{rel}: `## Journal Watchpoints` must include at least one bullet")

        forward_wave = _wave_requires_wave_owned_change_docs(text)
        change_records = _parse_change_records(text, rel)
        legacy_item_records = _parse_legacy_item_records(text, rel)
        work_records = change_records or legacy_item_records
        if forward_wave and legacy_item_records:
            failures.append(f"{rel}: ready or active wave records must use `Change ID` / `Change Status`, not `Item ID` / `Item Status`")
        if forward_wave and "## Changes" not in text:
            failures.append(f"{rel}: ready or active wave records must include `## Changes`")
        if not forward_wave and not change_records and not legacy_item_records:
            failures.append(f"{rel}: missing stable `Change ID` declaration")
        if forward_wave and not change_records:
            failures.append(f"{rel}: missing stable `Change ID` declaration")

        for record in work_records:
            if record.record_id in seen_item_ids:
                label = "Change ID" if record.anchor_type == "change" else "Item ID"
                failures.append(f"{rel}: duplicate {label} `{record.record_id}` across wave artifacts")
            seen_item_ids.add(record.record_id)
        for raw_line in [line for line in text.splitlines() if line.startswith("Item ID:")]:
            if not ITEM_ID_PATTERN.match(raw_line):
                item_value = _extract_backtick_value(raw_line)
                failures.append(f"{rel}: wave artifact has unstable Item ID `{item_value}`")
        for raw_line in [line for line in text.splitlines() if line.startswith("Change ID:")]:
            if not CHANGE_ID_PATTERN.match(raw_line):
                change_value = _extract_backtick_value(raw_line)
                failures.append(f"{rel}: wave artifact has unstable Change ID `{change_value}`")

        if work_records and all(record.status is None for record in work_records):
            status_label = "Change Status" if change_records else "Item Status"
            failures.append(f"{rel}: missing `{status_label}` for declared wave changes")
        for raw_line in [line for line in text.splitlines() if line.startswith("Change Status:")]:
            if not CHANGE_STATUS_PATTERN.match(raw_line):
                failures.append(f"{rel}: invalid `Change Status` declaration `{raw_line}`")
        for raw_line in [line for line in text.splitlines() if line.startswith("Previous Change Status:")]:
            if not PREVIOUS_CHANGE_STATUS_PATTERN.match(raw_line):
                failures.append(f"{rel}: invalid `Previous Change Status` declaration `{raw_line}`")
        for raw_line in [line for line in text.splitlines() if line.startswith("Item Status:")]:
            if not ITEM_STATUS_PATTERN.match(raw_line):
                failures.append(f"{rel}: invalid `Item Status` declaration `{raw_line}`")
        for raw_line in [line for line in text.splitlines() if line.startswith("Previous Item Status:")]:
            if not PREVIOUS_ITEM_STATUS_PATTERN.match(raw_line):
                failures.append(f"{rel}: invalid `Previous Item Status` declaration `{raw_line}`")
        for raw_line in [line for line in text.splitlines() if line.startswith("Depends On:")]:
            if "`" not in raw_line:
                failures.append(f"{rel}: `Depends On` must reference stable Change IDs in backticks")

        work_records_by_id = {record.record_id: record for record in work_records}
        for record in work_records:
            if record.status is None:
                status_label = "Change Status" if record.anchor_type == "change" else "Item Status"
                failures.append(f"{rel}: {record.anchor_type} `{record.record_id}` is missing `{status_label}`")
                continue
            if record.previous_status is not None:
                allowed_previous = (
                    ALLOWED_CHANGE_STATUS_TRANSITIONS if record.anchor_type == "change" else ALLOWED_ITEM_STATUS_TRANSITIONS
                ).get(record.previous_status, set())
                if record.status not in allowed_previous:
                    failures.append(
                        f"{rel}: {record.anchor_type} `{record.record_id}` has invalid status progression "
                        f"`{record.previous_status}` -> `{record.status}`"
                    )
            for dependency in record.depends_on:
                if dependency == record.record_id:
                    failures.append(f"{rel}: {record.anchor_type} `{record.record_id}` cannot depend on itself")
                    continue
                dependency_record = work_records_by_id.get(dependency)
                if dependency_record is None:
                    dependency_label = "Change ID" if record.anchor_type == "change" else "Item ID"
                    failures.append(f"{rel}: {record.anchor_type} `{record.record_id}` depends on unknown {dependency_label} `{dependency}`")
                    continue
                progressable_statuses = PROGRESSABLE_CHANGE_STATUSES if record.anchor_type == "change" else PROGRESSABLE_ITEM_STATUSES
                terminal_statuses = TERMINAL_CHANGE_STATUSES if record.anchor_type == "change" else TERMINAL_ITEM_STATUSES
                if record.status in progressable_statuses and dependency_record.status not in terminal_statuses:
                    failures.append(
                        f"{rel}: {record.anchor_type} `{record.record_id}` is `{record.status}` but dependency `{dependency}` "
                        f"is still `{dependency_record.status}`"
                    )

        non_terminal_states = {
            record.status
            for record in work_records
            if record.status
            and record.status
            not in (TERMINAL_CHANGE_STATUSES if record.anchor_type == "change" else TERMINAL_ITEM_STATUSES)
        }
        if non_terminal_states and watchpoints and not _contains_any(watchpoints, WAVE_WATCHPOINT_MARKERS):
            failures.append(
                f"{rel}: `## Journal Watchpoints` should capture follow-up, watchpoint, or blocking language for non-terminal changes"
            )
        if wave_matches and _wave_requires_wave_owned_change_docs(text):
            for change_id in sorted(set(CHANGE_ID_PATTERN.findall(text))):
                expected = path.parent / f"{change_id}.md"
                if not expected.exists():
                    failures.append(
                        f"{rel}: wave-owned change `{change_id}` must exist at "
                        f"`{relative_to_root(root, expected)}` (relocate during Prepare wave before implementation)"
                    )
                else:
                    change_text = read_text(expected)
                    change_rel = relative_to_root(root, expected)
                    if not _H1_TITLE_RE.search(change_text):
                        failures.append(f"{change_rel}: change doc must have an H1 title (`# Title text`) — used by the dashboard")
                    for section in _CHANGE_DOC_REQUIRED_SECTIONS:
                        if section not in change_text:
                            failures.append(f"{change_rel}: change doc is missing required section `{section}` — used by the dashboard")
                staging = root / "docs/plans" / f"{change_id}.md"
                if staging.is_file():
                    failures.append(
                        f"{rel}: admitted change `{change_id}` must not remain under `docs/plans/` once the wave is "
                        f"ready or active; keep the canonical copy in the wave folder only"
                    )
    return failures


def _build_wave_inventory(root: Path) -> tuple[dict[str, str], dict[str, str]]:
    wave_state, item_state = _collect_wave_state(root)
    return (
        {wave_id: record.path for wave_id, record in wave_state.items()},
        {item_id: record.path for item_id, record in item_state.items()},
    )


def check_journal_docs(root: Path) -> list[str]:
    failures: list[str] = []
    journal_root = root / "docs/agents/journals"
    for path in sorted(journal_root.rglob("*.md")):
        rel = relative_to_root(root, path)
        if path.name == "README.md":
            continue
        text = read_text(path)
        sections = _extract_sections(text)
        for section in JOURNAL_REQUIRED_SECTIONS:
            if section not in text:
                failures.append(f"{rel}: missing required section `{section}`")
        for pattern in JOURNAL_DISALLOWED_PATTERNS:
            if pattern.search(text):
                failures.append(
                    f"{rel}: journal appears to capture sensitive data, raw transcript content, or low-salience routine noise"
                )
                break
        identity = sections.get("## Operating Identity")
        if identity:
            if not _section_has_bullets(identity):
                failures.append(f"{rel}: `## Operating Identity` must include at least one bullet")
            elif not _contains_any(identity, ("role", "persona", "agent", "responsib", "perspective", "job")):
                failures.append(f"{rel}: `## Operating Identity` must describe role, persona, responsibility, or perspective")
        salience = sections.get("## Salience Triggers")
        if salience:
            if not _section_has_bullets(salience):
                failures.append(f"{rel}: `## Salience Triggers` must include at least one bullet")
            elif not _contains_any(salience, JOURNAL_SALIENCE_MARKERS):
                failures.append(
                    f"{rel}: `## Salience Triggers` must mention critical/high/medium/low salience or concrete operational triggers"
                )
        recent = sections.get("## Active Signals")
        if recent and not _section_has_bullets(recent):
            failures.append(f"{rel}: `## Active Signals` must include at least one bullet or an explicit none/deferred note")
        distillation = sections.get("## Distillation")
        if distillation and not _section_has_bullets(distillation):
            failures.append(f"{rel}: `## Distillation` must include at least one bullet")
        promotion = sections.get("## Promotion Evidence")
        if promotion:
            if not _section_has_bullets(promotion):
                failures.append(f"{rel}: `## Promotion Evidence` must include at least one bullet")
            elif "`" not in promotion:
                failures.append(f"{rel}: `## Promotion Evidence` should reference a stable artifact or identifier in backticks")
        retirement = sections.get("## Retirement And Supersession")
        if retirement:
            if not _section_has_bullets(retirement):
                failures.append(f"{rel}: `## Retirement And Supersession` must include at least one bullet")
            elif not _contains_any(retirement, ("retire", "supersed", "stale", "replace", "invalid", "none")):
                failures.append(
                    f"{rel}: `## Retirement And Supersession` must describe retirement, supersession, invalidation, or explicit none"
                )
        governance = sections.get("## Governance")
        if governance:
            if not _section_has_bullets(governance):
                failures.append(f"{rel}: `## Governance` must include at least one bullet")
            elif not _contains_any(governance, JOURNAL_GOVERNANCE_MARKERS):
                failures.append(
                    f"{rel}: `## Governance` must define allowed/disallowed memory, review, deletion, retirement, or sensitivity rules"
                )
        follow_up = sections.get("## Follow-up Signals")
        if follow_up:
            if not _section_has_bullets(follow_up):
                failures.append(f"{rel}: `## Follow-up Signals` must include at least one bullet")
            elif not _contains_any(follow_up, JOURNAL_SIGNAL_MARKERS):
                failures.append(f"{rel}: `## Follow-up Signals` must mention a watchpoint, review, escalation, or follow-up signal")
        wave_refs = WAVE_REFERENCE_PATTERN.findall(text)
    return failures


def check_persona_docs(root: Path) -> list[str]:
    failures: list[str] = []
    persona_root = root / "docs/agents/personas"
    for path in sorted(persona_root.rglob("*.md")):
        rel = relative_to_root(root, path)
        if path.name == "README.md":
            continue
        text = read_text(path)
        sections = _extract_sections(text)
        for section in PERSONA_REQUIRED_SECTIONS:
            if section not in text:
                failures.append(f"{rel}: missing required section `{section}`")
        for section in (
            "## Scope",
            "## Operating Identity",
            "## Salience Triggers",
            "## Planning Duties",
            "## Review Triggers",
            "## Escalation Conditions",
            "## Associated Journal",
        ):
            section_text = sections.get(section)
            if section_text and not _section_has_bullets(section_text):
                failures.append(f"{rel}: `{section}` must include at least one bullet")
        identity_text = sections.get("## Operating Identity", "")
        if identity_text and not _contains_any(identity_text, ("persona", "perspective", "role", "evaluate", "protect")):
            failures.append(f"{rel}: `## Operating Identity` must describe the persona perspective or role")
        salience_text = sections.get("## Salience Triggers", "")
        if salience_text and not _contains_any(salience_text, JOURNAL_SALIENCE_MARKERS):
            failures.append(f"{rel}: `## Salience Triggers` must include operational salience cues")
        journal_paths = JOURNAL_PATH_PATTERN.findall(text)
        if not journal_paths:
            failures.append(f"{rel}: persona doc must reference an associated journal path")
        for journal_path in journal_paths:
            if not (root / journal_path).exists():
                failures.append(f"{rel}: persona doc references missing journal `{journal_path}`")
        scope_text = sections.get("## Scope", "")
        if scope_text and "wave-id:" not in scope_text:
            failures.append(f"{rel}: `## Scope` should anchor the persona to a stable `wave-id`")
        planning_text = sections.get("## Planning Duties", "")
        if planning_text and not _contains_any(planning_text, ("plan", "admission", "coordinate", "sequence")):
            failures.append(f"{rel}: `## Planning Duties` must describe concrete planning or coordination responsibilities")
        if _contains_any(text, FACTOR_REVIEW_MARKERS):
            review_text = sections.get("## Review Triggers", "")
            escalation_text = sections.get("## Escalation Conditions", "")
            if not _contains_any(review_text + "\n" + escalation_text, FACTOR_REVIEW_MARKERS):
                failures.append(f"{rel}: factor-review expectations must be captured in `## Review Triggers` or `## Escalation Conditions`")
    return failures


def _check_doc_references(
    *,
    root: Path,
    doc_root: Path,
    missing_wave_message: str,
    missing_item_message: str,
    missing_change_message: str,
) -> list[str]:
    failures: list[str] = []
    wave_inventory, record_inventory = _build_wave_inventory(root)
    for path in sorted(doc_root.rglob("*.md")):
        if path.name == "README.md":
            continue
        rel = relative_to_root(root, path)
        text = read_text(path)
        for wave_id in WAVE_REFERENCE_PATTERN.findall(text):
            if wave_id not in wave_inventory:
                failures.append(missing_wave_message.format(rel=rel, wave_id=wave_id))
        for item_id in ITEM_REFERENCE_PATTERN.findall(text):
            if item_id not in record_inventory:
                failures.append(missing_item_message.format(rel=rel, item_id=item_id))
        for change_id in CHANGE_REFERENCE_PATTERN.findall(text):
            if change_id not in record_inventory:
                failures.append(missing_change_message.format(rel=rel, change_id=change_id))
    return failures


def check_cross_artifact_consistency(root: Path) -> list[str]:
    failures: list[str] = []

    workflow_path = root / "docs/workflow-config.json"
    manifest_path = root / "docs/prompts/prompt-surface-manifest.json"
    workflow_data, workflow_error = load_json(workflow_path) if workflow_path.exists() else (None, None)
    manifest_data, manifest_error = load_json(manifest_path) if manifest_path.exists() else (None, None)
    if workflow_error is None and manifest_error is None and workflow_data and manifest_data:
        prompt_generation = workflow_data.get("prompt_generation")
        workflow_source = prompt_generation.get("seed_framework_source") if isinstance(prompt_generation, dict) else None
        manifest_source = manifest_data.get("seed_framework_source")
        if workflow_source and manifest_source and workflow_source != manifest_source:
            failures.append(
                "docs/workflow-config.json: `prompt_generation.seed_framework_source` does not match "
                "docs/prompts/prompt-surface-manifest.json `seed_framework_source`"
            )
        generated_artifacts = manifest_data.get("generated_artifacts")
        if isinstance(generated_artifacts, list):
            for required in MANIFEST_REQUIRED_GENERATED_ARTIFACTS:
                if required not in generated_artifacts:
                    failures.append(
                        f"docs/prompts/prompt-surface-manifest.json: `generated_artifacts` is missing `{required}`"
                    )
        public_prompt_surface = manifest_data.get("public_prompt_surface")
        if isinstance(public_prompt_surface, list):
            seen_shortcuts: set[str] = set()
            for entry in public_prompt_surface:
                if not isinstance(entry, dict):
                    failures.append(
                        "docs/prompts/prompt-surface-manifest.json: `public_prompt_surface` entries must be objects"
                    )
                    continue
                doc = entry.get("doc")
                shortcut = entry.get("shortcut")
                if not doc or not isinstance(doc, str):
                    failures.append(
                        "docs/prompts/prompt-surface-manifest.json: `public_prompt_surface` entries must include `doc`"
                    )
                elif not (root / doc).exists():
                    failures.append(
                        f"docs/prompts/prompt-surface-manifest.json: registered prompt doc `{doc}` does not exist"
                    )
                if not shortcut or not isinstance(shortcut, str):
                    failures.append(
                        "docs/prompts/prompt-surface-manifest.json: `public_prompt_surface` entries must include `shortcut`"
                    )
                elif shortcut in seen_shortcuts:
                    failures.append(
                        f"docs/prompts/prompt-surface-manifest.json: duplicate public shortcut `{shortcut}`"
                    )
                else:
                    seen_shortcuts.add(shortcut)

    wave_inventory, record_inventory = _collect_wave_state(root)
    journal_root = root / "docs/agents/journals"
    journal_wave_refs: set[str] = set()
    for path in sorted(journal_root.rglob("*.md")):
        if path.name == "README.md":
            continue
        text = read_text(path)
        journal_wave_refs.update(WAVE_REFERENCE_PATTERN.findall(text))
    for wave_id, record in wave_inventory.items():
        active_records = [
            record_inventory[record_id]
            for record_id in record.record_ids
            if record_id in record_inventory
            and record_inventory[record_id].status
            not in (TERMINAL_CHANGE_STATUSES if record_inventory[record_id].anchor_type == "change" else TERMINAL_ITEM_STATUSES)
        ]
        if active_records and wave_id not in journal_wave_refs:
            failures.append(
                f"{record.path}: active wave `{wave_id}` must be referenced by at least one journal artifact"
                f" — add exactly this line to a file under docs/agents/journals/:"
                f" wave-id: `{wave_id}`"
                f" (the wave-id key must be alone on its line with no trailing content after the closing backtick)"
            )

    failures.extend(
        _check_doc_references(
            root=root,
            doc_root=root / "docs/agents/journals",
            missing_wave_message="{rel}: journal doc references unknown `wave-id` `{wave_id}`",
            missing_item_message="{rel}: journal doc references unknown Item ID `{item_id}`",
            missing_change_message="{rel}: journal doc references unknown Change ID `{change_id}`",
        )
    )
    failures.extend(
        _check_doc_references(
            root=root,
            doc_root=root / "docs/agents/personas",
            missing_wave_message="{rel}: persona doc references unknown `wave-id` `{wave_id}`",
            missing_item_message="{rel}: persona doc references unknown Item ID `{item_id}`",
            missing_change_message="{rel}: persona doc references unknown Change ID `{change_id}`",
        )
    )
    return failures


def check_migration_edges(root: Path) -> list[str]:
    warnings: list[str] = []
    audit_roots = [
        root / "docs/prompts",
        root / "docs/waves",
        root / "docs/agents/journals",
        root / "docs/agents/personas",
    ]
    for doc_root in audit_roots:
        if not doc_root.exists():
            continue
        for path in sorted(doc_root.rglob("*.md")):
            if _is_archived_legacy_wave_doc(root, path):
                continue
            text = read_text(path)
            rel = relative_to_root(root, path)
            for marker in (*LEGACY_MARKERS, *HYBRID_LEGACY_MARKERS):
                if marker in text:
                    warnings.append(
                        f"migration-edge drift detected; stale legacy marker remains in {rel}: {marker}"
                    )

    for wrapper_name in ("docs-lint", "docs-gardener"):
        wrapper_path = root / wrapper_name
        if not wrapper_path.exists() or not wrapper_path.is_file():
            continue
        wrapper_text = read_text(wrapper_path)
        if "agent-workflows/legacy-framework/scripts/" in wrapper_text:
            warnings.append(
                f"migration-edge drift detected; stale wrapper target remains in {wrapper_name}: agent-workflows/legacy-framework/scripts/"
            )

    return warnings


def _is_archived_legacy_wave_doc(root: Path, path: Path) -> bool:
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        return False
    if len(relative_parts) < 4:
        return False
    if relative_parts[0] != "docs" or relative_parts[1] != "waves":
        return False
    wave_folder = relative_parts[2]
    if not wave_folder.startswith("00000 "):
        return False
    return path.name != "wave.md"
