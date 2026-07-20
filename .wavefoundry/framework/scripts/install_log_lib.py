"""Wavefoundry install-log parser and state queries.

Wave 1p35d (1p35h): shared library consumed by ``wf_audit_install`` (MCP
tool) and any other tooling that needs to read the install log without
duplicating the parser.

The canonical schema lives at ``docs/references/install-log-format.md``.
Row format summary:

- Seed-driven:     ``- [STATE] N.M — <slug> (seed-NNN) — artifact: <path>``
- Script-driven:   ``- [STATE] N.M — <slug> (<script>.py) — artifact: <path>``
- Verification:    ``- [STATE] N.M — <slug> (verify) — expects: <return shape>``
- Instruction:     ``- [STATE] N.M — <slug> (instruction)``

Where ``STATE`` is one of ``[ ]`` (pending), ``[x]`` (done), or ``[~]``
(not applicable, treated as terminal).

The parser is permissive on surrounding prose: lines that don't match the row
regex are silently passed through. Phases are detected from H2 headings
matching ``## Phase N`` (case-insensitive).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Canonical filename for the live install log (operator-owned instance).
# Lives at .wavefoundry/install-log.md (under the project's .wavefoundry/ dir).
INSTALL_LOG_REL_PATH = ".wavefoundry/install-log.md"


# Row regex
# Group 1: state character ( | x | ~)
# Group 2: N.M[.K...] step number
# Group 3: slug (greedy until the parenthesized source tag)
# Group 4: source tag (seed-NNN | verify | instruction | <script>.py)
# Group 5: the trailing field KEYWORD ('artifact' or 'expects'), when present
# Group 6: the trailing field VALUE (the path for 'artifact:', or the return shape for 'expects:')
#
# Wave 1p8gw: group 5 now captures the field keyword so the parser knows whether the trailing value is
# a stat-able artifact PATH ('artifact:') or a verification DESCRIPTION ('expects:'). Previously both
# landed in `target` with no way to tell them apart, so a row whose `artifact:` value is a prose
# verification description (e.g. step 1.2: "the committed `.mcp.json` names ... AND ... exits 0") was
# treated as a literal file path and stat'd — the description-as-path field defect that broke
# wf_audit_install on a native-Windows install.
# Wave 1p8gw (rev.): the source tag also accepts MULTI-SEED / qualified forms shipped in the template —
# ``(seed-080 + seed-090)`` and ``(seed-110 / conditional)`` — which the single-seed pattern silently
# dropped (rows 2.2 / 2.8 never parsed → never validated). A multi-seed tag still ``startswith("seed-")``
# so kind-detection is unchanged.
# Wave 1p9bh: the row separators (originally required to be a literal em dash `—`) are now matched
# ENCODING-AGNOSTICALLY — an em/en dash, a hyphen, OR mojibake (e.g. `â€"` from a non-UTF-8 PowerShell
# write) all parse — by matching the separator as an opaque non-space token rather than a specific
# character. The parser still anchors on the checkbox, the dotted step number, and the `(source)`
# parenthetical, so a mis-encoded log parses instead of silently yielding ZERO rows (which then read as
# vacuously "complete"). The six capture groups (state, number, slug, source, field, value) are
# preserved for parse_row.
_ROW_RE = re.compile(
    r"^\s*-\s+\[([ x~])\]\s+"
    r"(\d+(?:\.\d+)+)\s+"
    r"(?:\S+\s+)?"
    r"(.+?)\s+"
    r"\((seed-\d+(?:\s*[+/]\s*(?:seed-\d+|[A-Za-z][\w\-]*))*|verify|instruction|[A-Za-z_][\w\-]*\.py)\)"
    r"(?:\s+\S+\s+(artifact|expects):\s+(.+?))?"
    r"\s*$"
)

_PHASE_HEADING_RE = re.compile(r"^##\s+Phase\s+(\d+)\b", re.IGNORECASE)


# Wave 1p8gw (rev. after adversarial review): classify an ``artifact:`` value as a stat-able PATH only
# when, AFTER stripping markdown backticks and one trailing parenthetical aside, it is a SINGLE
# path-shaped token. A multi-clause / prose value (multiple backtick spans, a leading sentence, or a
# conjunction/sentence verb) is a verification DESCRIPTION and must NOT be stat'd (mirrors ``expects:``).
#
# CRITICAL: the SHIPPED template backtick-wraps EVERY path (``- … — artifact: `docs/repo-profile.json` ``),
# so the classifier MUST strip backticks FIRST. The earlier "any backtick ⇒ prose" rule made 0/15
# rows stat-able and turned wf_audit_install CHECK 2 into a silent no-op. Shipped-template examples:
#   2.3  `docs/repo-profile.json`                                   -> PATH  (single span)
#   2.2  `docs/waves/00000 wave-zero-plans-and-specs/wave.md` (or…) -> PATH  (single span + aside)
#   1.2  the committed `.mcp.json` names … AND … exits 0            -> DESC  (prose around spans)
#   2.13 drift entries in `docs/workflow-config.json`              -> DESC  (leading sentence)
_ARTIFACT_TRAILING_ASIDE_RE = re.compile(r"\s*\([^()]*\)\s*$")
_SINGLE_BACKTICK_SPAN_RE = re.compile(r"^`([^`]+)`$")
_PROSE_CLAUSE_MARKERS = (" AND ", " OR ", " names ", " exits ", " returns ", " expects ")


def _strip_one_trailing_aside(value: str) -> str:
    return _ARTIFACT_TRAILING_ASIDE_RE.sub("", value).strip()


def _artifact_path_token(value: str) -> Optional[str]:
    """Return the stat-able path token from an ``artifact:`` value, or None if it is a prose clause.

    1. Drop one trailing parenthetical aside (e.g. the conditional ``(or mark [~] …)`` on row 2.2).
    2. If the remainder is exactly ONE whole backtick span, use its content; if backticks are present
       but it is NOT a single whole span (prose wrapping spans, e.g. 1.2 / 2.13) → None; otherwise the
       bare remainder is the candidate.
    3. The candidate is a PATH iff it is path-shaped (contains ``/`` or a trailing ``.ext``), carries
       no prose-clause marker, and is a single token modulo a couple of internal directory-name spaces
       (a real path like the wave-zero dir, never a multi-word sentence).
    """
    if not value:
        return None
    core = _strip_one_trailing_aside(value)
    m = _SINGLE_BACKTICK_SPAN_RE.match(core)
    if m:
        candidate = m.group(1).strip()
    elif "`" in core:
        return None
    else:
        candidate = core
    if not candidate:
        return None
    if any(marker in f" {candidate} " for marker in _PROSE_CLAUSE_MARKERS):
        return None
    if "/" not in candidate and not re.search(r"\.[A-Za-z0-9]+$", candidate):
        return None
    if candidate.count(" ") > 2:
        return None
    return candidate


def _artifact_value_is_path(value: str) -> bool:
    """True when an ``artifact:`` value resolves to a single stat-able path token (wave 1p8gw)."""
    return _artifact_path_token(value) is not None


@dataclass(frozen=True)
class Row:
    """A single parsed install-log row."""

    state: str       # ' ', 'x', or '~'
    number: str      # e.g., '1.2', '2.13', '1.3.5'
    slug: str        # short prose description
    kind: str        # 'seed' | 'script' | 'verify' | 'instruction'
    source: str      # 'seed-NNN' | '<script>.py' | 'verify' | 'instruction'
    target: Optional[str]  # artifact path (seed/script) or expected shape (verify); None for instruction
    phase: int       # 1 or 2
    # Wave 1p8gw: which trailing field produced `target` — 'artifact' (a stat-able path on seed/script
    # rows), 'expects' (a verification return shape, never stat'd), or None when the row has no
    # trailing field. Carried explicitly so a description is never confused for a path.
    field: Optional[str] = None

    @property
    def artifact_path(self) -> Optional[str]:
        """The stat-able artifact path (backticks/aside stripped), or None for a prose description.

        Returns the cleaned single path TOKEN for seed/script rows whose ``artifact:`` value is a
        single path (see ``_artifact_path_token`` — strips the shipped template's backtick wrapping and
        any trailing conditional aside); a compound/prose verification artifact resolves to None so
        callers never stat it as a file path (wave 1p8gw)."""
        if self.field != "artifact" or self.kind not in ("seed", "script"):
            return None
        if self.target is None:
            return None
        return _artifact_path_token(self.target)

    @property
    def description(self) -> Optional[str]:
        """The non-path verification text carried by the row, when any.

        This is the ``expects:`` return shape (verify rows) OR an ``artifact:`` value that is actually
        a prose verification clause rather than a stat-able path (wave 1p8gw). None when the row's
        trailing value is a real path or the row has no trailing field."""
        if self.target is None:
            return None
        if self.field == "expects":
            return self.target
        if self.field == "artifact" and not _artifact_value_is_path(self.target):
            return self.target
        return None

    @property
    def is_pending(self) -> bool:
        return self.state == " "

    @property
    def is_done(self) -> bool:
        return self.state == "x"

    @property
    def is_not_applicable(self) -> bool:
        return self.state == "~"

    @property
    def is_terminal(self) -> bool:
        """True if the row is no longer pending — done OR not applicable.

        Used by check 3 (find first unchecked): skip terminal rows.
        """
        return self.state in ("x", "~")

    @property
    def needs_artifact_check(self) -> bool:
        """True iff this row's artifact is an on-disk path we can stat.

        Seed and script rows carry an ``artifact:`` path that must exist when
        the row is marked ``[x]``. Verify and instruction rows do not — verify
        rows carry an ``expects:`` return shape (past event, not stat-able),
        and instruction rows carry no on-disk artifact at all.

        Wave 1p8gw: this is now gated on ``artifact_path`` (a single stat-able path token), so a
        seed/script row whose ``artifact:`` value is a prose verification clause is NOT stat'd — it is
        treated as a verification description, never a file path. This closes the description-as-path
        field defect that made ``wf_audit_install`` verify against bogus "paths".
        """
        return self.artifact_path is not None


def parse_row(line: str, phase: int) -> Optional[Row]:
    """Parse a single line into a Row, or return None if the line isn't a row."""
    m = _ROW_RE.match(line)
    if not m:
        return None
    state, number, slug, source, field, target = m.groups()
    source_clean = source.strip()
    if source_clean.startswith("seed-"):
        kind = "seed"
    elif source_clean == "verify":
        kind = "verify"
    elif source_clean == "instruction":
        kind = "instruction"
    elif source_clean.endswith(".py"):
        kind = "script"
    else:
        # Defensive: regex shouldn't match anything else, but be safe.
        return None
    return Row(
        state=state,
        number=number,
        slug=slug.strip(),
        kind=kind,
        source=source_clean,
        target=target.strip() if target else None,
        phase=phase,
        field=field.strip() if field else None,
    )


