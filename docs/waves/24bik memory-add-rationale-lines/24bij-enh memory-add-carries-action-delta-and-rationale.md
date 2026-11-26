# memory_add Carries Action Delta and Validation Rationale

Spec ID: `24bij-enh memory-add-carries-action-delta-and-rationale`
Spec Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-25
Wave: 24bik memory-add-rationale-lines

## Rationale

Review memories rewrites an active record with `memory_add(..., status="active", supersedes=<id>)`. The `memory_add` MCP tool and the public `memory_add_response` handler do not accept `action_delta` or `validation_rationale`. The internal `_memory_add_response_locked` already takes `_action_delta` and `_validation_rationale` and `render_memory_record` already writes both lines, but only `memory_validate` reaches them, and the review prompt forbids sending an active record to `memory_validate`.

So every rewrite of an active record loses its `Action delta:` and `Validation rationale:` lines. `memory_consolidate(mode="create")` has the same gap: `memory_consolidate_response` calls `_memory_add_response_locked(..., status="active", supersedes=...)` without either private value, so every consolidation replacement is written without the lines. The memory evaluation counts a record with neither line as uncoverable for the reason `no_rationale`. The item 7 batch review of arc `244cm` rewrote 52 records: the census on 2026-11-25 found 53 active records with a `Supersedes:` line and none with either line, and `no_rationale` rose from 31 to 55. As long as this gap exists, Review memories raises the count it is meant to reduce.

Arc context: `docs/arcs/244cm memory-quality/244cm-arc memory-quality.md`, Next step item 2.

## Product Intent

An agent running Review memories can rewrite or consolidate active records and keep a one-line statement of when the lesson applies. Before: the replacement record drops that line and counts as `no_rationale`. After: the replacement writes `Action delta:` (and, when given, `Validation rationale:`) and is not counted as `no_rationale`. The change only adds optional inputs; existing `memory_add` and `memory_consolidate` calls behave as before. The evaluation checks only that a line is present, so the quality of the line remains a review judgment. AC-1 and AC-4 together establish the intent: the tool writes the line, and the review workflow tells the agent to supply it.

## Requirements

1. `memory_add` (MCP tool) and `memory_add_response`, and `memory_consolidate` (MCP tool) and `memory_consolidate_response`, accept two optional string inputs, `action_delta` and `validation_rationale`, defaulting to empty. `memory_consolidate` uses them only for `mode="create"`; `mode="dry_run"` ignores them.
2. The public entry points (`memory_add_response`, and `memory_consolidate_response` for `create`) validate the values before the project-state lock is taken. Each value is stripped of surrounding whitespace first. The stripped value must be a single line by `memory_single_line`, so a trailing newline is accepted and an internal line break or separator (CR, LF, U+2028, U+2029, U+0085 and the others `str.splitlines` recognizes) is refused with `invalid_memory_record`. Both stripped values join the forbidden-content scan under the field names `action_delta` and `validation_rationale`; a refusal names the field and reason code in `data.content_reasons` and never echoes the value. A refused call writes, supersedes and archives nothing.
3. The entry points pass the stripped values to the existing private `_action_delta` and `_validation_rationale` parameters of `_memory_add_response_locked`, which already render them through `render_memory_record`. A non-empty value writes `Action delta: <value>` or `Validation rationale: <value>`; an empty or whitespace-only value writes no line, as today. No check is added inside `_memory_add_response_locked`.
4. For `memory_add`, the values are accepted with any `status` and with or without `supersedes`. Neither tool copies a value from a superseded or consolidated source record.
5. `memory_validate` behavior is unchanged: it keeps its own required checks, refusal wording and field names, and its rewrite branch still reaches the private parameters without the new checks.
6. The Review memories rewrite step and consolidation step carry the new inputs in all three copies of the prompt: the seed `.wavefoundry/framework/seeds/240-memory-review.prompt.md`, the install template `.wavefoundry/framework/install/lifecycle-prompts/memory-review.prompt.md`, and the self-hosted `docs/prompts/memory-review.prompt.md`. Rendering is missing-only, so the same text is merged by hand into each copy; unrelated drift between the copies is left alone. In each copy:
   1. The rewrite call reads `memory_add(..., status="active", supersedes=<original id>, action_delta=...)`.
   2. The consolidation call reads `memory_consolidate(mode="create", ..., action_delta=...)`.
   3. One sentence defines the value: one line stating the condition under which the lesson applies and what the next action does differently, not a restatement of the summary or title, written fresh from the rewritten or merged lesson rather than copied from a source record.
   4. One sentence says `validation_rationale` is optional and states the evidence checked in this review.
