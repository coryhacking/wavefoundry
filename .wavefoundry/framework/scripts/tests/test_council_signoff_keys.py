"""Wave 1zyb4 (1zxnx): tier-neutral council signoff keys.

New approvals carry ``council-readiness`` / ``council-delivery``. The earlier
spellings ``wave-council-readiness`` / ``wave-council-delivery`` are history:
they stay readable forever (ledgers and wave records are never rewritten), and
they stay accepted as tool input and config values during the alias period.
The fixtures below that write the earlier spelling model those legacy ledgers.
"""
from __future__ import annotations

import copy
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import review_evidence as subject
import review_policy
import vocabulary_profile
from server_tools_support import load_server
from test_lifecycle_golden import (
    _APPROVAL_INTEGRITY,
    _WAVE_REVIEW_CONFIG,
    _approval_evidence,
    _build_one,
    _make_repo,
    _stub_garden,
    _stub_validate,
    _write_config,
    capture,
    seed_state,
)
from test_review_evidence import derive, executable_evidence, synthesis

OLD_READINESS = "wave-council-readiness"
OLD_DELIVERY = "wave-council-delivery"
NEW_READINESS = "council-readiness"
NEW_DELIVERY = "council-delivery"


def _legacy(text: str, *, keys: tuple[str, ...] = (NEW_READINESS, NEW_DELIVERY)) -> str:
    """Spell the named current keys the earlier way (models a legacy ledger)."""
    for key in keys:
        text = re.sub(rf"(?<!wave-){re.escape(key)}", f"wave-{key}", text)
    return text


def _current(text: str) -> str:
    return text.replace(OLD_READINESS, NEW_READINESS).replace(OLD_DELIVERY, NEW_DELIVERY)


def _approval(key: str, evidence_id: str | None = None, **overrides: object) -> dict[str, object]:
    actor = overrides.pop("actor", None) or (
        "wave-council" if subject.is_council_signoff_key(key) else key)
    return executable_evidence(
        evidence_id or f"approval-{key}",
        f"approval:{key}",
        claim_kind="approval",
        actor=actor,
        required_for_approval=True,
        **overrides,
    )


class CanonicalKeyTests(unittest.TestCase):
    """AC-1: one mapping every reader uses."""

    def test_canonical_signoff_key(self) -> None:
        self.assertEqual(subject.canonical_signoff_key(OLD_READINESS), NEW_READINESS)
        self.assertEqual(subject.canonical_signoff_key(OLD_DELIVERY), NEW_DELIVERY)
        for unchanged in (NEW_READINESS, NEW_DELIVERY, "operator-signoff",
                          "code-reviewer", "qa-reviewer", "wave-council-x", "wave-council"):
            with self.subTest(key=unchanged):
                self.assertEqual(subject.canonical_signoff_key(unchanged), unchanged)

    def test_is_council_signoff_key(self) -> None:
        for key in (OLD_READINESS, OLD_DELIVERY, NEW_READINESS, NEW_DELIVERY, "wave-council-x"):
            with self.subTest(key=key):
                self.assertTrue(subject.is_council_signoff_key(key))
        for key in ("council-review", "code-reviewer", "operator-signoff", "wave-council", ""):
            with self.subTest(key=key):
                self.assertFalse(subject.is_council_signoff_key(key))

    def test_claim_ids_canonicalize_only_approval_keys(self) -> None:
        self.assertEqual(
            subject.canonical_approval_claim_id(f"approval:{OLD_READINESS}"),
            f"approval:{NEW_READINESS}",
        )
        self.assertEqual(subject.canonical_approval_claim_id("finding:x"), "finding:x")

    def test_digest_spelling_mirrors_the_alias_map(self) -> None:
        self.assertEqual(
            review_policy._DIGEST_COUNCIL_SIGNOFF_SPELLING,
            {new: old for old, new in subject.LEGACY_COUNCIL_SIGNOFF_KEYS.items()},
        )