def parse_log(text: str) -> list[Row]:
    """Parse the install-log markdown into a list of Rows in document order.

    Rows are tagged with their phase based on the most recent ``## Phase N`` heading.
    Rows that appear before any phase heading are tagged with phase=0 (which
    callers can filter out or treat as malformed).
    """
    rows: list[Row] = []
    current_phase = 0
    for line in text.splitlines():
        m_phase = _PHASE_HEADING_RE.match(line)
        if m_phase:
            try:
                current_phase = int(m_phase.group(1))
            except ValueError:
                pass
            continue
        row = parse_row(line, current_phase)
        if row is not None:
            rows.append(row)
    return rows


def filter_phase(rows: list[Row], phase: Optional[int]) -> list[Row]:
    """Return rows filtered by phase (None = no filter)."""
    if phase is None:
        return list(rows)
    return [r for r in rows if r.phase == phase]


def first_unchecked_row(rows: list[Row]) -> Optional[Row]:
    """Return the first row whose state is ``[ ]`` (pending). None if all are terminal."""
    for r in rows:
        if r.is_pending:
            return r
    return None


def checked_rows_missing_artifact(rows: list[Row], project_root: Path) -> list[tuple[Row, Path]]:
    """For each ``[x]`` row with an artifact, return (row, expected_path) when the artifact is absent.

    Verify rows and instruction rows are skipped (no on-disk artifact to check).
    Returns an empty list when all checked rows are valid.
    """
    missing: list[tuple[Row, Path]] = []
    for r in rows:
        if not r.is_done:
            continue
        if not r.needs_artifact_check:
            continue
        # Wave 1p8gw: stat the classified artifact PATH, never a prose verification description.
        rel = r.artifact_path
        assert rel is not None  # invariant: needs_artifact_check implies artifact_path is set
        artifact_path = (project_root / rel).resolve()
        if not artifact_path.exists():
            missing.append((r, artifact_path))
    return missing


