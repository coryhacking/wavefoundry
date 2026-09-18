"""Unit tests for record_paths (wave 1y0gz / 1y042 / 1y043).

The record layout is defined by module constants (``WAVES_ROOT``,
``PLANS_ROOT``, ``NESTED``, ``MAX_DEPTH``); tests relocate by patching them
through ``record_layout_support``.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import record_paths as rp  # noqa: E402
from record_layout_support import apply_layout, patch_layout  # noqa: E402


class _TempRoot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()


class ShippedLayoutTests(_TempRoot):
    def test_shipped_constants_are_the_historical_layout_byte_identical(self):
        # The constants ARE the layout; the historical literal joins must be reproduced exactly.
        self.assertEqual(rp.WAVES_ROOT, "docs/waves")
        self.assertEqual(rp.PLANS_ROOT, "docs/plans")
        self.assertIs(rp.NESTED, False)
        self.assertEqual(rp.MAX_DEPTH, 4)
        roots = rp.load_record_roots(self.root)
        self.assertEqual(roots.waves, self.root / "docs" / "waves")
        self.assertEqual(roots.plans, self.root / "docs" / "plans")
        self.assertEqual(roots.waves_rel, "docs/waves")
        self.assertEqual(roots.plans_rel, "docs/plans")
        self.assertEqual(roots.waves_prefix, "docs/waves/")
        self.assertEqual(roots.plans_prefix, "docs/plans/")
        self.assertFalse(roots.nested)
        self.assertEqual(roots.max_depth, 4)
        self.assertEqual(rp.validate_record_layout(self.root), [])

    def test_no_configuration_is_read(self):
        # A workflow-config record_layout block or legacy wave_root is inert.
        (self.root / "docs").mkdir()
        (self.root / "docs" / "workflow-config.json").write_text(
            '{"record_layout": {"waves_root": "elsewhere"}, "wave_implement": {"wave_root": "legacy/"}}',
            encoding="utf-8",
        )
        self.assertEqual(rp.load_record_roots(self.root).waves_rel, "docs/waves")
        self.assertFalse(hasattr(rp, "read_record_layout"))
        self.assertFalse(hasattr(rp, "legacy_key_hint"))

    def test_stdlib_only_imports(self):
        import ast

        tree = ast.parse((SCRIPTS_DIR / "record_paths.py").read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
        self.assertEqual(names, {"__future__", "os", "dataclasses", "pathlib"})

    def test_layout_constants_are_read_at_call_time(self):
        before = rp.layout_constants()
        with patch_layout(modules=(rp,), waves_root="records/waves", nested=True, max_depth=2):
            self.assertEqual(rp.layout_constants(), ("records/waves", "docs/plans", True, 2))
        self.assertEqual(rp.layout_constants(), before)


class RelocatedLayoutTests(_TempRoot):
    def test_relocated_roots(self):
        apply_layout(self, modules=(rp,), waves_root="project/records/waves", plans_root="project/records/plans")
        roots = rp.load_record_roots(self.root)
        self.assertEqual(roots.waves, self.root / "project" / "records" / "waves")
        self.assertEqual(roots.plans, self.root / "project" / "records" / "plans")
        self.assertEqual(roots.waves_prefix, "project/records/waves/")

    def test_trailing_slash_and_backslash_are_normalized(self):
        apply_layout(self, modules=(rp,), waves_root="records\\waves/", plans_root="records/plans/")
        roots = rp.load_record_roots(self.root)
        self.assertEqual(roots.waves_rel, "records/waves")
        self.assertEqual(roots.plans_rel, "records/plans")

    def test_dot_segments_and_doubled_slashes_are_canonicalized(self):
        # Review finding resolver-identity-gaps: the prefix must match on-disk relative paths.
        for spelling in ("./records/waves", "records/./waves", "records//waves", "./records//waves/"):
            with self.subTest(spelling=spelling):
                with patch_layout(modules=(rp,), waves_root=spelling, plans_root="records/plans"):
                    self.assertEqual(rp.validate_record_layout(self.root), [])
                    roots = rp.load_record_roots(self.root)
                    self.assertEqual(roots.waves_rel, "records/waves")
                    self.assertEqual(roots.waves_prefix, "records/waves/")
                    self.assertEqual(roots.waves, self.root / "records" / "waves")
                    self.assertTrue("records/waves/1abcd x/wave.md".startswith(roots.waves_prefix))

    def test_unvalidated_roots_never_raise(self):
        apply_layout(self, modules=(rp,), waves_root="/abs", plans_root="records/plans")
        with self.assertRaises(rp.RecordLayoutInvalid):
            rp.load_record_roots(self.root)
        roots = rp.unvalidated_record_roots(self.root)
        self.assertEqual(roots.plans_rel, "records/plans")


class InvalidLayoutTests(_TempRoot):
    def _assert_invalid(self, fragment: str, **layout):
        with patch_layout(modules=(rp,), **layout):
            diagnostics = rp.validate_record_layout(self.root)
            self.assertTrue(diagnostics, layout)
            self.assertTrue(all(d.startswith("record_layout_invalid:") for d in diagnostics), diagnostics)
            self.assertIn(fragment, "\n".join(diagnostics))
            with self.assertRaises(rp.RecordLayoutInvalid) as ctx:
                rp.load_record_roots(self.root)
            self.assertEqual(ctx.exception.diagnostics, diagnostics)
            self.assertNotIsInstance(ctx.exception, ValueError)

    def test_absolute_root(self):
        self._assert_invalid("must be repository-relative", waves_root="/abs/waves")

    def test_windows_drive_root(self):
        self._assert_invalid("must be repository-relative", plans_root="C:\\plans")

    def test_embedded_windows_drive_is_refused_before_ancestor_lookup(self):
        # Portable pin: Path on POSIX accepts this spelling, but joining it
        # on Windows can switch drives. Neither missing nor existing parents
        # may permit that fork constant for either record root.
        for existing in (False, True):
            if existing:
                (self.root / "records").mkdir()
            for name in ("waves_root", "plans_root"):
                for value in ("records/D:/waves", "records/C:relative", "records\\D:\\waves"):
                    with self.subTest(existing=existing, name=name, value=value):
                        self._assert_invalid("drive-qualified component", **{name: value})

    def test_dotdot_root(self):
        self._assert_invalid("must not contain '..'", waves_root="../outside")

    def test_empty_root(self):
        self._assert_invalid("must be a non-empty string", waves_root="   ")

    def test_dot_only_root(self):
        self._assert_invalid("must name a directory", waves_root="./")

    def test_non_string_root(self):
        self._assert_invalid("must be a non-empty string", plans_root=None)

    def test_equal_roots(self):
        self._assert_invalid("must differ", waves_root="docs/records", plans_root="docs/records")

    def test_equal_roots_by_spelling(self):
        self._assert_invalid("must differ", waves_root="docs/./records", plans_root="docs/records/")

    def test_nested_roots_either_direction(self):
        self._assert_invalid("must not nest", waves_root="docs/records", plans_root="docs/records/plans")
        self._assert_invalid("must not nest", waves_root="docs/records/waves", plans_root="docs/records")

    def test_file_as_root(self):
        (self.root / "docs").mkdir()
        (self.root / "docs" / "notes.md").write_text("x", encoding="utf-8")
        self._assert_invalid("not a file", waves_root="docs/notes.md")

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_escaping_symlink(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (self.root / "records").mkdir()
        os.symlink(outside.name, self.root / "records" / "waves")
        self._assert_invalid("resolves outside the repository", waves_root="records/waves", plans_root="records/plans")

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_dangling_symlink_root_is_refused(self):
        # Finding `dangling-symlink-root-invisible`: the entry exists but its
        # target does not, so `exists()` is False and the old walk treated the
        # root as absent (a first create would write THROUGH the link).
        (self.root / "docs").mkdir()
        os.symlink(self.root / "docs" / "missing-target", self.root / "docs" / "waves")
        with patch_layout(modules=(rp,), waves_root="docs/waves"):
            diagnostics = rp.validate_record_layout(self.root)
        self.assertEqual(len(diagnostics), 1, diagnostics)
        self.assertIn("record_paths.WAVES_ROOT must name a directory, not a dangling symlink", diagnostics[0])
        self.assertIn("(docs/waves is a dangling symlink)", diagnostics[0])
        self.assertNotIn("is a file", diagnostics[0])
        self._assert_invalid("not a dangling symlink", waves_root="docs/waves")
        self.assertFalse((self.root / "docs" / "missing-target").exists(), "nothing may be created through the link")

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_dangling_symlink_ancestor_is_refused(self):
        # The dangling entry ABOVE an absent root is the nearest existing
        # entry, and the message names that ancestor.
        os.symlink("missing-target", self.root / "records")
        with patch_layout(modules=(rp,), waves_root="records/waves", plans_root="docs/plans"):
            diagnostics = rp.validate_record_layout(self.root)
        self.assertEqual(len(diagnostics), 1, diagnostics)
        self.assertIn("record_paths.WAVES_ROOT must name a directory, not a dangling symlink", diagnostics[0])
        self.assertIn("(records is a dangling symlink)", diagnostics[0])
        self._assert_invalid("not a dangling symlink", waves_root="records/waves", plans_root="docs/plans")

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_looping_symlink_root_is_refused(self):
        # A self-referential link: `lstat` succeeds, `stat` raises ELOOP on
        # some platforms; validation must refuse it, never raise.
        (self.root / "docs").mkdir()
        os.symlink("waves", self.root / "docs" / "waves")
        with patch_layout(modules=(rp,), waves_root="docs/waves"):
            diagnostics = rp.validate_record_layout(self.root)
        self.assertEqual(len(diagnostics), 1, diagnostics)
        self.assertIn("not a dangling symlink", diagnostics[0])
        self.assertIn("(docs/waves is a dangling symlink)", diagnostics[0])
        self._assert_invalid("not a dangling symlink", waves_root="docs/waves")
        # The plans root sharing the looping ancestor is refused the same way.
        self._assert_invalid("(docs/waves is a dangling symlink)", plans_root="docs/waves/plans")

    def test_file_ancestor_of_root(self):
        # Finding `root-ancestor-is-file`: a file ABOVE the (absent) root is
        # refused, naming the offending ancestor, before a first create fails.
        (self.root / "docs").mkdir()
        (self.root / "docs" / "notes.md").write_text("x", encoding="utf-8")
        with patch_layout(modules=(rp,), waves_root="docs/notes.md/waves"):
            diagnostics = rp.validate_record_layout(self.root)
        self.assertEqual(len(diagnostics), 1, diagnostics)
        self.assertIn("record_paths.WAVES_ROOT must name a directory, not a file", diagnostics[0])
        self.assertIn("docs/notes.md is a file", diagnostics[0])
        self._assert_invalid("not a file", waves_root="docs/notes.md/waves")

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_nesting_judged_against_nearest_existing_ancestor(self):
        # `docs/plans -> docs` with `docs/waves` absent: the first wave would be
        # created INSIDE the plans root, so the layout is refused before it is.
        (self.root / "docs").mkdir()
        os.symlink(self.root / "docs", self.root / "docs" / "plans")
        self._assert_invalid("must not nest", waves_root="docs/waves", plans_root="docs/plans")
        self.assertFalse((self.root / "docs" / "waves").exists())
        # The mirror image: the plans root absent under a waves-root alias.
        (self.root / "records").mkdir()
        os.symlink(self.root / "records", self.root / "records" / "waves")
        self._assert_invalid("must not nest", waves_root="records/waves", plans_root="records/plans")

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_symlink_alias_root_is_refused(self):
        # D5: `records -> docs/waves` is an alias of the canonical directory;
        # every lifecycle tool refuses it through its containment guard, so the
        # layout refuses it too (the former internal-symlink allowance is gone).
        (self.root / "docs" / "waves").mkdir(parents=True)
        os.symlink(self.root / "docs" / "waves", self.root / "records")
        self._assert_invalid(
            "record_paths.WAVES_ROOT must resolve to the canonical in-repository directory",
            waves_root="records", plans_root="docs/plans",
        )
        # A symlinked ANCESTOR of an absent root is the same alias.
        (self.root / "real").mkdir()
        os.symlink(self.root / "real", self.root / "linked")
        self._assert_invalid("must resolve to the canonical", waves_root="linked/waves", plans_root="docs/plans")

    def test_case_alias_root_is_refused(self):
        (self.root / "docs" / "waves").mkdir(parents=True)
        if not (self.root / "Docs" / "waves").exists():
            self.skipTest("case-sensitive filesystem: spellings are distinct directories")
        self._assert_invalid(
            "record_paths.WAVES_ROOT must resolve to the canonical in-repository directory",
            waves_root="Docs/waves", plans_root="docs/plans",
        )

    def test_case_variant_roots_are_one_directory_on_a_case_insensitive_filesystem(self):
        (self.root / "docs" / "plans").mkdir(parents=True)
        if not (self.root / "docs" / "Plans").exists():
            self.skipTest("case-sensitive filesystem: spellings are distinct directories")
        self._assert_invalid("must differ", waves_root="docs/Plans", plans_root="docs/plans")

    def test_case_variant_nesting_on_a_case_insensitive_filesystem(self):
        (self.root / "docs" / "waves" / "plans").mkdir(parents=True)
        if not (self.root / "Docs" / "Waves").exists():
            self.skipTest("case-sensitive filesystem: spellings are distinct directories")
        self._assert_invalid("must not nest", waves_root="docs/waves", plans_root="Docs/Waves/plans")

    def test_absent_root_is_valid(self):
        apply_layout(self, modules=(rp,), waves_root="not/yet/created")
        self.assertEqual(rp.validate_record_layout(self.root), [])

    def test_invalid_layout_never_falls_back(self):
        apply_layout(self, modules=(rp,), waves_root="/abs")
        with self.assertRaises(rp.RecordLayoutInvalid):
            rp.load_record_roots(self.root)
        with self.assertRaises(rp.RecordLayoutInvalid):
            rp.discover_wave_dirs(self.root)

    def test_max_depth_and_nested_are_validated(self):
        for layout, fragment in (
            ({"nested": "yes"}, "must be True or False"),
            ({"nested": 1}, "must be True or False"),
            ({"nested": True, "max_depth": 0}, "integer from 1 to 8"),
            ({"nested": True, "max_depth": 9}, "integer from 1 to 8"),
            ({"nested": True, "max_depth": True}, "integer from 1 to 8"),
            ({"nested": True, "max_depth": "4"}, "integer from 1 to 8"),
        ):
            with self.subTest(layout=layout):
                self._assert_invalid(fragment, **layout)


class NestedDiscoveryTests(_TempRoot):
    """1y043: discover_wave_dirs, walk guards, depth bound, ambiguity."""

    def setUp(self):
        super().setUp()
        self.waves = self.root / "docs" / "waves"
        self.waves.mkdir(parents=True)

    def _wave(self, rel: str) -> Path:
        d = self.waves.joinpath(*rel.split("/"))
        d.mkdir(parents=True, exist_ok=True)
        (d / "wave.md").write_text("# Wave Record\n\nStatus: planned\n", encoding="utf-8")
        return d

    def _nested(self, max_depth=None):
        layout = {"nested": True}
        if max_depth is not None:
            layout["max_depth"] = max_depth
        apply_layout(self, modules=(rp,), **layout)

    def test_flat_returns_immediate_children_with_wave_md_only(self):
        a = self._wave("1aaaa one")
        self._wave("group/1bbbb two")  # nested: invisible in flat mode
        (self.waves / "loose").mkdir()  # no wave.md
        self.assertEqual(rp.discover_wave_dirs(self.root), [a])
        self.assertEqual(rp.walk_wave_candidates(self.root), [a, self.waves / "group", self.waves / "loose"])
        roots = rp.load_record_roots(self.root)
        self.assertFalse(roots.nested)
        self.assertEqual(roots.max_depth, 4)

    def test_flat_never_lists_a_file_as_a_candidate(self):
        # Review finding: the is_dir filter had no discriminating test.
        a = self._wave("1aaaa one")
        (self.waves / "1zzzz stray.md").write_text("x", encoding="utf-8")
        self.assertEqual(rp.walk_wave_candidates(self.root), [a])

    def test_default_max_depth_is_four_and_finds_a_depth_four_wave(self):
        # Review finding: the default was pinned tautologically.
        apply_layout(self, modules=(rp,), nested=True)
        self.assertEqual(rp.load_record_roots(self.root).max_depth, 4)
        four = self._wave("a/b/c/1dddd four")
        self._wave("a/b/c/d/1eeee five")
        self.assertEqual(rp.discover_wave_dirs(self.root), [four])

    def test_nested_finds_waves_at_depth_one_two_and_three(self):
        self._nested()
        a = self._wave("1aaaa one")
        b = self._wave("team/1bbbb two")
        c = self._wave("team/feature/1cccc three")
        self.assertEqual(rp.discover_wave_dirs(self.root), sorted([a, b, c]))

    def test_nested_never_descends_into_a_discovered_wave_folder(self):
        self._nested()
        a = self._wave("1aaaa one")
        self._wave("1aaaa one/evidence/1zzzz not-a-wave")
        self.assertEqual(rp.discover_wave_dirs(self.root), [a])

    def test_nested_skips_dot_directories(self):
        # AC-4a, dot-prefixed directory
        self._nested()
        a = self._wave("1aaaa one")
        self._wave(".hidden/1hhhh hidden")
        self.assertEqual(rp.discover_wave_dirs(self.root), [a])

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_nested_skips_symlinked_directories(self):
        # AC-4a, symlinked directory (pointing outside the repository)
        self._nested()
        a = self._wave("1aaaa one")
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / "1ssss linked").mkdir()
        (Path(outside.name) / "1ssss linked" / "wave.md").write_text("x", encoding="utf-8")
        os.symlink(outside.name, self.waves / "linked")
        self.assertEqual(rp.discover_wave_dirs(self.root), [a])

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_flat_layout_still_enumerates_a_symlinked_child(self):
        # AC-1: the flat layout matches the pre-change ``iterdir`` enumeration,
        # so a symlinked wave folder is found here and refused downstream by the
        # record-writer path-escape guards (pinned in the lifecycle suite).
        a = self._wave("1aaaa one")
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / "wave.md").write_text("x", encoding="utf-8")
        os.symlink(outside.name, self.waves / "1ssss linked")
        self.assertEqual(rp.discover_wave_dirs(self.root), [a, self.waves / "1ssss linked"])

    def test_max_depth_bounds_the_walk_and_no_directory_beyond_it_is_visited(self):
        self._nested(max_depth=2)
        a = self._wave("1aaaa one")
        b = self._wave("g1/1bbbb two")
        self._wave("g1/g2/1cccc three")  # depth 3: beyond the bound
        visited = []
        original = rp._list_subdirs

        def spy(directory, **kwargs):
            visited.append(directory)
            return original(directory, **kwargs)

        try:
            rp._list_subdirs = spy
            found = rp.discover_wave_dirs(self.root)
        finally:
            rp._list_subdirs = original
        self.assertEqual(found, [a, b])
        for d in visited:
            depth = len(d.relative_to(self.waves).parts)
            self.assertLessEqual(depth, 1, f"visited beyond max_depth: {d}")

    def test_duplicate_ids_at_two_depths_are_reported_with_both_paths(self):
        self._nested()
        self._wave("1aaaa one")
        self._wave("team/1aaaa one-again")
        self._wave("1bbbb unique")
        dirs = rp.discover_wave_dirs(self.root)
        self.assertEqual(list(rp.ambiguous_wave_ids(dirs)), ["1aaaa"])
        lines = rp.ambiguous_wave_id_diagnostics(self.root, dirs)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("ambiguous_wave_id: 1aaaa at "))
        self.assertIn("docs/waves/1aaaa one", lines[0])
        self.assertIn("docs/waves/team/1aaaa one-again", lines[0])

    def test_ambiguity_diagnostics_tolerate_a_resolved_path_against_an_unresolved_root(self):
        # Review finding F3: /var vs /private/var.
        self._nested()
        self._wave("1aaaa one")
        self._wave("team/1aaaa one-again")
        dirs = [d.resolve() for d in rp.discover_wave_dirs(self.root)]
        lines = rp.ambiguous_wave_id_diagnostics(self.root, dirs)
        self.assertEqual(len(lines), 1)
        self.assertIn("docs/waves/1aaaa one, docs/waves/team/1aaaa one-again", lines[0])

    def test_wave_id_of_lower_cases_the_token(self):
        self.assertEqual(rp.wave_id_of(Path("1ABCD Slug")), "1abcd")


if __name__ == "__main__":
    unittest.main()
