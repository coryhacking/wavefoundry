# Memory Summary Spacing Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-22

Phase: readiness. Receipt: `review-policy-312028dae8bdf2f6199d`.
Reviewed change: `1yq69-bug memory-summary-spacing.md`.

## Required lane judgments

**Code reviewer: approve. QA reviewer: approve.** These are plan-readiness judgments, not implementation or delivery approvals. Required ACs remain unchecked. The bounded plan addresses the demonstrated insertion defect, replacement whitespace consumption, repeated calls, and body preservation without historical migration.

Reviewer context `/root/spacing_readiness` independently read the current tree and plan and made no implementation edits. Code, QA, and rotating docs-contract roles share this context and are correlated; they are not three independent reviewers. The isolated primer was supplied by `/root/spacing_primer`. Fixed-seat outputs and synthesis are recorded below when available.

## Evidence and limits

MCP `code_outline` and targeted `code_read` inspected `.wavefoundry/framework/scripts/memory_records.py` lines 147–165 and 868–1086, and `.wavefoundry/framework/scripts/tests/test_memory_records.py` lines 4342–4401. No area AGENTS.md exists under the scripts area. The helper currently searches the whole record before inserting, and its patterns end in whitespace-consuming `\s*$`. The renderer already emits the desired boundary. Existing `MemoryAgentValidationTests` use the real renderer/writer and `memory_validate_response`, providing the right producer fixture to extend.

A completed `python3 -B` probe imported the current production module and used temporary storage only. It checked insertion with zero, one and three blank lines; replacement of an existing final metadata field; and a field absent from the header but present as body prose. Observed: every insertion leaves the new field immediately adjoining Summary; replacement consumes the existing separator; whole-record matching modifies the body example. A canonical render → write → `record_memory_validation` probe also produced `Canonical overlap: none\n## Summary` while retaining parsed validation `retain`. All assertions completed, with no skips. No source mutation was needed to establish the known-bad control because the current helper is the original defective behavior.

Independent reference: the independently read ACs require exactly one blank line and an untouched body; the renderer's existing section boundary corroborates that contract. Exact text and suffix equality can falsify the claim independently of the proposed partition implementation. Shared original reproduction and primer create common-mode risk; these checks establish readiness feasibility and defect relevance only. The full suite, new regressions, original-helper injection into those regressions, and independent delivery review remain implementation tasks, not results of this review.

## QA coverage and implementation notes

| AC | Required evidence at delivery | Readiness assessment |
| --- | --- | --- |
| AC-1 | Six exact expected-output cases: insert/replace × zero/one/excess blank lines | Clear and feasible; use actual field patterns to expose whitespace consumption |
| AC-2 | Repeated same-field and additional-field updates; exact body suffix and unrelated metadata preservation | Include body-only metadata match so searching the whole record fails |
| AC-3 | Producer-built repeated validation with parsed fields, original-helper negative control, and both no-Summary branches | Existing fixture supplies real producer/response path; insertion must still raise and existing replacement must still work without Summary |

These are implementation notes within admitted ACs, not additional scope or readiness blockers. Normalize after the requested mutation, confined to the prefix before the first existing Summary marker, and rejoin the untouched suffix. Preserve the no-marker fallback. No retrieval benchmark, historical rewrite, parser redesign, schema change, or new lint rule is needed.

## Primer and rotating seat

Declared primer depth: `standard`. Stances: adversarial (replacement whitespace and body matching), constructive (partition and suffix preservation), and simplicity (one helper, no migration). Independent contexts were `/root/spacing_primer`, `/root/spacing_architecture`, `/root/spacing_security`, and `/root/spacing_reality`.

The isolated primer's strongest challenge is confirmed by executable evidence: insertion-only newline repair misses replacement, while broad search can rewrite body examples. Its questions about the exact separator matrix and producer-based repeated validation are answered by the coverage table above; implementation must produce that evidence.

The rotating docs-contract seat approves readiness. Best smaller alternative: add one newline only on insertion. This would be better in patch size, but fails the required replacement and body-preservation contract. Whole-record rerendering might centralize formatting but is weaker because it changes unrelated bytes. No alternative is stronger than local prefix mutation followed by boundary normalization. The plan's exclusions and no-marker compatibility requirement are clear; no seed or published contract change is necessary.

## Integrity declarations

For the code and QA readiness approvals, all five booleans are true for this readiness evidence: `test_ran_without_unintended_skip`, `public_path_reached`, `boundary_values_realistic`, `assertions_non_vacuous`, and `known_bad_detected`.

`known_bad_detection_method`: executed the original production helper against the required exact-boundary/body-preservation properties, including canonical render/write/record_memory_validation in a temporary repository; observed missing separator and body alteration. The public-path declaration refers to the actual production record writer used in this feasibility probe, not a claim that future response-path regressions or delivery tests already ran.

## Council synthesis

**Wave Council readiness: approve.** No blockers and no material disagreement. Fixed architecture, security, and reality-checker perspectives ran in isolated contexts; their outputs were relayed by the coordinator. QA was this reviewer's fixed seat. The rotating docs-contract seat and synthesis share QA's context, so this is disclosed correlated review, not five fully independent seat contexts. The separate primer preceded all seat reviews.

First-pass merit assessment used role-free labels in a shuffled order: Seat 1 found the narrower mutation preserves existing path/authority boundaries; Seat 2 found the six exact outputs, repeated updates, and original-helper control capable of falsifying the promised result; Seat 3 found the existing owner and renderer sufficient without new dependencies; Seat 4 found insertion-only and whole-record alternatives weaker; Seat 5 found the no-marker branches explicit and independently verifiable. Each claim is supported by the inspected plan/current tree, rather than the role's authority. No required-lane blocker was anonymized or downgraded. Reattached identities: Seat 1 security, Seat 2 QA, Seat 3 architecture, Seat 4 docs-contract, Seat 5 reality-checker.

Architecture approves: its own probes confirmed insertion, replacement and body-only matching failures; the existing helper remains the owner, the renderer already has correct spacing, and no dependency change is needed. It weighs local prefix mutation above insertion-only because both branches need repair.

Security approves: there is no new filesystem path, permission, network or execution surface; existing confined record access remains the boundary. No credible less-trusted actor or authority delta is introduced. Header-only mutation improves content preservation. It prefers the bounded fix over whole-record rerendering and expects the exact separator matrix plus producer validation to verify it.

Reality-checker approves: exact text, repeat, producer and original-helper controls address the load-bearing assumptions. Both no-marker success and error branches must remain covered. A line-oriented editor adds machinery without improving this contract; insertion-only is insufficient.

All fixed perspectives confirmed the primer's strongest challenge and accepted the concrete tests answering its questions. QA and docs-contract judgments and alternative weighing appear above. Agreement: all seat verdicts align, `max_severity: none`. The `seat_agreement` value is `majority` conservatively: the shared QA/docs-contract context prevents a claim that all five independently reached unanimity. There is no dissent or split requiring a challenge round.

Strongest alternative: insertion-only is smaller, but cannot meet required replacement normalization. Improvements recommended: preserve the first Summary suffix exactly; make body-only matching a negative assertion; test the two no-marker behaviors; inject the original helper into new regressions to establish known-bad detection. All fit the existing ACs. No further readiness repair is requested. Implementation and delivery review remain outstanding.

The council readiness integrity booleans use the same completed phase-appropriate evidence described above, supplemented by the isolated seat reports. This records this synthesizer's review and probes; it does not present relayed observations as tests personally executed by the synthesizer.
