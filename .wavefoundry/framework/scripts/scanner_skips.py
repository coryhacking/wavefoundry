"""Durable guard-skip observations; missing history is not coverage proof."""

from __future__ import annotations

import json
import os
import re
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
    """The TOML array element that excludes exactly *rel* and no other path.

    ``\\z`` is end of text in RE2, so it is exact on the upstream matcher; ``$`` would also
    match before a trailing newline on Python's. Python 3.14 reads ``\\z`` natively and older
    interpreters reach it through the matcher's RE2 translation (wave 22u26, change 22qr7).
    """
    import re

    return _toml_string("^" + re.escape(rel) + "\\z")


def _remedy(entry: str) -> str:
    return (
        "Rescanning alone will not clear a fixed scanner input limit. Convert or split "
        "the file, or, after confirming it holds no secrets, add "
        f"{entry} to the project [allowlist] paths in {_PROJECT_RULES_REL}."
    )


# Change 22r96: deterministic work limits reached during detection. The scanner
# records one of these fixed details, chosen by exact membership, never by
# copying worker text. Rescanning the same content reaches the same limit.
UPSTREAM_INCOMPLETE_REASON = "upstream scan incomplete"
MATCH_LIMIT_DETAIL = "match_limit"
RESULT_LIMIT_DETAIL = "result_limit"
COMPONENT_SET_LIMIT_DETAIL = "component_set_limit"
RESPONSE_TOO_LARGE_DETAIL = "worker_response_too_large"
WORK_LIMIT_DETAILS = frozenset({
    MATCH_LIMIT_DETAIL, RESULT_LIMIT_DETAIL, COMPONENT_SET_LIMIT_DETAIL, RESPONSE_TOO_LARGE_DETAIL,
})
# When the engine reports several limits, the first in this order names the
# row: a raised limit (no findings returned) outranks the composite-set limit.
WORK_LIMIT_PRECEDENCE = (RESULT_LIMIT_DETAIL, MATCH_LIMIT_DETAIL, COMPONENT_SET_LIMIT_DETAIL)
# A scan-time timeout may depend on load; a path-check timeout happens in the
# check that would evaluate a path entry, so it is recorded separately.
SCAN_TIMEOUT_DETAIL = "worker_timeout"
PATH_CHECK_TIMEOUT_DETAIL = "path_check_worker_timeout"


def work_limit_detail(diagnostics: object) -> str | None:
    """The fixed detail for the first known work-limit token, else None."""
    if not isinstance(diagnostics, list):
        return None
    present = {token for token in diagnostics if isinstance(token, str)}
    return next((detail for detail in WORK_LIMIT_PRECEDENCE if detail in present), None)


def _add_entry(entry: str) -> str:
    return f"add {entry} to the project [allowlist] paths in {_PROJECT_RULES_REL}"


def _work_limit_remedy(detail: str, entry: str) -> str:
    if detail == MATCH_LIMIT_DETAIL:
        return ("Rescanning alone will not clear a fixed scanner work limit: the file produced "
                "more raw rule matches than one scan evaluates. Convert or split the file, or, "
                f"after confirming it holds no secrets, {_add_entry(entry)}.")
    if detail == COMPONENT_SET_LIMIT_DETAIL:
        return ("Rescanning alone will not clear a fixed scanner work limit: the scan stopped "
                "combining related findings. The findings it reported stand, and a path entry "
                "would also suppress them. Resolve the reported findings, or narrow the rule, "
                f"first; only after confirming they are false positives, {_add_entry(entry)}.")
    return ("Rescanning alone will not clear a fixed scanner work limit: the file holds more "
            "candidate findings, after filtering, than one scan can return, so none are shown "
            "and they are unreviewed candidate secrets. Split the file and rescan the parts so "
            f"the findings appear; only after those findings are reviewed, {_add_entry(entry)}.")


def _scan_timeout_guidance(entry: str) -> str:
    return ("The scan of this file timed out. Retry the scan first. If it times out again on "
            "unchanged content, convert or split the file, or, after confirming it holds no "
            f"secrets, {_add_entry(entry)}.")


PATH_CHECK_TIMEOUT_GUIDANCE = (
    "The path-exclusion check for this file timed out. Retry the scan; a path entry cannot "
    "clear this, because the same check evaluates it."
)


def _is_fixed_limit(row: dict) -> bool:
    """Input or work limits; timeouts are never counted as fixed limits."""
    if row.get("reason") in FIXED_LIMIT_REASONS:
        return True
    return row.get("reason") == UPSTREAM_INCOMPLETE_REASON and row.get("detail") in WORK_LIMIT_DETAILS


def fixed_limit_remedy(row: dict) -> str | None:
    """Per-row remedy for an incomplete row; None keeps a reason's own text.

    This is the one projection every ``[scan-incomplete]`` producer uses: the
    completion row names the exact entry, and summaries stay path-free.
    Input limits, work limits and worker timeouts each get their own text.
    """
    reason, detail = row.get("reason"), row.get("detail")
    upstream = reason == UPSTREAM_INCOMPLETE_REASON
    if reason not in FIXED_LIMIT_REASONS and not (
            upstream and detail in WORK_LIMIT_DETAILS | {SCAN_TIMEOUT_DETAIL, PATH_CHECK_TIMEOUT_DETAIL}):
        return None
    if upstream and detail == PATH_CHECK_TIMEOUT_DETAIL:
        return PATH_CHECK_TIMEOUT_GUIDANCE
    rel = row.get("file")
    if not isinstance(rel, str) or not rel:
        entry = "an entry anchored to that one path ('^' + escaped path + '\\z')"
    else:
        entry = allowlist_entry(rel)
    if upstream and detail == SCAN_TIMEOUT_DETAIL:
        return _scan_timeout_guidance(entry)
    if upstream:
        return _work_limit_remedy(detail, entry)
    return _remedy(entry)


