"""Drive the operator-selected lane through the tools a target repository serves."""
from __future__ import annotations

import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from declaration_support import RecordingFastMCP
from server_tools_support import (
    _make_repo, close_container, close_member, create_container, declared_wave_doc_gates,
    integrity_checks, load_server,
)
import record_paths
import vocabulary_profile as vocab
from test_lifecycle_golden import _change_doc, _stub_garden, _stub_validate, _write_config, _WAVE_REVIEW_CONFIG


class SmallChangeLifecycleTests(unittest.TestCase):
    source = "src/internal/summary.py"
    change_id = "1200b-ref summary"

    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = _make_repo(Path(temp.name).resolve(), {
            self.source: "def count(rows):\n    return len(tuple(rows))\n",
            "src/api/result.py": "from src.internal.summary import count\n\n"
                                 "def result(rows):\n    return {'count': count(rows)}\n",
            ".gitignore": ".wavefoundry/cache/\n.wavefoundry/index/\n.wavefoundry/work/\n"
                          ".wavefoundry/locks/\n.wavefoundry/logs/\n*.lock\n"
                          ".wavefoundry/framework/test-cache.json\n__pycache__/\n",
        })
        _write_config(self.root, _WAVE_REVIEW_CONFIG)
        scripts = self.root / ".wavefoundry/framework/scripts"
        scripts.mkdir(parents=True)
        shutil.copyfile(Path(__file__).resolve().parents[2] / "install/install-log.template.md",
                        self.root / ".wavefoundry/install-log.md")
        self.runner = scripts / "run_tests.py"
        shutil.copyfile(Path(__file__).resolve().parents[1] / "run_tests.py", self.runner)

        gates = declared_wave_doc_gates(self.server, {
            "run_validate": _stub_validate, "run_garden": _stub_garden,
            "_run_post_write_lint": lambda *args, **kwargs: {"mode": "fixture"},
            "_trigger_background_index_refresh_for_paths": lambda *args, **kwargs: {},
        })
        gates.__enter__()
        self.addCleanup(gates.__exit__, None, None, None)
        telemetry = MagicMock()
        telemetry.focus = SimpleNamespace(wave_id="", stage="general")
        telemetry.record_workflow.return_value = {}
        handler = SimpleNamespace(root=self.root, cache=None, telemetry=telemetry)
        surface = RecordingFastMCP()
        self.server.register_mcp_surface(surface, lambda: handler)
        self.tools = surface._tool_manager._tools
        created = create_container(self.call, self.root, "internal-summary", mode="create")
        self.require_ok(created)
        self.wave_id = created["data"]["wave_id"]
        self.wave_md = self.root / created["data"]["path"]
        roots = record_paths.load_record_roots(self.root)
        roots.plans.mkdir(parents=True, exist_ok=True)
        plan = roots.plans / f"{self.change_id}.md"
        body = _change_doc(self.change_id)
        header = f"{vocab.MEMBER_ID_LABEL}: `{self.change_id}`\n{vocab.MEMBER_STATUS_LABEL}: `planned`\nStatus: planned"
        plan.write_text(body.replace("\n\n", f"\n\n{header}\n\n", 1), encoding="utf-8")
        self.git("init", "--quiet")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Fixture baseline")

    def git(self, *args):
        return subprocess.run(
            ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
             "-c", "commit.gpgsign=false", "-c", "core.hooksPath=unused-hooks", *args],
            cwd=self.root, check=True, capture_output=True, text=True,
        ).stdout.strip()

    def call(self, name, **arguments):
        return self.tools[name].fn(**arguments)

    def wave(self, name, **arguments):
        return self.call(name, wave_id=self.wave_id, **arguments)

    def require_ok(self, result):
        self.assertIn(result["status"], ("ok", "dry_run"), result.get("diagnostics"))
        return result["data"]

    def admit(self, *, path=None, selected=True, mode="create"):
        selection = {}
        if selected:
            selection["small_change"] = {
                "operator_direction": "Use small review for the internal summary change.",
                "intended_diff": "Simplify the internal count helper.",
                "paths": [path or self.source],
            }
        return self.require_ok(self.wave("wf_add_spec", spec_id=self.change_id, mode=mode, **selection))

    def record_run(self, kind):
        self.require_ok(self.wave("wf_review_event", event="run", actor="code-reviewer",
                                  context_id="fixture-run-" + kind, run_kind=kind, mode="create",
                                  fresh_context=True, independent=True))

    def approval(self, phase, *, key="code-reviewer", digest=None, context="", mode="create"):
        operator = key == "operator-signoff"
        evidence = {"observed": "Verified the specified fixture inputs.", "artifact_or_test_id": self.id()}
        if not operator:
            evidence["small_change_impact"] = "internal"
        if digest is not None:
            evidence["small_change_content_digest"] = digest
        return self.wave("wf_review_event", event="approval", actor="operator" if operator else key,
                         context_id=f"fixture-{phase}-{key}-{context}", mode=mode,
                         signoff_key=key, approval_phase=phase, fresh_context=True, independent=True,
                         evidence=evidence, integrity_checks=None if operator else integrity_checks())

    def open_small(self):
        preview = self.admit(mode="dry_run")["small_change"]
        self.assertTrue(preview["eligible"], preview)
        self.assertNotIn("small-change-selection:", self.wave_md.read_text())
        actual = self.admit()["small_change"]
        self.assertEqual(preview["selection"], actual["selection"])
        self.assertEqual(self.git("rev-parse", "HEAD"), actual["selection"]["baseline"])
        self.assertEqual(actual["selection"], self.admit()["small_change"]["selection"])
        before = self.wave("wf_prepare_wave", mode="ready")
        self.assertEqual(before["status"], "error", before)
        self.assertIn("code-reviewer", json.dumps(before["diagnostics"]))
        refused = self.wave("wf_implement_wave", mode="create")
        self.assertEqual(refused["status"], "error", refused)
        self.record_run("readiness")
        self.require_ok(self.approval("readiness"))
        ready = self.require_ok(self.wave("wf_prepare_wave", mode="ready"))
        self.assertEqual(ready["small_change"]["required_readiness"], ["code-reviewer"])
        self.assertEqual(set(ready["small_change"]["required_delivery"]), {"code-reviewer", "operator-signoff"})
        opened = self.require_ok(self.wave("wf_implement_wave", mode="create"))
        self.assertTrue(opened["transitioned_to_implementing"])

        # The implementer updates member status and the source during the open wave.
        member = self.wave_md.parent / f"{self.change_id}.md"
        for path in (self.wave_md, member):
            text = path.read_text()
            old = f"{vocab.MEMBER_STATUS_LABEL}: `planned`"
            self.assertIn(old, text)
            updated = text.replace(old, f"{vocab.MEMBER_STATUS_LABEL}: `implemented`", 1)
            if path == member:
                updated = updated.replace("Status: planned", "Status: implemented", 1)
            path.write_text(updated, encoding="utf-8")
        (self.root / self.source).write_text("def count(rows):\n    return len(rows)\n", encoding="utf-8")
        self.record_run("initial_delivery")

    def review(self):
        return self.wave("wf_review_wave", phase="implementation")

    def record_finding(self, *, public):
        evidence = {
            "proposition": "The returned count matches the declared numeric result.",
            "failure_condition": "An input of two rows yields a nonnumeric count.",
            "command_or_fixture": self.id(),
            "public_path": "src.api.result.result" if public else "src.internal.summary.count",
            "expected": "A numeric count.", "observed": "The fixture returned a string count.",
            "artifact_or_test_id": self.source, "known_bad_detection_method": "Compare integer 2 to string '2'.",
            "limitations": "This fixture uses a local two-row sample.",
            "safety_and_authorization": "The fixture runs in a temporary Git repository.",
            "disposition_rationale": "The reviewer requires repair before closure.",
        }
        judgment = {
            "validation_status": "real", "scope_relation": "admitted", "introduced_or_worsened_by_wave": True,
            "contract_relevance": "public_contract" if public else "required_ac", "observable_impact": "material",
            "supported_reachability": True, "attacker_reachability": False,
            "authority_domain": "none", "authority_delta": "none", "containment": "none",
        }
        self.require_ok(self.wave(
            "wf_review_event", event="finding", run_kind="initial_delivery", finding_id="wrong-count",
            actor="code-reviewer", context_id="inspect-return-shape", source_lanes=["code-reviewer"],
            blocking_required_lanes=["code-reviewer"], approval_recheck_lanes=["code-reviewer"],
            review_boundaries_changed=["contract_or_required_ac_semantics_changed"] if public else [],
            judgment=judgment, evidence=evidence, integrity_checks=integrity_checks(),
            fresh_context=True, independent=True, mode="create",
        ))

    def close_change(self, mode="dry_run"):
        return close_member(self.call, self.root, self.wave_id, self.change_id, mode=mode)

    def close_wave(self, mode="dry_run"):
        return close_container(self.call, self.root, self.wave_id, mode=mode)

    def write_green_receipt(self):
        runner = self.server.lifecycle_gate_support._load_framework_test_runner(self.runner)
        runner._write_cache(runner._hash_inputs(), 1)

    def test_selected_review_checks_revised_contents_and_retains_wave_close_guards(self):
        self.open_small()
        self.require_ok(self.wave("wf_pause_wave", mode="create"))
        resumed = self.require_ok(self.wave("wf_reopen_wave", purpose="review"))
        self.assertEqual(resumed["small_change"]["effective_lane"], "small")
        pending = self.review()
        first = pending["data"]["small_change"]["content_digest"]
        self.assertTrue(first, pending)
        self.assertEqual(self.close_change()["status"], "error")
        self.require_ok(self.approval("delivery", digest=first))
        self.require_ok(self.close_change())

        with (self.root / self.source).open("a", encoding="utf-8") as handle:
            handle.write("# Same file, revised after review.\n")
        stale = self.review()
        current = stale["data"]["small_change"]["content_digest"]
        self.assertNotEqual(first, current)
        for result in (stale, self.close_change(), self.close_wave()):
            self.assertEqual(result["status"], "error", result)
            self.assertIn("code-reviewer", json.dumps(result["diagnostics"]))
        replay = self.approval("delivery", digest=first, context="old-digest")
        self.assertEqual(replay["status"], "error", replay)
        self.require_ok(self.approval("delivery", digest=current, context="revised"))
        self.require_ok(self.close_change(mode="create"))
        unsigned = self.close_wave()
        self.assertIn("missing_operator_signoff", [d["code"] for d in unsigned["diagnostics"]])
        self.require_ok(self.approval("delivery", key="operator-signoff"))
        missing_receipt = self.close_wave()
        self.assertIn("framework_test_receipt_not_proven", [d["code"] for d in missing_receipt["diagnostics"]])
        self.write_green_receipt()
        self.require_ok(self.close_wave(mode="create"))
        rows = [json.loads(line) for line in (self.wave_md.parent / "events.jsonl").read_text().splitlines()]
        approvals = [r for r in rows if r.get("claim_kind") == "approval"]
        self.assertEqual({r["event_identity"]["signoff_key"] for r in approvals}, {"code-reviewer", "operator-signoff"})
        self.assertEqual([r["small_change_content_digest"] for r in approvals if r.get("small_change_content_digest")],
                         [first, current])

    def test_unselected_admission_keeps_the_ordinary_readiness_council(self):
        self.admit(selected=False)
        prepared = self.wave("wf_prepare_wave", mode="ready")
        self.assertIn("missing_wave_council_signoff", [d["code"] for d in prepared["diagnostics"]])
        self.assertNotIn("small-change-selection:", self.wave_md.read_text())

    def test_protected_file_explains_ordinary_review_at_admission(self):
        small = self.admit(path="src/api/result.py")["small_change"]
        self.assertFalse(small["eligible"])
        self.assertIn("src/api/result.py", " ".join(small["reasons"]))
        prepared = self.wave("wf_prepare_wave", mode="ready")
        self.assertIn("missing_wave_council_signoff", [d["code"] for d in prepared["diagnostics"]])

    def test_requested_specialist_is_part_of_the_ordinary_roster(self):
        self.admit()
        original = self.wave_md.read_text()
        marker = "- Requested review lanes: none"
        self.assertIn(marker, original)
        self.wave_md.write_text(original.replace(marker, "- Requested review lanes: qa-reviewer", 1))
        prepared = self.wave("wf_prepare_wave", mode="ready")
        lane = prepared["data"]["small_change"]
        self.assertEqual(lane["effective_lane"], "ordinary")
        self.assertIn("qa-reviewer", " ".join(lane["reasons"]))
        self.assertIn("qa-reviewer", lane["required_readiness"])

    def test_second_admission_permanently_replaces_the_selected_roster(self):
        self.admit()
        second = "1200c-ref measurement"
        roots = record_paths.load_record_roots(self.root)
        (roots.plans / f"{second}.md").write_text(_change_doc(second), encoding="utf-8")
        self.require_ok(self.wave("wf_add_spec", spec_id=second, mode="create"))
        result = self.wave("wf_prepare_wave", mode="ready")
        self.assertEqual(result["data"]["small_change"]["effective_lane"], "ordinary")
        self.require_ok(self.wave("wf_remove_spec", spec_id=second, mode="create"))
        after_removal = self.wave("wf_prepare_wave", mode="ready")
        self.assertIn("missing_wave_council_signoff", [d["code"] for d in after_removal["diagnostics"]])
        self.assertEqual(after_removal["data"]["small_change"]["effective_lane"], "ordinary")

    def test_expanded_scope_cannot_reuse_narrow_approval_at_either_close(self):
        self.open_small()
        digest = self.review()["data"]["small_change"]["content_digest"]
        self.require_ok(self.approval("delivery", digest=digest))
        self.require_ok(self.close_change())
        extra = self.root / "src/internal/another.py"
        extra.write_text("COUNT = 2\n", encoding="utf-8")
        for result in (self.review(), self.close_change(), self.close_wave()):
            self.assertEqual(result["status"], "error", result)
            self.assertIn("another.py", json.dumps(result))
        self.wave("wf_prepare_wave", mode="ready")
        extra.unlink()
        for result in (self.review(), self.close_change(), self.close_wave()):
            self.assertEqual(result["status"], "error", result)
            self.assertIn("ordinary", json.dumps(result).lower())

    def test_contract_escalation_survives_revert_and_pause(self):
        self.open_small()
        source = self.root / self.source
        reviewed = source.read_bytes()
        self.require_ok(self.approval("delivery", digest=self.review()["data"]["small_change"]["content_digest"]))
        probe = "import json; from src.api.result import result; print(json.dumps(result([1, 2])))"
        def public_result():
            out = subprocess.run([sys.executable, "-B", "-c", probe], cwd=self.root,
                                 capture_output=True, text=True, check=True)
            return json.loads(out.stdout)
        self.assertEqual(public_result(), {"count": 2})
        source.write_text("def count(rows):\n    return str(len(rows))\n", encoding="utf-8")
        self.assertEqual(public_result(), {"count": "2"})
        self.record_finding(public=True)
        source.write_bytes(reviewed)
        self.assertEqual(public_result(), {"count": 2})
        for result in (self.review(), self.close_change(), self.close_wave()):
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["data"]["small_change"]["effective_lane"], "ordinary")
            self.assertIn("council", json.dumps(result["diagnostics"]).lower())
        self.require_ok(self.wave("wf_pause_wave", mode="create"))
        resume = self.wave("wf_reopen_wave", purpose="review")
        self.assertEqual(resume["status"], "error", resume)
        self.assertIn("council", json.dumps(resume["diagnostics"]).lower())

    def test_open_finding_blocks_otherwise_qualified_closure(self):
        self.open_small()
        source = self.root / self.source
        source.write_text("def count(rows):\n    return str(len(rows))\n", encoding="utf-8")
        self.assertEqual(runpy.run_path(str(source))["count"]([1, 2]), "2")
        self.require_ok(self.approval("delivery", digest=self.review()["data"]["small_change"]["content_digest"]))
        self.require_ok(self.approval("delivery", key="operator-signoff"))
        self.write_green_receipt()
        self.require_ok(self.close_change())
        self.require_ok(self.close_wave())
        self.record_finding(public=False)
        for result in (self.close_change(), self.close_wave()):
            self.assertEqual(result["status"], "error", result)
            self.assertEqual(result["data"]["small_change"]["effective_lane"], "small")
            self.assertIn("code-reviewer", json.dumps(result["diagnostics"]))

    def fully_approve_small(self):
        self.open_small()
        digest = self.review()["data"]["small_change"]["content_digest"]
        self.require_ok(self.approval("delivery", digest=digest))
        self.require_ok(self.approval("delivery", key="operator-signoff"))
        self.write_green_receipt()
        self.require_ok(self.close_change())
        self.require_ok(self.close_wave())
        return digest

    def test_review_preserves_observed_expansion_after_restore_and_pause(self):
        self.fully_approve_small()
        extra = self.root / "src/internal/another.py"
        extra.write_text("COUNT = 2\n", encoding="utf-8")
        observed = self.review()
        self.assertEqual(observed["status"], "error")
        self.assertEqual(observed["data"]["small_change"]["effective_lane"], "ordinary")
        self.assertIn("src/internal/another.py", " ".join(observed["data"]["small_change"]["reasons"]))
        extra.unlink()

        # No intervening Prepare, approval or finding records the change of scope.
        def check_ordinary(result):
            self.assertEqual(result["status"], "error", result.get("diagnostics"))
            self.assertEqual(result["data"]["small_change"]["effective_lane"], "ordinary")
            self.assertIn("council", json.dumps(result["diagnostics"]).lower())

        for close in (self.close_change, self.close_wave):
            with self.subTest(close=close.__name__, stage="restored"):
                check_ordinary(close())
        self.require_ok(self.wave("wf_pause_wave", mode="create"))
        check_ordinary(self.wave("wf_reopen_wave", purpose="review"))
        for close in (self.close_change, self.close_wave):
            with self.subTest(close=close.__name__, stage="resume withheld"):
                check_ordinary(close())

    def test_identical_file_replacement_requires_fresh_delivery_approval(self):
        prior = self.fully_approve_small()
        source = self.root / self.source
        replacement = source.with_suffix(".new")
        shutil.copy2(source, replacement)
        self.assertFalse(source.samefile(replacement))
        self.assertEqual(source.read_bytes(), replacement.read_bytes())
        self.assertEqual(source.stat().st_mode, replacement.stat().st_mode)
        replacement.replace(source)

        review = self.review()
        lane = review["data"]["small_change"]
        self.assertEqual(lane["effective_lane"], "small")
        self.assertNotEqual(prior, lane["content_digest"])
        for result in (review, self.close_change(), self.close_wave()):
            self.assertEqual(result["status"], "error", result.get("diagnostics"))
            self.assertIn("code-reviewer", json.dumps(result["diagnostics"]))
        self.require_ok(self.approval("delivery", digest=lane["content_digest"], context="replacement"))
        self.require_ok(self.close_change())
        self.require_ok(self.close_wave())
