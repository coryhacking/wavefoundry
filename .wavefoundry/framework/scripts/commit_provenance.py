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

# A commit input is 7-40 lowercase hex. Syntax is only the first guard; callers
# must also canonicalize it through local git before treating it as authority.
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")

# The landing grammar is anchored to the commit subject.  Quoted/reverted text
# and later descriptive ids are not provenance.
_LAND_SUBJECT_RE = re.compile(
    r"^Land\s+waves?\s+"
    r"(?P<ids>1[0-9a-z]{4,}(?:\s*(?:,|and|\+)\s*1[0-9a-z]{4,})*)"
    r"(?=\s*(?::|\bfor\b|$))",
    re.IGNORECASE,
)
# Lifecycle ids start with '1' then >=4 more [0-9a-z] (e.g. 1shv4). A bare "1" or a
# version like "1.13.0" cannot match (needs 4+ trailing base36 chars, no '.').
_WAVE_ID_TOKEN_RE = re.compile(r"\b(1[0-9a-z]{4,})\b")
_LANDING_COMMIT_RE = re.compile(
    r"(?im)^\s*landing-commit\s*:\s*`?([0-9a-f]{7,40})`?\s*$"
)
_CHANGE_ID_RE = re.compile(r"(?im)^Change ID:\s*`([^`]+)`\s*$")

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


def canonical_commit(root: Path, sha: str) -> Optional[str]:
    """Return the unique full local commit id, or ``None`` when not authoritative."""
    sha = (sha or "").strip().lower()
    if not is_valid_sha(sha):
        return None
    out = _git(root, "rev-parse", "--verify", f"{sha}^{{commit}}")
    if not out:
        return None
    full = out.strip().lower()
    return full if re.fullmatch(r"[0-9a-f]{40}", full) else None


def _without_fenced_code(markdown: str) -> str:
    """Exclude example payloads from metadata association."""
    lines: list[str] = []
    fence = ""
    for line in (markdown or "").splitlines():
        stripped = line.lstrip()
        marker = "```" if stripped.startswith("```") else (
            "~~~" if stripped.startswith("~~~") else ""
        )
        if marker:
            fence = "" if fence == marker else marker if not fence else fence
            continue
        if not fence:
            lines.append(line)
    return "\n".join(lines)


def resolve_via_message(root: Path, sha: str) -> list[str]:
    """Path (a): parse ``git show -s --format=%B <sha>`` for landed wave ids.

    Returns the ordered, de-duplicated wave-id tokens named by the landing
    convention, or an empty list when the commit does not name a wave.
    """
    if not is_valid_sha(sha):
        return []
    canonical = canonical_commit(root, sha)
    if canonical is None:
        return []
    body = _git(root, "show", "-s", "--format=%s", canonical)
    if not body:
        return []
    match = _LAND_SUBJECT_RE.match(body.strip())
    if match is None:
        return []
    ids: list[str] = []
    for tok in _WAVE_ID_TOKEN_RE.findall(match.group("ids")):
        if tok not in ids:
            ids.append(tok)
    return ids


def resolve_via_evidence(root: Path, sha: str) -> list[str]:
    """Path (b): an explicit ``landing-commit: <sha>`` wave association.

    Generic hexadecimal mentions are deliberately non-authoritative: wave
    records routinely cite fixture, comparison, and prior-wave commits.
    """
    canonical = canonical_commit(root, sha)
    if canonical is None:
        return []
    waves_dir = root / "docs" / "waves"
    if not waves_dir.is_dir():
        return []
    found: list[str] = []
    for wave_md in sorted(waves_dir.glob("*/wave.md")):
        try:
            text = wave_md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        markers = _LANDING_COMMIT_RE.findall(_without_fenced_code(text))
        if any(canonical_commit(root, marker) == canonical for marker in markers):
            # Wave dirs are "<id> <slug>"; return the id token so both resolution
            # paths speak the same vocabulary (the message path returns ids too).
            wid = wave_md.parent.name.split(" ", 1)[0]
            if wid and wid not in found:
                found.append(wid)
    return found


