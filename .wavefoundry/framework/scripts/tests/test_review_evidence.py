from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

import review_evidence as subject  # noqa: E402
from wave_lint_lib.wave_validators import check_wave_docs  # noqa: E402


def review_run(
    run_id: str = "run-0",
    *,
    kind: str = "initial_delivery",
    cycle: int = 0,
    candidates: list[str] | None = None,
    **extra: object,
) -> dict[str, object]:
    return {
        "record_type": "review_run",
        "review_run_id": run_id,
        "run_kind": kind,
        "cycle": cycle,
        "candidate_finding_ids": ["finding-1"] if candidates is None else candidates,
        "source_record_ids": [f"source-{run_id}"],
        "dedup_evidence_id": f"dedup-{run_id}",
        **extra,
    }


def synthesis(
    record_id: str = "synthesis-0",
    *,
    run_id: str = "run-0",
    finding_id: str = "finding-1",
    cycle: int = 0,
    **overrides: object,
) -> dict[str, object]:
    row: dict[str, object] = {
        "record_type": "finding_synthesis",
        "record_id": record_id,
        "review_run_id": run_id,
        "cycle": cycle,
        "finding_id": finding_id,
        "validation_status": "real",
        "scope_relation": "admitted",
        "introduced_or_worsened_by_wave": False,
        "contract_relevance": "important_ac",
        "supported_reachability": False,
        "attacker_reachability": False,
        "authority_domain": "none",
        "authority_delta": "none",
        "observable_impact": "low",
        "containment": "preventive",
        "fix_risk": "comparable",
        "optional_value": "positive",
        "repair_scope_bounded": True,
        "repair_safety": "safe",
        "benefit_vs_fix_risk": "greater",
        "rejection_basis": "none",
        "disposition": "maybe_later",
        "blocking": False,
        "source_lanes": ["code-reviewer"],
        "blocking_required_lanes": [],
        "approval_recheck_lanes": ["code-reviewer"],
        "contract_or_required_ac_semantics_changed": False,
        "trust_boundary_changed": False,
        "architecture_or_ownership_changed": False,
        "cross_component_protocol_or_state_changed": False,
        "failure_or_readiness_semantics_changed": False,
        "review_depth": "focused",
        "repair_execution_state": "pending",
        "evidence_record_id": f"evidence-{record_id}",
        "decision_authority": "moderator",
        "disposition_rationale": "bounded optional value is worth completing now",
    }
    row.update(overrides)
    return row


def executable_evidence(
    evidence_id: str,
    claim_id: str,
    *,
    claim_kind: str = "finding",
    phase: str = "delivery",
    execution_status: str = "executed",
    actor: str = "qa-reviewer",
    fresh_context: bool = True,
    independent: bool = True,
    **overrides: object,
) -> dict[str, object]:
    row: dict[str, object] = {
        "record_type": "executable_evidence",
        "evidence_record_id": evidence_id,
        "claim_id": claim_id,
        "claim_kind": claim_kind,
        "required_for_approval": False,
        "phase": phase,
        "proposition": f"{claim_id} is reproduced through the named path",
        "counterexample_or_failure_condition": "the public result differs from the contract",
        "execution_status": execution_status,
        "public_path": "test public path",
        "command_or_fixture": "ReviewEvidenceStateMachineTests",
        "expected": "contract result",
        "observed": "contract result observed",
        "artifact_or_test_id": f"test:{evidence_id}",
        "adjacent_controls": ["stable control"],
        "test_ran_without_unintended_skip": True,
        "public_path_reached": True,
        "boundary_values_realistic": True,
        "assertions_non_vacuous": True,
        "known_bad_detected": True,
        "known_bad_detection_method": "focused injected old behavior",
        "limitations": "temporary local fixture only",
        "safety_and_authorization": "local disposable fixture; no external effects",
        "probe_class": "local_safe",
        "authorization_status": "not_required",
        "safe_boundary": False,
        "unexecuted_remainder_prohibited": False,
        "universal_claim": False,
        "verification_context": {
            "actor": actor,
            "context_id": f"context-{evidence_id}",
            "fresh_context": fresh_context,
            "independent": independent,
        },
    }
    row.update(overrides)
    return row


def derive(row: dict[str, object]) -> dict[str, object]:
    row["disposition"] = subject.derive_disposition(row)
    row["blocking"] = subject.derive_blocking(row)
    row["review_depth"] = subject.derive_review_depth(row)
    return row


def closed_census(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "claim": "all registered writers are enumerated",
        "boundary": "temporary repository production paths",
        "inclusion_policy": "production included; tests and generated files excluded",
        "tools_and_queries": ["AST writer census"],
        "enumerated_sites": ["writer_a", "writer_b"],
        "total_count": 2,
        "registration_checks": ["public registration table checked"],
        "exclusions": ["tests: outside production claim"],
        "result_truncated": False,
        "index_freshness": "current",
        "tool_errors": [],
        "residual_uncertainty": "none",
        "residual_uncertainty_status": "none",
        "universe_closed": True,
    }
    row.update(overrides)
    return row


def validate_records(
    records: list[dict[str, object]], *, closure: bool = False
) -> subject.ReviewEvidenceValidation:
    """Validate canonical records directly (the inline wave.md container was
    deleted in wave 1to78; events.jsonl is the only physical container)."""
    errors = subject.validate_review_evidence_records(records, closure=closure)
    return subject.ReviewEvidenceValidation(
        subject.PROTOCOL_VERSION, tuple(records), tuple(errors)
    )


