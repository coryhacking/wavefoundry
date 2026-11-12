"""Tests for rules-hash auto-escalation in scan_secrets.py and run_secrets_scan.py."""
from __future__ import annotations

import contextlib
import gzip
import io
import json
import sys
import tempfile
import types
import tomllib
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
    mod.scanner_runtime_roots = lambda: (".wavefoundry",)
    mod.is_scanner_excluded_path = lambda rel: False
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

        def fake_check(r, *, files=None, max_workers=1, history_scope=None):
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


class DetectionIdentityConsumers(unittest.TestCase):
    """Assets and executable detection code are part of both cache identities."""

    _run_owner = ActualRulesChangeConsumers._run_owner

    def test_every_detection_input_changes_both_fingerprints(self):
        self.assertEqual(len(scan_secrets._DETECTION_RELPATHS), 10)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _make_root(root)
            prior = scan_secrets._compute_rules_hash(root)
            for rel in scan_secrets._DETECTION_RELPATHS:
                with self.subTest(path=rel):
                    path = root / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"synthetic detection input identity")
                    current = scan_secrets._compute_rules_hash(root)
                    self.assertNotEqual(prior, current)
                    self.assertEqual(current, run_secrets_scan._compute_rules_hash(root))
                    prior = current

    def test_asset_engine_and_path_policy_change_rescan_unchanged_source_in_both_owners(self):
        from wave_lint_lib import secrets_validators as sv
        from wave_lint_lib.betterleaks_worker import close_worker
        self.addCleanup(close_worker)
        for owner in ("indexer", "cli"):
            for rel in (scan_secrets._DETECTION_RELPATHS[0],
                        scan_secrets._DETECTION_RELPATHS[-2],
                        ".wavefoundry/framework/scripts/wave_lint_lib/constants.py",
                        ".wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py"):
                with self.subTest(owner=owner, path=rel), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory).resolve()
                    _make_root(root)
                    (root / ".wavefoundry/framework/scan-rules.toml").write_text(
                        'wavefoundryProfile = "betterleaks-v2-8f376ff9"\n'
                        'prefilter = "false"\nfilter = "false"\n'
                        '[allowlist]\npaths = [\'^\\.wavefoundry/\', \'^docs/\']\n'
                        '[[rules]]\nid = "synthetic-probe"\nregex = "SYNTH_[0-9]{3}"\n')
                    subject = root / "unchanged.txt"
                    subject.write_text("SYNTH_001\n")
                    self._run_owner(owner, root)
                    ledger = root / _FINDINGS_RELPATH
                    rows = json.loads(ledger.read_text())
                    self.assertEqual(len(rows), 1)
                    rows[0].update(status="false-positive", override_reason="fixture disposition")
                    ledger.write_text(json.dumps(rows))
                    path = root / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"changed detection identity")
                    with patch.object(sv, "scan_file_raw", wraps=sv.scan_file_raw) as scanned:
                        result = self._run_owner(owner, root)
                    self.assertIn(subject, [call.args[0] for call in scanned.call_args_list])
                    self.assertTrue(result["rules_change_escalation"] if owner == "indexer"
                                    else result["escalated_to_full"])
                    current = json.loads(ledger.read_text())
                    self.assertEqual(current[0]["id"], rows[0]["id"])
                    self.assertEqual(current[0]["override_reason"], "fixture disposition")


class ShippedProfileUpgradeConsumers(unittest.TestCase):
    """The shipped 280-rule legacy baseline upgrades through both real caches."""

    _run_owner = ActualRulesChangeConsumers._run_owner

    def test_shipped_upgrade_finds_new_rule_and_preserves_triage(self):
        from wave_lint_lib.betterleaks_worker import close_worker
        self.addCleanup(close_worker)
        fixture_root = Path(__file__).parent / "fixtures/betterleaks"
        baseline = (fixture_root / "baseline.toml").read_bytes()
        shipped = (SCRIPTS_ROOT.parent / "scan-rules.toml").read_bytes()
        old_ids = {rule["id"] for rule in tomllib.loads(baseline.decode())["rules"]}
        new_ids = {rule["id"] for rule in tomllib.loads(shipped.decode())["rules"]}
        self.assertEqual((len(old_ids), len(new_ids)), (280, 474))
        self.assertNotIn("kimi-api-key", old_ids)
        self.assertIn("kimi-api-key", new_ids)
        samples = {}
        with gzip.open(fixture_root / "oracle.jsonl.gz", "rt", encoding="utf-8") as rows:
            for line in rows:
                row = json.loads(line)
                if (row.get("rule_id") in {"aws-access-token", "kimi-api-key"}
                        and row.get("label") == "positive" and row.get("findings")):
                    samples.setdefault(row["rule_id"], row["content"])
                if len(samples) == 2:
                    break
        self.assertEqual(set(samples), {"aws-access-token", "kimi-api-key"})
        for owner in ("indexer", "cli"):
            with self.subTest(owner=owner), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                _make_root(root)
                framework = root / ".wavefoundry/framework/scan-rules.toml"
                framework.write_bytes(baseline)
                (root / "docs/scan-rules.toml").write_text(
                    "[allowlist]\npaths = ['^\\.wavefoundry/', '^docs/']\n")
                for rel in ("prior-pending.env", "prior-classified.env"):
                    (root / rel).write_text(samples["aws-access-token"])
                subject = root / "unchanged-new-provider.env"
                subject.write_text(samples["kimi-api-key"])
                self._run_owner(owner, root)
                ledger = root / _FINDINGS_RELPATH
                initial = json.loads(ledger.read_text())
                self.assertFalse(any(row["rule_id"] == "kimi-api-key" for row in initial))
                retained = {}
                for rel, status in (("prior-pending.env", "pending"),
                                    ("prior-classified.env", "false-positive")):
                    entry = next(row for row in initial if row["file"] == rel and row["rule_id"] == "aws-access-token")
                    entry.update(status=status, history=[{"note": "pre-upgrade synthetic evidence"}])
                    if status == "false-positive":
                        entry.update(confirmations=[{"confirmed_by": "fixture reviewer"}],
                                     override_reason="Retain reviewed fixture classification")
                    retained[entry["id"]] = {key: entry[key] for key in (
                        "status", "history", "confirmations", "override_reason") if key in entry}
                ledger.write_text(json.dumps(initial))
                cached = self._run_owner(owner, root)
                self.assertTrue(cached["up_to_date"] if owner == "indexer" else cached["files_skipped"] >= 3)
                framework.write_bytes(shipped)
                result = self._run_owner(owner, root)
                current = json.loads(ledger.read_text())
                self.assertTrue(any(row["file"] == subject.name and row["rule_id"] == "kimi-api-key"
                                    for row in current), "new shipped rule must inspect already-cached unchanged source")
                for identity, fields in retained.items():
                    entry = next(row for row in current if row["id"] == identity)
                    self.assertEqual({key: entry[key] for key in fields}, fields)
                self.assertTrue(result["rules_change_escalation"] if owner == "indexer"
                                else result["escalated_to_full"])
                self.assertEqual(subject.read_text(), samples["kimi-api-key"])
                self.assertNotIn(samples["kimi-api-key"], ledger.read_text())


if __name__ == "__main__":
    unittest.main()
