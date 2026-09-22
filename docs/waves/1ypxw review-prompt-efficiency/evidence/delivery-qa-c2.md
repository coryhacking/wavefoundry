# C-2 — Stale guidance and census expectations

Owner: Engineering
Status: active
Last verified: 2026-09-22

Finding ID: C-2
Source lane: qa-reviewer
Context: `/root/ypxw_delivery_qa` (independent delivery context; no implementation edits).
Disposition: do_now; blocks the required green-suite AC until repaired and independently reverified.

The two failures are expectation maintenance omitted alongside admitted behavior changes. Seed 239 intentionally adds a conditional sixth evidence-integrity condition, while `test_fixture_fidelity_guidance.py:51` requires exactly 1–5. The owned carrier rewrite intentionally removes the old record-layout literal, while `test_record_layout_census.py:128` still exempts that absent literal and its stale-entry check rejects it. Neither failure justifies reverting the admitted guidance or weakening the census.

Independent reproduction: from repository root, `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests python3 -B -m unittest test_fixture_fidelity_guidance.FixtureFidelityGuidanceTests.test_qa_preserves_five_conditions_and_self_hosted_guidance test_record_layout_census.RecordLayoutCensusTests.test_allowlist_has_no_stale_entries -v`. Two tests ran in 0.127 seconds, both failed on the expected assertions, zero errors and skips. First actual list: `['1','2','3','4','5','6']`, expected `['1','2','3','4','5']`. Second actual stale entry: `('render_agent_surfaces.py', '`docs/waves/<wave>/events.jsonl` authority')`.

Independent-reference check: all first five numbered conditions in seed 239 are byte-identical to `/tmp/1ypxw-before`. The sixth condition is explicitly authorized by 1ypxu Requirement 2. The renderer literal removal is authorized by 1yoy2 Requirement 4. The census is therefore correctly flagging a retired exemption.

Bounded repair probe: in a separate Python process, changed only the expected numbering to 123456 and removed only that ALLOWLIST key in memory. Executed all tests in both modules against the real source tree: eight passed in 0.266 seconds, zero errors/skips, including the real scanner's injected literal-join polarity test. No source was changed by this reviewer. This establishes that a narrow repair suffices; final source repair still needs independent reverification.

Recommended repair: update the guidance expectation and pin that condition six is conditional on a measured delta, retaining the first five checks and known-bad controls; remove the single stale ALLOWLIST entry. Preserve `SITES`, which is explicitly a historical pre-routing inventory (the initial suggestion to remove its matching row was withdrawn after checking that documented purpose). Preserve the stale-entry and unrouted-site scanner predicates.

## Typed finding facts

```json
{
  "judgment": {
    "validation_status": "real",
    "scope_relation": "admitted",
    "introduced_or_worsened_by_wave": true,
    "contract_relevance": "required_ac",
    "supported_reachability": true,
    "attacker_reachability": false,
    "authority_domain": "integrity",
    "authority_delta": "low",
    "observable_impact": "material",
    "containment": "preventive"
  },
  "source_lanes": ["qa-reviewer"],
  "blocking_required_lanes": ["qa-reviewer"],
  "approval_recheck_lanes": ["qa-reviewer"],
  "review_boundaries_changed": [],
  "evidence": {
    "proposition": "Two unchanged test expectations reject the admitted guidance and owned-carrier edits.",
    "failure_condition": "The canonical framework suite executes either named test against the delivered source tree.",
    "public_path": "python3 .wavefoundry/framework/scripts/run_tests.py; its real unittest modules independently executed here",
    "command_or_fixture": "Two named unittest methods above; whole two-module in-memory repair probe",
    "expected": "All six numbered conditions are recognized, first five retained, and the record-layout allowlist contains only present sites.",
    "observed": "Two assertion failures reproduced; minimal in-memory expectation repair makes all eight module tests pass.",
    "artifact_or_test_id": "docs/waves/1ypxw review-prompt-efficiency/evidence/delivery-qa-c2.md",
    "known_bad_detection_method": "pre-fix-failure",
    "limitations": "Did not rerun the entire 9533-test suite; final repair and independent reverification remain pending.",
    "safety_and_authorization": "Authorized independent review; disposable test roots and process-local patches only; no source or lifecycle writes.",
    "disposition_rationale": "Required full-suite AC is blocked; two expectation-only repairs preserve admitted contracts and census strength."
  },
  "integrity_checks": {
    "test_ran_without_unintended_skip": true,
    "public_path_reached": true,
    "boundary_values_realistic": true,
    "assertions_non_vacuous": true,
    "known_bad_detected": true,
    "known_bad_detection_method": "pre-fix-failure"
  }
}
```
