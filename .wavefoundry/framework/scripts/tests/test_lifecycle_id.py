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


if __name__ == "__main__":
    unittest.main()
