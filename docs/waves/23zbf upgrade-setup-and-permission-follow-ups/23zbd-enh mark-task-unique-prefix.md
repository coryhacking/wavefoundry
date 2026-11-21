# Mark a task by a unique prefix

Change ID: `23zbd-enh mark-task-unique-prefix`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-21
Wave: 23zbf upgrade-setup-and-permission-follow-ups

## Rationale

`wf_mark_task` accepts a task only by its complete label. Task labels are free prose, often a full sentence with backticks and punctuation, so one differing character costs a failed call and a retry with the label copied from the error. Acceptance criteria do not have this cost: `wf_mark_ac` already accepts the short id `AC-1` for `AC-1: ...`. Field feedback item 13.1 on v1.46.0 asked for the same economy on tasks, and the operator accepted the evaluator's DO verdict on 2026-11-21 (`.wavefoundry/work/23zbf/eval/upgrade-and-backlog.md`, section 13.1).

## Product Intent

An agent that tracks tasks in real time marks a task by typing the start of its label, as long as that start identifies exactly one task. Before: any request shorter than the full label fails with `mark_target_not_found`. After: a unique prefix marks the task, and a prefix that fits several tasks is refused with the matching labels listed. The tool never guesses between tasks, and acceptance criteria keep their id-based matching.

## Requirements

Current behavior, verified by running `.wavefoundry/work/23zbf/planning/23zbd/probe_current_matching.py` against HEAD: `wf_mark_ac` and `wf_mark_task` both call `_mark_change_item_response` in `.wavefoundry/framework/scripts/wf_server/server_impl.py`. Its candidate loop lowercases the stripped request and each logical label, and an item matches when `label == requested or label.startswith(requested + ":")`. This is the **existing rule** below. Zero matches return `mark_target_not_found` with every label of the section in `candidate_labels`; more than one returns `ambiguous_mark_target`.

1. The existing rule runs first and is unchanged for both sections. When it matches exactly one item, that item is marked. When it matches more than one, the call is refused with `ambiguous_mark_target` as today, and the prefix rule does not run.
2. The prefix rule runs only when all of these hold: the target section is `Tasks`, the existing rule matched no item, and the stripped request is not empty. A task matches the prefix rule when its lowercased logical label starts with the lowercased stripped request. The logical label is the one the loop already builds, including continuation lines of a wrapped task.
3. When the prefix rule matches exactly one task, that task is marked through the unchanged write path. The response is the ordinary success envelope; `matched_text` shows the full matched item and `item_label` echoes the request.
4. When the prefix rule matches more than one task, the call is refused with `ambiguous_mark_target` and nothing is written. `candidate_labels` holds the full logical label of each matching task, in document order, and no other label. The message states that the request is a prefix of several tasks, keeps the words `Do not choose arbitrarily`, and tells the caller to retry with a longer prefix or the full label.
5. When the prefix rule matches no task, the call is refused with `mark_target_not_found` exactly as today, with every task label in `candidate_labels`.
6. A request that equals one task's full label marks that task even when the same text is a prefix of other tasks. This follows from requirement 1 and is today's behavior.
7. An empty or whitespace-only request never matches by prefix. It is refused with `mark_target_not_found` as today.
8. `wf_mark_ac` matching does not change. A request such as `AC-1` in a document whose only criteria are `AC-10` and `AC-11` stays refused with `mark_target_not_found`.
9. The `wf_mark_task` docstring states that a task is named by its full label or a unique prefix. The Tool Index row and the detail entry for the two mark tools in `docs/specs/mcp-tool-surface.md` state the new matching, and the `wf_mark_task` pin in `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json` is refreshed. No other pin moves.

Consistency between the two tools: both resolve a short form to exactly one item, refuse instead of guessing, and use the same two diagnostic codes with the same recovery tool. They differ only in what the short form is: a criterion has an id before a colon, a task has only prose, so its short form is a unique prefix.

