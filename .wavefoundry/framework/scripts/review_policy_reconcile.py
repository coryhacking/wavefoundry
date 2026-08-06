"""Versioned, fail-closed reconciliation of retired review-lifecycle sections."""

from __future__ import annotations

import difflib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from review_policy import (
    LIFECYCLE_RECONCILER_CARRIERS,
    RETIRED_LIFECYCLE_TOKENS,
    UPGRADE_POLICY_BLOCK,
    UPGRADE_POLICY_MARKER_BEGIN,
    UPGRADE_POLICY_MARKER_END,
    contained_relative_path,
)


RECONCILER_VERSION = 1
MANAGED_BEGIN = "<!-- wavefoundry:review-lifecycle:begin -->"
MANAGED_END = "<!-- wavefoundry:review-lifecycle:end -->"
UPGRADE_POLICY_DESTINATION = "docs/prompts/upgrade-wavefoundry.prompt.md"


# Wave 1uhcb: the editorial-only stop condition plus the narrate-not-amend rule.
# Both baselines below (the v1.14 prose and the shipped repair-cycle sentence)
# converge on this one current text, and neither baseline is a substring of it,
# so a second reconciliation pass is a no-op.
_REPAIR_CYCLE_STOP_CONDITION = (
    "Blocking findings open a recorded repair cycle. The implementer repairs the affected "
    "boundary and each blocking lane independently reverifies it before delivery approval is "
    "restored. After the first delivery cycle, an editorial-only finding (wording that is true but "
    "imprecise, drifted citations, formatting) is repaired inline in the current cycle and "
    "recorded in the Progress Log; it does not by itself open another repair cycle. Every finding "
    "that needs verification, a boundary repair, or escalation retains its existing action-matrix "
    "route. An editorial finding that makes a shipped claim FALSE is a correctness defect. A scope, "
    "requirement, or AC change is recorded in the section that owns it, and the Progress Log row "
    "points at that edit rather than substituting for it."
)

_SHIPPED_REPAIR_CYCLE_SENTENCE = (
    "Blocking findings open a recorded repair cycle; the implementer repairs the affected "
    "boundary and each blocking lane independently reverifies it before delivery approval is "
    "restored."
)


