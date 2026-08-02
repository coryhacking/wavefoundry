# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-08-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1u8o2 downstream-field-report-fixes`
Title: Downstream Field Report Fixes

## Objective

Repair the four defects from the Solaris downstream field report (2026-08-01) that are genuinely new or long-unfiled: unbounded blank-line growth in rendered `.aiignore`, orphaned graph and sidecar store rows surviving every incremental build, the doc-drift classifier failing closed on deletion frames while audit reports a clean zero, and coherence-scan noise on pack-owned migration text. This wave ships now because all four are field-confirmed on a real downstream repository, and three of them silently misreport state, which is the defect class this project has been systematically eliminating.

## Changes

Change ID: `1u725-bug aiignore-render-accumulates-blank-lines`
Change Status: `planned`

Change ID: `1u8nz-bug index-removal-missed-when-path-leaves-scope-before-disk`
Change Status: `planned`

Change ID: `1u8o0-bug doc-drift-classifier-fails-every-build-silently`
Change Status: `planned`

Change ID: `1u8o1-bug coherence-scan-flags-pack-owned-migration-text`
Change Status: `planned`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (single `fix` workstream, four ordered changes)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

## Wave Summary

Four-change bug wave filed from one downstream field report, then substantially corrected by the prepare cycle's executed grounding: a renderer idempotency fix (`render_aiignore`); an orphan-store reconciliation at the existing reap seam inside the build epoch (graph plus freshness and secret-scan sidecars; the filed registry-minus-disk design was refuted, since Lance already self-heals); a red-first fix for the reproduced deletion-frame classifier trigger plus per-return-site reason taxonomy and a first-failure staleness surface (Required additive spec update); and checker-side name resolution for pack-owned seed text with seed-160's debris identification extended in place (gated).

## Watchpoints

- RESOLVED at prepare (2026-08-01): both reporter hypotheses were code-grounded by two independent executing reviewers and BOTH failed. 1u8nz's scope-exclusion root cause is refuted (all deletion orderings heal on the current tree; the verified defect is orphaned graph and sidecar rows, and the plan was rewritten around it). 1u8o0's never-succeeds premise is refuted (the classifier succeeds on this repo and environment); the reproduced trigger is the living-doc deletion frame failing the parser closed, now the plan's red-first target.
- Watchpoint: 1u725's fix must not eat intentional blank lines inside project-owned `.aiignore` content; the field report's suggested fix has exactly that trap, and AC-1 carries the exact-content first-render assertion that catches it.
- Watchpoint: 1u8nz's reconciliation is conservative on IO errors (ENOENT removes; EACCES/EIO preserves) with a mass-removal circuit breaker, runs inside the build epoch at the existing reap seam, and a removal-only pass opens and finalizes an epoch.
- Watchpoint: 1u8o1's seed-160 `wave_open_gate` mentions are migration instructions that MUST keep the retired name; the fix is checker-side scope. The seed edit (debris paragraph) is gated: open `seed_edit_allowed` before, close immediately after; re-render the prompt mirror.
- Watchpoint, serialization: 1u8nz and 1u8o0 both edit `index_state_store.py`; 1u8o0 and 1u8o1 both edit `server_impl.py`'s `wf_audit` response assembly. Land the two audit-shape edits against `docs/specs/mcp-tool-surface.md` in one pass, and sequence the index-store changes, never interleave.
- Watchpoint: the 1u5vl delegation and 1u44n publication test clusters stay green. Executable rerun list: the seam six (`test_upgrade_wavefoundry`, `test_review_policy`, `test_index_state_store`, `test_upgrade_protocol`, `test_server_tools`, `test_reconcile_scan`) plus this wave's surfaces (`test_render_platform_surfaces`, `test_indexer`, `test_graph_indexer`, `test_doc_drift`), then the full suite.
- Watchpoint: uncommitted tree carries the closed 1u5vl delivery plus the two release-prep doc edits; per standing practice, commit before implementation touches shared files (operator authorized commits this session at the analogous point; confirm before running one).

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: both reporter-supplied root causes failed executed code-grounding by two independent reviewers, forcing full rewrites before readiness. 1u8nz's scope-exclusion hypothesis was refuted end to end (all four deletion orderings heal on the current tree; removal detection diffs the unfiltered registry at indexer.py:990; the Lance eligibility reaper at :2284 already retires scope-departed paths), and the verified defect was relocated to orphaned store rows: graph file rows plus the freshness and secret-scan sidecars survive every incremental build, healed only by a full graph rebuild, which itself contradicts the reporter's zero-removals and mints the pack-lineage requirement. 1u8o0's never-succeeds premise was refuted by executing the real classifier successfully on the affected environment class, and the red-team reproduced the deterministic trigger synthetically: a living-doc deletion frame fails the parser closed at index_state_store.py:3400, persisting only under the delete-then-recreate condition the code lane then pinned into the fixture requirement. Both seats verified every rewrite-introduced citation against the tree, including the twelfth coherence finding in the rendered prompt mirror that proves pack-path exclusion alone insufficient for 1u8o1; strongest-alternative: unconditional exclusion of the pack from the coherence scan, rejected because it would silence this repository's only automated stale-seed-text audit, with requirement 2 instead forcing a recorded choice between a conditional exclusion with an upstream carve-out and a non-blocking pack-internal classification, the coverage tradeoff stated honestly. All five reviewers returned CONFIRM verdicts on the final bytes after the consolidated repair pass; docs-lint clean.)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 7 records; 1 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| architecture-reviewer | pending | no current executed approval | record approval evidence for architecture-reviewer |
| docs-contract-reviewer | pending | no current executed approval | record approval evidence for docs-contract-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 124 | 1,619,752 |
| **Total** | **124** | **1,619,752** |

<!-- wave:context-efficiency-state {"generation":124,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":124,"content_source_credit":1854052,"derived_artifact_credit":1416,"direct_net":1619752,"estimated_tokens_saved":1619752,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7727,"response_debit":231354,"source_credit_count":75,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3365}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":124,"content_source_credit":1854052,"derived_artifact_credit":1416,"direct_net":1619752,"estimated_tokens_saved":1619752,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7727,"response_debit":231354,"source_credit_count":75,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3365},"wave_id":"1u8o2 downstream-field-report-fixes"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