def incomplete_guidance(rows: list[dict], retry: str = "inspect completion details and retry.") -> str:
    """Closing guidance for a ``[scan-incomplete]`` summary of *rows*.

    Without a fixed-limit row the producer's own *retry* text is unchanged.
    Worker timeouts are retry candidates here, never fixed limits.
    """
    incomplete = incomplete_rows(rows)
    inputs = {row["file"] for row in incomplete if row.get("reason") in FIXED_LIMIT_REASONS}
    work = {row["file"] for row in incomplete if _is_fixed_limit(row)} - inputs
    other = {row["file"] for row in incomplete} - inputs - work
    if not inputs and not work:
        return retry
    parts = []
    if inputs:
        remedy = fixed_limit_remedy({"reason": FILE_TOO_LARGE_REASON})
        parts.append(f"{len(inputs)} of them exceed a fixed scanner input limit. {remedy} "
                     "Each file's completion details name its exact entry.")
    if work:
        parts.append(f"{len(work)} of them reached a fixed scanner work limit, which rescanning "
                     "alone will not clear; each file's completion details give its remedy and exact entry.")
    rest = " Inspect completion details and retry the other file(s)." if other else ""
    return " ".join(parts) + rest


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


def _scan_history_path(root: Path) -> Path:
    # Derive from the existing profile-owned scanner location; forks rename one owner.
    return (root / LEDGER_REL).with_name("scan-history.json")


def _read_scan_history(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("scan history too large")
        value = json.loads(raw)
    except RecursionError:
        raise ValueError("invalid scan history") from None
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("invalid scan history")
    for key in ("latest_run", "last_full"):
        row = value.get(key)
        if row is None and key == "last_full":
            continue
        if (not isinstance(row, dict)
                or row.get("scope") not in {"full", "incremental"}
                or (key == "last_full" and row["scope"] != "full")
                or type(row.get("complete")) is not bool
                or type(row.get("requested_files")) is not int or row["requested_files"] < 1
                or not isinstance(row.get("scanner_version"), str)
                or not re.fullmatch(r"[0-9]{1,10}", row["scanner_version"])
                or not isinstance(row.get("rules_hash"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", row["rules_hash"])
                or not isinstance(row.get("scanned_at"), str)):
            raise ValueError("invalid scan history observation")
        from datetime import datetime
        stamp = datetime.fromisoformat(row["scanned_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("scan timestamp has no timezone")
        row["scanned_at"] = stamp.isoformat()
    return value


def publish_scan_history(root: Path, *, scope: str, requested_files: int,
                         complete: bool, scanned_at: str, rules_hash: str | None = None) -> None:
    """Publish one executed scan observation atomically; never refresh on no work."""
    if not requested_files:
        return
    if scope not in {"full", "incremental"} or type(requested_files) is not int or requested_files < 0 or type(complete) is not bool:
        raise ValueError("invalid scan observation")
    import indexer
    scanner = indexer._get_secrets_scanner()
    if scanner is None:
        raise ValueError("scanner identity unavailable")
    row = {"scanned_at": scanned_at, "scope": scope,
           "requested_files": requested_files, "complete": complete,
           "scanner_version": scanner.SCANNER_VERSION, "rules_hash": rules_hash if rules_hash is not None else scanner._compute_rules_hash(root)}
    path = _scan_history_path(root)
    with RuntimeFileLock(path.with_suffix(".lock"), blocking=True):
        try:
            previous = _read_scan_history(path)
        except FileNotFoundError:
            previous = {}
        # Malformed prior observations are not silently overwritten with a fresh health claim.
        state = {"version": 1, "latest_run": row,
                 "last_full": row if scope == "full" else previous.get("last_full")}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             prefix=".scan-history-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(state, stream, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def scan_history(root: Path) -> dict:
    """Read allowlisted, machine-local observations without scanning or writing."""
    out = {"available": False, "machine_local": True, "latest_run": None, "last_full": None,
           "qualification": "Historical observations on this machine, not shared history or proof that the current tree is clean."}
    try:
        state = _read_scan_history(_scan_history_path(root))
    except FileNotFoundError:
        return {**out, "reason": "scan_history_missing"}
    except (OSError, ValueError, TypeError, OverflowError):
        return {**out, "reason": "scan_history_unreadable_or_invalid"}
    try:
        import indexer
        scanner = indexer._get_secrets_scanner()
        rules_hash = scanner._compute_rules_hash(root) if scanner is not None else None
    except Exception:
        rules_hash = None
    for key in ("latest_run", "last_full"):
        row = state.get(key)
        if row is not None:
            out[key] = {name: row[name] for name in (
                "scanned_at", "scope", "requested_files", "complete", "scanner_version")}
            out[key]["rules_current"] = row["rules_hash"] == rules_hash if rules_hash is not None else None
            out[key]["scope_note"] = ("Full requested candidate scope under the recorded rules and exclusions; not all repository bytes."
                                      if row["scope"] == "full" else "Requested incremental file scope only.")
    out["available"] = True
    return out
