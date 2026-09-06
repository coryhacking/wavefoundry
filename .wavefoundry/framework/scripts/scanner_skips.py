"""Durable guard-skip observations; missing history is not coverage proof."""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import tempfile

from runtime_lock import RuntimeFileLock


LEDGER_REL = ".wavefoundry/index/scan/guard-skips.json"


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