def is_complete(rows: list[Row]) -> bool:
    """True iff there is at least one row AND every row is terminal (``[x]`` or ``[~]``).

    Wave 1p9bh: an EMPTY list is NOT complete. Previously this was ``all(...)``, which is vacuously
    ``True`` for zero rows — so a present-but-unparseable install log (e.g. a non-UTF-8 write mojibake'd
    the row separators, so ``parse_log`` returned ``[]``) read as "install complete." ``read_install_log``
    returns ``None`` when no log exists, so ``is_complete`` is only reached for a log that is present; a
    present log with zero parseable rows is genuinely not complete."""
    return bool(rows) and all(r.is_terminal for r in rows)


def is_unparseable(text: Optional[str], rows: list[Row]) -> bool:
    """Wave 1p9bh: True when an install log is PRESENT with install-log-shaped content but yielded ZERO
    parsed rows — a strong signal of encoding corruption (e.g. a non-UTF-8 write mojibake'd the row
    separators). The caller must surface this as an ERROR, never treat it as complete. Only flags text
    that looks like an install log (a ``## Phase`` heading or a ``- [ ]`` checkbox line — both ASCII, so
    they survive em-dash mojibake), not arbitrary prose or a blank file."""
    if not text or not text.strip() or rows:
        return False
    if _PHASE_HEADING_RE.search(text) or re.search(r"^\s*-\s+\[[ x~]\]", text, re.MULTILINE):
        return True
    # Wave 1p9hj: a genuinely non-UTF-8 log (UTF-16 BOM, or cp1252 written by a bare PowerShell
    # Set-Content/Out-File) read with errors="replace" (see read_install_log) yields U+FFFD replacement
    # chars and/or interleaved NUL bytes, and its ASCII markers no longer match the patterns above — so
    # the earlier looks-like-an-install-log heuristic misses it. Classify it unparseable so the audit
    # surfaces an actionable encoding error instead of vacuous "install complete". A clean UTF-8 log
    # never contains U+FFFD or NUL, so this cannot false-positive on a valid (if row-less) log.
    return "�" in text or "\x00" in text


