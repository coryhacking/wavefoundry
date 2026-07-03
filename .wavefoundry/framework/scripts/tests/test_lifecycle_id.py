from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


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
    # Encoding tests — integer-packed scheme (wave 131bt 131bu)
    # Epoch: 2020-02-02T02:02:00Z (date 2020-02-02)
    # Packing: base36((days_since_epoch * 288 + bucket_5min) mod 36^5), padded to 5.
    #
    # unix=1735691400 (2025-01-01T00:30:00Z) → days=1795, bucket=6  → '0b2w6'
    # unix=1735773300 (2025-01-01T23:15:00Z) → days=1795, bucket=279 → '0b33r'
    # unix=1735779540 (2025-01-02T00:59:00Z) → days=1796, bucket=11 → '0b34b'
    # ------------------------------------------------------------------

    def test_prefix_only_packs_days_and_bucket(self) -> None:
        result = self.run_script("--prefix-only", "--unix-seconds", "1735691400")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "0b2w6")

    def test_bug_id_uses_shared_prefix(self) -> None:
        result = self.run_script("--kind", "bug", "--slug", "runtime-retry", "--unix-seconds", "1735773300")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "0b33r-bug runtime-retry")

    def test_wave_id_uses_shared_prefix(self) -> None:
        result = self.run_script("--kind", "wave", "--slug", "routine-behavior-contract", "--unix-seconds", "1735779540")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "0b34b routine-behavior-contract")

    def test_legacy_wave_id_uses_reserved_prefix(self) -> None:
        result = self.run_script("--kind", "wave", "--slug", "wave-zero-plans-and-specs", "--legacy")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "00000 wave-zero-plans-and-specs")

    def test_legacy_slug_still_validates_format(self) -> None:
        result = self.run_script("--kind", "wave", "--slug", "Plans-and-specs", "--legacy")
        self.assertEqual(result.returncode, 2)
        self.assertIn("slug must contain only lowercase letters, digits, and dashes", result.stderr)

    def test_timestamp_before_epoch_is_rejected(self) -> None:
        # Epoch is 2020-02-02; use a timestamp clearly before that date.
        # (The new integer-packed scheme uses date-resolution comparison, so
        # sub-day-before-epoch timestamps land on day 0 — only different-date
        # pre-epoch inputs are rejected.)
        result = self.run_script("--prefix-only", "--unix-seconds", "0")
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
        # Round-trip a representative spread: small, day-boundary, day-mid, end-of-day,
        # and the very last packed value (36^5 - 1).
        for n in (0, 1, 287, 288, 1296, 517446, 517719, 60466175):
            encoded = mod.encode_base36(n).rjust(5, "0")
            self.assertEqual(mod.decode_base36(encoded), n)

    def test_decode_full_5char_prefix_roundtrip(self) -> None:
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        policy = (mod.DEFAULT_EPOCH_UTC, 0)
        prefix = mod.build_prefix(ts, policy=policy)
        self.assertEqual(len(prefix), 5)
        n = mod.decode_base36(prefix)
        self.assertEqual(mod.encode_base36(n).rjust(5, "0"), prefix)