Platforms: no difference on Windows, macOS, Linux or WSL2. The change is a string comparison on labels the function has already decoded and newline-normalized; it adds no file access, path handling, process or encoding step. CRLF documents take the existing normalization and write path.

## Scope

**Problem statement:** a task can be marked only by its complete label, so real-time task tracking costs a failed call whenever the agent's text differs from the label by one character.

**In scope:**

- The candidate selection in `_mark_change_item_response` and the ambiguity message for a prefix match.
- The `wf_mark_task` docstring and the internal docstring of `_mark_change_item_response`.
- Tests in `MarkChangeItemRecoveryTests` (`.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`).
- The `wf_mark_task` handler-digest pin.
- The Tool Index row and the mark-tools detail entry in `docs/specs/mcp-tool-surface.md`.
- An Unreleased `CHANGELOG.md` bullet.

**Out of scope:**

- Prefix matching for acceptance criteria. DECLINE: a criterion already has a short form, and a prefix would let a mistyped `AC-1` mark `AC-10` when `AC-1` does not exist.
- Substring, fuzzy or whitespace-insensitive matching. DECLINE: each widens what a short request can select and none was requested; a prefix is the smallest rule that removes the reported cost.
- Restricting the prefix rule to unmarked tasks. DECLINE: the existing rule selects items in any state, and a state filter would make the same request select different tasks as work proceeds.
- A new response field naming the resolved label. DECLINE: `matched_text` already returns the full matched item.
- Changing the response for an ambiguous match under the existing rule (its `candidate_labels` and message). DECLINE: unrelated to the request, and existing tests pin it.
- Edits to the `wf_mark_ac` docstring, seeds or prompts. DECLINE: no seed or prompt states that a task needs its full label (census: `wf_mark_task` appears in seed 050 and `docs/prompts/implement-wave.prompt.md` only as a tool name), and leaving the `wf_mark_ac` docstring alone keeps its pin still.

## Acceptance Criteria

AC-1 with AC-2 and AC-3 tests whether the intent is established: a unique prefix marks the task, and the tool still never guesses. Every test below calls `_mark_change_item_response` or the registered tool on a real change document in a temporary wave; none asserts on source text.

- [x] AC-1: A unique prefix marks its task. Fails at HEAD, where each case returns `mark_target_not_found`.
  1. With tasks `Add tests for the parser.` and `Add the CHANGELOG bullet.`, the registered `wf_mark_task` with `task="Add tests"`, `state="x"`, `mode="create"` returns `status: ok` with `applied: true`, and the document differs from the original only in the mark of the first task.
  2. The same request in a different case (`add TESTS`) marks the same task.
  3. For a wrapped task whose label continues on a second line, a prefix that ends inside the continuation line marks that task.
  4. The default `mode="dry_run"` with a unique prefix returns `status: ok`, `applied: false`, a `matched_text` holding the full task, and leaves the document bytes unchanged.
- [x] AC-2: An ambiguous prefix is refused and lists its candidates. With tasks `Add tests for the parser.`, `Add the CHANGELOG bullet.` and `Update the spec.`, a `mode="create"` request for `Add t` returns `status: error` with `ambiguous_mark_target`; `candidate_labels` equals the two `Add ...` labels in document order and omits `Update the spec.`; the message contains `Do not choose arbitrarily` and the word `prefix`; the document bytes are unchanged. Fails under an implementation that marks the first match, and at HEAD, where the code is `mark_target_not_found`.
- [x] AC-3: An exact full label wins over the prefix rule. With tasks `Add` and `Add tests for the parser.`, a `mode="create"` request for `Add` marks only the `Add` task. Fails under an implementation that applies the prefix rule first or merges both rules into one candidate set, which reports two candidates.
- [x] AC-4: Requests that identify no task stay refused with `mark_target_not_found`, with every task label in `candidate_labels` and the document unchanged.
  1. A request that is a prefix of no task.
  2. A request that occurs inside a label but not at its start (`tests` against `Add tests for the parser.`). Fails under a substring implementation.
  3. A whitespace-only request against a section that holds exactly one task. Fails under an implementation that treats the empty string as a prefix of every label.
