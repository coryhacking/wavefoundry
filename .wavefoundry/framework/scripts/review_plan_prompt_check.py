"""Read-only legacy review-plan classification shared by upgrade and rendering.

No installed-framework imports: incoming upgrade hooks load this privately.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

REVIEW_PLAN_OLD_PROMPT = "docs/prompts/interrogate-plan.prompt.md"
REVIEW_PLAN_NEW_PROMPT = "docs/prompts/review-plan.prompt.md"
REVIEW_PLAN_LEGACY_CONTRACT_LINES: "tuple[tuple[str, str, str], ...]" = (
    ("Heading", "# Interrogate This Plan", "# Review Plan"),
    (
        "Shortcut",
        "Shortcut: **`Interrogate this plan`** | Alias: **`Stress-test this plan`**",
        "Shortcut: **`Review plan`** | Aliases: **`Interrogate this plan`**, **`Stress-test this plan`**",
    ),
    (
        "Purpose",
        "Optional stress-test of a consolidated change doc before wave admission. Walks every unresolved decision branch in Requirements, Acceptance Criteria, and Scope.",
        "Optional stress-test of a consolidated change doc, or the current wave record when no change is specified, before or after admission and before implementation. Walks every unresolved decision branch in Requirements, Acceptance Criteria, and Scope.",
    ),
    (
        "Input fallback",
        "Given a change doc as context:",
        "Given a change doc as context, or the current wave record when no change is specified:",
    ),
    (
        "When to use",
        "- Before admitting a complex or high-risk change",
        "- Before or after admitting a complex or high-risk change, but before implementation",
    ),
    (
        "No-gate timing",
        "**Interrogate this plan** is an optional stress-testing tool, not a required lifecycle step. Use it before or after authoring a change doc but before wave admission.",
        "**Review plan** is an optional stress-testing tool, not a required lifecycle step. Use it before or after plan admission, at the operator's discretion, before implementation begins.",
    ),
    (
        "Canonical source",
        "See `.wavefoundry/framework/seeds/175-interrogate-plan.prompt.md` for the full interrogation contract.",
        "See `.wavefoundry/framework/seeds/175-review-plan.prompt.md` for the full plan-review contract.",
    ),
)

REVIEW_PLAN_EARLY_CANONICAL_CONTRACT_LINES: "tuple[tuple[str, str, tuple[str, ...]], ...]" = (
    ("Heading", "# Interrogate This Plan Prompt", ("# Review Plan Prompt",)),
    (
        "Primary trigger",
        "- `Interrogate this plan`",
        ("- `Review plan`", "- `Interrogate this plan`"),
    ),
    (
        "Canonical source",
        "Use `.wavefoundry/framework/seeds/175-interrogate-plan.prompt.md` to:",
        ("Use `.wavefoundry/framework/seeds/175-review-plan.prompt.md` to:",),
    ),
    (
        "Input fallback",
        "- Load the target change doc (`docs/waves/<wave-id>/<change-id>.md` or `docs/plans/<change-id>.md`) or wave record (`docs/waves/<wave-id>/wave.md`).",
        ("- Load the target change doc (`docs/waves/<wave-id>/<change-id>.md` or `docs/plans/<change-id>.md`) or, when no change is specified, the current wave record (`docs/waves/<wave-id>/wave.md`).",),
    ),
    (
        "Scope wording",
        "- Do not re-plan or derive new scope during interrogation; record emergent scope items as follow-on candidates rather than introducing them inline.",
        ("- Do not re-plan or derive new scope during plan review; record emergent scope items as follow-on candidates rather than introducing them inline.",),
    ),
    (
        "No-gate identity",
        "- Do not treat this as a required lifecycle gate; it is entirely voluntary before or after plan admission.",
        ("- Do not treat **Review plan** as a required lifecycle gate; it is entirely voluntary before or after plan admission.",),
    ),
    (
        "Bounded wording",
        "- Keep interrogation bounded to Requirements, Acceptance Criteria, and Scope — do not re-examine explicitly resolved Decision Log entries.",
        ("- Keep plan review bounded to Requirements, Acceptance Criteria, and Scope — do not re-examine explicitly resolved Decision Log entries.",),
    ),
    (
        "Batch example",
        "- In `--batch` mode (e.g. `Interrogate this plan --batch`): dump all unresolved questions as a numbered list rather than asking one at a time. Each item includes the recommended answer and source citation.",
        ("- In `--batch` mode (e.g. `Review plan --batch`): dump all unresolved questions as a numbered list rather than asking one at a time. Each item includes the recommended answer and source citation.",),
    ),
)

REVIEW_PLAN_LEGACY_CONTRACT_PROFILES = (
    (
        "shortcut-contract",
        tuple(
            (label, old_line, (new_line,))
            for label, old_line, new_line in REVIEW_PLAN_LEGACY_CONTRACT_LINES
        ),
    ),
    ("early-trigger-phrases-contract", REVIEW_PLAN_EARLY_CANONICAL_CONTRACT_LINES),
)

RECOVERY_POINTER = "docs/references/native-windows-support.md#review-plan-prompt-migration-recovery"


def line_content_and_ending(physical_line: str) -> tuple[str, str]:
    if physical_line.endswith("\r\n"):
        return physical_line[:-2], "\r\n"
    if physical_line.endswith(("\r", "\n")):
        return physical_line[:-1], physical_line[-1:]
    return physical_line, ""


def classify_review_plan_prompt(old: dict, new: dict) -> dict:
    """Classify observed lexical entries; readers own containment and identity."""
    reason = None
    profile = None
    original = None
    if old.get("exists") and new.get("exists"):
        reason = f"both {REVIEW_PLAN_OLD_PROMPT} and {REVIEW_PLAN_NEW_PROMPT} exist; both were preserved"
    elif not old.get("exists"):
        return {"blocked": False, "profile": None, "original": None}
    elif old.get("linked"):
        reason = "the legacy prompt is a symlink or reparse point"
    elif not old.get("regular"):
        reason = "the legacy prompt is not a regular file"
    elif old.get("error"):
        reason = f"the legacy prompt could not be read as UTF-8 ({old['error']})"
    else:
        try:
            original = old["bytes"].decode("utf-8")
        except UnicodeDecodeError:
            reason = "the legacy prompt could not be read as UTF-8 (UnicodeDecodeError)"
        if reason is None:
            logical = [line_content_and_ending(line)[0] for line in original.splitlines(keepends=True)]
            checks = [(name, candidate, [label for label, line, _ in candidate if logical.count(line) != 1])
                      for name, candidate in REVIEW_PLAN_LEGACY_CONTRACT_PROFILES]
            recognized = [(name, candidate) for name, candidate, missing in checks if not missing]
            if len(recognized) == 1:
                profile = recognized[0][1]
            else:
                details = "; ".join(f"{name}: {', '.join(missing) if missing else 'matched'}"
                                    for name, _, missing in checks)
                reason = ("the legacy prompt has customized or unrecognized canonical contract lines, "
                          "or mixes recognized profiles; the old prompt was preserved and the new skill/baseline "
                          f"were not rendered. Resolve these fields manually: {details}")
    if reason is None:
        return {"blocked": False, "profile": profile, "original": original}
    message = (f"review-plan prompt migration blocked: {REVIEW_PLAN_OLD_PROMPT}: {reason}. "
               f"Write {REVIEW_PLAN_NEW_PROMPT} from the packaged lifecycle-prompts/review-plan.prompt.md "
               "template, merge project-authored prose and keep project aliases, remove the old prompt, and rerun the upgrade "
               "after updating docs/prompts/index.md and the prompt manifest. Rerunning is safe after repair; "
               "waves avoid re-Prepare only with byte-identical migrated policy, no carrier changes and a current evaluator. "
               "Changed policy/carriers or a stale evaluator legitimately require re-Prepare. "
               f"Recovery: {RECOVERY_POINTER}.")
    return {"blocked": True, "reason": reason, "message": message, "path": REVIEW_PLAN_OLD_PROMPT,
            "recovery_pointer": RECOVERY_POINTER}


def observe_prompt(path: Path) -> dict:
    """Plain read-only old-code-window observation; does not promise race closure."""
    try:
        entry = os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return {"exists": False}
    except OSError as exc:
        return {"exists": True, "regular": True, "error": type(exc).__name__}
    linked = path.is_symlink() or bool(getattr(entry, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024))
    result = {"exists": True, "linked": linked, "regular": stat.S_ISREG(entry.st_mode)}
    if result["regular"] and not linked:
        try:
            result["bytes"] = path.read_bytes()
        except OSError as exc:
            result["error"] = type(exc).__name__
    return result


def check_review_plan_prompt(root: Path) -> dict:
    return classify_review_plan_prompt(observe_prompt(root / REVIEW_PLAN_OLD_PROMPT),
                                      observe_prompt(root / REVIEW_PLAN_NEW_PROMPT))
