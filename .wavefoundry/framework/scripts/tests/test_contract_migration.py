"""Exercise behavior contract publication, migration, interruption and retry."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import contract_migration as migration
from techdocs_audit_lib import excluded, parse_mkdocs

SITE = """site_name: Private docs
docs_dir: docs
plugins:
  - techdocs-core
nav:
  - Home: index.md
  - Visible: specs/visible.md
exclude_docs: |
  /specs/**
  !/specs/visible.md
  !/architecture/**
"""


class ContractMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.put("mkdocs.yml", SITE)
        self.private = "docs/specs/private.md"
        self.visible = "docs/specs/visible.md"
        self.dest = "docs/architecture/contracts/private.md"
        self.put(self.private, "# Private\n[API](../api.md)\n")
        self.put(self.visible, "# Visible\n[Private](private.md#section)\n")
        self.put("docs/index.md", "[Private](specs/private.md)\n")
        self.put("docs/api.md", "# API\n")
        self.put("docs/specs/changes/kept.md", "# Old plan\n")
        self.put("docs/architecture/decisions/abc-adr.md", "[Private](../../specs/private.md)\n")

    def put(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode())

    def digest(self, publish=()):
        plan = migration.preview(self.root, publish)
        return plan, migration.save_preview(self.root, plan)

    def test_default_exclusion_and_owned_links_survive_move_and_repeat(self):
        plan, digest = self.digest()
        self.assertEqual(plan["rules"], ["/architecture/contracts/private.md"])
        self.assertEqual((self.root / "mkdocs.yml").read_text(), SITE)
        self.assertEqual(plan["exposure"], [{"source": self.private, "destination": self.dest,
                         "currently_published": False, "would_publish": True}])
        migration.apply(self.root, digest)
        parsed = parse_mkdocs((self.root / "mkdocs.yml").read_text())
        self.assertTrue(excluded(self.dest[5:], parsed["exclude_docs"]))
        self.assertEqual(parsed["nav"], ["index.md", "architecture/contracts/visible.md"])
        self.assertEqual((self.root / self.dest).read_text(), "# Private\n[API](../../api.md)\n")
        self.assertEqual((self.root / "docs/index.md").read_text(), "[Private](architecture/contracts/private.md)\n")
        self.assertIn("../../specs/private.md", (self.root / "docs/architecture/decisions/abc-adr.md").read_text())
        self.assertTrue((self.root / "docs/specs/changes/kept.md").is_file())
        migration.apply(self.root, digest)
        self.assertEqual(migration.remaining(self.root), [])

    def test_link_beside_comment_preserves_hidden_bytes(self):
        original = ("[Private](specs/private.md) <!-- [sample](specs/private.md) -->\r\n"
                    "<!-- note\r\nstill hidden --> [Visible](specs/visible.md)\r\n")
        self.put("docs/index.md", original)
        _, digest = self.digest()
        migration.apply(self.root, digest)
        expected = original.replace("[Private](specs/", "[Private](architecture/contracts/").replace(
            "[Visible](specs/", "[Visible](architecture/contracts/")
        self.assertEqual((self.root / "docs/index.md").read_bytes(), expected.encode())

    def test_config_migration_preserves_untouched_endings_and_uses_majority_for_new_rules(self):
        site = SITE.replace("exclude_docs: |\n", "exclude_docs: |\r\n")
        self.put("mkdocs.yml", site)
        _, digest = self.digest()
        migration.apply(self.root, digest)
        expected = site.replace("Visible: specs/", "Visible: architecture/contracts/")
        expected += "  /architecture/contracts/private.md\n"
        self.assertEqual((self.root / "mkdocs.yml").read_bytes(), expected.encode())

    def test_resume_rechecks_reference_definitions_before_retiring_originals(self):
        _, digest = self.digest()
        with patch.object(migration, "unlink_contained", side_effect=OSError("interrupted")):
            with self.assertRaisesRegex(OSError, "interrupted"):
                migration.apply(self.root, digest)
        self.put("docs/late.md", "[contract]: specs/private.md#status\n")
        with self.assertRaisesRegex(ValueError, "late.md"):
            migration.apply(self.root, digest)
        self.assertTrue((self.root / self.private).is_file())
        self.assertTrue((self.root / self.visible).is_file())

    def test_only_nav_changes_when_custom_metadata_repeats_a_route(self):
        metadata = "extra:\n  examples:\n    - specs/visible.md\n"
        self.put("mkdocs.yml", SITE + metadata)
        _, digest = self.digest()
        migration.apply(self.root, digest)
        config = (self.root / "mkdocs.yml").read_text()
        self.assertIn("  - Visible: architecture/contracts/visible.md\n", config)
        self.assertTrue(config.endswith(metadata))

    def test_selection_and_interruption(self):
        self.put("docs/specs/other.md", "# Also private\n")
        plan, digest = self.digest([self.private])
        self.assertEqual(plan["rules"], ["/architecture/contracts/other.md"])
        original = migration.unlink_contained
        with patch.object(migration, "unlink_contained", side_effect=OSError("interrupted")):
            with self.assertRaisesRegex(OSError, "interrupted"):
                migration.apply(self.root, digest)
        self.assertIs(original, migration.unlink_contained)
        self.assertTrue((self.root / self.dest).exists())
        self.assertTrue((self.root / self.private).exists())
        migration.apply(self.root, digest)
        self.assertFalse((self.root / self.private).exists())
        parsed = parse_mkdocs((self.root / "mkdocs.yml").read_text())
        self.assertTrue(excluded("architecture/contracts/other.md", parsed["exclude_docs"]))
        self.assertFalse(excluded(self.dest[5:], parsed["exclude_docs"]))

    def test_changed_scope_or_config_preserves_original(self):
        _, digest = self.digest()
        self.put("docs/new.md", "[Private](specs/private.md)")
        with self.assertRaisesRegex(ValueError, "scope"):
            migration.apply(self.root, digest)
        _, digest = self.digest()
        self.put("mkdocs.yml", SITE + "\n# operator edit\n")
        with self.assertRaisesRegex(ValueError, "changed"):
            migration.apply(self.root, digest)
        self.assertTrue((self.root / self.private).exists())
        self.assertFalse((self.root / self.dest).exists())

    def test_owner_conflicts_and_unknown_config_defer_without_writes(self):
        self.put(self.dest, "# Existing owner content")
        plan = migration.preview(self.root)
        self.assertIn(self.private, plan["deferred"])
        self.assertNotIn(self.private, plan["moves"])
        self.put("mkdocs.yml", "INHERIT: parent.yml\n" + SITE)
        plan = migration.preview(self.root)
        self.assertCountEqual(plan["deferred"], [self.private, self.visible])
        self.assertEqual(plan["actions"], [])
        self.assertEqual((self.root / self.dest).read_text(), "# Existing owner content")

    def test_move_without_site_and_unknown_link_syntax(self):
        (self.root / "mkdocs.yml").unlink()
        self.put(self.visible, "[API][wire]\n\n[wire]: ../api.md\n")
        plan, digest = self.digest()
        self.assertIn(self.visible, plan["deferred"])
        self.assertFalse(plan["exposure"])
        migration.apply(self.root, digest)
        self.assertTrue((self.root / self.visible).is_file())
        self.assertFalse((self.root / self.private).exists())

    def test_preserve_pretty_url_collision_and_unhandled_inbound_reference(self):
        self.put("docs/architecture/contracts/visible/index.md", "# Existing page")
        self.put("docs/references/incoming.md", "[contract]: ../specs/private.md\n")
        plan = migration.preview(self.root)
        self.assertIn("site URL", plan["deferred"][self.visible])
        self.assertIn("incoming.md", plan["deferred"][self.private])
        self.assertFalse(plan["actions"])

    def test_new_destination_at_publication_survives(self):
        import render_agent_surfaces as renderer
        _, digest = self.digest()
        publish = renderer._write_bytes_atomic_exclusive
        def create_competitor(path, data, **kwargs):
            if path == self.root / self.dest:
                self.put(self.dest, "Independent edit")
            return publish(path, data, **kwargs)
        with patch.object(renderer, "_write_bytes_atomic_exclusive", side_effect=create_competitor):
            with self.assertRaises(RuntimeError):
                migration.apply(self.root, digest)
        self.assertEqual((self.root / self.dest).read_text(), "Independent edit")
        self.assertTrue((self.root / self.private).is_file())

    def test_current_branch_link_and_example_literals(self):
        self.put(".git/config", '[remote "origin"]\n url = https://github.com/example/project.git\n')
        self.put(".git/HEAD", "ref: refs/heads/main\n")
        self.put("docs/index.md", "~~~md\n[example](specs/private.md)\n~~~\n"
                 "[repo](https://github.com/example/project/blob/main/docs/specs/private.md)\n"
                 "[pinned](https://github.com/example/project/blob/abcdef/docs/specs/private.md)\n")
        _, digest = self.digest()
        migration.apply(self.root, digest)
        text = (self.root / "docs/index.md").read_text()
        self.assertIn("[example](specs/private.md)", text)
        self.assertIn("/blob/main/docs/architecture/contracts/private.md", text)
        self.assertIn("/blob/abcdef/docs/specs/private.md", text)

    def test_completed_upgrade_reports_executable_recovery_for_a_custom_hook(self):
        import upgrade_wavefoundry as upgrade
        summary = upgrade._contract_migration_summary(self.root)
        self.assertEqual(summary["contract_migration_count"], 2)
        self.assertIn("contracts --root", summary["contract_migration_preview"])
        self.assertCountEqual(summary["contract_migration_paths"], [self.private, self.visible])
