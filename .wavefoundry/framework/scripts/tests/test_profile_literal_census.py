"""Literal-path census over the framework tests (change 1zim6, Requirement 4).

A test that exercises framework behaviour takes record paths and filenames
from ``record_paths``, ``vocabulary_profile`` or the builders in
``record_layout_support`` (``waves_dir``, ``waves_rel``,
``localize_record_text``, ``RecordTreeBuilder``), never a literal default
layout path. This census scans every ``tests/test_*.py`` for two literals:

- ``docs/waves``: inside one string constant, or spelled as adjacent
  ``"docs"`` and ``"waves"`` constants in a ``/`` path chain or in a call's
  positional arguments (``root / "docs" / "waves"``,
  ``Path("docs", "waves")``);
- ``wave.md`` as a whole file name inside a string constant (not a suffix
  of a longer name such as ``close-wave.md``).

Detection reads the module's AST, so comments are never seen (they are not
nodes) and docstrings (the first statement of a module, class or function
when it is a string) are dropped. An occurrence is reported once per source
line: the file name, the line number and the line's text.

An occurrence is allowed when it sits inside a test carrying
``@default_profile_only`` (method or class), or when an ``ALLOWLIST`` entry
matches it. An entry is keyed by file and snippet with a typed reason
(``REASONS``); it matches an occurrence in that file whose source line
contains the snippet, or whose enclosing module-level assignment starts with
it (so a census table bound at module level is listed once, by its binding
line). An entry that matches nothing is stale and fails the census. This file
is not scanned: its allowlist names the literals it allows.
"""
from __future__ import annotations

import ast
import functools
import re
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SELF_NAME = Path(__file__).name

TOKEN_RE = re.compile(r"docs/waves|(?<![A-Za-z0-9_.-])wave\.md(?![A-Za-z0-9_])")
MARKER_NAME = "default_profile_only"

REASONS = {
    "configured-layout-value": "a layout value the test configures explicitly (patch_layout, apply_layout, "
                               "patch.multiple, a profile asset, an explicit prefix argument), or a control "
                               "path deliberately outside that configured layout",
    "opaque-fixture-path": "a path or prose string the code under test never resolves against the record "
                           "layout (an index or ledger row key, a parser input, a query string)",
    "production-source-census": "a census of production source text, or a test reading production source",
    "planted-control": "text planted into a scratch file or source to prove a census or scanner fails",
    "repository-input-prose": "this repository's own records read as input, whose location does not follow "
                              "a profile",
    "historical-old-runner-layout": "a record written in the layout an older runner used",
    "shipped-template-text": "shipped prompt, template, golden or reference-doc text pinned verbatim",
}

