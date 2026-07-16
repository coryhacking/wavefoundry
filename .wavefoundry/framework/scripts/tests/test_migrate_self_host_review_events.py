from __future__ import annotations

import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import migrate_self_host_review_events as migration
import review_evidence as review


class SelfHostReviewEventMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs" / "waves").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _legacy_wave(self, key: str, records: list[dict]) -> None:
        wave_dir = self.root / "docs" / "waves" / key
        wave_dir.mkdir()
        text = (
            "# Wave Record\n\n"
            "Owner: Engineering\nStatus: implementing\n"
            "review-evidence-protocol: 1\n\n"
            f"wave-id: `{key}`\nTitle: Preserved title\n\n"
            "## Objective\n\nPreserve this narrative exactly.\n\n"
            + review.empty_finding_synthesis_section()
            + "\n## Review Evidence\n\n- operator-signoff: pending\n"
        )
        (wave_dir / "wave.md").write_text(
            review.render_review_evidence_records(text, records), encoding="utf-8"
        )

    @staticmethod
    def _run_record(run_id: str) -> dict:
        return {
            "record_type": "review_run",
            "review_run_id": run_id,
            "run_kind": "readiness",
            "cycle": 0,
            "candidate_finding_ids": [],
            "source_record_ids": [],
            "dedup_evidence_id": None,
        }

    def test_exact_census_migrates_in_flight_last_and_reruns_idempotently(self):
        first = "1skt1 executable-review-evidence"
        last = "1slep external-wave-event-ledger"
        first_records = [self._run_record("run-first")]
        last_records = [self._run_record("run-last-a"), self._run_record("run-last-b")]
        self._legacy_wave(first, first_records)
        self._legacy_wave(last, last_records)
        adoption = {
            "protocol_version": 1,
            "waves": {
                last: {"version": 1, "records": last_records},
                first: {"version": 1, "records": first_records},
            },
        }
        adoption_path = self.root / review.ADOPTION_LEDGER_REL
        adoption_path.write_text(json.dumps(adoption) + "\n", encoding="utf-8")

        manifest = migration.migrate_self_host_review_events(
            self.root, in_flight_wave=last
        )

        self.assertEqual(manifest["adopted_wave_keys"], [first, last])
        self.assertEqual(manifest["in_flight_wave_last"], last)
        for key, expected in ((first, first_records), (last, last_records)):
            wave_md = self.root / "docs" / "waves" / key / "wave.md"
            text = wave_md.read_text(encoding="utf-8")
            self.assertIn("review-evidence-source: events.jsonl", text)
            self.assertNotIn("review-evidence-protocol", text)
            self.assertNotIn("```jsonl", text)
            self.assertIn("Preserve this narrative exactly.", text)
            parsed = review.validate_external_review_evidence(wave_md)
            self.assertEqual(list(parsed.records), expected)
            self.assertFalse(review.validate_adopted_protocol_state(self.root, key, wave_md))
            entry = manifest["waves"][key]
            self.assertEqual(entry["migration_state"], "complete")
            self.assertEqual(entry["source_record_count"], len(expected))
            self.assertEqual(entry["target_record_count"], len(expected))
            self.assertEqual(entry["source_prefix_sha256"], entry["target_prefix_sha256"])

        before = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        rerun = migration.migrate_self_host_review_events(
            self.root, in_flight_wave=last
        )
        after = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        self.assertEqual(rerun, manifest)
        self.assertEqual(after, before)

    def test_resume_after_wave_commit_before_adoption_commit(self):
        key = "1slep external-wave-event-ledger"
        records = [self._run_record("run-resume")]
        self._legacy_wave(key, records)
        adoption_path = self.root / review.ADOPTION_LEDGER_REL
        adoption_path.write_text(
            json.dumps({
                "protocol_version": 1,
                "waves": {key: {"version": 1, "records": records}},
            }) + "\n",
            encoding="utf-8",
        )
        real_atomic_json = migration._atomic_json

        def fail_adoption(path, value, label):
            if label == "migration-adoption":
                raise OSError("forced adoption interruption")
            return real_atomic_json(path, value, label)

        with patch.object(migration, "_atomic_json", side_effect=fail_adoption):
            with self.assertRaises(OSError):
                migration.migrate_self_host_review_events(
                    self.root, in_flight_wave=key
                )
        wave_md = self.root / "docs" / "waves" / key / "wave.md"
        self.assertIn(
            review.REVIEW_EVIDENCE_SOURCE_DECLARATION,
            wave_md.read_text(encoding="utf-8"),
        )
        self.assertIn("records", json.loads(adoption_path.read_text())["waves"][key])

        resumed = migration.migrate_self_host_review_events(
            self.root, in_flight_wave=key
        )
        self.assertEqual(resumed["waves"][key]["migration_state"], "complete")
        self.assertFalse(review.validate_adopted_protocol_state(self.root, key, wave_md))


if __name__ == "__main__":
    unittest.main()
