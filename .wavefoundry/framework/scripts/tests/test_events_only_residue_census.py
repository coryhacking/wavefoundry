"""Wave 1tomw (AC-7/AC-10): executable events-only deletion census.

Fails when live shipped code, current seeds/rendered carriers, install/
upgrade/package assets, or current architecture/spec/contributing docs retain
the removed adoption sidecar names, adoption-only API symbols, adoption-only
diagnostics, or publication-lock literals outside their two bounded roles:

- the current nested lock literal in ``project_state_publication_lock``
  (``review_evidence.py``), the upgrade cutover code/contract, and the docs
  that describe the publication-lock carrier; and
- the v1.13 root-lock literal in the bounded upgrade compatibility probe and
  the upgrade cutover contract.

Archived closed-wave records (``docs/waves/``), ADR archives
(``docs/architecture/decisions/``), memory records, and this change's own
decision history are deliberately outside the census: history is evidence,
not live product surface.

Wave 1to78 (Requirement 5 / AC-5) extends the census to the tests tree.
Test files may legitimately carry retired tokens only at named
negative-assertion and probe sites: every allowance in ``TEST_ALLOWANCES``
names an exact file, and every allowance is load-bearing: an allowance whose
file no longer exists or no longer carries the token FAILS the census, so the
allowlist can never rot into a blanket exemption. This census module itself
is excluded from the scan: its token lists ARE the census, not residue.

Wave 1to78 (AC-1d) also forbids the prose-evidence helpers outside their one
legitimate home: the authority facade module ``review_evidence.py``, where the
prose implementation survives only as the legacy branch inside
``resolve_review_authority``. Any direct prose read in another shipped module
(``server_impl.py`` must have zero hits) fails the census.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
FRAMEWORK = REPO_ROOT / ".wavefoundry" / "framework"


# Adoption-only API symbols, migration helpers, retired projector, and
# adoption-only diagnostics: no live surface may mention any of them.
# Wave 1to78 appends the deleted inline-ledger machinery (the 1.13-era
# in-wave.md authority reader/renderer): the inline validator (the call/def
# form is listed because the plain name is a substring of the surviving
# ``validate_review_evidence_records``), the inline record parser, the inline
# renderer, the inline empty-section scaffolder, and the details-close
# constant orphaned by their deletion. Detection stays: the inline-marker
# fail-closed triggers and negative guards are live keeps, not residue.
FORBIDDEN_EVERYWHERE = (
    "validate_review_evidence(",
    "_parse_records",
    "render_review_evidence_records",
    "empty_finding_synthesis_section",
    "REVIEW_EVIDENCE_DETAILS_END",
    # Wave 1to78 delivery repair (DF3): the zero-caller prose-append helper
    # deleted from server_impl.py. Substring-safe: no surviving symbol
    # contains this token.
    "_append_review_evidence_state_line",
    "record_protocol_state",
    "adopted_protocol_state",
    "validate_adopted_protocol_state",
    "externalize_adopted_inline_wave_locked",
    "review_event_prefix_proof",
    "review_event_write_lock",
    "ADOPTION_LEDGER_REL",
    "ADOPTION_LOCK_REL",
    "REVIEW_EVENT_HASH_DOMAIN",
    "adopted_legacy_inline_protocol_state_for_migration",
    "record_legacy_inline_protocol_state_for_migration",
    "migrate_self_host_review_events",
    "phase_review_status_projection",
    "review_evidence_adoption_pending",
    "review_evidence_adoption_invalid",
    "adoption proof is ahead",
    "adopted prefix hash",
    "unadopted suffix",
)

# Removed sidecar names and lock literals: allowed only in their bounded
# roles (repo-relative paths).
BOUNDED_ALLOWANCES = {
    "review-evidence-adoptions.json": {
        # One-way deletion targets in the upgrade cutover, and the carriers
        # documenting that cutover boundary.
        ".wavefoundry/framework/scripts/upgrade_wavefoundry.py",
        ".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md",
        "docs/specs/mcp-tool-surface.md",
        "docs/contributing/build-and-verification.md",
    },
    "review-evidence-migration.json": {
        ".wavefoundry/framework/scripts/upgrade_wavefoundry.py",
        ".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md",
        "docs/specs/mcp-tool-surface.md",
        "docs/contributing/build-and-verification.md",
    },
    # The physical carrier of project_state_publication_lock: its definition,
    # the upgrade probe/cutover, and the docs that describe the carrier.
    "review-evidence-adoptions.lock": {
        ".wavefoundry/framework/scripts/review_evidence.py",
        ".wavefoundry/framework/scripts/upgrade_wavefoundry.py",
        ".wavefoundry/framework/scripts/upgrade_extensions.py",
        ".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md",
        "docs/architecture/cross-cutting-concerns.md",
        "docs/architecture/data-and-control-flow.md",
        "docs/architecture/domain-map.md",
    },
}

# Prose-evidence helpers (wave 1to78, AC-1d): legitimate ONLY inside the
# authority facade module, where they form the legacy branch of
# resolve_review_authority. Every other shipped module must derive review
# evidence through the facade; a direct prose read anywhere else is residue.
# `lane_has_signoff_in_evidence` also substring-catches the retired
# `_lane_has_signoff_in_evidence` server helper spelling.
FACADE_MODULE = ".wavefoundry/framework/scripts/review_evidence.py"
FORBIDDEN_OUTSIDE_FACADE = (
    "lane_has_signoff_in_evidence",
    "combined_review_evidence",
    "prepare_review_evidence",
    "prose_max_severity",
    "review_evidence_has_any_signoff_line",
    "_SEVERITY_WORD_RE",
)

# Test-scope allowances (wave 1to78, AC-5): exact file -> the retired tokens
# its negative assertions or probes legitimately carry. Every entry is
# load-bearing: `test_every_test_allowance_is_load_bearing` fails when the
# file is gone or the token no longer appears in it.
_TESTS_PREFIX = ".wavefoundry/framework/scripts/tests"
TEST_ALLOWANCES: dict[str, frozenset[str]] = {
    # Pack-content probe: asserts the deleted migration script ships in no pack.
    "migrate_self_host_review_events": frozenset({f"{_TESTS_PREFIX}/test_build_pack.py"}),
    # Retired-name absence assertions (assertNotIn over the module surface).
    "record_protocol_state": frozenset({
        f"{_TESTS_PREFIX}/test_review_evidence.py",
        f"{_TESTS_PREFIX}/test_server_context_efficiency.py",
    }),
    "adopted_protocol_state": frozenset({f"{_TESTS_PREFIX}/test_review_evidence.py"}),
    "validate_adopted_protocol_state": frozenset({f"{_TESTS_PREFIX}/test_review_evidence.py"}),
    "externalize_adopted_inline_wave_locked": frozenset({
        f"{_TESTS_PREFIX}/test_review_evidence.py",
        f"{_TESTS_PREFIX}/test_upgrade_wavefoundry.py",
    }),
    "review_event_prefix_proof": frozenset({f"{_TESTS_PREFIX}/test_review_evidence.py"}),
    "ADOPTION_LEDGER_REL": frozenset({f"{_TESTS_PREFIX}/test_review_evidence.py"}),
    "REVIEW_EVENT_HASH_DOMAIN": frozenset({f"{_TESTS_PREFIX}/test_review_evidence.py"}),
    "adopted_legacy_inline_protocol_state_for_migration": frozenset({
        f"{_TESTS_PREFIX}/test_review_evidence.py",
    }),
    "record_legacy_inline_protocol_state_for_migration": frozenset({
        f"{_TESTS_PREFIX}/test_review_evidence.py",
    }),
    "phase_review_status_projection": frozenset({f"{_TESTS_PREFIX}/test_upgrade_wavefoundry.py"}),
    # Sidecar-name literals: deletion-target fixtures in the upgrade cutover
    # tests and never-consulted / never-rendered negative assertions.
    "review-evidence-adoptions.json": frozenset({
        f"{_TESTS_PREFIX}/test_docs_lint.py",
        f"{_TESTS_PREFIX}/test_render_agent_surfaces.py",
        f"{_TESTS_PREFIX}/test_server_tools.py",
        f"{_TESTS_PREFIX}/test_upgrade_wavefoundry.py",
    }),
    "review-evidence-migration.json": frozenset({
        f"{_TESTS_PREFIX}/test_server_tools.py",
        f"{_TESTS_PREFIX}/test_upgrade_wavefoundry.py",
    }),
    # The lock literal is the live physical carrier of
    # project_state_publication_lock: cross-process lock probes are real uses.
    "review-evidence-adoptions.lock": frozenset({
        f"{_TESTS_PREFIX}/test_review_evidence.py",
        f"{_TESTS_PREFIX}/test_runtime_lock.py",
        f"{_TESTS_PREFIX}/test_upgrade_wavefoundry.py",
    }),
    # Prose-evidence helpers: legacy-branch probes exercised through the
    # review_evidence facade module object, never through server_impl.
    "lane_has_signoff_in_evidence": frozenset({f"{_TESTS_PREFIX}/test_server_tools.py"}),
    "combined_review_evidence": frozenset({f"{_TESTS_PREFIX}/test_server_tools.py"}),
    "prose_max_severity": frozenset({f"{_TESTS_PREFIX}/test_server_tools.py"}),
}

TEXT_SUFFIXES = {".py", ".md", ".json", ".toml", ".txt", ".yml", ".yaml", ".js", ".css", ".html", ".cmd", ".sh", ""}


def _census_files() -> list[Path]:
    files: list[Path] = []
    # Live shipped code (tests are outside the census scope).
    for path in sorted((FRAMEWORK / "scripts").rglob("*.py")):
        if "tests" in path.relative_to(FRAMEWORK / "scripts").parts:
            continue
        files.append(path)
    # Seeds, install/package assets, shipped dashboard assets.
    for base in (FRAMEWORK / "seeds", FRAMEWORK / "install", FRAMEWORK / "dashboard"):
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in TEXT_SUFFIXES:
                files.append(path)
    # Current rendered carriers and hand-authored current docs.
    for base in (
        REPO_ROOT / "docs" / "prompts",
        REPO_ROOT / "docs" / "specs",
        REPO_ROOT / "docs" / "contributing",
    ):
        files.extend(sorted(base.rglob("*.md")))
    for path in sorted((REPO_ROOT / "docs" / "architecture").glob("*.md")):
        files.append(path)  # decisions/ (ADR archive) deliberately excluded
    for path in sorted((REPO_ROOT / "docs" / "agents").glob("*.md")):
        files.append(path)  # memory/ and archives deliberately excluded
    for name in ("AGENTS.md", "CLAUDE.md"):
        candidate = REPO_ROOT / name
        if candidate.is_file():
            files.append(candidate)
    return files


def _scan_forbidden(files: list[Path], root: Path) -> list[str]:
    """Flag any forbidden adoption symbol/diagnostic in the given files."""
    violations: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        for token in FORBIDDEN_EVERYWHERE:
            if token in text:
                violations.append(f"{rel}: {token}")
    return violations


def _scan_bounded(files: list[Path], root: Path) -> list[str]:
    """Flag sidecar/lock literals appearing outside their bounded roles."""
    violations: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        for token, allowed in BOUNDED_ALLOWANCES.items():
            if token in text and rel not in allowed:
                violations.append(f"{rel}: {token}")
    return violations


def _scan_outside_facade(files: list[Path], root: Path) -> list[str]:
    """Flag prose-evidence helper tokens outside the facade module."""
    violations: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if rel == FACADE_MODULE:
            continue
        for token in FORBIDDEN_OUTSIDE_FACADE:
            if token in text:
                violations.append(f"{rel}: {token}")
    return violations


def _test_files(tests_root: Path | None = None) -> list[Path]:
    """The tests-tree census scope: every test module except this census."""
    base = (FRAMEWORK / "scripts" / "tests") if tests_root is None else tests_root
    self_path = Path(__file__).resolve()
    return [
        path for path in sorted(base.rglob("*.py"))
        if path.resolve() != self_path
    ]


def _all_census_tokens() -> tuple[str, ...]:
    return (
        FORBIDDEN_EVERYWHERE
        + tuple(BOUNDED_ALLOWANCES)
        + FORBIDDEN_OUTSIDE_FACADE
    )


def _scan_tests(files: list[Path], root: Path) -> list[str]:
    """Flag any retired or prose-evidence token in a test file outside its
    exact-file allowance."""
    violations: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        for token in _all_census_tokens():
            if token in text and rel not in TEST_ALLOWANCES.get(token, frozenset()):
                violations.append(f"{rel}: {token}")
    return violations


def _dead_test_allowances(
    root: Path, allowances: dict[str, frozenset[str]] | None = None
) -> list[str]:
    """Every allowance must keep matching: named file exists AND carries the
    token. A stale entry is a census failure, never a silent widening."""
    dead: list[str] = []
    table = TEST_ALLOWANCES if allowances is None else allowances
    for token, rels in sorted(table.items()):
        for rel in sorted(rels):
            path = root / rel
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                dead.append(f"{rel}: {token} (allowance file missing or unreadable)")
                continue
            if token not in text:
                dead.append(f"{rel}: {token} (allowance no longer matches)")
    return dead


class EventsOnlyResidueCensusTests(unittest.TestCase):
    def test_census_scope_is_non_vacuous(self):
        files = _census_files()
        rels = {str(f.relative_to(REPO_ROOT)).replace("\\", "/") for f in files}
        self.assertGreater(len(files), 100)
        self.assertIn(".wavefoundry/framework/scripts/review_evidence.py", rels)
        self.assertIn(".wavefoundry/framework/scripts/upgrade_wavefoundry.py", rels)
        self.assertIn("docs/architecture/data-and-control-flow.md", rels)
        self.assertIn("docs/specs/mcp-tool-surface.md", rels)

    def test_no_live_surface_retains_adoption_symbols_or_diagnostics(self):
        self.assertEqual(_scan_forbidden(_census_files(), REPO_ROOT), [])

    def test_sidecar_names_and_lock_literals_stay_in_bounded_roles(self):
        self.assertEqual(_scan_bounded(_census_files(), REPO_ROOT), [])

    def test_prose_evidence_reads_stay_inside_the_facade(self):
        # Wave 1to78 (AC-1d): the prose helpers live only in the facade
        # module's legacy branch; server_impl.py and every other shipped
        # surface must derive review evidence through resolve_review_authority.
        self.assertEqual(_scan_outside_facade(_census_files(), REPO_ROOT), [])

    def test_tests_tree_scope_is_non_vacuous(self):
        files = _test_files()
        rels = {str(f.relative_to(REPO_ROOT)).replace("\\", "/") for f in files}
        self.assertGreater(len(files), 20)
        self.assertIn(f"{_TESTS_PREFIX}/test_server_tools.py", rels)
        self.assertIn(f"{_TESTS_PREFIX}/test_review_evidence.py", rels)
        # The census module itself is the one deliberate exclusion.
        self.assertNotIn(
            f"{_TESTS_PREFIX}/test_events_only_residue_census.py", rels
        )

    def test_tests_tree_carries_no_unallowed_residue(self):
        self.assertEqual(_scan_tests(_test_files(), REPO_ROOT), [])

    def test_every_test_allowance_is_load_bearing(self):
        self.assertEqual(_dead_test_allowances(REPO_ROOT), [])

    def test_known_bad_control_is_detected(self):
        # Non-vacuity: plant one file per forbidden class in a temp scope and
        # prove the REAL scan helpers (the same code the census tests run)
        # walk and flag them.
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            forbidden = root / "planted_symbol.py"
            forbidden.write_text(
                "def helper():\n    return record_protocol_state(root)\n",
                encoding="utf-8",
            )
            sidecar = root / "planted_sidecar.md"
            sidecar.write_text(
                "reads docs/waves/review-evidence-adoptions.json here\n",
                encoding="utf-8",
            )
            self.assertEqual(
                _scan_forbidden([forbidden, sidecar], root),
                ["planted_symbol.py: record_protocol_state"],
            )
            self.assertEqual(
                _scan_bounded([forbidden, sidecar], root),
                ["planted_sidecar.md: review-evidence-adoptions.json"],
            )

    def test_planted_token_in_test_scope_outside_allowance_is_detected(self):
        # Wave 1to78 (AC-5 executed known-bad control): a retired token
        # planted in a test file with NO allowance entry is flagged by the
        # REAL test-scope scanner, and a token planted in a file that holds
        # an allowance for a DIFFERENT token is flagged too.
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tests_dir = root / _TESTS_PREFIX
            tests_dir.mkdir(parents=True)
            unallowed = tests_dir / "test_planted_probe.py"
            unallowed.write_text(
                "def test_probe():\n    assert 'record_protocol_state'\n",
                encoding="utf-8",
            )
            # This rel path holds an allowance for prose tokens, but not for
            # the adoption symbol planted here (per-file, per-token scoping).
            wrong_token = tests_dir / "test_server_tools.py"
            wrong_token.write_text(
                "LEDGER = 'ADOPTION_LEDGER_REL'\n",
                encoding="utf-8",
            )
            self.assertEqual(
                sorted(_scan_tests([unallowed, wrong_token], root)),
                [
                    f"{_TESTS_PREFIX}/test_planted_probe.py: record_protocol_state",
                    f"{_TESTS_PREFIX}/test_server_tools.py: ADOPTION_LEDGER_REL",
                ],
            )

    def test_planted_prose_read_outside_facade_is_detected(self):
        # Wave 1to78 (AC-1d executed known-bad control): a direct prose read
        # planted in a non-facade shipped module is flagged by the REAL
        # outside-facade scanner; the same text inside the facade module's
        # own path is not.
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts_dir = root / ".wavefoundry" / "framework" / "scripts"
            scripts_dir.mkdir(parents=True)
            planted = scripts_dir / "server_impl.py"
            planted.write_text(
                "def gate(text):\n    return prose_max_severity(text)\n",
                encoding="utf-8",
            )
            facade = scripts_dir / "review_evidence.py"
            facade.write_text(
                "def prose_max_severity(text):\n    return 'none'\n",
                encoding="utf-8",
            )
            self.assertEqual(
                _scan_outside_facade([planted, facade], root),
                [".wavefoundry/framework/scripts/server_impl.py: prose_max_severity"],
            )

    def test_dead_allowance_fails_the_census(self):
        # Wave 1to78 (AC-5): allowances are load-bearing in both directions;
        # a missing file and a no-longer-matching file are each reported by
        # the REAL allowance checker.
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tests_dir = root / _TESTS_PREFIX
            tests_dir.mkdir(parents=True)
            stale = tests_dir / "test_token_gone.py"
            stale.write_text("def test_nothing():\n    pass\n", encoding="utf-8")
            synthetic = {
                "record_protocol_state": frozenset({
                    f"{_TESTS_PREFIX}/test_token_gone.py",
                    f"{_TESTS_PREFIX}/test_file_gone.py",
                }),
            }
            self.assertEqual(
                _dead_test_allowances(root, synthetic),
                [
                    f"{_TESTS_PREFIX}/test_file_gone.py: record_protocol_state "
                    "(allowance file missing or unreadable)",
                    f"{_TESTS_PREFIX}/test_token_gone.py: record_protocol_state "
                    "(allowance no longer matches)",
                ],
            )


if __name__ == "__main__":
    unittest.main()
