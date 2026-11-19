"""Finite ownership, generation and descriptor-bound deletion controls."""
from __future__ import annotations

import errno
import base64
import copy
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import wave_work as work  # noqa: E402
import vocabulary_profile as vp  # noqa: E402
from gardener_metadata import canonical_review_policy_body  # noqa: E402
from record_layout_support import default_profile_only, patch_layout, waves_dir, waves_rel  # noqa: E402


@unittest.skipUnless(work._SAFE_DELETE, "descriptor-safe work I/O unavailable")
class WaveWorkTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wf-work-")).resolve()
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.wave = waves_dir(self.root) / "abc12 example" / vp.RECORD_FILENAME
        self.wave.parent.mkdir(parents=True)
        self.wave.write_text("# Wave\n")
        self.path = self.root / work.WORK_ROOT / "abc12"
        self.outside = self.base / "outside"
        self.outside.mkdir()
        self.secret = self.outside / "keep.txt"
        self.secret.write_text("keep")

    def ensure(self):
        result = work.ensure_work(self.root, self.wave)
        self.assertTrue(result["available"], result)
        return result["generation"]

    def cleanup(self, generation):
        return work.cleanup_work(self.root, self.wave, expected_generation=generation)

    def test_reads_create_nothing_and_missing_cleanup_is_noop(self):
        self.assertFalse(work.describe_work(self.root, self.wave)["available"])
        self.assertFalse((self.root / ".wavefoundry").exists())
        self.assertEqual(self.cleanup(None)["outcome"], "absent")
        self.assertFalse((self.root / ".wavefoundry").exists())

    def test_same_wave_shared_distinct_waves_isolated_and_durable_records_retained(self):
        generation = self.ensure()
        (self.path / "scratch").mkdir()
        (self.path / "scratch/probe").write_text("temporary")
        other = self.wave.parent.parent / "abc13 other" / vp.RECORD_FILENAME
        other.parent.mkdir()
        other.write_text("# Other\n")
        second = work.ensure_work(self.root, other)
        self.assertEqual(work.describe_work(self.root, self.wave)["generation"], generation)
        self.assertEqual(work.ensure_work(self.root, self.wave)["generation"], generation)
        self.assertNotEqual(second["path"], work.describe_work(self.root, self.wave)["path"])
        self.assertEqual(self.cleanup(generation)["outcome"], "removed")
        self.assertFalse(self.path.exists())
        self.assertTrue((self.root / second["path"]).is_dir())
        self.assertTrue(self.wave.is_file())
        self.assertEqual(self.cleanup(generation)["outcome"], "absent")

    def test_empty_preexisting_directory_is_never_adopted(self):
        self.path.mkdir(parents=True)
        self.assertFalse(work.ensure_work(self.root, self.wave)["available"])
        self.assertEqual(self.cleanup(None)["outcome"], "preserved")
        self.assertEqual(list(self.path.iterdir()), [])

    def test_malformed_repository_wrong_wave_or_directory_identity_is_preserved(self):
        for field, value in [("repository", "elsewhere"), ("wave", waves_rel("abc13", vp.RECORD_FILENAME)),
                             ("directory", [0, 0])]:
            with self.subTest(field=field):
                generation = self.ensure()
                marker = self.path / work.OWNER_FILE
                owner = json.loads(marker.read_text())
                original = owner[field]
                owner[field] = value
                marker.write_text(json.dumps(owner))
                self.assertFalse(work.describe_work(self.root, self.wave)["available"])
                self.assertEqual(self.cleanup(generation)["outcome"], "preserved")
                owner[field] = original
                marker.write_text(json.dumps(owner))

    def test_schema_two_repository_spelling_is_history_with_verified_root_identity(self):
        generation = self.ensure()
        marker = self.path / work.OWNER_FILE
        owner = json.loads(marker.read_text())
        owner["repository"] = str(self.outside)
        marker.write_text(json.dumps(owner))
        before = marker.read_bytes()
        self.assertEqual(work.describe_work(self.root, self.wave)["generation"], generation)
        self.assertEqual(marker.read_bytes(), before)

    def test_unknown_generation_never_discovers_cleanup_authority(self):
        generation = self.ensure()
        self.assertEqual(self.cleanup(None)["outcome"], "preserved")
        self.assertEqual(self.cleanup("0" * 32)["outcome"], "preserved")
        self.assertEqual(work.describe_work(self.root, self.wave)["generation"], generation)

    def test_device_drift_keeps_adoption_available_without_restamping(self):
        generation = self.ensure()
        marker = self.path / work.OWNER_FILE
        owner = json.loads(marker.read_text())
        owner["directory"][0] += 1
        owner["repository_directory"][0] += 1
        marker.write_text(json.dumps(owner))
        before = marker.read_bytes()
        for result in (work.describe_work(self.root, self.wave),
                       work.ensure_work(self.root, self.wave)):
            self.assertTrue(result["available"], result)
            self.assertEqual(result["generation"], generation)
            self.assertEqual(marker.read_bytes(), before)

    def test_root_rename_uses_persisted_identity_without_restamping(self):
        generation = self.ensure()
        tail = self.wave.relative_to(self.root)
        before = (self.path / work.OWNER_FILE).read_bytes()
        moved = self.root.with_name("renamed")
        self.root.rename(moved)
        self.root, self.wave = moved, moved / tail
        self.path = moved / work.WORK_ROOT / "abc12"
        self.assertEqual(work.describe_work(moved, self.wave)["generation"], generation)
        self.assertEqual(work.ensure_work(moved, self.wave)["generation"], generation)
        self.assertEqual((self.path / work.OWNER_FILE).read_bytes(), before)
        self.assertEqual(self.cleanup(generation)["outcome"], "removed")

    def test_actual_case_alias_is_accepted_without_case_folding_foreign_roots(self):
        generation = self.ensure()
        alias = self.root.with_name("REPO")
        if not alias.exists():
            self.skipTest("filesystem has distinct case spellings")
        self.assertTrue(os.path.samefile(alias, self.root))
        result = work.describe_work(alias, alias / self.wave.relative_to(self.root))
        self.assertEqual(result.get("generation"), generation, result)

    def test_moved_work_alone_cannot_transfer_repository_ownership(self):
        generation = self.ensure()
        foreign = self.base / "foreign"
        foreign_wave = foreign / self.wave.relative_to(self.root)
        foreign_wave.parent.mkdir(parents=True)
        foreign_wave.write_bytes(self.wave.read_bytes())
        destination = foreign / work.WORK_ROOT / "abc12"
        destination.parent.mkdir(parents=True)
        self.path.rename(destination)
        marker = destination / work.OWNER_FILE
        before = marker.read_bytes()
        self.assertFalse(work.describe_work(foreign, foreign_wave)["available"])
        self.assertFalse(work.ensure_work(foreign, foreign_wave)["available"])
        result = work.cleanup_work(foreign, foreign_wave, expected_generation=generation)
        self.assertEqual(result["outcome"], "preserved")
        self.assertEqual(marker.read_bytes(), before)

    def test_legacy_same_root_remains_usable_but_unprovable_rename_preserves(self):
        generation = self.ensure()
        marker = self.path / work.OWNER_FILE
        owner = json.loads(marker.read_text())
        owner["schema"] = 1
        owner.pop("repository_directory")
        marker.write_text(json.dumps(owner))
        original = marker.read_bytes()
        self.assertEqual(work.describe_work(self.root, self.wave)["generation"], generation)
        self.assertEqual(marker.read_bytes(), original)
        tail = self.wave.relative_to(self.root)
        before = marker.read_bytes()
        moved = self.root.with_name("legacy-renamed")
        self.root.rename(moved)
        wave = moved / tail
        for result in (work.describe_work(moved, wave), work.ensure_work(moved, wave),
                       work.cleanup_work(moved, wave, expected_generation=generation)):
            self.assertFalse(result["available"], result)
            self.assertIn("move retained work aside", result["notice"])
        self.assertEqual((moved / work.WORK_ROOT / "abc12" / work.OWNER_FILE).read_bytes(), before)

    def test_invalid_root_identity_never_grants_ownership(self):
        generation = self.ensure()
        marker = self.path / work.OWNER_FILE
        owner = json.loads(marker.read_text())
        device, inode = owner["repository_directory"]
        for value in ([device, inode + 1], [device, 0], [True, inode], [device, True], None, [], [device]):
            with self.subTest(root_identity=value):
                owner["repository_directory"] = value
                marker.write_text(json.dumps(owner))
                before = marker.read_bytes()
                self.assertFalse(work.describe_work(self.root, self.wave)["available"])
                self.assertEqual(self.cleanup(generation)["outcome"], "preserved")
                self.assertEqual(marker.read_bytes(), before)

    def test_invalid_directory_records_refuse_reads_and_cleanup_without_mutation(self):
        generation = self.ensure()
        marker = self.path / work.OWNER_FILE
        owner = json.loads(marker.read_text())
        device, inode = owner["directory"]
        scratch = self.path / "keep.txt"
        scratch.write_bytes(b"retained scratch")
        invalid = ([device, inode + 1], [device, 0], [0, 0], [], [device],
                   [device, inode, 1], None, {}, "directory", [True, inode],
                   [device, True], [-1, inode], [device, -1], [1.0, inode],
                   [device, str(inode)])
        for value in invalid:
            with self.subTest(directory=value):
                owner["directory"] = value
                marker.write_text(json.dumps(owner))
                before = marker.read_bytes()
                read = work.describe_work(self.root, self.wave)
                self.assertFalse(read["available"], read)
                self.assertIn("work_ownership_unproven", read["notice"])
                cleanup = self.cleanup(generation)
                self.assertEqual(cleanup["outcome"], "preserved", cleanup)
                self.assertIn("work_ownership_unproven", cleanup["notice"])
                self.assertEqual(marker.read_bytes(), before)
                self.assertEqual(scratch.read_bytes(), b"retained scratch")

    def test_zero_live_inode_is_never_path_only_ownership(self):
        self.ensure()
        fd = os.open(self.path, work._FLAGS)
        self.addCleanup(os.close, fd)
        directory = os.fstat(fd)
        unavailable = mock.Mock(st_dev=directory.st_dev, st_ino=0)
        with self.assertRaisesRegex(work._Refused, "work_ownership_unproven"):
            work._read_owner(fd, self.root, self.wave.relative_to(self.root).as_posix(), unavailable)

    def test_reopen_rotates_generation_retains_files_and_refuses_stale_cleanup(self):
        old = self.ensure()
        (self.path / "retained").write_text("retained")
        reopened = work.ensure_work(self.root, self.wave, reopen=True)
        self.assertNotEqual(old, reopened["generation"])
        self.assertIn("retained", reopened["notice"])
        self.assertEqual(self.cleanup(old)["outcome"], "preserved")
        self.assertEqual((self.path / "retained").read_text(), "retained")
        self.assertEqual(self.cleanup(reopened["generation"])["outcome"], "removed")

    def test_linked_parent_and_work_directory_are_refused(self):
        parent = self.root / ".wavefoundry"
        parent.symlink_to(self.outside, target_is_directory=True)
        self.assertFalse(work.ensure_work(self.root, self.wave)["available"])
        self.assertEqual(self.cleanup(None)["outcome"], "preserved")
        self.assertFalse((self.outside / "work").exists())
        parent.unlink()
        self.path.parent.mkdir(parents=True)
        self.path.symlink_to(self.outside, target_is_directory=True)
        self.assertFalse(work.ensure_work(self.root, self.wave)["available"])
        self.assertEqual(self.cleanup(None)["outcome"], "preserved")
        self.assertEqual(self.secret.read_text(), "keep")

    def test_nested_links_are_unlinked_never_followed_and_nested_owner_names_removed(self):
        generation = self.ensure()
        (self.path / "link").symlink_to(self.outside, target_is_directory=True)
        (self.path / "nested").mkdir()
        (self.path / "nested" / work.OWNER_FILE).write_text("ordinary scratch")
        self.assertEqual(self.cleanup(generation)["outcome"], "removed")
        self.assertEqual(self.secret.read_text(), "keep")

    def test_marker_symlink_or_special_file_cannot_be_read_as_ownership(self):
        generation = self.ensure()
        marker = self.path / work.OWNER_FILE
        marker.unlink()
        marker.symlink_to(self.secret)
        self.assertEqual(self.cleanup(generation)["outcome"], "preserved")
        self.assertEqual(self.secret.read_text(), "keep")
        marker.unlink()
        os.mkfifo(marker)
        self.assertFalse(work.describe_work(self.root, self.wave)["available"])

    def test_wave_traversal_link_and_invalid_identifier_are_refused(self):
        self.assertFalse(work.ensure_work(self.root, Path("..") / "outside" / vp.RECORD_FILENAME)["available"])
        link = self.root / "alias"
        link.symlink_to(self.wave.parent, target_is_directory=True)
        self.assertFalse(work.ensure_work(self.root, link / vp.RECORD_FILENAME)["available"])
        invalid = waves_dir(self.root) / "not-an-id" / vp.RECORD_FILENAME
        invalid.parent.mkdir()
        invalid.write_text("# Invalid\n")
        self.assertFalse(work.ensure_work(self.root, invalid)["available"])
        self.assertFalse((self.root / ".wavefoundry").exists())

    def test_configured_root_alias_accepts_lexical_wave_tail_without_following_inner_links(self):
        alias = self.base / "configured-root"
        alias.symlink_to(self.root, target_is_directory=True)
        aliased_wave = alias / self.wave.relative_to(self.root)
        established = work.ensure_work(alias, aliased_wave)
        self.assertTrue(established["available"], established)
        self.assertEqual(work.describe_work(self.root, self.wave)["generation"], established["generation"])
        self.assertEqual(work.describe_work(alias, aliased_wave)["generation"], established["generation"])
        inner = self.root / "inner"
        inner.symlink_to(self.wave.parent, target_is_directory=True)
        refused = work.ensure_work(alias, alias / "inner" / vp.RECORD_FILENAME)
        self.assertFalse(refused["available"], refused)
        foreign = self.base / "foreign/abc12 example" / vp.RECORD_FILENAME
        foreign.parent.mkdir(parents=True)
        foreign.write_text("# Foreign\n")
        self.assertFalse(work.ensure_work(alias, foreign)["available"])
        result = work.cleanup_work(alias, aliased_wave, expected_generation=established["generation"])
        self.assertEqual(result["outcome"], "removed")
        self.assertTrue(self.wave.is_file())

    def test_nondefault_record_filename_and_roots_support_full_work_and_snapshot_lifetime(self):
        from review_policy import build_review_context
        with patch_layout(WAVES_ROOT="planning/iterations", PLANS_ROOT="planning/changes"), \
                mock.patch.object(vp, "RECORD_FILENAME", "iteration.md"):
            record = waves_dir(self.root) / "abc14 portable" / vp.RECORD_FILENAME
            record.parent.mkdir(parents=True)
            record.write_text("# Portable record\n")
            established = work.ensure_work(self.root, record)
            self.assertTrue(established["available"], established)
            self.assertEqual(work.describe_work(self.root, record)["generation"], established["generation"])
            documents = {"abc99-enh portable": b"# Plan\r\n\r\n## Requirements\r\nPortable.\r\n"}
            receipt = {"receipt_id": "review-policy-" + "4" * 20, "policy_input_digest": "5" * 64,
                       "review_context": build_review_context(documents), "policy_inputs": {"changes": [
                           {"change_id": key, "kind": "enh", "sha256": hashlib.sha256(canonical_review_policy_body(body)).hexdigest()}
                           for key, body in documents.items()]}}
            self.assertTrue(work.publish_snapshot(self.root, record, receipt, documents)["available"])
            self.assertEqual(work.read_snapshot(self.root, record, receipt)["documents"], documents)
            reopened = work.ensure_work(self.root, record, reopen=True)
            self.assertNotEqual(reopened["generation"], established["generation"])
            self.assertEqual(work.cleanup_work(self.root, record, expected_generation=established["generation"])["outcome"], "preserved")
            self.assertEqual(work.cleanup_work(self.root, record, expected_generation=reopened["generation"])["outcome"], "removed")
            self.assertTrue(record.is_file())

    def test_directory_substitution_before_cleanup_preserves_replacement(self):
        generation = self.ensure()
        (self.path / "original").write_text("original")
        moved = self.path.with_name("moved")
        def swap(stage):
            if stage == "cleanup":
                self.path.rename(moved)
                self.path.mkdir()
                (self.path / "replacement").write_text("replacement")
        with mock.patch.object(work, "_checkpoint", side_effect=swap):
            self.assertEqual(self.cleanup(generation)["outcome"], "preserved")
        self.assertEqual((moved / "original").read_text(), "original")
        self.assertEqual((self.path / "replacement").read_text(), "replacement")

    def test_substitution_after_mkdir_never_adopts_replacement(self):
        def swap(stage):
            if stage == "created":
                self.path.rename(self.path.with_name("moved"))
                self.path.mkdir()
                (self.path / "foreign").write_text("foreign")
        with mock.patch.object(work, "_checkpoint", side_effect=swap):
            self.assertFalse(work.ensure_work(self.root, self.wave)["available"])
        self.assertEqual((self.path / "foreign").read_text(), "foreign")
        self.assertFalse((self.path / work.OWNER_FILE).exists())

    def test_parent_substitution_before_unlink_preserves_external_target(self):
        generation = self.ensure()
        (self.path / "probe").write_text("probe")
        parent = self.path.parent
        moved = parent.with_name("retained-work")
        changed = False
        def swap(stage):
            nonlocal changed
            if stage == "unlink" and not changed:
                changed = True
                parent.rename(moved)
                parent.symlink_to(self.outside, target_is_directory=True)
        with mock.patch.object(work, "_checkpoint", side_effect=swap):
            self.assertEqual(self.cleanup(generation)["outcome"], "preserved")
        self.assertEqual((moved / "abc12/probe").read_text(), "probe")
        self.assertEqual(self.secret.read_text(), "keep")

    def test_regular_parent_substitution_before_unlink_preserves_moved_work(self):
        generation = self.ensure()
        (self.path / "proof.txt").write_text("retain moved owned work")
        parent = self.path.parent
        moved = parent.with_name("retained-work")
        changed = False
        def swap(stage):
            nonlocal changed
            if stage == "unlink" and not changed:
                changed = True
                # A regular replacement isolates the parent identity guard;
                # a link would also be refused by the no-follow directory walk.
                parent.rename(moved)
                parent.mkdir()
        with mock.patch.object(work, "_checkpoint", side_effect=swap):
            result = self.cleanup(generation)
        self.assertTrue(changed, "control did not reach the unlink boundary")
        self.assertEqual(result["outcome"], "preserved")
        self.assertEqual(result["notice"], "work_parent_changed; work preserved")
        self.assertTrue(parent.is_dir())
        self.assertFalse(parent.is_symlink())
        self.assertEqual(list(parent.iterdir()), [])
        self.assertEqual((moved / "abc12/proof.txt").read_text(), "retain moved owned work")
        self.assertEqual(self.wave.read_text(), "# Wave\n")

    def test_child_substitution_before_unlink_is_refused(self):
        generation = self.ensure()
        target = self.path / "probe"
        target.write_text("probe")
        def swap(stage):
            if stage == "unlink":
                target.rename(self.path / "original")
                target.symlink_to(self.secret)
        with mock.patch.object(work, "_checkpoint", side_effect=swap):
            self.assertEqual(self.cleanup(generation)["outcome"], "preserved")
        self.assertTrue(target.is_symlink())
        self.assertEqual(self.secret.read_text(), "keep")

    def test_partial_unlink_failure_keeps_ownership_for_retry(self):
        generation = self.ensure()
        (self.path / "probe").write_text("probe")
        with mock.patch.object(work.os, "unlink", side_effect=PermissionError(errno.EACCES, "denied")):
            result = self.cleanup(generation)
        self.assertEqual(result["outcome"], "preserved")
        self.assertIn("EACCES", result["notice"])
        self.assertEqual(work.describe_work(self.root, self.wave)["generation"], generation)
        self.assertEqual(self.cleanup(generation)["outcome"], "removed")

    def test_late_rmdir_failure_restores_owner_for_retry(self):
        generation = self.ensure()
        real = os.rmdir
        def fail_top(name, *args, **kwargs):
            if name == "abc12":
                raise PermissionError(errno.EACCES, "denied")
            return real(name, *args, **kwargs)
        with mock.patch.object(work.os, "rmdir", side_effect=fail_top):
            self.assertEqual(self.cleanup(generation)["outcome"], "preserved")
        self.assertEqual(work.describe_work(self.root, self.wave)["generation"], generation)
        self.assertEqual(self.cleanup(generation)["outcome"], "removed")

    def _post_unlink_failure(self, *, rmdir_fails, anchor_exc=None, entry_exc=None):
        """Inject a failure after `.owner.json` is unlinked (change 22qr4)."""
        generation = self.ensure()
        state = {"unlinked": False}
        real_unlink, real_rmdir = os.unlink, os.rmdir
        real_anchor, real_entry = work._anchor, work._entry

        def unlink(name, *args, **kwargs):
            real_unlink(name, *args, **kwargs)
            if name == work.OWNER_FILE:
                state["unlinked"] = True

        def rmdir(name, *args, **kwargs):
            if rmdir_fails and name == "abc12":
                state["rmdir_failed"] = True
                raise PermissionError(errno.EACCES, "denied")
            return real_rmdir(name, *args, **kwargs)

        def anchor(*args, **kwargs):
            if anchor_exc is not None and state.get("rmdir_failed"):
                raise anchor_exc
            return real_anchor(*args, **kwargs)

        def entry(*args, **kwargs):
            if entry_exc is not None and state["unlinked"]:
                raise entry_exc
            return real_entry(*args, **kwargs)

        with mock.patch.object(work.os, "unlink", side_effect=unlink), \
                mock.patch.object(work.os, "rmdir", side_effect=rmdir), \
                mock.patch.object(work, "_anchor", side_effect=anchor), \
                mock.patch.object(work, "_entry", side_effect=entry):
            result = self.cleanup(generation)
        self.assertTrue(state["unlinked"])
        self.assertEqual(result["outcome"], "preserved", result)
        self.assertNotIn("owner_restore", result)
        self.assertTrue((self.path / work.OWNER_FILE).is_file())
        self.assertEqual(work.describe_work(self.root, self.wave)["generation"], generation)
        self.assertEqual(self.cleanup(generation)["outcome"], "removed")
        self.assertFalse(self.path.exists())
        return result

    def test_rmdir_failure_then_anchor_refusal_restores_owner(self):
        result = self._post_unlink_failure(
            rmdir_fails=True, anchor_exc=work._Refused("work_parent_changed; work preserved"))
        self.assertIn("EACCES", result["notice"])

    def test_entry_refusal_before_rmdir_restores_owner(self):
        result = self._post_unlink_failure(
            rmdir_fails=False, entry_exc=work._Refused("work_identity_changed; work preserved"))
        self.assertIn("work_identity_changed", result["notice"])

    def test_rmdir_failure_then_anchor_oserror_restores_owner(self):
        result = self._post_unlink_failure(
            rmdir_fails=True, anchor_exc=OSError(errno.EIO, "io"))
        self.assertIn("EACCES", result["notice"])

    def test_post_unlink_not_found_is_preserved_not_absent(self):
        result = self._post_unlink_failure(
            rmdir_fails=False, entry_exc=FileNotFoundError(errno.ENOENT, "gone"))
        self.assertIn("ENOENT", result["notice"])

    def test_failed_owner_restore_keeps_original_refusal_and_reports_restore(self):
        generation = self.ensure()
        real_entry = work._entry
        state = {"unlinked": False}
        real_unlink = os.unlink

        def unlink(name, *args, **kwargs):
            real_unlink(name, *args, **kwargs)
            if name == work.OWNER_FILE:
                state["unlinked"] = True

        def entry(*args, **kwargs):
            if state["unlinked"]:
                raise work._Refused("work_identity_changed; work preserved")
            return real_entry(*args, **kwargs)

        with mock.patch.object(work.os, "unlink", side_effect=unlink), \
                mock.patch.object(work, "_entry", side_effect=entry), \
                mock.patch.object(work, "_write_owner", side_effect=OSError(errno.ENOSPC, "full")):
            result = self.cleanup(generation)
        self.assertEqual(result["outcome"], "preserved")
        self.assertIn("work_identity_changed", result["notice"])
        self.assertEqual(result["owner_restore"], "failed:ENOSPC")
        self.assertTrue(self.path.is_dir())

    def test_unsupported_host_preserves_with_explicit_notice(self):
        generation = self.ensure()
        with mock.patch.object(work, "_SAFE_DELETE", False):
            self.assertFalse(work.ensure_work(self.root, self.wave)["available"])
            result = self.cleanup(generation)
        self.assertEqual(result["outcome"], "preserved")
        self.assertIn("unsupported", result["notice"])
        self.assertTrue(self.path.is_dir())

    def test_unsupported_host_absent_cleanup_still_succeeds(self):
        with mock.patch.object(work, "_SAFE_DELETE", False):
            self.assertEqual(self.cleanup(None)["outcome"], "absent")
        self.assertFalse((self.root / ".wavefoundry").exists())


