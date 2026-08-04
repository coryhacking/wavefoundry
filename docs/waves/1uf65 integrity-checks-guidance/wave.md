# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-04
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1uf65 integrity-checks-guidance`
Title: Integrity Checks Guidance

## Objective

Close out the target-repo field-report items: give the five `integrity_checks` booleans real phase-aware definitions in seed-209 with the attestation contract stated plainly (1uf64, field-confirmed), unstrand the docs gate from the RELIABILITY.md graph-builder claim (1uf66), stop the routine memory-checkpoint pause from printing failure prose (1uf67, both fielded clean on 1.15.2+pgto), and stop a no-op review-policy migration from marking every readied wave for re-Prepare on every upgrade (1uf69, field-observed on two consecutive upgrades).

## Changes

Change ID: `1uf64-bug integrity-checks-readiness-semantics-undefined`
Change Status: `implemented`

Change ID: `1uf66-bug reliability-doc-claim-strands-docs-gate-on-version-bump`
Change Status: `implemented`

Change ID: `1uf67-bug checkpoint-pause-prose-still-reports-upgrade-failed`
Change Status: `implemented`

Change ID: `1uf69-bug noop-policy-migration-invalidates-readied-waves`
Change Status: `implemented`

## Participants

- Coordinator: session agent (Claude Code)
- Write-owning roles: implementer (fix workstream)
- Requested review lanes: code-reviewer, docs-contract-reviewer, qa
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, qa

Completed At: 2026-08-04

## Wave Summary

Wave `1uf65` (Integrity Checks Guidance) delivered 4 changes: Integrity-Check Booleans Have No Defined Semantics at Readiness, Inviting False Execution Claims, RELIABILITY.md Graph-Builder Claim Strands the Target's Docs Gate When the Advancer's Preconditions Miss, Routine Memory-Checkpoint Pause Still Prints "ERROR: Upgrade failed" Prose Despite Correct Typed State, and A No-Op Review-Policy Migration Still Marks Every Readied Wave for Re-Prepare on Every Upgrade. Notable adjustments during implementation: Integrity-Check Booleans Have No Defined Semantics at Readiness, Inviting False Execution Claims: Four prepare-lane reviews ran (code, qa-reviewer, docs-contract, qa; all fresh, code-grounded, MCP-first). Code and both QA lanes approved; docs-contract WITHHELD on two missed execution-only carriers (seed-239:47-57 Evidence-integrity gate; render_agent_surfaces.py:842-855 QA block rendered into docs/agents/qa-reviewer.md) and AC-3's stale mirror phrase. Resolution folded in-phase: both retentions recorded as delivery-scoped by design (editing them fixes nothing and trips three pin sites), AC-3 renamed to the real carrier set, Requirement 6 gained the anchor-not-byte-pin assertion shape, and the :138 falsifiability-clause preservation note added. Executed baselines recorded green: test_review_evidence 139 OK, CouncilSeedVerificationContractTests 9 OK, test_render_agent_surfaces 63 OK, the two contract tests OK.; A No-Op Review-Policy Migration Still Marks Every Readied Wave for Re-Prepare on Every Upgrade: Readiness council ran (red-team + docs-contract, code-grounded, MCP-first with disclosed Gapfill sweeps for index-excluded carriers). Red-team confirmed every mechanism cite, proved the guard inputs stable across build successors (both are fixed-point), found no test that fights the guard, censused all four marker consumers, and named two residuals now accepted in Requirement 4; it also established the validation-walk constraint (resume preflights depend on the plan phase). Docs-contract found three uncensused seed carriers plus an architecture doc; all folded into Requirements 4-5, Scope, ACs, and Serialization Points before the receipt mint.; A No-Op Review-Policy Migration Still Marks Every Readied Wave for Re-Prepare on Every Upgrade: Guard added in `plan_review_policy_upgrade` (`review_policy_upgrade.py:74-82`, `:96-97`): `policy_unchanged = config_after == config_before and not carriers`, then a single `continue` placed AFTER the unreadable-wave and ledger-error branches so the validation walk still reads and validates every wave while the marker, reprojection, and `WaveMigration` append are skipped. `apply_review_policy_upgrade` needs no change: an empty `plan.waves` yields `waves_marked_for_reprepare: []` and no wave write.

**Changes delivered:**

- **Integrity-Check Booleans Have No Defined Semantics at Readiness, Inviting False Execution Claims** (`1uf64-bug integrity-checks-readiness-semantics-undefined`) — 4 ACs completed. Key decisions: Keep the attestation-gate semantics; fix the guidance and the message; Keep the table-first structure; rewrite :138 to agree rather than making it the single definition site
- **RELIABILITY.md Graph-Builder Claim Strands the Target's Docs Gate When the Advancer's Preconditions Miss** (`1uf66-bug reliability-doc-claim-strands-docs-gate-on-version-bump`) — 4 ACs completed. Key decisions: Test shape mapping: the seven formerly-stranding miss shapes collapse onto the two observable doc states the lint can see (wrong value present, claim absent), so the branch tests cover them via one mismatch test with stale-claim and duplicate-claim subtests plus one dropped-claim test; the version-probe-failure shape resolves through the pre-existing expected-None message (unchanged, already names its fix), and the unreadable-file shape keeps the documented out-of-scope skip; Convergence mechanism: actionable messages only; the advancer stays byte-unchanged
- **Routine Memory-Checkpoint Pause Still Prints "ERROR: Upgrade failed" Prose Despite Correct Typed State** (`1uf67-bug checkpoint-pause-prose-still-reports-upgrade-failed`) — 3 ACs completed. Key decisions: Recognition keys on token/run-id PRESENCE in the typed block, not on a value match against the raising site; Checkpoint wording prints via `_log` (stdout plus upgrade log), not `_err`
- **A No-Op Review-Policy Migration Still Marks Every Readied Wave for Re-Prepare on Every Upgrade** (`1uf69-bug noop-policy-migration-invalidates-readied-waves`) — 4 ACs completed. Key decisions: Guard keys on the migration's own outputs (config byte delta plus carrier edit count); skip marking, writes, and reprojection on a true no-op; keep the validation walk; Accept two residuals: the pre-policy-wave seam (server_impl.py:6965) and the block-prose replay asymmetry
## Watchpoints

- Blocking: the seed-209 edit requires the `seed_edit_allowed` gate (open before, close immediately after). No rendered mirror exists for seed-209 (council-verified); `docs/contributing/review-and-evals.md` is pointer-only and already conformant.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-04: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the plan's census missed seed-209's own second execution-only definition site at :138 (byte-pinned by test_docs_lint.py:2671-2677), the sibling all-five-true validator message at review_evidence.py:3199-3201 with its pin, and the label-parameterized reach of the :2946 message into executed findings; all folded into the plan in-phase before the receipt mint; strongest-alternative: make :138 the sole canonical definition site with the field table pointing at it; rejected in the Decision Log because it inverts the operator-authored table-first structure for equal simplicity at best)
- Watchpoint: the operator's simplicity constraint is binding: one unified meaning per boolean plus one phase rule; carriers may point at the seed table instead of duplicating it; no new schema, event field, validator branch, or test module.
- Watchpoint: validator SEMANTICS are frozen (executed approvals still require all-true; non-executed findings keep the honest-false path); only the message text changes, and message-pinning tests re-point in the same change.
- Watchpoint: 1uf66 implements exactly ONE convergence mechanism (Prepare decision recorded in its Decision Log); the healthy exact-match advance stays pinned unchanged.
- Watchpoint: 1uf67 keys wording on the typed action-required state, not the phase name; the existing 1ua8t suppression pins stay green.
- Watchpoint: 1uf69's guard keys on the migration's own outputs and must preserve the plan-phase validation walk; carrier doc edits touch three seeds including 1uf64's seed-209 (seed gate open/close; do not regress the integrity-check text); the rendered upgrade prompt updates via re-render only.
- Blocking: 1uf64 is already delivered and field-confirmed; the new delivery cycle must not regress it (its prior delivery evidence chain remains in events.jsonl for reference).
- **Prepare-phase Wave Council [prepare-council] — 2026-08-04 (expanded scope, 1uf66 + 1uf67): PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: 1uf66's Requirement 1 premise was partially refuted (the mismatch lint message already names file, line, and both values; the true gaps are the missing-claim branch and the fix-hint) and its miss-shape census gained three shapes plus the injection-site answer (no code writer exists; the claim is lint-coerced agent authorship), while 1uf67's fix scope was corrected to include the WRONG on-disk lock stamp (failed_phase and failed_at written over checkpoint state, masked only by the server layer) with the fix relocated to main's except-SystemExit caller; all folded into both plans plus the messages-only mechanism decision before the receipt mint; strongest-alternative: widen the advancer to auto-heal stranded claims; rejected because the narrow form heals nothing already stranded and the wide form breaks the byte-preservation pins that encode deliberate operator-text protection)
- **Prepare-phase Wave Council [prepare-council] — 2026-08-04 (late admission, 1uf69): PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the old-code-window carrier-replay asymmetry means block-prose-only packs mark nothing under the guard, and the pre-policy-wave seam at server_impl.py:6965 loses its per-run repair net; both accepted as residuals because receipt/evaluator recomputation at every lifecycle gate remains the surviving invalidation mechanism, recorded in the Decision Log; strongest-alternative: a policy-version watermark; rejected as more machinery that still needs the byte comparison the guard already performs)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 40 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| qa | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 260 | 3,570,764 |
| implement | 22 | 940,214 |
| review | 98 | 2,450,400 |
| **Total** | **380** | **6,961,378** |

<!-- wave:context-efficiency-state {"generation":397,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":22,"content_source_credit":982854,"derived_artifact_credit":0,"direct_net":940214,"estimated_tokens_saved":940214,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":587,"response_debit":43484,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":260,"content_source_credit":4117296,"derived_artifact_credit":1497,"direct_net":3570764,"estimated_tokens_saved":3570764,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12751,"response_debit":538643,"source_credit_count":232,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3365},"review":{"calls":98,"content_source_credit":2638984,"derived_artifact_credit":3406,"direct_net":2450400,"estimated_tokens_saved":2450400,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18511,"response_debit":174825,"source_credit_count":92,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":380,"content_source_credit":7739134,"derived_artifact_credit":4903,"direct_net":6961378,"estimated_tokens_saved":6961378,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":31849,"response_debit":756952,"source_credit_count":335,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6142},"wave_id":"1uf65 integrity-checks-guidance"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 29 | 0 | 8 | 11,661,275 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":8,"estimated_exploration_avoided":11661275,"surfaced_events":29} -->
<!-- wave:exploration-avoided end -->