class DigestInputTests(unittest.TestCase):
    """AC-11: a key spelling never rotates a receipt."""

    OLD = {"enabled": True, "delivery_mode": "universal", "phases": {
        "prepare": {"signoff_key": OLD_READINESS, "moderator_role": "wave-council"},
        "review": {"signoff_key": OLD_DELIVERY, "moderator_role": "wave-council"}}}
    NO_PHASES = {"enabled": True, "delivery_mode": "targeted"}
    KWARGS = dict(
        project_lanes=["code-reviewer"],
        review_policies={},
        changes=[("1aaaa-enh pinned", "enh", b"# Pinned\n")],
        requested_lanes=[],
    )
    # Computed by the pre-change ``policy_input_snapshot`` (which hashed
    # ``dict(wave_review)``) for exactly these inputs.
    PINNED = {
        "old": "e9890bb019dede839a4db0108256ffd250220007af7836d1870d3dd5db2a1082",
        "no_phases": "e73c274d443770ba4e64740c25700dadd457a340225587c3c2d1a54ef1705081",
    }

    def digest(self, wave_review) -> str:
        return review_policy.policy_input_snapshot(wave_review=wave_review, **self.KWARGS)[0]

    def test_old_and_new_spellings_hash_alike_and_match_the_pre_change_digest(self) -> None:
        new = json.loads(_current(json.dumps(self.OLD)))
        self.assertEqual(new["phases"]["prepare"]["signoff_key"], NEW_READINESS)
        self.assertEqual(self.digest(self.OLD), self.PINNED["old"])
        self.assertEqual(self.digest(new), self.PINNED["old"])
        self.assertEqual(self.digest(self.NO_PHASES), self.PINNED["no_phases"])

    def test_the_callers_policy_object_is_not_mutated(self) -> None:
        new = json.loads(_current(json.dumps(self.OLD)))
        before = copy.deepcopy(new)
        phases, prepare = new["phases"], new["phases"]["prepare"]
        self.digest(new)
        self.assertEqual(new, before)
        self.assertIs(new["phases"], phases)
        self.assertIs(new["phases"]["prepare"], prepare)
        self.assertEqual(prepare["signoff_key"], NEW_READINESS)