KNOWN_SECTION_REPLACEMENTS: dict[str, tuple[tuple[str, str], ...]] = {
    "docs/prompts/implement-wave.prompt.md": (
        (
            "Coordinator-managed implementation and review loop for all admitted changes in a wave. Not a pure coding phase — reviewer lanes participate during execution.",
            "Coordinator-managed implementation and computational verification for all admitted changes in a wave. Required inferential lanes run afterward through **Review wave**.",
        ),
        (
            "1. Records a `Thought:` entry in the Progress Log before each lane invocation.\n"
            "2. Produces an ordered lane sequence before the first edit.\n"
            "3. Runs parallel reviewer lanes (those with no shared dependencies) concurrently; synthesizes a merged `Observe:` before the next `Thought:`.\n"
            "4. Classifies findings: Level 1 (micro, internal fix), Level 2 (reviewer loop, fix and re-run, no re-Prepare), Level 3 (scope/plan invalidation, stop and re-Prepare or re-plan).",
            "1. Records a `Thought:` entry in the Progress Log before each scoped action.\n"
            "2. Produces an ordered implementation sequence before the first edit.\n"
            "3. Runs independent implementation and computational-verification actions concurrently where safe; synthesizes a merged `Observe:` before the next `Thought:`.\n"
            "4. Classifies findings: Level 1 (micro, internal fix), Level 2 (exceptional named checkpoint at the affected boundary), Level 3 (scope/plan invalidation, stop and re-Prepare or re-plan).",
        ),
        (
            "## Pre-Implementation Review Gate\n\n"
            "Mandatory first phase before any code edit. Purpose: challenge the wave from a failure-first perspective and confirm the implementation packet is complete enough to begin without avoidable rework.\n\n"
            "**Step 1 — Pre-mortem:** Assume the implementation produces avoidable churn. Name the 3–5 most likely causes before writing any code: scope ambiguity, missing codebase knowledge, unknown dependencies, missing test strategy, hidden assumptions, wrong lanes.\n\n"
            "**Step 2 — Packet completeness:** Verify all of the following before the first edit:\n"
            "- All admitted change docs are complete with Requirements and ACs\n"
            "- AC priority recorded (required / important / nice-to-have / not this scope)\n"
            "- Required review and builder lanes selected and in the wave record\n"
            "- Relevant architecture, spec, or context docs identified\n"
            "- Key unknowns named and either resolved or accepted as explicit known risks\n"
            "- Ordered lane sequence grounded in MCP evidence\n\n"
            "**Step 3 — Verdict:** Record in `## Review Checkpoints`:\n"
            "```\n"
            "- pre-implementation-review: passed (YYYY-MM-DD) — [brief note on highest risk and how it was addressed]\n"
            "```\n"
            "A `blocked` verdict halts implementation until the gap is resolved. When `wave_review.enabled`, the `wave-council-readiness` verdict covers admissibility; this gate is the coordinator's packet-completeness and failure-mode check.\n",
            "## Readiness Handoff\n\n"
            "**Prepare wave** owns the one pre-code critique: failure-first analysis, packet completeness, and the current readiness approval. `wf_implement_wave` consumes that authority directly on declared waves. Do not repeat the critique or mint a second approval before editing.\n",
        ),
        (
            "Required review lanes from readiness must participate during execution.",
            "Required review lanes from readiness participate during **Review wave** after implementation evidence is complete. During implementation, request a named checkpoint only when a high-risk boundary needs independent judgment before work can safely continue.",
        ),
    ),
    "docs/prompts/review-wave.prompt.md": (
        (
            "When implementation passes through the prepare gate, the review must also be able to verify that the prior prepare-council verdict was structured and machine-readable, not just a freeform marker.",
            "Delivery review verifies the current typed readiness authority on declared waves; it does not treat a prose `prepare-council` checkpoint as machine evidence. Legacy waves retain their prose compatibility contract.",
        ),
        (
            "Blocking findings return the wave to implementation (Level 2 loop).",
            _REPAIR_CYCLE_STOP_CONDITION,
        ),
        (
            "## Pre-Implementation Gate Reconciliation\n\n"
            "During review, confirm that a `pre-implementation-review: passed` verdict was recorded before the first code edit (in `## Review Checkpoints`). If the gate was skipped or recorded as `blocked` and implementation proceeded anyway, surface it as a finding. When implementation revealed that the pre-mortem missed important risks or information gaps, record a `Reflect:` entry in Progress Log noting what should be added to the pre-implementation checklist before the next similar wave.\n",
            "",
        ),
        (
            _SHIPPED_REPAIR_CYCLE_SENTENCE,
            _REPAIR_CYCLE_STOP_CONDITION,
        ),
    ),
    "docs/prompts/agents/review-wave.prompt.md": (
        (
            "When `wave_review.enabled` is true, Wavefoundry also requires a delivery-phase council pass.",
            "When the current Prepare receipt requires delivery Council, Wavefoundry runs a delivery-phase council pass.",
        ),
        (
            "- Level 2: fix and re-run reviewer, no re-Prepare",
            "- Level 2: after a recorded delivery finding, repair the affected boundary and obtain fresh independent reverification from each blocking lane; no re-Prepare unless the plan or scope became invalid",
        ),
    ),
    "docs/prompts/council-review.prompt.md": ((
        "the recorded verdict must be written back into `## Review Checkpoints` as a structured `prepare-council` line containing `moderator`, `primer-depth`, `seats`, `rotating-seat`, `strongest-challenge`, and `strongest-alternative`. The lifecycle gate only accepts that structured verdict, not a freeform marker.",
        "a declared wave records the machine authority as a typed `wave-council-readiness` approval event. Its `## Review Checkpoints` verdict may retain the structured `prepare-council` fields as narrative, but that prose never changes a declared wave's lifecycle outcome. A legacy wave still uses the structured verdict line as its compatibility gate.",
    ),),
    "docs/prompts/prepare-wave.prompt.md": (
        (
            "record `wave-council-readiness` in `## Review Evidence` and the narrative verdict in `## Review checkpoints`. The recorded verdict must be a structured `prepare-council` line with `moderator`, `primer-depth`, `seats`, `rotating-seat`, `strongest-challenge`, and `strongest-alternative` fields; `seats:` names the seats actually run, each at most once, and every rostered seat must have recorded evidence in the wave record (docs-lint checks this roster⇄evidence consistency — see `docs/prompts/council-review.prompt.md`). **`wf_prepare_wave` signals this step with `status: \"ready_for_council_review\"` — run the review immediately when you see that status, then call `wf_prepare_wave` again (mode `ready` to ready-without-opening, or `create` to prepare-and-open) to complete prepare.**",
            "On declared waves, record `wave-council-readiness` as a typed approval event via `wf_review_event`; this typed record is the sole machine authority, and any structured `prepare-council` checkpoint is narrative only. Legacy prose waves retain the structured checkpoint compatibility gate. Call `wf_prepare_wave` again after the current typed approval is recorded (`ready` to ready without opening, or `create` to prepare and open).",
        ),
        (
            "A clean readiness verdict confirms the wave is **admissible**. It does not replace the **pre-implementation review gate**, which is the mandatory first phase of `Implement wave`. The lifecycle sequence is: `Prepare wave` (readiness) → **pre-implementation review gate** (first phase of `Implement wave`) → first code edit.",
            "A clean readiness verdict confirms the wave is **admissible** and is the single pre-code review decision. The lifecycle sequence is: `Prepare wave` (failure-first critique, packet completeness, current readiness approval) → `Implement wave` → first code edit.",
        ),
    ),
    "docs/prompts/upgrade-wavefoundry.prompt.md": (),
}