class IntegerPackedPrefixTests(unittest.TestCase):
    """Wave 131bt (131bu): integer-packed prefix scheme — `(days * 288 + bucket_5min) mod 36^5`.

    Replaces the prior `elapsed_hours base36 + minute % 36` scheme. The 5th-char
    minute-mod-36 disambiguator wrapped every 36 minutes; the new scheme is fully
    monotonic across days within the 36^5 / 288 = 209,952-day (~575-year) horizon.
    """

    def setUp(self) -> None:
        self.mod = _load_module()

    def _policy(self):
        return (self.mod.DEFAULT_EPOCH_UTC, 0)

    def test_prefix_advances_with_bucket(self) -> None:
        """Two timestamps in different 5-minute buckets produce strictly-increasing prefixes."""
        mod = self.mod
        epoch_unix = 1580608920
        # 5 min = 300 sec apart, aligned to bucket boundary at minute 0
        ts1 = datetime.fromtimestamp(epoch_unix + 300, tz=timezone.utc)   # bucket+1
        ts2 = datetime.fromtimestamp(epoch_unix + 600, tz=timezone.utc)   # bucket+2
        policy = self._policy()
        p1 = mod.build_prefix(ts1, policy=policy)
        p2 = mod.build_prefix(ts2, policy=policy)
        self.assertLess(p1, p2)

    def test_same_bucket_produces_same_prefix(self) -> None:
        """Two timestamps within the same 5-minute window produce identical prefixes.

        That's the documented behavior: 5-minute resolution is the bucket size.
        Higher resolution would require a different bit budget."""
        mod = self.mod
        epoch_unix = 1580608920
        ts1 = datetime.fromtimestamp(epoch_unix + 60, tz=timezone.utc)
        ts2 = datetime.fromtimestamp(epoch_unix + 120, tz=timezone.utc)
        policy = self._policy()
        self.assertEqual(mod.build_prefix(ts1, policy=policy),
                         mod.build_prefix(ts2, policy=policy))

    def test_day_boundary_increments_prefix(self) -> None:
        """A prefix from midnight UTC of the next day lex-sorts after every prefix on the current day."""
        mod = self.mod
        epoch_unix = 1580608920
        # End of UTC day 0 vs start of UTC day 1
        last_bucket_day0 = datetime.fromtimestamp(epoch_unix + 23*3600 + 55*60, tz=timezone.utc)
        first_bucket_day1 = datetime.fromtimestamp(epoch_unix + 24*3600, tz=timezone.utc)
        policy = self._policy()
        p_end = mod.build_prefix(last_bucket_day0, policy=policy)
        p_start = mod.build_prefix(first_bucket_day1, policy=policy)
        self.assertLess(p_end, p_start)

    def test_monotonic_across_full_day(self) -> None:
        """No lex-order violations across all 1440 minutes of a UTC day."""
        mod = self.mod
        epoch_unix = 1580608920
        policy = self._policy()
        prev = ""
        for minute in range(1440):
            ts = datetime.fromtimestamp(epoch_unix + minute * 60, tz=timezone.utc)
            prefix = mod.build_prefix(ts, policy=policy)
            self.assertGreaterEqual(prefix, prev, f"Lex regression at minute {minute}: {prev!r} → {prefix!r}")
            prev = prefix


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
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0b2w6'
        prefix = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(prefix, "0b2w6")

    def test_no_scan_when_repo_root_is_none(self) -> None:
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        prefix = mod.next_available_prefix(ts, policy=self._policy(), repo_root=None)
        self.assertEqual(prefix, "0b2w6")

    def test_borrow_skips_taken_adr(self) -> None:  # 1p45b AC-1
        adr = self.repo_root / "docs" / "architecture" / "decisions"
        adr.mkdir(parents=True)
        (adr / "0b2w6-adr-something.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0b2w6'
        prefix = self.mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(prefix, "0b2w7")  # ADR stem is in the dedup set

    def test_existing_prefixes_union_of_plans_waves_adrs(self) -> None:  # 1p45b AC-5
        (self.repo_root / "docs" / "plans" / "aaaaa-enh p.md").touch()
        (self.repo_root / "docs" / "waves" / "bbbbb w").mkdir()
        adr = self.repo_root / "docs" / "architecture" / "decisions"
        adr.mkdir(parents=True)
        (adr / "ccccc-adr-x.md").touch()
        found = self.mod._existing_prefixes(self.repo_root)
        self.assertTrue({"aaaaa", "bbbbb", "ccccc"} <= found)

    def test_peek_then_commit_return_same_stem(self) -> None:  # 1p45b AC-3
        (self.repo_root / "docs" / "plans" / "0b2w6-enh taken.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        kw = dict(legacy=False, timestamp=ts, repo_root=self.repo_root, policy=self._policy())
        peek = self.mod.build_id("enhancement", "x", commit=False, **kw)
        commit = self.mod.build_id("enhancement", "x", commit=True, **kw)
        self.assertEqual(peek, commit)
        self.assertTrue(peek.startswith("0b2w7-"))  # both skip the taken 0b2w6

    def test_unsupplied_repo_root_uses_discover_fallback(self) -> None:  # 1p45b AC-4
        (self.repo_root / "docs" / "plans" / "0b2w6-enh taken.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        with patch.object(self.mod, "discover_repo_root", return_value=self.repo_root):
            prefix = self.mod.next_available_prefix(ts, policy=self._policy())  # repo_root unsupplied
        self.assertEqual(prefix, "0b2w7")  # discovered repo deduped (no silent empty-set)

    def test_explicit_none_repo_root_still_no_scan(self) -> None:  # 1p45b AC-4 (preserve opt-out)
        (self.repo_root / "docs" / "plans" / "0b2w6-enh taken.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        # Even though discover would find the repo, an explicit None opts out.
        with patch.object(self.mod, "discover_repo_root", return_value=self.repo_root):
            prefix = self.mod.next_available_prefix(ts, policy=self._policy(), repo_root=None)
        self.assertEqual(prefix, "0b2w6")  # no scan → natural prefix

    def test_cli_reminder_on_stderr_stdout_is_bare_id(self) -> None:  # 1p45b AC-7
        out, err = io.StringIO(), io.StringIO()
        with patch.object(self.mod, "discover_repo_root", return_value=self.repo_root), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = self.mod.main(["--kind", "change", "--slug", "demo"])
        self.assertEqual(rc, 0)
        self.assertNotIn("MCP", out.getvalue())          # stdout is ID-only
        self.assertIn("-change demo", out.getvalue().strip())
        self.assertIn("wave_new_", err.getvalue())        # reminder on stderr

    def test_cli_prefix_only_no_reminder(self) -> None:  # 1p45b decision (prefix-only exempt)
        err = io.StringIO()
        with patch.object(self.mod, "discover_repo_root", return_value=self.repo_root), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = self.mod.main(["--prefix-only"])
        self.assertEqual(rc, 0)
        self.assertEqual(err.getvalue(), "")  # no reminder for the prefix utility

    def test_borrow_skips_taken_change_doc_in_plans(self) -> None:
        mod = self.mod
        # Simulate a staged change doc that owns the natural prefix
        (self.repo_root / "docs" / "plans" / "0b2w6-enh something.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0b2w6'
        prefix = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(prefix, "0b2w7")  # 0b2w6 + 1 in base36

    def test_borrow_skips_taken_change_doc_in_waves(self) -> None:
        mod = self.mod
        wave_dir = self.repo_root / "docs" / "waves" / "0b2w6 test-wave"
        wave_dir.mkdir(parents=True)
        (wave_dir / "0b2w6-enh foo.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        prefix = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        # Both the directory name AND the stem are scanned, but only one unique '0b2w6' entry; next is '0b2w7'
        self.assertEqual(prefix, "0b2w7")

    def test_borrow_skips_multiple_taken_prefixes(self) -> None:
        mod = self.mod
        plans = self.repo_root / "docs" / "plans"
        (plans / "0b2w6-enh first.md").touch()
        (plans / "0b2w7-enh second.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        prefix = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(prefix, "0b2w8")  # skips 0b2w6 and 0b2w7

    def test_borrow_applies_to_change_ids(self) -> None:
        mod = self.mod
        plans = self.repo_root / "docs" / "plans"
        (plans / "0b2w6-enh taken.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        result = mod.build_id("enh", "new-thing", legacy=False, timestamp=ts, repo_root=self.repo_root, policy=self._policy())
        self.assertTrue(result.startswith("0b2w7-enh"), result)

    def test_borrow_applies_to_wave_ids(self) -> None:
        # AC-8: wave IDs must also go through collision checking
        mod = self.mod
        # Simulate an existing wave directory that owns '0b2w6'
        wave_dir = self.repo_root / "docs" / "waves" / "0b2w6 old-wave"
        wave_dir.mkdir(parents=True)
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        result = mod.build_id("wave", "new-wave", legacy=False, timestamp=ts, repo_root=self.repo_root, policy=self._policy())
        self.assertEqual(result, "0b2w7 new-wave")

    def test_legacy_bypasses_borrow_check(self) -> None:
        mod = self.mod
        # Even if '00000' were "taken" (it never is by live docs), legacy always uses it
        result = mod.build_id("wave", "baseline", legacy=True, repo_root=self.repo_root, policy=self._policy())
        self.assertEqual(result, "00000 baseline")

    def test_existing_prefixes_scans_plans_and_waves(self) -> None:
        mod = self.mod
        plans = self.repo_root / "docs" / "plans"
        (plans / "0b2w6-enh plan-doc.md").touch()
        wave_dir = self.repo_root / "docs" / "waves" / "0b33r old-wave"
        wave_dir.mkdir(parents=True)
        prefixes = mod._existing_prefixes(self.repo_root)
        self.assertIn("0b2w6", prefixes)
        self.assertIn("0b33r", prefixes)

    def test_existing_prefixes_ignores_wave_dot_md(self) -> None:
        # wave.md itself should not produce a spurious prefix entry
        mod = self.mod
        wave_dir = self.repo_root / "docs" / "waves" / "0b2w6 my-wave"
        wave_dir.mkdir(parents=True)
        (wave_dir / "wave.md").touch()
        prefixes = mod._existing_prefixes(self.repo_root)
        # 'wave' stem doesn't match _PREFIX_RE → not added
        self.assertNotIn("wave.", prefixes)
        self.assertIn("0b2w6", prefixes)  # from directory name

    def test_rapid_successive_calls_return_unique_prefixes(self) -> None:
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0b2w6'
        p1 = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        p2 = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        p3 = mod.next_available_prefix(ts, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(p1, "0b2w6")
        self.assertEqual(p2, "0b2w7")
        self.assertEqual(p3, "0b2w8")

    def test_in_memory_floor_not_applied_when_time_advances(self) -> None:
        mod = self.mod
        ts1 = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0b2w6'
        ts2 = datetime.fromtimestamp(1735773300, tz=timezone.utc)  # → '0b33r'
        p1 = mod.next_available_prefix(ts1, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(p1, "0b2w6")
        p2 = mod.next_available_prefix(ts2, policy=self._policy(), repo_root=self.repo_root)
        self.assertEqual(p2, "0b33r")

    def test_in_memory_floor_applies_without_repo_root(self) -> None:
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0b2w6'
        p1 = mod.next_available_prefix(ts, policy=self._policy(), repo_root=None)
        self.assertEqual(p1, "0b2w6")
        p2 = mod.next_available_prefix(ts, policy=self._policy(), repo_root=None)
        self.assertEqual(p2, "0b2w7")


class PeekWithoutConsumeTests(unittest.TestCase):
    """Wave 1p3dk / 1p3ds: ``commit=False`` previews the next prefix without
    advancing the in-process counter. ``dry_run`` MCP tool paths use this so
    a preview followed by an apply call returns the same id rather than
    skipping one."""

    def setUp(self) -> None:
        self.mod = _load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        (self.repo_root / "docs" / "plans").mkdir(parents=True)
        (self.repo_root / "docs" / "waves").mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _policy(self):
        return (self.mod.DEFAULT_EPOCH_UTC, 0)

    def test_peek_returns_a_prefix(self) -> None:
        """AC-1: ``commit=False`` returns the same prefix value as ``commit=True``
        would have at the same point in time, but does not mutate state."""
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0b2w6'
        prefix = mod.next_available_prefix(
            ts, policy=self._policy(), repo_root=self.repo_root, commit=False,
        )
        self.assertEqual(prefix, "0b2w6")

    def test_peek_does_not_advance_counter(self) -> None:
        """AC-2: two consecutive ``commit=False`` calls return the same prefix
        — the second is not pushed past the first."""
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0b2w6'
        p1 = mod.next_available_prefix(
            ts, policy=self._policy(), repo_root=self.repo_root, commit=False,
        )
        p2 = mod.next_available_prefix(
            ts, policy=self._policy(), repo_root=self.repo_root, commit=False,
        )
        self.assertEqual(p1, p2, "peek must be idempotent")
        self.assertEqual(p2, "0b2w6")

    def test_peek_then_commit_returns_same_prefix(self) -> None:
        """AC-3: peek followed by commit returns the prefix the peek previewed.
        Only the commit advances state."""
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0b2w6'
        previewed = mod.next_available_prefix(
            ts, policy=self._policy(), repo_root=self.repo_root, commit=False,
        )
        committed = mod.next_available_prefix(
            ts, policy=self._policy(), repo_root=self.repo_root, commit=True,
        )
        self.assertEqual(previewed, committed)

    def test_commit_advances_subsequent_calls(self) -> None:
        """After a commit, a fresh peek sees the advanced counter."""
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0b2w6'
        committed = mod.next_available_prefix(
            ts, policy=self._policy(), repo_root=self.repo_root, commit=True,
        )
        self.assertEqual(committed, "0b2w6")
        next_peek = mod.next_available_prefix(
            ts, policy=self._policy(), repo_root=self.repo_root, commit=False,
        )
        self.assertEqual(next_peek, "0b2w7")

    def test_backward_compatible_default_is_commit(self) -> None:
        """AC-8: callers that omit ``commit`` see the prior behavior — the
        prefix is consumed exactly as before."""
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)  # → '0b2w6'
        p1 = mod.next_available_prefix(
            ts, policy=self._policy(), repo_root=self.repo_root,
        )
        p2 = mod.next_available_prefix(
            ts, policy=self._policy(), repo_root=self.repo_root,
        )
        self.assertEqual(p1, "0b2w6")
        self.assertEqual(p2, "0b2w7")  # advanced — default commits

    def test_peek_respects_filesystem_claims(self) -> None:
        """AC-9: when a concurrent process plants a file at the peeked prefix,
        peek still returns a *valid* free prefix — the filesystem scan
        prevents handing out a colliding id."""
        mod = self.mod
        # Plant a file claiming the natural prefix
        (self.repo_root / "docs" / "plans" / "0b2w6-enh planted.md").touch()
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        prefix = mod.next_available_prefix(
            ts, policy=self._policy(), repo_root=self.repo_root, commit=False,
        )
        self.assertEqual(prefix, "0b2w7", "must skip externally-claimed prefix")

    def test_build_id_propagates_commit_flag(self) -> None:
        """``build_id`` exposes the same ``commit`` parameter so callers don't
        have to drop down to ``next_available_prefix`` to peek."""
        mod = self.mod
        ts = datetime.fromtimestamp(1735691400, tz=timezone.utc)
        peeked = mod.build_id(
            "enh", "test-slug", legacy=False,
            timestamp=ts, policy=self._policy(), repo_root=self.repo_root,
            commit=False,
        )
        committed = mod.build_id(
            "enh", "test-slug", legacy=False,
            timestamp=ts, policy=self._policy(), repo_root=self.repo_root,
            commit=True,
        )
        # Both should produce the same id since peek did not advance state.
        self.assertEqual(peeked, committed)
        self.assertTrue(peeked.startswith("0b2w6-enh"))

    def test_build_id_legacy_bypasses_commit_logic(self) -> None:
        """``legacy=True`` returns the reserved baseline prefix `00000`
        regardless of ``commit`` — the lifecycle counter is not consulted."""
        mod = self.mod
        result = mod.build_id(
            "wave", "legacy-slug", legacy=True, commit=False,
        )
        self.assertTrue(result.startswith("00000 "))


# ----------------------------------------------------------------------
# Scheme v2 — daily time index + 12-bit deterministic blake2s entropy
# (wave 1p9q0). Fixed vectors: epoch 2026-01-01T00:00:00Z, offset 100000.
# ----------------------------------------------------------------------

_V2_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
_V2_OFFSET = 100_000


def _v2_policy(offset: int = _V2_OFFSET):
    return (_V2_EPOCH, 0, offset, "v2")


class V2EncodingTests(unittest.TestCase):
    """AC-1 / AC-2 / AC-2b / AC-5 (encoder side)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def test_v2_value_formula_and_min_width(self) -> None:  # AC-1
        mod = self.mod
        ts = datetime(2026, 1, 11, 9, 0, tzinfo=timezone.utc)  # day_index = 10
        prefix = mod.build_prefix(ts, policy=_v2_policy(), kind="enh", slug="golden-vector")
        expected = _V2_OFFSET + 10 * 4096 + mod._v2_entropy("enh", "golden-vector")
        self.assertEqual(mod.decode_base36(prefix), expected)
        self.assertEqual(len(prefix), 5)
        self.assertGreater(mod.decode_base36(prefix), _V2_OFFSET)

    def test_v2_day_bands_never_overlap(self) -> None:  # AC-1
        """decode(day d) < decode(day d+1) for ANY entropy — max-entropy day d
        still sorts below min-entropy day d+1 (bands are 4096 wide)."""
        mod = self.mod
        day_d_max = _V2_OFFSET + 7 * 4096 + 4095
        day_d1_min = _V2_OFFSET + 8 * 4096 + 0
        self.assertLess(day_d_max, day_d1_min)
        # And through the real encoder with real (different-entropy) slugs:
        d7 = mod.build_prefix(datetime(2026, 1, 8, 23, 59, tzinfo=timezone.utc),
                              policy=_v2_policy(), kind="bug", slug="beta-two")
        d8 = mod.build_prefix(datetime(2026, 1, 9, 0, 0, tzinfo=timezone.utc),
                              policy=_v2_policy(), kind="bug", slug="alpha-one")
        self.assertLess(mod.decode_base36(d7), mod.decode_base36(d8))
        self.assertLess(d7, d8)  # lex order == value order at equal width

    def test_v2_base_encoder_is_deterministic_across_module_loads(self) -> None:  # AC-2
        """Same (kind, slug, day, epoch, offset) → same BASE prefix across
        independent module loads (fresh process state). Scoped to build_prefix,
        NOT next_available_prefix (which linear-probes past on-disk IDs)."""
        ts = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc)
        first = _load_module().build_prefix(ts, policy=_v2_policy(), kind="feat", slug="alpha-one")
        second = _load_module().build_prefix(ts, policy=_v2_policy(), kind="feat", slug="alpha-one")
        self.assertEqual(first, second)

    def test_v2_pre_verified_golden_slugs_have_distinct_tails(self) -> None:  # AC-2
        """Distinct-tail asserted with pre-verified golden slugs (entropies 36 /
        2921 / 1947) — NOT universal injectivity; 4096 buckets birthday-collide."""
        mod = self.mod
        entropies = {slug: mod._v2_entropy("bug", slug)
                     for slug in ("alpha-one", "beta-two", "gamma-three")}
        self.assertEqual(entropies, {"alpha-one": 36, "beta-two": 2921, "gamma-three": 1947})
        ts = datetime(2026, 3, 1, tzinfo=timezone.utc)
        prefixes = {mod.build_prefix(ts, policy=_v2_policy(), kind="bug", slug=s)
                    for s in entropies}
        self.assertEqual(len(prefixes), 3)

    def test_v2_golden_vector_freezes_entropy_contract(self) -> None:  # AC-2b
        """THE contract freeze: (enh, golden-vector, day 10, epoch 2026-01-01,
        offset 100000) → exactly '0321q'. This hardcoded literal locks blake2s +
        digest_size 8 + big-endian int + `kind + "\\x00" + slug` UTF-8 + `% 4096`.
        If this test fails, the entropy mapping changed — that is a NEW SCHEME
        VERSION, not a refactor."""
        ts = datetime(2026, 1, 11, 9, 0, tzinfo=timezone.utc)
        prefix = self.mod.build_prefix(ts, policy=_v2_policy(), kind="enh", slug="golden-vector")
        self.assertEqual(prefix, "0321q")

    def test_v2_no_wall_clock_or_rng_in_entropy(self) -> None:  # AC-2
        """Entropy depends only on (kind, slug) — repeated calls agree and a
        different timestamp changes only the day band, not the entropy tail."""
        mod = self.mod
        e1 = mod._v2_entropy("enh", "stable-slug")
        e2 = mod._v2_entropy("enh", "stable-slug")
        self.assertEqual(e1, e2)
        p_day1 = mod.build_prefix(datetime(2026, 1, 2, tzinfo=timezone.utc),
                                  policy=_v2_policy(), kind="enh", slug="stable-slug")
        p_day2 = mod.build_prefix(datetime(2026, 1, 3, tzinfo=timezone.utc),
                                  policy=_v2_policy(), kind="enh", slug="stable-slug")
        self.assertEqual(mod.decode_base36(p_day2) - mod.decode_base36(p_day1), 4096)

    def test_v2_six_char_overflow_never_wraps(self) -> None:  # AC-5
        mod = self.mod
        far = datetime(2080, 1, 1, tzinfo=timezone.utc)  # ~54 yr — past the horizon
        with contextlib.redirect_stderr(io.StringIO()):
            prefix = mod.build_prefix(far, policy=_v2_policy(619_519), kind="bug", slug="far-future")
        self.assertEqual(len(prefix), 6)
        self.assertGreaterEqual(mod.decode_base36(prefix), 36 ** 5)
        self.assertGreater(mod.decode_base36(prefix), mod.decode_base36("zzzzz"))
        # A 6-char string can never equal a 5-char one — width alone separates them.

    def test_v2_near_horizon_warning_fires_within_threshold_only(self) -> None:  # AC-5
        mod = self.mod
        # ~1 year from the ceiling: warning fires.
        near = datetime(2065, 6, 1, tzinfo=timezone.utc)
        offset = 36 ** 5 - 4096 * 400 - (near.date() - _V2_EPOCH.date()).days * 4096
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            mod.build_prefix(near, policy=(_V2_EPOCH, 0, offset, "v2"), kind="bug", slug="x")
        self.assertIn("5-character ID space", err.getvalue())
        # Far from the ceiling: silent.
        err2 = io.StringIO()
        with contextlib.redirect_stderr(err2):
            mod.build_prefix(datetime(2026, 6, 1, tzinfo=timezone.utc),
                             policy=_v2_policy(), kind="bug", slug="x")
        self.assertEqual(err2.getvalue(), "")

    def test_v2_near_horizon_threshold_boundary_exact(self) -> None:  # AC-5 (delivery qa)
        """Boundary-adjacent cases on BOTH sides of the exact threshold, so a
        widened/narrowed `_NEAR_HORIZON_MARGIN` or a flipped comparison fails."""
        mod = self.mod
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)  # day 0: value = offset + entropy
        e = mod._v2_entropy("bug", "x")
        threshold = 36 ** 5 - mod._NEAR_HORIZON_MARGIN
        # value == threshold - 1 → silent.
        err_below = io.StringIO()
        with contextlib.redirect_stderr(err_below):
            mod.build_prefix(ts, policy=(_V2_EPOCH, 0, threshold - 1 - e, "v2"),
                             kind="bug", slug="x")
        self.assertEqual(err_below.getvalue(), "")
        # value == threshold → fires.
        err_at = io.StringIO()
        with contextlib.redirect_stderr(err_at):
            mod.build_prefix(ts, policy=(_V2_EPOCH, 0, threshold - e, "v2"),
                             kind="bug", slug="x")
        self.assertIn("5-character ID space", err_at.getvalue())

    def test_v2_rejects_pre_epoch_timestamp(self) -> None:
        with self.assertRaises(ValueError):
            self.mod.build_prefix(datetime(2025, 12, 31, tzinfo=timezone.utc),
                                  policy=_v2_policy(), kind="bug", slug="x")


class V2PolicyLoaderTests(unittest.TestCase):
    """AC-8 malformed-v2 fixtures + widened-loader behavior (Req 10)."""

    def setUp(self) -> None:
        self.mod = _load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        (self.repo_root / "docs").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_policy(self, policy) -> None:
        (self.repo_root / "docs" / "workflow-config.json").write_text(
            json.dumps({"lifecycle_id_policy": policy}), encoding="utf-8",
        )

    def test_valid_v2_policy_loads_four_tuple(self) -> None:
        self._write_policy({"epoch_utc": "2026-01-01T00:00:00Z", "offset": 100000,
                            "scheme_version": "v2"})
        epoch, hour_offset, offset, scheme = self.mod.load_lifecycle_policy(self.repo_root)
        self.assertEqual((offset, scheme), (100000, "v2"))
        self.assertEqual(epoch.year, 2026)

    def test_absent_policy_block_falls_back_to_v1_defaults(self) -> None:
        (self.repo_root / "docs" / "workflow-config.json").write_text("{}", encoding="utf-8")
        epoch, hour_offset, offset, scheme = self.mod.load_lifecycle_policy(self.repo_root)
        self.assertEqual(scheme, "v1")
        self.assertEqual(epoch, self.mod.DEFAULT_EPOCH_UTC)

    def test_unknown_scheme_version_raises(self) -> None:
        self._write_policy({"epoch_utc": "2026-01-01T00:00:00Z", "scheme_version": "v3"})
        with self.assertRaises(ValueError):
            self.mod.load_lifecycle_policy(self.repo_root)

    def test_v2_missing_offset_raises(self) -> None:
        self._write_policy({"epoch_utc": "2026-01-01T00:00:00Z", "scheme_version": "v2"})
        with self.assertRaises(ValueError):
            self.mod.load_lifecycle_policy(self.repo_root)

    def test_v2_bool_offset_raises(self) -> None:
        self._write_policy({"epoch_utc": "2026-01-01T00:00:00Z", "scheme_version": "v2",
                            "offset": True})
        with self.assertRaises(ValueError):
            self.mod.load_lifecycle_policy(self.repo_root)

    def test_v2_below_band_offset_raises(self) -> None:
        # A silently-defaulted or under-band offset would mint in/below the
        # reserved band — must fail loudly, never mint.
        self._write_policy({"epoch_utc": "2026-01-01T00:00:00Z", "scheme_version": "v2",
                            "offset": 100})
        with self.assertRaises(ValueError):
            self.mod.load_lifecycle_policy(self.repo_root)

    def test_v2_missing_epoch_raises(self) -> None:
        self._write_policy({"scheme_version": "v2", "offset": 100000})
        with self.assertRaises(ValueError):
            self.mod.load_lifecycle_policy(self.repo_root)

    def test_v2_nonzero_node_bits_raises(self) -> None:
        self._write_policy({"epoch_utc": "2026-01-01T00:00:00Z", "scheme_version": "v2",
                            "offset": 100000, "node_bits": 4})
        with self.assertRaises(ValueError):
            self.mod.load_lifecycle_policy(self.repo_root)

    def test_unparseable_config_warns_and_falls_back_to_v1(self) -> None:
        (self.repo_root / "docs" / "workflow-config.json").write_text("{corrupt", encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            epoch, hour_offset, offset, scheme = self.mod.load_lifecycle_policy(self.repo_root)
        self.assertEqual(scheme, "v1")
        self.assertIn("could not parse", err.getvalue())

    def test_legacy_two_tuple_policy_still_accepted(self) -> None:
        """~20 existing call sites pass (epoch, hour_offset) 2-tuples — those
        are v1 by construction and must stay byte-unchanged."""
        mod = self.mod
        ts = datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc)
        self.assertEqual(mod.build_prefix(ts, policy=(mod.DEFAULT_EPOCH_UTC, 0)), "0b2w6")

    def test_malformed_policy_tuple_length_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.mod.build_prefix(policy=(self.mod.DEFAULT_EPOCH_UTC, 0, 100))  # type: ignore[arg-type]


class V2ProvisioningHelperTests(unittest.TestCase):
    """AC-3 / AC-3b / AC-4 — the pure compute half of provisioning."""

    def setUp(self) -> None:
        self.mod = _load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        (self.repo_root / "docs").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_migrated_offset_clears_scanned_max_plus_margin(self) -> None:  # AC-3
        mod = self.mod
        wave_dir = self.repo_root / "docs" / "waves" / "1p9pk example-wave"
        wave_dir.mkdir(parents=True)
        scanned = mod.scan_max_prefix_value(self.repo_root)
        self.assertEqual(scanned, mod.decode_base36("1p9pk"))  # 2,858,600
        offset = mod.compute_migrated_offset(scanned)
        self.assertGreaterEqual(offset, scanned + mod.V1_MERGE_MARGIN)
        # Lands in the 1xxxx band, continuing the existing sequence.
        self.assertEqual(mod.encode_base36(offset).rjust(5, "0")[0], "1")

    def test_margin_is_a_named_constant_sized_for_the_merge_window(self) -> None:  # AC-3
        # ≥ ~1 year of v1 drift at 288/day (operator-tuned from 3 yr post-council).
        self.assertGreaterEqual(self.mod.V1_MERGE_MARGIN, 288 * 365)

    def test_legacy_baseline_prefix_does_not_count_as_history(self) -> None:
        (self.repo_root / "docs" / "waves" / "00000 wave-zero").mkdir(parents=True)
        self.assertIsNone(self.mod.scan_max_prefix_value(self.repo_root))

    def test_fresh_offset_band_and_second_char(self) -> None:  # AC-3b
        mod = self.mod
        for seed in ("2026-07-03T10:00:00+00:00|alpha",
                     "2026-07-03T10:00:00+00:00|beta",
                     "2027-01-01T00:00:00+00:00|gamma"):
            offset = mod.compute_fresh_offset(seed)
            self.assertGreaterEqual(offset, 36 ** 3)
            self.assertLess(offset, 619_520)
            # Worst case day-0 value never renders `0000x`; second char in 1..d
            # even with max entropy.
            worst_day0 = mod.encode_base36(offset + 4095).rjust(5, "0")
            self.assertEqual(worst_day0[0], "0")
            self.assertIn(worst_day0[1], "123456789abcd")

    def test_fresh_offset_deterministic_and_seeds_diverge(self) -> None:  # AC-3b
        mod = self.mod
        s1 = "2026-07-03T10:00:00+00:00|alpha"
        s2 = "2026-07-03T10:00:00+00:00|beta"
        self.assertEqual(mod.compute_fresh_offset(s1), mod.compute_fresh_offset(s1))
        self.assertNotEqual(mod.compute_fresh_offset(s1), mod.compute_fresh_offset(s2))

    def test_worst_case_offset_guarantees_forty_year_floor(self) -> None:  # AC-3b
        # Top-of-band offset + 14,610 days (40.0 yr) + max entropy still < 36^5.
        self.assertLess(619_519 + 14_610 * 4096 + 4095, 36 ** 5)
        # And one day fewer than 40 years is NOT yet 6-char for the top offset:
        self.assertLess(619_519 + 14_609 * 4096 + 4095, 36 ** 5)
        # Bind the literals to the implementation constants so a band change
        # cannot silently invalidate this arithmetic (delivery qa).
        self.assertEqual(self.mod.FRESH_OFFSET_CAP, 619_520)
        self.assertEqual(self.mod.FRESH_OFFSET_FLOOR, 36 ** 3)

    def test_scan_max_ignores_six_char_word_like_matches(self) -> None:  # delivery red-team F2
        """v1 history is 5-char by construction; a 6-char token in the scan is
        always a word-like false positive (`review` decodes above 36^5 and would
        otherwise freeze an offset that makes every ID 6-char from day one)."""
        mod = self.mod
        plans = self.repo_root / "docs" / "plans"
        plans.mkdir(parents=True, exist_ok=True)
        (plans / "review-notes.md").write_text("x", encoding="utf-8")
        self.assertIsNone(mod.scan_max_prefix_value(self.repo_root))
        # A genuine 5-char prefix alongside it still wins the scan.
        (plans / "1p9pk-enh real.md").write_text("x", encoding="utf-8")
        self.assertEqual(mod.scan_max_prefix_value(self.repo_root),
                         mod.decode_base36("1p9pk"))

    def test_provisioning_epoch_is_install_date_never_stale(self) -> None:  # AC-4
        mod = self.mod
        now = datetime(2026, 7, 3, 18, 45, tzinfo=timezone.utc)
        self.assertEqual(mod.compute_provisioning_epoch(now), "2026-07-03T00:00:00Z")
        # Compute-or-error: naive datetime is rejected, no silent default.
        with self.assertRaises(ValueError):
            mod.compute_provisioning_epoch(datetime(2026, 7, 3))
        with self.assertRaises(ValueError):
            mod.compute_provisioning_epoch(None)  # type: ignore[arg-type]

    def test_compute_v2_policy_fields_fresh_vs_migrated(self) -> None:  # AC-3/3b/4
        mod = self.mod
        now = datetime(2026, 7, 3, 18, 45, tzinfo=timezone.utc)
        fresh = mod.compute_v2_policy_fields(self.repo_root, now, "proj")
        self.assertEqual(fresh["scheme_version"], "v2")
        self.assertEqual(fresh["epoch_utc"], "2026-07-03T00:00:00Z")
        self.assertIn("project_seed", fresh)
        self.assertLess(fresh["offset"], 619_520)
        (self.repo_root / "docs" / "waves" / "1p9pk w").mkdir(parents=True)
        migrated = mod.compute_v2_policy_fields(self.repo_root, now, "proj")
        self.assertNotIn("project_seed", migrated)
        self.assertEqual(migrated["offset"],
                         mod.decode_base36("1p9pk") + mod.V1_MERGE_MARGIN)


class V2WidthToleranceTests(unittest.TestCase):
    """AC-6a — 6-char IDs flow through the prefix regex and dedup scan."""

    def setUp(self) -> None:
        self.mod = _load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        (self.repo_root / "docs" / "plans").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_prefix_re_accepts_six_char_ids(self) -> None:
        m5 = self.mod._PREFIX_RE.match("1p9pk-enh some-slug")
        m6 = self.mod._PREFIX_RE.match("100001-enh some-slug")
        self.assertIsNotNone(m5)
        self.assertIsNotNone(m6)
        self.assertEqual(m6.group(1), "100001")

    def test_dedup_scan_sees_six_char_prefixes(self) -> None:
        (self.repo_root / "docs" / "plans" / "100001-enh future.md").write_text("x", encoding="utf-8")
        self.assertIn("100001", self.mod._existing_prefixes(self.repo_root))

    def test_linear_probe_crosses_the_width_boundary(self) -> None:
        """A mint whose base is `zzzzz` with the slot taken probes to the
        6-char `100000` rather than wrapping or erroring."""
        mod = self.mod
        (self.repo_root / "docs" / "plans" / "zzzzz-enh last-five.md").write_text("x", encoding="utf-8")
        # v2 policy engineered so the base value is exactly 36^5 - 1 (zzzzz):
        # entropy('bug','x') is fixed; pick offset so offset + 0*4096 + e = 36^5 - 1.
        e = mod._v2_entropy("bug", "x")
        pol = (datetime(2026, 1, 1, tzinfo=timezone.utc), 0, 36 ** 5 - 1 - e, "v2")
        with contextlib.redirect_stderr(io.StringIO()):
            prefix = mod.next_available_prefix(
                datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                policy=pol, repo_root=self.repo_root, kind="bug", slug="x",
            )
        self.assertEqual(prefix, "100000")


class V2DualSchemeTests(unittest.TestCase):
    """AC-8 — config-driven cutover; v1 byte-unchanged, v2 active when written."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def test_v1_config_mints_current_encoding_unchanged(self) -> None:
        mod = self.mod
        ts = datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc)
        four_tuple_v1 = (mod.DEFAULT_EPOCH_UTC, 0, 0, "v1")
        self.assertEqual(mod.build_prefix(ts, policy=four_tuple_v1), "0b2w6")
        # kind/slug are ignored under v1 — identical output either way.
        self.assertEqual(mod.build_prefix(ts, policy=four_tuple_v1, kind="bug", slug="any"),
                         "0b2w6")

    def test_v2_config_mints_new_encoding(self) -> None:
        mod = self.mod
        ts = datetime(2026, 1, 11, 9, 0, tzinfo=timezone.utc)
        self.assertEqual(
            mod.build_prefix(ts, policy=_v2_policy(), kind="enh", slug="golden-vector"),
            "0321q",
        )

    def test_same_repo_probe_stays_dense_under_v2(self) -> None:
        """Req 12 — the linear probe keeps same-repo re-mints dense/ordered."""
        mod = self.mod
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "docs" / "plans").mkdir(parents=True)
        ts = datetime(2026, 1, 11, 9, 0, tzinfo=timezone.utc)
        base = mod.build_prefix(ts, policy=_v2_policy(), kind="enh", slug="golden-vector")
        (root / "docs" / "plans" / f"{base}-enh taken.md").write_text("x", encoding="utf-8")
        probed = mod.next_available_prefix(ts, policy=_v2_policy(), repo_root=root,
                                           kind="enh", slug="golden-vector", commit=False)
        self.assertEqual(mod.decode_base36(probed), mod.decode_base36(base) + 1)

    def test_in_process_floor_is_scoped_to_the_minting_policy(self) -> None:  # delivery red-team F4
        """A committed v1 mint must not ratchet a subsequent fresh-band v2 mint
        (raw decoded values are not comparable across schemes/offsets)."""
        mod = _load_module()  # fresh module: clean floor state
        ts = datetime(2026, 1, 11, 9, 0, tzinfo=timezone.utc)
        v1 = mod.next_available_prefix(ts, policy=(mod.DEFAULT_EPOCH_UTC, 0),
                                       repo_root=None, commit=True)
        self.assertGreater(mod.decode_base36(v1), 619_520)  # v1 today ≫ the fresh band
        v2 = mod.next_available_prefix(ts, policy=_v2_policy(50_000 + 36 ** 3),
                                       repo_root=None, kind="enh", slug="golden-vector",
                                       commit=True)
        expected_base = mod.build_prefix(ts, policy=_v2_policy(50_000 + 36 ** 3),
                                         kind="enh", slug="golden-vector")
        self.assertEqual(v2, expected_base)  # NOT v1-floor + 1
        # And the floor still works WITHIN one policy: an immediate same-input
        # re-mint advances by exactly one.
        v2_again = mod.next_available_prefix(ts, policy=_v2_policy(50_000 + 36 ** 3),
                                             repo_root=None, kind="enh",
                                             slug="golden-vector", commit=True)
        self.assertEqual(mod.decode_base36(v2_again), mod.decode_base36(v2) + 1)

    def test_mint_policy_comes_from_the_named_repo_root(self) -> None:
        """Policy/dedup coherence: a mint scoped to repo_root=X encodes under
        X's policy, not the ambient CWD-discovered repo's. (Surfaced when the
        self-hosted repo migrated to v2: secrets-test mints with pinned past
        timestamps started reading the host repo's new epoch.)"""
        mod = _load_module()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "workflow-config.json").write_text(json.dumps({
            "lifecycle_id_policy": {"epoch_utc": "2026-01-01T00:00:00Z",
                                    "scheme_version": "v2", "offset": 200_000}
        }), encoding="utf-8")
        ts = datetime(2026, 1, 11, 9, 0, tzinfo=timezone.utc)
        prefix = mod.next_available_prefix(ts, repo_root=root, commit=False,
                                           kind="enh", slug="golden-vector")
        expected = 200_000 + 10 * 4096 + mod._v2_entropy("enh", "golden-vector")
        self.assertEqual(mod.decode_base36(prefix), expected)

    def test_non_dict_policy_block_warns_on_stderr(self) -> None:  # delivery security
        mod = self.mod
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "workflow-config.json").write_text(
            json.dumps({"lifecycle_id_policy": "not-an-object"}), encoding="utf-8",
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            epoch, hour_offset, offset, scheme = mod.load_lifecycle_policy(root)
        self.assertEqual(scheme, "v1")
        self.assertIn("not an object", err.getvalue())


if __name__ == "__main__":
    unittest.main()
