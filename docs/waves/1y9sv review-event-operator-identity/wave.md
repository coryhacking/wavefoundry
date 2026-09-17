# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y9sv review-event-operator-identity`
Title: Review Event Operator Identity

## Objective

When this wave closes, every review event written through `wf_review_event` (approval, finding, run, including the close-time operator signoff) can record an available contributor handle resolved from a committed contributors map keyed by git email, and the wave record's review-status table shows who approved. Now because the ledger records roles but no person, so accountability on a shared repository lives only in git history.

## Changes

Change ID: `1y9su-enh review-event-operator-identity`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (coordinator integration, resolver and ledger workers)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-09-17

## Wave Summary

Wave `1y9sv` (Review Event Operator Identity) delivered one change: Record The Human Operator On Review Events. Notable adjustments during implementation: Record The Human Operator On Review Events: Prepare council repairs: named the two validator call sites and the one shared optional-set constant; named `build_compact_review_event` and its three context literals as the insertion point; excluded the identity from the request-digest payload and added AC-8; collapsed the `source` enum to `explicit` and `git_email` with a free-text reason for unresolved cases. Refuted: the red-team claim that no reload eviction block exists at the top of `server_impl.py`; the block commented "Evict lifecycle-validation modules" is there and Requirement 6 now quotes it; Record The Human Operator On Review Events: Reflect / repair: full suite exposed required stdin isolation and Windows console suppression on Git lookup, plus exact schema/advisory inventories and a contiguous reload census. Added isolation kwargs and tests, updated only the admitted inventories, moved eviction entry to preserve unrelated census. Thirteen focused checks pass. Many initial suite failures came from CommandLineTools Python3.9 shadowing venv Python3.13 in child commands; corrected PATH and reran full suite.

**Changes delivered:**

- **Record The Human Operator On Review Events** (`1y9su-enh review-event-operator-identity`) — 8 ACs completed. Key decisions: Contributor handle resolved from a committed map keyed by git email, with an optional explicit override; Unresolved identity never refuses an event; warn for configuration problems, remain silent when the map is absent
## Accounting correction

Removed 113,050,624 invalid tokens credited to the binary index database; retained the original row and correction rationale in [the audit record](evidence/context-accounting-correction.json). Remaining context figures use a whole-file baseline and are **not measured token savings**. The estimator fix is separately planned by operator request.

## Watchpoints

- Adds one optional parameter to `wf_review_event`, so the golden tool-surface fixture from `1y0do` must be regenerated as a named step if that wave has landed first; otherwise pin the schema in this change's own test.
- Seed `209-agent-harness-core` edit requires opening and closing the `seed_edit_allowed` gate; rendered role docs are regenerated, not hand-edited.
- Enforcing that repairer and reverifier handles differ is deliberately deferred to a follow-up after field data.
- The new module must be added to the `sys.modules` eviction block at the top of `server_impl.py` or it stays stale across `wf_reload_mcp`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: approved by explicit operator close request, recorded in typed delivery evidence.

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 93 | 1,610,677 |
| implement | 111 | 1,694,332 |
| review | 22 | 487,809 |
| **Total** | **226** | **3,792,818** |

<!-- wave:context-efficiency-state {"generation":152,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":111,"content_source_credit":1886166,"derived_artifact_credit":208,"direct_net":1694332,"estimated_tokens_saved":1694332,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4346,"response_debit":189791,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2095},"plan":{"calls":93,"content_source_credit":1750285,"derived_artifact_credit":1149,"direct_net":1610677,"estimated_tokens_saved":1610677,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5822,"response_debit":143124,"source_credit_count":125,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8189},"review":{"calls":22,"content_source_credit":516919,"derived_artifact_credit":762,"direct_net":487809,"estimated_tokens_saved":487809,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3819,"response_debit":28055,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":226,"content_source_credit":4153370,"derived_artifact_credit":2119,"direct_net":3792818,"estimated_tokens_saved":3792818,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13987,"response_debit":360970,"source_credit_count":177,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12286},"wave_id":"1y9sv review-event-operator-identity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 8 | 0 | 5 | 6,730,731 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":6730731,"surfaced_events":8} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: red-team showed the request digest hashes the semantic event payload, so an identity carried in that payload would turn a replayed retry into a conflicting write; strongest-alternative: keep the identity outside the digest payload and pin it with AC-8, applied in-session; also named the two validator call sites and the three `build_compact_review_event` context literals, collapsed the source enum to two values; docs-contract seat found no residue of the earlier larger design and no unfalsifiable AC; refuted: the claim that no reload eviction block exists near the top of `server_impl.py`).

- **Plan review resolved — 2026-09-17:** operator requested minimal best-effort attribution. The change now covers the identified-builder wrapper and fourth convergence context, ambiguous emails, absent-versus-invalid map diagnostics, and immutable original attribution on replay. No production edits or delivery approval. Requirements/AC edits require refreshed Prepare authority and the outstanding required lane reviews before implementation; the prior council entry remains historical evidence.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: optional attribution must never invalidate otherwise valid events; strongest-alternative: explicit-only handle is smaller but loses accepted automatic mapping; agreement: unanimous; max-severity: none). Code and QA independently confirmed four contexts and existing public replay fixtures. Blank handles are malformed map data; no new rule or infrastructure. Product-owner acknowledgment: operator authorized prepare/review/implementation with simplest best-effort attribution.
- Allocation: coordinator owns server integration and spec/seed; implementer workers own resolver/tests and ledger/tests on disjoint paths. Current capable models retained for protocol changes; no unmeasured efficiency claim. Gapfill: stale semantic/definition MCP paths required narrow shell location scans; working MCP code_read validated current sources.

- **Delivery lanes — 2026-09-17: PASS.** Independent code-reviewer, qa-reviewer and docs-contract-reviewer found no actionable identity defects. Current receipt selects no delivery council. Executed checks, stable fingerprints, mutation table and limitations: [delivery review](evidence/delivery-review.md). No unresolved tree-moved finding; all eight ACs and all tasks completed, no deferrals.
- **Retrospective / memory checkpoint — 2026-09-17:** preserve original attribution outside request identity; already canonical in seed209/spec and decision log. `memory_propose(mode=create)` produced zero candidates and no pending validation. No duplicate memory promotion needed. Accounting defect corrected only for this wave; estimator repair separately requested.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: reader may mistake local attribution for authenticated personal approval; strongest-alternative: explicit-only mapping loses requested automatic lookup; agreement: current plan and unchanged executed implementation retain explicit reference-only limits). Refreshed current receipt after completion-document digest moved; no source change.
