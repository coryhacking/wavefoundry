from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Wave 1p457 — fixed reference "now" so confirmation-expiry age math (and the
# false-positive fixtures dated 2026-06-06) is deterministic regardless of the
# real wall clock. Tests needing expiry pass their own future as_of.
_FIXED_AS_OF = datetime(2026, 6, 8, tzinfo=timezone.utc)


TESTS_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TESTS_ROOT.parent
sys.path.insert(0, str(SCRIPTS_ROOT))

from wave_lint_lib import secrets_validators as _sv
from wave_lint_lib.secrets_validators import (
    _hash_context,
    _hash_line,
    _next_secret_finding_id,
    _path_matches_allowlist,
    _SEC_ID_RE,
    check_hardcoded_secrets,
    check_inline_suppression,
    get_scan_files,
    load_exceptions,
    load_merged_ruleset,
    redact,
    scan_file_raw,
)
from wave_lint_lib.constants import (
    SCAN_ALLOWLIST_PATH,
    SCAN_FINDINGS_PATH,
    SCAN_RULES_FRAMEWORK_PATH,
    SCAN_RULES_PROJECT_PATH,
)

try:
    import tomllib
except ImportError:  # Python < 3.11
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Minimal TOML ruleset for tests
# ---------------------------------------------------------------------------

_FRAMEWORK_TOML = """
title = "test config"

[policy]
false_positive_confirmations_required = 2

[[rules]]
id = "test-stripe-key"
description = "Stripe API key"
regex = '''sk_live_[0-9a-zA-Z]{24}'''
keywords = ["sk_live_"]

[[rules]]
id = "test-generic-secret"
description = "Generic secret assignment"
regex = '''(?i)secret\\s*=\\s*["'][A-Za-z0-9+/]{16,}["']'''
"""

_PROJECT_TOML_OVERRIDE = """
[policy]
false_positive_confirmations_required = 1
"""

_PROJECT_TOML_NEW_RULE = """
[[rules]]
id = "project-custom-rule"
description = "Custom project rule"
regex = '''CUSTOM_SECRET_[A-Z0-9]{8}'''
"""

_PROJECT_TOML_DISABLE = """
[policy]
disabled_rules = ["test-stripe-key"]
"""


def _make_root(tmp: Path) -> None:
    """Create minimal project structure in tmp."""
    (tmp / ".wavefoundry").mkdir(parents=True, exist_ok=True)
    (tmp / "docs").mkdir(parents=True, exist_ok=True)


def _write_framework_toml(tmp: Path, content: str = _FRAMEWORK_TOML) -> None:
    path = tmp / SCAN_RULES_FRAMEWORK_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_project_toml(tmp: Path, content: str) -> None:
    path = tmp / SCAN_RULES_PROJECT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_exceptions(tmp: Path, entries: list) -> None:
    path = tmp / SCAN_FINDINGS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


def _run_check(tmp: Path, scan_all: bool = True, as_of=None) -> list[str]:
    with patch("wave_lint_lib.secrets_validators.get_current_git_user_email", return_value="tester@example.com"):
        return check_hardcoded_secrets(
            tmp, scan_all=scan_all, as_of=as_of if as_of is not None else _FIXED_AS_OF
        )


# ---------------------------------------------------------------------------
# redact()
# ---------------------------------------------------------------------------

class TestRedact(unittest.TestCase):
    def test_long_text_partial(self) -> None:
        # 24 chars >= 20 → 4+4 reveal preserved (cap permits).
        self.assertEqual(redact("sk_live_ABCD1234EFGH5678"), "sk_l****5678")

    def test_exactly_8_chars_fully_redacted(self) -> None:
        self.assertEqual(redact("12345678"), "****")

    def test_short_text_fully_redacted(self) -> None:
        self.assertEqual(redact("abc"), "****")

    def test_nine_chars_partial(self) -> None:
        # Wave 1p44x — 9 chars: 40% cap (floor(3.6)=3) allows only a 1+1 window.
        self.assertEqual(redact("123456789"), "1****9")

    # Wave 1p44x — AC-5: exact output across the boundary lengths.
    def test_ten_chars_two_plus_two(self) -> None:
        self.assertEqual(redact("0123456789"), "01****89")  # 4/10 = 40% cap

    def test_sixteen_chars_at_most_two_plus_two(self) -> None:
        self.assertEqual(redact("0123456789ABCDEF"), "01****EF")  # <=16 → <=2+2

    def test_twenty_chars_four_plus_four(self) -> None:
        self.assertEqual(redact("0123456789ABCDEFGHIJ"), "0123****GHIJ")  # >=20 → 4+4

    def test_forty_chars_four_plus_four(self) -> None:
        self.assertEqual(redact("0123456789" * 4), "0123****6789")

    def test_exposure_never_exceeds_forty_percent(self) -> None:
        # Wave 1p44x AC-3 — no input reveals more than ~40% of its characters.
        for n in range(9, 60):
            s = "".join(chr(ord("a") + (i % 26)) for i in range(n))
            out = redact(s)
            revealed = 0 if out == "****" else sum(len(p) for p in out.split("****"))
            self.assertLessEqual(
                revealed, 0.4 * n, f"len={n} revealed {revealed} chars (> 40%)"
            )
            if n <= 16:
                self.assertLessEqual(revealed, 4, f"len={n} (<=16) revealed > 2+2")


# ---------------------------------------------------------------------------
# check_inline_suppression()
# ---------------------------------------------------------------------------

class TestInlineSuppression(unittest.TestCase):
    def test_no_suppression(self) -> None:
        suppressed, err = check_inline_suppression("api_key = 'something'")
        self.assertFalse(suppressed)
        self.assertIsNone(err)

    def test_valid_suppression(self) -> None:
        suppressed, err = check_inline_suppression(
            "api_key = 'val'  # wavefoundry-ignore: secrets test fixture value"
        )
        self.assertTrue(suppressed)
        self.assertIsNone(err)

    def test_bare_suppression_is_error(self) -> None:
        suppressed, err = check_inline_suppression(
            "api_key = 'val'  # wavefoundry-ignore: secrets"
        )
        self.assertTrue(suppressed)
        self.assertIsNotNone(err)
        self.assertIn("bare", err)

    def test_extra_whitespace_bare(self) -> None:
        suppressed, err = check_inline_suppression(
            "x = 1  # wavefoundry-ignore: secrets   "
        )
        self.assertTrue(suppressed)
        self.assertIsNotNone(err)


# ---------------------------------------------------------------------------
# load_merged_ruleset()
# ---------------------------------------------------------------------------

class TestLoadMergedRuleset(unittest.TestCase):
    def test_framework_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _write_framework_toml(tmp)
            rules, policy, errors = load_merged_ruleset(tmp)
            self.assertEqual(errors, [])
            self.assertEqual(len(rules), 2)
            self.assertEqual(policy["false_positive_confirmations_required"], 2)

    def test_project_file_absent_is_not_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _write_framework_toml(tmp)
            rules, policy, errors = load_merged_ruleset(tmp)
            self.assertEqual(errors, [])
            self.assertGreater(len(rules), 0)

    def test_project_policy_overrides_framework(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _write_framework_toml(tmp)
            _write_project_toml(tmp, _PROJECT_TOML_OVERRIDE)
            rules, policy, errors = load_merged_ruleset(tmp)
            self.assertEqual(errors, [])
            self.assertEqual(policy["false_positive_confirmations_required"], 1)

    def test_project_adds_new_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _write_framework_toml(tmp)
            _write_project_toml(tmp, _PROJECT_TOML_NEW_RULE)
            rules, policy, errors = load_merged_ruleset(tmp)
            self.assertEqual(errors, [])
            ids = [r["id"] for r in rules]
            self.assertIn("project-custom-rule", ids)
            self.assertIn("test-stripe-key", ids)

    def test_project_can_disable_framework_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _write_framework_toml(tmp)
            _write_project_toml(tmp, _PROJECT_TOML_DISABLE)
            rules, policy, errors = load_merged_ruleset(tmp)
            self.assertEqual(errors, [])
            ids = [r["id"] for r in rules]
            self.assertNotIn("test-stripe-key", ids)
            self.assertIn("test-generic-secret", ids)

    def test_missing_framework_toml_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            rules, policy, errors = load_merged_ruleset(tmp)
            self.assertEqual(errors, [])
            self.assertEqual(rules, [])


# ---------------------------------------------------------------------------
# check_hardcoded_secrets() — match detection
# ---------------------------------------------------------------------------

class TestMatchDetection(unittest.TestCase):
    def _setup(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        _make_root(tmp)
        _write_framework_toml(tmp)
        return tmp

    def tearDown(self) -> None:
        import shutil
        # cleanup handled per-test via finally blocks or ignored (tempfile GC)

    def test_file_with_matching_pattern_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            target = tmp / "config.py"
            target.write_text('key = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"\n', encoding="utf-8")
            errors = _run_check(tmp)
            self.assertTrue(any("test-stripe-key" in e for e in errors), errors)

    def test_file_without_match_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            target = tmp / "config.py"
            target.write_text('key = os.environ.get("STRIPE_KEY")\n', encoding="utf-8")
            errors = _run_check(tmp)
            self.assertEqual(errors, [])

    def test_record_only_records_but_does_not_fail(self) -> None:
        # 1p5pz: record_only (docs-lint / hook / upgrade gate) — a found secret is
        # recorded to scan-findings.json but NOT returned as a failure; the secrets
        # gate is enforced solely at wave_close. Default mode still returns it.
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            (tmp / "config.py").write_text('key = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"\n', encoding="utf-8")
            with patch("wave_lint_lib.secrets_validators.get_current_git_user_email", return_value="t@x.com"):
                rec = check_hardcoded_secrets(tmp, scan_all=True, record_only=True)
            self.assertEqual(rec, [], "record_only must not return secret findings as failures")
            findings = json.loads((tmp / "docs" / "scan-findings.json").read_text())
            self.assertTrue(any(f.get("status") == "pending" for f in findings),
                            "the finding must still be recorded to scan-findings.json")
            # control: default mode DOES surface it as a failure (so wave_close-era callers see it)
            with patch("wave_lint_lib.secrets_validators.get_current_git_user_email", return_value="t@x.com"):
                default = check_hardcoded_secrets(tmp, scan_all=True)
            self.assertTrue(any("test-stripe-key" in e for e in default), default)

    def test_binary_extension_files_are_skipped(self) -> None:
        # 091yo: a secret-looking string inside a binary-extension file (LanceDB
        # segment, zip, .so) must be skipped by extension BEFORE the per-file sniff,
        # so a repo full of such files doesn't spin. Control: the same content in a
        # .py source file IS flagged.
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            secret = 'key = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"\n'
            for name in ("data.lance", "pack.zip", "lib.so"):
                (tmp / name).write_text(secret, encoding="utf-8")
            self.assertEqual(_run_check(tmp), [], "binary-extension files must be skipped")
            (tmp / "config.py").write_text(secret, encoding="utf-8")
            self.assertTrue(any("test-stripe-key" in e for e in _run_check(tmp)),
                            "a real source file with the same content must still be flagged")

    def test_error_contains_rule_id_and_redacted_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            target = tmp / "app.py"
            target.write_text('key = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"\n', encoding="utf-8")
            errors = _run_check(tmp)
            self.assertTrue(any("test-stripe-key" in e for e in errors))
            self.assertTrue(any("****" in e for e in errors))


# ---------------------------------------------------------------------------
# Auto-append pending entry
# ---------------------------------------------------------------------------

class TestAutoAppend(unittest.TestCase):
    def test_new_match_appends_pending_entry_and_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            target = tmp / "config.py"
            target.write_text('key = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"\n', encoding="utf-8")

            errors = _run_check(tmp)
            self.assertTrue(any("pending" in e for e in errors), errors)

            exceptions = load_exceptions(tmp)
            self.assertEqual(len(exceptions), 1)
            self.assertEqual(exceptions[0]["status"], "pending")
            self.assertEqual(exceptions[0]["rule_id"], "test-stripe-key")

    def test_auto_appended_id_is_unique(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            toml = """
title = "t"
[policy]
false_positive_confirmations_required = 2
[[rules]]
id = "rule-a"
regex = '''SECRET_A_[A-Z]{8}'''
[[rules]]
id = "rule-b"
regex = '''SECRET_B_[A-Z]{8}'''
"""
            _write_framework_toml(tmp, toml)
            target = tmp / "x.py"
            target.write_text(
                'a = "SECRET_A_ABCDEFGH"\nb = "SECRET_B_ABCDEFGH"\n', encoding="utf-8"
            )
            _run_check(tmp)
            exceptions = load_exceptions(tmp)
            ids = [e["id"] for e in exceptions]
            self.assertEqual(len(ids), len(set(ids)), "duplicate exception IDs")


# ---------------------------------------------------------------------------
# Exception status handling
# ---------------------------------------------------------------------------

class TestExceptionStatus(unittest.TestCase):
    _STRIPE_KEY = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"

    def _write_stripe_file(self, tmp: Path) -> None:
        (tmp / "config.py").write_text(f'key = "{self._STRIPE_KEY}"\n', encoding="utf-8")

    def test_pending_entry_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            self._write_stripe_file(tmp)
            _write_exceptions(tmp, [{
                "id": "exc-001", "file": "config.py", "line": 1,
                "rule_id": "test-stripe-key",
                "matched_text": redact(self._STRIPE_KEY),
                "status": "pending", "override_reason": "",
                "acknowledged_for_wave": "", "confirmations": [],
            }])
            errors = _run_check(tmp)
            self.assertTrue(any("pending" in e for e in errors), errors)

    def test_false_positive_threshold_met_suppresses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            self._write_stripe_file(tmp)
            _write_exceptions(tmp, [{
                "id": "exc-001", "file": "config.py", "line": 1,
                "rule_id": "test-stripe-key",
                "matched_text": redact(self._STRIPE_KEY),
                "status": "false-positive", "override_reason": "",
                "acknowledged_for_wave": "",
                "confirmations": [
                    {"git_user_name": "Alice", "git_user_email": "alice@example.com",
                     "verdict": "false-positive", "reason": "test fixture",
                     "confirmed_at": "2026-06-06T10:00:00Z"},
                    {"git_user_name": "Bob", "git_user_email": "bob@example.com",
                     "verdict": "false-positive", "reason": "test fixture",
                     "confirmed_at": "2026-06-06T11:00:00Z"},
                ],
            }])
            errors = _run_check(tmp)
            self.assertEqual(errors, [], errors)

    def test_false_positive_below_threshold_user_not_in_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            self._write_stripe_file(tmp)
            _write_exceptions(tmp, [{
                "id": "exc-001", "file": "config.py", "line": 1,
                "rule_id": "test-stripe-key",
                "matched_text": redact(self._STRIPE_KEY),
                "status": "false-positive", "override_reason": "",
                "acknowledged_for_wave": "",
                "confirmations": [
                    {"git_user_name": "Alice", "git_user_email": "alice@example.com",
                     "verdict": "false-positive", "reason": "test fixture",
                     "confirmed_at": "2026-06-06T10:00:00Z"},
                ],
            }])
            errors = _run_check(tmp)
            # Wave 1p451 — message now names the policy file + key, not "not yet on the list".
            self.assertTrue(any("unconfirmed false positive" in e for e in errors), errors)
            self.assertTrue(any("false_positive_confirmations_required" in e for e in errors), errors)
            self.assertTrue(any("docs/scan-rules.toml" in e for e in errors), errors)

    def test_false_positive_below_threshold_user_already_in_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            self._write_stripe_file(tmp)
            _write_exceptions(tmp, [{
                "id": "exc-001", "file": "config.py", "line": 1,
                "rule_id": "test-stripe-key",
                "matched_text": redact(self._STRIPE_KEY),
                "status": "false-positive", "override_reason": "",
                "acknowledged_for_wave": "",
                "confirmations": [
                    {"git_user_name": "Tester", "git_user_email": "tester@example.com",
                     "verdict": "false-positive", "reason": "test fixture",
                     "confirmed_at": "2026-06-06T10:00:00Z"},
                ],
            }])
            errors = _run_check(tmp)
            # Wave 1p451 — already-confirmed reviewer sees the policy hint + override
            # path, not the impossible "needs N more from a different reviewer".
            self.assertTrue(any("You have already confirmed" in e for e in errors), errors)
            self.assertTrue(any("false_positive_confirmations_required" in e for e in errors), errors)
            self.assertTrue(any("override_reason" in e for e in errors), errors)
            self.assertFalse(any("more from a different reviewer" in e for e in errors), errors)

    def test_suspected_secret_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            self._write_stripe_file(tmp)
            _write_exceptions(tmp, [{
                "id": "exc-001", "file": "config.py", "line": 1,
                "rule_id": "test-stripe-key",
                "matched_text": redact(self._STRIPE_KEY),
                "status": "suspected-secret", "override_reason": "",
                "acknowledged_for_wave": "", "confirmations": [],
            }])
            errors = _run_check(tmp)
            self.assertTrue(any("suspected-secret" in e for e in errors), errors)

    def test_confirmed_secret_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            self._write_stripe_file(tmp)
            _write_exceptions(tmp, [{
                "id": "exc-001", "file": "config.py", "line": 1,
                "rule_id": "test-stripe-key",
                "matched_text": redact(self._STRIPE_KEY),
                "status": "confirmed-secret", "override_reason": "will rotate",
                "acknowledged_for_wave": "", "confirmations": [],
            }])
            errors = _run_check(tmp)
            self.assertTrue(any("confirmed secret" in e for e in errors), errors)


# ---------------------------------------------------------------------------
# Inline suppression in check_hardcoded_secrets
# ---------------------------------------------------------------------------

class TestInlineSuppressionIntegration(unittest.TestCase):
    _STRIPE_KEY = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"

    def test_valid_inline_suppression_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            (tmp / "config.py").write_text(
                f'key = "{self._STRIPE_KEY}"  # wavefoundry-ignore: secrets test fixture\n',
                encoding="utf-8",
            )
            errors = _run_check(tmp)
            self.assertEqual(errors, [], errors)

    def test_bare_inline_suppression_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            (tmp / "config.py").write_text(
                f'key = "{self._STRIPE_KEY}"  # wavefoundry-ignore: secrets\n',
                encoding="utf-8",
            )
            errors = _run_check(tmp)
            self.assertTrue(any("bare" in e for e in errors), errors)


# ---------------------------------------------------------------------------
# Duplicate email deduplication (AC-15)
# ---------------------------------------------------------------------------

class TestDuplicateEmailDedup(unittest.TestCase):
    _STRIPE_KEY = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"

    def test_duplicate_email_counts_as_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            (tmp / "config.py").write_text(f'key = "{self._STRIPE_KEY}"\n', encoding="utf-8")
            _write_exceptions(tmp, [{
                "id": "exc-001", "file": "config.py", "line": 1,
                "rule_id": "test-stripe-key",
                "matched_text": redact(self._STRIPE_KEY),
                "status": "false-positive", "override_reason": "",
                "acknowledged_for_wave": "",
                "confirmations": [
                    {"git_user_name": "Alice", "git_user_email": "alice@example.com",
                     "verdict": "false-positive", "reason": "r1",
                     "confirmed_at": "2026-06-06T10:00:00Z"},
                    {"git_user_name": "Alice Again", "git_user_email": "alice@example.com",
                     "verdict": "false-positive", "reason": "r2",
                     "confirmed_at": "2026-06-06T11:00:00Z"},
                ],
            }])
            # Two entries but same email — count = 1, threshold = 2 → should fail
            errors = _run_check(tmp)
            self.assertTrue(len(errors) > 0, "duplicate email should not satisfy threshold of 2")


# ---------------------------------------------------------------------------
# Scan-rules.toml content (AC-1, AC-11, AC-16)
# ---------------------------------------------------------------------------

class TestGlobalPathAllowlist(unittest.TestCase):
    _STRIPE_KEY = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"
    _TOML_WITH_EXCLUSION = """
title = "t"
[policy]
false_positive_confirmations_required = 2
[[rules]]
id = "test-stripe-key"
description = "Stripe API key"
regex = '''sk_live_[0-9a-zA-Z]{24}'''
keywords = ["sk_live_"]
[allowlist]
paths = ['''(?:^|/)excluded_dir/''']
"""

    def test_file_in_excluded_path_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp, self._TOML_WITH_EXCLUSION)
            excluded = tmp / "excluded_dir" / "secret.py"
            excluded.parent.mkdir(parents=True)
            excluded.write_text(f'key = "{self._STRIPE_KEY}"\n', encoding="utf-8")
            errors = _run_check(tmp)
            self.assertEqual(errors, [], errors)

    def test_file_outside_excluded_path_still_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp, self._TOML_WITH_EXCLUSION)
            excluded = tmp / "excluded_dir" / "secret.py"
            excluded.parent.mkdir(parents=True)
            excluded.write_text(f'key = "{self._STRIPE_KEY}"\n', encoding="utf-8")
            non_excluded = tmp / "config.py"
            non_excluded.write_text(f'key = "{self._STRIPE_KEY}"\n', encoding="utf-8")
            errors = _run_check(tmp)
            self.assertTrue(any("config.py" in e for e in errors), errors)
            self.assertFalse(any("excluded_dir" in e for e in errors), errors)


class TestShippedFrameworkSelfExclusions(unittest.TestCase):
    """The shipped framework ruleset must self-exclude the scanner's own artifacts.

    The findings ledger holds redacted hits plus free-form reviewer prose, both of
    which re-trigger rules on a re-scan (self-match noise). The framework
    [allowlist].paths is wavefoundry-authored — a betterleaks ruleset re-download
    could silently drop it. This guard pins the behavior to the shipped file so
    that regression fails loudly here rather than surfacing as phantom findings.
    """

    def _shipped_allowlist_paths(self) -> list[str]:
        if tomllib is None:
            self.skipTest("tomllib/tomli unavailable")
        repo_root = SCRIPTS_ROOT.parents[2]
        fw_path = repo_root / SCAN_RULES_FRAMEWORK_PATH
        if not fw_path.exists():
            self.skipTest(f"shipped ruleset not present at {fw_path}")
        with open(fw_path, "rb") as f:
            data = tomllib.load(f)
        return list(data.get("allowlist", {}).get("paths", []))

    def test_findings_ledger_excluded_by_default(self) -> None:
        paths = self._shipped_allowlist_paths()
        self.assertTrue(
            _path_matches_allowlist(SCAN_FINDINGS_PATH, paths),
            f"{SCAN_FINDINGS_PATH} must be excluded by the shipped framework allowlist",
        )

    def test_all_scanner_artifacts_excluded_by_default(self) -> None:
        paths = self._shipped_allowlist_paths()
        for rel in (
            SCAN_FINDINGS_PATH,          # docs/scan-findings.json
            SCAN_RULES_PROJECT_PATH,     # docs/scan-rules.toml
            SCAN_RULES_FRAMEWORK_PATH,   # .wavefoundry/framework/scan-rules.toml
            SCAN_ALLOWLIST_PATH,         # .wavefoundry/framework/scan-allowlist
        ):
            self.assertTrue(
                _path_matches_allowlist(rel, paths),
                f"scanner artifact {rel} is not self-excluded by the shipped ruleset",
            )

    def test_generated_artifacts_excluded_by_default(self) -> None:
        """Wave 1p44t — generic minified/source-map/snapshot/compiled-binary rules."""
        paths = self._shipped_allowlist_paths()
        for rel in (
            "app.min.js",
            "vendor/foo.min.css",
            "dist/bundle.min.js.map",
            "src/index.js.map",
            "styles.css.map",
            "lib/util.mjs.map",
            "lib/util.cjs.map",
            "__snapshots__/Component.test.js.snap",
            "lib/native.wasm",
            "build/addon.node",
            "obj/main.o",
            "libfoo.so",
            "Foo.class",
        ):
            self.assertTrue(
                _path_matches_allowlist(rel, paths),
                f"generated artifact {rel} must be excluded by the shipped allowlist",
            )

    def test_normal_source_not_excluded(self) -> None:
        """Wave 1p44t — the generic rules must not over-match real source files."""
        paths = self._shipped_allowlist_paths()
        for rel in ("config.js", "src/app.ts", "main.css", "index.mjs"):
            self.assertFalse(
                _path_matches_allowlist(rel, paths),
                f"normal source file {rel} must NOT be allowlisted",
            )


class TestScanFileRawGuards(unittest.TestCase):
    """Wave 1p44s — scan_file_raw input guards (size/binary/line) + skip surfacing.

    Guards keep the existing ([], None, []) skip shape so phase-2 short-circuits
    without a stale-exception sweep (AC-5); size/binary skips are surfaced (AC-9).
    """

    _SECRET = "sk_live_ABCDEFGHIJKLMNOP"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # One stripe-like rule with a capture group; no keywords/allowlists/CEL.
        self._rules = [("stripe", [], re.compile(r"(sk_live_[A-Za-z0-9]{16,})"), [], [], "")]
        _sv._SCANNER_SKIPS.clear()

    def tearDown(self) -> None:
        _sv._SCANNER_SKIPS.clear()
        self.tmp.cleanup()

    def _scan(self, name, *, text=None, raw=None, rules=None):
        p = self.root / name
        if raw is not None:
            p.write_bytes(raw)
        else:
            p.write_text(text, encoding="utf-8")
        return scan_file_raw(p, name, rules or self._rules, [], set())

    # AC-7: in-bounds files scan exactly as before — no detection regression.
    def test_normal_file_with_secret_still_detected(self):
        lines, sha, hits = self._scan("config.py", text=f'key = "{self._SECRET}"\n')
        self.assertEqual(len(hits), 1)
        self.assertEqual(_sv._SCANNER_SKIPS, [])

    def test_clean_file_no_hits_no_skip(self):
        lines, sha, hits = self._scan("clean.py", text="x = 1\n")
        self.assertEqual(hits, [])
        self.assertEqual(_sv._SCANNER_SKIPS, [])

    # AC-2: per-file size cap.
    def test_oversized_file_skipped(self):
        with patch.object(_sv, "MAX_FILE_BYTES", 64):
            lines, sha, hits = self._scan("big.py", text=f'k="{self._SECRET}"\n' * 20)
        self.assertEqual((lines, sha, hits), ([], None, []))
        self.assertTrue(any(s["reason"] == "file too large" for s in _sv._SCANNER_SKIPS))

    # AC-3: NUL-byte binary detection.
    def test_binary_file_skipped_and_secret_not_reported(self):
        # Non-binary extension (.txt) so the NUL-byte content sniff path is exercised
        # rather than the 1p5qp extension fast-skip (which preempts .dat/.bin/etc.).
        blob = b"\x00\x01" + f'key="{self._SECRET}"'.encode() + b"\x00" * 8
        lines, sha, hits = self._scan("blob.txt", raw=blob)
        self.assertEqual((lines, sha, hits), ([], None, []))
        self.assertTrue(any(s["reason"] == "binary file" for s in _sv._SCANNER_SKIPS))

    # AC-1: max-line-length guard — over-long line skipped before the rule regex.
    def test_giant_line_skipped(self):
        with patch.object(_sv, "MAX_LINE_BYTES", 32):
            lines, sha, hits = self._scan("bundle.min.js", text="x" * 200 + self._SECRET + "\n")
        self.assertEqual(hits, [])           # over-long line never reached the regex
        self.assertNotEqual(lines, [])        # but the file itself was read (under size cap)

    # AC-6 (deterministic perf-leverage proxy, no wall-clock flakiness): prove the
    # over-long line never reaches pattern.search — that is the cost the guard removes.
    def test_giant_line_does_not_invoke_regex(self):
        sentinel = MagicMock()
        sentinel.search.side_effect = AssertionError("regex must not run on over-long line")
        rules = [("r", [], sentinel, [], [], "")]
        with patch.object(_sv, "MAX_LINE_BYTES", 32):
            lines, sha, hits = self._scan("min.css", text="y" * 200 + "\n", rules=rules)
        self.assertEqual(hits, [])
        sentinel.search.assert_not_called()

    # AC-5: a skipped file returns the empty shape phase-2 short-circuits on.
    def test_skipped_file_short_circuit_shape(self):
        lines, sha, hits = self._scan("x.bin", raw=b"\x00data")
        self.assertTrue(not lines and not hits)  # `if not lines and not hits: continue`

    # AC-9: the skip is surfaced (never silent) — stderr trace + in-process record.
    def test_skip_surfaced_to_stderr(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf), patch.object(_sv, "MAX_FILE_BYTES", 16):
            self._scan("huge.py", text="a = 1\n" * 50)
        out = buf.getvalue()
        self.assertIn("SKIPPED", out)
        self.assertIn("huge.py", out)

    def test_stat_race_on_vanished_file_is_clean_skip(self):
        # File never created: stat() raises → clean skip, no crash, no false record.
        ghost = self.root / "ghost.py"
        lines, sha, hits = scan_file_raw(ghost, "ghost.py", self._rules, [], set())
        self.assertEqual((lines, sha, hits), ([], None, []))
        self.assertEqual(_sv._SCANNER_SKIPS, [])  # a race is not an auditable skip


class TestFindingDedupAndComment(unittest.TestCase):
    """Wave 1p44v — one secret → one finding; in_comment triage flag (no suppress)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _scan(self, name, text, rules):
        p = self.root / name
        p.write_text(text, encoding="utf-8")
        return scan_file_raw(p, name, rules, [], set())

    def test_two_rules_same_secret_one_finding(self):
        # AC-1: two rules match the same secret (overlapping spans) → one finding.
        rules = [
            ("rule-a", [], re.compile(r"(sk_live_[A-Za-z0-9]+)"), [], [], ""),
            ("rule-b", [], re.compile(r'key\s*=\s*"(sk_live_[A-Za-z0-9]+)"'), [], [], ""),
        ]
        _, _, hits = self._scan("config.py", 'key = "sk_live_ABCDEFGHIJKLMNOP"\n', rules)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["rule_id"], "rule-a")  # first rule in order wins

    def test_distinct_secrets_same_redaction_not_merged(self):
        # AC-2: two distinct 8-char secrets both redact to "****" but live at
        # different spans → two findings (dedup is span-based, not redacted_match).
        rules = [
            ("rule-x", [], re.compile(r"(A{8})"), [], [], ""),
            ("rule-y", [], re.compile(r"(B{8})"), [], [], ""),
        ]
        _, _, hits = self._scan("c.py", "AAAAAAAA BBBBBBBB\n", rules)
        self.assertEqual(len(hits), 2)
        self.assertTrue(all(h["redacted_match"] == "****" for h in hits))

    def test_comment_secret_flagged_not_suppressed(self):
        # AC-3 / AC-4: a commented secret still produces a finding, with in_comment.
        rules = [("stripe", [], re.compile(r"(sk_live_[A-Za-z0-9]+)"), [], [], "")]
        _, _, hits = self._scan("config.py", '# key = "sk_live_ABCDEFGHIJKLMNOP"\n', rules)
        self.assertEqual(len(hits), 1)
        self.assertTrue(hits[0]["in_comment"])

    def test_non_comment_line_in_comment_false(self):
        rules = [("stripe", [], re.compile(r"(sk_live_[A-Za-z0-9]+)"), [], [], "")]
        _, _, hits = self._scan("config.py", 'key = "sk_live_ABCDEFGHIJKLMNOP"\n', rules)
        self.assertEqual(len(hits), 1)
        self.assertFalse(hits[0]["in_comment"])

    def test_unknown_extension_defaults_not_comment(self):
        rules = [("stripe", [], re.compile(r"(sk_live_[A-Za-z0-9]+)"), [], [], "")]
        _, _, hits = self._scan("data.unknownext", '# sk_live_ABCDEFGHIJKLMNOP\n', rules)
        self.assertEqual(len(hits), 1)
        self.assertFalse(hits[0]["in_comment"])  # unknown ext → not flagged

    def test_dedup_is_deterministic_across_runs(self):
        # AC-6: repeated scans of an unchanged file produce identical findings.
        rules = [
            ("rule-a", [], re.compile(r"(sk_live_[A-Za-z0-9]+)"), [], [], ""),
            ("rule-b", [], re.compile(r'key\s*=\s*"(sk_live_[A-Za-z0-9]+)"'), [], [], ""),
        ]
        text = 'key = "sk_live_ABCDEFGHIJKLMNOP"\n'
        _, _, hits1 = self._scan("config.py", text, rules)
        _, _, hits2 = self._scan("config.py", text, rules)
        self.assertEqual(hits1, hits2)

    def test_exception_entry_carries_in_comment(self):
        # AC-3: the in_comment flag propagates into the created exception entry.
        line = '# key = "sk_live_ABCDEFGHIJKLMNOP"'
        lines = [line]
        hit = {
            "rule_id": "r", "line_no": 1, "matched_text": "sk_live_ABCDEFGHIJKLMNOP",
            "redacted_match": "****", "redacted_line": "# key = ****",
            "line_hash": _hash_line(line), "context_hash": _hash_context(lines, 1),
            "in_comment": True, "suppress_error": None,
        }
        exceptions: list = []
        _sv._match_hits_for_file(
            "config.py", lines, None, [hit], exceptions, set(), 2,
            "tester@example.com",
        )
        self.assertEqual(len(exceptions), 1)
        self.assertTrue(exceptions[0]["in_comment"])


class TestGenericApiKeyDocsScope(unittest.TestCase):
    """Wave 1p44u — generic-api-key suppresses moderate-entropy docs/.md prose
    while preserving recall on genuine high-entropy keys (path-scoped, not blanket)."""

    # `a3f9c2b8d1e07645` (entropy ~4.0) slips the rule's GLOBAL entropy(<=3.5)/
    # token-efficiency/stopword bars, so it fires in code — but the new docs clause
    # (entropy <= 4.2 on a .md/docs path) suppresses it in documentation.
    # A genuinely prose-shaped docs line (>=5 word tokens) carrying a
    # moderate-entropy (~3.75) token — the FP class the docs clause targets.
    _PROSE = "The service api key: c1d2e3f4a5b6c7d8 is referenced throughout these design notes.\n"
    _REAL = 'api_key: sk_live_4eC39HqLyjWDarjtT1zdp7dcKQ8xZ2mn\n'  # entropy ~5.1
    # A BARE moderate-entropy key assignment (NOT prose) — a real leak vector that
    # must still fire even in docs (delivery-review recall fix, wave 1p44n).
    _BARE_KEY = 'api_key: 5f4dcc3b5aa765d61d8327deb882cf99\n'  # 32-char hex, entropy ~3.8

    @classmethod
    def setUpClass(cls):
        if tomllib is None:
            raise unittest.SkipTest("tomllib/tomli unavailable")
        fw = SCRIPTS_ROOT.parents[2] / SCAN_RULES_FRAMEWORK_PATH
        if not fw.exists():
            raise unittest.SkipTest(f"shipped ruleset absent at {fw}")
        cls._fw_path = fw
        with open(fw, "rb") as f:
            data = tomllib.load(f)
        rule = next(r for r in data["rules"] if r["id"] == "generic-api-key")
        al_paths: list = []
        al_regexes: list = []
        for al in rule.get("allowlists", []):
            al_paths.extend(al.get("paths", []))
            al_regexes.extend(al.get("regexes", []))
        cls._compiled = [(
            rule["id"], [kw.lower() for kw in rule.get("keywords", [])],
            re.compile(rule["regex"]), al_paths, al_regexes, rule.get("filter", ""),
        )]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _hits(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        _, _, hits = scan_file_raw(p, rel, self._compiled, [], set())
        return hits

    def test_docs_prose_suppressed(self):  # AC-1
        self.assertEqual(self._hits("docs/architecture.md", self._PROSE), [])

    def test_same_prose_still_fires_in_code(self):  # AC-1 control — path-scoped, not blanket
        self.assertEqual(len(self._hits("src/config.py", self._PROSE)), 1)

    def test_real_high_entropy_key_in_markdown_still_fires(self):  # AC-2 recall
        self.assertEqual(len(self._hits("docs/setup.md", self._REAL)), 1)

    def test_bare_moderate_entropy_key_assignment_in_docs_still_fires(self):  # recall (delivery review)
        # A bare `api_key: <32-hex>` line is NOT prose-shaped, so the docs clause
        # must NOT suppress it even though its entropy is <= 4.2.
        self.assertEqual(len(self._hits("docs/runbook.md", self._BARE_KEY)), 1)

    def test_integration_through_full_ruleset_pipeline(self):  # AC-5 / AC-6
        # Drive the same check_hardcoded_secrets path the wave_scan_secrets MCP
        # wrapper invokes, against the REAL shipped ruleset.
        _make_root(self.root)
        (self.root / SCAN_RULES_FRAMEWORK_PATH).parent.mkdir(parents=True, exist_ok=True)
        (self.root / SCAN_RULES_FRAMEWORK_PATH).write_bytes(self._fw_path.read_bytes())
        (self.root / "docs").mkdir(exist_ok=True)
        (self.root / "docs" / "architecture.md").write_text(self._PROSE, encoding="utf-8")
        (self.root / "docs" / "setup.md").write_text(self._REAL, encoding="utf-8")
        failures = _run_check(self.root, scan_all=True)
        joined = "\n".join(failures)
        self.assertNotIn("architecture.md", joined)  # prose suppressed
        self.assertIn("setup.md", joined)             # real key still flagged


class TestJwtExpiry(unittest.TestCase):
    """Wave 1p44w — JWT expiry: fail-safe decode builtin, exp_date surfacing,
    policy-gated suppression (default still surfaces an expired token)."""

    @classmethod
    def setUpClass(cls):
        if tomllib is None:
            raise unittest.SkipTest("tomllib/tomli unavailable")
        cls._fw_path = SCRIPTS_ROOT.parents[2] / SCAN_RULES_FRAMEWORK_PATH
        if not cls._fw_path.exists():
            raise unittest.SkipTest("shipped ruleset absent")
        with open(cls._fw_path, "rb") as f:
            data = tomllib.load(f)
        rule = next(r for r in data["rules"] if r["id"] == "jwt")
        cls._compiled = [(
            rule["id"], [kw.lower() for kw in rule.get("keywords", [])],
            re.compile(rule["regex"]), [], [], rule.get("filter", ""),
        )]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _jwt(exp):
        import base64 as _b64
        h = _b64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
        p = _b64.urlsafe_b64encode(json.dumps({"exp": exp, "sub": "abc"}).encode()).rstrip(b"=").decode()
        return f"{h}.{p}.c2lnbmF0dXJlMTIzNDU2"

    def _scan(self, token, policy=None):
        p = self.root / "config.py"
        p.write_text(f'data = "{token}"\n', encoding="utf-8")
        _, _, hits = scan_file_raw(p, "config.py", self._compiled, [], set(), policy)
        return hits

    def test_builtin_expired_valid_malformed(self):  # AC-1 / AC-5
        from wave_lint_lib.cel_filter import _jwt_exp_claim, _jwt_expired
        self.assertTrue(_jwt_expired(self._jwt(1000000000)))                 # 2001 — expired
        self.assertFalse(_jwt_expired(self._jwt(int(time.time()) + 99999)))  # future
        for bad in ["", "ey.ey", "not.a.jwt", "a.b.c", self._jwt("not-a-number")]:
            self.assertFalse(_jwt_expired(bad))      # fail-safe → not expired, never raises
            self.assertIsNone(_jwt_exp_claim(bad))

    def test_exp_date_surfaced_on_finding(self):  # AC-3
        hits = self._scan(self._jwt(1000000000))
        self.assertEqual(len(hits), 1)
        self.assertIn("EXPIRED", hits[0].get("exp_date", ""))

    def test_expired_surfaces_by_default(self):  # AC-4
        self.assertEqual(len(self._scan(self._jwt(1000000000))), 1)

    def test_expired_suppressed_only_with_policy_optin(self):  # AC-2 / AC-4
        self.assertEqual(self._scan(self._jwt(1000000000),
                                    policy={"suppress_expired_jwts": True}), [])

    def test_valid_jwt_never_suppressed_by_expiry(self):  # AC-4 recall
        hits = self._scan(self._jwt(int(time.time()) + 99999),
                          policy={"suppress_expired_jwts": True})
        self.assertEqual(len(hits), 1)

    def test_integration_exp_date_persisted_in_findings(self):  # AC-3 / AC-7
        _make_root(self.root)
        (self.root / SCAN_RULES_FRAMEWORK_PATH).parent.mkdir(parents=True, exist_ok=True)
        (self.root / SCAN_RULES_FRAMEWORK_PATH).write_bytes(self._fw_path.read_bytes())
        (self.root / "app.py").write_text(f'data = "{self._jwt(1000000000)}"\n', encoding="utf-8")
        _run_check(self.root, scan_all=True)
        jwt_entries = [e for e in load_exceptions(self.root) if e.get("rule_id") == "jwt"]
        self.assertTrue(jwt_entries, "expired JWT should still surface as a finding")
        self.assertIn("EXPIRED", jwt_entries[0].get("exp_date", ""))


class TestGlobalValueFilter(unittest.TestCase):
    """Wave 1p456 — the global [allowlist] regexes/stopwords value-filter is loaded
    and applied to every rule's match values (was authored but inert)."""

    _FW_WITH_FILTER = '''
[[rules]]
id = "test-any"
description = "match any quoted value"
regex = \'\'\'val\\s*=\\s*"([^"]+)"\'\'\'

[policy]
false_positive_confirmations_required = 1

[allowlist]
paths = []
regexes = [
    \'\'\'^\\$(?:[A-Z_]+|[a-z_]+)$\'\'\',
    \'\'\'(?i)^true|false|null$\'\'\',
]
stopwords = ["NOISESTOPWORD"]
'''

    _FW_NO_FILTER = '''
[[rules]]
id = "test-any"
description = "match any quoted value"
regex = \'\'\'val\\s*=\\s*"([^"]+)"\'\'\'

[policy]
false_positive_confirmations_required = 1

[allowlist]
paths = []
'''

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._rule = [("any", [], re.compile(r'val\s*=\s*"([^"]+)"'), [], [], "")]

    def tearDown(self):
        self.tmp.cleanup()

    @classmethod
    def _shipped_filter(cls):
        if tomllib is None:
            raise unittest.SkipTest("tomllib unavailable")
        fw = SCRIPTS_ROOT.parents[2] / SCAN_RULES_FRAMEWORK_PATH
        if not fw.exists():
            raise unittest.SkipTest("ruleset absent")
        with open(fw, "rb") as f:
            allow = tomllib.load(f).get("allowlist", {})
        return list(allow.get("regexes", [])), list(allow.get("stopwords", []))

    def _direct_hits(self, value, regexes, stopwords):
        p = self.root / "f.py"
        p.write_text(f'val = "{value}"\n', encoding="utf-8")
        _, _, hits = scan_file_raw(
            p, "f.py", self._rule, [], set(), None, regexes, stopwords
        )
        return hits

    def test_each_noise_class_suppressed(self):  # AC-1 / AC-3 (shipped patterns)
        rx, sw = self._shipped_filter()
        for noise in (
            "$VAR", "${VAR}", "${HOME}", "{{ value }}", "%FMT%", "%s",
            "true", "false", "null", "/Users/alice/project/config", "/bin/bash",
        ):
            self.assertEqual(self._direct_hits(noise, rx, sw), [],
                             f"{noise!r} must be suppressed by the global value-filter")

    def test_high_entropy_secret_still_fires(self):  # AC-4 recall
        rx, sw = self._shipped_filter()
        self.assertEqual(len(self._direct_hits("xQ7mK9pL2wR8tY4zB1nC6vD3", rx, sw)), 1)

    def test_secret_containing_noise_substring_still_fires(self):  # recall (delivery review)
        # The value-filter matches the WHOLE value (re.fullmatch), so a real
        # high-entropy secret that merely CONTAINS "false"/"null" is NOT dropped.
        rx, sw = self._shipped_filter()
        for val in ("Xy7falseKp2Lm9Qr4Ns6Tv8Wb3Zc5", "Kp2Lm9Qr4Ns6Tv8Wb3Zc5Xy7null"):
            self.assertEqual(len(self._direct_hits(val, rx, sw)), 1,
                             f"{val!r} contains noise text but is a real secret — must fire")

    def test_stopword_substring_suppressed(self):  # AC-5
        rx, sw = self._shipped_filter()
        self.assertEqual(self._direct_hits("zz-abcdefghijklmnopqrstuvwxyz-zz", rx, sw), [])

    def test_without_filter_noise_fires(self):  # control — proves the filter is load-bearing
        p = self.root / "f.py"
        p.write_text('val = "$VAR"\n', encoding="utf-8")
        _, _, hits = scan_file_raw(p, "f.py", self._rule, [], set())
        self.assertEqual(len(hits), 1)

    def test_framework_filter_loaded_and_applied(self):  # AC-1 (full pipeline)
        _make_root(self.root)
        _write_framework_toml(self.root, self._FW_WITH_FILTER)
        (self.root / "code.py").write_text(
            'val = "$VAR"\nval = "true"\nval = "realsecret9KqXm"\n', encoding="utf-8"
        )
        failures = _run_check(self.root, scan_all=True)
        joined = "\n".join(failures)
        self.assertNotIn(':1:', joined)   # $VAR suppressed
        self.assertNotIn(':2:', joined)   # true suppressed
        self.assertIn(':3:', joined)      # real value still flagged

    def test_project_file_value_filter_merged(self):  # AC-2
        _make_root(self.root)
        _write_framework_toml(self.root, self._FW_NO_FILTER)
        _write_project_toml(self.root, "[allowlist]\nregexes = ['''^PROJECTNOISE$''']\n")
        (self.root / "code.py").write_text(
            'val = "PROJECTNOISE"\nval = "realsecret9KqXm"\n', encoding="utf-8"
        )
        failures = _run_check(self.root, scan_all=True)
        joined = "\n".join(failures)
        self.assertNotIn(':1:', joined)   # project regex suppressed it
        self.assertIn(':2:', joined)      # real value still flagged

    def test_parallel_path_applies_value_filter(self):  # AC-6
        _make_root(self.root)
        _write_framework_toml(self.root, self._FW_WITH_FILTER)
        # >= _PARALLEL_SCAN_THRESHOLD (50) files so the ProcessPoolExecutor path engages.
        for i in range(60):
            (self.root / f"f{i}.py").write_text('val = "$VAR"\n', encoding="utf-8")
        # Non-tautological guard (delivery review): if the parallel branch silently
        # falls back to serial, the PARENT process's scan_file_raw runs — spawned
        # workers re-import the module and use the real function, so this sentinel
        # fires ONLY on a fallback, making the test fail instead of passing blind.
        sentinel = patch(
            "wave_lint_lib.secrets_validators.scan_file_raw",
            side_effect=AssertionError("serial fallback used — parallel path did not run"),
        )
        with patch("wave_lint_lib.secrets_validators.get_current_git_user_email",
                   return_value="tester@example.com"), sentinel:
            failures = check_hardcoded_secrets(self.root, scan_all=True, max_workers=4)
        self.assertEqual(failures, [], "parallel workers must apply the global value-filter")

    def test_parallel_path_skips_oversized_file_in_worker(self):  # delivery review (AC-9 parallel)
        # The size guard must run inside the spawned workers: an oversized
        # secret-bearing file is skipped there (no finding), not just serially.
        _make_root(self.root)
        _write_framework_toml(self.root, self._FW_WITH_FILTER)
        for i in range(60):
            (self.root / f"f{i}.py").write_text('x = 1\n', encoding="utf-8")
        # A real >5MB (MAX_FILE_BYTES) file — workers re-import the module, so the
        # constant cannot be patched for them; use a genuinely oversized fixture.
        big = (self.root / "big.py")
        big.write_text('val = "realsecret9KqXm"\n' + ("# pad\n" * 900_000), encoding="utf-8")
        self.assertGreater(big.stat().st_size, 5 * 1024 * 1024)
        with patch("wave_lint_lib.secrets_validators.get_current_git_user_email",
                   return_value="tester@example.com"):
            failures = check_hardcoded_secrets(self.root, scan_all=True, max_workers=4)
        # The oversized file's value is skipped by the worker's size guard → no finding.
        self.assertEqual(
            [f for f in failures if "big.py" in f], [],
            "oversized file must be skipped by the size guard on the parallel path",
        )


class TestFalsePositiveOverrideAndClamp(unittest.TestCase):
    """Wave 1p44y — override_reason dismissal + reviewer-count clamp on the
    false-positive secrets-gate branch (deadlock escape for a lone maintainer)."""

    _STRIPE_KEY = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_root(self.root)
        _write_framework_toml(self.root)
        (self.root / "config.py").write_text(
            f'key = "{self._STRIPE_KEY}"\n', encoding="utf-8"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _init_git(self, emails):
        import subprocess as _sp
        _sp.run(["git", "init", "-q"], cwd=self.root, check=True)
        for i, email in enumerate(emails):
            (self.root / f"c{i}.txt").write_text(str(i), encoding="utf-8")
            _sp.run(["git", "add", "."], cwd=self.root, check=True)
            _sp.run(
                ["git", "-c", f"user.email={email}", "-c", f"user.name=Author{i}",
                 "-c", "commit.gpgsign=false", "commit", "-q", "-m", f"c{i}"],
                cwd=self.root, check=True,
            )

    def _fp_entry(self, *, override_reason="", confirmations=None):
        return {
            "id": "exc-001", "file": "config.py", "line": 1,
            "rule_id": "test-stripe-key", "matched_text": redact(self._STRIPE_KEY),
            "status": "false-positive", "override_reason": override_reason,
            "acknowledged_for_wave": "", "confirmations": confirmations or [],
        }

    @staticmethod
    def _conf(email, name="Reviewer"):
        return {"git_user_name": name, "git_user_email": email,
                "verdict": "false-positive", "reason": "fixture",
                "confirmed_at": "2026-06-06T10:00:00Z"}

    def test_override_reason_dismisses_without_confirmations(self):  # AC-1
        _write_exceptions(self.root, [
            self._fp_entry(override_reason="operator dismissed: known test fixture key"),
        ])
        self.assertEqual(_run_check(self.root), [])

    def test_clamp_single_reviewer_one_confirmation_passes(self):  # AC-2
        self._init_git(["alice@example.com"])
        _write_exceptions(self.root, [
            self._fp_entry(confirmations=[self._conf("alice@example.com", "Alice")]),
        ])
        self.assertEqual(_run_check(self.root), [])  # clamp 2→1; one confirmation suffices

    def test_clamp_preserved_when_two_reviewers(self):  # AC-3
        self._init_git(["alice@example.com", "bob@example.com"])
        _write_exceptions(self.root, [
            self._fp_entry(confirmations=[self._conf("alice@example.com", "Alice")]),
        ])
        self.assertTrue(any("test-stripe-key" in e for e in _run_check(self.root)),
                        "two confirmable reviewers must keep the threshold at 2")

    def test_bot_emails_excluded_from_clamp(self):  # AC-4
        self._init_git([
            "alice@example.com",
            "49699333+dependabot[bot]@users.noreply.github.com",
        ])
        _write_exceptions(self.root, [
            self._fp_entry(confirmations=[self._conf("alice@example.com", "Alice")]),
        ])
        self.assertEqual(_run_check(self.root), [])  # bot excluded → confirmable=1 → clamp to 1

    def test_no_override_unmet_count_still_fails(self):  # AC-5
        self._init_git(["alice@example.com", "bob@example.com"])
        _write_exceptions(self.root, [self._fp_entry()])  # no override, 0 confirmations
        errors = _run_check(self.root)
        self.assertTrue(any("test-stripe-key" in e for e in errors),
                        "gate must still fail actionably, not be silently disabled")


class TestConfirmationExpiry(unittest.TestCase):
    """Wave 1p457 — false-positive confirmations expire after confirmation_valid_days
    (per-confirmation clock), with a fixed injected as_of (no wall-clock reliance)."""

    _STRIPE_KEY = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"
    _NOW = datetime(2028, 6, 8, tzinfo=timezone.utc)  # 2 years after the 2026-06-06 fixtures

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_root(self.root)
        _write_framework_toml(self.root)
        (self.root / "config.py").write_text(
            f'key = "{self._STRIPE_KEY}"\n', encoding="utf-8"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _conf(self, email, when, name="Reviewer"):
        return {"git_user_name": name, "git_user_email": email,
                "verdict": "false-positive", "reason": "fixture", "confirmed_at": when}

    def _entry(self, confirmations):
        return {"id": "exc-001", "file": "config.py", "line": 1,
                "rule_id": "test-stripe-key", "matched_text": redact(self._STRIPE_KEY),
                "status": "false-positive", "override_reason": "",
                "acknowledged_for_wave": "", "confirmations": confirmations}

    def test_all_expired_not_suppressed(self):  # AC-1
        _write_exceptions(self.root, [self._entry([
            self._conf("a@x.com", "2026-06-06T10:00:00Z", "Alice"),
            self._conf("b@x.com", "2026-06-06T11:00:00Z", "Bob"),
        ])])
        self.assertTrue(any("test-stripe-key" in e for e in _run_check(self.root, as_of=self._NOW)))

    def test_mixed_fresh_and_expired_counts_fresh_only(self):  # AC-2
        _write_exceptions(self.root, [self._entry([
            self._conf("a@x.com", "2026-06-06T10:00:00Z", "Alice"),  # expired
            self._conf("b@x.com", "2028-06-07T11:00:00Z", "Bob"),    # fresh
        ])])
        errors = _run_check(self.root, as_of=self._NOW)
        self.assertTrue(any("1 of 2" in e for e in errors), errors)

    def test_two_fresh_confirmations_suppress(self):  # AC-2 (at/above threshold)
        _write_exceptions(self.root, [self._entry([
            self._conf("a@x.com", "2028-06-06T10:00:00Z", "Alice"),
            self._conf("b@x.com", "2028-06-07T11:00:00Z", "Bob"),
        ])])
        self.assertEqual(_run_check(self.root, as_of=self._NOW), [])

    def test_unparseable_confirmed_at_not_counted(self):  # AC-3
        _write_exceptions(self.root, [self._entry([
            self._conf("a@x.com", "", "Alice"),
            self._conf("b@x.com", "not-a-date", "Bob"),
        ])])
        self.assertTrue(any("0 of 2" in e for e in _run_check(self.root, as_of=self._NOW)))

    def test_expired_confirmations_left_in_place(self):  # AC-4
        _write_exceptions(self.root, [self._entry([
            self._conf("a@x.com", "2026-06-06T10:00:00Z", "Alice"),
        ])])
        _run_check(self.root, as_of=self._NOW)
        saved = load_exceptions(self.root)
        self.assertEqual(len(saved[0]["confirmations"]), 1)  # not mutated/pruned

    def test_expiry_message_is_distinct(self):  # AC-6
        _write_exceptions(self.root, [self._entry([
            self._conf("a@x.com", "2026-06-06T10:00:00Z", "Alice"),
        ])])
        self.assertTrue(any("EXPIRED" in e for e in _run_check(self.root, as_of=self._NOW)))

    def test_zero_days_disables_expiry(self):  # AC-5
        _write_project_toml(self.root, "[policy]\nconfirmation_valid_days = 0\n")
        _write_exceptions(self.root, [self._entry([
            self._conf("a@x.com", "2026-06-06T10:00:00Z", "Alice"),
            self._conf("b@x.com", "2026-06-06T11:00:00Z", "Bob"),
        ])])  # very old, but expiry disabled → both count → suppressed
        self.assertEqual(_run_check(self.root, as_of=self._NOW), [])

    def test_project_override_window(self):  # AC-5
        _write_project_toml(self.root, "[policy]\nconfirmation_valid_days = 30\n")
        _write_exceptions(self.root, [self._entry([
            self._conf("a@x.com", "2026-06-06T10:00:00Z", "Alice"),
            self._conf("b@x.com", "2026-06-06T11:00:00Z", "Bob"),
        ])])
        # 2 days later → within the 30-day window → suppressed.
        self.assertEqual(_run_check(self.root, as_of=_FIXED_AS_OF), [])
        # ~56 days later → beyond the 30-day window → fails.
        late = datetime(2026, 8, 1, tzinfo=timezone.utc)
        self.assertTrue(any("test-stripe-key" in e for e in _run_check(self.root, as_of=late)))

    def test_unique_confirmation_count_arity_preserved(self):  # AC-7
        from wave_lint_lib.secrets_validators import _unique_confirmation_count
        result = _unique_confirmation_count(self._entry([self._conf("a@x.com", "2026-06-06T10:00:00Z")]))
        self.assertEqual(len(result), 2)  # (count, names)
        self.assertIsInstance(result[0], int)
        self.assertIsInstance(result[1], list)


class TestSuppressedPendingReconciliation(unittest.TestCase):
    """Wave 1p4a2 — a FULL scan drops `pending` entries whose line still exists but
    which the current ruleset no longer produces as a hit (now suppressed). Strictly
    pending-only and full-scan-only; classifications and untouched files are safe."""

    LINE = 'x = "plain text here"'  # matches none of the test rules → no hit

    def _pending(self, **over):
        e = {"id": "exc-001", "file": "benign.py", "line": 1,
             "line_hash": _hash_line(self.LINE), "context_hash": "ctx",
             "rule_id": "test-stripe-key", "matched_text": "x = ****",
             "status": "pending", "confirmations": []}
        e.update(over)
        return e

    # --- unit: _sweep_suppressed_pending ---
    def test_sweep_removes_pending_phantom(self):  # AC-1
        from wave_lint_lib.secrets_validators import _sweep_suppressed_pending
        exc = [self._pending()]
        self.assertTrue(_sweep_suppressed_pending(exc, "benign.py", set()))
        self.assertEqual(exc, [])

    def test_sweep_keeps_still_produced(self):  # AC-3
        from wave_lint_lib.secrets_validators import _sweep_suppressed_pending
        exc = [self._pending()]
        self.assertFalse(_sweep_suppressed_pending(exc, "benign.py", {"exc-001"}))
        self.assertEqual(len(exc), 1)

    def test_sweep_keeps_classified(self):  # AC-2
        from wave_lint_lib.secrets_validators import _sweep_suppressed_pending
        for status in ("false-positive", "suspected-secret", "confirmed-secret"):
            exc = [self._pending(status=status)]
            self.assertFalse(_sweep_suppressed_pending(exc, "benign.py", set()), status)
            self.assertEqual(len(exc), 1, status)

    def test_sweep_keeps_legacy_without_line_hash(self):  # AC-5
        from wave_lint_lib.secrets_validators import _sweep_suppressed_pending
        e = self._pending()
        del e["line_hash"]
        exc = [e]
        self.assertFalse(_sweep_suppressed_pending(exc, "benign.py", set()))
        self.assertEqual(len(exc), 1)

    def test_sweep_scoped_to_named_file(self):
        from wave_lint_lib.secrets_validators import _sweep_suppressed_pending
        exc = [self._pending(file="other.py")]
        self.assertFalse(_sweep_suppressed_pending(exc, "benign.py", set()))
        self.assertEqual(len(exc), 1)

    # --- integration: _match_hits_for_file full-scan gate (no current hits) ---
    def _match(self, exc, prune):
        from wave_lint_lib.secrets_validators import _match_hits_for_file
        return _match_hits_for_file(
            "benign.py", [self.LINE], "sha", [],  # [] = no current hits
            exc, set(), 2, "tester@example.com",
            0, None, prune_suppressed=prune,
        )

    def test_full_scan_prunes_phantom(self):  # AC-1 (integration)
        exc = [self._pending()]
        _, changed = self._match(exc, prune=True)
        self.assertTrue(changed)
        self.assertEqual(exc, [])

    def test_incremental_keeps_phantom(self):  # AC-4
        exc = [self._pending()]
        self._match(exc, prune=False)
        self.assertEqual(len(exc), 1)  # scan_all=False → never pruned

    def test_line_removed_swept_regardless(self):  # AC-6 (no regression)
        from wave_lint_lib.secrets_validators import _match_hits_for_file
        exc = [self._pending(line_hash=_hash_line("a line now gone"))]
        _, changed = _match_hits_for_file(
            "benign.py", [self.LINE], "sha", [], exc, set(), 2, "tester@example.com",
            0, None, prune_suppressed=True,
        )
        self.assertTrue(changed)
        self.assertEqual(exc, [])  # removed by the existing line-removed sweep

    # --- end-to-end: orchestrator scan_all -> prune_suppressed wiring ---
    def _e2e(self, scan_all):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            _write_framework_toml(root)
            (root / "benign.py").write_text(self.LINE + "\n", encoding="utf-8")
            _write_exceptions(root, [self._pending()])
            with patch("wave_lint_lib.secrets_validators.get_current_git_user_email",
                       return_value="tester@example.com"):
                check_hardcoded_secrets(root, scan_all=scan_all, files=[root / "benign.py"])
            return load_exceptions(root)

    def test_e2e_full_scan_prunes(self):  # AC-1 end-to-end
        self.assertEqual(self._e2e(scan_all=True), [])

    def test_e2e_incremental_keeps(self):  # AC-4 end-to-end
        self.assertEqual(len(self._e2e(scan_all=False)), 1)

    def test_broken_rule_disables_prune_fail_closed(self):  # AC-8 (security: degraded ruleset)
        # A project rule whose regex fails to compile degrades the scan; the full-scan
        # prune must then fail CLOSED (skip), or a pending entry the broken rule would
        # have caught is silently dropped (fail-open miss of a possibly-real secret).
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            _write_framework_toml(root)
            _write_project_toml(root, "[[rules]]\nid = \"broken-rule\"\nregex = '''(unclosed'''\n")
            (root / "benign.py").write_text(self.LINE + "\n", encoding="utf-8")
            _write_exceptions(root, [self._pending()])
            with patch("wave_lint_lib.secrets_validators.get_current_git_user_email",
                       return_value="tester@example.com"):
                check_hardcoded_secrets(root, scan_all=True, files=[root / "benign.py"])
            self.assertEqual(len(load_exceptions(root)), 1)  # kept — degraded ruleset


class TestRe2PythonRegexCompat(unittest.TestCase):
    """Wave 1p4d1 — RE2→Python regex compatibility shim. 26 Gitleaks rules used
    RE2-only syntax (`(?i)` mid-pattern, `\\z`) that Python's `re` rejects, so they
    failed `re.compile` and were silently dead. The shim translates on failure only."""

    def _framework_rules(self):
        if tomllib is None:
            self.skipTest("tomllib unavailable")
        path = SCRIPTS_ROOT.parent / "scan-rules.toml"
        return tomllib.load(open(path, "rb")).get("rules", [])

    def _compile_with_shim(self, rx):
        from wave_lint_lib.secrets_validators import _re2_to_re
        try:
            return re.compile(rx)
        except re.error:
            return re.compile(_re2_to_re(rx))

    def test_all_framework_rules_compile(self):  # AC-1
        failed = []
        for r in self._framework_rules():
            rx = r.get("regex")
            if not rx:
                continue
            try:
                self._compile_with_shim(rx)
            except re.error as e:
                failed.append((r["id"], str(e)))
        self.assertEqual(failed, [], f"{len(failed)} rule(s) fail to compile even after shim: {failed[:5]}")

    def test_shim_translates_only_on_failure(self):  # AC-2 — no-op on valid patterns
        from wave_lint_lib.secrets_validators import _re2_to_re
        orig_broken = sum(
            1 for r in self._framework_rules()
            if r.get("regex") and self._fails(r["regex"])
        )
        self.assertGreater(orig_broken, 0)  # the previously-dead set exists
        # A valid pattern with a leading (?i) WOULD be altered by the shim — proving the
        # call-site gating (translate only on failure) is what leaves valid patterns intact.
        self.assertNotEqual(_re2_to_re("(?i)abc"), "(?i)abc")
        self.assertEqual(re.compile("(?i)abc").pattern, "(?i)abc")

    @staticmethod
    def _fails(rx):
        try:
            re.compile(rx); return False
        except re.error:
            return True

    def test_shim_preserves_prefix_case_sensitivity(self):  # AC-3
        from wave_lint_lib.secrets_validators import _re2_to_re
        rules = {r["id"]: r for r in self._framework_rules()}
        adobe = re.compile(_re2_to_re(rules["adobe-client-secret"]["regex"]))
        self.assertTrue(adobe.search('"p8e-A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"'))
        self.assertFalse(adobe.search('"P8E-' + "a" * 32 + '"'))  # wrong-case prefix rejected
        # authress's pre-existing scoped negative flag must survive translation.
        self.assertIn("(?-i:acc)", _re2_to_re(rules["authress-service-client-access-key"]["regex"]))

    def test_previously_dead_rules_now_detect(self):  # AC-4
        rules = {r["id"]: r for r in self._framework_rules()}
        cases = {
            "adobe-client-secret": '"p8e-A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"',
            "sendgrid-api-token": '"SG.' + "a" * 22 + "." + "b" * 43 + '"',
            "slack-session-cookie": "xoxd-" + "a" * 120,
            "gocardless-api-token": 'gocardless_key = "live_' + "a" * 40 + '"',
        }
        for rid, token in cases.items():
            pat = self._compile_with_shim(rules[rid]["regex"])
            self.assertTrue(pat.search(token), f"{rid} should now detect its token")

    def test_genuinely_malformed_regex_still_skipped(self):  # AC-5
        from wave_lint_lib.secrets_validators import _re2_to_re
        with self.assertRaises(re.error):
            re.compile(_re2_to_re("(unclosed"))  # shim does not mask a real syntax error

    def test_alternation_scoped_flag_does_not_kill_branch(self):  # AC-3 (faithfulness review fix)
        # curl-auth-header has a (?i) in EACH of its "…"|'…' branches sharing one group.
        # A scoped flag must stop at the alternation bar, or it swallows the | and the
        # single-quote branch goes dead (a fail-open narrowing caught by the RE2 oracle).
        rules = {r["id"]: r for r in self._framework_rules()}
        pat = self._compile_with_shim(rules["curl-auth-header"]["regex"])
        tok = "abcd1234EFGH5678ijkl"
        self.assertTrue(pat.search(f'curl -H "Authorization: Bearer {tok}"'))   # double-quote
        self.assertTrue(pat.search(f"curl -H 'Authorization: Bearer {tok}'"))   # single-quote (was dead)
        self.assertTrue(pat.search(f"curl --header 'X-Api-Key: {tok}'"))

    def test_scoped_flag_never_crosses_alternation_bar(self):  # unit guard for _enclosing_group_close
        from wave_lint_lib.secrets_validators import _re2_to_re
        # (?i) in one alternative must not extend its scoped group across the | bar.
        out = _re2_to_re('(?:a(?i)B|c)')
        self.assertEqual(re.compile(out).pattern, out)  # compiles
        self.assertTrue(re.search(out, "ab"))   # branch 1, CI applied
        self.assertTrue(re.search(out, "c"))    # branch 2 still reachable (not swallowed)
        self.assertFalse(re.search(out, "C"))   # branch 2 stays case-sensitive (no flag bleed)


class TestFullScanBaseline(unittest.TestCase):
    """Wave 1p450 — a full-repo baseline (scan_all=True) classifies secrets in
    unchanged files that the incremental (changed-files-only) path misses."""

    _STRIPE_KEY = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_root(self.root)
        _write_framework_toml(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _commit_secret_then_leave_clean(self):
        import subprocess as _sp
        (self.root / "untouched.py").write_text(
            f'key = "{self._STRIPE_KEY}"\n', encoding="utf-8"
        )
        _sp.run(["git", "init", "-q"], cwd=self.root, check=True)
        _sp.run(["git", "add", "."], cwd=self.root, check=True)
        _sp.run(
            ["git", "-c", "user.email=a@x.com", "-c", "user.name=A",
             "-c", "commit.gpgsign=false", "commit", "-q", "-m", "init"],
            cwd=self.root, check=True,
        )

    def test_full_scan_finds_secret_in_unchanged_file(self):  # AC-3 / AC-4 / AC-6
        self._commit_secret_then_leave_clean()
        full = _run_check(self.root, scan_all=True)
        self.assertTrue(any("untouched.py" in e for e in full),
                        "full baseline must classify the unchanged file")

    def test_incremental_misses_unchanged_file(self):  # AC-6 contrast
        self._commit_secret_then_leave_clean()
        self.assertEqual(_run_check(self.root, scan_all=False), [],
                         "incremental path scans only changed files → misses it")


class TestAlwaysPresentLedger(unittest.TestCase):
    """Wave 1p8o5 #4 / AC-4 — a CLEAN full scan (0 findings, no prior file) always WRITES
    `docs/scan-findings.json` as a bare `[]` so the file's presence confirms a scan ran. The bare `[]`
    keeps the gate semantics (`[]` → no block) and the incremental-scan trigger intact, and is
    idempotent (no git churn across repeated clean scans)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_root(self.root)
        _write_framework_toml(self.root)
        self.findings_path = self.root / SCAN_FINDINGS_PATH

    def tearDown(self):
        self.tmp.cleanup()

    def _seed_clean_repo(self):
        # A benign file with no secrets (committed so get_scan_files sees it on a full scan).
        import subprocess as _sp
        (self.root / "benign.py").write_text("x = 1\n", encoding="utf-8")
        _sp.run(["git", "init", "-q"], cwd=self.root, check=True)
        _sp.run(["git", "add", "."], cwd=self.root, check=True)
        _sp.run(
            ["git", "-c", "user.email=a@x.com", "-c", "user.name=A",
             "-c", "commit.gpgsign=false", "commit", "-q", "-m", "init"],
            cwd=self.root, check=True,
        )

    def test_clean_full_scan_writes_bare_empty_list(self):  # AC-4
        self._seed_clean_repo()
        self.assertFalse(self.findings_path.exists(), "precondition: no ledger yet")
        failures = _run_check(self.root, scan_all=True)
        self.assertEqual(failures, [], "clean repo must report no findings")
        self.assertTrue(self.findings_path.exists(),
                        "a clean full scan must WRITE the ledger (presence = scan ran)")
        # Bare `[]` — not a metadata wrapper. load_exceptions returns an empty LIST.
        self.assertEqual(load_exceptions(self.root), [])
        self.assertEqual(self.findings_path.read_text(encoding="utf-8"), "[]\n")

    def test_clean_scan_is_idempotent_no_churn(self):  # AC-4 (no-churn proof)
        self._seed_clean_repo()
        _run_check(self.root, scan_all=True)
        first = self.findings_path.read_text(encoding="utf-8")
        # A second clean full scan must NOT rewrite the file to different content.
        _run_check(self.root, scan_all=True)
        second = self.findings_path.read_text(encoding="utf-8")
        self.assertEqual(first, second, "repeated clean scans must not churn the ledger content")
        self.assertEqual(second, "[]\n")

    def test_incremental_clean_scan_does_NOT_create_ledger(self):  # AC-4 (preserve incremental trigger)
        # The missing-file-forces-full-rescan trigger lives in scan_secrets.update_secrets_scan: it
        # keys on `not findings_path.exists()`. An incremental scan must therefore NOT create the file,
        # or it would silently disable that regeneration trigger. Only full scans write the bare [].
        self._seed_clean_repo()
        self.assertFalse(self.findings_path.exists())
        _run_check(self.root, scan_all=False)
        self.assertFalse(
            self.findings_path.exists(),
            "an incremental clean scan must NOT create the ledger (preserves the full-rescan trigger)",
        )


class TestLineHashMatching(unittest.TestCase):
    """Exception lookup survives line drift; stale entries are swept on next scan."""

    _STRIPE_KEY = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"
    _REDACTED = redact(_STRIPE_KEY)

    def _stripe_file(self, tmp: Path, prefix_lines: int = 0) -> Path:
        """Write config.py with optional prefix lines, then the flagged line."""
        body = ("# padding\n" * prefix_lines) + f'key = "{self._STRIPE_KEY}"\n'
        p = tmp / "config.py"
        p.write_text(body, encoding="utf-8")
        return p

    def _make_exception(self, line_no: int, line_content: str, lines: list[str]) -> dict:
        return {
            "id": "exc-001", "file": "config.py", "line": line_no,
            "line_hash": _hash_line(line_content),
            "context_hash": _hash_context(lines, line_no),
            "rule_id": "test-stripe-key",
            "matched_text": self._REDACTED,
            "status": "false-positive", "override_reason": "",
            "acknowledged_for_wave": "",
            "confirmations": [
                {"git_user_name": "A", "git_user_email": "a@x.com",
                 "verdict": "false-positive", "reason": "fixture",
                 "confirmed_at": "2026-06-06T10:00:00Z"},
                {"git_user_name": "B", "git_user_email": "b@x.com",
                 "verdict": "false-positive", "reason": "fixture",
                 "confirmed_at": "2026-06-06T11:00:00Z"},
            ],
        }

    def test_exact_line_match_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            flagged_line = f'key = "{self._STRIPE_KEY}"'
            lines = [flagged_line]
            self._stripe_file(tmp, prefix_lines=0)
            _write_exceptions(tmp, [self._make_exception(1, flagged_line, lines)])
            errors = _run_check(tmp)
            self.assertEqual(errors, [], errors)

    def test_exception_survives_large_line_drift(self) -> None:
        # Exception recorded when flagged line was at line 1 (no prefix).
        # File now has 20 padding lines above it → flagged line drifted to line 21.
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            flagged_line = f'key = "{self._STRIPE_KEY}"'
            original_lines = [flagged_line]
            exception = self._make_exception(1, flagged_line, original_lines)
            # Rewrite file with 20 padding lines before the flagged line
            self._stripe_file(tmp, prefix_lines=20)
            _write_exceptions(tmp, [exception])
            errors = _run_check(tmp)
            self.assertEqual(errors, [], errors)

    def test_exception_updates_stored_line_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            flagged_line = f'key = "{self._STRIPE_KEY}"'
            exception = self._make_exception(1, flagged_line, [flagged_line])
            self._stripe_file(tmp, prefix_lines=5)
            _write_exceptions(tmp, [exception])
            _run_check(tmp)
            updated = load_exceptions(tmp)
            self.assertEqual(updated[0]["line"], 6)  # drifted from 1 to 6

    def test_stale_exception_is_swept_when_line_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            flagged_line = f'key = "{self._STRIPE_KEY}"'
            exception = self._make_exception(1, flagged_line, [flagged_line])
            # File no longer contains the flagged line
            (tmp / "config.py").write_text("# credential removed\n", encoding="utf-8")
            _write_exceptions(tmp, [exception])
            _run_check(tmp)
            remaining = load_exceptions(tmp)
            self.assertEqual(remaining, [], "stale exception should have been swept")

    def test_hash_context_clamped_at_first_line(self) -> None:
        lines = ["only line"]
        h = _hash_context(lines, 1)
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 12)

    def test_hash_context_clamped_at_last_line(self) -> None:
        lines = ["line one", "line two", "line three"]
        h = _hash_context(lines, 3)
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 12)

    def test_duplicate_line_hash_uses_context_to_disambiguate(self) -> None:
        # Two identical flagged lines — first confirmed, second still pending.
        # Context differs because surrounding code differs.
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            flagged = f'key = "{self._STRIPE_KEY}"'
            lines = [
                "# first block",
                flagged,
                "# second block",
                flagged,
            ]
            (tmp / "config.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
            exc_line2 = {
                "id": "exc-001", "file": "config.py", "line": 2,
                "line_hash": _hash_line(flagged),
                "context_hash": _hash_context(lines, 2),
                "rule_id": "test-stripe-key",
                "matched_text": self._REDACTED,
                "status": "false-positive", "override_reason": "",
                "acknowledged_for_wave": "",
                "confirmations": [
                    {"git_user_name": "A", "git_user_email": "a@x.com",
                     "verdict": "false-positive", "reason": "fixture",
                     "confirmed_at": "2026-06-06T10:00:00Z"},
                    {"git_user_name": "B", "git_user_email": "b@x.com",
                     "verdict": "false-positive", "reason": "fixture",
                     "confirmed_at": "2026-06-06T11:00:00Z"},
                ],
            }
            # Line 4 has no exception yet — should be auto-appended as pending
            _write_exceptions(tmp, [exc_line2])
            errors = _run_check(tmp)
            # Line 2 should be suppressed (false-positive confirmed); line 4 triggers new pending
            self.assertFalse(any("line 2" in e or ":2:" in e for e in errors), errors)
            self.assertTrue(any(":4:" in e for e in errors), errors)


class TestFrameworkRuleset(unittest.TestCase):
    FRAMEWORK_ROOT = Path(__file__).resolve().parents[4]

    def test_framework_scan_rules_exists(self) -> None:
        path = self.FRAMEWORK_ROOT / SCAN_RULES_FRAMEWORK_PATH
        self.assertTrue(path.exists(), f"{SCAN_RULES_FRAMEWORK_PATH} not found")

    def test_framework_scan_rules_has_policy_section(self) -> None:
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                self.skipTest("tomllib not available")
        path = self.FRAMEWORK_ROOT / SCAN_RULES_FRAMEWORK_PATH
        if not path.exists():
            self.skipTest(f"{SCAN_RULES_FRAMEWORK_PATH} not found")
        with open(path, "rb") as f:
            data = tomllib.load(f)
        policy = data.get("policy", {})
        self.assertIn("false_positive_confirmations_required", policy)
        self.assertEqual(policy["false_positive_confirmations_required"], 2)

    def test_framework_scan_rules_has_rules(self) -> None:
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                self.skipTest("tomllib not available")
        path = self.FRAMEWORK_ROOT / SCAN_RULES_FRAMEWORK_PATH
        if not path.exists():
            self.skipTest(f"{SCAN_RULES_FRAMEWORK_PATH} not found")
        with open(path, "rb") as f:
            data = tomllib.load(f)
        rules = data.get("rules", [])
        self.assertGreater(len(rules), 0, "scan-rules.toml has no [[rules]]")

    def test_framework_scan_rules_has_provenance_header(self) -> None:
        path = self.FRAMEWORK_ROOT / SCAN_RULES_FRAMEWORK_PATH
        if not path.exists():
            self.skipTest(f"{SCAN_RULES_FRAMEWORK_PATH} not found")
        content = path.read_text(encoding="utf-8")
        self.assertIn("Commit:", content)
        self.assertIn("gitleaks", content.lower())


# Wave 1p5rd — scanner scope: framework runtime artifacts allowlisted, rglob
# fallback honors .gitignore, versioned shared objects skipped.
class ScannerScopeHardeningTests(unittest.TestCase):
    def _real_allowlist_paths(self) -> list[str]:
        toml_path = SCRIPTS_ROOT.parent / "scan-rules.toml"
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        return list(data.get("allowlist", {}).get("paths", []))

    def test_runtime_artifacts_allowlisted_framework_source_not(self):
        # AC-1: the SHIPPED ruleset excludes framework runtime artifacts but keeps
        # framework source scannable.
        paths = self._real_allowlist_paths()
        for excluded in (
            ".wavefoundry/index/code.lance/data/x.lance",
            ".wavefoundry/index/scan/scan-state.json",
            ".wavefoundry/cache/onnx/model.onnx",
            ".wavefoundry/logs/upgrade.log",
            ".wavefoundry/dist/wavefoundry-1.6.1.p5r9.zip",
            "wavefoundry-1.6.1.p5r9.zip",
        ):
            self.assertTrue(_path_matches_allowlist(excluded, paths),
                            f"{excluded} should be allowlisted")
        # The runtime-artifact rule must NOT catch framework SOURCE (still scannable).
        runtime_rule = r'''(?:^|/)\.wavefoundry/(?:index|cache|logs|dist)(?:/.*)?$'''
        self.assertFalse(re.search(runtime_rule, ".wavefoundry/framework/scripts/server_impl.py"))
        self.assertFalse(re.search(runtime_rule, ".wavefoundry/framework/seeds/213-security-reviewer.prompt.md"))

    def test_is_binary_path_versioned_shared_objects(self):
        # AC-2: versioned .so.N / .dylib.N are binary; .so.txt and dotted source are not.
        for binary in ("libfoo.so", "libfoo.so.13", "libbar.dylib.1", "x.dll",
                       "data.lance", "pack.zip", "model.onnx"):
            self.assertTrue(_sv._is_binary_path(Path(binary)), binary)
        for text in ("module.py", "a.test.py", "foo.so.txt", "config.yaml", "readme.md"):
            self.assertFalse(_sv._is_binary_path(Path(text)), text)

    def test_filter_gitignored_drops_in_repo_keeps_when_non_git(self):
        # AC-2: in a real git repo, check-ignore drops .gitignore'd paths; in a
        # non-git dir the walk is kept unchanged.
        import subprocess
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            (tmp / ".gitignore").write_text("ignored/\n", encoding="utf-8")
            (tmp / "ignored").mkdir()
            (tmp / "ignored" / "secret.txt").write_text("x", encoding="utf-8")
            (tmp / "kept.py").write_text("x", encoding="utf-8")
            paths = [tmp / "ignored" / "secret.txt", tmp / "kept.py"]
            filtered = _sv._filter_gitignored(tmp, paths)
            names = {p.name for p in filtered}
            self.assertIn("kept.py", names)
            self.assertNotIn("secret.txt", names, "gitignored path must be dropped")
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)  # NOT a git repo
            (tmp / "a.py").write_text("x", encoding="utf-8")
            paths = [tmp / "a.py"]
            self.assertEqual(_sv._filter_gitignored(tmp, paths), paths,
                             "non-git dir: check-ignore errors → keep the walk")

    def test_artifact_with_secret_not_flagged_source_is(self):
        # AC-1 end-to-end (non-git tree → rglob fallback selects everything): a
        # secret-looking string in a .lance is skipped; the same in a .py is flagged.
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            secret = 'key = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"\n'
            (tmp / ".wavefoundry" / "index").mkdir(parents=True, exist_ok=True)
            (tmp / ".wavefoundry" / "index" / "data.lance").write_text(secret, encoding="utf-8")
            (tmp / "config.py").write_text(secret, encoding="utf-8")
            errors = _run_check(tmp)
            self.assertTrue(any("test-stripe-key" in e for e in errors), "source secret must be flagged")
            self.assertFalse(any(".lance" in e for e in errors), "LanceDB artifact must not be flagged")


# ---------------------------------------------------------------------------
# Wave 1p8l0 — lifecycle-backed `<prefix>-sec` finding IDs + migration
# ---------------------------------------------------------------------------

import lifecycle_id as _lifecycle_id  # noqa: E402

# Deterministic lifecycle policy for prefix math (matches the lib default epoch).
_LIFECYCLE_EPOCH = _lifecycle_id.DEFAULT_EPOCH_UTC
# A fixed mint timestamp → a fixed prefix for the default epoch ('1p400' family).
_MINT_TS = datetime(2026, 6, 8, tzinfo=timezone.utc)


def _reset_lifecycle_floor() -> None:
    """Reset the in-process lifecycle prefix floor so per-test prefix math is
    deterministic regardless of test ordering (wave 1p8l0)."""
    _lifecycle_id._last_assigned_prefix = None


class TestSecretFindingIdShape(unittest.TestCase):
    """AC-1 / AC-7 / AC-8 — new scanner findings use `<prefix>-sec`, no slug,
    and `sec` is collision-safe but not a public change-doc kind."""

    _STRIPE_KEY = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"

    def setUp(self) -> None:
        _reset_lifecycle_floor()

    def test_new_finding_id_matches_sec_regex(self) -> None:  # AC-1
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            (tmp / "config.py").write_text(f'key = "{self._STRIPE_KEY}"\n', encoding="utf-8")
            _run_check(tmp)
            findings = load_exceptions(tmp)
            self.assertEqual(len(findings), 1)
            fid = findings[0]["id"]
            self.assertRegex(fid, r"^[0-9a-z]{5}-sec$", f"bad id shape: {fid}")
            self.assertTrue(_SEC_ID_RE.fullmatch(fid))

    def test_new_finding_id_has_no_slug(self) -> None:  # AC-8
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            (tmp / "config.py").write_text(f'key = "{self._STRIPE_KEY}"\n', encoding="utf-8")
            _run_check(tmp)
            fid = load_exceptions(tmp)[0]["id"]
            self.assertNotIn(" ", fid, "scanner id must carry no slug")
            self.assertTrue(fid.endswith("-sec"))

    def test_helper_pins_prefix_with_timestamp(self) -> None:  # AC-10 determinism
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            (tmp / "docs").mkdir(parents=True, exist_ok=True)
            fid = _next_secret_finding_id(tmp, [], timestamp=_MINT_TS)
            expected_prefix = _lifecycle_id.build_prefix(_MINT_TS)
            self.assertEqual(fid, f"{expected_prefix}-sec")

    def test_multiple_findings_in_one_scan_get_distinct_sec_ids(self) -> None:  # AC-6
        toml = """
title = "t"
[policy]
false_positive_confirmations_required = 2
[[rules]]
id = "rule-a"
regex = '''SECRET_A_[A-Z]{8}'''
[[rules]]
id = "rule-b"
regex = '''SECRET_B_[A-Z]{8}'''
"""
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp, toml)
            (tmp / "x.py").write_text(
                'a = "SECRET_A_ABCDEFGH"\nb = "SECRET_B_ABCDEFGH"\n', encoding="utf-8"
            )
            _run_check(tmp)
            ids = [e["id"] for e in load_exceptions(tmp)]
            self.assertEqual(len(ids), 2)
            self.assertEqual(len(set(ids)), 2, f"duplicate sec ids minted in one scan: {ids}")
            for fid in ids:
                self.assertRegex(fid, r"^[0-9a-z]{5}-sec$")

    def test_sec_not_a_public_change_doc_kind(self) -> None:  # AC-7 — guard
        """`sec` must never become a normal change-doc kind. Assert the
        `wave_new_*` kind lists are unchanged (do not include `sec`)."""
        import server_impl
        self.assertNotIn("sec", server_impl.VALID_CHANGE_KINDS)
        # The lifecycle CLI mint-kind choices must also not expose `sec`.
        args = _lifecycle_id.parse_args(["--kind", "change", "--slug", "x"])
        self.assertEqual(args.kind, "change")
        with self.assertRaises(SystemExit):
            _lifecycle_id.parse_args(["--kind", "sec", "--slug", "x"])


class TestSecretFindingIdCollision(unittest.TestCase):
    """AC-6 — new/migrated `sec` ids dedupe against existing lifecycle prefixes
    (plans/waves/ADRs) AND existing finding ids."""

    def setUp(self) -> None:
        _reset_lifecycle_floor()

    def test_mint_skips_taken_lifecycle_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            (tmp / "docs" / "plans").mkdir(parents=True, exist_ok=True)
            natural = _lifecycle_id.build_prefix(_MINT_TS)
            # Park a plan doc on the natural prefix so the mint must skip it.
            (tmp / "docs" / "plans" / f"{natural}-enh taken.md").touch()
            fid = _next_secret_finding_id(tmp, [], timestamp=_MINT_TS)
            self.assertNotEqual(fid, f"{natural}-sec")
            self.assertRegex(fid, r"^[0-9a-z]{5}-sec$")

    def test_mint_skips_existing_finding_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            (tmp / "docs").mkdir(parents=True, exist_ok=True)
            natural = _lifecycle_id.build_prefix(_MINT_TS)
            existing = [{"id": f"{natural}-sec", "file": "a.py", "line": 1,
                         "rule_id": "r", "status": "pending"}]
            fid = _next_secret_finding_id(tmp, existing, timestamp=_MINT_TS)
            self.assertNotEqual(fid, f"{natural}-sec")
            self.assertRegex(fid, r"^[0-9a-z]{5}-sec$")


class TestGateSemanticsUnchanged(unittest.TestCase):
    """Secrets-gate behavior keys on `status`, never the id shape: pending/suspected block,
    confirmed reminds (non-blocking), cleared FP clears — verified by driving the real wave_close
    gate helper with both legacy `exc-###` and `<prefix>-sec` ids. (1p8vq: this also pins that a
    legacy ledger stays gate-correct after the `exc-###` migration was removed.)"""

    def setUp(self) -> None:
        _reset_lifecycle_floor()
        import server_impl
        self._gate = server_impl._check_secrets_gate
        self._notice = server_impl._confirmed_secret_notice

    def _write(self, tmp: Path, entries: list[dict]) -> None:
        (tmp / "docs").mkdir(parents=True, exist_ok=True)
        _write_exceptions(tmp, entries)

    def _entry(self, fid: str, status: str, **extra) -> dict:
        e = {"id": fid, "file": "a.py", "line": 1, "rule_id": "r", "status": status}
        e.update(extra)
        return e

    def _assert_gate(self, tmp: Path, *, blocks: bool, reminds: bool) -> None:
        diags = self._gate(tmp, "1p8nw test-wave")
        if blocks:
            self.assertTrue(diags, "gate should block but returned no diagnostics")
        else:
            self.assertEqual(diags, [], f"gate should NOT block: {diags}")
        notice = self._notice(tmp)
        if reminds:
            self.assertIsNotNone(notice, "confirmed-secret reminder should be present")
        else:
            self.assertIsNone(notice, "no confirmed-secret reminder expected")

    def test_pending_blocks_both_id_shapes(self) -> None:
        for fid in ("exc-001", "1p400-sec"):
            with self.subTest(id=fid), tempfile.TemporaryDirectory() as tmp_str:
                tmp = Path(tmp_str)
                self._write(tmp, [self._entry(fid, "pending")])
                self._assert_gate(tmp, blocks=True, reminds=False)

    def test_suspected_blocks_both_id_shapes(self) -> None:
        for fid in ("exc-002", "1p401-sec"):
            with self.subTest(id=fid), tempfile.TemporaryDirectory() as tmp_str:
                tmp = Path(tmp_str)
                self._write(tmp, [self._entry(fid, "suspected-secret")])
                self._assert_gate(tmp, blocks=True, reminds=False)

    def test_confirmed_does_not_block_but_reminds_both_id_shapes(self) -> None:
        for fid in ("exc-003", "1p402-sec"):
            with self.subTest(id=fid), tempfile.TemporaryDirectory() as tmp_str:
                tmp = Path(tmp_str)
                self._write(tmp, [self._entry(fid, "confirmed-secret")])
                self._assert_gate(tmp, blocks=False, reminds=True)

    def test_false_positive_clears_both_id_shapes(self) -> None:
        for fid in ("exc-004", "1p403-sec"):
            with self.subTest(id=fid), tempfile.TemporaryDirectory() as tmp_str:
                tmp = Path(tmp_str)
                self._write(tmp, [self._entry(fid, "false-positive")])
                self._assert_gate(tmp, blocks=False, reminds=False)

    def test_legacy_ledger_gates_correctly_and_is_not_rewritten(self) -> None:
        """1p8vq: with the `exc-###` migration removed, a legacy ledger is still READ and
        gate-correct (the gate keys on `status`, not id shape) — and the scanner no longer
        rewrites the old ids to the `sec` shape."""
        stripe = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _make_root(tmp)
            _write_framework_toml(tmp)
            line = f'key = "{stripe}"'
            (tmp / "config.py").write_text(line + "\n", encoding="utf-8")
            _write_exceptions(tmp, [{
                "id": "exc-001", "file": "config.py", "line": 1,
                "line_hash": _hash_line(line), "context_hash": _hash_context([line], 1),
                "rule_id": "test-stripe-key", "matched_text": redact(stripe),
                "status": "pending",
            }])
            errors = _run_check(tmp)
            self.assertTrue(any("pending" in e for e in errors), errors)
            findings = load_exceptions(tmp)
            self.assertEqual(findings[0]["id"], "exc-001", "legacy id must be left as-is (no migration)")
            self.assertNotIn("legacy_id", findings[0])


if __name__ == "__main__":
    unittest.main()
