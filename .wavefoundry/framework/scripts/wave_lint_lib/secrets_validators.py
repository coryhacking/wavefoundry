from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

from .cel_filter import eval_filter
from .constants import SCAN_ALLOWLIST_PATH, SCAN_FINDINGS_PATH, SCAN_RULES_FRAMEWORK_PATH, SCAN_RULES_PROJECT_PATH

_INLINE_SUPPRESS_RE = re.compile(r"#\s*wavefoundry-ignore:\s*secrets(.*)")


# ---------------------------------------------------------------------------
# TOML loading
# ---------------------------------------------------------------------------

def _require_tomllib() -> bool:
    if tomllib is None:
        return False
    return True


def _load_toml(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_merged_ruleset(root: Path) -> tuple[list[dict], dict, list[str]]:
    """Return (rules, policy, errors).

    rules: merged list of rule dicts from framework + project files.
    policy: merged policy dict (project overrides framework).
    errors: fatal diagnostic messages if tomllib is unavailable or files are corrupt.
    """
    if not _require_tomllib():
        return [], {}, [
            "secrets scan requires tomllib (Python >= 3.11) or the tomli package; "
            "run: pip install tomli"
        ]

    framework_path = root / SCAN_RULES_FRAMEWORK_PATH
    if not framework_path.exists():
        # Silent no-op: ruleset absent means this project hasn't installed secrets scanning yet.
        return [], {}, []

    try:
        fw_data = _load_toml(framework_path)
    except Exception as exc:
        return [], {}, [f"secrets scan: failed to parse {SCAN_RULES_FRAMEWORK_PATH}: {exc}"]

    rules: list[dict] = list(fw_data.get("rules", []))
    policy: dict = dict(fw_data.get("policy", {}))
    global_allowlist: dict = fw_data.get("allowlist", {})

    project_path = root / SCAN_RULES_PROJECT_PATH
    if project_path.exists():
        try:
            proj_data = _load_toml(project_path)
        except Exception as exc:
            return [], {}, [f"secrets scan: failed to parse {SCAN_RULES_PROJECT_PATH}: {exc}"]

        proj_policy = proj_data.get("policy", {})
        policy.update(proj_policy)

        disabled = set(proj_policy.get("disabled_rules", []))
        if disabled:
            rules = [r for r in rules if r.get("id") not in disabled]

        proj_rules = proj_data.get("rules", [])
        existing_ids = {r.get("id") for r in rules}
        for r in proj_rules:
            rid = r.get("id")
            if rid and rid in existing_ids:
                rules = [r if r.get("id") != rid else r for r in rules]
            else:
                rules.append(r)

    return rules, policy, []


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def _is_inside_git(root: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=root, capture_output=True, text=True
    )
    return result.returncode == 0


def _head_exists(root: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=root, capture_output=True, text=True
    )
    return result.returncode == 0


def _get_changed_files(root: Path) -> list[Path]:
    # Tracked files changed since HEAD (staged + unstaged)
    changed = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=root, capture_output=True, text=True
    )
    # Untracked files that are not gitignored (new files not yet staged)
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=root, capture_output=True, text=True
    )
    if changed.returncode != 0 and untracked.returncode != 0:
        return []
    seen: set[Path] = set()
    paths: list[Path] = []
    for line in (changed.stdout + untracked.stdout).splitlines():
        line = line.strip()
        if line:
            p = root / line
            if p.exists() and p.is_file() and p not in seen:
                seen.add(p)
                paths.append(p)
    return paths


def _get_all_files(root: Path) -> list[Path]:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=root, capture_output=True, text=True
    )
    if tracked.returncode != 0:
        # Fallback: walk the tree excluding .git/
        paths = []
        for p in root.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                paths.append(p)
        return paths

    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=root, capture_output=True, text=True
    )
    seen: set[Path] = set()
    paths: list[Path] = []
    for line in (tracked.stdout + untracked.stdout).splitlines():
        line = line.strip()
        if line:
            p = root / line
            if p.exists() and p.is_file() and p not in seen:
                seen.add(p)
                paths.append(p)
    return paths


