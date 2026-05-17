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
    # Legacy fallback (no old manifest)
    # ------------------------------------------------------------------

    def test_no_old_manifest_runs_legacy_list(self):
        # Plant a known legacy file; prune with no old manifest should remove it.
        self._write("scripts/run_tests.py")
        self._new_manifest("scripts/build_pack.py")
        deleted = prune_framework.prune(self.fw, None)
        self.assertFalse((self.fw / "scripts" / "run_tests.py").exists())
        self.assertTrue(len(deleted) >= 1)

    def test_nonexistent_old_manifest_path_triggers_legacy_list(self):
        self._write("scripts/render_hooks.py")
        self._new_manifest("scripts/build_pack.py")
        missing_path = self.tmp / "does-not-exist.txt"
        deleted = prune_framework.prune(self.fw, missing_path)
        self.assertFalse((self.fw / "scripts" / "render_hooks.py").exists())

    def test_legacy_removes_tests_directory(self):
        self._write_meta(
            {
                "built_at": "2026-01-01T00:00:00Z",
                "content": ["docs"],
                "file_meta": {
                    "scripts/tests/test_foo.py": {"hash": "old"},
                    "scripts/keep_me.py": {"hash": "keep"},
                },
            }
        )
        tests_dir = self.fw / "scripts" / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_foo.py").write_text("x", encoding="utf-8")
        self._new_manifest("scripts/build_pack.py")
        prune_framework.prune(self.fw, None)
        self.assertFalse(tests_dir.exists())
        meta = json.loads((self.fw / "index" / "meta.json").read_text(encoding="utf-8"))
        self.assertNotIn("scripts/tests/test_foo.py", meta["file_meta"])
        self.assertIn("scripts/keep_me.py", meta["file_meta"])

    def test_legacy_dry_run_does_not_delete(self):
        self._write("scripts/run_tests.py")
        self._new_manifest("scripts/build_pack.py")
        prune_framework.prune(self.fw, None, dry_run=True)
        self.assertTrue((self.fw / "scripts" / "run_tests.py").exists())

    def test_legacy_does_not_touch_user_created_files(self):
        # A file not in the legacy list must survive even with no old manifest.
        self._write("index/local-index.json")
        self._new_manifest("scripts/build_pack.py")
        prune_framework.prune(self.fw, None)
        self.assertTrue((self.fw / "index" / "local-index.json").exists())

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