@unittest.skipUnless(work._SAFE_DELETE, "descriptor-safe work I/O unavailable")
class SnapshotTests(unittest.TestCase):
    setUp = WaveWorkTests.setUp
    ensure = WaveWorkTests.ensure

    def setUp(self):
        WaveWorkTests.setUp(self)
        patch = mock.patch.object(work, "_snapshot_normalizer", return_value="a" * 64)
        patch.start()
        self.addCleanup(patch.stop)
        self.body = b"# Plan\r\n\r\n## Requirements\r\nKeep exact bytes.\r\n"
        self.documents = {"abc99-enh example": self.body}
        self.receipt = self.receipt_for(self.documents)
        self.snapshot = self.path / "receipts" / (self.receipt["receipt_id"] + ".json")

    def receipt_for(self, documents):
        return {"receipt_id": "review-policy-" + "1" * 20, "policy_input_digest": "2" * 64,
                "policy_inputs": {"changes": [
                    {"change_id": key, "kind": "enh", "sha256": hashlib.sha256(canonical_review_policy_body(body)).hexdigest()}
                    for key, body in documents.items()]},
                "review_context": {"version": 1, "normalizer_sha256": "a" * 64,
                                   "documents": [{"change_id": key, "raw_sha256": hashlib.sha256(body).hexdigest(),
                                                  "sections": []} for key, body in documents.items()]}}

    def publish(self, receipt=None, documents=None):
        return work.publish_snapshot(self.root, self.wave, receipt or self.receipt,
                                     documents if documents is not None else self.documents)

    def read(self, receipt=None):
        return work.read_snapshot(self.root, self.wave, receipt or self.receipt)

    def test_exact_crlf_round_trip_and_multiple_document_identity(self):
        documents = dict(self.documents, second=b"# Second\n")
        receipt = self.receipt_for(documents)
        self.assertTrue(self.publish(receipt, documents)["available"])
        result = self.read(receipt)
        self.assertTrue(result["available"], result)
        self.assertEqual(result["documents"], documents)
        self.assertIn(b"\r\n", result["documents"]["abc99-enh example"])

    def test_snapshot_written_before_device_drift_still_loads_without_restamping(self):
        self.assertTrue(self.publish()["available"])
        marker = self.path / work.OWNER_FILE
        owner = json.loads(marker.read_text())
        owner["directory"][0] += 1
        owner["repository_directory"][0] += 1
        marker.write_text(json.dumps(owner))
        before = marker.read_bytes()
        snapshot_before = self.snapshot.read_bytes()
        result = self.read()
        self.assertTrue(result["available"], result)
        self.assertEqual(result["documents"], self.documents)
        self.assertEqual(marker.read_bytes(), before)
        self.assertEqual(self.snapshot.read_bytes(), snapshot_before)

    def test_interrupted_post_link_unlink_keeps_snapshot_readable_and_immutable(self):
        real = os.unlink
        def interrupt(name, *args, **kwargs):
            if str(name).startswith(".snapshot-"):
                raise PermissionError(errno.EACCES, "interrupted cleanup")
            return real(name, *args, **kwargs)
        with mock.patch.object(work.os, "unlink", side_effect=interrupt):
            self.assertFalse(self.publish()["available"])
        temporary, = self.snapshot.parent.glob(".snapshot-*.tmp")
        self.assertEqual(self.snapshot.stat().st_nlink, 2)
        before = {p.name: p.read_bytes() for p in self.snapshot.parent.iterdir()}
        result = self.read()
        self.assertTrue(result["available"], result)
        self.assertEqual(result["documents"], self.documents)
        self.assertEqual({p.name: p.read_bytes() for p in self.snapshot.parent.iterdir()}, before)
        self.assertIn("immutable", self.publish()["notice"])
        self.assertTrue(temporary.exists())
        self.assertEqual(self.snapshot.read_bytes(), before[self.snapshot.name])

    def test_active_publisher_unlink_race_reads_without_mutating(self):
        self.assertTrue(self.publish()["available"])
        temporary = self.snapshot.parent / (".snapshot-" + "a" * 32 + ".tmp")
        os.link(self.snapshot, temporary)
        def finish(stage):
            if stage == "snapshot_link":
                temporary.unlink(missing_ok=True)
        with mock.patch.object(work, "_checkpoint", side_effect=finish):
            result = self.read()
        self.assertTrue(result["available"], result)
        self.assertEqual(result["documents"], self.documents)
        self.assertEqual(self.snapshot.stat().st_nlink, 1)

    def test_concurrent_publisher_read_and_collision_keep_first_bytes(self):
        linked, release = threading.Event(), threading.Event()
        results, errors = [], []
        real = os.unlink
        def hold(name, *args, **kwargs):
            if threading.current_thread() is publisher and str(name).startswith(".snapshot-"):
                linked.set()
                if not release.wait(10):
                    raise AssertionError("publisher not released")
            return real(name, *args, **kwargs)
        def publish():
            try:
                results.append(self.publish())
            except BaseException as exc:
                errors.append(exc)
        publisher = threading.Thread(target=publish, daemon=True)
        with mock.patch.object(work.os, "unlink", side_effect=hold):
            publisher.start()
            try:
                self.assertTrue(linked.wait(10), "publisher did not commit its link")
                self.assertEqual(self.snapshot.stat().st_nlink, 2)
                before = self.snapshot.read_bytes()
                self.assertEqual(self.read()["documents"], self.documents)
                collision = self.publish()
                self.assertIn("snapshot_exists", collision["notice"])
                self.assertEqual(self.snapshot.read_bytes(), before)
            finally:
                release.set()
                publisher.join(10)
        self.assertFalse(publisher.is_alive())
        self.assertFalse(errors, errors)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["available"], results)
        self.assertEqual(self.snapshot.stat().st_nlink, 1)
        self.assertEqual(self.read()["documents"], self.documents)

    def test_unknown_external_excess_and_symlink_links_refuse(self):
        self.assertTrue(self.publish()["available"])
        internal = self.snapshot.parent / (".snapshot-" + "a" * 32 + ".tmp")
        external = self.outside / "external.json"
        unknown = self.snapshot.parent / ".snapshot-not-a-uuid.tmp"
        for case in ("external", "unknown", "excess", "symlink"):
            with self.subTest(case=case):
                if case in ("external", "symlink", "excess"):
                    os.link(self.snapshot, external)
                if case in ("excess",):
                    os.link(self.snapshot, internal)
                if case == "unknown":
                    os.link(self.snapshot, unknown)
                if case == "symlink":
                    internal.symlink_to(external)
                try:
                    before = self.snapshot.read_bytes()
                    result = self.read()
                    self.assertFalse(result["available"], result)
                    self.assertIn("snapshot_file_unproven", result["notice"])
                    self.assertNotIn("documents", result)
                    self.assertEqual(self.snapshot.read_bytes(), before)
                finally:
                    internal.unlink(missing_ok=True)
                    external.unlink(missing_ok=True)
                    unknown.unlink(missing_ok=True)

    def test_recovered_link_still_checks_receipt_integrity(self):
        self.assertTrue(self.publish()["available"])
        temporary = self.snapshot.parent / (".snapshot-" + "a" * 32 + ".tmp")
        os.link(self.snapshot, temporary)
        bad = copy.deepcopy(self.receipt)
        bad["review_context"]["documents"][0]["raw_sha256"] = "f" * 64
        self.assertIn("raw_integrity", self.read(bad)["notice"])
        self.assertTrue(temporary.exists())

    def test_publisher_unlink_with_new_external_link_does_not_reuse_stale_proof(self):
        self.assertTrue(self.publish()["available"])
        temporary = self.snapshot.parent / (".snapshot-" + "a" * 32 + ".tmp")
        external = self.outside / "foreign-link.json"
        os.link(self.snapshot, temporary)
        def replace(stage):
            if stage == "snapshot_link_verified" and temporary.exists():
                temporary.unlink()
                os.link(self.snapshot, external)
        with mock.patch.object(work, "_checkpoint", side_effect=replace):
            result = self.read()
        self.assertFalse(result["available"], result)
        self.assertIn("snapshot_file_unproven", result["notice"])
        self.assertTrue(external.exists())

    def test_snapshot_survives_root_rename_and_both_device_history_changes(self):
        self.assertTrue(self.publish()["available"])
        marker = self.path / work.OWNER_FILE
        owner = json.loads(marker.read_text())
        owner["directory"][0] += 1
        owner["repository_directory"][0] += 1
        marker.write_text(json.dumps(owner))
        before = marker.read_bytes()
        tail = self.wave.relative_to(self.root)
        moved = self.root.with_name("snapshot-renamed")
        self.root.rename(moved)
        result = work.read_snapshot(moved, moved / tail, self.receipt)
        self.assertTrue(result["available"], result)
        self.assertEqual(result["documents"], self.documents)
        self.assertEqual((moved / work.WORK_ROOT / "abc12" / work.OWNER_FILE).read_bytes(), before)

    def test_missing_or_legacy_baseline_never_creates_work(self):
        result = self.read()
        self.assertFalse(result["available"])
        self.assertNotIn("documents", result)
        legacy = copy.deepcopy(self.receipt)
        legacy.pop("review_context")
        self.assertIn("metadata_unavailable", self.read(legacy)["notice"])
        self.assertFalse((self.root / ".wavefoundry").exists())

    def test_exclusive_publication_preserves_first_reviewed_bytes(self):
        self.assertTrue(self.publish()["available"])
        first = self.snapshot.read_bytes()
        other = {key: body.replace(b"\r\n", b"\n") for key, body in self.documents.items()}
        result = self.publish(self.receipt_for(other), other)
        self.assertFalse(result["available"])
        self.assertIn("immutable", result["notice"])
        self.assertEqual(self.snapshot.read_bytes(), first)
        self.assertEqual(self.read()["documents"], self.documents)
        self.assertFalse(any(self.snapshot.parent.glob(".snapshot-*")))

    def test_raw_and_canonical_hash_checks_are_both_required(self):
        bad_raw = copy.deepcopy(self.receipt)
        bad_raw["review_context"]["documents"][0]["raw_sha256"] = "f" * 64
        self.assertIn("raw_integrity", self.publish(bad_raw)["notice"])
        bad_canonical = copy.deepcopy(self.receipt)
        bad_canonical["policy_inputs"]["changes"][0]["sha256"] = "f" * 64
        self.assertIn("canonical_integrity", self.publish(bad_canonical)["notice"])
        self.assertFalse(self.path.exists())

    def test_reader_rejects_raw_tracking_corruption_even_when_canonical_digest_matches(self):
        self.assertTrue(self.publish()["available"])
        payload = json.loads(self.snapshot.read_bytes())
        key = next(iter(self.documents))
        altered = self.body.replace(b"\r\n", b"\n")
        self.assertEqual(canonical_review_policy_body(self.body), canonical_review_policy_body(altered))
        payload["documents"][key] = base64.b64encode(altered).decode("ascii")
        self.snapshot.write_text(json.dumps(payload))
        result = self.read()
        self.assertFalse(result["available"])
        self.assertIn("raw_integrity", result["notice"])
        self.assertNotIn("documents", result)

    def test_wrong_receipt_digest_document_set_and_normalizer_are_rejected(self):
        self.assertTrue(self.publish()["available"])
        altered = copy.deepcopy(self.receipt)
        altered["policy_input_digest"] = "3" * 64
        self.assertIn("binding_mismatch", self.read(altered)["notice"])
        altered = copy.deepcopy(self.receipt)
        altered["review_context"]["normalizer_sha256"] = "f" * 64
        self.assertIn("normalizer_mismatch", self.read(altered)["notice"])
        altered = copy.deepcopy(self.receipt)
        altered["review_context"]["documents"][0]["change_id"] = "foreign"
        self.assertIn("identity_mismatch", self.read(altered)["notice"])

    def test_corrupt_duplicate_keys_or_oversized_cache_falls_back(self):
        self.assertTrue(self.publish()["available"])
        original = self.snapshot.read_bytes()
        for corrupt in [b"{", b'{"version":1,"version":1}', b"x" * (work.SNAPSHOT_MAX_BYTES + 1)]:
            with self.subTest(size=len(corrupt)):
                self.snapshot.write_bytes(corrupt)
                self.assertFalse(self.read()["available"])
        self.snapshot.write_bytes(original)
        self.assertTrue(self.read()["available"])

    def test_oversized_publication_and_document_set_mismatch_create_nothing(self):
        with mock.patch.object(work, "SNAPSHOT_MAX_BYTES", 16):
            self.assertIn("oversized", self.publish()["notice"])
        self.assertIn("identity_mismatch", self.publish(documents={})["notice"])
        self.assertFalse((self.root / ".wavefoundry").exists())

    def test_receipt_identifier_cannot_choose_an_arbitrary_path(self):
        altered = copy.deepcopy(self.receipt)
        altered["receipt_id"] = "../../outside/keep.txt"
        self.assertFalse(self.publish(altered)["available"])
        self.assertFalse(self.read(altered)["available"])
        self.assertEqual(self.secret.read_text(), "keep")
        self.assertFalse((self.root / ".wavefoundry").exists())

    def test_snapshot_or_receipts_directory_link_is_never_followed(self):
        self.assertTrue(self.publish()["available"])
        self.snapshot.unlink()
        self.snapshot.symlink_to(self.secret)
        self.assertFalse(self.read()["available"])
        self.assertFalse(self.publish()["available"])
        self.snapshot.unlink()
        self.snapshot.parent.rmdir()
        self.snapshot.parent.symlink_to(self.outside, target_is_directory=True)
        self.assertFalse(self.read()["available"])
        self.assertFalse(self.publish()["available"])
        self.assertEqual(list(self.outside.iterdir()), [self.secret])

    def test_publish_and_read_boundary_substitution_preserve_foreign_files(self):
        def swap(stage):
            if stage == "snapshot_publish":
                self.path.rename(self.path.with_name("retained"))
                self.path.mkdir()
                (self.path / "foreign").write_text("foreign")
        with mock.patch.object(work, "_checkpoint", side_effect=swap):
            self.assertFalse(self.publish()["available"])
        self.assertEqual((self.path / "foreign").read_text(), "foreign")
        self.assertFalse((self.path / "receipts").exists())

    def test_read_boundary_substitution_returns_no_document_bytes(self):
        self.assertTrue(self.publish()["available"])
        def swap(stage):
            if stage == "snapshot_read":
                self.snapshot.rename(self.snapshot.with_suffix(".retained"))
                self.snapshot.write_text("foreign")
        with mock.patch.object(work, "_checkpoint", side_effect=swap):
            result = self.read()
        self.assertFalse(result["available"])
        self.assertNotIn("documents", result)
        self.assertEqual(self.snapshot.read_text(), "foreign")

    def test_cleanup_removes_aids_and_read_does_not_recreate_them(self):
        self.assertTrue(self.publish()["available"])
        generation = work.describe_work(self.root, self.wave)["generation"]
        self.assertEqual(work.cleanup_work(self.root, self.wave, expected_generation=generation)["outcome"], "removed")
        self.assertFalse(self.read()["available"])
        self.assertFalse(self.path.exists())


