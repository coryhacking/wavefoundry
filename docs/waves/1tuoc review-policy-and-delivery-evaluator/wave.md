# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-28
review-evidence-source: events.jsonl

wave-id: `1tuoc review-policy-and-delivery-evaluator`
Title: Review Policy And Delivery Evaluator

## Objective

Introduce an explicit, compatible delivery-review policy with a measured path away from universal repetition; persist one risk-selected delivery roster; and make Review and Close consume one delivery-state evaluator without dropping Close-only controls. The same wave makes review evidence phase-honest and caller-grounded, and replaces prose-only downstream cleanup with an idempotent lifecycle-section reconciler.

## Changes

Change ID: `1tsbu-enh review-policy-and-delivery-evaluator`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-07-29

## Wave Summary

Wave `1tuoc` (Review Policy And Delivery Evaluator) delivered one change: Review Policy and Delivery Evaluator. Notable adjustments during implementation: Review Policy and Delivery Evaluator: **Thought:** Repair the independently reproduced defects by bounded root-cause families: bridge selection/consumption, upgrade serialization/publication, receipt authority, and carrier reconciliation. **Gapfill:** Wavefoundry MCP retrieval tools are not attached in this Codex session, so the repair uses the codebase map followed by targeted `rg`/bounded reads. The operator explicitly declined the `docs/waves` parent-symlink finding as outside the realistic threat model; no code or AC claim will be added for it.; Review Policy and Delivery Evaluator: Bound policy approvals to an exact append-only receipt ABI; reused the lifecycle lock domain with lifecycle-before-publication ordering; added one carrier registry, old-runner/new-pack compatibility, and an honest native-Windows boundary.; Review Policy and Delivery Evaluator: Made the downstream-retirement ownership explicit after `1tsyx` withdrew its repeatedly drifting prose migration: this plan now owns complete replacement of already-installed carriers and requires production validation and tests to consume one vocabulary/scope contract.

**Changes delivered:**

- **Review Policy and Delivery Evaluator** (`1tsbu-enh review-policy-and-delivery-evaluator`) — 15 ACs completed. Key decisions: Make `build_pack.py` emit a standalone framework-only bridge bootstrap and two separately identified archives; bypass the old runner's post-extract pipeline for bridge installation, then select the feature by explicit protocol-2 pack path.; Hold lifecycle and publication locks continuously within each Upgrade transaction; use one fsynced, recovery-writer-only memory-validation pause; finalize child-computed index state in the lock-owning parent; fail outside publishers fast.
## Watchpoints

