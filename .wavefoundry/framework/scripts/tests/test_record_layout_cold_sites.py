"""AC-8 (wave 1y0gz / 1y042): the three consumers with no wave-path test
coverage before this change each see a wave placed under a relocated root.

* dashboard listing (``dashboard_lib.collect_waves``)
* memory-backfill wave scan (``memory_backfill.inventory_closed_waves``)
* the ``wave`` document classification (``_tag_utils.infer_tags`` through the
  chunker's ``_infer_tags`` binding and the server's ``_infer_tags`` live
  path, which derives the prefix from the repository root)

The layout is the ``record_paths`` module constants, patched through
``record_layout_support``.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from record_layout_support import apply_layout, patch_layout
from server_tools_support import _make_repo, load_server

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

RELOCATED = {"waves_root": "project/records/waves", "plans_root": "project/records/plans"}

WAVE_MD = """# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-17

wave-id: `1abcd relocated-demo`
Title: Relocated Demo

## Objective

Demo.

## Changes

Change ID: `1abce-enh demo`
Change Status: `complete`
"""


class ColdSiteRelocatedRootTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()  # binds `server` for dashboard_lib
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        apply_layout(self, modules=(self.srv.record_paths,), **RELOCATED)
        self.wave_dir = self.root / "project" / "records" / "waves" / "1abcd relocated-demo"
        self.wave_dir.mkdir(parents=True)
        (self.wave_dir / "wave.md").write_text(WAVE_MD, encoding="utf-8")
        (self.wave_dir / "1abce-enh demo.md").write_text("# Demo\n\nChange ID: `1abce-enh demo`\nChange Status: `complete`\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_dashboard_lists_a_wave_under_the_relocated_root(self):
        import dashboard_lib

        waves = dashboard_lib.collect_waves(self.root)
        ids = [w.get("wave_id") or w.get("id") for w in waves]
        self.assertIn("1abcd relocated-demo", ids, waves)
        for w in waves:
            for key in ("path", "wave_md", "record_path"):
                value = w.get(key)
                if isinstance(value, str):
                    self.assertIn("project/records/waves/", value.replace("\\", "/"))
                    self.assertNotIn("docs/waves/", value.replace("\\", "/"))

    def test_memory_backfill_inventories_a_closed_wave_under_the_relocated_root(self):
        import memory_backfill

        self.assertEqual(memory_backfill._canonical_waves_dir(self.root), self.wave_dir.parent.resolve())
        rows = memory_backfill.inventory_closed_waves(self.root)
        self.assertEqual([r.get("wave_id") or r.get("id") for r in rows], ["1abcd relocated-demo"], rows)

    def test_wave_tag_follows_the_configured_prefix(self):
        import chunker
        import record_paths

        prefix = record_paths.load_record_roots(self.root).waves_prefix
        self.assertEqual(prefix, "project/records/waves/")
        relocated = "project/records/waves/1abcd relocated-demo/wave.md"
        self.assertIn("wave", chunker._infer_tags(relocated, waves_prefix=prefix))
        # Under the relocated layout the DEFAULT location is no longer a wave.
        self.assertNotIn("wave", chunker._infer_tags("docs/waves/1abcd x/wave.md", waves_prefix=prefix))
        # And the module default (the WAVES_ROOT constant bound at
        # `_tag_utils` import time) keeps its own behaviour.
        import _tag_utils

        default_prefix = _tag_utils._DEFAULT_WAVES_PREFIX
        self.assertIn("wave", chunker._infer_tags(f"{default_prefix}1abcd x/wave.md"))

    def test_server_infer_tags_derives_the_prefix_from_the_root(self):
        # The server's live path threads `_record_prefixes(root)` through;
        # without a root the `_tag_utils` default binding applies unchanged.
        import _tag_utils

        relocated = "project/records/waves/1abcd relocated-demo/wave.md"
        shipped = "docs/waves/1abcd x/wave.md"
        other = "other/waves/1abcd x/wave.md"
        self.assertIn("wave", self.srv._infer_tags(relocated, root=self.root))
        self.assertNotIn("wave", self.srv._infer_tags(shipped, root=self.root))
        self.assertNotIn("wave", self.srv._infer_tags(other, root=self.root))
        # The module default can equal at most one layout, so the root-derived
        # prefix must be live for BOTH of these to hold.
        with patch_layout(modules=(self.srv.record_paths,), waves_root="other/waves"):
            self.assertIn("wave", self.srv._infer_tags(other, root=self.root))
            self.assertNotIn("wave", self.srv._infer_tags(relocated, root=self.root))
        for path in (relocated, shipped, other):
            self.assertEqual(self.srv._infer_tags(path), _tag_utils.infer_tags(path), path)


if __name__ == "__main__":
    unittest.main()
