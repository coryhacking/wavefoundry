from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
import sys
import tempfile
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


def raw_wave_text(records: list[dict[str, object]], *, marker: int | None = 1) -> str:
    marker_line = "" if marker is None else f"review-evidence-protocol: {marker}\n"
    lines = "\n".join(json.dumps(record, sort_keys=True) for record in records)
    return (
        f"# Wave\n\n{marker_line}\n## Finding Synthesis\n\n"
        f"{subject.FINDING_SYNTHESIS_MARKER_BEGIN}\n"
        f"```jsonl\n{lines}\n```\n"
        f"{subject.FINDING_SYNTHESIS_MARKER_END}\n"
    )


def wave_text(records: list[dict[str, object]], *, marker: int | None = 1) -> str:
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
    return raw_wave_text(expanded, marker=marker)


def _record_adoptions_worker(
    root: str,
    prefix: str,
    count: int,
    barrier: object,
    errors: object,
) -> None:
    text = raw_wave_text([])
    for index in range(count):
        barrier.wait()
        error = subject.record_legacy_inline_protocol_state_for_migration(
            Path(root), f"{prefix}-{index}", text
        )
        if error:
            errors.put(error)


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
        return subject.validate_review_evidence(wave_text(records), **kwargs)

    def assert_valid(self, records: list[dict[str, object]], **kwargs: object) -> None:
        result = self.validate(records, **kwargs)
        self.assertTrue(result.ok, "\n".join(result.errors))

    def assert_error(self, records: list[dict[str, object]], fragment: str, **kwargs: object) -> None:
        result = self.validate(records, **kwargs)
        self.assertFalse(result.ok)
        self.assertIn(fragment, "\n".join(result.errors))

    def test_unmarked_historical_wave_is_legacy_valid(self) -> None:
        result = subject.validate_review_evidence("# Closed historical wave\n")
        self.assertTrue(result.ok)
        self.assertIsNone(result.marker_version)

    def test_actionable_completion_requires_reverification_during_normal_validation(self) -> None:
        impossible = synthesis(repair_execution_state="completed")
        result = subject.validate_review_evidence(wave_text([review_run(), impossible]))
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
            "Lane reassessment evidence must be executed in delivery",
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

    def test_marker_is_monotonic_and_version_is_finite(self) -> None:
        previous = wave_text([review_run(), synthesis()])
        removed = subject.validate_review_evidence("# Wave\n", previous_text=previous)
        self.assertIn("may not be removed", "\n".join(removed.errors))
        downgraded = subject.validate_review_evidence(wave_text([], marker=0), previous_text=previous)
        self.assertIn("may not be downgraded", "\n".join(downgraded.errors))
        self.assertIn("unsupported", "\n".join(downgraded.errors))
        replaced = subject.validate_review_evidence(
            wave_text([review_run("replacement", candidates=[])]),
            previous_text=previous,
        )
        self.assertIn("append-only", "\n".join(replaced.errors))

    def test_marked_wave_allows_empty_creation_block_but_closure_requires_run(self) -> None:
        missing_section = subject.validate_review_evidence("# Wave\nreview-evidence-protocol: 1\n")
        self.assertIn("Finding Synthesis", "\n".join(missing_section.errors))
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
        result = subject.validate_review_evidence(subject.render_review_evidence_records(raw_wave_text([]), rows))
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
            "public_path": "wave_record_review_evidence",
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
        rendered = subject.render_review_evidence_records(raw_wave_text([]), rows)
        result = subject.validate_review_evidence(rendered)
        self.assertTrue(result.ok, "\n".join(result.errors))
        self.assertIn("| public-path-regression | do_now | yes | pending | qa-reviewer |", rendered)

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
            "public_path": "wave_record_review_evidence",
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
            result = subject.validate_review_evidence(
                subject.render_review_evidence_records(raw_wave_text([]), records)
            )
            self.assertTrue(result.ok, "\n".join(result.errors))
            return rows

        append_event()
        append_event(run_kind="repair_start", cycle=1, context_id="repair-a")

        later = append_event(
            finding_id="finding-b",
            run_kind="initial_delivery",
            cycle=0,
            context_id="later-review-b",
        )
        self.assertNotIn("deviation_ids", later[1])
        append_event(
            finding_id="finding-b",
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
                "public_path": "wave_upgrade archive extraction",
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

    def test_compact_summary_and_table_are_generated_views_not_authority(self) -> None:
        text = subject.empty_finding_synthesis_section()
        marked = "# Wave\nreview-evidence-protocol: 1\n\n" + text
        self.assertTrue(subject.validate_review_evidence(marked).ok)
        self.assertIn("Machine review evidence — 0 records", marked)
        self.assertIn("| Current finding | Disposition | Open block |", marked)
        # The JSONL remains canonical, so stale presentation never changes validation truth.
        stale = marked.replace("0 records", "9 records", 1)
        self.assertTrue(subject.validate_review_evidence(stale).ok)

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

    def test_marker_is_header_only_and_owned_region_is_required(self) -> None:
        prose = subject.validate_review_evidence(
            "# Legacy wave\n\n## Notes\n\nreview-evidence-protocol: 1\n"
        )
        self.assertTrue(prose.ok)
        self.assertIsNone(prose.marker_version)

        missing_owned = subject.validate_review_evidence(
            "# Wave\nreview-evidence-protocol: 1\n\n## Finding Synthesis\n\n```jsonl\n```\n"
        )
        self.assertIn("owned marker pair", "\n".join(missing_owned.errors))

        outside_owned = subject.validate_review_evidence(
            "# Wave\nreview-evidence-protocol: 1\n\n## Finding Synthesis\n\n"
            "```jsonl\n```\n"
            f"{subject.FINDING_SYNTHESIS_MARKER_BEGIN}\n"
            f"{subject.FINDING_SYNTHESIS_MARKER_END}\n"
        )
        self.assertIn("must be enclosed", "\n".join(outside_owned.errors))

    def test_parser_rejects_malformed_json_non_object_and_unknown_record(self) -> None:
        text = (
            "# Wave\nreview-evidence-protocol: 1\n\n## Finding Synthesis\n\n```jsonl\n"
            "not-json\n[]\n{\"record_type\":\"mystery\"}\n```\n"
        )
        result = subject.validate_review_evidence(text)
        joined = "\n".join(result.errors)
        self.assertIn("invalid JSON", joined)
        self.assertIn("record must be an object", joined)
        self.assertIn("unknown record_type", joined)

    def test_executable_evidence_is_linked_and_required_approval_must_execute(self) -> None:
        run = review_run()
        row = synthesis()
        missing = subject.validate_review_evidence(raw_wave_text([run, row]))
        self.assertIn("missing executable evidence", "\n".join(missing.errors))
        approval = executable_evidence(
            "approval-1",
            "delivery-approval",
            claim_kind="approval",
            required_for_approval=True,
            execution_status="inferred",
        )
        result = subject.validate_review_evidence(raw_wave_text([approval]))
        self.assertIn("must be executed in delivery", "\n".join(result.errors))
        self.assertIn("approval:<signoff-key>", "\n".join(result.errors))

    def test_synthesis_requires_prior_finding_evidence(self) -> None:
        run = review_run()
        row = synthesis()
        dedup = executable_evidence("dedup-run-0", "dedup-run-0", claim_kind="dedup")
        wrong_kind = executable_evidence(
            "evidence-synthesis-0", "finding-1", claim_kind="dedup"
        )
        result = subject.validate_review_evidence(
            raw_wave_text([dedup, run, wrong_kind, row])
        )
        self.assertIn("claim_kind `finding`", "\n".join(result.errors))

        finding = executable_evidence("evidence-synthesis-0", "finding-1")
        result = subject.validate_review_evidence(
            raw_wave_text([dedup, run, row, finding])
        )
        self.assertIn("cannot precede its executable finding evidence", "\n".join(result.errors))

    def test_universal_census_and_unsafe_probe_fail_closed(self) -> None:
        universal = executable_evidence(
            "census-1",
            "all-writers",
            claim_kind="census",
            universal_claim=True,
        )
        result = subject.validate_review_evidence(raw_wave_text([universal]))
        self.assertIn("requires a census object", "\n".join(result.errors))

        unsafe = executable_evidence(
            "unsafe-1",
            "remote-release",
            probe_class="external_or_destructive",
            authorization_status="not_authorized",
            execution_status="executed",
        )
        result = subject.validate_review_evidence(raw_wave_text([unsafe]))
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
            result = subject.validate_review_evidence(raw_wave_text([evidence]))
            self.assertIn(fragment, "\n".join(result.errors))

        valid = executable_evidence(
            "census-valid",
            "all-writers",
            claim_kind="census",
            universal_claim=True,
            census=closed_census(),
        )
        self.assertTrue(subject.validate_review_evidence(raw_wave_text([valid])).ok)

    def test_same_context_lane_reassessment_is_rejected(self) -> None:
        evidence = executable_evidence(
            "lane-1",
            "finding-1",
            claim_kind="lane_reassessment",
            fresh_context=False,
            independent=False,
        )
        result = subject.validate_review_evidence(raw_wave_text([evidence]))
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
        result = subject.validate_review_evidence(raw_wave_text([evidence]))
        self.assertIn("must be fresh and independent", "\n".join(result.errors))

    def test_required_approval_is_mandatory_at_closure(self) -> None:
        rows = [
            executable_evidence("dedup-empty", "dedup-empty", claim_kind="dedup"),
            review_run("initial-empty", candidates=[]),
        ]
        rows[-1]["dedup_evidence_id"] = "dedup-empty"
        result = subject.validate_review_evidence(raw_wave_text(rows), closure=True)
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
            result = subject.validate_review_evidence(raw_wave_text([evidence]))
            self.assertIn("all five evidence-integrity checks", "\n".join(result.errors), field)

    def test_migration_only_inline_adoption_rejects_history_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            original = wave_text([review_run(), synthesis()])
            self.assertIsNone(
                subject.record_legacy_inline_protocol_state_for_migration(
                    root, "1test wave", original
                )
            )
            replacement = wave_text(
                [review_run("other-run", candidates=[])]
            )
            replaced = subject.record_legacy_inline_protocol_state_for_migration(
                root, "1test wave", replacement
            )
            self.assertIn("removed or changed", str(replaced))

    def test_migration_only_inline_adoption_is_cross_process_serialized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ctx = multiprocessing.get_context("spawn")
            barrier = ctx.Barrier(2)
            errors = ctx.Queue()
            count = 12
            processes = [
                ctx.Process(
                    target=_record_adoptions_worker,
                    args=(temp_dir, prefix, count, barrier, errors),
                )
                for prefix in ("wave-a", "wave-b")
            ]
            for process in processes:
                process.start()
            for process in processes:
                process.join(20)
                self.assertEqual(process.exitcode, 0)
            self.assertTrue(errors.empty())
            ledger = json.loads(
                (Path(temp_dir) / subject.ADOPTION_LEDGER_REL).read_text(encoding="utf-8")
            )
            self.assertEqual(len(ledger["waves"]), count * 2)

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
        result = subject.validate_review_evidence(wave_text([row, review_run()]))
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
        result = subject.validate_review_evidence(wave_text(rows))
        self.assertIn("no preceding repair_start", "\n".join(result.errors))

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
        result = subject.validate_review_evidence(wave_text(rows))
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
        result = subject.validate_review_evidence(wave_text([start, rejected]))
        joined = "\n".join(result.errors)
        self.assertIn("preceding initial_delivery", joined)
        self.assertIn("requires an actionable synthesis", joined)

    def test_convergence_checkpoint_requires_two_completed_cycles(self) -> None:
        rows = [
            review_run(),
            synthesis(),
            review_run("checkpoint", kind="convergence_checkpoint", cycle=2, frozen_boundary=["finding-1"]),
            synthesis("checkpoint-s", run_id="checkpoint", cycle=2, supersedes_record_id="synthesis-0"),
        ]
        result = subject.validate_review_evidence(wave_text(rows))
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
        result = subject.validate_review_evidence(wave_text(rows))
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
        result = subject.validate_review_evidence(wave_text(partial))
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
        result = subject.validate_review_evidence(wave_text(complete))
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
        result = subject.validate_review_evidence(wave_text(rows))
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
        result = subject.validate_review_evidence(wave_text(rows))
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
        result = subject.validate_review_evidence(
            wave_text(
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
        result = subject.validate_review_evidence(
            wave_text(
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
        result = subject.validate_review_evidence(wave_text(rows), closure=True)
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
        result = subject.validate_review_evidence(
            wave_text(
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
        result = subject.validate_review_evidence(wave_text(self._cycle_records()), closure=True)
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
        result = subject.validate_review_evidence(wave_text(rows))
        self.assertTrue(result.ok, "\n".join(result.errors))

    def test_two_completed_cycles_require_convergence_checkpoint(self) -> None:
        rows = self._cycle_records()[:-2]
        result = subject.validate_review_evidence(wave_text(rows), closure=True)
        self.assertIn("require a convergence_checkpoint", "\n".join(result.errors))

    def test_frozen_boundary_requires_deviation_for_non_material_adjacency(self) -> None:
        rows = self._cycle_records()
        run3 = review_run("start-3", kind="repair_start", cycle=3, candidates=["finding-2"])
        new = synthesis("new-2", run_id="start-3", finding_id="finding-2", cycle=3)
        result = subject.validate_review_evidence(wave_text([*rows, run3, new]))
        self.assertIn("exceeds frozen boundary", "\n".join(result.errors))
        run3["deviation_ids"] = ["finding-2"]
        result = subject.validate_review_evidence(wave_text([*rows, run3, new]))
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
        result = subject.validate_review_evidence(wave_text([*rows, run3, new]))
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

    def test_prefix_proof_is_counted_domain_separated_and_pins_zero(self) -> None:
        rows = ({"record_type": "one"}, {"record_type": "two"})
        zero = subject.review_event_prefix_proof(rows, 0)
        self.assertEqual(zero["record_count"], 0)
        self.assertEqual(
            zero["prefix_sha256"],
            hashlib.sha256(b"wavefoundry-review-events\0").hexdigest(),
        )
        one_bytes = subject.canonical_review_event_bytes(rows[0])
        one = subject.review_event_prefix_proof(rows, 1)
        self.assertEqual(
            one["prefix_sha256"],
            hashlib.sha256(b"wavefoundry-review-events\0" + one_bytes).hexdigest(),
        )
        with self.assertRaises(ValueError):
            subject.review_event_prefix_proof(rows, 3)

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

    def test_zero_record_adoption_is_bounded_external_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wave = self.make_external_wave(root)
            with subject.review_event_write_lock(root):
                self.assertIsNone(
                    subject.record_protocol_state_locked(root, "1test sample", wave)
                )
            state, error = subject.adopted_protocol_state(root, "1test sample")
            self.assertIsNone(error)
            self.assertEqual(
                state,
                {
                    "version": 1,
                    "source": "events.jsonl",
                    "record_count": 0,
                    "prefix_sha256": hashlib.sha256(
                        b"wavefoundry-review-events\0"
                    ).hexdigest(),
                },
            )
            self.assertEqual(
                subject.validate_adopted_protocol_state(root, "1test sample", wave), ()
            )

    def test_retained_adoption_rejects_declaration_and_authority_loss(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wave = self.make_external_wave(root)
            self.assertIsNone(subject.record_protocol_state(root, "1test sample", wave))
            original = wave.read_text(encoding="utf-8")
            wave.write_text(
                original.replace("review-evidence-source: events.jsonl\n", ""),
                encoding="utf-8",
            )
            self.assertIn(
                "may not be removed",
                "\n".join(
                    subject.validate_adopted_protocol_state(root, "1test sample", wave)
                ),
            )
            wave.write_text(
                original.replace("events.jsonl", "wrong.jsonl", 1), encoding="utf-8"
            )
            self.assertIn(
                "must be exactly",
                "\n".join(
                    subject.validate_adopted_protocol_state(root, "1test sample", wave)
                ),
            )
            wave.write_text(original, encoding="utf-8")
            (wave.parent / "events.jsonl").unlink()
            self.assertIn(
                "is missing",
                "\n".join(
                    subject.validate_adopted_protocol_state(root, "1test sample", wave)
                ),
            )

    def test_retained_adoption_rejects_proof_ahead_prefix_mutation_and_suffix(self) -> None:
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
            wave = self.make_external_wave(root, rows)
            self.assertIsNone(subject.record_protocol_state(root, "1test sample", wave))

            mutated = copy.deepcopy(rows[0])
            mutated["review_run_id"] = "changed"
            (wave.parent / "events.jsonl").write_bytes(
                subject.canonical_review_events_bytes([mutated])
            )
            self.assertIn(
                "prefix hash",
                "\n".join(
                    subject.validate_adopted_protocol_state(root, "1test sample", wave)
                ),
            )

            (wave.parent / "events.jsonl").write_bytes(
                subject.canonical_review_events_bytes(rows)
                + subject.canonical_review_event_bytes(
                    {
                        "record_type": "review_run",
                        "review_run_id": "run-second",
                        "run_kind": "initial_delivery",
                        "cycle": 0,
                        "candidate_finding_ids": [],
                        "source_record_ids": [],
                        "dedup_evidence_id": None,
                    }
                )
            )
            self.assertIn(
                "unadopted suffix",
                "\n".join(
                    subject.validate_adopted_protocol_state(root, "1test sample", wave)
                ),
            )

            (wave.parent / "events.jsonl").write_bytes(b"")
            self.assertIn(
                "proof is ahead",
                "\n".join(
                    subject.validate_adopted_protocol_state(root, "1test sample", wave)
                ),
            )


class ReviewEvidenceLintIntegrationTests(unittest.TestCase):
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

if __name__ == "__main__":
    unittest.main()
