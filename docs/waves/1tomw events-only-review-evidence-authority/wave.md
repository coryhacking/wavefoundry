# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-27
review-evidence-source: events.jsonl

wave-id: `1tomw events-only-review-evidence-authority`
Title: Events Only Review Evidence Authority

## Objective

Make each wave's `events.jsonl` the sole machine authority for executable review evidence, removing the global adoption receipt and completed self-host migration state. Preserve direct ledger validation, cross-process serialization, exact replay, released-version upgrade safety, and the human current-state projection without replacing the removed receipts with another hash scheme.

## Changes

Change ID: `1to8f-enh events-only-review-evidence-authority`
Change Status: `complete`

Completed At: 2026-07-27

## Wave Summary

Wave `1tomw` (Events Only Review Evidence Authority) delivered one change: Events-Only Review Evidence Authority. Notable adjustments during implementation: Events-Only Review Evidence Authority: Implemented the full cutover: `review_evidence.py` reduced to direct declared-ledger validation plus the renamed `project_state_publication_lock` (same physical path, same reentrancy, RuntimeFileLock inlined); all adoption/proof/migration functions, constants, and exports deleted. Reconciled every runtime consumer: lint applicability now declaration-or-inline-marker only; dashboard fail-closed on declared damage without receipt reads; indexer exclusion is purely the fixed wave-folder role (structural, no wave.md read); `index_state_store` and all ~25 server lock sites renamed; typed-event transaction is ledger commit then projection with `projection_stale` partials and exact replay. Upgrade projector fully retired (def + three invocations + extension hook + `resume_after_gate` projection branch + summary/recovery fields); new `phase_review_evidence_sidecar_cleanup` does confined one-way deletion of both sidecars with held-lock refusal on both shipped lock paths, v1.13 root-lock cleanup after proof, and `restart_required` reporting; `externalize_adopted_inline_wave_locked` bridge removed. Migrator + dedicated tests deleted; `test_build_pack.py` now asserts pack ABSENCE. Seeds 100/160/209 updated first, surfaces re-rendered, create-wave install template edited, upgrade prompts and five architecture/spec/contributing docs reconciled, codebase map regenerated from a fresh graph.; Events-Only Review Evidence Authority: Final verification and self-host cutover. Full canonical suite: 6,295 tests across 59 files, all pass (309s). Docs lint clean via `wf_validate_docs`; `git diff --check` clean. MCP server reloaded in-process (`impl_matches_disk: true`, 83 tools re-registered, `wf_review_event` description propagated). Live one-way cleanup executed through the real `phase_review_evidence_sidecar_cleanup` path on this repository: both retired sidecars removed plus a stale v1.13 root lock, `restart_required` reported; post-cutover docs lint and lifecycle reads verified clean on the reloaded server. All ACs checked; change status advanced to review. The `.junie/mcp/mcp.json` diff is canonical-renderer reconciliation of the cwd-independent launcher form (wave 1tj0l), produced by the required re-render step. Upgrade fixture shapes are derived from the v1.12/v1.13/v1.14 tag inspection recorded at readiness (reality-checker seat); post-restart operation is proven by the whole suite running the new implementation.; Events-Only Review Evidence Authority: Delivery review executed: red-team primer (full depth) plus four fixed seats in fresh independent contexts, all initially CHANGES REQUESTED. Five typed findings recorded and repaired in cycle 1: DF1 the delivered residue census was red against the post-suite session-handoff rewrite (handoff reworded by role; census known-bad control strengthened to run planted files through the real scan helpers; census scope preserved per 3-1 seat consensus); DF2 the documented honesty boundary omitted declaration-removal-with-surviving-ledger (seed 209, data-and-control-flow, review-and-evals amended with the accurate detected/detectable split; first reverification round caught a residual review-and-evals clause, repaired and cleared by a second fresh context); DF3 the review_sidecar_cleanup refusal message directed operators into the gate's own refusal loop (now says re-run the full upgrade, consistent with all carriers, recovery route traced working); DF4 AC-5 evidence overstated the tests (fixture rebuilt through canonical producers with a validator assertion; new post-cutover public typed-event append test; non-None race-window assertions); DF5 orphaned _write_bytes_atomic helper deleted with an AST zero-caller sweep confirming no further orphans. All lanes cleared by fresh independent reverifications; wave-council delivery synthesis in a fresh context APPROVED with max unresolved severity none.

