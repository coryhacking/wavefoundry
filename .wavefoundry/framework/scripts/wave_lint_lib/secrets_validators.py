from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import tomllib

from .cel_filter import eval_filter, _jwt_exp_claim
from .constants import SCAN_ALLOWLIST_PATH, SCAN_FINDINGS_PATH, SCAN_RULES_FRAMEWORK_PATH, SCAN_RULES_PROJECT_PATH

# Shared subprocess isolation (wave 1p8gu). This module lives in the wave_lint_lib subpackage; the
# helper lives one level up in the scripts dir, so ensure that dir is importable before importing it.
_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import subprocess_util  # noqa: E402
import lifecycle_id  # noqa: E402  — wave 1p8l0: lifecycle-backed `<prefix>-sec` finding IDs

_INLINE_SUPPRESS_RE = re.compile(r"#\s*wavefoundry-ignore:\s*secrets(.*)")


# ---------------------------------------------------------------------------
# TOML loading
# ---------------------------------------------------------------------------

def _load_toml(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_merged_ruleset(root: Path) -> tuple[list[dict], dict, list[str]]:
    """Return (rules, policy, errors).

    rules: merged list of rule dicts from framework + project files.
    policy: merged policy dict (project overrides framework).
    errors: fatal diagnostic messages if files are corrupt.
    """
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
    result = subprocess_util.isolated_run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=root, capture_output=True, text=True,
    )
    return result.returncode == 0


def _head_exists(root: Path) -> bool:
    result = subprocess_util.isolated_run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=root, capture_output=True, text=True,
    )
    return result.returncode == 0


def _get_changed_files(root: Path) -> list[Path]:
    # Tracked files changed since HEAD (staged + unstaged)
    changed = subprocess_util.isolated_run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=root, capture_output=True, text=True,
    )
    # Untracked files that are not gitignored (new files not yet staged)
    untracked = subprocess_util.isolated_run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=root, capture_output=True, text=True,
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


def _filter_gitignored(root: Path, paths: list[Path]) -> list[Path]:
    """Best-effort: drop paths git would ignore, via ``git check-ignore --stdin``.

    Wave 1p5rd — used only by the `rglob` fallback (when `git ls-files` failed) so the
    fallback matches the git-tracked path, which already excludes gitignored files via
    `--exclude-standard`. Returns ``paths`` unchanged when the directory is not a git
    worktree (check-ignore exits non-0/1) or on any failure. Never raises.
    """
    if not paths:
        return paths
    rels: list[str] = []
    for p in paths:
        try:
            # .as_posix() → forward-slash separators so the membership test matches
            # `git check-ignore` stdout, which emits posix paths on every host including
            # Windows (wave 1p9ix). str(PurePath) is backslash-separated on Windows, so the
            # relpaths would never match git's output and gitignored files would not be dropped.
            rels.append(p.relative_to(root).as_posix())
        except ValueError:
            rels.append(str(p))
    try:
        proc = subprocess_util.isolated_run(
            ["git", "check-ignore", "--stdin"],
            cwd=root, input="\n".join(rels), capture_output=True, text=True,
        )
    except OSError:
        return paths
    # exit 0 = at least one ignored (printed on stdout); 1 = none ignored; anything
    # else (128 = not a git repo, etc.) → can't determine, keep all.
    if proc.returncode not in (0, 1):
        return paths
    ignored = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    if not ignored:
        return paths
    return [p for p, rel in zip(paths, rels) if rel not in ignored]