class ReadCompatibilityTests(unittest.TestCase):
    """AC-3 (record level): either spelling satisfies the same canonical key."""

    def test_either_spelling_satisfies_either_required_spelling(self) -> None:
        for recorded in (OLD_DELIVERY, NEW_DELIVERY):
            for required in (OLD_DELIVERY, NEW_DELIVERY):
                with self.subTest(recorded=recorded, required=required):
                    [row] = subject.review_status_rows([_approval(recorded)], [required])
                    self.assertEqual(row["state"], "approved")
                    self.assertEqual(row["signoff_key"], required)

    def test_legacy_readiness_claim_without_phase_is_readiness(self) -> None:
        record = _approval(OLD_READINESS)
        record.pop("approval_phase", None)
        self.assertEqual(subject.approval_record_phase(record), "readiness")
        self.assertEqual(subject.approval_record_phase(_approval(NEW_DELIVERY)), "delivery")

    def test_the_later_record_decides_across_spellings_in_both_orders(self) -> None:
        # A later approval record that is not valid (here: not independent)
        # is the latest word for its canonical claim, whichever spelling.
        for first, second in ((OLD_DELIVERY, NEW_DELIVERY), (NEW_DELIVERY, OLD_DELIVERY)):
            with self.subTest(order=(first, second)):
                valid = _approval(first, "approval-first")
                lapsed = _approval(second, "approval-second", independent=False)
                [row] = subject.review_status_rows([valid, lapsed], [NEW_DELIVERY])
                self.assertEqual(row["state"], "pending")
                self.assertIn("lacks independence", row["why"])
                [row] = subject.review_status_rows([lapsed, valid], [NEW_DELIVERY])
                self.assertEqual(row["state"], "approved")

    def test_prose_withdrawal_decides_across_spellings_in_both_orders(self) -> None:
        # The legacy (undeclared) prose branch, read through the authority facade.
        def current(evidence: str, lane: str) -> bool:
            authority = subject.ReviewAuthority(
                typed=False, wave_text=f"# Wave\n\n## Review Evidence\n\n{evidence}")
            return authority.signoff_current(lane)

        withdrawn = f"- {OLD_DELIVERY}: approved\n- {NEW_DELIVERY}: withdrawn\n"
        approved = f"- {NEW_DELIVERY}: withdrawn\n- {OLD_DELIVERY}: approved\n"
        for lane in (OLD_DELIVERY, NEW_DELIVERY):
            with self.subTest(lane=lane):
                self.assertFalse(current(withdrawn, lane))
                self.assertTrue(current(approved, lane))
        # A council key in either spelling is an authorization lane: prose
        # that is not a state line never authorizes it.
        self.assertFalse(current(
            "The council-delivery review approved and passed the scope.\n", NEW_DELIVERY))

    def test_status_keys_collapse_both_spellings_into_one_row(self) -> None:
        keys = subject.review_status_signoff_keys(
            [_approval(OLD_READINESS)], (NEW_READINESS, OLD_DELIVERY, "code-reviewer"))
        self.assertEqual(keys, (NEW_READINESS, NEW_DELIVERY, "code-reviewer"))

    def test_a_legacy_recheck_lane_withholds_the_current_key(self) -> None:
        head = derive(synthesis(
            finding_id="plan-defect",
            contract_relevance="required_ac",
            supported_reachability=True,
            blocking_required_lanes=["code-reviewer"],
            approval_recheck_lanes=[OLD_READINESS],
            optional_value="none",
        ))
        [row] = subject.review_status_rows([_approval(NEW_READINESS), head], [NEW_READINESS])
        self.assertEqual(row["state"], "withheld")

    def test_expected_actor_and_phase_rules_hold_for_both_spellings(self) -> None:
        for key in (OLD_READINESS, NEW_READINESS):
            with self.subTest(key=key):
                [row] = subject.review_status_rows(
                    [_approval(key, actor="council-readiness")], [NEW_READINESS])
                self.assertEqual(row["state"], "pending")
                self.assertIn("expected `wave-council`", row["why"])
        base = {
            "event": "approval", "context_id": "c", "fresh_context": True,
            "independent": True, "integrity_checks": dict(_APPROVAL_INTEGRITY),
            "observed": "o", "artifact_or_test_id": "a",
        }
        for key in (OLD_READINESS, NEW_READINESS):
            with self.subTest(key=key):
                _rows, errors = subject.build_compact_review_event(
                    (), {**base, "actor": "council-readiness", "signoff_key": key,
                         "approval_phase": "delivery"})
                joined = "\n".join(errors)
                self.assertIn("approval actor must be `wave-council`", joined)
                self.assertIn("requires approval_phase=readiness", joined)
        for key in (OLD_DELIVERY, NEW_DELIVERY):
            with self.subTest(key=key):
                _rows, errors = subject.build_compact_review_event(
                    (), {**base, "actor": "wave-council", "signoff_key": key,
                         "approval_phase": "readiness", "policy_receipt_id": "r"})
                self.assertIn(f"{key} approval requires approval_phase=delivery", errors)


def _section(rows_table: str) -> str:
    return (
        "# Wave\n\nStatus: implementing\n\n## Review Evidence\n\n"
        f"{subject.REVIEW_STATUS_MARKER_BEGIN}\n{rows_table}\n{subject.REVIEW_STATUS_MARKER_END}\n\n"
    )