def get_scan_files(root: Path, scan_all: bool = False) -> list[Path]:
    if scan_all:
        return _get_all_files(root)
    if _is_inside_git(root) and _head_exists(root):
        changed = _get_changed_files(root)
        return changed if changed is not None else _get_all_files(root)
    return _get_all_files(root)


# ---------------------------------------------------------------------------
# Path allowlist matching
# ---------------------------------------------------------------------------

def _path_matches_allowlist(rel_path: str, allowlist_paths: list[str]) -> bool:
    for pattern in allowlist_paths:
        try:
            if re.search(pattern, rel_path):
                return True
        except re.error:
            pass
    return False


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

def redact(text: str) -> str:
    if len(text) <= 8:
        return "****"
    return f"{text[:4]}****{text[-4:]}"


# ---------------------------------------------------------------------------
# Inline suppression
# ---------------------------------------------------------------------------

def check_inline_suppression(line: str) -> tuple[bool, str | None]:
    """Return (suppressed, error_or_none).

    suppressed=True, error=None → valid inline suppression with reason.
    suppressed=True, error=str → bare suppression (no reason) — itself a failure.
    suppressed=False, error=None → no suppression marker present.
    """
    m = _INLINE_SUPPRESS_RE.search(line)
    if not m:
        return False, None
    reason = m.group(1).strip()
    if not reason:
        return True, "bare wavefoundry-ignore: secrets suppression without a reason is a lint failure"
    return True, None


# ---------------------------------------------------------------------------
# Git identity
# ---------------------------------------------------------------------------

