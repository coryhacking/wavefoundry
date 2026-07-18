#!/usr/bin/env python3
"""Reverse commit->wave provenance resolution (wave 1sufq / change 1sufp).

Resolves a commit SHA (or a blamed line) back to the wave(s) that produced it,
by two LOCAL, READ-ONLY paths, and never fabricates a mapping:

  (a) commit-message parse — the ``Land wave(s) <id> ...`` landing convention.
  (b) evidence reverse-search — a wave record citing the commit SHA.

Local git only (routed through ``index_state_store._run_git``: argv list + the
sanitized git env, no shell), no network, no mutation. Honest on absence and on
message/evidence conflict (reported, never silently reconciled). This module is
the resolver primitive the ``code_commit_provenance`` MCP tool stands on; the
tool layer adds line->commit blame, Decision Log extraction, and the measured
``context_avoided`` credit.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

# The SINGLE sanctioned, argv-based, env-sanitized git entry point (a hostile
# SHA/path cannot inject a shell command through it).
from index_state_store import _run_git

# A landed SHA is 7-40 lowercase hex. Reject anything else before touching git,
# so a malformed value fails closed (honest absence), never reaches a subprocess.
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")

# "Land wave 1abcd: ..." / "Land waves 1abcd, 1abce and 1abcf for X" — capture the
# id list after the Land-wave(s) prefix, up to the first ':' or end of that line.
_LAND_WAVE_PREFIX_RE = re.compile(r"\bLand\s+waves?\s+(.+?)(?:[:\n]|$)", re.IGNORECASE)
# Lifecycle ids start with '1' then >=4 more [0-9a-z] (e.g. 1shv4). A bare "1" or a
# version like "1.13.0" cannot match (needs 4+ trailing base36 chars, no '.').
_WAVE_ID_TOKEN_RE = re.compile(r"\b(1[0-9a-z]{4,})\b")

_GIT_TIMEOUT = 10


def is_valid_sha(sha: str) -> bool:
    """True only for a 7-40 lowercase-hex token — the fail-closed input guard."""
    return bool(_SHA_RE.match((sha or "").strip().lower()))


def _git(root: Path, *args: str) -> Optional[str]:
    """Run a read-only git command under the sanctioned wrapper; stdout or None."""
    try:
        result = _run_git(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=_GIT_TIMEOUT,
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return None


def resolve_via_message(root: Path, sha: str) -> list[str]:
    """Path (a): parse ``git show -s --format=%B <sha>`` for landed wave ids.

    Returns the ordered, de-duplicated wave-id tokens named by the landing
    convention, or an empty list when the commit does not name a wave.
    """
    if not is_valid_sha(sha):
        return []
    body = _git(root, "show", "-s", "--format=%B", sha)
    if not body:
        return []
    ids: list[str] = []
    for m in _LAND_WAVE_PREFIX_RE.finditer(body):
        for tok in _WAVE_ID_TOKEN_RE.findall(m.group(1)):
            if tok not in ids:
                ids.append(tok)
    return ids


def resolve_via_evidence(root: Path, sha: str) -> list[str]:
    """Path (b): wave records whose text cites this SHA (short or full).

    Survives non-conventional commit messages (the message-parse path misses
    those) by finding the wave that recorded the landing SHA in its evidence.
    """
    if not is_valid_sha(sha):
        return []
    short = sha[:7]
    waves_dir = root / "docs" / "waves"
    if not waves_dir.is_dir():
        return []
    # Match the SHA as a hex token (short prefix or full), not a loose substring.
    token_re = re.compile(r"\b" + re.escape(short) + r"[0-9a-f]*\b")
    found: list[str] = []
    for wave_md in sorted(waves_dir.glob("*/wave.md")):
        try:
            text = wave_md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if token_re.search(text):
            # Wave dirs are "<id> <slug>"; return the id token so both resolution
            # paths speak the same vocabulary (the message path returns ids too).
            wid = wave_md.parent.name.split(" ", 1)[0]
            if wid and wid not in found:
                found.append(wid)
    return found


def blame_line_commits(
    root: Path, rel_path: str, start: int, end: int
) -> tuple[list[str], Optional[str]]:
    """``git blame`` a BOUNDED line range; return (unique full SHAs, error).

    The file path is confined to the repository (path-traversal guard) and the
    range is passed as ``-L start,end`` argv, never a shell string. Read-only.
    """
    if start < 1 or end < start:
        return [], "invalid line range"
    try:
        root_resolved = root.resolve()
        target = (root / rel_path).resolve()
        target.relative_to(root_resolved)  # raises if outside the repo
    except (ValueError, OSError):
        return [], "path outside repository"
    if not target.is_file():
        return [], "file not found"
    out = _git(root, "blame", "-L", f"{int(start)},{int(end)}", "--porcelain", "--", rel_path)
    if out is None:
        return [], "blame failed (uncommitted, binary, or out-of-range)"
    shas: list[str] = []
    _UNCOMMITTED = "0" * 40  # git blame sentinel for a not-yet-committed line
    for line in out.splitlines():
        m = re.match(r"^([0-9a-f]{40}) ", line)  # porcelain header lines
        if m and m.group(1) != _UNCOMMITTED and m.group(1) not in shas:
            shas.append(m.group(1))
    return shas, None


def resolve_commit_to_waves(root: Path, sha: str) -> dict[str, Any]:
    """Combine both paths into an honest verdict.

    ``resolved`` is False (not a fabricated guess) when neither path resolves;
    ``conflict`` is True when the two paths name different waves (reported, never
    silently reconciled).
    """
    sha = (sha or "").strip().lower()
    if not is_valid_sha(sha):
        return {
            "sha": sha, "waves": [], "via_message": [], "via_evidence": [],
            "method": "invalid_sha", "conflict": False, "resolved": False,
        }
    via_msg = resolve_via_message(root, sha)
    via_ev = resolve_via_evidence(root, sha)
    union = list(dict.fromkeys(via_msg + via_ev))
    conflict = bool(via_msg and via_ev and set(via_msg) != set(via_ev))
    if via_msg and via_ev:
        method = "message+evidence"
    elif via_msg:
        method = "message"
    elif via_ev:
        method = "evidence"
    else:
        method = "none"
    return {
        "sha": sha, "waves": union,
        "via_message": via_msg, "via_evidence": via_ev,
        "method": method, "conflict": conflict, "resolved": bool(union),
    }


# --- reasoning surfacing (Decision Log + change-doc pointers) ---

_MAX_DECISION_ROWS = 12  # bound the surfaced reasoning per source


def _wave_dir_for_id(root: Path, wave_id: str) -> Optional[Path]:
    """Locate the on-disk wave directory for a resolved wave id (prefix match).

    Wave dirs are ``docs/waves/<id> <slug>/`` — match by the leading id token.
    """
    waves_dir = root / "docs" / "waves"
    if not waves_dir.is_dir():
        return None
    for d in sorted(waves_dir.glob(f"{wave_id}*")):
        if d.is_dir() and (d.name == wave_id or d.name.startswith(wave_id + " ")):
            return d
    return None


def _decision_log_rows(md_text: str) -> list[str]:
    """Extract the data rows of a change doc's ``## Decision Log`` table.

    Returns compact "col1 | col2 | ..." strings (header/separator dropped),
    bounded by ``_MAX_DECISION_ROWS``. Empty when the doc has no Decision Log.
    """
    rows: list[str] = []
    in_section = False
    header_seen = False
    for line in md_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if in_section:
                break  # left the Decision Log section
            in_section = stripped.lower().startswith("## decision log")
            header_seen = False
            continue
        if not in_section or not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        joined = " | ".join(c for c in cells if c)
        if not joined:
            continue
        if set("".join(cells)) <= set("-: "):  # the |---|---| separator row
            continue
        if not header_seen:  # first data-looking row is the column header
            header_seen = True
            continue
        rows.append(joined)
        if len(rows) >= _MAX_DECISION_ROWS:
            break
    return rows


def _provenance_rows_for_wave(root: Path, wave_id: str) -> list[dict[str, Any]]:
    """Build the surfaced-reasoning rows for one resolved wave.

    One row per change doc (and the wave record), each carrying the file path
    and an ``excerpt`` of its Decision Log rows — the recorded reasoning the
    caller would otherwise have re-derived by reading the whole doc.
    """
    wave_dir = _wave_dir_for_id(root, wave_id)
    if wave_dir is None:
        return []
    out: list[dict[str, Any]] = []
    for md in sorted(wave_dir.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        decisions = _decision_log_rows(text)
        rel = str(md.relative_to(root)).replace("\\", "/")
        row: dict[str, Any] = {"path": rel, "wave_id": wave_id, "decisions": decisions}
        if decisions:  # only a doc with recorded reasoning is a content source
            row["excerpt"] = "\n".join(decisions)
        out.append(row)
    return out


def provenance_for_sha(root: Path, sha: str) -> dict[str, Any]:
    """Full provenance for a commit: resolution + surfaced reasoning rows."""
    verdict = resolve_commit_to_waves(root, sha)
    provenance: list[dict[str, Any]] = []
    for wave_id in verdict["waves"]:
        provenance.extend(_provenance_rows_for_wave(root, wave_id))
    verdict["provenance"] = provenance
    return verdict


def provenance_for_line(
    root: Path, rel_path: str, start: int, end: int
) -> dict[str, Any]:
    """Blame a line range, then resolve each producing commit to its reasoning."""
    shas, error = blame_line_commits(root, rel_path, start, end)
    if error is not None:
        return {"path": rel_path, "line_start": start, "line_end": end,
                "commits": [], "error": error, "resolved": False, "provenance": []}
    per_commit = [provenance_for_sha(root, s) for s in shas]
    waves: list[str] = []
    provenance: list[dict[str, Any]] = []
    for v in per_commit:
        for w in v["waves"]:
            if w not in waves:
                waves.append(w)
        provenance.extend(v["provenance"])
    return {
        "path": rel_path, "line_start": start, "line_end": end,
        "commits": shas, "waves": waves,
        "resolved": bool(waves), "provenance": provenance,
        "per_commit": [{k: v[k] for k in ("sha", "waves", "method", "conflict")}
                       for v in per_commit],
    }
