from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


TESTS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_ROOT.parents[2]
SCRIPT_PATH = PROJECT_ROOT / "framework" / "scripts" / "lifecycle_id.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("lifecycle_id_under_test", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class LifecycleIdScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        docs_dir = self.repo_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "workflow-config.json").write_text(
            json.dumps(
                {
                    "lifecycle_id_policy": {
                        "epoch_utc": "2020-02-02T02:02:00Z",
                        "hour_offset": 0,
                    }
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PROJECT_ROOT"] = str(self.repo_root)
        return subprocess.run(
            ["python3", str(SCRIPT_PATH), *args],
            cwd=self.repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    # ------------------------------------------------------------------
    # Existing prefix/ID encoding tests — updated for base36
    # Epoch: 2020-02-02T02:02:00Z = unix 1580608920
    # unix=1735691400: elapsed_hours=43078 → '0x8m'; elapsed_minutes=2584708; 2584708%36=16 → 'g' → prefix '0x8mg'
    # unix=1735773300: elapsed_hours=43101 → '0x99'; elapsed_minutes=2586073; 2586073%36=13 → 'd' → prefix '0x99d'
    # unix=1735779540: elapsed_hours=43102 → '0x9a'; elapsed_minutes=2586177; 2586177%36=9  → '9' → prefix '0x9a9'
    # ------------------------------------------------------------------

    def test_prefix_only_uses_epoch_hours_plus_minute_bucket(self) -> None:
        result = self.run_script("--prefix-only", "--unix-seconds", "1735691400")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "0x8mg")

    def test_bug_id_uses_shared_prefix(self) -> None:
        result = self.run_script("--kind", "bug", "--slug", "runtime-retry", "--unix-seconds", "1735773300")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "0x99d-bug runtime-retry")

    def test_wave_id_uses_shared_prefix(self) -> None:
        result = self.run_script("--kind", "wave", "--slug", "routine-behavior-contract", "--unix-seconds", "1735779540")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "0x9a9 routine-behavior-contract")

    def test_legacy_wave_id_uses_reserved_prefix(self) -> None:
        result = self.run_script("--kind", "wave", "--slug", "wave-zero-plans-and-specs", "--legacy")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "00000 wave-zero-plans-and-specs")

    def test_legacy_slug_still_validates_format(self) -> None:
        result = self.run_script("--kind", "wave", "--slug", "Plans-and-specs", "--legacy")
        self.assertEqual(result.returncode, 2)
        self.assertIn("slug must contain only lowercase letters, digits, and dashes", result.stderr)

    def test_timestamp_before_epoch_is_rejected(self) -> None:
        result = self.run_script("--prefix-only", "--unix-seconds", "1580608919")
        self.assertEqual(result.returncode, 2)
        self.assertIn("timestamp must not be earlier than the configured lifecycle epoch", result.stderr)

    def test_hour_offset_shifts_encoded_hours(self) -> None:
        mod = _load_module()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        base_policy = (mod.DEFAULT_EPOCH_UTC, 0)
        shifted = (mod.DEFAULT_EPOCH_UTC, 1024)
        self.assertNotEqual(
            mod.build_prefix(ts, policy=base_policy),
            mod.build_prefix(ts, policy=shifted),
        )


class DecodeBase36Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def test_decode_inverts_encode_for_zero(self) -> None:
        self.assertEqual(self.mod.decode_base36("0"), 0)

    def test_decode_inverts_encode_for_small_values(self) -> None:
        for n in (1, 35, 36, 100, 1296, 46656):
            encoded = self.mod.encode_base36(n)
            self.assertEqual(self.mod.decode_base36(encoded), n)

    def test_decode_inverts_encode_for_prefix_sized_values(self) -> None:
        mod = self.mod
        # Spot-check the three test timestamps
        for n in (43078, 43101, 43102):
            encoded = mod.encode_base36(n).rjust(4, "0")
            self.assertEqual(mod.decode_base36(encoded), n)

    def test_decode_full_5char_prefix_roundtrip(self) -> None:
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        policy = (mod.DEFAULT_EPOCH_UTC, 0)
        prefix = mod.build_prefix(ts, policy=policy)
        self.assertEqual(len(prefix), 5)
        n = mod.decode_base36(prefix)
        self.assertEqual(mod.encode_base36(n).rjust(5, "0"), prefix)


class ElapsedMinutes5thCharTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def _policy(self):
        return (self.mod.DEFAULT_EPOCH_UTC, 0)

    def test_5th_char_encodes_elapsed_minutes_mod_36(self) -> None:
        mod = self.mod
        epoch_unix = 1580608920  # 2020-02-02T02:02:00Z
        for unix_seconds, expected_mod in (
            (1735691400, 16),  # 2584708 % 36 = 16 → 'g'
            (1735773300, 13),  # 2586073 % 36 = 13 → 'd'
            (1735779540,  9),  # 2586177 % 36 =  9 → '9'
        ):
            ts = datetime.fromtimestamp(unix_seconds, tz=timezone.utc)
            elapsed_minutes = (unix_seconds - epoch_unix) // 60
            self.assertEqual(elapsed_minutes % 36, expected_mod)
            prefix = mod.build_prefix(ts, policy=self._policy())
            self.assertEqual(prefix[4], mod.BASE36_ALPHABET[expected_mod])

    def test_minute_boundary_increments_5th_char(self) -> None:
        mod = self.mod
        # Two timestamps 60 s apart should have different 5th chars when they
        # fall in different elapsed-minute buckets.
        epoch_unix = 1580608920
        # Pick a second aligned to a minute boundary
        ts1 = datetime.fromtimestamp(epoch_unix + 60, tz=timezone.utc)   # elapsed_minutes=1
        ts2 = datetime.fromtimestamp(epoch_unix + 120, tz=timezone.utc)  # elapsed_minutes=2
        policy = self._policy()
        p1 = mod.build_prefix(ts1, policy=policy)
        p2 = mod.build_prefix(ts2, policy=policy)
        self.assertNotEqual(p1[4], p2[4])


class BorrowFromFutureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        docs = self.repo_root / "docs"
        (docs / "workflow-config.json").parent.mkdir(parents=True, exist_ok=True)
        (docs / "workflow-config.json").write_text(
            json.dumps({"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}),
            encoding="utf-8",
        )
        (docs / "plans").mkdir()
        (docs / "waves").mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _policy(self):
        return (self.mod.DEFAULT_EPOCH_UTC, 0)

    def test_no_borrow_when_prefix_is_unused(self) -> None:
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0x8mg'
        prefix = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(prefix, "0x8mg")

    def test_no_scan_when_repo_root_is_none(self) -> None:
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        prefix = mod.next_available_prefix(ts, policy=self._policy(), repo_root=None)
        self.assertEqual(prefix, "0x8mg")

    def test_borrow_skips_taken_change_doc_in_plans(self) -> None:
        mod = self.mod
        # Simulate a staged change doc that owns the natural prefix
        (self.repo_root / "docs" / "plans" / "0x8mg-enh something.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0x8mg'
        prefix = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(prefix, "0x8mh")  # 0x8mg + 1 in base36

    def test_borrow_skips_taken_change_doc_in_waves(self) -> None:
        mod = self.mod
        wave_dir = self.repo_root / "docs" / "waves" / "0x8mg test-wave"
        wave_dir.mkdir(parents=True)
        (wave_dir / "0x8mg-enh foo.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        prefix = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        # Both the directory name AND the stem are scanned, but only one unique '0x8mg' entry; next is '0x8mh'
        self.assertEqual(prefix, "0x8mh")

    def test_borrow_skips_multiple_taken_prefixes(self) -> None:
        mod = self.mod
        plans = self.repo_root / "docs" / "plans"
        (plans / "0x8mg-enh first.md").touch()
        (plans / "0x8mh-enh second.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        prefix = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(prefix, "0x8mi")  # skips 0x8mg and 0x8mh

    def test_borrow_applies_to_change_ids(self) -> None:
        mod = self.mod
        plans = self.repo_root / "docs" / "plans"
        (plans / "0x8mg-enh taken.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        result = mod.build_id("enh", "new-thing", legacy=False, timestamp=ts, repo_root=self.repo_root, policy=self._policy())
        self.assertTrue(result.startswith("0x8mh-enh"), result)

    def test_borrow_applies_to_wave_ids(self) -> None:
        # AC-8: wave IDs must also go through collision checking
        mod = self.mod
        # Simulate an existing wave directory that owns '0x8mg'
        wave_dir = self.repo_root / "docs" / "waves" / "0x8mg old-wave"
        wave_dir.mkdir(parents=True)
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        result = mod.build_id("wave", "new-wave", legacy=False, timestamp=ts, repo_root=self.repo_root, policy=self._policy())
        self.assertEqual(result, "0x8mh new-wave")

    def test_legacy_bypasses_borrow_check(self) -> None:
        mod = self.mod
        # Even if '00000' were "taken" (it never is by live docs), legacy always uses it
        result = mod.build_id("wave", "baseline", legacy=True, repo_root=self.repo_root, policy=self._policy())
        self.assertEqual(result, "00000 baseline")

    def test_existing_prefixes_scans_plans_and_waves(self) -> None:
        mod = self.mod
        plans = self.repo_root / "docs" / "plans"
        (plans / "0x8mg-enh plan-doc.md").touch()
        wave_dir = self.repo_root / "docs" / "waves" / "0x99d old-wave"
        wave_dir.mkdir(parents=True)
        prefixes = mod._existing_prefixes(self.repo_root)
        self.assertIn("0x8mg", prefixes)
        self.assertIn("0x99d", prefixes)

    def test_existing_prefixes_ignores_wave_dot_md(self) -> None:
        # wave.md itself should not produce a spurious prefix entry
        mod = self.mod
        wave_dir = self.repo_root / "docs" / "waves" / "0x8mg my-wave"
        wave_dir.mkdir(parents=True)
        (wave_dir / "wave.md").touch()
        prefixes = mod._existing_prefixes(self.repo_root)
        # 'wave' stem doesn't match _PREFIX_RE → not added
        self.assertNotIn("wave.", prefixes)
        self.assertIn("0x8mg", prefixes)  # from directory name

    def test_rapid_successive_calls_return_unique_prefixes(self) -> None:
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0x8mg'
        p1 = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        p2 = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        p3 = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(p1, "0x8mg")
        self.assertEqual(p2, "0x8mh")
        self.assertEqual(p3, "0x8mi")

    def test_in_memory_floor_not_applied_when_time_advances(self) -> None:
        mod = self.mod
        ts1 = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0x8mg'
        ts2 = datetime.fromtimestamp(1735773300, tz=timezone.utc)  # → '0x99d'
        p1 = mod.next_available_prefix(ts1, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(p1, "0x8mg")
        p2 = mod.next_available_prefix(ts2, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(p2, "0x99d")

    def test_in_memory_floor_applies_without_repo_root(self) -> None:
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0x8mg'
        p1 = mod.next_available_prefix(ts, policy=self._policy(), repo_root=None)
        self.assertEqual(p1, "0x8mg")
        p2 = mod.next_available_prefix(ts, policy=self._policy(), repo_root=None)
        self.assertEqual(p2, "0x8mh")


if __name__ == "__main__":
    unittest.main()