def get_current_git_user_email(root: Path) -> str:
    result = subprocess.run(
        ["git", "config", "user.email"],
        cwd=root, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else ""


# ---------------------------------------------------------------------------
# Exceptions file
# ---------------------------------------------------------------------------

def load_exceptions(root: Path) -> list[dict]:
    path = root / SCAN_FINDINGS_PATH
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


_OMIT_WHEN_EMPTY: frozenset[str] = frozenset({"override_reason", "acknowledged_for_wave", "confirmations"})


def _strip_empty_fields(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if k not in _OMIT_WHEN_EMPTY or v}


def save_exceptions(root: Path, exceptions: list[dict]) -> None:
    path = root / SCAN_FINDINGS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = [_strip_empty_fields(e) for e in exceptions]
    path.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _next_exception_id(exceptions: list[dict]) -> str:
    existing = set()
    for e in exceptions:
        eid = e.get("id", "")
        if isinstance(eid, str) and eid.startswith("exc-"):
            try:
                existing.add(int(eid[4:]))
            except ValueError:
                pass
    n = 1
    while n in existing:
        n += 1
    return f"exc-{n:03d}"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_framework_scan_allowlist(root: Path) -> set[str]:
    """Load the shipped framework scan allowlist from .wavefoundry/framework/scan-allowlist.

    Returns a set of strings in the format '<sha256>:<rel_path>:<rule_id>:<line_hash>'.
    Lines starting with '#' and blank lines are ignored.
    """
    path = root / SCAN_ALLOWLIST_PATH
    if not path.exists():
        return set()
    entries: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.add(line)
    return entries


def _hash_line(line: str) -> str:
    return hashlib.md5(line.strip().encode("utf-8")).hexdigest()[:12]


def _hash_context(lines: list[str], line_no: int) -> str:
    """Hash of the matched line plus its immediate neighbors (±1, clamped to file bounds)."""
    n = len(lines)
    idx = line_no - 1  # convert to 0-indexed
    start = max(0, idx - 1)
    end = min(n - 1, idx + 1)
    combined = "\n".join(line.strip() for line in lines[start : end + 1])
    return hashlib.md5(combined.encode("utf-8")).hexdigest()[:12]


def _find_exception(
    exceptions: list[dict],
    rel_path: str,
    line_no: int,
    rule_id: str,
    matched_ids: set[str],
    current_line_hash: str | None = None,
    current_context_hash: str | None = None,
) -> tuple[dict | None, bool]:
    """Return (exception_or_None, line_was_updated).

    Tries exact (file, line, rule_id) match first. Falls back to hash matching
    when the line has drifted: finds entries with matching line_hash for this
    file+rule, using context_hash to disambiguate when multiple entries share
    the same line hash. Updates the entry's line field in place when drifted.

    matched_ids tracks exceptions already consumed in this file scan so that
    an exact match for one line cannot also be claimed by a hash fallback for
    a second identical line in the same file.
    """
    # Exact match
    for e in exceptions:
        if e.get("file") == rel_path and e.get("line") == line_no and e.get("rule_id") == rule_id:
            matched_ids.add(e.get("id", ""))
            return e, False
    if not current_line_hash:
        return None, False
    # Hash fallback — skip exceptions already consumed by an earlier exact match
    candidates = [
        e for e in exceptions
        if e.get("file") == rel_path
        and e.get("rule_id") == rule_id
        and e.get("line_hash") == current_line_hash
        and e.get("id") not in matched_ids
    ]
    if not candidates:
        return None, False
    if len(candidates) == 1:
        candidates[0]["line"] = line_no
        matched_ids.add(candidates[0].get("id", ""))
        return candidates[0], True
    # Multiple candidates share the same line_hash — use context_hash to disambiguate
    if current_context_hash:
        for e in candidates:
            if e.get("context_hash") == current_context_hash:
                e["line"] = line_no
                matched_ids.add(e.get("id", ""))
                return e, True
    return None, False


def _sweep_stale_exceptions(exceptions: list[dict], rel_path: str, lines: list[str]) -> bool:
    """Remove exceptions for rel_path whose line_hash no longer appears anywhere in the file.

    Only sweeps entries that have a stored line_hash. Entries without line_hash (created
    before this feature) are left untouched for backward compatibility.
    Returns True if any entries were removed.
    """
    file_hashes = {_hash_line(line) for line in lines}
    to_remove = [
        e for e in exceptions
        if e.get("file") == rel_path
        and e.get("line_hash")
        and e.get("line_hash") not in file_hashes
    ]
    for e in to_remove:
        exceptions.remove(e)
    return bool(to_remove)


# ---------------------------------------------------------------------------
# Confirmation count logic
# ---------------------------------------------------------------------------

def _unique_confirmation_count(entry: dict) -> tuple[int, list[str]]:
    """Return (unique_email_count, list_of_confirmer_names)."""
    seen_emails: set[str] = set()
    names: list[str] = []
    for c in entry.get("confirmations", []):
        email = c.get("git_user_email", "")
        if email and email not in seen_emails:
            seen_emails.add(email)
            name = c.get("git_user_name", email)
            names.append(name)
    return len(seen_emails), names


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

# Minimum file count before the parallel scan path is engaged.
_PARALLEL_SCAN_THRESHOLD = 50

# Module-level globals populated by _worker_init_secrets_scanner in spawned
# worker processes. Always None in the parent process.
_WORKER_COMPILED_RULES: list | None = None
_WORKER_GLOBAL_ALLOWLIST_PATHS: list[str] | None = None
_WORKER_FRAMEWORK_ALLOWLIST: set[str] | None = None


def _worker_init_secrets_scanner(
    scripts_dir: str,
    raw_rules: list,
    global_allowlist_paths: list,
    framework_allowlist_list: list,
) -> None:
    """ProcessPoolExecutor initializer for parallel secrets-scan workers.

    Fires once per worker process at startup, before the first task.
    Compiles rule patterns from raw data (list of tuples with pattern string)
    and caches them in module globals so scan_file_raw avoids per-task
    re-compilation — the dominant per-file cost on large rulesets.

    raw_rules: list of (rule_id, keywords, pattern_str, al_paths, al_regexes, cel_filter)
    framework_allowlist_list: framework allowlist entries as a list (set serialized for pickle).
    """
    global _WORKER_COMPILED_RULES, _WORKER_GLOBAL_ALLOWLIST_PATHS, _WORKER_FRAMEWORK_ALLOWLIST
    import sys as _sys, re as _re
    if scripts_dir not in _sys.path:
        _sys.path.insert(0, scripts_dir)
    compiled = []
    for rule_id, keywords, pattern_str, al_paths, al_regexes, cel_filter_expr in raw_rules:
        try:
            pattern = _re.compile(pattern_str)
        except _re.error:
            continue
        compiled.append((rule_id, keywords, pattern, al_paths, al_regexes, cel_filter_expr))
    _WORKER_COMPILED_RULES = compiled
    _WORKER_GLOBAL_ALLOWLIST_PATHS = global_allowlist_paths
    _WORKER_FRAMEWORK_ALLOWLIST = set(framework_allowlist_list)
    # ppid watchdog — same pattern as graph_indexer: daemon thread polls
    # os.getppid() and exits if the parent dies to avoid orphan workers on macOS.
    try:
        import threading as _t, time as _time, os as _os
        def _ppid_watchdog() -> None:
            try:
                orig_ppid = _os.getppid()
            except Exception:
                return
            while True:
                _time.sleep(2.0)
                try:
                    cur_ppid = _os.getppid()
                except Exception:
                    return
                if cur_ppid != orig_ppid or cur_ppid == 1:
                    try:
                        print(
                            f"secrets-scan: [worker pid={_os.getpid()}] parent died "
                            f"(ppid {orig_ppid} -> {cur_ppid}); exiting",
                            file=_sys.stderr, flush=True,
                        )
                    except Exception:
                        pass
                    _os._exit(0)
        _t.Thread(target=_ppid_watchdog, daemon=True, name="ppid-watchdog").start()
    except Exception:
        pass


def _scan_file_secrets_worker(args: tuple) -> tuple:
    """Worker task: scan one file using initializer-compiled globals."""
    file_path_str, rel = args
    from pathlib import Path as _Path
    return scan_file_raw(
        _Path(file_path_str), rel,
        _WORKER_COMPILED_RULES,
        _WORKER_GLOBAL_ALLOWLIST_PATHS,
        _WORKER_FRAMEWORK_ALLOWLIST,
    )


def _scan_file_secrets_batch_worker(batch_args: list) -> list:
    """Worker task: scan a batch of files — amortizes IPC overhead per batch."""
    return [_scan_file_secrets_worker(args) for args in batch_args]


def scan_file_raw(
    file_path: Path,
    rel: str,
    compiled_rules: list,
    global_allowlist_paths: list[str],
    framework_allowlist: set[str],
) -> tuple[list[str], str | None, list[dict]]:
    """Scan a single file for raw rule hits. Thread-safe — no shared mutations.

    Returns (lines, file_sha256_or_None, raw_hits).
    raw_hits: one dict per match that survived CEL + allowlist filtering.
    suppress_error=None means a valid (non-suppressed) hit needing exception lookup.
    suppress_error set means a bare-suppression lint error to report as a failure.
    Cleanly suppressed lines (wavefoundry-ignore with a reason) are excluded entirely.
    """
    if _path_matches_allowlist(rel, global_allowlist_paths):
        return [], None, []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return [], None, []

    lines = content.splitlines()
    content_lower = content.lower()
    file_sha256 = _sha256_file(file_path) if framework_allowlist else None
    hits: list[dict] = []

    for rule_id, keywords, pattern, al_paths, al_regexes, cel_filter_expr in compiled_rules:
        if keywords and not any(kw in content_lower for kw in keywords):
            continue
        if _path_matches_allowlist(rel, al_paths):
            continue
        for line_no, line in enumerate(lines, start=1):
            m = pattern.search(line)
            if not m:
                continue
            matched_text = m.group(0)
            secret = m.group(1) if m.lastindex and m.lastindex >= 1 else matched_text
            if cel_filter_expr and eval_filter(cel_filter_expr, secret, matched_text, rel, line_no):
                continue
            skip = False
            for al_regex in al_regexes:
                try:
                    if re.search(al_regex, matched_text) or re.search(al_regex, line):
                        skip = True
                        break
                except re.error:
                    pass
            if skip:
                continue
            suppressed, suppress_error = check_inline_suppression(line)
            if suppressed and not suppress_error:
                continue  # valid suppression with reason — skip entirely
            redacted_match = redact(matched_text)
            redacted_line = (line[:m.start()] + redacted_match + line[m.end():]).strip()
            hits.append({
                "rule_id": rule_id,
                "line_no": line_no,
                "matched_text": matched_text,
                "redacted_match": redacted_match,
                "redacted_line": redacted_line,
                "line_hash": _hash_line(line),
                "context_hash": _hash_context(lines, line_no),
                "suppress_error": suppress_error,  # None → normal hit; str → lint error
            })

    return lines, file_sha256, hits


def _match_hits_for_file(
    rel: str,
    lines: list[str],
    file_sha256: str | None,
    hits: list[dict],
    exceptions: list[dict],
    framework_allowlist: set[str],
    required_confirmations: int,
    current_email: str,
) -> tuple[list[str], bool]:
    """Serial exception matching for one file's pre-scanned hits.

    Returns (failures, exceptions_changed).
    Mutates exceptions in place (appending new entries, updating line drift).
    """
    failures: list[str] = []
    exceptions_changed = False
    matched_ids: set[str] = set()

    for hit in hits:
        rule_id = hit["rule_id"]
        line_no = hit["line_no"]
        redacted_match = hit["redacted_match"]

        # Bare inline suppression (no reason) is a lint error, not a secret
        if hit["suppress_error"]:
            failures.append(f"{rel}:{line_no}: {hit['suppress_error']}")
            continue

        existing, line_drifted = _find_exception(
            exceptions, rel, line_no, rule_id, matched_ids,
            hit["line_hash"], hit["context_hash"],
        )
        if line_drifted:
            exceptions_changed = True

        if existing is None:
            # Check shipped framework allowlist before creating a pending entry.
            # Key is sha256:path:rule_id:line_hash — content-based so it survives
            # line number drift and handles identical lines at different positions.
            if file_sha256 and f"{file_sha256}:{rel}:{rule_id}:{hit['line_hash']}" in framework_allowlist:
                continue
            new_entry: dict[str, Any] = {
                "id": _next_exception_id(exceptions),
                "file": rel,
                "line": line_no,
                "line_hash": hit["line_hash"],
                "context_hash": hit["context_hash"],
                "rule_id": rule_id,
                "matched_text": hit["redacted_line"],
                "status": "pending",
            }
            exceptions.append(new_entry)
            exceptions_changed = True
            failures.append(
                f"{rel}:{line_no}: [secrets] new match for rule '{rule_id}' "
                f"— appended to {SCAN_FINDINGS_PATH} with status 'pending' "
                f"(matched: {redacted_match})"
            )
            continue

        status = existing.get("status", "pending")

        if status == "pending":
            failures.append(
                f"{rel}:{line_no}: [secrets] rule '{rule_id}' — "
                f"exception status is 'pending'; run security reviewer to classify "
                f"(matched: {redacted_match})"
            )

        elif status == "false-positive":
            count, names = _unique_confirmation_count(existing)
            if count >= required_confirmations:
                pass  # suppressed
            else:
                names_str = ", ".join(names) if names else "(none)"
                needed = required_confirmations - count
                if current_email and current_email in {
                    c.get("git_user_email", "") for c in existing.get("confirmations", [])
                }:
                    failures.append(
                        f"{rel}:{line_no}: [secrets] rule '{rule_id}' — "
                        f"{count} of {required_confirmations} confirmations received "
                        f"from: {names_str} — needs {needed} more from a different reviewer"
                    )
                else:
                    failures.append(
                        f"{rel}:{line_no}: [secrets] rule '{rule_id}' — "
                        f"unconfirmed false positive — {count} of {required_confirmations} "
                        f"confirmations. You are not yet on the list. "
                        f"Please review and confirm or escalate. "
                        f"(confirmed by: {names_str})"
                    )

        elif status == "suspected-secret":
            failures.append(
                f"{rel}:{line_no}: [secrets] rule '{rule_id}' — "
                f"status is 'suspected-secret'; security reviewer must analyze and classify "
                f"as 'false-positive' or 'confirmed-secret' (matched: {redacted_match})"
            )

        elif status == "confirmed-secret":
            failures.append(
                f"{rel}:{line_no}: [secrets] rule '{rule_id}' — "
                f"confirmed secret present; wave close requires per-wave acknowledgment "
                f"(matched: {redacted_match})"
            )

    # Sweep stale exceptions for this file (line removed or content changed)
    if lines and _sweep_stale_exceptions(exceptions, rel, lines):
        exceptions_changed = True

    return failures, exceptions_changed


def check_hardcoded_secrets(
    root: Path,
    scan_all: bool = False,
    files: list[Path] | None = None,
    max_workers: int = 1,
) -> list[str]:
    """Scan tracked/changed files for secrets matching the merged ruleset.

    Returns a list of error strings (empty = clean).

    files: when provided, scan exactly these files instead of calling get_scan_files().
           Used by the incremental indexer path to pass pre-computed changed-file sets.
    max_workers: worker count for the parallel scan phase (phase 1). Set > 1 to
           parallelise regex matching across cores using ProcessPoolExecutor (spawn
           start method + initializer pattern). Exception matching (phase 2) is always
           serial. Falls back to serial scan on any spawn/IPC error.
    """
    rules, policy, load_errors = load_merged_ruleset(root)
    if load_errors:
        return load_errors
    if not rules:
        return []

    required_confirmations: int = int(policy.get("false_positive_confirmations_required", 2))
    global_allowlist_paths: list[str] = []

    fw_path = root / SCAN_RULES_FRAMEWORK_PATH
    try:
        if _require_tomllib() and fw_path.exists():
            with open(fw_path, "rb") as f:
                fw_raw = tomllib.load(f)
            global_allowlist_paths = list(fw_raw.get("allowlist", {}).get("paths", []))
    except Exception:
        pass

    proj_path = root / SCAN_RULES_PROJECT_PATH
    try:
        if _require_tomllib() and proj_path.exists():
            with open(proj_path, "rb") as f:
                proj_raw = tomllib.load(f)
            global_allowlist_paths += list(proj_raw.get("allowlist", {}).get("paths", []))
    except Exception:
        pass

    exceptions = load_exceptions(root)
    exceptions_changed = False

    # Sweep findings for paths that now match the combined path allowlist.
    excluded = [e for e in exceptions if _path_matches_allowlist(e.get("file", ""), global_allowlist_paths)]
    if excluded:
        for e in excluded:
            exceptions.remove(e)
        exceptions_changed = True

    # Sweep findings for files that no longer exist on disk.
    deleted = [e for e in exceptions if not (root / e["file"]).exists()]
    if deleted:
        for e in deleted:
            exceptions.remove(e)
        exceptions_changed = True

    current_email = get_current_git_user_email(root)
    framework_allowlist = load_framework_scan_allowlist(root)

    # Pre-compile all rule patterns once — compiling per-file is the dominant cost.
    CompiledRule = tuple  # (rule_id, keywords, pattern, al_paths, al_regexes, cel_filter)
    compiled_rules: list[CompiledRule] = []
    for rule in rules:
        rule_id = rule.get("id", "")
        pattern_str = rule.get("regex", "")
        if not pattern_str:
            continue
        try:
            pattern = re.compile(pattern_str)
        except re.error:
            continue
        keywords = [kw.lower() for kw in rule.get("keywords", [])]
        al_paths_r: list[str] = []
        al_regexes_r: list[str] = []
        for al in rule.get("allowlists", []):
            al_paths_r.extend(al.get("paths", []))
            al_regexes_r.extend(al.get("regexes", []))
        cel_filter_expr = rule.get("filter", "")
        compiled_rules.append((rule_id, keywords, pattern, al_paths_r, al_regexes_r, cel_filter_expr))

    if files is None:
        files = get_scan_files(root, scan_all)

    # Build (file_path, rel) pairs, filtering non-existent and out-of-root paths.
    file_scan_list: list[tuple[Path, str]] = []
    for file_path in files:
        try:
            rel = str(file_path.relative_to(root))
        except ValueError:
            rel = str(file_path)
        file_scan_list.append((file_path, rel))

    # Phase 1: parallel file scanning via ProcessPoolExecutor (spawn + initializer).
    # Each worker receives compiled rules via the initializer (once per process)
    # rather than per-task — avoids redundant regex compilation across all files.
    # Falls back to serial on any spawn/IPC error.
    _worker_scan_args = [(str(fp), rel) for fp, rel in file_scan_list]

    def _serial_scan() -> list:
        return [
            scan_file_raw(fp, rel, compiled_rules, global_allowlist_paths, framework_allowlist)
            for fp, rel in file_scan_list
        ]

    if max_workers > 1 and len(file_scan_list) >= _PARALLEL_SCAN_THRESHOLD:
        _scripts_dir = str(Path(__file__).parent.parent)
        if _scripts_dir not in sys.path:
            sys.path.insert(0, _scripts_dir)
        _raw_rules = [
            (rule_id, keywords, pattern.pattern, al_paths, al_regexes, cel_filter)
            for rule_id, keywords, pattern, al_paths, al_regexes, cel_filter in compiled_rules
        ]
        _fw_list = list(framework_allowlist)
        _batch_size = max(16, len(_worker_scan_args) // (max_workers * 4))
        _batches = [
            _worker_scan_args[i : i + _batch_size]
            for i in range(0, len(_worker_scan_args), _batch_size)
        ]
        scan_results: list | None = None
        try:
            from concurrent.futures import ProcessPoolExecutor as _PPE
            import multiprocessing as _mp
            _mp_ctx = _mp.get_context("spawn")
            with _PPE(
                max_workers=max_workers,
                mp_context=_mp_ctx,
                initializer=_worker_init_secrets_scanner,
                initargs=(_scripts_dir, _raw_rules, global_allowlist_paths, _fw_list),
            ) as _pool:
                _batch_results = list(_pool.map(_scan_file_secrets_batch_worker, _batches))
            scan_results = [r for batch in _batch_results for r in batch]
        except Exception:
            scan_results = None
        if scan_results is None:
            scan_results = _serial_scan()
    else:
        scan_results = _serial_scan()

    # Phase 2: serial exception matching — mutates exceptions list and collects failures.
    failures: list[str] = []
    for (_fp, rel), (lines, file_sha256, hits) in zip(file_scan_list, scan_results):
        if not lines and not hits:
            continue  # file unreadable or globally allowlisted
        file_failures, file_changed = _match_hits_for_file(
            rel, lines, file_sha256, hits,
            exceptions, framework_allowlist,
            required_confirmations, current_email,
        )
        failures.extend(file_failures)
        if file_changed:
            exceptions_changed = True

    if exceptions_changed:
        save_exceptions(root, exceptions)

    return failures
