"""Tests for the shipped upgrade-time retired-surface reconciliation scan (wave 1p8et).

Covers: the structured result shape, the single retired→new map (incl. the `mcp-server`
no-replacement case), the baked-in exclusion set (each excluded path NOT flagged), and the
anti-duplication guard (no second hand-authored copy of the map).
"""
from __future__ import annotations

import dataclasses
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
from framework_files import framework_source_files, source_path  # wf_server-aware source locations (wave 1yzd0)
REPO_ROOT = SCRIPTS_ROOT.parents[2]  # scripts -> framework -> .wavefoundry -> repo root
RENDER_PATH = SCRIPTS_ROOT / "render_platform_surfaces.py"
RECONCILE_PATH = SCRIPTS_ROOT / "reconcile_scan.py"
BUILD_PACK_PATH = SCRIPTS_ROOT / "build_pack.py"
SEED_160 = REPO_ROOT / ".wavefoundry" / "framework" / "seeds" / "160-upgrade-wavefoundry.prompt.md"
RENDERED_PROMPT = REPO_ROOT / "docs" / "prompts" / "upgrade-wavefoundry.prompt.md"

# Matches the seed/prompt reconciliation-example arrows: `<name>`→`wf <form>` (backtick name,
# the → arrow, backtick replacement).
_ARROW_RE = re.compile(r"`([a-z0-9-]+)`→`(wf [a-z0-9 -]+)`")


def _load(name: str, path: Path):
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class RetiredSurfaceMapTests(unittest.TestCase):
    """AC-1: one map, co-located with `_RETIRED_BIN_WRAPPERS`, covers renames + the no-replacement case."""

    def setUp(self):
        self.render = _load("render_platform_surfaces", RENDER_PATH)

    def test_map_keys_match_retired_bin_wrappers(self):
        # The map is co-located with — and keyed identically to — the renderer's deletion list.
        self.assertEqual(
            set(self.render._RETIRED_SURFACE_REPLACEMENTS),
            set(self.render._RETIRED_BIN_WRAPPERS),
        )

    def test_renames_are_one_to_one_wf_subcommands(self):
        m = self.render._RETIRED_SURFACE_REPLACEMENTS
        self.assertEqual(m["docs-lint"], "wf docs-lint")
        self.assertEqual(m["docs-gardener"], "wf docs-gardener")
        self.assertEqual(m["wave-gate"], "wf gate")
        self.assertEqual(m["update-indexes"], "wf update-indexes")
        self.assertEqual(m["lifecycle-id"], "wf lifecycle-id")
        self.assertEqual(m["wave-dashboard"], "wf dashboard")
        self.assertEqual(m["upgrade-wavefoundry"], "wf upgrade")
        self.assertEqual(m["setup-wavefoundry"], "wf setup")

    def test_mcp_server_has_no_replacement(self):
        # `mcp-server` has NO `wf` form — the value must be None and the suggestion must say
        # remove/rewrite + point at python3 server.py, never a (wrong) `wf mcp-server` form.
        self.assertIsNone(self.render._RETIRED_SURFACE_REPLACEMENTS["mcp-server"])
        suggestion = self.render.retired_surface_suggestion("mcp-server")
        self.assertIn("remove/rewrite", suggestion)
        self.assertIn("server.py", suggestion)
        self.assertNotIn("wf mcp-server", suggestion)
        self.assertNotIn("wf ", suggestion)

    def test_suggestion_for_rename(self):
        self.assertEqual(self.render.retired_surface_suggestion("wave-gate"), "wf gate")


class AntiDuplicationTests(unittest.TestCase):
    """AC-1: there must be no SECOND hand-authored retired→new mapping table."""

    def test_no_second_replacement_map_definition(self):
        # Only render_platform_surfaces.py may DEFINE `_RETIRED_SURFACE_REPLACEMENTS = {...}`.
        # reconcile_scan.py and upgrade_wavefoundry.py must IMPORT it, never re-author it.
        define_re = re.compile(r"^_RETIRED_SURFACE_REPLACEMENTS\s*[:=]", re.MULTILINE)
        definers = []
        for path in framework_source_files():
            text = path.read_text(encoding="utf-8")
            # An IMPORT line (`from ... import _RETIRED_SURFACE_REPLACEMENTS`) is not a definition.
            for m in define_re.finditer(text):
                # Skip if the match is actually inside an import (no `=`/`:` reassignment at col 0
                # in an import — the regex already anchors to a top-level `name =`/`name :`).
                definers.append(path.name)
        self.assertEqual(
            definers,
            ["render_platform_surfaces.py"],
            "the retired→new map must be defined in exactly one place "
            "(render_platform_surfaces.py); found: " + ", ".join(definers),
        )

    def test_reconcile_scan_imports_the_map(self):
        text = RECONCILE_PATH.read_text(encoding="utf-8")
        self.assertIn("from render_platform_surfaces import", text)
        self.assertIn("_RETIRED_SURFACE_REPLACEMENTS", text)


class SeedExampleParityTests(unittest.TestCase):
    """TA-4: seed-160's reconciliation example re-authors map values in prose; pin them to the one map,
    and pin the rendered prompt's example to the seed's."""

    def setUp(self):
        self.render = _load("render_platform_surfaces", RENDER_PATH)
        self.assertTrue(SEED_160.is_file(), f"missing seed: {SEED_160}")
        self.assertTrue(RENDERED_PROMPT.is_file(), f"missing prompt: {RENDERED_PROMPT}")
        self.seed_text = SEED_160.read_text(encoding="utf-8")
        self.prompt_text = RENDERED_PROMPT.read_text(encoding="utf-8")

    def test_seed_example_arrows_match_the_one_map(self):
        arrows = _ARROW_RE.findall(self.seed_text)
        self.assertTrue(arrows, "no `name`→`wf form` arrows found in seed-160 — example missing")
        for name, form in arrows:
            with self.subTest(name=name):
                self.assertEqual(
                    self.render.retired_surface_suggestion(name), form,
                    f"seed-160 example `{name}`→`{form}` disagrees with the one map",
                )

    def test_prompt_example_arrows_match_the_one_map(self):
        arrows = _ARROW_RE.findall(self.prompt_text)
        self.assertTrue(arrows, "no `name`→`wf form` arrows found in the rendered prompt")
        for name, form in arrows:
            with self.subTest(name=name):
                self.assertEqual(self.render.retired_surface_suggestion(name), form)

    def test_rendered_prompt_example_matches_seed(self):
        # Parallel-maintained surfaces: the rendered prompt's arrow example must carry the SAME
        # name→form pairs the seed does (set equality), so they cannot drift.
        self.assertEqual(set(_ARROW_RE.findall(self.seed_text)),
                         set(_ARROW_RE.findall(self.prompt_text)))


