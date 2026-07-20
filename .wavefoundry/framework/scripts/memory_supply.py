#!/usr/bin/env python3
"""Evidence-derived memory candidate drafting (wave 1stwm / change 1stwk).

Turns a wave's OWN typed review evidence into candidate memory records so the
memory corpus fills from work the wave already did, instead of staying empty
until someone hand-authors records. Two local, read-only sources:

  - each admitted change doc's ``## Decision Log`` -> ``decision`` candidates,
  - the canonical ``events.jsonl`` heads' repaired real-defect findings ->
    ``failed_attempt`` (a single repair) or ``fragile_file`` (a file repaired
    more than once in the wave) candidates.

CONSERVATIVE by design (council re-scope): only durable-shaped signals with a
concrete code anchor are drafted, never every material finding. A single-wave
``review_finding`` that was not a repaired defect is ephemeral wave state and is
skipped. The conversational kinds (``operator_preference`` /
``environment_gotcha`` / ``dependency_gotcha``) emerge from conversation this
tool refuses to read; they are structurally unavailable here and left to native
memory and operator authoring.

Never auto-promotes: drafts are the raw material for ``candidate`` records a
focused agent validates against their evidence and current target. The typed
validation tool records promote/retain/reject/rewrite while preserving the
source disposition. Sources are ONLY the typed ledger + Decision Logs, never a
raw transcript. Each draft is stamped with the measured
``source_exploration_cost`` (the producing wave's consumed retrieval tokens,
from its 1stwj telemetry) as the grounding unit the 1svuk
estimated-exploration-avoided category reads.
"""
from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any, Optional

from chunker import _EXT_TO_LANGUAGE
from review_evidence import read_review_event_ledger, current_synthesis_heads

DEFAULT_DRAFT_LIMIT = 20

