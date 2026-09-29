# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-29
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z8oz extension-tool-aliases`
Title: Extension Tool Aliases

## Objective

A fork can serve Wavefoundry tools under its own names, hide canonical names, and reuse a core name with an incompatible handler, while every name-keyed protection still applies (RFC section 4.3).

## Changes

Change ID: `1z8oy-enh extension-tool-aliases`
Change Status: `complete`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer
- Requested review lanes: architecture-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-09-29

## Wave Summary

Wave `1z8oz` (Extension Tool Aliases) delivered one change: Extension Tool Aliases, Hidden Names and Replacements. Notable adjustments during implementation: Extension Tool Aliases, Hidden Names and Replacements: Delivery repairs DEL-1 to DEL-4. DEL-1: `_wrap_first_party_tool_costs` skips a `_COST_EXEMPT_TOOLS` name only when it is not in `extractor_free`, so a replacing handler on a cost-exempt name records its debit; AC-4's marker clause amended accordingly. DEL-2: `_alias_hide_replacement_problems` refuses a hidden name declared twice, and the replaced-name refusal no longer advises aliasing `alias_for_core` (which is itself refused as another alias). DEL-3: threat model states that a declared tier replaces only the roster tier; the spec states that the rewrite also applies to the distribution's own tools and overrides, that an exempt replaced name gets the cost wrapper, and that a hidden name is declared once. DEL-4: the replacement fixture also replaces `wf_current_wave`, so a non-replaced core tool's lock-busy hints (`wf_add_change`) must name `fork_current_core`; replacement reload; a stock registration after a replacement on the same module leaves `_EXTENSION_REPLACED_CORE` empty and `wf_close_wave` without the cost marker; the replacing `memory_validate` keeps its guard and recovery exemption; the cost-exempt alias check calls without the busy lock; `_CORE_BEHAVIOUR_MIDDLEWARE` labels are pinned to `MIDDLEWARE`. Scratch mutants (clean baseline): reverting DEL-1, accepting duplicate hidden names, no clear at install start, main-pass map without replaced names, checkpoint guard for registered publishers, and a core chain missing a wrapper each fail at least one test. test_extension_tool_modules 57 OK.

**Changes delivered:**

- **Extension Tool Aliases, Hidden Names and Replacements** (`1z8oy-enh extension-tool-aliases`) — 8 ACs completed. Key decisions: Declare aliases in the extension declaration, not the vocabulary profile; Aliases are `model_copy` renames of the wrapped canonical `Tool`
## Watchpoints

- Watchpoint: serialized with wave `1z8ox`, which closed on 2026-09-29 and is committed (`24513060`); this wave builds on it.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-28: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the replacing handler and the core behaviour share one name key, so every name-keyed decision leaks across them, resolved by deciding extractors, rewrite skip and guard membership at wrap time from a main-pass-only set; strongest-alternative: split replacements into a follow-up change, declined by operator decision to keep them together). Red-team seat: the leak above plus the unwrapped replacement capture, both folded into Requirement 5. Docs seat: AC-7 named a source census that cannot see declarations, split into core-source and booted parity.
- 2026-09-29: AC sub-bullets folded into single lines (wording unchanged) so implement-time lint accepts them; every code anchor the plan names re-verified against the tree after waves 1z8ox and 1zbrr; approvals re-recorded by reference against the new receipt.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | — |
| DEL-2 | do_now | no | completed | — |
| DEL-3 | do_now | no | completed | — |
| DEL-4 | do_now | no | completed | — |

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
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 46 | 436,065 |
| implement | 40 | 0 |
| review | 47 | 929,267 |
| **Total** | **133** | **1,365,332** |

<!-- wave:context-efficiency-state {"generation":135,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":40,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-6454,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1285,"response_debit":7355,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2186},"plan":{"calls":46,"content_source_credit":512310,"derived_artifact_credit":3104,"direct_net":436065,"estimated_tokens_saved":436065,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7013,"response_debit":78847,"source_credit_count":38,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":47,"content_source_credit":1069563,"derived_artifact_credit":3190,"direct_net":929267,"estimated_tokens_saved":929267,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10807,"response_debit":134995,"source_credit_count":61,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":133,"content_source_credit":1581873,"derived_artifact_credit":6294,"direct_net":1358878,"estimated_tokens_saved":1365332,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19105,"response_debit":221197,"source_credit_count":99,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11013},"wave_id":"1z8oz extension-tool-aliases"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 3 | 486,615 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":486615,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
