# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y0gz record-layout-roots`
Title: Record Layout Roots

## Objective

When this wave closes, a downstream fork can relocate its wave and plan roots and group wave records at bounded depth by editing the module constants in `record_paths.py` at merge time (no runtime configuration; redirected from a `record_layout` config block during delivery review 2026-09-17), with the shipped constants reproducing today's `docs/waves` and `docs/plans` layout byte for byte. This is the first of the two waves that unblock Waveforge's adoption.

## Changes

Change ID: `1y042-enh record-roots-config-and-resolver`
Change Status: `complete`

Change ID: `1y043-enh nested-record-lookup`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-09-17

## Wave Summary

Delivered project-relative, fork-editable `WAVES_ROOT`, `PLANS_ROOT`, `NESTED` and `MAX_DEPTH` constants in `record_paths.py`; shared root validation; bounded nested discovery; and deterministic duplicate rejection across lifecycle tools, dashboard, lint, memory and historical attribution. Public tool schemas are unchanged. Runtime layout configuration was superseded by the simpler constants design.

Both changes and all 17 ACs are complete, with no AC deferrals. Required independent reviews and operator approval are recorded; the current framework receipt covers 9,277 tests with 12 skips. Memory validation is complete with no pending candidates. Canonical architecture, ADR and regression tests retain the lesson to use discovered record identity rather than directory-depth assumptions.

Conventional-root seed prose and a future nested-create parent parameter remain outside scope; native Windows/Linux execution remains release follow-through.

## Watchpoints

- `1y042` must land before `1y043`; the nested discovery builds on the resolver module.
- The existing `wave_implement.wave_root` key is written by installs but read by nothing, before and after this wave; it is inert, and no legacy fallback or lint hint exists (delivery-review redirect).
- Rendered prose in seeds, `AGENTS.md`, and prompt docs still names `docs/waves` as the conventional home; a one-sentence seed follow-up under the seed gate is deferred, not forgotten.
- Waveforge's exact tree is unstated; the nested option is generic and bounded. Confirm their layout before Prepare so the fixture in `1y043` mirrors it.
- Golden tool-surface fixture from `1y0do` must remain unchanged; no tool parameter is added in this wave.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ambiguous-id-not-universal | do_now | no | completed | — |
| audit-wave-snapshot-picks-one-twin | do_now | no | completed | — |
| commit-provenance-nested-wave-dir | do_now | no | completed | — |
| contract-doc-claims | do_now | no | completed | — |
| cycle2-adjacent-gaps | do_now | no | completed | — |
| dangling-symlink-root-invisible | do_now | no | completed | — |
| fail-closed-not-universal | do_now | no | completed | — |
| fail-closed-wrapper-telemetry | do_now | no | completed | — |
| lint-corpus-docs-only | do_now | no | completed | — |
| lint-validators-own-walk | do_now | no | completed | — |
| plans-cache-layout-key | do_now | no | completed | — |
| record-paths-test-pins-are-order-dependent | do_now | no | completed | — |
| resolver-identity-gaps | do_now | no | completed | — |
| root-ancestor-is-file | do_now | no | completed | — |
| supplemental-dashboard-layout-read | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| supplemental-fingerprint-depth-budget | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| supplemental-memory-reference-corpus | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| supplemental-nested-drift-attribution | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| supplemental-windows-drive-component | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| unreadable-ancestor-raises-raw-permission-error | dont_do_later | no | not_required | — |
| warm-cache-layout-flip | do_now | no | completed | — |
| wave-current-resource-serves-one-twin | do_now | no | completed | — |

*Machine review state — 22 findings; current: do_now 21, maybe_later 0, dont_do_later 1, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: approved by the operator’s explicit closure instruction; typed approval recorded.

## Dependencies

- `1y0do tool-surface-snapshot` should close first so both changes can assert an unchanged public surface.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| credit_history_unavailable | 0 | 0 |