# {(file, snippet): reason}. A snippet is a distinguishing part of the
# occurrence's source line, or the start of its module-level binding line.
ALLOWLIST: dict[tuple[str, str], str] = {
    # -- configured layout values and controls outside them --
    ("test_chunk_tags.py", "project/records/waves/1abcd relocated/wave.md"): "configured-layout-value",
    ("test_chunk_tags.py", "archive/old-waves/1aaaa archived/wave.md"): "configured-layout-value",
    ("test_chunk_tags.py", "docs/waves/1abce not-a-wave/wave.md"): "configured-layout-value",
    ("test_chunk_tags.py", 'waves_prefix="docs/waves/"'): "configured-layout-value",
    ("test_chunk_tags.py", '"src/docs/waves/1a x/wave.md"'): "configured-layout-value",
    ("test_chunk_tags.py", "docs/archive/waves/1aaaa archived/wave.md"): "configured-layout-value",
    ("test_chunk_tags.py", 'excluded_dirs=("docs/waves",)'): "configured-layout-value",
    ("test_dashboard_server.py", 'WAVES_ROOT="docs/waves"'): "configured-layout-value",
    ("test_dashboard_server.py", '_write(self.root / "docs/waves" / rel / _RECORD'): "configured-layout-value",
    ("test_docs_gardener.py", '"wave_root": "docs/waves"'): "configured-layout-value",
    ("test_docs_gardener.py", 'data["wave_root"], "docs/waves"'): "configured-layout-value",
    ("test_docs_gardener.py", 'f"{self.WAVES}/1abcd wave/wave.md"'): "configured-layout-value",
    ("test_docs_lint.py", 'wave_root="docs/waves/"'): "configured-layout-value",
    ("test_docs_lint.py", '{"wave_root": "docs/waves/"}'): "configured-layout-value",
    ("test_docs_lint.py", 'data["wave_implement"]["wave_root"] = "docs/waves/"'): "configured-layout-value",
    ("test_memory_records.py", '("docs/waves", "docs/plans")'): "configured-layout-value",
    ("test_profile_support.py", "BUILDER_DRIVER = r'''"): "configured-layout-value",
    ("test_profile_support.py", 'self.assertNotIn("wave.md", run["record_files"])'): "configured-layout-value",
    ("test_profile_support.py", 'self.assertIn("wave.md", run["record_files"])'): "configured-layout-value",
    ("test_profile_support.py", 'self.assertIn("wave.md", run["archive_files"])'): "configured-layout-value",
    ("test_profile_support.py", '["docs/waves/00060 archived-wave"]'): "configured-layout-value",
    ("test_profile_support.py", '["docs/waves/00070 built-wave", "docs/waves/change-2026-03"]'): "configured-layout-value",
    ("test_profile_support.py", '(shipped / "docs" / "waves" / "README.md")'): "configured-layout-value",
    ("test_profile_support.py", '(record_layout_support.DOCS_LINT_FIXTURE / "docs" / "waves"'): "configured-layout-value",
    ("test_profile_support.py", '["RECORD_FILENAME"], "wave.md")'): "configured-layout-value",
    ("test_record_paths.py", '"records/waves/1abcd x/wave.md".startswith'): "configured-layout-value",
    ("test_record_paths.py", 'waves_root="docs/waves"'): "configured-layout-value",
    ("test_record_paths.py", "(docs/waves is a dangling symlink)"): "configured-layout-value",
    ("test_record_paths.py", 'self.root / "docs" / "waves"'): "configured-layout-value",
    # -- paths and prose the code under test never resolves against the layout --
    ("test_chunker.py", 'chunk_file(source, "docs/waves/wave.md")'): "opaque-fixture-path",
    ("test_graph_indexer.py", 'self.root / "docs" / "wave.md"'): "opaque-fixture-path",
    ("test_graph_indexer.py", '"docs/wave.md"'): "opaque-fixture-path",
    ("test_graph_quality_eval.py", '"docs/waves/w/evidence/freeze.json": 1'): "opaque-fixture-path",
    ("test_index_state_store.py", '"docs/waves/old/wave.md"'): "opaque-fixture-path",
    ("test_review_evidence.py", "must stay inside docs/waves"): "opaque-fixture-path",
    ("test_review_evidence.py", "a wave path escapes docs/waves"): "opaque-fixture-path",
    ("test_review_policy.py", "- docs/waves/1uo1x declaration-and-digest-boundaries/wave.md"): "opaque-fixture-path",
    ("test_review_policy.py", "docs/waves/1abc some slug/wave.md"): "opaque-fixture-path",
    ("test_server_context_efficiency.py", '{"path": "wave.md", "rationale": "why"}'): "opaque-fixture-path",
    ("test_server_context_efficiency.py", '["change.md", "wave.md"]'): "opaque-fixture-path",
    ("test_server_tools_retrieval.py", '"path": "docs/waves/my-wave/wave.md"'): "opaque-fixture-path",
    ("test_server_tools_retrieval.py", '"docs/waves/sql-notes.md": ('): "opaque-fixture-path",
    ("test_server_tools_retrieval.py", '"path": "docs/waves/12dv9/'): "opaque-fixture-path",
    ("test_server_tools_retrieval.py", '"path": "docs/waves/old wave/change.md"'): "opaque-fixture-path",
    ("test_server_tools_retrieval.py", 'cue("what is under docs/waves/ now?")'): "opaque-fixture-path",
    ("test_server_tools_retrieval.py", '"docs/waves/1aaaa w/wave.md": {"historical": True'): "opaque-fixture-path",
    ("test_server_tools_retrieval.py", '"path": "docs/waves/w1/wave.md"'): "opaque-fixture-path",
    ("test_server_tools_retrieval.py", 'EVIDENCE_FILE = "docs/waves/w/evidence/'): "opaque-fixture-path",
    # -- censuses of production source --
    ("test_record_layout_census.py", "SITES: list[tuple[str, str, str]] = ["): "production-source-census",
    ("test_record_layout_census.py", "ALLOWLIST: dict[tuple[str, str], str] = {"): "production-source-census",
    ("test_vocabulary_census.py", "ALLOWLIST: dict[tuple[str, str], str] = {"): "production-source-census",
    ("test_server_tools_lifecycle.py", 'if "wave.md" in recv_src:'): "production-source-census",
    ("test_server_tools_lifecycle.py", 'if "wave.md" in ast.unparse(value):'): "production-source-census",
    ("test_server_tools_lifecycle.py", "every wave.md read must route through _read_wave_record_text"):
        "production-source-census",
    # -- planted census controls --
    ("test_record_layout_census.py", "'DEFAULT = \"docs/waves\"\\n'"): "planted-control",
    ("test_vocabulary_census.py", "'X = \"wave.md\"\\n'"): "planted-control",
    ("test_vocabulary_census.py", "'RECORD_FILENAME = \"wave.md\"\\n'"): "planted-control",
    ("test_vocabulary_census.py", "'    return name == \"wave.md\"\\n'"): "planted-control",
    ("test_events_only_residue_census.py", "reads docs/waves/review-evidence-"): "planted-control",
    # -- this repository's own records read as input --
    ("test_chunker.py", '"1p31b public-launch-prep"'): "repository-input-prose",
    ("test_graph_quality_eval.py", 'CONTROL_DIR = (REPO_ROOT / "docs" / "waves"'): "repository-input-prose",
    ("test_lifecycle_gates_structure.py", '(repo / "docs/waves/1y0h0 typed-phase-gates"'): "repository-input-prose",
    ("test_render_agent_surfaces.py", '(repo_root / "docs" / "waves").glob("1skt1*/1siu0*.md")'): "repository-input-prose",
    ("test_review_policy.py", '"docs/waves/1uo1x declaration-and-digest-boundaries/wave.md"'): "repository-input-prose",
    ("test_review_policy.py", '(root / "docs/waves").glob("*/*.md")'): "repository-input-prose",
    ("test_review_policy.py", 'if p.name != "wave.md"'): "repository-input-prose",
    ("test_secrets_prefix_collapse.py", '"1tmtx test-suite-performance" / "evidence"'): "repository-input-prose",
    ("test_server_tools_lifecycle.py", '"docs/waves/1ypy6 implement-prompt-efficiency/'): "repository-input-prose",
    ("test_server_tools_retrieval.py", 'CONTROL = ("docs/waves/1wpih index-quality-evaluation-and-ranking/"'):
        "repository-input-prose",
    ("test_shipped_reference_docs.py", 'rel.startswith("docs/waves/")'): "repository-input-prose",
    ("test_wf_cli.py", '"docs/architecture", "docs/plans", "docs/waves", "docs/reports"'): "repository-input-prose",
    # -- the layout an older runner wrote --
    ("test_upgrade_wavefoundry.py", 'wave = self.root / "docs" / "waves" / "1old closed"'): "historical-old-runner-layout",
    ("test_upgrade_wavefoundry.py", 'wave.joinpath("wave.md").write_text("# Wave\\n\\nStatus: closed\\n"'):
        "historical-old-runner-layout",
    ("test_upgrade_wavefoundry.py", '(self.root / "docs" / "waves" / "1old closed'): "historical-old-runner-layout",
    # -- shipped text pinned verbatim --
    ("test_install_log_lib.py", "docs/waves/00000 wave-zero-plans-and-specs/wave.md"): "shipped-template-text",
    ("test_install_log_lib.py", "artifact: docs/waves/00000/wave.md"): "shipped-template-text",
    ("test_render_agent_surfaces.py", '"historical `wave.md` or `events.jsonl`"'): "shipped-template-text",
    ("test_render_agent_surfaces.py", "- Load the target change doc (`docs/waves/<wave-id>/<change-id>.md`"):
        "shipped-template-text",
    ("test_render_agent_surfaces.py", '"waves/1vj4e x/wave.md",'): "shipped-template-text",
    ("test_shipped_reference_docs.py", 'self.assertIn("docs/waves/", normalized)'): "shipped-template-text",
    ("test_upgrade_wavefoundry.py", "- Load the target change doc (`docs/waves/<wave-id>/<change-id>.md`"):
        "shipped-template-text",
    ("test_vocabulary_writers.py", '"- `docs/waves/1abc some slug/set.md`"'): "shipped-template-text",
}