- [x] AC-5: Acceptance-criteria matching is unchanged. With criteria `AC-10: ...` and `AC-11: ...` only, `wf_mark_ac` for `AC-1` returns `mark_target_not_found`, and for `AC-10` it selects that criterion. Fails under an implementation that applies the prefix rule to both sections, which reports `ambiguous_mark_target` for `AC-1`.
- [x] AC-6: Existing-rule behavior is unchanged: the existing tests of `MarkChangeItemRecoveryTests` pass without edits to their assertions, including `test_ambiguous_task_returns_candidates_and_safe_recovery` (two identical labels stay ambiguous) and `test_missing_target_and_non_checkbox_text_return_a_structured_retry`.
- [x] AC-7: The tool surface describes the new matching and only the touched pin moves.
  1. The first sentence of the `wf_mark_task` docstring names both the full label and a unique prefix, and the `wf_mark_task` row of the Tool Index in `docs/specs/mcp-tool-surface.md` carries that sentence, so the Tool Index test in `test_server_tools.py` passes.
  2. The mark-tools detail entry in `docs/specs/mcp-tool-surface.md` states the prefix rule, the refusal with candidates, that an exact label wins, and that criteria are matched by id only. It no longer says a task is addressed only by its full label.
  3. `git diff` of `register-surface-handler-digests.json` shows exactly one changed line, the `wf_mark_task` entry, and `HandlerDigestTests` passes.
- [x] AC-8: `CHANGELOG.md` has one bullet under `[Unreleased]` that describes unique-prefix task marking and its refusal on ambiguity, and ends `Wave 23zbf / 23zbd.`.
- [x] AC-9: The full framework suite passes: `python3 .wavefoundry/framework/scripts/run_tests.py`.

## Tasks

- [x] Open `framework_edit_allowed` before the first framework edit and close it after the last.
- [x] Add the failing tests for AC-1 to AC-5 to `MarkChangeItemRecoveryTests` and confirm they fail at HEAD for the stated reasons.
- [x] Implement the prefix rule in `_mark_change_item_response`: collect prefix matches for `Tasks` beside the existing candidates, use them only when the existing rule matched none and the request is not empty, and give the prefix ambiguity its own message and full-label candidates.
- [x] Update the `wf_mark_task` docstring and the internal docstring of `_mark_change_item_response`.
- [x] Refresh only the `wf_mark_task` value in `register-surface-handler-digests.json` with the digest that `_handler_digests` in `test_mcp_tool_registry.py` computes; do not regenerate the file.
- [x] Update the `wf_mark_task` Tool Index row and the mark-tools detail entry in `docs/specs/mcp-tool-surface.md`.
- [x] Add the Unreleased `CHANGELOG.md` bullet ending `Wave 23zbf / 23zbd.`.
- [x] Run the focused tests (`test_server_tools_lifecycle.py`, `test_mcp_tool_registry.py`, `test_server_tools.py`), then the full suite last, and run `wf_validate_docs`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| tests-and-matching | implementer | none | Failing tests first, then the prefix rule in one function |
| surface-docs | implementer | tests-and-matching | Docstring, digest pin, tool spec, changelog; the docstring wording fixes the Tool Index row |


## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `docs/specs/mcp-tool-surface.md`

- The root changelog also changes; sibling specs in this wave add their own Unreleased bullets, so each adds a separate bullet.
- Sibling spec 23zbc changes the rendered permission allowlist. If it also edits a handler docstring in `server_impl.py`, each spec refreshes only its own pin.

## Affected Architecture Docs