def write_install_log(project_root: Path, content: str) -> Path:
    """Wave 1p9bh: write the install log as UTF-8 (never the platform default / cp1252), so the row
    separators survive. The framework-owned write path — agents must use this (or an explicit
    ``-Encoding utf8`` write) rather than a bare PowerShell ``Set-Content``/``Out-File`` that would
    mojibake the em dashes. Returns the path written."""
    log_path = project_root / INSTALL_LOG_REL_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(content, encoding="utf-8", newline="")
    return log_path


def read_install_log(project_root: Path) -> Optional[str]:
    """Read the live install log content from ``<project_root>/.wavefoundry/install-log.md``.

    Returns None when the file does not exist; the caller can use that to
    surface an actionable error pointing at ``install-wavefoundry.md`` for
    bootstrap instructions.
    """
    log_path = project_root / INSTALL_LOG_REL_PATH
    if not log_path.exists():
        return None
    # Wave 1p9hj: errors="replace" so a non-UTF-8 log (UTF-16 BOM / cp1252 from a bare PowerShell
    # Set-Content/Out-File on Windows) decodes without raising UnicodeDecodeError. Without this the
    # strict read raised BEFORE is_unparseable() (the 1p9bh safety net) could classify it, crashing
    # wf_audit_install on Windows. The replacement chars this produces are what is_unparseable keys
    # on to surface an actionable "install log unparseable" error rather than vacuous success.
    return log_path.read_text(encoding="utf-8", errors="replace")
