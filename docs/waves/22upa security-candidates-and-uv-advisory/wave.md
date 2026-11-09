# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22upa security-candidates-and-uv-advisory`
Title: Security Candidates And Uv Advisory

## Objective

Reviewers and operators can no longer close a wave with an unconfirmed security candidate unseen: it stays open until evidence settles it or the operator closes it by name. Setup warns about a uv affected by GHSA-hq85-5cpj-mr62 and offers `--upgrade-uv`, without forcing it. The scanner worker starts isolated, and agents learn the work area is not secret-scanned.

## Changes

Change ID: `22ubf-enh unsettled-security-candidate-stays-open`
Change Status: `implemented`

Change ID: `22ubg-maint scanner-worker-isolated-mode`
Change Status: `implemented`

Change ID: `22up9-doc work-area-not-secret-scanned-note`
Change Status: `implemented`

Change ID: `22ube-enh uv-tls-advisory-at-setup`
Change Status: `implemented`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer
- Requested review lanes: security-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-11-08

## Wave Summary

Wave `22upa` (Security Candidates And Uv Advisory) delivered 4 changes: An Unsettled Security Candidate Stays Open Until Settled, Start the Scanner Worker in Isolated Mode, Note That the Work Area Is Not Secret-Scanned, and Advise Upgrading an Affected uv at Setup. Notable adjustments during implementation: An Unsettled Security Candidate Stays Open Until Settled: Readiness round 1 repair (findings 22upa-docs-surface-census-incomplete, -arch-closed-wave-rule-breaks-new-records, -arch-summary-line-projection-equality, -qa-settle-paths-unwritable, -qa-reverify-marks-unsettled-completed, -qa-ac2-closable-claim-vacuous, -cr-summary-line-drift, -cr-closed-wave-rederive, -sec-rejection-basis-evasion, -sec-operator-close-unattributed). Operator chose: trigger by facts; stop re-deriving closed waves; attested operator close on explicit instruction. Requirements, scope, ACs and decisions rewritten.; An Unsettled Security Candidate Stays Open Until Settled: Readiness cycle 1 continued: binding amendments, which take precedence over the sections above where they differ. (1) 22upa-docs-surface-census-incomplete: AC-6's census covers only the framework and contract surfaces (`.wavefoundry/framework/`, `docs/specs/`, `docs/contributing/`, `docs/agents/`, `docs/prompts/`); dated reports under `docs/reports/` and root review artifacts such as `VISION-review.md` are history and out of scope, so they are not edited. (2) 22upa-cr-closed-wave-rederive: requirement 6's skip is a `closed` parameter on `validate_review_evidence_records`, passed by both `wave_lint_lib/wave_validators.py` and `dashboard_lib._review_evidence_dashboard_state`; in closed mode the validator's repair-chain checks read each record's stored disposition instead of calling `derive_disposition`. AC-5 gains a known-bad fixture: a closed wave holding an old-rule `dont_do_later` head with `attacker_reachability: "unverified"` passes full lint and the dashboard state, and fails validation when the closed flag is not passed. Open-wave acceptance of pre-change `dont_do_later` covers superseded records as well as heads. `--upgrade-uv` handling note for 22ube is in that doc. (3) 22upa-qa-settle-paths-unwritable: requirement 5's operator close is recorded in the head's open repair cycle when one exists (after a `repair_start` or a still-unsettled reverification) and counts as terminal progress for that cycle in `_repair_cycle_progress`; when the head has no open cycle it is recorded in the wave's next cycle, never a lower one. AC-3 gains the case: a still-unsettled reverification in cycle k, then the operator close in cycle k, then another finding's `repair_start` in cycle k+1, with full docs-lint passing. Implementer notes from reviewers: `review_status_rows` must check the stored `security_unsettled` plus `pending` state; the new branch in `derive_disposition` sits before `maybe_later`.; An Unsettled Security Candidate Stays Open Until Settled: Implemented. `review_evidence.py`: `security_unsettled` joins `DISPOSITIONS`; `derive_disposition` branch after `do_now`, before `maybe_later`; builder writes it `pending`, writes a reverification that settles a `security_unsettled` head as `do_now` `pending`, and requires `fresh_context`/`independent` for any lane reverification of one; `_build_operator_close` (waiver in `evidence.waiver`, no judgment, head's open cycle or `_guided_repair_cycle`); validator `closed` parameter on `validate_review_evidence_records` and `validate_external_review_evidence` (stored disposition, no derived-field recompute), open-wave acceptance of pre-rule `dont_do_later` on heads and superseded rows, operator-close link check; `_repair_cycle_progress` and the close-time independence audit treat the operator close as terminal progress or skip it with no open cycle; `security_candidate_state` feeds the `operator-signoff` withhold (stored state only) and the guided schema gains `waiver`. `lifecycle_gates`: `unsettled_security_candidate` (blocking, added to the shared registry), advisories `security_candidate_waived` and `security_candidate_predates_rule`. `wf_close_change` reads the ledger and refuses on stored `security_unsettled` + `pending`. docs-lint and `dashboard_lib` pass `closed`. Surfaces: seeds 007, 209, 211-217, 221, 225, 236, 237, 239, the install review-wave prompt, both `docs/agents` copies, review-and-evals, mcp-tool-surface; handler digest (wf_review_event only) and lifecycle golden (`waiver` entry, declared in test_lifecycle_golden) refreshed. Caller census, `derive_disposition`: `derive_blocking` (fifth is never `do_now`, so false); `derive_review_depth` (focused); `predates_security_rule` and `_validation_disposition` (the new rules); `review_authority_projection` finding facts (non-terminal while `pending`, terminal once `operator_waived`; the withhold reads stored state); builder repair-state expression and its two `synthesis["disposition"]` assignments; the `_repair_cycle_progress` and relationship/closure checks now go through `_validation_disposition`. `validate_review_evidence_records` without `closed`: `lifecycle_gate_support._prepare_policy_state` and server_impl Prepare publication (planned, readied or open waves only), server_impl `wf_review_event` append (a write; passing `closed` would skip derivation on newly appended rows, so it is not passed; a closed wave whose stored rows would re-derive differently fails closed with `review_evidence_invalid`), `run_tests._ledger_rows` (only ledgers changed during a run; a failure keeps the strict guard). None of 503 repository wave ledgers holds a row that re-derives differently. Deviations: (1) the amendment's closed-wave known-bad (old-rule `dont_do_later` fails without the closed flag) cannot fail, because requirement 6's open-wave acceptance accepts that same record; the known-bad used is an old-rule `maybe_later` with unknown attacker reachability, which fails without the flag and passes lint and the dashboard with it (mutating either caller's flag in a scratch copy fails the test). (2) `wf_close_change` findings are wave-scoped, so it refuses for any open candidate in the wave. (3) Six seeds and qa-reviewer saying `four-way` / `exact four dispositions` were corrected to five. Gapfill: shell grep and Python reads for retrieval in large files. Known-bad: the new test file run against HEAD's review_evidence, lifecycle_gates, server_impl, wave_validators and dashboard_lib in a scratch framework copy fails AC-1 (`dont_do_later`/`not_required`), AC-2 (row `approved`, no diagnostic), AC-3 (each path refused or not closable), AC-5 (no `closed`, no advisory, four-count only); AC-4 passes on both (regression guard); AC-6 census listed 15 surfaces missing before the edits.

