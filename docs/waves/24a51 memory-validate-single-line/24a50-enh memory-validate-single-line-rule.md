# memory_validate Uses the Single-Line Rule, and Rationale Lines Get a Size Cap

Spec ID: `24a50-enh memory-validate-single-line-rule`
Spec Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-25
Wave: 24a51 memory-validate-single-line

## Rationale

Three tools write the same `Action delta:` line, and they disagree on what a single line is. After wave `24bik` (spec `24bij`), `memory_add` and `memory_consolidate(mode="create")` check `action_delta` and `validation_rationale` with `memory_single_line`, which refuses every separator `str.splitlines` recognizes (CR, LF, U+2028, U+2029, U+0085 and the others). `memory_validate` still refuses only CR and LF, in two places: `memory_validate_response` (its `action_delta`/`rationale` loop) and `record_memory_validation` in `memory_records.py` (its `action_delta`/`rationale`/`validated_by` loop). A `memory_validate` call can therefore store `applies when x<U+2028>next does y`. The delivery review of `24bik` (architecture finding AR-1) showed the store reads it back intact, but editors and line-oriented readers show U+2028 as a line break, so the record looks like two lines. The security seat at readiness showed the effect is worse than appearance: today `memory_validate` stores `x<U+2028>Status: active`, and readers that split on `str.splitlines` (the indexer chunker and the per-line content scans) see a forged `Status:` line, although `parse_memory_record` and docs-lint are not fooled. The operator decided DO on 2026-11-25.

No tool caps the length of `action_delta` or `validation_rationale`. On 2026-11-25 the 101 stored `Action delta:` lines had a median of 217 characters and a maximum of 570, and the 101 `Validation rationale:` lines a median of 372 and a maximum of 1,566. `memory_brief` returns both lines in full for up to five advisories, so a runaway value (a pasted log or transcript) would be paid for in every briefing that surfaces the record. The operator chose a large backstop cap of 5,000 characters and folded it into this change on 2026-11-25.

Arc context: `docs/arcs/244cm memory-quality/244cm-arc memory-quality.md`, Next step item 3.

## Product Intent

Everyone who reads or edits a memory record sees each `Action delta:`, `Validation rationale:` and `Validated by:` value on one line, whichever tool wrote it. Before: `memory_validate` stores a value containing U+2028 or another non-CR/LF separator. After: `memory_validate` refuses it with its existing message, recognizing the same separators `memory_add` and `memory_consolidate` already refuse. `memory_validate` still checks the value as given, so a trailing newline stays refused there while `memory_add` strips it first. Values without such separators behave as today. In addition, all three tools refuse an `action_delta` or rationale longer than 5,000 characters, a backstop that no stored value comes close to. AC-1, AC-2 and AC-6 establish the intent.

## Requirements

1. `memory_validate_response` refuses `action_delta` or `rationale` for every verdict (`promote`, `retain`, `reject` and `rewrite`) when the value is empty after stripping or is not a single line by `memory_single_line`, keeping both tests (`memory_single_line("")` is true, so the emptiness test stays), with the existing problem text `<label> must be a non-empty single line` and the existing refusal shape. Nothing is written.
2. `record_memory_validation` applies the same rule to `action_delta`, `rationale` and `validated_by`, raising its existing `ValueError` text.
3. The single-line test runs on the value as given, matching today's check, which does not strip before testing for CR/LF. A trailing newline therefore stays refused, as it is today.
4. No other `memory_validate` behavior changes: verdicts, the evidence and target checks, content scanning, rewrite handling and the stored line format stay as they are.
5. The `memory_validate` entry in `docs/architecture/contracts/mcp-tool-surface.md` states that `action_delta` and `rationale` must be a single line by `memory_single_line`, the same separator set `memory_add` uses, checked on the value as given (so a trailing newline is refused here, while `memory_add` strips it first). It replaces the sentence added in change `24bij` ("its own parameters with its own checks; the optional ... inputs of change 24bij do not apply here").
6. One constant, `MEMORY_RATIONALE_MAX_CHARS = 5000`, defined in `memory_records.py` beside `MEMORY_REF_MAX_CHARS`, caps the length in characters of the stripped value of `action_delta` and `validation_rationale` in `memory_add` and `memory_consolidate(mode="create")` (in `_rationale_inputs_refusal`), and of `action_delta` and `rationale` in `memory_validate` (in `memory_validate_response`) and in `record_memory_validation`. A value over the cap is refused before any write: `memory_add` and `memory_consolidate` return `invalid_memory_record` with the problem `<label> exceeds 5000 characters`, `memory_validate` returns its existing refusal shape with the same problem text, and `record_memory_validation` raises `ValueError` with that text. A value of exactly 5,000 characters is accepted. The refusal does not echo the value.
7. The `memory_add`, `memory_consolidate` and `memory_validate` contract entries state the cap.

