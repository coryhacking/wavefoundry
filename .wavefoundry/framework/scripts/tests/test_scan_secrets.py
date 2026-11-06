"""Tests for rules-hash auto-escalation in scan_secrets.py and run_secrets_scan.py."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_ROOT))

import scan_secrets
import run_secrets_scan

_FINDINGS_RELPATH = "docs/scan-findings.json"


def _make_root(tmp: Path) -> None:
    (tmp / ".wavefoundry").mkdir(parents=True, exist_ok=True)
    (tmp / "docs").mkdir(parents=True, exist_ok=True)
    (tmp / ".wavefoundry/framework").mkdir(parents=True, exist_ok=True)
    (tmp / ".wavefoundry/framework/scan-rules.toml").write_text(
        "[policy]\nfalse_positive_confirmations_required = 2\n", encoding="utf-8"
    )
    (tmp / _FINDINGS_RELPATH).write_text("[]", encoding="utf-8")


def _make_scan_dir(tmp: Path) -> Path:
    scan_dir = tmp / ".wavefoundry/index/scan"
    scan_dir.mkdir(parents=True, exist_ok=True)
    return scan_dir


def _inject_mock_validators(captured: list) -> types.ModuleType:
    """Return a mock wave_lint_lib.secrets_validators that records scan_all calls."""
    mod = types.ModuleType("wave_lint_lib.secrets_validators")

    def fake_check(root, *, scan_all=False, files=None, max_workers=1):
        captured.append(scan_all)
        return []

    def fake_get_scan_files(root, scan_all):
        captured.append(("get_scan_files", scan_all))
        return []

    mod.check_hardcoded_secrets = fake_check
    mod.get_scan_files = fake_get_scan_files
    mod.unpublished_scanner_skips = lambda: []  # wave 1x5tr seam
    return mod


def _inject_mock_constants() -> types.ModuleType:
    mod = types.ModuleType("wave_lint_lib.constants")
    mod.SCAN_FINDINGS_PATH = _FINDINGS_RELPATH
    return mod


# ---------------------------------------------------------------------------
# _compute_rules_hash — unit tests (both modules must agree)
# ---------------------------------------------------------------------------

class TestComputeRulesHash(unittest.TestCase):

    def test_consistent_across_calls(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            self.assertEqual(
                scan_secrets._compute_rules_hash(root),
                scan_secrets._compute_rules_hash(root),
            )

    def test_framework_file_change_alters_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            fw = root / ".wavefoundry/framework/scan-rules.toml"
            h1 = scan_secrets._compute_rules_hash(root)
            fw.write_text("[policy]\nfalse_positive_confirmations_required = 3\n", encoding="utf-8")
            h2 = scan_secrets._compute_rules_hash(root)
            self.assertNotEqual(h1, h2)

    def test_project_file_added_alters_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            h1 = scan_secrets._compute_rules_hash(root)
            (root / "docs/scan-rules.toml").write_text("[policy]\nfalse_positive_confirmations_required = 1\n", encoding="utf-8")
            h2 = scan_secrets._compute_rules_hash(root)
            self.assertNotEqual(h1, h2)

    def test_project_file_content_change_alters_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            proj = root / "docs/scan-rules.toml"
            proj.write_text("[policy]\nfalse_positive_confirmations_required = 1\n", encoding="utf-8")
            h1 = scan_secrets._compute_rules_hash(root)
            proj.write_text("[policy]\nfalse_positive_confirmations_required = 2\n", encoding="utf-8")
            h2 = scan_secrets._compute_rules_hash(root)
            self.assertNotEqual(h1, h2)

    def test_both_modules_produce_same_hash(self):
        """scan_secrets and run_secrets_scan must agree on the hash."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            (root / "docs/scan-rules.toml").write_text("# project extra\n", encoding="utf-8")
            self.assertEqual(
                scan_secrets._compute_rules_hash(root),
                run_secrets_scan._compute_rules_hash(root),
            )

    def test_no_files_returns_stable_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            # Remove framework file so both are absent
            (root / ".wavefoundry/framework/scan-rules.toml").unlink()
            h = scan_secrets._compute_rules_hash(root)
            self.assertIsInstance(h, str)
            self.assertEqual(len(h), 64)  # SHA-256 hex


