"""Wavefoundry install-log parser and state queries.

Wave 1p35d (1p35h): shared library consumed by ``wave_install_audit`` (MCP
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
# Group 5: optional trailing 'artifact: <path>' or 'expects: <shape>'
_ROW_RE = re.compile(
    r"^\s*-\s+\[([ x~])\]\s+"
    r"(\d+(?:\.\d+)+)\s+"
    r"—\s+(.+?)\s+"
    r"\((seed-\d+|verify|instruction|[A-Za-z_][\w\-]*\.py)\)"
    r"(?:\s+—\s+(?:artifact|expects):\s+(.+?))?"
    r"\s*$"
)

_PHASE_HEADING_RE = re.compile(r"^##\s+Phase\s+(\d+)\b", re.IGNORECASE)


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
        """
        return self.kind in ("seed", "script") and self.target is not None


def parse_row(line: str, phase: int) -> Optional[Row]:
    """Parse a single line into a Row, or return None if the line isn't a row."""
    m = _ROW_RE.match(line)
    if not m:
        return None
    state, number, slug, source, target = m.groups()
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
        assert r.target is not None  # invariant: needs_artifact_check implies target is set
        # The artifact path is interpreted relative to the project root.
        artifact_path = (project_root / r.target).resolve()
        if not artifact_path.exists():
            missing.append((r, artifact_path))
    return missing


def is_complete(rows: list[Row]) -> bool:
    """True iff every row is terminal (``[x]`` or ``[~]``) — no rows pending."""
    return all(r.is_terminal for r in rows)


def read_install_log(project_root: Path) -> Optional[str]:
    """Read the live install log content from ``<project_root>/.wavefoundry/install-log.md``.

    Returns None when the file does not exist; the caller can use that to
    surface an actionable error pointing at ``install-wavefoundry.md`` for
    bootstrap instructions.
    """
    log_path = project_root / INSTALL_LOG_REL_PATH
    if not log_path.exists():
        return None
    return log_path.read_text(encoding="utf-8")