@dataclass(frozen=True)
class CarrierEdit:
    relative_path: str
    before: bytes
    after: bytes


def _managed_region(text: str) -> tuple[int, int] | None:
    begins = [i for i in range(len(text)) if text.startswith(MANAGED_BEGIN, i)]
    ends = [i for i in range(len(text)) if text.startswith(MANAGED_END, i)]
    if not begins and not ends:
        return None
    if len(begins) != 1 or len(ends) != 1 or begins[0] >= ends[0]:
        raise ValueError("ambiguous review-lifecycle managed markers")
    return begins[0], ends[0] + len(MANAGED_END)


def _contains_retired(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in RETIRED_LIFECYCLE_TOKENS)


def _retired_token_worklist(text: str) -> tuple[str, ...]:
    """Return every canonical retired token with all matching source lines."""

    lowered_lines = tuple(line.lower() for line in text.splitlines())
    worklist: list[str] = []
    for token in RETIRED_LIFECYCLE_TOKENS:
        lines = tuple(
            line_number
            for line_number, line in enumerate(lowered_lines, start=1)
            if token in line
        )
        if lines:
            joined = ",".join(str(line) for line in lines)
            worklist.append(f"{token!r} at line(s) {joined}")
    return tuple(worklist)


def _retired_recovery(relative: str, text: str, problem: str) -> str:
    matches = _retired_token_worklist(text)
    rendered = "; ".join(matches) if matches else "no canonical token match"
    matched_tokens = {
        token
        for token in RETIRED_LIFECYCLE_TOKENS
        if token in text.lower()
    }
    previews: list[str] = []
    for index, (legacy, current) in enumerate(
        KNOWN_SECTION_REPLACEMENTS.get(relative, ()),
        start=1,
    ):
        if not any(token in legacy.lower() for token in matched_tokens):
            continue
        patch = "\n".join(
            difflib.unified_diff(
                legacy.splitlines(),
                current.splitlines(),
                fromfile=f"{relative}:registered-legacy-{index}",
                tofile=f"{relative}:current-{index}",
                lineterm="",
            )
        )
        if patch:
            previews.append(patch)
    preview = (
        "registered replacement preview(s):\n" + "\n".join(previews)
        if previews
        else "no exact registered replacement covers this drift; rewrite manually"
    )
    return (
        f"{relative}: {problem}; complete retired-token worklist: {rendered}; "
        f"{preview}; edit the listed project-authored prose, then retry the same upgrade command"
    )