# ---------------------------------------------------------------------------
# update_secrets_scan — escalation logic (scan_secrets.py)
# ---------------------------------------------------------------------------

class TestUpdateSecretsScanEscalation(unittest.TestCase):

    def _call_update(self, root: Path, scan_dir: Path, stored_state: dict, changed: set) -> list:
        """Set stored scan-state, call update_secrets_scan, return captured scan_all values."""
        scan_secrets._save_scan_state(scan_dir, stored_state)
        captured: list = []
        mock_validators = _inject_mock_validators(captured)
        mock_constants = _inject_mock_constants()
        with patch.dict(sys.modules, {
            "wave_lint_lib": types.ModuleType("wave_lint_lib"),
            "wave_lint_lib.secrets_validators": mock_validators,
            "wave_lint_lib.constants": mock_constants,
        }):
            scan_secrets.update_secrets_scan(
                root=root, scan_dir=scan_dir,
                changed=changed, removed=set(), full=False,
            )
        # captured contains scan_all values from fake_check calls
        return [v for v in captured if isinstance(v, bool)]

    def test_no_stored_hash_escalates_to_full(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            scan_dir = _make_scan_dir(root)
            calls = self._call_update(root, scan_dir, {
                "scanner_version": scan_secrets.SCANNER_VERSION,
                # no rules_hash
            }, {"some/file.py"})
            self.assertTrue(calls[0], "missing rules_hash should escalate to full")

    def test_stale_hash_escalates_to_full(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            scan_dir = _make_scan_dir(root)
            calls = self._call_update(root, scan_dir, {
                "scanner_version": scan_secrets.SCANNER_VERSION,
                "rules_hash": "stale-hash-that-wont-match",
            }, {"some/file.py"})
            self.assertTrue(calls[0], "stale rules_hash should escalate to full")

    def test_current_hash_stays_incremental(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            scan_dir = _make_scan_dir(root)
            current_hash = scan_secrets._compute_rules_hash(root)
            calls = self._call_update(root, scan_dir, {
                "scanner_version": scan_secrets.SCANNER_VERSION,
                "rules_hash": current_hash,
            }, {"some/file.py"})
            self.assertFalse(calls[0], "current rules_hash should stay incremental")

    def test_rules_hash_written_to_state_after_scan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            scan_dir = _make_scan_dir(root)
            mock_validators = _inject_mock_validators([])
            mock_constants = _inject_mock_constants()
            with patch.dict(sys.modules, {
                "wave_lint_lib": types.ModuleType("wave_lint_lib"),
                "wave_lint_lib.secrets_validators": mock_validators,
                "wave_lint_lib.constants": mock_constants,
            }):
                scan_secrets.update_secrets_scan(
                    root=root, scan_dir=scan_dir,
                    changed={"some/file.py"}, removed=set(), full=False,
                )
            state = scan_secrets._load_scan_state(scan_dir)
            self.assertEqual(state.get("rules_hash"), scan_secrets._compute_rules_hash(root))

    def test_rules_hash_updated_after_framework_toml_change(self):
        """After rules change → full scan → new hash saved → next run is incremental."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _make_root(root)
            scan_dir = _make_scan_dir(root)
            old_hash = scan_secrets._compute_rules_hash(root)
            # Simulate previous scan with old hash
            scan_secrets._save_scan_state(scan_dir, {
                "scanner_version": scan_secrets.SCANNER_VERSION,
                "rules_hash": old_hash,
            })
            # Change the framework rules
            (root / ".wavefoundry/framework/scan-rules.toml").write_text(
                "[policy]\nfalse_positive_confirmations_required = 3\n", encoding="utf-8"
            )
            calls_round1: list = []
            mock_validators = _inject_mock_validators(calls_round1)
            mock_constants = _inject_mock_constants()
            with patch.dict(sys.modules, {
                "wave_lint_lib": types.ModuleType("wave_lint_lib"),
                "wave_lint_lib.secrets_validators": mock_validators,
                "wave_lint_lib.constants": mock_constants,
            }):
                scan_secrets.update_secrets_scan(
                    root=root, scan_dir=scan_dir,
                    changed={"x.py"}, removed=set(), full=False,
                )
            bool_calls_1 = [v for v in calls_round1 if isinstance(v, bool)]
            self.assertTrue(bool_calls_1[0], "round 1: changed rules should escalate to full")

            # Second call should see current hash and stay incremental
            calls_round2: list = []
            mock_validators2 = _inject_mock_validators(calls_round2)
            with patch.dict(sys.modules, {
                "wave_lint_lib": types.ModuleType("wave_lint_lib"),
                "wave_lint_lib.secrets_validators": mock_validators2,
                "wave_lint_lib.constants": mock_constants,
            }):
                scan_secrets.update_secrets_scan(
                    root=root, scan_dir=scan_dir,
                    changed={"x.py"}, removed=set(), full=False,
                )
            bool_calls_2 = [v for v in calls_round2 if isinstance(v, bool)]
            self.assertFalse(bool_calls_2[0], "round 2: hash now current, should stay incremental")


# ---------------------------------------------------------------------------
# run_secrets_scan helpers
# ---------------------------------------------------------------------------

class TestRunSecretsScanHelpers(unittest.TestCase):

    def test_load_scan_state_missing_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertEqual(run_secrets_scan._load_scan_state(root), {})

    def test_save_rules_hash_creates_state_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run_secrets_scan._save_rules_hash(root, "abc123")
            state = run_secrets_scan._load_scan_state(root)
            self.assertEqual(state["rules_hash"], "abc123")

    def test_save_rules_hash_preserves_existing_fields(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            state_path = root / run_secrets_scan._SCAN_STATE_RELPATH
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({"scanner_version": "1", "scan_type": "full"}) + "\n",
                encoding="utf-8",
            )
            run_secrets_scan._save_rules_hash(root, "newhash")
            state = run_secrets_scan._load_scan_state(root)
            self.assertEqual(state["scanner_version"], "1")
            self.assertEqual(state["scan_type"], "full")
            self.assertEqual(state["rules_hash"], "newhash")

    def test_save_rules_hash_overwrites_stale_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run_secrets_scan._save_rules_hash(root, "old")
            run_secrets_scan._save_rules_hash(root, "new")
            self.assertEqual(run_secrets_scan._load_scan_state(root)["rules_hash"], "new")

    def test_load_scan_state_corrupt_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            state_path = root / run_secrets_scan._SCAN_STATE_RELPATH
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text("not valid json", encoding="utf-8")
            self.assertEqual(run_secrets_scan._load_scan_state(root), {})


# ---------------------------------------------------------------------------
# run_secrets_scan.main() — escalation integration
# ---------------------------------------------------------------------------

class TestRunSecretsScanMainEscalation(unittest.TestCase):
    """main() escalates to full when rules_hash changed; stays incremental when current."""

    def _run_main(self, root: Path, mode: str) -> dict:
        """Call main() with mocked wave_lint_lib and capture JSON output."""
        captured_scan_all = []

        def fake_get_scan_files(r, scan_all):
            captured_scan_all.append(scan_all)
            return []

        def fake_check(r, *, files=None, max_workers=1):
            return []

        mock_mod = types.ModuleType("wave_lint_lib.secrets_validators")
        mock_mod.get_scan_files = fake_get_scan_files
        mock_mod.check_hardcoded_secrets = fake_check
        mock_mod.unpublished_scanner_skips = lambda: []  # wave 1x5tr seam

        output_lines = []

        old_argv = sys.argv
        sys.argv = ["run_secrets_scan.py", "--root", str(root), "--mode", mode]
        try:
            with patch.dict(sys.modules, {"wave_lint_lib.secrets_validators": mock_mod}), \
                 patch("builtins.print", side_effect=lambda *a, **k: output_lines.append(str(a[0])) if a else None):
                run_secrets_scan.main()
        finally:
            sys.argv = old_argv

        result = json.loads(output_lines[-1]) if output_lines else {}
        result["_captured_scan_all"] = captured_scan_all
        return result

    def _setup_root(self, tmp: Path) -> Path:
        _make_root(tmp)
        return tmp

    def test_mode_full_uses_full_scan_path(self):  # wave 1p450 AC-7
        # The full-scan entrypoint that wf_scan_secrets(mode="full") backs must
        # resolve to scan_all=True (covers all tracked files), distinct from the
        # default incremental path.
        with tempfile.TemporaryDirectory() as d:
            root = self._setup_root(Path(d))
            result = self._run_main(root, "full")
            self.assertTrue(result["_captured_scan_all"][0], "mode='full' must set scan_all=True")

    def test_no_stored_hash_escalates_incremental_to_full(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._setup_root(Path(d))
            result = self._run_main(root, "incremental")
            self.assertTrue(result["_captured_scan_all"][0], "should escalate to full")
            self.assertTrue(result["rules_hash_changed"])
            self.assertTrue(result["escalated_to_full"])

    def test_stale_hash_escalates_incremental_to_full(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._setup_root(Path(d))
            run_secrets_scan._save_rules_hash(root, "stale-hash")
            result = self._run_main(root, "incremental")
            self.assertTrue(result["_captured_scan_all"][0])
            self.assertTrue(result["rules_hash_changed"])
            self.assertTrue(result["escalated_to_full"])

    def test_current_hash_stays_incremental(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._setup_root(Path(d))
            run_secrets_scan._save_rules_hash(root, run_secrets_scan._compute_rules_hash(root))
            result = self._run_main(root, "incremental")
            # Wave 1rsh9 (1rsha): candidates are now ALWAYS all tracked files
            # (get_scan_files(root, True)) — the content-addressed cache skip
            # replaced the git-changed-only gate — so the captured scan_all
            # arg is True either way; "no escalation" is asserted via the
            # escalation flags instead.
            self.assertFalse(result["rules_hash_changed"])
            self.assertFalse(result["escalated_to_full"])
            self.assertIn("files_scanned", result)
            self.assertIn("files_skipped", result)

    def test_explicit_full_mode_not_flagged_as_escalated(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._setup_root(Path(d))
            # Even with current hash, mode=full → scan_all=True, but NOT escalated_to_full
            run_secrets_scan._save_rules_hash(root, run_secrets_scan._compute_rules_hash(root))
            result = self._run_main(root, "full")
            self.assertTrue(result["_captured_scan_all"][0], "full mode always scans all")
            self.assertFalse(result["escalated_to_full"], "explicitly full is not an escalation")

    def test_hash_saved_after_main_run(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._setup_root(Path(d))
            self._run_main(root, "incremental")
            state = run_secrets_scan._load_scan_state(root)
            self.assertEqual(state.get("rules_hash"), run_secrets_scan._compute_rules_hash(root))


class ActualRulesChangeConsumers(unittest.TestCase):
    """Both cache producers must rescan unchanged content after a rule edit."""

    def _run_owner(self, owner, root):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), \
             patch.object(scan_secrets, "_auto_max_workers", return_value=1), \
             patch.object(run_secrets_scan, "_auto_max_workers", return_value=1):
            if owner == "indexer":
                return scan_secrets.update_secrets_scan(
                    root=root, scan_dir=_make_scan_dir(root),
                    changed=set(), removed=set(), full=False,
                )
            with patch.object(sys, "argv", [
                "run_secrets_scan.py", "--root", str(root), "--mode", "incremental"
            ]):
                self.assertEqual(run_secrets_scan.main(), 0)
            return json.loads(output.getvalue().splitlines()[-1])

    def _exercise(self, owner, *, frozen_fingerprint=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _make_root(root)
            framework = root / ".wavefoundry/framework/scan-rules.toml"
            framework.write_text(
                '[policy]\nfalse_positive_confirmations_required = 1\n'
                '[allowlist]\npaths = ["^\\\\.wavefoundry/", "^docs/"]\n'
                '[[rules]]\nid = "synthetic-probe"\n'
                "regex = '''SYNTH_ALPHA_[0-9]{3}'''\n",
                encoding="utf-8",
            )
            content = b"SYNTH_ALPHA_001\nSYNTH_BETA_002\n"
            subject = root / "unchanged.txt"
            subject.write_bytes(content)
            findings = root / _FINDINGS_RELPATH
            self._run_owner(owner, root)
            initial = json.loads(findings.read_text())
            self.assertEqual(len(initial), 1)
            self.assertEqual(initial[0]["file"], "unchanged.txt")
            # Seed a pre-existing synthetic disposition, never a live finding.
            history = [{"confirmed_by": "fixture-reviewer", "confirmed_at": "2026-01-01"}]
            initial[0].update(status="false-positive", confirmations=history,
                              override_reason="Synthetic fixture disposition")
            findings.write_text(json.dumps(initial), encoding="utf-8")
            stable_id = initial[0]["id"]
            old_hash = scan_secrets._compute_rules_hash(root)
            unchanged = self._run_owner(owner, root)
            if owner == "indexer":
                self.assertTrue(unchanged["up_to_date"])
            else:
                self.assertFalse(unchanged["rules_hash_changed"])
                self.assertGreaterEqual(unchanged["files_skipped"], 1)

            (root / "docs/scan-rules.toml").write_text(
                '[[rules]]\nid = "synthetic-probe"\n'
                "regex = '''SYNTH_(?:ALPHA|BETA)_[0-9]{3}'''\n",
                encoding="utf-8",
            )
            module = scan_secrets if owner == "indexer" else run_secrets_scan
            control = (patch.object(module, "_compute_rules_hash", return_value=old_hash)
                       if frozen_fingerprint else contextlib.nullcontext())
            with control:
                result = self._run_owner(owner, root)
            current = json.loads(findings.read_text())
            self.assertEqual(len(current), 2, "newly detected unchanged file must survive cache reuse")
            self.assertEqual({row["line"] for row in current}, {1, 2})
            retained = next(row for row in current if row["id"] == stable_id)
            self.assertEqual(retained["status"], "false-positive")
            self.assertEqual(retained["confirmations"], history)
            self.assertEqual(retained["override_reason"], "Synthetic fixture disposition")
            self.assertTrue(result["rules_change_escalation"] if owner == "indexer"
                            else result["escalated_to_full"])
            self.assertEqual(subject.read_bytes(), content)
            self.assertNotIn("SYNTH_BETA_002", findings.read_text())
            self.assertEqual(scan_secrets._compute_rules_hash(root),
                             run_secrets_scan._load_scan_state(root)["rules_hash"])

    def test_indexer_rule_change_rescans_and_preserves_disposition(self):
        self._exercise("indexer")

    def test_cli_rule_change_rescans_and_preserves_disposition(self):
        self._exercise("cli")

    def test_stale_fingerprint_mutants_lose_the_new_finding(self):
        for owner in ("indexer", "cli"):
            with self.subTest(owner=owner), self.assertRaisesRegex(
                AssertionError, "newly detected unchanged file"
            ):
                self._exercise(owner, frozen_fingerprint=True)


if __name__ == "__main__":
    unittest.main()