class StickyLabelTests(unittest.TestCase):
    """AC-6 (renderer level): an existing block keeps its council-key spelling."""

    @staticmethod
    def _receipt(digest: str, current=None):
        semantic = {
            "schema_version": 1, "evaluator_version": 7, "policy_input_digest": digest,
            "delivery_mode": "targeted", "primer_depth": "standard",
            "council_seats": ["red-team"], "requested_lanes": [],
            "required_lanes": ["code-reviewer"], "delivery_council_required": False,
        }
        receipt, _appended = review_policy.build_policy_receipt(semantic, current)
        return receipt

    def _states(self) -> dict[str, list[dict[str, object]]]:
        first = self._receipt("a" * 64)
        second = self._receipt("b" * 64, first)
        stale_approval = _approval(
            OLD_READINESS, approval_phase="readiness", policy_receipt_id=first["receipt_id"])
        head = derive(synthesis(
            finding_id="plan-defect",
            contract_relevance="required_ac",
            supported_reachability=True,
            blocking_required_lanes=["code-reviewer"],
            approval_recheck_lanes=[OLD_READINESS],
            optional_value="none",
        ))
        return {
            "pending": [],
            "stale": [first, stale_approval, second],
            "withheld": [first, _approval(
                OLD_READINESS, approval_phase="readiness",
                policy_receipt_id=first["receipt_id"]), head],
        }

    def test_existing_legacy_rows_render_byte_identical(self) -> None:
        expected_next = {
            "pending": f"record approval evidence for {OLD_READINESS}",
            "stale": f"record approval evidence for {OLD_READINESS}",
            "withheld": f"then re-approve {OLD_READINESS}",
        }
        for state, records in self._states().items():
            with self.subTest(state=state):
                # The block as the earlier release wrote it: rows labelled by
                # the config's (earlier) key spelling.
                before = _section(subject.review_status_human_table(records, [OLD_READINESS]))
                self.assertIn(f"| {OLD_READINESS} |", before)
                self.assertIn(expected_next[state], before)
                self.assertNotIn(f"| {NEW_READINESS} |", before)
                # The renderer now receives the canonical key (what docs-lint
                # and every lifecycle writer derive) and keeps the spelling.
                after = subject.render_review_status_projection(before, records, [NEW_READINESS])
                self.assertEqual(after, before)
                row = next(line for line in after.splitlines() if line.startswith(f"| {OLD_READINESS} |"))
                self.assertIn(f"| {state if state != 'stale' else 'pending'} |", row)
                self.assertIn(expected_next[state], row)
                self.assertNotIn(NEW_READINESS.join(("| ", " |")), row)

    def test_a_new_key_approval_shows_under_the_sticky_label(self) -> None:
        before = _section(subject.review_status_human_table([], [OLD_DELIVERY]))
        after = subject.render_review_status_projection(
            before, [_approval(NEW_DELIVERY)], [NEW_DELIVERY])
        self.assertIn(f"| {OLD_DELIVERY} | approved |", after)
        self.assertNotIn(f"| {NEW_DELIVERY} |", after)

    def test_a_block_without_the_row_uses_the_current_spelling(self) -> None:
        before = _section(subject.review_status_human_table([], ["code-reviewer"]))
        after = subject.render_review_status_projection(before, [], [OLD_READINESS, "code-reviewer"])
        self.assertIn(f"| {NEW_READINESS} | pending |", after)
        self.assertNotIn(OLD_READINESS, after)

    def test_a_generated_legacy_line_is_dropped_when_the_ledger_holds_the_new_key(self) -> None:
        text = _section(subject.review_status_human_table([], [NEW_READINESS])) + (
            f"- {OLD_READINESS}: approved \u2014 recorded by an earlier release\n"
            "- operator note: keep this prose\n"
        )
        rendered = subject.render_review_status_projection(
            text, [_approval(NEW_READINESS, approval_phase="readiness")], [NEW_READINESS])
        self.assertNotIn(f"- {OLD_READINESS}: approved", rendered)
        self.assertIn("- operator note: keep this prose", rendered)