7. `docs/architecture/contracts/mcp-tool-surface.md` documents the change: both signature lines gain the inputs; the `memory_add` validation bullet adds both fields to the scanned fields and states the single-line rule; the consolidation bullets state that the values are validated before the locked preflight and that a refusal supersedes and archives nothing; and the `memory_validate` entry notes that its required `action_delta` is a separate parameter.

## Scope

**Problem statement:** the documented rewrite and consolidation paths cannot write the lines the memory evaluation uses to decide `no_rationale`.

**In scope:**

- The `memory_add` and `memory_consolidate` tool signatures, docstrings and handlers in `.wavefoundry/framework/scripts/wf_server/server_impl.py` and `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`.
- Tests in `.wavefoundry/framework/scripts/tests/test_memory_records.py` (handler behavior) and `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py` (prompt contract and known-bad controls).
- The committed schema fixtures: `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden.json`, `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden/declared.json` (both regenerated with `WF_UPDATE_TOOL_SURFACE_GOLDEN=1`) and `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json` (refreshed digests plus this wave's sentence appended to its `description`).
- The rewrite and consolidation steps in the three prompt copies named in Requirement 6.
- The `memory_add`, `memory_consolidate` and `memory_validate` contract entries.

**Out of scope:**

- Backfilling the 53 rewritten records that already lack the lines. That is a records task for a later Review memories pass, which the operator decides on separately.
- Making either value required for a rewrite.
- Any change to `memory_validate`, the evaluation's `no_rationale` rule, or memory tools other than `memory_add` and `memory_consolidate`.
- A non-blocking advisory when a replacement omits both lines (see Decision Log).

## Acceptance Criteria

Name at least one AC, or a clearly identified combination, that tests whether the intent was established. Keep implementation checks where useful; delivery of guidance alone does not prove improved agent behavior.

- [x] AC-1: In a temp root, a `memory_add` call with `status="active"`, `supersedes=<id>` and `action_delta="  applies when X; next action does Y  "` writes a record whose raw text contains the line `Action delta: applies when X; next action does Y`, and `memory_eval.uncoverable_records` does not report that record as `no_rationale`, while a control record written without the input is reported. The test fails if the input is accepted but not written or not stripped.
- [x] AC-2: A `memory_add` call with `validation_rationale` alone writes a `Validation rationale:` line holding the stripped value, a whitespace-only `action_delta` writes no `Action delta:` line, and a value with only a trailing newline is accepted and written without it.
- [x] AC-3: A value with an internal line break or a U+2028 separator in either input, and a value that trips the content scan, are refused by `memory_add` with `invalid_memory_record` before any file is written; the content refusal names the field and its reason code and the response does not contain the value.
- [x] AC-4: In all three prompt copies, the rewrite step contains `supersedes=<original id>, action_delta=...` inside its `memory_add` call, the consolidation step contains `action_delta=` inside its `memory_consolidate(mode="create", ...)` call, and both carry the phrase "what the next action does differently". `test_prompt_contract_and_known_bad_controls` gains known-bad controls that remove each call form, and each control fails the contract check. The existing `action_delta=...` in the `memory_validate` step does not satisfy this AC.
- [x] AC-5: A `memory_add` call with `supersedes=` pointing at a temp source record that carries both lines, and with neither new input, writes a replacement with no `Action delta:` and no `Validation rationale:` line; the existing `memory_add` and `memory_consolidate` tests pass unchanged.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-7: In a temp root, a `memory_consolidate(mode="create")` call with an `action_delta` writes a replacement whose raw text contains the stripped `Action delta:` line and which `memory_eval.uncoverable_records` does not report as `no_rationale`; a value with an internal line break or a content-scan hit is refused, and byte snapshots show no source record was superseded or archived and no replacement was written.
- [x] AC-8: A `memory_validate(verdict="rewrite")` call whose `action_delta` contains a U+2028 separator, which `memory_validate` accepts today, still writes the rewrite with its `Action delta:` line after the change.

## Tasks

- [x] Open `framework_edit_allowed`.
- [x] Add `action_delta` and `validation_rationale` to the `memory_add` tool and docstring; validate, strip and scan them in `memory_add_response` before the lock; pass them as `_action_delta` and `_validation_rationale`.
- [x] Add both to the `memory_consolidate` tool and docstring and to `memory_consolidate_response`; for `create`, validate, strip and scan them before the locked preflight and pass them to the replacement write.
- [x] Add tests for AC-1, AC-2, AC-3, AC-5, AC-7 and AC-8 in `test_memory_records.py`, and the AC-4 contract assertions and known-bad controls in `test_render_agent_surfaces.py`.
- [x] Regenerate both tool-surface goldens and refresh the handler digest fixture, appending this wave's sentence to its `description`.
- [x] Hand-merge the rewrite and consolidation step text into the install template and `docs/prompts/memory-review.prompt.md`.
- [x] Open `seed_edit_allowed`, merge the same step text into seed 240, and close the gate.
- [x] Update the `memory_add`, `memory_consolidate` and `memory_validate` contract entries.
- [x] Close `framework_edit_allowed`.
- [x] Run the targeted tests, then `--profile second` on each touched test file, then the framework suite.

## Agent Execution Graph

1. Handler and tool change with tests.
2. Seed and contract edits (independent of step 1).
3. Verification after both.

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| handler-and-tests | implementer | — | server_impl.py, memory_handlers.py, tests |
| seed-and-contract | implementer | — | seed 240, install template, self-hosted prompt, contract doc |
| verification | qa | handler-and-tests, seed-and-contract | targeted tests, second profile per file, suite |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_memory_records.py`, `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden.json`, `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden/declared.json`, `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `.wavefoundry/framework/seeds/240-memory-review.prompt.md`, `.wavefoundry/framework/install/lifecycle-prompts/memory-review.prompt.md`, `docs/prompts/memory-review.prompt.md`
- `docs/architecture/contracts/mcp-tool-surface.md`

## Affected Architecture Docs

N/A for the architecture hub and child docs: the change adds optional inputs to two tools inside the memory module and changes no boundary, flow or verification seam. The tool contract `docs/architecture/contracts/mcp-tool-surface.md` is updated (Requirement 8).

Platform behavior: the change is string handling in Python with no filesystem, process or path differences, so Windows, macOS, Linux and WSL2 behave the same.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The fix itself: a rewrite keeps the line and leaves `no_rationale`. |
| AC-2 | important | The second line uses the same path; one test covers it. |
| AC-3 | required  | New persisted fields must not bypass the single-line rule or content scan. |
| AC-4 | required  | Without the prompt step in every copy, agents keep calling the tools without the input. |
| AC-5 | required  | Existing callers see no change, and no line is inherited from a source record. |
| AC-6 | required  | Change-local verification. |
| AC-7 | required  | Consolidation is the second Review memories write path with the same gap. |
| AC-8 | required  | Guards Requirement 5: the new checks must not reach the `memory_validate` path. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-25 | Planned after the arc 244cm item 7 batch review found the gap. | Census: 53 active records with `Supersedes:`, 0 with either line. |
| 2026-11-25 | Amended before any readiness approval from the red-team primer: added `memory_consolidate` (F1), the tool-surface golden (F2), a testable AC-5 (F3) and whitespace stripping before the empty test (F4). | `evidence/review-notes.tar.gz` (readiness) |
| 2026-11-25 | Readiness repair cycle 1 for blocking findings `24bik-r-cr1-validate-path-check` (checks belong in the public entry points, not the shared locked writer; AC-8 added) and `24bik-r-q1-template-copy-omitted` (third prompt copy, hand merge, call-form AC-4), plus the nonblocking notes: per-profile golden and digest description, strip-then-check order, dry-run behavior, contract details, source-line inheritance in AC-5, raw-line assertion in AC-1, test file placement, risk wording. | `evidence/review-notes.tar.gz` (readiness) |
| 2026-11-25 | Readied on receipt `review-policy-be5e286544d717f7106e`: four lanes and `council-readiness` approved (intent_fit `establishes`). Carried notes for implementation: Affected Architecture Docs cites Requirement 8, which is Requirement 7 after renumbering; the wave Objective names only `memory_add`, and the spec governs consolidation and all three prompt copies; prompt literal checks must tolerate wrapped lines; consolidate's pre-lock refusal uses `invalid_memory_record`. | `docs/waves/24bik memory-add-rationale-lines/events.jsonl` |
| 2026-11-25 | Readback: `memory_add` and `memory_consolidate(mode="create")` gain optional `action_delta` and `validation_rationale`, stripped, single-line-checked and content-scanned in the public entry points before the lock, then passed to the existing private parameters; `memory_validate` and `_memory_add_response_locked` stay unchanged. Example: `memory_add(..., supersedes=X, action_delta=" applies when editing the loader; run its test first ")` writes `Action delta: applies when editing the loader; run its test first` and the record leaves `no_rationale`; today the input is refused as unknown. ACs 1-8; files: memory_handlers.py, server_impl.py, two test files, three fixtures, three prompt copies, the tool contract. Serves the intent by letting the documented Review memories rewrite and consolidation calls keep the line the evaluation counts. | wave 24bik opened |
| 2026-11-25 | Implemented. `_rationale_inputs_refusal` in memory_handlers.py strips, single-line-checks and content-scans both inputs for `memory_add_response` and `memory_consolidate_response(create)` before the lock and routes them to the private parameters; `_memory_add_response_locked` and `memory_validate_response` are unchanged. Tests: `RationaleInputTests` (AC-1, 2, 3, 5, 7, 8) in test_memory_records.py; prompt call-form and definition checks plus four known-bad controls in `assert_memory_review_contract` / `test_prompt_contract_and_known_bad_controls`. Landing mutants (scratch copy, each fails the named tests): routing dropped in memory_add (AC-1, AC-2), routing dropped in consolidate (AC-7), strip removed (AC-1, AC-2, AC-7), single-line check removed (AC-3, AC-7), content scan removed (AC-3, AC-7), single-line check moved into the locked writer (AC-8). Goldens regenerated with `WF_UPDATE_TOOL_SURFACE_GOLDEN=1` (20 lines each in `tool-surface-golden.json` and `tool-surface-golden/declared.json`); handler digests changed only for memory_add and memory_consolidate. Focused run: 1871 tests across 7 files OK; `--profile declared` and `--profile second` on the 4 touched test files: 0 of 4 failed each. Gapfill: edits and probes used shell and Python scripts for multi-site exact replacements and scratch-tree mutation; retrieval used the MCP server's earlier reads and direct reads of the named functions. | `evidence/review-notes.tar.gz` |
| 2026-11-25 | Framework suite green: 13620 tests across 261 files OK (13 skipped by design), receipt `result: ok` written by `run_tests.py`. All ACs and tasks complete; ready for Review wave. | `evidence/review-notes.tar.gz` (suite.log) |
| 2026-11-25 | Delivery review cycle 0: red-team, code, QA, architecture and docs-contract all APPROVE with nonblocking findings. Repaired before any delivery approval: QA-1 (AC-7 test now also writes and asserts `validation_rationale`), CR-3/QA-2 (new `test_registered_tools_forward_both_inputs` calls the registered MCP wrappers; wrapper-forwarding mutants for both tools now fail it), CR-2 (`recovery_usage` names the refused field), D-1 (consolidation step says the line is written fresh, not copied, and restates what `validation_rationale` holds, in all three copies, with new clause guards and four more known-bad controls), D-2 (the `supersedes_target_not_updated` fallback starts its own line), AR-2/D-3 (contract signature rewrapped). Declined: RT-2/CR-1 (merging the pre-check problems with the locked validation list; safe as is, one extra round trip), RT-3 (`preview_data` on the consolidate refusal; no caller reads it), option (d) advisory (unchanged Decision Log reasoning). Operator follow-up candidate: AR-1, aligning `memory_validate` with `memory_single_line`. Focused rerun 629 tests OK; `--profile second` and `--profile declared` on the two repaired test files: 0 of 2 failed each. | `evidence/review-notes.tar.gz` (delivery) |
| 2026-11-25 | Delivery focused re-review: all four lanes APPROVE the repaired delta. Suite on the repaired tree: 13621 tests across 261 files OK. Code-reviewer CR-4 (content-only refusal hint untested; mutant M19 survived) repaired by asserting `recovery_usage` names the field in the AC-3 content subtests; M19 now fails `test_ac3`. QA intent-check text corrections applied to the wave.md Intent outcome paragraph. | `evidence/review-notes.tar.gz` (delivery) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-25 | Add optional `action_delta` and `validation_rationale` inputs to `memory_add` and tell the Review memories rewrite step to pass `action_delta`. | Planner default after the operator asked to "plan a fix for memory_add". The write path already exists behind private parameters, so this is the smallest change. Efficacy: replaying item 7, each of the 52 rewrites would have written the line, and the record would leave `no_rationale`, which the evaluation checks by the presence of either line. The tool controls the write; whether the agent supplies the value depends on the prompt, which the AC-4 test protects. Success after release: the next Review memories pass lowers the `no_rationale` count instead of raising it. | (a) Copy the lines from the superseded record: a rewrite exists because the record was wrong, so the old line may be stale, and an inherited line would hide that. (b) Require `action_delta` whenever `supersedes` is set: blocks existing callers and adds a refusal path for a case the prompt already covers. (c) Route active-record rewrites through `memory_validate`: that tool is built for evidence-derived candidates and its rewrite verdict carries candidate-only checks; changing that is a larger redesign. (d) A non-blocking advisory when a rewrite omits both lines: declined; the prompt step plus AC-4 covers it, and the next Review memories pass measures whether agents comply. |
| 2026-11-25 | Validate in the public entry points, strip before the single-line check, and leave `_memory_add_response_locked` unchanged. | Planner decision on code-reviewer finding CR-1 and the strip-order notes: a check inside the shared locked writer would also reach `memory_validate`, which accepts U+2028 today (Requirement 5, AC-8). Stripping first accepts a trailing newline that hosts and editors add on every platform, while an internal break is still refused. | Check the raw value: refuses values that differ only by a trailing newline. |
| 2026-11-25 | Merge the step text by hand into all three prompt copies. | Planner decision on QA finding Q1: rendering only writes a missing prompt, so editing the seed and re-rendering would leave the install template and the self-hosted prompt unchanged. | Re-render only: the instruction never reaches this repository or target repositories. |
| 2026-11-25 | Extend the same inputs to `memory_consolidate(mode="create")`. | Planner decision on red-team finding F1: `memory_consolidate_response` writes active replacements through the same private path with neither value, so leaving it out would keep Review memories raising `no_rationale`. Same mechanism, no new design. | Narrow Product Intent to `memory_add` and leave consolidation as a follow-up: keeps the stated problem half-fixed. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Agents supply a line that restates the summary rather than when it applies. | The prompt step states what the line must say; the evaluation only checks presence, so quality stays a review judgment. |
| The 53 existing rewrites keep counting as `no_rationale`. | Out of scope; the operator decides whether a later Review memories pass addresses them. |
| A host caches the old tool schema, or the server is not reloaded. | A host with the cached schema cannot send the new inputs; a server that was not reloaded refuses them through `_ensure_no_extra_args` rather than dropping them. Reconnect after delivery. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
