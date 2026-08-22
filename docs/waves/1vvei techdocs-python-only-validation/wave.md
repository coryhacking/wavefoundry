# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1vvei techdocs-python-only-validation`
Title: Techdocs Python Only Validation

## Objective

Make downstream TechDocs validation entirely Wavefoundry/Python-owned by removing the external rendering step, and make the publication audit accept valid nav targets containing spaces. The wave preserves the audit's fail-closed shape and containment behavior without adding Docker, Node, MkDocs, or TechDocs CLI dependencies.

## Changes

Change ID: `1vrzu-bug techdocs-python-only-validation-and-spaced-nav`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-08-21

## Wave Summary

Wave `1vvei` delivered one change: TechDocs Validation Must Stay Python-Only and Accept Spaced Nav Paths.

**Changes delivered:**

- **TechDocs Validation Must Stay Python-Only and Accept Spaced Nav Paths** (`1vrzu-bug techdocs-python-only-validation-and-spaced-nav`) — all 7 ACs and all tasks completed. Required validation stays within Wavefoundry's Python toolchain; downstream rendering remains operator-owned. The existing recognized-shape parser was extended with a bounded spaced-nav grammar rather than replaced by a general YAML or external renderer dependency.

Nothing was deferred. The non-obvious closure lesson is that accepting spaces in a hand-written scalar grammar also requires explicit rejection of unmodelled YAML indicators and ambiguous terminal-colon forms; `QA-DEL-1` now pins that fail-closed boundary. The close memory pass produced no new durable candidates because the lesson is fully carried by the parser tests, change record, and typed finding chain.
## Watchpoints

- Operator direction (2026-08-20): downstream projects will not render through Wavefoundry and must not require Docker or tooling outside the declared Python environment.
- Stage gate: no seed, framework-script, test, rendered-prompt, architecture, or changelog edit before typed readiness is current; implementation must open only the narrowly required `seed_edit_allowed` and `framework_edit_allowed` gates.
- Canonical ownership: edit seeds first, then manually synchronize the self-hosted authored prompt twins and verify parity; the current renderer does not own these prompts, and a local-twin edit is never the source fix.
- Parser watchpoint: accepting spaces must not accept malformed/deeper YAML shapes or move any filesystem operation ahead of lexical and realpath containment.
- Dependency watchpoint: no manifest, setup, packaging, or runtime import may gain Docker, Node, MkDocs, `@techdocs/cli`, or `mkdocs-techdocs-core`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-DEL-1 | do_now | no | completed | qa-reviewer, code-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: approved on explicit operator closure instruction (2026-08-21)

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-20: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the current parser falsely computes a two-section-deep nav leaf, and a permissive spaced-tail regex could preserve that defect while guessing at unsupported YAML syntax; strongest-alternative: keep Python-only validation but use a tagged indentation-aware root/one-section parser with an explicit closed scalar grammar, fail-closed deeper/malformed cases, and old-`\\S+` plus naïve-`.+` known-bad controls.)

## Implementation Checkpoints

- **Builder allocation — 2026-08-21:** two non-overlapping `implementer` workstreams: canonical workflow carriers/authored twins/tests/changelog, and the bounded nav parser/focused audit tests. The wave coordinator owns lifecycle bookkeeping, merged verification, and gate closure.
- **Implementation verification — 2026-08-21:** all seven required ACs and all tasks are complete; warning-strict focused suites passed, the full framework suite passed 7,463 tests across 64 files, docs lint and diff checks are clean, and the seed/framework edit gates are closed. Delivery review remains pending.
- **Delivery repair cycle 1 — 2026-08-21:** QA found `QA-DEL-1`, a fail-closed gap for YAML indicator-led nav values, and code review found its terminal-colon sibling. The bounded repair rejects reserved anchors, aliases, tags, block/folded scalars, flow collections, directives, and ambiguous plain-scalar colon forms while preserving `target:slug.md`; the warning-strict audit suite passes 84 tests and the current full suite passes 7,464 tests across 64 files. Fresh QA and code reverifications are terminal.
- **Delivery Wave Council — 2026-08-21: PASS** (moderator: wave-council; primer-depth: standard; fixed seats: code-reviewer, qa-reviewer, docs-contract-reviewer; rotating seat: architecture/security; strongest challenge: a hand-written YAML subset could silently accept another unmodelled scalar form, as `QA-DEL-1` demonstrated; strongest alternative: depend on PyYAML or an external MkDocs/TechDocs renderer, rejected because that would expand the declared Python dependency and downstream rendering boundary; disagreement resolution: QA's fail-closed challenge prevailed, the parser was repaired, and fresh code/QA reverification closed the finding). All specialist, council, and operator delivery approvals are recorded.

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 141 | 2,228,892 |
| implement | 163 | 1,647,219 |
| review | 191 | 2,918,501 |
| **Total** | **495** | **6,794,612** |

<!-- wave:context-efficiency-state {"generation":401,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":163,"content_source_credit":1985319,"derived_artifact_credit":0,"direct_net":1647219,"estimated_tokens_saved":1647219,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6982,"response_debit":334636,"source_credit_count":95,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3518},"plan":{"calls":141,"content_source_credit":2660795,"derived_artifact_credit":2020,"direct_net":2228892,"estimated_tokens_saved":2228892,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14735,"response_debit":422694,"source_credit_count":187,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":191,"content_source_credit":3410147,"derived_artifact_credit":968,"direct_net":2918501,"estimated_tokens_saved":2918501,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":28878,"response_debit":465082,"source_credit_count":149,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":495,"content_source_credit":8056261,"derived_artifact_credit":2988,"direct_net":6794612,"estimated_tokens_saved":6794612,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":50595,"response_debit":1222412,"source_credit_count":431,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8370},"wave_id":"1vvei techdocs-python-only-validation"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 23 | 0 | 6 | 13,072,260 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":13072260,"surfaced_events":23} -->
<!-- wave:exploration-avoided end -->