@dataclass(frozen=True)
class Occurrence:
    file: str
    line: int
    text: str
    binding: str  # first line of the enclosing module-level assignment, else ""

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.text}"


@dataclass(frozen=True)
class FileScan:
    occurrences: tuple[Occurrence, ...]
    marked: int  # module-level test classes and their methods carrying the marker


def _docstring_nodes(tree: ast.AST) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                found.add(id(first.value))
    return found


def _is_marked(node: ast.AST) -> bool:
    for decorator in getattr(node, "decorator_list", ()):
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", None)
        if name == MARKER_NAME:
            return True
    return False


def _div_chain(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _div_chain(node.left) + _div_chain(node.right)
    return [node]


def _text(node: ast.AST) -> "str | None":
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def scan_source(name: str, source: str) -> FileScan:
    """The census occurrences of one test module's source outside marked
    tests, and how many tests it marks."""
    tree = ast.parse(source)
    lines = source.splitlines()
    docstrings = _docstring_nodes(tree)
    marked = [node for node in ast.walk(tree)
              if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and _is_marked(node)]
    spans = [(node.lineno, node.end_lineno) for node in marked]
    # Counted tests: a marked module-level class, or a marked method of one
    # (a marked class built inside a test body is that test's fixture).
    counted = 0
    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef):
            counted += _is_marked(stmt)
            counted += sum(1 for item in stmt.body
                           if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_marked(item))

    def in_marked(line: int) -> bool:
        return any(start <= line <= end for start, end in spans)

    bindings: list[tuple[int, int, str]] = []
    for stmt in tree.body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            bindings.append((stmt.lineno, stmt.end_lineno, lines[stmt.lineno - 1].strip()))

    hits: set[int] = set()
    for node in ast.walk(tree):
        value = _text(node)
        if value is not None and id(node) not in docstrings and TOKEN_RE.search(value):
            if not in_marked(node.lineno):
                own = [n for n in range(node.lineno, node.end_lineno + 1) if TOKEN_RE.search(lines[n - 1])]
                hits.update(own or [node.lineno])
        sequences = []
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            sequences.append(_div_chain(node))
        if isinstance(node, ast.Call):
            sequences.append(node.args)
        for sequence in sequences:
            for left, right in zip(sequence, sequence[1:]):
                if _text(left) == "docs" and _text(right) == "waves" and not in_marked(right.lineno):
                    hits.add(right.lineno)

    def binding_of(line: int) -> str:
        return next((text for start, end, text in bindings if start <= line <= end), "")

    occurrences = tuple(Occurrence(name, line, lines[line - 1].strip(), binding_of(line)) for line in sorted(hits))
    return FileScan(occurrences, counted)