def tree_snapshot(top: Path) -> dict:
    """Every entry under ``top`` with its type, mode and bytes (links by target text)."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(top, followlinks=False):
        for name in dirnames + filenames:
            path = Path(dirpath) / name
            info = os.lstat(path)
            rel = path.relative_to(top).as_posix()
            if os.path.islink(path):
                out[rel] = ("link", os.readlink(path))
            elif path.is_dir():
                out[rel] = ("dir", info.st_mode)
            elif not stat.S_ISREG(info.st_mode):
                # Never open a FIFO or device: the read would block.
                out[rel] = ("other", info.st_mode)
            else:
                out[rel] = ("file", info.st_mode, path.read_bytes())
    return out


def _nth_call_fails(real, n, exc):
    """Fail the Nth call (directory order is not alphabetical everywhere)."""
    calls = {"count": 0}

    def wrapper(name, *args, **kwargs):
        if name != work.OWNER_FILE:
            calls["count"] += 1
            if calls["count"] == n:
                raise exc
        return real(name, *args, **kwargs)
    return wrapper


@unittest.skipUnless(work._SAFE_DELETE, "descriptor-safe work I/O unavailable")
class PartialRemovalTests(unittest.TestCase):
    """Change 23phc AC-2: a partial deletion is reported as partial."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wf-work-partial-")).resolve()
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.root = self.base / "repo"
        self.wave = waves_dir(self.root) / "abc12 example" / vp.RECORD_FILENAME
        self.wave.parent.mkdir(parents=True)
        self.wave.write_text("# Wave\n")
        self.generation = work.ensure_work(self.root, self.wave)["generation"]
        self.path = self.root / work.WORK_ROOT / "abc12"
        for index in range(5):
            (self.path / f"f{index}").write_text(str(index))

    def cleanup(self):
        return work.cleanup_work(self.root, self.wave, expected_generation=self.generation)

    def test_failure_after_a_removal_is_partially_removed_with_entry_operation_and_errno(self):
        denied = PermissionError(errno.EACCES, "denied")
        with mock.patch.object(work.os, "unlink", side_effect=_nth_call_fails(os.unlink, 2, denied)):
            result = self.cleanup()
        self.assertEqual(result["outcome"], "partially_removed", result)
        self.assertGreaterEqual(result["removed_entries"], 1)
        self.assertEqual(result["failed_operation"], "unlink")
        self.assertIn(result["failed_errno"], ("EACCES", "EPERM"))
        remaining = sorted(p.name for p in self.path.iterdir() if p.name != work.OWNER_FILE)
        self.assertIn(result["failed_entry"], remaining)
        self.assertEqual(len(remaining), 5 - result["removed_entries"])
        self.assertNotIn("ACL", json.dumps(result))
        # Retry authority is unchanged: the owner file stayed in place.
        self.assertEqual(work.describe_work(self.root, self.wave)["generation"], self.generation)
        self.assertEqual(self.cleanup()["outcome"], "removed")

    def test_failure_before_any_removal_stays_preserved_and_names_the_entry(self):
        denied = PermissionError(errno.EPERM, "denied")
        with mock.patch.object(work.os, "unlink", side_effect=_nth_call_fails(os.unlink, 1, denied)):
            result = self.cleanup()
        self.assertEqual(result["outcome"], "preserved", result)
        self.assertEqual(result["removed_entries"], 0)
        self.assertIn(result["failed_entry"], {f"f{index}" for index in range(5)})
        self.assertEqual(result["failed_operation"], "unlink")
        self.assertEqual(result["failed_errno"], "EPERM")
        self.assertEqual(len(list(self.path.iterdir())), 6)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ignores directory permissions")
    def test_real_read_only_subdirectory_names_its_entry(self):
        locked = self.path / "zz"
        locked.mkdir()
        (locked / "locked").write_text("kept")
        os.chmod(locked, 0o500)
        self.addCleanup(os.chmod, locked, 0o700)
        result = self.cleanup()
        self.assertIn(result["outcome"], ("partially_removed", "preserved"), result)
        self.assertEqual(result["failed_entry"], "zz/locked")
        self.assertEqual(result["failed_operation"], "unlink")
        self.assertIn(result["failed_errno"], ("EACCES", "EPERM"))
        self.assertNotIn("ACL", json.dumps(result))
        self.assertEqual((locked / "locked").read_text(), "kept")

    def test_nested_progress_counts_removed_children_and_the_owner_is_not_counted(self):
        nested = self.path / "nested"
        nested.mkdir()
        (nested / "child").write_text("x")
        self.assertEqual(self.cleanup()["outcome"], "removed")
        real = os.rmdir

        def fail_top(name, *args, **kwargs):
            if name == "abc12":
                raise PermissionError(errno.EACCES, "denied")
            return real(name, *args, **kwargs)
        generation = work.ensure_work(self.root, self.wave)["generation"]
        (self.path / "one").write_text("1")
        with mock.patch.object(work.os, "rmdir", side_effect=fail_top):
            result = work.cleanup_work(self.root, self.wave, expected_generation=generation)
        # Every entry went, then the folder itself failed: partial, owner restored.
        self.assertEqual(result["outcome"], "partially_removed", result)
        self.assertEqual(result["removed_entries"], 1)
        self.assertEqual((result["failed_entry"], result["failed_operation"]), (".", "rmdir"))
        self.assertTrue((self.path / work.OWNER_FILE).is_file())


