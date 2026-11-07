"""Durable guard-skip observations; missing history is not coverage proof."""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import tempfile

from runtime_lock import RuntimeFileLock


LEDGER_REL = ".wavefoundry/index/scan/guard-skips.json"
INTENTIONAL_SKIP_REASONS = frozenset({"binary file", "binary file (extension)"})
# Fixed input limits checked before detection. Rescanning cannot clear them;
# they are failures, not exclusions, until the file changes or is excluded.
FILE_TOO_LARGE_REASON = "file too large"
DECODED_TOO_LARGE_REASON = "decoded content too large"
TOO_MANY_LINES_REASON = "too many lines"
FIXED_LIMIT_REASONS = frozenset({
    FILE_TOO_LARGE_REASON, DECODED_TOO_LARGE_REASON, TOO_MANY_LINES_REASON,
})
_PROJECT_RULES_REL = "docs/scan-rules.toml"


def incomplete_rows(rows: list[dict]) -> list[dict]:
    """Policy omissions are disclosed separately from failed eligible scans."""
    return [row for row in rows if row.get("reason") not in INTENTIONAL_SKIP_REASONS]


def _toml_string(text: str) -> str:
    """Quote *text* as a TOML string that parses back to exactly *text*."""
    if "'" not in text and not any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in text):
        return "'" + text + "'"  # A literal string keeps regex escapes readable.
    quoted = ['"']
    for ch in text:
        if ch in '"\\':
            quoted.append("\\" + ch)
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            quoted.append(f"\\u{ord(ch):04X}")
        else:
            quoted.append(ch)
    quoted.append('"')
    return "".join(quoted)


def allowlist_entry(rel: str) -> str:
    """The TOML array element that excludes exactly *rel* and no other path."""
    import re

    return _toml_string("^" + re.escape(rel) + "$")


def _remedy(entry: str) -> str:
    return (
        "Rescanning alone will not clear a fixed scanner input limit. Convert or split "
        "the file, or, after confirming it holds no secrets, add "
        f"{entry} to the project [allowlist] paths in {_PROJECT_RULES_REL}."
    )


def fixed_limit_remedy(row: dict) -> str | None:
    """Remedy for a fixed-limit incomplete row; None keeps a reason's own text.

    This is the one projection every ``[scan-incomplete]`` producer uses: the
    completion row names the exact entry, and summaries stay path-free.
    """
    if row.get("reason") not in FIXED_LIMIT_REASONS:
        return None
    rel = row.get("file")
    if not isinstance(rel, str) or not rel:
        return _remedy("an entry anchored to that one path ('^' + escaped path + '$')")
    return _remedy(allowlist_entry(rel))


def incomplete_guidance(rows: list[dict], retry: str = "inspect completion details and retry.") -> str:
    """Closing guidance for a ``[scan-incomplete]`` summary of *rows*.

    Without a fixed-limit row the producer's own *retry* text is unchanged.
    """
    incomplete = incomplete_rows(rows)
    fixed = {row["file"] for row in incomplete if fixed_limit_remedy(row)}
    other = {row["file"] for row in incomplete} - fixed
    if not fixed:
        return retry
    remedy = fixed_limit_remedy({"reason": FILE_TOO_LARGE_REASON})
    rest = " Inspect completion details and retry the other file(s)." if other else ""
    return (f"{len(fixed)} of them exceed a fixed scanner input limit. {remedy} "
            f"Each file's completion details name its exact entry.{rest}")


def incomplete_paths(root: Path) -> set[str]:
    """Return validated outstanding retry candidates, including absent paths.

    The scanner owns current-policy and removal reconciliation. A malformed
    ledger supplies no paths and still fails the completion assessment.
    """
    return {row["file"] for row in incomplete_rows(
        scanner_skip_notice(root).get("scanner_skips", []))}


def _validate_path(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or "\0" in value
        or PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).drive
        or any(part in ("", ".", "..") for part in value.split("/"))
    ):
        raise ValueError("scanner skip path must be repository-relative")
    return value


def is_recordable_path(value: object) -> bool:
    """True when the ledger can name this path; the scanner warns about the rest."""
    try:
        _validate_path(value)
    except ValueError:
        return False
    return True


def _validate_rows(rows: object) -> list[dict]:
    if not isinstance(rows, list):
        raise ValueError("scanner skip reasons must be a list")
    result = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != {"reason", "detail"}
            or not isinstance(row["reason"], str)
            or not row["reason"]
            or not isinstance(row["detail"], str)
        ):
            raise ValueError("invalid scanner skip reason")
        # Set-keyed dedupe keeps the reader linear in rows; a list membership
        # test was quadratic and a hostile ledger could stall close and scans.
        key = (row["reason"], row["detail"])
        if key not in seen:
            seen.add(key)
            result.append({"reason": row["reason"], "detail": row["detail"]})
    return sorted(result, key=lambda row: (row["reason"], row["detail"]))