**Changes delivered:**

- **Events-Only Review Evidence Authority** (`1to8f-enh events-only-review-evidence-authority`) — 11 ACs completed. Key decisions: Make `events.jsonl` the sole review authority and remove receipt hashes entirely.; Keep the existing source declaration as the applicability marker.
## Watchpoints

- Watchpoint: the typed-inline review format never shipped; upgrade tests must prove the released boundary instead of preserving a fallback reader.
- Do not rename or delete `.wavefoundry/locks/review-evidence-adoptions.lock` in this wave; retain the v1.13 root-lock literal only in the bounded upgrade probe/tests. Upgrade is a maintenance window, not a mixed-version compatibility mode.
- Preserve atomic visibility and exact-replay guarantees without implying `fsync` or power-loss durability.
- The deletion census excludes only closed historical records and the documented stable lock-path literal; no dormant adoption or migration implementation may remain.
- Implementation guard: preserve the council-approved v1.12/v1.13/v1.14 matrix, confined deletion, full-host restart, upgrade-projector retirement, reentrant lock topology, public subprocess/known-bad oracle, MCP resources, and canonical carrier census; any boundary change reopens readiness.

## Participants

- Coordinator: `wave-council`
- Adversarial primer: `red-team`
- Fixed readiness seats: `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`
- Rotating readiness seat: `docs-contract-reviewer`

## Review Checkpoints