## Scope

**Problem statement:** two write paths for the same stored fields use different line rules.

**In scope:**

- `memory_validate_response` and `_rationale_inputs_refusal` in `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`, and `record_memory_validation` plus the new constant in `.wavefoundry/framework/scripts/memory_records.py`.
- Tests in `.wavefoundry/framework/scripts/tests/test_memory_records.py`, including flipping `RationaleInputTests.test_ac8_memory_validate_rewrite_still_accepts_its_own_values` from 24bij, which pins the old behavior on purpose.
- The `memory_add`, `memory_consolidate` and `memory_validate` contract entries.

**Out of scope:**

- Any change to `memory_add` or `memory_consolidate` other than the length cap, and any change to the single-line rule itself.
- A cap on the record summary, title, evidence or targets (references already have their own 1,024-character cap).
- A docs-lint rule refusing separator characters anywhere in a record (security seat's alternative; a separate operator decision).
- Stripping values before the check (Requirement 3 keeps today's behavior).
- Rewriting stored records: a census on 2026-11-25 found no active or archived record with a non-CR/LF separator in these fields, and none longer than 1,566 characters.

## Acceptance Criteria

- [x] AC-1: In a temp root, `memory_validate` with each verdict (`promote`, `retain`, `reject` and `rewrite`) and a forging payload `x<SEP>Status: active` in `action_delta`, and separately in `rationale`, for each SEP in U+2028, U+2029, U+0085 and VT, is refused with diagnostic `invalid_memory_validation` and `<label> must be a non-empty single line`, and byte snapshots show nothing was written or superseded. With the fix absent, the records are written and the test fails; a fix that only adds two of the separators to the CR/LF test also fails.
- [x] AC-2: `record_memory_validation` called directly with each of U+2028, U+2029, U+0085 and VT in each of `action_delta`, `rationale` and `validated_by` raises `ValueError` and leaves the record unchanged.
- [x] AC-3: The existing `memory_validate` and `record_memory_validation` tests pass unchanged except the flipped 24bij AC-8 test, which now asserts the refusal; values without separators, including the existing fixtures, are still accepted.
- [x] AC-4: The `memory_validate` contract entry names `memory_single_line` and says the value is checked as given, and the 24bij sentence quoted in Requirement 5 is gone.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-6: In a temp root, a 5,001-character value (after stripping) in `action_delta`, and separately in the rationale field, is refused by `memory_add`, `memory_consolidate(mode="create")` and `memory_validate` with the problem `<label> exceeds 5000 characters`, nothing is written, and the response does not contain the value; `record_memory_validation` raises `ValueError` for the same input; a value of exactly 5,000 characters is accepted by each tool. With the cap absent, the 5,001-character writes succeed and the test fails.
- [x] AC-7: The `memory_add`, `memory_consolidate` and `memory_validate` contract entries each state the 5,000-character cap.

## Tasks

- [x] Replace the CR/LF test with `memory_single_line` in `memory_validate_response` and `record_memory_validation`.
- [x] Add `MEMORY_RATIONALE_MAX_CHARS` and the length check to `_rationale_inputs_refusal`, `memory_validate_response` and `record_memory_validation`.
- [x] Add tests for AC-1, AC-2 and AC-6; flip the 24bij AC-8 test.
- [x] Update the `memory_add`, `memory_consolidate` and `memory_validate` contract entries.
- [x] Run the targeted tests, then `--profile second` and `--profile declared` on `test_memory_records.py`, then the framework suite.

## Agent Execution Graph

1. Code and tests.
2. Contract entry.
3. Verification.

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| code-and-tests | implementer | — | memory_handlers.py, memory_records.py, test_memory_records.py |
| contract | implementer | — | mcp-tool-surface.md |
| verification | qa | code-and-tests, contract | targeted, profiles, suite |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`, `.wavefoundry/framework/scripts/memory_records.py`
- `.wavefoundry/framework/scripts/tests/test_memory_records.py`
- `docs/architecture/contracts/mcp-tool-surface.md`

## Affected Architecture Docs

N/A: one validation rule inside the memory module changes, with no boundary, flow or verification seam. The tool contract entry is updated (Requirement 5). The tool's parameters and schema do not change, so the tool-surface goldens and handler digests are unaffected.

Platform behavior: `str.splitlines` behaves the same on Windows, macOS, Linux and WSL2; the change has no path, process or filesystem component.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The fix at the public tool. |
| AC-2 | required | The record writer is the second place the rule lives. |
| AC-3 | required | Existing callers must see no other change. |
| AC-4 | required | The contract must stop describing two rules. |
| AC-5 | required | Change-local verification. |
| AC-6 | required | The cap at every write path, with the boundary value. |
| AC-7 | required | The contract must state the cap. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-25 | Planned on the operator's DO for delivery finding AR-1 of wave 24bik. Depends on 24bik closing first, because it flips a test that wave delivered. | `.wavefoundry/work/24bik/delivery/architecture.md` |
| 2026-11-25 | Amended before any readiness approval from the red-team primer: F1 (Product Intent and Requirement 5 now say the separator set is shared and the value is checked as given, not that the rule is identical to `memory_add`), F2 (AC-1 and Requirement 1 cover all four verdicts; the primer's replay showed all four store U+2028 today), F3 (Requirement 1 keeps the emptiness test, since `memory_single_line("")` is true). | readiness primer |
| 2026-11-25 | Readiness lanes and seats approved with nonblocking findings, carried as implementation notes rather than plan edits so the approvals stay on the current receipt. Implementer must: (1) in the AC-1 and AC-2 tests, loop over U+2028, U+2029, U+0085 and VT (QA-1), so a fix that only adds two characters to the CR/LF tuple fails; (2) use a forging payload such as `x<U+2028>Status: active` in those tests (security SR-1: today `str.splitlines` readers such as the chunker and the per-line content scans see a forged `Status:` line, while `parse_memory_record` and docs-lint are not fooled); (3) also assert diagnostic code `invalid_memory_validation` in AC-1 (code CR-2); (4) for AC-4, replace the 24bij sentence "its own parameters with its own checks; the optional ... inputs of change 24bij do not apply here" with a bullet naming `memory_single_line`, the shared separator set and the value-as-given check; the AC's "CR and LF only" clause has no matching text today (docs-contract D1, architecture AR-R1, code CR-1). Strongest alternative (security seat): a docs-lint rule refusing any splitlines-only separator anywhere in a memory record, as defense in depth for hand edits and future writers; surfaced to the operator, not in this scope. | readiness reports |
| 2026-11-25 | Amended after readiness, by operator decision, to add the 5,000-character cap (Requirements 6-7, AC-6, AC-7). The readiness implementation notes (forging payload, the four separators, the `invalid_memory_validation` assertion, the exact 24bij sentence for AC-4) are now part of AC-1, AC-2 and AC-4 and Requirement 5. Needs a focused re-Prepare. | operator request |
| 2026-11-25 | Focused readiness re-review of the cap amendment: code, QA, architecture, docs-contract, security and red-team all APPROVE with nonblocking notes, carried here as implementation notes. Implementer must: (1) leave the `memory_add`, `memory_consolidate` and `memory_validate` MCP wrapper docstrings in `server_impl.py` unchanged, so the tool-surface goldens and handler digests stay as they are; the contract entries alone carry the cap (architecture AR-R2); (2) in `_rationale_inputs_refusal`, include cap-refused labels in the field choice for `recovery_usage` and give the cap its own hint instead of `'<one line>'` (code CR-3, security SR-3); (3) count length on the stripped value everywhere, including `record_memory_validation`, while its single-line test stays on the value as given (red-team); (4) in AC-6 tests, assert a padded `" " + 5000 characters + " "` value is accepted at each tool (spaces, not a newline, for `memory_validate`) and a padded 5,001 is refused, and put a distinctive marker in the over-cap value and assert the marker is absent from the response (QA-3, QA-4); (5) in the `memory_consolidate` contract entry, state the cap in words rather than only by reference to `memory_add` (docs-contract N1); (6) AC-4's gone-check should match a fragment such as "its own checks", since the live sentence starts "Its required" and wraps (docs-contract). Affected Architecture Docs wording now means two rules and three contract entries (Requirements 5 and 7); N/A still holds (architecture AR-R3). | readiness focused re-review |
| 2026-11-25 | Readback: Keep each validation field on one line by testing its raw text. A trailing separator is refused. Cap each stripped rationale field at 5,000 characters across the three tools and the direct writer. Cover AC-1 through AC-7 in memory_records.py, memory_handlers.py, their tests and the tool contract. Use benign two-part text for separator coverage. | Admitted requirements and coordinator brief |
| 2026-11-25 | The default, second and declared focused profiles each passed all 335 tests with zero skips. Full docs lint passed. Validation refuses four non-CR/LF separators in each field across all verdicts, plus raw trailing newlines and blank input. Byte snapshots cover refusal paths. The tests use plain text on either side of each separator in place of the metadata-shaped fixture specified in AC-1. The padded 5,000-character values persist on all write paths, including both rewrite records. The padded 5,001-character values are refused. | test_memory_records.py, RationaleInputTests |
| 2026-11-25 | Coordinator restored the exact AC-1 fixture and reran all 335 focused tests in each of the default, second and declared profiles. All passed. | test_memory_records.py |
| 2026-11-25 | Repaired delivery finding CR-D1. The validator and direct writer preserve the line diagnostic first and report the length violation too. Independent review verified exact messages and byte-identical refusals. Final suite passed 13,627 tests across 261 files with 13 skips. All 336 memory tests passed on each of the three profiles. | RationaleInputTests.test_validation_reports_both_problems_on_a_long_multiline_field, framework test receipt and review ledger |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-25 | Fold a 5,000-character cap on `action_delta` and the rationale field into this change, at all three tools. | Operator: "we could set a large cap like 5k" and "fold it into 24a51". A backstop, not a style limit: every stored value is under 1,566 characters. Counted on the stripped value in characters, refused rather than truncated, through the same refusal paths as the single-line check. | (a) Truncate silently: changes the writer's text. (b) Smaller caps (about 600 and 1,000): would shape writing and refuse 6 stored rationales if applied to existing records; not chosen. (c) A separate change: costs a second full review cycle for one extra check. |
| 2026-11-25 | Use `memory_single_line` on the raw value in both `memory_validate` checks and keep their existing messages. | Operator: "do 2" (DO on aligning `memory_validate` with the single-line rule). Planner default for the mechanism: the same predicate the two other write paths use, on the value as given, so the only behavior change is refusing the separators CR/LF missed. Efficacy: replaying AR-1's U+2028 `action_delta` through the changed check refuses it; the corpus census found no stored value this would have refused, so nothing existing breaks. Success after release: no record written by any tool carries a non-CR/LF separator in these fields. | (a) Strip before checking, like `memory_add`: changes today's refusal of a trailing newline, which is a separate behavior change nobody asked for. (b) Normalize separators to spaces instead of refusing: silently rewrites the reviewer's text. (c) Leave the paths different: the operator chose DO. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A caller that sends a U+2028 value today starts getting refusals. | The census found no such stored value; the refusal names the field. |
| The flipped 24bij test conflicts with that wave if it is still open. | Implement only after wave 24bik closes. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