class ScanResultShapeTests(unittest.TestCase):
    """AC-2: structured result shape (file, line, retired_surface, matched, suggested)."""

    def setUp(self):
        self.scan = _load("reconcile_scan", RECONCILE_PATH)

    def test_finds_literal_reference_with_full_shape(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            doc = root / "guide.md"
            doc.write_text(
                "Line one.\n"
                "Run `.wavefoundry/bin/docs-lint` here.\n",
                encoding="utf-8",
            )
            findings = self.scan.scan_repo(root)
            self.assertEqual(len(findings), 1)
            f = findings[0]
            self.assertEqual(f.file, "guide.md")
            self.assertEqual(f.line, 2)
            self.assertEqual(f.retired_surface, "docs-lint")
            self.assertEqual(f.matched, ".wavefoundry/bin/docs-lint")
            self.assertEqual(f.suggested, "wf docs-lint")
            self.assertEqual(
                f.as_dict(),
                {"file": "guide.md", "line": 2, "retired_surface": "docs-lint",
                 "matched": ".wavefoundry/bin/docs-lint", "suggested": "wf docs-lint",
                 "disposition_key": self.scan.disposition_key(f),
                 "disposition_key_version": "v2",
                 "legacy_disposition_key": self.scan.legacy_disposition_key(f),
                 "disposition_state": "unrecorded",
                 "logical_line": "Run `.wavefoundry/bin/docs-lint` here.",
                 "heading_context": "",
                 "proposed_v2_key": None},
            )

    def test_mcp_server_reference_suggests_remove_rewrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "x.md").write_text("`.wavefoundry/bin/mcp-server`\n", encoding="utf-8")
            findings = self.scan.scan_repo(root)
            self.assertEqual(len(findings), 1)
            self.assertIn("remove/rewrite", findings[0].suggested)
            self.assertIn("server.py", findings[0].suggested)

    def test_dynamic_and_variable_bin_join_in_py(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "s.py").write_text(
                'a = REPO / ".wavefoundry" / "bin" / "docs-lint"\n'
                'b = bin_dir / "wave-gate"\n',
                encoding="utf-8",
            )
            findings = self.scan.scan_repo(root)
            kinds = {f.retired_surface for f in findings}
            self.assertIn("docs-lint", kinds)
            self.assertIn("wave-gate", kinds)

    def test_matched_field_carries_join_text_not_assumed_bin_path(self):
        # INV-recline: the .py-join finding's `matched` must be the actual join text, NOT a
        # synthesized `.wavefoundry/bin/<name>` form (which would be wrong for these).
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "s.py").write_text('b = bin_dir / "wave-gate"\n', encoding="utf-8")
            findings = self.scan.scan_repo(root)
            self.assertEqual(len(findings), 1)
            f = findings[0]
            self.assertEqual(f.retired_surface, "wave-gate")
            self.assertIn('"wave-gate"', f.matched)
            self.assertNotEqual(f.matched, ".wavefoundry/bin/wave-gate")

    def test_windows_backslash_and_mixed_separator_flagged(self):
        # SCAN-1: backslash and mixed-separator bin refs (Windows consumer docs) must be caught.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "win.md").write_text(
                "Backslash: `.wavefoundry\\bin\\docs-lint`\n"
                "Mixed: `.wavefoundry/bin\\wave-gate`\n",
                encoding="utf-8",
            )
            findings = self.scan.scan_repo(root)
            by_surface = {f.retired_surface: f for f in findings}
            self.assertIn("docs-lint", by_surface)
            self.assertEqual(by_surface["docs-lint"].suggested, "wf docs-lint")
            self.assertIn(".wavefoundry\\bin\\docs-lint", by_surface["docs-lint"].matched)
            self.assertIn("wave-gate", by_surface)
            self.assertEqual(by_surface["wave-gate"].suggested, "wf gate")

    def test_negative_controls_yield_zero_findings(self):
        # TA-6: `bin_dir / "wf"` (wf not retired) and `.wavefoundry/bin/docs-lint-extra`
        # (word-boundary) must NOT be flagged.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "ok.py").write_text('p = bin_dir / "wf"\n', encoding="utf-8")
            (root / "ok.md").write_text("`.wavefoundry/bin/docs-lint-extra` is fine\n", encoding="utf-8")
            self.assertEqual(self.scan.scan_repo(root), [])


