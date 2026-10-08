"""Vocabulary census (wave 1z8mm, change 1z826, Requirement 5; AC-3).

Mirrors ``tests/test_record_layout_census.py``. Every non-test ``.py`` under
``.wavefoundry/framework/scripts/`` except ``vocabulary_profile.py`` is scanned,
line by line, for each default vocabulary MARKER as a boundary-aware substring:
the record filename, the id key, the record title, the summary and member
headings, the member id and status labels, and the ``Wave:`` back-reference.
The bare tier names are not markers (they occur throughout prose). A line-based
scan sees every source shape a site can take -- an equality, an f-string part,
a regex source, a concatenation operand -- because the marker text is on the
line in each; the four planted controls below prove that.

Every hit must either be routed through ``vocabulary_profile`` (so it is gone)
or be named in ``ALLOWLIST`` keyed on file and a distinguishing snippet of the
line. Reasons: ``comment``, ``docstring``, ``message`` (human-facing prose),
``frozen_oracle`` (a pinned historical scaffold compared byte-for-byte) and
``retired_name`` (a retired name or legacy placeholder text, not a live record
marker). Construction and parse sites are never allowlisted. The writers were
routed by change ``1z8qi``, which removed the temporary pending-writer class.
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]

# Boundary-aware so ``upgrade-wave.md``, ``wave.md-file`` style prose and
# ``sub-wave-id`` do not match; ``Next Wave:`` does (a planted control pins it).
# A backslash before a space, dot, hyphen or ``#`` is tolerated, so a regex
# source that escapes the marker (``wave\.md``, ``Change\ ID``) is still seen.
# Known limit: a marker split across an alternation or concatenation
# (``(?:Change|Item) Status``, ``"Change" + " ID"``) has no contiguous marker
# text and is not seen here; the second-profile tests catch those readers.
_E = r"\\?"  # an optional escaping backslash
MARKER_RE = re.compile(
    rf"(?<![\w.-])wave{_E}\.md\b"
    rf"|(?<![\w-])wave{_E}-id(?![\w])"
    rf"|{_E}#{_E}#{_E} Changes\b"
    rf"|{_E}#{_E}#{_E} Wave{_E} Summary\b"
    rf"|{_E}#{_E} Wave{_E} Record\b"
    rf"|\bChange{_E} ID\b"
    rf"|\bChange{_E} Status\b"
    rf"|(?<![\w-])Wave:"
)

CENSUS_EXCLUDED_FILES = frozenset({"vocabulary_profile.py"})
CENSUS_EXCLUDED_DIRS = frozenset({"tests", "__pycache__", ".pytest_cache"})

ALLOWED_REASONS = frozenset({"comment", "docstring", "message", "frozen_oracle", "retired_name"})

# {(file, distinguishing snippet of the source line): reason}
ALLOWLIST: dict[tuple[str, str], str] = {
    ('commit_provenance.py', 'Returns the ordered, de-duplicated wave-id tokens named by the landing'): 'docstring',
    ('context_efficiency.py', 'pending durable generations into the marker-owned ``wave.md`` checkpoint.'): 'docstring',
    ('context_efficiency.py', 'reload, and upgrade boundaries project durable totals into `wave.md`.'): 'docstring',
    ('dashboard_lib.py', '# Accept both "Change Status: `value`" (canonical) and plain "Status: value" (fallback for'): 'comment',
    ('dashboard_server.py', '(the common ``docs/waves/<id>/<change>.md`` / ``wave.md`` editing pattern). These trees ge'): 'docstring',
    ('gardener_metadata.py', '``Status`` and ``Change Status`` describe workflow progress, not the'): 'docstring',
    ('gardener_metadata.py', '# `Change Status:` and `Status:`, and 794 of 1457 documents in this'): 'comment',
    ('index_state_store.py', '- ``Land …`` subjects attribute every wave-id token in the subject to the'): 'docstring',
    ('index_state_store.py', '"""Wave id from a ``docs/waves/<wave-id> <slug>/…`` path, if shaped so."""'): 'docstring',
    ('indexer.py', '# ledgers are machine authority, not retrieval content.  Generated ``wave.md``'): 'comment',
    ('indexer.py', '# state.  Search the generated wave.md current-head projection,'): 'comment',
    ('install_log_lib.py', '#   2.2  `docs/waves/00000 wave-zero-plans-and-specs/wave.md` (or…) -> PATH  (single span '): 'comment',
    ('lifecycle_gate_support.py', '(exception type plus detail, never an absolute path).  Every ``wave.md``'): 'docstring',
    ('memory_records.py', '"""The ``Status:`` value of a wave directory\'s wave.md; None when unreadable."""'): 'docstring',
    ('memory_supply.py', '# The durable, committed 1stwj telemetry projection embedded in wave.md.'): 'comment',
    ('memory_supply.py', '``wave.md`` only when no live wave state exists. Returns ``request_debit +'): 'docstring',
    ('record_paths.py', 'check need directories WITHOUT a ``wave.md`` too). Nested layout: a'): 'docstring',
    ('record_paths.py', "``wave.md`` (a wave folder's own subdirectories are evidence, not waves)."): 'docstring',
    ('record_paths.py', '"""Every wave folder (a directory containing ``wave.md``) under the waves'): 'docstring',
    ('render_agent_surfaces.py', '"- Load the target change doc (`docs/waves/<wave-id>/<change-id>.md` or `docs/plans/<chang'): 'message',
    ('render_agent_surfaces.py', '("- Load the target change doc (`docs/waves/<wave-id>/<change-id>.md` or `docs/plans/<chan'): 'message',
    ('render_agent_surfaces.py', 'in `wave.md`, and renders'): 'docstring',
    ('render_agent_surfaces.py', 'Never put canonical JSONL inside `wave.md`. Without MCP, create the'): 'docstring',
    ('render_platform_surfaces.py', '"wave-id",'): 'retired_name',
    ('review_evidence.py', '"""Resolve the fixed sibling authority from a wave directory or ``wave.md``."""'): 'docstring',
    ('review_evidence.py', 'No wave.md declaration or retained state is consulted, so a tampered or'): 'docstring',
    ('review_evidence.py', 'may hold this lock across a wave.md mutation and the telemetry projection'): 'docstring',
    ('review_evidence.py', 'records, so every read fails closed. An unreadable ``wave.md`` also'): 'docstring',
    ('review_evidence.py', 'fixed sibling of ``wave.md``) and roster/config parsing stays at'): 'docstring',
    ('review_evidence.py', 'wave_path: The wave directory or its ``wave.md`` path. ``None`` is'): 'docstring',
    ('review_evidence.py', 'wave_text: Optional already-read ``wave.md`` text; when omitted it is'): 'docstring',
    ('review_policy.py', '# Sorted by change_id. The caller collects change ids from `wave.md` in'): 'comment',
    ('review_policy.py', '# DOCUMENT order, so reordering the `## Changes` entries -- pure'): 'comment',
    ('upgrade_extensions.py', 'wave-id, title, and creation date substituted back in) provably carries'): 'docstring',
    ('upgrade_extensions.py', 'f"wave-id: `{wave_id}`\\n\\n"'): 'frozen_oracle',
    ('upgrade_extensions.py', 'rendered scaffold (its own wave-id/title/date substituted into the frozen'): 'docstring',
    ('upgrade_extensions.py', 'wave_m = re.search(r"^wave-id: `(.+)`$", text, re.MULTILINE)'): 'frozen_oracle',
    ('upgrade_extensions.py', "# on this repository's own migration: guru.md carried a wave-id"): 'comment',
    ('upgrade_wavefoundry.py', 'authority or migration input, and leaves every ``wave.md`` and'): 'docstring',
    ('wave_lint_lib/constants.py', '# It is not used for wave record headers — wave records carry only `wave-id`.'): 'comment',
    ('wave_lint_lib/constants.py', '# a `Wave:` line (rather than a `Change ID:` line) as their identifier. Such plans use the'): 'comment',
    ('wave_lint_lib/docs_constants_validators.py', 'docs must carry a truthful ``Wave:`` reference, and wave records must not use'): 'docstring',
    ('wave_lint_lib/docs_constants_validators.py', '# (a) admitted change docs: truthful Wave: reference.'): 'comment',
    ('wave_lint_lib/wave_validators.py', "itself holds a ``wave.md`` (a nested sub-wave is discovery's business, and"): 'docstring',
    ('wave_lint_lib/wave_validators.py', '"""Enforce that every `docs/plans/*.md` basename matches its `Change ID` (or `Wave:` for'): 'docstring',
    ('wave_lint_lib/wave_validators.py', 'too). The orphan state is a candidate whose sibling ``wave.md`` is'): 'docstring',
    ('wave_lint_lib/wave_validators.py', 'wave.md-file-driven, precisely so the cheaper tamper variants (deleting'): 'docstring',
    ('wave_lint_lib/wave_validators.py', 'or renaming ``wave.md``, or renaming the folder, while the non-empty'): 'docstring',
    ('wave_lint_lib/wave_validators.py', 'is content-driven on this same role). A wave.md that carries a'): 'docstring',
    ('wave_lint_lib/wave_validators.py', '# the discovery guards, not only folders holding a wave.md).'): 'comment',
    ('wave_lint_lib/wave_validators.py', 'paths for the incremental lint path. Note the cross-doc duplicate wave-id/item-id detectio'): 'docstring',
    ('wave_lint_lib/wave_validators.py', 'its tamper state has no ``wave.md`` path that could appear in ``only``, and'): 'docstring',
    ('wave_lint_lib/wave_validators.py', '# Wave record checks: wave-id, required sections, Title, Objective, Watchpoints, Changes'): 'comment',
    ('wave_lint_lib/wave_validators.py', '# (a) Status: planned AND (b) ## Changes section exists but is'): 'comment',
    ('wave_lint_lib/wave_validators.py', '``## Changes`` region are outside the corpus by construction — a Participants Role entry'): 'docstring',
    ('wf_server/memory_handlers.py', '# lifecycle checkpoints even without a wave-id link.'): 'comment',
    ('wf_server/memory_handlers.py', '# shared wave-id evidence ref is deliberately NOT a skip reason — every'): 'comment',
    ('wf_server/server_impl.py', '"""Compare wave.md change statuses against actual change doc files.'): 'docstring',
    ('wf_server/server_impl.py', 'for any change whose status differs between wave.md and its change doc file.'): 'docstring',
    ('wf_server/server_impl.py', '# wave where in-flight Change Status drift is meaningful.'): 'comment',
    ('wf_server/server_impl.py', 'be read: their inner ``wave-id`` may differ from the dirname, so callers'): 'docstring',
    ('wf_server/server_impl.py', 'The requested id may live inside a skipped record (wave-id and dirname can'): 'docstring',
    ('wf_server/server_impl.py', '"""Append a ``Change ID:`` block inside the ``## Changes`` section.'): 'docstring',
    ('wf_server/server_impl.py', 'the next ``## `` heading (or end-of-file). When ``## Changes`` is missing'): 'docstring',
    ('wf_server/server_impl.py', '_LEGACY_BACKREF_PLACEHOLDERS = r"\\[wave-id or TBD\\]|`?<wave-id>`?|TBD"'): 'retired_name',
    ('wf_server/server_impl.py', '# wave-id prefix like "12ecs"'): 'comment',
    ('wf_server/server_impl.py', '# Merge lanes from wave.md Participants table and project-declared required_review_lanes'): 'comment',
    ('wf_server/server_impl.py', '# retry after an interruption between the wave.md write and this point'): 'comment',
    ('wf_server/server_impl.py', 'change_id: Change ID or prefix for single lookup, e.g. "12926" or "12926-feat".'): 'docstring',
    ('wf_server/server_impl.py', 'change_id: Change ID or unique prefix.'): 'docstring',
    ('wf_server/server_impl.py', 'change_id: Change ID or unique prefix to remove.'): 'docstring',
    ('wf_server/server_impl.py', '"""Return the current active wave.md as markdown text."""'): 'docstring',
    ('wf_server/server_impl.py', 'description="Read a wave record (wave.md) by ID or prefix. Returns the raw markdown conten'): 'message',
    ('wf_server/server_impl.py', '"""Return the wave.md for the given wave ID or prefix."""'): 'docstring',
}


