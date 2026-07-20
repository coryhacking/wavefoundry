from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterable

from review_evidence import (
    REVIEW_STATUS_MARKER_BEGIN,
    adopted_protocol_state,
    canonicalize_finding_synthesis_markers,
    parse_review_evidence_source,
    render_review_evidence_projection,
    render_review_status_projection,
    required_review_status_keys,
    validate_adopted_protocol_state,
    validate_external_review_evidence,
)
from context_efficiency import checkpoint_validation_errors

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
    MEMORY_CONFIDENCE_PATTERN,
    MEMORY_CREATED_PATTERN,
    MEMORY_DISALLOWED_PATTERNS,
    MEMORY_ID_PATTERN,
    MEMORY_KIND_PATTERN,
    MEMORY_KINDS,
    MEMORY_RECORD_DIR,
    MEMORY_REQUIRED_SECTIONS,
    MEMORY_STATUSES,
    MEMORY_SUPERSEDED_BY_PATTERN,
    MEMORY_UPDATED_PATTERN,
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
_ROLE_RE = re.compile(r"^Role:\s+(.+)$", re.MULTILINE)
_CATEGORY_RE = re.compile(r"^Category:\s+(.+)$", re.MULTILINE)
_AGENT_ROLE_EXEMPT_NAMES = {"README.md", "session-handoff.md", "platform-mapping.md"}
_AGENT_ROLE_REQUIRED_PATHS = frozenset(
    {
        "docs/agents/architecture-reviewer.md",
        "docs/agents/code-reviewer.md",
        "docs/agents/specialists/wave-council.md",
        "docs/agents/docs-contract-reviewer.md",
        # NOTE: factor canonical docs (factor-<nn>-<name>.md) are NOT listed here.
        # Their required-existence is derived dynamically from `docs/workflow-config.json`
        # `factor_review_policy.applicable_factors` (the operational active-lane set —
        # each lane requires its canonical source) by `check_factor_surface` below. The
        # static-list approach was wrong because it demanded a fixed `03/05/12/13` set
        # regardless of a repo's actual lanes; keying off `repo-profile.json`
        # `factor_review` (1p79x) was also wrong because that is the broader applicability
        # *assessment*, not the operational lane set, so it false-blocked retired-lane
        # repos and over-required docs for assessment-only factors. Wave 1p7ac.
        "docs/agents/guru.md",
        "docs/agents/implementer.md",
        "docs/agents/performance-reviewer.md",
        "docs/agents/planner.md",
        "docs/agents/qa-reviewer.md",
        "docs/agents/release-reviewer.md",
        "docs/agents/security-reviewer.md",
        "docs/agents/wave-coordinator.md",
        "docs/agents/specialists/environment-auditor.md",
        "docs/agents/specialists/operating-surface-gardener.md",
        "docs/agents/specialists/senior-engineering-challenger.md",
    }
)
_REVIEW_SUFFIXES = ("-reviewer", "-auditor", "-tester")
_REVIEW_STEMS = frozenset({"reality-checker"})
_COORDINATE_STEMS = frozenset({"planner", "wave-coordinator", "wave-council"})
_COORDINATE_SUFFIXES = ("-coordinator", "-moderator")
_BUILD_SUFFIXES = ("-engineer", "-developer", "-builder", "-automator", "-programmer", "-coder")
_BUILD_STEMS = frozenset({"implementer"})
_CATEGORY_EXEMPT_NAMES = {"README.md", "session-handoff.md", "platform-mapping.md"}

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


# Wave 1p9bm (1p9bn): a line that is FORBIDDING content (a disallowed-list / governance rule) legitimately
# names the thing it forbids — e.g. "- Do not include raw transcript content or secrets." A journal's own
# Governance section must be able to say what it disallows without the disallowed-pattern check firing on
# it. These are explicit forbidding phrases (not the bare word "not", which is too broad); a real pasted
# transcript or a real secret value is never phrased this way, so true positives are preserved.
_DISALLOWED_NEGATION_MARKERS = (
    "do not", "don't", "never", "must not", "should not", "no raw", "no full",
    "avoid", "exclude", "forbid", "disallow", "prohibit", "rather than", "instead of",
)


def _line_forbids_content(line: str) -> bool:
    """True when a line is describing content it FORBIDS (so a disallowed-pattern match on it is the rule,
    not a violation)."""
    return _contains_any(line, _DISALLOWED_NEGATION_MARKERS)


_AC_PRIORITY_VALUES = {"required", "important", "nice-to-have", "not-this-scope"}
# Wave 1p31b (1p32k): include `~` as a valid checkbox mark for intentionally-deferred ACs and tasks.
# A `[~]` AC is one that was reconsidered, removed by operator direction during implementation,
# or genuinely narrowed by scope-discovery — it is neither satisfied nor still in-scope-but-unmet.
# See seed `170-plan-feature.prompt.md` for the canonical definition.
_AC_LINE_RE = re.compile(r"^\s*-\s+(?:(?:\[(?P<mark>[ xX~])\])\s+)?(?P<text>.+?)\s*$", re.MULTILINE)
_AC_ID_RE = re.compile(r"(AC-[\w\-]+)")