def scan_tests(tests_dir: Path = TESTS_DIR) -> FileScan:
    occurrences: list[Occurrence] = []
    marked = 0
    for path in sorted(tests_dir.glob("test_*.py")):
        if path.name == SELF_NAME:
            continue
        result = scan_source(path.name, path.read_text(encoding="utf-8"))
        occurrences.extend(result.occurrences)
        marked += result.marked
    return FileScan(tuple(occurrences), marked)


@functools.lru_cache(maxsize=1)
def tree_scan() -> FileScan:
    """The census of this tests directory, computed once per process."""
    return scan_tests()


def _matches(entry: tuple[str, str], occurrence: Occurrence) -> bool:
    file, snippet = entry
    return file == occurrence.file and (
        snippet in occurrence.text or (bool(occurrence.binding) and occurrence.binding.startswith(snippet)))


def unallowed(occurrences, allowlist: "dict[tuple[str, str], str]") -> list[Occurrence]:
    return [occ for occ in occurrences if not any(_matches(entry, occ) for entry in allowlist)]


def stale_entries(occurrences, allowlist: "dict[tuple[str, str], str]") -> list[tuple[str, str]]:
    return [entry for entry in allowlist if not any(_matches(entry, occ) for occ in occurrences)]


class ProfileLiteralCensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scan = tree_scan()

    def test_every_literal_is_marked_or_allowlisted(self) -> None:
        missed = unallowed(self.scan.occurrences, ALLOWLIST)
        self.assertEqual(
            [str(occ) for occ in missed], [],
            "default-layout literals outside a @default_profile_only test and the allowlist: take the path "
            "from record_paths / vocabulary_profile / record_layout_support, mark the test, or allowlist it "
            f"with a typed reason ({self.scan.marked} marked tests)")

    def test_no_allowlist_entry_is_stale(self) -> None:
        self.assertEqual(stale_entries(self.scan.occurrences, ALLOWLIST), [],
                         "allowlist entries that match no occurrence")

    def test_allowlist_entries_are_typed_and_distinguishing(self) -> None:
        for (file, snippet), reason in ALLOWLIST.items():
            with self.subTest(file=file, snippet=snippet):
                self.assertIn(reason, REASONS)
                self.assertTrue(file.startswith("test_") and file.endswith(".py"))
                self.assertTrue((TESTS_DIR / file).is_file(), "the allowlisted file exists")
                self.assertGreaterEqual(len(snippet.strip()), 8, "a snippet must distinguish its lines")

    def test_reports_the_marked_test_count(self) -> None:
        self.assertGreater(self.scan.marked, 0, "the marker is in use; a zero count means detection broke")
        sys.stderr.write(
            f"profile literal census: {self.scan.marked} tests marked default-profile-only; "
            f"{len(self.scan.occurrences)} literal occurrences, all allowlisted across {len(ALLOWLIST)} entries\n")