def wave_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Expand shorthand rows with the implied dedup/finding evidence rows."""
    existing_evidence = {
        str(record.get("evidence_record_id"))
        for record in records
        if record.get("record_type") == "executable_evidence"
    }
    expanded: list[dict[str, object]] = []
    for record in records:
        if record.get("record_type") == "review_run":
            evidence_id = str(record.get("dedup_evidence_id"))
            if evidence_id not in existing_evidence:
                expanded.append(executable_evidence(evidence_id, evidence_id, claim_kind="dedup"))
                existing_evidence.add(evidence_id)
        elif record.get("record_type") == "finding_synthesis":
            evidence_id = str(record.get("evidence_record_id"))
            if evidence_id not in existing_evidence:
                expanded.append(executable_evidence(evidence_id, str(record.get("finding_id"))))
                existing_evidence.add(evidence_id)
        expanded.append(record)
    return expanded


def _publication_lock_worker(
    root: str,
    barrier: object,
    outcomes: object,
) -> None:
    # Hold the publication lock briefly; overlapping holders would both be
    # inside the critical section at once, which the shared counter detects.
    barrier.wait()
    marker = Path(root) / "critical-section.marker"
    with subject.project_state_publication_lock(Path(root)):
        if marker.exists():
            outcomes.put("overlap")
            return
        marker.write_text("held", encoding="utf-8")
        time.sleep(0.2)
        marker.unlink()
    outcomes.put("clean")


class ReviewEvidenceStateMachineTests(unittest.TestCase):
    def validate(self, records: list[dict[str, object]], **kwargs: object) -> subject.ReviewEvidenceValidation:
        if kwargs.get("closure") and not any(
            record.get("record_type") == "executable_evidence"
            and record.get("claim_kind") == "approval"
            and record.get("required_for_approval") is True
            for record in records
        ):
            records = [
                executable_evidence(
                    "approval-test",
                    "approval:operator-signoff",
                    claim_kind="approval",
                    required_for_approval=True,
                ),
                *records,
            ]
        return validate_records(wave_records(records), **kwargs)

    def assert_valid(self, records: list[dict[str, object]], **kwargs: object) -> None:
        result = self.validate(records, **kwargs)
        self.assertTrue(result.ok, "\n".join(result.errors))

    def assert_error(self, records: list[dict[str, object]], fragment: str, **kwargs: object) -> None:
        result = self.validate(records, **kwargs)
        self.assertFalse(result.ok)
        self.assertIn(fragment, "\n".join(result.errors))

    def test_actionable_completion_requires_reverification_during_normal_validation(self) -> None:
        impossible = synthesis(repair_execution_state="completed")
        result = validate_records(wave_records([review_run(), impossible]))
        self.assertIn("may be completed only by reverification", "\n".join(result.errors))

    def test_canonical_seed_states_load_bearing_validator_contract(self) -> None:
        """Contract-presence guard only; behavioral proof lives in the validator fixtures."""

        seed = (SCRIPTS_ROOT.parent / "seeds" / "209-agent-harness-core.prompt.md").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "`residual_uncertainty_status`",
            "`waiver_reason`",
            "`waiver_risk`",
            "`approval:<signoff-key>`",
            "earlier Executable Evidence Record with `claim_kind: finding`",
            "Lane reassessment evidence must name the original finding phase",
            "Mandatory project orientation may disclose status or review history",
            "formed its own current-tree/test assessment before relying on prior findings",
            "One physical batch run may start several findings",
            "ordered same-cycle `reverification` progress",
            "truthfully reclassifies the finding to `not_issue` or `dont_do_later`",
            "continue ordered same-cycle lane reverifications",
            "A later review pass may discover a new finding",
            "final outstanding reverification",
        ):
            self.assertIn(phrase, seed)

    def test_empty_ledger_is_valid_but_closure_requires_run(self) -> None:
        self.assert_valid([])
        self.assert_error([], "at least one Review Run Record", closure=True)

    def test_compact_empty_run_needs_no_dedup_evidence_row(self) -> None:
        rows, errors = subject.build_compact_review_event(
            [],
            {
                "event": "run",
                "actor": "wave-council",
                "context_id": "lightweight-review",
                "run_kind": "initial_delivery",
                "cycle": 0,
            },
        )
        self.assertEqual(errors, ())
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["dedup_evidence_id"])
        self.assertEqual(rows[0]["verification_context"]["actor"], "wave-council")
        self.assertEqual(
            rows[0]["verification_context"]["context_id"], "lightweight-review"
        )
        result = validate_records(list(rows))
        self.assertTrue(result.ok, "\n".join(result.errors))

    def test_compact_single_finding_reuses_its_evidence_as_universe_proof(self) -> None:
        event = {
            "event": "finding",
            "actor": "qa-reviewer",
            "context_id": "compact-finding",
            "finding_id": "public-path-regression",
            "run_kind": "initial_delivery",
            "cycle": 0,
            "judgment": {
                "validation_status": "real",
                "scope_relation": "admitted",
                "introduced_or_worsened_by_wave": True,
                "contract_relevance": "public_contract",
                "supported_reachability": True,
                "attacker_reachability": False,
                "authority_domain": "integrity",
                "authority_delta": "low",
                "observable_impact": "material",
                "containment": "none",
            },
            "proposition": "the public path must reject the invalid state",
            "failure_condition": "the public path returns success",
            "public_path": "wf_review_event",
            "command_or_fixture": "compact public-path fixture",
            "expected": "error",
            "observed": "success reproduced before repair",
            "artifact_or_test_id": "test:compact-finding",
            "known_bad_detection_method": "injected the pre-fix branch",
            "limitations": "temporary local wave",
            "safety_and_authorization": "local disposable fixture",
            "disposition_rationale": "introduced public-contract regression is actionable now",
            "integrity_confirmed": True,
            "review_boundaries_changed": [],
            "source_lanes": ["qa-reviewer"],
            "blocking_required_lanes": ["qa-reviewer"],
            "approval_recheck_lanes": ["qa-reviewer"],
        }
        rows, errors = subject.build_compact_review_event([], event)
        self.assertEqual(errors, ())
        self.assertEqual(len(rows), 3)
        evidence, run, synthesis_row = rows
        self.assertEqual(run["dedup_evidence_id"], evidence["evidence_record_id"])
        self.assertEqual(synthesis_row["disposition"], "do_now")
        result = validate_records(list(rows))
        self.assertTrue(result.ok, "\n".join(result.errors))
        table = subject.review_evidence_human_table(rows)
        self.assertIn("| public-path-regression | do_now | yes | pending | qa-reviewer |", table)

    def test_later_review_pass_can_discover_and_repair_new_findings(self) -> None:
        base_event = {
            "event": "finding",
            "actor": "qa-reviewer",
            "context_id": "looping-review",
            "finding_id": "finding-a",
            "run_kind": "initial_delivery",
            "cycle": 0,
            "judgment": {
                "validation_status": "real",
                "scope_relation": "admitted",
                "introduced_or_worsened_by_wave": True,
                "contract_relevance": "required_ac",
                "supported_reachability": True,
                "attacker_reachability": False,
                "authority_domain": "integrity",
                "authority_delta": "low",
                "observable_impact": "material",
                "containment": "none",
            },
            "proposition": "the changed behavior satisfies its required contract",
            "failure_condition": "the public path reproduces the defect",
            "public_path": "wf_review_event",
            "command_or_fixture": "looping review public-path fixture",
            "expected": "each later review finding remains recordable and repairable",
            "observed": "the controlled finding was reproduced",
            "artifact_or_test_id": "test:looping-review",
            "known_bad_detection_method": "the pre-fix authoring path rejected the later finding as a cycle decrease",
            "limitations": "local disposable event ledger",
            "safety_and_authorization": "local fixture only",
            "disposition_rationale": "a required-contract regression must be repaired now",
            "integrity_confirmed": True,
            "fresh_context": True,
            "independent": True,
            "review_boundaries_changed": [],
            "source_lanes": ["qa-reviewer"],
            "blocking_required_lanes": ["qa-reviewer"],
            "approval_recheck_lanes": ["qa-reviewer"],
        }

        records: tuple[dict[str, object], ...] = ()

        def append_event(**updates: object) -> tuple[dict[str, object], ...]:
            nonlocal records
            event = dict(base_event)
            event.update(updates)
            rows, errors = subject.build_compact_review_event(records, event)
            self.assertEqual(errors, ())
            records = (*records, *rows)
            result = validate_records(list(records))
            self.assertTrue(result.ok, "\n".join(result.errors))
            return rows

        append_event()
        # Canonical roles (wave 1tmb2): the implementer records repair_start;
        # the blocking reviewer lane reverifies from its own context.
        append_event(actor="implementer", run_kind="repair_start", cycle=1, context_id="repair-a")

        later = append_event(
            finding_id="finding-b",
            run_kind="initial_delivery",
            cycle=0,
            context_id="later-review-b",
        )
        self.assertNotIn("deviation_ids", later[1])
        append_event(
            finding_id="finding-b",
            actor="implementer",
            run_kind="repair_start",
            cycle=1,
            context_id="repair-b",
        )
        append_event(
            run_kind="reverification",
            cycle=1,
            context_id="verify-a",
            blocking_required_lanes=[],
        )
        completed_b = append_event(
            finding_id="finding-b",
            run_kind="reverification",
            cycle=1,
            context_id="verify-b",
            blocking_required_lanes=[],
        )
        self.assertEqual(
            [
                row["run_kind"]
                for row in completed_b
                if row.get("record_type") == "review_run"
            ],
            ["reverification"],
        )

        after_completed_cycle = append_event(
            finding_id="finding-c",
            run_kind="initial_delivery",
            cycle=0,
            context_id="later-review-c",
        )
        self.assertNotIn("deviation_ids", after_completed_cycle[1])
        repair_c = append_event(
            finding_id="finding-c",
            actor="implementer",
            run_kind="repair_start",
            cycle=2,
            context_id="repair-c",
        )
        self.assertNotIn("deviation_ids", repair_c[1])

    def test_compact_finding_can_report_vacuous_reviewed_evidence(self) -> None:
        """Integrity flags describe this finding's proof, not the defective evidence it reviews."""

        event = {
            "event": "finding",
            "actor": "qa-reviewer",
            "context_id": "vacuous-reviewed-evidence",
            "finding_id": "reviewed-assertion-is-vacuous",
            "run_kind": "initial_delivery",
            "cycle": 0,
            "judgment": {
                "validation_status": "real",
                "scope_relation": "admitted",
                "introduced_or_worsened_by_wave": True,
                "contract_relevance": "required_ac",
                "supported_reachability": True,
                "attacker_reachability": False,
                "authority_domain": "integrity",
                "authority_delta": "low",
                "observable_impact": "material",
                "containment": "none",
            },
            "proposition": "the reviewed approval evidence must contain a non-vacuous assertion",
            "failure_condition": "the reviewed fixture passes without checking the claimed behavior",
            "public_path": "review evidence inspection through the compact finding tool",
            "command_or_fixture": "execute the reviewed fixture and mutate the claimed result",
            "expected": "the mutation makes the reviewed fixture fail",
            "observed": "the reviewed fixture still passed because it asserted only that a response existed",
            "artifact_or_test_id": "qa:vacuous-reviewed-evidence",
            "known_bad_detection_method": "the controlled wrong result remained green in the reviewed fixture",
            "limitations": "the finding is scoped to the named reviewed fixture",
            "safety_and_authorization": "local disposable fixture only",
            "disposition_rationale": "vacuous required-AC evidence cannot carry approval",
            "integrity_confirmed": True,
            "review_boundaries_changed": [],
            "source_lanes": ["qa-reviewer"],
            "blocking_required_lanes": ["qa-reviewer"],
            "approval_recheck_lanes": ["qa-reviewer"],
        }
        rows, errors = subject.build_compact_review_event([], event)
        self.assertEqual(errors, ())
        evidence, _run, synthesis_row = rows
        self.assertTrue(evidence["assertions_non_vacuous"])
        self.assertIn("asserted only", evidence["observed"])
        self.assertEqual(synthesis_row["disposition"], "do_now")

    def test_compact_finding_never_defaults_load_bearing_judgment(self) -> None:
        rows, errors = subject.build_compact_review_event(
            [],
            {
                "event": "finding",
                "actor": "qa-reviewer",
                "context_id": "missing-judgment",
                "finding_id": "missing-facts",
                "run_kind": "initial_delivery",
                "cycle": 0,
                "judgment": {"validation_status": "real"},
            },
        )
        self.assertEqual(rows, ())
        self.assertIn("missing load-bearing fields", "\n".join(errors))

    def test_credible_threat_gate_missing_model_external_path_stays_security_affecting(self) -> None:
        """Control (a): a directly evidenced external actor stays severity-affecting.

        Even when a project documents no threat model, a grounded external-actor
        finding (untrusted input reaching a supported path, real authority delta)
        must still derive `do_now` and blocking — the gate reduces false positives,
        not real findings. There is NO character-count gate on the rationale, so a
        concise capability basis ("read API keys") is accepted, not rejected.
        """

        def external_finding(rationale: str) -> dict[str, object]:
            return {
                "event": "finding",
                "actor": "security-reviewer",
                "context_id": "credible-external-threat",
                "finding_id": "untrusted-archive-path-escape",
                "run_kind": "initial_delivery",
                "cycle": 0,
                "judgment": {
                    "validation_status": "real",
                    "scope_relation": "admitted",
                    "introduced_or_worsened_by_wave": True,
                    "contract_relevance": "important_ac",
                    "supported_reachability": True,
                    "attacker_reachability": True,
                    "authority_domain": "integrity",
                    "authority_delta": "material",
                    "observable_impact": "material",
                    "containment": "none",
                },
                "proposition": "an unpacked untrusted archive must not write outside the target root",
                "failure_condition": "a crafted archive entry writes outside the allowed root",
                "public_path": "wf_upgrade archive extraction",
                "command_or_fixture": "extract a fixture archive with a ../ entry",
                "expected": "extraction refuses the escaping entry",
                "observed": "the escaping entry wrote outside the root before repair",
                "artifact_or_test_id": "security:untrusted-archive-path-escape",
                "known_bad_detection_method": "injected the pre-fix extraction branch",
                "limitations": "temporary local wave",
                "safety_and_authorization": "local disposable fixture",
                "disposition_rationale": rationale,
                "integrity_confirmed": True,
                "review_boundaries_changed": [],
                "source_lanes": ["security-reviewer"],
                "blocking_required_lanes": ["security-reviewer"],
                "approval_recheck_lanes": ["security-reviewer"],
            }

        # A grounded external finding derives do_now + blocking. The rationale here is
        # a valid CONCISE capability basis — proving the removed char-count heuristic
        # no longer rejects short, specific bases.
        rows, errors = subject.build_compact_review_event([], external_finding("read API keys"))
        self.assertEqual(errors, ())
        _evidence, _run, synthesis_row = rows
        self.assertEqual(synthesis_row["disposition"], "do_now")
        self.assertTrue(synthesis_row["blocking"])
        self.assertTrue(synthesis_row["attacker_reachability"])

        # And generic filler that names no actor/capability is NOT rejected by any
        # machine check either — the capability-naming requirement is reviewer-owned
        # (semantic), stated in the seeds, not enforced by rationale length here.
        rows, errors = subject.build_compact_review_event(
            [], external_finding("this material impact is important and must be addressed now")
        )
        self.assertEqual(errors, ())

    def test_credible_threat_gate_trusted_operator_owned_state_stays_correctness_only(self) -> None:
        """Control (b): trusted operator-owned local state is correctness-only.

        A defect whose only controlling actor is trusted (operator/same-user) has
        `attacker_reachability=false` and `authority_delta=none`; it stays `do_now`
        purely on required-AC/correctness grounds, NOT via the security-severity
        path. This is the reclassification shape for the three `1slep` findings.
        """

        event = {
            "event": "finding",
            "actor": "security-reviewer",
            "context_id": "trusted-operator-owned-finding",
            "finding_id": "wave-directory-symlink-escape",
            "run_kind": "initial_delivery",
            "cycle": 0,
            "judgment": {
                "validation_status": "real",
                "scope_relation": "admitted",
                "introduced_or_worsened_by_wave": True,
                "contract_relevance": "required_ac",
                "supported_reachability": True,
                "attacker_reachability": False,
                "authority_domain": "integrity",
                "authority_delta": "none",
                "observable_impact": "low",
                "containment": "none",
            },
            "proposition": "wave directory resolution must stay inside docs/waves",
            "failure_condition": "a wave path escapes docs/waves",
            "public_path": "wave directory resolution",
            "command_or_fixture": "resolve a wave path with a traversal segment",
            "expected": "resolution is contained",
            "observed": "the traversal escaped before repair",
            "artifact_or_test_id": "security:wave-directory-symlink-escape",
            "known_bad_detection_method": "injected the pre-fix resolution branch",
            "limitations": "temporary local wave",
            "safety_and_authorization": "local disposable fixture",
            "disposition_rationale": "root containment required-AC",
            "integrity_confirmed": True,
            "review_boundaries_changed": [],
            "source_lanes": ["security-reviewer"],
            "blocking_required_lanes": ["security-reviewer"],
            "approval_recheck_lanes": ["security-reviewer"],
        }
        rows, errors = subject.build_compact_review_event([], event)
        self.assertEqual(errors, ())
        _evidence, _run, synthesis_row = rows
        # do_now on required-AC/correctness grounds, with the security fields cleared.
        self.assertEqual(synthesis_row["disposition"], "do_now")
        self.assertFalse(synthesis_row["attacker_reachability"])
        self.assertEqual(synthesis_row["authority_delta"], "none")
        self.assertEqual(synthesis_row["contract_relevance"], "required_ac")

    def test_compact_finding_requires_an_originating_lane(self) -> None:
        event = {
            "event": "finding",
            "actor": "qa-reviewer",
            "context_id": "missing-source-lane",
            "finding_id": "missing-source-lane",
            "run_kind": "initial_delivery",
            "cycle": 0,
            "judgment": {
                "validation_status": "invalid",
                "scope_relation": "admitted",
                "introduced_or_worsened_by_wave": False,
                "contract_relevance": "none",
                "supported_reachability": False,
                "attacker_reachability": False,
                "authority_domain": "none",
                "authority_delta": "none",
                "observable_impact": "none",
                "containment": "preventive",
            },
            "source_lanes": [],
            "blocking_required_lanes": [],
            "approval_recheck_lanes": [],
            "review_boundaries_changed": [],
        }
        rows, errors = subject.build_compact_review_event([], event)
        self.assertEqual(rows, ())
        self.assertIn("source_lanes", "\n".join(errors))

    def test_compact_approval_refuses_wrong_or_non_independent_actor(self) -> None:
        base = {
            "event": "approval",
            "actor": "code-reviewer",
            "context_id": "approval-context",
            "signoff_key": "qa-reviewer",
            "observed": "passed",
            "artifact_or_test_id": "qa:approval",
            "integrity_confirmed": True,
            "fresh_context": True,
            "independent": True,
        }
        rows, errors = subject.build_compact_review_event([], base)
        self.assertEqual(rows, ())
        self.assertIn("approval actor", "\n".join(errors))

        base.update(actor="qa-reviewer", fresh_context=False)
        rows, errors = subject.build_compact_review_event([], base)
        self.assertEqual(rows, ())
        self.assertIn("fresh_context=true", "\n".join(errors))

    def test_human_table_reports_resolved_actionable_head_as_not_open(self) -> None:
        row = synthesis(
            finding_id="resolved-finding",
            disposition="do_now",
            blocking=True,
            repair_execution_state="completed",
            blocking_required_lanes=[],
        )
        table = subject.review_evidence_human_table([row])
        self.assertIn("| resolved-finding | do_now | no | completed |", table)

    def test_unknown_record_type_is_rejected(self) -> None:
        result = validate_records([{"record_type": "mystery"}])
        self.assertIn("unknown record_type", "\n".join(result.errors))

    def test_executable_evidence_is_linked_and_required_approval_must_execute(self) -> None:
        run = review_run()
        row = synthesis()
        missing = validate_records([run, row])
        self.assertIn("missing executable evidence", "\n".join(missing.errors))
        approval = executable_evidence(
            "approval-1",
            "delivery-approval",
            claim_kind="approval",
            required_for_approval=True,
            execution_status="inferred",
        )
        result = validate_records([approval])
        self.assertIn("must be executed in delivery", "\n".join(result.errors))
        self.assertIn("approval:<signoff-key>", "\n".join(result.errors))

    def test_synthesis_requires_prior_finding_evidence(self) -> None:
        run = review_run()
        row = synthesis()
        dedup = executable_evidence("dedup-run-0", "dedup-run-0", claim_kind="dedup")
        wrong_kind = executable_evidence(
            "evidence-synthesis-0", "finding-1", claim_kind="dedup"
        )
        result = validate_records(
            [dedup, run, wrong_kind, row]
        )
        self.assertIn("claim_kind `finding`", "\n".join(result.errors))

        finding = executable_evidence("evidence-synthesis-0", "finding-1")
        result = validate_records(
            [dedup, run, row, finding]
        )
        self.assertIn("cannot precede its executable finding evidence", "\n".join(result.errors))

    def test_universal_census_and_unsafe_probe_fail_closed(self) -> None:
        universal = executable_evidence(
            "census-1",
            "all-writers",
            claim_kind="census",
            universal_claim=True,
        )
        result = validate_records([universal])
        self.assertIn("requires a census object", "\n".join(result.errors))

        unsafe = executable_evidence(
            "unsafe-1",
            "remote-release",
            probe_class="external_or_destructive",
            authorization_status="not_authorized",
            execution_status="executed",
        )
        result = validate_records([unsafe])
        joined = "\n".join(result.errors)
        self.assertIn("requires explicit authorization", joined)
        self.assertIn("must remain inferred or unverified", joined)

    def test_executed_universal_census_requires_current_closed_exact_universe(self) -> None:
        for census, fragment in (
            (closed_census(index_freshness="stale"), "stale"),
            (closed_census(residual_uncertainty_status="unresolved"), "uncertain"),
            (closed_census(total_count=999), "enumerated_sites count"),
        ):
            evidence = executable_evidence(
                "census-closed",
                "all-writers",
                claim_kind="census",
                universal_claim=True,
                census=census,
            )
            result = validate_records([evidence])
            self.assertIn(fragment, "\n".join(result.errors))

        valid = executable_evidence(
            "census-valid",
            "all-writers",
            claim_kind="census",
            universal_claim=True,
            census=closed_census(),
        )
        self.assertTrue(validate_records([valid]).ok)

    def test_same_context_lane_reassessment_is_rejected(self) -> None:
        evidence = executable_evidence(
            "lane-1",
            "finding-1",
            claim_kind="lane_reassessment",
            fresh_context=False,
            independent=False,
        )
        result = validate_records([evidence])
        self.assertIn("must be fresh and independent", "\n".join(result.errors))

    def test_implementer_reference_probe_cannot_restore_withdrawn_lane_approval(self) -> None:
        # AC-3 machine-checkable ceiling: reference independence improves correctness evidence,
        # but an implementer's differential probe is still not independent approval.
        evidence = executable_evidence(
            "implementer-reference-1",
            "java-owner-parity",
            claim_kind="lane_reassessment",
            actor="implementer",
            fresh_context=True,
            independent=False,
            proposition="fallback and grammar-backed parser agree on exact owner identity",
            command_or_fixture="bounded differential Java owner fixture",
        )
        result = validate_records([evidence])
        self.assertIn("must be fresh and independent", "\n".join(result.errors))

    def test_required_approval_is_mandatory_at_closure(self) -> None:
        rows = [
            executable_evidence("dedup-empty", "dedup-empty", claim_kind="dedup"),
            review_run("initial-empty", candidates=[]),
        ]
        rows[-1]["dedup_evidence_id"] = "dedup-empty"
        result = validate_records(rows, closure=True)
        self.assertIn("required approval", "\n".join(result.errors))

    def test_skipped_vacuous_impossible_or_wrong_reason_evidence_is_not_executed(self) -> None:
        integrity_fields = (
            "test_ran_without_unintended_skip",
            "public_path_reached",
            "boundary_values_realistic",
            "assertions_non_vacuous",
            "known_bad_detected",
        )
        for field in integrity_fields:
            evidence = executable_evidence("integrity-1", field, **{field: False})
            result = validate_records([evidence])
            self.assertIn("all five evidence-integrity checks", "\n".join(result.errors), field)

    def test_publication_lock_is_cross_process_exclusive(self) -> None:
        # Wave 1tomw: two spawned OS processes contend on the real physical
        # lock carrier; a shared marker file detects any overlap inside the
        # critical section.
        with tempfile.TemporaryDirectory() as temp_dir:
            ctx = multiprocessing.get_context("spawn")
            barrier = ctx.Barrier(2)
            outcomes = ctx.Queue()
            processes = [
                ctx.Process(
                    target=_publication_lock_worker,
                    args=(temp_dir, barrier, outcomes),
                )
                for _ in range(2)
            ]
            for process in processes:
                process.start()
            for process in processes:
                process.join(20)
                self.assertEqual(process.exitcode, 0)
            results = [outcomes.get(timeout=5) for _ in range(2)]
            self.assertEqual(results, ["clean", "clean"])

    def test_sealed_candidate_universe_requires_exactly_one_row(self) -> None:
        self.assert_error([review_run(candidates=["a", "b"]), synthesis(finding_id="a")], "missing synthesis rows")
        self.assert_error(
            [review_run(candidates=["a"]), synthesis(finding_id="a"), synthesis("s2", finding_id="b")],
            "outside sealed candidates",
        )
        self.assert_error(
            [review_run(candidates=["a"]), synthesis(finding_id="a"), synthesis("s2", finding_id="a")],
            "duplicate synthesis rows",
        )

    def test_unknown_enum_and_unknown_trigger_are_rejected(self) -> None:
        bad_enum = synthesis(validation_status="plausible")
        self.assert_error([review_run(), bad_enum], "unknown value")
        bad_trigger = synthesis(new_full_council_trigger=True)
        self.assert_error([review_run(), bad_trigger], "unknown fields")

    def test_non_boolean_fact_is_rejected(self) -> None:
        row = synthesis(supported_reachability=0)
        self.assert_error([review_run(), row], "supported_reachability")

    def test_malformed_lists_report_errors_without_crashing(self) -> None:
        run = review_run(candidates=[{"not": "an id"}])  # type: ignore[list-item]
        row = synthesis(source_lanes=[{"not": "a lane"}])
        result = self.validate([run, row])
        self.assertFalse(result.ok)
        self.assertIn("string list", "\n".join(result.errors))

    def test_invalid_and_conforming_precede_all_actionable_facts(self) -> None:
        for status in ("invalid", "conforming"):
            row = synthesis(
                validation_status=status,
                contract_relevance="public_contract",
                supported_reachability=True,
                observable_impact="critical",
                containment="none",
                repair_execution_state="not_required",
            )
            derive(row)
            self.assertEqual(row["disposition"], "not_issue")
            self.assert_valid([review_run(), row])

    def test_supported_capability_absence_is_conforming_not_a_provider_failure(self) -> None:
        row = synthesis(
            validation_status="conforming",
            supported_reachability=False,
            attacker_reachability=False,
            observable_impact="none",
            optional_value="none",
            repair_execution_state="not_required",
        )
        derive(row)
        self.assertEqual((row["disposition"], row["blocking"]), ("not_issue", False))
        self.assert_valid([review_run(), row])

    def test_unsupported_payload_through_supported_entry_keeps_attacker_reachability(self) -> None:
        row = synthesis(
            validation_status="real",
            supported_reachability=True,
            attacker_reachability=True,
            authority_domain="integrity",
            authority_delta="material",
            observable_impact="material",
            containment="detect_only",
            optional_value="none",
        )
        derive(row)
        self.assertEqual((row["disposition"], row["blocking"]), ("do_now", True))
        self.assert_valid([review_run(), row])

    def test_required_contract_harmful_fix_stays_do_now_and_blocking(self) -> None:
        row = synthesis(
            contract_relevance="required_ac",
            fix_risk="higher",
            repair_safety="unsafe",
            optional_value="none",
        )
        derive(row)
        self.assertEqual(row["disposition"], "do_now")
        self.assertTrue(row["blocking"])
        self.assert_valid([review_run(), row])

    def test_supported_immaterial_regression_is_nonblocking_do_now(self) -> None:
        row = synthesis(
            introduced_or_worsened_by_wave=True,
            supported_reachability=True,
            observable_impact="low",
            optional_value="none",
        )
        derive(row)
        self.assertEqual((row["disposition"], row["blocking"]), ("do_now", False))
        self.assert_valid([review_run(), row])

    def test_material_detect_only_path_and_authority_gain_are_blocking(self) -> None:
        impact = synthesis(
            supported_reachability=True,
            observable_impact="material",
            containment="detect_only",
            authority_domain="integrity",
            optional_value="none",
        )
        derive(impact)
        self.assertTrue(impact["blocking"])
        authority = synthesis(
            supported_reachability=True,
            attacker_reachability=True,
            authority_domain="privilege",
            authority_delta="material",
            containment="impact_bounding",
            optional_value="none",
        )
        derive(authority)
        self.assertTrue(authority["blocking"])
        self.assert_valid([review_run(), impact])
        self.assert_valid([review_run(), authority])

    def test_low_authority_without_other_action_predicate_is_not_action_required(self) -> None:
        row = synthesis(
            supported_reachability=True,
            attacker_reachability=True,
            authority_domain="integrity",
            authority_delta="low",
            optional_value="none",
            rejection_basis="categorical",
            repair_execution_state="not_required",
        )
        derive(row)
        self.assertEqual((row["disposition"], row["blocking"]), ("dont_do_later", False))
        self.assert_valid([review_run(), row])

    def test_maybe_later_requires_every_typed_precondition(self) -> None:
        mutations = {
            "optional_value": "none",
            "repair_scope_bounded": False,
            "repair_safety": "unsafe",
            "scope_relation": "adjacent",
            "benefit_vs_fix_risk": "equal",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                row = synthesis(**{field: value, "rejection_basis": "categorical", "repair_execution_state": "not_required"})
                derive(row)
                self.assertEqual(row["disposition"], "dont_do_later")
                self.assert_valid([review_run(), row])

    def test_recorded_disposition_blocking_and_depth_must_equal_derivation(self) -> None:
        self.assert_error([review_run(), synthesis(disposition="do_now")], "disposition must be derived")
        self.assert_error([review_run(), synthesis(blocking=True)], "blocking must be derived")
        self.assert_error([review_run(), synthesis(review_depth="full")], "review_depth must be derived")

    def test_rejection_basis_and_promotion_trigger_rules(self) -> None:
        categorical = synthesis(
            optional_value="none",
            repair_execution_state="not_required",
            rejection_basis="categorical",
            disposition="dont_do_later",
            review_depth="none",
        )
        self.assert_valid([review_run(), categorical])
        for basis in ("insufficient_evidence", "unsupported_reachability", "disproportionate_repair"):
            row = copy.deepcopy(categorical)
            row["rejection_basis"] = basis
            self.assert_error([review_run(), row], "requires promotion_trigger")
            row["promotion_trigger"] = "new field evidence"
            self.assert_valid([review_run(), row])
        categorical["promotion_trigger"] = "should not exist"
        self.assert_error([review_run(), categorical], "promotion_trigger is not valid")

    def test_rejected_and_not_issue_rows_cannot_create_follow_on_debt(self) -> None:
        rejected = synthesis(
            optional_value="none",
            repair_execution_state="not_required",
            rejection_basis="categorical",
            disposition="dont_do_later",
            review_depth="none",
            follow_on_id="future-wave",
        )
        self.assert_error([review_run(), rejected], "must not create follow-on debt")

    def test_actionable_closure_requires_current_completion_not_historical_completion(self) -> None:
        pending = synthesis()
        self.assert_error([review_run(), pending], "before closure", closure=True)
        completed = synthesis(repair_execution_state="completed")
        self.assert_error([review_run(), completed], "only by reverification", closure=True)

        run1 = review_run("run-1", kind="repair_start", cycle=1)
        started = synthesis(
            "synthesis-1",
            run_id="run-1",
            cycle=1,
            supersedes_record_id="synthesis-0",
        )
        verify = review_run("verify-1", kind="reverification", cycle=1)
        repaired = synthesis(
            "synthesis-2",
            run_id="verify-1",
            cycle=1,
            supersedes_record_id="synthesis-1",
            repair_execution_state="completed",
        )
        self.assert_valid([review_run(), pending, run1, started, verify, repaired], closure=True)

    def test_operator_waiver_is_not_completion_and_keeps_derived_blocker(self) -> None:
        row = synthesis(
            contract_relevance="public_contract",
            optional_value="none",
            repair_execution_state="operator_waived",
            decision_authority="operator",
            waiver_id="waiver-1",
            waiver_scope="accept one scoped residual risk",
            waiver_reason="operator accepts the bounded compatibility tradeoff",
            waiver_risk="one named residual behavior remains",
        )
        derive(row)
        self.assertTrue(row["blocking"])
        self.assert_valid([review_run(), row], closure=True)
        row.pop("waiver_scope")
        self.assert_error([review_run(), row], "requires `waiver_scope`")

    def test_each_full_council_trigger_independently_derives_full(self) -> None:
        for trigger in subject.FULL_COUNCIL_TRIGGERS:
            with self.subTest(trigger=trigger):
                row = synthesis(**{trigger: True})
                derive(row)
                self.assertEqual(row["review_depth"], "full")
                self.assert_valid([review_run(), row])

    def test_supersession_must_follow_one_current_same_finding_head(self) -> None:
        run1 = review_run("run-1", kind="repair_start", cycle=1)
        disconnected = synthesis("s1", run_id="run-1", cycle=1)
        self.assert_error([review_run(), synthesis(), run1, disconnected], "must supersede current head")
        cross = synthesis(
            "s1", run_id="run-1", finding_id="finding-1", cycle=1, supersedes_record_id="other"
        )
        self.assert_error([review_run(), synthesis("other", finding_id="finding-2"), run1, cross], "outside sealed candidates")

    def test_required_lane_cannot_be_cleared_by_moderator_without_evidence(self) -> None:
        initial = synthesis(
            contract_relevance="required_ac",
            blocking_required_lanes=["qa-reviewer"],
            source_lanes=["qa-reviewer"],
            optional_value="none",
        )
        derive(initial)
        run1 = review_run("run-1", kind="repair_start", cycle=1)
        repaired = synthesis(
            "s1",
            run_id="run-1",
            cycle=1,
            supersedes_record_id="synthesis-0",
            contract_relevance="required_ac",
            source_lanes=["qa-reviewer"],
            blocking_required_lanes=[],
            optional_value="none",
        )
        derive(repaired)
        self.assert_error([review_run(), initial, run1, repaired], "lane reassessment evidence")
        repaired["lane_reassessment_evidence_id"] = "qa-reviewer-replay-1"
        replay = executable_evidence(
            "qa-reviewer-replay-1",
            "finding-1",
            claim_kind="lane_reassessment",
            actor="qa-reviewer",
        )
        self.assert_valid([review_run(), initial, run1, replay, repaired])

    def test_lane_reassessment_is_exactly_linked_and_single_use(self) -> None:
        initial = synthesis(
            contract_relevance="required_ac",
            blocking_required_lanes=["qa-reviewer"],
            source_lanes=["qa-reviewer"],
            optional_value="none",
        )
        derive(initial)
        start = review_run("start-1", kind="repair_start", cycle=1)
        repaired = synthesis(
            "repaired-1",
            run_id="start-1",
            cycle=1,
            supersedes_record_id="synthesis-0",
            contract_relevance="required_ac",
            source_lanes=["qa-reviewer"],
            blocking_required_lanes=[],
            optional_value="none",
            lane_reassessment_evidence_id="replay-wrong",
        )
        derive(repaired)
        wrong = executable_evidence(
            "replay-wrong",
            "different-finding",
            claim_kind="lane_reassessment",
            actor="qa-reviewer",
        )
        self.assert_error(
            [review_run(), initial, start, wrong, repaired],
            "lane reassessment evidence",
        )

        two_lanes = copy.deepcopy(initial)
        two_lanes["source_lanes"] = ["qa-reviewer", "security-reviewer"]
        two_lanes["blocking_required_lanes"] = ["qa-reviewer", "security-reviewer"]
        repaired_two = copy.deepcopy(repaired)
        repaired_two["supersedes_record_id"] = "synthesis-0"
        right = executable_evidence(
            "replay-wrong",
            "finding-1",
            claim_kind="lane_reassessment",
            actor="qa-reviewer",
        )
        self.assert_error(
            [review_run(), two_lanes, start, right, repaired_two],
            "lane reassessment evidence",
        )

    def test_synthesis_cannot_precede_its_sealing_run(self) -> None:
        row = synthesis()
        result = validate_records(wave_records([row, review_run()]))
        self.assertIn("cannot precede its sealing review run", "\n".join(result.errors))


class ReviewEvidenceConvergenceTests(unittest.TestCase):
    def _cycle_records(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = [
            executable_evidence(
                "approval-cycle",
                "approval:operator-signoff",
                claim_kind="approval",
                required_for_approval=True,
            ),
            review_run(),
            synthesis(),
        ]
        head = "synthesis-0"
        for cycle in (1, 2):
            start_id = f"start-{cycle}"
            start_row_id = f"start-s-{cycle}"
            start = review_run(start_id, kind="repair_start", cycle=cycle)
            start_row = synthesis(
                start_row_id,
                run_id=start_id,
                cycle=cycle,
                supersedes_record_id=head,
            )
            verify_id = f"verify-{cycle}"
            verify_row_id = f"verify-s-{cycle}"
            verify = review_run(verify_id, kind="reverification", cycle=cycle)
            verify_row = synthesis(
                verify_row_id,
                run_id=verify_id,
                cycle=cycle,
                supersedes_record_id=start_row_id,
                repair_execution_state="completed",
            )
            rows.extend([start, start_row, verify, verify_row])
            head = verify_row_id
        checkpoint = review_run(
            "checkpoint-2",
            kind="convergence_checkpoint",
            cycle=2,
            frozen_boundary=["finding-1"],
        )
        checkpoint_row = synthesis(
            "checkpoint-s-2",
            run_id="checkpoint-2",
            cycle=2,
            supersedes_record_id=head,
            repair_execution_state="completed",
        )
        rows.extend([checkpoint, checkpoint_row])
        return rows

    def test_reverification_requires_repair_start_and_monotonic_cycle(self) -> None:
        rows = [review_run(), synthesis(), review_run("verify", kind="reverification", cycle=1)]
        rows.append(synthesis("verify-s", run_id="verify", cycle=1, supersedes_record_id="synthesis-0"))
        result = validate_records(wave_records(rows))
        self.assertIn("no preceding repair_start", "\n".join(result.errors))

    def test_missing_repair_start_error_names_the_corrective_call(self) -> None:
        """Wave 1tis9: the error must lead the caller to the fix, semantically.

        Asserts the corrective CONCEPTS are present (record a repair_start, as
        a finding event, with a cycle) rather than a brittle exact string.
        """
        rows = [review_run(), synthesis(), review_run("verify", kind="reverification", cycle=1)]
        rows.append(synthesis("verify-s", run_id="verify", cycle=1, supersedes_record_id="synthesis-0"))
        text = "\n".join(validate_records(wave_records(rows)).errors)
        self.assertIn("repair_start", text)
        self.assertIn('event="finding"', text)
        self.assertIn("cycle", text)

    def test_run_event_with_finding_run_kind_points_at_the_finding_form(self) -> None:
        """Wave 1tis9: event="run" with a repair run_kind self-corrects."""
        for run_kind in ("repair_start", "reverification"):
            _records, errors = subject.build_compact_review_event(
                (),
                {
                    "event": "run",
                    "actor": "implementer",
                    "context_id": f"ctx-{run_kind}",
                    "run_kind": run_kind,
                    "cycle": 1,
                },
            )
            text = "\n".join(errors)
            self.assertIn("finding event", text, run_kind)
            self.assertIn(run_kind, text)
            self.assertIn('event="finding"', text)

    def test_terminal_reverification_requires_fresh_independent_evidence(self) -> None:
        evidence = executable_evidence(
            "terminal-self-check",
            "finding-1",
            fresh_context=False,
            independent=False,
        )
        rows = [
            review_run(),
            synthesis(),
            review_run("start", kind="repair_start", cycle=1),
            synthesis(
                "start-row",
                run_id="start",
                cycle=1,
                supersedes_record_id="synthesis-0",
            ),
            evidence,
            review_run(
                "verify",
                kind="reverification",
                cycle=1,
                candidates=["finding-1"],
                source_record_ids=["terminal-self-check"],
                dedup_evidence_id="terminal-self-check",
            ),
            synthesis(
                "verify-row",
                run_id="verify",
                cycle=1,
                supersedes_record_id="start-row",
                blocking_required_lanes=[],
                repair_execution_state="completed",
                evidence_record_id="terminal-self-check",
            ),
        ]
        result = validate_records(wave_records(rows))
        self.assertIn(
            "requires fresh independent evidence", "\n".join(result.errors)
        )

    def test_repair_start_requires_initial_delivery_and_actionable_row(self) -> None:
        start = review_run("start", kind="repair_start", cycle=1)
        rejected = synthesis(
            "start-s",
            run_id="start",
            cycle=1,
            optional_value="none",
            rejection_basis="categorical",
            repair_execution_state="not_required",
            disposition="dont_do_later",
            review_depth="none",
        )
        result = validate_records(wave_records([start, rejected]))
        joined = "\n".join(result.errors)
        self.assertIn("preceding initial_delivery", joined)
        self.assertIn("requires an actionable synthesis", joined)

    def test_readiness_finding_may_start_repair_without_initial_delivery(self) -> None:
        initial = synthesis(
            contract_relevance="required_ac",
            supported_reachability=True,
            blocking_required_lanes=["code-reviewer"],
            approval_recheck_lanes=["wave-council-readiness"],
            optional_value="none",
        )
        derive(initial)
        start = review_run("readiness-start", kind="repair_start", cycle=1)
        start_row = synthesis(
            "readiness-start-row",
            run_id="readiness-start",
            cycle=1,
            supersedes_record_id="synthesis-0",
            contract_relevance="required_ac",
            supported_reachability=True,
            blocking_required_lanes=["code-reviewer"],
            approval_recheck_lanes=["wave-council-readiness"],
            optional_value="none",
        )
        derive(start_row)
        result = validate_records(
            wave_records([review_run(kind="readiness"), initial, start, start_row])
        )
        self.assertTrue(result.ok, "\n".join(result.errors))

    def _readiness_repair_records(
        self, *, origin_run_kind: str = "readiness"
    ) -> tuple[dict[str, object], ...]:
        approval_lane = (
            "wave-council-readiness"
            if origin_run_kind == "readiness"
            else "wave-council-delivery"
        )
        base_event: dict[str, object] = {
            "event": "finding",
            "actor": "code-reviewer",
            "context_id": "readiness-origin",
            "finding_id": "readiness-finding",
            "run_kind": origin_run_kind,
            "cycle": 0,
            "judgment": {
                "validation_status": "real",
                "scope_relation": "admitted",
                "introduced_or_worsened_by_wave": True,
                "contract_relevance": "required_ac",
                "supported_reachability": True,
                "attacker_reachability": False,
                "authority_domain": "integrity",
                "authority_delta": "low",
                "observable_impact": "material",
                "containment": "none",
            },
            "proposition": "readiness findings clear in their origin phase",
            "failure_condition": "the terminal reassessment is forced into delivery",
            "public_path": "wf_review_event",
            "command_or_fixture": "readiness repair compact-event sequence",
            "expected": "the readiness lane clears after independent reverification",
            "observed": "the controlled readiness finding is repairable",
            "artifact_or_test_id": "test:readiness-origin-repair",
            "known_bad_detection_method": "the pre-repair validator rejects the readiness reassessment phase",
            "limitations": "local deterministic event sequence",
            "safety_and_authorization": "local fixture only",
            "disposition_rationale": "a required readiness-contract defect must be repaired now",
            "integrity_confirmed": True,
            "fresh_context": True,
            "independent": True,
            "review_boundaries_changed": [],
            "source_lanes": ["code-reviewer"],
            "blocking_required_lanes": ["code-reviewer"],
            "approval_recheck_lanes": [approval_lane],
        }
        records: tuple[dict[str, object], ...] = ()

        def append(**updates: object) -> None:
            nonlocal records
            event = copy.deepcopy(base_event)
            event.update(updates)
            rows, errors = subject.build_compact_review_event(records, event)
            self.assertEqual(errors, ())
            records = (*records, *rows)

        append()
        append(
            actor="implementer",
            context_id="readiness-repair",
            run_kind="repair_start",
            cycle=1,
            fresh_context=False,
            independent=False,
        )
        append(
            actor="code-reviewer",
            context_id="readiness-reverification",
            run_kind="reverification",
            cycle=1,
            blocking_required_lanes=[],
        )
        return records

    def test_readiness_finding_clears_lane_through_same_phase_reverification(self) -> None:
        """1tmb0 AC-2: execute the full readiness repair sequence."""
        records = self._readiness_repair_records()
        reassessments = [
            row
            for row in records
            if row.get("record_type") == "executable_evidence"
            and row.get("claim_kind") == "lane_reassessment"
        ]
        self.assertEqual(len(reassessments), 1)
        self.assertEqual(reassessments[0]["phase"], "readiness")
        result = validate_records(wave_records(list(records)))
        self.assertTrue(result.ok, "\n".join(result.errors))

    def test_readiness_finding_accepts_legacy_delivery_reassessment(self) -> None:
        """Closed historical waves may promote readiness repairs at delivery."""
        records = [copy.deepcopy(row) for row in self._readiness_repair_records()]
        for row in records:
            if (
                row.get("record_type") == "executable_evidence"
                and row.get("claim_kind") == "lane_reassessment"
            ):
                row["phase"] = "delivery"
        result = validate_records(wave_records(records))
        self.assertTrue(result.ok, "\n".join(result.errors))

    def test_delivery_finding_rejects_readiness_reassessment(self) -> None:
        """Negative control: a delivery finding cannot clear in an earlier phase."""
        records = [
            copy.deepcopy(row)
            for row in self._readiness_repair_records(origin_run_kind="initial_delivery")
        ]
        for row in records:
            if (
                row.get("record_type") == "executable_evidence"
                and row.get("claim_kind") == "lane_reassessment"
            ):
                row["phase"] = "readiness"
        result = validate_records(wave_records(records))
        self.assertFalse(result.ok)
        self.assertIn(
            "cannot clear a required-lane block without lane reassessment evidence",
            "\n".join(result.errors),
        )

    def test_orphan_evidence_cannot_spoof_finding_origin_phase(self) -> None:
        """An unlinked row cannot relabel a delivery finding as readiness-origin."""
        records = [
            copy.deepcopy(row)
            for row in self._readiness_repair_records(origin_run_kind="initial_delivery")
        ]
        finding_evidence = next(
            row
            for row in records
            if row.get("record_type") == "executable_evidence"
            and row.get("claim_kind") == "finding"
        )
        orphan = copy.deepcopy(finding_evidence)
        orphan["evidence_record_id"] = "ev-orphan-readiness-phase-spoof"
        orphan["phase"] = "readiness"
        for row in records:
            if (
                row.get("record_type") == "executable_evidence"
                and row.get("claim_kind") == "lane_reassessment"
            ):
                row["phase"] = "readiness"
        result = validate_records(wave_records([orphan, *records]))
        self.assertFalse(result.ok)
        self.assertIn(
            "cannot clear a required-lane block without lane reassessment evidence",
            "\n".join(result.errors),
        )

    def test_reordered_repair_synthesis_cannot_spoof_origin_phase(self) -> None:
        """Physical synthesis order cannot override the linked chain root."""
        records = [
            copy.deepcopy(row)
            for row in self._readiness_repair_records(origin_run_kind="initial_delivery")
        ]
        syntheses = [row for row in records if row.get("record_type") == "finding_synthesis"]
        root = next(row for row in syntheses if row.get("supersedes_record_id") is None)
        repair = next(row for row in syntheses if row.get("supersedes_record_id") == root["record_id"])
        repair_evidence_id = repair["evidence_record_id"]
        for row in records:
            if row.get("evidence_record_id") == repair_evidence_id:
                row["phase"] = "readiness"
            if (
                row.get("record_type") == "executable_evidence"
                and row.get("claim_kind") == "lane_reassessment"
            ):
                row["phase"] = "readiness"
        records.remove(root)
        records.insert(records.index(repair) + 1, root)
        result = validate_records(wave_records(records))
        self.assertFalse(result.ok)
        self.assertIn(
            "cannot clear a required-lane block without lane reassessment evidence",
            "\n".join(result.errors),
        )

    def test_root_evidence_phase_cannot_override_sealing_run(self) -> None:
        """The root run, not a mutable evidence field, owns finding phase."""
        records = [
            copy.deepcopy(row)
            for row in self._readiness_repair_records(origin_run_kind="initial_delivery")
        ]
        root = next(
            row
            for row in records
            if row.get("record_type") == "finding_synthesis"
            and row.get("supersedes_record_id") is None
        )
        root_evidence_id = root["evidence_record_id"]
        for row in records:
            if row.get("evidence_record_id") == root_evidence_id:
                row["phase"] = "readiness"
            if (
                row.get("record_type") == "executable_evidence"
                and row.get("claim_kind") == "lane_reassessment"
            ):
                row["phase"] = "readiness"
        result = validate_records(wave_records(records))
        self.assertFalse(result.ok)
        self.assertIn(
            "cannot clear a required-lane block without lane reassessment evidence",
            "\n".join(result.errors),
        )

    def test_convergence_checkpoint_requires_two_completed_cycles(self) -> None:
        rows = [
            review_run(),
            synthesis(),
            review_run("checkpoint", kind="convergence_checkpoint", cycle=2, frozen_boundary=["finding-1"]),
            synthesis("checkpoint-s", run_id="checkpoint", cycle=2, supersedes_record_id="synthesis-0"),
        ]
        result = validate_records(wave_records(rows))
        self.assertIn("two completed repair cycles", "\n".join(result.errors))

    def test_pending_reverification_does_not_complete_a_cycle(self) -> None:
        rows = self._cycle_records()
        for row in rows:
            if row.get("record_type") == "finding_synthesis" and row.get("review_run_id") in {
                "verify-1",
                "verify-2",
                "checkpoint-2",
            }:
                row["repair_execution_state"] = "pending"
        result = validate_records(wave_records(rows))
        joined = "\n".join(result.errors)
        self.assertIn("repair cycle 2 starts before cycle 1 completes", joined)
        self.assertIn("two completed repair cycles", joined)

    def test_multiple_findings_share_cycle_and_complete_aggregate(self) -> None:
        initial_run = review_run(
            "initial-batch", candidates=["finding-a", "finding-b"]
        )
        initial_a = synthesis(
            "initial-a", run_id="initial-batch", finding_id="finding-a"
        )
        initial_b = synthesis(
            "initial-b", run_id="initial-batch", finding_id="finding-b"
        )
        start_a = review_run(
            "start-a", kind="repair_start", cycle=1, candidates=["finding-a"]
        )
        start_a_row = synthesis(
            "start-a-row",
            run_id="start-a",
            finding_id="finding-a",
            cycle=1,
            supersedes_record_id="initial-a",
        )
        start_b = review_run(
            "start-b", kind="repair_start", cycle=1, candidates=["finding-b"]
        )
        start_b_row = synthesis(
            "start-b-row",
            run_id="start-b",
            finding_id="finding-b",
            cycle=1,
            supersedes_record_id="initial-b",
        )
        verify_a = review_run(
            "verify-a", kind="reverification", cycle=1, candidates=["finding-a"]
        )
        verify_a_row = synthesis(
            "verify-a-row",
            run_id="verify-a",
            finding_id="finding-a",
            cycle=1,
            supersedes_record_id="start-a-row",
            repair_execution_state="completed",
        )
        premature_cycle_2 = review_run(
            "start-cycle-2",
            kind="repair_start",
            cycle=2,
            candidates=["finding-a"],
        )
        premature_cycle_2_row = synthesis(
            "start-cycle-2-row",
            run_id="start-cycle-2",
            finding_id="finding-a",
            cycle=2,
            supersedes_record_id="verify-a-row",
        )
        partial = [
            initial_run,
            initial_a,
            initial_b,
            start_a,
            start_a_row,
            start_b,
            start_b_row,
            verify_a,
            verify_a_row,
            premature_cycle_2,
            premature_cycle_2_row,
        ]
        result = validate_records(wave_records(partial))
        self.assertIn(
            "repair cycle 2 starts before cycle 1 completes",
            "\n".join(result.errors),
        )

        verify_b = review_run(
            "verify-b", kind="reverification", cycle=1, candidates=["finding-b"]
        )
        verify_b_row = synthesis(
            "verify-b-row",
            run_id="verify-b",
            finding_id="finding-b",
            cycle=1,
            supersedes_record_id="start-b-row",
            repair_execution_state="completed",
        )
        complete = partial[:-2] + [verify_b, verify_b_row]
        result = validate_records(wave_records(complete))
        self.assertTrue(result.ok, "\n".join(result.errors))

    def test_reverification_can_terminally_reclassify_started_finding(self) -> None:
        rows = [
            review_run(),
            synthesis(),
            review_run("start", kind="repair_start", cycle=1),
            synthesis(
                "start-row",
                run_id="start",
                cycle=1,
                supersedes_record_id="synthesis-0",
            ),
            review_run("verify", kind="reverification", cycle=1),
            synthesis(
                "verify-row",
                run_id="verify",
                cycle=1,
                supersedes_record_id="start-row",
                validation_status="conforming",
                optional_value="none",
                rejection_basis="none",
                repair_execution_state="not_required",
                disposition="not_issue",
                review_depth="none",
                approval_recheck_lanes=[],
                disposition_rationale="reverification disproved the reported behavior",
            ),
            review_run("cycle-2", kind="repair_start", cycle=2),
            synthesis(
                "cycle-2-row",
                run_id="cycle-2",
                cycle=2,
                supersedes_record_id="verify-row",
            ),
        ]
        result = validate_records(wave_records(rows))
        self.assertTrue(result.ok, "\n".join(result.errors))

    def test_duplicate_start_for_same_finding_in_cycle_fails(self) -> None:
        rows = [
            review_run(),
            synthesis(),
            review_run("start-a", kind="repair_start", cycle=1),
            synthesis(
                "start-a-row",
                run_id="start-a",
                cycle=1,
                supersedes_record_id="synthesis-0",
            ),
            review_run("start-b", kind="repair_start", cycle=1),
            synthesis(
                "start-b-row",
                run_id="start-b",
                cycle=1,
                supersedes_record_id="start-a-row",
            ),
        ]
        result = validate_records(wave_records(rows))
        self.assertIn(
            "more than one repair_start for `finding-1`",
            "\n".join(result.errors),
        )

    def test_completed_cycle_rejects_late_start_and_terminal_reverification(self) -> None:
        initial = review_run(
            "initial-batch", candidates=["finding-a", "finding-b"]
        )
        initial_a = synthesis(
            "initial-a", run_id="initial-batch", finding_id="finding-a"
        )
        initial_b = synthesis(
            "initial-b", run_id="initial-batch", finding_id="finding-b"
        )
        start = review_run(
            "start-a", kind="repair_start", cycle=1, candidates=["finding-a"]
        )
        start_row = synthesis(
            "start-a-row",
            run_id="start-a",
            finding_id="finding-a",
            cycle=1,
            supersedes_record_id="initial-a",
        )
        verify = review_run(
            "verify-a", kind="reverification", cycle=1, candidates=["finding-a"]
        )
        verify_row = synthesis(
            "verify-a-row",
            run_id="verify-a",
            finding_id="finding-a",
            cycle=1,
            supersedes_record_id="start-a-row",
            repair_execution_state="completed",
        )
        late_start = review_run(
            "late-start-b",
            kind="repair_start",
            cycle=1,
            candidates=["finding-b"],
        )
        late_start_row = synthesis(
            "late-start-b-row",
            run_id="late-start-b",
            finding_id="finding-b",
            cycle=1,
            supersedes_record_id="initial-b",
        )
        result = validate_records(
            wave_records(
                [
                    initial,
                    initial_a,
                    initial_b,
                    start,
                    start_row,
                    verify,
                    verify_row,
                    late_start,
                    late_start_row,
                ]
            )
        )
        self.assertIn(
            "cannot add a repair_start after aggregate completion",
            "\n".join(result.errors),
        )

        repeat = review_run(
            "verify-a-again",
            kind="reverification",
            cycle=1,
            candidates=["finding-a"],
        )
        repeat_row = synthesis(
            "verify-a-again-row",
            run_id="verify-a-again",
            finding_id="finding-a",
            cycle=1,
            supersedes_record_id="verify-a-row",
            repair_execution_state="completed",
        )
        result = validate_records(
            wave_records(
                [
                    initial,
                    initial_a,
                    initial_b,
                    start,
                    start_row,
                    verify,
                    verify_row,
                    repeat,
                    repeat_row,
                ]
            )
        )
        self.assertIn(
            "cannot reverify terminal finding `finding-a` again",
            "\n".join(result.errors),
        )

    def test_operator_waiver_is_distinct_cycle_terminal_state(self) -> None:
        waived = synthesis(
            "waived-row",
            run_id="waive-1",
            cycle=1,
            supersedes_record_id="start-row",
            contract_relevance="public_contract",
            optional_value="none",
            repair_execution_state="operator_waived",
            decision_authority="operator",
            waiver_id="waiver-cycle-1",
            waiver_scope="accept one scoped residual risk",
            waiver_reason="operator accepts the bounded compatibility tradeoff",
            waiver_risk="one named residual behavior remains",
        )
        derive(waived)
        rows = [
            executable_evidence(
                "approval-waiver-cycle",
                "approval:operator-signoff",
                claim_kind="approval",
                required_for_approval=True,
            ),
            review_run(),
            synthesis(),
            review_run("start-1", kind="repair_start", cycle=1),
            synthesis(
                "start-row",
                run_id="start-1",
                cycle=1,
                supersedes_record_id="synthesis-0",
            ),
            review_run("waive-1", kind="reverification", cycle=1),
            waived,
        ]
        result = validate_records(wave_records(rows), closure=True)
        self.assertTrue(result.ok, "\n".join(result.errors))
        self.assertEqual(waived["repair_execution_state"], "operator_waived")
        self.assertTrue(waived["blocking"])

    def test_legacy_batch_repair_runs_remain_valid(self) -> None:
        findings = ["finding-a", "finding-b", "finding-deferred"]
        initial = review_run("initial-batch", candidates=findings)
        initial_rows = [
            synthesis(
                f"initial-{finding}",
                run_id="initial-batch",
                finding_id=finding,
            )
            for finding in findings
        ]
        start = review_run(
            "start-batch", kind="repair_start", cycle=1, candidates=findings
        )
        start_rows = [
            synthesis(
                f"start-{finding}",
                run_id="start-batch",
                finding_id=finding,
                cycle=1,
                supersedes_record_id=f"initial-{finding}",
            )
            for finding in findings[:2]
        ]
        deferred = synthesis(
            "start-finding-deferred",
            run_id="start-batch",
            finding_id="finding-deferred",
            cycle=1,
            supersedes_record_id="initial-finding-deferred",
            optional_value="none",
            rejection_basis="categorical",
            disposition="dont_do_later",
            review_depth="none",
            repair_execution_state="not_required",
        )
        verify = review_run(
            "verify-batch",
            kind="reverification",
            cycle=1,
            candidates=findings[:2],
        )
        verify_rows = [
            synthesis(
                f"verify-{finding}",
                run_id="verify-batch",
                finding_id=finding,
                cycle=1,
                supersedes_record_id=f"start-{finding}",
                repair_execution_state="completed",
            )
            for finding in findings[:2]
        ]
        result = validate_records(
            wave_records(
                [
                    initial,
                    *initial_rows,
                    start,
                    *start_rows,
                    deferred,
                    verify,
                    *verify_rows,
                ]
            )
        )
        self.assertTrue(result.ok, "\n".join(result.errors))

    def test_two_cycles_and_checkpoint_are_valid(self) -> None:
        result = validate_records(wave_records(self._cycle_records()), closure=True)
        self.assertTrue(result.ok, "\n".join(result.errors))

    def test_legacy_checkpoint_synthesis_can_terminalize_cycle_two(self) -> None:
        rows = self._cycle_records()
        rows = [
            row
            for row in rows
            if row.get("review_run_id") not in {"verify-2", "checkpoint-2"}
            and row.get("review_run_id") != "checkpoint-2"
        ]
        start_two_index = next(
            index
            for index, row in enumerate(rows)
            if row.get("review_run_id") == "start-2"
            and row.get("record_type") == "finding_synthesis"
        )
        legacy_checkpoint = review_run(
            "legacy-checkpoint-2",
            kind="convergence_checkpoint",
            cycle=2,
            frozen_boundary=["finding-1"],
        )
        legacy_row = synthesis(
            "legacy-checkpoint-row-2",
            run_id="legacy-checkpoint-2",
            cycle=2,
            supersedes_record_id="start-s-2",
            repair_execution_state="completed",
        )
        rows[start_two_index + 1 :] = [legacy_checkpoint, legacy_row]
        result = validate_records(wave_records(rows))
        self.assertTrue(result.ok, "\n".join(result.errors))

    def test_two_completed_cycles_require_convergence_checkpoint(self) -> None:
        rows = self._cycle_records()[:-2]
        result = validate_records(wave_records(rows), closure=True)
        self.assertIn("require a convergence_checkpoint", "\n".join(result.errors))

    def test_frozen_boundary_requires_deviation_for_non_material_adjacency(self) -> None:
        rows = self._cycle_records()
        run3 = review_run("start-3", kind="repair_start", cycle=3, candidates=["finding-2"])
        new = synthesis("new-2", run_id="start-3", finding_id="finding-2", cycle=3)
        result = validate_records(wave_records([*rows, run3, new]))
        self.assertIn("exceeds frozen boundary", "\n".join(result.errors))
        run3["deviation_ids"] = ["finding-2"]
        result = validate_records(wave_records([*rows, run3, new]))
        self.assertTrue(result.ok, "\n".join(result.errors))

    def test_frozen_boundary_admits_safely_evidenced_material_blocker(self) -> None:
        rows = self._cycle_records()
        run3 = review_run("start-3", kind="repair_start", cycle=3, candidates=["finding-2"])
        new = synthesis(
            "new-2",
            run_id="start-3",
            finding_id="finding-2",
            cycle=3,
            supported_reachability=True,
            observable_impact="critical",
            containment="none",
            optional_value="none",
        )
        derive(new)
        result = validate_records(wave_records([*rows, run3, new]))
        self.assertTrue(result.ok, "\n".join(result.errors))


class ExternalReviewEventLedgerTests(unittest.TestCase):
    def make_external_wave(
        self, root: Path, records: tuple[dict[str, object], ...] = ()
    ) -> Path:
        wave_dir = root / "docs" / "waves" / "1test sample"
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave = wave_dir / "wave.md"
        wave.write_text(
            "# Wave\nreview-evidence-source: events.jsonl\n\n"
            + subject.empty_external_finding_synthesis_section(),
            encoding="utf-8",
        )
        (wave_dir / "events.jsonl").write_bytes(
            subject.canonical_review_events_bytes(records)
        )
        return wave

    def test_canonical_utf8_jsonl_round_trip_and_rejection_matrix(self) -> None:
        row = {"z": "café", "a": 1}
        canonical = b'{"a":1,"z":"caf\xc3\xa9"}\n'
        self.assertEqual(subject.canonical_review_event_bytes(row), canonical)
        records, errors = subject.parse_review_event_bytes(canonical)
        self.assertEqual(errors, ())
        self.assertEqual(records, (row,))

        rejected = {
            "BOM": b"\xef\xbb\xbf" + canonical,
            "CRLF": canonical[:-1] + b"\r\n",
            "blank": canonical + b"\n",
            "final LF": canonical[:-1],
            "canonical JSON": b'{"z":"caf\xc3\xa9", "a":1}\n',
            "duplicate object key": b'{"a":1,"a":2}\n',
            "non-finite": b'{"a":NaN}\n',
            "record must be an object": b'[]\n',
        }
        for fragment, payload in rejected.items():
            with self.subTest(fragment=fragment):
                parsed, parse_errors = subject.parse_review_event_bytes(payload)
                self.assertEqual(parsed, ())
                self.assertIn(fragment, "\n".join(parse_errors))

        with self.assertRaises(ValueError):
            subject.canonical_review_event_bytes({"not_finite": float("nan")})

    def test_no_prefix_proof_or_hash_authority_surface_remains(self) -> None:
        # Wave 1tomw (AC-4/AC-7): the events-only contract deliberately ships
        # no receipt, checkpoint, prefix hash, or hash-chain surface. Keep the
        # module's public API free of any resurrected proof helper.
        for name in (
            "review_event_prefix_proof",
            "adopted_protocol_state",
            "record_protocol_state",
            "record_protocol_state_locked",
            "validate_adopted_protocol_state",
            "externalize_adopted_inline_wave_locked",
            "adopted_legacy_inline_protocol_state_for_migration",
            "record_legacy_inline_protocol_state_for_migration",
            "ADOPTION_LEDGER_REL",
            "REVIEW_EVENT_HASH_DOMAIN",
        ):
            self.assertFalse(hasattr(subject, name), name)
            self.assertNotIn(name, subject.__all__)

    def test_source_declaration_and_fixed_sibling_path_are_exact(self) -> None:
        text = "# Wave\nreview-evidence-source: events.jsonl\n\n## Objective\n"
        self.assertEqual(subject.parse_review_evidence_source(text), ("events.jsonl", ()))
        for malformed in (
            "review-evidence-source: `events.jsonl`",
            "review-evidence-source: other.jsonl",
            "review-evidence-source:  events.jsonl",
        ):
            _, errors = subject.parse_review_evidence_source(f"# Wave\n{malformed}\n\n## Objective\n")
            self.assertTrue(errors, malformed)
        wave = Path("docs/waves/1test sample/wave.md")
        self.assertEqual(
            subject.review_event_path(wave),
            Path("docs/waves/1test sample/events.jsonl"),
        )
        with self.assertRaises(ValueError):
            subject.review_event_path(wave.parent / "chosen.jsonl")

    def test_external_validation_reads_events_not_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wave_dir = Path(temp_dir) / "docs" / "waves" / "1test sample"
            wave_dir.mkdir(parents=True)
            projection = subject.empty_external_finding_synthesis_section()
            wave = wave_dir / "wave.md"
            wave.write_text(
                "# Wave\nreview-evidence-source: events.jsonl\n\n" + projection,
                encoding="utf-8",
            )
            (wave_dir / "events.jsonl").write_bytes(b"")
            result = subject.validate_external_review_evidence(wave)
            self.assertTrue(result.ok, result.errors)
            self.assertEqual(result.records, ())
            wave.write_text(
                "# Wave\nreview-evidence-source: events.jsonl\n",
                encoding="utf-8",
            )
            missing = subject.validate_external_review_evidence(wave)
            self.assertFalse(missing.ok)
            self.assertEqual(missing.authority_errors, ())
            self.assertIn("Finding Synthesis", "\n".join(missing.projection_errors))
            wave.write_text(
                "# Wave\nreview-evidence-source: events.jsonl\n\n" + projection,
                encoding="utf-8",
            )
            stale = wave.read_text(encoding="utf-8").replace("0 records", "99 records")
            wave.write_text(stale, encoding="utf-8")
            self.assertTrue(subject.validate_external_review_evidence(wave).ok)
            (wave_dir / "events.jsonl").write_bytes(b"{}")
            self.assertIn(
                "final LF", "\n".join(subject.validate_external_review_evidence(wave).errors)
            )

    def test_declared_wave_must_not_retain_inline_marker_or_fence(self) -> None:
        """Negative guards (wave 1to78 census keeps): the retained-marker and
        retained-fence rejections are the live consumers of the module's
        marker and jsonl-fence patterns after the inline reader's deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wave_dir = Path(temp_dir) / "docs" / "waves" / "1test sample"
            wave_dir.mkdir(parents=True)
            (wave_dir / "events.jsonl").write_bytes(b"")
            wave = wave_dir / "wave.md"
            projection = subject.empty_external_finding_synthesis_section()
            wave.write_text(
                "# Wave\nreview-evidence-source: events.jsonl\n"
                "review-evidence-protocol: 1\n\n" + projection,
                encoding="utf-8",
            )
            retained = subject.validate_external_review_evidence(wave)
            self.assertIn(
                "must not retain review-evidence-protocol",
                "\n".join(retained.errors),
            )
            # Header-only: a prose mention in a body section is not a marker.
            wave.write_text(
                "# Wave\nreview-evidence-source: events.jsonl\n\n"
                + projection
                + "\n## Notes\n\nreview-evidence-protocol: 1\n",
                encoding="utf-8",
            )
            prose = subject.validate_external_review_evidence(wave)
            self.assertTrue(prose.ok, prose.errors)
            # Retained-fence rejection: an embedded jsonl fence inside the
            # projection is inline authority and fails closed.
            fenced = projection.replace(
                subject.FINDING_SYNTHESIS_MARKER_END,
                "```jsonl\n```\n" + subject.FINDING_SYNTHESIS_MARKER_END,
            )
            wave.write_text(
                "# Wave\nreview-evidence-source: events.jsonl\n\n" + fenced,
                encoding="utf-8",
            )
            embedded = subject.validate_external_review_evidence(wave)
            self.assertIn(
                "must not embed a jsonl authority",
                "\n".join(embedded.errors),
            )

    def test_undeclared_inline_marker_wave_fails_with_migration_path(self) -> None:
        """A 1.13-shaped wave (inline marker, inline fence, no declaration,
        no sibling ledger) fails closed with the actionable manual migration
        message and never silently reclassifies as legacy prose."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wave_dir = Path(temp_dir) / "docs" / "waves" / "1test sample"
            wave_dir.mkdir(parents=True)
            wave = wave_dir / "wave.md"
            wave.write_text(
                "# Wave\nreview-evidence-protocol: 1\n\n"
                "## Finding Synthesis\n\n"
                f"{subject.FINDING_SYNTHESIS_MARKER_BEGIN}\n"
                "```jsonl\n```\n"
                f"{subject.FINDING_SYNTHESIS_MARKER_END}\n",
                encoding="utf-8",
            )
            result = subject.validate_external_review_evidence(wave)
            self.assertFalse(result.ok)
            joined = "\n".join(result.errors)
            self.assertIn(
                "must declare `review-evidence-source: events.jsonl`", joined
            )
            self.assertIn("migrate manually", joined)
            self.assertIn("`events.jsonl` ledger", joined)

    def test_external_projection_contains_no_inline_jsonl_authority(self) -> None:
        base = (
            "# Wave\nreview-evidence-source: events.jsonl\n\n"
            + subject.empty_external_finding_synthesis_section()
            + "\n## Notes\nkeep me\n"
        )
        rendered = subject.render_review_evidence_projection(base, [synthesis()])
        self.assertNotIn("```jsonl", rendered)
        self.assertIn("Machine review evidence — 1 records", rendered)
        self.assertIn("## Notes\nkeep me", rendered)

    def test_external_projection_migrates_legacy_owned_markers(self) -> None:
        legacy = (
            "# Wave\nreview-evidence-source: events.jsonl\n\n"
            + subject.empty_external_finding_synthesis_section()
            .replace(
                "<!-- wave:finding-synthesis begin -->",
                "<!-- waveframework:finding-synthesis begin -->",
            )
            .replace(
                "<!-- wave:finding-synthesis end -->",
                "<!-- waveframework:finding-synthesis end -->",
            )
        )
        rendered = subject.render_review_evidence_projection(
            legacy, [synthesis()]
        )
        self.assertIn("<!-- wave:finding-synthesis begin -->", rendered)
        self.assertNotIn("waveframework:finding-synthesis", rendered)

    def test_external_projection_uses_plain_summary_without_html(self) -> None:
        """Wave 1tb4z: the external-ledger projection is plain markdown — the
        details wrapper collapsed nothing once records moved to events.jsonl."""
        base = (
            "# Wave\nreview-evidence-source: events.jsonl\n\n"
            + subject.empty_external_finding_synthesis_section()
            + "\n## Notes\nkeep me\n"
        )
        rendered = subject.render_review_evidence_projection(base, [synthesis()])
        self.assertIn("*Machine review evidence — 1 records", rendered)
        self.assertNotIn("<details", rendered)
        self.assertNotIn("<summary>", rendered)
        self.assertNotIn("wavefoundry-review-evidence", rendered)

    def test_legacy_bodyless_details_form_validates_without_rewrite(self) -> None:
        """Wave 1tb4z: an archived external projection in the retired
        details-wrapped form canonicalizes to the plain line, so the
        stale-projection equality holds without touching the file."""
        summary = subject.review_evidence_summary_line(())
        legacy = (
            "# Wave\nreview-evidence-source: events.jsonl\n\n"
            "## Finding Synthesis\n\n"
            "<!-- wave:finding-synthesis begin -->\n"
            f"{subject.review_evidence_human_table(())}\n\n"
            '<details class="wavefoundry-review-evidence">\n'
            f"<summary>{summary}</summary>\n"
            "</details>\n"
            "<!-- wave:finding-synthesis end -->\n"
        )
        canonical = subject.canonicalize_finding_synthesis_markers(legacy)
        self.assertNotIn("<details", canonical)
        self.assertIn(f"*{summary}*", canonical)
        expected = subject.render_review_evidence_projection(legacy, [])
        self.assertEqual(expected, canonical)

    def test_canonicalizer_never_collapses_bodied_inline_details(self) -> None:
        """An ARCHIVED inline-authority form keeps its details wrapper (it
        collapses a real JSONL body); only the class spelling normalizes.
        The literal fixture mirrors the 1.13-era on-disk shape — nothing in
        shipped code renders this form anymore (wave 1to78)."""
        inline = (
            "## Finding Synthesis\n\n"
            f"{subject.FINDING_SYNTHESIS_MARKER_BEGIN}\n"
            f"{subject.review_evidence_human_table(())}\n\n"
            '<details class="wavefoundry-review-evidence">\n'
            f"<summary>{subject.review_evidence_summary_line(())}</summary>\n\n"
            "```jsonl\n```\n"
            "</details>\n"
            f"{subject.FINDING_SYNTHESIS_MARKER_END}\n"
        )
        canonical = subject.canonicalize_finding_synthesis_markers(inline)
        self.assertIn('<details class="wave-review-evidence">', canonical)
        self.assertNotIn("wavefoundry-review-evidence", canonical)
        self.assertIn("```jsonl", canonical)
        self.assertIn("<summary>", canonical)

    def test_structured_identity_distinguishes_finding_and_lifecycle_variants(self) -> None:
        common = {
            "event": "finding",
            "actor": "qa|reviewer",
            "context_id": "context:one",
            "run_kind": "initial_delivery",
            "cycle": 0,
        }
        first = subject.derive_review_event_identity(
            "1test sample", {**common, "finding_id": "one|two"}
        )
        second = subject.derive_review_event_identity(
            "1test sample", {**common, "finding_id": "one", "context_id": "two|context:one"}
        )
        six = subject.derive_review_event_identity(
            "1testx sample", {**common, "finding_id": "one|two"}
        )
        self.assertNotEqual(first, second)
        self.assertEqual(first["wave_id"], "1test")
        self.assertEqual(six["wave_id"], "1testx")
        self.assertNotEqual(first, {**first, "finding_id": "other"})
        with self.assertRaises(ValueError):
            subject.derive_review_event_identity("1bad sample", {**common, "finding_id": "x"})

    def test_request_digest_normalizes_defaults_and_set_like_fields_only(self) -> None:
        base = {
            "event": "finding",
            "actor": "qa-reviewer",
            "context_id": "ctx",
            "finding_id": "finding",
            "run_kind": "initial_delivery",
            "cycle": 0,
            "source_lanes": ["security-reviewer", "qa-reviewer"],
            "review_boundaries_changed": ["trust_boundary_changed"],
            "adjacent_controls": ["first", "second"],
        }
        equivalent = {
            **base,
            "mode": "append",
            "fresh_context": False,
            "independent": False,
            "source_lanes": ["qa-reviewer", "security-reviewer", "qa-reviewer"],
            "execution_status": "executed",
            "probe_class": "local_safe",
            "authorization_status": "not_required",
            "safe_boundary": False,
            "unexecuted_remainder_prohibited": False,
            "universal_claim": False,
        }
        self.assertEqual(
            subject.review_event_request_digest(base),
            subject.review_event_request_digest(equivalent),
        )
        reordered_evidence = {**equivalent, "adjacent_controls": ["second", "first"]}
        self.assertNotEqual(
            subject.review_event_request_digest(base),
            subject.review_event_request_digest(reordered_evidence),
        )

    def test_new_bundles_have_leading_identity_but_migrated_rows_need_none(self) -> None:
        event = {
            "event": "run",
            "actor": "wave-council",
            "context_id": "retry-context",
            "run_kind": "initial_delivery",
            "cycle": 0,
        }
        rows, errors = subject.build_identified_review_event([], "1test sample", event)
        self.assertEqual(errors, ())
        self.assertIn("event_identity", rows[0])
        self.assertIn("request_digest", rows[0])
        self.assertEqual(subject.validate_review_evidence_records(rows), ())

        migrated, old_errors = subject.build_compact_review_event([], event)
        self.assertEqual(old_errors, ())
        self.assertNotIn("event_identity", migrated[0])
        self.assertEqual(subject.validate_review_evidence_records(migrated), ())
        broken = dict(rows[0])
        broken.pop("request_digest")
        self.assertIn(
            "must appear together",
            "\n".join(subject.validate_review_evidence_records([broken])),
        )

    def test_declared_wave_fails_closed_on_missing_or_damaged_authority(self) -> None:
        # Wave 1tomw (AC-2): the declared fixed sibling ledger is the sole
        # authority; missing, noncanonical, and declaration-tampered states
        # reject without consulting any receipt state or Git.
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wave = self.make_external_wave(root)
            original = wave.read_text(encoding="utf-8")
            self.assertTrue(subject.validate_external_review_evidence(wave).ok)

            (wave.parent / "events.jsonl").unlink()
            self.assertIn(
                "missing",
                "\n".join(subject.validate_external_review_evidence(wave).errors),
            )
            (wave.parent / "events.jsonl").write_bytes(b'{"a":1}\r\n')
            self.assertFalse(subject.validate_external_review_evidence(wave).ok)

            (wave.parent / "events.jsonl").write_bytes(b"")
            wave.write_text(
                original.replace("events.jsonl", "wrong.jsonl", 1), encoding="utf-8"
            )
            self.assertIn(
                "must be exactly",
                "\n".join(subject.validate_external_review_evidence(wave).errors),
            )

    def test_valid_older_ledger_rollback_is_not_locally_detectable(self) -> None:
        # Wave 1tomw (AC-9) negative control: restoring a complete OLDER but
        # internally valid ledger passes local structural validation — that is
        # the documented boundary (Git/backups are the optional history
        # authority), and this control prevents future overclaiming. The
        # damaged states in the companion test above remain rejected.
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            event = {
                "event": "run",
                "actor": "wave-council",
                "context_id": "ctx",
                "run_kind": "initial_delivery",
                "cycle": 0,
            }
            rows, errors = subject.build_identified_review_event([], "1test sample", event)
            self.assertEqual(errors, ())
            wave = self.make_external_wave(root)
            older_ledger = (wave.parent / "events.jsonl").read_bytes()

            newer = subject.canonical_review_events_bytes(rows)
            (wave.parent / "events.jsonl").write_bytes(newer)
            self.assertTrue(subject.validate_external_review_evidence(wave).ok)

            # Roll the whole ledger back to the older valid state: local
            # validation accepts it — deliberately, with no receipt to notice.
            (wave.parent / "events.jsonl").write_bytes(older_ledger)
            result = subject.validate_external_review_evidence(wave)
            self.assertTrue(result.ok, "\n".join(result.errors))
            self.assertEqual(result.records, ())

    def test_publication_lock_is_reentrant_and_cross_process_exclusive(self) -> None:
        # Wave 1tomw (AC-3): same-thread nesting must not deadlock, and the
        # physical carrier keeps the stable 1.14+ pathname while another
        # process is blocked out for the duration of the hold.
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with subject.project_state_publication_lock(root):
                with subject.project_state_publication_lock(root):
                    carrier = root / subject.PROJECT_STATE_PUBLICATION_LOCK_REL
                    self.assertTrue(carrier.exists())
                    self.assertEqual(
                        carrier.name, "review-evidence-adoptions.lock"
                    )
                    from runtime_lock import probe_runtime_lock

                    probe = probe_runtime_lock(carrier)
                    self.assertTrue(probe.held)
            probe = probe_runtime_lock(root / subject.PROJECT_STATE_PUBLICATION_LOCK_REL)
            self.assertFalse(probe.held)


class ReviewStatusProjectionTests(unittest.TestCase):
    def approval(self, key: str, *, actor: str | None = None) -> dict[str, object]:
        return executable_evidence(
            f"approval-{key}",
            f"approval:{key}",
            claim_kind="approval",
            actor=actor or ("wave-council" if key.startswith("wave-council-") else key),
            required_for_approval=True,
        )

    def test_signoff_keys_stay_distinct_even_when_actor_is_shared(self) -> None:
        rows = [
            self.approval("wave-council-readiness"),
            self.approval("wave-council-delivery"),
        ]
        states = {
            row["signoff_key"]: row["state"]
            for row in subject.review_status_rows(
                rows, ["wave-council-readiness", "wave-council-delivery"]
            )
        }
        self.assertEqual(
            states,
            {
                "wave-council-readiness": "approved",
                "wave-council-delivery": "approved",
            },
        )

    def test_pending_readiness_finding_withholds_readiness_approval(self) -> None:
        pending = synthesis(
            finding_id="plan-defect",
            contract_relevance="required_ac",
            supported_reachability=True,
            blocking_required_lanes=["code-reviewer"],
            approval_recheck_lanes=["wave-council-readiness"],
            optional_value="none",
        )
        derive(pending)
        rows = [self.approval("wave-council-readiness"), pending]
        [state] = subject.review_status_rows(rows, ["wave-council-readiness"])
        self.assertEqual(state["state"], "withheld")
        self.assertIn("plan-defect", state["why"])

    def test_readiness_approval_waits_for_every_current_finding_head(self) -> None:
        first = synthesis(
            "plan-first-0",
            finding_id="plan-first",
            contract_relevance="required_ac",
            supported_reachability=True,
            blocking_required_lanes=["code-reviewer"],
            approval_recheck_lanes=["wave-council-readiness"],
            optional_value="none",
        )
        second = synthesis(
            "plan-second-0",
            finding_id="plan-second",
            contract_relevance="required_ac",
            supported_reachability=True,
            blocking_required_lanes=["qa-reviewer"],
            approval_recheck_lanes=["wave-council-readiness"],
            optional_value="none",
        )
        derive(first)
        derive(second)
        first_done = synthesis(
            "plan-first-1",
            finding_id="plan-first",
            cycle=1,
            supersedes_record_id="plan-first-0",
            blocking_required_lanes=[],
            approval_recheck_lanes=["wave-council-readiness"],
            disposition="do_now",
            blocking=False,
            repair_execution_state="completed",
        )
        [still_withheld] = subject.review_status_rows(
            [first, second, first_done, self.approval("wave-council-readiness")],
            ["wave-council-readiness"],
        )
        self.assertEqual(still_withheld["state"], "withheld")
        self.assertIn("plan-second", still_withheld["why"])

        second_done = synthesis(
            "plan-second-1",
            finding_id="plan-second",
            cycle=1,
            supersedes_record_id="plan-second-0",
            blocking_required_lanes=[],
            approval_recheck_lanes=["wave-council-readiness"],
            disposition="do_now",
            blocking=False,
            repair_execution_state="completed",
        )
        [approved] = subject.review_status_rows(
            [first, second, first_done, second_done, self.approval("wave-council-readiness")],
            ["wave-council-readiness"],
        )
        self.assertEqual(approved["state"], "approved")

    def test_affected_repair_withholds_only_its_lane_and_names_recovery(self) -> None:
        rows = [
            self.approval("qa-reviewer"),
            self.approval("code-reviewer"),
            synthesis(
                "repair-1",
                cycle=1,
                finding_id="F-1",
                source_lanes=["qa-reviewer"],
                blocking_required_lanes=["qa-reviewer"],
                approval_recheck_lanes=["qa-reviewer"],
                disposition="do_now",
                blocking=True,
                repair_execution_state="completed",
            ),
        ]
        states = {
            row["signoff_key"]: row
            for row in subject.review_status_rows(
                rows, ["qa-reviewer", "code-reviewer"]
            )
        }
        self.assertEqual(states["qa-reviewer"]["state"], "withheld")
        self.assertIn("F-1", states["qa-reviewer"]["why"])
        self.assertIn("qa-reviewer", states["qa-reviewer"]["next_action"])
        self.assertEqual(states["code-reviewer"]["state"], "approved")

    def test_later_reapproval_restores_affected_lane(self) -> None:
        rows = [
            self.approval("qa-reviewer"),
            synthesis(
                "repair-1",
                cycle=1,
                finding_id="F-1",
                source_lanes=["qa-reviewer"],
                approval_recheck_lanes=["qa-reviewer"],
                disposition="do_now",
                blocking=True,
                repair_execution_state="completed",
            ),
            self.approval("qa-reviewer"),
        ]
        status = subject.review_status_rows(rows, ["qa-reviewer"])
        self.assertEqual(status[0]["state"], "approved")

    def test_nonblocking_current_finding_does_not_withhold_approval(self) -> None:
        rows = [
            self.approval("qa-reviewer"),
            synthesis(
                "nonblocking-1",
                cycle=1,
                finding_id="F-NONBLOCKING",
                source_lanes=["qa-reviewer"],
                approval_recheck_lanes=["qa-reviewer"],
                disposition="dont_do_later",
                blocking=False,
                repair_execution_state="not_required",
            ),
        ]
        status = subject.review_status_rows(rows, ["qa-reviewer"])
        self.assertEqual(status[0]["state"], "approved")
        self.assertNotIn("F-NONBLOCKING", status[0]["why"])

    def test_projection_replaces_generated_lines_but_preserves_human_prose(self) -> None:
        text = (
            "# Wave\n\n## Review Evidence\n\n"
            "- qa-reviewer: approved — old generated state\n"
            "- qa-reviewer was withdrawn during an exploratory review for context.\n"
            "- operator-signoff: <approved when operator confirms closure>\n\n"
            "## Dependencies\n\n- none\n"
        )
        rendered = subject.render_review_status_projection(
            text, [self.approval("qa-reviewer")], ["qa-reviewer", "operator-signoff"]
        )
        self.assertNotIn("old generated state", rendered)
        self.assertIn("withdrawn during an exploratory review", rendered)
        self.assertIn("<approved when operator confirms closure>", rendered)
        self.assertIn("| qa-reviewer | approved |", rendered)

    def test_malformed_or_duplicate_marker_fails_closed(self) -> None:
        text = (
            "# Wave\n\n## Review Evidence\n\n"
            f"{subject.REVIEW_STATUS_MARKER_BEGIN}\n"
            f"{subject.REVIEW_STATUS_MARKER_BEGIN}\n"
            f"{subject.REVIEW_STATUS_MARKER_END}\n"
        )
        with self.assertRaises(ValueError):
            subject.render_review_status_projection(text, [], ["operator-signoff"])

    def test_projection_size_is_bounded_by_current_heads_not_cycles(self) -> None:
        records: list[dict[str, object]] = []
        for cycle in range(100):
            records.append(
                synthesis(
                    f"repair-{cycle}",
                    cycle=cycle,
                    finding_id="F-1",
                    source_lanes=["qa-reviewer"],
                    approval_recheck_lanes=["qa-reviewer"],
                    disposition="do_now",
                    blocking=True,
                    repair_execution_state="completed",
                    supersedes_record_id=(
                        f"repair-{cycle - 1}" if cycle else None
                    ),
                )
            )
        table = subject.review_status_human_table(records, ["qa-reviewer"])
        self.assertLess(len(table), 700)
        self.assertIn("F-1", table)


class ReviewEvidenceLintIntegrationTests(unittest.TestCase):
    def test_external_ledger_symlink_is_rejected_as_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wave = root / "docs" / "waves" / "1test unsafe-ledger" / "wave.md"
            wave.parent.mkdir(parents=True)
            wave.write_text(
                "# Wave\n\nStatus: implementing\n"
                "review-evidence-source: events.jsonl\n\n"
                "## Review Evidence\n\n## Finding Synthesis\n\n",
                encoding="utf-8",
            )
            outside = root / "outside-events.jsonl"
            outside.write_bytes(b"")
            try:
                wave.parent.joinpath("events.jsonl").symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"file symlinks unavailable: {exc}")

            result = subject.validate_external_review_evidence(wave)

            self.assertFalse(result.ok)
            self.assertIn("events.jsonl may not be a symlink", "\n".join(result.errors))

    def test_wave_docs_routes_marked_records_through_shared_validator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wave = root / "docs" / "waves" / "1test integration" / "wave.md"
            wave.parent.mkdir(parents=True)
            wave.write_text(
                "# Wave Record\n\n"
                "Owner: Engineering\nStatus: planned\nLast verified: 2026-07-14\n"
                "review-evidence-source: events.jsonl\n"
                "wave-id: `1test integration`\nTitle: Integration\n\n"
                "## Objective\n\nExercise lint routing.\n\n"
                "## Changes\n\n"
                "## Journal Watchpoints\n\n- test\n\n"
                "## Participants\n\n- Coordinator: test\n\n"
                + subject.empty_external_finding_synthesis_section(),
                encoding="utf-8",
            )
            (wave.parent / "events.jsonl").write_text("{not-json}\n", encoding="utf-8")
            errors = check_wave_docs(root)
            self.assertTrue(any("review evidence" in error and "invalid JSON" in error for error in errors), errors)

class RepairReverificationIndependenceTests(unittest.TestCase):
    """1tmb2: chain-aware repair/reverification independence at the append seam.

    Records are produced through the canonical compact producer
    (``build_compact_review_event``) rather than hand-written fixtures, so the
    chains match exactly what the tool appends.
    """

    @staticmethod
    def _judgment() -> dict[str, object]:
        return {
            "validation_status": "real",
            "scope_relation": "admitted",
            "introduced_or_worsened_by_wave": True,
            "contract_relevance": "required_ac",
            "supported_reachability": True,
            "attacker_reachability": False,
            "authority_domain": "none",
            "authority_delta": "none",
            "observable_impact": "material",
            "containment": "preventive",
        }

    @classmethod
    def _finding_event(cls, **overrides: object) -> dict[str, object]:
        event: dict[str, object] = {
            "event": "finding",
            "actor": "qa-reviewer",
            "context_id": "ctx-review",
            "finding_id": "finding-1",
            "run_kind": "initial_delivery",
            "cycle": 0,
            "judgment": cls._judgment(),
            "proposition": "finding-1 reproduces through the named path",
            "failure_condition": "public result differs from the contract",
            "public_path": "test public path",
            "command_or_fixture": "RepairReverificationIndependenceTests",
            "expected": "contract result",
            "observed": "contract violation observed",
            "artifact_or_test_id": "test:finding-1",
            "known_bad_detection_method": "focused injected old behavior",
            "limitations": "temporary local fixture only",
            "safety_and_authorization": "local disposable fixture; no external effects",
            "disposition_rationale": "real defect on a required AC; repair now",
            "source_lanes": ["qa-reviewer"],
            "blocking_required_lanes": ["qa-reviewer"],
            "approval_recheck_lanes": ["qa-reviewer"],
            "review_boundaries_changed": [],
            "fresh_context": True,
            "independent": True,
            "integrity_confirmed": True,
        }
        event.update(overrides)
        return event

    def _append(
        self, records: list[dict[str, object]], event: dict[str, object]
    ) -> list[dict[str, object]]:
        rows, errors = subject.build_compact_review_event(records, event)
        self.assertEqual(errors, (), "expected acceptance: " + "\n".join(errors))
        combined = [*records, *rows]
        record_errors = subject.validate_review_evidence_records(tuple(combined))
        self.assertEqual(record_errors, (), "\n".join(record_errors))
        return combined

    def _chain_through_repair_start(
        self,
        *,
        repair_actor: str = "implementer",
        repair_context: str = "ctx-repair",
    ) -> list[dict[str, object]]:
        records = self._append([], self._finding_event())
        return self._append(
            records,
            self._finding_event(
                actor=repair_actor,
                context_id=repair_context,
                run_kind="repair_start",
                cycle=1,
                observed="repair_start recorded before the mutation",
            ),
        )

    def _clearing_reverification(
        self, *, actor: str, context_id: str, fresh_context: bool = True
    ) -> dict[str, object]:
        return self._finding_event(
            actor=actor,
            context_id=context_id,
            run_kind="reverification",
            cycle=1,
            blocking_required_lanes=[],
            fresh_context=fresh_context,
            independent=True,
            observed="repair independently reverified through the original reproduction",
        )

    # ---- AC-1: same-context contradiction ----------------------------------

    def test_reverification_sharing_repair_context_with_fresh_claim_is_rejected(self) -> None:
        """AC-1 red test: a reverification that shares its chain's repair_start
        context while declaring fresh_context=true is self-contradictory and
        must append nothing."""
        records = self._chain_through_repair_start(
            repair_actor="implementer", repair_context="ctx-shared"
        )
        rows, errors = subject.build_compact_review_event(
            records,
            self._clearing_reverification(actor="qa-reviewer", context_id="ctx-shared"),
        )
        self.assertEqual(rows, (), "same-context fresh reverification must append nothing")
        joined = "\n".join(errors)
        self.assertIn("reverification_context_not_fresh", joined)
        # The prior synthesis head remains the current-state authority.
        head = subject.current_synthesis_heads(records)["finding-1"]
        self.assertEqual(head.get("repair_execution_state"), "pending")

    def test_same_context_on_another_finding_does_not_block(self) -> None:
        """AC-1 control: context matching is by exact finding and cycle.

        finding-2's repair_start (sharing the context the reverification will
        use) is appended AFTER finding-1's own repair_start, so an
        implementation that matches by cycle alone — ignoring the finding —
        would resolve finding-2's chain and falsely reject."""
        records = self._append([], self._finding_event())
        records = self._append(records, self._finding_event(finding_id="finding-2"))
        records = self._append(
            records,
            self._finding_event(
                actor="implementer",
                context_id="ctx-finding-1",
                run_kind="repair_start",
                cycle=1,
                observed="repair_start recorded before the mutation",
            ),
        )
        records = self._append(
            records,
            self._finding_event(
                finding_id="finding-2",
                actor="implementer",
                context_id="ctx-shared",
                run_kind="repair_start",
                cycle=1,
                observed="repair_start recorded before the mutation",
            ),
        )
        # finding-1's reverification reuses finding-2's repair context; only
        # finding-1's own chain controls, so this is accepted.
        records = self._append(
            records,
            self._clearing_reverification(actor="qa-reviewer", context_id="ctx-shared"),
        )
        head = subject.current_synthesis_heads(records)["finding-1"]
        self.assertEqual(head.get("repair_execution_state"), "completed")

    def test_same_context_on_earlier_cycle_does_not_block(self) -> None:
        """AC-1 control: an earlier cycle sharing the context does not control
        the current reverification."""
        records = self._chain_through_repair_start(repair_context="ctx-cycle1")
        records = self._append(
            records,
            self._clearing_reverification(actor="qa-reviewer", context_id="ctx-verify-1"),
        )
        records = self._append(
            records,
            self._finding_event(
                actor="implementer",
                context_id="ctx-cycle2",
                run_kind="repair_start",
                cycle=2,
                observed="repair_start recorded before the mutation",
            ),
        )
        event = self._finding_event(
            actor="qa-reviewer",
            context_id="ctx-cycle1",  # equals cycle 1's repair context only
            run_kind="reverification",
            cycle=2,
            blocking_required_lanes=[],
            observed="cycle 2 repair independently reverified",
        )
        records = self._append(records, event)
        head = subject.current_synthesis_heads(records)["finding-1"]
        self.assertEqual(head.get("cycle"), 2)
        self.assertEqual(head.get("repair_execution_state"), "completed")

    # ---- AC-2: same-actor protocol policy ----------------------------------

    def test_same_actor_reverification_is_rejected_as_protocol_policy(self) -> None:
        """AC-2 red test: actor equality with the resolving repair_start is
        rejected as protocol policy without claiming caller identity."""
        records = self._chain_through_repair_start(
            repair_actor="qa-reviewer", repair_context="ctx-repair"
        )
        rows, errors = subject.build_compact_review_event(
            records,
            self._clearing_reverification(actor="qa-reviewer", context_id="ctx-verify"),
        )
        self.assertEqual(rows, (), "same-actor reverification must append nothing")
        joined = "\n".join(errors)
        self.assertIn("reverification_actor_not_distinct", joined)
        self.assertIn("protocol policy", joined)
        self.assertIn("not proof", joined)
        self.assertIn("distinct acting role", joined)

    def test_same_actor_nonfresh_nonclearing_reverification_is_rejected(self) -> None:
        """AC-2 coverage (1to7k finding same-actor-nonfresh-rejection-untested):
        the actor policy does not depend on the freshness declaration.  A
        same-actor reverification from a distinct context is rejected with
        ``reverification_actor_not_distinct`` even when it honestly declares
        fresh_context=false and clears nothing (blocking_required_lanes
        unchanged) — the shape a mutation narrowing the actor check to
        fresh_context=true would wrongly accept."""
        records = self._chain_through_repair_start(
            repair_actor="qa-reviewer", repair_context="ctx-repair"
        )
        event = self._finding_event(
            actor="qa-reviewer",
            context_id="ctx-verify",
            run_kind="reverification",
            cycle=1,
            fresh_context=False,
            observed="same-actor non-fresh reverification attempt",
        )
        rows, errors = subject.build_compact_review_event(records, event)
        self.assertEqual(
            rows, (), "same-actor non-fresh non-clearing reverification must append nothing"
        )
        self.assertIn("reverification_actor_not_distinct", "\n".join(errors))
        # The prior chain stays the untouched current-state authority.
        record_errors = subject.validate_review_evidence_records(tuple(records))
        self.assertEqual(record_errors, (), "\n".join(record_errors))
        head = subject.current_synthesis_heads(records)["finding-1"]
        self.assertEqual(head.get("repair_execution_state"), "pending")

    def test_same_actor_same_context_nonfresh_reverification_is_rejected(self) -> None:
        """AC-2 coverage (1to7k finding
        same-actor-same-context-nonfresh-reverification-accepted): the actor
        policy fires whenever the higher-precedence fresh-context contradiction
        did not fire.  A same-actor reverification sharing its repair_start
        context and honestly declaring fresh_context=false must be rejected
        with ``reverification_actor_not_distinct`` and append nothing — not
        slip through the same-context/non-fresh early return."""
        records = self._chain_through_repair_start(
            repair_actor="qa-reviewer", repair_context="ctx-shared"
        )
        event = self._finding_event(
            actor="qa-reviewer",
            context_id="ctx-shared",
            run_kind="reverification",
            cycle=1,
            fresh_context=False,
            observed="same-actor same-context non-fresh reverification attempt",
        )
        rows, errors = subject.build_compact_review_event(records, event)
        self.assertEqual(
            rows,
            (),
            "same-actor same-context non-fresh reverification must append nothing",
        )
        self.assertIn("reverification_actor_not_distinct", "\n".join(errors))
        # The prior chain stays the untouched current-state authority.
        record_errors = subject.validate_review_evidence_records(tuple(records))
        self.assertEqual(record_errors, (), "\n".join(record_errors))
        head = subject.current_synthesis_heads(records)["finding-1"]
        self.assertEqual(head.get("repair_execution_state"), "pending")

    def test_same_actor_same_context_fresh_claim_returns_only_contradiction(self) -> None:
        """AC-2/AC-1 precedence control: when actor AND context both match and
        fresh_context=true, only the decidable same-context contradiction is
        returned — actor policy is evaluated only when the contradiction did
        not fire."""
        records = self._chain_through_repair_start(
            repair_actor="qa-reviewer", repair_context="ctx-shared"
        )
        rows, errors = subject.build_compact_review_event(
            records,
            self._clearing_reverification(actor="qa-reviewer", context_id="ctx-shared"),
        )
        self.assertEqual(rows, (), "contradictory reverification must append nothing")
        joined = "\n".join(errors)
        self.assertIn("reverification_context_not_fresh", joined)
        self.assertNotIn("reverification_actor_not_distinct", joined)

    def test_distinct_actor_same_context_nonfresh_reverification_passes_policy(self) -> None:
        """AC-2 quadrant control: a DISTINCT-actor reverification sharing the
        repair context while honestly declaring fresh_context=false passes the
        independence policies (it can never clear a lane — freshness gating
        lives elsewhere)."""
        records = self._chain_through_repair_start(
            repair_actor="implementer", repair_context="ctx-shared"
        )
        event = self._finding_event(
            actor="qa-reviewer",
            context_id="ctx-shared",
            run_kind="reverification",
            cycle=1,
            fresh_context=False,
            observed="distinct-actor same-context non-fresh reverification",
        )
        records = self._append(records, event)
        head = subject.current_synthesis_heads(records)["finding-1"]
        # Non-clearing: the blocking lane remains; the chain is not terminal.
        self.assertEqual(head.get("blocking_required_lanes"), ["qa-reviewer"])

    def test_distinct_role_and_context_reverification_succeeds(self) -> None:
        """AC-2 control, composing with the clearing-lane constraint: the
        implementer records repair_start and the blocking reviewer lane clears
        its own lane from a distinct context."""
        records = self._chain_through_repair_start(
            repair_actor="implementer", repair_context="ctx-repair"
        )
        records = self._append(
            records,
            self._clearing_reverification(actor="qa-reviewer", context_id="ctx-verify"),
        )
        head = subject.current_synthesis_heads(records)["finding-1"]
        self.assertEqual(head.get("repair_execution_state"), "completed")
        self.assertEqual(head.get("blocking_required_lanes"), [])

    def test_waiver_fields_do_not_bypass_independence_policies(self) -> None:
        """AC-2: the broad repair waiver has different semantics and must not
        become an independence bypass."""
        records = self._chain_through_repair_start(
            repair_actor="qa-reviewer", repair_context="ctx-repair"
        )
        event = self._clearing_reverification(actor="qa-reviewer", context_id="ctx-verify")
        event.update(
            {
                "waiver_id": "waiver-1",
                "waiver_scope": "finding-1",
                "waiver_reason": "attempted bypass",
                "waiver_risk": "low",
            }
        )
        rows, errors = subject.build_compact_review_event(records, event)
        self.assertEqual(rows, ())
        self.assertIn("reverification_actor_not_distinct", "\n".join(errors))

    def test_context_contradiction_takes_precedence_over_actor_policy(self) -> None:
        """Requirement 3: when both match, only the decidable same-context
        contradiction is returned."""
        records = self._chain_through_repair_start(
            repair_actor="qa-reviewer", repair_context="ctx-shared"
        )
        rows, errors = subject.build_compact_review_event(
            records,
            self._clearing_reverification(actor="qa-reviewer", context_id="ctx-shared"),
        )
        self.assertEqual(rows, ())
        joined = "\n".join(errors)
        self.assertIn("reverification_context_not_fresh", joined)
        self.assertNotIn("reverification_actor_not_distinct", joined)

    # ---- AC-4: close-time audit over older-code chains ---------------------

    def _older_code_chain(self, *, same_context: bool) -> list[dict[str, object]]:
        """Simulate a chain appended by older code (no append-time check).

        Built through the canonical producer with distinct roles, then the
        repair_start evidence's verification context is edited to collide the
        actor (or context) — the shape old code accepted.  Generic validation
        must remain green over these records (Requirement 4).
        """
        records = self._chain_through_repair_start(
            repair_actor="implementer", repair_context="ctx-repair"
        )
        records = self._append(
            records,
            self._clearing_reverification(actor="qa-reviewer", context_id="ctx-verify"),
        )
        for record in records:
            context = record.get("verification_context")
            if (
                isinstance(context, dict)
                and context.get("actor") == "implementer"
                and context.get("context_id") == "ctx-repair"
            ):
                if same_context:
                    context["context_id"] = "ctx-verify"
                else:
                    context["actor"] = "qa-reviewer"
        record_errors = subject.validate_review_evidence_records(tuple(records))
        self.assertEqual(record_errors, (), "\n".join(record_errors))
        return records

    def test_close_audit_flags_latest_same_actor_chain(self) -> None:
        records = self._older_code_chain(same_context=False)
        violations = subject.repair_independence_violations(records)
        self.assertEqual(len(violations), 1, violations)
        self.assertIn("finding-1", violations[0])
        self.assertIn("repair_start", violations[0])

    def test_close_audit_flags_latest_same_context_chain(self) -> None:
        records = self._older_code_chain(same_context=True)
        violations = subject.repair_independence_violations(records)
        self.assertEqual(len(violations), 1, violations)
        self.assertIn("finding-1", violations[0])
        self.assertIn("context", violations[0])

    def test_close_audit_clears_after_next_cycle_recovery(self) -> None:
        """AC-4 recovery: repair_start at the next cycle plus a distinct-role
        and distinct-context reverification supersedes the invalid terminal
        chain and clears the audit."""
        records = self._older_code_chain(same_context=False)
        self.assertTrue(subject.repair_independence_violations(records))
        records = self._append(
            records,
            self._finding_event(
                actor="implementer",
                context_id="ctx-recovery-repair",
                run_kind="repair_start",
                cycle=2,
                observed="recovery repair_start recorded before the mutation",
            ),
        )
        records = self._append(
            records,
            self._finding_event(
                actor="qa-reviewer",
                context_id="ctx-recovery-verify",
                run_kind="reverification",
                cycle=2,
                blocking_required_lanes=[],
                observed="recovery reverification by a distinct role and context",
            ),
        )
        self.assertEqual(subject.repair_independence_violations(records), ())

    def test_close_audit_accepts_clean_chain(self) -> None:
        records = self._chain_through_repair_start()
        records = self._append(
            records,
            self._clearing_reverification(actor="qa-reviewer", context_id="ctx-verify"),
        )
        self.assertEqual(subject.repair_independence_violations(records), ())

    # ---- AC-6: seed prose pinned against validator behavior ----------------

    def test_seed_enforced_versus_declared_split_is_pinned_to_validator_behavior(self) -> None:
        """AC-6: the seed states which independence properties are enforced
        and which stay declared, using the validator's exact diagnostic
        codes, and this test proves the validator actually emits them — so a
        change to either side breaks the pin."""
        seed = (SCRIPTS_ROOT.parent / "seeds" / "209-agent-harness-core.prompt.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Enforced versus declared independence", seed)
        for code in (
            subject.REVERIFICATION_CONTEXT_NOT_FRESH,
            subject.REVERIFICATION_ACTOR_NOT_DISTINCT,
            subject.REVIEW_EVIDENCE_INDEPENDENCE_INVALID,
        ):
            self.assertIn(f"`{code}`", seed)
        # The declared-limit claims a reader must not over-read.
        self.assertIn("sees strings, not callers", seed)
        self.assertIn("never proof of shared caller identity", seed)
        self.assertIn("cannot be authenticated in-process", seed)
        # Behavioral half of the pin: the codes the seed names are exactly
        # the leading tokens of the validator's rejections.
        records = self._chain_through_repair_start(
            repair_actor="qa-reviewer", repair_context="ctx-shared"
        )
        _rows, context_errors = subject.build_compact_review_event(
            records,
            self._clearing_reverification(actor="qa-reviewer", context_id="ctx-shared"),
        )
        self.assertTrue(
            context_errors
            and context_errors[0].startswith(
                f"{subject.REVERIFICATION_CONTEXT_NOT_FRESH}: "
            ),
            context_errors,
        )
        _rows, actor_errors = subject.build_compact_review_event(
            records,
            self._clearing_reverification(actor="qa-reviewer", context_id="ctx-distinct"),
        )
        self.assertTrue(
            actor_errors
            and actor_errors[0].startswith(
                f"{subject.REVERIFICATION_ACTOR_NOT_DISTINCT}: "
            ),
            actor_errors,
        )
        # QA seed carries the obligation with the same vocabulary.
        qa_seed = (SCRIPTS_ROOT.parent / "seeds" / "239-qa-reviewer.prompt.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(f"`{subject.REVERIFICATION_ACTOR_NOT_DISTINCT}`", qa_seed)
        self.assertIn("without claiming caller identity", qa_seed)


class RealCorpusRegressionTests(unittest.TestCase):
    """1tmb2 AC-5: executed over the real corpus, not a fixture.

    The fixtures elsewhere in this file were written by the same model that
    wrote the validator; the repository's own closed ledgers are the only
    oracle they cannot substitute for.  On installed targets without a wave
    corpus the test skips.
    """

    REPO_ROOT = SCRIPTS_ROOT.parents[2]

    def _corpus(self) -> list[Path]:
        waves_dir = self.REPO_ROOT / "docs" / "waves"
        if not waves_dir.is_dir():
            return []
        return sorted(
            wave_md.parent
            for wave_md in waves_dir.glob("*/wave.md")
            if (wave_md.parent / "events.jsonl").is_file()
        )

    def test_every_real_ledger_still_validates_and_no_sealed_wave_changes_state(self) -> None:
        corpus = self._corpus()
        if not corpus:
            self.skipTest("no real wave corpus in this checkout")
        for wave_dir in corpus:
            wave_md = wave_dir / "wave.md"
            events = wave_dir / "events.jsonl"
            before = (wave_md.read_bytes(), events.read_bytes())
            result = subject.validate_external_review_evidence(wave_md)
            self.assertTrue(
                result.ok, f"{wave_dir.name}: " + "\n".join(result.errors)
            )
            self.assertEqual(
                (wave_md.read_bytes(), events.read_bytes()),
                before,
                f"{wave_dir.name}: validation must not change sealed state",
            )

    def test_known_closed_archives_with_historical_chains_stay_passing(self) -> None:
        """The two known archive classes (same-actor chains, same-context
        contradictions) remain readable and passing while closed; the audit
        function would flag their latest chains only if explicitly reopened."""
        corpus = {wave_dir.name: wave_dir for wave_dir in self._corpus()}
        known = [name for name in corpus if name.split()[0] in {"1skt1", "1slep"}]
        if not known:
            self.skipTest("known historical archives not present in this checkout")
        for name in known:
            wave_md = corpus[name] / "wave.md"
            text = wave_md.read_text(encoding="utf-8")
            self.assertRegex(text, r"(?mi)^Status:\s*closed\s*$")
            result = subject.validate_external_review_evidence(wave_md)
            self.assertTrue(result.ok, f"{name}: " + "\n".join(result.errors))
            self.assertTrue(
                subject.repair_independence_violations(result.records),
                f"{name}: expected the latest chains to carry the historical "
                "independence defect the forward audit would flag on reopen",
            )


class ReviewAuthorityFacadeTests(unittest.TestCase):
    """Wave 1to78: the single authority-resolution facade for gate reads.

    Typed branch (declared waves) derives exclusively from events.jsonl via the
    ``review_status_rows`` chronology; the legacy prose branch preserves the
    historical parsing that used to live in server_impl.py.
    """

    @staticmethod
    def _approval(signoff_key: str, actor: str, *, fresh: bool = True, independent: bool = True) -> dict:
        return {
            "record_type": "executable_evidence",
            "evidence_record_id": f"approval-{signoff_key}",
            "claim_id": f"approval:{signoff_key}",
            "claim_kind": "approval",
            "required_for_approval": True,
            "phase": "delivery",
            "execution_status": "executed",
            "verification_context": {
                "actor": actor,
                "context_id": f"ctx-{signoff_key}",
                "fresh_context": fresh,
                "independent": independent,
            },
        }

    @staticmethod
    def _head(finding_id: str, **overrides: object) -> dict:
        head: dict = {
            "record_type": "finding_synthesis",
            "finding_id": finding_id,
            "validation_status": "real",
            "disposition": "do_now",
            "authority_delta": "none",
            "observable_impact": "none",
        }
        head.update(overrides)
        return head

    def test_dispatch_on_declaration(self):
        legacy = subject.resolve_review_authority(None, None, wave_text="# Wave Record\n")
        self.assertFalse(legacy.typed)
        declared = subject.resolve_review_authority(
            None, None, wave_text="# Wave Record\n\nreview-evidence-source: events.jsonl\n"
        )
        self.assertTrue(declared.typed)
        self.assertEqual(declared.records, ())

    def test_malformed_declaration_fails_closed_as_typed(self):
        malformed = subject.resolve_review_authority(
            None, None, wave_text="# Wave Record\n\nreview-evidence-source: wrong.jsonl\n"
        )
        self.assertTrue(malformed.typed)
        self.assertFalse(malformed.signoff_current("operator-signoff"))
        self.assertFalse(malformed.evidence_present())

    def test_typed_signoff_requires_exact_actor_and_ignores_prose(self):
        wave_text = (
            "# Wave Record\n\nreview-evidence-source: events.jsonl\n\n"
            "## Review Evidence\n\n- qa-reviewer: approved\n- operator-signoff: approved\n"
        )
        authority = subject.ReviewAuthority(
            typed=True,
            wave_text=wave_text,
            records=(self._approval("qa-reviewer", "qa-reviewer"),),
        )
        self.assertTrue(authority.signoff_current("qa-reviewer"))
        # prose operator-signoff line is narrative: no typed record, no approval
        self.assertFalse(authority.operator_signoff_present())
        forged = subject.ReviewAuthority(
            typed=True,
            wave_text=wave_text,
            records=(self._approval("qa-reviewer", "code-reviewer"),),
        )
        self.assertFalse(forged.signoff_current("qa-reviewer"))

    def test_prose_branch_matches_legacy_parsers(self):
        wave_text = (
            "# Wave Record\n\n"
            "## Prepare Review Evidence\n\n- qa-reviewer: approved\n\n"
            "## Review Evidence\n\n- operator-signoff: approved\n- code-reviewer: approved\n"
        )
        authority = subject.resolve_review_authority(None, None, wave_text=wave_text)
        self.assertFalse(authority.typed)
        self.assertTrue(authority.operator_signoff_present())
        self.assertTrue(authority.signoff_current("code-reviewer"))
        self.assertTrue(authority.signoff_current("qa-reviewer", section="prepare"))
        # section separation: qa-reviewer signed only in the prepare section
        self.assertFalse(authority.signoff_current("qa-reviewer", section="review"))
        self.assertTrue(authority.evidence_present())
        self.assertTrue(authority.any_signoff_evidence())

    def test_typed_max_severity_maps_impact_facts_not_words(self):
        base = "# Wave Record\n\nreview-evidence-source: events.jsonl\n"
        cases = [
            ((), "none"),
            ((self._head("f1", observable_impact="low"),), "low"),
            ((self._head("f1", observable_impact="material"),), "high"),
            ((self._head("f1", authority_delta="critical"),), "critical"),
            ((self._head("f1", observable_impact="unverified"),), "none"),
            # invalid / not_issue heads never contribute
            ((self._head("f1", observable_impact="critical", validation_status="invalid"),), "none"),
            ((self._head("f1", observable_impact="critical", disposition="not_issue"),), "none"),
            # only the CURRENT head per finding counts (append-order last wins)
            (
                (
                    self._head("f1", observable_impact="critical"),
                    self._head("f1", observable_impact="low"),
                ),
                "low",
            ),
        ]
        for records, expected in cases:
            authority = subject.ReviewAuthority(typed=True, wave_text=base, records=records)
            self.assertEqual(authority.max_severity(), expected, records)

    def test_typed_max_severity_ignores_prose_severity_words(self):
        wave_text = (
            "# Wave Record\n\nreview-evidence-source: events.jsonl\n\n"
            "## Review Evidence\n\n- note: a high severity remark with critical wording\n"
        )
        authority = subject.ReviewAuthority(typed=True, wave_text=wave_text, records=())
        self.assertEqual(authority.max_severity(), "none")
        legacy = subject.ReviewAuthority(typed=False, wave_text=wave_text)
        self.assertEqual(legacy.max_severity(), "critical")

    def test_resolve_reads_ledger_for_declared_wave(self):
        with tempfile.TemporaryDirectory() as tmp:
            wave_dir = Path(tmp) / "docs" / "waves" / "1test sample"
            wave_dir.mkdir(parents=True)
            wave_md = wave_dir / "wave.md"
            records = (
                executable_evidence("dedup-run-readiness", "dedup-run-readiness", claim_kind="dedup"),
                review_run("run-readiness", kind="readiness", candidates=[]),
            )
            wave_md.write_text(
                "# Wave\nreview-evidence-source: events.jsonl\n\n"
                + subject.render_review_evidence_projection(
                    subject.empty_external_finding_synthesis_section(), records
                ),
                encoding="utf-8",
            )
            (wave_dir / "events.jsonl").write_bytes(
                subject.canonical_review_events_bytes(records)
            )
            authority = subject.resolve_review_authority(Path(tmp), wave_dir)
            self.assertTrue(authority.typed)
            self.assertEqual(authority.ledger_errors, (), authority.ledger_errors)
            self.assertTrue(authority.evidence_present())
            # a corrupted ledger fails every read closed
            (wave_dir / "events.jsonl").write_bytes(b"{not-json}\n")
            broken = subject.resolve_review_authority(Path(tmp), wave_dir)
            self.assertTrue(broken.typed)
            self.assertTrue(broken.ledger_errors)
            self.assertEqual(broken.records, ())
            self.assertFalse(broken.evidence_present())


if __name__ == "__main__":
    unittest.main()
