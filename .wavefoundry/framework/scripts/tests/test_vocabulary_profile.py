"""Vocabulary profile validation and the discovery diagnostic (wave 1z8mm, change 1z826).

AC-5: each validation rule refuses a profile violating it, with a diagnostic
naming the field.
AC-4: a waves root whose folders hold a record under another filename produces
the advisory ``record_file_not_found`` diagnostic from ``list_waves``,
``wf_current_wave`` and docs-lint; a root with no candidate folders produces none.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import record_paths  # noqa: E402
import vocabulary_profile  # noqa: E402
from record_layout_support import patch_layout  # noqa: E402
from server_tools_support import _make_repo, load_server  # noqa: E402
import test_docs_lint as _docs_lint  # noqa: E402  (module import keeps its tests out of this module)
from wave_lint_lib.constants import SENSOR_POLARITY_REGISTRY  # noqa: E402
from wave_lint_lib.wave_validators import record_discovery_findings  # noqa: E402


def _errors(**overrides) -> list[str]:
    with patch.multiple(vocabulary_profile, **overrides):
        return vocabulary_profile.validation_errors()


class ValidationTests(unittest.TestCase):
    def assertRefused(self, field: str, **overrides) -> None:
        errors = _errors(**overrides)
        self.assertTrue(errors, f"{overrides} was accepted")
        self.assertTrue(any(field in e for e in errors), f"{field} not named in {errors}")
        with patch.multiple(vocabulary_profile, **overrides):
            with self.assertRaisesRegex(vocabulary_profile.VocabularyProfileInvalid,
                                        rf"^vocabulary_profile_invalid: .*{field}"):
                vocabulary_profile.validate()

    def test_default_profile_is_valid(self) -> None:
        self.assertEqual(vocabulary_profile.validation_errors(), [])

    def test_empty_multiline_or_padded_values_are_refused(self) -> None:
        self.assertRefused("CONTAINER_NAME", CONTAINER_NAME="")
        self.assertRefused("ITEM_NAME_PLURAL", ITEM_NAME_PLURAL="   ")
        self.assertRefused("MEMBER_ID_LABEL", MEMBER_ID_LABEL="Item\nID")
        self.assertRefused("BACKREF_LABEL", BACKREF_LABEL=" Set")
        self.assertRefused("ID_KEY", ID_KEY=None)

    def test_title_must_be_level_one(self) -> None:
        self.assertRefused("RECORD_TITLE", RECORD_TITLE="## Set Record")
        self.assertRefused("RECORD_TITLE", RECORD_TITLE="Set Record")

    def test_summary_and_member_headings_must_be_level_two(self) -> None:
        self.assertRefused("SUMMARY_HEADING", SUMMARY_HEADING="# Set Summary")
        self.assertRefused("SUMMARY_HEADING", SUMMARY_HEADING="### Set Summary")
        self.assertRefused("MEMBER_HEADING", MEMBER_HEADING="Waves")

    def test_labels_refuse_colon_and_backtick(self) -> None:
        self.assertRefused("ID_KEY", ID_KEY="set-id:")
        self.assertRefused("MEMBER_ID_LABEL", MEMBER_ID_LABEL="Wave `ID`")
        self.assertRefused("MEMBER_STATUS_LABEL", MEMBER_STATUS_LABEL="Wave: Status")
        self.assertRefused("BACKREF_LABEL", BACKREF_LABEL="Set`")

    def test_record_filename_must_be_a_bare_markdown_name(self) -> None:
        self.assertRefused("RECORD_FILENAME", RECORD_FILENAME="records/set.md")
        self.assertRefused("RECORD_FILENAME", RECORD_FILENAME="set\\record.md")
        self.assertRefused("RECORD_FILENAME", RECORD_FILENAME="set.txt")

    def test_record_filename_must_not_be_reserved(self) -> None:
        for reserved in ("README.md", "plan-template.md"):
            self.assertRefused("RECORD_FILENAME", RECORD_FILENAME=reserved)

    def test_headings_must_differ(self) -> None:
        self.assertRefused("MEMBER_HEADING", SUMMARY_HEADING="## Waves", MEMBER_HEADING="## Waves")

    def test_headings_must_not_collide_with_fixed_headings(self) -> None:
        self.assertRefused("MEMBER_HEADING", MEMBER_HEADING="## Progress Log")
        self.assertRefused("SUMMARY_HEADING", SUMMARY_HEADING="## Items")

    def test_labels_must_not_collide_with_fixed_labels(self) -> None:
        self.assertRefused("MEMBER_STATUS_LABEL", MEMBER_STATUS_LABEL="Status")
        self.assertRefused("BACKREF_LABEL", BACKREF_LABEL="Depends On")
        self.assertRefused("MEMBER_ID_LABEL", MEMBER_ID_LABEL="Item ID")

    def test_previous_status_label_is_checked_as_derived(self) -> None:
        # The derived label is computed at import; a collision through it is
        # refused under its own name.
        self.assertRefused("PREVIOUS_STATUS_LABEL", PREVIOUS_STATUS_LABEL="Previous Item Status")

    def test_headings_must_not_prefix_each_other(self) -> None:
        # Readers test headings by substring (`MEMBER_HEADING in text`).
        self.assertRefused("MEMBER_HEADING", MEMBER_HEADING="## Set", SUMMARY_HEADING="## Set Summary")
        self.assertRefused("SUMMARY_HEADING", SUMMARY_HEADING="## Members Summary", MEMBER_HEADING="## Members")

    def test_headings_must_not_prefix_a_fixed_heading(self) -> None:
        self.assertRefused("MEMBER_HEADING", MEMBER_HEADING="## Progress")
        self.assertRefused("SUMMARY_HEADING", SUMMARY_HEADING="## Objectives")

    def test_labels_must_not_prefix_each_other(self) -> None:
        self.assertRefused("BACKREF_LABEL", BACKREF_LABEL="Member", MEMBER_ID_LABEL="Member ID",
                           MEMBER_STATUS_LABEL="Entry Status", PREVIOUS_STATUS_LABEL="Previous Entry Status")

    def test_labels_must_not_prefix_a_fixed_label(self) -> None:
        self.assertRefused("MEMBER_STATUS_LABEL", MEMBER_STATUS_LABEL="Stat",
                           PREVIOUS_STATUS_LABEL="Previous Stat")
        self.assertRefused("BACKREF_LABEL", BACKREF_LABEL="Depends On Set")

    def test_labels_must_differ_from_each_other(self) -> None:
        self.assertRefused("BACKREF_LABEL", BACKREF_LABEL="Change ID")
        self.assertRefused("ID_KEY", ID_KEY="Wave")


class DiscoveryDiagnosticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        self.waves = self.root / "docs" / "waves"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _folder(self, name: str, record: str) -> None:
        folder = self.waves / name
        folder.mkdir(parents=True)
        (folder / record).write_text("# Set Record\n\nset-id: `1abcd`\n", encoding="utf-8")

    def test_registered_advisory(self) -> None:
        self.assertEqual(SENSOR_POLARITY_REGISTRY["record_file_not_found"]["polarity"], "advisory")

    def test_fresh_install_is_silent(self) -> None:
        self.assertIsNone(record_paths.record_discovery_mismatch(self.root))
        self.waves.mkdir(parents=True)
        self.assertIsNone(record_paths.record_discovery_mismatch(self.root))
        self.assertEqual(record_discovery_findings(self.root), [])

    def test_matching_record_is_silent(self) -> None:
        self._folder("1abcd first", "wave.md")
        self._folder("1abce second", "set.md")
        self.assertIsNone(record_paths.record_discovery_mismatch(self.root))

    def test_other_record_filename_reports(self) -> None:
        self._folder("1abcd first", "set.md")
        self._folder("1abce second", "set.md")
        message = record_paths.record_discovery_mismatch(self.root)
        self.assertRegex(message, r"^record_file_not_found: the waves root has 2 folder\(s\) but none holds `wave\.md`")
        self.assertEqual(record_discovery_findings(self.root), [f"docs/waves/: {message}"])

    # Change 1z8ql: candidates without a (non-dot) file are ignored.
    def _fileless_shapes(self) -> None:
        (self.waves / "1abcd empty").mkdir(parents=True)
        (self.waves / "group-a" / "inner").mkdir(parents=True)
        (self.waves / "group-b").mkdir(parents=True)
        (self.waves / "group-b" / ".gitkeep").write_text("", encoding="utf-8")
        (self.waves / "group-b" / ".DS_Store").write_bytes(b"\0")

    def test_fileless_folders_are_silent_flat(self) -> None:
        self._fileless_shapes()
        self.assertIsNone(record_paths.record_discovery_mismatch(self.root))
        self.assertEqual(record_discovery_findings(self.root), [])

    def test_fileless_folders_are_silent_nested(self) -> None:
        self._fileless_shapes()
        with patch_layout(modules=(record_paths,), nested=True, max_depth=4):
            self.assertIsNone(record_paths.record_discovery_mismatch(self.root))

    def test_renamed_record_beside_fileless_folders_reports_only_counted_folders(self) -> None:
        self._fileless_shapes()
        self._folder("1abce renamed", "set.md")
        message = record_paths.record_discovery_mismatch(self.root)
        self.assertRegex(message, r"^record_file_not_found: the waves root has 1 folder\(s\) ")

    def test_renamed_nested_leaf_under_fileless_group_reports(self) -> None:
        leaf = self.waves / "group" / "1abcd renamed"
        leaf.mkdir(parents=True)
        (leaf / "set.md").write_text("# Set Record\n", encoding="utf-8")
        with patch_layout(modules=(record_paths,), nested=True, max_depth=4):
            message = record_paths.record_discovery_mismatch(self.root)
        self.assertRegex(message, r"^record_file_not_found: the waves root has 1 folder\(s\) ")
        # Flat layout never looks below the group, which holds no file: silent.
        self.assertIsNone(record_paths.record_discovery_mismatch(self.root))

    def test_unlistable_folder_counts_as_fileless(self) -> None:
        self._folder("1abcd renamed", "set.md")
        leaf = (self.waves / "1abcd renamed").resolve()
        real_scandir = record_paths.os.scandir

        def scandir(path="."):
            # Only the leaf's own listing fails; the candidate walk (which may
            # list the waves root through os.scandir too) is left intact.
            if Path(path).resolve() == leaf:
                raise PermissionError("denied")
            return real_scandir(path)

        # Control: without the failure the renamed record is reported.
        self.assertIsNotNone(record_paths.record_discovery_mismatch(self.root))
        with patch.object(record_paths.os, "scandir", side_effect=scandir):
            self.assertEqual([d.name for d in record_paths.walk_wave_candidates(self.root)], ["1abcd renamed"])
            self.assertIsNone(record_paths.record_discovery_mismatch(self.root))

    def test_server_listing_and_current_wave_report(self) -> None:
        srv = load_server()
        self._folder("1abcd first", "set.md")
        listed = srv.wf_list_waves_response(self.root)
        current = srv.wf_current_wave_response(self.root)
        for response in (listed, current):
            codes = [d.get("code") for d in response.get("diagnostics", [])]
            self.assertIn("record_file_not_found", codes, response)

    def test_server_is_silent_on_a_fresh_install(self) -> None:
        srv = load_server()
        for response in (srv.wf_list_waves_response(self.root), srv.wf_current_wave_response(self.root)):
            codes = [d.get("code") for d in response.get("diagnostics", [])]
            self.assertNotIn("record_file_not_found", codes, response)


class DiscoveryLintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = _docs_lint.DocsLintFixtureTests()

    def test_lint_warns_when_records_use_another_filename(self) -> None:
        root = self.helper.copy_fixture()
        try:
            records = sorted((root / "docs" / "waves").rglob("wave.md"))
            self.assertTrue(records, "fixture holds no wave record")
            for record in records:
                record.rename(record.with_name("set.md"))
            result = self.helper.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertRegex(
            result.stderr,
            r"(?m)^WARNING: docs/waves/: record_file_not_found: .*advisory sensor `record_file_not_found`",
        )
        self.assertNotRegex(result.stderr, r"(?m)^ERROR: .*record_file_not_found")

    def test_lint_is_silent_on_the_fixture(self) -> None:
        root = self.helper.copy_fixture()
        try:
            result = self.helper.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertNotIn("record_file_not_found", result.stderr)


if __name__ == "__main__":
    unittest.main()