def _read_files(path: Path) -> dict[str, list[dict]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except RecursionError:
        # The C decoder raises this on pathological nesting. It is a malformed
        # ledger, not a crash: both the close reader and the scanner must take
        # their advisory paths rather than propagate it.
        raise ValueError("invalid scanner skip ledger") from None
    if (
        not isinstance(payload, dict)
        or set(payload) != {"version", "files"}
        or type(payload["version"]) is not int
        or payload["version"] != 1
        or not isinstance(payload["files"], dict)
    ):
        raise ValueError("invalid scanner skip ledger")
    files = {}
    for rel, rows in payload["files"].items():
        rel = _validate_path(rel)
        files[rel] = _validate_rows(rows)
        if not files[rel]:
            raise ValueError("scanner skip ledger contains an empty observation")
    return files


def update_scanner_skips(root: Path, outcomes: dict[str, dict]) -> None:
    """Merge evaluated paths, raising publication errors without replacing history.

    Complete, guard-free scans clear their path. Incomplete scans without guards
    retain it. Paths absent from the delta are retained unless lstat confirms that
    they no longer exist. The lock spans metadata checks and publication only;
    callers must finish content scanning before passing their delta here.
    """
    delta = {}
    for rel, outcome in outcomes.items():
        rel = _validate_path(rel)
        if (
            not isinstance(outcome, dict)
            or type(outcome.get("complete")) is not bool
            or not isinstance(outcome.get("skips"), list)
        ):
            raise ValueError("invalid scanner outcome")
        rows = []
        for row in outcome["skips"]:
            if not isinstance(row, dict) or set(row) != {"file", "reason", "detail"} or row["file"] != rel:
                raise ValueError("invalid scanner outcome skip")
            rows.append({"reason": row["reason"], "detail": row["detail"]})
        delta[rel] = (outcome["complete"], _validate_rows(rows))

    path = root / LEDGER_REL
    # Do not create a lock or index directories on a clean first scan.
    if not any(rows for _, rows in delta.values()):
        try:
            path.stat()
        except FileNotFoundError:
            return

    with RuntimeFileLock(path.with_suffix(".lock"), blocking=True):
        previous = _read_files(path)
        files = dict(previous)
        for rel, (complete, rows) in delta.items():
            if rows:
                files[rel] = rows
            elif complete:
                files.pop(rel, None)
        for rel in list(files):
            try:
                (root / rel).lstat()
            except FileNotFoundError:
                files.pop(rel)
            except OSError:
                # Permission failures and other I/O errors do not prove removal.
                pass
        if files == previous:
            return
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=".guard-skips-", suffix=".tmp", delete=False,
            ) as stream:
                temporary = Path(stream.name)
                json.dump({"version": 1, "files": files}, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def scanner_skip_notice(root: Path) -> dict:
    """Read outstanding observations without scanning, pruning, or writing."""
    try:
        files = _read_files(root / LEDGER_REL)
    except (OSError, ValueError):
        return {
            "scanner_skips_error": "Scanner coverage unavailable: guard-skip ledger is malformed or unreadable."
        }
    rows = [{"file": rel, **row} for rel in sorted(files) for row in files[rel]]
    return {"scanner_skips": rows} if rows else {}


def scanner_completion(root: Path, failures=(), *, limit: int = 50) -> dict:
    """Project outstanding coverage facts, never claim a whole-tree scan ran.

    Missing history means no recorded failures, not proof of prior coverage.
    Consumers combine this with their actual scan scope and current failures.
    """
    notice = scanner_skip_notice(root)
    rows = notice.get("scanner_skips", [])
    incomplete = [
        {**row, "remedy": remedy} if (remedy := fixed_limit_remedy(row)) else row
        for row in incomplete_rows(rows)
    ]
    error = notice.get("scanner_skips_error")
    current_error = any("[secrets]" not in failure for failure in failures)
    return {
        "complete": not (incomplete or error or current_error),
        "completion_scope": "requested scan and recorded outstanding failures",
        "incomplete_files": len({row["file"] for row in incomplete}),
        "incomplete": incomplete[:limit],
        "incomplete_omitted": max(0, len(incomplete) - limit),
        "policy_excluded_files": len({row["file"] for row in rows
                                      if row["reason"] in INTENTIONAL_SKIP_REASONS}),
        **({"coverage_error": error} if error else {}),
    }


def scanner_completion_failures(root: Path) -> list[str]:
    coverage = scanner_completion(root)
    if coverage.get("coverage_error"):
        return ["[scan-incomplete] Scanner coverage history is malformed or unreadable; restore it and rerun the scan."]
    if coverage["incomplete_files"]:
        rows = scanner_skip_notice(root).get("scanner_skips", [])
        guidance = incomplete_guidance(rows, "inspect scanner completion details and retry.")
        return [f"[scan-incomplete] {coverage['incomplete_files']} eligible file(s) have unresolved incomplete scans; {guidance}"]
    return []
