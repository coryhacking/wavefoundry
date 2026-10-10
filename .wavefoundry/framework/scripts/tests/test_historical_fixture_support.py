"""205jp: immutable historical source inputs survive checkouts without refs."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import historical_fixture_support as subject


class HistoricalFixtureIntegrityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "sources.json"
        self.path.write_bytes(subject.BUNDLE_PATH.read_bytes())

    def _replace(self, mutate):
        bundle = json.loads(self.path.read_bytes())
        mutate(bundle)
        self.path.write_text(json.dumps(bundle), encoding="utf-8")

    def test_old_python_bytes_match_the_independently_recorded_source_digests(self):
        pins = {
            "v122-upgrade": (269025, "ae18d63246bc55f398bb6ae10303044f7701b68dbbf7ecff8e8e54230df0fb24"),
            "v1-receipt-reader": (65762, "2facf5370782062acba6775aa6132ee933dd2c794acf8705cd23c8317aa98397"),
        }
        for key, (size, digest) in pins.items():
            with self.subTest(key=key):
                source = subject.historical_bytes(key)
                self.assertEqual(size, len(source))
                self.assertEqual(digest, hashlib.sha256(source).hexdigest())

    def test_a_missing_bundle_fails_without_checkout_or_current_source_fallback(self):
        self.path.unlink()
        with self.assertRaisesRegex(AssertionError, "missing or unreadable"):
            subject.historical_bytes("v122-upgrade", bundle_path=self.path)

    def test_metadata_changes_are_rejected_by_the_pinned_bundle_digest(self):
        self._replace(lambda b: b["entries"]["v122-upgrade"].update(revision="0" * 40))
        with self.assertRaisesRegex(AssertionError, "bundle integrity mismatch"):
            subject.historical_bytes("v122-upgrade", bundle_path=self.path)

    def test_source_digest_is_checked_even_if_bundle_digest_is_recomputed(self):
        def damage(bundle):
            entry = bundle["entries"]["v122-upgrade"]
            source = base64.b64decode("".join(entry["content_b64"]))
            damaged = bytes([source[0] ^ 1]) + source[1:]
            entry["content_b64"] = [base64.b64encode(damaged).decode()]
        self._replace(damage)
        with patch.object(subject, "BUNDLE_SHA256", hashlib.sha256(self.path.read_bytes()).hexdigest()):
            with self.assertRaisesRegex(AssertionError, "source integrity mismatch"):
                subject.historical_bytes("v122-upgrade", bundle_path=self.path)

    def test_source_size_is_checked_even_when_its_bytes_and_digest_match(self):
        self._replace(lambda b: b["entries"]["v122-upgrade"].update(size=1))
        with patch.object(subject, "BUNDLE_SHA256", hashlib.sha256(self.path.read_bytes()).hexdigest()):
            with self.assertRaisesRegex(AssertionError, "source integrity mismatch"):
                subject.historical_bytes("v122-upgrade", bundle_path=self.path)

    def test_substituting_current_source_does_not_make_an_old_fixture_valid(self):
        current = Path(__file__).parents[1] / "sqlite_storage_migration.py"
        self._replace(lambda b: b["entries"]["v1-receipt-reader"].update(
            content_b64=[base64.b64encode(current.read_bytes()).decode()]))
        with patch.object(subject, "BUNDLE_SHA256", hashlib.sha256(self.path.read_bytes()).hexdigest()):
            with self.assertRaisesRegex(AssertionError, "source integrity mismatch"):
                subject.historical_bytes("v1-receipt-reader", bundle_path=self.path)

    def test_only_recorded_historical_absence_is_optional(self):
        key = "v114:docs/contributing/lifecycle-overview.md"
        self.assertIsNone(subject.historical_bytes(key, optional=True))
        with self.assertRaisesRegex(AssertionError, "was absent at its revision"):
            subject.historical_bytes(key)
        with self.assertRaisesRegex(AssertionError, "entry missing"):
            subject.historical_bytes("unrecorded-source", optional=True)

    def test_an_oversized_bundle_is_refused_before_decoding(self):
        self.path.write_bytes(b"x" * (subject.MAX_BUNDLE_BYTES + 1))
        with self.assertRaisesRegex(AssertionError, "exceeds its size bound"):
            subject.historical_bytes("v122-upgrade", bundle_path=self.path)


if __name__ == "__main__":
    unittest.main()