@unittest.skipUnless(work._SAFE_DELETE, "descriptor-safe work I/O unavailable")
class WorkInventoryTests(unittest.TestCase):
    """Change 23phc AC-3: the read-only inventory and its classifier."""

    ARCHIVE = "docs/archive-records"

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wf-work-inventory-")).resolve()
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.outside = self.base / "outside"
        self.outside.mkdir()
        for index in range(30):
            (self.outside / f"big{index}").write_bytes(b"x" * 1000)

    def record(self, key, status, *, slug="fixture"):
        path = waves_dir(self.root) / f"{key} {slug}" / vp.RECORD_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# Wave Record\n\nStatus: {status}\n", encoding="utf-8")
        return path

    def owned(self, record, files=2):
        result = work.ensure_work(self.root, record)
        self.assertTrue(result["available"], result)
        folder = self.root / result["path"]
        for index in range(files):
            (folder / f"file{index}").write_bytes(b"ab")
        return folder

    def unowned(self, key, files=2):
        folder = self.root / work.WORK_ROOT / key
        folder.mkdir(parents=True)
        for index in range(files):
            (folder / f"file{index}").write_bytes(b"abc")
        return folder

    def fixture(self):
        """closed, archived, not-found, active owned and active unowned folders."""
        self.owned(self.record("abc12", "closed"))
        archived = self.record("abc14", "closed", slug="old")
        self.owned(archived)
        archive_dir = self.root / self.ARCHIVE
        archive_dir.mkdir(parents=True)
        moved = archive_dir / archived.parent.name
        archived.parent.rename(moved)
        # An archive is read with the archive profile's record filename.
        (moved / vp.RECORD_FILENAME).rename(moved / vp.archive_profile().RECORD_FILENAME)
        gone = self.record("abc15", "closed", slug="gone")
        self.owned(gone)
        shutil.rmtree(gone.parent)
        self.owned(self.record("abc13", "active"))
        self.record("abc16", "active", slug="unowned")
        self.unowned("abc16")
        (self.root / work.WORK_ROOT / "plain.txt").write_text("skipped")

    def inventory(self, **kwargs):
        with patch_layout(archive_root=self.ARCHIVE):
            return work.inventory_work_root(self.root, **kwargs)

    def by_key(self, items):
        return {item["key"]: item for item in items}

    def test_leftovers_live_unowned_and_valid_live_work_are_classified(self):
        self.fixture()
        before = tree_snapshot(self.root)
        result = self.inventory()
        self.assertEqual(tree_snapshot(self.root), before, "the inventory must write nothing")
        leftovers = self.by_key(result["leftovers"])
        self.assertEqual({key: item["state"] for key, item in leftovers.items()},
                         {"abc12": "closed", "abc14": "archived", "abc15": "not_found_in_checkout"})
        self.assertIn("another branch", leftovers["abc15"]["state_note"])
        self.assertEqual([item["key"] for item in result["live_unowned"]], ["abc16"])
        self.assertEqual(result["live_unowned"][0]["ownership"], "missing")
        self.assertEqual(result["live_owned"], 1)
        self.assertNotIn("abc13", leftovers)
        self.assertEqual(leftovers["abc12"]["entries"], 3)  # two files and the owner file
        self.assertTrue(all(item["complete"] for item in leftovers.values()))
        self.assertTrue(result["complete"], result)
        # Change 23rzt: the plain file in the work root is reported as a loose
        # entry, not as a folder (this assertion previously required its absence).
        self.assertEqual((result["loose_count"], result["loose_entries"]),
                         (1, [{"name": "plain.txt", "kind": "file", "bytes": len("skipped")}]))
        folders = result["leftovers"] + result["live_unowned"] + result["unclassified"]
        self.assertNotIn("plain.txt", [item["key"] for item in folders])
        self.assertTrue(result["next_action"])

    def test_archived_and_not_found_owners_report_structural_validity(self):
        self.fixture()
        leftovers = self.by_key(self.inventory()["leftovers"])
        self.assertEqual(leftovers["abc14"]["ownership"], "valid")
        self.assertEqual(leftovers["abc15"]["ownership"], "valid")
        self.assertEqual(leftovers["abc12"]["ownership"], "valid")
        # Known-bad control: the live wave-path match applied to an archived
        # owner reports it invalid.
        folder = self.root / work.WORK_ROOT / "abc14"
        self.assertEqual(work._owner_state(folder, os.lstat(folder), waves_rel("abc14 old", vp.RECORD_FILENAME)),
                         "valid")
        self.assertEqual(work._owner_state(folder, os.lstat(folder), "elsewhere/" + vp.RECORD_FILENAME), "invalid")

    def test_owner_by_path_read_used_on_native_windows_agrees(self):
        self.fixture()
        expected = {item["key"]: item["ownership"] for item in self.inventory()["leftovers"]}
        with mock.patch.object(work, "_OWNER_READ_BY_DESCRIPTOR", False):
            faked = {item["key"]: item["ownership"] for item in self.inventory()["leftovers"]}
        self.assertEqual(faked, expected)

    def test_malformed_linked_or_special_owner_is_invalid(self):
        record = self.record("abc12", "closed")
        folder = self.owned(record)
        marker = folder / work.OWNER_FILE
        original = marker.read_bytes()
        cases = {
            "not json": lambda: marker.write_text("{"),
            "bad generation": lambda: marker.write_text(json.dumps({**json.loads(original), "generation": "x"})),
            "relative repository": lambda: marker.write_text(json.dumps({**json.loads(original), "repository": "repo"})),
            "link": lambda: (marker.unlink(), marker.symlink_to(self.outside / "big0")),
            "fifo": lambda: (marker.unlink(), os.mkfifo(marker)),
            "oversized": lambda: marker.write_bytes(b" " * 5000),
        }
        for name, damage in cases.items():
            with self.subTest(case=name):
                if marker.is_symlink() or marker.exists():
                    marker.unlink()
                marker.write_bytes(original)
                damage()
                item = self.by_key(self.inventory()["leftovers"])["abc12"]
                self.assertEqual(item["ownership"], "invalid")

    def test_symlink_inside_a_folder_adds_only_the_link_entry(self):
        record = self.record("abc12", "closed")
        folder = self.owned(record, files=0)
        (folder / "link").symlink_to(self.outside, target_is_directory=True)
        item = self.by_key(self.inventory()["leftovers"])["abc12"]
        self.assertEqual(item["entries"], 2)  # the owner file and the link
        self.assertLess(item["bytes"], 1000)
        self.assertTrue(item["complete"])

    def test_entry_bound_reports_an_incomplete_lower_bound(self):
        record = self.record("abc12", "closed")
        self.owned(record, files=10)
        with mock.patch.object(work, "INVENTORY_ENTRY_LIMIT", 3):
            result = self.inventory()
        item = self.by_key(result["leftovers"])["abc12"]
        self.assertFalse(item["complete"])
        self.assertEqual(item["reason"], "entry_limit")
        self.assertLessEqual(item["entries"], 3)
        self.assertFalse(result["complete"])
        self.assertLessEqual(result["entries_visited"], 3)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ignores directory permissions")
    def test_unreadable_subdirectory_is_incomplete_not_empty(self):
        record = self.record("abc12", "closed")
        folder = self.owned(record)
        hidden = folder / "hidden"
        hidden.mkdir()
        (hidden / "secret").write_text("x")
        os.chmod(hidden, 0)
        self.addCleanup(os.chmod, hidden, 0o700)
        item = self.by_key(self.inventory()["leftovers"])["abc12"]
        self.assertFalse(item["complete"])
        self.assertTrue(item["reason"].startswith("unreadable:"), item)

    def test_renamed_record_roots_classify_the_same_way(self):
        import record_paths
        current = (record_paths.WAVES_ROOT, record_paths.PLANS_ROOT)
        with patch_layout(waves_root="alt/iterations", plans_root="alt/changes",
                          archive_root="alt/archive"):
            self.ARCHIVE = "alt/archive"
            self.fixture()
            result = work.inventory_work_root(self.root)
        self.assertEqual({item["key"]: item["state"] for item in result["leftovers"]},
                         {"abc12": "closed", "abc14": "archived", "abc15": "not_found_in_checkout"})
        # Known-bad control: the same tree read under the unrenamed roots does
        # not find the closed record.
        with patch_layout(waves_root=current[0], plans_root=current[1], archive_root=None):
            shipped = {item["key"]: item["state"] for item in work.inventory_work_root(self.root)["leftovers"]}
        self.assertEqual(shipped["abc12"], "not_found_in_checkout")

    def test_absent_work_root_creates_nothing_and_counts_as_empty(self):
        self.record("abc12", "closed")
        result = self.inventory()
        self.assertFalse(result["present"])
        self.assertTrue(result["complete"])
        self.assertIsNone(result["reason"])
        self.assertFalse((self.root / ".wavefoundry").exists())

    def test_linked_work_root_or_parent_lists_no_children(self):
        target = self.base / "linked"
        (target / "work" / "abc12").mkdir(parents=True)
        (target / "abc12").mkdir()
        for link, destination in ((self.root / ".wavefoundry", target),
                                  (self.root / ".wavefoundry" / "work", target)):
            with self.subTest(link=link.relative_to(self.root).as_posix()):
                if (self.root / ".wavefoundry").is_symlink():
                    (self.root / ".wavefoundry").unlink()
                shutil.rmtree(self.root / ".wavefoundry", ignore_errors=True)
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(destination, target_is_directory=True)
                result = self.inventory()
                self.assertFalse(result["complete"])
                self.assertEqual(result["reason"], "work_root_link")
                self.assertEqual(result["leftovers"] + result["live_unowned"] + result["unclassified"], [])
                self.assertNotIn("abc12", json.dumps(result))

    def test_missing_records_and_duplicate_ids_are_unreadable_or_ambiguous(self):
        self.unowned("abc12")
        (waves_dir(self.root) / "abc12 recordless").mkdir(parents=True)
        self.unowned("abc13")
        self.record("abc13", "closed", slug="one")
        self.record("abc13", "closed", slug="two")
        self.unowned("abc14")
        (self.root / self.ARCHIVE / "abc14 archived-recordless").mkdir(parents=True)
        self.unowned("abc15")
        linked = self.record("abc15", "closed", slug="target")
        alias = linked.parent.with_name("abc15 alias")
        os.rename(linked.parent, self.base / "moved-record")
        alias.symlink_to(self.base / "moved-record", target_is_directory=True)
        result = self.inventory()
        import record_paths
        states = {item["key"]: item["state"] for item in result["unclassified"]}
        expected = {"abc12": "unreadable", "abc13": "ambiguous", "abc14": "unreadable"}
        if record_paths.NESTED:
            # The nested discovery walk never enters a linked folder, so a
            # linked record folder is not a candidate at all.
            self.assertEqual(states, expected)
            self.assertEqual([(i["key"], i["state"]) for i in result["leftovers"]],
                             [("abc15", "not_found_in_checkout")])
        else:
            # The flat walk lists a linked folder; the classifier never follows it.
            self.assertEqual(states, {**expected, "abc15": "unreadable"})
            self.assertEqual(result["leftovers"], [])

    def test_untrusted_child_names_are_escaped_and_bounded(self):
        self.unowned("weird\x1bname" + "x" * 200)
        item = self.inventory()["leftovers"][0]
        self.assertNotIn("\x1b", item["key"])
        self.assertLessEqual(len(item["key"]), 83)
        self.assertEqual(item["state"], "not_found_in_checkout")

    def test_single_folder_inventory_includes_valid_live_work(self):
        self.owned(self.record("abc13", "active"))
        folder = work.inventory_work_folder(self.root, "abc13")
        self.assertEqual((folder["state"], folder["ownership"], folder["entries"]), ("active", "valid", 3))
        self.assertIsNone(work.inventory_work_folder(self.root, "abc99"))


