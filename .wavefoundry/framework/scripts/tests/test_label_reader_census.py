"""Label reader census (wave 1z8ou, change 1z8os, Requirement 3; AC-4).

Modelled on ``tests/test_vocabulary_census.py``. The profile no longer refuses
labels that are prefixes of one another (``Wave``, ``Wave ID``, ``Wave Status``),
so every reader must match a label in its colon form at the start of a line.
The rule is stated once in ``docs/architecture/layering-rules.md``.

Predicate. Every non-test ``.py`` under ``.wavefoundry/framework/scripts/``
except ``vocabulary_profile.py`` is scanned line by line for each reference to
a profile label constant (``ID_KEY``, ``MEMBER_ID_LABEL``,
``MEMBER_STATUS_LABEL``, ``PREVIOUS_STATUS_LABEL``, ``BACKREF_LABEL``, with or
without the ``_RE`` suffix, as a whole word). Each reference must lie inside
one of these line-anchored, colon-terminated reader shapes:

- a regex source where the escaped label follows a ``^`` anchor (not an escaped
  ``\\^`` or a character-class ``[^``; optionally inside an
  opening ``(?:`` alternation) and is followed by ``:`` (directly, or after
  closing that alternation): ``^{x.LABEL_RE}:``, ``(?m)^{x.LABEL_RE}:``,
  ``^(?:{x.LABEL_RE}|Status):``;
- ``re.fullmatch(rf"{x.LABEL_RE}:`` (anchored by ``fullmatch`` on one line);
- ``.startswith(f"{x.LABEL}:")`` on a line that iterates ``splitlines()``;

or inside the span of an ``ALLOWLIST`` snippet on that line. Allowlist
reasons: ``message`` (human-facing text, not a reader), ``writer`` (builds a
record line), ``exact_key`` (compared as a whole key, not a prefix),
``newline_anchored`` (a continuation inside a multi-line block pattern that a
literal ``\\n`` precedes) and ``variable`` (the label is passed on through a
variable or parameter; each entry's comment names where it is read and how).

Known limit: a reader that receives a label only through a variable or
parameter (``status_label``, ``_wf_id_prefix``, ``member_id_label_re``) is
seen only where the constant is named; the ``variable`` entries record those
hand-offs, and the second-profile driver exercises them.
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]

_LABELS = r"(?:ID_KEY|MEMBER_ID_LABEL|MEMBER_STATUS_LABEL|PREVIOUS_STATUS_LABEL|BACKREF_LABEL)"
LABEL_REF_RE = re.compile(rf"\b{_LABELS}(?:_RE)?\b")
# ``{<expr>.LABEL_RE}`` as an f-string field (``<expr>`` has no braces).
_FIELD_RE = rf"\{{[^{{}}]*\b{_LABELS}_RE\}}"
READER_SHAPES = (
    # The ``^`` must be a real anchor: not an escaped literal ``\^`` and not the
    # negation of a character class ``[^``.
    re.compile(rf"(?<![\\\[])\^(?:\(\?:)?{_FIELD_RE}(?:\|[^()]*\))?:"),
    re.compile(rf"re\.fullmatch\(rf?\"{_FIELD_RE}:"),
    re.compile(rf"\.startswith\(f\"\{{[^{{}}]*\b{_LABELS}\}}:\"\)"),
)

CENSUS_EXCLUDED_FILES = frozenset({"vocabulary_profile.py"})
CENSUS_EXCLUDED_DIRS = frozenset({"tests", "__pycache__", ".pytest_cache"})

ALLOWED_REASONS = frozenset({"message", "writer", "exact_key", "newline_anchored", "variable"})

# {(file, snippet of the source line): reason}. A snippet exempts only the
# label references inside its own span on that line.
ALLOWLIST: dict[tuple[str, str], str] = {
    # Carrier-key membership: a line's key is compared whole (`key in KEYS`).
    ("gardener_metadata.py", "_vocab.MEMBER_ID_LABEL, _vocab.MEMBER_STATUS_LABEL,"): "exact_key",
    ("gardener_metadata.py", "_vocab.BACKREF_LABEL, \"Last verified\", \"Title\", _vocab.ID_KEY,"): "exact_key",
    ("gardener_metadata.py", "_vocab.PREVIOUS_STATUS_LABEL, \"Role\""): "exact_key",
    # Passed to _admitted_change_re_for, which compiles rf"(?m)^{member_id_label_re}:".
    ("memory_supply.py", "(profile or _vocab).MEMBER_ID_LABEL_RE)"): "variable",
    # The Stop hook reads it as s.startswith(_wf_id_prefix + ":") on stripped lines.
    ("render_platform_surfaces.py", "getattr(_wf_vocab, \"ID_KEY\", None)"): "variable",
    ("wave_lint_lib/docs_constants_validators.py", "still says '{_vocab.BACKREF_LABEL}: TBD'"): "message",
    ("wave_lint_lib/docs_constants_validators.py", "'{_vocab.BACKREF_LABEL}: {value}' does not match"): "message",
    # status_label / label / dependency_label below feed only failure messages.
    ("wave_lint_lib/wave_validators.py", "status_label = _vocab.MEMBER_STATUS_LABEL if record.anchor_type"): "message",
    ("wave_lint_lib/wave_validators.py", "status_label = _vocab.MEMBER_STATUS_LABEL if change_records"): "message",
    ("wave_lint_lib/wave_validators.py", "label = _vocab.MEMBER_ID_LABEL if record.anchor_type"): "message",
    ("wave_lint_lib/wave_validators.py", "dependency_label = _vocab.MEMBER_ID_LABEL if record.anchor_type"): "message",
    ("wave_lint_lib/wave_validators.py", "plan filename must match `{_vocab.MEMBER_ID_LABEL}`"): "message",
    ("wave_lint_lib/wave_validators.py", "**{_vocab.MEMBER_ID_LABEL} / Filename**; generate"): "message",
    ("wave_lint_lib/wave_validators.py", "plan declares multiple `{_vocab.MEMBER_ID_LABEL}` values"): "message",
    ("wave_lint_lib/wave_validators.py", "must match `{_vocab.BACKREF_LABEL}:` identifier"): "message",
    ("wave_lint_lib/wave_validators.py", "missing a `{_vocab.MEMBER_ID_LABEL}:` or `{_vocab.BACKREF_LABEL}:` identifier"): "message",
    ("wave_lint_lib/wave_validators.py", "record it as `{_vocab.MEMBER_ID_LABEL}: "): "message",
    ("wave_lint_lib/wave_validators.py", "→ **{_vocab.MEMBER_ID_LABEL} / Filename**"): "message",
    ("wave_lint_lib/wave_validators.py", "missing stable `{_vocab.ID_KEY}` declaration"): "message",
    ("wave_lint_lib/wave_validators.py", "{_vocab.MEMBER_ID_LABEL} `{change_id}` uses undeclared change kind"): "message",
    ("wave_lint_lib/wave_validators.py", "multiple `{_vocab.ID_KEY}` declarations found"): "message",
    ("wave_lint_lib/wave_validators.py", "duplicate `{_vocab.ID_KEY}` `{wave_id}`"): "message",
    ("wave_lint_lib/wave_validators.py", "must use `{_vocab.MEMBER_ID_LABEL}` / `{_vocab.MEMBER_STATUS_LABEL}`"): "message",
    ("wave_lint_lib/wave_validators.py", "missing stable `{_vocab.MEMBER_ID_LABEL}` declaration"): "message",
    ("wave_lint_lib/wave_validators.py", "unstable {_vocab.MEMBER_ID_LABEL} `{change_value}`"): "message",
    ("wave_lint_lib/wave_validators.py", "invalid `{_vocab.MEMBER_STATUS_LABEL}` declaration"): "message",
    ("wave_lint_lib/wave_validators.py", "invalid `{_vocab.PREVIOUS_STATUS_LABEL}` declaration"): "message",
    ("wave_lint_lib/wave_validators.py", "stable {_vocab.MEMBER_ID_LABEL}s in backticks"): "message",
    ("wave_lint_lib/wave_validators.py", "references unknown `\" + _vocab.ID_KEY + \"`"): "message",
    ("wave_lint_lib/wave_validators.py", "references unknown \" + _vocab.MEMBER_ID_LABEL + \" `"): "message",
    # _change_block_pattern: the status lines follow a literal "\n" (the id line is anchored with ^).
    ("wf_server/server_impl.py",
     "\\n(?:{_vocab.PREVIOUS_STATUS_LABEL_RE}:\\s+`[^`]+`\\n)?{_vocab.MEMBER_STATUS_LABEL_RE}:"): "newline_anchored",
    ("wf_server/server_impl.py", "f\"{_vocab.MEMBER_ID_LABEL}: `{change_id}`\\n{_vocab.MEMBER_STATUS_LABEL}: `planned`\\n\""): "writer",
    ("wf_server/server_impl.py", "lambda _m: f\"{_vocab.BACKREF_LABEL}: {wave_md.parent.name}\""): "writer",
    ("wf_server/server_impl.py", "lambda _m: f\"{_vocab.MEMBER_ID_LABEL}: `{change_id}`\""): "writer",
    # wf_close_change (wave 1zlu1): writes the wave-record previous-status line.
    ("wf_server/server_impl.py", "previous_line = indent + _vocab.PREVIOUS_STATUS_LABEL + f\": `{previous}`\" + ending"): "writer",
}


def _spans(line: str) -> list[tuple[int, int]]:
    spans = [m.span() for shape in READER_SHAPES for m in shape.finditer(line)]
    # startswith(label + ":") counts as anchored only on a splitlines() scan.
    if "splitlines()" not in line:
        spans = [s for s in spans if not line[s[0]:s[1]].startswith(".startswith(")]
    return spans


def census(scripts_root: Path, allowlist: dict[tuple[str, str], str] | None = None) -> list[tuple[str, int, str]]:
    """Every (scripts-relative file, line number, stripped line) holding a
    label reference that is neither in a reader shape nor inside an allowlisted
    snippet."""
    allowlist = ALLOWLIST if allowlist is None else allowlist
    offenders: list[tuple[str, int, str]] = []
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
            refs = [m.span() for m in LABEL_REF_RE.finditer(line)]
            if not refs:
                continue
            covered = _spans(line)
            for (file, snippet) in allowlist:
                if file != rel.as_posix():
                    continue
                start = line.find(snippet)
                while start != -1:
                    covered.append((start, start + len(snippet)))
                    start = line.find(snippet, start + 1)
            if any(not any(a <= s and e <= b for a, b in covered) for s, e in refs):
                offenders.append((rel.as_posix(), lineno, line.strip()))
    return offenders


def _snippet_hits(scripts_root: Path) -> set[tuple[str, str]]:
    hits: set[tuple[str, str]] = set()
    for (file, snippet) in ALLOWLIST:
        path = scripts_root / file
        if path.is_file() and snippet in path.read_text(encoding="utf-8"):
            hits.add((file, snippet))
    return hits


class LabelReaderCensusTests(unittest.TestCase):
    def test_allowlist_reasons_are_known(self) -> None:
        for key, reason in ALLOWLIST.items():
            self.assertIn(reason, ALLOWED_REASONS, key)
            self.assertTrue(LABEL_REF_RE.search(key[1]), f"snippet names no label: {key}")

    def test_every_label_reader_is_anchored_and_colon_terminated(self) -> None:
        offenders = census(SCRIPTS_ROOT)
        self.assertEqual(
            offenders, [],
            "label reference outside a line-anchored, colon-terminated reader shape "
            "(anchor it with (?m)^ and match the colon form, or add an allowlist "
            "entry with a reason):\n"
            + "\n".join(f"  {f}:{n}: {line}" for f, n, line in offenders),
        )

    def test_allowlist_has_no_stale_entries(self) -> None:
        stale = sorted(set(ALLOWLIST) - _snippet_hits(SCRIPTS_ROOT))
        self.assertEqual(stale, [], f"allowlist entries that match nothing: {stale}")

    def test_census_fails_on_planted_readers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scripts = Path(tmp)
            (scripts / "tests").mkdir()
            (scripts / "tests" / "test_ignored.py").write_text(
                'X = f"{_vocab.ID_KEY}:" in text\n', encoding="utf-8"
            )
            (scripts / "vocabulary_profile.py").write_text(
                'ID_KEY_RE = re.escape(ID_KEY)\n', encoding="utf-8"
            )
            (scripts / "tiny.py").write_text(
                "import re\n"
                'A = re.compile(rf"^{_vocab.MEMBER_ID_LABEL_RE}:\\s+`([^`]+)`", re.M)\n'  # 2: anchored, ok
                'B = re.compile(rf"(?m)^(?:{_vocab.MEMBER_STATUS_LABEL_RE}|Status):")\n'  # 3: ok
                "def f(text):\n"
                '    return f"{_vocab.ID_KEY}:" in text\n'  # 5: colon, unanchored
                "def g(text):\n"
                '    return re.search(rf"{_vocab.BACKREF_LABEL_RE}:", text)\n'  # 7: colon, unanchored
                "def h(text):\n"
                "    return _vocab.BACKREF_LABEL in text\n"  # 9: bare label
                "def i(line):\n"
                "    return line.startswith(_vocab.MEMBER_ID_LABEL)\n"  # 11: bare prefix
                "def j(text):\n"
                '    return re.search(rf"(?m)^{_vocab.BACKREF_LABEL_RE}", text)\n'  # 13: anchored, no colon
                "def k(text):\n"
                '    return [l for l in text.splitlines() if l.startswith(f"{_vocab.PREVIOUS_STATUS_LABEL}:")]\n'  # 15: ok
                "def m(text):\n"
                '    return text.startswith(f"{_vocab.PREVIOUS_STATUS_LABEL}:")\n'  # 17: not a line scan
                "def n(text):\n"
                '    return re.search(rf"(?m)\\^{_vocab.BACKREF_LABEL_RE}:", text)\n'  # 19: escaped literal caret
                "def o(text):\n"
                '    return re.search(rf"[^{_vocab.BACKREF_LABEL_RE}:]", text)\n',  # 21: character-class caret reaching the colon
                encoding="utf-8",
            )
            offenders = census(scripts, allowlist={})
        self.assertEqual([(f, n) for f, n, _line in offenders],
                         [("tiny.py", 5), ("tiny.py", 7), ("tiny.py", 9), ("tiny.py", 11),
                          ("tiny.py", 13), ("tiny.py", 17), ("tiny.py", 19), ("tiny.py", 21)])

    def test_allowlist_snippet_exempts_only_its_own_span(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scripts = Path(tmp)
            (scripts / "tiny.py").write_text(
                'X = re.sub(rf"{_vocab.MEMBER_ID_LABEL_RE}:.*", lambda _m: f"{_vocab.MEMBER_ID_LABEL}: `x`", t)\n',
                encoding="utf-8",
            )
            writer = {("tiny.py", 'lambda _m: f"{_vocab.MEMBER_ID_LABEL}: `x`"'): "writer"}
            self.assertEqual([n for _f, n, _l in census(scripts, allowlist=writer)], [1])


if __name__ == "__main__":
    unittest.main()
