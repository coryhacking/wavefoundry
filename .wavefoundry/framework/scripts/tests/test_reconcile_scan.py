"""Tests for the shipped upgrade-time retired-surface reconciliation scan (wave 1p8et).

Covers: the structured result shape, the single retired→new map (incl. the `mcp-server`
no-replacement case), the baked-in exclusion set (each excluded path NOT flagged), and the
anti-duplication guard (no second hand-authored copy of the map).
"""
from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
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
        for path in sorted(SCRIPTS_ROOT.glob("*.py")):
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
                 "matched": ".wavefoundry/bin/docs-lint", "suggested": "wf docs-lint"},
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
            "docs/x/CHANGELOG.md",        # nested CHANGELOG — only the repo-root one is excluded
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