- pre-implementation-review: passed (2026-07-27) — highest risk is the project-global lock rename rippling through ~40 call sites including test mocks and the AST-based lock census in `test_server_context_efficiency.py`; addressed by an exact-token inventory (163 hits across 9 symbols) completed before the first edit, case-insensitive rename verification, and landing the `review_evidence.py` API change plus all import reconciliation as one coherent edit per the serialization points. Second risk: `server_impl.py` context-efficiency instrumentation is a known fragile area (memory 1t1wx); edits there stay outside the cost wrapper and are verified against canonical response builders.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-27: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: safe removal of the inline/adoption upgrade bridge while preserving tagged upgrade history, confined cleanup, and the publication-lock cutover; strongest-alternative: version-gated bridge or higher upgrade floor, rejected because no released tag contains typed-inline authority)
- Readiness adversarial primer — `red-team`, full depth: strongest challenge was that the draft treated all inline/adoption migration code as self-host-only even though `phase_review_status_projection` still called a general inline bridge; strongest alternative was a version-gated expand/contract bridge or an explicit upgrade-floor change. The first repair incorrectly dated external ledgers to 1.14; fixed-seat tag inspection corrected the matrix to v1.12 prose-only, v1.13 external ledger on the old root lock, and v1.14+ external ledger on the current lock. The plan now requires tag-derived preservation fixtures and an explicit maintenance-window/restart boundary rather than a data fallback or a false mixed-version guarantee.
- Fixed-seat review round 1 — CHANGES REQUESTED. Architecture, security, and QA independently reproduced the wrong release boundary; architecture also found that a shared lock pathname does not make old adoption-receipt and new events-only state machines compatible; QA found the lock's true consumer scope was broader than review events, AC-2 omitted MCP resources, AC-3 did not pin the public transaction, and the crash matrix lacked named cut points. All are repaired in the plan; readiness remains withheld for fresh rerun.
- Fixed-seat review round 2 — CHANGES REQUESTED. Fresh architecture/security/QA contexts confirmed the release matrix and maintenance-window direction, then sharpened five remaining contracts: root-confined sidecar deletion; role-aware allowance for both shipped lock literals; exact `project_state_publication_lock` reentrancy and outer-lock order; deterministic contention plus known-bad detection; and one unambiguous full-host restart boundary. The plan now carries each as a required AC; readiness remains withheld for the final fresh pass.
- Rotating-seat review — CHANGES REQUESTED. `docs-contract-reviewer` found the upgrade projector still rewrote `wave.md` despite the byte-preservation AC, and the plan omitted seed 160 plus several rendered/spec/contributing carriers; it also found the cross-cutting lock document was conditionally scoped despite an unconditional rename. Requirement/AC-11 now retires the projector, recovery/resume/summary surface, and hot-reload claim coherently and names the full carrier set; readiness remains withheld for recheck.
- `prepare-council: APPROVE — moderator: wave-council; primer-depth: full; seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating-seat: docs-contract-reviewer; strongest-challenge: safe removal of the inline/adoption upgrade bridge while preserving tagged upgrade history and lock cutover; strongest-alternative: version-gated bridge or higher upgrade floor, rejected because no released tag contains typed-inline authority; seat-agreement: unanimous; max-severity: none`
- **Delivery-phase Wave Council [delivery-council] — 2026-07-27: APPROVE** (moderator: wave-council, fresh synthesis context; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, all fresh contexts; all seats initially CHANGES REQUESTED; five typed findings DF1-DF5 recorded, repaired in cycle 1 with `repair_start` before mutation, and independently reverified by distinct fresh lanes; the DF2 first reverification round withheld clearance on a residual doc claim, repaired and cleared by a second fresh context; material disagreement: DF1 census-repair strategy, exclude-handoff-from-scope vs reword-handoff, resolved 3-1 for reword with census scope preserved and the resolution verified implemented; strongest-challenge: whether documenting the declaration-removal blind spot suffices versus forcing the detector into this wave, resolved for honest documentation plus operator-decided follow-up; strongest-remaining-risk: the undetected declaration-removal window, honestly documented, with the optional stateless orphan-ledger lint diagnostic surfaced as follow-on scope; seat-agreement: unanimous after repairs; max-unresolved-severity: none. Post-repair evidence: full canonical suite 6,296 tests across 59 files all passing, docs lint clean, census 4/4.)
- `Review wave` — AC priority reconciliation: qa-reviewer walked AC-1 through AC-11 against delivered behavior; every required row has executed verification evidence (AC-5 and AC-7/AC-10 gaps found during review were repaired as DF4 and DF1 and re-attested); the AC priority table is unchanged from readiness and matches shipped behavior.
- `Review wave` — AC scope gap check: one follow-on item surfaced for the operator, a stateless orphan-ledger lint diagnostic (non-empty `events.jsonl` in a wave-shaped folder whose `wave.md` lacks the declaration fails lint); deliberately not added in this wave because it is behavior beyond the enumerated requirements; if adopted later, the three boundary-clause carriers are re-worded in that same change.

## Prepare Review Evidence