<!-- wave:context-efficiency-state {"generation":513,"measurement_status":"credit_history_unavailable","pending":false,"schema_version":1,"stages":{"implement":{"calls":104,"content_source_credit":685795,"derived_artifact_credit":2155,"direct_net":624295,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3749,"response_debit":64429,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4523},"plan":{"calls":13,"content_source_credit":24184,"derived_artifact_credit":355,"direct_net":3357,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2753,"response_debit":23011,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4582},"review":{"calls":386,"content_source_credit":9452595,"derived_artifact_credit":3410,"direct_net":8635681,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":85123,"response_debit":737203,"source_credit_count":322,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":503,"content_source_credit":10162574,"derived_artifact_credit":5920,"direct_net":9263333,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":91625,"response_debit":824643,"source_credit_count":348,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11107},"wave_id":"1y0gz record-layout-roots"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 19 | 0 | 13 | 12,389,223 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":13,"estimated_exploration_avoided":12389223,"surfaced_events":19} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: 1y042's own success criterion was transitively coupled to an unrelated maintainer-only wave; strongest-alternative: a self-contained schema-pin test for the eight touched lifecycle tools, applied in-session).
- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: code-reviewer, qa-reviewer, reverifier; rotating-seat: docs-contract-reviewer not re-convened, its 2026-09-17 transfer-package findings stand; strongest-challenge: the code-reviewer showed the plan's census mixed two predicates and missed the two-token join form the real construction sites use, so the routing scope and the census test were mis-sized; strongest-alternative: state both predicates with their figures, list all 35 files, and name every construction site by symbol, applied in-session; also applied: the `_tag_utils.infer_tags` wave classifier added to both changes, the once-per-invocation mechanism fixed at the `McpRepoCache.list_waves_cached` seam, AC-4 split, AC-8 added for three untested cold sites; an independent reverifier refuted three details of the first repair and all three were corrected before approval).
- **Delivery-phase Wave Council [delivery-council] — 2026-09-17: PASS after three repair cycles** (moderator: wave-council; primer-depth: standard; seats: code-reviewer, qa-reviewer, red-team primer, fixed seats architecture-reviewer and docs-contract-reviewer; rotating-seat: integrator-operator, which found the lint-corpus gap (lint and gardener walkers followed `docs/` only, so a relocated root outside `docs/` was never linted); strongest-challenge (red-team primer): the identity of a root was validated by spelling and containment, not by identity, so a case-variant or symlink-equivalent spelling of one directory passed as two roots; strongest-alternative: canonicalize the root, then validate, comparing by inode (adopted, then extended to the nearest existing ancestor, file and dangling-symlink ancestors, and symlink or case aliases); material disagreement: the rotating seat offered two options for the lint-corpus gap, union the resolved roots into the lint walkers or refuse roots outside `docs/`, resolved by the moderator for union because the ACs promise such roots; operator redirect during cycle 1: the layout moved from a runtime `record_layout` config block to fork-editable module constants in `record_paths.py`, which removed the runtime-dynamic surface behind three of the seven cycle-1 findings; sixteen finding heads recorded in `events.jsonl` across cycles 1 to 4 (seven in cycle 1, four plus the wrapper-telemetry head in cycle 2, three in cycle 3, one test-isolation head and one categorically-out-of-scope permission observation in cycle 4), fifteen do_now and every one repaired and independently reverified with fresh context, one dont_do_later (an unreadable ancestor directory is an environment fault outside the layout contract); seat verdicts at synthesis: code-reviewer APPROVE (cycle 3, whole tree), qa-reviewer APPROVE (cycle 3, full AC table), architecture-reviewer APPROVE (cycle 2), docs-contract-reviewer REPAIRED on all heads (cycle 4), red-team REPAIRED on all heads (cycle 4), integrator-operator REPAIRED (cycle 2); full suite green at 9,264 tests with the receipt refreshed after the final test-isolation fix).


## Supplemental repair checkpoint

2026-09-17: Five supplemental heads repaired and independently reverified by fresh code-reviewer and qa-reviewer contexts. Focused delivery council replay approved, with standard-depth adversarial/constructive/simplicity primer; participants: council/primer, code-reviewer, qa-reviewer (no claim of rerunning the earlier full seat roster). Strongest challenge was consumer omissions or weakened containment/history; chosen alternative reuses validated roots and discovered identities with no new configuration. Agreement unanimous; no remaining supplemental finding. Evidence: [supplemental review and repair report](supplemental-goal-review.md).

Full framework suite: 9,277 tests across 103 files passed, 12 skips. Roots remain project-relative constants and public record paths remain repository-relative; absolute paths are internal resolved filesystem values. Native Windows/Linux execution is not newly qualified by this pass. Operator signoff, closure, commit, and push are not authorized by this repair request.

Memory checkpoint: one new generated draft rejected as non-actionable/duplicate after evidence and current-target review; prior dispositions respected. Fresh-process response functions completed the checkpoint because the attached stale MCP could not acquire its memory fence. Framework gate is closed; full host restart remains necessary for the preexisting runner mismatch.

## Closure reconciliation

Both admitted changes are complete; all ACs and tasks are checked, with no `[~]` AC deferrals. Required code, QA, readiness and delivery council approvals are current, and operator closure approval is recorded. Docs-contract review was performed and its findings repaired as recorded above.

Delivered: project-relative fork-editable roots, bounded nested discovery, deterministic duplicate rejection, and consistent lifecycle/dashboard/lint/memory consumers. Public tool schemas remain unchanged. Runtime layout configuration was deliberately removed in favor of module constants.

Retrospective: validate every consumer against discovered record identity, not directory depth or basename assumptions; keep filesystem resolution internal and persisted/public paths project-relative. These lessons are captured in the canonical architecture/ADR and regression tests; no additional memory duplication is warranted. Memory proposal replay respected all eight dispositions and produced zero pending candidates.

Out-of-scope follow-ups remain the conventional-path prose in seeds and a future explicit nested-create parent parameter; neither is an unmet AC. Native Windows/Linux execution remains release follow-through.

The MCP host restart is verified: runner matches disk, index is ready, integrity is OK, and semantic/graph generations agree. The prior restart warning is resolved. Closure updates the session handoff to idle with deferred decisions retained.
