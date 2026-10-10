"""Actual dirty-repository lint traces and bounded proof invalidation controls."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from advisory_lint_identity import INCREMENTAL_FULL_FALLBACK_FILES
import test_docs_lint as docs_fixture
from test_server_tools import load_server
from wave_lint_lib.wave_validators import _parse_change_records
import record_paths
import vocabulary_profile


class AdvisoryLintReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()
        cls.identity = sys.modules["advisory_lint_identity"]

    def setUp(self):
        self.srv._advisory_lint_proofs.clear()
        self.root = self.make_root()

    def make_root(self):
        root = docs_fixture.DocsLintFixtureTests().copy_fixture()
        self.addCleanup(shutil.rmtree, root)
        # Canonical fixture has two intentionally tolerated status-drift warnings.
        # Complete its admitted headers so full proof is wholly green, no skips.
        for wave in (root / record_paths.WAVES_ROOT).glob("*/" + vocabulary_profile.RECORD_FILENAME):
            for member in _parse_change_records(wave.read_text(), ""):
                doc = wave.parent / (member.record_id + ".md")
                if not doc.is_file():
                    doc.write_text(f"# Fixture change\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-10-09\n\n{vocabulary_profile.MEMBER_ID_LABEL}: `{member.record_id}`\n{vocabulary_profile.MEMBER_STATUS_LABEL}: `{member.status}`\n\n## Rationale\n\nFixture.\n\n## Requirements\n\n1. Fixture.\n\n## Scope\n\nFixture.\n\n## Acceptance Criteria\n\n- [x] AC-1: Fixture.\n\n## Tasks\n\n- [x] Fixture.\n\n## AC Priority\n\n| AC | Priority | Rationale |\n| --- | --- | --- |\n| AC-1 | required | Fixture. |\n")
                else:
                    doc.write_text(doc.read_text().replace("\n## ", f"\n{vocabulary_profile.MEMBER_STATUS_LABEL}: `{member.status}`\n\n## ", 1))
        for args in (("init", "-q"), ("add", "-A"), ("-c", "user.email=wave@test", "-c", "user.name=wave", "commit", "-qm", "fixture")):
            subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)
        return root

    def dirty(self, root=None, trigger="docs/workflow-config.json"):
        root = root or self.root
        target = root / trigger
        if target.exists():
            target.write_text(target.read_text() + "\n")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{}\n")

    def establish(self):
        self.dirty()
        result = self.srv.run_validate_changed(self.root)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["mode"], "full-fallback")
        self.assertIn(str(self.root.resolve()), self.srv._advisory_lint_proofs)
        return result

    def test_real_dirty_trace_reuses_all_three_triggers_and_catches_new_doc(self):
        original = self.srv._mcp_subprocess_run
        for trigger in INCREMENTAL_FULL_FALLBACK_FILES:
            root = self.make_root()
            self.dirty(root, trigger)
            with patch.object(self.srv, "_mcp_subprocess_run", wraps=original) as run:
                first = self.srv.run_validate_changed(root)
                second = self.srv.run_validate_changed(root)
                third = self.srv.run_validate_changed(root)
                self.assertTrue(first["passed"], first)
                self.assertTrue(second["passed"], second)
                self.assertEqual([first["mode"], second["mode"], third["mode"]], ["full-fallback", "incremental", "incremental"])
                self.assertEqual(run.call_count, 3)
                self.assertNotIn("--advisory-trigger-proof", run.call_args_list[0].args[0])
                self.assertIn("--advisory-trigger-proof", run.call_args_list[1].args[0])
                bad = root / "docs/references/new-invalid.md"
                bad.write_text("# Invalid\n\n[missing](absent.md)\n")
                invalid = self.srv.run_validate_changed(root)
                self.assertFalse(invalid["passed"], invalid)
                self.assertEqual(invalid["mode"], "incremental")
                self.assertTrue(any("new-invalid.md" in error for error in invalid["errors"]))

    def test_changed_trigger_missing_baseline_and_other_root_force_full(self):
        self.establish()
        other = self.make_root(); self.dirty(other)
        self.assertEqual(self.srv.run_validate_changed(other)["mode"], "full-fallback")
        self.dirty()
        self.assertEqual(self.srv.run_validate_changed(self.root)["mode"], "full-fallback")
        self.srv._advisory_lint_proofs.clear()
        self.assertEqual(self.srv.run_validate_changed(self.root)["mode"], "full-fallback")

    def test_rule_identity_uses_bytes_names_root_and_scanner_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules = Path(tmp) / "scripts"; rules.mkdir()
            (rules / "docs_lint.py").write_text("# rule\n")
            (rules / "rule.py").write_text("VALUE=1\n")
            baseline = self.identity.advisory_lint_identity(self.root, rules)
            self.assertIsNotNone(baseline)
            (rules / "rule.py").write_text("VALUE=2\n")
            self.assertNotEqual(baseline, self.identity.advisory_lint_identity(self.root, rules))
            (rules / "rule.py").write_text("VALUE=1\n")
            (rules / "new_rule.py").write_text("# added\n")
            self.assertNotEqual(baseline, self.identity.advisory_lint_identity(self.root, rules))
            (rules / "new_rule.py").unlink()
            (self.root / "docs/scan-rules.toml").write_text("# changed scanner rules\n")
            self.assertNotEqual(baseline, self.identity.advisory_lint_identity(self.root, rules))
            (self.root / "docs/scan-rules.toml").unlink()
            (rules / "rule.py").unlink(); (rules / "rule.py").symlink_to(rules / "docs_lint.py")
            self.assertIsNone(self.identity.advisory_lint_identity(self.root, rules))

    def test_cached_helper_source_mismatch_declines_proof(self):
        self.assertIsNotNone(self.srv._advisory_lint_snapshot(self.root))
        with patch("advisory_lint_identity._LOADED_SOURCE", b"different cached source"):
            self.assertIsNone(self.srv._advisory_lint_snapshot(self.root))
        with patch("advisory_lint_identity._LOADED_SOURCE_CURRENT", False):
            self.assertIsNone(self.srv._advisory_lint_snapshot(self.root))

    def test_version_and_template_seed_assets_invalidate_exact_proof(self):
        self.establish()
        framework = self.root / ".wavefoundry/framework"
        framework.mkdir(parents=True, exist_ok=True)
        version = framework / "VERSION"
        before = self.srv._advisory_lint_snapshot(self.root)
        version.write_text("9.9.9\n")
        self.assertNotEqual(before, self.srv._advisory_lint_snapshot(self.root))
        result = self.srv.run_validate_changed(self.root)
        self.assertEqual(result["mode"], "full-fallback")
        for directory in ("seeds", "install", "docs"):
            path = framework / directory / "new-rule-asset.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            before = self.srv._advisory_lint_snapshot(self.root)
            path.write_text("changed rule asset\n")
            self.assertNotEqual(before, self.srv._advisory_lint_snapshot(self.root))

    def test_special_large_linked_and_unreadable_inputs_decline_without_hang(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules = Path(tmp) / "scripts"; rules.mkdir()
            (rules / "docs_lint.py").write_text("# rule\n")
            trigger = self.root / INCREMENTAL_FULL_FALLBACK_FILES[0]
            original = trigger.read_bytes(); trigger.unlink()
            if hasattr(os, "mkfifo"):
                os.mkfifo(trigger)
                self.assertIsNone(self.identity.advisory_lint_identity(self.root, rules))
                trigger.unlink()
            trigger.write_bytes(b"x" * (9 * 1024 * 1024))
            self.assertIsNone(self.identity.advisory_lint_identity(self.root, rules))
            trigger.write_bytes(original)
            external = Path(tmp) / "foreign"; external.mkdir(); (external / "rule.py").write_text("# foreign rule\n")
            (rules / "linked").symlink_to(external, target_is_directory=True)
            self.assertIsNone(self.identity.advisory_lint_identity(self.root, rules))
            (rules / "linked").unlink()
            with patch("advisory_lint_identity.os.walk", side_effect=PermissionError("unreadable rules")):
                self.assertIsNone(self.identity.advisory_lint_identity(self.root, rules))

    def test_failed_incomplete_and_moving_full_scan_never_mint_proof(self):
        self.dirty()
        for result in (
            subprocess.CompletedProcess([], 1, "", "ERROR: failed\n"),
            subprocess.CompletedProcess([], 0, "docs-lint: ok\n", ""),
            subprocess.CompletedProcess([], 0, "docs-lint: scope full\ndocs-lint: ok\n", "WARNING: doc skipped\n"),
        ):
            with patch.object(self.srv, "_mcp_subprocess_run", return_value=result):
                self.srv.run_validate_changed(self.root)
            self.assertNotIn(str(self.root.resolve()), self.srv._advisory_lint_proofs)
        original = self.srv._mcp_subprocess_run
        def moved(*args, **kwargs):
            result = original(*args, **kwargs)
            self.dirty()
            return result
        with patch.object(self.srv, "_mcp_subprocess_run", side_effect=moved):
            result = self.srv.run_validate_changed(self.root)
        self.assertFalse(result["passed"], result)
        self.assertIn("moved during validation", result["output"])
        self.assertNotIn(str(self.root.resolve()), self.srv._advisory_lint_proofs)
        # Explicit full scans also cannot mint proof from moving inputs, even
        # though their already-completed validation verdict remains observable.
        with patch.object(self.srv, "_mcp_subprocess_run", side_effect=moved):
            self.srv.run_validate(self.root)
        self.assertNotIn(str(self.root.resolve()), self.srv._advisory_lint_proofs)

    def test_child_rechecks_proof_and_refuses_race_under_hook_bound(self):
        self.establish()
        original = self.srv._mcp_subprocess_run
        def moved(*args, **kwargs):
            self.dirty()
            return original(*args, **kwargs)
        with patch.object(self.srv, "_mcp_subprocess_run", side_effect=moved) as run:
            result = self.srv.run_validate_changed(self.root)
        self.assertFalse(result["passed"], result)
        self.assertEqual(result["mode"], "incremental")
        self.assertNotIn("docs-lint: scope full", result["output"])
        self.assertIn("retry full validation", result["output"])
        self.assertIn("--advisory-incremental-only", run.call_args.args[0])

    def test_unpredicted_new_trigger_does_not_start_full_under_hook_bound(self):
        # The scope predictor sees no trigger, then another writer changes one.
        def race(_root):
            self.dirty()
            return False
        with patch.object(self.srv, "_predict_incremental_full_fallback", side_effect=race):
            result = self.srv.run_validate_changed(self.root)
        self.assertFalse(result["passed"], result)
        self.assertEqual(result["mode"], "incremental")
        self.assertIn("trigger appeared after scope prediction", result["output"])
        self.assertNotIn("docs-lint: scope full", result["output"])

    def test_hard_gate_always_spawns_fresh_full_after_reusable_proof(self):
        self.establish()
        original = self.srv._mcp_subprocess_run
        with patch.object(self.srv, "_mcp_subprocess_run", wraps=original) as run:
            full = self.srv.run_validate(self.root)
        self.assertTrue(full["passed"], full)
        self.assertEqual(run.call_count, 1)
        self.assertNotIn("--changed", run.call_args.args[0])
        self.assertNotIn("--advisory-trigger-proof", run.call_args.args[0])

    def test_timeout_and_non_git_skip_do_not_mint_proof(self):
        self.dirty()
        with patch.object(self.srv, "_mcp_subprocess_run", side_effect=subprocess.TimeoutExpired("lint", 9)):
            result = self.srv.run_validate_changed(self.root)
        self.assertFalse(result["passed"])
        self.assertEqual(result["mode"], "full-fallback")
        self.assertIn("full_scan_timeout_seconds", result["output"])
        self.assertFalse(self.srv._advisory_lint_proofs)
        shutil.rmtree(self.root / ".git")
        skipped = self.srv.run_validate_changed(self.root)
        self.assertEqual(skipped["mode"], "skipped")
        self.assertIn("docs-lint: skipped", skipped["output"])
        self.assertFalse(self.srv._advisory_lint_proofs)

    def test_proof_cache_has_one_entry_per_root_and_finite_eviction(self):
        green = {"passed": True, "errors": [], "warnings": [], "output": "docs-lint: scope full\ndocs-lint: ok\n"}
        with patch.object(self.srv, "_advisory_lint_snapshot", return_value="identity"):
            for number in range(self.srv._ADVISORY_LINT_PROOF_CAP + 2):
                self.srv._remember_advisory_lint_proof(self.root / str(number), "identity", green)
            self.assertEqual(len(self.srv._advisory_lint_proofs), self.srv._ADVISORY_LINT_PROOF_CAP)
            self.assertNotIn(str((self.root / "0").resolve()), self.srv._advisory_lint_proofs)
            self.srv._remember_advisory_lint_proof(self.root / "2", "identity", green)
            self.assertEqual(len(self.srv._advisory_lint_proofs), self.srv._ADVISORY_LINT_PROOF_CAP)

    def test_no_proof_sidecar_and_same_invalid_doc_diagnostics_as_full(self):
        self.establish()
        before = {path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file()}
        for _ in range(2):
            self.assertEqual(self.srv.run_validate_changed(self.root)["mode"], "incremental")
        after = {path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        invalid = self.root / "docs/references/bad.md"
        invalid.write_text("# Invalid\n\n[bad](absent.md)\n")
        advisory = self.srv.run_validate_changed(self.root)
        full = self.srv.run_validate(self.root)
        self.assertFalse(advisory["passed"])
        self.assertFalse(full["passed"])
        self.assertEqual(sorted(advisory["errors"]), sorted(full["errors"]))


if __name__ == "__main__":
    unittest.main()
