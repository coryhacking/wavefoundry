from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TESTS_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TESTS_ROOT.parent
sys.path.insert(0, str(SCRIPTS_ROOT))

from wave_lint_lib.secrets_validators import (
    _hash_context,
    _hash_line,
    _path_matches_allowlist,
    check_hardcoded_secrets,
    check_inline_suppression,
    get_scan_files,
    load_exceptions,
    load_merged_ruleset,
    redact,
    save_exceptions,
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


def _run_check(tmp: Path, scan_all: bool = True) -> list[str]:
    with patch("wave_lint_lib.secrets_validators.get_current_git_user_email", return_value="tester@example.com"):
        return check_hardcoded_secrets(tmp, scan_all=scan_all)


# ---------------------------------------------------------------------------
# redact()
# ---------------------------------------------------------------------------

class TestRedact(unittest.TestCase):
    def test_long_text_partial(self) -> None:
        self.assertEqual(redact("sk_live_ABCD1234EFGH5678"), "sk_l****5678")

    def test_exactly_8_chars_fully_redacted(self) -> None:
        self.assertEqual(redact("12345678"), "****")

    def test_short_text_fully_redacted(self) -> None:
        self.assertEqual(redact("abc"), "****")

    def test_nine_chars_partial(self) -> None:
        result = redact("123456789")
        self.assertEqual(result, "1234****6789")


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
            self.assertTrue(any("not yet on the list" in e for e in errors), errors)

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
            self.assertTrue(any("needs" in e and "more from a different reviewer" in e for e in errors), errors)
            self.assertFalse(any("not yet on the list" in e for e in errors))

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


if __name__ == "__main__":
    unittest.main()
