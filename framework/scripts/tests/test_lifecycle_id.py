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

    def test_prefix_only_uses_epoch_hours_plus_minute_bucket(self) -> None:
        result = self.run_script("--prefix-only", "--unix-seconds", "1735691400")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "1a26f")

    def test_bug_id_uses_shared_prefix(self) -> None:
        result = self.run_script("--kind", "bug", "--slug", "runtime-retry", "--unix-seconds", "1735773300")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "1a2x8-bug runtime-retry")

    def test_wave_id_uses_shared_prefix(self) -> None:
        result = self.run_script("--kind", "wave", "--slug", "routine-behavior-contract", "--unix-seconds", "1735779540")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "1a2yy routine-behavior-contract")

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
        spec = importlib.util.spec_from_file_location("lifecycle_id_under_test", SCRIPT_PATH)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        base_policy = (mod.DEFAULT_EPOCH_UTC, 0)
        shifted = (mod.DEFAULT_EPOCH_UTC, 1024)
        self.assertNotEqual(
            mod.build_prefix(ts, policy=base_policy),
            mod.build_prefix(ts, policy=shifted),
        )


if __name__ == "__main__":
    unittest.main()
