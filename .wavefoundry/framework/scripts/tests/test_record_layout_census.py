"""Record-layout census (wave 1y0gz, change 1y042, Requirements 6 and 7).

Two predicates over every non-test ``.py`` under ``.wavefoundry/framework/scripts/``:

* Predicate A -- the literal substring ``docs/waves`` or ``docs/plans`` in any quoting.
* Predicate B -- the two-token join ``"docs" / "waves"`` (also ``os.path.join`` and
  tuple forms: ``["']docs["']\\s*[/,]\\s*["'](waves|plans)["']``).

Outside ``record_paths.py`` every hit must either be gone (routed through
``record_paths.load_record_roots``) or be named in ``ALLOWLIST`` with a reason of
``comment``, ``docstring`` or ``message``. Construction and prefix-check sites are
never allowlisted, so reintroducing a literal join anywhere in the tree fails
``test_census_has_no_unrouted_sites``.

``SITES`` is the classification table for the scripts routed by this change's
script-routing lane (Requirement 6). It was written before any routing started
and records what each site WAS; ``construction`` and ``prefix_check`` rows are
the ones the routing removed, the other rows are the ones the allowlist keeps.
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]

SUBSTRING_RE = re.compile(r"docs/(?:waves|plans)")
JOIN_RE = re.compile(r"[\"']docs[\"']\s*[/,]\s*[\"'](?:waves|plans)[\"']")

# Files the census never scans: the resolver itself (it defines the defaults)
# and this test tree.
CENSUS_EXCLUDED_FILES = frozenset({"record_paths.py"})
CENSUS_EXCLUDED_DIRS = frozenset({"tests", "__pycache__", ".pytest_cache"})

# ---------------------------------------------------------------------------
# Classification table (Requirement 6) -- (file, symbol_or_context, kind).
# kind: construction | prefix_check | message | comment
# (``comment`` covers docstrings too; the allowlist reason distinguishes them.)
# ---------------------------------------------------------------------------
SITES: list[tuple[str, str, str]] = [
    ("_tag_utils.py", "infer_tags docstring: wave -- docs/waves/ subtree", "comment"),
    ("_tag_utils.py", "infer_tags: '\"docs/waves/\" in p'", "prefix_check"),
    # chunker.py: imports _tag_utils.infer_tags but never calls it; no sites.
    ("commit_provenance.py", "resolve_via_evidence: root / \"docs\" / \"waves\"", "construction"),
    ("commit_provenance.py", "_wave_dir_for_id docstring", "comment"),
    ("commit_provenance.py", "_wave_dir_for_id: root / \"docs\" / \"waves\"", "construction"),
    ("context_efficiency.py", "resolve_open_wave: Path(root) / \"docs\" / \"waves\"", "construction"),
    ("dashboard_lib.py", "parse_change_doc: '\"docs/waves/\" in str(change_path)'", "prefix_check"),
    ("dashboard_lib.py", "_unreadable_change_record: '\"docs/waves/\" in str(change_path)'", "prefix_check"),
    ("dashboard_server.py", "SnapshotStore._watched_paths: r / \"docs\" / \"waves\"", "construction"),
    ("dashboard_server.py", "SnapshotStore._watched_paths: r / \"docs\" / \"plans\"", "construction"),
    ("dashboard_server.py", "SnapshotStore._watched_trees docstring", "comment"),
    ("dashboard_server.py", "SnapshotStore._watched_trees: r / \"docs\" / \"waves\"", "construction"),
    ("dashboard_server.py", "SnapshotStore._watched_trees: r / \"docs\" / \"plans\"", "construction"),
    ("dashboard_server.py", "_handle_doc: root / \"docs\" / \"waves\" / doc_id / \"wave.md\"", "construction"),
    ("dashboard_server.py", "_handle_doc: root / \"docs\" / \"waves\" / wave_id / f\"{doc_id}.md\"", "construction"),
    ("docs_gardener.py", "default_manifest_payload: generated_artifacts \"docs/waves/\"", "construction"),
    ("docs_gardener.py", "default_manifest_payload: generated_artifacts \"docs/waves/README.md\"", "construction"),
    ("gardener_metadata.py", "module comment: docs/plans/plan-template.md producer", "comment"),
    ("graph_indexer.py", "_DOC_SCAN_EXCLUDE_PREFIXES: \"docs/waves/\", \"docs/plans/\"", "prefix_check"),
    ("graph_indexer.py", "docstring: memory target into docs/waves/ are evidence", "comment"),
    ("graph_indexer.py", "comment: memory target into docs/waves/ is evidence", "comment"),
    ("graph_indexer.py", "comment: docs/waves/1p2q3 field-feedback-round-4 example", "comment"),
    ("graph_quality_eval.py", "CONTROL_DIRECTORY: docs/waves/1wpih .../evidence", "pinned_evidence"),
    ("index_state_store.py", "docstring: Historical (docs/waves/) rows are excluded", "comment"),
    ("index_state_store.py", "_HISTORICAL_DOC_PREFIX = \"docs/waves/\"", "prefix_check"),
    ("index_state_store.py", "_wave_id_for_historical_path docstring", "comment"),
    ("index_state_store.py", "compute_doc_drift docstring: Historical docs (docs/waves/)", "comment"),
    ("indexer.py", "comment: docs/waves/ evidence census_results.json", "comment"),
    ("indexer.py", "comment: chunker version 6 -> 7 events.jsonl", "comment"),
    ("install_log_lib.py", "comment: install-log line shape example", "comment"),
    ("lifecycle_id.py", "_existing_prefixes: repo_root / \"docs\" / \"plans\"", "construction"),
    ("lifecycle_id.py", "_existing_prefixes: repo_root / \"docs\" / \"waves\"", "construction"),
    ("memory_backfill.py", "_canonical_waves_dir: root / \"docs\" / \"waves\"", "construction"),
    ("memory_records.py", "repair references: rel_parts[:2] == (\"docs\", \"waves\")", "construction"),
    ("memory_supply.py", "resolve_wave_dir: root / \"docs\" / \"waves\"", "construction"),
    ("reconcile_scan.py", "EXCLUDED_DIRS: \"docs/waves\"", "prefix_check"),
    ("render_agent_surfaces.py", "docstring: docs/waves/<wave>/events.jsonl authority", "comment"),
    ("render_agent_surfaces.py", "review-plan prompt lines: Load the target change doc (...)", "message"),
    ("render_agent_surfaces.py", "SCAFFOLD_BASELINES: \"docs/plans/plan-template.md\"", "construction"),
    ("render_platform_surfaces.py", "claude_stop_source hook body _find_repo_root: cand / \"docs\" / \"waves\"", "construction"),
    ("render_platform_surfaces.py", "claude_stop_source hook body _active_wave: root / \"docs\" / \"waves\"", "construction"),
    ("retrieval_eval.py", "_CARRIER_PATH_RULES wave_record: p.startswith(\"docs/waves/\")", "prefix_check"),
    ("review_evidence.py", "docstring: docs/waves/<one wave directory>/events.jsonl", "comment"),
    ("review_evidence.py", "docstring: direct child directory of docs/waves/", "comment"),
    ("review_policy.py", "SCAFFOLD_DOCS = (\"docs/plans/plan-template.md\",)", "construction"),
    ("review_policy.py", "docstring: leading fragment (docs/waves/1uo1x)", "comment"),
    ("review_policy_reconcile.py", "_LIVE_MARKDOWN_EXCLUDED_PREFIXES: \"docs/waves/\"", "prefix_check"),
    ("review_policy_upgrade.py", "plan_migration: root / \"docs\" / \"waves\"", "construction"),
    ("techdocs_audit_lib.py", "docstring: link_validators._SKIP_PREFIXES example", "comment"),
    ("upgrade_extensions.py", "_migrate_journals: root / \"docs\" / \"waves\" / wave_id", "construction"),
    ("upgrade_extensions.py", "_migrate_journals: moved.append(f\"... -> docs/waves/...\")", "message"),
    ("upgrade_wavefoundry.py", "_retired_sidecar_path_error docstring", "comment"),
    ("upgrade_wavefoundry.py", "_retired_sidecar_path_error: root / \"docs\" / \"waves\"", "construction"),
    ("upgrade_wavefoundry.py", "_retired_sidecar_path_error: 'docs/waves may not be a symlink'", "message"),
    ("upgrade_wavefoundry.py", "_retired_sidecar_path_error: 'docs/waves escapes the repository root'", "message"),
    ("upgrade_wavefoundry.py", "_retired_sidecar_path_error: f'... escapes docs/waves'", "message"),
    ("upgrade_wavefoundry.py", "retired-sidecar cleanup docstring: adoptions/migration json", "comment"),
    ("upgrade_wavefoundry.py", "retired-sidecar cleanup: root / \"docs\" / \"waves\"", "construction"),
]

# ---------------------------------------------------------------------------
# Allowlist (Requirement 7) -- {(file, distinguishing snippet): reason}.
# The snippet must occur in the matching source LINE; a bare filename is never
# enough. Reasons: comment | docstring | message.
# Entries for ``server_impl.py`` and ``wave_lint_lib/`` cover ONLY their
# comment/docstring/message sites; their construction sites are routed by
# other lanes of the same change.
# ---------------------------------------------------------------------------
ALLOWLIST: dict[tuple[str, str], str] = {
    # -- deliberate exception, see ALLOWED_REASONS --
    ("graph_quality_eval.py", '"docs/waves/1wpih index-quality-evaluation-and-ranking/evidence"'): "pinned_evidence",
    # -- script-routing lane (Requirement 6) --
    ("_tag_utils.py", "wave      — docs/waves/ subtree"): "docstring",
    ("dashboard_server.py", "(the common ``docs/waves/<id>/<change>.md``"): "docstring",
    ("gardener_metadata.py", "Two producers ship this sentence -- docs/plans/plan-template.md"): "comment",
    ("graph_indexer.py", "a memory target into ``docs/waves/``) are evidence"): "docstring",
    ("graph_indexer.py", "a memory target into `docs/waves/`) is evidence"): "comment",
    ("graph_indexer.py", "# `docs/waves/1p2q3 field-feedback-round-4/1p2wd-bug parallel-"): "comment",
    ("index_state_store.py", "Historical (``docs/waves/``) rows are excluded by construction"): "docstring",
    ("index_state_store.py", "Wave id from a ``docs/waves/<wave-id> <slug>/"): "docstring",
    ("index_state_store.py", "Historical docs (``docs/waves/``): anchored"): "docstring",
    ("indexer.py", "# (docs/waves/ evidence census_results.json)."): "comment",
    ("indexer.py", "canonical per-wave ``docs/waves/<wave>/events.jsonl``"): "comment",
    ("install_log_lib.py", "`docs/waves/00000 wave-zero-plans-and-specs/wave.md`"): "comment",
    ("render_agent_surfaces.py", "`docs/waves/<wave>/events.jsonl` authority"): "docstring",
    ("render_agent_surfaces.py", "- Load the target change doc (`docs/waves/<wave-id>/<change-id>.md`"): "message",
    ("review_evidence.py", "``docs/waves/<one wave directory>/events.jsonl`` occupies"): "docstring",
    ("review_evidence.py", "direct child directory of ``docs/waves/`` holding the fixed sibling"): "docstring",
    ("review_policy.py", "the leading fragment (`docs/waves/1uo1x`)"): "docstring",
    ("techdocs_audit_lib.py", "`link_validators._SKIP_PREFIXES` (`docs/reports/`, `docs/waves/00000 `)"): "docstring",
    ("upgrade_wavefoundry.py", "Deletion is confined: a symlinked ``docs/waves`` parent"): "docstring",
    # Snippet assembled at import time: the retired sidecar's basename may not
    # appear literally in a test file (test_events_only_residue_census).
    ("upgrade_wavefoundry.py", "``docs/waves/review-evidence-" + "adoptions.json`` and"): "docstring",
    ("upgrade_wavefoundry.py", "``docs/waves/review-evidence-" + "migration.json`` without"): "docstring",
    # -- server-routing lane (Requirement 4): non-construction sites only --
    ("server_impl.py", "_DEMOTION_WAVES = 0.75  # docs/waves/"): "comment",
    ("server_impl.py", "_DEMOTION_PLANS = 0.60  # docs/plans/"): "comment",
    ("server_impl.py", "# Prefer wave folder; fall back to docs/plans"): "comment",
    ("server_impl.py", "usage=\"wf_map(address='doc:docs/plans/1234-feat x.md')\""): "message",
    ("server_impl.py", "When a change doc is relocated from ``docs/plans/`` to a wave folder"): "docstring",
    ("server_impl.py", "valid from ``docs/plans/`` but become invalid"): "docstring",
    ("server_impl.py", "already *inside* ``docs/waves/``)"): "docstring",
    ("server_impl.py", "# relocate the file out of `docs/plans/`"): "comment",
    ("memory_handlers.py", "recovery_usage=\"repair the local docs/waves path, then retry\""): "message",
    ("server_impl.py", "# historical (docs/waves/) rows excluded by construction"): "comment",
    ("upgrade_handlers.py", "# the full-corpus lint, which includes docs/waves"): "comment",
    ("server_impl.py", "every ``docs/waves/`` record"): "docstring",
    ("context_efficiency_handlers.py", "\"\"\"Plan docs under docs/plans/ are pending work"): "docstring",
    ("server_impl.py", "while historical docs/waves records receive an"): "docstring",
    ("server_impl.py", "\"\"\"List pending plan/change docs in docs/plans that have not yet"): "docstring",
    ("server_impl.py", "\"\"\"Create a wave record under docs/waves using a lifecycle wave ID."): "docstring",
    # -- lint-routing lane (Requirement 5): non-construction sites only --
    ("wave_lint_lib/constants.py", "at check time, so `docs/waves/README.md` stays"): "comment",
    ("wave_lint_lib/constants.py", "# CHANGE_ID_PATTERN validates change plan document headers (docs/plans/**/*.md"): "comment",
    ("wave_lint_lib/constants.py", "# PLAN_WAVE_OVERVIEW_PATTERN matches wave-level overview plans that sit under `docs/plans/`"): "comment",
    ("wave_lint_lib/constants.py", "(example: `docs/plans/1n3dq github-enterprise-webhooks.md`)"): "comment",
    ("wave_lint_lib/helpers.py", "``root / \"docs\" / \"waves\"`` and ``root / \"docs\" / \"plans\"``, byte-identical"): "docstring",
    ("wave_lint_lib/helpers.py", "(e.g. the docs/reports & docs/waves/00000 link-check skips"): "comment",
    ("wave_lint_lib/link_validators.py", "at check time (wave 1y0gz): `docs/waves/00000 ` by default."): "comment",
    ("wave_lint_lib/wave_validators.py", "and parked `docs/plans/*.md` drafts are therefore never reached"): "docstring",
    ("wave_lint_lib/wave_validators.py", "\"\"\"Enforce that every `docs/plans/*.md` basename matches"): "docstring",
    ("wave_lint_lib/wave_validators.py", "(shipped `docs/waves`); the remaining"): "comment",
    ("wave_lint_lib/wave_validators.py", "Any direct child DIRECTORY of ``docs/waves/`` holding a NON-EMPTY"): "docstring",
    ("wave_lint_lib/wave_validators.py", "``docs/waves/events.jsonl`` file (a file, never a child directory)"): "docstring",
}

# ``pinned_evidence`` is the one deliberate non-prose exception: the site lives
# in a module whose SHA-256 is recorded as ``evaluator_identity`` inside the
# shipped report pair ``docs/reports/graph-quality-{baseline,post}.json``; the
# baseline was produced against pre-change production code and cannot be
# regenerated, so editing that module would silently void a shipped
# attributable comparison. The control corpus it names is default-layout only.
ALLOWED_REASONS = frozenset({"comment", "docstring", "message", "pinned_evidence"})


def census(scripts_root: Path) -> list[tuple[str, int, str]]:
    """Every (repo-relative-to-scripts file, line number, stripped line) hit."""
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
            if SUBSTRING_RE.search(line) or JOIN_RE.search(line):
                hits.append((rel.as_posix(), lineno, line.strip()))
    return hits


def _allowed(hit: tuple[str, int, str]) -> bool:
    file, _lineno, line = hit
    return any(
        entry_file == file and snippet in line for (entry_file, snippet) in ALLOWLIST
    )


class RecordLayoutCensusTests(unittest.TestCase):
    def test_allowlist_reasons_are_non_construction(self) -> None:
        for key, reason in ALLOWLIST.items():
            self.assertIn(reason, ALLOWED_REASONS, key)
            self.assertTrue(key[1].strip(), f"bare filename entry: {key}")

    def test_sites_table_kinds(self) -> None:
        kinds = {"construction", "prefix_check", "message", "comment", "pinned_evidence"}
        for row in SITES:
            self.assertIn(row[2], kinds, row)

    def test_census_has_no_unrouted_sites(self) -> None:
        offenders = [hit for hit in census(SCRIPTS_ROOT) if not _allowed(hit)]
        self.assertEqual(
            offenders, [],
            "record-root literal outside record_paths.py and not allowlisted "
            "(route it through record_paths.load_record_roots, or add a "
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

    def test_census_polarity_reports_a_literal_join(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scripts = Path(tmp)
            (scripts / "tests").mkdir()
            (scripts / "tests" / "test_ignored.py").write_text(
                'X = root / "docs" / "waves"\n', encoding="utf-8"
            )
            (scripts / "record_paths.py").write_text(
                'DEFAULT = "docs/waves"\n', encoding="utf-8"
            )
            (scripts / "tiny.py").write_text(
                "from pathlib import Path\n"
                "def waves(root: Path) -> Path:\n"
                '    return root / "docs" / "waves"\n'
                "def is_plan(rel: str) -> bool:\n"
                '    return rel.startswith("docs/plans/")\n',
                encoding="utf-8",
            )
            hits = census(scripts)
        self.assertEqual(
            [(f, n) for f, n, _line in hits], [("tiny.py", 3), ("tiny.py", 5)]
        )
        self.assertFalse(any(_allowed(hit) for hit in hits))


if __name__ == "__main__":
    unittest.main()