class LifecycleCompatibilityTests(unittest.TestCase):
    """AC-2, AC-3, AC-4 and AC-6 through the real lifecycle producers."""

    CONFIG = {**_WAVE_REVIEW_CONFIG, "wave_review": {"enabled": True, "delivery_mode": "universal"}}

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        for name, value in (("run_validate", _stub_validate), ("run_garden", _stub_garden),
                            ("_run_post_write_lint", lambda *a, **k: {"mode": "stubbed"})):
            patcher = patch.object(self.srv, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _event(self, root, wave_id, event, actor, context_id, **kwargs):
        return self.srv.wf_review_event_response(
            root, wave_id, event, actor, context_id,
            fresh_context=True, independent=True,
            evidence=_approval_evidence(actor),
            integrity_checks=dict(_APPROVAL_INTEGRITY), **kwargs)

    def _readied(self, name, *, status="planned", approvals=(NEW_READINESS, "code-reviewer")):
        root = _make_repo(self.base / name)
        _write_config(root, self.CONFIG)
        wave_md, wave_id = _build_one(self.srv, root, name, status=status)
        # The change document carries its status header from the start, so a
        # later status change moves no receipt input (as in test_phase_gates).
        label = vocabulary_profile.MEMBER_STATUS_LABEL
        doc = next(path for path in wave_md.parent.glob("*.md") if path != wave_md)
        title, rest = doc.read_text(encoding="utf-8").split("\n", 1)
        doc.write_text(f"{title}\n\n{label}: `planned`\n{rest}", encoding="utf-8")
        seed_state(self.srv, root, wave_id, approvals)
        return root, wave_md, wave_id

    def _deliver(self, root, wave_md, wave_id):
        self.assertEqual(self._event(root, wave_id, "run", "wave-council", "delivery-run",
                                     mode="create", run_kind="initial_delivery")["status"], "ok")
        for key, actor in (("code-reviewer", "code-reviewer"), (NEW_DELIVERY, "wave-council"),
                           ("operator-signoff", "operator")):
            response = self._event(root, wave_id, "approval", actor, f"delivery-{key}", mode="create",
                                   signoff_key=key, approval_phase="delivery")
            self.assertEqual(response["status"], "ok", response)
        label = vocabulary_profile.MEMBER_STATUS_LABEL
        for doc in wave_md.parent.glob("*.md"):
            text = doc.read_text(encoding="utf-8")
            doc.write_text(text.replace(f"{label}: `planned`", f"{label}: `complete`", 1),
                           encoding="utf-8")

    @staticmethod
    def _respell(root: Path, wave_md: Path, keys: tuple[str, ...]) -> None:
        for path in (wave_md, subject.review_event_path(wave_md)):
            path.write_text(_legacy(path.read_text(encoding="utf-8"), keys=keys), encoding="utf-8")

    def _variants(self, build):
        """The same wave with new-key, legacy and mixed ledgers."""
        out = {}
        for variant, keys in (("new", ()), ("legacy", (NEW_READINESS, NEW_DELIVERY)),
                              ("mixed", (NEW_READINESS,))):
            root, wave_md, wave_id = build(variant)
            if keys:
                self._respell(root, wave_md, keys)
                ledger = subject.review_event_path(wave_md).read_text(encoding="utf-8")
                self.assertIn(f"approval:{OLD_READINESS}", ledger)
            out[variant] = (root, wave_md, wave_id)
        return out

    def _normalized(self, response, wave_id):
        return json.loads(_current(json.dumps(response, sort_keys=True)).replace(wave_id, "<wave>"))

    def test_old_key_input_writes_the_new_key(self) -> None:
        """AC-2."""
        root, wave_md, wave_id = self._readied("alias-input", approvals=())
        self._event(root, wave_id, "run", "wave-council", "readiness-run", mode="create",
                    run_kind="readiness")
        for mode in ("dry_run", "create"):
            for given in (OLD_READINESS, NEW_READINESS):
                with self.subTest(mode=mode, given=given):
                    response = self._event(root, wave_id, "approval", "wave-council",
                                           f"alias-{mode}-{given}", mode=mode,
                                           signoff_key=given, approval_phase="readiness")
                    self.assertIn(response["status"], {"ok", "dry_run"}, response)
                    notices = [d for d in response["diagnostics"] if d["code"] == "signoff_key_alias"]
                    if given == OLD_READINESS:
                        self.assertEqual(len(notices), 1)
                        self.assertEqual(notices[0]["severity"], "info")
                        self.assertIn(f"`{NEW_READINESS}`", notices[0]["message"])
                    else:
                        self.assertEqual(notices, [])
        records, errors = subject.read_review_event_ledger(wave_md)
        self.assertEqual(errors, ())
        approvals = [r for r in records if r.get("claim_kind") == "approval"]
        self.assertEqual(len(approvals), 2)
        for record in approvals:
            self.assertEqual(record["claim_id"], f"approval:{NEW_READINESS}")
            self.assertEqual(record[subject.EVENT_IDENTITY_FIELD]["signoff_key"], NEW_READINESS)
        for given in (OLD_READINESS, NEW_READINESS):
            with self.subTest(rejected=given):
                wrong_actor = self._event(root, wave_id, "approval", "council-readiness",
                                          f"actor-{given}", mode="dry_run",
                                          signoff_key=given, approval_phase="readiness")
                self.assertEqual(wrong_actor["status"], "error")
                self.assertIn("approval actor must be `wave-council`",
                              json.dumps(wrong_actor["diagnostics"]))
                wrong_phase = self._event(root, wave_id, "approval", "wave-council",
                                          f"phase-{given}", mode="dry_run",
                                          signoff_key=given, approval_phase="delivery")
                self.assertEqual(wrong_phase["status"], "error")
                self.assertIn("requires approval_phase=readiness",
                              json.dumps(wrong_phase["diagnostics"]))

    def test_activation_and_implement_pass_alike_on_legacy_new_and_mixed_ledgers(self) -> None:
        """AC-3: the prepare activation gate and wf_implement_wave."""
        variants = self._variants(lambda v: self._readied(f"ready-{v}"))
        results = {}
        for variant, (root, _wave_md, wave_id) in variants.items():
            captured = capture(self.srv, root, wave_id)
            work = root.parent / f"{root.name}__implement"
            shutil.copytree(root, work)
            captured["implement:dry_run"] = self.srv.wf_implement_wave_response(work, wave_id, mode="dry_run")
            captured["implement:create"] = self.srv.wf_implement_wave_response(work, wave_id, mode="create")
            results[variant] = {
                route: self._normalized(captured[route], wave_id)
                for route in ("prepare:dry_run", "prepare:ready", "prepare:create",
                              "implement:dry_run", "implement:create")
            }
        self.assertEqual(results["new"]["prepare:create"]["status"], "ok", results["new"]["prepare:create"])
        self.assertEqual(results["new"]["implement:create"]["status"], "ok", results["new"]["implement:create"])
        for route, response in results["new"].items():
            for variant in ("legacy", "mixed"):
                with self.subTest(route=route, variant=variant):
                    self.assertEqual(results[variant][route]["status"], response["status"])
                    self.assertEqual(
                        [d["code"] for d in results[variant][route]["diagnostics"]],
                        [d["code"] for d in response["diagnostics"]],
                    )
                    self.assertEqual(results[variant][route]["data"].get("required_council_signoffs"),
                                     response["data"].get("required_council_signoffs"))

    def test_review_and_close_pass_alike_on_legacy_new_and_mixed_ledgers(self) -> None:
        """AC-3: the review gate and the close gate; the mixed ledger closes."""
        def build(variant):
            root, wave_md, wave_id = self._readied(f"close-{variant}", status="active")
            self._deliver(root, wave_md, wave_id)
            return root, wave_md, wave_id

        variants = self._variants(build)
        results = {}
        for variant, (root, _wave_md, wave_id) in variants.items():
            with patch.object(self.srv, "_framework_test_receipt_diagnostic", lambda *a, **k: None, create=True):
                captured = capture(self.srv, root, wave_id)
            results[variant] = {
                route: self._normalized(captured[route], wave_id)
                for route in ("review:implementation", "close:dry_run", "close:create")
            }
        self.assertEqual(results["new"]["close:create"]["status"], "ok", results["new"]["close:create"])
        for route, response in results["new"].items():
            for variant in ("legacy", "mixed"):
                with self.subTest(route=route, variant=variant):
                    self.assertEqual(results[variant][route]["status"], response["status"],
                                     results[variant][route])
                    self.assertEqual(
                        [d["code"] for d in results[variant][route]["diagnostics"]],
                        [d["code"] for d in response["diagnostics"]],
                    )

    def test_old_new_and_absent_config_keys_require_the_same_keys(self) -> None:
        """AC-4: configs are read canonically and never written."""
        support = self.srv.lifecycle_gate_support
        root, wave_md, wave_id = self._readied("config-keys", status="active")
        config_path = root / "docs" / "workflow-config.json"
        phases = {"prepare": {"signoff_key": OLD_READINESS, "moderator_role": "wave-council"},
                  "review": {"signoff_key": OLD_DELIVERY, "moderator_role": "wave-council"}}
        configs = {
            "old": {**self.CONFIG, "wave_review": {**self.CONFIG["wave_review"], "phases": phases}},
            "new": {**self.CONFIG, "wave_review": {**self.CONFIG["wave_review"],
                                                   "phases": json.loads(_current(json.dumps(phases)))}},
            "absent": self.CONFIG,
        }
        seen = {}
        for name, config in configs.items():
            _write_config(root, config)
            before = config_path.read_bytes()
            text = wave_md.read_text(encoding="utf-8")
            seen[name] = (
                {phase: support._required_wave_council_signoffs(root, phase, wave_text=text, wave_md=wave_md)
                 for phase in ("prepare", "review", "close")},
                subject.required_review_status_keys(root, text),
            )
            self.srv.wf_prepare_wave_response(root, wave_id, mode="dry_run")
            self.srv.wf_review_wave_response(root, wave_id, phase="implementation")
            self.assertEqual(config_path.read_bytes(), before, name)
        self.assertEqual(seen["old"], seen["new"])
        self.assertEqual(seen["old"], seen["absent"])
        self.assertEqual(seen["old"][0]["close"], [NEW_READINESS, NEW_DELIVERY])

    def test_status_block_label_sticks_and_new_waves_show_the_new_key(self) -> None:
        """AC-6: through the real writer, with docs-lint clean on both waves."""
        from wave_lint_lib.wave_validators import check_wave_docs

        root, wave_md, wave_id = self._readied("sticky", status="active", approvals=("code-reviewer",))
        self._respell(root, wave_md, (NEW_READINESS, NEW_DELIVERY))
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn(f"| {OLD_READINESS} | pending |", text)
        self.assertEqual(check_wave_docs(root), [])
        response = self._event(root, wave_id, "approval", "wave-council", "sticky-readiness",
                               mode="create", signoff_key=NEW_READINESS, approval_phase="readiness")
        self.assertEqual(response["status"], "ok", response)
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn(f"| {OLD_READINESS} | approved |", text)
        self.assertNotIn(f"| {NEW_READINESS} |", text)
        created = self.srv.wf_create_wave_response(root, "fresh-wave", mode="create")["data"]
        fresh = (root / created["path"]).read_text(encoding="utf-8")
        self.assertIn(f"| {NEW_READINESS} | pending |", fresh)
        self.assertNotIn(OLD_READINESS, fresh)
        self.assertEqual(check_wave_docs(root), [])

    def test_dashboard_rows_keep_the_sticky_label(self) -> None:
        """AC-6 on the dashboard: a legacy-labelled block plus a new-key
        approval shows the row under the block's earlier spelling."""
        import dashboard_lib

        root, wave_md, wave_id = self._readied("dashboard-sticky", status="active",
                                               approvals=("code-reviewer",))
        self._respell(root, wave_md, (NEW_READINESS, NEW_DELIVERY))
        self.assertIn(f"| {OLD_READINESS} | pending |", wave_md.read_text(encoding="utf-8"))
        response = self._event(root, wave_id, "approval", "wave-council", "dashboard-readiness",
                               mode="create", signoff_key=NEW_READINESS, approval_phase="readiness")
        self.assertEqual(response["status"], "ok", response)
        text = wave_md.read_text(encoding="utf-8")
        state = dashboard_lib._review_evidence_dashboard_state(root, wave_md, text)
        self.assertEqual(state["integrity"], "ok", state)
        rows = {row["key"]: row["value"] for row in state["approvals"]}
        self.assertEqual(rows.get(OLD_READINESS), "approved", rows)
        self.assertNotIn(NEW_READINESS, rows)
        self.assertIn(f"| {OLD_READINESS} | approved |", state["projection"])
        self.assertNotIn(f"| {NEW_READINESS} |", state["projection"])

    def test_a_legacy_key_approval_replays_after_the_rename(self) -> None:
        """An approval first recorded under the earlier key (its identity and
        digest hashed that spelling) replays when retried with the same
        context_id after the rename, in either spelling; nothing is appended
        and the ledger is not rewritten."""
        root, wave_md, wave_id = self._readied("legacy-replay", approvals=())
        self._event(root, wave_id, "run", "wave-council", "readiness-run", mode="create",
                    run_kind="readiness")
        # The earlier release recorded the key as given: call below the
        # canonicalizing input wrapper.
        unwrapped = self.srv.wf_review_event_response.__wrapped__.__wrapped__
        legacy = unwrapped(root, wave_id, "approval", "wave-council", "legacy-ctx",
                           fresh_context=True, independent=True,
                           evidence=_approval_evidence("wave-council"),
                           integrity_checks=dict(_APPROVAL_INTEGRITY), mode="create",
                           signoff_key=OLD_READINESS, approval_phase="readiness")
        self.assertEqual(legacy["status"], "ok", legacy)
        ledger_path = subject.review_event_path(wave_md)
        ledger = ledger_path.read_bytes()
        records, errors = subject.read_review_event_ledger(wave_md)
        self.assertEqual(errors, ())
        approvals = [r for r in records if r.get("claim_kind") == "approval"]
        self.assertEqual(len(approvals), 1)
        self.assertEqual(approvals[0][subject.EVENT_IDENTITY_FIELD]["signoff_key"], OLD_READINESS)
        for given in (OLD_READINESS, NEW_READINESS):
            for mode in ("dry_run", "create"):
                with self.subTest(given=given, mode=mode):
                    retry = self._event(root, wave_id, "approval", "wave-council", "legacy-ctx",
                                        mode=mode, signoff_key=given, approval_phase="readiness")
                    self.assertIn(retry["status"], {"ok", "dry_run"}, retry)
                    self.assertNotIn("review_event_identity_conflict", json.dumps(retry))
                    self.assertEqual(ledger_path.read_bytes(), ledger)
        # A new context still appends, with the canonical identity.
        fresh = self._event(root, wave_id, "approval", "wave-council", "fresh-ctx",
                            mode="create", signoff_key=OLD_READINESS, approval_phase="readiness")
        self.assertEqual(fresh["status"], "ok", fresh)
        records, _errors = subject.read_review_event_ledger(wave_md)
        approvals = [r for r in records if r.get("claim_kind") == "approval"]
        self.assertEqual(len(approvals), 2)
        self.assertEqual(approvals[1][subject.EVENT_IDENTITY_FIELD]["signoff_key"], NEW_READINESS)

    def test_a_legacy_key_approval_with_different_evidence_is_a_conflict(self) -> None:
        """The legacy lookup replays only the request the earlier release
        recorded: the same context_id with different evidence is an identity
        conflict in either spelling and either mode, and nothing is written."""
        root, wave_md, wave_id = self._readied("legacy-conflict", approvals=())
        self._event(root, wave_id, "run", "wave-council", "readiness-run", mode="create",
                    run_kind="readiness")
        unwrapped = self.srv.wf_review_event_response.__wrapped__.__wrapped__
        legacy = unwrapped(root, wave_id, "approval", "wave-council", "legacy-ctx",
                           fresh_context=True, independent=True,
                           evidence=_approval_evidence("wave-council"),
                           integrity_checks=dict(_APPROVAL_INTEGRITY), mode="create",
                           signoff_key=OLD_READINESS, approval_phase="readiness")
        self.assertEqual(legacy["status"], "ok", legacy)
        ledger_path = subject.review_event_path(wave_md)
        ledger = ledger_path.read_bytes()
        changed = _approval_evidence("wave-council")
        changed["observed"] = "wave-council verified a different fixture scope"
        for given in (OLD_READINESS, NEW_READINESS):
            for mode in ("dry_run", "create"):
                with self.subTest(given=given, mode=mode):
                    retry = self.srv.wf_review_event_response(
                        root, wave_id, "approval", "wave-council", "legacy-ctx",
                        fresh_context=True, independent=True, evidence=dict(changed),
                        integrity_checks=dict(_APPROVAL_INTEGRITY), mode=mode,
                        signoff_key=given, approval_phase="readiness")
                    self.assertEqual(retry["status"], "error", retry)
                    self.assertIn("review_event_identity_conflict", json.dumps(retry))
                    self.assertEqual(ledger_path.read_bytes(), ledger)


if __name__ == "__main__":
    unittest.main()