_BACKTICK_RE = re.compile(r"`([^`]+)`")
# The durable, committed 1stwj telemetry projection embedded in wave.md.
_CE_STATE_RE = re.compile(
    r"<!-- wave:context-efficiency-state (\{.*?\}) -->", re.DOTALL
)
_PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_])((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+"
    r"|[A-Za-z0-9_.-]+\.[A-Za-z][A-Za-z0-9]{0,8})(?::\d+(?::\d+)?)?"
)
_ADMITTED_CHANGE_RE = re.compile(r"(?m)^Change ID:\s*`([^`]+)`\s*$")
_NON_IMPLEMENTATION_EXTENSIONS = {
    ".json", ".jsonc", ".yaml", ".yml", ".toml",
    ".md", ".markdown", ".xml", ".xsd", ".xsl", ".xslt", ".svg",
}
_IMPLEMENTATION_EXTENSIONS = (
    set(_EXT_TO_LANGUAGE) - _NON_IMPLEMENTATION_EXTENSIONS
)


def _wave_id_token(wave_id: str) -> str:
    """The leading lifecycle-id token of a wave id ("1stwm memory-supply" -> "1stwm")."""
    return (wave_id or "").strip().split(" ", 1)[0]


def resolve_wave_dir(root: Path, wave_id: str) -> tuple[Optional[Path], Optional[str]]:
    """Resolve an exact id/full name or a unique lifecycle-id/name prefix."""
    query = (wave_id or "").strip()
    if not query:
        return None, "wave_not_found"
    waves_dir = root / "docs" / "waves"
    if not waves_dir.is_dir():
        return None, "wave_not_found"
    try:
        root_real = root.resolve(strict=True)
        dirs = [
            path
            for path in sorted(waves_dir.iterdir())
            if path.is_dir()
            and not path.is_symlink()
            and path.resolve(strict=True).is_relative_to(root_real)
        ]
    except (OSError, RuntimeError):
        return None, "wave_not_found"
    exact = [
        path for path in dirs
        if path.name == query or path.name.split(" ", 1)[0] == query
    ]
    if len(exact) == 1:
        return exact[0], None
    matches = [
        path for path in dirs
        if path.name.startswith(query)
        or path.name.split(" ", 1)[0].startswith(query)
    ]
    if len(matches) == 1:
        return matches[0], None
    return None, "ambiguous_wave_id" if matches else "wave_not_found"


def _wave_dir_for_id(root: Path, wave_id: str) -> Optional[Path]:
    path, _error = resolve_wave_dir(root, wave_id)
    return path


def _backtick_refs(text: str) -> list[str]:
    return [r.strip() for r in _BACKTICK_RE.findall(text or "") if r.strip()]


def _contained_source_file(wave_dir: Path, path: Path) -> bool:
    try:
        wave_real = wave_dir.resolve(strict=True)
        path_real = path.resolve(strict=True)
        return (
            not wave_dir.is_symlink()
            and not path.is_symlink()
            and path_real.is_relative_to(wave_real)
            and path.is_file()
        )
    except (OSError, RuntimeError):
        return False


def _code_targets(refs: list[str]) -> list[str]:
    """Keep only refs that name a concrete code anchor (path or ``symbol:``).

    Drops wave/change ids (which carry a space), bare event ids, and version
    strings. A ``foo.py:8`` line anchor is normalized to ``foo.py`` so it
    matches ``match_targets``. Order-preserving and de-duplicated.
    """
    out: list[str] = []
    for ref in refs:
        ref = ref.strip()
        if not ref:
            continue
        if ref.startswith("symbol:") or ref.startswith("community:"):
            out.append(ref)
            continue
        if " " in ref:  # "1stwk-feat slug", "Land wave 1abcd" — not a code path
            continue
        base = ref.split(":", 1)[0]  # strip a trailing :line[:col] anchor
        suffix = Path(base).suffix.lower()
        if suffix in _IMPLEMENTATION_EXTENSIONS:
            out.append(base)
    seen: set[str] = set()
    deduped: list[str] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped


def _text_refs(*values: Any) -> list[str]:
    """Explicit backtick/path refs from canonical evidence string fields."""
    refs: list[str] = []
    for value in values:
        text = str(value or "")
        refs.extend(_backtick_refs(text))
        refs.extend(match.group(1) for match in _PATH_TOKEN_RE.finditer(text))
    return refs


def _admitted_change_ids(wave_dir: Path) -> list[str]:
    if not _contained_source_file(wave_dir, wave_dir / "wave.md"):
        return []
    try:
        text = (wave_dir / "wave.md").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    return list(dict.fromkeys(_ADMITTED_CHANGE_RE.findall(text)))


def _admitted_change_docs(wave_dir: Path) -> list[Path]:
    docs: list[Path] = []
    for change_id in _admitted_change_ids(wave_dir):
        matches = [
            path for path in wave_dir.glob("*.md")
            if path.name != "wave.md"
            and _contained_source_file(wave_dir, path)
            and (path.stem == change_id or path.stem.startswith(change_id + " "))
        ]
        if len(matches) == 1:
            docs.append(matches[0])
    return docs


def _split_markdown_row(line: str) -> list[str]:
    """Split a pipe row while preserving escaped and inline-code pipes."""
    text = line.strip().strip("|")
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    in_code = False
    for char in text:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
            current.append(char)
        elif char == "`":
            in_code = not in_code
            current.append(char)
        elif char == "|" and not in_code:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    cells.append("".join(current).strip())
    return cells


def _decision_log_rows(text: str) -> list[dict[str, str]]:
    """Extract ``## Decision Log`` data rows as ``{decision, reason, alternatives, refs}``.

    The table is ``Date | Decision | Reason | Alternatives``; the header and the
    ``|---|`` separator are dropped. Empty when the doc has no Decision Log.
    """
    rows: list[dict[str, str]] = []
    in_section = False
    header_seen = False
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if in_section:
                break
            in_section = stripped.lower().startswith("## decision log")
            header_seen = False
            continue
        if not in_section or not stripped.startswith("|"):
            continue
        cells = _split_markdown_row(stripped)
        if set("".join(cells)) <= set("-: "):  # the |---|---| separator
            continue
        if not header_seen:  # first row is the column header
            header_seen = True
            continue
        decision = cells[1] if len(cells) > 1 else ""
        if not decision:
            continue
        rows.append({
            "decision": decision,
            "reason": cells[2] if len(cells) > 2 else "",
            "alternatives": cells[3] if len(cells) > 3 else "",
            "refs": _backtick_refs(" ".join(cells)),
        })
    return rows


def source_exploration_cost(wave_dir: Path) -> int:
    """Measured consumed-token cost of the wave, from its 1stwj telemetry.

    Prefers the live SQLite write-through authority and falls back to the
    durable ``<!-- wave:context-efficiency-state -->`` projection embedded in
    ``wave.md`` only when no live wave state exists. Returns ``request_debit +
    response_debit`` (the tokens actually spent flowing through the wave's
    retrieval calls). A measured quantity, never a constant; 0 when neither
    authority has telemetry for the wave.
    """
    # SQLite is the live write-through authority. Closed projections remain a
    # portable fallback for copied/older projects whose telemetry store is absent.
    try:
        import context_efficiency as ce
        snapshot = ce.read_wave_snapshot(wave_dir.parents[2], wave_dir.name)
        totals = snapshot.get("totals") or {}
        live = max(
            0,
            int(totals.get("request_debit", 0))
            + int(totals.get("response_debit", 0)),
        )
        conn = ce._open_read_store(wave_dir.parents[2])
        present = False
        if conn is not None:
            try:
                present = bool(
                    conn.execute(
                        "SELECT 1 FROM wave_state WHERE wave_id=? LIMIT 1",
                        (wave_dir.name,),
                    ).fetchone()
                    or conn.execute(
                        "SELECT 1 FROM telemetry_event WHERE wave_id=? LIMIT 1",
                        (wave_dir.name,),
                    ).fetchone()
                )
            finally:
                conn.close()
        if present:
            return live
    except (ImportError, OSError, ValueError, TypeError):
        pass
    wave_md = wave_dir / "wave.md"
    if not _contained_source_file(wave_dir, wave_md):
        return 0
    try:
        text = wave_md.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    m = _CE_STATE_RE.search(text)
    if not m:
        return 0
    try:
        state = json.loads(m.group(1))
        totals = state.get("totals") or {}
        return max(0, int(totals.get("request_debit", 0)) + int(totals.get("response_debit", 0)))
    except (ValueError, TypeError):
        return 0


def _truncate(text: str, limit: int = 240) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def draft_candidates(
    root: Path, wave_id: str, *, limit: Optional[int] = DEFAULT_DRAFT_LIMIT
) -> list[dict[str, Any]]:
    """Draft candidate memory records from a wave's typed evidence.

    Returns a deterministic list of draft dicts, each carrying
    ``kind``, ``title``, ``summary``, ``evidence`` (refs), ``targets`` (code
    anchors), ``source_event`` (what it was drafted from), and the measured
    ``source_exploration_cost``. ``limit=None`` returns the complete eligible
    source set so lifecycle gates cannot silently ignore rows beyond the public
    page size. Never writes; the caller gates promotion.
    """
    wave_dir = _wave_dir_for_id(root, wave_id)
    if wave_dir is None:
        return []
    wid = _wave_id_token(wave_id)
    cost = source_exploration_cost(wave_dir)
    drafts: list[dict[str, Any]] = []

    # (A) Decision Log rows -> `decision` candidates (durable by definition).
    for change_doc in _admitted_change_docs(wave_dir):
        try:
            text = change_doc.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        change_id = change_doc.stem
        for row in _decision_log_rows(text):
            targets = _code_targets(row["refs"])
            if not targets:  # conservative: a decision needs a code anchor to attach to
                continue
            reason = f" Rationale: {row['reason']}." if row["reason"] else ""
            decision_identity = hashlib.sha256(
                (row["decision"].strip() + "\n" + row["reason"].strip()).encode("utf-8")
            ).hexdigest()[:16]
            drafts.append({
                "kind": "decision",
                "title": f"Decision: {_truncate(row['decision'], 60)}",
                "summary": f"Decision (wave {wid}): {row['decision']}.{reason}",
                # Bare refs (no backticks): the renderer wraps them and
                # find_duplicates compares the same backtick-free contents.
                "evidence": [change_id, wid],
                "targets": targets,
                "source_event": f"decision-log:{change_id}:{decision_identity}",
                "source_exploration_cost": cost,
            })

    # (B) Repaired real-defect findings -> `failed_attempt` / `fragile_file`.
    event_path = wave_dir / "events.jsonl"
    if event_path.exists() and not _contained_source_file(wave_dir, event_path):
        records = ()
    else:
        records, _errors = read_review_event_ledger(wave_dir)
    evidence_by_id = {
        str(record.get("evidence_record_id")): record
        for record in records
        if record.get("record_type") == "executable_evidence"
        and record.get("evidence_record_id")
    }
    heads = current_synthesis_heads(records)
    repaired: list[dict[str, Any]] = []
    for finding_id, head in heads.items():
        if head.get("disposition") != "do_now":
            continue  # only a real, actionable issue
        if head.get("repair_execution_state") != "completed":
            continue  # only one that was actually fixed (a durable lesson)
        rationale = str(head.get("disposition_rationale") or "")
        evidence_id = str(head.get("evidence_record_id") or "")
        evidence_record = evidence_by_id.get(evidence_id, {})
        targets = _code_targets(_text_refs(
            evidence_record.get("artifact_or_test_id"),
            evidence_record.get("public_path"),
            evidence_record.get("command_or_fixture"),
        ))
        if not targets:  # need a concrete code anchor to attach the advisory to
            continue
        repaired.append({
            "finding_id": finding_id, "targets": targets, "rationale": rationale,
            "evidence_record_id": evidence_id,
        })

    # A file repaired more than once IN THIS WAVE is a fragile_file signal; a
    # single repair is a failed_attempt. (Cross-wave repetition is a corpus-wide
    # pass, not a single-wave concern, so it is deliberately not attempted here.)
    by_target: dict[str, list[dict[str, Any]]] = {}
    for item in repaired:
        for t in item["targets"]:
            by_target.setdefault(t, []).append(item)
    used: set[str] = set()
    for target, items in by_target.items():
        if len(items) < 2:
            continue
        fids = [it["finding_id"] for it in items]
        drafts.append({
            "kind": "fragile_file",
            "title": f"Fragile: {target}",
            "summary": (
                f"{target} required {len(items)} separate repairs during wave "
                f"{wid}; treat it as fragile and re-verify edits with the full "
                "suite before relying on them."
            ),
            "evidence": [*fids, wid],
            "targets": [target],
            "source_event": f"repeated-repairs:{wid}:{target}",
            "source_exploration_cost": cost,
        })
        used.update(fids)

    for item in repaired:
        if item["finding_id"] in used:
            continue  # already represented by a fragile_file record
        evidence = [item["finding_id"]]
        if item["evidence_record_id"]:
            evidence.append(item["evidence_record_id"])
        evidence.append(wid)
        drafts.append({
            "kind": "failed_attempt",
            "title": f"Repaired defect {item['finding_id']}",
            "summary": (
                f"Real defect fixed in wave {wid}: {_truncate(item['rationale'])}"
            ),
            "evidence": evidence,
            "targets": item["targets"],
            "source_event": f"finding:{wid}:{item['finding_id']}",
            "source_exploration_cost": cost,
        })

    if limit is None:
        return drafts
    return drafts[: max(0, int(limit))]
