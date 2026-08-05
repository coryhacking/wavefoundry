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

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
FRAMEWORK = REPO_ROOT / ".wavefoundry" / "framework"
if str(FRAMEWORK / "scripts") not in sys.path:
    sys.path.insert(0, str(FRAMEWORK / "scripts"))

from review_policy import RETIRED_LIFECYCLE_TOKENS


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
        ".wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py",
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
        f"{_TESTS_PREFIX}/test_review_policy.py",
        f"{_TESTS_PREFIX}/test_runtime_lock.py",
        f"{_TESTS_PREFIX}/test_upgrade_wavefoundry.py",
    }),
    # Prose-evidence helpers: legacy-branch probes exercised through the
    # review_evidence facade module object, never through server_impl.
    "lane_has_signoff_in_evidence": frozenset({f"{_TESTS_PREFIX}/test_server_tools.py"}),
    "combined_review_evidence": frozenset({f"{_TESTS_PREFIX}/test_server_tools.py"}),
    "prose_max_severity": frozenset({f"{_TESTS_PREFIX}/test_server_tools.py"}),
}

TEXT_SUFFIXES = {".py", ".md", ".mdc", ".json", ".toml", ".txt", ".yml", ".yaml", ".js", ".css", ".html", ".cmd", ".sh", ""}


# Wave 1tsyx (AC-3): the retired pre-implementation review gate appears as
# both a machine-readable verdict token and prose. Keep the forms separate so
# a carrier cannot survive merely by dropping the token while retaining the
# instruction. Matching is case-insensitive; the values here are normalized.
PREIMPLEMENTATION_GATE_TOKENS = RETIRED_LIFECYCLE_TOKENS

# These are the committed, project-local host surfaces rendered by the
# framework today, plus reserved roots for supported hosts whose renderer may
# add a surface later. Scanning a missing directory is intentionally a no-op;
# the non-vacuity test pins every surface that exists in this repository.
PREIMPLEMENTATION_PLATFORM_DIRS = (
    ".agents",       # Antigravity
    ".air",          # Air (when a project-local surface is available)
    ".claude",       # Claude Code
    ".codex",        # Codex
    ".cursor",       # Cursor
    ".github",       # Copilot
    ".junie",        # Junie
    ".vscode",       # Copilot workspace surface, when present
    ".windsurf",     # Windsurf
)
PREIMPLEMENTATION_ROOT_SURFACES = (
    "AGENTS.md",
    "AIR.md",
    "CLAUDE.md",
    "GEMINI.md",
    "README.md",
    "WARP.md",
)

# Exact file/token/count allowances for historical prose that is evidence of
# the retired gate rather than a live instruction. The expected count makes
# each allowance load-bearing in both directions: deletion makes it stale and
# another occurrence in the same file exceeds the allowance rather than being
# hidden by it. Every entry also carries its required written justification.
PREIMPLEMENTATION_GATE_ALLOWANCES: dict[
    str, dict[str, tuple[int, str]]
] = {}


# Wave 1ug7o: the delivered mapping is `enabled -> targeted` and the
# fresh-install default is `targeted` (`review_policy.FRESH_INSTALL_DELIVERY_MODE`,
# and the canonical `UPGRADE_POLICY_BLOCK` sentence). Four living doc surfaces
# drifted into claiming `universal` on that axis after wave 1u7dq flipped the
# default, promising downstream operators a heavier review posture than the
# upgrade configures.
#
# The pin keys on the CLAIM, never on the bare word: `universal` is a live legal
# enum value with dozens of legitimate occurrences in scope (mode enumerations
# such as "every wave in `universal`", `server_impl.py`'s fail-closed
# `"delivery_mode": "universal"` default on malformed policy, and unrelated
# English uses like "universal specialist"). A bare-token sweep would be red on
# contact against correct prose, then loosened, then rotted, which is the exact
# failure this pin exists to prevent.
#
# There is deliberately NO allowance table for these patterns. The expected
# count for every pattern, in every file the census reads, is zero, so an
# allowance could exempt nothing: any entry admitting an occurrence would
# immediately fail `test_universal_delivery_mode_claim_count_is_zero_across_scope`,
# which is the stronger pin. If a future carrier ever needs a genuine exemption,
# add the table then, with a real entry and a written justification, in the
# shape PREIMPLEMENTATION_GATE_ALLOWANCES already establishes.
DELIVERY_MODE_CLAIM_TOKENS = (
    "delivery_mode=universal",
    "delivery_mode: universal",
    "enabled review to `universal`",
)


def _normalized_preimplementation_text(text: str) -> str:
    """Case-fold and collapse layout whitespace so line wrapping cannot evade a token."""
    return " ".join(text.casefold().split())


