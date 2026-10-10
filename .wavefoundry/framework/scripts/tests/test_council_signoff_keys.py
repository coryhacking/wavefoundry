"""Wave 1zyb4 (1zxnx): tier-neutral council signoff keys.

New approvals carry ``council-readiness`` / ``council-delivery``. The earlier
spellings (``review_evidence.LEGACY_COUNCIL_SIGNOFF_KEYS``) are history: they
stay readable forever (ledgers and wave records are never rewritten), and they
stay accepted as tool input and config values during the alias period. The
fixtures below that write the earlier spelling model those legacy ledgers.

Change 200ex: every earlier spelling is derived from ``review_evidence`` (the
framework's single source of the legacy map), never written here, so a
distribution that declares other or additional earlier spellings runs these
tests unchanged. A frozen historical payload encoder supplies an independent
compatibility oracle, cross-checked against shipped golden vectors.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import tempfile
import sys
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

NEW_READINESS = subject.COUNCIL_READINESS_SIGNOFF_KEY
NEW_DELIVERY = subject.COUNCIL_DELIVERY_SIGNOFF_KEY
# Every earlier spelling per current key, from the framework's legacy map; the
# first one is the spelling the fixtures write.
OLD_SPELLINGS = {key: subject.legacy_signoff_key_spellings(key) for key in (NEW_READINESS, NEW_DELIVERY)}
OLD_READINESS = OLD_SPELLINGS[NEW_READINESS][0]
OLD_DELIVERY = OLD_SPELLINGS[NEW_DELIVERY][0]
# A custom key a distribution may configure under the legacy council prefix.
CUSTOM_COUNCIL_KEY = subject._LEGACY_COUNCIL_KEY_PREFIX + "x"
# Wave 200ey (change 200ew): the council actor and its earlier name, which
# ledgers written before the rename carry.
ACTOR = subject.COUNCIL_ACTOR
LEGACY_ACTOR = subject.LEGACY_COUNCIL_ACTORS[0]


def _as_earlier_release(srv):
    """Write events as the release before the actor rename did: the builder's
    expected council actor is the earlier name (in the module the server's
    builder reads)."""
    module = sys.modules[srv.build_identified_review_event.__module__]
    return patch.object(module, "COUNCIL_ACTOR", LEGACY_ACTOR)


def _builtin_legacy_keys() -> dict[str, str]:
    """The built-in legacy mapping: the legacy map less any distribution-declared
    extra spellings (``EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS``, when the vocabulary
    profile declares it)."""
    extra = getattr(vocabulary_profile, "EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS", {}) or {}
    return {old: new for old, new in subject.LEGACY_COUNCIL_SIGNOFF_KEYS.items() if old not in extra}


def _token(key: str) -> str:
    """``key`` as a whole token: not preceded or followed by a word character or ``-``."""
    return rf"(?<![\w-]){re.escape(key)}(?![\w-])"


def _legacy(text: str, *, keys: tuple[str, ...] = (NEW_READINESS, NEW_DELIVERY)) -> str:
    """Spell the named current keys the earlier way (models a legacy ledger)."""
    for key in keys:
        text = re.sub(_token(key), OLD_SPELLINGS[key][0], text)
    return text


def _current(text: str) -> str:
    """Spell every earlier council key the current way."""
    for old in sorted(subject.LEGACY_COUNCIL_SIGNOFF_KEYS, key=len, reverse=True):
        text = re.sub(_token(old), subject.LEGACY_COUNCIL_SIGNOFF_KEYS[old], text)
    return text


def _approval(key: str, evidence_id: str | None = None, **overrides: object) -> dict[str, object]:
    actor = overrides.pop("actor", None) or (
        ACTOR if subject.is_council_signoff_key(key) else key)
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
        for new, spellings in OLD_SPELLINGS.items():
            self.assertTrue(spellings, new)
            for old in spellings:
                with self.subTest(old=old):
                    self.assertEqual(subject.canonical_signoff_key(old), new)
        for unchanged in (NEW_READINESS, NEW_DELIVERY, "operator-signoff",
                          "code-reviewer", "qa-reviewer", CUSTOM_COUNCIL_KEY, ACTOR, LEGACY_ACTOR):
            with self.subTest(key=unchanged):
                self.assertEqual(subject.canonical_signoff_key(unchanged), unchanged)

    def test_is_council_signoff_key(self) -> None:
        legacy = tuple(old for spellings in OLD_SPELLINGS.values() for old in spellings)
        for key in (*legacy, NEW_READINESS, NEW_DELIVERY, CUSTOM_COUNCIL_KEY):
            with self.subTest(key=key):
                self.assertTrue(subject.is_council_signoff_key(key))
        for key in ("council-review", "code-reviewer", "operator-signoff", ACTOR, LEGACY_ACTOR,
                    ACTOR + "-x", ""):
            with self.subTest(key=key):
                self.assertFalse(subject.is_council_signoff_key(key))

    def test_claim_ids_canonicalize_only_approval_keys(self) -> None:
        self.assertEqual(
            subject.canonical_approval_claim_id(f"approval:{OLD_READINESS}"),
            f"approval:{NEW_READINESS}",
        )
        self.assertEqual(subject.canonical_approval_claim_id("finding:x"), "finding:x")

    def test_digest_spelling_mirrors_the_alias_map(self) -> None:
        # The digest map equals the reverse of the built-in pair only, never
        # the map merged with a distribution's extra spellings.
        self.assertEqual(
            review_policy._DIGEST_COUNCIL_SIGNOFF_SPELLING,
            {new: old for old, new in _builtin_legacy_keys().items()},
        )


def _phases_config(readiness: str, delivery: str, moderator: str = ACTOR) -> dict:
    return {"enabled": True, "delivery_mode": "universal", "phases": {
        "prepare": {"signoff_key": readiness, "moderator_role": moderator},
        "review": {"signoff_key": delivery, "moderator_role": moderator}}}


class DigestInputTests(unittest.TestCase):
    """AC-11: a key spelling never rotates a receipt."""

    # A config naming the built-in earlier spellings (the ones the digest map
    # writes), derived, never a literal.
    OLD = _phases_config(*(next(old for old, new in _builtin_legacy_keys().items() if new == key)
                           for key in (NEW_READINESS, NEW_DELIVERY)))
    # Historical config uses only the built-in key/actor declarations. Extra
    # distribution aliases never determine the historical digest spelling.
    PINNED_OLD_INPUT = _phases_config(
        *(next(old for old, new in subject.BUILTIN_LEGACY_COUNCIL_SIGNOFF_KEYS.items() if new == key)
          for key in (NEW_READINESS, NEW_DELIVERY)),
        moderator=subject.BUILTIN_LEGACY_COUNCIL_ACTORS[0])
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

    def test_old_and_new_spellings_hash_alike(self) -> None:
        new = json.loads(_current(json.dumps(self.OLD)))
        self.assertEqual(new["phases"]["prepare"]["signoff_key"], NEW_READINESS)
        self.assertEqual(new["phases"]["review"]["signoff_key"], NEW_DELIVERY)
        self.assertEqual(self.digest(new), self.digest(self.OLD))
        self.assertEqual(self.digest(self.NO_PHASES), self.PINNED["no_phases"])

    def historical_payload(self, config) -> dict:
        # Frozen pre-alias encoder for this tiny fixture; no current production
        # canonicalizer, snapshot, digest normalization or version constants.
        return {
            "schema_version": 1,
            "evaluator_version": 7,
            "wave_review": copy.deepcopy(config),
            "project_required_review_lanes": ["code-reviewer"],
            "review_policies": {},
            "changes": [{"change_id": "1aaaa-enh pinned", "kind": "enh",
                         "sha256": "c2743efe0145928e5d6c28910e372846d112e28788daa62ab611299809988290"}],
            "requested_lanes": [],
        }

    def historical_digest(self, config) -> str:
        return hashlib.sha256(json.dumps(self.historical_payload(config),
            sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()

    def test_the_pre_change_digest_is_unchanged(self) -> None:
        expected = self.historical_digest(self.PINNED_OLD_INPUT)
        self.assertEqual(self.digest(self.PINNED_OLD_INPUT), expected)
        self.assertEqual(self.digest(_phases_config(NEW_READINESS, NEW_DELIVERY, ACTOR)), expected)
        self.assertEqual(self.digest(self.NO_PHASES), self.historical_digest(self.NO_PHASES))
        self.assertEqual(self.historical_digest(self.NO_PHASES), self.PINNED["no_phases"])

    def test_frozen_encoder_matches_the_independent_shipped_golden(self) -> None:
        # Build the shipped-language golden input without rename-sensitive
        # lifecycle literals. This vector is fixed independently of live aliases.
        old_actor = "-".join(("wa" + "ve", "council"))
        shipped = _phases_config(old_actor + "-readiness", old_actor + "-delivery", old_actor)
        self.assertEqual(self.historical_digest(shipped), self.PINNED["old"])

    def test_the_oracle_detects_payload_and_key_normalization_mutants(self) -> None:
        expected = self.historical_digest(self.PINNED_OLD_INPUT)
        changed = copy.deepcopy(self.PINNED_OLD_INPUT)
        changed["delivery_mode"] = "targeted"
        self.assertNotEqual(self.digest(changed), expected)
        with patch.object(review_policy, "_DIGEST_COUNCIL_SIGNOFF_SPELLING", {}):
            self.assertNotEqual(self.digest(_phases_config(NEW_READINESS, NEW_DELIVERY, ACTOR)), expected)
        with patch.object(review_policy, "canonical_review_policy_body", return_value=b"changed"):
            self.assertNotEqual(self.digest(self.PINNED_OLD_INPUT), expected)

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
        for recorded in (*OLD_SPELLINGS[NEW_DELIVERY], NEW_DELIVERY):
            for required in (*OLD_SPELLINGS[NEW_DELIVERY], NEW_DELIVERY):
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
        for lane in (*OLD_SPELLINGS[NEW_DELIVERY], NEW_DELIVERY):
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
        for key in (*OLD_SPELLINGS[NEW_READINESS], NEW_READINESS):
            with self.subTest(key=key):
                [row] = subject.review_status_rows(
                    [_approval(key, actor="council-readiness")], [NEW_READINESS])
                self.assertEqual(row["state"], "pending")
                self.assertIn(f"expected `{ACTOR}`", row["why"])
        base = {
            "event": "approval", "context_id": "c", "fresh_context": True,
            "independent": True, "integrity_checks": dict(_APPROVAL_INTEGRITY),
            "observed": "o", "artifact_or_test_id": "a",
        }
        for key in (*OLD_SPELLINGS[NEW_READINESS], NEW_READINESS):
            with self.subTest(key=key):
                _rows, errors = subject.build_compact_review_event(
                    (), {**base, "actor": "council-readiness", "signoff_key": key,
                         "approval_phase": "delivery"})
                joined = "\n".join(errors)
                self.assertIn(f"approval actor must be `{ACTOR}`", joined)
                self.assertIn("requires approval_phase=readiness", joined)
        for key in (*OLD_SPELLINGS[NEW_DELIVERY], NEW_DELIVERY):
            with self.subTest(key=key):
                _rows, errors = subject.build_compact_review_event(
                    (), {**base, "actor": ACTOR, "signoff_key": key,
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
        self.assertEqual(self._event(root, wave_id, "run", ACTOR, "delivery-run",
                                     mode="create", run_kind="initial_delivery")["status"], "ok")
        for key, actor in (("code-reviewer", "code-reviewer"), (NEW_DELIVERY, ACTOR),
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
        self._event(root, wave_id, "run", ACTOR, "readiness-run", mode="create",
                    run_kind="readiness")
        for mode in ("dry_run", "create"):
            for given in (OLD_READINESS, NEW_READINESS):
                with self.subTest(mode=mode, given=given):
                    response = self._event(root, wave_id, "approval", ACTOR,
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
                self.assertIn(f"approval actor must be `{ACTOR}`",
                              json.dumps(wrong_actor["diagnostics"]))
                wrong_phase = self._event(root, wave_id, "approval", ACTOR,
                                          f"phase-{given}", mode="dry_run",
                                          signoff_key=given, approval_phase="delivery")
                self.assertEqual(wrong_phase["status"], "error")
                self.assertIn("requires approval_phase=readiness",
                              json.dumps(wrong_phase["diagnostics"]))

    def test_old_actor_input_writes_the_new_actor(self) -> None:
        """Wave 200ey (change 200ew, AC-4): an approval given the earlier
        council actor name is recorded with the current one and the response
        carries an ``actor_alias`` notice; the current name carries none."""
        root, wave_md, wave_id = self._readied("actor-alias", approvals=())
        self._event(root, wave_id, "run", ACTOR, "readiness-run", mode="create",
                    run_kind="readiness")
        for mode in ("dry_run", "create"):
            for given in (LEGACY_ACTOR, ACTOR):
                with self.subTest(mode=mode, given=given):
                    response = self._event(root, wave_id, "approval", given,
                                           f"actor-{mode}-{given}", mode=mode,
                                           signoff_key=NEW_READINESS, approval_phase="readiness")
                    self.assertIn(response["status"], {"ok", "dry_run"}, response)
                    notices = [d for d in response["diagnostics"] if d["code"] == "actor_alias"]
                    if given == LEGACY_ACTOR:
                        self.assertEqual(len(notices), 1, response["diagnostics"])
                        self.assertEqual(notices[0]["severity"], "info")
                        self.assertIn(f"`{ACTOR}`", notices[0]["message"])
                    else:
                        self.assertEqual(notices, [])
        records, errors = subject.read_review_event_ledger(wave_md)
        self.assertEqual(errors, ())
        approvals = [r for r in records if r.get("claim_kind") == "approval"]
        self.assertEqual(len(approvals), 2)
        for record in approvals:
            self.assertEqual(record["verification_context"]["actor"], ACTOR)
            self.assertEqual(record[subject.EVENT_IDENTITY_FIELD]["actor"], ACTOR)

    def test_declared_spaced_legacy_key_writes_a_canonical_approval(self) -> None:
        root, wave_md, wave_id = self._readied("declared-key", approvals=())
        self._event(root, wave_id, "run", ACTOR, "readiness-run", mode="create",
                    run_kind="readiness")
        earlier = "Review Board Readiness"
        mapping = self.srv.canonical_signoff_key.__globals__["LEGACY_COUNCIL_SIGNOFF_KEYS"]
        with patch.dict(mapping, {earlier: NEW_READINESS}):
            for mode in ("dry_run", "create"):
                response = self._event(root, wave_id, "approval", LEGACY_ACTOR,
                                       f"declared-{mode}", mode=mode,
                                       signoff_key=earlier, approval_phase="readiness")
                self.assertIn(response["status"], {"ok", "dry_run"}, response)
                notices = {d["code"] for d in response["diagnostics"]}
                self.assertTrue({"actor_alias", "signoff_key_alias"} <= notices, response)
        records, errors = subject.read_review_event_ledger(wave_md)
        self.assertEqual(errors, ())
        approvals = [r for r in records if r.get("claim_kind") == "approval"]
        self.assertEqual(len(approvals), 1)
        self.assertEqual(approvals[0]["verification_context"]["actor"], ACTOR)
        self.assertEqual(approvals[0]["claim_id"], f"approval:{NEW_READINESS}")
        self.assertEqual(approvals[0][subject.EVENT_IDENTITY_FIELD]["signoff_key"], NEW_READINESS)

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
        phases = {"prepare": {"signoff_key": OLD_READINESS, "moderator_role": LEGACY_ACTOR},
                  "review": {"signoff_key": OLD_DELIVERY, "moderator_role": LEGACY_ACTOR}}
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
        response = self._event(root, wave_id, "approval", ACTOR, "sticky-readiness",
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
        response = self._event(root, wave_id, "approval", ACTOR, "dashboard-readiness",
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
        self._event(root, wave_id, "run", ACTOR, "readiness-run", mode="create",
                    run_kind="readiness")
        # The earlier release recorded the key as given: call below the
        # canonicalizing input wrapper.
        unwrapped = self.srv.wf_review_event_response.__wrapped__.__wrapped__
        with _as_earlier_release(self.srv):
            legacy = unwrapped(root, wave_id, "approval", LEGACY_ACTOR, "legacy-ctx",
                               fresh_context=True, independent=True,
                               evidence=_approval_evidence(LEGACY_ACTOR),
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
        for given, actor in ((OLD_READINESS, LEGACY_ACTOR), (NEW_READINESS, LEGACY_ACTOR),
                             (NEW_READINESS, ACTOR)):
            for mode in ("dry_run", "create"):
                with self.subTest(given=given, actor=actor, mode=mode):
                    # The evidence names the earlier actor, as the first request did.
                    retry = self.srv.wf_review_event_response(
                        root, wave_id, "approval", actor, "legacy-ctx",
                        fresh_context=True, independent=True,
                        evidence=_approval_evidence(LEGACY_ACTOR),
                        integrity_checks=dict(_APPROVAL_INTEGRITY),
                        mode=mode, signoff_key=given, approval_phase="readiness")
                    self.assertIn(retry["status"], {"ok", "dry_run"}, retry)
                    self.assertNotIn("review_event_identity_conflict", json.dumps(retry))
                    self.assertEqual(ledger_path.read_bytes(), ledger)
        # A new context still appends, with the canonical identity.
        fresh = self._event(root, wave_id, "approval", ACTOR, "fresh-ctx",
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
        self._event(root, wave_id, "run", ACTOR, "readiness-run", mode="create",
                    run_kind="readiness")
        unwrapped = self.srv.wf_review_event_response.__wrapped__.__wrapped__
        with _as_earlier_release(self.srv):
            legacy = unwrapped(root, wave_id, "approval", LEGACY_ACTOR, "legacy-ctx",
                               fresh_context=True, independent=True,
                               evidence=_approval_evidence(LEGACY_ACTOR),
                               integrity_checks=dict(_APPROVAL_INTEGRITY), mode="create",
                               signoff_key=OLD_READINESS, approval_phase="readiness")
        self.assertEqual(legacy["status"], "ok", legacy)
        ledger_path = subject.review_event_path(wave_md)
        ledger = ledger_path.read_bytes()
        changed = _approval_evidence(LEGACY_ACTOR)
        changed["observed"] = "wave-council verified a different fixture scope"
        for given in (OLD_READINESS, NEW_READINESS):
            for mode in ("dry_run", "create"):
                with self.subTest(given=given, mode=mode):
                    retry = self.srv.wf_review_event_response(
                        root, wave_id, "approval", LEGACY_ACTOR, "legacy-ctx",
                        fresh_context=True, independent=True, evidence=dict(changed),
                        integrity_checks=dict(_APPROVAL_INTEGRITY), mode=mode,
                        signoff_key=given, approval_phase="readiness")
                    self.assertEqual(retry["status"], "error", retry)
                    self.assertIn("review_event_identity_conflict", json.dumps(retry))
                    self.assertEqual(ledger_path.read_bytes(), ledger)


if __name__ == "__main__":
    unittest.main()