def _get_all_files(root: Path) -> list[Path]:
    tracked = subprocess_util.isolated_run(
        ["git", "ls-files"],
        cwd=root, capture_output=True, text=True,
    )
    if tracked.returncode != 0:
        # Fallback (not a usable git worktree — e.g. not a repo, git unavailable, or
        # root != worktree root): walk the tree excluding .git/, then best-effort honor
        # .gitignore via `git check-ignore` (wave 1p5rd). If the dir IS a repo and
        # `git ls-files` merely glitched, ignored paths are dropped; if truly non-git,
        # check-ignore errors and the walk is kept (the [allowlist] + binary skip still
        # exclude framework runtime artifacts before any read).
        walked = [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
        return _filter_gitignored(root, walked)

    untracked = subprocess_util.isolated_run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=root, capture_output=True, text=True,
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


# ---------------------------------------------------------------------------
# Wave 1p4d1 — RE2 → Python `re` regex compatibility shim.
#
# The ruleset is Gitleaks-schema (Go's RE2 engine). A subset of patterns use RE2
# syntax that Python's `re` rejects, so they fail re.compile and the rule silently
# never runs. Rather than rewrite the .toml (which would re-break on the next
# Gitleaks import), translate at load — but ONLY when the original fails to compile,
# so already-valid patterns are untouched. Two RE2-isms appear in the ruleset:
#   1. an inline `(?i)` flag placed mid-pattern (RE2: scoped to the enclosing group;
#      Python: only valid at position 0) → relocate to a SCOPED group `(?i:…)` that
#      spans from the flag to the enclosing group's close, preserving the exact flag
#      scope (a case-sensitive token prefix before the flag stays case-sensitive);
#   2. the `\z` end-of-text anchor → Python's `\Z`.
# ---------------------------------------------------------------------------

_BARE_INLINE_FLAG_RE = re.compile(r"\(\?([aiLmsux]+)\)")


def _is_escaped(s: str, idx: int) -> bool:
    """True if the char at idx is escaped by an odd run of preceding backslashes."""
    bs = 0
    j = idx - 1
    while j >= 0 and s[j] == "\\":
        bs += 1
        j -= 1
    return bs % 2 == 1


def _in_char_class(s: str, idx: int) -> bool:
    """True if idx falls inside an unescaped [...] character class."""
    in_class = False
    i = 0
    while i < idx:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if in_class:
            if c == "]":
                in_class = False
        elif c == "[":
            in_class = True
        i += 1
    return in_class


def _enclosing_group_close(pat: str, pos: int) -> int:
    """Index where a scoped flag opened at ``pos`` must close: the first of (a) the
    ``)`` that closes the group ENCLOSING ``pos``, or (b) an alternation bar ``|`` at
    the same group depth, or (c) ``len(pat)`` at the top level. Stopping at a same-depth
    ``|`` is essential — a scoped ``(?…:…)`` group must not span across an alternation
    bar, or it swallows the ``|`` and restructures the alternation (wave 1p4d1: the
    ``curl-auth-header`` ``"…"|'…'`` case, where wrapping past the ``|`` killed the
    single-quote branch). RE2 inline flags are zero-width directives, so each branch's
    own ``(?i)`` independently makes that branch case-insensitive. Skips escaped chars
    and ``[...]`` character classes so their parens/brackets/bars don't miscount."""
    depth = 0
    i = pos
    n = len(pat)
    in_class = False
    while i < n:
        c = pat[i]
        if c == "\\":
            i += 2
            continue
        if in_class:
            if c == "]":
                in_class = False
            i += 1
            continue
        if c == "[":
            in_class = True
        elif c == "(":
            depth += 1
        elif c == ")":
            if depth == 0:
                return i
            depth -= 1
        elif c == "|" and depth == 0:
            return i
        i += 1
    return n


def _scope_inline_flags(pat: str) -> str:
    """Rewrite each bare mid-pattern ``(?flags)`` to a scoped ``(?flags:…)`` spanning
    to the enclosing group's close — faithful to RE2's group-scoped flag semantics."""
    guard = 0
    while True:
        guard += 1
        if guard > 200:  # pathological — bail out unchanged rather than loop
            return pat
        m = None
        for cand in _BARE_INLINE_FLAG_RE.finditer(pat):
            if _is_escaped(pat, cand.start()) or _in_char_class(pat, cand.start()):
                continue
            m = cand
            break
        if m is None:
            return pat
        close = _enclosing_group_close(pat, m.end())
        pat = pat[: m.start()] + f"(?{m.group(1)}:" + pat[m.end() : close] + ")" + pat[close:]


def _translate_end_anchor(pat: str) -> str:
    """RE2 ``\\z`` (end of text) → Python ``\\Z`` (end of string), honoring escapes
    and character classes so a literal ``z`` is never touched."""
    out: list[str] = []
    i = 0
    n = len(pat)
    in_class = False
    while i < n:
        c = pat[i]
        if c == "\\" and i + 1 < n:
            nxt = pat[i + 1]
            out.append("\\Z" if (nxt == "z" and not in_class) else "\\" + nxt)
            i += 2
            continue
        if c == "[":
            in_class = True
        elif c == "]":
            in_class = False
        out.append(c)
        i += 1
    return "".join(out)


def _re2_to_re(pattern: str) -> str:
    """Translate RE2-only constructs to Python ``re`` equivalents (wave 1p4d1).
    Faithful and minimal — only relocates inline flags to scoped groups and maps
    ``\\z``→``\\Z``. Caller applies it ONLY when the original fails to compile."""
    return _scope_inline_flags(_translate_end_anchor(pattern))


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
    # Wave 1p44x — length-scaled reveal window with a hard ~40% exposure cap so
    # short secrets stop leaking the fixed 4+4 (8-char) window into the committed
    # findings ledger. The full 4+4 reveal is reached only at length >= 20; the
    # cap (floor(0.4*n) characters revealed in total) tightens it further for the
    # shortest values. Long-secret output is unchanged where the cap permits.
    n = len(text)
    if n <= 8:
        return "****"
    target = 4 if n >= 20 else (3 if n >= 17 else 2)
    w = min(target, (n * 2 // 5) // 2)  # (n*2//5) == floor(0.4*n); //2 per side
    if w <= 0:
        return "****"
    return f"{text[:w]}****{text[-w:]}"


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
    result = subprocess_util.isolated_run(
        ["git", "config", "user.email"],
        cwd=root, capture_output=True, text=True,
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


# ---------------------------------------------------------------------------
# Finding IDs (wave 1p8l0)
#
# Scanner-created secret findings use a LIFECYCLE-backed ID `<prefix>-sec`
# (e.g. `1p8l0-sec`) — the same 5-char base36 lifecycle prefix family used by
# waves/changes/ADRs, with a `sec` suffix and NO slug. Finding context lives in
# the structured record fields (file/line/rule_id/line_hash/context_hash/
# matched_text), so a generated slug would only duplicate already-structured
# data and add avoidable collision/determinism work.
#
# `sec` is deliberately scoped to the scanner + the lifecycle library here — it
# is NOT a public change-doc kind (it never appears in `wave_new_*` kind lists,
# `VALID_CHANGE_KINDS`, or plan/wave scaffolding). The lifecycle CLI/MCP minting
# tools do not expose it; only the scanner mints `<prefix>-sec`.
# ---------------------------------------------------------------------------

# 5-6 chars: 6 is the lifecycle scheme's graceful post-horizon overflow width.
_SEC_ID_RE = re.compile(r"^[0-9a-z]{5,6}-sec$")


def _existing_finding_ids(exceptions: list[dict]) -> set[str]:
    """All `<prefix>-sec` ids already present on findings. Used so a freshly-minted `sec` id never
    collides with an existing finding (in addition to the lifecycle-prefix dedup against
    waves/changes/ADRs). Reads every `id` regardless of shape, so an imported ledger carrying an
    older id form is still deduped against."""
    out: set[str] = set()
    for e in exceptions:
        eid = e.get("id", "")
        if isinstance(eid, str) and eid:
            out.add(eid)
    return out


def _next_secret_finding_id(
    root: Path,
    exceptions: list[dict],
    *,
    timestamp: datetime | None = None,
    taken: set[str] | None = None,
    entropy_slug: str = "",
) -> str:
    """Mint the next available lifecycle-backed secret-finding id `<prefix>-sec`.

    Wave 1p8l0 — replaces the old `exc-###` sequential id. The prefix comes from
    ``lifecycle_id.next_available_prefix``, which dedupes against existing
    wave/change/ADR ids on disk under ``root``. We then additionally dedupe the
    formatted `<prefix>-sec` against existing scan-finding ids (``exceptions`` +
    ``taken``) and advance the lifecycle floor until a free prefix is found —
    this covers multiple findings minted during a single scan (each
    ``commit=True`` call advances the in-process lifecycle floor, so consecutive
    mints get distinct prefixes).

    ``timestamp`` is forwarded to the lifecycle generator so tests can pin the
    minted prefix for deterministic output (Requirement 10 / AC-10).

    ``entropy_slug`` feeds the scheme-v2 per-mint hash entropy (ignored under
    v1). Callers pass a per-finding identity (file:rule:line_hash) so distinct
    findings hash to distinct entropy — without it every sec mint on a given
    day would share one constant base value, making same-day cross-branch sec
    mints a guaranteed collision (a wider window than v1's 5-minute bucket).
    """
    used = _existing_finding_ids(exceptions)
    if taken:
        used |= taken
    # next_available_prefix(commit=True) advances the in-process lifecycle floor,
    # so re-calling on a collision yields a strictly later prefix. Bounded loop
    # guards against a pathological run rather than the expected 0–1 retries.
    for _ in range(len(used) + 2):
        prefix = lifecycle_id.next_available_prefix(
            timestamp, repo_root=root, kind="sec", slug=entropy_slug,
        )
        candidate = f"{prefix}-sec"
        if candidate not in used:
            return candidate
    # Unreachable in practice; fall through to the last advanced prefix.
    return f"{lifecycle_id.next_available_prefix(timestamp, repo_root=root, kind='sec', slug=entropy_slug)}-sec"


def _sha256_file(path: Path) -> str:
    # Wave 1p9hm: normalize CRLF→LF before hashing so the digest is line-ending independent. Non-.py
    # shipped framework files (.md/.json/.html/.js/.css) without an explicit `eol` attribute check out
    # as CRLF under git-for-Windows `core.autocrlf=true`; a raw byte hash would then differ from the
    # LF-based digest baked into the shipped scan-allowlist and the previously-suppressed framework
    # false-positive would resurface as a hard lint failure. Kept byte-identical with the copy in
    # build_scan_allowlist._sha256_file so allowlist build and lint agree.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


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


def _sweep_suppressed_pending(
    exceptions: list[dict], rel_path: str, matched_ids: set[str]
) -> bool:
    """Wave 1p4a2 — on a FULL scan, drop ``pending`` entries for ``rel_path`` whose
    source line still exists (they survived ``_sweep_stale_exceptions``, so a
    ``line_hash`` is present) but which the CURRENT ruleset did NOT reproduce as a hit
    this scan (``id`` absent from ``matched_ids``) — i.e. a rule/allowlist change has
    since suppressed them, leaving a phantom that keeps blocking ``wave_close``.

    Strictly ``pending``-only: operator classifications (``false-positive``,
    ``suspected-secret``, ``confirmed-secret``) and legacy entries without a
    ``line_hash`` are never touched. Returns True if any entries were removed. The
    caller gates this to full scans (``scan_all=True``) so an incremental run — which
    re-evaluates only changed files — never prunes an untouched file's entries.
    """
    to_remove = [
        e for e in exceptions
        if e.get("file") == rel_path
        and e.get("status", "pending") == "pending"
        and e.get("line_hash")
        and e.get("id") not in matched_ids
    ]
    for e in to_remove:
        exceptions.remove(e)
    return bool(to_remove)


# ---------------------------------------------------------------------------
# Confirmation count logic
# ---------------------------------------------------------------------------

def _parse_confirmed_at(value: Any) -> datetime | None:
    """Parse a confirmation's ISO-8601 ``confirmed_at`` to a tz-aware UTC datetime,
    or None if missing/empty/unparseable (wave 1p457). Trailing ``Z`` is accepted;
    a naive timestamp is assumed UTC."""
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _unique_confirmation_count(
    entry: dict, as_of: datetime | None = None, valid_days: int = 0,
) -> tuple[int, list[str]]:
    """Return (unique_email_count, list_of_confirmer_names).

    Wave 1p457 — when ``valid_days`` > 0, a confirmation counts only if its
    ``confirmed_at`` parses AND is no older than ``valid_days`` relative to
    ``as_of`` (default: now). Stale/unparseable confirmations are dropped from the
    count (fail-closed) but are NOT removed from ``confirmations[]`` — history is
    preserved. ``valid_days`` falsy → no expiry (legacy behavior). The
    ``(count, names)`` return shape is unchanged (1p44y reads it)."""
    cutoff: datetime | None = None
    if valid_days and valid_days > 0:
        ref = as_of or datetime.now(timezone.utc)
        cutoff = ref - timedelta(days=valid_days)
    seen_emails: set[str] = set()
    names: list[str] = []
    for c in entry.get("confirmations", []):
        email = c.get("git_user_email", "")
        if not email or email in seen_emails:
            continue
        if cutoff is not None:
            ts = _parse_confirmed_at(c.get("confirmed_at", ""))
            if ts is None or ts < cutoff:
                continue  # expired or unparseable — fail-closed
        seen_emails.add(email)
        names.append(c.get("git_user_name", email))
    return len(seen_emails), names


def _expired_confirmation_count(
    entry: dict, as_of: datetime | None, valid_days: int,
) -> int:
    """Count unique confirmer emails whose confirmations are ALL expired/unparseable
    (wave 1p457). Used only for the gate-failure message detail; 0 when expiry off."""
    if not valid_days or valid_days <= 0:
        return 0
    ref = as_of or datetime.now(timezone.utc)
    cutoff = ref - timedelta(days=valid_days)
    fresh: set[str] = set()
    stale: set[str] = set()
    for c in entry.get("confirmations", []):
        email = c.get("git_user_email", "")
        if not email:
            continue
        ts = _parse_confirmed_at(c.get("confirmed_at", ""))
        (fresh if (ts is not None and ts >= cutoff) else stale).add(email)
    return len(stale - fresh)


# Wave 1p44y — bot / no-reply author addresses that must not count as confirmable
# reviewers (they inflate the install-derived confirmation threshold but can never
# actually confirm a finding).
_BOT_EMAIL_RE = re.compile(r"(?:noreply|no-reply|\[bot\]|\+bot@|@bots?\.)", re.IGNORECASE)


def _confirmable_reviewer_emails(root: Path, days: int = 365) -> set[str]:
    """Return recent, non-bot committer/author emails — the reviewers who could
    plausibly confirm a false positive (wave 1p44y).

    Used to clamp the required-confirmation threshold DOWN (never up) so a lone
    active maintainer is not deadlocked by a threshold inflated by bots/inactive
    co-authors. Returns an empty set when git history is unavailable (then the
    caller leaves the policy threshold unchanged and relies on override_reason)."""
    try:
        result = subprocess_util.isolated_run(
            ["git", "log", f"--since={days} days ago", "--format=%ae%n%ce"],
            cwd=root, capture_output=True, text=True, check=False,
        )
    except Exception:
        return set()
    if result.returncode != 0:
        return set()
    emails: set[str] = set()
    for line in result.stdout.splitlines():
        email = line.strip().lower()
        if email and not _BOT_EMAIL_RE.search(email):
            emails.add(email)
    return emails


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

# Minimum file count before the parallel scan path is engaged.
_PARALLEL_SCAN_THRESHOLD = 50

# ── Wave 1p44s — scan_file_raw input guards ──────────────────────────────────
# Real credential tokens are short and live in normal-length lines of text files,
# so these generous caps skip the pathological inputs (multi-MB minified lines,
# oversized generated assets, binary blobs) that pin a worker and drive full-scan
# wall-clock time, WITHOUT weakening detection on in-bounds files. Framework-owned
# and tunable here in one place.
#
# Per-line length cap (characters). Generous on purpose: the longest real
# single-line secrets (an RSA-4096 PEM is ~3.2 KB, long JWTs a few KB) stay well
# under this, while multi-MB minified/generated lines are skipped.
MAX_LINE_BYTES = 32 * 1024
# Per-file size cap (bytes). Files above this are generated/data artifacts, not
# hand-authored source carrying a hidden credential.
MAX_FILE_BYTES = 5 * 1024 * 1024
# Bytes sniffed from the file head for NUL-byte binary detection.
BINARY_SNIFF_BYTES = 8192
# Wave 1p5qp: extension-based fast-skip — checked BEFORE stat/read so known-binary
# and data artifacts (LanceDB segments, archives, shared objects, media, model
# weights) never reach the per-file NUL-byte sniff. Field report (091yo): the
# 8 KB-per-file sniff over ~300 such files made docs-lint / wave_* tools spin (~54s).
_BINARY_SKIP_EXTENSIONS = frozenset({
    ".zip", ".gz", ".tar", ".tgz", ".bz2", ".xz", ".7z", ".rar", ".zst",
    ".so", ".dylib", ".dll", ".a", ".o", ".obj", ".lib", ".node", ".wasm",
    ".lance",  # LanceDB segment files
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".tif", ".tiff", ".svgz",
    ".pdf", ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".mov", ".avi", ".mkv", ".wav", ".flac", ".ogg", ".webm",
    ".pyc", ".pyo", ".whl", ".egg", ".bin", ".dat", ".db", ".sqlite", ".sqlite3",
    ".onnx", ".pt", ".pth", ".safetensors", ".npy", ".npz", ".parquet", ".arrow", ".feather",
    ".class", ".jar", ".war",
})


def _is_binary_path(file_path: Path) -> bool:
    """True when the path's extension marks it binary/data — including VERSIONED
    shared objects like ``libfoo.so.13`` / ``libbar.dylib.1`` (wave 1p5rd), whose
    ``Path.suffix`` is the trailing version (``.13``) rather than ``.so``. A
    ``.so``/``.dylib``/``.dll`` component followed only by numeric version segments
    counts; ``foo.so.txt`` does not (still scanned)."""
    if file_path.suffix.lower() in _BINARY_SKIP_EXTENSIONS:
        return True
    suffixes = [s.lower() for s in file_path.suffixes]
    for i, s in enumerate(suffixes):
        if s in (".so", ".dylib", ".dll"):
            trailing = suffixes[i + 1:]
            if all(t[1:].isdigit() for t in trailing):  # empty trailing → plain .so
                return True
    return False

# ── Wave 1p44s (AC-9) — skip visibility ──────────────────────────────────────
# Files skipped by the size/binary guards must be SURFACED, never silent, so a
# real secret in a skipped file leaves a trace. Two channels:
#   1. A per-skip stderr line (the authoritative, process-safe record — emitted
#      from whichever process does the skip, so parallel-worker skips are visible).
#   2. An in-process list (serial path + tests) for a queryable count/paths;
#      reset at the start of each check_hardcoded_secrets run so it stays bounded.
_SCANNER_SKIPS: list[dict] = []


def _record_scan_skip(rel: str, reason: str, detail: str) -> None:
    """Record and surface a guard skip (wave 1p44s AC-9)."""
    _SCANNER_SKIPS.append({"file": rel, "reason": reason, "detail": detail})
    try:
        print(
            f"secrets-scan: SKIPPED {rel} ({reason}: {detail}) "
            f"— NOT scanned for secrets",
            file=sys.stderr, flush=True,
        )
    except Exception:
        pass


# Module-level globals populated by _worker_init_secrets_scanner in spawned
# worker processes. Always None in the parent process.
_WORKER_COMPILED_RULES: list | None = None
_WORKER_GLOBAL_ALLOWLIST_PATHS: list[str] | None = None
_WORKER_FRAMEWORK_ALLOWLIST: set[str] | None = None
_WORKER_POLICY: dict | None = None  # wave 1p44w — policy flags for rule filters
_WORKER_GLOBAL_REGEXES: list | None = None     # wave 1p456 — global value-filter
_WORKER_GLOBAL_STOPWORDS: list | None = None   # wave 1p456 — global value-filter


def _worker_init_secrets_scanner(
    scripts_dir: str,
    raw_rules: list,
    global_allowlist_paths: list,
    framework_allowlist_list: list,
    policy: dict | None = None,
    global_regexes: list | None = None,
    global_stopwords: list | None = None,
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
    global _WORKER_POLICY, _WORKER_GLOBAL_REGEXES, _WORKER_GLOBAL_STOPWORDS
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
    _WORKER_POLICY = policy
    _WORKER_GLOBAL_REGEXES = global_regexes
    _WORKER_GLOBAL_STOPWORDS = global_stopwords
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
        _WORKER_POLICY,
        _WORKER_GLOBAL_REGEXES,
        _WORKER_GLOBAL_STOPWORDS,
    )


def _scan_file_secrets_batch_worker(batch_args: list) -> list:
    """Worker task: scan a batch of files — amortizes IPC overhead per batch."""
    return [_scan_file_secrets_worker(args) for args in batch_args]


# Wave 1p44v — leading inline-comment tokens by file extension. Best-effort
# triage signal only (in_comment): a commented-out secret is still a leak, so the
# flag is recorded for the reviewer and never auto-suppresses. Unknown extensions
# default to not-a-comment; no block-comment parsing.
_LINE_COMMENT_TOKENS: dict[str, tuple[str, ...]] = {
    ".py": ("#",), ".rb": ("#",), ".sh": ("#",), ".bash": ("#",), ".zsh": ("#",),
    ".yaml": ("#",), ".yml": ("#",), ".toml": ("#",), ".cfg": ("#",), ".conf": ("#",),
    ".ini": ("#", ";"), ".pl": ("#",), ".pm": ("#",), ".r": ("#",), ".tf": ("#",),
    ".js": ("//",), ".jsx": ("//",), ".ts": ("//",), ".tsx": ("//",), ".mjs": ("//",),
    ".cjs": ("//",), ".java": ("//",), ".c": ("//",), ".h": ("//",), ".cpp": ("//",),
    ".hpp": ("//",), ".cc": ("//",), ".cs": ("//",), ".go": ("//",), ".rs": ("//",),
    ".swift": ("//",), ".kt": ("//",), ".kts": ("//",), ".scala": ("//",),
    ".php": ("//", "#"), ".sql": ("--",), ".lua": ("--",), ".hs": ("--",),
    ".clj": (";",), ".lisp": (";",), ".el": (";",),
}


def _line_is_comment(rel: str, line: str) -> bool:
    """Return True if *line* begins with the leading comment token for *rel*'s
    extension (wave 1p44v). Unknown extensions → False; flag only, never suppress."""
    tokens = _LINE_COMMENT_TOKENS.get(Path(rel).suffix.lower())
    if not tokens:
        return False
    stripped = line.lstrip()
    return any(stripped.startswith(tok) for tok in tokens)


def _format_jwt_exp(secret: str) -> str | None:
    """Wave 1p44w — if *secret* is a decodable JWT with an `exp` claim, return a
    human-readable UTC expiry (suffixed ``(EXPIRED)`` when past), else None.

    Surfacing only — the reviewer sees expiry context; suppression stays
    policy-gated in the rule filter. Fail-safe: never raises."""
    exp = _jwt_exp_claim(secret)
    if exp is None:
        return None
    try:
        when = datetime.fromtimestamp(exp, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    stamp = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{stamp} (EXPIRED)" if when < datetime.now(timezone.utc) else stamp


def scan_file_raw(
    file_path: Path,
    rel: str,
    compiled_rules: list,
    global_allowlist_paths: list[str],
    framework_allowlist: set[str],
    policy: dict | None = None,
    global_regexes: list[str] | None = None,
    global_stopwords: list[str] | None = None,
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
    # Wave 1p5qp — extension fast-skip BEFORE any stat/read: known-binary/data
    # artifacts (archives, shared objects, LanceDB segments, media, model weights)
    # never reach the per-file NUL-byte sniff. Field report 091yo: the 8 KB sniff
    # over ~300 such files made docs-lint / wave_* tools spin (~54s).
    if _is_binary_path(file_path):
        _record_scan_skip(rel, "binary file (extension)", "".join(file_path.suffixes).lower() or file_path.name)
        return [], None, []
    # Wave 1p44s — input guards BEFORE reading the file. Each returns the same
    # ([], None, []) shape as a clean skip so phase-2 short-circuits without a
    # stale-exception sweep (AC-5). Size/binary skips are surfaced (AC-9).
    try:
        size = file_path.stat().st_size
    except OSError:
        return [], None, []  # vanished mid-scan (stat race) — treat as a clean skip
    if size > MAX_FILE_BYTES:
        _record_scan_skip(rel, "file too large", f"{size} bytes > {MAX_FILE_BYTES} cap")
        return [], None, []
    try:
        if b"\x00" in file_path.read_bytes()[:BINARY_SNIFF_BYTES]:
            _record_scan_skip(
                rel, "binary file", f"NUL byte in first {BINARY_SNIFF_BYTES} bytes"
            )
            return [], None, []
    except OSError:
        return [], None, []  # disappeared between stat and read — clean skip
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return [], None, []

    lines = content.splitlines()
    content_lower = content.lower()
    file_sha256 = _sha256_file(file_path) if framework_allowlist else None
    # Wave 1p44w — policy flag a rule filter can read via attributes. Default off
    # ("") so an expired JWT still SURFACES; an opt-in policy enables suppression.
    _jwt_suppress = "1" if policy and policy.get("suppress_expired_jwts") else ""
    hits: list[dict] = []
    # Wave 1p44v — per-secret dedup. line_no → spans already recorded on that
    # line. When a later rule matches the SAME secret (an overlapping span on the
    # same line) we skip it, so one secret yields one finding instead of one per
    # matching rule. Keyed on position (not redacted_match) so two distinct
    # secrets that redact identically stay separate (AC-2); the first-matching
    # rule in ruleset order wins, making the result deterministic (AC-6).
    _kept_spans: dict[int, list[tuple[int, int]]] = {}

    for rule_id, keywords, pattern, al_paths, al_regexes, cel_filter_expr in compiled_rules:
        if keywords and not any(kw in content_lower for kw in keywords):
            continue
        if _path_matches_allowlist(rel, al_paths):
            continue
        for line_no, line in enumerate(lines, start=1):
            # Wave 1p44s — skip pathological over-long lines (minified bundles,
            # generated lockfiles) before handing them to the rule regex. Real
            # credential tokens are short, so a > MAX_LINE_BYTES line cannot hide a
            # detectable secret; the threshold is generous to protect long config.
            if len(line) > MAX_LINE_BYTES:
                continue
            m = pattern.search(line)
            if not m:
                continue
            matched_text = m.group(0)
            secret = m.group(1) if m.lastindex and m.lastindex >= 1 else matched_text
            if cel_filter_expr and eval_filter(
                cel_filter_expr, secret, matched_text, rel, line,
                attrs={"suppress_expired_jwts": _jwt_suppress},
            ):
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
            # Wave 1p456 — global [allowlist] value-filter. Composes AFTER the
            # per-rule CEL filter and per-rule allowlist: a match surviving those
            # is still dropped if its VALUE is global structural noise (the WHOLE
            # value matches a global regex) or contains a global stopword.
            # Uses re.fullmatch (whole-value semantics) NOT re.search, so a real
            # secret that merely CONTAINS structural-noise text (e.g. a high-entropy
            # value containing the substring "false") is NOT over-suppressed — this
            # also defends against an un-anchored allowlist regex (delivery review,
            # wave 1p44n: the shipped `^true|false|null$` parses as three branches,
            # two of them unanchored).
            if global_regexes or global_stopwords:
                g_skip = False
                for g_regex in (global_regexes or ()):
                    try:
                        if re.fullmatch(g_regex, secret):
                            g_skip = True
                            break
                    except re.error:
                        pass
                if not g_skip and global_stopwords:
                    _sl = secret.lower()
                    for sw in global_stopwords:
                        if isinstance(sw, str) and sw.lower() in _sl:
                            g_skip = True
                            break
                if g_skip:
                    continue
            suppressed, suppress_error = check_inline_suppression(line)
            if suppressed and not suppress_error:
                continue  # valid suppression with reason — skip entirely
            # Wave 1p44v — dedup: if an earlier rule already recorded an
            # overlapping span on this line, it is the same secret → skip.
            start, end = m.start(), m.end()
            spans = _kept_spans.setdefault(line_no, [])
            if any(start < e0 and s0 < end for (s0, e0) in spans):
                continue
            spans.append((start, end))
            redacted_match = redact(matched_text)
            redacted_line = (line[:m.start()] + redacted_match + line[m.end():]).strip()
            hit = {
                "rule_id": rule_id,
                "line_no": line_no,
                "matched_text": matched_text,
                "redacted_match": redacted_match,
                "redacted_line": redacted_line,
                "line_hash": _hash_line(line),
                "context_hash": _hash_context(lines, line_no),
                "in_comment": _line_is_comment(rel, line),  # wave 1p44v — triage flag
                "suppress_error": suppress_error,  # None → normal hit; str → lint error
            }
            # Wave 1p44w — surface JWT expiry for reviewer triage (only set when the
            # secret decodes as a JWT carrying an exp claim; never for other rules).
            _exp_date = _format_jwt_exp(secret)
            if _exp_date:
                hit["exp_date"] = _exp_date
            hits.append(hit)

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
    confirmation_valid_days: int = 0,
    as_of: datetime | None = None,
    prune_suppressed: bool = False,
    root: Path | None = None,
    mint_timestamp: datetime | None = None,
) -> tuple[list[str], bool]:
    """Serial exception matching for one file's pre-scanned hits.

    Returns (failures, exceptions_changed).
    Mutates exceptions in place (appending new entries, updating line drift).

    prune_suppressed: wave 1p4a2 — when True (full scan), drop ``pending`` entries the
        current ruleset no longer produces (line present, but not a hit this scan).

    root / mint_timestamp: wave 1p8l0 — new findings get a lifecycle-backed
        `<prefix>-sec` id (``_next_secret_finding_id``). ``root`` lets the
        lifecycle generator dedupe against on-disk wave/change/ADR ids;
        ``mint_timestamp`` pins the prefix for deterministic test output.
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
                "id": _next_secret_finding_id(
                    root if root is not None else Path("."),
                    exceptions,
                    timestamp=mint_timestamp,
                    entropy_slug=f"{rel}:{rule_id}:{hit['line_hash']}",
                ),
                "file": rel,
                "line": line_no,
                "line_hash": hit["line_hash"],
                "context_hash": hit["context_hash"],
                "rule_id": rule_id,
                "matched_text": hit["redacted_line"],
                "in_comment": hit.get("in_comment", False),  # wave 1p44v — triage context
                "status": "pending",
            }
            if hit.get("exp_date"):
                new_entry["exp_date"] = hit["exp_date"]  # wave 1p44w — JWT expiry context
            exceptions.append(new_entry)
            # Wave 1p4a2 — a freshly-created entry IS a current hit; register it in
            # matched_ids so the full-scan suppressed-pending sweep never prunes it.
            matched_ids.add(new_entry["id"])
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
            # Wave 1p44y — operator override: a non-empty override_reason dismisses
            # the finding (parity with the confirmed/suspected-secret dismissal in
            # server_impl._check_secrets_gate), even below the confirmation count.
            if existing.get("override_reason", "").strip():
                continue  # operator-dismissed false positive
            count, names = _unique_confirmation_count(
                existing, as_of, confirmation_valid_days
            )
            if count >= required_confirmations:
                pass  # suppressed
            else:
                names_str = ", ".join(names) if names else "(none)"
                # Wave 1p451 — both messages name the policy file + key, state the
                # threshold is operator-tunable and install-derived (committer count),
                # and point to the real escape paths (1p44y): another reviewer's
                # confirmation, lowering the threshold, or an override_reason. They no
                # longer instruct the impossible "needs N more from a different reviewer".
                _policy_hint = (
                    f"The threshold is `false_positive_confirmations_required` in "
                    f"{SCAN_RULES_PROJECT_PATH} (auto-detected from committer count at "
                    f"install, operator-tunable). To clear: add a confirmation from another "
                    f"reviewer, lower the threshold in {SCAN_RULES_PROJECT_PATH}, or set an "
                    f"`override_reason` on this finding in {SCAN_FINDINGS_PATH} to dismiss it."
                )
                # Wave 1p457 — when the re-open is caused by EXPIRED confirmations,
                # say so distinctly (separate from the never-confirmed wording).
                _expired = _expired_confirmation_count(
                    existing, as_of, confirmation_valid_days
                )
                _expiry_note = (
                    f" {_expired} prior confirmation(s) EXPIRED (older than "
                    f"{confirmation_valid_days} days); re-verification with a fresh dated "
                    f"confirmation is required."
                ) if _expired else ""
                if current_email and current_email in {
                    c.get("git_user_email", "") for c in existing.get("confirmations", [])
                }:
                    failures.append(
                        f"{rel}:{line_no}: [secrets] rule '{rule_id}' — false positive has "
                        f"{count} of {required_confirmations} confirmations (from: {names_str}). "
                        f"You have already confirmed.{_expiry_note} {_policy_hint}"
                    )
                else:
                    failures.append(
                        f"{rel}:{line_no}: [secrets] rule '{rule_id}' — unconfirmed false "
                        f"positive: {count} of {required_confirmations} confirmations "
                        f"(confirmed by: {names_str}).{_expiry_note} {_policy_hint}"
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

    # Wave 1p4a2 — full-scan only: drop pending entries whose line still exists but
    # which the current ruleset no longer produces as a hit (now suppressed). Gated
    # to full scans by the caller so an incremental run never prunes an untouched file.
    if prune_suppressed and lines and _sweep_suppressed_pending(exceptions, rel, matched_ids):
        exceptions_changed = True

    return failures, exceptions_changed


def check_hardcoded_secrets(
    root: Path,
    scan_all: bool = False,
    files: list[Path] | None = None,
    max_workers: int = 1,
    as_of: datetime | None = None,
    record_only: bool = False,
) -> list[str]:
    """Scan tracked/changed files for secrets matching the merged ruleset.

    Returns a list of error strings (empty = clean).

    record_only: wave 1p5pz — when True, secret *findings* (new/pending/suspected/
        confirmed/under-confirmed-false-positive, all tagged ``[secrets]``) are still
        detected and recorded to scan-findings.json, but are NOT returned as failures
        — only genuine lint errors (a bare ``wavefoundry-ignore`` directive) are. The
        secrets gate is enforced solely at ``wave_close`` (`_check_secrets_gate`), so
        docs-lint (post-edit hook, ``wave_validate``, the upgrade docs gate) must not
        block on secret findings. A non-fatal stderr notice surfaces the recorded count.

    files: when provided, scan exactly these files instead of calling get_scan_files().
           Used by the incremental indexer path to pass pre-computed changed-file sets.
    max_workers: worker count for the parallel scan phase (phase 1). Set > 1 to
           parallelise regex matching across cores using ProcessPoolExecutor (spawn
           start method + initializer pattern). Exception matching (phase 2) is always
           serial. Falls back to serial scan on any spawn/IPC error.
    """
    # Wave 1p44s (AC-9) — reset the in-process skip ledger for this scan run so
    # its count/paths reflect only the current scan (serial path; parallel-worker
    # skips surface via the per-skip stderr line emitted in the worker process).
    _SCANNER_SKIPS.clear()

    rules, policy, load_errors = load_merged_ruleset(root)
    if load_errors:
        return load_errors
    if not rules:
        return []

    required_confirmations: int = int(policy.get("false_positive_confirmations_required", 2))
    # Wave 1p457 — max age (days) of a false-positive confirmation; non-positive /
    # absent → 0 = no expiry (opt-out). `as_of` is the scan's reference "now"
    # (injectable by tests for deterministic age math).
    confirmation_valid_days: int = max(0, int(policy.get("confirmation_valid_days", 365)))
    scan_as_of: datetime = as_of or datetime.now(timezone.utc)
    global_allowlist_paths: list[str] = []
    # Wave 1p456 — the global [allowlist] value-filter (regexes + stopwords) was
    # authored but loaded nowhere; load it here so structural-noise values
    # ($VAR, {{template}}, %FMT%, /Users/…, stopword substrings) are suppressed
    # fleet-wide across every rule, not just per-rule allowlists.
    global_regexes: list[str] = []
    global_stopwords: list[str] = []

    fw_path = root / SCAN_RULES_FRAMEWORK_PATH
    try:
        if fw_path.exists():
            with open(fw_path, "rb") as f:
                fw_raw = tomllib.load(f)
            fw_allow = fw_raw.get("allowlist", {})
            global_allowlist_paths = list(fw_allow.get("paths", []))
            global_regexes = list(fw_allow.get("regexes", []))
            global_stopwords = list(fw_allow.get("stopwords", []))
    except Exception:
        pass

    proj_path = root / SCAN_RULES_PROJECT_PATH
    try:
        if proj_path.exists():
            with open(proj_path, "rb") as f:
                proj_raw = tomllib.load(f)
            proj_allow = proj_raw.get("allowlist", {})
            global_allowlist_paths += list(proj_allow.get("paths", []))
            global_regexes += list(proj_allow.get("regexes", []))
            global_stopwords += list(proj_allow.get("stopwords", []))
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

    # Wave 1p44y — clamp the false-positive confirmation threshold DOWN to the
    # count of currently-confirmable (recent, non-bot) reviewers, so a single
    # active maintainer is never blocked by a threshold inflated by bots/inactive
    # co-authors. Never raises the policy value (floor 1). Computed once, and only
    # when a false-positive entry actually exists (avoids a git call otherwise).
    effective_confirmations = required_confirmations
    if required_confirmations > 1 and any(
        e.get("status") == "false-positive" for e in exceptions
    ):
        confirmable = _confirmable_reviewer_emails(root)
        if confirmable:
            effective_confirmations = min(required_confirmations, max(1, len(confirmable)))

    # Pre-compile all rule patterns once — compiling per-file is the dominant cost.
    CompiledRule = tuple  # (rule_id, keywords, pattern, al_paths, al_regexes, cel_filter)
    compiled_rules: list[CompiledRule] = []
    # Wave 1p4a2 — track regex-compile failures. A rule that fails to compile is
    # silently dropped, so the scan runs with a DEGRADED ruleset; on a full scan the
    # 1p4a2 suppressed-pending prune must then fail CLOSED (skip pruning), because a
    # missing hit may be the broken rule, not a legitimate suppression — pruning a
    # pending entry that the broken rule would have caught is a fail-OPEN miss.
    rules_degraded = False
    for rule in rules:
        rule_id = rule.get("id", "")
        pattern_str = rule.get("regex", "")
        if not pattern_str:
            continue
        try:
            pattern = re.compile(pattern_str)
        except re.error:
            # Wave 1p4d1 — the pattern is RE2-schema; retry via the Python-compat
            # translation before giving up. Only a genuinely-malformed regex (not an
            # RE2-ism the shim handles) still fails, which correctly degrades the scan
            # (1p4a2 fail-closed). The shim runs ONLY on this failure path, so the 253
            # already-valid patterns are compiled once and never translated.
            try:
                pattern = re.compile(_re2_to_re(pattern_str))
            except re.error:
                rules_degraded = True
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
            # Wave 1p6dx: forward-slash the rel path (.as_posix(), not str() which is `\`-separated
            # on Windows) so a Windows-generated findings JSON / shipped scan-allowlist matches a
            # POSIX scan's entries — the allowlist keys on `<sha256>:<rel>:…`.
            rel = file_path.relative_to(root).as_posix()
        except ValueError:
            rel = file_path.as_posix()
        file_scan_list.append((file_path, rel))

    # Phase 1: parallel file scanning via ProcessPoolExecutor (spawn + initializer).
    # Each worker receives compiled rules via the initializer (once per process)
    # rather than per-task — avoids redundant regex compilation across all files.
    # Falls back to serial on any spawn/IPC error.
    _worker_scan_args = [(str(fp), rel) for fp, rel in file_scan_list]

    def _serial_scan() -> list:
        return [
            scan_file_raw(
                fp, rel, compiled_rules, global_allowlist_paths, framework_allowlist,
                policy, global_regexes, global_stopwords,
            )
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
        # Wave 1p8gu (review fix): the spawn pool launches console-subsystem python.exe workers, each
        # of which flashes a console window on Windows. Route through the window-free mp context
        # (pythonw.exe on Windows); when one cannot be guaranteed (Windows without pythonw), fall back
        # to the serial scan rather than open console windows.
        _mp_ctx = subprocess_util.windowless_mp_context("spawn")
        if _mp_ctx is not None:
            try:
                from concurrent.futures import ProcessPoolExecutor as _PPE
                with _PPE(
                    max_workers=max_workers,
                    mp_context=_mp_ctx,
                    initializer=_worker_init_secrets_scanner,
                    initargs=(
                        _scripts_dir, _raw_rules, global_allowlist_paths, _fw_list,
                        policy, global_regexes, global_stopwords,
                    ),
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
            effective_confirmations, current_email,
            confirmation_valid_days, scan_as_of,
            # Wave 1p4a2 — fail closed: never prune on a degraded ruleset (a rule
            # failed to compile), only on a clean full scan.
            prune_suppressed=scan_all and not rules_degraded,
            # Wave 1p8l0 — new findings get a lifecycle-backed `<prefix>-sec` id;
            # root enables on-disk id dedup, scan_as_of pins the prefix.
            root=root,
            mint_timestamp=scan_as_of,
        )
        failures.extend(file_failures)
        if file_changed:
            exceptions_changed = True

    if exceptions_changed:
        save_exceptions(root, exceptions)
    elif scan_all and not (root / SCAN_FINDINGS_PATH).exists():
        # Wave 1p8o5 #4 — always-present ledger: a CLEAN full scan (0 findings, no prior file) writes
        # a bare `[]` so the file's PRESENCE confirms a scan ran (vs. the ambiguous "clean or never
        # ran?" of an absent file). Operator decision: a bare `[]`, NOT a metadata wrapper — a
        # `scanned_at`-style wrapper would rewrite the file on every scan → git churn (the scan-state
        # file already records timing). Gated to full scans only: an incremental scan must NOT create
        # the file, since `scan_secrets.update_secrets_scan` forces a full re-scan when it is missing
        # (its absence is the regeneration trigger). The bare `[]` loads as an empty list → the
        # `wave_close` secrets gate sees no findings → no block (gate semantics unchanged). Idempotent:
        # a re-run finds the file present and writes nothing here, so the content never churns.
        save_exceptions(root, [])

    # Wave 1p5pz — record-only mode (docs-lint / hook / upgrade docs gate): secret
    # findings are tagged "[secrets]" by _match_hits_for_file; a bare-suppression
    # lint error is not. Detection still recorded the findings to scan-findings.json
    # above; here we strip the finding messages from the returned failures so they
    # don't block, leaving only genuine lint errors. wave_close is the sole gate.
    if record_only:
        findings = [f for f in failures if "[secrets]" in f]
        lint_errors = [f for f in failures if "[secrets]" not in f]
        if findings:
            print(
                f"[secrets] {len(findings)} finding(s) recorded in {SCAN_FINDINGS_PATH} "
                "— not blocking (the secrets gate runs at wave_close); run the security "
                "reviewer to classify pending entries.",
                file=sys.stderr, flush=True,
            )
        return lint_errors

    return failures