N/A. The change is confined to candidate selection inside one function. `docs/architecture/data-and-control-flow.md` mentions `wf_mark_task` only for context accounting and receipt neutrality, and neither changes: a prefix mark takes the same write path and stays receipt-neutral.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The requested behavior |
| AC-2 | required  | The tool must not guess between tasks |
| AC-3 | required  | Keeps today's exact-label behavior |
| AC-4 | required  | Guards the empty-request and substring over-matches |
| AC-5 | required  | Keeps criteria matching by id |
| AC-6 | required  | No regression in existing refusals |
| AC-7 | required  | The tool surface and its pins are test-enforced |
| AC-8 | required  | Release notes carry every shipped behavior change |
| AC-9 | required  | Close needs a green suite receipt |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-21 | Readback: A unique task prefix such as “Add tests” should mark the full task. An exact task label wins, ambiguous prefixes list only the matching tasks, and criteria retain ID matching. | AC-1 through AC-9, shared writer and lifecycle tests, task docstring and handler pin, tool reference and changelog. Existing AC pin b15eec37 is the 23xlm baseline. |
| 2026-11-21 | Before the prefix implementation, the new registered tests reported four expected failures for unique, case-varied, wrapped and ambiguous prefixes. All 27 mark recovery tests then passed, including the original exact-label assertions. | HandlerDigestTests and test_tool_spec_index_matches_registration passed. Compared with the 23xlm baseline, only the task handler pin changed (51854cc2). Both release bullets are present. Full docs validation passed with the existing AC-9 wording advisory. |
| 2026-11-21 | Spec authored. Current matching executed against HEAD: a unique prefix, an ambiguous prefix and an empty request all return `mark_target_not_found`; an exact label that prefixes other tasks is marked; `AC-1` against `AC-10` and `AC-11` returns `mark_target_not_found`. | `.wavefoundry/work/23zbf/planning/23zbd/probe_current_matching.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-21 | Selected: a second-tier prefix rule that runs only when the existing rule matches nothing. | It leaves every request that works today working the same way, so the exact-label and `Label:` forms cannot become ambiguous. Efficacy: replaying the motivating case (a request that is the start of one long task label) through the rule marks the task in one call; the rule controls the outcome and does not advise. It marks a wrong task only when a truncated request is unique by accident, and the default dry run shows `matched_text` before any write. Success is measured by AC-1 and by fewer `mark_target_not_found` retries in field use. | A single merged candidate set (exact or prefix): rejected, because an exact label that prefixes another task becomes ambiguous and breaks today's behavior. Substring or fuzzy matching: rejected, because it selects tasks the caller did not start to name and makes accidental uniqueness more likely. |
| 2026-11-21 | The prefix rule applies to `Tasks` only. | Verified at HEAD that `AC-1` against `AC-10` and `AC-11` is refused; a prefix rule on criteria would turn a mistyped or stale id into a mark on a different criterion when only one longer id exists. Criteria already have the id short form, so the two tools stay consistent in outcome. | Apply the rule to both sections for one code path: rejected for the wrong-criterion hazard. |
| 2026-11-21 | A prefix ambiguity reuses `ambiguous_mark_target` and lists full logical labels. | Callers already handle that code and its recovery tool; full labels let the caller extend the prefix without another read. | A new diagnostic code: rejected, a new code adds a contract for the same recovery. |
| 2026-11-21 | Leave the `wf_mark_ac` docstring unchanged. | Its matching does not change, and an edit would move a second pin for no behavior. | Mention the contrast in both docstrings: rejected; the tool spec entry carries the contrast. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A short prefix that is unique by accident marks a task the caller did not mean. | The default mode is `dry_run` and returns `matched_text`; the mark is one character and reversible by a hand edit; the docstring tells callers the prefix must identify one task. |
| A prefix that was unique at dry run becomes ambiguous before the write because a task was added. | The write call re-resolves the request and refuses with the candidates. |
| The docstring edit moves more than one pin or drifts from the Tool Index row. | AC-7 checks a one-line fixture diff and the Tool Index test compares the row with the registered first sentence. |
| A sibling spec edits the same function region in `server_impl.py`. | The change is confined to the candidate loop and the refusal block of one function; Serialization Points names the file. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
