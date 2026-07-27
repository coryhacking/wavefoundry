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
not live product surface. Test files are also outside it — the dedicated dead
tests were deleted, and the surviving tests only assert absence.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
FRAMEWORK = REPO_ROOT / ".wavefoundry" / "framework"


# Adoption-only API symbols, migration helpers, retired projector, and
# adoption-only diagnostics: no live surface may mention any of them.
FORBIDDEN_EVERYWHERE = (
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


if __name__ == "__main__":
    unittest.main()