class WorkCitationTests(unittest.TestCase):
    """Change 23phc Requirement 7: the cited-work-path search."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wf-work-cite-")).resolve()
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)

    def write(self, name, text):
        path = self.base / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_only_this_keys_folder_matches(self):
        cited = self.write("record.md", "one\nsee .wavefoundry/work/abc12/notes.md\n"
                                      "and `.wavefoundry/work/abc12`\n.wavefoundry/work/abc123/x\n"
                                      ".wavefoundry/work/\n.wavefoundry/work/abc13/y\n")
        result = work.find_work_path_citations(self.base, "abc12", [(cited, True)])
        self.assertEqual(result["hits"], [{"path": "record.md", "line": 2}, {"path": "record.md", "line": 3}])
        self.assertEqual(result["coverage"], "complete")

    def test_unreadable_required_input_is_named_and_absent_optional_is_skipped(self):
        cited = self.write("record.md", ".wavefoundry/work/abc12/x\n")
        bad = self.write("change.md", "")
        bad.write_bytes(b"\xff\xfe")
        result = work.find_work_path_citations(
            self.base, "abc12", [(cited, True), (bad, True), (self.base / "handoff.md", False)])
        self.assertEqual(result["coverage"], "incomplete")
        self.assertEqual(result["unreadable"], ["change.md"])
        self.assertEqual(len(result["hits"]), 1)


class _DeviceStat:
    """An ``os.stat_result`` stand-in with a different ``st_dev``."""

    def __init__(self, real, device):
        self._real, self.st_dev = real, device

    def __getattr__(self, name):
        return getattr(self._real, name)


@unittest.skipUnless(work._SAFE_DELETE, "descriptor-safe work I/O unavailable")
class ExplicitCleanupTests(unittest.TestCase):
    """Change 23q0s: explicit, operator-directed cleanup of one work folder."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wf-work-explicit-")).resolve()
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.record = self.make_record("abc12", "closed")
        self.folder = self.unowned("abc12", files=4)
        self.sibling = self.unowned("abc13", files=2)
        self.make_record("abc13", "closed", slug="sibling")
        self.outside = self.base / "outside"
        self.outside.mkdir()
        (self.outside / "keep.txt").write_text("keep")
        (self.root / "notes.txt").write_text("outside the work root")

    def make_record(self, key, status, *, slug="fixture"):
        path = waves_dir(self.root) / f"{key} {slug}" / vp.RECORD_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# Wave Record\n\nStatus: {status}\n", encoding="utf-8")
        return path

    def unowned(self, key, files=2):
        folder = self.root / work.WORK_ROOT / key
        folder.mkdir(parents=True, exist_ok=True)
        for index in range(files):
            (folder / f"f{index}").write_text(str(index))
        return folder

    def preview(self, key="abc12"):
        result = work.explicit_cleanup(self.root, key)
        self.assertEqual(result["outcome"], "preview", result)
        return result

    def apply(self, token, key="abc12"):
        return work.explicit_cleanup(self.root, key, apply=True, confirmation=token)

    def owner_files(self):
        return sorted(p for p in (self.root / work.WORK_ROOT).rglob(work.OWNER_FILE))

    # AC-1 -------------------------------------------------------------------

    def test_default_and_dry_run_preview_write_nothing(self):
        before = tree_snapshot(self.base)
        for result in (work.explicit_cleanup(self.root, "abc12"),
                       work.explicit_cleanup(self.root, "abc12", apply=False)):
            self.assertEqual(result["outcome"], "preview", result)
            self.assertEqual(result["state"], "closed")
            self.assertEqual(result["ownership"], "missing")
            self.assertEqual((result["entries"], result["complete"]), (4, True))
            self.assertEqual([c["name"] for c in result["children"]], ["f0", "f1", "f2", "f3"])
            self.assertEqual({c["type"] for c in result["children"]}, {"file"})
            self.assertTrue(result["apply_possible"])
            self.assertRegex(result["confirmation"], r"^[0-9a-f]{64}$")
        self.assertEqual(tree_snapshot(self.base), before, "a preview must write nothing")
        self.assertEqual(self.owner_files(), [])

    def test_invalid_keys_are_refused_with_the_tree_unchanged(self):
        os.symlink(self.outside, self.root / work.WORK_ROOT / "lnk12")
        (self.root / work.WORK_ROOT / "fil12").write_text("a file named like a key")
        before = tree_snapshot(self.base)
        cases = {"../x": "work_key_invalid", "abc12/def": "work_key_invalid", "ABC12": "work_key_invalid",
                 "": "work_key_invalid", None: "work_key_invalid", "abc12*": "work_key_invalid",
                 "lnk12": "work_entry_not_directory", "fil12": "work_entry_not_directory"}
        for key, reason in cases.items():
            for apply in (False, True):
                with self.subTest(key=key, apply=apply):
                    result = work.explicit_cleanup(self.root, key, apply=apply, confirmation="x" * 64)
                    self.assertEqual((result["outcome"], result["reason"]), ("refused", reason), result)
        self.assertEqual(tree_snapshot(self.base), before)

    def test_preview_bounds_and_escapes_child_names(self):
        for index in range(60):
            (self.folder / f"n{index:02d}").write_text("x")
        (self.folder / "bad\nname").write_text("x")
        result = self.preview()
        self.assertEqual(len(result["children"]), work.CHILD_PREVIEW_LIMIT)
        self.assertTrue(result["children_truncated"])
        self.assertTrue(all("\n" not in child["name"] for child in result["children"]))

    # AC-2 and AC-4 ------------------------------------------------------------

    def test_apply_removes_only_the_unowned_closed_folder(self):
        (self.folder / "nested").mkdir()
        (self.folder / "nested" / "deep").write_text("deep")
        os.symlink(self.outside, self.folder / "outside-link")
        keep = {"sibling": tree_snapshot(self.sibling), "outside": tree_snapshot(self.outside),
                "record": self.record.read_bytes(), "notes": (self.root / "notes.txt").read_bytes()}
        token = self.preview()["confirmation"]
        result = self.apply(token)
        self.assertEqual(result["outcome"], "removed", result)
        self.assertFalse(os.path.lexists(self.folder))
        self.assertEqual({"sibling": tree_snapshot(self.sibling), "outside": tree_snapshot(self.outside),
                          "record": self.record.read_bytes(), "notes": (self.root / "notes.txt").read_bytes()},
                         keep, "only the named folder may change; the link target stays intact")
        self.assertEqual(self.owner_files(), [])
        # Idempotent: the folder is gone.
        self.assertEqual(self.apply(token)["outcome"], "absent")

    def test_valid_and_invalid_owner_folders_are_eligible(self):
        shutil.rmtree(self.folder)
        self.assertTrue(work.ensure_work(self.root, self.record)["available"])
        with self.subTest(owner="valid"):
            self.assertEqual(self.preview()["ownership"], "valid")
            self.assertEqual(self.apply(self.preview()["confirmation"])["outcome"], "removed")
        for owner in (b'{"schema": 2}', b"not json"):
            with self.subTest(owner=owner):
                folder = self.unowned("abc12", files=1)
                (folder / work.OWNER_FILE).write_bytes(owner)
                self.assertEqual(self.preview()["ownership"], "invalid")
                self.assertEqual(self.apply(self.preview()["confirmation"])["outcome"], "removed")
        self.assertEqual(self.owner_files(), [])

    def test_not_found_in_checkout_folder_is_labelled_and_cleanable(self):
        folder = self.unowned("zzq99", files=1)
        result = self.preview("zzq99")
        self.assertEqual(result["state"], "not_found_in_checkout")
        self.assertIn("another branch or checkout", result["state_note"])
        self.assertIsNone(result["record"])
        self.assertEqual(self.apply(result["confirmation"], "zzq99")["outcome"], "removed")
        self.assertFalse(folder.exists())

    # AC-3 ---------------------------------------------------------------------

    def assert_refused(self, result, reason):
        self.assertEqual((result["outcome"], result["reason"]), ("refused", reason), result)

    def test_empty_and_wrong_tokens_are_stale(self):
        before = tree_snapshot(self.base)
        token = self.preview()["confirmation"]
        for wrong in ("", None, token[:-1] + ("0" if token[-1] != "0" else "1"), token.upper()):
            with self.subTest(token=wrong):
                self.assert_refused(self.apply(wrong), "preview_stale")
        self.assertEqual(tree_snapshot(self.base), before)

    def test_owner_created_or_changed_after_preview_is_stale(self):
        token = self.preview()["confirmation"]
        owner = self.folder / work.OWNER_FILE
        owner.write_bytes(b"{}")
        self.assert_refused(self.apply(token), "preview_stale")
        token = self.preview()["confirmation"]
        owner.write_bytes(b"{ }")
        before = tree_snapshot(self.base)
        self.assert_refused(self.apply(token), "preview_stale")
        self.assertEqual(tree_snapshot(self.base), before)

    def test_live_and_reopened_states_are_refused(self):
        token = self.preview()["confirmation"]
        for status in ("active", "implementing", "paused", "planned", "ready"):
            with self.subTest(status=status):
                self.record.write_text(f"# Wave Record\n\nStatus: {status}\n")
                before = tree_snapshot(self.base)
                result = self.apply(token)
                self.assert_refused(result, "work_state_not_cleanable")
                self.assertEqual(result["state"], status)
                preview = self.preview()
                self.assertFalse(preview["apply_possible"])
                self.assertIsNone(preview["confirmation"])
                self.assertEqual(tree_snapshot(self.base), before)

    def test_ambiguous_and_unreadable_states_are_refused(self):
        with self.subTest(state="ambiguous"):
            token = self.preview()["confirmation"]
            other = self.make_record("abc12", "closed", slug="duplicate")
            result = self.apply(token)
            self.assert_refused(result, "work_state_not_cleanable")
            self.assertEqual(result["state"], "ambiguous")
            shutil.rmtree(other.parent)
        with self.subTest(state="unreadable: live folder without a record"):
            token = self.preview()["confirmation"]
            self.record.unlink()
            result = self.apply(token)
            self.assert_refused(result, "work_state_not_cleanable")
            self.assertEqual(result["state"], "unreadable")
            self.assertTrue(self.folder.exists())

    def test_replaced_folder_is_stale(self):
        token = self.preview()["confirmation"]
        aside = self.root / "aside"
        self.folder.rename(aside)
        self.unowned("abc12", files=4)
        before = tree_snapshot(self.base)
        self.assert_refused(self.apply(token), "preview_stale")
        self.assertEqual(tree_snapshot(self.base), before)

    def test_token_bound_to_another_device_number_is_stale(self):
        result = self.preview()
        info = os.lstat(self.folder)
        root = str(self.root.resolve())
        same = work.cleanup_token(root, "abc12", [info.st_dev, info.st_ino], "absent", "closed",
                                  result["record"])
        self.assertEqual(same, result["confirmation"], "the oracle must reproduce the real token")
        moved = work.cleanup_token(root, "abc12", [info.st_dev + 1, info.st_ino], "absent", "closed",
                                   result["record"])
        self.assert_refused(self.apply(moved), "preview_stale")
        self.assertTrue((self.folder / "f0").exists())

    def test_work_parent_replaced_by_a_link_is_refused(self):
        token = self.preview()["confirmation"]
        work_root = self.root / work.WORK_ROOT
        aside = self.root / "work-aside"
        work_root.rename(aside)
        other = self.base / "other"
        (other / "abc12").mkdir(parents=True)
        (other / "abc12" / "victim").write_text("victim")
        os.symlink(other, work_root)
        before = tree_snapshot(self.base)
        result = self.apply(token)
        self.assert_refused(result, "work_root_link")
        self.assertEqual(tree_snapshot(self.base), before)

    def test_unsupported_host_previews_without_token_and_refuses_apply(self):
        token = self.preview()["confirmation"]
        before = tree_snapshot(self.base)
        with mock.patch.object(work, "_SAFE_DELETE", False):
            preview = work.explicit_cleanup(self.root, "abc12")
            result = self.apply(token)
        self.assertEqual(preview["outcome"], "preview", preview)
        self.assertFalse(preview["apply_possible"])
        self.assertIsNone(preview["confirmation"])
        self.assertIn("safe_work_io_unsupported", preview["apply_blockers"])
        self.assertEqual((preview["entries"], preview["state"], preview["ownership"]), (4, "closed", "missing"))
        self.assertEqual(len(preview["children"]), 4)
        self.assert_refused(result, "safe_work_io_unsupported")
        self.assertEqual(tree_snapshot(self.base), before)

    def mid_deletion(self, change, *, stage="unlink", at=2):
        """Run apply and call ``change`` at the ``at``-th ``stage`` checkpoint."""
        token = self.preview()["confirmation"]
        seen = {"count": 0}

        def checkpoint(name):
            if name == stage:
                seen["count"] += 1
                if seen["count"] == at:
                    change()
        with mock.patch.object(work, "_checkpoint", side_effect=checkpoint):
            result = self.apply(token)
        self.assertGreaterEqual(seen["count"], at, "the change must have happened")
        return result

    def assert_partial(self, result, reasons):
        self.assertEqual(result["outcome"], "partially_removed", result)
        self.assertIn(result["reason"], reasons)
        self.assertEqual(result["removed_entries"], 1)

    def test_owner_changed_during_deletion_stops_after_one_entry(self):
        owner = self.folder / work.OWNER_FILE
        owner.write_bytes(b"{}")
        keep = tree_snapshot(self.outside), tree_snapshot(self.sibling)
        result = self.mid_deletion(lambda: owner.write_bytes(b"{ }"))
        self.assert_partial(result, {"work_owner_changed"})
        self.assertEqual(len([p for p in self.folder.iterdir() if p.name != work.OWNER_FILE]), 3)
        self.assertEqual(owner.read_bytes(), b"{ }")
        self.assertEqual((tree_snapshot(self.outside), tree_snapshot(self.sibling)), keep)

    def test_owner_created_during_deletion_stops_after_one_entry(self):
        owner = self.folder / work.OWNER_FILE
        result = self.mid_deletion(lambda: owner.write_bytes(b"{}"))
        self.assert_partial(result, {"work_owner_changed"})
        self.assertEqual(len([p for p in self.folder.iterdir() if p.name != work.OWNER_FILE]), 3)

    def test_folder_swapped_during_deletion_stops_after_one_entry(self):
        aside = self.root / "aside"
        replacement = {}

        def swap():
            self.folder.rename(aside)
            self.unowned("abc12", files=3)
            replacement.update(tree_snapshot(self.folder))
        result = self.mid_deletion(swap)
        self.assert_partial(result, {"work_identity_changed"})
        self.assertEqual(len(list(aside.iterdir())), 3, "the previewed folder keeps its other entries")
        self.assertEqual(tree_snapshot(self.folder), replacement, "the new folder is untouched")

    def test_work_parent_replaced_during_deletion_stops_after_one_entry(self):
        work_root = self.root / work.WORK_ROOT
        aside = self.root / "work-aside"
        other = self.base / "other"
        (other / "abc12").mkdir(parents=True)
        (other / "abc12" / "victim").write_text("victim")
        target = tree_snapshot(other)

        def replace():
            work_root.rename(aside)
            os.symlink(other, work_root)
        result = self.mid_deletion(replace)
        # _anchor's no-follow walk raises before it can compare identities.
        self.assert_partial(result, {"work_parent_changed", "work_io_failed"})
        self.assertEqual(len(list((aside / "abc12").iterdir())), 3)
        self.assertEqual(tree_snapshot(other), target)

    def test_nested_directory_change_is_caught_before_rmdir_child(self):
        for child in list(self.folder.iterdir()):
            child.unlink()
        (self.folder / "d").mkdir()
        (self.folder / "d" / "x").write_text("x")
        owner = self.folder / work.OWNER_FILE
        owner.write_bytes(b"{}")
        result = self.mid_deletion(lambda: owner.write_bytes(b"{ }"), stage="rmdir_child", at=1)
        self.assert_partial(result, {"work_owner_changed"})
        self.assertTrue((self.folder / "d").is_dir())

    def test_folder_on_another_device_is_refused(self):
        real_fstat = os.fstat
        inode = os.lstat(self.folder).st_ino
        token = self.preview()["confirmation"]

        def fstat(fd):
            info = real_fstat(fd)
            return _DeviceStat(info, info.st_dev + 1) if info.st_ino == inode else info
        before = tree_snapshot(self.base)
        with mock.patch.object(work.os, "fstat", side_effect=fstat):
            preview = work.explicit_cleanup(self.root, "abc12")
            results = [self.apply(token), self.apply("")]
        self.assertEqual(preview["outcome"], "preview", preview)
        self.assertIn("work_filesystem_changed", preview["apply_blockers"])
        self.assertIsNone(preview["confirmation"])
        for result in results:
            self.assert_refused(result, "work_filesystem_changed")
        self.assertEqual(tree_snapshot(self.base), before)

    def test_nested_directory_on_another_device_is_kept(self):
        """Requirement 5 (DELIV-Q0S-NESTED-MOUNT-UNPINNED): a directory inside
        the folder on another device, as a mount point reads, stops apply
        before anything in it is removed."""
        mount = self.folder / "mnt"
        mount.mkdir()
        (mount / "precious.txt").write_text("on another filesystem")
        inode = os.lstat(mount).st_ino
        real = {name: getattr(os, name) for name in ("stat", "lstat", "fstat")}

        def other_device(name):
            def patched(*args, **kwargs):
                info = real[name](*args, **kwargs)
                return _DeviceStat(info, info.st_dev + 1) if info.st_ino == inode else info
            return patched
        keep = tree_snapshot(self.outside), tree_snapshot(self.sibling)
        with mock.patch.object(work.os, "stat", side_effect=other_device("stat")), \
                mock.patch.object(work.os, "lstat", side_effect=other_device("lstat")), \
                mock.patch.object(work.os, "fstat", side_effect=other_device("fstat")):
            preview = self.preview()
            # The preview's sizing walk reads entries through scandir, which
            # this patch does not reach, so it still offers a token: the
            # deletion's own device comparison is what is under test.
            self.assertIsNotNone(preview["confirmation"], preview)
            result = self.apply(preview["confirmation"])
        # Entries listed before the mount point may already be gone.
        self.assertIn(result["outcome"], {"partially_removed", "preserved"}, result)
        self.assertEqual((result["reason"], result["failed_entry"]), ("work_filesystem_changed", "mnt"), result)
        self.assertEqual((mount / "precious.txt").read_text(), "on another filesystem")
        self.assertTrue(mount.is_dir())
        self.assertEqual((tree_snapshot(self.outside), tree_snapshot(self.sibling)), keep)

    def test_unsafe_owner_entries_are_refused_promptly(self):
        owner = self.folder / work.OWNER_FILE
        cases = {"large": lambda: owner.write_bytes(b"x" * 4097),
                 "link": lambda: os.symlink(self.outside / "keep.txt", owner),
                 "directory": lambda: owner.mkdir(),
                 "hard link": lambda: os.link(self.outside / "keep.txt", owner)}
        if hasattr(os, "mkfifo"):
            cases["fifo"] = lambda: os.mkfifo(owner)
        for name, make in cases.items():
            with self.subTest(owner=name):
                make()
                before = tree_snapshot(self.base)
                outcome = {}
                thread = threading.Thread(target=lambda: outcome.update(
                    preview=work.explicit_cleanup(self.root, "abc12"),
                    apply=self.apply("x" * 64)), daemon=True)
                thread.start()
                thread.join(timeout=10)
                self.assertFalse(thread.is_alive(), "an unsafe owner entry must not block")
                self.assertEqual(outcome["preview"]["owner_entry"], "unsafe")
                self.assertIn("unsafe_owner_entry", outcome["preview"]["apply_blockers"])
                self.assertIsNone(outcome["preview"]["confirmation"])
                self.assert_refused(outcome["apply"], "unsafe_owner_entry")
                self.assertEqual(tree_snapshot(self.base), before)
                if owner.is_dir() and not owner.is_symlink():
                    owner.rmdir()
                else:
                    owner.unlink()

    # AC-5 ---------------------------------------------------------------------

    def test_permission_failure_is_partial_then_a_fresh_preview_and_apply_removes(self):
        modes = {p.name: p.stat().st_mode for p in self.folder.iterdir()}
        denied = PermissionError(errno.EACCES, "denied")
        token = self.preview()["confirmation"]
        with mock.patch.object(work.os, "unlink", side_effect=_nth_call_fails(os.unlink, 2, denied)):
            result = self.apply(token)
        self.assertEqual(result["outcome"], "partially_removed", result)
        self.assertEqual(result["removed_entries"], 1)
        self.assertEqual((result["failed_operation"], result["failed_errno"]), ("unlink", "EACCES"))
        remaining = {p.name: p.stat().st_mode for p in self.folder.iterdir()}
        self.assertIn(result["failed_entry"], remaining)
        self.assertEqual(len(remaining), 3)
        self.assertEqual({name: modes[name] for name in remaining}, remaining, "permissions are never changed")
        self.assertEqual(self.owner_files(), [], "no owner file is written")
        self.assertEqual(self.apply(self.preview()["confirmation"])["outcome"], "removed")

    @unittest.skipUnless(sys.platform == "darwin", "macOS deny-delete ACL")
    def test_macos_deny_delete_acl_is_reported_as_partial(self):
        import subprocess

        locked = self.folder / "zz-locked"
        locked.write_text("kept")
        acl = subprocess.run(["chmod", "+a", "everyone deny delete", str(locked)], capture_output=True)
        if acl.returncode != 0:
            self.skipTest("cannot set an ACL here: " + acl.stderr.decode(errors="replace"))
        self.addCleanup(subprocess.run, ["chmod", "-N", str(locked)], capture_output=True)
        real_listdir = os.listdir
        token = self.preview()["confirmation"]
        # Deterministic order only; the denial itself is the real ACL.
        with mock.patch.object(work.os, "listdir", side_effect=lambda fd: sorted(real_listdir(fd))):
            result = self.apply(token)
        if result["outcome"] == "removed":
            self.skipTest("this file system does not enforce deny-delete ACL entries")
        self.assertEqual(result["outcome"], "partially_removed", result)
        self.assertEqual(result["removed_entries"], 4)
        self.assertEqual((result["failed_entry"], result["failed_operation"]), ("zz-locked", "unlink"))
        self.assertIn(result["failed_errno"], ("EPERM", "EACCES"))
        self.assertEqual(locked.read_text(), "kept")
        self.assertEqual(self.owner_files(), [])


