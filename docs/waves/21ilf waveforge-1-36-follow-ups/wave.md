# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-23
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21ilf waveforge-1-36-follow-ups`
Title: Waveforge 1.36.0 Follow-Ups

## Objective

Distributions and maintainers get a framework suite and build metadata that work on every supported host, and security reviewers keep unconfirmed candidates open until settled. The 3.11 and newer-lancedb test failures stop, `pyproject.toml` builds, upstream-only fixture tests skip outside this repository but fail here when content goes missing, and the credible-threat gate says an unknown factor is not an absent one. Boundaries: no product behaviour change beyond one named constant; no new gate, lane or lint rule.

## Changes

Change ID: `21goe-bug host-dependent-test-failures-on-3-11-and-newer-lancedb`
Change Status: `implemented`

Change ID: `21ij7-bug pyproject-build-backend-and-license-metadata`
Change Status: `implemented`

Change ID: `21ild-enh credible-threat-unknown-factor-stays-open`
Change Status: `implemented`

Change ID: `21ile-enh skip-upstream-only-fixture-tests-outside-source-repo`
Change Status: `implemented`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-24

## Wave Summary

Wave `21ilf` (Waveforge 1.36.0 Follow-Ups) delivered 4 changes: Host-Dependent Test Failures on Python 3.11 and Newer LanceDB, Pyproject Build Backend and License Metadata, Credible-Threat Gate: An Unknown Factor Stays Open, and Skip Upstream-Only Fixture Tests Outside the Source Repository. Notable adjustments during implementation: Pyproject Build Backend and License Metadata: Delivery note: the wheel reports version `1.0.0` from `pyproject.toml` while `VERSION` is 1.36.x; the wheel carries metadata only and is not the distribution, so aligning the version is out of scope.; Credible-Threat Gate: An Unknown Factor Stays Open: Readiness round 1 amendments: "stays open" mapped to the ledger's existing `insufficient_evidence` basis with a required `promotion_trigger` (security-reviewer and red-team found `derive_disposition` would otherwise yield `dont_do_later` with no trace); the exclusion scoped to security severity, blocking and approval freshness; census exclusions named; threat-model pointer added; seed 160 entry made definite; AC-2 marker phrase; AC-3 fixture uses an unknown `authority_delta` given inline.; Credible-Threat Gate: An Unknown Factor Stays Open: Readiness round 2 clarifications (Progress Log only): Scope's "if needed" for seed 160 is superseded by Requirement 4, which makes the entry definite; `docs/architecture/threat-model.md` is edited per Requirement 3, and its pointer sentence carries the marker phrase. Test files are outside the census. The seed text says the mapping applies only when no other predicate already makes the finding action-required, and that the candidate is kept on record with its trigger; the ledger projection treats `dont_do_later` as terminal, so it does not hold a gate or status row open.

Intent outcome: achieved for the delivered fixes, not yet established downstream. The reported 3.11 stat-kind failures pass on 3.11.17 and 3.14 (11 of 11), the storage rebuild tests skip with a stated reason unless the pinned reader is installed, `pyproject.toml` builds a metadata-only wheel offline, the credible-threat gate keeps an unconfirmed candidate on record with `insufficient_evidence` and a promotion trigger (and routes unexercisable paths to the safe-execution rule), and upstream-only fixture tests skip in a copy without the content while failing here (temporary-copy run: 32 routed tests, no failure for a missing upstream file). Full suite 12100 tests OK. Each change's measure of success is the distribution's next report, which cannot be read yet. Limitations: the credible-threat candidate is kept on record, not held open, and nothing re-surfaces it; the AC-3 run shows an agent applies the rule when given it; the reported dashboard child exit did not reproduce and is out of scope.

**Changes delivered:**

- **Host-Dependent Test Failures on Python 3.11 and Newer LanceDB** (`21goe-bug host-dependent-test-failures-on-3-11-and-newer-lancedb`) — 4 ACs completed. Key decisions: Patch both path-stat call sites in the tests; Skip when the pinned reader is absent, keyed to one product constant
- **Pyproject Build Backend and License Metadata** (`21ij7-bug pyproject-build-backend-and-license-metadata`) — 3 ACs completed. Key decisions: Fix the four fields and declare no packages; Mechanism efficacy
- **Credible-Threat Gate: An Unknown Factor Stays Open** (`21ild-enh credible-threat-unknown-factor-stays-open`) — 4 ACs completed. Key decisions: State the rule once in seed 209 and summarise it in each carrier; Record an unsettled candidate through the existing `insufficient_evidence` basis and `promotion_trigger`
- **Skip Upstream-Only Fixture Tests Outside the Source Repository** (`21ile-enh skip-upstream-only-fixture-tests-outside-source-repo`) — 4 ACs completed. Key decisions: A dedicated explicit opt-in key, pinned true here; Derive the set by a temporary-copy run, not a literal-path census
## Watchpoints

- Watchpoint: seed edits need `seed_edit_allowed`; framework edits need `framework_edit_allowed`.
- Watchpoint: run the stat-kind tests on Python 3.11 with the pinned environment as well as 3.14.
- Follow-up: reply to Waveforge covering all eight items, including the declined known-failure list and a request for the dashboard child's log.

## Review Checkpoints

Intent outcome: achieved for the delivered fixes, not yet established downstream. The reported 3.11 stat-kind failures pass on 3.11.17 and 3.14 (11 of 11), the storage rebuild tests skip with a stated reason unless the pinned reader is installed, `pyproject.toml` builds a metadata-only wheel offline, the credible-threat gate keeps an unconfirmed candidate on record with `insufficient_evidence` and a promotion trigger (and routes unexercisable paths to the safe-execution rule), and upstream-only fixture tests skip in a copy without the content while failing here (temporary-copy run: 32 routed tests, no failure for a missing upstream file). Full suite 12100 tests OK. Each change's measure of success is the distribution's next report, which cannot be read yet. Limitations: the credible-threat candidate is kept on record, not held open, and nothing re-surfaces it; the AC-3 run shows an agent applies the rule when given it; the reported dashboard child exit did not reproduce and is out of scope.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer |
| SEC-DEL-1 | do_now | no | completed | security-reviewer, docs-contract-reviewer, qa-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 68 | 2,007,174 |
| implement | 72 | 480,411 |
| review | 26 | 211,652 |
| **Total** | **166** | **2,699,237** |

<!-- wave:context-efficiency-state {"generation":161,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":72,"content_source_credit":590960,"derived_artifact_credit":0,"direct_net":480411,"estimated_tokens_saved":480411,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2017,"response_debit":145553,"source_credit_count":33,"source_credit_drop_count":0,"structural_source_credit":35659,"workflow_prompt_credit":1362},"plan":{"calls":68,"content_source_credit":2195023,"derived_artifact_credit":6807,"direct_net":2007174,"estimated_tokens_saved":2007174,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4840,"response_debit":194273,"source_credit_count":111,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4457},"review":{"calls":26,"content_source_credit":284109,"derived_artifact_credit":3285,"direct_net":211652,"estimated_tokens_saved":211652,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10383,"response_debit":68594,"source_credit_count":38,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3235}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":166,"content_source_credit":3070092,"derived_artifact_credit":10092,"direct_net":2699237,"estimated_tokens_saved":2699237,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17240,"response_debit":408420,"source_credit_count":182,"source_credit_drop_count":0,"structural_source_credit":35659,"workflow_prompt_credit":9054},"wave_id":"21ilf waveforge-1-36-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 3 | 2,075,722 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":2075722,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