def census(scripts_root: Path) -> list[tuple[str, int, str]]:
    """Every (scripts-relative file, line number, stripped line) marker hit."""
    hits: list[tuple[str, int, str]] = []
    for path in sorted(scripts_root.rglob("*.py")):
        rel = path.relative_to(scripts_root)
        if any(part in CENSUS_EXCLUDED_DIRS for part in rel.parts[:-1]):
            continue
        if rel.as_posix() in CENSUS_EXCLUDED_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if MARKER_RE.search(line):
                hits.append((rel.as_posix(), lineno, line.strip()))
    return hits


def _allowed(hit: tuple[str, int, str]) -> bool:
    file, _lineno, line = hit
    return any(entry_file == file and snippet in line for (entry_file, snippet) in ALLOWLIST)


class VocabularyCensusTests(unittest.TestCase):
    def test_allowlist_reasons_are_known(self) -> None:
        for key, reason in ALLOWLIST.items():
            self.assertIn(reason, ALLOWED_REASONS, key)
            self.assertTrue(key[1].strip(), f"bare filename entry: {key}")

    def test_census_has_no_unrouted_sites(self) -> None:
        offenders = [hit for hit in census(SCRIPTS_ROOT) if not _allowed(hit)]
        self.assertEqual(
            offenders, [],
            "record vocabulary marker outside vocabulary_profile.py and not "
            "allowlisted (route it through vocabulary_profile, or add a "
            "comment/docstring/message entry):\n"
            + "\n".join(f"  {f}:{n}: {line}" for f, n, line in offenders),
        )

    def test_allowlist_has_no_stale_entries(self) -> None:
        hits = census(SCRIPTS_ROOT)
        stale = [
            key for key in ALLOWLIST
            if not any(key[0] == f and key[1] in line for f, _n, line in hits)
        ]
        self.assertEqual(stale, [], f"allowlist entries that match nothing: {stale}")

    def test_census_reports_each_planted_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scripts = Path(tmp)
            (scripts / "tests").mkdir()
            (scripts / "tests" / "test_ignored.py").write_text(
                'X = "wave.md"\n', encoding="utf-8"
            )
            (scripts / "vocabulary_profile.py").write_text(
                'RECORD_FILENAME = "wave.md"\n', encoding="utf-8"
            )
            (scripts / "tiny.py").write_text(
                "import re\n"
                "def is_record(name):\n"
                '    return name == "wave.md"\n'  # 3: equality
                "def id_line(wave_id):\n"
                '    return f"wave-id: `{wave_id}`"\n'  # 5: f-string part
                'STATUS_RE = re.compile(r"^Change Status:\\s*`([^`]+)`")\n'  # 6: regex source
                "def summary(body):\n"
                '    return "## Wave Summary" + "\\n\\n" + body\n'  # 8: concatenation
                'SAFE = "upgrade-wave.md"\n'  # 9: boundary, not a marker
                'OTHER = "Next Wave: soon"\n'  # 10: prose token, still a marker
                'ESCAPED_RE = re.compile(r"^Change\\ ID:\\s|/wave\\.md$")\n',  # 11: escaped regex source
                encoding="utf-8",
            )
            hits = census(scripts)
        self.assertEqual(
            [(f, n) for f, n, _line in hits],
            [("tiny.py", 3), ("tiny.py", 5), ("tiny.py", 6), ("tiny.py", 8), ("tiny.py", 10),
             ("tiny.py", 11)],
        )
        self.assertFalse(any(_allowed(hit) for hit in hits))

    def test_no_pending_writer_class(self) -> None:
        # Change 1z8qi (AC-3): every writer is routed, so no deferral class remains.
        self.assertFalse(any(reason.startswith("pending") for reason in ALLOWED_REASONS))
        self.assertFalse(any(reason.startswith("pending") for reason in ALLOWLIST.values()))


if __name__ == "__main__":
    unittest.main()