class RetiredPlanReviewIdentityTests(unittest.TestCase):
    """1w047 AC-5: retired skill/path forms report; phrase aliases and history do not."""

    def setUp(self):
        self.scan = _load("reconcile_scan", RECONCILE_PATH)

    def test_exact_skill_prompt_and_seed_references_are_repairable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "guide.md").write_text(
                "Use `/wf-interrogate-plan`.\n"
                "Read `docs/prompts/interrogate-plan.prompt.md`.\n"
                "Merge `docs/prompts/agents/interrogate-plan.prompt.md` manually.\n"
                "Source: `.wavefoundry/framework/seeds/175-interrogate-plan.prompt.md`.\n",
                encoding="utf-8",
            )

            findings = self.scan.scan_repo(root)

        self.assertEqual(
            [(f.line, f.retired_surface, f.suggested) for f in findings],
            [
                (1, "wf-interrogate-plan", "wf-review-plan"),
                (
                    2,
                    "docs/prompts/interrogate-plan.prompt.md",
                    "docs/prompts/review-plan.prompt.md",
                ),
                (
                    3,
                    "docs/prompts/agents/interrogate-plan.prompt.md",
                    "merge unique guidance into docs/prompts/review-plan.prompt.md, then remove the obsolete agents prompt",
                ),
                (
                    4,
                    "175-interrogate-plan.prompt.md",
                    ".wavefoundry/framework/seeds/175-review-plan.prompt.md",
                ),
            ],
        )

    def test_seed_basename_reference_is_also_repairable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "guide.md").write_text(
                "See `175-interrogate-plan.prompt.md`.\n", encoding="utf-8"
            )
            findings = self.scan.scan_repo(root)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].matched, "175-interrogate-plan.prompt.md")
        self.assertEqual(
            findings[0].suggested,
            ".wavefoundry/framework/seeds/175-review-plan.prompt.md",
        )

    def test_legacy_agents_prompt_is_reported_by_file_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            legacy = root / "docs/prompts/agents/interrogate-plan.prompt.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text(
                "# Project-specific plan review\n\n"
                "Keep this unique operator guidance during the rename.\n",
                encoding="utf-8",
            )

            findings = self.scan.scan_repo(root)

        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.file, "docs/prompts/agents/interrogate-plan.prompt.md")
        self.assertEqual(finding.line, 1)
        self.assertEqual(
            finding.retired_surface,
            "docs/prompts/agents/interrogate-plan.prompt.md",
        )
        self.assertEqual(finding.matched, finding.retired_surface)
        self.assertEqual(
            finding.suggested,
            "merge unique guidance into docs/prompts/review-plan.prompt.md, then remove the obsolete agents prompt",
        )

    def test_supported_phrase_aliases_are_not_retired(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "guide.md").write_text(
                "Use **Interrogate this plan** or **Stress-test this plan**.\n",
                encoding="utf-8",
            )
            self.assertEqual(self.scan.scan_repo(root), [])

    def test_longer_skill_near_misses_are_not_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "guide.md").write_text(
                "`my-wf-interrogate-plan` and `wf-interrogate-plan-extra`\n"
                "`mydocs/prompts/interrogate-plan.prompt.md` and "
                "`docs/prompts/interrogate-plan.prompt.md.bak`\n"
                "`mydocs/prompts/agents/interrogate-plan.prompt.md` and "
                "`docs/prompts/agents/interrogate-plan.prompt.md.bak`\n"
                "`x175-interrogate-plan.prompt.md` and "
                "`175-interrogate-plan.prompt.md.old`\n",
                encoding="utf-8",
            )
            self.assertEqual(self.scan.scan_repo(root), [])

    def test_declared_history_and_frozen_benchmarks_are_excluded(self):
        excluded = (
            "docs/waves/1p6lp/history.md",
            "docs/waves/1w047 review-plan-naming/change.md",
            "CHANGELOG.md",
            ".wavefoundry/framework/scripts/benchmarks/model_swap_docs_queries.json",
            ".wavefoundry/framework/scripts/benchmarks/model_swap_v2_result.json",
        )
        body = (
            "`wf-interrogate-plan`\n"
            "`docs/prompts/interrogate-plan.prompt.md`\n"
            "`175-interrogate-plan.prompt.md`\n"
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel in excluded:
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
            self.assertEqual(self.scan.scan_repo(root), [])


class ExclusionTests(unittest.TestCase):
    """AC-4: the baked-in exclusion set is enforced — each excluded path is NOT flagged."""

    def setUp(self):
        self.scan = _load("reconcile_scan", RECONCILE_PATH)

    def _write(self, root: Path, rel: str) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("Run `.wavefoundry/bin/docs-lint` here.\n", encoding="utf-8")

    def test_each_excluded_path_is_not_flagged(self):
        excluded = [
            ".wavefoundry/framework/seeds/160-x.md",   # framework pack tree (prefix)
            ".wavefoundry/framework.rollback-bridge-pfps-p2/docs/legacy.md",  # inactive bridge backup
            ".wavefoundry/upgrade-assets/feature.zip.md",  # retained generated upgrade payload
            ".wavefoundry/index/notes.md",             # generated index (prefix)
            "docs/waves/1p8ev/x.md",                   # wave history (prefix)
            "docs/reports/field-report.md",            # report history (prefix)
            "CHANGELOG.md",                            # release history (repo-root file)
            "docs/agents/journals/role-journal.md",    # under journals/ component
            "docs/snapshots/2026-state.md",            # under snapshots/ component
            ".wavefoundry/framework/scripts/tests/test_x.py",  # test file (framework tree)
            # TA-2: a NON-framework test file must also be excluded (not vacuously via the tree).
            "src/tests/test_thing.py",
        ]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel in excluded:
                self._write(root, rel)
            # One in-scope file to prove the scan itself works.
            self._write(root, "docs/runbook.md")
            findings = self.scan.scan_repo(root)
            flagged = {f.file for f in findings}
            self.assertEqual(
                flagged,
                {"docs/runbook.md"},
                "only the in-scope file should be flagged; excluded paths leaked: "
                + ", ".join(sorted(flagged - {"docs/runbook.md"})),
            )

    def test_near_miss_paths_stay_in_scope(self):
        # SCAN-2: substring matching over-excluded these in-scope operator docs. They MUST be flagged.
        near_miss = [
            "docs/reports-overview.md",   # NOT under docs/reports/
            "src/snapshotter.py",         # substring `snapshot` but no snapshots/ component
            ".wavefoundry/framework.rollback-notes.md",  # file, not a generated rollback directory
            "docs/framework.rollback-p2/guide.md",        # similarly named project directory
        ]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel in near_miss:
                self._write(root, rel)
            findings = self.scan.scan_repo(root)
            flagged = {f.file for f in findings}
            self.assertEqual(
                flagged,
                set(near_miss),
                "near-miss in-scope docs were wrongly excluded: "
                + ", ".join(sorted(set(near_miss) - flagged)),
            )

    def test_changelog_excluded_by_basename_anywhere(self):
        # 1p8o5 #1: CHANGELOG.md is release history wherever it lives — a nested
        # `.wavefoundry/CHANGELOG.md` (or any path) must NOT be flagged, but a real in-scope doc must.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "CHANGELOG.md")                 # repo-root changelog
            self._write(root, ".wavefoundry/CHANGELOG.md")    # nested changelog (the field FP)
            self._write(root, "docs/x/CHANGELOG.md")          # deeper nested changelog
            self._write(root, "docs/guide.md")                # real in-scope operator doc
            findings = self.scan.scan_repo(root)
            self.assertEqual(
                {f.file for f in findings},
                {"docs/guide.md"},
                "only the real in-scope doc should be flagged; CHANGELOG.md must be excluded by basename",
            )

    def test_prompt_surface_manifest_excluded(self):
        # 1p8o5 #1: the renderer-managed prompt-surface-manifest.json (historical upgrade_merge_notes)
        # is a generated manifest — never flag it, but still flag a real in-scope config.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs" / "prompts").mkdir(parents=True)
            (root / "docs" / "prompts" / "prompt-surface-manifest.json").write_text(
                '{"upgrade_merge_notes": "see .wavefoundry/bin/docs-lint history"}\n',
                encoding="utf-8",
            )
            self._write(root, "docs/config.json")  # a real in-scope config referencing the wrapper
            findings = self.scan.scan_repo(root)
            self.assertEqual(
                {f.file for f in findings},
                {"docs/config.json"},
                "prompt-surface-manifest.json must be excluded; a real in-scope config still flagged",
            )

    def test_non_test_file_under_tests_dir_stays_in_scope(self):
        # TA-2 negative control: a non-`test_` file under tests/ is in scope (only `test_*` is excluded).
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "src/tests/helper.py")
            findings = self.scan.scan_repo(root)
            self.assertEqual({f.file for f in findings}, {"src/tests/helper.py"})

    def test_unscannable_suffix_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "image.png").write_bytes(b".wavefoundry/bin/docs-lint")
            self.assertEqual(self.scan.scan_repo(root), [])