- Preserve the single readiness Council gate while changing delivery policy; do not weaken specialist-lane non-waiver semantics.
- Bind the persisted roster and Council decision into readiness authority so later edits invalidate stale approval.
- Existing enabled/disabled projects preserve enforcement on upgrade; fresh installs remain universal until the measured targeted-adoption gate passes.
- Review and Close share evaluation, but Close-only secrets, memory, unchecked-AC, operator, transition, and independence controls remain enumerated and mutation-pinned.
- Lifecycle reconciliation must preserve project prose, refuse ambiguity, and be byte-stable on retry across WSL2, macOS, and Linux; native Windows receives path-contract coverage without claiming unexecuted NTFS behavior.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ac-priority-not-recorded | do_now | no | completed | wave-council-readiness |
| ac1-invalid-truth-table-mutants-unpinned | do_now | no | completed | wave-council-readiness |
| ac11-platform-forms-collapsed-to-posix | do_now | no | completed | wave-council-readiness |
| ac14-not-bound-to-real-pack-builder | do_now | no | completed | wave-council-readiness |
| ac4-operator-and-transition-mutations-unpinned | do_now | no | completed | wave-council-readiness |
| ac5-whitespace-only-detection-method-unpinned | do_now | no | completed | wave-council-readiness |
| ac5-wrong-type-integrity-cases-unpinned | do_now | no | completed | wave-council-readiness |
| ac7-ac8-retry-branches-can-substitute | do_now | no | completed | wave-council-readiness |
| ac7-disabled-projection-can-pass-by-erasure | do_now | no | completed | wave-council-readiness |
| architecture-decision-obligation-nonbinding | do_now | no | completed | wave-council-readiness |
| background-index-launcher-writes-during-upgrade | do_now | no | completed | wave-council-delivery |
| bridge-accepts-unsupported-installed-identity | do_now | no | completed | wave-council-delivery |
| bridge-lock-style-diverges-from-product-lock-domain | do_now | no | completed | wave-council-delivery |
| bridge-pack-selection-and-identity-contract-missing | do_now | no | completed | wave-council-readiness |
| bridge-protocol-operator-guidance-not-registry-pinned | do_now | no | completed | wave-council-readiness |
| carrier-owner-permissions-and-domain-boundary-undefined | do_now | no | completed | wave-council-readiness |
| delivery-policy-disabled-has-contradictory-phase-scope | do_now | no | completed | wave-council-readiness |
| in-flight-upgrade-migrates-projection-but-not-new-authorities | do_now | no | completed | wave-council-readiness |
| integrity-checks-public-schema-is-unnamed | do_now | no | completed | wave-council-readiness |
| legacy-approval-phase-collides-with-new-currency | do_now | no | completed | wave-council-readiness |
| lifecycle-lock-acquisition-failure-not-fail-closed | do_now | no | completed | wave-council-readiness |
| lifecycle-lock-writer-census-incomplete | do_now | no | completed | wave-council-readiness |
| mandatory-pack-validation-misses-import-and-protocol-mismatch | do_now | no | completed | wave-council-delivery |
| native-retrieval-telemetry-writes-during-upgrade | do_now | no | completed | wave-council-delivery |
| native-windows-claim-exceeds-supported-platform-boundary | do_now | no | completed | wave-council-readiness |
| old-runner-new-pack-upgrade-seam-unpinned | do_now | no | completed | wave-council-readiness |
| old-runner-post-extract-writes-before-renderer-backstop | do_now | no | completed | wave-council-readiness |
| persisted-roster-can-drop-later-project-required-lanes | do_now | no | completed | wave-council-readiness |
| policy-receipt-authority-and-digest-ambiguous | do_now | no | completed | wave-council-readiness |
| policy-receipt-has-no-ledger-abi-or-approval-binding | do_now | no | completed | wave-council-readiness |
| reconciler-legacy-literals-match-no-real-carrier | do_now | no | completed | wave-council-delivery |
| reconciler-write-boundary-undefined | do_now | no | completed | wave-council-readiness |
| review-policy-documentation-family-lacks-one-registry | do_now | no | completed | wave-council-readiness |
| review-policy-registry-not-complete-production-authority | do_now | no | completed | wave-council-delivery |
| shared-evaluator-contract-not-independently-testable | do_now | no | completed | wave-council-readiness |
| supported-floor-bridge-unlocked-mixed-version-interval | do_now | no | completed | wave-council-readiness |
| targeted-council-polarity-unpinned | do_now | no | completed | wave-council-readiness |
| targeted-review-cost-case-unmeasured | do_now | no | completed | wave-council-readiness |
| upgrade-lock-domain-and-order-undefined | do_now | no | completed | wave-council-readiness |
| upgrade-protocol-generation-has-no-abi | do_now | no | completed | wave-council-readiness |
| upgrade-publication-lock-coverage-incomplete | do_now | no | completed | wave-council-readiness |
| upgrade-sentinel-is-not-serialization | do_now | no | completed | wave-council-readiness |

*Machine review evidence — 436 records; 128 runs; 42 findings; current: do_now 42, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-28: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the legacy runner's post-extract writers and Upgrade's cross-turn memory gate made the original bridge and continuous-lock designs unsafe; strongest-alternative: use a standalone atomic framework-only bridge bootstrap plus process-bounded dual-lock transactions, a restrictive memory pause, parent-owned index finalization, and fail-fast outside publishers)

## Dependencies

- `1tsyx review-lifecycle-simplification` — closed; this wave owns its explicitly deferred policy, evaluator, and downstream migration work.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 225 | 9,331,004 |
| implement | 29 | 1,560,986 |
| review | 489 | 3,373,887 |
| **Total** | **743** | **14,265,877** |

<!-- wave:context-efficiency-state {"generation":267,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":29,"content_source_credit":1654205,"derived_artifact_credit":0,"direct_net":1560986,"estimated_tokens_saved":1560986,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1112,"response_debit":93464,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1357},"plan":{"calls":225,"content_source_credit":10005309,"derived_artifact_credit":2564,"direct_net":9331004,"estimated_tokens_saved":9331004,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":71493,"response_debit":608651,"source_credit_count":368,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3275},"review":{"calls":489,"content_source_credit":4861568,"derived_artifact_credit":740,"direct_net":3373887,"estimated_tokens_saved":3373887,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":29162,"response_debit":1460605,"source_credit_count":246,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":743,"content_source_credit":16521082,"derived_artifact_credit":3304,"direct_net":14265877,"estimated_tokens_saved":14265877,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":101767,"response_debit":2162720,"source_credit_count":656,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5978},"wave_id":"1tuoc review-policy-and-delivery-evaluator"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 2 | 2261994 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":2261994,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
