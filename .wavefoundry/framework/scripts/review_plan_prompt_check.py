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

# Distribution source declaration, deliberately local to this standalone checker.
# Shape: ((name, ((label, exact_old_line, (replacement_line, ...)), ...)), ...).
# Incoming pack preflight loads this file privately, never an installed profile.
EXTRA_REVIEW_PLAN_LEGACY_CONTRACT_PROFILES = ()


def _legacy_contract_profiles():
    extra = EXTRA_REVIEW_PLAN_LEGACY_CONTRACT_PROFILES
    if not isinstance(extra, (tuple, list)):
        raise ValueError("extra legacy profiles must be a sequence")
    profiles = (*REVIEW_PLAN_LEGACY_CONTRACT_PROFILES, *extra)
    names = set()
    for declaration in profiles:
        if not isinstance(declaration, (tuple, list)) or len(declaration) != 2:
            raise ValueError("legacy profile must contain a name and contract lines")
        name, lines = declaration
        if not isinstance(name, str) or not name.strip() or len(name) > 128 or name in names:
            raise ValueError("legacy profile names must be nonempty and unique")
        names.add(name)
        if not isinstance(lines, (tuple, list)) or not lines:
            raise ValueError("legacy profile contract must be nonempty")
        labels, old_lines = set(), set()
        for row in lines:
            if not isinstance(row, (tuple, list)) or len(row) != 3:
                raise ValueError("legacy profile rows must contain label, old line and replacements")
            label, old, replacements = row
            if (not isinstance(label, str) or not label.strip() or label in labels
                    or not isinstance(old, str) or not old.strip() or old in old_lines
                    or "\n" in old or "\r" in old
                    or not isinstance(replacements, (tuple, list)) or not replacements
                    or any(not isinstance(line, str) or "\n" in line or "\r" in line for line in replacements)):
                raise ValueError("legacy profile rows must have unique labels and exact single lines")
            labels.add(label)
            old_lines.add(old)
    return profiles


RECOVERY_POINTER = "docs/references/native-windows-support.md#review-plan-prompt-migration-recovery"
PROMPT_MAX_BYTES = 8 * 1024 * 1024
_DIR_FD_SUPPORTED = (
    hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW")
    and hasattr(os, "O_NONBLOCK") and {os.open, os.stat} <= os.supports_dir_fd
)


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
    try:
        profiles = _legacy_contract_profiles()
    except ValueError as exc:
        reason = f"invalid legacy profile declaration ({exc}); correct the source declaration and retry"
        profiles = ()
    if reason is not None:
        pass
    elif old.get("exists") and new.get("exists"):
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
                      for name, candidate in profiles]
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


def _linked_entry(entry) -> bool:
    return stat.S_ISLNK(entry.st_mode) or bool(
        getattr(entry, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)
    )


def _same_entry(checked, opened) -> bool:
    return (checked.st_dev, checked.st_ino) == (opened.st_dev, opened.st_ino)


def _read_prompt_bytes(fd: int) -> bytes:
    chunks = []
    remaining = PROMPT_MAX_BYTES + 1
    while remaining:
        chunk = os.read(fd, min(remaining, 1024 * 1024))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def observe_prompt(path: Path, root: Path | None = None) -> dict:
    """Bound one regular descriptor observation below a trusted root.

    The optional root preserves direct callers (their parent is the anchor).
    POSIX walks lexical parents by descriptor. The path fallback checks links
    and opened identity, but retains a directory-component swap window on
    native Windows; neither branch promises a total filesystem I/O deadline.
    """
    result = {"exists": True, "regular": True, "linked": False}
    parent_fd = fd = None
    observed = False
    try:
        path = Path(path)
        root = Path(root) if root is not None else path.parent
        lexical_root = Path(os.path.abspath(root))
        candidate = path if path.is_absolute() else Path(os.path.abspath(path))
        parts = candidate.relative_to(lexical_root).parts
        if not parts or ".." in parts:
            result["error"] = "OutsideRoot"
            return result
        trusted_root = lexical_root.resolve(strict=True)
        current = trusted_root
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
        if _DIR_FD_SUPPORTED:
            parent_fd = os.open(trusted_root, flags | os.O_DIRECTORY | os.O_NOFOLLOW)
        for name in parts[:-1]:
            current = current / name
            try:
                entry = (os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                         if parent_fd is not None else os.lstat(current))
            except FileNotFoundError:
                return {"exists": False}
            observed = True
            if _linked_entry(entry):
                result["linked"] = True
                return result
            if not stat.S_ISDIR(entry.st_mode):
                result["error"] = "NotADirectoryError"
                return result
            if parent_fd is not None:
                next_fd = os.open(name, flags | os.O_DIRECTORY | os.O_NOFOLLOW,
                                  dir_fd=parent_fd)
                try:
                    opened_parent = os.fstat(next_fd)
                except BaseException:
                    os.close(next_fd)
                    raise
                if not _same_entry(entry, opened_parent):
                    os.close(next_fd)
                    result["error"] = "ChangedIdentity"
                    return result
                os.close(parent_fd)
                parent_fd = next_fd
        target = current / parts[-1]
        try:
            entry = (os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
                     if parent_fd is not None else os.lstat(target))
        except FileNotFoundError:
            return {"exists": False}
        observed = True
        result.update(linked=_linked_entry(entry), regular=stat.S_ISREG(entry.st_mode))
        if result["linked"] or not result["regular"]:
            return result
        if parent_fd is not None:
            fd = os.open(parts[-1], flags | os.O_NOFOLLOW, dir_fd=parent_fd)
        else:
            fd = os.open(target, flags | getattr(os, "O_BINARY", 0)
                         | getattr(os, "O_NOINHERIT", 0))
        opened = os.fstat(fd)
        after = (os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
                 if parent_fd is not None else os.lstat(target))
        if (_linked_entry(after) or not stat.S_ISREG(opened.st_mode)
                or not stat.S_ISREG(after.st_mode)
                or not _same_entry(entry, opened) or not _same_entry(after, opened)):
            result["error"] = "ChangedIdentity"
            return result
        raw = _read_prompt_bytes(fd)
        if len(raw) > PROMPT_MAX_BYTES:
            result["error"] = "SizeLimit"
        else:
            result["bytes"] = raw
    except FileNotFoundError:
        if not observed:
            return {"exists": False}
        result["error"] = "ChangedIdentity"
    except (OSError, ValueError, RuntimeError, MemoryError) as exc:
        result["error"] = type(exc).__name__
    finally:
        if fd is not None:
            os.close(fd)
        if parent_fd is not None:
            os.close(parent_fd)
    return result


def check_review_plan_prompt(root: Path) -> dict:
    return classify_review_plan_prompt(observe_prompt(root / REVIEW_PLAN_OLD_PROMPT, root),
                                      observe_prompt(root / REVIEW_PLAN_NEW_PROMPT, root))