class ArchiveSectionExclusionTests(unittest.TestCase):
    """Wave 1vk4c (1vk4b): table rows under seed-230's `## Resolved / closed` heading in
    `docs/missing-docs.md` are historical record, so the scan does not report them; every
    other shape and location keeps reporting (fail toward reporting, memory 1u43m)."""

    ARCHIVE = "docs/missing-docs.md"
    # every producer family in one row: retired content path, literal bin wrapper path,
    # renamed MCP tool (bare + qualified), stale prompt extension (resolves against the tree)
    ROW = (
        "| 2026-04-06 | docs/agents/journals/ created at init; retired, see docs/agents/memory/ | "
        "ran `.wavefoundry/bin/docs-lint`; used `wave_close` and `mcp__wavefoundry__wave_audit`; "
        "see docs/prompts/plan-feature.md | Historical record only |"
    )

    def setUp(self):
        self.scan = _load("reconcile_scan", RECONCILE_PATH)

    def _root(self, td: str, missing_docs: str) -> Path:
        root = Path(td)
        (root / "docs" / "prompts").mkdir(parents=True)
        # makes the stale `.md` prompt reference resolvable, so that producer fires
        (root / "docs" / "prompts" / "plan-feature.prompt.md").write_text("# p\n", encoding="utf-8")
        (root / self.ARCHIVE).write_text(missing_docs, encoding="utf-8")
        return root

    def _findings(self, root: Path) -> list:
        return [f for f in self.scan.scan_repo(root) if f.file == self.ARCHIVE]

    def test_archive_rows_are_silent_for_every_producer(self):
        # AC-1: the seed-230 shape (heading, then a table) with a row naming every
        # retired-surface family reports nothing.
        text = "# Missing docs\n\n## Resolved / closed\n\n| Date | Item | Note | Status |\n| --- | --- | --- | --- |\n" + self.ROW + "\n"
        with tempfile.TemporaryDirectory() as td:
            root = self._root(td, text)
            live = [f for f in self.scan.scan_repo(root) if f.file != self.ARCHIVE]
            self.assertEqual(self._findings(root), [])
            self.assertEqual(live, [], "the fixture must not leak findings elsewhere")

    def test_same_strings_outside_the_archive_still_report(self):
        # AC-2: priority table, prose under the archive heading, another heading.
        text = (
            "# Missing docs\n\n## High\n\n| Date | Item | Note | Status |\n| --- | --- | --- | --- |\n" + self.ROW + "\n\n"
            "## Resolved / closed\n\n| Date | Item | Note | Status |\n| --- | --- | --- | --- |\n" + self.ROW + "\n"
            "Prose parked under the archive heading still names docs/agents/journals/ and .wavefoundry/bin/docs-lint.\n\n"
            "## Watchpoints\n\n" + self.ROW + "\n"
        )
        with tempfile.TemporaryDirectory() as td:
            root = self._root(td, text)
            lines = sorted({f.line for f in self._findings(root)})
        expected_lines = [7, 14, 18]  # High row (7), prose under the archive heading (14), Watchpoints row (18); the archive row on line 13 is silent
        self.assertEqual(lines, expected_lines)
        # and each family reports on the High row
        with tempfile.TemporaryDirectory() as td:
            root = self._root(td, text)
            surfaces = {f.retired_surface for f in self._findings(root) if f.line == 7}
        self.assertEqual(surfaces, {"docs/agents/journals", "docs-lint", "wave_close", "wave_audit", "prompt .md extension"})

    def test_field_reproduction_reports_only_the_priority_table_row(self):
        # The Aceiss field shape: one archive row plus the same path in a priority table.
        text = (
            "# Missing docs\n\n## High\n\n| Item | Note |\n| --- | --- |\n| docs/agents/journals/ | still open |\n\n"
            "## Resolved / closed\n\n| Date | Item | Note |\n| --- | --- | --- |\n"
            "| 2026-04-06 | docs/agents/journals/ | Historical record only; the journal system has since been retired; durable lessons are captured as typed memory records under docs/agents/memory/ |\n"
        )
        with tempfile.TemporaryDirectory() as td:
            root = self._root(td, text)
            found = self._findings(root)
        self.assertEqual([(f.line, f.retired_surface) for f in found], [(7, "docs/agents/journals")])

    def test_legacy_disposition_never_suppresses_the_live_hit(self):
        # 1w3bq AC-3: preserved v1 keys are diagnostic-only. A historical
        # judgment over the broad file/surface/matched tuple cannot suppress a
        # current candidate, even when exactly one candidate remains.
        text = (
            "# Missing docs\n\n## High\n\n| Item | Note |\n| --- | --- |\n| docs/agents/journals/ | still open |\n\n"
            "## Resolved / closed\n\n| Date | Item |\n| --- | --- |\n| 2026-04-06 | docs/agents/journals/ retired |\n"
        )
        with tempfile.TemporaryDirectory() as td:
            root = self._root(td, text)
            [live] = self._findings(root)
            key = self.scan.legacy_disposition_key(live)
            store = root / self.scan.DISPOSITIONS_REL
            store.write_text(json.dumps([{"key": key, "status": self.scan.HISTORICAL_RECORD}]), encoding="utf-8")
            reconciliation, _, _ = self.scan.scan_repo_channels(root)
            [reported] = [f for f in reconciliation if f.file == self.ARCHIVE]
            self.assertEqual(reported.disposition_state, "legacy-reclassification-required")
            self.assertEqual(reported.as_dict()["proposed_v2_key"], self.scan.disposition_key(reported))
            store.unlink()
            reconciliation, _, _ = self.scan.scan_repo_channels(root)
            self.assertEqual([f.line for f in reconciliation if f.file == self.ARCHIVE], [7])
            store.write_text("not json", encoding="utf-8")
            self.assertEqual(self.scan.load_dispositions(root), {}, "fail-open on a corrupt store")
            reconciliation, _, _ = self.scan.scan_repo_channels(root)
            self.assertEqual([f.line for f in reconciliation if f.file == self.ARCHIVE], [7], "corrupt store suppresses nothing")

    def test_no_other_document_or_shape_gains_suppression(self):
        # AC-4: identical heading in another file, H3, renamed heading, setext, no-space
        # `##`, fenced heading, and non-Markdown files all keep reporting; H1 ends the span.
        row = "| 2026-04-06 | docs/agents/journals/ retired |"
        cases = {
            "docs/other.md": "## Resolved / closed\n\n" + row + "\n",
            "docs/missing-docs.md": (
                "### Resolved / closed\n\n" + row + "\n"          # H3, line 3
                "## Resolved and closed\n\n" + row + "\n"          # renamed, line 6
                "Resolved / closed\n-----------------\n" + row + "\n"  # setext, line 9
                "##Resolved / closed\n\n" + row + "\n"             # no space, line 12
                "```\n## Resolved / closed\n```\n" + row + "\n"     # fenced, line 16
                "## Resolved / closed\n\n# Top-level again\n\n" + row + "\n"  # H1 ends span, line 21
                "## Resolved / closed (2026 archive)\n\n" + row + "\n"   # exact text only, not substring, line 24
                "```\n~~~\n## Resolved / closed\n```\n" + row + "\n"     # ~~~ inside a ``` fence is content; heading stays fenced, line 29
                "````\n```\n## Resolved / closed\n````\n" + row + "\n"   # ``` inside a ```` fence does not close it, line 34
                "## Resolved / closed\n##\n" + row + "\n"                 # an empty ATX heading terminates the span, line 37
            ),
            "notes/archive.py": "# ## Resolved / closed\nX = 'docs/agents/journals/'\n",
            "config/archive.json": '{"heading": "## Resolved / closed", "path": "docs/agents/journals/"}\n',
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel, body in cases.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")
            by_file = {}
            for f in self.scan.scan_repo(root):
                by_file.setdefault(f.file, []).append(f.line)
        self.assertEqual(by_file.get("docs/other.md"), [3])
        self.assertEqual(sorted(by_file.get("docs/missing-docs.md", [])), [3, 6, 9, 12, 16, 21, 24, 29, 34, 37])
        self.assertEqual(by_file.get("notes/archive.py"), [2])
        self.assertEqual(by_file.get("config/archive.json"), [1])

    def test_archive_span_helper_contract(self):
        # CRLF, closing hashes, nested H3 inside the span, other-file short-circuit.
        text = "## Resolved / closed ##\r\n\r\n| a | docs/agents/journals/ |\r\n### nested\r\n| b | x |\r\n  | c | indented row |\r\nplain\r\n"
        spans = self.scan._archive_row_spans(text, "docs/missing-docs.md")
        self.assertEqual([text[s:e] for s, e in spans], ["| a | docs/agents/journals/ |", "| b | x |", "  | c | indented row |"])
        # fence bookkeeping: a shorter or other-character run inside an open fence is content
        fenced = "````\n```\n## Resolved / closed\n| a | x |\n````\n| b | y |\n"
        self.assertEqual(self.scan._archive_row_spans(fenced, "docs/missing-docs.md"), [])
        mixed = "```\n~~~\n## Resolved / closed\n```\n| a | x |\n"
        self.assertEqual(self.scan._archive_row_spans(mixed, "docs/missing-docs.md"), [])
        self.assertEqual(self.scan._archive_row_spans(text, "docs/other.md"), [])
        self.assertEqual(self.scan._archive_row_spans("no headings at all\n| row |\n", "docs/missing-docs.md"), [])
        self.assertEqual(self.scan._ARCHIVE_SECTIONS, (("docs/missing-docs.md", "resolved / closed"),))


class HostPermissionChannelTests(unittest.TestCase):
    """1p8o5 #2 / AC-2: host permission/allow-rule files go to a SEPARATE channel, not the editable
    `reconciliation` list — an agent cannot self-edit them under host auto-mode guards."""

    def setUp(self):
        self.scan = _load("reconcile_scan", RECONCILE_PATH)

    def _write(self, root: Path, rel: str) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("Run `.wavefoundry/bin/docs-lint` here.\n", encoding="utf-8")

    def test_settings_local_absent_from_reconciliation_present_in_host_channel(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, ".claude/settings.local.json")  # host permission/allow-rule file
            self._write(root, "docs/runbook.md")              # editable repo doc
            reconciliation, host_perm, _prov = self.scan.scan_repo_channels(root)
            recon_files = {f.file for f in reconciliation}
            host_files = {f.file for f in host_perm}
            self.assertNotIn(
                ".claude/settings.local.json", recon_files,
                "allow-rule file must NOT be in the editable reconciliation list",
            )
            self.assertIn(".claude/settings.local.json", host_files,
                          "allow-rule file must be in the separate host-permission channel")
            self.assertIn("docs/runbook.md", recon_files,
                          "editable repo doc stays in the reconciliation list")
            self.assertNotIn("docs/runbook.md", host_files)

    def test_host_permission_flag_on_stale_reference(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, ".claude/settings.json")  # also a host permission file
            findings = self.scan.scan_repo(root)
            self.assertEqual(len(findings), 1)
            self.assertTrue(findings[0].host_permission)
            self.assertTrue(self.scan.is_host_permission_file(".claude/settings.json"))
            self.assertFalse(self.scan.is_host_permission_file("docs/runbook.md"))

    def test_scan_repo_returns_both_channels_combined(self):
        # scan_repo() (the self-host guard's entrypoint) still returns ALL findings (both channels), so
        # the guard catching a retired ref anywhere — incl. a host file — keeps working.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, ".claude/settings.local.json")
            self._write(root, "docs/runbook.md")
            all_files = {f.file for f in self.scan.scan_repo(root)}
            self.assertEqual(all_files, {".claude/settings.local.json", "docs/runbook.md"})


class ShipsInPackTests(unittest.TestCase):
    """AC-2: the helper ships — it is not excluded by build_pack's real ship gate."""

    def test_reconcile_scan_not_excluded_from_pack(self):
        bp = _load("build_pack", BUILD_PACK_PATH)
        excluded = bp.EXCLUDED_REL_PATHS
        self.assertNotIn("scripts/reconcile_scan.py", excluded)
        self.assertNotIn("scripts/reconcile_scan", excluded)
        # TA-5: assert the REAL ship gate, not just membership — should_exclude must return False.
        self.assertFalse(
            bp.should_exclude("scripts/reconcile_scan.py", "reconcile_scan.py"),
            "reconcile_scan.py must ship in the pack (should_exclude returned True)",
        )
        # And it lives under scripts/ (not scripts/tests/).
        self.assertTrue(RECONCILE_PATH.is_file())
        self.assertNotIn("tests", RECONCILE_PATH.relative_to(SCRIPTS_ROOT).parts)


if __name__ == "__main__":
    unittest.main()


class RenamedMcpToolScanTests(unittest.TestCase):
    """Wave 1t72b (1t6p8): the scan covers the 1.14.0 MCP tool renames."""

    def setUp(self):
        self.render = _load("render_platform_surfaces", RENDER_PATH)
        self.scan = _load("reconcile_scan", RECONCILE_PATH)

    def test_map_is_oracle_anchored_to_the_live_registration_census(self):
        """AC-1 (two directions): every NEW name is a currently registered MCP
        tool; no OLD name is. The census source is server_impl's registration
        AST — the same authority the envelope census test uses — so a
        hand-copied map cannot drift from the shipped surface."""
        import ast as _ast
        registered: set[str] = set()
        # server_impl registers the surface; server.py registers the reload
        # survivor (wf_reload_mcp) in build_server — census both.
        for file_name, fn_name in (
            ("server_impl.py", "register_mcp_surface"),
            ("server.py", "build_server"),
        ):
            source = source_path(file_name).read_text(encoding="utf-8")
            tree = _ast.parse(source)
            for node in _ast.walk(tree):
                if isinstance(node, _ast.FunctionDef) and node.name == fn_name:
                    for inner in _ast.walk(node):
                        if isinstance(
                            inner, (_ast.FunctionDef, _ast.AsyncFunctionDef)
                        ) and any(
                            isinstance(d, _ast.Call) for d in inner.decorator_list
                        ):
                            registered.add(inner.name)
        self.assertGreater(len(registered), 60, "census sanity: the surface is large")
        mapping = self.render._RENAMED_MCP_TOOLS
        missing_new = sorted(v for v in mapping.values() if v not in registered)
        self.assertEqual(missing_new, [],
                         "every NEW name must be a registered tool")
        stale_old = sorted(k for k in mapping if k in registered)
        self.assertEqual(stale_old, [],
                         "no OLD name may still be registered")

    def test_doc_naming_old_tool_is_flagged_with_new_name(self):
        """AC-2: bare form in an editable doc."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "howto.md").write_text(
                "Close the wave with `wave_close(mode='create')`.\n",
                encoding="utf-8",
            )
            reconciliation, host_flags, _prov = self.scan.scan_repo_channels(root)
        self.assertEqual(host_flags, [])
        self.assertEqual(len(reconciliation), 1)
        ref = reconciliation[0]
        self.assertEqual(ref.retired_surface, "wave_close")
        self.assertIn("wf_close_wave", ref.suggested)

    def test_allow_rule_routes_to_host_permission_channel(self):
        """AC-2: fully-qualified form in a host allow-rule file."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            claude = root / ".claude"
            claude.mkdir()
            (claude / "settings.local.json").write_text(
                '{"permissions": {"allow": ["mcp__wavefoundry__wave_validate"]}}\n',
                encoding="utf-8",
            )
            reconciliation, host_flags, prov_flags = self.scan.scan_repo_channels(root)
        self.assertEqual(reconciliation, [])
        self.assertEqual(prov_flags, [], "settings.local.json is NEVER renderer-provenance")
        self.assertEqual(len(host_flags), 1)
        self.assertEqual(host_flags[0].retired_surface, "wave_validate")
        self.assertIn("wf_validate_docs", host_flags[0].suggested)

    def test_config_key_names_bare_form_never_flagged(self):
        """AC-3: wave_review/wave_implement are workflow-config KEYS — a bare
        flag would instruct a config-breaking rename. Only the qualified
        tool-call form flags them."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "workflow-config.json").write_text(
                '{"wave_review": {"lanes": []}, "wave_implement": {}}\n',
                encoding="utf-8",
            )
            (root / "docs" / "note.md").write_text(
                "Run mcp__wavefoundry__wave_review then check wave_implement config.\n",
                encoding="utf-8",
            )
            reconciliation, host_flags, _prov = self.scan.scan_repo_channels(root)
        self.assertEqual(host_flags, [])
        self.assertEqual(
            [(r.file, r.retired_surface, r.matched) for r in reconciliation],
            [("docs/note.md", "wave_review", "mcp__wavefoundry__wave_review")],
            "only the qualified form of a config-key name flags; bare never does",
        )

    def test_longest_name_wins_at_the_sharpest_boundary(self):
        """AC-3: wave_index_build must not match inside wave_index_build_status."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "ops.md").write_text(
                "Poll wave_index_build_status until done.\n", encoding="utf-8"
            )
            reconciliation, _host, _prov = self.scan.scan_repo_channels(root)
        self.assertEqual([r.retired_surface for r in reconciliation],
                         ["wave_index_build_status"])
        self.assertIn("index_build_status", reconciliation[0].suggested)

    def test_history_exclusions_hold_for_tool_renames(self):
        """AC-4: wave archives, journals, memory records, CHANGELOG stay unflagged."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in (
                "docs/waves/1x old/wave.md",
                "docs/agents/journals/session.md",
                "docs/agents/memory/mem-old-decision.md",
                "CHANGELOG.md",
            ):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Used wave_close and mcp__wavefoundry__wave_validate.\n",
                                encoding="utf-8")
            reconciliation, host_flags, prov_flags = self.scan.scan_repo_channels(root)
        self.assertEqual(reconciliation, [])
        self.assertEqual(host_flags, [])
        self.assertEqual(prov_flags, [])

    def test_live_self_repo_scan_is_clean_on_the_editable_channel(self):
        """AC-4 end-to-end oracle: this repository's own editable surfaces carry
        no stale tool names under the extended scan."""
        reconciliation, _host, _prov = self.scan.scan_repo_channels(REPO_ROOT)
        tool_refs = [r for r in reconciliation
                     if r.retired_surface in self.render._RENAMED_MCP_TOOLS]
        self.assertEqual(
            [(r.file, r.line, r.retired_surface) for r in tool_refs], [],
            "self-repo editable surfaces must be clean of old tool names",
        )


class RendererProvenanceChannelTests(unittest.TestCase):
    """Wave 1u2az AC-4: stale allow rules inside the permissions renderer's
    provenance route to a THIRD, self-healing channel; everything outside the
    provenance (and all of settings.local.json) stays operator territory.

    Fragile-file note (reconcile_scan.py, wave 1tz6l x2): every positive here
    carries a near-miss negative control so the channel boundary cannot go
    vacuous: same rule string outside the provenance, same string in a
    different host file, and a corrupt provenance key all stay operator-side.
    """

    def setUp(self):
        self.scan = _load("reconcile_scan", RECONCILE_PATH)

    @staticmethod
    def _settings(root: Path, rel: str, payload: str) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(payload, encoding="utf-8")

    def test_provenance_claimed_stale_rule_routes_to_self_heal_channel(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._settings(
                root,
                ".claude/settings.json",
                '{"permissions": {"allow": ["mcp__wavefoundry__wave_close",\n'
                ' "mcp__wavefoundry__wave_prepare"]},\n'
                ' "wavefoundryManagedAllow": ["mcp__wavefoundry__wave_close"]}\n',
            )
            reconciliation, host_flags, prov_flags = self.scan.scan_repo_channels(root)
        self.assertEqual(reconciliation, [])
        # The claimed stale rule self-heals (both its allow occurrence and its
        # provenance-list occurrence report on the self-heal channel).
        self.assertTrue(prov_flags, "claimed stale rule must reach the provenance channel")
        self.assertEqual(
            {(f.file, f.matched) for f in prov_flags},
            {(".claude/settings.json", "mcp__wavefoundry__wave_close")},
        )
        self.assertTrue(all(f.renderer_provenance for f in prov_flags))
        # NEAR-MISS: the same-file stale rule OUTSIDE the provenance is
        # operator territory, never reclassified by the name prefix.
        self.assertEqual(
            {(f.file, f.matched) for f in host_flags},
            {(".claude/settings.json", "mcp__wavefoundry__wave_prepare")},
            "non-provenance settings.json rules stay in the operator channel",
        )
        self.assertTrue(all(not f.renderer_provenance for f in host_flags))

    def test_settings_local_never_routes_to_provenance_channel(self):
        # NEAR-MISS: the exact rule string IS in settings.json's provenance,
        # but the hit lives in settings.local.json; host-local files are
        # always operator territory.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._settings(
                root,
                ".claude/settings.json",
                '{"wavefoundryManagedAllow": ["mcp__wavefoundry__wave_close"],\n'
                ' "permissions": {"allow": []}}\n',
            )
            self._settings(
                root,
                ".claude/settings.local.json",
                '{"permissions": {"allow": ["mcp__wavefoundry__wave_close"]}}\n',
            )
            _rec, host_flags, prov_flags = self.scan.scan_repo_channels(root)
        local_hits = [f for f in host_flags if f.file == ".claude/settings.local.json"]
        self.assertEqual(len(local_hits), 1)
        self.assertFalse(local_hits[0].renderer_provenance)
        self.assertEqual(
            [f.file for f in prov_flags],
            [".claude/settings.json"],
            "only the committed settings.json provenance occurrence self-heals",
        )

    def test_corrupt_or_absent_provenance_degrades_to_operator_channel(self):
        # Fail-safe: an unreadable provenance key must not silently claim
        # ownership; every hit stays on the operator channel.
        for payload in (
            '{"permissions": {"allow": ["mcp__wavefoundry__wave_close"]},\n'
            ' "wavefoundryManagedAllow": "not-a-list"}\n',
            '{"permissions": {"allow": ["mcp__wavefoundry__wave_close"]}}\n',
        ):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                self._settings(root, ".claude/settings.json", payload)
                _rec, host_flags, prov_flags = self.scan.scan_repo_channels(root)
            self.assertEqual(prov_flags, [], payload)
            self.assertEqual(len(host_flags), 1, payload)

    def test_same_rule_string_in_a_hooks_command_stays_operator_side(self):
        """Wave 1u2b0 F3: the LOCATION near-miss the three original controls never
        varied. The existing controls change the rule or the file; this one keeps
        both identical and moves the hit out of the allow/provenance arrays into a
        hooks COMMAND in the same file. Nothing rewrites a hooks command, so
        routing it to the "no edit needed" self-healing channel would guarantee it
        is never fixed."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._settings(
                root,
                ".claude/settings.json",
                '{"wavefoundryManagedAllow": ["mcp__wavefoundry__wave_close"],\n'
                ' "permissions": {"allow": ["mcp__wavefoundry__wave_close"]},\n'
                ' "hooks": {"PostToolUse": [{"hooks": [{"type": "command",\n'
                '   "command": ".claude/hooks/check.py --tool '
                'mcp__wavefoundry__wave_close"}]}]}}\n',
            )
            _rec, host_flags, prov_flags = self.scan.scan_repo_channels(root)
        # The allow entry and its provenance record self-heal (2 occurrences).
        self.assertEqual(len(prov_flags), 2, [f.matched for f in prov_flags])
        self.assertTrue(all(f.renderer_provenance for f in prov_flags))
        # The hooks-command occurrence is OPERATOR territory.
        self.assertEqual(len(host_flags), 1, [f.matched for f in host_flags])
        self.assertFalse(host_flags[0].renderer_provenance)
        self.assertEqual(host_flags[0].file, ".claude/settings.json")

    def test_bare_retired_token_is_never_claimed_by_a_longer_provenance_rule(self):
        """Wave 1u2b0 F3(b): classification uses EXACT provenance membership, not
        containment. A bare `wave_close` token is a substring of the provenance's
        `mcp__wavefoundry__wave_close`, but it is not a rule the renderer emits or
        prunes — in an allow entry or in a hooks command it stays operator-side."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._settings(
                root,
                ".claude/settings.json",
                '{"wavefoundryManagedAllow": ["mcp__wavefoundry__wave_prepare"],\n'
                ' "permissions": {"allow": ["Bash(wf wave_close)",\n'
                '   "mcp__wavefoundry__wave_prepare"]},\n'
                ' "hooks": {"Stop": [{"hooks": [{"command": "check.py wave_close"}]}]}}\n',
            )
            _rec, host_flags, prov_flags = self.scan.scan_repo_channels(root)
        # Only the exact provenance rule (twice: allow entry + provenance record).
        self.assertEqual(
            {f.matched for f in prov_flags}, {"mcp__wavefoundry__wave_prepare"}
        )
        self.assertEqual(len(prov_flags), 2)
        # Both bare `wave_close` occurrences stay operator-side, including the one
        # INSIDE the allow array (a governed region, but not a governed rule).
        self.assertEqual({f.matched for f in host_flags}, {"wave_close"})
        self.assertEqual(len(host_flags), 2)

    def test_foreign_array_named_allow_stays_operator_side(self):
        """Wave 1u2b0 F3(c): the location near-miss narrowed to a FOREIGN array that
        merely happens to be named `allow`. The rule string, the file, and the
        provenance record are all held identical to the positive; only the array's
        position moves, from `permissions.allow` to `somePlugin.config.allow`. No
        render ever rewrites a plugin's own config, so routing it to the "no edit
        needed" self-healing channel would guarantee it is never fixed."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._settings(
                root,
                ".claude/settings.json",
                '{"wavefoundryManagedAllow": ["mcp__wavefoundry__wave_close"],\n'
                ' "permissions": {"allow": ["mcp__wavefoundry__wave_close"]},\n'
                ' "somePlugin": {"config": {"allow": '
                '["mcp__wavefoundry__wave_close"]}}}\n',
            )
            _rec, host_flags, prov_flags = self.scan.scan_repo_channels(root)
        # POSITIVE (unchanged): the permissions.allow entry and its provenance record.
        self.assertEqual(len(prov_flags), 2, [f.matched for f in prov_flags])
        self.assertTrue(all(f.renderer_provenance for f in prov_flags))
        # NEAR-MISS: the foreign `allow` array is OPERATOR territory.
        self.assertEqual(len(host_flags), 1, [f.matched for f in host_flags])
        self.assertFalse(host_flags[0].renderer_provenance)
        self.assertEqual(host_flags[0].matched, "mcp__wavefoundry__wave_close")

    def test_governed_spans_are_positional_not_key_named(self):
        """Direct unit pin on the span resolver behind the channel split. Each case
        holds the rule string constant and varies only STRUCTURE, so the assertions
        cannot pass on a scanner that keys on the name `allow` alone."""
        rule = "mcp__wavefoundry__wave_close"
        governed_cases = {
            "permissions.allow": '{"permissions": {"allow": ["%s"]}}',
            "top-level provenance": '{"wavefoundryManagedAllow": ["%s"]}',
            "brackets inside a rule string": (
                '{"permissions": {"allow": ["Bash(ls [a-z])", "%s"]}}'
            ),
            "nested array sibling": '{"permissions": {"allow": [["x"], "%s"]}}',
            "whitespace between key and array": (
                '{\n "permissions" :\n {\n "allow" :\n [\n "%s"\n ]\n }\n}'
            ),
            "string value equal to the key": (
                '{"kind": "allow", "permissions": {"allow": ["%s"]}}'
            ),
        }
        ungoverned_cases = {
            "foreign nested allow": (
                '{"somePlugin": {"config": {"allow": ["%s"]}}, '
                '"permissions": {"allow": []}}'
            ),
            "foreign sibling allow": (
                '{"somePlugin": {"allow": ["%s"]}, "permissions": {"allow": []}}'
            ),
            "permissions object nested under another key": (
                '{"somePlugin": {"permissions": {"allow": ["%s"]}}}'
            ),
            "provenance key nested, not top level": (
                '{"somePlugin": {"wavefoundryManagedAllow": ["%s"]}}'
            ),
            "the key inside a string literal": (
                '{"hooks": {"cmd": "echo \\"allow\\": [\\"%s\\"]"}}'
            ),
            "deny entry": '{"permissions": {"allow": [], "deny": ["%s"]}}',
            "allow value is not an array": '{"permissions": {"allow": "%s"}}',
            "unclosed array degrades operator-side": '{"permissions": {"allow": ["%s"',
        }
        for label, template in governed_cases.items():
            text = template % rule
            offset = text.find(rule)
            spans = self.scan.provenance_governed_spans(text)
            self.assertTrue(
                any(start <= offset < end for start, end in spans),
                f"{label}: expected the rule offset inside a governed span, got {spans}",
            )
        for label, template in ungoverned_cases.items():
            text = template % rule
            offset = text.find(rule)
            spans = self.scan.provenance_governed_spans(text)
            self.assertFalse(
                any(start <= offset < end for start, end in spans),
                f"{label}: expected NO governed span over the rule offset, got {spans}",
            )

    def test_provenance_key_name_is_the_renderers(self):
        # Anti-duplication: the scan resolves the provenance key from
        # render_platform_surfaces (the one authority), not a local literal.
        render = _load("render_platform_surfaces", RENDER_PATH)
        self.assertEqual(render.PERMISSIONS_PROVENANCE_KEY, "wavefoundryManagedAllow")
        text = RECONCILE_PATH.read_text(encoding="utf-8")
        self.assertIn("PERMISSIONS_PROVENANCE_KEY", text)
        self.assertNotIn('"wavefoundryManagedAllow"', text,
                         "reconcile_scan must import the key, not re-author it")