**Changes delivered:**

- **An Unsettled Security Candidate Stays Open Until Settled** (`22ubf-enh unsettled-security-candidate-stays-open`) — 6 ACs completed. Key decisions: Non-terminal disposition `security_unsettled`; Withhold `operator-signoff` only, not lane approvals
- **Start the Scanner Worker in Isolated Mode** (`22ubg-maint scanner-worker-isolated-mode`) — 3 ACs completed. Key decisions: `-I` on the command line
- **Note That the Work Area Is Not Secret-Scanned** (`22up9-doc work-area-not-secret-scanned-note`) — 2 ACs completed. Key decisions: Note in seed 180, pointer in 209
- **Advise Upgrading an Affected uv at Setup** (`22ube-enh uv-tls-advisory-at-setup`) — 5 ACs completed. Key decisions: Advisory on stderr every setup run, upgrade only behind `--upgrade-uv`; Upgrade installs into the tool environment, never the `PATH` uv
## Watchpoints

- Watchpoint: 22ubf changes the review ledger contract: census every `dont_do_later` consumer, and keep every closed wave passing full docs-lint.
- Seed edits need `seed_edit_allowed`; framework edits need `framework_edit_allowed`.
- Each change states Windows, macOS, Linux and WSL2 behaviour.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 22upa-arch-closed-wave-rule-breaks-new-records | do_now | no | completed | architecture-reviewer |
| 22upa-arch-summary-line-projection-equality | do_now | no | completed | architecture-reviewer |
| 22upa-cr-closed-wave-rederive | do_now | no | completed | code-reviewer |
| 22upa-cr-summary-line-drift | do_now | no | completed | code-reviewer |
| 22upa-cr-uv-advisory-runs-twice | do_now | no | completed | code-reviewer |
| 22upa-del-prerule-maybe-later-stranded | do_now | no | completed | architecture-reviewer, code-reviewer, security-reviewer, qa-reviewer, docs-contract-reviewer |
| 22upa-docs-surface-census-incomplete | do_now | no | completed | docs-contract-reviewer |
| 22upa-qa-ac2-closable-claim-vacuous | do_now | no | completed | qa-reviewer |
| 22upa-qa-reverify-marks-unsettled-completed | do_now | no | completed | qa-reviewer |
| 22upa-qa-settle-paths-unwritable | do_now | no | completed | qa-reviewer |
| 22upa-sec-operator-close-unattributed | do_now | no | completed | security-reviewer |
| 22upa-sec-rejection-basis-evasion | do_now | no | completed | security-reviewer |
| 22upa-sec-upgrade-uv-after-deps | do_now | no | completed | security-reviewer |

*Machine review state — 13 findings; current: do_now 13, maybe_later 0, dont_do_later 0, not_issue 0*
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

## Review Checkpoints

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 80 | 1,225,617 |
| implement | 26 | 0 |
| review | 124 | 5,226,984 |
| **Total** | **230** | **6,452,601** |

<!-- wave:context-efficiency-state {"generation":222,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":26,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-2072,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":754,"response_debit":3852,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2534},"plan":{"calls":80,"content_source_credit":1705906,"derived_artifact_credit":1964,"direct_net":1225617,"estimated_tokens_saved":1225617,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":56434,"response_debit":431321,"source_credit_count":93,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5502},"review":{"calls":124,"content_source_credit":5548800,"derived_artifact_credit":4903,"direct_net":5226984,"estimated_tokens_saved":5226984,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":29401,"response_debit":301094,"source_credit_count":454,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":230,"content_source_credit":7254706,"derived_artifact_credit":6867,"direct_net":6450529,"estimated_tokens_saved":6452601,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":86589,"response_debit":736267,"source_credit_count":547,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11812},"wave_id":"22upa security-candidates-and-uv-advisory"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