def blame_line_coverage(
    root: Path, rel_path: str, start: int, end: int
) -> tuple[list[str], dict[str, int], Optional[str]]:
    """``git blame`` a bounded range with committed/uncommitted coverage.

    The file path is confined to the repository (path-traversal guard) and the
    range is passed as ``-L start,end`` argv, never a shell string. Read-only.
    """
    if start < 1 or end < start:
        return [], {}, "invalid line range"
    try:
        root_resolved = root.resolve()
        target = (root / rel_path).resolve()
        target.relative_to(root_resolved)  # raises if outside the repo
    except (ValueError, OSError):
        return [], {}, "path outside repository"
    if not target.is_file():
        return [], {}, "file not found"
    out = _git(root, "blame", "-L", f"{int(start)},{int(end)}", "--porcelain", "--", rel_path)
    if out is None:
        return [], {}, "blame failed (binary or out-of-range)"
    shas: list[str] = []
    _UNCOMMITTED = "0" * 40  # git blame sentinel for a not-yet-committed line
    committed = 0
    uncommitted = 0
    for line in out.splitlines():
        m = re.match(r"^([0-9a-f]{40}) ", line)  # porcelain header lines
        if not m:
            continue
        if m.group(1) == _UNCOMMITTED:
            uncommitted += 1
        else:
            committed += 1
            if m.group(1) not in shas:
                shas.append(m.group(1))
    return shas, {
        "requested_lines": end - start + 1,
        "committed_lines": committed,
        "uncommitted_lines": uncommitted,
    }, None


def blame_line_commits(
    root: Path, rel_path: str, start: int, end: int
) -> tuple[list[str], Optional[str]]:
    """Compatibility wrapper returning only unique committed ids and an error."""
    shas, _coverage, error = blame_line_coverage(root, rel_path, start, end)
    return shas, error


def resolve_commit_to_waves(root: Path, sha: str) -> dict[str, Any]:
    """Combine both paths into an honest verdict.

    ``resolved`` is False (not a fabricated guess) when neither path resolves;
    ``conflict`` is True when the two paths name different waves (reported, never
    silently reconciled).
    """
    requested_sha = (sha or "").strip().lower()
    if not is_valid_sha(requested_sha):
        return {
            "sha": requested_sha, "waves": [], "via_message": [], "via_evidence": [],
            "method": "invalid_sha", "conflict": False, "resolved": False,
        }
    sha = canonical_commit(root, requested_sha)
    if sha is None:
        return {
            "sha": requested_sha, "waves": [], "via_message": [], "via_evidence": [],
            "method": "commit_not_found", "conflict": False, "resolved": False,
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
        "sha": sha, "requested_sha": requested_sha, "waves": union,
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


def _section_text(md_text: str, heading: str) -> str:
    """Return one level-two Markdown section without its heading."""
    lines: list[str] = []
    in_section = False
    wanted = f"## {heading}".lower()
    for line in md_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if in_section:
                break
            in_section = stripped.lower() == wanted
            continue
        if in_section:
            lines.append(line)
    return "\n".join(lines).strip()


def _explicit_refs(md_text: str) -> set[str]:
    return {ref.strip() for ref in re.findall(r"`([^`\n]+)`", md_text) if ref.strip()}


def _file_relevant(md_text: str, rel_path: str) -> bool:
    if not rel_path:
        return False
    normalized = rel_path.replace("\\", "/")
    basename = Path(normalized).name
    for ref in _explicit_refs(md_text):
        clean = ref.split(":", 1)[0].replace("\\", "/")
        if clean in {normalized, basename}:
            return True
    return False


def _provenance_rows_for_wave(
    root: Path, wave_id: str, *, target_path: str = ""
) -> list[dict[str, Any]]:
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
        change_match = _CHANGE_ID_RE.search(text)
        relevant = _file_relevant(text, target_path) if target_path else False
        row: dict[str, Any] = {
            "path": rel,
            "wave_id": wave_id,
            "change_id": change_match.group(1) if change_match else None,
            "relevance": "file_relevant" if relevant else "wave_level",
            "decisions": decisions,
            "rationale": _section_text(text, "Rationale"),
        }
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
    shas, coverage, error = blame_line_coverage(root, rel_path, start, end)
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
        for wave_id in v["waves"]:
            provenance.extend(
                _provenance_rows_for_wave(root, wave_id, target_path=rel_path)
            )
    conflict = any(bool(v.get("conflict")) for v in per_commit)
    partial = bool(coverage.get("uncommitted_lines"))
    return {
        "path": rel_path, "line_start": start, "line_end": end,
        "commits": shas, "waves": waves,
        "resolved": bool(waves), "partial": partial, "coverage": coverage,
        "conflict": conflict, "provenance": provenance,
        "per_commit": [{k: v[k] for k in ("sha", "waves", "via_message",
                                           "via_evidence", "method", "conflict")}
                       for v in per_commit],
    }