class UpgradeRenderBeforeScanOrderingTests(unittest.TestCase):
    """Wave 1u2az AC-4: the upgrade renders surfaces (which self-heals the
    renderer-provenance allow rules) BEFORE any reconciliation scan reports;
    the seed-160 sequence becomes a tested invariant, not an accident."""

    UPGRADE_PATH = SCRIPTS_ROOT / "upgrade_wavefoundry.py"

    def test_main_renders_surfaces_before_any_scan_reporting(self):
        import ast as _ast

        source = self.UPGRADE_PATH.read_text(encoding="utf-8")
        tree = _ast.parse(source)
        main_fn = next(
            node for node in tree.body
            if isinstance(node, _ast.FunctionDef) and node.name == "main"
        )
        calls: list[tuple[str, int]] = []
        for node in _ast.walk(main_fn):
            if isinstance(node, _ast.Call):
                fn = node.func
                name = fn.id if isinstance(fn, _ast.Name) else getattr(fn, "attr", "")
                calls.append((name, node.lineno))
        def first(name: str) -> int:
            linenos = [ln for n, ln in calls if n == name]
            self.assertTrue(linenos, f"main() must call {name}")
            return min(linenos)
        render_line = first("phase_surface_rendering")
        # In the primary invocation, scan reporting happens only through the
        # single delegate-or-fallback emit site (wave 1u44o re-point: main() no
        # longer calls _emit_primary_phase_summary directly; it survives only
        # as the delegator's in-process degradation fallback); it must come
        # after the render.
        self.assertLess(
            render_line,
            first("_emit_primary_summary_via_delegate_or_fallback"),
            "_emit_primary_summary_via_delegate_or_fallback (whose producer or "
            "fallback runs the reconciliation scan) must follow "
            "phase_surface_rendering in upgrade main()",
        )
        # The other emitter, _print_operator_summary, runs only in the
        # cleanup/failure paths (phase_cleanup), which the upgrade reaches
        # after the primary phases, i.e. after the render already happened.
        callers: set[str] = set()
        for node in tree.body:
            if not isinstance(node, _ast.FunctionDef):
                continue
            for inner in _ast.walk(node):
                if (
                    isinstance(inner, _ast.Call)
                    and isinstance(inner.func, _ast.Name)
                    and inner.func.id == "_print_operator_summary"
                ):
                    callers.add(node.name)
        self.assertEqual(
            callers,
            {"phase_cleanup"},
            "_print_operator_summary must only run from the post-render "
            "cleanup path",
        )

    def test_scan_is_only_invoked_by_the_summary_emitters(self):
        # The ordering pin above is only sound if _run_reconciliation_scan has
        # no other call sites that could run before the render.
        import ast as _ast

        source = self.UPGRADE_PATH.read_text(encoding="utf-8")
        tree = _ast.parse(source)
        callers: set[str] = set()
        for node in tree.body:
            if not isinstance(node, _ast.FunctionDef):
                continue
            for inner in _ast.walk(node):
                if (
                    isinstance(inner, _ast.Call)
                    and isinstance(inner.func, _ast.Name)
                    and inner.func.id == "_run_reconciliation_scan"
                ):
                    callers.add(node.name)
        self.assertEqual(
            callers,
            {
                "_emit_primary_phase_summary",
                "_print_operator_summary",
                # Wave 1u44o (deliberate extension of the exhaustive emitter
                # set): the delegated producer computes the scan FRESH in the
                # extracted tree's own process; the requirement that closes
                # the pg1a cross-version import skew. It runs post-render by
                # construction (the parent spawns it at the primary emit).
                "_emit_delegated_summary",
            },
            "the reconciliation scan may only run from the summary emitters",
        )