def _markdown_table_rows(section_text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in section_text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or line.count("|") < 2:
            continue
        if set(line.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
    return rows


def _normalize_ac_priority(raw_priority: str) -> str:
    normalized = raw_priority.strip().lower().replace(" ", "-")
    return normalized if normalized in _AC_PRIORITY_VALUES else "unknown"


def _parse_ac_items_for_lint(ac_section: str, priority_section: str) -> tuple[list[str], list[str]]:
    """Return AC priorities in bullet order plus the raw priority table rows."""
    priority_rows: list[str] = []
    priority_map: dict[str, str] = {}
    for row in _markdown_table_rows(priority_section)[1:]:
        if len(row) < 2:
            continue
        ac_id = row[0].strip()
        priority = _normalize_ac_priority(row[1])
        priority_rows.append(priority)
        if ac_id:
            priority_map[ac_id] = priority

    ac_priorities: list[str] = []
    for index, match in enumerate(_AC_LINE_RE.finditer(ac_section)):
        text = match.group("text").strip()
        id_match = _AC_ID_RE.search(text)
        ac_id = id_match.group(1) if id_match else ""
        priority = priority_map.get(ac_id)
        if priority is None and index < len(priority_rows):
            priority = priority_rows[index]
        if priority is None:
            priority = "unknown"
        ac_priorities.append(priority)
    return ac_priorities, priority_rows


def _check_ac_priority_alignment(text: str, rel: str) -> list[str]:
    failures: list[str] = []
    sections = _extract_sections(text)
    ac_section = sections.get("## Acceptance Criteria", "")
    priority_section = sections.get("## AC Priority", "")
    if not ac_section or not priority_section:
        return failures

    ac_priorities, priority_rows = _parse_ac_items_for_lint(ac_section, priority_section)
    if len(ac_priorities) != len(priority_rows):
        failures.append(
            f"{rel}: AC Priority table must have one row per Acceptance Criteria bullet "
            f"(found {len(ac_priorities)} AC bullets and {len(priority_rows)} AC priority rows); "
            "unknown ACs are not allowed"
        )

    unknown_count = sum(1 for priority in ac_priorities if priority == "unknown")
    if unknown_count:
        failures.append(
            f"{rel}: AC Priority table left {unknown_count} Acceptance Criteria bullet(s) uncategorized; "
            "unknown ACs are not allowed"
        )

    return failures


_PLAIN_AC_LINE_RE = re.compile(r"^\s*-\s+AC-[\w\-]+:", re.MULTILINE)
# Wave 1p31b (1p32k): `~` accepted alongside ` ` / `x` to recognize intentionally-deferred items.
_CHECKBOX_AC_LINE_RE = re.compile(r"^\s*-\s+\[[ xX~]\]\s+", re.MULTILINE)
_CHECKBOX_TASK_LINE_RE = re.compile(r"^\s*-\s+\[[ xX~]\]\s+", re.MULTILINE)
_TILDE_AC_LINE_RE = re.compile(r"^\s*-\s+\[~\]\s+(?P<ac_id>AC-[\w\-]+):\s*(?P<rest>.*)$", re.MULTILINE)
# A "non-empty inline rationale" is at least 40 chars of prose after the AC label OR
# a markdown italic segment (`*...*`) anywhere in the line. Both signal a real explanation
# rather than a silent marker.
_INLINE_ITALIC_RE = re.compile(r"\*[^*\n]{4,}\*")
_INLINE_NOTE_MIN_CHARS = 40


def _check_checkbox_ac_syntax(text: str, rel: str) -> list[str]:
    """Fail when an Acceptance Criteria section exists with items but none use checkbox syntax."""
    sections = _extract_sections(text)
    ac_section = sections.get("## Acceptance Criteria", "")
    if not ac_section:
        return []
    has_items = bool(_AC_LINE_RE.search(ac_section))
    if not has_items:
        return []
    has_any_checkbox = bool(_CHECKBOX_AC_LINE_RE.search(ac_section))
    if has_any_checkbox:
        return []
    has_plain_bullets = bool(_PLAIN_AC_LINE_RE.search(ac_section))
    if not has_plain_bullets:
        return []
    return [
        f"{rel}: `## Acceptance Criteria` uses plain bullet format; "
        "use checkbox syntax (`- [ ] AC-1: ...` / `- [x] AC-1: ...` / `- [~] AC-1: ...` for intentionally-deferred) "
        "so AC completion can be tracked during implementation"
    ]


def _check_checkbox_task_syntax(text: str, rel: str) -> list[str]:
    """Fail when a Tasks section contains bullet items without checkbox syntax."""
    sections = _extract_sections(text)
    tasks_section = sections.get("## Tasks", "")
    if not tasks_section:
        return []
    task_lines = [line for line in tasks_section.splitlines() if line.lstrip().startswith("- ")]
    if not task_lines:
        return []
    if all(_CHECKBOX_TASK_LINE_RE.match(line) for line in task_lines):
        return []
    return [
        f"{rel}: `## Tasks` uses plain bullet format; "
        "use checkbox syntax (`- [ ] step` / `- [x] step` / `- [~] step` for intentionally-deferred) "
        "so task completion can be tracked during implementation"
    ]


def _check_tilde_required_ac_has_inline_note(text: str, rel: str) -> list[str]:
    """Wave 1p31b (1p32k): a `[~]` AC at required priority must carry an inline status note.

    The convention's defense against silent technical debt is mechanical: `[~]` without
    a recorded rationale defeats the discoverability promise. Required-priority ACs
    carry contract weight, so the inline note is enforced; important / nice-to-have ACs
    can use `[~]` more loosely. Tasks never require the inline note (per Req-12).

    A line satisfies the inline-note rule if it contains:
      - a markdown italic segment (`*...*` with at least 4 chars of content), OR
      - at least ``_INLINE_NOTE_MIN_CHARS`` characters of prose after the AC label.
    """
    sections = _extract_sections(text)
    ac_section = sections.get("## Acceptance Criteria", "")
    priority_section = sections.get("## AC Priority", "")
    if not ac_section:
        return []

    # Build AC-id -> priority map from the priority table (priority by AC-id; positional fallback).
    priority_map: dict[str, str] = {}
    priority_rows: list[str] = []
    for row in _markdown_table_rows(priority_section)[1:]:
        if len(row) < 2:
            continue
        ac_id_raw = row[0].strip()
        priority = _normalize_ac_priority(row[1])
        priority_rows.append(priority)
        if ac_id_raw:
            id_match = _AC_ID_RE.search(ac_id_raw)
            if id_match:
                priority_map[id_match.group(1)] = priority

    # Walk AC bullets in order; for each `[~]` AC at required priority, check for inline note.
    failures: list[str] = []
    ac_index = 0
    for match in _AC_LINE_RE.finditer(ac_section):
        text_part = match.group("text").strip()
        id_match = _AC_ID_RE.search(text_part)
        ac_id = id_match.group(1) if id_match else ""
        # Resolve priority by id first, then positional fallback.
        priority = priority_map.get(ac_id)
        if priority is None and ac_index < len(priority_rows):
            priority = priority_rows[ac_index]
        if priority is None:
            priority = "unknown"
        ac_index += 1

        # Only enforce on required-priority ACs.
        if priority != "required":
            continue
        # Only check ACs that use the tilde marker.
        if match.group("mark") != "~":
            continue

        # Has an inline italic segment?
        if _INLINE_ITALIC_RE.search(text_part):
            continue
        # Or sufficient prose length after the AC label?
        rationale = ""
        ac_label_match = re.match(r"AC-[\w\-]+:\s*(.*)$", text_part)
        if ac_label_match:
            rationale = ac_label_match.group(1).strip()
        if len(rationale) >= _INLINE_NOTE_MIN_CHARS:
            continue

        failures.append(
            f"{rel}: `[~]` required AC `{ac_id or '<unidentified>'}` lacks an inline status note. "
            "Wrap the rationale in italics (e.g. *Operator-directed removal during implementation, "
            "see Decision Log entry on <date>*) or include at least "
            f"{_INLINE_NOTE_MIN_CHARS} characters of prose explaining the deferral. "
            "See seed `170-plan-feature.prompt.md` for the convention."
        )
    return failures


def _metadata_value(text: str, key: str) -> str | None:
    prefix = f"{key}:"
    for raw_line in text.splitlines():
        if raw_line.startswith(prefix):
            return raw_line.split(":", 1)[1].strip()
    return None


def _check_agent_role_metadata(root: Path, only: set[Path] | None = None, skip: set[Path] | None = None) -> list[str]:
    """``only`` (wave 1p9c1): when provided, restrict to those paths for the incremental lint path;
    when None the behavior is unchanged (whole-tree). ``skip`` (wave 1p9cj): exclude these paths
    (oversized docs skipped by the file-size guard)."""
    failures: list[str] = []
    agents_root = root / "docs" / "agents"
    if not agents_root.is_dir():
        return failures
    seen: set[Path] = set()
    for rel in sorted(_AGENT_ROLE_REQUIRED_PATHS):
        path = root / rel
        if not path.is_file():
            continue
        if only is not None and path not in only:
            continue
        if skip is not None and path in skip:
            continue
        rel = relative_to_root(root, path)
        if path.name in _AGENT_ROLE_EXEMPT_NAMES:
            continue
        text = read_text(path)
        role_match = _ROLE_RE.search(text)
        if not role_match:
            failures.append(f"{rel}: missing required `Role:` metadata")
            seen.add(path)
            continue
        role = role_match.group(1).strip()
        if role != path.stem:
            failures.append(f"{rel}: `Role:` must match filename slug `{path.stem}`")
        seen.add(path)
    for path in sorted(agents_root.rglob("*.md")):
        if path in seen:
            continue
        if path.name in _AGENT_ROLE_EXEMPT_NAMES or "journals" in path.parts or "memory" in path.parts:
            continue
        if only is not None and path not in only:
            continue
        if skip is not None and path in skip:
            continue
        rel = relative_to_root(root, path)
        text = read_text(path)
        role_match = _ROLE_RE.search(text)
        if not role_match:
            failures.append(
                f"{rel}: missing required `Role:` metadata "
                "(the dashboard classifies agents by this field; missing field = invisible agent)"
            )
            continue
        role = role_match.group(1).strip()
        if role != path.stem:
            failures.append(f"{rel}: `Role:` must match filename slug `{path.stem}`")
    return failures


def _expected_agent_category(path: Path) -> str | None:
    if path.name in _CATEGORY_EXEMPT_NAMES or "journals" in path.parts or "memory" in path.parts:
        return None
    if path.stem.startswith("factor-") or "factor" in path.parts:
        return "factor"
    if "personas" in path.parts:
        return "persona"
    if "specialists" in path.parts:
        return "specialist"
    if path.stem in _COORDINATE_STEMS or any(path.stem.endswith(s) for s in _COORDINATE_SUFFIXES):
        return "coordinate"
    if path.stem in _REVIEW_STEMS or any(path.stem.endswith(s) for s in _REVIEW_SUFFIXES):
        return "review"
    if path.stem in _BUILD_STEMS or any(path.stem.endswith(s) for s in _BUILD_SUFFIXES):
        return "build"
    return "specialist"


def _check_agent_category_metadata(root: Path, only: set[Path] | None = None, skip: set[Path] | None = None) -> list[str]:
    """``only`` (wave 1p9c1): when provided, restrict to those paths for the incremental lint path;
    when None the behavior is unchanged (whole-tree). ``skip`` (wave 1p9cj): exclude these paths
    (oversized docs skipped by the file-size guard)."""
    failures: list[str] = []
    agents_root = root / "docs" / "agents"
    if not agents_root.is_dir():
        return failures
    for path in sorted(agents_root.rglob("*.md")):
        if path.name in _CATEGORY_EXEMPT_NAMES or "journals" in path.parts or "memory" in path.parts:
            continue
        if only is not None and path not in only:
            continue
        if skip is not None and path in skip:
            continue
        rel = relative_to_root(root, path)
        text = read_text(path)
        category_match = _CATEGORY_RE.search(text)
        if not category_match:
            failures.append(f"{rel}: missing required `Category:` metadata")
            continue
        category = category_match.group(1).strip()
        expected = _expected_agent_category(path)
        if expected is not None and category != expected:
            failures.append(f"{rel}: `Category:` must be `{expected}`")
    return failures


_FACTOR_ID_RE = re.compile(r"^\d{2}$")
_FACTOR_CANONICAL_RE = re.compile(r"^factor-(\d{2})-[a-z0-9][a-z0-9\-]*$")
# A YAML frontmatter block is a `---` fence on the very first line, a body, and a
# closing `---` fence. A factor wrapper missing this block cannot load as a
# native subagent (Claude Code requires the frontmatter to register the agent).
_FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|$)", re.DOTALL)
_FACTOR_RECOVERY = (
    "regenerate the canonical+wrapper pair via `seed-050` task 5 "
    "(or an `Upgrade Wavefoundry` reconciliation) — do not hand-relocate or retire the wrapper, "
    "and keep the canonical home flat at `docs/agents/` (never `docs/agents/factors/`)"
)


def _factor_canonical_for(root: Path, factor_id: str) -> Path | None:
    """Return the canonical `docs/agents/factor-<nn>-*.md` for a factor number, if one exists.

    The kebab-case name segment is not 1:1 with the repo-profile `name` field
    (e.g. "Build / release / run" -> `build-release-run`), so the canonical doc
    is located by its zero-padded two-digit number prefix.
    """
    agents_root = root / "docs" / "agents"
    if not agents_root.is_dir():
        return None
    matches = sorted(agents_root.glob(f"factor-{factor_id}-*.md"))
    return matches[0] if matches else None


def check_factor_surface(root: Path) -> tuple[list[str], list[str]]:
    """Wave 1p79x / 1p7ac — the declared-but-missing gate for the factor-review surface.

    Wave 1p7ac re-keys the canonical-doc requirement off the **operational active-lane
    set** — `docs/workflow-config.json` `factor_review_policy.applicable_factors` — NOT
    the broader `docs/repo-profile.json` `factor_review` applicability *assessment* that
    `1p79x` keyed off. The canonical factor docs are the review-LANE artifacts, so they
    must be required for the lanes a repo actually runs, not for every factor merely
    assessed relevant. `repo-profile` answers "is this factor relevant?";
    `workflow-config.applicable_factors` answers "do we run a lane for it?" — only the
    latter implies a canonical doc.

    Returns ``(failures, warnings)``:

      ERRORS (failures, block the gate):
      (a) each factor in `applicable_factors` must have its canonical
          `docs/agents/factor-<nn>-<name>.md` with `Role: factor-<nn>-<name>` +
          `Category: factor` headers — a missing/malformed canonical for an ACTIVE
          lane is the real defect;
      (b) a `.claude/agents/factor-*.md` wrapper with NO matching canonical source
          is an orphan wrapper (wrappers are optional rendered copies, never the
          source of truth), regardless of the lane set;
      (c) a factor wrapper present but missing YAML frontmatter cannot load as a
          native subagent, regardless of the lane set.

      WARNINGS (non-blocking, surfaced for operator reconciliation):
      (d) a factor marked `applicable` in `repo-profile.json` `factor_review` but NOT
          present in `applicable_factors` — assessed-relevant with no active review
          lane. Visible but unblocked (no forced doc over-generation).

    An absent/empty `applicable_factors` (retired lane) requires NO canonical docs even
    when `repo-profile` still marks factors `applicable` (those surface as (d) warnings).
    """
    failures: list[str] = []
    warnings: list[str] = []

    # The operational active-lane set drives the canonical-doc requirement.
    active_factors: set[str] = set()
    config_path = root / "docs" / "workflow-config.json"
    if config_path.is_file():
        config, cfg_err = load_json(config_path)
        if cfg_err is None and isinstance(config, dict):
            policy = config.get("factor_review_policy")
            if isinstance(policy, dict):
                raw_active = policy.get("applicable_factors")
                if isinstance(raw_active, list):
                    active_factors = {
                        str(fid) for fid in raw_active if _FACTOR_ID_RE.match(str(fid))
                    }

    # (a) Each active-lane factor must have a canonical doc with the factor headers.
    for factor_id in sorted(active_factors):
        canonical = _factor_canonical_for(root, factor_id)
        if canonical is None:
            failures.append(
                f"docs/agents/: factor `{factor_id}` is an active review lane in "
                f"docs/workflow-config.json `factor_review_policy.applicable_factors` but "
                f"has no canonical `docs/agents/factor-{factor_id}-<name>.md` — "
                f"{_FACTOR_RECOVERY}"
            )
            continue
        rel = relative_to_root(root, canonical)
        text = read_text(canonical)
        role_match = _ROLE_RE.search(text)
        if not role_match:
            failures.append(
                f"{rel}: active-lane factor `{factor_id}` canonical doc is missing the "
                f"`Role: {canonical.stem}` header — {_FACTOR_RECOVERY}"
            )
        elif role_match.group(1).strip() != canonical.stem:
            failures.append(
                f"{rel}: factor canonical `Role:` must match filename slug `{canonical.stem}`"
            )
        category_match = _CATEGORY_RE.search(text)
        if not category_match:
            failures.append(
                f"{rel}: active-lane factor `{factor_id}` canonical doc is missing the "
                f"`Category: factor` header — {_FACTOR_RECOVERY}"
            )
        elif category_match.group(1).strip() != "factor":
            failures.append(f"{rel}: factor canonical `Category:` must be `factor`")

    # (d) Assessment-vs-lane drift WARNING (non-blocking): a factor assessed
    # `applicable` in repo-profile that has no active review lane. Surfaces the gap
    # for operator reconciliation without forcing doc over-generation or blocking.
    #
    # Wave 1p9bm (1p9bp): when the lane set is ENTIRELY empty (a fresh install that
    # never seeded `applicable_factors`) and several factors are applicable, emit ONE
    # consolidated advisory with a single next step instead of N near-identical per-
    # factor warnings — the field report hit ~10 of these on every audit. When the
    # lane set is non-empty (genuine partial drift on specific factors), keep the
    # precise per-factor warnings so the operator sees exactly which factor drifted.
    profile_path = root / "docs" / "repo-profile.json"
    if profile_path.is_file():
        data, err = load_json(profile_path)
        if err is None and isinstance(data, dict):
            factor_review = data.get("factor_review")
            if isinstance(factor_review, dict):
                inactive_applicable: list[str] = []
                for factor_id, entry in sorted(factor_review.items()):
                    if not _FACTOR_ID_RE.match(str(factor_id)):
                        continue
                    if not isinstance(entry, dict):
                        continue
                    status = str(entry.get("status", "")).strip().casefold()
                    if status != "applicable":
                        continue
                    if str(factor_id) in active_factors:
                        continue
                    inactive_applicable.append(str(factor_id))
                if not active_factors and len(inactive_applicable) >= 2:
                    factor_list = ", ".join(f"`{fid}`" for fid in inactive_applicable)
                    warnings.append(
                        f"docs/workflow-config.json: `factor_review_policy.applicable_factors` "
                        f"is empty while docs/repo-profile.json marks {len(inactive_applicable)} "
                        f"factors applicable ({factor_list}) — no factor-review lanes are active. "
                        f"Next step: add the factor IDs you want to run to `applicable_factors` "
                        f"in docs/workflow-config.json (each active lane gets a generated "
                        f"`docs/agents/factor-<nn>-<name>.md`; re-run the agent-entry-surface "
                        f"generation, e.g. via `Upgrade Wavefoundry`), or leave it empty "
                        f"deliberately (and align those assessments to `partial`) if this project "
                        f"runs no factor-review lanes. No canonical docs are required while the "
                        f"lane set is empty."
                    )
                else:
                    for factor_id in inactive_applicable:
                        warnings.append(
                            f"docs/repo-profile.json: factor `{factor_id}` is marked "
                            f"`applicable` (assessment) but is not in docs/workflow-config.json "
                            f"`factor_review_policy.applicable_factors` (no active review lane) — "
                            f"reconcile: add it to `applicable_factors` to run a lane (which "
                            f"requires its canonical doc), or align the assessment to `partial` "
                            f"if it is not an active lane. No canonical doc is required while it "
                            f"is not an active lane."
                        )

    # (b)/(c) Validate any `.claude/agents/factor-*.md` wrappers: orphan + frontmatter.
    # These run regardless of the lane set — a malformed wrapper is always a defect.
    claude_agents = root / ".claude" / "agents"
    if claude_agents.is_dir():
        for wrapper in sorted(claude_agents.glob("factor-*.md")):
            id_match = _FACTOR_CANONICAL_RE.match(wrapper.stem)
            wrapper_rel = relative_to_root(root, wrapper)
            factor_id = id_match.group(1) if id_match else None
            canonical = _factor_canonical_for(root, factor_id) if factor_id else None
            if canonical is None:
                failures.append(
                    f"{wrapper_rel}: factor wrapper has no matching canonical source "
                    f"`docs/agents/{wrapper.stem}.md` (orphan wrapper) — {_FACTOR_RECOVERY}"
                )
            wrapper_text = read_text(wrapper)
            if not _FRONTMATTER_RE.match(wrapper_text):
                failures.append(
                    f"{wrapper_rel}: factor wrapper is missing YAML frontmatter "
                    f"(no leading `---` fenced block) so it cannot load as a native subagent — "
                    f"{_FACTOR_RECOVERY}"
                )
    return failures, warnings


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


def check_plan_filenames(root: Path, only: set[Path] | None = None, skip: set[Path] | None = None) -> list[str]:
    """Enforce that every `docs/plans/*.md` basename matches its `Change ID` (or `Wave:` for
    wave-level overview plans). Prevents slug-only plan filenames from slipping in during
    staging before wave readiness would normally fire the staging-vs-wave check.

    ``only`` (wave 1p9c1): when provided, restrict the per-file checks to those paths — used by
    the incremental (post-edit) lint path. When None the behavior is unchanged (whole-tree).
    ``skip`` (wave 1p9cj): exclude these paths (oversized docs skipped by the file-size guard)."""
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
        if only is not None and path not in only:
            continue
        if skip is not None and path in skip:
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


def check_wave_docs(root: Path, only: set[Path] | None = None, skip: set[Path] | None = None) -> list[str]:
    """``only`` (wave 1p9c1): when provided, restrict the per-file section/status checks to those
    paths for the incremental lint path. Note the cross-doc duplicate wave-id/item-id detection is
    inherently corpus-wide and only meaningful in the unscoped (full) run — the incremental path
    relies on the full gate at wf_validate_docs/close for that. When None, behavior is unchanged.
    ``skip`` (wave 1p9cj): exclude these paths (oversized docs skipped by the file-size guard)."""
    failures: list[str] = []
    wave_root = root / "docs/waves"
    seen_wave_ids: dict[str, str] = {}
    seen_item_ids: set[str] = set()
    for path in sorted(wave_root.rglob("*.md")):
        rel = relative_to_root(root, path)
        if path.name == "README.md":
            continue
        if only is not None and path not in only:
            continue
        if skip is not None and path in skip:
            continue
        text = read_text(path)
        is_wave_record = path.name == "wave.md"
        wave_matches: list[str] = []
        watchpoints = ""

        if is_wave_record:
            failures.extend(
                f"{rel}: Context Efficiency checkpoint: {error}"
                for error in checkpoint_validation_errors(text)
            )
            source, _source_errors = parse_review_evidence_source(text)
            adopted, _adoption_error = adopted_protocol_state(root, path.parent.name)
            inline_marker = re.search(r"(?mi)^review-evidence-protocol\s*:", text) is not None
            if source is not None or adopted is not None or _source_errors or _adoption_error or inline_marker:
                review_evidence = validate_external_review_evidence(path)
                failures.extend(
                    f"{rel}: review evidence: {error}" for error in review_evidence.errors
                )
                failures.extend(
                    f"{rel}: review evidence: {error}"
                    for error in validate_adopted_protocol_state(root, path.parent.name, path)
                )
                if review_evidence.ok:
                    try:
                        expected_projection = render_review_evidence_projection(
                            text, review_evidence.records
                        )
                        expected_projection = render_review_status_projection(
                            expected_projection,
                            review_evidence.records,
                            required_review_status_keys(
                                root, expected_projection, review_evidence.records
                            ),
                        )
                    except ValueError as exc:
                        failures.append(f"{rel}: review evidence projection: {exc}")
                    else:
                        if expected_projection != canonicalize_finding_synthesis_markers(text):
                            failures.append(
                                f"{rel}: review evidence projection is stale; regenerate it from sibling events.jsonl"
                            )
            # Wave record checks: wave-id, required sections, Title, Objective, Watchpoints, Changes
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

        forward_wave = _wave_requires_wave_owned_change_docs(text) if is_wave_record else False
        change_records = _parse_change_records(text, rel)
        legacy_item_records = _parse_legacy_item_records(text, rel)
        work_records = change_records or legacy_item_records

        if is_wave_record:
            if forward_wave and legacy_item_records:
                failures.append(f"{rel}: ready or active wave records must use `Change ID` / `Change Status`, not `Item ID` / `Item Status`")
            if forward_wave and "## Changes" not in text:
                failures.append(f"{rel}: ready or active wave records must include `## Changes`")
            # Wave 1p3dk / 1p3do: a freshly-created `planned` wave has no
            # admitted changes yet. Defer the Change-ID requirement when both
            # (a) Status: planned AND (b) ## Changes section exists but is
            # empty of records. The deferral disables the moment status moves
            # past planned OR the first change is admitted — full enforcement
            # resumes.
            wave_status = (_metadata_value(text, "Status") or "").casefold().strip()
            empty_changes_planned_wave = (
                wave_status == "planned"
                and "## Changes" in text
                and not change_records
                and not legacy_item_records
            )
            if not forward_wave and not change_records and not legacy_item_records:
                if not empty_changes_planned_wave:
                    failures.append(f"{rel}: missing stable `Change ID` declaration")
            if forward_wave and not change_records:
                if not empty_changes_planned_wave:
                    failures.append(f"{rel}: missing stable `Change ID` declaration")

        if is_wave_record:
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
                    failures.extend(_check_ac_priority_alignment(change_text, change_rel))
                    failures.extend(_check_checkbox_ac_syntax(change_text, change_rel))
                    failures.extend(_check_checkbox_task_syntax(change_text, change_rel))
                    failures.extend(_check_tilde_required_ac_has_inline_note(change_text, change_rel))
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


def check_memory_docs(root: Path, only: set[Path] | None = None, skip: set[Path] | None = None) -> list[str]:
    """Agent memory records (wave 1ro44 / 1p8gy AC-1): schema + forbidden content.

    The lint contract is the schema contract — a record failing these checks
    must never surface as an advisory. Same ``only``/``skip`` semantics as
    ``check_journal_docs`` (incremental path + oversized-file guard).
    """
    failures: list[str] = []
    memory_root = root / MEMORY_RECORD_DIR
    status_line = re.compile(r"^Status:\s+(\S+)\s*$", re.MULTILINE)
    source_event_line = re.compile(r"^Source event:\s*`([^`\r\n]+)`\s*$", re.MULTILINE)
    validation_line = re.compile(
        r"^Validation:\s*(pending|promote|retain|reject|rewrite)\s*$", re.MULTILINE
    )
    for path in sorted(memory_root.rglob("*.md")):
        rel = relative_to_root(root, path)
        if path.name == "README.md":
            continue
        if only is not None and path not in only:
            continue
        if skip is not None and path in skip:
            continue
        text = read_text(path)
        mem_id = MEMORY_ID_PATTERN.search(text)
        if not mem_id:
            failures.append(f"{rel}: missing backticked `Memory ID:` line")
        elif mem_id.group(1) != path.stem:
            failures.append(
                f"{rel}: `Memory ID` {mem_id.group(1)!r} must match the filename stem {path.stem!r}"
            )
        kind = MEMORY_KIND_PATTERN.search(text)
        if not kind:
            failures.append(f"{rel}: missing backticked `Kind:` line")
        elif kind.group(1) not in MEMORY_KINDS:
            failures.append(
                f"{rel}: unknown memory kind {kind.group(1)!r}; allowed: {', '.join(MEMORY_KINDS)}"
            )
        status = status_line.search(text)
        if not status:
            # Delivery-review finding: a missing Status must FAIL lint — the
            # runtime parser no longer defaults it, and a status-less record
            # must never pass the schema gate and surface as an advisory.
            failures.append(
                f"{rel}: missing `Status:` line (one of {', '.join(MEMORY_STATUSES)})"
            )
        elif status.group(1) not in MEMORY_STATUSES:
            failures.append(
                f"{rel}: memory `Status` must be one of {', '.join(MEMORY_STATUSES)} "
                f"(got {status.group(1)!r})"
            )
        source_event = source_event_line.search(text)
        validation = validation_line.search(text)
        if source_event and not validation:
            failures.append(
                f"{rel}: evidence-derived records with `Source event:` require "
                "`Validation: pending|promote|retain|reject|rewrite`"
            )
        if validation and not source_event:
            failures.append(f"{rel}: `Validation:` requires a backticked `Source event:`")
        if validation:
            verdict = validation.group(1)
            expected_status = {
                "pending": "candidate",
                "promote": "active",
                "retain": "candidate",
                "reject": "rejected",
                "rewrite": "superseded",
            }[verdict]
            if status and status.group(1) != expected_status:
                failures.append(
                    f"{rel}: `Validation: {verdict}` requires `Status: {expected_status}`"
                )
            if verdict != "pending":
                required_validation_lines = (
                    "Validated by:",
                    "Action delta:",
                    "Validation rationale:",
                    "Evidence verified:",
                    "Current target verified:",
                    "Canonical overlap:",
                )
                for required in required_validation_lines:
                    if not re.search(rf"^{re.escape(required)}\s*\S+", text, re.MULTILINE):
                        failures.append(
                            f"{rel}: finalized validation requires `{required} ...`"
                        )
        confidence = MEMORY_CONFIDENCE_PATTERN.search(text)
        if not confidence:
            failures.append(f"{rel}: missing `Confidence: <0.0-1.0>` line")
        else:
            try:
                value = float(confidence.group(1))
                if not 0.0 <= value <= 1.0:
                    raise ValueError
            except ValueError:
                failures.append(f"{rel}: `Confidence` must be a number in [0.0, 1.0]")
        # Created/Updated must be present AND a real calendar date — the
        # runtime reader validates the calendar (strptime), so lint must too
        # (delivery-review parity finding: `2020-13-40` must fail both, not
        # pass lint while the record silently never surfaces).
        import datetime as _dt
        for label, pat in (("Created", MEMORY_CREATED_PATTERN), ("Updated", MEMORY_UPDATED_PATTERN)):
            m = pat.search(text)
            if not m:
                failures.append(f"{rel}: missing `{label}: YYYY-MM-DD` line")
                continue
            try:
                _dt.date.fromisoformat(m.group(1))
            except ValueError:
                failures.append(f"{rel}: `{label}` is not a valid calendar date ({m.group(1)})")
        if status and status.group(1) == "superseded" and not MEMORY_SUPERSEDED_BY_PATTERN.search(text):
            failures.append(
                f"{rel}: a superseded record must carry a backticked `Superseded by:` memory-id "
                "(history is preserved through supersession, never deletion)"
            )
        sections = _extract_sections(text)
        for section in MEMORY_REQUIRED_SECTIONS:
            if section not in text:
                failures.append(f"{rel}: missing required section `{section}`")
        summary_body = sections.get("## Summary")
        if summary_body is not None and not summary_body.strip():
            failures.append(f"{rel}: `## Summary` must not be empty")
        for section in ("## Evidence", "## Targets"):
            body = sections.get(section)
            if body is not None:
                if not _section_has_bullets(body):
                    failures.append(f"{rel}: `{section}` must include at least one bullet")
                elif "`" not in body:
                    failures.append(
                        f"{rel}: `{section}` bullets must carry backticked refs "
                        "(paths, symbols, wave/change ids, or commit SHAs)"
                    )
        # Forbidden content: secrets, raw transcripts, personal facts — same
        # prohibition-line exemption as journals (a line FORBIDDING content
        # may name it).
        for raw_line in text.splitlines():
            if _line_forbids_content(raw_line):
                continue
            if any(pattern.search(raw_line) for pattern in MEMORY_DISALLOWED_PATTERNS):
                failures.append(
                    f"{rel}: memory record appears to capture secrets, raw transcript content, "
                    f"or personal facts (forbidden by schema): {raw_line.strip()[:80]!r}"
                )
                break
    return failures


def check_journal_docs(root: Path, only: set[Path] | None = None, skip: set[Path] | None = None) -> list[str]:
    """``only`` (wave 1p9c1): when provided, restrict to those paths for the incremental lint path;
    when None the behavior is unchanged (whole-tree). ``skip`` (wave 1p9cj): exclude these paths
    (oversized docs skipped by the file-size guard)."""
    failures: list[str] = []
    journal_root = root / "docs/agents/journals"
    for path in sorted(journal_root.rglob("*.md")):
        rel = relative_to_root(root, path)
        if path.name == "README.md":
            continue
        if only is not None and path not in only:
            continue
        if skip is not None and path in skip:
            continue
        text = read_text(path)
        sections = _extract_sections(text)
        for section in JOURNAL_REQUIRED_SECTIONS:
            if section not in text:
                failures.append(f"{rel}: missing required section `{section}`")
        # Wave 1p9bn: scan per line and EXEMPT a line that is forbidding the content — a journal's own
        # Governance/disallowed list must be able to name what it forbids ("do not include raw transcript
        # content") without tripping the disallowed-pattern check. A real pasted transcript/secret line is
        # never phrased as a prohibition, so true positives are preserved.
        for raw_line in text.splitlines():
            if _line_forbids_content(raw_line):
                continue
            if any(pattern.search(raw_line) for pattern in JOURNAL_DISALLOWED_PATTERNS):
                failures.append(
                    f"{rel}: journal appears to capture sensitive data, raw transcript content, or low-salience "
                    f"routine noise (a line that is *forbidding* such content is exempt; this line is not): {raw_line.strip()[:80]!r}"
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
                    f"{rel}: `## Salience Triggers` — every bullet must contain a salience marker word; "
                    f"accepted markers: {', '.join(JOURNAL_SALIENCE_MARKERS)}"
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


def check_persona_docs(root: Path, only: set[Path] | None = None, skip: set[Path] | None = None) -> list[str]:
    """``only`` (wave 1p9c1): when provided, restrict to those paths for the incremental lint path;
    when None the behavior is unchanged (whole-tree). ``skip`` (wave 1p9cj): exclude these paths
    (oversized docs skipped by the file-size guard)."""
    failures: list[str] = []
    persona_root = root / "docs/agents/personas"
    for path in sorted(persona_root.rglob("*.md")):
        rel = relative_to_root(root, path)
        if path.name == "README.md":
            continue
        if only is not None and path not in only:
            continue
        if skip is not None and path in skip:
            continue
        text = read_text(path)
        sections = _extract_sections(text)
        for section in PERSONA_REQUIRED_SECTIONS:
            if section not in text:
                failures.append(f"{rel}: missing required section `{section}`")
        if "## Scope" in text:
            failures.append(f"{rel}: persona docs must not contain `## Scope` (plan/change doc concept — use `## Who` and `## Goals` for evidence)")
        for section in (
            "## Who",
            "## Goals",
            "## Workflows",
            "## Failure modes",
            "## Invocation signals",
            "## Operating identity",
            "## Salience triggers",
            "## Associated journal",
        ):
            section_text = sections.get(section)
            if section_text and not _section_has_bullets(section_text):
                failures.append(f"{rel}: `{section}` must include at least one bullet")
        identity_text = sections.get("## Operating identity", "")
        if identity_text and not _contains_any(identity_text, ("persona", "perspective", "role", "evaluate", "protect")):
            failures.append(f"{rel}: `## Operating identity` must describe the persona perspective or role")
        salience_text = sections.get("## Salience triggers", "")
        if salience_text and not _contains_any(salience_text, JOURNAL_SALIENCE_MARKERS):
            failures.append(
                f"{rel}: `## Salience triggers` — every bullet must contain a salience marker word; "
                f"accepted markers: {', '.join(JOURNAL_SALIENCE_MARKERS)}"
            )
        journal_paths = JOURNAL_PATH_PATTERN.findall(text)
        if not journal_paths:
            failures.append(f"{rel}: persona doc must reference an associated journal path")
        for journal_path in journal_paths:
            if not (root / journal_path).exists():
                failures.append(f"{rel}: persona doc references missing journal `{journal_path}`")
        if _contains_any(text, FACTOR_REVIEW_MARKERS):
            invocation_text = sections.get("## Invocation signals", "")
            workflows_text = sections.get("## Workflows", "")
            if not _contains_any(invocation_text + "\n" + workflows_text, FACTOR_REVIEW_MARKERS):
                failures.append(f"{rel}: factor-review expectations must be captured in `## Invocation signals` or `## Workflows`")
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


def check_prepare_council_verdict(root: Path) -> tuple[list[str], list[str]]:
    """Check that active/implementing waves have a prepare-council verdict in ## Review Checkpoints.

    Backwards-compatibility rule:
    - ``implementing`` waves: hard error (wf_implement_wave sets this status after this feature landed).
    - ``active`` waves: warning only (may predate this feature).
    """
    errors: list[str] = []
    warnings: list[str] = []
    wave_root = root / "docs" / "waves"
    if not wave_root.exists():
        return errors, warnings

    for path in sorted(wave_root.rglob("wave.md")):
        text = read_text(path)
        if "wave-id:" not in text:
            continue
        status = (_metadata_value(text, "Status") or "").casefold().strip()
        if status not in ("active", "implementing"):
            continue
        sections = _extract_sections(text)
        checkpoints = sections.get("## Review Checkpoints", "")
        if "prepare-council" in checkpoints.casefold():
            continue
        rel = relative_to_root(root, path)
        msg = f"{rel}: wave status is `{status}` but no `prepare-council` verdict found in `## Review Checkpoints`; run the prepare-phase Wave Council review before implementation"
        if status == "implementing":
            errors.append(msg)
        else:
            warnings.append(msg)
    return errors, warnings


# Structured prepare-council verdict line, mirroring the wf_prepare_wave parser in server_impl.py.
# Only PASS / PASS WITH NOTES / BLOCKED verdict lines carry a machine-checkable roster; freeform
# corrective or narrative checkpoint bullets that merely mention "prepare-council" are not rosters.
_PREPARE_COUNCIL_VERDICT_LINE_RE = re.compile(
    r"^\s*-\s*\*\*Prepare-phase Wave Council \[prepare-council\] — (?P<date>[^:]+): "
    r"(?P<verdict>PASS(?: WITH NOTES)?|BLOCKED)\*\*(?:\s*\((?P<meta>.*)\))?\s*$",
    re.IGNORECASE,
)

# Seats that legitimately appear in a roster without a dedicated evidence bullet:
# wave-council is the moderator (synthesis is the verdict line itself) and red-team is the
# adversarial primer, whose output is conventionally folded into `strongest-challenge`.
PREPARE_COUNCIL_ROSTER_TOLERANCE = frozenset({"red-team", "wave-council"})

# A roster claim is a hyphenated role token (architecture-reviewer, qa-reviewer, reality-checker,
# docs-contract-reviewer, ...). Requiring the hyphen is the fail-safe filter: prose fragments,
# stray annotation words, and placeholder text never look like role tokens.
_PREPARE_COUNCIL_ROLE_TOKEN_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")


def _prepare_council_roster_tokens(meta_text: str) -> list[str]:
    """Extract claimed non-tolerance seat tokens from a verdict line's meta fields.

    Reads the ``seats:`` and ``rotating-seat:`` fields, splits on commas, and keeps only
    plausible role tokens. Parts containing ``<`` / ``>`` are template placeholder text,
    not seat claims; non-hyphenated parts (``none``, annotation fragments) are skipped.
    """
    meta: dict[str, str] = {}
    for raw_part in re.split(r";\s*", meta_text or ""):
        key, sep, value = raw_part.partition(":")
        if sep:
            meta[key.strip().casefold()] = value.strip()
    tokens: list[str] = []
    for field_name in ("seats", "rotating-seat"):
        for part in (meta.get(field_name) or "").split(","):
            candidate = part.strip().casefold()
            if "<" in candidate or ">" in candidate:
                continue
            if not _PREPARE_COUNCIL_ROLE_TOKEN_RE.match(candidate):
                continue
            if candidate in PREPARE_COUNCIL_ROSTER_TOLERANCE:
                continue
            if candidate not in tokens:
                tokens.append(candidate)
    return tokens


def _prepare_council_seat_evidenced(seat: str, corpus: str) -> bool:
    """True when the seat has a literal corroboration in the (casefolded) evidence corpus.

    Matches the literal role token (``architecture-reviewer``) or the seat's lane stem followed
    by the word ``seat`` (``architecture seat``) — the two surface forms wave records actually
    use when a seat records findings in checkpoint prose. Anything looser (e.g. the bare stem)
    would re-open the vacuity this check exists to close.
    """
    if seat in corpus:
        return True
    stem = seat.rsplit("-", 1)[0]
    return bool(stem) and f"{stem} seat" in corpus


def check_prepare_council_roster_evidence(root: Path) -> tuple[list[str], list[str]]:
    """Check that every seat named in a prepare-council verdict roster has recorded evidence.

    The failure mode this closes: a structurally valid ``prepare-council: PASS`` line whose
    ``seats:`` roster was pasted from the verdict template while the recorded evidence names
    different (or no) reviewers — a thin readiness review that sails through the existence-only
    check above.

    Matching rule (pinned; deliberately non-vacuous):

    - Roster = tokens parsed from the verdict line's ``seats:`` and ``rotating-seat:`` fields,
      excluding the tolerance set ``{red-team, wave-council}`` (moderator synthesis and the
      adversarial primer legitimately have no dedicated evidence bullet).
    - Evidence corpus = ``## Prepare Review Evidence`` + ``## Review Evidence`` +
      ``## Review Checkpoints``, with EVERY structured verdict line removed — not just the
      matched line's own text. A seat named only inside a verdict-line roster does not
      self-certify, and two pasted thin PASS lines must not mutually certify each other's
      rosters (the review-fix hardening: excluding only the matched line let a second,
      near-identical verdict line corroborate the first). The ``## Participants`` table and
      ``## Changes`` region are outside the corpus by construction — a Participants Role entry
      is a responsibility assignment, not review evidence.
    - A seat is corroborated by its literal role token or its ``<stem> seat`` prose form
      appearing anywhere in the corpus (see ``_prepare_council_seat_evidenced``).

    Scope and severity (fail-safe by design):

    - Only ``active`` / ``implementing`` waves are checked — the roster claim becomes
      load-bearing when the wave opens for implementation, while readied-``planned`` records
      are still being amended by prepare passes; closed records are preserved history.
    - Findings are warnings, not errors: this is a consistency backstop through the standard
      lint channel, not a hard structural gate. It can only catch unnamed/unevidenced seats;
      it cannot judge whether a recorded review was actually code-grounded.

    Recorded limitation (bounded by design, per the introducing change's Decision Log): any
    prose mention of a seat token in a non-verdict evidence/checkpoint line corroborates —
    including negative or planning sentences ("security-reviewer will review later",
    "architecture-reviewer was not run"). The check closes the unnamed/unevidenced-seat
    hole; it does not (and cannot) judge whether the mention constitutes real evidence.
    """
    errors: list[str] = []
    warnings: list[str] = []
    wave_root = root / "docs" / "waves"
    if not wave_root.exists():
        return errors, warnings

    for path in sorted(wave_root.rglob("wave.md")):
        text = read_text(path)
        if "wave-id:" not in text:
            continue
        status = (_metadata_value(text, "Status") or "").casefold().strip()
        if status not in ("active", "implementing"):
            continue
        sections = _extract_sections(text)
        corpus_sections = (
            sections.get("## Prepare Review Evidence", ""),
            sections.get("## Review Evidence", ""),
            sections.get("## Review Checkpoints", ""),
        )
        # Review-fix hardening: exclude ALL structured verdict lines from the
        # corpus, not just the matched line's own text — otherwise two pasted
        # near-identical thin PASS lines mutually certify each other's rosters
        # (each line's seat tokens "corroborate" the other's claim).
        corpus = "\n".join(
            "\n".join(
                line
                for line in section.splitlines()
                if not _PREPARE_COUNCIL_VERDICT_LINE_RE.match(line.strip())
            )
            for section in corpus_sections
        ).casefold()
        checkpoints = sections.get("## Review Checkpoints", "")
        for raw_line in checkpoints.splitlines():
            match = _PREPARE_COUNCIL_VERDICT_LINE_RE.match(raw_line.strip())
            if not match:
                continue
            roster = _prepare_council_roster_tokens(match.group("meta") or "")
            if not roster:
                continue
            missing = [seat for seat in roster if not _prepare_council_seat_evidenced(seat, corpus)]
            if missing:
                rel = relative_to_root(root, path)
                warnings.append(
                    f"{rel}: prepare-council verdict roster names seat(s) with no recorded evidence "
                    f"in the wave record: {', '.join(missing)}. Each seat listed in `seats:` / "
                    "`rotating-seat:` must record findings (or an explicit no-findings note) in "
                    "`## Prepare Review Evidence`, `## Review Evidence`, or a `## Review Checkpoints` "
                    "entry other than the verdict line itself; record the seats actually run, not the "
                    "template roster"
                )
    return errors, warnings


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