class WorkRootLooseEntryTests(unittest.TestCase):
    """Change 23rzt AC-2: plain files and links directly in the work root.

    No owned folder is needed, so this runs on every host, native Windows
    included; only the link cases depend on the host being able to create links.
    """

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wf-work-loose-")).resolve()
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.root = self.base / "repo"
        self.work = self.root / work.WORK_ROOT
        self.work.mkdir(parents=True)
        self.outside = self.base / "outside"
        self.outside.mkdir()

    def record(self, key, status, slug="fixture"):
        path = waves_dir(self.root) / f"{key} {slug}" / vp.RECORD_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# Wave Record\n\nStatus: {status}\n", encoding="utf-8")

    def folders(self):
        """Two folders: a closed record's and a live record's."""
        self.record("abc12", "closed")
        self.record("abc13", "active", slug="live")
        for key in ("abc12", "abc13"):
            (self.work / key).mkdir()
            (self.work / key / "scratch.txt").write_bytes(b"abcd")

    def files(self):
        (self.work / "a-brief.md").write_bytes(b"x" * 10)
        (self.work / "b-build.log").write_bytes(b"x" * 300)
        (self.work / "c-notes.txt").write_bytes(b"x")

    def link(self, name, target):
        try:
            os.symlink(target, self.work / name)
        except (OSError, NotImplementedError, AttributeError) as exc:
            self.skipTest(f"symbolic links cannot be created on this host ({type(exc).__name__}: {exc})")

    @staticmethod
    def folder_view(result):
        return {field: result[field] for field in ("leftovers", "live_unowned", "unclassified", "live_owned",
                                                     "totals", "next_action", "complete", "reason", "present")}

    def test_files_and_links_are_listed_with_kind_and_size_and_folders_are_unchanged(self):
        self.folders()
        control = work.inventory_work_root(self.root)
        self.assertEqual((control["loose_count"], control["loose_entries"]), (0, []))
        self.files()
        large = self.outside / "large.bin"
        large.write_bytes(b"x" * 1_000_000)
        self.link("outside-link", large)
        self.link("dangling-link", self.outside / "missing")
        before = tree_snapshot(self.root)
        touched = []
        real_stat, real_open, real_scandir = os.stat, os.open, os.scandir

        def spy(real):
            def call(path, *args, **kwargs):
                touched.append(os.fspath(path) if isinstance(path, (str, bytes, os.PathLike)) else path)
                return real(path, *args, **kwargs)
            return call
        with mock.patch.object(os, "stat", spy(real_stat)), mock.patch.object(os, "open", spy(real_open)), \
                mock.patch.object(os, "scandir", spy(real_scandir)):
            result = work.inventory_work_root(self.root)
        self.assertEqual(tree_snapshot(self.root), before, "the inventory must write nothing")
        self.assertEqual(self.folder_view(result), self.folder_view(control), "folder results are unchanged")
        self.assertEqual(result["loose_count"], 5)
        self.assertEqual(result["loose_entries"], [
            {"name": "b-build.log", "kind": "file", "bytes": 300},
            {"name": "a-brief.md", "kind": "file", "bytes": 10},
            {"name": "c-notes.txt", "kind": "file", "bytes": 1},
            {"name": "dangling-link", "kind": "link", "bytes": None},
            {"name": "outside-link", "kind": "link", "bytes": None},
        ])
        named = [str(item) for item in touched]
        for target in (str(large), str(self.outside / "missing"), "outside-link", "dangling-link"):
            self.assertFalse([item for item in named if item.endswith(target)],
                             f"no stat, open or listing may reach {target}")

    def test_count_is_exact_and_the_list_is_capped_largest_first(self):
        count = work.LOOSE_ENTRY_LIST_CAP + 5
        for index in range(count):
            (self.work / f"f{index:03d}.log").write_bytes(b"x" * (index + 1))
        result = work.inventory_work_root(self.root)
        self.assertEqual(result["loose_count"], count)
        self.assertEqual(len(result["loose_entries"]), work.LOOSE_ENTRY_LIST_CAP)
        self.assertEqual([item["bytes"] for item in result["loose_entries"]],
                         list(range(count, 5, -1)), "the cap drops the smallest files")
        self.assertTrue(result["complete"])

    def test_entry_limit_makes_the_count_a_lower_bound(self):
        for index in range(10):
            (self.work / f"f{index}.log").write_bytes(b"x")
        result = work.inventory_work_root(self.root, entry_limit=4)
        self.assertFalse(result["complete"])
        self.assertEqual(result["reason"], "entry_limit")
        self.assertEqual(result["loose_count"], 4)
        self.assertLessEqual(result["entries_visited"], 4)
        bound = "(a lower bound: the listing stopped early)"
        self.assertIn(f"4 loose file(s) or link(s) directly in {work.WORK_ROOT.as_posix()}/ {bound}: ",
                      work.loose_entries_message(result))
        # The control: a complete listing does not call its count a lower bound.
        self.assertNotIn(bound, work.loose_entries_message(work.inventory_work_root(self.root)))

    def test_sizes_are_reported_without_a_measuring_walk(self):
        self.folders()
        self.files()
        result = work.inventory_work_root(self.root, measure=False)
        self.assertIsNone(result["leftovers"][0]["bytes"], "folders are not measured")
        self.assertEqual({item["name"]: item["bytes"] for item in result["loose_entries"]},
                         {"b-build.log": 300, "a-brief.md": 10, "c-notes.txt": 1})

    def test_an_entry_whose_metadata_cannot_be_read_is_not_listed_and_marks_the_result_incomplete(self):
        self.files()
        real_scandir = os.scandir

        class Unreadable:
            def __init__(self, entry):
                self._entry = entry
                self.name, self.path = entry.name, entry.path

            def stat(self, *, follow_symlinks=True):
                raise PermissionError(errno.EACCES, "denied", self.path)

        class Listing:
            def __init__(self, path):
                self._listing = real_scandir(path)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self._listing.close()

            def __iter__(self):
                for entry in self._listing:
                    yield Unreadable(entry) if entry.name == "a-brief.md" else entry

        def scandir(path):
            return Listing(path) if Path(path) == self.work else real_scandir(path)
        with mock.patch.object(work.os, "scandir", scandir):
            result = work.inventory_work_root(self.root)
        self.assertFalse(result["complete"])
        self.assertEqual(result["reason"], "unreadable:EACCES")
        self.assertEqual(result["loose_count"], 2)
        self.assertNotIn("a-brief.md", [item["name"] for item in result["loose_entries"]])

    def test_untrusted_names_are_escaped_and_bounded(self):
        name = "weird\x1bname" + "x" * 200
        try:
            (self.work / name).write_bytes(b"x")
        except OSError as exc:
            self.skipTest(f"this file system refuses the name ({exc})")
        listed = work.inventory_work_root(self.root)["loose_entries"][0]["name"]
        self.assertNotIn("\x1b", listed)
        self.assertLessEqual(len(listed), 83)
        message = work.loose_entries_message(work.inventory_work_root(self.root))
        self.assertIn(listed, message)
        self.assertNotIn("\x1b", message)

    def test_the_upgrade_report_does_not_carry_the_loose_entries(self):
        import upgrade_wavefoundry

        self.folders()
        self.files()
        report = upgrade_wavefoundry._run_work_root_inventory(self.root)
        self.assertTrue(report["reported"], report)
        fields = upgrade_wavefoundry._work_root_fields({"work_root": report})
        for carried in (report, fields):
            self.assertFalse([key for key in carried if key.startswith("loose")], carried)
        self.assertNotIn("b-build.log", json.dumps([report, fields]))


