"""Tests for prune_framework.py."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import prune_framework  # noqa: E402


class PruneFrameworkTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self.fw = self.tmp / ".wavefoundry" / "framework"
        self.fw.mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write(self, rel: str, content: str = "x") -> Path:
        p = self.fw / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _old_manifest(self, *entries: str) -> Path:
        path = self.tmp / "old-manifest.txt"
        path.write_text("\n".join(entries) + "\n", encoding="utf-8")
        return path

    def _new_manifest(self, *entries: str) -> None:
        (self.fw / "MANIFEST").write_text("\n".join(entries) + "\n", encoding="utf-8")

    def _write_meta(self, payload: dict) -> Path:
        meta_path = self.fw / "index" / "meta.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(payload), encoding="utf-8")
        return meta_path

    # ------------------------------------------------------------------

    def test_file_removed_from_new_pack_is_deleted(self):
        self._write("scripts/old_tool.py")
        old = self._old_manifest("scripts/old_tool.py")
        self._new_manifest("seeds/foo.md")
        prune_framework.prune(self.fw, old)
        self.assertFalse((self.fw / "scripts" / "old_tool.py").exists())

    def test_file_still_in_new_pack_is_kept(self):
        self._write("scripts/keep_me.py")
        old = self._old_manifest("scripts/keep_me.py")
        self._new_manifest("scripts/keep_me.py")
        prune_framework.prune(self.fw, old)
        self.assertTrue((self.fw / "scripts" / "keep_me.py").exists())

    def test_user_created_file_not_in_any_manifest_is_never_deleted(self):
        self._write("index/local-index.json")
        old = self._old_manifest("seeds/foo.md")
        self._new_manifest("seeds/foo.md")
        prune_framework.prune(self.fw, old)
        self.assertTrue((self.fw / "index" / "local-index.json").exists())

    def test_file_meta_entries_removed_from_meta_json(self):
        self._write("scripts/keep_me.py")
        self._write("scripts/old_tool.py")
        self._write_meta(
            {
                "built_at": "2026-01-01T00:00:00Z",
                "content": ["docs"],
                "file_meta": {
                    "scripts/keep_me.py": {"hash": "keep"},
                    "scripts/old_tool.py": {"hash": "old"},
                },
            }
        )
        old = self._old_manifest("scripts/keep_me.py", "scripts/old_tool.py")
        self._new_manifest("scripts/keep_me.py")

        prune_framework.prune(self.fw, old)

        meta = json.loads((self.fw / "index" / "meta.json").read_text(encoding="utf-8"))
        self.assertIn("scripts/keep_me.py", meta["file_meta"])
        self.assertNotIn("scripts/old_tool.py", meta["file_meta"])

    def test_empty_dir_removed_after_prune(self):
        self._write("scripts/tests/test_old.py")
        old = self._old_manifest("scripts/tests/test_old.py")
        self._new_manifest("seeds/foo.md")
        prune_framework.prune(self.fw, old)
        self.assertFalse((self.fw / "scripts" / "tests").exists())

    def test_non_empty_dir_kept_after_partial_prune(self):
        self._write("scripts/tests/test_old.py")
        self._write("scripts/tests/test_kept.py")
        old = self._old_manifest("scripts/tests/test_old.py", "scripts/tests/test_kept.py")
        self._new_manifest("scripts/tests/test_kept.py")
        prune_framework.prune(self.fw, old)
        self.assertFalse((self.fw / "scripts" / "tests" / "test_old.py").exists())
        self.assertTrue((self.fw / "scripts" / "tests" / "test_kept.py").exists())
        self.assertTrue((self.fw / "scripts" / "tests").is_dir())

    def test_file_hashes_entries_removed_from_meta_json(self):
        self._write("scripts/keep_me.py")
        self._write("scripts/old_tool.py")
        self._write_meta(
            {
                "built_at": "2026-01-01T00:00:00Z",
                "content": ["docs"],
                "file_hashes": {
                    "scripts/keep_me.py": "keep",
                    "scripts/old_tool.py": "old",
                },
            }
        )
        old = self._old_manifest("scripts/keep_me.py", "scripts/old_tool.py")
        self._new_manifest("scripts/keep_me.py")

        prune_framework.prune(self.fw, old)

        meta = json.loads((self.fw / "index" / "meta.json").read_text(encoding="utf-8"))
        self.assertIn("scripts/keep_me.py", meta["file_hashes"])
        self.assertNotIn("scripts/old_tool.py", meta["file_hashes"])

    def test_dry_run_does_not_delete(self):
        self._write("scripts/old_tool.py")
        old = self._old_manifest("scripts/old_tool.py")
        self._new_manifest("seeds/foo.md")
        deleted = prune_framework.prune(self.fw, old, dry_run=True)
        self.assertTrue((self.fw / "scripts" / "old_tool.py").exists())
        self.assertEqual(len(deleted), 1)

    def test_missing_new_manifest_emits_warning_and_returns_empty(self):
        old = self._old_manifest("scripts/old_tool.py")
        # Do not write new MANIFEST.
        import io
        from contextlib import redirect_stderr
        buf = io.StringIO()
        with redirect_stderr(buf):
            result = prune_framework.prune(self.fw, old)
        self.assertEqual(result, [])
        self.assertIn("MANIFEST", buf.getvalue())

    # ------------------------------------------------------------------
    # Wave 1p2q3 (1p2ta): no-manifest behavior — prune is a no-op.
    # The prior legacy-fallback list was deleting git-tracked development
    # files (scripts/tests/, scripts/run_tests.py) on every self-hosted
    # upgrade because build_pack deletes MANIFEST after writing it into
    # the zip, leaving upgrade-wavefoundry without an old manifest to diff
    # against. The fallback is removed; prune now logs and returns when
    # called without --old-manifest.
    # ------------------------------------------------------------------

    def test_no_old_manifest_is_noop_does_not_delete_tests_dir(self):
        """AC-4: prune called without --old-manifest must not touch tests/."""
        tests_dir = self.fw / "scripts" / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_foo.py").write_text("x", encoding="utf-8")
        self._write("scripts/run_tests.py")
        self._new_manifest("scripts/build_pack.py")
        deleted = prune_framework.prune(self.fw, None)
        self.assertEqual(deleted, [])
        self.assertTrue(tests_dir.exists(), "tests/ must not be deleted on no-manifest prune")
        self.assertTrue((tests_dir / "test_foo.py").is_file())
        self.assertTrue((self.fw / "scripts" / "run_tests.py").is_file())

    def test_no_old_manifest_emits_skip_notice(self):
        self._new_manifest("scripts/build_pack.py")
        import io
        from contextlib import redirect_stderr
        buf = io.StringIO()
        with redirect_stderr(buf):
            prune_framework.prune(self.fw, None)
        self.assertIn("no old MANIFEST", buf.getvalue())
        self.assertIn("skipping prune", buf.getvalue())

    def test_nonexistent_old_manifest_path_is_also_noop(self):
        """An old-manifest path that doesn't exist on disk is treated as no
        manifest; same no-op behavior."""
        self._write("scripts/render_hooks.py")
        self._new_manifest("scripts/build_pack.py")
        missing_path = self.tmp / "does-not-exist.txt"
        deleted = prune_framework.prune(self.fw, missing_path)
        self.assertEqual(deleted, [])
        self.assertTrue((self.fw / "scripts" / "render_hooks.py").exists())

    def test_legacy_constants_and_function_removed(self):
        """Regression: _LEGACY_REMOVALS and _prune_legacy were deleted in
        wave 1p2q3 (1p2ta). Their re-introduction would re-open the data-loss
        vector this change fixed."""
        self.assertFalse(hasattr(prune_framework, "_LEGACY_REMOVALS"))
        self.assertFalse(hasattr(prune_framework, "_prune_legacy"))

    def test_diff_path_still_deletes_when_old_manifest_supplied(self):
        """AC-5: the diff-based deletion path is unaffected by removing the
        legacy fallback."""
        self._write("scripts/old_tool.py")
        old = self._old_manifest("scripts/old_tool.py")
        self._new_manifest("scripts/build_pack.py")
        prune_framework.prune(self.fw, old)
        self.assertFalse((self.fw / "scripts" / "old_tool.py").exists())

    def test_returns_list_of_deleted_paths(self):
        self._write("scripts/old_a.py")
        self._write("scripts/old_b.py")
        old = self._old_manifest("scripts/old_a.py", "scripts/old_b.py")
        self._new_manifest("seeds/foo.md")
        deleted = prune_framework.prune(self.fw, old)
        self.assertEqual(len(deleted), 2)

    def test_blank_lines_in_manifest_ignored(self):
        self._write("scripts/old_tool.py")
        path = self.tmp / "old-manifest.txt"
        path.write_text("\n\nscripts/old_tool.py\n\n", encoding="utf-8")
        self._new_manifest("seeds/foo.md")
        prune_framework.prune(self.fw, path)
        self.assertFalse((self.fw / "scripts" / "old_tool.py").exists())


if __name__ == "__main__":
    unittest.main()