- `red-team`: full-depth primer completed. Strongest challenge: prove removing `externalize_adopted_inline_wave_locked` does not violate skipped-version upgrades. Strongest alternative: retain a temporary version-gated bridge or raise the upgrade floor. Primer questions covered the earliest external-ledger release, treatment of typed-inline state, all-writer lock quiescence, true subprocess concurrency, and the boundary between process-crash replay and power-loss durability. Findings RT-001 through RT-004 were incorporated into the plan before fixed-seat review.
- `architecture-reviewer`: round-1 CHANGES REQUESTED — tag evidence corrected the release matrix; same-path locking alone does not reconcile old receipt writers with new events-only writers. Required an explicit cutover contract and non-overstated compatibility.
- `security-reviewer`: round-1 CHANGES REQUESTED — integrity/readiness defect, security severity none under the trusted local-operator threat model. Required v1.12/v1.13/v1.14 tag fixtures and an honest mixed-version boundary.
- `qa-reviewer`: round-1 CHANGES REQUESTED — required the broad lifecycle/state-publication consumer census, exact public two-process append oracle, named termination/projection cuts, MCP resource coverage, and lint-clean watchpoint.
- `architecture-reviewer`: round-2 CHANGES REQUESTED — required role-aware two-path residue rules, exact reentrant publication-lock topology/census, and a single host-convergence contract.
- `security-reviewer`: round-2 CHANGES REQUESTED — security severity none, integrity severity medium; required repository-confined sidecar deletion and consistent broad lock naming.
- `qa-reviewer`: round-2 CHANGES REQUESTED — required bridge-vs-authority wording, a deterministic interprocess contention handshake with a known-bad mutant, and consistent broad lock naming.
- `reality-checker`: APPROVE — validated all 38 current adoption entries against their sibling ledgers, the three tagged release shapes, the 112-reference live census, direct ledger/replay seams, and the proportional maintenance-window boundary; no hidden implementation blocker.
- `docs-contract-reviewer`: CHANGES REQUESTED — required deletion of the upgrade projector and owned recovery/resume/summary contracts, explicit seed 160/rendered upgrade/MCP/build-doc ownership, and unconditional cross-cutting lock documentation.
- `architecture-reviewer`: APPROVE on recheck — exact `project_state_publication_lock` semantics, outer-lock order, caller census, role-aware lock literals, and full-host restart boundary are complete without a data fallback.
- `security-reviewer`: APPROVE on recheck — confined sidecar deletion and broad lock semantics are explicit; no residual security/integrity finding.
- `qa-reviewer`: APPROVE on recheck — tag fixtures, deterministic interprocess contention/known-bad control, named crash cuts, resources, index and upgrade oracles are non-vacuous.
- `docs-contract-reviewer`: APPROVE on recheck — Requirement/AC-11 owns projector/recovery removal, seed 160, rendered upgrade prompts, MCP spec, contributing docs, tests, and unconditional cross-cutting lock documentation.
- `wave-council`: APPROVE — full-depth final synthesis independently validated the repaired plan against current code and v1.12/v1.13/v1.14 tags; unanimous seat agreement, maximum unresolved severity none.
- Product-owner acknowledgment: the operator directed removal of both obsolete global JSON files and all dead adoption/migration code, with Git retained for optional historical analysis and no replacement fallback/hash authority. Upgrade remains a controlled maintenance operation; the plan must preserve supported stored history and state its host-restart boundary honestly.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DF1-census-red-on-delivered-tree | do_now | no | completed | — |
| DF2-declaration-removal-boundary-understated | do_now | no | completed | — |
| DF3-sidecar-refusal-recovery-message-dead-end | do_now | no | completed | — |
| DF4-ac5-evidence-overstates-delivered-tests | do_now | no | completed | — |
| DF5-dead-write-bytes-atomic-helper | maybe_later | no | completed | — |

*Machine review evidence — 56 records; 17 runs; 5 findings; current: do_now 4, maybe_later 1, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: approved (2026-07-27, operator instructed closure after the delivery review)

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 319 | 3,044,782 |
| implement | 20 | 1,386,692 |
| review | 232 | 4,060,268 |
| **Total** | **571** | **8,491,742** |

<!-- wave:context-efficiency-state {"generation":305,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":20,"content_source_credit":1428677,"derived_artifact_credit":0,"direct_net":1386692,"estimated_tokens_saved":1386692,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1793,"response_debit":41765,"source_credit_count":53,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1573},"plan":{"calls":319,"content_source_credit":3986080,"derived_artifact_credit":69,"direct_net":3044782,"estimated_tokens_saved":3044782,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11315,"response_debit":933423,"source_credit_count":193,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3371},"review":{"calls":232,"content_source_credit":4667000,"derived_artifact_credit":480,"direct_net":4060268,"estimated_tokens_saved":4060268,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20542,"response_debit":587882,"source_credit_count":192,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1212}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":571,"content_source_credit":10081757,"derived_artifact_credit":549,"direct_net":8491742,"estimated_tokens_saved":8491742,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":33650,"response_debit":1563070,"source_credit_count":438,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6156},"wave_id":"1tomw events-only-review-evidence-authority"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 2 | 894801 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":894801,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