@default_profile_only("a census of the shipped seeds, templates and this repository's prompt copies")
class LooseFileGuidanceTests(unittest.TestCase):
    """Change 23rzt AC-1: every "Disposable work" section that tells the
    coordinator to put the work path in briefs states where an agent's own
    files go and who acts on a loose one. The sections are found, not listed."""

    FRAMEWORK = SCRIPTS.parent
    ROOTS = (FRAMEWORK / "seeds", FRAMEWORK / "install" / "lifecycle-prompts", SCRIPTS.parents[2] / "docs" / "prompts")
    IN_SCOPE_MINIMUM = 13
    RULE = (
        "Write every file you create for a wave, including coordinator briefs, logs, captured test output "
        "and build output, inside that wave's own work folder, in a child folder when that helps",
        "never write a file directly in `.wavefoundry/work/`",
        "Before the wave exists, keep the content in task context until a lifecycle call reports the work area.",
        "If you wrote such a file for a wave, move it into that wave's folder while the wave is open, or delete it.",
        "Leave any other loose file in place, including one you are not sure you wrote",
        "and report it to the operator, who decides.",
        "Never move a file you did not write into a wave's folder: close removes that folder with everything in it.",
    )
    SEED_209_RULE = (
        "write it inside the wave's own work folder, in a child folder when that helps, never directly in "
        "`.wavefoundry/work/`",
        "before the wave exists, keep it in task context until a lifecycle call reports the work area",
        "If you wrote a loose file there for a wave, move it into that wave's folder while the wave is open, "
        "or delete it.",
        "Leave any other loose file in place, including one you are not sure you wrote, and report it to the "
        "operator, who decides.",
        "Never move a file you did not write into a wave's folder: close removes that folder with everything in it.",
    )
    _HEADING = re.compile(r"^(#{2,3}) Disposable work$")

    @classmethod
    def sections(cls) -> list[tuple[Path, str]]:
        found = []
        for top in cls.ROOTS:
            for path in sorted(top.glob("*.md")):
                lines = path.read_text(encoding="utf-8").splitlines()
                for index, line in enumerate(lines):
                    match = cls._HEADING.match(line)
                    if not match:
                        continue
                    body = []
                    for following in lines[index + 1:]:
                        level = len(following) - len(following.lstrip("#"))
                        if 0 < level <= len(match.group(1)) and following[level:level + 1] == " ":
                            break
                        body.append(following)
                    found.append((path, "\n".join(body)))
        return found

    def test_every_in_scope_section_states_the_rule(self):
        in_scope = [(path, body) for path, body in self.sections() if "briefs" in body]
        self.assertGreaterEqual(len(in_scope), self.IN_SCOPE_MINIMUM, [str(path) for path, _ in in_scope])
        for path, body in in_scope:
            for fragment in self.RULE:
                with self.subTest(path=path.name, parent=path.parent.name, fragment=fragment[:40]):
                    self.assertIn(fragment, " ".join(body.split()))

    def test_seed_209_briefing_guidance_states_the_rule(self):
        text = (self.FRAMEWORK / "seeds" / "209-agent-harness-core.prompt.md").read_text(encoding="utf-8")
        bullet = next(line for line in text.splitlines()
                      if line.startswith("- Pass briefing packets in the agent task context."))
        for fragment in self.SEED_209_RULE:
            with self.subTest(fragment=fragment[:40]):
                self.assertIn(fragment, bullet)


class NextActionTests(unittest.TestCase):
    def test_cleanup_tool_is_named_only_when_registered(self):
        import mcp_tool_roster

        with mock.patch.object(work, "_SAFE_DELETE", True):
            self.assertEqual(work.cleanup_tool_registered(), work.CLEANUP_TOOL in mcp_tool_roster.TOOL_TIERS)
            with mock.patch.dict(mcp_tool_roster.TOOL_TIERS, clear=False):
                mcp_tool_roster.TOOL_TIERS.pop(work.CLEANUP_TOOL, None)
                self.assertNotIn(work.CLEANUP_TOOL, work.retained_work_next_action("abc12"))
                mcp_tool_roster.TOOL_TIERS[work.CLEANUP_TOOL] = "write"
                self.assertIn(f"{work.CLEANUP_TOOL}(work_key='abc12')", work.retained_work_next_action("abc12"))
        with mock.patch.object(work, "_SAFE_DELETE", False):
            text = work.retained_work_next_action("abc12")
            self.assertNotIn(work.CLEANUP_TOOL, text)
            self.assertIn("remove it yourself", text)


if __name__ == "__main__":
    unittest.main()
