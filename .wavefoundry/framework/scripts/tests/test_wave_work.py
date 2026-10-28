"""Finite ownership, generation and descriptor-bound deletion controls."""
from __future__ import annotations

import errno
import base64
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import wave_work as work  # noqa: E402
import vocabulary_profile as vp  # noqa: E402
from gardener_metadata import canonical_review_policy_body  # noqa: E402
from record_layout_support import patch_layout, waves_dir, waves_rel  # noqa: E402


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

    def test_wrong_repository_wave_or_directory_identity_is_preserved(self):
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
        marker.write_text(json.dumps(owner))
        before = marker.read_bytes()
        for result in (work.describe_work(self.root, self.wave),
                       work.ensure_work(self.root, self.wave)):
            self.assertTrue(result["available"], result)
            self.assertEqual(result["generation"], generation)
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
        marker.write_text(json.dumps(owner))
        before = marker.read_bytes()
        snapshot_before = self.snapshot.read_bytes()
        result = self.read()
        self.assertTrue(result["available"], result)
        self.assertEqual(result["documents"], self.documents)
        self.assertEqual(marker.read_bytes(), before)
        self.assertEqual(self.snapshot.read_bytes(), snapshot_before)

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


if __name__ == "__main__":
    unittest.main()
