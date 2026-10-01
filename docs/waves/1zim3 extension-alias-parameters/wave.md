# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zim3 extension-alias-parameters`
Title: Extension Alias Parameters

## Objective

Let a distribution with a renamed vocabulary serve tools whose parameter names match its vocabulary, with renamed and pinned parameters on an alias, while every name-keyed control stays on the canonical tool, and let an override delegate to the core handler without copying internals.

## Changes

Change ID: `1zim0-feat extension-alias-parameter-mapping`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-01

## Wave Summary

Wave `1zim3` (Extension Alias Parameters) delivered one change: Extension Aliases Can Rename and Pin Parameters, and Overrides Can Delegate to the Core Handler. Notable adjustments during implementation: Extension Aliases Can Rename and Pin Parameters, and Overrides Can Delegate to the Core Handler: Second independent reverification of the follow-up: NEW-1 and NEW-2 resolved (20,000 fuzzed calls kept every value; Python 3.11 and 3.13). Timing correction: the worst case found near the caps is about 0.36 s CPU per hint field (64 nested candidates each wrapping about 8 KB that fails to parse), not the 0.05 s stated in the row below; still bounded by 64 scans and 64 parses. Coordinator pinned the scanner's comment and triple-quote handling with four cases in `test_unparseable_call_bound_respects_quotes_and_escapes` (a `)` inside a comment, a comment without a newline, a `)` and a lone quote inside `'''` and `"""` strings); each of three scratch mutations (comment handling removed, unterminated comment not running to the end, triple-quote detection removed) fails the test. Known low residuals: a Python 3.12+ nested same-quote f-string inside hint text can misbound (no producer emits it); whitespace before `(` is dropped on a mapped rewrite (pinned, cosmetic); Extension Aliases Can Rename and Pin Parameters, and Overrides Can Delegate to the Core Handler: Planned from the downstream "Tool-name seams" note, verified: `_install_served_names` serves an alias as `table[canonical].model_copy(update={"name": alias})`, sharing the wrapped callable and schema; `_rewrite_served_names` rewrites tool names only in hint fields; replacements capture the core tool into `_EXTENSION_REPLACED_CORE` and serve it under `alias_for_core`, overrides capture nothing; FastMCP validates arguments through the tool's own `fn_metadata`, so a renamed schema needs its own argument model. Request 4 shipped in 1zicq (1zhme).

**Changes delivered:**

- **Extension Aliases Can Rename and Pin Parameters, and Overrides Can Delegate to the Core Handler** (`1zim0-feat extension-alias-parameter-mapping`) — 6 ACs completed. Key decisions: Parameter-mapped aliases rather than a public call-by-name accessor; `core_handler` returns the pre-middleware handler
## Watchpoints

- Watchpoint: readiness should include a spike proving the translated argument model on `wf_add_change` and `wf_review_wave`.
- Follow-up: test-suite portability under a distribution's declarations is planned in `1zim1`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZIM3-FIXED-VALUE-UNVALIDATED | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| DEL-1ZIM3-HIDDEN-NAME-HINTS | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer, wave-council-delivery |
| DEL-1ZIM3-HINT-VALUE-REWRITE | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |
| DEL-1ZIM3-UNPINNED-GUARDS | do_now | no | completed | qa-reviewer, wave-council-delivery |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the hint rule rewrote calls whose meaning changes (an absent pinned parameter means the canonical default; probed: a dry-run `wf_add_change` hint became a `mode=create` alias call) and the default argument model drops extras that could defeat a pin; resolved by the default-equality rule, pinned-alias list-hint rule and translator-side extra refusal; strongest-alternative: a declared replacement delegating through `core_handler`, rejected because it loses canonical-name keying for the lock and guard)
- Prepare council seat evidence (2026-10-01): red-team blocked round 1 on the hint rule, approved round 2; security seat approved (translation precedes the canonical wrapper; controls do not inspect arguments). A readiness spike through the real server proved the translated argument model, single lock, single cost record, upgrade guard and canonical tier. Code lane blocked on pinned-only list hints, approved round 2. Reviewer models: requested opus for every seat and lane; observed runtime identity unknown.
- Readiness recheck after delivery repair (2026-10-01): Requirement 3 (hint rule) corrected to the repaired behaviour (keyword-name rewrite to unpinned aliases, prose maps to the preferred unpinned alias, kept-canonical cases listed). Independent scoped recheck: code, qa, architecture and docs-contract lanes and the red-team and security-reviewer seats approved; the docs-contract seat's two wording notes (positional arguments beside keywords; data, messages and descriptions rather than prose) were applied verbatim before re-recording. Reviewer model: requested opus; observed runtime identity unknown.
- **Delivery Wave Council [delivery-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: a distribution renaming wf_add_change and hiding the canonical got busy hints naming the hidden tool, and a string pin such as 'false' passed lax validation yet ran as its opposite; resolved by strict pin validation forwarding the validated value, keyword-name hint rewriting with prose mapped to the served alias, and tests killing every reviewer mutant, independently reverified through the real server; strongest-alternative: a public call-by-name accessor for extension tools, rejected at planning because the mapped alias keeps every control keyed on the canonical name)
- Delivery seat evidence (2026-10-01): round 1 red-team and code, qa, docs-contract and security lanes requested changes (two blocking defects, four unpinned guards), architecture approved; round 2 independent reverifier resolved all three findings, every lane and both seats approved, scratch full suite 10252 OK. Reviewer models: requested opus for every seat, lane and reverifier; observed runtime identity unknown.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 24 | 97,938 |
| implement | 18 | 269,865 |
| review | 51 | 456,047 |
| **Total** | **93** | **823,850** |

<!-- wave:context-efficiency-state {"generation":97,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":18,"content_source_credit":272777,"derived_artifact_credit":0,"direct_net":269865,"estimated_tokens_saved":269865,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":568,"response_debit":4690,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2346},"plan":{"calls":24,"content_source_credit":128064,"derived_artifact_credit":2715,"direct_net":97938,"estimated_tokens_saved":97938,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5235,"response_debit":34117,"source_credit_count":19,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":51,"content_source_credit":564417,"derived_artifact_credit":4309,"direct_net":456047,"estimated_tokens_saved":456047,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14022,"response_debit":100973,"source_credit_count":60,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":93,"content_source_credit":965258,"derived_artifact_credit":7024,"direct_net":823850,"estimated_tokens_saved":823850,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19825,"response_debit":139780,"source_credit_count":81,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11173},"wave_id":"1zim3 extension-alias-parameters"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 8 | 0 | 5 | 301,624 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":301624,"surfaced_events":8} -->
<!-- wave:exploration-avoided end -->