class FindingSpecificDispositionTests(unittest.TestCase):
    """1w3bq: exact v2 identity, duplicate refusal, and field oracle."""

    def setUp(self):
        self.scan = _load("reconcile_scan", RECONCILE_PATH)

    @staticmethod
    def _write(root: Path, body: str) -> Path:
        path = root / "docs" / "agents" / "session-handoff.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_exact_downstream_cardinality_and_live_append(self):
        historical = (
            "# Handoff\n"
            "## Rename\n"
            "The wf-interrogate-plan skill was removed.\n"
            "The old wf-interrogate-plan directory was pruned.\n"
            "docs/prompts/interrogate-plan.prompt.md failed the old profile.\n"
            "Later docs/prompts/interrogate-plan.prompt.md was removed.\n"
            "The path docs/prompts/interrogate-plan.prompt.md stayed absent.\n"
            "The seed 175-interrogate-plan.prompt.md was retired.\n"
            "The old wf-interrogate-plan wrapper no longer renders.\n"
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = self._write(root, historical)
            raw = self.scan.scan_repo(root)
            self.assertEqual(len(raw), 7)
            self.assertEqual(len({self.scan.legacy_disposition_key(f) for f in raw}), 3)
            self.assertEqual(len({self.scan.disposition_key(f) for f in raw}), 7)
            self.assertTrue(all(re.fullmatch(r"v2:[0-9a-f]{32}", self.scan.disposition_key(f)) for f in raw))

            store = root / self.scan.DISPOSITIONS_REL
            store.write_text(
                json.dumps([
                    {"key": self.scan.disposition_key(f), "status": self.scan.HISTORICAL_RECORD}
                    for f in raw
                ]),
                encoding="utf-8",
            )
            self.assertEqual(self.scan.scan_repo_channels(root)[0], [])

            path.write_text(historical + "Use wf-interrogate-plan for every new plan.\n", encoding="utf-8")
            self.assertEqual(len(self.scan.scan_repo(root)), 8)
            [live] = self.scan.scan_repo_channels(root)[0]
            self.assertIn("Use wf-interrogate-plan", live.logical_line)

    def test_movement_stable_but_line_and_heading_context_change_key(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = self._write(root, "# One\nUse wf-interrogate-plan here.\n")
            [first] = self.scan.scan_repo(root)
            path.write_text("Unrelated preface.\n# One\nUse wf-interrogate-plan here.\n", encoding="utf-8")
            [moved] = self.scan.scan_repo(root)
            self.assertEqual(self.scan.disposition_key(first), self.scan.disposition_key(moved))
            path.write_text("# One\nUse wf-interrogate-plan here now.\n", encoding="utf-8")
            [line_changed] = self.scan.scan_repo(root)
            self.assertNotEqual(self.scan.disposition_key(first), self.scan.disposition_key(line_changed))
            path.write_text("# Two\nUse wf-interrogate-plan here.\n", encoding="utf-8")
            [heading_changed] = self.scan.scan_repo(root)
            self.assertNotEqual(self.scan.disposition_key(first), self.scan.disposition_key(heading_changed))

    def test_heading_context_ignores_atx_lines_inside_fences(self):
        for marker in ("```", "~~~"):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                self._write(
                    root,
                    "# Real heading\n"
                    f"{marker}md\n"
                    f"{marker}not-a-close\n"
                    "# Fenced example\n"
                    f"{marker}\t \n"
                    "Use wf-interrogate-plan here.\n",
                )
                [finding] = self.scan.scan_repo(root)

                self.assertEqual(finding.heading_context, "# Real heading")
                self.assertEqual(finding.logical_line, "Use wf-interrogate-plan here.")

    def test_duplicate_v2_fingerprint_suppresses_neither(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "# Same\nUse wf-interrogate-plan.\nUse wf-interrogate-plan.\n")
            raw = self.scan.scan_repo(root)
            self.assertEqual(len({self.scan.disposition_key(f) for f in raw}), 1)
            store = root / self.scan.DISPOSITIONS_REL
            store.write_text(
                json.dumps([{"key": self.scan.disposition_key(raw[0]), "status": self.scan.HISTORICAL_RECORD}]),
                encoding="utf-8",
            )
            reported = self.scan.scan_repo_channels(root)[0]
            self.assertEqual(len(reported), 2)
            self.assertEqual({f.disposition_state for f in reported}, {"v2-ambiguous"})

    def test_legacy_many_and_duplicate_store_entries_fail_open(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "# H\nPast wf-interrogate-plan one.\nPast wf-interrogate-plan two.\n")
            raw = self.scan.scan_repo(root)
            legacy = self.scan.legacy_disposition_key(raw[0])
            store = root / self.scan.DISPOSITIONS_REL
            store.write_text(json.dumps([{"key": legacy, "status": self.scan.HISTORICAL_RECORD}]), encoding="utf-8")
            reported = self.scan.scan_repo_channels(root)[0]
            self.assertEqual({f.disposition_state for f in reported}, {"legacy-ambiguous"})

            v2 = self.scan.disposition_key(raw[0])
            store.write_text(
                json.dumps([
                    {"key": v2, "status": self.scan.HISTORICAL_RECORD},
                    {"key": v2, "status": self.scan.HISTORICAL_RECORD},
                ]),
                encoding="utf-8",
            )
            reported = self.scan.scan_repo_channels(root)[0]
            self.assertEqual(len(reported), 2)
            self.assertIn("v2-ambiguous", {f.disposition_state for f in reported})

    def test_malformed_unknown_and_dormant_legacy_entries_fail_open_without_rewrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "# H\nUse wf-interrogate-plan here.\n")
            [raw] = self.scan.scan_repo(root)
            v2_digest = self.scan.disposition_key(raw).removeprefix("v2:")
            store = root / self.scan.DISPOSITIONS_REL
            original = json.dumps(
                [
                    {"key": "0123456789abcdef", "status": self.scan.HISTORICAL_RECORD},
                    {"key": "v2:not-hex", "status": self.scan.HISTORICAL_RECORD},
                    {"key": f"v3:{v2_digest}", "status": self.scan.HISTORICAL_RECORD},
                ],
                indent=2,
            ) + "\n"
            store.write_text(original, encoding="utf-8")

            [reported] = self.scan.scan_repo_channels(root)[0]

            self.assertEqual(reported.disposition_state, "unknown-version")
            self.assertEqual(store.read_text(encoding="utf-8"), original)

    def test_store_diagnostics_expose_settled_v2_and_dormant_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "# H\nPast wf-interrogate-plan here.\n")
            [raw] = self.scan.scan_repo(root)
            settled = self.scan.disposition_key(raw)
            dormant = "0123456789abcdef"
            store = root / self.scan.DISPOSITIONS_REL
            original = json.dumps(
                [
                    {"key": settled, "status": self.scan.HISTORICAL_RECORD},
                    {"key": dormant, "status": self.scan.HISTORICAL_RECORD},
                ],
                indent=2,
            ) + "\n"
            store.write_text(original, encoding="utf-8")

            diagnostics = self.scan.disposition_diagnostics(root)

            self.assertEqual(
                [(item["disposition_key"], item["disposition_state"]) for item in diagnostics],
                [(dormant, "legacy-dormant"), (settled, "v2-historical-record")],
            )
            self.assertEqual(diagnostics[0]["candidate_count"], 0)
            self.assertEqual(diagnostics[1]["candidate_locations"], [f"{raw.file}:{raw.line}"])
            self.assertEqual(self.scan.scan_repo_channels(root)[0], [])
            self.assertEqual(store.read_text(encoding="utf-8"), original)