class ProfileLiteralCensusPolarityTests(unittest.TestCase):
    """The census can fail: planted literals are reported, and so is a stale
    allowlist entry."""

    PLANTED = (
        '"""Module docstring naming docs/waves/x/wave.md is not counted."""\n'  # 1
        "import unittest\n"  # 2
        "from record_layout_support import default_profile_only\n"  # 3
        "RECORD = 'docs/waves/1a x/wave.md'  # comment docs/waves\n"  # 4
        "def build(root):\n"  # 5
        '    """docs/waves in a docstring is not counted."""\n'  # 6
        '    return root / "docs" / "waves" / "x"\n'  # 7
        "def name():\n"  # 8
        "    return 'wave.md'\n"  # 9
        "def other():\n"  # 10
        "    return ('close-wave.md', 'my_wave.md', 'wave.mdx')\n"  # 11
        "class T(unittest.TestCase):\n"  # 12
        "    @default_profile_only('the shipped layout')\n"  # 13
        "    def test_marked(self):\n"  # 14
        "        self.assertEqual('docs/waves', 'docs/waves')\n"  # 15
        "@default_profile_only('the shipped layout')\n"  # 16
        "class Marked(unittest.TestCase):\n"  # 17
        "    def test_inside(self):\n"  # 18
        "        return Path('docs', 'waves')\n"  # 19
        "def joined():\n"  # 20
        "    return Path('docs', 'waves')\n"  # 21
        "# comment docs/waves/wave.md\n"  # 22
    )

    def test_planted_source_reports_exactly_the_unmarked_literals(self) -> None:
        result = scan_source("test_planted.py", self.PLANTED)
        self.assertEqual([occ.line for occ in result.occurrences], [4, 7, 9, 21])
        self.assertEqual(result.marked, 2)
        self.assertEqual(len(unallowed(result.occurrences, {})), 4)
        allow = {("test_planted.py", "RECORD = 'docs/waves"): "planted-control",
                 ("test_planted.py", 'root / "docs" / "waves"'): "planted-control",
                 ("test_planted.py", "return 'wave.md'"): "planted-control",
                 ("test_planted.py", "Path('docs', 'waves')"): "planted-control"}
        self.assertEqual(unallowed(result.occurrences, allow), [])
        self.assertEqual(stale_entries(result.occurrences, allow), [])

    def test_a_binding_entry_covers_a_module_level_table(self) -> None:
        source = "TABLE = [\n    'docs/waves/a',\n    'b/wave.md',\n]\nOTHER = 'docs/waves'\n"
        result = scan_source("test_table.py", source)
        self.assertEqual([occ.line for occ in result.occurrences], [2, 3, 5])
        missed = unallowed(result.occurrences, {("test_table.py", "TABLE = ["): "production-source-census"})
        self.assertEqual([occ.line for occ in missed], [5])

    def test_a_literal_planted_in_a_real_test_file_fails_the_census(self) -> None:
        real = TESTS_DIR / "test_chunk_tags.py"
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / real.name
            copy.write_text(real.read_text(encoding="utf-8")
                            + '\n\nPLANTED_RECORD = "docs/waves/1zzzz planted/wave.md"\n', encoding="utf-8")
            result = scan_tests(Path(tmp))
        missed = unallowed(result.occurrences, ALLOWLIST)
        self.assertEqual([occ.text for occ in missed], ['PLANTED_RECORD = "docs/waves/1zzzz planted/wave.md"'])

    def test_a_stale_allowlist_entry_fails_the_census(self) -> None:
        planted = dict(ALLOWLIST)
        planted[("test_chunk_tags.py", "no line carries this snippet")] = "planted-control"
        stale = stale_entries(tree_scan().occurrences, planted)
        self.assertEqual(stale, [("test_chunk_tags.py", "no line carries this snippet")])


if __name__ == "__main__":
    unittest.main()