_LIVE_MARKDOWN_EXCLUDED_PREFIXES = (
    ".git/",
    ".wavefoundry/framework/",
    ".wavefoundry/index/",
    ".wavefoundry/upgrade-assets/",
    "docs/waves/",
    "docs/reports/",
    "docs/agents/memory/",
)


def _live_markdown_dir_excluded(relative_dir: str) -> bool:
    normalized = relative_dir.strip("/")
    if any((normalized + "/").startswith(prefix) for prefix in _LIVE_MARKDOWN_EXCLUDED_PREFIXES):
        return True
    parts = normalized.split("/")
    return (
        len(parts) >= 2
        and parts[0] == ".wavefoundry"
        and parts[1].startswith("framework.rollback-")
    )


def _live_markdown_retired_errors(root: Path) -> tuple[str, ...]:
    """Report retired guidance outside registered lifecycle carriers."""

    registered = set(LIFECYCLE_RECONCILER_CARRIERS)
    errors: list[str] = []
    candidates: list[Path] = []
    try:
        for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
            current_path = Path(current)
            relative_dir = current_path.relative_to(root).as_posix()
            dirs[:] = [
                name
                for name in dirs
                if not _live_markdown_dir_excluded(
                    name if relative_dir == "." else f"{relative_dir}/{name}"
                )
            ]
            candidates.extend(
                current_path / name for name in files if name.endswith(".md")
            )
    except (OSError, ValueError) as exc:
        return (f"live Markdown retired-guidance scan failed: {exc}",)
    for path in sorted(candidates):
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if (
            relative in registered
            or relative == "CHANGELOG.md"
            or any(relative.startswith(prefix) for prefix in _LIVE_MARKDOWN_EXCLUDED_PREFIXES)
            or path.is_symlink()
            or not path.is_file()
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{relative}: unreadable live Markdown: {exc}")
            continue
        if _contains_retired(text):
            errors.append(
                _retired_recovery(
                    relative,
                    text,
                    "retired lifecycle prose outside a registered carrier "
                    "(report-only; automatic rewrite is refused)",
                )
            )
    return tuple(errors)


def _reconcile_upgrade_policy_region(text: str) -> str:
    begins = text.count(UPGRADE_POLICY_MARKER_BEGIN)
    ends = text.count(UPGRADE_POLICY_MARKER_END)
    if begins != ends or begins > 1:
        raise ValueError("ambiguous review-policy upgrade markers")
    if begins == 0:
        return text.rstrip() + "\n\n" + UPGRADE_POLICY_BLOCK + "\n"
    start = text.index(UPGRADE_POLICY_MARKER_BEGIN)
    end = text.index(UPGRADE_POLICY_MARKER_END, start) + len(UPGRADE_POLICY_MARKER_END)
    return text[:start] + UPGRADE_POLICY_BLOCK + text[end:]


def plan_reconciliation(root: Path) -> tuple[CarrierEdit, ...]:
    """Preflight every carrier and return a complete atomic-write plan."""

    edits: list[CarrierEdit] = []
    errors: list[str] = []
    for relative in LIFECYCLE_RECONCILER_CARRIERS:
        try:
            path = contained_relative_path(root, relative)
        except (OSError, ValueError) as exc:
            errors.append(f"{relative}: {exc}")
            continue
        if not path.exists():
            continue
        try:
            before = path.read_bytes()
            text = before.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{relative}: unreadable carrier: {exc}")
            continue
        try:
            managed = _managed_region(text)
        except ValueError as exc:
            errors.append(f"{relative}: {exc}")
            continue
        after = text
        if relative == "docs/prompts/upgrade-wavefoundry.prompt.md":
            try:
                after = _reconcile_upgrade_policy_region(text)
            except ValueError as exc:
                errors.append(f"{relative}: {exc}")
                continue
        if managed is not None:
            # Current managed regions are renderer-owned. The reconciler may
            # validate them but never rewrite them.
            if _contains_retired(text[managed[0]:managed[1]]):
                errors.append(
                    _retired_recovery(
                        relative,
                        text[managed[0]:managed[1]],
                        "retired lifecycle prose inside renderer-owned region",
                    )
                )
            continue
        matches = [
            (legacy, current)
            for legacy, current in KNOWN_SECTION_REPLACEMENTS.get(relative, ())
            if legacy in text
        ]
        if matches:
            for legacy, current in matches:
                if text.count(legacy) != 1:
                    errors.append(f"{relative}: repeated recognized legacy section; refusing to guess")
                    break
                after = after.replace(legacy, current, 1)
            if errors and errors[-1].startswith(f"{relative}:"):
                continue
            if _contains_retired(after):
                errors.append(
                    _retired_recovery(
                        relative,
                        after,
                        "retired lifecycle prose remains after registered replacement",
                    )
                )
                continue
        elif _contains_retired(after):
            errors.append(
                _retired_recovery(
                    relative,
                    after,
                    "retired lifecycle prose is not an exact registered baseline",
                )
            )
            continue
        if after != text:
            edits.append(CarrierEdit(relative, before, after.encode("utf-8")))
    errors.extend(_live_markdown_retired_errors(root))
    if errors:
        raise ValueError("lifecycle carrier preflight failed: " + "; ".join(errors))
    return tuple(edits)


def _atomic_replace(path: Path, body: bytes) -> None:
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def apply_reconciliation(root: Path, edits: tuple[CarrierEdit, ...]) -> tuple[str, ...]:
    """Apply a preflighted plan with immediate identity/shape revalidation."""

    changed: list[str] = []
    for edit in edits:
        path = contained_relative_path(root, edit.relative_path)
        if path.read_bytes() != edit.before:
            raise ValueError(f"{edit.relative_path}: carrier changed after preflight; retry Upgrade")
        _atomic_replace(path, edit.after)
        changed.append(edit.relative_path)
    return tuple(changed)


def reconcile_lifecycle_sections(root: Path) -> tuple[str, ...]:
    return apply_reconciliation(root, plan_reconciliation(root))


def reconcile_upgrade_policy_surface(root: Path) -> tuple[str, ...]:
    """Refresh only the upgrade-policy marker from freshly extracted code.

    The in-process lifecycle reconciler remains the primary owner. This bounded
    helper exists for the installing-upgrade old-code window: the fresh renderer
    may replay the shared marker without adopting any other lifecycle carrier.
    """

    path = contained_relative_path(root, UPGRADE_POLICY_DESTINATION)
    if not path.is_file():
        return ()
    try:
        before = path.read_bytes()
        text = before.decode("utf-8")
        after = _reconcile_upgrade_policy_region(text).encode("utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(
            f"{UPGRADE_POLICY_DESTINATION}: upgrade-policy reconciliation failed: {exc}"
        ) from exc
    if after == before:
        return ()
    _atomic_replace(path, after)
    return (UPGRADE_POLICY_DESTINATION,)


__all__ = [
    "CarrierEdit", "KNOWN_SECTION_REPLACEMENTS", "MANAGED_BEGIN", "MANAGED_END",
    "RECONCILER_VERSION", "UPGRADE_POLICY_DESTINATION", "_live_markdown_retired_errors",
    "apply_reconciliation", "plan_reconciliation",
    "reconcile_lifecycle_sections", "reconcile_upgrade_policy_surface",
]