def _preimplementation_carrier_files(root: Path = REPO_ROOT) -> list[Path]:
    """Return every current carrier that may install or instruct the gate."""
    relative_dirs = (
        ".wavefoundry/framework/seeds",
        ".wavefoundry/framework/install",
        "docs/prompts",
        "docs/agents",
        "docs/architecture",
        "docs/contributing",
        "docs/references",
        "docs/specs",
        *PREIMPLEMENTATION_PLATFORM_DIRS,
    )
    files: set[Path] = set()
    for rel in relative_dirs:
        base = root / rel
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in TEXT_SUFFIXES:
                files.add(path)
    for rel in PREIMPLEMENTATION_ROOT_SURFACES:
        path = root / rel
        if path.is_file():
            files.add(path)
    framework_readme = root / ".wavefoundry" / "framework" / "README.md"
    if framework_readme.is_file():
        files.add(framework_readme)
    owner_readme = root / ".wavefoundry" / "README.md"
    if owner_readme.is_file():
        files.add(owner_readme)
    return sorted(files)


def _scan_preimplementation_gate(files: list[Path], root: Path) -> list[str]:
    """Flag retired gate carriers outside exact, count-bounded allowances."""
    violations: list[str] = []
    for path in files:
        try:
            text = _normalized_preimplementation_text(
                path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        for token in PREIMPLEMENTATION_GATE_TOKENS:
            count = text.count(token)
            if count == 0:
                continue
            allowance = PREIMPLEMENTATION_GATE_ALLOWANCES.get(token, {}).get(rel)
            if allowance is not None and count == allowance[0]:
                continue
            violations.append(f"{rel}: {token} ({count} occurrence(s))")
    return violations


def _dead_preimplementation_allowances(
    root: Path,
    allowances: dict[str, dict[str, tuple[int, str]]] | None = None,
) -> list[str]:
    """Reject missing, stale, count-drifted, or unjustified allowances."""
    dead: list[str] = []
    table = PREIMPLEMENTATION_GATE_ALLOWANCES if allowances is None else allowances
    for token, entries in sorted(table.items()):
        for rel, (expected_count, justification) in sorted(entries.items()):
            path = root / rel
            try:
                text = _normalized_preimplementation_text(
                    path.read_text(encoding="utf-8")
                )
            except (OSError, UnicodeDecodeError):
                dead.append(f"{rel}: {token} (allowance file missing or unreadable)")
                continue
            actual_count = text.count(token)
            if actual_count != expected_count:
                dead.append(
                    f"{rel}: {token} (allowance expected {expected_count}, "
                    f"found {actual_count})"
                )
            if not justification.strip():
                dead.append(f"{rel}: {token} (allowance has no justification)")
    return dead


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
    # Current rendered carriers and hand-authored current docs. `docs/references/`
    # joined the scope in wave 1ug7o: `project-overview.md` is the Tier-1
    # startup doc AGENTS.md lists as read-first, and it carried the drifted
    # delivery-mode claim while sitting outside every executable census.
    for base in (
        REPO_ROOT / "docs" / "prompts",
        REPO_ROOT / "docs" / "specs",
        REPO_ROOT / "docs" / "contributing",
        REPO_ROOT / "docs" / "references",
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


def _scan_delivery_mode_claim(files: list[Path], root: Path) -> list[str]:
    """Flag any live claim that upgrade or fresh install selects `universal`.

    No occurrence is exempt (see the DELIVERY_MODE_CLAIM_TOKENS note), and the
    text is normalized the same way as the retired-gate scan so a line wrap or a
    capitalization change cannot carry the claim past the pin.
    """
    violations: list[str] = []
    for path in files:
        try:
            text = _normalized_preimplementation_text(
                path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        for token in DELIVERY_MODE_CLAIM_TOKENS:
            count = text.count(token)
            if count == 0:
                continue
            violations.append(f"{rel}: {token} ({count} occurrence(s))")
    return violations


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
        # Wave 1ug7o: the Tier-1 startup doc is inside the scope, and the ADR
        # archive stays outside it (1tsbu-adr keeps its original decision text
        # under an amendment note, so the census must never read it).
        self.assertIn("docs/references/project-overview.md", rels)
        self.assertNotIn(
            "docs/architecture/decisions/"
            "1tsbu-adr review-policy-and-upgrade-protocol.md",
            rels,
        )

    def test_preimplementation_carrier_scope_is_non_vacuous(self):
        files = _preimplementation_carrier_files()
        rels = {str(f.relative_to(REPO_ROOT)).replace("\\", "/") for f in files}
        # Canonical/install/rendered prompt carriers plus the public README.
        self.assertIn(
            ".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md", rels
        )
        self.assertIn(
            ".wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md",
            rels,
        )
        self.assertIn("docs/prompts/implement-wave.prompt.md", rels)
        self.assertIn(".wavefoundry/README.md", rels)
        self.assertIn(".wavefoundry/framework/README.md", rels)
        self.assertIn("docs/contributing/feature-workflow.md", rels)
        self.assertIn("README.md", rels)
        # Every committed platform family is inside the executable scope.
        self.assertIn(".agents/mcp_config.json", rels)
        self.assertIn(".claude/skills/upgrade-wave.md", rels)
        self.assertIn(".codex/skills/auto-guru/SKILL.md", rels)
        self.assertIn(".cursor/rules/project-context.mdc", rels)
        self.assertIn(".github/copilot-instructions.md", rels)
        self.assertIn(".junie/guidelines.md", rels)
        self.assertIn(".windsurf/hooks/docs-lint.py", rels)
        self.assertIn("WARP.md", rels)

    def test_no_live_surface_retains_preimplementation_review_gate(self):
        self.maxDiff = None
        self.assertEqual(
            _scan_preimplementation_gate(
                _preimplementation_carrier_files(), REPO_ROOT
            ),
            [],
        )

    def test_review_system_keeps_the_existing_final_readiness_recheck_contract(self):
        text = (
            REPO_ROOT / ".wavefoundry" / "framework" / "seeds"
            / "007-review-system-overview.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "The same readiness evaluation used before implementation should be rerun "
            "during final review before closure.",
            text,
        )
        self.assertNotIn(
            "does not rerun or replace the readiness decision",
            text,
        )

    def test_upgrade_seed_does_not_claim_downstream_reconciliation(self):
        text = (
            REPO_ROOT / ".wavefoundry" / "framework" / "seeds"
            / "160-upgrade-wavefoundry.prompt.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "reconcile every previously installed retired review-lifecycle carrier",
            text,
        )
        self.assertNotIn(
            "recursively scan every live file under `docs/prompts/`",
            text,
        )
        self.assertNotIn(
            "## Retired review-lifecycle reconciliation",
            (
                REPO_ROOT / "docs" / "prompts" / "upgrade-wavefoundry.prompt.md"
            ).read_text(encoding="utf-8"),
        )

    def test_historical_target_carrier_family_is_detected_before_reconciliation(self):
        import tempfile

        historical = {
            "docs/prompts/implement-wave.prompt.md": (
                "## Pre-Implementation Review Gate\n"
                "Runs parallel reviewer lanes (those with no shared dependencies) concurrently.\n"
                "Level 2 is the reviewer loop; reviewers participate during implementation.\n"
            ),
            "docs/prompts/review-wave.prompt.md": (
                "## Pre-Implementation Gate Reconciliation\n"
                "Blocking findings return the wave to implementation (Level 2 loop).\n"
                "Verify that the prior prepare-council verdict was structured and machine-readable.\n"
            ),
            "docs/prompts/agents/review-wave.prompt.md": (
                "Level 2: fix and re-run reviewer, no re-Prepare.\n"
            ),
            "docs/prompts/council-review.prompt.md": (
                "The recorded verdict must be written back into `## Review Checkpoints` "
                "as a structured `prepare-council` line.\n"
                "The lifecycle gate only accepts that structured verdict.\n"
            ),
            "docs/prompts/prepare-wave.prompt.md": (
                "The recorded verdict must be a structured `prepare-council` line.\n"
                "`wf_prepare_wave` signals this step with `status: \"ready_for_council_review\"`.\n"
                "pre-implementation-review: passed\n"
            ),
        }
        current = {
            "docs/prompts/implement-wave.prompt.md": (
                "Prepare owns the single pre-code critique; an exceptional named checkpoint "
                "is available at a high-risk boundary.\n"
            ),
            "docs/prompts/review-wave.prompt.md": (
                "Record repair_start before mutation and reverify the typed finding chain.\n"
            ),
            "docs/prompts/agents/review-wave.prompt.md": (
                "Level 2: exceptional named checkpoint at the affected boundary.\n"
            ),
            "docs/prompts/council-review.prompt.md": (
                "Declared waves consume typed readiness authority; legacy prose stays narrative.\n"
            ),
            "docs/prompts/prepare-wave.prompt.md": (
                "Readiness approval is the single pre-code review decision.\n"
            ),
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, body in historical.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")

            violations = _scan_preimplementation_gate(
                _preimplementation_carrier_files(root), root
            )
            violation_paths = {entry.split(": ", 1)[0] for entry in violations}
            self.assertEqual(violation_paths, set(historical))

            for rel, body in current.items():
                (root / rel).write_text(body, encoding="utf-8")
            self.assertEqual(
                _scan_preimplementation_gate(
                    _preimplementation_carrier_files(root), root
                ),
                [],
            )

    def test_each_new_historical_semantic_route_is_detected_individually(self):
        import tempfile

        routes = {
            "`wf_prepare_wave` signals this step with `status: \"ready_for_council_review\"`":
                "`wf_prepare_wave` signals this step with `status: \"ready_for_council_review\"`",
            "The recorded verdict must be a structured `prepare-council` line":
                "the recorded verdict must be a structured `prepare-council` line",
            "Runs parallel reviewer lanes (those with no shared dependencies) concurrently":
                "runs parallel reviewer lanes (those with no shared dependencies) concurrently",
            "The recorded verdict must be written back into `## Review Checkpoints` "
            "as a structured `prepare-council` line":
                "recorded verdict must be written back into `## review checkpoints` "
                "as a structured `prepare-council` line",
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            probe = root / "docs" / "prompts" / "probe.prompt.md"
            probe.parent.mkdir(parents=True)
            for body, expected_token in routes.items():
                with self.subTest(body=body):
                    probe.write_text(body + "\n", encoding="utf-8")
                    self.assertEqual(
                        _scan_preimplementation_gate([probe], root),
                        [f"docs/prompts/probe.prompt.md: {expected_token} (1 occurrence(s))"],
                    )

    def test_every_preimplementation_allowance_is_load_bearing(self):
        self.assertEqual(_dead_preimplementation_allowances(REPO_ROOT), [])

    def test_stale_preimplementation_allowance_fails_the_census(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stale = root / "docs" / "agents" / "history.md"
            stale.parent.mkdir(parents=True)
            stale.write_text("no retired gate vocabulary here\n", encoding="utf-8")
            synthetic = {
                "pre-implementation review gate": {
                    "docs/agents/history.md": (1, "historical record"),
                    "docs/agents/missing.md": (1, "historical record"),
                },
                "pre-implementation-review": {
                    "docs/agents/history.md": (0, ""),
                },
            }
            self.assertEqual(
                _dead_preimplementation_allowances(root, synthetic),
                [
                    "docs/agents/history.md: pre-implementation review gate "
                    "(allowance expected 1, found 0)",
                    "docs/agents/missing.md: pre-implementation review gate "
                    "(allowance file missing or unreadable)",
                    "docs/agents/history.md: pre-implementation-review "
                    "(allowance has no justification)",
                ],
            )

    def test_preimplementation_census_detects_seed_and_non_seed_mutations(self):
        # AC-3 known-bad controls use the REAL scope builder and scanner. One
        # plants seed 160's prose carrier; the other plants the verdict token
        # in README.md, proving the census is not a seeds-only check.
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = (
                root
                / ".wavefoundry"
                / "framework"
                / "seeds"
                / "160-upgrade-wavefoundry.prompt.md"
            )
            seed.parent.mkdir(parents=True)
            seed.write_text(
                "Restore the Pre-Implementation Review Gate.\n",
                encoding="utf-8",
            )
            framework_readme = root / ".wavefoundry" / "framework" / "README.md"
            framework_readme.parent.mkdir(parents=True, exist_ok=True)
            framework_readme.write_text(
                "Level 2 is the reviewer loop.\n", encoding="utf-8"
            )
            owner_readme = root / ".wavefoundry" / "README.md"
            owner_readme.write_text(
                "L2 is the reviewer loop.\n", encoding="utf-8"
            )
            readme = root / "README.md"
            readme.write_text(
                "pre-implementation-review: passed\n", encoding="utf-8"
            )
            workflow = root / "docs" / "contributing" / "feature-workflow.md"
            workflow.parent.mkdir(parents=True, exist_ok=True)
            workflow.write_text(
                "reviewers participate during implementation\n"
                "fix and re-run reviewer\n"
                "blocking findings return the wave to implementation (Level 2 loop)\n",
                encoding="utf-8",
            )
            files = _preimplementation_carrier_files(root)
            rels = {str(f.relative_to(root)).replace("\\", "/") for f in files}
            self.assertEqual(
                rels,
                {
                    ".wavefoundry/README.md",
                    ".wavefoundry/framework/README.md",
                    ".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md",
                    "README.md",
                    "docs/contributing/feature-workflow.md",
                },
            )
            self.assertEqual(
                _scan_preimplementation_gate(files, root),
                [
                    ".wavefoundry/README.md: reviewer loop (1 occurrence(s))",
                    ".wavefoundry/framework/README.md: reviewer loop (1 occurrence(s))",
                    ".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md: "
                    "pre-implementation review gate (1 occurrence(s))",
                    "README.md: pre-implementation-review (1 occurrence(s))",
                    "docs/contributing/feature-workflow.md: fix and re-run reviewer "
                    "(1 occurrence(s))",
                    "docs/contributing/feature-workflow.md: blocking findings return the wave "
                    "to implementation (level 2 loop) (1 occurrence(s))",
                    "docs/contributing/feature-workflow.md: reviewers participate during "
                    "implementation (1 occurrence(s))",
                ],
            )

    def test_no_live_surface_retains_adoption_symbols_or_diagnostics(self):
        self.assertEqual(_scan_forbidden(_census_files(), REPO_ROOT), [])

    def test_sidecar_names_and_lock_literals_stay_in_bounded_roles(self):
        self.assertEqual(_scan_bounded(_census_files(), REPO_ROOT), [])

    def test_prose_evidence_reads_stay_inside_the_facade(self):
        # Wave 1to78 (AC-1d): the prose helpers live only in the facade
        # module's legacy branch; server_impl.py and every other shipped
        # surface must derive review evidence through resolve_review_authority.
        self.assertEqual(_scan_outside_facade(_census_files(), REPO_ROOT), [])

    def test_no_live_surface_claims_the_universal_delivery_mode(self):
        # Wave 1ug7o (AC-3/AC-4): no live carrier may say the upgrade maps
        # enabled review to `universal`, or that `universal` is the shipped
        # default. Both are false: the mapping is `enabled -> targeted`.
        self.maxDiff = None
        self.assertEqual(
            _scan_delivery_mode_claim(_census_files(), REPO_ROOT), []
        )

    def test_universal_delivery_mode_claim_count_is_zero_across_scope(self):
        # The expected count for every claim pattern is zero everywhere in
        # scope, so no allowance can hide an occurrence behind a matching count.
        counts = {token: 0 for token in DELIVERY_MODE_CLAIM_TOKENS}
        for path in _census_files():
            try:
                text = _normalized_preimplementation_text(
                    path.read_text(encoding="utf-8")
                )
            except (OSError, UnicodeDecodeError):
                continue
            for token in DELIVERY_MODE_CLAIM_TOKENS:
                counts[token] += text.count(token)
        self.assertEqual(counts, {token: 0 for token in DELIVERY_MODE_CLAIM_TOKENS})

    def test_each_planted_universal_delivery_mode_claim_is_detected(self):
        # Wave 1ug7o (AC-4 known-bad control): each claim pattern is caught
        # individually, so a carrier cannot survive by reformatting one of the
        # three spellings, and a wrapped claim is caught too.
        import tempfile

        planted = {
            "legacy enabled projects become `wave_review.delivery_mode=universal`":
                "delivery_mode=universal",
            "the framework ships `delivery_mode: universal` by default":
                "delivery_mode: universal",
            "it maps legacy enabled review to `universal` and disabled review to "
            "`disabled`":
                "enabled review to `universal`",
            "the framework ships `delivery_mode:\nuniversal` by default":
                "delivery_mode: universal",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            probe = root / "docs" / "references" / "probe.md"
            probe.parent.mkdir(parents=True)
            for body, expected_token in planted.items():
                with self.subTest(body=body):
                    probe.write_text(body + "\n", encoding="utf-8")
                    self.assertEqual(
                        _scan_delivery_mode_claim([probe], root),
                        [
                            "docs/references/probe.md: "
                            f"{expected_token} (1 occurrence(s))"
                        ],
                    )

    def test_legitimate_universal_mode_uses_do_not_trip_the_claim_pin(self):
        # The negative controls: the fail-closed default shape shipped in
        # server_impl.py, a correct mode enumeration, and unrelated English.
        # None of them asserts the false mapping, so none may be flagged.
        import tempfile

        allowed = (
            '        return {"enabled": True, "delivery_mode": "universal"}',
            "Delivery Council is mode-specific: every wave in `universal`, "
            "risk/receipt-selected waves in `targeted`.",
            "`delivery_mode` is exactly `disabled | targeted | universal`.",
            "The universal specialist lane owns the universal fallback.",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            probe = root / "docs" / "references" / "probe.md"
            probe.parent.mkdir(parents=True)
            for body in allowed:
                with self.subTest(body=body):
                    probe.write_text(body + "\n", encoding="utf-8")
                    self.assertEqual(_scan_delivery_mode_claim([probe], root), [])

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
