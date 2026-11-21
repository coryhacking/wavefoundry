# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-20
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23z45 field-feedback-correctness`
Title: Field Feedback Correctness

## Objective

Operators can write framework files on Windows, install planning prompts under their distribution's names, and see which file or unresolved security condition needs attention during review and close.

## Changes

Change ID: `23z47-bug windows-fchmod-guard`
Change Status: `implemented`

Change ID: `23z8y-bug role-derived-planning-names`
Change Status: `implemented`

Change ID: `23z90-enh errors-name-path-and-operation`
Change Status: `implemented`

Change ID: `23z8z-enh security-advisories-at-review-and-close`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (main session)
- Write-owning roles: implementer
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-11-21

## Wave Summary

Wave `23z45` (Field Feedback Correctness) delivered 4 changes: Skip descriptor chmod on native Windows, Derive planning prompt names from each key's role, Name the path and the operation in two failure messages, and Name accepted security candidates at Review and both closes.

Intent outcome: partially established. The Windows-branch tests exercise the contained writer and renderer with a refused descriptor chmod on macOS. Native Windows installation still needs a platform check. The renamed-profile tests exercise a fresh render without planning-name pins. The security tests exercise Review and both close paths, including the advisory for an unreachable candidate and the existing blocking cases. The telemetry and TechDocs tests check which operation, target or baseline an operator sees when a step fails. These tests establish the reported output on their fixtures. A downstream operator has yet to confirm the changes on their installation.

**Changes delivered:**

- **Skip descriptor chmod on native Windows** (`23z47-bug windows-fchmod-guard`) — AC-1, AC-2, AC-3 and AC-4 completed. Key decisions: Selected: skip descriptor chmod on native Windows through one predicate in `contained_files.py`, used by every `hasattr(os, "fchmod")` guard; The direct-copy site at `render_agent_surfaces.py:3007` takes the predicate although it is unreachable on Windows.
- **Derive planning prompt names from each key's role** (`23z8y-bug role-derived-planning-names`) — AC-1, AC-2, AC-3, AC-4, AC-5 and AC-6 completed. Key decisions: Derive each unregistered planning name from a declared role phrase per key (item, or item in container) filled with the profile's nouns; Mechanism efficacy. Replay: the prototype run on the reproduction fixture imports with no pins and gives `plan-wave-doc`, `implement-wave-doc`, `close-wave-doc`, `add-wave-doc-to-set`, `remove-wave-doc-from-set`; under two pins the plan key is `plan-wave-doc`. Control: the derivation decides the names directly, it is not advice. Misses: a rewrite that changes the role phrases themselves, which AC-3 guards for the shipped tier words but cannot guard for an arbitrary map; a map that rewrites dictionary keys inconsistently between tables, which the key-set check reports. Existing mechanism: none gives this; pins are the workaround being removed. Measure after release: the reporter removes the five pins and imports.
- **Name the path and the operation in two failure messages** (`23z90-enh errors-name-path-and-operation`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9 and AC-10 completed. Key decisions: Selected: add `operation` and `target` keys to the failed context-efficiency rows and render `error` with the existing `path_free_exception_text`; describe audience degrade tokens with ref and paths through one shared helper, leaving the token list unchanged; Operator decision: bring `_flush_context_efficiency`'s outer handler and `FlushResult.error` into scope; they must use the same `operation`, `target` and `path_free_exception_text` form.
- **Name accepted security candidates at Review and both closes** (`23z8z-enh security-advisories-at-review-and-close`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6 and AC-7 completed. Key decisions: Selected: add a fourth class to `security_candidate_state` and one advisory diagnostic from the shared source; have the change close carry the source's `advisory: True` diagnostics on `dry_run` and `ok`; Mechanism efficacy for the selected approach.

## Watchpoints

- 23z8z edits seed 209: open `seed_edit_allowed` around the edit and close it after.
- Framework edits need `framework_edit_allowed` open for the edit window.
- security-reviewer is requested by judgment: 23z8z changes how security review state is reported, though no gate outcome may change.
- Windows behaviour in 23z47 is verified by simulation on macOS; native Windows verification is a release-check follow-up.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| D1-23z47-windows-identity-fixture | do_now | no | completed | — |
| D1-23z90-conditional-target-note | do_now | no | completed | — |
| D1-23z90-producer-lease-target | do_now | no | completed | architecture-reviewer, code-reviewer, docs-contract-reviewer, qa-reviewer, council-delivery |
| D1-23z90-unreadable-errno | do_now | no | completed | — |
| R1-23z47-native-windows-intent-gap | dont_do_later | no | not_required | — |
| R1-23z8y-ac6-unsatisfiable | do_now | no | completed | — |
| R1-23z8z-seed209-anchor | do_now | no | completed | — |
| R1-23z90-ac5-priority | do_now | no | pending | — |
| R1-23z90-techdocs-fixture-scope | do_now | no | pending | — |
| R1-23z90-unreadable-row-uncovered | do_now | no | completed | — |

*Machine review state — 10 findings; current: do_now 9, maybe_later 0, dont_do_later 1, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| security-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-21: Delivery council approved the four repairs after seven independent lane reverifications. Architecture, QA, the reality checker and the rotating release reviewer withheld on the first pass. Security approved with notes and confirmed the lease defect. Initial seat agreement was `majority`, maximum severity `low`. The chair weighed the five anonymized seat summaries before restoring their identities. No substantive dissent remains. The red-team primer identified the lock/store attribution error. Its closing check also found that missing-wave rows omit an operation. Docs-contract verified both documents against missing-wave, parse and write responses.

The repair names the producer lock before transfer opens SQLite and names the database after acquisition succeeds. This preserves retry behavior and gives the operator the correct file. The publication test retains its byte, identity and cleanup checks on the simulated Windows path. A native Windows installation remains the release follow-up. Require no per-distribution pins for the five renamed routes. A fresh render verified routing; the seed-authored prompt bodies and downstream adoption remain outside that result.

QA confirmed the intent paragraph below. The council judged 23z47 and the wave objective partially established, and 23z8y, 23z8z and 23z90 established within their stated test boundaries. The coordinator checked the final docstring correction against the chair's 27-file manifest. Only a single docstring changed. The five vocabulary and eleven diagnostic tests passed, followed by 13,123 tests across 251 files with twelve skips in the full suite. The two pending 23z90 readiness notes have no unresolved blocking lane.

2026-11-20: QA checked the first delivery against all four specs. Record-write, SQLite and TechDocs failures named their tested targets. A producer-lease refusal named SQLite before the transfer opened it. The code and documentation reviews also found a Windows test that bypassed the guard, a denied-read message that lost its errno and a release note that promised a target for every failure. See the four initial-delivery findings and their current dispositions above.

2026-11-20: Intent outcome: partially established. The Windows-branch tests exercise the contained writer and renderer with a refused descriptor chmod on macOS. Native Windows installation still needs a platform check. The renamed-profile tests exercise a fresh render without planning-name pins. The security tests exercise Review and both close paths, including the advisory for an unreachable candidate and the existing blocking cases. The telemetry and TechDocs tests check which operation, target or baseline an operator sees when a step fails. These tests establish the reported output on their fixtures. A downstream operator has yet to confirm the changes on their installation.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 55 | 257,637 |
| implement | 130 | 0 |
| review | 495 | 6,257,861 |
| **Total** | **680** | **6,515,498** |

<!-- wave:context-efficiency-state {"generation":707,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":130,"content_source_credit":18452,"derived_artifact_credit":0,"direct_net":-22883,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5958,"response_debit":47575,"source_credit_count":19,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12198},"plan":{"calls":55,"content_source_credit":442463,"derived_artifact_credit":1848,"direct_net":257637,"estimated_tokens_saved":257637,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":37511,"response_debit":155091,"source_credit_count":40,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5928},"review":{"calls":495,"content_source_credit":7597845,"derived_artifact_credit":1993,"direct_net":6257861,"estimated_tokens_saved":6257861,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":45019,"response_debit":1303520,"source_credit_count":272,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6562}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":680,"content_source_credit":8058760,"derived_artifact_credit":3841,"direct_net":6492615,"estimated_tokens_saved":6515498,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":88488,"response_debit":1506186,"source_credit_count":331,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":24688},"wave_id":"23z45 field-feedback-correctness"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 71 | 0 | 32 | 33,358,207 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":32,"estimated_exploration_avoided":33358207,"surfaced_events":71} -->
<!-- wave:exploration-avoided end -->
