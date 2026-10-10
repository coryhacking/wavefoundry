"""Declared council actor aliases: real profile loads, lifecycle replay and reload."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import vocabulary_profile as vp

SCRIPTS = Path(__file__).resolve().parents[1]
ALIAS = "retired-board-chair"

# The child loads actual copied declarations and producers. Fixture helpers
# stub only docs gardening/post-write lint; identity and policy checks are real.
_DRIVER = r'''
import importlib, json, re, sys, tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path.cwd() / "tests"))
from test_council_signoff_keys import LifecycleCompatibilityTests
from test_lifecycle_golden import _approval_evidence, _APPROVAL_INTEGRITY, _write_config
from test_review_evidence import RepairReverificationIndependenceTests
from server_tools_support import load_thin_runner
alias = "retired-board-chair"
case = LifecycleCompatibilityTests("runTest")
case.setUpClass()
case.setUp()
try:
    srv = case.srv
    subject = importlib.import_module("review_evidence")
    profile = importlib.import_module("vocabulary_profile")
    assert subject.LEGACY_COUNCIL_ACTORS.count(alias) == 1
    assert subject.COUNCIL_ACTORS.count(subject.COUNCIL_ACTOR) == 1
    assert subject.is_council_actor(alias)
    assert not subject.is_council_actor("undeclared-board-chair")
    assert subject.canonical_council_actor(alias) == subject.COUNCIL_ACTOR
    assert subject.LEGACY_COUNCIL_ACTORS[0] == subject.BUILTIN_LEGACY_COUNCIL_ACTORS[0]
    from test_distribution_seams import CouncilActorReadTests
    CouncilActorReadTests("test_distinctness_treats_both_names_as_one_actor").test_distinctness_treats_both_names_as_one_actor()
    key = subject.COUNCIL_READINESS_SIGNOFF_KEY
    root, wave_md, wave_id = case._readied("declared-alias", approvals=())
    assert case._event(root, wave_id, "run", subject.COUNCIL_ACTOR, "readiness-run",
                       mode="create", run_kind="readiness")["status"] == "ok"
    unwrapped = srv.wf_review_event_response.__wrapped__.__wrapped__
    builder_module = sys.modules[srv.build_identified_review_event.__module__]
    with patch.object(builder_module, "COUNCIL_ACTOR", alias):
        old = unwrapped(root, wave_id, "approval", alias, "history-context",
                        fresh_context=True, independent=True,
                        evidence=_approval_evidence(alias), integrity_checks=dict(_APPROVAL_INTEGRITY),
                        mode="create", signoff_key=key, approval_phase="readiness")
    assert old["status"] == "ok", old
    ledger_path = subject.review_event_path(wave_md)
    original = ledger_path.read_bytes()
    for actor in (alias, subject.COUNCIL_ACTOR):
        for mode in ("dry_run", "create"):
            retry = srv.wf_review_event_response(root, wave_id, "approval", actor, "history-context",
                fresh_context=True, independent=True, evidence=_approval_evidence(alias),
                integrity_checks=dict(_APPROVAL_INTEGRITY), mode=mode,
                signoff_key=key, approval_phase="readiness")
            assert retry["status"] in ("ok", "dry_run"), retry
            assert ledger_path.read_bytes() == original
    altered = _approval_evidence(alias)
    altered["observed"] = "different fixture"
    conflict = srv.wf_review_event_response(root, wave_id, "approval", alias, "history-context",
                fresh_context=True, independent=True, evidence=altered,
                integrity_checks=dict(_APPROVAL_INTEGRITY), mode="create",
                signoff_key=key, approval_phase="readiness")
    assert conflict["status"] == "error" and "review_event_identity_conflict" in json.dumps(conflict)
    assert ledger_path.read_bytes() == original
    fresh = case._event(root, wave_id, "approval", alias, "fresh-context", mode="create",
                        signoff_key=key, approval_phase="readiness")
    assert fresh["status"] == "ok", fresh
    rows, errors = subject.read_review_event_ledger(wave_md)
    assert not errors
    approvals = [r for r in rows if r.get("claim_kind") == "approval"]
    assert approvals[-1]["verification_context"]["actor"] == subject.COUNCIL_ACTOR
    assert approvals[-1][subject.EVENT_IDENTITY_FIELD]["actor"] == subject.COUNCIL_ACTOR
    for lane, actor in ((key, "undeclared-board-chair"), ("code-reviewer", alias), ("operator-signoff", alias)):
        refused = case._event(root, wave_id, "approval", actor, "wrong-" + lane,
                            mode="create", signoff_key=lane, approval_phase="readiness" if lane == key else "delivery")
        assert refused["status"] == "error", refused
    repair = RepairReverificationIndependenceTests("runTest")
    chain = repair._chain_through_repair_start(repair_actor=alias, repair_context="repair-alias")
    for actor in (alias, subject.COUNCIL_ACTOR):
        added, errors = subject.build_compact_review_event(chain,
            repair._clearing_reverification(actor=actor, context_id="fresh-verifier"))
        assert not added and "reverification_actor_not_distinct" in "\n".join(errors), errors
    added, errors = subject.build_compact_review_event(chain,
            repair._clearing_reverification(actor="qa-reviewer", context_id="fresh-independent"))
    assert added and not errors, errors
    base = dict(case.CONFIG)
    text = wave_md.read_text()
    for config, wave in (
        ({**base, "required_review_lanes": [alias]}, text),
        ({**base, "phase_gates": {"prepare": {"required_lanes": [alias]}}}, text),
        ({**base, "phase_gates": {"close": {"required_lanes": [alias]}}}, text),
        (base, re.sub(r"(?m)^- Requested review lanes:.*$", "- Requested review lanes: " + alias, text)),
    ):
        _write_config(root, config)
        state, errors = srv._prepare_policy_state(root, wave_md, wave, [], {})
        assert state is None and "EXTRA_LEGACY_COUNCIL_ACTORS" in "\n".join(errors), (config, wave[-200:], errors)
    _write_config(root, {**base, "required_review_lanes": ["custom-auditor"]})
    state, errors = srv._prepare_policy_state(root, wave_md, text, [], {})
    assert state is not None and not errors, errors
    policy = importlib.import_module("review_policy")
    assert policy._DIGEST_COUNCIL_MODERATOR_SPELLING[subject.COUNCIL_ACTOR] == subject.BUILTIN_LEGACY_COUNCIL_ACTORS[0]
    assert alias not in policy._DIGEST_COUNCIL_MODERATOR_SPELLING.values()
    if sys.argv[1] == "reload":
        runner = load_thin_runner()
        runner.build_server(root)
        source = Path("vocabulary_profile.py")
        before = source.read_text()
        text, count = re.subn(r"(?m)^(EXTRA_LEGACY_COUNCIL_ACTORS(?:[ \t]*:[^=\r\n]*)?[ \t]*=[ \t]*)[^\r\n]*(?=\r?$)",
            lambda m: m.group(1) + repr(("replacement-board-chair",)), before)
        assert count == 1
        source.write_text(text)
        try:
            result = runner.perform_mcp_reload()
            assert result["status"] == "ok", result
            updated = importlib.import_module("review_evidence")
            assert updated.is_council_actor("replacement-board-chair")
            assert not updated.is_council_actor(alias)
            handler = sys.modules["server_impl"]
            # The reloaded implementation binds the same new merged actor tuple.
            assert "replacement-board-chair" in handler.LEGACY_COUNCIL_ACTORS
            assert alias not in handler.LEGACY_COUNCIL_ACTORS
        finally:
            runner._get_handler().close()
    print(json.dumps({"status": "ok", "mode": sys.argv[1], "history_bytes_preserved": True}))
finally:
    case.doCleanups()
'''


class LegacyActorDeclarationTests(unittest.TestCase):
    def test_invalid_declarations_and_reserved_authority_tokens(self):
        for value in ([], "retired", (1,), ("",), ("Upper-case",), ("bad--token",),
                      ("bad\n",), ("operator",), ("operator-signoff",), ("qa-reviewer",),
                      ("code-reviewer",), ("architecture-reviewer",), ("docs-contract-reviewer",),
                      ("release-reviewer",), ("performance-reviewer",), ("security-reviewer",)):
            with self.subTest(value=value):
                self.assertTrue(vp.legacy_council_actor_errors(value))
        self.assertEqual(vp.legacy_council_actor_errors((ALIAS, ALIAS)), [])
        self.assertTrue(vp.legacy_council_actor_errors((ALIAS,), reviewer_roles=(ALIAS,)))
        self.assertEqual(vp.legacy_council_actor_errors((ALIAS,), reviewer_roles=("other-reviewer",)), [])

    def test_validation_at_real_module_import(self):
        source = (SCRIPTS / "vocabulary_profile.py").read_text()
        import re
        for value in (("operator",), [ALIAS], ("bad token",)):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp:
                replaced, count = re.subn(r"(?m)^(EXTRA_LEGACY_COUNCIL_ACTORS[^=\n]*=)[^\n]*$",
                                         lambda m: m.group(1) + " " + repr(value), source)
                self.assertEqual(count, 1)
                path = Path(temp) / "profile.py"
                path.write_text(replaced)
                spec = importlib.util.spec_from_file_location("_invalid_actor_profile", path)
                module = importlib.util.module_from_spec(spec)
                with self.assertRaisesRegex(ValueError, "EXTRA_LEGACY_COUNCIL_ACTORS"):
                    spec.loader.exec_module(module)

    def _driver(self, mode):
        with tempfile.TemporaryDirectory() as temp:
            scripts = Path(temp) / "scripts"
            shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            from record_layout_support import apply_profile
            import review_evidence
            builtin = review_evidence.BUILTIN_LEGACY_COUNCIL_ACTORS[0]
            apply_profile(scripts, {"modules": {"vocabulary_profile": {
                "EXTRA_LEGACY_COUNCIL_ACTORS": [builtin, builtin, ALIAS, ALIAS]}}})
            result = subprocess.run([sys.executable, "-B", "-c", _DRIVER, mode], cwd=scripts,
                env=dict(os.environ, PYTHONPATH=str(scripts), PYTHONDONTWRITEBYTECODE="1"),
                capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-6000:])
        self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1]),
                         {"status": "ok", "mode": mode, "history_bytes_preserved": True})

    def test_declared_alias_lifecycle_replay_authority_and_runtime_role_collisions(self):
        self._driver("lifecycle")

    def test_real_mcp_reload_observes_changed_actor_declaration(self):
        self._driver("reload")


if __name__ == "__main__":
    unittest.main()
